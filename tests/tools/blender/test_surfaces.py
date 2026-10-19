"""python3 -m unittest discover -s tests/tools/blender"""
import math
import pathlib
import sys
import unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import surfaces as SF  # noqa: E402

IRON = (0.431, 0.423, 0.408)


def old_metal(rgb, size=64):
    """The per-pixel painter texturize() used before surfaces.py, verbatim."""
    out = np.zeros((size, size, 3))
    cell = size // 4
    for x in range(size):
        tx, u = (x // cell), (x % cell) / (cell - 1.0)
        for y in range(size):
            ty = y // cell
            v = (y % cell) / (cell - 1.0)
            ramp = 0.30 + 0.85 * (v ** 1.1)
            trim = 1.35 if 0.62 < v < 0.70 else 1.0
            crease = 1.0 - 0.30 * math.exp(-((v - 0.22) ** 2) / 0.0022)
            mottle = 1.0 + 0.07 * math.sin(u * 17 + tx) * math.sin(v * 9 + ty)
            k = ramp * trim * crease * mottle
            out[y, x] = [min(1.0, c * k) for c in rgb]
    return out


class Paint(unittest.TestCase):
    def test_metal_is_the_approved_painter(self):
        np.testing.assert_allclose(SF.paint("metal", IRON, 64), old_metal(IRON, 64), atol=1e-12)

    def test_every_surface_is_in_range_and_varies(self):
        for name in SF.SURFACES:
            img = SF.paint(name, (0.5, 0.4, 0.3), 64)
            self.assertEqual(img.shape, (64, 64, 3), name)
            self.assertTrue(0.0 <= img.min() and img.max() <= 1.0, name)
            self.assertGreater(img.std(), 0.01, name)       # never a flat fill

    def test_glossy_surfaces_paint_a_brighter_highlight_than_cloth(self):
        rgb = (0.3, 0.3, 0.3)
        cloth = SF.paint("cloth", rgb, 64).max()
        for name in ("silk", "plastic", "chitin", "polished"):
            self.assertGreater(SF.paint(name, rgb, 64).max(), cloth, name)

    def test_white_highlight_on_plastic_tinted_on_metal(self):
        red = (0.6, 0.1, 0.1)
        hot = SF.paint("plastic", red, 64).reshape(-1, 3)
        top = hot[hot.sum(axis=1).argmax()]
        self.assertGreater(top[1], 0.5)                     # highlight goes toward white


class Decal(unittest.TestCase):
    def test_dots_are_opaque_and_background_clear(self):
        for kind, dots in SF.DECALS.items():
            rgb, alpha = SF.decal(kind, None, 64)
            self.assertEqual(alpha[0, 0], 0.0)
            cu, cv, _ = dots[0]
            self.assertGreater(alpha[int(cv * 64), int(cu * 64)], 0.9, kind)

    def test_glowing_eyes_take_the_colour(self):
        rgb, alpha = SF.decal("eyes2", (0.2, 0.9, 0.3), 64)
        ring = rgb[alpha > 0.9]
        self.assertGreater(ring[:, 1].mean(), ring[:, 0].mean())    # green dominates


class Layout(unittest.TestCase):
    def test_atlas_grid(self):
        self.assertEqual(SF.atlas_layout(1), (1, 1))
        self.assertEqual(SF.atlas_layout(4), (2, 2))
        self.assertEqual(SF.atlas_layout(5), (3, 2))


if __name__ == "__main__":
    unittest.main()
