#!/usr/bin/env python3
"""Pull the sharp edges of a deformed GLB onto the inner edges of the hard sheet (Chen 2023 §4, PIPELINE 24.L6-12).

    python3.14 tools/blender/align_features.py <in.glb> <sheet.jpg> <sheet-hard.jpg> <out.glb> [--iters 3]

Runs after deform_to_sheet.py (the contour is already on the drawing). Live edges = mesh edges whose two faces
differ by more than FEATURE_DEG. Per view (front / left / back) the edges whose two faces both look at the camera
(normal test) have their vertices projected on the canvas and moved, in the view plane, toward the nearest pixel of
`silhouette.edges(hard sheet)` (the same canvas `fit_spec.edge_term` uses), at most LIMIT * H, only when that pixel is
nearer than REACH * H. The pull weight is small (A) against a stay-put term on every other vertex, so the interior
follows through the uniform Laplacian of deform_to_sheet. A step is refused (damped 1, 1/2, 1/4) when it turns a face,
adds more than SLIVER_PP of slivers, drops a view's IoU against the approved sheet by more than IOU_SLIP,
or does not lower edge_cost (mean distance of the live-edge vertices to the drawn edges, clipped at REACH).
No Blender: same GLB-in-place machinery as deform_to_sheet.py.
"""
import argparse
import json
import math
import pathlib
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import deform_to_sheet as D  # noqa: E402
import silhouette as S  # noqa: E402
from views import layout_of  # noqa: E402

FEATURE_DEG = 35.0   # dihedral angle above which an edge is live
FACING = 0.2         # a face is seen by a view when its normal . toward-camera is above this
REACH = 0.06         # a live-edge vertex farther than this (H) from a drawn edge is not pulled
LIMIT = 0.02         # largest move of a vertex per step (H)
WEIGHT = 3.0         # pull weight of a live-edge vertex against the stay-put term
STAY = 1.0           # weight of "stay where you are" on every other vertex
SLIVER_PP = 0.02     # slivers may grow by this share of the triangles
IOU_SLIP = 0.005     # no view (front/left/back/top/bottom) may end this far under its IoU at the start: half of the
                     # deformation's guard, the edges are a finishing pass
VIEWS = ("front", "left", "back")


def live_edges(pos, tri):
    """(vertex pairs of the live edges, their two face ids, unit face normals, valid faces). Edges with a
    near-zero-area face are skipped: their normal is noise."""
    q = pos[tri]
    cross = np.cross(q[:, 1] - q[:, 0], q[:, 2] - q[:, 0])
    area = np.linalg.norm(cross, axis=1)
    ok = area > D.TINY * np.median(area)
    normal = cross / np.maximum(area, 1e-30)[:, None]
    pair = np.sort(np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]), axis=1)
    face = np.tile(np.arange(len(tri)), 3)
    uniq, inv, count = np.unique(pair, axis=0, return_inverse=True, return_counts=True)
    inv = inv.reshape(-1)
    order = np.argsort(inv, kind="stable")
    shared = np.where(count == 2)[0]
    first = np.searchsorted(inv[order], shared)
    f0, f1 = face[order[first]], face[order[first + 1]]
    live = ok[f0] & ok[f1] & (np.einsum("ed,ed->e", normal[f0], normal[f1]) < math.cos(math.radians(FEATURE_DEG)))
    return uniq[shared][live], f0[live], f1[live], normal


def seen_vertices(edge, f0, f1, normal, view, count):
    """Boolean per vertex: ends of a live edge whose two faces look at the camera of `view`."""
    toward = np.cross(view.ru, view.rv)
    seen = (normal[f0] @ toward > FACING) & (normal[f1] @ toward > FACING)
    out = np.zeros(count, bool)
    out[edge[seen].ravel()] = True
    return out


def hard_edges(hard, views, layout):
    """{view name: bool canvas of the hard sheet's inner edges, as fit_spec.hard_canvas_edges makes it}."""
    panels = S.concept_panels(pathlib.Path(hard), layout=layout)
    return {n: S.fit_canvas(S.edges(hard, panels[n]), panels[n]) for n in views if n in panels}


class Target:
    """One edge view: the camera (View), the drawn-edge canvas, the vertices to pull, the distance field."""

    def __init__(self, view, edge, feat):
        self.view, self.feat = view, feat
        dist, idx = ndimage.distance_transform_edt(~edge, return_indices=True) if edge.any() else (None, None)
        self.dist, self.idx = dist, idx

    def usable(self):
        return self.dist is not None and self.feat.any()

    def lookup(self, xy):
        """(distance in canvas px, goal canvas point) of the nearest drawn edge per vertex."""
        h, w = self.dist.shape
        px = np.clip(np.floor(xy).astype(int), 0, [w - 1, h - 1])
        goal = np.stack([self.idx[1][px[:, 1], px[:, 0]], self.idx[0][px[:, 1], px[:, 0]]], 1) + 0.5
        return self.dist[px[:, 1], px[:, 0]], goal


def edge_cost(pos, tri, targets):
    """Mean over the views of the live-edge vertices' distance to a drawn edge (canvas heights, clipped at REACH):
    what the pull lowers."""
    costs = []
    for t in targets:
        dist, _ = t.lookup(D.view_state(pos, tri, t.view)[0][t.feat])
        costs.append(np.minimum(dist, REACH * S.CANVAS_H).mean() / S.CANVAS_H)
    return float(np.mean(costs)) if costs else 0.0


def flipped(pos, tri):
    """Faces against the sum of their vertices' normals: the count mesh_lint's `flipped == 0` gate reads."""
    q = pos[tri]
    cross = np.cross(q[:, 1] - q[:, 0], q[:, 2] - q[:, 0])
    live = np.linalg.norm(cross, axis=1) / 2 > 1e-8 * np.ptp(pos[:, 2]) ** 2
    nor = D.new_normals(pos, np.zeros_like(pos), tri)
    return int((np.einsum("fd,fd->f", cross, nor[tri].sum(1))[live] < 0).sum())


def accept(new, tri, guard, ref, floor, limit):
    """True when `new` turns no face, flips none more than `floor` had, keeps slivers under `limit` and every guard
    view's IoU within IOU_SLIP of `floor` (the start: per-view IoU and the flipped count under "flipped")."""
    if D.turned(ref, new, tri).any() or D.sliver_share(new, tri) > limit or flipped(new, tri) > floor["flipped"]:
        return False
    got = D.measure(new, tri, guard)
    return all(got[v.name]["iou"] >= floor[v.name] - IOU_SLIP for v in guard)


def step_view(pos, tri, lap, t, height, ground):
    """The welded positions after one pull of the live edges seen by `t` toward the drawn edges."""
    xy, _, s = D.view_state(pos, tri, t.view)
    dist, goal = t.lookup(xy)
    sel = t.feat & (dist / s <= REACH * height)
    move = goal - xy
    d = D.clamp(np.stack([move[:, 0] / s * t.view.mirror, -move[:, 1] / s], 1) * sel[:, None], LIMIT * height)
    d = D.clamp(D.solve(lap, d, WEIGHT * sel, STAY * ~sel + 1e-3), LIMIT * height)
    world = d[:, :1] * t.view.ru + d[:, 1:] * t.view.rv
    world[ground, 2] = 0.0
    return pos + world


def align(pos, tri, panels, hard_canvas, nor=None, iters=3):
    """(new welded Z-up positions, report). `panels`: the approved sheet's raw panels (the IoU guard), `hard_canvas`:
    {view: drawn-edge canvas}."""
    guard = D.make_views(pos, tri, panels, VIEWS)
    edge_views = [v for v in guard if v.name in hard_canvas]
    edge, f0, f1, normal = live_edges(pos, tri)
    targets = [Target(v, hard_canvas[v.name], seen_vertices(edge, f0, f1, normal, v, len(pos))) for v in edge_views]
    targets = [t for t in targets if t.usable()]
    ref = D.reference(pos, tri, np.zeros_like(pos) if nor is None else nor)
    height = float(np.ptp(pos[:, 2]))
    ground = pos[:, 2] < pos[:, 2].min() + D.SOLE * height
    lap = D.laplacian(tri, len(pos))
    slivers = D.sliver_share(pos, tri)
    before = D.measure(pos, tri, guard)
    floor = {k: r["iou"] for k, r in before.items()} | {"flipped": flipped(pos, tri)}
    cost = {t.view.name: edge_cost(pos, tri, [t]) for t in targets}
    report = {"live_edges": int(len(edge)), "feature_vertices": {t.view.name: int(t.feat.sum()) for t in targets},
              "cost_before": {k: round(v, 4) for k, v in cost.items()}, "before": before,
              "slivers_before": round(slivers, 4), "steps": 0, "refused": 0}
    cur, now = pos, edge_cost(pos, tri, targets)
    for _ in range(iters):
        for t in targets:
            full = D.untangle(ref, cur, step_view(cur, tri, lap, t, height, ground), tri)
            best = next((c for c in (cur + k * (full - cur) for k in D.DAMP)
                         if accept(c, tri, guard, ref, floor, slivers + SLIVER_PP)
                         and edge_cost(c, tri, targets) < now - 1e-6), None)
            report["refused"] += best is None
            if best is not None:
                cur, now = best, edge_cost(best, tri, targets)
                report["steps"] += 1
    report.update(after=D.measure(cur, tri, guard), slivers_after=round(D.sliver_share(cur, tri), 4),
                  cost_after={t.view.name: round(edge_cost(cur, tri, [t]), 4) for t in targets},
                  turned=int(D.turned(ref, cur, tri).sum()), flipped=[floor["flipped"], flipped(cur, tri)])
    return cur, report


def run(glb, sheet, hard, out, layout="unit", iters=3):
    """Align `glb` to the hard sheet's inner edges and write `out` (+ <out>.align.json); returns the report."""
    panels = D.sheet_panels(sheet, VIEWS, layout)
    canvas = hard_edges(hard, VIEWS, layout)
    report = D.transform(glb, out, lambda pos, tri, nor: align(pos, tri, panels, canvas, nor, iters))
    pathlib.Path(out).with_suffix(".align.json").write_text(json.dumps(report, indent=2))
    return report


def apply(glb, args):
    """spec_pipeline hook, after deform_to_sheet.apply: align `glb` in place when the run wants it (args.align on a
    unioned body with a hard sheet), keeping the unaligned one beside it as <stem>-prealign.glb. Report or None."""
    hard = getattr(args, "hard", None)
    if not (getattr(args, "align", False) and getattr(args, "union_body", False) and hard and pathlib.Path(hard).exists()):
        return None
    glb = pathlib.Path(glb)
    pre = glb.with_name(f"{glb.stem}-prealign.glb")
    pre.write_bytes(glb.read_bytes())
    return run(pre, args.sheet, hard, glb, layout=layout_of(args.kind))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("glb")
    ap.add_argument("sheet")
    ap.add_argument("hard")
    ap.add_argument("out")
    ap.add_argument("--iters", type=int, default=3)
    a = ap.parse_args()
    r = run(a.glb, a.sheet, a.hard, a.out, iters=a.iters)
    for v, c in r["cost_before"].items():
        print(f"{v:6} edge cost {c:.4f} -> {r['cost_after'][v]:.4f}  IoU {r['before'][v]['iou']:.3f} -> {r['after'][v]['iou']:.3f}")
    print(f"live edges {r['live_edges']} steps {r['steps']} refused {r['refused']} "
          f"slivers {r['slivers_before']} -> {r['slivers_after']} turned {r['turned']}")


if __name__ == "__main__":
    main()
