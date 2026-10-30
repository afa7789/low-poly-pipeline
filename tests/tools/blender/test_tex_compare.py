import json
import pathlib
import struct
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))
import tex_compare as T  # noqa: E402


def glb(images):
    doc = json.dumps({"bufferViews": [{"byteLength": 2048}], "images": images}).encode()
    doc += b" " * (-len(doc) % 4)
    return b"glTF" + struct.pack("<III", 2, 20 + len(doc), len(doc)) + b"JSON" + doc


class TexCompare(unittest.TestCase):
    def test_atlas_kb_counts_embedded_images_only(self):
        with tempfile.TemporaryDirectory() as t:
            p = pathlib.Path(t, "m.glb")
            p.write_bytes(glb([{"bufferView": 0}]))
            self.assertEqual(T.atlas_kb(p), 2.0)
            p.write_bytes(glb([]))
            self.assertEqual(T.atlas_kb(p), 0)

    def test_a_flat_render_has_no_shade_and_the_right_colour_has_no_distance(self):
        sheet = np.zeros((32, 32, 3)) + 0.9
        ramp = np.linspace(0.3, 0.7, 32)[None, :, None] * np.ones((32, 32, 3))
        sheet[8:24, 8:24] = ramp[8:24, 8:24]
        mask = np.zeros((32, 32), bool)
        mask[8:24, 8:24] = True
        centres = T.S.zone_feature(np.array([[0.5, 0.5, 0.5]]))
        flat = np.zeros((32, 32, 3), np.uint8) + 230
        flat[8:24, 8:24] = 128
        de, shade = T.look_numbers(flat, sheet, mask, centres)
        self.assertEqual(shade, 0.0)
        self.assertLess(de, 5)


if __name__ == "__main__":
    unittest.main()
