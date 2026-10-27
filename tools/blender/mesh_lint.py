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
import os
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile

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
    "components_body == 1": (lambda m: m["components_body"] == 1, False),    # Chen 2023: one welded shell (PIPELINE 24.L6-4)
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


def cover_map(uv, tri, wh, cols, rows):
    """Triangles covering each pixel of a wh = (w, h) raster of the atlas, decal cells
    excluded (they are painted twice)."""
    cover = np.zeros((wh[1], wh[0]), np.int16)
    for t in uv[tri]:
        c = t.mean(0)
        # glTF v runs top-down, the atlas cells are numbered bottom-up
        cell = int((1 - c[1]) * rows * 4) % 4 * 4 + int(c[0] * cols * 4) % 4
        if cell in DECAL_CELLS:
            continue
        q = t * wh
        lo, hi = np.maximum(np.floor(q.min(0)).astype(int), 0), np.minimum(np.ceil(q.max(0)).astype(int), wh)
        gx, gy = np.meshgrid(np.arange(lo[0], hi[0]) + 0.5, np.arange(lo[1], hi[1]) + 0.5)
        cover[lo[1]:hi[1], lo[0]:hi[0]] += inside_tri(q, gx, gy)
    return cover


def raster_uv(uv, tri, size, cols, rows):
    """(overlap % of the covered pixels, atlas used %): UV triangles at size x size."""
    cover = cover_map(uv, tri, (size, size), cols, rows)
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


def atlas_kb(doc):
    """Size of the embedded atlas PNG in KB (1 decimal); None without an image."""
    if not doc.get("images"):
        return None
    return round(doc["bufferViews"][doc["images"][0]["bufferView"]]["byteLength"] / 1024, 1)


def uv_image(glb, scale=2):
    """PIL image of the atlas with every UV triangle outlined and the pixels covered by 2+
    triangles tinted red (Begemann & Hutson 2026 UV screenshot); None without UVs or atlas.
    `scale` multiplies the atlas size so the outlines stay thin."""
    import io

    from PIL import Image, ImageDraw
    doc, blob = read_glb(glb)
    uv, tri = geometry(doc, blob)[2:]
    if uv is None or not doc.get("images"):
        return None
    view = doc["bufferViews"][doc["images"][0]["bufferView"]]
    atlas = Image.open(io.BytesIO(blob[view.get("byteOffset", 0):view.get("byteOffset", 0) + view["byteLength"]])).convert("RGB")
    wh = (atlas.width * scale, atlas.height * scale)
    img = atlas.resize(wh, Image.NEAREST)
    cover = cover_map(uv, tri, wh, max(atlas.width // BLOCK_PX, 1), max(atlas.height // BLOCK_PX, 1))
    px = np.asarray(img).astype(np.float64)
    px[cover > 1] = px[cover > 1] * 0.4 + np.array([255, 0, 0]) * 0.6
    img = Image.fromarray(px.astype(np.uint8))
    draw = ImageDraw.Draw(img)
    for t in uv[tri] * wh:
        draw.polygon([tuple(v) for v in t], outline=(20, 20, 20))
    return img


def root_scale(doc):
    """The scene-root / mesh-node scale furthest from 1 (1.0 when all are unscaled)."""
    roots = set(doc["scenes"][doc.get("scene", 0)]["nodes"])
    nodes = [n for i, n in enumerate(doc["nodes"]) if i in roots or "mesh" in n]
    scales = [s for n in nodes for s in n.get("scale", [1, 1, 1])]
    return float(max(scales, key=lambda s: abs(s - 1), default=1.0))


def components_body(glb, comps):
    """Components of the body alone: build_unit.py counts them (props are components of their own) and
    writes them to the attach.json beside the GLB. No such file (an old run): every component counts."""
    stem = pathlib.Path(glb).stem
    path = pathlib.Path(glb).parent / ("attach.json" if stem in ("clay", "model") else f"{stem}-attach.json")
    try:
        return json.loads(path.read_text())["union"]["components_body"]
    except (OSError, KeyError, ValueError):
        return comps


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
           "nonmanifold_edges": nonmanifold, "components": comps,
           "components_body": components_body(glb, comps), "materials": len(doc.get("materials", [])),
           "images": len(doc.get("images", [])),
           "pivot": {"min_y": float(pos[:, 1].min()), "height": height}, "root_scale": root_scale(doc)}
    out["image_size"], out["unique_colours"] = image_info(doc, blob)
    out["atlas_kb"] = atlas_kb(doc)
    out.update(uv_report(uv, tri, out["image_size"], p, area))
    # atlas pixels laid along the unit's height at the median texel density (report only)
    out["texel_per_height"] = round(out["texel"]["median"] * height) if out["texel"] else None
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
                      "median": float(np.median(texel)), "ratio": float(texel.max() / texel.min())} if len(texel) else None}


ROOT = pathlib.Path(__file__).resolve().parents[2]
IMPORT_SRC = ROOT / "tools/glb_import_check.cpp"


def import_binary():
    """The glb_import_check binary: $GLB_IMPORT_CHECK, the CMake one in build/, else compiled
    once (about 1 s) with c++ + pkg-config raylib into the temp dir. None when none of those work."""
    for cand in (os.environ.get("GLB_IMPORT_CHECK"), ROOT / "build/glb_import_check"):
        if cand and pathlib.Path(cand).exists():
            return pathlib.Path(cand)
    out = pathlib.Path(tempfile.gettempdir()) / f"glb_import_check-{os.getuid()}"
    if out.exists() and out.stat().st_mtime >= IMPORT_SRC.stat().st_mtime:
        return out
    if not (shutil.which("c++") and shutil.which("pkg-config")):
        return None
    flags = subprocess.run(["pkg-config", "--cflags", "--libs", "raylib"], capture_output=True, text=True)
    if flags.returncode:
        return None
    gl = ["-framework", "OpenGL"] if sys.platform == "darwin" else []
    build = subprocess.run(["c++", "-std=c++17", "-O1", str(IMPORT_SRC), *flags.stdout.split(), *gl, "-o", str(out)],
                           capture_output=True)
    return out if build.returncode == 0 else None


def engine_import(glb):
    """`ok meshes=N verts=V anims=A`, `error <msg>` or `n/a <why>`: the GLB through the game's own
    loader (raylib LoadModel + LoadModelAnimations, tools/glb_import_check.cpp), headless."""
    binary = import_binary()
    if binary is None:
        return "n/a (no glb_import_check: make glb-check, or install a C++ compiler and raylib)"
    try:
        run = subprocess.run([str(binary), str(glb)], capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return "error timeout"
    line = run.stdout.strip().split("\t")[-1]
    return line or f"n/a (loader exited {run.returncode} without output: no window?)"


def mean_iou(sheet, glb, out, layout, rig):
    """Mean silhouette IoU over the views silhouette.py scores for this GLB against the sheet."""
    subprocess.run([sys.executable, str(ROOT / "tools/blender/silhouette.py"), str(sheet), str(glb), str(out),
                    "--layout", layout, "--shape", "--rig", rig or ""], capture_output=True, text=True)
    ious = [r["iou"] for r in json.loads((out / "silhouette.json").read_text()).values()]
    return sum(ious) / len(ious)


def decimate_loss(glb, sheet, work, layout="unit", rig=None, ratio=0.5):
    """What the triangles buy (report only, PIPELINE §20.M10): Blender collapse-decimates the GLB to `ratio`,
    both are measured against the sheet, and the mean IoU lost goes per 100 triangles removed.
    {"tris": [before, after], "iou": [before, after], "lost_per_100_tris": float | None}; None
    when the decimated GLB did not come out."""
    work = pathlib.Path(work)
    work.mkdir(parents=True, exist_ok=True)
    small = work / "decimated.glb"
    subprocess.run(["blender", "-b", "-P", str(ROOT / "tools/blender/decimate_glb.py"), "--", str(glb), str(small), str(ratio)],
                   capture_output=True, text=True)
    if not small.exists():
        return None
    tris = [lint_tris(g) for g in (glb, small)]
    iou = [mean_iou(sheet, g, work / name, layout, rig) for g, name in ((glb, "sil-full"), (small, "sil-decimated"))]
    removed = tris[0] - tris[1]
    return {"tris": tris, "iou": iou, "lost_per_100_tris": 100 * (iou[0] - iou[1]) / removed if removed > 0 else None}


def lint_tris(glb):
    return len(geometry(*read_glb(pathlib.Path(glb)))[3])


def failing(m, textured):
    """Names of the failed gates; the texture gates only count when `textured`."""
    return [name for name, (check, needs_tex) in GATES.items()
            if (textured or not needs_tex) and not check(m)]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("glbs", nargs="+", type=pathlib.Path)
    ap.add_argument("--decimate", type=pathlib.Path, metavar="SHEET", help="instead of the lint: IoU lost per 100 tris at 50 %% vs this sheet")
    ap.add_argument("--layout", default="unit", choices=("unit", "building"))
    ap.add_argument("--rig", default=None)
    a = ap.parse_args()
    for f in a.glbs:
        if a.decimate:
            with tempfile.TemporaryDirectory() as tmp:
                print(json.dumps({str(f): decimate_loss(f, a.decimate, tmp, a.layout, a.rig)}))
        else:
            print(json.dumps({str(f): lint(f)}))
