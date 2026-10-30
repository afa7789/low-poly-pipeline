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
import os
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


def _blob_panels(fg, split, layout, grow=6):
    """concept_panels(blob=True): the 3 largest blobs above `split` and the 2 largest below, each
    in reading order (x of the centroid), after a `grow`-px dilation joins a figure's loose
    pieces (a rope, a detached lamp). A sheet with fewer blobs than panels stops."""
    from scipy import ndimage
    from views import LAYOUTS
    panels = {}
    names = iter(LAYOUTS[layout])
    for lo, hi, count in ((0, split, 3), (split, fg.shape[0], 2)):
        labels, n = ndimage.label(ndimage.binary_dilation(fg[lo:hi], iterations=grow))
        areas = ndimage.sum(fg[lo:hi], labels, range(1, n + 1))
        keep = sorted(np.argsort(areas)[::-1][:count] + 1,
                      key=lambda k: ndimage.center_of_mass(labels == k)[1])
        if len(keep) < count:
            return None          # figures merged into one blob (a hard sheet): the caller cuts by columns
        # every smaller blob (a lantern drawn loose, a thrown prop) goes with the nearest figure by x,
        # so nothing is dropped and nothing leaks into the neighbour's cell (2026-10-28)
        centres = {k: ndimage.center_of_mass(labels == k)[1] for k in keep}
        owner = {j: min(keep, key=lambda k: abs(centres[k] - ndimage.center_of_mass(labels == j)[1]))
                 for j in range(1, n + 1) if j not in keep and areas[j - 1] > 0}
        for k in keep:
            name = next(names)
            mine = (labels == k) | np.isin(labels, [j for j, o in owner.items() if o == k])
            full = np.zeros_like(fg)
            full[lo:hi] = fg[lo:hi] & mine
            panels[name] = full
    return panels


# Sheets whose side profile is wider than a third of the page (quadruped, wyrm, drake): the default cut puts
# the snout in the front panel, so they are split by blob (PIPELINE 22.L4-4a, 22.L4-4b).
BLOB_SHEETS = ("n017", "n00H", "n010")


def concept_panels(path, size=768, layout="unit", blob=False, columns=False):
    """Key the flat background, split the 3+2 template on its empty bands, and
    return one boolean mask per panel in reading order, named by the sheet layout
    (views.LAYOUTS: a unit's bottom row is top/bottom, a building's right/roof).
    `blob` splits by connected blob instead (quadruped, drake: a profile wider than a third of the page)."""
    from views import LAYOUTS
    fg = foreground(path, size)
    # Units are split by blob since 2026-10-28: the column cut sliced the n005 gun barrel into the
    # left panel (the overlay showed the barrel as a stray bar); a blob is a whole figure with its props.
    blob = (blob or layout == "unit") and not columns      # columns=True: the old cut, for tests and diffs

    runs = gaps(fg, 1, 0, size)
    interior = [r for r in runs if r[0] > 0.2 * size and r[1] < 0.8 * size]
    split = (max(interior, key=lambda r: r[1] - r[0])[0]
             + max(interior, key=lambda r: r[1] - r[0])[1]) // 2 if interior else size // 2

    top_x = gaps(fg, 0, 0, split)
    top_x = sorted(top_x, key=lambda r: r[1] - r[0], reverse=True)[:2]
    inner = sorted([(a, b) for a, b in top_x if a > 0.1 * size and b < 0.9 * size])
    if blob:
        panels = _blob_panels(fg, split, layout)
        if panels is not None:
            return panels
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


# Sano 2026 r_sym and the sheet's own coherence (PIPELINE 24.L6-9): the sheet is five drawings of one figure by a
# generator, and some disagree. A view whose panel contradicts front x left is reported, not gated.
SYM_MIN = 0.85         # a front under this r_sym is drawn asymmetric (a prop or pose on one side): do not mirror it
COHERENCE_MIN = 0.6    # a panel under this IoU with the hull of front x left is not a view of that figure
HULL_N = 64            # voxels along the figure's height


def r_sym(mask):
    """IoU of the figure's bounding box crop with its left-right mirror (Sano r_sym): 1.0 = symmetric."""
    m = crop(mask)
    return iou(m, np.fliplr(m))


def to_height(mask, n):
    """The cropped figure resampled (nearest) to n rows, columns in proportion."""
    m = crop(mask)
    w = max(1, round(m.shape[1] * n / m.shape[0]))
    return m[(np.arange(n) * m.shape[0] / n).astype(int)[:, None], (np.arange(w) * m.shape[1] / w).astype(int)[None, :]]


def hull_voxels(front, left, n=HULL_N):
    """bool [y, x, z]: the visual hull of front[y, x] and left[y, z] on an n-high grid."""
    return to_height(front, n)[:, :, None] & to_height(left, n)[:, None, :]


def stretched(mask, n=HULL_N):
    """The cropped figure stretched to an n x n box: the extents agree by construction, so only the shape counts
    (a top or bottom view is drawn tilted, at its own scale)."""
    m = crop(mask)
    return m[(np.arange(n) * m.shape[0] / n).astype(int)[:, None], (np.arange(n) * m.shape[1] / n).astype(int)[None, :]]


def best_flip(panel, proj):
    """Best stretched IoU of a panel with a hull footprint [rows, cols] in any of its 4 flips: the sheet's top and
    bottom are drawn head-up or head-down and the side panel faces either way."""
    a = stretched(panel)
    return max(iou(a, stretched(f)) for f in (proj, np.fliplr(proj), np.flipud(proj), np.flipud(np.fliplr(proj))))


RTS_RES = 2            # raster pixels per hull voxel when the hull is projected into the rts camera


def hull_rts_mask(hull, cam, zflip=False):
    """bool mask of the hull [y(down), x, z] seen from the rts camera cam = (elevation, azimuth) (views.rts_offset,
    orthographic; x to the viewer's right, z toward the viewer, flipped when the side panel faces the other way)."""
    from scipy import ndimage as ndi
    e, a = math.radians(cam[0]), math.radians(cam[1])
    ys, xs, zs = np.nonzero(hull)
    x, y, z = xs - hull.shape[1] / 2, hull.shape[0] - ys, (zs - hull.shape[2] / 2) * (-1 if zflip else 1)
    sx = x * math.cos(a) - z * math.sin(a)
    sy = -x * math.sin(e) * math.sin(a) + y * math.cos(e) - z * math.sin(e) * math.cos(a)
    px = ((sx - sx.min()) * RTS_RES).astype(int)
    py = ((sy.max() - sy) * RTS_RES).astype(int)
    m = np.zeros((py.max() + 1 + RTS_RES, px.max() + 1 + RTS_RES), bool)
    m[py, px] = True
    return ndi.binary_closing(ndi.binary_dilation(m, iterations=RTS_RES), iterations=RTS_RES)


def rts_coherence(hull, rts, cams=None):
    """(best IoU, (elevation, azimuth)) of an rts panel mask with the hull of front x left in the gameplay cameras
    (default: every views.RTS candidate, both facings of the side panel, as the model sweep does)."""
    from views import RTS
    target = normalize(rts)
    best = (0.0, None)
    for cam in cams or RTS:
        for zflip in (False, True):
            best = max(best, (iou(target, normalize(hull_rts_mask(hull, cam, zflip))), cam), key=lambda b: b[0])
    return best


def rts_vs_sheet(sheet, rts_img, cams=None):
    """(IoU, camera) of an rts image on disk with the hull of the sheet's front x left; None when unreadable."""
    try:
        panels = concept_panels(sheet)
    except SystemExit:
        return None
    return rts_coherence(hull_voxels(panels["front"], panels["left"]), foreground(rts_img, 768), cams)


def ortho_strip(sheet, out, margin=0.02):
    """Write the top row of a unit sheet (front, left, back) as an image to `out`: the three orthographic panels
    that tie the rts redraw to one figure. Rows come from the keyed panels' bounds (fractions of the page)."""
    from PIL import Image
    panels = concept_panels(sheet)
    rows = np.where(sum(panels[v] for v in ("front", "left", "back")).any(axis=1))[0]
    img = Image.open(sheet).convert("RGB")
    size = panels["front"].shape[0]
    y0, y1 = max(0, rows.min() / size - margin), min(1, (rows.max() + 1) / size + margin)
    img.crop((0, round(y0 * img.height), img.width, round(y1 * img.height))).save(out, quality=92)


def sheet_report(sheet, layout="unit", cams=None):
    """{"r_sym": {view: r}, "coherence": {back, top, bottom, and rts when sheet-rts.jpg exists: IoU with the hull
    of front x left}, "rts_cam": [elevation, azimuth] of the best hull match, "incoherent": [views under
    COHERENCE_MIN]}; {} for a building sheet or one whose panels cannot be read."""
    if layout != "unit":
        return {}
    try:
        panels = concept_panels(sheet, layout=layout)
    except SystemExit:
        return {}
    hull = hull_voxels(panels["front"], panels["left"])
    foot = hull.any(axis=0).T            # [z, x]
    coh = {"back": iou(normalize(panels["back"]), normalize(np.fliplr(hull.any(axis=2)))),
           "top": best_flip(panels["top"], foot), "bottom": best_flip(panels["bottom"], foot)}
    extra = {}
    if rts_path(sheet).exists():
        coh["rts"], cam = rts_coherence(hull, foreground(rts_path(sheet), 768), cams)
        extra["rts_cam"] = list(cam)
    return {**extra, "r_sym": {v: round(r_sym(m), 4) for v, m in panels.items()},
            "coherence": {v: round(c, 4) for v, c in coh.items()},
            "incoherent": [v for v, c in coh.items() if c < COHERENCE_MIN]}


def run_report(args):
    """sheet_report() of the run's sheet, computed once per run (cached on `args`): who weighs the views and who is gated."""
    if not hasattr(args, "sheet_rep"):
        from views import layout_of
        args.sheet_rep = sheet_report(args.sheet, layout_of(args.kind))
    return args.sheet_rep


def write_sheet_report(args):
    """Write outdir/sheet.json; the set of views the sheet is incoherent on."""
    rep = sheet_report(args.sheet, args.layout)
    (args.outdir / "sheet.json").write_text(json.dumps(rep, indent=2))
    return set(rep.get("incoherent", ()))


def verdict_of(gate, ok, waived):
    """(counts as ok, printed verdict) of a view: a waived view is reported, never failed."""
    verdict = "n/a" if gate is None else ("PASS" if ok else "FAIL")
    return (True, f"{verdict} (incoherent, not gated)") if waived else (ok, verdict)


def sheet_line(rep):
    """One line for review.md: 'front r_sym .93, back-vs-hull .81, top-vs-hull .52 (incoherent)'."""
    if not rep:
        return ""
    bad = set(rep["incoherent"])
    parts = [f"front r_sym {rep['r_sym']['front']:.2f}"] + [
        f"{v}-vs-hull {c:.2f}" + (" (incoherent)" if v in bad else "") for v, c in rep["coherence"].items()]
    return ", ".join(parts)


def sheet_text(rep):
    """The brief's sentences for what sheet_report found (empty when the sheet is symmetric and coherent)."""
    if not rep:
        return ""
    out = ""
    if rep["r_sym"]["front"] < SYM_MIN:
        out += (f"\nThe figure is asymmetric in the front view (r_sym {rep['r_sym']['front']:.2f}): a prop or a pose "
                "on one side only; keep it on that side, do not mirror it.")
    for v in rep["incoherent"]:
        out += (f"\nThe sheet's {v} panel disagrees with its front x left views ({rep['coherence'][v]:.2f} IoU with "
                "their hull): do not trust it.")
    return out


# F6 turntable (PIPELINE 21.F6): refs/<id>/sheet-turn.jpg is a 4 x 2 grid read left to right, top row first,
# one drawing per 45 deg of azimuth from the front (0 = front, 90 = the unit's left, 180 = back, 270 = right).
TURN_ANGLES = (0, 45, 90, 135, 180, 225, 270, 315)
TURN_H_TOL = 0.10      # panel heights (all 8) and mirrored-pair widths within +-10 % of the median / of each other
TURN_MIRROR = 0.85     # IoU of a panel with the mirror of its opposite
TURN_PAIRS = ((0, 180), (90, 270))   # gated pairs; (45, 315) and (135, 225) are reported only


def turn_panels(path, width=1024):
    """angle -> boolean mask of the 8 panels of a turntable sheet, all in the coordinates of one
    `width`-wide keyed image (native aspect: a 2:1 sheet is not squeezed square). Rows are split on the
    widest empty band, each row's 4 columns on its 3 widest empty bands (equal quarters when missing)."""
    from PIL import Image
    img = Image.open(path).convert("RGB")
    rgb = np.asarray(img.resize((width, round(width * img.height / img.width)), Image.LANCZOS), dtype=np.int16)
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    fg = np.abs(rgb - np.median(border, axis=0)).sum(axis=2) > 30
    h, w = fg.shape
    rows = [r for r in gaps(fg, 1, 0, h) if r[0] > 0.2 * h and r[1] < 0.8 * h]
    mid = sum(max(rows, key=lambda r: r[1] - r[0])) // 2 if rows else h // 2
    panels = {}
    for r, (y0, y1) in enumerate(((0, mid), (mid, h))):
        cols = sorted((c for c in gaps(fg, 0, y0, y1) if c[0] > 0.05 * w and c[1] < 0.95 * w),
                      key=lambda c: c[1] - c[0], reverse=True)[:3]
        cuts = sorted((a + b) // 2 for a, b in cols) if len(cols) == 3 else [w // 4, w // 2, 3 * w // 4]
        for c, (x0, x1) in enumerate(zip([0] + cuts, cuts + [w])):
            full = np.zeros_like(fg)
            full[y0:y1, x0:x1] = fg[y0:y1, x0:x1]
            if not full.any():
                raise SystemExit(f"turntable panel {TURN_ANGLES[r * 4 + c]} is empty after background keying")
            panels[TURN_ANGLES[r * 4 + c]] = full
    return panels


def turn_check(panels):
    """Is the turntable one figure? {ok, height_dev, width_dev, mirror, fails}. height_dev = worst panel
    height vs the median (all 8; the model is told they share one ground line and scale), width_dev = worst
    width gap inside a gated mirrored pair (the width itself changes with the angle), mirror = IoU of each
    pair (0/180, 90/270 gated; 45/315, 135/225 reported) of one panel with the left-right flip of the
    other, both normalized as the view gates do."""
    boxes = {a: crop(m).shape for a, m in panels.items()}      # (h, w)
    hs = np.array([boxes[a][0] for a in TURN_ANGLES], float)
    height_dev = float(np.abs(hs / np.median(hs) - 1).max())
    width_dev = max(abs(boxes[a][1] / boxes[b][1] - 1) for a, b in TURN_PAIRS)
    mirror = {f"{a}/{b}": round(iou(normalize(panels[a]), np.fliplr(normalize(panels[b]))), 4)
              for a, b in TURN_PAIRS + ((45, 315), (135, 225))}
    fails = []
    if height_dev > TURN_H_TOL:
        fails.append("height")
    if width_dev > TURN_H_TOL:
        fails.append("width")
    fails += [f"mirror {a}/{b}" for a, b in TURN_PAIRS if mirror[f"{a}/{b}"] < TURN_MIRROR]
    return {"ok": not fails, "height_dev": round(height_dev, 4), "width_dev": round(width_dev, 4),
            "mirror": mirror, "fails": fails}


TURN_3Q = (45, 135, 225, 315)    # the three-quarter panels measured against the clay
TURN_SWEEP, TURN_STEP = 20, 5    # azimuth window around the nominal angle, degrees


def turn_azimuths():
    """Every model azimuth the 3/4 sweep needs: each nominal angle +-TURN_SWEEP; the mirror window
    (360 - angle) is among them because the four windows are symmetric."""
    return sorted({(a + d) % 360 for a in TURN_3Q for d in range(-TURN_SWEEP, TURN_SWEEP + 1, TURN_STEP)})


def turn_match(concept, model, angle):
    """(iou, azimuth, side, iou at the nominal azimuth) of one 3/4 panel against the model masks
    {azimuth: normalized mask}: best over the window of `angle` and of its mirror 360 - angle (which
    side of the model the sheet's "45" is on is measured, not assumed, as for the RTS view). The
    masks are never flipped."""
    best = (-1.0, 0, "own")
    for side, centre in (("own", angle), ("mirror", 360 - angle)):
        for d in range(-TURN_SWEEP, TURN_SWEEP + 1, TURN_STEP):
            azim = (centre + d) % 360
            score = iou(concept, model[azim])
            if score > best[0]:
                best = (score, azim, side)
    return round(best[0], 4), best[1], best[2], round(max(iou(concept, model[angle]), iou(concept, model[360 - angle])), 4)


def turn_report(sheet_turn, glb, outdir):
    """{angle: {iou, azim, side, iou_nominal}} of the four 3/4 panels of `sheet_turn` against the
    clay `glb` shot every TURN_STEP deg around each of them (render_silhouette.py turn). Masks and
    overlays go to outdir/turn/ (mask-concept-<angle>.png, mask-model-<angle>.png, overlay-<angle>.png)
    for the compare; outdir/turn/turn.json holds the report."""
    renders = outdir / "turn"
    subprocess.run(["blender", "-b", "-P", str(HERE / "render_silhouette.py"), "--", str(glb), str(renders),
                    "turn", *map(str, turn_azimuths())], check=True, capture_output=True, text=True)
    model = {a: normalize(read_mask(renders / f"{glb.stem}-sil-turn@{a}.png")) for a in turn_azimuths()}
    panels = turn_panels(sheet_turn)
    report = {}
    for angle in TURN_3Q:
        concept = normalize(panels[angle])
        score, azim, side, nominal = turn_match(concept, model, angle)
        report[angle] = {"iou": score, "azim": azim, "side": side, "iou_nominal": nominal}
        write_mask(concept, renders / f"mask-concept-{angle}.png", (255, 80, 80))
        write_mask(model[azim], renders / f"mask-model-{angle}.png", (80, 255, 80))
        write_overlay(concept, model[azim], renders / f"overlay-{angle}.png")
    (renders / "turn.json").write_text(json.dumps(report, indent=2))
    return report


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


JOINT_STEP = 0.25     # a knee or elbow is a step of the leg's width at least this share of the median width


def _runs(row, gap=3):
    """[(start, end)] of the filled runs of a boolean row; runs `gap` px apart or less are one (the
    outline's own breaks)."""
    d = np.diff(np.concatenate([[0], row.astype(int), [0]]))
    out = []
    for a, b in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
        out[-1:] = [(out[-1][0], b)] if out and a - out[-1][1] <= gap else [*out[-1:], (a, b)]
    return out


def limb_widths(front, start, top, pick):
    """[(row, width px)] from row `start` up to row `top` of the +x limb in a cropped front mask: the run
    `pick` chooses among those right of the centre at `start`, followed up while it stays one run narrower
    than 0.2 H (it ends where the limb merges into the pelvis, a coat or the shoulder)."""
    n = front.shape[0]
    cx = front.shape[1] / 2
    runs = [r for r in _runs(front[start]) if r[1] > cx and r[1] - r[0] <= 0.2 * n]
    if not runs:
        return []
    prev = pick(runs, cx, n)
    out = []
    for i in range(start, top, -1):
        hit = [r for r in _runs(front[i]) if r[0] < prev[1] and r[1] > prev[0] and r[1] > cx]
        if len(hit) != 1 or hit[0][1] - hit[0][0] > 0.2 * n:
            break
        prev = hit[0]
        out.append((i, prev[1] - prev[0]))
    return out


def leg_run(runs, cx, n):
    return min(runs, key=lambda r: abs((r[0] + r[1]) / 2 - cx - 0.2 * n))


def arm_run(runs, cx, n):
    return max(runs, key=lambda r: r[1])


def knee_row(series):
    """Row of the biggest width step in the middle of leg_widths' series (the narrowing or the widening
    where thigh meets shin, upper arm meets forearm), None when no step reaches JOINT_STEP of the median width."""
    if len(series) < 12:
        return None
    rows, w = np.array([r for r, _ in series]), np.array([v for _, v in series], float)
    k = max(len(w) // 10, 2)
    w = np.convolve(np.pad(w, (2, 2), mode="edge"), np.ones(5) / 5, mode="valid")
    lo, hi = len(w) // 5, len(w) - len(w) // 5
    step = np.array([abs(w[min(i + k, len(w) - 1)] - w[max(i - k, 0)]) for i in range(lo, hi)])
    if step.max() < JOINT_STEP * np.median(w):
        return None
    return int(rows[lo + int(np.median(np.where(step >= 0.98 * step.max())[0]))])   # the middle of the plateau


def joint_measures(panel, boot, shoulder_frac, arm_len, arm_angle):
    """{knee_h, elbow_h} of a biped sheet's front panel: height above the feet in H of the leg's
    width step and of the arm's; a joint the drawing does not show is left out."""
    front = _crop(panel)
    n = front.shape[0]
    fist = shoulder_frac + arm_len * math.cos(math.radians(arm_angle))
    wrist = int((min(fist, 0.9) - 0.1) * n)      # fist is the bottom of the hand (0.1 H tall): read the arm above it
    rows = {"knee_h": knee_row(limb_widths(front, int((1 - boot) * n), int(0.3 * n), leg_run)),
            "elbow_h": knee_row(limb_widths(front, wrist, int(shoulder_frac * n), arm_run))}
    return {k: round(1 - r / (n - 1), 3) for k, r in rows.items() if r is not None}


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
        **joint_measures(panels["front"], boot_height(panels["left"], k), shoulder_row / 199, arm_len, angle),
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


def leg_ridge(mask):
    """(width, distance from the body) of the ridge pixels of the thin parts outside the body
    (the mask minus its opening by a disc of 0.6 of the thickest radius), in pixels."""
    from scipy import ndimage
    r = ndimage.distance_transform_edt(mask).max()
    n = int(0.6 * r)
    disc = np.hypot(*np.ogrid[-n:n + 1, -n:n + 1]) <= 0.6 * r
    body = ndimage.binary_opening(mask, structure=disc)
    dist = ndimage.distance_transform_edt(mask & ~ndimage.binary_dilation(body, iterations=2))
    ys, xs = np.where((dist == ndimage.maximum_filter(dist, 5)) & (dist > 1.5))
    return 2 * dist[ys, xs], ndimage.distance_transform_edt(~body)[ys, xs]


def leg_measures(views):
    """leg_w (median leg radius) and leg_taper (tip / base radius, thirds nearest and farthest from
    the body) pooled over [(mask, pixels per H)] views, fractions of H; None without thin parts."""
    pairs = [(w / ppf / 2, a) for m, ppf in views for w, a in [leg_ridge(m)]]
    w = np.concatenate([p[0] for p in pairs])
    a = np.concatenate([p[1] / ppf for p, (_, ppf) in zip(pairs, views)])
    if len(w) < 6:
        return None
    w = w[np.argsort(a)]
    third = len(w) // 3
    return {"leg_w": round(float(np.median(w)), 3),
            "leg_taper": round(float(np.median(w[-third:]) / np.median(w[:third])), 2)}


LEGS = 8              # a spider's legs
LEG_MIN_AREA = 0.6    # a branch under this share of the median branch area is a fang or a palp, not a leg
LEG_SPEC = 0.002      # a speck under this share of the panel is noise


def leg_branches(top, k):
    """[[angle, base x, base z, knee x, knee z, tip x, tip z, radius]] of the legs of a spider's top panel
    (cropped, head up), sorted by angle (degrees, 0 = +x, 90 = the head); metres-free: fractions of H (`k` per pixel), from the
    centre of the body's bounding box (the legs opened away), x right, z toward the head. A leg is a branch of the mask
    outside the body; the knee is the chord's 0.6 point pushed sideways by the branch's mean offset from the chord
    (PIPELINE 25.L7-3). None unless exactly LEGS branches are left (touching legs merge: the rig's ring stays)."""
    from scipy import ndimage
    body = thin_opened(top)
    ys, xs = np.nonzero(body)
    cy, cx = (ys.min() + ys.max()) / 2, (xs.min() + xs.max()) / 2
    lab, n = ndimage.label(top & ~ndimage.binary_dilation(body, iterations=2))
    near = ndimage.distance_transform_edt(~body)
    found = []
    for i in range(1, n + 1):
        yy, xx = np.nonzero(lab == i)
        if len(yy) >= LEG_SPEC * top.size:
            found.append((yy, xx))
    if len(found) < LEGS:
        return None
    floor = LEG_MIN_AREA * float(np.median([len(f[0]) for f in found]))
    found = [f for f in found if len(f[0]) >= floor]
    if len(found) != LEGS:
        return None
    out = []
    for yy, xx in found:
        b, t = int(np.argmin(near[yy, xx])), int(np.argmax(np.hypot(xx - cx, yy - cy)))
        base, tip = np.array([xx[b], yy[b]], float), np.array([xx[t], yy[t]], float)
        chord = tip - base
        length = max(float(np.hypot(*chord)), 1.0)
        side = np.array([-chord[1], chord[0]]) / length
        dev = float(np.mean((np.stack([xx, yy], 1) - base) @ side))
        knee = base + 0.6 * chord + dev * side
        pt = lambda p: [round(float((p[0] - cx) * k), 3), round(float((cy - p[1]) * k), 3)]   # noqa: E731
        ang = math.degrees(math.atan2(cy - tip[1], tip[0] - cx))
        out.append([round(ang, 1), *pt(base), *pt(knee), *pt(tip), round(len(yy) / length / 2 * k, 3)])
    return sorted(out)


def measure_spider(sheet, size=768):
    """Spider proportions of the approved sheet, fractions of the front view's height H
    (L14, PIPELINE section 20): the numbers rig_families.scale_spider builds the rig from.
    body_r / body_len: half width and length of the body seen from the top (the legs are
    opened away); body_under: height of the belly above the ground (back view, where the
    fangs do not hang in the way); knee_h / knee_r: the front view's widest row between the
    shell and the feet, and half the width there; foot_r: half the width at the feet;
    leg_w / leg_taper: median leg radius and tip/base ratio (leg_measures, front and top)."""
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
            "foot_r": round(float(max(half[-4:])), 3),
            **(leg_measures([(front, h), (top, 1 / k)]) or {}),
            **({"legs": legs} if (legs := leg_branches(top, k)) else {})}


# ---- quadruped, wyrm, drake (PIPELINE 22.L4-4b). Numbers are fractions of H, the figure's height in the
# side panel; x runs from the snout (0) to the tail tip, y up from the ground. The side panel has the head on
# the left, as the model's left view does.
LINE_POINTS = 17      # points of a body centre line (snout to tail tip)
TAIL_FLOOR = 0.25     # a quadruped's tail tip is above this height (the wolf's rope lies on the ground)
TUBE = 1.3            # a pixel farther than this many radii from the centre line is not the body (a wing)


def thin_opened(mask, share=0.6):
    """The mask with its thin parts (legs, tail, rope) opened away by a disc of `share` of the thickest radius."""
    from scipy import ndimage
    r = ndimage.distance_transform_edt(mask).max()
    q = int(share * r)
    return ndimage.binary_opening(mask, structure=np.hypot(*np.ogrid[-q:q + 1, -q:q + 1]) <= share * r)


def centreline(mask, n=LINE_POINTS, floor=0.0):
    """[(col, row, radius)] x n along the medial path of the one blob in `mask` from its leftmost pixel to its
    rightmost pixel above `floor` (fraction of the height up from the bottom: a rope on the ground is not the tail): the cheapest path where a pixel costs (R / (d + 1))^2, d its distance to the edge. A wing or a
    leg is a side branch the path does not take. Radius = d in pixels."""
    from scipy import ndimage, sparse
    from scipy.sparse.csgraph import dijkstra
    dist = ndimage.distance_transform_edt(mask)
    ys, xs = np.nonzero(mask)
    ids = -np.ones(mask.shape, int)
    ids[ys, xs] = np.arange(len(ys))
    cost = (dist.max() / (dist + 1)) ** 2
    rows, cols, wts = [], [], []
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        y2, x2 = ys + dy, xs + dx
        ok = (y2 < mask.shape[0]) & (x2 >= 0) & (x2 < mask.shape[1])
        ok[ok] = mask[y2[ok], x2[ok]]
        a, b = ids[ys[ok], xs[ok]], ids[y2[ok], x2[ok]]
        rows.append(a), cols.append(b)
        wts.append((cost[ys[ok], xs[ok]] + cost[y2[ok], x2[ok]]) / 2 * math.hypot(dy, dx))
    graph = sparse.csr_matrix((np.concatenate(wts), (np.concatenate(rows), np.concatenate(cols))), shape=(len(ys),) * 2)
    high = np.nonzero(ys <= (1 - floor) * mask.shape[0])[0]
    ends = [int(np.argmin(xs)), int(high[np.argmax(xs[high])])]
    _, pred = dijkstra(graph, directed=False, indices=ends[0], return_predecessors=True)
    path, k = [], ends[1]
    while k >= 0:
        path.append(k)
        k = pred[k]
    pts = np.array([(xs[k], ys[k]) for k in path[::-1]], float)
    arc = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(pts, axis=0).T))])
    at = np.linspace(0, arc[-1], n)
    px, py = np.interp(at, arc, pts[:, 0]), np.interp(at, arc, pts[:, 1])
    return [(float(x), float(y), float(dist[int(round(y)), int(round(x))])) for x, y in zip(px, py)]


def body_line(left, floor=0.0):
    """{"len", "line": [[x, y, r]] x LINE_POINTS} of the side panel (cropped): fractions of its height; the line ends
    at the rightmost pixel above `floor`."""
    h = left.shape[0]
    return {"len": round(left.shape[1] / h, 3),
            "line": [[round(x / h, 3), round(1 - (y + 0.5) / h, 3), round(r / h, 3)] for x, y, r in centreline(left, floor=floor)]}


def row_runs(mask, row, min_w=1):
    """[(first col, last col)] of the runs of figure pixels in one row at least `min_w` wide."""
    cols = np.nonzero(mask[row])[0]
    if not len(cols):
        return []
    cut = np.nonzero(np.diff(cols) > 1)[0]
    runs = zip(np.concatenate([[cols[0]], cols[cut + 1]]), np.concatenate([cols[cut], [cols[-1]]]))
    return [(int(a), int(b)) for a, b in runs if b - a + 1 >= min_w]


def trunk_span(line):
    """(first, last) index of the line's trunk: the points whose radius is at least 0.6 of the widest."""
    rmax = max(p[2] for p in line)
    ok = [i for i, p in enumerate(line) if p[2] >= 0.6 * rmax]
    return ok[0], ok[-1]


def leg_columns(left, line, belly, i0, i1):
    """([x of the front legs, x of the rear legs], leg radius) in fractions of H from the snout: the outer runs of the
    side panel at knee height, inside the trunk's span, and their median half width; None for what the panel does not separate."""
    h = left.shape[0]
    row = int(round((1 - 0.5 * belly) * h))
    lo, hi = line[i0][0] * h - 0.1 * h, line[i1][0] * h + 0.1 * h
    runs = [(a, b) for a, b in row_runs(left, min(row, h - 1), int(0.035 * h)) if lo <= (a + b) / 2 <= hi]
    if len(runs) < 2:
        return [None, None], None
    half = float(np.median([(b - a + 1) / 2 for a, b in runs])) / h
    return [round((runs[0][0] + runs[0][1]) / 2 / h, 3), round((runs[-1][0] + runs[-1][1]) / 2 / h, 3)], round(half, 3)


def leg_stance(front, level=0.08):
    """(half spread of the feet, leg radius) in H from the front panel's runs at `level` H above the ground;
    one merged run reads as a spread of a third of its width."""
    h = front.shape[0]
    cx = (front.shape[1] - 1) / 2
    runs = row_runs(front, int(round((1 - level) * h)), int(0.02 * h))
    outer = [r for r in runs if r[1] > cx]
    if len(outer) > 1 or (outer and outer[0][0] > cx):
        a, b = outer[-1]
        return round(((a + b) / 2 - cx) / h, 3), round(float(np.clip((b - a + 1) / 2 / h, 0.025, 0.09)), 3)
    wide = (max(b for _, b in runs) - cx) / h if runs else 0.2
    return round(wide / 1.5, 3), 0.05


def measure_quadruped(sheet, size=768, winged=False):
    """Quadruped proportions of the sheet (rig_families.scale_quadruped builds the rig from them): body_line
    (the snout-to-tail centre line with its radius), `trunk` (x of the first and last trunk point), `belly`
    (height of the underside), `legs` (x of the front and rear pair, half spread of the feet, radius). The
    trunk's radius is the line's. `winged` (a drake) adds `wing` as measure_chain does."""
    panels = concept_panels(sheet, size)
    left, front = _crop(panels["left"]), _crop(panels["front"])
    m = body_line(left, TAIL_FLOOR)
    i0, i1 = trunk_span(m["line"])
    rmax = max(p[2] for p in m["line"])
    spread, leg_r = leg_stance(front)
    belly = max(m["line"][(i0 + i1) // 2][1] - rmax, 0.0)
    xs, side_r = leg_columns(left, m["line"], belly, i0, i1)
    out = {**m, "trunk": [m["line"][i0][0], m["line"][i1][0]], "belly": round(belly, 3),
           "legs": {"x": xs, "spread": spread, "r": round(min(leg_r, side_r or leg_r), 3)}}
    return {**out, "wing": wing_measures(panels, m["line"])} if winged else out


def wing_side(front, low=0.10, high=0.45):
    """(+x wing region mask, centre column) of a winged front panel: above `high` of the height, what lies beyond
    1.15 x the body's half width, the median over the rows from `low` to `high` (the feet and the wings stay out)."""
    h, w = front.shape
    cx = (w - 1) / 2
    rows = [(np.ptp(np.nonzero(front[r])[0]) + 1) / 2 for r in range(int((1 - high) * h), int((1 - low) * h)) if front[r].any()]
    start = int(cx + 1.15 * float(np.median(rows)) + 1)
    region = np.zeros_like(front)
    region[:int((1 - high) * h), start:] = front[:int((1 - high) * h), start:]
    return region, cx


def wing_numbers(front):
    """{"span", "tip": [x, y], "root_x", "root_y", "width", "area"} of the +x wing of the front panel, fractions of
    H: the outer edge; the spar, which runs through the middle of the wing's rows (tip = its top end at the highest
    row, root = its bottom end at the lowest); the mean row width and the area (H^2)."""
    h = front.shape[0]
    region, cx = wing_side(front)
    rows = np.nonzero(region.any(axis=1))[0]
    mid = np.array([(np.nonzero(region[r])[0].min() + np.nonzero(region[r])[0].max() + 1) / 2 for r in rows])
    wid = np.array([np.ptp(np.nonzero(region[r])[0]) + 1 for r in rows])
    k = max(len(rows) // 7, 1)
    r3 = lambda v: round(float(v), 3)   # noqa: E731
    return {"span": r3((np.nonzero(region)[1].max() + 1 - cx) / h),
            "tip": [r3((mid[:k].mean() - cx) / h), r3(1 - rows[0] / h)],
            "root_x": r3((mid[-k:].mean() - cx) / h), "root_y": r3(1 - (rows[-1] + 1) / h),
            "width": r3(wid.mean() / h), "area": round(float(region.sum()) / h ** 2, 4)}


def wing_mask(left, line):
    """The wing in the side panel (cropped): the highest blob left when the body (the line's discs of TUBE x
    radius) is taken away."""
    from scipy import ndimage
    h = left.shape[0]
    yy, xx = np.mgrid[:left.shape[0], :left.shape[1]]
    body = np.zeros_like(left)
    for x, y, r in line:
        body |= np.hypot(xx - x * h, yy - (1 - y) * h) <= TUBE * r * h + 2
    lab, n = ndimage.label(left & ~body)
    tops = [np.nonzero(lab == k)[0].min() for k in range(1, n + 1)]
    return lab == 1 + int(np.argmin(tops))


def wing_blob(left, line):
    """{"chord": [x0, x1], "top": x of the wing's highest pixel, "root": index of the nearest line point} of wing_mask."""
    h = left.shape[0]
    ys, xs = np.nonzero(wing_mask(left, line))
    k = int(np.argmin(ys))
    near = [np.hypot(xs - x * h, ys - (1 - y) * h).min() for x, y, _ in line]
    return {"chord": [round(float(xs.min()) / h, 3), round(float(xs.max() + 1) / h, 3)], "top": round(float(xs[k] + 0.5) / h, 3),
            "root": int(np.argmin(near))}


def wing_measures(panels, line):
    """The `wing` entry of measure_chain: the front panel's numbers and the side panel's blob."""
    return {**wing_numbers(_crop(panels["front"])), **wing_blob(_crop(panels["left"]), line)}


def measure_chain(sheet, winged=True, size=768):
    """Serpent proportions (rig_families.scale_wyrm): body_line, and for a winged one `wing`: span, tip [x, y],
    root_y, root_x, area (front panel), chord, top and root (side panel; root = index of the line point the wing
    hangs on)."""
    panels = concept_panels(sheet, size)
    m = body_line(_crop(panels["left"]))
    return {**m, "wing": wing_measures(panels, m["line"])} if winged else m


def measure_rig(family, sheet):
    """The sheet's measures for a family rig_families can scale (spider, quadruped, wyrm, drake), else None."""
    return {"spider": measure_spider, "spider_high": measure_spider, "quadruped": measure_quadruped,
            "wyrm": measure_chain, "drake": lambda s: measure_quadruped(s, winged=True)}.get(family, lambda s: None)(sheet)

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


def zone_views(sheet, renders, stem, silhouettes, layout="unit", tilts=None, rotate=()):
    """view -> zone_report for front/left/back/top/bottom: the sheet and the model's flat-colour
    render, both in the sheet's own zones and normalized like the silhouettes.
    `silhouettes` maps view -> the model mask best_match chose (picks the mirror);
    `tilts` maps top/bottom -> the tilt that mask was shot at, so the colour is shot from
    the same camera. `rotate` = the views whose sheet panel is drawn upside down (detect_rotated)."""
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
        sheet_rgb, sheet_mask = (np.rot90(rgb, 2), np.rot90(panels[view], 2)) if view in rotate else (rgb, panels[view])
        lab = zone_labels(match_luma(lit, mask, sheet_rgb[sheet_mask]), mask, centres)
        model = max(variants(mode_filter(normalize(lab)), view), key=lambda v: iou(v > 0, silhouettes[view]))
        sheet_lab = zone_labels(sheet_rgb, sheet_mask, centres, ink=True)
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


DETAIL_VIEWS = ("front", "left", "back")
DETAIL_CHROMA = 0.04   # Oklab chroma of a pixel that carries a colour (steel grey, ink and shadow stay under)
DETAIL_BIN = 40        # degrees of hue per bin: the sheet's colours are few, a bin is one of them
DETAIL_MIN = 0.001     # a colour under this share of the figure in every view is a speck
HUE_TOL = 30           # a model colour within this many degrees of a detail's hue is that detail
READ_MIN = 0.5         # identity_reads: the render shows at least this share of the sheet's area
HUE_NAMES = ((42, "red"), (82, "orange"), (126, "yellow"), (168, "green"), (230, "cyan"), (296, "blue"), (346, "magenta"))


def hex_rgb(h):
    return np.array([int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]) / 255.0


def hue_chroma(rgb):
    """(hue in degrees, Oklab chroma) of sRGB (0-1) colours, any leading shape."""
    lab = oklab(np.asarray(rgb, float).reshape(-1, 3)).reshape(np.shape(rgb))
    return np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360, np.hypot(lab[..., 1], lab[..., 2])


def hue_name(hue):
    return next((n for top, n in HUE_NAMES if hue < top), "red")


def same_colour(hue, chroma, ref_hue):
    """True where (hue, chroma) is a colour (not grey) within HUE_TOL degrees of ref_hue."""
    return (chroma >= DETAIL_CHROMA) & (np.abs((hue - ref_hue + 180) % 360 - 180) <= HUE_TOL)


def identity_details(sheet, layout="unit"):
    """The sheet's identity details (PIPELINE 23.L5-6): a saturated colour that is under ZONE_SHARE of the
    figure in every one of front/left/back (a badge, a brass valve, red lenses) and over DETAIL_MIN in one.
    [{"hex", "name", "shares": {view: share of the figure}}], by hex. ponytail: fixed hue bins, a colour
    straddling a bin edge splits in two; add overlapping bins when a sheet shows it."""
    rgb = read_rgba(sheet, 768)[..., :3] / 255.0
    panels = concept_panels(sheet, layout=layout)
    hue, chroma = hue_chroma(rgb)
    bins = (hue // DETAIL_BIN).astype(int)
    lit = (chroma > DETAIL_CHROMA) & (rgb.max(axis=-1) > 0.12)
    shares = {}
    for view in [v for v in DETAIL_VIEWS if v in panels]:
        for b in np.unique(bins[panels[view] & lit]):
            shares.setdefault(b, {})[view] = float((panels[view] & lit & (bins == b)).sum() / panels[view].sum())
    out = []
    for b, s in sorted(shares.items()):
        if not DETAIL_MIN <= max(s.values()) < ZONE_SHARE:
            continue
        view = max(s, key=s.get)
        mean = rgb[panels[view] & lit & (bins == b)].mean(axis=0)
        out.append({"hex": hexcolour(mean), "name": hue_name(float(hue_chroma(mean)[0])),
                    "shares": {v: round(x, 4) for v, x in s.items()}})
    return out


def identity_reads(details, renders, stem):
    """Per detail, how much of it the ID render shows (flat material colours): in each view the sheet has it,
    the model's share of the figure in the detail's hue over the sheet's share; the best view counts.
    [{"hex", "view", "ratio", "read": ratio >= READ_MIN}]."""
    out = []
    for d in details:
        ref = float(hue_chroma(hex_rgb(d["hex"]))[0])
        best = ("", 0.0)
        for view, share in d["shares"].items():
            path = renders / f"{stem}-zone-{view}.png"
            if not path.exists():
                continue
            shot = read_rgba(path, 512)
            fig = shot[..., 3] > 16
            h, c = hue_chroma(shot[..., :3] / 255.0)
            ratio = float((fig & same_colour(h, c, ref)).sum() / max(fig.sum(), 1)) / share
            best = max(best, (view, ratio), key=lambda t: t[1])
        out.append({"hex": d["hex"], "view": best[0], "ratio": round(best[1], 3), "read": best[1] >= READ_MIN})
    return out


def ids_zones(sheet, glb, outdir, layout, tilts, rotate=()):
    """view -> zone_report of the "ID" render of `glb`, the stage 1 shape rebuilt in the spec's
    palette (one flat colour per material): is the part of material X where the sheet has colour
    X? Only the flat-colour shots are rendered (render_silhouette.py ids); the mask that picks the
    mirror is their own alpha, shot from the cameras `tilts` pins. Written to outdir/zones_clay.json."""
    from views import parse_tilts
    renders = outdir / "ids"
    subprocess.run(["blender", "-b", "-P", str(HERE / "render_silhouette.py"),
                    "--", str(glb), str(renders), "ids"], check=True, capture_output=True, text=True)
    concept = oriented(concept_panels(sheet, layout=layout), rotate)
    pinned, masks = parse_tilts(tilts), {}
    for view in ZONE_VIEWS:
        path = renders / f"{glb.stem}-zone-{view}{f'@{pinned[view]}' if pinned.get(view) else ''}.png"
        if view in concept and path.exists():
            masks[view] = best_match(concept[view], {0: read_mask(path)}, view)[1]
    zones = zone_views(sheet, renders, glb.stem, masks, layout, pinned, rotate)
    zone_gate({v: {} for v in zones}, zones)
    (outdir / "zones_clay.json").write_text(json.dumps(zones, indent=2))
    (outdir / "identity.json").write_text(json.dumps(identity_reads(identity_details(sheet, layout), renders, glb.stem), indent=2))
    return zones


# Top and bottom panels the image model draws turned 180 degrees from views.py (front at the bottom of
# top, at the top of bottom): the n00U shell has its head up in the top panel. The orientation is read
# once, before the IoU, from the model's own top/bottom: the panel is rotated only when it matches the
# model clearly better that way (humanoids, whose head is the centre, give ~0 and stay as drawn).
FLIP_MARGIN = 0.10
HEAD = {"top": ("head-down", "head-up"), "bottom": ("head-up", "head-down")}   # (as views.py, rotated)


def oriented(panels, rotate=()):
    """Normalized concept panels, those in `rotate` turned 180 degrees first (before the crop)."""
    return {k: normalize(rot180(v) if k in rotate else v) for k, v in panels.items()}


def head_of(view, rotate):
    """{"head": where the sheet draws the head} for top/bottom (silhouette.json), {} for the others."""
    return {"head": HEAD[view][view in rotate]} if view in HEAD else {}


def detect_rotated(panels, model, forced=""):
    """The set of top/bottom views whose sheet panel is drawn turned 180 degrees: the best IoU over
    the tilt sweep (and the mirror) with the panel turned beats the one as drawn by FLIP_MARGIN.
    `forced` (--rotate, "top,bottom" or "none") skips the detection."""
    if forced:
        return set(forced.split(","))
    def score(view, turned):      # both sides framed by their bbox: the orientation does not depend on the frame
        mask = np.rot90(np.asarray(panels[view]), 2) if turned else np.asarray(panels[view])
        return best_match(normalize(mask), model[view], view)[0]
    return {v for v in HEAD if v in panels and model.get(v) and score(v, True) - score(v, False) > FLIP_MARGIN}


def best_match(concept, tilted, name, boxes=None):
    """Best IoU over the mirror variants of every rendered tilt: (iou, mask, tilt, flipped). A side view
    (one tilt) takes the mirror pick_variant chooses; its score is the plain IoU of that mask.
    `boxes` {tilt: (x0, y0, x1, y1)}: the model's body box in the mask's pixels (model_boxes), framed like the
    concept's (framed_panels); a tilt without one is framed by its bbox."""
    best = (-1.0, None, 0, False)
    for tilt, mask in tilted.items():
        box = (boxes or {}).get(tilt)
        options = variants(normalize(mask if box is None else framed(mask, box)), name)
        ks = range(len(options))
        if name in SIDE_VIEWS:
            k = pick_variant(concept, options, name)
            options, ks = [options[k]], [k]
        for variant, k in zip(options, ks):
            score = iou(concept, variant)
            if score > best[0]:
                best = (score, variant, tilt, k == 1)
    return best


def model_boxes(glb, model, panels):
    """{view: {camera: box}} for best_match(boxes=): the body box (deform_to_sheet.body_fractions: the largest welded
    component) of the model in the pixels of each rendered mask, for the views whose panel is body-framed. {} otherwise."""
    views = [v for v in model if getattr(panels.get(v), "box", None) is not None]
    if not views:
        return {}
    import deform_to_sheet as D
    pos, tri = D.welded_mesh(glb)
    out = {}
    for view in views:
        out[view] = {}
        for cam, mask in model[view].items():
            frac = D.body_fractions(pos, tri, *D.view_axes(view, cam))
            if frac is None or not mask.any():
                continue
            ys, xs = np.where(mask)
            (x0, y0), (w, h) = (xs.min(), ys.min()), (np.ptp(xs) + 1, np.ptp(ys) + 1)
            out[view][cam] = (x0 + frac[0] * w, y0 + frac[1] * h, x0 + frac[2] * w, y0 + frac[3] * h)
    return out


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


FRAME = os.environ.get("CF_FRAME", "bbox")   # PIPELINE 29.L11-0b: "bbox" frames a panel by its figure, "body" by the figure less its props


class Framed(np.ndarray):
    """A panel mask that remembers the box (x0, y0, x1, y1, raw pixels) normalize() frames instead of its bbox: the
    body without its props. Arrays derived from it (slices, ufuncs, rot90) frame by their own bbox."""
    box = None

    def __array_finalize__(self, obj):
        self.box = None


def framed(mask, box):
    out = np.asarray(mask).view(Framed)
    out.box = box
    return out


def rot180(mask):
    """np.rot90(mask, 2) that keeps the frame box."""
    out = np.rot90(np.asarray(mask), 2)
    box = getattr(mask, "box", None)
    h, w = mask.shape
    return out if box is None else framed(out, (w - box[2], h - box[3], w - box[0], h - box[1]))


def geometry(mask):
    """((sx, sy), (tx, ty)): normalize()'s map raw pixel -> canvas pixel (canvas = raw * s + t) for the bbox frame, or
    for the body box a Framed mask carries."""
    box = getattr(mask, "box", None)
    if box is not None:
        x0, y0, x1, y1 = box
        s = min(CANVAS_H / (y1 - y0), CANVAS_W / (x1 - x0))
        return (s, s), (CANVAS_W / 2 - (x0 + x1) / 2 * s, CANVAS_H / 2 - (y0 + y1) / 2 * s)
    ys, xs = np.where(mask)
    h, w = ys.max() - ys.min() + 1, xs.max() - xs.min() + 1
    th = CANVAS_H
    tw = max(1, round(w * th / h))
    if tw > CANVAS_W:
        th, tw = max(1, round(h * CANVAS_W / w)), CANVAS_W
    s = (tw / w, th / h)
    return s, ((CANVAS_W - tw) // 2 - xs.min() * s[0], (CANVAS_H - th) // 2 - ys.min() * s[1])


def reframe(mask, src, dst):
    """`mask` (a canvas mask in the frame `src` = geometry()) in the frame `dst`, nearest pixel."""
    (sx, sy), (tx, ty) = src
    (dx, dy), (ux, uy) = dst
    iy = np.floor(((np.arange(CANVAS_H) + 0.5 - uy) / dy) * sy + ty).astype(int)
    ix = np.floor(((np.arange(CANVAS_W) + 0.5 - ux) / dx) * sx + tx).astype(int)
    ok_y, ok_x = (iy >= 0) & (iy < mask.shape[0]), (ix >= 0) & (ix < mask.shape[1])
    out = np.zeros((CANVAS_H, CANVAS_W), mask.dtype)
    out[np.ix_(ok_y, ok_x)] = mask[np.ix_(iy[ok_y], ix[ok_x])]
    return out


def normalize(mask, target_h=CANVAS_H, canvas_w=CANVAS_W):
    if getattr(mask, "box", None) is not None:
        return reframe(np.asarray(mask), ((1.0, 1.0), (0.0, 0.0)), geometry(mask))
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


FLIP_SIDE = os.environ.get("CF_FLIP_SIDE") == "1"   # PIPELINE 29.L11-0 (opt-in: hfoo left .43 -> .32): front/left/back pick the mirror by the shift-tolerant IoU
SIDE_VIEWS = ("front", "left", "back")
SIDE_MARGIN = 0.05     # side_iou must separate the mirrors by this much to overrule the plain IoU
SIDE_STEP = 4          # the shift search runs on every 4th pixel: it only decides the side, the score stays the plain IoU


def side_iou(a, b):
    """IoU of the masks at the best translation of b (coarse FFT cross-correlation). The panels are framed by their
    bbox, and a drawn prop (a diagonal pike) widens the sheet's bbox but not the model's: the plain IoU then
    prefers the mirror whose body lands on the shifted outline, even with the pack on the wrong side."""
    from scipy.signal import fftconvolve
    a, b = (np.asarray(m)[::SIDE_STEP, ::SIDE_STEP].astype(float) for m in (a, b))
    inter = fftconvolve(a, b[::-1, ::-1], mode="full")
    return float((inter / np.maximum(a.sum() + b.sum() - inter, 1.0)).max())


def pick_variant(concept, options, name):
    """Index of the option (variants(): the mask, its mirror) that matches `concept`. The side views go by side_iou
    when it separates the options by SIDE_MARGIN and FLIP_SIDE is on (opt-in); a near-symmetric figure (a spider's
    front) or any other view keeps the plain IoU."""
    plain = [iou(concept, o) for o in options]
    if FLIP_SIDE and name in SIDE_VIEWS and len(options) > 1:
        shifted = [side_iou(concept, o) for o in options]
        if max(shifted) - min(shifted) >= SIDE_MARGIN:
            return int(np.argmax(shifted))
    return int(np.argmax(plain))


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
# outside the sheet. Switched on 2026-10-28 (user: "pode ligar tudo"): the v7-r2 runs sit at
# 8-17 % uncovered on the critical views, under the caps; a run over them is a CHECK now.
COUPLING_BLOCKING = True
# Proposed caps (best runs n01X v5-fit-r1 / v13, n005 v5-fit-r2 / v6-r4, rounded up +0.03; PIPELINE 21.F7).
# 10 of the 23 IoU-passing runs would be flagged (> 1/3), so they stay a report.
# L12-2 (user: "pode ter verde sobrando, e pouco; vermelho não pode, em nenhum ângulo"): one cap per view, no average. Spill is the model's
# share outside the sheet, bare the sheet's share the model leaves uncovered. Measured before the change: spill .03-.39, bare .02-.44.
UNCOVERED_MAX = dict.fromkeys(("front", "left", "back", "top", "bottom", "rts"), 0.10)
SPILL_MAX = dict.fromkeys(("front", "left", "back", "top", "bottom", "rts"), 0.03)
# Asymmetric cost of the optimizers (fit_spec, optimize_verts, deform_to_sheet): (SPILL_W * spill px + BARE_W * bare px) / union px.
# SPILL_W = BARE_W = 1 (default) is exactly 1 - IoU. A model INSCRIBED in the sheet and tangent to its edge is the target (CONTACT_*).
SPILL_W, BARE_W = float(os.environ.get("CF_SPILL_W", 1.0)), 1.0     # opt-in CF_SPILL_W=3: spill -.00..-.02 for bare +.03..+.06, IoU -.01..-.03 (PIPELINE 30.L12-2)
CONTACT_EPS = 2        # px (canvas of the gate): a model contour pixel this close, inside the sheet, touches the sheet's contour
CONTACT_MIN = 0.70     # CHECK (report) share of the sheet's contour touched from inside; not a gate yet (L12-2)


def asym_cost(concept, model, spill_w=None, bare_w=None):
    """(spill_w * model px outside the sheet + bare_w * sheet px uncovered) / union px; weights default to SPILL_W / BARE_W.
    With both 1 it is 1 - iou(concept, model)."""
    spill_w, bare_w = SPILL_W if spill_w is None else spill_w, BARE_W if bare_w is None else bare_w
    if spill_w == bare_w == 1:
        return 1 - iou(concept, model)
    c, m = concept.astype(bool), model.astype(bool)
    union = np.logical_or(c, m).sum()
    return float((spill_w * (m & ~c).sum() + bare_w * (c & ~m).sum()) / union) if union else 0.0


def contact(concept, model, eps=None):
    """Share of the sheet's contour pixels with a contour pixel of the model within `eps` px (CONTACT_EPS) that lies
    inside the sheet: 1 = the model is inscribed and tangent all round, 0 = it never touches the edge from inside
    (shrunk away from it, or spilling over it)."""
    from scipy.ndimage import binary_erosion, distance_transform_edt
    c, m = concept.astype(bool), model.astype(bool)
    if not c.any() or not m.any():
        return 0.0
    inner = m & ~binary_erosion(m) & c
    if not inner.any():
        return 0.0
    edge = c & ~binary_erosion(c)
    return float((distance_transform_edt(~inner)[edge] <= (CONTACT_EPS if eps is None else eps)).mean())


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


PROP_PAD = 2           # px: a prop's mask grows this much, so the body's outline stops short of the prop's edge
BODY_PAD = 0.02        # a body part's parts.json box grows this much (fraction of the panel) before it claims pixels from a prop's box
PROP_BIG = 0.25        # a prop's box over this share of the panel (a diagonal spear's) is mostly figure: the body boxes are cut out of it
PROP_KEEP = 0.5        # a compact prop keeps its mask only when this share of it lies outside the body's boxes
PROP_MIN = 40          # px: a prop mask smaller than this is not a prop on this view
PROP_NEAR = 6          # px: model spill this close to a prop's mask is the prop's


def prop_masks(sheet, view, layout="unit", panels=None):
    """{prop name: normalized canvas mask} of the props drawn in `view` of the sheet (PIPELINE 25.L7-5): the panel's
    pixels inside the prop's parts.json box and outside every body part's box (a diagonal spear's box covers the
    figure), grown PROP_PAD px. {} without a refs/<id>/parts.json or a box for that view. `panels`: concept_panels()."""
    import parts_fit
    from scipy.ndimage import binary_dilation
    doc = parts_fit.load(sheet)
    fig = (panels or concept_panels(pathlib.Path(sheet), layout=layout)).get(view)
    if not doc or fig is None:
        return {}
    pad = lambda b: [max(b[0] - BODY_PAD, 0), max(b[1] - BODY_PAD, 0), b[2] + BODY_PAD, b[3] + BODY_PAD]  # noqa: E731
    body = np.zeros((CANVAS_H, CANVAS_W), bool)
    for p in doc["parts"]:
        if not p.get("prop") and view in p.get("box2d", {}):
            body |= parts_fit.part_mask(fig, pad(p["box2d"][view]))
    out = {}
    for p in doc["parts"]:
        if p.get("prop") and view in p.get("box2d", {}):
            whole = parts_fit.part_mask(fig, p["box2d"][view])
            b = p["box2d"][view]
            m = whole & ~body
            if (b[2] - b[0]) * (b[3] - b[1]) <= PROP_BIG and m.sum() < PROP_KEEP * whole.sum():
                continue         # a compact prop mostly inside the body's boxes (goggles, a belt) is not in the outline
            if m.sum() >= PROP_MIN:
                out[p["name"]] = binary_dilation(m, iterations=PROP_PAD)
    if getattr(fig, "box", None) is not None:       # a body-framed panel: the masks follow its frame (parts.json is in the bbox's)
        src, dst = geometry(np.asarray(fig)), geometry(fig)
        out = {k: reframe(m, src, dst) for k, m in out.items()}
    return out


def body_box(fig, props):
    """(x0, y0, x1, y1) in the pixels of `fig` (a raw panel) of the figure less `props` (prop_masks of the bbox frame):
    the box a body-framed panel is normalized by. None without props."""
    if not props:
        return None
    plain = np.asarray(fig)
    whole = normalize(plain)
    body = whole & ~np.any(list(props.values()), axis=0)
    if not body.any():
        return None
    (sx, sy), (tx, ty) = geometry(plain)
    ys, xs = np.where(body)
    return ((xs.min() - tx) / sx, (ys.min() - ty) / sy, (xs.max() + 1 - tx) / sx, (ys.max() + 1 - ty) / sy)


def framed_panels(path, layout="unit", **kw):
    """concept_panels() with, when FRAME is "body", each panel that has prop masks framed by its body box."""
    panels = concept_panels(path, layout=layout, **kw)
    if FRAME != "body":
        return panels
    boxes = {v: body_box(p, prop_masks(path, v, layout, panels)) for v, p in panels.items()}
    return {v: p if boxes[v] is None else framed(p, boxes[v]) for v, p in panels.items()}


def body_mask(sheet, view, layout="unit", panels=None):
    """The view's normalized panel mask minus its props' masks: what the body (not what it carries) looks like.
    The whole panel when the view has no prop mask."""
    panels = panels or concept_panels(pathlib.Path(sheet), layout=layout)
    props = prop_masks(sheet, view, layout, panels)
    whole = normalize(panels[view])
    return whole & ~np.any(list(props.values()), axis=0) if props else whole


def coupling_split(concept, model, props):
    """`uncovered` / `spill` of coupling() told apart as body and props (`props`: boolean union of the view's prop
    masks): uncovered = sheet pixels bare, by whether the sheet pixel is in a prop mask, as shares of the sheet;
    spill = model outside the sheet, by whether it is within PROP_NEAR px of a prop mask, as shares of the model.
    Each pair sums to the coupling() total; the gate stays on the total."""
    from scipy.ndimage import binary_dilation
    c, m = concept.astype(bool), model.astype(bool)
    bare, spill = c & ~m, m & ~c
    near = binary_dilation(props, iterations=PROP_NEAR)
    share = lambda x, total: round(float(x.sum() / max(total.sum(), 1)), 4)  # noqa: E731
    return {"uncovered_body": share(bare & ~props, c), "uncovered_prop": share(bare & props, c),
            "spill_body": share(spill & ~near, m), "spill_prop": share(spill & near, m)}


def body_prop_scores(concept, model, props):
    """The view told apart as body and props (PIPELINE 30.L12-5; `props`: boolean union of the view's prop masks). The sheet's
    body is the panel less the prop masks; the model's prop is what lies in a prop mask or spills within PROP_NEAR px of one
    (coupling_split's attribution), its body is the rest. {body,prop}_{iou,spill,bare}, each pair measured on its own pair of
    masks (spill = share of that model part outside its sheet part, bare = share of the sheet part it leaves uncovered)."""
    from scipy.ndimage import binary_dilation
    c, m = concept.astype(bool), model.astype(bool)
    prop_m = (m & props) | (m & ~c & binary_dilation(props, iterations=PROP_NEAR))
    out = {}
    for name, cs, ms in (("body", c & ~props, m & ~prop_m), ("prop", props & c, prop_m)):
        both = (cs & ms).sum()
        out |= {f"{name}_iou": round(float(both / max((cs | ms).sum(), 1)), 4),
                f"{name}_spill": round(float((ms & ~cs).sum() / max(ms.sum(), 1)), 4),
                f"{name}_bare": round(float((cs & ~ms).sum() / max(cs.sum(), 1)), 4)}
    return out


def split_of(sheet, view, layout, panels, concept, model):
    """coupling_split() and body_prop_scores() of one view, {} when the sheet has no prop mask there (no parts.json, or no
    box for the view)."""
    props = prop_masks(sheet, view, layout, panels)
    if not props:
        return {}
    union = np.any(list(props.values()), axis=0)
    return coupling_split(concept, model, union) | body_prop_scores(concept, model, union)


def gated_values(r):
    """(IoU, coupling dict) the gate judges a view's report `r` by: the body's when the sheet has props there (the props are a
    CHECK, printed), else the whole silhouette's."""
    if "body_iou" not in r:
        return r["iou"], r
    return r["body_iou"], {"uncovered": r["body_bare"], "spill": r["body_spill"]}


def body_text(r):
    """'  [body IoU .71 spill .02 bare .05 | prop CHECK IoU .55 spill .20]' for a view with props, else ''."""
    if "body_iou" not in r:
        return ""
    return (f"  [body IoU {r['body_iou']:.3f} spill {r['body_spill']:.3f} bare {r['body_bare']:.3f} | prop CHECK IoU "
            f"{r['prop_iou']:.3f} spill {r['prop_spill']:.3f} bare {r['prop_bare']:.3f}]")


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


def bbox_masks(panels, model, rotate, masks):
    """`masks` ({view: model mask best_match chose}) for the colour stage, which frames by bbox: with FRAME "body" the
    masks are matched again against the bbox-framed panels (the mirror it picks is against those)."""
    if FRAME != "body":
        return masks
    plain = oriented({k: np.asarray(v) for k, v in panels.items()}, rotate)
    return {n: best_match(plain[n], model[n], n)[1] for n in masks}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet", type=pathlib.Path)
    ap.add_argument("glb", type=pathlib.Path)
    ap.add_argument("outdir", type=pathlib.Path)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--measure", action="store_true", help="print sheet proportions, r_sym and coherence and exit")
    ap.add_argument("--rig", default=None, help="rig family: picks its gates (GATES + RIG_GATES)")
    ap.add_argument("--layout", default="unit", choices=("unit", "building"))
    ap.add_argument("--shape", action="store_true",
                    help="stage 1 (clay): silhouette gates only, no colour zones")
    ap.add_argument("--ids", action="store_true",
                    help="glb is the palette-colour rebuild of the shape (no clay grey): only measure its "
                         "colour zones, from the --tilts cameras; writes outdir/zones_clay.json")
    ap.add_argument("--turn", type=pathlib.Path, default=None,
                    help="refs/<id>/sheet-turn.jpg: also measure its four 3/4 panels (azimuth sweep), report only")
    ap.add_argument("--space", choices=("legacy", "oklab"), default="legacy",
                    help="colour space of the zone feature (oklab: see PIPELINE 19.C2 for why legacy is the default)")
    ap.add_argument("--rotate", default="",
                    help="top/bottom views whose sheet panel is drawn turned 180 degrees, e.g. top,bottom "
                         "(the colour stage reuses what the shape stage detected; unset = detect)")
    ap.add_argument("--tilts", default="",
                    help="pin the top/bottom/rts cameras, e.g. top:10,bottom:20,rts:35/30 "
                         "(the colour stage reuses the shape stage's cameras)")
    ap.add_argument("--flip-side", action="store_true",
                    help="front/left/back pick the mirror by the shift-tolerant IoU (29.L11-0), not the plain IoU")
    ap.add_argument("--frame", choices=("bbox", "body"), default=None,
                    help="frame the panels by the figure's bbox or by its body without the props (29.L11-0b; default CF_FRAME or bbox)")
    args = ap.parse_args()
    global ZONE_SPACE, FLIP_SIDE, FRAME
    ZONE_SPACE = args.space
    FLIP_SIDE = FLIP_SIDE or args.flip_side
    FRAME = args.frame or FRAME
    gates = gates_for(args.rig)
    if args.measure:
        print(json.dumps({**measure(args.sheet), "sheet": sheet_report(args.sheet, args.layout)}, indent=2))
        return 0

    args.outdir.mkdir(parents=True, exist_ok=True)
    if args.ids:
        rotate = set(args.rotate.split(","))
        return 0 if ids_zones(args.sheet, args.glb, args.outdir, args.layout, args.tilts, rotate) else 1
    renders = args.outdir / "sil"
    if not args.no_render:
        subprocess.run(["blender", "-b", "-P", str(HERE / "render_silhouette.py"),
                        "--", str(args.glb), str(renders)], check=True,
                       capture_output=True, text=True)

    panels = framed_panels(args.sheet, layout=args.layout)
    model = model_panels(renders, args.glb.stem)
    if args.tilts:
        from views import parse_tilts
        model = pin_tilts(model, parse_tilts(args.tilts))

    rotate = detect_rotated(panels, model, args.rotate)
    concept = oriented(panels, rotate)
    boxes = model_boxes(args.glb, model, panels)
    if rts_path(args.sheet).exists():
        concept["rts"] = normalize(foreground(rts_path(args.sheet), 768))
    waived = write_sheet_report(args)    # views where the sheet contradicts itself: measured, not gated
    print(f"{'view':8} {'IoU':>6}  {'L1':>6}  {'32px':>5}  {'camera':>6}  {'spill':>5} {'bare':>5} {'cont':>5}  gate")
    report, bad, best_masks = {}, 0, {}
    for name in [v for v in concept if model.get(v)]:
        best, best_mask, tilt, flipped = best_match(concept[name], model[name], name, boxes.get(name))
        l1 = float(np.abs(profile(concept[name]) - profile(best_mask)).mean())
        px = iou(downsample(concept[name]), downsample(best_mask))
        gate = gates.get(name)
        report[name] = {"iou": round(best, 4), "width_l1": round(l1, 4),
                        "iou_32": round(px, 4), "chamfer": round(chamfer(concept[name], best_mask), 4),
                        "tilt": tilt, "flipped": flipped, "frame": "body" if getattr(panels.get(name), "box", None) is not None else "bbox", "gate": gate, **coupling(concept[name], best_mask),
                        "contact": round(contact(concept[name], best_mask), 4),
                        **split_of(args.sheet, name, args.layout, panels, concept[name], best_mask),
                        **head_of(name, rotate)}
        g_iou, g_cov = gated_values(report[name])
        ok = (gate is None or g_iou >= gate) and coupling_ok(name, g_cov)
        report[name]["incoherent"] = name in waived
        ok, verdict = verdict_of(gate, ok, name in waived)
        bad += 0 if ok else 1
        print(f"{name:8} {best:6.3f}  {l1:6.3f}  {px:5.3f}  {str(tilt):>6}  {report[name]['spill']:5.3f} {report[name]['uncovered']:5.3f} {report[name]['contact']:5.3f}  {verdict}"
              + ("" if report[name]["contact"] >= CONTACT_MIN else "  (contact CHECK)")
              + body_text(report[name]))
        write_mask(concept[name], args.outdir / f"mask-concept-{name}.png", (255, 80, 80))
        write_mask(best_mask, args.outdir / f"mask-model-{name}.png", (80, 255, 80))
        write_overlay(concept[name], best_mask, args.outdir / f"overlay-{name}.png")
        best_masks[name] = best_mask

    if not args.shape:
        bad += zone_gate(report, zone_views(args.sheet, renders, args.glb.stem, bbox_masks(panels, model, rotate, best_masks), args.layout,
                                             report_tilts(report),
                                             rotate))
    (args.outdir / "silhouette.json").write_text(json.dumps(report, indent=2))
    if args.turn:
        print("turn views (3/4 IoU @ azimuth):",
              {a: (r["iou"], r["azim"]) for a, r in turn_report(args.turn, args.glb, args.outdir).items()})
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
