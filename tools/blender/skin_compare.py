#!/usr/bin/env python3
"""L16-4 battery report (PIPELINE 34.L16-4): runs v16-skin-<technique> of the 6 units against v16-r1 (and v16-skin-off, the same pieces rebuilt).

    python3.14 tools/blender/skin_compare.py [--units n005,hfoo] [--techniques bridge,blend,wrap,weld] [--table] [--images] [--judge] [--accept]

--table   per unit and technique: triangles (pieces -> file), joints skinned, components, verts per tri, planarity, crease share, parts k/n, IoU per
          view, stretch p99.5, non-manifold edges, seconds                       -> history/2026-10-30-l16-skin/table.md
--images  per unit: concept | v16 (= off: the same vertices rebuilt) | techniques, one row per view          -> history/2026-10-30-l16-skin/<id>.png
--judge   review_pair.py (session:opus, one vote at a time) v16-r1 x v16-skin-<t>; kept as runs/draft/<id>/v16-skin-<t>/pairwise-v16.json
--accept  per technique the brief's acceptance (form >= 3-1 for the skin in >= 4/6, sheet and artist not lost in >= 5/6, parts k/n of no unit
          falls, stretch <= 1.5, triangles <= 700). Pure helpers are tested without disk."""
import argparse
import json
import pathlib
import shutil
import sys
import tempfile

from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import eye_compare as EC  # noqa: E402
import make_compare as MC  # noqa: E402

DRAFT = EC.DRAFT
OUT = EC.ROOT / "artifacts/model-sheets/history/2026-10-30-l16-skin"
UNITS = ("n005", "n00U", "hfoo", "n017", "n02X", "n01X")
TECHNIQUES = ("bridge", "blend", "wrap", "weld")
VIEWS = EC.VIEWS
STRETCH_MAX, TRIS_MAX = 1.5, 700


def read(path):
    return json.loads(path.read_text()) if path.exists() else {}


def skin_of(unit, technique):
    return read(DRAFT / unit / f"v16-skin-{technique}/skin.json")


def table(units, techniques):
    head = "| unit | technique | tris pieces -> file | skins | components | verts/tri | planarity | crease % | parts | IoU f/l/b/top/bot/rts | stretch p99.5 | non-manifold | s |"
    lines = [head, "|---" * 13 + "|"]
    for u in units:
        for t in ("off", *techniques):
            s = skin_of(u, t)
            if not s:
                continue
            lines.append(f"| {u} | {t} | {s['tris_pieces']} -> {s['tris']} ({s['file_tris']}) | {s['skins']} | {s['components']} | {s['verts_per_tri']} | {s['planarity']} "
                         f"| {s['crease_pct']} | {s['parts'][0]}/{s['parts'][1]} | {EC.per_view(s['views'], 'iou')} | {EC.v(EC.worst_stretch(s['stretch']), 2)} | {s['nonmanifold']} | {s['skin_s']} |")
    return "\n".join(lines)


def view_file(unit, technique, view):
    """The render of a model in the view, kept by run_unit in eye/skin/views (v16-skin-off is v16-r1's pieces rebuilt: same vertices)."""
    return DRAFT / unit / f"v16-skin-{technique}/eye/skin/views/model-{EC.FILES.get(view, view)}.png"


def sheet(unit, techniques):
    import eye_stage
    cols = ["off", *techniques]
    cw, ch = MC.CELL
    img = Image.new("RGB", (cw * (len(cols) + 1), 20 + (ch + 20) * len(VIEWS)), MC.BG)
    d = ImageDraw.Draw(img)
    with tempfile.TemporaryDirectory() as tmp:
        concept = EC.concept_cells(unit, tmp)
    for x, label in enumerate(["concept", "v16 (off)", *techniques]):
        d.text((x * cw + 6, 4), label, fill=(255, 255, 255))
    for y, view in enumerate(VIEWS):
        top = 20 + y * (ch + 20)
        if view in concept:
            img.paste(concept[view], (0, top))
        for x, t in enumerate(cols):
            img.paste(eye_stage.cell(view_file(unit, t, view)), ((x + 1) * cw, top))
        d.text((4, top + ch), view, fill=(255, 255, 255))
    return img


def judge(unit, technique):
    """review_pair.compare(v16-r1, v16-skin-<t>) one vote at a time; kept as pairwise-v16.json beside the skin run."""
    import review_pair
    new = DRAFT / unit / f"v16-skin-{technique}"
    saved = review_pair.concurrent.futures.ThreadPoolExecutor
    review_pair.concurrent.futures.ThreadPoolExecutor = lambda n: saved(1)
    try:
        result = review_pair.compare(DRAFT / unit / "v16-r1", new, unit, "mass", "session:opus")
    finally:
        review_pair.concurrent.futures.ThreadPoolExecutor = saved
    shutil.move(new / "pairwise.json", new / "pairwise-v16.json")
    print(unit, technique, review_pair.line(result))
    return result


def form_win(result):
    """The skin (B) wins the form axis 3-1 or better."""
    return result["form"]["winner"] == "B" and result["form"]["B"] >= 3


def holds(result):
    """Sheet and artist not lost by the skin (a 2-2 or better, an axis flagged for position bias does not lose)."""
    return all(result[a]["winner"] != "A" for a in ("sheet", "artist"))


def parts_kept(skin, base):
    return skin["parts"][0] >= base["parts"][0]


def acceptance(technique, results, skins, bases):
    """The brief's acceptance for one technique. results/skins/bases: {unit: pairwise result / skin.json / v16-skin-off skin.json}."""
    stretch = max((EC.worst_stretch(s["stretch"]) or 0 for s in skins.values()), default=0)
    out = {"form >= 3-1 in >= 4/6": sum(map(form_win, results.values())) >= 4, "sheet+artist held in >= 5/6": sum(map(holds, results.values())) >= 5,
           "parts k/n kept in every unit": all(parts_kept(skins[u], bases[u]) for u in skins), "stretch <= 1.5": stretch <= STRETCH_MAX,
           "tris <= 700": all(s["tris"] <= TRIS_MAX for s in skins.values())}
    return {"technique": technique, "form wins": sorted(u for u, r in results.items() if form_win(r)), "held": sorted(u for u, r in results.items() if holds(r)),
            "worst stretch": stretch, **out, "ACCEPTED": all(out.values())}


def accept_all(units, techs):
    """The acceptance of every technique over the judged units."""
    report = []
    for t in techs:
        res = {u: read(DRAFT / u / f"v16-skin-{t}/pairwise-v16.json") for u in units}
        res = {u: r for u, r in res.items() if r}
        report.append(acceptance(t, res, {u: skin_of(u, t) for u in res}, {u: skin_of(u, "off") for u in res}))
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--units", default=",".join(UNITS))
    ap.add_argument("--techniques", default=",".join(TECHNIQUES))
    for f in ("table", "images", "judge", "accept"):
        ap.add_argument(f"--{f}", action="store_true")
    args = ap.parse_args(argv)
    units, techs = args.units.split(","), args.techniques.split(",")
    OUT.mkdir(parents=True, exist_ok=True)
    if args.judge:
        for t in techs:
            for u in units:
                if not (DRAFT / u / f"v16-skin-{t}/pairwise-v16.json").exists():
                    judge(u, t)
    if args.table:
        text = table(units, techs)
        (OUT / "table.md").write_text(text + "\n")
        print(text)
    if args.images:
        for u in units:
            im = sheet(u, techs)
            im.resize((im.width // 2, im.height // 2), Image.LANCZOS).save(OUT / f"{u}.png")
            print("wrote", OUT / f"{u}.png")
    if args.accept:
        report = accept_all(units, techs)
        (OUT / "accept.json").write_text(json.dumps(report, indent=1))
        print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
