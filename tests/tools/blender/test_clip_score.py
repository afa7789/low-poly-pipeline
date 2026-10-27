"""clip_score without the model: embeddings are stubbed, so the suite never downloads weights."""
import pathlib
import sys
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools" / "blender"))
import clip_score as cs  # noqa: E402


def basis(i, n=6, d=8):
    """n views, all near axis i of a d-dim space."""
    v = np.zeros((n, d))
    v[:, i] = 1.0
    return v + 0.01 * np.arange(n)[:, None]


class ClipScore(unittest.TestCase):
    def test_score_picks_own_unit(self):
        concepts = {u: basis(i) for i, u in enumerate("abc")}
        texts = {u: basis(i, 3) for i, u in enumerate("abc")}
        s = cs.score(basis(1), concepts, texts, "b", topk=2)
        self.assertEqual((s["rank"], s["topk"][0]), (1, "b"))
        self.assertGreater(s["concept"]["pos_neg"], 0.5)
        self.assertGreater(s["text"]["pos_neg"], 0.5)
        wrong = cs.score(basis(0), concepts, texts, "b")
        self.assertLess(wrong["concept"]["pos_neg"], 0)

    def test_crop_compare(self):
        grid = Image.new("RGB", cs.GRID_SIZE)
        self.assertEqual(cs.crop_compare(grid, "rts", 1).size, (cs.CELL_W, cs.ROW_H))
        self.assertIsNone(cs.crop_compare(Image.new("RGB", (10, 10)), "front", 0))

    def test_pos_neg_without_others(self):
        self.assertEqual(cs.pos_neg(np.ones(2), np.ones(2), [])[1], 0.0)


if __name__ == "__main__":
    unittest.main()
