"""L14-1 body comparison (PIPELINE 32.L14-1): the runs l14-{sdf,union}-{700,1000} of the 6 units, measured by the look and by the silhouette.

    python3.14 tools/blender/body_compare.py [--units n005,hfoo] [--times l14-all.out] [--images]

Table per (unit, run): planarity, crease precision / recall, wire entropy, real tris, slivers, body components, seconds, then the
silhouette as a guard (IoU, spill, bare, contact means, spill <= .03 views, the views whose IoU falls > 2 sigma of noise-l12.json
against the control `l14-sdf-700`). `--images` writes history/2026-10-30-l14-body/<id>.png: per view one row, per run the columns
clay | wire | textured. Rows reuse ablation_matrix.make_row (pure); only main touches disk."""
import argparse
import pathlib
import re
import sys

from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/blender"))
import ablation_matrix as AM  # noqa: E402
import make_compare as MC  # noqa: E402
import mesh_lint as ML  # noqa: E402
import noise as NZ  # noqa: E402

DRAFT = ROOT / "artifacts/model-sheets/runs/draft"
OUT = ROOT / "artifacts/model-sheets/history/2026-10-30-l14-body"
RUNS = ("sdf-700", "union-700", "sdf-1000", "union-1000")
VIEWS = AM.VIEWS
FILES = {"rts": "wc3"}     # the rts render of clay/model is named wc3


def times_from(path):
    """{(unit, run): seconds} of the `<id> <run> exit=N t=Ss` lines the battery driver printed."""
    if not path:
        return {}
    return {(m[1], m[2]): float(m[3]) for m in re.finditer(r"^(\w+) (\S+) exit=\d+ t=(\d+)s", pathlib.Path(path).read_text(), re.M)}


def row_of(unit, run, secs):
    d = DRAFT / unit / f"l14-{run}"
    if not (d / "clay.glb").exists():
        return AM.fail_row(unit, run, "no clay.glb")
    look = AM.read_json(d / "clay.look.json").get("look_after") or {}
    row = AM.make_row(unit, run, AM.read_json(d / "silhouette.json"), ML.lint(d / "clay.glb", sdf=(d / "clay.sdf.json").exists()),
                      {"total_s": secs}, None, None, look, AM.read_json(d / "clay.depth.json"))
    cc = list(look.get("crease_chamfer", {}).values())
    row.update(cprec=AM.mean([c[0] for c in cc]), crec=AM.mean([c[1] for c in cc]), entropy=look.get("wire_entropy"),
               tris_model=(ML.lint(d / "model.glb")["tris"] if (d / "model.glb").exists() else None),
               stage2=AM.read_json(d / "stage2" / "colour.json").get("zones") is not None)
    return row


def falls(row, ctl, noise):
    return [v for v, a, b in zip(VIEWS, row["iou"], ctl["iou"]) if a is not None and b is not None and a - b < -NZ.threshold(v, noise, unit=row["unit"])]


def table(rows, noise):
    out = ["| unit | run | planarity | crease P | crease R | entropy | tris (clay/model) | sliver % | comps | s | IoU | spill | spill<=.03 | bare | contact | falls>2σ vs sdf-700 |",
           "|---" * 16 + "|"]
    by = {(r["unit"], r["variant"]): r for r in rows}
    for r in rows:
        if not r["ok"]:
            out.append(f"| {r['unit']} | {r['variant']} | FAIL {r['cause']} |" + " |" * 13)
            continue
        ctl = by.get((r["unit"], "sdf-700"))
        fl = ",".join(falls(r, ctl, noise)) if ctl and ctl["ok"] and r["variant"] != "sdf-700" else "–"
        out.append(f"| {r['unit']} | {r['variant']} | {AM.f(r['planarity'])} | {AM.f(r['cprec'])} | {AM.f(r['crec'])} | {AM.f(r['entropy'])} "
                   f"| {r['tris']}/{r['tris_model']} | {AM.f(r['sliver'], 1)} | {r['comp']} | {AM.f(r['total_s'], 0)} | {AM.f(r['mean'], 4)} | {AM.f(r['spill'], 4)} "
                   f"| {r['spill_ok']}/6 | {AM.f(r['bare'], 4)} | {AM.f(r['contact'], 3)} | {fl or '–'} |")
    return "\n".join(out)


def wins(rows, a, b, key, higher=True):
    """Units where run `a` beats run `b` on `key` (strictly), over the units both measured: (wins, n)."""
    by = {(r["unit"], r["variant"]): r for r in rows if r["ok"]}
    pairs = [(by[(u, a)][key], by[(u, b)][key]) for u in dict.fromkeys(r["unit"] for r in rows) if (u, a) in by and (u, b) in by]
    pairs = [(x, y) for x, y in pairs if x is not None and y is not None]
    return sum(1 for x, y in pairs if (x > y if higher else x < y)), len(pairs)


def sheet(unit):
    """Per view a row, per run clay | wire | textured, every cell cropped to the figure at one scale."""
    cols = [(run, kind) for run in RUNS for kind in ("clay", "wire", "model")]
    cw, ch = MC.CELL
    img = Image.new("RGB", (cw * len(cols), 20 + (ch + 20) * len(VIEWS)), MC.BG)
    d = ImageDraw.Draw(img)
    for x, (run, kind) in enumerate(cols):
        d.text((x * cw + 6, 4), f"{run} {kind}", fill=(255, 255, 255))
    for y, v in enumerate(VIEWS):
        for x, (run, kind) in enumerate(cols):
            name = f"{kind}-{FILES.get(v, v) if kind != 'wire' else v}.png"
            p = DRAFT / unit / f"l14-{run}" / "views" / unit / name
            if p.exists():
                img.paste(MC.fit(Image.open(p)), (x * cw, 20 + y * (ch + 20)))
        d.text((4, 20 + y * (ch + 20) + ch), v, fill=(255, 255, 255))
    return img


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--units", default=",".join(AM.UNITS))
    ap.add_argument("--times", default="")
    ap.add_argument("--images", action="store_true")
    args = ap.parse_args(argv)
    noise = AM.read_json(AM.NOISE)
    secs = times_from(args.times)
    units = args.units.split(",")
    rows = [row_of(u, r, secs.get((u, r), 0.0)) for u in units for r in RUNS]
    print(table(rows, noise))
    for a, b, key, hi in (("union-700", "sdf-700", "planarity", True), ("union-700", "sdf-700", "crec", True), ("union-1000", "union-700", "planarity", True),
                          ("sdf-1000", "sdf-700", "planarity", True)):
        print(f"{a} beats {b} on {key}: %d/%d" % wins(rows, a, b, key, hi))
    if args.images:
        OUT.mkdir(parents=True, exist_ok=True)
        for u in units:
            im = sheet(u)
            im.resize((im.width // 2, im.height // 2), Image.LANCZOS).save(OUT / f"{u}.png")
            print("wrote", OUT / f"{u}.png")


if __name__ == "__main__":
    main()
