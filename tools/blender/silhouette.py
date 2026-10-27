#!/usr/bin/env python3
"""Silhouette gate: compare an exported unit with its approved concept sheet.

    python3 tools/blender/silhouette.py <sheet.jpg> <unit.glb> <outdir>

Both sides are reduced to a binary mask, normalized by body height and compared per
view: front / left / back / top. Prints IoU, width-profile L1 and a 32x32 IoU, and
exits non-zero when the front, profile or top view is below the gate.

This is the check that was missing while ten prose-review rounds plateaued: the
reviewer could see "the wheel is edge-on" only because it was told to look, while
the pipeline had no numeric target. The concept panels are segmented by the empty
background bands of the 3+2 template, so the same code works for every unit sheet.
"""
import argparse
import json
import math
import pathlib
import subprocess
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANVAS_H = 256
CANVAS_W = 384
VIEWS = ["front", "left", "back", "top"]
# Shape gates (PIPELINE §18.F), min silhouette IoU per view; top/bottom are scored at the
# tilt the sweep picks, rts at the (elevation, azimuth) it picks. Calibrated on clay rebuilds.
GATES = {"front": 0.75, "left": 0.65, "back": 0.70, "top": 0.65, "bottom": 0.65, "rts": 0.70}
ZONE_GATED = ("front", "left")   # views whose colour-zone numbers can fail the gate
# A spider is long and low: its front/back read as a thin ring of legs, so those two views get
# a lower bar (PIPELINE §18.L). Calibrated on the n00U runs: best 0.667/0.658/0.675 f/l/b passes,
# the 0.611 and 0.530 fronts do not.
RIG_GATES = {"spider": {"front": 0.65, "back": 0.65}, "spider_high": {"front": 0.65, "back": 0.65}}


def gates_for(rig=None):
    """GATES of one rig family: the defaults with that family's overrides."""
    return {**GATES, **RIG_GATES.get(rig, {})}


# Colour zones (PIPELINE §18): what the silhouette cannot see inside the contour.
ZONE_VIEWS = ("front", "left", "back", "top", "bottom")
ZONE_GATED = ZONE_VIEWS   # all five views gate the colour (PIPELINE §18.F)
PIECE_MIN = 0.005      # a zone piece under this share of the figure is noise, not a part
INK = 0.15             # sheet pixels this dark are outline, not a zone
ZONE_GATES = {"mean": 0.08, "cover": 0.30}   # gated views; the lowest of the 7 hard-v1 is 0.100 / 0.368
LOST = 0.02            # a zone of ZONE_SHARE+ under this IoU is "lost" (the model has none of it)
ZONE_SHARE = 0.03      # a zone under this share of the figure does not set "min"
SLACK = 4              # px of tolerance for a part that is there but offset
SMOOTH = 2             # mode-filter radius on the 256-px canvas
INK_FILL = 10          # px an outline is grown over from the zones beside it


def read_rgba(path, size):
    raw = subprocess.run(["magick", str(path), "-resize", f"{size}x{size}!",
                          "-depth", "8", "rgba:-"], check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.uint8).reshape(size, size, 4)


def foreground(path, size):
    """Key the flat background (the median border colour) out of a concept image."""
    arr = read_rgba(path, size)
    rgb, alpha = arr[..., :3].astype(np.int16), arr[..., 3]
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    bg = np.median(border, axis=0)
    return (np.abs(rgb - bg).sum(axis=2) > 30) & (alpha > 10)


def rts_path(sheet):
    """The gameplay-camera concept drawn from this sheet by generate.py --image:
    refs/<id>/sheet.jpg -> sheet-rts.jpg, sheet-hard.jpg -> sheet-hard-rts.jpg."""
    return sheet.with_name(f"{sheet.stem}-rts.jpg")


DRIFT_VIEWS = ("front", "left", "back")
DRIFT_MIN = 0.90   # 7 units measured: 0.90-0.98, n01N left 0.76 and n01I left 0.88 below


def sheet_drift(approved, redraw, layout="unit"):
    """Silhouette IoU of a redrawn sheet (the hard variant) against the approved one,
    per panel, plus the RTS views when both exist. Only DRIFT_VIEWS gate: the RTS images
    are two independent draws and differ in camera, not in design."""
    a = {k: normalize(v) for k, v in concept_panels(approved, layout=layout).items()}
    b = {k: normalize(v) for k, v in concept_panels(redraw, layout=layout).items()}
    out = {k: round(iou(a[k], b[k]), 4) for k in a if k in b}
    if rts_path(approved).exists() and rts_path(redraw).exists():
        out["rts"] = round(iou(normalize(foreground(rts_path(approved), 768)),
                               normalize(foreground(rts_path(redraw), 768))), 4)
    return out


def gaps(mask, axis, lo, hi):
    """Empty runs of rows (axis=1, offset lo) or columns (axis=0) inside mask[lo:hi]."""
    counts = mask[lo:hi].any(axis=axis)
    offset = lo if axis == 1 else 0
    found, s = [], None
    for i, v in enumerate(counts):
        if not v and s is None:
            s = i
        elif v and s is not None:
            found.append((s + offset, i + offset))
            s = None
    if s is not None:
        found.append((s + offset, len(counts) + offset))
    return found


def concept_panels(path, size=768, layout="unit"):
    """Key the flat background, split the 3+2 template on its empty bands, and
    return one boolean mask per panel in reading order, named by the sheet layout
    (views.LAYOUTS: a unit's bottom row is top/bottom, a building's right/roof)."""
    from views import LAYOUTS
    fg = foreground(path, size)

    runs = gaps(fg, 1, 0, size)
    interior = [r for r in runs if r[0] > 0.2 * size and r[1] < 0.8 * size]
    split = (max(interior, key=lambda r: r[1] - r[0])[0]
             + max(interior, key=lambda r: r[1] - r[0])[1]) // 2 if interior else size // 2

    top_x = gaps(fg, 0, 0, split)
    top_x = sorted(top_x, key=lambda r: r[1] - r[0], reverse=True)[:2]
    inner = sorted([(a, b) for a, b in top_x if a > 0.1 * size and b < 0.9 * size])
    cuts = [(a + b) // 2 for a, b in inner] if len(inner) == 2 else [size // 3, 2 * size // 3]
    bot_x = gaps(fg, 0, split, size)
    bot_x = sorted([r for r in bot_x if r[0] > 0.1 * size and r[1] < 0.9 * size],
                   key=lambda r: r[1] - r[0], reverse=True)[:1]
    cut_b = (bot_x[0][0] + bot_x[0][1]) // 2 if bot_x else size // 2

    bounds = [(0, cuts[0], 0, split), (cuts[0], cuts[1], 0, split), (cuts[1], size, 0, split),
              (0, cut_b, split, size), (cut_b, size, split, size)]
    cells = [(name, *box) for name, box in zip(LAYOUTS[layout], bounds)]
    panels = {}
    for name, x0, x1, y0, y1 in cells:
        cell = fg[y0:y1, x0:x1]
        if not cell.any():
            raise SystemExit(f"concept panel '{name}' is empty after background keying")
        # Keep full-image coordinates: every consumer (normalize, compare crops)
        # expects one coordinate space.
        full = np.zeros_like(fg)
        full[y0:y1, x0:x1] = cell
        panels[name] = full
    return panels


def row_spans(mask, count):
    """(height, half-width x2 per row as fractions of the height) of a mask, sampled at
    `count` rows from the top to the bottom of the figure."""
    ys = np.where(mask.any(axis=1))[0]
    h = ys.max() - ys.min() + 1
    spans = []
    for f in np.linspace(0.0, 1.0, count):
        cols = np.where(mask[ys.min() + int(f * (h - 1))])[0]
        spans.append((cols.max() - cols.min() + 1) / h if len(cols) else 0.0)
    return h, np.array(spans)


BOOT_ROW = 0.7   # a boot row is as long (side view) as this share of the sole row


def boot_height(side, k):
    """Height of the boot in fractions of H: the rows from the ground up that stay at least
    BOOT_ROW as long as the sole (side view); the shin above is narrower."""
    _, ls = row_spans(side, 200)
    sole = max(ls[-20:])
    rows = ls[::-1] >= BOOT_ROW * sole
    start = int(np.argmax(rows))               # the outline's own last rows may be thin
    run = 0
    for ok in rows[start:]:
        if not ok:
            break
        run += 1
    return run / 199


def arm_measures(spans, shoulder_row):
    """(arm angle from vertical in degrees, outward positive; arm length in H) read on the
    outer edge of the front silhouette: from the shoulder tip down to the lowest row (60-85%
    from the top) still as wide as the shoulders' own half width at the hip row."""
    half = spans / 2
    n = len(spans) - 1
    top = half[shoulder_row]
    fist = max((i for i in range(int(0.6 * n), int(0.85 * n) + 1) if half[i] >= half[int(0.5 * n)]),
               default=int(0.65 * n))
    dy = (fist - shoulder_row) / n
    dx = half[fist] - top
    return round(math.degrees(math.atan2(dx, dy)), 1), round(math.hypot(dx, dy), 3)


def head_measures(spans, shoulder_row):
    """(head width, neck width) in H: the head is the widest row in the top 70% of the way
    down to the shoulder line, the neck the narrowest row below the first 30%."""
    above = spans[:max(shoulder_row, 4)]
    cut = max(int(0.7 * len(above)), 1)
    return round(float(above[:cut].max()), 3), round(float(above[int(0.3 * len(above)):].min()), 3)


# Sano 2026 (§3.3-3.4): morphology -> exterior contour -> Douglas-Peucker -> axis snap
OUTLINE_EPS = 0.012     # DP tolerance, fractions of the figure height
OUTLINE_MAX = 24        # eps grows until the polygon has at most this many vertices
SNAP_DEG = 4            # an edge this close to vertical or horizontal is made so
_RING = ((-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1))   # (dy, dx) clockwise


def trace(mask):
    """Boundary pixels (y, x) of the one blob in `mask`: Moore-neighbour walk from the first
    raster pixel, stopping when the start is reached again."""
    pad = np.pad(mask, 1)
    ys, xs = np.nonzero(pad)
    start = (int(ys[0]), int(xs[0]))
    path, cur, back = [], start, 6               # the start's west neighbour is background
    for _ in range(pad.size):
        path.append(cur)
        for i in range(1, 9):
            k = (back + i) % 8
            nxt = (cur[0] + _RING[k][0], cur[1] + _RING[k][1])
            if pad[nxt]:
                bg = (cur[0] + _RING[(k - 1) % 8][0], cur[1] + _RING[(k - 1) % 8][1])
                back = _RING.index((bg[0] - nxt[0], bg[1] - nxt[1]))
                break
        else:
            break                                # a single pixel
        if nxt == start:
            break
        cur = nxt
    return [(y - 1, x - 1) for y, x in path]


def douglas_peucker(pts, eps):
    """Open polyline simplified so no dropped point is farther than eps from the kept chord."""
    pts = np.asarray(pts, float)
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    d = b - a
    norm = math.hypot(*d)
    rel = pts[1:-1] - a
    dist = np.hypot(*rel.T) if norm == 0 else np.abs(d[0] * rel[:, 1] - d[1] * rel[:, 0]) / norm
    i = int(np.argmax(dist))
    if dist[i] <= eps:
        return np.array([a, b])
    left, right = douglas_peucker(pts[:i + 2], eps), douglas_peucker(pts[i + 1:], eps)
    return np.vstack([left[:-1], right])


def snap_axes(poly, deg=SNAP_DEG):
    """Edges within `deg` of vertical or horizontal get both ends on the same x (or y)."""
    poly = poly.copy()
    tol = math.tan(math.radians(deg))
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        dx, dy = abs(b[0] - a[0]), abs(b[1] - a[1])
        if dy and dx <= tol * dy:
            poly[i][0] = poly[(i + 1) % len(poly)][0] = (a[0] + b[0]) / 2
        elif dx and dy <= tol * dx:
            poly[i][1] = poly[(i + 1) % len(poly)][1] = (a[1] + b[1]) / 2
    return poly


def outline(mask, eps=OUTLINE_EPS, limit=OUTLINE_MAX):
    """Simplified exterior polygon of a figure mask: [(x/H, y/H)] clockwise on screen, x from
    the figure's centre line (right positive), y up from the feet, H the figure height.
    Morphology first (close, fill, largest blob), then Douglas-Peucker on the closed contour."""
    from scipy import ndimage
    m = ndimage.binary_fill_holes(ndimage.binary_closing(mask, iterations=2))
    lab, n = ndimage.label(m)
    if n > 1:
        m = lab == (1 + int(np.argmax(np.bincount(lab.ravel())[1:])))
    ys, xs = np.nonzero(m)
    h = ys.max() - ys.min() + 1
    pts = np.array([(x, y) for y, x in trace(m)], float)
    far = int(np.argmax(np.hypot(*(pts - pts[0]).T)))
    halves = (pts[:far + 1], np.vstack([pts[far:], pts[:1]]))
    while True:
        poly = np.vstack([douglas_peucker(halves[0], eps * h)[:-1], douglas_peucker(halves[1], eps * h)[:-1]])
        poly = snap_axes(poly)
        if len(poly) <= limit or eps > 0.2:
            break
        eps *= 1.25
    cx = (xs.min() + xs.max()) / 2
    return [(round(float((x - cx) / h), 3), round(float((ys.max() - y) / h), 3)) for x, y in poly]


def band_areas(mask, shoulder_frac):
    """Share of the front silhouette's area in the head (above the shoulder line), the body
    (shoulders to hips, half the height) and the legs (below the hips)."""
    ys = np.where(mask.any(axis=1))[0]
    rows = mask[ys.min():ys.max() + 1].sum(axis=1)
    h = len(rows)
    cut = [int(shoulder_frac * h), h // 2]
    head, body, legs = rows[:cut[0]].sum(), rows[cut[0]:cut[1]].sum(), rows[cut[1]:].sum()
    return [round(float(v) / rows.sum(), 3) for v in (head, body, legs)]


def outlines(panels):
    """view -> outline in the spec's axes: front (x, y); left (z, y) with +z the way the feet
    point; back (x, y) mirrored, since the camera looks from behind."""
    out = {}
    for view in ("front", "left", "back"):
        poly = outline(panels[view])
        if view == "back":
            poly = [(-x, y) for x, y in poly]
        if view == "left":
            toe = np.mean([x for x, y in poly if y < 0.06] or [0.0])
            poly = [(-x, y) for x, y in poly] if toe < 0 else poly
        out[view] = poly
    return out


def measure(sheet, size=768):
    """Code-derived proportions from the five panels, in fractions of front-view H.
    The spec author gets numbers, not adjectives; this is the measurement stage the
    v9 review said was missing."""
    panels = concept_panels(sheet, size)

    def profile(mask):
        ys, xs = np.where(mask)
        h = ys.max() - ys.min() + 1
        spans = []
        for f in np.linspace(0.0, 1.0, 21):
            y = ys.min() + int(f * (h - 1))
            cols = np.where(mask[y])[0]
            spans.append((cols.max() - cols.min() + 1) / h if len(cols) else 0.0)
        return h, spans

    fh, fs = profile(panels["front"])
    lh, ls = profile(panels["left"])
    k = lh / fh
    fine_h, fine = row_spans(panels["front"], 200)
    shoulder_row = 8 + int(np.argmax(fine[8:60] >= 0.85 * fine[8:60].max()))   # first wide row
    angle, arm_len = arm_measures(fine, shoulder_row)
    head_w, neck_w = head_measures(fine, shoulder_row)
    area_head, area_body, area_legs = band_areas(panels["front"], shoulder_row / 199)
    return {
        "area_head": area_head, "area_body": area_body, "area_legs": area_legs,
        "boot_height": round(boot_height(panels["left"], k), 3),
        "head_width": head_w, "neck_width": neck_w,
        "arm_angle": angle, "arm_length": arm_len,
        "shoulder_span": round(max(fs[2:7]), 3),
        "fist_span": round(max(fs[12:17]), 3),
        "stance": round(max(fs[19:]), 3),
        "body_depth": round(max(ls[8:16]) * k, 3),
        "foot_length": round(max(ls[18:]) * k, 3),
        # the widest top row is the shoulder line: how far below the top it sits
        "shoulder_frac": shoulder_row / 199,
        "head_clear": round(0.05 * max(range(2, 7), key=lambda i: fs[i]), 3),
        "outline": outlines(panels),
        "front_width_profile": [round(v, 3) for v in fs],
        "left_width_profile": [round(v * k, 3) for v in ls],
    }


EDGE_REL = 0.3       # an edge is a gradient above this share of the panel's 99th percentile (shadows stay under)
EDGE_RIM = 7         # px at 768 of the silhouette rim dropped: the contour is not an inner edge
EDGE_BANDS = ("head", "torso", "legs")


def edges(path, mask, size=768):
    """Inner edges of a concept panel: Sobel gradient of the smoothed luma, thresholded
    relative to the panel's own strong edges (soft shading is far weaker than a drawn facet
    line), minus a rim along the mask border. Ink lines give two ridges; a 1 px closing merges
    them. Boolean, same shape as `mask`."""
    from scipy import ndimage as ndi
    luma = ndi.gaussian_filter(read_rgba(path, size)[..., :3].astype(float) @ LUMA, 1.0)
    mag = np.hypot(ndi.sobel(luma, axis=1), ndi.sobel(luma, axis=0))
    inner = ndi.binary_erosion(mask, iterations=EDGE_RIM)
    if not inner.any():
        return inner
    hit = inner & (mag > EDGE_REL * np.percentile(mag[inner], 99))
    return ndi.binary_closing(hit, iterations=1) & inner


def edge_bands(path, shoulder_frac, size=768):
    """Per height band (head above the shoulder line, torso to the hips, legs; the same cuts as
    band_areas) of the hard sheet's front panel: share of all inner-edge pixels (`salience`),
    facets (median edge lines a scanline crosses, plus one) and the dominant direction of the
    lines (vertical / horizontal / mixed: which long straight runs dominate)."""
    from scipy import ndimage as ndi
    mask = concept_panels(path, size)["front"]
    hit = edges(path, mask, size)
    rows = np.where(mask.any(axis=1))[0]
    top, h = rows.min(), rows.max() - rows.min() + 1
    cuts = [top, top + int(shoulder_frac * h), top + h // 2, top + h]
    total = max(int(hit.sum()), 1)
    out = {}
    for name, a, b in zip(EDGE_BANDS, cuts, cuts[1:]):
        band = hit[a:b]
        runs = [int(((r[1:] & ~r[:-1]).sum()) + r[0]) for r in band[::2] if r.any()]
        # long straight runs: a vertical facet line survives a 9x1 opening, a horizontal one a 1x9
        vert = ndi.binary_opening(band, np.ones((9, 1), bool)).sum()
        horiz = ndi.binary_opening(band, np.ones((1, 9), bool)).sum()
        direction = ("vertical" if vert > 1.5 * horiz else "horizontal" if horiz > 1.5 * vert else "mixed")
        out[name] = {"salience": round(float(band.sum()) / total, 3),
                     "facets": int(np.median(runs)) + 1 if runs else 0, "direction": direction}
    return out


def fit_canvas(edge, mask):
    """`edge` cropped to the bounding box of `mask` and resampled onto the CANVAS_H x CANVAS_W
    canvas, centred, aspect kept (what normalize does for a silhouette)."""
    ys, xs = np.where(mask)
    e = edge[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = e.shape
    scale = min(CANVAS_H / h, CANVAS_W / w)
    th, tw = max(1, round(h * scale)), max(1, round(w * scale))
    small = e[(np.arange(th) * h / th).astype(int)[:, None], (np.arange(tw) * w / tw).astype(int)[None, :]]
    out = np.zeros((CANVAS_H, CANVAS_W), bool)
    y0, x0 = (CANVAS_H - th) // 2, (CANVAS_W - tw) // 2
    out[y0:y0 + th, x0:x0 + tw] = small
    return out


def wire_edges(path, size=512):
    """(edges, mask) of a render_wire.py image: figure = pixels off the flat background, edges =
    the dark lines inside it."""
    rgb = read_rgba(path, size)[..., :3].astype(float)
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    mask = np.abs(rgb - np.median(border, axis=0)).sum(axis=2) > 30
    return (rgb @ LUMA < 110) & mask, mask


def edge_chamfer(hard_edge, hard_mask, wire, wire_mask):
    """Chamfer between the hard sheet's inner edges and the clay's wire, both fitted to one
    canvas (in canvas heights; Sketch2Mesh Eq. 5 on edges instead of contours). `drawn` = mean
    distance from a drawn edge to the nearest wire edge (did the model facet where the drawing
    does), `extra` = the other way (the wire also carries the triangulation, so this one is
    large by construction). The better of the two left-right mirrors, as the silhouette gate
    does."""
    from scipy.ndimage import distance_transform_edt
    if not (hard_edge.any() and wire.any()):
        return None
    a, b = fit_canvas(hard_edge, hard_mask), fit_canvas(wire, wire_mask)
    best = None
    for w in (b, np.fliplr(b)):
        drawn = distance_transform_edt(~w)[a].mean() / CANVAS_H
        extra = distance_transform_edt(~a)[w].mean() / CANVAS_H
        best = min(best or (drawn, extra), (drawn, extra))
    return {"drawn": round(float(best[0]), 4), "extra": round(float(best[1]), 4)}


def edge_report(hard, wire_dir):
    """{view: edge_chamfer} of the hard sheet against wire-<view>.png in `wire_dir`, for the
    views both have."""
    out = {}
    for view, mask in concept_panels(hard).items():
        path = wire_dir / f"wire-{view}.png"
        if view == "rts" or not path.exists():
            continue
        wire, wmask = wire_edges(path)
        out[view] = edge_chamfer(edges(hard, mask), mask, wire, wmask)
    return {v: r for v, r in out.items() if r}
def _crop(mask):
    ys, xs = np.where(mask)
    return mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def _fill_end(col):
    """Row after the first filled run of a boolean column (len when it never ends)."""
    first = int(np.argmax(col))
    gap = np.where(~col[first:])[0]
    return first + int(gap[0]) if len(gap) else len(col)


def measure_spider(sheet, size=768):
    """Spider proportions of the approved sheet, fractions of the front view's height H
    (L14, PIPELINE section 20): the numbers rig_families.scale_spider builds the rig from.
    body_r / body_len: half width and length of the body seen from the top (the legs are
    opened away); body_under: height of the belly above the ground (back view, where the
    fangs do not hang in the way); knee_h / knee_r: the front view's widest row between the
    shell and the feet, and half the width there; foot_r: half the width at the feet."""
    from scipy import ndimage
    panels = concept_panels(sheet, size)
    front, back, top = (_crop(panels[v]) for v in ("front", "back", "top"))
    h = front.shape[0]
    _, spans = row_spans(front, 100)
    half = [s / 2 for s in spans]
    # the leg ring's width is the same seen from the front and from the top: that calibrates the top panel
    k = (front.shape[1] / h) / top.shape[1]
    dist = ndimage.distance_transform_edt(top)
    r = dist.max()
    disc = np.hypot(*np.ogrid[-int(0.6 * r):int(0.6 * r) + 1, -int(0.6 * r):int(0.6 * r) + 1]) <= 0.6 * r
    body = _crop(ndimage.binary_opening(top, structure=disc))
    cx = back.shape[1] // 2
    under = _fill_end(ndimage.binary_closing(back, iterations=2)[:, cx - 2:cx + 3].any(axis=1))
    knee = max(range(len(half) // 5, len(half) * 85 // 100), key=lambda i: half[i])   # not the shell, not the feet
    return {"body_r": round(float(r * k), 3), "body_len": round(body.shape[0] * k, 3),
            "body_under": round(1 - under / back.shape[0], 3),
            "knee_h": round(1 - knee / (len(half) - 1), 3), "knee_r": round(float(half[knee]), 3),
            "foot_r": round(float(max(half[-4:])), 3)}


def read_mask(path):
    return read_rgba(path, 512)[..., 3] > 16


LUMA = np.array([0.299, 0.587, 0.114])
LW = 0.35


def figure_pixels(path, size=768, seed=0):
    """Up to 20000 non-ink figure pixels (rgb 0-1) of the front, left and back panels."""
    rgb = read_rgba(path, size)[..., :3].reshape(-1, 3).astype(float) / 255.0
    panels = concept_panels(path, size)
    mask = (panels["front"] | panels["left"] | panels["back"]).reshape(-1)
    px = rgb[mask]
    px = px[px.max(axis=1) > 0.12]
    rng = np.random.default_rng(seed)
    return px[rng.choice(len(px), min(len(px), 20000), replace=False)]


def kmeans(x, luma, k, iters=12):
    """(centres, label) of rows x, seeded from k quantiles of their luma."""
    centres = x[np.argsort(luma)[np.linspace(0, len(x) - 1, k).astype(int)]]
    for _ in range(iters):
        label = np.argmin(((x[:, None, :] - centres[None]) ** 2).sum(axis=2), axis=1)
        centres = np.array([x[label == i].mean(axis=0) if (label == i).any() else centres[i]
                            for i in range(k)])
    return centres, label


def hexcolour(c):
    return "#" + "".join(f"{round(v * 255):02X}" for v in c)


def sheet_colours(path, k=6, size=768, seed=0):
    """The sheet's flat tones, code-measured: k-means over the figure pixels of the
    front, left and back panels. Ink outlines (near black) are dropped. Returns
    [(hex, share)] by share, so the spec author picks colours instead of guessing."""
    px = figure_pixels(path, size, seed)
    centres, label = kmeans(px, px @ LUMA, k)
    share = np.bincount(label, minlength=k) / len(px)
    return [(hexcolour(centres[i]), round(float(share[i]), 3)) for i in np.argsort(-share)
            if share[i] >= 0.02]


def model_panels(render_dir, stem):
    """view -> {camera: mask} for every rendered view. Top and bottom carry every
    rendered tilt, the RTS view every (elevation, azimuth), the rest tilt 0."""
    from views import RTS, TILTED, TILTS, VIEWS
    panels = {}
    for name in [v for v in VIEWS if (render_dir / f"{stem}-sil-{v}.png").exists()]:
        panels[name] = {0: read_mask(render_dir / f"{stem}-sil-{name}.png")}
        if name in TILTED:
            for t in TILTS:
                path = render_dir / f"{stem}-sil-{name}@{t}.png"
                if t and path.exists():
                    panels[name][t] = read_mask(path)
    rts = {cam: render_dir / f"{stem}-sil-rts@{cam[0]}_{cam[1]}.png" for cam in RTS}
    panels["rts"] = {cam: read_mask(path) for cam, path in rts.items() if path.exists()}
    return panels


def oklab(rgb):
    """sRGB rows (0-1) as Oklab (L, a, b), Ottosson 2020: distance there follows perceived colour."""
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    lms = np.cbrt(lin @ OKLAB_LMS.T)
    return lms @ OKLAB_LAB.T


OKLAB_LMS = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                      [0.2119034982, 0.6806995451, 0.1073969566],
                      [0.0883024619, 0.2817188376, 0.6299787005]])
OKLAB_LAB = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                      [1.9779984951, -2.4285922050, 0.4505937099],
                      [0.0259040371, 0.7827717662, -0.8086757660]])
ZONE_SPACE = "legacy"     # "oklab": zone_feature_oklab (PIPELINE 19.C2 has the measure behind the default)
OKLAB_CHROMA = 3.0        # (a, b) scale: Oklab chroma is ~0.3 at most, the legacy r-g / y-b reach ~1


def zone_feature_oklab(rgb):
    """(a, b, LW x L) in Oklab, a and b scaled by OKLAB_CHROMA to the legacy range."""
    lab = oklab(rgb)
    return np.stack([OKLAB_CHROMA * lab[..., 1], OKLAB_CHROMA * lab[..., 2], LW * lab[..., 0]], axis=-1)


def zone_feature(rgb):
    """Colour as (red-green, yellow-blue, 0.35 x luma) rows: hue and chroma decide a zone,
    lightness barely does, because the model's render is darker than the sheet's lit tones
    (a grey plate must still be the sheet's grey, not its dark brown)."""
    if ZONE_SPACE == "oklab":
        return zone_feature_oklab(rgb)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    return np.stack([r - g, (r + g) / 2 - b, LW * (rgb @ LUMA)], axis=-1)


def zone_palette(path, k=4):
    """(names, centres, ramps): the sheet's colour zones, k-means in zone_feature space over its
    figure pixels. A zone is named by the mean colour of its pixels; its ramp is (p10, p90) of
    their luma, the light range the artist painted inside that colour (Le 2026). Under 2 % is dropped."""
    px = figure_pixels(path)
    bg = np.median(read_rgba(path, 768)[0, :, :3], axis=0) / 255.0
    px = px[np.abs(px - bg).sum(axis=1) > 0.3]   # the anti-aliased halo is not a zone
    centres, label = kmeans(zone_feature(px), px @ LUMA, k)
    keep = [i for i in np.argsort(-np.bincount(label, minlength=k)) if (label == i).mean() >= 0.02]
    ramps = [tuple(round(float(q), 4) for q in np.quantile(px[label == i] @ LUMA, (0.1, 0.9))) for i in keep]
    return [hexcolour(px[label == i].mean(axis=0)) for i in keep], centres[keep], ramps


def nearest(rgb, centres):
    """Zone index + 1 of every row of an (n, 3) colour array."""
    return np.argmin(((zone_feature(rgb)[:, None, :] - centres[None]) ** 2).sum(axis=2), axis=1) + 1


def match_luma(lit, mask, target):
    """The render's rgb with its luma histogram matched to the sheet figure's `target`
    pixels: the render is unlit albedo, the sheet is lit, and zones must not be exposure."""
    qs = np.linspace(0, 1, 33)
    luma = lit @ LUMA
    new = np.interp(luma, np.quantile(luma[mask], qs), np.quantile(target @ LUMA, qs))
    return np.clip(lit * (new / np.maximum(luma, 1e-3))[..., None], 0, 1)


LUMA_QS = (0.1, 0.5, 0.9)


def luma_l1(render, model_lab, sheet, concept_lab, zones):
    """L1 between the luma quantiles (p10/p50/p90) of the render and of the sheet, per zone,
    weighted by the zone's share of the sheet figure. `render` and `sheet` are rgb images with
    their label maps (0 = outside), the render as shot: BEFORE match_luma, which would hide
    exactly this. 0 = the render's light range is the artist's; None when no zone is in both."""
    total, weight = 0.0, 0.0
    sheet_luma, render_luma = sheet @ LUMA, render @ LUMA
    solid = sheet.max(axis=-1) > INK            # an outline is not a light value
    for z in range(1, zones + 1):
        a, b = render_luma[model_lab == z], sheet_luma[(concept_lab == z) & solid]
        if len(a) < 20 or len(b) < 20:
            continue
        share = len(b)
        total += share * float(np.abs(np.quantile(a, LUMA_QS) - np.quantile(b, LUMA_QS)).mean())
        weight += share
    return round(total / weight, 4) if weight else None


def mode_filter(lab, r=SMOOTH):
    """Each labelled pixel takes the most common label in its (2r+1)^2 window, outside
    pixels not counted: outline slivers and texture grain go, a part's blocks stay."""
    h, w = lab.shape
    k = 2 * r + 1
    counts = []
    for z in range(1, lab.max() + 1):
        c = np.pad((lab == z).astype(np.int32), r + 1).cumsum(0).cumsum(1)   # summed-area table
        counts.append(c[k:k + h, k:k + w] - c[:h, k:k + w] - c[k:k + h, :w] + c[:h, :w])
    return np.where(lab > 0, np.argmax(counts, axis=0) + 1, 0).astype(lab.dtype)


def zone_labels(rgb, mask, centres, ink=False):
    """Zone index + 1 (0 = outside) of every mask pixel: the nearest zone. With
    `ink` the sheet's black outlines are first grown over from the zones beside them, so a
    face keeps one label across its drawn edges."""
    lab = np.zeros(mask.shape, np.int16)
    px = rgb[mask]
    idx = nearest(px, centres)
    if ink:
        idx[px.max(axis=1) <= INK] = 0
    lab[mask] = idx
    for _ in range(INK_FILL if ink else 0):
        empty = mask & (lab == 0)
        if not empty.any():
            break
        pad = np.pad(lab, 1)
        near = np.maximum.reduce([pad[:-2, 1:-1], pad[2:, 1:-1], pad[1:-1, :-2], pad[1:-1, 2:]])
        lab = np.where(empty, near, lab)
    rest = mask & (lab == 0)   # an outline-only island: fall back to its own colour
    if rest.any():
        lab[rest] = nearest(rgb[rest], centres)
    return lab


def components(mask):
    """Connected pieces of a boolean mask as a list of boolean masks (4-neighbour)."""
    big = mask.size + 1
    ids = np.where(mask, np.arange(mask.size).reshape(mask.shape), big)
    while True:
        pad = np.pad(ids, 1, constant_values=big)
        near = np.minimum.reduce([ids, pad[:-2, 1:-1], pad[2:, 1:-1], pad[1:-1, :-2], pad[1:-1, 2:]])
        near = np.where(mask, near, big)
        if (near == ids).all():
            break
        ids = near
    return [ids == i for i in np.unique(ids[mask])]


def dilate(mask, r):
    """Boolean mask grown by r pixels (square window)."""
    for _ in range(r):
        pad = np.pad(mask, 1)
        mask = np.logical_or.reduce([pad[i:i + mask.shape[0], j:j + mask.shape[1]]
                                     for i in range(3) for j in range(3)])
    return mask


def cover(piece, zone):
    """Share of one drawn piece the model's same-colour zone reaches within SLACK px: a
    part present but a little off still counts, a part painted in another colour, or not
    there at all, is ~0. Unlike the zone IoU it cannot be hidden by a same-colour part
    elsewhere on the figure."""
    return float((piece & dilate(zone, SLACK)).sum() / piece.sum())


def zone_report(concept, model, names):
    """Per colour zone and per drawn piece, how well the model's flat-colour render covers
    the concept's. `concept` and `model` are normalized label maps (0 = outside). Returns
      mean    area-weighted zone IoU
      lost    zones of >= ZONE_SHARE of the figure under LOST IoU: a colour the model lacks
              entirely (the carapace, the club) reads ~0 however small its weight
      cover   area-weighted piece cover (see cover())
      zones   {hex: {"iou", "share"}}       pieces   {"hex@x,y": cover}  (x, y in % of canvas)"""
    total = (concept > 0).sum()
    zones, pieces, areas = {}, {}, {}
    for z, name in enumerate(names, 1):
        zc, zm = concept == z, model == z
        if zc.sum() < PIECE_MIN * total:
            continue
        zones[name] = {"iou": round(iou(zc, zm), 4), "share": round(float(zc.sum() / total), 4)}
        for piece in components(zc):
            if piece.sum() >= PIECE_MIN * total:
                ys, xs = np.where(piece)
                at = f"{name}@{int(100 * xs.mean() / CANVAS_W)},{int(100 * ys.mean() / CANVAS_H)}"
                pieces[at], areas[at] = round(cover(piece, zm), 4), int(piece.sum())
    weight = sum(z["share"] for z in zones.values()) or 1.0
    return {"mean": round(sum(z["iou"] * z["share"] for z in zones.values()) / weight, 4),
            "lost": [k for k, z in zones.items() if z["share"] >= ZONE_SHARE and z["iou"] < LOST],
            "cover": round(sum(pieces[k] * areas[k] for k in pieces) / max(sum(areas.values()), 1), 4),
            "zones": zones, "pieces": pieces}


def zone_views(sheet, renders, stem, silhouettes, layout="unit", tilts=None):
    """view -> zone_report for front/left/back/top/bottom: the sheet and the model's flat-colour
    render, both in the sheet's own zones and normalized like the silhouettes.
    `silhouettes` maps view -> the model mask best_match chose (picks the mirror);
    `tilts` maps top/bottom -> the tilt that mask was shot at, so the colour is shot from
    the same camera."""
    names, centres, _ = zone_palette(sheet)
    rgb = read_rgba(sheet, 768)[..., :3] / 255.0
    panels = concept_panels(sheet, layout=layout)
    out = {}
    for view in ZONE_VIEWS:
        tilt = (tilts or {}).get(view)
        path = renders / f"{stem}-zone-{view}{f'@{tilt}' if tilt else ''}.png"
        if view not in silhouettes or view not in panels or not path.exists():
            continue
        shot = read_rgba(path, 512)
        lit, mask = shot[..., :3] / 255.0, shot[..., 3] > 16
        lab = zone_labels(match_luma(lit, mask, rgb[panels[view]]), mask, centres)
        model = max(variants(mode_filter(normalize(lab)), view), key=lambda v: iou(v > 0, silhouettes[view]))
        sheet_lab = zone_labels(rgb, panels[view], centres, ink=True)
        concept = mode_filter(normalize(sheet_lab))
        out[view] = zone_report(concept, model, names)
        out[view]["luma_l1"] = luma_l1(lit, lab, rgb, sheet_lab, len(names))
    return out


def zone_gate(report, zones):
    """Attach each view's zone report to the silhouette report and print it. On the ZONE_GATED
    views a mean or cover under ZONE_GATES fails (returned: how many views); a lost zone
    only warns, it is the passes' acceptance that must not make one."""
    bad = 0
    for name, z in zones.items():
        fails = [m for m, lo in ZONE_GATES.items() if z[m] < lo] if name in ZONE_GATED else []
        report[name]["zones"] = {**z, "fails": fails}
        lost = f"  LOST {','.join(z['lost'])}" if z["lost"] else ""
        print(f"{name:8} zones mean {z['mean']:.3f}  cover {z['cover']:.3f}  luma L1 {z.get('luma_l1')}  "
              f"{'FAIL ' + ','.join(fails) if fails else 'ok'}{lost}")
        bad += bool(fails)
    return bad


def ids_zones(sheet, glb, outdir, layout, tilts):
    """view -> zone_report of the "ID" render of `glb`, the stage 1 shape rebuilt in the spec's
    palette (one flat colour per material): is the part of material X where the sheet has colour
    X? Only the flat-colour shots are rendered (render_silhouette.py ids); the mask that picks the
    mirror is their own alpha, shot from the cameras `tilts` pins. Written to outdir/zones_clay.json."""
    from views import parse_tilts
    renders = outdir / "ids"
    subprocess.run(["blender", "-b", "-P", str(HERE / "render_silhouette.py"),
                    "--", str(glb), str(renders), "ids"], check=True, capture_output=True, text=True)
    concept = {k: normalize(v) for k, v in concept_panels(sheet, layout=layout).items()}
    pinned, masks = parse_tilts(tilts), {}
    for view in ZONE_VIEWS:
        path = renders / f"{glb.stem}-zone-{view}{f'@{pinned[view]}' if pinned.get(view) else ''}.png"
        if view in concept and path.exists():
            masks[view] = best_match(concept[view], {0: read_mask(path)}, view)[1]
    zones = zone_views(sheet, renders, glb.stem, masks, layout, pinned)
    zone_gate({v: {} for v in zones}, zones)
    (outdir / "zones_clay.json").write_text(json.dumps(zones, indent=2))
    return zones


def best_match(concept, tilted, name):
    """Best IoU over the mirror variants of every rendered tilt: (iou, mask, tilt)."""
    best = (-1.0, None, 0)
    for tilt, mask in tilted.items():
        for variant in variants(normalize(mask), name):
            score = iou(concept, variant)
            if score > best[0]:
                best = (score, variant, tilt)
    return best


def pin_tilts(model, tilts):
    """model_panels() reduced to the cameras in `tilts` ({view: tilt}): top/bottom at that tilt
    only, the RTS view at that (elevation, azimuth) only. The colour stage measures the cameras
    the shape stage chose; a free sweep there could pick another camera for the same model."""
    return {view: {cam: m for cam, m in cams.items() if cam == tilts[view]} if view in tilts else cams
            for view, cams in model.items()}


def report_tilts(report):
    """{view: tilt} of the top/bottom/rts cameras a silhouette report matched."""
    return {view: r["tilt"] for view, r in report.items() if r.get("tilt")}


def crop(mask):
    ys, xs = np.where(mask)
    if len(ys) == 0:
        raise ValueError("empty mask")
    return mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def normalize(mask, target_h=CANVAS_H, canvas_w=CANVAS_W):
    m = crop(mask)
    h, w = m.shape
    tw = max(1, round(w * target_h / h))
    if tw > canvas_w:
        target_h = max(1, round(h * canvas_w / w))
        tw = canvas_w
    iy = (np.arange(target_h) * h / target_h).astype(int)
    ix = (np.arange(tw) * w / tw).astype(int)
    small = m[iy[:, None], ix[None, :]]
    out = np.zeros((target_h if target_h == CANVAS_H else CANVAS_H, canvas_w), m.dtype)
    y0, x0 = (CANVAS_H - target_h) // 2, (canvas_w - tw) // 2
    out[y0:y0 + target_h, x0:x0 + tw] = small
    return out


def variants(mask, name):
    """Left-right mirror only. Top and bottom used to try an upside-down flip too, but a
    flipped back-side tilt then out-scored the real front-side camera; the tilt sweep
    covers the angle, and the renders share the sheet's orientation (front at the bottom).
    The RTS view is never mirrored: the azimuth sweep already covers both sides, and a
    mirrored match renders the model from the opposite side of the concept."""
    return [mask] if name == "rts" else [mask, np.fliplr(mask)]


def iou(a, b):
    union = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / union) if union else 1.0


def chamfer(a, b):
    """Symmetric 2D chamfer between the outer contours of two masks, in units of canvas
    height (Sketch2Mesh Eq. 5: mean nearest-contour distance, both directions; 0 = same
    outline). A signal, not a gate. Unlike IoU it grows with how far an outline is off."""
    from scipy.ndimage import binary_erosion, distance_transform_edt
    if not a.any() or not b.any():
        return 1.0
    edge = [m & ~binary_erosion(m) for m in (a.astype(bool), b.astype(bool))]
    dist = [distance_transform_edt(~e) for e in edge]
    return float((dist[1][edge[0]].mean() + dist[0][edge[1]].mean()) / 2 / a.shape[0])


BANDS = 8              # height bands of the coupling report (0 = feet)
BLOB_OPEN = 2          # px an opening removes from the red before its largest piece is boxed (contour slivers)
# Coupling gates (PIPELINE 21.F7): share of the sheet the model leaves bare / of the model
# outside the sheet. Report only until calibrated on the stored runs.
COUPLING_BLOCKING = False
# Proposed caps (best runs n01X v5-fit-r1 / v13, n005 v5-fit-r2 / v6-r4, rounded up +0.03; PIPELINE 21.F7).
# 10 of the 23 IoU-passing runs would be flagged (> 1/3), so they stay a report.
UNCOVERED_MAX = {"front": 0.15, "left": 0.20, "back": 0.15, "top": 0.25, "bottom": 0.25, "rts": 0.20}
SPILL_MAX = {"front": 0.20, "left": 0.15, "back": 0.15, "top": 0.25, "bottom": 0.20, "rts": 0.25}


def coupling_ok(view, r):
    """False when the view's uncovered or spill share is over its cap and COUPLING_BLOCKING is on."""
    return not COUPLING_BLOCKING or (r["uncovered"] <= UNCOVERED_MAX.get(view, 1)
                                     and r["spill"] <= SPILL_MAX.get(view, 1))


def coupling(concept, model):
    """How the model sits on the sheet, as shares of area. `uncovered` = sheet not covered by
    the model / sheet (the sheet-only pixels of the overlay), `spill` = model outside the
    sheet / model. Per height band (BANDS, from the feet) the same two areas, as shares of
    the SHEET and the MODEL, so the bands sum to the totals and say where the miss is.
    `red` = the worst band of the uncovered area and the bbox of its largest piece after a
    BLOB_OPEN opening, in fractions of the figure height (y from the feet): 'the lantern'."""
    from scipy.ndimage import binary_opening, label
    c, m = concept.astype(bool), model.astype(bool)
    bare, spill = c & ~m, m & ~c
    rows = np.where(c.any(axis=1))[0]
    top, h = (rows.min(), rows.max() - rows.min() + 1) if len(rows) else (0, 1)
    edges = [round(top + h - h * i / BANDS) for i in range(BANDS + 1)]     # band i: rows edges[i+1]..edges[i]

    def per_band(x, total):
        return [round(float(x[edges[i + 1]:edges[i]].sum() / max(total, 1)), 4) for i in range(BANDS)]
    bands = {"uncovered": per_band(bare, c.sum()), "spill": per_band(spill, m.sum())}
    worst = int(np.argmax(bands["uncovered"]))
    red = {"band": worst, "lo": round(worst / BANDS, 3), "hi": round((worst + 1) / BANDS, 3),
           "share": bands["uncovered"][worst], "blob": None}
    pieces, count = label(binary_opening(bare, iterations=BLOB_OPEN))
    if count:
        sizes = np.bincount(pieces.ravel())[1:]
        ys, xs = np.where(pieces == 1 + int(np.argmax(sizes)))
        mid = c.shape[1] / 2
        red["blob"] = {"x": [round(float((xs.min() - mid) / h), 3), round(float((xs.max() + 1 - mid) / h), 3)],
                       "y": [round(float((top + h - ys.max() - 1) / h), 3), round(float((top + h - ys.min()) / h), 3)],
                       "share": round(float(sizes.max() / max(c.sum(), 1)), 4)}
    return {"uncovered": round(float(bare.sum() / max(c.sum(), 1)), 4),
            "spill": round(float(spill.sum() / max(m.sum(), 1)), 4), "bands": bands, "red": red}


def red_text(red):
    """'band 5 (0.62-0.75 H), 9 % of sheet; largest piece x -0.10..+0.10 H, y 0.60..0.70 H (4 % of sheet)'."""
    text = f"band {red['band']} ({red['lo']:.2f}-{red['hi']:.2f} H), {100 * red['share']:.0f} % of sheet"
    blob = red.get("blob")
    if blob:
        text += (f"; largest piece x {blob['x'][0]:+.2f}..{blob['x'][1]:+.2f} H, "
                 f"y {blob['y'][0]:.2f}..{blob['y'][1]:.2f} H ({100 * blob['share']:.0f} % of sheet)")
    return text


def profile(mask, bands=32):
    rows = np.where(mask.any(axis=1))[0]
    h = rows.max() - rows.min() + 1 if len(rows) else 1
    out = []
    for i in range(bands):
        a = rows.min() + i * h // bands if len(rows) else 0
        b = rows.min() + (i + 1) * h // bands if len(rows) else 0
        band = mask[a:b]
        cols = np.where(band.any(axis=0))[0]
        out.append((cols.max() - cols.min() + 1) / max(h, 1) if len(cols) else 0.0)
    return np.asarray(out)


def downsample(mask, n=32):
    kh, kw = mask.shape[0] // n, mask.shape[1] // n
    return mask.reshape(n, kh, n, kw).mean(axis=(1, 3)) >= 0.5


def write_mask(mask, path, color=(255, 255, 255)):
    rgba = np.zeros((*mask.shape, 4), np.uint8)
    rgba[mask] = (*color, 255)
    subprocess.run(["magick", "-size", f"{mask.shape[1]}x{mask.shape[0]}", "-depth", "8",
                    "rgba:-", str(path)], input=rgba.tobytes(), check=True)


def write_overlay(concept, model, path):
    rgba = np.zeros((*concept.shape, 4), np.uint8)
    rgba[..., 0] = concept * 255
    rgba[..., 1] = model * 255
    rgba[..., 3] = np.where(np.logical_or(concept, model), 255, 0)
    subprocess.run(["magick", "-size", f"{concept.shape[1]}x{concept.shape[0]}", "-depth", "8",
                    "rgba:-", str(path)], input=rgba.tobytes(), check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet", type=pathlib.Path)
    ap.add_argument("glb", type=pathlib.Path)
    ap.add_argument("outdir", type=pathlib.Path)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--measure", action="store_true", help="print sheet proportions and exit")
    ap.add_argument("--rig", default=None, help="rig family: picks its gates (GATES + RIG_GATES)")
    ap.add_argument("--layout", default="unit", choices=("unit", "building"))
    ap.add_argument("--shape", action="store_true",
                    help="stage 1 (clay): silhouette gates only, no colour zones")
    ap.add_argument("--ids", action="store_true",
                    help="glb is the palette-colour rebuild of the shape (no clay grey): only measure its "
                         "colour zones, from the --tilts cameras; writes outdir/zones_clay.json")
    ap.add_argument("--space", choices=("legacy", "oklab"), default="legacy",
                    help="colour space of the zone feature (oklab: see PIPELINE 19.C2 for why legacy is the default)")
    ap.add_argument("--tilts", default="",
                    help="pin the top/bottom/rts cameras, e.g. top:10,bottom:20,rts:35/30 "
                         "(the colour stage reuses the shape stage's cameras)")
    args = ap.parse_args()
    global ZONE_SPACE
    ZONE_SPACE = args.space
    gates = gates_for(args.rig)
    if args.measure:
        print(json.dumps(measure(args.sheet), indent=2))
        return 0

    args.outdir.mkdir(parents=True, exist_ok=True)
    if args.ids:
        return 0 if ids_zones(args.sheet, args.glb, args.outdir, args.layout, args.tilts) else 1
    renders = args.outdir / "sil"
    if not args.no_render:
        subprocess.run(["blender", "-b", "-P", str(HERE / "render_silhouette.py"),
                        "--", str(args.glb), str(renders)], check=True,
                       capture_output=True, text=True)

    concept = {k: normalize(v) for k, v in concept_panels(args.sheet, layout=args.layout).items()}
    if rts_path(args.sheet).exists():
        concept["rts"] = normalize(foreground(rts_path(args.sheet), 768))
    model = model_panels(renders, args.glb.stem)
    if args.tilts:
        from views import parse_tilts
        model = pin_tilts(model, parse_tilts(args.tilts))

    print(f"{'view':8} {'IoU':>6}  {'L1':>6}  {'32px':>5}  {'camera':>6}  gate")
    report, bad, best_masks = {}, 0, {}
    for name in [v for v in concept if model.get(v)]:
        best, best_mask, tilt = best_match(concept[name], model[name], name)
        l1 = float(np.abs(profile(concept[name]) - profile(best_mask)).mean())
        px = iou(downsample(concept[name]), downsample(best_mask))
        gate = gates.get(name)
        report[name] = {"iou": round(best, 4), "width_l1": round(l1, 4),
                        "iou_32": round(px, 4), "chamfer": round(chamfer(concept[name], best_mask), 4),
                        "tilt": tilt, "gate": gate, **coupling(concept[name], best_mask)}
        ok = (gate is None or best >= gate) and coupling_ok(name, report[name])
        bad += 0 if ok else 1
        print(f"{name:8} {best:6.3f}  {l1:6.3f}  {px:5.3f}  {str(tilt):>6}  "
              f"{'n/a' if gate is None else ('PASS' if ok else 'FAIL')}")
        write_mask(concept[name], args.outdir / f"mask-concept-{name}.png", (255, 80, 80))
        write_mask(best_mask, args.outdir / f"mask-model-{name}.png", (80, 255, 80))
        write_overlay(concept[name], best_mask, args.outdir / f"overlay-{name}.png")
        best_masks[name] = best_mask

    if not args.shape:
        bad += zone_gate(report, zone_views(args.sheet, renders, args.glb.stem, best_masks, args.layout,
                                             report_tilts(report)))
    (args.outdir / "silhouette.json").write_text(json.dumps(report, indent=2))
    gated = [g for g in gates if g in concept]    # a view with no concept image (no RTS draw) is not gated
    missing = [g for g in gated if g not in report]
    if missing:
        # no render (missing GLB, failed Blender) must not read as a pass
        print(f"\nno measurement for gated views {missing}: FAIL")
        return 1
    print(f"\n{len(gated) - bad}/{len(gated)} view gates pass")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
