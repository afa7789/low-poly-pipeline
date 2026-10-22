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
                           random.uniform(-0.2, 0.2)) for b in RF.bones(fam)}
                 for fam in ("biped", "quadruped", "spider", "mounted", "hydra")}
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
            for name, motion in M.storyboard(fam).items():
                self.assertIn(motion["kind"], KINDS, (fam, name))
                self.assertEqual(sorted(motion["poses"]), list(range(1, M.FRAMES + 1)), (fam, name))
                for pose in motion["poses"].values():
                    self.assertTrue(set(pose) <= names, (fam, name, set(pose) - names))

    def test_new_motions_start_and_end_at_rest_and_hit_inside(self):
        for fam, motions in M.MOTIONS.items():
            for name, motion in motions.items():
                self.assertIn(motion["impact"], range(2, M.FRAMES), (fam, name))
                poses = M.storyboard(fam)[f"keyed_{name}"]["poses"]
                for frame in (1, M.FRAMES):
                    js, rest = P.joints(fam, poses[frame]), P.joints(fam)
                    for bone in rest:
                        self.assertTrue(close(js[bone][1], rest[bone][1], 1e-6), (fam, name, frame, bone))

    def test_grounded_frames_touch_the_floor(self):
        for fam, motions in M.MOTIONS.items():
            floor = M.lowest(fam, {})
            for name, motion in motions.items():
                poses = M.storyboard(fam)[f"keyed_{name}"]["poses"]
                for frame, pose in poses.items():
                    low = M.lowest(fam, pose)
                    if frame in motion.get("air", ()):
                        self.assertGreater(low, floor, (fam, name, frame))
                    else:
                        self.assertAlmostEqual(low, floor, places=4, msg=(fam, name, frame))

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
        for fam in ("biped", "spider", "quadruped", "mounted", "drake"):
            pose = {b: (random.uniform(-70, 70), 0, random.uniform(-70, 70), 0) for b in RF.bones(fam)}
            pose["root"] = (0, 0, 0, 0)
            js = P.joints(fam, pose)
            dirs = {b: tuple(t[i] - h[i] for i in range(3)) for b, (h, t) in js.items() if b != "root"}
            got = P.joints(fam, P.aim(fam, dirs))
            for b, d in dirs.items():
                h, t = got[b]
                self.assertTrue(close(unit(d), unit([t[i] - h[i] for i in range(3)]), 1e-6), (fam, b))


@unittest.skipUnless((RT.REF_DIR / "hfoo/joints.json").exists(), "needs the captured references")
class Retarget(unittest.TestCase):
    def test_maps_name_real_bones_on_both_sides(self):
        """Every map's bones exist in some family that uses it, and its reference points
        exist in every model it is used with."""
        used = {}
        for fam, motions in M.REF_MOTIONS.items():
            for _, _, layers in motions.values():
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
        ref, spec = RT.load("hfoo"), RT.MAPS["kaykit_biped"]
        frame = RT.ten(ref["clips"]["1H_Melee_Attack_Chop"], 24)[12]
        got = P.joints("biped", RT.clip("biped", [("hfoo", "1H_Melee_Attack_Chop", "kaykit_biped")])["poses"][12])
        for bone, (a, b) in spec["bones"].items():
            want = unit([RT._point(frame, b)[i] - RT._point(frame, a)[i] for i in range(3)])
            h, t = got[bone]
            self.assertTrue(close(want, unit([t[i] - h[i] for i in range(3)]), 1e-6), bone)

    def test_layers_drive_mount_and_rider_together(self):
        got = RT.clip("mounted", [("e006", "AnimalArmature|Idle", "quaternius_animal"),
                                  ("hfoo", "1H_Melee_Attack_Chop", "kaykit_rider")])["poses"]
        moved = {b for p in got for b, v in p.items() if any(abs(x) > 1e-6 for x in v[:3])}
        self.assertTrue({"rider.arm.R", "leg1.upper"} <= moved)


@unittest.skipUnless((RT.REF_DIR / "hfoo/joints.json").exists(), "needs the captured references")
class Library(unittest.TestCase):
    def test_every_animated_family_has_defaults_that_exist(self):
        animated = {f for f in RF.FAMILIES if f not in RF.STATIC}
        self.assertEqual(set(M.DEFAULTS), animated)
        for fam, picks in M.DEFAULTS.items():
            self.assertEqual(set(picks), set(M.SLOTS), fam)
            for slot, name in picks.items():
                self.assertIn(name, M.names(fam), (fam, slot))

    def test_clips_are_the_five_slots_on_real_bones(self):
        for fam in M.DEFAULTS:
            clips = M.clips(fam)
            self.assertEqual([c[0] for c in clips], list(M.SLOTS), fam)
            names = set(RF.bones(fam))
            for slot, poses, cyclic, contacts, _ in clips:
                self.assertEqual(min(poses), 1, (fam, slot))
                self.assertTrue(all(set(p) <= names for p in poses.values()), (fam, slot))
                self.assertEqual(cyclic, slot in ("idle", "walk"), (fam, slot))
                if slot == "attack":
                    self.assertTrue(contacts and 1 < contacts[0] < max(poses), (fam, contacts))

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
        self.assertEqual({r[0] for r in rows}, set(ideas))
        for row in rows:
            rig, picks = row[1], dict(zip(head[2:7], row[2:7]))
            self.assertIn(rig, M.DEFAULTS, row[0])
            for slot, name in picks.items():
                self.assertIn(name, M.names(rig), (row[0], slot))


class Storyboard(unittest.TestCase):
    def test_strip_draws_every_bone_in_twenty_cells(self):
        fam = "quadruped"
        motion = M.storyboard(fam)["keyed_pounce"]
        svg = S.strip_svg(fam, "keyed_pounce", motion)
        drawn = len(RF.bones(fam)) - 1                                 # the root is not drawn
        self.assertEqual(svg.count("<circle"), drawn * 2 * M.FRAMES)
        self.assertEqual(svg.count("IMPACTO"), 1)


if __name__ == "__main__":
    unittest.main()
