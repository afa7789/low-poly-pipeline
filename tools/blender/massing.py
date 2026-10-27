#!/usr/bin/env python3
"""Stage 0: a deterministic pre-spec, one mass per bone, straight from the sheet's silhouettes.

    python3.14 tools/blender/massing.py <sheet.jpg> <biped|spider|spider_high> <out.json>
        [--race Mech] [--palette-sheet <hard sheet.jpg>]

PIPELINE section 21.F1. The author used to write the mass from scratch and spent its edits on
fixing proportions the sheet already states; here code reads the width profiles of the front and
left panels (silhouette.concept_panels) and the rig, and writes the spec the author then EDITS
(props, decals, materials, small moves). Same trade as Sano 2026 (a visual hull as the base volume)
and EdgeRunner 2024 (budget split by band), one level up: per bone instead of per building.

Biped: head, torso and pelvis are stacks of frustums whose widths and depths follow the sheet's row
widths (a piecewise-linear lathe), arms and legs are tapered prisms from joint to joint, hands and
feet are frustums. Spider: the rig's own legs (scale_spider already measured them) as prisms, the
shell a z-slab stack read from the top view and the side profile. Materials are the sheet's colour
zones (silhouette.zone_palette), each part takes the zone that dominates its band of the front view.
Other families return None: the old brief stays.

KIND_FOR is the one place that says which kind each role is built with. A part role whose kind has
an emitter in EMIT is built by it; `lathe` and `limb` (F2) become one entry in each table.
"""
import argparse
import fnmatch
import json
import math
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lathe_limb  # noqa: E402
import rig_families as RF  # noqa: E402
import preflight  # noqa: E402
import silhouette as SIL  # noqa: E402

FAMILIES = ("biped", "spider", "spider_high")
# frustum stacks follow the sheet's depth centre per slice; a lathe cannot (its axis is straight), and
# measured alone it lost 0.03-0.06 on left/top/bottom (n01X) with no gain on the spider (2026-10-27).
# LATHE_MASSING flips head/torso/pelvis/shell to the lathe emitters for a one-surface look.
LATHE_MASSING = False
KIND_FOR = {"head": "frustum", "torso": "frustum", "pelvis": "frustum", "foot": "frustum", "hand": "frustum",
            "arm": "prism", "leg": "prism", "shell": "frustum", "tail": "chain", "neck": "chain"}
if LATHE_MASSING:
    KIND_FOR.update(head="lathe", torso="lathe", pelvis="lathe", shell="lathe")
LATHE_RINGS = {"torso": 8, "shell": 8, "head": 6, "pelvis": 6}   # profile samples per role (lathe_limb.PROFILE_RANGE)
LATHE_SIDES = {"torso": 8, "shell": 8, "head": 6, "pelvis": 6}   # a head of 6x6 costs 68 tris, a torso of 8x8 124
# stack height per role (frustum stacks). Halved on 2026-10-27: 8/5/5/5 read as a pile of ledges
# (n005 v7-r1) and measured alone the IoU moved by at most 0.02 (runs leva3-massing-few).
SLICES = {"head": 3, "torso": 4, "pelvis": 3, "shell": 3}
SPECK = 0.08            # a detached blob under this share of the figure's area is a prop, not the body
BACK_PROP_DEPTH = 0.75  # torso depth cap, x its width, when the props sheet lists a prop on the back (head: +0.3)
JOINT = 0.008           # stack slices overlap by this share of the figure's height
EDGE = 0.008            # half the row window a width is read over, in H
THIN = 0.03             # a stack slice shorter than this share of the top is a step, drawn without taper
MIN_TRIS = 410            # the class floor is 400; grow the torso stack until the pre-spec clears it
SURFACE = {"Mech": "metal"}    # race -> palette surface; the author edits it
DEFAULT_SURFACE = {"biped": "cloth", "spider": "chitin", "spider_high": "chitin"}
LEG_SIDES = 6            # spider legs are thin: a hexagonal tube reads as round and saves 8 tris a leg
LEG_FAT = 2.2             # spider legs are drawn this much thicker than the sheet's runs: the rig's joints are near the sheet's legs, not on them
REACH = 1.1             # the elbow's outer edge stays within this share of the sheet's shoulder span (preflight allows 1.15)
ARM_HAND = 0.06         # hand size in H when the sheet shows no free arm to measure
ARM_R = 0.06              # arm radius in H when the sheet shows no separate arm to measure
MERGED_TORSO = 0.82       # share of the row width that is torso where the arms touch it
SIDES = 8


def _without_specks(mask):
    """The mask minus the blobs under SPECK of its area: a detached prop (n005's vaporiser in the side
    view) would stretch the row extents of the body it floats beside."""
    from scipy import ndimage
    lab, n = ndimage.label(mask)
    if n < 2:
        return mask
    area = np.bincount(lab.ravel())[1:]
    return np.isin(lab, 1 + np.nonzero(area >= SPECK * area.sum())[0])


class View:
    """One sheet panel in spec metres: rows from the top, `s` metres per pixel, centre column."""

    def __init__(self, mask, height):
        mask = _without_specks(mask)
        ys, xs = np.nonzero(mask)
        self.mask = mask[ys.min():ys.max() + 1]
        self.n = self.mask.shape[0]
        self.s = height / self.n
        self.cx = (xs.min() + xs.max() + 1) / 2          # in pixel edges, like runs() and extent()
        cols = np.arange(mask.shape[1])
        self.lo = np.where(self.mask.any(axis=1), np.where(self.mask, cols, 10 ** 6).min(axis=1), -1)
        self.hi = np.where(self.mask.any(axis=1), np.where(self.mask, cols, -1).max(axis=1), -1)

    @property
    def width(self):
        """The figure's full width in metres."""
        ok = self.hi >= 0
        return float(self.hi[ok].max() - self.lo[ok].min() + 1) * self.s

    def recentre(self, y0, y1):
        """Put the centre line midway between the extremes of the rows y0..y1: a prop that hangs on one
        side (n005's vaporiser) pulls the bounding box off the body, the feet stay under it."""
        lo, hi = self.extent(y0, y1)
        self.cx = (lo + hi) / 2

    def rows(self, y0, y1):
        """Row indices covering the heights y0..y1 (metres up from the ground), at least one."""
        a = int(np.clip(round(self.n - 1 - y1 / self.s), 0, self.n - 1))
        b = int(np.clip(round(self.n - 1 - y0 / self.s), 0, self.n - 1))
        return slice(a, max(b, a) + 1)

    def extent(self, y0, y1):
        """(left edge, right edge) in pixels over the rows of y0..y1, ignoring empty rows: the median of
        the rows, so one stray row (a strap, a spike of ink) does not set the width."""
        sl = self.rows(y0, y1)
        lo, hi = self.lo[sl], self.hi[sl]
        ok = hi >= 0
        if not ok.any():
            return self.cx, self.cx
        return float(np.median(lo[ok])), float(np.median(hi[ok])) + 1

    def half(self, y0, y1):
        """Half width in metres around the centre line: the mean of both sides' reach."""
        lo, hi = self.extent(y0, y1)
        return ((hi - self.cx) + (self.cx - lo)) / 2 * self.s

    def span(self, y0, y1):
        """(start, end) in metres from the centre column, over the rows of y0..y1."""
        lo, hi = self.extent(y0, y1)
        return (lo - self.cx) * self.s, (hi - self.cx) * self.s

    def runs(self, y):
        """[(start, end)] in metres from the centre line of the runs of figure pixels at height y."""
        cols = np.nonzero(self.mask[self.rows(y, y).start])[0]
        if not len(cols):
            return []
        breaks = np.nonzero(np.diff(cols) > 1)[0]
        starts = np.concatenate([[cols[0]], cols[breaks + 1]])
        ends = np.concatenate([cols[breaks], [cols[-1]]])
        return [((a - self.cx) * self.s, (b + 1 - self.cx) * self.s) for a, b in zip(starts, ends)]

    def central_half(self, y):
        """Half width of the run of pixels that holds the centre line at height y; None when the
        row is one run with the arms (nothing to tell torso from arm), so the caller falls back."""
        row = self.mask[self.rows(y, y).start]
        cols = np.nonzero(row)[0]
        if not len(cols):
            return None
        run = _run_at(cols, int(round(self.cx)))
        if (run[1] - run[0]) >= 0.92 * (cols.max() - cols.min()):
            return None
        return (run[1] - run[0] + 1) / 2 * self.s


def _run_at(cols, c):
    """(first, last) column of the run of `cols` (sorted) nearest the column c."""
    breaks = np.nonzero(np.diff(cols) > 1)[0]
    starts = np.concatenate([[0], breaks + 1])
    ends = np.concatenate([breaks, [len(cols) - 1]])
    k = min(range(len(starts)), key=lambda i: 0 if cols[starts[i]] <= c <= cols[ends[i]]
            else min(abs(cols[starts[i]] - c), abs(cols[ends[i]] - c)))
    return int(cols[starts[k]]), int(cols[ends[k]])


def zone_slot(labels, view, y0, y1, x0, x1):
    """Slot index (0-based) of the colour zone that dominates the front view's box (heights
    y0..y1, x0..x1 metres from the centre line); 0 when the box holds no figure."""
    sl = view.rows(y0, y1)
    c0, c1 = sorted((int(view.cx + x0 / view.s), int(view.cx + x1 / view.s)))
    box = labels[sl, max(c0, 0):max(c1, 0) + 1]
    counts = np.bincount(box[box > 0].ravel(), minlength=2)
    return int(np.argmax(counts[1:])) if counts[1:].any() else 0


def r3(v):
    return round(float(v), 4)


# ---- emitters: (role, bone, slot, geometry) -> parts. One per kind in KIND_FOR.

def breakpoints(ys, channels, n):
    """n+1 heights from ys[0] to ys[-1]: the profile's vertices, picked greedily where the straight
    line between the chosen ones is farthest from the sampled widths w and depths d (Douglas-Peucker
    on all the channels at once)."""
    pick = [0, len(ys) - 1]
    while len(pick) <= n:
        err = np.zeros(len(ys))
        for ch in channels:
            err = np.maximum(err, np.abs(ch - np.interp(ys, ys[pick], ch[pick])))
        err[pick] = -1
        if err.max() <= 1e-4:
            break
        pick = sorted(pick + [int(err.argmax())])
    return ys[pick]


def _frustum_stack(role, bone, slot, g):
    """Frustums stacked from y0 to y1 whose full widths g["w"](y), depths g["d"](y) and depth centre
    g["zc"](y) follow the sheet; the breakpoints sit where the profile bends (a piecewise-linear lathe)."""
    ys = np.linspace(g["y0"], g["y1"], 41)
    chans = [np.array([g[k](y) for y in ys]) for k in ("w", "d", "zc")]
    parts = []
    cuts = breakpoints(ys, chans, g.get("n", SLICES.get(role, 1)))
    for ya, yb in zip(cuts[:-1], cuts[1:]):
        pad = 0.04 * (yb - ya)
        wa, wb = g["w"](ya + pad), g["w"](yb - pad)
        da, db = g["d"](ya + pad), g["d"](yb - pad)
        za, zb = g["zc"](ya + pad), g["zc"](yb - pad)
        if yb - ya < THIN * g["y1"]:    # a step in the profile: a straight slab, not a flared wedge
            wa, da, za = (wa + wb) / 2, (da + db) / 2, (za + zb) / 2
            wb, db, zb = wa, da, za
        sx, sz = np.clip([wb / max(wa, 1e-3), db / max(da, 1e-3)], 0.3, 3.0)
        h = yb - ya + JOINT * g["y1"]    # joints overlap, so the 1/256 grid snap and the rig never open a gap
        parts.append([bone, "frustum", [r3(wa), r3(h), r3(da)], [r3(g.get("xc", 0.0)), r3((ya + yb) / 2), r3(za)],
                      slot, {"top": [r3(sx), r3(sz)], "shift": [0, r3(zb - za)]}])
    return parts


def _prism_limb(role, bone, slot, g):
    """One tapered prism from g["a"] to g["b"], radii g["r"] = (at a, at b)."""
    r0, r1 = g["r"]
    a, b = g["a"], g["b"]
    return [[bone, "prism", [r3(r0), r3(r1), r3(math.dist(a, b))], [0, 0, 0], slot,
             {"sides": g.get("sides", SIDES), "from": [r3(v) for v in a], "to": [r3(v) for v in b]}]]


def _lathe_body(role, bone, slot, g):
    """One lathe from y0 to y1: the profile is the sheet's full width w(y) at LATHE_RINGS heights
    (fraction of the widest ring), squash = mean width / mean depth, centre at the mean depth
    centre. One continuous surface instead of a stack of frustums with ledges (PIPELINE 21.F1)."""
    ys = np.linspace(g["y0"], g["y1"], LATHE_RINGS.get(role, 8))
    pad = 0.03 * (g["y1"] - g["y0"])
    w = np.array([g["w"](min(max(y, g["y0"] + pad), g["y1"] - pad)) for y in ys])
    d = np.array([g["d"](min(max(y, g["y0"] + pad), g["y1"] - pad)) for y in ys])
    zc = float(np.mean([g["zc"](y) for y in ys]))
    r = max(float(w.max()) / 2, 1e-3)
    profile = [r3(float(v)) for v in np.clip(w / (2 * r), 0.05, 1.5)]
    squash = r3(float(np.clip(w.mean() / max(d.mean(), 1e-3), 0.5, 2.0)))
    h = g["y1"] - g["y0"] + JOINT * g["y1"]
    return [[bone, "lathe", [r3(r), r3(h)], [r3(g.get("xc", 0.0)), r3((g["y0"] + g["y1"]) / 2), r3(zc)],
             slot, {"profile": profile, "squash": squash, "sides": LATHE_SIDES.get(role, 8)}]]


CHAIN_SIDES = 6          # a chain's ring is a hexagon (lathe_limb.chain_rings phases it to read round from the side and above)


def _chain_run(role, bone, slot, g):
    """One chain along the rig bones from `bone` (g["bones"] of them): the radius at each joint is
    g["half"](joint), the sheet's half width there (metres). PIPELINE 22.L4-1. No family in FAMILIES
    has a tail or a neck to massing yet (L4-4): the emitter waits for its caller, opt-in by role."""
    radii = [r3(max(g["half"](j), 0.02)) for j in lathe_limb.chain_joints(bone, g["bones"])]
    return [[bone, "chain", radii, [0, 0, 0], slot,
             {"bones": g["bones"], "sides": CHAIN_SIDES, "profile_axis": "left"}]]


EMIT = {"frustum": _frustum_stack, "prism": _prism_limb, "lathe": _lathe_body, "chain": _chain_run}


def emit(role, bone, slot, geometry):
    """The parts of one role, built with the kind KIND_FOR says; a kind without an emitter (a
    swap to lathe/limb before its emitter is registered) falls back to the one that exists."""
    kind = KIND_FOR[role] if KIND_FOR[role] in EMIT else ("prism" if "a" in geometry else "frustum")
    return EMIT[kind](role, bone, slot, geometry)


# ---- palette

def palette_of(path, race, rig):
    """(palette dict, slot names, centres): the sheet's colour zones as slots z1..zk, at least 3."""
    hexes, centres, _ = SIL.zone_palette(path)
    surface = SURFACE.get(race, DEFAULT_SURFACE[rig])
    names = [f"z{i + 1}" for i in range(len(hexes))]
    pal = {n: {"surface": surface, "color": h} for n, h in zip(names, hexes)}
    while len(pal) < 3:                 # the preflight wants 3-8 slots: a darker copy of the main zone
        n = f"z{len(pal) + 1}"
        base = hexes[0]
        pal[n] = {"surface": surface, "color": "#" + "".join(f"{int(int(base[i:i + 2], 16) * 0.7):02X}" for i in (1, 3, 5))}
        names.append(n)
    return pal, names, centres


# ---- biped

def crotch_y(front, H):
    """Height where the two legs part: the first row under 55 % of the height whose centre
    column is empty for 3 rows; 0.45 H when the figure never splits (a long coat)."""
    c = int(round(front.cx))
    empty = ~front.mask[:, max(c - 1, 0):c + 2].any(axis=1)
    for r in range(int(0.45 * front.n), int(0.95 * front.n)):
        if empty[r:r + 3].all():
            return H - r * front.s
    return 0.45 * H


def arm_geometry(front, H, y_sh, y_fist, reach):
    """(shoulder, elbow, wrist, r_upper, r_lower) of the +x arm. Where the arm hangs free of the torso
    (three runs in a row) its centre line is the middle of the outer run and its radius half that run;
    where it touches the torso, the outer edge of the front view inset by the radius. The elbow stays
    inside `reach` (metres from the centre line, the arm's own outer edge): preflight's shoulder_span
    reads the box of every part that touches the shoulder band, so a slanted upper arm must not lean out
    past the sheet's shoulders."""
    top = y_sh - 0.05 * H
    wrist = y_fist + 2.1 * ARM_HAND * H          # y_fist is the bottom of the fist: the hand fills the last two radii
    mid = (top + wrist) / 2

    def radius(y0, y1):
        free = [front.runs(y)[-1] for y in np.linspace(y0, y1, 4) if len(front.runs(y)) >= 3]
        widths = [b - a for a, b in free if b > 0]
        return float(np.clip(np.median(widths) / 2, 0.035 * H, 0.12 * H)) if widths else ARM_R * H

    r_up, r_lo = radius(top, mid), radius(mid, y_fist)

    def centre(y, r):
        runs = front.runs(y)
        if len(runs) >= 3 and runs[-1][1] > 0:
            return (runs[-1][0] + runs[-1][1]) / 2
        return front.half(y - 0.01 * H, y + 0.01 * H) - r

    elbow_x = min(centre(mid, r_up), reach - r_up)
    return (centre(top, r_up), top, 0.0), (elbow_x, mid, 0.0), (centre(wrist, r_lo), wrist, 0.0), r_up, r_lo


def nearest_run(front, y, x):
    """(centre, width) in metres of the +x run of the front view at height y nearest to x; None
    when the row has no run to the right of the centre line."""
    runs = [(a, b) for a, b in front.runs(y) if b > 0.02 * front.n * front.s]
    if not runs:
        return None
    a, b = min(runs, key=lambda r: abs((r[0] + r[1]) / 2 - x))
    return (a + b) / 2, b - a


def leg_geometry(front, left, H, y_top, bh):
    """(hip, knee, ankle, r_thigh, r_shin) of the +x leg: the run nearest the ankle's own x in the
    front view (the arms hang outside, the pelvis inside), z-centred on the side view's row centre.
    A run wider than a fifth of H is torso or arm, not leg: the ankle's x and width stand in."""
    base = nearest_run(front, 1.3 * bh, 0.2 * H) or (0.2 * H, 0.1 * H)
    knee_y = (y_top + bh) / 2

    def leg(y):
        run = nearest_run(front, y, base[0])
        return run if run and run[1] <= 0.2 * H else base

    pts = [leg(y) for y in (y_top, knee_y, 1.3 * bh)]
    zc = [zcentre(left, y) for y in (y_top, knee_y, 1.3 * bh)]
    hip, knee, ankle = ((pts[i][0], y, zc[i]) for i, y in enumerate((y_top, knee_y, bh)))
    cap = lambda w: float(np.clip(w / 2, 0.025 * H, 0.09 * H))   # noqa: E731
    return hip, knee, ankle, cap(leg((y_top + knee_y) / 2)[1]), cap(leg((knee_y + bh) / 2)[1]), base


class Side:
    """The left panel as depth along z (+z the way the feet point), centred like the figure."""

    def __init__(self, view, sign, zero):
        self.v, self.sign, self.zero = view, sign, zero

    def span(self, y0, y1):
        lo, hi = self.v.extent(y0, y1)
        a, b = (lo - self.zero) * self.v.s * self.sign, (hi - self.zero) * self.v.s * self.sign
        return min(a, b), max(a, b)


def zcentre(side, y, e=0.01):
    a, b = side.span(y - e, y + e)
    return (a + b) / 2


def side_of(panel, H, front_y_toe=0.06):
    """The left view with its sign so that +z is the way the feet point (the toe row sticks out of the
    leg column), centred on the figure's own bounding box."""
    v = View(panel, H)
    lo, hi = v.extent(0.0, front_y_toe * H)
    mid = (v.extent(0.3 * H, 0.7 * H))
    centre = (v.extent(0.0, H)[0] + v.extent(0.0, H)[1]) / 2
    sign = 1 if (lo + hi) / 2 >= (mid[0] + mid[1]) / 2 else -1
    return Side(v, sign, centre)


def stack_geometry(front, side, y0, y1, torso=None, depth_cap=None):
    e = EDGE * front.n * front.s
    """g for _frustum_stack: full widths from the front view (torso: the central run when the arms
    hang free), depths from the side view."""
    def w(y):
        if torso is not None:
            c = front.central_half(y)
            h = c if c is not None else front.half(y - e, y + e) * (MERGED_TORSO if y > torso else 1.0)
            return 2 * h
        return 2 * front.half(y - e, y + e)

    def span(y):
        """(depth, centre z): a back-mounted prop (a tank) is the author's part, not the body's: with a
        cap the depth is cut to cap x the width and the chest line, the front edge, stays."""
        a, b = side.span(y - e, y + e)
        if depth_cap is None or b - a <= depth_cap * w(y):
            return b - a, (a + b) / 2
        return depth_cap * w(y), b - depth_cap * w(y) / 2
    return {"y0": y0, "y1": y1, "w": w, "d": lambda y: span(y)[0], "zc": lambda y: span(y)[1]}


def landmarks(front, H, m):
    """Heights in metres of the biped's joints, read from the front view and silhouette.measure: shoulder
    line, crotch, neck, bottom of the fist, top of the pelvis, boot top. The head takes at least the top
    70 % of the way down to the shoulders (a hood has no neck; the preflight reads head_width there)."""
    y_sh = H * (1 - m["shoulder_frac"])
    y_hip = crotch_y(front, H)
    rows = front.mask[:max(int(m["shoulder_frac"] * front.n), 4)]
    lo = int(0.3 * len(rows))
    y_neck = min(H - (rows.sum(axis=1)[lo:].argmin() + lo) * front.s, y_sh + 0.3 * (H - y_sh))
    return {"shoulder": y_sh, "hip": y_hip, "neck": y_neck,
            "fist": y_sh - m["arm_length"] * math.cos(math.radians(m["arm_angle"])) * H,
            "pelvis": y_hip + 0.22 * (y_neck - y_hip), "boot": max(m["boot_height"] * H, 0.05 * H)}


def trunk_parts(front, side, lm, H, labels_for, cap=None):
    """Head, torso and pelvis stacks; `cap` (a back-mounted prop is listed): the depth cap of torso and head."""
    head = labels_for(lm["neck"], H, -0.5 * H, 0.5 * H)
    parts = emit("head", "head", head, stack_geometry(front, side, lm["neck"] - 0.02 * H, H, depth_cap=cap and cap + 0.3))
    for role, bone, y0, y1 in (("torso", "spine", lm["pelvis"], lm["neck"]), ("pelvis", "pelvis", lm["hip"], lm["pelvis"])):
        g = stack_geometry(front, side, y0 - 0.02 * H, y1 + 0.02 * H, torso=lm["fist"], depth_cap=cap)
        parts += emit(role, bone, labels_for(y0, y1, -0.3 * H, 0.3 * H), g)
    return parts


def arm_parts(front, side, lm, H, labels_for, sides, reach):
    """Both arms: upper arm, forearm and hand."""
    sh, el, wr, r_up, r_lo = arm_geometry(front, H, lm["shoulder"], lm["fist"], reach)
    z = zcentre(side, lm["shoulder"])
    parts = []
    for sgn, tag in ((1, "L"), (-1, "R")):
        pt = lambda p: (sgn * p[0], p[1], z)   # noqa: E731
        slot = labels_for(lm["fist"], lm["shoulder"], 0.0, sgn * H)
        for bone, a, b, radii in (("arm", sh, el, (1.1 * r_up, r_up)), ("forearm", el, wr, (r_lo, 1.15 * r_lo))):
            parts += emit("arm", f"{bone}.{tag}", slot, {"a": pt(a), "b": pt(b), "r": radii, "sides": sides})
        parts.append([f"forearm.{tag}", "frustum", [r3(2.3 * r_lo), r3(2.1 * r_lo), r3(2.1 * r_lo)],
                      [r3(sgn * wr[0]), r3(wr[1] - 1.05 * r_lo), r3(z)], slot, {"top": [1.0, 1.0], "shift": [0, 0]}])
    return parts


def leg_parts(front, side, lm, H, labels_for, sides):
    """Both legs: thigh, shin and the boot, centred on the front view's run at the boot's own rows."""
    hip, knee, ankle, r_th, r_sh, base = leg_geometry(front, side, H, lm["hip"] + 0.06 * H, lm["boot"])
    bh = lm["boot"]
    foot = nearest_run(front, 0.45 * bh, base[0]) or base
    foot_w = float(np.clip(foot[1], 2 * r_sh, 0.25 * H))
    zlo, zhi = side.span(0.0, bh)
    parts = []
    for sgn, tag in ((1, "L"), (-1, "R")):
        pt = lambda p: (sgn * p[0], p[1], p[2])   # noqa: E731
        slot = labels_for(0.0, lm["hip"], min(0.0, sgn * 0.5 * H), max(0.0, sgn * 0.5 * H))
        parts += emit("leg", f"thigh.{tag}", slot, {"a": pt(hip), "b": pt(knee), "r": (r_th * 1.05, r_th * 0.9), "sides": sides})
        parts += emit("leg", f"shin.{tag}", slot, {"a": pt(knee), "b": pt((ankle[0], ankle[1] + 0.02 * H, ankle[2])),
                                                    "r": (r_sh * 0.95, r_sh), "sides": sides})
        parts.append([f"foot.{tag}", "frustum", [r3(foot_w), r3(bh), r3(zhi - zlo)],
                      [r3(sgn * foot[0]), r3(bh / 2), r3((zlo + zhi) / 2)], slot,
                      {"top": [0.9, 0.8], "shift": [0, r3(-0.04 * (zhi - zlo))]}])
    return parts


def biped(sheet, H, labels_for, sides=SIDES):
    """Parts of the biped pre-spec: head, torso and pelvis stacks, arms, legs, hands and boots."""
    from silhouette import concept_panels, measure
    panels = concept_panels(sheet)
    front, side = View(panels["front"], H), side_of(panels["left"], H)
    front.recentre(0.0, 0.08 * H)
    m_sheet = measure(sheet)
    lm = landmarks(front, H, m_sheet)
    props = preflight.load_props(pathlib.Path(sheet).parent.name)
    back = any(b in ("spine", "pelvis") for prop in props for b in prop["bones"])
    return (trunk_parts(front, side, lm, H, labels_for, BACK_PROP_DEPTH if back else None) + arm_parts(front, side, lm, H, labels_for, sides, REACH * m_sheet["shoulder_span"] * H / 2)
            + leg_parts(front, side, lm, H, labels_for, sides))


# ---- spider

def spider(sheet, rig, labels_for, sides=LEG_SIDES):
    """Parts of the spider pre-spec: the rig's 16 leg bones as prisms (scale_spider already put the
    joints where the sheet has them), the shell as z-slabs."""
    panels = SIL.concept_panels(sheet)
    table = {name: (head, tail) for name, _, head, tail in RF.FAMILIES[rig]}
    H = RF.top(rig)
    front = View(panels["front"], H)
    leg_r = float(np.clip(LEG_FAT * _leg_radius(front, H), 0.012 * H, 0.08 * H))
    parts = []
    for i in range(1, 9):
        slot = labels_for(0.0, 0.4 * H, -0.5 * H, 0.5 * H)
        (h1, t1), (h2, t2) = table[f"leg{i}.upper"], table[f"leg{i}.lower"]
        parts += emit("leg", f"leg{i}.upper", slot, {"a": h1, "b": t1, "r": (leg_r * 1.15, leg_r), "sides": sides})
        parts += emit("leg", f"leg{i}.lower", slot, {"a": h2, "b": t2, "r": (leg_r, leg_r * 0.6), "sides": sides})
    hips_z = min(table[f"leg{i}.upper"][0][2] for i in range(1, 9)) - leg_r
    return parts + _shell(sheet, panels, front, H, labels_for, hips_z)


def _leg_radius(front, H):
    """Half the median width of the runs in the front view's lowest rows: the legs' own thickness."""
    widths = [b - a for y in np.linspace(0.02 * H, 0.12 * H, 6) for a, b in front.runs(y)]
    return float(np.median(widths)) / 2 if widths else 0.03 * H


def body_footprint(top):
    """(half width in pixels per row of the body seen from above with the legs opened away, head end
    first; the mask's full width in pixels)."""
    body = opened(top)
    rows = np.nonzero(body.any(axis=1))[0]
    halves = [(np.ptp(np.nonzero(body[i])[0]) + 1) / 2 for i in rows]
    ys, xs = np.nonzero(top)
    return np.array(halves), xs.max() - xs.min() + 1


def opened(mask):
    """The mask with its thin parts (the legs) opened away: binary opening with a disc 0.6 of the
    largest inscribed one, as measure_spider reads the body in the top view."""
    from scipy import ndimage
    r = ndimage.distance_transform_edt(mask).max()
    q = int(0.6 * r)
    disc = np.hypot(*np.ogrid[-q:q + 1, -q:q + 1]) <= 0.6 * r
    return ndimage.binary_opening(mask, structure=disc)


def shell_profile(left, H):
    """(columns, top edge y, bottom edge y) of the side view's body (bottom: legs opened away), head
    end last: the head end is the one whose back line is lower, and it must be +z."""
    body = opened(left.mask)
    cols = np.nonzero(body.any(axis=0))[0]
    top_y = H - np.argmax(left.mask[:, cols], axis=0) * left.s     # the back line is the real one: it sets the model's height
    bot_y = H - (body.shape[0] - 1 - np.argmax(body[::-1][:, cols], axis=0)) * left.s
    n = max(len(cols) // 6, 1)
    if top_y[:n].mean() < top_y[-n:].mean():
        cols, top_y, bot_y = cols[::-1], top_y[::-1], bot_y[::-1]
    return cols, top_y, bot_y


DOME_AT = (0.0, 0.35, 0.7, 1.0)   # a shell slab's frustum boundaries, fractions of belly -> back
SLABS = (("abdomen", 0.0, 0.1), ("abdomen", 0.1, 0.2), ("abdomen", 0.2, 0.3), ("abdomen", 0.3, 0.45),
         ("body", 0.45, 0.55), ("body", 0.55, 0.65), ("body", 0.65, 0.76), ("head", 0.76, 1.0))


def _shell(sheet, panels, front, H, labels_for, hips_z):
    """Body, abdomen and head as z-slabs of the side view's length (SLABS, fractions from the tail):
    x width from the top view with the legs opened away (rows laid over the slabs without the head),
    y range from the side view's opened body, z centred where the rig's own body is."""
    m = SIL.measure_spider(sheet)
    left = View(panels["left"], H)
    cols, top_y, bot_y = shell_profile(left, H)
    halves, top_w = body_footprint(panels["top"])
    halves = halves[::-1]                         # the top view has the head end up: tail first
    k = front.width / top_w                       # metres per top-view pixel: the leg ring is as wide from both views
    zs = min(max(m["body_len"] * H / 1.57, 0.3), 1.5)
    z_lo = -0.065 * zs - len(cols) * left.s / 2
    body_half = m["body_r"] * H
    dome = lambda y: float(np.clip(front.half(y - 0.01 * H, y + 0.01 * H) / body_half, 0.3, 1.0))   # noqa: E731
    parts = []
    for bone, f0, f1 in SLABS:
        i0 = int(f0 * len(cols))
        i1 = max(int(f1 * len(cols)), i0 + 1)
        r0 = min(int(f0 / 0.76 * len(halves)), len(halves) - 1)
        rows = halves[r0:max(int(f1 / 0.76 * len(halves)), r0 + 1)] if bone != "head" else halves[-max(len(halves) // 4, 1):]
        width = 2 * k * float(np.mean(rows)) * (0.55 if bone == "head" else 1.0)
        ybot, ytop = float(bot_y[i0:i1].mean()), float(top_y[i0:i1].mean())
        if top_y[i0:i1].max() == top_y.max():      # the highest slab reaches the figure's own top: the model's height
            ytop = float(top_y.max())
        slot = labels_for(ybot, ytop, -width / 2, width / 2)
        z = (z_lo + i0 * left.s, z_lo + i1 * left.s)
        if bone == "abdomen" and z[1] > hips_z:      # a slab over the leg hips is the body's: the legs hang from it
            bone = "body"
        parts += _slab(bone, slot, z, (ybot, ytop), width, dome)
    return _shell_lathes(parts, dome) if KIND_FOR["shell"] == "lathe" else parts


def _shell_lathes(slabs, dome):
    """The frustum slabs of each spider bone merged into one upright lathe: x radius = the widest
    slab, z radius = half the bone's length (squash = width / length, an oval from the top), the
    profile from the front view's dome between belly and back. The top view stops being a box."""
    out, done = [], set()
    for bone in [p[0] for p in slabs]:
        if bone in done:
            continue
        done.add(bone)
        mine = [p for p in slabs if p[0] == bone]
        width = max(p[2][0] for p in mine)
        z0 = min(p[3][2] - p[2][2] / 2 for p in mine)
        z1 = max(p[3][2] + p[2][2] / 2 for p in mine)
        ybot = min(p[3][1] - p[2][1] / 2 for p in mine)
        ytop = max(p[3][1] + p[2][1] / 2 for p in mine)
        r = max(width / 2, 1e-3)
        squash = float(np.clip(width / max(z1 - z0, 1e-3), 0.5, 2.0))
        ys = np.linspace(ybot, ytop, 6)
        profile = [r3(max(float(dome(y)), 0.3)) for y in ys]
        out.append([bone, "lathe", [r3(r), r3(ytop - ybot)], [0, r3((ybot + ytop) / 2), r3((z0 + z1) / 2)],
                    mine[0][4], {"profile": profile, "squash": r3(squash), "sides": 8}])
    return out


def _slab(bone, slot, z, y, width, dome):
    """Frustums stacked from the belly to the back line, each narrowing as the front view's shell
    does: a dome slice. dome(y) is the share of the width left at height y."""
    za, zb = z
    ybot, ytop = y
    levels = ybot + np.array(DOME_AT) * (ytop - ybot)
    parts = []
    for ya, yb in zip(levels[:-1], levels[1:]):
        wa, wb = width * dome(ya), width * dome(yb)
        da = db = (zb - za) * 1.08       # a little over, so neighbouring slabs overlap
        parts.append([bone, "frustum", [r3(wa), r3(yb - ya + JOINT * ytop), r3(da)], [0, r3((ya + yb) / 2), r3((za + zb) / 2)], slot,
                      {"top": [r3(wb / wa), r3(db / da)], "shift": [0, 0]}])
    return parts


SLOT_GROUPS = ("foot.*", "head", "abdomen", "forearm.*", "leg?.lower")   # parts handed the unused zones, in this order


def ensure_slots(parts, names, need=3):
    """The preflight wants `need` materials in use: when the dominant zones leave fewer, the parts of the
    first SLOT_GROUPS hand the colours no part took (a sheet of one dark colour: every part is zone 1)."""
    spare = [n for n in names if n not in {p[4] for p in parts}]
    for pattern in SLOT_GROUPS:
        if len({p[4] for p in parts}) >= need or not spare:
            return
        name = spare.pop(0)
        for p in parts:
            if fnmatch.fnmatch(p[0], pattern):
                p[4] = name


def placeholder_props(parts, rig, unit, slot):
    """One box per prop of prompts/<unit>/props.json that no part stands for yet, at the middle of the
    prop's bone and as long as the middle of its extent bracket: the preflight's props_present holds,
    and the author, who sees the props sheet, moves it where the prop is. (Massing reads silhouettes; a
    prop's place is not in them.)"""
    props = preflight.load_props(unit)
    if not props:
        return []
    boxes = {id(p): preflight.bbox(p) for p in parts}
    height = max(b[1][1] for b in boxes.values())
    table = {name: (head, tail) for name, _, head, tail in RF.FAMILIES[rig]}
    out = []
    for name in preflight.props_missing(parts, boxes, height, props):
        prop = next(p for p in props if p["name"] == name)
        head, tail = table[prop["bones"][0]]
        size = sum(prop["extent"]) / 2 * height
        out.append([prop["bones"][0], "box", [r3(size), r3(0.6 * size), r3(0.6 * size)],
                    [r3((head[i] + tail[i]) / 2) for i in range(3)], slot, {"asym": True}])
    return out


def build(sheet, rig, race="", palette_sheet=None):
    """The pre-spec dict for `sheet` and rig family, or None for a family without a massing."""
    if rig not in FAMILIES:
        return None
    palette, names, centres = palette_of(palette_sheet or sheet, race, rig)
    H = RF.top(rig)
    pan = SIL.concept_panels(palette_sheet or sheet)["front"]
    fv = View(pan, H)
    rgb = SIL.read_rgba(palette_sheet or sheet, 768)[..., :3].astype(float) / 255.0
    labels = SIL.zone_labels(rgb, pan, centres)

    def labels_for(y0, y1, x0, x1):
        return names[min(zone_slot(labels, fv, y0, y1, x0, x1), len(centres) - 1)]

    parts = []
    for sides in ((LEG_SIDES, 8, 10) if rig != "biped" else (SIDES, 10, 12)):   # more sides until the pre-spec clears the class floor
        parts = biped(sheet, H, labels_for, sides) if rig == "biped" else spider(sheet, rig, labels_for, sides)
        if sum(preflight.part_tris(p) for p in parts) >= MIN_TRIS:
            break
    parts += placeholder_props(parts, rig, pathlib.Path(sheet).parent.name, names[-1])
    ensure_slots(parts, names)
    return {"palette": palette, "parts": parts, "rig": rig}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet", type=pathlib.Path)
    ap.add_argument("rig")
    ap.add_argument("out", type=pathlib.Path)
    ap.add_argument("--race", default="")
    ap.add_argument("--palette-sheet", type=pathlib.Path, default=None)
    a = ap.parse_args()
    if a.rig in RF.SPIDERS:        # the pipeline does this in set_rig; standalone, scale the rig by the sheet here
        RF.scale_spider(a.rig, SIL.measure_spider(a.sheet))
    spec = build(a.sheet, a.rig, a.race, a.palette_sheet)
    a.out.write_text(json.dumps(spec, indent=2))
    print(f"{len(spec['parts'])} parts -> {a.out}")


if __name__ == "__main__":
    main()
