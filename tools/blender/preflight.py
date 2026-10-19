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
# triangle budgets, WC3 SD standard (PIPELINE.md §6); spec_pipeline.py reads them from here
BUDGETS = {"mass": (400, 700), "hero": (900, 1600), "building": (600, 800), "large": (2000, 3000)}
ORNAMENT = ("ring", "wheel")


def is_leg(bone):
    return bone.startswith(("thigh", "shin", "foot", "leg"))


def load(path):
    """(parts, spec document) of a spec file."""
    doc = json.loads(pathlib.Path(path).read_text())
    return load_parts(doc), doc


def load_parts(doc):
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


def _tube(r, h, axis):
    """Half extents of a tube of radius r and length h along `axis`."""
    return {"up": (r, h / 2, r), "side": (h / 2, r, r)}.get(axis, (r, r, h / 2))


def _disc(kind, dims, opts):
    r, t = dims[0], dims[-1]
    axis = opts.get("axis", "fwd" if kind == "wheel" else "up")
    tilt = math.radians(opts.get("tilt", 0.0)) if kind == "ring" else 0.0
    if axis == "up":
        return r, r * math.sin(tilt) + t / 2, r * math.cos(tilt) + t / 2
    return (t / 2, r, r) if axis == "side" else (r, r, t / 2)


def _frustum(dims, opts):
    w, h, d = dims
    sx, sz = opts.get("top", (1.0, 1.0))
    return max(w, w * sx) / 2, h / 2, max(d, d * sz) / 2


# kind -> half extents (x, y, z) around the part centre; anything else is a box
HALF = {
    "prism": lambda d, o: _tube(max(d[0], d[1]), d[2], o.get("axis", "up")),
    "cyl": lambda d, o: _tube(d[0], d[1], o.get("axis", "fwd")),
    "dome": lambda d, o: (d[0], d[1] / 2, d[0]),
    "wheel": lambda d, o: _disc("wheel", d, o),
    "ring": lambda d, o: _disc("ring", d, o),
    "frustum": _frustum,
}
SPAN_RADIUS = {"prism": lambda d: max(d[0], d[1]), "cyl": lambda d: d[0]}


def bbox(part):
    _, kind, dims, _, _, opts = part
    if "from" in opts and "to" in opts:
        a, b = opts["from"], opts["to"]
        r = SPAN_RADIUS.get(kind, lambda d: max(d[0], d[2]) / 2)(dims)
        return (tuple(min(a[i], b[i]) - r for i in range(3)),
                tuple(max(a[i], b[i]) + r for i in range(3)))
    x, y, z = centre(part)
    hx, hy, hz = HALF.get(kind, lambda d, o: (d[0] / 2, d[1] / 2, d[2] / 2))(dims, opts)
    return (x - hx, y - hy, z - hz), (x + hx, y + hy, z + hz)


def overlaps(a, b):
    (al, ah), (bl, bh) = bbox(a), bbox(b)
    return all(al[i] <= bh[i] and bl[i] <= ah[i] for i in range(3))


def span(parts, names):
    boxes = [bbox(p) for p in parts if p[0] in names]
    if not boxes:
        return 0.0
    return max(max(abs(b[0][0]), abs(b[1][0])) for b in boxes) * 2


def biped_checks(parts, boxes, height):
    """Landmarks measured on the n01X sheet; they only mean something for a biped."""
    checks = []
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
    return checks


def floating_parts(parts, parent_of):
    """Bones whose parts touch neither another part on the bone nor one on its parent."""
    floating = []
    for p in parts:
        parent = parent_of.get(p[0])
        if not parent:
            continue
        # A distal piece may sit on its own bone: the fist overlaps the forearm
        # shell, not the upper arm. Check the bone and its parent together.
        group = {p[0], parent}
        siblings = [q for q in parts if q[0] in group and q is not p]
        if siblings and not any(overlaps(p, q) for q in siblings):
            floating.append(p[0])
    return sorted(set(floating))


def main():
    import rig_families as RF
    path = sys.argv[1]
    kind = sys.argv[2] if len(sys.argv) > 2 else "mass"
    lo, hi = BUDGETS[kind]
    parts, doc = load(path)
    family = doc.get("rig", "biped")                       # specs without "rig" are bipeds
    palette = PALETTE | set(doc.get("palette") or {})      # n01X names + the spec's slots
    checks = []

    tris = sum(part_tris(p) for p in parts)
    checks.append(("budget", lo <= tris <= hi, f"{tris} tris vs {lo}-{hi}"))

    mats = {p[4] for p in parts}
    checks.append(("materials", 3 <= len(mats) <= 5 and mats <= palette,
                   f"{sorted(mats)} ({len(mats)} slots)"))

    missing = RF.required(family) - {p[0] for p in parts}
    checks.append(("bones", not missing, f"{family}: missing {sorted(missing) or 'none'}"))

    boxes = {id(p): bbox(p) for p in parts}
    height = max(max(b[1][1] for b in boxes.values()), 1e-6)
    if family == "biped":
        checks += biped_checks(parts, boxes, height)

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

    floating = floating_parts(parts, RF.parents(family, doc.get("bones")))
    checks.append(("overlap", not floating, f"detached: {floating or 'none'}"))

    width = max(len(name) for name, *_ in checks)
    bad = 0
    for name, ok, detail in checks:
        bad += 0 if ok else 1
        print(f"  {name.ljust(width)}  {'PASS' if ok else 'FAIL'}  {detail}")
    leg_share = sum(part_tris(p) for p in parts if is_leg(p[0])) / max(tris, 1)
    print(f"  {'tri_mix'.ljust(width)}  {'INFO':4}  legs+feet {leg_share:.0%}, "
          f"ornament {share:.0%}, parts {len(parts)}")
    print(f"\n{len(checks) - bad}/{len(checks)} rules pass -> "
          f"{'ship it' if not bad else 'fix before building'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
