#!/usr/bin/env python3
"""Stage 2 of the pipeline: colour on a frozen shape (PIPELINE §18.F).

    stage_colour(spec, glb_clay, args, tilts, work) -> (ok, report_markdown)

The spec that passed stage 1 gets its texture (`--texture cel|painted|sheet`), then the
colour zones are measured on all five views, top and bottom from the cameras stage 1 chose
(`tilts`, {view: tilt} as silhouette.report_tilts). An optional colour pass may move only the
palette (colour, surface) and the decals (kind, colour); a reply that touches a part is
rejected, so the shape cannot drift under the colour.

    cel      flat tone per face by orientation (surfaces.paint_cel)
    painted  the older procedural pattern and gloss
    sheet    the construction sheet's own panels projected onto the clay GLB (project_concept.py)

`args` needs: id, tag, kind, sheet (the judge), build (the sheet the model was built from),
texture, out; and, for the colour pass only, model and colour_pass (how many tries).
The final GLB is <out>/model.glb, its review renders <out>/views/<tag>/model-<view>.png.
"""
import copy
import json
import pathlib
import re
import shutil
import subprocess
import sys

import cut_hull
import align_features
import deform_to_sheet
import look
import optimize_verts
import outline
import overrides
import shared_atlas as SA
import silhouette as SIL
from preflight import BUDGETS, is_prop, load_props, misplaced_decals
from surfaces import DECALS, SURFACES
from views import layout_of

HERE = pathlib.Path(__file__).resolve().parent
TEXTURES = ("cel", "painted", "sheet")
COLOUR_OPTS = ("decal", "decal_color")     # the only part fields a colour pass may set
HEX = re.compile(r"#[0-9A-Fa-f]{6}")
FIT_LUMA = False    # stage 2 cel: per-slot tone multipliers and a light direction fitted to the sheet (--fit-luma, PIPELINE 26.L8-8)


def run(script, *argv, blender=False):
    cmd = (["blender", "-b", "-P", str(HERE / script), "--"] if blender
           else [sys.executable, str(HERE / script)])
    return subprocess.run(cmd + [str(a) for a in argv] + (overrides.build_args() if script == "build_unit.py" else []),
                          capture_output=True, text=True)


def tilts_text(tilts):
    """{'top': 10, 'rts': (35, 30)} -> 'top:10,rts:35/30' (views.parse_tilts reads it back)."""
    return ",".join(f"{v}:{'/'.join(map(str, t)) if isinstance(t, (list, tuple)) else t}"
                    for v, t in tilts.items())


# ---------------------------------------------------------------- colour pass: what may change
def strip_colour(part):
    """A part without the fields a colour pass owns."""
    opts = part[5]
    if isinstance(opts, dict):
        opts = {k: v for k, v in opts.items() if k not in COLOUR_OPTS}
    return [*part[:5], opts]


def validate_colour(old, new):
    """`new` or ValueError: the spec after a colour pass differs from `old` only in the
    palette's colour and surface and in the parts' decal and decal_color."""
    if set(new) != set(old):
        raise ValueError(f"colour pass changed the spec's fields: {sorted(set(new) ^ set(old))}")
    for key in set(old) - {"palette", "parts"}:
        if new[key] != old[key]:
            raise ValueError(f"colour pass changed {key}")
    if [strip_colour(p) for p in new["parts"]] != [strip_colour(p) for p in old["parts"]]:
        raise ValueError("colour pass changed a part (only decal and decal_color may move)")
    check_palette(old.get("palette", {}), new.get("palette", {}))
    for i, p in enumerate(new["parts"]):
        opts = p[5] if isinstance(p[5], dict) else {}
        if opts.get("decal") and opts["decal"] not in DECALS:
            raise ValueError(f"part {i}: decal outside {sorted(DECALS)}")
        if opts.get("decal_color") and not HEX.fullmatch(str(opts["decal_color"])):
            raise ValueError(f"part {i}: decal_color is not #RRGGBB")
    if misplaced_decals(new["parts"]):
        raise ValueError("decal on a non-head bone")
    return new


def valid_ramp(ramp):
    """None (no ramp) or [p10, p90] luma, 0 <= p10 <= p90 <= 1."""
    return ramp is None or (isinstance(ramp, (list, tuple)) and len(ramp) == 2
                            and all(isinstance(v, (int, float)) for v in ramp) and 0 <= ramp[0] <= ramp[1] <= 1)


def valid_tones(tones):
    """None (the surface's own tones) or [up, side, down] multipliers, each in (0, 3]."""
    return tones is None or (isinstance(tones, (list, tuple)) and len(tones) == 3
                             and all(isinstance(v, (int, float)) and 0 < v <= 3 for v in tones))


def check_palette(old, new):
    """Same slots, same alpha; each slot's colour is #RRGGBB, its surface a known one, its ramp valid."""
    if set(new) != set(old):
        raise ValueError(f"colour pass changed the palette slots: {sorted(set(new) ^ set(old))}")
    for name, entry in new.items():
        if (not HEX.fullmatch(str(entry.get("color", ""))) or entry.get("surface") not in SURFACES
                or entry.get("alpha", 1.0) != old[name].get("alpha", 1.0) or not valid_ramp(entry.get("ramp"))
                or not valid_tones(entry.get("tones"))):
            raise ValueError(f"palette slot {name} outside the schema: {entry}")


def apply_colour(spec, patch):
    """The spec with a reply's {"palette": {slot: {...}}, "decals": {part: {...} | null}}
    applied, validated by validate_colour. Any other key of the reply is rejected."""
    if set(patch) - {"palette", "decals", "why"}:
        raise ValueError(f"colour reply has fields beyond palette/decals: {sorted(patch)}")
    new = copy.deepcopy(spec)
    for name, entry in (patch.get("palette") or {}).items():
        new.setdefault("palette", {}).setdefault(name, {}).update(entry)
    for idx, decal in (patch.get("decals") or {}).items():
        part = new["parts"][int(idx)]
        opts = dict(part[5]) if isinstance(part[5], dict) else {}
        for key in COLOUR_OPTS:
            opts.pop(key, None)
        part[5] = {**opts, **(decal or {})}
    return validate_colour(spec, new)


PROMPT = """You are the colour artist of a low-poly WC3-style unit. The shape is frozen: you may only
change the palette (each slot's "color" and "surface") and the decals (a part's "decal" kind and
"decal_color"). Never move, add, drop or re-material a part.
Image 1 is the approved concept's front, image 2 the model's front render, image 3 the concept's
top, image 4 the model's top (the model is built from the same palette, unlit).

Palette now: {palette}
{hint}Parts with a decal: {decals}
Colour-zone scores per view (IoU of each sheet colour zone; 1.0 = the model paints that zone where
the sheet does): {scores}

Reply with ONE JSON object and nothing else:
{{"palette": {{"<slot>": {{"color": "#RRGGBB", "surface": "<surface>"}}}}, "decals": {{"<part index>": {{"decal": "<kind>", "decal_color": "#RRGGBB"}} or null}}, "why": "<one line>"}}
Only list the slots and parts you change. Surfaces: {surfaces}. Decal kinds: {kinds}.
Fix the colours the sheet shows and the model does not (hue first, the unit's own lighting is not yours to fix)."""


def colour_brief(spec, scores, race=None):
    """The colour reply's brief; `race` adds the race palette as a soft hint (shared_atlas.hint_text, PIPELINE 27.T7)."""
    decals = {i: {k: p[5][k] for k in COLOUR_OPTS if k in p[5]}
              for i, p in enumerate(spec["parts"]) if isinstance(p[5], dict) and p[5].get("decal")}
    return PROMPT.format(palette=json.dumps(spec.get("palette", {})), decals=json.dumps(decals),
                         scores=json.dumps(scores), hint=SA.hint_text(race) if race else "", surfaces=", ".join(SURFACES),
                         kinds=", ".join(sorted(DECALS)))


def parse_reply(txt):
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        raise ValueError("no JSON in the reply")
    return json.loads(m.group(0))


# ---------------------------------------------------------------- build and measure
def with_ramps(spec, sheet):
    """A copy of `spec` whose palette slots carry "ramp": [p10, p90] of the luma of the sheet
    zone nearest their colour (silhouette.zone_palette): the cel cells then ramp as far as the artist's did."""
    import numpy as np
    out = copy.deepcopy(spec)
    names, _, ramps = SIL.zone_palette(sheet)
    zone_rgb = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in names], float)
    for entry in out.get("palette", {}).values():
        rgb = np.array([int(entry["color"][i:i + 2], 16) for i in (1, 3, 5)], float)
        entry["ramp"] = list(ramps[int(np.argmin(((zone_rgb - rgb) ** 2).sum(axis=1)))])
    return out


def fit_luma(spec, args, tilts, work):
    """(spec, report): `spec` with palette[slot]["tones"] = the cel multipliers fit_luma.fit measured on the
    sheet (PIPELINE 26.L8-8). The ID + normal shots come from the spec rebuilt as flat palette colours, like
    spec_pipeline.zones_clay. The spec comes back as it was, report None, when nothing was fitted."""
    import fit_luma as FL
    work = pathlib.Path(work) / "luma"
    work.mkdir(parents=True, exist_ok=True)
    glb, path, hi = work / "ids.glb", work / "spec.json", BUDGETS[args.kind][1]
    path.write_text(json.dumps(spec, indent=2))
    run("build_unit.py", path, glb, hi, "nofuse", hi, *cut_hull.args(spec, args.sheet, args.kind, work), blender=True)
    if glb.exists():
        run("render_silhouette.py", glb, work, "ids", blender=True)
    if not glb.exists():
        return spec, None
    report = FL.fit(work, glb.stem, args.sheet, layout_of(args.kind), spec.get("palette", {}),
                    {v: t for v, t in tilts.items() if isinstance(t, int)})
    if report is None:
        return spec, None
    out = copy.deepcopy(spec)
    for slot, tones in report["tones"].items():
        out["palette"][slot]["tones"] = tones
    return out, report


def zone_contrast(spec, floor=8.0, dark=0.8):
    """A copy of `spec` where, of two palette slots closer than `floor` (Oklab distance x100), the darker is scaled x`dark` in
    luma (--zone-contrast on, PIPELINE 33.L15-3): neighbouring zones the cel would paint as one."""
    import numpy as np
    out = copy.deepcopy(spec)
    pal = out.get("palette", {})
    rgb = {k: np.array([int(e["color"][i:i + 2], 16) for i in (1, 3, 5)], float) / 255 for k, e in pal.items()}
    lab = {k: SIL.oklab(v[None])[0] for k, v in rgb.items()}
    for a, b in ((a, b) for a in rgb for b in rgb if a < b):
        if 100 * np.linalg.norm(lab[a] - lab[b]) < floor:
            k = a if lab[a][0] < lab[b][0] else b
            rgb[k] = rgb[k] * dark
            lab[k] = SIL.oklab(rgb[k][None])[0]
            pal[k]["color"] = "#%02X%02X%02X" % tuple(int(round(c * 255)) for c in rgb[k])
    return out


def face_quad(spec, args, work):
    """The 128 px head cut for --face decal (a part wears the "sheet" decal), else None."""
    if getattr(args, "face", "off") != "decal" or not any(isinstance(p[5], dict) and p[5].get("decal") == "sheet" for p in spec["parts"]):
        return None
    from split_sheet import head_face
    return head_face(pathlib.Path(args.sheet), work / "face128.png", cell=128)


def build_textured(spec, glb_clay, args, glb, work):
    """The spec in `args.texture`, written to `glb`. True when the file came out."""
    glb.unlink(missing_ok=True)
    if args.texture == "sheet":      # project the sheet onto the clay shape; the spec is not rebuilt
        run("project_concept.py", glb_clay, args.build, glb, blender=True)
        return glb.exists()
    path = work / "spec-colour.json"
    if getattr(args, "zone_contrast", "off") == "on":
        spec = zone_contrast(spec)
    quad = face_quad(spec, args, work)
    if quad:       # the quad wears the face: the lathe's striped decal goes
        spec = {**spec, "parts": [[*p[:5], {k: v for k, v in p[5].items() if k != "decal"}] if isinstance(p[5], dict) and p[5].get("decal") == "sheet" else p
                                  for p in spec["parts"]]}
    if getattr(args, "ramp", False) and args.texture == "cel":
        spec = with_ramps(spec, args.sheet)
    path.write_text(json.dumps(spec, indent=2))
    hi = BUDGETS[args.kind][1]
    run("build_unit.py", path, glb, hi, "nofuse", hi, "tex", f"style={args.texture}",
        *face_args(spec, args, work), *prop_args(spec, args, work), *cut_hull.args(spec, args.sheet, args.kind, work),
        *shared_args(args), *atlas_args(args), *materials_args(args), *body_args(args), *(["cull=remove"] if getattr(args, "cull", False) else []), blender=True)
    if glb.exists():
        deform_to_sheet.apply(glb, args)     # the clay was deformed; the rebuilt textured body gets the same pull
        align_features.apply(glb, args)
        optimize_verts.apply(glb, args)
        look.apply(glb, args)
        if quad:
            outline.apply(glb, False, quad)
    return glb.exists()


def body_args(args):
    """["body=sdf"] for `--body sdf` (build_unit.BODY, PIPELINE 28.L10-7); nothing when args has no body."""
    core = getattr(args, "sdf_core", None)
    return [*([f"body={args.body}"] if getattr(args, "body", None) else []), *([f"sdf_core={core}"] if core in ("on", "off") else [])]


def shared_args(args):
    """["shared=<race table>"] for `--atlas shared` on a cel build: the race's 128 px atlas
    (shared_atlas.py, PIPELINE 27.T3) instead of the unit's own."""
    if getattr(args, "atlas", "own") != "shared" or args.texture != "cel":
        return []
    return [f"shared={pathlib.Path(args.atlas_dir) / (args.race.lower() + '.json')}"]


def materials_args(args):
    """["materials=split"] for `--materials split` (build_unit.MERGE_MATERIALS, PIPELINE 27.T5)."""
    return ["materials=split"] if getattr(args, "materials", "merge") == "split" else []


def atlas_args(args):
    """["cel_atlas=compact|legacy"] when `--atlas` names the unit's own atlas layout (PIPELINE 27.T1);
    nothing for `own` (build_unit.COMPACT_ATLAS decides) and `shared`."""
    choice = getattr(args, "atlas", "own")
    return [f"cel_atlas={choice}"] if choice in ("compact", "legacy") and args.texture == "cel" else []


def face_args(spec, args, work):
    """["face=<png>"]: the approved sheet's head, cut out, when a part asks for the "sheet" decal."""
    if not any(isinstance(p[5], dict) and p[5].get("decal") == "sheet" for p in spec["parts"]):
        return []
    from split_sheet import head_face
    return [f"face={head_face(pathlib.Path(args.sheet), work / 'face.png')}"]


def prop_args(spec, args, work):
    """["propcrops=<json>"]: {part index: crop of the props sheet} for the prop parts (opts "prop") that
    match a drawing of the unit's props sheet; the build projects each crop on its part (PIPELINE 23.L5-3).
    Nothing when the unit has no props sheet, its drawings do not match props.json one to one, or no part is marked."""
    props, sheet = load_props(args.id), getattr(args, "props", None)
    if not (props and sheet and pathlib.Path(sheet).exists() and any(is_prop(p) for p in spec["parts"])):
        return []
    from prop_measure import crop_props, crops_by_part
    crops = crop_props(sheet, work, "propcrop")
    found = crops_by_part(spec["parts"], props, crops) if len(crops) == len(props) else {}
    if not found:
        return []
    (work / "propcrops.json").write_text(json.dumps(found))
    return [f"propcrops={work / 'propcrops.json'}"]


def measure(glb, args, tilts, work):
    """silhouette.json of the textured model against the approved sheet, from stage 1's cameras."""
    out = work / "sil"
    run("silhouette.py", args.sheet, glb, out, "--layout", layout_of(args.kind),
        "--rig", args.rig, "--tilts", tilts_text(tilts))
    try:
        return json.loads((out / "silhouette.json").read_text())
    except (OSError, ValueError):
        return {}


def zones_of(report):
    return {v: r["zones"] for v, r in report.items() if "zones" in r}


def gate(zones):
    """(ok, views that fail): every ZONE_GATED view measured must hold; none measured fails."""
    gated = {v: z for v, z in zones.items() if v in SIL.ZONE_GATED}
    bad = sorted(v for v, z in gated.items() if z["fails"])
    return bool(gated) and not bad, bad


def score(zones):
    return sum(z["mean"] for z in zones.values()) / max(len(zones), 1)


def render_views(glb, args, tilts, view_dir):
    run("render_unit.py", glb, view_dir, f"tilt={tilts_text(tilts)}", blender=True)


# ---------------------------------------------------------------- the stage
def attempt(spec, glb_clay, args, tilts, work, name):
    """Build, measure and render one candidate: (glb, zones) with zones None when no GLB."""
    work = work / name
    work.mkdir(parents=True, exist_ok=True)
    glb = work / "model.glb"
    if not build_textured(spec, glb_clay, args, glb, work):
        return glb, None, work
    zones = zones_of(measure(glb, args, tilts, work))
    if getattr(args, "outline", "off") == "hull":     # after the measure: the zone shots (workbench) draw both sides of the hull, black over the body
        outline.apply(glb)
    render_views(glb, args, tilts, work / "views")
    return glb, zones, work


def colour_pass(spec, zones, best_work, glb_clay, args, tilts, work, k, ask):
    """One colour try on the current best: (spec, zones, glb, dir, log line). A reply that
    breaks the contract, or that does not raise the zone mean without failing a view that
    held, leaves the best untouched."""
    from split_sheet import split
    panels = split(args.sheet, work / "panels", args.id, layout_of(args.kind))
    views = best_work / "views"
    scores = {v: {"mean": z["mean"], "zones": {h: g["iou"] for h, g in z["zones"].items()}}
              for v, z in zones.items()}
    images = [panels["front"], views / "model-front.png", panels["top"], views / "model-top.png"]
    try:
        cand = apply_colour(spec, parse_reply(ask(args.model, colour_brief(spec, scores, args.race if getattr(args, "atlas", "own") == "shared" else None), images)))
    except (ValueError, KeyError, IndexError, TypeError, RuntimeError) as err:
        return spec, zones, None, best_work, f"try {k}: rejected reply: {err}"
    glb, new, new_work = attempt(cand, glb_clay, args, tilts, work, f"try{k}")
    held = new is not None and set(gate(new)[1]) <= set(gate(zones)[1]) and score(new) > score(zones)
    if not held:
        return spec, zones, None, best_work, f"try {k}: kept the old colour (zones {score(zones):.3f} -> {score(new or {}):.3f})"
    return cand, new, glb, new_work, f"try {k}: ACCEPT (zones {score(zones):.3f} -> {score(new):.3f})"


def table_rows(zones, tilts):
    views = [v for v in SIL.ZONE_VIEWS if v in zones]
    rows = [f"| cameras (from stage 1) | {tilts_text(tilts) or 'all square-on'} |"]
    rows.append("| colour zones mean / cover, " + "/".join(views) + " | "
                + " ; ".join(f"{zones[v]['mean']:.2f} / {zones[v]['cover']:.2f}" for v in views) + " |")
    rows.append("| luma L1 vs sheet (p10/p50/p90 per zone, before match_luma) | "
                + " ; ".join(f"{zones[v].get('luma_l1')}" for v in views) + " |")
    lost = {v: zones[v]["lost"] for v in views if zones[v]["lost"]}
    if lost:
        rows.append("| lost zones (WARN, not a gate) | " + "; ".join(f"{v}: {', '.join(z)}" for v, z in lost.items()) + " |")
    fails = {v: zones[v]["fails"] for v in views if zones[v]["fails"]}
    if fails:
        rows.append("| FAIL | " + "; ".join(f"{v}: {', '.join(f)}" for v, f in fails.items()) + " |")
    return rows


def stage_colour(spec, glb_clay, args, tilts, work, ask=None):
    """Texture the frozen `spec` and gate its colour zones. Returns (ok, markdown) where the
    markdown is the review.md section "Stage 2 — colour". The final GLB is <out>/model.glb."""
    work = pathlib.Path(work)
    luma = None
    if (FIT_LUMA or getattr(args, "fit_luma", False)) and args.texture == "cel":
        spec, luma = fit_luma(spec, args, tilts, work)
    glb, zones, best_work = attempt(spec, glb_clay, args, tilts, work, "texture")
    if zones is None:
        return False, f"## Stage 2 — colour\n\nBUILD FAILED: the `{args.texture}` texture produced no GLB.\n"
    log = []
    for k in range(1, getattr(args, "colour_pass", 0) + 1):
        if gate(zones)[0]:
            break
        if ask is None:
            from spec_pipeline import ask
        spec, zones, new_glb, best_work, line = colour_pass(spec, zones, best_work, glb_clay, args,
                                                            tilts, work, k, ask)
        glb = new_glb or glb
        log.append(line)
    ok, _ = gate(zones)
    shutil.copy(glb, pathlib.Path(args.out) / "model.glb")
    view_dir = pathlib.Path(args.out) / "views" / args.tag
    # next to stage 1's clay-<view>.png, which the review sheet shows in its own column
    shutil.copytree(best_work / "views", view_dir, dirs_exist_ok=True)
    (pathlib.Path(args.out) / "spec-colour.json").write_text(json.dumps(spec, indent=2))   # the spec with its accepted colour
    (work / "colour.json").write_text(json.dumps(
        {"texture": args.texture, "tilts": {v: list(t) if isinstance(t, tuple) else t for v, t in tilts.items()},
         "zones": zones, "colour_pass": log}, indent=2))
    md = ["## Stage 2 — colour", "", "| gate | value |", "|---|---|", f"| texture | {args.texture} |",
          *table_rows(zones, tilts)]
    if luma:
        md.append(f"| luma fit (light az/el {luma['light']}, b {luma['b']}, loss {luma['cost0']} -> {luma['cost']}) | "
                  + ("DEGENERATE, no light direction" if luma["degenerate"] else "applied") + " |")
    if log:
        md.append("| colour pass | " + "; ".join(log) + " |")
    md += ["", f"colour: **{'PASS' if ok else 'FAIL'}**", ""]
    return ok, "\n".join(md)
