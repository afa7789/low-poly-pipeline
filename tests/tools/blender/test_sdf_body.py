"""python3.14 -m unittest tests.tools.blender.test_sdf_body"""
import json
import math
import pathlib
import sys
import unittest
from typing import ClassVar

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import lathe_limb as LL
import part_geom as PG
import rig_families as RF
import sdf_body as S

D = math.radians
WING = [[0.5912, 0.2961], [0.929, 0.0405], [0.2681, 0.2291], [0.2279, 0.5823], [0.0663, 0.697], [0.1868, 0.9601], [0.7425, 0.9601]]
L_SHAPE = [[-0.5, 0], [0.5, 0], [0.5, 0.8], [0.0, 0.8], [0.0, 2.0], [-0.5, 2.0]]
CUT = {"box": [[-0.5, 0, -0.5], [0.5, 2, 0.5]], "front": L_SHAPE,
       "left": [[-1, 0], [1, 0], [1, 2], [-1, 2]], "top": [[-1, -1], [1, -1], [1, 1], [-1, 1]]}


def row(bone, kind, dims, at=(0.1, 1.0, 0.05), **opts):
    return (bone, kind, tuple(dims), tuple(at), "iron", opts)


# name -> (row, rig, cuts). Every vertex the build emits for the row must be on the zero set.
KINDS = {
    "box": (row("spine", "box", (0.4, 0.6, 0.3), rot=[10, 20, 30]), "biped", None),
    "prism": (row("arm.L", "prism", (0.2, 0.15, 0.3), sides=6, **{"from": [0.3, 1.5, 0], "to": [0.5, 0.8, 0.2]}), "biped", None),
    "frustum": (row("spine", "frustum", (0.5, 0.4, 0.3), top=[0.6, 0.8], shift=[0.05, 0.02], spin=20, sides=6), "biped", None),
    "cyl": (row("spine", "cyl", (0.2, 0.5), axis="up"), "biped", None),
    "dome": (row("head", "dome", (0.3, 0.2), top=0.4, axis="side"), "biped", None),
    "ring": (row("head", "ring", (0.4, 0.1, 0.05), spokes=3, tilt=20, spin=15, axis="fwd"), "biped", None),
    "wheel": (row("head", "wheel", (0.3, 0.05), axis="side", tilt=10), "biped", None),
    "lathe": (row("head", "lathe", (0.3, 0.6), squash=1.3, corner=0.5), "biped", None),
    "lathe rings axis z": (row("spine", "lathe", (0.3, 0.8), axis="z", profile=[[1, .8, 0, 0], [1.2, 1, .1, .05], [.9, .7, 0, 0]]), "biped", None),
    "limb knee": (row("thigh.L", "limb", (0.2, 0.15, 0.1), (0, 0, 0), **{"from": [0.3, 1, 0], "to": [0.3, 0, 0.1], "knee": [0.5, 0.05, 0.1]}),
                  "biped", None),
    "chain": (row("tail.1", "chain", (0.2, 0.1, 0.02), (0, 0, 0), bones=2, sides=8), "quadruped", None),
    "plate bevel": (row("arm.L", "plate", (0.5, 0.5, 0.1), axis="left", bevel=0.15), "biped", None),
    "plate concave": (row("wing1.upper", "plate", (0.5, 0.5, 0.1), axis="left", profile=WING, bevel=0.15, rot=[0, 0, -14]), "biped", None),
    "cut": (row("spine", "box", (1, 2, 1), (0, 1, 0), cut="sheet"), "biped", {"0": CUT}),
}
NO_CENTROID = ("ring", "wheel")      # the centre of a ring is its hole


def emitted(r, cuts):
    """(vertices on the surface, vertices that may be inside) the build emits for one spec row."""
    _bone, kind, dims, _at, _, opts = r
    sheet = ((cuts or {}).get("0") or {}).get({"lathe": "profile", "chain": "radii", "plate": "profile"}.get(kind, ""))
    if opts.get("cut") == "sheet" and cuts:
        lo, hi = cuts["0"]["box"]
        m = [0.1 * (hi[a] - lo[a]) + 0.01 for a in range(3)]
        return S.to_blender([(x, y, z) for x, y in cuts["0"]["front"] for z in (lo[2] - m[2], hi[2] + m[2])]), np.zeros((0, 3))
    if kind in S.SWEEPS:
        return np.concatenate(PG.rings_of(r, sheet)), np.zeros((0, 3))
    pts, rot, centre, _ = PG.placed(r)
    if kind == "wheel":      # bpy's torus: 10 x 4 vertices on the true torus
        a, b = np.meshgrid(np.arange(10) * 2 * math.pi / 10, np.arange(4) * 2 * math.pi / 4)
        loc = np.stack([(dims[0] + dims[1] * np.cos(b)) * np.cos(a), (dims[0] + dims[1] * np.cos(b)) * np.sin(a), dims[1] * np.sin(b)], -1)
        return loc.reshape(-1, 3) @ rot.T + centre, np.zeros((0, 3))
    if kind == "ring":       # the annulus' polygon; the spokes' corners are inside the wall
        outer, width, thick = dims
        inner = max(outer - width, 0.01)
        a = np.arange(10) * 2 * math.pi / 10
        loc = np.array([[rad * math.cos(t), rad * math.sin(t), z] for rad in (outer, inner) for z in (-thick / 2, thick / 2) for t in a])
        return loc @ rot.T + centre, np.zeros((0, 3))
    return pts @ rot.T + centre, np.zeros((0, 3))


class Parity(unittest.TestCase):
    def setUp(self):
        self.rig = LL.RIG
        self.addCleanup(setattr, LL, "RIG", self.rig)

    def test_every_emitted_vertex_is_on_the_zero_set(self):
        for name, (r, rig, cuts) in KINDS.items():
            with self.subTest(name):
                LL.set_rig(rig)
                part = S.normalize([r], cuts, (rig, ()))[0]
                verts, _ = emitted(r, cuts)
                self.assertLessEqual(np.abs(S.part_d(part, verts)).max(), 1e-6)
                if name not in NO_CENTROID and not cuts:
                    self.assertLess(S.part_d(part, verts.mean(0, keepdims=True))[0], 0)
                self.assertTrue(part["exact"])

    def test_unknown_kind_falls_back_to_the_hull(self):
        part = S.normalize([row("spine", "blob", (0.4, 0.6, 0.3))])[0]
        self.assertFalse(part["exact"])
        self.assertLess(S.part_d(part, np.array([[0.1, -0.05, 1.0]]))[0], 0)

    def test_props_and_flame_are_out(self):
        rows = [row("spine", "box", (1, 1, 1)), row("spine", "box", (1, 1, 1), prop="spear"), ("spine", "box", (1, 1, 1), (0, 1, 0), "flame", {})]
        self.assertEqual([p["i"] for p in S.normalize(rows)], [0])

    def test_brute_hull_equals_qhull(self):
        pts = PG.part_points(KINDS["frustum"][0])
        a = S.hull_planes(pts)
        qh, S.ConvexHull = S.ConvexHull, None
        try:
            b = S.hull_planes(pts)
        finally:
            S.ConvexHull = qh
        probe = np.random.default_rng(1).normal(size=(200, 3)) * 0.5 + pts.mean(0)
        self.assertTrue(np.allclose((probe @ a[:, :3].T + a[:, 3]).max(1), (probe @ b[:, :3].T + b[:, 3]).max(1), atol=1e-6))


class Union(unittest.TestCase):
    ROWS: ClassVar = [row("spine", "box", (0.4, 0.4, 0.4), (0, 1, 0)), row("spine", "box", (0.4, 0.4, 0.4), (0.4, 1.4, 0))]

    P = np.array([[0.2, 0.0, 1.2]])        # on the crease of the two boxes

    def test_smin_between_parent_and_child_only(self):
        child = S.field([self.ROWS[0], ("head", *self.ROWS[1][1:])], rig=("biped", ()), grid=32, compute=False)
        apart = S.field([self.ROWS[0], ("hand.L", *self.ROWS[1][1:])], rig=("biped", ()), grid=32, compute=False)
        self.assertEqual(len(child.pairs), 1)
        self.assertEqual(apart.pairs, [])
        self.assertLess(float(child.d(self.P)[0]), 0)
        self.assertAlmostEqual(float(apart.d(self.P)[0]), 0.0, 9)

    def test_k_zero_is_the_hard_union(self):
        f = S.field(self.ROWS, rig=("biped", ()), grid=32, k=0.0, compute=False)
        self.assertAlmostEqual(float(f.d(self.P)[0]), 0.0, 9)

    def test_k_is_clamped(self):
        f = S.field(self.ROWS, rig=("biped", ()), grid=32, compute=False)
        (_, _, k), = f.pairs
        self.assertGreaterEqual(k, 0.5 * f.voxel - 1e-12)
        self.assertLessEqual(k, 0.03 * f.shape[2] * f.voxel)

    def test_k_by_joint_class(self):
        """trunk-trunk x1, trunk-limb x0.5, limb-limb 0; hard = 0 whatever the pair (PIPELINE 29.L11-5)."""
        r = lambda bone, thick: row(bone, "box", (thick, 0.4, 0.4), (0, 1, 0))
        ks = {}
        for mode in ("base", "class", "hard"):
            f = S.field([r("pelvis", 0.4), r("spine", 0.4), r("arm.L", 0.4)] + [r("forearm.L", 0.4)], rig=("biped", ()), grid=32,
                        compute=False, k_mode=mode)
            ks[mode] = {(f.parts[a]["bone"], f.parts[b]["bone"]): k for a, b, k in f.pairs}
        k0 = ks["base"][("pelvis", "spine")]
        self.assertAlmostEqual(ks["class"][("pelvis", "spine")], k0)
        self.assertAlmostEqual(ks["class"][("spine", "arm.L")], 0.5 * k0)
        self.assertEqual(ks["class"][("arm.L", "forearm.L")], 0.0)
        self.assertEqual(set(ks["hard"].values()), {0.0})
        with self.assertRaises(ValueError):
            S.field(self.ROWS, rig=("biped", ()), grid=32, compute=False, k_mode="nope")

    def test_exterior_blend_does_not_fatten_the_inside(self):
        rows = [row("spine", "box", (0.4, 0.4, 0.4), (0, 1, 0)), row("head", "box", (0.4, 0.4, 0.4), (0.2, 1.0, 0))]
        base = S.field(rows, rig=("biped", ()), grid=32, compute=False)
        ext = S.field(rows, rig=("biped", ()), grid=32, compute=False, k_mode="ext")
        inside = np.array([[0.1, 0.0, 1.0]])             # d = -0.1 in both boxes
        self.assertLess(float(base.d(inside)[0]), -0.1 - 1e-6)
        self.assertAlmostEqual(float(ext.d(inside)[0]), -0.1, 9)
        crease = np.array([[0.3, 0.0, 1.3]])             # outside both: the fillet is still there
        self.assertAlmostEqual(float(ext.d(crease)[0]), float(base.d(crease)[0]), 9)
        self.assertEqual(S.Field.from_json(json.loads(json.dumps(ext.to_json()))).k_mode, "ext")

    def test_grid_matches_the_exact_field_and_json_roundtrips(self):
        f = S.field(self.ROWS, rig=("biped", ()), grid=32, owner=True)
        g = S.Field.from_json(json.loads(json.dumps(f.to_json()))).compute(True)
        self.assertTrue(np.array_equal(f.grid, g.grid))
        ij = np.random.default_rng(0).integers(0, f.shape, (300, 3))
        d, near = f.d(f.origin + ij * f.voxel), f.grid[tuple(ij.T)]
        small = d < 0.9 * f.margin
        self.assertLess(float(np.abs(d - near)[small].max()), 1e-5)
        idx, d1, d2 = f.ownership(f.origin + ij * f.voxel)
        self.assertTrue(np.all(d1 <= d2))
        inside = near < 0
        self.assertTrue(np.all(f.owner[tuple(ij.T)][inside] == idx[inside]) or float(np.mean(f.owner[tuple(ij.T)][inside] == idx[inside])) > 0.99)


def spec_parity(path):
    """Worst |d| of the vertices on the surface of every body part of one spec, and the worst d of those inside it."""
    doc = json.loads(pathlib.Path(path).read_text())
    family, saved, rig = doc.get("rig", "biped"), dict(RF.FAMILIES), LL.RIG
    try:
        RF.scale_rig(family, doc.get("rig_measure"))
        LL.set_rig(family, doc.get("bones"))
        worst = inner = 0.0
        for i, r in enumerate(doc["parts"]):
            r = (r[0], r[1], tuple(r[2]), tuple(r[3]), r[4], r[5] or {})
            if not S.is_body(r):
                continue
            part = S.normalize([r], None, (family, doc.get("bones")))[0]
            surf, within = emitted(r, None)
            worst = max(worst, float(np.abs(S.part_d(part, surf)).max()))
            if len(within):
                inner = max(inner, float(S.part_d(part, within).max()))
        return worst, inner
    finally:
        RF.FAMILIES.clear()
        RF.FAMILIES.update(saved)
        LL.RIG = rig


class Skin(unittest.TestCase):
    """sdf_body.weights / materials (PIPELINE 28.L10-5): bones by ownership, a mixed junction, the limb ramp, the material."""
    RIG = ("biped", ())

    def setUp(self):
        self.rig = LL.RIG
        self.addCleanup(setattr, LL, "RIG", self.rig)

    def weights_at(self, rows, spec_points, grid=48):
        f = S.field(rows, rig=self.RIG, grid=grid, compute=False)
        names, W = S.weights(S.to_blender(spec_points), f, rows, self.RIG)
        return dict(zip(names, W.T))

    def test_parent_child_boxes_own_their_vertices_and_mix_at_the_crease(self):
        rows = [row("spine", "box", (0.4, 0.4, 0.4), (0, 1, 0)), row("head", "box", (0.4, 0.4, 0.4), (0.4, 1.4, 0))]
        w = self.weights_at(rows, [(-0.2, 0.8, 0.0), (0.6, 1.6, 0.0), (0.2, 1.2, 0.0)])
        self.assertTrue(np.allclose(w["spine"][0], 1) and np.allclose(w["head"][1], 1))
        self.assertGreater(min(w["spine"][2], w["head"][2]), 0.3)               # the crease: both bones
        self.assertAlmostEqual(sum(float(v[2]) for v in w.values()), 1.0)

    def test_siblings_far_apart_do_not_mix(self):
        rows = [row("foot.L", "box", (0.2, 0.2, 0.2), (-1, 1, 0)), row("foot.R", "box", (0.2, 0.2, 0.2), (1, 1, 0))]
        w = self.weights_at(rows, [(-1, 1, 0), (1, 1, 0)])
        self.assertTrue(np.allclose(w["foot.L"], [1, 0]) and np.allclose(w["foot.R"], [0, 1]))

    def test_limb_ramps_from_upper_to_lower_around_the_knee(self):
        rows = [row("thigh.L", "limb", (0.2, 0.15, 0.1), (0, 0, 0), **{"from": [0.3, 1, 0], "to": [0.3, 0, 0], "knee": [0.5, 0, 0]})]
        ys = [0.99, 0.65, 0.5, 0.35, 0.01]               # from, above the ramp, the knee, below the ramp, to
        w = self.weights_at(rows, [(0.3, y, 0) for y in ys])
        np.testing.assert_allclose(w["thigh.L"], [1, 1, 0.5, 0, 0], atol=0.02)
        np.testing.assert_allclose(w["thigh.L"] + w["shin.L"], 1)
        self.assertTrue(np.all(np.diff(w["thigh.L"]) <= 1e-9))

    def test_a_bone_the_rig_lacks_rides_the_root(self):
        rows = [row("abdomen", "box", (0.4, 0.4, 0.4), (0, 1, 0))]       # a spider bone on a biped rig (massing pre-spec, v13)
        w = self.weights_at(rows, [(0, 1, 0)])
        self.assertTrue(np.allclose(w["root"], [1]))

    def test_material_is_the_nearest_part_s(self):
        rows = [row("spine", "box", (0.4, 0.4, 0.4), (0, 1, 0)), ("head", "box", (0.4, 0.4, 0.4), (0.4, 1.4, 0), "brass", {})]
        f = S.field(rows, rig=self.RIG, grid=32, compute=False)
        self.assertEqual(S.materials(S.to_blender([(-0.1, 1.0, 0.0), (0.5, 1.5, 0.0)]), f, rows), ["iron", "brass"])


if __name__ == "__main__":
    unittest.main()
