"""python3 -m unittest discover -s tests/tools/blender"""
import pathlib
import sys
import types
import unittest

import numpy as np

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[3] / "tools/blender"))

import lathe_limb as LL  # noqa: E402
import massing as M  # noqa: E402
import preflight as PF  # noqa: E402
import rig_families as RF  # noqa: E402

REFS = HERE.parents[3] / "artifacts/model-sheets/refs"


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
        self.assertIsNone(M.build(REFS / "n01X/sheet.jpg", "quadruped"))


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


class Surface(unittest.TestCase):
    """PIPELINE 23.L5-5: round heads and boots, the sheet's face, a bent limb only on demand."""

    def test_limb_knee_projects_on_the_axis_and_keeps_the_offset(self):
        g = {"a": (0, 1.0, 0), "b": (0, 0.0, 0), "knee": (0.1, 0.6, 0.2), "r": (0.2, 0.15, 0.1), "sides": 10}
        (part,) = M.emit("leg", "thigh.L", "z1", g)
        self.assertEqual(part[1], "limb")
        self.assertEqual(part[5]["knee"], [0.4, 0.1, 0.2, 0.0])
        self.assertEqual(part[5]["sides"], 8)              # a limb is 6-8 sided, the pre-spec's 10 is for prisms
        self.assertIsNone(LL.bad_opts("limb", part[2], part[5]))

    @unittest.skipUnless((REFS / "n005/sheet.jpg").exists(), "needs the n005 sheet")
    def test_prespec_surface_defaults(self):
        spec = M.build(REFS / "n005/sheet.jpg", "biped", "Human")
        kinds = {p[0]: p for p in spec["parts"]}
        head = kinds["head"]
        self.assertEqual((head[1], head[5]["decal"], head[5]["sides"]), ("lathe", "sheet", 8))
        self.assertEqual([kinds[f"foot.{t}"][5]["sides"] for t in "LR"], [8, 8])
        self.assertFalse(any(p[1] == "limb" for p in spec["parts"]))     # LIMB_KNEE is off
        self.assertTrue(400 <= sum(PF.part_tris(p) for p in spec["parts"]) <= 700)


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


if __name__ == "__main__":
    unittest.main()
