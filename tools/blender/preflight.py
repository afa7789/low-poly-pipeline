#!/usr/bin/env python3
"""Pre-flight for a unit spec: the rules this project learned the hard way, checked
BEFORE anything is built, so the first attempt is already inside the design.

    python3 tools/blender/preflight.py <spec.json> <kind> [<approved sheet.jpg>]

Rules (each one exists because an iteration failed on it):

  budget         BUDGETS per kind, counted with DSL v2 primitive costs
  materials      MATERIAL_SLOTS (3-8) slots, palette names or the spec's own "palette"
  bones          every required bone of the rig family covered
  shoulder_span  biped widths in the sheet's height bands (shoulders, fists, stance),
  fist_span        within TOLERANCE of the unit's own sheet when it is given,
  stance           else of the n01X sheet
  feet_mass      boot height >= 0.045 H and length >= 0.8 x the sheet's foot length
  shin_mass      calf width >= 0.09 H (v9's stilts were 0.07)
  head_top       the head may rise over the shoulders as far as the sheet's shoulder line
                 sits below its top (+0.05 H); an ornamented head at least 0.25 H
  ornament_cost  head-wheel geometry <= 22% of the triangle budget (v9: 15% on spokes)
  boot_height    boot height 0.7-1.6 x the sheet's, head_width 0.6-1.4 x the sheet's
  props_present  one part per prop of prompts/<id>/props.json, on one of its bones, as long as
                 the prop's extent bracket (fractions of H); a presence check, not a shape one
  ground         no part below y = 0
  overlap        each distal limb segment intersects its parent (no floating pieces)
  box_ceiling    "box" parts <= 1/3 of the parts (not for buildings): prism/frustum/dome/cyl
  decal_place    a face decal (eyes, mask...) sits on a head/jaw/face bone, never the chest
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
MATERIAL_SLOTS = (3, 8)   # one atlas holds every slot, so more materials cost no texture
# animation clips of an animated rig: idle, walk, attack, death, spell, plus attack2/attack3
# when the unit's combo has them (PIPELINE §17); static rigs and buildings carry none
CLIPS = (5, 7)
# Biped landmarks, as fractions of the height, read in the same height bands the sheet
# measure uses (silhouette.measure): rows 10-30% from the top are the shoulders, 60-80% the
# fists, the bottom 5% the stance. Targets come from the unit's own sheet (--sheet); the
# n01X numbers are only the fallback. Calibrated: n01X v1 and n00U v1 sit within 9% of
# their sheets; every hfoo run so far is 30-53% wider than its sheet at the shoulders.
BANDS = {"shoulder_span": (0.70, 0.90), "fist_span": (0.20, 0.40), "stance": (0.0, 0.05)}
TOLERANCE = 0.15
FOOT_MOST = 1.4     # boot length ceiling, x the sheet's foot length (floor is 0.8 x)
N01X_TARGETS = {"shoulder_span": 0.635, "fist_span": 0.863, "stance": 0.506,
                "foot_length": 0.228, "head_clear": 0.25, "boot_height": 0.07, "head_width": 0.237}
# floor and ceiling of the boot height and the head width, x the sheet's own (lesson 2026-10-26:
# every mass rule has both; the sheet is the approved one, never the hard)
BOOT_BAND = (0.7, 1.6)
HEAD_BAND = (0.6, 1.4)


PROPS_DIR = pathlib.Path(__file__).resolve().parents[2] / "artifacts/model-sheets/prompts"


def load_props(unit):
    """The unit's props [{name, where, bones, extent: [min, max] in H}] in the order they are
    drawn on its props sheet (left to right), or [] when it carries none."""
    path = PROPS_DIR / unit / "props.json"
    return json.loads(path.read_text()) if path.exists() else []


def props_missing(parts, boxes, height, props):
    """Names of the props with no part of their own: each prop claims one unclaimed part on
    one of its bones whose longest side lies in its extent bracket (a part serves one prop)."""
    used, missing = set(), []
    for prop in props:
        lo, hi = prop["extent"]
        hit = next((i for i, p in enumerate(parts) if i not in used and p[0] in prop["bones"]
                    and lo <= max(boxes[id(p)][1][k] - boxes[id(p)][0][k] for k in range(3)) / height <= hi),
                   None)
        if hit is None:
            missing.append(prop["name"])
        else:
            used.add(hit)
    return missing


def targets_from(sheet):
    """Landmark targets measured on this unit's approved sheet, or the n01X fallback."""
    if not sheet:
        return dict(N01X_TARGETS)
    from silhouette import measure
    m = measure(pathlib.Path(sheet))
    return {k: float(m[k]) for k in N01X_TARGETS}


def band_span(boxes, height, band):
    """Widest |x| extent x2 of any part reaching into a height band, as a fraction of H."""
    lo, hi = band[0] * height, band[1] * height
    w = [max(abs(b[0][0]), abs(b[1][0])) * 2 for b in boxes if b[1][1] >= lo and b[0][1] <= hi]
    return max(w) / height if w else 0.0


def ground_fix(parts):
    """Lift every part whose box dips below y = 0 by exactly the dip, so the spec stands
    on the ground without the model having to get it right. Returns the parts lifted."""
    lifted = []
    for p in parts:
        dip = -bbox(p)[0][1]
        if dip <= 1e-6:
            continue
        opts = p[5] if isinstance(p[5], dict) else {}
        p[3] = [p[3][0], p[3][1] + dip, p[3][2]]
        for end in ("from", "to"):
            if end in opts:
                opts[end] = [opts[end][0], opts[end][1] + dip, opts[end][2]]
        lifted.append(p[0])
    return lifted


BOX_SHARE = 1 / 3
FACE_BONES = ("head", "jaw", "face", "skull")


def is_face_bone(bone):
    """head, jaw, rider.head...: the last dotted segment names a face."""
    return bone.split(".")[-1].startswith(FACE_BONES)


def misplaced_decals(parts):
    """(index, bone) of every decal part whose bone is not a head/face bone."""
    return [(i, p[0]) for i, p in enumerate(parts)
            if isinstance(p[5], dict) and p[5].get("decal") and not is_face_bone(p[0])]


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
# radius of a from/to part around its axis; box and frustum use half their wider side
SPAN_RADIUS = {"prism": lambda d: max(d[0], d[1]), "cyl": lambda d: d[0],
               "dome": lambda d: d[0], "wheel": lambda d: d[0], "ring": lambda d: d[0]}


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


def biped_checks(parts, boxes, height, targets):
    """Biped landmarks against the unit's own sheet (targets_from), within TOLERANCE."""
    checks = []
    for name, band in BANDS.items():
        got, want = band_span(list(boxes.values()), height, band), targets[name]
        checks.append((name, abs(got - want) <= TOLERANCE * want,
                       f"{got:.2f} (sheet {want:.2f}, +/-{TOLERANCE:.0%})"))

    feet = [b for p, b in ((p, boxes[id(p)]) for p in parts) if p[0] in ("foot.L", "foot.R")]
    if feet:
        fh = min(b[1][1] - b[0][1] for b in feet) / height
        fl = min(b[1][2] - b[0][2] for b in feet) / height
        need, most = 0.8 * targets["foot_length"], FOOT_MOST * targets["foot_length"]
        # a ceiling too: with only a floor the repair pass kept growing the boot (n005 v3 ended
        # with a 2.1 m boot, 77% of the height) and nothing asked it to shrink
        lo, hi = (BOOT_BAND[0] * targets["boot_height"], BOOT_BAND[1] * targets["boot_height"])
        checks.append(("boot_height", lo <= fh <= hi,
                       f"{fh:.3f} H (sheet {targets['boot_height']:.3f}, want {lo:.3f}-{hi:.3f})"))
        checks.append(("feet_mass", fh >= 0.045 and need <= fl <= most,
                       f"height {fh:.3f} H, length {fl:.3f} H (sheet {targets['foot_length']:.2f}, "
                       f"want {need:.2f}-{most:.2f})"))
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
        hw = max(max(abs(b[0][0]), abs(b[1][0])) for b in head) * 2 / height
        lo, hi = (HEAD_BAND[0] * targets["head_width"], HEAD_BAND[1] * targets["head_width"])
        checks.append(("head_width", lo <= hw <= hi,
                       f"{hw:.3f} H (sheet {targets['head_width']:.3f}, want {lo:.3f}-{hi:.3f})"))
        head_top = max(b[1][1] for b in head)
        shoulder_top = max((boxes[id(p)][1][1] for p in parts if p[0].startswith("arm.")),
                           default=head_top)
        ornamented = any(p[0] == "head" and p[1] in ORNAMENT for p in parts)
        # the sheet's shoulder line sets how far a head may rise; an ornament keeps 0.25
        allowance = max(targets["head_clear"] + 0.05, 0.25 if ornamented else 0.0)
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
    checks.append(("materials", MATERIAL_SLOTS[0] <= len(mats) <= MATERIAL_SLOTS[1]
                   and mats <= palette,
                   f"{sorted(mats)} ({len(mats)} slots)"))

    missing = RF.required(family) - {p[0] for p in parts}
    checks.append(("bones", not missing, f"{family}: missing {sorted(missing) or 'none'}"))

    boxes = {id(p): bbox(p) for p in parts}
    height = max(max(b[1][1] for b in boxes.values()), 1e-6)
    if family == "biped":
        checks += biped_checks(parts, boxes, height,
                               targets_from(sys.argv[3] if len(sys.argv) > 3 else None))

    props = load_props(pathlib.Path(sys.argv[3]).parent.name) if len(sys.argv) > 3 else []
    if props:
        lost = props_missing(parts, boxes, height, props)
        checks.append(("props_present", not lost,
                       f"missing: {lost or 'none'} (one part per prop, on its bone, sized like the "
                       "props sheet; see props.json)"))

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

    if family != "building":
        boxes_n = sum(p[1] == "box" for p in parts)
        checks.append(("box_ceiling", boxes_n <= BOX_SHARE * len(parts) + 1e-9,
                       f"{boxes_n} of {len(parts)} parts are boxes (max {int(BOX_SHARE * len(parts))}); "
                       "use prism/frustum/dome/cyl"))

    bad_decals = misplaced_decals(parts)
    checks.append(("decal_place", not bad_decals,
                   f"decal off the head: {bad_decals or 'none'} (eyes go on a head/jaw part)"))

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
