"""python3.14 -m unittest tests.tools.blender.test_noise   (no Blender: L12-7 noise floor, sigma battery, 2-sigma guards)"""
import json
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import author_guard as G  # noqa: E402
import compare_runs as CR  # noqa: E402
import loop_stage as L  # noqa: E402
import noise as NZ  # noqa: E402
import sdf_batch as B  # noqa: E402

TABLE = {"u": {"front": 0.02, "left": 0.001}, "global": {"front": 0.004, "left": 0.004, "top": 0.01}}


class Threshold(unittest.TestCase):
    def test_without_table_is_the_constant(self):
        self.assertEqual(NZ.threshold("front", None), 0.01)
        self.assertEqual(NZ.threshold("front", None, 0.02), 0.02)
        self.assertEqual(NZ.load(None), None)

    def test_with_table(self):
        self.assertAlmostEqual(NZ.threshold("front", TABLE, unit="u"), 0.04)     # 2 sigma of the unit
        self.assertEqual(NZ.threshold("left", TABLE, unit="u"), NZ.FLOOR)        # floor
        self.assertAlmostEqual(NZ.threshold("top", TABLE, unit="u"), 0.02)       # no unit sigma: global
        self.assertEqual(NZ.threshold("rts", TABLE, unit="u"), 0.01)             # no sigma at all: default

    def test_load_and_mark(self):
        with tempfile.TemporaryDirectory() as t:
            p = pathlib.Path(t) / "noise.json"
            p.write_text(json.dumps(TABLE))
            self.assertEqual(NZ.load(p), TABLE)
        self.assertEqual(NZ.mark("front", 0.05, TABLE, "u"), "> 2σ")
        self.assertEqual(NZ.mark("front", -0.03, TABLE, "u"), "ruído")
        self.assertEqual(NZ.mark("rts", 0.5, TABLE, "u"), "")


class Guards(unittest.TestCase):
    def test_loop_accept_uses_two_sigma(self):
        before, after = {"front": .80, "left": .80}, {"front": .77, "left": .90}
        self.assertFalse(L.loop_accept(before, after, {})[0])                  # -.03 > .01
        self.assertTrue(L.loop_accept(before, after, {}, TABLE, "u")[0])        # -.03 < 2 x .02
        self.assertFalse(L.loop_accept(before, {"front": .75, "left": .9}, {}, TABLE, "u")[0])

    def test_author_drops_use_two_sigma(self):
        mass, author = {"front": .80, "left": .80}, {"front": .77, "left": .77}
        self.assertEqual(G.drops(mass, author), ["front", "left"])
        self.assertEqual(G.drops(mass, author, noise=TABLE, unit="u"), ["left"])    # front: 2 sigma = .04; left: floor .005


class Compare(unittest.TestCase):
    def test_stability_marks_noise_vs_change(self):
        with tempfile.TemporaryDirectory() as t:
            runs = []
            for i, front in enumerate((0.80, 0.87)):
                d = pathlib.Path(t) / "u" / f"r{i}"
                d.mkdir(parents=True)
                (d / "silhouette.json").write_text(json.dumps({"approved": {"front": front, "left": 0.8}}))
                runs.append(d)
            with mock.patch.object(CR, "chamfer_3d", return_value=(0.0, 1.0)), mock.patch.object(CR, "run_glb"):
                text = CR.stability(*runs, noise=TABLE)
        self.assertIn("front 0.070 > 2σ", text)
        self.assertIn("left 0.000 ruído", text)


class Battery(unittest.TestCase):
    def test_sigma_and_table(self):
        s = NZ.sigmas([{"front": .80}, {"front": .82}, {"front": .84}])
        self.assertEqual(s, {"front": 0.02})
        self.assertEqual(NZ.sigmas([{"front": .8}]), {})
        t = NZ.table({"a": [{"front": .8}, {"front": .82}, {"front": .84}], "b": [{"front": .8}, {"front": .8}], "c": [{"front": .8}]})
        self.assertEqual(sorted(t), ["a", "b", "global"])
        self.assertEqual(t["global"], {"front": 0.01})      # median of .02 and 0

    def test_repeat_three_builds_and_writes_sigma(self):
        iou = {1: .80, 2: .82, 3: .84}
        calls = []

        def fake_one(u, body, args, rep=1):
            calls.append(rep)
            return {"ok": True, "unit": u["unit"], "body": body, "rig": "biped", "grid": 96, "iou": [iou[rep]] * 6, "rep": rep}

        with tempfile.TemporaryDirectory() as t:
            out = pathlib.Path(t) / "l.json"
            units = [{"unit": "u1", "rig": "biped", "run": "v13-r1", "spec": pathlib.Path("/x/spec.json")}]
            with mock.patch.object(B, "one", fake_one), mock.patch.object(B, "discover", return_value=units), \
                    mock.patch.object(B, "table", return_value="T"):
                B.main(["--body", "sdf", "--repeat", "3", "--json", str(out), "--spec-run", "v13-r1"])
            noise = json.loads((pathlib.Path(t) / "noise.json").read_text())
        self.assertEqual(sorted(calls), [1, 2, 3])
        self.assertEqual(noise["u1"]["front"], 0.02)
        self.assertEqual(noise["global"]["rts"], 0.02)

    def test_repeat_names(self):
        a = types.SimpleNamespace(repeat=3, prefix="l12-noise", run="")
        self.assertEqual(B.repeat_name(a, 2), "l12-noise-r2")
        self.assertIsNone(B.repeat_name(types.SimpleNamespace(repeat=1, prefix="x", run=""), 1))
        self.assertEqual(B.repeat_name(types.SimpleNamespace(repeat=1, prefix="x", run="l15-gate-sdf"), 1), "l15-gate-sdf")
        u = {"unit": "u", "rig": "biped", "spec": pathlib.Path("/s")}
        self.assertIn("l12-noise-r2", B.command(u, "sdf", 0, "", "l12-noise-r2"))


if __name__ == "__main__":
    unittest.main()
