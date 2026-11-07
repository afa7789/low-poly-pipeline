#!/usr/bin/env python3
"""Per-view look of the eye stage (author's rule 2026-11-04): each angle is judged ALONE, before the artist and after its build.

Round r: look(model of r-1) -> one call per view, each seeing only that view's row (concept | render | overlay) -> a score 0-10 and at most
4 defects per view. The artist then sees ALL boards plus those per-view lists and rebuilds. Its build is looked at view by view again; that
"after" is the next round's "before" (no second call). summary["views"] keeps before/after scores per round.
"""
import concurrent.futures as cf
import json
import time

MAX_DEFECTS = 4
SCHEMA = {"type": "object", "required": ["score", "defects"],
          "properties": {"score": {"type": "integer", "minimum": 0, "maximum": 10},
                         "defects": {"type": "array", "maxItems": MAX_DEFECTS,
                                     "items": {"type": "object", "required": ["part", "what", "fix"],
                                               "properties": {k: {"type": "string"} for k in ("part", "what", "fix")}}}}}


def prompt(unit, view, label):
    return (f"You check ONE view of a low-poly game model of {unit['name']} ({unit['race']}). The image is one row: left the concept art's {view.upper()} view, "
            f"middle the {label} rendered from the same side, right an overlay (red = concept only, green = model only).\n"
            f"Judge only this view, as if no other view existed. Score 0-10 how well the render reads as the concept from this side: silhouette, the "
            f"parts present and in place, proportions, colours. List at most {MAX_DEFECTS} defects, worst first, each with the part, what is wrong "
            f"from this side, and the concrete fix (move, resize, add, remove or recolour a piece). No defect when this view already reads right.")


def look(model, unit, rows, label, out_dir, jobs=6):
    """{view: {"score", "defects"} or {"error"}} from one call per row image ({view: png}); model: session:<claude model>, answered under SCHEMA."""
    def one(item):
        view, png = item
        t0 = time.monotonic()
        try:
            import spec_pipeline as SP
            doc = json.loads(SP.ask(model, prompt(unit, view, label), [png], schema=SCHEMA))
            return view, {"score": int(doc["score"]), "defects": doc["defects"][:MAX_DEFECTS], "seconds": round(time.monotonic() - t0, 1)}
        except (RuntimeError, ValueError, KeyError, TypeError) as err:
            return view, {"error": str(err)[:200]}
    with cf.ThreadPoolExecutor(jobs) as ex:
        out = dict(ex.map(one, rows.items()))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "views.json").write_text(json.dumps(out, indent=1))
    return out


def note(looked):
    """The artist's per-view list, appended to the round block."""
    lines = []
    for view, d in looked.items():
        if "error" in d:
            continue
        lines.append(f"- {view.upper()} (score {d['score']}/10): " + ("; ".join(f"{x['part']}: {x['what']} FIX {x['fix']}" for x in d["defects"]) or "reads right, keep it"))
    if not lines:
        return ""
    return ("\n\nEach view was checked ALONE by a reviewer who saw only that side. Look at ALL boards together, reconcile these lists (a fix for one "
            "view must not break another) and fix what they agree on:\n" + "\n".join(lines))


def scores(looked):
    return {v: d.get("score") for v, d in looked.items()}
