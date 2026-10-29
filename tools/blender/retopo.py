#!/usr/bin/env python3
"""Guarded QEM retopology of a dense closed shell (PIPELINE 28.L10-3): numpy + heapq, python3.14 and Blender's Python.

    verts, tris, report = reduce(verts, tris, target_faces, sdf=None, features_deg=35, min_angle=15, floor=0.9)

Garland & Heckbert 1997 edge collapse with what a blind COLLAPSE lacks:
  * feature quadrics: an edge whose two faces meet at >= `features_deg` (measured on the INPUT mesh) adds a plane through it,
    perpendicular to its faces, with a heavy weight to both ends; a vertex with >= 3 feature edges is a corner and never moves;
    an edge between two feature vertices that is not itself a feature edge (a chord across a corner) is never collapsed;
  * quality guard: a collapse is refused when a surviving triangle would get a smallest angle under `min_angle` (unless it was
    that bad already and does not get worse) or its normal would turn (dot < 0) or vanish, or the link condition fails
    (more than the two opposite vertices shared: the shell would pinch);
  * `sdf(points (N, 3)) -> d (N,)` (negative inside): after each collapse the new vertex is Newton-projected onto the zero set,
    p <- p - d(p) grad d / |grad d|^2 (2 steps, central differences) before the guard looks at it; `polish` (default `sdf`)
    does the same over every non-corner vertex at the end, reverting a vertex whose faces would turn;
  * target: stop at F <= B (B = target_faces; V* = (B + 4) / 2 on a closed genus-0 shell, F = 2V - 4) and never go under
    floor * B (the last collapse that would is not made). If the heap runs dry above B the guard is relaxed in stages
    (min_angle halves, then 0; the turn guard stays), and the report says so.
The input must be a welded, closed, manifold triangle shell (a boundary edge is kept in place and never collapsed).
"""
import heapq
import math
import time

import numpy as np

FEATURE_W = 100.0       # weight of a feature plane, x (edge length)^2: a face plane weighs its area
CLAMP = 1.0             # the optimum may sit at most this many edge lengths from the edge's midpoint
NEWTON = 2              # projection steps after each collapse
TINY = 1e-12            # x (scale^2): a triangle under this area is gone
RELAX = (0.5, 0.0)      # min_angle factors tried when the heap runs dry above the target
OFFSETS = np.vstack([np.zeros(3), np.eye(3), -np.eye(3)])


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


def edge_faces(T):
    """(unique sorted edges (E, 2), faces per edge (E, 2) with -1 where there is no 2nd face, faces per edge count (E,))."""
    e = np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), axis=1)
    face = np.tile(np.arange(len(T)), 3)
    uniq, inv, count = np.unique(e, axis=0, return_inverse=True, return_counts=True)
    order = np.argsort(inv.reshape(-1), kind="stable")
    start = np.concatenate([[0], np.cumsum(count)[:-1]])
    first = face[order][start]
    second = np.where(count >= 2, face[order][np.minimum(start + 1, len(order) - 1)], -1)
    return uniq, np.c_[first, second], count


def feature_edges(P, T, deg):
    """(edges (k, 2), the unit normal averaged over their two faces (k, 3)) with dihedral >= deg on edges of exactly 2 faces."""
    edges, faces, count = edge_faces(T)
    n, _ = tri_normals(P, T)
    two = count == 2
    n0, n1 = n[faces[two, 0]], n[faces[two, 1]]
    sharp = np.degrees(np.arccos(np.clip(np.einsum("kd,kd->k", n0, n1), -1, 1))) >= deg
    avg = n0 + n1
    avg = avg / np.maximum(np.linalg.norm(avg, axis=1), 1e-300)[:, None]
    return edges[two][sharp], avg[sharp]


def initial_quadrics(P, T, feat, feat_n):
    """Face quadrics (area weighted) + the feature planes of `feat` edges (weight FEATURE_W x length^2)."""
    n, area = tri_normals(P, T)
    K = plane_quadric(n, P[T[:, 0]], area)
    Q = scatter_quadric(T.ravel(), np.repeat(K, 3, axis=0), len(P))
    if len(feat):
        d = P[feat[:, 1]] - P[feat[:, 0]]
        ln = np.linalg.norm(d, axis=1)
        c = np.cross(d / np.maximum(ln, 1e-300)[:, None], feat_n)
        c /= np.maximum(np.linalg.norm(c, axis=1), 1e-300)[:, None]
        Kf = plane_quadric(c, P[feat[:, 0]], FEATURE_W * ln * ln)
        Q += scatter_quadric(feat.ravel(), np.repeat(Kf, 2, axis=0), len(P))
    return Q


def grid_sdf(grid, origin, voxel):
    """d(points) by trilinear interpolation of an (nx, ny, nz) grid (sdf_body.Field.grid): the cheap field for the collapse
    loop. Outside the grid the nearest cell's value (the field is truncated there anyway)."""
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
    """F - 2V + 4: 0 on a closed genus-0 shell (2 per extra handle... -4 per handle, +8 per extra component)."""
    return int(n_tris - 2 * n_verts + 4)


# ---------------------------------------------------------------- the reducer
class Reducer:
    def __init__(self, verts, tris, sdf, features_deg, min_angle, grad_h=None):
        self.P = np.array(verts, float)
        self.n = len(self.P)
        self.T = [list(map(int, t)) for t in np.asarray(tris)]
        self.alive = [True] * len(self.T)
        self.nf = len(self.T)
        self.v2f = [set() for _ in range(self.n)]
        for f, t in enumerate(self.T):
            for v in t:
                self.v2f[v].add(f)
        self.version = [0] * self.n
        self.scale = float(np.ptp(self.P, axis=0).max())
        self.sdf, self.min_angle = sdf, min_angle
        self.h = grad_h or 1e-3 * self.scale
        self.why = {}
        self.accepted = 0
        self.fnb = [set() for _ in range(self.n)]
        feat, feat_n = feature_edges(self.P, np.asarray(self.T), features_deg) if features_deg else (np.zeros((0, 2), int), None)
        self.n_features = len(feat)
        for a, b in feat.tolist():
            self.fnb[a].add(b)
            self.fnb[b].add(a)
        self.Q = initial_quadrics(self.P, np.asarray(self.T), feat, feat_n)
        self.heap = []

    # -- feature state
    def is_corner(self, v):
        return len(self.fnb[v]) >= 3

    def feature_flags(self, ws):
        return np.array([len(self.fnb[w]) for w in ws])

    # -- candidates
    def evaluate(self, a, ws):
        """(cost (K,), position (K, 3)) of collapsing a with each w in ws: the quadric optimum within CLAMP edge lengths
        of the midpoint, or the feature rules' position; inf where the edge must not collapse."""
        ws = np.asarray(ws)
        Qs = self.Q[a] + self.Q[ws]
        A = Qs[:, :3, :3]
        pa, pw = self.P[a], self.P[ws]
        mid = (pa + pw) / 2
        dx = np.einsum("kij,kj->ki", np.linalg.pinv(A, rcond=1e-5, hermitian=True),
                       -(Qs[:, :3, 3] + np.einsum("kij,kj->ki", A, mid)))
        reach = CLAMP * np.linalg.norm(pw - pa, axis=1)
        dx *= np.minimum(1.0, reach / np.maximum(np.linalg.norm(dx, axis=1), 1e-300))[:, None]
        x = mid + dx
        bad = self.constrain(a, ws, x, pa, pw)
        xh = np.c_[x, np.ones(len(x))]
        cost = np.einsum("ki,kij,kj->k", xh, Qs, xh)
        return np.where(bad, np.inf, np.maximum(cost, 0.0)), x

    def constrain(self, a, ws, x, pa, pw):
        """Apply the feature rules in place on x; the mask of the edges that must not collapse. A corner stays where it is,
        a feature vertex absorbs a plain one, two feature vertices join only along a feature edge."""
        fa, fw = len(self.fnb[a]), self.feature_flags(ws)
        pin_a = np.full(len(ws), fa >= 3) | ((fa >= 1) & (fw == 0))
        pin_w = ((fw >= 3) | ((fw >= 1) & (fa == 0))) & ~pin_a
        x[pin_a] = pa
        x[pin_w] = pw[pin_w]
        chord = np.array([fa > 0 and fw[k] > 0 and ws[k] not in self.fnb[a] for k in range(len(ws))])
        return ((fa >= 3) & (fw >= 3)) | chord

    def push(self, a, ws):
        cost, x = self.evaluate(a, ws)
        va = self.version[a]
        for k, w in enumerate(ws):
            if cost[k] < np.inf:
                heapq.heappush(self.heap, (float(cost[k]), a, w, va, self.version[w], x[k, 0], x[k, 1], x[k, 2]))

    def rebuild(self):
        self.heap = []
        for a in range(self.n):
            if self.v2f[a]:
                ws = [w for w in self.neighbours(a) if w > a]
                if ws:
                    self.push(a, ws)
        heapq.heapify(self.heap)

    def neighbours(self, v):
        return sorted({u for f in self.v2f[v] for u in self.T[f]} - {v})

    # -- collapse
    def refuse(self, why):
        self.why[why] = self.why.get(why, 0) + 1
        return False

    def project(self, p, reach):
        for _ in range(NEWTON):
            d = self.sdf(p + self.h * OFFSETS)
            g = np.array([d[1] - d[4], d[2] - d[5], d[3] - d[6]]) / (2 * self.h)
            gg = float(g @ g)
            if gg < 1e-12:
                break
            step = d[0] * g / gg
            ln = float(np.linalg.norm(step))
            p = p - step * min(1.0, reach / ln) if ln > 0 else p
        return p

    def guard(self, a, b, shared, p):
        """The reason to refuse moving a and b to p, or None."""
        ids = list((self.v2f[a] | self.v2f[b]) - shared)
        tri = np.array([self.T[f] for f in ids])
        old = self.P[tri]
        new = np.where(((tri == a) | (tri == b))[:, :, None], p, old)
        n0, _ = tri_normals(self.P, tri)
        c = np.cross(new[:, 1] - new[:, 0], new[:, 2] - new[:, 0])
        area = np.linalg.norm(c, axis=1) / 2
        if (area < TINY * self.scale ** 2).any():
            return "degenerate"
        if (np.einsum("fd,fd->f", n0, c) < 0).any():
            return "turned"
        worse = min_angles(new)
        if (worse < np.minimum(self.min_angle, min_angles(old))).any():
            return "angle"
        return None

    def try_collapse(self, a, b, p):
        shared = self.v2f[a] & self.v2f[b]
        if len(shared) != 2:
            return self.refuse("edge")
        opposite = {u for f in shared for u in self.T[f]} - {a, b}
        if {u for f in self.v2f[a] for u in self.T[f]} & {u for f in self.v2f[b] for u in self.T[f]} != opposite | {a, b}:
            return self.refuse("link")
        if self.sdf is not None:
            p = self.project(p, float(np.linalg.norm(self.P[a] - self.P[b])))
        why = self.guard(a, b, shared, p)
        if why:
            return self.refuse(why)
        self.merge(a, b, shared, p)
        return True

    def merge(self, a, b, shared, p):
        for f in shared:
            self.alive[f] = False
            for v in self.T[f]:
                self.v2f[v].discard(f)
        for f in self.v2f[b]:
            self.T[f] = [a if v == b else v for v in self.T[f]]
            self.v2f[a].add(f)
        self.v2f[b] = set()
        self.nf -= 2
        self.P[a] = p
        self.Q[a] += self.Q[b]
        self.version[a] += 1
        self.version[b] += 1
        for w in self.fnb[b]:
            self.fnb[w].discard(b)
            self.fnb[w].add(a)
        self.fnb[a] = (self.fnb[a] | self.fnb[b]) - {a, b}
        self.fnb[b] = set()
        self.accepted += 1

    def run(self, goal, lowest):
        """Pop until nf <= goal; never make nf < lowest. True when the goal is met."""
        while self.heap and self.nf > goal:
            cost, a, b, va, vb, x, y, z = heapq.heappop(self.heap)
            if va != self.version[a] or vb != self.version[b] or not self.v2f[a] or not self.v2f[b]:
                continue
            if self.nf - 2 < lowest:
                return self.nf <= goal
            if self.try_collapse(a, b, np.array([x, y, z])):
                self.push(a, self.neighbours(a))
        return self.nf <= goal

    # -- end
    def polish(self, d):
        """2 Newton steps on every vertex that is not a corner, then back the moves that turn a face."""
        used = np.array([i for i in range(self.n) if self.v2f[i]])
        T = np.array([t for f, t in enumerate(self.T) if self.alive[f]])
        old, move = self.P.copy(), np.array([not self.is_corner(i) for i in range(self.n)])
        for _ in range(NEWTON):
            pts = (self.P[used][:, None, :] + self.h * OFFSETS[None]).reshape(-1, 3)
            v = d(pts).reshape(-1, 7)
            g = np.stack([v[:, 1] - v[:, 4], v[:, 2] - v[:, 5], v[:, 3] - v[:, 6]], 1) / (2 * self.h)
            gg = np.maximum(np.einsum("kd,kd->k", g, g), 1e-12)
            self.P[used] -= np.where(move[used, None], v[:, :1] * g / gg[:, None], 0.0)
        n0, _ = tri_normals(old, T)
        c = np.cross(self.P[T[:, 1]] - self.P[T[:, 0]], self.P[T[:, 2]] - self.P[T[:, 0]])
        turned = np.einsum("fd,fd->f", n0, c) < 0
        back = np.unique(T[turned])
        self.P[back] = old[back]
        return len(back)

    def result(self):
        T = np.array([t for f, t in enumerate(self.T) if self.alive[f]])
        used = np.unique(T)
        remap = np.full(self.n, -1)
        remap[used] = np.arange(len(used))
        return self.P[used], remap[T]


def reduce(verts, tris, target_faces, sdf=None, features_deg=35, min_angle=15, floor=0.9, polish=None, grad_h=None):
    """(verts, tris, report) with `target_faces` triangles at most (and at least floor x target_faces unless the guard
    stops it sooner). `sdf`: see the module doc, None = no projection; `features_deg` None / 0 = no feature quadrics;
    `polish`: the field of the final projection, default `sdf`; `grad_h`: central-difference step (default 1e-3 x size)."""
    t0 = time.perf_counter()
    R = Reducer(verts, tris, sdf, features_deg, min_angle, grad_h)
    f0, v0 = R.nf, int((np.bincount(np.asarray(tris).ravel(), minlength=R.n) > 0).sum())
    lowest = floor * target_faces
    R.rebuild()
    met, relaxed = R.run(target_faces, lowest), None
    for k in RELAX:
        if met:
            break
        relaxed = R.min_angle = min_angle * k
        R.rebuild()
        met = R.run(target_faces, lowest)
    flipped_back = R.polish(polish or sdf) if (polish or sdf) is not None else 0
    out_v, out_t = R.result()
    report = {"faces_in": f0, "verts_in": v0, "faces": len(out_t), "verts": len(out_v), "euler_in": euler(v0, f0),
              "euler": euler(len(out_v), len(out_t)), "accepted": R.accepted, "refused": dict(R.why),
              "features": R.n_features, "corners": sum(R.is_corner(v) for v in range(R.n) if R.v2f[v]),
              "target_met": bool(met), "relaxed_min_angle": relaxed, "polish_reverted": int(flipped_back),
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
