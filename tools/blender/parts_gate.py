#!/usr/bin/env python3
"""The gate by part (PIPELINE 33.L15-1): the silhouette gate measures mass, the eye measures parts.

    python3.14 tools/blender/parts_gate.py freeze <id>... [--runs DIR]     # write refs/<id>/sheet.json (the sheet's orientation)

Two things live here.

1. Per part: for each part of refs/<id>/parts.json with a role that a silhouette can show (head, hand, foot, leg, arm, wing,
   tail, prop) and a box in the front or left panel, does the model have it? Three checks per (part, view):
     cover    the model's silhouette covers PART_COVER_MIN of the part's pixels of the sheet (silhouette.cover)
     material the model's flat-colour render has the part's colour zone over PART_COVER_MIN of the part's pixels in that colour
              (only when the zone render exists, i.e. not at the grey clay stage)
     prop     size (the model's pixels near the prop, outside the sheet's body, are 1 +- PART_SIZE_TOL of the prop's) and side
              (the same side of the body as the sheet's prop): the club behind the body fails here, IoU does not see it.
   `parts k/n` is the share of rows that pass every check that applies. PARTS_MIN (.8) is the acceptance.
2. The sheet's orientation (C4): which top/bottom panels are drawn turned 180 degrees and which views are mirrored is a property
   of the sheet, not of the model. `freeze` writes it to refs/<id>/sheet.json (rotation: the majority of the unit's runs;
   mirror of the left panel: which way the sheet's face, hands and head look); silhouette.py reads it (--orient sheet)
   instead of deciding again for each model."""
import argparse
import hashlib
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import silhouette as S  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
PART_VIEWS = ("front", "left")
ROLES = ("head", "hand", "foot", "leg", "arm", "wing", "tail", "prop")
COLOUR_ROLES = ("face", "torso", "pelvis", "other")   # no outline of their own: judged by their colour zone only (the face reads, the coat is the coat's colour)
PART_COVER_MIN = 0.5    # share of the part's sheet pixels the model reaches
PART_SIZE_TOL = 0.4     # a prop's model area within 1 +- this of the sheet's
PART_MIN_PX = 60        # a part under this many pixels (of 384 x 256) in a view is not judged there
PARTS_MIN = 0.8         # acceptance: share of (part, view) rows that pass
BODY_FLOOR = 0.75       # guard: body IoU (never stricter than the view's own silhouette gate)
SPILL_GUARD = 0.15      # guard: share of the body the model has outside the sheet (a disaster detector, not the acceptance)
SIDE_MIN = 10           # px: a prop centroid this close to the body's centre has no side
VOTE_MIN = 0.75         # freeze: a top/bottom panel is rotated when this share of the runs say so
GUARD_VIEWS = ("front", "left", "back", "top", "bottom", "rts")


def zone_of(part, centres):
    """Zone index + 1 (zone_labels' labelling) of the part's parts.json colour, None without one."""
    hexa = part.get("zone")
    if not hexa:
        return None
    rgb = np.array([[int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5)]])
    return int(S.nearest(rgb, centres)[0])


def sheet_mask(fig, part, view, props):
    """The part's pixels of the sheet in the frame of `fig` (normalized canvas): the prop's own mask (outside the body)
    for a prop, else the figure's pixels inside the part's box."""
    import parts_fit
    if part.get("prop") and part["name"] in props:
        return props[part["name"]]
    m = parts_fit.part_mask(np.asarray(fig), part["box2d"][view])
    if getattr(fig, "box", None) is not None:
        m = S.reframe(m, S.geometry(np.asarray(fig)), S.geometry(fig))
    return m


def centroid_x(mask):
    xs = np.where(mask)[1]
    return float(xs.mean()) if len(xs) else None


def prop_checks(sheet_part, model, body, body_cx):
    """(size ok, side ok) of a prop: `sheet_part` the sheet's prop mask (outside the body), `model` the model's silhouette,
    `body` the sheet's body mask. The model's prop = its pixels outside the sheet's body near the sheet's prop."""
    near = S.dilate(sheet_part, S.PROP_NEAR + 4)
    got = model & near & ~body
    ratio = got.sum() / max(sheet_part.sum(), 1)
    size = abs(ratio - 1) <= PART_SIZE_TOL
    want, have = centroid_x(sheet_part), centroid_x(got)
    if have is None:
        return False, False
    side = abs(want - body_cx) < SIDE_MIN or (want - body_cx) * (have - body_cx) > 0
    return bool(size), bool(side)


def evaluate(sheet, layout, panels, concept, masks, keep=None, centres=None):
    """The rows of every judged (part, view). `panels`: framed_panels(), `concept`: the oriented, normalized panels the
    masks were matched against, `masks`: {view: the model silhouette best_match chose}, `keep`: {view: (concept labels,
    model labels)} of zone_views (None = no colour: material is not judged). [] without a parts.json."""
    import parts_fit
    doc = parts_fit.load(sheet)
    rows = []
    for view in (v for v in PART_VIEWS if doc and v in masks and v in panels):
        props = S.prop_masks(sheet, view, layout, panels)
        union = np.any(list(props.values()), axis=0) if props else np.zeros((S.CANVAS_H, S.CANVAS_W), bool)
        body = concept[view].astype(bool) & ~union
        body_cx = centroid_x(body) or S.CANVAS_W / 2
        for part in doc["parts"]:
            if part.get("role") not in (*ROLES, *COLOUR_ROLES) or view not in part.get("box2d", {}):
                continue
            mask = sheet_mask(panels[view], part, view, props)
            row = part_row(part, view, mask, masks[view].astype(bool), (keep or {}).get(view), centres, body, body_cx, part.get("name") in props)
            rows.append(row) if row else None
    return rows


def part_row(part, view, mask, model, labels, centres, body, body_cx, outer=False):
    """One row {part, role, view, px, cover, material, size, side, ok} of a part in a view; None when it is too small."""
    if mask.sum() < PART_MIN_PX:
        return None
    row = {"part": part["name"], "role": part["role"], "view": view, "px": int(mask.sum()),
           "cover": round(S.cover(mask, model), 3), "material": None, "size": None, "side": None}
    z = zone_of(part, centres) if labels is not None and centres is not None else None
    if z:
        piece = mask & (labels[0] == z)
        if piece.sum() >= PART_MIN_PX:
            row["material"] = round(S.cover(piece, labels[1] == z), 3)
    if part.get("prop") and outer:      # a prop drawn inside the body (goggles, a belt) has no outline of its own: cover and material only
        row["size"], row["side"] = prop_checks(mask, model, body, body_cx)
    if part["role"] in COLOUR_ROLES and row["material"] is None:
        return None
    row["ok"] = ((row["cover"] >= PART_COVER_MIN or part["role"] in COLOUR_ROLES) and (row["material"] is None or row["material"] >= PART_COVER_MIN)
                 and row["size"] is not False and row["side"] is not False)
    return row


def summary(rows):
    """{k, n, share, by_view {view: [k, n]}}: rows that pass / rows judged."""
    k = sum(r["ok"] for r in rows)
    by = {v: [sum(r["ok"] for r in rows if r["view"] == v), sum(r["view"] == v for r in rows)] for v in PART_VIEWS}
    return {"k": k, "n": len(rows), "share": round(k / len(rows), 4) if rows else None, "by_view": by}


def text(rows):
    """The table, one line per judged row, then 'parts k/n (xx %)'."""
    f = lambda v: "  -  " if v is None else (f"{v:5.2f}" if isinstance(v, float) else ("  ok " if v else " BAD "))  # noqa: E731
    out = [f"{'part':28} {'view':5} {'px':>5} {'cover':>5} {'mater':>5} {'size':>5} {'side':>5}  ok"]
    out += [f"{r['part'][:28]:28} {r['view']:5} {r['px']:5d} {f(r['cover'])} {f(r['material'])} {f(r['size'])} {f(r['side'])}  "
            f"{'PASS' if r['ok'] else 'FAIL'}" for r in rows]
    s = summary(rows)
    return "\n".join(out + [f"parts {s['k']}/{s['n']}" + (f" ({100 * s['share']:.0f} %)" if s["n"] else " (no parts.json)")])


def guard_ok(g_iou, cov, gate):
    """The guards of one view: body IoU >= min(its silhouette gate, BODY_FLOOR) and body spill <= SPILL_GUARD; True without a gate."""
    return gate is None or bool(g_iou >= min(gate, BODY_FLOOR) and cov["spill"] <= SPILL_GUARD)


def guards(report, gates, incoherent=()):
    """{view: ok} of guard_ok over a silhouette report; a view with no gate, or one the sheet contradicts, is skipped."""
    return {v: guard_ok(*S.gated_values(r), gates[v]) for v, r in report.items()
            if v in GUARD_VIEWS and v not in incoherent and gates.get(v) is not None}


def verdict(held, rows):
    """'PASS' when every guard holds and parts >= PARTS_MIN, 'CHECK(guard: views)' when a guard fails, 'CHECK(parts k/n)'
    otherwise; the tuple orders verdicts (better is bigger): (guards held, parts share)."""
    s = summary(rows)
    share = s["share"] or 0.0
    bad = [v for v, ok in held.items() if not ok]
    if bad:
        return f"CHECK(guard {','.join(bad)})", (0, share)
    if s["n"] and share < PARTS_MIN:
        return f"CHECK(parts {s['k']}/{s['n']})", (1, share)
    return "PASS", (2, share)


# --- the sheet's orientation (C4) -------------------------------------------------------------------------------------

def sheet_json(sheet):
    return pathlib.Path(sheet).with_suffix(".json")


def load_orientation(sheet):
    """refs/<id>/sheet.json {rotate: [views], mirror: {view: bool | None}} or None (no file: decide per model)."""
    path = sheet_json(sheet)
    return json.loads(path.read_text()) if path.exists() else None


FACING_MIN = 0.05       # the left panel's forward cue (share of the panel width) under which the facing is not decided
FACING_ROLES = {"face": 1, "hand": 1, "head": 1, "tail": -1}   # where these parts sit, from the torso, tells which way the figure looks


def left_facing(doc):
    """+1 when the sheet's left panel looks right, -1 left, None when the cue is under FACING_MIN: the face, hands and head
    sit toward the front of the torso (a tail toward the back), in the parts.json boxes of the left panel. A rig's left render
    shows the front on the right (views.VIEWS), so a sheet that looks left needs the mirror."""
    boxes = {p["name"]: p["box2d"]["left"] for p in doc["parts"] if "left" in p.get("box2d", {})}
    centre = lambda name: (boxes[name][0] + boxes[name][2]) / 2  # noqa: E731
    torso = next((p["name"] for p in doc["parts"] if p["role"] == "torso" and p["name"] in boxes), None)
    if torso is None:
        return None
    cue = sum(w * (centre(p["name"]) - centre(torso)) for p in doc["parts"] if p["name"] in boxes
              for role, w in FACING_ROLES.items() if p["role"] == role)
    return None if abs(cue) < FACING_MIN else (1 if cue > 0 else -1)


def freeze(unit, runs, refs):
    """Write refs/<unit>/sheet.json. rotate: the top/bottom panels drawn turned 180 degrees, the views VOTE_MIN of the runs of
    the unit on disk (<runs>/<unit>/*/silhouette.json top_orientation) agree on. mirror: front, back, top and bottom are not
    mirrored (the rig and the sheet share the x axis); left is mirrored when the sheet looks left (left_facing), None
    (the model decides) when the cue is weak. The mirror is NOT a vote of past runs: they chose it by IoU, and a club put
    behind the body fits a left panel that looks left as well as one in front (n02X v15: 0 of 153 mirrored, the hand fix
    needs it)."""
    import parts_fit
    heads, n = {"top": [0, 0], "bottom": [0, 0]}, 0
    for f in sorted((runs / unit).glob("*/silhouette.json")):
        try:
            d = json.loads(f.read_text())
        except ValueError:
            continue
        if not (isinstance(d, dict) and isinstance(d.get("top_orientation"), dict)):
            continue
        n += 1
        for v, h in d["top_orientation"].items():
            heads[v][0] += h == S.HEAD[v][1]
            heads[v][1] += 1
    doc = parts_fit.load(refs / unit / "sheet.jpg")
    face = left_facing(doc) if doc else None
    out = {"unit": unit, "runs": n, "rotate": [v for v, (t, m) in heads.items() if m and t / m >= VOTE_MIN],
           "head_votes": heads, "mirror": {"front": False, "back": False, "top": False, "bottom": False,
                                           "left": None if face is None else face < 0},
           "left_facing": face, "source": "rotate: majority of the runs' top_orientation; mirror: parts.json (left_facing)",
           "parts_sha": hashlib.sha1((refs / unit / "parts.json").read_bytes()).hexdigest()[:12] if doc else None}
    (refs / unit / "sheet.json").write_text(json.dumps(out, indent=2))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=("freeze",))
    ap.add_argument("units", nargs="+")
    ap.add_argument("--runs", type=pathlib.Path, default=ROOT / "artifacts/model-sheets/runs/draft")
    ap.add_argument("--refs", type=pathlib.Path, default=ROOT / "artifacts/model-sheets/refs")
    args = ap.parse_args()
    for u in args.units:
        doc = freeze(u, args.runs, args.refs)
        print(u, doc["runs"], "runs", "rotate", doc["rotate"], "mirror", doc["mirror"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
