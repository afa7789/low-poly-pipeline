"""Noise floor of the per-view IoU (PIPELINE 30.L12-7): sigma per view from N rebuilds of one unit, and the 2-sigma threshold the
guards (loop_stage, author_guard, spec_pipeline.guard_fit) and compare_runs use instead of a fixed 0.01.

noise.json = {unit: {view: sigma}, "global": {view: median over units of sigma}}. No file -> every threshold is its old constant.
Pure functions; sdf_batch.py --repeat N writes the file.
"""
import json
import pathlib
import statistics

FLOOR = 0.005        # a view never needs more than this to be called a change, whatever sigma says
K = 2.0              # sigmas


def load(path):
    """The noise.json at `path`, or None (no path)."""
    return json.loads(pathlib.Path(path).read_text()) if path else None


def sigmas(rows):
    """{view: sample standard deviation} over N >= 2 {view: IoU} rebuilds of one unit; {} for fewer."""
    if len(rows) < 2:
        return {}
    return {v: round(statistics.stdev(r[v] for r in rows), 4) for v in rows[0] if all(v in r for r in rows)}


def table(per_unit):
    """noise.json content from {unit: [{view: IoU}, ...]}: the sigmas per unit and `global` = the median over units, per view."""
    out = {u: s for u, rows in per_unit.items() if (s := sigmas(rows))}
    views = {v for s in out.values() for v in s}
    out["global"] = {v: round(statistics.median(s[v] for s in out.values() if v in s), 4) for v in sorted(views)}
    return out


def sigma(noise, view, unit=None):
    """Sigma of `view` for `unit`, else the global one, else None."""
    for key in (unit, "global"):
        s = ((noise or {}).get(key) or {}).get(view) if key else None
        if s is not None:
            return s
    return None


def threshold(view, noise=None, default=0.01, unit=None):
    """The change a view must exceed to count: max(2 sigma, FLOOR); `default` without a noise table or a sigma for the view."""
    s = sigma(noise, view, unit)
    return default if s is None else max(K * s, FLOOR)


def mark(view, delta, noise, unit=None):
    """'> 2σ' when |delta| clears the threshold, 'ruído' when not, '' without a sigma for the view."""
    s = sigma(noise, view, unit)
    return "" if s is None else ("> 2σ" if abs(delta) > threshold(view, noise, unit=unit) else "ruído")
