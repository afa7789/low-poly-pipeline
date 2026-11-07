#!/usr/bin/env python3
"""Mass mold (author 2026-11-05, lever 1): the eye stage's unions fill out toward the concept's silhouette, read from the neural molds.

    --eye-mold splat   the TripoSplat depth renders of refs/<id>/neural/ (depth-front, depth-left0 / left180): a visual hull of the front and
                       left covers plus the two near surfaces (a point is inside when it projects inside both covers, behind the front surface
                       and inside of the left surface)
    --eye-mold masks   the SAM2 part masks of the body parts (role != prop) united per view: the hull of the two covers, no depth
    --eye-mold off     the unions as before

prepare() runs in the pipeline's python (scipy for the distance transforms) and writes <run>/eye/mold/mold-<view>.npz; Mold (numpy only,
imported by eye_union inside Blender) registers each raster on the body's own silhouette (the body pieces voxelised and projected: scale
sweep around height-to-height, then the best shift by FFT) and gives sdf(points) in world units. eye_union blends it into each group's
field only within INFLATE x height of the group's own pieces, so a limb grows toward the concept's width and no group swallows the body.
Blender frame: z up, the front at -y; the front camera's image right is +x, the left camera (views.py: at -x) has the front on its right.
TripoSplat frame: the unit faces +x, up +z; depth-front's u = y, near = x; depth-left0 (camera -y, the unit's right side) u = x, near = -y."""
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

ROOT = HERE.parents[1]
REFS = ROOT / "artifacts/model-sheets/refs"
MODES = ("off", "splat", "masks")
RASTER = 512            # longest side of a mold raster, px
INFLATE = 0.08          # a union fills out to the mold at most this (share of the height) beyond its own pieces
VOX = 0.02              # the body silhouette the mold is registered on: grid step (share of the height)
SCALES = np.arange(0.85, 1.151, 0.025)    # the registration's scale sweep around height-to-height
MIN_IOU = 0.35          # a view that registers under this is not trusted: the mold is off (a thin body on a wide concept scores .4-.6: that gap is what the mold fills)
FAR = 10.0
NEURAL_RES = 1024       # neural_molds.RES: the depth renders' size; a cube unit of the splat is (RES - 1) px there


# ---------------------------------------------------------------- python3.14 side: the rasters
def _edt(mask):
    from scipy import ndimage
    return ndimage.distance_transform_edt(mask)


def signed_px(cover):
    """Signed distance in pixels to the cover's rim: negative inside."""
    return (_edt(~cover) - _edt(cover)).astype(np.float32)


def filled(values, cover):
    """`values` with every pixel outside `cover` taking its nearest covered pixel's value."""
    from scipy import ndimage
    idx = ndimage.distance_transform_edt(~cover, return_distances=False, return_indices=True)
    return values[idx[0], idx[1]]


def shrunk(img, factor):
    """An array resized by `factor` (nearest), PIL."""
    from PIL import Image
    h, w = img.shape
    size = (max(1, round(w * factor)), max(1, round(h * factor)))
    return np.asarray(Image.fromarray(img).resize(size, Image.NEAREST))


def raster_of(cover, near, px_per_cube):
    """{sdf, near, cover, px_per_cube}: the cover's signed distance and the filled near map, shrunk to RASTER on the longest side."""
    f = min(1.0, RASTER / max(cover.shape))
    cover = cover.astype(np.uint8)
    cov = shrunk(cover, f) > 0
    out = {"sdf": signed_px(cov), "cover": cov, "px_per_cube": np.float32(px_per_cube * f), "has_depth": np.bool_(near is not None)}
    out["near"] = shrunk(filled(np.nan_to_num(near, nan=0.0).astype(np.float32), np.isfinite(near)), f) if near is not None else np.zeros(cov.shape, np.float32)
    return out


def splat_rasters(neural):
    """{front, left0, left180: raster} of the TripoSplat depth renders."""
    out = {}
    for v in ("front", "left0", "left180"):
        d = np.load(neural / f"depth-{v}.npy")
        out[v] = raster_of(np.isfinite(d), d, NEURAL_RES - 1)
    return out


def body_parts(unit):
    doc = json.loads((REFS / unit / "parts.json").read_text())
    return [p["name"] for p in doc["parts"] if p.get("role") != "prop"]


def mask_rasters(unit, neural):
    """{front, left: raster} of the SAM2 masks of the body parts united, per view (no depth)."""
    from PIL import Image
    out = {}
    for v in ("front", "left"):
        cover = None
        for name in body_parts(unit):
            f = neural / "sam2" / v / f"{name}.png"
            if f.exists():
                m = np.asarray(Image.open(f).convert("L")) > 127
                cover = m if cover is None else cover | m
        if cover is not None and cover.any():
            out[v] = raster_of(cover, None, 0.0)
    return out


def prepare(unit, mode, out):
    """<out>/mold-<view>.npz + mold.json for `mode`; the report, or None when off or the neural refs are missing."""
    neural = REFS / unit / "neural"
    if mode == "off" or not neural.exists():
        return None
    rasters = splat_rasters(neural) if mode == "splat" and (neural / "depth-front.npy").exists() else mask_rasters(unit, neural) if mode == "masks" else {}
    if "front" not in rasters:
        return None
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for v, r in rasters.items():
        np.savez(out / f"mold-{v}.npz", **r)
    doc = {"mode": mode, "unit": unit, "views": {v: {"shape": list(r["cover"].shape), "cover_px": int(r["cover"].sum()), "depth": bool(r["has_depth"])} for v, r in rasters.items()}}
    (out / "mold.json").write_text(json.dumps(doc, indent=1))
    return doc


# ---------------------------------------------------------------- numpy side (Blender): registration and the field
def best_shift(a, b):
    """(iou, dy, dx): b rolled by (dy, dx) on a, the shift with the highest IoU (FFT cross-correlation on same-shape masks)."""
    inter = np.fft.irfft2(np.fft.rfft2(a.astype(float)) * np.conj(np.fft.rfft2(b.astype(float))), a.shape)
    iou = inter / np.maximum(a.sum() + b.sum() - inter, 1.0)
    i = np.unravel_index(np.argmax(iou), iou.shape)
    dy, dx = (int(c) if c <= s // 2 else int(c) - s for c, s in zip(i, a.shape))
    return float(iou[i]), dy, dx


def body_grid(pieces, height):
    """(inside (nx, ny, nz) bool, origin, vox): the body pieces voxelised."""
    import eye_skin as K
    vox = VOX * height
    lo, hi = np.min([p["lo"] for p in pieces], 0) - vox, np.max([p["hi"] for p in pieces], 0) + vox
    n = np.ceil((hi - lo) / vox).astype(int) + 1
    axes = [lo[i] + vox * (np.arange(n[i]) + 0.5) for i in range(3)]
    pts = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)
    inside = np.zeros(len(pts), bool)
    for p in pieces:
        near = ((pts > p["lo"]) & (pts < p["hi"])).all(1)
        if near.any():
            inside[near] |= K.convex_d(p["planes"], pts[near]) < 0
    return inside.reshape(*n), lo, vox


class View:
    """One registered raster: px_u(h), px_v(z) of the world's horizontal h (x for the front, -y for the left) and height z."""

    def __init__(self, raster, flip, near_dir):
        self.sdf, self.cover, self.near = raster["sdf"], raster["cover"], raster["near"]
        self.ppc, self.depth, self.near_dir = float(raster["px_per_cube"]), bool(raster["has_depth"]), near_dir
        if flip:
            self.sdf, self.cover, self.near = self.sdf[:, ::-1], self.cover[:, ::-1], self.near[:, ::-1]
        self.flip = flip
        ys, xs = np.nonzero(self.cover)
        self.rows, self.uc, self.vc = (ys.max() + 1 - ys.min()), (xs.min() + xs.max() + 1) / 2, (ys.min() + ys.max() + 1) / 2
        self.ppu = self.h0 = self.z0 = self.iou = None

    def register(self, mask, origin_h, origin_z, vox, z_extent):
        """Fit the cover on `mask` (nz, nh) (rows = z, cols = h, cell centres at origin + vox x (i + .5)): a scale sweep, the best FFT shift. The IoU."""
        nz, nh = mask.shape
        zi, hi_ = np.nonzero(mask)
        hc, zc = origin_h + vox * (hi_.mean() + 0.5), origin_z + vox * (zi.mean() + 0.5)
        base = self.rows / max(z_extent, 1e-9)
        hs, zs = origin_h + vox * (np.arange(nh) + 0.5), origin_z + vox * (np.arange(nz) + 0.5)
        best = None
        for s in SCALES:
            ppu = base * s
            u = np.clip(np.round((hs - hc) * ppu + self.uc).astype(int), 0, self.cover.shape[1] - 1)
            v = np.clip(np.round(self.vc - (zs - zc) * ppu).astype(int), 0, self.cover.shape[0] - 1)
            inside_u = ((hs - hc) * ppu + self.uc >= 0) & ((hs - hc) * ppu + self.uc < self.cover.shape[1])
            inside_v = (self.vc - (zs - zc) * ppu >= 0) & (self.vc - (zs - zc) * ppu < self.cover.shape[0])
            c = self.cover[v[:, None], u[None, :]] & inside_v[:, None] & inside_u[None, :]
            iou, dy, dx = best_shift(mask, c)
            if best is None or iou > best[0]:
                best = (iou, ppu, dy, dx)
        self.iou, self.ppu, dy, dx = best
        self.h0, self.z0 = hc + dx * vox, zc + dy * vox          # px_u = (h - h0) * ppu + uc; px_v = vc - (z - z0) * ppu
        return self.iou

    def px(self, h, z):
        return (h - self.h0) * self.ppu + self.uc, self.vc - (z - self.z0) * self.ppu

    def overlay(self, mask, origin_h, origin_z, vox):
        """(nz, nh, 3) uint8: the registered cover (red) over the body mask (green), both yellow; for <mold dir>/fit-<view>.ppm."""
        nz, nh = mask.shape
        hs, zs = origin_h + vox * (np.arange(nh) + 0.5), origin_z + vox * (np.arange(nz) + 0.5)
        h, z = np.meshgrid(hs, zs)
        cov = self.sample(self.sdf, h.ravel(), z.ravel()).reshape(nz, nh) < 0
        img = np.zeros((nz, nh, 3), np.uint8)
        img[..., 0] = np.where(cov, 255, 0)
        img[..., 1] = np.where(mask, 255, 0)
        return img[::-1]

    def world_u(self, px_u):
        return self.h0 + (px_u - self.uc) / self.ppu

    def cube_px(self, cube):
        """Raster column of a splat cube coordinate (left180 is rendered mirrored and flipped back: its columns are left0's)."""
        return cube * self.ppc

    def sample(self, arr, h, z):
        """arr at the pixels of (h, z); FAR (sdf) / NaN (near) outside the raster."""
        u, v = self.px(h, z)
        ok = (u >= 0) & (v >= 0) & (u < arr.shape[1] - 1) & (v < arr.shape[0] - 1)
        out = np.full(len(u), np.nan if arr is self.near else FAR, np.float32)
        iu, iv = np.clip(u.astype(int), 0, arr.shape[1] - 1), np.clip(v.astype(int), 0, arr.shape[0] - 1)
        out[ok] = arr[iv[ok], iu[ok]]
        return out


class Mold:
    """The registered mold of a run: sdf(points (N, 3)) in world units, negative inside; `report` for the summary."""

    def __init__(self, where, pieces, height):
        where = pathlib.Path(where)
        self.doc = json.loads((where / "mold.json").read_text())
        rasters = {v: dict(np.load(where / f"mold-{v}.npz")) for v in self.doc["views"]}
        inside, lo, vox = body_grid(pieces, height)
        z_extent = float(np.ptp(np.nonzero(inside.any((0, 1)))[0]) + 1) * vox
        front_mask = inside.any(1).T                        # (nz, nx): h = x
        left_mask = inside.any(0).T[:, ::-1]                # (nz, ny) with columns = -y increasing: the front on the right
        ny = inside.shape[1]
        self.front = View(rasters["front"], False, 0)
        f_iou = self.front.register(front_mask, lo[0], lo[2], vox, z_extent)
        cands = [("left0", False, 1), ("left180", True, -1)] if "left0" in rasters else [("left", False, 0), ("left", True, 0)]
        best = None
        for name, flip, near_dir in cands:
            if name not in rasters:
                continue
            v = View(rasters[name], flip, near_dir)
            iou = v.register(left_mask, -(lo[1] + vox * ny), lo[2], vox, z_extent)
            if best is None or iou > best[0]:
                best = (iou, name, v)
        self.left = best[2] if best else None
        self.ok = f_iou >= MIN_IOU and self.left is not None and self.left.iou >= MIN_IOU
        self.report = {"mode": self.doc["mode"], "front_iou": round(f_iou, 3), "left_iou": round(best[0], 3) if best else None, "left_render": best[1] if best else None,
                       "left_flip": bool(self.left.flip) if self.left else None, "ok": self.ok, "depth": bool(self.front.depth and self.left and self.left.depth)}
        ppm(where / "fit-front.ppm", self.front.overlay(front_mask, lo[0], lo[2], vox))
        if self.left:
            ppm(where / "fit-left.ppm", self.left.overlay(left_mask, -(lo[1] + vox * ny), lo[2], vox))

    def sdf(self, pts):
        x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
        df = self.front.sample(self.front.sdf, x, z) / self.front.ppu
        dl = self.left.sample(self.left.sdf, -y, z) / self.left.ppu
        d = np.maximum(df, dl)
        if self.report["depth"]:
            near_f = self.front.sample(self.front.near, x, z)            # splat x (cube): the front surface's depth = the left raster's column
            y_surf = -self.left.world_u(self.left.cube_px(near_f))        # h = -y
            d = np.maximum(d, np.nan_to_num(y_surf - y, nan=-FAR))
            near_l = self.left.sample(self.left.near, -y, z)              # +-splat y (cube): the side surface = the front raster's column
            x_surf = self.front.world_u(self.front.cube_px(near_l * -self.left.near_dir))
            d = np.maximum(d, np.nan_to_num(self.left.near_dir * (x_surf - x), nan=-FAR))
        return d


def main_axis(verts):
    """Unit vector of the longest direction of a piece (the first principal component of its vertices)."""
    r = verts - verts.mean(0)
    w, v = np.linalg.eigh(r.T @ r)
    return v[:, int(np.argmax(w))]


def inflate(pieces, mold, height, vox):
    """The body `pieces` (records of eye_skin.piece_data) pushed out to the mold IN PLACE: every vertex moves sideways (perpendicular to the piece's
    main axis, away from its centre) as far as it stays inside the mold, at most INFLATE x height, never inward; planes, samples and box follow.
    The pieces' ends (the joints) stay. {pieces, verts, mean_m, max_m} for the report."""
    import eye_skin as K
    steps = np.arange(1, int(INFLATE * height / vox) + 1) * vox
    moved, dist = 0, []
    for p in pieces:
        verts = np.asarray(p["verts"], float)
        a = main_axis(verts)
        r = verts - verts.mean(0)
        perp = r - np.outer(r @ a, a)
        n = np.linalg.norm(perp, axis=1)
        ok = n > 1e-6
        if not ok.any():
            continue
        u = np.zeros_like(perp)
        u[ok] = perp[ok] / n[ok, None]
        pts = verts[:, None, :] + u[:, None, :] * steps[None, :, None]
        inside = (mold.sdf(pts.reshape(-1, 3)) < 0).reshape(len(verts), len(steps))
        k = np.cumprod(inside, axis=1).sum(1)                   # consecutive in-mold steps from the vertex
        k[~ok] = 0
        if not k.any():
            continue
        shift = np.where(k > 0, steps[np.maximum(k - 1, 0)], 0.0)
        verts = verts + u * shift[:, None]
        p["verts"], p["planes"], p["samples"] = verts, K.face_planes(verts, p["faces"]), K.samples_of(verts, p["faces"])
        p["lo"], p["hi"] = verts.min(0), verts.max(0)
        moved += 1
        dist += shift[k > 0].tolist()
    return {"pieces": moved, "verts": len(dist), "mean_m": round(float(np.mean(dist)), 3) if dist else 0.0, "max_m": round(float(np.max(dist)), 3) if dist else 0.0}


def ppm(path, img):
    """A binary PPM of an (h, w, 3) uint8 image (Blender's python has no PIL)."""
    pathlib.Path(path).write_bytes(b"P6\n%d %d\n255\n" % (img.shape[1], img.shape[0]) + np.ascontiguousarray(img).tobytes())


def load(where, pieces, height):
    """The Mold of <run>/eye/mold registered on the body `pieces` (its .ok says whether it may be used), or None without a mold dir."""
    if not where or not (pathlib.Path(where) / "mold.json").exists() or not pieces:
        return None
    m = Mold(where, pieces, height)
    print("MOLD", json.dumps(m.report))
    return m
