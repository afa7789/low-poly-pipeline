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


class EdgeTerm(unittest.TestCase):
    def test_edge_term(self):
        """a part outline on the drawn edge costs ~0, one far from it more; no drawn edge costs 0;
        the loss only carries the term when the proxy holds hard edges"""
        parts = [box("a", (1, 2, 1), (0, 1, 0)), box("b", (1, 1, 1), (0, 2.5, 0))]
        outs = F.Proxy({}, VIEWS).outlines(parts)["front"]
        mask = F.raster(outs)[0]
        on, off = F.edge_of(mask), np.zeros_like(mask)
        off[:, 5] = True
        self.assertLess(F.edge_term(outs, on), 0.02)
        self.assertGreater(F.edge_term(outs, off), 0.1)
        self.assertEqual(F.edge_term(outs, np.zeros_like(mask)), 0.0)
        concept = {"front": mask}
        plain = F.Proxy(concept, ("front",)).loss(parts)
        self.assertAlmostEqual(F.Proxy(concept, ("front",), hard={"front": off}).loss(parts) - plain,
                               F.EDGE_W * F.edge_term(outs, off), places=6)


class Proxy(unittest.TestCase):
    def test_outlines(self):
        """a box fills its rectangle; a rotated one stays inside the hull of its corners; a cyl
        along fwd is a rectangle from the front and a disc from the left"""
        for name, part, view, want in [
                ("box front", box("b", (1, 2, 1), (0, 1, 0)), "front", (1.0, 2.0)),
                ("box left", box("b", (1, 2, 3), (0, 1, 0)), "left", (3.0, 2.0)),
                ("cyl front", ["b", "cyl", [0.5, 2.0], [0, 1, 0], "iron", {"axis": "fwd"}], "front", (1.0, 1.0)),
                ("cyl up front", ["b", "cyl", [0.5, 2.0], [0, 1, 0], "iron", {"axis": "up"}], "front", (1.0, 2.0)),
                ("frustum 8 left", ["b", "frustum", [1, 2, 3], [0, 1, 0], "iron", {"sides": 8}], "left", (3.0, 2.0)),
                ("cyl up 12 front", ["b", "cyl", [0.5, 2.0], [0, 1, 0], "iron", {"axis": "up", "sides": 12}], "front", (1.0, 2.0)),
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
        self.assertEqual(F.bounds_of(leg, False, grow=10.0), [(-1, 10.0), (-1, 10.0), (-1, 1)] + [(-1, 1)] * 3)
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


class FitProps(unittest.TestCase):
    """PIPELINE 23.L5-3: a prop keeps its dims and follows its anchor; the fit never frees it."""

    def test_prop_follows_its_anchor_and_keeps_its_size(self):
        arm = box("forearm.R", (0.5, 1, 0.5), (0, 1, 0))
        club = box("forearm.R", (0.1, 0.6, 0.1), (0.1, 0.8, 0), prop="club", anchor="hand.R")
        wide = F.moved(arm, [1, 1, 1, 0.5, 0, 0], 2.0)            # dims x1.2 (DIMS_RANGE), at moved sideways
        out = F.carry_props([arm, club], [wide, club])
        self.assertEqual(out[1][2], [0.1, 0.6, 0.1])
        self.assertAlmostEqual(out[1][3][0] - 0.1, wide[3][0] - arm[3][0])
        self.assertEqual(club[3], [0.1, 0.8, 0], "the input is not edited")

    def test_apply_carries_the_prop_with_a_moved_anchor(self):
        arm = box("forearm.R", (0.5, 1, 0.5), (0, 1, 0))
        club = box("forearm.R", (0.1, 0.6, 0.1), (0.1, 0.8, 0), prop="club", anchor="hand.R")
        out = F.apply([arm, club], [(0, None)], np.array([0, 0, 0, 1.0, 0, 0]), 2.0)
        self.assertGreater(out[1][3][0], 0.1)
        self.assertEqual(out[1][2], [0.1, 0.6, 0.1])


class Wide(unittest.TestCase):
    """PIPELINE 21.F4: swept cameras, rot, wide dims, zones, the cut toggle, the budget"""

    def test_project(self):
        """top tilts toward the front (v = y cos + z sin), bottom mirrors y; rts at 0 deg elevation and
        azimuth 0 is the front camera; at azimuth 90 the camera sits on +x and sees y as its right"""
        p = np.array([[1.0, 2.0, 3.0]])
        for name, view, cam, want in [("top 0", "top", 0, (1, 2)), ("top 30", "top", 30, (1, 2 * 0.866 + 3 * 0.5)),
                                      ("bottom 30", "bottom", 30, (1, -2 * 0.866 + 3 * 0.5)),
                                      ("rts front", "rts", (0, 0), (1, 3)), ("turn 90", "turn90", 90, (2, 3))]:
            with self.subTest(name):
                u, v = F.project(view, p, cam)
                self.assertTrue(np.allclose((u[0], v[0]), want, atol=1e-3), (u, v))

    def test_rot_extra(self):
        """a hand takes a rot of up to ROT_RANGE deg per axis; its twin turns (right, -up, -forward)"""
        hand = ["hand.L", "box", [1, 1, 1], [0.5, 1, 0], "iron", {"rot": [0, 0, 10]}]
        self.assertEqual(F.extras_of(hand), ("rot",))
        self.assertEqual(F.extras_of(["spine", "box", [1, 1, 1], [0, 1, 0], "iron", {}]), ())
        self.assertEqual(F.extras_of(["arm.L", "prism", [1, 1, 1], [0, 0, 0], "iron", {"from": [0] * 3, "to": [1] * 3}]), ())
        self.assertEqual(F.extras_of(["spine", "box", [1, 1, 1], [0, 1, 0], "iron", {}], hood=True), ("rot",))
        x = [0, 0, 0, 0, 0, 0, 1, 0, -1]
        self.assertEqual(F.moved(hand, x, 2.0, extra=("rot",))[5]["rot"], [F.ROT_RANGE, 0, 10 - F.ROT_RANGE])
        self.assertEqual(F.moved(hand, x, 2.0, mirror=True, extra=("rot",))[5]["rot"], [F.ROT_RANGE, 0, 10 + F.ROT_RANGE])
        self.assertEqual(len(F.bounds_of(hand, False, False, ("rot",))), 3 + 3 + 3)

    def test_wide_dims(self):
        """attached parts move their dims by 20 %, a no-grow part still only shrinks"""
        part = box("arm.L", (1, 2, 1), (0, 1, 0))
        self.assertEqual(F.bounds_of(part, False, True)[:3], [(-2, 2)] * 3)
        self.assertEqual(F.bounds_of(part, True, True)[:3], [(-1, 0), (-2, 2), (-1, 0)])

    def test_toggle_cut(self):
        """cut goes on the largest plain torso/pelvis/hood part, off everywhere when any part has it"""
        doc = {"parts": [box("spine", (1, 2, 1), (0, 1, 0)), box("spine", (0.2, 0.2, 0.2), (0, 1, 0)),
                         box("arm.L", (1, 2, 1), (0, 1, 0)), box("pelvis", (1, 1, 1), (0, 1, 0), rot=[0, 0, 5])]}
        on = F.toggle_cut(doc)
        self.assertEqual([p[5].get("cut") for p in on["parts"]], ["sheet", None, None, None])
        self.assertNotIn("cut", doc["parts"][0][5], "the input is not edited")
        self.assertEqual([p[5].get("cut") for p in F.toggle_cut(on)["parts"]], [None] * 4)
        self.assertIsNone(F.toggle_cut({"parts": [box("arm.L", (1, 1, 1), (0, 1, 0))]}))

    def test_zone_share(self):
        """a part lying half in its zone scores one half, a flipped view reads the labels mirrored"""
        zones = F.Zones.__new__(F.Zones)
        labels = np.zeros((silhouette.CANVAS_H, silhouette.CANVAS_W), np.int16)
        labels[:, :silhouette.CANVAS_W // 2] = 1
        zones.labels = {"front": labels}
        outline = np.array([[0, 0], [2, 0], [2, 2], [0, 2]], float)
        canvas = F.canvas_of([outline])           # fills the canvas height, centred
        wide = np.array([[-1, 0], [1, 0], [1, 2], [-1, 2]], float)
        for flipped, want in [(False, 0.5), (True, 0.5)]:
            self.assertAlmostEqual(zones.share("front", wide, F.canvas_of([wide]), 1, flipped), want, places=1)
        self.assertGreater(canvas[2], 0)
        left = np.array([[-1, 0], [-0.1, 0], [-0.1, 2], [-1, 2]], float)
        both = [left, np.array([[0.1, 0], [1, 0], [1, 2], [0.1, 2]], float)]
        self.assertAlmostEqual(zones.share("front", left, F.canvas_of(both), 1, False), 1.0, places=1)
        self.assertAlmostEqual(zones.share("front", left, F.canvas_of(both), 1, True), 0.0, places=1)

    def test_turn_panels_only_when_the_sheet_has_them(self):
        self.assertEqual(F.turn_masks(pathlib.Path("/nonexistent/sheet.jpg")), {})
        mask = np.zeros((20, 10), bool)
        mask[2:18, 3:7] = True
        with mock.patch.object(F.silhouette, "turn_panels", create=True, return_value={0: mask, 45: mask}), \
                mock.patch.object(pathlib.Path, "exists", return_value=True):
            self.assertEqual(list(F.turn_masks(pathlib.Path("sheet.jpg"))), ["turn45"])

    def test_budget_stops_the_search(self):
        """no time left: the search stops at once and the spec comes back intact"""
        parts = [box("arm.L", (0.5, 2, 0.5), (0, 1, 0))]
        shapes = F.Proxy({}, VIEWS).outlines([box("arm.L", (0.9, 2, 0.9), (0, 1, 0))])
        panels = {v: F.raster(shapes[v])[0] for v in VIEWS}
        doc = {"parts": parts, "rig": "biped"}
        with mock.patch.object(F.silhouette, "concept_panels", return_value=panels), \
                mock.patch.object(F.preflight, "targets_from", return_value={}), \
                mock.patch.object(F.preflight, "load_props", return_value=[]), \
                mock.patch.object(F, "broken_rules", return_value=set()):
            out, report = F.fit(doc, pathlib.Path("sheet.jpg"), seconds=0)
        self.assertIs(out, doc)
        self.assertEqual(report["evals"], 0)


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

    def test_view_floor(self):
        """a spider's top may not fall > FIT_SLIP even under its gate; a biped's top is not critical"""
        gates = {"front": 0.65, "top": 0.65}
        prev, cur = {"front": 0.60, "top": 0.60}, {"front": 0.70, "top": 0.56}
        self.assertFalse(SP.fit_accepted(prev, cur, gates, (None, None), "spider"))
        self.assertTrue(SP.fit_accepted(prev, cur, gates, (None, None), "biped"))
        self.assertTrue(SP.fit_accepted(prev, {**cur, "top": 0.59}, gates, (None, None), "spider"))


class Stages(unittest.TestCase):
    def test_masks(self):
        """trunk = dims/at of trunk bones, limbs = the rest and rot/knee, profiles = lathe radii; the masks
        partition the flat vector"""
        parts = [box("spine", (1, 2, 1), (0, 1, 0)), box("arm", (1, 1, 1), (1, 1, 0)),
                 ["body", "lathe", [0.5, 1.0], [0, 1, 0], "iron", {"profile": [0.4, 0.5, 0.4]}]]
        groups = [(0, None), (1, None), (2, None)]
        extra = {0: ("rot",), 1: ("rot",), 2: ("profile",)}
        masks = F.stage_masks(parts, groups, extra, F.STAGES)
        size = sum(F.group_size(parts[i], extra[i]) for i, _ in groups)
        self.assertEqual(sum(m.sum() for m in masks.values()), size)
        self.assertFalse(np.logical_and.reduce([masks["trunk"], masks["limbs"]]).any())
        self.assertEqual(int(masks["trunk"].sum()), 6 + 5)             # spine and lathe dims+at
        self.assertEqual(int(masks["profiles"].sum()), 4)
        self.assertEqual(int(masks["limbs"].sum()), 6 + 3 + 3)         # arm dims+at, both rots

    def test_descend_stages(self):
        """staged Powell reaches the optimum of a separable bowl, spending at most 1/3 of the budget per stage"""
        target = np.array([0.5, -0.5, 0.25, 0.1, -0.2, 0.3])
        masks = {"a": np.array([1, 1, 0, 0, 0, 0], bool), "b": np.array([0, 0, 1, 1, 0, 0], bool),
                 "c": np.array([0, 0, 0, 0, 1, 1], bool)}

        class Bowl:
            ctx = {"max_evals": 300, "deadline": float("inf")}
            best, n = {"f": float("inf"), "x": None}, 0

            def __call__(self, x):
                if self.n >= self.ctx["max_evals"]:
                    raise F.Stop
                self.n += 1
                f = float(((x - target) ** 2).sum())
                if f < self.best["f"]:
                    self.best.update(f=f, x=np.array(x, float))
                return f
        bowl = Bowl()
        F.descend(bowl, [(-1, 1)] * 6, masks, 100.0)
        self.assertLess(bowl.best["f"], 1e-3)


class JointTerm(unittest.TestCase):
    def test_gap_in_h_and_zero_without_a_target(self):
        thigh = ["thigh.L", "prism", [0.1, 0.1, 0.5], [0, 0.75, 0], "iron", {"from": [0, 1.0, 0], "to": [0, 0.6, 0]}]
        shin = ["shin.L", "prism", [0.1, 0.1, 0.5], [0, 0.3, 0], "iron", {"from": [0, 0.6, 0], "to": [0, 0, 0]}]
        for name, targets, want in (("gap", {"knee_h": 0.5}, 0.1), ("on it", {"knee_h": 0.6}, 0.0), ("unseen", {}, 0.0)):
            with self.subTest(name):
                self.assertAlmostEqual(F.joint_term([thigh, shin], targets, 1.0), want, places=1)


if __name__ == "__main__":
    unittest.main()
