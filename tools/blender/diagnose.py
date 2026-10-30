#!/usr/bin/env python3
"""LLM diagnosis of a finished run (ROADMAP Leva 4, L4-8). An OUTPUT only: nothing here is read back
by the author, repair, fit or variants.

    python3.14 tools/blender/diagnose.py <run dir> --id n00U [--kind mass] [--model session:opus]

The reviewer gets review.md (stages, uncovered/spill and worst red per view and height band,
zones_clay, preflight), compare.png (concept | clay | wire | overlay | textured) and a summary of
spec.json, and answers four questions: which parts cause the red (model outside the sheet) and
the green (sheet not covered) of each failing view, what identity is missing against the sheet,
three ordered spec changes with the gain expected, and whether the fault is the author, the
massing, the fit or the DSL (a missing kind). Writes <run>/diagnosis.json (findings, identity,
changes, owner, cost), <run>/diagnosis.md and a `## Diagnosis (LLM, not fed back)` block in
review.md. spec_pipeline --diagnose runs it after review.md and compare.png are written.
"""
import argparse
import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import apply_deltas as AD  # noqa: E402
import preflight as PF  # noqa: E402

VIEWS = ("front", "left", "back", "top", "bottom", "rts")
COLOURS = ("red", "green")
OWNERS = ("author", "massing", "fit", "dsl")
HEADING = "## Diagnosis (LLM, not fed back)"
SKIP_SECTIONS = ("Avalia", "Readiness", "Timing", "Few-shot")     # no signal for the reviewer
DIAG_SCHEMA = {
    "type": "object", "required": ["findings", "identity", "changes", "owner", "deltas", "expected"],
    "properties": {
        "findings": {"type": "array", "items": {
            "type": "object", "required": ["view", "part", "colour", "cause", "fix"],
            "additionalProperties": False,
            "properties": {"view": {"enum": list(VIEWS)}, "part": {"type": "string"},
                           "colour": {"enum": list(COLOURS)}, "cause": {"type": "string"},
                           "fix": {"type": "string"}}}},
        "identity": {"type": "array", "items": {"type": "string"}},
        "changes": {"type": "array", "minItems": 1, "maxItems": 3, "items": {
            "type": "object", "required": ["change", "gain"], "additionalProperties": False,
            "properties": {"change": {"type": "string"}, "gain": {"type": "string"}}}},
        "owner": {"type": "object", "required": ["who", "why"], "additionalProperties": False,
                  "properties": {"who": {"enum": list(OWNERS)}, "why": {"type": "string"}}},
        "deltas": {"type": "array", "maxItems": 6, "items": {      # shape checked per action by apply_deltas
            "type": "object", "required": ["part", "action"],
            "properties": {"part": {"type": "string"}, "action": {"type": "string"}, "why": {"type": "string"}}}},
        "expected": {"type": "object", "additionalProperties": {"type": "number"}}}}
PROMPT = """You diagnose ONE finished run of a low-poly game-unit model, to help humans and a paper. Nothing you say is fed back to the model: be concrete and honest, not polite.

Image 1 is compare.png: one row per view (front, left, back, top, bottom, rts), columns concept | clay | wire | overlay | textured. In the overlay the concept silhouette is GREEN where the model does not cover it (uncovered: something is missing there), the model is RED where it is outside the concept (spill: something is too big or in the wrong place), grey is a hit. Look at the images before you answer.

The run's report (review.md, stage sections only):
{review}

The spec, summarised (part name: count, kinds, palette key, centre range in model units; y is up; the unit is {height} tall):
{spec}
{extra}
Answer with one JSON object:
- "findings": for EVERY view that fails its gate or whose uncovered share is over its ceiling or whose worst red is large, one entry per cause: {{"view", "part" (a part NAME from the spec summary, or "(none)" when no part exists there), "colour" ("red": the part spills out of the sheet; "green": a part is missing or too small to cover the sheet), "cause", "fix"}}.
- "identity": what identity the sheet has that the model lacks (props, face, shape), one short string each.
- "changes": exactly three concrete spec changes, in order, each {{"change", "gain" (the expected gain, e.g. "front IoU +0.03")}}.
- "owner": {{"who": "author" | "massing" | "fit" | "dsl", "why"}}: who owns the main problem; "dsl" means the spec language lacks a kind to say it.
- "deltas": up to 6 machine-applied edits of single parts, most useful first, [] when none is safe. A part is addressed `<bone>#<k>` from the part table below (a bone with one part may be written bare); parts you do not name stay exactly as they are, and the build checks every delta, rejecting alone the ones outside its limits. Each delta is one of:
  {{"part": "spine#0", "action": "scale", "axis": "x" | "y" | "z" (omit = uniform), "value": {lo}-{hi}, "why"}} (axis scale: box/frustum dims, prism/cyl length, lathe height or squash)
  {{"part": "forearm.L#1", "action": "radius", "value": {lo}-{hi}, "why"}} (lathe, cyl, frustum, prism, limb, chain)
  {{"part": "head#0", "action": "move", "axis": "x" | "y" | "z", "value": metres, at most {move} in magnitude, "why"}}
  {{"part": "head#1", "action": "rotate", "axis": "x" | "y" | "z", "value": degrees, at most {rot} in magnitude, "why"}} (box, prism, dome, frustum without from/to only)
  {{"part": "<bone>", "action": "add", "kind": <a DSL kind>, "dims": [...], "at": [x, y, z], "material": <palette slot, optional>, "opts": {{...}} optional, "why"}} (at most {adds} per answer, each under {addshare:.0%} of the figure; on a .L/.R bone the twin is added too)
  {{"part": "pelvis#2", "action": "remove", "why"}} (only a part under {rmshare:.0%} of the figure)
  Edits to a .L/.R part are mirrored to its twin by the build; do not send both. One delta per part. Never write other fields.
- "expected": {{"<view>": the IoU gain you expect on that view if the deltas apply, e.g. "left": 0.05}} for each view the deltas should move.

Part table (address, kind, dims, centre, palette key):
{parts}
"""


def spec_summary(spec):
    """One line per part name: count, kinds, palette keys and the range of the part centres."""
    groups = {}
    for p in spec["parts"]:
        groups.setdefault(p[0], []).append(p)
    lines = []
    for name, ps in groups.items():
        at = [p[3] for p in ps]
        lo = [round(min(a[i] for a in at), 2) for i in range(3)]
        hi = [round(max(a[i] for a in at), 2) for i in range(3)]
        lines.append(f"- {name}: {len(ps)}x {'/'.join(sorted({p[1] for p in ps}))}, "
                     f"{'/'.join(sorted({str(p[4]) for p in ps}))}, at {lo}..{hi}")
    return "\n".join(lines)


def part_table(spec):
    """One line per part with the address apply_deltas understands."""
    return "\n".join(f"- {a}: {p[1]} {[round(v, 2) for v in p[2]]} at {[round(v, 2) for v in PF.centre(p)]}, {p[4]}"
                     for a, p in AD.addresses(spec))


def spec_height(spec):
    """Top of the highest part (centre + half height): the unit's height, near enough."""
    return round(max(p[3][1] + p[2][1] / 2 for p in spec["parts"]), 2)


def review_stages(text):
    """review.md without the header, the empty evaluation table and the sections in SKIP_SECTIONS
    (and without a diagnosis block of an earlier run of this tool)."""
    text = text.split(HEADING)[0]
    parts = re.split(r"(?m)^(?=## )", text)
    return "".join(s for s in parts[1:] if not s[3:].startswith(SKIP_SECTIONS)).strip()


def failing_rules(run, unit, kind):
    """Preflight rules that FAIL for the run's spec (best effort: '' when the tool or sheet is missing)."""
    import spec_pipeline as SP
    sheet = SP.ROOT / "artifacts/model-sheets/refs" / unit / "sheet.jpg"
    if not sheet.exists():
        return ""
    out = SP.tool("preflight.py", run / "spec.json", kind, sheet).stdout
    bad = [name for name, res in SP.RULE_LINE.findall(out) if res == "FAIL"]
    return f"\nPreflight rules failing: {', '.join(bad) or 'none'}\n"


def attach_text(run):
    f = run / "attach.json"
    if not f.exists():
        return ""
    loose = [f"{x['part']} (bone {x['bone']}, parent {x['parent']})" for x in json.loads(f.read_text()).get("loose", [])]
    return f"\nLoose parts (attach): {', '.join(loose) or 'none'}\n"


def prompt_of(run, unit, kind):
    spec = json.loads((run / "spec.json").read_text())
    return PROMPT.format(review=review_stages((run / "review.md").read_text()),
                         spec=spec_summary(spec), height=spec_height(spec),
                         extra=failing_rules(run, unit, kind) + attach_text(run), parts=part_table(spec),
                         lo=AD.SCALE_RANGE[0], hi=AD.SCALE_RANGE[1], move=round(AD.MOVE_SHARE * spec_height(spec), 3),
                         rot=AD.ROTATE_MAX, adds=AD.ADD_MAX, addshare=AD.ADD_SHARE, rmshare=AD.REMOVE_SHARE)


def check_reply(txt):
    """Raise ValueError (a BAD_REPLY) when the reply is not a valid diagnosis."""
    import spec_pipeline as SP
    doc = SP.json_object(txt)
    missing = [k for k in DIAG_SCHEMA["required"] if k not in doc]
    if missing:
        raise ValueError(f"missing keys: {missing}")
    for f in doc["findings"]:
        if f.get("view") not in VIEWS or f.get("colour") not in COLOURS or not f.get("part"):
            raise ValueError(f"bad finding: {f}")
    if (doc["owner"] or {}).get("who") not in OWNERS:
        raise ValueError("owner.who must be one of " + "/".join(OWNERS))
    check_deltas(doc)
    return doc


def check_deltas(doc):
    """deltas: a list of objects with a part and an action (their fields are checked, and a bad delta rejected
    alone, by apply_deltas); expected: {view: number}."""
    if not isinstance(doc["deltas"], list) or any(not isinstance(d, dict) for d in doc["deltas"]):
        raise ValueError("deltas is a list of objects")
    exp = doc["expected"]
    if not isinstance(exp, dict) or any(v not in VIEWS or not AD.num(x) for v, x in exp.items()):
        raise ValueError(f"expected is {{view: number}} with views in {VIEWS}")


def delta_lines(doc):
    return "".join(f"- `{json.dumps(d)}`\n" for d in doc["deltas"]) or "- none\n"


def markdown(doc, cost):
    rows = "".join(f"| {f['view']} | {f['part']} | {f['colour']} | {f['cause']} | {f['fix']} |\n"
                   for f in doc["findings"])
    table = ("| view | part | colour | cause | fix |\n|---|---|---|---|---|\n" + rows) if rows else "no findings.\n"
    ident = "".join(f"- {s}\n" for s in doc["identity"]) or "- none\n"
    steps = "".join(f"{i}. {c['change']} (expected: {c['gain']})\n" for i, c in enumerate(doc["changes"], 1))
    return (f"### Parts behind the red and the green\n\n{table}\n### Missing identity\n\n{ident}\n"
            f"### Three changes, in order\n\n{steps}\n"
            f"### Deltas (applied by apply_deltas.py, expected {doc['expected']})\n\n{delta_lines(doc)}\n"
            f"### Owner: {doc['owner']['who']}\n\n{doc['owner']['why']}\n\n"
            f"cost: {cost['seconds']} s, {cost['tokens'].get('input_tokens', 0)} in / "
            f"{cost['tokens'].get('output_tokens', 0)} out tokens "
            f"(+{cost['tokens'].get('cache_read_input_tokens', 0)} cache read), model {cost['model']}\n")


def write_outputs(run, doc, cost):
    """diagnosis.json, diagnosis.md and the review.md block (replaced, not stacked, on a rerun)."""
    (run / "diagnosis.json").write_text(json.dumps({**doc, "cost": cost}, indent=2))
    body = markdown(doc, cost)
    (run / "diagnosis.md").write_text(f"# Diagnosis of {run.name}\n\nLLM, not fed back to the model.\n\n{body}")
    review = run / "review.md"
    text = review.read_text().split(HEADING)[0].rstrip("\n")
    review.write_text(f"{text}\n\n{HEADING}\n\n{body.replace('### ', '#### ')}")


def run_diagnosis(run, unit, kind="mass", model="session:opus", ask=None):
    """Diagnose `run`; returns the result dict. `ask(model, brief, images, schema, check)` defaults
    to spec_pipeline.ask. Reads the run, writes only diagnosis.* and the review.md block."""
    import spec_pipeline as SP
    ask = ask or SP.ask
    compare = run / "compare.png"
    if not compare.exists():
        raise RuntimeError(f"{compare} missing: run make_compare.py first")
    before, t0 = dict(SP.USAGE), time.monotonic()
    doc = check_reply(ask(model, prompt_of(run, unit, kind), [compare], DIAG_SCHEMA, check_reply))
    cost = {"seconds": round(time.monotonic() - t0, 1), "model": model,
            "tokens": {k: v - before.get(k, 0) for k, v in SP.USAGE.items() if v - before.get(k, 0)}}
    write_outputs(run, doc, cost)
    return {**doc, "cost": cost}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run", type=pathlib.Path)
    ap.add_argument("--id", required=True)
    ap.add_argument("--kind", default="mass")
    ap.add_argument("--model", default="session:opus")
    args = ap.parse_args()
    import spec_pipeline as SP
    spec = json.loads((args.run / "spec.json").read_text())
    SP.set_rig(spec.get("rig", "biped"), spec.get("rig_measure"))     # part_table measures the parts
    r = run_diagnosis(args.run, args.id, args.kind, args.model)
    print(f"diagnosis: {len(r['findings'])} findings, owner {r['owner']['who']}, {r['cost']['seconds']} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
