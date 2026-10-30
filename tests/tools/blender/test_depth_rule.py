"""depth_rule.py (L12-8): the tilted-camera triangulation, the landmark residual, z_err, relief_agreement, the spec's z from box3d. Pure numpy, no Blender."""
import pathlib
import sys
import unittest

import numpy as np

TOOLS = pathlib.Path(__file__).resolve().parents[3] / "tools/blender"
sys.path.insert(0, str(TOOLS))

import depth_rule as DR  # noqa: E402
import sdf_batch  # noqa: E402


def box_mesh(lo, hi):
    """(positions, triangles) of an axis-aligned box in spec metres (x, y up, z forward)."""
    x, y, z = ([lo[i], hi[i]] for i in range(3))
    pos = np.array([[a, b, c] for a in x for b in y for c in z], float)
    quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return pos, np.array([t for a, b, c, d in quads for t in ((a, b, c), (a, c, d))])


class TiltedTriangulation(unittest.TestCase):
    """The top panel is drawn tilted: the row of a point is v = y sin(tilt) - z cos(tilt). Reading it as a straight-down view (tilt 0) puts the point y tan(tilt) away."""
    pts = np.array([[0.2, 0.3, 0.1], [-0.4, 1.6, -0.3], [0.0, 2.5, 0.4]])

    def test_pinned_camera_recovers_z_exactly_and_a_pure_orthographic_reading_does_not(self):
        for cam in (-30, -20, 10):
            u, v = DR.project(self.pts, "top", cam)
            z = DR.z_from_view(u, v, self.pts[:, 0], self.pts[:, 1], "top", cam)
            np.testing.assert_allclose(z, self.pts[:, 2], atol=1e-9)
            flat = DR.z_from_view(u, v, self.pts[:, 0], self.pts[:, 1], "top", 0)
            self.assertGreater(np.abs(flat - self.pts[:, 2]).max(), 0.1, f"tilt {cam}: the flat reading is off by about y sin(tilt)")

    def test_bottom_camera_too(self):
        u, v = DR.project(self.pts, "bottom", 30)
        np.testing.assert_allclose(DR.z_from_view(u, v, self.pts[:, 0], self.pts[:, 1], "bottom", 30), self.pts[:, 2], atol=1e-9)


class Fit(unittest.TestCase):
    """A hull and a top panel made from the same boxes at a known tilt, the panel drawn turned 180 degrees and at its own scale."""

    def setUp(self):
        self.H, self.cam = 2.0, -20
        n = 60
        xs, ys, zs = np.meshgrid(np.linspace(-.5, .5, n), np.linspace(0, 2, n), np.linspace(-.2, .3, n // 2), indexing="ij")
        body = np.stack([xs.ravel(), ys.ravel(), zs.ravel()], 1)
        arm = body[(np.abs(body[:, 0]) > .3)]
        self.points = np.concatenate([body[np.abs(body[:, 0]) <= .3], arm[arm[:, 1] > 1.2]])
        u, v = DR.project(self.points, "top", self.cam)
        s, c = 120.0, (400.0, 380.0)
        self.px = np.stack([c[0] - s * (u - u.mean()), c[1] + s * (v - v.mean())], 1)        # turned 180: (su, sv) = (-1, -1)
        self.panel = DR.splat(self.px, (768, 768), 1)

    def test_fit_finds_the_turn_and_the_projection_of_a_point(self):
        frame = DR.fit_top(self.points, self.panel, self.cam)
        self.assertGreater(frame.iou, 0.9)
        self.assertEqual((frame.su, frame.sv), (-1, -1))
        inside = DR.top_inside(frame, self.points[::50], self.panel)
        self.assertTrue(inside.mean() > 0.95, "the hull's own points land on the figure")

    def test_a_landmark_off_the_figure_has_a_residual_and_one_on_it_has_none(self):
        frame = DR.fit_top(self.points, self.panel, self.cam)
        marks = [{"name": "in", "xyz": [0.0, 1.0, 0.05], "gap": 0.0}, {"name": "out", "xyz": [0.0, 1.0, 1.5], "gap": 0.0},
                 {"name": "gap", "xyz": [0.0, 1.0, 0.05], "gap": 0.07}]
        got = {m["name"]: m["resid"] for m in DR.residuals(marks, frame, self.panel, self.H)}
        self.assertLess(got["in"], DR.RESID_MAX)
        self.assertGreater(got["out"], DR.RESID_MAX, "z 1.5 is outside the hull: the top panel does not show a figure there")
        self.assertAlmostEqual(got["gap"], 0.07, places=2)


class ZError(unittest.TestCase):
    pos, tri = box_mesh([-.2, 0, -.1], [.2, 1, .1])      # centred on z = 0

    def mark(self, z, resid=0.0, **kw):
        return {"name": "m", "xyz": [0.0, 0.5, z], "gap": 0.0, "resid": resid, **kw}

    def test_a_clay_shifted_a_tenth_of_h_reads_a_tenth(self):
        r = DR.z_error([self.mark(0.1)], self.pos, self.tri, 1.0)
        self.assertEqual((r["n_used"], r["n_total"]), (1, 1))
        self.assertAlmostEqual(r["z_err"], 0.1, places=6)

    def test_an_incoherent_landmark_is_dropped_and_counted(self):
        r = DR.z_error([self.mark(0.1), self.mark(0.9, resid=2 * DR.RESID_MAX)], self.pos, self.tri, 1.0)
        self.assertEqual((r["n_used"], r["n_total"], r["dropped"]), (1, 2, 1))
        self.assertAlmostEqual(r["z_err"], 0.1, places=6, msg="the dropped one (0.9 H off) does not count")

    def test_a_line_the_clay_does_not_cross_is_a_miss(self):
        r = DR.z_error([{**self.mark(0.1), "xyz": [5.0, 0.5, 0.1]}], self.pos, self.tri, 1.0)
        self.assertEqual((r["miss"], r["n_used"], r["z_err"]), (1, 0, None))

    def test_a_sheet_facing_the_other_way_is_read_with_the_other_sign(self):
        pos, tri = box_mesh([-.2, 0, .3], [.2, 1, .5])      # the clay is forward (z = +.4); the sheet says -.4
        r = DR.z_error([self.mark(-0.4)], pos, tri, 1.0)
        self.assertEqual(r["z_sign"], -1)
        self.assertAlmostEqual(r["z_err"], 0.0, places=6)

    def test_a_face_mark_asks_for_the_front_surface_not_the_centre(self):
        pos, tri = box_mesh([-.2, 0, -.3], [.2, 1, .3])      # a thick head: centre 0, front .3
        r = DR.z_error([self.mark(0.0, face=[0.1, 0.3])], pos, tri, 1.0)
        self.assertAlmostEqual(r["z_err"], 0.0, places=6)


class Relief(unittest.TestCase):
    def test_zbuffer_keeps_the_nearest_triangle(self):
        xy = np.array([[2, 2], [30, 2], [2, 30], [2, 2], [30, 2], [2, 30]], float)
        zb = DR.zbuffer(xy, np.array([0, 0, 0, 1.0, 1.0, 1.0]), np.array([[0, 1, 2], [3, 4, 5]]), (40, 40))
        self.assertEqual(zb[10, 10], 1.0)
        self.assertEqual(zb[35, 35], -np.inf)

    def scene(self):
        zb = np.full((64, 96), -np.inf)
        zb[8:56, 8:88] = 0.0
        zb[20:40, 30:60] = 0.2                          # a plate 0.2 H in front of the rest
        return zb

    def test_steps_are_the_plates_outline_and_not_the_silhouette(self):
        steps = DR.depth_steps(self.scene(), 1.0, 1.0, rim=2)
        self.assertTrue(steps[20, 45] and steps[30, 30] and steps[30, 59])
        self.assertFalse(steps[8, 40] or steps[30, 45], "the figure's own outline, and the flat inside of the plate, are no steps")

    def test_agreement_is_one_when_steps_and_ink_coincide_and_zero_eight_px_away(self):
        zb = np.full((64, 96), -np.inf)
        zb[8:56, 8:48] = 0.0
        zb[8:56, 48:88] = 0.2                           # one vertical depth step, at column 48
        steps = DR.depth_steps(zb, 1.0, 1.0, rim=2)
        ink = np.zeros_like(steps)
        ink[12:52, 48] = True
        p, r, *_ = DR.agreement(steps, ink)
        self.assertEqual((p, r), (1.0, 1.0))
        ink = np.zeros_like(steps)
        ink[12:52, 48 + 8 + DR.SLACK] = True                # 8 px beyond the slack
        p, r, *_ = DR.agreement(steps, ink)
        self.assertEqual((p, r), (0.0, 0.0))


class SpecShifts(unittest.TestCase):
    doc = {"H": 2.0, "incoherent": [{"part": "bad", "dy_H": 0.09}], "parts": [
        {"name": "mask", "box3d": [[0, 0, 0.30], [1, 1, 0.60]]},
        {"name": "tank", "box3d": [[0, 0, -0.80], [1, 1, -0.20]]},
        {"name": "bad", "box3d": [[0, 0, 0.30], [1, 1, 0.60]]},
        {"name": "wheel", "box3d": [[0, 0, 0.30], [1, 1, 0.60]], "z_from": "top"},
        {"name": "lamp", "box3d": None},
        {"name": "twin", "box3d": [[0, 0, 0.30], [1, 1, 0.60]], "z_from": "mirror"}]}

    def test_a_part_outside_the_range_goes_to_the_middle_half_and_the_rest_stay(self):
        centres = [(0, 0, 0.0), (0, 0, -0.5), (0, 0, 0.0), (0, 0, 0.0), (0, 0, 0.0), (0, 0, 0.1), (0, 0, 0.0)]
        moves = DR.tri_shifts(centres, [0, 1, 2, 3, 4, None, 5], self.doc, 2.0)
        self.assertEqual(sorted(moves), [0], "tank: inside its range; bad: the views disagree; wheel: from the top hull; lamp: no box; None: no part; twin: a mirrored z")
        self.assertAlmostEqual(moves[0], 0.375, places=6, msg="z 0 -> the middle half starts at .30 + .075")

    def test_a_far_part_moves_at_most_dz_max(self):
        moves = DR.tri_shifts([(0, 0, -3.0)], [0], self.doc, 2.0)
        self.assertAlmostEqual(moves[0], DR.DZ_MAX * 2.0)


class CompleteBox(unittest.TestCase):
    H = 2.0

    def hull(self):
        g = np.stack(np.meshgrid(np.linspace(0, 1, 11), np.linspace(0, 2, 21), np.linspace(-.5, .5, 21), indexing="ij"), -1).reshape(-1, 3)
        return g

    def test_z_is_read_from_the_voxels_outside_the_other_parts(self):
        torso = ([0, 0.0, -0.5], [1, 2.0, -0.2])         # the other part owns the back
        win = {"x": (0.2, 0.8), "y": (0.2, 1.8), "z": None}
        box, why = DR.complete_box(win, self.hull(), [torso], self.H, grow=0.0)
        self.assertIsNone(why)
        self.assertAlmostEqual(box[0][2], -0.15, delta=0.06)
        self.assertAlmostEqual(box[1][2], 0.5, delta=0.02)
        self.assertEqual((box[0][0], box[1][1]), (0.2, 1.8))

    def test_a_window_the_other_parts_fill_says_so(self):
        box, why = DR.complete_box({"x": (0.2, 0.8), "y": (0.5, 1.5), "z": None}, self.hull(), [([-1, -1, -1], [2, 3, 1])], self.H)
        self.assertEqual((box, why), (None, "inside-other-parts"))

    def test_an_envelope_wider_than_the_part_is_refused(self):
        box, why = DR.complete_box({"x": (0.4, 0.5), "y": (0.5, 0.7), "z": None}, self.hull(), [], self.H)
        self.assertEqual((box, why), (None, "envelope"))      # z 1.0 deep for a .2 part
        self.assertEqual(DR.complete_box({"x": (0.4, 0.5), "y": (0.5, 0.7), "z": None}, np.zeros((0, 3)), [], self.H), (None, "no-hull"))


class Cell(unittest.TestCase):
    def test_sdf_batch_cell(self):
        self.assertEqual(sdf_batch.depth_cell({}), "–")
        got = sdf_batch.depth_cell({"z_err": {"z_err": 0.0304, "n_used": 9, "n_total": 13}, "relief_agreement": {"front": [0.5, 0.1, 10, 20]}})
        self.assertEqual(got, "z_err 0.030 (9/13), relief P/R 0.50/0.10")


if __name__ == "__main__":
    unittest.main()
