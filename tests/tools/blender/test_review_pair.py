"""python3 -m unittest discover -s tests/tools/blender"""
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

try:
    from PIL import Image
except ImportError:
    raise unittest.SkipTest("Pillow is not installed")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import review_pair as RP  # noqa: E402
import spec_pipeline as SP  # noqa: E402


def png(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (60, 90), (200, 50, 50)).save(path)
    return path


def fake_shoot(glb, tilt, out, lit):
    return {"front": png(out / "f.png"), "rts": png(out / "r.png")}


class Pair(unittest.TestCase):
    def test_parse_vote(self):
        ok = 'sure {"sheet": "left", "sheet_why": "a", "artist": "right", "artist_why": "b"}'
        self.assertEqual(RP.parse_vote(ok)["artist"], "right")
        for bad in ("no json", '{"sheet": "middle", "artist": "left"}', '{"sheet": "left"}', "{oops}"):
            with self.subTest(bad=bad):
                self.assertIsNone(RP.parse_vote(bad))

    def test_sides_hold_both_orders(self):
        for seed in "abcdef":
            self.assertEqual(sorted(RP.sides(seed)), [False, True, True])

    def test_tally_line_gate_and_demote(self):
        def vote(sheet, artist, left_sheet, left_artist):
            return {"sheet": sheet, "artist": artist, "sheet_side": left_sheet, "artist_side": left_artist}

        votes = [vote("A", "B", "left", "right"), vote("A", "B", "right", "left"), vote("B", "B", "left", "right")]
        r = {"A": "v4", **RP.tally(votes)}
        self.assertEqual(RP.line(r), "pairwise vs v4: sheet A 2-1, artist B 3-0")
        self.assertFalse(RP.lost(r))
        every = [vote("A", "A", "left", "right"), vote("A", "A", "right", "left")] * 2
        self.assertTrue(RP.lost({"A": "v4", **RP.tally(every)}))
        self.assertEqual(RP.tally(every[:2])["sheet"]["winner"], "A")
        tie = RP.tally([vote("A", "A", "left", "left"), vote("B", "A", "right", "left")])
        self.assertEqual(tie["sheet"]["winner"], "tie")
        biased = RP.tally([vote("A", "A", "left", "left"), vote("A", "B", "left", "left"), vote("B", "A", "left", "left")])
        self.assertEqual((biased["sheet"]["winner"], biased["sheet"]["biased"]), ("tie", True))
        self.assertIn("(position bias)", RP.line({"A": "v4", **biased}))
        for status, down in (("final-use", "prototype-safe"), ("prototype-safe", "placeholder"),
                             ("placeholder", "rejected"), ("rejected", "rejected")):
            with self.subTest(status=status):
                self.assertEqual(RP.demote(status), down)

    def test_gate_demotes_only_when_both_axes_lost(self):
        def won(a, s, _):
            return {"sheet": {"winner": a}, "artist": {"winner": s}}
        summary = {"approved": {"front": 0.9}, "gates": {"front": 0.75}}
        for pw, want in ((None, "final-use"), (won("A", "A", 0), "prototype-safe"),
                         (won("A", "B", 0), "final-use"), (won("tie", "A", 0), "final-use")):
            with self.subTest(pw=pw):
                args = mock.Mock(summary=summary, pairwise=pw)
                self.assertEqual(SP.final_status(args, "PASS", []), want)

    def test_ask_vote_retries_once(self):
        good = '{"sheet": "left", "artist": "left"}'
        self.assertEqual(RP.ask_vote(mock.Mock(side_effect=["??", good]), "m", "i")["sheet"], "left")
        self.assertIsNone(RP.ask_vote(mock.Mock(side_effect=["??", RuntimeError("x")]), "m", "i"))

    def test_compare_with_stub_reviewer(self):
        """Reviewer that always prefers the old run: sides flip with the order, B loses both axes."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            a, b = tmp / "old", tmp / "new"
            for run in (a, b):
                run.mkdir()
                (run / "clay.glb").write_bytes(b"")
            seen = []

            def ask(model, brief, images):
                seen.append(images[0])
                left_is_a = RP.sides("u" + a.name + b.name)[int(images[0].stem[-1])]   # votes run in threads
                side = "left" if left_is_a else "right"
                return json.dumps({"sheet": side, "sheet_why": "x", "artist": side, "artist_why": "y"})

            panels = {"front": png(tmp / "p/f.png"), "rts": png(tmp / "p/r.png")}
            with mock.patch.object(RP, "shoot", fake_shoot), mock.patch.object(RP, "sheet_panels", return_value=panels):
                r = RP.compare(a, b, "u", ask=ask, work=tmp / "w")
            self.assertEqual((r["sheet"]["A"], r["artist"]["A"], r["valid_votes"]), (3, 3, 3))
            self.assertTrue(RP.lost(r))
            self.assertFalse(r["textured"])
            self.assertEqual(json.loads((b / "pairwise.json").read_text())["B"], "new")
            with Image.open(seen[0]) as im:
                self.assertEqual(im.size, (RP.CELL * 3, RP.CELL * 2))
            RP.append_review(b, r)
            self.assertIn("pairwise vs old: sheet A 3-0, artist A 3-0", (b / "review.md").read_text())


if __name__ == "__main__":
    unittest.main()
