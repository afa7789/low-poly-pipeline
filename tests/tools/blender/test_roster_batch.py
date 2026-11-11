"""python3.14 -m unittest tests.tools.blender.test_roster_batch   (pure functions only: no API, no Blender)"""
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import roster_batch as RB  # noqa: E402

COMP = {"races": [{"name": "Human", "entries": [{"id": "hfoo", "name": "Footman", "kind": "unit", "description": "a soldier"},
                                                {"id": "h05X", "name": "Barracks", "kind": "building"}]},
                  {"name": "Nature", "entries": [{"id": "n01N", "name": "Giant Spider", "kind": "unit", "tooltip": "spider"}]}]}
PARTS = {"H": 2.0, "parts": [{"name": "helmet", "role": "head", "bone": "head", "prop": False, "box3d": [[0, 1.8, 0], [0.4, 2.1, 0.4]]},
                             {"name": "trench pike", "role": "prop", "bone": "forearm.R", "anchor": "hand.R", "prop": True,
                              "box3d": [[0.3, 0.2, -0.1], [0.5, 2.0, 0.1]]},
                             {"name": "field pack", "role": "prop", "bone": "spine", "anchor": "back", "prop": True,
                              "box3d": [[-0.2, 1.0, 0.3], [0.2, 1.6, 0.6]]}]}


def state(**kw):
    base = {"prompts": {s: True for s in RB.SHEETS}, "sheets": {s: True for s in RB.SHEETS}, "parts": True, "sheet_json": True,
            "props_json": True, "rts_missing": 0, "model": True}
    for k, v in kw.items():
        if isinstance(v, dict):
            base[k] = {**base[k], **v}
        else:
            base[k] = v
    return base


class Roster(unittest.TestCase):
    def test_roster_keeps_units_only(self):
        got = RB.roster(COMP)
        self.assertEqual([u["id"] for u in got], ["hfoo", "n01N"])
        self.assertEqual(got[0]["race"], "Human")
        self.assertIn("a soldier", got[0]["card"])

    def test_rig_of(self):
        for uid, text, rig in (("n01N", "", "spider_high"), ("n017", "", "quadruped"), ("hfoo", "Footman a soldier", "biped"),
                               ("x1", "Frost Wolf lean quadruped", "quadruped"), ("x2", "Soot Drake glides", "drake"),
                               ("x3", "Black Spiders of the wood", "spider"), ("x4", "Ogre", "biped"), ("x5", "a spiderling", "biped")):
            with self.subTest(uid=uid, text=text):
                self.assertEqual(RB.rig_of(uid, text), rig)


class Plan(unittest.TestCase):
    def test_stage_done_and_reached(self):
        cases = (("all", state(), ["prompt", "sheets", "parts", "model"], "model"),
                 ("no props sheet, no props prompt", state(prompts={"sheet-props": False}, sheets={"sheet-props": False}), ["prompt", "sheets", "parts", "model"], "model"),
                 ("props prompt, sheet missing", state(sheets={"sheet-props": False}), ["prompt", "parts", "model"], "prompt"),
                 ("no hard-clean at all (quadruped)", state(prompts={"sheet-hard-clean": False}, sheets={"sheet-hard-clean": False}), ["prompt", "sheets", "parts", "model"], "model"),
                 ("hard-clean prompt, sheet missing", state(sheets={"sheet-hard-clean": False}), ["prompt", "parts", "model"], "prompt"),
                 ("only sheets", state(parts=False, sheet_json=False, model=False), ["prompt", "sheets"], "sheets"),
                 ("parts without sheet.json", state(sheet_json=False, model=False), ["prompt", "sheets"], "sheets"),
                 ("nothing", state(prompts={s: False for s in RB.SHEETS}, sheets={s: False for s in RB.SHEETS}, parts=False, sheet_json=False, model=False), [], "-"))
        for name, st, done, last in cases:
            with self.subTest(name):
                self.assertEqual([s for s in RB.STAGES if RB.stage_done(st, s)], done)
                self.assertEqual(RB.reached(st), last)

    def test_plan(self):
        st = state(parts=False, sheet_json=False, model=False)
        self.assertEqual(RB.plan(st), ["parts", "model"])
        self.assertEqual(RB.plan(st, "sheets"), [])
        self.assertEqual(RB.plan(st, "parts"), ["parts"])
        self.assertEqual(RB.plan(state(), "all", resume=True), [])
        self.assertEqual(RB.plan(state(), "all", resume=False), ["model"])      # without --resume the model is rebuilt, the data never
        self.assertEqual(RB.plan(state(prompts={"sheet": False}), "all"), ["prompt"])

    def test_unit_state_reads_disk(self):
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            refs, prompts, draft = root / "refs", root / "prompts", root / "draft"
            (prompts / "u1").mkdir(parents=True)
            (prompts / "u1" / "unit.txt").write_text("# unit prompt\n# redesign: " + "x" * 1000 + "\n# Fill from template y\n")      # a stub, mark past 1 K as in the real ones
            (prompts / "u1" / "unit-u1-hard.txt").write_text("Clean 2D model-sheet ...")
            (refs / "u1").mkdir(parents=True)
            (refs / "u1" / "sheet.jpg").write_bytes(b"x")
            (draft / "u1" / "r1").mkdir(parents=True)
            (draft / "u1" / "r1" / "model.glb").write_bytes(b"x")
            st = RB.unit_state("u1", "r1", refs, prompts, draft)
            self.assertEqual(st["prompts"], {"sheet": False, "sheet-hard": True, "sheet-hard-clean": False, "sheet-props": False})
            self.assertEqual(st["sheets"]["sheet"], True)
            self.assertFalse(st["parts"])
            self.assertFalse(st["model"])            # review.md missing
            self.assertIsNone(RB.prompt_path("u1", "unit", prompts))
            self.assertEqual(RB.prompt_path("u1", "unit-hard", prompts).name, "unit-u1-hard.txt")


class Props(unittest.TestCase):
    def test_props_from_parts(self):
        rows = RB.props_from_parts(PARTS)
        self.assertEqual([r["name"] for r in rows], ["trench pike", "field pack"])
        self.assertEqual(rows[0]["bones"], ["forearm.R", "forearm.L"])
        self.assertEqual(rows[0]["extent"], [0.72, 1.08])          # longest side 1.8 / H 2.0 = 0.9 x (0.8, 1.2)
        self.assertEqual(rows[1]["bones"], ["spine"])
        self.assertIn("back", rows[1]["where"])
        self.assertEqual(RB.props_from_parts({"H": 2, "parts": [PARTS["parts"][0]]}), [])


class Parsers(unittest.TestCase):
    def test_parse_pipeline_line(self):
        text = "noise\nhfoo\troster-v1\troster\ttris 696/400-700\tskins 13\tanims 3\tsmear 0 %\tpreflight PASS\tstage1 FAIL\tstage2 PASS\tCHECK\n"
        self.assertEqual(RB.parse_pipeline_line(text), {"verdict": "CHECK", "tris": 696, "preflight": "PASS", "stage1": "FAIL", "stage2": "PASS"})
        self.assertEqual(RB.parse_pipeline_line("Traceback\nValueError: x"), {})

    def test_parse_eye_summary_and_cause(self):
        self.assertEqual(RB.parse_eye_summary({"rounds": [{"tris": 700, "parts": [18, 25]}, {"tris": 696, "parts": "16/25"}]}), {"tris": 696, "parts": "16/25"})
        self.assertEqual(RB.parse_eye_summary({}), {})
        self.assertEqual(RB.cause_of("a\nTraceback (most recent call last):\n  File x\nValueError: bad sheet\n"), "ValueError: bad sheet")
        self.assertEqual(RB.cause_of("HTTP 401: no key\n"), "HTTP 401: no key")
        self.assertEqual(RB.cause_of("   "), "no output")
        self.assertEqual(RB.cause_of("last line only"), "last line only")


class Table(unittest.TestCase):
    def entries(self):
        a = {**RB.new_entry({"id": "hfoo", "name": "Footman", "race": "Human"}, "biped"), "reached": "model", "total_s": 1500.4, "cost_usd": 0.153,
             "stages": {"model": {"state": "done", "tris": 696, "parts": "18/25", "verdict": "CHECK"}}}
        b = {**RB.new_entry({"id": "n01N", "name": "Giant Spider", "race": "Nature"}, "spider_high"), "reached": "sheets",
             "stages": {"parts": {"state": "failed", "error": "RuntimeError: claude -p failed"}}}
        return [b, a]

    def test_row_and_table(self):
        rows = [RB.row_of(e) for e in self.entries()]
        self.assertEqual(rows[1]["gate"], "CHECK")
        self.assertEqual(rows[0]["gate"], "FAIL")
        self.assertEqual(rows[0]["error"], "parts: RuntimeError: claude -p failed")
        md = RB.table(self.entries()).splitlines()
        self.assertEqual(len(md), 4)
        self.assertTrue(md[2].startswith("| hfoo | Human | biped | model | 696 | 18/25 | CHECK | 1500 | 0.15 |"))
        self.assertIn("| n01N | Nature | spider_high | sheets | – | – | FAIL | 0 | 0.00 | parts:", md[3])

    def test_estimate(self):
        states = {"a": state(), "b": state(parts=False, sheet_json=False, model=False),
                  "c": state(prompts={s: False for s in RB.SHEETS}, sheets={s: False for s in RB.SHEETS}, parts=False, sheet_json=False, model=False)}
        est = RB.estimate(states, medians={"prompt": 10, "sheets": 20, "parts": 30, "model": 100})
        self.assertEqual(est["ready"], {"prompt": 2, "sheets": 2, "parts": 1, "model": 1})
        self.assertEqual(est["todo"], {"prompt": 1, "sheets": 1, "parts": 2, "model": 2})
        self.assertEqual(est["seconds"], 10 + 20 + 60 + 200)
        self.assertEqual(est["images"], 4)
        self.assertAlmostEqual(est["usd"], 0.046 + 3 * 0.051 + RB.USD_RTS, delta=0.006)      # b has its rts views, c draws 3
        self.assertIn("3 units", RB.estimate_text(est))

    def test_model_command_carries_the_cvt_recipe(self):
        cmd = RB.model_command({"id": "n01N", "race": "Nature", "name": "Giant Spider"}, "spider_high", "roster-pilot")
        for flag, value in (("--rig", "spider_high"), ("--eye", "on"), ("--eye-union-reduce", "cvt"), ("--eye-fuse", "12"),
                            ("--eye-union", "bone"), ("--eye-paint", "box"), ("--outline", "off"), ("--model", "session:opus"), ("--run", "roster-pilot")):
            with self.subTest(flag):
                self.assertEqual(cmd[cmd.index(flag) + 1], value)
        self.assertIn("--deterministic", cmd)
        self.assertEqual(json.dumps(RB.PROMPT_SCHEMA)[:9], '{"type": ')


if __name__ == "__main__":
    unittest.main()
