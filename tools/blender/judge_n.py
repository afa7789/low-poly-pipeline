#!/usr/bin/env python3
"""L18-4: how many votes does the pairwise judge need? (PIPELINE 36.L18-4)

    python3.14 tools/blender/judge_n.py run    --a v16-r3 --b v18-up [--units n005,...] [--ns 2,4,6,8] [--reps 2] [--out DIR]
    python3.14 tools/blender/judge_n.py report [--out DIR]

`run` judges B against A (review_pair.compare, half the votes with A/B swapped, one vote at a time) with N votes, `reps` independent
repetitions per N, and keeps <out>/res/<unit>__N<n>__r<rep>.json with the wall clock of the call. `report`: per N the tie rate (axes that
end tie), the agreement between repetitions (same winner per unit and axis), the agreement on form in units, calls and seconds; and the
pick: the smallest N whose form agreement reaches AGREE of the units AND is not beaten by the next N (stable: more votes buy nothing)."""
import argparse
import json
import pathlib
import statistics
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ablation_matrix as AM  # noqa: E402
import review_pair as RP  # noqa: E402

ROOT = AM.ROOT
DRAFT = ROOT / "artifacts/model-sheets/runs/draft"
OUT = ROOT / "artifacts/model-sheets/history/2026-10-31-l18/judge-n"
NS, REPS, AGREE = (2, 4, 6, 8), 2, 5 / 6
AXES = RP.AXES


def judge_once(unit, a, b, n, rep, out, model="session:opus"):
    """One compare of N votes, kept as res/<unit>__N<n>__r<rep>.json (reused when there); the result with seconds and votes."""
    res = out / "res" / f"{unit}__N{n}__r{rep}.json"
    if res.exists():
        return json.loads(res.read_text())
    res.parent.mkdir(parents=True, exist_ok=True)
    saved = RP.concurrent.futures.ThreadPoolExecutor
    RP.concurrent.futures.ThreadPoolExecutor = lambda k: saved(1)
    t0 = time.perf_counter()
    try:
        result = RP.compare(DRAFT / unit / a, DRAFT / unit / b, unit, "mass", model, work=out / "work" / f"{unit}-N{n}-r{rep}", votes=n,
                            out=out / "work" / f"{unit}-N{n}-r{rep}" / "pairwise.json")
    finally:
        RP.concurrent.futures.ThreadPoolExecutor = saved
    result.update(n=n, rep=rep, seconds=round(time.perf_counter() - t0, 1), calls=n)
    res.write_text(json.dumps(result, indent=1))
    print(unit, f"N{n} r{rep}", RP.line(result), f"{result['seconds']} s")
    return result


def run(units, a, b, ns, reps, out):
    for n in ns:
        for rep in range(1, reps + 1):
            for u in units:
                judge_once(u, a, b, n, rep, out)


# ---------------------------------------------------------------- pure report helpers
def winners(results):
    """{(unit, rep): {axis: winner}} of a list of results."""
    return {(r["unit"], r["rep"]): {ax: r[ax]["winner"] for ax in AXES} for r in results}


def tie_rate(results):
    """Share of the (unit, axis) verdicts that are a tie."""
    picks = [r[ax]["winner"] for r in results for ax in AXES]
    return round(picks.count("tie") / len(picks), 3) if picks else None


def agreement(results, axis=None):
    """Share of (unit, axis) pairs on which every repetition names the same winner (`axis` restricts to one axis)."""
    by = {}
    for r in results:
        for ax in AXES if axis is None else (axis,):
            by.setdefault((r["unit"], ax), []).append(r[ax]["winner"])
    pairs = [v for v in by.values() if len(v) > 1]
    return round(sum(len(set(v)) == 1 for v in pairs) / len(pairs), 3) if pairs else None


def form_units(results):
    """Units on which every repetition agrees on form, and their number."""
    by = {}
    for r in results:
        by.setdefault(r["unit"], []).append(r["form"]["winner"])
    agreed = sorted(u for u, v in by.items() if len(v) > 1 and len(set(v)) == 1)
    return agreed, len(by)


def per_n(results):
    """{n: {tie, agree, agree_form, form_units, units, calls, seconds_median, seconds_total}} from all results."""
    out = {}
    for n in sorted({r["n"] for r in results}):
        rs = [r for r in results if r["n"] == n]
        agreed, units = form_units(rs)
        out[n] = {"tie": tie_rate(rs), "agree": agreement(rs), "agree_form": agreement(rs, "form"), "form_units": len(agreed), "units": units,
                  "calls": sum(r.get("calls", n) for r in rs), "seconds_median": round(statistics.median(r.get("seconds", 0) for r in rs), 1),
                  "seconds_total": round(sum(r.get("seconds", 0) for r in rs), 1), "reps": max(r["rep"] for r in rs)}
    return out


def pick(table, agree=AGREE):
    """The smallest N whose form agreement reaches `agree` of the units and is not beaten by the next N measured (stable); when none does,
    the N with the highest form agreement (ties: the smallest)."""
    ns = sorted(table)
    for i, n in enumerate(ns):
        t = table[n]
        nxt = table[ns[i + 1]]["form_units"] if i + 1 < len(ns) else t["form_units"]
        if t["units"] and t["form_units"] / t["units"] >= agree and nxt <= t["form_units"]:
            return n
    return min(ns, key=lambda n: (-table[n]["form_units"], n)) if ns else None


def lines(table, chosen):
    rows = ["| N | tie rate | agreement reps (all axes) | agreement reps (form) | form: same winner (units) | calls | median s / call | total s |", "|---" * 8 + "|"]
    for n, t in table.items():
        rows.append(f"| {n}{' **(default)**' if n == chosen else ''} | {t['tie']} | {t['agree']} | {t['agree_form']} | {t['form_units']}/{t['units']} | {t['calls']} | "
                    f"{t['seconds_median']} | {t['seconds_total']} |")
    return "\n".join(rows)


def load(out):
    return [json.loads(p.read_text()) for p in sorted((out / "res").glob("*.json"))] if (out / "res").exists() else []


def report(out):
    table = per_n(load(out))
    chosen = pick(table)
    text = lines(table, chosen) + f"\n\npick: N = {chosen} (smallest N with form agreement >= {AGREE:.2f} of the units between repetitions that the next N does not beat)\n"
    (out / "table.md").write_text(text)
    print(text)
    return chosen


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=("run", "report"))
    ap.add_argument("--a", default="v16-r3")
    ap.add_argument("--b", default="v18-up")
    ap.add_argument("--units", default=",".join(AM.UNITS))
    ap.add_argument("--ns", default=",".join(map(str, NS)))
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    out = pathlib.Path(args.out)
    if args.cmd == "run":
        run(args.units.split(","), args.a, args.b, [int(x) for x in args.ns.split(",")], args.reps, out)
    report(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
