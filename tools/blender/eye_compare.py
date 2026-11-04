#!/usr/bin/env python3
"""L15-5 battery report (PIPELINE 33.L15-5): the runs v16-r1 (eye stage) of the 6 units against v15-r1 and the hand fix of L14-3.

    python3.14 tools/blender/eye_compare.py [--units n005,hfoo] [--table] [--images] [--judge] [--accept]

--table   per unit and round: seconds, model calls, triangles, parts k/n, IoU / spill / bare per view (the guards), the views whose IoU falls
          more than 2 sigma (noise-l12.json) below the v15 model measured by the same gate, components, stretch      -> history/2026-10-30-l15-eye/table.md
--images  per unit and view a row: concept | v15 | round 0 | round 1 | ... | hand fix (L14-3, the 3 units that have one)  -> history/2026-10-30-l15-eye/<id>.png
--judge   review_pair.py (session:opus, one vote at a time: the machine is shared) v16 x v15 on the 6 units and v16 x l14-fix on the 3 that
          have it; the results are kept in runs/draft/<id>/v16-r1/pairwise-v15.json and pairwise-fix.json
--accept  the brief's acceptance (judge form + artist >= 3-1 for v16 in >= 4/6 and >= 2/3 of the unseen units; IoU >= .6 in every coherent
          view; stretch <= 2.0; pieces <= 700 triangles; <= 15 min per unit). Pure helpers (falls, judged, acceptance) are tested without disk.

L16-1 (PIPELINE 34.L16-1), the rounds curve: runs v16-r9 (9 rounds, --eye-stop never) and its prefixes v16-r3 / v16-r6, against v16-r1 (L15-5, old prompt) and
the fair control l15-col-part-outline (v15 + outline).

    python3.14 tools/blender/eye_compare.py --l16 snapshot|judge|stop|table|images|accept [--units n005,hfoo]
snapshot  v16-r3 and v16-r6 = the first 3 / 6 rounds of v16-r9 (same trajectory, same prompt), finished like a run (outline, clay, stretch, hash)
judge     review_pair one vote at a time: r6 x r3, r9 x r6, r9 x r3, r3 x v16-r1, and r3 / r6 / r9 x control; kept as <run>/pairwise-<A>.json (resumes)
stop      the judge rule of --eye-stop judge replayed on v16-r9: round r x r-1 until 2 stalled rounds in a row; rounds, seconds saved   -> <run>/stop-curve.json
table     rounds x unit                                                              -> history/2026-10-30-l16-rounds/table.md
images    per unit: concept | control | r3 | r6 | r9, six views                      -> history/2026-10-30-l16-rounds/<id>.png
accept    the brief's acceptance for the default of --eye-rounds"""
import argparse
import copy
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ablation_matrix as AM  # noqa: E402
import make_compare as MC  # noqa: E402
import mesh_lint  # noqa: E402
import noise as NZ  # noqa: E402

ROOT = AM.ROOT
DRAFT = ROOT / "artifacts/model-sheets/runs/draft"
OUT = ROOT / "artifacts/model-sheets/history/2026-10-30-l15-eye"
RUN = "v16-r1"            # the run reported; critic_compare.py (L16-2) points it at v16-critic-r1
FIX = ROOT / "artifacts/model-sheets/history/2026-10-30-l14-fix"
SEEN = ("n02X", "n005", "n00U")           # the guidelines of the prompt were distilled from the diagnoses of these
UNSEEN = ("hfoo", "n017", "n01X")
VIEWS = AM.VIEWS
FILES = {"rts": "wc3"}
IOU_MIN, STRETCH_MAX, STRETCH_GOOD, TRIS_MAX, MINUTES_MAX = 0.6, 2.0, 1.5, 700, 15


def read(path):
    return json.loads(path.read_text()) if path.exists() else {}


def falls(unit, views, base, noise):
    """The views whose IoU is more than 2 sigma under the base's (the guard of the brief)."""
    return [v for v in VIEWS if v in views and v in base and views[v]["iou"] - base[v]["iou"] < -NZ.threshold(v, noise, unit=unit)]


def worst_stretch(anim):
    vals = [c["p99.5_stretch"] for c in (anim or {}).values() if c]
    return max(vals) if vals else None


def v(x, nd=3):
    return "–" if x is None else f"{x:.{nd}f}"


def per_view(views, key):
    return "/".join(v(views[w][key], 2) if w in views else "–" for w in VIEWS)


def rows_of(unit, noise):
    """The table rows of one unit: the v15 model under the eye stage's gate, then every built round."""
    s = read(DRAFT / unit / RUN / "eye/summary.json")
    if not s:
        return []
    base = s["base"]["views"]
    out = [{"unit": unit, "stage": "v15-r1", "s": None, "calls": None, "tris": None, "parts": s["base"]["parts"], "views": base, "falls": []}]
    for r in s["rounds"]:
        if "tris" in r:
            out.append({"unit": unit, "stage": f"round {r['round']}", "s": r["llm_s"] + r["build_s"] + r["measure_s"], "calls": 1 + r["resent"], "tris": r["tris"],
                        "parts": r["parts"], "views": r["views"], "falls": falls(unit, r["views"], base, noise)})
    return out


def table(units, noise):
    lines = ["| unit | stage | s | calls | tris | parts | IoU f/l/b/top/bot/rts | spill | bare | falls > 2σ vs v15 |", "|---" * 10 + "|"]
    for u in units:
        for r in rows_of(u, noise):
            parts = f"{r['parts'][0]}/{r['parts'][1]}"
            lines.append(f"| {u} | {r['stage']} | {v(r['s'], 0)} | {r['calls'] or '–'} | {r['tris'] or '–'} | {parts} | {per_view(r['views'], 'iou')} | {per_view(r['views'], 'spill')} "
                         f"| {per_view(r['views'], 'bare')} | {','.join(r['falls']) or '–'} |")
    lines += ["", "| unit | total s | model calls | resends | final round | pieces tris | file tris (+hull) | components | stretch p99.5 | v15 stretch |", "|---" * 10 + "|"]
    for u in units:
        s = read(DRAFT / u / RUN / "eye/summary.json")
        if not s or s.get("final_round") is None:
            lines.append(f"| {u} | no model |" + " |" * 8)
            continue
        lint = mesh_lint.lint(DRAFT / u / RUN / "model.glb")
        final = next(r for r in s["rounds"] if r.get("round") == s["final_round"] and "tris" in r)
        old = read(DRAFT / u / "v15-r1/anim.json")
        lines.append(f"| {u} | {s['seconds']} | {s['llm_calls']} | {s['resends']} | {s['final_round']} | {final['tris']} | {lint['tris']} | {lint['components']} "
                     f"| {v(worst_stretch(s.get('stretch')), 2)} | {v(worst_stretch(old), 2)} |")
    return "\n".join(lines)


# ---------------------------------------------------------------- images
def concept_cells(unit, tmp):
    return MC.concept_cells(MC.load_run(DRAFT / unit / RUN), pathlib.Path(tmp))


def round_dirs(unit):
    base = DRAFT / unit / RUN / "eye"
    return [("v15-r1", base / "base")] + [(f"round {r}", base / f"round-{r}") for r in range(4) if (base / f"round-{r}/model.glb").exists()]


def sheet(unit):
    cols = round_dirs(unit)
    fix = Image.open(FIX / f"{unit}.png") if (FIX / f"{unit}.png").exists() else None
    cw, ch = MC.CELL
    img = Image.new("RGB", (cw * (len(cols) + 1 + (fix is not None)), 20 + (ch + 20) * len(VIEWS)), MC.BG)
    d = ImageDraw.Draw(img)
    with tempfile.TemporaryDirectory() as tmp:
        concept = concept_cells(unit, tmp)
    for x, label in enumerate(["concept"] + [c[0] for c in cols] + (["hand fix (L14-3)"] if fix is not None else [])):
        d.text((x * cw + 6, 4), label, fill=(255, 255, 255))
    import eye_stage
    for y, view in enumerate(VIEWS):
        top = 20 + y * (ch + 20)
        if view in concept:
            img.paste(concept[view], (0, top))
        for x, (_, work) in enumerate(cols):
            stem = "input" if work.name == "base" else "model"
            img.paste(eye_stage.cell(work / "views" / f"{stem}-{FILES.get(view, view)}.png"), ((x + 1) * cw, top))
        if fix is not None:
            y0 = 40 + MC.TITLE_H + 2 * MC.GAP + y * (ch + MC.GAP)
            img.paste(fix.crop((2 * cw, y0, 3 * cw, y0 + ch)), ((len(cols) + 1) * cw, top))
        d.text((4, top + ch), view, fill=(255, 255, 255))
    return img


# ---------------------------------------------------------------- the judge
def judge(unit, against, name):
    """review_pair.compare(`against`, v16-r1) with one vote at a time; kept as pairwise-<name>.json beside the run."""
    import review_pair
    new = DRAFT / unit / RUN
    saved = review_pair.concurrent.futures.ThreadPoolExecutor
    review_pair.concurrent.futures.ThreadPoolExecutor = lambda n: saved(1)
    try:
        result = review_pair.compare(against, new, unit, "mass", "session:opus")
    finally:
        review_pair.concurrent.futures.ThreadPoolExecutor = saved
    shutil.move(new / "pairwise.json", new / f"pairwise-{name}.json")
    print(unit, review_pair.line(result))
    return result


def fix_run(unit, tmp):
    """A scratch copy of the hand fix's model with the v15 cameras, as a run dir for review_pair (the committed l14-fix dir is not touched)."""
    d = pathlib.Path(tmp) / unit / "l14-fix"
    d.mkdir(parents=True)
    shutil.copy(DRAFT / unit / "l14-fix/model.glb", d / "model.glb")
    shutil.copy(DRAFT / unit / "v15-r1/silhouette.json", d / "silhouette.json")
    return d


def judged(result):
    """(form B votes, artist B votes) of a pairwise result when B (v16) wins the axis, else 0 for it."""
    return tuple(result[a]["B"] if result[a]["winner"] == "B" else 0 for a in ("form", "artist"))


def wins(result):
    return all(x >= 3 for x in judged(result))


def acceptance(units, results, summaries):
    """The brief's acceptance. results: {unit: pairwise result v15 x v16}, summaries: {unit: eye summary}. {check: bool or list}."""
    won = {u for u, r in results.items() if wins(r)}
    built = {u: last_built(s) for u, s in summaries.items() if s.get("final_round") is not None}
    coherent_low = [f"{u} {w}" for u, r in built.items() for w, x in r["views"].items() if not x["incoherent"] and x["iou"] < IOU_MIN]
    stretch = max((worst_stretch(s.get("stretch")) or 0 for s in summaries.values()), default=0)
    return {"judge >= 3-1 in >= 4/6": len(won) >= 4, "judge >= 2/3 unseen": len(won & set(UNSEEN)) >= 2, "won": sorted(won), "seen won": sorted(won & set(SEEN)),
            "coherent views under IoU .6": coherent_low, "stretch <= 2.0": stretch <= STRETCH_MAX, "stretch <= 1.5": stretch <= STRETCH_GOOD,
            "pieces <= 700 tris": all(r["tris"] <= TRIS_MAX for r in built.values()),
            "<= 15 min": all(s["seconds"] <= 60 * MINUTES_MAX for s in summaries.values()), "units built": sorted(built)}


def last_built(summary):
    return next(r for r in reversed(summary["rounds"]) if "tris" in r and r["round"] == summary["final_round"])


# ---------------------------------------------------------------- L16-1: the rounds curve
OUT16 = ROOT / "artifacts/model-sheets/history/2026-10-30-l16-rounds"
CONTROL, OLD, FULL, ROUNDS16 = "l15-col-part-outline", "v16-r1", "v16-r9", {"v16-r3": 3, "v16-r6": 6}
CURVE = ("v16-r3", "v16-r6", FULL)
LABEL = {"v16-r3": "r3", "v16-r6": "r6", FULL: "r9"}
ORDER = [("v16-r6", "v16-r3"), (FULL, "v16-r6"), (FULL, "v16-r3"), ("v16-r3", OLD), ("v16-r3", CONTROL), ("v16-r6", CONTROL), (FULL, CONTROL)]    # (new B, older A)


def prefix_summary(summary, n):
    """The eye summary of the first n rounds of a longer run: the rounds, the calls and the seconds up to round n-1 (the base measurement included)."""
    out = copy.deepcopy(summary)
    out["rounds"] = [r for r in summary["rounds"] if r["round"] < n]
    out["llm_calls"] = sum(1 + r.get("resent", 0) for r in out["rounds"] if "llm_s" in r)
    out["resends"] = sum(r.get("resent", 0) for r in out["rounds"])
    out["seconds"] = round(summary["base"]["seconds"] + sum(r.get("llm_s", 0) + r.get("build_s", 0) + r.get("measure_s", 0) for r in out["rounds"]), 1)
    built = [r["round"] for r in out["rounds"] if "tris" in r]
    out["final_round"] = max(built) if built else None
    for k in ("vertex_hash", "outline", "stretch"):
        out.pop(k, None)
    return out


def snapshot(unit, n, dst, src=FULL):
    """DRAFT/unit/dst = the first n rounds of DRAFT/unit/src, finished by eye_stage.finish (outline, clay.glb, stretch, hash)."""
    import eye_stage
    a, b = DRAFT / unit / src, DRAFT / unit / dst
    summary = prefix_summary(read(a / "eye/summary.json"), n)
    eye = b / "eye"
    eye.mkdir(parents=True, exist_ok=True)
    eye_stage.seed(DRAFT / unit / summary["from"], b)
    for f in ("input.glb", "bones.json"):
        shutil.copy(a / "eye" / f, eye / f)
    for r in range(n):
        if (a / f"eye/round-{r}").exists():
            shutil.copytree(a / f"eye/round-{r}", eye / f"round-{r}", ignore=shutil.ignore_patterns("views", "sil", "board-*.png", "pairwise*"), dirs_exist_ok=True)
    final = summary["final_round"]
    eye_stage.finish(summary, eye / f"round-{final}/model.glb", eye / "input.glb", b, eye)
    print(unit, dst, "rounds", final + 1, "seconds", summary["seconds"], "hash", summary["vertex_hash"])


def judge_runs(unit, a, b):
    """B (newer) x A through review_pair, one vote at a time, kept as DRAFT/unit/B/pairwise-A.json (a result already there is reused)."""
    import review_pair
    done = DRAFT / unit / b / f"pairwise-{a}.json"
    if not done.exists():
        result = judge_runs_dir(DRAFT / unit / a, DRAFT / unit / b, unit, DRAFT / unit / b / f"pairwise-{a}")
        (DRAFT / unit / b / "pairwise.json").rename(done)
        print(unit, b, "x", a, review_pair.line(result))
    return read(done)


def stop_curve(unit, run=FULL):
    """The judge rule replayed on a full run: round r x r-1 (kept in the round's dir) until STALLS stalled rounds in a row. -> stop-curve.json."""
    import eye_stage
    base = DRAFT / unit / run
    summary = read(base / "eye/summary.json")
    built = {r["round"]: r for r in summary["rounds"] if "tris" in r}
    rows, stalls, stop = [], 0, None
    for r in range(1, max(built) + 1):
        f = base / f"eye/round-{r}/pairwise.json"
        t0 = time.monotonic()
        res = read(f) or eye_stage.judge_round(lambda x, y: judge_runs_dir(x, y, unit), base / "eye", r, DRAFT / unit / "v15-r1")
        stalled = eye_stage.stalled(built[r - 1]["parts"], built[r]["parts"], res)
        stalls = stalls + 1 if stalled else 0
        rows.append({"round": r, "stalled": stalled, "parts": built[r]["parts"], "judge": {a: res[a]["winner"] for a in AXES}, "judge_s": res.get("seconds", round(time.monotonic() - t0, 1))})
        if stalls >= eye_stage.STALLS:
            stop = r
            break
    spent = lambda rs: sum(built[x].get("llm_s", 0) + built[x].get("build_s", 0) + built[x].get("measure_s", 0) for x in rs)    # noqa: E731
    kept = [x for x in built if stop is None or x <= stop]
    out = {"unit": unit, "stop_after_round": stop, "rounds_built": len(kept), "rounds_full": len(built), "seconds_full": round(spent(built), 1), "seconds_stopped": round(spent(kept), 1),
           "judge_seconds": round(sum(x["judge_s"] for x in rows), 1), "judged": rows, "parts_at_stop": built[max(kept)]["parts"], "parts_full": built[max(built)]["parts"]}
    (base / "stop-curve.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "judged"}))
    return out


AXES = ("sheet", "artist", "wc3", "form")


def judge_runs_dir(a, b, unit, work=None):
    """review_pair.compare on two run dirs, one vote at a time (the stop curve judges round dirs); the seconds are kept in the result."""
    import review_pair
    t0 = time.monotonic()
    saved = review_pair.concurrent.futures.ThreadPoolExecutor
    review_pair.concurrent.futures.ThreadPoolExecutor = lambda n: saved(1)
    try:
        result = review_pair.compare(a, b, unit, "mass", "session:opus", work=work)
    finally:
        review_pair.concurrent.futures.ThreadPoolExecutor = saved
    result["seconds"] = round(time.monotonic() - t0, 1)
    (b / "pairwise.json").write_text(json.dumps(result, indent=2))
    return result


def b_wins(result, axes=("sheet", "artist"), votes=3):
    """True when B (the newer run) wins every axis in `axes` with at least `votes` votes."""
    return all(result[a]["winner"] == "B" and result[a]["B"] >= votes for a in axes)


def form_holds(result):
    """The form axis does not get worse: B has at least 2 of the 4 votes."""
    return result["form"]["B"] >= 2


def curve_acceptance(results, seconds):
    """The brief's acceptance of N rounds over 3. results: {(B, A): {unit: pairwise}}; seconds: {run: {unit: seconds}}. {run: {check: value}}."""
    out = {}
    for new, old in (("v16-r6", "v16-r3"), (FULL, "v16-r3")):
        res = results.get((new, old), {})
        cost = sum(seconds[new].values()) / max(sum(seconds[old].values()), 1)
        won, form = [u for u, r in res.items() if b_wins(r)], [u for u, r in res.items() if form_holds(r)]
        out[LABEL[new]] = {"judge sheet+artist >= 3-1 in >= 4/6": len(won) >= 4, "won": sorted(won), "form >= 2-2 in >= 4/6": len(form) >= 4, "form kept": sorted(form),
                           "cost <= 2x r3": cost <= 2, "cost x r3": round(cost, 2), "accepted": len(won) >= 4 and len(form) >= 4 and cost <= 2}
    return out


def run_seconds(unit, run):
    s = read(DRAFT / unit / run / "eye/summary.json")
    return s.get("seconds") or 0


def tally_text(result):
    return " ".join(f"{a[0]}{result[a]['B']}-{result[a]['A']}" for a in AXES) if result else "–"


def round_lines(units, noise):
    lines = ["| unit | run | round | cum s | calls | tris | pieces | parts | IoU f/l/b/top/bot/rts | spill | bare | falls > 2σ vs v15 | asked stop |", "|---" * 13 + "|"]
    for u in units:
        for run in (OLD, FULL):
            s = read(DRAFT / u / run / "eye/summary.json")
            cum = s["base"]["seconds"] if s else 0
            for r in (s or {}).get("rounds", []):
                cum += r.get("llm_s", 0) + r.get("build_s", 0) + r.get("measure_s", 0)
                if "tris" not in r:
                    lines.append(f"| {u} | {run} | {r['round']} | {v(cum, 0)} |" + " – |" * 8 + f" {r.get('stop', r.get('error', ''))} |")
                    continue
                lines.append(f"| {u} | {run} | {r['round']} | {v(cum, 0)} | {1 + r['resent']} | {r['tris']} | {r['pieces']} | {r['parts'][0]}/{r['parts'][1]} | {per_view(r['views'], 'iou')} "
                             f"| {per_view(r['views'], 'spill')} | {per_view(r['views'], 'bare')} | {','.join(falls(u, r['views'], s['base']['views'], noise)) or '–'} | |")
    return lines


def pair_lines(units):
    lines = ["", "| unit | pair (B x A) | " + " | ".join(AXES) + " (winner B votes-A votes) |", "|---" * 6 + "|"]
    for b, a in ORDER:
        for u in units:
            res = read(DRAFT / u / b / f"pairwise-{a}.json")
            if res:
                lines.append(f"| {u} | {LABEL.get(b, b)} x {LABEL.get(a, a)} | " + " | ".join(f"{res[x]['winner']} {res[x]['B']}-{res[x]['A']}" for x in AXES) + " |")
    return lines


def stop_lines(units):
    lines = ["", "| unit | stop after round | rounds built | seconds full | seconds stopped | judge seconds | parts at stop | parts full |", "|---" * 8 + "|"]
    for u in units:
        c = read(DRAFT / u / FULL / "stop-curve.json")
        if c:
            lines.append(f"| {u} | {c['stop_after_round']} | {c['rounds_built']}/{c['rounds_full']} | {c['seconds_full']} | {c['seconds_stopped']} | {c['judge_seconds']} | {c['parts_at_stop']} | {c['parts_full']} |")
    return lines


def curve_table(units, noise):
    """The rounds x unit table of v16-r9 and v16-r1 (cumulative seconds, calls count resends), the judge pairs and the stop curve."""
    return "\n".join(round_lines(units, noise) + pair_lines(units) + stop_lines(units))


def final_cells(unit, run, cache):
    """{view: PIL cell} of the final (outlined) model.glb of a run, rendered with the cameras its last measurement chose (the control: the v15 silhouette's)."""
    import eye_stage
    d = DRAFT / unit / run
    if run == CONTROL:
        cams = eye_stage.tilt_text(read(d / "silhouette.json"))
    else:
        s = read(d / "eye/summary.json")
        cams = read(d / f"eye/round-{s['final_round']}/eval.json").get("tilts", "")
    out = cache / unit / run
    if not (out / "model-front.png").exists():
        out.mkdir(parents=True, exist_ok=True)
        subprocess.run(["nice", "-n", "10", "blender", "-b", "-P", str(pathlib.Path(__file__).resolve().parent / "render_unit.py"), "--", str(d / "model.glb"), str(out), f"tilt={cams}"],
                       capture_output=True)
    return {view: eye_stage.cell(out / f"model-{FILES.get(view, view)}.png") for view in VIEWS}


def curve_sheet(unit, cache):
    cols = [("control (v15 + outline)", CONTROL)] + [(LABEL[r], r) for r in CURVE]
    cw, ch = MC.CELL
    img = Image.new("RGB", (cw * (len(cols) + 1), 20 + (ch + 20) * len(VIEWS)), MC.BG)
    d = ImageDraw.Draw(img)
    with tempfile.TemporaryDirectory() as tmp:
        concept = MC.concept_cells(MC.load_run(DRAFT / unit / FULL), pathlib.Path(tmp))
    for x, label in enumerate(["concept"] + [c[0] for c in cols]):
        d.text((x * cw + 6, 4), label, fill=(255, 255, 255))
    cells = [final_cells(unit, run, cache) for _, run in cols]
    for y, view in enumerate(VIEWS):
        top = 20 + y * (ch + 20)
        if view in concept:
            img.paste(concept[view], (0, top))
        for x, cs in enumerate(cells):
            img.paste(cs[view], ((x + 1) * cw, top))
        d.text((4, top + ch), view, fill=(255, 255, 255))
    return img


def curve_images(units, cache):
    for u in units:
        im = curve_sheet(u, cache)
        im.resize((im.width // 2, im.height // 2), Image.LANCZOS).save(OUT16 / f"{u}.png")
        print("wrote", OUT16 / f"{u}.png")


def curve_accept(units):
    results = {(b, a): {u: read(DRAFT / u / b / f"pairwise-{a}.json") for u in units if read(DRAFT / u / b / f"pairwise-{a}.json")} for b, a in ORDER}
    print(json.dumps(curve_acceptance(results, {r: {u: run_seconds(u, r) for u in units} for r in ("v16-r3", "v16-r6", FULL)}), indent=1))


def write_table(units):
    text = curve_table(units, read(AM.NOISE))
    (OUT16 / "table.md").write_text(text + "\n")
    print(text)


def l16(what, units):
    OUT16.mkdir(parents=True, exist_ok=True)
    cache = pathlib.Path(os.environ.get("L16_VIEWS", OUT16 / ".views"))
    {"snapshot": lambda: [snapshot(u, n, dst) for u in units for dst, n in ROUNDS16.items()],
     "judge": lambda: [judge_runs(u, a, b) for b, a in ORDER for u in units],
     "stop": lambda: [stop_curve(u) for u in units],
     "table": lambda: write_table(units),
     "images": lambda: curve_images(units, cache),
     "accept": lambda: curve_accept(units)}[what]()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--units", default=",".join(AM.UNITS))
    ap.add_argument("--table", action="store_true")
    ap.add_argument("--images", action="store_true")
    ap.add_argument("--judge", action="store_true")
    ap.add_argument("--accept", action="store_true")
    ap.add_argument("--l16", choices=("snapshot", "judge", "stop", "table", "images", "accept"), help="the rounds curve of L16-1 (see the module doc)")
    args = ap.parse_args(argv)
    units = args.units.split(",")
    if args.l16:
        return l16(args.l16, units)
    OUT.mkdir(parents=True, exist_ok=True)
    if args.judge:
        with tempfile.TemporaryDirectory() as tmp:
            for u in units:
                judge(u, DRAFT / u / "v15-r1", "v15")
                if (DRAFT / u / "l14-fix/model.glb").exists():
                    judge(u, fix_run(u, tmp), "fix")
    if args.table:
        text = table(units, read(AM.NOISE))
        (OUT / "table.md").write_text(text + "\n")
        print(text)
    if args.images:
        for u in units:
            im = sheet(u)
            im.resize((im.width // 2, im.height // 2), Image.LANCZOS).save(OUT / f"{u}.png")
            print("wrote", OUT / f"{u}.png")
    if args.accept:
        res = {u: read(DRAFT / u / "v16-r1/pairwise-v15.json") for u in units}
        print(json.dumps(acceptance(units, {u: r for u, r in res.items() if r}, {u: read(DRAFT / u / "v16-r1/eye/summary.json") for u in units}), indent=1))


if __name__ == "__main__":
    main()
