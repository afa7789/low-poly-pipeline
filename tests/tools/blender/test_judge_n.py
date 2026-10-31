"""L18-4: the vote-count calibration of the pairwise judge (judge_n.py), pure helpers on fake results."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))
import judge_n as J  # noqa: E402


def res(unit, n, rep, form="B", sheet="A", artist="tie", wc3="B", seconds=10.0):
    return {"unit": unit, "n": n, "rep": rep, "seconds": seconds, "calls": n,
            **{ax: {"winner": w} for ax, w in (("sheet", sheet), ("artist", artist), ("wc3", wc3), ("form", form))}}


class Report(unittest.TestCase):
    def test_tie_rate_agreement_and_the_pick(self):
        units = ["u1", "u2", "u3", "u4", "u5", "u6"]
        results = []
        for u in units:                                        # N=2: form flips between reps on 3 units; N=4: 1 flips; N=8: none
            results += [res(u, 2, 1, form="B"), res(u, 2, 2, form="A" if u in ("u1", "u2", "u3") else "B")]
            results += [res(u, 4, 1, form="B"), res(u, 4, 2, form="A" if u == "u1" else "B")]
            results += [res(u, 8, 1, form="B", seconds=40), res(u, 8, 2, form="B", seconds=40)]
        table = J.per_n(results)
        self.assertEqual([table[n]["form_units"] for n in (2, 4, 8)], [3, 5, 6])
        self.assertEqual(J.pick(table), 8)                     # 5/6 at N=4 is beaten by 6/6 at N=8: the first stable N is 8
        wobble = {2: dict(table[2], form_units=5), 4: dict(table[4], form_units=6), 6: dict(table[4], form_units=5), 8: dict(table[8])}
        self.assertEqual(J.pick(wobble), 4)                    # 5/6 at N=2 is beaten by N=4: not stable; 6/6 at 4 is not beaten by 6
        self.assertEqual(table[2]["tie"], 0.25)                # artist is a tie everywhere
        self.assertEqual(table[8]["agree"], 1.0)
        self.assertEqual((table[8]["calls"], table[8]["seconds_median"]), (96, 40))
        self.assertIn("**(default)**", J.lines(table, 4))
        self.assertEqual(J.pick({n: t for n, t in table.items() if n == 2}), 2)      # none reaches the bar: the best, smallest
        self.assertIsNone(J.tie_rate([]))
        self.assertIsNone(J.agreement([res("u1", 2, 1)]))      # one repetition: nothing to agree with
