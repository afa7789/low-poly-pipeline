"""python3 -m unittest discover -s tests/tools/blender"""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import preflight as PF  # noqa: E402
import rig_families as RF  # noqa: E402


def spider_spec():
    """One prism per spider bone, laid along the bone so every joint touches."""
    parts = []
    for name, _, head, tail in RF.FAMILIES["spider"]:
        if name == "root":
            continue
        mid = [(head[i] + tail[i]) / 2 for i in range(3)]
        mat = ["iron", "darkiron", "brass"][len(parts) % 3]
        r = 0.5 if name == "body" else 0.06     # the body is the mass the legs root in
        parts.append([name, "prism", [r, r, 0.5], mid, mat,
                      {"sides": 6, "from": list(head), "to": list(tail)}])
    return {"rig": "spider", "parts": parts}


def run(spec, kind="mass"):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(spec, f)
    return subprocess.run([sys.executable, str(ROOT / "tools/blender/preflight.py"), f.name, kind],
                          capture_output=True, text=True).stdout


class Family(unittest.TestCase):
    def test_spider_skips_biped_landmarks(self):
        out = run(spider_spec())
        self.assertIn("spider: missing none", out)
        for rule in ("shoulder_span", "fist_span", "stance", "feet_mass"):
            self.assertNotIn(rule, out)

    def test_missing_leg_is_reported(self):
        spec = spider_spec()
        spec["parts"] = [p for p in spec["parts"] if p[0] != "leg5.lower"]
        self.assertIn("missing ['leg5.lower']", run(spec))

    def test_spec_without_rig_is_a_biped(self):
        doc = {"parts": [[name, "prism", [0.1, 0.1, 0.5], [0, 1, 0], "iron", {"from": list(h), "to": list(t)}]
                         for name, _, h, t in RF.BIPED if name != "root"]}
        self.assertIn("shoulder_span", run(doc))          # no "rig" key: biped rules apply


class Palette(unittest.TestCase):
    def test_spec_palette_slots_are_valid_materials(self):
        spec = spider_spec()
        names = ["chitin", "moss", "eye"]
        for i, part in enumerate(spec["parts"]):
            part[4] = names[i % 3]
        self.assertIn("materials      FAIL", run(spec))
        spec["palette"] = {"chitin": {"surface": "chitin", "color": "#4E3E39"},
                           "moss": {"surface": "fur", "color": "#62794C"},
                           "eye": {"surface": "glow", "color": "#B3DEAB"}}
        self.assertIn("materials      PASS", run(spec))


class Floating(unittest.TestCase):
    def test_detached_child_is_flagged(self):
        parts = spider_spec()["parts"]
        loose = [p for p in parts if p[0] == "leg2.lower"][0]
        loose[5] = {}
        loose[3] = [3.0, 0.3, 3.0]          # far from leg2.upper
        self.assertEqual(PF.floating_parts(parts, RF.parents("spider")), ["leg2.lower"])


if __name__ == "__main__":
    unittest.main()
