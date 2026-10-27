#!/usr/bin/env python3
"""Sheet across runs of one unit: a row per view, the concept first, then one column per run.

    python3 tools/blender/compare_runs.py <out.png> <run_dir> [<run_dir> ...]
        [--against approved|hard] [--show textured|clay|wire|overlay|uv|budgets|clay+wire+overlay+textured]
    python3 tools/blender/compare_runs.py --stability <run_a> <run_b>     # noise between two equal runs

    e.g. compare_runs.py cmp.png runs/draft/n01X/hard-v1 runs/draft/n01X/v2-hard-r1 ...

Same grid and same per-run input contract as make_compare.py (read its docstring): a run
directory with review.md, sil/<against>/ and views/<tag>/. A run missing the files of the
chosen column shows an empty cell and a warning, so older runs still line up. The concept
column comes from the first run's sheet. Footer of each cell: IoU, gate verdict, zones. A last row gives each
run's form numbers from its GLB (mesh_lint, PIPELINE 24.L6-6): normal_diff mean/p90, fairness, body
components, slivers. --show defaults to clay+wire+overlay+textured (the wire shows the steps).

--show budgets: the run dirs given hold budgets/<B>/ (spec_pipeline --budgets, PIPELINE 24.L6-10); one clay column per
budget, the header says tris and slivers.

Score of a run (Zhao 2026: 30 % time, 70 % quality), shown in its header and printed ranked:

    score = 0.3 * f(t) + 0.7 * g(IoU, zones)
    t     = t_gen + t_build + t_passes + t_colour   (seconds, from the "## Timing" of review.md)
    f(t)  = max(0, 1 - t / T_MAX)                   T_MAX = 1200 s: a run that long scores 0 on time
    IoU   = mean over the views of the IoU vs the approved sheet (silhouette.json)
    zones = mean over the views of the zone mean, / ZONE_FULL, capped at 1 (stage 2 runs only)
    g     = IoU                          without zones (a stage 1 run)
          = 0.6 * IoU + 0.4 * zones      with zones
Both f and g are absolute, in [0, 1]: a run's score does not depend on which runs sit beside it.
--stability prints, for two runs meant to be equal (same unit, same recipe), the 3D Chamfer between their
GLBs (5000 points sampled by face area on each, symmetric mean nearest distance, in % of the height of the
first) and the |delta IoU| per view: the measurement noise any "run X beat run Y" claim has to clear.
A run with no Timing section (older than 2026-10-27) or no silhouette numbers has no score.
"""
import argparse
import json
import pathlib
import re
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import make_compare as MC  # noqa: E402
import mesh_lint  # noqa: E402
import review_pair  # noqa: E402

SHOWS = ("textured", "clay", "wire", "overlay", "uv", "budgets")
DEFAULT_SHOW = "clay+wire+overlay+textured"
T_MAX = 1200.0       # seconds; f(t) reaches 0 here
ZONE_FULL = 0.5      # a zone mean of this counts as 1 (the hard-v1 sheets sit near 0.37)
W_TIME, W_QUALITY = 0.3, 0.7
W_IOU, W_ZONES = 0.6, 0.4
STAB_POINTS = 5000   # surface samples per GLB for the 3D Chamfer


def times_of(run_dir):
    """{"gen", "build", "passes", "colour"} seconds from review.md's Timing lines, or None."""
    review = pathlib.Path(run_dir) / "review.md"
    text = review.read_text() if review.exists() else ""
    found = dict(re.findall(r"^- t_(\w+): ([\d.]+) s$", text, re.M))
    return {k: float(v) for k, v in found.items()} if found else None


def score_of(run):
    """(score, f, g, seconds) of a loaded run, or None without timing or IoU numbers."""
    times = times_of(run["dir"])
    path = pathlib.Path(run["dir"]) / "silhouette.json"
    summary = json.loads(path.read_text()) if path.exists() else {}
    ious = list((summary.get("approved") or {}).values())
    if not times or not ious:
        return None
    t = sum(times.values())
    f, iou = max(0.0, 1 - t / T_MAX), sum(ious) / len(ious)
    zones = [z["mean"] for z in ((summary.get("zones") or {}).get("approved") or {}).values()]
    g = iou if not zones else W_IOU * iou + W_ZONES * min(1.0, sum(zones) / len(zones) / ZONE_FULL)
    return W_TIME * f + W_QUALITY * g, f, g, t


def column_cell(run, view, show):
    if show == "overlay":
        return MC.overlay_cell(run, view)
    if show == "wire":
        return MC.wire_cell(run, view)
    if show == "uv":
        return MC.uv_cell(run, view)
    return MC.render_cell(run, view, show == "clay")


def cell_footer(run, view):
    """Short footer text parts of one cell: IoU + gate verdict + zone mean/cover."""
    r = run["report"].get(view)
    if not r:
        return [("no measurement", MC.DIM)]
    gate = r.get("gate")
    ok = "n/a" if gate is None else ("PASS" if r["iou"] >= gate else "FAIL")
    parts = [(f"IoU {r['iou']:.3f} ", MC.INK), (ok, MC.tone(ok))]
    parts += MC.coupling_parts(r)
    z = r.get("zones")
    if z:
        parts.append((f"  zones {z['mean']:.2f}/{z['cover']:.2f}", MC.INK))
    return parts


def form_parts(run):
    """Footer parts of the run's form numbers (4 of mesh_lint.lint on its GLB), or a note without a GLB."""
    try:
        m = mesh_lint.lint(run_glb(run["dir"]))
    except StopIteration:
        return [("form: no GLB", MC.DIM)]
    nd = m["normal_diff"]
    return [(f"form  nd {nd['mean']:.1f}/{nd['p90']:.0f}  fair {m['fairness']:.1f}  "
             f"body {m['components_body']}  slivers {m['sliver_pct']:.1f}%", MC.INK)]


def pair_text(run):
    """'pair vs v7-r2 S A3-1 R B4-0 W tie2-2' from the run's pairwise.json (S sheet, R artist,
    W wc3; the winner, then the votes it got - A is the earlier run), or ''."""
    f = pathlib.Path(run["dir"]) / "pairwise.json"
    if not f.exists():
        return ""
    pw = json.loads(f.read_text())
    cells = [f"{a[0].upper() if a != 'artist' else 'R'} {pw[a]['winner']}{max(pw[a]['A'], pw[a]['B'])}-"
             f"{min(pw[a]['A'], pw[a]['B'])}" for a in review_pair.AXES if a in pw]
    return f"  pair vs {pw['A']} " + " ".join(cells)


def budget_text(run):
    """'B 700 tris 703 slivers 4.2 %' from budget.json of a spec_pipeline --budgets directory, or ''."""
    f = pathlib.Path(run["dir"]) / "budget.json"
    if not f.exists():
        return ""
    b = json.loads(f.read_text())
    return f"  B {b['budget']} tris {b['tris']} slivers {b['sliver_pct']} %"


def budget_dirs(run_dirs):
    """The budgets/<B> directories (ascending B) of every run dir that has them: one column each."""
    out = []
    for d in run_dirs:
        out += sorted((pathlib.Path(d) / "budgets").glob("*/budget.json"), key=lambda f: int(f.parent.name))
    return [f.parent for f in out] or list(run_dirs)


def run_head(run, width):
    img = Image.new("RGB", (width, MC.HEAD_H), (245, 245, 245))
    d = ImageDraw.Draw(img)
    m = run["meta"]
    d.text((10, 8), run["run"], fill=MC.INK, font=MC.font(22))
    d.text((10, 40), f"author {m.get('author', '?')}{pair_text(run)}{budget_text(run)}", fill=MC.DIM, font=MC.font(14))
    st = m.get("stages", {})
    MC.draw_parts(d, (10, 64), [("S1 ", MC.INK), (st.get("1", "n/a"), MC.tone(st.get("1"))),
                                ("  S2 ", MC.INK), (st.get("2", "n/a"), MC.tone(st.get("2"))),
                                ("  verdict ", MC.INK), (m.get("verdict", "n/a"), MC.tone(m.get("verdict")))],
                  MC.font(14))
    sc = score_of(run)
    shown = "score n/a" if sc is None else f"score {sc[0]:.3f} (f {sc[1]:.2f} g {sc[2]:.2f}, {sc[3]:.0f} s)"
    d.text((10, 80), f"status {m.get('status', 'n/a')}  {shown}", fill=MC.INK, font=MC.font(14))
    return img


def concept_head(unit, show, width):
    img = Image.new("RGB", (width, MC.HEAD_H), (245, 245, 245))
    d = ImageDraw.Draw(img)
    d.text((10, 8), unit, fill=MC.INK, font=MC.font(22))
    d.text((10, 40), "concept", fill=MC.DIM, font=MC.font(14))
    d.text((10, 64), f"columns: {show}", fill=MC.DIM, font=MC.font(14))
    return img


def build_sheet(runs, show):
    """One block of columns per run: `show` is one of SHOWS or several joined by "+"
    ("clay+overlay+textured" puts the silhouette difference next to the render, 23.v9)."""
    shows = [x for x in show.split("+") if x]
    w, n = MC.CELL[0], len(shows)
    cols = [concept_head(runs[0]["unit"], show, w)] + [run_head(r, w * n) for r in runs]
    with tempfile.TemporaryDirectory() as tmp:
        concepts = MC.concept_cells(runs[0], pathlib.Path(tmp))
    width = w * (len(runs) * n + 1)
    head = Image.new("RGB", (width, MC.HEAD_H))
    x = 0
    for c in cols:
        head.paste(c, (x, 0))
        x += c.width
    rows = [head]
    for view in MC.view_names(runs[0]):
        cells = [concepts.get(view) or MC.empty_cell("concept absent")]
        cells += [column_cell(r, view, sh) for r in runs for sh in shows]
        foot = Image.new("RGB", (width, MC.FOOT_H), (245, 245, 245))
        d = ImageDraw.Draw(foot)
        d.text((10, 6), view.upper(), fill=MC.INK, font=MC.font(15))
        for i, r in enumerate(runs):
            MC.draw_parts(d, ((1 + i * n) * w + 10, 6), cell_footer(r, view), MC.font(15))
        rows += [MC.join(cells), foot]
    foot = Image.new("RGB", (width, MC.FOOT_H), (245, 245, 245))
    d = ImageDraw.Draw(foot)
    d.text((10, 6), "FORM", fill=MC.INK, font=MC.font(15))
    for i, r in enumerate(runs):
        MC.draw_parts(d, ((1 + i * n) * w + 10, 6), form_parts(r), MC.font(15))
    return MC.stack(rows + [foot])


def sample_surface(glb, n=STAB_POINTS, seed=0):
    """n points on the surface of the GLB, triangles picked by area, uniform inside each."""
    doc, blob = mesh_lint.read_glb(glb)
    pos, _, _, tri = mesh_lint.geometry(doc, blob)
    p = pos[tri]
    area = np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1)
    rng = np.random.default_rng(seed)
    t = p[rng.choice(len(tri), n, p=area / area.sum())]
    u, v = rng.random((2, n, 1))
    flip = u + v > 1
    u, v = np.where(flip, 1 - u, u), np.where(flip, 1 - v, v)
    return t[:, 0] + u * (t[:, 1] - t[:, 0]) + v * (t[:, 2] - t[:, 0]), float(np.ptp(pos[:, 1]))


def chamfer_3d(glb_a, glb_b):
    """(symmetric mean nearest-point distance, height of a) between two GLB surfaces."""
    from scipy.spatial import cKDTree
    a, height = sample_surface(glb_a)
    b, _ = sample_surface(glb_b, seed=1)
    return (cKDTree(b).query(a)[0].mean() + cKDTree(a).query(b)[0].mean()) / 2, height


def run_glb(run_dir):
    """clay.glb when the run has one (stage 1 shape), else model.glb."""
    d = pathlib.Path(run_dir)
    return next(f for f in (d / "clay.glb", d / "model.glb") if f.exists())


def stability(run_a, run_b):
    """Text report: Chamfer 3D (% of height) and |delta IoU| per view between two runs."""
    ch, h = chamfer_3d(run_glb(run_a), run_glb(run_b))
    iou = [json.loads((pathlib.Path(r) / "silhouette.json").read_text()).get("approved") or {} for r in (run_a, run_b)]
    deltas = {v: abs(iou[0][v] - iou[1][v]) for v in iou[0] if v in iou[1]}
    mean = sum(deltas.values()) / max(len(deltas), 1)
    cells = "  ".join(f"{v} {d:.3f}" for v, d in deltas.items())
    return (f"{pathlib.Path(run_a).parent.name}\t{pathlib.Path(run_a).name} vs {pathlib.Path(run_b).name}\t"
            f"chamfer {100 * ch / h:.2f} % H\t|dIoU| mean {mean:.3f} max {max(deltas.values(), default=0):.3f}\t{cells}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", type=pathlib.Path, help="out.png then runs; with --stability: the two runs")
    ap.add_argument("--stability", action="store_true")
    ap.add_argument("--against", choices=("approved", "hard"), default="approved")
    ap.add_argument("--show", default=DEFAULT_SHOW,
                    help="column(s) per run: " + "|".join(SHOWS) + ', or several joined by "+" (clay+overlay+textured)')
    args = ap.parse_args()
    if args.stability:
        if len(args.paths) != 2:
            ap.error("--stability takes exactly two run directories")
        print(stability(*args.paths))
        return
    args.out, args.runs = args.paths[0], args.paths[1:]
    if args.show == "budgets":          # one clay column per budget of spec_pipeline --budgets
        args.runs, args.show = budget_dirs(args.runs), "clay"
    runs = [MC.load_run(r, args.against) for r in args.runs]
    build_sheet(runs, args.show).save(args.out)
    for r in sorted(runs, key=lambda r: -(score_of(r) or (-1,))[0]):
        sc = score_of(r)
        print(f"{r['run']}\t" + ("score n/a" if sc is None else f"score {sc[0]:.3f}\tf {sc[1]:.2f}\tg {sc[2]:.2f}\t{sc[3]:.0f} s"))
    print("wrote", args.out)


if __name__ == "__main__":
    main()
