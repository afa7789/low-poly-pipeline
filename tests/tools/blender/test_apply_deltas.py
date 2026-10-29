"""python3 -m unittest discover -s tests/tools/blender"""
import copy
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import apply_deltas as AD  # noqa: E402
import spec_pipeline as SP  # noqa: E402

SPEC = {"palette": {"cloth": {"surface": "cloth", "color": "#445566"}},
        "parts": [
            ["pelvis", "frustum", [0.5, 0.3, 0.3], [0, 0.9, 0], "cloth", {}],
            ["spine", "lathe", [0.3, 0.8], [0, 1.4, 0], "cloth", {}],
            ["spine", "box", [0.2, 0.2, 0.1], [0, 1.4, -0.3], "cloth", {}],
            ["spine", "box", [0.05, 0.05, 0.05], [0, 1.6, -0.3], "cloth", {}],
            ["head", "box", [0.3, 0.3, 0.3], [0, 1.9, 0], "cloth", {}],
            ["arm.L", "prism", [0.1, 0.08, 0.5], [0.4, 1.4, 0], "cloth", {"axis": "up"}],
            ["arm.R", "prism", [0.1, 0.08, 0.5], [-0.4, 1.4, 0], "cloth", {"axis": "up"}],
            ["thigh.L", "limb", [0.1, 0.09, 0.08], [0, 0, 0], "cloth", {"from": [0.2, 0.9, 0], "to": [0.2, 0.1, 0.05]}],
            ["thigh.R", "limb", [0.1, 0.09, 0.08], [0, 0, 0], "cloth", {"from": [-0.2, 0.9, 0], "to": [-0.2, 0.1, 0.05]}]]}
H = 2.1


def run(*deltas, spec=SPEC):
    out, log = AD.apply(copy.deepcopy(spec), list(deltas), H)
    return out, [e["status"] for e in log], [e["why"] for e in log]


class ApplyDeltas(unittest.TestCase):
    def test_scale_axis_and_uniform_leave_the_rest_frozen(self):
        out, st, _ = run({"part": "spine#1", "action": "scale", "axis": "x", "value": 0.8},
                         {"part": "head", "action": "scale", "value": 1.2})
        self.assertEqual(st, ["applied", "applied"])
        self.assertAlmostEqual(out["parts"][2][2][0], 0.16, delta=0.01)
        self.assertAlmostEqual(out["parts"][4][2][2], 0.36, delta=0.01)
        for i in (0, 1, 3, 5, 6, 7, 8):
            self.assertEqual(json.dumps(out["parts"][i]), json.dumps(SPEC["parts"][i]))

    def test_radius_and_twin_mirrored_move(self):
        out, st, why = run({"part": "arm.L", "action": "radius", "value": 1.3},
                           {"part": "thigh.L", "action": "move", "axis": "x", "value": 0.05})
        self.assertEqual(st, ["applied", "applied"])
        self.assertIn("twin", why[0])
        self.assertAlmostEqual(out["parts"][5][2][0], 0.13, delta=0.01)
        self.assertAlmostEqual(out["parts"][6][2][0], 0.13, delta=0.01)
        self.assertAlmostEqual(out["parts"][7][5]["from"][0], 0.25, delta=0.01)
        self.assertAlmostEqual(out["parts"][8][5]["from"][0], -0.25, delta=0.01)

    def test_rotate_adds_to_rot_and_refuses_span_kinds(self):
        out, st, why = run({"part": "head", "action": "rotate", "axis": "x", "value": 20},
                           {"part": "thigh.L", "action": "rotate", "axis": "z", "value": 10},
                           {"part": "spine#0", "action": "rotate", "axis": "z", "value": 10})
        self.assertEqual(st, ["applied", "rejected", "rejected"])
        self.assertEqual(out["parts"][4][5]["rot"], [20.0, 0.0, 0.0])
        self.assertIn("rotation", why[1])

    def test_limits_reject_alone(self):
        out, st, why = run({"part": "head", "action": "scale", "value": 1.9},
                           {"part": "head", "action": "move", "axis": "y", "value": 0.5},
                           {"part": "head", "action": "rotate", "axis": "y", "value": 40},
                           {"part": "head", "action": "move", "axis": "y", "value": 0.05})
        self.assertEqual(st, ["rejected"] * 3 + ["applied"])
        self.assertIn("outside", why[0])
        self.assertAlmostEqual(out["parts"][4][3][1], 1.95, delta=0.01)

    def test_schema_and_unknown_part(self):
        _, st, why = run({"part": "tail#0", "action": "scale", "value": 1.1},
                         {"part": "spine", "action": "scale", "value": 1.1},        # three spine parts: ambiguous
                         {"part": "head", "action": "scale", "value": 1.1, "colour": "red"},
                         {"part": "head", "action": "explode"}, "head")
        self.assertEqual(st, ["rejected"] * 5)
        self.assertIn("no part", why[0])
        self.assertIn("spine#k", why[1])
        self.assertIn("fields", why[2])

    def test_add_twice_then_too_many_and_too_big(self):
        out, st, why = run(
            {"part": "head", "action": "add", "kind": "box", "dims": [0.1, 0.1, 0.1], "at": [0, 2.1, 0]},
            {"part": "spine", "action": "add", "kind": "box", "dims": [0.1, 0.1, 0.1], "at": [0, 1.5, -0.35]},
            {"part": "head", "action": "add", "kind": "box", "dims": [0.1, 0.1, 0.1], "at": [0, 2.2, 0]},
            {"part": "head", "action": "add", "kind": "box", "dims": [2, 2, 2], "at": [0, 2.0, 0]})
        self.assertEqual(st, ["applied", "applied", "rejected", "rejected"])
        self.assertEqual(len(out["parts"]), len(SPEC["parts"]) + 2)
        self.assertIn("adds", why[2])

    def test_add_on_side_bone_brings_the_twin(self):
        out, st, _ = run({"part": "arm.L", "action": "add", "kind": "box", "dims": [0.1, 0.1, 0.1], "at": [0.5, 1.2, 0]})
        self.assertEqual(st, ["applied"])
        added = out["parts"][-2:]
        self.assertEqual([p[0] for p in added], ["arm.L", "arm.R"])
        self.assertEqual(added[1][3][0], -added[0][3][0])

    def test_remove_only_small_parts(self):
        out, st, why = run({"part": "spine#2", "action": "remove"}, {"part": "spine#0", "action": "remove"})
        self.assertEqual(st, ["applied", "rejected"])
        self.assertEqual(len(out["parts"]), len(SPEC["parts"]) - 1)
        self.assertIn("figure", why[1])

    def test_one_delta_per_part_and_original_addresses(self):
        out, st, _ = run({"part": "spine#2", "action": "remove"}, {"part": "spine#1", "action": "scale", "value": 1.2},
                         {"part": "spine#2", "action": "scale", "value": 1.2})
        self.assertEqual(st, ["applied", "applied", "rejected"])      # addresses are the input's: #1 stays the big box after #2 is gone
        self.assertEqual(len(out["parts"]), len(SPEC["parts"]) - 1)

    def test_result_passes_parse_spec_and_input_untouched(self):
        before = json.dumps(SPEC)
        out, st, _ = run({"part": "head", "action": "move", "axis": "y", "value": -0.15},
                         {"part": "arm.R", "action": "scale", "axis": "y", "value": 1.2})
        self.assertEqual(st, ["applied"] * 2)
        SP.parse_spec(json.dumps(out))
        self.assertEqual(json.dumps(SPEC), before)


class FitLimits(unittest.TestCase):
    """L11-3, via B: deltas as limits of the fit."""

    def limits(self, *deltas):
        return AD.fit_limits(copy.deepcopy(SPEC), list(deltas), H)

    def test_scale_radius_move_become_intervals_with_the_twin(self):
        lim = self.limits({"part": "spine#1", "action": "scale", "axis": "x", "value": 0.8},
                          {"part": "arm.L", "action": "radius", "value": 1.2},
                          {"part": "head", "action": "move", "axis": "y", "value": 0.1},
                          {"part": "arm.L", "action": "move", "axis": "x", "value": 0.05})
        self.assertEqual(lim[2]["dims"], {0: (0.7, 0.9)})
        self.assertEqual(lim[5]["dims"], {0: (1.1, 1.3), 1: (1.1, 1.3)})
        self.assertEqual(lim[6]["dims"], lim[5]["dims"])               # the twin
        self.assertAlmostEqual(lim[4]["at"][1][0], 0.1 - 0.02 * H)
        self.assertAlmostEqual(lim[5]["at"][0][0], 0.05 - 0.02 * H)
        self.assertAlmostEqual(lim[6]["at"][0][0], -0.05 - 0.02 * H)   # mirrored x

    def test_add_rotate_unknown_and_out_of_range_have_no_via_b(self):
        self.assertEqual(self.limits({"part": "head", "action": "add", "kind": "box", "dims": [.1, .1, .1], "at": [0, 2, 0]},
                                     {"part": "head", "action": "rotate", "axis": "x", "value": 10},
                                     {"part": "ghost", "action": "scale", "value": 0.8},
                                     {"part": "head", "action": "scale", "value": 2.0}), {})

    def test_bounds_replace_only_the_named_slots(self):
        import fit_spec as F
        part = SPEC["parts"][2]
        b = F.limit_bounds(part, F.bounds_of(part, False), {"dims": {0: (0.7, 0.9)}, "at": {1: (0.0, 0.03 * 2)}}, 2.0)
        self.assertAlmostEqual(b[0][0], -3.0)
        self.assertAlmostEqual(b[0][1], -1.0)
        self.assertEqual(b[1], (-1, 1))
        self.assertAlmostEqual(b[4][1], 1.0)


if __name__ == "__main__":
    unittest.main()
