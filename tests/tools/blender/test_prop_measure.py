"""python3 -m unittest discover -s tests/tools/blender"""
import pathlib
import sys
import unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import prop_measure as P  # noqa: E402


def part(bone, material, at, dims=(0.2, 0.2, 0.2), **opts):
    return [bone, "box", list(dims), list(at), material, opts]


# a 2.6 high unit: skin arms, a leather club in the right hand with an iron cap, a skin fist
BODY = [part("pelvis", "cloth", (0, 1.2, 0), (0.5, 0.4, 0.3)),
        part("head", "skin", (0, 2.5, 0), (0.3, 0.3, 0.3)),
        part("arm.R", "skin", (-0.5, 1.8, 0), (0.2, 0.6, 0.2)),
        part("forearm.R", "skin", (-0.55, 1.2, 0), (0.2, 0.5, 0.2)),
        part("arm.L", "skin", (0.5, 1.8, 0), (0.2, 0.6, 0.2)),
        part("forearm.L", "skin", (0.55, 1.2, 0), (0.2, 0.5, 0.2))]
CLUB = [part("forearm.R", "leather", (-0.55, 1.5, 0.1), (0.12, 1.2, 0.12)),
        part("forearm.R", "iron", (-0.55, 2.2, 0.1), (0.3, 0.2, 0.3)),
        part("forearm.R", "skin", (-0.55, 1.0, 0.1), (0.25, 0.25, 0.25))]   # the fist on the shaft


class PropParts(unittest.TestCase):
    def test_finds_the_weapon_and_what_touches_it(self):
        parts = BODY + CLUB
        self.assertEqual(P.prop_parts(parts), [6, 7])    # shaft + cap; the skin fist is the limb

    def test_no_weapon_no_prop(self):
        self.assertEqual(P.prop_parts(BODY), [])

    def test_long_limb_of_the_arms_own_material_is_not_a_weapon(self):
        long_arm = BODY[:2] + [part("arm.R", "skin", (-0.5, 1.5, 0), (0.2, 1.3, 0.2))]
        self.assertEqual(P.prop_parts(long_arm), [])

    def test_long_part_on_a_body_bone_is_not_an_arm_prop(self):
        self.assertEqual(P.prop_parts(BODY + [part("spine", "iron", (0, 1.6, -0.3), (0.3, 1.3, 0.3))]), [])


class Match(unittest.TestCase):
    @staticmethod
    def club(horizontal):
        m = np.zeros((200, 200), bool)
        m[20:180, 90:110] = True                     # shaft
        m[10:50, 70:130] = True                      # head
        return np.rot90(m) if horizontal else m

    def test_a_club_lying_down_matches_the_club_held_up(self):
        drawings = [norm(self.club(True))]
        score, view, n = P.best_match(drawings, {"front": self.club(False)})
        self.assertGreater(score, 0.9)
        self.assertEqual((view, n), ("front", 0))

    def test_a_different_prop_scores_low(self):
        box = np.zeros((200, 200), bool)
        box[40:160, 20:180] = True
        score, _, _ = P.best_match([norm(box)], {"front": self.club(False)})
        self.assertLess(score, 0.5)

    def test_picks_the_drawing_that_fits(self):
        box = np.zeros((200, 200), bool)
        box[40:160, 20:180] = True
        score, _, n = P.best_match([norm(box), norm(self.club(True))], {"left": self.club(False)})
        self.assertEqual(n, 1)


class Crops(unittest.TestCase):
    def test_one_crop_per_drawing_left_to_right(self):
        import tempfile
        from PIL import Image
        img = Image.new("RGB", (400, 400), (200, 200, 200))
        img.paste((40, 40, 40), (260, 100, 340, 300))      # right, tall
        img.paste((90, 60, 20), (40, 150, 120, 200))       # left, wide
        with tempfile.TemporaryDirectory() as tmp:
            sheet = pathlib.Path(tmp) / "props.png"
            img.save(sheet)
            crops = P.crop_props(sheet, tmp, "c")
            self.assertEqual(len(crops), 2)
            sizes = []
            for c in crops:
                with Image.open(c) as im:
                    sizes.append(im.size)
            self.assertGreater(sizes[0][0], sizes[0][1])      # the wide one is on the left
            self.assertGreater(sizes[1][1], sizes[1][0])


def norm(mask):
    return P.S.normalize(mask)


if __name__ == "__main__":
    unittest.main()
