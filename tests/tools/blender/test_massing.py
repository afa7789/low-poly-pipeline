"""python3 -m unittest discover -s tests/tools/blender"""
import pathlib
import sys
import json
import types
import unittest

import numpy as np

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[3] / "tools/blender"))

import lathe_limb  # noqa: E402
import massing as M  # noqa: E402
import preflight as PF  # noqa: E402
import rig_families as RF  # noqa: E402

REFS = HERE.parents[3] / "artifacts/model-sheets/refs"
FIXTURES = HERE.parent / "fixtures"


def figure():
    """A 100 px figure: a 20 px wide column with a detached 3 px speck beside it."""
    m = np.zeros((120, 120), bool)
    m[10:110, 50:70] = True
    m[40:50, 100:103] = True
    return m


class View(unittest.TestCase):
    def test_metres_and_specks(self):
        v = M.View(figure(), 2.0)
        self.assertAlmostEqual(v.s, 0.02)
        self.assertAlmostEqual(v.width, 0.4, 2)          # the speck is not the figure
        self.assertAlmostEqual(v.half(0.5, 1.5), 0.2, 2)
        self.assertEqual(len(v.runs(1.0)), 1)

    def test_recentre_and_runs(self):
        m = figure()
        m[:, 55:60] = False                              # a gap down the middle: two runs
        v = M.View(m, 2.0)
        self.assertEqual(len(v.runs(1.0)), 2)
        v.recentre(0.0, 1.0)
        self.assertAlmostEqual(v.cx, 60.0)


class Stack(unittest.TestCase):
    def test_breakpoints_land_on_the_bend(self):
        ys = np.linspace(0, 1, 41)
        w = np.where(ys < 0.5, 1.0, 1.0 - (ys - 0.5))
        cuts = M.breakpoints(ys, [w], 2)
        self.assertIn(0.5, [round(float(c), 3) for c in cuts])

    def test_stack_follows_widths_and_overlaps(self):
        g = {"y0": 0.0, "y1": 1.0, "w": lambda y: 1.0 - 0.5 * y, "d": lambda y: 0.4, "zc": lambda y: 0.0}
        parts = M._frustum_stack("torso", "spine", "z1", g)
        self.assertEqual(len(parts), 1)                  # a straight taper is one frustum
        self.assertAlmostEqual(parts[0][2][0], 1.0, 1)
        self.assertAlmostEqual(parts[0][5]["top"][0], 0.5, 1)
        self.assertTrue(all(p[1] == "frustum" and p[0] == "spine" for p in parts))

    def test_emit_falls_back_for_a_kind_without_emitter(self):
        saved = dict(M.KIND_FOR)
        try:
            M.KIND_FOR["torso"] = "dome"                 # a kind with no emitter
            g = {"y0": 0.0, "y1": 1.0, "w": lambda y: 1.0, "d": lambda y: 1.0, "zc": lambda y: 0.0}
            self.assertEqual(M.emit("torso", "spine", "z1", g)[0][1], "frustum")
        finally:
            M.KIND_FOR.update(saved)


class Slots(unittest.TestCase):
    def test_three_materials_in_use(self):
        parts = [["head", "box", [1, 1, 1], [0, 0, 0], "z1", {}], ["foot.L", "box", [1, 1, 1], [0, 0, 0], "z1", {}],
                 ["abdomen", "box", [1, 1, 1], [0, 0, 0], "z1", {}]]
        M.ensure_slots(parts, ["z1", "z2", "z3"])
        self.assertEqual(len({p[4] for p in parts}), 3)


@unittest.skipUnless((REFS / "n01X/sheet.jpg").exists(), "needs the n01X sheet")
class Build(unittest.TestCase):
    def test_biped_prespec_passes_the_preflight(self):
        sheet = REFS / "n01X/sheet.jpg"
        spec = M.build(sheet, "biped", "Mech")
        self.assertTrue(RF.required("biped") <= {p[0] for p in spec["parts"]})
        self.assertGreaterEqual(sum(PF.part_tris(p) for p in spec["parts"]), 400)
        doc = {"rig": "biped", "palette": spec["palette"]}
        checks = PF.checks_of(spec["parts"], doc, "mass", PF.targets_from(sheet), PF.load_props("n01X"), sheet)
        self.assertEqual([c[0] for c in checks if not c[1]], [])

    def test_other_families_have_no_massing(self):
        self.assertIsNone(M.build(REFS / "n01X/sheet.jpg", "vehicle"))


@unittest.skipUnless((REFS / "n005/sheet-hard.jpg").exists(), "needs the n005 sheet")
class PartsBuild(unittest.TestCase):
    """PIPELINE 23.L5-2: refs/<id>/parts.json drives the pre-spec; without it the band massing is unchanged."""

    def test_one_piece_per_part_and_no_parts_is_the_band_massing(self):
        sheet, doc = REFS / "n005/sheet-hard.jpg", json.loads((FIXTURES / "parts-n005.json").read_text())
        band = M.build(sheet, "biped", "Human", parts=False)
        self.assertEqual(M.build(sheet, "biped", "Human"), band)         # no refs/n005/parts.json: nothing changes
        spec = M.build(sheet, "biped", "Human", parts=doc)
        kinds = {p[1] for p in spec["parts"]}
        self.assertLessEqual({"lathe", "limb", "prism", "box", "frustum"}, kinds)
        tank = [p for p in spec["parts"] if p[1] == "lathe" and p[0] == "spine"]
        self.assertEqual(len(tank), 1)                                    # the tank is its own lathe on the spine
        self.assertLess(tank[0][3][2], -0.5)                              # behind the torso
        self.assertTrue(any(p[1] == "box" and p[0] == "forearm.L" for p in spec["parts"]))   # the held weapon

    def test_half_written_parts_fall_back(self):
        sheet, doc = REFS / "n005/sheet-hard.jpg", json.loads((FIXTURES / "parts-n005.json").read_text())
        doc["parts"] = [q for q in doc["parts"] if q["role"] != "leg"]
        self.assertEqual(M.build(sheet, "biped", "Human", parts=doc), M.build(sheet, "biped", "Human", parts=False))

    def test_limb_knee_comes_from_the_joints(self):
        doc = json.loads((FIXTURES / "parts-n005.json").read_text())
        leg = next(q for q in doc["parts"] if q["bone"] == "thigh.L")
        part = M.limb_part(leg, "z1", doc, 8, ("hip", "knee", "ankle"))[0]
        self.assertEqual(part[1], "limb")
        knee = M.lathe_limb.knee_of(part[5])
        for got, want in zip(knee, doc["joints"]["knee.L"]["xyz"]):
            self.assertAlmostEqual(got, want, 2)


class Joints(unittest.TestCase):
    def test_measured_joint_is_kept_inside_the_bone_and_midway_without_it(self):
        for name, y, want in (("none", None, 5.0), ("in", 4.0, 4.0), ("too low", 0.1, 1.5), ("too high", 9.9, 8.5)):
            with self.subTest(name):
                self.assertAlmostEqual(M.joint_between(y, 0.0, 10.0), want)

    def test_landmarks_follow_the_measure_only_when_enabled(self):
        front, m = M.View(figure(), 1.0), {"shoulder_frac": 0.2, "arm_length": 0.4, "arm_angle": 0.0, "boot_height": 0.07,
                                           "knee_h": 0.3, "elbow_h": 0.6}
        self.assertEqual((M.landmarks(front, 1.0, m)["knee"], M.landmarks(front, 1.0, m)["elbow"]), (None, None))
        M.MEASURED_JOINTS = True
        try:
            lm = M.landmarks(front, 1.0, m)
        finally:
            M.MEASURED_JOINTS = False
        self.assertEqual((lm["knee"], lm["elbow"]), (0.3, 0.6))


class Pipeline(unittest.TestCase):
    def test_edit_report(self):
        import spec_pipeline as SP
        pre = {"parts": [["head", "box", [1], [0], "a", {}], ["spine", "box", [1], [0], "a", {}]]}
        spec = {"parts": [["head", "box", [1], [0], "a", {}], ["spine", "box", [2], [0], "a", {}], ["head", "box", [3], [0], "b", {}]]}
        self.assertEqual(SP.edit_changes(pre, spec), (2, 1))
        self.assertEqual(SP.rules_of("\n20/21 rules pass -> fix"), "20/21")
        self.assertEqual(SP.rules_of("nothing"), "-")

    def test_massing_off_and_section(self):
        import spec_pipeline as SP
        args = types.SimpleNamespace(no_massing=True, spec=None, rig="biped")
        self.assertIsNone(SP.massing_spec(args))
        self.assertEqual(SP.massing_section(types.SimpleNamespace()), "")
        args = types.SimpleNamespace(pre_spec={"parts": [1, 2]}, massing_report={
            "iou": {"front": 0.8}, "ok": False, "failed": ["silhouette"], "tris": 488, "rules": "20/21", "edit": (3, 1)})
        text = SP.massing_section(args)
        self.assertIn("massing alone", text)
        self.assertIn("0.800 / - / -", text)
        self.assertIn("3 parts new or edited, 1 dropped (of 2)", text)


class Families(unittest.TestCase):
    """The pre-spec of the three new body plans, on their real sheets (PIPELINE 22.L4-4b)."""

    def tearDown(self):
        RF.FAMILIES.update(RF.FIXED)
        RF._drop_caches()

    def test_each_unit_covers_its_bones_inside_the_budget(self):
        for unit, rig, kinds in (("n017", "quadruped", {"frustum", "limb", "chain"}), ("n00H", "wyrm", {"chain", "plate", "prism"}),
                                 ("n010", "drake", {"chain", "plate", "limb", "prism"})):
            with self.subTest(unit):
                spec = M.build(REFS / unit / "sheet.jpg", rig)
                parts = spec["parts"]
                self.assertTrue(kinds <= {p[1] for p in parts})
                self.assertIn("line", spec["rig_measure"])
                have = {p[0] for p in parts} | {b for p in parts if p[1] == "limb" for b in lathe_limb.limb_bones(p[0], RF.required(rig)) or ()} \
                    | {b for p in parts if p[1] == "chain" for b in lathe_limb.chain_bones(p[0], p[5]["bones"]) or ()}
                self.assertFalse(RF.required(rig) - have)
                tris = sum(PF.part_tris(p) for p in parts)
                self.assertGreaterEqual(tris, PF.BUDGETS["mass"][0])
                self.assertLessEqual(tris, 700)

    def test_wings_lean_out_and_mirror(self):
        spec = M.build(REFS / "n00H" / "sheet.jpg", "wyrm")
        plates = {p[0]: p for p in spec["parts"] if p[1] == "plate"}
        self.assertEqual(set(plates), {"wing1.upper", "wing1.lower", "wing2.upper", "wing2.lower"})
        self.assertAlmostEqual(plates["wing1.upper"][3][0], -plates["wing2.upper"][3][0], 3)
        self.assertAlmostEqual(plates["wing1.lower"][5]["rot"][2], -plates["wing2.lower"][5]["rot"][2], 3)

    def test_slot_groups_hand_out_zones_for_the_new_families(self):
        self.assertTrue(set(M.SLOT_GROUPS_FOR) == {"quadruped", "wyrm", "drake"})


if __name__ == "__main__":
    unittest.main()
