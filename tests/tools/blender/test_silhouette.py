"""python3 -m unittest discover -s tests/tools/blender"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import silhouette as S  # noqa: E402

REFS = ROOT / "artifacts/model-sheets/refs/hfoo"


HARD = REFS / "sheet-hard.jpg"


@unittest.skipUnless(HARD.exists(), "hfoo refs not checked out")
class Drift(unittest.TestCase):
    def test_hard_redraw_stays_on_the_approved_design(self):
        drift = S.sheet_drift(REFS / "sheet.jpg", HARD)
        for view in S.DRIFT_VIEWS:
            self.assertGreaterEqual(drift[view], S.DRIFT_MIN, view)   # measured 0.93-0.94

    def test_a_sheet_does_not_drift_from_itself(self):
        drift = S.sheet_drift(REFS / "sheet.jpg", REFS / "sheet.jpg")
        self.assertEqual(min(drift[v] for v in S.DRIFT_VIEWS), 1.0)


class GateWithoutModel(unittest.TestCase):
    def test_missing_glb_fails_the_gate(self):
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            run = subprocess.run([sys.executable, str(ROOT / "tools/blender/silhouette.py"),
                                  str(REFS / "sheet.jpg"), str(pathlib.Path(tmp) / "none.glb"),
                                  tmp, "--no-render"], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("no measurement", run.stdout)


if __name__ == "__main__":
    unittest.main()
