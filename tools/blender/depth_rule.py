#!/usr/bin/env python3
"""Depth from the art: a ruler (`z_err`), a relief check (`relief_agreement`) and z from the top panel (PIPELINE 30.L12-8).

    python3.14 tools/blender/depth_rule.py measure <run dir> --id n005 [--glb clay.glb]
    python3.14 tools/blender/depth_rule.py boxes <id> --run <run dir>        # parts.json: box3d re-triangulated, no VLM call

`z_err`: 8-12 landmarks per sheet (the joints both the front and the left panel show, the centre of the head / face / torso /
pelvis / prop boxes both show), triangulated front x left (exact: those panels are drawn straight). Each one is checked in a
third view, the top panel, through the camera the gate pins (`views.camera`: the panel is drawn tilted, so a point at height y
moves by y * sin(tilt) in the panel's rows; a pure orthographic reading, tilt 0, puts it y * tan(tilt) away): the front x left
hull of the sheet is projected into the top panel and fitted to it (`fit_top`), a landmark farther than RESID_MAX * H from the
panel's figure (or whose two views disagree on its height by more) is dropped and counted. `z_err` = mean |z of the clay at the
landmark - triangulated z| / H over the kept ones (the clay's z = the centre of the solid its (x, y) ray crosses nearest the
triangulated z), reported as `n_used / n_total`.

`relief_agreement`: the clay's z-pass (a z-buffer in the gate's camera, front / left / back) -> its depth steps (neighbour pixels
more than STEP_MIN * H apart in depth, away from the silhouette) against the ink inside the sheet-hard's drawing (`silhouette.edges`),
precision / recall at SLACK px of the gate's canvas, as look.py's crease_chamfer. A CHECK, not a gate.

z for a part one panel shows (`complete_boxes`): the front x left x top hull of the sheet (a voxel is kept when its projection in the
tilted top panel lands on the figure) minus the boxes of the other parts gives the missing range; the part says why when it stays null.
"""
import argparse
import json
import pathlib
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import deform_to_sheet as D  # noqa: E402
import silhouette as S  # noqa: E402
from views import layout_of  # noqa: E402

RESID_MAX = 0.04       # H: a landmark whose views disagree by more (height gap, distance to the top panel's figure) is dropped
STEP_MIN = 0.02        # H: neighbouring pixels of the z-pass this far apart in depth are a step
SLACK = 4              # canvas px: a step and an ink line this close agree (look.SLACK)
HULL_N = 90            # voxels along H
MIN_VOX = 12           # voxels a z (or x) range is read from
FREE_MIN = 0.5         # share of the hull voxels in a part's window that no other part's box holds: under it the window is the body's, not the part's
THICK_MAX = 0.6        # the range read for the missing axis may be this many times the largest extent the panel gave; above it the hull is an envelope, not the part
TOP_IOU_MIN = 0.5      # a top panel the hull fits worse than this is not a view of that figure: no z from it
BODY_ROLES = ("head", "face", "torso", "pelvis")
SURFACE_JOINTS = ("chin", "snout")
RAY_OFFSETS = (0.0, -0.01, 0.01, -0.02, 0.02, -0.03, 0.03)   # H: a landmark on the surface (head_top) is looked for just under it
DZ_MIN = 0.05          # H: a spec part whose z centre is this close to its semantic part's triangulated box stays where it is
DZ_MAX = 0.25          # H: ... and moves at most this much along z
VIEWS = ("front", "left", "back")


# ---- the tilted camera

def spec_of(zup):
    """Z-up camera frame (x, Y, Z) -> spec metres (x, y up, z forward): forward is -Y."""
    zup = np.asarray(zup, float)
    return np.stack([zup[..., 0], zup[..., 2], -zup[..., 1]], -1)


def zup_of(spec):
    spec = np.asarray(spec, float)
    return np.stack([spec[..., 0], -spec[..., 2], spec[..., 1]], -1)


def project(points, name, cam):
    """(u, v) of spec-metre points in the view `name` at camera `cam` (a tilt for top/bottom): the image axes of the gate's camera."""
    ru, rv = D.view_axes(name, cam)
    p = zup_of(points)
    return p @ ru, p @ rv


def z_from_view(u, v, x, y, name, cam):
    """z forward of the point whose x and y the front panel gave and whose row v the tilted `name` panel gave: the row is
    v = x rv_x - z rv_y + y rv_z, the tilt shows in rv_y = cos(tilt), rv_z = sin(tilt)."""
    _, rv = D.view_axes(name, cam)
    return (x * rv[0] + y * rv[2] - v) / rv[1]


# ---- the sheet's hull and the top panel

def hull_points(front_has, left_has, extent, H, n=HULL_N):
    """(N, 3) spec-metre centres of the voxels the front and left panels both contain. `front_has(x, y)` and `left_has(z, y)` take
    broadcast arrays and return bool; extent = ((x0, x1), (z0, z1)); the grid is H / n voxels."""
    h = H / n
    ys = (np.arange(n) + 0.5) * h
    xs = np.arange(extent[0][0], extent[0][1], h) + h / 2
    zs = np.arange(extent[1][0], extent[1][1], h) + h / 2
    f = front_has(xs[:, None], ys[None, :])                       # [x, y]
    lf = left_has(zs[:, None], ys[None, :])                       # [z, y]
    ix, iy, iz = np.nonzero(f[:, :, None] & lf.T[None, :, :])
    return np.stack([xs[ix], ys[iy], zs[iz]], 1)


class TopFrame:
    """Metric (u, v) of the top camera <-> pixel of the sheet's top panel: px = cx + su s (u - u0), py = cy - sv s (v - v0);
    (su, sv) = (-1, -1) is the panel drawn turned 180 degrees, (-1, 1) mirrored. `iou` is the fit's score."""

    def __init__(self, ru, rv, su, sv, s, centre, origin, iou):
        self.ru, self.rv, self.su, self.sv, self.s, self.c, self.o, self.iou = ru, rv, su, sv, s, centre, origin, iou

    def px(self, points):
        p = zup_of(points)
        return np.stack([self.c[0] + self.su * self.s * (p @ self.ru - self.o[0]), self.c[1] - self.sv * self.s * (p @ self.rv - self.o[1])], 1)


def splat(xy, shape, step):
    """Boolean image (1/step of full res) of the points, closed to a solid blob."""
    ij = np.round(xy / step).astype(int)
    h, w = shape[0] // step, shape[1] // step
    ok = (ij[:, 0] >= 0) & (ij[:, 0] < w) & (ij[:, 1] >= 0) & (ij[:, 1] < h)
    img = np.zeros((h, w), bool)
    img[ij[ok, 1], ij[ok, 0]] = True
    return ndimage.binary_closing(ndimage.binary_dilation(img), iterations=1)


def score(img, target):
    return float((img & target).sum() / max((img | target).sum(), 1))


def fit_top(points, panel, cam, flip=None, step=3):
    """TopFrame of the top panel (bool, full-res) for the hull `points` seen at the tilt `cam`: scale from the figure's width, shifts and
    scale refined by IoU, over the four ways the panel can be drawn (flip: None = all four, True = turned 180, False = as drawn,
    mirrored or not). The hull holds the whole silhouette and more, so this is a fit, not an identity."""
    ru, rv = D.view_axes("top", cam)
    p = zup_of(points)
    u, v = p @ ru, p @ rv
    ys, xs = np.nonzero(panel)
    pc = np.array([(xs.min() + xs.max() + 1) / 2, (ys.min() + ys.max() + 1) / 2])
    pw, ph = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
    o = np.array([(u.min() + u.max()) / 2, (v.min() + v.max()) / 2])
    s0 = np.sqrt(pw / max(np.ptp(u), 1e-6) * ph / max(np.ptp(v), 1e-6))
    target = splat(np.stack(np.nonzero(panel)[::-1], 1).astype(float), panel.shape, step)
    sub = np.arange(0, len(u), max(len(u) // 20000, 1))
    options = {None: [(1, 1), (-1, 1), (-1, -1), (1, -1)], False: [(1, 1), (-1, 1)], True: [(-1, -1), (1, -1)]}[flip]
    best = None
    for su, sv in options:
        for k in (0.94, 0.97, 1.0, 1.03, 1.06):
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    s, c = s0 * k, pc + np.array([dx, dy]) * 0.02 * ph
                    xy = np.stack([c[0] + su * s * (u[sub] - o[0]), c[1] - sv * s * (v[sub] - o[1])], 1)
                    sc = score(splat(xy, panel.shape, step), target)
                    if best is None or sc > best[0]:
                        best = (sc, su, sv, s, c)
    sc, su, sv, s, c = best
    return TopFrame(ru, rv, su, sv, s, c, o, round(sc, 4))


def top_inside(frame, points, panel, grow=2):
    """Bool per point: its projection falls on the top panel's figure (grown by `grow` px)."""
    xy = np.round(frame.px(points)).astype(int)
    fig = ndimage.binary_dilation(panel, iterations=grow) if grow else panel
    ok = (xy[:, 0] >= 0) & (xy[:, 0] < panel.shape[1]) & (xy[:, 1] >= 0) & (xy[:, 1] < panel.shape[0])
    out = np.zeros(len(points), bool)
    out[ok] = fig[xy[ok, 1], xy[ok, 0]]
    return out


def top_distance(frame, points, panel, H):
    """Distance in H of each point's top projection to the top panel's figure (0 inside)."""
    dist = ndimage.distance_transform_edt(~panel)
    xy = np.clip(np.round(frame.px(points)).astype(int), 0, np.array(panel.shape[::-1]) - 1)
    return dist[xy[:, 1], xy[:, 0]] / (frame.s * H)


# ---- landmarks and z_err

def landmarks(doc, frames):
    """[{name, xyz, gap, face?}] triangulated front x left: the joints both panels show (not a mirrored .R) and the centre of the head /
    torso / pelvis / prop boxes both show. gap = how far apart (in H) the two views put its height. The points on a surface (a chin, a
    snout, a face plate: SURFACE_JOINTS, role face) carry `face` = their z range, the clay is asked for its front surface there."""
    out = []
    for name, j in doc["joints"].items():
        if j["front"] and j["left"]:
            fx, lz = frames.front_xy(*j["front"]), frames.left_zy(*j["left"])
            m = {"name": name, "xyz": [fx[0], (fx[1] + lz[1]) / 2, lz[0]], "gap": abs(fx[1] - lz[1]) / frames.H, "front_uv": j["front"]}
            out.append({**m, "face": [lz[0], lz[0]]} if name in SURFACE_JOINTS else m)
    for p in doc["parts"]:
        b = p["box2d"]
        if "front" in b and "left" in b and (p["role"] in BODY_ROLES or p.get("prop")):
            c = [((b[v][0] + b[v][2]) / 2, (b[v][1] + b[v][3]) / 2) for v in ("front", "left")]
            fx, lz = frames.front_xy(*c[0]), frames.left_zy(*c[1])
            m = {"name": "part:" + p["name"], "xyz": [fx[0], (fx[1] + lz[1]) / 2, lz[0]], "gap": abs(fx[1] - lz[1]) / frames.H, "front_uv": c[0]}
            if p["role"] == "face":
                za, zb = sorted((frames.left_zy(b["left"][0], b["left"][1])[0], frames.left_zy(b["left"][2], b["left"][3])[0]))
                m["face"] = [za, zb]
            out.append(m)
    return out


def ray_z(pos, tri, x, y):
    """Sorted z of every crossing of the triangles (spec metres) by the line along z through (x, y)."""
    a, b, c = pos[tri[:, 0]], pos[tri[:, 1]], pos[tri[:, 2]]
    d = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1])
    ok = np.abs(d) > 1e-12
    d = np.where(ok, d, 1.0)
    l1 = ((b[:, 1] - c[:, 1]) * (x - c[:, 0]) + (c[:, 0] - b[:, 0]) * (y - c[:, 1])) / d
    l2 = ((c[:, 1] - a[:, 1]) * (x - c[:, 0]) + (a[:, 0] - c[:, 0]) * (y - c[:, 1])) / d
    inside = ok & (l1 >= 0) & (l2 >= 0) & (l1 + l2 <= 1)
    return np.sort(l1[inside] * a[inside, 2] + l2[inside] * b[inside, 2] + (1 - l1[inside] - l2[inside]) * c[inside, 2])


def solid_centres(z):
    """Centres of the solids a ray crosses: consecutive pairs of crossings (entry, exit); an odd count falls back to the span."""
    z = z[np.concatenate([[True], np.diff(z) > 1e-6])] if len(z) else z      # a ray through the edge two triangles share crosses it twice
    if len(z) < 2:
        return []
    return [(z[i] + z[i + 1]) / 2 for i in range(0, len(z) - 1, 2)] if len(z) % 2 == 0 else [(z[0] + z[-1]) / 2]


def clay_solids(pos, tri, xyz, H, face=False):
    """Centres of the solids the clay has along the line through the landmark's (x, y), trying the heights RAY_OFFSETS in turn (a landmark on
    the surface, head_top, is looked for just under it); [] when the line crosses nothing. `face`: the front-most crossing instead."""
    for dy in RAY_OFFSETS:
        z = ray_z(pos, tri, xyz[0], xyz[1] + dy * H)
        if len(z):
            return [float(z[-1])] if face else solid_centres(z)
    return []


def z_target(mark, sign):
    """The z a mark asks of the clay for a given sign of z: its triangulated z, or (a face) the front of its box."""
    face = mark.get("face")
    if face is None:
        return sign * mark["xyz"][2]
    return face[1] if sign > 0 else -face[0]


def z_error(marks, pos, tri, H):
    """{z_err, z_sign, n_used, n_total, dropped, miss, marks[]}: `marks` already carry `resid`; a mark above RESID_MAX is dropped, one the clay
    does not cross is a miss, the rest are averaged. The clay's z is the centre of the solid nearest the triangulated z (a `face` mark: the
    clay's front surface against the front of the face's box). `z_sign`: the side panel's facing is a heuristic (massing.side_of: the toe
    row; a quadruped's paws or a spider have none), so the error is read with the sign of z that suits the clay better (-1: the sheet's z
    points the other way); a model facing the wrong way is the gate's business."""
    solids = [clay_solids(pos, tri, m["xyz"], H, "face" in m) for m in marks]
    keep = [m["resid"] <= RESID_MAX for m in marks]
    use = [i for i, k in enumerate(keep) if k and solids[i]]

    def errs(sign):
        return [min(abs(c - z_target(marks[i], sign)) for c in solids[i]) / H for i in use]

    sign = min((1, -1), key=lambda g: np.mean(errs(g)) if use else 0.0)
    e = dict(zip(use, errs(sign)))
    rows = [{"name": m["name"], "xyz": [round(v, 3) for v in m["xyz"]], "resid": round(m["resid"], 3),
             **({"err": round(e[i], 3)} if i in e else {}), **({} if keep[i] else {"dropped": True}), **({} if solids[i] else {"miss": True})}
            for i, m in enumerate(marks)]
    return {"z_err": round(float(np.mean(list(e.values()))), 4) if e else None, "z_sign": sign, "n_used": len(e), "n_total": len(marks),
            "dropped": keep.count(False), "miss": sum(1 for i, k in enumerate(keep) if k and not solids[i]), "marks": rows}


def residuals(marks, frame, panel, H):
    """Each mark's `resid` = max(its two views' height gap, its distance to the top panel's figure) in H; the gap only without a frame."""
    if frame is None or frame.iou < TOP_IOU_MIN:
        return [{**m, "resid": m["gap"]} for m in marks]
    d = top_distance(frame, np.array([m["xyz"] for m in marks]), panel, H) if marks else []
    return [{**m, "resid": float(max(m["gap"], dist))} for m, dist in zip(marks, d)]


# ---- z of the spec's parts from the triangulated boxes

def tri_shifts(centres, assoc, parts_doc, height):
    """{spec part index: dz in metres (forward)} for the spec parts whose z centre lies farther than DZ_MIN * H outside the z range of the
    box3d of the semantic part they are (parts_fit.associate): the centre goes to the nearest point of the box's middle half. Only
    boxes from front x left count (not the twin's z of a hidden .R part: n02X holds its club behind and the other arm forward, and a
    mirrored box would put the club's arm in front), and not a part whose two views disagree on its height (the doc's `incoherent`);
    capped at DZ_MAX * H. A part inside the range stays: the box is the part's envelope, a detail on it is not out of place.
    The spec's centres are (right, up, forward)."""
    scale = height / float(parts_doc.get("H") or height)
    bad = {b["part"] for b in parts_doc.get("incoherent", ()) if "part" in b}
    out = {}
    for i, a in enumerate(assoc):
        part = parts_doc["parts"][a] if a is not None else None
        if not part or not part.get("box3d") or part.get("z_from") or part["name"] in bad:
            continue
        lo, hi = part["box3d"][0][2] * scale, part["box3d"][1][2] * scale
        z = centres[i][2]
        if lo - DZ_MIN * height <= z <= hi + DZ_MIN * height:
            continue
        dz = float(np.clip(z, lo + 0.25 * (hi - lo), hi - 0.25 * (hi - lo))) - z
        out[i] = float(np.clip(dz, -DZ_MAX * height, DZ_MAX * height))
    return out


# ---- relief_agreement

def zbuffer(xy, nearness, tri, shape):
    """Per pixel the largest `nearness` of the triangles over it (-inf where none): xy canvas coordinates of the vertices (pixel
    centres at +0.5), nearness the distance toward the camera."""
    zb = np.full(shape, -np.inf)
    for t in tri:
        p = xy[t]
        x0, y0 = np.maximum(np.floor(p.min(0) - 0.5).astype(int), 0)
        x1, y1 = np.minimum(np.ceil(p.max(0) + 0.5).astype(int) + 1, [shape[1], shape[0]])
        if x1 <= x0 or y1 <= y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        d = (p[1, 1] - p[2, 1]) * (p[0, 0] - p[2, 0]) + (p[2, 0] - p[1, 0]) * (p[0, 1] - p[2, 1])
        if abs(d) < 1e-12:
            continue
        l1 = ((p[1, 1] - p[2, 1]) * (gx - p[2, 0]) + (p[2, 0] - p[1, 0]) * (gy - p[2, 1])) / d
        l2 = ((p[2, 1] - p[0, 1]) * (gx - p[2, 0]) + (p[0, 0] - p[2, 0]) * (gy - p[2, 1])) / d
        l3 = 1 - l1 - l2
        inside = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
        z = l1 * nearness[t[0]] + l2 * nearness[t[1]] + l3 * nearness[t[2]]
        win = zb[y0:y1, x0:x1]
        upd = inside & (z > win)
        win[upd] = z[upd]
    return zb


def depth_steps(zb, scale, H, rim, step=STEP_MIN):
    """Bool canvas of the pixels with a neighbour more than step * H apart in depth (metres), both on the figure, and farther than `rim`
    px from its outline. `scale` canvas px per metre."""
    covered = np.isfinite(zb)
    z = np.where(covered, zb, 0.0)
    jump = np.zeros(zb.shape, bool)
    for axis in (0, 1):
        a, b = np.swapaxes(z, 0, axis), np.swapaxes(covered, 0, axis)
        far = (np.abs(np.diff(a, axis=0)) > step * H) & b[1:] & b[:-1]
        j = np.swapaxes(jump, 0, axis)
        j[1:] |= far
        j[:-1] |= far
    inner = ndimage.binary_erosion(covered, iterations=max(int(round(rim)), 1)) if covered.any() else covered
    return jump & inner


def agreement(steps, ink, slack=SLACK):
    """(precision, recall, n_steps, n_ink): the share of the steps within `slack` px of the ink and of the ink within `slack` px of a step."""
    if not (steps.any() and ink.any()):
        return 0.0, 0.0, int(steps.sum()), int(ink.sum())
    near_ink = ndimage.distance_transform_edt(~ink) <= slack
    near_step = ndimage.distance_transform_edt(~steps) <= slack
    return float(near_ink[steps].mean()), float(near_step[ink].mean()), int(steps.sum()), int(ink.sum())


def relief(pos_zup, tri, views, ink, H, rims):
    """{view: [P, R, n_steps, n_ink]} of the clay's z-pass in the gate's `views` (D.View) against the sheet-hard's `ink` {view: canvas};
    `rims` {view: px} of the outline margin the sheet's own edges drop (silhouette.EDGE_RIM at the canvas scale)."""
    out = {}
    for v in views:
        if v.name not in ink:
            continue
        uv = v.uv(pos_zup)
        to_canvas, s = D.frame(uv, v.mirror, v.frame_on)
        zb = zbuffer(to_canvas(uv), pos_zup @ np.cross(v.ru, v.rv), tri, (S.CANVAS_H, S.CANVAS_W))
        p, r, n, m = agreement(depth_steps(zb, s, H, rims.get(v.name, 2)), ink[v.name])
        out[v.name] = [round(p, 3), round(r, 3), n, m]
    return out


# ---- boxes of the parts a panel shows alone

def hull3(points, frame, panel):
    """The hull points whose top projection lands on the top panel's figure (the front x left x top visual hull)."""
    return points[top_inside(frame, points, panel)]


def inside_boxes(points, boxes, grow):
    ok = np.zeros(len(points), bool)
    for lo, hi in boxes:
        ok |= np.all((points >= np.array(lo) - grow) & (points <= np.array(hi) + grow), axis=1)
    return ok


def complete_box(window, hull, others, H, grow=0.02):
    """(box3d, why) of a part one panel shows. `window` {"x": (a, b) | None, "y": (a, b), "z": (a, b) | None}: the ranges that panel
    gave, None the axis it did not. The missing range is read from the hull voxels in the window, leaving out the voxels inside the
    other parts' boxes (`others`, [(lo, hi)]); `why` is None when the box is read, else the reason it stays null."""
    if len(hull) == 0:
        return None, "no-hull"
    keys = ("x", "y", "z")
    win = np.ones(len(hull), bool)
    for axis, k in enumerate(keys):
        if window[k] is not None:
            win &= (hull[:, axis] >= window[k][0]) & (hull[:, axis] <= window[k][1])
    free = hull[win & ~inside_boxes(hull, others, grow * H)]
    if win.sum() < MIN_VOX:
        return None, "no-hull"
    if len(free) < max(MIN_VOX, FREE_MIN * win.sum()):
        return None, "inside-other-parts"
    lo, hi = np.percentile(free, 2, axis=0), np.percentile(free, 98, axis=0)
    box = [[window[k][0] if window[k] is not None else float(lo[i]) for i, k in enumerate(keys)],
           [window[k][1] if window[k] is not None else float(hi[i]) for i, k in enumerate(keys)]]
    known = max(window[k][1] - window[k][0] for k in keys if window[k] is not None)
    if max(box[1][i] - box[0][i] for i, k in enumerate(keys) if window[k] is None) > THICK_MAX * known:
        return None, "envelope"
    return [[round(float(v), 3) for v in box[0]], [round(float(v), 3) for v in box[1]]], None


# ---- the sheet's frames and the report of a run

def sheet_hull(frames, n=HULL_N):
    """(N, 3) hull of the sheet's front x left panels in spec metres, with `frames` = segment_sheet.Frames."""
    fr, sd, H = frames.front, frames.side, frames.H
    top_f, top_l = frames.top["front"], frames.top["left"]
    mf, ml = frames.panels["front"], frames.panels["left"]

    def lookup(mask, px, py):
        ix, iy = np.floor(px).astype(int), np.floor(py).astype(int)
        ok = (ix >= 0) & (ix < mask.shape[1]) & (iy >= 0) & (iy < mask.shape[0])
        return ok & mask[np.clip(iy, 0, mask.shape[0] - 1), np.clip(ix, 0, mask.shape[1] - 1)]

    def front_has(x, y):
        return lookup(mf, fr.cx + x / fr.s, top_f + (H - y) / fr.s)

    def left_has(z, y):
        return lookup(ml, sd.zero + sd.sign * z / sd.v.s, top_l + (H - y) / sd.v.s)

    cols_f, cols_l = np.nonzero(mf.any(axis=0))[0], np.nonzero(ml.any(axis=0))[0]
    xs = sorted(((c - fr.cx) * fr.s for c in (cols_f.min(), cols_f.max() + 1)))
    zs = sorted(((c - sd.zero) * sd.v.s * sd.sign for c in (cols_l.min(), cols_l.max() + 1)))
    return hull_points(front_has, left_has, (tuple(xs), tuple(zs)), H, n)


def frames_for(sheet, doc):
    """segment_sheet.Frames of the sheet at the panel crops the VLM read (parts.json meta): the 2D answers are fractions of those images,
    and the crops of a sheet drift when the panel split changes."""
    import segment_sheet as SG
    frames = SG.Frames(sheet, doc["H"])
    frames.crop = {v: tuple(c) for v, c in doc["meta"]["panel_crop"].items()}
    return frames


def top_context(frames, cam, flip=None):
    """(hull points, TopFrame, top panel) of a sheet at the top tilt `cam`; the frame is None without a top panel."""
    points = sheet_hull(frames)
    panel = frames.panels.get("top")
    if panel is None or not panel.any():
        return points, None, None
    return points, fit_top(points, np.asarray(panel), cam, flip), np.asarray(panel)


def rims_of(hard, views, layout):
    """{view: px} of the margin silhouette.edges() leaves at the outline, at the canvas scale of each view."""
    panels = S.concept_panels(pathlib.Path(hard), layout=layout)
    out = {}
    for name in views:
        if name in panels:
            ys, xs = np.nonzero(panels[name])
            out[name] = S.EDGE_RIM * min(S.CANVAS_H / (np.ptp(ys) + 1), S.CANVAS_W / (np.ptp(xs) + 1))
    return out


def measure(glb, sheet, hard, parts, cams, kind="mass"):
    """{z_err, relief_agreement, top} of the clay `glb` against the sheet, `parts` the parts.json dict (None: no ruler), `cams` the gate's
    cameras ({"top": tilt, ...}; None: no top check). See the module doc."""
    import align_features as AF
    layout = layout_of(kind)
    pos, tri = D.welded_mesh(glb)
    out = {"H": parts["H"] if parts else None}
    if parts:
        frames = frames_for(sheet, parts)
        marks = landmarks(parts, frames)
        frame = panel = None
        if cams is not None:
            _, frame, panel = top_context(frames, cams.get("top", 0))
        out["top"] = None if frame is None else {"cam": cams.get("top", 0), "iou": frame.iou, "flip": [frame.su, frame.sv]}
        out["z_err"] = z_error(residuals(marks, frame, panel, parts["H"]), spec_of(pos), tri, parts["H"])
    if hard and pathlib.Path(hard).exists():
        views = [v for v in D.make_views(pos, tri, D.sheet_panels(sheet, D.SIX, layout), (), cams=cams) if v.name in VIEWS]
        H = float(np.ptp(pos[:, 2]))
        out["relief_agreement"] = relief(pos, tri, views, AF.hard_edges(hard, VIEWS, layout), H, rims_of(hard, VIEWS, layout))
    return out


def line(report):
    """One log line of a measure() report."""
    z = report.get("z_err")
    ra = " ".join(f"{v} {p:.2f}/{r:.2f}" for v, (p, r, *_) in report.get("relief_agreement", {}).items())
    zs = "z_err -" if not z or z["z_err"] is None else f"z_err {z['z_err']:.3f} H ({z['n_used']}/{z['n_total']} marks)"
    return f"depth: {zs}, relief P/R {ra or '-'}"


def row(glb):
    """review.md row of the depth report written beside `glb` (apply), "" when there is none."""
    path = pathlib.Path(glb).with_suffix(".depth.json") if glb else None
    return f"| depth | {line(json.loads(path.read_text()))[7:]} |\n" if path and path.exists() else ""


def apply(glb, args):
    """spec_pipeline hook, after look.apply: <stem>.depth.json = measure() of the clay against refs/<id>/parts.json and the sheet-hard.
    Report or None (a stub run with no sheet)."""
    sheet = getattr(args, "sheet", None)
    if not (sheet and pathlib.Path(sheet).exists()) or layout_of(getattr(args, "kind", "mass")) != "unit":
        return None
    sheet = pathlib.Path(sheet)
    path = sheet.with_name("parts.json")
    parts = json.loads(path.read_text()) if path.exists() else None
    try:
        report = measure(glb, sheet, getattr(args, "hard", None), parts, D.run_cams(args), getattr(args, "kind", "mass"))
    except (SystemExit, KeyError, ValueError, OSError) as err:      # a metric: a sheet it cannot read must not stop the run
        print(f"no-op: depth: {type(err).__name__}: {err}")
        return None
    pathlib.Path(glb).with_suffix(".depth.json").write_text(json.dumps(report, indent=1))
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("measure",))
    ap.add_argument("run")
    ap.add_argument("--id", required=True)
    ap.add_argument("--glb", default="clay.glb")
    ap.add_argument("--tilts", default=None, help="the gate's cameras (views.parse_tilts); default: the run's silhouette.json")
    a = ap.parse_args()
    run = pathlib.Path(a.run)
    refs = pathlib.Path(__file__).resolve().parents[2] / "artifacts/model-sheets/refs" / a.id
    args = argparse.Namespace(out=run, sheet=refs / "sheet.jpg", hard=refs / "sheet-hard.jpg", kind="mass", tilts=a.tilts or "")
    report = apply(run / a.glb, args)
    print(json.dumps(report, indent=1))
    print(line(report))


if __name__ == "__main__":
    main()
