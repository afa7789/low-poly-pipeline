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

    def test_cells_are_ramps_with_the_tone_at_the_typical_height(self):
        img = SF.paint_cel("metal", (0.4, 0.4, 0.4), 256, slope=0.5)     # 64-px cells, 8-px slots
        slot = 64 // SF.RAMP_SLOTS
        for c, v0 in enumerate(SF.TONE_V):
            col = 4 + (c % 4) * 64
            rows = [float(img[(c // 4) * 64 + j * slot + 4, col, 0]) for j in range(SF.RAMP_SLOTS)]
            self.assertEqual(rows, sorted(rows), c)                      # dark at the bottom, light on top
            self.assertAlmostEqual(rows[min(int(v0 * SF.RAMP_SLOTS), SF.RAMP_SLOTS - 1)], 0.4 * SF.CEL_TONES[c], delta=0.4 * 0.07)
            self.assertAlmostEqual(float(img[(c // 4) * 64 + 4, col + 20, 0]), rows[0])   # flat along u

    def test_default_cells_are_flat(self):
        img = SF.paint_cel("metal", (0.4,) * 3, 256)
        inside = img[4:60, 4:60, 0]                               # cell 0, clear of the ink rows
        slot = 64 // SF.RAMP_SLOTS
        self.assertAlmostEqual(float(inside[slot * 2, 20]), float(inside[slot * 6, 20]))

    def test_ramp_slope_is_the_measured_width_over_the_tone_and_capped(self):
        self.assertAlmostEqual(SF.ramp_slope((0.4, 0.5), (0.5, 0.5, 0.5)), 0.2)
        self.assertEqual(SF.ramp_slope((0.5, 0.5), (0.5, 0.5, 0.5)), 0.0)
        self.assertEqual(SF.ramp_slope((0.0, 1.0), (0.5, 0.5, 0.5)), SF.RAMP_MAX)

    def test_slot_border_is_ink_but_glow_has_none(self):
        img = SF.paint_cel("metal", (0.4,) * 3, 256)             # 8-px slots in 64-px cells: 1-px ink on all sides
        mid = float(img[64 + 12, 64 + 8][0])                      # cell 5, slot 1, inside
        for y, x in ((64 + 8, 64 + 8), (64 + 15, 64 + 8), (64 + 12, 64 + 1), (64 + 12, 64 + 62)):
            self.assertAlmostEqual(float(img[y, x][0] / mid), SF.INK, delta=0.02)
        glow = SF.paint_cel("glow", (0.5,) * 3, 256)
        self.assertEqual(float(glow[0, 0, 0]), float(glow[8, 8, 0]))

    def test_ramp_slot_follows_normal_and_height_and_chamfers_take_the_top(self):
        self.assertEqual(SF.ramp_slot(1.0, 1.0), SF.RAMP_SLOTS - 1)
        self.assertEqual(SF.ramp_slot(-1.0, 0.0), 0)
        self.assertLess(SF.ramp_slot(0.0, 0.1), SF.ramp_slot(0.0, 0.9))
        self.assertEqual(SF.ramp_slot(-1.0, 0.0, chamfer=True), SF.RAMP_SLOTS - 1)
        # the face's v range stays inside its slot, so its sampled texels are that slot's
        lo, hi = SF.slot_v(3, 0.0), SF.slot_v(3, 1.0)
        self.assertTrue(3 / SF.RAMP_SLOTS < lo < hi < 4 / SF.RAMP_SLOTS)

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


class CompactAtlas(unittest.TestCase):
    SIZES = [(16, 4)] * 20 + [(32, 32)] * 3 + [(16, 16)] * 2 + [(16, 16)]

    def test_pack_cells_inside_disjoint_pot(self):
        w, h, pos = SF.pack_cells(self.SIZES)
        self.assertTrue(all(n & (n - 1) == 0 for n in (w, h)))
        used = np.zeros((h, w), int)
        for (x, y), (cw, ch) in zip(pos, self.SIZES):
            self.assertTrue(x + cw <= w and y + ch <= h)
            used[y:y + ch, x:x + cw] += 1
        self.assertEqual(used.max(), 1)                              # no overlap

    def test_pack_cells_padding_and_alignment(self):
        _, _, pos = SF.pack_cells(self.SIZES, align=8, pad=2)
        self.assertTrue(all(x % 8 == 0 and y % 8 == 0 for x, y in pos))

    def test_flat_cell_rows_and_ink(self):
        cell = SF.tone_cell("metal", (0.5, 0.5, 0.5), 1)
        self.assertEqual(cell.shape, (SF.FLAT_ROWS, SF.TONE_W, 3))
        self.assertLess(cell[0, 5, 0], cell[2, 5, 0])                # ink row under the colour rows
        self.assertLess(cell[2, 0, 0], cell[2, 5, 0])                # ink column
        ramp = SF.tone_cell("metal", (0.5, 0.5, 0.5), 1, slope=0.4)
        self.assertEqual(ramp.shape[0], SF.COMPACT_ROWS)
        self.assertGreater(ramp[2 * 7 + 1, 5, 0], ramp[1, 5, 0])     # the ramp climbs slot by slot

    def test_face_row_never_samples_ink(self):
        for t in (0.0, 0.5, 1.0):
            self.assertTrue(1 <= int(SF.face_row(SF.FLAT_ROWS, 0, t)) <= 3)
            for slot in range(SF.RAMP_SLOTS):
                row = SF.face_row(SF.COMPACT_ROWS, slot, t)
                self.assertEqual(int(row) % SF.SLOT_PX, 1)           # the slot's upper row, ink is the lower
                self.assertLess(row, SF.COMPACT_ROWS)


if __name__ == "__main__":
    unittest.main()
