#!/usr/bin/env python3
"""Semantic segmentation of an approved sheet: joints and part boxes in 2D, triangulated to 3D.

    python3.14 tools/blender/segment_sheet.py <id> [--rig biped] [--race Human] [--model session:opus]
        [--sheet <sheet.jpg>] [--out refs/<id>] [--masks]

PIPELINE section 23.L5-1. The VLM is a segmenter, not an author (Point QA): ONE call per sheet gets the
front and left panels, each under a 0-1 ruler, and the unit's card; it answers, as strict JSON, the 2D
position of every joint of the rig family, a 2D box per semantic part (hood, torso, tank, pistol...) and
the identity list. Code does the rest: x from the front panel, z from the left one (spec metres, the same
frame massing.py reads: View/side_of), y the mean of both (a gap over COHERENT H is recorded, not hidden),
`depth_order` from where the part's z sits against the torso's. Writes refs/<id>/parts.json (the contract
the other leva-5 items read), refs/<id>/parts-overlay.png and, with --masks, refs/<id>/parts/*.png
(part box x colour zone x figure). Nothing downstream needs the file: without it they keep their old path.
"""
import argparse
import json
import pathlib
import sys
import tempfile
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import massing  # noqa: E402
import rig_families as RF  # noqa: E402
import silhouette as SIL  # noqa: E402
import split_sheet  # noqa: E402

ROOT = HERE.parents[1]
REFS = ROOT / "artifacts/model-sheets/refs"
PROMPTS = ROOT / "artifacts/model-sheets/prompts"
SIZE = split_sheet.SIZE
VIEWS = ("front", "left")
COHERENT = 0.05           # front and left may disagree on a joint's height by this many H before it is logged
DEPTH_NEAR, DEPTH_FAR = 0.04, 0.12   # |dz| from the torso, in H: under NEAR the part is level with it, over FAR it is order 2
ROLES = ("head", "face", "torso", "pelvis", "arm", "leg", "hand", "foot", "wing", "tail", "shell", "prop", "other")
BIPED_TYPES = ("shoulder", "elbow", "wrist", "hip", "knee", "ankle")
JOINTS = {"biped": ["head_top", "chin"] + [f"{t}.{s}" for t in BIPED_TYPES for s in "LR"],
          "spider": [f"leg{i}.{k}" for i in range(1, 9) for k in ("root", "knee")],
          "quadruped": ["head_top", "snout", "tail_tip"] + [f"leg{i}.{k}" for i in range(1, 5) for k in ("root", "knee", "foot")],
          "generic": ["head_top", "snout", "tail_tip", "wing_root.L", "wing_tip.L"]}
SPIDERS = RF.SPIDERS
ZONE_SHARE = 0.2          # a zone names a part when it fills this share of the part's box x figure
RESERVED = {"root"}       # a bone no part hangs from


def family_of(rig):
    return "spider" if rig in SPIDERS else rig if rig in JOINTS else "generic"


# ---- frames: a ruler fraction -> spec metres

class Frames:
    """Fraction (u right, v up) of the front / left crop -> (x, y) and (z, y) in spec metres, the frame
    massing.py builds the pre-spec in (View: rows from the top, s metres per pixel, centre column)."""

    def __init__(self, sheet, H):
        from PIL import Image
        panels = SIL.concept_panels(sheet)
        with Image.open(sheet) as img:
            width, height = img.size
        self.k = (width / SIZE, height / SIZE)
        boxes = split_sheet.panel_boxes(sheet)
        self.crop = {v: split_sheet.scaled(boxes[v], *self.k, width, height) for v in VIEWS}
        self.H = H
        self.front = massing.View(panels["front"], H)
        self.front.recentre(0.0, 0.08 * H)
        self.side = massing.side_of(panels["left"], H)
        self.top = {"front": self._top(panels["front"]), "left": self._top(panels["left"])}
        self.panels = panels

    @staticmethod
    def _top(mask):
        return int(np.nonzero(massing._without_specks(mask))[0].min())

    def px(self, view, u, v):
        """Pixel (x, y) of the 768 square the masks live in."""
        x0, y0, x1, y1 = self.crop[view]
        return (x0 + u * (x1 - x0)) / self.k[0], (y0 + (1 - v) * (y1 - y0)) / self.k[1]

    def front_xy(self, u, v):
        x, y = self.px("front", u, v)
        return ((x - self.front.cx) * self.front.s, self.H - (y - self.top["front"]) * self.front.s)

    def left_zy(self, u, v):
        x, y = self.px("left", u, v)
        s = self.side.v.s
        return ((x - self.side.zero) * s * self.side.sign, self.H - (y - self.top["left"]) * s)



# ---- the call

def leg_hint(rig, name):
    """Where the rig puts a leg: 'forward/side/rear, on the unit's left (+x, image right in the front panel)'."""
    table = {b: head for b, _, head, _ in RF.FAMILIES[rig]}
    x, _, z = table[name + ".upper"]
    along = "forward" if z > 0.15 else "rear" if z < -0.15 else "middle"
    return f"{along}, unit's {'left' if x > 0 else 'right'}"


def joint_lines(rig, names):
    out = []
    for n in names:
        leg = n.split(".")[0]
        hint = f" ({leg} of the rig: {leg_hint(rig, leg)})" if leg.startswith("leg") and rig in RF.FAMILIES else ""
        out.append(f"- {n}{hint}")
    return "\n".join(out)


BRIEF = """You segment a character concept sheet. You do NOT design anything: you point at what is drawn.

Image 1 = FRONT panel, image 2 = LEFT-side panel of the same {kind} ({name}). Each has a ruler: 0 to 1 across
(x, left to right) and 0 to 1 up (y, 0 = bottom edge, 1 = top edge), grid lines every 0.1. Report every
coordinate as [x, y] in those ruler units, read at the grid, to two decimals. Boxes are [x0, y0, x1, y1]
with x0 < x1 and y0 < y1. Use null for what the panel does not show (hidden by the body, off the figure):
never guess a point you cannot see. In the front panel the unit's own LEFT (.L) is on the image RIGHT.
The left panel shows the unit's left side: .R limbs are mostly hidden there (null).

JOINTS, the 2D point of each, in both panels (the pivot where the two segments meet, on the body's centre line):
{joints}

PARTS: one entry per distinct semantic part you can SEE, the box tight around it in each panel it shows in.
Always the head/hood/helmet, face or mask when it is a separate shape, torso, pelvis/skirt/coat, each arm,
each leg, each foot/boot, each hand; plus EVERY prop and accessory of the card below as a part of its own
(role "prop", prop true, anchor = where it is attached: "back", "belt", "chest", "hand.R", "hand.L", "head"...),
a held item or a back-mounted tank gets its own box even when it overlaps the body. `bone` is the rig bone
the part rides on, one of: {bones}. `depth_hint` = -2..2, how far the part sits in front (+) or behind (-)
the torso seen from the front, 0 = level with the torso; judge it from the left panel (z along the facing
direction) and the overlaps in the front panel.

IDENTITY: 4-8 short phrases, the details that make THIS unit recognisable at a glance and that a model must
keep (props, the eyes/lenses, badges, valves, scars). Only what the drawing shows.

CARD
{card}

Reply with the JSON object only."""


def box_schema():
    return {"anyOf": [{"type": "null"}, {"type": "array", "minItems": 4, "maxItems": 4, "items": {"type": "number"}}]}


def point_schema():
    return {"anyOf": [{"type": "null"}, {"type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "number"}}]}


def schema_of(names, bones):
    joint = {"type": "object", "required": ["name", "front", "left"], "additionalProperties": False,
             "properties": {"name": {"enum": names}, "front": point_schema(), "left": point_schema()}}
    part = {"type": "object", "additionalProperties": False,
            "required": ["name", "role", "bone", "prop", "anchor", "depth_hint", "box_front", "box_left"],
            "properties": {"name": {"type": "string"}, "role": {"enum": list(ROLES)}, "bone": {"enum": bones},
                           "prop": {"type": "boolean"}, "anchor": {"type": "string"},
                           "depth_hint": {"type": "integer", "minimum": -2, "maximum": 2},
                           "box_front": box_schema(), "box_left": box_schema()}}
    return {"type": "object", "required": ["joints", "parts", "identity"], "additionalProperties": False,
            "properties": {"joints": {"type": "array", "items": joint},
                           "parts": {"type": "array", "minItems": 3, "items": part},
                           "identity": {"type": "array", "minItems": 1, "maxItems": 10, "items": {"type": "string"}}}}


def check_reply(text):
    """The parsed reply, or ValueError (quoted back in the one resend): a coordinate off the ruler,
    a box turned inside out, an unknown reply shape."""
    doc = json.loads(text[text.index("{"):text.rindex("}") + 1])
    for j in doc["joints"]:
        for view in VIEWS:
            if j[view] is not None and not all(0 <= c <= 1 for c in j[view]):
                raise ValueError(f"joint {j['name']} {view} {j[view]} is off the 0-1 ruler")
    for p in doc["parts"]:
        for view in VIEWS:
            b = p["box_" + view]
            if b is not None and not (0 <= b[0] < b[2] <= 1 and 0 <= b[1] < b[3] <= 1):
                raise ValueError(f"part {p['name']} box_{view} {b} must be [x0, y0, x1, y1] on the 0-1 ruler, x0<x1, y0<y1")
    return doc


def ruler_image(src, out, size=1100):
    """`src` with a 0.1 grid and 0-1 labels (y up) burnt in, scaled so its long side is `size`."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.open(src).convert("RGB")
    k = size / max(img.size)
    img = img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS)
    draw = ImageDraw.Draw(img, "RGBA")
    font = ImageFont.load_default(size=14)
    for i in range(11):
        t = i / 10
        x, y = round(t * (img.width - 1)), round((1 - t) * (img.height - 1))
        edge = (255, 0, 0, 150) if i == 5 else (0, 120, 255, 90)
        draw.line([(x, 0), (x, img.height)], fill=edge, width=1)
        draw.line([(0, y), (img.width, y)], fill=edge, width=1)
        for ty in (2, img.height - 18):
            draw.text((min(x + 2, img.width - 28), ty), f"{t:.1f}", fill=(220, 0, 90, 255), font=font)
        for tx in (2, img.width - 30):
            draw.text((tx, min(y + 1, img.height - 16)), f"{t:.1f}", fill=(220, 0, 90, 255), font=font)
    img.save(out)
    return out


def card_text(unit, props_json=None):
    """The card the VLM reads: the compendium's redesign paragraph and the props list."""
    lines = []
    try:
        sys.path.insert(0, str(ROOT / "artifacts/model-sheets"))
        import unit_facts
        facts = unit_facts.facts(unit)
    except (ImportError, OSError, KeyError, ValueError):
        facts = None
    if facts:
        lines += [f"{facts['name']} ({facts['race']}, tier {facts['tier']}): {facts['redesign']}"]
    path = props_json or PROMPTS / unit / "props.json"
    if pathlib.Path(path).exists():
        lines += [f"Prop: {p['name']} - {p['where']}" for p in json.loads(pathlib.Path(path).read_text())]
    return "\n".join(lines) or "(no card for this unit: name every prop you can see)"


# ---- triangulation

def triangulate_point(front, left, frames, mirror_z=None):
    """{'front', 'left', 'xyz'} of one joint. y = mean of both views; xyz is None unless x and z are known
    (z of a hidden .R joint comes from `mirror_z`, its .L twin's). Second value: |dy| in H when the views differ."""
    fx = frames.front_xy(*front) if front else None
    lz = frames.left_zy(*left) if left else None
    z = lz[0] if lz else mirror_z
    out = {"front": front, "left": left, "xyz": None}
    if fx is None or z is None:
        return out, None
    ys = [fx[1]] + ([lz[1]] if lz else [])
    out["xyz"] = [round(fx[0], 3), round(float(np.mean(ys)), 3), round(z, 3)]
    if not lz:
        out["z_from"] = "mirror"
    return out, (abs(fx[1] - lz[1]) / frames.H if lz else None)


def triangulate_joints(raw, frames):
    """({name: joint}, [incoherences]) for the reply's joints; a .R joint takes its .L twin's z when it is hidden."""
    by = {j["name"]: j for j in raw}
    joints, bad = {}, []
    for name in sorted(by, key=lambda n: n.endswith(".R")):     # .L first: the twin's z is known by then
        j = by[name]
        twin = joints.get(name[:-2] + ".L") if name.endswith(".R") else None
        mirror = twin["xyz"][2] if twin and twin["xyz"] and not j["left"] else None
        joints[name], gap = triangulate_point(j["front"], j["left"], frames, mirror)
        if gap is not None and gap > COHERENT:
            bad.append({"joint": name, "dy_H": round(gap, 3)})
    return {n: joints[n] for n in by}, bad


def box3d(front, left, frames, mirror_z=None):
    """[[X0, Y0, Z0], [X1, Y1, Z1]] of a part or None: x from the front box, z from the left one (or the
    twin's), y the mean of the two boxes' ranges."""
    if not front:
        return None, None
    (x0, ya), (x1, yb) = frames.front_xy(front[0], front[1]), frames.front_xy(front[2], front[3])
    z, ys = mirror_z, [(ya, yb)]
    if left:
        (za, yc), (zb, yd) = frames.left_zy(left[0], left[1]), frames.left_zy(left[2], left[3])
        z, ys = sorted((za, zb)), ys + [(yc, yd)]
    if z is None:
        return None, None
    y = [float(np.mean([p[i] for p in ys])) for i in (0, 1)]
    gap = max(abs(ys[0][i] - ys[-1][i]) for i in (0, 1)) / frames.H
    box = [[round(min(x0, x1), 3), round(min(y), 3), round(z[0], 3)], [round(max(x0, x1), 3), round(max(y), 3), round(z[1], 3)]]
    return box, gap


def depth_order(part, torso_z, H):
    """(order, source): from the part's z centre against the torso's (left panel), else the VLM's hint."""
    box = part["box3d"]
    if box is None or torso_z is None or part.get("z_from") == "mirror":
        return part["_hint"], "vlm"
    dz = ((box[0][2] + box[1][2]) / 2 - torso_z) / H
    mag = 0 if abs(dz) < DEPTH_NEAR else 1 if abs(dz) < DEPTH_FAR else 2
    return int(np.sign(dz)) * mag, "left"


def triangulate_parts(raw, frames):
    parts, bad = [], []
    for p in raw:
        box, gap = box3d(p["box_front"], p["box_left"], frames)
        parts.append({"name": p["name"], "role": p["role"], "bone": p["bone"], "prop": bool(p["prop"]),
                      "anchor": p["anchor"] or None, "box2d": {v: p["box_" + v] for v in VIEWS if p["box_" + v]},
                      "box3d": box, "_hint": p["depth_hint"]})
        if gap is not None and gap > COHERENT:
            bad.append({"part": p["name"], "dy_H": round(gap, 3)})
    mirror_boxes(parts, raw, frames)
    torso = next((p for p in parts if p["role"] == "torso" and p["box3d"]), None)
    tz = (torso["box3d"][0][2] + torso["box3d"][1][2]) / 2 if torso else None
    for p in parts:
        p["depth_order"], src = depth_order(p, tz, frames.H)
        p["depth_src"] = src
        del p["_hint"]
    return parts, bad


def mirror_boxes(parts, raw, frames):
    """A .R part the left panel hides takes the z range of its .L twin (same role, bone swapped)."""
    for p, r in zip(parts, raw):
        if p["box3d"] is not None or not r["box_front"] or not p["bone"].endswith(".R"):
            continue
        twin = next((q for q in parts if q["role"] == p["role"] and q["bone"] == p["bone"][:-2] + ".L" and q["box3d"]), None)
        if twin:
            p["box3d"], _ = box3d(r["box_front"], None, frames, [twin["box3d"][0][2], twin["box3d"][1][2]])
            p["z_from"] = "mirror"


def summary(joints, family):
    """How many joints were read: both views (xyz), one view, none; and, for a biped, joint TYPES with an xyz on at least one side."""
    both = sum(1 for j in joints.values() if j["xyz"])
    one = sum(1 for j in joints.values() if not j["xyz"] and (j["front"] or j["left"]))
    out = {"expected": len(JOINTS[family]), "xyz": both, "one_view": one,
           "none": len(JOINTS[family]) - both - one}
    if family == "biped":
        types = {n.split(".")[0] for n, j in joints.items() if j["xyz"]}
        out["types_xyz"] = f"{len(types)}/{len(BIPED_TYPES) + 2}"
    return out


def on_figure(joints, frames):
    """'n/m': the 2D joints that fall on the figure's silhouette (a joint is inside the body, so one off it is wrong)."""
    hit = tot = 0
    for j in joints.values():
        for view in VIEWS:
            if j[view]:
                x, y = frames.px(view, *j[view])
                m = frames.panels[view]
                tot += 1
                hit += bool(0 <= int(y) < m.shape[0] and 0 <= int(x) < m.shape[1] and m[int(y), int(x)])
    return f"{hit}/{tot}"


# ---- masks and overlay

def zone_data(sheet, frames):
    """(hexes, {view: label image}) of the sheet's colour zones, labelled on the 768 square."""
    hexes, centres, _ = SIL.zone_palette(sheet)
    rgb = SIL.read_rgba(sheet, SIZE)[..., :3].astype(float) / 255.0
    return hexes, {v: SIL.zone_labels(rgb, frames.panels[v], centres) for v in VIEWS}


def part_region(box, view, frames):
    """Boolean 768-square image of the part's 2D box (fractions of the view's crop)."""
    (x0, y0), (x1, y1) = frames.px(view, box[0], box[3]), frames.px(view, box[2], box[1])
    out = np.zeros((SIZE, SIZE), bool)
    out[max(int(y0), 0):int(np.ceil(y1)), max(int(x0), 0):int(np.ceil(x1))] = True
    return out


def zone_of(region, labels, figure, k):
    """(zone index + 1, region share) that stands out in `region`: the zone of at least ZONE_SHARE of the region
    with the highest lift over its share of the whole figure (a dark coat is mostly the dominant zone; a grey tank
    on it is the rare one), else the most common one."""
    counts = np.bincount(labels[region], minlength=k + 1)[1:] / max(int(region.sum()), 1)
    base = np.bincount(labels[figure], minlength=k + 1)[1:] / max(int(figure.sum()), 1)
    lift = np.where(counts >= ZONE_SHARE, counts / np.maximum(base, 1e-3), 0.0)
    best = int(lift.argmax()) if lift.max() > 0 else int(counts.argmax())
    return best + 1, float(lift[best])


def add_zones(parts, hexes, labels, frames, mask_dir=None):
    """Each part's colour zone ('zone': hex) from its box x figure in the view where it stands out most, and with
    `mask_dir` the mask (box x that zone) as a 768 square png per view."""
    from PIL import Image
    for p in parts:
        found = {}
        for view in VIEWS:
            if view not in p["box2d"]:
                continue
            region = part_region(p["box2d"][view], view, frames) & frames.panels[view]
            if region.any():
                found[view] = (region, *zone_of(region, labels[view], frames.panels[view], len(hexes)))
        best = max(found.values(), key=lambda f: f[2], default=None)
        p["zone"] = hexes[best[1] - 1] if best else None
        for view, (region, zone, _) in found.items() if mask_dir else ():
            mask_dir.mkdir(parents=True, exist_ok=True)
            name = "".join(c if c.isalnum() else "_" for c in p["name"])
            Image.fromarray(((region & (labels[view] == (best[1] if best else zone))) * 255).astype(np.uint8)).save(mask_dir / f"{name}-{view}.png")


def overlay(sheet, doc, frames, out):
    """front | left crops of the sheet with the joints (dots + names) and the part boxes drawn on them."""
    from PIL import Image, ImageDraw, ImageFont
    full = Image.open(sheet).convert("RGB")
    font = ImageFont.load_default(size=13)
    tiles = []
    for view in VIEWS:
        tile = full.crop(frames.crop[view])
        k = 900 / tile.height
        tile = tile.resize((round(tile.width * k), 900), Image.LANCZOS)
        d = ImageDraw.Draw(tile)
        at = lambda u, v: (u * (tile.width - 1), (1 - v) * (tile.height - 1))   # noqa: E731
        for i, p in enumerate(doc["parts"]):
            if view in p["box2d"]:
                b = p["box2d"][view]
                colour = (255, 140, 0) if p["prop"] else (0, 170, 90)
                d.rectangle([*at(b[0], b[3]), *at(b[2], b[1])], outline=colour, width=2)
                d.text(at(b[0], b[3]), p["name"], fill=colour, font=font)
        for name, j in doc["joints"].items():
            if j[view]:
                x, y = at(*j[view])
                d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(255, 0, 0) if j["xyz"] else (255, 0, 255))
                d.text((x + 6, y - 6), name, fill=(200, 0, 0), font=font)
        tiles.append(tile)
    sheet_img = Image.new("RGB", (sum(t.width for t in tiles) + 10, 900), (255, 255, 255))
    sheet_img.paste(tiles[0], (0, 0))
    sheet_img.paste(tiles[1], (tiles[0].width + 10, 0))
    sheet_img.save(out)
    return out


# ---- run

def segment(unit, sheet, rig="biped", race="", model="session:opus", ask=None, work=None, masks_dir=None, out_dir=None):
    """parts.json dict for `unit`. `ask(model, brief, images, schema, check)` is spec_pipeline.ask by default
    (tests pass a stub). Writes the ruler panels into `work`, parts.json / overlay into `out_dir` when given."""
    if ask is None:
        import spec_pipeline
        ask = spec_pipeline.ask
    family = family_of(rig)
    if rig in SPIDERS:
        RF.scale_spider(rig, SIL.measure_spider(sheet))
    H = RF.top(rig) if rig in RF.FAMILIES else 2.0
    work = pathlib.Path(work or out_dir or ".")
    work.mkdir(parents=True, exist_ok=True)
    panels = split_sheet.split(sheet, work / "panels", unit)
    images = [ruler_image(panels[v], work / f"ruler-{v}.png") for v in VIEWS]
    names, bones = JOINTS[family], [b for b in (RF.bones(rig) if rig in RF.FAMILIES else ["root", "head"]) if b not in RESERVED]
    brief = BRIEF.format(kind=family, name=unit, joints=joint_lines(rig, names), bones=", ".join(bones), card=card_text(unit))
    t0 = time.time()
    reply = ask(model, brief, images, schema_of(names, bones), check=check_reply)
    seconds = round(time.time() - t0, 1)
    raw = check_reply(reply)
    if out_dir:
        (pathlib.Path(out_dir) / "parts-reply.json").write_text(json.dumps(raw, indent=1))
    frames = Frames(sheet, H)
    joints, bad_joints = triangulate_joints(raw["joints"], frames)
    parts, bad_parts = triangulate_parts(raw["parts"], frames)
    hexes, labels = zone_data(sheet, frames)
    add_zones(parts, hexes, labels, frames, masks_dir)
    doc = {"unit": unit, "H": round(H, 3), "views": list(VIEWS), "rig": rig, "joints": joints, "parts": parts,
           "identity": raw["identity"], "incoherent": bad_joints + bad_parts, "joints_read": {**summary(joints, family), "on_figure": on_figure(joints, frames)},
           "meta": {"model": model, "seconds": seconds, "sheet": pathlib.Path(sheet).name,
                    "panel_crop": {v: list(frames.crop[v]) for v in VIEWS}}}
    if out_dir:
        out_dir = pathlib.Path(out_dir)
        (out_dir / "parts.json").write_text(json.dumps(doc, indent=1))
        overlay(sheet, doc, frames, out_dir / "parts-overlay.png")
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("unit")
    ap.add_argument("--rig", default="biped", choices=sorted(RF.FAMILIES))
    ap.add_argument("--race", default="")
    ap.add_argument("--model", default="session:opus")
    ap.add_argument("--sheet", type=pathlib.Path, default=None)
    ap.add_argument("--out", type=pathlib.Path, default=None)
    ap.add_argument("--work", type=pathlib.Path, default=None)
    ap.add_argument("--masks", action="store_true")
    ap.add_argument("--reply", type=pathlib.Path, default=None, help="re-triangulate a saved parts-reply.json: no VLM call")
    a = ap.parse_args()
    out = a.out or REFS / a.unit
    sheet = a.sheet or REFS / a.unit / "sheet.jpg"
    import spec_pipeline
    before = dict(spec_pipeline.USAGE)
    saved = a.reply.read_text() if a.reply else None
    old_meta = json.loads((out / "parts.json").read_text())["meta"] if saved and (out / "parts.json").exists() else {}
    doc = segment(a.unit, sheet, a.rig, a.race, a.model, ask=(lambda *_, **__: saved) if saved else None, work=a.work or tempfile.mkdtemp(prefix="segment-"),
                  masks_dir=out / "parts" if a.masks else None, out_dir=out)
    doc["meta"]["tokens"] = {k: v - before.get(k, 0) for k, v in spec_pipeline.USAGE.items() if v - before.get(k, 0)}
    doc["meta"]["resent"] = spec_pipeline.STATS["resent"]
    doc["meta"] |= {k: v for k, v in old_meta.items() if saved and k in ("seconds", "tokens", "resent")}   # a re-triangulation keeps what the VLM call cost
    (out / "parts.json").write_text(json.dumps(doc, indent=1))
    print(f"{a.unit}: joints {doc['joints_read']}  parts {len(doc['parts'])}  incoherent {len(doc['incoherent'])}"
          f"  {doc['meta']['seconds']} s  tokens {doc['meta']['tokens']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
