"""Guarded VLM loop (ROADMAP Leva 11, L11-2; PIPELINE 29.L11-2): diagnose -> one delta at a time -> rebuild -> keep only what measures better.

`run(...)` is pure orchestration: every side effect (the diagnosis call, the rebuild, the file shuffling) is a callback, so the
acceptance rule, the ordering, the 3-deltas-per-round limit and the stop are testable without Blender or an LLM.
Called by spec_pipeline.py --loop N; the callbacks are built there.

    loop/round0/            copy of the round-0 run (clay.glb, spec.json, silhouette.json, views/) for the paired judge
    loop/round<k>/delta<j>/ the candidate rebuilt with the delta alone (spec.json, silhouette.json, clay.glb, views/)
    loop/round<k>/diagnosis.json
    loop.json               per delta: status, delta, before/after IoU per view, change per view, seconds
"""
import json
import re
import time

DROP = 0.01       # a view may not fall more than this
GAIN = 0.005      # the mean must rise by this ... (or a failing gate must pass)
PER_ROUND = 3     # rebuilds per round
EPS = 1e-9
VIEWS = ("front", "left", "back", "top", "bottom", "rts")


def mean(iou):
    return sum(iou[v] for v in VIEWS if v in iou) / max(1, sum(v in iou for v in VIEWS))


def loop_accept(before, after, gates):
    """(accepted, reason): no view falls more than DROP and (the mean rises by GAIN or a gate that failed now passes)."""
    fell = [f"{v} {after[v] - before[v]:+.3f}" for v in before if v in after and after[v] < before[v] - DROP - EPS]
    if fell:
        return False, "view fell: " + ", ".join(fell)
    fixed = [v for v in before if v in after and v in gates and before[v] < gates[v] <= after[v]]
    gain = mean(after) - mean(before)
    if gain >= GAIN - EPS:
        return True, f"mean {gain:+.4f}"
    if fixed:
        return True, f"gate passes: {', '.join(fixed)}"
    return False, f"mean {gain:+.4f} < {GAIN}, no gate fixed"


def order_deltas(deltas, expected):
    """Largest expected gain first. A delta has no view of its own: its score is the best `expected` among the views its
    `why` names (word match); a delta that names none scores 0 and keeps the VLM's order (stable sort)."""
    def score(d):
        words = set(re.findall(r"[a-z]+", str(d.get("why", "")).lower()))
        return max([x for v, x in expected.items() if v in words] or [0.0])
    return sorted(deltas, key=lambda d: -score(d))


def change(before, after):
    return {v: round(after[v] - before[v], 4) for v in before if v in after}


def attempt(cur, delta, out, hooks):
    """One delta alone on the current spec -> (entry, candidate or None). The rebuild is the round-0 path (hooks.rebuild)."""
    t0 = time.monotonic()
    spec2, log = hooks.apply(cur["spec"], [delta])
    entry = {"delta": delta, "status": log[0]["status"], "why": log[0]["why"]}
    if log[0]["status"] != "applied":
        return {**entry, "status": "not-applied"}, None
    spec3, shape, summary = hooks.rebuild(spec2, out)
    after = summary.get("approved") or {}
    entry["seconds"] = round(time.monotonic() - t0, 1)
    if shape.get("glb") is None or not after:
        return {**entry, "status": "rejected", "why": "build failed"}, None
    ok, why = loop_accept(cur["iou"], after, cur["gates"])
    entry |= {"status": "accepted" if ok else "rejected", "why": why, "after": after, "change": change(cur["iou"], after)}
    return entry, ({"spec": spec3, "shape": shape, "summary": summary, "iou": after, "gates": cur["gates"], "dir": out}
                   if ok else None)


def do_round(k, cur, hooks, limit):
    """One round: diagnose the current best, try its deltas in `expected` order, promote each accepted one. Returns
    (round entry, cur)."""
    t0 = time.monotonic()
    hooks.prepare(cur)                                   # review.md + compare.png of the current best (the diagnosis reads them)
    doc = hooks.diagnose()
    rdir = hooks.loop_dir / f"round{k}"
    rdir.mkdir(parents=True, exist_ok=True)
    (rdir / "diagnosis.json").write_text(json.dumps(doc, indent=2))
    rows, tried = [], 0
    for d in order_deltas(doc["deltas"], doc["expected"]):
        if tried >= limit:
            break
        entry, cand = attempt(cur, d, rdir / f"delta{len(rows) + 1}", hooks)
        entry["before"] = cur["iou"]
        tried += entry["status"] != "not-applied"
        rows.append(entry)
        if cand:
            cur = cand
            hooks.promote(cur)
            if d.get("action") in ("add", "remove"):     # part addresses shifted: the rest of the list is stale
                break
    return {"round": k, "cost": doc["cost"], "expected": doc["expected"], "deltas": rows,
            "accepted": sum(r["status"] == "accepted" for r in rows), "seconds": round(time.monotonic() - t0, 1)}, cur


def run(n, spec, shape, summary, hooks, limit=PER_ROUND):
    """Rounds 1..n over the round-0 build (`spec`, `shape`, `summary`). Returns (spec, shape, summary, report) of the best;
    stops at the first round with no accepted delta. hooks: apply(spec, [delta]) -> (spec2, log); rebuild(spec, dir) ->
    (spec, shape, summary); diagnose() -> doc; prepare(cur); promote(cur); loop_dir."""
    cur = {"spec": spec, "shape": shape, "summary": summary, "iou": summary["approved"],
           "gates": summary.get("gates", {}), "dir": None}
    # measured: two --deterministic rebuilds of one spec are equal (hfoo, PIPELINE 29.L11-2); the clocked ones varied up to .013 per view
    report = {"deterministic": True, "noise": 0.0, "round0": cur["iou"], "rounds": []}
    for k in range(1, n + 1):
        entry, cur = do_round(k, cur, hooks, limit)
        report["rounds"].append(entry)
        if not entry["accepted"]:
            break
    report |= {"final": cur["iou"], "mean": [round(mean(report["round0"]), 4), round(mean(cur["iou"]), 4)]}
    (hooks.loop_dir / "loop.json").write_text(json.dumps(report, indent=2))
    return cur["spec"], cur["shape"], cur["summary"], report


def table(report):
    """review.md 'Laço' section."""
    if not report:
        return ""
    rows = "".join(
        f"| {r['round']}.{j} | {d['status']} | {json.dumps(d['delta'], separators=(',', ':'))[:70]} | "
        f"{' '.join(f'{v[:2]} {x:+.3f}' for v, x in d.get('change', {}).items())} | {d['why'][:50]} | {d.get('seconds', '-')} |\n"
        for r in report["rounds"] for j, d in enumerate(r["deltas"], 1))
    cost = sum(r["cost"]["seconds"] for r in report["rounds"])
    return (f"## Laço (--loop)\n\nmean {report['mean'][0]} -> {report['mean'][1]}; diagnose {cost:.0f} s over "
            f"{len(report['rounds'])} round(s).\n\n| delta | status | delta | change per view | why | s |\n|---|---|---|---|---|---|\n"
            f"{rows}\n")
