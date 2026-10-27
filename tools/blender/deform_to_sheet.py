#!/usr/bin/env python3
"""Deform a GLB's vertices onto the approved sheet's outlines (Sketch2Mesh, PIPELINE 24.L6-5).

    python3.14 tools/blender/deform_to_sheet.py <in.glb> <sheet.jpg> <out.glb>
        [--views front,left,back] [--iters 4] [--band 0.4-0.7]

Per view (Sketch2Mesh §3.3, Fig. 2c): the model's external contour = the vertices that project onto the
outer boundary of its rendered mask; each goes toward the nearest point of the sheet panel's outline, at
most STEP * H per step, in the view plane. The rest of the mesh follows through a uniform-Laplacian
smoothing solved with scipy.sparse. Eq. 6 (partial regularisation): the pull weight falls to zero away
from the height bands that carry red (sheet bare) or green (model outside the sheet), `--band lo-hi`
(fractions of H) forces those bands instead. A step is refused when it adds slivers or flips faces, and
dropped when the mean IoU of the views does not grow. Only POSITION and NORMAL bytes of the GLB change:
skin weights, UVs, materials and clips stay as they are. Top/bottom (tilted cameras) are not deformed.

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
from scipy.sparse.linalg import spsolve

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mesh_lint as ML  # noqa: E402
import silhouette as S  # noqa: E402
from views import TILTS, layout_of  # noqa: E402

STEP = 0.05           # largest move of a vertex per step, fractions of the model height
CONTOUR_PX = 1.5      # a vertex this close (canvas px) to the mask's outer boundary is on the contour
DAMP = (1.0, 0.5, 0.25)  # a refused step is tried again at these shares of its length
REACH = 0.10         # a contour vertex farther than this (H) from the sheet's outline is not pulled: that is another part
PULL = 10.0           # weight of a contour vertex's target against the smoothness term
ANCHOR = 5.0          # weight of "stay where you are" where the band weight is 0
BAD_ON, BAD_FULL = 0.003, 0.015   # band share of the sheet/model that is red+green: weight 0 below, 1 above
SLIVER_MAX = 0.05     # share of triangles under mesh_lint.SLIVER_DEG a step may leave, or the share before + SLIVER_GROW
SLIVER_GROW = 0.05   # the union bodies of L6-4 start at 19-28 % slivers: an absolute 5 % cap would refuse every step
UNTANGLE = 8          # rounds of pulling the vertices of turned faces back toward where they were
SLIVER_AREA = 0.30    # unflip: a turned face under this share of the median area has its winding swapped
TINY = 0.02           # a face under this share of the median area is a sliver whose orientation does not count
SOLE = 0.02           # vertices this close to the ground (H) keep their height: the pivot stays put
SS = 2                # supersampling of the PIL raster
GUARD = 0.01          # no view may end more than this under its IoU at the start


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

    def __init__(self, name, ru, rv, mirror, concept, active):
        self.name, self.ru, self.rv, self.mirror, self.concept, self.active = name, ru, rv, mirror, concept, active

    def uv(self, pos):
        return np.stack([pos @ self.ru, pos @ self.rv], 1)


def frame(uv, mirror=1):
    """Canvas map of the points' bbox, the way silhouette.normalize fits a mask: (to_canvas, scale)."""
    uv = uv * np.array([mirror, 1.0])
    lo, hi = uv.min(0), uv.max(0)
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


def pull(concept, model_mask, xy, nearest=None):
    """Canvas displacement of each vertex toward the sheet's outline, 0 off the model's contour. `nearest` =
    (iy, ix) of the outline pixel nearest to every pixel, when the caller keeps it (it only depends on `concept`)."""
    ch, cw = model_mask.shape
    on = boundary(model_mask)
    px = np.clip(np.floor(xy).astype(int), 0, [cw - 1, ch - 1])
    near = ndimage.distance_transform_edt(~on)[px[:, 1], px[:, 0]] <= CONTOUR_PX
    iy, ix = ndimage.distance_transform_edt(~boundary(concept), return_indices=True)[1] if nearest is None else nearest
    goal = np.stack([ix[px[:, 1], px[:, 0]], iy[px[:, 1], px[:, 0]]], 1) + 0.5
    move = goal - xy
    near &= np.linalg.norm(move, axis=1) <= REACH * S.CANVAS_H
    return np.where(near[:, None], move, 0.0), near


def view_state(pos, tri, view):
    """(canvas coords, model mask, scale) of the welded Z-up positions in one view."""
    uv = view.uv(pos)
    to_canvas, s = frame(uv, view.mirror)
    xy = to_canvas(uv)
    return xy, raster(xy, tri), s


def clamp(d, limit):
    return d * np.minimum(1.0, limit / np.maximum(np.linalg.norm(d, axis=1), 1e-12))[:, None]


def step_view(pos, tri, lap, view, band, height, ground):
    """The welded positions after one deformation step in `view`."""
    xy, mask, s = view_state(pos, tri, view)
    wb = band_weights(view.concept, mask, band)
    if view.name in S_TILTED:         # no height axis: the whole outline is pulled
        wb = np.ones_like(wb)
    mid = (np.arange(S.BANDS) + 0.5) / S.BANDS
    w = np.interp((pos[:, 2] - pos[:, 2].min()) / height, mid, wb)
    move, near = pull(view.concept, mask, xy)
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
    return out


def mean_iou(report, views, active=True):
    return float(np.mean([report[v.name]["iou"] for v in views if v.active == active] or [0.0]))


def accept(old, new, tri, views, ref, floor, limit):
    """True when the step keeps slivers and normals sane, the pulling views' mean IoU does not drop and no
    view (pulling or only watched, a top/bottom) ends more than GUARD under `floor` (its IoU at the start)."""
    if turned(ref, new, tri).any() or sliver_share(new, tri) > limit:
        return False
    a, b = measure(old, tri, views), measure(new, tri, views)
    if any(b[v.name]["iou"] < floor[v.name] - GUARD for v in views):
        return False
    return mean_iou(b, views) >= mean_iou(a, views) - 1e-4


FRONT_AXES = {"front": ((1, 0, 0), (0, 0, 1)), "left": ((0, -1, 0), (0, 0, 1)), "back": ((-1, 0, 0), (0, 0, 1))}
S_TILTED = ("top", "bottom")


def tilted_axes(name, tilt):
    """Image axes of views.camera(name, tilt): x to the right, up = (0, cos, sin) of the camera's x rotation."""
    theta = math.radians(tilt if name == "top" else 180 - tilt)
    return np.array([1.0, 0, 0]), np.array([0.0, math.cos(theta), math.sin(theta)])


def candidates(name, panel):
    """(ru, rv, concept) of every way the sheet's top/bottom could be drawn: tilt sweep x panel turned or not."""
    for turned in (False, True):
        concept = S.normalize(np.rot90(panel, 2) if turned else panel)
        for tilt in TILTS:
            yield (*tilted_axes(name, tilt), concept)


def make_views(pos, tri, panels, pulling):
    """Views of the sheet: the pulling ones (`pulling` names) and the guards (the other top/bottom). The mirror
    of each (and tilt / turn of top/bottom) is the one whose raster matches the panel best, like silhouette.py."""
    views = []
    for name, panel in panels.items():
        options = [(*np.array(FRONT_AXES[name], float), S.normalize(panel))] if name in FRONT_AXES \
            else list(candidates(name, panel))
        score = lambda o, m: S.iou(o[2], view_state(pos, tri, View(name, o[0], o[1], m, o[2], True))[1])  # noqa: E731
        best = max(((o, m) for o in options for m in (1, -1)), key=lambda om: score(*om))
        (ru, rv, concept), mirror = best
        views.append(View(name, ru, rv, mirror, concept, name in pulling))
    return views


def deform(pos, tri, panels, pulling, iters=4, band=None, nor=None):
    """(new welded Z-up positions, report). Rounds of one step per pulling view, each refused when it makes things
    worse. `nor`: the welded Z-up vertex normals, the facing of the zero-area faces (None: their own)."""
    views = make_views(pos, tri, panels, pulling)
    ref = reference(pos, tri, np.zeros_like(pos) if nor is None else nor)
    height = float(np.ptp(pos[:, 2]))
    ground = pos[:, 2] < pos[:, 2].min() + SOLE * height
    lap = laplacian(tri, len(pos))
    slivers = sliver_share(pos, tri)
    limit = max(SLIVER_MAX, slivers + SLIVER_GROW)
    before = measure(pos, tri, views)
    floor = {k: r["iou"] for k, r in before.items()}
    report = {"before": before, "slivers_before": round(slivers, 4), "steps": 0, "refused": 0}
    cur = pos
    for _ in range(iters):
        for view in [v for v in views if v.active]:
            full = untangle(ref, cur, step_view(cur, tri, lap, view, band, height, ground), tri)
            tries = [cur + k * (full - cur) for k in DAMP]
            best = next((t for t in tries if accept(cur, t, tri, views, ref, floor, limit)), None)
            report["refused"] += best is None
            if best is not None:
                cur, report["steps"] = best, report["steps"] + 1
    report.update(after=measure(cur, tri, views), slivers_after=round(sliver_share(cur, tri), 4),
                  turned=int(turned(ref, cur, tri).sum()), mirrors={v.name: v.mirror for v in views})
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
    """Raw panels of the sheet: the pulling `views` and, as guards, the top/bottom that are not among them."""
    panels = S.concept_panels(pathlib.Path(sheet), layout=layout)
    return {v: p for v, p in panels.items() if v in views or v in S_TILTED}


def rewrite(glb, out, change, suffix=".deform.json"):
    """Write `out` = `glb` with the welded Z-up positions replaced by change(uniq, tri, normals, file) -> (new uniq,
    report), `file` = (welded index of each file vertex, the file's triangles); the report goes beside it as
    <out><suffix>. Shared with optimize_verts.py (PIPELINE 24.L6-7)."""
    data, doc, base = read(glb)
    parts, tri_all = geometry(data, doc, base)
    old = np.vstack([p for p, _, _ in parts]).astype(np.float64)
    old_nor = np.vstack([n for _, n, _ in parts]).astype(np.float64)
    zpos = to_z_up(old)
    uniq, inv = weld(zpos)
    tri = inv[tri_all]
    tri = tri[(tri[:, 0] != tri[:, 1]) & (tri[:, 1] != tri[:, 2]) & (tri[:, 0] != tri[:, 2])]
    new_uniq, report = change(uniq, tri, welded_normals(to_z_up(old_nor), inv, len(uniq)), (inv, tri_all))
    new = from_z_up(new_uniq[inv]).astype(np.float32).astype(np.float64)     # what the file will hold
    nor = new_normals(new, old_nor, tri_all)
    write(data, doc, base, parts, new, nor, unflip(new, nor, tri_all))
    pathlib.Path(out).write_bytes(repack(data, doc, base))
    pathlib.Path(out).with_suffix(suffix).write_text(json.dumps(report, indent=2))
    return report


def run(glb, sheet, out, views=("front", "left", "back"), iters=4, band=None, layout="unit"):
    """Deform `glb` onto the sheet and write `out`; returns the report (before / after per view, slivers)."""
    panels = sheet_panels(sheet, views, layout)
    return rewrite(glb, out, lambda uniq, tri, nor, _file: deform(uniq, tri, panels, views, iters, band, nor))


def apply(glb, args):
    """spec_pipeline hook: deform `glb` in place when the run wants it (args.deform on a unioned body),
    keeping the original beside it as <stem>-raw.glb. Returns the report or None."""
    if not (getattr(args, "deform", False) and getattr(args, "union_body", False)):
        return None
    glb = pathlib.Path(glb)
    raw = glb.with_name(f"{glb.stem}-raw.glb")
    raw.write_bytes(glb.read_bytes())
    return run(raw, args.sheet, glb, layout=layout_of(args.kind))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("glb")
    ap.add_argument("sheet")
    ap.add_argument("out")
    ap.add_argument("--views", default="front,left,back")
    ap.add_argument("--iters", type=int, default=4)
    ap.add_argument("--band", type=parse_band, default=None, help="deform only this height range, e.g. 0.4-0.7")
    a = ap.parse_args()
    r = run(a.glb, a.sheet, a.out, tuple(a.views.split(",")), a.iters, a.band)
    for v in r["after"]:
        b, f = r["before"][v], r["after"][v]
        print(f"{v:6} IoU {b['iou']:.3f} -> {f['iou']:.3f}  red {b['uncovered']:.3f} -> {f['uncovered']:.3f}  "
              f"green {b['spill']:.3f} -> {f['spill']:.3f}")
    print(f"steps {r['steps']} refused {r['refused']} slivers {r['slivers_before']} -> {r['slivers_after']} "
          f"turned {r['turned']}")


if __name__ == "__main__":
    main()
