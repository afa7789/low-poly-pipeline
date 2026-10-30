#!/usr/bin/env python3
"""L14-2: what a texture variant looks like next to the concept (PIPELINE 32.L14-2).

    python3.14 tools/blender/tex_compare.py <id> [--kind mass] [--runs l14-tex-cel,...] [--out dir]

Per run and view (front/left/back/top/bottom, the renders stage 2 shot as views/<id>/model-<view>.png): the concept's colour zones
(silhouette.zone_palette) are found in the render by hue (luma matched, like the zone gate) and each zone's mean colour is read from
the render as shot. `de` = area-weighted Oklab distance between the render's zone colours and the concept's (x100: the colour the
artist painted); `shade` = the render's luma spread inside a zone over the concept's (1 = as much light and shadow as the concept,
0 = flat). Also the stage 2 zone numbers, the GLB's atlas size and the stage 2 time. Writes <out>/<id>.png (concept | runs, 6 views)
and <out>/<id>.json.
"""
import argparse
import json
import pathlib
import re
import struct
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import silhouette as S  # noqa: E402
from views import layout_of  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNS = ("l15-col-cel", "l15-col-part", "l15-col-part-outline", "l15-col-part-outline-face")
VIEWS = ("front", "left", "back", "top", "bottom")
CELL = 320


def zone_stats(rgb, labels, zones):
    """{z: (mean Oklab (3,), luma std)} of the pixels of each label z in 1..zones with at least 20 pixels."""
    out = {}
    for z in range(1, zones + 1):
        px = rgb[labels == z]
        if len(px) >= 20:
            out[z] = (S.oklab(px).mean(axis=0), float((px @ S.LUMA).std()))
    return out


def look_numbers(render, sheet_rgb, sheet_mask, centres):
    """(de, shade) of one render against one concept panel; None, None when no zone is in both."""
    bg = render[0, 0].astype(float)
    mask = np.abs(render.astype(float) - bg).sum(axis=2) > 24
    lit = render / 255.0
    lab = S.zone_labels(S.match_luma(lit, mask, sheet_rgb[sheet_mask]), mask, centres)
    ref = S.zone_labels(sheet_rgb, sheet_mask, centres, ink=True)
    solid = sheet_rgb.max(axis=-1) > S.INK
    a, b = zone_stats(lit, lab, len(centres)), zone_stats(sheet_rgb, np.where(solid, ref, 0), len(centres))
    num = den = sh = 0.0
    for z in set(a) & set(b):
        w = float((ref == z).sum())
        num += w * float(np.linalg.norm(a[z][0] - b[z][0]))
        sh += w * (a[z][1] / max(b[z][1], 1e-3))
        den += w
    return (round(100 * num / den, 2), round(sh / den, 3)) if den else (None, None)


def atlas_kb(glb):
    """KB of the images embedded in a GLB (its atlas); 0 when it has none."""
    data = pathlib.Path(glb).read_bytes()
    n = struct.unpack("<I", data[12:16])[0]
    doc = json.loads(data[20:20 + n])
    return round(sum(doc["bufferViews"][i["bufferView"]]["byteLength"] for i in doc.get("images", []) if "bufferView" in i) / 1024, 1)


def glb_tris(glb):
    """(total triangles, triangles beyond the biggest mesh, the body): the second number is what an outline hull / face quad adds."""
    data = pathlib.Path(glb).read_bytes()
    doc = json.loads(data[20:20 + struct.unpack("<I", data[12:16])[0]])
    per = [sum(doc["accessors"][p["indices"]]["count"] // 3 for p in m["primitives"] if "indices" in p) for m in doc["meshes"]]
    return sum(per), sum(per) - max(per)


def run_row(run, unit, sheet, layout):
    """The numbers of one run: per view zones mean/cover, luma_l1, de, shade; atlas KB."""
    zones = json.loads((run / "stage2/colour.json").read_text())["zones"]
    rgb = S.read_rgba(sheet, 768)[..., :3] / 255.0
    panels = S.concept_panels(sheet, layout=layout)
    _, centres, _ = S.zone_palette(sheet)
    views = {}
    for v in VIEWS:
        shot = run / "views" / unit / f"model-{v}.png"
        if v not in zones or not shot.exists():
            continue
        render = np.asarray(Image.open(shot).convert("RGB"))
        de, shade = look_numbers(render, rgb, panels[v], centres)
        views[v] = {"mean": zones[v]["mean"], "cover": zones[v]["cover"], "luma_l1": zones[v].get("luma_l1"), "de": de, "shade": shade}
    tris, extra = glb_tris(run / "model.glb")
    return {"views": views, "atlas_kb": atlas_kb(run / "model.glb"), "tris": tris, "tris_extra_meshes": extra}


def fit(im):
    """`im` cropped to the pixels that differ from its corner colour, with a margin (a render is one small figure on a big flat ground)."""
    box = ImageChops.difference(im, Image.new("RGB", im.size, im.getpixel((0, 0)))).convert("L").point(lambda v: 255 if v > 24 else 0).getbbox()
    if not box:
        return im
    m = max(box[2] - box[0], box[3] - box[1]) // 10
    return im.crop((max(box[0] - m, 0), max(box[1] - m, 0), min(box[2] + m, im.width), min(box[3] + m, im.height)))


def contact(unit, runs, panels, out):
    """concept | each run, one row per view (front left back top bottom rts)."""
    names = ["concept", *(re.sub(r"^l1[45]-(tex|col|fix)-", "", r.name) for r in runs)]
    img = Image.new("RGB", (CELL * len(names), CELL * 6), (158, 160, 166))
    shots = [("front", "front"), ("left", "left"), ("back", "back"), ("top", "top"), ("bottom", "bottom"), ("rts", "wc3")]
    for row, (view, shot) in enumerate(shots):
        cells = [panels[view], *(r / "views" / unit / f"model-{shot}.png" for r in runs)]
        for col, path in enumerate(cells):
            if not pathlib.Path(path).exists():
                continue
            im = fit(Image.open(path).convert("RGB")) if col else Image.open(path).convert("RGB")
            im.thumbnail((CELL, CELL))
            img.paste(im, (col * CELL + (CELL - im.width) // 2, row * CELL + (CELL - im.height) // 2))
    d = ImageDraw.Draw(img)
    for col, name in enumerate(names):
        d.text((col * CELL + 6, 6), name, fill=(0, 0, 0))
    img.save(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("id")
    ap.add_argument("--kind", default="mass")
    ap.add_argument("--runs", default=",".join(RUNS))
    ap.add_argument("--out", type=pathlib.Path, default=ROOT / "artifacts/model-sheets/history/2026-10-30-l15-colour")
    a = ap.parse_args()
    import split_sheet
    base = ROOT / "artifacts/model-sheets/runs/draft" / a.id
    runs = [base / r for r in a.runs.split(",") if (base / r / "stage2/colour.json").exists()]
    sheet = ROOT / "artifacts/model-sheets/refs" / a.id / "sheet.jpg"
    layout = layout_of(a.kind)
    a.out.mkdir(parents=True, exist_ok=True)
    rows = {r.name: run_row(r, a.id, sheet, layout) for r in runs}
    (a.out / f"{a.id}.json").write_text(json.dumps(rows, indent=2))
    with __import__("tempfile").TemporaryDirectory() as t:
        contact(a.id, runs, split_sheet.split(sheet, pathlib.Path(t), a.id, layout), a.out / f"{a.id}.png")
    for name, r in rows.items():
        v = r["views"]
        print(name, "mean", {k: x["mean"] for k, x in v.items()}, "de", {k: x["de"] for k, x in v.items()}, "atlas", r["atlas_kb"], "tris", r["tris"], "+", r["tris_extra_meshes"])


if __name__ == "__main__":
    main()
