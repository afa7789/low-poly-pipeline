#!/usr/bin/env python3
"""Inscribe the model in the sheet's visual hull (PIPELINE 31.L13-5, opt-in `--inscribe cut|on`).

The volume of a spec (prisms, SDF with smin) is bigger than the drawn contour by construction, so no cost weight removes the
spill (30.L12-10a: every lever trades it 1:1 for bare). Here the volume is CUT by the visual hull of the sheet before the fit:

    carve(field, npz)      numpy only (it runs inside Blender, build_unit sdf_dense): field.grid = max(body sdf, hull sdf), the hull
                           being the max over the coherent front/left/back/top/bottom views of the signed distance (px / scale) of the
                           panel's mask eroded `erode` px, along the view's ray. The gate frames the model by its bbox, so the cut
                           is iterated until the bbox stops moving: the frame of each pass is the bbox of the previous pass's cut
                           body (+ the props' points). The fixed point is the largest body inside every mask under its own frame:
                           when the views disagree with the body it is much smaller than the body (bare is the price of spill 0).
    build_args(...)        python3.14 side of carve: the masks' signed distances, their axes and the mirror the gate picks (read on an
                           uncut build of the same spec: one more Blender build) as an npz
    clamp / apply(...)     after deform + vertex fit (which push vertices out again): every vertex in red goes to the nearest
                           pixel of the eroded mask, in the view plane (the ray is kept); `--inscribe on` = cut + clamp.

A view the sheet contradicts (sheet_report 'incoherent') never cuts. A top/bottom cuts only when its camera is pinned (--tilts, or the
run's silhouette.json). Props: the clamp holds a prop component to its own mask when the view has prop masks, else leaves it
(the spear is not destroyed); the cut never touches them (they are not in the body's field)."""
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

ERODE_PX = 1            # the hull is the mask eroded this many canvas px (negative: dilated; the gate's own raster reads up to 1 px other than ours)
PAD = 64                # px of signed distance kept around the canvas: a voxel outside the canvas still knows how far it is
PASSES = 14             # frame/cut passes of carve (the bbox of the cut body is the next frame); n017 and n00U need all of them
SETTLED = 0.05          # ... stop when the bbox moved less than this many voxels
VIEWS = ("front", "left", "back", "top", "bottom")
PROP_OWN = 0.3          # a component is a prop's when this share of its vertices lies in the prop's mask (deform_to_sheet.PROP_OWN)
PULL = 10.0             # clamp: weight of a red vertex's target against the smoothness of the mesh (deform_to_sheet.PULL)
FOLLOW = 0.5            # ... weight of "stay where you are" for the rest: the neighbours follow over a few rings
IOU_SLIP = 0.004        # ... a round may not take more than this from a view's IoU (noise.py's floor is max(2 sigma, .005))
ROUNDS = 5              # clamp: rounds over the views (a move in one view shifts the others)


# ---------------------------------------------------------------- numpy only: runs in Blender's Python
def bilinear(img, x, y):
    """img sampled at pixel-corner canvas coordinates (pixel i covers [i, i + 1), its centre is i + .5); clamped at the border."""
    x, y = np.clip(x - 0.5, 0, img.shape[1] - 1.001), np.clip(y - 0.5, 0, img.shape[0] - 1.001)
    x0, y0 = x.astype(int), y.astype(int)
    fx, fy = x - x0, y - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


def frame_of(uv, mirror, canvas):
    """(lo, hi, scale, x0, y0) of deform_to_sheet.frame: the points' bbox fitted to the canvas, centred."""
    uv = uv * np.array([mirror, 1.0])
    lo, hi = uv.min(0), uv.max(0)
    w, h = hi - lo
    s = canvas[0] / h
    if w * s > canvas[1]:
        s = canvas[1] / w
    return lo, hi, s, (canvas[1] - w * s) / 2, (canvas[0] - h * s) / 2


def to_canvas(u, v, fr, mirror):
    lo, hi, s, x0, y0 = fr
    return (u * mirror - lo[0]) * s + x0, (hi[1] - v) * s + y0


def surface(grid, origin, voxel):
    """(N, 3) points of the zero set: the linear zero crossing of every grid edge whose ends differ in sign. The frame of a view is the
    bbox of these, to a fraction of a voxel (the centres of the voxels in would be off by up to half of one)."""
    out = []
    for a in range(3):
        g = np.moveaxis(grid, a, 0)
        lo, hi = g[:-1], g[1:]
        sel = (lo < 0) != (hi < 0)
        idx = np.argwhere(sel).astype(float)
        idx[:, 0] += lo[sel] / (lo[sel] - hi[sel])
        pts = np.empty_like(idx)
        pts[:, a] = idx[:, 0]
        pts[:, [b for b in range(3) if b != a]] = idx[:, 1:]
        out.append(pts)
    return origin + voxel * np.vstack(out)


def hull_grid(field_axes, views, chosen, solid, extra, meta):
    """Max over the views of the signed distance (world units, positive outside) of the eroded mask, at every voxel centre; the
    frame of each view is the bbox of `solid` (the body's surface points) and `extra`."""
    canvas = tuple(meta["canvas"])
    X, Y, Z = field_axes
    out = None
    for name, (i, m) in chosen.items():
        view, axes = views[name], views[name]["axes"][i]
        framing = solid if meta["framed"][name] or not len(extra) else np.vstack([solid, extra])
        uv = np.stack([framing @ axes[0], framing @ axes[1]], 1)
        fr = frame_of(uv, m, canvas)
        u = X[:, None, None] * axes[0][0] + Y[None, :, None] * axes[0][1] + Z[None, None, :] * axes[0][2]
        v = X[:, None, None] * axes[1][0] + Y[None, :, None] * axes[1][1] + Z[None, None, :] * axes[1][2]
        cx, cy = to_canvas(u, v, fr, m)
        h = bilinear(view["sd"][i], (cx + PAD).ravel(), (cy + PAD).ravel()).reshape(u.shape) / fr[2]
        out = h if out is None else np.maximum(out, h)
    return out


def load_views(path):
    """(meta, {view: {axes, masks, sd, mirror}}, extra points) of a write_views() npz."""
    z = np.load(path, allow_pickle=False)
    meta = json.loads(str(z["meta"]))
    return meta, {v: {k: z[f"{v}__{k}"] for k in ("axes", "masks", "sd", "mirror")} for v in meta["views"]}, z["extra"]


def carve(field, path):
    """field.grid = max(field.grid, hull) (the intersection of the body with the visual hull), in place; returns a report."""
    meta, views, extra = load_views(path)
    margin = field.margin
    axes = [field.origin[a] + field.voxel * np.arange(field.shape[a]) for a in range(3)]
    chosen = {n: (0, int(v["mirror"])) for n, v in views.items()}
    skin = surface(field.grid, field.origin, field.voxel)
    report = {"views": list(views), "passes": 0, "voxels_before": int((field.grid < 0).sum())}
    cut = None
    for _ in range(PASSES):
        cut = np.maximum(field.grid, hull_grid(axes, views, chosen, skin, extra, meta))
        report["passes"] += 1
        if not (cut < 0).any():
            break
        now = surface(cut, field.origin, field.voxel)
        moved = np.abs(np.ptp(now, axis=0) - np.ptp(skin, axis=0)).max()
        skin = now
        if moved < SETTLED * field.voxel:
            break
    if cut is not None and (cut < 0).any():
        field.grid = np.minimum(cut, margin).astype(field.grid.dtype)
    report["voxels_after"] = int((field.grid < 0).sum())
    return report


# ---------------------------------------------------------------- python3.14 side (scipy, PIL, silhouette, deform_to_sheet)
def eroded(mask, erode_px):
    """`mask` eroded erode_px canvas px (dilated when negative). The canvas border is not an edge: the figure is framed to touch it."""
    from scipy import ndimage
    if erode_px < 0:
        return ndimage.binary_dilation(mask, iterations=-erode_px)
    return ndimage.binary_erosion(mask, iterations=erode_px, border_value=1) if erode_px else mask


def signed(mask, erode_px):
    """Signed distance (px, positive outside) of `mask` eroded erode_px, padded PAD px; None when the erosion leaves nothing. The padding
    repeats the canvas border."""
    from scipy import ndimage
    inner = eroded(mask, erode_px)
    if not inner.any():
        return None
    inner = np.pad(inner, PAD, mode="edge")
    return (ndimage.distance_transform_edt(~inner) - ndimage.distance_transform_edt(inner)).astype(np.float32)


def cutting_views(panels, rep, cams):
    """Names of the views that cut: drawn, coherent (not in rep['incoherent']), and with a camera when tilted (top/bottom)."""
    bad = set((rep or {}).get("incoherent", ()))
    return [n for n in VIEWS if n in panels and n not in bad and (n in ("front", "left", "back") or (cams or {}).get(n) is not None)]


def prop_points(rows):
    """(M, 3) corners of the boxes of every piece of the spec rows that are not body (props, the flame slit): they frame the model
    in the gate though the body's field does not hold them."""
    import sdf_body as SB
    pts = []
    for row in rows:
        if SB.is_body(row):
            continue
        row = (row[0], row[1], tuple(row[2]), tuple(row[3]), row[4], row[5] or {})
        for q in SB.part_pieces(row, None)[0]:
            lo, hi = q["lo"], q["hi"]
            pts += [[a, b, c] for a in (lo[0], hi[0]) for b in (lo[1], hi[1]) for c in (lo[2], hi[2])]
    return np.array(pts, float).reshape(-1, 3)


def write_views(path, options, rows, erode_px=ERODE_PX, framed=None, mirrors=None):
    """Write the npz carve() reads: options {view: (axes (2, 3), concept mask)}, mirrors {view: 1 | -1} (default 1). Returns the views
    kept (an erosion that empties a mask drops its view)."""
    import silhouette as S
    meta = {"erode": erode_px, "canvas": [S.CANVAS_H, S.CANVAS_W], "views": [], "framed": {}}
    arrays = {}
    for name, (axes, concept) in options.items():
        sd = signed(concept, erode_px)
        if sd is None:
            continue
        meta["views"].append(name)
        meta["framed"][name] = bool((framed or {}).get(name))
        arrays |= {f"{name}__axes": np.array([axes]), f"{name}__masks": np.array([concept], bool), f"{name}__sd": np.array([sd]),
                   f"{name}__mirror": np.array((mirrors or {}).get(name, 1))}
    np.savez_compressed(path, meta=json.dumps(meta), extra=prop_points(rows), **arrays)
    return meta["views"]


def chosen_views(args, uncut):
    """({view: (axes, concept)}, {view: mirror}, {view: framed}) of the views that cut, as the gate picks them on the glb `uncut` (mirror,
    the top/bottom's turn, camera: deform_to_sheet.make_views, the code the deformation and the vertex fit use)."""
    import deform_to_sheet as D
    import silhouette as S
    from views import layout_of
    panels = S.framed_panels(pathlib.Path(args.sheet), layout=layout_of(args.kind))
    cams = D.run_cams(args)
    pos, tri = D.welded_mesh(uncut)
    made = D.make_views(pos, tri, {n: panels[n] for n in cutting_views(panels, S.run_report(args), cams)}, (), None, cams)
    return ({v.name: (np.array([v.ru, v.rv]), v.concept) for v in made}, {v.name: v.mirror for v in made},
            {v.name: getattr(panels[v.name], "box", None) is not None for v in made})


def build_args(spec, args, work, uncut):
    """build_unit.py arguments of the cut: ['inscribe=<npz>'] when --inscribe is cut|on and some view cuts, else []. `uncut`: the glb of
    the same spec built without the cut (where the gate's mirrors are read)."""
    if getattr(args, "inscribe", "off") == "off":
        return []
    path = pathlib.Path(work) / "inscribe.npz"
    options, mirrors, framed = chosen_views(args, uncut)
    kept = write_views(path, options, spec["parts"], args.inscribe_erode, framed, mirrors)
    return [f"inscribe={path}"] if kept else []


def regions(view, px, owner, body):
    """{key: (vertex mask, mask the vertices must stay in)}: the body against the view's whole mask, each prop component against the
    prop mask most of its vertices lie in (D.PROP_OWN); a component with no such mask is left out (the spear stays)."""
    out = {0: (owner == body, view.concept)}
    for c in set(owner[owner != body].tolist()) if view.props else ():
        mine = owner == c
        hits = [m[px[mine, 1], px[mine, 0]].mean() for m in view.props]
        if max(hits) >= PROP_OWN:
            out[c + 1] = (mine, view.props[int(np.argmax(hits))])
    return out


def pull_red(cur, views, erode_px, owner, body, ground):
    """(displacement (N, 3), vertices that asked for it): each vertex outside a view's mask (eroded erode_px) goes, in that view's
    plane, to the nearest pixel of it; the body against the whole mask, a prop component against its own mask (none: left alone)."""
    from scipy import ndimage
    import deform_to_sheet as D
    step, red_any = np.zeros_like(cur), np.zeros(len(cur), bool)
    for view in views:
        uv = view.uv(cur)
        to_px, s = D.frame(uv, view.mirror, view.frame_on)
        xy = to_px(uv)
        px = D.pixels(xy, view.concept.shape)
        for mine, mask in regions(view, px, owner, body).values():
            region = eroded(mask, erode_px)
            red = mine & ~region[px[:, 1], px[:, 0]] if region.any() else np.zeros(len(cur), bool)
            if not red.any():
                continue
            iy, ix = ndimage.distance_transform_edt(~region, return_indices=True)[1]
            goal = np.stack([ix[px[red, 1], px[red, 0]], iy[px[red, 1], px[red, 0]]], 1) + 0.5
            d = (goal - xy[red]) * np.array([view.mirror, -1.0]) / s
            step[red] += d[:, :1] * view.ru + d[:, 1:] * view.rv
            red_any |= red
    step[ground, 2] = 0.0
    return step, red_any


def better(before, after):
    """The gate's own numbers of a round: the mean spill falls and no view loses more than IOU_SLIP of IoU."""
    spill = lambda m: np.mean([r["spill"] for r in m.values()])  # noqa: E731
    return spill(after) < spill(before) - 1e-4 and all(after[v]["iou"] >= before[v]["iou"] - IOU_SLIP for v in before)


def clamp(pos, tri, nor, views, erode_px=ERODE_PX, rounds=ROUNDS):
    """(new welded Z-up positions, report): rounds over `views` (D.View list), one view at a time (a vertex moved in one plane moves in
    the others: all at once the top view cost the front 5 points of IoU): its red vertices go to the mask, the rest of the mesh follows
    through the uniform Laplacian (deform_to_sheet.solve); the step is damped (D.DAMP) until `better` accepts it, else the view is
    skipped; a move that turns a face is pulled back (D.untangle). Ends when a round accepts nothing."""
    import deform_to_sheet as D
    owner, body = D.owner_body(tri, len(pos))
    ref = D.reference(pos, tri, nor)
    ground = pos[:, 2] < pos[:, 2].min() + D.SOLE * float(np.ptp(pos[:, 2]))
    lap = D.laplacian(tri, len(pos))
    cur, report = pos, {"red_vertices": [], "accepted": 0, "refused": 0}
    for _ in range(rounds):
        taken = 0
        for view in views:
            step, red = pull_red(cur, [view], erode_px, owner, body, ground)
            if not red.any():
                continue
            move = D.solve(lap, step, PULL * red, FOLLOW + 1e-3)
            move[ground, 2] = 0.0
            before = D.measure(cur, tri, views)
            best = next((t for t in (D.untangle(ref, cur, cur + k * move, tri) for k in D.DAMP) if better(before, D.measure(t, tri, views))), None)
            report["red_vertices"].append([view.name, int(red.sum())])
            report["refused" if best is None else "accepted"] += 1
            cur, taken = (cur, taken) if best is None else (best, taken + 1)
        if not taken:
            break
    return cur, {**report, "turned": int(D.turned(ref, cur, tri).sum())}


def apply(glb, args):
    """spec_pipeline hook, after optimize_verts.apply; prints its own lines. --inscribe cut|on: the carve's report (build_unit wrote
    inscribe.carve.json beside the npz); on: the vertices that stand outside the eroded masks are pulled back in (clamp), keeping the
    input as <stem>-preinscribe.glb; <stem>.inscribe.json holds the clamp's report with the gate-like numbers before / after. Returns the
    clamp's report, None when there was none."""
    if getattr(args, "inscribe", "off") == "off":
        return None
    carved = pathlib.Path(args.out) / "inscribe.carve.json"
    if carved.exists():
        c = json.loads(carved.read_text())
        print(f"inscribe cut: {', '.join(c['views'])}; {c['passes']} passes; body voxels {c['voxels_before']} -> {c['voxels_after']} ({c['voxels_after'] / c['voxels_before']:.2f})")
    if args.inscribe != "on" or not getattr(args, "union_body", False):
        return None
    import deform_to_sheet as D
    import silhouette as S
    from views import layout_of
    glb = pathlib.Path(glb)
    before = glb.with_name(f"{glb.stem}-preinscribe.glb")
    before.write_bytes(glb.read_bytes())
    layout, cams = layout_of(args.kind), D.run_cams(args)
    panels = D.sheet_panels(args.sheet, VIEWS, layout)
    names = cutting_views(panels, S.run_report(args), cams)
    props = {v: S.prop_masks(args.sheet, v, layout, panels) for v in names}
    pick = lambda pos, tri: D.make_views(pos, tri, {n: panels[n] for n in names}, (), props, cams)  # noqa: E731

    def change(pos, tri, nor, _file):
        views = pick(pos, tri)
        new, report = clamp(pos, tri, nor, views, args.inscribe_erode)
        return new, report | {"views": names, "before": D.measure(pos, tri, views), "after": D.measure(new, tri, pick(new, tri))}
    report = D.rewrite(before, glb, change, suffix=".inscribe.json")
    print(line(report))
    return report


def line(report):
    """One log line of a clamp report."""
    cut = lambda k: " ".join(f"{v} {r['spill']:.3f}" for v, r in report[k].items())  # noqa: E731
    return f"inscribe clamp: {report['accepted']} view steps accepted, {report['refused']} refused, turned {report['turned']}; spill before {cut('before')} -> after {cut('after')}"
