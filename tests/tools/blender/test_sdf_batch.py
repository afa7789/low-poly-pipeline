"""python3.14 -m unittest tests.tools.blender.test_sdf_batch   (SLOW=1 runs Blender: one unit through sdf_batch, ~1.5 min)"""
import json
import os
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import sdf_batch as B  # noqa: E402

UNIT = {"unit": "u1", "rig": "biped", "run": "v12-r1", "spec": pathlib.Path("/x/spec.json")}


def lint(**kw):
    return {"tris": 700, "sliver_pct": 1.0, "normal_diff": {"mean": 35.0}, "euler": 0, "components_body": 1,
            "sdf_dev": {"pct_h": {"p95": 1.2, "max": 3.0}}, **kw}


def row(body="sdf", unit=UNIT, anim=None, plates=((4, 3, False), (7, 5, False)), **kw):
    sil = {"approved": dict(zip(B.VIEWS, (.9, .8, .9, .7, .7, .6))), "gates": {"front": .75, "left": .65, "rts": .7}, "uncovered": {"front": .1}, "spill": {"front": .2}}
    att = {"union": {"seconds": 2.0, "inflated": [1], "kept": []}}
    return B.make_row(unit, body, sil, att, lint(**kw), lint(sliver_pct=0.0), anim, list(plates), ["sliver_pct < 5"], 12.34)


class Pure(unittest.TestCase):
    def test_discover_latest_spec_and_skips_buildings(self):
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            for unit, run, rig in (("a", "v10-r1", "biped"), ("a", "v12-r1", "biped"), ("b", "v11-r1", "wyrm"), ("c", "v10-r1", "building"), ("n01I", "v2-hard-r2", "biped")):
                (root / unit / run).mkdir(parents=True)
                (root / unit / run / "spec.json").write_text(json.dumps({"rig": rig}))
            (root / "d").mkdir()
            got = [(u["unit"], u["run"]) for u in B.discover(root)]
            self.assertEqual(got, [("a", "v12-r1"), ("b", "v11-r1"), ("n01I", "v2-hard-r2")])
            self.assertEqual([u["unit"] for u in B.discover(root, ["b"])], ["b"])

    def test_tilts_and_command(self):
        self.assertEqual(B.tilts_arg({"tilt": {"bottom": 20, "rts": [55, -60]}}), "bottom:20,rts:55/-60")
        self.assertEqual(B.tilts_arg({}), "")
        cmd = B.command(UNIT, "sdf", 128, "top:10")
        self.assertEqual((cmd[cmd.index("--body") + 1], cmd[cmd.index("--sdf-grid") + 1], cmd[cmd.index("--tilts") + 1], cmd[cmd.index("--run") + 1]),
                         ("sdf", "128", "top:10", "l10-batch-sdfg128"))
        self.assertNotIn("--sdf-grid", B.command(UNIT, "union", 128))

    def test_cause_of(self):
        tb = f'noise\nTraceback (most recent call last):\n  File "{B.ROOT}/tools/blender/a.py", line 3, in f\n    x\nValueError: boom\n'
        self.assertEqual(B.cause_of(tb), "ValueError: boom [File \"tools/blender/a.py\", line 3, in f]")
        self.assertEqual(B.cause_of("a\nb\n"), "b")
        self.assertEqual(B.cause_of(""), "no output")

    def test_row_fields(self):
        r = row(anim={"walk": {"p99.5_stretch": 1.5}, "death": None})
        self.assertEqual((r["build_s"], r["total_s"], r["thin"], r["plates"], r["plates_zero"], r["stretch"]), (2.0, 12.3, 1, 2, 0, {"walk": 1.5}))
        self.assertEqual(r["nd_raw"], 35.0)
        z = row(plates=((4, 0, True), (6, 0, False), (7, 2, False)))
        self.assertEqual((z["plates_zero_rows"], z["plates_zero"], z["plates_buried"]), ([4, 6], 1, [4]))
        self.assertEqual((r["sil_fail"], r["lint_fail"], r["sliver_raw"], r["dev_p95"]), (["front", "rts"], ["sliver_pct < 5"], 0.0, 1.2))
        self.assertEqual(B.rig_group("spider_high"), "spider")
        self.assertEqual(B.rig_group("serpent"), "outros")

    def test_tables(self):
        un = {**UNIT, "rig": "wyrm"}
        rows = [row("sdf", un), row("union", un), B.fail_row({**UNIT, "unit": "u2"}, "sdf", "boom", 3.0)]
        md = B.table(rows)
        self.assertEqual(md.count("\n"), 4)
        self.assertIn("| u2 | biped | sdf | FAIL | 3.0 | boom |", md)
        self.assertIn("| u1 | wyrm | sdf | 2.0 |", md)
        self.assertIn("| u1 | wyrm | 0.000", B.delta_table(rows))

    def test_acceptance_by_rig(self):
        def get(g, body_kw, union_kw=None):
            u = {**UNIT, "rig": g}
            rows = [row("sdf", u, **body_kw)] + ([row("union", u, **union_kw)] if union_kw is not None else [])
            return dict((x[0], x[2]) for x in B.acceptance(rows))["u1"]
        self.assertEqual(get("biped", {"sliver_pct": 1.0, "normal_diff": {"mean": 30.0}}, {"normal_diff": {"mean": 41.0}}), [])
        self.assertEqual(len(get("biped", {"sliver_pct": 6.0}, {})), 2)             # sliver, nd gain
        self.assertEqual(len(get("quadruped", {"sliver_pct": 6.0})), 1)
        self.assertEqual(len(get("spider", {"components_body": 2}, {})), 1)
        self.assertEqual(get("wyrm", {"plates": ()}, {}), [])
        self.assertIn("1 of 2 plates", get("drake", {"plates": ((2, 0, False), (3, 4, False))})[0])
        out = B.acceptance([row("sdf", UNIT, build_s=None), B.fail_row({**UNIT, "unit": "u2"}, "sdf", "boom", 1.0)])
        self.assertIn("build failed: boom", out[1][2][0])

    def test_build_time_rule(self):
        slow = row("sdf")
        slow["build_s"] = 31.0
        why = B.acceptance([slow])[-1][2]
        self.assertEqual(len(why), 2)
        self.assertIn("1/1 units", B.acceptance_table([row("sdf")]))


@unittest.skipUnless(os.environ.get("SLOW"), "SLOW=1: runs Blender")
class Slow(unittest.TestCase):
    def test_one_unit(self):
        with tempfile.NamedTemporaryFile(suffix=".json") as t:
            self.assertEqual(B.main(["--units", "n010", "--body", "sdf", "--json", t.name, "--no-anim"]), 0)
            rows = json.loads(pathlib.Path(t.name).read_text())["rows"]
        self.assertTrue(rows[0]["ok"])
        self.assertEqual(rows[0]["plates_zero"], 0)


if __name__ == "__main__":
    unittest.main()
