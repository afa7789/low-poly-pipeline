"""python3 -m unittest discover -s tests/tools/blender"""
import json
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

    def test_table_is_append_only_and_full_at_64_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "atlas" / "human.json"
            cols = lambda keys: SA.extend(path, keys)["columns"]
            self.assertEqual(cols(["#000001:metal", "#000002:glow"]), ["#000001:metal", "#000002:glow"])
            self.assertEqual(cols(["#000002:glow", "#000003:skin", "#000003:skin"]),
                             ["#000001:metal", "#000002:glow", "#000003:skin"])      # nothing moves, no duplicates
            with self.assertRaises(ValueError):
                SA.extend(path, [f"#{i % 5 * 60:02X}{i // 5 % 5 * 60:02X}{i // 25 * 60:02X}:metal" for i in range(1, 2 + SA.COLUMNS)])
            self.assertEqual(len(cols([])), 3)                                       # a refused extension writes nothing


class Decals(unittest.TestCase):
    def test_decal_cells_append_without_moving_and_two_units_share_a_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "human.json"
            path.write_text('["#808080:metal"]')                                      # an old table (a bare list) loads
            first = SA.extend(path, ["#808080:metal"], [("aaaa", 16), ("bbbb", 32)])["decals"]
            self.assertEqual(first["bbbb"][2:], [32, 32])
            self.assertGreaterEqual(min(c[1] for c in first.values()), SA.TONE_ROWS)    # above the tone band
            again = SA.extend(path, [], [("aaaa", 16), ("cccc", 16)])["decals"]        # unit 2: same hash, one new cell
            self.assertEqual({k: again[k] for k in first}, first)
            self.assertEqual(len(again), 3)
            self.assertEqual(json.loads(path.read_text())["decals"], again)

    def test_decal_cells_never_overlap_and_a_full_band_refuses(self):
        decals = {}
        while (spot := SA.place(decals, 32)) is not None:
            decals[len(decals)] = [*spot, 32, 32]
        boxes = {(x + i, y + j) for x, y, w, h in decals.values() for i in range(0, w, 4) for j in range(0, h, 4)}
        self.assertEqual(len(boxes), 64 * len(decals))                            # 8 x 8 blocks each, no block twice
        self.assertEqual(len(decals), 12)                                         # (128 - 12 -> 3 rows of 32) x 4 per row


class Palette(unittest.TestCase):
    def test_hint_is_the_races_palette_and_empty_for_unknown(self):
        human = SA.palette_hint("Human")
        self.assertTrue(len(human) >= 4 and all(c.startswith("#") and len(c) == 7 for c in human))
        self.assertEqual(SA.palette_hint("nobody"), [])
        self.assertIn(human[0], SA.hint_text("Human"))
        self.assertEqual(SA.hint_text("nobody"), "")

    def test_snap_moves_a_near_colour_to_the_palette_and_leaves_a_far_one(self):
        palette = ["#808080", "#204060"]
        self.assertEqual(SA.snap("#828282:metal", palette), "#808080:metal")      # dE ~ .008 < SNAP_DE
        self.assertEqual(SA.snap("#A08080:skin", palette), "#A08080:skin")
        self.assertEqual(SA.snap("#828282:metal", []), "#828282:metal")


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
            got = SA.extend(path, ["#818181:metal", "#FF0000:skin", "#FE0101:skin"])["columns"]
            self.assertEqual(got, ["#808080:metal", "#202020:glow", "#FF0000:skin"])

    def test_column_is_two_texels_and_u_sits_on_their_seam(self):
        px = SA.image({"columns": ["#808080:metal", "#FF0000:skin"]})
        self.assertTrue(np.array_equal(px[:, 2], px[:, 3]) and not np.array_equal(px[:, 1], px[:, 2]))
        self.assertAlmostEqual(SA.u_of(1) * SA.SIZE, 3.0)                        # between texels 2 and 3


class Image(unittest.TestCase):
    def test_tone_cells_are_the_compact_atlas_cells_without_side_ink(self):
        px = SA.image({"columns": ["#808080:metal", "#808080:glow"]})
        self.assertEqual(px.shape, (SA.SIZE, SA.SIZE, 3))
        for tone in range(3):
            x, y, w, h = SA.tone_cell_xywh(0, tone)
            want = SF.tone_cell("metal", [128 / 255] * 3, tone, slope=0, width=4)[:, 1:3]
            self.assertTrue(np.allclose(px[y:y + h, x:x + w], want))
            self.assertLess(px[y, x, 0], px[y + 1, x, 0])                       # the ink row is darker than the colour rows
        self.assertTrue((px[SA.TONE_ROWS:] == 1.0).all() and (px[:, 4:] == 1.0).all())


if __name__ == "__main__":
    unittest.main()
