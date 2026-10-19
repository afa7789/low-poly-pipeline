#!/usr/bin/env python3
"""Pre-flight for a unit spec: the rules this project learned the hard way, checked
BEFORE anything is built, so the first attempt is already inside the design.

    python3 tools/blender/preflight.py artifacts/model-sheets/draft11/spec-n01X-v11.json mass

Rules (each one exists because an iteration failed on it):

  budget         400-700 mass / 900-1600 hero, counted with DSL v2 primitive costs
  materials      3-5 slots from the shared warm palette (iron, darkiron, brass, lamp)
  bones          every bone of the family covered
  shoulder_span  pauldron span / height 0.55-0.70 (concept n01X: 0.62)
  fist_span      fist-to-fist span / height 0.78-0.95 (concept n01X: 0.88)
  stance         foot-to-foot span / height 0.45-0.62 (concept n01X: 0.50)
  feet_mass      boot height >= 0.045 H and length >= 0.18 H (v9 failed: 0.05 / 0.14)
  shin_mass      calf width >= 0.09 H (v9's stilts were 0.07)
  head_top       ornamented head may rise 0.25 H over the shoulders; a bare head 0.05 H
  ornament_cost  head-wheel geometry <= 22% of the triangle budget (v9: 15% on spokes)
  ground         no part below y = 0
  overlap        each distal limb segment intersects its parent (no floating pieces)
"""
import json
import math
import pathlib
import sys

# Same estimates as build_unit.BASE_TRIS; ring counts its real mesh.
BASE_TRIS = {"box": 12, "frustum": 12, "cyl": 44, "wheel": 80, "prism": 28,
             "dome": 28, "ring": 144}
PALETTE = {"iron", "darkiron", "brass", "flame", "lamp"}
REQUIRED = {"pelvis", "spine", "head", "arm.L", "forearm.L", "thigh.L", "shin.L", "foot.L"}
PARENT = {"forearm.L": "arm.L", "forearm.R": "arm.R", "shin.L": "thigh.L",
          "shin.R": "thigh.R", "foot.L": "shin.L", "foot.R": "shin.R"}
ORNAMENT = ("ring", "wheel")
LEG_BONES = {"thigh.L", "shin.L", "foot.L", "thigh.R", "shin.R", "foot.R"}


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


def part_tris(part):
    _, kind, dims, _, _, opts = part
    if kind == "prism":
        return 4 * int(opts.get("sides", 8)) - 4
    if kind != "ring":
        return BASE_TRIS.get(kind, 12)
    sides = int(opts.get("sides", 10))
    spokes = int(opts.get("spokes", 0))
    hub = bool(opts.get("hub", 0.0) or spokes)
    return 8 * sides + 12 * spokes + (28 if hub else 0)


def centre(part):
    _, kind, dims, at, _, opts = part
    if "from" in opts and "to" in opts:
        a, b = opts["from"], opts["to"]
        return tuple((a[i] + b[i]) / 2 for i in range(3))
    return tuple(at)


def bbox(part):
    _, kind, dims, at, _, opts = part
    x, y, z = centre(part)
    if "from" in opts and "to" in opts:
        a, b = opts["from"], opts["to"]
        if kind == "prism":
            r = max(dims[0], dims[1])
        elif kind == "cyl":
            r = dims[0]
        else:
            r = max(dims[0], dims[2]) / 2
        lo = tuple(min(a[i], b[i]) - r for i in range(3))
        hi = tuple(max(a[i], b[i]) + r for i in range(3))
        return lo, hi
    if kind in ("prism", "cyl"):
        if kind == "prism":
            r, h = max(dims[0], dims[1]), dims[2]
        else:
            r, h = dims[0], dims[1]
        axis = opts.get("axis", "up" if kind == "prism" else "fwd")
        if axis == "up":
            return (x - r, y - h / 2, z - r), (x + r, y + h / 2, z + r)
        if axis == "side":
            return (x - h / 2, y - r, z - r), (x + h / 2, y + r, z + r)
        return (x - r, y - r, z - h / 2), (x + r, y + r, z + h / 2)
    if kind == "dome":
        r, h = dims
        return (x - r, y - h / 2, z - r), (x + r, y + h / 2, z + r)
    if kind in ("wheel", "ring"):
        r, t = dims[0], dims[-1]
        axis = opts.get("axis", "fwd" if kind == "wheel" else "up")
        tilt = math.radians(opts.get("tilt", 0.0)) if kind == "ring" else 0.0
        if axis == "up":
            hx, hy, hz = r, r * math.sin(tilt) + t / 2, r * math.cos(tilt) + t / 2
        elif axis == "side":
            hx, hy, hz = t / 2, r, r
        else:
            hx, hy, hz = r, r, t / 2
        return (x - hx, y - hy, z - hz), (x + hx, y + hy, z + hz)
    if kind == "frustum":
        w, h, d = dims
        sx, sz = opts.get("top", (1.0, 1.0))
        dx, dz = opts.get("shift", (0.0, 0.0))
        hw, hd = max(w, w * sx) / 2, max(d, d * sz) / 2
        return (x - hw, y - h / 2, z - hd), (x + hw, y + h / 2, z + hd)
    w, h, d = dims
    return (x - w / 2, y - h / 2, z - d / 2), (x + w / 2, y + h / 2, z + d / 2)


def overlaps(a, b):
    (al, ah), (bl, bh) = bbox(a), bbox(b)
    return all(al[i] <= bh[i] and bl[i] <= ah[i] for i in range(3))


def span(parts, names):
    boxes = [bbox(p) for p in parts if p[0] in names]
    if not boxes:
        return 0.0
    return max(max(abs(b[0][0]), abs(b[1][0])) for b in boxes) * 2


def main():
    path = sys.argv[1]
    kind = sys.argv[2] if len(sys.argv) > 2 else "mass"
    lo, hi = (400, 700) if kind == "mass" else (900, 1600)
    parts = load(path)
    checks = []

    tris = sum(part_tris(p) for p in parts)
    checks.append(("budget", lo <= tris <= hi, f"{tris} tris vs {lo}-{hi}"))

    mats = {p[4] for p in parts}
    checks.append(("materials", 3 <= len(mats) <= 5 and mats <= PALETTE,
                   f"{sorted(mats)} ({len(mats)} slots)"))

    bones = {p[0] for p in parts}
    missing = REQUIRED - bones
    checks.append(("bones", not missing, f"missing {sorted(missing) or 'none'}"))

    boxes = {id(p): bbox(p) for p in parts}
    height = max(b[1][1] for b in boxes.values())
    zs = [b[1][1] for b in boxes.values()]
    height = max(height, 1e-6)

    shoulder_parts = [p for p in parts if p[0] in ("arm.L", "arm.R")
                      and centre(p)[1] > 0.70 * height]
    shoulder = (max(max(abs(bbox(p)[0][0]), abs(bbox(p)[1][0])) for p in shoulder_parts) * 2
                if shoulder_parts else 0.0)
    checks.append(("shoulder_span", 0.55 <= shoulder / height <= 0.70,
                   f"{shoulder / height:.2f} (sheet 0.62)"))

    fist = span(parts, {"forearm.L", "forearm.R"})
    checks.append(("fist_span", 0.78 <= fist / height <= 0.95,
                   f"{fist / height:.2f} (sheet 0.88)"))

    stance = span(parts, {"foot.L", "foot.R"})
    checks.append(("stance", 0.45 <= stance / height <= 0.62,
                   f"{stance / height:.2f} (sheet 0.50)"))

    feet = [b for p, b in ((p, boxes[id(p)]) for p in parts) if p[0] in ("foot.L", "foot.R")]
    if feet:
        fh = min(b[1][1] - b[0][1] for b in feet) / height
        fl = min(b[1][2] - b[0][2] for b in feet) / height
        checks.append(("feet_mass", fh >= 0.045 and fl >= 0.18,
                       f"height {fh:.3f} H, length {fl:.3f} H"))
    else:
        checks.append(("feet_mass", False, "no foot parts"))

    shins = [p for p in parts if p[0] in ("shin.L", "shin.R") and p[1] == "prism"]
    if shins:
        sw = max(max(p[2][0], p[2][1]) * 2 for p in shins) / height
        checks.append(("shin_mass", sw >= 0.09, f"width {sw:.3f} H"))
    else:
        checks.append(("shin_mass", False, "no shin parts"))

    head = [b for p, b in ((p, boxes[id(p)]) for p in parts) if p[0] == "head"]
    if head:
        head_top = max(b[1][1] for b in head)
        shoulder_top = max((boxes[id(p)][1][1] for p in parts if p[0].startswith("arm.")),
                           default=head_top)
        ornamented = any(p[0] == "head" and p[1] in ORNAMENT for p in parts)
        allowance = 0.25 if ornamented else 0.05
        checks.append(("head_top", head_top <= shoulder_top + allowance * height,
                       f"head {head_top:.2f} vs shoulder {shoulder_top:.2f} "
                       f"(allow +{allowance:.2f} H)"))

    head_ornaments = [p for p in parts if p[0] == "head" and p[1] in ORNAMENT]
    if head_ornaments:
        axis_ok = all(p[5].get("axis", "fwd" if p[1] == "wheel" else "up") == "up"
                      and 15 <= float(p[5].get("tilt", 0.0)) <= 40 for p in head_ornaments)
        checks.append(("wheel_axis", axis_ok,
                       "head ornament is axis 'up' with tilt 15-40 (concept halo)"))

    ornament = sum(part_tris(p) for p in parts if p[0] == "head" and p[1] in ORNAMENT)
    # Against the budget ceiling, not the model's own total: a lean body must not fail
    # for carrying the same wheel a padded one passes with.
    share = ornament / hi
    checks.append(("ornament_cost", share <= 0.22, f"{ornament} tris = {share:.0%} of budget"))

    below = [p[0] for p in parts if boxes[id(p)][0][1] < -0.02]
    checks.append(("ground", not below, f"below y=0: {below or 'none'}"))

    floating = []
    for p in parts:
        parent = PARENT.get(p[0])
        if not parent:
            continue
        # A distal piece may sit on its own bone: the fist overlaps the forearm
        # shell, not the upper arm. Check the bone and its parent together.
        group = {p[0], parent}
        siblings = [q for q in parts if q[0] in group and q is not p]
        if siblings and not any(overlaps(p, q) for q in siblings):
            floating.append(p[0])
    checks.append(("overlap", not floating, f"detached: {sorted(set(floating)) or 'none'}"))

    width = max(len(name) for name, *_ in checks)
    bad = 0
    for name, ok, detail in checks:
        bad += 0 if ok else 1
        print(f"  {name.ljust(width)}  {'PASS' if ok else 'FAIL'}  {detail}")
    leg_share = sum(part_tris(p) for p in parts if p[0] in LEG_BONES) / max(tris, 1)
    print(f"  {'tri_mix'.ljust(width)}  {'INFO':4}  legs+feet {leg_share:.0%}, "
          f"ornament {share:.0%}, parts {len(parts)}")
    print(f"\n{len(checks) - bad}/{len(checks)} rules pass -> "
          f"{'ship it' if not bad else 'fix before building'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
