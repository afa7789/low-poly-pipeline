"""python3 -m unittest discover -s tests/tools/blender"""
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import depth_rule as SG_DR  # noqa: E402
import segment_sheet as SG  # noqa: E402

SHEET = ROOT / "artifacts/model-sheets/refs/n005/sheet.jpg"


class Lin:
    """Frames stand-in: both panels map a fraction (u, v) to (u - 0.5, 2 v) metres, H = 2."""
    H = 2.0

    def front_xy(self, u, v):
        return u - 0.5, 2 * v

    def left_zy(self, u, v):
        return u - 0.5, 2 * v


def joint(name, front, left):
    return {"name": name, "front": front, "left": left}


def part(name, role, front, left, bone="spine", hint=0, prop=False):
    return {"name": name, "role": role, "bone": bone, "prop": prop, "anchor": "back" if prop else "",
            "depth_hint": hint, "box_front": front, "box_left": left}


class Triangulation(unittest.TestCase):
    def test_joint_xyz_incoherence_and_mirror(self):
        joints, bad = SG.triangulate_joints([
            joint("knee.L", [0.7, 0.30], [0.6, 0.31]),
            joint("knee.R", [0.3, 0.30], None),                   # hidden in the left panel: z of the .L twin
            joint("hip.L", [0.6, 0.50], [0.5, 0.60]),             # 0.2 m = 0.1 H apart
            joint("elbow.L", [0.7, 0.4], None)], Lin())           # one view only: no xyz
        self.assertEqual(joints["knee.L"]["xyz"], [0.2, 0.61, 0.1])
        self.assertEqual(joints["knee.R"]["xyz"], [-0.2, 0.6, 0.1])
        self.assertEqual(joints["knee.R"]["z_from"], "mirror")
        self.assertIsNone(joints["elbow.L"]["xyz"])
        self.assertEqual([b["joint"] for b in bad], ["hip.L"])

    def test_boxes_and_depth_order(self):
        parts, bad = SG.triangulate_parts([
            part("torso", "torso", [0.3, 0.3, 0.7, 0.8], [0.4, 0.3, 0.6, 0.8]),
            part("tank", "prop", [0.3, 0.4, 0.7, 0.8], [0.1, 0.4, 0.3, 0.8], prop=True),     # z -0.3: behind the torso
            part("pistol", "prop", [0.6, 0.3, 0.7, 0.4], [0.7, 0.3, 0.9, 0.4], prop=True),   # z +0.3: in front
            part("lamp", "prop", [0.6, 0.2, 0.7, 0.3], None, hint=1, prop=True)], Lin())
        by = {p["name"]: p for p in parts}
        self.assertEqual(by["torso"]["box3d"], [[-0.2, 0.6, -0.1], [0.2, 1.6, 0.1]])
        self.assertEqual([by[n]["depth_order"] for n in ("torso", "tank", "pistol")], [0, -2, 2])
        self.assertEqual((by["lamp"]["box3d"], by["lamp"]["depth_order"], by["lamp"]["depth_src"]), (None, 1, "vlm"))
        self.assertEqual(bad, [])

    def test_summary_counts_types(self):
        joints, _ = SG.triangulate_joints([joint("knee.L", [0.7, 0.3], [0.6, 0.3]), joint("knee.R", [0.3, 0.3], None),
                                           joint("head_top", [0.5, 1.0], None)], Lin())
        out = SG.summary(joints, "biped")
        self.assertEqual((out["expected"], out["xyz"], out["one_view"], out["types_xyz"]), (14, 2, 1, "1/8"))


class OnePanelParts(unittest.TestCase):
    """L12-8: a part only one panel shows gets its other range from the top-carved hull, or says why it stays None."""
    torso = part("torso", "torso", [0.3, 0.3, 0.7, 0.8], [0.4, 0.3, 0.6, 0.8])             # x -.2..+.2, y .6..1.6, z -.1..+.1
    lamp = part("lamp", "prop", [0.6, 0.2, 0.7, 0.3], None, prop=True)                      # x .1..0.2, y .4..0.6: below the torso
    badge = part("badge", "prop", [0.4, 0.4, 0.5, 0.45], None, prop=True)                   # inside the torso's box
    ghost = part("ghost", "prop", None, None, prop=True)

    def run(self, top):
        import numpy as np
        g = np.stack(np.meshgrid(np.linspace(-0.3, 0.3, 13), np.linspace(0.3, 1.7, 29), np.linspace(-0.2, 0.5, 15), indexing="ij"), -1).reshape(-1, 3)
        frame = mock.Mock(iou=0.9)
        with mock.patch.object(SG_DR, "hull3", return_value=g[(g[:, 2] > 0.25) | (np.abs(g[:, 0]) < 0.2)]):
            parts, _ = SG.triangulate_parts([self.torso, self.lamp, self.badge, self.ghost], Lin(), (g, frame, None) if top else None)
        return {p["name"]: p for p in parts}

    def test_the_hull_gives_the_part_that_sticks_out_its_z_and_says_why_for_the_rest(self):
        by = self.run(top=True)
        lamp = by["lamp"]
        self.assertEqual((lamp["z_from"], lamp["box3d_src"]), ("top", "front+top"))
        self.assertGreater(lamp["box3d"][0][2], 0.2)
        self.assertEqual(lamp["box3d"][0][:2], [0.1, 0.4])
        self.assertEqual((by["badge"]["box3d"], by["badge"]["z_why"]), (None, "inside-other-parts"))
        self.assertEqual((by["ghost"]["box3d"], by["ghost"]["z_why"]), (None, "no-box"))
        self.assertNotIn("z_why", by["torso"])

    def test_without_a_top_camera_it_stays_null_and_says_so(self):
        by = self.run(top=False)
        self.assertEqual((by["lamp"]["box3d"], by["lamp"]["z_why"]), (None, "no-top"))


class Reply(unittest.TestCase):
    def test_rejects_off_ruler_and_inside_out_boxes(self):
        ok = {"joints": [joint("knee.L", [0.5, 0.5], None)], "parts": [part("t", "torso", [0.1, 0.1, 0.2, 0.2], None)], "identity": ["x"]}
        self.assertEqual(SG.check_reply("here: " + json.dumps(ok))["identity"], ["x"])
        for what, edit in (("joint", lambda d: d["joints"][0].update(front=[1.4, 0.5])),
                           ("box", lambda d: d["parts"][0].update(box_front=[0.5, 0.1, 0.2, 0.2]))):
            with self.subTest(what):
                bad = json.loads(json.dumps(ok))
                edit(bad)
                with self.assertRaises(ValueError):
                    SG.check_reply(json.dumps(bad))

    def test_schema_lists_the_family(self):
        self.assertEqual(len(SG.JOINTS["biped"]), 14)
        self.assertEqual(len(SG.JOINTS["spider"]), 16)
        s = SG.schema_of(SG.JOINTS["biped"], ["spine", "head"])
        self.assertEqual(s["properties"]["joints"]["items"]["properties"]["name"]["enum"], SG.JOINTS["biped"])
        self.assertEqual(SG.family_of("spider_high"), "spider")
        self.assertEqual(SG.family_of("drake"), "generic")


class Segment(unittest.TestCase):
    @unittest.skipUnless((pathlib.Path(__file__).resolve().parents[3] / "artifacts/model-sheets/refs/n005/sheet.jpg").exists(), "needs game data or a local sheet (make link)")
    def test_stub_vlm_end_to_end_on_n005(self):
        asked = []
        reply = {"joints": [joint("head_top", [0.5, 0.97], [0.5, 0.97]), joint("knee.L", [0.6, 0.22], [0.5, 0.22]),
                            joint("knee.R", [0.4, 0.22], None)],
                 "parts": [part("hood", "head", [0.3, 0.7, 0.7, 0.97], [0.3, 0.7, 0.7, 0.97], "head"),
                           part("torso", "torso", [0.25, 0.3, 0.75, 0.7], [0.3, 0.3, 0.7, 0.7]),
                           part("tank", "prop", [0.3, 0.5, 0.7, 0.8], [0.6, 0.5, 0.9, 0.8], prop=True)],
                 "identity": ["gas mask"]}

        def ask(model, brief, images, schema=None, check=None):
            asked.append((model, len(images), brief))
            check(json.dumps(reply))
            return json.dumps(reply)
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp)
            doc = SG.segment("n005", SHEET, ask=ask, out_dir=out, masks_dir=out / "parts")
            self.assertEqual((len(asked), asked[0][1], asked[0][0]), (1, 2, "session:opus"))
            self.assertIn("pressure tank", asked[0][2])      # the card's props reach the brief
            self.assertEqual(json.loads((out / "parts.json").read_text())["unit"], "n005")
            self.assertTrue((out / "parts-overlay.png").exists())
            self.assertTrue(list((out / "parts").glob("torso-*.png")))
        self.assertEqual(doc["joints"]["knee.R"]["z_from"], "mirror")
        self.assertTrue(all(p["zone"] for p in doc["parts"]), doc["parts"])
        torso = next(p for p in doc["parts"] if p["name"] == "torso")
        self.assertEqual(torso["depth_order"], 0)


if __name__ == "__main__":
    unittest.main()
