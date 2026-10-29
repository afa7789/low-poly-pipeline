#!/usr/bin/env python3
"""Guarded QEM retopology of a dense closed shell (PIPELINE 28.L10-3): numpy only, python3.14 and Blender's Python.

    verts, tris, report = reduce(verts, tris, target_faces, sdf=None, features_deg=35, min_angle=15, floor=0.9)

Garland & Heckbert 1997 edge collapse, with what a blind COLLAPSE lacks:
  * feature quadrics: an edge whose two faces meet at >= `features_deg` (measured on the INPUT mesh) adds a plane through it,
    perpendicular to its faces, with a heavy weight to both ends; a vertex with >= 3 feature edges is a corner and never moves;
    a feature vertex absorbs a plain one (it keeps its place); two feature vertices join only along a feature edge (a chord
    across a corner is never collapsed);
  * quality guard: a collapse is refused when a surviving triangle would get a smallest angle under `min_angle` (unless it was
    that bad already and does not get worse), or its normal would turn (dot < 0) or vanish, or the link condition fails
    (more shared neighbours than the two opposite vertices: the shell would pinch);
  * `sdf(points (N, 3)) -> d (N,)` (negative inside): the new vertex of a collapse is Newton-projected onto the zero set,
    p <- p - d(p) grad d / |grad d|^2 (2 steps, central differences), before the guard looks at it; `polish` (default `sdf`)
    does the same over every non-corner vertex at the end and backs the moves that turn a face;
  * target: stop at F <= B (B = target_faces; V* = (B + 4) / 2 on a closed genus-0 shell, F = 2V - 4) and never go under
    floor * B. If nothing collapsible is left above B the guard is relaxed in stages (min_angle halves, then 0; the turn guard
    stays) and the report says so.
Not a heap: the collapses go in rounds. Each round costs every edge (vectorized: cost + best position), takes the edges that are
the cheapest of their 2-ring (an independent set: no two touch, so applying them together equals applying them one after the
other), projects and guards them all at once and applies the ones that pass; an edge that fails is banned until its
neighbourhood changes. A python heap with a few numpy calls per collapse measured 9.7 s on 34 k triangles (PIPELINE 28.L10-3).
The last round is cut to land inside [floor * B, B]. The input must be a welded, closed, manifold triangle shell.
"""
import time

import numpy as np

FEATURE_W = 100.0       # weight of a feature plane, x (edge length)^2: a face plane weighs its area
LEN_REG = 1e-2          # ties between flat edges go to the short one: + (LEN_REG x size)^2 x length^2 on the cost
CLAMP = 1.0             # the optimum may sit at most this many edge lengths from the edge's midpoint
DAMP = 1e-4             # Tikhonov damping of the 3x3 solve, x the mean eigenvalue
NEWTON = 2              # projection steps after each collapse
TINY = 1e-12            # x size^2: a triangle under this area is gone
RELAX = (0.8, 0.6, 0.4, 0.2, 0.0)   # min_angle factors tried, one after the other, when nothing collapsible is left above the target
RULES = ("corner", "absorb", "chord")   # the feature rules that apply (corners fixed / a feature vertex absorbs a plain one / no chords)
SLACK = 1.0             # a fallback position is taken when its quadric error is within this factor of the optimum's
ROUNDS = 2000           # safety stop
PASSES = 4              # independent sets per round (the edges that fail are banned between them)
OFFSETS = np.vstack([np.zeros(3), np.eye(3), -np.eye(3)])
REASONS = ("ok", "degenerate", "turned", "angle", "link")


# ---------------------------------------------------------------- numpy helpers
def tri_normals(P, T):
    """(unit normals, areas) of the triangles T over positions P; a collapsed triangle has a zero normal."""
    c = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    ln = np.linalg.norm(c, axis=1)
    return c / np.maximum(ln, 1e-300)[:, None], ln / 2


def min_angles(p):
    """Smallest inner angle (degrees) of each triangle p[F, 3, 3]."""
    e = np.stack([p[:, 1] - p[:, 0], p[:, 2] - p[:, 1], p[:, 0] - p[:, 2]], 1)
    ln = np.maximum(np.linalg.norm(e, axis=2), 1e-300)
    cos = -np.einsum("fid,fid->fi", e, np.roll(e, 1, 1)) / (ln * np.roll(ln, 1, 1))
    return np.degrees(np.arccos(np.clip(cos, -1, 1))).min(1)


def edge_faces(T, n):
    """(sorted unique edge keys a * n + b with a < b, first face, second face or -1, faces on the edge)."""
    a, b = T.ravel(), T[:, [1, 2, 0]].ravel()
    key = np.minimum(a, b) * n + np.maximum(a, b)
    order = np.argsort(key, kind="stable")
    ks, fs = key[order], (np.arange(len(key)) // 3)[order]
    start = np.flatnonzero(np.r_[True, ks[1:] != ks[:-1]])
    count = np.diff(np.r_[start, len(ks)])
    second = np.where(count >= 2, fs[np.minimum(start + 1, len(ks) - 1)], -1)
    return ks[start], fs[start], second, count


def scatter_quadric(idx, K, n):
    """Sum of the (m, 4, 4) quadrics K into (n, 4, 4) by vertex index idx (m,)."""
    Q = np.zeros((n, 4, 4))
    for i in range(4):
        for j in range(i, 4):
            Q[:, i, j] = Q[:, j, i] = np.bincount(idx, K[:, i, j], minlength=n)
    return Q


def plane_quadric(normal, point, weight):
    """weight * [n, d][n, d]^T for the planes through `point` with unit `normal` (m, 3)."""
    p = np.c_[normal, -np.einsum("kd,kd->k", normal, point)]
    return weight[:, None, None] * p[:, :, None] * p[:, None, :]


def feature_edges(P, T, deg):
    """(keys of the edges with dihedral >= deg on exactly 2 faces, their unit normal averaged over the two faces)."""
    keys, f0, f1, count = edge_faces(T, len(P))
    n, _ = tri_normals(P, T)
    two = count == 2
    n0, n1 = n[f0[two]], n[f1[two]]
    sharp = np.degrees(np.arccos(np.clip(np.einsum("kd,kd->k", n0, n1), -1, 1))) >= deg
    avg = n0 + n1
    avg = avg / np.maximum(np.linalg.norm(avg, axis=1), 1e-300)[:, None]
    return keys[two][sharp], avg[sharp]


def initial_quadrics(P, T, keys, feat_n):
    """Face quadrics (area weighted) + the feature planes of the `keys` edges (weight FEATURE_W x length^2)."""
    n, area = tri_normals(P, T)
    Q = scatter_quadric(T.ravel(), np.repeat(plane_quadric(n, P[T[:, 0]], area), 3, axis=0), len(P))
    if len(keys):
        a, b = keys // len(P), keys % len(P)
        d = P[b] - P[a]
        ln = np.linalg.norm(d, axis=1)
        c = np.cross(d / np.maximum(ln, 1e-300)[:, None], feat_n)
        c /= np.maximum(np.linalg.norm(c, axis=1), 1e-300)[:, None]
        Kf = np.repeat(plane_quadric(c, P[a], FEATURE_W * ln * ln), 2, axis=0)
        Q += scatter_quadric(np.stack([a, b], 1).ravel(), Kf, len(P))
    return Q


def grid_sdf(grid, origin, voxel):
    """d(points) by trilinear interpolation of an (nx, ny, nz) grid (sdf_body.Field.grid): the cheap field for the loop.
    Outside the grid the nearest cell's value (the field is truncated there anyway)."""
    top = np.array(grid.shape) - 1.0

    def d(points):
        g = np.clip((np.asarray(points, float).reshape(-1, 3) - origin) / voxel, 0, top - 1e-9)
        i = g.astype(int)
        f = g - i
        out = 0.0
        for dx, dy, dz in np.ndindex(2, 2, 2):
            w = np.where(dx, f[:, 0], 1 - f[:, 0]) * np.where(dy, f[:, 1], 1 - f[:, 1]) * np.where(dz, f[:, 2], 1 - f[:, 2])
            out = out + w * grid[i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz]
        return out
    return d


def euler(n_verts, n_tris):
    """F - 2V + 4: 0 on a closed genus-0 shell (-4 per handle, +8 per extra component)."""
    return int(n_tris - 2 * n_verts + 4)


def newton_step(sdf, p, h):
    """One step p - d grad d / |grad d|^2 for the points p (K, 3); the step vectors (K, 3)."""
    d = sdf((p[:, None, :] + h * OFFSETS[None]).reshape(-1, 3)).reshape(-1, 7)
    g = np.stack([d[:, 1] - d[:, 4], d[:, 2] - d[:, 5], d[:, 3] - d[:, 6]], 1) / (2 * h)
    return d[:, :1] * g / np.maximum(np.einsum("kd,kd->k", g, g), 1e-12)[:, None]


def project(sdf, p, h, reach):
    """NEWTON steps toward the zero set, none longer than `reach` (K,)."""
    for _ in range(NEWTON):
        step = newton_step(sdf, p, h)
        p = p - step * np.minimum(1.0, reach / np.maximum(np.linalg.norm(step, axis=1), 1e-300))[:, None]
    return p


def adjacency(keys, n):
    """CSR of the vertex graph of the sorted unique edge keys: (ptr (n + 1,), neighbours)."""
    lo, hi = keys // n, keys % n
    src = np.r_[lo, hi]
    order = np.argsort(src, kind="stable")
    return np.r_[0, np.cumsum(np.bincount(src, minlength=n))], np.r_[hi, lo][order]


def common_neighbours(keys, n, adj, a, b):
    """Number of vertices adjacent to both a[k] and b[k] (keys: the sorted unique edge keys, adj: adjacency(keys, n))."""
    ptr, dst = adj
    deg = ptr[a + 1] - ptr[a]
    owner = np.repeat(np.arange(len(a)), deg)
    w = dst[np.arange(deg.sum()) - np.repeat(np.cumsum(deg) - deg, deg) + ptr[a][owner]]
    k = np.minimum(w, b[owner]) * n + np.maximum(w, b[owner])
    hit = (keys[np.minimum(np.searchsorted(keys, k), len(keys) - 1)] == k) & (w != b[owner])
    return np.bincount(owner[hit], minlength=len(a))


# ---------------------------------------------------------------- the reducer
class Reducer:
    def __init__(self, verts, tris, sdf, features_deg, min_angle, grad_h=None):
        self.P = np.array(verts, float)
        self.n = len(self.P)
        self.T = np.asarray(tris, np.int64).copy()
        self.scale = float(np.ptp(self.P, axis=0).max())
        self.sdf, self.min_angle = sdf, min_angle
        self.h = grad_h or 1e-3 * self.scale
        self.FE, normal = np.zeros(0, np.int64), None
        if features_deg:
            self.FE, normal = feature_edges(self.P, self.T, features_deg)
        self.n_features = len(self.FE)
        self.Q = initial_quadrics(self.P, self.T, self.FE, normal)
        self.ban = np.zeros(0, np.int64)
        self.accepted, self.rounds, self.why = 0, 0, {}

    def feature_count(self):
        return np.bincount(np.r_[self.FE // self.n, self.FE % self.n], minlength=self.n)

    # -- costs
    def evaluate(self, a, b, fcnt):
        """(cost (K,), position (K, 3)) of collapsing each edge a-b: the quadric optimum within CLAMP edge lengths of the
        midpoint, or the position the feature rules pin; inf where the edge must not collapse."""
        Qs = self.Q[a] + self.Q[b]
        A = Qs[:, :3, :3]
        pa, pb = self.P[a], self.P[b]
        mid = (pa + pb) / 2
        mu = DAMP * np.einsum("kii->k", A) / 3 + 1e-30
        rhs = -(Qs[:, :3, 3] + np.einsum("kij,kj->ki", A, mid))
        dx = np.linalg.solve(A + mu[:, None, None] * np.eye(3), rhs[:, :, None])[:, :, 0]
        ln = np.linalg.norm(pb - pa, axis=1)
        dx *= np.minimum(1.0, CLAMP * ln / np.maximum(np.linalg.norm(dx, axis=1), 1e-300))[:, None]
        never, stay_a, stay_b = self.pin(a, b, fcnt)
        x = np.where(stay_a[:, None], pa, np.where(stay_b[:, None], pb, mid + dx))
        xh = np.c_[x, np.ones(len(x))]
        cost = np.einsum("ki,kij,kj->k", xh, Qs, xh) + (LEN_REG * self.scale) ** 2 * ln * ln
        return np.where(never, np.inf, np.maximum(cost, 0.0)), x

    def pin(self, a, b, fcnt):
        """(must not collapse, keeps a's place, keeps b's place) per edge, from the feature degrees of its two ends."""
        fa, fb = fcnt[a], fcnt[b]
        r = RULES
        on_feature = np.isin(np.minimum(a, b) * self.n + np.maximum(a, b), self.FE)
        corner_a, corner_b = (fa >= 3) & ("corner" in r), (fb >= 3) & ("corner" in r)
        stay_a = corner_a | ((fa >= 1) & (fb == 0) & ("absorb" in r))
        stay_b = (corner_b | ((fb >= 1) & (fa == 0) & ("absorb" in r))) & ~stay_a
        return (corner_a & corner_b) | ((fa > 0) & (fb > 0) & ~on_feature & ("chord" in r)), stay_a, stay_b

    # -- one round
    def select(self, lo, hi, cost, ok):
        """Indices among `ok` of the edges that are the cheapest of their 2-ring (an independent set), cheapest first."""
        if not len(ok):
            return ok
        order = np.argsort(cost[ok], kind="stable")
        rank = np.empty(len(ok), np.int64)
        rank[order] = np.arange(len(ok))
        m1 = np.full(self.n, len(ok))
        np.minimum.at(m1, lo[ok], rank)
        np.minimum.at(m1, hi[ok], rank)
        m2 = m1.copy()
        np.minimum.at(m2, lo, m1[hi])
        np.minimum.at(m2, hi, m1[lo])
        mine = rank == np.minimum(m2[lo[ok]], m2[hi[ok]])
        return ok[order][mine[order]]

    def shared(self, e):
        """Faces that hold both ends of a selected edge (they disappear with it)."""
        has = e >= 0
        return ((e[:, 0] == e[:, 1]) & has[:, 0]) | ((e[:, 1] == e[:, 2]) & has[:, 1]) | ((e[:, 0] == e[:, 2]) & has[:, 0])

    def guard(self, a, b, x):
        """Per selected collapse: 0 if it passes, else 1 degenerate, 2 turned, 3 angle (the worst wins)."""
        eid = np.full(self.n, -1)
        eid[a] = eid[b] = np.arange(len(a))
        e = eid[self.T]
        touched = np.flatnonzero((e >= 0).any(1) & ~self.shared(e))
        tri, owner = self.T[touched], e[touched].max(1)
        old = self.P[tri]
        new = np.where((e[touched] >= 0)[:, :, None], x[owner][:, None, :], old)
        n0, _ = tri_normals(self.P, tri)
        c = np.cross(new[:, 1] - new[:, 0], new[:, 2] - new[:, 0])
        why = np.zeros(len(a), np.int8)
        for code, bad in ((3, min_angles(new) < np.minimum(self.min_angle, min_angles(old))),
                          (2, np.einsum("fd,fd->f", n0, c) < 0),
                          (1, np.linalg.norm(c, axis=1) / 2 < TINY * self.scale ** 2)):
            why[owner[bad]] = code
        return why

    def settle(self, a, b, best, link):
        """(why, position) per picked edge: the quadric optimum, else a's place, b's, the midpoint: the first one the guard
        passes (why 0) and whose quadric error is within SLACK x the optimum's (+ the length term), else the last reason.
        `link` flags the edges that fail the link condition (why 4, not tried)."""
        pa, pb = self.P[a], self.P[b]
        Qs, ln = self.Q[a] + self.Q[b], np.linalg.norm(pb - pa, axis=1)
        err = lambda p: np.einsum("ki,kij,kj->k", np.c_[p, np.ones(len(p))], Qs, np.c_[p, np.ones(len(p))])  # noqa: E731
        cap = SLACK * err(best) + (LEN_REG * self.scale) ** 2 * ln * ln
        pos, why, pending = best.copy(), np.where(link, 4, 0).astype(np.int8), ~link
        for k, cand in enumerate((best, pa, pb, (pa + pb) / 2)):
            todo = np.flatnonzero(pending)
            if not len(todo):
                break
            c = cand[todo]
            if self.sdf is not None:
                c = project(self.sdf, c, self.h, ln[todo])
            r = self.guard(a[todo], b[todo], c)
            r[(r == 0) & (err(cand)[todo] > cap[todo])] = 3
            pos[todo], why[todo] = c, r
            pending[todo[r == 0]] = False
        return why, pos

    def step(self, goal):
        """One round: the number of edges tried (0: nothing is left to try). PASSES times: pick an independent set among the
        edges not banned and not next to a collapse already taken this round, guard it, ban what fails, take the rest."""
        keys, _, _, count = edge_faces(self.T, self.n)
        lo, hi = keys // self.n, keys % self.n
        cost, x = self.evaluate(lo, hi, self.feature_count())
        adj = adjacency(keys, self.n)
        free = (count == 2) & np.isfinite(cost) & ~np.isin(keys, self.ban)
        blocked, take, tried, need = np.zeros(self.n, bool), [], 0, (len(self.T) - goal + 1) // 2
        for _ in range(PASSES):
            pick = self.select(lo, hi, cost, np.flatnonzero(free & ~blocked[lo] & ~blocked[hi]))
            if not len(pick) or need <= 0:
                break
            tried += len(pick)
            a, b = lo[pick], hi[pick]
            why, xs = self.settle(a, b, x[pick], common_neighbours(keys, self.n, adj, a, b) != 2)
            for code in np.unique(why[why > 0]):
                self.why[REASONS[code]] = self.why.get(REASONS[code], 0) + int((why == code).sum())
            free[pick[why > 0]] = False
            self.ban = np.union1d(self.ban, keys[pick][why > 0])
            ok = np.flatnonzero(why == 0)[:need]
            need -= len(ok)
            take.append((a[ok], b[ok], xs[ok]))
            seed = np.zeros(self.n, bool)
            seed[a[ok]] = seed[b[ok]] = True
            near = seed[lo] | seed[hi]
            blocked |= seed
            blocked[lo[near]] = blocked[hi[near]] = True
        if take:
            self.apply(*(np.concatenate(c) for c in zip(*take)))
        return tried

    def apply(self, a, b, x):
        rep = np.arange(self.n)
        rep[b] = a
        T = rep[self.T]
        self.T = T[(T[:, 0] != T[:, 1]) & (T[:, 1] != T[:, 2]) & (T[:, 0] != T[:, 2])]
        self.P[a] = x
        self.Q[a] += self.Q[b]
        for name in ("FE", "ban"):
            setattr(self, name, self.renamed(getattr(self, name), rep, a if name == "ban" else None))
        self.accepted += len(a)

    def renamed(self, keys, rep, lift):
        """Edge keys after the merges; with `lift` (the surviving vertices) the keys around them are dropped."""
        u, v = rep[keys // self.n], rep[keys % self.n]
        keep = u != v
        if lift is not None and len(lift):
            near = np.unique(self.T[np.isin(self.T, lift).any(1)])
            keep &= ~(np.isin(u, near) | np.isin(v, near))
        return np.unique(np.minimum(u, v)[keep] * self.n + np.maximum(u, v)[keep])

    def run(self, goal, lowest):
        """Rounds until F <= goal or nothing is left to try; never F < lowest. True when the goal is met."""
        while len(self.T) > goal and self.rounds < ROUNDS and len(self.T) - 2 >= lowest:
            self.rounds += 1
            if self.step(goal) == 0:
                break
        return len(self.T) <= goal

    # -- end
    def polish(self, d):
        """NEWTON steps on every vertex that is not a corner, then back the moves that turn a face."""
        used = np.unique(self.T)
        move = (self.feature_count()[used] < 3)[:, None]
        old = self.P.copy()
        for _ in range(NEWTON):
            self.P[used] -= np.where(move, newton_step(d, self.P[used], self.h), 0.0)
        n0, _ = tri_normals(old, self.T)
        c = np.cross(self.P[self.T[:, 1]] - self.P[self.T[:, 0]], self.P[self.T[:, 2]] - self.P[self.T[:, 0]])
        back = np.unique(self.T[np.einsum("fd,fd->f", n0, c) < 0])
        self.P[back] = old[back]
        return len(back)

    def result(self):
        used = np.unique(self.T)
        remap = np.full(self.n, -1)
        remap[used] = np.arange(len(used))
        return self.P[used], remap[self.T]


def reduce(verts, tris, target_faces, sdf=None, features_deg=35, min_angle=15, floor=0.9, polish=None, grad_h=None):
    """(verts, tris, report) with `target_faces` triangles at most (and at least floor x target_faces unless the guard
    stops it sooner). `sdf`: see the module doc, None = no projection; `features_deg` None / 0 = no feature quadrics;
    `polish`: the field of the final projection, default `sdf`; `grad_h`: central-difference step (default 1e-3 x size)."""
    t0 = time.perf_counter()
    R = Reducer(verts, tris, sdf, features_deg, min_angle, grad_h)
    f0, v0 = len(R.T), len(np.unique(R.T))
    lowest = floor * target_faces
    met, relaxed, stages = R.run(target_faces, lowest), None, [(min_angle, len(R.T))]
    for k in RELAX:
        if met:
            break
        relaxed = R.min_angle = min_angle * k
        R.ban = R.ban[:0]
        met = R.run(target_faces, lowest)
        stages.append((relaxed, len(R.T)))
    final = polish or sdf
    reverted = R.polish(final) if final is not None else 0
    out_v, out_t = R.result()
    fcnt = R.feature_count()[np.unique(R.T)]
    report = {"faces_in": f0, "verts_in": v0, "faces": len(out_t), "verts": len(out_v), "euler_in": euler(v0, f0),
              "euler": euler(len(out_v), len(out_t)), "accepted": R.accepted, "refused": dict(R.why), "rounds": R.rounds,
              "features": R.n_features, "corners": int((fcnt >= 3).sum()), "target_met": bool(met),
              "relaxed_min_angle": relaxed, "stages": stages, "polish_reverted": int(reverted),
              "seconds": round(time.perf_counter() - t0, 3)}
    return out_v, out_t, report


def main():
    import argparse
    import json
    import pathlib
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("npz", help="verts + tris of a dense closed shell")
    ap.add_argument("target", type=int)
    ap.add_argument("--no-features", action="store_true")
    ap.add_argument("--out", help="npz of the result")
    a = ap.parse_args()
    z = np.load(a.npz)
    v, t, rep = reduce(z["verts"], z["tris"], a.target, features_deg=None if a.no_features else 35)
    if a.out:
        np.savez(pathlib.Path(a.out), verts=v, tris=t)
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
