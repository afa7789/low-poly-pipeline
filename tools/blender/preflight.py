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
  overlap_80     the same with every box shrunk to 80 % (a corner touch does not connect); report only
  box_ceiling    "box" parts <= 1/3 of the parts (not for buildings): prism/frustum/dome/cyl
  budget_split   tris per body group (head, body, legs) within a band around the sheet's own area
                 split (EdgeRunner 2024); the head wheel is counted by ornament_cost
  symmetry       a .L part has its .R twin: same kind, dims (5%) and mirrored rot, unless
                 opts.asym (Wiersma 2026); weapons and shields carry asym
  outside_hull   per part, the share of its box outside the visual hull of the approved sheet's
                 front x left silhouettes (64^3 grid) <= 25%; names the part and wide/tall/deep
                 (Sano 2026). Needs the sheet.
  decal_place    a face decal (eyes, mask...) sits on a head/jaw/face bone, never the chest
"""
import json
import math
import pathlib
import sys

import numpy as np

import lathe_limb

# Same estimates as build_unit.BASE_TRIS; ring counts its real mesh.
BASE_TRIS = {"box": 12, "frustum": 12, "cyl": 44, "wheel": 80, "prism": 28,
             "dome": 28, "ring": 144, "lathe": 68, "limb": 32}
CUT_TRIS = 60   # a part cut by the sheet silhouette (cut_hull.py), upper end of the measured range
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
                "foot_length": 0.228, "head_clear": 0.25, "boot_height": 0.07, "head_width": 0.237,
                "area_head": 0.041, "area_body": 0.455, "area_legs": 0.504}
# floor and ceiling of the boot height and the head width, x the sheet's own (lesson 2026-10-26:
# every mass rule has both; the sheet is the approved one, never the hard)
BOOT_BAND = (0.7, 1.6)
HEAD_BAND = (0.6, 1.4)


# Tris per group of bones (head, body = torso+pelvis+arms+props, legs), as a share of the
# non-ornament tris. The target blends the sheet's front-silhouette area per band with the
# corpus prior (area alone is wrong: legs are cylinders, 0.4x their area in tris; the head
# has a floor). Calibrated on the 6 units / 37 biped specs of runs/draft: n01X hard-v1 and
# every n01X run that passes the shape gate sit inside (PIPELINE §19.B2).
GROUPS = ("head", "body", "legs")
SPLIT_PRIOR = (0.13, 0.63, 0.24)
SPLIT_AREA_WEIGHT = 0.5
SPLIT_SALIENCE = False  # True: the other half is the hard sheet's edge density per band, not the prior. Off: it fails 45/49 biped specs and n01X hard-v1 (PIPELINE §20.E15)
SPLIT_REL = 0.25     # +-25% around the target ...
SPLIT_SLACK = 0.08   # ... and this much absolute, so a small group is not judged to the tri
SYM_TOL = 0.05       # twin dims within 5%, mirrored rot within 5 degrees


def group_of(bone):
    if bone.split(".")[-1].startswith(FACE_BONES):
        return 0
    return 2 if is_leg(bone) else 1


def split_bands(targets):
    """[(low, high)] share of the tris for each of GROUPS, from the sheet's band areas."""
    area = [targets[f"area_{g}"] for g in GROUPS]
    other = [targets[f"edge_{g}"] for g in GROUPS] if SPLIT_SALIENCE and "edge_head" in targets else SPLIT_PRIOR
    mid = [SPLIT_AREA_WEIGHT * a + (1 - SPLIT_AREA_WEIGHT) * q for a, q in zip(area, other)]
    return [(max((1 - SPLIT_REL) * m - SPLIT_SLACK, 0.0), (1 + SPLIT_REL) * m + SPLIT_SLACK) for m in mid]


def split_shares(parts):
    """Tri share per GROUPS, ornaments left out (ornament_cost owns them)."""
    tris = [0, 0, 0]
    for p in parts:
        if not (p[0] == "head" and p[1] in ORNAMENT):
            tris[group_of(p[0])] += part_tris(p)
    total = max(sum(tris), 1)
    return [v / total for v in tris]


def mirror_gap(a, b):
    """Why twin parts a (.L) and b (.R) are not mirrors of each other, or None."""
    if a[1] != b[1]:
        return f"{a[1]} vs {b[1]}"
    for x, y in zip(a[2], b[2]):
        if abs(x - y) > SYM_TOL * max(abs(x), abs(y), 1e-6):
            return f"dims {a[2]} vs {b[2]}"
    ra, rb = rot_euler(a[5]), rot_euler(b[5])
    if any(abs(u - v) > 100 * SYM_TOL for u, v in zip(ra, (rb[0], -rb[1], -rb[2]))):
        return f"rot {list(ra)} vs {list(rb)} (mirror = [rx, -ry, -rz])"
    return None


def asymmetric(parts):
    """'bone: reason' for every .L/.R part without a mirrored twin on the other side. A part
    marked opts.asym, or a bone pair where either side has it, is exempt. Twins are matched
    by (kind, y, z) order inside each bone pair."""
    bad = []
    for left in sorted({p[0] for p in parts if p[0].endswith(".L")}):
        right = left[:-2] + ".R"
        side = {b: sorted((p for p in parts if p[0] == b), key=lambda p: (p[1], centre(p)[1], centre(p)[2]))
                for b in (left, right)}
        if any(isinstance(p[5], dict) and p[5].get("asym") for p in side[left] + side[right]):
            continue
        if len(side[left]) != len(side[right]):
            bad.append(f"{left[:-2]}: {len(side[left])} parts left, {len(side[right])} right")
            continue
        bad += [f"{left[:-2]}: {why}" for a, b in zip(side[left], side[right])
                if (why := mirror_gap(a, b))]
    return bad


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
    targets = {k: float(m[k]) for k in N01X_TARGETS}
    hard = pathlib.Path(sheet).with_name("sheet-hard.jpg")
    if hard.exists():       # edge density per band (head, body = torso, legs) of the hard sheet
        from silhouette import edge_bands
        bands = edge_bands(hard, m["shoulder_frac"])
        targets.update({f"edge_{g}": bands[b]["salience"] for g, b in zip(GROUPS, ("head", "torso", "legs"))})
    return targets


HULL_MAX = 0.25      # a part may sit this much of its box outside the sheet's visual hull
HULL_BLOCKING = False  # outside_hull reports but does not fail until the 25% is calibrated
HULL_GRID = 64
OVERLAP_SHRINK = 0.8   # overlap_80 compares boxes at this share of their size
# overlap_80 reports but does not fail: on 2026-10-27 it failed 48 of 63 draft specs (rule: < 1/3)
OVERLAP_BLOCKING = False
HULL_SLIDE = 0.12    # how far the panel may slide sideways, x the figure's height
HULL_PAD = 0.03      # margin around the hull, x the figure's height


def hull_masks(sheet, layout="unit"):
    """[(mask, pad)] for the sheet's front and left: the figure cropped, then grown by HULL_PAD of
    its height on every side (pad pixels of margin: a plate proud of the body, an ink line), or
    None when the sheet's panels cannot be read."""
    from scipy.ndimage import binary_dilation
    from silhouette import concept_panels, crop
    try:
        panels = concept_panels(pathlib.Path(sheet), layout=layout)
    except SystemExit:
        return None
    out = []
    for name in ("front", "left"):
        m = crop(panels[name])
        pad = round(HULL_PAD * m.shape[0])
        out.append((binary_dilation(np.pad(m, pad), iterations=pad), pad))
    return out


ROUND = ("prism", "cyl", "dome")    # kinds whose cross-section is an ellipse, not the box's corners
AXIS_ROUND = {"up": (0, 2), "side": (1, 2), "fwd": (0, 1)}   # the two axes the ellipse spans


def sample_points(part, cell):
    """(n, 3) spec-space points filling the part (its rotated box; a round unrotated part keeps
    its ellipse, a from/to part only its axis, a ring or wheel nothing: its box is mostly air),
    one per `cell`."""
    lo, hi = bbox(part)
    opts = part[5]
    if part[1] in ORNAMENT:
        return np.empty((0, 3))
    if "from" in opts and "to" in opts:
        t = np.linspace(0, 1, max(int(math.dist(opts["from"], opts["to"]) / cell), 1) + 1)
        return np.array(opts["from"]) + t[:, None] * (np.array(opts["to"]) - np.array(opts["from"]))
    axes = [np.linspace(a, b, max(int(math.ceil((b - a) / cell)), 1) + 1) for a, b in zip(lo, hi)]
    pts = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)
    if part[1] in ROUND and not any(rot_euler(opts)):
        a, b = AXIS_ROUND[opts.get("axis", "fwd" if part[1] == "cyl" else "up")]
        c, h = (np.array(lo) + hi) / 2, np.maximum((np.array(hi) - lo) / 2, 1e-9)
        pts = pts[((pts[:, a] - c[a]) / h[a]) ** 2 + ((pts[:, b] - c[b]) / h[b]) ** 2 <= 1.0]
    return pts


def view_misses(pts, mask, pad, k, height, centre, mirror=False):
    """(above, miss) bool per point for one panel: above = over the figure's height, miss = not
    on the panel's hull. The panel is scaled so the figure is `height` tall, set on `centre`
    along axis k (mirror: facing the other way), then slid sideways (HULL_SLIDE of the height) to where the fewest points
    miss: the sheet may carry a weapon or a pose the spec lacks, which skews its box."""
    mask = mask[:, ::-1] if mirror else mask
    ppm = (mask.shape[0] - 2 * pad) / height               # pixels per spec metre
    r = np.rint(mask.shape[0] - pad - pts[:, 1] * ppm - 0.5).astype(int)
    c0 = (pts[:, k] - centre) * ppm + mask.shape[1] / 2 - 0.5
    above = r < 0
    best = None
    for slide in range(-round(HULL_SLIDE * mask.shape[0]), round(HULL_SLIDE * mask.shape[0]) + 1, 2):
        c = np.rint(c0 + slide).astype(int)
        ok = ~above & (r < mask.shape[0]) & (c >= 0) & (c < mask.shape[1])
        ok[ok] = mask[r[ok], c[ok]]
        miss = ~ok & ~above
        if best is None or miss.sum() < best.sum():
            best = miss
    return above, best


def hull_outside(parts, masks, height):
    """{bone: (share outside the visual hull, 'wide'|'tall'|'deep')} per part over HULL_MAX.
    The hull is front[y, x] and left[y, z]: the front's columns run along +x (right), the left's
    along +z (forward) or -z. Each panel is scaled by the spec's own height and
    centred on its extent, as silhouette.normalize does to the sheet."""
    boxes = [bbox(p) for p in parts]
    centre_of = [(min(b[0][k] for b in boxes) + max(b[1][k] for b in boxes)) / 2 for k in range(3)]
    clouds = [sample_points(p, height / HULL_GRID) for p in parts]
    pts = np.concatenate(clouds)
    cuts = np.cumsum([len(c) for c in clouds])[:-1]
    (m, pad), (ml, padl) = masks
    above, wide = view_misses(pts, m, pad, 0, height, centre_of[0])
    # the left panel faces either way (the biped's toe points right, the spider's head left)
    _, deep = min((view_misses(pts, ml, padl, 2, height, centre_of[2], flip) for flip in (False, True)),
                  key=lambda v: v[1].sum())
    bad = {}
    for p, up, w, d in zip(parts, *(np.split(a, cuts) for a in (above, wide, deep))):
        share = float((up | w | d).mean()) if len(up) else 0.0
        if share > HULL_MAX:
            votes = {"wide": w.sum(), "deep": d.sum(), "tall": up.sum()}
            bad[p[0]] = max(bad.get(p[0], (0, "")), (share, max(votes, key=votes.get)))
    return bad


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


GRID = 256   # EdgeRunner 2024 / MeshGPT 2024: coordinates on a 1/256 grid of the height


def _snap(v, q):
    return round(round(v / q) * q, 6)


def normalise(parts, family="biped", extra=()):
    """Canonical form of a spec's parts, in place: at, dims and from/to on a (rig height)/GRID grid (a dim
    never below one cell), then ordered by the rig's bone order (+ the spec's extra bones), then y, with the .L part
    right before its .R twin. Same spec in, same bytes out; a mirrored pair stays mirrored."""
    import rig_families as RF
    q = RF.top(family) / GRID        # the rig's own height, so a second pass moves nothing
    for p in parts:
        opts = p[5] if isinstance(p[5], dict) else {}
        if p[3] is not None:
            p[3] = [_snap(v, q) for v in p[3]]
        p[2] = [max(_snap(v, q), q) if v > 0 else v for v in p[2]]
        for end in ("from", "to"):
            if end in opts:
                opts[end] = [_snap(v, q) for v in opts[end]]
    order = {name: i for i, name in enumerate([*RF.bones(family), *sorted(extra)])}

    def key(p):
        base = p[0][:-2] if p[0].endswith((".L", ".R")) else p[0]
        return (order.get(base, order.get(p[0], len(order))), round(centre(p)[1] / q),
                p[0].endswith(".R"), centre(p)[0])
    parts.sort(key=key)
    return parts


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
    if opts.get("cut") == "sheet":      # two <= 8-gon extrusions intersected: 42-61 tris measured (PIPELINE 19.B4)
        return opts.get("hull", {}).get("tris", CUT_TRIS)      # a building's base volume knows its own
    if kind == "prism":
        return 4 * int(opts.get("sides", 8)) - 4
    if kind in ("lathe", "limb", "plate"):
        return lathe_limb.tris(kind, opts)
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


ROT_KINDS = ("box", "prism", "dome", "frustum")    # kinds build_unit rotates by opts["rot"]


def rot_euler(opts):
    """opts["rot"] as (right, up, forward) degrees; a bare number turns around forward."""
    rot = opts.get("rot", 0.0)
    return (0.0, 0.0, float(rot)) if isinstance(rot, (int, float)) else tuple(float(v) for v in rot)


def rot_matrix(rx, ry, rz):
    """The build's rotation in spec (right, up, forward) axes: right first, then forward,
    then up (Blender XYZ euler after the axis swap). Right-handed, degrees."""
    (sx, cx), (sy, cy), (sz, cz) = ((math.sin(math.radians(v)), math.cos(math.radians(v)))
                                    for v in (rx, ry, rz))
    about_right = ((1, 0, 0), (0, cx, -sx), (0, sx, cx))
    about_fwd = ((cz, -sz, 0), (sz, cz, 0), (0, 0, 1))
    about_up = ((cy, 0, sy), (0, 1, 0), (-sy, 0, cy))
    return _matmul(about_up, _matmul(about_fwd, about_right))


def _matmul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def rotated_half(half, euler):
    """Half extents of the box `half` after the rotation, as an axis-aligned box."""
    m = rot_matrix(*euler)
    return tuple(sum(abs(m[i][j]) * half[j] for j in range(3)) for i in range(3))


def plate_box(dims, at, opts):
    """Box of a plate: its points turned by opts rot about `at`, as build_unit.build_part turns a box."""
    m = rot_matrix(*rot_euler(opts))
    pts = [tuple(sum(m[i][j] * (p[j] - at[j]) for j in range(3)) + at[i] for i in range(3))
           for ring in lathe_limb.plate_rings(dims, at, opts) for p in ring]
    return tuple(min(p[i] for p in pts) for i in range(3)), tuple(max(p[i] for p in pts) for i in range(3))


def bbox(part):
    _, kind, dims, at, _, opts = part
    if kind == "plate":
        return plate_box(dims, at, opts)
    if kind in ("lathe", "limb"):
        return lathe_limb.half_extent(kind, dims, at, opts)
    if "from" in opts and "to" in opts:
        a, b = opts["from"], opts["to"]
        r = SPAN_RADIUS.get(kind, lambda d: max(d[0], d[2]) / 2)(dims)
        return (tuple(min(a[i], b[i]) - r for i in range(3)),
                tuple(max(a[i], b[i]) + r for i in range(3)))
    x, y, z = centre(part)
    half = HALF.get(kind, lambda d, o: (d[0] / 2, d[1] / 2, d[2] / 2))(dims, opts)
    if kind in ROT_KINDS and any(rot_euler(opts)):
        half = rotated_half(half, rot_euler(opts))
    hx, hy, hz = half
    return (x - hx, y - hy, z - hz), (x + hx, y + hy, z + hz)


def shrunk(box, k):
    """The box scaled to k of its size about its centre."""
    lo, hi = box
    return (tuple((l + h) / 2 - (h - l) / 2 * k for l, h in zip(lo, hi)),
            tuple((l + h) / 2 + (h - l) / 2 * k for l, h in zip(lo, hi)))


def overlaps(a, b, k=1.0):
    """The two parts' boxes, each shrunk to k of its size, intersect: at k = OVERLAP_SHRINK a box
    that only touches the other at a corner or an edge does not count as connected."""
    (al, ah), (bl, bh) = shrunk(bbox(a), k), shrunk(bbox(b), k)
    return all(al[i] <= bh[i] and bl[i] <= ah[i] for i in range(3))


# Spider rules that fail the preflight: FAIL rate over the 15 spider specs of runs/draft/*/*/ was
# spider_leg 3/15 (blocks), spider_body 7/15 and spider_reach 11/15 (> 1/3: report only), PIPELINE section 20.L14
SPIDER_BLOCKING = {"spider_leg"}
SPIDER_BAND = (0.7, 1.4)  # a body or a leg within -30%/+40% of the sheet's measure
LEG_W_BAND = (0.6, 1.4)   # leg radius within +-40% of the sheet's leg_w (report only, PIPELINE 21.F3)


def leg_radius(part):
    """Mean radius of a spider leg part: a prism tapers from dims[0] to dims[1]."""
    d = part[2]
    return (d[0] + d[1]) / 2 if part[1] == "prism" else SPAN_RADIUS.get(part[1], lambda d: max(d[0], d[2]) / 2)(d)


def spider_checks(parts, boxes, height, m):
    """The spider rules (the fourth, spider_leg_w, when the measure has leg_w) against the sheet's measures (silhouette.measure_spider, kept in
    the spec as rig_measure), each a fraction of the unit's own height: body width, leg reach
    and leg length. [(rule, passed, detail)]."""
    import rig_families as RF
    body = [boxes[id(p)] for p in parts if p[0] in ("body", "abdomen")]
    legs = [p for p in parts if p[0].startswith("leg")]
    width = (max(b[1][0] for b in body) - min(b[0][0] for b in body)) / height if body else 0.0
    reach = max([max(abs(boxes[id(p)][i][a]) for i in (0, 1) for a in (0, 2)) for p in legs] or [0.0]) / height
    per_leg = {}
    for p in legs:
        a, b = p[5].get("from"), p[5].get("to")
        if a and b:
            per_leg[p[0].split(".")[0]] = per_leg.get(p[0].split(".")[0], 0.0) + math.dist(a, b)
    length = sorted(per_leg.values())[len(per_leg) // 2] / height if per_leg else 0.0
    rows = [("spider_body", width, 2 * m["body_r"], "body+abdomen width", SPIDER_BAND),
            ("spider_reach", reach, max(m["knee_r"], m["foot_r"]), "leg reach from the axis", SPIDER_BAND),
            ("spider_leg", length, RF.spider_leg_len(m), "leg length hip-knee-foot", SPIDER_BAND)]
    if "leg_w" in m and legs:
        radii = sorted(leg_radius(p) for p in legs)
        rows.append(("spider_leg_w", radii[len(radii) // 2] / height, m["leg_w"], "leg radius", LEG_W_BAND))
    out = []
    for rule, got, want, what, band in rows:
        ok = band[0] * want <= got <= band[1] * want
        out.append((rule, ok or rule not in SPIDER_BLOCKING,
                    f"{what} {got:.3f} H vs sheet {want:.3f} H (band {band[0]}-{band[1]} x)"
                    + ("" if ok else " - OUT")))
    return out


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

    # a limb on the thigh bone carries the shin too (dims = r_top, r_knee, r_base)
    shins = [p for p in parts if (p[0] in ("shin.L", "shin.R") and p[1] == "prism")
             or (p[0] in ("thigh.L", "thigh.R") and p[1] == "limb")]
    if shins:
        sw = max(max(p[2][-2:] if p[1] == "limb" else p[2][:2]) * 2 for p in shins) / height
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


def floating_parts(parts, parent_of, k=1.0):
    """Bones whose parts touch neither another part on the bone nor one on its parent
    (boxes at k of their size)."""
    floating = []
    for p in parts:
        parent = parent_of.get(p[0])
        if not parent:
            continue
        # A distal piece may sit on its own bone: the fist overlaps the forearm
        # shell, not the upper arm. Check the bone and its parent together.
        group = {p[0], parent}
        siblings = [q for q in parts if q[0] in group and q is not p]
        if siblings and not any(overlaps(p, q, k) for q in siblings):
            floating.append(p[0])
    return sorted(set(floating))


def checks_of(parts, doc, kind, targets, props, sheet=None):
    """[(rule, passed, detail)] of one spec. `targets` = targets_from(sheet), `props` =
    load_props(unit): both read once by the caller, so fit_spec can re-run the rules cheaply."""
    import rig_families as RF
    lo, hi = BUDGETS[kind]
    family = doc.get("rig", "biped")                       # specs without "rig" are bipeds
    palette = PALETTE | set(doc.get("palette") or {})      # n01X names + the spec's slots
    checks = []

    tris = sum(part_tris(p) for p in parts)
    checks.append(("budget", lo <= tris <= hi, f"{tris} tris vs {lo}-{hi}"))

    mats = {p[4] for p in parts}
    checks.append(("materials", MATERIAL_SLOTS[0] <= len(mats) <= MATERIAL_SLOTS[1]
                   and mats <= palette,
                   f"{sorted(mats)} ({len(mats)} slots)"))

    need = RF.required(family)
    covered = {p[0] for p in parts} | {b for p in parts if p[1] == "limb" for b in lathe_limb.limb_bones(p[0], need) or ()}
    missing = need - covered       # a limb covers its upper and lower bone
    checks.append(("bones", not missing, f"{family}: missing {sorted(missing) or 'none'}"))

    boxes = {id(p): bbox(p) for p in parts}
    height = max(max(b[1][1] for b in boxes.values()), 1e-6)
    if family == "biped":
        checks += biped_checks(parts, boxes, height, targets)
    if doc.get("rig_measure") and family in RF.SPIDERS:
        checks += spider_checks(parts, boxes, height, doc["rig_measure"])

    if family == "biped":
        shares = split_shares(parts)
        bands = split_bands(targets)
        off = [g for g, s, (lo_s, hi_s) in zip(GROUPS, shares, bands) if not lo_s <= s <= hi_s]
        checks.append(("budget_split", not off,
                       ", ".join(f"{g} {s:.0%} ({lo_s:.0%}-{hi_s:.0%})"
                                 for g, s, (lo_s, hi_s) in zip(GROUPS, shares, bands))))
        lopsided = asymmetric(parts)
        checks.append(("symmetry", not lopsided,
                       f"{lopsided or 'every .L has its .R twin'} (opts.asym exempts a weapon or shield)"))

    if sheet:
        masks = hull_masks(sheet, "building" if family == "building" else "unit")
        bad_hull = hull_outside(parts, masks, height) if masks else {}
        # Reporting only until calibrated: on 2026-10-27 the rule failed 42 of 53 draft specs.
        checks.append(("outside_hull", not bad_hull or not HULL_BLOCKING,
                       ", ".join(f"{b} {s:.0%} outside the sheet's hull, too {d}"
                                 for b, (s, d) in bad_hull.items())
                       or f"every part inside the sheet's front x left hull (max {HULL_MAX:.0%} out)"))

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

    parent_of = RF.parents(family, doc.get("bones"))
    floating = floating_parts(parts, parent_of)
    checks.append(("overlap", not floating, f"detached: {floating or 'none'}"))
    loose = floating_parts(parts, parent_of, OVERLAP_SHRINK)
    checks.append(("overlap_80", not loose or not OVERLAP_BLOCKING,
                   f"detached at {OVERLAP_SHRINK:.0%} boxes: {loose or 'none'}"))

    return checks


def main():
    sheet = sys.argv[3] if len(sys.argv) > 3 else None
    kind = sys.argv[2] if len(sys.argv) > 2 else "mass"
    parts, doc = load(sys.argv[1])
    checks = checks_of(parts, doc, kind, targets_from(sheet),
                       load_props(pathlib.Path(sheet).parent.name) if sheet else [], sheet)
    tris = sum(part_tris(p) for p in parts)
    share = sum(part_tris(p) for p in parts if p[0] == "head" and p[1] in ORNAMENT) / BUDGETS[kind][1]
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
