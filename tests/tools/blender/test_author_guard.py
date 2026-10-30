"""python3 -m unittest discover -s tests/tools/blender"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import author_guard as G  # noqa: E402


def part(bone, w, mat="z1", **opts):
    return [bone, "box", [w, 0.1, 0.1], [0, 1, 0], mat, opts]


MASS = {"parts": [part("spine", .4), part("arm.L", .1)], "palette": {"z1": {"color": "#111111"}}}
AUTHOR = {"parts": [part("spine", .5, "skin"), part("arm.L", .3, "skin"), part("spine", .1, "belt", prop="pack")],
          "palette": {"skin": {"color": "#222222"}}, "rig": "biped"}


class FakeProxy:
    """left IoU is high only with the massing's arm; front only with the massing's spine."""
    def ious(self, parts):
        arm = [p for p in parts if p[0] == "arm.L" and p[2][0] == .1]
        spine = [p for p in parts if p[0] == "spine" and p[2][0] == .4]
        return {"left": .9 if arm else .5, "front": .9 if spine else .8}


class Drops(unittest.TestCase):
    def test_threshold(self):
        mass = {"front": .8, "left": .8, "top": .8}
        author = {"front": .79, "left": .78, "top": .9, "rts": .1}
        self.assertEqual(G.drops(mass, author), ["left"])      # -.01 is at the limit and passes
        self.assertEqual(G.drops(mass, mass), [])


class Revert(unittest.TestCase):
    def test_reverts_the_bone_of_the_dropped_view(self):
        spec, done = G.revert(AUTHOR, MASS, FakeProxy(), ["left"], {"left": .3})
        self.assertEqual(done, ["arm.L"])
        self.assertEqual([p[2][0] for p in spec["parts"] if p[0] == "arm.L"], [.1])
        self.assertEqual([p[2][0] for p in spec["parts"] if p[0] == "spine"], [.5, .1])     # untouched, prop kept
        self.assertIn("z1", spec["palette"])
        self.assertIn("skin", spec["palette"])

    def test_nothing_falls_nothing_reverted(self):
        spec, done = G.revert(AUTHOR, MASS, FakeProxy(), ["left"], {"left": 0.0})
        self.assertEqual((done, spec), ([], AUTHOR))

    def test_no_bone_helps(self):
        class Flat:
            def ious(self, parts):
                return {"left": .5}
        self.assertEqual(G.revert(AUTHOR, MASS, Flat(), ["left"], {"left": .3})[1], [])


class Reject(unittest.TestCase):
    def test_massing_body_author_props(self):
        spec = G.reject(AUTHOR, MASS)
        self.assertEqual([(p[0], p[2][0]) for p in spec["parts"]], [("spine", .4), ("arm.L", .1), ("spine", .1)])
        self.assertEqual([p[2][0] for p in G.reject(AUTHOR, MASS, props=False)["parts"]], [.4, .1])
        self.assertEqual(spec["rig"], "biped")
        self.assertEqual(set(spec["palette"]), {"z1", "skin"})


class Stage(unittest.TestCase):
    """spec_pipeline.guard_stage with the builds stubbed: off does nothing, no drop leaves the spec, a drop reverts, else rejects."""
    def run_stage(self, mode, author_iou, fixed=True):
        import tempfile
        import types
        from unittest import mock

        import spec_pipeline as SP
        rows = {"massing": {"left": {"iou": .8, "spill": .1}}}
        rows["author"] = {"left": {"iou": author_iou, "spill": .2}}
        good, bad = {"left": {"iou": .8, "spill": .1}}, {"left": {"iou": .5, "spill": .1}}
        measure = lambda spec, args, layout, work, name: rows.get(name) or (good if fixed else bad)  # noqa: E731
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(SP, "massing_base", return_value=MASS), \
                mock.patch.object(SP, "guard_measure", measure), mock.patch.object(SP, "proxy_ious", return_value=FakeProxy()):
            return SP.guard_stage(AUTHOR, types.SimpleNamespace(author_guard=mode, out=pathlib.Path(tmp)), "mass")

    def test_off(self):
        self.assertEqual(self.run_stage("off", .1), (AUTHOR, None))

    def test_no_drop(self):
        spec, report = self.run_stage("revert", .795)
        self.assertEqual((spec, report["action"]), (AUTHOR, "intact"))

    def test_drop_that_revert_does_not_fix_rejects(self):
        spec, report = self.run_stage("revert", .5, fixed=False)
        self.assertEqual(report["action"], "reject-bare")
        self.assertEqual([p[2][0] for p in spec["parts"]], [.4, .1])

    def test_drop_reverts(self):
        spec, report = self.run_stage("revert", .5)
        self.assertEqual((report["action"], report["reverted"], report["drops"]), ("revert", ["arm.L"], ["left"]))
        self.assertNotEqual(spec, AUTHOR)


class MeasureTilt(unittest.TestCase):
    """L13-2: the pinned --tilts of the run never reach a guard candidate's own camera sweep."""
    def test_candidate_sweeps_its_own_tilts(self):
        import tempfile
        import types
        from unittest import mock

        import spec_pipeline as SP
        seen = []
        args = types.SimpleNamespace(tilts="top:-20,bottom:20", out=pathlib.Path("."), summary={"keep": 1})
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(SP, "stage_shape", lambda path, a, layout: seen.append(a.tilts)):
            SP.guard_measure(MASS, args, "mass", pathlib.Path(tmp), "massing")
        self.assertEqual((seen, args.tilts, args.summary), ([""], "top:-20,bottom:20", {"keep": 1}))


class Repin(unittest.TestCase):
    """guard_repin: the pin follows the spec the guard kept."""
    def repin(self, action, tilts_of_massing):
        import json
        import tempfile
        import types

        import spec_pipeline as SP
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp) / "guard" / "massing"
            d.mkdir(parents=True)
            (d / "silhouette.json").write_text(json.dumps({"tilt": tilts_of_massing}))
            args = types.SimpleNamespace(tilts="top:-20,bottom:20", out=pathlib.Path(tmp))
            SP.guard_repin(args, {"action": action})
            return args.tilts

    def test_massing_body_takes_massing_cameras(self):
        self.assertEqual(self.repin("reject-bare", {"top": 20, "bottom": -20, "rts": [55, -30]}), "bottom:-20,rts:55/-30,top:20")

    def test_intact_and_skipped_keep_the_pin(self):
        self.assertEqual(self.repin("intact", {"top": 20}), "top:-20,bottom:20")
        self.assertEqual(self.repin("skipped", {"top": 20}), "top:-20,bottom:20")


class FitGuard(unittest.TestCase):
    """spec_pipeline.guard_fit: a fit that pushes a view under the massing's keeps the spec as it was."""
    def run_fit(self, final):
        import tempfile
        import types
        from unittest import mock

        import spec_pipeline as SP
        report = {"action": "intact", "rows": {"massing": {"left": {"iou": .8, "spill": 0}}}}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(SP, "stage_shape", return_value="rebuilt"), \
                mock.patch.object(SP, "add_times"):
            args = types.SimpleNamespace(guard_report=report, summary={"approved": final, "spill": {}}, out=pathlib.Path(tmp))
            return SP.guard_fit(args, MASS, AUTHOR, "fitted", "mass"), report

    def test_fit_kept(self):
        self.assertEqual(self.run_fit({"left": .85})[0], (AUTHOR, "fitted"))

    def test_fit_dropped(self):
        (spec, shape), report = self.run_fit({"left": .7})
        self.assertEqual((spec, shape, report["fit_drops"]), (MASS, "rebuilt", ["left"]))


if __name__ == "__main__":
    unittest.main()
