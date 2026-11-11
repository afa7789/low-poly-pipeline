"""python3 -m unittest discover -s tests/tools -p 'test_rig_static.py'"""
import copy
import json
import math
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "tools"))

import assign_model_clips as AMC  # noqa: E402
import inject_clips as I  # noqa: E402
import rig_families as RF  # noqa: E402
import rig_static as R  # noqa: E402

CUBE = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
FACES = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1),
         (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]


def boxes(doc, bin_, parts):
    """A mesh of one primitive holding the boxes [(centre, half size)]; its index."""
    pos, idx = [], []
    for centre, half in parts:
        base = len(pos)
        pos += [tuple(c + h * s for c, h, s in zip(centre, half, corner)) for corner in CUBE]
        idx += [base + i for face in FACES for i in face]
    p = R.append(doc, bin_, [c for v in pos for c in v], "f", "VEC3", len(pos))
    i = R.append(doc, bin_, idx, "H", "SCALAR", len(idx))
    doc.setdefault("meshes", []).append({"primitives": [{"attributes": {"POSITION": p}, "indices": i}]})
    return len(doc["meshes"]) - 1


def tank():
    """A static tank: hull and gun in one mesh, a hatch in a node of its own (turned, moved)."""
    doc, bin_ = {"asset": {"version": "2.0"}, "scenes": [{"nodes": [0, 1]}], "nodes": [], "buffers": [{}]}, bytearray()
    body = boxes(doc, bin_, [((0, 0.5, 0), (0.6, 0.5, 1.0)), ((0, 1.2, 1.2), (0.1, 0.1, 0.6))])
    hatch = boxes(doc, bin_, [((0, 0, 0), (0.2, 0.05, 0.2))])
    doc["nodes"] = [{"name": "Body", "mesh": body},
                    {"name": "Hatch", "mesh": hatch, "translation": [0, 1.05, -0.4],
                     "rotation": [0, 0.3826834, 0, 0.9238795]}]
    doc["buffers"][0]["byteLength"] = len(bin_)
    return doc, bin_


TANK = {"front": "+z", "weights": "rigid", "row": "h06S", "omit": ("track.L", "track.R", "arm.L", "arm.R"),
        "bones": {"hull": ((0, 0.3, -0.8), (0, 0.35, 0.8)), "head": ((0, 0.85, 0.2), (0, 0.85, 1.0))},
        "regions": [("head", (-0.3, 0.3, 0.7, 1.0, 0.1, 1.1)), ("hull", R.EVERYWHERE)], "parts": {"^Hatch$": "hull"}}


def rest_of(doc, bin_):
    world = R.worlds(doc)
    return [R.rest_points(doc, bin_, world, n, doc["meshes"][m]["primitives"][k]) for n, m, k in R.primitives(doc)]


def joint_name(doc, prim, vertex):
    skin = doc["skins"][0]
    js = R.read(doc, bytes(prim[1]), prim[0]["attributes"]["JOINTS_0"])
    return doc["nodes"][skin["joints"][js[vertex][0]]]["name"]


class Static(unittest.TestCase):
    def setUp(self):
        self.doc, self.bin = tank()
        self.before = rest_of(self.doc, self.bin)
        self.bin = R.build("t", TANK, self.doc, self.bin)

    def prim(self, node):
        mesh = self.doc["nodes"][node]["mesh"]
        return self.doc["meshes"][mesh]["primitives"][0], self.bin

    def test_the_rest_pose_is_unchanged(self):
        for old, new in zip(self.before, rest_of(self.doc, self.bin)):
            self.assertLess(max(math.dist(a, b) for a, b in zip(old, new)), 1e-5)

    def test_rigid_pieces_follow_their_region_and_a_named_part_its_bone(self):
        self.assertEqual(joint_name(self.doc, self.prim(0), 0), "cf:hull")       # hull box: vertices 0-7
        self.assertEqual(joint_name(self.doc, self.prim(0), 8), "cf:head")       # gun box: vertices 8-15
        self.assertTrue(joint_name(self.doc, self.prim(1), 0).startswith("cf:hull~"))

    def test_a_mesh_in_another_frame_hangs_from_an_alias_of_the_bone(self):
        alias = next(i for i, n in enumerate(self.doc["nodes"]) if n["name"].startswith("cf:hull~"))
        hull = next(i for i, n in enumerate(self.doc["nodes"]) if n["name"] == "cf:hull")
        self.assertIn(alias, self.doc["nodes"][hull]["children"])

    def test_the_map_names_a_joint_and_an_end_for_every_bone(self):
        mark = self.doc["extras"]["cf_rig"]
        self.assertEqual(sorted(mark["map"]), ["head", "hull", "root"])
        self.assertEqual(mark["row"], "h06S")
        for joint, end in mark["map"].values():
            self.assertIn(joint, self.doc["skins"][0]["joints"])
            self.assertIn(end, self.doc["nodes"][joint]["children"])

    def test_unrigging_gives_the_glb_back(self):
        doc, bin_ = tank()
        R.unrig(self.doc, self.bin)
        self.assertEqual(json.dumps(self.doc, sort_keys=True), json.dumps(doc, sort_keys=True))


class Smooth(unittest.TestCase):
    def test_weights_take_the_two_nearest_bones_of_the_vertex_side(self):
        box = R.Box([(-1, 0, -1), (1, 2, 1)], "+z")
        bones = {"arm.L": ((0.5, 1.5, 0), (1, 1.5, 0), 1), "arm.R": ((-0.5, 1.5, 0), (-1, 1.5, 0), -1),
                 "spine": ((0, 0.5, 0), (0, 1.5, 0), 0)}
        (w,) = R.smooth([(0.9, 1.5, 0)], box, bones)
        self.assertEqual({b for b, _ in w}, {"arm.L", "spine"})
        self.assertAlmostEqual(sum(v for _, v in w), 1.0)
        self.assertGreater(dict(w)["arm.L"], 0.9)


class Rerun(unittest.TestCase):
    def test_same_spec_skips_a_new_one_replaces_and_the_rig_files_match(self):
        with tempfile.TemporaryDirectory() as d:
            old, R.ASSETS = R.ASSETS, pathlib.Path(d)
            try:
                doc, bin_ = tank()
                I.write_glb(pathlib.Path(d) / "t.glb", doc, bin_)
                self.assertTrue(R.rig("t", TANK).startswith("rigged"))
                self.assertEqual(R.rig("t", TANK), "up to date")
                moved = copy.deepcopy(TANK)
                moved["bones"]["head"] = ((0, 0.9, 0.2), (0, 0.9, 1.0))
                self.assertTrue(R.rig("t", moved).startswith("rigged"))
                doc, _ = I.read_glb(pathlib.Path(d) / "t.glb")
                rig = (pathlib.Path(d) / "t.rig").read_text().split("\n")
                joints = (pathlib.Path(d) / "t.joints").read_text().split()
            finally:
                R.ASSETS = old
        self.assertEqual(len(doc["nodes"]), 2 + 3 * 2 + 1)                  # 3 joints, 3 ends, 1 alias
        self.assertEqual(rig[1], f"{len(doc['nodes'])} {len(doc['skins'][0]['joints'])} 2")
        self.assertEqual(joints, ["-1", "-1"])


class Attached(unittest.TestCase):
    def test_a_loose_gun_joins_the_tanks_own_skin_under_our_root(self):
        doc, bin_ = tank()
        doc["nodes"].append({"name": "Root", "translation": [0, 0.5, 0]})
        doc["scenes"][0]["nodes"].append(2)
        prim = doc["meshes"][0]["primitives"][0]
        count = doc["accessors"][prim["attributes"]["POSITION"]]["count"]
        prim["attributes"]["JOINTS_0"] = R.append(doc, bin_, [0] * 4 * count, "B", "VEC4", count)
        prim["attributes"]["WEIGHTS_0"] = R.append(doc, bin_, [1.0, 0, 0, 0] * count, "f", "VEC4", count)
        ibm = R.append(doc, bin_, [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, -0.5, 0, 1], "f", "MAT4", 1)
        doc["skins"] = [{"joints": [2], "inverseBindMatrices": ibm}]
        doc["nodes"][0]["skin"] = 0
        spec = {**TANK, "attach": {"hull": "Root"}, "parts": {"^Hatch$": "head"}}
        before = rest_of(doc, bin_)
        world_root = R.worlds(doc)[2]
        bin_ = R.build("t", spec, doc, bin_)
        for old, new in zip(before, rest_of(doc, bin_)):
            self.assertLess(max(math.dist(a, b) for a, b in zip(old, new)), 1e-5)
        self.assertLess(max(abs(a - b) for ra, rb in zip(world_root, R.worlds(doc)[2]) for a, b in zip(ra, rb)), 1e-6)
        mark = doc["extras"]["cf_rig"]
        self.assertEqual(mark["map"]["hull"][0], 2)                           # their Root plays our hull
        self.assertEqual(doc["skins"][0]["joints"][0], 2)                     # their joints keep their slots


class Specs(unittest.TestCase):
    def test_every_spec_names_bones_of_its_family(self):
        for unit, spec in R.RIGS.items():
            family = R.family_of(unit, spec)
            bones = set(RF.bones(family))
            laid = set(R.layout(family, spec))
            self.assertLessEqual(set(spec.get("bones", {})), bones, unit)
            self.assertLessEqual(set(spec.get("omit", ())), bones, unit)
            used = set(spec.get("attach", {})) | {b for b, _ in spec.get("regions", [])} | \
                set(spec.get("parts", {}).values())
            self.assertLessEqual(used, laid, unit)

    def test_chains_mirror_the_left_side(self):
        got = R._chains({"arm.L forearm.L": [(1, 2, 3), (2, 2, 3), (3, 1, 3)], "leg1.upper": [(1, 1, 0), (1, 0, 0)]},
                        {"leg1": "leg2"})
        self.assertEqual(got["forearm.R"], ((-2, 2, 3), (-3, 1, 3)))
        self.assertEqual(got["leg2.upper"], ((-1, 1, 0), (-1, 0, 0)))


class Inject(unittest.TestCase):
    def test_our_turns_reach_the_rigged_gun_and_a_strike_ends_at_rest(self):
        with tempfile.TemporaryDirectory() as d:
            old, R.ASSETS, I.ASSETS = R.ASSETS, pathlib.Path(d), pathlib.Path(d)
            try:
                doc, bin_ = tank()
                I.write_glb(pathlib.Path(d) / "t.glb", doc, bin_)
                R.rig("t", TANK)
                self.assertEqual(I.plan("t")[0], "tracked")                    # the registry row of "h06S"
                anims = {a[0]: a for a in I.build("t", pathlib.Path(d) / "t.glb", {"attack", "death"})}
                gun = I.read_glb(pathlib.Path(d) / "t.glb")[0]["extras"]["cf_rig"]["map"]["head"][0]
            finally:
                R.ASSETS = I.ASSETS = old
        track = anims["attack"][2][gun]
        self.assertGreater(max(1 - abs(q[3]) for q in track), 0.005)           # the recoil turns it
        self.assertLess(1 - abs(track[-1][3]), 1e-6)

    def test_closing_and_slerp(self):
        self.assertEqual(I._closing(0, 10), 0.0)
        self.assertEqual(I._closing(9, 10), 1.0)
        self.assertEqual(I._closing(3, 10), 0.0)
        half = I.slerp([0, 0, 0, 1], [0, 0, 1, 0], 0.5)
        self.assertAlmostEqual(half[2], math.sqrt(0.5))

    def test_a_model_with_no_clips_lacks_every_slot(self):
        row = {"clip_spell": "2", "clip_death": "1"}
        self.assertEqual(I.wanted_slots(row, []), {"attack", "spell", "death"})
        self.assertEqual(I.wanted_slots(row), {"attack"})

    def test_an_anchored_bone_is_measured_from_the_clips_first_pose(self):
        got = I._anchored({"leg1.upper": [0, -1, 0], "head": [0, 0, 1]}, {"leg1.upper": [0, 0, 1], "head": [1, 0, 0]},
                          ("leg1",))
        self.assertEqual(got, {"leg1.upper": [0, 0, 1], "head": [0, 0, 1]})


class Registry(unittest.TestCase):
    def test_a_model_rigged_like_another_unit_takes_its_row(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "x.glb"
            I.write_glb(path, {"asset": {"version": "2.0"}, "extras": {"cf_rig": {"row": "o001"}},
                               "buffers": [{"byteLength": 0}]}, bytearray())
            self.assertEqual(AMC.registry_row({"o001": "row"}, "x", path), "row")
            self.assertIsNone(AMC.registry_row({"o001": "row"}, "x", pathlib.Path(d) / "none.glb"))


if __name__ == "__main__":
    unittest.main()
