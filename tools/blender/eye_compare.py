#!/usr/bin/env python3
"""L15-5 battery report (PIPELINE 33.L15-5): the runs v16-r1 (eye stage) of the 6 units against v15-r1 and the hand fix of L14-3.

    python3.14 tools/blender/eye_compare.py [--units n005,hfoo] [--table] [--images] [--judge] [--accept]

--table   per unit and round: seconds, model calls, triangles, parts k/n, IoU / spill / bare per view (the guards), the views whose IoU falls
          more than 2 sigma (noise-l12.json) below the v15 model measured by the same gate, components, stretch      -> history/2026-10-30-l15-eye/table.md
--images  per unit and view a row: concept | v15 | round 0 | round 1 | ... | hand fix (L14-3, the 3 units that have one)  -> history/2026-10-30-l15-eye/<id>.png
--judge   review_pair.py (session:opus, one vote at a time: the machine is shared) v16 x v15 on the 6 units and v16 x l14-fix on the 3 that
          have it; the results are kept in runs/draft/<id>/v16-r1/pairwise-v15.json and pairwise-fix.json
--accept  the brief's acceptance (judge form + artist >= 3-1 for v16 in >= 4/6 and >= 2/3 of the unseen units; IoU >= .6 in every coherent
          view; stretch <= 2.0; pieces <= 700 triangles; <= 15 min per unit). Pure helpers (falls, judged, acceptance) are tested without disk."""
import argparse
import concurrent.futures
import json
import pathlib
import shutil
import sys
import tempfile

from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ablation_matrix as AM  # noqa: E402
import make_compare as MC  # noqa: E402
import mesh_lint  # noqa: E402
import noise as NZ  # noqa: E402

ROOT = AM.ROOT
DRAFT = ROOT / "artifacts/model-sheets/runs/draft"
OUT = ROOT / "artifacts/model-sheets/history/2026-10-30-l15-eye"
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
    s = read(DRAFT / unit / "v16-r1/eye/summary.json")
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
        s = read(DRAFT / u / "v16-r1/eye/summary.json")
        if not s or s.get("final_round") is None:
            lines.append(f"| {u} | no model |" + " |" * 8)
            continue
        lint = mesh_lint.lint(DRAFT / u / "v16-r1/model.glb")
        final = next(r for r in s["rounds"] if r.get("round") == s["final_round"] and "tris" in r)
        old = read(DRAFT / u / "v15-r1/anim.json")
        lines.append(f"| {u} | {s['seconds']} | {s['llm_calls']} | {s['resends']} | {s['final_round']} | {final['tris']} | {lint['tris']} | {lint['components']} "
                     f"| {v(worst_stretch(s.get('stretch')), 2)} | {v(worst_stretch(old), 2)} |")
    return "\n".join(lines)


# ---------------------------------------------------------------- images
def concept_cells(unit, tmp):
    return MC.concept_cells(MC.load_run(DRAFT / unit / "v16-r1"), pathlib.Path(tmp))


def round_dirs(unit):
    base = DRAFT / unit / "v16-r1/eye"
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
    new = DRAFT / unit / "v16-r1"
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--units", default=",".join(AM.UNITS))
    ap.add_argument("--table", action="store_true")
    ap.add_argument("--images", action="store_true")
    ap.add_argument("--judge", action="store_true")
    ap.add_argument("--accept", action="store_true")
    args = ap.parse_args(argv)
    units = args.units.split(",")
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
