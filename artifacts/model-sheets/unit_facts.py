#!/usr/bin/env python3
"""Print every fact needed to fill the model-sheet prompt template, for one id.

    python3 unit_facts.py n01X
    python3 unit_facts.py n01X n01N n00U
    python3 unit_facts.py --emit-prompt n01X      # write prompts/<id>/unit*.txt stubs

Sources: data/compendium.json (stats, tier, predecessor), reports/design/race-<key>.md
(the redesign paragraph), reports/design/00-art-bible.md §1.4 (the locked palette row).
Nothing here calls the image API.
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DESIGN = ROOT / "reports" / "design"
PROMPTS = ROOT / "artifacts/model-sheets" / "prompts"


def comp_index():
    d = json.loads((ROOT / "data" / "compendium.json").read_text())
    idx = {}
    for race in d["races"]:
        for e in race["entries"]:
            e["_race"] = race["name"]
            idx[e["id"]] = e
    return idx


def card_section(uid):
    for f in sorted(DESIGN.glob("race-*.md")):
        txt = f.read_text()
        m = re.search(rf"\n### `{re.escape(uid)}` — (.+?)\n(.*?)(?=\n### |\n## |\Z)", txt, re.S)
        if m:
            return f.name, m.group(1).strip(), m.group(2).strip()
    return None, None, None


def palette_row(race_name):
    txt = (DESIGN / "00-art-bible.md").read_text()
    for line in txt.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0] == race_name:
            return [c for c in cells[1:] if c and c != "—"]
    return []


def facts(uid):
    idx = comp_index()
    e = idx.get(uid)
    if not e:
        return None
    st = e["stats"]
    card_file, title, body = card_section(uid)
    redesign = re.search(r"\*\*(?:Low-poly redesign \(target\)|Redesign)\*\* — (.+)", body or "")
    pred = idx.get(e.get("predecessorId") or "", {})
    succ = [x for x in idx.values() if x.get("predecessorId") == uid]
    return {
        "uid": uid, "name": e["name"], "race": e["_race"], "tier": e["tier"],
        "kind": e["kind"], "card": f"{card_file} :: {title}",
        "range": st.get("range"), "attack": st.get("attackType"), "armor": st.get("armorType"),
        "hp": st.get("hitPoints"), "cd": st.get("cooldown"),
        "dmg": f"{st.get('damageMin')}-{st.get('damageMax')}",
        "chain": f"{pred.get('id', '—')} -> {uid} -> {', '.join(x['id'] for x in succ) or '—'}",
        "palette": " | ".join(palette_row(e["_race"])) or "see art bible §1.4",
        "redesign": redesign.group(1) if redesign else "—",
    }


def main(ids):
    for f in ids:
        d = facts(f)
        if not d:
            print(f"!! {f}: not in the compendium")
            continue
        print(f"=== {d['uid']} — {d['name']} ({d['race']}, tier {d['tier']}, {d['kind']})")
        print(f"  card        : {d['card']}")
        print(f"  range       : {d['range']}   (null = melee)")
        print(f"  attack/armor: {d['attack']} / {d['armor']}   hp {d['hp']}  cd {d['cd']}  dmg {d['dmg']}")
        print(f"  chain       : {d['chain']}")
        print(f"  palette     : {d['palette']}")
        print(f"  redesign    : {d['redesign']}")
        print()


def emit_prompt(uid):
    d = facts(uid)
    if not d:
        sys.exit(f"{uid}: not in the compendium")
    out = PROMPTS / uid
    out.mkdir(parents=True, exist_ok=True)
    for base in ("unit", "unit-hard", "unit-hard-clean", "unit-props"):
        path = out / f"{base}.txt"
        path.write_text(
            f"# {base} prompt for {uid} ({d['name']}, {d['race']})\n"
            f"# range={d['range']} palette={d['palette']}\n"
            f"# redesign: {d['redesign']}\n"
            f"# Fill from template artifacts/model-sheets/draft2/prompts/00-template-{base.replace('unit', 'unit')}.txt\n")
        print(f"{path}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--emit-prompt", action="store_true",
                    help="write prompts/<id>/{unit,unit-hard,unit-hard-clean,unit-props}.txt stubs")
    args = ap.parse_args()
    if args.emit_prompt:
        for uid in args.ids or ["n01X"]:
            emit_prompt(uid)
    else:
        main(args.ids or ["n01X"])
