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


def quad_doc():
    """A small glTF quadruped (Y up, facing +Z, left = +X), metarig-like names; ears hang off
    the head with a side but point up, so they must not be taken for legs."""
    spec = [  # name, parent, translation
        ("root", None, [0, 0, 0]), ("spine", "root", [0, 1.0, -0.5]), ("spine.001", "spine", [0, 0, 1.0]),
        ("neck", "spine.001", [0, 0.2, 0.2]), ("head", "neck", [0, 0.1, 0.2]), ("jaw", "head", [0, -0.1, 0.3]),
        ("ear.L", "head", [0.1, 0.1, 0]), ("ear.L.001", "ear.L", [0, 0.1, 0]), ("ear.L.002", "ear.L.001", [0, 0.1, 0]),
        ("ear.R", "head", [-0.1, 0.1, 0]), ("ear.R.001", "ear.R", [0, 0.1, 0]), ("ear.R.002", "ear.R.001", [0, 0.1, 0]),
    ]
    for leg, parent, z in (("front_", "spine.001", 0.0), ("", "spine", 0.0)):
        for side, x in (("L", 0.2), ("R", -0.2)):
            thigh, shin = f"{leg}thigh.{side}", f"{leg}shin.{side}"
            spec += [(thigh, parent, [x, 0, z]), (shin, thigh, [0, -0.5, 0]),
                     (f"{leg}foot.{side}", shin, [0, -0.45, 0])]
    names = [n for n, *_ in spec]
    nodes = [{"name": f"{n}_{i}", "translation": t} for i, (n, _, t) in enumerate(spec)]
    for i, (_, parent, _) in enumerate(spec):
        if parent is not None:
            nodes[names.index(parent)].setdefault("children", []).append(i)
    return {"asset": {"version": "2.0"}, "nodes": nodes, "skins": [{"joints": list(range(len(nodes)))}]}


def drake_doc():
    """A Portuguese-named winged drake (coxa/perna/pe, asa, calda, pescoco, cranio) facing +Z,
    plus an IK target that must be ignored; and a fish whose tail chain starts at its head."""
    spec = [
        ("root", None, [0, 0, 0]), ("tronco", "root", [0, 1.0, -0.5]), ("peito", "tronco", [0, 0, 1.0]),
        ("pescoco", "peito", [0, 0.3, 0.3]), ("cranio", "pescoco", [0, 0.3, 0.3]), ("boca_sup", "cranio", [0, 0, 0.3]),
        ("calda_001", "tronco", [0, 0, -0.3]), ("calda_002", "calda_001", [0, 0, -0.3]),
        ("calda_003", "calda_002", [0, 0, -0.3]), ("calda_004", "calda_003", [0, 0, -0.3]),
        ("leg_IK.L", "root", [0.2, 0, 0.5]),
    ]
    for part, parent, z in (("", "peito", 0.0), ("_T", "tronco", 0.0)):
        for side, x in (("L", 0.2), ("R", -0.2)):
            coxa, perna = f"coxa{part}_{side}", f"perna{part}_{side}"
            spec += [(coxa, parent, [x, 0, z]), (perna, coxa, [0, -0.5, 0]), (f"pe{part}_{side}", perna, [0, -0.45, 0])]
    for side, x in (("L", 1), ("R", -1)):
        spec += [(f"asa_{side}", "peito", [0.2 * x, 0.2, 0]), (f"asa_02_{side}", f"asa_{side}", [0.5 * x, 0.1, 0]),
                 (f"asa_03_{side}", f"asa_02_{side}", [0.5 * x, 0, 0])]
    names = [n for n, *_ in spec]
    nodes = [{"name": f"{n}_Armature_{i}", "translation": t} for i, (n, _, t) in enumerate(spec)]
    for i, (_, parent, _) in enumerate(spec):
        if parent is not None:
            nodes[names.index(parent)].setdefault("children", []).append(i)
    return {"asset": {"version": "2.0"}, "nodes": nodes, "skins": [{"joints": list(range(len(nodes)))}]}


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


class Quadruped(unittest.TestCase):
    def test_legs_spine_and_head_are_found_and_ears_are_not_legs(self):
        doc = quad_doc()
        skel = I.Skeleton(doc)
        m = I.quadruped(skel, set(doc["skins"][0]["joints"]))
        names = {k: (skel.names[a].rsplit("_", 1)[0], skel.names[b].rsplit("_", 1)[0]) for k, (a, b) in m.items()}
        self.assertEqual(names["leg1.upper"], ("front_thigh.L", "front_shin.L"))
        self.assertEqual(names["leg4.lower"], ("shin.R", "foot.R"))
        self.assertEqual(names["spine.1"], ("spine", "spine.001"))
        self.assertEqual(names["head"], ("head", "jaw"))
        left, _, front = I.front_of_body(skel, m)
        self.assertAlmostEqual(front[2], 1.0)
        self.assertAlmostEqual(left[0], 1.0)


class Creature(unittest.TestCase):
    def names(self, family):
        doc = drake_doc()
        skel = I.Skeleton(doc)
        m, axes = I.body_map(skel, set(doc["skins"][0]["joints"]), family)
        base = lambda j: skel.names[j].split("_Armature")[0]  # noqa: E731
        return {k: (base(a), base(b)) for k, (a, b) in m.items()}, axes

    def test_a_portuguese_drake_maps_legs_wings_neck_and_tail(self):
        m, (left, _, front) = self.names("drake")
        self.assertEqual(m["leg1.upper"], ("coxa_L", "perna_L"))           # front left
        self.assertEqual(m["leg4.lower"], ("perna_T_R", "pe_T_R"))         # hind right
        self.assertEqual(m["wing2.upper"], ("asa_R", "asa_02_R"))
        self.assertEqual(m["tail.1"], ("calda_001", "calda_002"))
        self.assertEqual(m["head"], ("cranio", "boca_sup"))
        self.assertAlmostEqual(front[2], 1.0)
        self.assertAlmostEqual(left[0], 1.0)

    def test_a_two_legged_bird_takes_the_legs_nearest_its_own(self):
        m, _ = self.names("bird")
        self.assertEqual({m["leg1.upper"][0], m["leg2.upper"][0]} & {"coxa_L", "coxa_T_L"}, {m["leg1.upper"][0]})
        self.assertNotIn("leg3.upper", m)

    def test_manual_maps_find_joints_by_base_name(self):
        doc = drake_doc()
        skel = I.Skeleton(doc)
        spec = {"front": ("tronco", "peito"), "bones": {"head": ("cranio", "boca_sup")}}
        m, (_, _, front) = I.manual_map(skel, set(doc["skins"][0]["joints"]), spec)
        self.assertEqual([skel.names[j].split("_Armature")[0] for j in m["head"]], ["cranio", "boca_sup"])
        self.assertAlmostEqual(front[2], 1.0)


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
