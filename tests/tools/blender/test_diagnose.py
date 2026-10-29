"""python3 -m unittest discover -s tests/tools/blender"""
import hashlib
import inspect
import json
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

try:
    from PIL import Image
except ImportError:
    raise unittest.SkipTest("Pillow is not installed")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import diagnose as D  # noqa: E402
import spec_pipeline as SP  # noqa: E402

SPEC = {"parts": [["body", "frustum", [0.4, 0.3, 0.2], [0, 0.5, 0], "shell", {}],
                  ["body", "prism", [0.2, 0.2, 0.2], [0.1, 0.6, 0.1], "shell", {}],
                  ["head", "frustum", [0.2, 0.2, 0.2], [0, 0.9, 0.3], "head", {}]], "palette": {}}
REVIEW = ("# u — run r (t)\n\n## Avaliação\n\n| x |\n\n## Timing\n\n- t_gen: 1 s\n\n"
          "## Stage 1 - shape (clay): **FAIL**\n\n| worst red front | band 1 |\n\n"
          "## Readiness\n\n| file | clay.glb |\n\nverdict: **CHECK**\n")
REPLY = {"findings": [{"view": "front", "part": "body", "colour": "red", "cause": "too wide", "fix": "narrow"}],
         "identity": ["no backpack"],
         "changes": [{"change": "narrow body", "gain": "front +0.02"}] * 3,
         "owner": {"who": "fit", "why": "dims"},
         "deltas": [{"part": "body#0", "action": "scale", "axis": "x", "value": 0.9, "why": "too wide"}],
         "expected": {"front": 0.02}}


def make_run(tmp):
    run = pathlib.Path(tmp) / "r"
    run.mkdir()
    (run / "spec.json").write_text(json.dumps(SPEC))
    (run / "review.md").write_text(REVIEW)
    Image.new("RGB", (8, 8)).save(run / "compare.png")
    return run


def stub(reply=REPLY):
    calls = []

    def ask(model, brief, images, schema=None, check=None):
        calls.append((model, brief, images, schema))
        return json.dumps(reply)
    ask.calls = calls
    return ask


class Diagnose(unittest.TestCase):
    def test_prompt_has_stage_report_spec_and_drops_noise(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(D, "failing_rules", return_value=""):
            p = D.prompt_of(make_run(tmp), "u", "mass")
        for want in ("worst red front", "- body: 2x frustum/prism", "- head: 1x", "1.0 tall"):
            with self.subTest(want=want):
                self.assertIn(want, p)
        for gone in ("t_gen", "clay.glb", "Avalia"):
            with self.subTest(gone=gone):
                self.assertNotIn(gone, p)

    def test_outputs_and_rerun_replaces_block(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(D, "failing_rules", return_value=""):
            run, ask = make_run(tmp), stub()
            for _ in range(2):
                r = D.run_diagnosis(run, "u", ask=ask)
            self.assertEqual(ask.calls[0][2], [run / "compare.png"])
            self.assertEqual(ask.calls[0][3], D.DIAG_SCHEMA)
            doc = json.loads((run / "diagnosis.json").read_text())
            self.assertEqual(doc["findings"], REPLY["findings"])
            self.assertEqual(r["owner"]["who"], "fit")
            review = (run / "review.md").read_text()
            self.assertEqual(review.count(D.HEADING), 1)
            self.assertIn("too wide", review)
            self.assertIn("too wide", (run / "diagnosis.md").read_text())

    def test_bad_replies_are_refused(self):
        bad = {**REPLY, "findings": [{**REPLY["findings"][0], "colour": "blue"}]}
        for name, doc in (("colour", bad), ("owner", {**REPLY, "owner": {"who": "me", "why": ""}}),
                          ("missing", {"findings": []})):
            with self.subTest(name):
                with self.assertRaises(ValueError):
                    D.check_reply(json.dumps(doc))
        self.assertEqual(D.check_reply(json.dumps(REPLY))["identity"], ["no backpack"])
        for key, val in (("deltas", "scale"), ("expected", {"sideways": 0.1})):
            with self.assertRaises(ValueError):
                D.check_reply(json.dumps({**REPLY, key: val}))


class Hook(unittest.TestCase):
    def test_default_on_for_check_only(self):
        for diag, verdict, runs in ((None, "CHECK", 1), (None, "PASS", 0), (True, "PASS", 1),
                                    (False, "CHECK", 0), (None, "SHAPE-PASS", 0)):
            with self.subTest(diag=diag, verdict=verdict), \
                    mock.patch.object(D, "run_diagnosis", return_value={"findings": [], "owner": {"who": "fit"},
                                                                         "cost": {"seconds": 0}}) as m:
                SP.run_diagnose(types.SimpleNamespace(diagnose=diag, out=pathlib.Path("."), id="u",
                                                      kind="mass", model="m"), verdict)
                self.assertEqual(m.call_count, runs)

    def test_failed_call_does_not_fail_the_run(self):
        args = types.SimpleNamespace(diagnose=True, out=pathlib.Path("."), id="u", kind="mass", model="m")
        with mock.patch.object(D, "run_diagnosis", side_effect=RuntimeError("boom")):
            self.assertIsNone(SP.run_diagnose(args, "CHECK"))

    def test_spec_is_the_same_with_and_without_diagnose(self):
        def digest(diag):
            with tempfile.TemporaryDirectory() as tmp, mock.patch.object(D, "failing_rules", return_value=""):
                run = make_run(tmp)
                args = types.SimpleNamespace(diagnose=diag, out=run, id="u", kind="mass", model="m")
                with mock.patch.object(SP, "ask", stub()):
                    SP.run_diagnose(args, "CHECK")
                return hashlib.sha256((run / "spec.json").read_bytes()).hexdigest()
        self.assertEqual(digest(True), digest(False))

    def test_nothing_before_review_reads_the_diagnosis(self):
        for fn in (SP.stage_one, SP.stage_shape, SP.repair, SP.run_passes, SP.fit_stage,
                   SP.author_specs, SP.best_of_n, SP.author_brief, SP.make_brief, SP.with_fewshot):
            with self.subTest(fn=fn.__name__):
                self.assertNotIn("diagnos", inspect.getsource(fn).lower())


if __name__ == "__main__":
    unittest.main()
