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
        for name in ("silk", "plastic", "polished"):
            self.assertGreater(SF.paint(name, rgb, 64).max(), cloth, name)

    def test_white_highlight_on_plastic_tinted_on_metal(self):
        red = (0.6, 0.1, 0.1)
        hot = SF.paint("plastic", red, 64).reshape(-1, 3)
        top = hot[hot.sum(axis=1).argmax()]
        self.assertGreater(top[1], 0.5)                     # highlight goes toward white


class Organic(unittest.TestCase):
    def test_new_surfaces_are_registered_and_the_brief_lists_them(self):
        for name in ("bark", "slime", "flesh"):
            self.assertIn(name, SF.SURFACES)

    def test_chitin_is_matte_next_to_polished_armour(self):
        rgb = (0.4, 0.3, 0.2)
        self.assertLess(SF.paint("chitin", rgb, 64).max(), SF.paint("polished", rgb, 64).max())

    def test_bark_furrows_run_vertically(self):
        img = SF.paint("bark", (0.4, 0.3, 0.2), 64)[:16, :16].mean(axis=2)   # one cell
        across, along = np.abs(np.diff(img, axis=1)).mean(), np.abs(np.diff(img, axis=0)).mean()
        self.assertGreater(across, along)         # tone changes across the cell more than up it

    def test_wet_surfaces_carry_a_highlight_wood_does_not(self):
        rgb = (0.3, 0.4, 0.2)
        self.assertGreater(SF.paint("slime", rgb, 64).max(), SF.paint("wood", rgb, 64).max())
        self.assertGreater(SF.paint("flesh", rgb, 64).max(), SF.paint("cloth", rgb, 64).max())

    def test_wood_has_a_dark_joint_between_boards(self):
        img = SF.paint("wood", (0.5, 0.4, 0.3), 64)[8, :16].mean(axis=1)
        self.assertLess(img.min(), 0.8 * img.max())


class Cel(unittest.TestCase):
    def test_tone_follows_the_face_orientation(self):
        for nz, want in ((1.0, 0), (0.6, 0), (0.0, 1), (-0.3, 1), (-0.5, 2), (-1.0, 2)):
            self.assertEqual(SF.tone_index(nz), want, nz)

    def test_cells_are_flat_light_mid_dark(self):
        rgb = (0.4, 0.4, 0.4)
        img = SF.paint_cel("metal", rgb, 64)
        cell = 16
        tones = [img[c // 4 * cell + 2:(c // 4 + 1) * cell - 2, c % 4 * cell + 2:(c % 4 + 1) * cell - 2]
                 for c in range(3)]                                 # inside the ink border
        for t in tones:
            self.assertAlmostEqual(float(t.std()), 0.0)             # no pattern, no gloss inside a cell
        lit, mid, dark = (float(t[0, 0, 0]) for t in tones)
        self.assertGreater(lit, mid)
        self.assertGreater(mid, dark)
        self.assertAlmostEqual(mid, 0.4)                      # the sheet colour is the side tone

    def test_cell_border_is_ink_but_glow_has_none(self):
        img = SF.paint_cel("metal", (0.4,) * 3, 256)             # 64-px cells: 2-px border
        mid = img[64 + 8, 64 + 8]                                 # cell 5, inside
        for y, x in ((64, 64 + 8), (64 + 63, 64 + 8), (64 + 8, 64 + 1), (64 + 8, 64 + 62)):
            self.assertAlmostEqual(float(img[y, x][0] / mid[0]), SF.INK)
        self.assertGreater(float(img[64 + 2, 64 + 2][0]), SF.INK * float(mid[0]))     # past the border
        glow = SF.paint_cel("glow", (0.5,) * 3, 256)
        self.assertEqual(float(glow[0, 0, 0]), float(glow[8, 8, 0]))

    def test_glow_stays_one_tone_and_wet_tops_are_lighter(self):
        glow = SF.paint_cel("glow", (0.5, 0.5, 0.5), 64)
        self.assertEqual(float(glow[0, 0, 0]), float(glow[0, 16, 0]))
        slime, plain = SF.paint_cel("slime", (0.4,) * 3, 64), SF.paint_cel("chitin", (0.4,) * 3, 64)
        self.assertGreater(float(slime[0, 0, 0]), float(plain[0, 0, 0]))


class Decal(unittest.TestCase):
    def test_dots_are_opaque_and_background_clear(self):
        for kind, dots in SF.DECALS.items():
            if not dots:                      # "sheet": painted from the sheet's head, no dots
                continue
            rgb, alpha = SF.decal(kind, None, 64)
            self.assertEqual(alpha[0, 0], 0.0)
            cu, cv = dots[0][:2]
            self.assertGreater(alpha[int(cv * 64), int(cu * 64)], 0.9, kind)

    def test_glowing_eyes_take_the_colour(self):
        rgb, alpha = SF.decal("eyes2", (0.2, 0.9, 0.3), 64)
        ring = rgb[alpha > 0.9]
        self.assertGreater(ring[:, 1].mean(), ring[:, 0].mean())    # green dominates

    def test_mask_is_dark_with_glowing_eyes(self):
        rgb, alpha = SF.decal("mask", (0.9, 0.1, 0.1), 64)
        self.assertGreater(alpha[32, 32], 0.9)
        self.assertLess(rgb[32, 32].max(), 0.1)                      # dark fill between the eyes
        eye = rgb[int(0.56 * 64), int(0.33 * 64)]
        self.assertGreater(eye[0], 0.8)                              # eye lit in the decal colour
        pale = SF.decal("mask", None, 64)[0][int(0.56 * 64), int(0.33 * 64)]
        self.assertGreater(pale.max(), 0.8)                          # no colour: still lit

    def test_face_has_dark_mouth_and_eyes(self):
        rgb, alpha = SF.decal("face", (0.2, 0.9, 0.3), 64)
        mouth = rgb[int(0.27 * 64), int(0.50 * 64)]
        self.assertLess(mouth.max(), 0.1)                            # mouth stays dark when eyes glow
        self.assertGreater(alpha[int(0.64 * 64), int(0.32 * 64)], 0.9)


class Layout(unittest.TestCase):
    def test_atlas_grid(self):
        self.assertEqual(SF.atlas_layout(1), (1, 1))
        self.assertEqual(SF.atlas_layout(4), (2, 2))
        self.assertEqual(SF.atlas_layout(5), (3, 2))


if __name__ == "__main__":
    unittest.main()
