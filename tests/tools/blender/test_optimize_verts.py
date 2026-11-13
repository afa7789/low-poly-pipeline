"""python3.14 -m unittest discover -s tests/tools/blender"""
import pathlib
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import deform_to_sheet as D
import mesh_lint as ML
import optimize_verts as O
from test_deform_to_sheet import POS, TRI, panel, write_glb

FILE = (np.arange(len(POS)), TRI)          # one file vertex per welded one
FRONT = D.View("front", np.array([1.0, 0, 0]), np.array([0, 0, 1.0]), 1, panel(1.15), True)


def problem(views=(FRONT,)):
    return O.Problem(POS, TRI, list(views), np.zeros_like(POS), FILE)


class TestOptimizeVerts(unittest.TestCase):
    def test_stamp_is_reversible(self):
        cnt = np.zeros((40 * O.SS, 40 * O.SS), np.int16)
        tri = np.array([[5.2, 5.1], [20.7, 8.3], [11.4, 30.9]])
        blit(cnt, tri, 1)
        self.assertGreater(cnt.sum(), 0)
        blit(cnt, tri, -1)
        self.assertEqual(cnt.sum(), 0)

    def test_body_is_the_largest_component(self):
        tri = np.vstack([TRI, TRI[:4] + len(POS)])           # a second, smaller shell: a prop
        body = O.body_mask(tri, 2 * len(POS))
        self.assertTrue(body[:len(POS)].all() and not body[len(POS):].any())

    def test_gradient_pushes_a_narrow_box_outward(self):
        prob = problem()
        _value, ctxs, _ = prob.evaluate(prob.pos0)
        side = np.flatnonzero(np.isclose(prob.pos0[:, 0], 0.5 / 2.0) & (prob.pos0[:, 2] > 0.1))
        g = O.iou_gradient(ctxs[0], prob.pos0, TRI, side, prob.rings)
        self.assertTrue((g[:, 0] < 0).all())                 # d(1 - IoU)/dx < 0 on the right wall: moving right helps
        self.assertTrue(np.allclose(g[:, 1], 0))             # depth is invisible in the front view

    def test_soft_gradient_points_where_the_finite_difference_does(self):
        prob = problem()
        _, ctxs, _ = prob.evaluate(prob.pos0)
        # the right wall: the forward difference only sees outward moves there (the left wall's helpful move is -x)
        free = np.flatnonzero(np.isclose(prob.pos0[:, 0], 0.25) & (prob.pos0[:, 2] > 0.1) & (prob.pos0[:, 2] < 0.9))
        fd = O.iou_gradient(ctxs[0], prob.pos0, TRI, free, prob.rings)
        soft = O.soft_gradient(ctxs, prob.pos0, TRI)[free]
        cos = (fd * soft).sum() / (np.linalg.norm(fd) * np.linalg.norm(soft))
        self.assertGreater(cos, 0.5)

    def test_one_soft_step_lowers_the_hard_loss(self):
        prob = problem()
        value, ctxs, _ = prob.evaluate(prob.pos0)
        free = prob.body
        step = O.descent_step(prob, prob.gradient(prob.pos0, ctxs, np.flatnonzero(free)), free, np.ones(len(POS), bool))
        best = O.search(prob, prob.pos0, step, value, ctxs, {"unsafe": 0, "worse": 0})
        self.assertIsNotNone(best)
        self.assertGreater(best[1][0].iou, ctxs[0].iou)

    def test_grad_switch_rejects_unknown(self):
        prob = problem()
        _, ctxs, _ = prob.evaluate(prob.pos0)
        with mock.patch.object(O, "GRAD", "nope"), self.assertRaises(ValueError):
            prob.gradient(prob.pos0, ctxs, np.flatnonzero(prob.body))

    def test_asym_loss_term_and_step(self):
        prob = problem()
        with mock.patch.object(O, "LOSS", "asym"):
            value, ctxs, terms = prob.evaluate(prob.pos0)
            w = O.view_weights("front")
            self.assertAlmostEqual(terms["iou"], ctxs[0].asym(*w))
            free = prob.body
            step = O.descent_step(prob, prob.gradient(prob.pos0, ctxs, np.flatnonzero(free)), free, np.ones(len(POS), bool))
            best = O.search(prob, prob.pos0, step, value, ctxs, {"unsafe": 0, "worse": 0})
            self.assertIsNotNone(best)
            self.assertLess(best[2]["iou"], terms["iou"])
            with mock.patch.object(O, "GRAD", "fd"), self.assertRaises(ValueError):
                O.view_weights("front")

    def test_tau_schedule_falls_with_progress(self):
        with mock.patch.object(O, "TAU_SCHEDULE", (4, 2, 1, 0.5, 0.5)):
            taus = [O.tau_at(p / 20) for p in range(21)]
            self.assertEqual((taus[0], taus[-1]), (4, 0.5))
            self.assertEqual(taus, sorted(taus, reverse=True))
            self.assertEqual(O.next_level(0.05), 0.2)
            self.assertIsNone(O.next_level(0.9))
        self.assertEqual(O.tau_at(0.3), O.TAU)             # no schedule: the constant

    def test_annealed_gradient_still_descends(self):
        prob = problem()
        _, ctxs, _ = prob.evaluate(prob.pos0)
        with mock.patch.object(O, "DIST", "gamma_inv"):
            g = prob.gradient(prob.pos0, ctxs, np.flatnonzero(prob.body), tau=4.0)
        self.assertTrue(np.isfinite(g).all() and np.abs(g).max() > 0)

    def test_optimize_raises_iou_and_keeps_faces(self):
        panels = {"front": panel(1.15), "left": panel(1.0), "back": panel(1.15)}
        with mock.patch.object(O.S, "SPILL_W", 1.0), mock.patch.object(O, "make_views", return_value=[
                D.View(n, *np.array(D.FRONT_AXES[n], float), 1, p, True) for n, p in panels.items()]):
            new, rep = O.optimize(POS, TRI, np.zeros_like(POS), FILE, "unused.jpg", seconds=20, iters=3)
        self.assertGreater(rep["after"]["front"]["iou"], rep["before"]["front"]["iou"] + 0.03)
        self.assertLess(rep["objective"][1], rep["objective"][0])
        self.assertEqual(rep["turned"], 0)
        self.assertTrue(np.all(new[:8, 2] == 0))              # the sole stays on the ground
        self.assertLessEqual(rep["slivers_after"], rep["slivers_before"] + 1e-9)

    def test_ctx_cost_prices_spill_dearer_and_is_one_minus_iou_at_one(self):
        prob = problem()
        ctx = prob.evaluate(prob.pos0)[1][0]
        with mock.patch.object(O.S, "SPILL_W", 1.0), mock.patch.object(O.S, "BARE_W", 1.0):
            self.assertAlmostEqual(ctx.cost, 1 - ctx.iou)
        spill = (np.maximum(ctx.cov - ctx.c, 0).sum() > 0, np.maximum(ctx.c - ctx.cov, 0).sum() > 0)
        self.assertNotEqual(*spill)                        # the fixture is all bare or all spill: the weight moves the cost one way
        with mock.patch.object(O.S, "SPILL_W", 3.0):
            heavy = ctx.cost
        self.assertEqual(heavy > ctx.cost + 1e-9, spill[0])

    def test_repair_refuses_a_flip(self):
        prob = problem()
        step = np.zeros_like(POS)
        step[16:24, 0] = -3.0                                 # the top ring dragged through the other side
        sliver_old = O.slivers(prob, prob.pos0)
        new, ok = O.repaired(prob, prob.pos0, step / 2.0, sliver_old)
        self.assertTrue(ok)                                    # repaired: the spoiled faces' vertices stayed
        self.assertFalse(O.spoiled(prob, new, sliver_old).any())

    def test_settled_pulls_a_crease_back(self):
        prob = problem()
        pos = prob.pos0.copy()
        self.assertTrue(np.array_equal(O.settled(prob, prob.pos0, pos), pos))        # nothing new: untouched
        pos[20] = [0.0, 0.0, 0.5]                                                  # a vertex pushed into the box
        self.assertGreaterEqual(O.creased(prob, O.settled(prob, prob.pos0, pos)).min(), 0.0)

    def test_rts_axes_at_the_front(self):
        right, up = O.rts_axes(0, 0)
        self.assertTrue(np.allclose(right, [1, 0, 0]) and np.allclose(up, [0, 0, 1]))
        right, up = O.rts_axes(45, 0)
        self.assertGreater(up[1], 0)                           # a camera above the front sees the top face upward

    def test_run_writes_report_and_keeps_every_other_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = pathlib.Path(tmp, "a.glb"), pathlib.Path(tmp, "b.glb")
            write_glb(src)
            with mock.patch.object(O, "make_views", return_value=[FRONT]):
                rep = O.run(src, "unused.jpg", out, seconds=10, iters=1)
            self.assertTrue(out.with_suffix(".verts.json").exists())
            self.assertEqual(rep["vertices"], len(POS))
            (_, da), (jb, db) = ML.read_glb(src), ML.read_glb(out)
            self.assertEqual(da[2 * 2 * len(POS) * 12:], db[2 * 2 * len(POS) * 12:])      # indices after positions and normals
            self.assertTrue(np.allclose(ML.accessor(jb, db, 0)[:len(POS)], ML.accessor(jb, db, 0)[len(POS):]))

    def test_pinned_cams_are_the_gates(self):
        """L12-1: the vertex optimiser shoots top and rts from the cameras the gate chose, not from its own sweep."""
        panels = {"top": panel(1.15, 1.0)}
        gate = {"top": {"iou": .8, "tilt": 40}, "rts": {"iou": .8, "tilt": [35, -45]}}
        cams = {v: tuple(r["tilt"]) if isinstance(r["tilt"], list) else r["tilt"] for v, r in gate.items()}
        with mock.patch.object(O.S, "framed_panels", return_value=panels), mock.patch.object(O, "rts_view") as rts:
            free = O.make_views(POS, TRI, "unused.jpg", ("top", "rts"), "unit")
            pinned = O.make_views(POS, TRI, "unused.jpg", ("top", "rts"), "unit", cams)
        self.assertTrue(np.allclose(pinned[0].rv, D.tilted_axes("top", 40)[1]))
        self.assertFalse(np.allclose(free[0].rv, D.tilted_axes("top", 40)[1]))
        self.assertEqual(rts.call_args_list[1].args[3], (35, -45))
        self.assertIsNone(rts.call_args_list[0].args[3])

    def test_optimize_with_every_view_under_view_min_leaves_the_mesh(self):
        with mock.patch.object(O, "make_views", return_value=[FRONT]), mock.patch.object(O, "VIEW_MIN", 1.01):
            new, rep = O.optimize(POS, TRI, np.zeros_like(POS), FILE, "unused.jpg", ("front",), 1, 5.0)
        self.assertTrue(np.array_equal(new, POS))
        self.assertEqual((rep["views"], rep["skipped"], rep["steps"]), ([], ["front"], 0))
        for key in ("steps", "seconds", "objective", "slivers_before", "slivers_after", "before", "after"):       # what stage_shape and main read
            self.assertIn(key, rep)

    def test_optimize_reports_the_cams_it_used(self):
        cams = {"top": 40, "rts": (35, -45)}
        with mock.patch.object(O, "make_views", return_value=[FRONT]) as mv:
            rep = O.optimize(POS, TRI, np.zeros_like(POS), FILE, "unused.jpg", ("front", "top"), 1, 5.0, "unit", cams)[1]
        self.assertEqual(mv.call_args.args[-1], cams)
        self.assertEqual(rep["cams"], {"top": 40})

    def test_rts_view_pins_the_camera(self):
        with tempfile.TemporaryDirectory() as tmp:
            sheet = pathlib.Path(tmp, "sheet.jpg")
            pathlib.Path(tmp, "sheet-rts.jpg").write_bytes(b"x")
            with mock.patch.object(O.S, "rts_path", return_value=pathlib.Path(tmp, "sheet-rts.jpg")), \
                    mock.patch.object(O.S, "foreground", return_value=panel(1.15)):
                view = O.rts_view(POS, TRI, sheet, (35, -45))
        self.assertTrue(np.allclose(view.ru, O.rts_axes(35, -45)[0]))

    def test_apply_needs_both_switches(self):
        self.assertIsNone(O.apply("x.glb", SimpleNamespace(fit_verts=True, union_body=False)))
        self.assertIsNone(O.apply("x.glb", SimpleNamespace(fit_verts=False, union_body=True)))


def blit(cnt, tri, sign):
    lo, mask = O.stamp(tri)
    O.blit(cnt, np.zeros(2, int), lo, mask, sign)


class TestDihedral(unittest.TestCase):
    @staticmethod
    def bumped_grid(lift=0.3):
        """3x3 vertex grid in z=0 (8 triangles) with the centre vertex lifted: gentle dihedrals on every interior edge."""
        pos = np.array([[x, y, 0.0] for y in range(3) for x in range(3)], float)
        pos[4, 2] = lift
        quads = [(0, 1, 4, 3), (1, 2, 5, 4), (3, 4, 7, 6), (4, 5, 8, 7)]
        return pos, np.array([t for a, b, c, d in quads for t in ((a, b, c), (a, c, d))])

    def test_cube_edges_at_90_degrees_are_not_selected(self):
        faces = O.flat_edges(POS, TRI)
        n = np.cross(POS[TRI[:, 1]] - POS[TRI[:, 0]], POS[TRI[:, 2]] - POS[TRI[:, 0]])
        n /= np.linalg.norm(n, axis=1, keepdims=True)
        self.assertLess(len(faces), 3 * len(TRI) // 2)                       # the box's creases are out
        self.assertTrue((np.einsum("ed,ed->e", n[faces[:, 0]], n[faces[:, 1]]) > 0.99).all())   # only coplanar pairs

    def test_bump_costs_and_the_gradient_flattens_it(self):
        pos, tri = self.bumped_grid()
        faces = O.flat_edges(pos, tri)
        self.assertGreater(len(faces), 0)
        value, grad = O.dihedral_term(pos, tri, faces)
        self.assertGreater(value, 0)
        after, _ = O.dihedral_term(pos - 0.1 * grad, tri, faces)
        self.assertLess(after, value)
        self.assertEqual(O.dihedral_term(pos, tri, faces[:0])[0], 0.0)

    def test_zero_lambda_leaves_the_objective_unchanged(self):
        prob = problem()
        self.assertNotIn("dihedral", prob.evaluate(prob.pos0)[2])


if __name__ == "__main__":
    unittest.main()
