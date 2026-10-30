"""Ablation matrix of every opt-in of the shape and colour pipeline on the v13 specs (PIPELINE 29.L11-7, rerun 30.L12-10a), no LLM.

    python3.14 tools/blender/ablation_matrix.py [--variants base,fit-grad,k-hard+fit-grad] [--units n005,hfoo] [--jobs 2]
                                                [--collect-only] [--list] [--legacy DIR]

A variant is a name -> flags of spec_pipeline.py, module globals (CF_OVERRIDES), environment (CF_SPILL_W) and build_unit arguments
(CF_BUILD_ARGS), see VARIANTS; `a+b` is the combination of two. For each unit the v13-r1 spec is rebuilt with `--shape-only
--no-repair --no-diagnose --deterministic --body sdf` (noise 0, L11-2), cameras pinned to the v13 run's silhouette.json, into
runs/draft/<id>/l12-mx-<name>/ (colour variants drop --shape-only). Rows are measured (silhouette.json, mesh_lint, clay.look.json,
clay.depth.json) and summarized against `base` per variant: spill first (the gate's own numbers), then IoU, bare, contact, z_err,
planarity, crease recall, and the views that fall more than 2 sigma of noise-l12.json. The parsing, the aggregation and the tables are
pure functions (tests/tools/blender/test_ablation_matrix.py); only `build`, `collect` and `main` touch disk or processes."""
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
import noise as NZ  # noqa: E402

DRAFT = ROOT / "artifacts/model-sheets/runs/draft"
ANALYSIS = ROOT / "artifacts/model-sheets/analysis"
DELTAS = ANALYSIS / "2026-10-29-l11-1-deltas"            # <id>/diagnosis.json of L11-1 (no LLM here: reused)
NOISE = DRAFT / "noise-l12.json"
# unit -> (race, name, role) as in the v13 battery (they label the run; with --spec they do not move the shape)
UNITS = {"n005": ("Human", "Warlock Field Chemist", "area-damage caster"), "n00U": ("Nature", "Black Spider", "fast swarm unit"),
         "hfoo": ("Human", "Footman", "basic line infantry with a spear"), "n017": ("Nature", "Frost Wolf", "fast melee beast"),
         "n02X": ("Desert", "Ogre", "pipeline siege bruiser"), "n01X": ("Mech", "Iron Golem", "frontline melee construct")}
ORIGIN = "v13-r1"
PREFIX = "l12-mx-"
VIEWS = ("front", "left", "back", "top", "bottom", "rts")
SPILL_OK = 0.03          # a view whose spill is at most this counts as "clean"
SPILL_EPS = 0.002        # a mean spill change smaller than this is not a change
FLAT = 0.0005            # every delta under this: the variant moved nothing (a no-op)
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




def var(flags=(), over=None, build="", colour=False, units=None, needs=None, note="", env=None):
    """One variant: spec_pipeline flags (a `{deltas}` word becomes the unit's L11-1 diagnosis.json), module overrides
    {"module.NAME": value}, build_unit arguments, colour (stage 2 runs), units (None = all), needs (a file of the unit that must exist),
    env (environment variables of the build, e.g. CF_SPILL_W)."""
    return {"flags": groups(flags), "over": dict(over or {}), "build": build, "colour": colour, "units": units, "needs": needs, "note": note,
            "env": dict(env or {})}


VARIANTS = {
    "base": var(note="the pipeline as it stands: fit, sdf body k=base, deform, fit-verts 8 it/stage"),
    # Leva 12 opt-ins
    "spill-w3": var(env={"CF_SPILL_W": "3"}, note="30.L12-2: model outside the sheet costs 3x (fit, deform, fit-verts)"),
    "author-guard": var(["--author-guard", "revert"], note="30.L12-3: revert the author's parts that fall under the massing's (the massing is v13-r1/massing)"),
    "incoh-1": var(["--incoherent-weight", "1.0"], note="30.L12-5: an incoherent sheet view weighs as a coherent one"),
    "incoh-0": var(["--incoherent-weight", "0"], note="30.L12-5: an incoherent sheet view weighs nothing"),
    "dsl-all": var(["--dsl-repair", "all"], note="30.L12-6: every DSL repair, also the ones with no rule failing"),
    "dsl-off": var(["--dsl-repair", "off"], note="control: no DSL repair (default is on)"),
    "look-snap": var(["--look-snap", "on"], note="30.L12-9: planar snap by region, guarded by IoU/spill/bare"),
    "look-creases": var(["--look-snap", "on", "--look-creases", "on"], note="30.L12-9: snap + the sheet's drawn lines as region borders (read against base: includes the snap)"),
    "look-ink": var(["--look-ink", "on"], note="30.L12-9: ink on the atlas edges (cel)"),
    "depth-tri": var(["--depth-source", "tri"], needs="parts.json", note="30.L12-8: part z from the front x left triangulation"),
    "inscribe": var(["--inscribe", "on"], note="31.L13-5: the sdf body cut by the visual hull of the coherent views + a guarded clamp of the vertices still outside"),
    "inscribe-cut": var(["--inscribe", "cut"], note="31.L13-5: only the cut (read against base: no clamp)"),
    "noise": var(["--noise", str(NOISE)], note="30.L12-7: guards read 2 sigma from noise-l12.json"),
    # fit (fit_spec / fit_grad)
    "fit-grad": var(["--fit-grad"], note="26.L8-7: Adam on the soft silhouette"),
    "fit-stages": var(["--fit-stages"], note="22.L4-3: trunk, limbs, profiles one after the other"),
    "fit-edges": var(["--fit-edges"], note="21.F7: part outlines onto the hard sheet's inner edges"),
    "fit-fast": var(["--fit-fast"], note="19.D1: the fast fit (wide steps)"),
    "fit-parts": var(["--fit-parts"], needs="parts.json", note="23.L5-4: each part inside its 2D mask"),
    "fit-depth": var(["--depth"], needs="parts.json", note="23.L5-4b: Depth Anything start + occlusion order"),
    "constraints": var(["--constraints", "{deltas}"], needs="deltas", note="29.L11-3 via B: L11-1 deltas as fit limits"),
    "leg-spill": var(over={"fit_spec.LEG_SPILL_W": 3.0, "fit_spec.LEG_SPILL": 0.05}, units=("n00U", "n017"), note="25.L7-3: rts leg spill in the fit"),
    "leg-grow": var(over={"fit_spec.LEG_GROW": True}, units=("n00U",), note="21.F3: spider legs may grow to the sheet's leg_w"),
    # body (sdf_body / build_unit)
    "body-union": var(["--body", "union"], note="control: boolean union + decimate (24.L6-4)"),
    "body-join": var(["--body", "join"], note="24.L6-4: the parts joined, no single shell"),
    "k-class": var(["--sdf-k-mode", "class"], note="29.L11-5"),
    "k-hard": var(["--sdf-k-mode", "hard"], note="29.L11-5"),
    "core": var(["--sdf-core", "on"], note="33.L15-2: only the core in the SDF; head, hands, feet, props, hard plates rigid pieces"),
    "cvt": var(["--sdf-retopo", "cvt"], note="29.L11-6: Voronoi/CVT retopology guided by curvature"),
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
    "iters-8": var(over={"optimize_verts.DETERMINISTIC_ITERS": 8}, note="control: the old default, 8 iterations per stage (15 since 31.L13-4)"),
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
    "c-no-outline": var(["--outline", "off"], colour=True, note="33.L15-7: control without the inverted-hull contour (hull is the default)"),
    "c-face": var(["--face", "decal"], colour=True, note="33.L15-3: the head cut at 128 px on a quad in front of the head"),
    "c-zone-contrast": var(["--zone-contrast", "on"], colour=True, note="33.L15-3: close palette slots pushed apart (darker x.8)"),
    "c-painted": var(["--texture", "painted"], colour=True, note="the older painted texture"),
}
# live flags the matrix does not turn on as a variant, each with the reason (test_ablation_matrix: nothing live may be missing)
NOT_A_VARIANT = {
    "eye": "needs the LLM agent (L15-5: ~10 min and 3-4 model calls per unit, measured in its own battery v16, not in a deterministic matrix)",
    "eye_rounds": "a parameter of --eye (L15-5)",
    "gate": "the acceptance, not a shape: stage 1 runs the same build, the verdict differs (L15-1: its own table over the v15 battery)",
    "orient": "how the gate reads the sheet (refs/<id>/sheet.json), not a shape variant (L15-1)",
    "judge_gate": "needs the paired judge (a Claude session) on top of --pair; not a deterministic variant (L15-1)",
    "loop": "needs the LLM author (L11-2/L11-4: measured in the v14 battery)",
    "deterministic": "on in every run of the matrix (base is deterministic)",
    "parts": "the input of fit-parts / fit-depth / depth-tri (refs/<id>/parts.json by default)",
    "shape_only": "stage selector: the shape variants are --shape-only, the c-* ones are not",
    "colour_on_fail": "stage 2 after a failing stage 1: only matters to a battery with a failing unit",
    "colour_only": "stage selector: stage 2 alone on an existing run (L14-2)",
    "fit_luma": "colour wave: variant c-luma",
    "polish": "needs the LLM agent (L13-1: measured in its own pilot, not in a deterministic matrix)",
}


def merge(a, b, name=""):
    """The combination of two variants. Flags join (a repeated one once); a flag, a module override or an environment variable
    must agree or be absent in one of them; units intersect."""
    over, env = dict(a["over"]), dict(a["env"])
    for what, src, dst in (("override", b["over"], over), ("env", b["env"], env)):
        for k, v in src.items():
            if k in dst and dst[k] != v:
                raise ValueError(f"{name}: {what} {k} is {dst[k]!r} in one part and {v!r} in the other")
            dst[k] = v
    flags = list(a["flags"])
    for g in b["flags"]:
        clash = [h for h in flags if h[0] == g[0] and h != g]
        if clash:
            raise ValueError(f"{name}: {g[0]} is {clash[0][1:]} in one part and {g[1:]} in the other")
        if g not in flags:
            flags.append(g)
    units = a["units"] if b["units"] is None else b["units"] if a["units"] is None else tuple(u for u in a["units"] if u in b["units"])
    return var([w for g in flags for w in g], over, f"{a['build']} {b['build']}".strip(), a["colour"] or b["colour"], units, a["needs"] or b["needs"],
               f"{a['note']} + {b['note']}".strip(" +"), env)


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


def run_name(name, prefix=PREFIX):
    return f"{prefix}{name}"


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
    race, label, role = UNITS[unit]
    return [sys.executable, str(ROOT / "tools/blender/spec_pipeline.py"), "--id", unit, "--race", race, "--name", label, "--role", role, "--kind", "mass",
            "--rig", json.loads((DRAFT / unit / ORIGIN / "spec.json").read_text()).get("rig", "biped"), "--spec", str(DRAFT / unit / ORIGIN / "spec.json"),
            "--no-repair", "--no-diagnose", "--deterministic", "--run", run_name(name),
            *([] if "--body" in flags else ["--body", "sdf"]), *([] if v["colour"] else ["--shape-only"]),
            *(["--tilts", tilts] if tilts else []), *flags]


def environment(v):
    """The environment of one build: SOFT_SIL_THREADS, plus the variant's env, CF_OVERRIDES and CF_BUILD_ARGS when it has any."""
    env = {**os.environ, "SOFT_SIL_THREADS": os.environ.get("SOFT_SIL_THREADS", "4"), **v["env"]}
    if v["over"]:
        env["CF_OVERRIDES"] = json.dumps(v["over"])
    if v["build"]:
        env["CF_BUILD_ARGS"] = v["build"]
    return env


# ------------------------------------------------------------------------------------------------ measurement rows
def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 4) if xs else None


def gate_view(sil, key, view):
    """The number the gate judges `view` by (spill, bare, iou): the body's when the sheet has props there (L12-5), else the whole
    silhouette's (`uncovered` is the key of bare in silhouette.json)."""
    if view in sil.get("body_iou", {}):
        return sil.get(f"body_{key}", {}).get(view)
    return sil.get({"iou": "approved", "bare": "uncovered"}.get(key, key), {}).get(view)


def look_numbers(look):
    """(planarity, mean crease recall over the views) of clay.look.json's look_after; (None, None) without it."""
    if not look:
        return None, None
    return look.get("planarity"), mean([r for _, r in look.get("crease_chamfer", {}).values()])


def make_row(unit, name, sil, lint, times, zones=None, model=None, look=None, depth=None):
    """One flat measurements row (inputs already parsed). `lint` = mesh_lint of clay.glb (or None), `times` = {total_s, build_s,
    verts_s}, `zones` = stage 2's per-view zone report, `model` = {atlas_kb, prims, images, materials, ...} of model.glb, `look` =
    clay.look.json's look_after, `depth` = clay.depth.json."""
    ap, gates = sil.get("approved", {}), sil.get("gates", {})
    iou = [ap.get(v) for v in VIEWS]
    spill, bare = ([gate_view(sil, k, v) for v in VIEWS] for k in ("spill", "bare"))
    planarity, crease = look_numbers(look)
    row = {"unit": unit, "variant": name, "ok": True, "iou": iou, "mean": mean(iou),
           "spill_v": spill, "bare_v": bare, "contact_v": [sil.get("contact", {}).get(v) for v in VIEWS],
           "spill": mean(spill), "bare": mean(bare), "contact": mean([sil.get("contact", {}).get(v) for v in VIEWS]),
           "spill_ok": sum(1 for x in spill if x is not None and x <= SPILL_OK),
           "z_err": ((depth or {}).get("z_err") or {}).get("z_err"), "planarity": planarity, "crease": crease,
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


def vs_base(row, base, noise=None):
    """Deltas of one row against the base row of its unit: per view and mean for IoU, spill, bare; the views that fall more than 2 sigma
    (noise.threshold; 0.01 without a table); the views clean in spill; contact, z_err, planarity, crease, slivers, nd, tris, seconds."""
    if not (row["ok"] and base and base["ok"]):
        return None
    d = [dv(a, b) for a, b in zip(row["iou"], base["iou"])]
    unit = row["unit"]
    out = {"iou": d, "spill_v": [dv(a, b) for a, b in zip(row["spill_v"], base["spill_v"])],
           "falls": [v for v, x in zip(VIEWS, d) if x is not None and x < -NZ.threshold(v, noise, unit=unit)]}
    for k in ("mean", "spill", "bare", "contact", "z_err", "planarity", "crease", "sliver", "nd", "total_s", "luma_l1", "atlas_kb", "tris", "spill_ok"):
        out[k] = dv(row.get(k), base.get(k))
    return out


def summarize(rows, noise=None):
    """{variant: {n, mean, spill, spill_ok, base_spill_ok, bare, falls, contact, z_err, planarity, crease, tris, seconds, moved, units}}:
    each variant against the base row of its unit; averages are over the per-unit deltas, spill_ok / falls are sums over units (views)."""
    by = {(r["unit"], r["variant"]): r for r in rows}
    out = {}
    for name in dict.fromkeys(r["variant"] for r in rows):
        if name in ("base", "c-base"):
            continue
        b = base_of(name)
        got = {u: d for u in UNITS if (u, name) in by and (d := vs_base(by[u, name], by.get((u, b)), noise))}
        mine = [by[u, name] for u in got]
        base = [by[u, b] for u in got]
        out[name] = {"n": len(got), "units": got, "falls": sum(len(d["falls"]) for d in got.values()),
                     "spill_ok": sum(r["spill_ok"] for r in mine), "base_spill_ok": sum(r["spill_ok"] for r in base),
                     "views": 6 * len(got), "moved": any(abs(x) > FLAT for d in got.values() for x in (d["mean"], d["spill"], d["bare"]) if x is not None),
                     **{k: mean([d[k] for d in got.values()]) for k in ("mean", "spill", "bare", "contact", "z_err", "planarity", "crease", "sliver", "nd", "tris")},
                     "seconds": mean([d["total_s"] for d in got.values()])}
    return out


def verdict(s):
    """default-candidate: spill falls (mean by more than SPILL_EPS) and no view falls more than 2 sigma. opt-in: something improves
    (spill or IoU) but a view falls. no: nothing improves (or nothing moved at all: said so)."""
    if s["n"] == 0:
        return "not measured"
    if not s["moved"]:
        return "no (no-op: nothing moved)"
    better_spill = (s["spill"] or 0) < -SPILL_EPS
    if better_spill and not s["falls"]:
        return "default-candidate"
    if better_spill or (s["mean"] or 0) > 0:
        return f"opt-in ({s['falls']} view(s) fall > 2σ)" if s["falls"] else "opt-in (spill does not fall)"
    return "no"


def verdict_class(s):
    """The verdict without its detail: default-candidate, opt-in, no, not measured (a changed count of falling views is not a change of verdict)."""
    return verdict(s).split(" (")[0]


def winners(summary):
    """The shape variants (not combinations, not controls) with the verdict default-candidate, in the table's order."""
    return [n for n, s in summary.items() if "+" not in n and not n.startswith(("no-", "body-", "c-", "dsl-off")) and verdict(s) == "default-candidate"]


# ------------------------------------------------------------------------------------------------ tables
def f(v, nd=3):
    return "–" if v is None else f"{v:.{nd}f}" if isinstance(v, float) else str(v)


def sgn(v, nd=3):
    return "–" if v is None else f"{v:+.{nd}f}"


def order_of(name):
    first = name.split("+")[0]
    return (list(VARIANTS).index(first) if first in VARIANTS else 99, name)


def table(rows, noise=None):
    """Markdown: one line per (variant, unit) with IoU, spill and bare per view, then the deltas against the unit's base."""
    head = ("| variant | unit | IoU f/l/b/top/bot/rts | spill f/l/b/top/bot/rts | spill ≤ .03 | bare mean | Δ IoU | Δ spill | falls > 2σ | contact | z_err | plan | crease R | tris | s |\n"
            + "|---" * 15 + "|")
    by = {(r["unit"], r["variant"]): r for r in rows}
    out = [head]
    for r in sorted(rows, key=lambda r: (order_of(r["variant"]), r["unit"])):
        if not r["ok"]:
            out.append(f"| {r['variant']} | {r['unit']} | {'skipped: ' if r.get('skipped') else 'FAIL: '}{r['cause']} |" + " |" * 12)
            continue
        d = vs_base(r, by.get((r["unit"], base_of(r["variant"]))), noise)
        out.append(f"| {r['variant']} | {r['unit']} | {' / '.join(f(x).lstrip('0') for x in r['iou'])} | {' / '.join(f(x).lstrip('0') for x in r['spill_v'])} "
                   f"| {r['spill_ok']}/6 | {f(r['bare'])} | {sgn(d and d['mean'], 4)} | {sgn(d and d['spill'], 4)} | {', '.join(d['falls']) if d and d['falls'] else '–'} "
                   f"| {f(r['contact'])} | {f(r['z_err'])} | {f(r['planarity'], 2)} | {f(r['crease'], 2)} | {f(r['tris'])} | {f(r['total_s'], 0)} |")
    return "\n".join(out)


def summary_table(summary):
    """Markdown: one line per variant against base, spill first, then the rest of the brief's columns and the verdict."""
    out = ["| variant | units | Δ spill | views spill ≤ .03 (base) | Δ IoU | Δ bare | views fall > 2σ | Δ contact | Δ z_err | Δ planarity | Δ crease R | Δ tris | Δ s | verdict |",
           "|---" * 14 + "|"]
    for n, s in summary.items():
        out.append(f"| {n} | {s['n']} | {sgn(s['spill'], 4)} | {s['spill_ok']}/{s['views']} ({s['base_spill_ok']}) | {sgn(s['mean'], 4)} | {sgn(s['bare'], 4)} | {s['falls']} "
                   f"| {sgn(s['contact'], 4)} | {sgn(s['z_err'], 4)} | {sgn(s['planarity'], 3)} | {sgn(s['crease'], 3)} | {sgn(s['tris'], 0)} | {sgn(s['seconds'], 0)} | {verdict(s)} |")
    return "\n".join(out)


def before_after_table(before, after):
    """Markdown: the variants measured in both matrices whose verdict changed (before = L11-7 code, after = L12), with the numbers."""
    out = ["| variant | verdict before (L11-7) | verdict after (L12) | Δ spill before → after | Δ IoU before → after | views fall > 2σ before → after |", "|---" * 6 + "|"]
    for n in after:
        if n in before and verdict_class(before[n]) != verdict_class(after[n]):
            b, a = before[n], after[n]
            out.append(f"| {n} | {verdict(b)} | {verdict(a)} | {sgn(b['spill'], 4)} → {sgn(a['spill'], 4)} | {sgn(b['mean'], 4)} → {sgn(a['mean'], 4)} | {b['falls']} → {a['falls']} |")
    return "\n".join(out) if len(out) > 2 else "(no variant changed verdict)"


def colour_table(rows):
    """Markdown: the stage 2 variants, one line per (variant, unit): atlas KB, primitives, luma L1, zone mean, failing zone views."""
    cols = [r for r in rows if r["ok"] and "atlas_kb" in r]
    out = ["| variant | unit | atlas KB | image | prims | materials | luma L1 | zones mean | zone gate | uv out of range |", "|---" * 10 + "|"]
    out += [f"| {r['variant']} | {r['unit']} | {f(r['atlas_kb'], 1)} | {r.get('image', '–')} | {f(r['prims'])} | {f(r['materials'])} | {f(r['luma_l1'])} "
            f"| {f(r['zones_mean'])} | {'FAIL ' + ','.join(r['zone_fail']) if r['zone_fail'] else 'ok'} | {f(r['uv_out'])} |"
            for r in sorted(cols, key=lambda r: (r["variant"], r["unit"]))]
    return "\n".join(out)


COLUMNS = ("variant", "unit", "ok", *(f"iou_{v}" for v in VIEWS), *(f"spill_{v}" for v in VIEWS), *(f"bare_{v}" for v in VIEWS),
           *(f"contact_{v}" for v in VIEWS), "mean", "spill", "bare", "contact", "spill_ok", "d_mean", "d_spill", "d_bare", "falls_2sigma",
           "z_err", "planarity", "crease", "sil_fail", "tris", "sliver", "nd", "euler", "comp", "dev_p95", "hausdorff",
           "form", "total_s", "build_s", "verts_s", "fit_s", "zones_mean", "luma_l1", "atlas_kb", "prims", "materials", "cause")


def csv_text(rows, noise=None):
    """The CSV of all rows (one line per (variant, unit); failed rows keep their cause; d_* and falls_2sigma are against the unit's base)."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    by = {(r["unit"], r["variant"]): r for r in rows}
    for r in rows:
        flat = {**r}
        for key in ("iou", "spill", "bare", "contact"):
            vals = r.get("iou") if key == "iou" else r.get(f"{key}_v")
            flat.update({f"{key}_{v}": (vals or [None] * 6)[i] for i, v in enumerate(VIEWS)})
        d = vs_base(r, by.get((r["unit"], base_of(r["variant"]))), noise) if r["ok"] else None
        flat.update(d_mean=d and d["mean"], d_spill=d and d["spill"], d_bare=d and d["bare"], falls_2sigma=" ".join(d["falls"]) if d else "",
                    sil_fail=" ".join(r.get("sil_fail", [])))
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


def collect(unit, name, v, total_s, root=DRAFT, prefix=PREFIX):
    """The row of one finished run (or a fail row: no clay.glb / silhouette.json, cause from batch.log)."""
    import mesh_lint as ML
    run = root / unit / run_name(name, prefix)
    if not (run / "clay.glb").exists() or not (run / "silhouette.json").exists():
        log = run / "batch.log"
        lines = [ln.strip() for ln in (log.read_text() if log.exists() else "").splitlines() if ln.strip()]
        return fail_row(unit, name, lines[-1][:200] if lines else "no output", total_s)
    lint = ML.lint(run / "clay.glb", sdf=(run / "clay.sdf.json").exists())
    zones = read_json(run / "stage2" / "colour.json").get("zones") if v["colour"] else None
    return make_row(unit, name, read_json(run / "silhouette.json"), lint, times_of(run, total_s), zones if v["colour"] else None,
                    model_of(run) if v["colour"] else None, read_json(run / "clay.look.json").get("look_after"), read_json(run / "clay.depth.json"))


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
    """Runs spec_pipeline for one (unit, variant) into runs/draft/<unit>/l12-mx-<name>/; output to batch.log. An earlier run is renamed
    -invalid<ts>, never deleted. Returns the wall seconds."""
    run = DRAFT / unit / run_name(name)
    if run.exists():
        run.rename(run.with_name(f"{run.name}-invalid{int(time.time())}"))
    run.mkdir(parents=True)
    tilts = tilts_arg(read_json(DRAFT / unit / ORIGIN / "silhouette.json"))
    t0 = time.perf_counter()
    done = subprocess.run(command(unit, name, v, tilts), capture_output=True, text=True, cwd=ROOT, env=environment(v))
    total = time.perf_counter() - t0
    (run / "batch.log").write_text(done.stdout + done.stderr)
    (run / "batch.json").write_text(json.dumps({"total_s": round(total, 1), "returncode": done.returncode, "variant": name, "over": v["over"],
                                                "env": v["env"], "build": v["build"], "flags": v["flags"]}))
    return total


def one(unit, name, args):
    v = resolve(name)
    if not applies(v, unit, ROOT / "artifacts/model-sheets/refs"):
        return skip_row(unit, name, "not applicable (unit not listed or its input file missing)")
    run = DRAFT / unit / run_name(name)
    done = read_json(run / "batch.json")
    if args.collect_only or ("returncode" in done and not args.rebuild):      # exit 1 = a gate FAIL, the run is complete
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
    print(f"{unit} {name}: {'ok mean ' + str(row['mean']) + ' spill ' + str(row['spill']) if row['ok'] else 'FAIL ' + row['cause']} ({row['total_s']} s)", file=sys.stderr, flush=True)
    return row


def disk_rows(root=DRAFT, prefix=PREFIX):
    """The rows of every variant that has a run under `root` (a skip row where it does not apply), so the tables cover all the invocations."""
    names = sorted({d.name[len(prefix):] for d in root.glob(f"*/{prefix}*") if d.is_dir() and "-invalid" not in d.name and resolvable(d.name[len(prefix):])},
                   key=order_of)
    refs, rows = ROOT / "artifacts/model-sheets/refs", []
    for n in names:
        v = resolve(n)
        for u in UNITS:
            if not applies(v, u, refs):
                rows.append(skip_row(u, n, "not applicable (unit not listed or its input file missing)"))
            elif (root / u / run_name(n, prefix) / "batch.json").exists():
                rows.append(collect(u, n, v, read_json(root / u / run_name(n, prefix) / "batch.json").get("total_s", 0.0), root, prefix))
    return rows


def resolvable(name):
    try:
        resolve(name)
        return True
    except ValueError:
        return False


def report(rows, noise=None, before=None):
    """The markdown of analysis/2026-10-30-l12-matrix.md; `before` = summarize() of the L11-7 runs measured the same way."""
    summary = summarize(rows, noise)
    shape = [r for r in rows if not resolve(r["variant"])["colour"]]
    colour = [r for r in rows if resolve(r["variant"])["colour"]]
    return ("# L12-10a ablation matrix (PIPELINE 30.L12-10a)\n\nEach variant rebuilds the v13 spec of the 6 units with `--deterministic` (noise 0), "
            "cameras of v13 fixed, no LLM; Δ against `base` (colour: against `c-base`). Spill and bare are the gate's numbers (the body's where the sheet has props). "
            "\"falls > 2σ\" counts the (unit, view) cells whose IoU falls by more than 2σ of `noise-l12.json`. Verdict: default-candidate = mean spill falls "
            f"(by more than {SPILL_EPS}) and no view falls > 2σ; opt-in = spill or IoU improves but a view falls; no = nothing improves.\n\n"
            "## Summary by variant\n\n" + summary_table(summary)
            + ("\n\n## Before (L11-7 code) vs after (L12)\n\n" + before_after_table(before, summary) if before else "")
            + "\n\n## Variant x unit (shape)\n\n" + table(shape, noise) + ("\n\n## Stage 2 (colour)\n\n" + colour_table(colour) if colour else "") + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--variants", default="", help="comma-separated names (a+b combines); default: every shape variant")
    ap.add_argument("--units", default="", help="comma-separated ids (default: the 6 of the battery)")
    ap.add_argument("--jobs", type=int, default=2, help="parallel spec_pipeline processes (2 max on this machine)")
    ap.add_argument("--collect-only", action="store_true", help="do not build, measure the runs already on disk")
    ap.add_argument("--rebuild", action="store_true", help="rebuild runs that already have a batch.json (the old one is renamed -invalid)")
    ap.add_argument("--list", action="store_true", help="print the variants and exit")
    ap.add_argument("--out", type=pathlib.Path, default=ANALYSIS / "2026-10-30-l12-matrix", help="writes <out>.csv and <out>.md")
    ap.add_argument("--copy", type=pathlib.Path, default=None, help="also copy the csv and md to this directory (as ablation-matrix-<out name>.*)")
    ap.add_argument("--legacy", type=pathlib.Path, default=None,
                    help="runs/draft of the L11-7 matrix (l11-mx-* runs): its verdicts, measured the same way, go in a before/after table")
    args = ap.parse_args(argv)
    if args.list:
        print("\n".join(f"{n:16} {v['note']}" for n, v in VARIANTS.items()))
        return 0
    names = [x for x in args.variants.split(",") if x] or [n for n, v in VARIANTS.items() if not v["colour"]]
    for n in names:
        resolve(n)
    units = [u for u in (args.units.split(",") if args.units else UNITS) if u]
    tasks = [(u, n) for n in names for u in units]
    if not args.collect_only:
        with cf.ThreadPoolExecutor(args.jobs) as pool:
            list(pool.map(lambda t: one(*t, args), tasks))
    noise = NZ.load(NOISE)
    rows = disk_rows()
    before = summarize(disk_rows(args.legacy, "l11-mx-"), noise) if args.legacy else None
    args.out.with_suffix(".csv").write_text(csv_text(rows, noise))
    args.out.with_suffix(".md").write_text(report(rows, noise, before))
    for ext in (".csv", ".md") if args.copy else ():
        shutil.copy(args.out.with_suffix(ext), args.copy / f"ablation-matrix-{args.out.name}{ext}")
    print(summary_table(summarize(rows, noise)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
