#!/usr/bin/env python3
"""WC3 reference models (Hive MDX) as study material: stats, textured GLB, 6-view sheet (L16-3).

    python3.14 tools/blender/hive_sheet.py stats [--out analysis/2026-10-30-l16-hive-stats]
    python3.14 tools/blender/hive_sheet.py render <Name|all> [--out artifacts/reference/hive/renders]
    python3.14 tools/blender/hive_sheet.py pair <unit|all>      # concept | v16 | control | Hive -> history/2026-10-30-l16-hive/<unit>.png
    python3.14 tools/blender/hive_sheet.py judge <unit>         # review_pair with the Hive sheet as the wc3 reference (4 votes)

`stats` reads every MDX under artifacts/reference/hive/mdx plus our v16 runs and writes a CSV and a
markdown table (median / p10 / p90 of the Hive, our six beside it). `render` writes a textured GLB per
model (positions, uvs, the texture of each geoset's first layer, team colour from teamcolor00) and
shoots it with render_unit.py, so the six views have the framing of our own renders; the contact sheet
lands in <out>/<Name>.png. Blizzard-derived files are reference only: nothing here is committed
(.gitignore keeps mdx/, tex/, renders/ and the zips out).
"""
import argparse
import csv
import io
import json
import pathlib
import statistics
import struct
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mdx_inspect  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
HIVE = ROOT / "artifacts/reference/hive"
DRAFT = ROOT / "artifacts/model-sheets/runs/draft"
UNITS = ("n005", "n00U", "hfoo", "n017", "n02X", "n01X")
NOT_A_UNIT = ("NewAssassin_portrait", "SatyrDryadMissile")     # a portrait model, a projectile
VIEWS = ("front", "left", "back", "top", "bottom", "wc3")
HEIGHT = 2.2                      # GLB height in metres-ish: ours are 2-2.4 tall, the ortho framing is relative anyway
DARK, INK_STEP, SHARE = 46, 70, 0.03   # dark texel: luma < 46/255; ink: dark with a texel 70 brighter within 2 px; palette share >= 3 %


# ---------------------------------------------------------------- textures

def tex_index():
    """{lowercase file stem: path} of every texture under hive/tex."""
    return {p.stem.lower(): p for p in (HIVE / "tex").rglob("*") if p.suffix.lower() in (".blp", ".dds", ".png", ".tga")}


def tex_image(rep, path, index):
    """RGBA PIL image of one TEXS entry (replaceable 1 = team colour 00, 2 = team glow 00), or None when
    the file is not in the study set."""
    if rep == 1:
        found = HIVE / "tex/replaceabletextures/teamcolor/teamcolor00.blp"
    elif rep == 2:
        found = HIVE / "tex/replaceabletextures/teamglow/teamglow00.blp"
    else:
        found = index.get(path.replace("\\", "/").rsplit("/", 1)[-1].rsplit(".", 1)[0].lower())
    return Image.open(found).convert("RGBA") if found and found.exists() else None


def luma(rgb):
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def kmeans(px, k=16, iters=12, seed=0):
    """(centres, shares) of k-means on an (n, 3) float array; deterministic."""
    rng = np.random.default_rng(seed)
    centres = px[rng.choice(len(px), min(k, len(px)), replace=False)].copy()
    for _ in range(iters):
        label = np.argmin(((px[:, None, :] - centres[None]) ** 2).sum(-1), axis=1)
        for c in range(len(centres)):
            if (label == c).any():
                centres[c] = px[label == c].mean(0)
    label = np.argmin(((px[:, None, :] - centres[None]) ** 2).sum(-1), axis=1)
    return centres, np.bincount(label, minlength=len(centres)) / len(px)


def palette_stats(centres, shares):
    """(colours with >= 3 % share, share-weighted mean luma distance between colours, 0..1)."""
    big = int((shares >= SHARE).sum())
    lum = luma(centres)
    w = shares[:, None] * shares[None]
    spread = float((w * np.abs(lum[:, None] - lum[None])).sum() / max(w.sum() - np.trace(w), 1e-9) / 255)
    return big, spread


def uv_mask(geos, size):
    """Boolean (h, w) mask of the texels the geosets' triangles cover in UV space (an atlas is mostly
    unused black: only the texels a model samples are its painting)."""
    from PIL import ImageDraw                            # noqa: PLC0415
    w, h = size
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for g in geos:
        uv = [((v[6] % 1.0 if v[6] != 1.0 else 1.0) * (w - 1), (v[7] % 1.0 if v[7] != 1.0 else 1.0) * (h - 1)) for v in g["vertices"]]
        for i in range(0, len(g["faces"]) - 2, 3):
            draw.polygon([uv[j] for j in g["faces"][i:i + 3]], fill=255)
    return np.asarray(mask) > 0


def texture_stats(img, used=None):
    """Painted-detail numbers of the opaque texels the model samples (`used`: UV mask, default all):
    palette (k-means 16, colours >= 3 %), zone contrast (mean luma distance between palette colours), grad
    (mean |luma gradient|, 0..1), dark (share of texels with luma < 46) and ink (dark texels with a texel
    >= 70 brighter within 2 px: a painted outline)."""
    a = np.asarray(img, dtype=np.float32)
    keep = (a[..., 3] > 128) & (used if used is not None else True)
    if keep.sum() < 16:
        return None
    sample = a[..., :3][keep]
    sample = sample[np.random.default_rng(0).choice(len(sample), min(len(sample), 20000), replace=False)]
    big, spread = palette_stats(*kmeans(sample))
    lum = np.where(keep, luma(a[..., :3]), 0)            # a texel outside the painted area is not a neighbour
    gy, gx = np.abs(np.diff(lum, axis=0))[:, :-1], np.abs(np.diff(lum, axis=1))[:-1]
    both = keep[:-1, :-1] & keep[1:, 1:] & keep[:-1, 1:] & keep[1:, :-1]
    dark = (lum < DARK) & keep
    near = np.zeros_like(lum)
    pad = np.pad(lum, 2, mode="edge")
    for dy in range(5):
        for dx in range(5):
            near = np.maximum(near, pad[dy:dy + lum.shape[0], dx:dx + lum.shape[1]])
    return {"colours": big, "contrast": round(spread, 3), "grad": round(float((gx + gy)[both].mean() / 255 / 2), 4),
            "dark": round(float(dark.sum() / keep.sum()), 3),
            "ink": round(float((dark & (near - lum > INK_STEP)).sum() / keep.sum()), 3), "px": img.width * img.height,
            "used": round(float(keep.sum() / (img.width * img.height)), 3)}


# ---------------------------------------------------------------- Hive geometry

def layer0_texture(mdx, geoset):
    """Index into mdx['textures'] of the geoset's first layer, or None."""
    mats = mdx["materials"]
    layers = mats[geoset["material"]] if geoset["material"] < len(mats) else []
    return layers[0]["texture"] if layers else None


def drawn_geosets(mdx):
    """Geosets that are part of the unit: visible, and not the team-glow ground quad (replaceable 2)."""
    out = []
    for g in mdx["geosets"]:
        tex = layer0_texture(mdx, g)
        rep = mdx["textures"][tex][0] if tex is not None and tex < len(mdx["textures"]) else 0
        if g["visible"] and rep != 2 and g["faces"]:
            out.append(g)
    return out


def band_widths(x, up, h):
    """Width (2 x p90 of |x - median|) over H of the vertices in the legs / torso / head bands."""
    out = []
    for lo, hi in ((0, 0.4), (0.4, 0.75), (0.75, 1.0)):
        sel = x[(up >= up.min() + lo * h) & (up <= up.min() + hi * h + 1e-9)]
        out.append(round(float(2 * np.percentile(np.abs(sel - np.median(sel)), 90) / h), 3) if len(sel) else 0.0)
    return out


def shape_stats(side, up, front):
    """H and the W/H, D/H of the vertex cloud (1st-99th percentile); side/front are its horizontal axes (width, depth)."""
    span = lambda a: float(np.percentile(a, 99) - np.percentile(a, 1))     # noqa: E731  trimmed: a stray vertex or a spear tip is not the body
    h = span(up)
    return {"H": round(h, 2), "W/H": round(span(side) / h, 3), "D/H": round(span(front) / h, 3),
            **dict(zip(("legs", "torso", "head"), band_widths(side, up, h)))}


def hive_stats(path, index):
    mdx = mdx_inspect.read_mdx(path)
    geos = drawn_geosets(mdx)
    xyz = np.array([v[:3] for g in geos for v in g["vertices"]], dtype=np.float64)
    used = {}                                       # texture index -> triangles
    for g in geos:
        t = layer0_texture(mdx, g)
        used[t] = used.get(t, 0) + len(g["faces"]) // 3
    files = [t for t in used if t is not None and mdx["textures"][t][0] == 0]
    main = max(files, key=used.get, default=None)
    img = tex_image(*mdx["textures"][main], index) if main is not None else None
    tex = texture_stats(img, uv_mask([g for g in geos if layer0_texture(mdx, g) == main], img.size)) if img else None
    row = {"name": path.stem, "tris": sum(len(g["faces"]) // 3 for g in geos),
            "verts": sum(len(g["vertices"]) for g in geos), "parts": len(geos),
            "materials": len({g["material"] for g in geos}), "textures": len(files), "bones": len(mdx["bones"]),
            "missing_tex": sum(tex_image(*mdx["textures"][t], index) is None for t in files),
            **shape_stats(xyz[:, 1], xyz[:, 2], xyz[:, 0]), **(tex_fields(tex))}
    return derived(row)


def derived(row):
    """Ratios of a stats row: vertices per triangle (smooth shared vs split flat-shaded), triangles per part, top band / torso band width."""
    return {**row, "v/t": round(row["verts"] / row["tris"], 2), "t/part": round(row["tris"] / row["parts"], 1) if row["parts"] else None,
            "head/torso": round(row["head"] / row["torso"], 2) if row["torso"] else None}


def tex_fields(tex):
    keys = ("px", "used", "colours", "contrast", "grad", "dark", "ink")
    return {k: (tex[k] if tex else None) for k in keys}


# ---------------------------------------------------------------- our GLBs

def read_glb(path):
    """(json, bin) of a .glb."""
    d = pathlib.Path(path).read_bytes()
    n = struct.unpack_from("<I", d, 12)[0]
    m = struct.unpack_from("<I", d, 20 + n)[0]
    return json.loads(d[20:20 + n]), d[28 + n:28 + n + m]


def accessor(j, blob, idx):
    a, v = j["accessors"][idx], j["bufferViews"][j["accessors"][idx]["bufferView"]]
    width = {"VEC3": 3, "SCALAR": 1}[a["type"]]
    dt = {5126: "<f4", 5123: "<u2", 5125: "<u4"}[a["componentType"]]
    off = v.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = v.get("byteStride")
    if stride and stride != width * np.dtype(dt).itemsize:
        raw = np.frombuffer(blob, np.uint8, count=a["count"] * stride, offset=off).reshape(a["count"], stride)
        return raw[:, :width * np.dtype(dt).itemsize].copy().view(dt).reshape(a["count"], width)
    return np.frombuffer(blob, dt, count=a["count"] * width, offset=off).reshape(a["count"], width)


def srgb(c):
    """linear 0..1 -> 0..255 sRGB."""
    c = np.clip(np.asarray(c, dtype=np.float64), 0, 1)
    return 255 * np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


def our_stats(unit, run="v16-r1"):
    """Same row as hive_stats for one of our GLBs: the body mesh ('eye' or whatever is not 'outline'),
    flat material colours (palette weighted by area), no texture; `parts` = the eye stage's pieces."""
    glb = DRAFT / unit / run / "model.glb"
    j, blob = read_glb(glb)
    tris = verts = 0
    area, colours, pts, hull = [], [], [], 0
    for m in j["meshes"]:
        for p in m["primitives"]:
            pos = accessor(j, blob, p["attributes"]["POSITION"]).astype(np.float64)
            idx = accessor(j, blob, p["indices"]).reshape(-1, 3) if "indices" in p else np.arange(len(pos)).reshape(-1, 3)
            if m.get("name") == "outline":
                hull += len(idx)
                continue
            tri = pos[idx]
            area.append(float(np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1).sum()) / 2)
            colours.append(srgb(j["materials"][p["material"]]["pbrMetallicRoughness"]["baseColorFactor"][:3]))
            tris, verts = tris + len(idx), verts + len(pos)
            pts.append(pos[np.unique(idx)])
    cloud = np.concatenate(pts)
    w = np.array(area) / sum(area)
    big, spread = palette_stats(np.array(colours), w)
    summary = DRAFT / unit / run / "eye/summary.json"
    pieces = json.loads(summary.read_text())["rounds"][-1]["pieces"] if summary.exists() else None
    return derived({"name": f"{unit} {run}", "tris": tris, "verts": verts, "parts": pieces, "materials": len(colours),
            "textures": 0, "bones": sum(len(s["joints"]) for s in j.get("skins", [])), "hull_tris": hull,
            "missing_tex": 0, **shape_stats(cloud[:, 0], cloud[:, 1], cloud[:, 2]),
            **tex_fields(None), "colours": big, "contrast": round(spread, 3), "grad": 0.0, "dark": None, "ink": 0.0})


# ---------------------------------------------------------------- stats table

COLS = ("name", "tris", "verts", "v/t", "parts", "t/part", "materials", "textures", "bones", "H", "W/H", "D/H", "legs", "torso", "head", "head/torso",
        "px", "used", "colours", "contrast", "grad", "dark", "ink")


def quantiles(rows, col):
    vals = sorted(r[col] for r in rows if r.get(col) is not None)
    if not vals:
        return None
    p = lambda q: float(np.percentile(vals, q))   # noqa: E731
    return round(statistics.median(vals), 3), round(p(10), 3), round(p(90), 3)


def fmt(v):
    return "-" if v is None else f"{v:g}" if isinstance(v, (int, float)) else str(v)


NOTES = ("Notes. `parts`: Hive = geosets drawn in the first sequence (a skinned mesh with one material; hidden geosets and the team-glow quad dropped), "
         "ours = pieces of the eye stage. `tris` of ours = the body mesh; the black hull is another equal count (file = 2x). `bones`: Hive = BONE + HELP nodes "
         "(attachment points included), not comparable with our rig. `H`: WC3 units vs model units. `legs/torso/head` = width (2 x p90 of |x - median|) / H of the "
         "vertices in the height bands 0-40 / 40-75 / 75-100 %; a held weapon inflates the top band. Texture columns: the model's main file texture, only the texels "
         "its UVs cover (`used` = their share of the atlas); `colours` = k-means 16 clusters with >= 3 %, `contrast` = share-weighted luma distance between the "
         "clusters (0..1), `grad` = mean |luma gradient|, `dark` = texels with luma < 46, `ink` = dark texels with a texel 70 brighter within 2 px. "
         "Ours has no texture: `colours` / `contrast` are the flat material colours weighted by area, `grad` / `ink` are 0 by construction. "
         "Hive geometry is the bind pose (no animation evaluated).")


def stats_md(hive, ours):
    units = [r for r in hive if r["name"] not in NOT_A_UNIT]
    lines = ["| metric | Hive median | p10 | p90 | " + " | ".join(r["name"].split()[0] for r in ours) + " |",
             "|---|---|---|---|" + "---|" * len(ours)]
    for c in COLS[1:]:
        q = quantiles(units, c) or ("-", "-", "-")
        lines.append(f"| {c} | " + " | ".join(fmt(v) for v in q) + " | " + " | ".join(fmt(r.get(c)) for r in ours) + " |")
    lines += ["", f"Hive: {len(units)} unit models (the {len(hive) - len(units)} others, a portrait and a projectile, are in the CSV only). Ours: v16-r1 of the six battery units.", "",
              NOTES, "",
              "| model | " + " | ".join(COLS[1:]) + " |", "|---|" + "---|" * (len(COLS) - 1)]
    lines += [f"| {r['name']} | " + " | ".join(fmt(r.get(c)) for c in COLS[1:]) + " |" for r in hive]
    return "\n".join(lines) + "\n"


def cmd_stats(args):
    index = tex_index()
    hive = [hive_stats(p, index) for p in sorted((HIVE / "mdx").glob("*.mdx"))]
    ours = [our_stats(u) for u in UNITS]
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out.with_suffix(".csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[*COLS, "missing_tex", "set"], extrasaction="ignore")
        w.writeheader()
        w.writerows([{**r, "set": "hive"} for r in hive] + [{**r, "set": "ours-v16"} for r in ours])
    out.with_suffix(".md").write_text(stats_md(hive, ours))
    print(f"wrote {out.with_suffix('.csv')} and {out.with_suffix('.md')}")


# ---------------------------------------------------------------- GLB + sheet

def png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


class Glb:
    """A growing glTF binary: one buffer, its views and accessors (the writer below fills it geoset by geoset)."""

    def __init__(self):
        self.blob, self.views, self.accs = bytearray(), [], []

    def add(self, data, target=None, **acc):
        """Append bytes as a buffer view (and an accessor when `acc` is given); returns the view index."""
        self.blob.extend(b"\0" * (-len(self.blob) % 4))
        self.views.append({"buffer": 0, "byteOffset": len(self.blob), "byteLength": len(data), **({"target": target} if target else {})})
        self.blob.extend(data)
        if acc:
            self.accs.append({"bufferView": len(self.views) - 1, **acc})
        return len(self.views) - 1

    def accessor(self, arr, typ, name=None):
        extra = {"min": arr.min(0).tolist(), "max": arr.max(0).tolist()} if name == "POSITION" else {}
        self.add(arr.tobytes(), 34962, componentType=5126, count=len(arr), type=typ, **extra)
        return len(self.accs) - 1

    def pack(self, doc):
        js = json.dumps({**doc, "accessors": self.accs, "bufferViews": self.views, "buffers": [{"byteLength": len(self.blob)}]}).encode()
        js += b" " * (-len(js) % 4)
        body = bytes(self.blob) + b"\0" * (-len(self.blob) % 4)
        return (struct.pack("<4sII", b"glTF", 2, 28 + len(js) + len(body)) + struct.pack("<I4s", len(js), b"JSON") + js
                + struct.pack("<I4s", len(body), b"BIN\0") + body)


def glb_material(layer, tex):
    """glTF material of a geoset: its texture (None: flat white) and the alpha mode of its first layer's filter."""
    pm = {"baseColorFactor": [1, 1, 1, 1], "metallicFactor": 0, "roughnessFactor": 1}
    if tex is not None:
        pm["baseColorTexture"] = {"index": tex}
    return {"doubleSided": True, "pbrMetallicRoughness": pm,
            **({} if layer["filter"] == 0 else {"alphaMode": "MASK" if layer["filter"] == 1 else "BLEND"})}


def build_glb(mdx, index):
    """glTF binary of the drawn geosets: Y-up, facing as our models face (x_wc3 -> +Z, y_wc3 -> +X), scaled to HEIGHT;
    one material per geoset with its first-layer texture (nearest-neighbour, like the game's low-res atlases)."""
    geos = drawn_geosets(mdx)
    allv = np.array([v[:3] for g in geos for v in g["vertices"]])
    lo_z, scale = allv[:, 2].min(), HEIGHT / np.ptp(allv[:, 2])
    cx, cy = (allv[:, 0].min() + allv[:, 0].max()) / 2, (allv[:, 1].min() + allv[:, 1].max()) / 2
    glb, images, textures, materials, prims, slot = Glb(), [], [], [], [], {}
    for g in geos:
        t = layer0_texture(mdx, g)
        img = tex_image(*mdx["textures"][t], index) if t is not None and t < len(mdx["textures"]) else None
        if img is not None and t not in slot:
            slot[t] = len(textures)
            images.append({"bufferView": glb.add(png_bytes(img)), "mimeType": "image/png"})
            textures.append({"source": len(images) - 1, "sampler": 0})
        layer = mdx["materials"][g["material"]][0] if mdx["materials"] else {"filter": 0}
        materials.append(glb_material(layer, slot.get(t)))
        v = np.array(g["vertices"], dtype=np.float64)
        pos = np.stack([(v[:, 1] - cy) * scale, (v[:, 2] - lo_z) * scale, (v[:, 0] - cx) * scale], 1).astype("<f4")
        attrs = {"POSITION": glb.accessor(pos, "VEC3", "POSITION"),
                 "NORMAL": glb.accessor(np.stack([v[:, 4], v[:, 5], v[:, 3]], 1).astype("<f4"), "VEC3"),
                 "TEXCOORD_0": glb.accessor(v[:, 6:8].astype("<f4"), "VEC2")}
        faces = np.array(g["faces"], dtype="<u2")
        prims.append({"attributes": attrs, "indices": len(glb.accs), "material": len(materials) - 1})
        glb.add(faces.tobytes(), 34963, componentType=5123, count=len(faces), type="SCALAR")
    doc = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0, "name": "hive"}],
           "meshes": [{"primitives": prims}], "materials": materials,
           "samplers": [{"magFilter": 9728, "minFilter": 9728, "wrapS": 10497, "wrapT": 10497}],
           **({"images": images, "textures": textures} if textures else {})}
    return glb.pack(doc)


def shoot(glb, out, tilt="", lit=False):
    """The six render_unit views of a GLB in `out` (cached)."""
    if not all((out / f"{glb.stem}-{v}.png").exists() for v in VIEWS):
        out.mkdir(parents=True, exist_ok=True)
        subprocess.run(["nice", "-n", "10", "blender", "-b", "-P", str(ROOT / "tools/blender/render_unit.py"), "--", str(glb), str(out),
                        *([tilt] if tilt else []), *(["lit"] if lit else [])], capture_output=True, text=True, check=True)
    return {v: out / f"{glb.stem}-{v}.png" for v in VIEWS}


def contact_sheet(shots, out, cell=320, cols=3):
    """6 views on a grid, each cropped to its figure on the render grey."""
    from review_pair import crop_figure                 # noqa: PLC0415
    tmp = out.parent / ".crop"
    tmp.mkdir(exist_ok=True)
    sheet = Image.new("RGB", (cell * cols, cell * 2), (158, 160, 166))
    for n, v in enumerate(VIEWS):
        im = Image.open(crop_figure(shots[v], tmp / f"{out.stem}-{v}.png")).convert("RGB")
        im.thumbnail((cell, cell))
        sheet.paste(im, ((n % cols) * cell + (cell - im.width) // 2, (n // cols) * cell + (cell - im.height) // 2))
    sheet.save(out)
    return out


def cmd_render(args):
    index = tex_index()
    names = sorted(p.stem for p in (HIVE / "mdx").glob("*.mdx")) if args.name == "all" else [args.name]
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name in names:
        glb = out / "glb" / f"{name}.glb"
        glb.parent.mkdir(exist_ok=True)
        glb.write_bytes(build_glb(mdx_inspect.read_mdx(HIVE / "mdx" / f"{name}.mdx"), index))
        print(contact_sheet(shoot(glb, out / "views" / name), out / f"{name}.png"))


# ---------------------------------------------------------------- pairs and the judge

PAIRS = {"hfoo": "MutantFootman", "n02X": "OgrePudge", "n005": "MutantAcolyte"}   # the pairs the judge sees
OUT_HISTORY = ROOT / "artifacts/model-sheets/history/2026-10-30-l16-hive"
CONTROL = "l15-col-part-outline"       # v15 with the hull outline: the fair control of v16 (L15-5)


def our_views(unit, run):
    """Six render_unit views of one of our runs, at the camera its silhouette sweep chose."""
    import review_pair                                  # noqa: PLC0415
    glb = DRAFT / unit / run / "model.glb"
    return shoot(glb, HIVE / "renders/ours" / f"{unit}-{run}", review_pair.run_tilt(DRAFT / unit / run))


def pair_image(unit, name, out=None):
    """concept | our v16 | control (v15 + outline) | the Hive model, a row per view, half size -> history/2026-10-30-l16-hive/<unit>.png"""
    import eye_stage                                    # noqa: PLC0415
    import make_compare as MC                           # noqa: PLC0415
    import review_pair                                  # noqa: PLC0415
    from PIL import ImageDraw                           # noqa: PLC0415
    cols = [("concept", None), ("our v16-r1", our_views(unit, "v16-r1")), (f"control {CONTROL}", our_views(unit, CONTROL)),
            (f"Hive {name}", {v: HIVE / "renders/views" / name / f"{name}-{v}.png" for v in VIEWS})]
    with tempfile.TemporaryDirectory() as tmp:
        panels = review_pair.sheet_panels(unit, "mass", pathlib.Path(tmp))
        cw, ch = MC.CELL
        img = Image.new("RGB", (cw * len(cols), 20 + (ch + 20) * len(VIEWS)), MC.BG)
        draw = ImageDraw.Draw(img)
        for x, (label, shots) in enumerate(cols):
            draw.text((x * cw + 6, 4), label, fill=(255, 255, 255))
            for y, view in enumerate(VIEWS):
                src = panels.get("rts" if view == "wc3" else view) if shots is None else shots[view]
                cell = eye_stage.cell(src) if src else MC.empty_cell("-")
                img.paste(cell, (x * cw, 20 + y * (ch + 20)))
    out = pathlib.Path(out or OUT_HISTORY / f"{unit}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.resize((img.width // 2, img.height // 2), Image.LANCZOS).save(out)
    return out


def cmd_pair(args):
    for unit in ([args.unit] if args.unit != "all" else PAIRS):
        print(pair_image(unit, PAIRS[unit] if args.hive is None else args.hive))


def cmd_judge(args):
    """The pairwise judge with the Hive model as the visual reference of the wc3 axis: A = the control, B = our v16."""
    import review_pair                                  # noqa: PLC0415
    unit = args.unit
    ref = HIVE / "renders" / f"{PAIRS[unit]}.png"
    res = review_pair.compare(DRAFT / unit / CONTROL, DRAFT / unit / "v16-r1", unit, reference=ref,
                              work=HIVE / "renders/judge" / unit, out=DRAFT / unit / "v16-r1" / f"pairwise-ref-{ref.stem}.json")
    print(unit, PAIRS[unit], res["valid_votes"], "votes;", ", ".join(
        f"{a} {res[a]['winner']} {max(res[a]['A'], res[a]['B'])}-{min(res[a]['A'], res[a]['B'])}" for a in review_pair.AXES))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("stats")
    st.add_argument("--out", default=str(ROOT / "artifacts/model-sheets/analysis/2026-10-30-l16-hive-stats"))
    rd = sub.add_parser("render")
    rd.add_argument("name")
    rd.add_argument("--out", default=str(HIVE / "renders"))
    pr = sub.add_parser("pair")
    pr.add_argument("unit")
    pr.add_argument("--hive", default=None)
    jd = sub.add_parser("judge")
    jd.add_argument("unit", choices=sorted(PAIRS))
    args = ap.parse_args()
    {"stats": cmd_stats, "render": cmd_render, "pair": cmd_pair, "judge": cmd_judge}[args.cmd](args)


if __name__ == "__main__":
    main()
