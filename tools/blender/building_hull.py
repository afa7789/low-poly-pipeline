#!/usr/bin/env python3
"""Base volume of a building from its sheet: the hull part (Sano 2026 §3.4-3.5; Gao, Wu, Pan 2022).

    python3.14 tools/blender/building_hull.py <sheet.jpg> <outdir> [--height 4.0]

Runs in the system Python (numpy, scipy). The front and left elevation masks are reduced to the
big masses (morphological opening drops chimneys, ramps, rails, overhang tips), traced, simplified
by Douglas-Peucker and made orthogonal (edges within ORTHO_DEG of H/V become H/V). The result is
one spec part, kind box with opts {"cut": "sheet", "hull": {"front": .., "left": ..}}: build_unit
extrudes the front outline along z, the left along x, intersects them (BOOLEAN EXACT, the cut_hull
path) and dissolves the coplanar faces. The LLM gets the volume ready and adds only roof and props.
The CLI writes hull-spec.json (the partial spec), hull.glb and hull-iou.json (hull alone vs sheet).
"""
import argparse
import json
import pathlib

import numpy as np

import silhouette as SIL
from views import layout_of

KEEP = 0.75       # a row (column) thinner than this share of the fullest one is not the body
EPS = 0.02        # Douglas-Peucker tolerance, share of the body height
LIMIT = 16        # vertices per outline: a hull is a few dozen triangles, not a budget
MIN_EDGE = 0.06   # an edge shorter than this (share of the body height) is a rounded corner, not a wall
ORTHO_DEG = 10    # an edge this close to H/V is made so (silhouette.snap_axes)
HEIGHT = 4.0      # spec metres of the whole figure (rig_families.top("building"))
MATERIAL = "hull"


def trim(mask, axis):
    """`mask` without the leading and trailing rows (axis 1) or columns (axis 0) whose pixel count
    is under KEEP of the fullest one: the chimney above the roof, the ramp and rails below the
    wall line, the arm out of the side. Only the ends go; a lower wing or roof tier goes with them, the author adds those."""
    n = mask.sum(axis=axis)
    ok = (n >= KEEP * n.max()).nonzero()[0]
    return mask[ok[0]:ok[-1] + 1] if axis == 1 else mask[:, ok[0]:ok[-1] + 1]


def body(mask):
    """The big masses of an elevation mask: its bbox crop trimmed of thin ends, rows then columns."""
    ys, xs = mask.nonzero()
    return trim(trim(mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1], 1), 0)


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def collapse(pts, i):
    """`pts` with the short edge i -> i+1 replaced by the corner its neighbours point at: the
    trace rounds every right angle into a few diagonal pixels, this squares it again."""
    j = (i + 1) % len(pts)
    a, b, p = pts[i], pts[j], pts[i - 1]
    corner = np.array([a[0], b[1]]) if abs(a[0] - p[0]) < abs(a[1] - p[1]) else np.array([b[0], a[1]])
    rest = [q for k, q in enumerate(pts) if k not in (i, j)]
    rest.insert(min(i, j), corner)
    return rest


def rectify(poly):
    """Axis snap, short diagonal edges (MIN_EDGE of the body height) squared into corners, then
    no collinear vertices. Orthogonality as Sano 2026 §3.4: what the sheet draws square, builds square."""
    pts = list(SIL.snap_axes(np.array(poly, float), ORTHO_DEG))
    while len(pts) > 4:
        short = [i for i in range(len(pts)) if np.hypot(*(pts[(i + 1) % len(pts)] - pts[i])) < MIN_EDGE]
        if not short:
            break
        pts = collapse(pts, short[0])
    while len(pts) > 3:
        keep = [p for i, p in enumerate(pts)
                if abs(cross(p - pts[i - 1], pts[(i + 1) % len(pts)] - p)) > 1e-4]
        if len(keep) == len(pts):
            break
        pts = keep
    return pts


def hull_outline(mask, scale):
    """[[a, y]] of one elevation's body in metres: a from the bbox centre, y up from the feet."""
    return [[round(float(a) * scale, 3), round(float(y) * scale, 3)]
            for a, y in rectify(SIL.outline(body(mask), eps=EPS, limit=LIMIT))]


def rows(mask):
    ys = mask.any(axis=1).nonzero()[0]
    return int(ys.max() - ys.min() + 1)


def hull_part(panels, height=HEIGHT, bone="body"):
    """The spec row of the base volume from the sheet's panels (silhouette.concept_panels, building
    layout). The whole front figure is `height` metres tall; the body is as tall in both views,
    so one metre scale serves the two outlines. x and z are centred on 0, the feet on y = 0."""
    scale = rows(body(panels["front"])) * height / rows(panels["front"])
    front, left = hull_outline(panels["front"], scale), hull_outline(panels["left"], scale)
    xs, zs = [p[0] for p in front], [p[0] for p in left]
    top = max(p[1] for p in front)
    dims = [round(max(xs) - min(xs), 3), round(top, 3), round(max(zs) - min(zs), 3)]
    at = [round((max(xs) + min(xs)) / 2, 3), round(top / 2, 3), round((max(zs) + min(zs)) / 2, 3)]
    return [bone, "box", dims, at, MATERIAL, {"cut": "sheet", "hull": {"front": front, "left": left}}]


def is_hull(part):
    return isinstance(part[5], dict) and "hull" in part[5]


def with_hull(spec, part):
    """The spec with the hull part first (kept when it already has one) and the palette slot
    the part names. An author that wrote its own `hull` slot keeps its colour."""
    if any(is_hull(p) for p in spec["parts"]):
        return spec
    palette = {MATERIAL: {"surface": "stone", "color": "#6b6f75"}, **spec.get("palette", {})}
    return {**spec, "palette": palette, "parts": [part] + spec["parts"]}


def brief_text(part):
    """What the brief says about the ready volume (appended after the measured numbers)."""
    x, y, z = part[2]
    return (f"\nBASE VOLUME, READY: the walls are already built from the sheet's own front and left "
            f"outlines ({x:.2f} m wide, {y:.2f} m tall, {z:.2f} m deep, centred on x = 0 and z = 0, "
            f"feet on y = 0, material slot \"{MATERIAL}\"). Do NOT write it and do NOT recreate it "
            f"with boxes. Write only what sits on or against it: the roof or cap, the door recess, "
            f"stacks, tanks, cranes, rails, ramps and the team-colour zone, placed relative to that "
            f"volume.\n")


def export(part, work, kind="building"):
    """Build the hull alone: work/hull-spec.json (partial spec) and work/hull.glb (clay). Returns
    the triangle count, 0 when Blender wrote nothing. Imports spec_pipeline here: it imports us."""
    import cut_hull
    from spec_pipeline import clay_args, glb_stats, tool
    work = pathlib.Path(work)
    work.mkdir(parents=True, exist_ok=True)
    spec = with_hull({"rig": "building", "parts": []}, part)
    (work / "hull-spec.json").write_text(json.dumps(spec, indent=2))
    glb = work / "hull.glb"
    tool("build_unit.py", work / "hull-spec.json", glb, *clay_args(kind),
         *cut_hull.args(spec, None, kind, work), blender=True)
    return glb_stats(glb)[0] if glb.exists() else 0


def measure(sheet, glb, work):
    """IoU of the hull alone against the sheet: front, left, back (silhouette sweep, as the
    gate) and the roof plan against the top view, next to the IoU of a plain bbox box (`bbox_box`)
    and of the hull against the sheet's body alone (`body_only`: how well the volume is traced).
    Written to work/hull-iou.json."""
    import subprocess
    work = pathlib.Path(work)
    subprocess.run(["blender", "-b", "-P", str(SIL.HERE / "render_silhouette.py"), "--", str(glb),
                    str(work / "sil")], check=True, capture_output=True, text=True)
    sheet_panels = SIL.concept_panels(sheet, layout="building")
    concept = {k: SIL.normalize(v) for k, v in sheet_panels.items()}
    model = SIL.model_panels(work / "sil", glb.stem)
    out, box, mass = {}, {}, {}
    for view, name in (("front", "front"), ("left", "left"), ("back", "back"), ("roof", "top")):
        out[view] = round(SIL.best_match(concept[view], model[name], name)[0], 4)
        # the baseline: one box of the sheet's own bounding box (what a plain `box` part gives)
        box[view] = round(float(concept[view].sum() / SIL.crop(concept[view]).size), 4)
        # what the hull is for: the sheet's body without the thin ends, same camera as the best match
        target = SIL.normalize(body(sheet_panels[view]))
        mass[view] = round(SIL.iou(target, SIL.best_match(target, model[name], name)[1]), 4)
    out["bbox_box"], out["body_only"] = box, mass
    (work / "hull-iou.json").write_text(json.dumps(out, indent=2))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("sheet", type=pathlib.Path)
    ap.add_argument("outdir", type=pathlib.Path)
    ap.add_argument("--height", type=float, default=HEIGHT)
    ap.add_argument("--kind", default="building", choices=("building", "large"))
    args = ap.parse_args()
    assert layout_of(args.kind) == "building"
    part = hull_part(SIL.concept_panels(args.sheet, layout="building"), args.height)
    tris = export(part, args.outdir, args.kind)
    print(f"hull {part[2]} m, front {len(part[5]['hull']['front'])} / left "
          f"{len(part[5]['hull']['left'])} vertices, {tris} tris")
    if tris:
        print(json.dumps(measure(args.sheet, args.outdir / "hull.glb", args.outdir)))
    return 0 if tris else 1


if __name__ == "__main__":
    raise SystemExit(main())
