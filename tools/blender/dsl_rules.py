#!/usr/bin/env python3
"""DSL rules that were prose, now preflight rules with a deterministic repair (PIPELINE 30.L12-6).

  hood_recess    a unit with a hood (parts.json names one on the head, or opts "hood") needs a face part (head bone, opts decal)
                 whose front face stands >= HOOD_RECESS_MIN of the hood's depth in front of its back wall and >= HOOD_MOUTH_GAP H
                 behind its mouth, and a hood at least HOOD_DEEP_MIN x as deep as wide (else it is a hat)
  prop_axis      a prop whose sheet mask is elongated (prop_masks, front/left): the PCA axis of the projected prop within
                 PROP_AXIS_MAX degrees of the mask's
  prop_coverage  the projected prop covers its mask: IoU >= PROP_COVER_MIN (best flip and slide of the panel, as the hull does)
  leg_joints     spider legs: every leg has a joint (two chained pieces or a bent limb) bending >= LEG_BEND_MIN degrees, and its
                 tibia reaches >= LEG_TIBIA_MIN x what the sheet's leg (rig_measure legs) shows

checks() -> ([(rule, passed, detail)], {rule: "n/a reason"}); repair() -> (parts, [(rule, part, before, after)]). A repair never
calls a model; it moves, adds or splits parts, and the rules are measured again after it."""
import copy
import math
import re

import numpy as np
from PIL import Image, ImageDraw

import lathe_limb
import preflight as PF
import rig_families as RF

HOOD_WORDS = re.compile(r"hood|cowl|capuz", re.I)
HOOD_RECESS_MIN = 0.15      # of the hood's depth
HOOD_MOUTH_GAP = 0.05       # of H
HOOD_DEEP_MIN = 0.6         # depth / width
PROP_AXIS_MAX = 15.0        # degrees
PROP_COVER_MIN = 0.50
PROP_PAD = 2                # px, silhouette.PROP_PAD
AXIS_ELONG = 2.0            # sqrt(l1 / l2) of the pixels: under it a shape has no axis
LEG_BEND_MIN = 15.0         # degrees
LEG_BEND_DEFAULT = 25.0     # the bend a split leg gets when the sheet gives none
LEG_TIBIA_MIN = 0.5         # of the sheet's knee -> foot reach in plan
LEG_FAMILIES = RF.SPIDERS       # not the quadruped: its sheet draws straight columns, and a bend added spill (n017 left .054 -> .09, PIPELINE 30.L12-6)
ROT_LIMIT = 60.0            # DSL: rot within +-60
SCALE_RANGE = (0.6, 1.6)
CANVAS_H, CANVAS_W = 256, 384       # silhouette.CANVAS_*, repeated so this module loads without scipy
VIEWS = ("front", "left")
_PANELS = {}


def opts_of(part):
    return part[5] if isinstance(part[5], dict) else {}


def height_of(parts):
    return max(max(PF.bbox(p)[1][1] for p in parts), 1e-6)


def parts_doc(sheet):
    import parts_fit
    return parts_fit.load(sheet) if sheet else None


# ---------------------------------------------------------------- hood_recess

def hood_part(parts):
    """The hood: the biggest non-prop part on the head bone."""
    heads = [p for p in parts if p[0] == "head" and not PF.is_prop(p)]
    return max(heads, key=lambda p: math.prod(b - a for a, b in zip(*PF.bbox(p))), default=None)


def has_hood(parts, pdoc):
    named = pdoc and any(p.get("bone") == "head" and not p.get("prop") and HOOD_WORDS.search(p.get("name", ""))
                         for p in pdoc["parts"])
    return bool(named or any(opts_of(p).get("hood") for p in parts))


def face_of(parts, hood):
    return next((p for p in parts if p[0] == "head" and p is not hood and not PF.is_prop(p) and "decal" in opts_of(p)), None)


def hood_numbers(parts, hood, face):
    (lo, hi), height = PF.bbox(hood), height_of(parts)
    back, front, depth, width = lo[2], hi[2], hi[2] - lo[2], hi[0] - lo[0]
    out = {"back": back, "front": front, "depth": depth, "width": width, "height": height, "face_front": None}
    if face is not None:
        out["face_front"] = PF.bbox(face)[1][2]
    return out


def hood_checks(parts, pdoc):
    if not has_hood(parts, pdoc):
        return [], {"hood_recess": "no hood (parts.json names none on the head, no opts hood)"}
    hood = hood_part(parts)
    if hood is None:
        return [], {"hood_recess": "no non-prop part on the head bone"}
    n = hood_numbers(parts, hood, face_of(parts, hood))
    deep = n["depth"] >= HOOD_DEEP_MIN * n["width"]
    why = f"hood depth {n['depth']:.3f} vs width {n['width']:.3f} (want >= {HOOD_DEEP_MIN} x)"
    if n["face_front"] is None:
        return [("hood_recess", False, f"no face part (head bone, opts decal) inside the hood; {why}")], {}
    recess = (n["face_front"] - n["back"]) / max(n["depth"], 1e-6)
    gap = (n["front"] - n["face_front"]) / n["height"]
    ok = deep and recess >= HOOD_RECESS_MIN and gap >= HOOD_MOUTH_GAP
    return [("hood_recess", ok, f"face {recess:.0%} of the depth in front of the back wall (want >= {HOOD_RECESS_MIN:.0%}), "
                                f"{gap:.3f} H behind the mouth (want >= {HOOD_MOUTH_GAP}); {why}")], {}


def deepen(hood, depth):
    """The hood `depth` deep with its back wall where it was; False when its primitive has no depth to stretch."""
    lo, hi = PF.bbox(hood)
    old, o = hi[2] - lo[2], hood[5]
    k = depth / old
    if hood[1] in ("box", "frustum") and "from" not in o:
        hood[2][2] *= k
        hood[3][2] += (depth - old) / 2
        return True
    rings = o.get("profile")
    if hood[1] != "lathe" or not rings:
        return False
    if isinstance(rings[0], list):
        for r in rings:
            r[1], r[2] = r[1] * k, r[2] * k
        hood[3][2] += (1 - k) * (lo[2] - hood[3][2])
    else:
        o["squash"] = o.get("squash", 1.0) / k
        hood[3][2] += (depth - old) / 2
    return True


def face_dims(parts, hood, pdoc, n):
    """(width, height, y centre) of a new face part: parts.json's face box when it has one, else a share of the hood."""
    (lo, hi) = PF.bbox(hood)
    w, h, y = 0.6 * n["width"], 0.5 * (hi[1] - lo[1]), (lo[1] + hi[1]) / 2
    face = next((p for p in (pdoc or {"parts": []})["parts"] if p.get("role") == "face" and p.get("bone") == "head" and p.get("box3d")), None)
    if face:
        s = n["height"] / float(pdoc.get("H") or n["height"])
        (x0, y0, _), (x1, y1, _) = face["box3d"]
        w, h, y = (x1 - x0) * s, (y1 - y0) * s, (y0 + y1) / 2 * s
    return min(w, 0.8 * n["width"]), min(h, 0.8 * (hi[1] - lo[1])), y


def hood_repair(parts, pdoc, log):
    if not hood_checks(parts, pdoc)[0]:
        return
    hood = hood_part(parts)
    n = hood_numbers(parts, hood, face_of(parts, hood))
    if n["depth"] < HOOD_DEEP_MIN * n["width"]:
        want = HOOD_DEEP_MIN * n["width"] * 1.02
        if deepen(hood, want):
            log.append(("hood_recess", "head hood", f"depth {n['depth']:.3f}", f"depth {want:.3f}"))
    face = face_of(parts, hood)
    n = hood_numbers(parts, hood, face)
    top = n["front"] - HOOD_MOUTH_GAP * n["height"] - 0.002
    low = n["back"] + HOOD_RECESS_MIN * n["depth"] + 0.002
    if top <= low:
        return
    if face is None:
        w, h, y = face_dims(parts, hood, pdoc, n)
        d = max(0.1 * n["depth"], 0.02)
        decal = {k: opts_of(hood).pop(k) for k in ("decal", "decal_color") if k in opts_of(hood)} or {"decal": "sheet"}
        parts.append(["head", "frustum", [w, h, d], [(PF.bbox(hood)[0][0] + PF.bbox(hood)[1][0]) / 2, y, top - d / 2], hood[4],
                      {"top": [1, 1], "shift": [0, 0], **decal}])
        log.append(("hood_recess", "head face", "none", f"frustum {w:.2f}x{h:.2f}x{d:.2f}, front at z {top:.3f}"))
    elif not low <= n["face_front"] <= top:
        dz = min(max(n["face_front"], low), top) - n["face_front"]
        shift_part(face, 2, dz)
        log.append(("hood_recess", "head face", f"front z {n['face_front']:.3f}", f"front z {n['face_front'] + dz:.3f}"))


def shift_part(part, axis, d):
    o = opts_of(part)
    part[3][axis] += d
    for end in ("from", "to"):
        if end in o:
            o[end][axis] += d


# ----------------------------------------------------------- prop_axis / prop_coverage

def groups(parts):
    out = {}
    for p in parts:
        if PF.is_prop(p):
            out.setdefault(str(p[5]["prop"]).lower(), []).append(p)
    return out


def frame_of(parts, view):
    """(s, horizontal mid, vertical mid): the figure's bbox scaled into the 256x384 canvas the sheet's panel is normalized to."""
    boxes = [PF.bbox(p) for p in parts]
    k = 0 if view == "front" else 2
    h0, h1 = min(b[0][k] for b in boxes), max(b[1][k] for b in boxes)
    y0, y1 = min(b[0][1] for b in boxes), max(b[1][1] for b in boxes)
    return min(CANVAS_H / max(y1 - y0, 1e-6), CANVAS_W / max(h1 - h0, 1e-6)), (h0 + h1) / 2, (y0 + y1) / 2


def raster(group, view, frame, flip):
    """Boolean canvas of the parts projected on the view; flip = the left panel faces the other way."""
    s, hm, ym = frame
    k, sign = (0, 1) if view == "front" else (2, -1 if flip else 1)
    img = Image.new("L", (CANVAS_W, CANVAS_H))
    draw = ImageDraw.Draw(img)

    def px(v):
        return CANVAS_W / 2 + sign * (v[k] - hm) * s, CANVAS_H / 2 - (v[1] - ym) * s

    for p in group:
        o = opts_of(p)
        if "from" in o and "to" in o:
            r = PF.SPAN_RADIUS.get(p[1], lambda d: max(d[0], d[2]) / 2)(p[2])
            draw.line([px(o["from"]), px(o["to"])], fill=255, width=max(1, round(2 * r * s)))
            continue
        for x, y in map(px, PF.sample_points(p, 1.0 / s)):
            draw.point((x, y), fill=255)
    from scipy.ndimage import binary_dilation
    return binary_dilation(np.asarray(img) > 0, iterations=PROP_PAD)        # the mask is grown the same way (silhouette.PROP_PAD)


def axis_of(b):
    """(angle degrees in [0, 180), elongation, length in px) of the pixels' principal axis, or None under 10 px."""
    ys, xs = np.nonzero(b)
    if len(ys) < 10:
        return None
    pts = np.stack([xs, -ys]).astype(float)
    w, v = np.linalg.eigh(np.cov(pts))
    u = v[:, 1]
    along = u @ (pts - pts.mean(axis=1, keepdims=True))
    return math.degrees(math.atan2(u[1], u[0])) % 180, math.sqrt(w[1] / max(w[0], 1e-9)), float(along.max() - along.min())


def shifted(a, dy, dx):
    out = np.zeros_like(a)
    ys, xs = slice(max(dy, 0), a.shape[0] + min(dy, 0)), slice(max(dx, 0), a.shape[1] + min(dx, 0))
    yd, xd = slice(max(-dy, 0), a.shape[0] + min(-dy, 0)), slice(max(-dx, 0), a.shape[1] + min(-dx, 0))
    out[ys, xs] = a[yd, xd]
    return out


def best_overlap(ras, mask):
    """(IoU, shifted raster) at the best slide (rows +-6 %, columns +-HULL_SLIDE of the canvas)."""
    best = (-1.0, ras)
    for dy in range(-16, 17, 4):
        for dx in range(-round(PF.HULL_SLIDE * CANVAS_H), round(PF.HULL_SLIDE * CANVAS_H) + 1, 3):
            r = shifted(ras, dy, dx)
            iou = float((r & mask).sum() / max((r | mask).sum(), 1))
            if iou > best[0]:
                best = (iou, r)
    return best


def measure(group, parts, view, mask):
    """{iou, flip, d_angle (mask - part, degrees in [-90, 90) or None), k (mask length / part length or None)} of one prop on one view."""
    frame = frame_of(parts, view)
    best = None
    for flip in (False,) if view == "front" else (False, True):
        iou, ras = best_overlap(raster(group, view, frame, flip), mask)
        if best is None or iou > best["iou"]:
            best = {"iou": iou, "flip": flip, "ras": ras}
    a, b = axis_of(mask), axis_of(best.pop("ras"))
    best.update(d_angle=None, k=None)
    if a and b and a[1] >= AXIS_ELONG and b[1] >= AXIS_ELONG:
        best.update(d_angle=(a[0] - b[0] + 90) % 180 - 90, k=a[2] / max(b[2], 1e-6))
    return best


def prop_rows(parts, sheet, layout="unit"):
    """{(prop, view): measure()} for every prop of the spec with a mask in the sheet's front/left panel."""
    from silhouette import concept_panels, prop_masks
    g = groups(parts)
    if not g or not sheet:
        return {}
    key = str(sheet)
    if key not in _PANELS:
        try:
            _PANELS[key] = concept_panels(PF.pathlib.Path(sheet), layout=layout)
        except SystemExit:
            _PANELS[key] = None
    panels = _PANELS[key]
    if panels is None:
        return {}
    rows = {}
    for view in VIEWS:
        for name, mask in prop_masks(sheet, view, layout, panels).items():
            if name.lower() in g:
                rows[(name.lower(), view)] = measure(g[name.lower()], parts, view, mask)
    return rows


def prop_checks(parts, sheet, family, pdoc, rows=None):
    na = lambda why: ([], {"prop_axis": why, "prop_coverage": why})  # noqa: E731
    if family == "building":
        return na("building")
    if not groups(parts):
        return na("no prop part in the spec")
    if not pdoc:
        return na("no refs parts.json (prop masks)")
    rows = prop_rows(parts, sheet) if rows is None else rows
    if not rows:
        return na("no prop mask in the sheet's front/left panel")
    out, gone = [], {}
    axis = {k: r for k, r in rows.items() if r["d_angle"] is not None}
    if axis:
        bad = [f"{n} {v} {r['d_angle']:+.0f} deg" for (n, v), r in axis.items() if abs(r["d_angle"]) > PROP_AXIS_MAX]
        out.append(("prop_axis", not bad, f"{bad or 'every elongated prop within'} {PROP_AXIS_MAX:.0f} deg of its mask's axis ({len(axis)} measured)"))
    else:
        gone["prop_axis"] = "no elongated prop mask"
    low = [f"{n} {v} {r['iou']:.2f}" for (n, v), r in rows.items() if r["iou"] < PROP_COVER_MIN]
    out.append(("prop_coverage", not low, f"{low or 'every prop'} covers its mask (IoU >= {PROP_COVER_MIN}); {len(rows)} measured"))
    return out, gone


def turn_group(group, view, flip, delta, scale):
    """The group turned by `delta` degrees (counter-clockwise on the panel) and scaled by `scale` about its centre, in the view's plane."""
    k, sign = (0, 1) if view == "front" else (2, -1 if flip else 1)
    c = np.mean([PF.centre(p) for p in group], axis=0)
    cos, sin = math.cos(math.radians(delta)), math.sin(math.radians(delta))

    def move(v):
        h, u = sign * (v[k] - c[k]), v[1] - c[1]
        out = list(v)
        out[k], out[1] = c[k] + sign * scale * (h * cos - u * sin), c[1] + scale * (h * sin + u * cos)
        return [out[i] if i in (k, 1) else c[i] + scale * (v[i] - c[i]) for i in range(3)]

    for p in group:
        o = opts_of(p)
        p[3] = move(p[3])
        for end in ("from", "to"):
            if end in o:
                o[end] = move(o[end])
        if "from" in o and p[1] == "prism":
            p[2][2] *= scale
        elif p[1] in PF.ROT_KINDS and "from" not in o:
            rot = list(o.get("rot", [0, 0, 0]))
            i, s = (2, 1.0) if view == "front" else (0, -float(sign))
            rot[i] = max(-ROT_LIMIT, min(ROT_LIMIT, rot[i] + s * delta))
            o["rot"] = rot


def prop_repair(parts, sheet, pdoc, log):
    g = groups(parts)
    for (name, view), r in list(prop_rows(parts, sheet).items()):
        d, k = r["d_angle"], r["k"]
        if d is None or not (abs(d) > PROP_AXIS_MAX or (r["iou"] < PROP_COVER_MIN and abs(k - 1) > 0.1)):
            continue            # a rule that holds is left alone
        scale = min(max(k, SCALE_RANGE[0]), SCALE_RANGE[1]) if abs(k - 1) > 0.1 else 1.0
        saved = copy.deepcopy(g[name])
        turn_group(g[name], view, r["flip"], d, scale)
        again = prop_rows(parts, sheet).get((name, view))
        worse = again["iou"] + 0.02 < r["iou"] and abs(again["d_angle"] or 0) > abs(d)     # worse on both counts: put it back
        log.append(("prop_axis", name, f"{view} {d:+.0f} deg, IoU {r['iou']:.2f}, length x{k:.2f}",
                    "kept as it was (the turn made it worse)" if worse else
                    f"{view} {'-' if again['d_angle'] is None else format(again['d_angle'], '+.0f')} deg, IoU {again['iou']:.2f}"))
        if worse:
            for p, was in zip(g[name], saved):
                p[:] = was


# ------------------------------------------------------------------- leg_joints

def leg_pieces(parts):
    """{leg number: (upper part, lower part or None)} of the non-prop from/to pieces on legN.upper / legN.lower."""
    out = {}
    for p in parts:
        m = re.fullmatch(r"leg(\d+)\.(upper|lower)", p[0])
        o = opts_of(p)
        if m and not PF.is_prop(p) and "from" in o and "to" in o:
            out.setdefault(int(m[1]), {}).setdefault(m[2], p)
    return {n: (v["upper"], v.get("lower")) for n, v in sorted(out.items()) if "upper" in v}


def leg_points(upper, lower):
    """(hip, knee, foot) of a leg, or (hip, None, foot) when it is one straight piece."""
    a, b = opts_of(upper)["from"], opts_of(upper)["to"]
    if upper[1] == "limb":
        k = lathe_limb.knee_of(opts_of(upper))
        return a, k, b
    if lower is not None:
        return a, b, opts_of(lower)["to"]
    return a, None, b


def bend(a, k, b):
    u, v = np.subtract(k, a), np.subtract(b, k)
    n = np.linalg.norm(u) * np.linalg.norm(v)
    return 0.0 if n < 1e-9 else math.degrees(math.acos(max(-1.0, min(1.0, float(u @ v) / n))))


def sheet_legs(doc, height):
    """[(azimuth, hip, knee, foot)] of rig_measure's legs, (x, z) in metres."""
    rows = (doc.get("rig_measure") or {}).get("legs")
    if not isinstance(rows, list) or not all(isinstance(r, list) and len(r) >= 7 for r in rows):       # a quadruped's legs are not the spider's rows
        return []
    return [(r[0], (r[1] * height, r[2] * height), (r[3] * height, r[4] * height), (r[5] * height, r[6] * height)) for r in rows]


def match_legs(feet, rows):
    """{leg number: sheet row}: each leg to the unused row with the nearest azimuth of its foot."""
    pairs = sorted((abs((math.degrees(math.atan2(f[1], f[0])) - r[0] + 180) % 360 - 180), n, i)
                   for n, f in feet.items() for i, r in enumerate(rows))
    out, used = {}, set()
    for _, n, i in pairs:
        if n not in out and i not in used:
            out[n] = rows[i]
            used.add(i)
    return out


def leg_rows(parts, doc):
    """[(leg, bend deg or None, tibia reach in plan or None, sheet reach or None)] per leg; bend None = one straight piece."""
    height, legs = height_of(parts), leg_pieces(parts)
    pts = {n: leg_points(*pc) for n, pc in legs.items()}
    sheet = match_legs({n: (p[2][0], p[2][2]) for n, p in pts.items()}, sheet_legs(doc, height))
    out = []
    for n, (a, k, b) in pts.items():
        reach = sheet_reach = None
        if k is not None and n in sheet:
            sheet_reach = math.dist(sheet[n][2], sheet[n][3])
            reach = math.dist((k[0], k[2]), (b[0], b[2]))
        out.append((n, None if k is None else bend(a, k, b), reach, sheet_reach))
    return out


def leg_checks(parts, doc, family):
    if family not in LEG_FAMILIES:
        return [], {"leg_joints": f"rig {family} (spider legs only)"}
    rows = leg_rows(parts, doc)
    if not rows:
        return [], {"leg_joints": "no leg piece with from/to"}
    height = height_of(parts)
    flat = [f"leg{n} {'1 straight piece' if b is None else f'{b:.0f} deg'}" for n, b, _, _ in rows if b is None or b < LEG_BEND_MIN]
    short = [f"leg{n} tibia {r / height:.3f} H vs sheet {s / height:.3f} H" for n, b, r, s in rows
             if b is not None and s and s >= 0.05 * height and r < LEG_TIBIA_MIN * s]
    return [("leg_joints", not flat and not short,
             f"{len(rows)} legs; no joint or under {LEG_BEND_MIN:.0f} deg: {flat or 'none'}; tibia under {LEG_TIBIA_MIN} x the sheet's: {short or 'none'}")], {}


def split_leg(parts, upper, k, hip, foot):
    """One straight piece on legN.upper into two: hip -> k on the upper bone, k -> foot on the lower."""
    o = opts_of(upper)
    lower = copy.deepcopy(upper)
    lower[0] = upper[0].replace(".upper", ".lower")
    d = upper[2]
    mid = (d[0] + d[1]) / 2
    upper[2], lower[2] = [d[0], mid, math.dist(hip, k)], [mid, d[1], math.dist(k, foot)]
    o["to"], opts_of(lower)["from"] = list(k), list(k)
    parts.insert(parts.index(upper) + 1, lower)


def lifted_knee(hip, foot, deg):
    """Mid-chord point raised so the two halves meet at `deg` degrees."""
    mid = (np.array(hip) + foot) / 2
    return list(mid + np.array([0.0, 1.0, 0.0]) * np.linalg.norm(np.subtract(foot, hip)) / 2 * math.tan(math.radians(deg) / 2))


def leg_repair(parts, doc, log):
    """Each failing leg gets the sheet's own knee and foot (rig_measure legs, matched by azimuth: x, z in H, the knee at knee_h), hip and foot
    height kept; a leg the sheet has no row for is bent LEG_BEND_DEFAULT degrees at mid-chord, up."""
    height, legs = height_of(parts), leg_pieces(parts)
    pts = {n: leg_points(*pc) for n, pc in legs.items()}
    sheet = match_legs({n: (p[2][0], p[2][2]) for n, p in pts.items()}, sheet_legs(doc, height))
    knee_h = (doc.get("rig_measure") or {}).get("knee_h")
    bad = {n for n, b, r, s in leg_rows(parts, doc) if b is None or b < LEG_BEND_MIN or (s and s >= 0.05 * height and r < LEG_TIBIA_MIN * s)}
    for n in sorted(bad):
        upper, lower = legs[n]
        hip, was, foot = pts[n]
        if n in sheet:
            (kx, kz), (fx, fz) = sheet[n][2], sheet[n][3]
            k, foot = [kx, (knee_h * height if knee_h else (hip[1] + foot[1]) / 2), kz], [fx, foot[1], fz]
        else:
            k = lifted_knee(hip, foot, LEG_BEND_DEFAULT)
        before = "1 straight piece" if was is None else f"knee ({was[0]:.3f}, {was[1]:.3f}, {was[2]:.3f})"
        set_leg(parts, upper, lower, hip, k, foot)
        log.append(("leg_joints", f"leg{n}", before, f"knee ({k[0]:.3f}, {k[1]:.3f}, {k[2]:.3f}), {bend(hip, k, foot):.0f} deg"))


def set_leg(parts, upper, lower, hip, k, foot):
    """The leg's pieces through hip -> knee -> foot: two pieces chained at the knee, a limb with its knee offset, or one piece split in two."""
    if lower is not None:
        opts_of(upper)["to"], opts_of(lower)["from"], opts_of(lower)["to"] = list(k), list(k), list(foot)
        upper[2][2], lower[2][2] = math.dist(hip, k), math.dist(k, foot)
    elif upper[1] == "limb":
        d = np.subtract(foot, hip)
        f = float(np.clip(np.dot(np.subtract(k, hip), d) / max(np.dot(d, d), 1e-9), 0.15, 0.85))
        base = np.array(hip) + f * d
        opts_of(upper)["to"] = list(foot)
        opts_of(upper)["knee"] = [f, k[0] - base[0], k[2] - base[2], k[1] - base[1]]
    else:
        split_leg(parts, upper, k, hip, foot)
        opts_of(parts[parts.index(upper) + 1])["to"] = list(foot)


# ------------------------------------------------------------------- entry points

def checks(parts, doc, sheet=None, rows=None, na=None):
    """([(rule, passed, detail)], {rule: n/a reason}) of the four rules on a spec (`doc` = the spec document, `sheet` = the approved sheet).
    `na`: a dict that takes the n/a reasons too."""
    family = doc.get("rig", "biped")
    pdoc = parts_doc(sheet)
    out, gone_all = [], {} if na is None else na
    for got, gone in (hood_checks(parts, pdoc) if family == "biped" else ([], {"hood_recess": f"rig {family}"}),
                      prop_checks(parts, sheet, family, pdoc, rows), leg_checks(parts, doc, family)):
        out += got
        gone_all.update(gone)
    import part_rules
    return out + part_rules.checks(parts, doc, sheet, pdoc, gone_all)[0], gone_all      # prop_side, arm_pose, part_exists, incoherent_part (33.L15-4)


def repair(parts, doc, sheet=None, opt_in=False):
    """(parts repaired in place, log [(rule, part, before, after)]) for the rules that fail; a rule that does not apply is left alone.
    The spider legs always; opt_in adds prop_side, arm_pose and reject-part (part_exists, L15-4), and hood_recess (the face it adds hides inside a closed lathe hood: n005 front .920 -> .907) and the
    props (n005 front/back -.006/-.007, coverage still under .5) - PIPELINE 30.L12-6."""
    import part_rules
    log, pdoc = [], parts_doc(sheet)
    failing = {n for n, ok, _ in checks(parts, doc, sheet)[0] if not ok}
    if "hood_recess" in failing and opt_in:
        hood_repair(parts, pdoc, log)
    if failing & {"prop_axis", "prop_coverage"} and opt_in:
        prop_repair(parts, sheet, pdoc, log)
    if "leg_joints" in failing:
        leg_repair(parts, doc, log)
    if opt_in:                  # measured on the v15 battery: prop_side / arm_pose / reject-part cost views > 2 sigma (PIPELINE 33.L15-4)
        part_rules.repair(parts, doc, sheet, pdoc, failing, log, reject=True)
    return parts, log
