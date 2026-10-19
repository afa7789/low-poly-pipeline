#!/usr/bin/env python3
"""Closed-loop drafts: build -> five-view comparison -> Claude review -> the review
changes how the next model is built.

A draft is exactly that cycle. Each folder under artifacts/model-sheets/draftNN holds:
    n01X.glb            the model
    n01X.gif            turntable
    n01X-compare.png    concept sheet above our five views
    claude.txt          the review that produced the NEXT draft

    python3 tools/blender/draft_loop.py [count]
"""
import base64
import json
import pathlib
import re
import subprocess
import sys
import urllib.request

import make_drafts as MD   # BASE parts + the part-level improvements

ROOT = MD.ROOT
OUT = ROOT / "artifacts/model-sheets"
KEY = json.load(open(pathlib.Path.home() / ".config/opencode/opencode.json"))["provider"]["ppq"]["options"]["apiKey"]

OPS = {
    "neck": ("add a short neck under the valve wheel", MD.m_neck),
    "knuckles": ("split each fist into three knuckle blocks", MD.m_knuckles),
    "knees": ("add brass knee pucks", MD.m_knees),
    "boots": ("make the boots a wedge", MD.m_boots),
    "pelvis": ("widen the pelvis 22%", MD.m_pelvis),
    "deep": ("deepen the chest 30%", MD.m_deep),
    "taper": ("taper the upper arm at the shoulder", MD.m_taper),
    "rims": ("add a thin rim plate on each pauldron", MD.m_rims),
    "disc": ("push the chest disc 0.06 forward", MD.m_disc),
    "backplate": ("add a back plate", MD.m_backplate),
    "bigwheel": ("enlarge the valve wheel 18%", MD.m_bigwheel),
    "thickspokes": ("thicken the wheel spokes", MD.m_thickspokes),
    "pauldron_angle": ("angle the pauldrons out and up", MD.m_pauldron_angle),
    "legs": ("thicken the legs 18%", MD.m_legs),
    "forearms": ("thicken the forearms 12%", MD.m_forearms),
    "sunk": ("sink the head 0.10", MD.m_sunk),
    "chestring": ("add an iron ring around the chest disc", MD.m_chestring),
    "flame": ("enlarge the flame slit 25%", MD.m_flame),
    "feet_wide": ("widen the feet 12%", MD.m_feet_wide),
    "arms_out": ("move the arms 6% outward", MD.m_arms_out),
}
MENU = "\n".join(f"- {k}: {d}" for k, (d, _) in OPS.items())


def jpg(src, dst, size=760):
    subprocess.run(["magick", str(src), "-resize", f"{size}x{size}", "-quality", "84", str(dst)], check=True)
    return dst


def build(tag, recipe):
    spec = pathlib.Path("/tmp") / f"{tag}-spec.json"
    spec.write_text(json.dumps({"parts": recipe}, indent=1))
    vdir = OUT / tag
    vdir.mkdir(parents=True, exist_ok=True)
    glb = vdir / "n01X.glb"
    subprocess.run(["blender", "-b", "-P", "tools/blender/build_unit.py", "--", str(spec), str(glb),
                    "700", "nofuse", "700", "tex"], cwd=ROOT, capture_output=True)
    if not glb.exists():
        return None
    views = pathlib.Path("/tmp") / f"{tag}-views"
    subprocess.run(["blender", "-b", "-P", "tools/blender/render_unit.py", "--", str(glb), str(views)],
                   cwd=ROOT, capture_output=True)
    fs = [views / f"n01X-{v}.png" for v in ("front", "left", "back", "top", "bottom")]
    if all(f.exists() for f in fs):
        subprocess.run(["magick", *map(str, fs[:3]), "+append", str(views / "r1.png")], check=True)
        subprocess.run(["magick", "-size", "512x512", "xc:#9e9e9e", "/tmp/empty.png"], check=True)
        subprocess.run(["magick", str(fs[3]), str(fs[4]), "/tmp/empty.png", "+append", str(views / "r2.png")], check=True)
        subprocess.run(["magick", str(views / "r1.png"), str(views / "r2.png"), "-append", str(views / "sheet.png")], check=True)
        subprocess.run(["magick", str(MD.CONCEPT), str(views / "sheet.png"), "-append", "-resize", "1500x",
                        str(vdir / "n01X-compare.png")], check=True)
    turn = pathlib.Path("/tmp") / f"{tag}-turn"
    subprocess.run(["blender", "-b", "-P", "tools/blender/turntable_color.py", "--", str(glb), str(turn), "18", "420"],
                   cwd=ROOT, capture_output=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(turn / "orbit-%03d.png"),
                    "-vf", "fps=12,scale=420:-1:flags=lanczos", "-loop", "0", str(vdir / "n01X.gif")], check=True)
    return vdir


def review(compare_png, previous):
    a = base64.b64encode(pathlib.Path(jpg(MD.CONCEPT, "/tmp/r-tgt.jpg")).read_bytes()).decode()
    b = base64.b64encode(pathlib.Path(jpg(compare_png, "/tmp/r-cur.jpg", 900)).read_bytes()).decode()
    ask = f"""Images: [target concept sheet] then [our model: five views on top, the concept repeated below]. Previous score {previous}.
Pick the next TWO improvements from this exact menu (do not invent new ones):
{MENU}

Return ONLY JSON: {{"score": <0-10>, "ops": ["<key>", "<key>"], "note": "<12 words>"}}"""
    body = {"model": "anthropic/claude-opus-4.8", "max_tokens": 300,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "[target]"}, {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + a}},
                {"type": "text", "text": "[ours]"}, {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b}},
                {"type": "text", "text": ask}]}]}
    req = urllib.request.Request("https://api.ppq.ai/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=300))
    m = re.search(r"\{.*\}", r["choices"][0]["message"].get("content") or "", re.S)
    return json.loads(m.group(0)) if m else {}


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    recipe = json.loads(json.dumps(MD.BASE))
    used, score = set(), 4.6
    for n in range(1, count + 1):
        tag = f"draft{n:02d}"
        vdir = build(tag, recipe)
        if not vdir:
            print(tag, "BUILD FAILED")
            return
        res = review(vdir / "n01X-compare.png", score)
        score = float(res.get("score", score))
        ops = [o for o in res.get("ops", []) if o in OPS]
        (vdir / "claude.txt").write_text(
            f"score: {score}\nops: {ops}\nnote: {res.get('note', '')}\n")
        for o in ops:
            if o not in used:
                OPS[o][1](recipe)
                used.add(o)
        print(f"{tag} claude {score:.1f} -> next adds {ops} | {res.get('note', '')}")


if __name__ == "__main__":
    main()
