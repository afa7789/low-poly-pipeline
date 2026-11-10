#!/usr/bin/env python3
"""L17-3: the eye stage's flat-colour pieces painted by hand, procedurally (PIPELINE 35.L17-3).

    blender -b -P tools/blender/eye_paint.py -- <in.glb> <out.glb> [grow|box] [on|off] [islands|palette] [64|128|256|auto]
                                                                          # + <out dir>/atlas.png (RGBA, alpha = the texels the model samples)
    eye_paint.apply(glb, charts, ink=False, atlas="islands", size="128")  # python side: --eye-paint on, in place, before outline.apply
    python3.14 tools/blender/eye_paint.py run --id n005 --from v16-r3 --tag v17-paint-hull [--outline hull|ink|both]
    python3.14 tools/blender/eye_paint.py stats <run dir>...              # hive_sheet.texture_stats of each run's atlas.png
    python3.14 tools/blender/eye_paint.py sheet <unit>                    # history/2026-10-30-l17-paint/<unit>.png

Works on the final GLB (one mesh, a primitive per material; a united mesh from L17-2 is the same shape): the triangles are grown into
islands (neighbours across a smooth edge, normal within 60 degrees of the seed, so a planar projection cannot fold), each island is flattened
on its seed's plane and the islands are shelf-packed into ONE square atlas (--eye-atlas-size: 64, 128 (default), 256 px, or auto = the
smallest multiple of 16 that holds the islands at AUTO_DENSITY texels over the model's height). Every texel is a point of the surface, so
the painting is a function of position and has no seam: the material colour x its ambient occlusion (BVH rays, in Blender) quantised to
AO_STEPS (light / mid / dark), so the atlas holds at most materials x 3 tones (author 2026-11-09: the 570 colours of the soft occlusion
became 36). With --eye-ink on the ink line is drawn: the edges with a dihedral over 40 degrees and the borders between materials, 1-2 texels
wide, in the material colour x .35 (not black). No model, no image from anywhere. The PNG is indexed (PLTE, 4 or 8 bits a texel) when
the atlas has at most 256 colours; eye_atlas.py then shares the flat islands and repacks the rest into the smallest atlas.

Author 2026-11-09: no lines between the pieces (--eye-ink off, the default: no ink texels, no edge highlight). --eye-atlas palette is the
swatch atlas: every triangle takes its piece's colour x its occlusion in 3 steps, at most materials x 3 swatches of 8 px cells in a 64 px
PNG (the Bob-omb practice: flat swatches, nothing drawn), the three UVs of a triangle at the centre of its cell, the glTF sampler NEAREST.
--eye-atlas islands (the default again, the author wants texel paint) keeps the texel atlas above.
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
SIZE = 128                  # the atlas, px, --eye-atlas-size (author 2026-11-09: 256 was the WC3 median and 20-27 KB a unit)
SIZES = ("64", "128", "256", "auto")
AUTO_DENSITY = 128          # auto: texels over the model's height (1 texel = 1/128 of the height), the atlas the smallest multiple of 16 that fits
AUTO_SIZES = range(32, 1025, 16)
PAD = 0                     # texels around every island (the rectangle has one texel of slack: islands never touch)
SHARP = np.cos(np.radians(40))      # dihedral over 40 degrees = a drawn edge
GROW = np.cos(np.radians(60))       # an island's normals stay within 60 degrees of its seed
INK_D = 0.75                # a texel centre within this of an edge is ink (a 1-2 texel line)
INK_MIN = 12 / 256          # an edge shorter than this share of the atlas side (12 texels at 256) is not drawn: it would be all ink
EDGE_LIGHT = 1.25           # the texel row inside the line: the material colour x 1.6, the hand-painted edge highlight
INK_DARK = 0.35             # ink = material colour x .35
COLOURS = 12                # the hand-painted palette of a model (eye_fuse's ceiling): the atlas holds at most COLOURS x len(AO_STEPS) tones
CHARTS = ("grow", "box")    # L18-3: grow = islands grown over smooth edges (L17-3, ~300 on a model of pieces); box = one chart per welded component and
                            # axis direction of the normal (6 at most per component: the united mesh of L18-2 gets a few large islands)
AXES = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], float)
ATLASES = ("islands", "palette")    # islands = the texel atlas above; palette = one 8 px swatch per (piece colour, occlusion step), author 2026-11-09
CELL, PALETTE_SIZE = 8, 64          # the swatch cell and the smallest palette atlas (64 px = 64 swatches; grows by whole cells when a model needs more)
AO_STEPS = ((0.3, 1.0), (0.65, 0.8), (1.01, 0.6))   # (occlusion below, colour multiplier): light, mid, dark (a united body is bimodal: open faces
                                                    # near 0, buried faces near 1; the band between is the crevices, cut in the middle)
AO_CAP = {"face": 0, "head": 1}     # author 2026-11-09 (dark blotches on the gnoll's face): the highest occlusion step of a piece by its DSL role: a face piece
                                    # (eyes, mask, muzzle) stays light, a head piece reaches mid at most; every other role reaches dark
DETAIL = 4                  # --eye-atlas-detail on: the bake at DETAIL x the atlas size; eye_atlas then gives every island its own density (the base is 1/DETAIL
                            # of the bake, an island with an accent detail or a busy pattern keeps up to the bake's) and packs the result
NEAREST = 9728                      # glTF sampler filter
LIFT = 20.0                 # 0..255 per unit of the multiplier's departure from 1: light and shadow do not vanish on a dark colour


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


def components(tri2, n):
    """Component id (T,) of every triangle over the shared edges (a welded mesh: the pieces of a united body are one)."""
    parent = np.arange(n)

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a, b in tri2:
        parent[find(a)] = find(b)
    roots = np.array([find(i) for i in range(n)])
    return np.unique(roots, return_inverse=True)[1].reshape(-1)


def islands_box(tri2, nrm):
    """(island id (T,), chart normal (K, 3)): box charts. Every triangle takes the axis its normal leans to; the triangles of one axis that touch
    across an edge are one chart (a projection on that axis plane: a planar cap is one island, a bent sleeve a few). Two charts of one axis
    never share a texel: triangles that do not touch are apart, so a fist in front of a forearm does not print on it."""
    axis = np.argmax(nrm @ AXES.T, axis=1)
    same = tri2[axis[tri2[:, 0]] == axis[tri2[:, 1]]]
    comp = components(same, len(nrm))
    uniq, isl = np.unique(comp * 6 + axis, return_inverse=True)
    return isl.reshape(-1), AXES[uniq % 6]


def flatten(pos, tri, nrm, isl, chart_n=None):
    """(flat (T, 3, 2) corner coordinates in world units, each island's min corner at its own origin; size (K, 2) of the islands).
    `chart_n` (K, 3): the projection plane of each island (box charts); default the seed triangle's normal."""
    flat, size = np.zeros((len(tri), 3, 2)), np.zeros((isl.max() + 1, 2))
    for k in range(isl.max() + 1):
        ts = np.flatnonzero(isl == k)
        n = chart_n[k] if chart_n is not None else (nrm[ts[0]] if np.linalg.norm(nrm[ts[0]]) > 0.5 else np.array([0.0, 0.0, 1.0]))
        u = np.cross([0.0, 0.0, 1.0] if abs(n[2]) < 0.9 else [1.0, 0.0, 0.0], n)
        u /= np.linalg.norm(u)
        q = pos[tri[ts]] @ np.stack([u, np.cross(n, u)], axis=1)
        span = np.ptp(q.reshape(-1, 2), axis=0)
        if span[0] < span[1]:                       # long side along u: shelves stay even (a rotation, no mirror)
            q, span = np.stack([q[..., 1], -q[..., 0]], axis=-1), span[::-1]
        flat[ts] = q - q.reshape(-1, 2).min(0)
        size[k] = span
    return flat, size


def shelf(px, size=SIZE):
    """Origins (K, 2) of the rectangles `px` (K, 2) on shelves of a `size` px atlas, tallest first; None when they do not fit."""
    org, x, y, row = np.zeros_like(px), 0, 0, 0
    for i in np.argsort(-px[:, 1], kind="stable"):
        w, h = px[i]
        if x + w > size:
            x, y, row = 0, y + row, 0
        if y + h > size or w > size:
            return None
        org[i] = (x, y)
        x, row = x + w, max(row, h)
    return org


def rects(size, scale):
    """(K, 2) texel rectangles of the islands `size` (K, 2) world units at `scale` texels a unit, PAD around and one texel of slack."""
    return np.ceil(size * scale).astype(int) + 1 + 2 * PAD


def fit(size, atlas=SIZE):
    """(scale texels per unit, origins): the largest scale whose islands, each with PAD texels around, shelf-pack into an `atlas` px atlas."""
    lo, hi, best = 0.0, atlas / max(size.max(), 1e-9), None
    for _ in range(24):
        mid = (lo + hi) / 2
        org = shelf(rects(size, mid), atlas)
        lo, hi, best = (mid, hi, (mid, org)) if org is not None else (lo, mid, best)
    return best


def fit_auto(size, height):
    """(scale, origins, atlas px): AUTO_DENSITY texels over the model's height, the smallest atlas of AUTO_SIZES that packs the islands at that
    scale (the largest one, at the scale that fits it, when none does)."""
    scale = AUTO_DENSITY / max(height, 1e-9)
    for atlas in AUTO_SIZES:
        org = shelf(rects(size, scale), atlas)
        if org is not None:
            return scale, org, atlas
    return (*fit(size, AUTO_SIZES[-1]), AUTO_SIZES[-1])


def unwrap(pos, tri, mat, charts="grow", size=SIZE):
    """(uv (T, 3, 2) in 0..1 with v up, tri2, sharp, nrm, island id (T,), scale, atlas px): the islands of the mesh packed in one atlas of
    `size` px (None: auto, see fit_auto)."""
    nrm = normals(pos, tri)[0]
    tri2, slot = shared_edges(weld(pos)[tri])
    sharp = sharp_edges(tri2, nrm, mat)
    if charts == "box":
        isl, chart_n = islands_box(tri2, nrm)
    else:
        isl, chart_n = islands(tri2, sharp, nrm), None
    flat, extent = flatten(pos, tri, nrm, isl, chart_n)
    scale, org, size = fit_auto(extent, np.ptp(pos[:, 2])) if size is None else (*fit(extent, size), size)
    px = (org[isl][:, None, :] + PAD + flat * scale) / size
    return px, (tri2, slot), sharp, nrm, isl, scale, size


# ---------------------------------------------------------------- texels
def rasterize(uv, pos, tri, nrm, size=SIZE):
    """(mask (S, S), P (S, S, 3), N (S, S, 3), T (S, S)): the surface point of every texel of a `size` px atlas the UV triangles cover; a
    triangle too small to cover a texel centre takes the texel of its centroid."""
    mask, P, N, T = np.zeros((size, size), bool), np.zeros((size, size, 3)), np.zeros((size, size, 3)), np.full((size, size), -1)
    for t in range(len(tri)):
        q = uv[t] * size
        lo, hi = np.floor(q.min(0)).astype(int), np.ceil(q.max(0)).astype(int)
        ys, xs = np.mgrid[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]
        w = bary(q, xs + 0.5, ys + 0.5)
        ok = (w >= -1e-6).all(0) if w is not None else np.zeros(xs.shape, bool)
        if not ok.any():
            xs, ys, ok, w = np.array([[int(q[:, 0].mean())]]), np.array([[int(q[:, 1].mean())]]), np.ones((1, 1), bool), np.full((3, 1, 1), 1 / 3)
        x, y = xs[ok], ys[ok]
        keep = (x >= 0) & (x < size) & (y >= 0) & (y < size)
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
    size = inside.shape[0]
    ink, col = np.zeros((size, size), bool), np.zeros((size, size, 3))
    for t, s in zip(tri2[sharp][:, 0], slot[sharp][:, 0]):
        a, b = uv[t, s] * size, uv[t, (s + 1) % 3] * size
        if np.linalg.norm(b - a) < INK_MIN * size:
            continue
        lo, hi = np.floor(np.minimum(a, b) - 2).astype(int).clip(0, size - 1), np.ceil(np.maximum(a, b) + 2).astype(int).clip(0, size - 1)
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


def nearest_piece(P, fields):
    """(n,) index in `fields` of the piece whose convex field is nearest to every surface point."""
    best, idx = np.full(len(P), np.inf), np.zeros(len(P), int)
    for i, f in enumerate(fields):
        d = (P @ np.asarray(f["n"], float).T - np.asarray(f["d"], float)).max(1)
        take = d < best
        best[take], idx[take] = d[take], i
    return idx


def texel_slots(P, fields):
    """(n,) material slot of every surface point: the slot of the piece whose convex field is nearest (L18-3: on a united mesh the triangles straddle
    two pieces and a per-triangle colour zigzags along the seam; the piece fields draw the seam where the pieces meet)."""
    return np.array([f["slot"] for f in fields])[nearest_piece(P, fields)]


def border_ink(mask, mid, isl_map):
    """(S, S) texels of `mask` next to a texel of a LOWER material slot inside the same island: the material border, one texel wide, drawn per texel."""
    out = np.zeros_like(mask)
    pm, pk, pi = (np.pad(a, 1, constant_values=c) for a, c in ((mid, -1), (mask, False), (isl_map, -2)))     # no wrap round the atlas
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        sl = (slice(1 + dy, 1 + dy + mask.shape[0]), slice(1 + dx, 1 + dx + mask.shape[1]))
        out |= mask & pk[sl] & (pi[sl] == isl_map) & (pm[sl] < mid)
    return out


def bake(pos, tri, mat, colours, occlusion=None, charts="grow", fields=None, ink=True, size=SIZE, caps=None):
    """The painted model. pos (V, 3) world positions, tri (T, 3), mat (T,) material index, colours (M, 3) sRGB 0..255 per material, occlusion(P, N) -> (n,)
    0..1 or None, charts: CHARTS, fields: eye_skin's piece fields (texel material by the nearest piece) or None (by triangle); ink False = no line
    and no edge highlight (author 2026-11-09): the flat tones, the occlusion and the accents stay. size: the atlas px, None = auto (fit_auto).
    Every texel = its material's colour x its occlusion step (AO_STEPS: at most materials x 3 tones, author 2026-11-09); caps (P,) the highest step
    of every piece of `fields` (AO_CAP by role) or None.
    (uv (T, 3, 2) 0..1 v up, img (S, S, 3) uint8, used (S, S) bool, info with islands and texels per island, median)."""
    uv, (tri2, slot), sharp, nrm, isl, scale, size = unwrap(pos, tri, mat, charts, size)
    n_isl = int(isl.max()) + 1
    mask, P, N, T = rasterize(uv, pos, tri, nrm, size)
    base = np.asarray(colours, float)[mat]
    occ = occlusion(P[mask], N[mask]) if occlusion else np.zeros(mask.sum())
    which = nearest_piece(P[mask], fields) if fields else None
    mid = np.full((size, size), -1)
    mid[mask] = np.array([f["slot"] for f in fields])[which] if fields else mat[T[mask]]
    tex_base = np.asarray(colours, float)[np.clip(mid, 0, None)]
    step = ao_step(occ)
    if fields and caps is not None:
        step = np.minimum(step, np.asarray(caps)[which])
    img = np.zeros((size, size, 3))
    img[mask] = swatch_colour(tex_base[mask], step)
    lines = ink_lines(img, uv, pos, tri, mat, base, tex_base, mask, mid, isl, T, tri2, slot, sharp, nrm, fields) if ink else np.zeros((size, size), bool)
    img, used = dilate(img, mask, 1)
    img[~used] = img[used].mean(0)
    per_island = np.bincount(isl[T[mask]], minlength=n_isl)
    claimed = np.zeros((size, size), int)
    for q in uv * size:                                     # texels two triangles both cover: the leak of an overlapping chart (0 by construction)
        lo, hi = np.floor(q.min(0)).astype(int).clip(0, size - 1), np.ceil(q.max(0)).astype(int).clip(0, size - 1)
        ys, xs = np.mgrid[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]
        w = bary(q, xs + 0.5, ys + 0.5)
        if w is not None:
            inside = (w > 1e-6).all(0)
            claimed[ys[inside], xs[inside]] += 1
    info = {"islands": int(n_isl), "scale": round(float(scale), 2), "size": int(size), "texels_per_height": round(float(scale * np.ptp(pos[:, 2])), 1),
            "ink": round(float(lines.sum() / mask.sum()), 3), "charts": charts, "atlas": "islands", "tris": int(len(tri)), "texels": int(mask.sum()),
            "coverage": round(float(mask.mean()), 3), "colours": int(len(np.unique(np.clip(img, 0, 255).astype(np.uint8).reshape(-1, 3), axis=0))),
            "texels_per_island_median": float(np.median(per_island)), "texels_per_island_min": int(per_island.min()),
            "islands_micro": int((per_island <= 4).sum()), "overlap_texels": int((claimed > 1).sum())}
    return uv, np.clip(img, 0, 255).astype(np.uint8), mask, info


def ink_lines(img, uv, pos, tri, mat, base, tex_base, mask, mid, isl, T, tri2, slot, sharp, nrm, fields):
    """The ink of L17-3 drawn into `img` in place: the lines along the drawn edges (and the edge highlight beside them), plus the material
    border per texel on a united mesh. The mask of the dark line."""
    edges = drawn_edges(pos, tri, tri2, slot, sharp, nrm, mat)
    if fields:
        edges &= mat[tri2[:, 0]] == mat[tri2[:, 1]]          # the material border is drawn per texel below, not along the triangles
    ink, painted = ink_texels(uv, tri2, slot, edges, base, mask)
    touched = painted.any(axis=-1)
    img[touched] = painted[touched]
    if fields:
        isl_map = np.full(mask.shape, -1)
        isl_map[mask] = isl[T[mask]]
        line = border_ink(mask, mid, isl_map)
        img[line] = tex_base[line] * INK_DARK
        ink |= line
    return ink


# ---------------------------------------------------------------- palette atlas (author 2026-11-09)
def triangle_occlusion(pos, tri, nrm, occlusion):
    """(T,) mean occlusion 0..1 of every triangle: four surface points (the centroid and the midpoints between it and the corners), or 0 without `occlusion`."""
    if occlusion is None:
        return np.zeros(len(tri))
    corners = pos[tri]                                  # (T, 3, 3)
    centre = corners.mean(1)
    pts = np.concatenate([centre, *((centre + corners[:, k]) / 2 for k in range(3))])
    occ = occlusion(pts, np.tile(nrm, (4, 1)))
    return occ.reshape(4, -1).mean(0)


def ao_step(occ):
    """(n,) 0 light, 1 mid, 2 dark: the occlusion quantised to AO_STEPS."""
    return np.searchsorted([t for t, _ in AO_STEPS[:-1]], occ, side="right")


def swatch_colour(base, step):
    """(n, 3) the piece colour `base` under the occlusion step, LIFT keeping a shadow on dark paint."""
    mult = np.array([m for _, m in AO_STEPS])[step][:, None]
    return np.clip(base * mult + LIFT * (mult - 1), 0, 255)


def bake_palette(pos, tri, mat, colours, occlusion=None, fields=None):
    """The swatch atlas: every triangle = one cell of its (piece colour, occlusion step), the three UVs at the cell's centre, no texel of the surface.
    fields: the triangle's piece by its centroid's nearest field (a united mesh), else its material. Same return as bake: uv (T, 3, 2) v up,
    img (S, S, 3) uint8, used (S, S) bool, info."""
    nrm = normals(pos, tri)[0]
    centroid = pos[tri].mean(1)
    slot = texel_slots(centroid, fields) if fields else mat
    step = ao_step(triangle_occlusion(pos, tri, nrm, occlusion))
    key, idx = np.unique(slot * 3 + step, return_inverse=True)
    idx = idx.reshape(-1)
    cols = max(PALETTE_SIZE // CELL, int(np.ceil(np.sqrt(len(key)))))
    size = cols * CELL
    tones = swatch_colour(np.asarray(colours, float)[key // 3], key % 3)
    img, used = np.zeros((size, size, 3)), np.zeros((size, size), bool)
    img[:] = tones.mean(0)                              # the empty cells: not black
    for k, tone in enumerate(tones):
        x, y = (k % cols) * CELL, (k // cols) * CELL
        img[y:y + CELL, x:x + CELL], used[y:y + CELL, x:x + CELL] = tone, True
    centre = (np.stack([idx % cols, idx // cols], axis=1) * CELL + CELL / 2) / size     # the cell's centre: 4 texels from any border
    uv = np.repeat(centre[:, None, :], 3, axis=1)
    info = {"atlas": "palette", "swatches": int(len(key)), "size": int(size), "materials": int(len(np.unique(slot))), "tris": int(len(tri)),
            "steps": np.bincount(step, minlength=3).tolist(), "ink": 0.0, "fields": fields is not None}
    return uv, np.clip(img, 0, 255).astype(np.uint8), used, info


def read_glb(path):
    """(json, bin) of a .glb (hive_sheet.read_glb, here without its imports: this runs inside Blender too)."""
    d = pathlib.Path(path).read_bytes()
    n = struct.unpack_from("<I", d, 12)[0]
    m = struct.unpack_from("<I", d, 20 + n)[0]
    return json.loads(d[20:20 + n]), d[28 + n:28 + n + m]


def write_glb(path, j, blob):
    head = json.dumps(j, separators=(",", ":")).encode()
    head += b" " * ((-len(head)) % 4)
    blob += b"\0" * ((-len(blob)) % 4)
    pathlib.Path(path).write_bytes(b"glTF" + struct.pack("<II", 2, 28 + len(head) + len(blob)) + struct.pack("<I", len(head)) + b"JSON" + head
                                   + struct.pack("<I", len(blob)) + b"BIN\0" + blob)


def set_nearest(glb):
    """Every sampler of `glb` NEAREST / NEAREST, no mipmaps: a swatch cell is sampled whole (raylib ignores the sampler and already filters POINT)."""
    j, blob = read_glb(glb)
    j["samplers"] = [{"magFilter": NEAREST, "minFilter": NEAREST} for _ in (j.get("samplers") or [{}])]
    for t in j.get("textures", []):
        t["sampler"] = 0
    write_glb(glb, j, blob)


def atlas_bytes(glb):
    """Bytes of the first image embedded in `glb` (0 without one)."""
    j, _ = read_glb(glb)
    return int(j["bufferViews"][j["images"][0]["bufferView"]]["byteLength"]) if j.get("images") else 0


# ---------------------------------------------------------------- png
def png_chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))


def png_indexed(arr):
    """(PLTE bytes, (h, w) indices, bit depth 4 or 8) of an (h, w, 3) uint8 array with at most 256 colours; None over that."""
    pal, idx = np.unique(arr.reshape(-1, 3), axis=0, return_inverse=True)
    if len(pal) > 256:
        return None
    return pal.astype(np.uint8).tobytes(), idx.reshape(arr.shape[:2]).astype(np.uint8), 4 if len(pal) <= 16 else 8


def png_rows(idx, depth):
    """The filter-0 scanlines of (h, w) indices at `depth` bits: two texels a byte at 4 bits (an odd row padded)."""
    if depth == 4:
        if idx.shape[1] % 2:
            idx = np.pad(idx, ((0, 0), (0, 1)))
        idx = idx[:, 0::2] * 16 + idx[:, 1::2]
    return b"".join(b"\x00" + row.astype(np.uint8).tobytes() for row in idx)


def png_bytes(arr):
    """An (h, w, 3|4) uint8 array as PNG bytes, row 0 first, zlib 9, no dependency: colour type 3 (PLTE, 4 or 8 bits a texel) when an RGB array has at
    most 256 colours (author 2026-11-09: the indexed atlas), else type 2 (RGB) or 6 (RGBA)."""
    arr = np.ascontiguousarray(arr)
    h, w, c = arr.shape
    indexed = png_indexed(arr) if c == 3 else None
    if indexed:
        plte, idx, depth = indexed
        head, raw, extra = struct.pack(">IIBBBBB", w, h, depth, 3, 0, 0, 0), png_rows(idx, depth), png_chunk(b"PLTE", plte)
    else:
        head, raw, extra = struct.pack(">IIBBBBB", w, h, 8, 6 if c == 4 else 2, 0, 0, 0), b"".join(b"\x00" + arr[y].tobytes() for y in range(h)), b""
    return b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", head) + extra + png_chunk(b"IDAT", zlib.compress(raw, 9)) + png_chunk(b"IEND", b"")


def write_png(path, arr):
    """png_bytes of `arr` to `path`, top row last in memory = the file's bottom row (v up)."""
    pathlib.Path(path).write_bytes(png_bytes(arr[::-1]))


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


def paint_mesh(bpy, body, uv, loops, png, nearest=False):
    """UV layer from the baked triangles; every polygon on one material with the atlas. nearest: point filter (exported as a NEAREST sampler)."""
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
    if nearest:
        tex.interpolation = "Closest"
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9
    bsdf.inputs["Specular IOR Level"].default_value = 0.0
    mesh.materials.append(mat)
    mesh.polygons.foreach_set("material_index", np.zeros(len(mesh.polygons), int))


def main():
    import bpy
    src, out, *rest = sys.argv[sys.argv.index("--") + 1:]
    charts, ink, atlas, size, detail = (rest + ["grow", "on", "islands", str(SIZE), "off"][len(rest):])[:5]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)
    body = body_of(bpy)
    if body is None:
        print("eye_paint: expected one body mesh")
        return
    pos, tri, loops, mat, colours = read_mesh(body)
    height = max(pos[:, 2].max() - pos[:, 2].min(), 1e-6)
    where = pathlib.Path(out).parent
    fields = read_fields(where / "fields.json", [slot.material.name if slot.material else "" for slot in body.material_slots])
    if atlas == "palette":
        uv, img, used, info = bake_palette(pos, tri, mat, colours, ambient(pos, tri, height), fields)
    else:
        px = None if size == "auto" else int(size) * (DETAIL if detail == "on" else 1)
        uv, img, used, info = bake(pos, tri, mat, colours, ambient(pos, tri, height), charts, fields, ink=ink != "off", size=px, caps=read_caps(where / "eye/fused.dsl.json", fields))
    info["fields"] = fields is not None
    info["detail"] = detail == "on"
    write_png(where / "atlas-rgb.png", img)
    write_png(where / "atlas.png", np.dstack([img, np.where(used, 255, 0).astype(np.uint8)]))
    paint_mesh(bpy, body, uv, loops, where / "atlas-rgb.png", nearest=atlas == "palette")
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_yup=True, export_animations=True,
                              export_animation_mode="ACTIONS", export_apply=False, export_skins=True, export_morph=False)
    if atlas == "palette":
        set_nearest(out)
    info["atlas_bytes"] = atlas_bytes(out)
    print("eye_paint:", json.dumps(info))


def read_fields(path, slot_names):
    """The piece fields eye_skin left beside a united model (L18-3), their slots mapped to this GLB's material order; None without the file
    or when a material of the build is not in the GLB (the pieces cannot be matched)."""
    if not pathlib.Path(path).exists():
        return None
    doc = json.loads(pathlib.Path(path).read_text())
    names = [n.split(".")[0] for n in slot_names]
    if any(m not in names for m in doc["materials"]):
        return None
    remap = [names.index(m) for m in doc["materials"]]
    return [dict(f, slot=remap[f["slot"]]) for f in doc["pieces"]]


def read_caps(path, fields):
    """(P,) the highest occlusion step of every piece of `fields` by its role in the fused DSL beside the model (AO_CAP; the fields and the DSL list the pieces
    in one order); None without the file, without fields or when the counts differ."""
    if fields is None or not pathlib.Path(path).exists():
        return None
    pieces = json.loads(pathlib.Path(path).read_text()).get("pieces", [])
    if len(pieces) != len(fields):
        return None
    return np.array([AO_CAP.get(p.get("role"), len(AO_STEPS) - 1) for p in pieces])


# ---------------------------------------------------------------- python side
def apply(glb, charts="grow", ink=True, atlas="islands", size=str(SIZE), detail=False):
    """Paint `glb` in place (a Blender round trip); atlas.png lands beside it. ink False: no line, no edge highlight; atlas: ATLASES; size: SIZES;
    detail: the bake at DETAIL x `size` (eye_atlas resamples the islands). The bake's info, {} when the file did not come out."""
    glb = pathlib.Path(glb)
    tmp = glb.with_name(f"{glb.stem}-paint.glb")
    tmp.unlink(missing_ok=True)
    done = subprocess.run(["nice", "-n", "10", "blender", "-b", "-P", str(HERE / "eye_paint.py"), "--", str(glb), str(tmp), charts, "on" if ink else "off", atlas, str(size),
                           "on" if detail else "off"], capture_output=True, text=True)
    (glb.parent / "atlas-rgb.png").unlink(missing_ok=True)
    line = next((ln for ln in done.stdout.splitlines() if ln.startswith("eye_paint: {")), None)
    if tmp.exists() and line:
        tmp.replace(glb)
        return json.loads(line[len("eye_paint:"):])
    return {}


def apply_stage(glb, paint, ink="off", atlas="islands", size=str(SIZE), detail="off"):
    """The one call of eye_stage.finish: {} when paint is off; "on" = grown islands (L17-3), "box" = box charts per component (L18-3).
    ink / atlas / size / detail: --eye-ink, --eye-atlas, --eye-atlas-size, --eye-atlas-detail (author 2026-11-09; charts, size and detail only matter to the islands atlas)."""
    return apply(glb, "box" if paint == "box" else "grow", ink=ink == "on", atlas=atlas, size=size, detail=detail == "on") if paint in ("on", "box") else {}


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
