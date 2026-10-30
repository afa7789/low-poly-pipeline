#!/usr/bin/env python3
"""Monocular depth of the sheet's front and left panels (Depth Anything V2 small), opt-in `--depth` (PIPELINE 23.L5-4b).

    python3.14 tools/blender/depth_map.py <sheet.jpg> <outdir>        # writes depth-front.png, depth-left.png

A pre-trained network, inference only, CPU/MPS: not a 3D generator. It answers what the left view cannot when two
parts line up along its axis: which one is nearer the camera in the front panel. `disparity` returns, per view,
a map in the fit's canvas layout (silhouette.normalize of the figure) with the figure's relative disparity in
0..1, larger = nearer the camera. `part_disparity` is the median over a part mask; `rank_order` turns those into
the integer depth_order parts.json would carry (relative to the torso).
"""
import argparse
import json
import pathlib
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import parts_fit  # noqa: E402
import silhouette  # noqa: E402

MODEL = "depth-anything/Depth-Anything-V2-Small-hf"
LEVELS = 254            # canvas disparity is stored as an 8-bit label (0 = outside the figure)
MIN_CALIB = 4           # parts needed to fit disparity -> z
MIN_R = 0.7             # |correlation| with the triangulated landmarks' z under which the fitted map is not trusted to move a part (L12-8; was .3 against hand-boxed parts)
INIT_MAX = 0.10         # largest z shift of an initialised part, in heights
STEP = 0.12             # a part this much nearer (or farther) than the torso in disparity gets depth_order +-1
_pipe = []


def estimator():
    """The transformers depth-estimation pipeline, loaded once (MPS when there is one, else CPU)."""
    if not _pipe:
        import torch
        from transformers import pipeline
        _pipe.append(pipeline("depth-estimation", model=MODEL, device="mps" if torch.backends.mps.is_available() else "cpu"))
    return _pipe[0]


def panel_disparity(sheet, fig):
    """Disparity (0..1, larger = nearer) of the figure's pixels in 768-square coordinates, from the sheet's
    crop of that panel; 0 outside the figure. The figure is rescaled between its 2nd and 98th percentile."""
    img = Image.open(sheet).convert("RGB")
    sx, sy = img.width / fig.shape[1], img.height / fig.shape[0]
    x0, y0, x1, y1 = parts_fit.panel_rect(fig)
    crop = img.crop((round(x0 * sx), round(y0 * sy), round(x1 * sx), round(y1 * sy)))
    pred = np.asarray(estimator()(crop)["predicted_depth"].squeeze().float().cpu(), np.float32)
    small = np.asarray(Image.fromarray(pred).resize((x1 - x0, y1 - y0), Image.BILINEAR), np.float32)
    full = np.zeros(fig.shape, np.float32)
    full[y0:y1, x0:x1] = small
    lo, hi = np.percentile(full[fig], (2, 98))
    return np.where(fig, np.clip((full - lo) / max(hi - lo, 1e-6), 0, 1), 0.0)


def disparity(sheet, views=parts_fit.PART_VIEWS):
    """{view: canvas map}: the figure's relative disparity in the fit's layout (-1 outside the figure)."""
    out = {}
    for view, fig in silhouette.concept_panels(sheet).items():
        if view in views:
            label = np.where(fig, np.round(panel_disparity(sheet, fig) * (LEVELS - 1)).astype(np.int32) + 1, 0)
            canvas = silhouette.normalize(label)
            out[view] = np.where(canvas > 0, (canvas - 1) / (LEVELS - 1), -1.0)
    return out


def part_disparity(maps, masks, view="front"):
    """{part index: median disparity inside its mask in `view`} (`masks`: PartTerms.masks)."""
    return {i: float(np.median(maps[view][m & (maps[view] >= 0)])) for (i, v), m in masks.items()
            if v == view and (m & (maps[view] >= 0)).any()}


def rank_order(values, torso):
    """{part index: integer depth_order}: the disparity gap to the torso in STEP units, rounded toward zero."""
    return {i: int((d - torso) / STEP) for i, d in values.items()}


def calibrate(disp, z):
    """(a, b, r): z = a x disp + b by least squares over the parts that have both, and their Pearson r."""
    d, z = np.asarray(disp, float), np.asarray(z, float)
    if len(d) < MIN_CALIB or d.std() < 1e-6 or z.std() < 1e-6:
        return 0.0, float(z.mean()) if len(z) else 0.0, 0.0
    a, b = np.polyfit(d, z, 1)
    return float(a), float(b), float(np.corrcoef(d, z)[0, 1])


def landmark_calibration(sheet, parts_doc, disp=None):
    """{a, b, r, n}: z = a x disparity + b over depth_rule's landmarks (joints and part centres the front and left panels both show, whose two
    views agree on the height), the disparity the median of a 5 x 5 window of the front panel at the landmark; r is Pearson's. The target
    is the triangulation, not the hand-boxed parts L5-4b fitted on (PIPELINE 30.L12-8)."""
    import depth_rule
    frames = depth_rule.frames_for(sheet, parts_doc)
    fig = frames.panels["front"]
    disp = panel_disparity(sheet, fig) if disp is None else disp
    d, z = [], []
    for m in depth_rule.landmarks(parts_doc, frames):
        if m["gap"] > depth_rule.RESID_MAX or "face" in m:
            continue
        x, y = (int(v) for v in frames.px("front", *m["front_uv"]))
        win, inside = disp[max(y - 2, 0):y + 3, max(x - 2, 0):x + 3], fig[max(y - 2, 0):y + 3, max(x - 2, 0):x + 3]
        if inside.any():
            d.append(float(np.median(win[inside])))
            z.append(m["xyz"][2])
    a, b, r = calibrate(d, z)
    return {"a": a, "b": b, "r": round(r, 3), "n": len(d)}


def shifted(part, dz):
    """A copy of a spec part moved dz along z (forward): its `at` and from/to."""
    out = [*part[:3], [part[3][0], part[3][1], part[3][2] + dz], *part[4:5], dict(part[5] or {})]
    for end in ("from", "to"):
        if end in out[5]:
            out[5][end] = [*out[5][end][:2], out[5][end][2] + dz]
    return out


def depth_init(parts, pf, parts_doc, maps, height, centres, calib=None):
    """(parts, report): `--depth`. The front disparity of every spec part with a part mask gives
    (1) the depth order of the pairs, when parts.json carries no depth_order, and (2) a z for the parts the
    left panel does not show (no left box): z = a x disparity + b with (a, b) fitted on the parts that have both,
    used only when |r| >= MIN_R, moved at most INIT_MAX x height. `centres` are the spec parts' centres (right, up, forward).
    `calib` (landmark_calibration) replaces the fit on the parts that have a left mask: the line and its r come from the triangulated landmarks."""
    disp = part_disparity(maps, pf.masks)
    scale = height / float(parts_doc.get("H") or height)
    z_of = {i: (parts_doc["parts"][pf.assoc[i]]["box3d"][0][2] + parts_doc["parts"][pf.assoc[i]]["box3d"][1][2]) / 2 * scale
            for i in disp if (i, "left") in pf.masks}
    a, b, r = (calib["a"], calib["b"], calib["r"]) if calib else calibrate([disp[i] for i in z_of], list(z_of.values()))
    report = {"disparity": {i: round(d, 3) for i, d in disp.items()}, "r_front_vs_left_z": round(r, 3), "calibration": [a, b],
              "moved": {}, **({"landmarks": calib["n"]} if calib else {})}
    out = list(parts)
    if (r if calib else abs(r)) >= MIN_R:        # the landmarks' z is the sheet's forward: disparity must rise with it (r < 0: the sheet's z points the other way, nothing moves)
        for i, d in disp.items():
            if i in z_of:
                continue
            dz = float(np.clip(a * d + b - centres[i][2], -INIT_MAX * height, INIT_MAX * height))
            out[i] = shifted(parts[i], dz)
            report["moved"][i] = round(dz, 3)
    if not any(p.get("depth_order") for p in parts_doc["parts"]):
        torso = float(np.median(list(disp.values()))) if disp else 0.0
        pf.pairs = parts_fit.front_pairs(parts_doc, pf.assoc, rank_order(disp, torso))
        report["pairs_from_depth"] = len(pf.pairs)
    return out, report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet", type=pathlib.Path)
    ap.add_argument("out", type=pathlib.Path)
    ap.add_argument("--landmarks", type=pathlib.Path, default=None, help="a parts.json: print the Pearson r of the disparity with its triangulated landmarks' z")
    args = ap.parse_args()
    if args.landmarks:
        print(json.dumps(landmark_calibration(args.sheet, json.loads(args.landmarks.read_text()))))
    args.out.mkdir(parents=True, exist_ok=True)
    for view, canvas in disparity(args.sheet).items():
        Image.fromarray((np.clip(canvas, 0, 1) * 255).astype(np.uint8)).save(args.out / f"depth-{view}.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
