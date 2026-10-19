"""python3 -m unittest discover -s tests/tools/blender"""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import spec_pipeline as SP  # noqa: E402

PARTS = [
    ["spine", "prism", [0.4, 0.4, 0.8], [0, 1.8, 0], "iron", {"sides": 8}],
    ["head", "box", [0.2, 0.2, 0.2], [0, 2.4, 0], "iron", {}],
    ["pelvis", "frustum", [0.5, 0.3, 0.3], [0, 1.3, 0], "darkiron", {}],
]


def reply(patch):
    return "here you go\n" + json.dumps(patch)


class ApplyPatch(unittest.TestCase):
    def test_set_drop_add_keep_the_rest(self):
        new = ["head", "box", [0.3, 0.2, 0.2], [0, 2.4, 0], "brass", {}]
        extra = ["spine", "box", [0.1, 0.1, 0.1], [0, 1.9, 0.3], "lamp", {}]
        parts, why = SP.apply_patch(PARTS, reply({"set": {"1": new}, "drop": [2],
                                                  "add": [extra], "why": "wider head"}))
        self.assertEqual(parts, [PARTS[0], new, extra])
        self.assertEqual(why, "wider head")

    def test_too_many_edits_is_rejected(self):
        drops = list(range(SP.PASS_EDITS + 1))
        with self.assertRaises(ValueError):
            SP.apply_patch(PARTS, reply({"drop": drops}))

    def test_repair_limit_allows_larger_patch(self):
        sets = {str(i % 3): PARTS[i % 3] for i in range(3)}
        drops = list(range(SP.PASS_EDITS))
        with self.assertRaises(ValueError):
            SP.apply_patch(PARTS * 3, reply({"set": sets, "drop": drops}))
        parts, _ = SP.apply_patch(PARTS * 3, reply({"set": sets, "drop": drops}),
                                  SP.REPAIR_EDITS)
        self.assertEqual(len(parts), 9 - SP.PASS_EDITS)

    def test_patch_outside_schema_is_rejected(self):
        bad = ["tail", "box", [0.1, 0.1, 0.1], [0, 1, 0], "iron", {}]
        with self.assertRaises(ValueError):
            SP.apply_patch(PARTS, reply({"set": {"0": bad}}))

    def test_bare_bone_names_are_quoted(self):
        parts, _ = SP.apply_patch(PARTS, '{"set": {"1": [head, "box", [0.3, 0.2, 0.2], '
                                         '[0, 2.4, 0], "iron", {}]}}')
        self.assertEqual(parts[1][0], "head")


class ParseSpec(unittest.TestCase):
    def test_from_to_limb_without_at_gets_the_midpoint(self):
        limb = ["thigh.L", "prism", [0.1, 0.08, 0.6], None, "iron",
                {"from": [0.3, 1.2, 0], "to": [0.3, 0.6, 0.1]}]
        spec = SP.parse_spec(json.dumps({"parts": [PARTS[0], limb]}))
        for got, want in zip(spec["parts"][1][3], [0.3, 0.9, 0.05]):
            self.assertAlmostEqual(got, want)

    def test_missing_at_without_span_is_rejected(self):
        bad = ["head", "box", [0.2, 0.2, 0.2], None, "iron", {}]
        with self.assertRaises(ValueError):
            SP.parse_spec(json.dumps({"parts": [bad]}))


class Palette(unittest.TestCase):
    PALETTE = {"hide": {"surface": "leather", "color": "#6B4423"},
               "eye": {"surface": "glow", "color": "#FFD24A"}}

    def test_palette_slots_are_materials(self):
        part = ["head", "box", [0.2, 0.2, 0.2], [0, 2.4, 0], "hide", {}]
        spec = SP.parse_spec(json.dumps({"palette": self.PALETTE, "parts": [part]}))
        self.assertEqual(spec["palette"], self.PALETTE)
        with self.assertRaises(ValueError):          # undeclared slot
            SP.parse_spec(json.dumps({"parts": [part]}))

    def test_unknown_surface_or_bad_colour_is_rejected(self):
        for entry in ({"surface": "velvet", "color": "#112233"},
                      {"surface": "cloth", "color": "red"}):
            with self.assertRaises(ValueError):
                SP.parse_spec(json.dumps({"palette": {"x": entry}, "parts": PARTS}))

    def test_alpha_must_be_an_opacity(self):
        glass = {"surface": "glass", "color": "#AACCDD", "alpha": 0.4}
        part = ["head", "box", [0.2, 0.2, 0.2], [0, 2.4, 0], "lens", {}]
        spec = SP.parse_spec(json.dumps({"palette": {"lens": glass}, "parts": [part]}))
        self.assertEqual(spec["palette"]["lens"]["alpha"], 0.4)
        for bad in (0.0, 1.5, "half"):
            with self.assertRaises(ValueError):
                SP.parse_spec(json.dumps({"palette": {"lens": {**glass, "alpha": bad}},
                                          "parts": [part]}))

    def test_decal_names_are_checked(self):
        head = ["head", "box", [0.2, 0.2, 0.2], [0, 2.4, 0], "iron", {"decal": "eyes2"}]
        self.assertEqual(SP.parse_spec(json.dumps({"parts": [head]}))["parts"][0][5]["decal"], "eyes2")
        head[5] = {"decal": "mouth"}
        with self.assertRaises(ValueError):
            SP.parse_spec(json.dumps({"parts": [head]}))

    def test_legacy_specs_need_no_palette(self):
        self.assertNotIn("palette", SP.parse_spec(json.dumps({"parts": PARTS})))

    def test_patch_may_use_palette_slots(self):
        new = ["head", "box", [0.3, 0.2, 0.2], [0, 2.4, 0], "eye", {}]
        parts, _ = SP.apply_patch(PARTS, reply({"set": {"1": new}}), palette=self.PALETTE)
        self.assertEqual(parts[1][4], "eye")

    def test_refinement_prompt_shows_the_fixed_palette(self):
        text = SP.numbered({"palette": self.PALETTE, "parts": PARTS})
        self.assertIn("use only these slot names", text)
        self.assertIn("  0: ", text)


class Rig(unittest.TestCase):
    def tearDown(self):
        SP.set_rig("biped")

    def test_spider_bones_parse_and_bare_names_are_quoted(self):
        SP.set_rig("spider")
        spec = SP.parse_spec('{"parts": [[leg3.upper, "prism", [0.05, 0.04, 0.5], '
                             '[0.2, 0.5, 0.2], "iron", {}]]}')
        self.assertEqual(spec["parts"][0][0], "leg3.upper")

    def test_biped_bone_is_outside_the_spider(self):
        SP.set_rig("spider")
        with self.assertRaises(ValueError):
            SP.parse_spec(json.dumps({"parts": [PARTS[0]]}))

    def test_biped_aliases_only_apply_to_bipeds(self):
        part = ["chest", "box", [0.1, 0.1, 0.1], [0, 1.8, 0], "iron", {}]
        self.assertEqual(SP.parse_spec(json.dumps({"parts": [part]}))["parts"][0][0], "spine")
        SP.set_rig("quadruped")
        with self.assertRaises(ValueError):
            SP.parse_spec(json.dumps({"parts": [part]}))

    def test_extra_bones_join_the_rig(self):
        SP.set_rig("vehicle")
        part = ["mast", "cyl", [0.05, 1.0], [0, 1.0, 0], "iron", {}]
        bones = [["mast", "hull", [0, 0.5, 0], [0, 1.5, 0]]]
        spec = SP.parse_spec(json.dumps({"bones": bones, "parts": [part]}))
        self.assertEqual(spec["bones"], bones)
        self.assertIn("extra bones", SP.numbered(spec))
        with self.assertRaises(ValueError):          # parent unknown to the vehicle
            SP.parse_spec(json.dumps({"bones": [["mast", "spine", [0, 0, 0], [0, 1, 0]]],
                                      "parts": [part]}))
        with self.assertRaises(ValueError):          # bone used but not declared
            SP.parse_spec(json.dumps({"parts": [part]}))

    def test_every_family_has_brief_text(self):
        for fam in SP.RF.FAMILIES:
            self.assertIn("bones", SP.rig_text(fam)[1], fam)

    def test_non_biped_brief_drops_biped_landmarks(self):
        m = {"front_width_profile": [0.5] * 21, "left_width_profile": [0.3] * 21}
        text = SP.measured_text("spider", m)
        self.assertIn("Side silhouette", text)
        self.assertNotIn("shoulder span", text)
        self.assertIn("eight-legged", SP.rig_text("spider")[1])


class Accepted(unittest.TestCase):
    PREV = {"front": 0.70, "left": 0.65, "back": 0.60, "top": 0.5, "bottom": 0.4}

    def scores(self, **kw):
        return {**self.PREV, **kw}

    def test_own_view_must_improve(self):
        self.assertTrue(SP.accepted(self.PREV, self.scores(back=0.62), "back"))
        self.assertFalse(SP.accepted(self.PREV, self.scores(back=0.60), "back"))

    def test_gated_view_may_not_slip(self):
        self.assertFalse(SP.accepted(self.PREV, self.scores(back=0.7, front=0.68), "back"))
        self.assertTrue(SP.accepted(self.PREV, self.scores(back=0.7, front=0.695), "back"))

    def test_failed_build_is_rejected(self):
        self.assertFalse(SP.accepted(self.PREV, None, "left"))


class TiltArg(unittest.TestCase):
    def test_only_tilted_views_are_passed(self):
        report = {"front": {"iou": 0.8, "tilt": 0}, "top": {"iou": 0.7, "tilt": 10},
                  "bottom": {"iou": 0.7, "tilt": 20}}
        self.assertEqual(SP.tilt_arg(report), "tilt=top:10,bottom:20")
        self.assertEqual(SP.tilt_arg({}), "tilt=")

    def test_rts_camera_is_a_pair(self):
        self.assertEqual(SP.tilt_arg({"rts": {"tilt": [55, -30]}}), "tilt=rts:55/-30")


if __name__ == "__main__":
    unittest.main()
