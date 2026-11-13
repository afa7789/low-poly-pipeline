"""tools/hand_models_install.py: copies hand and output GLBs into <game>/assets/units/<id>/ and repoints
data/models.tsv; tools/blender/game_paths.py: CF_GAME resolution."""
import json
import os
import pathlib
import struct
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/blender"))
import game_paths  # noqa: E402
import hand_models_install as I  # noqa: E402

HEADER = ["unit_id", "name", "url", "sha256", "clip_idle", "clip_walk", "clip_attack", "clip_death", "clip_spell",
          "license", "credit"]


def glb(path, clips):
    doc = json.dumps({"animations": [{"name": n} for n in clips]}).encode()
    doc += b" " * (-len(doc) % 4)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(struct.pack("<III", 0x46546C67, 2, 20 + len(doc)) + struct.pack("<II", len(doc), 0x4E4F534A)
                     + doc)


class InstallTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = pathlib.Path(tmp.name)
        self.game, self.hand, self.sheets = self.tmp / "game", self.tmp / "hand", self.tmp / "sheets"
        glb(self.hand / "e00E/model.glb", ["attack", "attack2", "death", "idle", "spell", "walk"])
        (self.hand / "e00E/model.palette.png").write_bytes(b"png")
        glb(self.sheets / "runs/draft/perk_tower/v/model.glb", ["idle"])
        rows = [["e00E", "Twins", "artifacts/model-sheets/hand/e00E/model.glb"],
                ["n02L", "Twin Smiley", "artifacts/model-sheets/hand/e00E/model.glb"],
                ["perk_tower", "Tower", "artifacts/model-sheets/runs/draft/perk_tower/v/model.glb"],
                ["hfoo", "Footman", "https://example.org/f.glb"]]
        lines = ["\t".join(HEADER)] + ["\t".join(r + ["x", "-1", "-1", "-1", "-1", "-1", "cc0", "c"]) for r in rows]
        (self.game / "data").mkdir(parents=True)
        (self.game / "data/models.tsv").write_text("\n".join(lines) + "\n")
        self.where = {"hand": self.hand, "sheets": self.sheets}

    def rows(self, text):
        lines = text.splitlines()
        return {r[0]: dict(zip(HEADER, r)) for r in (line.split("\t") for line in lines[1:])}

    def test_copies_and_repoints(self):
        text, changed, kept, hand, copies = I.plan(self.game, **self.where)
        rows = self.rows(text)
        self.assertEqual(rows["e00E"]["url"], "assets/units/e00E/model.glb")
        self.assertEqual(rows["n02L"]["url"], "assets/units/e00E/model.glb")      # shared model, one copy
        self.assertEqual((rows["e00E"]["clip_attack"], rows["e00E"]["clip_walk"]), ("0,1", "5"))
        self.assertEqual(rows["e00E"]["license"], "project-own")
        self.assertEqual(rows["perk_tower"]["url"], "assets/units/perk_tower/model.glb")
        self.assertEqual((rows["perk_tower"]["license"], rows["perk_tower"]["clip_idle"]), ("cc0", "-1"))
        self.assertEqual(rows["hfoo"]["url"], "https://example.org/f.glb")
        self.assertEqual((kept, hand), (["hfoo"], {"e00E", "n02L"}))
        self.assertEqual(len(copies), 3)                                          # 2 GLBs + 1 palette
        refresh = self.tmp / "refresh.tsv"
        refresh.write_text("unit_id\nn02L\nhpea\n")
        refresh_text, dropped = I.refresh(hand, refresh)
        I.write(self.game, text, copies, refresh_text, refresh)
        self.assertEqual(dropped, 1)
        self.assertEqual((self.game / "assets/units/e00E/model.palette.png").read_bytes(), b"png")
        self.assertEqual(I.plan(self.game, **self.where)[1], [])                  # second run: nothing left

    def test_only_listed_ids(self):
        text, changed, kept, hand, copies = I.plan(self.game, {"perk_tower"}, **self.where)
        self.assertEqual((changed, hand), (["perk_tower"], set()))
        self.assertEqual(self.rows(text)["e00E"]["url"], "artifacts/model-sheets/hand/e00E/model.glb")

    def test_game_paths(self):
        with mock.patch.dict(os.environ, {"CF_GAME": str(self.game)}):
            self.assertEqual(game_paths.game(), self.game.resolve())
        with mock.patch.dict(os.environ, {"CF_GAME": str(self.tmp / "nope")}), self.assertRaises(SystemExit) as e:
            game_paths.game()
        self.assertIn("set CF_GAME", str(e.exception))
        with mock.patch.dict(os.environ, {"CF_PIPELINE_OUT": str(self.tmp / "out")}):
            self.assertEqual(game_paths.output(), (self.tmp / "out").resolve())


if __name__ == "__main__":
    unittest.main()
