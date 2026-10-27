"""python3 -m unittest discover -s tests/tools/blender"""
import pathlib
import sys
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "artifacts/model-sheets"))
import redo_topbottom as RT  # noqa: E402


def sheet(blob_rows):
    a = np.full((120, 60, 3), 200, np.uint8)
    for y0, y1 in blob_rows:
        a[y0:y1, 10:50] = (30, 30, 30)
    return Image.fromarray(a)


class CutRow(unittest.TestCase):
    def test_cut_lies_in_the_empty_band(self):
        img = sheet([(5, 40), (80, 115)])
        y = RT.cut_row(img, img)
        self.assertTrue(40 <= y < 80)

    def test_none_without_a_band(self):
        img = sheet([(5, 115)])
        self.assertIsNone(RT.cut_row(img, img))


if __name__ == "__main__":
    unittest.main()
