"""python3.14 -m unittest tests.tools.blender.test_body_sdf   (SLOW=1 runs Blender: n005 built with body=sdf closes mesh_lint's gates)"""
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
import sdf_body as S  # noqa: E402
import spec_pipeline as SP  # noqa: E402

RUN = ROOT / "artifacts/model-sheets/runs/draft/n005/v12-r1"
BPY = mock.MagicMock()


def build_unit():
    with mock.patch.dict(sys.modules, {"bpy": BPY, "bmesh": BPY, "mathutils": BPY, "mathutils.bvhtree": BPY}):
        import build_unit as BU
    return BU


def row(kind, dims, at, bone="spine"):
    return (bone, kind, dims, at, "iron", {})


class Flags(unittest.TestCase):
    def test_body_derives_union_body_and_nounion(self):
        BU = build_unit()
        self.assertEqual(BU.body_flags(None, False), (BU.BODY, True, False))     # the default: "sdf" since v13 (28.L10-9)
        self.assertEqual(BU.body_flags("sdf", False), ("sdf", True, False))
        self.assertEqual(BU.body_flags("join", False), ("join", False, True))
        self.assertEqual(BU.body_flags("sdf", True), ("join", False, True))      # the old word wins: the join build
        with self.assertRaises(ValueError):
            BU.body_flags("mesh", False)

    def test_spec_pipeline_reads_the_defaults_from_the_source(self):
        self.assertIn("\nUNION_BODY = True", (ROOT / "tools/blender/build_unit.py").read_text())     # the regex of old readers
        self.assertEqual(SP.DEFAULT_BODY, build_unit().BODY)

    def test_sdf_arguments(self):
        BU = build_unit()
        self.assertEqual(BU.sdf_args(["body=sdf", "sdf_grid=64", "sdf_adapt=0.5", "sdf_k=0", "sdf_thin=keep"]),
                         {"grid": 64, "adaptivity": 0.5, "k": 0.0, "thin": "keep"})
        self.assertEqual(BU.sdf_args(["body=sdf"]), {})

    def test_body_reaches_the_builds(self):
        with mock.patch.object(SP, "BODY", "union"):
            self.assertEqual(SP.clay_args("mass")[-1], "body=union")
        self.assertEqual(SP.clay_args("mass"), ["700", "nofuse", "700", "clay"])        # the default adds nothing
        self.assertEqual(CS.body_args(mock.Mock(body="sdf")), ["body=sdf"])
        self.assertEqual(CS.body_args(object()), [])


class ThinParts(unittest.TestCase):
    """Policy for a part under 2 voxels (PIPELINE 28.L10-7), on a body of one thick box and one plate."""
    ROWS = [row("box", (0.5, 0.8, 0.3), (0, 1.0, 0)), row("box", (0.6, 0.6, 0.004), (0, 1.0, 0.31))]

    def field(self, thin):
        return S.field(self.ROWS, None, ("biped", ()), 1.0, 48, False, thin=thin)

    def test_inflation_is_the_missing_thickness_to_two_and_a_half_voxels(self):
        parts = [{"i": 3, "r": 0.5}, {"i": 5, "r": 0.004}]
        self.assertEqual(S.thin_inflation(parts, 0.01), {5: (0.025 - 0.008) / 2})
        self.assertEqual(S.thin_inflation(parts, 0.001), {})

    def test_off_inflate_keep(self):
        off, fat, kept = self.field("off"), self.field("inflate"), self.field("keep")
        self.assertEqual((off.kept, fat.kept, kept.kept), ([], [], [1]))
        self.assertEqual((len(off.parts), len(fat.parts), len(kept.parts)), (2, 2, 1))
        plate = np_point(0, -(0.31 + 0.004), 1.0)        # just over the plate's face (Blender axes: depth on -y, up on z)
        self.assertGreater(off.d(plate)[0], 0)
        self.assertLess(fat.d(plate)[0], off.d(plate)[0])
        self.assertTrue(all("inflate" not in p for p in off.parts))                   # off leaves the parts as they were

    def test_inflated_plate_has_inside_voxels(self):
        inside = lambda f: int((f.grid < 0).sum())  # noqa: E731
        self.assertGreater(inside(self.field("inflate")), inside(self.field("off")))


def np_point(*xyz):
    import numpy as np
    return np.array([xyz], float)


@unittest.skipUnless(os.environ.get("SLOW") and shutil.which("blender") and RUN.exists(), "SLOW=1: Blender, n005, ~10 s")
class Blender(unittest.TestCase):
    def test_sdf_build_closes_the_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp)
            shutil.copy(RUN / "spec.json", out / "spec.json")
            subprocess.run(["blender", "-b", "-P", str(ROOT / "tools/blender/build_unit.py"), "--", str(out / "spec.json"),
                            str(out / "clay.glb"), "700", "nofuse", "700", "clay", "body=sdf", f"cuts={RUN / 'fit/cuts.json'}"],
                           check=True, capture_output=True)
            m, doc = ML.lint(out / "clay.glb"), json.loads((out / "attach.json").read_text())["union"]
            self.assertTrue((out / "clay.sdf.json").exists())
        self.assertEqual((m["skins"], m["components_body"], m["boundary_edges"], m["nonmanifold_edges"], m["flipped"]), (1, 1, 0, 0, 0))
        self.assertLess(m["sliver_pct"], 5)
        self.assertLessEqual(m["tris"], 700)
        self.assertEqual((doc["method"], doc["grid"], doc["components_body"]), ("sdf", 96, 1))
        self.assertTrue(doc["retopo"]["target_met"])


if __name__ == "__main__":
    unittest.main()
