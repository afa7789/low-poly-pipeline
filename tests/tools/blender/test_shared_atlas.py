"""python3 -m unittest discover -s tests/tools/blender"""
import pathlib
import sys
import tempfile
import unittest

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import shared_atlas as SA  # noqa: E402
import surfaces as SF  # noqa: E402


class Table(unittest.TestCase):
    def test_key_is_hex_and_surface(self):
        self.assertEqual(SA.key((0.431, 0.423, 0.408), "metal"), "#6E6C68:metal")

    def test_table_is_append_only_and_full_at_32_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "atlas" / "human.json"
            self.assertEqual(SA.extend(path, ["#000001:metal", "#000002:glow"]), ["#000001:metal", "#000002:glow"])
            self.assertEqual(SA.extend(path, ["#000002:glow", "#000003:skin", "#000003:skin"]),
                             ["#000001:metal", "#000002:glow", "#000003:skin"])      # nothing moves, no duplicates
            with self.assertRaises(ValueError):
                SA.extend(path, [f"#{i * 0x080808:06X}:metal" for i in range(1, 2 + SA.COLUMNS)])
            self.assertEqual(len(SA.extend(path, [])), 3)                            # a refused extension writes nothing


class Merge(unittest.TestCase):
    def test_close_colours_of_one_surface_share_a_column_far_or_other_surface_do_not(self):
        table = ["#808080:metal"]
        self.assertEqual(SA.find(table, "#818181:metal"), 0)          # dE ~ .004
        self.assertIsNone(SA.find(table, "#A08080:metal"))             # dE well above MERGE_DE
        self.assertIsNone(SA.find(table, "#818181:skin"))              # same colour, other surface
        self.assertEqual(SA.find(table, "#808080:metal"), 0)

    def test_extend_reuses_a_matching_column_and_old_tables_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "old.json"
            path.write_text('["#808080:metal", "#202020:glow"]')                 # a table written before the merge
            got = SA.extend(path, ["#818181:metal", "#FF0000:skin", "#FE0101:skin"])
            self.assertEqual(got, ["#808080:metal", "#202020:glow", "#FF0000:skin"])

    def test_column_is_two_texels_and_u_sits_on_their_seam(self):
        px = SA.image(["#808080:metal", "#FF0000:skin"])
        self.assertTrue(np.array_equal(px[:, 2], px[:, 3]) and not np.array_equal(px[:, 1], px[:, 2]))
        self.assertAlmostEqual(SA.u_of(1) * SA.SIZE, 3.0)                        # between texels 2 and 3


class Image(unittest.TestCase):
    def test_flat_cel_tones_sit_at_tone_v_rows(self):
        px = SA.image(["#808080:metal"])
        self.assertEqual(px.shape, (SA.SIZE, SA.SIZE, 3))
        for tone, mult in enumerate(SF.CEL_TONES):                 # the row a face of that tone maps to
            row = round(SF.TONE_V[tone] * (SA.SIZE - 1))
            self.assertAlmostEqual(px[row, 0, 0], min(1.0, 128 / 255 * mult), delta=0.002)   # row 32 of 63 is v .508, not .5

    def test_ramp_runs_dark_to_light_glow_is_flat_unused_columns_white(self):
        px = SA.image(["#808080:metal", "#808080:glow"])
        self.assertTrue((np.diff(px[:, 0, 0]) > 0).all())
        self.assertTrue(np.allclose(px[:, 2], px[0, 2]))
        self.assertTrue((px[:, 4:] == 1.0).all())


if __name__ == "__main__":
    unittest.main()
