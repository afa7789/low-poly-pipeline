"""python3 -m unittest discover -s tests/tools/blender"""
import pathlib
import sys
import tempfile
import unittest

import numpy as np

try:
    from PIL import Image
except ImportError:  # make_compare / compare_runs need Pillow (pip3.14 install pillow)
    raise unittest.SkipTest("Pillow is not installed")

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import compare_runs as CR  # noqa: E402
import make_compare as MC  # noqa: E402

REVIEW = """# n01X — run hard-v1 (n01X)

- spec author: session:opus
- kind: mass

stage 1 (shape): PASS
stage 2 (colour): FAIL

verdict: **FAIL**
"""


def fake_run(tmp):
    """A run dir: review.md, one report entry, front masks and a textured front render (no clay)."""
    (tmp / "review.md").write_text(REVIEW)
    sil = tmp / "sil/approved"
    sil.mkdir(parents=True)
    (sil / "silhouette.json").write_text(
        '{"front": {"iou": 0.8, "iou_32": 0.7, "width_l1": 0.1, "tilt": 0, "gate": 0.75}}')
    mask = np.zeros((64, 96, 4), np.uint8)
    mask[10:50, 20:60] = 255
    Image.fromarray(mask).save(sil / "mask-concept-front.png")
    Image.fromarray(mask).save(sil / "mask-model-front.png")
    views = tmp / "views/n01X"
    views.mkdir(parents=True)
    img = np.full((120, 160, 3), 90, np.uint8)
    img[30:90, 50:110] = 200
    Image.fromarray(img).save(views / "n01X-front.png")
    return MC.load_run(tmp)


class Contract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = fake_run(pathlib.Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_review_and_files_are_found(self):
        run = self.run
        self.assertEqual((run["unit"], run["run"], run["stem"]), ("n01X", "hard-v1", "n01X"))
        self.assertEqual(run["meta"]["stages"], {"1": "PASS", "2": "FAIL"})
        self.assertEqual(run["meta"]["verdict"], "FAIL")
        self.assertEqual(run["layout"], "unit")

    def test_missing_clay_and_masks_are_empty_cells(self):
        clay = MC.render_cell(self.run, "front", True)
        textured = MC.render_cell(self.run, "front", False)
        no_mask = MC.overlay_cell(self.run, "left")
        self.assertTrue(all(c.size == MC.CELL for c in (clay, textured, no_mask)))
        self.assertEqual(clay.getpixel((0, 0)), MC.EMPTY)
        self.assertEqual(no_mask.getpixel((0, 0)), MC.EMPTY)
        self.assertEqual(textured.getpixel((0, 0)), MC.BG)

    def test_textured_column_without_stage_2_shows_the_clay_labelled(self):
        run = self.run
        (run["views"] / "n01X-front.png").rename(run["views"] / "clay-front.png")
        run = MC.load_run(run["dir"])
        self.assertIsNone(run["stem"])
        cell = MC.render_cell(run, "front", False)
        clay = MC.render_cell(run, "front", True)
        self.assertEqual(cell.getpixel((0, 0)), (60, 60, 60))         # the label strip
        self.assertEqual(cell.crop((0, 40, *MC.CELL)).tobytes(), clay.crop((0, 40, *MC.CELL)).tobytes())
        self.assertEqual(CR.column_cell(run, "front", "textured").tobytes(), cell.tobytes())

    def test_overlay_marks_the_hit(self):
        cell = np.asarray(MC.overlay_cell(self.run, "front"))
        self.assertTrue((cell == MC.OVERLAY["hit"]).all(axis=2).any())

    def test_footer_numbers(self):
        text = "".join(p[0] for p in MC.footer_parts(self.run, "front"))
        self.assertIn("IoU 0.800", text)
        self.assertIn("PASS", text)
        self.assertIn("no measurement", "".join(p[0] for p in CR.cell_footer(self.run, "left")))

    def test_footer_coupling(self):
        r = {"iou": 0.8, "uncovered": 0.094, "spill": 0.031}
        for fn in (lambda: MC.coupling_parts(r), lambda: CR.cell_footer({"report": {"front": r}}, "front")):
            self.assertIn("bare 9% spill 3%", "".join(p[0] for p in fn()))
        self.assertEqual(MC.coupling_parts({"iou": 0.8}), [])


class WireColumn(unittest.TestCase):
    def test_wire_and_uv_columns_status_and_view_discovery(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        fake_run(tmp)
        (tmp / "review.md").write_text(REVIEW + "status: **placeholder**\n")
        run = MC.load_run(tmp)
        self.assertEqual(run["meta"]["status"], "placeholder")
        self.assertEqual(MC.COLUMNS[2::3], ("wire", "uv"))
        Image.new("RGB", (64, 64), 255).save(run["views"] / "wire-front.png")
        self.assertEqual(MC.find_views(tmp)[1], "n01X")          # wire-*.png is not a textured stem
        self.assertEqual(MC.wire_cell(run, "front").size, MC.CELL)
        self.assertEqual(MC.wire_cell(run, "left").getpixel((5, 5)), MC.EMPTY)   # absent -> empty cell
        self.assertEqual(MC.uv_cell(run, "left").getpixel((5, 5)), MC.EMPTY)     # first row only
        self.assertEqual(CR.column_cell(run, "front", "wire").size, MC.CELL)


class Score(unittest.TestCase):
    def run_dir(self, timing, approved, zones=None):
        tmp = pathlib.Path(tempfile.mkdtemp())
        (tmp / "review.md").write_text(REVIEW + timing)
        summary = {"approved": approved}
        if zones is not None:
            summary["zones"] = {"approved": {v: {"mean": z} for v, z in zones.items()}}
        (tmp / "silhouette.json").write_text(__import__("json").dumps(summary))
        return {"dir": tmp}

    def test_score_formula(self):
        timing = "- t_gen: 100.0 s\n- t_build: 200.0 s\n- t_passes: 0.0 s\n- t_colour: 300.0 s\n"
        sc = CR.score_of(self.run_dir(timing, {"front": 0.8, "left": 0.6}))       # IoU only
        self.assertAlmostEqual(sc[3], 600)
        self.assertAlmostEqual(sc[1], 0.5)
        self.assertAlmostEqual(sc[2], 0.7)
        self.assertAlmostEqual(sc[0], 0.3 * 0.5 + 0.7 * 0.7)
        sc = CR.score_of(self.run_dir(timing, {"front": 0.8, "left": 0.6}, {"front": 0.25, "left": 0.25}))
        self.assertAlmostEqual(sc[2], 0.6 * 0.7 + 0.4 * 0.5)                      # zones 0.25 / 0.5
        slow = CR.score_of(self.run_dir("- t_gen: 5000.0 s\n", {"front": 1.0}))
        self.assertEqual(slow[1], 0.0)                                            # f floors at 0

    def test_no_timing_or_no_iou_means_no_score(self):
        self.assertIsNone(CR.score_of(self.run_dir("", {"front": 0.8})))
        self.assertIsNone(CR.score_of(self.run_dir("- t_gen: 1.0 s\n", {})))
        self.assertIsNone(CR.times_of(pathlib.Path(tempfile.mkdtemp())))


if __name__ == "__main__":
    unittest.main()
