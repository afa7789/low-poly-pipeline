"""python3.14 -m unittest discover -s tests/tools/blender   (SLOW=1 adds the n005 fit)"""
import json
import os
import pathlib
import subprocess
import sys
import unittest

import numpy as np
import torch

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import fit_grad as G  # noqa: E402
import fit_spec as F  # noqa: E402
import lathe_limb  # noqa: E402
import silhouette  # noqa: E402

RUNS = ROOT / "artifacts/model-sheets/runs/draft"
REFS = ROOT / "artifacts/model-sheets/refs"


def part(bone, kind, dims, at, **opts):
    return [bone, kind, list(dims), list(at), "iron", opts]


# one part per kind/variant the torch twin has that the three real specs do not already carry
SYNTH = [part("arm.L", "box", (.3, .6, .2), (.5, 1.5, .1), rot=[10, 20, 30]),
         part("spine", "prism", (.3, .2, .8), (0, 1, 0), axis="fwd", sides=6, scale=[1.2, .8], spin=15),
         part("arm.R", "frustum", (.4, .5, .3), (-.5, 1, 0), sides=8, top=[.6, .7], shift=[.05, .02], rot=[5, 15, -10]),
         part("head", "dome", (.3, .4), (0, 2, 0), top=.5, axis="side", rot=20),
         part("leg.L", "cyl", (.1, .7), (.2, .4, 0), axis="up", sides=6),
         part("leg.R", "wheel", (.3, .1), (-.2, .4, 0), tilt=12),
         part("body", "ring", (.5, .1, .2), (0, 1, 0), tilt=8, spin=30),
         part("leg.L", "prism", (.1, .08, .5), (0, 0, 0), **{"from": [.2, 1, 0], "to": [.3, .2, .3], "axis": "up"}),
         part("leg.L", "box", (.2, .5, .2), (0, 0, 0), **{"from": [.2, 1, 0], "to": [.3, .2, .3], "fit": False}),
         part("spine", "lathe", (.4, 1.0), (0, 1, 0), profile=[[.8, .6, 0, 0, 0], [1, .8, .1, .05, .3], [.5, .5, 0, 0, 1]],
              corner=.5),
         part("spine", "lathe", (.4, 1.0), (0, 1, 0), profile=[[.8, .6, 0, 0], [1, .8, .1, .05], [.5, .5, 0, 0]], axis="z"),
         part("spine", "lathe", (.4, 1.0), (0, 1, 0), profile=[.5, .9, 1, .8, .6, .4], squash=1.2, sides=6),
         part("arm.L", "limb", (.1, .08, .06), (0, 0, 0), **{"from": [.5, 1.5, 0], "to": [.6, .7, .2], "knee": [.4, .05, -.03]}),
         part("spine", "plate", (.6, .8, .1), (0, 1, 0), profile=[[0, 0], [1, .1], [.9, 1], [.1, .9]], axis="left", bevel=.1,
              rot=[0, 10, 20])]


def real_parts(unit, version="v11-r1"):
    doc = json.loads((RUNS / unit / version / "spec.json").read_text())
    F.RF.scale_rig(doc.get("rig", "biped"), doc.get("rig_measure"))
    lathe_limb.set_rig(doc.get("rig", "biped"), doc.get("bones"))
    return doc["parts"]


class Parity(unittest.TestCase):
    def setUp(self):
        self.families = dict(F.RF.FAMILIES)    # real_parts scales the rigs of n00U / n017: the other suites want the fixed tables

    def tearDown(self):
        F.RF.FAMILIES.clear()
        F.RF.FAMILIES.update(self.families)
        F.RF._drop_caches()
        lathe_limb.set_rig("biped")

    def check(self, p, rng, hood=False):
        names = F.extras_of(p, hood)
        for mirror in (False, True):
            x = rng.uniform(-1, 1, F.group_size(p, names))
            want = F.part_points(F.moved(p, x, 2.0, mirror, names))
            st = G.dynamic(p, torch.as_tensor(x, dtype=G.DT), 2.0, mirror, names)
            got = G.POINTS[p[1]](p, st).numpy()
            self.assertEqual(got.shape, want.shape)
            np.testing.assert_allclose(got, want, atol=1e-4, err_msg=f"{p[0]} {p[1]} mirror={mirror}")

    def test_points_match_numpy(self):
        """the torch twin of moved + part_points equals the numpy one (error < 1e-4) at a random pose, for every kind"""
        rng = np.random.default_rng(3)
        for p in SYNTH:
            with self.subTest(kind=p[1], bone=p[0]):
                self.check(p, rng, hood=p[1] == "dome")
        for unit in ("n005", "n00U", "n017"):
            for p in real_parts(unit):
                with self.subTest(unit=unit, kind=p[1], bone=p[0]):
                    self.check(p, rng)


class Registered(unittest.TestCase):
    def test_flag_is_on_both_entry_points(self):
        """--fit-grad is reachable from fit_spec.py and from spec_pipeline.py (the composed CLIs, not only fit())"""
        for tool in ("fit_spec.py", "spec_pipeline.py"):
            with self.subTest(tool=tool):
                help_text = subprocess.run([sys.executable, str(ROOT / "tools/blender" / tool), "--help"],
                                           capture_output=True, text=True).stdout
                self.assertIn("--fit-grad", help_text)


def scene_of(parts, truth, views=("front", "left", "back")):
    """(Scene, groups, bounds) fitting `parts` to the masks of `truth`."""
    concept = {v: m for v, (m, _) in F.Proxy({}, views).masks(truth).items()}
    proxy = F.Proxy(concept, views)
    groups = F.groups_of(parts, list(range(len(parts))))
    extra, bounds = F.search_space(parts, groups, None, {}, set(), True)
    return G.Scene(proxy, parts, groups, extra, 2.0), bounds


class Descent(unittest.TestCase):
    parts = [part("spine", "box", (.8, 1.2, .5), (0, 1.2, 0)),
             part("arm.L", "box", (.25, .8, .25), (.6, 1.2, 0), rot=[0, 0, 10]),
             part("arm.R", "box", (.25, .8, .25), (-.6, 1.2, 0), rot=[0, 0, -10])]

    def test_adam_step_reduces_the_loss_and_twins_stay_mirrored(self):
        truth = [part("spine", "box", (.8, 1.2, .5), (0, 1.2, 0)),
                 part("arm.L", "box", (.3, .9, .25), (.65, 1.2, 0), rot=[0, 0, 10]),
                 part("arm.R", "box", (.3, .9, .25), (-.65, 1.2, 0), rot=[0, 0, -10])]
        scene, bounds = scene_of(self.parts, truth)
        x = torch.zeros(scene.size, requires_grad=True)
        before = scene.loss(x, 2.0)
        before.backward()
        self.assertTrue(x.grad.abs().sum() > 0)
        after = scene.loss((x - 0.05 * x.grad / x.grad.abs().max()).detach(), 2.0)
        self.assertLess(float(after.detach()), float(before.detach()))
        pts = scene.points(torch.rand(scene.size) * 2 - 1)
        left, right = (np.sort(pts[i].numpy() * [sx, 1, 1], axis=0) for i, sx in ((1, 1), (2, -1)))
        np.testing.assert_allclose(left, right, atol=1e-5)       # arm.R is arm.L seen in a mirror, whatever x is


@unittest.skipUnless(os.environ.get("SLOW") and (REFS / "n005/sheet.jpg").exists(), "SLOW=1")
class SlowFit(unittest.TestCase):
    def test_n005_grad_fit_raises_the_gated_proxy_iou(self):
        doc = json.loads((RUNS / "n005/v11-r1/spec.json").read_text())
        tilt = json.loads((RUNS / "n005/v11-r1/silhouette.json").read_text())["tilt"]
        tilts = {v: tuple(c) if isinstance(c, list) else c for v, c in tilt.items()}
        out, report = F.fit(doc, REFS / "n005/sheet.jpg", margin=0.1, tilts=tilts, seconds=90, grad=True)   # v11-r1 passes every gate: margin 0.1 makes the views fail
        self.assertGreater(report["grad_steps"], 0)
        self.assertTrue(report["changed"])
        gated = [v for v in silhouette.gates_for(doc.get("rig")) if v in report["after"]]
        mean = lambda ious: sum(ious[v] for v in gated) / len(gated)  # noqa: E731
        self.assertGreater(mean(report["after"]), mean(report["before"]))
        self.assertEqual(len(out["parts"]), len(doc["parts"]))


if __name__ == "__main__":
    unittest.main()
