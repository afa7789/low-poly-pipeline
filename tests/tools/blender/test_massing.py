"""python3 -m unittest discover -s tests/tools/blender"""
import pathlib
import sys
import types
import unittest

import numpy as np

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[3] / "tools/blender"))

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
            M.KIND_FOR["torso"] = "lathe"                # F2 not registered yet
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
