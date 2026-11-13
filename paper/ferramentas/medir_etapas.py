#!/usr/bin/env python3
"""Mede e fotografa cada etapa listada em etapas.csv com a régua ATUAL do pipeline.

    python3 ferramentas/medir_etapas.py                 # todas as etapas
    python3 ferramentas/medir_etapas.py --only hfoo     # uma unidade
    python3 ferramentas/medir_etapas.py --force         # ignora o cache e mede/renderiza de novo

Por etapa: tris/materiais/skins/clips (check_gates.stats), IoU de silhueta contra
refs/<unit>/sheet.jpg (silhouette.py) e um render front|left|wc3 (render_unit.py).
Saídas: evolution-metrics.csv, figuras/<unit>-<NN>-<stage>.png, figuras/<unit>-evolucao.png.
Cache de renders/máscaras em ferramentas/.cache/ (apagável).
Requer: Blender no PATH, ImageMagick (magick), numpy, repo castle_fight.
"""
import argparse
import csv
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PAPER = HERE.parent
CACHE = HERE / ".cache"
FIGS = PAPER / "figuras"
FONT = ["-font", "/System/Library/Fonts/Supplemental/Arial.ttf", "-pointsize", "20"]
FIELDS = ["unit", "order", "stage", "commit", "change", "tris", "materials", "skins", "anims",
          "iou_front", "iou_left", "iou_back", "iou_top", "iou32_front", "gate_pass"]


def tag(row):
    return f"{row['unit']}-{int(row['order']):02d}-{re.sub(r'[^A-Za-z0-9.-]+', '_', row['stage']).strip('_')}"


def measure(castle, row, glb, cache, force):
    """IoU contra o sheet aprovado; reaproveita o silhouette.json do cache."""
    sil = cache / "sil"
    report = sil / "silhouette.json"
    if force or not report.exists():
        sheet = castle / f"artifacts/model-sheets/refs/{row['unit']}/sheet.jpg"
        subprocess.run([sys.executable, str(castle / "tools/blender/silhouette.py"), str(sheet), str(glb), str(sil)],
                       capture_output=True, cwd=castle)
    rep = json.loads(report.read_text()) if report.exists() else {}
    out = {f"iou_{v}": rep.get(v, {}).get("iou", "") for v in ("front", "left", "back", "top")}
    out["iou32_front"] = rep.get("front", {}).get("iou_32", "")
    out["gate_pass"] = all(rep.get(v, {}).get("iou", 0) >= g for v, g in (("front", 0.75), ("left", 0.65)))
    return out


def strip(castle, row, glb, cache, force, m):
    views = [cache / "views" / f"{glb.stem}-{v}.png" for v in ("front", "left", "wc3")]
    if force or not all(v.exists() for v in views):
        subprocess.run(["blender", "-b", "-P", str(castle / "tools/blender/render_unit.py"), "--",
                        str(glb), str(cache / "views")], capture_output=True)
    text = (f"{int(row['order']):02d} {row['stage']} ({row['commit']})  tris {m['tris']}  "
            f"IoU f/l/b {m['iou_front']:.2f}/{m['iou_left']:.2f}/{m['iou_back']:.2f}  "
            f"{'PASS' if m['gate_pass'] else 'FAIL'}")
    dst = FIGS / f"{tag(row)}.png"
    labelled(views, text, dst)
    return dst


def labelled(images, text, dst):
    subprocess.run(["magick", "(", "-size", "960x34", "-background", "white", *FONT, "-gravity", "center",
                    "label:" + text, ")", "(", *map(str, images), "+append", "-resize", "960x", "+repage", ")",
                    "-append", str(dst)], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--castle", type=pathlib.Path, default=PAPER.parent / "castle_fight")
    ap.add_argument("--only", help="só esta unidade")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    castle = args.castle.resolve()
    sys.path.insert(0, str(castle / "tools/blender"))
    from check_gates import stats

    rows = list(csv.DictReader(open(HERE / "etapas.csv")))
    rows = [r for r in rows if not args.only or r["unit"] == args.only]
    FIGS.mkdir(exist_ok=True)
    out_csv = PAPER / "evolution-metrics.csv"
    keep = [r for r in csv.DictReader(open(out_csv))] if args.only and out_csv.exists() else []
    keep = [r for r in keep if r["unit"] != args.only]
    results, strips = [], {}
    for row in rows:
        glb = castle / row["glb"]
        if not glb.exists():
            print(f"FALTA {glb}")
            continue
        cache = CACHE / tag(row)
        m = dict(zip(("tris", "materials", "skins", "anims"), stats(glb)))
        m.update(measure(castle, row, glb, cache, args.force))
        if m["iou_front"] == "":
            print(f"SEM MEDIDA {tag(row)}")
            continue
        strips.setdefault(row["unit"], []).append(strip(castle, row, glb, cache, args.force, m))
        results.append({**{k: row[k] for k in ("unit", "order", "stage", "commit", "change")}, **m})
        print(f"{tag(row):28} tris {m['tris']:4}  f/l/b {m['iou_front']:.3f}/{m['iou_left']:.3f}/"
              f"{m['iou_back']:.3f}  {'PASS' if m['gate_pass'] else 'FAIL'}", flush=True)

    with out_csv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        w.writerows(sorted(keep + results, key=lambda r: (r["unit"], int(r["order"]))))
    for unit, files in strips.items():
        head = CACHE / f"{unit}-sheet.png"
        labelled([castle / f"artifacts/model-sheets/refs/{unit}/sheet.jpg"], f"{unit} - sheet aprovado (juiz)", head)
        subprocess.run(["magick", str(head), *map(str, files), "-append", "-resize", "50%",
                        str(FIGS / f"{unit}-evolucao.png")], check=True)


if __name__ == "__main__":
    main()
