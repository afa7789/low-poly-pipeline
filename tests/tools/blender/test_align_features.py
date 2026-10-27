"""python3.14 -m unittest discover -s tests/tools/blender"""
import pathlib
import sys
import unittest
from types import SimpleNamespace

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import align_features as A  # noqa: E402
import deform_to_sheet as D  # noqa: E402
import silhouette as S  # noqa: E402
from test_deform_to_sheet import POS, TRI, panel  # noqa: E402

DIAG = np.array([np.sqrt(0.5), np.sqrt(0.5), 0.0])      # a camera at the +x, -y corner of the box
VIEW = D.View("diag", DIAG, np.array([0, 0, 1.0]), 1, panel(1.0), True)


class TestAlign(unittest.TestCase):
    def test_live_edges_are_the_box_corners(self):
        edge, f0, f1, normal = A.live_edges(POS, TRI)
        self.assertEqual(len(edge), 8)                                    # 4 corners x 2 levels, vertical
        self.assertTrue(np.allclose(POS[edge[:, 0], :2], POS[edge[:, 1], :2]))
        self.assertEqual(f0.shape, f1.shape)

    def test_seen_needs_both_faces_facing_the_camera(self):
        edge, f0, f1, normal = A.live_edges(POS, TRI)
        seen = A.seen_vertices(edge, f0, f1, normal, VIEW, len(POS))
        self.assertEqual(seen.sum(), 3)                                    # the corner nearest the camera
        self.assertTrue(np.allclose(POS[seen, :2], [0.5, -0.5]))
        front = D.View("front", np.array([1.0, 0, 0]), np.array([0, 0, 1.0]), 1, panel(1.0), True)
        self.assertFalse(A.seen_vertices(edge, f0, f1, normal, front, len(POS)).any())   # side walls edge-on

    def test_pull_toward_a_drawn_edge_is_capped(self):
        xy = D.frame(VIEW.uv(POS))[0](VIEW.uv(POS))
        drawn = np.zeros((S.CANVAS_H, S.CANVAS_W), bool)
        drawn[:, int(xy[(POS[:, 0] == 0.5) & (POS[:, 1] == -0.5)][:, 0].max() + 4)] = True          # a vertical line a few px to the right
        edge, f0, f1, normal = A.live_edges(POS, TRI)
        target = A.Target(VIEW, drawn, A.seen_vertices(edge, f0, f1, normal, VIEW, len(POS)))
        new = A.step_view(POS, TRI, D.laplacian(TRI, len(POS)), target, 2.0, POS[:, 2] < 0.04)
        move = (new - POS) @ DIAG
        self.assertGreater(move[target.feat & (POS[:, 2] > 0.04)].min(), 0.0)
        self.assertLessEqual(np.abs(new - POS).max(), A.LIMIT * 2.0 + 1e-9)
        self.assertTrue(np.all(new[:8, 2] == 0))                           # the sole stays on the ground

    def test_nothing_drawn_nothing_moves(self):
        panels = {"front": panel(1.0), "left": panel(1.0), "back": panel(1.0)}
        new, rep = A.align(POS, TRI, panels, {})
        self.assertTrue(np.array_equal(new, POS))
        self.assertEqual(rep["steps"], 0)

    def test_apply_needs_the_switches_and_a_hard_sheet(self):
        for ns in (dict(align=False, union_body=True, hard=__file__), dict(align=True, union_body=False, hard=__file__),
                   dict(align=True, union_body=True, hard=None), dict(align=True, union_body=True, hard="missing.jpg")):
            self.assertIsNone(A.apply("x.glb", SimpleNamespace(**ns)))


if __name__ == "__main__":
    unittest.main()
