"""Ablation matrix of every opt-in of the shape and colour pipeline on the v13 specs (PIPELINE 29.L11-7), no LLM.

    python3.14 tools/blender/ablation_matrix.py [--variants base,fit-grad,k-hard+fit-grad] [--units n005,hfoo] [--jobs 2]
                                                [--collect-only] [--list] [--report]

A variant is a name -> flags of spec_pipeline.py, module globals (CF_OVERRIDES) and build_unit arguments (CF_BUILD_ARGS), see
VARIANTS; `a+b` is the combination of two. For each unit the v13-r1 spec is rebuilt with `--shape-only --no-repair --no-diagnose
--deterministic --body sdf` (noise 0, L11-2), cameras pinned to the v13 run's silhouette.json, into runs/draft/<id>/l11-mx-<name>/
(colour variants drop --shape-only: stage 2 runs on the units whose stage 1 passes). Rows are measured (silhouette.json,
mesh_lint) and summarized against `base` into analysis/2026-10-29-l11-matrix.{csv,md}. The parsing, the aggregation and the
tables are pure functions (tests/tools/blender/test_ablation_matrix.py); only `build`, `collect` and `main` touch disk or processes."""
import argparse
import concurrent.futures as cf
import csv
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/blender"))
DRAFT = ROOT / "artifacts/model-sheets/runs/draft"
ANALYSIS = ROOT / "artifacts/model-sheets/analysis"
DELTAS = ANALYSIS / "2026-10-29-l11-1-deltas"            # <id>/diagnosis.json of L11-1 (no LLM here: reused)
UNITS = ("n005", "n00U", "hfoo", "n017", "n02X")
ORIGIN = "v13-r1"
VIEWS = ("front", "left", "back", "top", "bottom", "rts")
DROP, GAIN, WIN_UNITS = 0.01, 0.005, 3         # a view falling more than DROP; a mean gain of at least GAIN; in WIN_UNITS of 5
FLAT = 0.005                                   # |Δ mean| under this, nothing else moved: "neutral"
TAU_ANNEAL = [4, 2, 1, 0.5, 0.5]


def groups(flags):
    """['--atlas', 'shared', '--fit-grad'] -> [('--atlas', 'shared'), ('--fit-grad',)]: a flag with its values."""
    out = []
    for w in flags:
        if w.startswith("--") or not out:
            out.append((w,))
        else:
            out[-1] += (w,)
    return out


def var(flags=(), over=None, build="", colour=False, units=None, needs=None, note=""):
    """One variant: spec_pipeline flags (a `{deltas}` word becomes the unit's L11-1 diagnosis.json), module overrides
    {"module.NAME": value}, build_unit arguments, colour (stage 2 runs), units (None = all), needs (a file of the unit that must exist)."""
    return {"flags": groups(flags), "over": dict(over or {}), "build": build, "colour": colour, "units": units, "needs": needs, "note": note}


VARIANTS = {
    "base": var(note="the pipeline as it stands: fit, sdf body k=base, deform, fit-verts 8 it/stage"),
    # fit (fit_spec / fit_grad)
    "fit-grad": var(["--fit-grad"], note="26.L8-7: Adam on the soft silhouette"),
    "fit-stages": var(["--fit-stages"], note="22.L4-3: trunk, limbs, profiles one after the other"),
    "fit-edges": var(["--fit-edges"], note="21.F7: part outlines onto the hard sheet's inner edges"),
    "fit-parts": var(["--fit-parts"], needs="parts.json", note="23.L5-4: each part inside its 2D mask"),
    "fit-depth": var(["--depth"], needs="parts.json", note="23.L5-4b: Depth Anything start + occlusion order"),
    "constraints": var(["--constraints", "{deltas}"], needs="deltas", note="29.L11-3 via B: L11-1 deltas as fit limits"),
    "leg-spill": var(over={"fit_spec.LEG_SPILL_W": 3.0, "fit_spec.LEG_SPILL": 0.05}, units=("n00U", "n017"), note="25.L7-3: rts leg spill in the fit"),
    "leg-grow": var(over={"fit_spec.LEG_GROW": True}, units=("n00U",), note="21.F3: spider legs may grow to the sheet's leg_w"),
    # body (sdf_body / build_unit)
    "body-union": var(["--body", "union"], note="control: boolean union + decimate (24.L6-4)"),
    "k-class": var(["--sdf-k-mode", "class"], note="29.L11-5"),
    "k-hard": var(["--sdf-k-mode", "hard"], note="29.L11-5"),
    "thin-keep": var(build="sdf_thin=keep", note="28.L10-7: parts under 2 voxels kept as their own plates"),
    "thin-off": var(build="sdf_thin=off", note="28.L10-7: parts under 2 voxels may vanish"),
    "grid-128": var(["--sdf-grid", "128"], note="28.L10-7: 128 voxels"),
    # deform / verts
    "no-deform": var(["--no-deform"], note="control: Sketch2Mesh deformation off"),
    "no-verts": var(["--no-fit-verts"], note="control: vertex optimisation off"),
    "align": var(["--align"], note="24.L6-12: sharp edges onto the hard sheet (negative)"),
    "props-own": var(over={"deform_to_sheet.PROPS_OWN_MASK": True}, note="25.L7-5: a prop pulled only toward its own mask (negative)"),
    "verts-fd": var(over={"optimize_verts.GRAD": "fd"}, note="26.L8-2: finite-difference gradient instead of autograd"),
    "verts-tau": var(over={"optimize_verts.TAU_SCHEDULE": TAU_ANNEAL}, note="26.L8-3: tau 4 -> 0.5 annealed"),
    "verts-asym": var(over={"optimize_verts.LOSS": "asym"}, note="26.L8-5: red/green asymmetric loss"),
    "verts-dihedral": var(over={"optimize_verts.LAMBDA.dihedral": 30.0}, note="26.L8-4: dihedral regulariser, lambda 30"),
    "verts-gamma": var(over={"optimize_verts.DIST": "gamma_inv"}, note="26.L8-3: gamma_inv raster distribution"),
    "verts-uniform": var(over={"optimize_verts.DIST": "uniform"}, note="26.L8-3: uniform raster distribution"),
    "iters-15": var(over={"optimize_verts.DETERMINISTIC_ITERS": 15}, note="29.L11-4: 15 iterations per stage instead of 8 (where does it match the clock?)"),
    "verts-yager": var(over={"optimize_verts.AGG": "yager2"}, note="26.L8-3: yager2 aggregation"),
    # silhouette framing
    "flip-side": var(["--flip-side"], note="29.L11-0: shift-tolerant side picks the mirror"),
    "frame-body": var(["--frame", "body"], note="29.L11-0b: frame by the body without props"),
    # colour (stage 2, on the units whose stage 1 passes)
    "c-base": var(colour=True, note="stage 2 as it stands: cel, own compact atlas, merged materials"),
    "c-legacy": var(["--atlas", "legacy"], colour=True, note="27.T1: 256 px cells"),
    "c-shared": var(["--atlas", "shared"], colour=True, note="27.T3: the race's 128 px shared atlas"),
    "c-split": var(["--materials", "split"], colour=True, note="27.T5: one material per slot"),
    "c-luma": var(["--fit-luma"], colour=True, note="26.L8-8: per-slot tones fitted to the sheet's luma"),
    "c-ramp": var(["--ramp"], colour=True, note="cel ramps as wide as the sheet zone"),
    "c-snap": var(["--atlas", "shared"], build="palette_snap", colour=True, note="27.T7: shared atlas + palette snap"),
    "c-painted": var(["--texture", "painted"], colour=True, note="the older painted texture"),
}
BASE = {"base": "base", "c-base": "c-base"}      # which row a variant is compared with: colour variants against c-base


def merge(a, b, name=""):
    """The combination of two variants. Flags join (a repeated one once); a flag or a module override must agree or be
    absent in one of them; units intersect."""
    over = dict(a["over"])
    for k, v in b["over"].items():
        if k in over and over[k] != v:
            raise ValueError(f"{name}: {k} is {over[k]!r} in one part and {v!r} in the other")
        over[k] = v
    flags = list(a["flags"])
    for g in b["flags"]:
        clash = [h for h in flags if h[0] == g[0] and h != g]
        if clash:
            raise ValueError(f"{name}: {g[0]} is {clash[0][1:]} in one part and {g[1:]} in the other")
        if g not in flags:
            flags.append(g)
    units = a["units"] if b["units"] is None else b["units"] if a["units"] is None else tuple(u for u in a["units"] if u in b["units"])
    return var([w for g in flags for w in g], over, f"{a['build']} {b['build']}".strip(), a["colour"] or b["colour"], units, a["needs"] or b["needs"],
               f"{a['note']} + {b['note']}".strip(" +"))


def resolve(name, table=None):
    """The variant called `name` ('a+b+c' combines): ValueError for an unknown name. The base of a combination is the first name's."""
    table = table or VARIANTS
    parts = name.split("+")
    missing = [p for p in parts if p not in table]
    if missing:
        raise ValueError(f"unknown variant {', '.join(missing)} (known: {', '.join(table)})")
    out = table[parts[0]]
    for p in parts[1:]:
        out = merge(out, table[p], name)
    return out if len(parts) > 1 else dict(out)


def run_name(name):
    return f"l11-mx-{name}"


def base_of(name):
    """The variant a row is compared with: `c-base` for the colour ones, else `base`."""
    return "c-base" if resolve(name)["colour"] else "base"


def applies(v, unit, refs):
    """True when variant `v` has anything to do for `unit`: it lists the unit and the file it needs exists (refs/<id>/parts.json,
    or the unit's L11-1 diagnosis.json)."""
    if v["units"] is not None and unit not in v["units"]:
        return False
    need = v["needs"]
    return need is None or ((DELTAS / unit / "diagnosis.json" if need == "deltas" else refs / unit / need)).exists()


def tilts_arg(sil):
    """silhouette.py --tilts value of the cameras a silhouette.json chose: {'bottom': 20, 'rts': [55, -60]} -> 'bottom:20,rts:55/-60'."""
    return ",".join(f"{v}:{'/'.join(map(str, t)) if isinstance(t, (list, tuple)) else t}" for v, t in sorted((sil.get("tilt") or {}).items()))


def command(unit, name, v, tilts):
    """The spec_pipeline.py command line of one (unit, variant); a `{deltas}` word is the unit's L11-1 diagnosis.json."""
    flags = [str(DELTAS / unit / "diagnosis.json") if w == "{deltas}" else w for g in v["flags"] for w in g]
    return [sys.executable, str(ROOT / "tools/blender/spec_pipeline.py"), "--id", unit, "--race", "Human", "--name", unit, "--kind", "mass",
            "--rig", json.loads((DRAFT / unit / ORIGIN / "spec.json").read_text()).get("rig", "biped"), "--spec", str(DRAFT / unit / ORIGIN / "spec.json"), "--no-repair", "--no-diagnose", "--deterministic", "--run", run_name(name),
            *([] if "--body" in flags else ["--body", "sdf"]), *([] if v["colour"] else ["--shape-only"]),
            *(["--tilts", tilts] if tilts else []), *flags]


def environment(v):
    """The environment of one build: SOFT_SIL_THREADS, plus CF_OVERRIDES / CF_BUILD_ARGS when the variant has any."""
    env = {**os.environ, "SOFT_SIL_THREADS": os.environ.get("SOFT_SIL_THREADS", "4")}
    if v["over"]:
        env["CF_OVERRIDES"] = json.dumps(v["over"])
    if v["build"]:
        env["CF_BUILD_ARGS"] = v["build"]
    return env


# ------------------------------------------------------------------------------------------------ measurement rows
def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 4) if xs else None


def make_row(unit, name, sil, lint, times, zones=None, model=None):
    """One flat measurements row (inputs already parsed). `lint` = mesh_lint of clay.glb (or None), `times` = {total_s, build_s,
    verts_s}, `zones` = stage 2's per-view zone report, `model` = {atlas_kb, prims, images, materials, ...} of model.glb."""
    ap, gates = sil.get("approved", {}), sil.get("gates", {})
    iou = [ap.get(v) for v in VIEWS]
    row = {"unit": unit, "variant": name, "ok": True, "iou": iou, "mean": mean(iou),
           "sil_fail": [v for v in VIEWS if ap.get(v) is not None and v in gates and ap[v] < gates[v]],
           "tris": lint and lint["tris"], "sliver": lint and lint["sliver_pct"], "nd": lint and lint["normal_diff"]["mean"],
           "euler": lint and lint["euler"], "comp": lint and lint["components_body"],
           "dev_p95": lint and ((lint.get("sdf_dev") or {}).get("pct_h") or {}).get("p95"),
           "hausdorff": lint and lint.get("hausdorff_sdf"), "form": sil.get("form"), **times}
    if zones is not None:
        z = {v: r for v, r in zones.items() if isinstance(r, dict)}
        row.update(zones_mean=mean([r.get("mean") for r in z.values()]), luma_l1=mean([r.get("luma_l1") for r in z.values()]),
                   zone_fail=sorted(v for v, r in z.items() if r.get("fails")), **(model or {}))
    return row


def fail_row(unit, name, cause, total_s=0.0):
    return {"unit": unit, "variant": name, "ok": False, "cause": cause, "total_s": round(total_s, 1)}


def skip_row(unit, name, why):
    return {"unit": unit, "variant": name, "ok": False, "skipped": True, "cause": why}


def dv(a, b):
    """a - b, None when either is missing."""
    return None if a is None or b is None else round(a - b, 4)


def vs_base(row, base):
    """Deltas of one row against the base row of its unit: per view, mean, views falling more than DROP, slivers, nd, seconds."""
    if not (row["ok"] and base and base["ok"]):
        return None
    d = [dv(a, b) for a, b in zip(row["iou"], base["iou"])]
    return {"iou": d, "mean": dv(row["mean"], base["mean"]), "drops": [v for v, x in zip(VIEWS, d) if x is not None and x < -DROP],
            "sliver": dv(row["sliver"], base["sliver"]), "nd": dv(row["nd"], base["nd"]), "total_s": dv(row["total_s"], base["total_s"]),
            "luma_l1": dv(row.get("luma_l1"), base.get("luma_l1")), "atlas_kb": dv(row.get("atlas_kb"), base.get("atlas_kb"))}


def unit_pass(d):
    """A unit counts for a flag when the mean rises by GAIN and no view falls more than DROP."""
    return bool(d) and d["mean"] is not None and d["mean"] >= GAIN and not d["drops"]


def summarize(rows):
    """{variant: {n, wins, mean, drops, hurt, sliver, nd, seconds, units}}: each variant against the base row of its unit.
    wins = units with mean gain >= GAIN and no falling view; hurt = units whose mean fell by GAIN or more; drops = views falling > DROP
    summed over units; mean/sliver/nd/seconds = averages of the per-unit deltas."""
    by = {(r["unit"], r["variant"]): r for r in rows}
    out = {}
    for name in dict.fromkeys(r["variant"] for r in rows):
        if name in ("base", "c-base"):
            continue
        b = base_of(name)
        ds = {u: vs_base(by[u, name], by.get((u, b))) for u in UNITS if (u, name) in by}
        got = {u: d for u, d in ds.items() if d}
        out[name] = {"n": len(got), "wins": sum(unit_pass(d) for d in got.values()),
                     "mean": mean([d["mean"] for d in got.values()]), "drops": sum(len(d["drops"]) for d in got.values()),
                     "hurt": sum(1 for d in got.values() if d["mean"] is not None and d["mean"] <= -GAIN),
                     "sliver": mean([d["sliver"] for d in got.values()]), "nd": mean([d["nd"] for d in got.values()]),
                     "seconds": mean([d["total_s"] for d in got.values()]), "units": got,
                     "worst": min(((x, v) for d in got.values() for v, x in zip(VIEWS, d["iou"]) if x is not None), default=None)}
    return out


def verdict(s):
    """One line per variant: 'default' (it wins on WIN_UNITS of 5), 'neutral', or 'opt-in (loses ...)' with the worst view fall."""
    if s["n"] == 0:
        return "not measured"
    if s["wins"] >= WIN_UNITS:
        return "default (proposal)"
    if s["mean"] is not None and abs(s["mean"]) < FLAT and not s["drops"] and abs(s["sliver"] or 0) < 1 and abs(s["nd"] or 0) < 1:
        return "neutral"
    loses = f"{s['worst'][1]} {s['worst'][0]:+.3f}" if s["worst"] and s["worst"][0] < -DROP else f"mean {s['mean']:+.4f}"
    return f"opt-in (loses {loses}; {s['drops']} view(s) > {DROP})" if (s["mean"] or 0) >= 0 else f"no (loses {loses}; {s['hurt']}/{s['n']} units worse)"


def winners(summary, min_wins=WIN_UNITS):
    """The variants (not combinations) that win on at least `min_wins` units, in the table's order."""
    return [n for n, s in summary.items() if "+" not in n and not n.startswith(("no-", "body-", "c-", "grid")) and s["wins"] >= min_wins]


# ------------------------------------------------------------------------------------------------ tables
def f(v, nd=3):
    return "–" if v is None else f"{v:.{nd}f}" if isinstance(v, float) else str(v)


def sgn(v, nd=3):
    return "–" if v is None else f"{v:+.{nd}f}"


def table(rows):
    """Markdown: one line per (variant, unit) with IoU per view, mean, form and timing; deltas against the unit's base below it."""
    head = ("| variant | unit | IoU f/l/b/top/bot/rts | mean | Δ mean | falls > .01 | slivers % | nd ° | euler | comp | tris | sdf p95 % H | hausdorff % H | s |\n"
            + "|---" * 14 + "|")
    by = {(r["unit"], r["variant"]): r for r in rows}
    out = [head]
    for r in sorted(rows, key=lambda r: (list(VARIANTS).index(r["variant"].split("+")[0]) if r["variant"].split("+")[0] in VARIANTS else 99, r["variant"], r["unit"])):
        if not r["ok"]:
            out.append(f"| {r['variant']} | {r['unit']} | {'skipped: ' if r.get('skipped') else 'FAIL: '}{r['cause']} |" + " |" * 11)
            continue
        d = vs_base(r, by.get((r["unit"], base_of(r["variant"]))))
        out.append(f"| {r['variant']} | {r['unit']} | {' / '.join(f(x).lstrip('0') for x in r['iou'])} | {f(r['mean'], 4)} | {sgn(d and d['mean'], 4)} "
                   f"| {', '.join(d['drops']) if d and d['drops'] else '–'} | {f(r['sliver'], 1)} | {f(r['nd'], 1)} | {f(r['euler'])} | {f(r['comp'])} | {f(r['tris'])} "
                   f"| {f(r['dev_p95'], 2)} | {f(r['hausdorff'], 2)} | {f(r['total_s'], 0)} |")
    return "\n".join(out)


def summary_table(summary):
    """Markdown: one line per variant against base (Δ mean IoU, units won, views falling, units hurt, slivers, nd, seconds, decision)."""
    out = ["| variant | units | Δ mean IoU | units won (≥ +.005, no fall) | views falling > .01 | units worse | Δ slivers % | Δ nd ° | Δ seconds | worst view | decision |",
           "|---" * 11 + "|"]
    for n, s in summary.items():
        worst = f"{s['worst'][1]} {s['worst'][0]:+.3f}" if s["worst"] else "–"
        out.append(f"| {n} | {s['n']} | {sgn(s['mean'], 4)} | {s['wins']}/{s['n']} | {s['drops']} | {s['hurt']} | {sgn(s['sliver'], 1)} | {sgn(s['nd'], 1)} "
                   f"| {sgn(s['seconds'], 0)} | {worst} | {verdict(s)} |")
    return "\n".join(out)


def colour_table(rows):
    """Markdown: the stage 2 variants, one line per (variant, unit): atlas KB, primitives, luma L1, zone mean, failing zone views."""
    cols = [r for r in rows if r["ok"] and "atlas_kb" in r]
    out = ["| variant | unit | atlas KB | image | prims | materials | luma L1 | zones mean | zone gate | uv out of range |", "|---" * 10 + "|"]
    out += [f"| {r['variant']} | {r['unit']} | {f(r['atlas_kb'], 1)} | {r.get('image', '–')} | {f(r['prims'])} | {f(r['materials'])} | {f(r['luma_l1'])} "
            f"| {f(r['zones_mean'])} | {'FAIL ' + ','.join(r['zone_fail']) if r['zone_fail'] else 'ok'} | {f(r['uv_out'])} |"
            for r in sorted(cols, key=lambda r: (r["variant"], r["unit"]))]
    return "\n".join(out)


COLUMNS = ("variant", "unit", "ok", *(f"iou_{v}" for v in VIEWS), "mean", "sil_fail", "tris", "sliver", "nd", "euler", "comp", "dev_p95", "hausdorff",
           "form", "total_s", "build_s", "verts_s", "fit_s", "zones_mean", "luma_l1", "atlas_kb", "prims", "materials", "cause")


def csv_text(rows):
    """The CSV of all rows (one line per (variant, unit); failed rows keep their cause)."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    for r in rows:
        flat = {**r, **{f"iou_{v}": (r.get("iou") or [None] * 6)[i] for i, v in enumerate(VIEWS)}, "sil_fail": " ".join(r.get("sil_fail", []))}
        w.writerow(["" if flat.get(c) is None else flat[c] for c in COLUMNS])
    return buf.getvalue()


# ------------------------------------------------------------------------------------------------ disk and processes
def read_json(path):
    return json.loads(path.read_text()) if path.exists() else {}


def times_of(run, total_s):
    """{total_s, build_s, verts_s, fit_s}: wall seconds of the whole run, of stage 1's build (review.md `- t_build`), of the fit-verts
    (clay.verts.json) and the fit (derived: what is left of the run once the build and the generation are taken off)."""
    review = (run / "review.md").read_text() if (run / "review.md").exists() else ""
    stage = {k: float(v) for k, v in re.findall(r"^- t_(\w+): ([\d.]+) s", review, re.M)}
    build = stage.get("build")
    return {"total_s": round(total_s, 1), "build_s": build and round(build, 1), "verts_s": read_json(run / "clay.verts.json").get("seconds"),
            "fit_s": build and round(max(total_s - build - stage.get("gen", 0.0), 0.0), 1)}


def model_of(run):
    """The stage 2 numbers of the run's model.glb: atlas KB, image size, primitives, materials, uv out of range; {} without it."""
    import mesh_lint as ML
    glb = run / "model.glb"
    if not glb.exists():
        return {}
    doc, _ = ML.read_glb(glb)
    lint = ML.lint(glb)
    return {"atlas_kb": lint["atlas_kb"], "image": "x".join(map(str, lint["image_size"] or ())) or "–", "images": lint["images"],
            "prims": sum(len(m["primitives"]) for m in doc["meshes"]), "materials": lint["materials"], "uv_out": lint["uv_out_of_range"]}


def collect(unit, name, v, total_s):
    """The row of one finished run (or a fail row: no clay.glb / silhouette.json, cause from batch.log)."""
    import mesh_lint as ML
    run = DRAFT / unit / run_name(name)
    if not (run / "clay.glb").exists() or not (run / "silhouette.json").exists():
        log = run / "batch.log"
        lines = [ln.strip() for ln in (log.read_text() if log.exists() else "").splitlines() if ln.strip()]
        return fail_row(unit, name, lines[-1][:200] if lines else "no output", total_s)
    lint = ML.lint(run / "clay.glb", sdf=(run / "clay.sdf.json").exists())
    zones = read_json(run / "stage2" / "colour.json").get("zones") if v["colour"] else None
    return make_row(unit, name, read_json(run / "silhouette.json"), lint, times_of(run, total_s), zones if v["colour"] else None,
                    model_of(run) if v["colour"] else None)


def lock(path):
    """Create `path` exclusively with this pid; False when a live process holds it (never two chains on one run)."""
    for _ in range(2):
        try:
            os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            path.write_text(str(os.getpid()))
            return True
        except FileExistsError:
            try:
                os.kill(int(path.read_text() or 0), 0)
                return False
            except (ProcessLookupError, ValueError):
                path.unlink(missing_ok=True)
            except PermissionError:
                return False
    return False


def build(unit, name, v):
    """Runs spec_pipeline for one (unit, variant) into runs/draft/<unit>/l11-mx-<name>/; output to batch.log. An earlier run without a
    batch.json (killed) is renamed -invalid, never deleted. Returns the wall seconds."""
    run = DRAFT / unit / run_name(name)
    if run.exists():
        run.rename(run.with_name(f"{run.name}-invalid{int(time.time())}"))
    run.mkdir(parents=True)
    tilts = tilts_arg(read_json(DRAFT / unit / ORIGIN / "silhouette.json"))
    t0 = time.perf_counter()
    done = subprocess.run(command(unit, name, v, tilts), capture_output=True, text=True, cwd=ROOT, env=environment(v))
    total = time.perf_counter() - t0
    (run / "batch.log").write_text(done.stdout + done.stderr)
    (run / "batch.json").write_text(json.dumps({"total_s": round(total, 1), "returncode": done.returncode, "variant": name,
                                                "over": v["over"], "build": v["build"], "flags": v["flags"]}))
    return total


def one(unit, name, args):
    v = resolve(name)
    if not applies(v, unit, ROOT / "artifacts/model-sheets/refs"):
        return skip_row(unit, name, "not applicable (unit not listed or its input file missing)")
    run = DRAFT / unit / run_name(name)
    done = read_json(run / "batch.json")
    if args.collect_only or (done.get("returncode") == 0 and not args.rebuild):
        total = done.get("total_s", 0.0)
    else:
        guard = DRAFT / unit / f"{run_name(name)}.lock"
        if not lock(guard):
            return fail_row(unit, name, "locked by another process")
        try:
            total = build(unit, name, v)
        finally:
            guard.unlink(missing_ok=True)
    row = collect(unit, name, v, total)
    print(f"{unit} {name}: {'ok mean ' + str(row['mean']) if row['ok'] else 'FAIL ' + row['cause']} ({row['total_s']} s)", file=sys.stderr, flush=True)
    return row


def disk_rows():
    """The rows of every variant that has a run on disk (a skip row where it does not apply), so the tables cover all the invocations."""
    names = sorted({d.name[len("l11-mx-"):] for d in DRAFT.glob("*/l11-mx-*") if d.is_dir() and "-invalid" not in d.name},
                   key=lambda n: (list(VARIANTS).index(n) if n in VARIANTS else 99, n))
    refs, rows = ROOT / "artifacts/model-sheets/refs", []
    for n in names:
        v = resolve(n)
        for u in UNITS:
            if not applies(v, u, refs):
                rows.append(skip_row(u, n, "not applicable (unit not listed or its input file missing)"))
            elif (DRAFT / u / run_name(n) / "batch.json").exists():
                rows.append(collect(u, n, v, read_json(DRAFT / u / run_name(n) / "batch.json").get("total_s", 0.0)))
    return rows


def report(rows):
    """The markdown of analysis/2026-10-29-l11-matrix.md."""
    summary = summarize(rows)
    shape = [r for r in rows if not resolve(r["variant"])["colour"]]
    colour = [r for r in rows if resolve(r["variant"])["colour"]]
    return ("# L11-7 ablation matrix (PIPELINE 29.L11-7)\n\nEach variant rebuilds the v13 spec of the 5 units with `--deterministic` (noise 0), "
            "cameras of v13 fixed; Δ against `base` (colour: against `c-base`).\n\n## Summary by variant\n\n" + summary_table(summary)
            + "\n\n## Variant x unit (shape)\n\n" + table(shape) + ("\n\n## Stage 2 (colour)\n\n" + colour_table(colour) if colour else "") + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--variants", default="", help="comma-separated names (a+b combines); default: every shape variant")
    ap.add_argument("--units", default="", help="comma-separated ids (default: the 5 of the v13 battery)")
    ap.add_argument("--jobs", type=int, default=2, help="parallel spec_pipeline processes (2 max on this machine)")
    ap.add_argument("--collect-only", action="store_true", help="do not build, measure the runs already on disk")
    ap.add_argument("--rebuild", action="store_true", help="rebuild runs that already have a batch.json (the old one is renamed -invalid)")
    ap.add_argument("--list", action="store_true", help="print the variants and exit")
    ap.add_argument("--out", type=pathlib.Path, default=ANALYSIS / "2026-10-29-l11-matrix", help="writes <out>.csv and <out>.md")
    ap.add_argument("--copy", type=pathlib.Path, default=None, help="also copy the csv and md to this directory (ablation-matrix-2026-10-29.*)")
    args = ap.parse_args(argv)
    if args.list:
        print("\n".join(f"{n:16} {v['note']}" for n, v in VARIANTS.items()))
        return 0
    names = [x for x in args.variants.split(",") if x] or [n for n, v in VARIANTS.items() if not v["colour"]]
    for n in names:
        resolve(n)
    units = [u for u in (args.units.split(",") if args.units else UNITS) if u]
    tasks = [(u, n) for n in names for u in units]
    with cf.ThreadPoolExecutor(args.jobs) as pool:
        list(pool.map(lambda t: one(*t, args), tasks))
    rows = disk_rows()
    args.out.with_suffix(".csv").write_text(csv_text(rows))
    args.out.with_suffix(".md").write_text(report(rows))
    for ext in (".csv", ".md") if args.copy else ():
        shutil.copy(args.out.with_suffix(ext), args.copy / f"ablation-matrix-2026-10-29{ext}")
    print(summary_table(summarize(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
