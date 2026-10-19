#!/usr/bin/env python3
"""One unit, end to end: sheet -> spec (vision model) -> GLB -> gates -> turntable GIF.

    python3 tools/blender/spec_pipeline.py --id n01X --race Mech --name "Iron Golem" \\
        --sheet artifacts/model-sheets/draft2/n01X.jpg --model google/gemini-4-argon --tag argon

    python3 tools/blender/spec_pipeline.py --id hfoo --race Human --name Footman \\
        --sheet artifacts/model-sheets/draft2/hfoo.jpg --model claude-opus-5.5 --tag opus55 \\
        --budget 400-700 --out artifacts/model-sheets/draft4

Triangle budgets, WC3 SD standard (see PIPELINE.md §6):
    mass unit 400-700 · hero 900-1600 · standard building 600-800 · town hall / large 2000-3000

Writes <out>/specs/<tag>-<id>.json, <out>/glb/<tag>-<id>.glb, <out>/<tag>/<id>.gif and prints one
gate line: id, tag, tris, budget, materials, smear. Exit code 1 if any gate fails.
"""
import argparse
import base64
import json
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
SKILLS = pathlib.Path.home() / ".config" / "opencode" / "skills"
BONES = {"root", "pelvis", "spine", "head", "arm.L", "forearm.L", "arm.R", "forearm.R",
         "thigh.L", "shin.L", "foot.L", "thigh.R", "shin.R", "foot.R"}
KINDS, MATS = {"box", "cyl", "wheel"}, {"iron", "brass", "flame"}
BUDGETS = {"mass": (400, 700), "hero": (900, 1600), "building": (600, 800), "large": (2000, 3000)}

BRIEF = """You are a technical artist. The attached image is a 5-view turnaround sheet of ONE low-poly game unit: a {race} {name} (id {uid}), {role}, from a dieselpunk dark-fantasy RTS. Study the sheet carefully: proportions, the shape of every block, where the coloured parts are, how the limbs and props are built.

Write a Blender part spec for that exact character as a JSON object: {{"parts": [[bone, kind, dims, at, material, opts], ...]}}

Schema, exactly:
- bone: one of root, pelvis, spine, head, arm.L, forearm.L, arm.R, forearm.R, thigh.L, shin.L, foot.L, thigh.R, shin.R, foot.R
- kind: "box" | "cyl" | "wheel"
- dims: box = (width_x, height_y, depth_z) in metres; cyl = (radius, depth); wheel = (major_radius, tube_radius)
- at = (x, y, z) in metres: +y is UP, +z is FORWARD (towards the viewer in the front view), x is right. The figure stands on y=0 and is about {height} m tall.
- material: "iron", "brass" or "flame" - use the sheet's actual colour masses, not one flat grey
- opts: {{}} normally; {{"axis": "up"}} or {{"axis": "fwd"}} for cylinders; {{"rot": degrees}} rotates a part around the forward axis (wheels, spokes).

Budget: {budget} triangles, the Warcraft III standard-definition budget for this kind of unit. A box is 12 tris, a 12-sided cylinder about 44, a 10x4 wheel about 80. Use 25 to 45 parts, nothing below y = 0.

Parts are rigid-bound: each part follows the bone you name. Rig reference: the head bone runs 2.16 to 2.72 up, the arms hang from 2.02 to 0.90, the legs from 1.18 to 0.10. If the creature is not a biped, bind its mass to spine/pelvis and its limbs to the closest bones.

Rules: every part needs real volume; the silhouette must read at 32x32 pixels; match the big shapes first, small trims last.

Return ONLY the JSON object, no prose, no code fences."""


def api_key():
    cfg = pathlib.Path.home() / ".config" / "opencode" / "opencode.json"
    return json.loads(cfg.read_text())["provider"]["ppq"]["options"]["apiKey"]


def ask(model, brief, image_b64):
    body = {"model": model, "max_tokens": 9000, "temperature": 0.2,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": brief},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_b64}}]}]}
    req = urllib.request.Request("https://api.ppq.ai/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {api_key()}",
                                          "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=900))
    m = r["choices"][0]["message"]
    return m.get("content") or m.get("reasoning_content") or ""


def parse_spec(txt):
    txt = re.sub(r'\[\s*(root|pelvis|spine|head|arm\.[LR]|forearm\.[LR]|thigh\.[LR]|shin\.[LR]|foot\.[LR])\s*,',
                 r'["\1",', txt)
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        raise ValueError("no JSON in the reply")
    parts = json.loads(m.group(0)).get("parts")
    if not isinstance(parts, list) or not parts:
        raise ValueError("no parts array")
    for i, p in enumerate(parts):
        if len(p) != 6 or p[0] not in BONES or p[1] not in KINDS or p[4] not in MATS:
            raise ValueError(f"part {i} outside the schema: {p}")
        if p[3][1] < -0.01:
            raise ValueError(f"part {i} below the ground plane")
    return {"parts": parts}


def glb_stats(path):
    data = path.read_bytes()
    doc = json.loads(data[20:20 + int.from_bytes(data[12:16], "little")].decode("utf8", "ignore").rstrip("\0 "))
    tris = sum(doc["accessors"][p["indices"]]["count"] // 3
               for m in doc["meshes"] for p in m["primitives"])
    mats = [m["name"] for m in doc.get("materials", [])]
    return tris, mats, len(doc.get("skins", [])), len(doc.get("animations", []))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--race", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--role", default="game unit")
    ap.add_argument("--sheet", required=True, type=pathlib.Path)
    ap.add_argument("--model", default="google/gemini-4-argon")
    ap.add_argument("--tag", default="argon")
    ap.add_argument("--height", type=float, default=2.0)
    ap.add_argument("--kind", default="mass", choices=BUDGETS.keys())
    ap.add_argument("--out", type=pathlib.Path, default=ROOT / "artifacts/model-sheets/draft4")
    args = ap.parse_args()

    lo, hi = BUDGETS[args.kind]
    for d in ("specs", "glb", args.tag):
        (args.out / d).mkdir(parents=True, exist_ok=True)

    sheet = args.out / ".." / ".." / ".sheet.jpg"
    subprocess.run(["magick", str(args.sheet), "-resize", "1024x1024", "-quality", "88", str(sheet)], check=True)
    b64 = base64.b64encode(sheet.read_bytes()).decode()
    brief = BRIEF.format(race=args.race, name=args.name, uid=args.id, role=args.role,
                         height=args.height, budget=f"{lo} to {hi}")
    spec = parse_spec(ask(args.model, brief, b64))
    spec_path = args.out / "specs" / f"{args.tag}-{args.id}.json"
    spec_path.write_text(json.dumps(spec))
    sheet.unlink(missing_ok=True)

    glb = args.out / "glb" / f"{args.tag}-{args.id}.glb"
    build = subprocess.run(["blender", "-b", "-P", str(ROOT / "tools/blender/build_unit.py"),
                            "--", str(spec_path), str(glb)], capture_output=True, text=True)
    if not glb.exists():
        print(f"{args.id}\t{args.tag}\tBUILD FAILED\t{build.stderr[-200:]}")
        return 1
    smear = re.search(r"normal smear on \d+ flat faces \(([\d.]+)%", build.stdout + build.stderr)
    smear_pct = float(smear.group(1)) if smear else 0.0

    tris, mats, skins, anims = glb_stats(glb)
    mp4 = pathlib.Path(f"/tmp/{args.tag}-{args.id}.mp4")
    subprocess.run(["blender", "-b", "-P", str(ROOT / "tools/blender/turntable.py"),
                    "--", str(glb), str(mp4)], capture_output=True, text=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4),
                    "-vf", "fps=12,scale=380:-1:flags=neighbor", "-loop", "0",
                    str(args.out / args.tag / f"{args.id}.gif")], check=False)
    mp4.unlink(missing_ok=True)

    ok = lo <= tris <= hi and len(mats) == 3 and skins == 1 and anims == 4 and smear_pct <= 0.5
    print(f"{args.id}\t{args.tag}\ttris {tris}/{lo}-{hi}\tmats {len(mats)}\tskins {skins}\tanims {anims}\t"
          f"smear {smear_pct}%\t{'PASS' if ok else 'CHECK'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
