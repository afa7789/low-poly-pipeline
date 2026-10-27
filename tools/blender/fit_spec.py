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
"""
import argparse
import copy
import json
import math
import pathlib
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_erosion, distance_transform_edt
from scipy.optimize import minimize
from scipy.spatial import ConvexHull, QhullError

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import preflight  # noqa: E402
import rig_families as RF  # noqa: E402
import silhouette  # noqa: E402

FIT_VIEWS = ("front", "left", "back")
DIMS_RANGE = 0.10       # a dim may move by this fraction (0.20 pulled limbs off their parents, PIPELINE 20.N12)
AT_RANGE = 0.03         # `at` may move by this fraction of the height
LOOSE_W = 0.3           # objective cost of each part not connected to its parent (80 % boxes)
# bones whose parts keep their width and depth: the torso, and the hood (the widest part on the head)
NO_GROW = ("spine", "pelvis", "body", "abdomen")
HORIZONTAL = {"box": (0, 2), "frustum": (0, 2), "prism": (0, 1), "cyl": (0,), "dome": (0,)}
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


def raster(outlines):
    """Fill the outlines (model units, +v up) into the 256 x 384 canvas the way
    silhouette.normalize lays a figure out: cropped to its extent, as tall as the canvas
    allows, centred. Returns (mask, [(first row, last row) per outline])."""
    allp = np.concatenate(outlines)
    lo, hi = allp.min(axis=0), allp.max(axis=0)
    w, h = max(hi[0] - lo[0], 1e-6), max(hi[1] - lo[1], 1e-6)
    s = min(silhouette.CANVAS_H / h, silhouette.CANVAS_W / w)
    x0 = (silhouette.CANVAS_W - w * s) / 2
    y0 = (silhouette.CANVAS_H - h * s) / 2
    img = Image.new("L", (silhouette.CANVAS_W, silhouette.CANVAS_H), 0)
    draw, rows = ImageDraw.Draw(img), []
    for o in outlines:
        px = np.stack([(o[:, 0] - lo[0]) * s + x0, (hi[1] - o[:, 1]) * s + y0], 1)
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
    return {v: silhouette.fit_canvas(silhouette.edges(hard, panels[v]), panels[v]) for v in views}


class Proxy:
    """Scores a parts list against the concept masks of the views being fitted."""

    def __init__(self, concept, views, hard=None):
        self.concept, self.views, self.hard = concept, views, hard
        # the concept's contour and its distance map never change: silhouette.chamfer, halved
        self.edge = {v: edge_of(m) for v, m in concept.items()}
        self.dist = {v: distance_transform_edt(~e) for v, e in self.edge.items()}

    def outlines(self, parts, cache=None):
        """{view: [outline per part]}; `cache` {part index: world points} spares the frozen parts."""
        world = [cache[i] if cache and i in cache else part_points(p) for i, p in enumerate(parts)]
        return {v: [hull2d(np.stack(PROJECT[v](w), 1)) for w in world] for v in self.views}

    def masks(self, parts, cache=None):
        """{view: (mask, row span per part)}"""
        return {v: raster(o) for v, o in self.outlines(parts, cache).items()}

    def view_score(self, view, mask):
        """(IoU, chamfer) against the concept: the better of the mask and its mirror, like silhouette.variants."""
        best = max(silhouette.variants(mask, view), key=lambda m: silhouette.iou(self.concept[view], m))
        if not best.any():
            return 0.0, 1.0
        edge = edge_of(best)
        chamfer = (self.dist[view][edge].mean() + distance_transform_edt(~edge)[self.edge[view]].mean()) / 2
        return silhouette.iou(self.concept[view], best), float(chamfer / best.shape[0])

    def ious(self, parts, cache=None):
        return {v: round(self.view_score(v, m)[0], 4) for v, (m, _) in self.masks(parts, cache).items()}

    def loss(self, parts, cache=None):
        scores = [self.view_score(v, m) for v, (m, _) in self.masks(parts, cache).items()]
        edge = self.outlines(parts, cache) if self.hard else {}      # --fit-edges (PIPELINE 21.F7)
        return sum((1 - i) + CHAMFER_W * c for i, c in scores) / len(scores) \
            + EDGE_W * sum(edge_term(o, self.hard[v]) for v, o in edge.items()) / max(len(edge), 1)


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


def moved(part, x, height, mirror=False):
    """A copy of `part` with unit parameters x = (dim scales..., dx, dy, dz) in [-1, 1] applied."""
    out = copy.deepcopy(part)
    n = len(out[2])
    out[2] = [d * (1 + DIMS_RANGE * s) for d, s in zip(out[2], x[:n])]
    delta = [AT_RANGE * height * v * (-1 if mirror and k == 0 else 1) for k, v in enumerate(x[n:])]
    out[3] = [a + d for a, d in zip(out[3], delta)]
    opts = out[5] if isinstance(out[5], dict) else {}
    for end in ("from", "to"):
        if end in opts:
            opts[end] = [a + d for a, d in zip(opts[end], delta)]
    return out


def apply(parts, groups, x, height):
    out, k = list(parts), 0
    for i, j in groups:
        n = len(parts[i][2]) + 3
        out[i] = moved(parts[i], x[k:k + n], height)
        if j is not None:
            out[j] = moved(parts[j], x[k:k + n], height, mirror=True)
            out[j][2] = list(out[i][2])      # twins share dims exactly: the grid snap rounds each
            k += n                           # side on its own and preflight `symmetry` allows 5 %
            continue
        k += n
    return out


def hood_index(parts):
    """Index of the widest part on the head bone (the hood or helmet shell), or None."""
    def width(i):
        lo, hi = preflight.bbox(parts[i])
        return hi[0] - lo[0]
    return max((i for i, p in enumerate(parts) if p[0] == "head"), key=width, default=None)


def bounds_of(part, no_grow):
    """scipy bounds of one group's unit parameters: a no-grow part may only shrink its horizontal dims."""
    horizontal = HORIZONTAL.get(part[1], ()) if no_grow else ()
    n = len(part[2])
    return [(-1, 0 if k in horizontal else 1) for k in range(n)] + [(-1, 1)] * 3


def loose_of(parts, parent_of):
    """Parts not connected to their parent when every box is shrunk to OVERLAP_SHRINK."""
    return set(preflight.floating_parts(parts, parent_of, preflight.OVERLAP_SHRINK))


def broken_rules(parts, doc, kind, targets, props):
    return {n for n, ok, _ in preflight.checks_of(parts, doc, kind, targets, props) if not ok}


def fit(doc, sheet, kind="mass", views=FIT_VIEWS, margin=MARGIN, max_evals=MAX_EVALS, hard=None):
    """(fitted doc, report). The doc is returned untouched when no view is under its gate
    (+ margin) or the parts on the failing band cannot move without breaking a rule."""
    parts = doc["parts"] if "parts" in doc else None
    gates = silhouette.gates_for(doc.get("rig"))
    panels = silhouette.concept_panels(sheet)
    proxy = Proxy({v: silhouette.normalize(panels[v]) for v in views}, views,
                  hard_canvas_edges(hard, views) if hard else None)
    before = proxy.ious(parts) if parts else {}
    failing = [v for v in views if before.get(v, 1.0) < gates[v] + margin]
    report = {"views": list(views), "before": before, "after": before, "failing": failing,
              "free": 0, "evals": 0, "changed": False}
    if not parts or not failing:
        return doc, report
    masks = proxy.masks(parts)
    free = touched(proxy, parts, masks, failing)
    groups = groups_of(parts, free)
    height = max(max(b[1][1] for b in map(preflight.bbox, parts)), 1e-6)
    targets, props = preflight.targets_from(sheet), preflight.load_props(pathlib.Path(sheet).parent.name)
    held = broken_rules(parts, doc, kind, targets, props)
    cache = {i: part_points(p) for i, p in enumerate(parts) if i not in free}
    sizes = [len(parts[i][2]) + 3 for i, _ in groups]
    hood = hood_index(parts)
    bounds = [b for i, j in groups for b in bounds_of(parts[i], parts[i][0] in NO_GROW or hood in (i, j) and hood is not None)]
    # the anchor: a part that was connected to its parent stays connected (hard); each one that
    # was not costs LOOSE_W, so the fit can reconnect it
    parent_of = RF.parents(doc.get("rig", "biped"), doc.get("bones"))
    loose0 = loose_of(parts, parent_of)
    counts, best = {"n": 0}, {"f": math.inf, "x": np.zeros(sum(sizes))}

    def objective(x):
        counts["n"] += 1
        cand = apply(parts, groups, x, height)
        worse = broken_rules(cand, doc, kind, targets, props) - held
        loose = loose_of(cand, parent_of)
        if worse or loose - loose0:
            return PENALTY + len(worse) + len(loose - loose0)
        f = (proxy.loss(cand, cache | {j: part_points(cand[j]) for j in free if j not in cache})
             + LOOSE_W * len(loose))
        if f < best["f"]:             # Powell can end on a worse point across the penalty cliffs
            best.update(f=f, x=np.array(x, float))
        return f

    start = proxy.loss(parts) + LOOSE_W * len(loose0)
    minimize(objective, np.zeros(sum(sizes)), method="Powell", bounds=bounds,
             options={"maxfev": max_evals, "xtol": 1e-2, "ftol": 1e-4})
    fitted = apply(parts, groups, best["x"], height)
    report.update(free=len(free), groups=len(groups), evals=counts["n"], loss=[round(start, 4), round(best["f"], 4)])
    if best["f"] >= start - 1e-4:
        return doc, report
    out = {**doc, "parts": fitted}
    report.update(after=proxy.ious(fitted), changed=True)
    return out, report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", type=pathlib.Path)
    ap.add_argument("sheet", type=pathlib.Path, help="the approved sheet (the judge)")
    ap.add_argument("out", type=pathlib.Path)
    ap.add_argument("--views", default=",".join(FIT_VIEWS))
    ap.add_argument("--kind", default="mass", choices=preflight.BUDGETS.keys())
    ap.add_argument("--margin", type=float, default=MARGIN,
                    help="fit views under gate + margin (the proxy is a little off the real render)")
    ap.add_argument("--hard", type=pathlib.Path, default=None,
                    help="the hard sheet: adds the edge term (hard-sheet inner edges vs part outlines)")
    args = ap.parse_args()
    doc = json.loads(args.spec.read_text())
    out, report = fit(doc, args.sheet, args.kind, tuple(args.views.split(",")), args.margin, hard=args.hard)
    args.out.write_text(json.dumps(out, indent=2))
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
