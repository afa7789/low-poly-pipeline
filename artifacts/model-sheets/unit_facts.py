#!/usr/bin/env python3
"""Print every fact needed to fill the model-sheet prompt template, for one id.

    python3 unit_facts.py n01X
    python3 unit_facts.py n01X n01N n00U

Sources: data/compendium.json (stats, tier, predecessor), reports/design/race-<key>.md
(the redesign paragraph), reports/design/00-art-bible.md §1.4 (the locked palette row).
Nothing here calls the image API.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DESIGN = ROOT / "reports" / "design"


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


def main(ids):
    idx = comp_index()
    for uid in ids:
        e = idx.get(uid)
        if not e:
            print(f"!! {uid}: not in the compendium")
            continue
        st = e["stats"]
        card_file, title, body = card_section(uid)
        redesign = re.search(r"\*\*(?:Low-poly redesign \(target\)|Redesign)\*\* — (.+)", body or "")
        pred = idx.get(e.get("predecessorId") or "", {})
        succ = [x for x in idx.values() if x.get("predecessorId") == uid]
        print(f"=== {uid} — {e['name']} ({e['_race']}, tier {e['tier']}, {e['kind']})")
        print(f"  card        : {card_file} :: {title}")
        print(f"  range       : {st.get('range')}   (null = melee)")
        print(f"  attack/armor: {st.get('attackType')} / {st.get('armorType')}   hp {st.get('hitPoints')}  cd {st.get('cooldown')}  dmg {st.get('damageMin')}-{st.get('damageMax')}")
        print(f"  chain       : {pred.get('id', '—')} -> {uid} -> {', '.join(x['id'] for x in succ) or '—'}")
        print(f"  palette     : {' | '.join(palette_row(e['_race'])) or 'see art bible §1.4'}")
        print(f"  redesign    : {(redesign.group(1) if redesign else '—')}")
        print()


if __name__ == "__main__":
    main(sys.argv[1:] or ["n01X"])
