"""python3.14 -m unittest tests.tools.blender.test_retopo   (SLOW=1 adds n005: 96^3 field -> surface nets -> 600 triangles)"""
import json
import os
import pathlib
import sys
import time
import unittest

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import mesh_lint as ML  # noqa: E402
import retopo as R  # noqa: E402
import retopo_mc as MC  # noqa: E402
import rig_families as RF  # noqa: E402
import sdf_body as S  # noqa: E402

RUNS = ROOT / "artifacts/model-sheets/runs/draft"


def cube(n=5):
    """The unit cube, n x n cells per face, outward triangles: (verts, tris)."""
    g = np.linspace(0, 1, n + 1)
    verts, index, tris = [], {}, []

    def vid(p):
        key = tuple(np.round(p, 9))
        if key not in index:
            index[key] = len(verts)
            verts.append(p)
        return index[key]
    for axis in range(3):
        for side in (0, 1):
            u, w = [a for a in range(3) if a != axis]
            for i in range(n):
                for j in range(n):
                    quad = []
                    for a, b in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)):
                        p = np.zeros(3)
                        p[axis], p[u], p[w] = side, g[a], g[b]
                        quad.append(vid(p))
                    q = quad if (side == 1) == (axis != 1) else quad[::-1]
                    tris += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]]
    return np.array(verts), np.array(tris)


def sphere(level=4):
    """Subdivided octahedron projected on the unit sphere: (verts, tris)."""
    v = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], float)
    t = np.array([[0, 2, 4], [2, 1, 4], [1, 3, 4], [3, 0, 4], [2, 0, 5], [1, 2, 5], [3, 1, 5], [0, 3, 5]])
    for _ in range(level):
        mid, verts, tris = {}, list(v), []

        def m(a, b):
            k = (min(a, b), max(a, b))
            if k not in mid:
                mid[k] = len(verts)
                p = verts[a] + verts[b]
                verts.append(p / np.linalg.norm(p))
            return mid[k]
        for a, b, c in t:
            ab, bc, ca = m(a, b), m(b, c), m(c, a)
            tris += [[a, ab, ca], [ab, b, bc], [ca, bc, c], [ab, bc, ca]]
        v, t = np.array(verts), np.array(tris)
    return v, t


def sphere_sdf(points):
    return np.linalg.norm(np.asarray(points).reshape(-1, 3), axis=1) - 1.0


class Reduce(unittest.TestCase):
    def test_subdivided_cube_is_12_triangles_with_its_edges_alive(self):
        v, t = cube()
        self.assertEqual(len(t), 300)
        out_v, out_t, rep = R.reduce(v, t, 12, features_deg=35, floor=1.0)
        self.assertEqual(len(out_t), 12)
        self.assertEqual(rep["euler"], 0)
        self.assertEqual(sorted(map(tuple, np.round(out_v).astype(int))), sorted(map(tuple, np.ndindex(2, 2, 2))))
        self.assertTrue(np.allclose(out_v, np.round(out_v), atol=1e-6))          # every vertex sits on a corner
        self.assertEqual(ML.topology(out_v, out_t)[:2], (0, 0))

    def test_dense_sphere_reaches_the_target_without_slivers(self):
        v, t = sphere()
        self.assertEqual(len(t), 2048)
        out_v, out_t, rep = R.reduce(v, t, 200, features_deg=None)
        self.assertTrue(rep["target_met"])
        self.assertTrue(180 <= len(out_t) <= 200)
        self.assertEqual(rep["euler"], 0)
        self.assertEqual(ML.topology(out_v, out_t), (0, 0, 1))
        self.assertEqual(float((ML.angles_min(out_v[out_t]) < ML.SLIVER_DEG).sum()), 0)

    def test_guard_refuses_the_collapse_that_turns_a_normal(self):
        v, t = sphere(0)                     # the octahedron
        red = R.Reducer(v, t, None, None, 15)
        a, b = np.array([4]), np.array([0])
        self.assertEqual(int(red.guard(a, b, np.array([[0.5, 0, 0.5]]))[0]), 0)       # towards the middle: fine
        self.assertEqual(int(red.guard(a, b, np.array([[0, 0, -3.0]]))[0]), 2)         # through the shell: turned

    def test_guard_refuses_a_sliver(self):
        v, t = sphere(2)
        red = R.Reducer(v, t, None, None, 15)
        a = int(t[0][0])
        b = int(next(w for w in t[0] if w != a))
        # all of a's 1-ring squeezed onto b's side: a new triangle of ~0 degrees
        x = (v[a] + 40 * (v[b] - v[a]))[None]
        self.assertGreater(int(red.guard(np.array([a]), np.array([b]), x)[0]), 0)

    def test_projection_brings_the_points_to_the_zero_set(self):
        p = np.array([[1.3, 0.1, 0.0], [0.0, 0.7, 0.2], [0.5, 0.5, 0.9]])
        q = R.project(sphere_sdf, p, 1e-3, np.full(3, 1.0))
        self.assertLess(np.abs(sphere_sdf(q)).max(), np.abs(sphere_sdf(p)).max() * 0.02)

    def test_projection_in_the_loop_keeps_the_sphere_round(self):
        v, t = sphere()
        v = v * 1.0
        bumpy = v * (1 + 0.02 * np.sin(40 * v[:, :1]))      # a field to project back from
        flat = R.reduce(bumpy, t, 150, features_deg=None)[0]
        proj = R.reduce(bumpy, t, 150, sdf=sphere_sdf, features_deg=None, grad_h=1e-3)[0]
        self.assertLess(np.abs(sphere_sdf(proj)).mean(), np.abs(sphere_sdf(flat)).mean())

    def test_deviation_guard_keeps_the_triangles_near_the_surface(self):
        v, t = sphere()
        out_v, out_t, _ = R.reduce(v, t, 100, sdf=sphere_sdf, features_deg=None, grad_h=1e-3, max_dev=0.03, floor=0.5)
        centroids = out_v[out_t].mean(1)
        self.assertLessEqual(np.abs(sphere_sdf(centroids)).max(), 0.03 + 1e-6)

    def test_grid_sdf_matches_the_field_between_nodes(self):
        x = np.linspace(-1.5, 1.5, 61)
        grid = np.linalg.norm(np.stack(np.meshgrid(x, x, x, indexing="ij"), -1), axis=-1) - 1.0
        d = R.grid_sdf(grid, np.full(3, -1.5), x[1] - x[0])
        pts = np.random.default_rng(0).uniform(-1.2, 1.2, (200, 3))
        self.assertLess(np.abs(d(pts) - sphere_sdf(pts)).max(), 0.002)


class Remesh(unittest.TestCase):
    def test_dense_sphere_is_fair_closed_and_without_slivers(self):
        v, t = sphere(5)
        out_v, out_t, rep = R.remesh(v, t, 300, sdf=sphere_sdf, grad_h=1e-3)
        self.assertEqual(rep["euler"], 0)
        self.assertEqual(ML.topology(out_v, out_t), (0, 0, 1))
        self.assertTrue(270 <= len(out_t) <= 330)
        p = out_v[out_t]
        self.assertLess(float(np.abs(ML.angles(p) - 60).mean()), 15)
        self.assertEqual(float((ML.angles_min(p) < ML.SLIVER_DEG).sum()), 0)

    def test_cube_corners_survive_as_feature_vertices(self):
        v, t = cube(8)
        max_dev = 0.02
        out_v, out_t, rep = R.remesh(v, t, 120, features=35, max_dev=max_dev)
        self.assertEqual(rep["euler"], 0)
        for corner in np.ndindex(2, 2, 2):
            self.assertLessEqual(np.linalg.norm(out_v - np.array(corner), axis=1).min(), max_dev)

    def test_projection_brings_the_remeshed_vertices_onto_the_zero_set(self):
        v, t = sphere(4)
        bumpy = v * (1 + 0.05 * np.sin(30 * v[:, :1]))
        flat = R.remesh(bumpy, t, 150, grad_h=1e-3)[0]
        proj = R.remesh(bumpy, t, 150, sdf=sphere_sdf, grad_h=1e-3)[0]
        self.assertLess(np.abs(sphere_sdf(proj)).max(), 1e-6)
        self.assertLess(np.abs(sphere_sdf(proj)).mean(), np.abs(sphere_sdf(flat)).mean())

    def test_retopo_entry_point_closes_the_budget_for_every_method(self):
        v, t = sphere(4)
        for method in ("qem", "remesh", "hybrid", "guided"):
            out_v, out_t, _ = R.retopo(v, t, 200, sdf=sphere_sdf, method=method, grad_h=1e-3)
            self.assertLessEqual(len(out_t), 200, method)
            self.assertEqual(R.euler(len(out_v), len(out_t)), 0, method)


class SurfaceNets(unittest.TestCase):
    def test_sphere_grid_gives_a_closed_manifold_on_the_zero_set(self):
        x = np.linspace(-1.5, 1.5, 41)
        grid = np.linalg.norm(np.stack(np.meshgrid(x, x, x, indexing="ij"), -1), axis=-1) - 1.0
        v, t = MC.surface_nets(grid, np.full(3, -1.5), x[1] - x[0])
        self.assertEqual(ML.topology(v, t), (0, 0, 1))
        self.assertEqual(R.euler(len(v), len(t)), 0)
        self.assertLess(np.abs(sphere_sdf(v)).max(), 0.05)
        vol = np.einsum("fd,fd->f", v[t[:, 0]], np.cross(v[t[:, 1]], v[t[:, 2]])).sum() / 6
        self.assertAlmostEqual(vol, 4 / 3 * np.pi, delta=0.15)


@unittest.skipUnless(os.environ.get("SLOW") and RUNS.exists(), "SLOW=1: n005 96^3 -> 600 triangles, ~3 s")
class Unit(unittest.TestCase):
    def test_n005_600_triangles(self):
        run = RUNS / "n005/v12-r1"
        doc = json.loads((run / "spec.json").read_text())
        saved = dict(RF.FAMILIES)
        try:
            RF.scale_rig(doc["rig"], doc.get("rig_measure"))
            f = S.field([tuple(r) for r in doc["parts"]], json.loads((run / "fit/cuts.json").read_text()),
                        (doc["rig"], doc.get("bones") or ()), grid=96)
        finally:
            RF.FAMILIES.clear()
            RF.FAMILIES.update(saved)
        v, t = MC.surface_nets(f.grid, f.origin, f.voxel)
        self.assertGreater(len(t), 20000)
        H = float(max(p["hi"][2] for p in f.parts) - min(p["lo"][2] for p in f.parts))
        t0 = time.perf_counter()
        out_v, out_t, rep = R.reduce(v, t, 600, sdf=R.grid_sdf(f.grid, f.origin, f.voxel), features_deg=None,
                                     polish=f.d, grad_h=0.5 * f.voxel, max_dev=0.02 * H)
        self.assertLessEqual(time.perf_counter() - t0, 3.0)
        self.assertTrue(540 <= len(out_t) <= 600)
        self.assertEqual(rep["euler"], rep["euler_in"])          # the naive nets have 4 non-manifold edges: no handle is made or lost
        self.assertLess(float((ML.angles_min(out_v[out_t]) < ML.SLIVER_DEG).mean()), 0.05)
        pts = np.vstack([out_v, out_v[out_t].mean(1)])
        self.assertLessEqual(float(np.percentile(np.abs(f.d(pts)), 95)), H / 64)
        self.assertLessEqual(float(np.abs(f.d(pts)).max()), H / 32)
        boundary, nonmanifold, components = ML.topology(out_v, out_t)
        self.assertEqual((boundary, components), (0, 1))
        self.assertLessEqual(nonmanifold, ML.topology(v, t)[1])


if __name__ == "__main__":
    unittest.main()
