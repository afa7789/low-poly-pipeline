"""python3 -m unittest discover -s tests/tools/blender"""
import os
import pathlib
import sys
import json
import types
import unittest
from unittest import mock

import numpy as np

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[3] / "tools/blender"))

import lathe_limb  # noqa: E402
import lathe_limb as LL  # noqa: E402
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

    def test_ring_stack_is_one_lathe_through_the_breakpoints(self):
        g = {"y0": 0.0, "y1": 1.0, "w": lambda y: 1.0 if y < 0.5 else 0.6, "d": lambda y: 0.4, "zc": lambda y: 0.1 * y}
        (part,) = M._ring_stack("torso", "spine", "z1", g)
        rings = part[5]["profile"]
        self.assertEqual(part[1], "lathe")
        self.assertTrue(3 <= len(rings) <= 6)
        self.assertEqual(max(q[0] for q in rings), 1.0)                      # r = the widest half width
        self.assertEqual([q[4] for q in rings], sorted(q[4] for q in rings))
        self.assertGreater(part[2][1], 1.0)                                  # the end rings moved out to overlap the neighbours
        self.assertIsNone(LL.bad_opts("lathe", part[2], part[5]))

    def test_emit_uses_rings_for_the_trunk_unless_stack_lathe_is_off(self):
        g = {"y0": 0.0, "y1": 1.0, "w": lambda y: 1.0, "d": lambda y: 0.5, "zc": lambda y: 0.0}
        saved = M.STACK_LATHE
        try:
            for flag, kind in ((True, "lathe"), (False, "frustum")):
                with self.subTest(flag):
                    M.STACK_LATHE = flag
                    self.assertEqual({p[1] for p in M.emit("torso", "spine", "z1", g)}, {kind})
        finally:
            M.STACK_LATHE = saved

    def test_emit_falls_back_for_a_kind_without_emitter(self):
        saved = dict(M.KIND_FOR)
        try:
            M.KIND_FOR["torso"] = "dome"                 # a kind with no emitter
            M.STACK_LATHE = False
            g = {"y0": 0.0, "y1": 1.0, "w": lambda y: 1.0, "d": lambda y: 1.0, "zc": lambda y: 0.0}
            self.assertEqual(M.emit("torso", "spine", "z1", g)[0][1], "frustum")
        finally:
            M.KIND_FOR.update(saved)
            M.STACK_LATHE = True


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
        have = {p[0] for p in spec["parts"]} | {b for p in spec["parts"] if p[1] == "limb" for b in lathe_limb.limb_bones(p[0], RF.required("biped")) or ()}
        self.assertTrue(RF.required("biped") <= have)           # n01X has a parts.json: legs are limbs
        self.assertGreaterEqual(sum(PF.part_tris(p) for p in spec["parts"]), 400)
        doc = {"rig": "biped", "palette": spec["palette"]}
        checks = PF.checks_of(spec["parts"], doc, "mass", PF.targets_from(sheet), PF.load_props("n01X"), sheet)
        self.assertEqual([c[0] for c in checks if not c[1]], [])

    def test_other_families_have_no_massing(self):
        self.assertIsNone(M.build(REFS / "n01X/sheet.jpg", "vehicle"))


@unittest.skipUnless((REFS / "n005/sheet-hard.jpg").exists(), "needs the n005 sheet")
class PartsBuild(unittest.TestCase):
    """PIPELINE 23.L5-2 / 23.L5-2b: refs/<id>/parts.json drives the pre-spec; without it the band massing is unchanged."""

    def setUp(self):
        self.sheet, self.hard = REFS / "n005/sheet.jpg", REFS / "n005/sheet-hard.jpg"
        self.doc = json.loads((FIXTURES / "parts-n005.json").read_text())

    def test_one_piece_per_part_and_no_parts_is_the_band_massing(self):
        band = M.build(self.sheet, "biped", "Human", self.hard, parts=False)
        spec = M.build(self.sheet, "biped", "Human", self.hard, parts=self.doc)
        self.assertLessEqual({"lathe", "limb", "prism", "box", "frustum"}, {p[1] for p in spec["parts"]})
        tank = [p for p in spec["parts"] if p[1] == "lathe" and p[0] == "spine" and p[5].get("asym")]
        self.assertEqual(len(tank), 1)                                    # the tank is its own lathe on the spine
        (torso,) = [p for p in spec["parts"] if p[1] == "lathe" and p[0] == "spine" and not p[5].get("asym")]
        self.assertTrue(lathe_limb.is_ring_profile(torso[5]["profile"]))   # and the torso one ring lathe (L6-1), not a stack
        self.assertLess(tank[0][3][2], -0.5)                              # behind the torso
        self.assertTrue(any(p[1] == "plate" and p[0] == "forearm.L" for p in spec["parts"]))   # the held weapon: a plate (24.L6-3)
        self.assertNotEqual(spec, band)
        self.assertTrue(M.PARTS_MASSING)                                  # on by default: parts.json of the sheet's folder is read

    def test_a_group_parts_json_lacks_comes_from_the_band_massing(self):
        self.doc["parts"] = [q for q in self.doc["parts"] if q["role"] != "leg"]
        band = M.build(self.sheet, "biped", "Human", self.hard, parts=False)["parts"]
        got = M.build(self.sheet, "biped", "Human", self.hard, parts=self.doc)["parts"]
        legs = lambda parts: [(p[0], p[1], p[5]["from"], p[5]["to"]) for p in parts if p[0].split(".")[0] in ("thigh", "shin")]   # noqa: E731
        self.assertEqual(legs(got), legs(band))
        self.assertTrue(any(p[1] == "lathe" and p[0] == "head" for p in got))   # the head is still the part's lathe

    def test_limb_knee_comes_from_the_joints(self):
        leg = next(q for q in self.doc["parts"] if q["bone"] == "thigh.L")
        part = M.limb_part(leg, "z1", self.doc, 8, ("hip", "knee", "ankle"))[0]
        self.assertEqual(part[1], "limb")
        knee = M.lathe_limb.knee_of(part[5])
        for got, want in zip(knee, self.doc["joints"]["knee.L"]["xyz"]):
            self.assertAlmostEqual(got, want, 2)

    def test_non_bipeds_never_read_parts_json(self):
        saved, M.load_parts = M.load_parts, lambda sheet: self.fail("a spider read parts.json")
        try:
            self.assertTrue(M.build(REFS / "n00U/sheet.jpg", "spider")["parts"])
        finally:
            M.load_parts = saved


class Conform(unittest.TestCase):
    """PIPELINE 23.L5-2b: the VLM's boxes are made symmetric, centred and cut to the sheet before they become parts."""

    def doc(self):
        j = lambda x, y: {"xyz": [x, y, 0.0]}   # noqa: E731
        return {"H": 2.0, "joints": {"shoulder.L": j(0.6, 1.5), "shoulder.R": j(-0.4, 1.5), "elbow.L": j(0.7, 1.0), "elbow.R": j(-0.5, 1.0),
                                     "wrist.L": j(0.7, 0.6), "wrist.R": j(-0.5, 0.6), "head_top": j(0.1, 2.0)},
                "parts": [{"name": "arm L", "role": "arm", "bone": "arm.L", "box3d": [[0.5, 1.0, -0.1], [0.9, 1.5, 0.1]]},
                          {"name": "arm R", "role": "arm", "bone": "arm.R", "box3d": [[-0.9, 1.0, -0.3], [-0.1, 1.5, 0.3]]},
                          {"name": "pike", "role": "prop", "bone": "forearm.R", "prop": True, "box3d": [[-0.6, 0.1, 0], [-0.5, 1.9, 0.1]]}]}

    def test_centred_mirrored_and_the_better_read_side_wins(self):
        S = M.symmetric_doc(self.doc())
        self.assertAlmostEqual(S["joints"]["shoulder.L"]["xyz"][0], 0.5)           # centre line was 0.1 off
        self.assertEqual(S["joints"]["shoulder.R"]["xyz"][0], -S["joints"]["shoulder.L"]["xyz"][0])
        self.assertEqual(S["joints"]["head_top"]["xyz"][0], 0.0)
        arms = {p["bone"]: p["box3d"] for p in S["parts"] if p["role"] == "arm"}
        self.assertEqual(arms["arm.R"], [[-arms["arm.L"][1][0], 1.0, -0.3], [-arms["arm.L"][0][0], 1.5, 0.3]])   # R holds its elbow, L does not
        self.assertEqual(len([p for p in S["parts"] if p["role"] == "prop"]), 1)    # a prop is moved, not mirrored
        self.assertAlmostEqual(next(p for p in S["parts"] if p["role"] == "prop")["box3d"][0][0], -0.7)

    def test_a_part_past_the_band_ceiling_moves_in(self):
        part = ["forearm.R", "box", [0.1, 1.8, 0.1], [-0.9, 1.0, 0.0], "z1", {"asym": True}]
        targets = {"shoulder_span": 0.4, "fist_span": 0.4, "stance": 0.4}
        M.clamp_widths([part, ["head", "box", [0.2, 0.2, 0.2], [0.0, 1.9, 0.0], "z1", {}]], targets)
        self.assertLessEqual(-PF.bbox(part)[0][0], M.MARGIN * (1 + PF.TOLERANCE) * 0.4 * 2.0 / 2 + 1e-6)

    def test_budget_split_trades_sides(self):
        targets = {"area_head": 0.1, "area_body": 0.4, "area_legs": 0.5}
        legs = [["thigh.L", "limb", [0.1, 0.1, 0.1], [0, 0, 0], "z1", {"sides": 6, "from": [0, 1, 0], "to": [0, 0, 0]}]]
        arms = [["arm.L", "prism", [0.1, 0.1, 1], [0, 0, 0], "z1", {"sides": 10, "from": [0, 1, 0], "to": [0, 0, 0]}] for _ in range(6)]
        head = [["head", "lathe", [0.2, 0.3], [0, 2, 0], "z1", {"sides": 6, "profile": [1] * 6}]]
        groups = {"head": head, "trunk": [], "arms": arms, "legs": legs, "props": []}
        M.balance(groups, targets)
        self.assertGreater(legs[0][5]["sides"], 6)                                  # the legs, far under their band, took sides


@unittest.skipUnless(os.environ.get("SLOW") and (REFS / "n02X/sheet.jpg").exists(), "SLOW=1: the 4 biped sheets, ~15 s")
class RealParts(unittest.TestCase):
    """PIPELINE 23.L5-2b: the real parts.json of the four bipeds clears every preflight rule, with no group falling back."""

    def test_preflight_passes_on_the_four_bipeds(self):
        import spec_pipeline as SP
        for unit in ("n005", "n01X", "n02X", "hfoo"):
            with self.subTest(unit):
                sheet = REFS / unit / "sheet.jpg"
                spec = SP.parse_spec(json.dumps(M.build(sheet, "biped", "Human", REFS / unit / "sheet-hard.jpg")))
                parts, doc = spec["parts"], spec
                RF.scale_rig("biped", None)
                checks = PF.checks_of(parts, doc, "mass", PF.targets_from(sheet), PF.load_props(unit), sheet)
                self.assertEqual([n for n, ok, _ in checks if not ok], [])


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
        # the parts massing (23.L5-2b) draws legs as limbs bent at parts.json's knee; every limb is well-formed
        self.assertTrue(all(LL.bad_opts("limb", p[2], p[5]) is None for p in spec["parts"] if p[1] == "limb"))
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


class Families(unittest.TestCase):
    """The pre-spec of the three new body plans, on their real sheets (PIPELINE 22.L4-4b)."""

    def tearDown(self):
        RF.FAMILIES.update(RF.FIXED)
        RF._drop_caches()

    def test_each_unit_covers_its_bones_inside_the_budget(self):
        for unit, rig, kinds in (("n017", "quadruped", {"lathe", "limb", "chain"}), ("n00H", "wyrm", {"chain", "plate", "prism"}),
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

    def test_trunk_is_one_lathe_along_z_per_spine_bone(self):
        for unit, rig in (("n017", "quadruped"), ("n010", "drake")):
            with self.subTest(unit):
                trunk = [p for p in M.build(REFS / unit / "sheet.jpg", rig)["parts"] if p[1] == "lathe"]
                self.assertEqual(sorted(p[0] for p in trunk), ["spine.1", "spine.2"])
                self.assertTrue(all(p[5]["axis"] == "z" and lathe_limb.bad_opts("lathe", p[2], p[5]) is None for p in trunk))
                back, front = sorted(trunk, key=lambda p: p[3][2])
                self.assertGreater(back[3][2] + back[2][1] / 2, front[3][2] - front[2][1] / 2)       # they overlap

    def test_wings_lean_out_and_mirror(self):
        spec = M.build(REFS / "n00H" / "sheet.jpg", "wyrm")
        plates = {p[0]: p for p in spec["parts"] if p[1] == "plate"}
        self.assertEqual(set(plates), {"wing1.upper", "wing1.lower", "wing2.upper", "wing2.lower"})
        self.assertAlmostEqual(plates["wing1.upper"][3][0], -plates["wing2.upper"][3][0], 3)
        self.assertAlmostEqual(plates["wing1.lower"][5]["rot"][2], -plates["wing2.lower"][5]["rot"][2], 3)

    def test_slot_groups_hand_out_zones_for_the_new_families(self):
        self.assertTrue(set(M.SLOT_GROUPS_FOR) == {"quadruped", "wyrm", "drake"})


class Props(unittest.TestCase):
    """PIPELINE 24.L6-3: a prop is a lathe, a plate or a pole by name, marked on its anchor, pushed out of the body."""

    def part(self, name, lo, hi, bone="forearm.R", anchor="hand.R"):
        return {"name": name, "role": "prop", "bone": bone, "anchor": anchor, "prop": True, "box3d": [lo, hi]}

    def panel(self, lean=0):
        """A 180 px figure facing +columns (toe stub at the feet); lean +1: a pole from col 30 to 190 rising toward
        the higher columns (the front), -1: falling."""
        m = np.zeros((200, 220), bool)
        m[10:190, 100:120] = True
        m[180:190, 100:140] = True
        for k in range(161 if lean else 0):
            row = 154 - k * 135 // 160 if lean > 0 else 19 + k * 135 // 160
            m[row:row + 3, 30 + k] = True
        return m

    def test_prop_kind_follows_the_name(self):
        front, side = M.View(self.panel(), 2.0), M.side_of(self.panel(), 2.0)
        low, high = [-0.2, 1.0, -0.2], [0.2, 1.4, 0.2]
        for name, want in (("drill-pipe club", "prism"), ("shield", "plate"), ("pressure tank", "lathe"), ("belt lantern", "box")):
            with self.subTest(name):
                box = ([-0.05, 0.1, -0.8], [0.05, 1.9, 0.8]) if want == "prism" else (low, high)
                rows = M.prop_rows(self.part(name, *box), "s", front, side, 8)
                self.assertEqual(rows[0][1], want)
                self.assertEqual((rows[0][5]["prop"], rows[0][5]["anchor"]), (name, "hand.R"))

    def test_plate_is_thin_along_the_shallower_axis(self):
        rows = M.plate_part(self.part("shield", [-0.3, 1.0, -0.05], [0.3, 1.5, 0.05]), "s")
        self.assertEqual((rows[0][1], rows[0][5]["axis"]), ("plate", "front"))
        rows = M.plate_part(self.part("pistol", [-0.05, 1.0, -0.3], [0.05, 1.2, 0.3]), "s")
        self.assertEqual(rows[0][5]["axis"], "left")

    def test_hull_profile_is_a_small_polygon_in_unit_box(self):
        m = np.zeros((40, 40), bool)
        m[5:35, 10:20] = True
        prof = M.hull_profile(m, keep=4)
        self.assertLessEqual(len(prof), 4)
        self.assertEqual((min(u for u, _ in prof), max(u for u, _ in prof), min(v for _, v in prof), max(v for _, v in prof)), (0, 1, 0, 1))

    def test_upright_author_pole_is_leant_with_its_head(self):
        """PIPELINE 25.L7-4: shaft and spear head turn together about the shaft's foot, to the diagonal of parts.json's box."""
        part = self.part("pike", [-0.05, 0.4, -0.8], [0.05, 1.9, 0.8])
        shaft = ["forearm.R", "prism", [0.04, 0.04, 1.5], [0, 0, 0], "s", {"from": [0, 0.4, 0], "to": [0, 1.9, 0], "prop": "pike"}]
        head = ["forearm.R", "prism", [0.08, 0.01, 0.3], [0, 0, 0], "s", {"from": [0, 1.9, 0], "to": [0, 2.2, 0], "prop": "pike"}]
        other = ["spine", "box", [1, 1, 1], [0, 1, 0], "s", {}]
        for lean in (1, -1):
            with self.subTest(lean):
                out = M.lean_poles({"parts": [other, shaft, head]}, {"parts": [part]}, M.side_of(self.panel(lean), 2.0))["parts"]
                self.assertEqual(out[0], other)
                (a, b), (c, d) = ((r[5]["from"], r[5]["to"]) for r in out[1:])
                self.assertEqual(a, [0.0, 0.4, -0.8 * lean])                          # the foot goes to the box's corner, x stays
                self.assertEqual(c, b)                                                  # the head still sits on the tip
                self.assertAlmostEqual(d[1], 2.2, 3)                                    # the top keeps its height
                self.assertAlmostEqual((b[2] - a[2]) / (b[1] - a[1]), lean * 1.6 / 1.5, 3)   # the diagonal of the box
                self.assertEqual((b[0], d[0]), (0.0, 0.0))

    def test_pole_leans_where_the_sheet_leans(self):
        part = self.part("pike", [-0.05, 0.4, -0.8], [0.05, 1.9, 0.8])
        for lean in (1, -1):
            with self.subTest(lean):
                self.assertEqual(M.pole_lean(part, M.side_of(self.panel(lean), 2.0)), lean)
        self.assertEqual(M.pole_lean(part, M.side_of(self.panel(), 2.0)), 1)          # no pole drawn: forward, as before

    def test_clear_props_pushes_out_by_the_gap_and_keeps_the_prop_whole(self):
        torso = ["spine", "box", [1.0, 0.8, 0.6], [0, 1.9, 0], "s", {}]
        tank = ["spine", "box", [0.4, 0.8, 0.4], [0, 1.9, -0.2], "s", {"prop": "tank", "anchor": "back"}]
        valve = ["spine", "box", [0.1, 0.1, 0.1], [0, 2.35, -0.2], "s", {"prop": "tank", "anchor": "back"}]
        PF.clear_props([torso, tank, valve], 2.0)
        lo, hi = PF.bbox(tank)
        self.assertGreaterEqual(-0.3 - hi[2], PF.PROP_GAP * 2.0 - 1e-6)           # behind the torso's back face, by the gap
        self.assertAlmostEqual(PF.bbox(valve)[0][2] - lo[2], -0.25 - -0.4, 3)       # the valve moved with it
        self.assertEqual(PF.loose_props([torso, tank, valve], {"spine"}), [])

    def test_worn_part_is_not_a_prop(self):
        torso = ["spine", "box", [1.0, 0.8, 0.6], [0, 1.9, 0], "s", {}]
        belt = ["spine", "box", [1.1, 0.2, 0.7], [0, 1.9, 0], "s", {"prop": "belt", "anchor": "belt"}]
        pad = ["arm.L", "box", [0.3, 0.3, 0.3], [0.8, 2.1, 0], "s", {"prop": "pad", "anchor": "shoulder.L"}]
        flask = ["forearm.L", "box", [0.1, 0.3, 0.1], [1.2, 1.0, 0], "s", {"prop": "flask", "anchor": "hand.L"}]
        M.unmark_worn([torso, belt, pad, flask])
        self.assertEqual([PF.is_prop(p) for p in (belt, pad, flask)], [False, False, True])

    def test_touching_props_of_one_anchor_share_a_name(self):
        club = ["forearm.R", "box", [0.2, 1.6, 0.2], [0, 1.0, 0], "s", {"prop": "club", "anchor": "hand.R"}]
        disc = ["forearm.R", "box", [0.3, 0.05, 0.3], [0, 1.8, 0], "s", {"prop": "disc", "anchor": "hand.R"}]
        far = ["forearm.R", "box", [0.1, 0.1, 0.1], [2, 0, 0], "s", {"prop": "far", "anchor": "hand.R"}]
        M.merge_props([disc, club, far])
        self.assertEqual((disc[5]["prop"], far[5]["prop"]), ("club", "far"))


@unittest.skipUnless((REFS / "n00U/sheet.jpg").exists(), "needs the n00U sheet")
class TopLegs(unittest.TestCase):
    def test_spider_legs_are_limbs_bent_at_the_top_panels_knee(self):
        sheet = REFS / "n00U/sheet.jpg"
        fixed = list(RF.FAMILIES["spider"])
        try:
            with mock.patch.object(RF, "TOP_LEGS", True):
                RF.scale_rig("spider", __import__("silhouette").measure_rig("spider", sheet))
                parts = M.build(sheet, "spider", "Nature")["parts"]
        finally:
            RF.FAMILIES["spider"] = fixed
            RF._drop_caches()
        legs = [p for p in parts if p[0].startswith("leg")]
        self.assertEqual([p[1] for p in legs], ["limb"] * 8)
        self.assertEqual(len({tuple(p[5]["to"][::2]) for p in legs}), 8)       # eight different feet: not the rig's ring
        self.assertTrue(all(p[5]["knee"][3] != 0 or p[5]["knee"][1] != 0 for p in legs))


if __name__ == "__main__":
    unittest.main()


class CleanSideTest(unittest.TestCase):
    def test_an_asymmetric_front_is_read_from_the_side_without_the_prop(self):
        m = np.zeros((40, 50), bool)
        m[:, 15:25] = True                      # body, feet centred on column 20
        m[10:20, 25:45] = True                  # a club on the +x (image right) side
        flipped = M.clean_side(m)
        self.assertTrue(flipped[10:20, 5:25].all())
        self.assertIs(M.clean_side(flipped), flipped)          # the heavy side is -x now: kept
        sym = np.zeros((40, 50), bool)
        sym[:, 15:35] = True
        self.assertIs(M.clean_side(sym), sym)
