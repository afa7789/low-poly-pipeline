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
        self.assertIn("shoulder_span  FAIL", wide)
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
