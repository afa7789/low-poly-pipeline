"""python3 -m unittest discover -s tests/tools/blender

L15-1: the gate by part (parts_gate.py), the sheet's orientation (refs/<id>/sheet.json) and the body frame of a model made of
separate pieces (silhouette.body_fractions)."""
import json
import pathlib
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import deform_to_sheet as D  # noqa: E402
import parts_gate as PG  # noqa: E402
import review_pair as RP  # noqa: E402
import silhouette as S  # noqa: E402


def blank():
    return np.zeros((S.CANVAS_H, S.CANVAS_W), bool)


def box(x0, y0, x1, y1):
    m = blank()
    m[y0:y1, x0:x1] = True
    return m


class Verdict(unittest.TestCase):
    ROWS = [{"view": "front", "ok": True}] * 4 + [{"view": "left", "ok": False}]

    def test_summary(self):
        s = PG.summary(self.ROWS)
        self.assertEqual((s["k"], s["n"], s["by_view"]["left"]), (4, 5, [0, 1]))
        self.assertIsNone(PG.summary([])["share"])

    def test_pass_needs_the_guards_and_80_percent(self):
        ok = {"front": True}
        self.assertEqual(PG.verdict(ok, self.ROWS)[0], "PASS")                       # 4/5 = .8
        self.assertEqual(PG.verdict(ok, self.ROWS[1:])[0], "CHECK(parts 3/4)")
        self.assertTrue(PG.verdict({"front": False}, self.ROWS)[0].startswith("CHECK(guard front"))

    def test_a_guard_fail_is_worse_than_a_parts_fail(self):
        self.assertLess(PG.verdict({"front": False}, self.ROWS)[1], PG.verdict(ok := {"front": True}, self.ROWS[1:])[1])
        self.assertLess(PG.verdict(ok, self.ROWS[1:])[1], PG.verdict(ok, self.ROWS)[1])

    def test_guard_is_never_stricter_than_the_views_gate(self):
        good = {"spill": 0.05}
        self.assertTrue(PG.guard_ok(0.66, good, 0.65))       # left gate .65: the guard is min(.65, .75)
        self.assertFalse(PG.guard_ok(0.64, good, 0.65))
        self.assertFalse(PG.guard_ok(0.74, good, 0.90))      # a high gate is capped at BODY_FLOOR
        self.assertFalse(PG.guard_ok(0.90, {"spill": 0.16}, 0.70))
        self.assertTrue(PG.guard_ok(0.1, {"spill": 1.0}, None))


class Props(unittest.TestCase):
    def test_club_behind_the_body_fails_the_side(self):
        body, club = box(150, 40, 230, 240), box(110, 30, 125, 200)       # the sheet's club in front (left of the body here)
        behind = box(250, 30, 265, 200)
        size, side = PG.prop_checks(club, club | body, body, PG.centroid_x(body))
        self.assertTrue(size and side)
        size, side = PG.prop_checks(club, behind | body, body, PG.centroid_x(body))
        self.assertFalse(side)

    def test_size(self):
        body, club = box(150, 40, 230, 240), box(110, 30, 125, 200)
        fat = box(100, 30, 135, 200)
        self.assertFalse(PG.prop_checks(club, fat | body, body, PG.centroid_x(body))[0])


class Facing(unittest.TestCase):
    def doc(self, face_u, hand_u):
        part = lambda name, role, u: {"name": name, "role": role, "box2d": {"left": [u - 0.05, 0.1, u + 0.05, 0.5]}}  # noqa: E731
        return {"parts": [part("t", "torso", 0.5), part("f", "face", face_u), part("h", "hand", hand_u)]}

    def test_right_left_and_weak(self):
        self.assertEqual(PG.left_facing(self.doc(0.62, 0.55)), 1)
        self.assertEqual(PG.left_facing(self.doc(0.40, 0.45)), -1)
        self.assertIsNone(PG.left_facing(self.doc(0.51, 0.50)))

    def test_freeze_writes_sheet_json_with_the_mirror_from_the_parts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            (tmp / "refs" / "u").mkdir(parents=True)
            (tmp / "refs" / "u" / "parts.json").write_text(json.dumps(self.doc(0.4, 0.45)))
            run = tmp / "runs" / "u" / "r1"
            run.mkdir(parents=True)
            (run / "silhouette.json").write_text(json.dumps({"top_orientation": {"top": "head-down", "bottom": "head-up"}}))
            doc = PG.freeze("u", tmp / "runs", tmp / "refs")
            self.assertEqual(doc["rotate"], [])
            self.assertEqual(doc["mirror"], {"front": False, "back": False, "top": False, "bottom": False, "left": True})
            self.assertEqual(PG.load_orientation(tmp / "refs" / "u" / "sheet.jpg"), json.loads((tmp / "refs/u/sheet.json").read_text()))
        self.assertIsNone(PG.load_orientation(tmp / "nowhere" / "sheet.jpg"))


class Orientation(unittest.TestCase):
    def test_a_fixed_mirror_overrules_the_better_iou(self):
        concept = box(50, 20, 120, 230) | box(50, 20, 160, 60)
        model = {0: box(250, 20, 320, 230) | box(210, 20, 320, 60)}      # matches only when mirrored
        free = S.best_match(concept, model, "front")
        self.assertTrue(free[3])
        fixed = S.best_match(concept, model, "front", mirror=False)
        self.assertFalse(fixed[3])
        self.assertLess(fixed[0], free[0])

    def test_the_sheets_rotation_is_not_decided_again(self):
        panels = {"top": box(40, 20, 100, 80), "bottom": box(40, 20, 100, 80)}
        model = {"top": {0: np.rot90(panels["top"], 2)}, "bottom": {0: panels["bottom"]}}
        self.assertEqual(S.detect_rotated(panels, model, orient={"rotate": []}), set())
        self.assertEqual(S.detect_rotated(panels, model, orient={"rotate": ["top"]}), {"top"})
        self.assertEqual(S.detect_rotated(panels, model, forced="bottom", orient={"rotate": ["top"]}), {"bottom"})


class BodyFrame(unittest.TestCase):
    """A model of separate pieces (torso, head, a club far to one side): the body is everything but the club."""
    @staticmethod
    def cube(cx, cz, w, h):
        pos = [(cx + dx, 0, cz + dz) for dx in (-w, w) for dz in (-h, h)]
        return pos, [(0, 1, 2), (1, 2, 3)]

    def test_head_and_torso_stay_in_the_body_and_the_club_leaves(self):
        pieces = [self.cube(0, 0, 1.0, 2.0), self.cube(0, 2.6, 0.5, 0.5), self.cube(3.0, 1.0, 0.1, 2.5)]
        pos, tri = [], []
        for p, t in pieces:
            tri += [tuple(i + len(pos) for i in tt) for tt in t]
            pos += p
        pos, tri = np.array(pos, float), np.array(tri)
        mask = np.zeros((300, 300), bool)
        mask[10:290, 100:240] = True                       # raster of the model: u from -1 to 3.1 maps to these columns
        props = blank()
        props[:, 236:] = True                      # where the sheet's club is: the model's right edge in the canvas
        frac = S.body_fractions(D, pos, tri, np.array([1.0, 0, 0]), np.array([0, 0, 1.0]), mask, props)
        self.assertIsNotNone(frac)
        self.assertLess(frac[2], 0.85)                     # the right edge of the box is not the club's
        self.assertLess(frac[1], 0.1)                      # the head is in: the box starts at its top (the club's is higher)

    def test_a_dominant_component_is_the_body_whatever_the_masks_say(self):
        body, club = self.cube(0, 0, 1.0, 2.0), self.cube(3.0, 1.0, 0.1, 0.5)
        pos = np.array(body[0] + self.cube(0, 2.6, 0.5, 0.5)[0] + club[0], float)       # 8 vertices of one welded body, 4 of the club
        tri = np.array(body[1] + [(2, 3, 4), (3, 4, 5), (4, 5, 6), (5, 6, 7)] + [(8, 9, 10), (9, 10, 11)])
        mask = np.zeros((300, 300), bool)
        mask[10:290, 100:240] = True
        axes = (np.array([1.0, 0, 0]), np.array([0, 0, 1.0]))
        everything = np.ones((S.CANVAS_H, S.CANVAS_W), bool)       # the masks would call every component a prop
        self.assertEqual(S.body_fractions(D, pos, tri, *axes, mask, everything), D.body_fractions(pos, tri, *axes))

    def test_no_prop_no_box(self):
        pos, tri = self.cube(0, 0, 1, 1)
        pos, tri = np.array(pos, float), np.array(tri)
        mask = np.zeros((300, 300), bool)
        mask[10:290, 100:240] = True
        self.assertIsNone(S.body_fractions(D, pos, tri, np.array([1.0, 0, 0]), np.array([0, 0, 1.0]), mask, blank()))


class JudgeGate(unittest.TestCase):
    def result(self, form, artist):
        mk = lambda a, b: {"A": a, "B": b, "winner": "A" if a > b else "B" if b > a else "tie", "biased": False}  # noqa: E731
        return {"A": "v13", "B": "v15", "form": mk(*form), "artist": mk(*artist), "sheet": mk(0, 4)}

    def test_regression_is_losing_form_or_artist_3_1(self):
        self.assertFalse(RP.regressed(self.result((2, 2), (1, 3))))
        self.assertTrue(RP.regressed(self.result((3, 1), (1, 3))))
        self.assertTrue(RP.regressed(self.result((2, 2), (4, 0))))
        self.assertIn("FAIL", RP.gate_line(self.result((4, 0), (2, 2))))
        self.assertIn("PASS", RP.gate_line(self.result((2, 2), (2, 2))))

    def test_a_position_biased_axis_is_a_tie(self):
        res = self.result((3, 1), (2, 2))
        res["form"]["winner"] = "tie"
        self.assertFalse(RP.regressed(res))


if __name__ == "__main__":
    unittest.main()
