"""python3 -m unittest discover -s tests/tools/blender"""
import json
import pathlib
import sys
import unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import fit_spec as F  # noqa: E402
import parts_fit as PF  # noqa: E402
import silhouette  # noqa: E402

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "parts-n005.json"


def part(name, bone, box3d, order=0, front=None, zone=None):
    return {"name": name, "bone": bone, "box3d": box3d, "depth_order": order, "zone": zone,
            "box2d": {"front": front} if front else {}}


def spec(bone, material="coat"):
    return [bone, "box", [1, 1, 1], [0, 0, 0], material, {}]


class Association(unittest.TestCase):
    def test_bone_family_distance_and_zone(self):
        """the part on the bone family wins over a nearer one on another bone; the zone breaks a tie;
        a spec part far from every box belongs to none"""
        doc = {"H": 2.0, "parts": [part("torso", "spine", [[-1, 0, -1], [1, 2, 1]]),
                                   part("arm", "arm.L", [[1, 0, -1], [2, 2, 1]], zone="#111111"),
                                   part("pistol", "hand.L", [[1.2, 0, -.5], [1.8, 1, .5]], zone="#aaaaaa"),
                                   part("far", "head", [[9, 9, 9], [10, 10, 10]])]}
        zone_idx = {"#aaaaaa": 2, "#111111": 1}
        got = PF.associate([spec("forearm.L", "metal"), spec("forearm.L", "cloth"), spec("spine"), spec("head")],
                           [(1.5, 0.5, 0), (1.5, 0.5, 0), (0, 1, 0), (-5, -5, -5)], doc, 2.0,
                           {"metal": 2, "cloth": 1}, zone_idx)
        self.assertEqual(got, [2, 1, 0, None])

    def test_scales_with_the_spec_height(self):
        doc = {"H": 1.0, "parts": [part("a", "spine", [[0, 0, 0], [1, 1, 1]])]}
        self.assertEqual(PF.associate([spec("spine")], [(1.5, 1.5, 1.5)], doc, 2.0), [0])

    def test_front_pairs_need_order_and_overlap(self):
        doc = {"parts": [part("tank", "spine", [], -1, [0, 0, .5, .5]), part("torso", "spine", [], 0, [.4, .4, 1, 1]),
                         part("lamp", "spine", [], 1, [.8, .8, 1, 1]), part("same", "spine", [], 0, [0, 0, 1, 1])]}
        self.assertEqual(sorted(PF.front_pairs(doc, [0, 1, 2, 3])),
                         [(1, 0), (2, 1), (2, 3), (3, 0)])
        self.assertEqual(PF.front_pairs(doc, [0, 0, None, None]), [])
        self.assertEqual(PF.front_pairs(doc, [0, 1, 2, 3], {0: 5, 1: 0, 2: 0, 3: 0}), [(0, 1), (0, 3)])


class Masks(unittest.TestCase):
    def test_part_mask_lays_out_like_the_figure(self):
        """a box over the whole crop is the normalized figure; a box over its right half only has pixels there"""
        fig = np.zeros((768, 768), bool)
        fig[100:400, 200:300] = True
        whole = PF.part_mask(fig, [-0.5, -0.5, 1.5, 1.5])
        self.assertTrue((whole == silhouette.normalize(fig)).all())
        right = PF.part_mask(fig, [0.5, 0, 1, 1])
        cols = np.where(right.any(axis=0))[0]
        mid = np.where(whole.any(axis=0))[0].mean()
        self.assertGreater(cols.min(), mid - 2)

    def test_fixture_parts_resolve_inside_the_n005_panels(self):
        doc = json.loads(FIXTURE.read_text())
        self.assertTrue(all(p["box3d"][0][1] <= p["box3d"][1][1] for p in doc["parts"]))
        self.assertTrue({p["bone"] for p in doc["parts"]} >= {"head", "spine", "arm.L", "hand.L"})


class Terms(unittest.TestCase):
    def terms(self, masks, pairs=()):
        t = PF.PartTerms.__new__(PF.PartTerms)
        t.masks, t.pairs, t.views = masks, list(pairs), sorted({v for _, v in masks})
        return t

    def test_occlusion_and_share(self):
        """the nearer square covers the farther one: the far part is only judged where it shows"""
        big = np.array([[0, 0], [200, 0], [200, 200], [0, 200]], float)
        small = np.array([[50, 50], [150, 50], [150, 150], [50, 150]], float)
        hulls = [{"near": {"front": 0.0}}, {"near": {"front": 1.0}}]
        inside = np.zeros((silhouette.CANVAS_H, silhouette.CANVAS_W), bool)
        inside[:, :40] = True                      # the far part's mask is only a left strip
        t = self.terms({(0, "front"): inside, (1, "front"): np.ones_like(inside)})
        got = t.shares([0, 1], hulls, {"front": [big, small]})
        self.assertAlmostEqual(got[1, "front"], 1.0)
        self.assertLess(got[0, "front"], 0.4)
        self.assertGreater(t.term([0, 1], hulls, {"front": [big, small]}), 0.2)
        hidden = t.shares([0], [hulls[0], {"near": {"front": 1.0}}], {"front": [small, big]})
        self.assertEqual(hidden[0, "front"], 1.0, "a part with nothing visible is not judged")

    def test_broken_pairs(self):
        t = self.terms({}, [(0, 1), (1, 2)])
        near = [{"near": {"front": z}} for z in (0.3, 0.1, 0.1)]
        self.assertEqual(t.broken(near), {(1, 2)})


class InTheFit(unittest.TestCase):
    def test_loss_carries_the_terms_only_with_parts(self):
        parts = [["a", "box", [1, 1, 1], [0, 0, 0], "iron", {}]]
        mask = F.raster(F.Proxy({}, ("front",)).outlines(parts)["front"])[0]
        plain = F.Proxy({"front": mask}, ("front",))
        base = plain.loss(parts, free=[0])
        t = Terms().terms({(0, "front"): np.zeros_like(mask)}, [(0, 0)])      # a mask nothing falls in; a pair that cannot hold
        with_parts = F.Proxy({"front": mask}, ("front",), partfit=t)
        self.assertAlmostEqual(with_parts.loss(parts, free=[0]) - base, F.PART_W * 1.0 + F.DEPTH_W, places=6)
        self.assertAlmostEqual(with_parts.loss(parts, free=[]), plain.loss(parts, free=[]), places=6)

    def test_part_shares_report(self):
        parts = [["a", "box", [1, 1, 1], [0, 0, 0], "iron", {}]]
        mask = F.raster(F.Proxy({}, ("front",)).outlines(parts)["front"])[0]
        t = Terms().terms({(0, "front"): mask})
        proxy = F.Proxy({"front": mask}, ("front",), partfit=t)
        self.assertGreater(proxy.part_shares(parts, [0])[0, "front"], 0.95)


if __name__ == "__main__":
    unittest.main()
