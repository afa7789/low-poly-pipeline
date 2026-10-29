"""python3 -m unittest discover -s tests/tools/blender"""
import json
import pathlib
import sys
import tempfile
import types
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import loop_stage as L  # noqa: E402

BASE = {"front": .8, "left": .6, "back": .8, "top": .7, "bottom": .7, "rts": .7}
GATES = {"front": .75, "left": .65, "back": .7, "top": .65, "bottom": .65, "rts": .7}


def moved(**kw):
    return {**BASE, **{k: BASE[k] + v for k, v in kw.items()}}


class Accept(unittest.TestCase):
    def test_rule(self):
        cases = [
            ("mean up", moved(front=.03), True),
            ("below gain", moved(front=.02), False),                   # mean +.0033
            ("one view falls", moved(front=.1, top=-.011), False),     # mean up, a view falls > .01
            ("fall at the limit", moved(front=.1, top=-.01), True),
            ("gate fixed, mean flat", moved(left=.06, front=-.005, back=-.005, top=-.005, bottom=-.005, rts=-.005), True),
            ("nothing", dict(BASE), False),
        ]
        for name, after, want in cases:
            with self.subTest(name):
                self.assertEqual(L.loop_accept(BASE, after, GATES)[0], want)

    def test_gate_fixed_does_not_excuse_a_fall(self):
        self.assertFalse(L.loop_accept(BASE, moved(left=.06, top=-.02), GATES)[0])


class Order(unittest.TestCase):
    def test_expected_first_stable(self):
        ds = [{"why": "none named"}, {"why": "pack too wide in front"}, {"why": "top and rts lobes"}, {"why": "also nothing"}]
        out = L.order_deltas(ds, {"top": .03, "front": .01})
        self.assertEqual([d["why"] for d in out], ["top and rts lobes", "pack too wide in front", "none named", "also nothing"])


class Hooks:
    """rebuild: the IoU a delta gives = table[delta['value']]; records calls."""
    def __init__(self, tmp, table, deltas):
        self.loop_dir, self.table, self.calls, self.promoted, self.diags = pathlib.Path(tmp), table, [], [], 0
        self.deltas = deltas

    def apply(self, spec, ds):
        d = ds[0]
        if d.get("bad"):
            return spec, [{"status": "rejected", "why": "limit"}]
        return {**spec, "n": spec["n"] + 1}, [{"status": "applied", "why": "ok"}]

    def rebuild(self, spec, out):
        out.mkdir(parents=True)
        self.calls.append(out.name)
        iou = self.table[spec["n"]]
        return spec, {"glb": out / "clay.glb"} if iou else {"glb": None}, {"approved": iou or {}}

    def diagnose(self):
        self.diags += 1
        return {"deltas": self.deltas, "expected": {}, "cost": {"seconds": 1.0}}

    def prepare(self, cur):
        pass

    def promote(self, cur):
        self.promoted.append(cur["spec"]["n"])


def delta(i, **kw):
    return {"part": f"p#{i}", "action": "scale", "value": 0.9, "why": "", **kw}


class Run(unittest.TestCase):
    def go(self, table, deltas, n=2, limit=3):
        with tempfile.TemporaryDirectory() as tmp:
            h = Hooks(tmp, table, deltas)
            spec, _, summary, report = L.run(n, {"n": 0}, {"glb": "r0"}, {"approved": BASE, "gates": GATES}, h, limit)
            self.assertEqual(json.loads((h.loop_dir / "loop.json").read_text())["final"], report["final"])
            return h, spec, report

    def test_limit_three_rebuilds_per_round(self):
        h, _, r = self.go({1: BASE, 2: BASE, 3: BASE, 4: BASE}, [delta(i) for i in range(5)], n=1)
        self.assertEqual(h.calls, ["delta1", "delta2", "delta3"])
        self.assertEqual(r["rounds"][0]["accepted"], 0)

    def test_not_applied_does_not_use_a_slot_and_is_not_rebuilt(self):
        h, _, r = self.go({1: BASE, 2: BASE, 3: BASE}, [delta(0, bad=1), delta(1), delta(2), delta(3)], n=1)
        self.assertEqual(len(h.calls), 3)
        self.assertEqual(r["rounds"][0]["deltas"][0]["status"], "not-applied")

    def test_accept_chains_and_stops_on_empty_round(self):
        better = moved(front=.03)
        h, spec, r = self.go({1: better, 2: better}, [delta(0)], n=3)
        self.assertEqual((spec["n"], h.promoted, h.diags), (1, [1], 2))        # round 2 accepts nothing -> stop, no round 3
        self.assertEqual(r["final"], better)
        self.assertEqual(r["rounds"][0]["deltas"][0]["change"]["front"], .03)

    def test_rejected_is_discarded_and_failed_build_rejected(self):
        h, spec, r = self.go({1: moved(front=.1, top=-.05), 2: None}, [delta(0), delta(1)], n=1)
        self.assertEqual(spec["n"], 0)
        self.assertEqual([d["status"] for d in r["rounds"][0]["deltas"]], ["rejected", "rejected"])
        self.assertEqual(r["final"], BASE)

    def test_remove_ends_the_round(self):
        h, _, r = self.go({1: moved(front=.05), 2: moved(front=.1)}, [delta(0, action="remove"), delta(1)], n=1)
        self.assertEqual(h.calls, ["delta1"])

    def test_table(self):
        h, _, r = self.go({1: moved(front=.03)}, [delta(0)], n=1)
        self.assertIn("accepted", L.table(r))
        self.assertEqual(L.table(None), "")


if __name__ == "__main__":
    unittest.main()
