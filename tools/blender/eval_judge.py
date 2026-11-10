#!/usr/bin/env python3
"""Computer half of the human-vs-judge evaluation (IA_gen_paper/05-avaliacao-humana-vs-juiz.md).

    python3.14 tools/blender/eval_judge.py --make-sample [--seed 7] [--n 30]      # writes eval/sample-30.json
    python3.14 tools/blender/eval_judge.py --stimuli [--sample eval/sample-30.json] # renders / crops the images
    python3.14 tools/blender/eval_judge.py --sample eval/sample-30.json --model session:sonnet --out eval/computer-<ts>.json

Sample: stratified from IA_gen_paper/results-roster-v6.csv with a fixed seed, 15 bipeds spread over
the races + 15 non-bipeds, one of each of the worst rig families first (WORST_RIGS), the rest random.
Stimuli per unit (same images the human test shows in viewer /eval):
  model  : runs/draft/<id>/<run>/views-final/model-{front,left,wc3}.png (render_unit.py when missing)
  concept: eval/stimuli/<id>/concept-front.png = front panel of refs/<id>/sheet.jpg (split_sheet, de-inked)
  wc3    : artifacts/reference/hive/renders/<id>.png + icons/<id>.png (icon optional)
Judge: one `claude -p` call per unit (spec_pipeline.ask_session, model `session:<name>`), the same three
questions and 1-5 scale as the human page, JSON schema {q1, q2, q3, why}. The automatic numbers of
the unit (glb_parts_share, glb_front/left/rts IoU) come from the CSV and ride along in the output.
"""
import argparse
import csv
import datetime
import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAPER = ROOT.parent / "IA_gen_paper"
CSV = PAPER / "results-roster-v6.csv"
EVAL = ROOT / "artifacts/model-sheets/eval"
STIMULI = EVAL / "stimuli"
FINAL_MODELS = ROOT / "artifacts/model-sheets/runs/roster/roster-v6/final-models.json"
RENDERS = ROOT / "artifacts/reference/hive/renders"
ICONS = ROOT / "artifacts/reference/hive/icons"
REFS = ROOT / "artifacts/model-sheets/refs"
WORST_RIGS = ("ray", "wyrm", "spider_high", "drake", "harpy", "quadruped", "naga", "vehicle")
AUTO = {"parts": "glb_parts_share", "iou_front": "glb_front", "iou_left": "glb_left", "iou_rts": "glb_rts"}
QUESTIONS = (
    ("q1", "Does the model look like the Warcraft III unit? (model vs the WC3 print and icon)"),
    ("q2", "Is the model faithful to the concept sheet? (model vs the concept front panel)"),
    ("q3", "Would you use it in the game as it is, for an alpha build?"),
)
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["q1", "q2", "q3", "why"],
          "properties": {**{q: {"type": "integer", "minimum": 1, "maximum": 5} for q, _ in QUESTIONS},
                         "why": {"type": "string"}}}
PROMPT = """You rate one low-poly 3D game-unit model (about 700 triangles, for an RTS in the style of
Warcraft III) made by an automatic pipeline. Images, in order:
  1. our model, front view        2. our model, left view        3. our model, RTS game camera
  4. the approved concept sheet, front panel (what the pipeline was asked to build)
  5. the original Warcraft III unit (render){icon}
Answer three questions on a 1-5 scale (1 = not at all, 3 = partly, 5 = yes, clearly):
  q1: {q1}
  q2: {q2}
  q3: {q3}
Judge shape, proportions, colours and props; ignore the grey background and the missing animation.
Answer with one JSON object and nothing else: {{"q1": int, "q2": int, "q3": int, "why": "one or two sentences"}}"""


def read_rows():
    with CSV.open() as f:
        return list(csv.DictReader(f))


def has_print(uid):
    return (RENDERS / f"{uid}.png").is_file()


def make_sample(seed, n):
    """Stratified sample of n units: n/2 bipeds (round-robin over races) + n/2 non-bipeds
    (one per WORST_RIGS family first). Only units with a WC3 print and a final model."""
    rows = [r for r in read_rows() if has_print(r["id"]) and (REFS / r["id"] / "sheet.jpg").is_file()]
    rng = random.Random(seed)
    bipeds = [r for r in rows if r["rig"] == "biped"]
    others = [r for r in rows if r["rig"] != "biped"]
    rng.shuffle(bipeds)
    rng.shuffle(others)
    half = n // 2
    by_race = {}
    for r in bipeds:
        by_race.setdefault(r["race"], []).append(r)
    picked = []
    races = sorted(by_race)
    rng.shuffle(races)
    while len(picked) < half and any(by_race.values()):
        for race in races:
            if by_race[race] and len(picked) < half:
                picked.append(by_race[race].pop())
    rest = []
    for rig in WORST_RIGS:
        cand = next((r for r in others if r["rig"] == rig and r not in rest), None)
        if cand:
            rest.append(cand)
    rest += [r for r in others if r not in rest][:n - half - len(rest)]
    sample = [{"id": r["id"], "name": r["name"], "race": r["race"], "rig": r["rig"], "run": r["final_run"],
               "group": "biped" if r["rig"] == "biped" else "non-biped"} for r in picked + rest]
    return {"seed": seed, "n": len(sample), "source": CSV.name, "units": sample}


def final_glb(uid):
    rel = json.loads(FINAL_MODELS.read_text())[uid]
    return ROOT / rel


def model_views(uid, render=True):
    """{front, left, wc3}: views-final renders of the unit's final GLB (rendered when missing)."""
    glb = final_glb(uid)
    out = glb.parent / "views-final"
    views = {v: out / f"model-{v}.png" for v in ("front", "left", "wc3")}
    if render and not all(p.is_file() for p in views.values()):
        import spec_pipeline as SP
        summary = glb.parent / "eye" / "summary.json"
        tilts = (json.loads(summary.read_text()).get("tilts") if summary.is_file() else None) or ""
        print(f"render {uid} -> {out.relative_to(ROOT)}", flush=True)
        SP.tool("render_unit.py", glb, out, f"tilt={tilts}", blender=True)
    return views


def concept_front(uid, kind="unit"):
    """eval/stimuli/<id>/concept-front.png: de-inked front panel of the approved sheet."""
    out = STIMULI / uid / "concept-front.png"
    if out.is_file():
        return out
    import split_sheet
    from silhouette import deink_image
    from views import layout_of
    work = STIMULI / uid / "split"
    panels = split_sheet.split(REFS / uid / "sheet.jpg", work, "sheet", layout_of(kind))
    deink_image(panels["front"], out)
    return out


def stimuli(uid, render=True):
    views = model_views(uid, render)
    icon = ICONS / f"{uid}.png"
    return {"front": views["front"], "left": views["left"], "wc3": views["wc3"],
            "concept": concept_front(uid), "print": RENDERS / f"{uid}.png",
            "icon": icon if icon.is_file() else None}


def judge_one(uid, model):
    import spec_pipeline as SP
    s = stimuli(uid)
    images = [s["front"], s["left"], s["wc3"], s["concept"], s["print"]] + ([s["icon"]] if s["icon"] else [])
    prompt = PROMPT.format(icon="        6. its Warcraft III icon" if s["icon"] else "",
                           **{q: text for q, text in QUESTIONS})
    reply = SP.ask_session(model, prompt, images, SCHEMA)
    doc = json.loads(reply)
    return {q: int(doc[q]) for q, _ in QUESTIONS} | {"why": str(doc.get("why", ""))}


def auto_numbers(uid, rows):
    r = next(x for x in rows if x["id"] == uid)
    return {k: (float(r[col]) if r.get(col) else None) for k, col in AUTO.items()}


def run_judge(sample, model, out):
    rows = read_rows()
    results = []
    for i, u in enumerate(sample["units"], 1):
        print(f"[{i}/{sample['n']}] {u['id']} {u['name']} ({u['rig']})", flush=True)
        try:
            scores = judge_one(u["id"], model.removeprefix("session:"))
        except Exception as err:            # one failed call must not lose the batch
            print(f"  FAILED: {err}", flush=True)
            scores = {"error": str(err)[-300:]}
        results.append(u | scores | {"auto": auto_numbers(u["id"], rows)})
        print(f"  {({k: scores.get(k) for k in ('q1', 'q2', 'q3')})}", flush=True)
        out.write_text(json.dumps({"model": model, "sample": sample.get("seed"),
                                   "generated": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                                   "questions": dict(QUESTIONS), "results": results}, indent=1) + "\n")
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--make-sample", action="store_true")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--stimuli", action="store_true", help="only prepare the images")
    ap.add_argument("--sample", default=str(EVAL / "sample-30.json"))
    ap.add_argument("--model", default="session:sonnet")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    EVAL.mkdir(parents=True, exist_ok=True)
    sample_path = pathlib.Path(args.sample)
    if args.make_sample:
        sample = make_sample(args.seed, args.n)
        sample_path.write_text(json.dumps(sample, indent=1) + "\n")
        print(f"{sample_path}: {sample['n']} units, "
              f"{sum(u['group'] == 'biped' for u in sample['units'])} bipeds")
        return
    sample = json.loads(sample_path.read_text())
    if args.stimuli:
        for u in sample["units"]:
            s = stimuli(u["id"])
            missing = [k for k, p in s.items() if p is not None and not p.is_file()]
            print(f"{u['id']}: {'ok' if not missing else 'MISSING ' + ','.join(missing)}")
        return
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = pathlib.Path(args.out) if args.out else EVAL / f"computer-{ts}.json"
    run_judge(sample, args.model, out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
