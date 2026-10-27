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


if __name__ == "__main__":
    unittest.main()
