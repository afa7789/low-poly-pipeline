"""python3 -m unittest discover -s tests/tools/blender"""
import pathlib
import subprocess
import sys
import unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import building_hull as BH  # noqa: E402
import cut_hull as CH  # noqa: E402
import preflight as PF  # noqa: E402
import silhouette as SIL  # noqa: E402
import spec_pipeline as SP  # noqa: E402


def house():
    """A 100 x 60 px wall block with a chimney on the roof, a ramp under it and an arm out of the side."""
    m = np.zeros((90, 130), bool)
    m[20:80, 10:110] = True        # the body: rows 20-79
    m[0:20, 50:58] = True          # chimney
    m[80:90, 30:90] = True         # ramp / rails under the wall line
    m[40:50, 110:130] = True       # arm
    return m


def l_shape():
    m = np.zeros((100, 100), bool)
    m[:, :40] = True
    m[60:, :] = True
    return m


class Body(unittest.TestCase):
    def test_thin_ends_go(self):
        self.assertEqual(BH.body(house()).shape, (60, 100))

    def test_a_narrow_tower_is_not_the_body(self):
        self.assertEqual(BH.body(l_shape()).shape, (40, 100))        # the roof and the tiers are the author's


class Rectify(unittest.TestCase):
    def test_near_axis_edges_become_axis_edges_without_extra_vertices(self):
        poly = BH.rectify([(0, 0), (1.0, 0.02), (1.01, 1.0), (0.5, 1.0), (0.0, 1.0)])
        self.assertEqual(len(poly), 4)
        for a, b in zip(poly, poly[1:] + poly[:1]):
            self.assertTrue(abs(a[0] - b[0]) < 1e-6 or abs(a[1] - b[1]) < 1e-6)

    def test_l_shape_outline_has_six_vertices(self):
        self.assertEqual(len(BH.rectify(SIL.outline(l_shape(), eps=BH.EPS, limit=BH.LIMIT))), 6)


class HullPart(unittest.TestCase):
    def part(self):
        return BH.hull_part({"front": house(), "left": house()}, height=4.0)

    def test_dims_scale_to_the_figure_height_and_stand_on_the_ground(self):
        part = self.part()
        _, kind, dims, at, mat, opts = part
        self.assertEqual((kind, mat, opts["cut"]), ("box", "hull", "sheet"))
        self.assertAlmostEqual(dims[1], 4.0 * 60 / 90, delta=0.1)          # 60 body rows of the 90 figure rows
        self.assertAlmostEqual(at[1], dims[1] / 2, 3)
        self.assertAlmostEqual(dims[0] / dims[1], 100 / 60, delta=0.1)
        self.assertAlmostEqual(dims[2], dims[0], 2)

    def test_the_spec_takes_it_once_and_the_slot_comes_with_it(self):
        spec = BH.with_hull({"rig": "building", "parts": [["body", "box", [1, 1, 1], [0, 0.5, 0], "hull", {}]]},
                            self.part())
        self.assertTrue(BH.is_hull(spec["parts"][0]))
        self.assertIn("hull", spec["palette"])
        self.assertIs(BH.with_hull(spec, self.part()), spec)

    def test_registered_in_the_composed_pipeline(self):
        spec = BH.with_hull({"rig": "building", "parts": []}, self.part())
        SP.set_rig("building")
        self.addCleanup(SP.set_rig, "biped")
        SP.validate(spec["parts"], spec["palette"])                  # the schema takes it
        help_ = subprocess.run([sys.executable, str(pathlib.Path(SP.__file__)), "--help"],
                               capture_output=True, text=True).stdout
        self.assertIn("--hull", help_)                               # and the CLI reaches it
        self.assertEqual(PF.part_tris(spec["parts"][0]), PF.CUT_TRIS)
        entry = CH.cut_polys(spec["parts"], None)[0]                 # no sheet needed
        self.assertTrue(entry["dissolve"])
        self.assertEqual(entry["front"], spec["parts"][0][5]["hull"]["front"])
        self.assertIn("Do NOT write it", BH.brief_text(self.part()))


if __name__ == "__main__":
    unittest.main()
