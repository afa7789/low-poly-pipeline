"""Regression battery of the SDF body on every existing spec (PIPELINE 28.L10-8), no LLM.

    python3.14 tools/blender/sdf_batch.py [--units n005,n00H] [--body sdf,union] [--jobs 2] [--grid 96] [--no-anim] [--collect-only] [--compare DIR]

For each unit the latest runs/draft/<id>/v1{2,1,0}-r1/spec.json is built with `spec_pipeline.py --shape-only --no-repair
--body <b>` (cameras pinned to the origin run's silhouette.json) into runs/draft/<id>/l10-batch-<b>[g<grid>]/, measured
(silhouette.json, attach.json, mesh_lint, anim_check.py) and summarized as markdown + l10-batch.json. The parsing and the
table are pure functions (tests/tools/blender/test_sdf_batch.py); only `build`, `collect` and `main` touch disk or processes."""
import argparse
import concurrent.futures as cf
import json
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/blender"))
DRAFT = ROOT / "artifacts/model-sheets/runs/draft"
VERSIONS = ("v12-r1", "v11-r1", "v10-r1")
EXTRA = {"n01I": "v2-hard-r2", "n01N": "v2-hard-r2"}      # units with no v1x run: their last hard-sheet spec
VIEWS = ("front", "left", "back", "top", "bottom", "rts")
RIGS = {"biped": "biped", "spider": "spider", "spider_high": "spider", "quadruped": "quadruped", "wyrm": "wyrm", "drake": "drake"}
BUILD_MEAN, BUILD_MAX, SLIVER_MAX, ND_GAIN, IOU_SLACK = 15.0, 30.0, 5.0, 10.0, 0.01     # the L10-8 acceptance


def rig_group(rig):
    return RIGS.get(rig, "outros")


def discover(root=DRAFT, units=None):
    """[{unit, run, spec, rig}] of the latest spec of each unit (sorted by id); `units`: only those ids."""
    out = []
    for d in sorted(p for p in pathlib.Path(root).iterdir() if p.is_dir()):
        if units and d.name not in units:
            continue
        run = next((v for v in (*VERSIONS, EXTRA.get(d.name)) if v and (d / v / "spec.json").exists()), None)
        if run:
            spec = d / run / "spec.json"
            out.append({"unit": d.name, "run": run, "spec": spec, "rig": json.loads(spec.read_text()).get("rig", "biped")})
    return [u for u in out if u["rig"] != "building"]


def tilts_arg(sil):
    """silhouette.py --tilts value of the cameras a silhouette.json chose: {'bottom': 20, 'rts': [55, -60]} -> 'bottom:20,rts:55/-60'."""
    return ",".join(f"{v}:{'/'.join(map(str, t)) if isinstance(t, (list, tuple)) else t}" for v, t in sorted((sil.get("tilt") or {}).items()))


def run_name(body, grid=0):
    return f"l10-batch-{body}" + (f"g{grid}" if grid else "")


def command(u, body, grid=0, tilts=""):
    cmd = [sys.executable, str(ROOT / "tools/blender/spec_pipeline.py"), "--id", u["unit"], "--race", "Human", "--name", u["unit"],
           "--kind", "mass", "--rig", u["rig"], "--spec", str(u["spec"]), "--shape-only", "--no-repair", "--no-diagnose",
           "--run", run_name(body, grid), "--body", body]
    return cmd + (["--sdf-grid", str(grid)] if grid and body == "sdf" else []) + (["--tilts", tilts] if tilts else [])


def cause_of(text):
    """One line for a failed build: the last exception line of the traceback and the innermost frame; else the last output line."""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    tb = [i for i, ln in enumerate(lines) if ln.startswith("Traceback")]
    if not tb:
        return lines[-1][:200] if lines else "no output"
    frames = [ln for ln in lines[tb[-1]:] if ln.startswith('File "')]
    where = frames[-1].replace(str(ROOT) + "/", "") if frames else ""
    return f"{lines[-1][:160]} [{where[:100]}]"


def mean(d):
    return round(sum(d.values()) / len(d), 3) if d else None


def stat(lint, key):
    return ((lint.get("sdf_dev") or {}).get("pct_h") or {}).get(key)


def make_row(u, body, sil, attach, lint, raw, anim, plates, failing, total_s, grid=0):
    """One measurements row (all inputs already parsed) -> flat dict. `plates` = [(spec row, owned triangles, buried)] per 'plate' part."""
    un, ap = attach.get("union", {}), sil.get("approved", {})
    gates = sil.get("gates", {})
    return {"unit": u["unit"], "rig": u["rig"], "group": rig_group(u["rig"]), "spec": f"{u['run']}", "body": body, "grid": grid or 96, "ok": True,
            "build_s": un.get("seconds"), "total_s": round(total_s, 1), "tris": lint["tris"], "sliver": lint["sliver_pct"],
            "sliver_raw": raw["sliver_pct"] if raw else None, "nd": lint["normal_diff"]["mean"], "dev_p95": stat(lint, "p95"),
            "dev_max": stat(lint, "max"), "euler": lint["euler"], "comp": lint["components_body"],
            "iou": [ap.get(v) for v in VIEWS], "unc": mean(sil.get("uncovered", {})), "spill": mean(sil.get("spill", {})),
            "sil_fail": [v for v in VIEWS if ap.get(v) is not None and v in gates and ap[v] < gates[v]], "lint_fail": failing,
            "thin": len(un.get("inflated", [])) + len(un.get("kept", [])), "inflated": len(un.get("inflated", [])),
            "plates": len(plates), "plates_zero": sum(1 for _, n, b in plates if n == 0 and not b),
            "plates_zero_rows": [i for i, n, _ in plates if n == 0], "plates_buried": [i for i, n, b in plates if n == 0 and b],
            "specks": un.get("specks", 0),
            "nd_raw": raw["normal_diff"]["mean"] if raw else None,
            "stretch": {k: v["p99.5_stretch"] for k, v in (anim or {}).items() if v}}


def fail_row(u, body, cause, total_s, grid=0):
    return {"unit": u["unit"], "rig": u["rig"], "group": rig_group(u["rig"]), "spec": u["run"], "body": body, "grid": grid or 96,
            "ok": False, "cause": cause, "total_s": round(total_s, 1)}


def f(v, nd=1):
    return "–" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))


def verdict(r):
    bad = [*r["lint_fail"], *(f"sil:{v}" for v in r["sil_fail"])]
    return "PASS" if not bad else "FAIL " + ", ".join(bad)


def table(rows):
    """Markdown: one line per (unit, body)."""
    head = ("| unit | rig | body | build s | total s | tris | sliver % (raw→final) | nd | sdf_dev p95 / max % H | euler | comp | "
            "IoU f/l/b/top/bot/rts | unc / spill | thin (<2 vox) | plates (0 tris, buried) | walk p99.5 | gates |\n" + "|---" * 17 + "|")
    out = [head]
    for r in sorted(rows, key=lambda r: (r["unit"], r["body"] != "sdf")):
        if not r["ok"]:
            out.append(f"| {r['unit']} | {r['rig']} | {r['body']} | FAIL | {r['total_s']} | {r['cause']} |" + " |" * 11)
            continue
        iou = " / ".join(f(x, 3).lstrip("0") for x in r["iou"])
        out.append(f"| {r['unit']} | {r['rig']} | {r['body']} | {f(r['build_s'])} | {r['total_s']} | {r['tris']} | {f(r['sliver_raw'])} → {f(r['sliver'])} "
                   f"| {f(r['nd'])} | {f(r['dev_p95'], 2)} / {f(r['dev_max'], 2)} | {r['euler']} | {r['comp']} | {iou} | {f(r['unc'], 3)} / {f(r['spill'], 3)} "
                   f"| {r['thin']} ({r['inflated']} inflated) | {r['plates']} ({r['plates_zero']}, {len(r['plates_buried'])}) | {f(r['stretch'].get('walk'), 2)} | {verdict(r)} |")
    return "\n".join(out)


def pairs(rows):
    """{unit: (sdf row, union row)} of the units with both built."""
    by = {(r["unit"], r["body"]): r for r in rows if r["ok"] and r["grid"] == 96}
    return {u: (by[u, "sdf"], by[u, "union"]) for u, b in by if b == "sdf" and (u, "union") in by}


def delta_table(rows):
    """Markdown: sdf − union per unit (IoU per view and mean, slivers, nd, comp, walk stretch)."""
    out = ["| unit | rig | ΔIoU f/l/b/top/bot/rts | Δ mean | Δ sliver % | Δ nd ° | comp (union → sdf) | walk p99.5 (union → sdf) |", "|---" * 8 + "|"]
    for u, (s, un) in pairs(rows).items():
        d = [None if a is None or b is None else a - b for a, b in zip(s["iou"], un["iou"])]
        ok = [x for x in d if x is not None]
        out.append(f"| {u} | {s['rig']} | {' / '.join(f(x, 3) for x in d)} | {f(sum(ok) / len(ok) if ok else None, 3)} | {f(s['sliver'] - un['sliver'])} "
                   f"| {f(s['nd'] - un['nd'])} | {un['comp']} → {s['comp']} | {f(un['stretch'].get('walk'), 2)} → {f(s['stretch'].get('walk'), 2)} |")
    return "\n".join(out)


def rig_checks(g, s, un):
    """Failed acceptance lines of one unit (L10-8): by rig group, sdf row `s` against the union row `un` (None: no union)."""
    out = []
    if g in ("biped", "quadruped") and s["sliver"] >= SLIVER_MAX:
        out.append(f"sliver {s['sliver']} % >= {SLIVER_MAX}")
    if g == "biped" and un and s["nd"] > un["nd"] - ND_GAIN:
        out.append(f"nd {s['nd']} > union {un['nd']} - {ND_GAIN:g}")
    if g == "spider" and s["comp"] != 1:
        out.append(f"components_body {s['comp']} != 1")
    if g == "spider" and un and (s["iou"][5] or 0) < (un["iou"][5] or 0):
        out.append(f"rts {s['iou'][5]} < union {un['iou'][5]}")
    if g in ("wyrm", "drake") and s["plates_zero"]:
        out.append(f"{s['plates_zero']} of {s['plates']} plates with 0 tris")
    if g in ("wyrm", "drake") and un:
        out += [f"{VIEWS[i]} {s['iou'][i]} < union {un['iou'][i]} - {IOU_SLACK:g}" for i in (1, 3) if s["iou"][i] < un["iou"][i] - IOU_SLACK]
    return out


def acceptance(rows):
    """[(unit, rig, [reasons])] for each sdf row (a failed build is one reason); empty reasons = in the acceptance. Also
    ('*', 'all', reasons) with the build-time rule (mean <= 15 s, max <= 30 s)."""
    sdf = [r for r in rows if r["body"] == "sdf" and r["grid"] == 96]
    union = {r["unit"]: r for r in rows if r["body"] == "union" and r["ok"] and r["grid"] == 96}
    out = [(r["unit"], r["rig"], [f"build failed: {r['cause']}"] if not r["ok"] else rig_checks(r["group"], r, union.get(r["unit"]))) for r in sdf]
    times = [r["build_s"] for r in sdf if r["ok"] and r["build_s"] is not None]
    bad = ([f"mean build {sum(times) / len(times):.1f} s > {BUILD_MEAN:g}"] if times and sum(times) / len(times) > BUILD_MEAN else []) + \
          ([f"max build {max(times):.1f} s > {BUILD_MAX:g}"] if times and max(times) > BUILD_MAX else [])
    return out + [("*", "all", bad)]


def acceptance_table(rows):
    lines = ["| unit | rig | acceptance |", "|---|---|---|"]
    lines += [f"| {u} | {rig} | {'; '.join(why) if why else 'ok'} |" for u, rig, why in acceptance(rows)]
    n = [w for u, _, w in acceptance(rows) if u != "*"]
    return "\n".join(lines) + f"\n\n{sum(1 for w in n if not w)}/{len(n)} units in the acceptance."


COMPARE_VIEWS = ("front", "left", "back", "top", "bottom", "rts")


def compare_png(unit, out, size=256):
    """<out>/<unit>.png: the clay renders of the union run (top row) and the sdf run (bottom), one column per view."""
    from PIL import Image
    runs = [DRAFT / unit / run_name(b) / "views" / unit for b in ("union", "sdf")]
    sheet = Image.new("RGB", (size * len(COMPARE_VIEWS), size * 2), "white")
    for r, views in enumerate(runs):
        for c, v in enumerate(COMPARE_VIEWS):
            if (views / f"clay-{v}.png").exists():
                sheet.paste(Image.open(views / f"clay-{v}.png").convert("RGB").resize((size, size)), (c * size, r * size))
    sheet.save(pathlib.Path(out) / f"{unit}.png", optimize=True)


def read_json(path):
    return json.loads(path.read_text()) if path.exists() else {}


def buried(field, k):
    """True when part `k` of `field` is inside the others: at 27 points of its box every other part's d is under -1 voxel
    (the plate cannot show, so 0 triangles are right)."""
    import itertools
    import numpy as np
    lo, hi = np.array(field.parts[k]["lo"]), np.array(field.parts[k]["hi"])
    pts = np.array([lo + (hi - lo) * np.array(c) for c in itertools.product((0, .5, 1), repeat=3)])
    dm = field.distances(pts)
    return len(dm) > 1 and bool((np.delete(dm, k, 0).min(0) < -field.voxel).all())


def plate_tris(run, field_path):
    """[(spec row, triangles owned by the nearest part, buried)] per 'plate' part of the body's field in `run`/clay.glb;
    [] without the field."""
    import mesh_lint as ML
    import sdf_body as SB
    if not field_path.exists():
        return []
    field = SB.load(field_path)
    pos, _, _, tri = ML.geometry(*ML.read_glb(run / "clay.glb"))
    owner = field.ownership(ML.to_blender(pos[tri].mean(1)))[0]
    return [(p["i"], int((owner == n).sum()), buried(field, n)) for n, p in enumerate(field.parts) if p["kind"] == "plate"]


def anim(run, skip):
    """anim_check.py's {clip: {p99.5_stretch}} of the run's clay.glb (cached in anim.json); {} when skipped."""
    out = run / "anim.json"
    if skip:
        return read_json(out)
    subprocess.run(["blender", "-b", "-P", str(ROOT / "tools/blender/anim_check.py"), "--", str(run / "clay.glb"), str(out)], capture_output=True)
    return read_json(out)


def collect(u, body, grid, total_s, skip_anim):
    """The row of one finished run (or a fail row: no clay.glb / no silhouette.json, cause from batch.log)."""
    import mesh_lint as ML
    run = DRAFT / u["unit"] / run_name(body, grid)
    if not (run / "clay.glb").exists() or not (run / "silhouette.json").exists():
        log = run / "batch.log"
        return fail_row(u, body, cause_of(log.read_text() if log.exists() else ""), total_s, grid)
    lint = ML.lint(run / "clay.glb", sdf=True)
    raw = ML.lint(run / "clay-raw.glb", sdf=True) if (run / "clay-raw.glb").exists() else None
    field = DRAFT / u["unit"] / run_name("sdf", grid if body == "sdf" else 0) / "clay.sdf.json"
    return make_row(u, body, read_json(run / "silhouette.json"), read_json(run / "attach.json"), lint, raw, anim(run, skip_anim),
                    plate_tris(run, field), ML.failing(lint, False), total_s, grid)


def build(u, body, grid):
    """Runs spec_pipeline for one (unit, body); the output goes to <run>/batch.log. Returns the wall seconds. The l10-batch-* dir
    of an earlier battery is removed first (it is this tool's own output): the pipeline reuses a run dir's fit/ and spec, so
    a rebuild over it is not a rebuild from the origin spec (n00H, n010, n01N moved 0.03-0.2 IoU between two runs)."""
    run = DRAFT / u["unit"] / run_name(body, grid)
    shutil.rmtree(run, ignore_errors=True)
    run.mkdir(parents=True)
    t0 = time.perf_counter()
    done = subprocess.run(command(u, body, grid, tilts_arg(read_json(u["spec"].parent / "silhouette.json"))), capture_output=True, text=True, cwd=ROOT)
    (run / "batch.log").write_text(done.stdout + done.stderr)
    total = time.perf_counter() - t0
    (run / "batch.json").write_text(json.dumps({"total_s": round(total, 1), "returncode": done.returncode}))
    return total


def one(u, body, args):
    grid = args.grid if body == "sdf" else 0
    total = read_json(DRAFT / u["unit"] / run_name(body, grid) / "batch.json").get("total_s", 0.0) if args.collect_only else build(u, body, grid)
    row = collect(u, body, grid, total, args.no_anim)
    print(f"{u['unit']} {body}: {'ok' if row['ok'] else 'FAIL ' + row['cause']} ({row['total_s']} s)", file=sys.stderr, flush=True)
    return row


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--units", default="", help="comma-separated ids (default: every unit with a spec)")
    ap.add_argument("--body", default="sdf,union", help="comma-separated: sdf, union (control), join")
    ap.add_argument("--jobs", type=int, default=2, help="parallel spec_pipeline processes (2 max on this machine)")
    ap.add_argument("--grid", type=int, default=0, help="sdf voxels on the longest side (0 = build_unit default, 96); runs go to l10-batch-sdfg<N>")
    ap.add_argument("--no-anim", action="store_true", help="skip anim_check.py (reuse a previous anim.json)")
    ap.add_argument("--collect-only", action="store_true", help="do not build, measure the runs already on disk")
    ap.add_argument("--compare", type=pathlib.Path, help="also write <dir>/<unit>.png: union (top) | sdf (bottom) clay views")
    ap.add_argument("--json", type=pathlib.Path, default=DRAFT / "l10-batch.json")
    args = ap.parse_args(argv)
    units = discover(units=[x for x in args.units.split(",") if x])
    bodies = args.body.split(",")
    with cf.ThreadPoolExecutor(args.jobs) as pool:
        rows = list(pool.map(lambda t: one(*t, args), [(u, b) for u in units for b in bodies]))
    for u in units if args.compare else []:
        args.compare.mkdir(parents=True, exist_ok=True)
        compare_png(u["unit"], args.compare)
    args.json.write_text(json.dumps({"rows": rows, "acceptance": acceptance(rows) if "sdf" in bodies else []}, indent=1))
    print(table(rows) + "\n\n" + delta_table(rows) + ("\n\n" + acceptance_table(rows) if "sdf" in bodies else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
