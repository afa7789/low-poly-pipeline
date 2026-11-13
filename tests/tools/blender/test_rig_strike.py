"""python3 -m unittest discover -s tests/tools/blender"""
import itertools
import math
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import attack_gate as G  # noqa: E402
import rig_families as RF  # noqa: E402
import rig_motions as M  # noqa: E402
import rig_poses as P  # noqa: E402
import rig_retarget as RT  # noqa: E402
import rig_strike as RS  # noqa: E402

SPEAR_UP = (("L", (0.0, -1.9, 0.3)), ("R", None))       # carried upright in the left hand


def tip(family, pose, side, blade):
    """World point of a blade's tip (wrist + the blade turned by the forearm)."""
    wrist = P.joints(family, pose)[f"forearm.{side}"][1]
    frame = P.frames(family, pose)[f"forearm.{side}"]
    return [wrist[i] + sum(frame[i][k] * blade[k] for k in range(3)) for i in range(3)]


class Repose(unittest.TestCase):
    def test_a_blade_points_where_asked_and_other_bones_stay(self):
        pose = {"spine": (20, 10, -15, 0), "thigh.L": (30, 0, 0, 0)}
        blade, w = P.unit((0.2, 0.5, 0.8)), P.unit((0.3, -1.0, -0.2))
        out = P.repose("biped", pose, {"arm.R": (0, -1, 0), "forearm.R": ((blade, w), ((0, 1, 0), (0, 0, -1)))})
        frame = P.frames("biped", out)["forearm.R"]
        got = [sum(frame[i][k] * blade[k] for k in range(3)) for i in range(3)]
        self.assertLess(math.dist(got, w), 1e-6)
        self.assertEqual(out["thigh.L"][:3], (30, 0, 0))
        arm = P.joints("biped", out)["arm.R"]
        self.assertLess(math.dist(P.unit([arm[1][i] - arm[0][i] for i in range(3)]), (0, -1, 0)), 1e-6)

    def test_mirror_swaps_the_sides(self):
        for family, name, layer in (("biped", "chop", "kaykit_biped"), ("mounted", "chop", "kaykit_rider"),
                                    ("naga", "stab", "kaykit_upper"), ("centaur", "chop", "kaykit_centaur")):
            bones = RT.MAPS[layer]["bones"]
            pose = M.motion(family, name)["clip"][9]
            was, now = P.joints(family, pose), P.joints(family, RS.mirror(pose, bones))
            for bone in (b for b in bones if b.endswith("forearm.L")):
                other = was[bone[:-1] + "R"][1]
                self.assertLess(math.dist(now[bone][1], (-other[0], other[1], other[2])), 1e-6, (family, bone))


class Strikes(unittest.TestCase):
    def test_the_armed_hand_strikes_and_the_body_stands(self):
        blade = SPEAR_UP[0][1]
        for name in ("chop", "slice_horizontal", "stab", "chop_2h", "tool_hammer"):
            with self.subTest(name):
                clip = M.motion("biped", name, 24, SPEAR_UP)["clip"]
                tips = [tip("biped", p, "L", blade) for p in clip]
                self.assertGreater(max(math.dist(tips[0], t) for t in tips), 0.8 * RF.top("biped"))
                self.assertLessEqual(max(abs(p["root"][3]) for p in clip), RS.ROOT_MAX * RF.top("biped") + 1e-6)
                self.assertLess(math.dist(tips[0], tips[-1]), 0.4)        # back in the stance (the body still settles)

    def test_the_contact_is_held_and_registered(self):
        m = M.motion("biped", "chop", 24, SPEAR_UP)
        hit = m["hit"]
        tips = [tip("biped", p, "L", SPEAR_UP[0][1]) for p in m["clip"]]
        self.assertLessEqual(hit, RS.LEAD)                                  # the wind-up is the clip's start
        self.assertLess(math.dist(tips[hit], tips[hit + 2]), 0.45)           # a 1.9 m spear on a breathing body
        self.assertLess(tips[hit][1], -1.0)                                 # the tip is out ahead (-y)

    def test_an_attack_lands_by_the_contact_frame(self):
        for family, pick in (("biped", "stab+keyed_overhead+bow"), ("quadruped", "bite"), ("spider", "bite")):
            for slot, _, _, contacts, _ in M.clips(family, {"attack": pick}):
                if slot.startswith("attack"):
                    self.assertLessEqual(contacts[0], M.CONTACT, (family, slot))

    def test_new_strikes_exist_where_the_arms_are(self):
        for family in ("biped", "harpy", "naga", "wraith"):
            for name in ("claw_rake", "staff_point", "fist_slam", "reverse_slash", "hipfire_sweep"):
                self.assertEqual(M.motion(family, name)["kind"], "attack", (family, name))
        self.assertIsNotNone(M.motion("quadruped", "claw_chop").get("hit"))

    def test_without_a_grip_the_right_hand_strikes(self):
        self.assertEqual(RS.hands(RS.STRIKES["chop"], None), (("R",), "R"))
        self.assertEqual(RS.hands(RS.STRIKES["dual_chop"], dict(SPEAR_UP))[0], ("L", "R"))
        self.assertEqual(RS.hands(RS.STRIKES["chop"], dict(SPEAR_UP))[1], "L")


SWORD = (("L", None), ("R", (0.0, 1.0, 0.0)))           # along the right forearm
STAFF = (("L", None), ("R", (0.0, -1.8, 0.0)))          # carried upright in the right hand


def blade(family, name, grip, side="R", fore=None):
    """Where the blade of a side points on the strike's contact (the sample after the registered one:
    track pushes the keys one later), armature axes."""
    m = M.motion(family, name, 24, grip, 1.0)
    held = P.unit(dict(grip)[side] or (0.0, 1.0, 0.0))
    frame = P.frames(family, m["clip"][m["hit"] + 1])[fore or f"forearm.{side}"]
    return [sum(frame[i][k] * held[k] for k in range(3)) for i in range(3)]


def apart(a, b):
    return math.degrees(math.acos(max(-1.0, min(1.0, sum(p * q for p, q in zip(a, b))))))


class Silhouettes(unittest.TestCase):
    def test_the_strikes_of_a_combo_end_apart(self):
        ends = {name: blade("biped", name, SWORD) for name in ("chop", "slice_horizontal", "slice_diagonal", "stab")}
        for (a, one), (b, other) in itertools.combinations(ends.items(), 2):
            self.assertGreater(apart(one, other), 30.0, (a, b))
        self.assertLess(ends["chop"][2], -0.5)                      # a chop ends pointing down
        self.assertLess(abs(ends["slice_horizontal"][2]), 0.2)      # a flat slice level

    def test_a_staff_jabs_level_and_stays_planted_while_the_free_hand_casts(self):
        jab, cast = blade("biped", "staff_point", STAFF), blade("biped", "cast_shoot", STAFF)
        self.assertLess(abs(jab[2]), 0.3)                           # the jab: level at the target
        self.assertGreater(cast[2], 0.8)                            # the cast: the staff stays upright
        self.assertGreater(apart(jab, cast), 35.0)
        self.assertEqual(RS.hands(RS.STRIKES["cast_shoot"], dict(STAFF)), (("L",), "R"))
        m = M.motion("biped", "cast_shoot", 24, STAFF, 1.0)
        fore = P.joints("biped", m["clip"][m["hit"] + 1])["forearm.L"]
        self.assertLess((fore[1][1] - fore[0][1]) / math.dist(*fore), -0.8)     # the free hand is thrust at the target
        self.assertEqual(RS.hands(RS.STRIKES["cast_shoot"], None), (("R",), "R"))       # nothing held: the right pushes

    def test_a_bare_hand_the_grip_names_strikes(self):
        self.assertEqual(RS.hands({"hands": "one"}, {"L": (), "R": None})[1], "L")
        self.assertEqual(RS.hands({"hands": "one"}, {"L": None, "R": None})[1], "R")
        self.assertEqual(RS.hands({"hands": "one"}, {"L": (), "R": (0.0, 1.0, 0.0)})[1], "R")

    def test_a_bow_no_hand_carries_stays_on_a_hanging_arm(self):
        m = M.motion("biped", "bow", 24, (("L", ()), ("R", None)), 1.0)
        head, tail = P.joints("biped", m["clip"][m["hit"] + 1])["arm.L"]
        self.assertLess((tail[2] - head[2]) / math.dist(head, tail), -0.7)      # the upper arm (and the bow on it) hangs
        fore = P.joints("biped", m["clip"][m["hit"] + 1])["forearm.L"]
        self.assertLess((fore[1][1] - fore[0][1]) / math.dist(*fore), -0.8)     # the forearm points at the target

    def test_a_bow_shot_high_cants_the_stave_and_kicks_on_the_release(self):
        m = M.motion("biped", "bow_up", 24, (("L", ()), ("R", None)), 1.0)

        def forward(sample):        # how far the upper arm (and the bow on it) swings forward, 0 hanging .. 1 level
            head, tail = P.joints("biped", m["clip"][sample])["arm.L"]
            return (head[1] - tail[1]) / math.dist(head, tail)
        aimed, loosed = forward(m["hit"] - 1), forward(m["hit"])
        self.assertGreater(aimed, forward(0) + 0.1)         # out of the body's outline
        self.assertLess(aimed, 0.6)                         # and far from level: a levelled stave is a lance
        self.assertGreater(loosed, aimed + 0.05)            # the release kicks it on
        self.assertLess(forward(m["hit"] + 6), aimed)       # and the arm comes down at once

    def test_a_gun_on_the_body_is_panned_by_the_torso(self):
        yaw = [P.pad(p.get("spine", ()))[1] for p in M.motion("biped", "hipfire_sweep", 24, None, 1.0)["clip"]]
        self.assertGreater(max(yaw) - min(yaw), 55.0)

    def test_the_free_arm_waits_while_the_other_throws(self):
        clip = M.motion("biped", "throw", 24, SWORD, 1.0)["clip"]
        idle = M.motion("biped", "idle")["clip"][0]
        for pose in clip:
            self.assertEqual(P.pad(pose["arm.L"]), P.pad(idle.get("arm.L", ())))

    def test_an_arm_the_grip_holds_still_waits_and_never_strikes(self):
        grip = (("L", ()), ("R", RS.STILL))
        self.assertEqual(RS.hands({"hands": "one"}, dict(grip))[1], "L")
        clip = M.motion("biped", "chop", 24, grip, 1.0)["clip"]
        idle = M.motion("biped", "idle")["clip"][0]
        self.assertTrue(all(P.pad(pose["arm.R"]) == P.pad(idle.get("arm.R", ())) for pose in clip))
        reach = [P.joints("biped", pose)["forearm.L"][1][2] for pose in clip]
        self.assertGreater(max(reach) - min(reach), 0.5)            # the left one chops

    def test_a_riders_slice_rises_where_its_chop_falls(self):
        grip = (("L", None), ("R", (0.0, 1.0, 0.0)))
        self.assertGreater(blade("mounted", "slice", grip, fore="rider.forearm.R")[2], 0.3)
        self.assertLess(blade("mounted", "chop", grip, fore="rider.forearm.R")[2], -0.3)


class Gate(unittest.TestCase):
    def grade(self, tips):
        still = [(0.0, 0.0, 0.0)] * len(tips)
        return G.grade({"tip": tips}, {"tip": tips}, still, [(0.0, 0.0, 1.0)] * len(tips), 1.0)

    def test_a_held_thrust_passes_and_a_flick_fails(self):
        out = [(0.0, -0.1 * min(i, 6), 1.0) for i in range(12)]
        flick = [(0.0, -0.2 * (i if i <= 6 else 12 - i), 1.0) for i in range(13)]
        self.assertEqual(self.grade(out)["fails"], [])
        self.assertTrue(self.grade(flick)["fails"])

    def test_a_swing_backward_is_no_strike(self):
        back = [(0.0, 0.1 * min(i, 8) - 1.0, 1.0) for i in range(12)]
        self.assertLess(self.grade(back)["strike"], 0.3)

    def test_a_torn_mesh_fails_whatever_the_clip(self):
        fine = {"strike": 1.0, "line": 1.0, "arm": 1.0, "root": 0.0, "torso": 0.0, "move": 1.0}
        self.assertEqual(G.fails({**fine, "gap": 0.02, "ribbon": 3.0}), [])
        for kind in ("melee", "ranged", "body"):
            self.assertTrue(G.fails({**fine, "gap": G.GAP + 0.01, "ribbon": 0.0}, kind), kind)
            self.assertTrue(G.fails({**fine, "gap": 0.0, "ribbon": G.RIBBON + 1}, kind), kind)

    def test_a_softer_strike_travels_less(self):
        def far(soft):
            clip = M.motion("biped", "chop", 24, SPEAR_UP, soft)["clip"]
            tips = [tip("biped", p, "L", SPEAR_UP[0][1]) for p in clip]
            return max(math.dist(tips[0], t) for t in tips)
        self.assertLess(far(0.55), 0.9 * far(1.0))

    def test_the_reference_chop_passes_with_its_blade_and_not_bare(self):
        self.assertEqual(G.grade_ref("kk_melee", "Melee_1H_Attack_Chop", 0.5)["fails"], [])
        self.assertTrue(G.grade_ref("kk_melee", "Melee_1H_Attack_Chop")["fails"])


if __name__ == "__main__":
    unittest.main()
