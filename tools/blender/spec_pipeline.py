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
KINDS, MATS = {"box", "cyl", "wheel", "prism", "dome"}, {"iron", "brass", "flame"}
BUDGETS = {"mass": (400, 700), "hero": (900, 1600), "building": (600, 800), "large": (2000, 3000)}

BRIEF = """You are a technical artist building a low-poly game unit in the style of classic Warcraft III. The attached image is a 5-view turnaround of ONE unit: a {race} {name} (id {uid}), {role}, from a dieselpunk dark-fantasy RTS. Study the sheet: proportions, the shape of every mass, where the coloured parts are, how the limbs and props are built.

Write a Blender part spec as a JSON object: {{"parts": [[bone, kind, dims, at, material, opts], ...]}}

Kinds and dims, exactly:
- "prism": a tapered n-gon tube - THE limb and torso primitive. dims = (radius_bottom, radius_top, height). opts {{"sides": 6 or 8, "axis": "up" | "fwd"}}. Use a smaller radius_top so the limb tapers away from the body.
- "dome": a closed dome for shoulders, helmet crown, knee and elbow caps. dims = (radius, height). opts {{"sides": 8, "top": 0.2 to 0.4}}.
- "box": ONLY for flat plates, boots, shields and weapon heads. dims = (width_x, height_y, depth_z). Never for a limb.
- "cyl": a straight tube, only when a part is genuinely cylindrical. dims = (radius, depth). opts {{"axis": "up" | "fwd"}}.
- "wheel": a torus rim. dims = (major_radius, tube_radius).
- at = (x, y, z) in metres: +y is UP, +z is FORWARD (towards the viewer in the front view), x is right. The unit stands on y = 0, about {height} m tall.
- material: "iron", "brass" or "flame" - use the sheet's real colour masses.

RIG TABLE - place every part ON these segments. The "at" of a part must be the segment
MIDPOINT, and its length (prism height / cyl depth / box height) must be 105 to 115 percent of
the segment length, so consecutive parts overlap and the body stays connected:

{bones}

FORM RULES, non-negotiable - these are what keep the model from reading as Minecraft:
1. No limb is a box. Thighs, shins, upper arms, forearms, necks and torso are prisms with 6 or 8 sides and a taper along their length.
2. The torso is wider at the shoulders than at the waist (a prism, or two stacked prisms). It is never a cuboid.
3. Shoulders, helmet crown, knee caps and elbows are domes, not blocks.
4. Boxes may be at most a third of the parts, and only as flat plates, boots, shields or weapon heads.
5. Nothing is axis-aligned: arms sit 10 to 20 degrees out from the body and slightly bent at the elbow; feet turn 8 to 12 degrees outward.
6. The silhouette is asymmetric: one arm carries the main prop, the other stays free or carries a smaller one.
7. Use 22 to 28 parts, and end near {budget} triangles (prism about 28, dome about 28, box 12, cyl 44). Nothing below y = 0.
8. Joints overlap: every limb segment overlaps its neighbour by at least 10 percent of its length, so no gap opens when the rig rotates.
9. Never lock a joint straight: elbows and knees sit 2 to 4 degrees off the axis (blender-rigging: pre-bend 1 to 3 degrees).
10. Chamfer every edge the silhouette reads, at about 0.5 percent of the unit height; no razor edges, no feature thinner than twice that chamfer.
11. Heroic mass: two thirds of the volume in torso and shoulders, hands and feet oversized (that proportion is what reads at 32 px).
12. Feet are planted flat on y = 0, wider than the shin, and centred under the body (blender-rigging model_check).
13. The front silhouette must still read as one black shape at 32 x 32 pixels; if a part only works with colour, it is decoration, not form.
14. Keep flat faces planar and quad-based; no n-gon with a hole, no geometry that only exists to add a bevel.
15. DETAIL LIVES IN THE TEXTURE, NOT THE GEOMETRY (lowpoly-style skill): no micro-bevels, no weighted normals, no subdivision. Surface is flat-shaded or auto-smooth at 60 degrees or more.
16. No face that does not change the silhouette; merge coplanar faces. If a feature would only read in colour, leave it to the atlas.
17. Hands are mitts - no fingers. Feet are wedges. Fur, cloth, spikes and fangs are flat cards, never modelled strands.
18. Mirror what can be mirrored (arm and leg parts are duplicated across x); asymmetry comes from props, not from different limbs.
19. Separate placed parts are allowed - classic WC3 uses them (ghoul claws, back spikes) - as long as each one overlaps the body mass and the union reads as one silhouette.
20. One 256 to 512 pixel atlas per unit (1024 only for a hero). Model the large forms the atlas will describe, nothing finer.

CHUNKIFY - the Blizzard house style (Samwise Didier, WC3 art direction):
21. Exaggerate what carries identity: oversized hands, oversized shoulders, oversized weapon. A limb is never thinner than a sixth of the torso width.
22. Everything is thick. No zero-thickness plane: a plate or a cape is a slab with volume, and its corners are cut so primitive lighting catches the edge.
23. Reserve one big flat zone for team colour, about 10 to 15 percent of the visible surface (pauldron, shield, banner). Never put it on the face or on a small part.
24. Angle the main prop outward from the body, so the silhouette stays readable when units overlap in a fight.
25. The unit must be identifiable as one black shape from the RTS camera (high, top-down, about 35 degrees), not only from the front.

Parts are rigid-bound: each part follows the bone you name. Rig reference: the head bone runs 2.16 to 2.72 up, the arms hang from 2.02 to 0.90, the legs from 1.18 to 0.10. If the creature is not a biped, bind its mass to spine/pelvis and its limbs to the closest bones.

The silhouette must read at 32x32 pixels: big shapes first, small trims last. Return ONLY the JSON object, no prose, no code fences."""


BONES_TABLE = [
    ("root", (0, 0, 0), (0, 0.3, 0)), ("pelvis", (0, 1.20, 0), (0, 1.50, 0)),
    ("spine", (0, 1.50, 0), (0, 2.16, 0)), ("head", (0, 2.16, 0), (0, 2.72, 0)),
    ("arm.L", (0.78, 2.02, 0), (0.78, 1.40, 0)), ("forearm.L", (0.78, 1.40, 0), (0.78, 0.90, 0)),
    ("arm.R", (-0.78, 2.02, 0), (-0.78, 1.40, 0)), ("forearm.R", (-0.78, 1.40, 0), (-0.78, 0.90, 0)),
    ("thigh.L", (0.28, 1.18, 0), (0.28, 0.56, 0)), ("shin.L", (0.28, 0.56, 0), (0.28, 0.10, 0)),
    ("foot.L", (0.28, 0.10, 0), (0.28, 0.06, 0.55)),
    ("thigh.R", (-0.28, 1.18, 0), (-0.28, 0.56, 0)), ("shin.R", (-0.28, 0.56, 0), (-0.28, 0.10, 0)),
    ("foot.R", (-0.28, 0.10, 0), (-0.28, 0.06, 0.55)),
]


def rig_table():
    lines = []
    for name, head, tail in BONES_TABLE:
        mid = tuple((head[i] + tail[i]) / 2 for i in range(3))
        length = sum((tail[i] - head[i]) ** 2 for i in range(3)) ** 0.5
        lines.append(f"  {name:10} head {head} tail {tail} midpoint {tuple(round(v, 2) for v in mid)} length {length:.2f}")
    return "\n".join(lines)


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


ALIASES = {"upper_arm.L": "arm.L", "upper_arm.R": "arm.R", "lower_arm.L": "forearm.L",
           "lower_arm.R": "forearm.R", "forearm.L": "forearm.L", "forearm.R": "forearm.R",
           "chest": "spine", "torso": "spine", "hips": "pelvis", "hip": "pelvis",
           "neck": "head", "hand.L": "forearm.L", "hand.R": "forearm.R",
           "shoulder.L": "arm.L", "shoulder.R": "arm.R"}


def normalise(parts):
    out = []
    for p in parts:
        p = list(p)
        p[0] = ALIASES.get(p[0], p[0])
        if isinstance(p[5], dict):
            opts = dict(p[5])
            if not isinstance(opts.get("rot", 0), (int, float)):
                opts.pop("rot", None)
            p[5] = opts
        out.append(p)
    return out


def parse_spec(txt):
    txt = re.sub(r'\[\s*(root|pelvis|spine|head|arm\.[LR]|forearm\.[LR]|thigh\.[LR]|shin\.[LR]|foot\.[LR])\s*,',
                 r'["\1",', txt)
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        raise ValueError("no JSON in the reply")
    parts = normalise(json.loads(m.group(0)).get("parts"))
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
                         height=args.height, budget=f"{lo} to {hi}", bones=rig_table())
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
