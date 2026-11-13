"""SLOW=1 python3 -m unittest tests.tools.blender.test_hand_unit   (runs Blender, ~10 s)

The hand-made unit builder (tools/blender/hand_unit.py), through the approved Footman (units/hfoo.py)."""
import json
import os
import pathlib
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
UNIT = ROOT / "tools/blender/units/hfoo.py"
BIPED = {"root", "pelvis", "spine", "head", "arm.L", "forearm.L", "arm.R", "forearm.R",
         "thigh.L", "shin.L", "foot.L", "thigh.R", "shin.R", "foot.R"}


def read_glb(path):
    data = path.read_bytes()
    return json.loads(data[20:20 + struct.unpack("<I", data[12:16])[0]])


@unittest.skipUnless(os.environ.get("SLOW") and shutil.which("blender"), "SLOW=1: Blender, ~10 s")
class Footman(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        out = pathlib.Path(cls.tmp.name) / "hfoo.glb"
        run = subprocess.run(["blender", "-b", "--factory-startup", "-P", str(UNIT), "--", str(out)],
                             capture_output=True, text=True, check=False)
        cls.log = run.stdout
        cls.doc = read_glb(out)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_one_skinned_mesh_on_the_family_skeleton_with_its_clips(self):
        doc = self.doc
        with self.subTest("clips in the order data/models.tsv indexes them"):
            self.assertEqual([a["name"] for a in doc["animations"]],
                             ["attack", "attack2", "death", "idle", "spell", "walk"])
        with self.subTest("every biped bone is a joint"):
            joints = {doc["nodes"][j]["name"] for j in doc["skins"][0]["joints"]}
            self.assertEqual(joints, BIPED)
        with self.subTest("one mesh, one palette texture"):
            self.assertEqual((len(doc["meshes"]), len(doc["images"]), len(doc["materials"])), (1, 1, 1))
        with self.subTest("the rifle is found in the hand the sheet shows it in"):
            self.assertRegex(self.log, r"grip=\{'L': \(.*\), 'R': None\}")
        with self.subTest("triangle budget"):
            tris = sum(doc["accessors"][p["indices"]]["count"] // 3 for m in doc["meshes"] for p in m["primitives"])
            self.assertLessEqual(tris, 1200)


if __name__ == "__main__":
    unittest.main()
