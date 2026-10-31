"""python3 -m unittest discover -s tests/tools/blender"""
import json
import math
import pathlib
import subprocess
import sys
import tempfile
import unittest

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import preflight as PF  # noqa: E402
import rig_families as RF  # noqa: E402


def spider_spec():
    """One prism per spider bone, laid along the bone so every joint touches."""
    parts = []
    for name, _, head, tail in RF.FAMILIES["spider"]:
        if name == "root":
            continue
        mid = [(head[i] + tail[i]) / 2 for i in range(3)]
        mat = ["iron", "darkiron", "brass"][len(parts) % 3]
        r = 0.5 if name == "body" else 0.06     # the body is the mass the legs root in
        parts.append([name, "prism", [r, r, 0.5], mid, mat,
                      {"sides": 6, "from": list(head), "to": list(tail)}])
    return {"rig": "spider", "parts": parts}


def run(spec, kind="mass", sheet=None):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(spec, f)
    argv = [sys.executable, str(ROOT / "tools/blender/preflight.py"), f.name, kind]
    return subprocess.run(argv + ([str(sheet)] if sheet else []), capture_output=True, text=True).stdout


class Family(unittest.TestCase):
    def test_spider_skips_biped_landmarks(self):
        out = run(spider_spec())
        self.assertIn("spider: missing none", out)
        for rule in ("shoulder_span", "fist_span", "stance", "feet_mass"):
            self.assertNotIn(rule, out)

    def test_missing_leg_is_reported(self):
        spec = spider_spec()
        spec["parts"] = [p for p in spec["parts"] if p[0] != "leg5.lower"]
        self.assertIn("missing ['leg5.lower']", run(spec))

    def test_spec_without_rig_is_a_biped(self):
        doc = {"parts": [[name, "prism", [0.1, 0.1, 0.5], [0, 1, 0], "iron", {"from": list(h), "to": list(t)}]
                         for name, _, h, t in RF.BIPED if name != "root"]}
        self.assertIn("shoulder_span", run(doc))          # no "rig" key: biped rules apply


class Palette(unittest.TestCase):
    def test_up_to_eight_slots(self):
        spec = spider_spec()
        names = [f"m{i}" for i in range(8)]
        for i, part in enumerate(spec["parts"]):
            part[4] = names[i % 8]
        spec["palette"] = {n: {"surface": "metal", "color": "#808080"} for n in names}
        self.assertIn("materials      PASS", run(spec))
        spec["parts"][0][4] = "m8"
        spec["palette"]["m8"] = {"surface": "metal", "color": "#808080"}
        self.assertIn("materials      FAIL", run(spec))

    def test_spec_palette_slots_are_valid_materials(self):
        spec = spider_spec()
        names = ["chitin", "moss", "eye"]
        for i, part in enumerate(spec["parts"]):
            part[4] = names[i % 3]
        self.assertIn("materials      FAIL", run(spec))
        spec["palette"] = {"chitin": {"surface": "chitin", "color": "#4E3E39"},
                           "moss": {"surface": "fur", "color": "#62794C"},
                           "eye": {"surface": "glow", "color": "#B3DEAB"}}
        self.assertIn("materials      PASS", run(spec))


class Landmarks(unittest.TestCase):
    def biped(self, half_width):
        """A biped whose every arm part sits half_width out from the centre line."""
        parts = []
        for name, _, h, t in RF.BIPED:
            if name == "root":
                continue
            x = half_width if name.endswith(".L") else -half_width if name.endswith(".R") else 0
            h, t = (x, h[1], h[2]), (x, t[1], t[2])
            parts.append([name, "prism", [0.08, 0.08, 0.5], [x, (h[1] + t[1]) / 2, 0],
                          ["iron", "darkiron", "brass"][len(parts) % 3],
                          {"sides": 6, "from": list(h), "to": list(t)}])
        return parts

    def test_widths_are_read_in_the_sheet_bands(self):
        boxes = [PF.bbox(p) for p in self.biped(0.5)]
        h = max(b[1][1] for b in boxes)
        self.assertAlmostEqual(PF.band_span(boxes, h, PF.BANDS["shoulder_span"]), (0.5 + 0.08) * 2 / h, places=3)

    def test_targets_fall_back_to_n01x(self):
        self.assertEqual(PF.targets_from(None), PF.N01X_TARGETS)

    def test_a_boot_has_a_floor_and_a_ceiling(self):
        # n01X targets: foot 0.228 H -> 0.18-0.32 H. The repair pass used to grow a boot forever.
        h = max(PF.bbox(p)[1][1] for p in self.biped(0.5))

        def feet_mass(length):
            foot = ["foot.L", "box", [0.2, 0.06 * h, length], [0.3, 0.03 * h, 0.0], "iron", {}]
            parts = [p for p in self.biped(0.5) if not p[0].startswith("foot")] + [foot]
            boxes = {id(p): PF.bbox(p) for p in parts}
            return next(c for c in PF.biped_checks(parts, boxes, h, PF.N01X_TARGETS) if c[0] == "feet_mass")
        self.assertTrue(feet_mass(0.25 * h)[1])
        self.assertFalse(feet_mass(0.10 * h)[1])                 # too short
        too_long = feet_mass(0.50 * h)
        self.assertFalse(too_long[1])
        self.assertIn("want 0.18-0.32", too_long[2])

    @unittest.skipUnless((ROOT / "artifacts/model-sheets/refs/hfoo/sheet.jpg").exists(), "refs")
    def test_a_too_wide_footman_fails_its_own_sheet(self):
        sheet = ROOT / "artifacts/model-sheets/refs/hfoo/sheet.jpg"
        wide = run({"parts": self.biped(1.0)}, sheet=sheet)
        self.assertRegex(wide, r"shoulder_span\s+FAIL")
        self.assertIn("sheet 0.46", wide)


class Ground(unittest.TestCase):
    def test_dipping_parts_are_lifted_by_their_dip(self):
        shin = ["shin.L", "prism", [0.1, 0.1, 0.6], [0.3, 0.2, 0], "iron",
                {"from": [0.3, 0.5, 0], "to": [0.3, -0.1, 0]}]
        boot = ["foot.L", "box", [0.2, 0.1, 0.4], [0.3, 0.5, 0.2], "iron", {}]
        self.assertEqual(PF.ground_fix([shin, boot]), ["shin.L"])
        self.assertAlmostEqual(PF.bbox(shin)[0][1], 0.0)
        self.assertEqual(boot[3], [0.3, 0.5, 0.2])                # untouched


class SpanBoxes(unittest.TestCase):
    def test_two_dimension_kinds_placed_from_to(self):
        for kind, dims in (("dome", [0.2, 0.3]), ("wheel", [0.3, 0.05]), ("ring", [0.3, 0.05, 0.04])):
            part = ["head", kind, dims, [0, 1, 0], "iron", {"from": [0, 1, 0], "to": [0, 1.4, 0]}]
            (lo, hi) = PF.bbox(part)
            self.assertAlmostEqual(hi[0] - lo[0], 2 * dims[0], msg=kind)


class Floating(unittest.TestCase):
    def test_detached_child_is_flagged(self):
        parts = spider_spec()["parts"]
        loose = [p for p in parts if p[0] == "leg2.lower"][0]
        loose[5] = {}
        loose[3] = [3.0, 0.3, 3.0]          # far from leg2.upper
        self.assertEqual(PF.floating_parts(parts, RF.parents("spider")), ["leg2.lower"])


    def test_corner_touch_is_loose_at_80_percent(self):
        """boxes that meet only at a corner overlap at full size and not at 80 %"""
        a = ["arm.L", "box", [1, 1, 1], [0, 0, 0], "iron", {}]
        b = ["forearm.L", "box", [1, 1, 1], [0.95, 0.95, 0.95], "iron", {}]
        parents = {"forearm.L": "arm.L"}
        self.assertEqual(PF.floating_parts([a, b], parents), [])
        self.assertEqual(PF.floating_parts([a, b], parents, PF.OVERLAP_SHRINK), ["forearm.L"])


def rule(out, name):
    return [line for line in out.splitlines() if line.strip().startswith(name)][0]


class Shape(unittest.TestCase):
    def test_box_ceiling(self):
        for boxes, want in ((3, "PASS"), (4, "FAIL")):
            spec = spider_spec()
            for p in spec["parts"][:boxes]:
                p[1] = "box"
            spec["parts"] = spec["parts"][:9]       # 3 of 9 is a third; 4 is over
            with self.subTest(boxes=boxes):
                self.assertIn(want, rule(run(spec), "box_ceiling"))

    def test_decal_place(self):
        for bone, want in (("head", "PASS"), ("body", "FAIL")):
            spec = spider_spec()
            part = [p for p in spec["parts"] if p[0] == bone][0]
            part[5]["decal"] = "eyes8"
            with self.subTest(bone=bone):
                self.assertIn(want, rule(run(spec), "decal_place"))


class Props(unittest.TestCase):
    PROPS = [{"name": "tank", "bones": ["spine"], "extent": [0.25, 0.55]},
             {"name": "lantern", "bones": ["pelvis"], "extent": [0.04, 0.15]}]
    TANK = ["spine", "box", [0.4, 0.8, 0.4], [0, 1, 0], "iron", {}]      # 0.8 of H = 2.0: 0.4 H

    def missing(self, parts):
        return PF.props_missing(parts, {id(p): PF.bbox(p) for p in parts}, 2.0, self.PROPS)

    def test_a_part_per_prop_in_its_bracket(self):
        lamp = ["pelvis", "box", [0.2, 0.2, 0.2], [0, 1, 0], "lamp", {}]     # 0.1 H
        self.assertEqual(self.missing([self.TANK, lamp]), [])

    def test_missing_and_oversized_parts_are_reported(self):
        giant = ["pelvis", "box", [0.2, 1.6, 0.2], [0, 1, 0], "lamp", {}]    # 0.8 H: over the ceiling
        self.assertEqual(self.missing([self.TANK, giant]), ["lantern"])
        self.assertEqual(self.missing([self.TANK]), ["lantern"])

    def test_unit_without_props_file_has_none(self):
        self.assertEqual(PF.load_props("no-such-unit"), [])


class PropParts(unittest.TestCase):
    """PIPELINE 23.L5-3: a part with opts prop + anchor is held at its anchor, not sunk in the body."""
    FOREARM = ["forearm.R", "box", [0.2, 0.5, 0.2], [-0.8, 1.2, 0], "iron", {}]      # y 0.95-1.45: hand = y <= 1.15
    TORSO = ["spine", "box", [1.0, 0.8, 0.6], [0, 1.9, 0], "iron", {}]
    PARENTS = {"forearm.R": "arm.R", "spine": "pelvis"}

    def prop(self, bone, anchor, at, dims=(0.1, 0.6, 0.1), name="club"):
        return [bone, "box", list(dims), list(at), "brass", {"prop": name, "anchor": anchor}]

    def test_prop_only_has_to_reach_its_anchor(self):
        for at, want in (([-0.8, 1.0, 0], []), ([-0.8, 1.9, 0], ["forearm.R"]), ([-0.2, 1.0, 0], ["forearm.R"])):
            with self.subTest(at=at):
                parts = [self.FOREARM, self.prop("forearm.R", "hand.R", at)]
                self.assertEqual(PF.floating_parts(parts, self.PARENTS), want)

    def test_a_valve_held_by_its_tank_is_held(self):
        tank = self.prop("spine", "back", [0, 1.9, -0.4], (0.4, 0.8, 0.4), "tank")       # z -0.6..-0.2, y 1.5-2.3
        valve = self.prop("spine", "back", [0, 2.35, -0.4], (0.1, 0.1, 0.1), "tank")
        other = self.prop("spine", "back", [0, 2.35, -0.6], (0.1, 0.1, 0.1), "other")
        self.assertEqual(PF.floating_parts([self.TORSO, tank, valve], self.PARENTS), [])
        self.assertEqual(PF.floating_parts([self.TORSO, tank, other], self.PARENTS), ["spine"])

    def test_clearance_is_the_share_of_the_box_in_the_body(self):
        torso = [PF.bbox(self.TORSO)]                       # z -0.3..0.3
        for z, want in ((-0.4, 0.25), (-0.5, 0.0), (0.0, 1.0)):
            tank = self.prop("spine", "back", [0, 1.9, z], (0.4, 0.8, 0.4), "tank")     # 0.4 deep
            with self.subTest(z=z):
                self.assertAlmostEqual(PF.prop_inside(PF.bbox(tank), torso), want, delta=0.05)

    def test_clearance_is_a_report_until_calibrated(self):
        sunk = self.prop("spine", "back", [0, 1.9, 0], (0.4, 0.8, 0.4), "tank")
        (name, ok, detail), = PF.clearance_checks([self.TORSO, sunk])
        self.assertEqual(name, "prop_clearance")
        self.assertEqual(ok, not PF.CLEARANCE_BLOCKING)
        self.assertIn("tank 100% in the body - OUT", detail)
        self.assertEqual(PF.clearance_checks([self.TORSO]), [])

    def test_a_marked_part_claims_its_prop_first_and_a_prop_has_no_twin(self):
        props = [{"name": "club", "bones": ["forearm.R"], "extent": [0.1, 0.9]}]
        plain = ["forearm.R", "box", [0.2, 0.6, 0.2], [-0.8, 1.2, 0], "iron", {}]
        mark = self.prop("forearm.R", "hand.R", [-0.8, 1.0, 0])
        parts = [plain, mark]
        self.assertEqual(PF.props_missing(parts, {id(p): PF.bbox(p) for p in parts}, 2.0, props), [])
        twin = ["forearm.L", "box", [0.2, 0.6, 0.2], [0.8, 1.2, 0], "iron", {}]
        self.assertEqual(PF.asymmetric([twin, plain, mark]), [])      # the prop is not .R's twin-less extra


class JointPlace(unittest.TestCase):
    def parts(self, knee_y):
        return [["thigh.L", "prism", [0.1, 0.1, 0.5], [0, (knee_y + 1.0) / 2, 0], "iron", {"from": [0, 1.0, 0], "to": [0, knee_y, 0]}],
                ["shin.L", "prism", [0.1, 0.1, 0.5], [0, knee_y / 2, 0], "iron", {"from": [0, knee_y, 0], "to": [0, 0, 0]}]]

    def rule(self, parts, targets):
        boxes = {id(p): PF.bbox(p) for p in parts}
        return PF.joint_checks(parts, boxes, 1.0, targets)

    def test_within_the_band_and_out(self):
        for name, knee_y, out in (("near", 0.5, False), ("far", 0.7, True)):
            with self.subTest(name):
                (rule, ok, detail), = self.rule(self.parts(knee_y), {"knee_h": 0.5})
                self.assertEqual((rule, "OUT" in detail), ("joint_place", out))
                self.assertTrue(ok, "report only")

    def test_silent_without_a_measured_joint(self):
        self.assertEqual(self.rule(self.parts(0.5), {}), [])
        self.assertEqual(self.rule([], {"knee_h": 0.5}), [])

    def test_vlm_joints_compare_all_types(self):
        parts = [["head", "box", [0.2, 0.4, 0.2], [0, 0.8, 0], "iron", {}],
                 ["thigh.L", "box", [0.1, 0.3, 0.1], [0, 0.45, 0], "iron", {}]]
        boxes = {id(p): PF.bbox(p) for p in parts}
        own = PF.own_joints(parts, boxes, 1.0)
        self.assertEqual((round(own["head_top"], 2), round(own["chin"], 2), round(own["hip"], 2)), (1.0, 0.6, 0.6))
        (rule, ok, detail), = PF.joint_checks(parts, boxes, 1.0, {"vlm_joints": {"head_top": 1.0, "hip": 0.8, "wrist": 0.4}})
        self.assertEqual((rule, ok, detail.startswith("2 joints"), "hip 0.60 H (sheet 0.80, +/-0.06) - OUT" in detail),
                         ("joint_place", True, True, True))

    def test_parts_joints_reads_the_sheets_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            (pathlib.Path(tmp) / "parts.json").write_text(json.dumps({"H": 2.0, "joints": {
                "knee.L": {"xyz": [0, 0.5, 0]}, "knee.R": {"xyz": [0, 0.7, 0]}, "elbow.L": {"xyz": None}}}))
            self.assertEqual(PF.parts_joints(pathlib.Path(tmp) / "sheet.jpg"), {"knee": 0.3})
            self.assertEqual(PF.parts_joints(pathlib.Path(tmp) / "x" / "sheet.jpg"), {})

    def test_limb_gives_its_knee_point(self):
        limb = [["thigh.L", "limb", [0.1, 0.1, 0.1], [0, 0.5, 0], "iron", {"from": [0, 1.0, 0], "to": [0, 0, 0], "knee": [0.6, 0, 0]}]]
        self.assertAlmostEqual(PF.joint_height(limb, {id(limb[0]): PF.bbox(limb[0])}, 1.0, "knee_h"), 0.4)


class FamilyPlace(unittest.TestCase):
    def rule(self, z, span):
        parts = [["spine.1", "prism", [0.1, 0.1, 1.0], [0, 0.5, 0], "iron", {"from": [0, 0.5, -z / 2], "to": [0, 0.5, z / 2]}],
                 ["wing1.upper", "plate", [span, 0.2, 0.05], [0, 0.5, 0], "iron", {"axis": "front"}]]
        m = {"len": 1.0, "wing": {"span": 0.5}}
        return PF.family_checks(parts, {id(p): PF.bbox(p) for p in parts}, 1.0, m)

    def test_floor_and_ceiling_are_reported_not_enforced(self):
        for name, z, span, out in (("near", 0.9, 1.0, False), ("short", 0.5, 1.0, True), ("wide", 0.9, 1.6, True)):
            with self.subTest(name):
                (rule, ok, detail), = self.rule(z, span)
                self.assertEqual((rule, ok, "OUT" in detail), ("family_place", True, out))


if __name__ == "__main__":
    unittest.main()


class RotatedBox(unittest.TestCase):
    def part(self, kind="box", **opts):
        return ["arm.L", kind, [0.2, 1.0, 0.2], [0.6, 1.5, 0.0], "iron", opts]

    def test_roll_widens_x_and_keeps_z(self):
        lo, hi = PF.bbox(self.part(rot=[0, 0, 30]))
        c, s = math.cos(math.radians(30)), math.sin(math.radians(30))
        self.assertAlmostEqual(hi[0] - 0.6, 0.1 * c + 0.5 * s)
        self.assertAlmostEqual(hi[1] - 1.5, 0.5 * c + 0.1 * s)
        self.assertAlmostEqual(hi[2], 0.1)

    def test_tip_forward_widens_z(self):
        _, hi = PF.bbox(self.part(rot=[90, 0, 0]))
        self.assertAlmostEqual(hi[2], 0.5)
        self.assertAlmostEqual(hi[1] - 1.5, 0.1)

    def test_scalar_rot_turns_around_forward(self):
        self.assertEqual(PF.bbox(self.part(rot=30)), PF.bbox(self.part(rot=[0, 0, 30])))

    def test_no_rot_and_span_parts_unchanged(self):
        self.assertEqual(PF.bbox(self.part()), PF.bbox(self.part(rot=[0, 0, 0])))
        span = self.part(rot=[0, 0, 40], **{"from": [0, 1, 0], "to": [0, 2, 0]})
        self.assertEqual(PF.bbox(span), PF.bbox(self.part(**{"from": [0, 1, 0], "to": [0, 2, 0]})))

    def test_ground_fix_lifts_by_the_rotated_dip(self):
        part = ["foot.L", "box", [0.2, 0.2, 1.0], [0, 0.1, 0], "iron", {"rot": [90, 0, 0]}]
        PF.ground_fix([part])
        self.assertAlmostEqual(PF.bbox(part)[0][1], 0.0)
        self.assertAlmostEqual(part[3][1], 0.5)


def limb(bone, x, **kw):
    opts = {"rot": [0, 0, 10 if x > 0 else -10], **kw}
    return [bone, "prism", [0.1, 0.1, 0.5], [x, 1.5, 0.0], "iron", opts]


class Symmetry(unittest.TestCase):
    def test_mirrored_twins_pass(self):
        self.assertEqual(PF.asymmetric([limb("arm.L", 0.5), limb("arm.R", -0.5)]), [])

    def test_dims_and_rot_gaps_are_named(self):
        wide = limb("arm.R", -0.5)
        wide[2] = [0.2, 0.1, 0.5]
        self.assertIn("dims", PF.asymmetric([limb("arm.L", 0.5), wide])[0])
        same_rot = limb("arm.R", -0.5)
        same_rot[5]["rot"] = [0, 0, 10]
        self.assertIn("rot", PF.asymmetric([limb("arm.L", 0.5), same_rot])[0])

    def test_asym_and_unpaired_parts(self):
        held = limb("forearm.R", -0.5)
        extra = limb("forearm.R", -0.5)
        pair = [limb("forearm.L", 0.5), held, extra]
        self.assertIn("1 parts left, 2 right", PF.asymmetric(pair)[0])
        extra[5]["asym"] = True
        self.assertEqual(PF.asymmetric(pair), [])


class RoundKinds(unittest.TestCase):
    def test_tris_follow_sides(self):
        """Eight sides by default (PIPELINE 23.L5-5); a frustum stays a box until it asks for sides."""
        for name, kind, dims, opts, want in [
                ("cyl default", "cyl", [0.1, 1.0], {}, 28), ("cyl 12", "cyl", [0.1, 1.0], {"sides": 12}, 44),
                ("frustum box", "frustum", [1, 1, 1], {}, 12), ("frustum 8", "frustum", [1, 1, 1], {"sides": 8}, 28),
                ("prism default", "prism", [0.1, 0.1, 1], {}, 28)]:
            with self.subTest(name):
                self.assertEqual(PF.part_tris(["b", kind, dims, [0, 0, 0], "iron", opts]), want)

    def test_round_frustum_keeps_the_box(self):
        box = PF.bbox(["foot.L", "frustum", [0.2, 0.1, 0.4], [0, 0.05, 0], "iron", {"top": [0.9, 0.8], "sides": 8}])
        self.assertAlmostEqual(box[1][0] - box[0][0], 0.2)
        self.assertAlmostEqual(box[1][2] - box[0][2], 0.4)


class BudgetSplit(unittest.TestCase):
    def test_band_blends_sheet_area_and_prior(self):
        n01x = PF.split_bands(PF.N01X_TARGETS)
        wide_head = PF.split_bands({**PF.N01X_TARGETS, "area_head": 0.3, "area_body": 0.2})
        self.assertGreater(wide_head[0][1], n01x[0][1])
        self.assertTrue(all(lo <= hi for lo, hi in n01x))

    def test_salience_replaces_the_prior_only_when_switched_on(self):
        t = {**PF.N01X_TARGETS, "edge_head": 0.5, "edge_body": 0.3, "edge_legs": 0.2}
        self.assertEqual(PF.split_bands(t), PF.split_bands(PF.N01X_TARGETS))
        PF.SPLIT_SALIENCE = True
        try:
            self.assertNotEqual(PF.split_bands(t), PF.split_bands(PF.N01X_TARGETS))
        finally:
            PF.SPLIT_SALIENCE = False

    def test_ornament_is_not_a_head_cost(self):
        wheel = ["head", "ring", [0.3, 0.05, 0.02], [0, 2, 0], "iron", {"sides": 10}]
        torso = ["spine", "box", [1, 1, 1], [0, 1, 0], "iron", {}]
        self.assertEqual(PF.split_shares([wheel, torso]), [0.0, 1.0, 0.0])


class Normalise(unittest.TestCase):
    def parts(self):
        return [["foot.R", "box", [0.2, 0.1, 0.4], [-0.3, 0.0501, 0.1], "iron", {}],
                ["head", "box", [0.5, 0.5, 0.5], [0, 2.5, 0], "iron", {}],
                ["foot.L", "box", [0.2, 0.1, 0.4], [0.3, 0.0501, 0.1], "iron", {}],
                ["spine", "prism", [0.3, 0.3, 0.6], [0, 1.4, 0], "iron", {"from": [0, 1.1, 0], "to": [0, 1.7, 0.001]}]]

    def test_grid_order_and_pairs_adjacent(self):
        out = PF.normalise(self.parts(), "biped")
        self.assertEqual([p[0] for p in out], ["spine", "head", "foot.L", "foot.R"])
        q = RF.top("biped") / 256
        self.assertTrue(all(abs(v / q - round(v / q)) < 1e-3 for p in out for v in p[3]))
        self.assertEqual(out[2][3][0], -out[3][3][0])

    def test_idempotent_and_order_independent(self):
        once = PF.normalise(self.parts())
        self.assertEqual(PF.normalise([list(p) for p in reversed(once)]), once)


class OutsideHull(unittest.TestCase):
    """Front 0.4 m wide, left 0.2 m deep, both 1 m tall (pad 0: the masks are the hull)."""
    masks = [(np.ones((100, 40), bool), 0), (np.ones((100, 20), bool), 0)]

    def box(self, bone, dims, at):
        return [bone, "box", dims, at, "iron", {}]

    def test_inside_passes_and_names_the_direction(self):
        body = self.box("spine", [0.4, 1.0, 0.2], [0, 0.5, 0])
        fat = [self.box("spine", [0.4, 1.0, 0.2], [0, 0.5, 0]), self.box("arm.L", [0.8, 0.1, 0.1], [0, 0.5, 0])]
        deep = [self.box("spine", [0.4, 1.0, 0.2], [0, 0.5, 0]), self.box("head", [0.1, 0.1, 0.8], [0, 0.5, 0])]
        self.assertEqual(PF.hull_outside([body], self.masks, 1.0), {})
        self.assertEqual(PF.hull_outside(fat, self.masks, 1.0)["arm.L"][1], "wide")
        self.assertEqual(PF.hull_outside(deep, self.masks, 1.0)["head"][1], "deep")

    def test_ornament_has_no_samples_and_leaning_limb_follows_its_axis(self):
        ring = ["head", "ring", [0.5, 0.05, 0.02], [0, 2, 0], "iron", {}]
        self.assertEqual(len(PF.sample_points(ring, 0.1)), 0)
        arm = ["arm.L", "prism", [0.05, 0.05, 1], [0, 0.5, 0], "iron", {"from": [0, 0, 0], "to": [1, 1, 0]}]
        pts = PF.sample_points(arm, 0.1)
        self.assertTrue(np.allclose(pts[:, 0], pts[:, 1]))


class SpiderRules(unittest.TestCase):
    MEASURE = {"body_r": 0.3, "body_len": 0.8, "body_under": 0.25, "knee_h": 0.45, "knee_r": 0.6, "foot_r": 0.45}

    def rules(self, measure):
        parts = spider_spec()["parts"]
        boxes = {id(p): PF.bbox(p) for p in parts}
        height = max(b[1][1] for b in boxes.values())
        return {name: (ok, detail) for name, ok, detail in PF.spider_checks(parts, boxes, height, measure)}

    def test_only_the_leg_rule_blocks_and_all_three_name_the_numbers(self):
        big = {**self.MEASURE, "knee_r": 3.0, "foot_r": 3.0, "body_r": 2.0}   # a sheet far bigger than the fixed spider
        got = self.rules(big)
        self.assertEqual(set(got), {"spider_body", "spider_reach", "spider_leg"})
        self.assertFalse(got["spider_leg"][0])
        self.assertTrue(got["spider_body"][0] and got["spider_reach"][0])      # report only
        self.assertTrue(all("OUT" in got[r][1] for r in got))
        self.assertIn("vs sheet", got["spider_leg"][1])

    def test_a_limb_leg_counts_through_its_knee(self):
        """a limb from hip to foot with the knee far off the chord is longer than its chord"""
        limb = ["leg1.upper", "limb", [0.05, 0.05, 0.05], [0, 0, 0], "iron",
                {"from": [0, 0, 0], "to": [0, 0, 1.0], "knee": [0.5, 0.5, 0.0, 0.0]}]
        self.assertAlmostEqual(PF.leg_length(limb), 2 * math.hypot(0.5, 0.5))
        self.assertAlmostEqual(PF.leg_length(["b", "prism", [1, 1, 1], [0, 0, 0], "iron", {"from": [0, 0, 0], "to": [0, 0, 2]}]), 2.0)

    def test_leg_w_reports_thin_legs_without_blocking(self):
        parts = spider_spec()["parts"]
        r = PF.leg_radius([p for p in parts if p[0].startswith("leg")][0])
        height = max(PF.bbox(p)[1][1] for p in parts)
        for name, leg_w, ok in [("matches", r / height, True), ("sheet twice as thick", 2.5 * r / height, False)]:
            with self.subTest(name):
                got = self.rules({**self.MEASURE, "leg_w": leg_w})["spider_leg_w"]
                self.assertTrue(got[0], "report only")
                self.assertEqual("OUT" in got[1], not ok)
        self.assertNotIn("spider_leg_w", self.rules(self.MEASURE))


class Identity(unittest.TestCase):
    """identity_items / identity_rows / identity_status (PIPELINE 23.L5-6), no sheet needed."""
    PARTS = [["head", "frustum", [0.3, 0.3, 0.3], [0, 2, 0], "hood", {"decal": "sheet", "decal_color": "#8A2A35"}],
             ["pelvis", "box", [0.1, 0.1, 0.1], [0.3, 1, 0], "lantern", {}],
             ["spine", "box", [0.5, 0.8, 0.5], [0, 1.5, 0], "tank", {}]]
    DOC = {"palette": {"hood": {"color": "#2E2D30"}, "lantern": {"color": "#5A6AA8"}, "tank": {"color": "#64686E"}}}

    def test_checklist_sources(self):
        fixture = ROOT / "tests/tools/blender/fixtures/parts-n005.json"
        kinds = [i["kind"] for i in PF.identity_items("n005", parts_path=fixture)]
        self.assertEqual(kinds, ["eyes", "text", "prop", "prop", "prop"])   # tank, lantern, vaporiser -> their props.json entries
        self.assertEqual([i["kind"] for i in PF.identity_items("n005", parts_path="/nowhere")],
                         ["prop", "prop", "prop"])                           # props.json, no eyes without a list (L18-0)
        self.assertEqual([i["kind"] for i in PF.identity_items("n005", biped=False, parts_path="/nowhere")],
                         ["prop"] * 3)

    def test_face_kind_of_the_eight_sheets(self):
        """L18-0: the identity list says what the face has; the eight real lists, no list, an empty one, and the items that follow."""
        want = {"hfoo": "none", "n005": "lenses", "n00U": "eyes", "n00H": "eyes", "n02X": "lenses", "n017": "eyes", "n010": "none", "n01X": "none"}
        for unit, kind in want.items():
            with self.subTest(unit=unit):
                texts = PF.identity_texts(unit)
                self.assertIsNotNone(texts)
                self.assertEqual(PF.face_kind(texts), kind)
                eyes = [i for i in PF.identity_items(unit) if i["kind"] == "eyes"]
                self.assertEqual(bool(eyes), kind != "none")
        for texts, kind in ((None, "none"), ([], "none"), (["dark brown globular body"], "none"), (["a brow"], "eyes"),
                            (["two eyes", "no face or glass"], "none"), (["blue-glass belt lantern"], "none"), (["single glowing cyan lens"], "lenses")):
            with self.subTest(texts=texts):
                self.assertEqual(PF.face_kind(texts), kind)

    def test_rows_and_status(self):
        blue = {"name": "blue detail #586B87", "kind": "zone", "hex": "#586B87"}
        red = {"name": "red detail #50252E", "kind": "zone", "hex": "#50252E"}
        gold = {"name": "orange detail #89704B", "kind": "zone", "hex": "#89704B"}
        items = [{"name": "eyes", "kind": "eyes"}, {"name": "tank", "kind": "prop"}, blue, red, gold,
                 {"name": "whatever", "kind": "text"}]
        rows = PF.identity_rows(items, self.PARTS, self.DOC, ["tank"])
        self.assertEqual([(r["name"], r["present"], r["via"]) for r in rows],
                         [("eyes", True, "decal"), ("tank", False, "part"), (blue["name"], True, "material"),
                          (red["name"], True, "decal"), (gold["name"], False, None)])   # text is not scored
        self.assertEqual(PF.identity_status(rows)["missing"], ["tank", gold["name"]])
        read = PF.identity_status(rows, [{"hex": "#586B87", "ratio": 0.2, "read": False}])
        self.assertIn("blue detail #586B87 (not in the render: 20% of the sheet's area)", read["missing"])
        self.assertEqual((read["ok"], read["total"]), (2, 5))
