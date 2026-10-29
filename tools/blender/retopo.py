#!/usr/bin/env python3
"""Guarded QEM retopology of a dense closed shell (PIPELINE 28.L10-3): numpy only, python3.14 and Blender's Python.

    verts, tris, report = reduce(verts, tris, target_faces, sdf=None, features_deg=None, min_angle=15, floor=0.9)

Garland & Heckbert 1997 edge collapse, with what a blind COLLAPSE lacks:
  * quality guard: a collapse is refused when a surviving triangle would get a smallest angle under `min_angle` (unless it was
    that bad already and does not get worse), or its normal would turn (dot < 0) or vanish, or the link condition fails
    (more shared neighbours than the two opposite vertices: the shell would pinch). When the quadric optimum fails, a's place,
    b's place and the midpoint are tried, and taken only if their quadric error is within SLACK x the optimum's;
  * `sdf(points (N, 3)) -> d (N,)` (negative inside): the new vertex of a collapse is Newton-projected onto the zero set,
    p <- p - d(p) grad d / |grad d|^2 (2 steps, central differences), before the guard looks at it; `polish` (default `sdf`)
    does the same over every non-corner vertex at the end and backs the moves that turn a face; `max_dev` refuses a collapse
    that leaves a triangle's centroid farther than that from the zero set (and farther than it was);
  * features (`features_deg`, OFF by default: the ablation of PIPELINE 28.L10-3 says they hurt on these bodies at 600 triangles):
    an edge whose two faces meet at >= features_deg on the INPUT mesh adds a plane through it, perpendicular to its faces, with
    weight FEATURE_W; RULES: a vertex with >= 3 feature edges is a corner and never moves, a feature vertex absorbs a plain one
    (keeps its place), two feature vertices join only along a feature edge (no chord across a corner);
  * target: stop at F <= B (B = target_faces; V* = (B + 4) / 2 on a closed genus-0 shell, F = 2V - 4) and never go under
    floor * B. If nothing collapsible is left above B the guard is relaxed in stages (min_angle x RELAX; the turn guard stays) and
    the report says so. The euler number F - 2V + 4 of the input is kept (a handle is neither made nor lost).
Not a heap: the collapses go in rounds. Each round costs every edge (vectorized: cost + best position), takes the edges that are
the cheapest of their 2-ring (an independent set: no two touch, so applying them together equals applying them one after the
other), projects and guards them all at once and applies the ones that pass; an edge that fails is banned until its
neighbourhood changes. A python heap with a few numpy calls per collapse measured 9.7 s on 34 k triangles (PIPELINE 28.L10-3).
The last round is cut to land inside [floor * B, B]. The input must be a welded, closed, manifold triangle shell.

`remesh` (PIPELINE 28.L10-4, Botsch & Kobbelt 2004): isotropic remeshing, the alternative to the QEM above: split edges over 4/3 L,
collapse the ones under 4/5 L (the same independent-set rounds, `Shorts`), flip toward valence 6, tangential relaxation, projection
on the SDF; `retopo(..., method=)` picks `reduce`, `remesh`, `remesh` + a short `reduce` ("hybrid") or `reduce` -> `remesh` guided
by its own edge lengths ("guided"). It buys fairness (equilateral triangles) and pays in deviation: a uniform L cannot follow the
facets (see METHOD).
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
REASONS = ("ok", "degenerate", "turned", "angle", "link", "deviation")


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
    def __init__(self, verts, tris, sdf, features_deg, min_angle, grad_h=None, max_dev=None):
        self.P = np.array(verts, float)
        self.n = len(self.P)
        self.T = np.asarray(tris, np.int64).copy()
        self.scale = float(np.ptp(self.P, axis=0).max())
        self.sdf, self.min_angle, self.max_dev = sdf, min_angle, max_dev
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
        for code, bad in ((5, self.too_far(old, new)),
                          (3, min_angles(new) < np.minimum(self.min_angle, min_angles(old))),
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

    def too_far(self, old, new):
        """Triangles whose centroid is farther than max_dev from the zero set and farther than the old one was."""
        if self.sdf is None or self.max_dev is None:
            return np.zeros(len(new), bool)
        far = np.abs(self.sdf(new.mean(1)))
        return (far > self.max_dev) & (far > np.abs(self.sdf(old.mean(1))))

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


def reduce(verts, tris, target_faces, sdf=None, features_deg=None, min_angle=15, floor=0.9, polish=None, grad_h=None, max_dev=None):
    """(verts, tris, report) with `target_faces` triangles at most (and at least floor x target_faces unless the guard
    stops it sooner). `sdf`: see the module doc, None = no projection; `features_deg` None / 0 = no feature quadrics;
    `polish`: the field of the final projection, default `sdf`; `grad_h`: central-difference step (default 1e-3 x size);
    `max_dev`: refuse a collapse that leaves a triangle's centroid farther than this from the zero set of `sdf`."""
    t0 = time.perf_counter()
    R = Reducer(verts, tris, sdf, features_deg, min_angle, grad_h, max_dev)
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


# ---------------------------------------------------------------- isotropic remeshing (L10-4)
METHOD = "qem"          # the default of retopo(): "qem" | "remesh" | "hybrid" | "guided". PIPELINE 28.L10-4 table: the remesh wins
                        # fairness (12 vs 24) but fails the sdf_dev / IoU ceilings on n00U, n017, hfoo (spider legs, boxy armour): stays "qem"
SPLIT_AT = 4 / 3        # Botsch & Kobbelt: split edges longer than 4/3 L, collapse the ones shorter than 4/5 L
COLLAPSE_AT = 4 / 5
FLIP_COS = 0.9          # a flip may not leave a new face turned more than ~25 degrees from the two it replaces
FLIP_ANGLE = 20.0       # ... nor with a smallest angle under this
SMOOTH = 0.6            # tangential relaxation step (share of the way to the neighbours' centroid)
SMOOTH_PASSES = 3       # relaxation + projection passes after each flip pass
AIM = 0.96              # remesh / guided aim at this x the target (the count lands within a few % of the aim), reduce closes the rest
HYBRID_OVER = 1.2       # hybrid: the remesh aims at this x the target, then `reduce` closes the budget


def edge_length_for(P, T, faces):
    """L of a mesh of `faces` equilateral triangles with the area of (P, T): sqrt(4 A / (sqrt(3) F))."""
    return float(np.sqrt(4 * tri_normals(P, T)[1].sum() / (np.sqrt(3) * faces)))


def best_of_faces(n_faces, fa, fb, prio):
    """Mask over the candidate edges (faces fa, fb): the ones that have the lowest `prio` on both their faces."""
    order = np.argsort(prio, kind="stable")
    rank = np.empty(len(prio), np.int64)
    rank[order] = np.arange(len(prio))
    best = np.full(n_faces, len(prio))
    np.minimum.at(best, fa, rank)
    np.minimum.at(best, fb, rank)
    return (best[fa] == rank) & (best[fb] == rank)


def manifold_edges(T, n):
    """(a, b, face0, face1) of the edges with exactly two faces, a < b."""
    keys, f0, f1, count = edge_faces(T, n)
    two = count == 2
    return keys[two] // n, keys[two] % n, f0[two], f1[two]


def forward(T, f, a, b):
    """True where face f runs a -> b (False: b -> a)."""
    t = T[f]
    return ((t == a[:, None]) & (np.roll(t, -1, 1) == b[:, None])).any(1)


def keys_of(pairs, n):
    return np.unique(np.minimum(pairs[:, 0], pairs[:, 1]) * n + np.maximum(pairs[:, 0], pairs[:, 1])) if len(pairs) else np.zeros(0, np.int64)


def guide_size(P, T, k=4):
    """size(points) from a guide mesh: the mean edge length at its vertices, inverse-distance weighted over the k nearest."""
    n = len(P)
    keys = edge_faces(T, n)[0]
    a, b = keys // n, keys % n
    ln = np.linalg.norm(P[b] - P[a], axis=1)
    mean = np.bincount(np.r_[a, b], np.r_[ln, ln], minlength=n) / np.maximum(np.bincount(np.r_[a, b], minlength=n), 1)

    def size(points):
        q = np.asarray(points, float).reshape(-1, 3)
        d2 = ((q[:, None, :] - P[None]) ** 2).sum(2)
        near = np.argpartition(d2, min(k, n - 1), axis=1)[:, :k]
        w = 1 / (np.take_along_axis(d2, near, 1) + 1e-12)
        return (w * mean[near]).sum(1) / w.sum(1)
    return size


def split_long(P, T, FE, sdf, h, size):
    """One pass: split (at the midpoint, projected) the edges longer than 4/3 x size(midpoint), at most one per face.
    (P, T, FE, count)."""
    n = len(P)
    a, b, f0, f1 = manifold_edges(T, n)
    ln = np.linalg.norm(P[b] - P[a], axis=1)
    need = ln / (SPLIT_AT * size((P[a] + P[b]) / 2))
    cand = np.flatnonzero(need > 1)
    if not len(cand):
        return P, T, FE, 0
    cand = cand[best_of_faces(len(T), f0[cand], f1[cand], -need[cand])]
    a, b, f0, f1, ln = a[cand], b[cand], f0[cand], f1[cand], ln[cand]
    m = (P[a] + P[b]) / 2
    if sdf is not None:
        m = project(sdf, m, h, ln)
    mid = n + np.arange(len(cand))
    fs, ends = np.r_[f0, f1], np.r_[np.stack([a, b], 1), np.stack([a, b], 1)]
    t = T[fs]
    at = ((t == ends[:, :1]) & (np.roll(t, -1, 1) == ends[:, 1:])) | ((t == ends[:, 1:]) & (np.roll(t, -1, 1) == ends[:, :1]))
    i = at.argmax(1)
    u, v, w = (t[np.arange(len(t)), (i + k) % 3] for k in range(3))
    mm = np.r_[mid, mid]
    keep = np.ones(len(T), bool)
    keep[fs] = False
    T2 = np.vstack([T[keep], np.stack([u, mm, w], 1), np.stack([mm, v, w], 1)])
    if len(FE):
        sk, order = a * n + b, np.argsort(a * n + b)
        ek = np.minimum(FE[:, 0], FE[:, 1]) * n + np.maximum(FE[:, 0], FE[:, 1])
        pos = np.minimum(np.searchsorted(sk[order], ek), len(sk) - 1)
        hit = sk[order][pos] == ek
        m_id = mid[order[pos[hit]]]
        FE = np.vstack([FE[~hit], np.stack([FE[hit, 0], m_id], 1), np.stack([m_id, FE[hit, 1]], 1)])
    return np.vstack([P, m]), T2, FE, len(cand)


def flip_pass(P, T, FE):
    """One pass of valence flips (toward 6): the edge a-b of faces (u, v, w) and (v, u, z) becomes w-z. (T, count)."""
    n = len(P)
    a, b, f0, f1 = manifold_edges(T, n)
    val = np.bincount(T.ravel(), minlength=n)
    fwd = forward(T, f0, a, b)
    u, v = np.where(fwd, a, b), np.where(fwd, b, a)
    w, z = T[f0].sum(1) - a - b, T[f1].sum(1) - a - b
    before = sum(np.abs(val[k] - 6) for k in (a, b, w, z))
    after = np.abs(val[a] - 7) + np.abs(val[b] - 7) + np.abs(val[w] - 5) + np.abs(val[z] - 5)
    keys = np.unique(np.minimum(a, b) * n + np.maximum(a, b))
    nk = np.minimum(w, z) * n + np.maximum(w, z)
    new1, new2 = np.stack([u, z, w], 1), np.stack([z, v, w], 1)
    nav = tri_normals(P, T[f0])[0] + tri_normals(P, T[f1])[0]
    nav /= np.maximum(np.linalg.norm(nav, axis=1), 1e-300)[:, None]
    ok = (after < before) & (val[a] > 3) & (val[b] > 3) & (w != z) & ~np.isin(nk, keys)
    if len(FE):
        fcnt = np.bincount(FE.ravel(), minlength=n)
        ok &= ~np.isin(a * n + b, keys_of(FE, n)) & ~((fcnt[w] > 0) & (fcnt[z] > 0))
    for t in (new1, new2):
        ok &= np.einsum("fd,fd->f", tri_normals(P, t)[0], nav) > FLIP_COS
        ok &= min_angles(P[t]) >= FLIP_ANGLE
    cand = np.flatnonzero(ok)
    cand = cand[best_of_faces(len(T), f0[cand], f1[cand], (before - after)[cand] * -1.0)]
    T = T.copy()
    T[f0[cand]], T[f1[cand]] = new1[cand], new2[cand]
    return T, len(cand)


def relax(P, T, FE, sdf, h, reach, step=SMOOTH, tol=None):
    """One tangential relaxation toward the neighbours' centroid (feature vertices: along their two feature neighbours,
    corners fixed), projected on the zero set; the moves that turn a face are undone."""
    n = len(P)
    a, b, _, _ = manifold_edges(T, n)
    src, dst = np.r_[a, b], np.r_[b, a]
    cnt = np.maximum(np.bincount(src, minlength=n), 1)
    cen = np.stack([np.bincount(src, P[dst, k], minlength=n) for k in range(3)], 1) / cnt[:, None]
    nrm, area = tri_normals(P, T)
    vn = np.zeros((n, 3))
    for c in range(3):
        np.add.at(vn, T[:, c], nrm * area[:, None])
    vn /= np.maximum(np.linalg.norm(vn, axis=1), 1e-300)[:, None]
    move = cen - P
    move -= np.einsum("kd,kd->k", move, vn)[:, None] * vn
    if len(FE):
        fcnt = np.bincount(FE.ravel(), minlength=n)
        fcen = np.stack([np.bincount(np.r_[FE[:, 0], FE[:, 1]], P[np.r_[FE[:, 1], FE[:, 0]], k], minlength=n) for k in range(3)], 1) / np.maximum(fcnt, 1)[:, None]
        move = np.where((fcnt == 2)[:, None], fcen - P, np.where((fcnt > 0)[:, None], 0.0, move))
    used = np.unique(T)
    Q = P.copy()
    Q[used] = P[used] + step * move[used]
    if sdf is not None:
        Q[used] = project(sdf, Q[used], h, np.full(len(used), reach))
    n0 = tri_normals(P, T)[0]
    c = np.cross(Q[T[:, 1]] - Q[T[:, 0]], Q[T[:, 2]] - Q[T[:, 0]])
    off = np.einsum("fd,fd->f", n0, c) <= 0
    if tol is not None and sdf is not None:
        old, new = np.abs(sdf(P[T].mean(1))), np.abs(sdf(Q[T].mean(1)))
        off |= (new > tol) & (new > old)
    bad = np.unique(T[off])
    Q[bad] = P[bad]
    return Q


class Shorts(Reducer):
    """Reducer whose cost is the edge length: collapses the edges under 4/5 x size(midpoint) (to the midpoint, projected, or
    the pinned end), never leaving a triangle with an edge over 4/3 x size(centroid) that was not already there."""

    def __init__(self, verts, tris, sdf, FE, size, min_angle, grad_h, max_dev):
        super().__init__(verts, tris, sdf, None, min_angle, grad_h, max_dev)
        self.FE, self.size = FE, size

    def evaluate(self, a, b, fcnt):
        never, stay_a, stay_b = self.pin(a, b, fcnt)
        pa, pb = self.P[a], self.P[b]
        ln = np.linalg.norm(pb - pa, axis=1)
        x = np.where(stay_a[:, None], pa, np.where(stay_b[:, None], pb, (pa + pb) / 2))
        return np.where(never | (ln >= COLLAPSE_AT * self.size((pa + pb) / 2)), np.inf, ln), x

    def too_far(self, old, new):
        def longest(p):
            return np.linalg.norm(p - np.roll(p, 1, 1), axis=2).max(1)
        over = longest(new) > SPLIT_AT * self.size(new.mean(1))
        return super().too_far(old, new) | (over & (longest(new) > longest(old)))


def collapse_short(P, T, FE, sdf, h, size, max_dev):
    """(P, T, FE) after collapsing the short edges; the vertices keep their ids (compact() drops the dead ones)."""
    n = len(P)
    R = Shorts(P, T, sdf, keys_of(FE, n), size, 15, h, max_dev)
    R.run(0, 0)
    return R.P, R.T, np.stack([R.FE // n, R.FE % n], 1) if len(R.FE) else FE[:0]


def compact(P, T, FE):
    used = np.unique(T)
    remap = np.full(len(P), -1)
    remap[used] = np.arange(len(used))
    return P[used], remap[T], remap[FE] if len(FE) else FE


def remesh(verts, tris, target_faces, sdf=None, iters=10, features=None, polish=None, grad_h=None, max_dev=None, guide=None):
    """(verts, tris, report): isotropic remeshing (Botsch & Kobbelt 2004) of a closed shell to ~`target_faces` triangles:
    per iteration split the edges over 4/3 L, collapse the ones under 4/5 L, flip toward valence 6, relax tangentially and
    project on the zero set of `sdf` (see the module doc; None = no projection). L starts at the equilateral edge of the target
    and follows the triangle count (L x sqrt(F / target)) so the count lands near the target. `guide` = (verts, tris) of a
    coarse mesh of the same shape (e.g. the `reduce` result): L is then a field, the guide's local edge length x a scale that
    follows the count, so the thin parts keep the small triangles the guide gave them. `features`: dihedral (degrees)
    of the INPUT edges that become feature lines (corners fixed, the rest slide only along the line). `polish`: exact field of
    the last projection; `max_dev`: as in reduce. The count is not guaranteed <= target: `reduce` closes it (METHOD "hybrid")."""
    t0 = time.perf_counter()
    P, T = np.array(verts, float), np.asarray(tris, np.int64).copy()
    h = grad_h or 1e-3 * float(np.ptp(P, axis=0).max())
    FE = np.zeros((0, 2), np.int64)
    if features:
        keys = feature_edges(P, T, features)[0]
        FE = np.stack([keys // len(P), keys % len(P)], 1)
    f0, e0 = len(T), euler(len(np.unique(T)), len(T))
    L0, area = edge_length_for(P, T, target_faces), tri_normals(P, T)[1].sum()
    base = guide_size(*guide) if guide is not None else (lambda p: np.full(len(p), L0))
    scale, log = 1.0, []
    for it in range(iters):
        size = lambda p, s=scale: s * base(p)  # noqa: E731
        for _ in range(4):
            P, T, FE, n_split = split_long(P, T, FE, sdf, h, size)
            if not n_split:
                break
        P, T, FE = collapse_short(P, T, FE, sdf, h, size, max_dev)
        P, T, FE = compact(P, T, FE)
        for _ in range(2):
            T = flip_pass(P, T, FE)[0]
        for _ in range(SMOOTH_PASSES):
            P = relax(P, T, FE, sdf, h, L0, tol=max_dev)
        if it < iters - 2:
            scale *= (len(T) / target_faces) ** 0.5
        log.append((len(T), round(scale, 4)))
    if (polish or sdf) is not None:
        P = relax(P, T, FE, polish or sdf, h, L0, step=0.0)
    P, T, _ = compact(P, T, FE)
    report = {"faces_in": f0, "faces": len(T), "verts": len(P), "euler_in": e0, "euler": euler(len(P), len(T)), "iters": log,
              "area": float(area), "seconds": round(time.perf_counter() - t0, 3)}
    return P, T, report


# ---------------------------------------------------------------- curvature-guided CVT (L11-6)
CVT_EPS = 0.1           # density rho = (CVT_EPS + kappa)^CVT_ALPHA, kappa = smoothed mean dihedral angle (rad) at the dense vertex
CVT_ALPHA = 1.0
CVT_ITERS = 30          # Lloyd iterations (stops sooner when no seed moves)
CVT_SMOOTH = 2          # rings of averaging over kappa (the openvdb mesh has a 45 degree staircase: the raw dihedral is noise)
CVT_SEED = 0
CVT_PLACE = "centroid"  # "centroid" (weighted cell centroid, projected) | "qef" (quadric minimiser of the cell's face planes, projected)
CVT_QEF_REG = 0.1       # qef: Tikhonov pull to the centroid, x the mean eigenvalue


def vertex_curvature(P, T, smooth=CVT_SMOOTH):
    """(kappa (n,), vertex area (n,), sorted unique edge keys): kappa = mean dihedral angle (radians) of the incident edges,
    averaged over `smooth` more rings. The dihedral is a 1-ring estimate that needs no cotan weights and is 0 on a plane."""
    n = len(P)
    keys, f0, f1, count = edge_faces(T, n)
    nrm, area = tri_normals(P, T)
    two = count == 2
    theta = np.zeros(len(keys))
    theta[two] = np.arccos(np.clip(np.einsum("kd,kd->k", nrm[f0[two]], nrm[f1[two]]), -1, 1))
    a, b = keys // n, keys % n
    deg = np.maximum(np.bincount(np.r_[a, b], minlength=n), 1)
    kappa = np.bincount(np.r_[a, b], np.r_[theta, theta], minlength=n) / deg
    for _ in range(smooth):
        kappa = (np.bincount(np.r_[a, b], np.r_[kappa[b], kappa[a]], minlength=n) + kappa) / (deg + 1)
    return kappa, np.bincount(T.ravel(), np.repeat(area / 3, 3), minlength=n), keys


def seed_counts(label, weight, total):
    """Seeds per connected component: 4 each (a tetrahedron is the smallest shell), the rest in proportion to the weight."""
    k = label.max() + 1
    size, w = np.bincount(label, minlength=k), np.bincount(label, weight, minlength=k)
    extra = max(total - 4 * k, 0) * w / w.sum()
    count = 4 + np.floor(extra).astype(int)
    count[np.argsort(extra - np.floor(extra))[::-1][:max(total - count.sum(), 0)]] += 1
    return np.minimum(count, size)


def initial_seeds(label, weight, count, rng):
    return np.concatenate([rng.choice(np.flatnonzero(label == c), count[c], replace=False, p=weight[label == c] / weight[label == c].sum())
                           for c in range(len(count))])


def components(src, dst, n):
    """Connected-component label per vertex of the graph with directed edges src -> dst (both directions present): min-label
    propagation with pointer jumping (a handful of rounds, no scipy: Blender's Python has none)."""
    lab = np.arange(n)
    while True:
        new = lab.copy()
        np.minimum.at(new, src, lab[dst])
        new = new[new]
        if (new == lab).all():
            return np.unique(lab, return_inverse=True)[1]
        lab = new


def voronoi(adj, length, seeds, n):
    """Cell (index into `seeds`) of every vertex: multi-source Dijkstra along the edges, as label-correcting rounds over the
    frontier (numpy, ~the cost of a few passes over the edges; Blender's Python has no scipy.sparse.csgraph). adj = adjacency(...),
    length = edge length per entry of adj[1]."""
    ptr, dst = adj
    dist, cell = np.full(n, np.inf), np.full(n, -1)
    dist[seeds], cell[seeds] = 0.0, np.arange(len(seeds))
    active = seeds
    while len(active):
        deg = ptr[active + 1] - ptr[active]
        owner = np.repeat(np.arange(len(active)), deg)
        idx = np.arange(deg.sum()) - np.repeat(np.cumsum(deg) - deg, deg) + ptr[active][owner]
        tgt, cand = dst[idx], dist[active][owner] + length[idx]
        better = cand < dist[tgt]
        if not better.any():
            break
        tgt, cand, who = tgt[better], cand[better], cell[active][owner][better]
        order = np.lexsort((cand, tgt))
        tgt, cand, who = tgt[order], cand[order], who[order]
        first = np.r_[True, tgt[1:] != tgt[:-1]]
        dist[tgt[first]], cell[tgt[first]] = cand[first], who[first]
        active = tgt[first]
    return cell


def lloyd(P, adj, length, weight, seeds, iters):
    """Discrete Lloyd relaxation: cells = `voronoi` (the geodesic Voronoi diagram of the seeds, approximated along the edges),
    seed <- the cell's vertex nearest to its weighted centroid. (seeds, cell label per vertex)."""
    n, N = len(P), len(seeds)
    for _ in range(iters):
        label = voronoi(adj, length, seeds, n)
        cw = np.maximum(np.bincount(label, weight, minlength=N), 1e-300)
        centre = np.stack([np.bincount(label, weight * P[:, k], minlength=N) for k in range(3)], 1) / cw[:, None]
        order = np.lexsort((np.linalg.norm(P - centre[label], axis=1), label))
        first = order[np.r_[True, label[order][1:] != label[order][:-1]]]
        moved = seeds.copy()
        moved[label[first]] = first
        if (moved == seeds).all():
            break
        seeds = moved
    return seeds, voronoi(adj, length, seeds, n)


def dual_faces(T, label, N):
    """Triangles of the cell adjacency: each dense triangle whose three vertices lie in three different cells (a Voronoi vertex)
    is one face on those cells, once, with the orientation of the dense triangle."""
    L = label[T]
    L = L[(L[:, 0] != L[:, 1]) & (L[:, 1] != L[:, 2]) & (L[:, 0] != L[:, 2])]
    key = np.sort(L, axis=1) @ np.array([N * N, N, 1])
    return L[np.unique(key, return_index=True)[1]]


def drop_nonmanifold(F, P):
    """F without the faces that overload an edge (> 2 faces): the smallest area first. (F, number dropped)."""
    dropped = 0
    while True:
        keys, _, _, count = edge_faces(F, len(P))
        bad = keys[count > 2]
        if not len(bad):
            return F, dropped
        a, b = F.ravel(), F[:, [1, 2, 0]].ravel()
        k = np.minimum(a, b) * len(P) + np.maximum(a, b)
        hit = np.unique(np.flatnonzero(np.isin(k, bad)) // 3)
        worst = hit[np.argmin(tri_normals(P, F[hit])[1])]
        F = np.delete(F, worst, axis=0)
        dropped += 1


def cell_positions(P, T, label, weight, N, place, sdf, h, reach):
    """One vertex per cell: the weighted centroid (or, place="qef", the minimiser of the cell's quadric damped toward it),
    Newton-projected on the zero set of `sdf`."""
    cw = np.maximum(np.bincount(label, weight, minlength=N), 1e-300)
    X = np.stack([np.bincount(label, weight * P[:, k], minlength=N) for k in range(3)], 1) / cw[:, None]
    if place == "qef":
        Qc = np.zeros((N, 4, 4))
        Qv = initial_quadrics(P, T, np.zeros(0, np.int64), None)
        for i, j in np.ndindex(4, 4):
            Qc[:, i, j] = np.bincount(label, Qv[:, i, j], minlength=N)
        A, b = Qc[:, :3, :3], Qc[:, :3, 3]
        mu = CVT_QEF_REG * np.einsum("kii->k", A) / 3 + 1e-30
        X = np.linalg.solve(A + mu[:, None, None] * np.eye(3), (mu[:, None] * X - b)[:, :, None])[:, :, 0]
    return project(sdf, X, h, np.full(N, reach)) if sdf is not None else X


def cvt(verts, tris, target_faces, sdf=None, polish=None, grad_h=None, max_dev=None, eps=CVT_EPS, alpha=CVT_ALPHA, iters=CVT_ITERS,
        smooth=CVT_SMOOTH, place=None, seed=CVT_SEED, **_):
    """(verts, tris, report): curvature-guided Voronoi / CVT retopology (Chatterjee, Soni, Bhowmick 2022; Valette & Chassery 2004,
    Valette, Chassery & Prost 2008) of a dense closed shell to ~`target_faces` triangles. N = (B + 4 - euler_in) / 2 seeds are drawn
    on the dense vertices with probability ~ area x (eps + kappa)^alpha (kappa: `vertex_curvature`), relaxed by `lloyd`
    (geodesic cells along the edges: unlike a kd-tree it never joins two legs that touch in space), each cell becomes one vertex
    (`cell_positions`, projected on `sdf`; `polish` the exact field of the last projection) and each dense triangle on three cells one
    face (`dual_faces`; an overloaded edge drops its smallest face, then the hole is left to the report: `dropped`). `max_dev` is
    only reported (`dev_over`): the dual has no per-operation guard like `reduce`. Faces = 2N - 4 + euler_in on a clean dual."""
    t0 = time.perf_counter()
    P, T = np.array(verts, float), np.asarray(tris, np.int64)
    n, e_in = len(P), euler(len(np.unique(T)), len(T))
    h = grad_h or 1e-3 * float(np.ptp(P, axis=0).max())
    kappa, area, keys = vertex_curvature(P, T, smooth)
    weight = np.maximum(area * (eps + kappa) ** alpha, 1e-300)
    a, b = keys // n, keys % n
    adj = adjacency(keys, n)
    length = np.linalg.norm(P[adj[1]] - P[np.repeat(np.arange(n), np.diff(adj[0]))], axis=1)
    comp = components(np.r_[a, b], np.r_[b, a], n)
    N = max(int((target_faces + 4 - e_in) // 2), 4)
    seeds = initial_seeds(comp, weight, seed_counts(comp, weight, N), np.random.default_rng(seed))
    seeds, label = lloyd(P, adj, length, weight, seeds, iters)
    N = len(seeds)
    X = cell_positions(P, T, label, weight, N, place or CVT_PLACE, sdf, h, float(np.ptp(P, axis=0).max()) * 0.05)
    F, dropped = drop_nonmanifold(dual_faces(T, label, N), X)
    if (polish or sdf) is not None:
        X = project(polish or sdf, X, h, np.full(N, float(np.ptp(P, axis=0).max()) * 0.02))
    used = np.unique(F)
    remap = np.full(N, -1)
    remap[used] = np.arange(len(used))
    out_v, out_t = X[used], remap[F]
    over = int((np.abs((polish or sdf)(out_v[out_t].mean(1))) > max_dev).sum()) if max_dev is not None and (polish or sdf) is not None else None
    return out_v, out_t, {"faces_in": len(T), "faces": len(out_t), "verts": len(out_v), "seeds": N, "euler_in": e_in,
                          "euler": euler(len(out_v), len(out_t)), "dropped": dropped, "dev_over": over, "target_met": len(out_t) <= target_faces,
                          "seconds": round(time.perf_counter() - t0, 3)}


def retopo(verts, tris, target_faces, sdf=None, method=None, features=None, **kw):
    """The retopology entry point; `method` (default METHOD): "qem" = reduce; "remesh" = remesh; "remesh" = remesh
    aimed at AIM x target; "hybrid" = remesh to HYBRID_OVER x target, then reduce to the target; "guided" = reduce, then remesh
    with that mesh as the size guide. Every method but "qem" ends with a short `reduce` when the count is above the target.
    kw: polish, grad_h, max_dev (see reduce)."""
    method = method or METHOD
    if method == "cvt":
        return cvt(verts, tris, target_faces, sdf, **kw)
    if method == "qem":
        return reduce(verts, tris, target_faces, sdf, features_deg=features, **kw)
    if method == "remesh":
        v, t, rep = remesh(verts, tris, int(AIM * target_faces), sdf, features=features, **kw)
    elif method == "hybrid":
        v, t, rep = remesh(verts, tris, int(HYBRID_OVER * target_faces), sdf, features=features, **kw)
    else:
        gv, gt, rep = reduce(verts, tris, int(AIM * target_faces), sdf, features_deg=features, **kw)
        v, t, rep = remesh(verts, tris, int(AIM * target_faces), sdf, features=features, guide=(gv, gt), **kw)
    v, t, rep2 = reduce(v, t, target_faces, sdf, **kw) if len(t) > target_faces else (v, t, {"seconds": 0.0})
    return v, t, {**rep2, "remesh": rep, "seconds": round(rep["seconds"] + rep2["seconds"], 3)}


def main():
    import argparse
    import json
    import pathlib
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("npz", help="verts + tris of a dense closed shell")
    ap.add_argument("target", type=int)
    ap.add_argument("--features", type=float, default=None, help="dihedral (degrees) that makes an edge a feature")
    ap.add_argument("--out", help="npz of the result")
    a = ap.parse_args()
    z = np.load(a.npz)
    v, t, rep = reduce(z["verts"], z["tris"], a.target, features_deg=a.features)
    if a.out:
        np.savez(pathlib.Path(a.out), verts=v, tris=t)
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
