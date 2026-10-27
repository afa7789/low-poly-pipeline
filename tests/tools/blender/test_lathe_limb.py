"""python3 -m unittest discover -s tests/tools/blender"""
import pathlib
import sys
import unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import cut_hull as CH  # noqa: E402
import fit_spec as F  # noqa: E402
import lathe_limb as LL  # noqa: E402
import preflight as PF  # noqa: E402
import spec_pipeline as SP  # noqa: E402

LEG = {"from": [0.3, 1.0, 0.0], "to": [0.3, 0.0, 0.1], "knee": [0.5, 0.0, 0.1]}


def lathe(dims=(0.4, 0.6), at=(0, 1, 0), **opts):
    return ["head", "lathe", list(dims), list(at), "iron", opts]


def limb(bone="thigh.L", dims=(0.2, 0.15, 0.1), **opts):
    return [bone, "limb", list(dims), [0, 0, 0], "iron", {**LEG, **opts}]


class Geometry(unittest.TestCase):
    def test_tris(self):
        for name, kind, opts, want in [
                ("lathe default", "lathe", {}, 68),
                ("lathe 8 sides, 5 rings", "lathe", {"sides": 8, "profile": [1] * 5}, 76),
                ("limb 6", "limb", {}, 32),
                ("limb 8", "limb", {"sides": 8}, 44)]:
            with self.subTest(name):
                self.assertEqual(LL.tris(kind, opts), want)
                self.assertEqual(PF.part_tris(["b", kind, [1, 1], [0, 0, 0], "iron", opts]), want)

    def test_lathe_box_and_squash(self):
        (lo, hi) = PF.bbox(lathe(sides=8, squash=2.0))
        self.assertAlmostEqual(hi[0] - lo[0], 0.8, 3)       # x radius r
        self.assertAlmostEqual(hi[2] - lo[2], 0.4, 3)       # z radius r / squash
        self.assertAlmostEqual(hi[1] - lo[1], 0.6, 3)

    def test_limb_knee_and_box(self):
        rings = LL.limb_rings((0.2, 0.15, 0.1), LEG)
        self.assertEqual([len(r) for r in rings], [6, 6, 6])
        knee = np.mean(rings[1], axis=0)
        self.assertTrue(np.allclose(knee, (0.3, 0.5, 0.15), atol=1e-6))
        lo, hi = PF.bbox(limb())
        self.assertGreaterEqual(hi[2], 0.1 + 0.15 * 0.8)    # the bent knee is inside the box

    def test_bone_pairs(self):
        known = {"leg1.upper", "leg1.lower", "thigh.L", "shin.L", "arm.L", "forearm.L", "spine"}
        for bone, want in [("leg1.upper", ("leg1.upper", "leg1.lower")), ("shin.L", ("thigh.L", "shin.L")),
                           ("arm.L", ("arm.L", "forearm.L")), ("spine", None), ("foot.L", None)]:
            with self.subTest(bone):
                self.assertEqual(LL.limb_bones(bone, known), want)


class Rules(unittest.TestCase):
    def test_limb_covers_the_pair_bone(self):
        import rig_families as RF
        doc = {"rig": "spider", "parts": [limb("leg1.upper", (0.05, 0.03, 0.02))]}
        rows = {n: d for n, _, d in PF.checks_of(doc["parts"], doc, "mass", PF.targets_from(None), [])}
        self.assertIn("leg1.lower", RF.required("spider"))
        self.assertNotIn("leg1.lower", rows["bones"])


class Schema(unittest.TestCase):
    def test_validate(self):
        for name, part, ok in [
                ("lathe", lathe(profile=[0.5, 0.8, 1, 1, 0.8, 0.5], squash=1.1), True),
                ("limb", limb(), True),
                ("lathe with rot", lathe(rot=[0, 0, 10]), False),
                ("lathe cut", lathe(cut="sheet"), False),
                ("short profile", lathe(profile=[1, 1, 1]), False),
                ("12 sides", lathe(sides=12), False),
                ("limb without span", ["thigh.L", "limb", [0.2, 0.1, 0.1], [0, 1, 0], "iron", {}], False),
                ("knee at the end", limb(knee=[0.95, 0, 0]), False)]:
            with self.subTest(name):
                if ok:
                    SP.validate([part])
                else:
                    with self.assertRaises(ValueError):
                        SP.validate([part])

    def test_dsl_names_both(self):
        self.assertTrue(all(f'"{k}"' in SP.DSL for k in ("lathe", "limb")))


class SheetProfile(unittest.TestCase):
    def test_bell_with_an_arm_beside(self):
        """figure 2.0 tall on 200 rows: the strip y 0.6-1.0 is widest at the top; a far arm column is ignored"""
        m = np.zeros((200, 200), bool)
        for r in range(100, 140):
            half = 10 + (140 - r) // 2
            m[r, 100 - half:100 + half] = True
        m[0:200, 100] |= True
        m[100:140, 190:200] = True                      # an arm 0.9 m away from the part
        part = ["spine", "lathe", [0.3, 0.4], [0.0, 0.8, 0.0], "iron", {}]
        prof = CH.lathe_profile(m, (2.0, 0.0), part, 0)
        self.assertEqual(len(prof), LL.SHEET_RINGS)
        self.assertGreater(prof[-1], prof[0])           # bottom (row 140) narrow, top (row 100) wide
        self.assertLessEqual(max(prof), CH.PROFILE_WIN)  # the arm 0.9 m out is outside the window
        self.assertIsNone(CH.lathe_profile(np.zeros((200, 200), bool), (2.0, 0.0), part, 0))


class Fit(unittest.TestCase):
    def test_points_and_params(self):
        part = lathe(profile=[0.5, 0.8, 1, 1, 0.8, 0.5])
        x = np.stack(F.PROJECT["front"](F.part_points(part)), 1)
        self.assertAlmostEqual(x[:, 0].max() - x[:, 0].min(), 0.8, 3)
        self.assertEqual(sum(F.extra_size(part, n) for n in F.extras_of(part)), 7)
        self.assertEqual(sum(F.extra_size(limb(), n) for n in F.extras_of(limb())), 3)
        self.assertEqual(len(F.bounds_of(part, False, extra=F.extras_of(part))), 2 + 3 + 7)
        self.assertEqual(F.bounds_of(part, True, extra=F.extras_of(part))[2 + 3], (-1, 0))     # a torso profile only shrinks

    def test_moved_mirrors_the_knee(self):
        left, x = limb(knee=[0.5, 0.05, 0.1]), np.ones(3 + 3 + 3)
        right = F.flip_x(left)
        a, b = F.moved(left, x, 2.0, extra=("knee",)), F.moved(right, x, 2.0, mirror=True, extra=("knee",))
        self.assertGreater(a[5]["knee"][0], 0.5)
        self.assertAlmostEqual(a[5]["knee"][1], -b[5]["knee"][1], 4)
        self.assertEqual(a[5]["knee"][2], b[5]["knee"][2])
        prof = F.moved(lathe(profile=[1.0] * 6), np.ones(2 + 3 + 7), 2.0, extra=("profile",))[5]["profile"]
        self.assertEqual(prof, [1.15] * 6)


def plate(dims=(0.6, 0.4, 0.1), at=(0, 1, 0), bone="arm.L", **opts):
    return [bone, "plate", list(dims), list(at), "iron", opts]


TRI = [[0, 0], [1, 0], [0.5, 1]]


class Plate(unittest.TestCase):
    def test_tris(self):
        for name, opts, want in [("default sheet worst case", {}, 2 * 6 + 2 * 8), ("triangle", {"profile": TRI}, 8),
                                 ("beveled", {"profile": TRI, "bevel": 0.2}, 2 + 18)]:
            with self.subTest(name):
                self.assertEqual(PF.part_tris(plate(**opts)), want)

    def test_axes_put_the_thickness_on_the_normal(self):
        for axis, thin in [("front", 2), ("left", 0), ("top", 1)]:
            with self.subTest(axis):
                lo, hi = PF.bbox(plate((0.6, 0.4, 0.1), axis=axis, profile=[[0, 0], [1, 0], [1, 1], [0, 1]]))
                ext = [h - l for l, h in zip(lo, hi)]
                self.assertAlmostEqual(ext[thin], 0.1, 4)
                self.assertAlmostEqual(sorted(ext)[2], 0.6, 4)

    def test_bevel_shrinks_the_faces(self):
        rings = LL.plate_rings((1, 1, 0.2), (0, 0, 0), {"profile": [[0, 0], [1, 0], [1, 1], [0, 1]], "bevel": 0.3})
        self.assertEqual(len(rings), 4)
        self.assertAlmostEqual(max(p[0] for p in rings[0]), 0.35, 4)      # face: 0.5 * (1 - 0.3)
        self.assertAlmostEqual(max(p[0] for p in rings[1]), 0.5, 4)

    def test_rot_turns_the_box(self):
        flat = PF.bbox(plate(profile=TRI))
        turned = PF.bbox(plate(profile=TRI, rot=[0, 0, 90]))
        self.assertAlmostEqual(turned[1][1] - turned[0][1], flat[1][0] - flat[0][0], 3)    # roll: w now stands up

    def test_validate(self):
        for name, part, ok in [
                ("plain", plate(), True), ("profile", plate(profile=TRI, bevel=0.2, axis="top", rot=[0, 0, 20]), True),
                ("axis", plate(axis="up"), False), ("2 points", plate(profile=TRI[:2]), False),
                ("9 points", plate(profile=[[0.1 * i, 0.5] for i in range(9)]), False),
                ("outside 0-1", plate(profile=[[0, 0], [1.2, 0], [1, 1]]), False),
                ("bevel", plate(bevel=0.5), False), ("span", plate(**{"from": [0, 0, 0], "to": [0, 1, 0]}), False),
                ("cut", plate(cut="sheet"), False), ("two dims", plate((0.6, 0.4)), False)]:
            with self.subTest(name):
                if ok:
                    SP.validate([part])
                else:
                    with self.assertRaises(ValueError):
                        SP.validate([part])
        self.assertIn('"plate"', SP.DSL)

    def test_top_outline_front_is_v_one(self):
        """figure x -0.5..0.5, z -1..1 on a 200x100 mask; a plate in the front half reads v 0..1 inside its box,
        wider at the front (bottom rows of the sheet) than at the back"""
        m = np.zeros((200, 100), bool)
        for r in range(200):
            half = 10 + r // 5
            m[r, 50 - half:50 + half] = True
        box = ((-0.5, 0.0, -1.0), (0.5, 1.0, 1.0))
        poly = CH.top_outline(m, box, (-0.5, 0.5, 0.0), (0.5, 1.0, 1.0))
        self.assertIsNotNone(poly)
        self.assertLessEqual(len(poly), CH.LIMIT)
        self.assertTrue(all(0 <= u <= 1 and 0 <= v <= 1 for u, v in poly))
        wide = [u for u, v in poly if v > 0.9]
        narrow = [u for u, v in poly if v < 0.1]
        self.assertGreater(max(wide) - min(wide), max(narrow) - min(narrow))

    def test_top_flipped_when_the_head_is_up(self):
        """boxes: a big body at z<0 and a small head at z>0; the panel draws the big mass at the bottom (head up)"""
        boxes = [((-0.4, 0, -1.0), (0.4, 1, 0.2)), ((-0.1, 0, 0.2), (0.1, 1, 0.6))]
        ext = ((-0.4, 0, -1.0), (0.4, 1, 0.6))
        m = np.zeros((160, 80), bool)
        m[0:40, 35:45] = True                       # the head at the top of the panel
        m[40:160, 5:75] = True
        self.assertTrue(CH.top_flipped(m, boxes, ext))
        self.assertFalse(CH.top_flipped(m[::-1], boxes, ext))

    def test_fit_points_and_params(self):
        part = plate(profile=TRI, rot=[0, 0, 90])
        lo, hi = PF.bbox(part)
        pts = F.part_points(part)                      # Blender axes: x, -z, y
        self.assertAlmostEqual(pts[:, 2].max(), hi[1], 3)
        self.assertAlmostEqual(pts[:, 2].min(), lo[1], 3)
        self.assertEqual(F.extras_of(plate()), ())      # no profile baked yet: nothing to scale
        names = F.extras_of(part)
        out = F.moved(part, np.ones(3 + 3 + 2), 2.0, extra=names)[5]["profile"]
        self.assertTrue(all(0 <= v <= 1 for q in out for v in q))
        self.assertGreater(out[1][0] - out[0][0], 1.0 * 1.0 - 1e-9)       # base grew about the centroid, then clipped at 1


if __name__ == "__main__":
    unittest.main()
