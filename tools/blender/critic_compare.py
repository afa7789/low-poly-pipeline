#!/usr/bin/env python3
"""L16-2 battery report (PIPELINE 34.L16-2): v16-critic-r1 (critic + fixer) against v16-r1 (one model) and the fair control l15-col-part-outline.

    python3.14 tools/blender/critic_compare.py [--units n005,hfoo] [--table] [--images] [--judge] [--accept]

--table    (measures the final model.glb of the three runs through the eye stage's own gate and renders, eye_stage.measure with swept
           cameras, into runs/draft/<id>/<run>/l16-measure/, kept) per unit and run: parts k/n, IoU / spill per view, tris; per unit the defects found / resolved by round, fix rate, seconds, calls,
           cost (USD, from the CLI)                                                                  -> history/2026-10-30-l16-critic/table.md
--images   per unit and view a row: concept | control | v16 | critic                               -> history/2026-10-30-l16-critic/<id>.png
--judge    review_pair.py (session:opus, one vote at a time) critic x v16 and critic x control on the 6 units, kept as
           runs/draft/<id>/v16-critic-r1/pairwise-v16.json and pairwise-control.json
--accept   the brief's acceptance: sheet and artist >= 3-1 for the critic over v16 in >= 4/6, form >= 2-2 in >= 4/6, fix rate >= 60 %,
           time <= 1.5x v16. Pure helpers (acceptance, fix_rate) are tested without disk."""
import argparse
import json
import pathlib
import sys
import tempfile

from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import eye_compare as EC  # noqa: E402
import eye_stage as ES  # noqa: E402
import make_compare as MC  # noqa: E402

DRAFT, VIEWS, FILES = EC.DRAFT, EC.VIEWS, EC.FILES
OUT = EC.ROOT / "artifacts/model-sheets/history/2026-10-30-l16-critic"
CRITIC, ONE, CONTROL = "v16-critic-r1", "v16-r1", "l15-col-part-outline"
RUNS = (CONTROL, ONE, CRITIC)
FIX_RATE_MIN, TIME_MAX, WINS_MIN = 0.6, 1.5, 4


def read(path):
    return EC.read(path)


def model_of(unit, run):
    """The model a run is judged by: the eye stage's last built round (not outlined, like its renders), else the run's model.glb (the control)."""
    s = read(DRAFT / unit / run / "eye/summary.json")
    return DRAFT / unit / run / (f"eye/round-{s['final_round']}/model.glb" if s.get("final_round") is not None else "model.glb")


def measure(unit, run):
    """The eval dict of the run's model under the eye stage's gate, renders kept in <run>/l16-measure/."""
    work = DRAFT / unit / run / "l16-measure"
    cached = work / "eval.json"
    if not cached.exists():
        spec = read(DRAFT / unit / run / "spec.json")
        ev = ES.measure(model_of(unit, run), work, ES.REFS / unit / "sheet.jpg", spec.get("rig") or "biped")
        cached.write_text(json.dumps(ev, indent=1))
    return read(cached)


def fix_rate(summaries):
    """Pooled fix rate of the critic: resolved defects / defects listed before, over all rounds of all units (None without a list)."""
    done = [c for s in summaries for c in s.get("critic", []) if c.get("of_previous")]     # an error entry has no of_previous
    total = sum(c["of_previous"] for c in done)
    return sum(c["resolved"] for c in done) / total if total else None


def votes(result, axis):
    """Votes of B (the critic run) on an axis."""
    return result[axis]["B"]


def acceptance(results, summaries, baseline):
    """The brief's acceptance. results: {unit: pairwise critic(B) x v16(A)}, summaries: {unit: eye summary of the critic run}, baseline: {unit: of v16-r1}."""
    both = sorted(u for u, r in results.items() if votes(r, "sheet") >= 3 and votes(r, "artist") >= 3)
    form = sorted(u for u, r in results.items() if votes(r, "form") >= 2)
    rate = fix_rate(summaries.values())
    seconds, base_seconds = (sum(s.get("seconds") or 0 for s in d.values()) for d in (summaries, baseline))
    ratio = seconds / base_seconds if base_seconds else None
    return {"sheet+artist >= 3-1 in >= 4/6": len(both) >= WINS_MIN, "won": both, "form >= 2-2 in >= 4/6": len(form) >= WINS_MIN, "form ok": form,
            "fix rate >= 60 %": rate is not None and rate >= FIX_RATE_MIN, "fix rate": rate, "time <= 1.5x v16": ratio is not None and ratio <= TIME_MAX, "time ratio": ratio,
            "accepted": len(both) >= WINS_MIN and len(form) >= WINS_MIN and rate is not None and rate >= FIX_RATE_MIN and ratio is not None and ratio <= TIME_MAX}


# ---------------------------------------------------------------- table
def view_row(unit, run, ev, summary):
    tris = (next((r["tris"] for r in summary.get("rounds", []) if r.get("round") == summary.get("final_round") and "tris" in r), None)
            if summary else None)
    return (f"| {unit} | {run} | {ev['parts'][0]}/{ev['parts'][1]} | {EC.per_view(ev['views'], 'iou')} | {EC.per_view(ev['views'], 'spill')} "
            f"| {tris or '–'} | {EC.v(summary.get('seconds'), 0) if summary else '–'} | {summary.get('llm_calls', '–') if summary else '–'} |")


def table(units):
    lines = ["| unit | run | parts | IoU f/l/b/top/bot/rts | spill | tris | s | calls |", "|---" * 8 + "|"]
    for u in units:
        lines += [view_row(u, run, measure(u, run), read(DRAFT / u / run / "eye/summary.json")) for run in RUNS]
    lines += ["", "| unit | critic call | defects listed | previous resolved | fix rate | verdict | s | USD | fixer said fixed |", "|---" * 9 + "|"]
    for u in units:
        s = read(DRAFT / u / CRITIC / "eye/summary.json")
        for c in (c for c in s.get("critic", []) if "error" not in c):
            fixed = len((s.get("fixed") or {}).get(str(c["round"]), [])) if not c.get("audit") else "–"
            usd = (c["usage"].get("cost_micro_usd") or 0) / 1e6
            lines.append(f"| {u} | round {c['round']}{' (audit)' if c.get('audit') else ''} | {c['defects']} | {c['resolved']}/{c['of_previous']} "
                         f"| {EC.v(c['fix_rate'], 2)} | {c['verdict']} | {c['seconds']:.0f} | {usd:.2f} | {fixed} |")
    lines += ["", f"pooled fix rate: {EC.v(fix_rate(read(DRAFT / u / CRITIC / 'eye/summary.json') for u in units), 2)}"]
    return "\n".join(lines)


# ---------------------------------------------------------------- images
def sheet(unit):
    cw, ch = MC.CELL
    img = Image.new("RGB", (cw * (1 + len(RUNS)), 20 + (ch + 20) * len(VIEWS)), MC.BG)
    d = ImageDraw.Draw(img)
    EC.RUN = ONE
    for run in RUNS:
        measure(unit, run)
    with tempfile.TemporaryDirectory() as tmp:
        concept = EC.concept_cells(unit, tmp)
    for x, label in enumerate(["concept", "control (v15 + contour)", "v16 (one model)", "critic + fixer"]):
        d.text((x * cw + 6, 4), label, fill=(255, 255, 255))
    for y, view in enumerate(VIEWS):
        top = 20 + y * (ch + 20)
        if view in concept:
            img.paste(concept[view], (0, top))
        for x, run in enumerate(RUNS):
            img.paste(ES.cell(DRAFT / unit / run / "l16-measure/views" / f"model-{FILES.get(view, view)}.png"), ((x + 1) * cw, top))
        d.text((4, top + ch), view, fill=(255, 255, 255))
    return img


# ---------------------------------------------------------------- the judge
def judge(unit, against, name):
    """review_pair.compare(against, critic run) one vote at a time; kept as pairwise-<name>.json beside the critic run."""
    EC.RUN = CRITIC
    return EC.judge(unit, against, name)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--units", default=",".join(EC.AM.UNITS))
    for f in ("table", "images", "judge", "accept"):
        ap.add_argument("--" + f, action="store_true")
    args = ap.parse_args(argv)
    units = args.units.split(",")
    OUT.mkdir(parents=True, exist_ok=True)
    if args.judge:
        for u in units:
            judge(u, DRAFT / u / ONE, "v16")
            judge(u, DRAFT / u / CONTROL, "control")
    if args.table:
        text = table(units)
        (OUT / "table.md").write_text(text + "\n")
        print(text)
    if args.images:
        for u in units:
            im = sheet(u)
            im.resize((im.width // 2, im.height // 2), Image.LANCZOS).save(OUT / f"{u}.png")
            print("wrote", OUT / f"{u}.png")
    if args.accept:
        res = {u: read(DRAFT / u / CRITIC / "pairwise-v16.json") for u in units}
        print(json.dumps(acceptance({u: r for u, r in res.items() if r}, {u: read(DRAFT / u / CRITIC / "eye/summary.json") for u in units},
                                    {u: read(DRAFT / u / ONE / "eye/summary.json") for u in units}), indent=1))


if __name__ == "__main__":
    main()
