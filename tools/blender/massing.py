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

FAMILIES = ("biped", "spider", "spider_high", "quadruped", "wyrm", "drake")
# frustum stacks follow the sheet's depth centre per slice; a lathe cannot (its axis is straight), and
# measured alone it lost 0.03-0.06 on left/top/bottom (n01X) with no gain on the spider (2026-10-27).
# LATHE_MASSING flips head/torso/pelvis/shell to the lathe emitters for a one-surface look.
LATHE_MASSING = False
# MEASURED_JOINTS puts the knee and the elbow where the sheet's width step is (silhouette.joint_measures) instead
# of midway: n01X +0.002 mean IoU, n005 -0.004 (2026-10-28, PIPELINE 22.L4-6), so it stays off.
MEASURED_JOINTS = False
KIND_FOR = {"head": "frustum", "torso": "frustum", "pelvis": "frustum", "foot": "frustum", "hand": "frustum",
            "arm": "prism", "leg": "prism", "shell": "frustum", "tail": "chain", "neck": "chain",
            # quadruped, wyrm, drake (22.L4-4b): a brick is a frustum in a z-slab, the wing a plate on the side panel's blob
            "trunk": "slab", "paw": "slab", "snout": "prism", "leg4": "limb", "wing": "plate", "spine": "chain"}
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
DEFAULT_SURFACE = {"biped": "cloth", "spider": "chitin", "spider_high": "chitin", "quadruped": "fur", "wyrm": "scales",
                   "drake": "scales"}
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


def _chain_run(role, bone, slot, g):  # ponytail: round rings only; an elliptical trunk needs a lathe on its side, add when a sheet needs it
    """One chain along the rig bones from `bone` (g["bones"] of them): the radius at each joint is
    g["half"](joint), the sheet's half width there (metres). PIPELINE 22.L4-1; the tails, necks and bodies of
    the quadruped, wyrm and drake (22.L4-4b) call it."""
    radii = [r3(max(g["half"](j), 0.02)) for j in lathe_limb.chain_joints(bone, g["bones"])]
    return [[bone, "chain", radii, [0, 0, 0], slot,
             {"bones": g["bones"], "sides": g.get("sides", CHAIN_SIDES), "profile_axis": "left"}]]


def _brick(role, bone, slot, g):
    """One frustum, w x h x d at g["at"], no taper: a z-slab of a body seen from the side and from above."""
    return [[bone, "frustum", [r3(g["w"]), r3(g["h"]), r3(g["d"])], [r3(v) for v in g["at"]], slot, {"top": [1.0, 1.0], "shift": [0, 0]}]]


def _limb_leg(role, bone, slot, g):
    """One limb from g["a"] to g["b"], radii g["r"] = (top, knee, base), the knee halfway."""
    return [[bone, "limb", [r3(v) for v in g["r"]], [0, 0, 0], slot,
             {"from": [r3(v) for v in g["a"]], "to": [r3(v) for v in g["b"]], "sides": g.get("sides", SIDES), "knee": [0.5, 0, 0]}]]


def _plate_wing(role, bone, slot, g):
    """One plate on the side panel's axis: dims (w, h, t), centre g["at"], profile g["profile"], turned g["rot"] about forward."""
    return [[bone, "plate", [r3(v) for v in g["dims"]], [r3(v) for v in g["at"]], slot,
             {"axis": "left", "profile": g["profile"], "rot": [0, 0, r3(g["rot"])], "bevel": g.get("bevel", 0.0)}]]


EMIT = {"frustum": _frustum_stack, "prism": _prism_limb, "lathe": _lathe_body, "chain": _chain_run,
        "slab": _brick, "limb": _limb_leg, "plate": _plate_wing}


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


def joint_between(y, lo, hi, share=0.15):
    """The measured joint height `y` kept `share` of the span lo..hi inside it (a joint on a bone's end
    leaves a zero-length bone); the midpoint when the sheet does not show it."""
    if y is None:
        return (lo + hi) / 2
    return min(max(y, lo + share * (hi - lo)), hi - share * (hi - lo))


def arm_geometry(front, H, y_sh, y_fist, reach, y_elbow=None):
    """(shoulder, elbow, wrist, r_upper, r_lower) of the +x arm. Where the arm hangs free of the torso
    (three runs in a row) its centre line is the middle of the outer run and its radius half that run;
    where it touches the torso, the outer edge of the front view inset by the radius. The elbow stays
    inside `reach` (metres from the centre line, the arm's own outer edge): preflight's shoulder_span
    reads the box of every part that touches the shoulder band, so a slanted upper arm must not lean out
    past the sheet's shoulders."""
    top = y_sh - 0.05 * H
    wrist = y_fist + 2.1 * ARM_HAND * H          # y_fist is the bottom of the fist: the hand fills the last two radii
    mid = joint_between(y_elbow, wrist, top)

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


def leg_geometry(front, left, H, y_top, bh, y_knee=None):
    """(hip, knee, ankle, r_thigh, r_shin) of the +x leg: the run nearest the ankle's own x in the
    front view (the arms hang outside, the pelvis inside), z-centred on the side view's row centre.
    A run wider than a fifth of H is torso or arm, not leg: the ankle's x and width stand in."""
    base = nearest_run(front, 1.3 * bh, 0.2 * H) or (0.2 * H, 0.1 * H)
    knee_y = joint_between(y_knee, bh, y_top)

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
            "pelvis": y_hip + 0.22 * (y_neck - y_hip), "boot": max(m["boot_height"] * H, 0.05 * H),
            **{joint: m[key] * H if MEASURED_JOINTS and key in m else None for joint, key in (("knee", "knee_h"), ("elbow", "elbow_h"))}}


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
    sh, el, wr, r_up, r_lo = arm_geometry(front, H, lm["shoulder"], lm["fist"], reach, lm["elbow"])
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
    hip, knee, ankle, r_th, r_sh, base = leg_geometry(front, side, H, lm["hip"] + 0.06 * H, lm["boot"], lm["knee"])
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


# ---- parts.json (PIPELINE 23.L5-2): one piece per semantic part, from the part's 3D box

PARTS_FILE = "parts.json"
PARTS_MASSING = False      # read refs/<id>/parts.json by default (see build)
PROP_LATHE = ("tank", "cylinder", "bottle", "canister", "barrel")   # a prop named so is a lathe, any other a box
LATHE_ROLES = ("head", "mask")
# An arm as ONE limb (elbow from joints) makes preflight's shoulder_span/fist_span read the whole arm's box in the
# shoulder band (n005: 0.79 vs the sheet's 0.46, 2026-10-27, PIPELINE 23.L5-2), so arms stay two prisms joined at
# the elbow; flip to try the limb.
ARM_LIMB = False
RING_ROWS = 6            # profile samples of a lathe read from the sheet inside the part's box


def load_parts(sheet):
    """refs/<id>/parts.json next to the sheet (L5-1's contract), or None: the band massing stays."""
    path = pathlib.Path(sheet).parent / PARTS_FILE
    return json.loads(path.read_text()) if path.exists() else None


def box_dims(part):
    """(size, centre) of the part's box3d in spec metres."""
    lo, hi = part["box3d"]
    return [hi[i] - lo[i] for i in range(3)], [(hi[i] + lo[i]) / 2 for i in range(3)]


def window_width(view, y, c0, c1, e):
    """Metres between the first and last figure pixel of the rows around y, inside the columns c0..c1."""
    sl = view.rows(y - e, y + e)
    cols = np.nonzero(view.mask[sl, max(int(c0), 0):max(int(c1), 0) + 1].any(axis=0))[0]
    return (cols.max() - cols.min() + 1) * view.s if len(cols) else 0.0


def box_profile(part, front, side):
    """Lathe profile (RING_ROWS radii, bottom to top, fraction of the box's width) read from the sheet inside
    the box: the front view's row widths between the box's x range, the left view's (z range) for a part the
    body hides in front (a prop)."""
    size, ctr = box_dims(part)
    lo, hi = part["box3d"]
    use_side = part.get("prop") or size[2] > 1.5 * size[0]
    if use_side:
        v, a, full = side.v, sorted((side.zero + side.sign * lo[2] / side.v.s, side.zero + side.sign * hi[2] / side.v.s)), size[2]
    else:
        v, a, full = front, (front.cx + lo[0] / front.s, front.cx + hi[0] / front.s), size[0]
    e = EDGE * v.n * v.s
    ys = np.linspace(lo[1], hi[1], RING_ROWS + 2)[1:-1]
    return [r3(float(np.clip(window_width(v, y, a[0], a[1], e) / max(full, 1e-3), 0.25, 1.0))) for y in ys]


def lathe_part(part, slot, front, side, sides):
    """A head, a mask or a tank: a lathe in the part's box (x radius = half its width, squash = width / depth),
    hexagonal like the band massing's head: an octagonal tank tips budget_split (legs under 19 %)."""
    size, ctr = box_dims(part)
    return [[part["bone"], "lathe", [r3(size[0] / 2), r3(size[1])], [r3(c) for c in ctr], slot,
             {"profile": box_profile(part, front, side), "squash": r3(float(np.clip(size[0] / max(size[2], 1e-3), 0.5, 2.0))),
              "sides": LATHE_SIDES["head"]}]]


def stack_part(part, slot, front, side, fist):
    """Torso or pelvis: the band stack, but every width, depth and centre is cut to the part's box."""
    (wx, h, wz), ctr = box_dims(part)
    lo, hi = part["box3d"]
    g = stack_geometry(front, side, lo[1], hi[1], torso=fist)
    w, d, zc = g["w"], g["d"], g["zc"]
    g["w"] = lambda y: min(w(y), wx)
    g["d"] = lambda y: min(d(y), wz)
    g["zc"] = lambda y: float(np.clip(zc(y), lo[2] + g["d"](y) / 2, hi[2] - g["d"](y) / 2))
    g["xc"] = ctr[0]
    return emit(part["role"], part["bone"], slot, g)


def joint_xyz(doc, name, tag):
    """The joint `name` of side `tag`, the other side's mirrored when only that one is listed; None without."""
    j = doc["joints"]
    if f"{name}.{tag}" in j:
        return j[f"{name}.{tag}"]["xyz"]
    other = j.get(f"{name}.{'R' if tag == 'L' else 'L'}")
    return [-other["xyz"][0], other["xyz"][1], other["xyz"][2]] if other else None


def prism_arm(part, slot, doc, sides, reach):
    """An arm as the band massing draws it (upper arm and forearm prisms), but through the joints of parts.json.
    Shoulder and elbow stay `reach` metres from the centre line at the arm's outer edge (as arm_geometry does:
    preflight's shoulder_span reads the box of every part in the shoulder band)."""
    tag = part["bone"].split(".")[-1]
    a, k, b = (joint_xyz(doc, n, tag) for n in ("shoulder", "elbow", "wrist"))
    if None in (a, k, b):
        return []
    size, _ = box_dims(part)
    r = float(np.clip(min(size[0], size[2]) / 2, 0.02, 0.4))
    cap = lambda p: [math.copysign(min(abs(p[0]), reach - r), p[0]), p[1], p[2]]   # noqa: E731
    a, k = cap(a), cap(k)
    return (emit("arm", f"arm.{tag}", slot, {"a": a, "b": k, "r": (1.1 * r, r), "sides": sides})
            + emit("arm", f"forearm.{tag}", slot, {"a": k, "b": b, "r": (r, 1.1 * r), "sides": sides}))


def limb_part(part, slot, doc, sides, names):
    """An arm or a leg: one limb from the first joint to the last with the knee at the middle one (the elbow
    and the knee of parts.json), radius = half the thinner of the box's x and z."""
    tag = part["bone"].split(".")[-1]
    a, k, b = (joint_xyz(doc, n, tag) for n in names)
    if None in (a, k, b):
        return []
    size, _ = box_dims(part)
    r = float(np.clip(min(size[0], size[2]) / 2, 0.02, 0.4))
    ab = [b[i] - a[i] for i in range(3)]
    f = float(np.clip(sum((k[i] - a[i]) * ab[i] for i in range(3)) / max(sum(v * v for v in ab), 1e-6), 0.2, 0.8))
    off = [k[i] - a[i] - f * ab[i] for i in range(3)]
    return [[part["bone"], "limb", [r3(1.05 * r), r3(0.95 * r), r3(r)], [0, 0, 0], slot,
             {"from": [r3(v) for v in a], "to": [r3(v) for v in b], "knee": [r3(f), r3(off[0]), r3(off[2]), r3(off[1])],
              "sides": min(sides, lathe_limb.SIDES_RANGE[1])}]]


def block_part(part, slot):
    """A foot, a hand or a prop that is no lathe: one frustum (feet and hands) or box in the part's box."""
    size, ctr = box_dims(part)
    bone = part["bone"].replace("hand.", "forearm.")     # a prop held in the hand rides the forearm bone
    if part.get("prop"):
        return [[bone, "box", [r3(v) for v in size], [r3(c) for c in ctr], slot, {"asym": True}]]
    return [[bone, "frustum", [r3(v) for v in size], [r3(c) for c in ctr], slot,
             {"top": [0.9, 0.8], "shift": [0, 0]} if part["role"] == "foot" else {"top": [1.0, 1.0], "shift": [0, 0]}]]


def part_slot(part, palette, labels_for):
    """The palette slot whose colour is nearest the part's zone; the front view's dominant zone in its box without one."""
    if part.get("zone"):
        rgb = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)])   # noqa: E731
        return min(palette, key=lambda n: np.abs(rgb(palette[n]["color"]) - rgb(part["zone"])).sum())
    lo, hi = part["box3d"]
    return labels_for(lo[1], hi[1], lo[0], hi[0])


def is_lathe(part):
    """A head, a mask, or a prop whose name says it is a cylinder (tank, bottle...)."""
    if part["role"] in LATHE_ROLES:
        return True
    return bool(part.get("prop")) and any(w in part["name"] for w in PROP_LATHE)


def parts_biped(doc, front, side, palette, labels_for, sides, reach=9.0):
    """The pre-spec parts of a biped from parts.json, in the order of the file (a part with a role this
    massing does not know is skipped)."""
    fist = min((j["xyz"][1] for n, j in doc["joints"].items() if n.startswith("wrist")), default=0.0)
    out = []
    for part in doc["parts"]:
        if not part.get("box3d"):        # segment_sheet leaves a prop seen in one view without a box
            continue
        slot, role = part_slot(part, palette, labels_for), part["role"]
        if is_lathe(part):
            out += lathe_part(part, slot, front, side, sides)
        elif role in ("torso", "pelvis"):
            out += stack_part(part, slot, front, side, fist)
        elif role == "arm":
            out += (limb_part(part, slot, doc, sides, ("shoulder", "elbow", "wrist")) if ARM_LIMB
                    else prism_arm(part, slot, doc, sides, reach))
        elif role == "leg":
            out += limb_part(part, slot, doc, sides, ("hip", "knee", "ankle"))
        elif role in ("foot", "hand", "prop"):
            out += block_part(part, slot)
    return out


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
SLOT_GROUPS_FOR = {"quadruped": ("head", "leg?.lower", "tail.1", "leg?.upper"), "wyrm": ("head", "wing?.lower", "wing?.upper"),
                   "drake": ("head", "wing?.lower", "tail.*", "leg?.lower")}


def ensure_slots(parts, names, need=3, groups=SLOT_GROUPS):
    """The preflight wants `need` materials in use: when the dominant zones leave fewer, the parts of the
    first SLOT_GROUPS hand the colours no part took (a sheet of one dark colour: every part is zone 1)."""
    spare = [n for n in names if n not in {p[4] for p in parts}]
    for pattern in groups:
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


def parts_prespec(sheet, doc, H, palette, labels_for, sides):
    """The biped parts of parts.json, or None when they leave a required bone without a part (the band
    massing then stands in: a half-written parts.json must not give a half model)."""
    from silhouette import concept_panels, measure
    panels = concept_panels(sheet)
    front, side = View(panels["front"], H), side_of(panels["left"], H)
    front.recentre(0.0, 0.08 * H)
    reach = REACH * measure(sheet)["shoulder_span"] * H / 2
    parts = parts_biped(doc, front, side, palette, labels_for, sides, reach)
    covered = {p[0] for p in parts} | {b for p in parts if p[1] == "limb" for b in lathe_limb.limb_bones(p[0], RF.required("biped")) or ()}
    missing = RF.required("biped") - covered
    if missing:
        print(f"massing: parts.json leaves {sorted(missing)} without a part, using the band massing")
        return None
    return parts


# ---- quadruped, wyrm, drake (PIPELINE 22.L4-4b)

DETAIL = ((6, 0.0), (8, 0.0), (8, 0.15))   # (sides, plate bevel) tried in order until the pre-spec clears the class floor
TRUNK_SLABS = 8          # bricks along the trunk (one frustum each: the side view's top and bottom line, the top view's width)
HEAD_SLABS = 4
WING_OVERLAP = 0.08      # the two plates of a wing overlap by this share of its height


class Scaled:
    """The side, front and top panels of a quadruped, wyrm or drake sheet in rig metres (the rig was scaled by `m`):
    x runs from the snout, z = (x0 - x) * H, y up."""

    def __init__(self, sheet, family, m, labels_for):
        panels = {k: SIL._crop(v) for k, v in SIL.concept_panels(sheet).items()}
        self.m, self.family, self.labels_for = m, family, labels_for
        self.left, self.line = panels["left"], m["line"]
        self.h = self.left.shape[0]
        self.H = RF.top(family)
        self.x0 = sum(m["trunk"]) / 2 if "trunk" in m else m["len"] / 2
        self.front = View(panels["front"], self.H)
        top = panels["top"]
        self.top = np.rot90(top, -1) if top.shape[1] > 1.2 * top.shape[0] else top    # n010's top is drawn head left
        self.bones = {n: (h, t) for n, _, h, t in RF.FAMILIES[family]}
        self.opened = SIL.thin_opened(self.left)

    def z(self, x):
        return (self.x0 - x) * self.H

    def y_range(self, mask, xa, xb):
        """(bottom, top) in metres of `mask` over the columns x = xa..xb (fractions of H from the snout)."""
        rows = np.nonzero(mask[:, int(xa * self.h):max(int(xb * self.h), int(xa * self.h) + 1)].any(axis=1))[0]
        return (self.h - rows.max() - 1) / self.h * self.H, (self.h - rows.min()) / self.h * self.H

    def top_half(self, xa, xb, opened=True):
        """Mean half width in metres of the top view between x = xa..xb, None when the panel has no rows there."""
        mask = SIL.thin_opened(self.top) if opened else self.top
        k = mask.shape[0] / self.m["len"]
        halves = [(np.ptp(np.nonzero(row)[0]) + 1) / 2 for row in mask[int(xa * k):max(int(xb * k), int(xa * k) + 1)] if row.any()]
        return float(np.mean(halves)) / k * self.H if halves else None

    def line_y(self, x):
        """The centre line's height in metres at x (fractions of H from the snout)."""
        return float(np.interp(x, [p[0] for p in self.line], [p[1] for p in self.line])) * self.H

    def radius_at(self, joint):
        """Radius in metres of the centre line's point nearest the joint (x, y, z)."""
        best = min(self.line, key=lambda p: math.hypot(self.z(p[0]) - joint[2], p[1] * self.H - joint[1]))
        return best[2] * self.H

    def chain(self, role, bone, n, sides):
        return emit(role, bone, self.labels_for(0.0, self.H, -0.3 * self.H, 0.3 * self.H), {"bones": n, "half": lambda j: CHAIN_FAT * self.radius_at(j), "sides": sides})


def _slabs(S, role, bone_of, xa, xb, n, mask, winged, opened_top=True):
    """n bricks from x = xa to xb: height from the side panel's `mask` in the brick's columns, width from the top
    view (the front view for a winged body, whose wings cover the top line: then the brick is as tall above the centre line as the belly is below)."""
    parts = []
    for a, b in zip(np.linspace(xa, xb, n + 1)[:-1], np.linspace(xa, xb, n + 1)[1:]):
        ybot, ytop = S.y_range(mask, a, b)
        front = S.front.half(ybot, ybot + 0.6 * (ytop - ybot))
        half = WIDTH * (front if winged else min(S.top_half(a, b, opened_top) or front, front))
        if winged:
            ytop = min(ytop, 2 * S.line_y((a + b) / 2) - ybot)    # the wing hides the back line: the trunk is as tall as the belly is far below the line
        slot = S.labels_for(ybot, ytop, -half, half)
        parts += emit(role, bone_of((a + b) / 2), slot, {"w": 2 * half, "h": ytop - ybot + JOINT * S.H, "d": (b - a) * S.H * 1.12,
                                                        "at": (0.0, (ybot + ytop) / 2, S.z((a + b) / 2))})
    return parts


def _paws_and_legs(S, sides):
    """Four limbs along the rig's leg bones and a paw brick under each."""
    r = S.m["legs"]["r"] * S.H
    parts = []
    for i in range(1, 5):
        (hip, _), (_, foot) = S.bones[f"leg{i}.upper"], S.bones[f"leg{i}.lower"]
        slot = S.labels_for(0.0, hip[1], min(hip[0], 0) - 0.1 * S.H, max(hip[0], 0) + 0.1 * S.H)
        parts += emit("leg4", f"leg{i}.upper", slot, {"a": hip, "b": foot, "r": (1.5 * r, 1.05 * r, 0.8 * r), "sides": sides})
        parts += emit("paw", f"leg{i}.lower", slot, {"w": 2.4 * r, "h": 0.06 * S.H, "d": 3.4 * r, "at": (foot[0], 0.03 * S.H, foot[2] + r)})
    return parts


CHAIN_FAT = 1.1          # the side panel's radius under-reads the body's width in the front panel (n00H: 0.082 against 0.095 H)
WIDTH = 0.9              # a brick is a box: its outline is as wide as the sheet's widest row, the sheet's body tapers; 0.9 measured on n017
BODY_DEPTH = 0.06        # ... and at least this far (H) below the wing's lowest pixel
BODY_REACH = 0.4         # the inner wing plate ends this many radii above the centre line
WING_FAT = 1.3          # blade thickness over the wing's mean row width (the wing flares toward its base)
HEAD_PIECES = 3          # tapered tubes along a prism head: a skull, a muzzle, a snout


def _head_prism(S, sides):
    """The head bone as HEAD_PIECES tapered tubes: the line's radius at the bone's base, 0.35 of it at the tip."""
    head, tip = S.bones["head"]
    r = S.radius_at(head)
    slot = S.labels_for(head[1] - r, head[1] + r, -r, r)
    at = lambda f: tuple(a + f * (b - a) for a, b in zip(head, tip))   # noqa: E731
    k = HEAD_PIECES
    return [p for i in range(k) for p in emit("snout", "head", slot, {
        "a": at(i / k), "b": at((i + 1) / k), "r": (r * (1.15 - 0.8 * i / k), r * (1.15 - 0.8 * (i + 1) / k)), "sides": sides})]


def _wing_plates(S, bevel):
    """Both wings as blades: the side panel's wing blob is cut in two halves (upper bone, lower bone), each a plate in
    the (z, y) plane with that outline, turned about forward to lean out like the front panel's spar (root to tip).
    The inner half gets one more vertex, inside the body at the line point nearest the wing's foot, so it meets the body."""
    w = S.m["wing"]
    blob = SIL.wing_mask(S.left, S.line)
    rows = np.nonzero(blob.any(axis=1))[0]
    r0, r1 = rows.min(), rows.max() + 1
    mid = (r0 + r1) / 2
    (rx, ry), (tx, ty) = (w["root_x"], w["root_y"]), w["tip"]
    theta = math.degrees(math.atan2(tx - rx, ty - ry))
    thick = float(np.clip(WING_FAT * w["width"] * math.cos(math.radians(theta)), 0.02, 0.25)) * S.H    # the row width is horizontal, the plate's thickness is across the blade
    xs = np.nonzero(blob.any(axis=0))[0]
    ax, ay, ar = min(S.line, key=lambda p: math.hypot(p[0] - (xs.min() + xs.max()) / 2 / S.h, p[1] - (S.h - r1) / S.h))
    foot = (ax * S.h, max((1 - ay - BODY_REACH * ar) * S.h, r1 + BODY_DEPTH * S.h))       # (col, row) in the side panel
    parts = []
    for name, (a, b) in (("upper", (mid - WING_OVERLAP * (r1 - r0), r1)), ("lower", (r0, mid + WING_OVERLAP * (r1 - r0)))):
        part = np.zeros_like(blob)
        part[int(a):int(b)] = blob[int(a):int(b)]
        poly, box = _blade(part, foot if name == "upper" else None)
        if poly is None:
            continue
        (c0, c1), (q0, q1) = box
        top, bottom = (S.h - q0) / S.h * S.H, (S.h - q1) / S.h * S.H
        yc, length = (top + bottom) / 2, top - bottom
        xc = max((rx + (yc / S.H - ry) / (ty - ry) * (tx - rx)) * S.H, 0.0)
        if name == "upper":
            xc = max(xc - 0.5 * thick, 0.0)      # the inner plate's face reaches into the body's tube
        for n, side in ((1, 1), (2, -1)):
            slot = S.labels_for(yc - length / 2, yc + length / 2, 0.0, side * S.H)
            parts += emit("wing", f"wing{n}.{name}", slot,
                          {"dims": ((c1 - c0) / S.h * S.H, length / math.cos(math.radians(theta)), thick),
                           "at": (side * xc, yc, S.z((c0 + c1) / 2 / S.h)), "profile": poly, "rot": -side * theta,
                           "bevel": bevel})
    return parts


def _blade(mask, spike=None):
    """([[u, v]] polygon of at most 8 points in 0-1 of its box, u toward the head as the plate's z, v up) and the
    ((c0, c1), (r0, r1)) pixel box (the box grows to hold `spike`, a (col, row) vertex put after the lowest one);
    (None, None) for an empty mask."""
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return None, None
    c0, c1, r0, r1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    hs = r1 - r0
    poly = SIL.outline(mask[r0:r1, c0:c1], eps=0.004, limit=7 if spike else 8)
    pts = [(c0 + (c1 - c0 - 1) / 2 + x * hs, r1 - 1 - y * hs) for x, y in poly]
    if spike:
        low = max(range(len(pts)), key=lambda i: pts[i][1])
        pts.insert(low + 1, spike)
        c0, c1, r1 = min(c0, spike[0]), max(c1, spike[0]), max(r1, spike[1])
    px, py = np.array(pts).T
    u = 1 - (px - c0) / max(c1 - c0, 1e-6)
    v = (r1 - py) / max(r1 - r0, 1e-6)
    return [[r3(min(max(a, 0), 1)), r3(min(max(b, 0), 1))] for a, b in zip(u, v)][::-1], ((c0, c1), (r0, r1))


def _quadruped_parts(S, detail):
    """Trunk bricks, head bricks (or a prism for a drake), legs and paws, tail and neck chains: a quadruped or drake."""
    m, winged, (sides, bevel) = S.m, "wing" in S.m, detail
    x0, x1 = m["trunk"]
    pad = 0.4 * max(p[2] for p in S.line)
    mid = (x0 + x1) / 2
    parts = _slabs(S, "trunk", lambda x: "spine.2" if x < mid else "spine.1", x0 - pad, x1 + pad, TRUNK_SLABS, S.opened, winged)
    parts += _paws_and_legs(S, sides)
    if winged:
        parts += _head_prism(S, sides) + S.chain("neck", "neck.1", 2, sides) + S.chain("tail", "tail.1", 3, sides) + _wing_plates(S, bevel)
    else:
        parts += _slabs(S, "trunk", lambda x: "head", 0.0, x0 - pad, HEAD_SLABS, S.left, False, opened_top=False)
        parts += S.chain("tail", "tail.1", 2, sides)
    return parts


def _wyrm_parts(S, detail):
    """The body as one chain over spine.1..6, the head as a prism, two wing blades."""
    sides, bevel = detail
    return S.chain("spine", "spine.1", RF.WYRM_SPINES, sides) + _head_prism(S, sides) + _wing_plates(S, bevel)


def scaled(sheet, rig, m, labels_for, detail):
    """Parts of the quadruped, wyrm or drake pre-spec (the rig was scaled by the measures `m`); detail = (sides, bevel)."""
    S = Scaled(sheet, rig, m, labels_for)
    return _wyrm_parts(S, detail) if rig == "wyrm" else _quadruped_parts(S, detail)


def build(sheet, rig, race="", palette_sheet=None, parts=None):
    """The pre-spec dict for `sheet` and rig family, or None for a family without a massing. A biped whose
    refs/<id>/parts.json exists is built from its parts (`parts`: a parts.json dict instead, or False for the band massing)."""
    if rig not in FAMILIES:
        return None
    palette, names, centres = palette_of(palette_sheet or sheet, race, rig)
    measure = SIL.measure_rig(rig, sheet) if rig in RF.SCALABLE else None
    RF.scale_rig(rig, measure)
    lathe_limb.set_rig(rig)
    H = RF.top(rig)
    pan = SIL.concept_panels(palette_sheet or sheet)["front"]
    fv = View(pan, H)
    rgb = SIL.read_rgba(palette_sheet or sheet, 768)[..., :3].astype(float) / 255.0
    labels = SIL.zone_labels(rgb, pan, centres)

    def labels_for(y0, y1, x0, x1):
        return names[min(zone_slot(labels, fv, y0, y1, x0, x1), len(centres) - 1)]

    # The parts massing is opt-in (PARTS_MASSING or an explicit `parts` dict): with the real
    # segment_sheet output it fails symmetry/fist_span/boot_height on the 4 bipeds (2026-10-28).
    auto = load_parts(sheet) if PARTS_MASSING else None
    doc = (auto if parts is None else parts) if rig == "biped" else None
    parts = []
    for sides in {"biped": (SIDES, 10, 12), "quadruped": DETAIL, "wyrm": DETAIL, "drake": DETAIL}.get(rig, (LEG_SIDES, 8, 10)):   # more sides until the pre-spec clears the class floor
        parts = (doc and parts_prespec(sheet, doc, H, palette, labels_for, sides)) or None
        doc = doc if parts else None
        if not parts:
            parts = (biped(sheet, H, labels_for, sides) if rig == "biped" else scaled(sheet, rig, measure, labels_for, sides)
                     if measure else spider(sheet, rig, labels_for, sides))
        if sum(preflight.part_tris(p) for p in parts) >= MIN_TRIS:
            break
    parts += placeholder_props(parts, rig, pathlib.Path(sheet).parent.name, names[-1])
    ensure_slots(parts, names, groups=SLOT_GROUPS_FOR.get(rig, SLOT_GROUPS))
    return {"palette": palette, "parts": parts, "rig": rig, **({"rig_measure": measure} if rig in RF.SCALABLE else {})}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet", type=pathlib.Path)
    ap.add_argument("rig")
    ap.add_argument("out", type=pathlib.Path)
    ap.add_argument("--race", default="")
    ap.add_argument("--palette-sheet", type=pathlib.Path, default=None)
    ap.add_argument("--no-parts", action="store_true", help="ignore refs/<id>/parts.json: the band massing")
    ap.add_argument("--parts", type=pathlib.Path, default=None, help="a parts.json other than the sheet's own")
    a = ap.parse_args()
    RF.scale_rig(a.rig, SIL.measure_rig(a.rig, a.sheet))     # the pipeline does this in set_rig; standalone, scale the rig by the sheet here
    spec = build(a.sheet, a.rig, a.race, a.palette_sheet,
                 False if a.no_parts else a.parts and json.loads(a.parts.read_text()))
    a.out.write_text(json.dumps(spec, indent=2))
    print(f"{len(spec['parts'])} parts -> {a.out}")


if __name__ == "__main__":
    main()
