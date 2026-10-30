"""python3 -m unittest discover -s tests/tools/blender"""
import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import preflight as PF  # noqa: E402
import rig_families as RF  # noqa: E402
import rig_remap as RM  # noqa: E402


class Carry(unittest.TestCase):
    def test_same_fraction_along_the_bone_and_same_offset_across(self):
        old, new = ((0, 0, 0), (2, 0, 0)), ((0, 0, 0), (0, 4, 0))
        self.assertEqual(RM.carry((1, 0.5, 0), old, new), [0.0, 2.5, 0.0])
        self.assertEqual(RM.carry((2, 0, 0), old, new), [0.0, 4.0, 0.0])


class Remap(unittest.TestCase):
    M = {"body_r": 0.3, "body_len": 0.8, "body_under": 0.25, "knee_h": 0.45, "knee_r": 0.6, "foot_r": 0.45}

    def test_leg_parts_reach_the_scaled_feet_and_the_rest_stays(self):
        fixed = list(RF.FAMILIES["spider"])
        try:
            foot = [c for n, _, _, c in fixed if n == "leg1.lower"][0]
            body = ["body", "prism", [0.3, 0.3, 0.5], [0, 0.5, 0], "iron", {"from": [0, 0.5, 0], "to": [0, 0.5, 0.4]}]
            leg = ["leg1.lower", "prism", [0.04, 0.02, 0.5], [0, 0, 0], "iron",
                   {"from": [c * 0.5 for c in foot], "to": list(foot)}]
            doc = {"rig": "spider", "parts": [body, leg]}
            out = RM.remap(doc, self.M)
            self.assertEqual(out["parts"][0], body)
            self.assertEqual(out["rig_measure"], self.M)
            to, top = out["parts"][1][5]["to"], max(PF.bbox(q)[1][1] for q in doc["parts"])
            self.assertAlmostEqual(math.hypot(to[0], to[2]), 0.45 * top, places=4)   # feet at foot_r of the spec's height
            self.assertNotEqual(out["parts"][1][5]["to"], list(foot))
            self.assertEqual(doc["parts"][1][5]["to"], list(foot))      # the input is not touched
        finally:
            RF.FAMILIES["spider"] = fixed
