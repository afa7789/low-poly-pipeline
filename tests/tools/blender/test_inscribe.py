"""python3 -m unittest discover -s tests/tools/blender

L13-5 (inscribe.py): the visual hull cuts the body's field per view, an incoherent view or a top without a camera never cuts, and the
clamp moves only the vertices that are red (a prop with no mask of its own stays). No Blender."""
import pathlib
import sys
import tempfile
import types
import unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import deform_to_sheet as D  # noqa: E402
import inscribe as I  # noqa: E402
import silhouette as S  # noqa: E402

FRONT = np.array(D.FRONT_AXES["front"], float)


def disc(r=128, cx=192, cy=128):
    y, x = np.mgrid[:S.CANVAS_H, :S.CANVAS_W]
    return (x + .5 - cx) ** 2 + (y + .5 - cy) ** 2 <= r * r


def cube_field(half=1.0, voxel=0.05):
    """A cube of side 2 * half as the body's field (a hard box sdf), the grid a Field would have."""
    n = int(2 * (half + 4 * voxel) / voxel) + 1
    origin = np.full(3, -(half + 4 * voxel))
    ax = origin[0] + voxel * np.arange(n)
    X, Y, Z = np.meshgrid(ax, ax, ax, indexing="ij")
    q = np.stack([np.abs(X), np.abs(Y), np.abs(Z)]) - half
    grid = (np.linalg.norm(np.maximum(q, 0), axis=0) + np.minimum(q.max(0), 0)).astype(np.float32)
    return types.SimpleNamespace(grid=grid, origin=origin, voxel=voxel, shape=grid.shape, margin=4 * voxel), ax


class Carve(unittest.TestCase):
    def cut(self, options):
        field, ax = cube_field()
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "h.npz"
            I.write_views(path, options, [])
            report = I.carve(field, path)
        return field, ax, report

    def test_the_corners_outside_a_round_mask_are_cut_and_nothing_else(self):
        field, ax, report = self.cut({"front": (FRONT, disc())})     # the disc touches the cube's face at its four mid-edges
        X, Y, Z = np.meshgrid(ax, ax, ax, indexing="ij")
        radius = np.hypot(X, Z)
        was_in = np.abs(X) <= 1.0 - 1e-6
        was_in &= (np.abs(Y) <= 1.0 - 1e-6) & (np.abs(Z) <= 1.0 - 1e-6)
        self.assertTrue((field.grid[was_in & (radius > 1.03)] > 0).all(), "a voxel outside the disc is still in the body")
        self.assertTrue((field.grid[was_in & (radius < 0.95)] < 0).all(), "a voxel well inside the disc was cut")
        self.assertLess(report["voxels_after"], report["voxels_before"])

    def test_a_mask_that_already_holds_the_body_cuts_almost_nothing(self):
        square = np.zeros((S.CANVAS_H, S.CANVAS_W), bool)
        square[:, 64:320] = True
        field, _, report = self.cut({"front": (FRONT, square)})
        self.assertGreater(report["voxels_after"], 0.95 * report["voxels_before"])      # the 1 px erosion of the walls, no more


class Selection(unittest.TestCase):
    def test_an_incoherent_view_and_a_top_without_a_camera_do_not_cut(self):
        panels = {v: disc() for v in ("front", "back", "top")}
        self.assertEqual(I.cutting_views(panels, {"incoherent": ["back"]}, {}), ["front"])
        self.assertEqual(I.cutting_views(panels, {}, {"top": -20}), ["front", "back", "top"])
        self.assertEqual(I.cutting_views(panels, {}, None), ["front", "back"])

    def test_a_mask_the_erosion_empties_drops_its_view(self):
        sliver = np.zeros((S.CANVAS_H, S.CANVAS_W), bool)
        sliver[:, 100] = True
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(I.write_views(pathlib.Path(tmp) / "h.npz", {"front": (FRONT, sliver), "back": (FRONT, disc())}, []), ["back"])

    def test_the_gates_mirror_is_the_one_carved_with(self):
        lopsided = np.zeros((S.CANVAS_H, S.CANVAS_W), bool)       # the body leans right in the sheet: mirrored it would be cut from the other side
        lopsided[:, 64:320] = True
        lopsided[:, 64:192] &= disc(128, 192, 128)[:, 64:192]
        outs = []
        for mirror in (1, -1):
            field, _ = cube_field()
            with tempfile.TemporaryDirectory() as tmp:
                path = pathlib.Path(tmp) / "h.npz"
                I.write_views(path, {"front": (FRONT, lopsided)}, [], mirrors={"front": mirror})
                I.carve(field, path)
            outs.append(field.grid < 0)
        self.assertFalse((outs[0] == outs[1]).all())

    def test_a_negative_erosion_grows_the_hull(self):
        m = disc()
        self.assertGreater(I.eroded(m, -2).sum(), m.sum())
        self.assertLess(I.eroded(m, 2).sum(), m.sum())
        self.assertTrue((I.eroded(m, 0) == m).all())


def box(lo, hi, base):
    """(8 vertices, 12 triangles) of an axis-aligned box in the Z-up frame; `base` offsets the indices."""
    v = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])], float)
    t = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    return v, t + base


class Clamp(unittest.TestCase):
    """A body box x in [-1, 1] (canvas px 25.6 .. 281.6 once the bbox is framed) and a prop box at x 1.5 .. 1.6 (345 .. 358)."""

    def mesh(self):
        body, bt = box((-1, -.2, 0), (1, .2, 2), 0)
        prop, pt = box((1.5, -.05, 0), (1.6, .05, 2), 8)
        return np.vstack([body, prop]), np.vstack([bt, pt])

    def view(self, mask, props=None):
        return D.View("front", FRONT[0], FRONT[1], 1, mask, True, props)

    def rect(self, x0, x1):
        m = np.zeros((S.CANVAS_H, S.CANVAS_W), bool)
        m[:, x0:x1] = True
        return m

    def step(self, view):
        pos, tri = self.mesh()
        owner, body = D.owner_body(tri, len(pos))
        step, red = I.pull_red(pos, [view], 1, owner, body, np.zeros(len(pos), bool))
        return pos, owner, body, step, red

    def test_only_the_red_body_vertices_move_and_a_prop_with_no_mask_stays(self):
        pos, owner, body, step, red = self.step(self.view(self.rect(40, 300)))
        np.testing.assert_array_equal(red, (owner == body) & (pos[:, 0] < 0))        # the body's left face is left of px 40; the prop is outside and untouched
        self.assertTrue((step[red, 0] > 0).all(), "a red vertex goes toward the mask")
        self.assertFalse(step[~red].any())

    def test_a_prop_goes_only_to_its_own_mask(self):
        own = self.rect(352, 380)           # the prop's vertices straddle its mask's left edge: the ones outside go in
        pos, owner, body, step, red = self.step(self.view(self.rect(40, 300) | own, {"spear": own}))
        self.assertTrue(red[owner != body].any() and (step[owner != body][red[owner != body]][:, 0] > 0).all())
        self.assertTrue((pos[red & (owner == body), 0] < 0).all())

    def test_a_round_is_kept_only_when_the_spill_falls_and_no_view_loses_iou(self):
        m = lambda spill, iou: {"front": {"spill": spill, "iou": iou}}  # noqa: E731
        self.assertTrue(I.better(m(.10, .80), m(.05, .80)))
        self.assertFalse(I.better(m(.10, .80), m(.05, .70)))
        self.assertFalse(I.better(m(.10, .80), m(.10, .80)))


if __name__ == "__main__":
    unittest.main()
