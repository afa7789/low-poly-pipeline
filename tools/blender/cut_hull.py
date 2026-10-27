"""Parts cut by the sheet's silhouette (opts {"cut": "sheet"}; Sano 2026, visual hull: the
extrusion of the front outline intersected with the extrusion of the left outline).

Runs in the system Python (numpy, scipy), before the Blender build: for every part that asks
for the cut it returns the two simplified outlines (<= 8 vertices) of the strip of the
approved sheet's front and left masks that the part covers, fitted to the part's own box.
build_unit.py only extrudes and intersects them (`cuts=<json>` argument). A `lathe` part without
a profile of its own gets one read from the same masks (lathe_profile); it travels in the same json.
"""
import json
import math
import pathlib

import numpy as np

import lathe_limb
import preflight
import silhouette as SIL
from views import layout_of

LIMIT = 8       # vertices per outline
PAD = 0.1       # the strip is read this much wider than the part, then fitted back to it
MIN_ROWS = 6    # a strip thinner than this (px) is not worth tracing
PROFILE_WIN = 1.25   # a lathe reads the sheet this many r either side of its centre; a profile value is at most this
PROFILE_MIN = 0.1
TOP_OPEN = 0.12   # a plate read from the top panel drops what is thinner than this share of its strip (legs)


def wants_cut(opts):
    return isinstance(opts, dict) and opts.get("cut") == "sheet"


def strip_outline(mask, frame, lo, hi, axis):
    """Outline of the rows/columns of `mask` the box (lo, hi) covers, as [(a, y)] fitted to the box.
    frame = (H, centre): figure height and the figure's centre along `axis` (0 = x, 2 = z).
    None when the strip is empty or thinner than MIN_ROWS."""
    height, centre = frame
    ys, xs = mask.nonzero()
    bottom, h, c0 = ys.max(), ys.max() - ys.min() + 1, (xs.min() + xs.max()) / 2
    scale = h / height
    pad = PAD * (hi[axis] - lo[axis])
    r0, r1 = (int(round(bottom - hi[1] * scale)), int(round(bottom - lo[1] * scale)) + 1)
    k0, k1 = (int(round(c0 + (lo[axis] - pad - centre) * scale)),
              int(round(c0 + (hi[axis] + pad - centre) * scale)) + 1)
    strip = mask[max(r0, 0):r1, max(k0, 0):k1]
    if strip.shape[0] < MIN_ROWS or not strip.any():
        return None
    poly = SIL.outline(strip, eps=0.02, limit=LIMIT)
    if len(poly) > LIMIT:
        return None
    us, vs = zip(*poly)
    sa, sy = ((hi[axis] - lo[axis]) / ((max(us) - min(us)) or 1),
              (hi[1] - lo[1]) / ((max(vs) - min(vs)) or 1))
    return [[round(lo[axis] + (u - min(us)) * sa, 4), round(lo[1] + (v - min(vs)) * sy, 4)]
            for u, v in poly]


def hull_cut(hull, box):
    """The cut entry of a building's base volume (building_hull.py): its outlines are already in
    metres, so they are used as they are; the boolean is followed by a planar dissolve."""
    return {"box": [list(box[0]), list(box[1])], **hull, "dissolve": True}


def cut_polys(parts, sheet, layout="unit"):
    """{part index: {"box": [lo, hi], "front": [[x, y]..], "left": [[z, y]..]}} for the parts that
    ask for the cut and whose strip could be read; the others build as their plain primitive."""
    wanted = [i for i, p in enumerate(parts) if wants_cut(p[5])]
    if not wanted:
        return {}
    boxes = [preflight.bbox(p) for p in parts]
    out = {i: hull_cut(parts[i][5]["hull"], boxes[i]) for i in wanted if "hull" in parts[i][5]}
    wanted = [i for i in wanted if i not in out]
    if not wanted:
        return out
    top = max(b[1][1] for b in boxes)
    centre = {a: (min(b[0][a] for b in boxes) + max(b[1][a] for b in boxes)) / 2 for a in (0, 2)}
    panels = SIL.concept_panels(sheet, layout=layout)
    for i in wanted:
        lo, hi = boxes[i]
        front = strip_outline(panels["front"], (top, centre[0]), lo, hi, 0)
        left = strip_outline(panels["left"], (top, centre[2]), lo, hi, 2)
        if front and left:
            out[i] = {"box": [list(lo), list(hi)], "front": front, "left": left}
    return out


def lathe_profile(mask, frame, part, axis):
    """The profile (lathe_limb.SHEET_RINGS radii, bottom to top, as fractions of the part's r) of a
    lathe from the rows of `mask` it covers, or None when the strip is empty. frame = (H, centre)
    as in strip_outline; axis 0 reads the front panel (x radius), 2 the left one (z radius, times
    squash). Only the columns within PROFILE_WIN * r of the part's centre count, so an arm beside
    a torso is not part of it."""
    height, centre = frame
    (r, h), at, opts = part[2], part[3], part[5]
    if not mask.any():
        return None
    ys, xs = mask.nonzero()
    bottom, scale, c0 = ys.max(), (ys.max() - ys.min() + 1) / height, (xs.min() + xs.max()) / 2
    k0, k1 = (int(round(c0 + (at[axis] + s * PROFILE_WIN * r - centre) * scale)) for s in (-1, 1))
    step, out = h / (lathe_limb.SHEET_RINGS - 1), []
    for i in range(lathe_limb.SHEET_RINGS):
        y = at[1] - h / 2 + i * step
        r0, r1 = (int(round(bottom - (y + s * step / 2) * scale)) for s in (1, -1))
        cols = mask[max(r0, 0):max(r1, 0) + 1, max(k0, 0):k1 + 1].any(axis=0).nonzero()[0]
        if not len(cols):
            out.append(None)
            continue
        half = (cols.max() - cols.min() + 1) / 2 / scale
        out.append(half * (float(opts.get("squash", 1.0)) if axis == 2 else 1.0) / r)
    if not any(v is not None for v in out):
        return None
    known = [v for v in out if v is not None]
    return [round(min(max(v if v is not None else min(known), PROFILE_MIN), PROFILE_WIN), 3) for v in out]


def lathe_profiles(parts, sheet, layout="unit"):
    """{part index: {"profile": [...]}} for the lathe parts that bring no profile and whose strip of
    the sheet could be read; the others build from their own or the default profile."""
    wanted = [i for i, p in enumerate(parts) if p[1] == "lathe" and not p[5].get("profile")]
    if not wanted or sheet is None:
        return {}
    boxes = [preflight.bbox(p) for p in parts]
    top = max(b[1][1] for b in boxes)
    centre = {a: (min(b[0][a] for b in boxes) + max(b[1][a] for b in boxes)) / 2 for a in (0, 2)}
    panels = SIL.concept_panels(sheet, layout=layout)
    out = {}
    for i in wanted:
        axis = 2 if parts[i][5].get("axis") == "left" else 0
        prof = lathe_profile(panels["left" if axis else "front"], (top, centre[axis]), parts[i], axis)
        if prof:
            out[i] = {"profile": prof}
    return out


def chain_widths(mask, frame, part, axis):
    """Width of each joint of a one-radius chain as a fraction of dims[0] (lathe_limb.chain_radii),
    from `mask` (front or left panel; axis 0 or 2): the run of mask pixels across the chain's
    direction at the joint, at most PROFILE_WIN * r each side. None when no joint is inside the
    mask. frame = (H, centre) as in strip_outline."""
    height, centre = frame
    r = part[2][0]
    if not mask.any():
        return None
    ys, xs = mask.nonzero()
    bottom, scale, c0 = ys.max(), (ys.max() - ys.min() + 1) / height, (xs.min() + xs.max()) / 2
    joints = lathe_limb.chain_joints(part[0], part[5]["bones"])
    out = []
    for i, c in enumerate(joints):
        a, b = joints[max(i - 1, 0)], joints[min(i + 1, len(joints) - 1)]
        da, dy = b[axis] - a[axis], b[1] - a[1]
        norm = math.hypot(da, dy) or 1.0
        row0, col0 = bottom - c[1] * scale, c0 + (c[axis] - centre) * scale
        reach = int(PROFILE_WIN * r * scale)
        run = [t for t in range(-reach, reach + 1)
               if _inside(mask, round(row0 - t * da / norm), round(col0 - t * dy / norm))]
        out.append(_run(run) / scale / 2 / r if 0 in run else None)
    known = [v for v in out if v is not None]
    if not known:
        return None
    return [round(min(max(v if v is not None else min(known), PROFILE_MIN), PROFILE_WIN), 3) for v in out]


def _inside(mask, row, col):
    return 0 <= row < mask.shape[0] and 0 <= col < mask.shape[1] and bool(mask[row, col])


def _run(ts):
    """Length of the run of consecutive integers in `ts` that holds 0."""
    have = set(ts)
    lo = hi = 0
    while lo - 1 in have:
        lo -= 1
    while hi + 1 in have:
        hi += 1
    return hi - lo + 1


def chain_profiles(parts, sheet, layout="unit"):
    """{part index: {"radii": [...]}} for the chain parts with one radius whose sheet panel could be
    read; the others build from their own radii or the taper."""
    wanted = [i for i, p in enumerate(parts) if p[1] == "chain" and len(p[2]) == 1]
    if not wanted or sheet is None:
        return {}
    boxes = [preflight.bbox(p) for p in parts]
    top = max(b[1][1] for b in boxes)
    centre = {a: (min(b[0][a] for b in boxes) + max(b[1][a] for b in boxes)) / 2 for a in (0, 2)}
    panels = SIL.concept_panels(sheet, layout=layout)
    out = {}
    for i in wanted:
        axis = 0 if parts[i][5].get("profile_axis") == "front" else 2
        widths = chain_widths(panels["left" if axis else "front"], (top, centre[axis]), parts[i], axis)
        if widths:
            out[i] = {"radii": widths}
    return out


def top_outline(mask, extent, lo, hi):
    """Outline of the top panel inside the box (lo, hi) as [[u, v]] in 0-1 of the box (u along x, v
    toward +z, the front, which the sheet draws at the bottom). `extent` = (lo, hi) of the whole
    figure: the panel's figure is stretched onto it, so the tilt of the panel costs a little depth.
    None when the strip is empty or thinner than MIN_ROWS."""
    ys, xs = mask.nonzero()
    (flo, fhi), pad = extent, PAD
    sx, sz = (xs.max() - xs.min() + 1) / ((fhi[0] - flo[0]) or 1), (ys.max() - ys.min() + 1) / ((fhi[2] - flo[2]) or 1)
    k0, k1 = (int(round(xs.min() + (v - flo[0]) * sx)) for v in (lo[0] - pad * (hi[0] - lo[0]), hi[0] + pad * (hi[0] - lo[0])))
    r0, r1 = (int(round(ys.min() + (v - flo[2]) * sz)) for v in (lo[2] - pad * (hi[2] - lo[2]), hi[2] + pad * (hi[2] - lo[2])))
    strip = mask[max(r0, 0):r1 + 1, max(k0, 0):k1 + 1]
    if strip.shape[0] < MIN_ROWS or not strip.any():
        return None
    from scipy import ndimage
    body = ndimage.binary_opening(strip, iterations=max(1, int(TOP_OPEN * min(strip.shape))))   # legs are thinner than the shell
    poly = SIL.outline(body if body.any() else strip, eps=0.02, limit=LIMIT)
    if len(poly) > LIMIT:
        return None
    us, vs = zip(*poly)
    return [[round((u - min(us)) / ((max(us) - min(us)) or 1), 3), round(1 - (v - min(vs)) / ((max(vs) - min(vs)) or 1), 3)]
            for u, v in poly]


def top_flipped(mask, boxes, extent):
    """True when the top panel is drawn head up (the sheet's front at the top, rows running toward -z):
    the union of the part boxes seen from above is laid on the panel's figure both ways and the better
    overlap wins. A humanoid sheet draws it front down (views.py), a spider's straight top-down view
    does not, and a plate read the wrong way round would land on the abdomen."""
    ys, xs = mask.nonzero()
    (flo, fhi) = extent
    sx, sz = (xs.max() - xs.min() + 1) / ((fhi[0] - flo[0]) or 1), (ys.max() - ys.min() + 1) / ((fhi[2] - flo[2]) or 1)
    top = np.zeros(mask.shape, bool)
    for lo, hi in boxes:
        c0, c1 = (int(round(xs.min() + (v - flo[0]) * sx)) for v in (lo[0], hi[0]))
        r0, r1 = (int(round(ys.min() + (v - flo[2]) * sz)) for v in (lo[2], hi[2]))
        top[max(r0, 0):max(r1, 0) + 1, max(c0, 0):max(c1, 0) + 1] = True
    fig = mask[ys.min():ys.max() + 1]
    boxes_fig = top[ys.min():ys.max() + 1]
    return SIL.iou(fig[::-1], boxes_fig) > SIL.iou(fig, boxes_fig)


def plate_profiles(parts, sheet, layout="unit"):
    """{part index: {"profile": [[u, v]..]}} for the plates that bring no profile and whose strip of
    the sheet could be read (front, left: strip_outline of the part's box; top: top_outline); the
    others build the default polygon. The box is the plate's own, unrotated."""
    wanted = [i for i, p in enumerate(parts) if p[1] == "plate" and not p[5].get("profile")]
    if not wanted or sheet is None:
        return {}
    boxes = [preflight.bbox(p) for p in parts]
    top = max(b[1][1] for b in boxes)
    ext = (tuple(min(b[0][a] for b in boxes) for a in range(3)), tuple(max(b[1][a] for b in boxes) for a in range(3)))
    panels = SIL.concept_panels(sheet, layout=layout)
    out = {}
    for i in wanted:
        lo, hi = boxes[i]
        axis = parts[i][5].get("axis", "front")
        if axis == "top":
            mask = panels["top"][::-1] if top_flipped(panels["top"], boxes, ext) else panels["top"]
            prof = top_outline(mask, ext, lo, hi)
        else:
            a = 2 if axis == "left" else 0
            poly = strip_outline(panels[axis], (top, (ext[0][a] + ext[1][a]) / 2), lo, hi, a)
            prof = poly and [[round((u - lo[a]) / ((hi[a] - lo[a]) or 1), 3), round((v - lo[1]) / ((hi[1] - lo[1]) or 1), 3)]
                             for u, v in poly]
        if prof:
            out[i] = {"profile": prof}
    return out


def args(spec, sheet, kind, work):
    """["cuts=<json>"] for build_unit.py: the outlines of the spec's cut parts and the sheet
    profiles of its lathes written to work/cuts.json; [] when there is neither."""
    cuts = cut_polys(spec["parts"], sheet, layout_of(kind))
    cuts.update(lathe_profiles(spec["parts"], sheet, layout_of(kind)))
    cuts.update(chain_profiles(spec["parts"], sheet, layout_of(kind)))
    cuts.update(plate_profiles(spec["parts"], sheet, layout_of(kind)))
    if not cuts:
        return []
    path = pathlib.Path(work) / "cuts.json"
    path.write_text(json.dumps(cuts))
    return [f"cuts={path}"]
