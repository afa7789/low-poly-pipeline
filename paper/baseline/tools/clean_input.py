#!/usr/bin/env python3
"""input/<id>-front.png -> input/clean/<id>.png: largest figure only (slivers of the neighbour panel repainted with the sheet grey), square padded."""
import pathlib
import sys

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

base = pathlib.Path(__file__).resolve().parents[1] / "input"
(base / "clean").mkdir(exist_ok=True)
for unit in sys.argv[1:]:
    im = Image.open(base / f"{unit}-front.png").convert("RGB")
    a = np.asarray(im).astype(int)
    bg = np.median(np.concatenate([a[:8].reshape(-1, 3), a[:, :8].reshape(-1, 3)]), axis=0)
    fg = np.abs(a - bg).sum(axis=2) > 36
    labels, n = ndimage.label(ndimage.binary_dilation(fg, iterations=4))
    sizes = ndimage.sum(np.ones_like(labels), labels, range(1, n + 1))
    keep = labels == 1 + int(np.argmax(sizes))
    out = a.copy()
    out[~keep] = bg
    s = int(max(im.size) * 1.1)
    canvas = Image.new("RGB", (s, s), tuple(int(v) for v in bg))
    canvas.paste(Image.fromarray(out.astype("uint8")), ((s - im.width) // 2, (s - im.height) // 2))
    canvas.save(base / "clean" / f"{unit}.png")
    print(unit, im.size, "->", s, "removed comps", n - 1, "bg", bg.tolist())
