"""python3 -m unittest discover -s tests/tools/blender"""
import pathlib
import shutil
import sys
import tempfile
import math
import unittest
import unittest.mock

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


class JointMeasures(unittest.TestCase):
    def figure(self, thigh=12, shin=24):
        """Front mask 200 rows: a right leg (x 110..) thin above row 120, wide below; the left leg mirrors it."""
        m = np.zeros((200, 200), bool)
        for x0, sign in ((110, 1), (90, -1)):
            for rows, w in ((slice(60, 120), thigh), (slice(120, 200), shin)):
                m[rows, x0:x0 + w] = True if sign > 0 else False
                if sign < 0:
                    m[rows, x0 - w:x0] = True
        return m

    def test_knee_is_the_width_step(self):
        front = self.figure()
        row = S.knee_row(S.limb_widths(front, 180, 60, S.leg_run))
        self.assertAlmostEqual(row, 120, delta=8)

    def test_no_step_no_knee(self):
        front = self.figure(thigh=24)
        self.assertIsNone(S.knee_row(S.limb_widths(front, 180, 60, S.leg_run)))

    def test_outline_breaks_do_not_split_a_run(self):
        row = np.zeros(40, bool)
        row[5:15] = row[17:30] = True            # a 2 px ink gap
        self.assertEqual(S._runs(row), [(5, 30)])
        self.assertEqual(S._runs(row, gap=0), [(5, 15), (17, 30)])


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


class Families(unittest.TestCase):
    """quadruped, wyrm, drake (PIPELINE 22.L4-4b): centre line, wings, measure_rig."""

    def test_centreline_follows_a_bar_and_skips_a_rope_below_the_floor(self):
        m = np.zeros((80, 200), bool)
        m[20:50, 10:150] = True                          # body, 30 px thick
        m[75:78, 150:199] = True                         # a thin rope on the ground, farther right
        m[60:78, 148:152] = True                         # ... joined to it
        line = S.centreline(m, floor=0.0)
        self.assertEqual(len(line), S.LINE_POINTS)
        self.assertGreater(line[-1][0], 190)             # the rope is the rightmost pixel
        line = S.centreline(m, floor=0.4)
        self.assertLess(line[-1][0], 150)                # above the floor the body ends the line
        self.assertTrue(all(18 < y < 52 for _, y, _ in line))
        self.assertAlmostEqual(line[len(line) // 2][2], 15, delta=2)    # radius = half the thickness

    def test_wing_numbers_read_the_spar_and_the_row_width(self):
        m = np.zeros((100, 100), bool)
        m[40:100, 40:60] = True                           # body column
        for r in range(0, 40):                            # a wing leaning out: centre col 70 + (40 - r) / 2, 10 wide
            c = 70 + (40 - r) // 2
            m[r, c - 5:c + 5] = True
            m[r, 100 - c - 5:100 - c + 5] = True
        w = S.wing_numbers(m)
        self.assertAlmostEqual(w["width"], 0.1, delta=0.02)
        self.assertGreater(w["tip"][0], w["root_x"])      # the spar leans out going up
        self.assertAlmostEqual(w["tip"][1], 1.0, delta=0.01)
        self.assertGreater(w["span"], w["tip"][0])

    def test_measure_rig_only_for_scalable_families(self):
        self.assertIsNone(S.measure_rig("biped", WOLF))
        m = S.measure_rig("quadruped", WOLF)
        self.assertGreater(m["len"], 1.5)                                 # a wolf is longer than tall
        self.assertLess(m["trunk"][0], m["trunk"][1])
        self.assertLess(m["legs"]["x"][0], m["legs"]["x"][1])             # front pair nearer the snout
        self.assertNotIn("wing", m)


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


class Coupling(unittest.TestCase):
    def setUp(self):
        self.sheet = np.zeros((256, 384), bool)
        self.sheet[0:256, 150:230] = True          # a full-height column

    def test_shares_and_bands(self):
        model = self.sheet.copy()
        model[64:96, :] = False                    # a bare strip: rows 64-95 = 0.625-0.75 H from the feet
        model[:, 230:250] = self.sheet[:, 150:170][:, :20] | True   # spill on the right, 20 columns wide
        got = S.coupling(self.sheet, model)
        for name, key, want in (("uncovered", "uncovered", 32 / 256), ("spill", "spill", 20 * 256 / (80 * 224 + 20 * 256))):
            with self.subTest(name):
                self.assertAlmostEqual(got[key], want, places=3)
        with self.subTest("worst band"):
            self.assertEqual(got["red"]["band"], 5)
            self.assertEqual((got["red"]["lo"], got["red"]["hi"]), (0.625, 0.75))
            self.assertAlmostEqual(got["red"]["share"], 32 / 256, places=3)
            self.assertAlmostEqual(sum(got["bands"]["uncovered"]), got["uncovered"], places=2)
        with self.subTest("blob + text"):
            self.assertEqual(got["red"]["blob"]["y"], [0.625, 0.75])
            self.assertIn("band 5 (0.62-0.75 H), 12 % of sheet", S.red_text(got["red"]))

    def test_perfect_and_gate_switch(self):
        got = S.coupling(self.sheet, self.sheet)
        self.assertEqual((got["uncovered"], got["spill"], got["red"]["blob"]), (0.0, 0.0, None))
        bad = {"uncovered": 0.9, "spill": 0.0}
        self.assertFalse(S.coupling_ok("front", bad))                # a gate since 2026-10-28
        self.assertTrue(S.coupling_ok("front", got))
        with unittest.mock.patch.object(S, "COUPLING_BLOCKING", False):
            self.assertTrue(S.coupling_ok("front", bad))             # report only when switched off


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


@unittest.skipUnless(HARD.exists(), "hfoo refs not checked out")
class Edges(unittest.TestCase):
    def test_bands_have_facets_and_salience_sums_to_one(self):
        m = S.measure(REFS / "sheet.jpg")
        bands = S.edge_bands(HARD, m["shoulder_frac"])
        self.assertEqual(list(bands), list(S.EDGE_BANDS))
        self.assertAlmostEqual(sum(b["salience"] for b in bands.values()), 1.0, delta=0.01)
        self.assertTrue(all(b["facets"] >= 1 for b in bands.values()))

    def test_rim_is_not_an_edge(self):
        mask = S.concept_panels(HARD)["front"]
        hit = S.edges(HARD, mask)
        from scipy.ndimage import binary_erosion
        self.assertFalse((hit & ~binary_erosion(mask, iterations=S.EDGE_RIM)).any())


class EdgeChamfer(unittest.TestCase):
    def test_same_lines_are_zero_and_missing_lines_are_far(self):
        import numpy as np
        mask = np.zeros((200, 200), bool)
        mask[20:180, 40:160] = True
        lines = np.zeros_like(mask)
        lines[60:62, 50:150] = True
        self.assertEqual(S.edge_chamfer(lines, mask, lines, mask), {"drawn": 0.0, "extra": 0.0})
        other = np.zeros_like(mask)
        other[140:142, 50:150] = True
        self.assertGreater(S.edge_chamfer(lines, mask, other, mask)["drawn"], 0.1)
        self.assertIsNone(S.edge_chamfer(lines, mask, np.zeros_like(mask), mask))
SPIDER_SHEET = ROOT / "artifacts/model-sheets/refs/n00U/sheet.jpg"


@unittest.skipUnless(SPIDER_SHEET.exists(), "n00U refs not checked out")
class MeasureSpider(unittest.TestCase):
    def test_n00u_body_belly_and_legs(self):
        m = S.measure_spider(SPIDER_SHEET)
        self.assertTrue(0.28 <= m["body_r"] <= 0.36, m)       # the shell: about 0.65 H wide
        self.assertTrue(0.18 <= m["body_under"] <= 0.30, m)   # belly a quarter of H above the floor
        self.assertTrue(0.5 <= m["foot_r"] <= 0.65, m)        # legs spread over 1.16 H
        self.assertTrue(m["body_len"] > m["body_r"], m)
        self.assertTrue(0.03 <= m["leg_w"] <= 0.06, m)        # legs about 0.09 H thick
        self.assertIn("leg_taper", m)

    def test_n00u_top_panel_gives_eight_legs_four_a_side(self):
        legs = S.measure_spider(SPIDER_SHEET)["legs"]
        self.assertEqual(len(legs), 8)
        self.assertEqual(sum(1 for r in legs if r[5] > 0), 4)             # tip x > 0: four on the right
        for _, bx, bz, kx, kz, tx, tz, r in legs:
            self.assertGreater(math.hypot(tx, tz), math.hypot(bx, bz))   # the tip is farther out than the base
            self.assertTrue(0.02 <= r <= 0.08, r)

    def test_merged_legs_give_no_branches(self):
        import numpy as np
        yy, xx = np.mgrid[:200, :200]
        self.assertIsNone(S.leg_branches(np.hypot(yy - 100, xx - 100) <= 40, 1 / 200))      # a bare disc: no legs


class LegMeasures(unittest.TestCase):
    def test_thin_bars_around_a_disc(self):
        """a 40 px disc with 6 px bars out of it: leg_w is the bar radius in H, a bar that
        narrows to the tip has a taper under 1"""
        import numpy as np
        yy, xx = np.mgrid[:200, :200]
        mask = np.hypot(yy - 100, xx - 100) <= 40
        for k in range(8):
            mask[96 + k // 4:104 - k // 4, 140 + 8 * k:148 + 8 * k] = True    # right bar, 8 px thick to 6 px
            mask[96:104, 52 - 8 * k - 8:52 - 8 * k] = True                    # left bar, constant 8 px
        got = S.leg_measures([(mask, 100.0)])
        self.assertAlmostEqual(got["leg_w"], 0.04, delta=0.012)
        self.assertLess(got["leg_taper"], 1.1)
        self.assertIsNone(S.leg_measures([(np.pad(np.ones((30, 30), bool), 20), 100.0)]))


WOLF = ROOT / "artifacts/model-sheets/refs/n017/sheet.jpg"


@unittest.skipUnless(WOLF.exists(), "n017 sheet not checked out")
class BlobPanels(unittest.TestCase):
    def test_wide_profile_keeps_its_whole_body(self):
        with tempfile.TemporaryDirectory() as tmp:           # the column cut (layout "unit" splits by blob by default now)
            shutil.copy(WOLF, pathlib.Path(tmp) / "sheet.jpg")
            thirds = S.concept_panels(pathlib.Path(tmp) / "sheet.jpg", blob=False, columns=True)
        blobs = S.concept_panels(WOLF, blob=True)
        self.assertEqual(S.concept_panels(WOLF)["left"].sum(), blobs["left"].sum())      # units default to blob
        self.assertEqual(list(blobs), list(thirds))
        width = lambda m: int(m.any(axis=0).sum())  # noqa: E731
        self.assertGreater(width(blobs["left"]), 768 // 3)      # the thirds split clips it at 256
        self.assertLessEqual(width(thirds["left"]), 768 // 3)
        self.assertLess(width(blobs["front"]), width(thirds["front"]))   # no snout in the front panel


class PanelOrientation(unittest.TestCase):
    def teardrop(self):
        m = S.np.zeros((200, 200), bool)
        m[20:60, 60:140] = True      # wide head at the top
        m[60:180, 90:110] = True     # narrow tail
        return m

    def test_rotates_only_a_panel_clearly_drawn_upside_down(self):
        m = self.teardrop()
        model = {"top": {0: m}, "bottom": {0: m}}
        self.assertEqual(S.detect_rotated({"top": m, "bottom": m}, model), set())
        self.assertEqual(S.detect_rotated({"top": m[::-1], "bottom": m}, model), {"top"})

    def test_a_symmetric_panel_is_left_as_drawn_and_oriented_rotates_before_the_crop(self):
        box = S.np.zeros((200, 200), bool)
        box[40:160, 60:140] = True
        self.assertEqual(S.detect_rotated({"top": box}, {"top": {0: box}}), set())
        m = self.teardrop()
        self.assertTrue(S.np.array_equal(S.oriented({"top": m}, {"top"})["top"], S.normalize(S.np.rot90(m, 2))))


class IdentityReads(unittest.TestCase):
    def test_hue_match_ignores_grey_and_other_hues(self):
        blue = float(S.hue_chroma(S.hex_rgb("#586B87"))[0])
        hue, chroma = S.hue_chroma(S.hex_rgb("#5A6AA8")), S.hue_chroma(S.hex_rgb("#64686E"))
        self.assertTrue(S.same_colour(*hue, blue))
        self.assertFalse(S.same_colour(*chroma, blue))                         # steel grey: no colour
        self.assertFalse(S.same_colour(*S.hue_chroma(S.hex_rgb("#A0803C")), blue))
        self.assertEqual(S.hue_name(float(S.hue_chroma(S.hex_rgb("#8A2A35"))[0])), "red")

    def test_reads_is_the_render_share_over_the_sheet_share(self):
        import tempfile
        from PIL import Image
        details = [{"hex": "#586B87", "shares": {"front": 0.01}}, {"hex": "#50252E", "shares": {"front": 0.01}}]
        with tempfile.TemporaryDirectory() as d:
            img = np.zeros((512, 512, 4), np.uint8)
            img[100:400, 100:400] = (100, 100, 110, 255)      # grey figure, 90000 px
            img[100:110, 100:190] = (90, 106, 168, 255)       # blue patch, 900 px = 1 % of it
            Image.fromarray(img).save(pathlib.Path(d) / "u-zone-front.png")
            got = S.identity_reads(details, pathlib.Path(d), "u")
        self.assertEqual([(r["read"], r["view"]) for r in got], [(True, "front"), (False, "")])
        self.assertAlmostEqual(got[0]["ratio"], 1.0, places=1)


class SheetCoherenceTest(unittest.TestCase):
    def test_r_sym_is_one_for_a_mirror_and_drops_with_a_one_sided_prop(self):
        m = np.zeros((40, 40), bool)
        m[:, 15:25] = True
        self.assertEqual(S.r_sym(m), 1.0)
        m[10:20, 25:35] = True        # a club on one side
        self.assertLess(S.r_sym(m), S.SYM_MIN)

    def test_hull_is_front_by_left_on_the_grid(self):
        front, left = np.zeros((40, 30), bool), np.zeros((40, 20), bool)
        front[:, 5:25] = True
        left[:, 4:16] = True
        hull = S.hull_voxels(front, left, 32)
        self.assertEqual(hull.shape, (32, 16, 10))        # y, x, z: widths scaled by the same 32 / 40
        self.assertTrue(hull.all())

    def test_rts_of_the_hull_is_coherent_with_its_own_projection(self):
        front, left = np.zeros((60, 30), bool), np.zeros((60, 20), bool)
        front[:, 5:25] = True
        left[:30, 4:16] = True
        left[30:, 8:12] = True            # a wide head, a thin pair of legs: not a box
        hull = S.hull_voxels(front, left, 32)
        for cam, zflip in (((35, 30), False), ((55, -45), True)):
            with self.subTest(cam=cam):
                iou, found = S.rts_coherence(hull, S.hull_rts_mask(hull, cam, zflip))
                self.assertGreater(iou, 0.95)
        self.assertLess(S.rts_coherence(hull, np.ones((40, 40), bool), [(35, 30)])[0], 0.6)

    def test_sheets_measured(self):
        refs = ROOT / "artifacts/model-sheets/refs"
        for sheet, sym, bad in (("n01X", True, []), ("hfoo", False, ["rts"]), ("n00H", True, ["top", "bottom", "rts"])):
            with self.subTest(sheet):
                rep = S.sheet_report(refs / sheet / "sheet.jpg")
                self.assertEqual(rep["r_sym"]["front"] >= S.SYM_MIN, sym)
                self.assertEqual(rep["incoherent"], bad)
        self.assertEqual(S.sheet_report(refs / "n01X" / "sheet.jpg", "building"), {})

    def test_text_names_the_problem_only_when_there_is_one(self):
        ok = {"r_sym": {"front": 0.95}, "coherence": {"back": 0.8}, "incoherent": []}
        bad = {"r_sym": {"front": 0.78}, "coherence": {"back": 0.8, "top": 0.52}, "incoherent": ["top"]}
        self.assertEqual(S.sheet_text(ok), "")
        self.assertIn("asymmetric in the front view (r_sym 0.78)", S.sheet_text(bad))
        self.assertIn("top panel disagrees", S.sheet_text(bad))
        self.assertIn("top-vs-hull 0.52 (incoherent)", S.sheet_line(bad))


class BodyOnly(unittest.TestCase):
    """PIPELINE 25.L7-5: the body's mask is the panel minus its props'."""
    SHEET = ROOT / "artifacts/model-sheets/refs/hfoo/sheet.jpg"

    @unittest.skipUnless(SHEET.exists(), "hfoo sheet")
    def test_masks(self):
        panels = S.concept_panels(self.SHEET)
        props = S.prop_masks(self.SHEET, "left", panels=panels)
        body, whole = S.body_mask(self.SHEET, "left", panels=panels), S.normalize(panels["left"])
        for name, want in [("pike is a prop", "trench pike" in props), ("pike mask is thin", props["trench pike"].sum() < 0.5 * whole.sum()),
                           ("body has no prop pixel", not (body & props["trench pike"]).any()),
                           ("body is most of the panel", 0.5 * whole.sum() < body.sum() < whole.sum())]:
            with self.subTest(name):
                self.assertTrue(want)
        self.assertEqual(S.prop_masks(self.SHEET, "top", panels=panels), {})       # no box for the view
        self.assertTrue((S.body_mask(self.SHEET, "top", panels=panels) == S.normalize(panels["top"])).all())

    def test_split_sums_to_total(self):
        concept, model = np.zeros((256, 384), bool), np.zeros((256, 384), bool)
        concept[10:200, 100:200] = True
        model[10:200, 120:230] = True
        props = np.zeros_like(concept)
        props[:, 150:190] = True
        got, tot = S.coupling_split(concept, model, props), S.coupling(concept, model)
        self.assertAlmostEqual(got["uncovered_body"] + got["uncovered_prop"], tot["uncovered"], places=3)
        self.assertAlmostEqual(got["spill_body"] + got["spill_prop"], tot["spill"], places=3)


class SideMirror(unittest.TestCase):
    """29.L11-0: a prop that widens the sheet's bbox must not decide which mirror a side view takes."""

    @staticmethod
    def figure(pike):
        m = np.zeros((256, 384), bool)
        m[10:250, 150:190] = True             # body
        m[60:160, 120:150] = True             # pack behind (image-left)
        if pike:                              # a diagonal pike running far past the body on the right
            for t in np.linspace(0, 1, 400):
                m[int(250 - 240 * t), int(100 + 150 * t)] = True
        return S.normalize(m)

    def test_pike_does_not_flip_the_pick(self):
        concept, model = self.figure(True), self.figure(False)
        options = S.variants(model, "left")
        self.assertGreater(S.iou(concept, options[1]), S.iou(concept, options[0]))     # the premise: plain IoU says mirror
        self.assertEqual(S.pick_variant(concept, options, "left"), 1)                    # opt-in: off by default
        with unittest.mock.patch.object(S, "FLIP_SIDE", True):
            self.assertEqual(S.pick_variant(concept, options, "left"), 0)
            self.assertEqual(S.pick_variant(concept, S.variants(model, "rts"), "rts"), 0)    # other views: plain

    def test_best_match_reports_flipped(self):
        concept = self.figure(False)
        score, mask, tilt, flipped = S.best_match(concept, {0: np.fliplr(concept)}, "left")
        self.assertTrue(flipped)
        self.assertGreater(score, 0.95)
        self.assertFalse(S.best_match(concept, {0: concept}, "left")[3])
        self.assertFalse(S.best_match(concept, {0: np.fliplr(concept)}, "rts")[3])      # the rts is never mirrored


class BodyFrame(unittest.TestCase):
    """29.L11-0b: a Framed panel (box = the body) and a model framed by its body match where the bbox frames do not."""

    @staticmethod
    def sheet():
        m = np.zeros((300, 400), bool)
        m[40:290, 150:190] = True             # body
        m[90:190, 120:150] = True             # pack behind (image-left)
        for t in np.linspace(0, 1, 500):      # a diagonal pike running far past the body on the right
            m[int(290 - 250 * t), int(100 + 200 * t)] = True
        return m

    @staticmethod
    def model():
        m = np.zeros((300, 400), bool)
        m[40:290, 150:190] = True
        m[90:190, 120:150] = True
        m[0:300, 60:66] = True                # a vertical pike (a prop of the model, outside the body box)
        return m

    def test_body_frame_matches_bbox_does_not(self):
        sheet, model = self.sheet(), self.model()
        body = S.framed(sheet, (120, 40, 190, 290))
        self.assertGreater(S.iou(S.normalize(body), S.normalize(S.framed(model, (120, 40, 190, 290)))), 0.8)
        self.assertLess(S.iou(S.normalize(sheet), S.normalize(model)), 0.6)

    def test_best_match_takes_the_model_box(self):
        sheet, model = self.sheet(), self.model()
        concept = S.normalize(S.framed(sheet, (120, 40, 190, 290)))
        plain = S.best_match(concept, {0: model}, "left")[0]
        boxed = S.best_match(concept, {0: model}, "left", {0: (120, 40, 190, 290)})[0]
        self.assertGreater(boxed, plain + 0.1)
        self.assertGreater(boxed, 0.8)

    def test_rot180_turns_the_box(self):
        m = S.framed(self.model(), (120, 40, 190, 290))
        self.assertEqual(S.rot180(m).box, (210, 10, 280, 260))
        self.assertIsNone(getattr(S.rot180(np.asarray(m)), "box", None))
        self.assertIsNone(getattr(m[:10], "box", None))      # a slice frames by its own bbox
