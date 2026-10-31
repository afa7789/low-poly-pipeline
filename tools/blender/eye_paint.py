#!/usr/bin/env python3
"""L17-3: the eye stage's flat-colour pieces painted by hand, procedurally (PIPELINE 35.L17-3).

    blender -b -P tools/blender/eye_paint.py -- <in.glb> <out.glb>        # + <out dir>/atlas.png (RGBA, alpha = the texels the model samples)
    eye_paint.apply(glb)                                                  # python side: --eye-paint on, in place, before outline.apply
    python3.14 tools/blender/eye_paint.py run --id n005 --from v16-r3 --tag v17-paint-hull [--outline hull|ink|both]
    python3.14 tools/blender/eye_paint.py stats <run dir>...              # hive_sheet.texture_stats of each run's atlas.png
    python3.14 tools/blender/eye_paint.py sheet <unit>                    # history/2026-10-30-l17-paint/<unit>.png

Works on the final GLB (one mesh, a primitive per material; a united mesh from L17-2 is the same shape): the triangles are grown into
islands (neighbours across a smooth edge, normal within 60 degrees of the seed, so a planar projection cannot fold), each island is flattened
on its seed's plane and the islands are shelf-packed into ONE 256 px atlas. Every texel is a point of the surface, so the painting is a
function of position and has no seam: material colour x a vertical gradient (+-.05) x low-frequency brush noise x the light baked at +-.06 x
ambient occlusion (BVH rays, in Blender). The result is quantised to 12 colours (k-means) so it reads as paint, then the ink line is
drawn: the edges with a dihedral over 40 degrees and the borders between materials, 1-2 texels wide, in the material colour x .35 (not black).
No model, no image from anywhere: noise, gradients and strokes only.
"""
import json
import pathlib
import struct
import subprocess
import sys
import tempfile
import zlib

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SIZE = 256                  # the atlas, px (the WC3 median: 256 px textures)
PAD = 0                     # texels around every island (the rectangle has one texel of slack: islands never touch)
SHARP = np.cos(np.radians(40))      # dihedral over 40 degrees = a drawn edge
GROW = np.cos(np.radians(60))       # an island's normals stay within 60 degrees of its seed
INK_D = 0.75                # a texel centre within this of an edge is ink (a 1-2 texel line)
INK_MIN = 12                # an edge shorter than this many texels is not drawn: it would be all ink
EDGE_LIGHT = 1.6            # the texel row inside the line: the material colour x 1.6, the hand-painted edge highlight
INK_DARK = 0.35             # ink = material colour x .35
COLOURS = 12                # the hand-painted palette of a model
GRADIENT, BRUSH, LIGHT_GAIN, AO_GAIN = 0.16, 0.12, 0.18, 0.55   # +-.08 over the height, +-.06 noise, +-.09 light, up to -55 % in a crevice
LIFT = 20.0                 # 0..255 per unit of the multiplier's departure from 1: light and shadow do not vanish on a dark colour
LUMA = np.array([0.299, 0.587, 0.114])
LIGHT = np.array([-0.4, -0.5, 0.77]) / np.linalg.norm([-0.4, -0.5, 0.77])    # up, front (-Y) and left of the model


# ---------------------------------------------------------------- islands
def weld(pos):
    """Ids of the positions to 1e-5: a hard edge's split vertices are one."""
    return np.unique(np.round(pos / 1e-5).astype(np.int64), axis=0, return_inverse=True)[1].reshape(-1)


def normals(pos, tri):
    """(n (T, 3) unit normals, area (T,)) of the triangles."""
    f = np.cross(pos[tri[:, 1]] - pos[tri[:, 0]], pos[tri[:, 2]] - pos[tri[:, 0]])
    a = np.linalg.norm(f, axis=1)
    return f / np.maximum(a, 1e-12)[:, None], a / 2


def shared_edges(wtri):
    """(tri (E, 2), slot (E, 2)): the two triangles of every edge that exactly two share, and the edge's slot in each (corners slot, slot + 1)."""
    t = len(wtri)
    ab = np.concatenate([wtri[:, [0, 1]], wtri[:, [1, 2]], wtri[:, [2, 0]]])
    _, inv, cnt = np.unique(np.sort(ab, axis=1), axis=0, return_inverse=True, return_counts=True)
    inv = inv.reshape(-1)
    pick = np.flatnonzero(cnt[inv] == 2)
    pick = pick[np.argsort(inv[pick], kind="stable")].reshape(-1, 2)
    return pick % t, pick // t


def sharp_edges(tri2, nrm, mat):
    """Boolean (E,): a drawn edge, a dihedral over 40 degrees or two materials."""
    return ((nrm[tri2[:, 0]] * nrm[tri2[:, 1]]).sum(1) < SHARP) | (mat[tri2[:, 0]] != mat[tri2[:, 1]])


def islands(tri2, sharp, nrm):
    """Island id (T,) of every triangle: grown from the lowest free one over smooth edges while its normal is within 60 degrees of the seed's."""
    nb = [[] for _ in range(len(nrm))]
    for (a, b), s in zip(tri2, sharp):
        if not s:
            nb[a].append(b)
            nb[b].append(a)
    isl, count = np.full(len(nrm), -1), 0
    for seed in range(len(nrm)):
        if isl[seed] >= 0:
            continue
        isl[seed], count = count, count + 1
        stack = [seed]
        while stack:
            for u in nb[stack.pop()]:
                if isl[u] < 0 and nrm[u] @ nrm[seed] >= GROW:
                    isl[u] = isl[seed]
                    stack.append(u)
    return isl


def flatten(pos, tri, nrm, isl):
    """(flat (T, 3, 2) corner coordinates in world units, each island's min corner at its own origin; size (K, 2) of the islands)."""
    flat, size = np.zeros((len(tri), 3, 2)), np.zeros((isl.max() + 1, 2))
    for k in range(isl.max() + 1):
        ts = np.flatnonzero(isl == k)
        n = nrm[ts[0]] if np.linalg.norm(nrm[ts[0]]) > 0.5 else np.array([0.0, 0.0, 1.0])
        u = np.cross([0.0, 0.0, 1.0] if abs(n[2]) < 0.9 else [1.0, 0.0, 0.0], n)
        u /= np.linalg.norm(u)
        q = pos[tri[ts]] @ np.stack([u, np.cross(n, u)], axis=1)
        span = np.ptp(q.reshape(-1, 2), axis=0)
        if span[0] < span[1]:                       # long side along u: shelves stay even (a rotation, no mirror)
            q, span = np.stack([q[..., 1], -q[..., 0]], axis=-1), span[::-1]
        flat[ts] = q - q.reshape(-1, 2).min(0)
        size[k] = span
    return flat, size


def shelf(px):
    """Origins (K, 2) of the rectangles `px` (K, 2) on shelves of the atlas, tallest first; None when they do not fit."""
    org, x, y, row = np.zeros_like(px), 0, 0, 0
    for i in np.argsort(-px[:, 1], kind="stable"):
        w, h = px[i]
        if x + w > SIZE:
            x, y, row = 0, y + row, 0
        if y + h > SIZE or w > SIZE:
            return None
        org[i] = (x, y)
        x, row = x + w, max(row, h)
    return org


def fit(size):
    """(scale texels per unit, origins): the largest scale whose islands, each with PAD texels around, shelf-pack into the atlas."""
    lo, hi, best = 0.0, SIZE / max(size.max(), 1e-9), None
    for _ in range(24):
        mid = (lo + hi) / 2
        org = shelf(np.ceil(size * mid).astype(int) + 1 + 2 * PAD)
        lo, hi, best = (mid, hi, (mid, org)) if org is not None else (lo, mid, best)
    return best


def unwrap(pos, tri, mat):
    """(uv (T, 3, 2) in 0..1 with v up, tri2, sharp, nrm, n islands, scale): the islands of the mesh packed in one atlas."""
    nrm = normals(pos, tri)[0]
    tri2, slot = shared_edges(weld(pos)[tri])
    sharp = sharp_edges(tri2, nrm, mat)
    isl = islands(tri2, sharp, nrm)
    flat, size = flatten(pos, tri, nrm, isl)
    scale, org = fit(size)
    px = (org[isl][:, None, :] + PAD + flat * scale) / SIZE
    return px, (tri2, slot), sharp, nrm, isl.max() + 1, scale


# ---------------------------------------------------------------- texels
def rasterize(uv, pos, tri, nrm):
    """(mask (S, S), P (S, S, 3), N (S, S, 3), T (S, S)): the surface point of every texel the UV triangles cover; a triangle too small to
    cover a texel centre takes the texel of its centroid."""
    mask, P, N, T = np.zeros((SIZE, SIZE), bool), np.zeros((SIZE, SIZE, 3)), np.zeros((SIZE, SIZE, 3)), np.full((SIZE, SIZE), -1)
    for t in range(len(tri)):
        q = uv[t] * SIZE
        lo, hi = np.floor(q.min(0)).astype(int), np.ceil(q.max(0)).astype(int)
        ys, xs = np.mgrid[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]
        w = bary(q, xs + 0.5, ys + 0.5)
        ok = (w >= -1e-6).all(0) if w is not None else np.zeros(xs.shape, bool)
        if not ok.any():
            xs, ys, ok, w = np.array([[int(q[:, 0].mean())]]), np.array([[int(q[:, 1].mean())]]), np.ones((1, 1), bool), np.full((3, 1, 1), 1 / 3)
        x, y = xs[ok], ys[ok]
        keep = (x >= 0) & (x < SIZE) & (y >= 0) & (y < SIZE)
        x, y = x[keep], y[keep]
        mask[y, x], T[y, x], N[y, x] = True, t, nrm[t]
        P[y, x] = (w[:, ok][:, keep].T[:, :, None] * pos[tri[t]][None]).sum(1)
    return mask, P, N, T


def bary(q, px, py):
    """(3, ...) barycentric weights of the points in the triangle q (3, 2); None for a degenerate one."""
    d = (q[1, 0] - q[0, 0]) * (q[2, 1] - q[0, 1]) - (q[1, 1] - q[0, 1]) * (q[2, 0] - q[0, 0])
    if abs(d) < 1e-9:
        return None
    w1 = ((px - q[0, 0]) * (q[2, 1] - q[0, 1]) - (py - q[0, 1]) * (q[2, 0] - q[0, 0])) / d
    w2 = ((q[1, 0] - q[0, 0]) * (py - q[0, 1]) - (q[1, 1] - q[0, 1]) * (px - q[0, 0])) / d
    return np.stack([1 - w1 - w2, w1, w2])


def lattice(ix, iy, iz):
    """Pseudo random 0..1 at the integer lattice points (the hash of three large primes)."""
    h = (ix * 73856093 ^ iy * 19349663 ^ iz * 83492791) & 0xFFFF
    return h / 65535.0


def value_noise(p):
    """(n,) smooth value noise 0..1 at the points p (n, 3)."""
    i, f = np.floor(p).astype(np.int64), p - np.floor(p)
    f = f * f * (3 - 2 * f)
    out = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out = out + w * lattice(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz)
    return out


def brush(p, height):
    """(n,) -1..1: three octaves of low-frequency noise, the brush's unevenness."""
    q = p / height
    return sum(a * (2 * value_noise(q * f) - 1) for a, f in ((0.5, 5.0), (0.3, 11.0), (0.2, 23.0)))


def shade(P, N, base, occ, lo, height):
    """(n, 3) painted colours 0..255 of the surface points P with normals N, material colours `base` (n, 3) and occlusion `occ` (n,) 0..1."""
    gradient = 1 + GRADIENT * ((P[:, 2] - lo) / height - 0.5)
    light = 1 + LIGHT_GAIN * (np.clip(N @ LIGHT, 0, 1) - 0.5)
    mult = (gradient * light * (1 + BRUSH * brush(P, height)) * (1 - AO_GAIN * occ))[:, None]
    return np.clip(base * mult + LIFT * (mult - 1), 0, 255)      # the lift: a dark paint still has a light and a shadow


def kmeans(px, k, iters=10):
    """(k, 3) centres of k-means on px (n, 3): k-means++ starts from a fixed seed, deterministic."""
    rng = np.random.default_rng(0)
    sub = px[rng.choice(len(px), min(len(px), 20000), replace=False)]
    centres = [sub[rng.integers(len(sub))]]
    for _ in range(k - 1):
        d = np.min([((sub - c) ** 2).sum(1) for c in centres], axis=0)
        centres.append(sub[rng.choice(len(sub), p=d / d.sum())] if d.sum() > 0 else sub[0])
    centres = np.array(centres)
    for _ in range(iters):
        label = nearest(sub, centres)
        for c in range(k):
            if (label == c).any():
                centres[c] = sub[label == c].mean(0)
    return centres


def nearest(px, centres):
    return np.argmin(((px[:, None, :] - centres[None]) ** 2).sum(-1), axis=1)


def drawn_edges(pos, tri, tri2, slot, sharp, nrm, mat):
    """Boolean (E,): the sharp edges that are inked. A concave crease between one material is left to the occlusion; so is a crease within
    a tenth of a texel's worth of nothing: only edges that are convex or border two materials get a line."""
    a, sa, b = tri2[:, 0], slot[:, 0], tri2[:, 1]
    behind = ((pos[tri[b, (slot[:, 1] + 2) % 3]] - pos[tri[a, sa]]) * nrm[a]).sum(1) > 1e-6        # b's far corner above a's plane: concave
    return sharp & ~(behind & (mat[a] == mat[b]))


def ink_texels(uv, tri2, slot, sharp, tri_col, inside):
    """(ink (S, S), colour (S, S, 3)): the texels of `inside` within INK_D of a drawn edge, on the first triangle's side (the other face keeps its
    paint: a line on both would be half of a small island), in the colour of the triangle x .35; the row beside it, which is no ink, x 1.6 (the
    edge highlight). The ink mask is the dark line only."""
    ink, col = np.zeros((SIZE, SIZE), bool), np.zeros((SIZE, SIZE, 3))
    for t, s in zip(tri2[sharp][:, 0], slot[sharp][:, 0]):
        a, b = uv[t, s] * SIZE, uv[t, (s + 1) % 3] * SIZE
        if np.linalg.norm(b - a) < INK_MIN:
            continue
        lo, hi = np.floor(np.minimum(a, b) - 2).astype(int).clip(0, SIZE - 1), np.ceil(np.maximum(a, b) + 2).astype(int).clip(0, SIZE - 1)
        ys, xs = np.mgrid[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]
        p = np.stack([xs + 0.5, ys + 0.5], axis=-1) - a
        ab = b - a
        d = np.linalg.norm(p - np.clip((p @ ab) / max(ab @ ab, 1e-9), 0, 1)[..., None] * ab, axis=-1)
        line, light = (d <= INK_D) & inside[ys, xs], (d > INK_D) & (d <= INK_D + 1) & inside[ys, xs] & ~ink[ys, xs]
        col[ys[light], xs[light]] = np.clip(tri_col[t] * EDGE_LIGHT, 0, 255)
        col[ys[line], xs[line]] = tri_col[t] * INK_DARK
        ink[ys[line], xs[line]] = True
    return ink, col


def dilate(img, mask, iters=2):
    """Texels next to the painted ones take their colour: the island's pad, so a filtered lookup at the border finds paint."""
    img, mask = img.copy(), mask.copy()
    for _ in range(iters):
        grown = mask.copy()
        for axis, shift in ((0, 1), (0, -1), (1, 1), (1, -1)):
            src, ok = np.roll(img, shift, axis), np.roll(mask, shift, axis)
            take = ok & ~grown
            img[take], grown = src[take], grown | take
        mask = grown
    return img, mask


def keep_colour(shaded, base, mid):
    """`shaded` (n, 3) with every material's texels rescaled (0.7-1.5) so their mean luma is the material's own: the painting moves tones around
    the colour of the concept and does not darken it."""
    out = shaded.copy()
    for m in np.unique(mid):
        sel = mid == m
        out[sel] = np.clip(shaded[sel] * np.clip(base[sel][0] @ LUMA / max(shaded[sel].mean(0) @ LUMA, 1e-6), 0.7, 1.5), 0, 255)
    return out


def quantize(px, mid):
    """px (n, 3) cut to a hand-painted palette: each material gets its own 1-4 tones (k-means in sqrt space, the tone = the mean of its texels),
    in proportion to its share, so a small accent keeps its colour and does not melt into the big ones. About COLOURS tones in all."""
    out = px.copy()
    for m in np.unique(mid):
        sel = np.flatnonzero(mid == m)
        k = int(np.clip(round(len(sel) / len(px) * COLOURS * 1.5), 1, min(4, len(sel))))
        sq = np.sqrt(px[sel] / 255)
        label = nearest(sq, kmeans(sq, k))
        out[sel] = np.array([px[sel][label == c].mean(0) if (label == c).any() else 0 for c in range(k)])[label]
    return out


def bake(pos, tri, mat, colours, occlusion=None):
    """The painted model. pos (V, 3) world positions, tri (T, 3), mat (T,) material index, colours (M, 3) sRGB 0..255 per material, occlusion(P, N) -> (n,)
    0..1 or None. (uv (T, 3, 2) 0..1 v up, img (S, S, 3) uint8, used (S, S) bool, info)."""
    uv, (tri2, slot), sharp, nrm, n_isl, scale = unwrap(pos, tri, mat)
    mask, P, N, T = rasterize(uv, pos, tri, nrm)
    base = np.asarray(colours, float)[mat]
    height = max(pos[:, 2].max() - pos[:, 2].min(), 1e-6)
    occ = occlusion(P[mask], N[mask]) if occlusion else np.zeros(mask.sum())
    img = np.zeros((SIZE, SIZE, 3))
    img[mask] = shade(P[mask], N[mask], base[T[mask]], occ, pos[:, 2].min(), height)
    img[mask] = quantize(keep_colour(img[mask], base[T[mask]], mat[T[mask]]), mat[T[mask]])
    ink, painted = ink_texels(uv, tri2, slot, drawn_edges(pos, tri, tri2, slot, sharp, nrm, mat), base, mask)
    touched = painted.any(axis=-1)
    img[touched] = painted[touched]
    img, used = dilate(img, mask, 1)
    img[~used] = img[used].mean(0)
    info = {"islands": int(n_isl), "scale": round(float(scale), 2), "ink": round(float(ink.sum() / mask.sum()), 3),
            "tris": int(len(tri)), "texels": int(mask.sum())}
    return uv, np.clip(img, 0, 255).astype(np.uint8), mask, info


# ---------------------------------------------------------------- png
def write_png(path, arr):
    """An (h, w, 3|4) uint8 array as a PNG, top row last in memory = the file's bottom row (v up), no dependency."""
    arr = np.ascontiguousarray(arr[::-1])
    h, w, c = arr.shape
    raw = b"".join(b"\x00" + arr[y].tobytes() for y in range(h))

    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))
    pathlib.Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6 if c == 4 else 2, 0, 0, 0))
                                   + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


# ---------------------------------------------------------------- Blender
def srgb(c):
    c = np.clip(np.asarray(c, float), 0, 1)
    return 255 * np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


def ambient(pos, tri, height):
    """occlusion(P, N) -> (n,) 0..1: the share of 8 cosine-spread rays (0.15 H long) that hit the model, BVH rays of mathutils."""
    from mathutils.bvhtree import BVHTree
    tree = BVHTree.FromPolygons(pos.tolist(), tri.tolist())
    k = np.arange(8)
    z, phi = np.sqrt((k + 0.5) / 8), k * 2.399963
    local = np.stack([np.sqrt(1 - z * z) * np.cos(phi), np.sqrt(1 - z * z) * np.sin(phi), z], axis=1)

    def occlusion(P, N):
        helper = np.where(np.abs(N[:, 2:3]) < 0.9, [[0.0, 0.0, 1.0]], [[1.0, 0.0, 0.0]])
        u = np.cross(helper, N)
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        v = np.cross(N, u)
        dirs = local[None, :, 0:1] * u[:, None] + local[None, :, 1:2] * v[:, None] + local[None, :, 2:3] * N[:, None]
        origin = P + N * (height * 1e-3)
        hits = np.zeros(len(P))
        for i in range(len(P)):
            hits[i] = sum(tree.ray_cast(origin[i].tolist(), d.tolist(), 0.15 * height)[0] is not None for d in dirs[i])
        return hits / 8
    return occlusion


def body_of(bpy):
    bodies = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith(("outline", "face", "Icosphere"))]
    return bodies[0] if len(bodies) == 1 else None


def read_mesh(body):
    """(pos world (V, 3), tri (T, 3), loops (T, 3), mat (T,), colours (M, 3) sRGB) of the evaluated-free mesh."""
    mesh = body.data
    mesh.calc_loop_triangles()
    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", co)
    m = np.array(body.matrix_world)
    pos = co.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3]
    lt = mesh.loop_triangles
    tri, loops, mat = np.empty(len(lt) * 3, int), np.empty(len(lt) * 3, int), np.empty(len(lt), int)
    lt.foreach_get("vertices", tri)
    lt.foreach_get("loops", loops)
    lt.foreach_get("material_index", mat)
    colours = []
    for slot in body.material_slots:
        bsdf = slot.material.node_tree.nodes.get("Principled BSDF") if slot.material and slot.material.use_nodes else None
        colours.append(srgb(list(bsdf.inputs["Base Color"].default_value)[:3]) if bsdf else np.full(3, 128.0))
    return pos, tri.reshape(-1, 3), loops.reshape(-1, 3), mat, np.array(colours)


def paint_mesh(bpy, body, uv, loops, png):
    """UV layer from the baked triangles; every polygon on one material with the atlas."""
    mesh = body.data
    layer = mesh.uv_layers[0] if mesh.uv_layers else mesh.uv_layers.new(name="UVMap")
    arr = np.zeros((len(mesh.loops), 2))
    for k in range(3):
        arr[loops[:, k]] = uv[:, k]
    layer.data.foreach_set("uv", arr.ravel())
    mesh.materials.clear()
    mat = bpy.data.materials.new("paint")
    mat.use_nodes = True
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(png))
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9
    bsdf.inputs["Specular IOR Level"].default_value = 0.0
    mesh.materials.append(mat)
    mesh.polygons.foreach_set("material_index", np.zeros(len(mesh.polygons), int))


def main():
    import bpy
    src, out = sys.argv[sys.argv.index("--") + 1:][:2]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)
    body = body_of(bpy)
    if body is None:
        print("eye_paint: expected one body mesh")
        return
    pos, tri, loops, mat, colours = read_mesh(body)
    height = max(pos[:, 2].max() - pos[:, 2].min(), 1e-6)
    uv, img, used, info = bake(pos, tri, mat, colours, ambient(pos, tri, height))
    where = pathlib.Path(out).parent
    write_png(where / "atlas-rgb.png", img)
    write_png(where / "atlas.png", np.dstack([img, np.where(used, 255, 0).astype(np.uint8)]))
    paint_mesh(bpy, body, uv, loops, where / "atlas-rgb.png")
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_yup=True, export_animations=True,
                              export_animation_mode="ACTIONS", export_apply=False, export_skins=True, export_morph=False)
    print("eye_paint:", json.dumps(info))


# ---------------------------------------------------------------- python side
def apply(glb):
    """Paint `glb` in place (a Blender round trip); atlas.png lands beside it. The bake's info, {} when the file did not come out."""
    glb = pathlib.Path(glb)
    tmp = glb.with_name(f"{glb.stem}-paint.glb")
    tmp.unlink(missing_ok=True)
    done = subprocess.run(["nice", "-n", "10", "blender", "-b", "-P", str(HERE / "eye_paint.py"), "--", str(glb), str(tmp)], capture_output=True, text=True)
    (glb.parent / "atlas-rgb.png").unlink(missing_ok=True)
    line = next((ln for ln in done.stdout.splitlines() if ln.startswith("eye_paint: {")), None)
    if tmp.exists() and line:
        tmp.replace(glb)
        return json.loads(line[len("eye_paint:"):])
    return {}


def apply_stage(glb, paint):
    """The one call of eye_stage.finish: {} when paint is off."""
    return apply(glb) if paint == "on" else {}


def run_battery(args):
    """A copy of a run with the paint (and the contour) on its last round: eye_stage.finish's tail without the rounds."""
    import outline
    import eye_stage
    src = eye_stage.RUNS / args.id / args.src
    out = eye_stage.RUNS / args.id / args.tag
    eye_stage.seed(src, out)
    last = json.loads((src / "eye/summary.json").read_text())["final_round"]
    out.mkdir(parents=True, exist_ok=True)
    glb = out / "model.glb"
    glb.write_bytes((src / "eye" / f"round-{last}" / "model.glb").read_bytes())
    info = apply(glb)
    hull = args.outline in ("hull", "both") and outline.apply(glb)
    (out / "paint.json").write_text(json.dumps(dict(info, outline=args.outline, hull=bool(hull)), indent=1))
    print(args.id, args.tag, info, "hull" if hull else "no hull")
    return 0 if info else 1


def stats_of(run):
    """hive_sheet.texture_stats of a run's atlas.png (alpha = the texels the model samples)."""
    import hive_sheet
    from PIL import Image
    img = Image.open(pathlib.Path(run) / "atlas.png").convert("RGBA")
    return hive_sheet.texture_stats(img, np.asarray(img)[..., 3] > 128)


def sheet(unit):
    """history/2026-10-30-l17-paint/<unit>.png: concept | v16-r3 (flat + hull) | paint + hull | paint + ink | Hive, a row per view and one row of atlases."""
    import eye_stage
    import hive_sheet as H
    import make_compare as MC
    import review_pair
    from PIL import Image, ImageDraw
    runs = ("v16-r3", "v17-paint-hull", "v17-paint-ink")
    name = H.PAIRS.get(unit)
    cols = [("concept", None)] + [(r, H.shoot(H.DRAFT / unit / r / "model.glb", H.HIVE / "renders/ours" / f"{unit}-{r}", review_pair.run_tilt(H.DRAFT / unit / r)))
                                  for r in runs] + [(f"Hive {name}", {v: H.HIVE / "renders/views" / name / f"{name}-{v}.png" for v in H.VIEWS}) if name else ("no Hive pair", {})]
    with tempfile.TemporaryDirectory() as tmp:
        panels = review_pair.sheet_panels(unit, "mass", pathlib.Path(tmp))
        cw, ch = MC.CELL
        img = Image.new("RGB", (cw * len(cols), 20 + (ch + 20) * (len(H.VIEWS) + 1)), MC.BG)
        draw = ImageDraw.Draw(img)
        for x, (label, shots) in enumerate(cols):
            draw.text((x * cw + 6, 4), label, fill=(255, 255, 255))
            for y, view in enumerate(H.VIEWS):
                src = panels.get("rts" if view == "wc3" else view) if shots is None else shots.get(view)
                img.paste(eye_stage.cell(src) if src else MC.empty_cell("-"), (x * cw, 20 + y * (ch + 20)))
            atlas = H.DRAFT / unit / label / "atlas.png"
            if atlas.exists():
                img.paste(Image.open(atlas).convert("RGB").resize((ch, ch), Image.NEAREST), (x * cw, 20 + len(H.VIEWS) * (ch + 20)))
    out = ROOT / "artifacts/model-sheets/history/2026-10-30-l17-paint" / f"{unit}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.resize((img.width // 2, img.height // 2), Image.LANCZOS).save(out)
    return out


def cli(argv):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--id", required=True)
    r.add_argument("--from", dest="src", required=True)
    r.add_argument("--tag", required=True)
    r.add_argument("--outline", choices=("hull", "ink", "both"), default="hull")
    s = sub.add_parser("stats")
    s.add_argument("runs", nargs="+")
    sub.add_parser("sheet").add_argument("unit")
    args = ap.parse_args(argv)
    if args.cmd == "run":
        return run_battery(args)
    if args.cmd == "sheet":
        print(sheet(args.unit))
        return 0
    for run in args.runs:
        print(run, json.dumps(stats_of(run)))
    return 0


if __name__ == "__main__":
    if "-P" in sys.argv:        # blender -b -P eye_paint.py -- in out
        main()
    else:
        sys.exit(cli(sys.argv[1:]))
