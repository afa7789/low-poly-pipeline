"""python3 -m unittest discover -s tests/tools/blender"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import spec_pipeline as SP  # noqa: E402

# runs inside Blender: a hollow shell holding a small cube nobody can see, then a subdivided plate
SCRIPT = """
import json, sys
sys.path.insert(0, {tools!r})
import bpy, cull
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add(size=2)
outer = bpy.context.object
bpy.ops.mesh.primitive_cube_add(size=0.5)
bpy.context.object.select_set(True)
outer.select_set(True)
bpy.context.view_layer.objects.active = outer
bpy.ops.object.join()
stats = cull.cull(outer, {out!r}, remove=True)
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=24, ring_count=12)
sphere = bpy.context.object
tol = cull.decimate_union(sphere, 1000, blind=False)
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=24, ring_count=12)
budget = cull.decimate_union(bpy.context.object, 10, blind=False)
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=24, ring_count=12)
floor = cull.decimate_union(bpy.context.object, 1000, blind=False, floor=200)
json.dump({{"cull": stats, "tol": tol, "budget": budget, "floor": floor, "left": len(outer.data.polygons)}}, open({res!r}, "w"))
"""


@unittest.skipUnless(shutil.which("blender"), "blender not installed")
class CullInBlender(unittest.TestCase):
    def test_hidden_cube_removed_and_tolerance_decimate(self):
        with tempfile.TemporaryDirectory() as tmp:
            script, res = pathlib.Path(tmp) / "s.py", pathlib.Path(tmp) / "res.json"
            script.write_text(SCRIPT.format(tools=str(ROOT / "tools/blender"), out=str(pathlib.Path(tmp) / "x.glb"),
                                            res=str(res)))
            subprocess.run(["blender", "-b", "-P", str(script)], capture_output=True, timeout=120)
            out = json.loads(res.read_text())
            self.assertEqual((out["cull"]["total_faces"], out["cull"]["visible_faces"]), (12, 6))
            self.assertEqual(out["left"], 6)
            self.assertTrue((pathlib.Path(tmp) / "cull.json").exists())
            self.assertLessEqual(out["tol"]["dev"], out["tol"]["tol"] + 1e-6)
            self.assertLess(out["tol"]["faces"], out["tol"]["faces_before"])
            self.assertTrue(out["budget"]["budget_bound"])          # the budget beats the tolerance
            self.assertLess(out["budget"]["faces"], 30)
            self.assertGreaterEqual(out["floor"]["faces"], 190)       # the floor holds the tolerance back


class ReviewRow(unittest.TestCase):
    def test_row_and_missing_stats(self):
        self.assertEqual(SP.cull_row({}), "")
        kept = SP.cull_row({"cull": {"visible_tris": 534, "total_tris": 620}})
        self.assertIn("534/620 (86%)", kept)
        self.assertIn("kept", kept)
        gone = SP.cull_row({"cull": {"visible_tris": 5, "total_tris": 10, "removed": True, "tris_after": 5}})
        self.assertIn("removed -> 5 tris", gone)

    def test_stats_read_from_beside_the_glb(self):
        with tempfile.TemporaryDirectory() as tmp:
            glb = pathlib.Path(tmp) / "clay.glb"
            self.assertIsNone(SP.cull_stats(glb))
            (pathlib.Path(tmp) / "cull.json").write_text('{"visible_tris": 1}')
            self.assertEqual(SP.cull_stats(glb), {"visible_tris": 1})


if __name__ == "__main__":
    unittest.main()
