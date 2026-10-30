"""python3 -m unittest discover -s tests/tools/blender  (no network, no model: the network is mocked)"""
import pathlib
import sys
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import depth_map as D  # noqa: E402
import parts_fit as PF  # noqa: E402


class Pure(unittest.TestCase):
    def test_calibrate_rank_shift(self):
        a, b, r = D.calibrate([0.2, 0.4, 0.6, 0.8], [-0.4, -0.2, 0.0, 0.2])
        self.assertAlmostEqual(a, 1.0)
        self.assertAlmostEqual(b, -0.6)
        self.assertAlmostEqual(r, 1.0)
        self.assertEqual(D.calibrate([0.5, 0.6], [0, 1])[2], 0.0, "too few parts: no trust")
        self.assertEqual(D.rank_order({0: 0.9, 1: 0.5, 2: 0.2}, 0.5), {0: 3, 1: 0, 2: -2})
        moved = D.shifted(["a", "box", [1, 1, 1], [0, 1, 2], "m", {"from": [0, 0, 0], "to": [0, 1, 1]}], 0.5)
        self.assertEqual((moved[3], moved[5]["from"], moved[5]["to"]), ([0, 1, 2.5], [0, 0, 0.5], [0, 1, 1.5]))


class Landmarks(unittest.TestCase):
    def test_calibration_reads_the_disparity_at_each_landmark_and_the_pearson_r(self):
        """four landmarks (joints both panels show) whose z rises with the disparity of the front panel: r = 1, a = 1"""
        import depth_rule
        fig = np.ones((768, 768), bool)
        disp = np.zeros((768, 768), np.float32)
        frames = mock.Mock()
        frames.panels = {"front": fig}
        frames.px = lambda view, u, v: (u * 100, v * 100)
        marks = [{"name": f"m{k}", "xyz": [0, 0, 0.1 * k], "gap": 0.0, "front_uv": (k + 1, k + 1)} for k in range(5)]
        marks.append({"name": "face", "xyz": [0, 0, 9], "gap": 0.0, "front_uv": (1, 1), "face": [0, 1]})      # a surface mark is not a solid's centre
        marks.append({"name": "gap", "xyz": [0, 0, 9], "gap": 0.2, "front_uv": (1, 1)})                         # its two views disagree: out
        for k in range(5):
            disp[(k + 1) * 100 - 2:(k + 1) * 100 + 3, (k + 1) * 100 - 2:(k + 1) * 100 + 3] = 0.1 * k
        with mock.patch.object(depth_rule, "frames_for", return_value=frames), mock.patch.object(depth_rule, "landmarks", return_value=marks):
            got = D.landmark_calibration("sheet.jpg", {}, disp)
        self.assertEqual((got["n"], got["r"]), (5, 1.0))
        self.assertAlmostEqual(got["a"], 1.0)


class DepthInit(unittest.TestCase):
    def setUp(self):
        self.doc = {"H": 2.0, "parts": [
            {"name": f"p{k}", "bone": "spine", "box2d": {"front": [0, 0, 1, 1]}, "box3d": [[0, 0, z], [1, 1, z]],
             "depth_order": 0} for k, z in enumerate((-1.0, -0.5, 0.0, 0.5))]}
        self.pf = PF.PartTerms.__new__(PF.PartTerms)
        self.pf.assoc = [0, 1, 2, 3, 2]
        full = np.ones((8, 8), bool)
        self.pf.masks = {(i, "front"): full for i in range(5)} | {(i, "left"): full for i in range(4)}
        self.pf.pairs = []
        self.parts = [["a", "box", [1, 1, 1], [0, 0, 0], "m", {}] for _ in range(5)]
        self.centres = [(0, 0, 0)] * 5

    def test_moves_only_the_parts_the_left_does_not_show(self):
        """disparity tracks z on the four parts with a left mask (r = 1): the fifth, with none, gets z from the line"""
        with mock.patch.object(D, "part_disparity", return_value={0: 0.1, 1: 0.3, 2: 0.5, 3: 0.7, 4: 0.7}):
            parts, report = D.depth_init(self.parts, self.pf, self.doc, {}, 2.0, self.centres)
        self.assertAlmostEqual(report["r_front_vs_left_z"], 1.0)
        self.assertEqual(report["moved"], {4: 0.2}, "z = 0.5 on the line, clipped to INIT_MAX x height")
        self.assertAlmostEqual(parts[4][3][2], 0.2)
        self.assertEqual(parts[0][3][2], 0, "a part with a left mask stays")

    def test_the_landmark_line_moves_a_part_only_when_r_is_at_least_the_trust_floor_and_positive(self):
        """L12-8: the line and its r come from the triangulated landmarks; r < .7 (L5-4b measured .2 to .4) or negative (the sheet's z points the other way) moves nothing"""
        disp = {0: 0.1, 1: 0.3, 2: 0.5, 3: 0.7, 4: 0.7}
        for r, moved in ((0.95, {4: 0.1}), (0.69, {}), (-0.95, {})):
            with self.subTest(r=r), mock.patch.object(D, "part_disparity", return_value=disp):
                _, report = D.depth_init(self.parts, self.pf, self.doc, {}, 2.0, self.centres, {"a": 1.0, "b": -0.6, "r": r, "n": 9})
            self.assertEqual((report["moved"], report["landmarks"]), (moved, 9))

    def test_order_from_depth_when_the_doc_has_none(self):
        with mock.patch.object(D, "part_disparity", return_value={0: 0.1, 1: 0.3, 2: 0.5, 3: 0.9}):
            _, report = D.depth_init(self.parts, self.pf, self.doc, {}, 2.0, self.centres)
        self.assertEqual(report["pairs_from_depth"], len(self.pf.pairs))
        self.assertIn((3, 0), self.pf.pairs)
        self.assertNotIn((0, 3), self.pf.pairs)


if __name__ == "__main__":
    unittest.main()
