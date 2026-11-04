#!/usr/bin/env python3
"""L20-0: the concept sheet projected onto the painted atlas (PIPELINE 39.L20-0; Hunyuan3D-Paint's MeshRender, arXiv 2501.12202, without the diffusion).

    eye_project.apply_stage(glb, unit, "on")                                  # --eye-project on: in place, after the paint, before the contour
    python3.14 tools/blender/eye_project.py variant --id hfoo --tag v20-proj-flat --mode flat [--from v19-default] [--k 2 --soft]
    python3.14 tools/blender/eye_project.py sheet hfoo                         # history/2026-10-31-l20/<unit>.png

No Blender and no model: the GLB's embedded atlas is swapped, UVs and mesh untouched. The sheet is delit discretely (a shared palette over the
five panels, every family's lightest tone is its albedo, its shadows are pulled to it, the ink stays); every texel of the atlas is a point
of the surface, seen by front, left, back, top, bottom and a right view that is the left panel mirrored, each with the review camera
(views.camera) registered to its panel by mask. A texel takes the mean of the views that see it, weight w_view * cos(n, v)^K, zero under
cos 75 degrees, behind other geometry, on the panel's or the model's eroded rim or on a depth edge. A texel no view sees keeps the procedural paint.
Mean: sRGB. Modes: on = delit, raw = the sheet as drawn, flat = delit and no ink line.
"""
import argparse
import json
import pathlib
import struct
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import eye_paint  # noqa: E402

ROOT = HERE.parents[1]
REFS = ROOT / "artifacts/model-sheets/refs"
DRAFT = ROOT / "artifacts/model-sheets/runs/draft"
HISTORY = ROOT / "artifacts/model-sheets/history/2026-10-31-l20"
MODES = ("on", "raw", "flat")
K = 4                       # the power of cos(n, v)
COS_MIN = float(np.cos(np.radians(75)))
VIEW_NAMES = ("front", "left", "back", "top", "bottom", "right")
INK_L, INK_GRAD = 0.40, 0.035       # OKLab L under this and an OKLab L gradient over this nearby: a drawn line
FAMILIES = 10               # colour families of the sheet (k-means on a, b and a little L)
L_WEIGHT = 0.35             # how much L counts in a family: a shadow stays with its lit tone
TONES = 3                   # tones of L inside a family
TONE_MIN = 0.15             # a tone under this share of its family is a highlight, not the albedo
SHADOW_KEPT = 0.2           # what stays of a tone's distance to the albedo
RIM = 0.012                 # erosion of the panel and model masks, share of the panel height
DEPTH_EPS = 0.012           # depth test tolerance, share of the model height
DEPTH_EDGE = 0.02           # a step of depth between neighbour pixels over this share of the height is a depth edge
SCALES = np.arange(0.88, 1.121, 0.03)   # the registration's scale sweep per axis, around the height-to-height scale
OWN_AB, OWN_L = 0.06, 0.15  # L20-2: a dominant colour further than this from the DSL colour of its piece (OKLab) is the neighbour's (hfoo hands and straps: L .21-.24); set by hand on 2 units
ACC_C, ACC_REL = 0.05, 1.6   # L20-2 accent: OKLab chroma of the DSL colour at least this and this times the palette's (texel-weighted median)
WORDS = {"red": (15, 35), "orange": (55, 20), "brass": (80, 25), "gold": (85, 25), "amber": (70, 25), "yellow": (100, 25), "green": (140, 40), "teal": (195, 30),
         "blue": (255, 35), "purple": (310, 35), "violet": (300, 30), "pink": (350, 25)}      # colour words of an identity line -> hue centre, half-width (OKLab degrees); open list
ACC_LEAK = 0.03             # L20-2: a projected colour this near (OKLab a, b) an accent colour does not go on a piece that is not that accent
TIGHT_GATE, TIGHT_PARTS = (0.04, 0.2), (0.03, 0.08, 0.5)   # L20-2: --eye-project tight, the author's choice over the two test units: gate_keep (ab, L), part filter (ab, L, share)
PART_MIN = 8               # L20-2: a piece with fewer covered texels than this has no dominant colour worth the name
FIT_N = 128                 # the registration's mask height, px
OK_M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566], [0.0883024619, 0.2817188376, 0.6299787005]])
OK_M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099], [0.0259040371, 0.7827717662, -0.8086757660]])


# ---------------------------------------------------------------- colour
def to_oklab(rgb):
    """(..., 3) sRGB 0..255 -> OKLab."""
    c = np.asarray(rgb, float) / 255
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return np.cbrt(lin @ OK_M1.T) @ OK_M2.T


def from_oklab(lab):
    """(..., 3) OKLab -> sRGB 0..255, clipped."""
    lin = (np.asarray(lab, float) @ np.linalg.inv(OK_M2).T) ** 3 @ np.linalg.inv(OK_M1).T
    lin = np.clip(lin, 0, 1)
    return 255 * np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * lin ** (1 / 2.4) - 0.055)


def grow(mask, r=1):
    """`mask` dilated by r pixels (4-neighbours)."""
    out = np.asarray(mask, bool).copy()
    for _ in range(r):
        p = np.pad(out, 1)
        out = p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    return out


def shrink(mask, r=1):
    """`mask` eroded by r pixels; the image's border counts as outside."""
    return ~grow(~np.asarray(mask, bool), r) & _inner(mask.shape, r)


def _inner(shape, r):
    out = np.zeros(shape, bool)
    out[r:shape[0] - r, r:shape[1] - r] = True
    return out


def contour_of(lab):
    """(h, w) bool: drawn lines, a dark pixel near a strong step of L (a dark plate's flat inside is no line)."""
    gy, gx = np.gradient(lab[..., 0])
    return (lab[..., 0] < INK_L) & grow(np.hypot(gx, gy) > INK_GRAD, 3)


def albedo_of(lab):
    """OKLab colour of a family's pixels (n, 3): the mean of its lightest tone that holds at least TONE_MIN of them."""
    L = lab[:, 0]
    centres = np.quantile(L, (np.arange(TONES) + 0.5) / TONES)
    for _ in range(8):
        tone = np.argmin(np.abs(L[:, None] - centres[None]), axis=1)
        centres = np.array([L[tone == t].mean() if (tone == t).any() else centres[t] for t in range(TONES)])
    for t in np.argsort(-centres):
        if (tone == t).mean() >= TONE_MIN:
            return lab[tone == t].mean(0)
    return lab.mean(0)


def remap(lab, albedo):
    """lab (n, 3) of one family pulled to its albedo: a shadow keeps SHADOW_KEPT of its distance, a lighter pixel stays."""
    dark = lab[:, 0] < albedo[0]
    out = lab.copy()
    out[dark] = albedo + SHADOW_KEPT * (lab[dark] - albedo)
    return out


def fill_lines(rgb, line, inside):
    """rgb with the `line` pixels replaced by their nearest non-line neighbours inside the figure."""
    out, todo = rgb.copy(), line.copy()
    known = inside & ~line
    while todo.any():
        total, count = np.zeros_like(out), np.zeros(known.shape)
        for axis, shift in ((0, 1), (0, -1), (1, 1), (1, -1)):
            ok = np.roll(known, shift, axis)
            total += np.roll(out, shift, axis) * ok[..., None]
            count += ok
        added = todo & (count > 0)
        if not added.any():
            break
        out[added] = total[added] / count[added][:, None]
        known, todo = known | added, todo & ~added
    return out


def delight(panels):
    """{view: {rgb, mask}} -> {view: {raw, on, flat, line}} and the palette's report. The families are shared by the panels: one coat has one albedo in every view."""
    labs = {v: to_oklab(p["rgb"]) for v, p in panels.items()}
    lines = {v: contour_of(labs[v]) & grow(panels[v]["mask"]) for v in panels}
    pool = np.concatenate([labs[v][panels[v]["mask"] & ~lines[v]] for v in panels])
    feat = lambda lab: lab * np.array([L_WEIGHT, 1, 1])     # noqa: E731
    centres = eye_paint.kmeans(feat(pool), FAMILIES)
    label = chunked_nearest(feat(pool), centres)
    albedos = {c: albedo_of(pool[label == c]) for c in np.unique(label)}
    out = {}
    for v, p in panels.items():
        sel = p["mask"] & ~lines[v]
        lab, which = labs[v][sel], chunked_nearest(feat(labs[v][sel]), centres)
        for c, a in albedos.items():
            lab[which == c] = remap(lab[which == c], a)
        lit = np.clip(p["rgb"], 0, 255).copy()
        lit[sel] = from_oklab(lab)
        out[v] = {"raw": p["rgb"], "on": lit, "flat": fill_lines(lit, lines[v], p["mask"]), "line": lines[v]}
    return out, {"families": len(albedos), "albedo": [[int(x) for x in from_oklab(a).round()] for a in albedos.values()],
                 "line_share": round(float(sum(lines[v].sum() for v in panels) / sum(p["mask"].sum() for p in panels.values())), 3)}


def chunked_nearest(px, centres, step=200000):
    return np.concatenate([eye_paint.nearest(px[i:i + step], centres) for i in range(0, len(px), step)]) if len(px) else np.zeros(0, int)


# ---------------------------------------------------------------- cameras and the sheet
def euler_xyz(deg):
    """3x3 of Blender's XYZ Euler (R = Rz Ry Rx), degrees."""
    x, y, z = np.radians(deg)
    cx, sx, cy, sy, cz, sz = np.cos(x), np.sin(x), np.cos(y), np.sin(y), np.cos(z), np.sin(z)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rz @ ry @ rx


def axes(view, tilt=0):
    """(right, up, back) of a review camera: world vectors of the image's x, y and of the direction towards the camera."""
    import views
    return tuple(euler_xyz(views.camera(view, tilt)[1]).T)


def sheet_panels(sheet, doc):
    """{view: {rgb (h, w, 3) float 0..255, mask (h, w)}}: the figure boxes of the sheet at full size, turned as refs/<id>/sheet.json says; right = left mirrored."""
    import silhouette
    from PIL import Image
    img = np.asarray(Image.open(sheet).convert("RGB"), float)
    masks = silhouette.concept_panels(sheet, 768)
    out = {}
    for view, m in masks.items():
        m = np.asarray(m)
        ys, xs = np.nonzero(m)
        sy, sx = img.shape[0] / m.shape[0], img.shape[1] / m.shape[1]
        y0, y1, x0, x1 = int(ys.min() * sy), int((ys.max() + 1) * sy), int(xs.min() * sx), int((xs.max() + 1) * sx)
        iy, ix = (np.arange(y0, y1) / sy).astype(int), (np.arange(x0, x1) / sx).astype(int)
        rgb, mask = img[y0:y1, x0:x1], m[iy[:, None], ix[None, :]]
        if view in doc.get("rotate", ()):
            rgb, mask = np.rot90(rgb, 2), np.rot90(mask, 2)
        if doc.get("mirror", {}).get(view):
            rgb, mask = rgb[:, ::-1], mask[:, ::-1]
        out[view] = {"rgb": rgb.copy(), "mask": mask.copy()}
    out["right"] = {"rgb": out["left"]["rgb"][:, ::-1].copy(), "mask": out["left"]["mask"][:, ::-1].copy()}
    return out


def zbuffer(xyd, tri, shape):
    """(h, w) depth of the nearest surface (largest d, towards the camera), -inf where there is none; xyd (V, 3) pixel x, y and depth."""
    h, w = shape
    z = np.full(shape, -np.inf)
    for t in tri:
        q = xyd[t]
        lo = np.floor(q[:, :2].min(0)).astype(int).clip(0, [w - 1, h - 1])
        hi = np.ceil(q[:, :2].max(0)).astype(int).clip(0, [w - 1, h - 1])
        ys, xs = np.mgrid[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]
        b = eye_paint.bary(q[:, :2], xs + 0.5, ys + 0.5)
        if b is None:
            continue
        ok = (b >= -1e-6).all(0)
        d = b[0] * q[0, 2] + b[1] * q[1, 2] + b[2] * q[2, 2]
        ys, xs, d = ys[ok], xs[ok], d[ok]
        near = d > z[ys, xs]
        z[ys[near], xs[near]] = d[near]
    return z


def resized(mask, h, w):
    """`mask` resized to (h, w), nearest."""
    iy, ix = (np.arange(h) * mask.shape[0] // h), (np.arange(w) * mask.shape[1] // w)
    return mask[iy[:, None], ix[None, :]]


def best_shift(a, b):
    """(iou, dy, dx): b rolled by (dy, dx) on a, the shift with the highest IoU (FFT cross-correlation on same-shape masks)."""
    inter = np.fft.irfft2(np.fft.rfft2(a.astype(float)) * np.conj(np.fft.rfft2(b.astype(float))), a.shape)
    iou = inter / np.maximum(a.sum() + b.sum() - inter, 1.0)
    i = np.unravel_index(np.argmax(iou), iou.shape)
    dy, dx = (int(c) if c <= s // 2 else int(c) - s for c, s in zip(i, a.shape))
    return float(iou[i]), dy, dx


def register(xy, tri, mask):
    """(sx, sy, tx, ty, iou): the map px = sx * x + tx, py = ty - sy * y from view coordinates xy (V, 2) to the panel, the model's mask on the panel's mask:
    a scale per axis around height-to-height, then the best shift."""
    lo, hi = xy.min(0), xy.max(0)
    ys, _ = np.nonzero(mask)
    base = (ys.max() + 1 - ys.min()) / max(hi[1] - lo[1], 1e-9)
    zoom = FIT_N / mask.shape[0]
    pad = FIT_N // 2
    canvas = (FIT_N + 2 * pad, int(round(mask.shape[1] * zoom)) + 2 * pad)
    target = np.zeros(canvas, bool)
    target[pad:pad + FIT_N, pad:canvas[1] - pad] = resized(mask, FIT_N, canvas[1] - 2 * pad)
    fine = np.c_[(xy - lo) * base * zoom * 2, np.zeros(len(xy))]     # one raster, 2 x, of the largest scale's order; the sweep resizes it
    fine[:, 1] = (hi[1] - xy[:, 1]) * base * zoom * 2
    size = np.ceil(fine[:, :2].max(0)).astype(int) + 2
    shot = np.isfinite(zbuffer(fine, tri, (size[1], size[0])))
    best = (-1.0,)
    for fx in SCALES:
        for fy in SCALES:
            h, w = max(int(size[1] / 2 * fy), 1), max(int(size[0] / 2 * fx), 1)
            if h >= canvas[0] or w >= canvas[1]:
                continue
            m = np.zeros(canvas, bool)
            m[:h, :w] = resized(shot, h, w)
            score, dy, dx = best_shift(target, m)
            if score > best[0]:
                best = (score, fx, fy, dx - pad, dy - pad)
    score, fx, fy, dx, dy = best
    sx, sy = base * fx, base * fy
    return sx, sy, dx / zoom - lo[0] * sx, dy / zoom + hi[1] * sy, score


def best_camera(view, pos, tri, mask):
    """{tilt, fit (sx, sy, tx, ty, iou), r, u, b}: the review camera of a view, the tilted ones swept as silhouette.py sweeps them."""
    import views
    tilts = views.TILTS if view in views.TILTED else (0,)
    best = None
    for tilt in tilts:
        r, u, b = axes(view, tilt)
        fit = register(np.c_[pos @ r, pos @ u], tri, mask)
        if best is None or fit[4] > best["fit"][4]:
            best = {"tilt": int(tilt), "fit": fit, "r": r, "u": u, "b": b}
    return best


def camera_pixels(cam, P):
    """(px, py, depth) of the points P (n, 3) in a registered camera."""
    sx, sy, tx, ty, _ = cam["fit"]
    return sx * (P @ cam["r"]) + tx, ty - sy * (P @ cam["u"]), P @ cam["b"]


def depth_edges(z, step):
    """(h, w) bool: pixels beside a jump of depth over `step` (a depth-map Canny without its blur and thinning: a z-buffer has no noise; cv2 is not in Blender's or this Python)."""
    gy, gx = np.zeros(z.shape, bool), np.zeros(z.shape, bool)
    d = np.nan_to_num(z, neginf=-1e6)
    gy[1:] = np.abs(d[1:] - d[:-1]) > step
    gx[:, 1:] = np.abs(d[:, 1:] - d[:, :-1]) > step
    return gy | gx


def view_mask(cam, panel_mask, pos, tri, height):
    """(z, usable): the view's depth map in panel pixels and the pixels it may paint from: inside both masks, off their rims, off the depth edges."""
    px, py, d = camera_pixels(cam, pos)
    z = zbuffer(np.c_[px, py, d], tri, panel_mask.shape)
    r = max(int(round(RIM * panel_mask.shape[0])), 1)
    usable = shrink(panel_mask, r) & shrink(np.isfinite(z), r) & ~grow(depth_edges(z, DEPTH_EDGE * height), 2)
    return z, usable


def weight_of(n_dot_v, seen, w_view, k=K):
    """(n,) the weight of a view over the texels: w_view * cos^k where seen, zero under COS_MIN."""
    c = np.asarray(n_dot_v, float)
    return np.where(np.asarray(seen) & (c >= COS_MIN), w_view * np.clip(c, 0, 1) ** k, 0.0)


def lookup(img, px, py):
    """(n, ...) bilinear sample of img at the pixel coordinates, pixel centres at .5."""
    h, w = img.shape[:2]
    x, y = np.clip(px - 0.5, 0, w - 1.001), np.clip(py - 0.5, 0, h - 1.001)
    i, j = x.astype(int), y.astype(int)
    fx, fy = x - i, y - j
    if img.ndim == 3:
        fx, fy = fx[:, None], fy[:, None]
    return img[j, i] * (1 - fx) * (1 - fy) + img[j, i + 1] * fx * (1 - fy) + img[j + 1, i] * (1 - fx) * fy + img[j + 1, i + 1] * fx * fy


def inside_pixels(px, py, shape):
    return (px >= 0) & (py >= 0) & (px < shape[1]) & (py < shape[0])


def view_texels(cam, usable, z, P, N, eps):
    """(n,) n dot v, (n,) seen (paintable), (n,) visible (no geometry in front, whatever the masks say), px, py of the texels in a camera."""
    px, py, d = camera_pixels(cam, P)
    ok = inside_pixels(px, py, z.shape)
    ix, iy = px.astype(int).clip(0, z.shape[1] - 1), py.astype(int).clip(0, z.shape[0] - 1)
    front = ok & (d >= z[iy, ix] - eps)
    return N @ cam["b"], front & usable[iy, ix], front & (N @ cam["b"] >= COS_MIN), px, py


def soft_normals(pos, tri, T, P):
    """(n, 3) unit normals of the texels (T their triangle, P their point) interpolated from area-weighted normals of the welded vertices: the weights slide over an edge."""
    wid = eye_paint.weld(pos)
    w = wid[tri]
    face = np.cross(pos[tri[:, 1]] - pos[tri[:, 0]], pos[tri[:, 2]] - pos[tri[:, 0]])
    vn = np.zeros((wid.max() + 1, 3))
    for k in range(3):
        np.add.at(vn, w[:, k], face)
    a, b, c = (pos[tri[T, k]] for k in range(3))
    total = np.maximum((face[T] ** 2).sum(1), 1e-18)
    u = (np.cross(c - b, P - b) * face[T]).sum(1) / total
    v = (np.cross(a - c, P - c) * face[T]).sum(1) / total
    n = u[:, None] * vn[w[T, 0]] + v[:, None] * vn[w[T, 1]] + (1 - u - v)[:, None] * vn[w[T, 2]]
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def blend(colours, weights):
    """(n, 3) weighted mean of the views' colours (V, n, 3), (n,) covered; uncovered texels are 0."""
    total = weights.sum(0)
    cov = total > 0
    out = np.zeros(colours.shape[1:])
    out[cov] = (colours[:, cov] * weights[:, cov, None]).sum(0) / total[cov, None]
    return out, cov


def coverage(weights, names, visible):
    """The report of (V, n) weights: % of the texels each view reaches and leads, % nobody paints; `visible` (n,): the surface some view sees at a usable angle, the
    rest is inside the model (overlapping pieces) or only ever grazed."""
    lead = np.argmax(weights, axis=0)
    cov = weights.sum(0) > 0
    n = max(weights.shape[1], 1)
    return {"seen_pct": {v: round(100 * float((weights[i] > 0).mean()), 1) for i, v in enumerate(names)},
            "lead_pct": {v: round(100 * float(((lead == i) & cov).sum() / n), 1) for i, v in enumerate(names)},
            "uncovered_pct": round(100 * float(1 - cov.mean()), 1), "hidden_pct": round(100 * float(1 - visible.mean()), 1),
            "visible_uncovered_pct": round(100 * float((visible & ~cov).sum() / max(visible.sum(), 1)), 1), "views_per_texel": round(float((weights > 0).sum(0)[cov].mean()), 2) if cov.any() else 0.0}


def disagreement(colours, weights, names):
    """Where two views see one texel, how far apart they paint it: {pair: {texels, de_median}} in OKLab ×100 for the two heaviest views of each texel."""
    order = np.argsort(-weights, axis=0)[:2]
    idx = np.arange(weights.shape[1])
    both = weights[order[1], idx] > 0
    out = {}
    for a, b in {tuple(sorted(p)) for p in order[:, both].T.tolist()}:
        sel = both & (np.minimum(order[0], order[1]) == a) & (np.maximum(order[0], order[1]) == b)
        de = np.linalg.norm(to_oklab(colours[a, sel]) - to_oklab(colours[b, sel]), axis=1)
        out[f"{names[a]}+{names[b]}"] = {"texels": int(sel.sum()), "de_median": round(100 * float(np.median(de)), 1)}
    return dict(sorted(out.items(), key=lambda kv: -kv[1]["texels"]))


def edge_samples(uv, tri2, slot):
    """(a, b): atlas texels (E, 2) (x, y) one texel inside each triangle at the midpoint of the shared edges; the two sides of a seam, wherever the charts put them."""
    def side(t, s):
        mid = (uv[t, s] + uv[t, (s + 1) % 3]) / 2 * eye_paint.SIZE
        to = uv[t].mean(1) * eye_paint.SIZE - mid
        return (mid + to / np.maximum(np.linalg.norm(to, axis=1, keepdims=True), 1e-9)).astype(int).clip(0, eye_paint.SIZE - 1)
    return side(tri2[:, 0], slot[:, 0]), side(tri2[:, 1], slot[:, 1])


def seams(img, lead, used, uv, pos, tri, names):
    """Across the mesh edges: OKLab distance (×100) between the two sides, for edges whose sides are led by one view and by two. Per pair of views also the mean height."""
    tri2, slot = eye_paint.shared_edges(eye_paint.weld(pos)[tri])
    a, b = edge_samples(uv, tri2, slot)
    ok = used[a[:, 1], a[:, 0]] & used[b[:, 1], b[:, 0]]
    a, b, tri2, slot = a[ok], b[ok], tri2[ok], slot[ok]
    la, lb = lead[a[:, 1], a[:, 0]], lead[b[:, 1], b[:, 0]]
    lab = to_oklab(img.astype(float))
    de = 100 * np.linalg.norm(lab[a[:, 1], a[:, 0]] - lab[b[:, 1], b[:, 0]], axis=1)
    known = (la >= 0) & (lb >= 0)
    same, cross = known & (la == lb), known & (la != lb)
    z = pos[tri[tri2[:, 0], slot[:, 0]], 2]
    z = (z - pos[:, 2].min()) / max(np.ptp(pos[:, 2]), 1e-9)
    pairs = {}
    for p, q in {tuple(sorted(x)) for x in np.c_[la[cross], lb[cross]].tolist()}:
        sel = cross & (np.minimum(la, lb) == p) & (np.maximum(la, lb) == q)
        pairs[f"{names[p]}+{names[q]}"] = {"edges": int(sel.sum()), "de_median": round(float(np.median(de[sel])), 1), "height": round(float(z[sel].mean()), 2)}
    pct = lambda s, q: round(float(np.percentile(de[s], q)), 1) if s.any() else None        # noqa: E731
    return {"edges_same_view": int(same.sum()), "edges_two_views": int(cross.sum()), "de_same_p50": pct(same, 50), "de_same_p90": pct(same, 90),
            "de_seam_p50": pct(cross, 50), "de_seam_p90": pct(cross, 90), "pairs": dict(sorted(pairs.items(), key=lambda kv: -kv[1]["edges"]))}


# ---------------------------------------------------------------- the GLB
def read_model(glb):
    """(pos (V, 3) Z-up, tri (T, 3), uv (T, 3, 2) glTF: v down, the atlas PNG's bytes) of the painted body."""
    import hive_sheet as H
    j, blob = H.read_glb(glb)
    prim = j["meshes"][0]["primitives"][0]
    pos = H.accessor(j, blob, prim["attributes"]["POSITION"]).astype(float)
    tri = H.accessor(j, blob, prim["indices"]).reshape(-1, 3).astype(int)
    uv = H.accessor(j, blob, prim["attributes"]["TEXCOORD_0"]).astype(float)
    view = j["bufferViews"][j["images"][0]["bufferView"]]
    start = view.get("byteOffset", 0)
    return np.c_[pos[:, 0], -pos[:, 2], pos[:, 1]], tri, uv[tri], blob[start:start + view["byteLength"]]


def swap_atlas(glb, png):
    """`glb` in place with its one image replaced by the bytes `png`; the buffer views after it move, nothing else changes."""
    import hive_sheet as H
    j, blob = H.read_glb(glb)
    view = j["bufferViews"][j["images"][0]["bufferView"]]
    start, old = view.get("byteOffset", 0), view["byteLength"]
    gap = (-len(png)) % 4
    new = blob[:start] + png + b"\0" * gap + blob[start + old + ((-old) % 4):]
    delta = len(png) + gap - old - ((-old) % 4)
    for v in j["bufferViews"]:
        if v is not view and v.get("byteOffset", 0) > start:
            v["byteOffset"] += delta
    view["byteLength"] = len(png)
    j["buffers"][0]["byteLength"] = len(new)
    head = json.dumps(j, separators=(",", ":")).encode()
    head += b" " * ((-len(head)) % 4)
    new += b"\0" * ((-len(new)) % 4)
    pathlib.Path(glb).write_bytes(b"glTF" + struct.pack("<II", 2, 28 + len(head) + len(new)) + struct.pack("<I", len(head)) + b"JSON" + head + struct.pack("<I", len(new)) + b"BIN\0" + new)


def png_bytes(img):
    import io
    from PIL import Image
    out = io.BytesIO()
    Image.fromarray(img.astype(np.uint8)).save(out, "PNG")
    return out.getvalue()


# ---------------------------------------------------------------- the stage
def gate_keep(mixed, own, ab_max, l_max=None):
    """L20-1: which projected colours a texel accepts: near its own painted colour in hue and chroma (and in L when l_max is given). All sRGB 0..255."""
    a, b = to_oklab(mixed), to_oklab(own)
    keep = np.linalg.norm(a[..., 1:] - b[..., 1:], axis=-1) <= ab_max
    return keep if l_max is None else keep & (np.abs(a[..., 0] - b[..., 0]) <= l_max)


def dominant(rgb, ab_max, l_max):
    """(3,) sRGB the sheet gives a piece: the OKLab median of its projected colours, then the median of those within the tolerance of it (twice)."""
    dom = from_oklab(np.median(to_oklab(rgb), axis=0))
    for _ in range(2):
        near = gate_keep(rgb, dom, ab_max, l_max)
        dom = from_oklab(np.median(to_oklab(rgb[near]), axis=0)) if near.any() else dom
    return dom


def accents(colours, areas, identity):
    """(P,) bool: the pieces whose DSL colour is an accent, a saturated detail over a darker or neutral body (eyes, glass, jewels, brass). By colour only, never by name:
    chroma over ACC_C and over ACC_REL times the palette's (median chroma weighted by `areas`), or, when an `identity` line says a colour word (WORDS), a chroma over
    ACC_C at that hue."""
    lab = to_oklab(colours)
    chroma, hue = np.hypot(lab[:, 1], lab[:, 2]), np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) % 360
    order = np.argsort(chroma)
    base = chroma[order][np.searchsorted(np.cumsum(areas[order]), areas.sum() / 2)] if areas.sum() else 0.0
    said = [WORDS[w] for line in identity for w in WORDS if w in line.lower()]
    named = np.zeros(len(colours), bool)
    for centre, half in said:
        named |= np.abs((hue - centre + 180) % 360 - 180) <= half
    return (chroma >= ACC_C) & ((chroma >= ACC_REL * base) | named)


def part_filter(mixed, cov, piece, colours, names, ab_max, l_max, share):
    """L20-2: the colour a piece takes from the sheet, one per piece. mixed (n, 3) sRGB projected, cov (n,) covered, piece (n,) the piece of every texel,
    colours (P, 3) sRGB the DSL gives the pieces, names (P,). A piece is painted when its dominant colour is near its DSL colour (OWN_AB, OWN_L) and `share` of its
    covered texels are within the tolerance of it: those texels keep their projection, every other texel of the piece (refused, uncovered) takes the dominant
    colour. Any other piece keeps the procedural paint whole. (colours (n, 3), painted (n,), per-piece report)."""
    out, painted, report = mixed.copy(), np.zeros(len(mixed), bool), []
    for p in np.unique(piece):
        mine = piece == p
        seen = mine & cov
        if seen.sum() < PART_MIN:
            continue
        dom = dominant(mixed[seen], ab_max, l_max)
        near = seen & gate_keep(mixed, dom, ab_max, l_max)
        uniform = bool(gate_keep(dom, colours[p], OWN_AB, OWN_L) and near.sum() / seen.sum() >= share)
        report.append({"piece": int(p), "name": names[p], "texels": int(mine.sum()), "covered": int(seen.sum()), "kept": int(near.sum()),
                       "dominant": [int(x) for x in dom.round()], "dsl": [int(x) for x in colours[p]], "painted": uniform})
        if uniform:
            out[mine & ~near], painted[mine] = dom, True
    return out, painted, report


def piece_accents(parts, points):
    """(piece (n,) of every point, accent (P,)) for `parts`, (None, None) without."""
    if not parts:
        return None, None
    fields, rgb, _, identity = parts[:4]
    piece = eye_paint.nearest_piece(points, fields)
    return piece, accents(rgb, np.bincount(piece, minlength=len(rgb)).astype(float), identity)


def shield(cov, mixed, piece, accent, rgb):
    """`cov` without the texels of the accent pieces (they keep their paint) and without the projected colours that are an accent's, on a piece that is not it (no leak)."""
    leak = np.zeros(len(cov), bool)
    for i in np.nonzero(accent)[0]:
        leak |= gate_keep(mixed, rgb[i], ACC_LEAK) & (piece != i)
    return cov & ~accent[piece] & ~leak


def project(pos, tri, uv, atlas, panels, mode="on", k=K, soft=False, gate=None, parts=None):
    """(img (S, S, 3) uint8, used (S, S), lead (S, S), info): the atlas of the model with the sheet projected; texels no view sees keep `atlas`.
    soft: the weight's cosine from interpolated normals (the cut-off stays on the triangle's own normal). gate: (ab_max, l_max), see gate_keep: a refused texel keeps `atlas`.
    parts: (fields, colours, names, identity, ab_max, l_max, share), see part_filter and accents (an accent piece is never touched: no gate, no projection) (L20-2): after the gate, a texel takes its piece's dominant colour or keeps `atlas`."""
    nrm = eye_paint.normals(pos, tri)[0]
    used, P, N, T = eye_paint.rasterize(uv, pos, tri, nrm)
    smooth = soft_normals(pos, tri, T[used], P[used]) if soft else None
    height = max(np.ptp(pos[:, 2]), 1e-6)
    lit, palette = delight(panels)
    names = [v for v in VIEW_NAMES if v in panels]
    colours, weights, cams, visible = [], [], {}, np.zeros(used.sum(), bool)
    for v in names:
        cam = best_camera(v, pos, tri, panels[v]["mask"])
        z, usable = view_mask(cam, panels[v]["mask"], pos, tri, height)
        n_dot_v, seen, front, px, py = view_texels(cam, usable, z, P[used], N[used], DEPTH_EPS * height)
        visible |= front
        w_view = cam["fit"][4] ** 2
        cams[v] = {"tilt": cam["tilt"], "iou": round(cam["fit"][4], 3), "w": round(w_view, 3), "scale": [round(x, 1) for x in cam["fit"][:2]]}
        weights.append(weight_of(n_dot_v, seen, w_view, k) if smooth is None else weight_of(smooth @ cam["b"], seen & (n_dot_v >= COS_MIN), w_view, k))
        colours.append(lookup(lit[v][mode], px, py))
    colours, weights = np.array(colours), np.array(weights)
    mixed, cov = blend(colours, weights)
    piece, accent = piece_accents(parts, P[used])
    cov = shield(cov, mixed, piece, accent, parts[1]) if parts else cov
    refused = 0
    if gate:
        accepted = cov & gate_keep(mixed, atlas[used].astype(float), *gate)
        refused, cov = int(cov.sum() - accepted.sum()), accepted
    report = []
    if parts:
        mixed, cov, report = part_filter(mixed, cov, piece, *parts[1:3], *parts[4:])
        report = {"accent": [parts[2][i] for i in np.nonzero(accent)[0]], "pieces": report}
    img = atlas.astype(float).copy()
    img[np.nonzero(used)[0][cov], np.nonzero(used)[1][cov]] = mixed[cov]
    lead = np.full(used.shape, -1)
    lead[used] = np.where(cov, np.argmax(weights, axis=0), -1)
    info = {"mode": mode, "cameras": cams, "palette": palette, **coverage(weights, names, visible), "k": k, "soft": soft, "disagreement": disagreement(colours, weights, names),
            "seams": seams(img, lead, used, uv, pos, tri, names), "texels": int(used.sum()), "gate": gate, "refused": refused, "parts": report}
    done, grown = eye_paint.dilate(img, used, 1)
    done[~grown] = done[grown].mean(0)
    return np.clip(done, 0, 255).astype(np.uint8), used, lead, info


def lead_map(lead):
    """The view that leads each texel, as colours (front red, left green, back blue, top yellow, bottom magenta, right cyan, nobody grey, outside black)."""
    colours = np.array([[230, 60, 60], [60, 200, 60], [70, 90, 240], [240, 220, 60], [220, 60, 220], [60, 220, 220], [120, 120, 120], [0, 0, 0]], np.uint8)
    out = colours[np.where(lead >= 0, lead, 6)]
    out[lead == -2] = colours[7]
    return out


def read_parts(where, unit):
    """(fields, colours (P, 3) sRGB, names, identity) of the pieces of the model: eye_skin's fields.json beside it and the fused DSL in eye/ (same order, one field per piece); the identity lines of refs/<unit>/parts.json."""
    where = pathlib.Path(where)
    fields = json.loads((where / "fields.json").read_text())["pieces"]
    dsl = json.loads((where / "eye/fused.dsl.json").read_text())
    if len(fields) != len(dsl["pieces"]):
        raise SystemExit(f"{where}: {len(fields)} fields for {len(dsl['pieces'])} DSL pieces")
    rgb = {m: [int(h[i:i + 2], 16) for i in (0, 2, 4)] for m, h in dsl["colours"].items()}
    parts = REFS / unit / "parts.json"
    identity = json.loads(parts.read_text()).get("identity", []) if parts.exists() else []
    return fields, np.array([rgb[p["mat"]] for p in dsl["pieces"]], float), [p["name"] for p in dsl["pieces"]], identity


def apply(glb, unit, mode="on", k=K, soft=False, gate=None, parts=None):
    """The sheet of `unit` on the atlas of `glb` in place. atlas.png (alpha = used texels) + atlas-procedural.png, atlas-noline.png, lead.png, project.json beside it. The info."""
    import io
    from PIL import Image
    glb = pathlib.Path(glb)
    where = glb.parent
    pos, tri, uv, png = read_model(glb)
    doc = json.loads((REFS / unit / "sheet.json").read_text()) if (REFS / unit / "sheet.json").exists() else {}
    panels = sheet_panels(REFS / unit / "sheet.jpg", doc)
    atlas = np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))
    img, used, lead, info = project(pos, tri, uv, atlas, panels, mode, k, soft, gate, parts and (*read_parts(where, unit), *parts))
    swap_atlas(glb, png_bytes(img))
    Image.fromarray(atlas).save(where / "atlas-procedural.png")
    Image.fromarray(np.dstack([img, np.where(used, 255, 0).astype(np.uint8)])).save(where / "atlas.png")
    Image.fromarray(lead_map(np.where(used, lead, -2))).save(where / "lead.png")
    if mode == "on":
        Image.fromarray(project(pos, tri, uv, atlas, panels, "flat", k, soft, gate, parts and (*read_parts(where, unit), *parts))[0]).save(where / "atlas-noline.png")
    (where / "project.json").write_text(json.dumps(info, indent=1))
    return info


def apply_stage(glb, unit, project_mode):
    """The one call of eye_stage.finish: {} when off, or when tight has no piece fields or no sheet (a gate never stops the pipeline)."""
    if project_mode == "tight":
        if not ((pathlib.Path(glb).parent / "fields.json").exists() and (REFS / unit / "sheet.jpg").exists()):
            return {}
        try:
            return apply(glb, unit, "flat", gate=TIGHT_GATE, parts=TIGHT_PARTS)
        except ValueError as err:                  # a panel that registers nowhere: the procedural paint stays, the unit is still produced
            return {"error": str(err)[:200]}
    return apply(glb, unit, project_mode) if project_mode in MODES else {}


def run_variant(unit, src, tag, mode, k=K, soft=False, gate=None, parts=None):
    """A copy of a run with another mode of the projection, from its body before the hull: `model-body.glb` -> project -> hull."""
    import shutil
    import outline
    from_dir, out = DRAFT / unit / src, DRAFT / unit / tag
    if out.exists():
        raise SystemExit(f"{out} exists")
    out.mkdir()
    for f in from_dir.iterdir():
        if f.is_file() and not f.name.startswith("pairwise"):
            shutil.copy(f, out / f.name)
    if parts:
        (out / "eye").mkdir()
        shutil.copy(from_dir / "eye/fused.dsl.json", out / "eye/fused.dsl.json")
    shutil.copy(from_dir / "model-body.glb", out / "model.glb")
    info = apply(out / "model.glb", unit, mode, k, soft, gate, parts)
    shutil.copy(out / "model.glb", out / "model-body.glb")
    outline.apply(out / "model.glb", hull=True)
    print(unit, tag, json.dumps({k: info[k] for k in ("uncovered_pct", "seen_pct", "refused", "texels")}))


def sheet(unit, runs, history=HISTORY):
    import leva18
    print(leva18.sheet(unit, runs=runs, wires=(), hive=False, history=pathlib.Path(history)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("variant")
    v.add_argument("--id", required=True)
    v.add_argument("--tag", required=True)
    v.add_argument("--mode", choices=MODES, required=True)
    v.add_argument("--from", dest="src", default="v19-default")
    v.add_argument("--k", type=int, default=K)
    v.add_argument("--soft", action="store_true", help="the weight's cosine from interpolated normals")
    v.add_argument("--gate-ab", type=float, help="L20-1: refuse a projected colour this far (OKLab a, b) from the texel's painted colour")
    v.add_argument("--gate-l", type=float, help="with --gate-ab: also refuse this far in L")
    v.add_argument("--part-ab", type=float, help="L20-2: one colour per piece: refuse a projected colour this far (OKLab a, b) from the piece's dominant colour")
    v.add_argument("--part-l", type=float, default=0.2, help="with --part-ab: also refuse this far in L")
    v.add_argument("--part-share", type=float, default=0.5, help="with --part-ab: a piece with less of its covered texels near its dominant colour keeps the procedural paint")
    s = sub.add_parser("sheet")
    s.add_argument("unit")
    s.add_argument("--runs", default="v16-r3,v19-default,v20-proj,v20-proj-flat,v20-proj-raw")
    s.add_argument("--history", default=str(HISTORY), help="the dir of the board (never overwritten)")
    args = ap.parse_args(argv)
    if args.cmd == "variant":
        run_variant(args.id, args.src, args.tag, args.mode, args.k, args.soft, (args.gate_ab, args.gate_l) if args.gate_ab else None,
                    (args.part_ab, args.part_l, args.part_share) if args.part_ab else None)
    else:
        sheet(args.unit, tuple(args.runs.split(",")), args.history)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
