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
