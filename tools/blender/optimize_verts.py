#!/usr/bin/env python3
"""Fixed-topology vertex optimisation of a unit GLB against the sheet (Wiersma 2026 §3-4, PIPELINE 24.L6-7).

    python3.14 tools/blender/optimize_verts.py <in.glb> <sheet.jpg> <out.glb>
        [--views front,left,back,top,bottom,rts] [--iters 30] [--seconds 120]

The triangle budget is fixed: only the positions of the body's welded vertices move (the other connected
components, the props, stay), no SDS and no diffusion. Objective, in units of the model height:

    sum over views of (1 - soft IoU of the rasterised triangles with the sheet panel)     [silhouette]
  + lam_c * mean squared distance of the contour vertices to the panel's outline           [chamfer, Eq. 5]
  + lam_f * mean ((inner angle - pi/3) / (pi/3))^2 over the triangles                      [fairness]
  + lam_l * mean |L (x - x0)|^2 over the vertices                                          [smooth displacement]

GRAD = "soft" (default, L8-2): the silhouette gradient is `loss.backward()` of soft_sil (differentiable raster, TAU px
edge band, one pass over all views); accept / holds / evaluate stay on the hard raster below. GRAD = "fd" keeps the
L6-7 gradient: a forward finite difference per vertex, evaluated locally: the 1-ring's triangles
are re-rasterised (4x supersampled, so the coverage is continuous in the position) in a small window and the
IoU is updated incrementally. Fairness uses finite differences per triangle corner, chamfer and Laplacian are
analytic. Descent steps move at most STEP * H; a step that turns a face over or leaves a new sliver
(< mesh_lint.SLIVER_DEG) is repaired by halving the moves of the vertices of those faces, and refused when
it still does, and the line search shrinks a step until the objective falls. Multi-resolution: first an
anchor vertex out of every ANCHOR_EVERY (the rest follow harmonically), then all of them.

Only POSITION and NORMAL change in the file (as deform_to_sheet.py): skin weights and UVs stay. No Blender.
"""
import argparse
import math
import pathlib
import sys
import time
from functools import cached_property

import numpy as np
from PIL import Image, ImageDraw
from scipy import sparse
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import spsolve

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import align_features as AF  # noqa: E402
import deform_to_sheet as D  # noqa: E402
import mesh_lint as ML  # noqa: E402
import silhouette as S  # noqa: E402
from views import RTS, layout_of  # noqa: E402

SS = 4                    # supersampling of the raster: the coverage of a pixel moves with a sub-pixel vertex
STEP = 0.02               # largest move of a vertex per step, fractions of the model height
FD = 0.006                # forward difference of the silhouette gradient, fractions of H (1.5 px)
FD_ANGLE = 1e-5           # same, for the fairness gradient
LAMBDA = {"chamfer": 10.0, "fair": 0.05, "lap": 10.0, "dihedral": 0.0}   # dihedral: L8-4 (NMR Eq. 6), 0 = off
ANCHOR_EVERY = 4
COARSE = 0.35             # share of the time budget given to the anchor stage
BLOCKS = 8                # height bands tried one by one when the whole step does not lower the objective
SHRINK = (1.0, 0.5, 0.25, 0.125, 0.0625, 0.03)    # the line search tries these shares of the step, longest first
CREASE = 0.05            # settled: a face must lose this much cosine against its corners' normal to count
SETTLE = 16               # rounds of `settled`
HALVE, REPAIR = 3, 24     # a step that spoils faces: the moves of their vertices are halved HALVE times, then dropped
GAIN = 1e-5               # the objective must fall by this much for a step to count
VIEW_MIN = 0.5            # a view that starts under this IoU is another drawing than the model: left out
GRAD = "soft"             # silhouette gradient: "soft" = autograd of soft_sil (L8-2), "fd" = the 1-ring finite difference (L6-7)
TAU = 0.5                # edge band of the soft raster, canvas px (measured L8-2: 0.5 > 1.0 > 2.0; below ~0.3 px sparse)
DETACH = False            # the bbox fit of the projection counts as a constant in the soft gradient (the fd one always does)
DEVICE = "cpu"            # torch device of the soft gradient: "cpu" | "mps"
DEFAULT_VIEWS = ("front", "left", "back", "top", "bottom", "rts")


def stamp(tri_xy):
    """(origin in supersampled px, boolean mask) of one triangle at canvas coordinates tri_xy[3,2]. The same
    triangle always gives the same stamp, so adding then subtracting it is exact."""
    lo = np.floor(tri_xy.min(0) * SS - 0.5).astype(int) - 1
    hi = np.ceil(tri_xy.max(0) * SS - 0.5).astype(int) + 2
    img = Image.new("L", (int(hi[0] - lo[0]), int(hi[1] - lo[1])), 0)
    ImageDraw.Draw(img).polygon([tuple(q * SS - 0.5 - lo) for q in tri_xy], fill=1)
    return lo, np.asarray(img, bool)


def blit(dst, off, lo, mask, sign=1):
    """dst (a window of the supersampled canvas at pixel offset `off`) += sign * mask placed at `lo`, clipped."""
    x0, y0 = lo - off
    h, w = mask.shape
    ya, yb = max(y0, 0), min(y0 + h, dst.shape[0])
    xa, xb = max(x0, 0), min(x0 + w, dst.shape[1])
    if ya < yb and xa < xb:
        part, new = dst[ya:yb, xa:xb], mask[ya - y0:yb - y0, xa - x0:xb - x0]
        if sign > 0:
            part += new
        else:
            part -= new


def pool(covered):
    """Coverage fraction per canvas pixel of a boolean supersampled array."""
    h, w = covered.shape
    return covered.reshape(h // SS, SS, w // SS, SS).sum(axis=(1, 3)) / (SS * SS)


class Ctx:
    """One view of the model at some positions: canvas coordinates, triangle count image, soft IoU sums. Given the
    previous Ctx of the same view, only the triangles whose canvas vertices moved are restamped."""

    def __init__(self, view, pos, tri, prev=None):
        uv = view.uv(pos)
        to_canvas, self.s = D.frame(uv, view.mirror)
        self.view, self.xy, self.tri = view, to_canvas(uv), tri
        zero = np.zeros(2, int)
        if prev is None:
            self.cnt = np.zeros((S.CANVAS_H * SS, S.CANVAS_W * SS), np.int16)
            self.stamps, todo = [None] * len(tri), np.arange(len(tri))
        else:
            self.cnt, self.stamps = prev.cnt.copy(), list(prev.stamps)
            todo = np.flatnonzero((self.xy[tri] != prev.xy[tri]).any(axis=(1, 2)))
            for t in todo:
                blit(self.cnt, zero, *self.stamps[t], -1)
        for t in todo:
            self.stamps[t] = stamp(self.xy[tri[t]])
            blit(self.cnt, zero, *self.stamps[t])
        self.c = view.concept.astype(float)
        self.cov = pool(self.cnt > 0)
        self.inter = float(np.minimum(self.cov, self.c).sum())
        self.union = float(np.maximum(self.cov, self.c).sum())

    @property
    def iou(self):
        return self.inter / self.union

    @cached_property
    def contour(self):
        """(world displacement of each vertex toward the panel's outline, 0 off the contour), unit-height frame."""
        move, near = D.pull(self.view, self.cov >= 0.5, self.xy, np.full(len(self.xy), -1))   # -1: whole outline, cached in View.goal
        d = np.stack([move[:, 0] / self.s * self.view.mirror, -move[:, 1] / self.s], 1)
        return d[:, :1] * self.view.ru + d[:, 1:] * self.view.rv, near


def iou_gradient(ctx, pos, tri, verts, rings):
    """d(1 - IoU)/d position of `verts`, forward differences with a window-local re-raster of each 1-ring."""
    g = np.zeros((len(verts), 3))
    ru, rv, s = ctx.view.ru, ctx.view.rv, ctx.s
    dxy = [FD * s * np.array([ru[k] * ctx.view.mirror, -rv[k]]) for k in range(3)]
    pad = FD * s * 1.5 + 2
    size = np.array([S.CANVAS_W, S.CANVAS_H])
    for i, v in enumerate(verts):
        ring = rings[v]
        if not len(ring):
            continue
        old = ctx.xy[tri[ring]]
        corner = (tri[ring] == v).argmax(1)
        lo = np.clip(np.floor(old.reshape(-1, 2).min(0) - pad), 0, size).astype(int)
        hi = np.clip(np.ceil(old.reshape(-1, 2).max(0) + pad), 0, size).astype(int)
        if (hi <= lo).any():
            continue
        cov0 = ctx.cov[lo[1]:hi[1], lo[0]:hi[0]]
        if cov0.min() > 1 - 1e-9:          # the model covers the whole window: no move in it changes the silhouette
            continue
        off = lo * SS
        win = ctx.cnt[lo[1] * SS:hi[1] * SS, lo[0] * SS:hi[0] * SS].copy()
        for t in ring:
            blit(win, off, *ctx.stamps[t], -1)
        c = ctx.c[lo[1]:hi[1], lo[0]:hi[0]]
        i0, u0 = np.minimum(cov0, c).sum(), np.maximum(cov0, c).sum()
        for k in range(3):
            if not dxy[k].any():
                continue
            cur = win.copy()
            for j, q in enumerate(old):
                q = q.copy()
                q[corner[j]] += dxy[k]
                blit(cur, off, *stamp(q))
            cov = pool(cur > 0)
            inter = ctx.inter + np.minimum(cov, c).sum() - i0
            union = ctx.union + np.maximum(cov, c).sum() - u0
            g[i, k] = (ctx.iou - inter / union) / FD
    return g


def soft_gradient(ctxs, pos, tri):
    """d sum(1 - soft IoU)/d position, all rows, one backward over every view (soft_sil, SoftRas Eq. 1+4). The hard
    contexts keep deciding what is accepted; this is only the direction."""
    import torch
    import soft_sil
    p = torch.tensor(pos, dtype=torch.float32, device=DEVICE, requires_grad=True)
    t = torch.as_tensor(tri, device=DEVICE)
    sum(soft_sil.loss(p, t, c.view, TAU, detach=DETACH) for c in ctxs).backward()
    return p.grad.cpu().numpy().astype(np.float64)


def flat_edges(pos, tri):
    """(face pairs [E,2] into `tri`) of the interior edges shared by exactly two faces whose dihedral at `pos` is under
    align_features.FEATURE_DEG: the live (WC3) edges are not in it. Faces of near-zero area are skipped."""
    q = pos[tri]
    cross = np.cross(q[:, 1] - q[:, 0], q[:, 2] - q[:, 0])
    area = np.linalg.norm(cross, axis=1)
    ok = area > D.TINY * np.median(area)
    pair = np.sort(np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]), axis=1)
    _, inv, count = np.unique(pair, axis=0, return_inverse=True, return_counts=True)
    inv = inv.reshape(-1)
    order = np.argsort(inv, kind="stable")
    shared = order[np.flatnonzero(count[inv[order]] == 2)].reshape(-1, 2)
    f = shared % len(tri)
    n = cross / np.maximum(area, 1e-30)[:, None]
    flat = ok[f[:, 0]] & ok[f[:, 1]] & (np.einsum("ed,ed->e", n[f[:, 0]], n[f[:, 1]]) > math.cos(math.radians(AF.FEATURE_DEG)))
    return f[flat]


def dihedral_term(pos, tri, faces):
    """(mean over `faces` of (cos theta + 1)^2, its gradient wrt `pos`), theta = dihedral between the two faces of an edge
    (flat = pi, so cos theta + 1 = 1 - n0 . n1; Neural Mesh Renderer Eq. 6). Analytic through torch autograd."""
    import torch
    if not len(faces):
        return 0.0, np.zeros_like(pos)
    p = torch.tensor(pos, dtype=torch.float64, requires_grad=True)
    q = p[torch.as_tensor(tri)]
    n = torch.cross(q[:, 1] - q[:, 0], q[:, 2] - q[:, 0], dim=1)
    n = n / n.norm(dim=1, keepdim=True).clamp_min(1e-12)
    f = torch.as_tensor(faces)
    loss = ((1 - (n[f[:, 0]] * n[f[:, 1]]).sum(1)) ** 2).mean()
    loss.backward()
    return float(loss.detach()), p.grad.numpy()


def tri_fairness(q):
    """Per triangle: mean ((inner angle - pi/3) / (pi/3))^2."""
    a = np.radians(ML.angles(q))
    return (((a - math.pi / 3) / (math.pi / 3)) ** 2).mean(1)


def fairness_gradient(pos, tri):
    """d mean(tri_fairness)/d position by forward differences per triangle corner."""
    q = pos[tri]
    base = tri_fairness(q)
    g = np.zeros_like(pos)
    for k in range(3):
        for a in range(3):
            q2 = q.copy()
            q2[:, k, a] += FD_ANGLE
            np.add.at(g[:, a], tri[:, k], (tri_fairness(q2) - base) / FD_ANGLE)
    return g / len(tri)


class Problem:
    """Everything the objective needs: the welded mesh in unit-height coordinates, the body, the views."""

    def __init__(self, pos, tri, views, nor, file):
        self.inv, self.tri_all = file       # the file's own vertices (split by normal / UV) and triangles
        self.height = float(np.ptp(pos[:, 2]))
        self.tri, self.views = tri, views
        self.pos0 = pos / self.height
        self.body = body_mask(tri, len(pos))
        self.tri_b = tri[self.body[tri].all(1)]
        self.ground = self.pos0[:, 2] < self.pos0[:, 2].min() + D.SOLE
        self.lap = D.laplacian(tri, len(pos))
        self.ref = D.reference(self.pos0, tri, nor)
        self.rings = ring_index(tri, len(pos))
        self.flat = flat_edges(self.pos0, self.tri_b)     # the edges the dihedral term smooths: fixed at the start
        self.nb = int(self.body.sum())
        self.floor = [0.0] * len(views)
        for v in views:      # the nearest outline pixel of the panel, once
            v.goal(-1)

    def holds(self, ctxs):
        """True when no view is under its floor (`floor`: the IoU of each at the start less D.GUARD, set by optimize)."""
        return all(c.iou >= f for c, f in zip(ctxs, self.floor))

    def evaluate(self, pos, prev=None):
        """(objective, per-view contexts, terms) at `pos`; `prev` = the contexts of a nearby position."""
        ctxs = [Ctx(v, pos, self.tri, prev[i] if prev else None) for i, v in enumerate(self.views)]
        terms = {"iou": float(sum(1 - c.iou for c in ctxs))}
        terms["chamfer"] = LAMBDA["chamfer"] * sum(
            float((np.linalg.norm(m, axis=1)[n & self.body] ** 2).sum()) for m, n in (c.contour for c in ctxs)) / self.nb
        terms["fair"] = LAMBDA["fair"] * float(tri_fairness(pos[self.tri_b]).mean())
        lap_d = (self.lap @ (pos - self.pos0))[self.body]
        terms["lap"] = LAMBDA["lap"] * float((lap_d ** 2).sum(1).mean())
        if LAMBDA["dihedral"]:
            terms["dihedral"] = LAMBDA["dihedral"] * dihedral_term(pos, self.tri_b, self.flat)[0]
        return sum(terms.values()), ctxs, terms

    def gradient(self, pos, ctxs, free):
        """d objective / d position, rows of `free` for the silhouette term, everywhere for the others."""
        g = np.zeros_like(pos)
        if GRAD == "soft":
            g[free] += soft_gradient(ctxs, pos, self.tri)[free]
        elif GRAD != "fd":
            raise ValueError(f"GRAD {GRAD!r}: soft | fd")
        for c in ctxs:
            if GRAD == "fd":
                g[free] += iou_gradient(c, pos, self.tri, free, self.rings)
            move, near = c.contour
            g -= 2 * LAMBDA["chamfer"] / self.nb * np.where((near & self.body)[:, None], move, 0.0)
        g += LAMBDA["fair"] * fairness_gradient(pos, self.tri_b)
        lap_d = np.where(self.body[:, None], self.lap @ (pos - self.pos0), 0.0)
        g += 2 * LAMBDA["lap"] / self.nb * (self.lap.T @ lap_d)
        if LAMBDA["dihedral"]:
            g += LAMBDA["dihedral"] * dihedral_term(pos, self.tri_b, self.flat)[1]
        return np.where(self.body[:, None], g, 0.0)


def body_mask(tri, n):
    """Vertices of the largest connected component (by triangles); the other components are props."""
    adj = sparse.coo_matrix((np.ones(3 * len(tri)), (tri.ravel(), np.roll(tri, 1, 1).ravel())), shape=(n, n))
    _, label = connected_components(adj, directed=False)
    return label == np.bincount(label[tri[:, 0]]).argmax()


def ring_index(tri, n):
    """Per vertex the indices of the triangles around it."""
    order = np.argsort(tri.ravel(), kind="stable")
    bounds = np.searchsorted(tri.ravel()[order], np.arange(n + 1))
    return [order[bounds[i]:bounds[i + 1]] // 3 for i in range(n)]


def spread(lap, d, known):
    """`d` with the rows not in `known` filled harmonically from those that are (solve L_uu x = -L_uk d_k)."""
    free = ~known
    if not free.any():
        return d
    a = (lap[free][:, free] + 1e-6 * sparse.identity(int(free.sum()))).tocsc()
    rhs = -(lap[free][:, known] @ d[known])
    out = d.copy()
    out[free] = np.stack([spsolve(a, rhs[:, k]) for k in range(d.shape[1])], 1)
    return out


def slivers(prob, pos):
    """Boolean per triangle: smallest angle under mesh_lint.SLIVER_DEG."""
    return ML.angles_min(pos[prob.tri]) < ML.SLIVER_DEG


def creased(prob, pos):
    """Per file triangle, the cosine between its normal and the area-weighted normal of its corners as the file holds
    them (vertices split by smoothing group; 1 for a face under the real-size floor): mesh_lint counts a real face
    under 0 as flipped (a sharp sliver between big faces)."""
    q = pos[prob.inv][prob.tri_all]
    cross = np.cross(q[:, 1] - q[:, 0], q[:, 2] - q[:, 0])
    acc = np.zeros((len(prob.inv), 3))
    for k in range(3):
        np.add.at(acc, prob.tri_all[:, k], cross)
    corner = acc[prob.tri_all].sum(1)
    size = np.linalg.norm(cross, axis=1)
    cos = np.einsum("fd,fd->f", cross, corner) / np.maximum(size * np.linalg.norm(corner, axis=1), 1e-12)
    return np.where(size > prob.ref[1], cos, 1.0)


def spoiled(prob, new, old):
    """Boolean per triangle: turned over, or a sliver that `old` (the slivers before) was not."""
    return D.turned(prob.ref, new, prob.tri) | (slivers(prob, new) & ~old)


def settled(prob, start, pos):
    """`pos` with the vertices of every face that turned over or got CREASE under 0 and worse than at `start` pulled
    back toward it by halves, then to it (the check is too coupled to the neighbours to be a per-step test: it
    refused most steps)."""
    pos, was = pos.copy(), creased(prob, start)
    for i in range(SETTLE):
        now = creased(prob, pos)
        bad = (now < 0) & (now < was - CREASE)
        turned = D.turned(prob.ref, pos, prob.tri)
        if not bad.any() and not turned.any():
            break
        v = np.unique(np.concatenate([prob.inv[prob.tri_all[bad]].ravel(), prob.tri[turned].ravel()]))
        pos[v] = start[v] + (0.5 if i < SETTLE - 2 else 0.0) * (pos[v] - start[v])
    return pos


def repaired(prob, old, step, old_slivers):
    """(pos after `step`, True when no face is turned and no new sliver): the vertices of spoiled faces move
    half as far, then stay, until none is (REPAIR rounds)."""
    step = step.copy()
    for i in range(REPAIR):
        bad = spoiled(prob, old + step, old_slivers)
        if not bad.any():
            return old + step, True
        step[np.unique(prob.tri[bad])] *= 0.5 if i < HALVE else 0.0
    return old + step, not spoiled(prob, old + step, old_slivers).any()


def descent_step(prob, g, free, known):
    """Move of every vertex against the gradient, the largest reaching STEP; the vertices not in `free` follow
    harmonically (stage 1) and the ground keeps its height."""
    raw = -np.where(free[:, None], g, 0.0)
    top = np.linalg.norm(raw, axis=1).max()
    if top <= 0:
        return None
    step = D.clamp(spread(prob.lap, raw * (STEP / top), known), STEP)
    step[prob.ground, 2] = 0.0
    return np.where(prob.body[:, None], step, 0.0)


def search(prob, pos, step, value, ctxs, log):
    """Line search along `step`: (objective, contexts, terms, positions) of the best share in SHRINK that is safe
    and lowers the objective below `value` without any view ending GUARD under its IoU at the start, or None. Stops at the first share that does worse than a better one."""
    old_slivers = slivers(prob, pos)
    best = None
    for share in SHRINK:
        new, ok = repaired(prob, pos, share * step, old_slivers)
        if not ok:
            log["unsafe"] += 1
            continue
        tried = prob.evaluate(new, ctxs)
        if tried[0] < (best or (value - GAIN,))[0] and prob.holds(tried[1]):
            best = (*tried, new)
        elif best:
            break
        else:
            log["worse"] += 1
    return best


def blocks(prob, free):
    """The free vertices in BLOCKS bands of height (equal counts), as boolean masks."""
    idx = np.flatnonzero(free)
    out = []
    for part in np.array_split(idx[np.argsort(prob.pos0[idx, 2])], BLOCKS):
        mask = np.zeros(len(free), bool)
        mask[part] = True
        out.append(mask)
    return out


def stage(prob, pos, free, known, iters, deadline, log):
    """Gradient descent on the vertices `free` until `iters`, the deadline, or nothing lowers the objective: when
    the whole step does not, it is tried one height block at a time (block coordinate descent)."""
    value, ctxs, terms = prob.evaluate(pos)
    for _ in range(iters):
        if time.time() > deadline:
            break
        step = descent_step(prob, prob.gradient(pos, ctxs, np.flatnonzero(free)), free, known)
        if step is None:
            break
        tries = [step] + [np.where(m[:, None], step, 0.0) for m in blocks(prob, free)]
        moved = False
        for part in tries:
            best = search(prob, pos, part, value, ctxs, log)
            if best:
                value, ctxs, terms, pos = best
                log["steps"] += 1
                moved = True
                if part is step:
                    break
        if not moved:
            break
    return pos, value, terms


def anchors(prob, free):
    """Every ANCHOR_EVERY-th free vertex in (height, x, y) order."""
    idx = np.flatnonzero(free)
    order = np.lexsort((prob.pos0[idx, 1], prob.pos0[idx, 0], prob.pos0[idx, 2]))
    out = np.zeros(len(free), bool)
    out[idx[order[::ANCHOR_EVERY]]] = True
    return out


def rts_axes(elev, azim):
    """Image axes (right, up) of the orthographic game camera at (elevation, azimuth), views.rts_offset."""
    e, a = math.radians(elev), math.radians(azim)
    fwd = -np.array([math.cos(e) * math.sin(a), -math.cos(e) * math.cos(a), math.sin(e)])
    right = np.cross(fwd, [0.0, 0.0, 1.0])
    right /= np.linalg.norm(right)
    return right, np.cross(right, fwd)


def rts_view(pos, tri, sheet):
    """The View of the sheet's rts panel at the camera whose raster matches it best (never mirrored), or None."""
    path = S.rts_path(pathlib.Path(sheet))
    if not path.exists():
        return None
    concept = S.normalize(S.foreground(path, 768))
    best = max((D.View("rts", *rts_axes(e, a), 1, concept, True) for e, a in RTS),
               key=lambda v: S.iou(concept, D.view_state(pos, tri, v)[1]))
    return best


def make_views(pos, tri, sheet, names, layout):
    """Views of the sheet among `names` (front/left/back, top/bottom with their tilt, rts)."""
    panels = {k: p for k, p in S.concept_panels(pathlib.Path(sheet), layout=layout).items()
              if k in names and (k in D.FRONT_AXES or k in D.S_TILTED)}
    views = D.make_views(pos, tri, panels, tuple(panels))
    rts = rts_view(pos, tri, sheet) if "rts" in names else None
    return views + [rts] if rts else views


def optimize(pos, tri, nor, file, sheet, names=DEFAULT_VIEWS, iters=30, seconds=120.0, layout="unit"):
    """(new welded Z-up positions, report) for the welded mesh: coarse stage on the anchors, fine on all."""
    start = time.time()
    views = make_views(pos, tri, sheet, names, layout)
    first = D.measure(pos, tri, views)
    skipped = [v.name for v in views if first[v.name]["iou"] < VIEW_MIN]     # a panel of another pose (a flier's rts)
    views = [v for v in views if v.name not in skipped]
    prob = Problem(pos, tri, views, nor, file)
    x0 = prob.pos0
    free = prob.body.copy()
    log = {"steps": 0, "unsafe": 0, "worse": 0}   # accepted; refused for a turned face / new sliver; refused for no gain
    value0, ctxs0, terms0 = prob.evaluate(x0)
    prob.floor = [c.iou - D.GUARD for c in ctxs0]
    anchor = anchors(prob, free)
    x, _, _ = stage(prob, x0, anchor, anchor | ~prob.body, iters, start + COARSE * seconds, log)
    x, value, terms = stage(prob, x, free, np.ones(len(pos), bool), iters, start + seconds, log)
    x = settled(prob, x0, x)
    value, _, terms = prob.evaluate(x)
    new = x * prob.height
    sliver = lambda p: round(D.sliver_share(p, tri), 4)  # noqa: E731
    report = {"before": first, "after": D.measure(new, tri, views), "objective": [round(value0, 5), round(value, 5)],
              "terms_before": {k: round(v, 5) for k, v in terms0.items()}, "terms_after": {k: round(v, 5) for k, v in terms.items()},
              "slivers_before": sliver(pos), "slivers_after": sliver(new),
              "fairness_before": round(float(tri_fairness(x0[tri]).mean()), 4),
              "fairness_after": round(float(tri_fairness(x[tri]).mean()), 4),
              "turned": int(D.turned(prob.ref, x, tri).sum()), "body_vertices": prob.nb, "vertices": len(pos),
              "views": [v.name for v in views], "skipped": skipped, "seconds": round(time.time() - start, 1), **log}
    return new, report


def run(glb, sheet, out, names=DEFAULT_VIEWS, iters=30, seconds=120.0, layout="unit"):
    """Optimise `glb` against the sheet and write `out`; returns the report (also written as <out>.verts.json)."""
    return D.rewrite(glb, out, lambda uniq, tri, nor, file: optimize(uniq, tri, nor, file, sheet, names, iters, seconds, layout),
                     suffix=".verts.json")


def apply(glb, args):
    """spec_pipeline hook: optimise `glb` in place when the run wants it (args.fit_verts on a unioned body),
    keeping the input as <stem>-prefit.glb. Returns the report or None."""
    if not (getattr(args, "fit_verts", False) and getattr(args, "union_body", False)):
        return None
    glb = pathlib.Path(glb)
    before = glb.with_name(f"{glb.stem}-prefit.glb")
    before.write_bytes(glb.read_bytes())
    return run(before, args.sheet, glb, layout=layout_of(args.kind))


def main():
    global GRAD, TAU, DEVICE
    ap = argparse.ArgumentParser()
    ap.add_argument("glb")
    ap.add_argument("sheet")
    ap.add_argument("out")
    ap.add_argument("--views", default=",".join(DEFAULT_VIEWS))
    ap.add_argument("--iters", type=int, default=30, help="descent steps per stage")
    ap.add_argument("--seconds", type=float, default=120.0)
    ap.add_argument("--grad", default=GRAD, choices=("soft", "fd"))
    ap.add_argument("--tau", type=float, default=TAU, help="soft raster edge band, px")
    ap.add_argument("--device", default=DEVICE, choices=("cpu", "mps"))
    ap.add_argument("--dihedral", type=float, default=LAMBDA["dihedral"], help="weight of the dihedral smoothing term, 0 = off")
    a = ap.parse_args()
    GRAD, TAU, DEVICE = a.grad, a.tau, a.device
    LAMBDA["dihedral"] = a.dihedral
    r = run(a.glb, a.sheet, a.out, tuple(a.views.split(",")), a.iters, a.seconds)
    for v in r["after"]:
        b, f = r["before"][v], r["after"][v]
        print(f"{v:6} IoU {b['iou']:.3f} -> {f['iou']:.3f}  red {b['uncovered']:.3f} -> {f['uncovered']:.3f}  "
              f"green {b['spill']:.3f} -> {f['spill']:.3f}")
    print(f"objective {r['objective'][0]} -> {r['objective'][1]}  steps {r['steps']} unsafe {r['unsafe']} worse {r['worse']}  "
          f"slivers {r['slivers_before']} -> {r['slivers_after']}  fairness {r['fairness_before']} -> "
          f"{r['fairness_after']}  turned {r['turned']}  {r['seconds']} s")


if __name__ == "__main__":
    main()
