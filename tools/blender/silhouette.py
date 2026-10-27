#!/usr/bin/env python3
"""Silhouette gate: compare an exported unit with its approved concept sheet.

    python3 tools/blender/silhouette.py <sheet.jpg> <unit.glb> <outdir>

Both sides are reduced to a binary mask, normalized by body height and compared per
view: front / left / back / top. Prints IoU, width-profile L1 and a 32x32 IoU, and
exits non-zero when the front, profile or top view is below the gate.

This is the check that was missing while ten prose-review rounds plateaued: the
reviewer could see "the wheel is edge-on" only because it was told to look, while
the pipeline had no numeric target. The concept panels are segmented by the empty
background bands of the 3+2 template, so the same code works for every unit sheet.
"""
import argparse
import json
import pathlib
import subprocess
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANVAS_H = 256
CANVAS_W = 384
VIEWS = ["front", "left", "back", "top"]
# Shape gates (PIPELINE §18.F), min silhouette IoU per view; top/bottom are scored at the
# tilt the sweep picks, rts at the (elevation, azimuth) it picks. Calibrated on clay rebuilds.
GATES = {"front": 0.75, "left": 0.65, "back": 0.70, "top": 0.65, "bottom": 0.65, "rts": 0.70}
ZONE_GATED = ("front", "left")   # views whose colour-zone numbers can fail the gate
# Colour zones (PIPELINE §18): what the silhouette cannot see inside the contour.
ZONE_VIEWS = ("front", "left", "back", "top", "bottom")
ZONE_GATED = ZONE_VIEWS   # all five views gate the colour (PIPELINE §18.F)
PIECE_MIN = 0.005      # a zone piece under this share of the figure is noise, not a part
INK = 0.15             # sheet pixels this dark are outline, not a zone
ZONE_GATES = {"mean": 0.08, "cover": 0.30}   # gated views; the lowest of the 7 hard-v1 is 0.100 / 0.368
LOST = 0.02            # a zone of ZONE_SHARE+ under this IoU is "lost" (the model has none of it)
ZONE_SHARE = 0.03      # a zone under this share of the figure does not set "min"
SLACK = 4              # px of tolerance for a part that is there but offset
SMOOTH = 2             # mode-filter radius on the 256-px canvas
INK_FILL = 10          # px an outline is grown over from the zones beside it


def read_rgba(path, size):
    raw = subprocess.run(["magick", str(path), "-resize", f"{size}x{size}!",
                          "-depth", "8", "rgba:-"], check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.uint8).reshape(size, size, 4)


def foreground(path, size):
    """Key the flat background (the median border colour) out of a concept image."""
    arr = read_rgba(path, size)
    rgb, alpha = arr[..., :3].astype(np.int16), arr[..., 3]
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    bg = np.median(border, axis=0)
    return (np.abs(rgb - bg).sum(axis=2) > 30) & (alpha > 10)


def rts_path(sheet):
    """The gameplay-camera concept drawn from this sheet by generate.py --image:
    refs/<id>/sheet.jpg -> sheet-rts.jpg, sheet-hard.jpg -> sheet-hard-rts.jpg."""
    return sheet.with_name(f"{sheet.stem}-rts.jpg")


DRIFT_VIEWS = ("front", "left", "back")
DRIFT_MIN = 0.90   # 7 units measured: 0.90-0.98, n01N left 0.76 and n01I left 0.88 below


def sheet_drift(approved, redraw, layout="unit"):
    """Silhouette IoU of a redrawn sheet (the hard variant) against the approved one,
    per panel, plus the RTS views when both exist. Only DRIFT_VIEWS gate: the RTS images
    are two independent draws and differ in camera, not in design."""
    a = {k: normalize(v) for k, v in concept_panels(approved, layout=layout).items()}
    b = {k: normalize(v) for k, v in concept_panels(redraw, layout=layout).items()}
    out = {k: round(iou(a[k], b[k]), 4) for k in a if k in b}
    if rts_path(approved).exists() and rts_path(redraw).exists():
        out["rts"] = round(iou(normalize(foreground(rts_path(approved), 768)),
                               normalize(foreground(rts_path(redraw), 768))), 4)
    return out


def gaps(mask, axis, lo, hi):
    """Empty runs of rows (axis=1, offset lo) or columns (axis=0) inside mask[lo:hi]."""
    counts = mask[lo:hi].any(axis=axis)
    offset = lo if axis == 1 else 0
    found, s = [], None
    for i, v in enumerate(counts):
        if not v and s is None:
            s = i
        elif v and s is not None:
            found.append((s + offset, i + offset))
            s = None
    if s is not None:
        found.append((s + offset, len(counts) + offset))
    return found


def concept_panels(path, size=768, layout="unit"):
    """Key the flat background, split the 3+2 template on its empty bands, and
    return one boolean mask per panel in reading order, named by the sheet layout
    (views.LAYOUTS: a unit's bottom row is top/bottom, a building's right/roof)."""
    from views import LAYOUTS
    fg = foreground(path, size)

    runs = gaps(fg, 1, 0, size)
    interior = [r for r in runs if r[0] > 0.2 * size and r[1] < 0.8 * size]
    split = (max(interior, key=lambda r: r[1] - r[0])[0]
             + max(interior, key=lambda r: r[1] - r[0])[1]) // 2 if interior else size // 2

    top_x = gaps(fg, 0, 0, split)
    top_x = sorted(top_x, key=lambda r: r[1] - r[0], reverse=True)[:2]
    inner = sorted([(a, b) for a, b in top_x if a > 0.1 * size and b < 0.9 * size])
    cuts = [(a + b) // 2 for a, b in inner] if len(inner) == 2 else [size // 3, 2 * size // 3]
    bot_x = gaps(fg, 0, split, size)
    bot_x = sorted([r for r in bot_x if r[0] > 0.1 * size and r[1] < 0.9 * size],
                   key=lambda r: r[1] - r[0], reverse=True)[:1]
    cut_b = (bot_x[0][0] + bot_x[0][1]) // 2 if bot_x else size // 2

    bounds = [(0, cuts[0], 0, split), (cuts[0], cuts[1], 0, split), (cuts[1], size, 0, split),
              (0, cut_b, split, size), (cut_b, size, split, size)]
    cells = [(name, *box) for name, box in zip(LAYOUTS[layout], bounds)]
    panels = {}
    for name, x0, x1, y0, y1 in cells:
        cell = fg[y0:y1, x0:x1]
        if not cell.any():
            raise SystemExit(f"concept panel '{name}' is empty after background keying")
        # Keep full-image coordinates: every consumer (normalize, compare crops)
        # expects one coordinate space.
        full = np.zeros_like(fg)
        full[y0:y1, x0:x1] = cell
        panels[name] = full
    return panels


def measure(sheet, size=768):
    """Code-derived proportions from the five panels, in fractions of front-view H.
    The spec author gets numbers, not adjectives; this is the measurement stage the
    v9 review said was missing."""
    panels = concept_panels(sheet, size)

    def profile(mask):
        ys, xs = np.where(mask)
        h = ys.max() - ys.min() + 1
        spans = []
        for f in np.linspace(0.0, 1.0, 21):
            y = ys.min() + int(f * (h - 1))
            cols = np.where(mask[y])[0]
            spans.append((cols.max() - cols.min() + 1) / h if len(cols) else 0.0)
        return h, spans

    fh, fs = profile(panels["front"])
    lh, ls = profile(panels["left"])
    k = lh / fh
    return {
        "shoulder_span": round(max(fs[2:7]), 3),
        "fist_span": round(max(fs[12:17]), 3),
        "stance": round(max(fs[19:]), 3),
        "body_depth": round(max(ls[8:16]) * k, 3),
        "foot_length": round(max(ls[18:]) * k, 3),
        # the widest top row is the shoulder line: how far below the top it sits
        "head_clear": round(0.05 * max(range(2, 7), key=lambda i: fs[i]), 3),
        "front_width_profile": [round(v, 3) for v in fs],
        "left_width_profile": [round(v * k, 3) for v in ls],
    }


def read_mask(path):
    return read_rgba(path, 512)[..., 3] > 16


LUMA = np.array([0.299, 0.587, 0.114])
LW = 0.35


def figure_pixels(path, size=768, seed=0):
    """Up to 20000 non-ink figure pixels (rgb 0-1) of the front, left and back panels."""
    rgb = read_rgba(path, size)[..., :3].reshape(-1, 3).astype(float) / 255.0
    panels = concept_panels(path, size)
    mask = (panels["front"] | panels["left"] | panels["back"]).reshape(-1)
    px = rgb[mask]
    px = px[px.max(axis=1) > 0.12]
    rng = np.random.default_rng(seed)
    return px[rng.choice(len(px), min(len(px), 20000), replace=False)]


def kmeans(x, luma, k, iters=12):
    """(centres, label) of rows x, seeded from k quantiles of their luma."""
    centres = x[np.argsort(luma)[np.linspace(0, len(x) - 1, k).astype(int)]]
    for _ in range(iters):
        label = np.argmin(((x[:, None, :] - centres[None]) ** 2).sum(axis=2), axis=1)
        centres = np.array([x[label == i].mean(axis=0) if (label == i).any() else centres[i]
                            for i in range(k)])
    return centres, label


def hexcolour(c):
    return "#" + "".join(f"{round(v * 255):02X}" for v in c)


def sheet_colours(path, k=6, size=768, seed=0):
    """The sheet's flat tones, code-measured: k-means over the figure pixels of the
    front, left and back panels. Ink outlines (near black) are dropped. Returns
    [(hex, share)] by share, so the spec author picks colours instead of guessing."""
    px = figure_pixels(path, size, seed)
    centres, label = kmeans(px, px @ LUMA, k)
    share = np.bincount(label, minlength=k) / len(px)
    return [(hexcolour(centres[i]), round(float(share[i]), 3)) for i in np.argsort(-share)
            if share[i] >= 0.02]


def model_panels(render_dir, stem):
    """view -> {camera: mask} for every rendered view. Top and bottom carry every
    rendered tilt, the RTS view every (elevation, azimuth), the rest tilt 0."""
    from views import RTS, TILTED, TILTS, VIEWS
    panels = {}
    for name in [v for v in VIEWS if (render_dir / f"{stem}-sil-{v}.png").exists()]:
        panels[name] = {0: read_mask(render_dir / f"{stem}-sil-{name}.png")}
        if name in TILTED:
            for t in TILTS:
                path = render_dir / f"{stem}-sil-{name}@{t}.png"
                if t and path.exists():
                    panels[name][t] = read_mask(path)
    rts = {cam: render_dir / f"{stem}-sil-rts@{cam[0]}_{cam[1]}.png" for cam in RTS}
    panels["rts"] = {cam: read_mask(path) for cam, path in rts.items() if path.exists()}
    return panels


def zone_feature(rgb):
    """Colour as (red-green, yellow-blue, 0.35 x luma) rows: hue and chroma decide a zone,
    lightness barely does, because the model's render is darker than the sheet's lit tones
    (a grey plate must still be the sheet's grey, not its dark brown)."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    return np.stack([r - g, (r + g) / 2 - b, LW * (rgb @ LUMA)], axis=-1)


def zone_palette(path, k=4):
    """(names, centres): the sheet's colour zones, k-means in zone_feature space over its
    figure pixels. A zone is named by the mean colour of its pixels. Under 2 % is dropped."""
    px = figure_pixels(path)
    bg = np.median(read_rgba(path, 768)[0, :, :3], axis=0) / 255.0
    px = px[np.abs(px - bg).sum(axis=1) > 0.3]   # the anti-aliased halo is not a zone
    centres, label = kmeans(zone_feature(px), px @ LUMA, k)
    keep = [i for i in np.argsort(-np.bincount(label, minlength=k)) if (label == i).mean() >= 0.02]
    return [hexcolour(px[label == i].mean(axis=0)) for i in keep], centres[keep]


def nearest(rgb, centres):
    """Zone index + 1 of every row of an (n, 3) colour array."""
    return np.argmin(((zone_feature(rgb)[:, None, :] - centres[None]) ** 2).sum(axis=2), axis=1) + 1


def match_luma(lit, mask, target):
    """The render's rgb with its luma histogram matched to the sheet figure's `target`
    pixels: the render is unlit albedo, the sheet is lit, and zones must not be exposure."""
    qs = np.linspace(0, 1, 33)
    luma = lit @ LUMA
    new = np.interp(luma, np.quantile(luma[mask], qs), np.quantile(target @ LUMA, qs))
    return np.clip(lit * (new / np.maximum(luma, 1e-3))[..., None], 0, 1)


def mode_filter(lab, r=SMOOTH):
    """Each labelled pixel takes the most common label in its (2r+1)^2 window, outside
    pixels not counted: outline slivers and texture grain go, a part's blocks stay."""
    h, w = lab.shape
    k = 2 * r + 1
    counts = []
    for z in range(1, lab.max() + 1):
        c = np.pad((lab == z).astype(np.int32), r + 1).cumsum(0).cumsum(1)   # summed-area table
        counts.append(c[k:k + h, k:k + w] - c[:h, k:k + w] - c[k:k + h, :w] + c[:h, :w])
    return np.where(lab > 0, np.argmax(counts, axis=0) + 1, 0).astype(lab.dtype)


def zone_labels(rgb, mask, centres, ink=False):
    """Zone index + 1 (0 = outside) of every mask pixel: the nearest zone. With
    `ink` the sheet's black outlines are first grown over from the zones beside them, so a
    face keeps one label across its drawn edges."""
    lab = np.zeros(mask.shape, np.int16)
    px = rgb[mask]
    idx = nearest(px, centres)
    if ink:
        idx[px.max(axis=1) <= INK] = 0
    lab[mask] = idx
    for _ in range(INK_FILL if ink else 0):
        empty = mask & (lab == 0)
        if not empty.any():
            break
        pad = np.pad(lab, 1)
        near = np.maximum.reduce([pad[:-2, 1:-1], pad[2:, 1:-1], pad[1:-1, :-2], pad[1:-1, 2:]])
        lab = np.where(empty, near, lab)
    rest = mask & (lab == 0)   # an outline-only island: fall back to its own colour
    if rest.any():
        lab[rest] = nearest(rgb[rest], centres)
    return lab


def components(mask):
    """Connected pieces of a boolean mask as a list of boolean masks (4-neighbour)."""
    big = mask.size + 1
    ids = np.where(mask, np.arange(mask.size).reshape(mask.shape), big)
    while True:
        pad = np.pad(ids, 1, constant_values=big)
        near = np.minimum.reduce([ids, pad[:-2, 1:-1], pad[2:, 1:-1], pad[1:-1, :-2], pad[1:-1, 2:]])
        near = np.where(mask, near, big)
        if (near == ids).all():
            break
        ids = near
    return [ids == i for i in np.unique(ids[mask])]


def dilate(mask, r):
    """Boolean mask grown by r pixels (square window)."""
    for _ in range(r):
        pad = np.pad(mask, 1)
        mask = np.logical_or.reduce([pad[i:i + mask.shape[0], j:j + mask.shape[1]]
                                     for i in range(3) for j in range(3)])
    return mask


def cover(piece, zone):
    """Share of one drawn piece the model's same-colour zone reaches within SLACK px: a
    part present but a little off still counts, a part painted in another colour, or not
    there at all, is ~0. Unlike the zone IoU it cannot be hidden by a same-colour part
    elsewhere on the figure."""
    return float((piece & dilate(zone, SLACK)).sum() / piece.sum())


def zone_report(concept, model, names):
    """Per colour zone and per drawn piece, how well the model's flat-colour render covers
    the concept's. `concept` and `model` are normalized label maps (0 = outside). Returns
      mean    area-weighted zone IoU
      lost    zones of >= ZONE_SHARE of the figure under LOST IoU: a colour the model lacks
              entirely (the carapace, the club) reads ~0 however small its weight
      cover   area-weighted piece cover (see cover())
      zones   {hex: {"iou", "share"}}       pieces   {"hex@x,y": cover}  (x, y in % of canvas)"""
    total = (concept > 0).sum()
    zones, pieces, areas = {}, {}, {}
    for z, name in enumerate(names, 1):
        zc, zm = concept == z, model == z
        if zc.sum() < PIECE_MIN * total:
            continue
        zones[name] = {"iou": round(iou(zc, zm), 4), "share": round(float(zc.sum() / total), 4)}
        for piece in components(zc):
            if piece.sum() >= PIECE_MIN * total:
                ys, xs = np.where(piece)
                at = f"{name}@{int(100 * xs.mean() / CANVAS_W)},{int(100 * ys.mean() / CANVAS_H)}"
                pieces[at], areas[at] = round(cover(piece, zm), 4), int(piece.sum())
    weight = sum(z["share"] for z in zones.values()) or 1.0
    return {"mean": round(sum(z["iou"] * z["share"] for z in zones.values()) / weight, 4),
            "lost": [k for k, z in zones.items() if z["share"] >= ZONE_SHARE and z["iou"] < LOST],
            "cover": round(sum(pieces[k] * areas[k] for k in pieces) / max(sum(areas.values()), 1), 4),
            "zones": zones, "pieces": pieces}


def zone_views(sheet, renders, stem, silhouettes, layout="unit", tilts=None):
    """view -> zone_report for front/left/back/top/bottom: the sheet and the model's flat-colour
    render, both in the sheet's own zones and normalized like the silhouettes.
    `silhouettes` maps view -> the model mask best_match chose (picks the mirror);
    `tilts` maps top/bottom -> the tilt that mask was shot at, so the colour is shot from
    the same camera."""
    names, centres = zone_palette(sheet)
    rgb = read_rgba(sheet, 768)[..., :3] / 255.0
    panels = concept_panels(sheet, layout=layout)
    out = {}
    for view in ZONE_VIEWS:
        tilt = (tilts or {}).get(view)
        path = renders / f"{stem}-zone-{view}{f'@{tilt}' if tilt else ''}.png"
        if view not in silhouettes or view not in panels or not path.exists():
            continue
        shot = read_rgba(path, 512)
        lit, mask = shot[..., :3] / 255.0, shot[..., 3] > 16
        lab = zone_labels(match_luma(lit, mask, rgb[panels[view]]), mask, centres)
        model = max(variants(mode_filter(normalize(lab)), view), key=lambda v: iou(v > 0, silhouettes[view]))
        concept = mode_filter(normalize(zone_labels(rgb, panels[view], centres, ink=True)))
        out[view] = zone_report(concept, model, names)
    return out


def zone_gate(report, zones):
    """Attach each view's zone report to the silhouette report and print it. On the ZONE_GATED
    views a mean or cover under ZONE_GATES fails (returned: how many views); a lost zone
    only warns, it is the passes' acceptance that must not make one."""
    bad = 0
    for name, z in zones.items():
        fails = [m for m, lo in ZONE_GATES.items() if z[m] < lo] if name in ZONE_GATED else []
        report[name]["zones"] = {**z, "fails": fails}
        lost = f"  LOST {','.join(z['lost'])}" if z["lost"] else ""
        print(f"{name:8} zones mean {z['mean']:.3f}  cover {z['cover']:.3f}  "
              f"{'FAIL ' + ','.join(fails) if fails else 'ok'}{lost}")
        bad += bool(fails)
    return bad


def best_match(concept, tilted, name):
    """Best IoU over the mirror variants of every rendered tilt: (iou, mask, tilt)."""
    best = (-1.0, None, 0)
    for tilt, mask in tilted.items():
        for variant in variants(normalize(mask), name):
            score = iou(concept, variant)
            if score > best[0]:
                best = (score, variant, tilt)
    return best


def pin_tilts(model, tilts):
    """model_panels() reduced to the cameras in `tilts` ({view: tilt}): top/bottom at that tilt
    only, the RTS view at that (elevation, azimuth) only. The colour stage measures the cameras
    the shape stage chose; a free sweep there could pick another camera for the same model."""
    return {view: {cam: m for cam, m in cams.items() if cam == tilts[view]} if view in tilts else cams
            for view, cams in model.items()}


def report_tilts(report):
    """{view: tilt} of the top/bottom/rts cameras a silhouette report matched."""
    return {view: r["tilt"] for view, r in report.items() if r.get("tilt")}


def crop(mask):
    ys, xs = np.where(mask)
    if len(ys) == 0:
        raise ValueError("empty mask")
    return mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def normalize(mask, target_h=CANVAS_H, canvas_w=CANVAS_W):
    m = crop(mask)
    h, w = m.shape
    tw = max(1, round(w * target_h / h))
    if tw > canvas_w:
        target_h = max(1, round(h * canvas_w / w))
        tw = canvas_w
    iy = (np.arange(target_h) * h / target_h).astype(int)
    ix = (np.arange(tw) * w / tw).astype(int)
    small = m[iy[:, None], ix[None, :]]
    out = np.zeros((target_h if target_h == CANVAS_H else CANVAS_H, canvas_w), m.dtype)
    y0, x0 = (CANVAS_H - target_h) // 2, (canvas_w - tw) // 2
    out[y0:y0 + target_h, x0:x0 + tw] = small
    return out


def variants(mask, name):
    """Left-right mirror only. Top and bottom used to try an upside-down flip too, but a
    flipped back-side tilt then out-scored the real front-side camera; the tilt sweep
    covers the angle, and the renders share the sheet's orientation (front at the bottom).
    The RTS view is never mirrored: the azimuth sweep already covers both sides, and a
    mirrored match renders the model from the opposite side of the concept."""
    return [mask] if name == "rts" else [mask, np.fliplr(mask)]


def iou(a, b):
    union = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / union) if union else 1.0


def profile(mask, bands=32):
    rows = np.where(mask.any(axis=1))[0]
    h = rows.max() - rows.min() + 1 if len(rows) else 1
    out = []
    for i in range(bands):
        a = rows.min() + i * h // bands if len(rows) else 0
        b = rows.min() + (i + 1) * h // bands if len(rows) else 0
        band = mask[a:b]
        cols = np.where(band.any(axis=0))[0]
        out.append((cols.max() - cols.min() + 1) / max(h, 1) if len(cols) else 0.0)
    return np.asarray(out)


def downsample(mask, n=32):
    kh, kw = mask.shape[0] // n, mask.shape[1] // n
    return mask.reshape(n, kh, n, kw).mean(axis=(1, 3)) >= 0.5


def write_mask(mask, path, color=(255, 255, 255)):
    rgba = np.zeros((*mask.shape, 4), np.uint8)
    rgba[mask] = (*color, 255)
    subprocess.run(["magick", "-size", f"{mask.shape[1]}x{mask.shape[0]}", "-depth", "8",
                    "rgba:-", str(path)], input=rgba.tobytes(), check=True)


def write_overlay(concept, model, path):
    rgba = np.zeros((*concept.shape, 4), np.uint8)
    rgba[..., 0] = concept * 255
    rgba[..., 1] = model * 255
    rgba[..., 3] = np.where(np.logical_or(concept, model), 255, 0)
    subprocess.run(["magick", "-size", f"{concept.shape[1]}x{concept.shape[0]}", "-depth", "8",
                    "rgba:-", str(path)], input=rgba.tobytes(), check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet", type=pathlib.Path)
    ap.add_argument("glb", type=pathlib.Path)
    ap.add_argument("outdir", type=pathlib.Path)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--measure", action="store_true", help="print sheet proportions and exit")
    ap.add_argument("--layout", default="unit", choices=("unit", "building"))
    ap.add_argument("--shape", action="store_true",
                    help="stage 1 (clay): silhouette gates only, no colour zones")
    ap.add_argument("--tilts", default="",
                    help="pin the top/bottom/rts cameras, e.g. top:10,bottom:20,rts:35/30 "
                         "(the colour stage reuses the shape stage's cameras)")
    args = ap.parse_args()
    if args.measure:
        print(json.dumps(measure(args.sheet), indent=2))
        return 0

    args.outdir.mkdir(parents=True, exist_ok=True)
    renders = args.outdir / "sil"
    if not args.no_render:
        subprocess.run(["blender", "-b", "-P", str(HERE / "render_silhouette.py"),
                        "--", str(args.glb), str(renders)], check=True,
                       capture_output=True, text=True)

    concept = {k: normalize(v) for k, v in concept_panels(args.sheet, layout=args.layout).items()}
    if rts_path(args.sheet).exists():
        concept["rts"] = normalize(foreground(rts_path(args.sheet), 768))
    model = model_panels(renders, args.glb.stem)
    if args.tilts:
        from views import parse_tilts
        model = pin_tilts(model, parse_tilts(args.tilts))

    print(f"{'view':8} {'IoU':>6}  {'L1':>6}  {'32px':>5}  {'camera':>6}  gate")
    report, bad, best_masks = {}, 0, {}
    for name in [v for v in concept if model.get(v)]:
        best, best_mask, tilt = best_match(concept[name], model[name], name)
        l1 = float(np.abs(profile(concept[name]) - profile(best_mask)).mean())
        px = iou(downsample(concept[name]), downsample(best_mask))
        gate = GATES.get(name)
        ok = gate is None or best >= gate
        bad += 0 if ok else 1
        report[name] = {"iou": round(best, 4), "width_l1": round(l1, 4),
                        "iou_32": round(px, 4), "tilt": tilt, "gate": gate}
        print(f"{name:8} {best:6.3f}  {l1:6.3f}  {px:5.3f}  {str(tilt):>6}  "
              f"{'n/a' if gate is None else ('PASS' if ok else 'FAIL')}")
        write_mask(concept[name], args.outdir / f"mask-concept-{name}.png", (255, 80, 80))
        write_mask(best_mask, args.outdir / f"mask-model-{name}.png", (80, 255, 80))
        write_overlay(concept[name], best_mask, args.outdir / f"overlay-{name}.png")
        best_masks[name] = best_mask

    if not args.shape:
        bad += zone_gate(report, zone_views(args.sheet, renders, args.glb.stem, best_masks, args.layout,
                                             report_tilts(report)))
    (args.outdir / "silhouette.json").write_text(json.dumps(report, indent=2))
    gated = [g for g in GATES if g in concept]    # a view with no concept image (no RTS draw) is not gated
    missing = [g for g in gated if g not in report]
    if missing:
        # no render (missing GLB, failed Blender) must not read as a pass
        print(f"\nno measurement for gated views {missing}: FAIL")
        return 1
    print(f"\n{len(gated) - bad}/{len(gated)} view gates pass")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
