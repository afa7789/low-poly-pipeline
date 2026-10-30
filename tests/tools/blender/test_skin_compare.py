"""L16-4: the acceptance of skin_compare.py, on made-up judge results (no disk, no model)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))
import skin_compare as SC  # noqa: E402


def axis(a, b):
    return {"A": a, "B": b, "winner": "A" if a > b else "B" if b > a else "tie"}


def result(form, sheet=(2, 2), artist=(2, 2)):
    return {"form": axis(*form), "sheet": axis(*sheet), "artist": axis(*artist)}


def skin(k=10, tris=700, stretch=1.2):
    return {"parts": [k, 12], "tris": tris, "stretch": {"walk": {"p99.5_stretch": stretch}}}


class Acceptance(unittest.TestCase):
    units = ["a", "b", "c", "d", "e", "f"]

    def run_accept(self, results, skins=None):
        skins = skins or {u: skin() for u in self.units}
        return SC.acceptance("blend", dict(zip(self.units, results)), skins, {u: skin() for u in self.units})

    def test_form_wins_in_four_units_and_nothing_lost_is_accepted(self):
        won = result((1, 3))
        self.assertTrue(self.run_accept([won] * 4 + [result((2, 2))] * 2)["ACCEPTED"])

    def test_three_form_wins_are_not_enough(self):
        self.assertFalse(self.run_accept([result((1, 3))] * 3 + [result((2, 2))] * 3)["ACCEPTED"])

    def test_losing_artist_in_two_units_fails_the_hold(self):
        lost = result((0, 4), artist=(3, 1))
        report = self.run_accept([lost] * 2 + [result((1, 3))] * 4)
        self.assertFalse(report["sheet+artist held in >= 5/6"])

    def test_a_fall_in_parts_or_over_budget_blocks(self):
        won = [result((1, 3))] * 6
        fell = {u: skin(k=9 if u == "a" else 10) for u in self.units}
        self.assertFalse(self.run_accept(won, fell)["parts k/n kept in every unit"])
        self.assertFalse(self.run_accept(won, {u: skin(tris=846) for u in self.units})["tris <= 700"])


if __name__ == "__main__":
    unittest.main()
