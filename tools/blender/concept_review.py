#!/usr/bin/env python3
"""Concept round from the author's review file: only rejected units, each with its note, upgrades built on their predecessor.

    python3.14 tools/blender/concept_review.py <concept-review.json> --round review1 [--jobs 8]

mode edit: image-to-image of the unit's own sheet. mode redesign: a new prompt, on the predecessor's sheet when there is one.
Only sheet.jpg is drawn; the old sheets go to history/2026-10-31-<round>/<id>/ first, the variants wait for approval.
"""
import argparse
import concurrent.futures as cf
import json
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import roster_batch as R

ROOT = pathlib.Path(__file__).resolve().parents[2]
M = ROOT / "artifacts/model-sheets"
HIVE = ROOT / "artifacts/reference/hive"
SCHEMA = {"type": "object", "required": ["mode", "prompt"],
          "properties": {"mode": {"enum": ["edit", "redesign"]}, "prompt": {"type": "string"}}}
STYLE = (M / "prompts/STYLE-trench-crusade.txt").read_text()
RULES = """Rules from the author's review of the whole roster:
- The author's note is the order. It outranks the card, the lore and every rule below.
- Note says the model is great and only colours, a prop or a small thing is wrong: mode edit, change only that.
- Note says awful, wrong design, not a <thing>, check wc3, or asks for a different body: mode redesign, and follow the original closely.
- Creatures are creatures, never machines: no boats, robots, trees or furnaces on them. Dieselpunk is restrained: at most one small piece of gear; no backpacks, gas tanks, pots, seats, lanterns or stamps unless the note asks.
- Few props. Human units read dieselpunk, not medieval or templar. Tanks are chunky and cartoonish like WC3.
- Elementals have no two legs: the body is a single mass of its element that floats or joins the ground in one point. Water and fire read as that element in the whole body.
- Colour: not one colour for a whole race. Take this unit's colours from the original icon and print, several clearly different colours per unit, the race palette at most a trim. Night elves have purple skin, orcs green skin, trolls as in WC3.
- Tiers: a low tier looks smaller and weaker, an upgrade is visibly the SAME character as its predecessor, bigger and stronger, with better gear. Every view of a sheet shows the same character in the same pose.
- Proportions as in WC3: chunky game proportions, never chibi or big-headed, unless the note asks. Low detail: few large shapes, this becomes a low-poly model.
- Faces and limbs that the original has stay. All limbs present. The five-panel layout, grey background, flat coarse blockout style and no text stay.
"""


def source_lines(u, pred):
    refs = M / "refs" / u["id"]
    lines = [f"Read {refs / 'sheet.jpg'}: our current concept, rejected by the author."]
    for label, path in (("the original game model", HIVE / "renders" / f"{u['id']}.png"), ("the original icon", HIVE / "icons" / f"{u['id']}.png")):
        if path.exists():
            lines.append(f"Read {path}: {label}; prints can load broken, then trust the icon.")
    if pred:
        lines.append(f"Read {M / 'refs' / pred / 'sheet.jpg'}: its predecessor {pred}, the character this unit must visibly be, upgraded.")
    return "\n".join(lines)


def brief(u, pred, old_prompt):
    return (f"You revise the image prompt of one model sheet of a dieselpunk dark-fantasy low-poly RTS: unit {u['id']} {u['name']}, race {u['race']}, tier {u['tier']}.\n"
            f"AUTHOR'S NOTE: {u['note']}\n\n{RULES}\n{STYLE}\n{source_lines(u, pred)}\n\n"
            f"Return mode and prompt. For edit, the prompt is an edit instruction to an image model holding our current sheet: say exactly what changes and "
            f"that all else, the layout and every view stay; name the same change for all five views. For redesign, the prompt is the full new prompt: keep the layout "
            f"sentences of the old prompt, rewrite the subject in plain words and describe each panel."
            f"{' It will be drawn from the predecessor sheet, so state what stays and what grows.' if pred else ''}\n\nOLD PROMPT\n{old_prompt}\n")


def draw(u, pred, round_name, log):
    uid = u["id"]
    refs, prompts = M / "refs" / uid, M / "prompts" / uid
    old = next(iter(sorted(prompts.glob(f"unit-{uid}.txt"))), None)
    got = R.claude_json(brief(u, pred, old.read_text() if old else ""), SCHEMA, log)
    text = prompts / f"{round_name}-{uid}.txt"
    text.write_text(got["prompt"].strip() + "\n")
    base = refs / "sheet.jpg" if got["mode"] == "edit" else (M / "refs" / pred / "sheet.jpg" if pred else None)
    argv = [sys.executable, "generate.py", str(text), "--id", uid, "--out", f"refs/{uid}", "--name", "sheet-new"]
    if base:
        argv += ["--image", str(base.relative_to(M))]
    run = subprocess.run(argv, cwd=M, capture_output=True, text=True)
    if run.returncode:
        raise RuntimeError((run.stdout + run.stderr)[-220:].replace("\n", " "))
    return got["mode"]


def one(u, pred, round_name, tmp):
    uid = u["id"]
    keep = M / f"history/2026-10-31-{round_name}/{uid}"
    keep.mkdir(parents=True, exist_ok=True)
    refs = M / "refs" / uid
    for f in sorted(refs.glob("*")):
        if f.is_file() and f.name != "parts.json" and not (keep / f.name).exists():
            shutil.copy2(f, keep / f.name)
    log = tmp / f"{uid}.log"
    log.write_text("")
    try:
        mode = draw(u, pred, round_name, log)
    except Exception as e:                        # noqa: BLE001 - one bad unit must not stop the round
        return uid, f"FAILED {e}"
    (refs / "sheet-new.jpg").replace(refs / "sheet.jpg")
    for f in refs.glob("sheet*"):
        if f.name != "sheet.jpg":
            f.unlink()
    return uid, mode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("review")
    ap.add_argument("--round", default="review1")
    ap.add_argument("--jobs", type=int, default=8)
    args = ap.parse_args()
    review = json.loads(pathlib.Path(args.review).read_text())
    comp = {e["id"]: e for r in json.loads((ROOT / "data/compendium.json").read_text())["races"] for e in r["entries"]}
    todo = {u["id"]: u for u in review["rejected"] if u["kind"] == "unit"}

    def pred_of(uid):
        p = todo[uid]["base"] if "base" in todo[uid] else comp[uid].get("predecessorId")
        return p if p in comp and comp[p].get("kind") == "unit" and (M / "refs" / p / "sheet.jpg").exists() else None

    def depth(uid):
        p = pred_of(uid) if uid in todo else None
        return 1 + depth(p) if p in todo else 0

    tmp = pathlib.Path(sys.argv[0]).parent / "__review_logs"
    tmp = M / f"history/2026-10-31-{args.round}/_logs"
    tmp.mkdir(parents=True, exist_ok=True)
    for level in sorted({depth(u) for u in todo}):
        batch = [u for u in todo if depth(u) == level]
        print(f"level {level}: {len(batch)}", flush=True)
        with cf.ThreadPoolExecutor(args.jobs) as ex:
            for uid, res in ex.map(lambda x: one(todo[x], pred_of(x), args.round, tmp), batch):
                print(uid, res, flush=True)


if __name__ == "__main__":
    main()
