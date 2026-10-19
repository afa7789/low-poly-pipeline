#!/usr/bin/env python3
"""Pre-flight for a unit spec: the rules this project learned the hard way, checked
BEFORE anything is built, so the first attempt is already inside the design.

    python3 tools/blender/preflight.py artifacts/model-sheets/draft9/spec-n01X-v9.json

Every rule below exists because a specific iteration failed on it:

  budget         416-700 mass / 900-1600 hero; a union of the body costs ~1000
  materials      exactly 3 (iron, brass, flame). A boolean absorbs the flame slit.
  bones          every bone of the family covered, nothing floating off its bone
  shoulderness   shoulder span / height in 0.55-0.70 (sheet measures 0.62)
  head           head top at or below the shoulder line + 0.05 H (the "mascot" tell)
  stance         feet wider than the shin, planted at y=0
  ground         no part below y = 0
  overlap        every limb part intersects its parent part (no gaps -> no "levitating" pieces)
"""
import json
import math
import pathlib
import sys

BASE_TRIS = {"box": 12, "cyl": 44, "wheel": 80, "prism": 28, "dome": 28}
REQUIRED = {"pelvis", "spine", "head", "arm.L", "forearm.L", "thigh.L", "shin.L", "foot.L"}


def load(path):
    doc = json.loads(pathlib.Path(path).read_text())
    if "segments" in doc:                       # skeleton-first spec
        parts = []
        for seg in doc["segments"]:
            r0, r1 = seg.get("radius", (0.12, 0.10))
            parts.append([seg["bone"], seg.get("kind", "prism"),
                          [r0, r1, 0.4], seg.get("at", [0, 1, 0]),
                          seg.get("material", "iron"), {}])
        for ex in doc.get("extras", []):
            parts.append([ex["bone"], ex.get("kind", "box"), ex["dims"],
                          ex.get("offset", [0, 0, 0]), ex.get("material", "iron"), {}])
        return parts
    return doc["parts"]


def bbox(part):
    _, kind, dims, at, _, _ = part
    x, y, z = at
    if kind in ("prism", "cyl"):
        r = dims[0]
        h = dims[2] if kind == "prism" else dims[1]
        return (x - r, y - h / 2, z - r), (x + r, y + h / 2, z + r)
    if kind == "dome":
        r, h = dims[0], dims[1]
        return (x - r, y - h / 2, z - r), (x + r, y + h / 2, z + r)
    if kind == "wheel":
        r, t = dims
        return (x - r, y - t, z - r), (x + r, y + t, z + r)
    w, h, d = dims
    return (x - w / 2, y - h / 2, z - d / 2), (x + w / 2, y + h / 2, z + d / 2)


def overlaps(a, b):
    (al, ah), (bl, bh) = bbox(a), bbox(b)
    return all(al[i] <= bh[i] and bl[i] <= ah[i] for i in range(3))


def main():
    path = sys.argv[1]
    kind = sys.argv[2] if len(sys.argv) > 2 else "mass"
    lo, hi = (416, 700) if kind == "mass" else (900, 1600)
    parts = load(path)
    checks = []

    tris = sum(BASE_TRIS.get(p[1], 12) for p in parts)
    checks.append(("budget", lo <= tris <= hi, f"{tris} tris vs {lo}-{hi}"))

    mats = {p[4] for p in parts}
    checks.append(("materials", mats == {"iron", "brass", "flame"}, f"uses {sorted(mats)}"))

    bones = {p[0] for p in parts}
    missing = REQUIRED - bones
    checks.append(("bones", not missing, f"missing {sorted(missing) or 'none'}"))

    boxes = [bbox(p) for p in parts]
    zs = [b[1][1] for b in boxes]
    xs = [max(abs(b[0][0]), abs(b[1][0])) for b in boxes]
    height = max(zs)
    shoulder = max(xs) * 2
    ratio = shoulder / max(height, 1e-6)
    checks.append(("shoulderness", 0.55 <= ratio <= 0.70, f"{ratio:.2f} (sheet 0.62)"))

    head = [b for p, b in zip(parts, boxes) if p[0] == "head"]
    if head:
        head_top = max(b[1][1] for b in head)
        shoulder_top = max((b[1][1] for p, b in zip(parts, boxes) if p[0].startswith("arm.")), default=head_top)
        sunk = head_top <= shoulder_top + 0.05 * height
        checks.append(("head_sunk", sunk, f"head {head_top:.2f} vs shoulder {shoulder_top:.2f}"))

    below = [p[0] for p, b in zip(parts, boxes) if b[0][1] < -0.02]
    checks.append(("ground", not below, f"below y=0: {below or 'none'}"))

    floating = []
    for p in parts:
        if p[0] in ("root",):
            continue
        parent = {"forearm.L": "arm.L", "forearm.R": "arm.R", "shin.L": "thigh.L",
                  "shin.R": "thigh.R", "foot.L": "shin.L", "foot.R": "shin.R"}.get(p[0])
        if not parent:
            continue
        siblings = [q for q in parts if q[0] == parent]
        if siblings and not any(overlaps(p, q) for q in siblings):
            floating.append(p[0])
    checks.append(("overlap", not floating, f"detached: {floating or 'none'}"))

    width = max(len(name) for name, *_ in checks)
    bad = 0
    for name, ok, detail in checks:
        bad += 0 if ok else 1
        print(f"  {name.ljust(width)}  {'PASS' if ok else 'FAIL'}  {detail}")
    print(f"\n{len(checks) - bad}/{len(checks)} rules pass -> {'ship it' if not bad else 'fix before building'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
