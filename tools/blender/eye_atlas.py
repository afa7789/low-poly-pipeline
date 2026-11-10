#!/usr/bin/env python3
"""The texel atlas compacted after the paint and the projection (author 2026-11-09: the islands covered 28-44 % of a 256 px atlas).

    python3.14 tools/blender/eye_atlas.py <model.glb> [--dry] [--unit hfoo] [--base 4]     # in place: UVs rewritten, the embedded PNG replaced, atlas.png (RGBA) beside it
    eye_atlas.apply_stage(glb, unit, base)                                                  # eye_stage.finish, after eye_project, before the contour

An island = one connected set of vertices of the exported mesh (the exporter splits the vertices at the UV seams, so an island is one chart).
0. Palette (author 2026-11-09, "quanto menos cores melhor"; with `base` > 1, the detail recipe): the body texels (every piece that is no accent, eye_project.accents, nor a face piece) merged to
   at most BODY_COLOURS colours (OKLab k-means weighted by texel count, each cluster painted its most used colour); an accent piece keeps its own colours,
   at most ACCENT_TONES of them (its most used; the rest go to the nearest kept one).
1. Density (author 2026-11-09, --eye-atlas-detail: the bake at eye_paint.DETAIL x the atlas size, `base` = DETAIL here): every island is resampled to its
   own density. A body island: 1/base of the bake (f x f blocks, the block's most used colour: no ramp, every texel a palette colour). A busy island (colour
   edges over BUSY a texel: the faerie dragon's wing stripes, the footman's belts): twice that. An island with an accent detail (an accent piece under
   ACC_SHARE of its texels: an eye on a head, a buckle on a belt): the bake's density, and 2x upsampled when the detail is under ACC_MIN texels of side.
   When the leaders do not pack into DETAIL_MAX px, the costliest promoted island falls back a step until they do (the eyes are the smallest, so the last).
2. Sharing: an island of one colour (a body island: one colour over FLAT_SHARE of it) maps to a CELL x CELL cell of that colour, one cell per colour (its
   UVs collapse to the cell's centre). Two islands with the same texels (NEAR of them equal within SHARE_DE OKLab, straight or mirrored in x or y: the
   L / R pieces of a symmetric body) share one rectangle: the follower's UVs land in the leader's rectangle, flipped.
3. Packing: the remaining islands as texel bitmaps, largest first, each at the top-left-most origin GAP texels from every placed texel (an FFT correlation of
   the two bitmaps finds the free origins; either way up), so an L-shaped box chart no longer costs its bounding box; the atlas the smallest multiple of 16
   that holds them. Every island's colour is dilated one texel into its gutter and the sampler is NEAREST: a lookup at a border never finds the fill colour.
4. The PNG indexed (eye_paint.png_bytes: PLTE, 4 or 8 bits a texel) when it has at most 256 colours.
No Blender: the GLB's TEXCOORD_0, its one image and its samplers change, nothing else.
"""
import io
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import eye_paint  # noqa: E402
import eye_project  # noqa: E402

CELL = 2                    # texels of a shared flat cell: its centre is a texel corner, bilinear or point, the cell's colour
SIZES = range(16, 2049, 16)
GAP = 2                     # texels between two islands: each one's own 1-texel dilation never reaches the other
NEAR = 0.95                 # two islands with this share of equal texels (straight or mirrored) share one rectangle
SHARE_DE = 0.04             # two texels this near in OKLab count as equal when two islands are compared
FLIPS = ((False, False), (True, False), (False, True), (True, True))
DETAIL_MAX = 96             # the side the detail atlas must fit: promoted islands fall back a step, costliest first, until it does
BUSY = 0.3                  # colour edges a texel between 4-neighbours at the bake (OKLab a, b over EDGE_AB or L over EDGE_L): a busy island keeps 2x the base density
EDGE_AB, EDGE_L = 0.025, 0.22   # an occlusion step moves L by ~.12-.15 and a, b not at all; a piece border does more
ACC_SHARE = 0.3             # an accent piece under this share of its island is a detail in it: the island keeps the bake's density
DETAIL_PIECE = 0.02         # ... and under this share of the model's texels (an eye, a buckle, a flame, a forehead mark; not a leg or a wing panel)
FACE_ROLES = ("face",)      # DSL roles whose pieces are protected like the colour accents (a pale eye is no saturated colour, it is a detail all the same)
STEP = 0.1                  # the demotion loop drops this share of the texels before it tries the pack again
ACC_MIN, UP_MAX = 4, 32     # a detail under ACC_MIN texels of side is upsampled 2x (nearest) when its island is at most UP_MAX texels of side at the bake
FLAT_SHARE = 0.85           # a body island with one colour over this share of its texels is a flat cell of that colour
BODY_COLOURS = 12           # the body merged to at most this many colours
ACCENT_TONES = 1            # an accent piece keeps its two most used colours (its light and mid steps as a rule); its other tones go to the nearest kept one (OKLab)


# ---------------------------------------------------------------- the model
def read_model(glb):
    """(json, blob, pos (V, 3), tri (T, 3), uv (V, 2) glTF v down, img (S, S, 3) uint8 row 0 = v 0) of a painted GLB; None without one mesh, one primitive, one image."""
    from PIL import Image
    import hive_sheet as H
    j, blob = eye_paint.read_glb(glb)
    if len(j.get("meshes", [])) != 1 or len(j["meshes"][0]["primitives"]) != 1 or not j.get("images"):
        return None
    prim = j["meshes"][0]["primitives"][0]
    pos = H.accessor(j, blob, prim["attributes"]["POSITION"]).astype(float)
    tri = H.accessor(j, blob, prim["indices"]).reshape(-1, 3).astype(int)
    uv = H.accessor(j, blob, prim["attributes"]["TEXCOORD_0"]).astype(float)
    view = j["bufferViews"][j["images"][0]["bufferView"]]
    png = blob[view.get("byteOffset", 0):view.get("byteOffset", 0) + view["byteLength"]]
    img = np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))
    return j, bytearray(blob), pos, tri, uv, img


def vertex_islands(tri, n):
    """(V,) island id of every vertex: the connected components over the triangles."""
    return eye_paint.components(np.concatenate([tri[:, :2], tri[:, 1:]]), n)


def texel_islands(uv, pos, tri, isl_v, size):
    """(used (S, S), isl_map (S, S) island id or -1, P (S, S, 3) surface point) of the atlas texels the triangles cover."""
    uvt = uv[tri]
    used, P, _, T = eye_paint.rasterize(uvt, pos, tri, eye_paint.normals(pos, tri)[0], size)
    isl_map = np.full((size, size), -1)
    isl_map[used] = isl_v[tri[T[used], 0]]
    return used, isl_map, P


def colour_key(img):
    """(S, S) int64 one number per colour."""
    c = img.astype(np.int64)
    return c[..., 0] * 65536 + c[..., 1] * 256 + c[..., 2]


def key_rgb(key):
    """(..., 3) the colour of every key."""
    k = np.asarray(key)
    return np.stack([k // 65536, k // 256 % 256, k % 256], -1)


def key_lab(key):
    return eye_project.to_oklab(key_rgb(key))


def pieces_of(glb, unit, used, P):
    """(piece (S, S) index or -1, accent (P,) bool, small (P,) bool, names) of the atlas texels by eye_skin's fields beside the GLB and the fused DSL
    (eye_project.read_parts): accent = a colour accent (eye_project.accents) or a FACE_ROLES piece, protected from the palette merge; small = under DETAIL_PIECE
    of the texels (an accent that is small is a detail). (None, None, None, []) without the files."""
    where = pathlib.Path(glb).parent
    if unit is None or not (where / "fields.json").exists() or not (where / "eye/fused.dsl.json").exists():
        return None, None, None, []
    try:
        fields, rgb, names, identity = eye_project.read_parts(where, unit)
    except SystemExit:
        return None, None, None, []
    roles = [p.get("role") for p in json.loads((where / "eye/fused.dsl.json").read_text())["pieces"]]
    pz = np.c_[P[used][:, 0], -P[used][:, 2], P[used][:, 1]]        # glTF Y up -> the fields' Z up
    piece = eye_paint.nearest_piece(pz, fields)
    pm = np.full(used.shape, -1)
    pm[used] = piece
    count = np.bincount(piece, minlength=len(rgb)).astype(float)
    accent = eye_project.accents(rgb, count, identity) | np.array([r in FACE_ROLES for r in roles])
    return pm, accent, count <= DETAIL_PIECE * count.sum(), names


# ---------------------------------------------------------------- the palette
def merge_palette(img, body, k=BODY_COLOURS):
    """(img, colours before, after): the colours of the `body` texels clustered to at most k in OKLab (k-means weighted by texel count), every cluster painted
    its most used colour. The other texels keep theirs."""
    key = colour_key(img)
    keys, cnt = np.unique(key[body], return_counts=True)
    if len(keys) <= k:
        return img, len(keys), len(keys)
    lab = key_lab(keys)
    centres = eye_paint.kmeans(np.repeat(lab, cnt, axis=0), k)
    label = eye_paint.nearest(lab, centres)
    table = {}
    for c in np.unique(label):
        members = np.flatnonzero(label == c)
        pick = keys[members[np.argmax(cnt[members])]]
        table.update({int(keys[m]): int(pick) for m in members})
    merged = np.vectorize(table.__getitem__)(key[body])
    out = img.copy()
    out[body] = key_rgb(merged)
    return out, len(keys), len(set(table.values()))


def cap_tones(img, pm, accent, used, k=ACCENT_TONES):
    """img with every accent piece on at most k colours: its k most used texel colours kept, the others moved to the nearest kept one in OKLab."""
    out, key = img.copy(), colour_key(img)
    for p in np.nonzero(accent)[0]:
        sel = used & (pm == p)
        keys, cnt = np.unique(key[sel], return_counts=True)
        if len(keys) <= k:
            continue
        kept = keys[np.argsort(-cnt, kind="stable")[:k]]
        to = kept[eye_paint.nearest(key_lab(keys), key_lab(kept))]
        out[sel] = key_rgb(to[np.searchsorted(keys, key[sel])])
    return out


# ---------------------------------------------------------------- the islands
def islands_of(img, isl_map, n):
    """One dict per island with texels: id, x0, y0, w, h (its texel bounding box at the bake), key (h, w) colour keys with -1 off the island, texels, flat
    (colour key or None), f 1."""
    key, out = colour_key(img), []
    for k in range(n):
        ys, xs = np.nonzero(isl_map == k)
        if not len(ys):
            continue
        y0, x0, h, w = ys.min(), xs.min(), np.ptp(ys) + 1, np.ptp(xs) + 1
        crop = np.where(isl_map[y0:y0 + h, x0:x0 + w] == k, key[y0:y0 + h, x0:x0 + w], -1)
        out.append({"id": k, "x0": int(x0), "y0": int(y0), "w": int(w), "h": int(h), "key": crop, "texels": int(len(ys)), "flat": flat_of(crop, False), "f": 1})
    return out


def flat_of(key, body):
    """The colour key of a flat island: one colour, or (a body island) one colour over FLAT_SHARE of its texels; None otherwise."""
    tones, cnt = np.unique(key[key >= 0], return_counts=True)
    if len(tones) == 1 or (body and cnt.max() >= FLAT_SHARE * cnt.sum()):
        return int(tones[cnt.argmax()])
    return None


def busyness(key):
    """Colour edges a texel of an island: 4-neighbour pairs over EDGE_AB in OKLab a, b or over EDGE_L in L."""
    on = key >= 0
    lab = np.zeros(key.shape + (3,))
    lab[on] = key_lab(key[on])
    edges = 0
    for ax in (0, 1):
        a, b = np.moveaxis(lab, ax, 0)[1:], np.moveaxis(lab, ax, 0)[:-1]
        oa, ob = np.moveaxis(on, ax, 0)[1:], np.moveaxis(on, ax, 0)[:-1]
        d = a - b
        edges += int((oa & ob & ((np.hypot(d[..., 1], d[..., 2]) > EDGE_AB) | (np.abs(d[..., 0]) > EDGE_L))).sum())
    return edges / max(int(on.sum()), 1)


def accent_detail(isl, isl_map, pm, accent, small):
    """The smallest bounding side of an accent piece that is a detail in the island (a small piece under ACC_SHARE of the island's texels); 0 without one."""
    if pm is None:
        return 0
    y0, x0, h, w = isl["y0"], isl["x0"], isl["h"], isl["w"]
    crop = np.where(isl_map[y0:y0 + h, x0:x0 + w] == isl["id"], pm[y0:y0 + h, x0:x0 + w], -1)
    side = 0
    for p in np.unique(crop[crop >= 0]):
        sel = crop == p
        if not (accent[p] and small[p]) or sel.sum() >= ACC_SHARE * isl["texels"]:
            continue
        ys, xs = np.nonzero(sel)
        s = int(min(np.ptp(ys) + 1, np.ptp(xs) + 1))
        side = s if side == 0 else min(side, s)
    return side


def factors(islands, isl_map, pm, accent, small, base):
    """{island id: (factor, kind)}: a body island at `base` (bake texels an atlas texel); a busy one at half of it; one with an accent detail at 1, or .5
    (2x upsampled) when the detail is under ACC_MIN texels of side in an island up to UP_MAX of side. base 1 (no detail bake): every factor 1."""
    out = {}
    for isl in islands:
        f, kind = base, "body"
        if isl["flat"] is None:
            side = accent_detail(isl, isl_map, pm, accent, small)
            if side:
                f, kind = (0.5 if base > 1 and side < ACC_MIN and max(isl["w"], isl["h"]) <= UP_MAX else 1), "accent"
            elif busyness(isl["key"]) >= BUSY:
                f, kind = max(base / 2, 1), "busy"
        out[isl["id"]] = (f, kind)
    return out


def downsample(key, f):
    """(h', w') the keys of `key` (h, w; -1 off the island) in f x f blocks: the block's most used island colour, -1 for a block with none."""
    h, w = key.shape
    H, W = -(-h // f), -(-w // f)
    pad = np.full((H * f, W * f), -1, dtype=key.dtype)
    pad[:h, :w] = key
    blk = pad.reshape(H, f, W, f).transpose(0, 2, 1, 3).reshape(H, W, f * f)
    on = blk >= 0
    counts = np.stack([((blk == blk[..., [k]]) & on).sum(-1) * on[..., k] for k in range(f * f)], -1)
    best = np.take_along_axis(blk, counts.argmax(-1)[..., None], -1)[..., 0]
    return np.where(on.any(-1), best, -1)


def resample(isl, f, body):
    """The island at 1/f of the bake's density (f > 1: blocks, see downsample; f < 1: every texel repeated), its w, h, texels and flat (flat_of) following."""
    key = isl["key"]
    if f > 1:
        key = downsample(key, int(f))
    elif f < 1:
        r = int(round(1 / f))
        key = np.repeat(np.repeat(key, r, 0), r, 1)
    return dict(isl, f=f, key=key, w=key.shape[1], h=key.shape[0], texels=int((key >= 0).sum()), flat=flat_of(key, body))


def budget(islands, isl_map, pm, accent, small, base):
    """(resampled islands, {id: (factor, kind)}, demoted): every island at its factor; while the leaders do not pack into DETAIL_MAX px the costliest promoted
    islands (most texels at their density, STEP of the texels a round) fall back a step and are resampled."""
    fk = factors(islands, isl_map, pm, accent, small, base)
    by_id = {i["id"]: i for i in islands}
    res = {k: resample(by_id[k], f, base > 1 and kind == "body") for k, (f, kind) in fk.items()}
    demoted = 0
    while base > 1:
        cells, leaders, followers, _ = plan(list(res.values()))
        if pack(masks_of(leaders, cells), DETAIL_MAX) is not None:
            break
        cand = sorted((r for r in res.values() if r["f"] < base and r["flat"] is None and r["id"] not in followers), key=lambda r: -r["texels"])
        if not cand:
            break
        goal, dropped = STEP * sum(r["texels"] for r in res.values()), 0
        for victim in cand:
            if dropped >= goal:
                break
            k = victim["id"]
            fk[k] = (min(fk[k][0] * 2, base), fk[k][1])
            res[k] = resample(by_id[k], fk[k][0], fk[k][1] == "body")
            dropped, demoted = dropped + victim["texels"] - res[k]["texels"], demoted + 1
    return list(res.values()), fk, demoted


# ---------------------------------------------------------------- sharing
def flipped(a, fx, fy):
    return a[::-1 if fy else 1, ::-1 if fx else 1]


def lab_of(isl):
    """(h, w, 3) OKLab of the island's texels (0 off it), kept on the dict."""
    if "lab" not in isl:
        lab, on = np.zeros(isl["key"].shape + (3,)), isl["key"] >= 0
        lab[on] = key_lab(isl["key"][on])
        isl["lab"] = lab
    return isl["lab"]


def alike(a, b):
    """(share of texels equal under the best flip, (fx, fy)) of two islands with the same bounding box; equal = the same colour or one within SHARE_DE."""
    best, la = (0.0, FLIPS[0]), lab_of(a)
    for fx, fy in FLIPS:
        kb, lb = flipped(b["key"], fx, fy), flipped(lab_of(b), fx, fy)
        on, both = (a["key"] >= 0) | (kb >= 0), (a["key"] >= 0) & (kb >= 0)
        eq = (a["key"] == kb) | (both & (np.linalg.norm(la - lb, axis=-1) <= SHARE_DE))
        share = float(eq[on].mean()) if on.any() else 0.0
        best = max(best, (share, (fx, fy)), key=lambda t: t[0])
    return best


def plan(islands):
    """(cells {colour key: cell index}, leaders [island], followers {island id: (leader index, fx, fy)}, near pairs): the flat islands share a cell per colour;
    an island NEAR-equal to an earlier one (straight or flipped) follows it; `near` counts the followers that are not exactly equal."""
    cells, leaders, followers, near = {}, [], {}, 0
    for isl in sorted((i for i in islands if i["flat"] is None), key=lambda i: -i["texels"]):
        match = None
        for li, lead in enumerate(leaders):
            if (lead["w"], lead["h"]) != (isl["w"], isl["h"]):
                continue
            share, flips = alike(lead, isl)
            if share >= NEAR:
                match = (li, *flips)
                near += share < 1.0
                break
        if match:
            followers[isl["id"]] = match
        else:
            leaders.append(isl)
    for isl in islands:
        if isl["flat"] is not None:
            cells.setdefault(isl["flat"], len(cells))
    return cells, leaders, followers, near


def masks_of(leaders, cells):
    return [lead["key"] >= 0 for lead in leaders] + [np.ones((CELL, CELL), bool)] * len(cells)


# ---------------------------------------------------------------- packing
def free_origins(occupied, mask):
    """(H, W) bool: the origins (y, x) where `mask` (h, w) lies inside the atlas and on no occupied texel (FFT correlation of the two bitmaps)."""
    S, (h, w) = occupied.shape[0], mask.shape
    if h > S or w > S:
        return np.zeros((S, S), bool)
    hits = np.fft.irfft2(np.fft.rfft2(occupied.astype(float)) * np.conj(np.fft.rfft2(mask.astype(float), s=occupied.shape)), s=occupied.shape)
    free = hits < 0.5
    free[S - h + 1:] = False
    free[:, S - w + 1:] = False
    return free


def pack(masks, size):
    """(origins (K, 2) (x, y), turned (K,) bool) of the texel bitmaps `masks` (each (h, w) bool) in a `size` px atlas: largest first, each at the top-left-most
    origin where it touches no placed texel nor the GAP-texel ring round one, either way up (the lower origin wins). None when one does not fit."""
    org, rot, occupied = np.zeros((len(masks), 2), int), np.zeros(len(masks), bool), np.zeros((size, size), bool)
    for i in np.argsort([-m.sum() for m in masks], kind="stable"):
        ring = eye_paint.dilate(occupied[..., None].astype(float), occupied, GAP)[1]
        best = None
        for turned in (False, True):
            m = masks[i].T if turned else masks[i]
            ys, xs = np.nonzero(free_origins(ring, m))
            if len(ys):
                k = np.lexsort((xs, ys))[0]
                best = min(best or (size, size, False), (int(ys[k]), int(xs[k]), turned))
        if best is None:
            return None
        y, x, turned = best
        m = masks[i].T if turned else masks[i]
        occupied[y:y + m.shape[0], x:x + m.shape[1]] |= m
        org[i], rot[i] = (x, y), turned
    return org, rot


def smallest(masks):
    """(size, origins, turned): the smallest atlas of SIZES that packs `masks`, tried from the side a 95 % full atlas would need."""
    area = sum(int(m.sum()) for m in masks)
    for size in SIZES:
        if size * size * 0.95 < area:
            continue
        packed = pack(masks, size)
        if packed is not None:
            return (size, *packed)
    raise SystemExit("eye_atlas: the islands do not fit a 2048 px atlas")


# ---------------------------------------------------------------- the new atlas
def new_uv(uv, isl_v, islands, cells, leaders, followers, org, rot, size_in, size):
    """(V, 2) the UVs in the compacted atlas: a flat island's at its cell's centre, a follower's in its leader's rectangle (flipped), the rest moved (and turned),
    each at its own density (f bake texels an atlas texel)."""
    by_id, lead_at = {i["id"]: i for i in islands}, {lead["id"]: li for li, lead in enumerate(leaders)}
    out = uv.copy()
    for k, isl in by_id.items():
        sel = isl_v == k
        if isl["flat"] is not None:
            o = org[len(leaders) + cells[isl["flat"]]]
            out[sel] = (o + CELL / 2) / size
            continue
        li, fx, fy = followers[k] if k in followers else (lead_at[k], False, False)
        local = (uv[sel] * size_in - (isl["x0"], isl["y0"])) / isl["f"]
        if fx:
            local[:, 0] = isl["w"] - local[:, 0]
        if fy:
            local[:, 1] = isl["h"] - local[:, 1]
        if rot[li]:
            local = local[:, ::-1]
        out[sel] = (org[li] + local) / size
    return out


def paint(cells, leaders, org, rot, size):
    """(img (size, size, 3) uint8, used): the leaders' texels and the cells placed, a one-texel ring of each dilated into its gutter, the rest the most used colour
    (no colour the islands do not have)."""
    out, used = np.zeros((size, size, 3), float), np.zeros((size, size), bool)
    for li, lead in enumerate(leaders):
        rgb, mask = key_rgb(np.maximum(lead["key"], 0)).astype(float), lead["key"] >= 0
        if rot[li]:
            rgb, mask = rgb.transpose(1, 0, 2), mask.T
        ox, oy = org[li]
        sub = out[oy:oy + mask.shape[0], ox:ox + mask.shape[1]]
        sub[mask] = rgb[mask]
        used[oy:oy + mask.shape[0], ox:ox + mask.shape[1]] |= mask
    for colour, ci in cells.items():
        ox, oy = org[len(leaders) + ci]
        out[oy:oy + CELL, ox:ox + CELL] = key_rgb(colour)
        used[oy:oy + CELL, ox:ox + CELL] = True
    out, grown = eye_paint.dilate(out, used, 1)
    keys, cnt = np.unique(colour_key(out[used].astype(np.uint8)), return_counts=True)
    out[~grown] = key_rgb(keys[cnt.argmax()])
    return np.clip(out, 0, 255).astype(np.uint8), used


def write_uv(j, blob, prim, uv):
    """`uv` (V, 2) float32 into the blob at TEXCOORD_0's place (same count, strided or not); the accessor's min / max follow when it has them."""
    a = j["accessors"][prim["attributes"]["TEXCOORD_0"]]
    v = j["bufferViews"][a["bufferView"]]
    off, stride = v.get("byteOffset", 0) + a.get("byteOffset", 0), v.get("byteStride") or 8
    data = uv.astype("<f4")
    for i in range(len(data)):
        blob[off + i * stride:off + i * stride + 8] = data[i].tobytes()
    if "min" in a:
        a["min"], a["max"] = data.min(0).tolist(), data.max(0).tolist()


def area_report(leaders, cells, fk):
    """{detail_pct, body_pct, cells_pct, texels}: the atlas texels by what holds them: the accent and busy leaders, the body leaders, the flat cells."""
    detail = sum(lead["texels"] for lead in leaders if fk[lead["id"]][1] != "body")
    body = sum(lead["texels"] for lead in leaders if fk[lead["id"]][1] == "body")
    cell = len(cells) * CELL * CELL
    total = max(detail + body + cell, 1)
    return {"detail_pct": round(100 * detail / total, 1), "body_pct": round(100 * body / total, 1), "cells_pct": round(100 * cell / total, 1), "texels": total}


def compact(glb, unit=None, base=1, dry=False):
    """`glb` in place with its atlas compacted (UVs, image, NEAREST sampler); atlas.png beside it. unit: the id (refs/<unit>, the accents' identity lines);
    base: bake texels an atlas texel for a body island (eye_paint.DETAIL with --eye-atlas-detail on). The info, {} when the GLB is not a painted body."""
    from PIL import Image
    glb = pathlib.Path(glb)
    model = read_model(glb)
    if model is None:
        return {}
    j, blob, pos, tri, uv, img = model
    size_in = img.shape[0]
    isl_v = vertex_islands(tri, len(pos))
    used_in, isl_map, P = texel_islands(uv, pos, tri, isl_v, size_in)
    pm, accent, small, names = pieces_of(glb, unit, used_in, P)
    body = used_in & ((pm < 0) | ~accent[np.clip(pm, 0, None)]) if pm is not None else used_in
    body_before = body_after = int(len(np.unique(colour_key(img)[body])))
    if base > 1 and pm is not None:                       # the detail recipe: the palette pushed down, the accents known
        img, body_before, body_after = merge_palette(img, body)
        img = cap_tones(img, pm, accent, used_in)
    islands = islands_of(img, isl_map, int(isl_v.max()) + 1)
    res, fk, demoted = budget(islands, isl_map, pm, accent, small, base)
    cells, leaders, followers, near = plan(res)
    masks = masks_of(leaders, cells)
    size, org, rot = smallest(masks)
    uv2 = new_uv(uv, isl_v, res, cells, leaders, followers, org, rot, size_in, size)
    out, used = paint(cells, leaders, org, rot, size)
    png = eye_paint.png_bytes(out)
    texels = np.array([i["texels"] for i in islands])
    fs = [float(f) for f, _ in fk.values()]
    info = {"size_in": int(size_in), "size": int(size), "base": base, "islands": len(islands), "islands_micro": int((texels <= 4).sum()),
            "flat_islands": sum(i["flat"] is not None for i in res), "flat_cells": len(cells), "pairs": len(followers),
            "pairs_mirror": sum(fx or fy for _, fx, fy in followers.values()), "pairs_near": int(near), "rects": int(len(masks)),
            "kinds": {k: sum(kind == k for _, kind in fk.values()) for k in ("accent", "busy", "body")},
            "factors": {f"{f:g}": fs.count(f) for f in sorted(set(fs))}, "detail_islands": sum(f < base for f in fs), "upsampled": sum(f < 1 for f in fs),
            "demoted": demoted, "accent_pieces": [names[i] for i in np.nonzero(accent)[0]] if accent is not None else [], "detail_pieces": [names[i] for i in np.nonzero(accent & small)[0]] if accent is not None else [],
            "area": area_report(leaders, cells, fk), "coverage_in": round(float(used_in.mean()), 3), "coverage": round(float(used.mean()), 3),
            "texels_in": int(used_in.sum()), "texels": int(used.sum()), "colours": int(len(np.unique(out.reshape(-1, 3), axis=0))),
            "body_colours": [int(body_before), int(body_after)],
            "accent_colours": int(len(np.unique(colour_key(img)[used_in & ~body]))) if pm is not None else 0,
            "bytes_in": int(eye_paint.atlas_bytes(glb)), "bytes": len(png)}
    if dry:
        return info
    write_uv(j, blob, j["meshes"][0]["primitives"][0], uv2)
    eye_paint.write_glb(glb, j, bytes(blob))
    eye_project.swap_atlas(glb, png)
    eye_paint.set_nearest(glb)
    Image.fromarray(np.dstack([out, np.where(used, 255, 0).astype(np.uint8)])).save(glb.parent / "atlas.png")
    return info


def apply_stage(glb, unit=None, base=1):
    """The one call of eye_stage.finish: the compaction on a texel atlas; base = eye_paint.DETAIL when the bake was DETAIL x the atlas size."""
    return compact(glb, unit, base)


if __name__ == "__main__":
    argv = sys.argv[1:]
    unit_id = argv[argv.index("--unit") + 1] if "--unit" in argv else None
    base_f = int(argv[argv.index("--base") + 1]) if "--base" in argv else 1
    print(json.dumps(compact(argv[0], unit_id, base_f, dry="--dry" in argv)))
