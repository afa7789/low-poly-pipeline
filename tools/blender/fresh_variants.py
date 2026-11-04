#!/usr/bin/env python3
"""Variant prompts written from each approved sheet, so old prompts cannot pull the old design back.

    python3.14 tools/blender/fresh_variants.py <ids-file> [--jobs 8]

Old variant prompts and parts data move to history/2026-11-01-pre-variants/<id>/, then roster_batch redraws them.
"""
import argparse
import concurrent.futures as cf
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import roster_batch as R

M = R.ROOT / "artifacts/model-sheets"
KEEP = M / "history/2026-11-01-pre-variants"
SCHEMA = {"type": "object", "required": ["unit_hard", "unit_hard_clean", "unit_props"],
          "properties": {k: {"type": ["string", "null"]} for k in ("unit_hard", "unit_hard_clean", "unit_props")}}


def brief(uid, name, race, rig, templates):
    return (f"Read {M / 'refs' / uid / 'sheet.jpg'}: the author's approved sheet of {uid} ({race} {name}, rig family {rig}). Fill the three templates below "
            f"strictly from what that image shows. Never invent or recall any other design. Keep every template sentence that is not a {{placeholder}} verbatim; "
            f"replace each placeholder and each <angle-bracket> instruction with concrete text. Keep every colour you see. Props are only what the image shows, "
            f"at most 4; when the unit has none set unit_props to null and say so.\n\n"
            + "".join(f"TEMPLATE {k}\n{v}\n\n" for k, v in templates.items()))


def one(row, templates):
    uid, name, race, rig = row
    prompts, refs = M / "prompts" / uid, M / "refs" / uid
    keep = KEEP / uid
    keep.mkdir(parents=True, exist_ok=True)
    log = keep / "fresh.log"
    log.write_text("")
    try:
        got = R.claude_json(brief(uid, name, race, rig, templates), SCHEMA, log)
    except Exception as e:                        # noqa: BLE001 - one bad unit must not stop the batch
        return uid, f"FAILED {e}"
    for f in [*prompts.glob("unit-hard*.txt"), *prompts.glob("unit-props.txt"), *prompts.glob(f"unit-{uid}-*.txt"), prompts / "props.json",
              refs / "parts.json", refs / "sheet.json", refs / "parts-reply.json", refs / "parts-overlay.png"]:
        if f.exists():
            shutil.move(str(f), str(keep / f.name))
    for key, suffix in (("unit_hard", "-hard"), ("unit_hard_clean", "-hard-clean"), ("unit_props", "-props")):
        if got.get(key):
            (prompts / f"unit-{uid}{suffix}.txt").write_text(got[key].strip() + "\n")
    return uid, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids")
    ap.add_argument("--jobs", type=int, default=8)
    args = ap.parse_args()
    comp = {e["id"]: e for r in __import__("json").loads((R.ROOT / "data/compendium.json").read_text())["races"] for e in r["entries"]}
    templates = {k: (R.PROMPTS / f"00-template-{k}.txt").read_text() for k in ("unit-hard", "unit-hard-clean", "props")}
    rows = []
    for uid in pathlib.Path(args.ids).read_text().split(","):
        e = comp[uid.strip()]
        rows.append((e["id"], e["name"], e["race"], R.rig_of(e["id"], e["name"])))
    with cf.ThreadPoolExecutor(args.jobs) as ex:
        for uid, res in ex.map(lambda r: one(r, templates), rows):
            print(uid, res, flush=True)


if __name__ == "__main__":
    main()
