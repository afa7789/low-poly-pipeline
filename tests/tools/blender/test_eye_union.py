"""L17-2: union by material (eye_union.py). Numpy only: the pieces are convex prisms built here, no Blender."""
import pathlib
import sys
import unittest

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))
import eye_skin as K  # noqa: E402
import eye_union as U  # noqa: E402


def prism(a, b, r, sides=8):
    a, b = np.array(a, float), np.array(b, float)
    u = (b - a) / np.linalg.norm(b - a)
    e1 = np.cross(u, [0, 0, 1.0] if abs(u[2]) < 0.9 else [1.0, 0, 0])
    e1 /= np.linalg.norm(e1)
    t = 2 * np.pi * np.arange(sides) / sides
    ring = r * (np.cos(t)[:, None] * e1 + np.sin(t)[:, None] * np.cross(u, e1))
    faces = [[i, (i + 1) % sides, sides + (i + 1) % sides, sides + i] for i in range(sides)] + [list(range(sides)), list(range(sides, 2 * sides))]
    return np.vstack([a + ring, b + ring]), faces


def piece(a, b, r, bone="a", mat="m", role="arm"):
    v, f = prism(a, b, r)
    return {"p": {"role": role, "mat": mat, "op": "between"}, "bone": bone, "slot": 0 if mat == "m" else 1, "verts": v, "faces": f,
            "planes": K.face_planes(v, f), "samples": K.samples_of(v, f), "lo": v.min(0), "hi": v.max(0), "area": 1.0}


def parts():
    return [piece((0, 0, 0), (0, 0, 0.6), 0.08), piece((0, 0, 0.55), (0.5, 0, 0.6), 0.08, "b"), piece((0, 0, -0.05), (0, 0, 0.05), 0.12),
            piece((2, 0, 0), (2, 0, 0.5), 0.08, "a", "other"), piece((0.3, 0, 0.1), (0.3, 0, 0.3), 0.05, "a", "m", "prop")]


def comps(tris):
    root = U.union_find(int(tris.max()) + 1, [(t[i], t[(i + 1) % 3]) for t in tris for i in range(3)])
    return len({root[v] for t in tris for v in t})


class Union(unittest.TestCase):
    def test_two_tubes_and_a_disc_of_one_material_are_one_component_under_budget(self):
        ps = parts()[:3]
        verts, tris = U.union_mesh(ps, 1.0, 80)
        self.assertEqual(comps(tris), 1)
        self.assertLessEqual(len(tris), 80)
        edges = {}
        for t in tris:
            for i in range(3):
                e = tuple(sorted((t[i], t[(i + 1) % 3])))
                edges[e] = edges.get(e, 0) + 1
        self.assertEqual({n for n in edges.values()}, {2})          # closed and manifold

    def test_the_cvt_reducer_lands_near_the_budget_and_the_technique_names_it(self):     # L18-2b
        verts, tris = U.union_mesh(parts()[:3], 1.0, 80, reducer="cvt")
        self.assertEqual(comps(tris), 1)
        self.assertLessEqual(len(tris), 96)                          # the dual lands within a few % of the budget (no per-collapse guard)
        self.assertEqual(U.parse_technique("union-bone@cvt"), ("bone", "cvt"))
        self.assertEqual(U.parse_technique("union-material"), ("material", "qem"))
        self.assertEqual((U.technique_of("bone"), U.technique_of("bone", "cvt")), ("union-bone", "union-bone@cvt"))

    def test_a_cluster_the_cvt_cannot_dual_keeps_its_pieces_when_the_qem_overshoots(self):     # L19-0: the 700 budget holds with the CVT
        from unittest import mock
        ps = parts()[:2]
        own = sum(len(f) - 2 for m in ps for f in m["faces"])
        big = (np.zeros((own + 10, 3)), np.array([[0, 1, 2]] * (own + 9)), {})
        with mock.patch.object(U.retopo, "cvt", side_effect=ValueError("empty dual")), mock.patch.object(U.retopo, "reduce", return_value=big) as qem:
            verts, tris = U.union_mesh(ps, 1.0, 20, reducer="cvt")
            self.assertEqual((len(tris), qem.call_count, len(verts)), (own, 1, sum(len(m["verts"]) for m in ps)))     # the pieces side by side
            self.assertEqual(len(U.union_mesh(ps, 1.0, 20, reducer="qem")[1]), own + 9)                              # the QEM option keeps its guard
        with mock.patch.object(U.retopo, "cvt", return_value=big[:2] + ({},)):
            self.assertEqual(len(U.union_mesh(ps, 1.0, 20, reducer="cvt")[1]), own)                                  # a dual over the pieces' own cost too

    def test_a_small_detail_stays_rigid_like_a_prop(self):          # L18-2
        ps = parts() + [piece((0, 0.2, 0.3), (0, 0.2, 0.33), 0.02, "a", "m")]      # a buckle: 4 cm on a 0.65 m body
        groups = U.groups_of(ps, "material", 0.65)
        self.assertNotIn(5, [i for g in groups for c in g for i in c])
        self.assertNotIn(4, [i for g in groups for c in g for i in c])             # the prop as before
        self.assertEqual(U.prop_tris_of(ps, 0.65), U.prop_tris_of(ps) + 2 * 8 + 2 * (8 - 2))

    def test_groups_leave_props_out_and_split_materials(self):
        ps = parts()
        self.assertEqual(U.groups_of(ps, "material", 1.0), [[[0, 1, 2]], [[3]]])
        self.assertEqual(U.groups_of(ps, "bone", 1.0), [[[0, 2], [3]], [[1]]])
        self.assertEqual(sorted(map(sorted, U.groups_of(ps, "group", 1.0))), [[[0, 1, 2]], [[3]]])
        self.assertTrue(all(4 not in c for g in U.groups_of(ps, "material", 1.0) for c in g))

    def test_group_splits_far_apart_pieces_of_one_material(self):
        ps = parts()
        ps[3]["p"]["mat"] = "m"
        self.assertEqual(len(U.groups_of(ps, "material", 1.0)), 1)
        self.assertEqual(len(U.groups_of(ps, "group", 1.0)), 2)

    def test_budget_sums_under_the_total_and_keeps_the_floor(self):
        out = U.split_budget([100, 100, 40, 300, 12, 12], total=550)
        self.assertLessEqual(sum(out), 550)
        self.assertTrue(all(o >= U.MIN_TRIS for o in out))
        self.assertEqual(U.split_budget([]), [])

    def test_weights_sum_to_one_follow_the_nearest_bone_and_blend_at_the_joint(self):
        ps = parts()[:3]
        verts, _ = U.union_mesh(ps, 1.0, 80)
        w = U.vertex_weights(ps, verts, 1.0)
        self.assertTrue(all(abs(sum(x.values()) - 1) < 1e-9 for x in w))
        far = int(np.argmax(verts[:, 0]))                           # the tip of the side tube
        self.assertEqual(max(w[far], key=w[far].get), "b")
        self.assertTrue(any(len(x) == 2 and min(x.values()) > 0.05 for x in w))   # a joint vertex carries both bones

    def test_slots_follow_the_nearest_piece(self):
        ps = [parts()[0], parts()[3]]
        verts, tris = U.union_mesh(ps, 1.0, 120)
        slots = U.face_slots(ps, verts, tris)
        self.assertEqual(set(slots), {0, 1})
        near_second = verts[tris].mean(1)[:, 0] > 1.0
        self.assertTrue(all(s == 1 for s, n in zip(slots, near_second) if n))


if __name__ == "__main__":
    unittest.main()
