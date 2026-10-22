"""python3 -m unittest discover -s tests/tools -p 'test_inject*.py'"""
import math
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "tools"))

import inject_clips as I  # noqa: E402


def biped_doc(helper=False):
    """A small glTF biped in T-pose (Y up, facing +Z, left = +X), mixamo-like names; with
    `helper`, a Maya scale-compensation node sits between the upper arm and the forearm."""
    spec = [  # name, parent, translation
        ("Root", None, [0, 0, 0]), ("Hips", "Root", [0, 1.0, 0]), ("Spine", "Hips", [0, 0.2, 0]),
        ("Neck", "Spine", [0, 0.5, 0]), ("Head", "Neck", [0, 0.1, 0]), ("HeadTop_End", "Head", [0, 0.2, 0]),
        ("LeftArm", "Spine", [0.2, 0.45, 0]), ("LeftForeArm", "LeftArm", [0.3, 0, 0]),
        ("LeftHand", "LeftForeArm", [0.3, 0, 0]),
        ("RightArm", "Spine", [-0.2, 0.45, 0]), ("RightForeArm", "RightArm", [-0.3, 0, 0]),
        ("RightHand", "RightForeArm", [-0.3, 0, 0]),
        ("LeftUpLeg", "Hips", [0.1, 0, 0]), ("LeftLeg", "LeftUpLeg", [0, -0.45, 0]),
        ("LeftFoot", "LeftLeg", [0, -0.45, 0]),
        ("RightUpLeg", "Hips", [-0.1, 0, 0]), ("RightLeg", "RightUpLeg", [0, -0.45, 0]),
        ("RightFoot", "RightLeg", [0, -0.45, 0]),
    ]
    if helper:
        spec[7] = ("LeftForeArm_scaleCompensation", "LeftArm", [0.3, 0, 0])
        spec.insert(8, ("LeftForeArm", "LeftForeArm_scaleCompensation", [0, 0, 0]))
    names = [n for n, *_ in spec]
    nodes = [{"name": f"mixamorig:{n}_{i}", "translation": t} for i, (n, _, t) in enumerate(spec)]
    for i, (_, parent, _) in enumerate(spec):
        if parent is not None:
            nodes[names.index(parent)].setdefault("children", []).append(i)
    joints = [i for i, n in enumerate(names) if "scaleCompensation" not in n]
    return {"asset": {"version": "2.0"}, "nodes": nodes, "skins": [{"joints": joints}],
            "buffers": [{"byteLength": 0}], "animations": [{"name": "Take 001", "samplers": [], "channels": []}]}


def mapped(doc):
    skel = I.Skeleton(doc)
    m = I.humanoid(skel, set(doc["skins"][0]["joints"]))
    return skel, {k: (skel.names[a].split(":")[1].rsplit("_", 1)[0], skel.names[b].split(":")[1].rsplit("_", 1)[0])
                  for k, (a, b) in m.items()}


class Names(unittest.TestCase):
    def test_roles_across_conventions(self):
        cases = {"mixamorig:LeftForeArm_10": ("L", "forearm"), "Bip001 R Forearm_031": ("R", "forearm"),
                 "forearm.L_metarig": ("L", "forearm"), "CATRigLArm2_015": ("L", "arm2"),
                 "L_knee_00": ("L", "knee"), "Elbow_R_014": ("R", "elbow"), "Upperarm.Left": ("L", "upperarm")}
        for name, want in cases.items():
            self.assertEqual(I.role(name), want, name)

    def test_a_name_every_joint_shares_is_noise(self):
        names = ["Sorcerer_Left_LowerArm", "Sorcerer_Left_Hand", "Sorcerer_Head", "Sorcerer_Hips"]
        noise = I.noise_tokens(names)
        self.assertIn("sorcerer", noise)
        self.assertEqual(I.role(names[0], noise), ("L", "lowerarm"))


class Mapping(unittest.TestCase):
    def test_a_mixamo_biped_maps_every_limb_and_the_torso(self):
        _, m = mapped(biped_doc())
        self.assertEqual(m["arm.L"], ("LeftArm", "LeftForeArm"))
        self.assertEqual(m["shin.R"], ("RightLeg", "RightFoot"))        # mixamo "Leg" under "UpLeg" is the shin
        self.assertEqual(m["spine"], ("Spine", "Neck"))
        self.assertEqual(m["head"], ("Head", "HeadTop_End"))

    def test_scale_compensation_nodes_are_looked_through(self):
        _, m = mapped(biped_doc(helper=True))
        self.assertEqual(m["arm.L"], ("LeftArm", "LeftForeArm"))

    def test_the_front_is_measured_from_the_shoulders(self):
        doc = biped_doc()
        skel = I.Skeleton(doc)
        m = I.humanoid(skel, set(doc["skins"][0]["joints"]))
        left, up, front = I.front_of(skel, m)
        self.assertAlmostEqual(front[2], 1.0)
        self.assertAlmostEqual(left[0], 1.0)


class Solve(unittest.TestCase):
    def test_a_mapped_joint_points_where_asked(self):
        doc = biped_doc()
        skel = I.Skeleton(doc)
        m = I.humanoid(skel, set(doc["skins"][0]["joints"]))
        target = I.unit([0.0, 0.3, 1.0])                               # left arm forward and a bit up
        local = I.solve(skel, list(m.items()), {"arm.L": target}, {})
        arm, fore = m["arm.L"]
        world = I.mul(skel.world_rot[skel.parent[arm]], I.q_to_m(local[arm]))
        rest_vec = [a - b for a, b in zip(skel.world_pos[fore], skel.world_pos[arm])]
        got = I.unit(I.apply(world, I.apply(I.tr(skel.world_rot[arm]), rest_vec)))
        self.assertLess(math.dist(got, target), 1e-6)


class Glb(unittest.TestCase):
    def test_appending_twice_replaces_instead_of_piling_up(self):
        doc, bin_ = biped_doc(), bytearray()
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "x.glb"
            for _ in range(2):
                bin_ = I.strip_previous(doc, bin_)
                doc["extras"] = {"cf_inject": {"bin": len(bin_), "accessors": len(doc.get("accessors", [])),
                                               "views": len(doc.get("bufferViews", [])), "hash": "h"}}
                I.add_animation(doc, bin_, "attack", [0.0, 0.5], {3: [[0, 0, 0, 1], [0, 0, 0, 1]]}, {})
                doc["buffers"][0]["byteLength"] = len(bin_)
                I.write_glb(path, doc, bin_)
                doc, bin_ = I.read_glb(path)
            self.assertEqual([a["name"] for a in doc["animations"]], ["Take 001", "cf_attack"])
            self.assertEqual(len(doc["accessors"]), 2)

    def test_slots_pointing_at_our_clips_count_as_missing(self):
        names = ["Idle", "cf_attack", "cf_death"]
        self.assertEqual(I.wanted_slots({"clip_spell": "-1", "clip_death": "2"}, names), {"attack", "spell", "death"})
        self.assertEqual(I.wanted_slots({"clip_spell": "0", "clip_death": "0"}, names), {"attack"})


if __name__ == "__main__":
    unittest.main()
