"""python3 -m unittest tests.tools.blender.test_dsl_rules

L12-6: the DSL's prose rules (hood, prop axis, spider legs) are preflight rules with a repair in code. Fixtures are a few parts.
No Blender, no model."""
import copy
import pathlib
import sys
import unittest
from typing import ClassVar
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import dsl_rules as D
import preflight as PF


def rules(parts, doc, sheet=None):
    got, na = D.checks(parts, doc, sheet)
    return {r: ok for r, ok, _ in got}, na


def hooded(depth=0.8, face=None):
    parts = [["pelvis", "box", [0.6, 1.0, 0.4], [0, 0.5, 0], "m", {}],
             ["head", "frustum", [0.6, 0.6, depth], [0, 2.3, 0.2], "m", {"top": [1, 1], "shift": [0, 0], "hood": True, "decal": "sheet"}]]
    if face:
        parts.append(["head", "frustum", [0.3, 0.3, 0.05], [0, 2.3, face], "m", {"top": [1, 1], "shift": [0, 0], "decal": "sheet"}])
    return parts


class Hood(unittest.TestCase):
    def test_a_hood_without_a_face_part_fails_and_the_repair_adds_one(self):
        parts = hooded()
        self.assertFalse(rules(parts, {})[0]["hood_recess"])
        self.assertEqual(D.repair(copy.deepcopy(parts), {})[1], [], "hood repair is opt-in (all)")
        parts, log = D.repair(parts, {}, opt_in=True)
        self.assertTrue(rules(parts, {})[0]["hood_recess"])
        self.assertEqual([r for r, *_ in log], ["hood_recess"])
        self.assertEqual(sum("decal" in p[5] for p in parts), 1, "the decal moved to the face, one pair of eyes")

    def test_a_face_at_the_mouth_is_moved_back_and_a_shallow_hood_is_deepened(self):
        parts = hooded(depth=0.3, face=0.55)
        ok, _ = rules(parts, {})
        self.assertFalse(ok["hood_recess"])
        parts, log = D.repair(parts, {}, opt_in=True)
        self.assertTrue(rules(parts, {})[0]["hood_recess"])
        self.assertEqual(len(log), 2)

    def test_a_unit_without_a_hood_is_not_applicable(self):
        parts = [["pelvis", "box", [0.6, 1.0, 0.4], [0, 0.5, 0], "m", {}], ["head", "box", [0.3, 0.3, 0.3], [0, 1.2, 0], "m", {}]]
        ok, na = rules(parts, {})
        self.assertNotIn("hood_recess", ok)
        self.assertIn("no hood", na["hood_recess"])
        self.assertEqual(D.repair(parts, {})[1], [])


def spider(legs):
    """Parts of a spider with one straight piece per leg: `legs` = [(hip, foot)]."""
    parts = [["body", "frustum", [0.4, 0.2, 0.5], [0, 0.4, 0], "m", {"top": [1, 1], "shift": [0, 0]}]]
    for n, (a, b) in enumerate(legs, 1):
        parts.append([f"leg{n}.upper", "prism", [0.04, 0.03, 0.5], [0, 0, 0], "m", {"sides": 6, "from": a, "to": b}])
    return parts


class Legs(unittest.TestCase):
    DOC: ClassVar = {"rig": "spider"}

    def test_a_one_piece_leg_fails_and_the_repair_splits_it_in_two(self):
        parts = spider([([0.1, 0.4, 0], [0.5, 0.0, 0])])
        self.assertFalse(rules(parts, self.DOC)[0]["leg_joints"])
        parts, log = D.repair(parts, self.DOC)
        self.assertEqual([p[0] for p in parts[1:]], ["leg1.upper", "leg1.lower"])
        self.assertTrue(rules(parts, self.DOC)[0]["leg_joints"])
        self.assertEqual(log[0][:2], ("leg_joints", "leg1"))

    def test_a_leg_bent_under_the_minimum_fails_and_a_bent_one_passes(self):
        parts = spider([([0.1, 0.4, 0], [0.3, 0.1, 0])])
        lower = copy.deepcopy(parts[1])
        lower[0] = "leg1.lower"
        lower[5].update({"from": [0.3, 0.1, 0], "to": [0.5, -0.2, 0]})
        straight = parts + [lower]
        self.assertFalse(rules(straight, self.DOC)[0]["leg_joints"])
        lower[5]["to"] = [0.5, 0.0, 0.0]
        self.assertTrue(rules(straight, self.DOC)[0]["leg_joints"])

    def test_a_biped_is_not_applicable(self):
        self.assertIn("leg_joints", rules(spider([([0.1, 0.4, 0], [0.5, 0.0, 0])]), {})[1])


class Props(unittest.TestCase):
    """prop_axis / prop_coverage against a synthetic sheet mask: the mask is the lance drawn upright."""

    @staticmethod
    def spec(top_x):
        return [["pelvis", "box", [0.6, 1.0, 0.4], [0, 0.5, 0], "m", {}],
                ["spine", "box", [0.6, 0.8, 0.4], [0, 1.4, 0], "m", {}],
                ["forearm.R", "prism", [0.03, 0.03, 1.6], [0, 0, 0], "m",
                 {"sides": 6, "from": [0.5, 0.2, 0], "to": [0.5 + top_x, 1.9, 0], "prop": "lance", "anchor": "hand.R", "asym": True}]]

    def run_rules(self, parts, mask):
        D._PANELS.clear()
        with mock.patch.object(D, "parts_doc", return_value={"parts": []}), \
                mock.patch("silhouette.concept_panels", return_value={"front": None, "left": None}), \
                mock.patch("silhouette.prop_masks", side_effect=lambda s, v, *a: {"lance": mask} if v == "front" else {}):
            return D.checks(parts, {}, "s.jpg"), D.prop_rows(parts, "s.jpg")

    def mask_of(self):
        upright = self.spec(0.0)
        return D.raster([p for p in upright if PF.is_prop(p)], "front", D.frame_of(upright, "front"), False)

    def test_a_lance_30_degrees_off_its_mask_fails_the_axis(self):
        (got, _), rows = self.run_rules(self.spec(0.9), self.mask_of())
        self.assertFalse({r: ok for r, ok, _ in got}["prop_axis"])
        self.assertGreater(abs(rows[("lance", "front")]["d_angle"]), D.PROP_AXIS_MAX)

    def test_the_repair_turns_it_back(self):
        parts, mask = self.spec(0.9), self.mask_of()
        D._PANELS.clear()
        with mock.patch.object(D, "parts_doc", return_value={"parts": []}), \
                mock.patch("silhouette.concept_panels", return_value={"front": None, "left": None}), \
                mock.patch("silhouette.prop_masks", side_effect=lambda s, v, *a: {"lance": mask} if v == "front" else {}):
            parts, log = D.repair(parts, {}, "s.jpg", opt_in=True)
            got, _ = D.checks(parts, {}, "s.jpg")
        self.assertEqual(log[0][:2], ("prop_axis", "lance"))
        self.assertTrue(all(ok for _, ok, _ in got), got)

    def test_no_prop_is_not_applicable(self):
        _ok, na = rules(self.spec(0.0)[:2], {}, "s.jpg")
        self.assertIn("no prop part", na["prop_axis"])
        self.assertIn("prop_coverage", na)


if __name__ == "__main__":
    unittest.main()
