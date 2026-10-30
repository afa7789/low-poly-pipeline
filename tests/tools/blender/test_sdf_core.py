"""python3.14 -m unittest tests.tools.blender.test_sdf_core   (SLOW=1 runs Blender: a synthetic trunk + head + hand + prop built with sdf_core=on)"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import colour_stage as CS  # noqa: E402
import mesh_lint as ML  # noqa: E402
import parts_compare as PC  # noqa: E402
import retopo as RT  # noqa: E402
import sdf_body as S  # noqa: E402
import spec_pipeline as SP  # noqa: E402

BPY = mock.MagicMock()


def build_unit():
    with mock.patch.dict(sys.modules, {"bpy": BPY, "bmesh": BPY, "mathutils": BPY, "mathutils.bvhtree": BPY}):
        import build_unit as BU
    return BU


def row(bone, kind, mat="skin", **opts):
    return (bone, kind, (0.3, 0.3, 0.3), (0, 1, 0), mat, opts)


ROWS = [row("pelvis", "lathe"), row("spine", "lathe"), row("thigh.L", "limb"), row("head", "lathe"), row("head", "frustum", decal="sheet"),
        row("hand.L", "prism"), row("foot.L", "frustum"), row("spine", "plate", "iron"), row("spine", "box", "cloth"),
        row("forearm.R", "prism", prop="club", anchor="hand.R")]


class Roles(unittest.TestCase):
    def test_role_not_name(self):
        marked, idx = S.core_rows(ROWS, "biped", {"iron": "metal", "cloth": "cloth"})
        self.assertEqual(idx, [3, 4, 5, 6, 7])        # head, face decal, hand, foot, metal plate; the cloth box stays core, the prop is already out
        self.assertEqual([i for i, r in enumerate(marked) if S.is_body(r)], [0, 1, 2, 8])

    def test_arthropod_lower_legs_only(self):
        rows = [row("body", "lathe"), row("leg1.upper", "prism"), row("leg1.lower", "prism")]
        self.assertEqual(S.core_rows(rows, "spider")[1], [2])
        self.assertEqual(S.core_rows(rows, "quadruped")[1], [])

    def test_no_core_left_changes_nothing(self):
        rows = [row("head", "lathe"), row("foot.L", "frustum")]
        self.assertEqual(S.core_rows(rows), (rows, []))

    def test_field_leaves_rigid_rows_out(self):
        rows = [row("spine", "box"), row("head", "box"), row("hand.L", "box")]
        marked, idx = S.core_rows(rows)
        self.assertEqual((idx, [p["i"] for p in S.normalize(marked)]), ([1, 2], [0]))


class Budget(unittest.TestCase):
    def test_under_the_share_nothing_changes(self):
        pieces = [("a", 40, 1.0, "face"), ("b", 20, 1.0, "")]
        self.assertEqual(RT.piece_budgets(700, pieces), {"a": 40, "b": 20})

    def test_over_the_share_divides_by_area_and_keeps_the_minimums(self):
        pieces = [("face", 300, 0.01, "face"), ("hand", 100, 0.01, "hand"), ("prop", 300, 0.01, "prop"), ("big", 500, 5.0, "")]
        got = RT.piece_budgets(700, pieces)
        self.assertGreaterEqual(got["face"], 40)
        self.assertGreaterEqual(got["hand"], 12)
        self.assertGreaterEqual(got["prop"], 24)
        self.assertLessEqual(sum(got.values()), 350 + 4)
        self.assertTrue(all(got[n] <= t for n, t, *_ in pieces))
        self.assertGreater(got["big"], got["face"])

    def test_a_small_piece_gives_its_share_back(self):
        got = RT.piece_budgets(100, [("tiny", 10, 5.0, ""), ("fat", 400, 1.0, "")])
        self.assertEqual(got["tiny"], 10)
        self.assertEqual(got["fat"], 40)


class Flags(unittest.TestCase):
    def test_the_flag_reaches_the_builds(self):
        self.assertEqual(SP.DEFAULT_SDF_CORE, "on" if build_unit().SDF_CORE else "off")
        with mock.patch.object(SP, "SDF_CORE", "on" if SP.DEFAULT_SDF_CORE == "off" else "off"):
            self.assertTrue(SP.clay_args("mass")[-1].startswith("sdf_core="))
        self.assertEqual(CS.body_args(mock.Mock(body="sdf", sdf_core="on")), ["body=sdf", "sdf_core=on"])
        self.assertEqual(CS.body_args(object()), [])

    def test_the_floor_classes(self):
        BU = build_unit()
        self.assertEqual([BU.piece_kind(r) for r in (ROWS[9], ROWS[4], ROWS[5], ROWS[6])], ["prop", "face", "hand", ""])


class Compare(unittest.TestCase):
    def test_acceptance_reads_body_iou_stretch_and_face(self):
        row = {"unit": "u", "variant": "core", "ok": True, "body_iou": [0.9, 0.7], "head": 88, "stretch": {"walk": {"p99.5_stretch": 1.2}}}
        got, judged = PC.acceptance([row, {**row, "unit": "v", "body_iou": [0.8, None], "head": 20, "stretch": {"walk": {"p99.5_stretch": 2.1}}}],
                                    {"u": (3, 3), "v": (1, 3)})
        self.assertEqual(got, {"u": {"body_iou": False, "stretch": True, "face": True}, "v": {"body_iou": True, "stretch": False, "face": False}})
        self.assertEqual(judged, 1)

    def test_times_from_the_driver_lines(self):
        with tempfile.NamedTemporaryFile("w", suffix=".out") as f:
            f.write("n005 core exit=0 t=312s\nnoise\n")
            f.flush()
            self.assertEqual(PC.times_from(f.name), {("n005", "core"): 312.0})


SPEC = {"rig": "biped", "palette": {"skin": {"surface": "skin", "color": "#C08A5E"}, "iron": {"surface": "metal", "color": "#6E6C68"}}, "parts": [
    ["pelvis", "box", [0.5, 0.3, 0.3], [0, 1.35, 0], "skin", {}],
    ["spine", "box", [0.6, 0.66, 0.35], [0, 1.83, 0], "skin", {}],
    ["head", "box", [0.4, 0.4, 0.4], [0, 2.3, 0], "skin", {"decal": "sheet"}],
    ["forearm.R", "prism", [0.1, 0.5, 0.1], [-0.78, 1.1, 0.1], "iron", {"prop": "club", "anchor": "hand.R"}],
    ["hand.L", "box", [0.14, 0.14, 0.14], [0.78, 0.84, 0], "skin", {}],
    ["thigh.L", "box", [0.2, 0.6, 0.2], [0.28, 0.6, 0], "skin", {}],
    ["thigh.R", "box", [0.2, 0.6, 0.2], [-0.28, 0.6, 0], "skin", {}]]}


@unittest.skipUnless(os.environ.get("SLOW") and shutil.which("blender"), "SLOW=1: Blender, ~10 s")
class Blender(unittest.TestCase):
    def build(self, core):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp)
            (out / "spec.json").write_text(json.dumps(SPEC))
            subprocess.run(["blender", "-b", "-P", str(ROOT / "tools/blender/build_unit.py"), "--", str(out / "spec.json"), str(out / "model.glb"),
                            "700", "nofuse", "700", "body=sdf", f"sdf_core={core}"], check=True, capture_output=True)
            return ML.lint(out / "model.glb"), json.loads((out / "attach.json").read_text())["union"]

    def test_on_separates_the_rigid_pieces_and_off_is_today(self):
        on, doc = self.build("on")
        off, old = self.build("off")
        self.assertGreaterEqual(on["components"], 4)
        self.assertGreater(on["components"], off["components"])
        self.assertNotIn("core", old)
        self.assertEqual({r["bone"] for r in doc["core"]["rigid"]}, {"head", "hand.L"})
        self.assertGreaterEqual(doc["core"]["head"], 12)
        self.assertLessEqual(on["tris"], 700)
        self.assertEqual((on["materials"], off["materials"]), (2, 2))      # the prop keeps the iron, the head its own skin slot


if __name__ == "__main__":
    unittest.main()
