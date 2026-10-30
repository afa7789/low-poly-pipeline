"""python3 -m unittest discover -s tests/tools/blender"""
import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import views as V  # noqa: E402


def looks_at_centre(offset, rot):
    """Camera looks down its local -Z; rotate that by the X-Euler and check it points
    from the offset back to the origin."""
    t = math.radians(rot[0])
    view = (0.0, math.sin(t), -math.cos(t))
    norm = math.dist(offset, (0, 0, 0))
    return all(math.isclose(view[i], -offset[i] / norm, abs_tol=1e-9) for i in range(3))


class Camera(unittest.TestCase):
    def test_untilted_views_are_the_table(self):
        for name in V.VIEWS:
            self.assertEqual(V.camera(name), V.VIEWS[name])
        self.assertEqual(V.camera("front", 30), V.VIEWS["front"])

    def test_tilted_top_and_bottom_still_aim_at_the_model(self):
        for name in V.TILTED:
            for tilt in V.TILTS:
                self.assertTrue(looks_at_centre(*V.camera(name, tilt)), (name, tilt))

    def test_positive_tilt_moves_the_camera_to_the_front(self):
        for name in V.TILTED:
            offset, _ = V.camera(name, 20)
            self.assertLess(offset[1], 0)       # front is -Y
            self.assertAlmostEqual(math.dist(offset, (0, 0, 0)), V.DIST)


class WeightOf(unittest.TestCase):
    """30.L12-5 (opt-in): a view the sheet contradicts weighs INCOHERENT_WEIGHT whatever the rig; unset, VIEW_WEIGHTS as before."""
    def test_incoherent_view_weighs_what_was_asked(self):
        rep = {"incoherent": ["top"]}
        self.assertEqual(V.weight_of("spider", "top", rep), 2.0)                 # default: unchanged
        self.assertEqual(V.weight_of("spider", "top", rep, incoherent_weight=0.0), 0.0)
        self.assertEqual(V.weight_of("spider", "bottom", rep, incoherent_weight=0.0), 2.0)   # a coherent view keeps the rig's weight
        self.assertEqual(V.weight_of("spider", "top", None, incoherent_weight=0.0), 2.0)     # no report, no incoherent view
        self.assertEqual(V.weight_of(None, "rts", {"incoherent": ["rts"]}, 1.0), 1.0)
        self.assertEqual(V.weight_of("biped", "rts", {"incoherent": ["rts"]}, 2.0), 2.0)


class RtsOffset(unittest.TestCase):
    def test_front_right_and_above(self):
        x, y, z = V.rts_offset(45, 45)
        self.assertGreater(x, 0)            # azimuth toward +X
        self.assertLess(y, 0)               # from the front (-Y)
        self.assertAlmostEqual(z, V.DIST * math.sin(math.radians(45)))
        self.assertAlmostEqual(math.dist((x, y, z), (0, 0, 0)), V.DIST)

    def test_zero_azimuth_is_the_front(self):
        x, y, _ = V.rts_offset(30, 0, dist=2.0)
        self.assertAlmostEqual(x, 0)
        self.assertLess(y, 0)


class ParseTilts(unittest.TestCase):
    def test_round_trip(self):
        self.assertEqual(V.parse_tilts("top:10,bottom:-20"), {"top": 10, "bottom": -20})
        self.assertEqual(V.parse_tilts(""), {})

    def test_rts_pair(self):
        self.assertEqual(V.parse_tilts("rts:55/-30"), {"rts": (55, -30)})


if __name__ == "__main__":
    unittest.main()
