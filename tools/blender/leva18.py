#!/usr/bin/env python3
"""Leva 18 battery (PIPELINE 36.L18): fused palette -> union by bone -> painted atlas with box charts, over the eye stage's final DSL.

    python3.14 tools/blender/leva18.py run   --id n005 [--from v18-r0] [--tag v18-up] [--fuse 12] [--union bone] [--charts box] [--outline hull]
    python3.14 tools/blender/leva18.py sheet <unit> [--runs v16-r3,v18-r0,v18-up]        # history/2026-10-31-l18/<unit>.png
    python3.14 tools/blender/leva18.py table [--units ...] [--tag v18-up]                 # history/2026-10-31-l18/table.md
    python3.14 tools/blender/leva18.py timing [--units ...] [--runs v18-r0,v18-up]        # median wall clock per stage over the units

`run`: runs/draft/<id>/<tag> = a copy of <from> whose last DSL is fused (eye_fuse), rebuilt as unions by bone (eye_union through eye_skin),
painted (eye_paint, charts) and outlined; measured by the eye stage's gate; leva18.json and timing.json beside the model."""
import argparse
import json
import pathlib
import shutil
import statistics
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ablation_matrix as AM  # noqa: E402
import eye_fuse  # noqa: E402

ROOT = AM.ROOT
DRAFT = ROOT / "artifacts/model-sheets/runs/draft"
HISTORY = ROOT / "artifacts/model-sheets/history/2026-10-31-l18"
STAGES = ("fuse", "union", "measure", "paint", "outline", "stretch")


def run_unit(unit, src_name, tag, fuse=12, union="bone", charts="box", contour="hull", reduce="qem", log=print):
    """The battery step of one unit; the summary (also <tag>/leva18.json), timing in <tag>/timing.json."""
    import eye_paint
    import eye_skin
    import eye_stage
    import eye_union
    import mesh_lint
    import outline
    src, out = DRAFT / unit / src_name, DRAFT / unit / tag
    if out.exists():
        raise SystemExit(f"{out} exists: rename it -invalid<ts> first")
    shutil.copytree(src, out, ignore=shutil.ignore_patterns("pairwise*"))
    _, dsl = eye_skin.final_round(src)
    timing, summary = {}, {"unit": unit, "from": src_name, "fuse": fuse, "union": union, "reduce": reduce, "charts": charts, "outline": contour}
    t0 = time.perf_counter()
    fused, summary["fused"] = eye_fuse.fuse(dsl, fuse) if fuse else (dsl, {"before": len(set(p["mat"] for p in dsl["pieces"])), "after": None})
    (out / "eye/fused.dsl.json").write_text(json.dumps(fused, indent=1))
    timing["fuse"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    summary["skin"] = eye_skin.apply_stage(out / "eye/input.glb", fused, out, eye_union.technique_of(union, reduce) if union != "off" else "off", always=True)
    timing[f"union_{reduce}"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    spec = json.loads((src / "spec.json").read_text()) if (src / "spec.json").exists() else {}
    ev = eye_stage.measure(out / "model.glb", out / "eye/l18", eye_stage.REFS / unit / "sheet.jpg", spec.get("rig") or "biped")   # before the paint: the parts gate reads material colours
    summary.update(parts=ev["parts"], views=ev["views"], disaster=ev["disaster"])
    timing["measure"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    summary["paint"] = eye_paint.apply(out / "model.glb", charts) if charts != "off" else {}
    timing["paint"] = time.perf_counter() - t0
    shutil.copy(out / "model.glb", out / "model-body.glb")          # the painted body without the hull: render_wire draws its triangulation
    t0 = time.perf_counter()
    summary["hull"] = contour in ("hull", "both") and outline.apply(out / "model.glb", hull=True)
    timing["outline"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    summary["stretch"] = eye_stage.stretch_of(out / "model.glb", out / "eye/l18-anim.json")
    timing["stretch"] = time.perf_counter() - t0
    lint = mesh_lint.lint(out / "model.glb")
    summary.update(file_tris=lint["tris"], components_body=lint["components_body"], nonmanifold=lint["nonmanifold_edges"])
    total = sum(timing.values())
    (out / "timing.json").write_text(json.dumps({"unit": unit, "total_s": round(total, 1), "stages": {k: {"s": round(v, 2), "n": 1, "pct": round(100 * v / total, 1)} for k, v in timing.items()}}, indent=1))
    (out / "leva18.json").write_text(json.dumps(summary, indent=1))
    log(f"{unit} {tag}: mats {summary['fused']['before']} -> {summary['fused']['after']}, body comps {summary['skin'].get('body_components')}, "
        f"tris {summary['skin'].get('tris')}, islands {summary['paint'].get('islands')} median texels {summary['paint'].get('texels_per_island_median')}, parts {ev['parts']}, {total:.0f}s")
    return summary


# ---------------------------------------------------------------- the images
def wire(unit, run):
    """{view: png} of render_wire.py (the triangulation drawn on the clay) for a run, cached in the run's wire/ dir."""
    import subprocess
    out = DRAFT / unit / run / "wire"
    glb = DRAFT / unit / run / ("model-body.glb" if (DRAFT / unit / run / "model-body.glb").exists() else "model.glb")   # no hull over the wire
    if not all((out / f"wire-{v}.png").exists() for v in ("front", "left", "rts")):
        out.mkdir(parents=True, exist_ok=True)
        subprocess.run(["nice", "-n", "10", "blender", "-b", "-P", str(ROOT / "tools/blender/render_wire.py"), "--", str(glb), str(out)],
                       capture_output=True, text=True)
    return {v: out / f"wire-{'rts' if v == 'wc3' else v}.png" for v in ("front", "left", "back", "top", "bottom", "wc3")}


def sheet(unit, runs=("v16-r3", "v18-qem", "v18-cvt"), wires=("v18-qem", "v18-cvt")):
    """history/2026-10-31-l18/<unit>.png: concept | runs... | Hive | wire of each v18 run, a row per view and one row of atlases."""
    import eye_stage
    import hive_sheet as H
    import make_compare as MC
    import review_pair
    from PIL import Image, ImageDraw
    name = H.PAIRS.get(unit)
    cols = [("concept", None)] + [(r, H.shoot(DRAFT / unit / r / "model.glb", H.HIVE / "renders/ours" / f"{unit}-{r}", review_pair.run_tilt(DRAFT / unit / r)))
                                  for r in runs if (DRAFT / unit / r / "model.glb").exists()]
    cols.append((f"Hive {name}", {v: H.HIVE / "renders/views" / name / f"{name}-{v}.png" for v in H.VIEWS}) if name else ("no Hive pair", {}))
    cols += [(f"wire {r}", wire(unit, r)) for r in wires if (DRAFT / unit / r / "model.glb").exists()]
    with tempfile.TemporaryDirectory() as tmp:
        panels = review_pair.sheet_panels(unit, "mass", pathlib.Path(tmp))
        cw, ch = MC.CELL
        img = Image.new("RGB", (cw * len(cols), 20 + (ch + 20) * (len(H.VIEWS) + 1)), MC.BG)
        draw = ImageDraw.Draw(img)
        for x, (label, shots) in enumerate(cols):
            draw.text((x * cw + 6, 4), label, fill=(255, 255, 255))
            for y, view in enumerate(H.VIEWS):
                src = panels.get("rts" if view == "wc3" else view) if shots is None else shots.get(view)
                img.paste(eye_stage.cell(src) if src and pathlib.Path(src).exists() else MC.empty_cell("-"), (x * cw, 20 + y * (ch + 20)))
            atlas = DRAFT / unit / label / "atlas.png"
            if atlas.exists():
                img.paste(Image.open(atlas).convert("RGB").resize((ch, ch), Image.NEAREST), (x * cw, 20 + len(H.VIEWS) * (ch + 20)))
    out = HISTORY / f"{unit}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        raise SystemExit(f"{out} exists: history sheets are never overwritten")
    img.resize((img.width // 2, img.height // 2), Image.LANCZOS).save(out)
    return out


# ---------------------------------------------------------------- tables
def read(path):
    return json.loads(path.read_text()) if path.exists() else {}


def table(units, tag="v18-qem", base="v16-r3"):
    rows = ["| un. | mats before -> after | body comps | tris (union) | islands | texels/island median (min) | ink | parts k/n base -> L18 | IoU front base -> L18 | stretch | s |", "|---" * 11 + "|"]
    for u in units:
        s = read(DRAFT / u / tag / "leva18.json")
        if not s:
            rows.append(f"| {u} | no run |" + " |" * 9)
            continue
        b = read(DRAFT / u / base / "eye/summary.json")
        bl = next((r for r in reversed(b.get("rounds", [])) if "tris" in r), {})
        st = max((c.get("p99.5_stretch", 0) for c in (s.get("stretch") or {}).values() if c), default=None)
        pt = s.get("paint", {})
        rows.append(f"| {u} | {s['fused']['before']} -> {s['fused']['after']} | {s['skin'].get('body_components')} | {s['skin'].get('tris')} | {pt.get('islands')} | "
                    f"{pt.get('texels_per_island_median')} ({pt.get('texels_per_island_min')}) | {pt.get('ink')} | {'/'.join(map(str, bl.get('parts', '?')))} -> {'/'.join(map(str, s['parts']))} | "
                    f"{bl.get('views', {}).get('front', {}).get('iou', '?')} -> {s['views'].get('front', {}).get('iou')} | {st} | {read(DRAFT / u / tag / 'timing.json').get('total_s')} |")
    return "\n".join(rows)


def timing_rows(units, runs):
    """{run: {stage: (median s, median pct)}} and the median total, from timing.json of every unit."""
    out = {}
    for run in runs:
        docs = [read(DRAFT / u / run / "timing.json") for u in units]
        docs = [d for d in docs if d]
        if not docs:
            continue
        stages = sorted({k for d in docs for k in d["stages"]})
        out[run] = {"total_s": statistics.median(d["total_s"] for d in docs), "units": len(docs), "stages": {
            k: {"s": round(statistics.median(d["stages"].get(k, {}).get("s", 0) for d in docs), 1), "pct": round(statistics.median(d["stages"].get(k, {}).get("pct") or 0 for d in docs), 1),
                "n": round(statistics.median(d["stages"].get(k, {}).get("n", 0) for d in docs), 1)} for k in stages}}
    return out


def timing_table(units, runs):
    doc = timing_rows(units, runs)
    rows = []
    for run, d in doc.items():
        rows += [f"**{run}** ({d['units']} units, median total {d['total_s']:.0f} s)", "", "| stage | median s | median calls | % of total |", "|---|---|---|---|"]
        rows += [f"| {k} | {v['s']} | {v['n']} | {v['pct']} |" for k, v in d["stages"].items()] + [""]
    return "\n".join(rows)


def judge(unit, a, b, votes, model="session:opus"):
    """review_pair.compare(a, b) with `votes` votes (half swapped), one at a time; kept as <b>/pairwise<votes>-<a>.json with the wall clock."""
    import review_pair
    saved = review_pair.concurrent.futures.ThreadPoolExecutor
    review_pair.concurrent.futures.ThreadPoolExecutor = lambda n: saved(1)
    t0 = time.perf_counter()
    try:
        result = review_pair.compare(DRAFT / unit / a, DRAFT / unit / b, unit, "mass", model, votes=votes, work=DRAFT / unit / b / f"pairwise-{a}",
                                     out=DRAFT / unit / b / f"pairwise{votes}-{a}.json")     # a work dir per A: review_pair.shoot caches A's renders by file name
    finally:
        review_pair.concurrent.futures.ThreadPoolExecutor = saved
    result["seconds"] = round(time.perf_counter() - t0, 1)
    (DRAFT / unit / b / f"pairwise{votes}-{a}.json").write_text(json.dumps(result, indent=2))
    print(unit, b, "x", a, review_pair.line(result), f"{result['seconds']} s")
    return result


def judge_table(units, pairs, votes):
    rows = [f"| un. | {' | '.join(f'{b} x {a}: sheet / artist / wc3 / form' for a, b in pairs)} |", "|---" * (1 + len(pairs)) + "|"]
    for u in units:
        cells = []
        for a, b in pairs:
            r = read(DRAFT / u / b / f"pairwise{votes}-{a}.json")
            cells.append(" / ".join(f"{r[ax]['winner']} {max(r[ax]['A'], r[ax]['B'])}-{min(r[ax]['A'], r[ax]['B'])}" for ax in ("sheet", "artist", "wc3", "form")) if r else "–")
        rows.append(f"| {u} | {' | '.join(cells)} |")
    return "\n".join(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=("run", "sheet", "table", "timing", "judge", "judge-table"))
    ap.add_argument("--a", default="v16-r3")
    ap.add_argument("--b", default="v18-qem")
    ap.add_argument("--votes", type=int, default=4)
    ap.add_argument("--pairs", default="v16-r3:v18-qem,v16-r3:v18-cvt,v18-qem:v18-cvt")
    ap.add_argument("unit", nargs="?")
    ap.add_argument("--id")
    ap.add_argument("--from", dest="src", default="v18-r0")
    ap.add_argument("--tag", default="v18-qem")
    ap.add_argument("--fuse", type=int, default=12)
    ap.add_argument("--union", choices=("off", "material", "bone", "group"), default="bone")
    ap.add_argument("--charts", choices=("off", "grow", "box"), default="box")
    ap.add_argument("--outline", choices=("hull", "ink", "both", "off"), default="hull")
    ap.add_argument("--reduce", choices=("qem", "cvt"), default="qem")
    ap.add_argument("--units", default=",".join(AM.UNITS))
    ap.add_argument("--runs", default="v16-r3,v18-qem,v18-cvt")
    args = ap.parse_args(argv)
    units = args.units.split(",")
    if args.cmd == "run":
        run_unit(args.id, args.src, args.tag, args.fuse, args.union, args.charts, args.outline, args.reduce)
    elif args.cmd == "sheet":
        print(sheet(args.unit, args.runs.split(",")))
    elif args.cmd == "table":
        text = "\n\n".join(f"**{t}**\n\n" + table(units, t) for t in args.runs.split(",") if t != "v16-r3")
        HISTORY.mkdir(parents=True, exist_ok=True)
        (HISTORY / "table.md").write_text(text + "\n")
        print(text)
    elif args.cmd == "judge":
        for u in units:
            judge(u, args.a, args.b, args.votes)
    elif args.cmd == "judge-table":
        text = judge_table(units, [tuple(p.split(":")) for p in args.pairs.split(",")], args.votes)
        HISTORY.mkdir(parents=True, exist_ok=True)
        (HISTORY / f"judge{args.votes}.md").write_text(text + "\n")
        print(text)
    else:
        print(timing_table(units, args.runs.split(",")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
