"""L15-2 core x whole-SDF comparison (PIPELINE 33.L15-2): the runs l15-sdf (control: the whole body in the SDF) and l15-core (--sdf-core on) of the 6 units.

    python3.14 tools/blender/parts_compare.py [--units n005,hfoo] [--times l15-all.out] [--images] [--anim]

Table per (unit, run): components_body / all components, tris per piece (core, rigid, head), joint depth of the rigid pieces, planarity,
crease precision / recall, mesh_lint (flipped + degenerate + non-manifold), slivers, walk stretch p99.5 (`--anim` runs anim_check.py, Blender,
on model.glb), seconds, and the silhouette as a GUARD (body IoU front / left, IoU / spill / bare means, the views that fall > 2 sigma of
noise-l12.json against l15-sdf). `--images` writes history/2026-10-30-l15-parts/<id>.png: per view a row, columns concept | sdf (clay, wire,
textured) | core (clay, wire, textured), the hand fix of L14-3 on the right for the units that have one. Pure helpers (row_of, falls,
acceptance) are tested without disk; only main touches files and processes."""
import argparse
import json
import pathlib
import re
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/blender"))
import ablation_matrix as AM  # noqa: E402
import make_compare as MC  # noqa: E402
import mesh_lint as ML  # noqa: E402
import noise as NZ  # noqa: E402

DRAFT = ROOT / "artifacts/model-sheets/runs/draft"
OUT = ROOT / "artifacts/model-sheets/history/2026-10-30-l15-parts"
FIX = ROOT / "artifacts/model-sheets/history/2026-10-30-l14-fix"      # concept | v15 | hand fix | overlays (L14-3), 3 units
RUNS = ("sdf", "core")
CONTROL = "sdf"
VIEWS = AM.VIEWS
FILES = {"rts": "wc3"}     # the rts render of clay/model is named wc3
BODY_IOU = 0.75           # acceptance: body IoU of the coherent views
STRETCH = 1.5             # acceptance: walk / attack / death p99.5 edge stretch
FACE_TRIS = 40            # acceptance: triangles of the head pieces


def times_from(path):
    """{(unit, run): seconds} of the `<id> <run> exit=N t=Ss` lines the battery driver printed."""
    if not path:
        return {}
    return {(m[1], m[2]): float(m[3]) for m in re.finditer(r"^(\w+) (\S+) exit=\d+ t=(\d+)s", pathlib.Path(path).read_text(), re.M)}


def row_of(unit, run, secs):
    d = DRAFT / unit / f"l15-{run}"
    if not (d / "clay.glb").exists():
        return AM.fail_row(unit, run, "no clay.glb")
    look = AM.read_json(d / "clay.look.json").get("look_after") or {}
    lint = ML.lint(d / "clay.glb", sdf=(d / "clay.sdf.json").exists())
    row = AM.make_row(unit, run, AM.read_json(d / "silhouette.json"), lint, {"total_s": secs}, None, None, look, AM.read_json(d / "clay.depth.json"))
    cc = list(look.get("crease_chamfer", {}).values())
    sil, doc = AM.read_json(d / "silhouette.json"), AM.read_json(d / "attach.json").get("union", {})
    core = doc.get("core") or {}
    row.update(cprec=AM.mean([c[0] for c in cc]), crec=AM.mean([c[1] for c in cc]), comps_all=lint["components"], bad=lint["flipped"] + lint["degenerate"] + lint["nonmanifold_edges"],
               body_iou=[(sil.get("body_iou") or {}).get(v) for v in ("front", "left")], head=core.get("head"), core_tris=core.get("core_tris", doc.get("tris")),
               rigid_tris=sum(r["tris"] for r in core.get("rigid", [])), joint=max((r["joint_depth"] for r in core.get("rigid", [])), default=None),
               height=lint["pivot"]["height"], stretch=(AM.read_json(d / "anim.json") or None))
    return row


def falls(row, ctl, noise):
    return [v for v, a, b in zip(VIEWS, row["iou"], ctl["iou"]) if a is not None and b is not None and a - b < -NZ.threshold(v, noise, unit=row["unit"])]


def worst_stretch(row):
    vals = [v["p99.5_stretch"] for v in (row.get("stretch") or {}).values() if v]
    return max(vals) if vals else None


def table(rows, noise):
    out = ["| unit | run | comps body/all | tris core+rigid (head) | joint depth (H) | planarity | crease P | crease R | lint bad | sliver % | stretch | s | body IoU f/l | IoU | spill | bare | falls>2σ vs sdf |",
           "|---" * 17 + "|"]
    by = {(r["unit"], r["variant"]): r for r in rows}
    for r in rows:
        if not r["ok"]:
            out.append(f"| {r['unit']} | {r['variant']} | FAIL {r['cause']} |" + " |" * 14)
            continue
        ctl = by.get((r["unit"], CONTROL))
        fl = ",".join(falls(r, ctl, noise)) if ctl and ctl["ok"] and r["variant"] != CONTROL else "–"
        joint = AM.f(r["joint"] / r["height"], 3) if r["joint"] is not None else "–"
        bi = "/".join(AM.f(x, 3) for x in r["body_iou"])
        out.append(f"| {r['unit']} | {r['variant']} | {r['comp']}/{r['comps_all']} | {r['core_tris']}+{r['rigid_tris']} ({r['head'] if r['head'] is not None else '–'}) | {joint} "
                   f"| {AM.f(r['planarity'])} | {AM.f(r['cprec'])} | {AM.f(r['crec'])} | {r['bad']} | {AM.f(r['sliver'], 1)} | {AM.f(worst_stretch(r), 2)} | {AM.f(r['total_s'], 0)} "
                   f"| {bi} | {AM.f(r['mean'], 3)} | {AM.f(r['spill'], 3)} | {AM.f(r['bare'], 3)} | {fl or '–'} |")
    return "\n".join(out)


def acceptance(rows, verdicts=None):
    """The brief's acceptance, per unit and overall: body IoU >= .75 on the coherent views, stretch <= 1.5, head >= 40 tris (units with a head),
    and the judge's form + artist votes >= 3-1 for core in >= 4 of 6 units (`verdicts` = {unit: (form_core_votes, artist_core_votes)})."""
    core = {r["unit"]: r for r in rows if r["variant"] == "core" and r["ok"]}
    out = {u: {"body_iou": all(x is None or x >= BODY_IOU for x in r["body_iou"]),
               "stretch": worst_stretch(r) is None or worst_stretch(r) <= STRETCH,
               "face": r["head"] is None or r["head"] >= FACE_TRIS} for u, r in core.items()}
    judged = sum(1 for f, a in (verdicts or {}).values() if f >= 3 and a >= 3)
    return out, judged


def sheet(unit):
    """Per view a row: concept, then per run clay | wire | textured, every cell cropped to the figure at one scale; the hand fix last when it exists."""
    cols = [(run, kind) for run in RUNS for kind in ("clay", "wire", "model")]
    cw, ch = MC.CELL
    fix = Image.open(FIX / f"{unit}.png") if (FIX / f"{unit}.png").exists() else None
    img = Image.new("RGB", (cw * (len(cols) + 1 + (fix is not None)), 20 + (ch + 20) * len(VIEWS)), MC.BG)
    d = ImageDraw.Draw(img)
    run = MC.load_run(DRAFT / unit / "l15-core")
    with tempfile.TemporaryDirectory() as tmp:
        concept = MC.concept_cells(run, pathlib.Path(tmp))
    d.text((6, 4), "concept", fill=(255, 255, 255))
    for x, (r, kind) in enumerate(cols):
        d.text(((x + 1) * cw + 6, 4), f"{r} {kind}", fill=(255, 255, 255))
    for y, v in enumerate(VIEWS):
        if v in concept:
            img.paste(concept[v], (0, 20 + y * (ch + 20)))
        for x, (r, kind) in enumerate(cols):
            name = f"{kind}-{FILES.get(v, v) if kind != 'wire' else v}.png"
            p = DRAFT / unit / f"l15-{r}" / "views" / unit / name
            if p.exists():
                img.paste(MC.fit(Image.open(p)), ((x + 1) * cw, 20 + y * (ch + 20)))
        d.text((4, 20 + y * (ch + 20) + ch), v, fill=(255, 255, 255))
    if fix is not None:
        d.text(((len(cols) + 1) * cw + 6, 4), "hand fix (L14-3), textured", fill=(255, 255, 255))
        top = 40 + MC.TITLE_H + 2 * MC.GAP      # compare_fix.py's strip: header, titles, then a row of CELL height per view
        for y in range(len(VIEWS)):
            y0 = top + y * (ch + MC.GAP)
            img.paste(fix.crop((2 * cw, y0, 3 * cw, y0 + ch)), ((len(cols) + 1) * cw, 20 + y * (ch + 20)))
    return img


def anim(units):
    """anim_check.py (Blender) on each model.glb: anim.json beside it."""
    for u in units:
        for r in RUNS:
            d = DRAFT / u / f"l15-{r}"
            if (d / "model.glb").exists() and not (d / "anim.json").exists():
                subprocess.run(["nice", "-n", "10", "blender", "-b", "-P", str(ROOT / "tools/blender/anim_check.py"), "--", str(d / "model.glb"), str(d / "anim.json")],
                               check=False, capture_output=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--units", default=",".join(AM.UNITS))
    ap.add_argument("--times", default="")
    ap.add_argument("--images", action="store_true")
    ap.add_argument("--anim", action="store_true", help="run anim_check.py on the model.glb of every run first (Blender)")
    args = ap.parse_args(argv)
    units = args.units.split(",")
    if args.anim:
        anim(units)
    noise, secs = AM.read_json(AM.NOISE), times_from(args.times)
    rows = [row_of(u, r, secs.get((u, r), 0.0)) for u in units for r in RUNS]
    print(table(rows, noise))
    print("acceptance (body IoU >= %.2f, stretch <= %.1f, head >= %d tris):" % (BODY_IOU, STRETCH, FACE_TRIS))
    print(json.dumps(acceptance(rows)[0]))
    if args.images:
        OUT.mkdir(parents=True, exist_ok=True)
        for u in units:
            im = sheet(u)
            im.resize((im.width // 2, im.height // 2), Image.LANCZOS).save(OUT / f"{u}.png")
            print("wrote", OUT / f"{u}.png")


if __name__ == "__main__":
    main()
