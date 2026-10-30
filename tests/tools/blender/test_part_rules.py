"""python3 -m unittest tests.tools.blender.test_part_rules

L15-4 (PIPELINE 33.L15-4): prop_side, part_exists, arm_pose, incoherent_part. Fixtures are a few parts and a hand-made parts.json;
the real v15 specs of n02X / n005 are the acceptance (skipped when the archive is not on this machine). No Blender, no model."""
import copy
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import dsl_rules as D  # noqa: E402
import part_rules as R  # noqa: E402

ARCHIVE = pathlib.Path("/Users/afa/Developer/arthur/castle_fight/.claude/worktrees/v2-hard/artifacts/model-sheets/runs/draft")
REFS = ROOT / "artifacts/model-sheets/refs"


def box(x0, y0, x1, y1):
    return [x0, y0, x1, y1]


def pdoc(club_x=(0.2, 0.35), face=-1):
    """Facing left in the left panel (chin left of the head top), a torso at .35-.81 and a club clear of it."""
    chin, top = ([0.5, 0.66], [0.54, 0.84]) if face < 0 else ([0.54, 0.66], [0.5, 0.84])
    return {"H": 2.0, "joints": {"chin": {"left": chin}, "head_top": {"left": top},
                                 "shoulder.R": {"xyz": [-0.5, 1.5, 0]}, "elbow.R": {"xyz": [-0.6, 1.0, 0]}, "wrist.R": {"xyz": [-0.8, 1.05, 0]}},
            "parts": [{"name": "torso", "role": "torso", "prop": False, "box2d": {"front": box(0.3, 0.3, 0.7, 0.7), "left": box(0.35, 0.3, 0.81, 0.7)},
                       "box3d": [[-0.5, 0.6, -0.3], [0.5, 1.4, 0.3]]},
                      {"name": "club", "role": "prop", "prop": True, "box2d": {"left": box(club_x[0], 0.4, club_x[1], 0.9)}}]}


def club(z):
    return ["forearm.R", "prism", [0.1, 0.1, 1.0], [-0.8, 1.5, z], "iron",
            {"from": [-0.8, 1.0, z], "to": [-0.8, 2.0, z], "prop": "club", "anchor": "hand.R"}]


def body():
    return [["spine", "box", [1.0, 0.8, 0.5], [0, 1.0, 0.1], "skin", {}], ["pelvis", "box", [0.8, 0.4, 0.5], [0, 0.5, 0.1], "skin", {}]]


class PropSide(unittest.TestCase):
    def test_a_prop_behind_the_body_fails_and_the_repair_mirrors_it_to_the_front(self):
        parts = body() + [club(-0.6)]
        got, _ = R.side_checks(parts, pdoc())
        self.assertFalse(got[0][1])
        log = []
        R.side_repair(parts, pdoc(), log)
        self.assertAlmostEqual(parts[-1][3][2], 0.1 + 0.3 * 1.5 * 1.0, delta=0.2, msg="the sheet's offset from the torso, in front")
        self.assertEqual(parts[-1][5]["to"][2], parts[-1][5]["from"][2], "a tall, narrow prop stands upright in depth")
        self.assertTrue(R.side_checks(parts, pdoc())[0][0][1])
        self.assertEqual(log[0][0], "prop_side")

    def test_a_prop_on_the_right_side_passes_and_the_face_direction_decides(self):
        self.assertTrue(R.side_checks(body() + [club(0.7)], pdoc())[0][0][1])
        self.assertFalse(R.side_checks(body() + [club(0.7)], pdoc(face=1))[0][0][1], "facing right, the club panel-left is behind")

    def test_a_prop_over_the_torso_has_no_side(self):
        got, na = R.side_checks(body() + [club(-0.6)], pdoc(club_x=(0.4, 0.8)))
        self.assertEqual(got, [])
        self.assertIn("prop_side", na)


class ArmPose(unittest.TestCase):
    def arm(self, to):
        return ["forearm.R", "prism", [0.1, 0.1, 0.5], [0, 0, 0], "skin", {"from": [-0.6, 1.0, 0.0], "to": to}]

    def test_a_forearm_hanging_when_the_sheet_raises_it_fails_and_is_turned_to_the_sheet(self):
        parts = body() + [self.arm([-0.65, 0.5, 0.0]), club(0.7)]
        parts[-1][5]["from"] = [-0.65, 0.5, 0.7]
        got, _ = R.arm_checks(parts, pdoc(), "biped")
        self.assertFalse(got[0][1])
        self.assertIn("forearm.R", got[0][2])
        log = []
        R.arm_repair(parts, pdoc(), log)
        self.assertTrue(R.arm_checks(parts, pdoc(), "biped")[0][0][1])
        self.assertAlmostEqual(parts[-2][5]["to"][1], 1.0 + (0.05 / 0.2) * 0.2, delta=0.1)
        self.assertEqual(parts[-1][5]["to"][1] - parts[-1][5]["from"][1], 1.5, "the prop slid with the wrist, it did not turn")

    def test_an_arm_within_the_tolerance_is_left_alone(self):
        parts = body() + [self.arm([-0.8, 1.05, 0.0])]
        self.assertTrue(R.arm_checks(parts, pdoc(), "biped")[0][0][1])
        log = []
        R.arm_repair(parts, pdoc(), log)
        self.assertEqual(log, [])

    def test_other_rigs_are_not_applicable(self):
        self.assertIn("arm_pose", R.arm_checks([], pdoc(), "spider")[1])


class PartExists(unittest.TestCase):
    def setUp(self):
        fg = np.ones((100, 100), bool)
        rgb = np.full((100, 100, 3), (190, 150, 110), np.uint8)       # skin everywhere ...
        rgb[40:60, 40:60] = (50, 50, 50)                              # ... and one dark zone at the centre
        self.panels = {"front": (rgb, fg), "back": (rgb, fg)}
        self.doc = {"palette": {"skin": {"surface": "skin", "color": "#BE966E"}, "dark": {"surface": "metal", "color": "#323232"},
                                "gold": {"surface": "metal", "color": "#D0A030"}}}
        self.pdoc = {"H": 2.0, "parts": [{"name": "a", "box2d": {"front": [0, 0, 1, 1]}, "box3d": [[-1, 0, 0], [1, 2, 0]]},      # x -1..1 -> 0..1, y 0..2 -> 0..1
                                         {"name": "b", "box2d": {"front": [0, 0, 0.5, 0.5]}, "box3d": [[-1, 0, 0], [0, 1, 0]]}]}

    def run_rule(self, parts):
        with mock.patch.object(R, "panels", return_value=self.panels):
            return R.missing_parts(parts, self.doc, self.pdoc, "sheet.jpg")

    def test_a_part_with_no_zone_of_its_colour_is_missing_and_one_with_it_is_not(self):
        on_zone = ["spine", "box", [0.4, 0.4, 0.2], [0.0, 1.0, 0.0], "dark", {}]
        off_zone = ["head", "box", [0.4, 0.4, 0.2], [0.7, 1.7, 0.0], "gold", {}]
        skin = ["pelvis", "box", [0.4, 0.4, 0.2], [0.0, 0.5, 0.0], "skin", {}]
        gone = self.run_rule([on_zone, off_zone, skin, ["head", "box", [0.1, 0.1, 0.1], [0, 2.0, 0], "skin", {}]])
        self.assertEqual([p[4] for p, _ in gone], ["gold"], "skin is the body, the dark zone is there")

    def test_a_prop_the_sheet_names_is_never_rejected_and_the_only_part_on_a_bone_is_kept(self):
        prop = ["forearm.R", "box", [0.4, 0.4, 0.2], [0.7, 1.7, 0.0], "gold", {"prop": "Club"}]
        self.pdoc["parts"].append({"name": "club", "prop": True, "box2d": {}})      # no box3d: the height reads the others
        self.assertEqual(self.run_rule([prop]), [])
        lone = ["head", "box", [0.4, 0.4, 0.2], [0.7, 1.7, 0.0], "gold", {}]
        parts, log = [lone], []
        with mock.patch.object(R, "panels", return_value=self.panels):
            R.exist_repair(parts, self.doc, self.pdoc, "sheet.jpg", log)
        self.assertEqual((len(parts), log), (1, []))
        parts = [lone, ["head", "box", [0.4, 0.4, 0.2], [0.0, 1.0, 0.0], "dark", {}]]
        with mock.patch.object(R, "panels", return_value=self.panels):
            R.exist_repair(parts, self.doc, self.pdoc, "sheet.jpg", log)
        self.assertEqual((len(parts), log[0][3]), (1, "reject-part (removed)"))

    def test_it_reports_and_does_not_block_while_the_colour_test_is_noisy(self):
        spec = [["head", "box", [0.4, 0.4, 0.2], [0.7, 1.7, 0.0], "gold", {}], ["head", "box", [0.1, 0.1, 0.1], [0, 2.0, 0], "skin", {}]]
        with mock.patch.object(R, "panels", return_value=self.panels):
            rule, ok, detail = R.exist_checks(spec, self.doc, self.pdoc, "sheet.jpg")[0][0]
        self.assertEqual(rule, "part_exists")
        self.assertEqual(ok, not R.EXIST_BLOCKING)
        self.assertIn("gold", detail)


class Incoherent(unittest.TestCase):
    def sheet(self, front_x, back_x):
        def pan(x):
            rgb = np.full((100, 100, 3), (190, 150, 110), np.uint8)
            rgb[40:60, x:x + 10] = (230, 110, 30)
            return rgb, np.ones((100, 100), bool)
        return {"front": pan(front_x), "back": pan(back_x)}

    def rows(self, front_x, back_x):
        with mock.patch.object(R, "panels", return_value=self.sheet(front_x, back_x)):
            return R.incoherent_parts("sheet.jpg", {"parts": []})

    def test_the_same_zone_on_opposite_sides_of_the_body_is_one_incoherent_part(self):
        rows = self.rows(70, 70)         # front: character's left (panel right); back: panel right = the character's right
        self.assertEqual([r["hue"] for r in rows], ["orange"])
        self.assertEqual(rows[0]["ignore"], ["back"])

    def test_the_same_side_is_coherent_and_the_spec_can_override(self):
        self.assertEqual(self.rows(70, 20), [])
        rows = self.rows(70, 70)
        rows[0]["part"] = "tanga"
        spec = [["pelvis", "box", [1, 1, 1], [0, 0, 0], "m", {"prop": "Tanga", "side": "back"}]]
        out = R.decided(rows, spec)[0]
        self.assertEqual((out["side"], out["ignore"], out["by"]), ("back", ["front"], "spec"))
        self.assertEqual(R.ignored_views({"part_coherence": rows}, spec), {"tanga": ["front"]})

    def test_save_merges_into_sheet_json_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            sheet = pathlib.Path(d) / "sheet.jpg"
            (pathlib.Path(d) / "sheet.json").write_text(json.dumps({"tilts": {"top": -20}}))
            self.assertIsNotNone(R.save(sheet, [{"part": "x"}]))
            self.assertEqual(json.loads((pathlib.Path(d) / "sheet.json").read_text()), {"tilts": {"top": -20}, "part_coherence": [{"part": "x"}]})
            self.assertIsNone(R.save(sheet, [{"part": "x"}]))


@unittest.skipUnless(ARCHIVE.exists() and (REFS / "n02X/sheet.jpg").exists(), "the v15 archive is not on this machine")
class V15Specs(unittest.TestCase):
    def load(self, unit):
        doc = json.loads((ARCHIVE / unit / "v15-r1/spec.json").read_text())
        return doc, REFS / unit / "sheet.jpg"

    def test_n02x_is_caught_by_all_three_rules_and_the_repair_passes_them(self):
        doc, sheet = self.load("n02X")
        got = {r: ok for r, ok, _ in D.checks(doc["parts"], doc, sheet)[0]}
        self.assertFalse(got["prop_side"])
        self.assertFalse(got["arm_pose"])
        self.assertTrue(R.missing_parts(doc["parts"], doc, D.parts_doc(sheet), sheet), "chest / belt plates, gauntlets, helmet")
        parts, log = D.repair(copy.deepcopy(doc["parts"]), doc, sheet, opt_in=True)
        after = {r: ok for r, ok, _ in D.checks(parts, doc, sheet)[0]}
        self.assertTrue(after["prop_side"] and after["arm_pose"])
        self.assertFalse(R.missing_parts(parts, doc, D.parts_doc(sheet), sheet))
        self.assertEqual({r for r, *_ in log}, {"prop_side", "arm_pose", "part_exists"})

    def test_the_default_repair_leaves_the_new_rules_alone(self):
        doc, sheet = self.load("n02X")
        self.assertEqual(D.repair(copy.deepcopy(doc["parts"]), doc, sheet)[1], [], "opt-in: the battery cost views > 2 sigma")

    def test_n02x_fuse_cloth_is_the_incoherent_part(self):
        self.assertEqual([r["part"] for r in R.incoherent_parts(REFS / "n02X/sheet.jpg")], ["well flame fuse cloth"])

    def test_n005_arm_pose_fails(self):
        doc, sheet = self.load("n005")
        self.assertFalse({r: ok for r, ok, _ in D.checks(doc["parts"], doc, sheet)[0]}["arm_pose"])


if __name__ == "__main__":
    unittest.main()
