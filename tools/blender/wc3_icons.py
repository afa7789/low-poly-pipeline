#!/usr/bin/env python3
"""Command-card icon of every unit and building, for reference only: python3.14 tools/blender/wc3_icons.py <map.w3x>"""
import concurrent.futures as cf
import io
import json
import pathlib
import subprocess
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import w3x_models as W

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/reference/hive/icons"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"


def casc(path):
    got = subprocess.run(["curl", "-s", "-m", "40", "-L", "-A", UA, "-e", "https://www.hiveworkshop.com/",
                          f"https://www.hiveworkshop.com/casc-contents?path={path}"], capture_output=True).stdout
    return got if got[:4] in (b"BLP1", b"BLP2", b"DDS ") else None


def main():
    W._table()
    mpq = W.Map(sys.argv[1])
    OUT.mkdir(parents=True, exist_ok=True)
    comp = json.loads((ROOT / "data/compendium.json").read_text())
    rows = [(e["id"], pathlib.Path(e["iconPath"]).stem) for r in comp["races"] for e in r["entries"]
            if e.get("kind") in ("unit", "building") and e.get("iconPath")]

    def one(row):
        uid, stem = row
        if (OUT / f"{uid}.png").exists():
            return True
        blob = casc(f"replaceabletextures/commandbuttons/{stem}.dds")
        if blob is None:
            try:
                blob = mpq.read(f"ReplaceableTextures\\CommandButtons\\{stem}.blp") or mpq.read(f"war3mapImported\\{stem}.blp")
            except Exception:                     # noqa: BLE001 - a broken map entry is a missing icon
                blob = None
        if blob is None:
            return False
        Image.open(io.BytesIO(blob)).convert("RGB").save(OUT / f"{uid}.png")
        return True

    with cf.ThreadPoolExecutor(8) as ex:
        done = list(ex.map(one, rows))
    print(sum(done), "of", len(rows))
    print("missing", [r for r, ok in zip(rows, done) if not ok][:30])


if __name__ == "__main__":
    main()
