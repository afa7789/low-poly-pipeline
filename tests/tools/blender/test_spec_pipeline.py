"""python3 -m unittest discover -s tests/tools/blender"""
import json
import pathlib
import sys
import types
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import rig_families as RF  # noqa: E402
import silhouette  # noqa: E402
import spec_pipeline as SP  # noqa: E402

PARTS = [
    ["spine", "prism", [0.4, 0.4, 0.8], [0, 1.8, 0], "iron", {"sides": 8}],
    ["head", "box", [0.2, 0.2, 0.2], [0, 2.4, 0], "iron", {}],
    ["pelvis", "frustum", [0.5, 0.3, 0.3], [0, 1.3, 0], "darkiron", {}],
]


def reply(patch):
    return "here you go\n" + json.dumps(patch)


class ApplyPatch(unittest.TestCase):
    def test_set_drop_add_keep_the_rest(self):
        new = ["head", "box", [0.3, 0.2, 0.2], [0, 2.4, 0], "brass", {}]
        extra = ["spine", "box", [0.1, 0.1, 0.1], [0, 1.9, 0.3], "lamp", {}]
        parts, why = SP.apply_patch(PARTS, reply({"set": {"1": new}, "drop": [2],
                                                  "add": [extra], "why": "wider head"}))
        self.assertCountEqual([p[0] for p in parts], [PARTS[0][0], new[0], extra[0]])   # normalised: rig order, grid
        self.assertEqual(why, "wider head")

    def test_too_many_edits_is_rejected(self):
        drops = list(range(SP.PASS_EDITS + 1))
        with self.assertRaises(ValueError):
            SP.apply_patch(PARTS, reply({"drop": drops}))

    def test_repair_limit_allows_larger_patch(self):
        sets = {str(i % 3): PARTS[i % 3] for i in range(3)}
        drops = list(range(SP.PASS_EDITS))
        with self.assertRaises(ValueError):
            SP.apply_patch(PARTS * 3, reply({"set": sets, "drop": drops}))
        parts, _ = SP.apply_patch(PARTS * 3, reply({"set": sets, "drop": drops}),
                                  SP.REPAIR_EDITS)
        self.assertEqual(len(parts), 9 - SP.PASS_EDITS)

    def test_patch_outside_schema_is_rejected(self):
        bad = ["tail", "box", [0.1, 0.1, 0.1], [0, 1, 0], "iron", {}]
        with self.assertRaises(ValueError):
            SP.apply_patch(PARTS, reply({"set": {"0": bad}}))

    def test_bare_bone_names_are_quoted(self):
        parts, _ = SP.apply_patch(PARTS, '{"set": {"1": [head, "box", [0.3, 0.2, 0.2], '
                                         '[0, 2.4, 0], "iron", {}]}}')
        self.assertEqual([p[0] for p in parts].count("head"), 1)   # quoted, then ordered by the rig


class ParseSpec(unittest.TestCase):
    def test_from_to_limb_without_at_gets_the_midpoint(self):
        limb = ["thigh.L", "prism", [0.1, 0.08, 0.6], None, "iron",
                {"from": [0.3, 1.2, 0], "to": [0.3, 0.6, 0.1]}]
        spec = SP.parse_spec(json.dumps({"parts": [PARTS[0], limb]}))
        thigh = next(p for p in spec["parts"] if p[0] == "thigh.L")
        for got, want in zip(thigh[3], [0.3, 0.9, 0.05]):
            self.assertAlmostEqual(got, want, delta=0.01)   # on the H/256 grid

    def test_missing_at_without_span_is_rejected(self):
        bad = ["head", "box", [0.2, 0.2, 0.2], None, "iron", {}]
        with self.assertRaises(ValueError):
            SP.parse_spec(json.dumps({"parts": [bad]}))


class Palette(unittest.TestCase):
    PALETTE = {"hide": {"surface": "leather", "color": "#6B4423"},
               "eye": {"surface": "glow", "color": "#FFD24A"}}

    def test_palette_slots_are_materials(self):
        part = ["head", "box", [0.2, 0.2, 0.2], [0, 2.4, 0], "hide", {}]
        spec = SP.parse_spec(json.dumps({"palette": self.PALETTE, "parts": [part]}))
        self.assertEqual(spec["palette"], self.PALETTE)
        with self.assertRaises(ValueError):          # undeclared slot
            SP.parse_spec(json.dumps({"parts": [part]}))

    def test_unknown_surface_or_bad_colour_is_rejected(self):
        for entry in ({"surface": "velvet", "color": "#112233"},
                      {"surface": "cloth", "color": "red"}):
            with self.assertRaises(ValueError):
                SP.parse_spec(json.dumps({"palette": {"x": entry}, "parts": PARTS}))

    def test_alpha_must_be_an_opacity(self):
        glass = {"surface": "glass", "color": "#AACCDD", "alpha": 0.4}
        part = ["head", "box", [0.2, 0.2, 0.2], [0, 2.4, 0], "lens", {}]
        spec = SP.parse_spec(json.dumps({"palette": {"lens": glass}, "parts": [part]}))
        self.assertEqual(spec["palette"]["lens"]["alpha"], 0.4)
        for bad in (0.0, 1.5, "half"):
            with self.assertRaises(ValueError):
                SP.parse_spec(json.dumps({"palette": {"lens": {**glass, "alpha": bad}},
                                          "parts": [part]}))

    def test_decal_names_are_checked(self):
        head = ["head", "box", [0.2, 0.2, 0.2], [0, 2.4, 0], "iron", {"decal": "eyes2"}]
        self.assertEqual(SP.parse_spec(json.dumps({"parts": [head]}))["parts"][0][5]["decal"], "eyes2")
        head[5] = {"decal": "mouth"}
        with self.assertRaises(ValueError):
            SP.parse_spec(json.dumps({"parts": [head]}))

    def test_decal_only_on_a_head_bone(self):
        for bone, ok in (("head", True), ("jaw", True), ("rider.head", True),
                         ("spine", False), ("arm.L", False)):
            part = [bone, "prism", [0.2, 0.2, 0.2], [0, 2.4, 0], "iron", {"decal": "mask"}]
            with self.subTest(bone=bone):
                if ok:
                    SP.validate([part], extra=("jaw", "rider.head"))
                else:
                    with self.assertRaisesRegex(ValueError, "non-head bone"):
                        SP.validate([part])

    def test_normalise_keeps_a_rot_triple(self):
        part = ["arm.L", "prism", [0.2, 0.2, 0.4], [0.6, 1.8, 0], "iron", {"rot": [0, 0, 15]}]
        self.assertEqual(SP.normalise([part])[0][5]["rot"], [0, 0, 15])
        part[5] = {"rot": "15"}
        self.assertNotIn("rot", SP.normalise([part])[0][5])

    def test_rot_is_limited_to_60_degrees(self):
        for rot, ok in ((0, True), (-45, True), ([0, 0, 15], True), ([60, -60, 0], True),
                        (61, False), ([0, 0, 75], False), ([0, 0], False), ("15", False)):
            part = ["arm.L", "prism", [0.2, 0.2, 0.4], [0.6, 1.8, 0], "iron", {"rot": rot}]
            with self.subTest(rot=rot):
                if ok:
                    SP.validate([part])
                else:
                    with self.assertRaisesRegex(ValueError, "rot outside"):
                        SP.validate([part])

    def test_cut_is_sheet_on_an_unrotated_mass(self):
        for kind, opts, ok in (("prism", {"cut": "sheet"}, True), ("frustum", {"cut": "sheet"}, True),
                               ("box", {"cut": "sheet", "rot": 10}, False), ("cyl", {"cut": "sheet"}, False),
                               ("prism", {"cut": "sheet", "from": [0, 1, 0], "to": [0, 2, 0]}, False),
                               ("prism", {"cut": "yes"}, False)):
            part = ["spine", kind, [0.4, 0.4, 0.8], [0, 1.8, 0], "iron", opts]
            with self.subTest(kind=kind, opts=opts):
                if ok:
                    SP.validate([part])
                else:
                    with self.assertRaisesRegex(ValueError, "cut"):
                        SP.validate([part])

    def test_legacy_specs_need_no_palette(self):
        self.assertNotIn("palette", SP.parse_spec(json.dumps({"parts": PARTS})))

    def test_patch_may_use_palette_slots(self):
        new = ["head", "box", [0.3, 0.2, 0.2], [0, 2.4, 0], "eye", {}]
        parts, _ = SP.apply_patch(PARTS, reply({"set": {"1": new}}), palette=self.PALETTE)
        self.assertIn("eye", [p[4] for p in parts])

    def test_refinement_prompt_shows_the_fixed_palette(self):
        text = SP.numbered({"palette": self.PALETTE, "parts": PARTS})
        self.assertIn("use only these slot names", text)
        self.assertIn("  0: ", text)


class Rig(unittest.TestCase):
    def tearDown(self):
        SP.set_rig("biped")

    def test_spider_bones_parse_and_bare_names_are_quoted(self):
        SP.set_rig("spider")
        spec = SP.parse_spec('{"parts": [[leg3.upper, "prism", [0.05, 0.04, 0.5], '
                             '[0.2, 0.5, 0.2], "iron", {}]]}')
        self.assertEqual(spec["parts"][0][0], "leg3.upper")

    def test_biped_bone_is_outside_the_spider(self):
        SP.set_rig("spider")
        with self.assertRaises(ValueError):
            SP.parse_spec(json.dumps({"parts": [PARTS[0]]}))

    def test_biped_aliases_only_apply_to_bipeds(self):
        part = ["chest", "box", [0.1, 0.1, 0.1], [0, 1.8, 0], "iron", {}]
        self.assertEqual(SP.parse_spec(json.dumps({"parts": [part]}))["parts"][0][0], "spine")
        SP.set_rig("quadruped")
        with self.assertRaises(ValueError):
            SP.parse_spec(json.dumps({"parts": [part]}))

    def test_extra_bones_join_the_rig(self):
        SP.set_rig("vehicle")
        part = ["mast", "cyl", [0.05, 1.0], [0, 1.0, 0], "iron", {}]
        bones = [["mast", "hull", [0, 0.5, 0], [0, 1.5, 0]]]
        spec = SP.parse_spec(json.dumps({"bones": bones, "parts": [part]}))
        self.assertEqual(spec["bones"], bones)
        self.assertIn("extra bones", SP.numbered(spec))
        with self.assertRaises(ValueError):          # parent unknown to the vehicle
            SP.parse_spec(json.dumps({"bones": [["mast", "spine", [0, 0, 0], [0, 1, 0]]],
                                      "parts": [part]}))
        with self.assertRaises(ValueError):          # bone used but not declared
            SP.parse_spec(json.dumps({"parts": [part]}))

    def test_every_family_has_brief_text(self):
        for fam in SP.RF.FAMILIES:
            self.assertIn("bones", SP.rig_text(fam)[1], fam)

    def test_non_biped_brief_drops_biped_landmarks(self):
        m = {"front_width_profile": [0.5] * 21, "left_width_profile": [0.3] * 21}
        text = SP.measured_text("spider", m)
        self.assertIn("Side silhouette", text)
        self.assertNotIn("shoulder span", text)
        self.assertIn("eight-legged", SP.rig_text("spider")[1])
        self.assertIn("ARCHES", SP.rig_text("spider_high")[1])


class ScaledSpiderBrief(unittest.TestCase):
    M = {"body_r": 0.3, "body_len": 0.8, "body_under": 0.25, "knee_h": 0.45, "knee_r": 0.6, "foot_r": 0.45}

    def tearDown(self):
        SP.RF.FAMILIES["spider"] = SP.RF.SPIDER
        SP.set_rig("biped")

    def test_measures_scale_the_rig_reach_the_spec_and_the_brief(self):
        SP.set_rig("spider", self.M)
        self.assertEqual(SP.RIG_MEASURE, self.M)
        part = ["leg1.upper", "prism", [0.1, 0.1, 0.5], [0.2, 0.3, 0.1], "iron", {"sides": 6}]
        self.assertEqual(SP.parse_spec(json.dumps({"parts": [part]}))["rig_measure"], self.M)
        m = {"front_width_profile": [0.5] * 21, "left_width_profile": [0.3] * 21, "spider": self.M}
        self.assertIn("SPIDER BODY", SP.measured_text("spider", m))
        self.assertNotIn("LEG RADIUS", SP.measured_text("spider", m))
        m["spider"] = {**self.M, "leg_w": 0.05, "leg_taper": 0.5}
        self.assertIn("LEG RADIUS: 0.067 H at the body, 0.033 H at the tip", SP.measured_text("spider", m))
        self.assertIn("exactly as the rig table", SP.rig_text("spider")[1])

    def test_no_measures_keeps_the_fixed_rig(self):
        SP.set_rig("spider")
        self.assertIsNone(SP.RIG_MEASURE)
        self.assertNotIn("rig_measure", SP.parse_spec(json.dumps({"parts": [
            ["leg1.upper", "prism", [0.1, 0.1, 0.5], [0.2, 0.3, 0.1], "iron", {"sides": 6}]]})))
        self.assertIsNone(SP.set_rig("vehicle", self.M))   # measures are for the families rig_families.SCALERS names
        self.assertIsNone(SP.RIG_MEASURE)


class MassingCarriesItsRig(unittest.TestCase):
    """A chain finds its bones through the spec's rig: the pre-spec of a scaled family names it (22.L4-4b)."""

    def tearDown(self):
        RF.FAMILIES.update(RF.FIXED)
        RF._drop_caches()
        SP.set_rig("biped")

    def test_wyrm_pre_spec_has_rig_and_measure(self):
        sheet = SP.REFS / "n00H" / "sheet.jpg"
        SP.set_rig("wyrm", silhouette.measure_rig("wyrm", sheet))
        args = types.SimpleNamespace(no_massing=False, spec=None, rig="wyrm", sheet=sheet, race="", build=sheet)
        spec = SP.massing_spec(args)
        self.assertEqual(spec["rig"], "wyrm")
        self.assertIn("line", spec["rig_measure"])


class HardFirst(unittest.TestCase):
    def test_hard_first_note_leads_the_references(self):
        text = SP.with_refs("BRIEF", [("props", None)], hard_first=True)
        self.assertLess(text.index("Image 1 is the faceted"), text.index("Image 2 is the same unit's props"))

    def test_no_refs_no_note_leaves_the_brief(self):
        self.assertEqual(SP.with_refs("BRIEF", []), "BRIEF")

    def test_prop_crops_are_named_from_props_json_in_order(self):
        props = [{"name": "tank", "where": "on the back"}, {"name": "lamp", "where": "on the hip"}]
        text = SP.with_refs("B", [("prop", None), ("prop", None)], props=props)
        self.assertLess(text.index("'tank'"), text.index("'lamp'"))
        self.assertIn("Image 3 is a close crop of the prop 'lamp'", text)

    def test_props_text_lists_bone_and_size_or_nothing(self):
        self.assertEqual(SP.props_text([]), "")
        text = SP.props_text([{"name": "tank", "where": "on the back", "bones": ["spine"],
                               "extent": [0.25, 0.55]}])
        self.assertIn("1. tank - on the back; on bone spine; longest side 0.25-0.55 H", text)

    def test_approved_ref_says_it_is_the_contract(self):
        self.assertIn("contract", SP.with_refs("B", [("approved", None)]))

    def test_coupling_rows(self):
        red = {"band": 5, "lo": 0.625, "hi": 0.75, "share": 0.09, "blob": None}
        rows = SP.iou_rows({"approved": {"front": 0.8}, "uncovered": {"front": 0.12}, "spill": {"front": 0.05},
                            "red": {"front": red}})
        self.assertIn("| uncovered (report, /sheet area) | 0.120 / - / - / - / - / - |", rows)
        self.assertIn("| worst red front | band 5 (0.62-0.75 H), 9 % of sheet |", rows)

    def test_iou_rows_list_each_sheet(self):
        rows = SP.iou_rows({"approved": {"front": 0.8, "left": 0.7, "back": 0.6},
                            "hard": {"front": 0.9}, "drift": {}})
        self.assertIn("IoU vs approved | 0.800 / 0.700 / 0.600 / - / - / - |", rows)
        self.assertIn("IoU vs hard", rows)
        self.assertNotIn("drift", rows)

    def test_zones_clay_rows_and_failed_build(self):
        from unittest import mock
        z = {"front": {"mean": 0.6, "cover": 0.9, "lost": []}}
        rows = SP.iou_rows({"approved": {"front": 0.8}, "zones_clay": z})
        self.assertIn("| zones_clay mean (report) | 0.600 / - / - / - / - / - |", rows)
        self.assertIn("| zones_clay cover (report) | 0.900 / ", rows)
        args = mock.Mock(out=pathlib.Path(self.id()), kind="mass", sheet="s", rig=None)
        with mock.patch.object(SP, "tool"), mock.patch.object(SP.cut_hull, "args", return_value=[]), \
                mock.patch.object(pathlib.Path, "read_text", return_value="{}"), \
                mock.patch.object(pathlib.Path, "mkdir"):
            self.assertEqual(SP.zones_clay("spec.json", args, "unit", {}), {})   # no ids.glb: report-only

    def test_iou_rows_show_sd_mean(self):
        rows = SP.iou_rows({"approved": {"front": 0.8}, "chamfer": {"front": 0.02, "left": 0.04}})
        self.assertIn("| SD mean | 0.0300 |", rows)

    def test_iou_rows_show_gates_and_cameras(self):
        rows = SP.iou_rows({"approved": {"front": 0.8, "rts": 0.7}, "gates": {"front": 0.75},
                            "tilt": {"top": 10, "rts": [35, 30]}})
        self.assertIn("gates | 0.750 / - / - / - / - / - |", rows)
        self.assertIn("top 10, rts 35/30", rows)


class FacetText(unittest.TestCase):
    def test_line_per_band_and_empty_without_edges(self):
        self.assertEqual(SP.facet_text({}), "")
        bands = {"torso": {"facets": 6, "direction": "vertical"}, "legs": {"facets": 4, "direction": "mixed"}}
        text = SP.facet_text({"edges": bands})
        self.assertIn("torso: 6 facets vertical; legs: 4 facets.", text)


class Drift(unittest.TestCase):
    SHEET = pathlib.Path(__file__).resolve().parents[3] / "artifacts/model-sheets/refs/hfoo/sheet.jpg"

    @unittest.skipUnless(SHEET.exists(), "hfoo refs not checked out")
    def test_unreadable_hard_sheet_falls_back_to_the_approved(self):
        import subprocess
        import tempfile
        import types
        with tempfile.TemporaryDirectory() as tmp:
            bad = pathlib.Path(tmp) / "sheet-hard.jpg"
            subprocess.run(["magick", "-size", "400x120", "xc:#cccccc", str(bad)], check=True)
            args = types.SimpleNamespace(sheet=self.SHEET, build=bad, id="hfoo")
            self.assertEqual(SP.check_drift(args, "unit"), {})
            self.assertEqual(args.build, self.SHEET)


class Accepted(unittest.TestCase):
    PREV = {"front": 0.70, "left": 0.65, "back": 0.60, "top": 0.5, "bottom": 0.4}

    def scores(self, **kw):
        return {**self.PREV, **kw}

    def test_own_view_must_improve(self):
        self.assertTrue(SP.accepted(self.PREV, self.scores(back=0.62), "back"))
        self.assertFalse(SP.accepted(self.PREV, self.scores(back=0.60), "back"))

    def test_gated_view_may_not_slip(self):
        self.assertFalse(SP.accepted(self.PREV, self.scores(back=0.7, front=0.68), "back"))
        self.assertTrue(SP.accepted(self.PREV, self.scores(back=0.7, front=0.695), "back"))

    def test_failed_build_is_rejected(self):
        self.assertFalse(SP.accepted(self.PREV, None, "left"))

    def test_view_with_no_concept_is_not_compared(self):
        # PREV has no rts: a sheet without a gameplay-camera concept must not raise
        self.assertTrue(SP.accepted(self.PREV, self.scores(back=0.7, rts=0.1), "back"))


class Stages(unittest.TestCase):
    def test_clay_build_takes_the_budget_ceiling_and_the_clay_flag(self):
        self.assertEqual(SP.clay_args("mass"), ["700", "nofuse", "700", "clay"])

    def test_tilts_are_the_sweeps_choice_in_parse_form(self):
        tilts = SP.tilts_of({"front": {"tilt": 0}, "top": {"tilt": 10}, "rts": {"tilt": [35, 30]}})
        self.assertEqual(tilts, {"top": 10, "rts": (35, 30)})

    def test_verdict_needs_both_stages(self):
        ok, bad = {"ok": True}, {"ok": False}
        self.assertEqual(SP.verdict_of(ok, (True, "")), "PASS")
        self.assertEqual(SP.verdict_of(ok, (False, "")), "CHECK")
        self.assertEqual(SP.verdict_of(bad, None), "CHECK")
        self.assertEqual(SP.verdict_of(ok, None), "SHAPE-PASS")   # no colour_stage: ends clean

    def test_review_says_where_a_failed_run_stopped(self):
        import types
        args = types.SimpleNamespace(kind="mass", texture="cel")
        text = SP.stage2_section(args, {"ok": False, "failed": ["silhouette"]}, None)
        self.assertIn("stopped at stage 1, failed: silhouette", text)

    def test_colour_stage_gets_the_contract_arguments(self):
        import tempfile
        import types
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            args = types.SimpleNamespace(out=pathlib.Path(tmp))
            shape = {"glb": "clay.glb", "tilts": {"top": 10}}
            stub = types.SimpleNamespace(stage_colour=mock.Mock(return_value=(False, "report")))
            with mock.patch.dict(sys.modules, {"colour_stage": stub}):
                self.assertEqual(SP.run_colour({"parts": []}, shape, args), (False, "report"))
            stub.stage_colour.assert_called_once_with({"parts": []}, "clay.glb", args, {"top": 10},
                                                      pathlib.Path(tmp) / "stage2")

    def test_missing_colour_stage_is_none(self):
        from unittest import mock
        with mock.patch.dict(sys.modules, {"colour_stage": None}):   # as if the file were absent
            self.assertIsNone(SP.load_colour_stage())


def report(*fails):
    """A preflight stdout: three rules, the named ones FAIL (what preflight.py prints)."""
    rules = ["shoulder_span", "feet_mass", "box_ceiling"]
    lines = "".join(f"  {r.ljust(13)}  {'FAIL' if r in fails else 'PASS'}  detail 1.0\n" for r in rules)
    return lines + "  tri_mix        INFO  legs+feet 40%\n\n1/3 rules pass\n"


class PreflightRules(unittest.TestCase):
    def test_failing_rules_by_name(self):
        self.assertEqual(SP.failing_rules(None), set())
        self.assertEqual(SP.failing_rules(report("shoulder_span", "box_ceiling")),
                         {"shoulder_span", "box_ceiling"})

    def test_unparseable_report_counts_as_a_failure(self):
        self.assertEqual(SP.failing_rules("Traceback ..."), {"<unparsed>"})

    def test_rule_that_passed_may_not_start_failing(self):
        cases = [("fixes one", report("shoulder_span", "feet_mass"), report("feet_mass"), True),
                 ("same failures", report("feet_mass"), report("feet_mass"), True),
                 ("breaks one that held", report("feet_mass"), report("feet_mass", "shoulder_span"), False),
                 ("swaps one for another", report("feet_mass"), report("shoulder_span"), False),
                 ("preflight clean before and after", None, None, True),
                 ("clean spec breaks a rule", None, report("box_ceiling"), False),
                 ("a rule this module never heard of", report(), report() + "  new_rule  FAIL  x\n", False)]
        for label, prev, cur, want in cases:
            with self.subTest(label):
                self.assertIs(SP.rules_hold(prev, cur), want)

    def test_accepted_checks_the_rules(self):
        prev = {"front": 0.7, "left": 0.65}
        cur = {"front": 0.75, "left": 0.65}
        self.assertTrue(SP.accepted(prev, cur, "front", problems=(report("feet_mass"), report("feet_mass"))))
        self.assertFalse(SP.accepted(prev, cur, "front", problems=(report("feet_mass"),
                                                                    report("feet_mass", "shoulder_span"))))


def zones(mean=0.5, pieces=None, gold=0.6, share=0.3):
    """One view's zone report, the shape silhouette.zone_report writes: a gold zone
    (`gold` IoU, `share` of the figure) and a grey one."""
    z = {"#AA8850": {"iou": gold, "share": share}, "#706C68": {"iou": 0.5, "share": 0.6}}
    return {"mean": mean, "zones": z, "pieces": pieces or {"#AA8850@50,29": 0.9, "#706C68@40,60": 0.8}}


class ReviewRows(unittest.TestCase):
    def test_zone_rows_name_the_lost_zone(self):
        z = {"front": {"mean": 0.33, "cover": 0.6, "lost": ["#AA8850"], "zones": {"#AA8850": 0.0}}}
        rows = SP.zone_rows({"zones": {"approved": z}})
        self.assertIn("0.33 / 0.60", rows)
        self.assertIn("LOST #AA8850", rows)
        self.assertEqual(SP.zone_rows({}), "")

    def test_prop_row_warns_only_when_the_prop_is_off(self):
        row = lambda iou: SP.prop_row({"prop": {"parts": [18, 19], "iou": iou, "view": "left"}})  # noqa: E731
        self.assertNotIn("WARN", row(0.83))
        self.assertIn("WARN", row(0.2))
        self.assertIn("no arm-held prop", SP.prop_row({"prop": {"parts": [], "iou": None}}))
        self.assertEqual(SP.prop_row({"prop": None}), "")


class ZonesHold(unittest.TestCase):
    PREV = {"front": zones()}

    def test_cases(self):
        cases = [("same", {"front": zones()}, True),
                 ("small noise", {"front": zones(0.48, {"#AA8850@50,29": 0.8, "#706C68@40,60": 0.7})}, True),
                 ("mean falls", {"front": zones(0.40)}, False),
                 ("a drawn piece (the chest disc) is lost",
                  {"front": zones(pieces={"#AA8850@50,29": 0.1, "#706C68@40,60": 0.8})}, False),
                 ("a whole zone is lost", {"front": zones(gold=0.0)}, False),
                 ("view not measured now", {}, True)]
        for label, cur, want in cases:
            with self.subTest(label):
                self.assertIs(SP.zones_hold(self.PREV, cur), want)

    def test_nothing_to_compare(self):
        self.assertTrue(SP.zones_hold(None, self.PREV))
        self.assertTrue(SP.zones_hold(self.PREV, None))

    def test_a_zone_too_small_to_weigh_may_go(self):
        self.assertTrue(SP.zones_hold({"front": zones(share=0.01)}, {"front": zones(gold=0.0)}))

    def test_accepted_checks_the_zones(self):
        prev = {"front": 0.7, "left": 0.65}
        cur = {"front": 0.75, "left": 0.65}
        self.assertTrue(SP.accepted(prev, cur, "front", zones=(self.PREV, self.PREV)))
        self.assertFalse(SP.accepted(prev, cur, "front", zones=(self.PREV, {"front": zones(0.3)})))


class TiltArg(unittest.TestCase):
    def test_only_tilted_views_are_passed(self):
        report = {"front": {"iou": 0.8, "tilt": 0}, "top": {"iou": 0.7, "tilt": 10},
                  "bottom": {"iou": 0.7, "tilt": 20}}
        self.assertEqual(SP.tilt_arg(report), "tilt=top:10,bottom:20")
        self.assertEqual(SP.tilt_arg({}), "tilt=")

    def test_rts_camera_is_a_pair(self):
        self.assertEqual(SP.tilt_arg({"rts": {"tilt": [55, -30]}}), "tilt=rts:55/-30")


class CountFigures(unittest.TestCase):
    def test_blobs_count_and_small_bits_do_not(self):
        import numpy as np
        m = np.zeros((200, 200), bool)
        m[10:90, 10:60] = True
        self.assertEqual(SP.count_figures(m), 1)
        m[120:190, 120:190] = True                 # a second figure
        self.assertEqual(SP.count_figures(m), 2)
        m[5:9, 150:154] = True                     # a speck is not a figure
        self.assertEqual(SP.count_figures(m), 2)
        m[10:90, 62:64] = True                     # a thin gap is closed: still one blob
        self.assertEqual(SP.count_figures(m), 2)
        m[85:89, 55:125] = True                    # two figures touching by a leg: still two
        self.assertEqual(SP.count_figures(m), 2)
        self.assertEqual(SP.count_figures(np.zeros((9, 9), bool)), 0)


class JointText(unittest.TestCase):
    def test_only_the_readable_joints(self):
        self.assertIn("knee at 0.27 H, elbow at 0.62 H", SP.joint_text({"knee_h": 0.27, "elbow_h": 0.62}))
        self.assertIn("elbow at 0.47 H", SP.joint_text({"elbow_h": 0.47}))
        self.assertNotIn("knee", SP.joint_text({"elbow_h": 0.47}))
        self.assertEqual(SP.joint_text({}), "")


if __name__ == "__main__":
    unittest.main()


class SessionAuthor(unittest.TestCase):
    def test_session_model_goes_to_claude_cli_with_every_image(self):
        from unittest import mock
        reply = mock.Mock(stdout=json.dumps({"result": '{"parts": []}', "is_error": False}), stderr="")
        with mock.patch.object(SP.subprocess, "run", return_value=reply) as run, \
                mock.patch.object(SP, "ask_api") as api:
            self.assertEqual(SP.ask("session:sonnet", "BRIEF", ["/a/x.png", "/b/y.png"]), '{"parts": []}')
        api.assert_not_called()
        argv, prompt = run.call_args.args[0], run.call_args.kwargs["input"]
        self.assertEqual(argv[:4], ["claude", "-p", "--model", "sonnet"])
        self.assertIn("1. /a/x.png", prompt)
        self.assertIn("2. /b/y.png", prompt)
        self.assertTrue(prompt.startswith("BRIEF"))
        self.assertEqual(argv.count("--add-dir"), 2)

    def test_api_model_and_cli_errors(self):
        from unittest import mock
        with mock.patch.object(SP, "ask_api", return_value="ok") as api:
            self.assertEqual(SP.ask("google/gemini-4-argon", "B", []), "ok")
        api.assert_called_once()
        bad = mock.Mock(stdout=json.dumps({"result": "limit", "is_error": True}), stderr="")
        with mock.patch.object(SP.subprocess, "run", return_value=bad), self.assertRaises(RuntimeError):
            SP.ask("session:opus", "B", [])


class AuthorSchema(unittest.TestCase):
    def test_session_gets_the_schema_and_returns_structured_output(self):
        from unittest import mock
        out = {"result": "prose", "structured_output": {"set": {}, "add": [], "drop": [], "why": "x"},
               "is_error": False}
        with mock.patch.object(SP.subprocess, "run", return_value=mock.Mock(stdout=json.dumps(out), stderr="")) as run:
            reply = SP.ask("session:opus", "B", [], SP.PATCH_SCHEMA)
        argv = run.call_args.args[0]
        self.assertEqual(json.loads(argv[argv.index("--json-schema") + 1]), SP.PATCH_SCHEMA)
        self.assertEqual(json.loads(reply)["why"], "x")
        self.assertNotIn("--json-schema", SP.session_command("opus", "B", [])[0])

    def test_api_asks_for_json_object_and_falls_back_on_400(self):
        from unittest import mock
        ok = {"choices": [{"message": {"content": "{}"}}]}
        err = SP.urllib.error.HTTPError("u", 400, "bad", {}, None)
        with mock.patch.object(SP, "post_chat", side_effect=[err, ok]) as post:
            self.assertEqual(SP.ask_api("m", "B", [], SP.SPEC_SCHEMA), "{}")
        self.assertEqual(post.call_args_list[0].args[0]["response_format"], {"type": "json_object"})
        self.assertNotIn("response_format", post.call_args_list[1].args[0])
        with mock.patch.object(SP, "post_chat", return_value=ok) as post:
            SP.ask_api("m", "B", [])
        self.assertNotIn("response_format", post.call_args.args[0])

    def test_rejected_reply_is_resent_once_with_the_error(self):
        from unittest import mock
        def check(txt):
            if txt == "bad":
                raise ValueError("patch edits frozen parts [1]")
        SP.STATS.clear()
        with mock.patch.object(SP, "ask_api", side_effect=["bad", "good"]) as api:
            self.assertEqual(SP.ask("m", "BRIEF", [], SP.PATCH_SCHEMA, check), "good")
        self.assertIn("frozen parts [1]", api.call_args.args[1])
        self.assertEqual((SP.STATS["asked"], SP.STATS["resent"], SP.STATS["frozen"]), (1, 1, 1))
        with mock.patch.object(SP, "ask_api", side_effect=["bad", "bad", "x"]) as api:
            SP.ask("m", "BRIEF", [], SP.PATCH_SCHEMA)
            self.assertEqual(api.call_count, 1)   # no check, no resend

    def test_schemas_describe_a_real_reply(self):
        part = PARTS[0]
        self.assertEqual(SP.SPEC_SCHEMA["properties"]["parts"]["items"], SP.PART_SCHEMA)
        self.assertEqual((SP.PART_SCHEMA["minItems"], SP.PART_SCHEMA["maxItems"]), (len(part), len(part)))
        json.dumps(SP.SPEC_SCHEMA)   # goes on the command line


class FrozenParts(unittest.TestCase):
    PARTS = PARTS + [["thigh.L", "prism", [0.2, 0.15, 0.9], [0.2, 0.45, 0], "iron", {}],
                     ["thigh.R", "prism", [0.2, 0.15, 0.9], [-0.2, 0.45, 0], "iron", {}]]
    LOW = SP.Editable({3, 4}, [(0.0, 0.3)], 3.0)    # the legs: below 0.9 m of 3.0

    def test_rule_editable_names_the_bones_of_the_failing_rules(self):
        bad = "  ground      FAIL  below y=0: ['thigh.L']\n  budget  PASS  ok\n"
        self.assertEqual(SP.rule_editable(self.PARTS, bad).indices, {3})
        sym = "  symmetry  FAIL  ['thigh: 1 parts left, 0 right']\n"
        self.assertEqual(SP.rule_editable(self.PARTS, sym).indices, {3, 4})
        for problem in (None, "  budget  FAIL  900 tris\n", bad + "  box_ceiling  FAIL  boxes\n",
                        "  ground  FAIL  below y=0: ['tail']\n"):
            with self.subTest(problem=problem):
                self.assertIsNone(SP.rule_editable(self.PARTS, problem))

    def test_patch_outside_the_editable_parts_is_rejected(self):
        leg = ["thigh.L", "prism", [0.2, 0.15, 0.8], [0.2, 0.4, 0], "iron", {}]
        head = ["head", "box", [0.3, 0.2, 0.2], [0, 2.4, 0], "brass", {}]
        parts, _ = SP.apply_patch(self.PARTS, reply({"set": {"3": leg}}), editable=self.LOW)
        self.assertEqual(len(parts), 5)
        for patch in ({"set": {"1": head}}, {"drop": [0]}, {"add": [head]}):
            with self.subTest(patch=patch), self.assertRaisesRegex(ValueError, "frozen|outside"):
                SP.apply_patch(self.PARTS, reply(patch), editable=self.LOW)
        low_add = ["thigh.R", "box", [0.1, 0.1, 0.1], [-0.2, 0.1, 0.1], "iron", {}]
        SP.apply_patch(self.PARTS, reply({"add": [low_add]}), editable=self.LOW)
        SP.apply_patch(self.PARTS, reply({"set": {"1": head}}), editable=SP.Editable({1}, None, 0.0))
        SP.apply_patch(self.PARTS, reply({"add": [head]}), editable=SP.Editable({1}, None, 0.0))

    def test_failing_bands_and_the_parts_that_touch_them(self):
        import tempfile
        import numpy as np
        from PIL import Image
        concept = np.zeros((512, 512), bool)
        concept[40:480, 200:300] = True
        model = concept.copy()
        model[300:480, 200:300] = False            # the model has no legs: the lowest bands fail
        model[300:480, 200:210] = True
        with tempfile.TemporaryDirectory() as tmp:
            for who, m in (("concept", concept), ("model", model)):
                rgba = np.zeros((512, 512, 4), np.uint8)
                rgba[m] = 255
                Image.fromarray(rgba).save(f"{tmp}/mask-{who}-front.png")
                Image.fromarray(rgba).save(f"{tmp}/mask-{who}-rts.png")
            bands = SP.failing_bands(pathlib.Path(tmp), "front")
            self.assertEqual(SP.failing_bands(pathlib.Path(tmp), "rts"), [])     # no height axis
            self.assertEqual(SP.failing_bands(pathlib.Path(tmp), "left"), [])    # no masks
        self.assertTrue(bands and max(hi for _, hi in bands) <= 0.5 and min(lo for lo, _ in bands) == 0.0)
        edit = SP.band_editable(self.PARTS, bands)
        self.assertEqual(edit.indices, {3, 4})                                   # the legs, not torso or head
        self.assertIsNone(SP.band_editable(self.PARTS, []))
        self.assertIsNone(SP.band_editable(self.PARTS, [(0.0, 1.0)]))            # all touch: nothing frozen

    def test_prompt_marks_the_frozen_parts(self):
        text = SP.numbered({"parts": self.PARTS}, self.LOW)
        self.assertEqual([("[FROZEN]" in ln) for ln in text.splitlines()], [True, True, True, False, False])
        self.assertIn("[3, 4]", SP.freeze_text(self.LOW))
        self.assertEqual(SP.freeze_text(None), "")
        self.assertNotIn("[FROZEN]", SP.numbered({"parts": self.PARTS}))


class BestOfN(unittest.TestCase):
    def fake_shape(self, margins):
        """stage_shape stub: writes clay.glb in args.out and reports the next margin."""
        it = iter(margins)

        def shape(spec_path, args, layout):
            ok, m = next(it)
            (args.out / "clay.glb").write_text(spec_path.parent.name)
            args.summary = {"approved": {"front": 0.75 + m}, "gates": {"front": 0.75}}
            return {"ok": ok, "glb": args.out / "clay.glb", "failed": [] if ok else ["silhouette"],
                    "t_pre": 1.0, "t_build": 2.0}
        return shape

    def run_best(self, margins):
        import tempfile
        import types
        from unittest import mock
        out = pathlib.Path(tempfile.mkdtemp())
        args = types.SimpleNamespace(out=out, times={"gen": 0.0, "build": 0.0})
        specs = [(k, {"parts": [], "k": k}) for k in range(1, len(margins) + 1)]
        with mock.patch.object(SP, "stage_shape", self.fake_shape(margins)):
            spec, shape = SP.best_of_n(specs, args, "unit")
        return out, args, spec, shape

    def test_margin_is_the_sum_over_the_gated_views(self):
        s = {"approved": {"front": 0.80, "left": 0.60, "extra": 0.9}, "gates": {"front": 0.75, "left": 0.65}}
        self.assertAlmostEqual(SP.margin_of(s), 0.0)
        self.assertEqual(SP.margin_of({}), 0)

    def test_largest_margin_wins_and_every_variant_stays(self):
        out, args, spec, shape = self.run_best([(True, 0.01), (True, 0.05), (True, 0.03)])
        self.assertEqual(spec["k"], 2)
        self.assertEqual(shape["glb"], out / "clay.glb")
        self.assertEqual((out / "clay.glb").read_text(), "2")        # the winner's files copied up
        for k in (1, 2, 3):
            self.assertTrue((out / "variants" / str(k) / "spec.json").exists())
        self.assertEqual(args.times, {"gen": 3.0, "build": 6.0})
        text = SP.variants_section(args)
        self.assertIn("| 2 (chosen) |", text)
        self.assertIn("+0.050", text)

    def test_a_passing_variant_beats_a_bigger_margin_that_fails(self):
        _, _, spec, _ = self.run_best([(False, 0.20), (True, 0.01)])
        self.assertEqual(spec["k"], 2)

    def test_sections_are_empty_for_one_variant_and_old_args(self):
        import types
        self.assertEqual(SP.variants_section(types.SimpleNamespace()), "")
        self.assertEqual(SP.timing_section(types.SimpleNamespace()), "")
        text = SP.timing_section(types.SimpleNamespace(times={"gen": 12.34, "build": 80, "n_passes": 2}))
        for line in ("- t_gen: 12.3 s", "- t_build: 80.0 s", "- t_colour: 0.0 s", "- passes: 2"):
            self.assertIn(line, text)


class FewShot(unittest.TestCase):
    def args(self, rig, off=False):
        import types
        return types.SimpleNamespace(rig=rig, no_fewshot=off)

    def test_example_per_family_and_switches(self):
        for rig in ("biped", "spider"):
            with self.subTest(rig=rig):
                a = self.args(rig)
                brief, imgs = SP.with_fewshot("BRIEF", a, 3)
                self.assertEqual(len(imgs), 1)
                self.assertTrue(imgs[0].exists())
                self.assertIn("Image 3 ", brief)
                self.assertIn("what a PASS looks like", brief)
                self.assertEqual(brief.split(SP.FEWSHOT_MARK)[0], "BRIEF")   # passes strip it
                self.assertIn("## Few-shot", SP.fewshot_section(a))
        for a in (self.args("biped", off=True), self.args("building")):
            self.assertEqual(SP.with_fewshot("BRIEF", a, 2), ("BRIEF", []))
            self.assertEqual(SP.fewshot_section(a), "")

    def test_summary_drops_opts_and_rounds(self):
        spec = {"parts": [["head", "box", [0.123456, 0.2, 0.2], [0, 2.4, 0], "iron", {"sides": 8}]]}
        self.assertEqual(SP.fewshot_summary(spec), '["head","box",[0.12,0.2,0.2],[0,2.4,0],"iron",{}]')
        limb = {"parts": [["arm.L", "prism", [0.2, 0.2, 0.4], [0, 0, 0], "iron",
                           {"from": [0.5, 2.0, 0], "to": [0.6, 1.5, 0.004]}]]}
        self.assertEqual(SP.fewshot_summary(limb),
                         '["arm.L","prism",[0.2,0.2,0.4],[0,0,0],"iron",{"from":[0.5,2.0,0],"to":[0.6,1.5,0.0]}]')


class RedDecides(unittest.TestCase):
    """The overlay's red (uncovered share) lowers a variant's margin, blocks a fit that grows it
    and keeps a PASS at prototype-safe when a critical view is over its cap."""

    def test_margin_pays_the_red(self):
        s = {"approved": {"front": 0.85, "left": 0.75}, "gates": {"front": 0.75, "left": 0.65},
             "uncovered": {"front": 0.10, "left": 0.20}}
        self.assertAlmostEqual(SP.margin_of(s), 0.20 - SP.RED_W * 0.15)

    def test_fit_refused_when_red_grows(self):
        gates = {"front": 0.75}
        prev, cur = {"front": 0.80, "red": 0.10}, {"front": 0.85, "red": 0.10 + SP.RED_SLIP + 0.01}
        self.assertFalse(SP.fit_accepted(prev, cur, gates, (None, None)))
        self.assertTrue(SP.fit_accepted(prev, {**cur, "red": 0.11}, gates, (None, None)))

    def test_status_capped_by_red(self):
        from silhouette import UNCOVERED_MAX
        s = {"uncovered": {"front": UNCOVERED_MAX["front"] + 0.01}}
        self.assertEqual(SP.status_of("PASS", s, False), "prototype-safe")
        self.assertEqual(SP.status_of("PASS", {"uncovered": {"front": 0.05}}, False), "final-use")


class Identity(unittest.TestCase):
    def test_low_identity_keeps_a_pass_prototype_safe(self):
        self.assertEqual(SP.status_of("PASS", {"identity": {"ok": 5, "total": 6, "missing": ["lantern"]}}, False),
                         "prototype-safe")
        self.assertEqual(SP.status_of("PASS", {"identity": {"ok": 6, "total": 6, "missing": []}}, False), "final-use")
        self.assertEqual(SP.status_of("PASS", {}, False), "final-use")      # no checklist, no demotion

    def test_review_line_and_brief_list(self):
        self.assertEqual(SP.identity_line({"identity": {"ok": 5, "total": 6, "missing": ["lantern"]}}),
                         "Identity: 5/6 - missing: lantern\n\n")
        self.assertEqual(SP.identity_line({}), "")
        text = SP.identity_text([{"name": "eyes", "kind": "eyes"},
                                 {"name": "blue detail #586B87", "kind": "zone", "views": ["front"]}])
        self.assertIn("must exist as parts or decals", text)
        self.assertIn("2. blue detail #586B87 - a material of exactly this colour", text)
        self.assertEqual(SP.identity_text([]), "")
