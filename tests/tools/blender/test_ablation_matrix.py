"""python3 -m unittest discover -s tests/tools/blender

L12-10a: the ablation matrix covers every live opt-in (test_flag_liveness.LIVE_PAIRS / LIVE_CUSTOM), and its pure parts (merge, deltas,
2-sigma falls, verdict) do what the tables say. No Blender, no pipeline run."""
import pathlib
import sys
import unittest

TOOLS = pathlib.Path(__file__).resolve().parents[3] / "tools/blender"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(pathlib.Path(__file__).parent))

import ablation_matrix as AM  # noqa: E402
import test_flag_liveness as TFL  # noqa: E402

NOISE = {"global": {v: 0.01 for v in AM.VIEWS}}


def row(unit="hfoo", name="base", iou=.8, spill=.1, **kw):
    r = {"unit": unit, "variant": name, "ok": True, "iou": [iou] * 6, "mean": iou, "spill_v": [spill] * 6, "spill": spill, "spill_ok": int(spill <= AM.SPILL_OK) * 6,
         "bare": .05, "contact": .9, "z_err": .1, "planarity": .5, "crease": .4, "sliver": 1.0, "nd": 30.0, "total_s": 100.0, "tris": 700}
    return {**r, **kw}


class Coverage(unittest.TestCase):
    def covered(self):
        defaults = vars(TFL.parse())
        out = set()
        for v in AM.VARIANTS.values():
            flags = [w for g in v["flags"] for w in g]
            out |= {k for k, x in vars(TFL.parse(*[AM.NOISE.as_posix() if w == "{deltas}" else w for w in flags])).items() if x != defaults[k]}
        return out

    def test_every_live_flag_has_a_variant_or_a_reason(self):
        live = {*TFL.LIVE_PAIRS, *TFL.LIVE_CUSTOM}
        self.assertEqual(live - self.covered() - set(AM.NOT_A_VARIANT), set(), "a live flag with no variant in the matrix (add one, or a reason to NOT_A_VARIANT)")

    def test_every_env_opt_in_has_a_variant(self):
        self.assertIn("CF_SPILL_W", {k for v in AM.VARIANTS.values() for k in v["env"]})

    def test_reasons_are_for_live_flags(self):
        self.assertEqual(set(AM.NOT_A_VARIANT) - {*TFL.LIVE_PAIRS, *TFL.LIVE_CUSTOM}, set())

    def test_every_variant_parses(self):
        for name in AM.VARIANTS:
            with self.subTest(name):
                AM.resolve(name)


class Merge(unittest.TestCase):
    def test_flags_join_and_a_clash_is_an_error(self):
        v = AM.resolve("fit-grad+k-hard")
        self.assertEqual([g[0] for g in v["flags"]], ["--fit-grad", "--sdf-k-mode"])
        with self.assertRaises(ValueError):
            AM.resolve("k-hard+k-class")

    def test_env_clash_is_an_error(self):
        table = {"a": AM.var(env={"CF_SPILL_W": "3"}), "b": AM.var(env={"CF_SPILL_W": "2"})}
        with self.assertRaises(ValueError):
            AM.resolve("a+b", table)
        self.assertEqual(AM.resolve("a+a", table)["env"], {"CF_SPILL_W": "3"})


class Deltas(unittest.TestCase):
    def test_a_fall_counts_only_beyond_two_sigma(self):
        base = row()
        small = row(name="x", iou=.8 - .015)          # 2 sigma = .02: noise
        big = row(name="x", iou=.8 - .03)
        self.assertEqual(AM.vs_base(small, base, NOISE)["falls"], [])
        self.assertEqual(len(AM.vs_base(big, base, NOISE)["falls"]), 6)

    def test_gate_numbers_use_the_body_where_there_are_props(self):
        sil = {"approved": {"front": .9, "left": .8}, "spill": {"front": .1, "left": .2}, "uncovered": {"front": .05, "left": .06},
               "body_iou": {"front": .95}, "body_spill": {"front": .02}, "body_bare": {"front": .01}}
        self.assertEqual((AM.gate_view(sil, "spill", "front"), AM.gate_view(sil, "spill", "left")), (.02, .2))
        self.assertEqual((AM.gate_view(sil, "bare", "front"), AM.gate_view(sil, "bare", "left")), (.01, .06))

    def test_verdicts(self):
        base = [row(u) for u in ("hfoo", "n005")]
        mk = lambda **kw: AM.summarize([*base, *[row(u, "look-snap", **kw) for u in ("hfoo", "n005")]], NOISE)["look-snap"]      # noqa: E731
        self.assertEqual(AM.verdict(mk(spill=.05, spill_ok=0)), "default-candidate")
        self.assertTrue(AM.verdict(mk(spill=.05, iou=.7)).startswith("opt-in"))
        self.assertEqual(AM.verdict(mk(spill=.2, iou=.7)), "no")
        self.assertIn("no-op", AM.verdict(mk()))

    def test_winners_skip_controls_and_combinations(self):
        rows = [row("hfoo"), row("hfoo", "no-deform", spill=.05), row("hfoo", "look-snap", spill=.05)]
        self.assertEqual(AM.winners(AM.summarize(rows, NOISE)), ["look-snap"])

    def test_before_after_lists_only_changed_verdicts(self):
        base = [row()]
        a = AM.summarize([*base, row(name="look-snap", spill=.05)], NOISE)
        b = AM.summarize([*base, row(name="look-snap", spill=.2)], NOISE)
        self.assertIn("| look-snap |", AM.before_after_table(b, a))
        self.assertIn("no variant", AM.before_after_table(a, a))


class Csv(unittest.TestCase):
    def test_columns_and_deltas(self):
        text = AM.csv_text([row(), row(name="look-snap", spill=.05)], NOISE).splitlines()
        head = text[0].split(",")
        self.assertEqual(len(head), len(set(head)))
        cells = dict(zip(head, text[2].split(",")))
        self.assertEqual(cells["d_spill"], "-0.05")


if __name__ == "__main__":
    unittest.main()
