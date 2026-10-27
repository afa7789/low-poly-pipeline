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

    def test_overlay_marks_the_hit(self):
        cell = np.asarray(MC.overlay_cell(self.run, "front"))
        self.assertTrue((cell == MC.OVERLAY["hit"]).all(axis=2).any())

    def test_footer_numbers(self):
        text = "".join(p[0] for p in MC.footer_parts(self.run, "front"))
        self.assertIn("IoU 0.800", text)
        self.assertIn("PASS", text)
        self.assertIn("no measurement", "".join(p[0] for p in CR.cell_footer(self.run, "left")))


if __name__ == "__main__":
    unittest.main()
