#!/usr/bin/env python3
"""Build a scale-normalized review sheet: concept panels over the model renders.

    python3 tools/blender/make_compare.py <sheet.jpg> <views_dir> <stem> <out.png>

Every panel is cropped to its silhouette and fitted into the same 480x360 cell, so
the two rows are directly comparable. The sheet also carries the five views at
32 px (the gameplay read) and the WC3-angle render. This replaces the old compare
image, which scaled the whole concept sheet and the whole model sheet and therefore
never showed the two at the same body height.
"""
import argparse
import pathlib
import shutil
import subprocess
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import silhouette as S  # noqa: E402

CELL = (480, 360)
PX = (96, 72)


def magick(*args, **kw):
    subprocess.run(["magick", *map(str, args)], check=True, **kw)


def bbox(mask):
    ys, xs = np.where(mask)
    if len(ys) == 0:
        raise ValueError("empty mask")
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def crop_to_panel(src, box, scale, out):
    x0, y0, x1, y1 = [int(v * scale) for v in box]
    w, h = x1 - x0, y1 - y0
    # 3% breathing room, then fit inside the common cell without stretching.
    pad = max(4, int(0.03 * max(w, h)))
    magick(src, "-crop", f"{w + 2 * pad}x{h + 2 * pad}+{max(0, x0 - pad)}+{max(0, y0 - pad)}",
           "+repage", "-resize", f"{CELL[0]}x{CELL[1]}", "-background", "#c8c8c8",
           "-gravity", "center", "-extent", f"{CELL[0]}x{CELL[1]}", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet", type=pathlib.Path)
    ap.add_argument("views", type=pathlib.Path)
    ap.add_argument("stem")
    ap.add_argument("out", type=pathlib.Path)
    ap.add_argument("--layout", default="unit", choices=("unit", "building"))
    args = ap.parse_args()

    tmp = args.out.parent / ".compare-tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    from views import LAYOUTS
    names = LAYOUTS[args.layout]
    cpan = S.concept_panels(args.sheet, 768, args.layout)
    sheet_w = int(subprocess.run(["magick", "identify", "-format", "%w", str(args.sheet)],
                                 check=True, capture_output=True, text=True).stdout)
    sscale = sheet_w / 768
    for name in (*names, "wc3"):
        rgb = S.read_rgba(args.views / f"{args.stem}-{name}.png", 512)[..., :3].astype(np.int16)
        bg = np.median(np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]]), axis=0)
        crop_to_panel(args.views / f"{args.stem}-{name}.png",
                      bbox(np.abs(rgb - bg).sum(axis=2) > 24), 1.0, f"{tmp}/model-{name}.png")
    for name in names:
        crop_to_panel(args.sheet, bbox(cpan[name]), sscale, f"{tmp}/concept-{name}.png")
    rts = S.rts_path(args.sheet)
    if rts.exists():  # the gameplay camera, paired with the model's wc3 render
        rts_w = int(subprocess.run(["magick", "identify", "-format", "%w", str(rts)],
                                   check=True, capture_output=True, text=True).stdout)
        crop_to_panel(rts, bbox(S.foreground(rts, 768)), rts_w / 768, f"{tmp}/concept-wc3.png")

    rows_made = []

    def row(items):
        files = [f"{tmp}/{i}.png" for i in items if i]
        while len(files) < 3:
            files.append(f"{tmp}/empty.png")
        out = f"{tmp}/row-{len(rows_made)}.png"
        magick(*files, "+append", out)
        rows_made.append(out)
        return out

    if not pathlib.Path(f"{tmp}/empty.png").exists():
        magick("-size", f"{CELL[0]}x{CELL[1]}", "xc:#c8c8c8", f"{tmp}/empty.png")

    rows = [
        row(["concept-front", "concept-left", "concept-back"]),
        row(["model-front", "model-left", "model-back"]),
        row([f"concept-{names[3]}", f"concept-{names[4]}", "concept-wc3" if rts.exists() else None]),
        row([f"model-{names[3]}", f"model-{names[4]}", "model-wc3" if (args.views / f"{args.stem}-wc3.png").exists() else None]),
    ]

    # 32 px gameplay row: concept/model pairs, front -> bottom.
    px = []
    for name in names:
        for side in ("concept", "model"):
            magick(f"{tmp}/{side}-{name}.png", "-filter", "point", "-resize", f"{PX[0]}x{PX[1]}",
                   f"{tmp}/px-{side}-{name}.png")
            px.append(f"{tmp}/px-{side}-{name}.png")
    magick(*px, "+append", "-background", "#c8c8c8", "-gravity", "west",
           "-extent", f"{3 * CELL[0]}x{PX[1]}", f"{tmp}/pxrow.png")

    strip = f"{tmp}/strip.png"
    width = 3 * CELL[0]
    magick("-size", f"{width}x6", "xc:#555555", strip)
    magick(rows[0], strip, rows[1], strip, rows[2], strip, rows[3], strip, f"{tmp}/pxrow.png",
           "-append", args.out)
    shutil.rmtree(tmp, ignore_errors=True)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
