"""python3 -m unittest discover -s tests/tools/blender"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import silhouette as S  # noqa: E402

REFS = ROOT / "artifacts/model-sheets/refs/hfoo"


class RigGates(unittest.TestCase):
    def test_spider_lowers_front_and_back_only(self):
        for rig in ("spider", "spider_high"):
            g = S.gates_for(rig)
            self.assertEqual((g["front"], g["back"]), (0.65, 0.65))
            self.assertEqual({k: v for k, v in g.items() if k not in ("front", "back")},
                             {k: v for k, v in S.GATES.items() if k not in ("front", "back")})

    def test_other_families_keep_the_defaults(self):
        self.assertEqual(S.gates_for("biped"), S.GATES)
        self.assertEqual(S.gates_for(None), S.GATES)

    def test_n00u_best_run_passes_and_the_worst_does_not(self):
        g = S.gates_for("spider")
        self.assertTrue(all(v >= g[k] for k, v in {"front": 0.667, "left": 0.658, "back": 0.675}.items()))
        self.assertFalse(0.530 >= g["front"])


HARD = REFS / "sheet-hard.jpg"


@unittest.skipUnless(HARD.exists(), "hfoo refs not checked out")
class Drift(unittest.TestCase):
    def test_hard_redraw_stays_on_the_approved_design(self):
        drift = S.sheet_drift(REFS / "sheet.jpg", HARD)
        for view in S.DRIFT_VIEWS:
            self.assertGreaterEqual(drift[view], S.DRIFT_MIN, view)   # measured 0.93-0.94

    def test_a_sheet_does_not_drift_from_itself(self):
        drift = S.sheet_drift(REFS / "sheet.jpg", REFS / "sheet.jpg")
        self.assertEqual(min(drift[v] for v in S.DRIFT_VIEWS), 1.0)


class GateWithoutModel(unittest.TestCase):
    def test_missing_glb_fails_the_gate(self):
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            run = subprocess.run([sys.executable, str(ROOT / "tools/blender/silhouette.py"),
                                  str(REFS / "sheet.jpg"), str(pathlib.Path(tmp) / "none.glb"),
                                  tmp, "--no-render"], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("no measurement", run.stdout)

    def test_shape_gates_cover_the_five_views_and_the_rts(self):
        self.assertEqual(set(S.GATES), {"front", "left", "back", "top", "bottom", "rts"})
        # measured clay rebuilds: n01X hard-v1 / v13 clear every gate, n01N clears none
        good = {"front": 0.873, "left": 0.771, "back": 0.858, "top": 0.792, "bottom": 0.780, "rts": 0.781}
        worst = {"front": 0.360, "left": 0.437, "back": 0.364, "top": 0.346, "bottom": 0.320, "rts": 0.440}
        self.assertTrue(all(good[v] >= g for v, g in S.GATES.items()))
        self.assertFalse(any(worst[v] >= g for v, g in S.GATES.items()))


import numpy as np  # noqa: E402


def figure():
    """A synthetic sheet figure on the 256x384 canvas: a body (zone 1) with a chest disc
    (zone 2) and two shoulder pads (zone 3), as zone label maps."""
    lab = np.zeros((256, 384), np.int16)
    lab[20:240, 130:254] = 1
    lab[60:110, 170:214] = 2
    lab[30:90, 60:130] = 3
    lab[30:90, 254:324] = 3
    return lab


NAMES = ["#706C68", "#AA8850", "#554433"]


class ZoneReport(unittest.TestCase):
    def test_same_figure_scores_one(self):
        z = S.zone_report(figure(), figure(), NAMES)
        self.assertEqual((z["mean"], z["cover"], z["lost"]), (1.0, 1.0, []))
        self.assertEqual(len(z["pieces"]), 4)          # body, disc, two pads

    def test_disc_painted_over_is_invisible_to_the_silhouette_but_not_here(self):
        model = figure()
        model[model == 2] = 1                           # the contour is untouched
        z = S.zone_report(figure(), model, NAMES)
        self.assertEqual(z["lost"], ["#AA8850"])        # a zone gone whole, small as it is
        self.assertEqual(z["zones"]["#AA8850"]["iou"], 0.0)
        self.assertEqual(min(z["pieces"].values()), 0.0)
        self.assertLess(z["mean"], 1.0)
        self.assertGreater(z["mean"], 0.8)              # area weighting: the body still matches

    def test_slack_forgives_a_part_a_few_px_off(self):
        model = np.roll(figure(), 3, axis=1)
        z = S.zone_report(figure(), model, NAMES)
        self.assertGreater(z["cover"], 0.97)
        self.assertLess(z["mean"], 0.95)

    def test_zone_under_the_floor_is_not_a_piece(self):
        lab = figure()
        lab[200:203, 140:143] = 2                       # 9 px speck of the disc colour
        z = S.zone_report(lab, lab, NAMES)
        self.assertEqual(len(z["pieces"]), 5 - 1)       # the speck is noise, not a part

    def test_gate_fails_a_wholesale_colour_miss_only(self):
        report = {"front": {}, "top": {}, "rts": {}}
        wrong = {k: 0 for k in ("mean", "cover")} | {"lost": ["#AA8850"]}
        good = {"mean": 0.3, "cover": 0.6, "lost": []}
        self.assertEqual(S.zone_gate(report, {"front": wrong, "top": wrong, "rts": wrong}), 2)   # all 5 views gate
        self.assertEqual(S.zone_gate({"front": {}}, {"front": good}), 0)


class Cameras(unittest.TestCase):
    def test_pin_keeps_only_the_chosen_camera(self):
        model = {"front": {0: "f"}, "top": {10: "a", 20: "b"}, "rts": {(35, 30): "x", (45, 45): "y"}}
        pinned = S.pin_tilts(model, {"top": 20, "rts": (35, 30)})
        self.assertEqual(pinned, {"front": {0: "f"}, "top": {20: "b"}, "rts": {(35, 30): "x"}})

    def test_report_tilts_skips_square_on_views(self):
        self.assertEqual(S.report_tilts({"front": {"tilt": 0}, "top": {"tilt": 10}}), {"top": 10})


class ZoneParts(unittest.TestCase):
    def test_components_split_by_gap(self):
        m = np.zeros((20, 20), bool)
        m[2:6, 2:6] = m[10:15, 10:15] = True
        m[2:6, 6:9] = True                              # touches the first
        self.assertEqual(sorted(int(c.sum()) for c in S.components(m)), [25, 28])

    def test_mode_filter_removes_a_sliver_and_keeps_a_block(self):
        lab = np.zeros((40, 40), np.int16)
        lab[5:35, 5:35] = 1
        lab[5:35, 20] = 2                               # 1-px outline of another zone
        lab[10:30, 24:34] = 2                           # a real block
        out = S.mode_filter(lab)
        self.assertTrue((out[8:32, 18:22] == 1).all())
        self.assertTrue((out[14:26, 26:32] == 2).all())
        self.assertTrue((out[lab == 0] == 0).all())

    def test_labels_nearest_zone_and_grow_ink_over(self):
        centres = S.zone_feature(np.array([[0.45, 0.43, 0.42], [0.66, 0.51, 0.31]]))
        rgb = np.zeros((6, 6, 3))
        rgb[:] = (0.46, 0.44, 0.43)                     # grey
        rgb[:, 3:] = (0.65, 0.5, 0.3)                   # gold
        rgb[:, 2] = 0.02                                # ink column between them
        mask = np.ones((6, 6), bool)
        lab = S.zone_labels(rgb, mask, centres, ink=True)
        self.assertEqual(set(lab[:, :2].ravel()), {1})
        self.assertEqual(set(lab[:, 3:].ravel()), {2})
        self.assertTrue((lab[:, 2] > 0).all())          # no hole where the outline was

    def test_darker_render_keeps_its_zones(self):
        sheet = np.array([[0.7, 0.7, 0.7]] * 60 + [[0.9, 0.9, 0.9]] * 40)
        render = np.zeros((10, 10, 3))
        render[:6] = 0.30
        render[6:] = 0.45                               # the same two tones, much darker
        out = S.match_luma(render, np.ones((10, 10), bool), sheet)
        self.assertAlmostEqual(float(out[0, 0] @ S.LUMA), 0.7, delta=0.05)
        self.assertAlmostEqual(float(out[9, 0] @ S.LUMA), 0.9, delta=0.05)


class SheetMeasures(unittest.TestCase):
    def test_boot_height_is_the_long_rows_above_the_ground(self):
        side = np.zeros((100, 100), bool)
        side[20:100, 40:50] = True          # shin, 10 wide
        side[90:100, 40:70] = True          # boot: the last 10 rows are 30 wide
        self.assertAlmostEqual(S.boot_height(side, 1.0), 0.1, delta=0.03)

    def test_arm_angle_is_positive_when_the_arms_swing_out(self):
        out = np.full(201, 0.3)
        out[40:130] = np.linspace(0.3, 0.7, 90)         # the outline widens down the arm
        angle, length = S.arm_measures(out, 40)
        self.assertGreater(angle, 0)
        self.assertGreater(length, 0.3)

    def test_head_is_the_widest_top_row_and_neck_the_narrowest_below(self):
        spans = np.array([0.0, 0.2, 0.25, 0.25, 0.1, 0.1, 0.5, 0.6, 0.6, 0.6])
        self.assertEqual(S.head_measures(spans, 8), (0.25, 0.1))


class ZoneRamp(unittest.TestCase):
    def test_oklab_matches_the_reference_values(self):
        lab = S.oklab(np.array([[1.0, 1.0, 1.0], [0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]))
        np.testing.assert_allclose(lab[0], (1, 0, 0), atol=1e-6)
        np.testing.assert_allclose(lab[1], (0, 0, 0), atol=1e-9)
        np.testing.assert_allclose(lab[2], (0.628, 0.225, 0.126), atol=2e-3)       # Ottosson's red

    def test_zone_feature_follows_the_space(self):
        rgb = np.array([[0.6, 0.4, 0.2]])
        self.assertFalse(np.allclose(S.zone_feature_oklab(rgb), S.zone_feature(rgb)))
        self.assertEqual(S.ZONE_SPACE, "legacy")       # measured in PIPELINE 19.C2: oklab stays opt-in

    def test_luma_l1_is_zero_for_the_same_light_and_grows_with_the_gap(self):
        rng = np.random.default_rng(0)
        sheet = np.repeat(rng.uniform(0.3, 0.7, (40, 40, 1)), 3, axis=2)
        lab = np.ones((40, 40), int)
        self.assertEqual(S.luma_l1(sheet, lab, sheet, lab, 1), 0.0)
        self.assertAlmostEqual(S.luma_l1(sheet * 0.8, lab, sheet, lab, 1), 0.1, delta=0.02)   # 20 % darker, mean ~0.5
        self.assertIsNone(S.luma_l1(sheet, lab * 0, sheet, lab, 1))                            # no zone in both


if __name__ == "__main__":
    unittest.main()


class Chamfer(unittest.TestCase):
    def test_distance_in_canvas_heights(self):
        a = np.zeros((100, 100), bool)
        a[20:60, 20:60] = True
        b = np.roll(a, 10, axis=1)
        for name, x, y, want in (("same", a, a, 0.0), ("empty", a, np.zeros_like(a), 1.0)):
            with self.subTest(name):
                self.assertEqual(S.chamfer(x, y), want)
        with self.subTest("shifted"):
            # vertical edges sit 10 px apart, horizontal ones overlap: mean well under 10/100
            self.assertTrue(0.02 < S.chamfer(a, b) < 0.10)
        with self.subTest("symmetric"):
            self.assertAlmostEqual(S.chamfer(a, b), S.chamfer(b, a))


class Outline(unittest.TestCase):
    def test_douglas_peucker_keeps_corners_drops_noise(self):
        line = [(0, 0), (5, 0.2), (10, 0), (10, 5), (10, 10)]
        kept = S.douglas_peucker(line, 0.5)
        self.assertEqual(kept.tolist(), [[0, 0], [10, 0], [10, 10]])

    def test_outline_of_a_t_shape(self):
        import numpy as np
        m = np.zeros((60, 60), bool)
        m[5:55, 25:35] = True        # stem
        m[5:15, 10:50] = True        # bar
        poly = S.outline(m)
        self.assertTrue(8 <= len(poly) <= 12)
        self.assertGreater(max(y for _, y in poly), 0.97)
        self.assertEqual(max(x for x, _ in poly), -min(x for x, _ in poly))   # centred
        self.assertTrue(any(abs(x - 0.4) < 0.03 and y > 0.8 for x, y in poly))  # the bar's tip

    def test_band_areas_sum_to_one(self):
        import numpy as np
        m = np.ones((100, 20), bool)
        self.assertEqual(S.band_areas(m, 0.2), [0.2, 0.3, 0.5])
