#!/usr/bin/env python3
"""Textured 6-view prints of the WC3 model behind every unit and building (reference only, never shipped).

    python3.14 tools/blender/wc3_ref_renders.py <map.w3x> [--jobs 4]

Model of an id: umdl of war3map.w3u, else the base id's `file` in unitskin.txt. Files: the map's own MPQ first,
then the classic (SD) tree of the Hive CDN. Prints land in artifacts/reference/hive/renders/<id>.png.
"""
import argparse
import concurrent.futures as cf
import json
import pathlib
import re
import struct
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import w3x_models as W

ROOT = pathlib.Path(__file__).resolve().parents[2]
HIVE = ROOT / "artifacts/reference/hive"
OUT = ROOT / "artifacts/model-sheets/wc3-model-map.json"
CDN = "https://cdn.hiveworkshop.com/assets/wc3/"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"


def fetch(rel):
    p = subprocess.run(["curl", "-s", "-m", "60", "-L", "-A", UA, CDN + rel], capture_output=True).stdout
    return p if p[:4] in (b"MDLX", b"BLP1", b"BLP2", b"DDS ") else None


def parse_w3u():
    b = (ROOT / "artifacts/w3x/war3map.w3u").read_bytes()
    pos = [4]

    def i32():
        pos[0] += 4
        return struct.unpack_from("<i", b, pos[0] - 4)[0]

    def s4():
        pos[0] += 4
        return b[pos[0] - 4:pos[0]].decode("latin1")

    out = {}
    for _ in range(2):
        for _ in range(i32()):
            base, new = s4(), s4()
            mods = {}
            for _ in range(i32()):
                i32()
                for _ in range(i32()):
                    field, kind = s4(), i32()
                    if kind >= 3:
                        end = b.index(0, pos[0])
                        value = b[pos[0]:end].decode("utf8", "replace")
                        pos[0] = end + 1
                    else:
                        value = i32()
                    s4()
                    mods.setdefault(field, value)
            out[new if new != "\0\0\0\0" else base] = (base, mods)
    return out


def skin_files():
    text = subprocess.run(["curl", "-s", "-m", "60", "-L", "-A", UA, CDN + "war3.w3mod/_hd.w3mod/units/unitskin.txt"],
                          capture_output=True).stdout.decode("utf8", "replace")
    if "[Hamg]" not in text:
        text = subprocess.run(["curl", "-s", "-m", "60", "-L", "-A", UA, "-e", "https://www.hiveworkshop.com/",
                               "https://www.hiveworkshop.com/casc-contents?path=units/unitskin.txt"],
                              capture_output=True).stdout.decode("utf8", "replace")
    files, cur = {}, None
    for line in text.splitlines():
        head = re.match(r"\[(\w{4})\]", line)
        if head:
            cur = head.group(1)
            continue
        m = re.match(r"file(:sd|:hd)?=(.+)", line.strip(), re.I)
        if cur and m:
            files.setdefault(cur, {})[m.group(1) or ""] = m.group(2).strip()
    return {k: v.get("") or v.get(":sd") or v.get(":hd") for k, v in files.items()}


def textures(b):
    pos, out = 4, []
    while pos + 8 <= len(b):
        n = struct.unpack_from("<I", b, pos + 4)[0]
        if b[pos:pos + 4] == b"TEXS":
            out += [b[i + 4:i + 264].split(b"\0")[0].decode("latin1") for i in range(pos + 8, pos + 8 + n, 268)]
        pos += 8 + n
    return [t for t in out if t]


def get_model(mpq, mdl):
    stem = mdl[:-4] if mdl.lower().endswith((".mdl", ".mdx")) else mdl
    data = mpq.read(stem + ".mdx")
    if data:
        return data
    rel = stem.replace("\\", "/").lower() + ".mdx"
    return fetch("war3.w3mod/" + rel) or fetch("war3.w3mod/_hd.w3mod/" + rel)


def get_textures(mpq, data):
    folder = HIVE / "tex/custom"
    for t in textures(data):
        s = pathlib.PureWindowsPath(t).stem.lower()
        if list(folder.glob(glob_safe(s) + ".*")):
            continue
        rel = str(pathlib.PureWindowsPath(t).with_suffix("")).replace("\\", "/").lower()
        blob = mpq.read(t) or fetch(f"war3.w3mod/{rel}.blp") or fetch(f"war3.w3mod/{rel}.dds") or fetch(f"war3.w3mod/_hd.w3mod/{rel}.dds")
        if blob:
            (folder / (s + (".dds" if blob[:3] == b"DDS" else ".blp"))).write_bytes(blob)


def glob_safe(s):
    return re.sub(r"[\[\]*?]", "?", s)


def render(uid):
    done = subprocess.run([sys.executable, "tools/blender/hive_sheet.py", "render", uid], cwd=ROOT, capture_output=True, text=True)
    return uid, done.returncode, (done.stdout + done.stderr)[-160:].replace("\n", " ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("map")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--ids", default="", help="comma-separated ids outside the compendium (summons, perks) to add, from war3map.w3u")
    args = ap.parse_args()
    W._table()
    mpq = W.Map(args.map)
    w3u, skin = parse_w3u(), skin_files()
    comp = json.loads((ROOT / "data/compendium.json").read_text())
    rows = json.loads(OUT.read_text()) if OUT.exists() else {}
    for uid in filter(None, args.ids.split(",")):
        base, mods = w3u.get(uid, (uid, {}))
        rows[uid] = {"name": mods.get("unam") or uid, "kind": "unit", "race": None, "base": base,
                     "mdl": mods.get("umdl") or skin.get(base), "source": "none"}
    for race in comp["races"]:
        for e in race["entries"]:
            if e.get("kind") not in ("unit", "building"):
                continue
            base, mods = w3u.get(e["id"], (e["id"], {}))
            rows[e["id"]] = {"name": e["name"], "kind": e["kind"], "race": e.get("race"), "base": base,
                             "mdl": mods.get("umdl") or skin.get(base), "source": "none"}
    todo = []
    for uid, r in rows.items():
        if not r["mdl"] or r["mdl"] == "no_model.mdl":
            continue
        dst = HIVE / "mdx" / f"{uid}.mdx"
        data = dst.read_bytes() if dst.exists() else get_model(mpq, r["mdl"])
        if not data:
            continue
        dst.write_bytes(data)
        get_textures(mpq, data)
        r["source"] = "ok"
        if not (HIVE / "renders" / f"{uid}.png").exists():
            todo.append(uid)
    OUT.write_text(json.dumps(rows, indent=1) + "\n")
    print(len(rows), "ids;", sum(r["source"] == "ok" for r in rows.values()), "models;", len(todo), "to render", flush=True)
    with cf.ThreadPoolExecutor(args.jobs) as ex:
        for uid, code, tail in ex.map(render, todo):
            print(uid, "ok" if code == 0 else f"FAIL {tail}", flush=True)


if __name__ == "__main__":
    main()
