#!/usr/bin/env python3
"""Preflight rules about what the author cannot see: depth, existence, pose, contradiction (PIPELINE 33.L15-4, diagnosis C5 + C6).
All numbers come from refs/<id>/parts.json (box2d, box3d, joints) and the approved sheet's pixels; no model call.

  prop_side      a prop that stands clear of the torso in the sheet's left panel (box2d) lies on the same side of the body (front / back
                 of the face's direction) in the spec. Repair: mirror the prop's z about the body's centre.
  part_exists    each spec part whose material has a colour (palette) and is not skin needs pixels of that colour (CIELAB dE <= EXIST_DE)
                 in its projected box in the front or back panel: >= EXIST_AREA of the panel, or >= EXIST_LOCAL of the box. Else reject-part:
                 the part is removed (never the only one on its bone).
  arm_pose       arm / forearm bones (non-prop prism, cyl, frustum with from/to): angle in the front plane against the sheet's joint
                 (shoulder -> elbow -> wrist, parts.json xyz) within ARM_ERR degrees. Repair: rotate the bone about its start to the
                 measured angle; what hangs from it moves along (props translate, never turn: a club stays upright in a raised fist).
  incoherent_part  (report only) an accent colour (saturated zone: the n02X fuse cloth) lying on opposite sides of the body in the front and
                 back panels; decision per part = the panel with more of it wins, written to refs/<id>/sheet.json "part_coherence";
                 a spec part with opts {"prop": <name>, "side": "front"|"back"} overrides it. The gate ignores the losing panel for
                 that part (silhouette.py, L15-1, reads ignored_views()).

checks() -> ([(rule, passed, detail)], {rule: n/a reason}); repair() appends (rule, part, before, after) to the log."""
import json
import math
import pathlib

import numpy as np

import dsl_rules as D
import preflight as PF
import rig_families as RF

SIDE_MIN = 0.05        # of H: a prop nearer the body's centre than this has no side
SIDE_CLEAR = 0.5       # a prop is judged when under this share of its width overlaps the torso's box in the left panel
STRAIGHT = 2.5         # prop box height / width above which the sheet's left panel shows it upright
SHEET_SIDE_MIN = 0.06  # of the crop width: centre offset prop - torso under which the sheet shows no side either
ARM_ERR = 25.0         # degrees
ARM_MIN = 0.04         # of H: a sheet bone shorter than this in the front plane is foreshortened, not judged
EXIST_DE = 12.0
EXIST_AREA = 0.01
EXIST_LOCAL = 0.25
EXIST_BLOCKING = False  # the colour test misses palette guesses (hfoo steel, n01X brass: 4-6 parts of 15 on sheets that have them), so it reports; --dsl-repair all removes
BOX_PAD = 0.10         # share the projected box grows by, per side
ACCENT_SAT, ACCENT_VAL = 0.72, 0.55
ACCENT_AREA = 0.003    # of the panel crop, in each panel
ACCENT_OFF = 0.08      # of the crop width: centroid offset from the midline under which a zone is "centred"
BODY_ROLES = ("torso", "pelvis")
ARM_SEGMENTS = (("arm", "shoulder", "elbow"), ("forearm", "elbow", "wrist"))
HUES = ("red", "orange", "yellow", "green", "cyan", "blue", "violet", "magenta")
_PANELS = {}


# ------------------------------------------------------------------ sheet readers

def doc_of(sheet):
    return D.parts_doc(sheet)


def facing(pdoc):
    """+1 when the face looks to the right of the left panel, -1 to the left, None when the joints do not say (chin vs head top)."""
    j = pdoc.get("joints") or {}
    a, b = (j.get("chin") or {}).get("left"), (j.get("head_top") or {}).get("left")
    if not a or not b or abs(a[0] - b[0]) < 0.01:
        return None
    return 1 if a[0] > b[0] else -1


def centre_x(box):
    return (box[0] + box[2]) / 2


def torso_box(pdoc):
    """box2d left of the torso: the union of the BODY_ROLES parts (else of every non-prop part), or None."""
    boxes = [p["box2d"]["left"] for p in pdoc["parts"] if not p.get("prop") and "left" in p.get("box2d", {}) and p.get("role") in BODY_ROLES]
    boxes = boxes or [p["box2d"]["left"] for p in pdoc["parts"] if not p.get("prop") and "left" in p.get("box2d", {})]
    if not boxes:
        return None
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def sheet_sides(pdoc):
    """{prop name (lower): +1 front, -1 back} of the props standing clear of the torso in the left panel; the others are absent."""
    face, torso = facing(pdoc), torso_box(pdoc)
    if face is None or torso is None:
        return {}
    out = {}
    for p in pdoc["parts"]:
        b = (p.get("box2d") or {}).get("left")
        if not p.get("prop") or not b:
            continue
        overlap = max(min(b[2], torso[2]) - max(b[0], torso[0]), 0) / max(b[2] - b[0], 1e-6)
        d = (centre_x(b) - centre_x(torso)) * face
        if overlap < SIDE_CLEAR and abs(d) >= SHEET_SIDE_MIN:
            out[str(p["name"]).lower()] = 1 if d > 0 else -1
    return out


# ------------------------------------------------------------------ prop_side

def body_z(parts):
    """z centre of the non-prop parts on the spine / pelvis (spec +z = forward), else of every non-prop part."""
    body = [p for p in parts if not PF.is_prop(p) and p[0] in ("spine", "pelvis")] or [p for p in parts if not PF.is_prop(p)]
    return float(np.mean([PF.centre(p)[2] for p in body])) if body else 0.0


def side_rows(parts, pdoc):
    """[(prop, spec side, sheet side)] of the props with a sheet side; the spec side is 0 when it stands within SIDE_MIN H of the body."""
    sheet, height, bz = sheet_sides(pdoc), D.height_of(parts), body_z(parts)
    rows = []
    for name, group in D.groups(parts).items():
        if name not in sheet:
            continue
        d = float(np.mean([PF.centre(p)[2] for p in group])) - bz
        rows.append((name, 0 if abs(d) < SIDE_MIN * height else (1 if d > 0 else -1), sheet[name]))
    return rows


def side_checks(parts, pdoc):
    if not D.groups(parts):
        return [], {"prop_side": "no prop part in the spec"}
    rows = side_rows(parts, pdoc) if pdoc else []
    if not rows:
        return [], {"prop_side": "no prop clear of the torso in the sheet's left panel (or no parts.json)"}
    bad = [f"{n}: spec {'front' if s > 0 else 'back' if s < 0 else 'at the body'}, sheet {'front' if t > 0 else 'back'}" for n, s, t in rows if s != t]
    return [("prop_side", not bad, f"{bad or 'every prop'} on the sheet's side of the body ({len(rows)} judged)")], {}


def z_scale(pdoc):
    """Spec metres of depth per unit of left-panel width: the torso's box3d depth over its box2d left width (None when parts.json lacks it)."""
    for p in pdoc["parts"]:
        b, c = (p.get("box2d") or {}).get("left"), p.get("box3d")
        if p.get("role") in BODY_ROLES and b and c and b[2] > b[0]:
            return (c[1][2] - c[0][2]) / (b[2] - b[0])
    return None


def prop_target(pdoc, name, side, bz, k):
    """(z centre, straight) of the prop in the spec: the sheet's offset from the torso centre (left panel box2d x z_scale, k = spec / sheet size)
    on `side`; straight when its box is tall and narrow (the sheet draws it upright, not leaning in depth)."""
    b = next(q["box2d"]["left"] for q in pdoc["parts"] if q.get("prop") and str(q["name"]).lower() == name)
    zs, torso = z_scale(pdoc), torso_box(pdoc)
    offset = abs(centre_x(b) - centre_x(torso)) * zs * k if zs else SIDE_MIN
    return bz + side * offset, (b[3] - b[1]) > STRAIGHT * (b[2] - b[0])


def place_z(group, z, straight):
    """The group's parts moved in z so their mean centre is `z`; straight = every end and centre on `z` (no lean in depth)."""
    mean = float(np.mean([PF.centre(p)[2] for p in group]))
    for p in group:
        o = D.opts_of(p)
        for v in [p[3]] + [o[e] for e in ("from", "to") if e in o]:
            v[2] = z if straight else v[2] - mean + z


def side_repair(parts, pdoc, log):
    bz, groups = body_z(parts), D.groups(parts)
    k = D.height_of([p for p in parts if not PF.is_prop(p)] or parts) / sheet_height(pdoc)
    for name, spec, sheet in side_rows(parts, pdoc):
        if spec == sheet:
            continue
        z, straight = prop_target(pdoc, name, sheet, bz, k)
        place_z(groups[name], z, straight)
        log.append(("prop_side", name, f"{'front' if spec > 0 else 'back' if spec < 0 else 'at the body'}",
                    f"{'front' if sheet > 0 else 'back'}, z {z:+.2f}{', upright' if straight else ''}"))


# ------------------------------------------------------------------ arm_pose

def joint_xy(pdoc, name):
    xyz = ((pdoc.get("joints") or {}).get(name) or {}).get("xyz")
    return None if not xyz else (xyz[0], xyz[1])


def sheet_arm(pdoc, side, segment):
    """(dx, dy) of the sheet's bone in the front plane, or None when a joint is missing."""
    _, a, b = segment
    p, q = joint_xy(pdoc, f"{a}.{side}"), joint_xy(pdoc, f"{b}.{side}")
    return None if p is None or q is None else (q[0] - p[0], q[1] - p[1])


def arm_part(parts, bone):
    """The non-prop prism / cyl / frustum on `bone` that carries from / to."""
    return next((p for p in parts if p[0] == bone and not PF.is_prop(p) and p[1] in ("prism", "cyl", "frustum")
                 and "from" in D.opts_of(p) and "to" in D.opts_of(p)), None)


def angle_of(v):
    return math.degrees(math.atan2(v[1], v[0]))


def turn_error(a, b):
    return abs((angle_of(a) - angle_of(b) + 180) % 360 - 180)


def arm_rows(parts, pdoc):
    """[(bone, spec angle, sheet angle, error degrees)] of the arm / forearm bones whose sheet projection is long enough to read."""
    k = D.height_of(parts) / float(pdoc.get("H") or D.height_of(parts))
    out = []
    for side in "LR":
        for segment in ARM_SEGMENTS:
            bone, part = f"{segment[0]}.{side}", arm_part(parts, f"{segment[0]}.{side}")
            sheet = sheet_arm(pdoc, side, segment)
            if part is None or sheet is None or math.hypot(*sheet) * k < ARM_MIN * D.height_of(parts):
                continue
            o = D.opts_of(part)
            spec = (o["to"][0] - o["from"][0], o["to"][1] - o["from"][1])
            if math.hypot(*spec) > 1e-6:
                out.append((bone, angle_of(spec), angle_of(sheet), turn_error(spec, sheet)))
    return out


def arm_checks(parts, pdoc, family):
    if family != "biped":
        return [], {"arm_pose": f"rig {family}"}
    rows = arm_rows(parts, pdoc) if pdoc else []
    if not rows:
        return [], {"arm_pose": "no arm bone with from/to and a sheet joint pair (parts.json xyz)"}
    bad = [f"{b} spec {s:+.0f} deg vs sheet {t:+.0f} deg (off {e:.0f})" for b, s, t, e in rows if e > ARM_ERR]
    return [("arm_pose", not bad, f"{bad or 'every arm bone'} within {ARM_ERR:.0f} deg of the sheet's, front plane ({len(rows)} measured)")], {}


def turn_xy(part, pivot, delta, move):
    """Part turned by `delta` degrees about pivot (x, y); a prop (`move` given) only slides by `move` = (dx, dy)."""
    o = D.opts_of(part)
    c, s = math.cos(math.radians(delta)), math.sin(math.radians(delta))
    points = [part[3]] + [o[e] for e in ("from", "to") if e in o]
    for v in points:
        if move is not None:
            v[0], v[1] = v[0] + move[0], v[1] + move[1]
        else:
            x, y = v[0] - pivot[0], v[1] - pivot[1]
            v[0], v[1] = pivot[0] + x * c - y * s, pivot[1] + x * s + y * c


def arm_followers(parts, side):
    """Parts that ride on a bone's end: the forearm's (and hand's) when the arm turns, the hand's when the forearm turns."""
    bones = {f"forearm.{side}", f"hand.{side}"}
    return [p for p in parts if p[0] in bones]


def arm_turn(parts, side, segment, delta):
    bone = f"{segment[0]}.{side}"
    part = arm_part(parts, bone)
    pivot = tuple(D.opts_of(part)["from"][:2])
    end = list(D.opts_of(part)["to"][:2])
    group = [p for p in parts if p[0] == bone and not PF.is_prop(p)]
    moved = group + [p for p in arm_followers(parts, side) if p not in group]
    for p in group:
        turn_xy(p, pivot, delta, None)
    new_end = D.opts_of(part)["to"][:2]
    slide = (new_end[0] - end[0], new_end[1] - end[1])
    for p in moved:
        if p in group:
            continue
        turn_xy(p, pivot, delta, slide if PF.is_prop(p) else None)


def arm_repair(parts, pdoc, log):
    for side in "LR":
        for segment in ARM_SEGMENTS:
            bone = f"{segment[0]}.{side}"
            row = next((r for r in arm_rows(parts, pdoc) if r[0] == bone), None)
            if row is None or row[3] <= ARM_ERR:
                continue
            delta = (row[2] - row[1] + 180) % 360 - 180
            arm_turn(parts, side, segment, delta)
            log.append(("arm_pose", bone, f"{row[1]:+.0f} deg (sheet {row[2]:+.0f})", f"turned {delta:+.0f} deg"))


# ------------------------------------------------------------------ part_exists

def to_lab(rgb):
    """CIELAB (D65) of uint8 sRGB, shape (..., 3)."""
    c = np.asarray(rgb, float) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    xyz = c @ np.array([[0.4124, 0.2126, 0.0193], [0.3576, 0.7152, 0.1192], [0.1805, 0.0722, 0.9505]]) / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def hex_rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def panels(sheet, layout="unit"):
    """{view: (rgb crop, figure mask crop)} of the front and back panels, cropped the way parts.json's fractions are (parts_fit.panel_rect)."""
    key = str(sheet)
    if not pathlib.Path(sheet).exists():
        return {}
    if key not in _PANELS:
        import parts_fit
        from silhouette import concept_panels, read_rgba
        try:
            masks = concept_panels(pathlib.Path(sheet), layout=layout)
        except SystemExit:
            _PANELS[key] = {}
            return {}
        rgb = read_rgba(sheet, 768)[..., :3]
        out = {}
        for view in ("front", "back"):
            if view in masks:
                x0, y0, x1, y1 = parts_fit.panel_rect(masks[view])
                out[view] = (rgb[y0:y1, x0:x1], masks[view][y0:y1, x0:x1])
        _PANELS[key] = out
    return _PANELS[key]


def sheet_height(pdoc):
    """Height of the sheet's figure less its props (parts.json box3d), the spec's own body height being the other half of the scale."""
    tops = [p["box3d"][1][1] for p in pdoc["parts"] if not p.get("prop") and p.get("box3d")]
    return max(tops, default=float(pdoc.get("H") or 0))


def front_map(pdoc):
    """((ax, bx), (ay, by)): spec metres -> fractions of the front crop (y up), least squares over parts.json box3d x box2d front."""
    xs, fx, ys, fy = [], [], [], []
    for p in pdoc["parts"]:
        b, c = (p.get("box2d") or {}).get("front"), p.get("box3d")
        if b and c:
            xs += [c[0][0], c[1][0]]
            fx += [b[0], b[2]]
            ys += [c[0][1], c[1][1]]
            fy += [b[1], b[3]]
    if len(xs) < 4:
        return None
    return np.polyfit(xs, fx, 1), np.polyfit(ys, fy, 1)


def exist_row(part, colour, view, pan, fmap, scale):
    """(matched area / panel area, matched / box area) of `colour` inside the part's projected, padded box on the panel."""
    rgb, fg = pan
    (lo, hi), (h, w) = PF.bbox(part), fg.shape
    fx, fy = [np.polyval(fmap[0], np.array([lo[0], hi[0]]) * scale)], [np.polyval(fmap[1], np.array([lo[1], hi[1]]) * scale)]
    x0, x1 = sorted(fx[0])
    y0, y1 = sorted(fy[0])
    if view == "back":
        x0, x1 = 1 - x1, 1 - x0
    px, py = BOX_PAD * (x1 - x0), BOX_PAD * (y1 - y0)
    c0, c1 = max(round((x0 - px) * w), 0), min(round((x1 + px) * w), w)
    r0, r1 = max(round((1 - y1 - py) * h), 0), min(round((1 - y0 + py) * h), h)
    if c1 <= c0 or r1 <= r0:
        return 0.0, 0.0
    near = (np.linalg.norm(to_lab(rgb[r0:r1, c0:c1]) - to_lab(np.array(colour)), axis=-1) <= EXIST_DE) & fg[r0:r1, c0:c1]
    return float(near.sum()) / (h * w), float(near.sum()) / max((r1 - r0) * (c1 - c0), 1)


def part_colour(part, doc):
    """RGB of the part's material, or None for skin / unknown material."""
    slot = (doc.get("palette") or {}).get(part[4])
    if not isinstance(slot, dict) or slot.get("surface") == "skin" or not slot.get("color"):
        return None
    return hex_rgb(slot["color"])


def missing_parts(parts, doc, pdoc, sheet):
    """[(part, best (panel share, box share))] of the colour-bearing parts with no matching zone in the front or back panel."""
    pan, fmap = panels(sheet), front_map(pdoc)
    if not pan or fmap is None:
        return None
    scale = sheet_height(pdoc) / D.height_of([p for p in parts if not PF.is_prop(p)] or parts)
    drawn = {str(p["name"]).lower() for p in pdoc["parts"] if p.get("prop")}       # a prop the sheet names exists; its palette colour is the author's guess
    out = []
    for p in parts:
        colour = part_colour(p, doc)
        if colour is None or (PF.is_prop(p) and str(p[5]["prop"]).lower() in drawn):
            continue
        best = max((exist_row(p, colour, v, pan[v], fmap, scale) for v in pan), key=lambda r: r[0])
        if best[0] < EXIST_AREA and best[1] < EXIST_LOCAL:
            out.append((p, best))
    return out


def lone_on_bone(parts, part):
    return sum(q[0] == part[0] for q in parts) <= 1


def exist_checks(parts, doc, pdoc, sheet):
    family = doc.get("rig", "biped")
    if family != "biped" and family not in RF.SPIDERS:
        return [], {"part_exists": f"rig {family} (the front-panel projection is the biped's and the spider's)"}
    if not pdoc or not sheet:
        return [], {"part_exists": "no sheet / parts.json"}
    gone = missing_parts(parts, doc, pdoc, sheet)
    if gone is None:
        return [], {"part_exists": "no front / back panel or no box3d pairs"}
    names = [f"{p[0]} {p[1]} {p[4]} ({s[0]:.1%} of the panel, {s[1]:.0%} of its box)" for p, s in gone]
    return [("part_exists", not gone or not EXIST_BLOCKING, f"{'' if EXIST_BLOCKING else 'report only: '}{names or 'every coloured part'} {'has no zone of its colour in the sheet' if gone else 'has its colour in the sheet'}")], {}


def exist_repair(parts, doc, pdoc, sheet, log):
    gone = missing_parts(parts, doc, pdoc, sheet) or []
    for p, s in gone:
        if lone_on_bone(parts, p):
            continue
        parts.remove(p)
        log.append(("part_exists", f"{p[0]} {p[1]} {p[4]}", f"{s[0]:.1%} of the panel, {s[1]:.0%} of its box in its colour", "reject-part (removed)"))


# ------------------------------------------------------------------ incoherent_part (C6)

def hue_class(rgb):
    r, g, b = [float(x) / 255 for x in rgb]
    mx, mn = max(r, g, b), min(r, g, b)
    d = max(mx - mn, 1e-9)
    h = (60 * ((g - b) / d % 6) if mx == r else 60 * ((b - r) / d + 2) if mx == g else 60 * ((r - g) / d + 4)) % 360
    return HUES[int((h + 22.5) // 45) % 8]


def accent_zones(pan):
    """{hue: (share of the crop, midline offset of the zone's centroid in crop widths)} of the saturated, bright figure pixels of a panel."""
    rgb, fg = pan
    f = rgb.astype(float) / 255
    mx, mn = f.max(axis=2), f.min(axis=2)
    acc = fg & (mx > ACCENT_VAL) & ((mx - mn) / np.maximum(mx, 1e-9) > ACCENT_SAT)
    out = {}
    ys, xs = np.nonzero(acc)
    for hue in HUES:
        sel = np.array([hue_class(rgb[y, x]) == hue for y, x in zip(ys, xs)]) if len(ys) else np.zeros(0, bool)
        if sel.sum() >= ACCENT_AREA * fg.size:
            out[hue] = (float(sel.sum()) / fg.size, float(xs[sel].mean()) / fg.shape[1] - 0.5, 1 - float(ys[sel].mean()) / fg.shape[0])
    return out


def zone_name(pdoc, hue, offset, up):
    """parts.json's name for the zone: the prop whose front box holds the zone's centre (offset from the midline, `up` from the bottom), else '<hue> zone'."""
    for p in pdoc["parts"]:
        b = (p.get("box2d") or {}).get("front")
        if b and b[0] <= 0.5 + offset <= b[2] and b[1] <= up <= b[3] and p.get("prop"):
            return str(p["name"])
    return f"{hue} zone"


def incoherent_parts(sheet, pdoc=None):
    """[{part, front, back, side, ignore}]: accent zones on opposite sides of the body in the front and back panels (character side:
    +x = the character's left; the back panel is mirrored). The panel with more of the zone wins (`side`), the other is in `ignore`."""
    pdoc = pdoc or doc_of(sheet)
    pan = panels(sheet)
    if not pdoc or "front" not in pan or "back" not in pan:
        return []
    f, b = accent_zones(pan["front"]), accent_zones(pan["back"])
    out = []
    for hue in f.keys() & b.keys():
        sf, sb = f[hue][1], -b[hue][1]
        if sf * sb < 0 and min(abs(sf), abs(sb)) > ACCENT_OFF:
            side = "front" if f[hue][0] >= b[hue][0] else "back"
            out.append({"part": zone_name(pdoc, hue, f[hue][1], f[hue][2]), "hue": hue, "front": round(sf, 3), "back": round(sb, 3),
                        "side": side, "ignore": ["back" if side == "front" else "front"]})
    return out


def decided(rows, parts):
    """`rows` with the spec's opts side override applied (a part with opts prop == the zone's name and side front / back)."""
    out = []
    for r in rows:
        r = dict(r)
        for p in parts:
            o = D.opts_of(p)
            if str(o.get("prop", "")).lower() == r["part"].lower() and o.get("side") in ("front", "back"):
                r["side"], r["ignore"], r["by"] = o["side"], ["back" if o["side"] == "front" else "front"], "spec"
        out.append(r)
    return out


def ignored_views(sheet_json, parts=()):
    """{part: [views the gate ignores for it]} from refs/<id>/sheet.json "part_coherence", the spec's override applied (for silhouette / L15-1)."""
    return {r["part"]: r["ignore"] for r in decided((sheet_json or {}).get("part_coherence", []), parts)}


def save(sheet, rows):
    """Merge `rows` into refs/<id>/sheet.json as "part_coherence"; the file's other keys stay. Returns the path, or None when nothing changed."""
    path = pathlib.Path(sheet).with_name("sheet.json")
    doc = json.loads(path.read_text()) if path.exists() else {}
    if doc.get("part_coherence") == rows:
        return None
    path.write_text(json.dumps({**doc, "part_coherence": rows}, indent=2))
    return path


def coherence_checks(parts, sheet, pdoc):
    if not sheet or not pdoc:
        return [], {"incoherent_part": "no sheet / parts.json"}
    rows = decided(incoherent_parts(sheet, pdoc), parts)
    if not rows:
        return [], {"incoherent_part": "no accent zone on opposite sides in the front and back panels"}
    text = "; ".join(f"{r['part']}: front {r['front']:+.2f}, back {r['back']:+.2f} -> {r['side']} wins ({r['by'] if 'by' in r else 'default'}), gate ignores {r['ignore'][0]}" for r in rows)
    return [("incoherent_part", True, f"report only: {text} (override: opts side on the part)")], {}


# ------------------------------------------------------------------ entry points

def checks(parts, doc, sheet, pdoc, na=None):
    out, gone_all = [], {} if na is None else na
    family = doc.get("rig", "biped")
    for got, gone in (side_checks(parts, pdoc) if family == "biped" else ([], {"prop_side": f"rig {family}"}),
                      arm_checks(parts, pdoc, family), exist_checks(parts, doc, pdoc, sheet), coherence_checks(parts, sheet, pdoc)):
        out += got
        gone_all.update(gone)
    return out, gone_all


def repair(parts, doc, sheet, pdoc, failing, log, reject=False):
    """reject-part first when `reject` (part_exists is report-only, so it is not in `failing`; it reads the projection of the spec as it
    came: the other two move props and change its height), then prop_side (z only), then arm_pose (x, y only)."""
    if reject and pdoc and sheet:
        exist_repair(parts, doc, pdoc, sheet, log)
    if "prop_side" in failing:
        side_repair(parts, pdoc, log)
    if "arm_pose" in failing:
        arm_repair(parts, pdoc, log)
    return parts
