"""python3.14 -m unittest discover -s tests/tools/blender"""
import json
import pathlib
import struct
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import deform_to_sheet as D  # noqa: E402
import mesh_lint as ML  # noqa: E402
import silhouette as S  # noqa: E402

# a 1 x 1 x 2 box (x, y depth, z up) on a 3-ring lattice: enough vertices for the contour to move
RING = [(x, y) for x, y in ((-.5, -.5), (0, -.5), (.5, -.5), (.5, 0), (.5, .5), (0, .5), (-.5, .5), (-.5, 0))]
LEVELS = (0.0, 1.0, 2.0)
POS = np.array([(x, y, z) for z in LEVELS for x, y in RING], float)


def tubes():
    """Triangles of the ring lattice's side walls, outward wound."""
    tri = []
    for lv in range(len(LEVELS) - 1):
        for i in range(8):
            a, b = lv * 8 + i, lv * 8 + (i + 1) % 8
            tri += [(a, b, b + 8), (a, b + 8, a + 8)]
    return np.array(tri)


TRI = tubes()


def panel(width, height=2.0):
    """The sheet panel of a box `width` wide, `height` tall: a normalised mask."""
    mask = np.zeros((512, 512), bool)
    w, h = int(width * 100), int(height * 100)
    mask[10:10 + h, 256 - w // 2:256 + w // 2] = True
    return S.normalize(mask)


def write_glb(path):
    """A one-primitive GLB of the lattice, welded twice (every vertex duplicated, as split normals do)."""
    pos = (np.vstack([POS, POS])[:, [0, 2, 1]] * [1, 1, -1]).astype("<f4")          # glTF axes: y up, z = -y
    nor = np.tile([0, 0, 1], (len(pos), 1)).astype("<f4")
    idx = np.vstack([TRI, TRI + len(POS)]).astype("<u2").ravel()
    blob = pos.tobytes() + nor.tobytes() + idx.tobytes()
    doc = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
           "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1}, "indices": 2}]}],
           "buffers": [{"byteLength": len(blob)}],
           "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": pos.nbytes},
                           {"buffer": 0, "byteOffset": pos.nbytes, "byteLength": nor.nbytes},
                           {"buffer": 0, "byteOffset": pos.nbytes * 2, "byteLength": idx.nbytes}],
           "accessors": [{"bufferView": 0, "componentType": 5126, "count": len(pos), "type": "VEC3",
                          "min": pos.min(0).tolist(), "max": pos.max(0).tolist()},
                         {"bufferView": 1, "componentType": 5126, "count": len(pos), "type": "VEC3"},
                         {"bufferView": 2, "componentType": 5123, "count": len(idx), "type": "SCALAR"}]}
    text = json.dumps(doc).encode()
    text += b" " * (-len(text) % 4)
    body = struct.pack("<II", len(blob), 0x004E4942) + blob
    head = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(text) + len(body))
    pathlib.Path(path).write_bytes(head + struct.pack("<II", len(text), 0x4E4F534A) + text + body)


class TestDeform(unittest.TestCase):
    def test_weld_and_frame(self):
        uniq, inv = D.weld(np.vstack([POS, POS]))
        self.assertEqual((len(uniq), len(inv)), (len(POS), 2 * len(POS)))
        view = D.View("front", np.array([1.0, 0, 0]), np.array([0, 0, 1.0]), 1, panel(1.0), True)
        mask = D.view_state(POS, TRI, view)[1]
        self.assertGreater(S.iou(mask, view.concept), 0.97)      # same bbox fit as silhouette.normalize

    def test_pull_toward_a_wider_panel(self):
        panels = {"front": panel(1.15), "left": panel(1.0), "back": panel(1.15)}
        new, rep = D.deform(POS, TRI, panels, ("front", "left", "back"))
        self.assertGreater(rep["steps"], 0)
        self.assertGreater(rep["after"]["front"]["iou"], rep["before"]["front"]["iou"] + 0.03)
        self.assertEqual(rep["turned"], 0)
        self.assertLessEqual(np.abs(new - POS).max(), 4 * D.STEP * 2.0 + 1e-9)       # 0.05 H a step, 4 rounds
        self.assertTrue(np.all(new[:8, 2] == 0))                                    # the sole stays on the ground

    def test_body_and_props_pull_to_their_own_outline(self):
        """a spear drawn beside the figure: the body's targets are off the spear, a prop's on it, a component
        that is in no prop's mask keeps the whole outline"""
        spear = np.zeros((S.CANVAS_H, S.CANVAS_W), bool)
        spear[20:200, 300:306] = True
        concept = panel(1.0) | spear
        view = D.View("front", np.array([1.0, 0, 0]), np.array([0, 0, 1.0]), 1, concept, True, {"spear": spear})
        xy, owner = np.array([[200.0, 100.0], [302.0, 100.0], [100.0, 100.0]]), np.array([0, 1, 2])
        self.assertEqual(D.target_keys(view, xy, owner, 0).tolist(), [0, -1, -1])      # default: a prop keeps the whole outline
        with mock.patch.object(D, "PROPS_OWN_MASK", True):
            self.assertEqual(D.target_keys(view, xy, owner, 0).tolist(), [0, 1, -1])
        self.assertLess(view.goal(0)[1][100, 250], 290)           # the body's nearest outline point is not the spear
        self.assertGreaterEqual(view.goal(1)[1][100, 250], 300)   # the spear's is
        self.assertEqual(D.target_keys(D.View("front", view.ru, view.rv, 1, concept, True), np.zeros((2, 2)), np.array([0, 1]), 0).tolist(),
                         [-1, -1])                                # no prop masks: unchanged

    def test_guard_view_refuses(self):
        # top (a guard here) wants a 1.0 footprint: the front pull may not make it worse than GUARD
        panels = {"front": panel(1.15), "top": panel(1.0, 1.0)}
        _, rep = D.deform(POS, TRI, panels, ("front",))
        self.assertGreaterEqual(rep["after"]["top"]["iou"], rep["before"]["top"]["iou"] - D.GUARD - 1e-9)

    def test_band_override(self):
        panels = {"front": panel(1.15)}
        new, _ = D.deform(POS, TRI, panels, ("front",), band=(0.9, 1.0))
        self.assertLess(np.abs(new[:16] - POS[:16]).max(), np.abs(new[16:] - POS[16:]).max())   # only the top ring

    def test_run_keeps_every_other_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = pathlib.Path(tmp, "a.glb"), pathlib.Path(tmp, "b.glb")
            write_glb(src)
            panels = {"front": panel(1.15), "left": panel(1.0), "back": panel(1.15)}
            with mock.patch.object(D, "sheet_panels", return_value=panels):
                rep = D.run(src, "unused.jpg", out)
            (ja, da), (jb, db) = ML.read_glb(src), ML.read_glb(out)
            self.assertGreater(rep["steps"], 0)
            self.assertEqual(da[2 * 2 * len(POS) * 12:], db[2 * 2 * len(POS) * 12:])      # indices after positions and normals
            pa, pb = (ML.accessor(j, d, 0) for j, d in ((ja, da), (jb, db)))
            self.assertEqual(len(pa), len(pb))
            self.assertFalse(np.allclose(pa, pb))
            self.assertTrue(np.allclose(pb[:len(POS)], pb[len(POS):]))               # the duplicates moved together
            self.assertTrue(np.allclose(jb["accessors"][0]["max"], pb.max(0), atol=1e-6))

    def test_rts_axes_are_fit_spec_project(self):
        """the gameplay camera projects like fit_spec.project (the proxy the fit ranks with) and a pinned cam is one candidate"""
        import fit_spec as F
        pts = np.random.default_rng(1).normal(size=(20, 3))
        for cam in ((35, -60), (65, 45)):
            ru, rv = D.rts_axes(cam)
            u, v = F.project("rts", pts, cam)
            self.assertTrue(np.allclose(pts @ ru, u) and np.allclose(pts @ rv, v))
        self.assertEqual(len(list(D.candidates("rts", panel(1.0)))), len(D.RTS))
        self.assertEqual(len(list(D.candidates("rts", panel(1.0), [35, -60]))), 1)
        self.assertEqual(len(list(D.candidates("top", panel(1.0), -30))), 2)

    def test_weights_and_rts_pull(self):
        """a view's weight scales its share of the mean IoU; an rts panel is pulled, never mirrored; no weight: plain mean"""
        views = [D.View("front", None, None, 1, None, True), D.View("rts", None, None, 1, None, True)]
        rep = {"front": {"iou": 0.5}, "rts": {"iou": 0.8}}
        self.assertAlmostEqual(D.mean_iou(rep, views), 0.65)
        self.assertAlmostEqual(D.mean_iou(rep, views, {"rts": 2.0}), 0.7)
        panels = {"front": panel(1.15), "rts": panel(1.15)}
        new, rep = D.deform(POS, TRI, panels, ("front", "rts"), cams={"rts": (45, 45)}, rig="spider")
        self.assertEqual((rep["mirrors"]["rts"], rep["weights"]["rts"]), (1, 2.0))
        self.assertGreaterEqual(rep["after"]["rts"]["iou"], rep["before"]["rts"]["iou"] - D.GUARD - 1e-9)

    def test_unlike_rts_is_only_watched(self):
        """an rts drawing that starts under PULL_MIN IoU (a sliver of a panel) does not pull; the ortographics still do"""
        _, rep = D.deform(POS, TRI, {"front": panel(1.15), "rts": panel(4.0, 0.3)}, ("front", "rts"), cams={"rts": (45, 45)})
        self.assertEqual(rep["pulled"], ["front"])

    def test_run_cams(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = SimpleNamespace(out=pathlib.Path(tmp))
            self.assertIsNone(D.run_cams(args))
            pathlib.Path(tmp, "silhouette.json").write_text(json.dumps({"tilt": {"top": -30, "rts": [65, 60]}}))
            self.assertEqual(D.run_cams(args), {"top": -30, "rts": (65, 60)})

    def test_apply_needs_both_switches(self):
        self.assertIsNone(D.apply("x.glb", SimpleNamespace(deform=True, union_body=False)))
        self.assertIsNone(D.apply("x.glb", SimpleNamespace(deform=False, union_body=True)))


if __name__ == "__main__":
    unittest.main()
