#!/usr/bin/env python3
"""Professional review sheet of one run: a row per view, columns concept | clay | overlay | textured.

    python3 tools/blender/make_compare.py --run <run_dir> [--against approved|hard] [--out x.png]
    python3 tools/blender/make_compare.py <sheet.jpg> <views_dir> <stem> <out.png> [--layout ...]

The second form is the spec_pipeline call: the run directory is `out.parent`, `--against` is
`hard` when the sheet's name says so (sheet-hard.jpg), else `approved`.

Rows: front, left, back, top, bottom, rts (buildings: front, left, back, right, roof, rts).
Every cell is cropped to its figure and fitted into the same box, so the columns are at one
scale. Each row has a footer with the view's numbers; the header has unit, run, spec author
and the verdict per stage. Overlay: concept green, model red, hit grey.

Input contract - everything is read from files of the run directory, nothing is recomputed:
  review.md              "# <unit> - run <run> (<tag>)", "- spec author: ...", "- kind: ...",
                         "- judge (approved sheet): <path>", "- built from (image 1): <path>",
                         "verdict: **PASS|FAIL**"; stage verdicts are any line naming
                         "stage 1" / "stage 2" with PASS or FAIL (older runs: shown as n/a)
  silhouette.json        summary (per-view "approved"/"hard" IoU, "drift"); only for the header
  sil/<against>/silhouette.json   per view: iou, iou_32, width_l1, tilt, gate, zones{mean,cover,lost}
  sil/<against>/mask-concept-<view>.png, mask-model-<view>.png    the matched masks (alpha)
  views/<tag>/<stem>-<view>.png   textured renders (view "rts" is the "wc3" file)
  views/<tag>/clay-<view>.png     clay renders (S1 writes them; rts: clay-wc3.png or clay-rts.png); absent -> empty cell + warning
  concept panels: split_sheet.split of the sheet named in review.md (fallback refs/<unit>/)
"""
import argparse
import json
import pathlib
import re
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import silhouette as S  # noqa: E402

ROOT = S.ROOT
CELL = (384, 288)
BG = (200, 200, 200)
EMPTY = (226, 226, 226)
HEAD_H, TITLE_H, FOOT_H, GAP = 96, 30, 30, 6
COLUMNS = ("concept", "clay", "overlay", "textured")
OVERLAY = {"concept": (70, 190, 70), "model": (220, 50, 50), "hit": (120, 120, 120)}
PASS, FAIL, DIM, INK = (30, 140, 50), (200, 40, 40), (110, 110, 110), (20, 20, 20)
FONTS = ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf")
RENDER_NAME = {"rts": "wc3"}


def font(size):
    for path in FONTS:
        if pathlib.Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def warn(msg):
    print(f"make_compare: {msg}", file=sys.stderr)


# --- run directory ---------------------------------------------------------------------------

def parse_review(path):
    """{"unit", "run", "tag", "author", "kind", "judge", "built", "verdict", "stages"} of review.md."""
    meta = {"stages": {}}
    if not path.exists():
        return meta
    for line in path.read_text().splitlines():
        head = re.match(r"#\s*(\S+)\s+\S+\s+run\s+(\S+)\s*\((.*)\)", line)
        if head:
            meta.update(unit=head[1], run=head[2], tag=head[3])
        for key, label in (("author", "spec author"), ("kind", "kind"), ("model", "model"),
                           ("judge", "judge (approved sheet)"), ("built", "built from (image 1)")):
            if line.startswith(f"- {label}:"):
                meta[key] = line.split(":", 1)[1].strip()
        verdict = re.match(r"verdict:\s*\*\*([\w-]+)\*\*", line)      # PASS, CHECK, SHAPE-PASS
        if verdict:
            meta["verdict"] = verdict[1]
        stage = re.search(r"stage\s*([12])\b.*?\b(PASS|FAIL)\b", line, re.I)
        if stage:
            meta["stages"][stage[1]] = stage[2].upper()
    return meta


def find_views(run_dir):
    """(views dir, stem): the views/<tag> directory holding the render set, and its file stem."""
    for d in sorted((run_dir / "views").glob("*")):
        for f in sorted(d.glob("*-front.png")):
            if not f.name.startswith("clay-"):
                return d, f.name[:-len("-front.png")]
        if (d / "clay-front.png").exists():
            return d, None
    return None, None


def find_sheet(meta, run_dir, against):
    """The concept sheet of the compared side: the path in review.md, else refs/<unit>/."""
    named = meta.get("judge" if against == "approved" else "built")
    if named and pathlib.Path(named.split()[0]).exists():
        return pathlib.Path(named.split()[0])
    unit = meta.get("unit") or run_dir.parent.name
    sheet = ROOT / "artifacts/model-sheets/refs" / unit / ("sheet.jpg" if against == "approved" else "sheet-hard.jpg")
    return sheet if sheet.exists() else None


def load_run(run_dir, against="approved", sheet=None, views=None, stem=None, layout=None):
    run_dir = pathlib.Path(run_dir)
    meta = parse_review(run_dir / "review.md")
    found_views, found_stem = find_views(run_dir)
    sil_report = run_dir / "sil" / against / "silhouette.json"
    kind = meta.get("kind", "mass")
    return {
        "dir": run_dir, "against": against, "meta": meta,
        "unit": meta.get("unit", run_dir.parent.name), "run": meta.get("run", run_dir.name),
        "sheet": sheet or find_sheet(meta, run_dir, against),
        "views": views or found_views, "stem": stem or found_stem,
        "layout": layout or ("building" if kind in ("building", "large") else "unit"),
        "report": json.loads(sil_report.read_text()) if sil_report.exists() else {},
        "sil": run_dir / "sil" / against,
    }


def view_names(run):
    from views import LAYOUTS
    return (*LAYOUTS[run["layout"]], "rts")


# --- cells -----------------------------------------------------------------------------------

def empty_cell(text):
    img = Image.new("RGB", CELL, EMPTY)
    d = ImageDraw.Draw(img)
    f = font(14)
    d.text((CELL[0] // 2, CELL[1] // 2), text, fill=DIM, font=f, anchor="mm")
    return img


def figure_box(img, bg=None):
    """Bounding box of the figure: what differs from the border colour, keeping the largest
    blobs only (a panel cut from a sheet can carry a stray line of its neighbour)."""
    from scipy import ndimage as ndi
    rgb = np.asarray(img.convert("RGB")).astype(np.int16)
    if bg is None:
        bg = np.median(np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]]), axis=0)
    lab, n = ndi.label(ndi.binary_closing(np.abs(rgb - bg).sum(axis=2) > 24, iterations=3))
    if not n:
        return None
    areas = ndi.sum(np.ones(lab.shape), lab, range(1, n + 1))
    keep = np.isin(lab, 1 + np.flatnonzero(areas >= 0.05 * areas.max()))
    ys, xs = np.where(keep)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def fit(img, box=None, pad_share=0.06):
    """Crop to `box` (default: the figure) plus padding and fit it into a CELL, no stretching."""
    box = box or figure_box(img)
    if box is None:
        return empty_cell("empty")
    x0, y0, x1, y1 = box
    pad = max(4, int(pad_share * max(x1 - x0, y1 - y0)))
    img = img.convert("RGB")
    img = ImageOps.expand(img, pad, fill=img.getpixel((0, 0)))   # padding beyond the edge
    img = img.crop((x0, y0, x1 + 2 * pad, y1 + 2 * pad))
    img.thumbnail(CELL, Image.LANCZOS)
    cell = Image.new("RGB", CELL, BG)
    cell.paste(img, ((CELL[0] - img.width) // 2, (CELL[1] - img.height) // 2))
    return cell


def concept_cells(run, tmp):
    """{view: cell}: split_sheet panels (and the RTS drawing) of the compared sheet."""
    sheet = run["sheet"]
    if not sheet:
        warn("no concept sheet found")
        return {}
    from split_sheet import split
    cells = {}
    for name, path in split(sheet, tmp, "c", run["layout"]).items():
        img = Image.open(path)
        cells[name] = fit(img)
    return cells


NO_STAGE2 = "stage 2 not run (clay)"


def stamp(cell, text):
    """`cell` with a label strip on its top edge."""
    d = ImageDraw.Draw(cell)
    f = font(13)
    d.rectangle((0, 0, CELL[0], 20), fill=(60, 60, 60))
    d.text((CELL[0] // 2, 10), text, fill=(255, 255, 255), font=f, anchor="mm")
    return cell


def render_cell(run, view, clay):
    """Clay or textured render of `view`, or an empty cell naming the missing file. A run
    without stage 2 has no textured render: that column shows the clay, labelled as such."""
    if not run["views"]:
        return empty_cell("no views/ in this run")
    if not clay and run["stem"] is None:
        return stamp(render_cell(run, view, True), NO_STAGE2)
    shot = RENDER_NAME.get(view, view)
    names = (f"clay-{shot}.png", f"clay-{view}.png") if clay else (f"{run['stem']}-{shot}.png",)
    name = names[0]
    path = next((p for p in (run["views"] / n for n in names) if p.exists()), None)
    if path is None:
        warn(f"{run['dir'].name}: {name} absent")
        return empty_cell(f"{name} absent")
    return fit(Image.open(path))


def read_alpha(path):
    return np.asarray(Image.open(path).convert("RGBA"))[..., 3] > 0


def overlay_cell(run, view):
    """Concept green, model red, hit grey, from the masks silhouette.py matched."""
    mc, mm = run["sil"] / f"mask-concept-{view}.png", run["sil"] / f"mask-model-{view}.png"
    if not (mc.exists() and mm.exists()):
        return empty_cell(f"sil/{run['against']}/mask-*-{view}.png absent")
    c, m = read_alpha(mc), read_alpha(mm)
    out = np.full((*c.shape, 3), EMPTY, np.uint8)
    out[c] = OVERLAY["concept"]
    out[m] = OVERLAY["model"]
    out[c & m] = OVERLAY["hit"]
    img = Image.fromarray(out)
    return fit(img, (0, 0, *img.size), 0.0)


# --- text ------------------------------------------------------------------------------------

def tone(word):
    return {"PASS": PASS, "FAIL": FAIL}.get(word, DIM)


def draw_parts(d, xy, parts, f):
    """Draw [(text, colour), ...] left to right from xy."""
    x, y = xy
    for text, colour in parts:
        d.text((x, y), text, fill=colour, font=f)
        x += d.textlength(text, font=f)


def footer_parts(run, view):
    """Row footer: the numbers the report holds for `view`."""
    r = run["report"].get(view)
    parts = [(view.upper().ljust(7), INK)]
    if not r:
        return parts + [("no measurement", DIM)]
    gate = r.get("gate")
    ok = "n/a" if gate is None else ("PASS" if r["iou"] >= gate else "FAIL")
    parts += [(f"IoU {r['iou']:.3f}", INK),
              (f" gate {'-' if gate is None else gate} {ok}", tone(ok)),
              (f"   32px {r.get('iou_32', 0):.3f}  L1 {r.get('width_l1', 0):.3f}  tilt {r.get('tilt')}", INK)]
    z = r.get("zones")
    if z:
        parts.append((f"   zones mean {z['mean']:.3f} cover {z['cover']:.3f} lost {len(z['lost'])}",
                      FAIL if z.get("fails") else INK))
    return parts


def stage_label(run):
    m = run["meta"]
    stages = m.get("stages", {})
    return [("stage 1 shape ", INK), (stages.get("1", "n/a"), tone(stages.get("1"))),
            ("   stage 2 colour ", INK), (stages.get("2", "n/a"), tone(stages.get("2"))),
            ("   verdict ", INK), (m.get("verdict", "n/a"), tone(m.get("verdict")))]


def header(run, width, title=None):
    img = Image.new("RGB", (width, HEAD_H), (245, 245, 245))
    d = ImageDraw.Draw(img)
    m = run["meta"]
    d.text((10, 8), title or f"{run['unit']}  run {run['run']}", fill=INK, font=font(24))
    d.text((10, 42), f"author {m.get('author', '?')}   model {m.get('model', '?')}   "
                     f"vs {run['against']} sheet", fill=DIM, font=font(15))
    draw_parts(d, (10, 66), stage_label(run), font(16))
    return img


# --- grid ------------------------------------------------------------------------------------

def titles(labels, width):
    img = Image.new("RGB", (width, TITLE_H), (60, 60, 60))
    d = ImageDraw.Draw(img)
    for i, text in enumerate(labels):
        d.text((i * CELL[0] + CELL[0] // 2, TITLE_H // 2), text, fill=(255, 255, 255),
               font=font(17), anchor="mm")
    return img


def footer(parts, width):
    img = Image.new("RGB", (width, FOOT_H), (245, 245, 245))
    draw_parts(ImageDraw.Draw(img), (10, 6), parts, font(15))
    return img


def stack(images):
    """Images one under another, a GAP of dark line between."""
    h = sum(i.height for i in images) + GAP * (len(images) - 1)
    out = Image.new("RGB", (images[0].width, h), (85, 85, 85))
    y = 0
    for i in images:
        out.paste(i, (0, y))
        y += i.height + GAP
    return out


def join(cells):
    out = Image.new("RGB", (CELL[0] * len(cells), CELL[1]), BG)
    for i, c in enumerate(cells):
        out.paste(c, (i * CELL[0], 0))
    return out


def build_grid(run):
    width = CELL[0] * len(COLUMNS)
    with tempfile.TemporaryDirectory() as tmp:
        concepts = concept_cells(run, pathlib.Path(tmp))
    rows = [header(run, width), titles(COLUMNS, width)]
    for view in view_names(run):
        cells = [concepts.get(view) or empty_cell("concept absent"), render_cell(run, view, True),
                 overlay_cell(run, view), render_cell(run, view, False)]
        rows += [join(cells), footer(footer_parts(run, view), width)]
    return stack(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pos", nargs="*", help="<sheet> <views_dir> <stem> <out> (spec_pipeline form)")
    ap.add_argument("--run", type=pathlib.Path)
    ap.add_argument("--against", choices=("approved", "hard"))
    ap.add_argument("--out", type=pathlib.Path)
    ap.add_argument("--layout", choices=("unit", "building"))
    args = ap.parse_args()
    if args.run:
        run = load_run(args.run, args.against or "approved", layout=args.layout)
        out = args.out or args.run / "compare.png"
    elif len(args.pos) == 4:
        sheet, views, stem, out = map(pathlib.Path, args.pos)
        against = args.against or ("hard" if "hard" in sheet.stem else "approved")
        run = load_run(out.parent, against, sheet, views, stem.name, args.layout)
    else:
        ap.error("give --run <dir> or <sheet> <views_dir> <stem> <out>")
    build_grid(run).save(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
