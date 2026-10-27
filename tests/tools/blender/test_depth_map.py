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

    def test_order_from_depth_when_the_doc_has_none(self):
        with mock.patch.object(D, "part_disparity", return_value={0: 0.1, 1: 0.3, 2: 0.5, 3: 0.9}):
            _, report = D.depth_init(self.parts, self.pf, self.doc, {}, 2.0, self.centres)
        self.assertEqual(report["pairs_from_depth"], len(self.pf.pairs))
        self.assertIn((3, 0), self.pf.pairs)
        self.assertNotIn((0, 3), self.pf.pairs)


if __name__ == "__main__":
    unittest.main()
