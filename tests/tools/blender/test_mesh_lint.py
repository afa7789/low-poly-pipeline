"""python3.14 -m unittest discover -s tests/tools/blender"""
import json
import pathlib
import struct
import sys
import tempfile
import unittest
from unittest import mock

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

    def test_form_of_a_cube(self):
        """12 box edges at 90 degrees, 6 diagonals at 0; the inner angles are 45/45/90"""
        m = L.lint(glb(self.tmp / "a.glb"))
        self.assertEqual(m["normal_diff"], {"mean": 60.0, "p90": 90.0, "hist": [33.3, 0.0, 0.0, 0.0, 66.7, 0.0]})
        self.assertEqual((m["fairness"], m["components_body"]), (20.0, 1))

    def test_shape_against_an_exact_box_sdf(self):
        """PIPELINE 28.L10-6: cube on its own SDF is exact; a pulled corner is not; an open shell has an Euler defect"""
        def box(q):
            e = np.abs(q - 0.5) - 0.5
            return np.linalg.norm(np.maximum(e, 0), axis=1) + np.minimum(e.max(1), 0)
        pos, tri = np.array(CUBE, float), np.array(TRIS)
        m = L.shape_report(pos, tri, box, 1 / 96)
        self.assertLess(m["sdf_dev"]["pct_h"]["max"], 1e-6)
        self.assertAlmostEqual(m["normal_consistency"], 1.0, places=3)
        self.assertEqual((m["euler"], m["euler_components"], m["nd_bands"]), (0, [0], [33.3, 0.0, 66.7, 0.0]))
        pos[7] += 0.2
        self.assertGreater(L.shape_report(pos, tri, box, 1 / 96)["sdf_dev"]["pct_h"]["p95"], 1)
        hole = L.shape_report(np.array(CUBE, float), tri[:-2])
        self.assertEqual(hole["euler"], -2)
        self.assertIsNone(hole["sdf_dev"])

    def test_no_field_beside_the_glb_leaves_the_sdf_metrics_empty(self):
        m = L.lint(glb(self.tmp / "e.glb"), sdf=True)
        self.assertEqual((m["sdf_dev"], m["hausdorff_sdf"], m["normal_consistency"], m["euler"]), (None, None, None, 0))

    def test_props_are_not_body_components(self):
        pos = np.vstack([np.array(CUBE, float), np.array(CUBE, float) + 5])
        tri = np.array(TRIS + [(a + 8, b + 8, c + 8) for a, b, c in TRIS])
        none = np.zeros(len(tri), bool)
        by_material = none.copy()
        by_material[12:] = True
        for name, flagged, props, want in (("two boxes", none, 0, 2), ("attach.json lists one prop", none, 1, 1),
                                           ("prop_* material", by_material, 0, 1), ("never below one", none, 5, 1)):
            with self.subTest(name):
                self.assertEqual(L.body_components(pos, tri, flagged, props), want)

    def test_components_body_reads_the_build_report(self):
        g = glb(self.tmp / "clay.glb")
        self.assertEqual(L.lint(g)["components_body"], 1)               # no attach.json: every component counts
        (self.tmp / "attach.json").write_text('{"union": {"components_body": 3}}')
        m = L.lint(g)
        self.assertEqual((m["components"], m["components_body"]), (1, 3))
        self.assertEqual(L.failing(m, textured=False), ["components_body == 1"])

    def test_committed_run_calibration(self):
        run = ROOT / "artifacts/model-sheets/runs/draft/n01X/hard-v1/model.glb"
        if not run.exists():
            self.skipTest("run not checked out")
        m = L.lint(run)
        self.assertEqual((m["tris"], m["flipped"], m["images"], m["uv_out_of_range"]), (620, 0, 1, 0))
        # the union (L6-4) is not integrated yet: 32 boxes, so only the body gate fails (PIPELINE 24.L6-6)
        self.assertEqual(L.failing(m, textured=True), ["components_body == 1"])
        self.assertEqual((m["components"], m["components_body"]), (32, 32))
        self.assertAlmostEqual(m["normal_diff"]["mean"], 48.64, 1)


class MirrorOverlap(unittest.TestCase):
    """Knodt & Gao 2025 symmetric overlap: .L/.R twins on the same texels (PIPELINE 27.T4)."""
    UV = np.array([[.1, .9], [.2, .9], [.1, .8]] * 2)       # two identical triangles in cell 0
    TRI = np.array([[0, 1, 2], [3, 4, 5]])

    def test_twins_share_texels(self):
        self.assertEqual(L.raster_uv(self.UV, self.TRI, 64, 1, 1)[0], 100.0)
        self.assertEqual(L.mirror_overlap_pct(self.UV, self.TRI, ["arm.L", "arm.R"], 64, 1, 1), 100.0)

    def test_same_side_overlap_is_not_mirror(self):
        self.assertEqual(L.mirror_overlap_pct(self.UV, self.TRI, ["arm.L", "forearm.L"], 64, 1, 1), 0.0)

    def test_no_skin_no_report(self):
        self.assertIsNone(L.mirror_overlap_pct(self.UV, self.TRI, [None, None], 64, 1, 1))

    def test_twin_bones_share_an_atlas_slot(self):
        """build_unit imports bpy: read TEX_SLOTS from its source."""
        import ast
        tree = ast.parse((ROOT / "tools/blender/build_unit.py").read_text())
        slots = next(ast.literal_eval(n.value) for n in tree.body
                     if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "TEX_SLOTS")
        twins = [b for b in slots if b.endswith(".L")]
        self.assertTrue(twins)
        for left in twins:
            self.assertEqual(slots[left], slots[left[:-2] + ".R"], left)


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


class Protocol(unittest.TestCase):
    """PIPELINE §20: atlas KB / texel per height, the engine import line, the 3D Chamfer."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def test_no_atlas_no_kb_and_committed_atlas_has_kb(self):
        m = L.lint(glb(self.tmp / "a.glb"))
        self.assertEqual((m["atlas_kb"], m["texel_per_height"]), (None, None))
        run = ROOT / "artifacts/model-sheets/runs/draft/n01X/hard-v1/model.glb"
        if run.exists():
            m = L.lint(run)
            self.assertGreater(m["atlas_kb"], 0)
            self.assertGreater(m["texel_per_height"], 0)

    def test_engine_import_lines(self):
        fake = self.tmp / "fake.sh"
        fake.write_text("#!/bin/sh\nprintf '%s\\t%s\\n' \"$1\" \"$FAKE_LINE\"\n")
        fake.chmod(0o755)
        for line in ("ok meshes=1 verts=8 anims=0", "error FILEIO: Failed to open file"):
            with self.subTest(line=line), mock.patch.dict("os.environ", {"GLB_IMPORT_CHECK": str(fake), "FAKE_LINE": line}):
                self.assertEqual(L.engine_import(self.tmp / "x.glb"), line)
        with mock.patch.object(L, "import_binary", return_value=None):
            self.assertTrue(L.engine_import(self.tmp / "x.glb").startswith("n/a"))

    def test_chamfer_3d(self):
        try:
            import compare_runs as CR
        except ImportError:
            self.skipTest("Pillow missing")
        a = glb(self.tmp / "a.glb")
        same, height = CR.chamfer_3d(a, a)
        self.assertEqual(height, 1.0)
        self.assertLess(same, 0.02)        # two samplings of one surface
        self.assertGreater(CR.chamfer_3d(a, glb(self.tmp / "b.glb", lift=0.5))[0], 0.1)


class MipBleed(unittest.TestCase):
    def test_aligned_cells_do_not_mix(self):
        self.assertEqual(L.mip_bleed((64, 32), [(0, 0, 32, 16), (32, 0, 16, 16)]), {"1/2": 0, "1/4": 0, "1/8": 0})

    def test_cells_off_the_grid_mix_and_padding_cures_it(self):
        bad = L.mip_bleed((64, 32), [(0, 0, 30, 16), (30, 0, 16, 16)])
        self.assertEqual((bad["1/2"], bad["1/4"], bad["1/8"]), (0, 4, 2))
        self.assertEqual(L.mip_bleed(np.zeros((32, 64, 3)), [(0, 0, 30, 16), (32, 0, 16, 16)]),
                         {"1/2": 0, "1/4": 0, "1/8": 0})             # a 2 px gutter: nothing mixes


if __name__ == "__main__":
    unittest.main()
