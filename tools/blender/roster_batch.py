#!/usr/bin/env python3
"""Roster batch: the whole model chain for any unit of the roster, no human hand, with resume (PIPELINE 38).

    python3.14 tools/blender/roster_batch.py --units n01I,n01N | --all-units [--jobs 2] [--run-id roster-v1]
        [--dry-run] [--stage prompt|sheets|parts|model|all] [--resume]

Per unit, in order, each stage idempotent (skipped when its outputs exist, with --resume or always for the data stages):
  prompt  prompts/<id>/unit-<id>{,-hard,-hard-clean,-props}.txt: unit_facts --emit-prompt writes the stubs, then ONE
          `claude -p` (session, no API credit) fills the four templates from the compendium card, like the hand-written ones.
  sheets  refs/<id>/sheet{,-hard,-hard-clean,-props}.jpg via artifacts/model-sheets/generate.py (nano-banana; the
          variants are image-to-image edits of sheet.jpg); props only when the unit has a props prompt (not body parts).
  parts   segment_sheet.py (parts.json + identity) -> parts_gate.py freeze (sheet.json) -> prompts/<id>/props.json derived
          from the parts the segmenter marked `prop` (name, bone, extent from box3d) when the unit has any.
  model   spec_pipeline.py with the v18-cvt recipe spelled out by flag (--eye on, fuse 12, union bone @ cvt, paint box,
          hull outline), --deterministic, --run <run-id>; race from the compendium, rig from RIG_OF / the card's words.
State in artifacts/model-sheets/runs/roster/<run-id>/status.json (per unit: stage, seconds, estimated cost, truncated error,
paths), one log per unit in logs/<id>.log, the final markdown table in table.md. A failing unit never stops the others.
The pure functions (unit state, stage plan, rig guess, props from parts, parsers, table, estimate) are tested in
tests/tools/blender/test_roster_batch.py without API or Blender; only `run_*`, `step` and `main` touch processes.
"""
import argparse
import concurrent.futures as cf
import json
import pathlib
import re
import subprocess
import sys
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
MSHEETS = ROOT / "artifacts/model-sheets"
REFS, PROMPTS, DRAFT = MSHEETS / "refs", MSHEETS / "prompts", MSHEETS / "runs/draft"
ROSTER = MSHEETS / "runs/roster"
COMPENDIUM = ROOT / "data/compendium.json"
STAGES = ("prompt", "sheets", "parts", "model")
SHEETS = ("sheet", "sheet-hard", "sheet-hard-clean", "sheet-props")        # refs/<id>/<name>.jpg
REQUIRED, OPTIONAL = SHEETS[:2], SHEETS[2:]      # hard-clean: no A-pose for quadruped/wyrm/drake (22.L4-4a); props: body parts (§16)
PROMPT_OF = {"sheet": "unit", "sheet-hard": "unit-hard", "sheet-hard-clean": "unit-hard-clean", "sheet-props": "unit-props"}
STUB_MARK = "# Fill from template"                                          # unit_facts.emit_prompt writes this header
SESSION_MODEL = "session:opus"
USD_PER_SHEET = {"sheet": 0.046, "sheet-hard": 0.051, "sheet-hard-clean": 0.051, "sheet-props": 0.051}   # generate.py docstring
USD_RTS = 3 * 0.051           # spec_pipeline.ensure_rts draws sheet-rts, sheet-hard-rts, sheet-hard-clean-rts (1K edits)
# measured in PIPELINE 38 (mean of the samples): prompt 1 unit (n00L, 111-115 s), parts 2 (53, 72 s), model 2 (1744, 1514 s, whole
# spec_pipeline with 3 author variants + eye); sheets NOT measured: no image was drawn, 45 s is a guess
MEDIANS_S = {"prompt": 113.0, "sheets": 45.0, "parts": 63.0, "model": 1629.0}
# rig family per unit when the card's words are not enough: the flags the batteries used (v15.sh, 22.L4-4a, v2-hard-r2)
RIG_OF = {"n00U": "spider", "n01N": "spider_high", "n01W": "spider_high", "n017": "quadruped", "n018": "quadruped",
          "n00H": "wyrm", "n010": "drake", "n01I": "biped"}
RIG_WORDS = (("spider", "spider"), ("quadruped", "quadruped"), ("wolf", "quadruped"), ("bear", "quadruped"), ("hound", "quadruped"),
             ("felhound", "quadruped"), ("drake", "drake"), ("dragon", "drake"), ("wyrm", "wyrm"), ("serpent", "serpent"),
             ("naga", "naga"), ("harpy", "harpy"), ("rider", "mounted"), ("mounted", "mounted"), ("tank", "vehicle"),
             ("cart", "vehicle"), ("wagon", "vehicle"), ("vehicle", "vehicle"))
EYE_RECIPE = ["--eye", "on", "--eye-rounds", "3", "--eye-stop", "model", "--eye-fuse", "12", "--eye-union", "bone",
              "--eye-union-reduce", "cvt", "--eye-paint", "box", "--outline", "hull"]        # runs/draft/hfoo/v18-cvt/leva18.json
PROPS_SLACK = (0.8, 1.2)      # props.json extent bracket around the longest side of the segmenter's box3d, in H


# ---- roster and per-unit facts (pure over the compendium dict)

def roster(comp):
    """[{id, name, race, card}] of every kind == "unit" entry, in compendium order."""
    out = []
    for race in comp["races"]:
        for e in race["entries"]:
            if e.get("kind") == "unit":
                out.append({"id": e["id"], "name": e["name"], "race": race["name"],
                            "card": " ".join(str(e.get(k) or "") for k in ("description", "tooltip", "extendedTooltip"))})
    return out


def rig_of(uid, text):
    """Rig family: RIG_OF when listed, else the first RIG_WORDS hit in the unit's name + card text, else biped."""
    if uid in RIG_OF:
        return RIG_OF[uid]
    low = (text or "").lower()
    return next((rig for word, rig in RIG_WORDS if re.search(rf"\b{word}s?\b", low)), "biped")


# ---- what exists on disk (pure over the paths)

def is_stub(path):
    """A prompt file unit_facts --emit-prompt wrote (comment header only), or a missing one."""
    return not path.exists() or STUB_MARK in path.read_text()


def prompt_path(uid, base, prompts=PROMPTS):
    """prompts/<id>/unit-<id>[-hard].txt (hand-written or filled), else unit[-hard].txt when it is not a stub, else None."""
    suffix = base[len("unit"):]
    for p in (prompts / uid / f"unit-{uid}{suffix}.txt", prompts / uid / f"{base}.txt"):
        if not is_stub(p):
            return p
    return None


def unit_state(uid, run_id, refs=REFS, prompts=PROMPTS, draft=DRAFT):
    """What the unit already has: prompts per sheet, sheets, parts.json / sheet.json / props.json, the run's model."""
    have_prompt = {s: prompt_path(uid, PROMPT_OF[s], prompts) is not None for s in SHEETS}
    have_sheet = {s: (refs / uid / f"{s}.jpg").exists() for s in SHEETS}
    run = draft / uid / run_id
    return {"prompts": have_prompt, "sheets": have_sheet,
            "parts": (refs / uid / "parts.json").exists(), "sheet_json": (refs / uid / "sheet.json").exists(),
            "props_json": (prompts / uid / "props.json").exists(),
            "rts_missing": sum(1 for s in SHEETS[:3] if not (refs / uid / f"{s}-rts.jpg").exists()),
            "model": (run / "model.glb").exists() and (run / "review.md").exists()}


def stage_done(state, stage):
    """True when the stage's outputs are on disk. An optional sheet (hard-clean, props) counts only when the unit has its prompt."""
    if stage == "prompt":
        return all(state["prompts"][s] for s in REQUIRED)
    if stage == "sheets":
        return all(state["sheets"][s] for s in REQUIRED) and all(state["sheets"][s] or not state["prompts"][s] for s in OPTIONAL)
    if stage == "parts":
        return state["parts"] and state["sheet_json"]
    return state["model"]


def plan(state, stage="all", resume=True):
    """The stages to run, in order: up to `stage` (all = model); a stage whose outputs exist is skipped (the data stages always:
    a sheet or a parts.json is never redrawn by this tool; the model run only with --resume)."""
    wanted = STAGES if stage == "all" else STAGES[:STAGES.index(stage) + 1]
    return [s for s in wanted if not (stage_done(state, s) and (resume or s != "model"))]


def reached(state):
    """The last stage whose outputs exist with every earlier one ('-' when none)."""
    last = "-"
    for s in STAGES:
        if not stage_done(state, s):
            break
        last = s
    return last


# ---- props.json from parts.json (pure)

def props_from_parts(doc, slack=PROPS_SLACK):
    """props.json rows from the parts the segmenter marked `prop`: name, where (anchor + bone), the bone (and its L/R twin), the
    extent bracket = longest side of box3d in H x slack. [] when no part is a prop (the unit's props are body parts)."""
    H = float(doc.get("H") or 2.0)
    out = []
    for p in doc.get("parts", []):
        if not p.get("prop") or not p.get("box3d"):
            continue
        lo, hi = p["box3d"]
        longest = max(b - a for a, b in zip(lo, hi)) / H
        bone = p.get("bone") or "spine"
        twin = [bone[:-1] + ("L" if bone.endswith("R") else "R")] if bone[-2:] in (".R", ".L") else []
        out.append({"name": p["name"], "where": f"anchor {p.get('anchor') or bone}, on bone {bone}", "bones": [bone, *twin],
                    "extent": [round(longest * slack[0], 3), round(longest * slack[1], 3)]})
    return out


# ---- parsers (pure)

def parse_pipeline_line(text):
    """The gate line spec_pipeline prints last ("<id>\\t<run>\\t<tag>\\ttris N/lo-hi\\t...\\t<verdict>") -> {tris, preflight, stage1,
    stage2, verdict}; {} when the text has none."""
    rows = [ln for ln in text.splitlines() if ln.count("\t") >= 6 and "\ttris " in ln]
    if not rows:
        return {}
    cells = rows[-1].split("\t")
    got = {"verdict": cells[-1].strip()}
    for c in cells:
        if c.startswith("tris "):
            got["tris"] = int(c.split()[1].split("/")[0])
        for key in ("preflight", "stage1", "stage2"):
            if c.startswith(key + " "):
                got[key] = c.split()[1]
    return got


def parse_eye_summary(summary):
    """tris and parts 'k/n' of the eye stage's final round (eye/summary.json); {} without rounds."""
    rounds = summary.get("rounds") or []
    if not rounds:
        return {}
    last = rounds[-1]
    parts = last.get("parts")
    if isinstance(parts, (list, tuple)):
        parts = f"{parts[0]}/{parts[1]}"
    return {"tris": last.get("tris"), "parts": parts}


def cause_of(text, n=200):
    """One line for a failed command: the last exception line of the traceback, else the last non-empty output line."""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return "no output"
    err = [ln for ln in lines if re.match(r"^\w*(Error|Exception|SystemExit)\b", ln) or ln.startswith("HTTP ")]
    return (err[-1] if err else lines[-1])[:n]


# ---- status rows, table, estimate (pure)

def new_entry(u, rig):
    return {"id": u["id"], "name": u["name"], "race": u["race"], "rig": rig, "stages": {}, "reached": "-", "total_s": 0.0, "cost_usd": 0.0}


def row_of(entry):
    """One table row from a status.json entry: unit, race, rig, stage reached, tris, parts, gate, time, cost."""
    model = entry["stages"].get("model") or {}
    err = next((f"{s}: {d['error']}" for s, d in entry["stages"].items() if d.get("error")), "")
    return {"unit": entry["id"], "race": entry["race"], "rig": entry["rig"], "reached": entry["reached"],
            "tris": model.get("tris"), "parts": model.get("parts"), "gate": model.get("verdict") or ("-" if not err else "FAIL"),
            "s": round(entry["total_s"]), "usd": round(entry["cost_usd"], 3), "error": err}


def table(entries):
    """Markdown: one line per unit (sorted by id)."""
    out = ["| unit | race | rig | stage reached | tris | parts k/n | gate | s | US$ | error |", "|---" * 10 + "|"]
    for r in (row_of(e) for e in sorted(entries, key=lambda e: e["id"])):
        out.append(f"| {r['unit']} | {r['race']} | {r['rig']} | {r['reached']} | {r['tris'] or '–'} | {r['parts'] or '–'} | {r['gate']} "
                   f"| {r['s']} | {r['usd']:.2f} | {r['error'][:80]} |")
    return "\n".join(out)


def sheet_cost(state):
    """US$ of the sheets the unit still lacks (+ the 3 rts views when it has no model run yet)."""
    need = [s for s in SHEETS if not state["sheets"][s] and (s in REQUIRED or state["prompts"][s] or not stage_done(state, "prompt"))]
    rts = 0 if state["model"] else min(3, state.get("rts_missing", 3) + sum(1 for s in need if s != "sheet-props")) * USD_RTS / 3
    return sum(USD_PER_SHEET[s] for s in need) + rts, len(need)


def estimate(states, medians=MEDIANS_S):
    """Over {id: state}: units with each stage done ('ready'), the stages still to run, seconds (sequential) and US$."""
    ready = {s: sum(1 for st in states.values() if stage_done(st, s)) for s in STAGES}
    todo = {s: sum(1 for st in states.values() if s in plan(st)) for s in STAGES}
    seconds = sum(todo[s] * medians[s] for s in STAGES)
    usd = sum(sheet_cost(st)[0] for st in states.values() if "sheets" in plan(st) or "model" in plan(st))
    images = sum(sheet_cost(st)[1] for st in states.values() if "sheets" in plan(st))
    return {"units": len(states), "ready": ready, "todo": todo, "images": images, "seconds": round(seconds), "usd": round(usd, 2)}


def estimate_text(est, jobs=2):
    h = est["seconds"] / 3600
    lines = [f"{est['units']} units; ready per stage: " + ", ".join(f"{s} {est['ready'][s]}" for s in STAGES),
             "to run: " + ", ".join(f"{s} {est['todo'][s]}" for s in STAGES) + f"; {est['images']} sheet images",
             f"estimate: {h:.1f} h sequential ({h / jobs:.1f} h at --jobs {jobs}), US$ {est['usd']:.2f} (nano-banana; the Claude session is free)"]
    return "\n".join(lines)


# ---- the commands (processes)

def prompt_fill_brief(u, rig, templates, example):
    """The brief of the one claude -p call that fills the four templates for a unit."""
    return (f"You write image prompts for the model-sheet pipeline of a dieselpunk dark-fantasy low-poly RTS. Fill the four templates "
            f"below for unit {u['id']} ({u['race']} {u['name']}, rig family {rig}) from its facts and card. Keep every template sentence "
            f"that is not a {{placeholder}} verbatim; replace each placeholder and each <angle-bracket> instruction with concrete text; "
            f"write one 'Panel N' line per view saying what is visible in that view; props are the card's, at most 4, largest crudest "
            f"shape. When the unit's props are body parts (plates, claws, fists), set unit_props to null and say so in the hard prompt.\n\n"
            f"FACTS\n{u['facts']}\n\nCARD\n{u['card']}\n\n" + "".join(f"TEMPLATE {k}\n{v}\n\n" for k, v in templates.items())
            + f"EXAMPLE of a finished unit prompt (another unit):\n{example}\n")


PROMPT_SCHEMA = {"type": "object", "required": ["unit", "unit_hard", "unit_hard_clean", "unit_props"],
                 "properties": {k: {"type": ["string", "null"]} for k in ("unit", "unit_hard", "unit_hard_clean", "unit_props")}}


def claude_json(brief, schema, log):
    """One `claude -p` (the local login, like spec_pipeline.ask_session) -> the structured reply dict."""
    import tempfile
    argv = ["claude", "-p", "--model", SESSION_MODEL.split(":")[1], "--tools", "Read", "--allowedTools", "Read", "--no-session-persistence", "--setting-sources", "",
            "--strict-mcp-config", "--output-format", "json", "--json-schema", json.dumps(schema)]
    with tempfile.TemporaryDirectory() as cwd:
        out = subprocess.run(argv, input=brief, cwd=cwd, capture_output=True, text=True, timeout=1800)
    log.write_text(log.read_text() + f"\n$ claude -p ... ({len(brief)} chars)\n{out.stderr[-2000:]}\n")
    r = json.loads(out.stdout)
    if r.get("is_error") or r.get("structured_output") is None:
        raise RuntimeError(f"claude -p: {str(r.get('result'))[-200:]}")
    return r["structured_output"]


def run_prompt(u, rig, log):
    """Stage prompt: the stubs (unit_facts --emit-prompt) and the filled prompts/<id>/unit-<id>*.txt; a prompt already written
    by hand is never overwritten."""
    facts = subprocess.run([sys.executable, str(MSHEETS / "unit_facts.py"), u["id"]], capture_output=True, text=True, cwd=MSHEETS)
    subprocess.run([sys.executable, str(MSHEETS / "unit_facts.py"), "--emit-prompt", u["id"]], capture_output=True, text=True, cwd=MSHEETS)
    templates = {k: (PROMPTS / f"00-template-{k}.txt").read_text() for k in ("unit", "unit-hard", "unit-hard-clean", "props")}
    example = (PROMPTS / "n01N/unit-n01N.txt").read_text()
    got = claude_json(prompt_fill_brief({**u, "facts": facts.stdout}, rig, templates, example), PROMPT_SCHEMA, log)
    written = []
    for key, suffix in (("unit", ""), ("unit_hard", "-hard"), ("unit_hard_clean", "-hard-clean"), ("unit_props", "-props")):
        if got.get(key) and prompt_path(u["id"], "unit" + suffix) is None:
            path = PROMPTS / u["id"] / f"unit-{u['id']}{suffix}.txt"
            path.write_text(got[key].strip() + "\n")
            written.append(str(path.relative_to(ROOT)))
    if not all(prompt_path(u["id"], PROMPT_OF[s]) for s in REQUIRED):
        raise RuntimeError(f"prompt fill left a required prompt missing (wrote {len(written)})")
    return {"paths": written, "cost_usd": 0.0}


def shell(argv, log, cwd=ROOT):
    """Run argv, append its output to the unit's log; raise with the cause on a non-zero exit. Returns stdout."""
    done = subprocess.run(argv, capture_output=True, text=True, cwd=cwd)
    with log.open("a") as f:
        f.write(f"\n$ {' '.join(map(str, argv))}\n{done.stdout}{done.stderr}\n")
    if done.returncode:
        raise RuntimeError(cause_of(done.stdout + done.stderr))
    return done.stdout


def run_sheets(u, state, log):
    """Stage sheets: generate.py per missing sheet (variants edit sheet.jpg); the props sheet only with a props prompt."""
    out, usd = [], 0.0
    for s in SHEETS:
        prompt = prompt_path(u["id"], PROMPT_OF[s])
        if state["sheets"][s] or (s in OPTIONAL and prompt is None):
            continue
        if prompt is None:
            raise RuntimeError(f"no prompt for {s}")
        argv = [sys.executable, "generate.py", str(prompt), "--id", u["id"], "--out", f"refs/{u['id']}", "--name", s]
        if s != "sheet":
            argv += ["--image", f"refs/{u['id']}/sheet.jpg"]
        shell(argv, log, cwd=MSHEETS)
        usd += USD_PER_SHEET[s]
        out.append(f"artifacts/model-sheets/refs/{u['id']}/{s}.jpg")
        state["sheets"][s] = True
    return {"paths": out, "cost_usd": usd}


def run_parts(u, rig, state, log):
    """Stage parts: segment_sheet (parts.json), parts_gate freeze (sheet.json), props.json from the prop parts."""
    paths = []
    if not state["parts"]:
        shell([sys.executable, "tools/blender/segment_sheet.py", u["id"], "--rig", rig, "--race", u["race"], "--model", SESSION_MODEL], log)
        paths.append(f"artifacts/model-sheets/refs/{u['id']}/parts.json")
    if not state["sheet_json"]:
        shell([sys.executable, "tools/blender/parts_gate.py", "freeze", u["id"]], log)
        paths.append(f"artifacts/model-sheets/refs/{u['id']}/sheet.json")
    if not state["props_json"]:
        rows = props_from_parts(json.loads((REFS / u["id"] / "parts.json").read_text()))
        if rows:
            (PROMPTS / u["id"] / "props.json").write_text(json.dumps(rows, indent=2) + "\n")
            paths.append(f"artifacts/model-sheets/prompts/{u['id']}/props.json")
    return {"paths": paths, "cost_usd": 0.0}


def model_command(u, rig, run_id):
    return [sys.executable, "tools/blender/spec_pipeline.py", "--id", u["id"], "--race", u["race"], "--name", u["name"], "--kind", "mass",
            "--rig", rig, "--model", SESSION_MODEL, "--tag", "roster", "--run", run_id, "--deterministic", *EYE_RECIPE]


def run_model(u, rig, run_id, log):
    """Stage model: spec_pipeline with the v18-cvt recipe; the gate line and the eye summary feed the table."""
    run = DRAFT / u["id"] / run_id
    rts_missing = [s for s in SHEETS[:3] if not (REFS / u["id"] / f"{s}-rts.jpg").exists()]      # ensure_rts draws these
    try:
        out = shell(model_command(u, rig, run_id), log)
    except RuntimeError as err:
        if not (run / "model.glb").exists():
            raise
        out = log.read_text()              # exit 1 = a failed gate (CHECK), the model exists: report it, not an error
        err_note = str(err)
    else:
        err_note = ""
    got = parse_pipeline_line(out)
    summ = run / "eye/summary.json"
    if summ.exists():
        got = {**got, **{k: v for k, v in parse_eye_summary(json.loads(summ.read_text())).items() if v is not None}}
    return {**got, "paths": [str(run.relative_to(ROOT))], "cost_usd": len(rts_missing) * USD_RTS / 3, "note": err_note}


# ---- per unit and the batch

class Status:
    def __init__(self, path):
        self.path, self.lock = path, threading.Lock()
        self.doc = json.loads(path.read_text()) if path.exists() else {"units": {}}

    def put(self, entry):
        with self.lock:
            self.doc["units"][entry["id"]] = entry
            self.path.write_text(json.dumps(self.doc, indent=1))


def step(u, args, status):
    """All of one unit's planned stages, in order; a failure stops this unit only and is recorded."""
    rig = rig_of(u["id"], u["name"] + " " + u["card"])
    entry = status.doc["units"].get(u["id"]) or new_entry(u, rig)
    entry["rig"] = rig
    log = ROSTER / args.run_id / "logs" / f"{u['id']}.log"
    log.touch()
    state = unit_state(u["id"], args.run_id)
    for stage in plan(state, args.stage, args.resume):
        t0 = time.perf_counter()
        try:
            got = {"prompt": lambda: run_prompt(u, rig, log), "sheets": lambda: run_sheets(u, state, log),
                   "parts": lambda: run_parts(u, rig, state, log), "model": lambda: run_model(u, rig, args.run_id, log)}[stage]()
            rec = {"state": "done", **got}
        except Exception as err:          # noqa: BLE001 - every failure of a unit is a row, never a stop
            rec = {"state": "failed", "error": str(err)[:200]}
        rec["s"] = round(time.perf_counter() - t0, 1)
        entry["stages"][stage] = rec
        entry["total_s"] += rec["s"]
        entry["cost_usd"] += rec.get("cost_usd", 0.0)
        entry["reached"] = reached(unit_state(u["id"], args.run_id))
        status.put(entry)
        print(f"{u['id']} {stage}: {rec['state']} {rec.get('error', '')} ({rec['s']} s)", file=sys.stderr, flush=True)
        if rec["state"] == "failed":
            break
        state = unit_state(u["id"], args.run_id)
    entry["reached"] = reached(state)
    status.put(entry)
    return entry


def dry_run(units, args):
    states = {u["id"]: unit_state(u["id"], args.run_id) for u in units}
    rows = [{**new_entry(u, rig_of(u["id"], u["name"] + " " + u["card"])), "reached": reached(states[u["id"]]),
             "stages": {s: {"state": "todo"} for s in plan(states[u["id"]], args.stage, args.resume)}} for u in units]
    print(table(rows))
    print()
    print(estimate_text(estimate(states), args.jobs))
    for r in rows:
        print(f"{r['id']}: rig {r['rig']}, to run: {', '.join(r['stages']) or 'nothing'}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--units", default="", help="comma-separated unit ids")
    ap.add_argument("--all-units", action="store_true", help="every kind == unit of data/compendium.json (162)")
    ap.add_argument("--jobs", type=int, default=2, help="units in parallel (each one runs at most one Blender / claude at a time)")
    ap.add_argument("--run-id", default="roster-v1", help="runs/draft/<id>/<run-id> and runs/roster/<run-id>/")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, the table of what exists and the estimate; run nothing")
    ap.add_argument("--stage", choices=(*STAGES, "all"), default="all", help="run up to this stage")
    ap.add_argument("--resume", action="store_true", help="skip a model run whose model.glb + review.md exist (the data stages always skip)")
    args = ap.parse_args(argv)
    comp = json.loads(COMPENDIUM.read_text())
    want = [x for x in args.units.split(",") if x]
    units = [u for u in roster(comp) if args.all_units or u["id"] in want]
    missing = sorted(set(want) - {u["id"] for u in units})
    if missing:
        sys.exit(f"not units of the compendium: {', '.join(missing)}")
    if not units:
        ap.error("--units or --all-units")
    if args.dry_run:
        return dry_run(units, args)
    out = ROSTER / args.run_id
    (out / "logs").mkdir(parents=True, exist_ok=True)
    status = Status(out / "status.json")
    with cf.ThreadPoolExecutor(max(1, args.jobs)) as pool:
        list(pool.map(lambda u: step(u, args, status), units))
    final = table(status.doc["units"].values())          # every unit of the run, also those of an earlier --resume call
    (out / "table.md").write_text(final + "\n")
    print(final)
    return 0


if __name__ == "__main__":
    sys.exit(main())
