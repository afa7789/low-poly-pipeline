"""python3 -m unittest discover -s tests/tools/blender"""
import math
import pathlib
import random
import shutil
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import rig_families as RF  # noqa: E402
import rig_motions as M  # noqa: E402
import rig_poses as P  # noqa: E402
import rig_retarget as RT  # noqa: E402
import rig_storyboard as S  # noqa: E402

KINDS = {"existing", "attack", "spell", "loop", "death"}


def close(a, b, tol=1e-6):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


class ForwardKinematics(unittest.TestCase):
    def test_rest_pose_is_the_table(self):
        for fam in RF.FAMILIES:
            js = P.joints(fam)
            for name, _, head, tail in RF.FAMILIES[fam]:
                self.assertTrue(close(js[name][0], P.bp(head)), (fam, name))
                self.assertTrue(close(js[name][1], P.bp(tail)), (fam, name))

    def test_bone_axes_are_orthonormal_with_y_along_the_bone(self):
        for d in ((0, 0, 1), (0, 0, -1), (0, -1, 0), (0, 1, 0), (1, 0.2, -0.3)):
            x, y, z = P.bone_axes(d)
            n = math.sqrt(sum(c * c for c in d))
            self.assertTrue(close(y, tuple(c / n for c in d)))
            for a, b in ((x, y), (y, z), (x, z)):
                self.assertAlmostEqual(sum(p * q for p, q in zip(a, b)), 0.0)

    def test_children_follow_their_parent(self):
        js = P.joints("biped", {"spine": (30, 0, 0, 0)})
        self.assertFalse(close(js["head"][1], P.joints("biped")["head"][1]))
        self.assertTrue(close(js["thigh.L"][0], P.joints("biped")["thigh.L"][0]))

    def test_root_up_is_vertical_and_lift_is_forward(self):
        up = P.joints("biped", {"root": (0, 0, 0, 0, 0.5)})["head"][1]
        fwd = P.joints("biped", {"root": (0, 0, 0, 0.5)})["head"][1]
        rest = P.joints("biped")["head"][1]
        self.assertAlmostEqual(up[2] - rest[2], 0.5)
        self.assertAlmostEqual(-(fwd[1] - rest[1]), 0.5)     # spec forward is Blender -y

    @unittest.skipUnless(shutil.which("blender"), "needs Blender")
    def test_matches_blender_pose_bones(self):
        random.seed(3)
        poses = {fam: {b: (random.uniform(-60, 60), random.uniform(-40, 40), random.uniform(-60, 60),
                           random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2)) for b in RF.bones(fam)}
                 for fam in ("biped", "quadruped", "spider", "spider_high", "mounted", "hydra")}
        probe = ROOT / "tests/tools/blender/blender_pose_probe.py"
        out = subprocess.run(["blender", "-b", "--python", str(probe), "--", repr(poses)],
                             capture_output=True, text=True, cwd=ROOT, timeout=120).stdout
        line = next(ln for ln in out.splitlines() if ln.startswith("POSE_PROBE "))
        theirs = eval(line[len("POSE_PROBE "):])          # noqa: S307 - our own probe's repr
        for fam, bones in theirs.items():
            mine = P.joints(fam, poses[fam])
            for bone, (head, tail) in bones.items():
                self.assertTrue(close(mine[bone][0], head, 1e-4), (fam, bone))
                self.assertTrue(close(mine[bone][1], tail, 1e-4), (fam, bone))


class Motions(unittest.TestCase):
    def test_every_motion_has_ten_poses_on_real_bones(self):
        for fam in M.FAMILIES:
            names = set(RF.bones(fam))
            for name in M.names(fam):
                motion = M.motion(fam, name)
                self.assertIn(motion["kind"], KINDS, (fam, name))
                self.assertEqual(sorted(motion["poses"]), list(range(1, M.FRAMES + 1)), (fam, name))
                known = names | set(motion.get("props", ()))        # a spec's prop bones the motion declares
                for pose in motion["poses"].values():
                    self.assertTrue(set(pose) <= known, (fam, name, set(pose) - known))

    def test_new_motions_start_and_end_at_rest_and_hit_inside(self):
        for fam, motions in M.MOTIONS.items():
            for name, motion in motions.items():
                self.assertIn(motion["impact"], range(2, M.FRAMES), (fam, name))
                poses = M.motion(fam, f"keyed_{name}")["poses"]
                for frame in (1, M.FRAMES):
                    js, rest = P.joints(fam, poses[frame]), P.joints(fam)
                    for bone in rest:
                        self.assertTrue(close(js[bone][1], rest[bone][1], 1e-6), (fam, name, frame, bone))

    def test_grounded_frames_touch_the_floor(self):
        for fam, motions in M.MOTIONS.items():
            floor = M.lowest(fam, {})
            for name, motion in motions.items():
                poses = M.motion(fam, f"keyed_{name}")["poses"]
                for frame, pose in poses.items():
                    low = M.lowest(fam, pose)
                    hop = max(P.pad(motion["keys"].get(frame, {}).get("root", (0, 0, 0, 0)))[4], 0.0)
                    if frame in motion.get("air", ()):
                        self.assertGreater(low, floor, (fam, name, frame))
                    elif fam not in RF.HOVER and hop == 0.0 and frame in motion["keys"]:
                        self.assertAlmostEqual(low, floor, places=4, msg=(fam, name, frame))

    def test_retargeted_spider_clips_keep_the_feet_on_the_floor(self):
        if not (RT.REF_DIR / "n00U/joints.json").exists():
            self.skipTest("needs the captured references")
        floor = M.lowest("spider_high", {})
        for name in ("idle", "walk", "bite"):
            clip = M.motion("spider_high", name)["clip"]
            lows = [M.lowest("spider_high", pose) for pose in clip]
            self.assertAlmostEqual(min(lows), floor, delta=0.05, msg=name)

    def test_hand_keyed_clips_end_exactly_at_rest(self):
        for fam, motions in M.MOTIONS.items():
            for name in motions:
                clip = M.motion(fam, f"keyed_{name}")["clip"]
                self.assertEqual(set(clip[0]), set(clip[-1]), (fam, name))   # the last key names every bone
                for bone, value in clip[-1].items():
                    if bone != "root":
                        self.assertTrue(all(abs(v) < 1e-9 for v in value[:3]), (fam, name, bone, value))

    def test_flyers_are_not_pinned_to_the_floor(self):
        for fam, name in (("drake", "fly"), ("shard", "fly"), ("bird", "hover"), ("mounted_flyer", "fly")):
            ups = [P.pad(p.get("root", (0, 0, 0, 0)))[4] for p in M.motion(fam, name)["clip"]]
            self.assertLess(max(ups) - min(ups), 0.1, (fam, name))
            self.assertLess(abs(sum(ups) / len(ups)), 0.1, (fam, name))

    def test_an_authored_hop_survives_the_plant(self):
        pose = M.motion("biped", "keyed_cast_raise")["poses"][6]
        floor = M.lowest("biped", {})
        self.assertAlmostEqual(M.lowest("biped", pose), floor + 0.08, places=3)

    def test_readable_pitch_swings_a_hanging_arm_forward(self):
        pose = M.raw("biped", {1: {"arm.R": (90, 0, 0)}})[1]
        hand = P.joints("biped", pose)["arm.R"][1]
        shoulder = P.joints("biped")["arm.R"][0]
        self.assertGreater(-(hand[1] - shoulder[1]), 0.5)            # forward
        self.assertAlmostEqual(hand[2], shoulder[2], places=1)        # at shoulder height

    def test_readable_side_moves_toward_plus_x(self):
        for bone in ("arm.L", "arm.R", "leg1.upper"):
            fam = "biped" if bone.startswith("arm") else "quadruped"
            pose = M.raw(fam, {1: {bone: (0, 30, 0)}})[1]
            self.assertGreater(P.joints(fam, pose)[bone][1][0], P.joints(fam)[bone][1][0], bone)


def unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


class Aim(unittest.TestCase):
    def test_aim_points_every_bone_where_asked(self):
        random.seed(5)
        for fam in ("biped", "spider", "spider_high", "quadruped", "mounted", "drake"):
            pose = {b: (random.uniform(-70, 70), 0, random.uniform(-70, 70), 0) for b in RF.bones(fam)}
            pose["root"] = (0, 0, 0, 0)
            js = P.joints(fam, pose)
            dirs = {b: tuple(t[i] - h[i] for i in range(3)) for b, (h, t) in js.items() if b != "root"}
            got = P.joints(fam, P.aim(fam, dirs))
            for b, d in dirs.items():
                h, t = got[b]
                self.assertTrue(close(unit(d), unit([t[i] - h[i] for i in range(3)]), 1e-6), (fam, b))


@unittest.skipUnless((RT.REF_DIR / "kk_melee/joints.json").exists(), "needs the captured references")
class Retarget(unittest.TestCase):
    def test_maps_name_real_bones_on_both_sides(self):
        """Every map's bones exist in some family that uses it, and its reference points
        exist in every model it is used with."""
        used = {}
        for fam, motions in M.REF_MOTIONS.items():
            for _, _, layers, *_ in motions.values():
                for model, _, map_name, *_ in layers:
                    used.setdefault(map_name, set()).add((fam, model))
        self.assertEqual(set(used), set(RT.MAPS))
        for name, pairs in used.items():
            spec = RT.MAPS[name]
            ours = set().union(*(RF.bones(fam) for fam, _ in pairs))
            leg_bones = [b for leg in spec.get("legs", {}) for b in RT._leg(spec, leg)]
            for bone in list(spec["bones"]) + leg_bones:
                self.assertIn(bone, ours, (name, bone))
            for _, model in pairs:
                frame = RT.load(model)["clips"][spec.get("neutral") or next(iter(RT.load(model)["clips"]))][0]
                points = [p for pair in spec["bones"].values() for p in pair]
                points += [p for leg in spec.get("legs", {}).values() for p in leg] + [spec["anchor"]]
                for p in points:
                    self.assertIsNotNone(RT._point(frame, p), (name, model, p))

    def test_bones_follow_the_reference_directions(self):
        chop = "Melee_1H_Attack_Chop"
        ref, spec = RT.load("kk_melee"), RT.MAPS["kaykit_biped"]
        frame = RT.ten(ref["clips"][chop], 24)[12]
        got = P.joints("biped", RT.clip("biped", [("kk_melee", chop, "kaykit_biped")])["poses"][12])
        for bone, (a, b) in spec["bones"].items():
            want = unit([RT._point(frame, b)[i] - RT._point(frame, a)[i] for i in range(3)])
            h, t = got[bone]
            self.assertTrue(close(want, unit([t[i] - h[i] for i in range(3)]), 1e-6), bone)

    def test_layers_drive_mount_and_rider_together(self):
        got = RT.clip("mounted", [("e006", "AnimalArmature|Idle", "quaternius_animal"),
                                  ("kk_melee", "Melee_1H_Attack_Chop", "kaykit_rider")])["poses"]
        moved = {b for p in got for b, v in p.items() if any(abs(x) > 1e-6 for x in v[:3])}
        self.assertTrue({"rider.arm.R", "leg1.upper"} <= moved)


@unittest.skipUnless((RT.REF_DIR / "kk_melee/joints.json").exists(), "needs the captured references")
class Library(unittest.TestCase):
    def test_every_animated_family_has_defaults_that_exist(self):
        animated = {f for f in RF.FAMILIES if f not in RF.STATIC}
        self.assertEqual(set(M.DEFAULTS), animated)
        for fam, picks in M.DEFAULTS.items():
            self.assertEqual(set(picks), set(M.SLOTS), fam)
            for slot, value in picks.items():
                for name in M.combo(value):
                    self.assertIn(name, M.names(fam), (fam, slot))

    def test_clips_are_the_five_slots_on_real_bones(self):
        for fam in M.DEFAULTS:
            clips = M.clips(fam)
            base = [c[0] for c in clips if not c[0][-1].isdigit()]
            self.assertEqual(base, list(M.SLOTS), fam)
            names = set(RF.bones(fam))
            for slot, poses, cyclic, contacts, _ in clips:
                self.assertEqual(min(poses), 1, (fam, slot))
                self.assertTrue(all(set(p) <= names for p in poses.values()), (fam, slot))
                self.assertEqual(cyclic, slot in ("idle", "walk"), (fam, slot))
                if slot.startswith("attack"):
                    self.assertTrue(contacts and 1 < contacts[0] < max(poses), (fam, contacts))

    def test_a_motion_runs_at_its_driving_clip_pace(self):
        chop = RT.duration("kk_melee", "Melee_1H_Attack_Chop")
        for fam in ("harpy", "mounted"):                 # not the wings' 40, not the mount's idle
            m = M.motion(fam, "chop")                   # a strike starts at its wind-up: fewer samples, same pace
            self.assertEqual(m["frames"], round(chop * (len(m["clip"]) - 1) / 23), fam)
        self.assertEqual(M.motion("drake", "fly")["frames"], RT.duration("e006", "AnimalArmature|Idle"))

    def test_loops_do_not_key_the_seam_twice(self):
        for fam in ("biped", "quadruped", "spider", "spider_high", "drake"):
            walk = dict((c[0], c[1]) for c in M.clips(fam))["walk"]
            frames = sorted(walk)
            self.assertNotEqual(walk[frames[0]], walk[frames[-1]], fam)
            self.assertEqual(len(frames), 23, fam)          # 24 samples, the closing one dropped

    def test_a_combo_becomes_numbered_attacks(self):
        names = [c[0] for c in M.clips("biped", {"attack": "chop+stab+bow"})]
        self.assertEqual(names[2:5], ["attack", "attack2", "attack3"])

    @unittest.skipUnless((pathlib.Path(__file__).resolve().parents[3] / "data/unit_anim.tsv").exists(), "needs game data or a local sheet (make link)")
    def test_unit_in_path_reads_only_spec_names_and_draft_folders(self):
        self.assertEqual(M.unit_in_path("artifacts/model-sheets/runs/draft/n00U/hard-v1/spec.json"), "n00U")
        self.assertEqual(M.unit_in_path("artifacts/model-sheets/draft11/spec-n01X-v11.json"), "n01X")
        self.assertIsNone(M.unit_in_path("/home/hfoo/work/spec.json"))       # a folder named like a unit

    def test_missing_reference_data_names_what_is_missing(self):
        with self.assertRaisesRegex(KeyError, "not captured"):
            RT.duration("kk_melee", "No_Such_Clip")
        with self.assertRaisesRegex(KeyError, "missing"):
            RT._key({"hips": None}, "spine")

    def test_a_spec_pick_overrides_the_default(self):
        default = dict((c[0], c[1]) for c in M.clips("biped"))
        picked = dict((c[0], c[1]) for c in M.clips("biped", {"attack": "stab"}))
        self.assertNotEqual(default["attack"], picked["attack"])
        self.assertEqual(default["walk"], picked["walk"])

    def test_unit_table_names_real_motions(self):
        path = ROOT / "data/unit_anim.tsv"
        if not path.exists():
            self.skipTest("no data/unit_anim.tsv")
        rows = [line.split("\t") for line in path.read_text().splitlines()]
        head, rows = rows[0], rows[1:]
        self.assertEqual(head[:7], ["unit_id", "rig", *M.SLOTS[:3], "spell", "death"])
        ideas = __import__("json").loads((ROOT / "data/unit_av_ideas.json").read_text())
        self.assertLessEqual(set(ideas), {r[0] for r in rows})    # summons have rows but no brief
        for row in rows:
            rig, picks = row[1], dict(zip(head[2:7], row[2:7]))
            self.assertIn(rig, M.DEFAULTS, row[0])
            for slot, value in picks.items():
                for name in M.combo(value):
                    self.assertIn(name, M.names(rig), (row[0], slot))


class Storyboard(unittest.TestCase):
    def test_strip_draws_every_bone_in_twenty_cells(self):
        fam = "quadruped"
        motion = M.storyboard(fam)["keyed_pounce"]
        svg = S.strip_svg(fam, "keyed_pounce", motion)
        drawn = len(RF.bones(fam)) - 1                                 # the root is not drawn
        self.assertEqual(svg.count("<circle"), drawn * 2 * M.FRAMES)
        self.assertEqual(svg.count("IMPACTO"), 1)


class Lunge(unittest.TestCase):
    """Beasts' strikes keyed over the idle stance (rig_motions.LUNGES) and the hand-keyed reaches: read from
    the game camera, which looks down, by travel along the ground and by a contact pose that is held."""

    HELD = (M._LUNGE_HIT, M._LUNGE_HIT + 4, M._LUNGE_HIT + 8)       # the contact and a third of a second on

    @staticmethod
    def _front(family, pose, bones):
        js = P.joints(family, pose)
        return min(js[b][1][1] for b in bones)                        # forward is -y

    def test_a_beast_reaches_half_a_body_over_hind_feet_that_stay_and_holds(self):
        for name in ("bite", "maul", "gore", "hawk"):
            with self.subTest(name=name):
                m = M.motion("quadruped", name)
                clip = m["clip"]
                stance, wound = (P.joints("quadruped", clip[i]) for i in (0, 3))
                chest = [self._front("quadruped", clip[i], ("spine.2",)) for i in self.HELD]
                self.assertGreater(stance["spine.2"][1][1] - chest[0], 0.4 * RF.top("quadruped"))
                self.assertGreater(wound["spine.2"][1][1], stance["spine.2"][1][1] + 0.1)        # pulled back first
                self.assertLess(max(chest) - min(chest), 0.1)                                     # held, not a flick
                self.assertAlmostEqual(clip[-1]["root"][3], clip[0]["root"][3], delta=0.01)       # and home again
                self.assertEqual(m["frames"], M._LUNGE_FRAMES)                                    # a second: inside the cooldowns
                for leg in ("leg3", "leg4"):
                    drag = stance[f"{leg}.lower"][1][1] - P.joints("quadruped", clip[M._LUNGE_HIT])[f"{leg}.lower"][1][1]
                    self.assertLess(drag, 0.45 * (stance["spine.2"][1][1] - chest[0]), leg)       # the body stretches

    def test_a_bite_is_level_not_a_dip(self):
        clip = M.motion("quadruped", "bite")["clip"]
        stance, wound, struck = (P.joints("quadruped", clip[i]) for i in (0, 3, M._LUNGE_HIT))
        reach = wound["head"][1][1] - struck["head"][1][1]
        self.assertGreater(reach, 0.6 * RF.top("quadruped"))
        self.assertLess(abs(struck["head"][1][2] - stance["head"][1][2]), 0.3 * reach)

    def test_a_paw_hook_sweeps_across_the_front_along_the_ground(self):
        clip = M.motion("quadruped", "claw_punch")["clip"]
        stance, wound, struck = (P.joints("quadruped", clip[i])["leg1.lower"][1] for i in (0, 3, M._LUNGE_HIT))
        self.assertGreater(wound[0] - struck[0], 0.8)                 # sideways: from its own side across the body
        self.assertGreater(stance[1] - struck[1], 0.6)                # and forward, past the idle paw
        self.assertLess(abs(wound[2] - struck[2]), 0.5 * (wound[0] - struck[0]))      # a hook, not a drop
        other = [P.joints("quadruped", clip[i])["leg2.lower"][1][1] for i in (0, M._LUNGE_HIT)]
        self.assertAlmostEqual(other[0], other[1], delta=0.15)        # the other forepaw stands

    def test_forepaws_are_thrown_ahead_of_the_head(self):
        clip = M.motion("quadruped", "paw_slam")["clip"]
        stance, struck = (P.joints("quadruped", clip[i]) for i in (0, M._LUNGE_HIT))
        self.assertGreater(stance["leg1.lower"][1][1] - struck["leg1.lower"][1][1], 0.9)
        self.assertLess(struck["leg1.lower"][1][1], struck["head"][1][1] + 0.1)
        self.assertAlmostEqual(struck["leg3.lower"][1][1], stance["leg3.lower"][1][1], delta=0.1)

    def test_a_flyer_thrusts_its_head_clear_of_wings_swept_back(self):
        for family, name in (("drake", "breath"), ("drake", "spit"), ("bird", "bite")):
            with self.subTest(family=family, name=name):
                clip = M.motion(family, name)["clip"]
                stance, wound, struck, held = (P.joints(family, clip[i]) for i in (0, 3, M._LUNGE_HIT, M._LUNGE_HIT + 8))
                self.assertGreater(wound["head"][1][1], struck["head"][1][1] + 0.6)     # reared, then thrown forward
                self.assertGreater(stance["head"][1][1] - struck["head"][1][1], 0.5)    # past where the idle has it
                self.assertAlmostEqual(held["head"][1][1], struck["head"][1][1], delta=0.1)
                for wing in ("wing1.lower", "wing2.lower"):                              # tips back: the silhouette opens
                    self.assertGreater(struck[wing][1][1] - struck[wing][0][1], 0.5, wing)
                gap = min(struck[w][1][1] for w in ("wing1.lower", "wing2.lower")) - struck["head"][1][1]
                self.assertGreater(gap, 1.0)                                             # the head leads the wings

    def test_a_spider_lunges_with_its_front_pair_over_planted_legs(self):
        for family in ("spider", "spider_high"):
            with self.subTest(family=family):
                clip = M.motion(family, "bite")["clip"]
                stance, struck = P.joints(family, clip[0]), P.joints(family, clip[M._LUNGE_HIT])
                self.assertGreater(stance["body"][1][1] - struck["body"][1][1], 0.35)
                self.assertGreater(stance["leg2.lower"][1][1] - struck["leg2.lower"][1][1], 0.3)
                advance = stance["body"][1][1] - struck["body"][1][1]
                for leg in ("leg6", "leg7"):          # the rear legs trail, stretched: out of reach they drag
                    drag = stance[f"{leg}.lower"][1][1] - struck[f"{leg}.lower"][1][1]
                    self.assertLess(drag, 0.8 * advance, leg)

    def test_a_spider_scratch_rakes_across_the_front_from_the_ring(self):
        for family in ("spider", "spider_high"):
            with self.subTest(family=family):
                poses = M.motion(family, "keyed_scratch")["poses"]
                stance, cocked, left, right = (P.joints(family, poses[f]) for f in (1, 3, 5, 6))
                self.assertLess(stance["body"][1][1] - left["body"][1][1], 0.3)          # the bite is the lunge
                self.assertGreater(cocked["leg2.lower"][1][0] - left["leg2.lower"][1][0], 0.8)     # the left claw crosses
                self.assertLess(left["leg2.lower"][1][0], 0.0)                                      # past the middle
                self.assertGreater(right["leg3.lower"][1][0], 0.0)                                  # then the right

    def test_a_keyed_body_strike_carries_its_weapon_to_the_target(self):
        cases = (("biped", "keyed_ram", "spine", 0.3),          # a barrel on the chest
                 ("quadruped", "keyed_tail_shot", "tail.2", 0.5),       # a nozzle on a raised tail
                 ("quadruped", "keyed_spit", "head", 0.4), ("quadruped", "keyed_quill_volley", "spine.2", 0.35),
                 ("wyrm", "keyed_spit", "head", 0.4), ("ray", "keyed_spit", "body", 0.4),
                 ("crawler", "keyed_pinch", "head", 0.4))
        for family, name, bone, reach in cases:
            with self.subTest(name=name):
                m = M.motion(family, name)
                stance, struck = (P.joints(family, m["poses"][f])[bone][1] for f in (1, m["impact"]))
                self.assertGreater(stance[1] - struck[1], reach * RF.top(family))

    def test_a_keyed_reach_is_held_three_drawings(self):
        for family, name in (("quadruped", "keyed_quill_volley"), ("quadruped", "keyed_pounce"), ("spider", "keyed_pounce"),
                             ("ray", "keyed_spit"), ("crawler", "keyed_pinch")):
            with self.subTest(family=family, name=name):
                m = M.motion(family, name)
                lifts = [m["poses"][f]["root"][3] for f in range(m["impact"], m["impact"] + 4)]
                self.assertGreater(min(lifts), 0.85 * max(lifts))
                self.assertAlmostEqual(m["poses"][M.FRAMES]["root"][3], 0.0, delta=0.01)

    def test_a_quadruped_spit_snaps_out_and_is_thrown_back(self):
        m = M.motion("quadruped", "keyed_spit")
        lifts = [m["poses"][f]["root"][3] for f in range(1, M.FRAMES + 1)]
        hit = m["impact"] - 1
        self.assertGreater(lifts[hit], 0.5)
        self.assertGreater(lifts[hit + 1], 0.85 * lifts[hit])           # out for two drawings
        self.assertLess(lifts[hit + 2], 0.0)                            # then the shot throws it back: not a held lunge
        cocked = P.joints("quadruped", m["poses"][3])["head"][1][0]
        self.assertGreater(abs(cocked), 0.15)                           # the head is cocked to one side before it snaps
        self.assertAlmostEqual(lifts[-1], 0.0, delta=0.01)

    def test_hydra_necks_strike_in_turn_and_each_is_held(self):
        for name in ("keyed_bite_volley", "keyed_spit_volley"):
            with self.subTest(name=name):
                poses = M.motion("hydra", name)["poses"]
                tips = {n: {f: P.joints("hydra", poses[f])[f"{n}.3"][1] for f in poses} for n in M._NECKS}
                out = {n: [f for f in sorted(poses) if tips[n][1][1] - tips[n][f][1] > 0.4] for n in M._NECKS}
                for neck in M._NECKS:
                    self.assertGreaterEqual(len(out[neck]), 3, neck)              # along the ground, three drawings
                self.assertLess(out["neck1"][0], out["neck2"][0])
                self.assertLess(out["neck2"][0], out["neck3"][0])

    def test_a_unit_with_a_long_body_travels_in_proportion(self):
        plain = {slot: poses for slot, poses, *_ in M.clips("quadruped", {"attack": "bite"})}
        long = {slot: poses for slot, poses, *_ in M.clips("quadruped", {"attack": "bite"}, fit=(1.8, 0.9))}
        far = max(p["root"][3] for p in plain["attack"].values())
        self.assertAlmostEqual(max(p["root"][3] for p in long["attack"].values()), 1.8 * far, delta=0.01)
        self.assertEqual(long["walk"], plain["walk"])                          # only the strikes are fitted


if __name__ == "__main__":
    unittest.main()
