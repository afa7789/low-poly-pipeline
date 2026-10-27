#!/usr/bin/env python3
"""Rebuild an old spider spec on the sheet-measured rig (PIPELINE section 20.L14), no LLM:

    python3 tools/blender/rig_remap.py <spec.json> <sheet.jpg> <out.json>

Parts are placed in model coordinates, not relative to their bone, so a new skeleton does
not move them. Each leg part is carried from the fixed bone it followed to the same place
along the scaled bone (same fraction of its length, same offset across it); body, head and
abdomen parts stay; the legs are scaled to the spec's own height. The output carries `rig_measure`, which build_unit scales the rig by.
"""
import copy
import json
import math
import pathlib
import sys

import rig_families as RF
import preflight
import silhouette


def carry(p, old, new):
    """Point p moved from the old bone (head, tail) to the new one: same fraction along it, same offset."""
    (h, t), (h2, t2) = old, new
    d = [t[i] - h[i] for i in range(3)]
    s = sum((p[i] - h[i]) * d[i] for i in range(3)) / sum(c * c for c in d)
    return [h2[i] + s * (t2[i] - h2[i]) + p[i] - (h[i] + s * d[i]) for i in range(3)]


def remap(doc, measure):
    """doc rebuilt on the rig scaled by `measure`: leg parts follow their bones."""
    family = doc["rig"]
    old = {n: (h, t) for n, _, h, t in RF.FAMILIES[family]}
    # the old specs ignore the rig's height (n01N is 1.29 m, the rig 0.74): legs go to the spec's own height
    k = max(preflight.bbox(p)[1][1] for p in doc["parts"]) / RF.SPIDER_H
    new = {n: ([c * k for c in h], [c * k for c in t]) for n, _, h, t in RF.scale_spider(family, measure)}
    out = copy.deepcopy(doc)
    for p in out["parts"]:
        if not p[0].startswith("leg"):
            continue
        opts = p[5]
        for end in ("from", "to"):
            opts[end] = carry(opts[end], old[p[0]], new[p[0]])
        p[3] = [(opts["from"][i] + opts["to"][i]) / 2 for i in range(3)]
        p[2][2] = math.dist(opts["from"], opts["to"])
    out["rig_measure"] = measure
    return out


def main():
    spec, sheet, dest = sys.argv[1:4]
    doc = json.loads(pathlib.Path(spec).read_text())
    measure = silhouette.measure_spider(sheet)
    pathlib.Path(dest).write_text(json.dumps(remap(doc, measure), indent=2))


if __name__ == "__main__":
    main()
