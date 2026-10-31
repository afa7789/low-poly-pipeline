"""L16-2: the critic (eye_critic.py) and its seam in the eye stage. No model call: both asks are stubs. The loop cases need Blender and the n005 v15 run."""
import json
import pathlib
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import critic_compare as CC  # noqa: E402
import eye_critic as EC  # noqa: E402
import eye_stage as ES  # noqa: E402
import spec_pipeline as SP  # noqa: E402
import test_eye as TE  # noqa: E402

D1 = {"part": "hand.L", "view": "front", "what": "the glove is the skin colour", "fix": "recolour piece hand.L to 28282B", "severity": 3}
D2 = {"part": "gun", "view": "left", "what": "the gun is in front of the body, the sheet has it behind", "fix": "move gun by [0, 0.5, 0]", "severity": 1}
UNIT = {"name": "Warlock", "race": "Human", "role": "caster"}


def reply(defects, verdict="continue", resolved=()):
    return json.dumps({"defects": defects, "verdict": verdict, "why": "w", "resolved": list(resolved)})


class Schema(unittest.TestCase):
    def test_a_defect_without_a_fix_is_rejected(self):
        with self.assertRaisesRegex(EC.Invalid, "no 'fix'"):
            EC.parse(reply([{k: v for k, v in D1.items() if k != "fix"}]))

    def test_severity_verdict_and_resolved_ids_are_checked(self):
        for bad in (reply([dict(D1, severity=4)]), reply([D1], verdict="maybe"), reply([D1], resolved=["d9.9"])):
            with self.assertRaises(EC.Invalid):
                EC.parse(bad, ["d1.1"])

    def test_defects_are_ordered_by_severity_and_capped_at_12(self):
        doc = EC.parse(reply([D2] * 10 + [D1] * 5))
        self.assertEqual((len(doc["defects"]), doc["defects"][0]["severity"]), (12, 3))


class Review(unittest.TestCase):
    def test_the_face_note_reaches_the_critic_prompt(self):          # L18-0
        text = EC.prompt_of(dict(UNIT, face_note=ES.FACE_CRITIC["none"]), 1, {"pieces": []}, "", [], "old")
        self.assertIn("BLANK", text)
        self.assertNotIn("{{face_note}}", EC.prompt_of(UNIT, 1, {"pieces": []}, "", [], "old"))

    def test_the_fix_rate_and_the_fixer_note(self):
        out = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out, True)
        prev = EC.with_ids([D1, D2], 1)
        doc = EC.review(lambda p, i, c: reply([D2], resolved=["d1.1"]), UNIT, 2, [], {"pieces": []}, "numbers", prev, "round 1 model", out)
        self.assertEqual((doc["fix_rate"], doc["of_previous"], doc["defects"][0]["id"]), (0.5, 2, "d2.1"))
        self.assertTrue((out / "critic.json").exists())
        self.assertIn("d1.1", (out / "critic-prompt.md").read_text())
        note = EC.fixer_note(EC.review(lambda p, i, c: reply([D1, D2]), UNIT, 1, [], {}, "n", [], "old", out))
        self.assertIn("recolour piece hand.L", note)
        self.assertIn("move gun by", note)
        self.assertIn('"fixed"', note)


@unittest.skipUnless(TE.BLENDER, "needs Blender and the n005 v15 run")
class Loop(unittest.TestCase):
    UNIT = {"id": "n005", "name": "Warlock", "race": "Human", "role": "caster", "rig": "biped"}

    def run_stage(self, fixer_replies, critic_replies, rounds=2):
        fixer, critic = [], []

        def ask_fixer(prompt, images, check_):
            fixer.append((prompt, images))
            check_(fixer_replies[len(fixer) - 1])
            return fixer_replies[len(fixer) - 1]

        def ask_critic(prompt, images, check_):
            critic.append((prompt, images))
            check_(critic_replies[len(critic) - 1])
            return critic_replies[len(critic) - 1]
        out = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out, True)
        with mock.patch.object(ES, "measure", TE.fake_measure(())), mock.patch.object(ES, "stretch_of", return_value={}), \
                mock.patch.object(ES.outline, "apply", return_value=True), mock.patch.object(ES, "boards", side_effect=TE.Loop.boards):
            summary = ES.run(self.UNIT, TE.RUN, out, ask_fixer, rounds=rounds, log=lambda *_: None, critic=ask_critic)
        return summary, fixer, critic, out

    def test_the_fixer_gets_the_defects_and_the_audit_closes_the_last_round(self):
        fixed = dict(TE.DSL, fixed=["d1.1"])
        summary, fixer, critic, out = self.run_stage([json.dumps(TE.DSL), json.dumps(fixed)], [reply([D1, D2]), reply([D2], resolved=["d1.1"])])
        self.assertEqual((len(fixer), len(critic)), (2, 2))
        self.assertIn("recolour piece hand.L", fixer[1][0])
        self.assertIn("move gun by", fixer[1][0])
        self.assertEqual(len(fixer[1][1]), 1)               # the sheet, not the boards
        self.assertEqual(summary["fixed"][1], ["d1.1"])
        self.assertEqual([(c["round"], c["fix_rate"], c.get("audit")) for c in summary["critic"]], [(1, None, None), (2, 0.5, True)])
        self.assertTrue((out / "eye/round-1/critic.json").exists() and (out / "eye/audit/critic.json").exists())

    def test_a_critic_stop_ends_the_loop_without_a_fixer_call(self):
        summary, fixer, critic, _ = self.run_stage([json.dumps(TE.DSL)], [reply([], verdict="stop")], rounds=3)
        self.assertEqual((len(fixer), len(critic), summary["final_round"]), (1, 1, 0))
        self.assertEqual(summary["rounds"][-1]["stop"], "critic")


def pair(sheet, artist, form):
    return {"sheet": {"B": sheet}, "artist": {"B": artist}, "form": {"B": form}}


class Acceptance(unittest.TestCase):
    summaries = {"a": {"seconds": 100, "critic": [{"of_previous": 4, "resolved": 3}, {"of_previous": 0, "resolved": 0}]}, "b": {"seconds": 100, "critic": [{"of_previous": 6, "resolved": 3}]}}

    def test_the_pooled_fix_rate_skips_rounds_without_a_previous_list(self):
        self.assertAlmostEqual(CC.fix_rate(self.summaries.values()), 0.6)
        self.assertIsNone(CC.fix_rate([{"critic": []}]))

    def test_accepted_only_when_the_judge_the_form_the_rate_and_the_time_all_hold(self):
        win, lose = pair(3, 4, 2), pair(2, 4, 2)
        base = {"a": {"seconds": 100}, "b": {"seconds": 100}}
        ok = CC.acceptance({u: win for u in "abcd"} | {"e": lose, "f": lose}, self.summaries, base)
        self.assertEqual((ok["won"], ok["accepted"]), (list("abcd"), True))
        self.assertFalse(CC.acceptance({u: win for u in "abc"} | {"d": lose}, self.summaries, base)["accepted"])
        self.assertFalse(CC.acceptance({u: win for u in "abcd"}, self.summaries, {"a": {"seconds": 50}, "b": {"seconds": 50}})["time <= 1.5x v16"])


@unittest.skipUnless(TE.BLENDER, "needs Blender and the n005 v15 run")
class Failure(unittest.TestCase):
    UNIT = Loop.UNIT

    def test_a_critic_that_fails_leaves_the_artist_to_look_for_itself(self):
        def broken(prompt, images, check_):
            raise RuntimeError("claude -p failed")
        out = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out, True)
        with mock.patch.object(ES, "measure", TE.fake_measure(())), mock.patch.object(ES, "stretch_of", return_value={}), \
                mock.patch.object(ES.outline, "apply", return_value=True), mock.patch.object(ES, "boards", side_effect=TE.Loop.boards):
            summary = ES.run(self.UNIT, TE.RUN, out, lambda p, i, c: json.dumps(TE.DSL), rounds=2, log=lambda *_: None, critic=broken)
        self.assertEqual([("error" in c) for c in summary["critic"]], [True, True])
        self.assertEqual(summary["final_round"], 1)


class Command(unittest.TestCase):
    def test_model_at_effort_becomes_the_effort_flag(self):
        argv, _ = SP.session_command("claude-fable-5-1@max", "b", [])
        self.assertEqual(argv[argv.index("--model") + 1:argv.index("--model") + 4], ["claude-fable-5-1", "--effort", "max"])
        self.assertNotIn("--effort", SP.session_command("opus", "b", [])[0])


if __name__ == "__main__":
    unittest.main()
