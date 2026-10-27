#!/usr/bin/env python3
"""Mesh lint of a unit GLB: numpy over the glTF JSON + BIN, no Blender (PIPELINE.md §19.A1).

    python3.14 tools/blender/mesh_lint.py <file.glb> [more.glb ...]    # JSON per file

lint(glb) -> dict of measurements; failing(lint, textured) -> the names of the gates that fail.
Only the gates in GATES are enforced (flipped normals, UV range, one atlas, feet on the
ground, root scale 1; image_size <= 512 stays a report: the 5-8 material atlas is 768 px); the rest is reported until the runs calibrate it (PIPELINE §19.A1).
Papers: Chen 2023 (manifold, self-intersection), Wiersma 2026 (slivers), Begemann & Hutson 2026
(technical matrix), MeshGPT 2024 (compactness, face area), EdgeRunner 2024 (orientation,
degenerates, components; watertight is NOT required: a unit is a union of closed parts).
"""
import json
import struct
import sys

import numpy as np

SLIVER_DEG = 10.0      # smallest triangle angle under this is a sliver (Wiersma 2026)
WELD = 1e-5            # vertices closer than this are one vertex when counting edges
RASTER = 1024          # UV overlap raster
DECAL_CELLS = range(8, 16)   # build_unit.paint_decals: cells 8+i of each 4x4 block
BLOCK_PX = 256         # build_unit.texturize: one block per material
COMP = {5126: "<f4", 5125: "<u4", 5123: "<u2", 5121: "u1"}
WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
# name -> (check on the lint dict, needs the textured model). Obvious gates only.
GATES = {
    "flipped == 0": (lambda m: m["flipped"] == 0, False),
    "uv_out_of_range == 0": (lambda m: m["uv_out_of_range"] == 0, True),
    "images == 1": (lambda m: m["images"] == 1, True),
    "abs(min_y) <= 0.01 H": (lambda m: abs(m["pivot"]["min_y"]) <= 0.01 * m["pivot"]["height"], False),
    "root_scale == 1": (lambda m: abs(m["root_scale"] - 1) < 1e-3, False),
}


def read_glb(path):
    data = path.read_bytes()
    jlen = int.from_bytes(data[12:16], "little")
    doc = json.loads(data[20:20 + jlen].decode("utf8", "ignore").rstrip("\0 "))
    return doc, data[28 + jlen:]


def accessor(doc, blob, idx):
    a = doc["accessors"][idx]
    view = doc["bufferViews"][a["bufferView"]]
    width, dt = WIDTH[a["type"]], np.dtype(COMP[a["componentType"]])
    stride = view.get("byteStride") or width * dt.itemsize
    start = view.get("byteOffset", 0) + a.get("byteOffset", 0)
    raw = np.frombuffer(blob, np.uint8, count=stride * (a["count"] - 1) + width * dt.itemsize, offset=start)
    rows = np.lib.stride_tricks.as_strided(raw, (a["count"], width * dt.itemsize), (stride, 1))
    out = np.ascontiguousarray(rows).view(dt).reshape(a["count"], width)
    return out[:, 0] if width == 1 else out


def geometry(doc, blob):
    """pos, normal, uv (None without UVs), tri indices: every primitive merged."""
    pos, nor, uv, tri, base = [], [], [], [], 0
    for m in doc["meshes"]:
        for p in m["primitives"]:
            at = p["attributes"]
            pos.append(accessor(doc, blob, at["POSITION"]).astype(np.float64))
            nor.append(accessor(doc, blob, at["NORMAL"]).astype(np.float64))
            uv.append(accessor(doc, blob, at["TEXCOORD_0"]).astype(np.float64) if "TEXCOORD_0" in at else None)
            tri.append(accessor(doc, blob, p["indices"]).astype(np.int64).reshape(-1, 3) + base)
            base += len(pos[-1])
    has_uv = all(u is not None for u in uv)
    return (np.vstack(pos), np.vstack(nor), np.vstack(uv) if has_uv else None, np.vstack(tri))


def angles_min(p):
    """Smallest angle (degrees) of each triangle p[F,3,3]."""
    e = np.stack([p[:, 1] - p[:, 0], p[:, 2] - p[:, 1], p[:, 0] - p[:, 2]], 1)
    ln = np.maximum(np.linalg.norm(e, axis=2), 1e-12)
    cos = -np.einsum("fid,fid->fi", e, np.roll(e, 1, 1)) / (ln * np.roll(ln, 1, 1))
    return np.degrees(np.arccos(np.clip(cos, -1, 1))).min(1)


def topology(pos, tri):
    """(boundary edges, non-manifold edges, components) on welded vertices."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    _, weld = np.unique(np.round(pos / WELD).astype(np.int64), axis=0, return_inverse=True)
    t = weld.reshape(-1)[tri]
    t = t[(t[:, 0] != t[:, 1]) & (t[:, 1] != t[:, 2]) & (t[:, 0] != t[:, 2])]
    edges = np.sort(np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]]), axis=1)
    uniq, count = np.unique(edges, axis=0, return_counts=True)
    n = weld.max() + 1
    graph = coo_matrix((np.ones(len(uniq)), (uniq[:, 0], uniq[:, 1])), shape=(n, n))
    used = np.zeros(n, bool)
    used[t.ravel()] = True
    comps = connected_components(graph, directed=False)[1][used]
    return int((count == 1).sum()), int((count > 2).sum()), int(len(np.unique(comps)))


def raster_uv(uv, tri, size, cols, rows):
    """(overlap % of the covered pixels, atlas used %, texel inputs): UV triangles at
    size x size, decal cells excluded from the overlap count (they are painted twice)."""
    cover = np.zeros((size, size), np.int16)
    for t in uv[tri]:
        c = t.mean(0)
        # glTF v runs top-down, the atlas cells are numbered bottom-up
        cell = int((1 - c[1]) * rows * 4) % 4 * 4 + int(c[0] * cols * 4) % 4
        if cell in DECAL_CELLS:
            continue
        q = t * size
        lo, hi = np.maximum(np.floor(q.min(0)).astype(int), 0), np.minimum(np.ceil(q.max(0)).astype(int), size)
        gx, gy = np.meshgrid(np.arange(lo[0], hi[0]) + 0.5, np.arange(lo[1], hi[1]) + 0.5)
        inside = inside_tri(q, gx, gy)
        cover[lo[1]:hi[1], lo[0]:hi[0]] += inside
    covered = cover > 0
    return (round(100.0 * (cover > 1).sum() / max(covered.sum(), 1), 1),
            round(100.0 * covered.sum() / cover.size, 1))


def inside_tri(q, gx, gy):
    """Boolean mask of the grid points inside triangle q[3,2] (either winding)."""
    def side(a, b):
        return (b[0] - a[0]) * (gy - a[1]) - (b[1] - a[1]) * (gx - a[0])
    s = [side(q[i], q[(i + 1) % 3]) for i in range(3)]
    return (np.all([v >= 0 for v in s], 0) | np.all([v <= 0 for v in s], 0))


def image_info(doc, blob):
    """((w, h), unique colours) of the first image; (None, None) without one."""
    if not doc.get("images"):
        return None, None
    view = doc["bufferViews"][doc["images"][0]["bufferView"]]
    png = blob[view.get("byteOffset", 0):view.get("byteOffset", 0) + view["byteLength"]]
    w, h = struct.unpack(">II", png[16:24])
    try:
        import io

        from PIL import Image
        px = np.asarray(Image.open(io.BytesIO(png)).convert("RGB")).reshape(-1, 3)
        return (w, h), int(len(np.unique(px, axis=0)))
    except ImportError:
        return (w, h), None


def root_scale(doc):
    """The scene-root / mesh-node scale furthest from 1 (1.0 when all are unscaled)."""
    roots = set(doc["scenes"][doc.get("scene", 0)]["nodes"])
    nodes = [n for i, n in enumerate(doc["nodes"]) if i in roots or "mesh" in n]
    scales = [s for n in nodes for s in n.get("scale", [1, 1, 1])]
    return float(max(scales, key=lambda s: abs(s - 1), default=1.0))


def lint(glb):
    doc, blob = read_glb(glb)
    pos, nor, uv, tri = geometry(doc, blob)
    p = pos[tri]
    cross = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    area = np.linalg.norm(cross, axis=1) / 2
    height = float(pos[:, 1].max() - pos[:, 1].min())
    live = area > 1e-8 * height ** 2
    geo_n = cross[live] / (2 * area[live, None])
    flipped = int((np.einsum("fd,fd->f", geo_n, nor[tri][live].sum(1)) < 0).sum())
    boundary, nonmanifold, comps = topology(pos, tri)
    med = float(np.median(area[live])) if live.any() else 0.0
    out = {"verts": len(pos), "faces": len(tri), "tris": len(tri),
           "nodes": len(doc["nodes"]), "meshes": len(doc["meshes"]), "skins": len(doc.get("skins", [])),
           "compactness": round(len(pos) / max(len(tri), 1), 2),
           "face_area": {"median": med, "p90": float(np.percentile(area[live], 90)) if live.any() else 0.0,
                         "max_over_median": float(area.max() / med) if med else 0.0},
           "sliver_pct": round(100.0 * float((angles_min(p[live]) < SLIVER_DEG).mean()), 1) if live.any() else 0.0,
           "degenerate": int((~live).sum()), "flipped": flipped, "boundary_edges": boundary,
           "nonmanifold_edges": nonmanifold, "components": comps, "materials": len(doc.get("materials", [])),
           "images": len(doc.get("images", [])),
           "pivot": {"min_y": float(pos[:, 1].min()), "height": height}, "root_scale": root_scale(doc)}
    out["image_size"], out["unique_colours"] = image_info(doc, blob)
    out.update(uv_report(uv, tri, out["image_size"], p, area))
    return out


def uv_report(uv, tri, size, p, area):
    """uv_out_of_range, uv_overlap_pct, atlas_used_pct, texel{min,max,ratio} (px per world unit)."""
    if uv is None or size is None:
        return {"uv_out_of_range": 0, "uv_overlap_pct": None, "atlas_used_pct": None, "texel": None}
    cols, rows = max(size[0] // BLOCK_PX, 1), max(size[1] // BLOCK_PX, 1)
    overlap, used = raster_uv(uv, tri, RASTER, cols, rows)
    a, b = uv[tri][:, 1] - uv[tri][:, 0], uv[tri][:, 2] - uv[tri][:, 0]
    uv_area = np.abs(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]) / 2
    ok = area > 1e-8 * area.max()
    texel = np.sqrt(uv_area[ok] * size[0] * size[1] / area[ok])
    texel = texel[texel > 0]
    return {"uv_out_of_range": int(((uv < -1e-4) | (uv > 1 + 1e-4)).any(1).sum()),
            "uv_overlap_pct": overlap, "atlas_used_pct": used,
            "texel": {"min": float(texel.min()), "max": float(texel.max()),
                      "ratio": float(texel.max() / texel.min())} if len(texel) else None}


def failing(m, textured):
    """Names of the failed gates; the texture gates only count when `textured`."""
    return [name for name, (check, needs_tex) in GATES.items()
            if (textured or not needs_tex) and not check(m)]


if __name__ == "__main__":
    import pathlib
    for f in sys.argv[1:]:
        print(json.dumps({f: lint(pathlib.Path(f))}))
