#!/usr/bin/env python3
"""Calibrate the pairwise judge (L17-1): cycles, repeatability, position bias, the identical-pair control, cost.

    python3.14 tools/blender/judge_calib.py run   <out_dir> --jobs trio|hfoo|ident [--drafts DIR]
    python3.14 tools/blender/judge_calib.py report <out_dir>

`run` judges each job one vote at a time (the machine is shared), 8 votes with the A/B swap, and keeps
<out_dir>/res/<unit>__<A>__<B>__<kind>__r<rep>.json (a result already there is reused). The renders come from
the pairwise dirs the earlier levas left in the drafts dir (no Blender). `ident` forces the judge on the
identical pair (v16-r1 x v16-r1: the same renders twice; v16-skin-off has no cached render and Blender is off limits) by turning the hash short-cut off: the control for the
winner the judge invents. `report` prints the markdown tables. A 4-vote reading is the subset of votes 0, 1, 4, 5
(two with A on the left, two swapped: the shape of the old default), so 4 and 8 votes see the same replies.
"""
import argparse
import itertools
import json
import pathlib
import shutil
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import review_pair as RP  # noqa: E402

DRAFTS = pathlib.Path(__file__).resolve().parents[2] / "artifacts/model-sheets/runs/draft"
JOBS = {
    "trio": [("n005", a, b) for a, b in (("v16-r3", "v16-r6"), ("v16-r6", "v16-r9"), ("v16-r3", "v16-r9"))],
    "hfoo": [("hfoo", "v16-r3", "v16-r6")],
    "ident": [(u, "v16-r1", "v16-r1") for u in ("n01X", "hfoo")],
}
REPS = {"trio": 2, "hfoo": 2, "ident": 1}
SUBSET4 = (0, 1, 4, 5)


def cached_renders(drafts, unit, run):
    """Dir holding model-front.png and model-wc3.png of `run`, left by an earlier pairwise (B of its own, A of another's)."""
    for d in sorted((drafts / unit).glob("*/pairwise-*")):
        owner, against = d.parent.name, d.name[len("pairwise-"):]
        for side, name in (("B", owner), ("A", against)):
            if name == run and (d / side / "model-front.png").exists() and (d / side / "model-wc3.png").exists():
                return d / side
    return None


def judge(out, drafts, unit, a, b, kind, rep, forced):
    res = out / "res" / f"{unit}__{a}__{b}__{kind}__r{rep}.json"
    if res.exists():
        return json.loads(res.read_text())
    work = out / "work" / f"{unit}__{a}__{b}"
    for k, run in (("A", a), ("B", b)):
        src = cached_renders(drafts, unit, run)
        if src is None:
            raise SystemExit(f"no cached render of {unit}/{run}")
        (work / k).mkdir(parents=True, exist_ok=True)
        for f in ("model-front.png", "model-wc3.png"):
            shutil.copy(src / f, work / k / f)
    res.parent.mkdir(parents=True, exist_ok=True)
    import spec_pipeline
    saved = RP.concurrent.futures.ThreadPoolExecutor, RP.closeness
    RP.concurrent.futures.ThreadPoolExecutor = lambda n: saved[0](1)
    if forced:
        RP.closeness = lambda *_: None
    c0, t0 = spec_pipeline.USAGE["cost_micro_usd"], time.monotonic()
    try:
        r = RP.compare(drafts / unit / a, drafts / unit / b, unit, work=work / f"w{rep}", votes=8, out=res)
    finally:
        RP.concurrent.futures.ThreadPoolExecutor, RP.closeness = saved
    r["seconds"], r["cost_usd"] = round(time.monotonic() - t0, 1), (spec_pipeline.USAGE["cost_micro_usd"] - c0) / 1e6
    res.write_text(json.dumps(r, indent=2))
    print(unit, a, b, rep, RP.line(r), r["seconds"], "s", r["cost_usd"], "usd", flush=True)
    return r


def retally(result, idx, near=False):
    """{axis: winner} of the votes `idx` of a stored result; `near`: the 3/4 rule, applied when the pair is near-identical."""
    votes = [result["votes"][i] for i in idx if i < len(result["votes"])]
    t = RP.tally(votes, near and result.get("near_identical", False))
    return {a: t[a]["winner"] for a in RP.AXES}, t


def beats(winners, pairs):
    """Edges (winner, loser) of one axis; winners: {(x, y): 'A'|'B'|'tie'} with x the earlier run."""
    return [(x, y) if w == "A" else (y, x) for (x, y), w in winners.items() if w != "tie"]


def has_cycle(edges, nodes):
    wins = {n: sum(w == n for w, _ in edges) for n in nodes}
    return len(edges) == len(nodes) and all(v == 1 for v in wins.values())


def load(out):
    rows = {}
    for f in sorted((out / "res").glob("*.json")):
        unit, a, b, kind, rep = f.stem.split("__")
        rows[(unit, a, b, kind, int(rep[1:]))] = json.loads(f.read_text())
    return rows


def report(out):
    rows = load(out)
    lines = []
    for label, idx, near in (("old rule: 4 votes (0,1,4,5 of the 8), majority", SUBSET4, False),
                             ("8 votes, majority", range(8), False),
                             ("new rule: 8 votes + 6-2 needed when near-identical", range(8), True)):
        lines += [f"### {label}", ""]
        lines += trio_lines(rows, idx, near) + agree_lines(rows, idx, near) + [""]
    lines += bias_lines(rows) + [""] + ident_lines(rows) + [""] + cost_lines(rows)
    text = "\n".join(lines)
    (out / "table.md").write_text(text + "\n")
    print(text)


def pair_winners(rows, kind, rep, idx, unit, near):
    return {(a, b): retally(r, idx, near)[0] for (u, a, b, k, p), r in rows.items() if (u, k, p) == (unit, kind, rep)}


def trio_lines(rows, idx, near):
    out = ["Trio n005 (r3, r6, r9): winner per pair and axis, and whether the three edges form a cycle.", "",
           "| rep | axis | r3 x r6 | r6 x r9 | r3 x r9 | cycle |", "|---|---|---|---|---|---|"]
    for rep in (1, 2):
        w = pair_winners(rows, "trio", rep, idx, "n005", near)
        if len(w) < 3:
            continue
        for ax in RP.AXES:
            per = {pair: w[pair][ax] for pair in w}
            cyc = has_cycle(beats(per, w), {"v16-r3", "v16-r6", "v16-r9"})
            cells = [per[p] for p in sorted(per, key=lambda p: (p[0], p[1]))]
            out.append(f"| {rep} | {ax} | " + " | ".join(cells) + f" | {'CYCLE' if cyc else 'no'} |")
    return out


def agree_lines(rows, idx, near):
    out = ["", "Agreement between the two repetitions (same pair, same axis, same winner incl. tie).", "",
           "| set | axis agreements | pct |", "|---|---|---|"]
    for kind in ("trio", "hfoo"):
        same = total = 0
        for (u, a, b, k, rep), r in rows.items():
            other = rows.get((u, a, b, k, 2))
            if k != kind or rep != 1 or other is None:
                continue
            x, y = retally(r, idx, near)[0], retally(other, idx, near)[0]
            same += sum(x[ax] == y[ax] for ax in RP.AXES)
            total += len(RP.AXES)
        if total:
            out.append(f"| {kind} | {same}/{total} | {100 * same / total:.0f} % |")
    return out


def bias_lines(rows):
    out = ["### Position bias (share of picks for the left cell; .5 = none)", "",
           "| set | all 8 votes (swapped) | the 4 with A on the left only (no swap) |", "|---|---|---|"]
    for kind in ("trio", "hfoo", "ident"):
        sel = [r for k, r in rows.items() if k[3] == kind and not r.get("identical")]
        if not sel:
            continue
        both = sum(len(r["votes"]) for r in sel)
        left = [v[f"{a}_side"] == "left" for r in sel for v in r["votes"] for a in RP.AXES]
        a_left = [v[f"{a}_side"] == "left" for r in sel for v in r["votes"] if v["order"] == "A|B" for a in RP.AXES]
        out.append(f"| {kind} ({both} votes) | {sum(left) / len(left):.3f} | {sum(a_left) / len(a_left):.3f} |")
    return out


def ident_lines(rows):
    out = ["### Identical pair (v16-r1 x v16-r1, same renders), judge forced to vote", "",
           "| unit | rule | sheet | artist | wc3 | form | spurious winners |", "|---|---|---|---|---|---|---|"]
    for (u, a, b, k, rep), r in rows.items():
        if k != "ident":
            continue
        for label, idx, near in (("old: 4 votes, majority", SUBSET4, False), ("8 votes, majority", range(8), False),
                                 ("8 votes, 6-2 needed", range(8), True)):
            t = RP.tally([r["votes"][i] for i in idx if i < len(r["votes"])], near)
            w = [f"{t[x]['winner']} {max(t[x]['A'], t[x]['B'])}-{min(t[x]['A'], t[x]['B'])}" for x in RP.AXES]
            out.append(f"| {u} | {label} | " + " | ".join(w) + f" | {sum(t[x]['winner'] != 'tie' for x in RP.AXES)}/4 |")
    return out


def cost_lines(rows):
    out = ["### Cost per pair (8 votes sequential; 4 votes = half)", "", "| set | pairs | seconds / pair | usd / pair |", "|---|---|---|---|"]
    for kind in ("trio", "hfoo", "ident"):
        sel = [r for k, r in rows.items() if k[3] == kind and "seconds" in r]
        if sel:
            out.append(f"| {kind} | {len(sel)} | {sum(r['seconds'] for r in sel) / len(sel):.0f} | {sum(r['cost_usd'] for r in sel) / len(sel):.2f} |")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("mode", choices=("run", "report"))
    ap.add_argument("out", type=pathlib.Path)
    ap.add_argument("--jobs", choices=tuple(JOBS), default="trio")
    ap.add_argument("--drafts", type=pathlib.Path, default=DRAFTS)
    args = ap.parse_args()
    if args.mode == "report":
        return report(args.out)
    for rep, (unit, a, b) in itertools.product(range(1, REPS[args.jobs] + 1), JOBS[args.jobs]):
        judge(args.out, args.drafts, unit, a, b, args.jobs, rep, forced=args.jobs == "ident")


if __name__ == "__main__":
    sys.exit(main())
