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
        ok = 'sure {"sheet": "left", "sheet_why": "a", "artist": "right", "artist_why": "b", "wc3": "left", "form": "right"}'
        self.assertEqual(RP.parse_vote(ok)["artist"], "right")
        for bad in ("no json", '{"sheet": "middle", "artist": "left", "wc3": "left", "form": "left"}',
                    '{"sheet": "left", "artist": "left", "wc3": "left"}', "{oops}"):
            with self.subTest(bad=bad):
                self.assertIsNone(RP.parse_vote(bad))

    def test_sides_hold_both_orders(self):
        self.assertEqual(RP.sides(), [True, True, False, False])

    def test_tally_line_gate_and_demote(self):
        def vote(sheet, artist, wc3, sides, form="B"):
            """picks (A/B) and the physical side of each axis"""
            sides = (*sides, sides[1])
            return {"sheet": sheet, "artist": artist, "wc3": wc3, "form": form,
                    **{f"{a}_side": d for a, d in zip(RP.AXES, sides)}}

        L, R = "left", "right"
        votes = [vote("A", "B", "B", (L, R, R)), vote("A", "B", "A", (R, L, L)),
                 vote("B", "B", "B", (L, R, R)), vote("A", "B", "A", (R, L, L))]
        r = {"A": "v4", **RP.tally(votes)}
        self.assertEqual(RP.line(r), "pairwise vs v4: sheet A 3-1, artist B 4-0, wc3 tie 2-2, form B 4-0")
        self.assertFalse(RP.lost(r))                       # 1 of 4 lost
        lost2 = RP.tally([vote("A", "A", "B", (L, R, L), "A"), vote("A", "A", "B", (R, L, R), "A")] * 2)
        self.assertTrue(RP.lost({"A": "v4", **lost2}))     # sheet + artist + form lost, wc3 won
        self.assertEqual(RP.tally(votes[:3])["sheet"]["winner"], "A")   # 3 valid votes: no tie possible
        one_axis = {"sheet": {"winner": "B"}, "artist": {"winner": "A"}, "wc3": {"winner": "tie"}}
        self.assertFalse(RP.lost(one_axis))
        two_of_four = {**one_axis, "wc3": {"winner": "B"}, "form": {"winner": "A"}}
        self.assertFalse(RP.lost(two_of_four))             # 2-2 over four axes is not a loss
        self.assertTrue(RP.lost({**two_of_four, "wc3": {"winner": "A"}}))
        old = {"sheet": {"winner": "A"}, "artist": {"winner": "A"}}
        self.assertTrue(RP.lost(old))                      # result written before the wc3 axis
        biased = RP.tally([vote("A", "A", "A", (L, L, L)), vote("A", "B", "B", (L, L, L)),
                           vote("B", "A", "A", (L, L, L)), vote("B", "B", "B", (L, L, L))])
        self.assertEqual((biased["sheet"]["winner"], biased["sheet"]["biased"]), ("tie", True))
        self.assertIn("(position bias)", RP.line({"A": "v4", **biased}))
        for status, down in (("final-use", "prototype-safe"), ("prototype-safe", "placeholder"),
                             ("placeholder", "rejected"), ("rejected", "rejected")):
            with self.subTest(status=status):
                self.assertEqual(RP.demote(status), down)

    def test_gate_demotes_only_when_both_axes_lost(self):
        def won(a, s, w):
            return {"sheet": {"winner": a}, "artist": {"winner": s}, "wc3": {"winner": w}}
        summary = {"approved": {"front": 0.9}, "gates": {"front": 0.75}}
        for pw, want in ((None, "final-use"), (won("A", "A", "B"), "prototype-safe"),
                         (won("A", "B", "A"), "prototype-safe"), (won("A", "B", "tie"), "final-use"),
                         (won("tie", "A", "B"), "final-use")):
            with self.subTest(pw=pw):
                args = mock.Mock(summary=summary, pairwise=pw)
                self.assertEqual(SP.final_status(args, "PASS", []), want)

    def test_wc3_ref_and_crop(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            big = tmp / "big.png"
            im = Image.new("RGB", (400, 300), (60, 60, 60))
            im.paste(Image.new("RGB", (20, 40), (200, 30, 30)), (100, 100))
            im.save(big)
            with Image.open(RP.crop_figure(big, tmp / "c.png")) as c:
                self.assertLess(c.width, 60)
            panels = {"front": tmp / "proxy.png"}
            with mock.patch.object(RP, "sheet_panels", return_value=panels):
                self.assertEqual(RP.wc3_ref("spider", "u", "mass", tmp), (panels["front"], True))
            with mock.patch.dict(RP.WC3_REFS, {"biped": str(big)}), mock.patch.object(RP, "ROOT", pathlib.Path("/")):
                self.assertEqual(RP.wc3_ref("biped", "u", "mass", tmp), (tmp / "wc3-ref.png", False))

    def test_compare_runs_shows_votes(self):
        import compare_runs as CR
        with tempfile.TemporaryDirectory() as tmp:
            run = {"dir": tmp}
            self.assertEqual(CR.pair_text(run), "")
            ab = {"A": 1, "B": 3, "winner": "B"}
            (pathlib.Path(tmp) / "pairwise.json").write_text(json.dumps(
                {"A": "v7", "sheet": ab, "artist": ab, "wc3": {"A": 2, "B": 2, "winner": "tie"}}))
            self.assertEqual(CR.pair_text(run), "  pair vs v7 S B3-1 R B3-1 W tie2-2")

    def test_ask_vote_retries_once(self):
        good = '{"sheet": "left", "artist": "left", "wc3": "right", "form": "left"}'
        self.assertEqual(RP.ask_vote(mock.Mock(side_effect=["??", good]), "m", "i")["sheet"], "left")
        self.assertIsNone(RP.ask_vote(mock.Mock(side_effect=["??", RuntimeError("x")]), "m", "i"))

    def test_compare_with_stub_reviewer(self):
        """Reviewer that always prefers the old run: sides flip with the order, B loses 2 of 3 axes."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            a, b = tmp / "old", tmp / "new"
            for run in (a, b):
                run.mkdir()
                (run / "clay.glb").write_bytes(b"")
            seen = []

            def ask(model, brief, images):
                seen.append(images[0])
                left_is_a = RP.sides()[int(images[0].stem[-1])]   # votes run in threads
                side = "left" if left_is_a else "right"
                return json.dumps({"sheet": side, "sheet_why": "x", "artist": side, "artist_why": "y",
                                   "wc3": side, "wc3_why": "z", "form": side, "form_why": "w"})

            panels = {"front": png(tmp / "p/f.png"), "rts": png(tmp / "p/r.png")}
            with mock.patch.object(RP, "shoot", fake_shoot), mock.patch.object(RP, "sheet_panels", return_value=panels):
                r = RP.compare(a, b, "u", ask=ask, work=tmp / "w")
            self.assertEqual((r["sheet"]["A"], r["wc3"]["A"], r["valid_votes"]), (4, 4, 4))
            self.assertTrue(RP.lost(r))
            self.assertFalse(r["textured"])
            self.assertEqual(json.loads((b / "pairwise.json").read_text())["B"], "new")
            self.assertTrue(r["wc3_proxy"])                # no rig in the stub run: the sheet-hard proxy
            with Image.open(seen[0]) as im:
                self.assertEqual(im.size, (RP.CELL * 4, RP.CELL * 2))
            RP.append_review(b, r)
            self.assertIn("pairwise vs old: sheet A 4-0, artist A 4-0, wc3 A 4-0", (b / "review.md").read_text())


if __name__ == "__main__":
    unittest.main()
