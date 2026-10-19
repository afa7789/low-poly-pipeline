"""python3 -m unittest discover -s tests/tools/blender"""
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import split_sheet as SS  # noqa: E402

SHEET = ROOT / "artifacts/model-sheets/draft2/n01X.jpg"


class Scaled(unittest.TestCase):
    def test_pads_and_maps_to_sheet_pixels(self):
        self.assertEqual(SS.scaled((100, 100, 200, 300), 2.0, 2.0, 2000, 2000),
                         (176, 176, 424, 624))

    def test_clamps_to_the_sheet(self):
        self.assertEqual(SS.scaled((0, 0, 768, 768), 1.0, 1.0, 768, 768), (0, 0, 768, 768))


@unittest.skipUnless(SHEET.exists(), "n01X sheet not checked out")
class Split(unittest.TestCase):
    def test_five_named_views(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = SS.split(SHEET, pathlib.Path(tmp), "n01X")
            views = {"front", "left", "back", "top", "bottom"}
            if SS.rts_path(SHEET).exists():
                views.add("rts")
            self.assertEqual(set(out), views)
            sizes = {k: subprocess.run(["magick", "identify", "-format", "%w %h", str(p)],
                                       capture_output=True, text=True).stdout.split()
                     for k, p in out.items()}
        w, h = map(int, sizes["left"])
        fw, fh = map(int, sizes["front"])
        self.assertGreater(h, w)          # profile is a tall, narrow figure
        self.assertLess(w, fw)            # narrower than the front view
        tw, th = map(int, sizes["top"])
        self.assertGreater(tw, th)        # plan view is wide, not tall


if __name__ == "__main__":
    unittest.main()
