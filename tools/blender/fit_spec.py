#!/usr/bin/env python3
"""Fit a spec's dims and positions to the approved sheet's silhouettes, before any Blender build.

    python3 tools/blender/fit_spec.py <spec.json> <approved sheet.jpg> <out.json>
        [--views front,left,back] [--kind mass] [--margin 0.02]

PIPELINE §19.D1. A numpy proxy of the build (every part's convex outline, projected on the
front/left/back cameras and normalised like silhouette.normalize) scores a spec in a few
milliseconds, so scipy can move dims (+-10 %) and `at` (+-0.03 H) of the parts that sit on the
failing height band, the way Sketch2Mesh refines parameters with a 2D contour Chamfer (Eq. 5),
touching only where the contour is wrong (Eq. 6). The preflight rules that held are a hard
constraint (Wiersma 2026: regularisers as constraints, not weights) and a part off the failing
band is frozen (MeshGPT 2024: keep what is already good). The proxy is a ranking signal, not the
verdict: spec_pipeline accepts the fitted spec only when the real clay build keeps every view
that passed (spec_pipeline --fit).

PIPELINE §21.F4 widens it: the objective also sees top/bottom/rts (projected with the tilt the run
chose, else the best of a sweep) and the sheet-turn.jpg 3/4 views when they exist; the parts of the
arms, legs and hood take a `rot` (+-20 deg); a part attached to its parent may move its dims by 20 %;
a small term keeps each part inside the sheet's colour zone of its material. `PARAMS` says which
extra continuous parameters each part kind has (extend it for a new kind).
"""
import argparse
import copy
import json
import math
import pathlib
import sys
import time

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_erosion, distance_transform_edt
from scipy.optimize import minimize
from scipy.spatial import ConvexHull, QhullError

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cut_hull  # noqa: E402
import lathe_limb  # noqa: E402
import preflight  # noqa: E402
import rig_families as RF  # noqa: E402
import silhouette  # noqa: E402
import views as V  # noqa: E402

FIT_VIEWS = ("front", "left", "back")
WIDE_VIEWS = ("front", "left", "back", "top", "bottom", "rts")     # the verdict's views (silhouette.GATES)
TURN_STEPS = (-20, -10, 0, 10, 20)   # degrees the azimuth of a sheet-turn panel is swept
ATTACHED_RANGE = 0.20   # a part connected to its parent may move its dims this far (PIPELINE 21.F4)
ROT_RANGE = 20.0        # degrees a `rot` axis may move
ROT_BONES = ("arm", "forearm", "hand", "thigh", "shin", "foot", "leg")   # bone name prefixes whose parts turn
ZONE_W = 0.1            # objective weight of the colour-zone term (1 - share of a part inside its zone)
MAX_SECONDS = 150.0     # wall-clock budget of one fit (the unit's budget is 3 min with the clay trials)
FAST_EVALS = 1500       # --fit-fast: the classic 3 views, no rot, no zones
CUT_BONES = ("spine", "pelvis", "body", "abdomen")
CUT_MAX = 3             # the DSL allows 3 cut parts per unit
DIMS_RANGE = 0.10       # a dim may move by this fraction (0.20 pulled limbs off their parents, PIPELINE 20.N12)
LEG_GROW = False        # spider legs may grow to the sheet's leg_w: off, n00U v6-r3 lost .002-.008 on 5 views (PIPELINE 21.F3)
AT_RANGE = 0.03         # `at` may move by this fraction of the height
PROFILE_RANGE = 0.15    # a lathe's profile radii and squash may move by this fraction (PIPELINE 21.F2)
KNEE_RANGE = 0.15       # a limb's knee fraction may move by this much, its dx/dz by AT_RANGE * height
LOOSE_W = 0.3           # objective cost of each part not connected to its parent (80 % boxes)
# bones whose parts keep their width and depth: the torso, and the hood (the widest part on the head)
NO_GROW = ("spine", "pelvis", "body", "abdomen")
HORIZONTAL = {"box": (0, 2), "frustum": (0, 2), "prism": (0, 1), "cyl": (0,), "dome": (0,), "lathe": (0,)}
CHAMFER_W = 1.0         # objective = (1 - IoU) + CHAMFER_W * chamfer, per view
EDGE_W = 0.1            # weight of the optional --fit-edges term (edge_term), per view mean
PENALTY = 10.0          # a preflight rule that held and breaks costs this much, plus 1 per rule
BAND_SHARE = 0.6        # failing band: rows whose error is this share of the worst row's
BAND_SMOOTH = 16        # rows of the moving average that smooths the error profile
MARGIN = 0.02          # fit views under gate + this: the proxy is within ~0.01 of the render (max 0.04)
MAX_EVALS = 4000        # scipy budget per fit (Powell, ~10 ms per evaluation)
SIDES = 12              # polygon count of a round part's outline
# canvas column of a point (x, y, z in the build's Blender axes, +z up) per camera
PROJECT = {"front": lambda p: (p[:, 0], p[:, 2]), "back": lambda p: (-p[:, 0], p[:, 2]),
           "left": lambda p: (-p[:, 1], p[:, 2])}
D = math.radians


def project(view, p, cam=None):
    """(u, v) of Blender-axes points p seen from `view`. `cam` is the swept camera: the tilt of
    top/bottom (views.camera), the (elevation, azimuth) of rts, the azimuth of a turn panel."""
    if view in PROJECT:
        return PROJECT[view](p)
    if view in V.TILTED:
        t = D(cam or 0)
        return p[:, 0], (p[:, 1] if view == "top" else -p[:, 1]) * math.cos(t) + p[:, 2] * math.sin(t)
    offset = V.rts_offset(*cam) if view == "rts" else V.rts_offset(0, cam)
    d = -np.asarray(offset) / np.linalg.norm(offset)
    right = np.cross(d, [0.0, 0.0, 1.0])
    right /= np.linalg.norm(right)
    return p @ right, p @ np.cross(right, d)


def cam_candidates(view):
    """The cameras a view's tilt sweep tries (None: a fixed view)."""
    if view in V.TILTED:
        return V.TILTS
    if view == "rts":
        return V.RTS
    return tuple(int(view[4:]) + s for s in TURN_STEPS) if view.startswith("turn") else None



# ---------------------------------------------------------------- the proxy
def spec_to_blender(p):
    """Spec (right, up, forward) -> Blender (x, y, z), as build_unit.bp."""
    return np.array([p[0], -p[2], p[1]], float)


def euler_matrix(ex, ey, ez):
    """Blender XYZ euler (radians): X is applied first, Z last."""
    (sx, cx), (sy, cy), (sz, cz) = ((math.sin(a), math.cos(a)) for a in (ex, ey, ez))
    return (np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
            @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
            @ np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]))


def box_corners(size):
    return np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]) * (np.asarray(size) / 2)


def ring_points(r0, r1, height, n=SIDES):
    """Two n-gons, radius r0 at z = -height/2 and r1 at +height/2."""
    a = np.arange(n) * 2 * math.pi / n
    return np.concatenate([np.stack([r0 * np.cos(a), r0 * np.sin(a), np.full(n, -height / 2)], 1),
                           np.stack([r1 * np.cos(a), r1 * np.sin(a), np.full(n, height / 2)], 1)])


def frustum_points(dims, top, shift):
    w, h, d = dims
    sx, sz = top
    dx, dz = shift
    lo = [(-w / 2, -d / 2, -h / 2), (w / 2, -d / 2, -h / 2), (w / 2, d / 2, -h / 2), (-w / 2, d / 2, -h / 2)]
    hi = [(-w / 2 * sx + dx, -d / 2 * sz + dz, h / 2), (w / 2 * sx + dx, -d / 2 * sz + dz, h / 2),
          (w / 2 * sx + dx, d / 2 * sz + dz, h / 2), (-w / 2 * sx + dx, d / 2 * sz + dz, h / 2)]
    return np.array(lo + hi)


def spec_rot(opts):
    """opts["rot"] as (right, up, forward) degrees: a bare number turns around forward."""
    return preflight.rot_euler(opts)


def disc_base(axis):
    """Rotation of a disc whose normal is local Z, for the build's axis names."""
    return euler_matrix(D(90), 0, 0) if axis == "fwd" else euler_matrix(0, D(90), 0) if axis == "side" else np.eye(3)


def track_z(d):
    """Rotation that points local +Z along d with local +Y towards world +Z (to_track_quat('Z','Y'))."""
    z = d / np.linalg.norm(d)
    up = np.array([0.0, 0.0, 1.0]) - z[2] * z
    y = up / np.linalg.norm(up) if np.linalg.norm(up) > 1e-6 else np.array([0.0, 1.0, 0.0])
    return np.stack([np.cross(y, z), y, z], 1)


def fitted_dims(kind, dims, a, b):
    """build_unit.fit_length: a from/to part is as long as its two joints are apart, plus 8 %."""
    length = float(np.linalg.norm(np.asarray(b) - np.asarray(a))) * 1.08
    if kind == "prism":
        return (dims[0], dims[1], length)
    if kind == "cyl":
        return (dims[0], length)
    return (dims[0], length, dims[2]) if kind in ("box", "frustum") else dims


def local_shape(kind, dims, opts):
    """(points, rotation matrix) of one part in its own frame, as build_part makes it."""
    rx, ry, rz = (D(v) for v in spec_rot(opts))
    euler = euler_matrix(rx, -rz, ry)
    if kind in ("prism", "dome"):
        if kind == "dome":
            dims = (dims[0], dims[0] * float(opts.get("top", 0.35)), dims[1])
        base = {"fwd": (D(90), 0, 0), "side": (0, D(90), 0)}.get(opts.get("axis", "up"), (0, 0, 0))
        pts = ring_points(dims[0], dims[1], dims[2], int(opts.get("sides", 8)))
        return scaled(pts, opts), euler_matrix(base[0] + rx, base[1] - rz, base[2] + ry + D(float(opts.get("spin", 0))))
    if kind == "frustum":
        pts = frustum_points(dims, opts.get("top", (1.0, 1.0)), opts.get("shift", (0.0, 0.0)))
        return scaled(pts, opts), euler_matrix(rx, -rz, ry + D(float(opts.get("spin", 0))))
    if kind == "cyl":
        up = opts.get("axis", "fwd") == "up"
        return ring_points(dims[0], dims[0], dims[1]), np.eye(3) if up else euler_matrix(D(90), 0, 0)
    if kind in ("wheel", "ring"):
        radius, half = (dims[0] + dims[1], dims[1]) if kind == "wheel" else (dims[0], dims[2] / 2)
        tilt = euler_matrix(D(float(opts.get("tilt", 0.0))), 0, 0)
        spin = euler_matrix(0, 0, D(float(opts.get("spin", 0.0)))) if kind == "ring" else np.eye(3)
        return ring_points(radius, radius, 2 * half), disc_base(opts.get("axis", "fwd" if kind == "wheel" else "up")) @ tilt @ spin
    return box_corners((dims[0], dims[2], dims[1])), euler        # box: bd(dims), and the unknown kinds


def scaled(pts, opts):
    sx, sy = (opts["scale"][0], opts["scale"][1]) if opts.get("scale") else (1.0, 1.0)
    return pts * np.array([sx, sy, 1.0])


def part_points(part):
    """World points (Blender axes) whose convex hull is the part's outline."""
    _, kind, dims, at, _, opts = part
    opts = opts or {}
    if kind in ("lathe", "limb"):
        rings = lathe_limb.lathe_rings(dims, at, opts) if kind == "lathe" else lathe_limb.limb_rings(dims, opts)
        pts = np.array([p for ring in rings for p in ring], float)
        return np.stack([pts[:, 0], -pts[:, 2], pts[:, 1]], 1)
    span = "from" in opts and "to" in opts
    if span:
        a, b = tuple(opts["from"]), tuple(opts["to"])
        at = tuple((a[i] + b[i]) / 2 for i in range(3))
        if opts.get("fit", True):
            dims = fitted_dims(kind, dims, a, b)
    pts, rot = local_shape(kind, dims, opts)
    if span and kind != "ring":
        d = spec_to_blender(b) - spec_to_blender(a)
        rot = track_z(d) if np.linalg.norm(d) > 1e-6 else rot
    return pts @ rot.T + spec_to_blender(at)


def hull2d(xy):
    """Vertices of the convex hull of 2D points (the bounding box when they are flat)."""
    try:
        return xy[ConvexHull(xy).vertices]
    except QhullError:
        lo, hi = xy.min(axis=0), xy.max(axis=0)
        return np.array([lo, [hi[0], lo[1]], hi, [lo[0], hi[1]]])


def canvas_of(outlines):
    """(lo, hi, scale, x0, y0): how silhouette.normalize lays a figure out in the canvas: cropped
    to its extent, as tall as the canvas allows, centred."""
    allp = np.concatenate(outlines)
    lo, hi = allp.min(axis=0), allp.max(axis=0)
    w, h = max(hi[0] - lo[0], 1e-6), max(hi[1] - lo[1], 1e-6)
    s = min(silhouette.CANVAS_H / h, silhouette.CANVAS_W / w)
    return lo, hi, s, (silhouette.CANVAS_W - w * s) / 2, (silhouette.CANVAS_H - h * s) / 2


def to_px(o, canvas):
    lo, hi, s, x0, y0 = canvas
    return np.stack([(o[:, 0] - lo[0]) * s + x0, (hi[1] - o[:, 1]) * s + y0], 1)


def raster(outlines):
    """Fill the outlines (model units, +v up) into the 256 x 384 canvas the way
    silhouette.normalize lays a figure out. Returns (mask, [(first row, last row) per outline])."""
    canvas = canvas_of(outlines)
    img = Image.new("L", (silhouette.CANVAS_W, silhouette.CANVAS_H), 0)
    draw, rows = ImageDraw.Draw(img), []
    for o in outlines:
        px = to_px(o, canvas)
        draw.polygon([tuple(p) for p in px], fill=255)
        rows.append((px[:, 1].min(), px[:, 1].max()))
    return np.asarray(img) > 0, rows


def edge_of(mask):
    return mask & ~binary_erosion(mask)


def edge_term(outlines, hard):
    """Optional fit term (--fit-edges, PIPELINE 21.F7): mean distance, in canvas heights, from each
    inner edge of the hard sheet (`hard`: bool canvas, silhouette.fit_canvas of silhouette.edges)
    to the nearest part outline of one view (`outlines`: model units, +v up) - did the model
    facet where the drawing does. Better of the two mirrors, like silhouette.variants. 0 without
    drawn edges. Same layout as raster() (kept apart so the fit objective can change freely)."""
    if not hard.any():
        return 0.0
    allp = np.concatenate(outlines)
    lo, hi = allp.min(axis=0), allp.max(axis=0)
    s = min(silhouette.CANVAS_H / max(hi[1] - lo[1], 1e-6), silhouette.CANVAS_W / max(hi[0] - lo[0], 1e-6))
    x0 = (silhouette.CANVAS_W - (hi[0] - lo[0]) * s) / 2
    y0 = (silhouette.CANVAS_H - (hi[1] - lo[1]) * s) / 2
    img = Image.new("L", (silhouette.CANVAS_W, silhouette.CANVAS_H), 0)
    draw = ImageDraw.Draw(img)
    for o in outlines:
        draw.polygon([((x - lo[0]) * s + x0, (hi[1] - y) * s + y0) for x, y in o], outline=255)
    lines = np.asarray(img) > 0
    return min(float(distance_transform_edt(~m)[hard].mean()) for m in (lines, np.fliplr(lines))) / silhouette.CANVAS_H


def hard_canvas_edges(hard, views):
    """{view: inner edges of the hard sheet's panel on the canvas} for edge_term."""
    panels = silhouette.concept_panels(hard)
    return {v: silhouette.fit_canvas(silhouette.edges(hard, panels[v]), panels[v]) for v in views if v in panels}


class Zones:
    """The sheet's colour zones per view (normalized label maps) and the zone each material belongs
    to: a part whose projection leaves the zone of its material is where the colour will not match."""

    def __init__(self, sheet, doc, views):
        names, centres, _ = silhouette.zone_palette(sheet)
        rgb = silhouette.read_rgba(sheet, 768)[..., :3] / 255.0
        panels = silhouette.concept_panels(sheet)
        self.labels = {v: silhouette.mode_filter(silhouette.normalize(
            silhouette.zone_labels(rgb, panels[v], centres, ink=True))) for v in views if v in panels}
        self.zone_of = {}
        for name, entry in (doc.get("palette") or {}).items():
            colour = str(entry.get("color", "") if isinstance(entry, dict) else entry).lstrip("#")
            if len(colour) == 6:
                self.zone_of[name] = int(silhouette.nearest(np.array([[int(colour[i:i + 2], 16) / 255
                                                                       for i in (0, 2, 4)]]), centres)[0])

    def share(self, view, outline, canvas, z, flipped):
        """Share of one part's projection inside zone z of the sheet."""
        px = to_px(outline, canvas)
        if flipped:
            px[:, 0] = silhouette.CANVAS_W - px[:, 0]
        x0, y0 = np.maximum(np.floor(px.min(axis=0)).astype(int), 0)
        x1, y1 = np.minimum(np.ceil(px.max(axis=0)).astype(int) + 1, (silhouette.CANVAS_W, silhouette.CANVAS_H))
        if x1 <= x0 or y1 <= y0:
            return 1.0
        img = Image.new("L", (x1 - x0, y1 - y0), 0)
        ImageDraw.Draw(img).polygon([(a - x0, b - y0) for a, b in px], fill=255)
        mask = np.asarray(img) > 0
        return float((mask & (self.labels[view][y0:y1, x0:x1] == z)).sum() / max(mask.sum(), 1))

    def term(self, parts, free, outs, flips):
        """1 - mean share, over the free parts that have a zone and the views that have labels."""
        got = [self.share(v, outs[v][i], canvas_of(outs[v]), z, flips[v])
               for v in self.labels if v in outs for i in free
               if (z := self.zone_of.get(parts[i][4]))]
        return 1.0 - sum(got) / len(got) if got else 0.0


class Proxy:
    """Scores a parts list against the concept masks of the views being fitted."""

    def __init__(self, concept, views, cams=None, zones=None, hard=None):
        self.concept, self.views, self.cams, self.zones, self.hard = concept, views, cams or {}, zones, hard
        # the concept's contour and its distance map never change: silhouette.chamfer, halved
        self.edge = {v: edge_of(m) for v, m in concept.items()}
        self.dist = {v: distance_transform_edt(~e) for v, e in self.edge.items()}

    def hulls(self, world, views=None):
        """{view: outline} of one part's world points."""
        return {v: hull2d(np.stack(project(v, world, self.cams.get(v)), 1)) for v in views or self.views}

    def outlines(self, parts, cache=None):
        """{view: [outline per part]}; `cache` {part index: hulls()} spares the frozen parts."""
        hulls = [cache[i] if cache and i in cache else self.hulls(part_points(p)) for i, p in enumerate(parts)]
        return {v: [h[v] for h in hulls] for v in self.views}

    def masks(self, parts, cache=None):
        """{view: (mask, row span per part)}"""
        return {v: raster(o) for v, o in self.outlines(parts, cache).items()}

    def best_variant(self, view, mask):
        """(mask, IoU, flipped): the better of the mask and its mirror, like silhouette.variants."""
        options = silhouette.variants(mask, view)
        scores = [silhouette.iou(self.concept[view], m) for m in options]
        k = int(np.argmax(scores))
        return options[k], scores[k], k == 1

    def view_score(self, view, mask):
        """(IoU, chamfer, flipped) against the concept."""
        best, score, flipped = self.best_variant(view, mask)
        if not best.any():
            return 0.0, 1.0, False
        edge = edge_of(best)
        chamfer = (self.dist[view][edge].mean() + distance_transform_edt(~edge)[self.edge[view]].mean()) / 2
        return score, float(chamfer / best.shape[0]), flipped

    def ious(self, parts, cache=None):
        return {v: round(self.view_score(v, m)[0], 4) for v, (m, _) in self.masks(parts, cache).items()}

    def loss(self, parts, cache=None, free=()):
        outs = self.outlines(parts, cache)
        scores = {v: self.view_score(v, raster(o)[0]) for v, o in outs.items()}
        total = sum((1 - i) + CHAMFER_W * c for i, c, _ in scores.values()) / len(scores)
        if self.zones and free:
            total += ZONE_W * self.zones.term(parts, free, outs, {v: f for v, (_, _, f) in scores.items()})
        if self.hard:                                                # --fit-edges (PIPELINE 21.F7)
            total += EDGE_W * sum(edge_term(o, self.hard[v]) for v, o in outs.items() if v in self.hard) / max(len(outs), 1)
        return total

    def pick_cams(self, parts, pinned=None):
        """The camera of every swept view: pinned (the run's silhouette.json) or the one whose
        outline of `parts` matches the sheet best."""
        world = [part_points(p) for p in parts]
        cams = {v: tuple(c) if isinstance(c, list) else c for v, c in (pinned or {}).items() if v in self.views}
        for v in self.views:
            if v not in cams and cam_candidates(v):
                cams[v] = max(cam_candidates(v), key=lambda c: self.cam_iou(v, c, world))
        return cams

    def cam_iou(self, view, cam, world):
        outline = [hull2d(np.stack(project(view, w, cam), 1)) for w in world]
        return self.best_variant(view, raster(outline)[0])[1]


# ---------------------------------------------------------------- the fit
def failing_band(proxy, mask, view):
    """Boolean per canvas row: where the proxy's error is concentrated (>= BAND_SHARE of the worst
    smoothed row). Sketch2Mesh Eq. 6: only the region that fails is allowed to move."""
    concept = max(silhouette.variants(mask, view), key=lambda m: silhouette.iou(proxy.concept[view], m))
    err = np.logical_xor(proxy.concept[view], concept).sum(axis=1).astype(float)
    err = np.convolve(err, np.ones(BAND_SMOOTH) / BAND_SMOOTH, mode="same")
    return err >= BAND_SHARE * err.max() if err.max() > 0 else np.zeros_like(err, bool)


def touched(proxy, parts, masks, failing):
    """Indices of the parts whose rows meet the failing band of a failing view."""
    hit = set()
    for view in failing:
        band = failing_band(proxy, masks[view][0], view)
        for i, (r0, r1) in enumerate(masks[view][1]):
            if band[max(int(r0), 0):int(r1) + 1].any():
                hit.add(i)
    return sorted(hit)


def flip_x(part):
    """The part seen in a mirror across x = 0: x of `at`, from/to and shift negate, rot (right, up,
    forward) becomes (right, -up, -forward)."""
    out = copy.deepcopy(part)
    out[3][0] = -out[3][0]
    opts = out[5] if isinstance(out[5], dict) else {}
    for key in ("from", "to", "shift"):
        if key in opts:
            opts[key][0] = -opts[key][0]
    if "knee" in opts:
        opts["knee"][1] = -opts["knee"][1]
    if "rot" in opts:
        rx, ry, rz = spec_rot(opts)
        opts["rot"] = [rx, -ry, -rz]
    return out


def canon(x):
    """x with its floats rounded, so two spec rows compare equal up to noise."""
    if isinstance(x, float):
        return round(x, 4) + 0.0
    if isinstance(x, dict):
        return {k: canon(v) for k, v in x.items()}
    return [canon(v) for v in x] if isinstance(x, (list, tuple)) else x


def mirror_of(parts, i, free):
    """Index of the free part that is part i seen in a mirror, or None."""
    if abs(parts[i][3][0]) < 1e-6:
        return None
    want = canon(flip_x(parts[i])[1:])               # the bone differs (arm.L / arm.R)
    return next((j for j in free if j != i and canon(parts[j][1:]) == want), None)


def groups_of(parts, free):
    """[(index, mirror index or None)]: a left/right pair moves as one, so a fit never breaks symmetry."""
    seen, groups = set(), []
    for i in free:
        if i in seen:
            continue
        j = mirror_of(parts, i, free)
        seen |= {i, j}
        groups.append((i, j))
    return groups


def apply_rot(part, values, mirror, height):
    """rot += ROT_RANGE x values (right, up, forward); the mirrored twin turns (right, -up, -forward)."""
    opts = part[5] if isinstance(part[5], dict) else {}
    sign = (1, -1, -1) if mirror else (1, 1, 1)
    opts["rot"] = [r + ROT_RANGE * v * k for r, v, k in zip(spec_rot(opts), values, sign)]


def rot_allowed(part, hood):
    """Arm, leg and hood parts that are not spans (from/to ignore rot) take a rot."""
    opts = part[5] if isinstance(part[5], dict) else {}
    return "from" not in opts and (hood or part[0].startswith(ROT_BONES))


def clip(v, lo, hi):
    return round(min(max(v, lo), hi), 4)


def apply_profile(part, values, mirror, height):
    """A lathe's profile radii and squash moved by PROFILE_RANGE x values (PIPELINE 21.F2)."""
    opts = part[5]
    prof = opts.get("profile") or []
    opts["profile"] = [clip(v * (1 + PROFILE_RANGE * s), 0.05, lathe_limb.PROFILE_MAX) for v, s in zip(prof, values)]
    opts["squash"] = clip(float(opts.get("squash", 1.0)) * (1 + PROFILE_RANGE * values[len(prof)]), 0.5, 2.0)


def profile_bounds(part, no_grow):
    cap = 0 if no_grow and part[1] == "lathe" else 1       # a no-grow lathe's profile only shrinks
    return [(-1, cap)] * len(part[5].get("profile") or ()) + [(-1, 1)]


def apply_knee(part, values, mirror, height):
    """A limb's knee fraction moved by KNEE_RANGE, its dx/dz by AT_RANGE x height."""
    opts = part[5]
    frac, dx, dz, *rest = opts.get("knee", lathe_limb.KNEE)
    step = AT_RANGE * height
    opts["knee"] = [clip(frac + KNEE_RANGE * values[0], 0.15, 0.85),
                    round(dx + step * values[1] * (-1 if mirror else 1), 4), round(dz + step * values[2], 4), *rest]


# Extra continuous parameters of a part kind, after its dims and `at`: PARAMS[kind] lists names, EXTRAS[name]
# says how many unit values it takes, when it applies and how it moves the part. A new kind (lathe, limb)
# adds its own entries here and touches nothing else.
PARAMS = {**{kind: ("rot",) for kind in ("box", "prism", "frustum", "dome")}, "lathe": ("profile",), "limb": ("knee",)}
EXTRAS = {"rot": {"size": 3, "allowed": rot_allowed, "apply": apply_rot},
          "profile": {"size": lambda p: len(p[5].get("profile") or ()) + 1, "allowed": lambda p, hood: True,
                      "apply": apply_profile, "bounds": profile_bounds},
          "knee": {"size": 3, "allowed": lambda p, hood: True, "apply": apply_knee}}


def extras_of(part, hood=False):
    return tuple(n for n in PARAMS.get(part[1], ()) if EXTRAS[n]["allowed"](part, hood))


def extra_size(part, name):
    size = EXTRAS[name]["size"]
    return size(part) if callable(size) else size


def group_size(part, extra=()):
    return len(part[2]) + 3 + sum(extra_size(part, n) for n in extra)


def moved(part, x, height, mirror=False, extra=()):
    """A copy of `part` with unit parameters x = (dim scales..., dx, dy, dz, extras...) in [-1, 1] applied."""
    out = copy.deepcopy(part)
    n = len(out[2])
    out[2] = [d * (1 + DIMS_RANGE * s) for d, s in zip(out[2], x[:n])]
    delta = [AT_RANGE * height * v * (-1 if mirror and k == 0 else 1) for k, v in enumerate(x[n:n + 3])]
    out[3] = [a + d for a, d in zip(out[3], delta)]
    opts = out[5] if isinstance(out[5], dict) else {}
    for end in ("from", "to"):
        if end in opts:
            opts[end] = [a + d for a, d in zip(opts[end], delta)]
    k = n + 3
    for name in extra:
        size = extra_size(out, name)
        EXTRAS[name]["apply"](out, x[k:k + size], mirror, height)
        k += size
    return out


def apply(parts, groups, x, height, extra=None):
    out, k = list(parts), 0
    for i, j in groups:
        names = (extra or {}).get(i, ())
        n = group_size(parts[i], names)
        out[i] = moved(parts[i], x[k:k + n], height, extra=names)
        if j is not None:
            out[j] = moved(parts[j], x[k:k + n], height, mirror=True, extra=names)
            out[j][2] = list(out[i][2])      # twins share dims exactly: the grid snap rounds each
        k += n                               # side on its own and preflight `symmetry` allows 5 %
    return out


def hood_index(parts):
    """Index of the widest part on the head bone (the hood or helmet shell), or None."""
    def width(i):
        lo, hi = preflight.bbox(parts[i])
        return hi[0] - lo[0]
    return max((i for i, p in enumerate(parts) if p[0] == "head"), key=width, default=None)


def leg_grow(part, leg_w, height):
    """Upper unit bound of a spider leg's horizontal dims: wide enough to reach the sheet's leg radius
    (leg_w, fraction of H) when the leg is thinner than that, the usual +DIMS_RANGE otherwise."""
    if not part[0].startswith("leg") or not leg_w:
        return 1.0
    return max(1.0, (leg_w * height / preflight.leg_radius(part) - 1) / DIMS_RANGE)


def bounds_of(part, no_grow, wide=False, extra=(), grow=1.0):
    """scipy bounds of one group's unit parameters: a no-grow part may only shrink its horizontal dims;
    a part attached to its parent (`wide`) may move them by ATTACHED_RANGE instead of DIMS_RANGE;
    `grow` (leg_grow, F3) lifts the upper bound of the horizontal dims."""
    horizontal = HORIZONTAL.get(part[1], ())
    top = ATTACHED_RANGE / DIMS_RANGE if wide else 1
    bounds = [(-1, 0) if no_grow and k in horizontal else (-top, max(top, grow) if k in horizontal else top)
              for k in range(len(part[2]))]
    bounds += [(-1, 1)] * 3
    for name in extra:
        bounds += EXTRAS[name].get("bounds", lambda p, g: [(-1, 1)] * extra_size(p, name))(part, no_grow)
    return bounds


def sheet_leg_w(doc, sheet):
    """The sheet's leg radius for a spider doc (its rig_measure, else measured), None for another rig or LEG_GROW off."""
    if not LEG_GROW or doc.get("rig") not in RF.SPIDERS:
        return None
    return (doc.get("rig_measure") or {}).get("leg_w") or silhouette.measure_spider(sheet).get("leg_w")


def loose_of(parts, parent_of):
    """Parts not connected to their parent when every box is shrunk to OVERLAP_SHRINK."""
    return set(preflight.floating_parts(parts, parent_of, preflight.OVERLAP_SHRINK))


def broken_rules(parts, doc, kind, targets, props):
    return {n for n, ok, _ in preflight.checks_of(parts, doc, kind, targets, props) if not ok}


def turn_masks(sheet):
    """{"turn<azimuth>": normalized mask} of the 3/4 panels of refs/<id>/sheet-turn.jpg (F6), or {}.
    silhouette.turn_panels(path) -> {azimuth degrees (0 = front): mask} is the contract; the 90-degree
    panels are the front/left/back already fitted."""
    path = pathlib.Path(sheet).with_name("sheet-turn.jpg")
    panels = getattr(silhouette, "turn_panels", None)
    if not (callable(panels) and path.exists()):
        return {}
    return {f"turn{int(az)}": silhouette.normalize(m) for az, m in panels(path).items() if int(az) % 90}


def concept_masks(sheet, views, wide):
    """{view: normalized concept mask} of the fitted views the sheet has (rts and turn only when wide)."""
    panels = silhouette.concept_panels(sheet)
    out = {v: silhouette.normalize(panels[v]) for v in views if v in panels}
    rts = silhouette.rts_path(pathlib.Path(sheet))
    if "rts" in views and wide and rts.exists():
        out["rts"] = silhouette.normalize(silhouette.foreground(rts, 768))
    return out | (turn_masks(sheet) if wide else {})


class Stop(Exception):
    """Raised by the objective when the wall-clock budget is gone: the best point so far stands."""


class Objective:
    """What Powell minimises: the proxy loss of a candidate plus LOOSE_W per part off its parent, or a
    flat penalty when a rule that held breaks or a connected part comes loose (hard constraints)."""

    def __init__(self, proxy, doc, parts, groups, free, ctx):
        self.proxy, self.doc, self.parts, self.groups, self.free, self.ctx = proxy, doc, parts, groups, free, ctx
        self.cache = {i: proxy.hulls(part_points(p)) for i, p in enumerate(parts) if i not in free}
        self.best, self.n = {"f": math.inf, "x": None}, 0

    def __call__(self, x):
        c = self.ctx
        if self.n >= c["max_evals"] or time.monotonic() > c["deadline"]:
            raise Stop
        self.n += 1
        cand = apply(self.parts, self.groups, x, c["height"], c["extra"])
        worse = broken_rules(cand, self.doc, c["kind"], c["targets"], c["props"]) - c["held"]
        loose = loose_of(cand, c["parent_of"])
        if worse or loose - c["loose0"]:
            return PENALTY + len(worse) + len(loose - c["loose0"])
        moving = {j: self.proxy.hulls(part_points(cand[j])) for j in self.free}
        f = self.proxy.loss(cand, self.cache | moving, self.free) + LOOSE_W * len(loose)
        if f < self.best["f"]:           # Powell can end on a worse point across the penalty cliffs
            self.best.update(f=f, x=np.array(x, float))
        return f


def toggle_cut(doc):
    """The doc with `cut: sheet` flipped: removed from every part when some part has it, else put on the
    largest plain box/prism/frustum of the torso, pelvis and abdomen bones and on the hood (at most CUT_MAX).
    None when no part can take it. spec_pipeline builds both and keeps the better clay (PIPELINE 21.F4)."""
    parts = copy.deepcopy(doc["parts"])
    if any(isinstance(p[5], dict) and p[5].get("cut") for p in parts):
        for p in parts:
            p[5].pop("cut", None)
        return {**doc, "parts": parts}

    def plain(p):
        return p[1] in ("box", "prism", "frustum") and isinstance(p[5], dict) and not (
            {"rot", "from", "to"} & p[5].keys())

    def volume(i):
        lo, hi = preflight.bbox(parts[i])
        return float(np.prod(np.subtract(hi, lo)))

    best = {b: max((i for i, p in enumerate(parts) if p[0] == b and plain(p)), key=volume, default=None)
            for b in CUT_BONES}
    hood = hood_index(parts)
    pick = [i for i in [*best.values(), hood] if i is not None and plain(parts[i])]
    pick = sorted(dict.fromkeys(pick), key=volume, reverse=True)[:CUT_MAX]
    for i in pick:
        parts[i][5]["cut"] = "sheet"
    return {**doc, "parts": parts} if pick else None


def search_space(parts, groups, hood, parent_of, loose0, wide, leg_w=None, height=1.0):
    """({part index: extra param names}, scipy bounds) of the fitted groups."""
    extra = {i: extras_of(parts[i], i == hood or j == hood and j is not None) if wide else () for i, j in groups}
    bounds = []
    for i, j in groups:
        shrink = parts[i][0] in NO_GROW or hood is not None and hood in (i, j)
        attached = wide and parts[i][0] in parent_of and parts[i][0] not in loose0
        bounds += bounds_of(parts[i], shrink, attached, extra[i], leg_grow(parts[i], leg_w, height))
    return extra, bounds


STAGES = ("trunk", "limbs", "profiles")
TRUNK_BONES = ("spine", "pelvis", "torso", "chest", "body", "abdomen", "head", "neck")   # bone prefixes of the trunk stage
STAGE_OF_EXTRA = {"profile": "profiles"}        # every other extra (rot, knee) moves in the limbs stage


def stage_masks(parts, groups, extra, stages):
    """{stage: boolean mask over the flat parameter vector} (PIPELINE 22.L4-3). Per group the dims and `at`
    belong to the trunk stage when the part sits on a trunk bone, else to the limbs stage; each extra to
    STAGE_OF_EXTRA (default limbs). A stage with no parameter is left out."""
    size = sum(group_size(parts[i], extra[i]) for i, _ in groups)
    masks = {s: np.zeros(size, bool) for s in stages}
    k = 0
    for i, _ in groups:
        n = len(parts[i][2]) + 3
        masks[("trunk" if parts[i][0].startswith(TRUNK_BONES) else "limbs")][k:k + n] = True
        k += n
        for name in extra[i]:
            masks[STAGE_OF_EXTRA.get(name, "limbs")][k:k + extra_size(parts[i], name)] = True
            k += extra_size(parts[i], name)
    return {s: m for s, m in masks.items() if m.any()}


def descend(objective, bounds, masks, seconds):
    """Powell over the whole vector (masks None) or, stage by stage, over each mask's coordinates with the
    rest held at the best point so far: each stage takes 1/len(masks) of the evaluations and the seconds,
    the same objective, the best point kept across stages."""
    ctx, total, end = objective.ctx, objective.ctx["max_evals"], objective.ctx["deadline"]
    lo = np.array([b[0] for b in bounds], float)
    hi = np.array([b[1] for b in bounds], float)
    for mask in (masks or {None: slice(None)}).values():
        base = np.zeros(len(bounds)) if objective.best["x"] is None else objective.best["x"].copy()
        if masks:
            ctx["max_evals"] = objective.n + total // len(masks)
            ctx["deadline"] = min(end, time.monotonic() + seconds / len(masks))

        def sub(y, base=base, mask=mask):
            x = base.copy()
            x[mask] = y
            return objective(x)
        try:
            minimize(sub, base[mask], method="Powell", bounds=list(zip(lo[mask], hi[mask])),
                     options={"maxfev": ctx["max_evals"] - objective.n, "xtol": 1e-2, "ftol": 1e-4})
        except Stop:
            if objective.n >= total or time.monotonic() > end:
                break


def baked(parts, sheet):
    """The parts with the sheet profile written into every lathe that has none, so the fit can move
    its radii; a copy, the doc is untouched until a fit is accepted."""
    read = cut_hull.lathe_profiles(parts, sheet) if any(p[1] == "lathe" for p in parts) else {}
    if not read:
        return parts
    out = copy.deepcopy(parts)
    for i, found in read.items():
        out[i][5]["profile"] = found["profile"]
    return out


def fit(doc, sheet, kind="mass", views=None, margin=MARGIN, max_evals=None, wide=True, tilts=None,
        seconds=MAX_SECONDS, hard=None, stages=None):
    """(fitted doc, report). The doc is returned untouched when no view is under its gate
    (+ margin) or the parts on the failing band cannot move without breaking a rule.
    `wide=False` is the classic fit (front/left/back, dims and `at`); `tilts` pins the
    top/bottom/rts cameras ({view: tilt}, silhouette.json's), else each is swept on the start spec.
    `stages` (subset of STAGES) runs one Powell per stage on its own parameters, 1/len of the budget each
    (PIPELINE 22.L4-3); None is the single Powell over every parameter."""
    t0 = time.monotonic()
    parts = baked(doc["parts"], sheet) if "parts" in doc else None
    gates = silhouette.gates_for(doc.get("rig"))
    concept = concept_masks(sheet, views or (WIDE_VIEWS if wide else FIT_VIEWS), wide)
    proxy = Proxy(concept, tuple(concept), hard=hard_canvas_edges(hard, tuple(concept)) if hard else None)
    if parts:
        proxy.cams = proxy.pick_cams(parts, tilts)
    before = proxy.ious(parts) if parts else {}
    failing = [v for v in proxy.views if v in gates and before.get(v, 1.0) < gates[v] + margin]
    report = {"views": list(proxy.views), "cams": proxy.cams, "before": before, "after": before,
              "failing": failing, "free": 0, "evals": 0, "changed": False}
    if not parts or not failing:
        return doc, report
    free = touched(proxy, parts, proxy.masks(parts), failing)
    groups = groups_of(parts, free)
    hood = hood_index(parts)
    # the anchor: a part that was connected to its parent stays connected (hard); each one that
    # was not costs LOOSE_W, so the fit can reconnect it
    parent_of = RF.parents(doc.get("rig", "biped"), doc.get("bones"))
    loose0 = loose_of(parts, parent_of)
    height = max(max(b[1][1] for b in map(preflight.bbox, parts)), 1e-6)
    extra, bounds = search_space(parts, groups, hood, parent_of, loose0, wide, sheet_leg_w(doc, sheet), height)
    if wide and pathlib.Path(sheet).exists() and doc.get("palette"):
        proxy.zones = Zones(sheet, doc, proxy.views)
    targets, props = preflight.targets_from(sheet), preflight.load_props(pathlib.Path(sheet).parent.name)
    ctx = {"kind": kind, "targets": targets, "props": props, "parent_of": parent_of, "loose0": loose0,
           "held": broken_rules(parts, doc, kind, targets, props), "extra": extra,
           "height": height,
           "max_evals": max_evals or (MAX_EVALS if wide else FAST_EVALS), "deadline": time.monotonic() + seconds}
    objective = Objective(proxy, doc, parts, groups, free, ctx)
    start = proxy.loss(parts, free=free) + LOOSE_W * len(loose0)
    masks = stage_masks(parts, groups, extra, stages) if stages else None
    descend(objective, bounds, masks, seconds)
    best = objective.best
    report.update(free=len(free), groups=len(groups), evals=objective.n, loss=[round(start, 4), round(best["f"], 4)],
                  seconds=round(time.monotonic() - t0, 1))
    if best["x"] is None or best["f"] >= start - 1e-4:
        return doc, report
    fitted = apply(parts, groups, best["x"], ctx["height"], extra)
    report.update(after=proxy.ious(fitted), changed=True)
    return {**doc, "parts": fitted}, report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", type=pathlib.Path)
    ap.add_argument("sheet", type=pathlib.Path, help="the approved sheet (the judge)")
    ap.add_argument("out", type=pathlib.Path)
    ap.add_argument("--views", default="", help=f"default: {','.join(WIDE_VIEWS)} (--fast: {','.join(FIT_VIEWS)})")
    ap.add_argument("--kind", default="mass", choices=preflight.BUDGETS.keys())
    ap.add_argument("--margin", type=float, default=MARGIN,
                    help="fit views under gate + margin (the proxy is a little off the real render)")
    ap.add_argument("--fast", action="store_true", help="the classic fit: front/left/back, dims and at only")
    ap.add_argument("--tilts", default="", help="pin the top/bottom/rts cameras, e.g. top:-20,bottom:30,rts:35/-45")
    ap.add_argument("--seconds", type=float, default=MAX_SECONDS, help="wall-clock budget of the search")
    ap.add_argument("--hard", type=pathlib.Path, default=None,
                    help="the hard sheet: adds the edge term (hard-sheet inner edges vs part outlines)")
    args = ap.parse_args()
    doc = json.loads(args.spec.read_text())
    views = tuple(args.views.split(",")) if args.views else None
    out, report = fit(doc, args.sheet, args.kind, views, args.margin, wide=not args.fast,
                      tilts=V.parse_tilts(args.tilts), seconds=args.seconds, hard=args.hard)
    args.out.write_text(json.dumps(out, indent=2))
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
