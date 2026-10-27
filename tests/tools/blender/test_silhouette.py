"""python3 -m unittest discover -s tests/tools/blender"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import silhouette as S  # noqa: E402

REFS = ROOT / "artifacts/model-sheets/refs/hfoo"


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


if __name__ == "__main__":
    unittest.main()
