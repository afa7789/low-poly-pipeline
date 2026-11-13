"""L16-4: the skin at the joints (eye_skin.py). The numpy helpers need no Blender."""
import pathlib
import sys
import unittest

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))
import eye_skin as K

CUBE = np.array([(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)], float)
CUBE_FACES = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
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
        _v, t = K.crop(CUBE, np.array([[0, 1, 2], [5, 6, 7]]), np.zeros(3), 1.0)
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


if __name__ == "__main__":
    unittest.main()
