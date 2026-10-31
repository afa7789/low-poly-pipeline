"""L15-5: the eye stage (eye_lib.py DSL + validation, eye_stage.py loop). No model call: ask is a stub. The Blender cases need the n005 v15 run."""
import contextlib
import copy
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))
import eye_lib as EL  # noqa: E402
import eye_compare as EC  # noqa: E402
import eye_stage as ES  # noqa: E402
import mesh_lint  # noqa: E402

RUN = ROOT / "artifacts/model-sheets/runs/draft/n005/v15-r1"
BLENDER = bool(shutil.which("blender")) and (RUN / "model.glb").exists()
BONES = {"spine", "head", "forearm.L", "shin.L"}
BOX = ([-1.0, -0.8, 0.0], [1.0, 0.7, 2.8])
DSL = {"colours": {"coat": "3A3A3F", "skin": "C8A06F", "glove": "28282B", "gun": "7A7E85", "boot": "2A2A2D"}, "why": "t", "pieces": [
    {"op": "tube", "name": "coat", "mat": "coat", "bone": "spine", "role": "torso", "r0": 0.5, "r1": 0.44, "length": 1.0, "at": [0, 0, 1.4], "scale": [1, 0.72, 1]},
    {"op": "ball", "name": "head", "mat": "skin", "bone": "head", "role": "head", "r": 0.2, "at": [0, 0, 2.3]},
    {"op": "box", "name": "hand", "mat": "glove", "bone": "forearm.L", "role": "hand", "size": [0.2, 0.2, 0.2], "at": [0.8, 0, 0.9], "top": [0.8, 0.8]},
    {"op": "between", "name": "gun", "mat": "gun", "bone": "forearm.L", "role": "prop", "a": [0.8, -0.15, 0.9], "b": [0.8, -0.6, 0.9], "r0": 0.05, "r1": 0.04, "sides": 6},
    {"op": "box", "name": "boot", "mat": "boot", "bone": "shin.L", "role": "foot", "size": [0.3, 0.4, 0.2], "at": [0.25, -0.05, 0.1]}]}
ROLES = ["head", "hand", "foot", "prop", "torso"]


def check(dsl, **kw):
    return EL.validate(dsl, kw.get("bones", BONES), kw.get("box", BOX), kw.get("roles", ROLES))


class Validate(unittest.TestCase):
    def test_a_good_dsl_passes(self):
        self.assertEqual(check(DSL), [])

    def test_unknown_bone_is_rejected_with_its_name(self):
        bad = copy.deepcopy(DSL)
        bad["pieces"][1]["bone"] = "skull"
        self.assertTrue(any("'skull'" in e for e in check(bad)))

    def test_a_point_outside_the_sheet_box_is_rejected(self):
        bad = copy.deepcopy(DSL)
        bad["pieces"][3]["b"] = [0.8, -3.0, 0.9]
        self.assertTrue(any("outside the sheet's box" in e for e in check(bad)))
        edge = copy.deepcopy(DSL)
        edge["pieces"][3]["b"] = [0.8, -0.8 - 0.2 * 1.5 + 0.01, 0.9]      # inside the +-20 % margin
        self.assertEqual(check(edge), [])

    def test_triangle_budget_and_estimate(self):
        many = copy.deepcopy(DSL)
        many["pieces"] += [dict(DSL["pieces"][1], name=f"b{i}") for i in range(10)]     # 10 balls of 80 tris
        self.assertTrue(any("over the budget" in e for e in check(many)))
        self.assertEqual([EL.tris_of(p) for p in DSL["pieces"]], [28, 80, 12, 20, 12])

    def test_a_role_the_sheet_has_needs_a_piece(self):
        bad = copy.deepcopy(DSL)
        bad["pieces"] = [p for p in bad["pieces"] if p["role"] != "foot"]
        self.assertTrue(any("role 'foot'" in e for e in check(bad)))
        self.assertEqual(check(bad, roles=["head", "hand"]), [])        # a sheet with no foot does not ask for one

    def test_more_than_the_piece_limit_is_rejected(self):          # L16-1: n017 asked for 65
        many = copy.deepcopy(DSL)
        many["pieces"] = [dict(DSL["pieces"][2], name=f"b{i}") for i in range(EL.MAX_PIECES + 1)]
        self.assertTrue(any(f"{EL.MAX_PIECES + 1} pieces, over the limit" in e for e in check(many)))
        many["pieces"].pop()
        self.assertEqual(check(many, roles=[]), [])

    def test_a_blank_face_refuses_eye_pieces_and_keeps_the_face_surface(self):      # L18-0
        d = copy.deepcopy(DSL)
        d["pieces"] += [dict(DSL["pieces"][1], name="eye_L", role="face", r=0.02, seg=6, rings=3), dict(DSL["pieces"][1], name="face", role="face", r=0.15),
                        dict(DSL["pieces"][1], name="Nose tip", role="face", r=0.02, seg=6, rings=3)]
        self.assertEqual(check(d), [])
        errors = EL.validate(d, BONES, BOX, ROLES, face="none")
        self.assertEqual(len(errors), 2)
        self.assertTrue(all("blank face" in e for e in errors) and any("eye_L" in e for e in errors) and any("Nose tip" in e for e in errors))
        self.assertEqual(EL.validate(d, BONES, BOX, ROLES, face="lenses"), [])

    def test_shape_errors_are_listed_not_raised(self):
        bad = {"pieces": [{"op": "cone"}, {"op": "ball", "name": "x", "mat": "m", "bone": "head", "role": "head", "r": 0.001, "at": [0, 0]}]}
        errors = check(bad)
        self.assertTrue(any("op must be" in e for e in errors) and any("'at' must be a list of 3" in e for e in errors) and any("'r' must be" in e for e in errors))
        self.assertTrue(check({"pieces": []}))
        missing = copy.deepcopy(DSL)
        del missing["colours"]["coat"]
        self.assertTrue(any("has no colour" in e for e in check(missing)))


class Frame(unittest.TestCase):
    def test_box_in_blender_frame(self):
        # a sheet whose left panel looks right has the front at +z: Blender y = -z; one that looks left: y = +z
        box = [[-0.1, 1.0, -0.8], [0.2, 2.0, -0.2]]
        self.assertEqual(ES.box_blender(box, ES.forward_sign({"left_facing": 1})), ([-0.1, 0.2, 1.0], [0.2, 0.8, 2.0]))
        self.assertEqual(ES.box_blender(box, ES.forward_sign({"left_facing": -1})), ([-0.1, -0.8, 1.0], [0.2, -0.2, 2.0]))

    def test_the_face_kind_reaches_the_context_and_the_prompt(self):          # L18-0
        rig = {"bbox": [[-1, -1, 0], [1, 1, 2]], "bones": {"head": {"head": [0, 0, 1.8], "tail": [0, 0, 2], "parent": None}}}
        for identity, kind, words in ((None, "none", "BLANK face"), (["two small black dot eyes"], "eyes", "eyes as small dark/bright"),
                                      (["round iron goggles over bald head"], "lenses", "do NOT add eyes")):
            with self.subTest(kind=kind):
                ctx = ES.context_of({"parts": [], "identity": identity} if identity is not None else {"parts": []}, {}, rig)
                self.assertEqual(ctx["face"], kind)
                prompt = ES.make_prompt({"name": "u", "race": "r", "role": "x", "rig": "biped"}, ctx, rig, 0, [], None, {"parts": [0, 0], "views": {}, "rows": [], "disaster": []}, "old")
                self.assertIn(words, prompt)
                self.assertNotIn("{{face_rule}}", prompt)

    def test_tilts_text_round_trips_the_pinned_cameras(self):
        self.assertEqual(ES.tilt_text({"tilt": {"top": -20, "bottom": 30, "rts": [35, -45]}}), "top:-20,bottom:30,rts:35/-45")


def glb_facts(path):
    """{material: {joint: weight sum / vertices}} and the number of welded components of a GLB."""
    doc, blob = mesh_lint.read_glb(pathlib.Path(path))
    joints = [doc["nodes"][j]["name"] for j in doc["skins"][0]["joints"]]
    weights = {}
    for m in doc["meshes"]:
        for p in m["primitives"]:
            at = p["attributes"]
            j = mesh_lint.accessor(doc, blob, at["JOINTS_0"]).astype(int)
            w = mesh_lint.accessor(doc, blob, at["WEIGHTS_0"]).astype(float)
            w = w / (255 if w.max() > 1.5 and w.max() <= 255 else 65535 if w.max() > 255 else 1)
            used = {}
            for col in range(4):
                for joint in np.unique(j[:, col][w[:, col] > 0.5]):
                    used[joints[joint]] = float(w[j[:, col] == joint, col].min())
            weights[doc["materials"][p["material"]]["name"]] = used
    pos, _, _, tri = mesh_lint.geometry(doc, blob)
    return weights, mesh_lint.topology(pos, tri)[2], len(tri)


@unittest.skipUnless(BLENDER, "needs Blender and the n005 v15 run")
class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp())
        cls.glb = cls.tmp / "a.glb"
        cls.info = ES.build(RUN / "model.glb", DSL, cls.glb)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_components_materials_bones_and_weights(self):
        weights, comps, tris = glb_facts(self.glb)
        self.assertEqual(comps, 5)
        self.assertEqual(set(weights), {"coat", "skin", "glove", "gun", "boot"})
        self.assertEqual({m: set(j) for m, j in weights.items()},
                         {"coat": {"spine"}, "skin": {"head"}, "glove": {"forearm.L"}, "gun": {"forearm.L"}, "boot": {"shin.L"}})
        self.assertTrue(all(abs(w - 1.0) < 1e-3 for j in weights.values() for w in j.values()))
        self.assertEqual(tris, sum(EL.tris_of(p) for p in DSL["pieces"]))
        self.assertEqual(self.info["tris"], tris)

    def test_the_rig_and_its_clips_come_through(self):
        self.assertGreaterEqual(self.info["actions"], 3)
        EL.run_blender("bones", self.glb, self.tmp / "b.json")
        rig = json.loads((self.tmp / "b.json").read_text())
        self.assertIn("forearm.L", rig["bones"])
        self.assertEqual(len(rig["bbox"]), 2)

    def test_the_same_dsl_gives_the_same_vertices(self):
        again = self.tmp / "b.glb"
        ES.build(RUN / "model.glb", json.loads(json.dumps(DSL)), again)
        self.assertEqual(ES.vertex_hash(self.glb), ES.vertex_hash(again))
        moved = copy.deepcopy(DSL)
        moved["pieces"][1]["at"] = [0, 0, 2.4]
        third = self.tmp / "c.glb"
        ES.build(RUN / "model.glb", moved, third)
        self.assertNotEqual(ES.vertex_hash(self.glb), ES.vertex_hash(third))


def fake_measure(disasters):
    """measure() stub: the first calls report these disaster lists, then none."""
    queue = list(disasters)

    def measure(glb, work, sheet, rig, tilts=""):
        (work / "sil").mkdir(parents=True, exist_ok=True)
        d = queue.pop(0) if queue else []
        return {"views": {"front": {"iou": 0.5 if d else 0.9, "spill": 0.1, "bare": 0.1, "incoherent": False, "parts": [1, 2]}}, "parts": [1, 2], "rows": [], "disaster": d}
    return measure


@unittest.skipUnless(BLENDER, "needs Blender and the n005 v15 run")
class Loop(unittest.TestCase):
    UNIT = {"id": "n005", "name": "Warlock", "race": "Human", "role": "caster", "rig": "biped"}

    def run_stage(self, replies, disasters=(), rounds=3, fast=False, **kw):
        """fast: Blender builds and the finish are stubbed (the loop alone, ~3 s for 9 rounds)."""
        asked = []

        def ask(prompt, images, check_):
            asked.append((prompt, images))
            reply = replies[len(asked) - 1]
            check_(reply)
            return reply
        out = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out, True)
        stubs = [mock.patch.object(ES, "build", side_effect=self.fake_build), mock.patch.object(ES, "finish", side_effect=lambda summary, *_: summary)] if fast else []
        with mock.patch.object(ES, "measure", fake_measure(disasters)), mock.patch.object(ES, "stretch_of", return_value={"walk": {"p99.5_stretch": 1.0}}), \
                mock.patch.object(ES.outline, "apply", return_value=True), mock.patch.object(ES, "boards", side_effect=self.boards):
            with contextlib.ExitStack() as stack:
                for m in stubs:
                    stack.enter_context(m)
                summary = ES.run(self.UNIT, RUN, out, ask, rounds=rounds, log=lambda *_: None, **kw)
        return summary, asked, out

    @staticmethod
    def fake_build(src, dsl, out):
        out.write_bytes(b"glb")
        return {"tris": 100, "pieces": len(dsl["pieces"])}

    @staticmethod
    def boards(concept, work, stem, label, out_dir, mirror=()):
        out_dir.mkdir(parents=True, exist_ok=True)
        paths = [out_dir / "board-1.png", out_dir / "board-2.png"]
        for p in paths:
            p.write_bytes(b"png")
        return paths

    def test_stops_when_the_model_says_stop(self):
        summary, asked, out = self.run_stage([json.dumps(DSL), '{"stop": true, "why": "reads like the concept"}'])
        self.assertEqual([("tris" in r, r.get("stop")) for r in summary["rounds"]], [(True, None), (False, True)])
        self.assertEqual((summary["llm_calls"], summary["final_round"]), (2, 0))
        for f in ("model.glb", "clay.glb", "review.md", "timing.json", "eye/summary.json", "eye/round-0/dsl.json", "eye/round-0/prompt.md", "eye/round-0/images.txt", "eye/round-0/why.md"):
            self.assertTrue((out / f).exists(), f)
        self.assertIn("sheet.jpg", asked[0][1][0].name)
        self.assertEqual(len(asked[1][1]), 3)               # round 1: the sheet and the two boards of the last round (not the old model's)
        self.assertIn("Your previous reply", asked[1][0])
        self.assertNotIn('"stop": true', asked[0][0])            # round 0 cannot stop
        self.assertIn('"stop": true', asked[1][0])
        with mock.patch.object(ES, "boards", side_effect=self.boards):          # --eye replay: the recorded DSL again, no model call, the same vertices
            again = ES.run(self.UNIT, RUN, out, None, replay=True, log=lambda *_: None)
        self.assertTrue(again["replay"]["same"])
        self.assertEqual(again["vertex_hash"], summary["vertex_hash"])
        out2 = pathlib.Path(tempfile.mkdtemp())             # L19-0: --eye replay --eye-from RUN --run NEW: RUN's rounds copied, finished with the recipe given
        self.addCleanup(shutil.rmtree, out2, True)
        shutil.copy(RUN / "silhouette.json", out)             # the pipeline seeds a run with the source's small files
        with mock.patch.object(ES, "boards", side_effect=self.boards), mock.patch.object(ES, "finish", side_effect=lambda summary, *_: summary) as fin:
            ES.run(self.UNIT, out, out2, None, replay=True, log=lambda *_: None, union="bone", paint="box", fuse=12, union_reduce="cvt")
        self.assertTrue((out2 / "eye/round-0/dsl.json").exists() and (out2 / "eye/replay.glb").exists())
        self.assertEqual(fin.call_args.args[1:3], (out2 / "eye/replay.glb", DSL))
        self.assertEqual(fin.call_args.args[6:], ("off", "bone", "box", "hull", 12, "cvt", "off"))
        self.assertEqual(fin.call_args.args[0]["timing"], {})


@unittest.skipUnless(os.environ.get("SLOW"), "SLOW=1: 4 more runs of the loop, ~8 s each")
class LoopSlow(Loop):
    test_stops_when_the_model_says_stop = None      # the fast tier runs it

    def test_a_disaster_refuses_the_first_stop_and_the_second_one_stands(self):
        summary, _, _ = self.run_stage([json.dumps(DSL), '{"stop": true}', '{"stop": true}'], disasters=[[], ["front"]])      # the old model, then round 0
        self.assertEqual([r.get("stop") for r in summary["rounds"]], [None, "refused (disaster)", True])

    def test_the_rounds_are_capped_and_a_disaster_adds_one(self):
        summary, _, _ = self.run_stage([json.dumps(DSL)] * 4, disasters=[[], [], []], rounds=2)
        self.assertEqual(len([r for r in summary["rounds"] if "tris" in r]), 2)      # rounds=2 and no disaster: stops
        summary, _, _ = self.run_stage([json.dumps(DSL)] * 4, disasters=[["front"]] * 5, rounds=2)
        self.assertEqual(len([r for r in summary["rounds"] if "tris" in r]), ES.MAX_ROUNDS)

    def test_an_invalid_first_reply_ends_the_stage_without_a_model(self):
        bad = copy.deepcopy(DSL)
        bad["pieces"][0]["bone"] = "nope"
        summary, _, out = self.run_stage([json.dumps(bad)])
        self.assertIsNone(summary["final_round"])
        self.assertIn("error", summary["rounds"][0])
        self.assertFalse((out / "model.glb").exists())


class Rounds(Loop):
    """L16-1: nine rounds, the stop modes and the judge's stop rule (the loop alone: builds, finish and the judge are stubs)."""
    test_stops_when_the_model_says_stop = None

    @staticmethod
    def verdict(sheet="tie", artist="tie"):
        return {a: {"winner": w} for a, w in (("sheet", sheet), ("artist", artist), ("wc3", "tie"), ("form", "tie"))}

    def test_nine_rounds_are_asked_and_built(self):
        summary, asked, _ = self.run_stage([json.dumps(DSL)] * 9, rounds=9, fast=True)
        self.assertEqual((len(asked), len([r for r in summary["rounds"] if "tris" in r]), summary["llm_calls"]), (9, 9, 9))
        self.assertEqual(ES.MAX_ROUNDS, 9)

    def test_stop_never_records_the_request_and_goes_on_then_honours_a_second_one(self):
        replies = [json.dumps(DSL), '{"stop": true}', json.dumps(DSL), '{"stop": true}', '{"stop": true}']
        summary, asked, _ = self.run_stage(replies, rounds=9, fast=True, stop="never")
        self.assertEqual([r.get("stop") for r in summary["rounds"]], [None, "ignored (stop=never)", None, "ignored (stop=never)", True])
        self.assertIn("NOT HONOURED", asked[2][0])

    def test_stop_model_honours_the_first_request(self):
        summary, _, _ = self.run_stage([json.dumps(DSL), '{"stop": true}'], rounds=9, fast=True, stop="model")
        self.assertEqual([r.get("stop") for r in summary["rounds"]], [None, True])

    def test_the_judge_stops_after_two_stalled_rounds_in_a_row(self):
        seen = []

        def judge(a, b):
            seen.append((a.name, b.name))
            return self.verdict(sheet="B") if len(seen) == 1 else self.verdict()       # round 1 wins the judge, rounds 2 and 3 stall (parts 1/2 each)
        with mock.patch.object(ES, "round_run", side_effect=lambda rd, _: rd):
            summary, asked, _ = self.run_stage([json.dumps(DSL)] * 9, rounds=9, fast=True, stop="judge", judge=judge)
        self.assertEqual(len(asked), 4)                                         # rounds 0-3, then the second stall ends it
        self.assertEqual(seen, [("round-0", "round-1"), ("round-1", "round-2"), ("round-2", "round-3")])
        self.assertEqual([r.get("stalled") for r in summary["rounds"]], [None, False, True, True])

    def test_stalled_wants_no_new_part_and_no_judge_win(self):
        self.assertTrue(ES.stalled([10, 12], [10, 12], self.verdict()))
        self.assertTrue(ES.stalled([10, 12], [9, 12], self.verdict(artist="A")))
        self.assertFalse(ES.stalled([10, 12], [11, 12], self.verdict()))
        self.assertFalse(ES.stalled([10, 12], [10, 12], self.verdict(artist="B")))


def pair(form, artist):
    """A pairwise result: (winner, B votes) per axis."""
    return {a: {"winner": w, "A": 4 - b, "B": b} for a, (w, b) in (("form", form), ("artist", artist))}




class Report(unittest.TestCase):
    """eye_compare: the judge's wins and the brief's acceptance, from numbers (no disk)."""

    @staticmethod
    def summary(iou=0.8, tris=600, seconds=500, stretch=1.0, incoherent=False):
        return {"final_round": 1, "seconds": seconds, "stretch": {"walk": {"p99.5_stretch": stretch}},
                "rounds": [{"round": 1, "tris": tris, "views": {"front": {"iou": iou, "incoherent": incoherent}}}]}

    def test_a_win_needs_both_axes_3_1_for_the_new_run(self):
        self.assertTrue(EC.wins(pair(("B", 4), ("B", 3))))
        self.assertFalse(EC.wins(pair(("B", 4), ("tie", 2))))
        self.assertFalse(EC.wins(pair(("A", 0), ("B", 4))))

    def test_acceptance_counts_wins_in_all_and_in_the_unseen_units(self):
        units = ["n02X", "n005", "n00U", "hfoo", "n017", "n01X"]
        win, lose = pair(("B", 4), ("B", 4)), pair(("A", 0), ("B", 4))
        sums = {u: self.summary() for u in units}
        got = EC.acceptance(units, {u: win for u in units[:3]} | {"hfoo": win, "n017": lose, "n01X": lose}, sums)
        self.assertTrue(got["judge >= 3-1 in >= 4/6"])
        self.assertFalse(got["judge >= 2/3 unseen"])
        self.assertTrue(got["stretch <= 1.5"] and got["pieces <= 700 tris"] and got["<= 15 min"])
        self.assertEqual(got["coherent views under IoU .6"], [])

    def test_the_guards_fail_on_iou_stretch_triangles_and_time(self):
        win = pair(("B", 4), ("B", 4))
        bad = {"n005": self.summary(iou=0.5, tris=701, seconds=16 * 60, stretch=1.8)}
        got = EC.acceptance(["n005"], {"n005": win}, bad)
        self.assertEqual(got["coherent views under IoU .6"], ["n005 front"])
        self.assertFalse(got["pieces <= 700 tris"] or got["<= 15 min"])
        self.assertTrue(got["stretch <= 2.0"])
        self.assertFalse(got["stretch <= 1.5"])
        self.assertEqual(EC.acceptance(["n005"], {}, {"n005": self.summary(iou=0.5, incoherent=True)})["coherent views under IoU .6"], [])

    def test_falls_marks_a_view_more_than_2_sigma_under_the_base(self):
        noise = {"global": {"front": 0.01, "left": 0.01}}
        views = {"front": {"iou": 0.80}, "left": {"iou": 0.90}}
        base = {"front": {"iou": 0.90}, "left": {"iou": 0.89}}
        self.assertEqual(EC.falls("u", views, base, noise), ["front"])


class Curve(unittest.TestCase):
    """L16-1 rounds curve: prefixes of a run and the acceptance of N rounds over 3, from numbers."""

    @staticmethod
    def full():
        rounds = [{"round": r, "llm_s": 100, "build_s": 2, "measure_s": 8, "tris": 600, "pieces": 40, "parts": [20 + r, 28], "views": {}, "resent": int(r == 1)} for r in range(9)]
        rounds.insert(2, {"round": 1, "stop": "ignored (stop=never)", "llm_s": 50})
        return {"base": {"seconds": 10.0}, "rounds": rounds, "llm_calls": 11, "resends": 1, "seconds": 1000, "final_round": 8, "vertex_hash": "x"}

    def test_a_prefix_keeps_the_rounds_calls_and_seconds_up_to_n(self):
        got = EC.prefix_summary(self.full(), 3)
        self.assertEqual([r["round"] for r in got["rounds"] if "tris" in r], [0, 1, 2])
        self.assertEqual((got["final_round"], got["llm_calls"], got["resends"]), (2, 5, 1))     # 3 built + 1 resend + the ignored stop
        self.assertEqual(got["seconds"], 10 + 3 * 110 + 50)
        self.assertNotIn("vertex_hash", got)

    def test_the_acceptance_needs_sheet_and_artist_3_1_form_2_2_in_4_of_6_and_twice_the_cost_at_most(self):
        win = {"sheet": {"winner": "B", "A": 1, "B": 3}, "artist": {"winner": "B", "A": 0, "B": 4}, "form": {"winner": "tie", "A": 2, "B": 2}}
        lose = {"sheet": {"winner": "tie", "A": 2, "B": 2}, "artist": {"winner": "B", "A": 0, "B": 4}, "form": {"winner": "A", "A": 3, "B": 1}}
        units = ["a", "b", "c", "d", "e", "f"]
        res = {("v16-r6", "v16-r3"): {u: win if u in "abcd" else lose for u in units}, (EC.FULL, "v16-r3"): {u: lose for u in units}}
        secs = {"v16-r3": {u: 600 for u in units}, "v16-r6": {u: 1100 for u in units}, EC.FULL: {u: 1500 for u in units}}
        got = EC.curve_acceptance(res, secs)
        self.assertTrue(got["r6"]["accepted"])
        self.assertEqual(got["r6"]["cost x r3"], 1.83)
        self.assertFalse(got["r9"]["accepted"])
        self.assertFalse(got["r9"]["cost <= 2x r3"])
        secs["v16-r6"] = {u: 1300 for u in units}
        self.assertFalse(EC.curve_acceptance(res, secs)["r6"]["accepted"])


if __name__ == "__main__":
    unittest.main()
