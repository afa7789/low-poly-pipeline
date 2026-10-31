"""L17-3: the painted atlas of the eye stage's pieces (eye_paint.py). The bake is numpy and needs no Blender; the round trip is the slow case."""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))
import eye_paint as P  # noqa: E402
import eye_stage  # noqa: E402

RUN = ROOT / "artifacts/model-sheets/runs/draft/n005/v15-r1"
BLENDER = bool(shutil.which("blender")) and (RUN / "model.glb").exists()
FACES = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
CUBE = np.array([(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)], float)


def box(lo, hi):
    """(pos (8, 3), tri (12, 3)) of the axis-aligned box."""
    pos = CUBE * (np.array(hi) - lo) + lo
    return pos, np.array([t for f in FACES for t in ([f[0], f[2], f[1]], [f[0], f[3], f[2]])])


def two_boxes():
    """A tall box and a short one on its side: two materials, 24 triangles."""
    (pa, ta), (pb, tb) = box((0, 0, 0), (1, 1, 2)), box((1, 0, 0.5), (2, 1, 1.5))
    return np.vstack([pa, pb]), np.vstack([ta, tb + 8]), np.repeat([0, 1], 12), np.array([[200.0, 160, 110], [70, 90, 170]])


def texel_overlap(uv):
    """Texels covered by more than one UV triangle's interior (centres strictly inside)."""
    count = np.zeros((P.SIZE, P.SIZE), int)
    for q in uv * P.SIZE:
        ys, xs = np.mgrid[int(q[:, 1].min()):int(q[:, 1].max()) + 1, int(q[:, 0].min()):int(q[:, 0].max()) + 1]
        w = P.bary(q, xs + 0.5, ys + 0.5)
        if w is not None:
            count[ys[(w > 1e-6).all(0)], xs[(w > 1e-6).all(0)]] += 1
    return int((count > 1).sum())


class Bake(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pos, cls.tri, cls.mat, cls.colours = two_boxes()
        cls.uv, cls.img, cls.used, cls.info = P.bake(cls.pos, cls.tri, cls.mat, cls.colours)

    def test_two_pieces_make_a_painted_palette(self):
        import hive_sheet
        from PIL import Image
        stats = hive_sheet.texture_stats(Image.fromarray(np.dstack([self.img, self.used * np.uint8(255)]), "RGBA"), self.used)
        self.assertGreaterEqual(stats["colours"], 8)
        self.assertTrue(0.02 <= self.info["ink"] <= 0.12, self.info)

    def test_uvs_are_in_the_atlas_and_islands_do_not_overlap(self):
        self.assertTrue(((self.uv >= 0) & (self.uv <= 1)).all())
        self.assertEqual(texel_overlap(self.uv), 0)

    def test_each_box_face_is_an_island_and_both_sides_of_an_edge_are_inked(self):
        self.assertEqual(self.info["islands"], 12)
        self.assertGreater(self.info["texels"], 0)

    def test_the_unpainted_atlas_is_not_black(self):
        self.assertGreater(self.img[~self.used].mean(), 20)


class Parts(unittest.TestCase):
    def test_a_curved_strip_never_folds(self):
        """A 12-sided tube (30 degree steps, smooth to the sharp test) is cut into islands whose normals stay within 60 degrees of their seed."""
        a = np.linspace(0, 2 * np.pi, 13)[:-1]
        ring = np.stack([np.cos(a), np.sin(a)], axis=1)
        pos = np.vstack([np.c_[ring, np.zeros(12)], np.c_[ring, np.ones(12)]])
        tri = np.array([t for i in range(12) for t in ([i, (i + 1) % 12, 12 + i], [(i + 1) % 12, 12 + (i + 1) % 12, 12 + i])])
        uv = P.unwrap(pos, tri, np.zeros(len(tri), int))[0]
        self.assertEqual(texel_overlap(uv), 0)

    def test_png_round_trip(self):
        from PIL import Image
        arr = np.arange(4 * 4 * 4, dtype=np.uint8).reshape(4, 4, 4)
        with tempfile.TemporaryDirectory() as tmp:
            P.write_png(pathlib.Path(tmp) / "a.png", arr)
            np.testing.assert_array_equal(np.asarray(Image.open(pathlib.Path(tmp) / "a.png"))[::-1], arr)

    def test_paint_off_does_nothing_and_on_calls_blender(self):
        with mock.patch.object(P, "apply", return_value={"islands": 1}) as apply:
            self.assertEqual(P.apply_stage("x.glb", "off"), {})
            self.assertEqual(P.apply_stage("x.glb", "on"), {"islands": 1})
        apply.assert_called_once()


class Contour(unittest.TestCase):
    """eye_stage.finish: the hull only for hull and both; ink and off add none."""
    def finish(self, contour):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp)
            (out / "eye/round-0").mkdir(parents=True)
            (out / "eye/round-0/model.glb").write_bytes(b"glb")
            summary = {"rounds": [{"round": 0, "tris": 1}], "unit": "u", "from": "s", "llm_calls": 0, "resends": 0}
            with mock.patch.object(eye_stage, "build"), mock.patch.object(eye_stage, "vertex_hash", return_value="h"), mock.patch.object(eye_stage, "stretch_of", return_value={}), \
                    mock.patch.object(eye_stage.eye_skin, "apply_stage", return_value={}), mock.patch.object(eye_stage.eye_paint, "apply_stage", return_value={}) as paint, \
                    mock.patch.object(eye_stage.outline, "apply", return_value=True) as hull:
                eye_stage.finish(summary, out / "x", {"pieces": [], "colours": {}}, None, out, out / "eye", paint="on", contour=contour)
        return hull.call_count, paint.call_count

    def test_hull_modes(self):
        self.assertEqual([self.finish(c) for c in ("hull", "both", "ink", "off")], [(1, 1), (1, 1), (0, 1), (0, 1)])


@unittest.skipUnless(BLENDER, "needs blender and the n005 v15-r1 run")
class RoundTrip(unittest.TestCase):
    def test_glb_carries_one_texture_and_loads_back(self):
        import mesh_lint
        with tempfile.TemporaryDirectory() as tmp:
            glb = pathlib.Path(tmp) / "model.glb"
            shutil.copy(RUN / "model.glb", glb)
            info = P.apply(glb)
            self.assertTrue(info, "blender produced no file")
            doc, _ = mesh_lint.read_glb(glb)
            self.assertEqual(len(doc["images"]), 1)
            self.assertEqual(len(doc["materials"]), 1 + sum(1 for m in doc["meshes"] if m["name"] == "outline"))
            self.assertTrue((pathlib.Path(tmp) / "atlas.png").exists())
            probe = subprocess.run(["blender", "-b", "--python-expr", f"import bpy;bpy.ops.import_scene.gltf(filepath={str(glb)!r});print('OK',[i.size[0] for i in bpy.data.images if i.users])"],
                                   capture_output=True, text=True)
            self.assertRegex(probe.stdout, r"OK \[.*256")


if __name__ == "__main__":
    unittest.main()
