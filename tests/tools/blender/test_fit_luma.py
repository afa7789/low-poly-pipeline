"""python3 -m unittest discover -s tests/tools/blender"""
import pathlib
import sys
import types
import unittest
from unittest import mock

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import colour_stage as CS  # noqa: E402
import fit_luma as FL  # noqa: E402


def synthetic(b, az, el, tones, n=1500, seed=3):
    """Normals on a sphere, one slot per octant (a slot on a whole sphere would not pin the light down);
    the quantile targets of the known model, one zone per slot."""
    rng = np.random.default_rng(seed)
    nrm = rng.normal(size=(n, 3))
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    slot = (nrm < 0) @ np.array([1, 2, 4])
    luma = np.array(tones)[slot] * FL.shade(b, nrm, FL.light(az, el))
    targets = {"front": {z + 1: (np.quantile(luma[slot == z], FL.QS), 0.5) for z in range(8)}}
    return {"front": (slot, nrm)}, targets, np.arange(1, 9)


TONES = (0.8, 0.5, 0.7, 0.9, 0.6, 0.75, 0.55, 0.85)


class Fit(unittest.TestCase):
    def test_recovers_light_ramp_and_tones(self):
        truth = (0.6, 0.5, 0.9, TONES)
        gbuf, targets, zone_of = synthetic(truth[0], truth[1], truth[2], truth[3])
        best = FL.solve(gbuf, targets, zone_of, np.full(8, 0.7))
        az, el, b = best.x[:3]
        with self.subTest("loss"):
            self.assertLess(float(np.abs(best.fun).sum()), 0.01)
        with self.subTest("light direction"):
            self.assertGreater(float(FL.light(az, el) @ FL.light(truth[1], truth[2])), 0.97)
        with self.subTest("ramp and tones"):
            self.assertAlmostEqual(b, truth[0], delta=0.1)
            np.testing.assert_allclose(best.x[3:], truth[3], atol=0.08)

    def test_class_tones_are_clipped_multipliers(self):
        gbuf, targets, zone_of = synthetic(0.6, 0.6, 0.5, TONES)
        best = FL.solve(gbuf, targets, zone_of, np.full(8, 0.7))
        k = FL.class_tones(best.x, gbuf, np.full(8, 0.5))
        self.assertEqual(k.shape, (8, 3))
        self.assertTrue(((k >= FL.TONE_LO) & (k <= FL.TONE_HI)).all())


class Flag(unittest.TestCase):
    SPEC = {"palette": {"iron": {"surface": "metal", "color": "#76716E"}}, "parts": []}
    ARGS = types.SimpleNamespace(texture="cel", fit_luma=True)

    def test_default_is_off(self):
        self.assertFalse(CS.FIT_LUMA)

    def test_stage_colour_paints_with_the_fitted_tones(self):
        seen = {}

        def attempt(spec, *_):
            seen["tones"] = spec["palette"]["iron"].get("tones")
            return None, None, pathlib.Path(".")

        fitted = {"palette": {"iron": {"surface": "metal", "color": "#76716E", "tones": [1.1, 1.0, 0.7]}}}
        with mock.patch.object(CS, "fit_luma", return_value=(fitted, {})), mock.patch.object(CS, "attempt", attempt):
            ok, _ = CS.stage_colour(self.SPEC, None, self.ARGS, {}, ".")
        self.assertFalse(ok)
        self.assertEqual(seen["tones"], [1.1, 1.0, 0.7])

    def test_off_leaves_the_spec_alone(self):
        seen = {}

        def attempt(spec, *_):
            seen["tones"] = spec["palette"]["iron"].get("tones")
            return None, None, pathlib.Path(".")

        args = types.SimpleNamespace(texture="cel", fit_luma=False)
        with mock.patch.object(CS, "fit_luma") as fit, mock.patch.object(CS, "attempt", attempt):
            CS.stage_colour(self.SPEC, None, args, {}, ".")
        fit.assert_not_called()
        self.assertIsNone(seen["tones"])

    def test_tones_schema(self):
        for tones, ok in ((None, True), ([1, 1, 1], True), ([1, 1], False), ([0, 1, 1], False), ([1, 1, 4], False)):
            with self.subTest(tones=tones):
                self.assertEqual(CS.valid_tones(tones), ok)


if __name__ == "__main__":
    unittest.main()
