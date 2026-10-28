"""python3.14 -m unittest discover -s tests/tools/blender"""
import os
import pathlib
import sys
import unittest

import numpy as np
import torch

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import deform_to_sheet as D  # noqa: E402
import optimize_verts as O  # noqa: E402
import silhouette as S  # noqa: E402
import soft_sil as SS  # noqa: E402
from test_deform_to_sheet import POS, TRI, panel  # noqa: E402

FRONT = D.View("front", np.array([1.0, 0, 0]), np.array([0, 0, 1.0]), 1, panel(1.15), True)
RUN = ROOT / "artifacts/model-sheets/runs/draft/n005/v11-r1"
SHEET = ROOT / "artifacts/model-sheets/refs/n005/sheet.jpg"


def soft_value(pos, view=FRONT, **kw):
    return 1 - SS.loss(pos, torch.as_tensor(TRI), view, **kw).item()


class TestSoftSil(unittest.TestCase):
    def test_project_is_the_hard_frame(self):
        for mirror in (1, -1):
            view = D.View("front", FRONT.ru, FRONT.rv, mirror, FRONT.concept, True)
            hard = D.frame(view.uv(POS), mirror)[0](view.uv(POS))
            np.testing.assert_allclose(SS.project(torch.tensor(POS), view).numpy(), hard, atol=1e-9)

    def test_tau_to_zero_is_the_hard_raster(self):
        hard = O.Ctx(FRONT, POS, TRI).iou
        for kw in ({}, {"dist": "uniform"}, {"dist": "gamma_inv"}, {"agg": "yager2"}):
            with self.subTest(**kw):
                self.assertLess(abs(soft_value(torch.tensor(POS), tau=0.1, ss=4, **kw) - hard), 0.01)

    def test_gradient_descends(self):
        pos = torch.tensor(POS, requires_grad=True)
        before = SS.loss(pos, torch.as_tensor(TRI), FRONT, tau=1.0)
        before.backward()
        self.assertGreater(pos.grad.abs().max().item(), 0)
        step = pos.detach() - 0.05 * pos.grad / pos.grad.norm()
        self.assertLess(SS.loss(step, torch.as_tensor(TRI), FRONT, tau=1.0).item(), before.item())

    def test_asym_has_one_term_per_colour(self):
        c = torch.zeros(8, 8)
        c[:, :4] = 1
        for name, mask, red, green in (("only red", c * 0.5, 0.5, 0.0), ("only green", torch.ones(8, 8), 0.0, 0.5)):
            with self.subTest(name):
                self.assertAlmostEqual(SS.soft_asym(mask, c, 1, 0).item(), red, places=6)
                self.assertAlmostEqual(SS.soft_asym(mask, c, 0, 1).item(), green, places=6)
        self.assertAlmostEqual(SS.soft_asym(c, c, 3, 5).item(), 0.0, places=6)

    def test_asym_weights_come_from_the_gates(self):
        self.assertEqual(SS.asym_weights("top"), (1.0, 1.0))
        red, green = SS.asym_weights("left")        # caps .20 / .15: the green is dearer
        self.assertAlmostEqual(red / green, S.SPILL_MAX["left"] / S.UNCOVERED_MAX["left"])
        self.assertAlmostEqual(red + green, 2.0)

    def test_asym_gradient_descends(self):
        pos = torch.tensor(POS, requires_grad=True)
        tri = torch.as_tensor(TRI)
        before = SS.loss(pos, tri, FRONT, tau=1.0, mode="asym")
        before.backward()
        self.assertGreater(pos.grad.abs().max().item(), 0)
        step = pos.detach() - 0.05 * pos.grad / pos.grad.norm()
        self.assertLess(SS.loss(step, tri, FRONT, tau=1.0, mode="asym").item(), before.item())
        with self.assertRaises(ValueError):
            SS.soft_iou(torch.zeros(2, 2), torch.ones(2, 2), mode="nope")


@unittest.skipUnless(os.environ.get("SLOW") and SHEET.exists(), "SLOW=1: a real clay, 6 views, ~10 s")
class RealClay(unittest.TestCase):
    def test_six_views_match_the_hard_raster(self):
        pos, tri, views = SS.run_views(RUN, SHEET)
        p, t = torch.tensor(pos, dtype=torch.float32), torch.as_tensor(tri)
        self.assertEqual(len(views), 6)
        for v in views:
            with self.subTest(v.name):
                hard = S.iou(v.concept, D.view_state(pos, tri, v)[1])
                self.assertLess(abs(1 - SS.loss(p, t, v, tau=0.5).item() - hard), 0.01)


if __name__ == "__main__":
    unittest.main()
