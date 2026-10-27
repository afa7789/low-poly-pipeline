#!/usr/bin/env python3
"""Sheet across runs of one unit: a row per view, the concept first, then one column per run.

    python3 tools/blender/compare_runs.py <out.png> <run_dir> [<run_dir> ...]
        [--against approved|hard] [--show textured|clay|wire|overlay|uv]

    e.g. compare_runs.py cmp.png runs/draft/n01X/hard-v1 runs/draft/n01X/v2-hard-r1 ...

Same grid and same per-run input contract as make_compare.py (read its docstring): a run
directory with review.md, sil/<against>/ and views/<tag>/. A run missing the files of the
chosen column shows an empty cell and a warning, so older runs still line up. The concept
column comes from the first run's sheet. Footer of each cell: IoU, gate verdict, zones.

Score of a run (Zhao 2026: 30 % time, 70 % quality), shown in its header and printed ranked:

    score = 0.3 * f(t) + 0.7 * g(IoU, zones)
    t     = t_gen + t_build + t_passes + t_colour   (seconds, from the "## Timing" of review.md)
    f(t)  = max(0, 1 - t / T_MAX)                   T_MAX = 1200 s: a run that long scores 0 on time
    IoU   = mean over the views of the IoU vs the approved sheet (silhouette.json)
    zones = mean over the views of the zone mean, / ZONE_FULL, capped at 1 (stage 2 runs only)
    g     = IoU                          without zones (a stage 1 run)
          = 0.6 * IoU + 0.4 * zones      with zones
Both f and g are absolute, in [0, 1]: a run's score does not depend on which runs sit beside it.
A run with no Timing section (older than 2026-10-27) or no silhouette numbers has no score.
"""
import argparse
import json
import pathlib
import re
import sys
import tempfile

from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import make_compare as MC  # noqa: E402

SHOWS = ("textured", "clay", "wire", "overlay", "uv")
T_MAX = 1200.0       # seconds; f(t) reaches 0 here
ZONE_FULL = 0.5      # a zone mean of this counts as 1 (the hard-v1 sheets sit near 0.37)
W_TIME, W_QUALITY = 0.3, 0.7
W_IOU, W_ZONES = 0.6, 0.4


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
    z = r.get("zones")
    if z:
        parts.append((f"  zones {z['mean']:.2f}/{z['cover']:.2f}", MC.INK))
    return parts


def run_head(run, width):
    img = Image.new("RGB", (width, MC.HEAD_H), (245, 245, 245))
    d = ImageDraw.Draw(img)
    m = run["meta"]
    d.text((10, 8), run["run"], fill=MC.INK, font=MC.font(22))
    d.text((10, 40), f"author {m.get('author', '?')}", fill=MC.DIM, font=MC.font(14))
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
    w = MC.CELL[0]
    cols = [concept_head(runs[0]["unit"], show, w)] +[run_head(r, w) for r in runs]
    with tempfile.TemporaryDirectory() as tmp:
        concepts = MC.concept_cells(runs[0], pathlib.Path(tmp))
    width = w * (len(runs) + 1)
    head = Image.new("RGB", (width, MC.HEAD_H))
    for i, c in enumerate(cols):
        head.paste(c, (i * w, 0))
    rows = [head]
    for view in MC.view_names(runs[0]):
        cells = [concepts.get(view) or MC.empty_cell("concept absent")]
        cells += [column_cell(r, view, show) for r in runs]
        foot = Image.new("RGB", (width, MC.FOOT_H), (245, 245, 245))
        d = ImageDraw.Draw(foot)
        d.text((10, 6), view.upper(), fill=MC.INK, font=MC.font(15))
        for i, r in enumerate(runs, 1):
            MC.draw_parts(d, (i * w + 10, 6), cell_footer(r, view), MC.font(15))
        rows += [MC.join(cells), foot]
    return MC.stack(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=pathlib.Path)
    ap.add_argument("runs", nargs="+", type=pathlib.Path)
    ap.add_argument("--against", choices=("approved", "hard"), default="approved")
    ap.add_argument("--show", choices=SHOWS, default="textured")
    args = ap.parse_args()
    runs = [MC.load_run(r, args.against) for r in args.runs]
    build_sheet(runs, args.show).save(args.out)
    for r in sorted(runs, key=lambda r: -(score_of(r) or (-1,))[0]):
        sc = score_of(r)
        print(f"{r['run']}\t" + ("score n/a" if sc is None else f"score {sc[0]:.3f}\tf {sc[1]:.2f}\tg {sc[2]:.2f}\t{sc[3]:.0f} s"))
    print("wrote", args.out)


if __name__ == "__main__":
    main()
