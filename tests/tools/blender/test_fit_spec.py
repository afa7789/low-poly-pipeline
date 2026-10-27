"""python3 -m unittest discover -s tests/tools/blender"""
import pathlib
import sys
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import fit_spec as F  # noqa: E402
import silhouette  # noqa: E402
import spec_pipeline as SP  # noqa: E402

VIEWS = F.FIT_VIEWS


def box(bone, dims, at, **opts):
    return [bone, "box", list(dims), list(at), "iron", opts]


class Proxy(unittest.TestCase):
    def test_outlines(self):
        """a box fills its rectangle; a rotated one stays inside the hull of its corners; a cyl
        along fwd is a rectangle from the front and a disc from the left"""
        for name, part, view, want in [
                ("box front", box("b", (1, 2, 1), (0, 1, 0)), "front", (1.0, 2.0)),
                ("box left", box("b", (1, 2, 3), (0, 1, 0)), "left", (3.0, 2.0)),
                ("cyl front", ["b", "cyl", [0.5, 2.0], [0, 1, 0], "iron", {"axis": "fwd"}], "front", (1.0, 1.0)),
                ("cyl up front", ["b", "cyl", [0.5, 2.0], [0, 1, 0], "iron", {"axis": "up"}], "front", (1.0, 2.0)),
                ("span", ["b", "prism", [0.1, 0.1, 9], [0, 0, 0], "iron",
                          {"from": [0, 0, 0], "to": [0, 2, 0]}], "front", (0.2, 2.16))]:
            with self.subTest(name):
                pts = np.stack(F.PROJECT[view](F.part_points(part)), 1)
                got = pts.max(axis=0) - pts.min(axis=0)
                self.assertTrue(np.allclose(got, want, atol=0.03), got)

    def test_self_score_is_perfect(self):
        parts = [box("a", (1, 2, 1), (0, 1, 0)), box("b", (0.4, 0.4, 0.4), (0, 2.4, 0))]
        mask = F.raster(F.Proxy({}, VIEWS).outlines(parts)["front"])[0]
        concept = {v: silhouette.normalize(mask) for v in VIEWS}
        self.assertEqual(F.Proxy(concept, VIEWS).ious(parts), {v: 1.0 for v in VIEWS})


class Mirror(unittest.TestCase):
    def test_pairs(self):
        left = ["arm.L", "prism", [0.2, 0.1, 0.5], [0.5, 1, 0], "iron",
                {"from": [0.4, 1.2, 0], "to": [0.6, 0.8, 0.1], "rot": [0, 10, 20]}]
        right = ["arm.R", "prism", [0.2, 0.1, 0.5], [-0.5, 1, 0], "iron",
                 {"from": [-0.4, 1.2, 0], "to": [-0.6, 0.8, 0.1], "rot": [0, -10, -20]}]
        centre = box("c", (1, 1, 1), (0, 1, 0))
        self.assertEqual(F.groups_of([left, right, centre], [0, 1, 2]), [(0, 1), (2, None)])
        moved = F.moved(left, [0.5, 0, 0, 1, 0, 0], 2.0)
        self.assertAlmostEqual(moved[2][0], 0.2 * (1 + F.DIMS_RANGE * 0.5))
        self.assertAlmostEqual(moved[5]["from"][0], 0.4 + F.AT_RANGE * 2.0)
        self.assertAlmostEqual(F.moved(right, [0.5, 0, 0, 1, 0, 0], 2.0, mirror=True)[5]["from"][0], -0.4 - F.AT_RANGE * 2.0)


class Anchor(unittest.TestCase):
    def test_bounds_and_loose(self):
        """a no-grow box may shrink x/z only; a lower leg moved off its upper leg is loose at 80 %"""
        self.assertEqual(F.bounds_of(box("spine", (1, 2, 1), (0, 1, 0)), True)[:3], [(-1, 0), (-1, 1), (-1, 0)])
        self.assertEqual(F.bounds_of(box("arm.L", (1, 2, 1), (0, 1, 0)), False)[:3], [(-1, 1)] * 3)
        parents = {"forearm.L": "arm.L"}
        upper, lower = box("arm.L", (1, 1, 1), (0, 0, 0)), box("forearm.L", (1, 1, 1), (0.9, 0.9, 0.9))
        self.assertEqual(F.loose_of([upper, lower], parents), {"forearm.L"})
        lower[3] = [0.5, 0.5, 0.5]
        self.assertEqual(F.loose_of([upper, lower], parents), set())


class LegGrowth(unittest.TestCase):
    def test_thin_leg_may_reach_the_sheet_radius(self):
        leg = ["leg1.upper", "prism", [0.04, 0.02, 0.4], [0, 0, 0], "body", {"from": [0, 1, 0], "to": [0.4, 0, 0]}]
        radius = 0.03                       # mean of 0.04 and 0.02
        for name, part, leg_w, want in [("thin", leg, 0.06, 10.0), ("already thick", leg, 0.02, 1.0),
                                        ("no measure", leg, None, 1.0),
                                        ("not a leg", box("body", (1, 1, 1), (0, 0, 0)), 0.06, 1.0)]:
            with self.subTest(name):
                self.assertAlmostEqual(F.leg_grow(part, leg_w, 1.0), want)
        self.assertEqual(F.bounds_of(leg, False, 10.0), [(-1, 10.0), (-1, 10.0), (-1, 1)] + [(-1, 1)] * 3)
        self.assertEqual(radius, F.preflight.leg_radius(leg))


class Fit(unittest.TestCase):
    """fit() on a spec whose torso is half as wide as the sheet's, with the sheet read from the proxy"""

    def run_fit(self, rules=frozenset(), bone="arm.L"):
        parts = [box(bone, (0.5, 2, 0.5), (0, 1, 0)), box("head", (0.3, 0.3, 0.3), (0, 2.2, 0))]
        want = [box(bone, (0.9, 2, 0.9), (0, 1, 0)), parts[1]]
        shapes = F.Proxy({}, VIEWS).outlines(want)
        panels = {v: F.raster(shapes[v])[0] for v in VIEWS}
        doc = {"parts": parts, "rig": "biped"}
        with mock.patch.object(F.silhouette, "concept_panels", return_value=panels), \
                mock.patch.object(F.preflight, "targets_from", return_value={}), \
                mock.patch.object(F.preflight, "load_props", return_value=[]), \
                mock.patch.object(F, "broken_rules", side_effect=lambda p, *a: set(rules) if p is parts else {"x"}):
            return doc, F.fit(doc, pathlib.Path("sheet.jpg"), max_evals=300)

    def test_fits_the_failing_band(self):
        doc, (out, report) = self.run_fit(rules={"x"})
        self.assertTrue(report["changed"])
        self.assertTrue(all(report["after"][v] > report["before"][v] for v in VIEWS))
        self.assertGreater(out["parts"][0][2][0], 0.5)
        self.assertEqual(doc["parts"][0][2], [0.5, 2, 0.5], "the input is not edited")

    def test_torso_does_not_grow(self):
        _, (out, report) = self.run_fit(rules={"x"}, bone="spine")
        self.assertLessEqual(out["parts"][0][2][0], 0.5)
        self.assertLessEqual(out["parts"][0][2][2], 0.5)

    def test_hard_constraint_keeps_the_spec(self):
        _, (out, report) = self.run_fit(rules=set())     # every move breaks rule "x", which held
        self.assertFalse(report["changed"])

    def test_nothing_failing_nothing_moves(self):
        doc = {"parts": [box("spine", (1, 2, 1), (0, 1, 0))], "rig": "biped"}
        mask = F.raster(F.Proxy({}, VIEWS).outlines(doc["parts"])["front"])[0]
        with mock.patch.object(F.silhouette, "concept_panels", return_value={v: mask for v in VIEWS}):
            out, report = F.fit(doc, pathlib.Path("sheet.jpg"))
        self.assertIs(out, doc)
        self.assertEqual(report["failing"], [])


class FitAccepted(unittest.TestCase):
    GATES = {"front": 0.75, "left": 0.65}

    def test_cases(self):
        for name, prev, cur, problems, want in [
                ("gain", {"front": 0.70, "left": 0.70}, {"front": 0.78, "left": 0.70}, (None, None), True),
                ("a passing view falls under its gate", {"front": 0.70, "left": 0.70},
                 {"front": 0.80, "left": 0.60}, (None, None), False),
                ("a passing view dips but holds", {"front": 0.70, "left": 0.80},
                 {"front": 0.78, "left": 0.78}, (None, None), True),
                ("no gain", {"front": 0.70, "left": 0.70}, {"front": 0.70, "left": 0.70}, (None, None), False),
                ("no build", {"front": 0.70}, None, (None, None), False),
                ("a rule breaks", {"front": 0.70, "left": 0.70}, {"front": 0.78, "left": 0.70},
                 (None, "  ground  FAIL  x"), False)]:
            with self.subTest(name):
                self.assertEqual(SP.fit_accepted(prev, cur, self.GATES, problems), want)


if __name__ == "__main__":
    unittest.main()
