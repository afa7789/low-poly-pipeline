"""python3.14 -m unittest discover -s tests/tools/blender"""
import json
import pathlib
import struct
import sys
import tempfile
import unittest

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import mesh_lint as L  # noqa: E402
import spec_pipeline as SP  # noqa: E402

CUBE = [(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)]
# outward-wound (CCW seen from outside) triangles of the unit cube, vertex ids into CUBE
TRIS = [(0, 3, 2), (0, 1, 3), (4, 7, 5), (4, 6, 7), (0, 5, 1), (0, 4, 5),
        (2, 7, 6), (2, 3, 7), (0, 6, 4), (0, 2, 6), (1, 7, 3), (1, 5, 7)]


def glb(path, tris=TRIS, scale=None, lift=0.0):
    """A one-primitive GLB of the cube; vertex normals point away from the centre."""
    pos = (np.array(CUBE) + [0, lift, 0]).astype("<f4")
    nor = (np.array(CUBE, "<f4") - 0.5)
    nor /= np.linalg.norm(nor, axis=1, keepdims=True)
    idx = np.array(tris, "<u2").ravel()
    blob = pos.tobytes() + nor.astype("<f4").tobytes() + idx.tobytes()
    node = {"mesh": 0, **({"scale": scale} if scale else {})}
    doc = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [node],
           "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1}, "indices": 2}]}],
           "buffers": [{"byteLength": len(blob)}],
           "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 96},
                           {"buffer": 0, "byteOffset": 96, "byteLength": 96},
                           {"buffer": 0, "byteOffset": 192, "byteLength": len(idx) * 2}],
           "accessors": [{"bufferView": 0, "componentType": 5126, "count": 8, "type": "VEC3"},
                         {"bufferView": 1, "componentType": 5126, "count": 8, "type": "VEC3"},
                         {"bufferView": 2, "componentType": 5123, "count": len(idx), "type": "SCALAR"}]}
    js = json.dumps(doc).encode()
    js += b" " * (-len(js) % 4)
    blob += b"\0" * (-len(blob) % 4)
    total = 12 + 8 + len(js) + 8 + len(blob)
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, total) + struct.pack("<I4s", len(js), b"JSON") + js
                     + struct.pack("<I4s", len(blob), b"BIN\0") + blob)
    return path


class Lint(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def test_closed_cube_is_clean(self):
        m = L.lint(glb(self.tmp / "a.glb"))
        self.assertEqual((m["faces"], m["flipped"], m["degenerate"], m["boundary_edges"],
                          m["nonmanifold_edges"], m["components"]), (12, 0, 0, 0, 0, 1))
        self.assertEqual(L.failing(m, textured=False), [])

    def test_flipped_winding_and_open_edges_are_found(self):
        m = L.lint(glb(self.tmp / "b.glb", tris=[(a, c, b) for a, b, c in TRIS[:-2]]))
        self.assertEqual(m["flipped"], 10)
        self.assertGreater(m["boundary_edges"], 0)
        self.assertIn("flipped == 0", L.failing(m, textured=False))

    def test_feet_off_the_ground_and_root_scale(self):
        m = L.lint(glb(self.tmp / "c.glb", lift=0.5, scale=[2, 2, 2]))
        self.assertEqual(sorted(L.failing(m, textured=False)), ["abs(min_y) <= 0.01 H", "root_scale == 1"])

    def test_texture_gates_wait_for_the_textured_model(self):
        m = L.lint(glb(self.tmp / "d.glb"))
        self.assertEqual(L.failing(m, textured=True), ["images == 1"])

    def test_committed_run_calibration(self):
        run = ROOT / "artifacts/model-sheets/runs/draft/n01X/hard-v1/model.glb"
        if not run.exists():
            self.skipTest("run not checked out")
        m = L.lint(run)
        self.assertEqual((m["tris"], m["flipped"], m["images"], m["uv_out_of_range"]), (620, 0, 1, 0))
        self.assertEqual(L.failing(m, textured=True), [])


class Status(unittest.TestCase):
    def test_four_levels(self):
        sm = {"approved": {"front": 0.80}, "gates": {"front": 0.85}}
        far = {"approved": {"front": 0.60}, "gates": {"front": 0.85}}
        for verdict, summary, bad, want in [
                ("SHAPE-PASS", sm, [], "prototype-safe"), ("PASS", sm, [], "final-use"),
                ("PASS", sm, ["flipped == 0"], "prototype-safe"), ("CHECK", far, [], "rejected"),
                ("CHECK", sm, [], "placeholder"), ("CHECK", {}, [], "placeholder")]:
            with self.subTest(verdict=verdict, bad=bad):
                self.assertEqual(SP.status_of(verdict, summary, bad), want)


if __name__ == "__main__":
    unittest.main()


class UvImage(unittest.TestCase):
    def test_no_uv_no_image_and_committed_atlas_has_overlap_tint(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        self.assertIsNone(L.uv_image(glb(tmp / "a.glb")))
        run = ROOT / "artifacts/model-sheets/runs/draft/n01X/hard-v1/model.glb"
        if not run.exists():
            self.skipTest("committed run absent")
        img = np.asarray(L.uv_image(run, scale=1))
        self.assertEqual(img.shape[2], 3)
        self.assertTrue(((img[..., 0] > 150) & (img[..., 1] < 80)).any())   # red = 2+ triangles
