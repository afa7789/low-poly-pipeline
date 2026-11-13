"""Where the scripts that write game assets (buildings_*, map_*, fx_*) put them by default (tools/blender/game_paths.py)."""
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))
import game_paths as G  # noqa: E402


class OutArg(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.game = pathlib.Path(self.tmp.name)
        (self.game / "data").mkdir()
        (self.game / "data/models.tsv").write_text("unit_id\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_without_the_flag_the_default_is_the_games_own_assets_folder(self):
        with mock.patch.dict(os.environ, {"CF_GAME": str(self.game)}):
            got = G.out_arg(["all", "--render", "/r"], "--out", "buildings", "chaos")
        self.assertEqual(pathlib.Path(got), self.game.resolve() / "assets/buildings/chaos")

    def test_the_flag_overrides_the_default(self):
        with mock.patch.dict(os.environ, {"CF_GAME": str(self.game)}):
            self.assertEqual(G.out_arg(["all", "--out", "/elsewhere"], "--out", "castles"), "/elsewhere")

    def test_no_game_checkout_says_what_to_set(self):
        with mock.patch.dict(os.environ, {"CF_GAME": str(self.game / "missing")}), self.assertRaises(SystemExit):
            G.out_arg(["all"], "--out", "fx3d")


if __name__ == "__main__":
    unittest.main()
