#!/usr/bin/env python3
"""Deform a GLB's vertices onto the approved sheet's outlines (Sketch2Mesh, PIPELINE 24.L6-5).

    python3.14 tools/blender/deform_to_sheet.py <in.glb> <sheet.jpg> <out.glb>
        [--views front,left,back,top,bottom,rts] [--iters 4] [--band 0.4-0.7] [--rig spider]

Per view (Sketch2Mesh §3.3, Fig. 2c): the model's external contour = the vertices that project onto the
outer boundary of its rendered mask; each goes toward the nearest point of the sheet panel's outline, at
most STEP * H per step, in the view plane. The rest of the mesh follows through a uniform-Laplacian
smoothing solved with scipy.sparse. Eq. 6 (partial regularisation): the pull weight falls to zero away
from the height bands that carry red (sheet bare) or green (model outside the sheet), `--band lo-hi`
(fractions of H) forces those bands instead. A step is refused when it adds slivers or flips faces, and
dropped when the weighted mean IoU of the views does not grow (views.VIEW_WEIGHTS[rig]: the legs of a spider
or quadruped only read from above and from the gameplay camera). Only POSITION and NORMAL bytes of the GLB
change: skin weights, UVs, materials and clips stay as they are. PIPELINE 25.L7-1: top, bottom and rts (the
gameplay camera, projected like fit_spec.project) pull too; the camera of each is the run's (silhouette.json)
or, without one, the best of the sweep.

No Blender: the masks are rasterised here (PIL) with the same bbox normalisation silhouette.py uses.
"""
import argparse
import json
import math
import pathlib
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage, sparse
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import spsolve

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mesh_lint as ML  # noqa: E402
import silhouette as S  # noqa: E402
from views import RTS, TILTS, layout_of, parse_tilts, rts_offset, weight_of  # noqa: E402

STEP = 0.05           # largest move of a vertex per step, fractions of the model height
CONTOUR_PX = 1.5      # a vertex this close (canvas px) to the mask's outer boundary is on the contour
DAMP = (1.0, 0.5, 0.25)  # a refused step is tried again at these shares of its length
REACH = 0.10         # a contour vertex farther than this (H) from the sheet's outline is not pulled: that is another part
PULL = 10.0           # weight of a contour vertex's target against the smoothness term
ANCHOR = 5.0          # weight of "stay where you are" where the band weight is 0
BAD_ON, BAD_FULL = 0.003, 0.015   # band share of the sheet/model that is red+green: weight 0 below, 1 above
SLIVER_MAX = 0.05     # share of triangles under mesh_lint.SLIVER_DEG a step may leave, or the share before + SLIVER_GROW
SLIVER_GROW = 0.05   # the union bodies of L6-4 start at 19-28 % slivers: an absolute 5 % cap would refuse every step
EXTRA_SLIVER = 0.02   # what the top/bottom/rts phase (25.L7-1) may add on top of the ortographic phase
UNTANGLE = 8          # rounds of pulling the vertices of turned faces back toward where they were
SLIVER_AREA = 0.30    # unflip: a turned face under this share of the median area has its winding swapped
TINY = 0.02           # a face under this share of the median area is a sliver whose orientation does not count
SOLE = 0.02           # vertices this close to the ground (H) keep their height: the pivot stays put
PROP_OWN = 0.3        # a component is a prop's when this share of its vertices lies in the prop's mask
PROPS_OWN_MASK = False  # NEGATIVE (25.L7-5): a prop pulled only toward its own mask cost n005 left -0.02..-0.03 IoU; props keep the whole outline
SS = 2                # supersampling of the PIL raster
GUARD = 0.01          # no view may end more than this under its IoU at the start
PULL_MIN = 0.4        # a top/bottom/rts that starts under this IoU does not agree with the 3 panels (n00H rts .23): watched only


def read(path):
    """(bytearray of the file, doc, offset of the BIN data)."""
    data = bytearray(pathlib.Path(path).read_bytes())
    jlen = int.from_bytes(data[12:16], "little")
    doc = json.loads(bytes(data[20:20 + jlen]).decode("utf8").rstrip("\0 "))
    return data, doc, 28 + jlen


def prims(doc):
    return [p for m in doc["meshes"] for p in m["primitives"]]


def acc_slice(doc, idx, base):
    """(byte offset, count) of a tightly packed float VEC3 accessor."""
    a = doc["accessors"][idx]
    view = doc["bufferViews"][a["bufferView"]]
    assert a["componentType"] == 5126 and a["type"] == "VEC3" and not view.get("byteStride")
    return base + view.get("byteOffset", 0) + a.get("byteOffset", 0), a["count"]


def geometry(data, doc, base):
    """Per primitive the writable views over `data` (positions, normals, triangle indices; glTF axes) and the
    merged triangles (indices into the merged vertices)."""
    out, tri, off = [], [], 0
    for p in prims(doc):
        views = []
        for key in ("POSITION", "NORMAL"):
            o, n = acc_slice(doc, p["attributes"][key], base)
            views.append(np.frombuffer(data, np.float32, n * 3, o).reshape(n, 3))
        idx = doc["accessors"][p["indices"]]
        view = doc["bufferViews"][idx["bufferView"]]
        dtype = np.dtype(ML.COMP[idx["componentType"]])
        start = base + view.get("byteOffset", 0) + idx.get("byteOffset", 0)
        views.append(np.frombuffer(data, dtype, idx["count"], start).reshape(-1, 3))
        tri.append(views[2].astype(np.int64) + off)
        out.append(views)
        off += len(views[0])
    return out, np.vstack(tri)


def to_z_up(p):
    """glTF (x, y up, z toward the front) -> the frame of the cameras (x, y = -z, z up)."""
    return np.stack([p[:, 0], -p[:, 2], p[:, 1]], 1).astype(np.float64)


def from_z_up(p):
    return np.stack([p[:, 0], p[:, 2], -p[:, 1]], 1)


def weld(pos):
    """(unique positions, index of each vertex in them): split normals and UV seams are one vertex."""
    _, first, inv = np.unique(np.round(pos / ML.WELD).astype(np.int64), axis=0, return_index=True, return_inverse=True)
    return pos[first], inv.reshape(-1)


class View:
    """One camera of the sheet: image axes (ru right, rv up, unit vectors of the Z-up frame), the mirror
    that matched the panel, the panel (normalised) and whether the view pulls the mesh or only guards it."""

    def __init__(self, name, ru, rv, mirror, concept, active, props=None, frame_on=None):
        self.name, self.ru, self.rv, self.mirror, self.concept, self.active = name, ru, rv, mirror, concept, active
        self.frame_on = frame_on         # vertex mask the canvas frame fits (the body, 29.L11-0b); None = every vertex
        self.props = list((props or {}).values())       # the prop masks of this view (silhouette.prop_masks); [] = no split
        self.allowed = {0: concept & ~np.any(self.props, axis=0)} if self.props else {}
        self.allowed |= {i + 1: m for i, m in enumerate(self.props)}
        self.goals = {}

    def goal(self, key):
        """(iy, ix) of the nearest point of the sheet's outline that key may be pulled to (PIPELINE 25.L7-5): key 0
        the body (the outline outside the props' masks), i the i-th prop's mask, len(props) + 1 any prop, -1 the
        whole outline. None when that outline has no pixel."""
        if key not in self.goals:
            edge = boundary(self.concept)
            edge = edge & self.allowed[key] if key >= 0 else edge
            self.goals[key] = ndimage.distance_transform_edt(~edge, return_indices=True)[1] if edge.any() else None
        return self.goals[key]

    def uv(self, pos):
        return np.stack([pos @ self.ru, pos @ self.rv], 1)


def frame(uv, mirror=1, on=None):
    """Canvas map of the points' bbox, the way silhouette.normalize fits a mask: (to_canvas, scale). `on`: the bbox of
    these points only (a boolean mask), as a body-framed panel (silhouette.framed_panels) fits the body."""
    uv = uv * np.array([mirror, 1.0])
    lo, hi = (uv if on is None else uv[on]).min(0), (uv if on is None else uv[on]).max(0)
    w, h = hi - lo
    s = S.CANVAS_H / h
    if w * s > S.CANVAS_W:
        s = S.CANVAS_W / w
    x0, y0 = (S.CANVAS_W - w * s) / 2, (S.CANVAS_H - h * s) / 2
    return (lambda q: np.stack([(q[:, 0] * mirror - lo[0]) * s + x0, (hi[1] - q[:, 1]) * s + y0], 1)), s


def raster(xy, tri):
    """Boolean canvas mask of the triangles at canvas coordinates xy."""
    img = Image.new("L", (S.CANVAS_W * SS, S.CANVAS_H * SS), 0)
    draw = ImageDraw.Draw(img)
    for t in tri:
        draw.polygon([tuple(v) for v in (xy[t] - 0.5) * SS + 0.5 * SS], fill=255)
    big = np.asarray(img).reshape(S.CANVAS_H, SS, S.CANVAS_W, SS).mean(axis=(1, 3))
    return big >= 128


def boundary(mask):
    filled = ndimage.binary_fill_holes(mask)
    return filled & ~ndimage.binary_erosion(filled)


def band_weights(concept, model, band):
    """Eq. 6: weight per height band (feet first) from the red+green share of each band, or 1/0 from `band`."""
    mid = (np.arange(S.BANDS) + 0.5) / S.BANDS
    if band:
        return ((mid >= band[0]) & (mid <= band[1])).astype(float)
    c = S.coupling(concept, model)["bands"]
    bad = np.array(c["uncovered"]) + np.array(c["spill"])
    return np.clip((bad - BAD_ON) / (BAD_FULL - BAD_ON), 0.0, 1.0)


def laplacian(tri, n):
    """Uniform Laplacian I - D^-1 A of the welded mesh."""
    e = np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]])
    e = np.unique(np.sort(e, axis=1), axis=0)
    adj = sparse.coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n))
    adj = (adj + adj.T).tocsr()
    deg = np.maximum(np.asarray(adj.sum(1)).ravel(), 1.0)
    return sparse.identity(n, format="csr") - sparse.diags(1.0 / deg) @ adj


def solve(lap, target, a, b):
    """Minimise |L d|^2 + sum a |d - target|^2 + sum b |d|^2: the contour follows its targets, the interior is smooth."""
    system = (lap.T @ lap + sparse.diags(a + b)).tocsc()
    return np.stack([spsolve(system, a * target[:, k]) for k in range(target.shape[1])], 1)


def pixels(xy, shape):
    return np.clip(np.floor(xy).astype(int), 0, [shape[1] - 1, shape[0] - 1])


def target_keys(view, xy, owner, body):
    """Which outline each vertex is pulled to (View.goal): the body component the body's, every other component
    (a prop) the mask of the prop most of its vertices lie in, else (a prop the sheet does not show here) -1: the whole outline,
    as before; -1 too when the view has no props."""
    keys = np.full(len(xy), -1)
    if not view.props:
        return keys
    px = pixels(xy, view.concept.shape)
    keys[owner == body] = 0
    for c in set(owner[owner != body].tolist()):
        mine = owner == c
        hits = [m[px[mine, 1], px[mine, 0]].mean() for m in view.props]
        keys[mine] = int(np.argmax(hits)) + 1 if PROPS_OWN_MASK and max(hits) >= PROP_OWN else -1
    return keys


def pull(view, model_mask, xy, keys):
    """Canvas displacement of each vertex toward the sheet's outline that its key allows, 0 off the model's contour."""
    px = pixels(xy, model_mask.shape)
    near = ndimage.distance_transform_edt(~boundary(model_mask))[px[:, 1], px[:, 0]] <= CONTOUR_PX
    move = np.zeros_like(xy)
    for key in set(keys.tolist()):
        goal, sel = view.goal(key), keys == key
        if goal is None:
            near[sel] = False
            continue
        iy, ix = goal
        move[sel] = np.stack([ix[px[sel, 1], px[sel, 0]], iy[px[sel, 1], px[sel, 0]]], 1) + 0.5 - xy[sel]
    near &= np.linalg.norm(move, axis=1) <= REACH * S.CANVAS_H
    return np.where(near[:, None], move, 0.0), near


def view_state(pos, tri, view):
    """(canvas coords, model mask, scale) of the welded Z-up positions in one view."""
    uv = view.uv(pos)
    to_canvas, s = frame(uv, view.mirror, view.frame_on)
    xy = to_canvas(uv)
    return xy, raster(xy, tri), s


def clamp(d, limit):
    return d * np.minimum(1.0, limit / np.maximum(np.linalg.norm(d, axis=1), 1e-12))[:, None]


def step_view(pos, tri, lap, view, band, height, ground, owner=None, body=0):
    """The welded positions after one deformation step in `view`."""
    xy, mask, s = view_state(pos, tri, view)
    wb = band_weights(view.concept, mask, band)
    if view.name in S_TILTED + ("rts",):         # no height axis: the whole outline is pulled
        wb = np.ones_like(wb)
    mid = (np.arange(S.BANDS) + 0.5) / S.BANDS
    w = np.interp((pos[:, 2] - pos[:, 2].min()) / height, mid, wb)
    move, near = pull(view, mask, xy, target_keys(view, xy, owner if owner is not None else np.zeros(len(pos), int), body))
    d = clamp(np.stack([move[:, 0] / s * view.mirror, -move[:, 1] / s], 1), STEP * height)
    d = clamp(solve(lap, d, PULL * w * near, ANCHOR * (1 - w) + 1e-3), STEP * height)
    world = d[:, :1] * view.ru + d[:, 1:] * view.rv
    world[ground, 2] = 0.0
    return pos + world


def reference(pos, tri, nor):
    """(direction expected of each face, area floor): the face's own normal, or the sum of its corners' normals for
    a zero-area sliver (a boolean leaves some), whose own normal is noise. Floor = TINY of the median area."""
    q = pos[tri]
    cross = np.cross(q[:, 1] - q[:, 0], q[:, 2] - q[:, 0])
    area = np.linalg.norm(cross, axis=1)
    floor = TINY * np.median(area)
    return np.where((area > floor)[:, None], cross, nor[tri].sum(1)), floor


def turned(ref, new, tri):
    """Boolean per face: of real size in `new` and facing against `ref`."""
    q = new[tri]
    cross = np.cross(q[:, 1] - q[:, 0], q[:, 2] - q[:, 0])
    return (np.linalg.norm(cross, axis=1) > ref[1]) & (np.einsum("fd,fd->f", ref[0], cross) < 0)


def untangle(ref, old, new, tri):
    """`new` with the vertices of every turned face pulled back toward `old` by halves until none is turned."""
    new = new.copy()
    for _ in range(UNTANGLE):
        bad = turned(ref, new, tri)
        if not bad.any():
            break
        v = np.unique(tri[bad])
        new[v] = old[v] + 0.5 * (new[v] - old[v])
    return new


def sliver_share(pos, tri):
    """Share of the triangles whose smallest angle is under mesh_lint.SLIVER_DEG."""
    p = pos[tri]
    area = np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1)
    live = area > 1e-10
    return float((ML.angles_min(p[live]) < ML.SLIVER_DEG).mean()) if live.any() else 0.0


def measure(pos, tri, views):
    """view name -> {iou, uncovered, spill} of the rasterised model against the sheet panels."""
    out = {}
    for view in views:
        mask = view_state(pos, tri, view)[1]
        c = S.coupling(view.concept, mask)
        out[view.name] = {"iou": round(S.iou(view.concept, mask), 4), "uncovered": c["uncovered"], "spill": c["spill"]}
        if view.props:      # body / props told apart (25.L7-5); the gate stays on the totals
            out[view.name].update(S.coupling_split(view.concept, mask, np.any(view.props, axis=0)))
    return out


def mean_iou(report, views, weight=None, active=True):
    """Weighted mean IoU of the pulling (or only watched) views; `weight` {view: w}, 1 where absent."""
    chosen = [v.name for v in views if v.active == active]
    w = np.array([(weight or {}).get(n, 1.0) for n in chosen] or [1.0])
    return float(np.dot(w, [report[n]["iou"] for n in chosen] or [0.0]) / w.sum())


def accept(old, new, tri, views, ref, floor, limit, weight=None):
    """True when the step keeps slivers and normals sane, the pulling views' mean IoU does not drop and no
    view (pulling or only watched, a top/bottom) ends more than GUARD under `floor` (its IoU at the start)."""
    if turned(ref, new, tri).any() or sliver_share(new, tri) > limit:
        return False
    a, b = measure(old, tri, views), measure(new, tri, views)
    if any(b[v.name]["iou"] < floor[v.name] - GUARD for v in views):
        return False
    return mean_iou(b, views, weight) >= mean_iou(a, views, weight) - 1e-4


FRONT_AXES = {"front": ((1, 0, 0), (0, 0, 1)), "left": ((0, -1, 0), (0, 0, 1)), "back": ((-1, 0, 0), (0, 0, 1))}
S_TILTED = ("top", "bottom")
SIX = ("front", "left", "back", "top", "bottom", "rts")


def tilted_axes(name, tilt):
    """Image axes of views.camera(name, tilt): x to the right, up = (0, cos, sin) of the camera's x rotation."""
    theta = math.radians(tilt if name == "top" else 180 - tilt)
    return np.array([1.0, 0, 0]), np.array([0.0, math.cos(theta), math.sin(theta)])


def rts_axes(cam):
    """Image axes of the gameplay camera at cam = (elevation, azimuth), as fit_spec.project: it looks at the centre."""
    d = -np.asarray(rts_offset(*cam))
    d /= np.linalg.norm(d)
    right = np.cross(d, [0.0, 0.0, 1.0])
    right /= np.linalg.norm(right)
    return right, np.cross(right, d)


def candidates(name, panel, cam=None):
    """(ru, rv, concept) of every way the sheet's top/bottom could be drawn: tilt sweep x panel turned or not;
    the rts: the (elevation, azimuth) sweep, never mirrored or turned. `cam` pins the sweep to one camera."""
    if name == "rts":
        for c in [tuple(cam)] if cam else RTS:
            yield (*rts_axes(c), S.normalize(panel))
        return
    for turned in (False, True):
        concept = S.normalize(S.rot180(panel) if turned else panel)
        for tilt in [cam] if cam is not None else TILTS:
            yield (*tilted_axes(name, tilt), concept)


def best_option(name, options, pos, tri, on=None):
    """(option, mirror) whose raster matches the panel best; the side views pick the mirror of that option by the
    shift-tolerant IoU (silhouette.pick_variant: a prop that widens the sheet's bbox must not decide the side)."""
    rasters = {(i, m): view_state(pos, tri, View(name, o[0], o[1], m, o[2], True, frame_on=on))[1]
               for i, o in enumerate(options) for m in ((1,) if name == "rts" else (1, -1))}
    i, m = max(rasters, key=lambda k: S.iou(options[k[0]][2], rasters[k]))
    if name in S.SIDE_VIEWS and S.FLIP_SIDE:
        m = (1, -1)[S.pick_variant(options[i][2], [rasters[i, 1], rasters[i, -1]], name)]
    return options[i], m


def best_oriented(name, options, pos, tri, on=None):
    """best_option over `options` = candidates(): the panel as drawn (first half) then turned 180 degrees (second half).
    Turned only when it matches the model better by S.FLIP_MARGIN, the gate's rule (silhouette.detect_rotated): a free
    choice picked it on a .02 edge (n017 top .82 -> .86) and the optimiser fitted what the gate never measures."""
    half = len(options) // 2
    plain, turned = (best_option(name, options[a:b], pos, tri, on) for a, b in ((0, half), (half, None)))
    score = lambda best: S.iou(best[0][2], view_state(pos, tri, View(name, best[0][0], best[0][1], best[1], best[0][2], True, frame_on=on))[1])  # noqa: E731
    return turned if score(turned) - score(plain) > S.FLIP_MARGIN else plain


def make_views(pos, tri, panels, pulling, props=None, cams=None):
    """Views of the sheet: the pulling ones (`pulling` names) and the guards (the other top/bottom). The mirror
    of each (and tilt / turn of top/bottom, camera of the rts) is the one whose raster matches the panel best, like
    silhouette.py; `cams` {view: tilt or (elevation, azimuth)} pins the camera the run's silhouette.json chose."""
    views = []
    owner, main = owner_body(tri, len(pos))
    for name, panel in panels.items():
        options = [(*np.array(FRONT_AXES[name], float), S.normalize(panel))] if name in FRONT_AXES \
            else list(candidates(name, panel, (cams or {}).get(name)))
        on = owner == main if getattr(panel, "box", None) is not None else None     # body-framed panel: fit the body
        best = (best_oriented if name in S_TILTED else best_option)(name, options, pos, tri, on)
        (ru, rv, concept), mirror = best
        views.append(View(name, ru, rv, mirror, concept, name in pulling, (props or {}).get(name), on))
    return views


def owner_body(tri, n):
    """(component id of every welded vertex, the id of the largest one: the body)."""
    edges = np.r_[tri[:, :2], tri[:, 1:]]
    owner = connected_components(sparse.coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(n, n)),
                                 directed=False)[1]
    return owner, int(np.argmax(np.bincount(owner)))


def view_axes(name, cam=0):
    """(ru, rv) of a view at camera `cam` (a tilt, or the rts' (elevation, azimuth))."""
    if name in FRONT_AXES:
        return np.array(FRONT_AXES[name], float)
    return rts_axes(cam) if name == "rts" else tilted_axes(name, cam)


def body_fractions(pos, tri, ru, rv):
    """(x0, y0, x1, y1), as fractions of the model's projected bbox (y down), of the body (the largest welded component)
    in one view: where silhouette.model_boxes puts the box a body-framed concept is matched with. None when the
    model is all one component (its body is its bbox)."""
    owner, main = owner_body(tri, len(pos))
    on = owner == main
    if on.all():
        return None
    uv = np.stack([pos @ ru, pos @ rv], 1)
    (lx, ly), (hx, hy), (bl, bh) = uv.min(0), uv.max(0), (uv[on].min(0), uv[on].max(0))
    return ((bl[0] - lx) / (hx - lx), (hy - bh[1]) / (hy - ly), (bh[0] - lx) / (hx - lx), (hy - bl[1]) / (hy - ly))


def deform(pos, tri, panels, pulling, iters=4, band=None, nor=None, props=None, cams=None, rig=None):
    """(new welded Z-up positions, report). Rounds of one step per pulling view, each refused when it makes things
    worse. Two phases (25.L7-1): the front/left/back alone, exactly as 24.L6-5 did (+SLIVER_GROW slivers, the top and
    bottom only watched); then every pulling view, weighted, nothing may end more than GUARD under what phase 1
    left it and the slivers may grow EXTRA_SLIVER more. A top/bottom/rts drawn so unlike the 3 panels that it starts
    under PULL_MIN IoU is only watched. `nor`: the welded Z-up vertex normals, the facing of the zero-area faces
    (None: their own). `props`: {view: {prop name: mask}} (silhouette.prop_masks): the body (the largest welded
    component) is pulled only toward the outline outside them, each other component toward its own prop's
    (25.L7-5). `cams`: the pinned top/bottom/rts cameras; `rig`: whose VIEW_WEIGHTS count in the acceptance."""
    views = make_views(pos, tri, panels, pulling, props, cams)
    owner, body = owner_body(tri, len(pos))
    weight = {v.name: weight_of(rig, v.name) for v in views}
    ref = reference(pos, tri, np.zeros_like(pos) if nor is None else nor)
    height = float(np.ptp(pos[:, 2]))
    ground = pos[:, 2] < pos[:, 2].min() + SOLE * height
    lap = laplacian(tri, len(pos))
    slivers = sliver_share(pos, tri)
    before = measure(pos, tri, views)
    report = {"before": before, "slivers_before": round(slivers, 4), "steps": 0, "refused": 0}
    extra = [v for v in views if v.active and v.name not in FRONT_AXES and before[v.name]["iou"] >= PULL_MIN]
    for v in views:
        v.active = v.active and v.name in FRONT_AXES

    def rounds(cur, seen, floor, limit):
        for _ in range(iters):
            for view in [v for v in seen if v.active]:
                full = untangle(ref, cur, step_view(cur, tri, lap, view, band, height, ground, owner, body), tri)
                tries = [cur + k * (full - cur) for k in DAMP]
                best = next((t for t in tries if accept(cur, t, tri, seen, ref, floor, limit, weight)), None)
                report["refused"] += best is None
                if best is not None:
                    cur, report["steps"] = best, report["steps"] + 1
        return cur

    first = {k: r["iou"] for k, r in before.items()}
    cur = rounds(pos, [v for v in views if v.name != "rts"], first, max(SLIVER_MAX, slivers + SLIVER_GROW))
    if extra:
        for v in extra:
            v.active = True
        floor = {k: r["iou"] for k, r in measure(cur, tri, views).items()}
        cur = rounds(cur, views, floor, sliver_share(cur, tri) + EXTRA_SLIVER)
    report.update(after=measure(cur, tri, views), slivers_after=round(sliver_share(cur, tri), 4),
                  turned=int(turned(ref, cur, tri).sum()), mirrors={v.name: v.mirror for v in views},
                  weights=weight, pulled=[v.name for v in views if v.active])
    return cur, report


def new_normals(new_pos, old_nor, tri):
    """Normals of the deformed mesh: the area-weighted sum of the new face normals around each vertex index
    (a split vertex belongs to one smoothing group, so flat faces stay flat and smooth ones stay smooth)."""
    q = new_pos[tri]
    face = np.cross(q[:, 1] - q[:, 0], q[:, 2] - q[:, 0])
    acc = np.zeros_like(new_pos)
    for k in range(3):
        np.add.at(acc, tri[:, k], face)
    length = np.linalg.norm(acc, axis=1)
    return np.where(length[:, None] > 1e-12, acc / np.maximum(length, 1e-12)[:, None], old_nor)


def unflip(pos, nor, tri):
    """Triangles with the winding of every near-degenerate face that disagrees with its vertex normals swapped
    (mesh_lint "flipped == 0": a boolean's zero-area slivers get a tiny area from the deformation and a random side)."""
    q = pos[tri]
    cross = np.cross(q[:, 1] - q[:, 0], q[:, 2] - q[:, 0])
    area = np.linalg.norm(cross, axis=1) / 2
    bad = (area > 1e-8 * np.ptp(pos[:, 1]) ** 2) & (np.einsum("fd,fd->f", cross, nor[tri].sum(1)) < 0)
    bad &= area < SLIVER_AREA * np.median(area)
    out = tri.copy()
    out[bad] = tri[bad][:, [0, 2, 1]]
    return out


def write(data, doc, base, parts, new_pos, new_nor, new_tri):
    """Put the deformed positions / normals (glTF axes, one block per primitive) and the re-wound triangles back
    into `data`, fix min/max."""
    start, face = 0, 0
    for p, (pos, nor, idx) in zip(prims(doc), parts):
        n = len(pos)
        pos[:] = new_pos[start:start + n]
        nor[:] = new_nor[start:start + n]
        idx[:] = new_tri[face:face + len(idx)] - start
        face += len(idx)
        acc = doc["accessors"][p["attributes"]["POSITION"]]
        acc["min"], acc["max"] = (pos.min(0).tolist(), pos.max(0).tolist())
        start += n
    return data


def repack(data, doc, base):
    """The file bytes with the edited JSON chunk (only numbers changed; re-padded to 4 bytes, lengths fixed)."""
    text = json.dumps(doc, separators=(",", ":")).encode()
    text += b" " * (-len(text) % 4)
    body = bytes(data[base - 8:])         # the BIN chunk header and data
    head = bytearray(data[:12]) + len(text).to_bytes(4, "little") + data[16:20] + text
    out = bytes(head) + body
    return out[:8] + len(out).to_bytes(4, "little") + out[12:]


def welded_normals(nor, inv, count):
    """Unit normals per welded vertex: the sum of the normals of the vertices that were welded into it."""
    acc = np.zeros((count, 3))
    np.add.at(acc, inv, nor)
    return acc / np.maximum(np.linalg.norm(acc, axis=1), 1e-12)[:, None]


def parse_band(arg):
    lo, hi = (float(x) for x in arg.split("-"))
    return lo, hi


def sheet_panels(sheet, views, layout="unit"):
    """Raw panels of the sheet: the pulling `views` and, as guards, the top/bottom that are not among them; the
    gameplay camera's drawing (sheet-rts.jpg, when it exists) only when `rts` is among the views."""
    panels = S.framed_panels(pathlib.Path(sheet), layout=layout)
    out = {v: p for v, p in panels.items() if v in views or v in S_TILTED}
    rts = S.rts_path(pathlib.Path(sheet))
    if "rts" in views and layout == "unit" and rts.exists():
        out["rts"] = S.foreground(rts, 768)
    return out


def transform(glb, out, fn, suffix=".deform.json"):
    """Read `glb`, give `fn(welded Z-up positions, triangles, welded Z-up normals)` -> (new positions, report),
    write `out` with the new positions / normals; returns the report. Shared with align_features.py."""
    return rewrite(glb, out, lambda uniq, tri, nor, file: fn(uniq, tri, nor), suffix)


def weld_mesh(data, doc, base):
    """(parts, file triangles, file positions, file normals, welded Z-up positions, welded index of each file vertex,
    welded triangles without the degenerate ones) of a read() GLB."""
    parts, tri_all = geometry(data, doc, base)
    old = np.vstack([p for p, _, _ in parts]).astype(np.float64)
    old_nor = np.vstack([n for _, n, _ in parts]).astype(np.float64)
    uniq, inv = weld(to_z_up(old))
    tri = inv[tri_all]
    tri = tri[(tri[:, 0] != tri[:, 1]) & (tri[:, 1] != tri[:, 2]) & (tri[:, 0] != tri[:, 2])]
    return parts, tri_all, old, old_nor, uniq, inv, tri


def welded_mesh(glb):
    """(welded Z-up positions, welded triangles) of a GLB."""
    *_, uniq, _, tri = weld_mesh(*read(glb))
    return uniq, tri


def rewrite(glb, out, change, suffix=".deform.json"):
    """Write `out` = `glb` with the welded Z-up positions replaced by change(uniq, tri, normals, file) -> (new uniq,
    report), `file` = (welded index of each file vertex, the file's triangles); the report goes beside it as
    <out><suffix>. Shared with optimize_verts.py (PIPELINE 24.L6-7)."""
    data, doc, base = read(glb)
    parts, tri_all, old, old_nor, uniq, inv, tri = weld_mesh(data, doc, base)
    new_uniq, report = change(uniq, tri, welded_normals(to_z_up(old_nor), inv, len(uniq)), (inv, tri_all))
    new = from_z_up(new_uniq[inv]).astype(np.float32).astype(np.float64)     # what the file will hold
    nor = new_normals(new, old_nor, tri_all)
    write(data, doc, base, parts, new, nor, unflip(new, nor, tri_all))
    pathlib.Path(out).write_bytes(repack(data, doc, base))
    pathlib.Path(out).with_suffix(suffix).write_text(json.dumps(report, indent=2))
    return report


def run(glb, sheet, out, views=("front", "left", "back"), iters=4, band=None, layout="unit", split=True, cams=None, rig=None):
    """Deform `glb` onto the sheet and write `out`; returns the report (before / after per view, slivers).
    Default 3 views; `views=SIX` enables the top/bottom/rts of 25.L7-1 (opt-in)."""
    panels = sheet_panels(sheet, views, layout)
    views = tuple(v for v in views if v in panels)       # no drawing of a view, no pull
    props = {v: S.prop_masks(sheet, v, layout, panels) for v in views} if split else {}
    report = transform(glb, out, lambda pos, tri, nor: deform(pos, tri, panels, views, iters, band, nor, props, cams, rig))
    pathlib.Path(out).with_suffix(".deform.json").write_text(json.dumps(report, indent=2))
    return report


def run_cams(args):
    """The top/bottom/rts cameras the gate measures this run with: --tilts, else the ones the run's silhouette.json
    chose ("tilt": {"top": -30, "rts": [65, 60]}), else None: before the shape stage has measured one the deformation
    and the vertex optimiser sweep. One definition for fit, deform, verts, gate and colour (L12-1)."""
    if getattr(args, "tilts", ""):
        return parse_tilts(args.tilts)
    path = args.out / "silhouette.json"
    tilt = json.loads(path.read_text()).get("tilt") if path.exists() else None
    return {v: tuple(c) if isinstance(c, list) else c for v, c in tilt.items()} if tilt else None


def apply(glb, args):
    """spec_pipeline hook: deform `glb` in place when the run wants it (args.deform on a unioned body),
    keeping the original beside it as <stem>-raw.glb. Returns the report or None."""
    if not (getattr(args, "deform", False) and getattr(args, "union_body", False)):
        return None
    glb = pathlib.Path(glb)
    raw = glb.with_name(f"{glb.stem}-raw.glb")
    raw.write_bytes(glb.read_bytes())
    return run(raw, args.sheet, glb, layout=layout_of(args.kind), cams=run_cams(args), rig=getattr(args, "rig", None))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("glb")
    ap.add_argument("sheet")
    ap.add_argument("out")
    ap.add_argument("--views", default="front,left,back",
                    help="front,left,back,top,bottom,rts enables the six weighted views (25.L7-1, opt-in)")
    ap.add_argument("--no-split", action="store_true", help="the whole outline for every vertex, body and props (before 25.L7-5)")
    ap.add_argument("--rig", default=None, help="the rig family, for views.VIEW_WEIGHTS")
    ap.add_argument("--iters", type=int, default=4)
    ap.add_argument("--band", type=parse_band, default=None, help="deform only this height range, e.g. 0.4-0.7")
    a = ap.parse_args()
    r = run(a.glb, a.sheet, a.out, tuple(a.views.split(",")), a.iters, a.band, split=not a.no_split, rig=a.rig)
    for v in r["after"]:
        b, f = r["before"][v], r["after"][v]
        print(f"{v:6} IoU {b['iou']:.3f} -> {f['iou']:.3f}  red {b['uncovered']:.3f} -> {f['uncovered']:.3f}  "
              f"green {b['spill']:.3f} -> {f['spill']:.3f}")
    print(f"steps {r['steps']} refused {r['refused']} slivers {r['slivers_before']} -> {r['slivers_after']} "
          f"turned {r['turned']}")


if __name__ == "__main__":
    main()
