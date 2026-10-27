"""python3 -m unittest discover -s tests/tools/blender"""
import copy
import json
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))

import colour_stage as CS  # noqa: E402

SPEC = {"rig": "biped",
        "palette": {"iron": {"surface": "metal", "color": "#76716E"},
                    "lamp": {"surface": "glow", "color": "#F2B632"}},
        "parts": [["head", "box", [1, 1, 1], [0, 1, 0], "iron", {"decal": "eyes2"}],
                  ["spine", "box", [1, 1, 1], [0, 0, 0], "iron", {}]]}


def edit(fn):
    spec = copy.deepcopy(SPEC)
    fn(spec)
    return spec


class ColourContract(unittest.TestCase):
    def test_palette_and_decal_may_change(self):
        new = CS.apply_colour(SPEC, {"palette": {"iron": {"color": "#445566", "surface": "stone"}},
                                     "decals": {"0": {"decal": "face", "decal_color": "#FFAA00"}}})
        self.assertEqual(new["palette"]["iron"]["surface"], "stone")
        self.assertEqual(new["parts"][0][5], {"decal": "face", "decal_color": "#FFAA00"})
        self.assertEqual(SPEC["parts"][0][5], {"decal": "eyes2"})      # the input is not touched

    def test_a_part_change_is_rejected(self):
        for change in (lambda s: s["parts"][1].__setitem__(2, [2, 2, 2]),
                       lambda s: s["parts"][1].__setitem__(4, "lamp"),
                       lambda s: s["parts"].pop(),
                       lambda s: s["parts"][1][5].update(sides=6),
                       lambda s: s.update(rig="spider")):
            with self.assertRaises(ValueError):
                CS.validate_colour(SPEC, edit(change))

    def test_a_reply_cannot_carry_parts_or_new_slots(self):
        with self.assertRaises(ValueError):
            CS.apply_colour(SPEC, {"parts": SPEC["parts"]})
        with self.assertRaises(ValueError):
            CS.apply_colour(SPEC, {"palette": {"gold": {"color": "#AA8850", "surface": "metal"}}})

    def test_bad_colours_and_decals_are_rejected(self):
        for patch in ({"palette": {"iron": {"color": "grey"}}},
                      {"palette": {"iron": {"surface": "velvet"}}},
                      {"decals": {"0": {"decal": "smile"}}},
                      {"decals": {"1": {"decal": "eyes2"}}}):      # spine is no face bone
            with self.assertRaises(ValueError):
                CS.apply_colour(SPEC, patch)


class Ramp(unittest.TestCase):
    def test_validator_accepts_a_valid_ramp_and_rejects_the_rest(self):
        for ramp in ([0.3, 0.6], (0.0, 1.0)):
            CS.validate_colour(SPEC, edit(lambda s, r=ramp: s["palette"]["iron"].update(ramp=r)))
        for ramp in ([0.6, 0.3], [0.3], [0.3, 1.2], "x"):
            with self.assertRaises(ValueError, msg=ramp):
                CS.validate_colour(SPEC, edit(lambda s, r=ramp: s["palette"]["iron"].update(ramp=r)))

    def test_with_ramps_gives_each_slot_its_nearest_sheet_zone_ramp(self):
        sheet = ROOT / "artifacts/model-sheets/refs/n01X/sheet.jpg"
        out = CS.with_ramps(SPEC, sheet)
        self.assertNotIn("ramp", SPEC["palette"]["iron"])               # the input is not touched
        for entry in out["palette"].values():
            lo, hi = entry["ramp"]
            self.assertTrue(0 <= lo <= hi <= 1)
        CS.validate_colour(SPEC, out)                                   # a colour pass may carry it


class Face(unittest.TestCase):
    def test_face_png_only_for_a_sheet_decal(self):
        args = types.SimpleNamespace(sheet="sheet.jpg")
        self.assertEqual(CS.face_args(SPEC, args, pathlib.Path("w")), [])
        spec = edit(lambda s: s["parts"][0][5].update(decal="sheet"))
        with mock.patch("split_sheet.head_face", return_value=pathlib.Path("w/face.png")) as cut:
            self.assertEqual(CS.face_args(spec, args, pathlib.Path("w")), ["face=w/face.png"])
        cut.assert_called_once_with(pathlib.Path("sheet.jpg"), pathlib.Path("w/face.png"))

    def test_sheet_is_a_decal_kind_a_colour_pass_may_set(self):
        CS.validate_colour(SPEC, edit(lambda s: s["parts"][0][5].update(decal="sheet")))


class Gate(unittest.TestCase):
    def test_tilts_text_round_trips_through_parse_tilts(self):
        from views import parse_tilts
        tilts = {"top": 10, "bottom": -20, "rts": (35, 30)}
        self.assertEqual(parse_tilts(CS.tilts_text(tilts)), tilts)

    def test_every_measured_view_must_hold_and_none_measured_fails(self):
        ok = {"mean": 0.3, "cover": 0.6, "fails": [], "lost": []}
        self.assertEqual(CS.gate({"front": ok, "top": ok}), (True, []))
        self.assertEqual(CS.gate({"front": ok, "top": {**ok, "fails": ["cover"]}}), (False, ["top"]))
        self.assertEqual(CS.gate({}), (False, []))


class SharedAtlas(unittest.TestCase):
    """--atlas shared reaches build_unit as shared=<atlas dir>/<race>.json, on a cel build only."""

    def built_with(self, **over):
        args = types.SimpleNamespace(id="n005", kind="mass", sheet="s.jpg", texture="cel", race="Human",
                                     atlas_dir="/a", props=None, **over)
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(CS, "run") as run:
            CS.build_textured(SPEC, pathlib.Path("clay.glb"), args, pathlib.Path(tmp) / "m.glb", pathlib.Path(tmp))
        return run.call_args.args

    def test_shared_and_cull_flags_are_passed_to_the_build(self):
        call = self.built_with(atlas="shared", cull=True)
        self.assertIn("shared=/a/human.json", call)
        self.assertIn("cull=remove", call)

    def test_default_build_has_neither(self):
        call = self.built_with(atlas="own")
        self.assertFalse([a for a in call if str(a).startswith(("shared=", "cull"))])

    def test_a_painted_build_ignores_shared(self):
        args = types.SimpleNamespace(atlas="shared", texture="painted", race="Human", atlas_dir="/a")
        self.assertEqual(CS.shared_args(args), [])


class Stage(unittest.TestCase):
    def test_report_section_and_files(self):
        zone = {"mean": 0.3, "cover": 0.6, "fails": [], "lost": [], "zones": {}}
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            built = tmp / "built"
            (built / "views").mkdir(parents=True)
            (built / "model.glb").write_bytes(b"glb")
            (built / "views" / "model-front.png").write_bytes(b"png")
            (tmp / "work").mkdir()
            args = types.SimpleNamespace(id="n01X", tag="n01X", out=tmp, texture="cel", colour_pass=0)
            with mock.patch.object(CS, "attempt",
                                   return_value=(built / "model.glb", {"front": zone, "top": zone}, built)):
                ok, md = CS.stage_colour(SPEC, tmp / "clay.glb", args, {"top": 10}, tmp / "work")
            self.assertTrue(ok)
            self.assertIn("## Stage 2 — colour", md)
            self.assertIn("top:10", md)
            self.assertTrue((tmp / "model.glb").exists() and (tmp / "views/n01X/model-front.png").exists())
            self.assertEqual(json.loads((tmp / "spec-colour.json").read_text()), SPEC)


if __name__ == "__main__":
    unittest.main()
