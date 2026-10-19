#!/usr/bin/env python3
"""Build 20 cumulative drafts of one unit: GLB + turntable GIF + a five-view comparison
PNG with the concept sheet above our model. The improvement of each draft is chosen
before it is built; no spec files are kept in the repo.

    python3 tools/blender/make_drafts.py [--only draftNN]
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/model-sheets/drafts"
CONCEPT = ROOT / "artifacts/model-sheets/draft2/n01X.jpg"
BASE = [
 [
  "spine",
  "prism",
  [
   0.42,
   0.48,
   0.26
  ],
  [
   0,
   1.52,
   0
  ],
  "iron",
  {
   "sides": 8
  }
 ],
 [
  "spine",
  "box",
  [
   1.128,
   0.7,
   1.0304
  ],
  [
   0,
   1.94,
   0
  ],
  "iron",
  {}
 ],
 [
  "spine",
  "cyl",
  [
   0.25,
   0.1
  ],
  [
   0,
   1.98,
   0.3
  ],
  "brass",
  {
   "axis": "fwd"
  }
 ],
 [
  "spine",
  "box",
  [
   0.13,
   0.17,
   0.06
  ],
  [
   0,
   1.62,
   0.29
  ],
  "flame",
  {}
 ],
 [
  "pelvis",
  "prism",
  [
   0.32,
   0.36,
   0.26
  ],
  [
   0,
   1.3,
   0
  ],
  "brass",
  {
   "sides": 8
  }
 ],
 [
  "pelvis",
  "box",
  [
   0.58,
   0.16,
   0.46
  ],
  [
   0,
   1.14,
   0
  ],
  "iron",
  {}
 ],
 [
  "head",
  "prism",
  [
   0.12,
   0.1,
   0.3
  ],
  [
   0,
   2.28,
   0
  ],
  "iron",
  {
   "sides": 6
  }
 ],
 [
  "head",
  "wheel",
  [
   0.45499999999999996,
   0.078
  ],
  [
   0,
   2.6,
   0
  ],
  "brass",
  {}
 ],
 [
  "head",
  "box",
  [
   0.8580000000000001,
   0.078,
   0.078
  ],
  [
   0,
   2.6,
   0
  ],
  "brass",
  {
   "rot": 0
  }
 ],
 [
  "head",
  "box",
  [
   0.8580000000000001,
   0.078,
   0.078
  ],
  [
   0,
   2.6,
   0
  ],
  "brass",
  {
   "rot": 60
  }
 ],
 [
  "head",
  "box",
  [
   0.8580000000000001,
   0.078,
   0.078
  ],
  [
   0,
   2.6,
   0
  ],
  "brass",
  {
   "rot": 120
  }
 ],
 [
  "arm.L",
  "dome",
  [
   0.36,
   0.4
  ],
  [
   0.54,
   2.04,
   0
  ],
  "brass",
  {
   "sides": 8,
   "top": 0.5,
   "rot": [
    0,
    -15,
    25
   ]
  }
 ],
 [
  "arm.L",
  "prism",
  [
   0.19,
   0.22,
   0.42
  ],
  [
   0.72,
   1.76,
   0.02
  ],
  "iron",
  {
   "sides": 6,
   "rot": [
    3.0,
    0,
    12.0
   ]
  }
 ],
 [
  "forearm.L",
  "prism",
  [
   0.21,
   0.24,
   0.5
  ],
  [
   0.8,
   1.36,
   0.06
  ],
  "iron",
  {
   "sides": 6,
   "rot": [
    15,
    0,
    10
   ]
  }
 ],
 [
  "forearm.L",
  "box",
  [
   0.5,
   0.44,
   0.52
  ],
  [
   0.82,
   1.02,
   0.14
  ],
  "brass",
  {
   "rot": [
    10,
    0,
    0
   ]
  }
 ],
 [
  "forearm.L",
  "dome",
  [
   0.34,
   0.28
  ],
  [
   0.82,
   1.14,
   0.14
  ],
  "brass",
  {
   "sides": 8,
   "top": 0.4
  }
 ],
 [
  "arm.R",
  "dome",
  [
   0.36,
   0.4
  ],
  [
   -0.54,
   2.04,
   0
  ],
  "brass",
  {
   "sides": 8,
   "top": 0.5,
   "rot": [
    0,
    15,
    -25
   ]
  }
 ],
 [
  "arm.R",
  "prism",
  [
   0.19,
   0.22,
   0.42
  ],
  [
   -0.72,
   1.76,
   0.02
  ],
  "iron",
  {
   "sides": 6,
   "rot": [
    3.0,
    0,
    12.0
   ]
  }
 ],
 [
  "forearm.R",
  "prism",
  [
   0.21,
   0.24,
   0.5
  ],
  [
   -0.8,
   1.36,
   0.06
  ],
  "iron",
  {
   "sides": 6,
   "rot": [
    15,
    0,
    -10
   ]
  }
 ],
 [
  "forearm.R",
  "box",
  [
   0.5,
   0.44,
   0.52
  ],
  [
   -0.82,
   1.02,
   0.14
  ],
  "brass",
  {
   "rot": [
    10,
    0,
    0
   ]
  }
 ],
 [
  "forearm.R",
  "dome",
  [
   0.34,
   0.28
  ],
  [
   -0.82,
   1.14,
   0.14
  ],
  "brass",
  {
   "sides": 8,
   "top": 0.4
  }
 ],
 [
  "thigh.L",
  "prism",
  [
   0.21970000000000003,
   0.30419999999999997,
   0.52
  ],
  [
   0.34,
   0.94,
   0
  ],
  "iron",
  {
   "sides": 6
  }
 ],
 [
  "shin.L",
  "prism",
  [
   0.2535,
   0.18590000000000004,
   0.46799999999999997
  ],
  [
   0.37,
   0.54,
   0
  ],
  "iron",
  {
   "sides": 6
  }
 ],
 [
  "foot.L",
  "box",
  [
   0.24,
   0.1,
   0.28
  ],
  [
   0.38,
   0.2,
   0.04
  ],
  "brass",
  {}
 ],
 [
  "foot.L",
  "box",
  [
   0.42,
   0.16,
   0.58
  ],
  [
   0.38,
   0.08,
   0.14
  ],
  "iron",
  {}
 ],
 [
  "thigh.R",
  "prism",
  [
   0.21970000000000003,
   0.30419999999999997,
   0.52
  ],
  [
   -0.34,
   0.94,
   0
  ],
  "iron",
  {
   "sides": 6
  }
 ],
 [
  "shin.R",
  "prism",
  [
   0.2535,
   0.18590000000000004,
   0.46799999999999997
  ],
  [
   -0.37,
   0.54,
   0
  ],
  "iron",
  {
   "sides": 6
  }
 ],
 [
  "foot.R",
  "box",
  [
   0.24,
   0.1,
   0.28
  ],
  [
   -0.38,
   0.2,
   0.04
  ],
  "brass",
  {}
 ],
 [
  "foot.R",
  "box",
  [
   0.42,
   0.16,
   0.58
  ],
  [
   -0.38,
   0.08,
   0.14
  ],
  "iron",
  {}
 ],
 [
  "spine",
  "cyl",
  [
   0.32,
   0.05
  ],
  [
   0,
   1.98,
   0.27
  ],
  "iron",
  {
   "axis": "fwd"
  }
 ]
]


def box(p, bone, dims, at, mat="iron", **opts): p.append([bone, "box", list(dims), list(at), mat, opts])
def prism(p, bone, dims, at, mat="iron", sides=6): p.append([bone, "prism", list(dims), list(at), mat, {"sides": sides}])
def cyl(p, bone, dims, at, mat="brass", axis="up"): p.append([bone, "cyl", list(dims), list(at), mat, {"axis": axis}])


def m_neck(p): prism(p, "head", (0.10, 0.09, 0.26), (0, 2.20, 0))
def m_knuckles(p):
    for s, x in (("L", 0.80), ("R", -0.80)):
        for dy in (-0.09, 0.03, 0.15):
            box(p, "forearm." + s, (0.13, 0.12, 0.15), (x, 1.02 + dy, 0.26), "brass")
def m_knees(p):
    for s, x in (("L", 0.34), ("R", -0.34)):
        cyl(p, "shin." + s, (0.17, 0.10), (x, 0.62, 0), "brass")
def m_boots(p):
    for s, x in (("L", 0.34), ("R", -0.34)):
        prism(p, "foot." + s, (0.22, 0.28, 0.18), (x, 0.06, 0.18), "iron")
def m_pelvis(p):
    for q in p:
        if q[0] == "pelvis" and q[1] == "box": q[2][0] *= 1.22
def m_deep(p):
    for q in p:
        if q[0] == "spine" and q[1] == "box" and q[2][0] > 0.9: q[2][2] *= 1.30
def m_taper(p):
    for q in p:
        if q[0].startswith("arm.") and q[1] == "prism": q[2][1] = q[2][0] * 1.35
def m_rims(p):
    for s, x in (("L", 0.62), ("R", -0.62)):
        box(p, "arm." + s, (0.36, 0.06, 0.46), (x, 2.26, 0), "brass")
def m_disc(p):
    for q in p:
        if q[0] == "spine" and q[1] == "cyl" and q[2][0] > 0.3: q[3][2] = 0.36
def m_backplate(p): box(p, "spine", (0.74, 0.54, 0.10), (0, 1.94, -0.40), "brass")
def m_bigwheel(p):
    for q in p:
        if q[0] == "head" and q[1] == "wheel": q[2][0] *= 1.18
        if q[0] == "head" and q[1] == "box" and max(q[2]) > 0.4: q[2] = [v * 1.18 for v in q[2]]
def m_thickspokes(p):
    for q in p:
        if q[0] == "head" and q[1] == "box": q[2][1] = 0.075; q[2][2] = 0.075
def m_pauldron_angle(p):
    for q in p:
        if q[0].startswith("arm.") and q[1] == "dome": q[5]["rot"] = [0, -12, 18]
def m_legs(p):
    for q in p:
        if (q[0].startswith("thigh.") or q[0].startswith("shin.")) and q[1] == "prism":
            q[2] = [v * 1.18 for v in q[2]]
def m_forearms(p):
    for q in p:
        if q[0].startswith("forearm.") and q[1] in ("prism", "box"): q[2] = [v * 1.12 for v in q[2]]
def m_sunk(p):
    for q in p:
        if q[0] == "head": q[3][1] -= 0.10
def m_chestring(p): cyl(p, "spine", (0.30, 0.05), (0, 1.98, 0.34), "iron", "fwd")
def m_flame(p):
    for q in p:
        if q[4] == "flame": q[2] = [v * 1.25 for v in q[2]]
def m_feet_wide(p):
    for q in p:
        if q[0].startswith("foot.") and q[1] == "box": q[2][0] *= 1.12
def m_arms_out(p):
    for q in p:
        if q[0].startswith("arm.") and q[1] == "prism":
            q[3][0] *= 1.06
        if q[0].startswith("forearm."):
            q[3][0] *= 1.06


STEPS = [m_neck, m_knuckles, m_knees, m_boots, m_pelvis, m_deep, m_taper, m_rims, m_disc,
         m_backplate, m_bigwheel, m_thickspokes, m_pauldron_angle, m_legs, m_forearms, m_sunk,
         m_chestring, m_flame, m_feet_wide, m_arms_out]


def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True)


def build_one(n):
    tag = f"draft{n:02d}"
    parts = json.loads(json.dumps(BASE))
    for fn in STEPS[: n - 1]:
        fn(parts)
    spec = pathlib.Path("/tmp") / (tag + "-spec.json")
    spec.write_text(json.dumps({"parts": parts}, indent=1))
    vdir = OUT / tag
    vdir.mkdir(parents=True, exist_ok=True)
    glb = vdir / "n01X.glb"
    run(["blender", "-b", "-P", "tools/blender/build_unit.py", "--", str(spec), str(glb),
         "700", "nofuse", "700", "tex"])
    if not glb.exists():
        print(tag, "BUILD FAILED")
        return
    views = pathlib.Path("/tmp") / (tag + "-views")
    run(["blender", "-b", "-P", "tools/blender/render_unit.py", "--", str(glb), str(views)])
    fs = [views / ("n01X-" + v + ".png") for v in ("front", "left", "back", "top", "bottom")]
    if all(f.exists() for f in fs):
        subprocess.run(["magick", *map(str, fs[:3]), "+append", str(views / "r1.png")], check=True)
        subprocess.run(["magick", "-size", "512x512", "xc:#9e9e9e", "/tmp/empty.png"], check=True)
        subprocess.run(["magick", str(fs[3]), str(fs[4]), "/tmp/empty.png", "+append", str(views / "r2.png")], check=True)
        subprocess.run(["magick", str(views / "r1.png"), str(views / "r2.png"), "-append", str(views / "sheet.png")], check=True)
        subprocess.run(["magick", str(CONCEPT), str(views / "sheet.png"), "-append", "-resize", "1500x",
                        str(vdir / "n01X-compare.png")], check=True)
    turn = pathlib.Path("/tmp") / (tag + "-turn")
    run(["blender", "-b", "-P", "tools/blender/turntable_color.py", "--", str(glb), str(turn), "18", "420"])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(turn / "orbit-%03d.png"),
                    "-vf", "fps=12,scale=420:-1:flags=lanczos", "-loop", "0", str(vdir / "n01X.gif")], check=True)
    print(tag, "ok |", len(parts), "parts")


def main():
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    for n in range(1, 21):
        if only and only != f"draft{n:02d}":
            continue
        build_one(n)


if __name__ == "__main__":
    main()
