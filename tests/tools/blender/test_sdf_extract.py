"""python3.14 -m unittest tests.tools.blender.test_sdf_extract"""
import pathlib
import sys
import unittest

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import sdf_body as S


class Pure(unittest.TestCase):
    def test_index_to_world(self):
        w = S.index_to_world([[0, 0, 0], [2, 4, 6.5]], (1.0, -2.0, 0.5), 0.25)
        np.testing.assert_allclose(w, [[1.0, -2.0, 0.5], [1.5, -1.0, 2.125]])

    def test_quads_to_tris_counts_and_shorter_diagonal(self):
        pts = np.array([[0, 0, 0], [4, 0, 0], [4, 1, 0], [0, 1, 0]], float)      # a trapezoid: 1-3 is the short diagonal
        pts[3] = [3, 1, 0]
        t = S.quads_to_tris(pts, [[0, 1, 2]], [[0, 1, 2, 3]])
        self.assertEqual(t.shape, (3, 3))
        self.assertEqual({tuple(sorted(x)) for x in t[1:]}, {(1, 2, 3), (0, 1, 3)})   # cut along 1-3
        area = lambda x: np.cross(pts[x[1]] - pts[x[0]], pts[x[2]] - pts[x[0]])[2] / 2
        self.assertTrue(all(area(x) > 0 for x in t[1:]))          # winding kept
        self.assertAlmostEqual(sum(area(x) for x in t[1:]), 2.5)

    def test_no_quads(self):
        self.assertEqual(S.quads_to_tris(np.zeros((3, 3)), [[0, 1, 2]], np.zeros((0, 4))).shape, (1, 3))


if __name__ == "__main__":
    unittest.main()
