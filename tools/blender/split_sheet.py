#!/usr/bin/env python3
"""Split a 3+2 concept sheet into one named image per view.

    python3 tools/blender/split_sheet.py <sheet.jpg> <outdir> [--stem n01X]

Writes <outdir>/<stem>-front.png, -left, -back, -top, -bottom: each panel cropped
tight around its figure (plus a margin) from the full-resolution sheet. When the sheet
has an RTS view beside it (<sheet>-rts.jpg), it is copied in as <stem>-rts.png. The panels
are found by the same background keying `silhouette.py` gates on, so a view image
and its silhouette mask always agree on what "front" is.
"""
import argparse
import pathlib
import subprocess
import sys

import numpy as np

from silhouette import concept_panels, rts_path

SIZE = 768
MARGIN = 0.06


def panel_boxes(sheet, size=SIZE, layout="unit"):
    """Pixel box (x0, y0, x1, y1) of each panel's figure, in `size`-square coordinates."""
    boxes = {}
    for name, mask in concept_panels(sheet, size, layout).items():
        ys, xs = np.where(mask)
        boxes[name] = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    return boxes


def scaled(box, sx, sy, width, height):
    """Map a box from the keyed square back to the sheet's pixels, padded by MARGIN."""
    x0, y0, x1, y1 = box
    pad = MARGIN * max(x1 - x0, y1 - y0)
    return (max(0, round((x0 - pad) * sx)), max(0, round((y0 - pad) * sy)),
            min(width, round((x1 + pad) * sx)), min(height, round((y1 + pad) * sy)))


def split(sheet, outdir, stem, layout="unit"):
    width, height = map(int, subprocess.run(
        ["magick", "identify", "-format", "%w %h", str(sheet)],
        check=True, capture_output=True, text=True).stdout.split())
    outdir.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, box in panel_boxes(sheet, layout=layout).items():
        x0, y0, x1, y1 = scaled(box, width / SIZE, height / SIZE, width, height)
        path = outdir / f"{stem}-{name}.png"
        subprocess.run(["magick", str(sheet), "-crop", f"{x1 - x0}x{y1 - y0}+{x0}+{y0}",
                        "+repage", str(path)], check=True)
        written[name] = path
    if rts_path(sheet).exists():
        written["rts"] = outdir / f"{stem}-rts.png"
        subprocess.run(["magick", str(rts_path(sheet)), str(written["rts"])], check=True)
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet", type=pathlib.Path)
    ap.add_argument("outdir", type=pathlib.Path)
    ap.add_argument("--stem", default=None)
    ap.add_argument("--layout", default="unit", choices=("unit", "building"))
    args = ap.parse_args()
    for name, path in split(args.sheet, args.outdir, args.stem or args.sheet.stem, args.layout).items():
        print(f"{name:7} {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
