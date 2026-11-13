"""L17-3: the painted atlas of the eye stage's pieces (eye_paint.py). The bake is numpy and needs no Blender."""
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))
import eye_paint as P
import eye_stage

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

    def test_uvs_are_in_the_atlas_and_islands_do_not_overlap(self):
        self.assertTrue(((self.uv >= 0) & (self.uv <= 1)).all())
        self.assertEqual(texel_overlap(self.uv), 0)

    def test_each_box_face_is_an_island_and_both_sides_of_an_edge_are_inked(self):
        self.assertEqual(self.info["islands"], 12)
        self.assertGreater(self.info["texels"], 0)

    def test_the_unpainted_atlas_is_not_black(self):
        self.assertGreater(self.img[~self.used].mean(), 20)


class Parts(unittest.TestCase):
    def test_box_charts_make_one_island_per_component_and_axis(self):          # L18-3
        a = np.linspace(0, 2 * np.pi, 13)[:-1]
        ring = np.stack([np.cos(a), np.sin(a)], axis=1)
        pos = np.vstack([np.c_[ring, np.zeros(12)], np.c_[ring, np.ones(12)]])
        tri = np.array([t for i in range(12) for t in ([i, (i + 1) % 12, 12 + i], [(i + 1) % 12, 12 + (i + 1) % 12, 12 + i])])
        for charts, islands in (("grow", None), ("box", 4)):
            with self.subTest(charts=charts):
                uv, _, _, _, isl, _, _ = P.unwrap(pos, tri, np.zeros(len(tri), int), charts)
                self.assertEqual(texel_overlap(uv), 0)               # a curved strip never folds
                if islands:
                    self.assertEqual(int(isl.max()) + 1, islands)          # one welded tube: +x, -x, +y, -y charts, no caps
        pos2, tri2, mat, colours = two_boxes()
        info = P.bake(pos2, tri2, mat, colours, charts="box")[3]
        self.assertEqual((info["islands"], info["charts"]), (12, "box"))      # two boxes apart: 2 components x 6 axes
        self.assertGreaterEqual(info["texels_per_island_median"], info["texels_per_island_min"])
        self.assertGreater(info["texels_per_island_median"], 100)

    def test_piece_fields_colour_texels_by_the_nearest_piece_and_ink_the_seam(self):     # L18-3
        pos, tri, mat, colours = two_boxes()
        fields = [{"slot": 1, "n": [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], "d": [1, 0, 1, 0, 1, 0]},    # the unit cube = slot 1
                  {"slot": 0, "n": [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], "d": [1, 0, 1, 0, 2, -1]}]   # above it = slot 0
        slots = P.texel_slots(np.array([[0.5, 0.5, 0.5], [0.5, 0.5, 1.5], [0.5, 0.5, 0.99]]), fields)
        self.assertEqual(slots.tolist(), [1, 0, 1])
        mask = np.ones((4, 4), bool)
        mid = np.array([[0, 0, 1, 1]] * 4)
        line = P.border_ink(mask, mid, np.zeros((4, 4), int))
        self.assertEqual(line.sum(), 4)                                     # one column, on the higher slot's side of the seam
        self.assertEqual(P.border_ink(mask, mid, np.array([[0, 0, 1, 1]] * 4)).sum(), 0)   # another island across the seam: no line
        info = P.bake(pos, tri, mat, colours, charts="box", fields=fields)[3]   # all triangles are one material per box: same picture, no crash
        self.assertEqual(info["islands"], 12)
        with tempfile.TemporaryDirectory() as tmp:
            f = pathlib.Path(tmp) / "fields.json"
            f.write_text('{"materials": ["coat", "skin"], "pieces": [{"slot": 1, "n": [[0, 0, 1]], "d": [1]}]}')
            self.assertEqual(P.read_fields(f, ["skin.001", "coat"])[0]["slot"], 0)
            self.assertIsNone(P.read_fields(f, ["skin"]))
            self.assertIsNone(P.read_fields(pathlib.Path(tmp) / "none.json", []))

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
            self.assertEqual(P.apply_stage("x.glb", "box"), {"islands": 1})
        self.assertEqual([c.args[1] for c in apply.call_args_list], ["grow", "box"])


class BestRound(unittest.TestCase):
    """eye_stage.best_round: no disaster, then most parts, then the latest; a stop entry has no tris."""
    def test_choice(self):
        r = lambda n, k, disaster=(): {"round": n, "tris": 600, "parts": [k, 35], "disaster": list(disaster)}
        for rounds, want in (([r(0, 21), r(1, 21), r(2, 18), r(3, 18)], 1),
                             ([r(0, 30, ["front"]), r(1, 18)], 1),
                             ([r(0, 18), {"round": 1, "stop": True}], 0)):
            with self.subTest(want=want):
                self.assertEqual(eye_stage.best_round(rounds), want)


class Contour(unittest.TestCase):
    """eye_stage.finish: the hull only for hull and both; ink and off add none."""
    def finish(self, contour):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp)
            (out / "eye/round-0").mkdir(parents=True)
            (out / "eye/round-0/model.glb").write_bytes(b"glb")
            (out / "eye/round-0/dsl.json").write_text('{"pieces": [], "colours": {}}')
            summary = {"rounds": [{"round": 0, "tris": 1, "parts": [1, 1], "disaster": []}], "unit": "u", "from": "s", "llm_calls": 0, "resends": 0}
            with mock.patch.object(eye_stage, "build"), mock.patch.object(eye_stage, "vertex_hash", return_value="h"), mock.patch.object(eye_stage, "stretch_of", return_value={}), \
                    mock.patch.object(eye_stage.eye_skin, "apply_stage", return_value={}), mock.patch.object(eye_stage.eye_paint, "apply_stage", return_value={}) as paint, \
                    mock.patch.object(eye_stage.outline, "apply", return_value=True) as hull:
                eye_stage.finish(summary, out / "x", None, out, out / "eye", paint="on", contour=contour)
        return hull.call_count, paint.call_count

    def test_hull_modes(self):
        self.assertEqual([self.finish(c) for c in ("hull", "both", "ink", "off")], [(1, 1), (1, 1), (0, 1), (0, 1)])


if __name__ == "__main__":
    unittest.main()
