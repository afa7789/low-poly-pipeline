"""python3 -m unittest discover -s tests/tools/blender"""
import pathlib
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import cut_hull as CH  # noqa: E402
import preflight as PF  # noqa: E402


def trapezoid_mask():
    """A 200 px figure: a trapezoid torso, widest at the shoulders (y 100-140 px from the top)."""
    m = np.zeros((200, 100), bool)
    for r in range(100, 140):
        half = 30 - (r - 100) // 4
        m[r, 50 - half:50 + half] = True
    m[0:100, 45:55] = True          # a head/neck column above, outside the strip
    m[140:200, 40:60] = True        # legs below
    return m


class StripOutline(unittest.TestCase):
    def test_fits_the_box_with_few_vertices(self):
        # figure 2.0 tall: rows 100-140 px from the top are y 1.0 down to 0.6
        poly = CH.strip_outline(trapezoid_mask(), (2.0, 0.0), (-0.3, 0.6, -0.3), (0.3, 1.0, 0.3), 0)
        self.assertIsNotNone(poly)
        self.assertLessEqual(len(poly), CH.LIMIT)
        xs, ys = zip(*poly)
        self.assertAlmostEqual(min(xs), -0.3, 3)
        self.assertAlmostEqual(max(xs), 0.3, 3)
        self.assertAlmostEqual(min(ys), 0.6, 3)
        self.assertAlmostEqual(max(ys), 1.0, 3)

    def test_taper_survives(self):
        poly = CH.strip_outline(trapezoid_mask(), (2.0, 0.0), (-0.3, 0.6, -0.3), (0.3, 1.0, 0.3), 0)
        top = [x for x, y in poly if y > 0.95]
        bottom = [x for x, y in poly if y < 0.65]
        self.assertGreater(max(top) - min(top), max(bottom) - min(bottom))   # shoulders wider than the waist

    def test_empty_or_thin_strip_is_none(self):
        box = ((-0.3, 1.9, -0.3), (0.3, 1.91, 0.3))
        self.assertIsNone(CH.strip_outline(trapezoid_mask(), (2.0, 0.0), *box, 0))


class Wiring(unittest.TestCase):
    def test_only_cut_parts_ask(self):
        plain = ["spine", "prism", [0.4, 0.4, 0.8], [0, 1.8, 0], "iron", {}]
        cut = ["spine", "prism", [0.4, 0.4, 0.8], [0, 1.8, 0], "iron", {"cut": "sheet"}]
        self.assertFalse(CH.wants_cut(plain[5]))
        self.assertTrue(CH.wants_cut(cut[5]))
        with tempfile.TemporaryDirectory() as work:     # no cut part: no argument, no sheet read
            self.assertEqual(CH.args({"parts": [plain]}, "missing.jpg", "mass", work), [])

    def test_preflight_counts_a_cut_part(self):
        part = ["spine", "prism", [0.4, 0.4, 0.8], [0, 1.8, 0], "iron", {"cut": "sheet", "sides": 8}]
        self.assertEqual(PF.part_tris(part), PF.CUT_TRIS)
        self.assertEqual(PF.bbox(part), ((-0.4, 1.4, -0.4), (0.4, 2.2, 0.4)))


if __name__ == "__main__":
    unittest.main()
