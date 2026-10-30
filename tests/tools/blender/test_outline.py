import pathlib
import sys
import tempfile
import unittest

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))
import colour_stage as CS  # noqa: E402
import outline as O  # noqa: E402

# a tetrahedron whose corner 0 is split in two vertices (a hard edge): vertices 0 and 4 share a position
POS = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 0, 0.0]])
TRI = np.array([[0, 2, 1], [0, 1, 3], [4, 3, 2], [1, 2, 3]])


def normals(pos, tri):
    return np.cross(pos[tri[:, 1]] - pos[tri[:, 0]], pos[tri[:, 2]] - pos[tri[:, 0]])


class Hull(unittest.TestCase):
    def test_same_faces_reversed_winding_and_pushed_out(self):
        pos, tri = O.hull_mesh(POS, TRI, 0.1)
        self.assertEqual(len(tri), len(TRI))
        flipped = normals(POS, TRI)
        self.assertTrue(np.allclose(normals(POS, tri), -flipped))             # every face now looks the other way
        self.assertGreater(np.linalg.norm(pos - POS.mean(0), axis=1).min(), np.linalg.norm(POS - POS.mean(0), axis=1).min() - 1e-9)

    def test_split_vertices_move_together(self):
        pos, _ = O.hull_mesh(POS, TRI, 0.1)
        self.assertTrue(np.allclose(pos[0], pos[4]))
        self.assertAlmostEqual(float(np.linalg.norm(pos[1] - POS[1])), 0.1, places=6)


class Face(unittest.TestCase):
    def test_cut_keeps_at_least_128_px(self):
        sheet = ROOT / "artifacts/model-sheets/refs/n02X/sheet.jpg"
        spec = {"parts": [["head", "box", [1, 1, 1], [0, 0, 0], "skin", {"decal": "sheet"}]]}
        args = type("A", (), {"face": "decal", "sheet": sheet})()
        with tempfile.TemporaryDirectory() as t:
            from PIL import Image
            with Image.open(CS.face_quad(spec, args, pathlib.Path(t))) as im:
                self.assertGreaterEqual(min(im.size), 128)
            self.assertIsNone(CS.face_quad(spec, type("A", (), {"face": "off", "sheet": sheet})(), pathlib.Path(t)))


class Contrast(unittest.TestCase):
    def test_the_darker_of_two_close_slots_goes_x08_and_far_ones_stay(self):
        spec = {"palette": {"a": {"color": "#808080"}, "b": {"color": "#828282"}, "c": {"color": "#202020"}}}
        out = CS.zone_contrast(spec)
        self.assertEqual(out["palette"]["a"]["color"], "#666666")
        self.assertEqual((out["palette"]["b"]["color"], out["palette"]["c"]["color"]), ("#828282", "#202020"))
        self.assertEqual(spec["palette"]["a"]["color"], "#808080")


if __name__ == "__main__":
    unittest.main()
