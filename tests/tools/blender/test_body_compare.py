import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))
import body_compare as BC  # noqa: E402


class Pure(unittest.TestCase):
    def test_times_from_reads_the_driver_lines(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "t.txt"
            p.write_text("n005 union-700 exit=1 t=196s\nALLDONE\n")
            self.assertEqual(BC.times_from(p), {("n005", "union-700"): 196.0})
        self.assertEqual(BC.times_from(""), {})

    def test_wins_counts_units_both_runs_measured(self):
        rows = [{"unit": u, "variant": v, "ok": True, "planarity": x} for u, v, x in
                (("a", "p", .2), ("a", "q", .1), ("b", "p", .1), ("b", "q", .1), ("c", "p", None), ("c", "q", .1))]
        self.assertEqual(BC.wins(rows, "p", "q", "planarity"), (1, 2))


if __name__ == "__main__":
    unittest.main()
