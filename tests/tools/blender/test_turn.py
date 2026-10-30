"""python3 -m unittest discover -s tests/tools/blender  (F6 turntable, PIPELINE 21.F6)"""
import pathlib
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))
import silhouette as S  # noqa: E402


def grid(widths, heights=None):
    """4 x 2 page: a dark box per cell, widths[i] x heights[i] px, on grey."""
    heights = heights or [80] * 8
    page = np.full((240, 400, 3), 200, np.uint8)
    for i in range(8):
        r, c = divmod(i, 4)
        x0, y0 = c * 100 + 50 - widths[i] // 2, r * 120 + 100 - heights[i]
        page[y0:y0 + heights[i], x0:x0 + widths[i]] = (30, 30, 30)
    return page


def panels_of(page):
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "t.png"
        Image.fromarray(page).save(path)
        return S.turn_panels(path)


class Turn(unittest.TestCase):
    def test_panels_in_reading_order(self):
        panels = panels_of(grid([20, 24, 28, 32, 36, 40, 44, 48]))
        self.assertEqual(sorted(panels), list(S.TURN_ANGLES))
        widths = [S.crop(panels[a]).shape[1] for a in S.TURN_ANGLES]
        self.assertEqual(widths, sorted(widths))

    def test_coherent_sheet_passes(self):
        verdict = S.turn_check(panels_of(grid([40] * 8)))
        self.assertTrue(verdict["ok"], verdict)

    def test_subcases_that_fail(self):
        nicked = grid([40] * 8)
        nicked[140:220, 252:262] = 200      # same box, a slot cut in the 270 panel: not the mirror of 90
        cases = {"height": grid([40] * 8, [80, 80, 80, 80, 60, 80, 80, 80]),
                 "width": grid([40, 40, 40, 40, 60, 40, 40, 40]),
                 "mirror 90/270": nicked}
        for fail, page in cases.items():
            with self.subTest(fail):
                self.assertIn(fail, S.turn_check(panels_of(page))["fails"])

    def test_azimuth_windows(self):
        azim = S.turn_azimuths()
        self.assertEqual(len(azim), 36)
        self.assertTrue({25, 65, 295, 335, 205, 245}.issubset(azim))

    def test_match_picks_the_azimuth_and_side(self):
        shape = np.zeros((S.CANVAS_H, S.CANVAS_W), bool)
        shape[20:230, 100:200] = True
        other = np.zeros_like(shape)
        other[20:230, 100:300] = True
        model = {a: other for a in S.turn_azimuths()}
        model[335] = shape
        score, azim, side, nominal = S.turn_match(shape, model, 45)
        self.assertEqual((score, azim, side), (1.0, 335, "mirror"))
        self.assertLess(nominal, 1.0)


if __name__ == "__main__":
    unittest.main()
