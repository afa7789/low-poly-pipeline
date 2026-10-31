#!/usr/bin/env python3
"""L16-2 critic and fixer apart (PIPELINE 34.L16-2): the strongest model FINDS the defects of the last round, the artist model fixes them.

    spec_pipeline.py ... --eye on --eye-critic claude-fable-5-1@max [--eye-fixer opus]

Round r > 0 of eye_stage: before the artist is asked for the new DSL, the critic sees the concept, the boards of the model built in round r-1, the
numbers and that DSL, and answers {"defects": [{part, view, what, fix, severity 1-3}], "verdict": "continue"|"stop", "why", "resolved": [ids]}
(at most 12 defects, worst first). `resolved` marks which defects of the PREVIOUS list are gone from the render: the fix rate of the round.
The fixer (the stage's own model) gets the DSL, the defect list (ids d<r>.<n>) and the concept sheet, not the boards, and answers the whole
new DSL plus "fixed": [ids it says it dealt with]. A critic "stop" ends the loop (the stage's disaster guard still wins). After the last round
one audit call (no fixer) marks the defects left, so the last round has a fix rate too. Kept: eye/round-<r>/critic.json, eye/audit/critic.json.
`model@effort` in --eye-critic is `claude -p --model model --effort effort` (spec_pipeline.session_command)."""
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

ROOT = HERE.parents[1]
PROMPT = ROOT / "artifacts/model-sheets/prompts/eye-critic.md"
MAX_DEFECTS = 12
VERDICTS = ("continue", "stop")
VIEWS = ("front", "left", "back", "top", "bottom", "rts", "all")


class Invalid(ValueError):
    """The reply cannot be used (a ValueError: spec_pipeline.ask resends once with the reason)."""


def check_defect(i, d):
    if not isinstance(d, dict):
        raise Invalid(f"defect {i} is not an object")
    for k in ("part", "what", "fix"):
        if not isinstance(d.get(k), str) or not d[k].strip():
            raise Invalid(f"defect {i} has no '{k}' (a defect says what is wrong AND the concrete fix in DSL terms)")
    if d.get("view") not in VIEWS:
        raise Invalid(f"defect {i}: 'view' must be one of {', '.join(VIEWS)}")
    if d.get("severity") not in (1, 2, 3):
        raise Invalid(f"defect {i}: 'severity' must be 1, 2 or 3")


def parse(reply, prev_ids=()):
    """The reply as {defects (worst first, <= 12), verdict, why, resolved}; Invalid when it breaks the schema."""
    import spec_pipeline as SP
    try:
        doc = SP.json_object(reply)
    except ValueError as err:
        raise Invalid(f"not a JSON object: {err}") from None
    if doc.get("verdict") not in VERDICTS:
        raise Invalid("'verdict' must be 'continue' or 'stop'")
    defects = doc.get("defects")
    if not isinstance(defects, list):
        raise Invalid("'defects' must be a list")
    for i, d in enumerate(defects):
        check_defect(i, d)
    resolved = doc.get("resolved") or []
    if not isinstance(resolved, list) or any(x not in prev_ids for x in resolved):
        raise Invalid(f"'resolved' must be a list of ids from {list(prev_ids)}")
    ranked = sorted(defects, key=lambda d: -d["severity"])[:MAX_DEFECTS]
    return {"defects": ranked, "verdict": doc["verdict"], "why": str(doc.get("why", "")), "resolved": resolved}


def with_ids(defects, r):
    return [dict(d, id=f"d{r}.{i}") for i, d in enumerate(defects, 1)]


def defect_lines(defects):
    return "\n".join(f"- {d['id']} (severity {d['severity']}, {d['part']}, {d['view']}): {d['what']} FIX: {d['fix']}" for d in defects)


def prompt_of(unit, r, prev_dsl, ev_text, prev_defects, label):
    prev = ("Defects you listed last round (mark in \"resolved\" the ids that are GONE from the render now; leave out the ones still there, and list those "
            "again as new defects):\n" + defect_lines(prev_defects)) if prev_defects else "There was no earlier defect list: \"resolved\" is []."
    return (PROMPT.read_text().replace("{{name}}", unit["name"]).replace("{{race}}", unit["race"]).replace("{{role}}", unit["role"])
            .replace("{{round}}", str(r)).replace("{{label}}", label).replace("{{ev}}", ev_text).replace("{{prev}}", prev)
            .replace("{{dsl}}", json.dumps(prev_dsl, separators=(",", ":"))).replace("{{max}}", str(MAX_DEFECTS)))


def review(ask, unit, r, images, prev_dsl, ev_text, prev_defects, label, out_dir, usage=None):
    """One critic call on the model built in round r-1 (images: the sheet and the two boards). The parsed reply with ids and
    `fix_rate` (resolved / previous defects, None without any), kept as out_dir/critic.json. `usage`: the token counter to diff (spec_pipeline.USAGE)."""
    prev_ids = [d["id"] for d in prev_defects]
    prompt = prompt_of(unit, r, prev_dsl, ev_text, prev_defects, label)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "critic-prompt.md").write_text(prompt)
    before, t0 = dict(usage or {}), time.monotonic()
    reply = ask(prompt, images, lambda txt: parse(txt, prev_ids))
    doc = parse(reply, prev_ids)
    doc["defects"] = with_ids(doc["defects"], r)
    doc["fix_rate"] = round(len(doc["resolved"]) / len(prev_ids), 3) if prev_ids else None
    doc["of_previous"] = len(prev_ids)
    doc["seconds"] = round(time.monotonic() - t0, 1)
    doc["usage"] = {k: v - before.get(k, 0) for k, v in (usage or {}).items() if v - before.get(k, 0)}
    (out_dir / "critic.json").write_text(json.dumps(doc, indent=1))
    return doc


def fixer_note(doc):
    """What the artist is told instead of looking: the critic's list, to be appended to the round block."""
    return ("\n\nA STRONGER REVIEWER compared your last model with the concept and found these defects. Fix them: each fix is stated in terms of your "
            "pieces. Keep everything that is not listed. Do NOT reply stop. The boards are not given this round, only the concept sheet.\n"
            f"Reviewer's note: {doc['why']}\n{defect_lines(doc['defects'])}\n\n"
            "Reply with the COMPLETE new object as always, plus one more key \"fixed\": [the ids above that you changed].")
