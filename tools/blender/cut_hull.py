"""Parts cut by the sheet's silhouette (opts {"cut": "sheet"}; Sano 2026, visual hull: the
extrusions of the front, left and top outlines intersected).

Runs in the system Python (numpy, scipy), before the Blender build: for every part that asks
for the cut it returns the simplified outlines (<= LIMIT vertices: Douglas-Peucker, edges snapped
to the axes, arcs fitted where a circle explains the contour better) of the strip of the approved
sheet's front, left and top masks that the part covers, fitted to the part's own box.
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

LIMIT = 14      # vertices per outline of a cut part (Sano: 12-16)
PLATE_LIMIT = 8     # ... of a plate's profile (lathe_limb.PLATE_PTS)
ARC_GAIN = 0.5      # an arc replaces a vertex when the circle's residual is under this share of the polyline's
ARC_MIN = 0.01      # ... and the polyline's residual is over this share of the strip height
CUT_BONES = ("spine", "pelvis", "body", "abdomen")   # bones whose largest plain part is cut by default
CUT_KINDS = ("box", "prism", "frustum", "lathe")     # a lathe is built, then trimmed by the prisms
TOP_PRISM = False  # the third prism (top outline): off, it opened the n02X belly and cost n005 left .03 (PIPELINE 24.L6-2)
CUT_MAX = 4     # cut parts per unit by default (each is decimated to its budget in build_unit.cut_part)
PAD = 0.1       # the strip is read this much wider than the part, then fitted back to it
MIN_ROWS = 6    # a strip thinner than this (px) is not worth tracing
PROFILE_WIN = 1.25   # a lathe reads the sheet this many r either side of its centre; a profile value is at most this
PROFILE_MIN = 0.1
TOP_OPEN = 0.12   # a plate read from the top panel drops what is thinner than this share of its strip (legs)


def wants_cut(opts):
    return isinstance(opts, dict) and opts.get("cut") == "sheet"


def hood_index(parts):
    """Index of the widest part on the head bone (the hood or helmet shell), or None."""
    def width(i):
        lo, hi = preflight.bbox(parts[i])
        return hi[0] - lo[0]
    return max((i for i, p in enumerate(parts) if p[0] == "head"), key=width, default=None)


def cuttable(part):
    """A body part the cut may take: an unrotated box, prism, frustum or lathe that is not a prop."""
    return part[1] in CUT_KINDS and isinstance(part[5], dict) and not (
        {"rot", "from", "to", "prop"} & part[5].keys()) and part[5].get("axis") != "z"


def cut_picks(parts):
    """Indices of the parts that get `cut: sheet` by default: the largest cuttable part of each torso,
    pelvis and abdomen bone and the hood, the biggest CUT_MAX of them."""
    def volume(i):
        lo, hi = preflight.bbox(parts[i])
        return float(np.prod(np.subtract(hi, lo)))

    best = [max((i for i, p in enumerate(parts) if p[0] == b and cuttable(p)), key=volume, default=None)
            for b in CUT_BONES]
    pick = [i for i in [*best, hood_index(parts)] if i is not None and cuttable(parts[i])]
    return sorted(dict.fromkeys(pick), key=volume, reverse=True)[:CUT_MAX]


def arcs(poly, dense, room):
    """`poly` (closed, [(x, y)]) with a vertex replaced by points on the circle through its neighbours
    where the contour `dense` between them lies on a circle (Kasa fit) far closer than on the two
    edges: the arcs of Sano 3.4. Two points per arc while the polygon has `room` vertices to spare, else
    one (the arc's middle). The polygon is returned as it was when no arc wins."""
    n, out, spare = len(poly), [], room
    dense = np.asarray(dense, float)
    for i, b in enumerate(poly):
        a, c = np.array(poly[i - 1], float), np.array(poly[(i + 1) % n], float)
        pts = _bulge(dense, a, np.array(b, float), c)
        arc = _arc_points(pts, a, np.array(b, float), c, 2 if spare > 0 else 1) if len(pts) >= 4 else None
        if arc is None:
            out.append(b)
            continue
        spare -= len(arc) - 1
        out.extend(arc)
    return out


def _bulge(dense, a, b, c):
    """The points of `dense` that run from a to c on b's side of the chord."""
    d = c - a
    rel = dense - a
    t = rel @ d / ((d @ d) or 1)
    side = d[0] * rel[:, 1] - d[1] * rel[:, 0]
    return dense[(t >= 0) & (t <= 1) & (side * (d[0] * (b - a)[1] - d[1] * (b - a)[0]) > 0)]


def _arc_points(pts, a, b, c, count):
    """`count` points on the circle fitted to `pts` between a and c when it beats the polyline a-b-c, else None."""
    x, y = pts[:, 0], pts[:, 1]
    sol, *_ = np.linalg.lstsq(np.c_[2 * x, 2 * y, np.ones(len(pts))], x * x + y * y, rcond=None)
    centre = sol[:2]
    radius2 = sol[2] + centre @ centre
    if radius2 <= 0:
        return None
    radius = math.sqrt(radius2)
    on_circle = float(np.sqrt(np.mean((np.hypot(*(pts - centre).T) - radius) ** 2)))
    on_lines = float(np.sqrt(np.mean(np.minimum(_seg_dist(pts, a, b), _seg_dist(pts, b, c)) ** 2)))
    if on_lines < ARC_MIN * _span(pts) or on_circle > ARC_GAIN * on_lines:
        return None
    ang = [math.atan2(*(p - centre)[::-1]) for p in (a, b, c)]
    sweep, to_b = ((ang[k] - ang[0] + math.pi) % (2 * math.pi) - math.pi for k in (2, 1))   # a to c, a to b: the short way
    if to_b * sweep <= 0 or abs(to_b) >= abs(sweep):         # b is not on the arc between a and c
        return None
    return [tuple(float(v) for v in centre + radius * np.array([math.cos(ang[0] + sweep * k), math.sin(ang[0] + sweep * k)]))
            for k in ((1 / 3, 2 / 3) if count == 2 else (0.5,))]


def _span(pts):
    return float(np.ptp(pts, axis=0).max()) or 1.0


def _seg_dist(pts, a, b):
    d = b - a
    t = np.clip((pts - a) @ d / ((d @ d) or 1), 0, 1)
    return np.hypot(*(pts - (a + t[:, None] * d)).T)


def regular_outline(strip, limit, arc=False):
    """The strip's simplified outline (silhouette.outline: Douglas-Peucker, edges snapped to the axes)
    with arcs fitted when `arc`; None when it needs more than `limit` vertices."""
    poly = SIL.outline(strip, eps=0.02, limit=limit)
    if len(poly) > limit:
        return None
    if arc and len(poly) > 3:
        poly = arcs(poly, SIL.outline(strip, eps=0.004, limit=400), limit - len(poly))
    return poly if len(poly) <= limit else None


def strip_outline(mask, frame, lo, hi, axis, limit=PLATE_LIMIT, arc=False):
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
    poly = regular_outline(strip, limit, arc)
    if poly is None:
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


def top_view(panels, boxes, extent):
    """The top panel, turned head down when top_flipped says it is drawn head up."""
    if "top" not in panels:                       # a sheet whose top panel the splitter did not find (h01N): no top view to cut by
        return None
    return panels["top"][::-1] if top_flipped(panels["top"], boxes, extent) else panels["top"]


def top_poly(mask, extent, lo, hi):
    """[[x, z]] metres of the top panel's outline inside the box (lo, hi), or None."""
    poly = top_outline(mask, extent, lo, hi, LIMIT, True)
    return poly and [[round(lo[0] + u * (hi[0] - lo[0]), 4), round(lo[2] + v * (hi[2] - lo[2]), 4)] for u, v in poly]


def cut_polys(parts, sheet, layout="unit"):
    """{part index: {"box": [lo, hi], "front": [[x, y]..], "left": [[z, y]..], "top": [[x, z]..]}} for the
    parts that ask for the cut and whose strip could be read (front and left; the top is left out when
    its panel gives none); the others build as their plain primitive."""
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
    ext = (tuple(min(b[0][a] for b in boxes) for a in range(3)), tuple(max(b[1][a] for b in boxes) for a in range(3)))
    panels = SIL.concept_panels(sheet, layout=layout)
    flat = top_view(panels, boxes, ext) if "top" in panels else None      # building layout: the roof plan, no top panel to read
    for i in wanted:
        lo, hi = boxes[i]
        front = strip_outline(panels["front"], (top, centre[0]), lo, hi, 0, LIMIT, True)
        left = strip_outline(panels["left"], (top, centre[2]), lo, hi, 2, LIMIT, True)
        if front and left:
            out[i] = {"box": [list(lo), list(hi)], "front": front, "left": left,
                      **({"top": t} if TOP_PRISM and flat is not None and (t := top_poly(flat, ext, lo, hi)) else {})}
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


def top_outline(mask, extent, lo, hi, limit=PLATE_LIMIT, arc=False):
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
    poly = regular_outline(body if body.any() else strip, limit, arc)
    if poly is None:
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
            prof = top_outline(top_view(panels, boxes, ext), ext, lo, hi)
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
    layout = layout_of(kind)
    cuts = {}
    for read in (cut_polys, lathe_profiles, chain_profiles, plate_profiles):   # a cut lathe has both its outlines and its profile
        for i, entry in read(spec["parts"], sheet, layout).items():
            cuts.setdefault(i, {}).update(entry)
    if not cuts:
        return []
    path = pathlib.Path(work) / "cuts.json"
    path.write_text(json.dumps(cuts))
    return [f"cuts={path}"]
