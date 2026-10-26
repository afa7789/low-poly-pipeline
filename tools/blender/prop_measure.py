#!/usr/bin/env python3
"""Measure the prop a unit carries on its own, against the props sheet.

    python3 tools/blender/prop_measure.py <sheet-props.jpg> <spec.json> <outdir>

The silhouette gate sees the prop only as part of the whole figure, where a club that is
too thin or too short costs a few pixels of IoU. Here the spec's prop parts are built and
rendered alone and compared, height-normalised like every other view, with each prop drawn
on the props sheet (the sheet has several: spear, backpack, lantern). The best match wins;
the prop may be rotated (the sheet draws a club lying down, the model holds it up) and
seen from the front or the side. Writes <outdir>/prop.json and prints it:
{"parts": [index...], "iou": best, "view": "front|left", "component": n of the sheet}.

A prop part is found, not marked (specs carry no marker): on an arm bone, a part as long
as PROP_LONG of the unit's height is a weapon; every part on that bone that touches it and
is not the limb's own material joins it. Props worn on the spine or pelvis (backpack,
lantern, tank) are not measured: ponytail, add when a spec marks its prop parts.
"""
import json
import pathlib
import subprocess
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import preflight as PF  # noqa: E402
import silhouette as S  # noqa: E402

ARM_BONES = ("arm.", "forearm.", "hand.")
PROP_LONG = 0.40        # a part this long (x unit height) on an arm bone is a weapon
PROP_AREA = 0.004       # a drawing under this share of the props sheet is not a prop
VIEWS = ("front", "left")


def extent(box):
    return max(box[1][i] - box[0][i] for i in range(3))


def touches(a, b):
    return all(a[0][i] <= b[1][i] and b[0][i] <= a[1][i] for i in range(3))


def prop_parts(parts):
    """Indices of the parts that form the prop held by an arm bone, or []."""
    boxes = [PF.bbox(p) for p in parts]
    height = max(max(b[1][1] for b in boxes), 1e-6)
    arms = [q[4] for q in parts if q[0].startswith(ARM_BONES)]
    limb = max(set(arms), key=arms.count, default=None)      # the arms' own material
    found = set()
    for i, p in enumerate(parts):
        if not p[0].startswith(ARM_BONES) or p[4] == limb or extent(boxes[i]) < PROP_LONG * height:
            continue
        group, more = {i}, {i}
        while more:
            more = {j for j, q in enumerate(parts) if q[0] == p[0] and q[4] != limb and j not in group
                    and any(touches(boxes[j], boxes[k]) for k in group)}
            group |= more
        found |= group
    return sorted(found)


def sheet_props(path, size=384):
    """One normalized mask per drawing on the props sheet (connected foreground pieces)."""
    fg = S.foreground(path, size)
    return [S.normalize(c) for c in S.components(fg) if c.sum() >= PROP_AREA * fg.size]


def orientations(mask):
    """The mask as drawn, turned by 90 degree steps, and mirrored: 8 normalized variants."""
    m = S.crop(mask)
    return [S.normalize(v) for k in range(4) for v in (np.rot90(m, k), np.fliplr(np.rot90(m, k)))]


def best_match(drawings, masks):
    """(IoU, view, drawing index) of the best model view x orientation x drawing."""
    best = (0.0, None, None)
    for view, mask in masks.items():
        for turned in orientations(mask):
            for n, drawing in enumerate(drawings):
                score = S.iou(drawing, turned)
                best = max(best, (score, view, n), key=lambda t: t[0])
    return best


def main():
    sheet, spec_path, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    doc = json.loads(spec_path.read_text())
    parts = PF.load_parts(doc)
    idx = prop_parts(parts)
    report = {"parts": idx, "iou": None, "view": None, "component": None}
    if idx:
        solo = out / "prop.json"
        # on the static building rig (one body bone) the prop stays where the spec put it,
        # not where the unit's pose swings its hand
        solo.write_text(json.dumps({"rig": "building", "palette": doc.get("palette"),
                                    "parts": [["body", *parts[i][1:]] for i in idx]}))
        glb = out / "prop.glb"
        subprocess.run(["blender", "-b", "-P", str(HERE / "build_unit.py"), "--", str(solo), str(glb)],
                       capture_output=True, text=True)
        subprocess.run(["blender", "-b", "-P", str(HERE / "render_silhouette.py"), "--", str(glb),
                        str(out / "sil")], capture_output=True, text=True)
        masks = {v: m[0] for v, m in S.model_panels(out / "sil", "prop").items() if v in VIEWS}
        drawings = sheet_props(sheet)
        if masks and drawings:
            score, view, n = best_match(drawings, masks)
            report.update(iou=round(score, 4), view=view, component=n)
    (out / "prop-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
