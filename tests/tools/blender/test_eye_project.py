"""L20-0: the sheet projected on the atlas (eye_project.py). All numpy: no Blender, no sheet on disk."""
import json
import pathlib
import struct
import sys
import tempfile
import unittest

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))
import eye_project as P  # noqa: E402
import hive_sheet as H  # noqa: E402

QUAD = np.array([[0, 1, 2], [0, 2, 3]])


class Colour(unittest.TestCase):
    def test_oklab_round_trip(self):
        for rgb in ([0, 0, 0], [255, 255, 255], [128, 64, 200], [12, 200, 90]):
            with self.subTest(rgb=rgb):
                self.assertTrue(np.allclose(P.from_oklab(P.to_oklab(np.array(rgb, float))), rgb, atol=0.5))

    def test_grow_shrink(self):
        m = np.zeros((9, 9), bool)
        m[3:6, 3:6] = True
        with self.subTest("grow"):
            self.assertEqual(P.grow(m).sum(), 21)
        with self.subTest("shrink"):
            self.assertEqual(P.shrink(m).sum(), 1)
        with self.subTest("the image's border is outside"):
            self.assertFalse(P.shrink(np.ones((5, 5), bool))[0].any())

    def test_albedo_and_remap(self):
        lit, shadow = np.array([0.7, 0.02, 0.03]), np.array([0.45, 0.02, 0.03])
        lab = np.r_[np.tile(lit, (70, 1)), np.tile(shadow, (30, 1))]
        with self.subTest("the lightest tone is the albedo"):
            self.assertTrue(np.allclose(P.albedo_of(lab), lit))
        with self.subTest("a small highlight is not"):
            spark = np.r_[lab, np.tile([0.95, 0.0, 0.0], (5, 1))]
            self.assertTrue(np.allclose(P.albedo_of(spark), lit, atol=1e-6))
        out = P.remap(lab, lit)
        with self.subTest("a shadow keeps a fifth of its distance"):
            self.assertAlmostEqual(out[-1, 0], 0.7 - 0.05)
        with self.subTest("the lit tone stays"):
            self.assertTrue(np.allclose(out[0], lit))

    def test_contour_keeps_a_line_and_not_a_dark_plate(self):
        rgb = np.full((40, 40, 3), 150.0)
        rgb[:, 18:21] = 5
        rgb[:, 30:] = 40
        line = P.contour_of(P.to_oklab(rgb))
        with self.subTest("the line"):
            self.assertTrue(line[:, 19].all())
        with self.subTest("the plate's inside"):
            self.assertFalse(line[:, 36].any())

    def test_fill_lines_takes_the_neighbours(self):
        rgb = np.full((5, 7, 3), 100.0)
        rgb[:, 3] = 0
        line = np.zeros((5, 7), bool)
        line[:, 3] = True
        self.assertTrue(np.allclose(P.fill_lines(rgb, line, np.ones((5, 7), bool)), 100.0))


class Camera(unittest.TestCase):
    def test_review_cameras(self):
        for view, right, up, back in (("front", (1, 0, 0), (0, 0, 1), (0, -1, 0)), ("left", (0, -1, 0), (0, 0, 1), (-1, 0, 0)), ("back", (-1, 0, 0), (0, 0, 1), (0, 1, 0)),
                                      ("right", (0, 1, 0), (0, 0, 1), (1, 0, 0)), ("top", (1, 0, 0), (0, 1, 0), (0, 0, 1)), ("bottom", (1, 0, 0), (0, -1, 0), (0, 0, -1))):
            with self.subTest(view):
                r, u, b = P.axes(view)
                self.assertTrue(np.allclose([r, u, b], [right, up, back], atol=1e-9))

    def test_zbuffer_keeps_the_nearest(self):
        far = np.array([[1, 1, 0], [9, 1, 0], [9, 9, 0], [1, 9, 0]], float)
        near = far + [0, 0, 2]
        z = P.zbuffer(np.r_[far, near], np.r_[QUAD, QUAD + 4], (10, 10))
        with self.subTest("nearest"):
            self.assertEqual(z[5, 5], 2)
        with self.subTest("empty"):
            self.assertTrue(np.isneginf(z[0, 0]))

    def test_register_finds_scale_and_shift(self):
        xy = np.array([[0, 0], [1, 0], [1, 2], [0, 2]], float)
        mask = np.zeros((300, 300), bool)
        mask[50:250, 70:170] = True
        sx, sy, tx, ty, iou = P.register(xy, QUAD, mask)
        with self.subTest("iou"):
            self.assertGreater(iou, 0.93)
        for name, got, want in (("left", tx, 70), ("right", sx + tx, 170), ("top", ty - 2 * sy, 50), ("bottom", ty, 250)):
            with self.subTest(name):
                self.assertLess(abs(got - want), 6)


class Mix(unittest.TestCase):
    def test_weight(self):
        for name, c, seen, want in (("head on", 1.0, True, 0.5), ("cos^4", 0.5, True, 0.03125), ("behind", 1.0, False, 0.0), ("under 75 degrees", 0.2, True, 0.0)):
            with self.subTest(name):
                self.assertAlmostEqual(float(P.weight_of(np.array([c]), np.array([seen]), 0.5)[0]), want)

    def test_blend_and_report(self):
        colours = np.array([[[100.0, 0, 0], [0, 0, 0], [0, 0, 0]], [[0, 100.0, 0], [50, 50, 50], [0, 0, 0]]])
        weights = np.array([[3.0, 0, 0], [1.0, 1.0, 0]])
        out, cov = P.blend(colours, weights)
        with self.subTest("mean"):
            self.assertTrue(np.allclose(out[0], [75, 25, 0]))
        with self.subTest("uncovered"):
            self.assertEqual(cov.tolist(), [True, True, False])
        rep = P.coverage(weights, ["front", "left"], np.array([True, True, False]))
        with self.subTest("coverage"):
            self.assertEqual((rep["seen_pct"]["left"], rep["uncovered_pct"], rep["hidden_pct"], rep["visible_uncovered_pct"]), (66.7, 33.3, 33.3, 0.0))
        with self.subTest("disagreement"):
            self.assertEqual(P.disagreement(colours, weights, ["front", "left"])["front+left"]["texels"], 1)

    def test_soft_normals_slide_over_an_edge(self):
        pos = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [2, 0, 1], [2, 1, 1]], float)
        tri = np.array([[0, 1, 2], [0, 2, 3], [1, 4, 5], [1, 5, 2]])
        n = P.soft_normals(pos, tri, np.array([0, 2]), pos[[1, 1]] + 1e-6)
        self.assertTrue(np.allclose(n[0], n[1], atol=1e-3))


class Gate(unittest.TestCase):
    def test_gate_keep(self):
        grey, skin, dark = [120.0, 124.0, 128.0], [235.0, 190.0, 160.0], [50.0, 53.0, 56.0]
        for mixed, l_max, want in ((skin, None, False), (dark, None, True), (dark, 0.1, False), ([125.0, 128.0, 131.0], 0.1, True)):
            with self.subTest(mixed=mixed, l_max=l_max):
                self.assertEqual(bool(P.gate_keep(np.array([mixed]), np.array([grey]), 0.04, l_max)[0]), want)


class Parts(unittest.TestCase):
    """L20-2: one colour per piece, accents untouched."""
    HELMET, SLEEVE, LENS = np.array([125.0, 131.0, 135.0]), np.array([132.0, 129.0, 96.0]), np.array([106.0, 30.0, 44.0])

    def test_nearest_piece_is_the_field_that_holds_the_point(self):
        box = lambda c: {"n": [[1, 0, 0], [-1, 0, 0]], "d": [c + 1, 1 - c], "slot": 0}      # noqa: E731  x in [c-1, c+1]
        pts = np.array([[0.2, 0, 0], [4.1, 0, 0], [2.0, 0, 0]])
        self.assertEqual(P.eye_paint.nearest_piece(pts, [box(0), box(4)]).tolist(), [0, 1, 0])

    def test_accents_by_colour_and_by_what_the_identity_says(self):
        pal = np.array([self.SLEEVE, self.HELMET, self.LENS, [50.0, 100.0, 180.0]])
        area = np.array([900.0, 500.0, 40.0, 30.0])
        with self.subTest("saturated over a neutral palette"):
            self.assertEqual(P.accents(pal, area, []).tolist(), [False, False, True, True])
        with self.subTest("the body colour is never an accent, said or not"):
            self.assertFalse(P.accents(pal, area, ["olive tunic"])[0])
        with self.subTest("a colour word lifts a modest chroma"):
            soft = np.array([self.HELMET, [150.0, 140.0, 100.0]])
            self.assertEqual(P.accents(soft, np.array([1.0, 1.0]), ["brass valve", "olive coat"]).tolist(), [False, True])

    def test_part_filter_one_colour_per_piece(self):
        n = 60
        piece = np.r_[np.zeros(20, int), np.ones(20, int), np.full(20, 2)]
        mixed = np.tile(self.HELMET, (n, 1))
        mixed[:4] = self.SLEEVE                                     # a stripe of another piece's colour on piece 0
        mixed[20:40] = [60.0, 60.0, 60.0]                           # piece 1 is dark in the sheet but a steel helmet in the DSL
        cov = np.ones(n, bool)
        cov[16:20] = False                                          # holes of piece 0
        out, painted, rep = P.part_filter(mixed, cov, piece, np.array([self.HELMET, self.HELMET, self.HELMET]), ["a", "b", "c"], 0.04, 0.2, 0.5)
        with self.subTest("a stripe and a hole take the dominant colour"):
            self.assertTrue(np.allclose(out[:20], self.HELMET, atol=1.0) and painted[:20].all())
        with self.subTest("a dominant far from the DSL colour keeps the paint"):
            self.assertFalse(painted[20:40].any())
        with self.subTest("the report"):
            self.assertEqual([(r["name"], r["painted"]) for r in rep], [("a", True), ("b", False), ("c", True)])

    def test_shield_drops_accent_pieces_and_their_colour_elsewhere(self):
        piece = np.array([0, 0, 1, 1])
        mixed = np.array([self.LENS, self.HELMET, self.LENS, self.HELMET])
        rgb = np.array([self.LENS, self.HELMET])
        kept = P.shield(np.ones(4, bool), mixed, piece, np.array([True, False]), rgb)
        self.assertEqual(kept.tolist(), [False, False, False, True])        # lens piece, then the lens colour on the other piece


class Stage(unittest.TestCase):
    def test_tight_without_fields_or_sheet_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(P.apply_stage(pathlib.Path(tmp) / "model.glb", "hfoo", "tight"), {})
            self.assertEqual(P.apply_stage(pathlib.Path(tmp) / "model.glb", "hfoo", "off"), {})


class Glb(unittest.TestCase):
    def test_swap_atlas_moves_what_follows(self):
        vec = np.arange(6, dtype="<f4").tobytes()
        blob = b"PNG1\0\0" + b"\0\0" + vec
        j = {"images": [{"bufferView": 0}], "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 6}, {"buffer": 0, "byteOffset": 8, "byteLength": len(vec)}],
             "accessors": [{"bufferView": 1, "count": 2, "componentType": 5126, "type": "VEC3"}], "buffers": [{"byteLength": len(blob)}]}
        head = json.dumps(j).encode()
        head += b" " * ((-len(head)) % 4)
        data = b"glTF" + struct.pack("<II", 2, 28 + len(head) + len(blob)) + struct.pack("<I", len(head)) + b"JSON" + head + struct.pack("<I", len(blob)) + b"BIN\0" + blob
        with tempfile.TemporaryDirectory() as tmp:
            glb = pathlib.Path(tmp) / "m.glb"
            glb.write_bytes(data)
            P.swap_atlas(glb, b"NEW-PNG-BYTES")
            j2, blob2 = H.read_glb(glb)
        view = j2["bufferViews"][0]
        with self.subTest("the image"):
            self.assertEqual(blob2[:view["byteLength"]], b"NEW-PNG-BYTES")
        with self.subTest("the accessor after it"):
            self.assertTrue(np.array_equal(H.accessor(j2, blob2, 0).ravel(), np.arange(6)))
        with self.subTest("alignment"):
            self.assertEqual(j2["bufferViews"][1]["byteOffset"] % 4, 0)


    def test_the_judge_tells_two_atlases_apart(self):
        import review_pair
        src = P.DRAFT / "hfoo/v19-default/model-body.glb"
        with tempfile.TemporaryDirectory() as tmp:
            a, b = pathlib.Path(tmp) / "a.glb", pathlib.Path(tmp) / "b.glb"
            a.write_bytes(src.read_bytes())
            b.write_bytes(src.read_bytes())
            same = review_pair.glb_fingerprint(a) == review_pair.glb_fingerprint(b)
            P.swap_atlas(b, b"another image")
            differ = review_pair.glb_fingerprint(a) != review_pair.glb_fingerprint(b)
        self.assertTrue(same and differ)


if __name__ == "__main__":
    unittest.main()
