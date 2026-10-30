"""python3.14 -m unittest tests.tools.blender.test_sdf_extract   (SLOW=1 runs Blender: sdf_mesh of n005, closed, sdf_dev)"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import mesh_lint as ML  # noqa: E402
import sdf_body as S  # noqa: E402

RUN = ROOT / "artifacts/model-sheets/runs/draft/n005/v12-r1"


class Pure(unittest.TestCase):
    def test_index_to_world(self):
        w = S.index_to_world([[0, 0, 0], [2, 4, 6.5]], (1.0, -2.0, 0.5), 0.25)
        np.testing.assert_allclose(w, [[1.0, -2.0, 0.5], [1.5, -1.0, 2.125]])

    def test_quads_to_tris_counts_and_shorter_diagonal(self):
        pts = np.array([[0, 0, 0], [4, 0, 0], [4, 1, 0], [0, 1, 0]], float)      # a trapezoid: 1-3 is the short diagonal
        pts[3] = [3, 1, 0]
        t = S.quads_to_tris(pts, [[0, 1, 2]], [[0, 1, 2, 3]])
        self.assertEqual(t.shape, (3, 3))
        self.assertEqual({tuple(sorted(x)) for x in t[1:]}, {(1, 2, 3), (0, 1, 3)})   # cut along 1-3
        area = lambda x: np.cross(pts[x[1]] - pts[x[0]], pts[x[2]] - pts[x[0]])[2] / 2  # noqa: E731
        self.assertTrue(all(area(x) > 0 for x in t[1:]))          # winding kept
        self.assertAlmostEqual(sum(area(x) for x in t[1:]), 2.5)

    def test_no_quads(self):
        self.assertEqual(S.quads_to_tris(np.zeros((3, 3)), [[0, 1, 2]], np.zeros((0, 4))).shape, (1, 3))


@unittest.skipUnless(os.environ.get("SLOW") and shutil.which("blender") and RUN.exists(), "SLOW=1: Blender, n005, ~10 s")
class Blender(unittest.TestCase):
    def test_sdf_mesh_is_closed_and_on_the_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["blender", "-b", "-P", str(ROOT / "tools/blender/sdf_extract.py"), "--", str(RUN), tmp,
                            "grids=96", "adapt=0.5", "octree=5"], check=True, capture_output=True)
            m = ML.lint(pathlib.Path(tmp) / "clay-sdfraw-g96-a0.5.glb")
            row = next(r for r in json.loads((pathlib.Path(tmp) / "ablation.json").read_text())["rows"] if r["config"] == "sdf-g96-a0.5")
        self.assertEqual((m["boundary_edges"], m["nonmanifold_edges"], m["components"], m["flipped"]), (0, 0, 1, 0))
        self.assertLess(m["sliver_pct"], 4)
        self.assertLessEqual(row["sdf_dev"]["p95"], 0.5)

    def test_skin_is_one_skin_one_body_with_the_clips(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["blender", "-b", "-P", str(ROOT / "tools/blender/sdf_extract.py"), "--", str(RUN), tmp, "skin=1", "clay=0"],
                           check=True, capture_output=True)
            m = ML.lint(pathlib.Path(tmp) / "clay-sdfskin.glb")
            info = json.loads((pathlib.Path(tmp) / "clay-sdfskin.json").read_text())
            imported = ML.engine_import(pathlib.Path(tmp) / "clay-sdfskin.glb")
        self.assertEqual((m["skins"], m["components_body"], m["boundary_edges"], m["nonmanifold_edges"]), (1, 1, 0, 0))
        self.assertTrue(imported.startswith("ok"))
        self.assertTrue({"pelvis", "thigh.L", "shin.L", "spine", "head"} <= set(info["groups"]))
        self.assertGreater(len(info["materials"]), 1)


if __name__ == "__main__":
    unittest.main()
