"""Parts cut by the sheet's silhouette (opts {"cut": "sheet"}; Sano 2026, visual hull: the
extrusion of the front outline intersected with the extrusion of the left outline).

Runs in the system Python (numpy, scipy), before the Blender build: for every part that asks
for the cut it returns the two simplified outlines (<= 8 vertices) of the strip of the
approved sheet's front and left masks that the part covers, fitted to the part's own box.
build_unit.py only extrudes and intersects them (`cuts=<json>` argument).
"""
import json
import pathlib

import preflight
import silhouette as SIL
from views import layout_of

LIMIT = 8       # vertices per outline
PAD = 0.1       # the strip is read this much wider than the part, then fitted back to it
MIN_ROWS = 6    # a strip thinner than this (px) is not worth tracing


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


def cut_polys(parts, sheet, layout="unit"):
    """{part index: {"box": [lo, hi], "front": [[x, y]..], "left": [[z, y]..]}} for the parts that
    ask for the cut and whose strip could be read; the others build as their plain primitive."""
    wanted = [i for i, p in enumerate(parts) if wants_cut(p[5])]
    if not wanted:
        return {}
    boxes = [preflight.bbox(p) for p in parts]
    top = max(b[1][1] for b in boxes)
    centre = {a: (min(b[0][a] for b in boxes) + max(b[1][a] for b in boxes)) / 2 for a in (0, 2)}
    panels = SIL.concept_panels(sheet, layout=layout)
    out = {}
    for i in wanted:
        lo, hi = boxes[i]
        front = strip_outline(panels["front"], (top, centre[0]), lo, hi, 0)
        left = strip_outline(panels["left"], (top, centre[2]), lo, hi, 2)
        if front and left:
            out[i] = {"box": [list(lo), list(hi)], "front": front, "left": left}
    return out


def args(spec, sheet, kind, work):
    """["cuts=<json>"] for build_unit.py: the outlines of the spec's cut parts written to
    work/cuts.json; [] when no part is cut or none could be read."""
    cuts = cut_polys(spec["parts"], sheet, layout_of(kind))
    if not cuts:
        return []
    path = pathlib.Path(work) / "cuts.json"
    path.write_text(json.dumps(cuts))
    return [f"cuts={path}"]
