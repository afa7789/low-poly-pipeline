#!/usr/bin/env python3
"""Soft silhouette raster in torch (PIPELINE 26.L8-1): the differentiable twin of the hard raster of
deform_to_sheet.raster / optimize_verts.Ctx, for the gradient only. Gates and verdicts stay on silhouette.py.

    SoftRas (Liu 2019) Eq. 1:  D_j(p) = F(delta_j(p) * d_j(p)^2 / tau^2)      delta = +1 inside the triangle, -1 outside
    SoftRas Eq. 4:             A(p)   = 1 - prod_j (1 - D_j(p))                  ("prob")
    GenDR (Wang 2022):         F logistic, uniform (a linear ramp) or gamma_inv (reversed Gamma p=.5), aggregation Yager(2): min(1, sqrt(sum D_j^2))

`tau` is in canvas pixels (the width of the edge band), d the distance in pixels of the pixel centre to the triangle.
PyTorch3D (Ravi 2020) pattern: every triangle is evaluated only in its bbox grown by 3 tau; the windows are laid out
ragged (one row per pixel of every window, no padding) so a few big triangles do not cost the many small ones. `project` is the same map as
deform_to_sheet.View.uv + frame (bbox of the projection fitted to the silhouette.CANVAS), so tau -> 0 gives the hard
raster of optimize_verts.Ctx for the same mesh and view. Everything is differentiable down to the 3D positions.

    python3.14 tools/blender/soft_sil.py <run dir with clay.glb + silhouette.json> <sheet.jpg> [--tau 0.5]
"""
import argparse
import json
import math
import pathlib
import sys

import numpy as np
import torch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import deform_to_sheet as D  # noqa: E402
import silhouette as S  # noqa: E402

REACH = 3.0               # window margin, in tau (logistic: D(3 tau) = 1.2e-4; gamma_inv: erfc(3) = 2e-5)
CHUNK = 1 << 21           # window pixels per vectorised block
EPS = 1e-9
SHAPE = (S.CANVAS_H, S.CANVAS_W)


def project(pos, view, detach=False):
    """Canvas xy [N,2] of the Z-up positions `pos` (torch [N,3]) in `view` (a deform_to_sheet.View): the same
    uv, mirror and bbox fit as View.uv + deform_to_sheet.frame. `detach`: the fit counts as a constant."""
    ru, rv = (torch.as_tensor(a, dtype=pos.dtype, device=pos.device) for a in (view.ru, view.rv))
    uv = torch.stack([pos @ ru, pos @ rv], 1) * torch.tensor([view.mirror, 1.0], dtype=pos.dtype, device=pos.device)
    lo, hi = uv.min(0).values, uv.max(0).values
    if detach:
        lo, hi = lo.detach(), hi.detach()
    w, h = hi - lo
    s = S.CANVAS_H / h
    s = torch.where(w * s > S.CANVAS_W, S.CANVAS_W / w, s)
    x0, y0 = (S.CANVAS_W - w * s) / 2, (S.CANVAS_H - h * s) / 2
    return torch.stack([(uv[:, 0] - lo[0]) * s + x0, (hi[1] - uv[:, 1]) * s + y0], 1)


def signed_d2(px, py, tri_xy):
    """(squared distance [N], inside [N]) of the points (px, py) [N] to the triangles tri_xy [N,3,2] (one per point).
    The three edges are one [N,3] block, x / y separate tensors: wide elementwise ops instead of [..., 2] stacks."""
    ab = tri_xy.roll(-1, 1) - tri_xy
    ax, ay, abx, aby = tri_xy[..., 0], tri_xy[..., 1], ab[..., 0], ab[..., 1]
    apx, apy = px[:, None] - ax, py[:, None] - ay
    t = ((apx * abx + apy * aby) / ((abx * abx + aby * aby) + EPS)).clamp(0, 1)
    d2 = ((apx - t * abx) ** 2 + (apy - t * aby) ** 2).amin(1)
    area = abx[:, 0] * aby[:, 1] - aby[:, 0] * abx[:, 1]                    # cross(b - a, c - b)
    sgn = torch.where(area >= 0, 1.0, -1.0)[:, None]
    inside = ((sgn * (abx * apy - aby * apx)).amin(1) >= 0) & (area.abs() > EPS)
    return d2, inside


def squash(x, dist):
    """F of the signed, scaled distance: logistic sigmoid, or the uniform ramp (linear on [-2, 2], then 0 / 1)."""
    if dist == "logistic":
        return torch.sigmoid(x)
    if dist == "uniform":
        return (0.5 + x / 4).clamp(0, 1)
    if dist == "gamma_inv":
        return gamma_inv(x)
    raise ValueError(f"dist {dist!r}: logistic | uniform | gamma_inv")


def gamma_inv(x):
    """GenDR's reversed Gamma(p = 0.5), one-sided: all the mass is outside the triangle (faces come out larger, no
    gaps between neighbours). 1 inside; outside 1 - P(0.5, d^2 / tau^2) = erfc(d / tau), with x = -d^2 / tau^2."""
    return torch.where(x >= 0, 1.0, torch.erfc((-x).clamp(min=EPS).sqrt()))


def windows(xy, size, margin):
    """(origin [T,2] int, extent [T,2] int) of every triangle's bbox + margin, clipped to the canvas (W, H)."""
    lo = torch.floor(xy.detach().amin(1) - margin).long().clamp(min=0)
    hi = torch.ceil(xy.detach().amax(1) + margin).long()
    hi = torch.minimum(hi, torch.tensor(size, device=xy.device))
    return lo, (hi - lo).clamp(min=0)


def triangle_terms(xy_tris, size, tau, dist):
    """(flat canvas index, D) of every pixel of every triangle's window, ragged: no padding, one row per pixel."""
    margin = math.sqrt(2.0) * tau if dist == "uniform" else REACH * tau
    lo, ext = windows(xy_tris, size, margin)
    count = ext[:, 0] * ext[:, 1]
    ends = count.cumsum(0)
    idx, val, first = [], [], 0
    while first < len(count):                                  # blocks of at most CHUNK pixels (one triangle at least)
        last = max(int(torch.searchsorted(ends, ends[first - 1] + CHUNK if first else CHUNK, right=True)), first + 1)
        who = torch.arange(first, last, device=xy_tris.device)
        n = count[who]
        tri_of = torch.repeat_interleave(torch.arange(len(who), device=xy_tris.device), n)
        local = torch.arange(len(tri_of), device=xy_tris.device) - (n.cumsum(0) - n)[tri_of]
        width = ext[who, 0][tri_of].clamp(min=1)
        gx, gy = lo[who, 0][tri_of] + local % width, lo[who, 1][tri_of] + local // width
        d2, inside = signed_d2(gx + 0.5, gy + 0.5, xy_tris[who][tri_of])
        val.append(squash(torch.where(inside, 1.0, -1.0) * d2 / tau ** 2, dist))
        idx.append(gy * size[0] + gx)
        first = last
    return torch.cat(idx), torch.cat(val)


def soft_mask(xy_tris, shape=SHAPE, tau=0.5, dist="logistic", agg="prob", ss=1):
    """Soft silhouette [H, W] in [0, 1] of the triangles xy_tris [T,3,2] at canvas coordinates (pixel centres at
    i + 0.5). `ss`: evaluated at ss x the resolution and averaged back (what optimize_verts.pool does with SS)."""
    h, w = shape[0] * ss, shape[1] * ss
    if not len(xy_tris):
        return xy_tris.new_zeros(shape)
    idx, val = triangle_terms(xy_tris * ss, (w, h), tau * ss, dist)
    if agg == "prob":                                          # 1 - prod(1 - D), as a sum of logs
        total = xy_tris.new_zeros(h * w).index_add(0, idx, torch.log1p(-val.clamp(max=1 - 1e-6)))
        out = 1 - torch.exp(total)
    elif agg == "yager2":                                      # min(1, sqrt(sum D^2))
        total = xy_tris.new_zeros(h * w).index_add(0, idx, val * val)
        out = torch.where(total > 0, total.clamp(min=EPS).sqrt(), total).clamp(max=1)
    else:
        raise ValueError(f"agg {agg!r}: prob | yager2")
    return torch.nn.functional.avg_pool2d(out.reshape(1, 1, h, w), ss).reshape(shape) if ss > 1 else out.reshape(shape)


def asym_weights(view):
    """(w_red, w_green) of a view name from the coupling gates (silhouette.UNCOVERED_MAX / SPILL_MAX): each share is
    priced by 1 / its cap, so a share at its cap costs the same on either side; scaled to w_red + w_green = 2 (the
    symmetric loss' scale). left: caps .20 / .15 -> (.857, 1.143), the green dearer; top: .25 / .25 -> (1, 1)."""
    inv_r, inv_g = 1 / S.UNCOVERED_MAX.get(view, 1), 1 / S.SPILL_MAX.get(view, 1)
    return 2 * inv_r / (inv_r + inv_g), 2 * inv_g / (inv_r + inv_g)


def soft_asym(mask, concept, w_red=1.0, w_green=1.0):
    """DVR Eq. 14-15 as masks: w_red * sum C(1-S)/sum C (sheet left bare = occupancy) + w_green * sum S(1-C)/sum S
    (model outside the sheet = freespace). The two shares are the soft uncovered / spill of silhouette.coupling."""
    red = (concept * (1 - mask)).sum() / concept.sum().clamp(min=EPS)
    green = (mask * (1 - concept)).sum() / mask.sum().clamp(min=EPS)
    return w_red * red + w_green * green


def soft_iou(mask, concept, mode="sym", w_red=1.0, w_green=1.0):
    """sum min / sum max of the soft mask and the sheet's panel (what optimize_verts.Ctx.iou computes today).
    mode "asym": 1 - soft_asym, so that `1 - soft_iou` is the asymmetric loss (the weights only matter there)."""
    if mode == "asym":
        return 1 - soft_asym(mask, concept, w_red, w_green)
    if mode != "sym":
        raise ValueError(f"mode {mode!r}: sym | asym")
    return torch.minimum(mask, concept).sum() / torch.maximum(mask, concept).sum()


def loss(pos, tri, view, tau=0.5, dist="logistic", agg="prob", ss=1, mode="sym", detach=False, w_red=None, w_green=None):
    """1 - soft IoU of the mesh (torch Z-up positions [N,3], int triangles [T,3]) with the view's panel; mode "asym":
    the weighted red / green loss instead (weights given, or asym_weights(view.name) when both are None)."""
    xy = project(pos, view, detach)
    concept = torch.as_tensor(view.concept, dtype=pos.dtype, device=pos.device)
    if mode == "asym" and w_red is None and w_green is None:   # ponytail: both or neither
        w_red, w_green = asym_weights(view.name)
    return 1 - soft_iou(soft_mask(xy[tri], concept.shape, tau, dist, agg, ss), concept, mode, w_red, w_green)


def load_welded(glb):
    """(welded Z-up positions, triangles) of a GLB, as deform_to_sheet.rewrite hands them to a change."""
    data, doc, base = D.read(glb)
    parts, tri_all = D.geometry(data, doc, base)
    uniq, inv = D.weld(D.to_z_up(np.vstack([p for p, _, _ in parts]).astype(np.float64)))
    tri = inv[tri_all]
    return uniq, tri[(tri[:, 0] != tri[:, 1]) & (tri[:, 1] != tri[:, 2]) & (tri[:, 0] != tri[:, 2])]


def run_views(run_dir, sheet, layout="unit"):
    """(welded positions, triangles, the 6 Views) of <run_dir>/clay.glb at the cameras of its silhouette.json."""
    run_dir = pathlib.Path(run_dir)
    pos, tri = load_welded(run_dir / "clay.glb")
    tilt = json.loads((run_dir / "silhouette.json").read_text()).get("tilt")
    cams = {v: tuple(c) if isinstance(c, list) else c for v, c in tilt.items()} if tilt else None
    names = ("front", "left", "back", "top", "bottom", "rts")
    panels = D.sheet_panels(pathlib.Path(sheet), names, layout)
    return pos, tri, D.make_views(pos, tri, panels, names, cams=cams)


def main():
    import time

    import optimize_verts as O
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("sheet")
    ap.add_argument("--tau", type=float, default=0.5)
    ap.add_argument("--dist", default="logistic")
    ap.add_argument("--agg", default="prob")
    ap.add_argument("--device", default="cpu")
    a = ap.parse_args()
    pos, tri, views = run_views(a.run_dir, a.sheet)
    p = torch.tensor(pos, dtype=torch.float32, device=a.device, requires_grad=True)
    t = torch.as_tensor(tri, device=a.device)
    print(f"{len(tri)} tris, tau {a.tau} {a.dist}/{a.agg} on {a.device}")
    for v in views:
        hard, coverage = S.iou(v.concept, D.view_state(pos, tri, v)[1]), O.Ctx(v, pos, tri).iou
        start = time.perf_counter()
        value = loss(p, t, v, a.tau, a.dist, a.agg)
        value.backward()
        ms = 1000 * (time.perf_counter() - start)
        print(f"{v.name:6} hard {hard:.4f} coverage {coverage:.4f} soft {1 - value.item():.4f} "
              f"|d| {abs(1 - value.item() - coverage):.4f}  {ms:.0f} ms")


if __name__ == "__main__":
    main()
