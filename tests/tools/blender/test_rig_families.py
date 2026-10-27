"""python3 -m unittest discover -s tests/tools/blender"""
import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import rig_families as RF  # noqa: E402

OTHERS = [f for f in RF.FAMILIES if f != "biped" and f not in RF.STATIC]


class Tables(unittest.TestCase):
    def test_required_bones_exist_and_skip_root_and_tails(self):
        for fam in RF.FAMILIES:
            req = RF.required(fam)
            self.assertTrue(req <= set(RF.bones(fam)), fam)
            self.assertNotIn("root", req)
            self.assertFalse(any(b.startswith("tail") for b in req), fam)

    def test_vehicle_needs_only_hull_and_head(self):
        self.assertEqual(RF.required("vehicle"), {"hull", "head"})

    def test_parents_skip_the_root(self):
        self.assertEqual(RF.parents("biped")["forearm.L"], "arm.L")
        self.assertNotIn("pelvis", RF.parents("biped"))     # hangs off root
        self.assertEqual(RF.parents("spider")["leg3.lower"], "leg3.upper")

    def test_top_is_the_rig_height(self):
        self.assertAlmostEqual(RF.top("biped"), 2.72)
        self.assertLess(RF.top("serpent"), 1.0)


class Composition(unittest.TestCase):
    def test_parents_exist_and_names_are_unique(self):
        for fam, table in RF.FAMILIES.items():
            names = [b[0] for b in table]
            self.assertEqual(len(names), len(set(names)), fam)
            for name, parent, *_ in table:
                self.assertTrue(parent is None or parent in names, (fam, name, parent))

    def test_spider_body_lies_along_the_ground(self):
        _, _, head, tail = next(b for b in RF.SPIDER if b[0] == "body")
        self.assertGreater(abs(tail[2] - head[2]), abs(tail[1] - head[1]))

    def test_high_spider_knees_stand_above_the_back_and_shins_reach_the_floor(self):
        table = {n: (h, t) for n, _, h, t in RF.SPIDER_HIGH}
        body_top = max(table["body"][0][1], table["abdomen"][0][1])
        self.assertEqual([b[0] for b in RF.SPIDER_HIGH], [b[0] for b in RF.SPIDER])
        for i in range(1, 9):
            hip, knee = table[f"leg{i}.upper"]
            self.assertGreater(knee[1], body_top)
            self.assertAlmostEqual(table[f"leg{i}.lower"][1][1], 0.04)

    def test_rider_sits_above_the_mount(self):
        table = dict((n, (h, t)) for n, _, h, t in RF.MOUNTED)
        self.assertGreater(table["rider.spine"][0][1], table["spine.2"][0][1])

    def test_extras_add_bones_and_reject_misfits(self):
        table = RF.with_extras("vehicle", [["mast", "hull", [0, 0.5, 0], [0, 1.5, 0]]])
        self.assertIn("mast", [b[0] for b in table])
        self.assertEqual(RF.parents("vehicle", [["mast", "hull", [0, 0.5, 0], [0, 1.5, 0]]])["mast"], "hull")
        for bad in (["hull", "root", [0, 0, 0], [0, 1, 0]],       # name taken
                    ["mast", "turret", [0, 0, 0], [0, 1, 0]]):   # no such parent
            with self.assertRaises(ValueError):
                RF.with_extras("vehicle", [bad])

    def test_hoverers_bob_and_flyers_flap(self):
        for fam in ("wraith", "pod", "drake"):               # the bob rises: `up`, the 5th value
            self.assertTrue(any(p.get("root", (0, 0, 0, 0, 0))[4] > 0 for p in RF.walk(fam).values()), fam)
        pose = RF.walk("drake")[4]
        self.assertAlmostEqual(pose["wing1.upper"][0], -pose["wing2.upper"][0])

    def test_quadruped_spine_stays_rigid_serpent_waves(self):
        self.assertNotIn("spine.2", RF.walk("quadruped")[4])
        self.assertIn("spine.5", RF.walk("serpent")[4])


class Clips(unittest.TestCase):
    def test_four_clips_keyed_only_on_real_bones(self):
        for fam in OTHERS:
            clips = RF.actions(fam)
            self.assertEqual([c[0] for c in clips], ["idle", "walk", "attack", "death"])
            names = set(RF.bones(fam))
            for _, poses, *_ in clips:
                for pose in poses.values():
                    self.assertTrue(set(pose) <= names, (fam, set(pose) - names))

    def test_buildings_have_no_clips(self):
        self.assertEqual(RF.actions("building"), [])
        self.assertEqual(RF.required("building"), {"body"})

    def test_walk_loops(self):
        for fam in ("quadruped", "spider", "spider_high", "serpent"):
            poses = RF.walk(fam)
            first, last = poses[1], poses[max(poses)]
            for bone, value in first.items():
                for a, b in zip(value, last[bone]):
                    self.assertAlmostEqual(a, b, places=6, msg=(fam, bone))

    def test_quadruped_trots_in_diagonal_pairs(self):
        pose = RF.walk("quadruped")[4]
        self.assertAlmostEqual(pose["leg1.upper"][0], pose["leg4.upper"][0])
        self.assertAlmostEqual(pose["leg1.upper"][0], -pose["leg2.upper"][0])

    def test_vehicle_wheels_spin_one_way(self):
        spins = [pose["wheel1"][1] for _, pose in sorted(RF.walk("vehicle").items())]
        self.assertEqual(spins, sorted(spins))
        self.assertGreater(spins[-1], 300)


class ScaledByLine(unittest.TestCase):
    """quadruped, wyrm, drake rebuilt from a snout-to-tail centre line (PIPELINE 22.L4-4b)."""
    LINE = [[0.1 * i, 0.5 - 0.01 * i, 0.08] for i in range(17)]
    M = {"len": 1.6, "line": LINE, "trunk": [0.5, 1.1], "belly": 0.35, "legs": {"x": [0.55, 1.05], "spread": 0.15, "r": 0.05},
         "wing": {"span": 0.4, "tip": [0.3, 1.0], "root_x": 0.15, "root_y": 0.6, "width": 0.08, "area": 0.03, "chord": [0.5, 0.9], "top": 0.7, "root": 6}}

    def tearDown(self):
        RF.FAMILIES.update(RF.FIXED)
        RF._drop_caches()

    def test_same_bones_as_the_fixed_table_and_the_height_kept(self):
        for fam in RF.SCALABLE:
            with self.subTest(fam):
                table = RF.scale_rig(fam, self.M) and RF.FAMILIES[fam]
                self.assertEqual({b[0] for b in table}, {b[0] for b in RF.FIXED[fam]})
                self.assertEqual(RF.top(fam), RF.HEIGHT[fam])
                self.assertTrue(all(b[2][1] >= 0 and b[3][1] >= 0 for b in table))      # nothing under the ground

    def test_quadruped_legs_stand_at_the_measured_columns_and_spread(self):
        RF.scale_rig("quadruped", self.M)
        legs = {b[0]: b for b in RF.FAMILIES["quadruped"]}
        self.assertAlmostEqual(legs["leg1.upper"][2][0], 0.15 * RF.HEIGHT["quadruped"], 3)
        self.assertGreater(legs["leg1.upper"][2][2], legs["leg3.upper"][2][2])        # front pair ahead of the rear pair (z forward)

    def test_wings_and_fallback(self):
        RF.scale_rig("drake", self.M)
        wing = {b[0]: b for b in RF.FAMILIES["drake"]}["wing1.lower"]
        self.assertAlmostEqual(wing[3][1], RF.HEIGHT["drake"], 3)                     # the tip is the sheet's highest pixel
        self.assertFalse(RF.scale_rig("biped", self.M))
        self.assertFalse(RF.scale_rig("drake", None))


if __name__ == "__main__":
    unittest.main()


class ScaledSpider(unittest.TestCase):
    M = {"body_r": 0.3, "body_len": 0.8, "body_under": 0.25, "knee_h": 0.45, "knee_r": 0.6, "foot_r": 0.45}

    def test_same_bones_height_kept_and_legs_follow_the_measures(self):
        fixed = {fam: list(RF.FAMILIES[fam]) for fam in RF.SPIDERS}
        try:
            for fam in RF.SPIDERS:
                table = RF.scale_spider(fam, self.M)
                self.assertEqual([b[0] for b in table], [b[0] for b in fixed[fam]])
                self.assertAlmostEqual(RF.top(fam), RF.SPIDER_H)
                feet = [b[3] for b in table if b[0].endswith(".lower")]
                self.assertTrue(all(abs(math.hypot(x, z) - 0.45 * RF.SPIDER_H) < 1e-9 for x, _, z in feet))
                knee = next(b[3] for b in table if b[0] == "leg1.upper")
                self.assertAlmostEqual(knee[1], 0.45 * RF.SPIDER_H)
        finally:
            RF.FAMILIES.update(fixed)

    def test_leg_length_is_hip_knee_foot(self):
        self.assertGreater(RF.spider_leg_len(self.M), 0.6)
