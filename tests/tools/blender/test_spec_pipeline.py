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
