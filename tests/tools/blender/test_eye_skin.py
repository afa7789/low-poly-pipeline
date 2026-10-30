"""L16-4: the skin at the joints (eye_skin.py). The numpy helpers need no Blender; the Blender cases build two tubes on the n005 rig."""
import pathlib
import shutil
import sys
import tempfile
import unittest

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))
import eye_skin as K  # noqa: E402
import mesh_lint  # noqa: E402

RUN = ROOT / "artifacts/model-sheets/runs/draft/n005/v15-r1"
BLENDER = bool(shutil.which("blender")) and (RUN / "model.glb").exists()
CUBE = np.array([(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)], float)
CUBE_FACES = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
L_JOINT = {"colours": {"a": "884422", "b": "224488"}, "pieces": [
    {"op": "between", "name": "up", "mat": "a", "bone": "spine", "role": "arm", "a": [0, 0, 1.0], "b": [0, 0, 1.6], "r0": 0.1, "r1": 0.1},
    {"op": "between", "name": "side", "mat": "b", "bone": "spine", "role": "arm", "a": [0, 0, 1.55], "b": [0.6, 0, 1.55], "r0": 0.1, "r1": 0.1}]}


def piece(verts, faces, bone="spine", role="arm"):
    return {"bone": bone, "verts": verts, "faces": faces, "planes": K.face_planes(verts, faces), "samples": K.samples_of(verts, faces),
            "lo": verts.min(0), "hi": verts.max(0), "area": 6.0, "p": {"role": role}}


class Pure(unittest.TestCase):
    def test_convex_distance_is_negative_inside_and_exact_at_a_face(self):
        planes = K.face_planes(CUBE, CUBE_FACES)
        d = K.convex_d(planes, np.array([[0.5, 0.5, 0.5], [0.5, 0.5, 2.0], [0.5, 0.5, 1.0]]))
        np.testing.assert_allclose(d, [-0.5, 1.0, 0.0], atol=1e-9)

    def test_joints_need_related_bones_and_nearness(self):
        a, b, far = piece(CUBE, CUBE_FACES), piece(CUBE + [0.9, 0, 0], CUBE_FACES, "arm.L"), piece(CUBE + [9, 0, 0], CUBE_FACES)
        parents = {"arm.L": "spine"}
        self.assertEqual([(j["a"], j["b"]) for j in K.find_joints([a, b, far], parents, 1.0)], [(0, 1)])
        self.assertEqual(K.find_joints([a, b], {}, 1.0), [])          # unrelated bones: no joint
        self.assertLessEqual(K.find_joints([a, b], parents, 1.0)[0]["gap"], 0)   # overlapping: not positive

    def test_ranking_puts_articulations_and_limbs_first(self):
        pcs = [piece(CUBE, CUBE_FACES, "spine", "torso"), piece(CUBE, CUBE_FACES, "spine", "prop"), piece(CUBE, CUBE_FACES, "arm.L", "arm")]
        joints = [{"a": 0, "b": 1}, {"a": 0, "b": 2}]
        self.assertEqual(K.rank_joints(joints, pcs)[0], {"a": 0, "b": 2})

    def test_smooth_min_only_adds_material_and_weights_split_between_bones(self):
        a, b = np.array([0.0, 0.1, 1.0]), np.array([0.0, 0.1, 1.0])
        self.assertTrue((K.smin(a, b, 0.2) <= np.minimum(a, b)).all())
        np.testing.assert_allclose(K.weight_toward_a(np.array([0.0, 1.0, 0.5]), np.array([1.0, 0.0, 0.5]), 0.1), [1.0, 0.0, 0.5])

    def test_hidden_faces_and_crop_keep_to_the_sphere(self):
        self.assertEqual(K.hidden_faces(CUBE, CUBE_FACES, np.array([0.5, 0.5, 0.5]), 2.0), list(range(6)))
        self.assertEqual(K.hidden_faces(CUBE, CUBE_FACES, np.array([9.0, 0, 0]), 2.0), [])
        v, t = K.crop(CUBE, np.array([[0, 1, 2], [5, 6, 7]]), np.zeros(3), 1.0)
        self.assertEqual(len(t), 1)

    def test_sleeve_is_three_rings_whose_weights_run_from_a_to_b(self):
        a, b = piece(CUBE, CUBE_FACES), piece(CUBE + [1.5, 0, 0], CUBE_FACES)
        ring, share = K.sleeve_rings(a, b, {"centre": [1.25, 0.5, 0.5]}, 2.0)
        self.assertEqual((ring.shape, sorted(set(share))), ((3 * K.SIDES, 3), [0.0, 0.5, 1.0]))

    def test_buried_faces_only_inside_a_piece_of_the_same_bone(self):
        big, small = piece(CUBE * 4, CUBE_FACES), piece(CUBE + 1.0, CUBE_FACES)
        self.assertEqual(len(K.buried_faces([big, small], 1, 0.01)), 6)
        small["bone"] = "arm.L"
        self.assertEqual(K.buried_faces([big, small], 1, 0.01), [])


@unittest.skipUnless(BLENDER, "needs blender and the n005 v15 run")
class InBlender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp())
        cls.addClassCleanup(shutil.rmtree, cls.tmp)

    def build(self, technique):
        out = self.tmp / f"{technique}.glb"
        return K.skin_build(RUN / "model.glb", L_JOINT, out, technique), out

    def test_off_is_eye_libs_build(self):
        info, out = self.build("off")
        self.assertEqual((info["tris"], info["components"]), (K.EL.tris_of(L_JOINT["pieces"][0]) * 2, 2))

    def test_bridge_closes_two_tubes_at_90_degrees_in_budget(self):
        info, out = self.build("bridge")
        lint = mesh_lint.lint(out)
        self.assertEqual((info["skins"], info["components"], lint["nonmanifold_edges"], lint["boundary_edges"]), (1, 1, 0, 0))
        self.assertLess(info["tris"], K.EL.BUDGET)

    def test_blend_leaves_vertices_outside_its_radius_alone(self):
        base, out0 = self.build("off")
        info, out1 = self.build("blend")
        self.assertGreaterEqual(info["skins"], 1)
        c = np.array(info["joints"][0]["centre"])
        c_gl = np.array([c[0], c[2], -c[1]])
        pos = lambda g: np.round(mesh_lint.geometry(*mesh_lint.read_glb(g))[0], 4)  # noqa: E731
        before, after = pos(out0), {tuple(p) for p in pos(out1)}
        far = [p for p in before if np.linalg.norm(p - c_gl) > info["joints"][0]["radius"] * K.SPREAD + 1e-3]
        self.assertTrue(far)
        self.assertTrue(all(tuple(p) in after for p in far))

    def test_wrap_weights_sum_to_one(self):
        info, out = self.build("wrap")
        doc, blob = mesh_lint.read_glb(out)
        prim = doc["meshes"][0]["primitives"][0]["attributes"]
        w = mesh_lint.accessor(doc, blob, prim["WEIGHTS_0"])
        self.assertEqual(info["skins"], 1)
        np.testing.assert_allclose(w.sum(1), 1.0, atol=1e-3)

    def test_weld_adds_no_geometry(self):
        info, _ = self.build("weld")
        self.assertLessEqual(info["tris"], info["tris_pieces"])


if __name__ == "__main__":
    unittest.main()
