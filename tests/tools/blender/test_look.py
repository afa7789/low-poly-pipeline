"""look.py (L12-9): the three look metrics, the planar snap, the ink of the sheet's lines. Pure numpy, no Blender."""
import pathlib
import sys
import unittest

import numpy as np
from scipy.spatial import Delaunay

TOOLS = pathlib.Path(__file__).resolve().parents[3] / "tools/blender"
sys.path.insert(0, str(TOOLS))

import look as L  # noqa: E402
import sdf_batch  # noqa: E402


def cube(n=4):
    """Unit cube centred on the origin, each face an n x n grid of quads (2 triangles each); welded vertices."""
    pts, tri, index = [], [], {}

    def vert(p):
        key = tuple(np.round(p, 9))
        if key not in index:
            index[key] = len(pts)
            pts.append(p)
        return index[key]

    for axis in range(3):
        for sign in (-0.5, 0.5):
            u, v = [a for a in range(3) if a != axis]
            for i in range(n):
                for j in range(n):
                    corner = []
                    for di, dj in ((0, 0), (1, 0), (1, 1), (0, 1)):
                        p = np.zeros(3)
                        p[axis], p[u], p[v] = sign, -0.5 + (i + di) / n, -0.5 + (j + dj) / n
                        corner.append(vert(p))
                    quad = [(0, 1, 2), (0, 2, 3)] if sign > 0 else [(0, 2, 1), (0, 3, 2)]
                    tri += [[corner[a] for a in t] for t in quad]
    return np.array(pts), np.array(tri)


def uv_sphere(rings=16, segs=32):
    pts = [[0, 0, 1]] + [[np.sin(t) * np.cos(p), np.sin(t) * np.sin(p), np.cos(t)]
                         for t in np.linspace(0, np.pi, rings + 1)[1:-1] for p in np.linspace(0, 2 * np.pi, segs, endpoint=False)] + [[0, 0, -1]]
    tri = [[0, 1 + k, 1 + (k + 1) % segs] for k in range(segs)]
    for r in range(rings - 2):
        for k in range(segs):
            a, b = 1 + r * segs + k, 1 + r * segs + (k + 1) % segs
            tri += [[a, a + segs, b], [b, a + segs, b + segs]]
    last = len(pts) - 1
    tri += [[last, last - segs + (k + 1) % segs, last - segs + k] for k in range(segs)]
    return np.array(pts, float), np.array(tri)


def plane_grid(points):
    return points, Delaunay(points[:, :2]).simplices


class Metrics(unittest.TestCase):
    def test_chamfer_of_a_line_on_itself_is_one_and_eight_px_away_is_zero(self):
        ink = np.zeros((256, 384), bool)
        ink[40:200, 100] = True
        near = np.roll(ink, 8, axis=1)
        self.assertEqual(L.chamfer_pr(ink, ink), (1.0, 1.0))
        self.assertEqual(L.chamfer_pr(near, ink), (0.0, 0.0))
        self.assertEqual(L.chamfer_pr(np.zeros_like(ink), ink), (0.0, 0.0))

    def test_planarity_cube_one_sphere_nearly_zero(self):
        self.assertEqual(L.planarity(*cube()), 1.0)
        self.assertLess(L.planarity(*uv_sphere()), 0.1)

    def test_wire_entropy_grid_below_random_triangulation(self):
        g = np.linspace(0, 1, 9)
        grid = np.array([[x, y, 0.0] for x in g for y in g])
        rng = np.random.default_rng(1)
        soup = np.c_[rng.random((81, 2)), np.zeros(81)]
        self.assertLess(L.wire_entropy(*plane_grid(grid))[0], L.wire_entropy(*plane_grid(soup))[0] - 0.2)


class Snap(unittest.TestCase):
    def test_noisy_cube_snaps_to_its_six_planes(self):
        pos, tri = cube()
        noisy = pos + np.random.default_rng(0).normal(0, 0.0015, pos.shape)
        found = L.regions(noisy, tri, None, L.SNAP_TOL * np.ptp(noisy[:, 2]))
        self.assertEqual(len(found), 6)
        new, planes = L.snap_regions(noisy, tri, found, 0.1)
        self.assertEqual(len(planes), 6)
        self.assertLess(np.abs(np.abs(new).max(1) - 0.5).max(), 0.003)      # every vertex on a face plane of the cube, to the noise
        for faces, point, normal in planes:                                 # ... and exactly on the planes it was snapped to
            self.assertLess(np.abs((new[np.unique(tri[faces])] - point) @ normal).max(), 1e-3)
        self.assertEqual(L.planarity(new, tri), 1.0)
        self.assertLess(L.planarity(noisy, tri), 1.0)

    def test_a_sharp_line_is_a_region_border(self):
        grid = np.array([[x, y, 0.0] for x in np.linspace(0, 1, 7) for y in np.linspace(0, 1, 7)])
        pos, tri = plane_grid(grid)
        self.assertEqual(len(L.regions(pos, tri)), 1)
        uniq, _ = L.edge_table(tri)
        line = np.where((pos[uniq[:, 0], 0] == 0.5) & (pos[uniq[:, 1], 0] == 0.5))[0]
        self.assertEqual(len(L.regions(pos, tri, line)), 2)

    def test_guard_keeps_only_the_regions_it_accepts(self):
        pos, tri = cube()
        noisy = pos + np.random.default_rng(0).normal(0, 0.0015, pos.shape)
        found = L.regions(noisy, tri, None, 0.01)
        best, kept = L.guarded(noisy, tri, found, 0.1, lambda c: kept_ok(c, noisy))
        self.assertEqual(kept, len(found))
        best, kept = L.guarded(noisy, tri, found, 0.1, lambda c: False)
        self.assertEqual((kept, bool((best == noisy).all())), (0, True))


def kept_ok(candidate, original):
    return bool(np.abs(candidate - original).max() < 0.1)


class Ink(unittest.TestCase):
    def test_a_segment_along_the_ink_is_marked_and_a_crossing_one_is_not(self):
        ink = np.zeros((256, 384), bool)
        ink[40:200, 100] = True
        a = np.array([[100.5, 60.0], [100.5, 60.0], [60.0, 100.5]])
        b = np.array([[100.5, 90.0], [130.5, 60.0], [140.0, 100.5]])
        self.assertEqual(L.along_ink(a, b, ink).tolist(), [True, False, False])

    def test_ink_faces_moves_the_marked_edge_to_the_cells_first_column(self):
        width = 64
        span = (L.SF.TONE_W - 2 * L.SF.INK_EDGE_PX) / width
        uv = np.array([[0.20, 0.5], [0.30, 0.4], [0.20 + span, 0.6]], np.float32)
        tri = np.array([[0, 1, 2]])
        self.assertEqual(L.ink_faces(uv, tri, np.array([0]), width), 1)
        self.assertEqual(uv[:, 0].tolist(), [np.float32(0.2), np.float32(0.2), np.float32(0.2 + span)])
        flat = uv.copy()
        self.assertEqual(L.ink_faces(flat, tri, np.array([-1]), width), 0)        # no marked edge: untouched

    def test_a_decal_face_is_left_alone(self):
        uv = np.array([[0.2, 0.5], [0.3, 0.4], [0.35, 0.6]], np.float32)
        before = uv.copy()
        self.assertEqual(L.ink_faces(uv, np.array([[0, 1, 2]]), np.array([0]), 64), 0)
        self.assertTrue((uv == before).all())


class Untextured(unittest.TestCase):
    def test_bake_ink_on_a_glb_without_uv_is_a_noop(self):
        import json
        import tempfile
        doc = {"meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}]}
        text = json.dumps(doc).encode()
        text += b" " * (-len(text) % 4)
        data = b"glTF" + (2).to_bytes(4, "little") + (28 + len(text)).to_bytes(4, "little") + len(text).to_bytes(4, "little") + b"JSON" + text
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "clay.glb"
            path.write_bytes(data)
            self.assertEqual(L.bake_ink(path, None), {"marked": 0, "inked": 0})
            self.assertEqual(path.read_bytes(), data)


class Report(unittest.TestCase):
    def test_batch_cell_and_line(self):
        look = {"planarity": 0.5, "wire_entropy": 0.9, "edges_per_ktri": 1500.0, "crease_chamfer": {"front": [0.6, 0.4]}}
        self.assertIn("plan 0.50", sdf_batch.look_cell(look))
        self.assertEqual(sdf_batch.look_cell(None), "–")
        text = L.line({"look_before": look, "look_after": look})
        self.assertIn("planarity 0.5 -> 0.5", text)
        self.assertIn("front 0.60/0.40", text)


if __name__ == "__main__":
    unittest.main()
