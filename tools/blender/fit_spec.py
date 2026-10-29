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
A part marked opts "prop" (a weapon, a tank: PIPELINE 23.L5-3) is never free: its dims stay and it moves with the parts on its anchor bone (carry_props).
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
import parts_fit  # noqa: E402
import preflight  # noqa: E402
import rig_families as RF  # noqa: E402
import silhouette  # noqa: E402
import views as V  # noqa: E402
from part_geom import (D, SIDES, box_corners, disc_base, euler_matrix, fitted_dims, frustum_points, local_shape,  # noqa: E402,F401
                       part_points, ring_points, scaled, spec_rot, spec_to_blender, track_z)

FIT_VIEWS = ("front", "left", "back")
WIDE_VIEWS = ("front", "left", "back", "top", "bottom", "rts")     # the verdict's views (silhouette.GATES)
TURN_STEPS = (-20, -10, 0, 10, 20)   # degrees the azimuth of a sheet-turn panel is swept
ATTACHED_RANGE = 0.20   # a part connected to its parent may move its dims this far (PIPELINE 21.F4)
ROT_RANGE = 20.0        # degrees a `rot` axis may move
ROT_BONES = ("arm", "forearm", "hand", "thigh", "shin", "foot", "leg")   # bone name prefixes whose parts turn
ZONE_W = 0.1            # objective weight of the colour-zone term (1 - share of a part inside its zone)
PART_W = 0.2            # ... of the part-mask term (1 - share of a part's visible projection inside its part, L5-4)
PART_POOR = 0.85         # a part with less than this share inside its part mask is moved even if no view fails
DEPTH_W = 0.3           # cost of each depth pair (A in front of B) that does not hold, as LOOSE_W
MAX_SECONDS = 150.0     # wall-clock budget of one fit (the unit's budget is 3 min with the clay trials)
FAST_EVALS = 1500       # --fit-fast: the classic 3 views, no rot, no zones
DIMS_RANGE = 0.10       # a dim may move by this fraction (0.20 pulled limbs off their parents, PIPELINE 20.N12)
LEG_GROW = False        # spider legs may grow to the sheet's leg_w: off, n00U v6-r3 lost .002-.008 on 5 views (PIPELINE 21.F3)
LEG_SPILL = 0.2         # a leg part may project this share of its own rts area outside the sheet's rts (PIPELINE 25.L7-3)
LEG_SPILL_W = 0.0       # objective cost per leg of the share over LEG_SPILL (the leg's green in the rts); off: n00U v10-r1 rts spill .283 -> .268, bottom -.025 (PIPELINE 25.L7-3)
AT_RANGE = 0.03         # `at` may move by this fraction of the height
PROFILE_RANGE = 0.15    # a lathe's profile radii and squash may move by this fraction (PIPELINE 21.F2)
KNEE_RANGE = 0.15       # a limb's knee fraction may move by this much, its dx/dz by AT_RANGE * height
LOOSE_W = 0.3           # objective cost of each part not connected to its parent (80 % boxes)
# bones whose parts keep their width and depth: the torso, and the hood (the widest part on the head)
NO_GROW = ("spine", "pelvis", "body", "abdomen")
HORIZONTAL = {"box": (0, 2), "frustum": (0, 2), "prism": (0, 1), "cyl": (0,), "dome": (0,), "lathe": (0,)}
CHAMFER_W = 1.0         # objective = (1 - IoU) + CHAMFER_W * chamfer, per view
EDGE_W = 0.1            # weight of the optional --fit-edges term (edge_term), per view mean
JOINT_W = 0.5           # weight of the optional --fit-joints term (joint_term): the mean gap in H of the readable joints
PENALTY = 10.0          # a preflight rule that held and breaks costs this much, plus 1 per rule
BAND_SHARE = 0.6        # failing band: rows whose error is this share of the worst row's
BAND_SMOOTH = 16        # rows of the moving average that smooths the error profile
MARGIN = 0.02          # fit views under gate + this: the proxy is within ~0.01 of the render (max 0.04)
MAX_EVALS = 4000        # scipy budget per fit (Powell, ~10 ms per evaluation)
# canvas column of a point (x, y, z in the build's Blender axes, +z up) per camera
PROJECT = {"front": lambda p: (p[:, 0], p[:, 2]), "back": lambda p: (-p[:, 0], p[:, 2]),
           "left": lambda p: (-p[:, 1], p[:, 2])}


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
def spec_centre(part):
    """Centre of a part's outline in spec axes (right, up, forward)."""
    w = part_points(part)
    c = (w.min(axis=0) + w.max(axis=0)) / 2
    return float(c[0]), float(c[2]), float(-c[1])




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


def raster(outlines, canvas=None):
    """Fill the outlines (model units, +v up) into the 256 x 384 canvas the way
    silhouette.normalize lays a figure out (`canvas`: canvas_of() of the whole figure, when these are only some
    of its parts). Returns (mask, [(first row, last row) per outline])."""
    canvas = canvas or canvas_of(outlines)
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
        self.centres = centres
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


def leg_spill(proxy, parts, outs, flipped, view="rts"):
    """Sum over the `leg*` parts of the share of the part's projection in `view` that lies outside the concept's mask,
    beyond LEG_SPILL (0 for a unit without legs or without that view). `flipped` = the mirror the whole model matched."""
    if view not in outs:
        return 0.0
    canvas, concept, total = canvas_of(outs[view]), proxy.concept[view], 0.0
    for i, p in enumerate(parts):
        if not p[0].startswith("leg"):
            continue
        px = to_px(outs[view][i], canvas)
        if flipped:
            px[:, 0] = silhouette.CANVAS_W - px[:, 0]
        x0, y0 = np.maximum(np.floor(px.min(axis=0)).astype(int), 0)
        x1, y1 = np.minimum(np.ceil(px.max(axis=0)).astype(int) + 1, (silhouette.CANVAS_W, silhouette.CANVAS_H))
        if x1 <= x0 or y1 <= y0:
            continue
        img = Image.new("L", (x1 - x0, y1 - y0), 0)
        ImageDraw.Draw(img).polygon([(a - x0, b - y0) for a, b in px], fill=255)
        mine = np.asarray(img) > 0
        out = float((mine & ~concept[y0:y1, x0:x1]).sum() / max(mine.sum(), 1))
        total += max(out - LEG_SPILL, 0.0)
    return total


class Proxy:
    """Scores a parts list against the concept masks of the views being fitted."""

    def __init__(self, concept, views, cams=None, zones=None, hard=None, partfit=None, rig=None):
        self.concept, self.views, self.cams, self.zones, self.hard = concept, views, cams or {}, zones, hard
        self.split = {}             # {view: (body mask, prop mask, body edge, its distance map)}: set_split
        self.weight = {v: V.weight_of(rig, v) for v in views}     # PIPELINE 25.L7-1
        self.partfit = partfit      # parts_fit.PartTerms: part masks and depth pairs (L5-4)
        # the concept's contour and its distance map never change: silhouette.chamfer, halved
        self.edge = {v: edge_of(m) for v, m in concept.items()}
        self.dist = {v: distance_transform_edt(~e) for v, e in self.edge.items()}

    def set_split(self, sheet):
        """Score the non-prop parts against the sheet's body mask and the props against theirs, in the views
        parts.json has prop boxes for (silhouette.prop_masks, PIPELINE 25.L7-5): a spear the model lacks stops
        pulling the legs toward it. The other views, and the gates' ious(), keep the whole silhouette."""
        panels = silhouette.concept_panels(sheet)
        for v in self.views:
            props = silhouette.prop_masks(sheet, v, panels=panels) if v in panels else {}
            if props:
                union = np.any(list(props.values()), axis=0) & self.concept[v]
                body = self.concept[v] & ~union
                self.split[v] = (body, union, edge_of(body), distance_transform_edt(~edge_of(body)))

    def hulls(self, world, views=None):
        """{view: outline} of one part's world points, plus "near": {view: nearness to that camera} (L5-4)."""
        out = {v: hull2d(np.stack(project(v, world, self.cams.get(v)), 1)) for v in views or self.views}
        return out | {"near": {v: float((f(world).min() + f(world).max()) / 2) for v, f in parts_fit.NEAR.items()}}

    def hull_list(self, parts, cache=None):
        """[hulls() per part]; `cache` {part index: hulls()} spares the frozen parts."""
        return [cache[i] if cache and i in cache else self.hulls(part_points(p)) for i, p in enumerate(parts)]

    def outlines(self, parts, cache=None):
        """{view: [outline per part]}"""
        hulls = self.hull_list(parts, cache)
        return {v: [h[v] for h in hulls] for v in self.views}

    def masks(self, parts, cache=None):
        """{view: (mask, row span per part)}"""
        return {v: raster(o) for v, o in self.outlines(parts, cache).items()}

    def best_variant(self, view, mask, concept=None):
        """(mask, IoU, flipped): the better of the mask and its mirror, like silhouette.variants."""
        options, concept = silhouette.variants(mask, view), self.concept[view] if concept is None else concept
        k = silhouette.pick_variant(concept, options, view)
        return options[k], silhouette.iou(concept, options[k]), k == 1

    def view_score(self, view, mask, split=None):
        """(IoU, chamfer, flipped, asymmetric cost silhouette.asym_cost: spill dearer than bare, L12-2) against the concept (`split`: self.split[view], against its body mask)."""
        concept, edge_c, dist = (self.concept[view], self.edge[view], self.dist[view]) if split is None \
            else (split[0], split[2], split[3])
        best, score, flipped = self.best_variant(view, mask, concept)
        if not best.any():
            return 0.0, 1.0, False, 1.0
        edge = edge_of(best)
        chamfer = (dist[edge].mean() + distance_transform_edt(~edge)[edge_c].mean()) / 2
        return score, float(chamfer / best.shape[0]), flipped, silhouette.asym_cost(concept, best)

    def score_view(self, view, outs, flags):
        """view_score of the parts' outlines `outs` (`flags`: which are props). In a split view the body parts go
        against the body mask and the props, if the model has any, against the prop mask on the same side
        (mirror), the two IoUs weighted by the area of their masks; chamfer on the body."""
        split = self.split.get(view)
        if not split:
            return self.view_score(view, raster(outs)[0])
        canvas = canvas_of(outs)       # the canvas of the whole model, as the sheet's panel was laid out
        body = [o for o, f in zip(outs, flags) if not f]
        iou, chamfer, flipped, cost = self.view_score(view, raster(body, canvas)[0] if body else np.zeros_like(split[0]), split)
        held = [o for o, f in zip(outs, flags) if f]
        if held:
            prop = raster(held, canvas)[0]
            share = split[1].sum() / max(split[0].sum() + split[1].sum(), 1)
            prop = np.fliplr(prop) if flipped else prop
            iou = (1 - share) * iou + share * silhouette.iou(split[1], prop)
            cost = (1 - share) * cost + share * silhouette.asym_cost(split[1], prop)
        return iou, chamfer, flipped, cost

    def ious(self, parts, cache=None):
        return {v: round(self.view_score(v, m)[0], 4) for v, (m, _) in self.masks(parts, cache).items()}

    def polygons(self, outs):
        """{view: pixel outline per part} on each view's canvas, for the views parts.json has boxes for."""
        return {v: [to_px(o, canvas_of(outs[v])) for o in outs[v]] for v in self.partfit.views}

    def part_shares(self, parts, free, cache=None):
        """{(part, view): share of the part's visible projection inside its part mask} (L5-4)."""
        hulls = self.hull_list(parts, cache)
        outs = {v: [h[v] for h in hulls] for v in self.views}
        return self.partfit.shares(free, hulls, self.polygons(outs))

    def loss(self, parts, cache=None, free=()):
        hulls = self.hull_list(parts, cache)
        outs = {v: [h[v] for h in hulls] for v in self.views}
        flags = [preflight.is_prop(p) for p in parts]
        scores = {v: self.score_view(v, o, flags) for v, o in outs.items()}
        total = sum(self.weight[v] * (cost + CHAMFER_W * c) for v, (_, c, _, cost) in scores.items()) \
            / sum(self.weight[v] for v in scores)
        total += LEG_SPILL_W * leg_spill(self, parts, outs, scores["rts"][2]) if "rts" in scores else 0.0
        if self.zones and free:
            total += ZONE_W * self.zones.term(parts, free, outs, {v: s[2] for v, s in scores.items()})
        if self.partfit and free:
            total += PART_W * self.partfit.term(free, hulls, self.polygons(outs))
            total += DEPTH_W * len(self.partfit.broken(hulls))
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
    options = silhouette.variants(mask, view)
    concept = options[silhouette.pick_variant(proxy.concept[view], options, view)]
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
    if lathe_limb.is_ring_profile(prof):      # rings [w, d, zc, xc(, t)]: w and d by the ring's value, d by the last one (squash's role) too
        deep = 1 + PROFILE_RANGE * values[len(prof)]
        opts["profile"] = [[clip(q[0] * (1 + PROFILE_RANGE * s), 0.05, lathe_limb.RING_MAX),
                            clip(q[1] * (1 + PROFILE_RANGE * s) / deep, 0.05, lathe_limb.RING_MAX), *q[2:]] for q, s in zip(prof, values)]
        return
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


def apply_plate(part, values, mirror, height):
    """A plate's profile scaled about its centroid by PROFILE_RANGE x (u, v), clipped to 0-1 (PIPELINE 22.L4-2)."""
    prof = part[5].get("profile") or []
    cu, cv = (sum(q[i] for q in prof) / len(prof) for i in (0, 1)) if prof else (0, 0)
    part[5]["profile"] = [[clip(cu + (q[0] - cu) * (1 + PROFILE_RANGE * values[0]), 0, 1),
                           clip(cv + (q[1] - cv) * (1 + PROFILE_RANGE * values[1]), 0, 1)] for q in prof]


PARAMS["plate"] = ("plate",)       # dims (w, h, t) already scale the box and the thickness
EXTRAS["plate"] = {"size": 2, "allowed": lambda p, hood: bool(p[5].get("profile")), "apply": apply_plate}


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


def carry_props(parts, out):
    """Each prop (preflight.is_prop) follows its anchor: its `at` and from/to move by the mean shift of the
    non-prop parts on the anchor bone that the fit moved; its dims stay (PIPELINE 23.L5-3)."""
    bones = {p[0] for p in parts}
    for i, prop in enumerate(parts):
        if not preflight.is_prop(prop):
            continue
        bone = preflight.anchor_bone(prop, bones)
        shifts = [np.subtract(preflight.centre(out[j]), preflight.centre(q)) for j, q in enumerate(parts)
                  if q[0] == bone and not preflight.is_prop(q)]
        if not shifts:
            continue
        out[i] = copy.deepcopy(prop)
        delta = np.mean(shifts, axis=0)
        out[i][3] = [a + d for a, d in zip(prop[3], delta)]
        for end in ("from", "to"):
            if end in out[i][5]:
                out[i][5][end] = [a + d for a, d in zip(out[i][5][end], delta)]
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
    return preflight.clear_props(carry_props(parts, out), height)    # the fit never sinks a prop into the body (24.L6-3)


def leg_grow(part, leg_w, height):
    """Upper unit bound of a spider leg's horizontal dims: wide enough to reach the sheet's leg radius
    (leg_w, fraction of H) when the leg is thinner than that, the usual +DIMS_RANGE otherwise."""
    if not part[0].startswith("leg") or not leg_w:
        return 1.0
    return max(1.0, (leg_w * height / preflight.leg_radius(part) - 1) / DIMS_RANGE)


def limit_bounds(part, bounds, limit, height):
    """`bounds` with the unit slots a constraint names replaced by its interval (apply_deltas.fit_limits; L11-3):
    dim factor f -> s = (f - 1) / DIMS_RANGE, `at` shift m metres -> s = m / (AT_RANGE * height)."""
    out, n = list(bounds), len(part[2])
    for k, (lo, hi) in limit.get("dims", {}).items():
        out[k] = ((lo - 1) / DIMS_RANGE, (hi - 1) / DIMS_RANGE)
    for k, (lo, hi) in limit.get("at", {}).items():
        out[n + k] = (lo / (AT_RANGE * height), hi / (AT_RANGE * height))
    return out


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


def joint_term(parts, targets, height):
    """Optional fit term (--fit-joints, PIPELINE 22.L4-6): mean distance, in H, from the unit's knee and
    elbow to the sheet's (preflight.joint_height vs the joint targets); 0 when the sheet shows none."""
    boxes = {id(p): preflight.bbox(p) for p in parts}
    gaps = [abs(got - targets[k]) for k in preflight.JOINT_KEYS if k in targets
            for got in [preflight.joint_height(parts, boxes, height, k)] if got is not None]
    return sum(gaps) / len(gaps) if gaps else 0.0


class Stop(Exception):
    """Raised by the objective when the wall-clock budget is gone: the best point so far stands."""


class Objective:
    """What Powell minimises: the proxy loss of a candidate plus LOOSE_W per part off its parent, or a
    flat penalty when a rule that held breaks or a connected part comes loose (hard constraints)."""

    def __init__(self, proxy, doc, parts, groups, free, ctx):
        self.proxy, self.doc, self.parts, self.groups, self.free, self.ctx = proxy, doc, parts, groups, free, ctx
        self.cache = {i: proxy.hulls(part_points(p)) for i, p in enumerate(parts)
                      if i not in free and not preflight.is_prop(p)}   # a prop follows its anchor: never cached
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
        pf = self.proxy.partfit
        order = pf.broken(self.proxy.hull_list(cand, self.cache | moving)) if pf else set()
        if order - c["order0"]:           # a depth pair that held no longer does (L5-4: hard)
            return PENALTY + len(order - c["order0"])
        f = self.proxy.loss(cand, self.cache | moving, self.free) + LOOSE_W * len(loose)
        f += c["joint_w"] * joint_term(cand, c["targets"], c["height"]) if c["joint_w"] else 0.0
        if f < self.best["f"]:           # Powell can end on a worse point across the penalty cliffs
            self.best.update(f=f, x=np.array(x, float))
        return f


def toggle_cut(doc):
    """The doc with `cut: sheet` flipped: removed from every part when some part has it, else put on the
    parts cut_hull.cut_picks chooses (the largest torso, pelvis and abdomen part and the hood).
    None when no part can take it. spec_pipeline builds both and keeps the better clay (PIPELINE 21.F4)."""
    parts = copy.deepcopy(doc["parts"])
    if any(isinstance(p[5], dict) and p[5].get("cut") for p in parts):
        for p in parts:
            p[5].pop("cut", None)
        return {**doc, "parts": parts}
    pick = cut_hull.cut_picks(parts)
    for i in pick:
        parts[i][5]["cut"] = "sheet"
    return {**doc, "parts": parts} if pick else None


def fit_limits_of(doc, parts, constraints, height):
    """{index of a fittable part: limit} of the constraints (empty without any); a prop only rides its anchor."""
    if not constraints:
        return {}
    import apply_deltas
    found = apply_deltas.fit_limits(doc, constraints, height)
    return {i: lim for i, lim in found.items() if not preflight.is_prop(parts[i])}


def search_space(parts, groups, hood, parent_of, loose0, wide, leg_w=None, height=1.0, limits=None):
    """({part index: extra param names}, scipy bounds) of the fitted groups; `limits` ({part index: limit}) narrows the
    slots a delta names (L11-3)."""
    extra = {i: extras_of(parts[i], i == hood or j == hood and j is not None) if wide else () for i, j in groups}
    bounds = []
    for i, j in groups:
        shrink = parts[i][0] in NO_GROW or hood is not None and hood in (i, j)
        attached = wide and parts[i][0] in parent_of and parts[i][0] not in loose0
        b = bounds_of(parts[i], shrink, attached, extra[i], leg_grow(parts[i], leg_w, height))
        bounds += limit_bounds(parts[i], b, (limits or {}).get(i, {}), height)
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


def search(grad, objective, groups, bounds, masks, scene, seconds):
    """Powell (descend) or, with `grad`, Adam on the soft proxy (fit_grad.descend; `scene` = parts, extra, proxy, height).
    Both leave the best point in objective.best; returns the report entries of the search."""
    if not grad:
        descend(objective, bounds, masks, seconds)
        return {}
    import fit_grad
    return fit_grad.descend(objective, groups, bounds, *scene, seconds)


def baked(parts, sheet):
    """The parts with the sheet profile written into every lathe that has none, so the fit can move
    its radii; a copy, the doc is untouched until a fit is accepted."""
    read = cut_hull.lathe_profiles(parts, sheet) if any(p[1] == "lathe" for p in parts) else {}
    read.update(cut_hull.plate_profiles(parts, sheet) if any(p[1] == "plate" for p in parts) else {})
    if not read:
        return parts
    out = copy.deepcopy(parts)
    for i, found in read.items():
        out[i][5]["profile"] = found["profile"]
    return out


def attach_parts(proxy, doc, sheet, parts, height, wide, wanted, parts_path):
    """Give the proxy its colour zones (a palette, or a parts.json to read) and, when `wanted` and the sheet
    has a parts.json (or `parts_path` names one), the part masks and depth pairs (PIPELINE 23.L5-4)."""
    parts_doc = parts_fit.load(sheet, parts_path) if wide and wanted else None
    if wide and pathlib.Path(sheet).exists() and (doc.get("palette") or parts_doc):
        proxy.zones = Zones(sheet, doc, proxy.views)
    if parts_doc:
        centres = [spec_centre(p) for p in parts]
        proxy.partfit = parts_fit.PartTerms(parts, centres, sheet, parts_doc, proxy.zones, height)
    return parts_doc


def misplaced(proxy, parts):
    """Indices of the parts whose visible projection leaves their part mask (share < PART_POOR) and of the
    parts that must be nearer the camera than another and are not: they move even when every view passes."""
    pf = proxy.partfit
    shares = proxy.part_shares(parts, range(len(parts)))
    return {i for (i, _), s in shares.items() if s < PART_POOR} | {i for i, _ in pf.broken(proxy.hull_list(parts))}


def fit(doc, sheet, kind="mass", views=None, margin=MARGIN, max_evals=None, wide=True, tilts=None,
        seconds=MAX_SECONDS, hard=None, joints=False, stages=None, partfit=False, parts_path=None, depth=False,
        split=True, grad=False, constraints=None):
    """(fitted doc, report). The doc is returned untouched when no view is under its gate
    (+ margin) or the parts on the failing band cannot move without breaking a rule.
    `wide=False` is the classic fit (front/left/back, dims and `at`); `tilts` pins the
    top/bottom/rts cameras ({view: tilt}, silhouette.json's), else each is swept on the start spec.
    `partfit` (opt-in: PIPELINE 23.L5-4 measured it neutral on the silhouettes) uses refs/<id>/parts.json, or `parts_path`, when there is one: part masks and depth order (PIPELINE 23.L5-4).
    `split`: the proxy scores the body against the sheet's body mask and the props against theirs (PIPELINE 25.L7-5).
    `depth` (opt-in, needs partfit) starts from Depth Anything's z and occlusion order (depth_map.py, PIPELINE 23.L5-4b).
    `stages` (subset of STAGES) runs one Powell per stage on its own parameters, 1/len of the budget each
    (PIPELINE 22.L4-3); None is the single Powell over every parameter.
    `grad` (opt-in, PIPELINE 26.L8-7) replaces Powell by Adam on the soft-silhouette twin of the proxy (fit_grad.py); the same
    objective judges and keeps the best point, `stages` do not apply.
    `constraints` (opt-in, L11-3, PIPELINE 29.L11-3): deltas (apply_deltas schema); each scale/radius/move becomes an interval on
    that part's dim/`at` parameter (apply_deltas.fit_limits), the part joins the free ones, and the best point inside the
    limits is returned even if the unconstrained start was cheaper."""
    t0 = time.monotonic()
    RF.scale_rig(doc.get("rig", "biped"), doc.get("rig_measure"))
    lathe_limb.set_rig(doc.get("rig", "biped"), doc.get("bones"))
    parts = baked(doc["parts"], sheet) if "parts" in doc else None
    gates = silhouette.gates_for(doc.get("rig"))
    concept = concept_masks(sheet, views or (WIDE_VIEWS if wide else FIT_VIEWS), wide)
    proxy = Proxy(concept, tuple(concept), hard=hard_canvas_edges(hard, tuple(concept)) if hard else None,
                  rig=doc.get("rig"))
    if parts:
        proxy.cams = proxy.pick_cams(parts, tilts)
        if split:
            proxy.set_split(sheet)
    before = proxy.ious(parts) if parts else {}
    failing = [v for v in proxy.views if v in gates and before.get(v, 1.0) < gates[v] + margin]
    report = {"views": list(proxy.views), "cams": proxy.cams, "before": before, "after": before,
              "failing": failing, "free": 0, "evals": 0, "changed": False}
    if not parts:
        return doc, report
    height = max(max(b[1][1] for b in map(preflight.bbox, parts)), 1e-6)
    attach_parts(proxy, doc, sheet, parts, height, wide, partfit, parts_path)
    if depth and proxy.partfit:
        import depth_map
        parts, report["depth"] = depth_map.depth_init(parts, proxy.partfit, parts_fit.load(sheet, parts_path),
                                                      depth_map.disparity(sheet), height, [spec_centre(p) for p in parts])
    limits = fit_limits_of(doc, parts, constraints, height)
    free = touched(proxy, parts, proxy.masks(parts), failing) if failing else []
    free = sorted({*free, *limits})
    if proxy.partfit:
        free = sorted({*free, *misplaced(proxy, parts)})
        report["assoc"] = proxy.partfit.assoc
    if not free:
        return doc, report
    free = [i for i in free if not preflight.is_prop(parts[i])]   # a prop only rides its anchor (23.L5-3)
    if not free:
        return doc, report
    groups = groups_of(parts, free)
    hood = cut_hull.hood_index(parts)
    # the anchor: a part that was connected to its parent stays connected (hard); each one that
    # was not costs LOOSE_W, so the fit can reconnect it
    parent_of = RF.parents(doc.get("rig", "biped"), doc.get("bones"))
    loose0 = loose_of(parts, parent_of)
    extra, bounds = search_space(parts, groups, hood, parent_of, loose0, wide, sheet_leg_w(doc, sheet), height, limits)
    targets, props = preflight.targets_from(sheet), preflight.load_props(pathlib.Path(sheet).parent.name)
    ctx = {"kind": kind, "targets": targets, "props": props, "parent_of": parent_of, "loose0": loose0,
           "held": broken_rules(parts, doc, kind, targets, props), "extra": extra, "order0": set(),
           "height": height, "joint_w": JOINT_W if joints else 0.0,
           "max_evals": max_evals or (MAX_EVALS if wide else FAST_EVALS), "deadline": time.monotonic() + seconds}
    if proxy.partfit:
        ctx["order0"] = proxy.partfit.broken(proxy.hull_list(parts))
        report["depth_pairs"] = [len(proxy.partfit.pairs), len(ctx["order0"])]
    objective = Objective(proxy, doc, parts, groups, free, ctx)
    start = proxy.loss(parts, free=free) + LOOSE_W * len(loose0)
    masks = stage_masks(parts, groups, extra, stages) if stages else None
    report.update(search(grad, objective, groups, bounds, masks, (parts, extra, proxy, height), seconds))
    best = objective.best
    report.update(free=len(free), groups=len(groups), evals=objective.n, loss=[round(start, 4), round(best["f"], 4)],
                  seconds=round(time.monotonic() - t0, 1))
    if best["x"] is None or best["f"] >= start - 1e-4 and not limits:
        return doc, report
    report["constrained"] = sorted(limits)
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
    ap.add_argument("--fit-joints", action="store_true",
                    help="adds the joint term (knee and elbow height vs the sheet's width step)")
    ap.add_argument("--depth", action="store_true",
                    help="start from Depth Anything V2 small's z and occlusion order (needs parts.json; PIPELINE 23.L5-4b)")
    ap.add_argument("--fit-grad", action="store_true",
                    help="Adam on a differentiable soft-silhouette proxy instead of Powell (fit_grad.py, PIPELINE 26.L8-7)")
    ap.add_argument("--constraints", type=pathlib.Path, default=None,
                    help="a diagnosis.json: its scale/radius/move deltas become per-part limits of the fit (L11-3)")
    ap.add_argument("--fit-parts", action="store_true", help="use refs/<id>/parts.json: part masks and depth order (L5-4)")
    ap.add_argument("--parts", type=pathlib.Path, default=None,
                    help="a parts.json other than the one beside the sheet (implies --fit-parts)")
    args = ap.parse_args()
    doc = json.loads(args.spec.read_text())
    views = tuple(args.views.split(",")) if args.views else None
    out, report = fit(doc, args.sheet, args.kind, views, args.margin, wide=not args.fast,
                      tilts=V.parse_tilts(args.tilts), seconds=args.seconds, hard=args.hard, joints=args.fit_joints,
                      partfit=args.fit_parts or bool(args.parts) or args.depth, parts_path=args.parts, depth=args.depth, grad=args.fit_grad,
                      constraints=json.loads(args.constraints.read_text()).get("deltas") if args.constraints else None)
    args.out.write_text(json.dumps(out, indent=2))
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
