"""python3 -m unittest discover -s tests/tools/blender

L12-4: no dead flag. Every argument of spec_pipeline's parser (and every CF_* variable of tools/blender) is in OPT_INS, and each
entry proves one of
  live   -> turning it on changes a number / a call of the module that consumes it (pure modules, no Blender),
  noop   -> with its precondition missing the pipeline prints "no-op: <flag>: <why>" (noop_notes, or the data check it names),
  plain  -> an input, label or path every run reads (the static check below: some tools/blender module reads args.<dest>).
A flag added to the parser and not to OPT_INS fails here; so does an entry whose flag is gone."""
import json
import pathlib
import re
import sys
import tempfile
import types
import unittest
from unittest import mock

TOOLS = pathlib.Path(__file__).resolve().parents[3] / "tools/blender"
sys.path.insert(0, str(TOOLS))

import colour_stage  # noqa: E402
import fit_spec  # noqa: E402
import look  # noqa: E402
import numpy as np  # noqa: E402
import parts_fit  # noqa: E402
import retopo  # noqa: E402
import sdf_body  # noqa: E402
import silhouette  # noqa: E402
import spec_pipeline as SP  # noqa: E402

REQUIRED = ["--id", "u", "--race", "Human", "--name", "N"]


def parse(*flags):
    return SP.build_parser().parse_args([*REQUIRED, *flags])


class Stop(Exception):
    pass


def fit_kwargs(*flags, with_constraints=False):
    """The keyword arguments fit_stage hands to fit_spec.fit for these flags (fit stubbed: it raises after recording)."""
    seen = {}

    def stub(*a, **kw):
        seen.update(kw)
        raise Stop

    with tempfile.TemporaryDirectory() as tmp:
        extra = []
        if with_constraints:
            c = pathlib.Path(tmp) / "diagnosis.json"
            c.write_text(json.dumps({"deltas": [{"op": "scale"}]}))
            extra = ["--constraints", str(c)]
        args = parse(*flags, *extra)
        args.sheet, args.build, args.out, args.kind = pathlib.Path(tmp) / "s.jpg", pathlib.Path(tmp) / "h.jpg", pathlib.Path(tmp), "mass"
        with mock.patch.object(fit_spec, "fit", stub), mock.patch.object(SP, "run_tilts", return_value=None), \
                mock.patch.object(silhouette, "run_report", return_value={}), mock.patch.object(SP, "ground_fix"), unittest.TestCase().assertRaises(Stop):
            SP.fit_stage({"parts": []}, args)
    return seen


def clay(body="sdf", **kw):
    with mock.patch.object(SP, "BODY", body), mock.patch.dict(vars(SP), {k.upper(): v for k, v in kw.items()}):
        return SP.clay_args("mass")


def live_fit_edges():
    return fit_kwargs()["hard"], fit_kwargs("--fit-edges")["hard"]


def live_fit_stages():
    return fit_kwargs()["stages"], fit_kwargs("--fit-stages")["stages"]


def live_fit_grad():
    return fit_kwargs()["grad"], fit_kwargs("--fit-grad")["grad"]


def live_fit_fast():
    return fit_kwargs()["wide"], fit_kwargs("--fit-fast")["wide"]


def live_fit_parts():
    return fit_kwargs()["partfit"], fit_kwargs("--fit-parts")["partfit"]


def live_depth():
    return fit_kwargs()["depth"], fit_kwargs("--depth")["depth"]


def live_parts():
    return fit_kwargs()["parts_path"], fit_kwargs("--parts", "p.json")["parts_path"]


def live_constraints():
    return fit_kwargs()["constraints"], fit_kwargs(with_constraints=True)["constraints"]


def live_deterministic():
    return "seconds" in fit_kwargs(), "seconds" in fit_kwargs("--deterministic")


def live_noise():      # --noise: the sigma table the guards read; without it None (the fixed 0.01)
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "noise.json"
        path.write_text(json.dumps({"global": {"front": 0.02}}))
        return SP.noise_kw(parse())["noise"], SP.noise_kw(parse("--noise", str(path)))["noise"]


def look_calls(*flags):
    """The look.py stages look.apply reaches for these flags (the stages stubbed; a hard sheet and a unioned body present)."""
    with tempfile.TemporaryDirectory() as tmp:
        glb = pathlib.Path(tmp) / "clay.glb"
        glb.write_bytes(b"glb")
        args = parse(*flags)
        args.hard, args.union_body = glb, True
        calls = []
        stub = {"look_report": {}, "run": {}, "bake_ink": {}}
        with mock.patch.multiple(look, **{k: mock.Mock(side_effect=lambda *a, _k=k, **kw: calls.append((_k, a[-1] if _k == "run" else None)) or v)
                                          for k, v in stub.items()}):
            look.apply(glb, args)
    return tuple(calls)


def live_look_snap():       # --look-snap on reaches look.run (the snap); off only measures
    return look_calls(), look_calls("--look-snap", "on")


def live_look_creases():    # --look-creases on hands the snap the sheet's lines as borders
    return look_calls("--look-snap", "on"), look_calls("--look-snap", "on", "--look-creases", "on")


def live_look_ink():        # --look-ink on bakes the ink into the atlas
    return look_calls(), look_calls("--look-ink", "on")


def live_loop():       # --loop 2 with an approved round 0 reaches loop_stage.run; 0 does not
    calls = []
    for n in ("0", "2"):
        args = parse("--loop", n)
        args.out, args.times = pathlib.Path(tempfile.mkdtemp()), {}
        shape = {"glb": args.out / "clay.glb"}
        args.summary = {"approved": {"front": .9}}
        with mock.patch.object(SP, "loop_hooks", side_effect=Stop):
            try:
                SP.run_loop(args, {}, shape, "unit")
                calls.append(False)
            except Stop:
                calls.append(True)
    return tuple(calls)


def live_author_guard():     # off never measures; revert measures the massing and the author
    measured = []
    for mode in ("off", "revert"):
        args = parse("--author-guard", mode)
        args.out, args.pre_spec = pathlib.Path(tempfile.mkdtemp()), {"parts": []}
        with mock.patch.object(SP, "guard_measure", side_effect=lambda *a: measured.append(mode)):
            SP.guard_stage({"parts": []}, args, "unit")
    return "off" in measured, "revert" in measured


def live_incoherent_weight():     # main() sets views.INCOHERENT_WEIGHT from the flag; the fit's proxy weighs the incoherent view by it
    out = []
    for flags in ((), ("--incoherent-weight", "0")):
        with mock.patch.object(SP.view_defs, "INCOHERENT_WEIGHT", parse(*flags).incoherent_weight):
            out.append(fit_spec.Proxy({}, ("top",), rig="spider", sheet_rep={"incoherent": ["top"]}).weight["top"])
    return tuple(out)


def live_dsl_repair():        # a spider with one straight leg piece: on splits it in two (dsl_rules.repair), off hands the spec back as it was
    spec = {"rig": "spider", "parts": [["body", "frustum", [.4, .2, .5], [0, .4, 0], "m", {"top": [1, 1], "shift": [0, 0]}],
                                       ["leg1.upper", "prism", [.04, .03, .5], [0, 0, 0], "m", {"sides": 6, "from": [.1, .4, 0], "to": [.5, 0, 0]}]]}
    out = []
    for flags in (("--dsl-repair", "off"), ()):
        args = parse(*flags)
        args.sheet = None
        out.append(len(SP.dsl_stage(spec, args)[0]["parts"]))
    return tuple(out)


def live_depth_source():      # tri moves a spec part whose z is outside the box3d triangulated for it (the proxy stubbed to lose nothing); none hands it back
    import parts_fit
    import preflight
    spec = {"rig": "biped", "parts": [["spine", "box", [0.4, 0.4, 0.2], [0, 1, 0.18], "m", {}]]}      # 0.08 m past the front of its box3d: associated (< .1 H), off by more than .05 H
    doc = {"H": 1.2, "parts": [{"name": "t", "bone": "spine", "box3d": [[-.2, .8, -.1], [.2, 1.2, .1]]}]}
    out = []
    for flags in (("--depth-source", "none"), ("--depth-source", "tri")):
        args = parse(*flags)
        args.sheet, args.kind = "s.jpg", "mass"
        with mock.patch.object(parts_fit, "load", return_value=doc), mock.patch.object(preflight, "targets_from", return_value={}), \
                mock.patch.object(SP, "load_props", return_value=[]), mock.patch.object(fit_spec, "broken_rules", return_value=set()), \
                mock.patch.object(SP, "proxy_ious", return_value=types.SimpleNamespace(ious=lambda parts: {"front": 0.9})):
            out.append(SP.depth_stage(spec, args, "shape")[0]["parts"][0][3][2])
    return tuple(out)


def live_sdf_k_mode():       # the flag reaches build_unit, and the mode changes the junction width
    a = {"r": .1, "bone": "arm.L"}
    return (clay() == clay(sdf_k_mode="hard"), sdf_body.pair_k(a, a, .01, 2, 1) == sdf_body.pair_k(a, a, .01, 2, 1, "hard"))


def live_sdf_retopo():
    called = []
    for method in ("qem", "cvt"):
        with mock.patch.object(retopo, "cvt", side_effect=lambda *a, **k: called.append("cvt") or Stop), \
                mock.patch.object(retopo, "reduce", side_effect=lambda *a, **k: called.append("qem") or Stop):
            retopo.retopo(None, None, 10, method=method)
    return clay() == clay(sdf_retopo="cvt"), called


def live_sdf_grid():
    return clay(), clay(sdf_grid=64)


def live_body():
    return clay("sdf"), clay("union")


def live_fit_luma():         # stage_colour fits the luma only with --fit-luma (cel); the stub ends it right after
    called = []
    for flag in ([], ["--fit-luma"]):
        args = parse(*flag)
        args.out = pathlib.Path(tempfile.mkdtemp())
        with mock.patch.object(colour_stage, "fit_luma", side_effect=lambda *a: called.append(bool(flag)) or ({}, None)), \
                mock.patch.object(colour_stage, "attempt", return_value=(None, None, None)):
            colour_stage.stage_colour({}, "clay.glb", args, {}, args.out)
    return called


def live_spill_w():         # CF_SPILL_W is SILHOUETTE.SPILL_W: the cost of a model with spill only changes with it
    c, m = np.zeros((8, 8), bool), np.zeros((8, 8), bool)
    c[:4], m[:5] = True, True
    return silhouette.asym_cost(c, m, 1, 1), silhouette.asym_cost(c, m, 3, 1)


def live_colour_on_fail():
    shape = {"glb": "clay.glb", "ok": False}
    return SP.wants_colour(parse("--colour-on-fail", "off"), shape), SP.wants_colour(parse(), shape)


def live_shape_only():
    shape = {"glb": "clay.glb", "ok": True}
    return SP.wants_colour(parse(), shape), SP.wants_colour(parse("--shape-only"), shape)


def noop_for(*flags):
    return SP.noop_notes(parse(*flags))


def lines_say(*flags, flag):
    return any(flag in n for n in noop_for(*flags))


# dest -> ("live", check, ...) | ("noop", argv, text) | ("plain",)
# live checks return (off, on): they must differ. Checks that return a tuple of booleans/lists assert on their own below.
LIVE_PAIRS = {
    "fit_edges": live_fit_edges, "fit_stages": live_fit_stages, "fit_grad": live_fit_grad, "fit_fast": live_fit_fast,
    "fit_parts": live_fit_parts, "depth": live_depth, "parts": live_parts, "constraints": live_constraints,
    "deterministic": live_deterministic, "noise": live_noise, "sdf_grid": live_sdf_grid, "body": live_body, "colour_on_fail": live_colour_on_fail,
    "shape_only": live_shape_only, "incoherent_weight": live_incoherent_weight, "dsl_repair": live_dsl_repair,
    "look_snap": live_look_snap, "look_creases": live_look_creases, "look_ink": live_look_ink, "depth_source": live_depth_source,
}
LIVE_CUSTOM = {         # dest -> (check, expected)
    "loop": (live_loop, (False, True)),
    "author_guard": (live_author_guard, (False, True)),
    "sdf_k_mode": (live_sdf_k_mode, (False, False)),          # clay_args differ, pair_k differs: "equal" is False for both
    "sdf_retopo": (live_sdf_retopo, (False, ["qem", "cvt"])),
    "fit_luma": (live_fit_luma, [True]),
}
NOOP = {         # dest -> (argv that switch it on without its precondition, text noop_notes says)
    "ramp": (["--texture", "painted", "--ramp"], "--ramp"),
    "atlas": (["--texture", "sheet", "--atlas", "shared"], "--atlas"),
    "materials": (["--texture", "sheet", "--materials", "split"], "--materials"),
    "colour_pass": (["--shape-only", "--colour-pass", "2"], "--colour-pass"),
    "align": (["--body", "join", "--align"], "--align"),
}
PLAIN = {      # read by every run (or by the mode they name): the static check proves some module reads args.<dest>
    "id", "race", "name", "role", "run", "sheet", "hard", "hard_clean", "props", "image1", "with_sheet", "model", "tag", "rig",
    "fixed_rig", "height", "kind", "texture", "atlas_dir", "no_silhouette", "no_rts", "spec", "hull", "cull", "fit", "no_fewshot",
    "no_massing", "variants", "decimate", "budgets", "tilts", "deform", "fit_verts", "flip_side", "frame", "no_repair", "passes",
    "diagnose", "pair", "out",
}
ENV = {"CF_SPILL_W", "CF_VERTS_SECONDS", "CF_FLIP_SIDE", "CF_FRAME", "CF_OVERRIDES", "CF_BUILD_ARGS"}       # each is read in the source (checked below) and documented here


class FlagTable(unittest.TestCase):
    def dests(self):
        return {a.dest for a in SP.build_parser()._actions if a.dest != "help"}

    def test_every_flag_is_in_the_table_and_the_table_has_no_stale_row(self):
        table = {*LIVE_PAIRS, *LIVE_CUSTOM, *NOOP, *PLAIN}
        self.assertEqual(self.dests() - table, set(), "a flag with no liveness row: add it to OPT_INS (live, noop or plain)")
        self.assertEqual(table - self.dests(), set(), "a row for a flag the parser no longer has")

    def test_every_dest_is_read_by_some_module(self):
        sources = {f.name: f.read_text() for f in TOOLS.glob("*.py")}
        dead = []
        for d in sorted(self.dests()):
            pat = re.compile(rf"args\.{d}\b|getattr\(args, \"{d}\"|\ba\.{d}\b")
            if not any(pat.search(t) for t in sources.values()):
                dead.append(d)
        self.assertEqual(dead, [], "no module reads these arguments: dead flags")

    def test_every_cf_variable_is_known_and_read(self):
        seen = {m for f in TOOLS.glob("*.py") for m in re.findall(r"CF_[A-Z_]+", f.read_text())}
        self.assertEqual(seen - ENV, set(), "a CF_* variable with no row in ENV")
        self.assertEqual(ENV - seen, set())


class Live(unittest.TestCase):
    def test_flags_that_change_a_call_or_a_number(self):
        for dest, check in LIVE_PAIRS.items():
            with self.subTest(dest):
                off, on = check()
                self.assertNotEqual(off, on, f"--{dest}: turning it on changes nothing it hands over")

    def test_flags_checked_by_their_consumer(self):
        for dest, (check, expected) in LIVE_CUSTOM.items():
            with self.subTest(dest):
                self.assertEqual(check(), expected)

    def test_spill_weight_changes_the_cost(self):         # CF_SPILL_W
        plain, weighted = live_spill_w()
        self.assertNotEqual(plain, weighted)
        self.assertIn("CF_SPILL_W", (TOOLS / "silhouette.py").read_text())

    def test_noop_flags_say_so(self):
        for dest, (argv, text) in NOOP.items():
            with self.subTest(dest):
                self.assertTrue(lines_say(*argv, flag=text), f"{argv}: no 'no-op: {text}' line")
                self.assertTrue(all(n.startswith("no-op: ") for n in noop_for(*argv)))

    def test_noop_is_silent_when_the_precondition_holds(self):
        self.assertEqual(noop_for("--texture", "cel", "--ramp", "--fit-luma", "--atlas", "compact"), [])
        self.assertEqual(noop_for(), [])


class PartsWithoutBox3d(unittest.TestCase):
    """--fit-parts / --depth read parts.json; 7 of the 8 refs/*/parts.json have parts with box3d null."""
    DOC = {"H": 2.0, "parts": [{"bone": "head", "box3d": None}, {"bone": "arm.L", "box3d": [[0, 1, 0], [.2, 1.2, .2]]}]}

    def test_a_part_without_box3d_associates_with_nothing(self):
        found = parts_fit.associate([["head", "box", [1, 1, 1], [0, 1, 0], "m", {}], ["arm.L", "box", [1, 1, 1], [0, 1, 0], "m", {}]],
                                    [(0, 2.0, 0), (.1, 1.1, .1)], self.DOC, 2.0)
        self.assertEqual(found, [None, 1])

    def test_all_null_says_no_op_and_gives_no_part_terms(self):
        doc = {"parts": [{"bone": "head", "box3d": None}]}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(parts_fit, "load", return_value=doc), \
                mock.patch("builtins.print") as out:
            got = fit_spec.attach_parts(types.SimpleNamespace(views=(), zones=None), {}, pathlib.Path(tmp) / "none.jpg", [], 1.0, True, True, None)
        self.assertIsNone(got)
        self.assertIn("no-op", out.call_args[0][0])
        self.assertIn("box3d", out.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
