#!/usr/bin/env python3
"""Pairwise vision review of two runs of one unit (ROADMAP-papers S4+N5).

    python3.14 tools/blender/review_pair.py <runA> <runB> --id n005 [--kind mass] [--model session:opus]

Each run is a directory (runs/draft/<id>/<run>). One image per vote: for the front and the RTS
view, `candidate | approved sheet panel | candidate`, the textured model when both runs have a
model.glb, else the clay. The reviewer picks the left or the right candidate on three axes
("looks like the sheet", "looks made by an artist", "reads as a WC3 game model", "continuous form":
no steps, no boxes crossing, PIPELINE 24.L6-6) with one sentence each. The third axis has a fourth cell: a WC3 reference of the same rig class (WC3_REFS; a rig
with none falls back to the unit's sheet-hard panel, a proxy). Four votes in the order A|B, A|B,
B|A, B|A, majority per axis, a tie only at 2-2; all four on the same physical side = position bias =
tie, flagged. Writes <runB>/pairwise.json and appends a line to <runB>/review.md
("pairwise vs <runA>: sheet A 3-1, artist B 4-0, wc3 tie 2-2").
spec_pipeline --pair <runA> runs this for the new run and demotes its status one level when it
loses most axes (the verdict itself is untouched).
"""
import argparse
import concurrent.futures
import json
import pathlib
import re
import sys

from PIL import Image, ImageChops, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from views import layout_of  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
CELL = 448
VOTES = 4
AXES = ("sheet", "artist", "wc3", "form")
WC3_REFS = {"biped": "artifacts/reference/wc3-footman.png"}   # rig class -> a real WC3 render
VIEWS = ("front", "rts")
LEVELS = ("rejected", "placeholder", "prototype-safe", "final-use")
PROMPT = """You review two 3D game-unit models against the approved concept sheet. Each image has
two rows (front view, then the top-down RTS game camera). In each row the MIDDLE cell is the
approved concept sheet; the LEFT cell and the THIRD cell are two candidate models of that unit.
The FOURTH cell of the first row is a reference model from a classic game (Warcraft III), only a
style target, not the unit. Read every image, then judge the two candidates (left vs third cell)
on three axes:
  sheet:  which one looks more like the concept sheet (shape, proportions, colours, props)
  artist: which one looks more like it was made by a game artist (clean readable form, no
          floating or clipped bits, deliberate colour, nothing that looks like a stack of boxes)
  wc3:    which of the two candidates reads more like a game model in the style of the fourth cell
          (clean silhouette, clear masses, nothing like stacked boxes)
  form:   which one has the more continuous surface: flowing from part to part, no steps, no
          ridges where slices meet, no boxes crossing through each other
Answer with one JSON object and nothing else:
{"sheet": "left" or "right", "sheet_why": "one sentence",
 "artist": "left" or "right", "artist_why": "one sentence",
 "wc3": "left" or "right", "wc3_why": "one sentence",
 "form": "left" or "right", "form_why": "one sentence"}"""


def model_of(run, textured):
    return run / ("model.glb" if textured else "clay.glb")


def shoot(glb, tilt, out, lit):
    """front and rts renders of `glb` in `out` (cached: a render already there is kept)."""
    import spec_pipeline as SP
    front, rts = out / f"{glb.stem}-front.png", out / f"{glb.stem}-wc3.png"
    if not (front.exists() and rts.exists()):
        SP.tool("render_unit.py", glb, out, tilt, *(["lit"] if lit else []), blender=True)
    return {"front": front, "rts": rts}


def run_tilt(run):
    """render_unit tilt= argument of the camera the run's silhouette sweep chose for the rts view."""
    f = run / "silhouette.json"
    t = json.loads(f.read_text()).get("tilt", {}).get("rts") if f.exists() else None
    return "tilt=" + (f"rts:{t[0]}/{t[1]}" if t else "")


def sheet_panels(unit, kind, work, name="sheet"):
    """{front, rts} panels of a concept sheet of the unit (sheet = approved, sheet-hard = the build one)."""
    import split_sheet
    sheet = ROOT / "artifacts/model-sheets/refs" / unit / f"{name}.jpg"
    return split_sheet.split(sheet, work / name, name, layout_of(kind))


def crop_figure(path, out):
    """`path` cropped to the pixels that differ from its corner colour (a render of one small
    figure on a big flat background), with a margin; written to `out`."""
    im = Image.open(path).convert("RGB")
    diff = ImageChops.difference(im, Image.new("RGB", im.size, im.getpixel((0, 0)))).convert("L")
    box = diff.point(lambda v: 255 if v > 24 else 0).getbbox()
    if box:
        m = max(box[2] - box[0], box[3] - box[1]) // 10
        im = im.crop((max(box[0] - m, 0), max(box[1] - m, 0), min(box[2] + m, im.width), min(box[3] + m, im.height)))
    im.save(out)
    return out


def wc3_ref(rig, unit, kind, work):
    """(png, is_proxy): the WC3 reference of the rig class, cropped; for a rig without one the
    unit's sheet-hard front panel, a proxy for the target style."""
    ref = ROOT / WC3_REFS[rig] if rig in WC3_REFS else None
    if ref and ref.exists():
        return crop_figure(ref, work / "wc3-ref.png"), False
    return sheet_panels(unit, kind, work, "sheet-hard")["front"], True


def fit_cell(path):
    """The picture centred on a square CELL on the sheet's grey, cropped to its figure."""
    im = Image.open(path).convert("RGB")
    im.thumbnail((CELL, CELL))
    cell = Image.new("RGB", (CELL, CELL), (158, 160, 166))
    cell.paste(im, ((CELL - im.width) // 2, (CELL - im.height) // 2))
    return cell


def vote_image(left, right, panels, wc3, out):
    """Write the two-row `left | sheet | right | wc3` image (the WC3 cell only in the first row);
    left and right map view -> png."""
    img = Image.new("RGB", (CELL * 4, CELL * len(VIEWS)), (158, 160, 166))
    for row, view in enumerate(VIEWS):
        for col, path in enumerate((left[view], panels[view], right[view])):
            img.paste(fit_cell(path), (col * CELL, row * CELL))
        ImageDraw.Draw(img).text((6, row * CELL + 6), view, fill=(0, 0, 0))
    img.paste(fit_cell(wc3), (CELL * 3, 0))
    ImageDraw.Draw(img).text((CELL * 3 + 6, 6), "wc3 style target", fill=(0, 0, 0))
    img.save(out)
    return out


def parse_vote(txt):
    """{axis: 'left'|'right', axis_why: str} from a reply, or None when it has no valid answer."""
    m = re.search(r"\{.*\}", txt, re.S)
    try:
        doc = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        return None
    if not all(doc.get(a) in ("left", "right") for a in AXES):
        return None
    return {k: doc.get(k, "") for a in AXES for k in (a, f"{a}_why")}


def tally(votes):
    """{axis: {'A': n, 'B': n, 'winner': 'A'|'B'|'tie', 'biased': bool}} of votes mapped to A/B
    (to_ab). Votes that all picked the same physical side (3+ votes, so 2 A and 2 B all on
    the left) are position bias, not a judgement: that axis is a tie. Otherwise a tie only at
    an even split."""
    out = {}
    for a in AXES:
        n = {s: sum(v[a] == s for v in votes) for s in "AB"}
        biased = len(votes) >= 3 and len({v[f"{a}_side"] for v in votes}) == 1
        win = "tie" if biased or n["A"] == n["B"] else "A" if n["A"] > n["B"] else "B"
        out[a] = {**n, "winner": win, "biased": biased}
    return out


def to_ab(vote, a_left):
    """The vote with 'left'/'right' turned into 'A'/'B' (a_left: A was on the left); the
    side picked stays as <axis>_side."""
    mapped = dict(vote)
    for a in AXES:
        mapped[a] = "A" if (vote[a] == "left") == a_left else "B"
        mapped[f"{a}_side"] = vote[a]
    return mapped


def sides(n=VOTES):
    """A-on-the-left flag per vote: A|B, A|B, B|A, B|A (the votes run in parallel, so the
    order is only the labelling)."""
    return [i < n // 2 for i in range(n)]


def ask_vote(ask, model, image, tries=2):
    """One parsed vote; a reply with no valid answer (or a failed call) is asked once more."""
    for _ in range(tries):
        try:
            vote = parse_vote(ask(model, PROMPT, [image]))
        except (RuntimeError, OSError):
            continue
        if vote:
            return vote
    return None


def rig_of(run):
    """The rig of the run's spec ('' when it has none)."""
    f = run / "spec.json"
    return json.loads(f.read_text()).get("rig", "") if f.exists() else ""


def compare(run_a, run_b, unit, kind="mass", model="session:opus", work=None, ask=None):
    """Run the pairwise review; returns the result dict (also written to run_b/pairwise.json).
    `ask(model, brief, images) -> str` defaults to spec_pipeline.ask."""
    if ask is None:
        import spec_pipeline
        ask = spec_pipeline.ask
    work = pathlib.Path(work or run_b / "pairwise")
    work.mkdir(parents=True, exist_ok=True)
    textured = all(model_of(r, True).exists() for r in (run_a, run_b))
    shots = {k: shoot(model_of(r, textured), run_tilt(r), work / k, lit=not textured)
             for k, r in (("A", run_a), ("B", run_b))}
    panels = sheet_panels(unit, kind, work)
    flags = sides()
    wc3, proxy = wc3_ref(rig_of(run_b), unit, kind, work)
    images = [vote_image(shots["A" if f else "B"], shots["B" if f else "A"], panels, wc3,
                         work / f"vote{i}.png") for i, f in enumerate(flags)]
    with concurrent.futures.ThreadPoolExecutor(len(images)) as pool:
        replies = list(pool.map(lambda im: ask_vote(ask, model, im), images))
    votes = [(to_ab(v, f), i) for i, (v, f) in enumerate(zip(replies, flags)) if v]
    result = {"unit": unit, "A": run_a.name, "B": run_b.name, "textured": textured,
              "wc3_proxy": proxy, "model": model, "valid_votes": len(votes), "votes": [
                  {"order": "A|B" if flags[i] else "B|A", **v} for v, i in votes],
              **tally([v for v, _ in votes])}
    (run_b / "pairwise.json").write_text(json.dumps(result, indent=2))
    return result


def line(result):
    """The review.md line: 'pairwise vs <A>: sheet A 3-1, artist B 4-0, wc3 tie 2-2' (A = the earlier run)."""
    parts = [f"{a} {result[a]['winner']} {max(result[a]['A'], result[a]['B'])}-"
             f"{min(result[a]['A'], result[a]['B'])}" + (" (position bias)" if result[a]["biased"] else "")
             for a in AXES if a in result]
    return f"pairwise vs {result['A']}: " + ", ".join(parts)


def lost(result):
    """True when the new run (B) loses most of the axes the result has: 2 of 3 (an older 2-axis
    result: both; with the form axis, 3 of 4: a 2-2 is not a loss)."""
    axes = [a for a in AXES if a in result]
    return 2 * sum(result[a]["winner"] == "A" for a in axes) > len(axes)


GATE_AXES = ("form", "artist")      # the axes of the non-regression gate (L15-1): continuous form and "made by an artist"


def regressed(result):
    """True when the new run (B) loses form or artist to the earlier one (A) 3-1 or 4-0 (the votes counted, a tie and a position-bias
    axis do not lose); a 2-2 does not regress. The judge as a gate of non-regression (PIPELINE 33.L15-1), not as a score."""
    return any(result[a]["winner"] == "A" for a in GATE_AXES if a in result)


def gate_line(result):
    """'judge gate: PASS (form B 3-1, artist tie 2-2)' / 'judge gate: FAIL (...)' for the form and artist axes."""
    axes = ", ".join(f"{a} {result[a]['winner']} {max(result[a]['A'], result[a]['B'])}-{min(result[a]['A'], result[a]['B'])}"
                     for a in GATE_AXES if a in result)
    return f"judge gate vs {result['A']}: {'FAIL' if regressed(result) else 'PASS'} ({axes})"


def demote(status):
    """One status level down (rejected stays)."""
    return LEVELS[max(LEVELS.index(status) - 1, 0)] if status in LEVELS else status


def append_review(run_b, result):
    review = run_b / "review.md"
    text = review.read_text() if review.exists() else ""
    review.write_text(text + f"\n{line(result)}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run_a", type=pathlib.Path)
    ap.add_argument("run_b", type=pathlib.Path)
    ap.add_argument("--id", required=True)
    ap.add_argument("--kind", default="mass")
    ap.add_argument("--model", default="session:opus")
    ap.add_argument("--work", type=pathlib.Path, default=None)
    ap.add_argument("--gate", action="store_true",
                    help="non-regression gate: exit 0 when the new run (B) does not lose form or artist to A 3-1 / 4-0, 1 when it does")
    args = ap.parse_args()
    result = compare(args.run_a, args.run_b, args.id, args.kind, args.model, args.work)
    append_review(args.run_b, result)
    print(line(result))
    if args.gate:
        print(gate_line(result))
        return int(regressed(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
