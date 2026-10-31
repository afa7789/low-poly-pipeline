"""L18-1: fusing the near colours of an eye DSL (eye_fuse.py). Pure python."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))
import eye_fuse as F  # noqa: E402


def piece(name, mat, colour=None, sides=8):
    p = {"op": "tube", "name": name, "mat": mat, "bone": "spine", "role": "torso", "r0": 0.1, "r1": 0.1, "length": 0.5, "at": [0, 0, 1], "sides": sides}
    return dict(p, colour=colour) if colour else p


class Fuse(unittest.TestCase):
    def test_oklab_round_trip_and_classes(self):
        for h in ("000000", "FFFFFF", "6B6F3C", "3A5FCD", "C8A06F"):
            with self.subTest(hex=h):
                self.assertEqual(F.hex_of(F.oklab(h)), h)
        for mat, cls in (("lamp_glow", "glow"), ("lens_L", "glass"), ("skin", "skin"), ("coat", "other"), ("Furnace", "glow")):
            with self.subTest(mat=mat):
                self.assertEqual(F.class_of(mat), cls)

    def test_near_colours_fuse_classes_never_and_the_ceiling_holds(self):
        cases = {
            "two near greys fuse, the heavier keeps its name": (
                {"colours": {"coat": "3A3A3F", "belt": "3C3B40", "skin": "C8A06F"}, "pieces": [piece("a", "coat"), piece("b", "coat"), piece("c", "belt"), piece("d", "skin")]},
                12, {"coat", "skin"}, 1),
            "a glow never melts into a dark coat of the same hue": (
                {"colours": {"coat": "3A3A3F", "lamp": "3B3B40"}, "pieces": [piece("a", "coat"), piece("b", "lamp")]}, 12, {"coat", "lamp"}, 0),
            "skin stays apart from cloth even when close": (
                {"colours": {"cloth": "C8A070", "skin": "C8A06F"}, "pieces": [piece("a", "cloth"), piece("b", "skin")]}, 12, {"cloth", "skin"}, 0),
            "over the ceiling the closest pair of a class fuses until it fits": (
                {"colours": {f"m{i}": f"{40 + 30 * i:02X}{40 + 30 * i:02X}{40 + 30 * i:02X}" for i in range(6)}, "pieces": [piece(f"p{i}", f"m{i}") for i in range(6)]},
                3, None, 3),
            "a piece with its own colour is its own material first": (
                {"colours": {"coat": "3A3A3F"}, "pieces": [piece("a", "coat"), piece("b", "coat", "F0F0F0")]}, 12, {"coat", "coat_"}, 0),
        }
        for name, (dsl, ceiling, want, merges) in cases.items():
            with self.subTest(case=name):
                out, log = F.fuse(dsl, max_mats=ceiling)
                self.assertEqual(len(log["merges"]), merges)
                self.assertLessEqual(log["after"], max(ceiling, log["classes"]["glow"] + log["classes"]["glass"] + log["classes"]["skin"] + 1))
                if want is not None:
                    self.assertEqual(set(out["colours"]), want)
                self.assertTrue(all(p["mat"] in out["colours"] and "colour" not in p for p in out["pieces"]))
                self.assertEqual(len(out["pieces"]), len(dsl["pieces"]))
        self.assertEqual(F.fuse(cases["two near greys fuse, the heavier keeps its name"][0])[0]["colours"]["coat"], "3B3A3F")   # the weighted mean in OKLab, 2:1

    def test_the_six_v16_dsls_land_at_or_under_twelve(self):
        import json
        for u in ("hfoo", "n005", "n00U", "n017", "n02X", "n01X"):
            path = ROOT / f"artifacts/model-sheets/runs/draft/{u}/v16-r3/eye/round-2/dsl.json"
            if not path.exists():
                continue
            with self.subTest(unit=u):
                _, log = F.fuse(json.loads(path.read_text()))
                self.assertLessEqual(log["after"], 12)
                self.assertLessEqual(log["after"], log["before"])
