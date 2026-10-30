#!/usr/bin/env python3
"""Low-poly look of a clay GLB: three numbers, a planar snap and the creases of the hard sheet (PIPELINE 30.L12-9).

    python3.14 tools/blender/look.py metrics <run dir> --id n02X [--glb clay.glb]
    python3.14 tools/blender/look.py snap <in.glb> <out.glb> --id n02X [--creases]

Metrics (numpy only, welded Z-up positions as deform_to_sheet.py reads them):
    crease_chamfer  per view (front / left / back) precision / recall, at SLACK px of the gate's canvas, between the model's
                    hard edges (dihedral >= CREASE_DEG, both faces seen by the camera) and the ink inside the sheet-hard's drawing
    planarity       share of the area in flat patches (connected faces within PLANE_DEG of the patch's seed normal, MIN_FACES or more)
    wire_entropy    Shannon entropy (0..1) of the edge directions measured in their face's plane (a grid is low, a random
                    triangulation is high), and the number of edges per 1000 triangles
Snap (`snap`): faces are grouped into planar regions (top-down: k-means on the normals, then every region that is not flat to
SNAP_TOL * H is split in two), a plane is fitted per region of MIN_FACES or more, and every vertex goes to the intersection of the
planes of its regions (a plane: projection, two: a line, three: a point; a small pull to where it was settles the degenerate cases).
`creases`: edges that run along the ink of the sheet-hard (both ends within MARK_PX of it, direction along the line) are region
borders, so the planes meet there. A step is refused (damped 1, 1/2, 1/4) when it turns a face, adds slivers or lowers a view's
IoU by more than IOU_SLIP or raises its spill by more than SPILL_SLIP. The triangles stay where they are: a coplanar edge is not
dissolved (a GLB edit in place cannot change the index count)."""
import argparse
import json
import math
import pathlib
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import align_features as AF  # noqa: E402
import deform_to_sheet as D  # noqa: E402
import silhouette as S  # noqa: E402
import surfaces as SF  # noqa: E402
from views import layout_of  # noqa: E402

CREASE_DEG = 30.0     # dihedral angle of a hard edge of the model (the metric)
SLACK = 4             # px of the canvas: a model edge and an ink line this close agree
PLANE_DEG = 2.0       # planarity: a face this close to the plane of its patch is flat
SNAP_TOL = 0.01       # H: a region is flat when no vertex is farther than this from its plane
MAX_MOVE = 1.5        # tolerances: largest move of a vertex in the snap
MIN_FACES = 4         # a region of fewer faces fixes no plane
MAX_SPREAD = 25.0     # degrees: a region whose face normals differ more than this from its plane's is split
MERGE_DEG = 8.0       # first split: centroids of the normals closer than this are one group
INIT_K = 8            # first split of the normals
ROUNDS = 3            # plane refits of the snap
PULL = 1e-3           # weight of "stay where you were" against the planes of a vertex
FACING = AF.FACING    # a face is seen by a view above this normal . toward-camera
MARK_PX = 3.0         # a crease edge has both ends this close (canvas px) to the ink
MARK_COS = 0.42       # ... and runs along it: |cos| of the angle to the ink's gradient under this (25 degrees)
MARK_MIN_DEG = 8.0    # ... and bends at least this much
IOU_SLIP = 0.003      # no view may lose more IoU than this in the snap: the gate's own raster reads up to .004 other than D.measure
                      # (with .005 the battery lost .006-.009 in 3 views, PIPELINE 30.L12-9) and noise.py's floor is max(2 sigma, .005)
SPILL_SLIP = 0.003    # ... nor gain more spill
BARE_SLIP = 0.003     # ... nor more uncovered share
VIEWS = ("front", "left", "back")
SIX = D.SIX


# ---------------------------------------------------------------- mesh basics
def face_normals(pos, tri):
    """(unit normals, areas) of the faces; a zero-area face has a zero normal."""
    q = pos[tri]
    cross = np.cross(q[:, 1] - q[:, 0], q[:, 2] - q[:, 0])
    size = np.linalg.norm(cross, axis=1)
    return cross / np.maximum(size, 1e-30)[:, None], size / 2


def edge_table(tri):
    """(sorted vertex pairs of every edge, the two faces of the interior ones as (rows, f0, f1)): rows index the pairs."""
    pair = np.sort(np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]), axis=1)
    face = np.tile(np.arange(len(tri)), 3)
    uniq, inv, count = np.unique(pair, axis=0, return_inverse=True, return_counts=True)
    inv = inv.reshape(-1)
    order = np.argsort(inv, kind="stable")
    rows = np.where(count == 2)[0]
    first = np.searchsorted(inv[order], rows)
    return uniq, (rows, face[order[first]], face[order[first + 1]])


def dihedral(normal, f0, f1, area):
    """Degrees between the faces f0 / f1 of each edge; 0 when either face is a sliver (its normal is noise)."""
    ok = (area[f0] > D.TINY * np.median(area)) & (area[f1] > D.TINY * np.median(area))
    cos = np.clip(np.einsum("ed,ed->e", normal[f0], normal[f1]), -1, 1)
    return np.where(ok, np.degrees(np.arccos(cos)), 0.0)


# ---------------------------------------------------------------- metrics
def kmeans_normals(n, w, k, iters=12):
    """(labels, unit centroids) of the face normals `n` weighted by `w`: farthest-point start, no randomness."""
    real = np.where(w >= 0.2 * np.median(w))[0]
    pick = [real[np.argmax(w[real])]]
    far = 1 - n[real] @ n[pick[0]]
    for _ in range(k - 1):
        pick.append(real[np.argmax(far)])
        far = np.minimum(far, 1 - n[real] @ n[pick[-1]])
    c = n[pick].copy()
    for _ in range(iters):
        lab = np.argmax(n @ c.T, axis=1)
        for j in range(k):
            s = (n[lab == j] * w[lab == j, None]).sum(0)
            if np.linalg.norm(s) > 1e-12:
                c[j] = s / np.linalg.norm(s)
    return np.argmax(n @ c.T, axis=1), c


def planarity(pos, tri, deg=PLANE_DEG, min_faces=MIN_FACES):
    """Share of the area in flat patches: connected faces whose normals are all within `deg` of their seed's (largest face first),
    `min_faces` or more of them (MIN_FACES: a region's size). 1 for a cube, ~0 for a UV sphere or a smooth blob."""
    n, w = face_normals(pos, tri)
    _, (rows, f0, f1) = edge_table(tri)
    near = np.einsum("ed,ed->e", n[f0], n[f1]) >= math.cos(math.radians(deg))        # a cheap cut: the patch test below is exact
    nbr = [[] for _ in range(len(tri))]
    for a, b in zip(f0[near], f1[near]):
        nbr[a].append(b)
        nbr[b].append(a)
    cos, patch, flat = math.cos(math.radians(deg)), np.full(len(tri), -1), 0.0
    for seed in np.argsort(-w):
        if patch[seed] >= 0:
            continue
        patch[seed], members, todo = seed, [seed], [seed]
        while todo:
            for g in nbr[todo.pop()]:
                if patch[g] < 0 and n[g] @ n[seed] >= cos:
                    patch[g] = seed
                    members.append(g)
                    todo.append(g)
        flat += w[members].sum() if len(members) >= min_faces else 0.0
    return float(flat / w.sum())


def wire_entropy(pos, tri, bins=18):
    """(entropy 0..1 of the directions of the edges taken in the plane of one of their faces against the plane's `up`,
    edges per 1000 triangles)."""
    n, _ = face_normals(pos, tri)
    pair = np.sort(np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]), axis=1)
    face = np.tile(np.arange(len(tri)), 3)
    uniq, first = np.unique(pair, axis=0, return_index=True)
    f = face[first]
    d = pos[uniq[:, 1]] - pos[uniq[:, 0]]
    d /= np.maximum(np.linalg.norm(d, axis=1), 1e-30)[:, None]
    up = np.array([0.0, 0.0, 1.0])
    r = up - (n[f] @ up)[:, None] * n[f]
    flat = np.linalg.norm(r, axis=1) < 0.2                      # a floor: the x axis is the reference
    r[flat] = np.array([1.0, 0.0, 0.0]) - n[f][flat][:, [0]] * n[f][flat]
    e1 = r / np.maximum(np.linalg.norm(r, axis=1), 1e-30)[:, None]
    e2 = np.cross(n[f], e1)
    phi = np.mod(np.arctan2(np.einsum("ed,ed->e", d, e2), np.einsum("ed,ed->e", d, e1)), math.pi)
    hist = np.bincount(np.floor(phi / (math.pi / bins) + 0.5).astype(int) % bins, minlength=bins) / len(phi)
    p = hist[hist > 0]
    return float(-(p * np.log(p)).sum() / math.log(bins)), 1000 * len(uniq) / len(tri)


def project(pos, view):
    """Canvas coordinates (pixel centres at +0.5) of the welded positions in `view`."""
    uv = view.uv(pos)
    to_canvas, _ = D.frame(uv, view.mirror, view.frame_on)
    return to_canvas(uv)


def seen_edges(view, f0, f1, normal):
    """Boolean per interior edge: both faces look at the camera of `view`."""
    toward = np.cross(view.ru, view.rv)
    return (normal[f0] @ toward > FACING) & (normal[f1] @ toward > FACING)


def draw_edges(xy, pairs):
    """Boolean canvas with a 1 px line along each vertex pair."""
    img = Image.new("L", (S.CANVAS_W, S.CANVAS_H), 0)
    draw = ImageDraw.Draw(img)
    for a, b in pairs:
        draw.line([tuple(xy[a] - 0.5), tuple(xy[b] - 0.5)], fill=255, width=1)
    return np.asarray(img) > 0


def model_edges(pos, tri, view, deg=CREASE_DEG):
    """Boolean canvas of the hard edges of the model (dihedral >= deg, both faces seen) in `view`."""
    uniq, (rows, f0, f1) = edge_table(tri)
    normal, area = face_normals(pos, tri)
    keep = seen_edges(view, f0, f1, normal) & (dihedral(normal, f0, f1, area) >= deg)
    return draw_edges(project(pos, view), uniq[rows[keep]])


def chamfer_pr(model, ink, slack=SLACK):
    """(precision, recall): the share of the model's edge pixels within `slack` px of the ink, and of the ink within `slack` of
    the model's edges. (0, 0) when either canvas is empty."""
    if not (model.any() and ink.any()):
        return 0.0, 0.0
    near_ink = ndimage.distance_transform_edt(~ink) <= slack
    near_model = ndimage.distance_transform_edt(~model) <= slack
    return float(near_ink[model].mean()), float(near_model[ink].mean())


def metrics(pos, tri, views, ink):
    """{crease_chamfer: {view: [P, R]}, planarity, wire_entropy, edges_per_ktri} for the welded mesh, `views` (D.View list), `ink` {view: canvas}."""
    cc = {v.name: [round(x, 3) for x in chamfer_pr(model_edges(pos, tri, v), ink[v.name])] for v in views if v.name in ink}
    entropy, per_k = wire_entropy(pos, tri)
    return {"crease_chamfer": cc, "planarity": round(planarity(pos, tri), 3), "wire_entropy": round(entropy, 3),
            "edges_per_ktri": round(per_k, 1), "tris": int(len(tri))}


# ---------------------------------------------------------------- creases from the ink
def along_ink(xy_a, xy_b, ink):
    """Boolean per segment (canvas coordinates): both ends and the middle within MARK_PX of the ink, direction along it."""
    dist = ndimage.distance_transform_edt(~ink)
    gy, gx = np.gradient(ndimage.gaussian_filter(ink.astype(float), 2.0))
    mid = (xy_a + xy_b) / 2
    near = np.ones(len(mid), bool)
    for q in (xy_a, xy_b, mid):
        i = np.clip(np.floor(q).astype(int), 0, [S.CANVAS_W - 1, S.CANVAS_H - 1])
        near &= dist[i[:, 1], i[:, 0]] <= MARK_PX
    i = np.clip(np.floor(mid).astype(int), 0, [S.CANVAS_W - 1, S.CANVAS_H - 1])
    grad = np.stack([gx[i[:, 1], i[:, 0]], gy[i[:, 1], i[:, 0]]], 1)
    unit_g = grad / np.maximum(np.linalg.norm(grad, axis=1), 1e-12)[:, None]
    direction = (xy_b - xy_a) / np.maximum(np.linalg.norm(xy_b - xy_a, axis=1), 1e-12)[:, None]
    return near & (np.abs(np.einsum("ed,ed->e", unit_g, direction)) <= MARK_COS)


def mark_sharp(pos, tri, views, ink):
    """Boolean per edge of edge_table's pairs: the edges that run along the ink of the hard sheet in some view."""
    uniq, (rows, f0, f1) = edge_table(tri)
    normal, area = face_normals(pos, tri)
    bend = dihedral(normal, f0, f1, area) >= MARK_MIN_DEG
    out = np.zeros(len(uniq), bool)
    for view in (v for v in views if v.name in ink and ink[v.name].any()):
        xy = project(pos, view)
        hit = bend & seen_edges(view, f0, f1, normal) & along_ink(xy[uniq[rows, 0]], xy[uniq[rows, 1]], ink[view.name])
        out[rows[hit]] = True
    return out


# ---------------------------------------------------------------- planar regions
def merge_close(centre):
    """Group id per centroid: a centroid within MERGE_DEG of an earlier one joins its group."""
    close = centre @ centre.T >= math.cos(math.radians(MERGE_DEG))
    group = np.arange(len(centre))
    for j in range(len(centre)):
        earlier = np.where(close[j, :j])[0]
        group[j] = group[earlier[0]] if len(earlier) else j
    return group


def components(tri_count, f0, f1, label=None):
    """Component id per face of the graph f0-f1 (only the pairs with equal `label` when it is given)."""
    keep = np.ones(len(f0), bool) if label is None else label[f0] == label[f1]
    g = coo_matrix((np.ones(keep.sum()), (f0[keep], f1[keep])), shape=(tri_count,) * 2)
    return connected_components(g, directed=False)[1]


def fit_plane(pos, tri, faces, normal, area):
    """(point, unit normal) of the plane of `faces`: area-weighted centroid, the smallest axis of the vertices' spread,
    turned to the side of the mean face normal."""
    verts = np.unique(tri[faces])
    c = pos[tri[faces]].mean(1).T @ area[faces] / area[faces].sum()
    q = pos[verts] - c
    nrm = np.linalg.eigh(q.T @ q)[1][:, 0]
    mean = normal[faces].T @ area[faces]
    return c, nrm if nrm @ mean >= 0 else -nrm


def two_means(n, w):
    """Boolean split of the normals in two groups (the two farthest apart as seeds); None when they all agree."""
    a = np.argmax(w)
    b = np.argmin(n @ n[a])
    if n[a] @ n[b] > 1 - 1e-9:
        return None
    seeds = n[[a, b]].copy()
    for _ in range(8):
        side = (n @ seeds[1]) > (n @ seeds[0])
        for j, m in enumerate((~side, side)):
            s = (n[m] * w[m, None]).sum(0) if m.any() else seeds[j]
            seeds[j] = s / max(np.linalg.norm(s), 1e-12)
    return side if side.any() and not side.all() else None


def split_region(pos, tri, faces, normal, area):
    """Two face sets: the two-means of the normals, else the halves along the region's longest axis."""
    side = two_means(normal[faces], area[faces])
    if side is None:
        centre = pos[tri[faces]].mean(1)
        axis = np.linalg.eigh(np.cov(centre.T))[1][:, -1]
        proj = centre @ axis
        side = proj > np.median(proj)
    return faces[~side], faces[side]


def regions(pos, tri, sharp=None, tol=SNAP_TOL):
    """List of face-index arrays of the planar regions of MIN_FACES or more (a region is flat to `tol` in model units and its
    normals are within MAX_SPREAD of its plane's). The `sharp` edges (rows of edge_table's pairs) are never crossed."""
    normal, area = face_normals(pos, tri)
    uniq, (rows, f0, f1) = edge_table(tri)
    if sharp is not None and len(sharp):
        s = np.zeros(len(uniq), bool)
        s[sharp] = True
        free = ~s[rows]
        f0, f1 = f0[free], f1[free]
    lab0, centre = kmeans_normals(normal, area, min(INIT_K, len(tri)))
    lab0 = merge_close(centre)[lab0]
    comp = components(len(tri), f0, f1, lab0)
    todo = [np.where(comp == k)[0] for k in range(comp.max() + 1)]
    out, cos_spread = [], math.cos(math.radians(MAX_SPREAD))
    while todo:
        faces = todo.pop()
        if len(faces) < MIN_FACES:
            continue
        c, nrm = fit_plane(pos, tri, faces, normal, area)
        flat = np.abs((pos[np.unique(tri[faces])] - c) @ nrm).max() <= tol
        if flat and (normal[faces] @ nrm).min() >= cos_spread:
            out.append(faces)
            continue
        for part in split_region(pos, tri, faces, normal, area):
            if len(part) == 0 or len(part) == len(faces):
                continue
            inside = np.zeros(len(tri), bool)
            inside[part] = True
            keep = inside[f0] & inside[f1]
            sub = components(len(tri), f0[keep], f1[keep])
            todo += [part[sub[part] == k] for k in np.unique(sub[part])]
    return out


def solve_vertices(pos, tri, planes, reach, origin):
    """New positions: each vertex on the planes of the regions it touches (QEF with a PULL toward where it was), moved by at
    most MAX_MOVE * `reach` (the tolerance in model units) from `origin`. `planes`: [(faces, point, normal)]."""
    touching = {}
    for k, (faces, _, _) in enumerate(planes):
        for v in np.unique(tri[faces]):
            touching.setdefault(int(v), []).append(k)
    new = pos.copy()
    for v, ks in touching.items():
        n = np.array([planes[k][2] for k in ks])
        off = np.einsum("kd,kd->k", n, np.array([planes[k][1] for k in ks]))
        a = n.T @ n + PULL * np.eye(3)
        x = np.linalg.solve(a, n.T @ off + PULL * pos[v])
        step = x - origin[v]
        new[v] = origin[v] + step * min(1.0, MAX_MOVE * reach / max(np.linalg.norm(step), 1e-30))
    return new, len(touching)


def snap_regions(pos, tri, found, reach):
    """(positions, planes [(faces, point, normal)]) with the regions `found` (face-index arrays) snapped: ROUNDS times planes
    refitted to the vertices as they are and every vertex put on the planes of its regions."""
    cur, planes = pos, []
    for _ in range(ROUNDS):
        normal, area = face_normals(cur, tri)
        planes = [(faces, *fit_plane(cur, tri, faces, normal, area)) for faces in found]
        cur = solve_vertices(cur, tri, planes, reach, pos)[0]
    return cur, planes


def accepted(new, tri, guard, ref, floor, limit):
    """AF.accept's tests plus the spill: no turned face, slivers under `limit`, no view with IoU lost over IOU_SLIP, spill gained over
    SPILL_SLIP or uncovered share over BARE_SLIP."""
    if D.turned(ref, new, tri).any() or D.sliver_share(new, tri) > limit:
        return False
    got = D.measure(new, tri, guard)
    return all(got[v.name]["iou"] >= floor[v.name]["iou"] - IOU_SLIP and got[v.name]["spill"] <= floor[v.name]["spill"] + SPILL_SLIP
               and got[v.name]["uncovered"] <= floor[v.name]["uncovered"] + BARE_SLIP for v in guard)


def guarded(pos, tri, found, reach, ok):
    """(positions, regions snapped): `found` region by region, cheapest move first, each kept when the snap of everything kept so
    far still passes `ok`. The regions interact through the vertices they share, so every step tests the real set."""
    full = snap_regions(pos, tri, found, reach)[0]
    cost = [np.linalg.norm(full[np.unique(tri[f])] - pos[np.unique(tri[f])], axis=1).mean() for f in found]
    best, kept = pos, []
    for i in np.argsort(cost):
        cand = snap_regions(pos, tri, kept + [found[i]], reach)[0]
        if ok(cand):
            best, kept = cand, kept + [found[i]]
    return best, len(kept)


def snap(pos, tri, panels, ink, nor=None, creases=False, cams=None, tol=SNAP_TOL):
    """(new welded positions, report, guard views, sharp edges): the guarded snap of the planar regions. `panels`: the sheet's raw
    panels (the guard)."""
    guard = D.make_views(pos, tri, panels, (), cams=cams)
    sharp = np.where(mark_sharp(pos, tri, [v for v in guard if v.name in VIEWS], ink))[0] if creases else None
    height = float(np.ptp(pos[:, 2]))
    found = regions(pos, tri, sharp, tol * height)
    ref = D.reference(pos, tri, np.zeros_like(pos) if nor is None else nor)
    before = D.measure(pos, tri, guard)
    limit = D.sliver_share(pos, tri) + AF.SLIVER_PP
    cur, used = guarded(pos, tri, found, tol * height, lambda c: accepted(c, tri, guard, ref, before, limit))
    moved = np.linalg.norm(cur - pos, axis=1)
    report = {"regions": len(found), "regions_snapped": used, "region_faces": int(sum(len(f) for f in found)), "faces": int(len(tri)),
              "sharp_edges": 0 if sharp is None else int(len(sharp)), "before": before, "after": D.measure(cur, tri, guard),
              "moved": int((moved > 1e-9).sum()), "max_move_h": round(float(moved.max() / height), 4)}
    return cur, report, guard, sharp


# ---------------------------------------------------------------- GLB / pipeline
def look_report(glb, args):
    """metrics of `glb` against the run's hard sheet (needs args.sheet, args.hard, args.kind); None without a hard sheet."""
    hard = getattr(args, "hard", None)
    if not (hard and pathlib.Path(hard).exists()):
        return None
    pos, tri = D.welded_mesh(glb)
    layout = layout_of(args.kind)
    views = D.make_views(pos, tri, D.sheet_panels(args.sheet, SIX, layout), (), cams=D.run_cams(args))
    return metrics(pos, tri, [v for v in views if v.name in VIEWS], AF.hard_edges(hard, VIEWS, layout))


def run(glb, out, args, creases):
    """Snap `glb` into `out` (positions only; <out>.look.json has the report: guard views, regions, metrics before / after)."""
    layout = layout_of(args.kind)
    panels = D.sheet_panels(args.sheet, SIX, layout)
    ink = AF.hard_edges(args.hard, VIEWS, layout)
    cams = D.run_cams(args)

    def change(pos, tri, nor):
        before = metrics(pos, tri, [v for v in D.make_views(pos, tri, panels, (), cams=cams) if v.name in VIEWS], ink)
        new, rep, guard, _ = snap(pos, tri, panels, ink, nor, creases, cams)
        rep.update(look_before=before, look_after=metrics(new, tri, [v for v in guard if v.name in VIEWS], ink))
        return new, rep

    return D.transform(glb, out, change, suffix=".look.json")


def png_width(doc, data, base):
    """Width in texels of the GLB's first image (PNG header), 0 when it has none."""
    if not doc.get("images"):
        return 0
    view = doc["bufferViews"][doc["images"][0]["bufferView"]]
    start = base + view.get("byteOffset", 0)
    return int.from_bytes(data[start + 16:start + 20], "big")


def ink_faces(uv, tri_local, edge_of, width):
    """Rewrites in place the u of the triangles that have a marked edge: the edge's two vertices to the triangle's smallest u (the
    ink column of the cel cell), the third to its largest. Only the tone-cell faces of the compact atlas (u spans INK-free
    TONE_W texels) whose three vertices belong to no other triangle. Returns the number of faces inked."""
    used = np.bincount(tri_local.ravel(), minlength=len(uv))
    span = (uv[tri_local, 0].max(1) - uv[tri_local, 0].min(1)) * width
    tone = np.abs(span - (SF.TONE_W - 2 * SF.INK_EDGE_PX)) < 0.05
    done = 0
    for f in np.where((edge_of >= 0) & tone & (used[tri_local] == 1).all(1))[0]:
        corner = tri_local[f]
        lo, hi = uv[corner, 0].min(), uv[corner, 0].max()
        uv[corner, 0] = hi
        uv[corner[[edge_of[f], (edge_of[f] + 1) % 3]], 0] = lo
        done += 1
    return done


def bake_ink(glb, args):
    """Ink along the edges that run on the hard sheet's lines (mark_sharp), in the cel atlas of `glb` (in place): the texture
    of a face is addressed across its tone cell, whose first column is ink, so putting a marked edge at u = the cell's start
    draws the line. Returns {"marked", "inked"} (the faces whose UVs moved)."""
    data, doc, base = D.read(glb)
    if not all("TEXCOORD_0" in p["attributes"] for p in D.prims(doc)):         # the clay of stage 1 has no texture
        return {"marked": 0, "inked": 0}
    parts, tri_all, _, _, uniq, inv, tri = D.weld_mesh(data, doc, base)
    layout = layout_of(args.kind)
    views = D.make_views(uniq, tri, D.sheet_panels(args.sheet, SIX, layout), (), cams=D.run_cams(args))
    pairs, _ = edge_table(tri)
    marked = mark_sharp(uniq, tri, [v for v in views if v.name in VIEWS], AF.hard_edges(args.hard, VIEWS, layout))
    width, key = png_width(doc, data, base), {tuple(e): i for i, e in enumerate(pairs[marked])}
    inked, start = 0, 0
    for p, (pos, _, idx) in zip(D.prims(doc), parts):
        acc = doc["accessors"][p["attributes"]["TEXCOORD_0"]]
        view = doc["bufferViews"][acc["bufferView"]]
        uv = np.frombuffer(data, np.float32, acc["count"] * 2, base + view.get("byteOffset", 0) + acc.get("byteOffset", 0)).reshape(-1, 2)
        w = inv[idx.astype(np.int64) + start]
        edge_of = np.full(len(idx), -1)
        for k in range(3):
            pair = np.sort(w[:, [k, (k + 1) % 3]], axis=1)
            edge_of[[tuple(q) in key for q in pair]] = k
        inked += ink_faces(uv, idx.astype(np.int64), edge_of, width)
        start += len(pos)
    pathlib.Path(glb).write_bytes(bytes(data))
    return {"marked": int(marked.sum()), "inked": inked}


def apply(glb, args):
    """spec_pipeline hook, after optimize_verts.apply: with args.look_snap == "on" snap `glb` in place (keeping the unsnapped one as
    <stem>-prelook.glb), with args.look_ink == "on" draw the ink of the marked edges into its atlas; either way <stem>.look.json
    holds the look metrics (needs the hard sheet and a unioned body). Report or None."""
    hard = getattr(args, "hard", None)
    if not (hard and pathlib.Path(hard).exists() and getattr(args, "union_body", False)):
        return None
    glb = pathlib.Path(glb)
    if getattr(args, "look_snap", "off") == "on":
        pre = glb.with_name(f"{glb.stem}-prelook.glb")
        pre.write_bytes(glb.read_bytes())
        report = run(pre, glb, args, getattr(args, "look_creases", "off") == "on")
    else:
        now = look_report(glb, args)
        report = {"look_before": now, "look_after": now}
    if getattr(args, "look_ink", "off") == "on":
        report["ink"] = bake_ink(glb, args)
    glb.with_suffix(".look.json").write_text(json.dumps(report, indent=2))
    return report


def line(report):
    """One log line of an apply() report: planarity / wire entropy / crease P-R, before -> after."""
    b, a = report["look_before"], report["look_after"]
    cc = " ".join(f"{v} {p:.2f}/{r:.2f}" for v, (p, r) in a["crease_chamfer"].items())
    snapped = f", snap {report['regions_snapped']}/{report['regions']} regions" if "regions" in report else ""
    ink = f", ink {report['ink']['inked']} faces" if "ink" in report else ""
    return (f"look: planarity {b['planarity']} -> {a['planarity']}, wire entropy {b['wire_entropy']} -> {a['wire_entropy']}, "
            f"{a['edges_per_ktri']} edges/ktri, crease P/R {cc}{snapped}{ink}")


def row(glb):
    """review.md row of the look metrics written beside `glb` (apply), "" when there are none."""
    path = pathlib.Path(glb).with_suffix(".look.json") if glb else None
    return f"| look | {line(json.loads(path.read_text()))[6:]} |\n" if path and path.exists() else ""


def cli_args(run_dir, unit, kind="mass"):
    """The slice of spec_pipeline's args this module reads, for a run dir of `unit`."""
    refs = pathlib.Path(__file__).resolve().parents[2] / "artifacts/model-sheets/refs" / unit
    return argparse.Namespace(out=pathlib.Path(run_dir), sheet=refs / "sheet.jpg", hard=refs / "sheet-hard.jpg", kind=kind,
                              tilts="", union_body=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("metrics", "snap"))
    ap.add_argument("path")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--id", required=True)
    ap.add_argument("--glb", default="clay.glb")
    ap.add_argument("--creases", action="store_true")
    a = ap.parse_args()
    if a.cmd == "metrics":
        args = cli_args(a.path, a.id)
        print(json.dumps(look_report(pathlib.Path(a.path) / a.glb, args), indent=2))
        return
    args = cli_args(pathlib.Path(a.path).parent, a.id)
    r = run(a.path, a.out, args, a.creases)
    print(json.dumps({k: r[k] for k in ("regions", "region_faces", "faces", "sharp_edges", "damp", "moved", "max_move_h",
                                        "look_before", "look_after")}, indent=2))


if __name__ == "__main__":
    main()
