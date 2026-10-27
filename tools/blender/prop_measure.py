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
    """Indices of the parts that form the prop held by an arm bone, or []: the parts marked opts "prop" with
    a hand anchor (PIPELINE 23.L5-3) when the spec has them, else found by size and material."""
    marked = [i for i, p in enumerate(parts) if PF.is_prop(p) and str(p[5].get("anchor", "")).startswith("hand")]
    if marked:
        return marked
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


def crop_props(path, out_dir, stem, size=384, pad=0.05, px=512):
    """Write one PNG per drawing of the props sheet, left to right, each cut from the
    full-resolution sheet with a margin. Returns the paths."""
    from PIL import Image
    sheet = Image.open(path).convert("RGB")
    fg = S.foreground(path, size)
    boxes = []
    for c in S.components(fg):
        if c.sum() < PROP_AREA * fg.size:
            continue
        ys, xs = np.where(c)
        boxes.append((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    paths = []
    for n, (x0, y0, x1, y1) in enumerate(sorted(boxes), start=1):
        m = pad * max(x1 - x0, y1 - y0)
        box = [max(v, 0) for v in (x0 - m, y0 - m)] + [min(v, size) for v in (x1 + m, y1 + m)]
        crop = sheet.crop(tuple(round(v * sheet.width / size) for v in box))
        crop.thumbnail((px, px))
        paths.append(pathlib.Path(out_dir) / f"{stem}-{n}.png")
        crop.save(paths[-1])
    return paths


def words(text):
    return {w for w in text.lower().replace("-", " ").split() if len(w) > 3}


def match_prop(name, props):
    """Index in props.json of the prop a part's opts "prop" name stands for: one name contains the other,
    else the entry sharing the most words of 4+ letters; None when none shares a word."""
    name = name.lower()
    scores = [(name in p["name"].lower() or p["name"].lower() in name, len(words(name) & words(p["name"])))
              for p in props]
    best = max(range(len(props)), key=scores.__getitem__, default=None)
    return best if best is not None and any(scores[best]) else None


def crops_by_part(parts, props, crops):
    """{str(part index): crop png} for each part marked opts "prop" whose name matches a props.json entry
    (the n-th crop is the n-th entry: crop_props reads the sheet left to right, like props.json)."""
    out = {}
    for i, p in enumerate(parts):
        n = match_prop(str(p[5]["prop"]), props) if PF.is_prop(p) else None
        if n is not None and n < len(crops):
            out[str(i)] = str(crops[n])
    return out


PROP_SEEN = 0.002    # prop_reads: a prop reads in a view when its largest piece covers this share of the figure ...
PROP_WHOLE = 0.5     # ... and is at least this share of what shows of it (the rest is not a scatter of crumbs)


def prop_views(unit, prop_name, props, parts_json=None):
    """The views of front/left/back in which the unit's sheet shows a prop: from refs/<id>/parts.json
    (L5-1, a part with "prop": true and a box2d for the view) when it exists and names the prop, else from
    props.json: a prop worn on the back shows from the side and the back, any other from the front and side."""
    if parts_json and pathlib.Path(parts_json).exists():
        rows = [p for p in json.loads(pathlib.Path(parts_json).read_text()).get("parts", []) if p.get("prop")]
        n = match_prop(prop_name, rows)
        if n is not None:
            return [v for v in ("front", "left", "back") if v in rows[n].get("box2d", {})]
    n = match_prop(prop_name, props)
    back = n is not None and "back" in props[n]["where"]
    return ["left", "back"] if back else ["front", "left"]


def prop_seen(rgb, alpha, colour):
    """(share of the figure, share of the prop's visible pixels) of the prop's largest piece in an ID
    render: `colour` is one of preflight.PROP_IDS; nothing of it shows -> (0, 0)."""
    from scipy.ndimage import label
    mask = (np.abs(rgb - np.array(colour) * 255).max(axis=-1) < 40) & alpha
    pieces, n = label(mask)
    if not n:
        return 0.0, 0.0
    biggest = int(np.bincount(pieces.ravel())[1:].max())
    return biggest / max(int(alpha.sum()), 1), biggest / int(mask.sum())


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
