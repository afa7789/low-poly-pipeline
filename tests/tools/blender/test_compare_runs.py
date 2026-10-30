"""python3 -m unittest discover -s tests/tools/blender"""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import compare_runs as CR  # noqa: E402


class BudgetColumns(unittest.TestCase):
    def test_budget_dirs_ascending_and_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = pathlib.Path(tmp)
            for b in (1000, 400, 700):
                (run / "budgets" / str(b)).mkdir(parents=True)
                (run / "budgets" / str(b) / "budget.json").write_text(json.dumps({"budget": b, "tris": b - 3, "sliver_pct": 2.5}))
            self.assertEqual([d.name for d in CR.budget_dirs([run])], ["400", "700", "1000"])
            self.assertEqual(CR.budget_text({"dir": run / "budgets" / "700"}), "  B 700 tris 697 slivers 2.5 %")
            self.assertEqual(CR.budget_dirs([run / "budgets" / "700"]), [run / "budgets" / "700"])   # no budgets/ under it
            self.assertEqual(CR.budget_text({"dir": run}), "")
