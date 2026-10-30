"""python3.14 -m unittest discover -s tests/tools/blender

L13-1: the polish stage. No LLM, no Blender: the MCP protocol, the ops on a synthetic mesh, the accept/revert verdict and the replay."""
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

TOOLS = pathlib.Path(__file__).resolve().parents[3] / "tools/blender"
sys.path.insert(0, str(TOOLS))

import deform_to_sheet as D  # noqa: E402
import polish  # noqa: E402
import polish_mcp  # noqa: E402
import polish_ops as PO  # noqa: E402
import silhouette as S  # noqa: E402

CUBE_TRI = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])


def box_scene(width):
    """A box width x 1 x 2 (x right, y depth, z up) and a front view whose sheet is a 1 x 2 rectangle: the box is too wide in front."""
    pos = np.array([[x, y, z] for z in (0, 2) for y in (0, 1) for x in (0, width)], float)
    tri = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    concept = np.zeros((S.CANVAS_H, S.CANVAS_W), bool)
    concept[:, 96:288] = True                       # 192 x 256 = the 1 x 2 sheet silhouette, as wide as it is tall / 2 ... 0.75 x
    view = D.View("front", np.array([1.0, 0, 0]), np.array([0, 0, 1.0]), 1, concept, True)
    return PO.Scene(pos, tri, np.array(["body"] * len(pos), dtype=object), {"front": view})


def spill(scene):
    mask = D.view_state(scene.pos, scene.tri, scene.views["front"])[1]
    return S.coupling(scene.views["front"].concept, mask)


class TestOps(unittest.TestCase):
    def test_erode_removes_red_without_much_bare(self):
        scene = box_scene(2.4)
        before = spill(scene)
        for _ in range(12):
            scene.erode_toward_view("front", px=8.0, margin=0)
        after = spill(scene)
        self.assertGreater(before["spill"], 0.15)
        self.assertLess(after["spill"], 0.03)
        self.assertLess(after["uncovered"] - before["uncovered"], 0.01)

    def test_erode_leaves_a_model_inside_the_sheet_alone(self):
        scene = box_scene(1.0)
        before = scene.pos.copy()
        self.assertEqual(scene.erode_toward_view("front"), 0)
        np.testing.assert_array_equal(scene.pos, before)

    def test_part_helpers(self):
        scene = box_scene(1.0)
        scene.bones[:4] = "leg"
        top = scene.pos[4:].copy()
        scene.shrink_part("leg", "x", 0.5)
        scene.move_part("leg", dz=0.1)
        self.assertAlmostEqual(np.ptp(scene.pos[:4, 0]), 0.5)
        self.assertAlmostEqual(scene.pos[0, 2], 0.1 * scene.H)
        np.testing.assert_array_equal(scene.pos[4:], top)
        with self.assertRaises(KeyError):
            scene.mask("tail")

    def test_snap_feet(self):
        scene = box_scene(1.0)
        scene.pos[:, 2] += 0.3
        scene.snap_feet_to_ground()
        self.assertAlmostEqual(scene.pos[:, 2].min(), 0.0)


class TestMcp(unittest.TestCase):
    def test_protocol(self):
        get = mock.Mock()
        init = polish_mcp.handle(get, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
        self.assertEqual(init["result"]["serverInfo"]["name"], "polish")
        self.assertIsNone(polish_mcp.handle(get, {"jsonrpc": "2.0", "method": "notifications/initialized"}))
        names = [t["name"] for t in polish_mcp.handle(get, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]]
        self.assertEqual(names, ["state", "views", "inspect", "apply", "done"])
        get.assert_not_called()                      # listing tools does not build the session (it measures the gate)

    def test_tool_error_is_a_result(self):
        reply = polish_mcp.handle(mock.Mock(side_effect=ValueError("boom")), {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "state"}})
        self.assertTrue(reply["result"]["isError"])


def table(**spill_by_view):
    return {v: {"iou": 0.8, "spill": s, "bare": 0.05, "contact": 0.3} for v, s in spill_by_view.items()}


def session(base, tmp):
    s = object.__new__(polish.Session)
    lint = {"tris": 700, "flipped": 0, "degenerate": 0, "nonmanifold_edges": 0, "sliver_pct": 2.0}
    s.__dict__.update(id="u", noise=None, base=base, table=base, ops=[], base_lint=lint, max_ops=12, budget=600.0, run=pathlib.Path(tmp), work=pathlib.Path(tmp),
                      cur=pathlib.Path(tmp) / "cur.glb", sheet=pathlib.Path("s.jpg"), layout="unit", cams={}, done_summary=None, sil=pathlib.Path(tmp), t0=__import__("time").monotonic())
    s.cur.write_bytes(b"old")
    return s, lint


class TestApply(unittest.TestCase):
    def apply(self, s, lint, after):
        ran = mock.Mock(returncode=0, stdout='{"moved": 3}', stderr="")

        def fake_run(cmd, **kw):
            pathlib.Path(cmd[4]).write_bytes(b"new")
            return ran
        with mock.patch.object(polish.subprocess, "run", fake_run), mock.patch.object(s, "measure", return_value=(s.work, after)), \
                mock.patch.object(polish.ML, "lint", return_value=lint):
            return s.apply("pass", "test op")

    def test_worse_view_is_reverted(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, lint = session(table(front=0.10, left=0.10), tmp)
            out = self.apply(s, lint, table(front=0.05, left=0.12))
            self.assertTrue(out["result"].startswith("rejected: left spill"))
            self.assertEqual(s.cur.read_bytes(), b"old")
            self.assertEqual(s.table["left"]["spill"], 0.10)

    def test_better_state_is_kept_and_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, lint = session(table(front=0.10, left=0.10), tmp)
            out = self.apply(s, lint, table(front=0.05, left=0.10))
            self.assertEqual(out["result"], "accepted")
            self.assertEqual(s.cur.read_bytes(), b"new")
            self.assertEqual(out["delta"]["front"]["spill"], -0.05)

    def test_dry_run_keeps_nothing_and_spends_no_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, lint = session(table(front=0.10), tmp)
            ran = mock.Mock(returncode=0, stdout='{"moved": 3}', stderr="")
            with mock.patch.object(polish.subprocess, "run", lambda cmd, **kw: (pathlib.Path(cmd[4]).write_bytes(b"new"), ran)[1]), \
                    mock.patch.object(s, "measure", return_value=(s.work, table(front=0.05))), mock.patch.object(polish.ML, "lint", return_value=lint):
                out = s.apply("pass", "try", dry_run=True)
            self.assertIn("would be accepted", out["result"])
            self.assertEqual((s.cur.read_bytes(), s.ops, s.table["front"]["spill"]), (b"old", [], 0.10))

    def test_lint_and_tris_revert(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, lint = session(table(front=0.10), tmp)
            out = self.apply(s, lint | {"tris": 702, "flipped": 1}, table(front=0.05))
            self.assertIn("tris 700 -> 702", out["result"])
            self.assertIn("flipped", out["result"])

    def test_cumulative_drift_against_the_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, lint = session(table(front=0.10), tmp)
            s.table = table(front=0.104)
            s.ops = [{"status": "accepted"}]
            self.assertIn("vs start", self.apply(s, lint, table(front=0.108))["result"])

    def test_budget_ends_the_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, lint = session(table(front=0.10), tmp)
            s.max_ops = 0
            self.assertIn("budget exhausted", self.apply(s, lint, table(front=0.0))["result"])


class TestReplay(unittest.TestCase):
    def test_script_roundtrip(self):
        ops = [{"n": 1, "status": "accepted", "why": "a", "code": "x = 1\n"}, {"n": 2, "status": "rejected", "why": "b", "code": "y"},
               {"n": 3, "status": "accepted", "why": "c", "code": "for i in range(2):\n    pass"}]
        self.assertEqual(polish.blocks(polish.script_of(ops)), [("a", "x = 1\n"), ("c", "for i in range(2):\n    pass\n")])

    def test_replay_applies_the_recorded_codes_in_order(self):
        seen = []
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(polish, "Session") as cls:
            cls.return_value.apply.side_effect = lambda code, why: seen.append((why, code)) or {"result": "accepted"}
            script = pathlib.Path(tmp) / "polish.py"
            script.write_text(polish.script_of([{"n": 1, "status": "accepted", "why": "w1", "code": "a"}, {"n": 2, "status": "accepted", "why": "w2", "code": "b"}]))
            polish.replay(mock.Mock(replay=script, id="u", sheet=None, rig=None), pathlib.Path(tmp))
        self.assertEqual(seen, [("w1", "a\n"), ("w2", "b\n")])


if __name__ == "__main__":
    unittest.main()
