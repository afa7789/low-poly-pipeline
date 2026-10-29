#!/usr/bin/env python3
"""Part masks and depth order for fit_spec (PIPELINE 23.L5-4).

`refs/<id>/parts.json` (L5-1) says, per semantic part, where it is in the front and left panels
(`box2d`, fractions of the split_sheet crop, y up), in space (`box3d`, metres, spec axes) and how far
from the camera it sits in the front view (`depth_order`, 0 = torso, positive = nearer). Three uses:

  * `associate`: each spec part gets the semantic part it is (same bone family, close to its box3d,
    same colour zone) - the way a human reads "this lathe behind the torso is the tank".
  * `PartTerms.term`: the fit objective gains "the visible projection of each part lies inside the 2D mask
    of its semantic part" (mask = box2d x the sheet's colour zone), the zone term of fit_spec.Zones
    generalised from one colour to one part. "Visible" = painted far to near, so a part behind another
    only counts where it shows (a tank behind the torso is not asked to be where the torso is).
  * `PartTerms.broken`: pairs (A in front of B, boxes overlapping in the front panel) are a hard
    constraint on the spec parts' z, held the way the preflight rules are.

Everything is optional: without a parts.json the callers behave as before.
"""
import json
import pathlib

import numpy as np
from PIL import Image, ImageDraw

import silhouette
import split_sheet

PART_VIEWS = ("front", "left")
# nearness to the camera of a point in Blender axes (x right, -y forward, z up); larger = nearer
NEAR = {"front": lambda w: -w[:, 1], "back": lambda w: w[:, 1], "left": lambda w: -w[:, 0]}
BONE_FAMILY = {"forearm": "arm", "hand": "arm", "thigh": "leg", "shin": "leg", "foot": "leg"}
BONE_MISS = 0.15        # association cost (in H) of a part on another bone family
ZONE_BONUS = 0.05       # ... bonus of the part whose colour zone is the spec part's material zone
ASSOC_REACH = 0.10      # a spec part farther than this (H) from every box3d belongs to no part
MAX_LABELS = 254        # the visible-part canvas is 8-bit


def load(sheet, path=None):
    """The sheet's parts.json (next to it, or `path`), or None."""
    path = pathlib.Path(path) if path else pathlib.Path(sheet).with_name("parts.json")
    return json.loads(path.read_text()) if path.exists() else None


def family(bone):
    base, _, side = bone.partition(".")
    return f"{BONE_FAMILY.get(base, base)}.{side}"


def box_gap(point, box):
    """Distance from a point to an axis-aligned box (0 inside)."""
    lo, hi = np.asarray(box[0], float), np.asarray(box[1], float)
    return float(np.linalg.norm(np.maximum(np.maximum(lo - point, point - hi), 0.0)))


def associate(spec_parts, centres, parts_doc, height, zone_of=None, zone_idx=None):
    """[index into parts_doc["parts"] or None] per spec part. `centres` are the spec parts' centres in spec
    axes (right, up, forward); the boxes scale by height / H. Cost = gap to the box (in H) + BONE_MISS off
    the bone family - ZONE_BONUS on the zone, smallest box on ties."""
    scale = height / float(parts_doc.get("H") or height)
    found = []
    for part, c in zip(spec_parts, centres):
        best = None
        for k, p in enumerate(parts_doc["parts"]):
            if not p.get("box3d"):      # hidden in the sheet (a prop behind the body, a leg under it): nothing to associate to
                continue
            box = [np.asarray(b, float) * scale for b in p["box3d"]]
            gap = box_gap(np.asarray(c, float), box) / height
            if gap > ASSOC_REACH:
                continue
            cost = (gap + (0 if family(p["bone"]) == family(part[0]) else BONE_MISS)
                    - (ZONE_BONUS if zone_idx is not None and zone_idx.get(p.get("zone")) == (zone_of or {}).get(part[4]) else 0)
                    + 1e-3 * float(np.prod(box[1] - box[0])))
            if best is None or cost < best[0]:
                best = (cost, k)
        found.append(best[1] if best else None)
    return found


def front_pairs(parts_doc, assoc, order=None):
    """[(i, j)]: spec part i must be nearer the front camera than part j - their semantic parts differ in
    depth_order and their front boxes overlap. `order` ({spec part index: depth_order}) replaces the
    parts.json depth_order (depth_map.py, --depth)."""
    boxes = [p.get("box2d", {}).get("front") for p in parts_doc["parts"]]
    order = order or {i: parts_doc["parts"][a].get("depth_order", 0) for i, a in enumerate(assoc) if a is not None}

    def overlap(a, b):
        return a and b and a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
    return [(i, j) for i, a in enumerate(assoc) for j, b in enumerate(assoc)
            if a is not None and b is not None and i in order and j in order and order[i] > order[j]
            and overlap(boxes[a], boxes[b])]


def panel_rect(fig):
    """Pixel rect (x0, y0, x1, y1) of the split_sheet crop of a panel mask (figure box + margin)."""
    ys, xs = np.where(fig)
    box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    return split_sheet.scaled(box, 1, 1, *fig.shape[::-1])


def part_mask(fig, box):
    """Normalized canvas mask: the figure's pixels inside `box` (fractions of the crop, y up), laid out
    exactly as silhouette.normalize lays out the figure."""
    x0, y0, x1, y1 = panel_rect(fig)
    w, h = x1 - x0, y1 - y0
    inside = np.zeros(fig.shape, bool)
    inside[max(round(y1 - box[3] * h), 0):max(round(y1 - box[1] * h), 0),
           max(round(x0 + box[0] * w), 0):max(round(x0 + box[2] * w), 0)] = True
    return silhouette.normalize(np.where(fig, inside + 1, 0)) == 2


class PartTerms:
    """The fit's view of parts.json: masks per (spec part, view), the front depth pairs, the term."""

    def __init__(self, spec_parts, centres, sheet, parts_doc, zones, height):
        assert len(spec_parts) <= MAX_LABELS
        zone_idx = {p["zone"]: int(silhouette.nearest(np.array([[int(p["zone"][i:i + 2], 16) / 255 for i in (1, 3, 5)]]),
                                                       zones.centres)[0])
                    for p in parts_doc["parts"] if p.get("zone")}
        self.assoc = associate(spec_parts, centres, parts_doc, height, zones.zone_of, zone_idx)
        self.pairs = front_pairs(parts_doc, self.assoc)
        figs = {v: p for v, p in silhouette.concept_panels(sheet).items() if v in PART_VIEWS}
        self.masks = {}
        for i, a in enumerate(self.assoc):
            part = parts_doc["parts"][a] if a is not None else {}
            for v, box in part.get("box2d", {}).items():
                if v in figs and v in zones.labels:
                    m = part_mask(figs[v], box)
                    z = zone_idx.get(part.get("zone"))
                    m = m & (zones.labels[v] == z) if z else m
                    if m.any():
                        self.masks[i, v] = m
        self.views = sorted({v for _, v in self.masks})

    def visible(self, view, hulls, polygons):
        """Label canvas (part index + 1, 0 empty) of the model's view in the proxy's layout (`polygons`: pixel
        outlines per part), painted far to near so the nearer part covers. Never mirrored: a part box is in
        the image's own left/right, as the camera shows it (the silhouette IoU may prefer the mirror)."""
        img = Image.new("L", (silhouette.CANVAS_W, silhouette.CANVAS_H), 0)
        draw = ImageDraw.Draw(img)
        for k in np.argsort([h["near"][view] for h in hulls]):
            draw.polygon([tuple(p) for p in polygons[k]], fill=int(k) + 1)
        return np.asarray(img)

    def shares(self, free, hulls, polygons):
        """{(part, view): share of the part's visible projection that lies inside its part mask} for the
        `free` parts (`polygons`: {view: pixel outline per part} of the proxy canvas; a hidden part scores 1)."""
        got = {}
        for v in self.views:
            lab = self.visible(v, hulls, polygons[v])
            for i in free:
                if (i, v) in self.masks:
                    vis = lab == i + 1
                    n = int(vis.sum())
                    got[i, v] = float((vis & self.masks[i, v]).sum()) / n if n else 1.0
        return got

    def term(self, free, hulls, polygons):
        """1 - mean of shares()."""
        got = self.shares(free, hulls, polygons)
        return 1.0 - sum(got.values()) / len(got) if got else 0.0

    def broken(self, hulls):
        """The depth pairs that do not hold: the front-near value of i is not above that of j."""
        return {(i, j) for i, j in self.pairs if hulls[i]["near"]["front"] <= hulls[j]["near"]["front"]}

