#!/usr/bin/env python3
"""L15-5 the stage with an eye (PIPELINE 33.L15-5): the agent SEES concept x render and redoes the parts by primitive.

    spec_pipeline.py --id n005 --race Human --name "..." --model session:opus --run v16-r1 --eye on --eye-from v15-r1 [--eye-rounds 3]
    spec_pipeline.py ... --eye on                  # after the colour stage of a normal run, on that run's model.glb
    spec_pipeline.py ... --eye replay --eye-from v16-r1 --run v16-r1    # rebuild from the recorded DSL, no model call

The hand fix of L14-3 (an agent that looked at concept and render and rebuilt head, hands, feet and props from tubes, boxes and balls,
flat colour per piece, weight 1.0 on the bone) as a reproducible stage. Input: a run dir with model.glb (its armature and clips are
kept). Rounds r = 0 .. R-1 (R <= 4): the model gets the images (round 0: the concept sheet and the input model's boards; later: the
boards of the last round) and answers a DSL (eye_lib.py) or, from round 1, {"stop": true}. Each DSL is validated before Blender
(bones, sheet box, triangles, roles; one resend with the reason), built, rendered and measured (parts k/n, IoU and spill per view as
guards). The gate only detects a disaster (a coherent view under IoU .6 forces one more round, up to 4); the stop is the model's.
Kept per round in <out>/eye/round-<r>/: prompt.md, images.txt, dsl.json, why.md, model.glb, board-*.png, eval.json. <out>/eye/summary.json
has the rounds, seconds, calls, triangles, parts and guards by round, the stretch of the clips and the vertex hash that --replay
checks (a rebuild from the recorded DSL, no model call). Last steps: outline.apply (L15-3) on model.glb, clay.glb, review.md."""
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageOps

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import eye_critic  # noqa: E402
import eye_lib as EL  # noqa: E402
import eye_paint  # noqa: E402
import eye_skin  # noqa: E402
import make_compare as MC  # noqa: E402
import outline  # noqa: E402
import preflight as PF  # noqa: E402
import split_sheet  # noqa: E402

ROOT = HERE.parents[1]
REFS = ROOT / "artifacts/model-sheets/refs"
RUNS = ROOT / "artifacts/model-sheets/runs/draft"
PROMPT = ROOT / "artifacts/model-sheets/prompts/eye.md"
ROUNDS, MAX_ROUNDS, DISASTER_CAP = 3, 9, 4   # a disaster adds rounds up to the larger of the rounds asked and DISASTER_CAP
STOPS = ("judge", "model", "never")      # --eye-stop (PIPELINE 34.L16-1): who ends the loop early
STALLS = 2                               # judge rule: this many rounds in a row that neither add parts nor win the judge end the loop
DISASTER = 0.6          # a coherent view under this IoU forces another round
VIEWS = ("front", "left", "back", "top", "bottom", "rts")
BOARDS = (("front", "left", "back"), ("top", "bottom", "rts"))
FILE = {"rts": "wc3"}
CLAY = "B4B4B4"
SLOW = 1800             # seconds of one model call
STAGES = ("artist", "critic", "judge", "blender_build", "measure", "boards", "union", "paint", "outline", "stretch", "clay")   # L18 timing.json


def tick(summary, stage, seconds, calls=1):
    """L18: add `seconds` (and `calls`) of a stage to summary['timing']; the wall clock per stage lands in <run>/timing.json."""
    t = summary.setdefault("timing", {}).setdefault(stage, {"s": 0.0, "n": 0})
    t["s"], t["n"] = round(t["s"] + seconds, 2), t["n"] + calls


def timing_file(summary, out):
    """<run>/timing.json: seconds and calls per stage, the share of the total, the total of the run."""
    total = summary.get("seconds") or 0.0
    rows = {k: dict(v, pct=round(100 * v["s"] / total, 1) if total else None) for k, v in summary.get("timing", {}).items()}
    other = round(total - sum(v["s"] for v in rows.values()), 2)
    doc = {"unit": summary.get("unit"), "total_s": total, "stages": rows, "other_s": other}
    (pathlib.Path(out) / "timing.json").write_text(json.dumps(doc, indent=1))
    return doc


class Invalid(ValueError):
    """The reply cannot be built (spec_pipeline.BAD_REPLY covers ValueError: ask() resends once with the reason)."""


def nice(argv, **kw):
    return subprocess.run(["nice", "-n", "10", *map(str, argv)], capture_output=True, text=True, **kw)


# ---------------------------------------------------------------- the sheet in the model's frame
def forward_sign(sheet_doc):
    """y_blender = sign * z_parts: the left panel of the sheet looks right (left_facing +1) when the front is +z of parts.json."""
    return 1.0 if (sheet_doc or {}).get("left_facing") == -1 else -1.0


def box_blender(box3d, sign):
    """parts.json box3d (y up, z toward the viewer of the left panel) -> (lo, hi) in the Blender frame (z up, -y forward)."""
    (x0, y0, z0), (x1, y1, z1) = box3d
    ys = sorted((sign * z0, sign * z1))
    return [min(x0, x1), ys[0], min(y0, y1)], [max(x0, x1), ys[1], max(y0, y1)]


def union(boxes):
    lo = [min(b[0][i] for b in boxes) for i in range(3)]
    hi = [max(b[1][i] for b in boxes) for i in range(3)]
    return [round(v, 3) for v in lo], [round(v, 3) for v in hi]


def context_of(doc, sheet_doc, rig):
    """What the prompt and the validation need from parts.json and the input rig (`rig` = bones.json): the parts table in the Blender
    frame, the box every point must lie in (the sheet's parts and the input model), the roles the sheet has, the model's size."""
    sign = forward_sign(sheet_doc)
    bbox = rig["bbox"]
    boxes = [bbox] + [box_blender(p["box3d"], sign) for p in (doc or {}).get("parts", []) if p.get("box3d")]
    rows = []
    for p in (doc or {}).get("parts", []):
        where = "inside other parts" if not p.get("box3d") else "box " + json.dumps(box_blender(p["box3d"], sign))
        rows.append(f"- {p['name']} | role {p['role']} | bone {p['bone']} | {where} | colour {p.get('zone', '?')}")
    lo, hi = union(boxes)
    return {"parts_text": "\n".join(rows) or "(no parts.json)", "box": (lo, hi), "roles": sorted({p["role"] for p in (doc or {}).get("parts", [])}),
            "ground": round(bbox[0][2], 3), "size": [round(bbox[1][i] - bbox[0][i], 2) for i in range(3)], "face": PF.face_kind((doc or {}).get("identity"))}


FACE_RULES = {
    "eyes": ("Face: a face must be legible with GEOMETRIC pieces, not a picture: eyes as small dark/bright 6-side tubes or balls on the front of the head, fangs/tusks/snout/mask\n"
             "   as small tubes or boxes, goggles as a band plus two lenses. The old model only had a tiny picture of the face that turned into stripes."),
    "lenses": ("Face: the concept's face is glass, not eyes: build the lenses / goggles / visor as GEOMETRIC pieces (a band plus two lenses, a mask as a box or tube,\n"
               "   tusks as small tubes), never a picture; do NOT add eyes behind or beside them. The old model only had a tiny picture of the face that turned into stripes."),
    "none": ("Face: this unit's concept has a BLANK face: do NOT add eyes, nose, mouth or any other face piece beyond the plain face surface (the head and its helmet,\n"
             "   hood or wheel as the sheet draws them). A piece named eye / nose / mouth / teeth is rejected before the build."),
}
FACE_CRITIC = {
    "eyes": "The concept's face has eyes: eyes, mouth, fangs and mask are compared as drawn.",
    "lenses": "The concept's face is glass (lenses, goggles or a visor), no eyes: an eye piece added behind or beside the glass is a defect (severity 2).",
    "none": "The concept's face is BLANK (no eyes, no mouth): any eye, nose, mouth or teeth piece on this unit is a defect of severity 2, fix = remove it.",
}


def bones_text(rig):
    r = lambda v: [round(c, 2) for c in v]  # noqa: E731
    return "\n".join(f"- {n}: {r(b['head'])} -> {r(b['tail'])}, parent {b['parent']}" for n, b in rig["bones"].items())


# ---------------------------------------------------------------- measuring a model
def vertex_hash(glb):
    """sha1 of the vertex positions of a GLB (rounded to 1e-5): the determinism check of --replay."""
    import mesh_lint
    doc, blob = mesh_lint.read_glb(pathlib.Path(glb))
    pos = mesh_lint.geometry(doc, blob)[0]
    return hashlib.sha1(np.round(pos / 1e-5).astype(np.int64).tobytes()).hexdigest()[:16]


def tilt_text(silhouette):
    """The --tilts value of the cameras a silhouette.json pinned: 'top:-20,bottom:30,rts:35/-45'."""
    return ",".join(f"{v}:{'/'.join(map(str, t)) if isinstance(t, list) else t}" for v, t in (silhouette.get("tilt") or {}).items())


def measure(glb, work, sheet, rig_family, tilts=""):
    """Gate (silhouette.py --gate parts) and render (render_unit.py, flat colours) one GLB into `work`; the eval dict:
    {views: {view: {iou, spill, bare, incoherent, parts [k, n]}}, parts [k, n], rows (failing parts), disaster: [views], tilts}.
    `tilts` pins the cameras; "" (default) sweeps them for this model: the cameras of the top, bottom and rts views are a property of the
    concept art, a pinned set that another model chose measures a different design as a disaster (n02X, PIPELINE 32.L14-3), and the sweep is 8 s."""
    work.mkdir(parents=True, exist_ok=True)
    nice([sys.executable, HERE / "silhouette.py", sheet, glb, work / "sil", "--rig", rig_family, "--gate", "parts", *(["--tilts", tilts] if tilts else [])])
    try:
        rep = json.loads((work / "sil/silhouette.json").read_text())
    except (OSError, ValueError):
        return {"views": {}, "parts": [0, 0], "rows": [], "disaster": ["no measurement"], "tilts": ""}
    cams = tilt_text({"tilt": {v: r["tilt"] for v, r in rep.items() if isinstance(r, dict) and r.get("tilt")}})
    nice(["blender", "-b", "-P", HERE / "render_unit.py", "--", glb, work / "views", f"tilt={cams}"])
    pg = work / "sil/parts_gate.json"
    gate = json.loads(pg.read_text()) if pg.exists() else {"rows": [], "k": 0, "n": 0}
    views = {v: {"iou": r["iou"], "spill": r.get("spill"), "bare": r.get("uncovered"), "incoherent": bool(r.get("incoherent")), "parts": r.get("parts")}
             for v, r in rep.items() if isinstance(r, dict) and "iou" in r}
    bad = [r for r in gate["rows"] if not r["ok"]]
    return {"views": views, "parts": [gate["k"], gate["n"]], "rows": bad, "tilts": cams,
            "disaster": [v for v, r in views.items() if r["iou"] < DISASTER and not r["incoherent"]]}


def eval_text(ev):
    """The numbers of a measurement as the prompt shows them."""
    k, n = ev["parts"]
    lines = [f"cameras of the top, bottom and rts renders (picked by matching this model to the sheet): {ev.get('tilts') or 'default'}",
             f"parts {k}/{n} (a part passes when the model covers its pixels in the sheet, in the part's colour, at the prop's size and side)"]
    lines += [f"- {v}: IoU {r['iou']:.2f}, model outside the sheet {r['spill']:.2f}, sheet uncovered {r['bare']:.2f}" + (" (the sheet contradicts itself here)" if r["incoherent"] else "")
              for v, r in ev["views"].items()]
    lines += [f"- FAIL {r['part']} in {r['view']}: cover {r['cover']}" + (f", colour {r['material']}" if r["material"] is not None else "")
              + (", wrong size" if r["size"] is False else "") + (", wrong side of the body" if r["side"] is False else "") for r in ev["rows"][:14]]
    if ev["disaster"]:
        lines.append(f"- DISASTER: IoU under {DISASTER} in {', '.join(ev['disaster'])}: the mass is wrong there, fix it before details")
    return "\n".join(lines)


# ---------------------------------------------------------------- boards (what the model sees)
def concept_panels(sheet, rotate, tmp):
    """{view: PIL image} of the concept sheet's panels, the top/bottom ones turned upright when the sheet draws them rotated."""
    out = {}
    for v, path in split_sheet.split(sheet, pathlib.Path(tmp), "c", "unit").items():
        im = Image.open(path).convert("RGB")
        out[v] = im.rotate(180) if v in rotate else im
    return out


def cell(path, flip=False):
    """A render of the model fitted to a cell by the box of EVERY pixel off the background (MC.fit keeps only the big blobs, and a
    hand or a prop apart from the body would be cut out of the picture the model is shown)."""
    if not pathlib.Path(path).exists():
        return MC.empty_cell("missing")
    img = Image.open(path).convert("RGB")
    img = ImageOps.mirror(img) if flip else img
    box = ImageChops.difference(img, Image.new("RGB", img.size, img.getpixel((0, 0)))).convert("L").point(lambda v: 255 if v > 24 else 0).getbbox()
    return MC.fit(img, box) if box else MC.empty_cell("empty")


def overlay_cell(path):
    if not pathlib.Path(path).exists():
        return MC.empty_cell("missing")
    img = Image.open(path).convert("RGB")
    out = Image.new("RGB", MC.CELL, (0, 0, 0))
    img.thumbnail(MC.CELL)
    out.paste(img, ((MC.CELL[0] - img.width) // 2, (MC.CELL[1] - img.height) // 2))
    return out


def boards(concept, work, stem, label, out_dir, mirror=()):
    """Two PNGs (front/left/back, top/bottom/rts): one row per view, columns concept | model render | overlay. Their paths. `mirror`: views whose
    render is shown flipped (the left panel of a sheet that looks left: the rig's left render looks right, and the overlay is already flipped)."""
    paths = []
    for i, views in enumerate(BOARDS):
        rows = []
        for v in views:
            r = FILE.get(v, v)
            row = MC.join([MC.fit(concept[v]) if v in concept else MC.empty_cell("no panel"), cell(work / "views" / f"{stem}-{r}.png", v in mirror),
                           overlay_cell(work / "sil" / f"overlay-{v}.png")])
            ImageDraw.Draw(row).text((6, 4), v.upper() + (" (render mirrored: the unit's front is on the left)" if v in mirror else ""), fill=(20, 20, 20), font=MC.font(16))
            rows.append(row)
        img = MC.stack([MC.titles(["concept", label, "overlay: red sheet only, green model only"], rows[0].width)] + rows)
        out_dir.mkdir(parents=True, exist_ok=True)
        paths.append(out_dir / f"board-{i + 1}.png")
        img.save(paths[-1])
    return paths


# ---------------------------------------------------------------- the prompt
def fill(template, values):
    for k, v in values.items():
        template = template.replace("{{" + k + "}}", str(v))
    return template


def round_block(r, images, prev_dsl, ev, label):
    names = {"sheet": "the approved concept sheet (all panels of the unit)", "hard": "the same sheet redrawn with flat faceted masses, props in place",
             "props": "the unit's props drawn detached", "b1": f"board 1: rows front / left / back; columns concept | {label} | overlay (red = the sheet where the model is missing, green = the model outside the sheet, yellow = both)",
             "b2": f"board 2: rows top / bottom / rts (the game camera); columns concept | {label} | overlay (same colours)"}
    listing = "\n".join(f"{i}. {names[k]}" for i, (k, _) in enumerate(images, 1))
    if r == 0:
        return (f"## Round 0: what you have (read every image with the Read tool)\n{listing}\n\nThe model on the boards is the OLD one: a smoothed blob that has the mass but "
                f"not the parts (no readable face, one or two colours, props fused into the body). Replace it entirely.\n\nNumbers of the old model:\n{eval_text(ev)}")
    return (f"## Round {r}: look at what you built (read every image with the Read tool)\n{listing}\n\nThe model on the boards is YOUR previous reply, rebuilt. "
            f"Compare it with the concept part by part (head, face, hands, feet, props, colours, proportions) and the overlays. Fix what is wrong.\n\n"
            f"Numbers:\n{eval_text(ev)}\n\nYour previous reply (JSON):\n{json.dumps(prev_dsl, separators=(',', ':'))}")


def make_prompt(unit, ctx, rig, r, images, prev, ev, label, final_note=""):
    lo, hi = ctx["box"]
    stop = ('If the render already reads like the concept in every view, reply {"stop": true, "why": "<what you checked>"} instead. '
            "Otherwise reply with the COMPLETE new object (all pieces), not a patch.") if r else ""
    return fill(PROMPT.read_text(), {
        "name": unit["name"], "race": unit["race"], "role": unit["role"], "rig": unit["rig"], "unit_note": "", "ground": ctx["ground"], "height": ctx["size"][2],
        "width": ctx["size"][0], "depth": ctx["size"][1], "budget": EL.BUDGET, "max_pieces": EL.MAX_PIECES, "need_roles": ", ".join(r_ for r_ in EL.NEED_ROLES if r_ in ctx["roles"]) or "(none)",
        "box_lo_x": lo[0], "box_hi_x": hi[0], "box_lo_y": lo[1], "box_hi_y": hi[1], "box_lo_z": lo[2], "box_hi_z": hi[2], "bones": bones_text(rig),
        "parts": ctx["parts_text"], "round_block": round_block(r, images, prev, ev, label) + final_note, "stop_clause": stop,
        "face_rule": FACE_RULES[ctx.get("face", "eyes")]})


# ---------------------------------------------------------------- the loop
def reply_checker(rig_names, ctx, r, seen):
    """check(reply) for spec_pipeline.ask: parses the JSON, accepts {"stop": true} from round 1, else validates the DSL (Invalid with the reasons)."""
    import spec_pipeline as SP

    def check(reply):
        try:
            doc = SP.json_object(reply)
        except ValueError as err:
            seen["failed"] += 1
            seen["why"].append(f"not a JSON object: {err}"[:200])
            raise Invalid(f"not a JSON object: {err}") from None
        if doc.get("stop") is True and r > 0:
            return
        errors = EL.validate(doc, rig_names, ctx["box"], ctx["roles"], face=ctx.get("face", "eyes"))
        if errors:
            seen["failed"] += 1
            seen["why"].append("; ".join(errors[:4])[:300])
            raise Invalid("; ".join(errors[:12]))
    return check


def parse_reply(reply):
    import spec_pipeline as SP
    return SP.json_object(reply)


def build(src, dsl, out):
    """eye_lib build in Blender: the GLB `out` and its info dict; RuntimeError when no GLB came out."""
    dsl_path = out.with_suffix(".dsl.json")
    dsl_path.write_text(json.dumps(dsl, indent=1))
    out.unlink(missing_ok=True)
    p = EL.run_blender("build", src, dsl_path, out)
    if not out.exists():
        raise RuntimeError("eye_lib build failed: " + (p.stderr or p.stdout)[-400:])
    dsl_path.unlink()
    info = json.loads(out.with_suffix(".json").read_text())
    out.with_suffix(".json").unlink()
    return info


def disaster_only(ev):
    return bool(ev["disaster"]) and ev["disaster"] != ["no measurement"]


def stalled(prev_parts, parts, result):
    """L16-1 judge rule: a round stalls when it passes no more parts than the one before and the judge gives it neither the sheet nor the artist axis."""
    return parts[0] <= prev_parts[0] and not any(result[a]["winner"] == "B" for a in ("sheet", "artist"))


def stop_verdict(stop, ev, note):
    """What the stage does with a {"stop": true} reply: "honour", or the refusal that is recorded and sent back to the model (never twice in a row)."""
    if note:
        return "honour"
    if stop == "never":
        return "ignored (stop=never)"
    return "refused (disaster)" if disaster_only(ev) else "honour"


def stop_note(verdict, ev):
    if verdict.startswith("ignored"):
        return "\n\nYOUR STOP WAS NOT HONOURED: this run measures every round. Edit the model once more; reply with a new complete object."
    return (f"\n\nYOUR STOP WAS REFUSED: the gate measures IoU under {DISASTER} in {', '.join(ev['disaster'])}, "
            "a disaster in the mass of a view the sheet is coherent about. Edit the model; reply with a new complete object.")


def judge_pair(run_a, run_b, unit_id, model="session:opus"):
    """review_pair.compare of two run dirs with ONE vote at a time (the machine is shared); the result is also kept in run_b/pairwise.json."""
    import review_pair
    saved = review_pair.concurrent.futures.ThreadPoolExecutor
    review_pair.concurrent.futures.ThreadPoolExecutor = lambda n: saved(1)
    try:
        return review_pair.compare(run_a, run_b, unit_id, "mass", model)
    finally:
        review_pair.concurrent.futures.ThreadPoolExecutor = saved


def round_run(rd, spec_from):
    """Make a round dir readable by review_pair (silhouette.json for the camera, spec.json for the rig class) and return it."""
    if (rd / "sil/silhouette.json").exists():
        shutil.copy(rd / "sil/silhouette.json", rd / "silhouette.json")
    if (spec_from / "spec.json").exists():
        shutil.copy(spec_from / "spec.json", rd / "spec.json")
    return rd


def judge_round(judge, eye, r, spec_from):
    """The judge's verdict of round r against round r-1 (judge(run_a, run_b) -> pairwise dict)."""
    return judge(round_run(eye / f"round-{r - 1}", spec_from), round_run(eye / f"round-{r}", spec_from))


def judge_step(stop, judge, eye, r, src_run, prev_ev, ev, stalls, summary):
    """L16-1: in --eye-stop judge mode, judge round r against r-1 and return the new stall count (unchanged when the judge is not on)."""
    if stop != "judge" or not judge or r == 0:
        return stalls
    t0 = time.monotonic()
    verdict = judge_round(judge, eye, r, src_run)
    stalls = stalls + 1 if stalled(prev_ev["parts"], ev["parts"], verdict) else 0
    summary["rounds"][-1].update(judge_s=round(time.monotonic() - t0, 1), stalled=stalls > 0, judge={a: verdict[a]["winner"] for a in ("sheet", "artist", "wc3", "form")})
    tick(summary, "judge", time.monotonic() - t0)
    return stalls


def run(unit, src_run, out, ask, rounds=ROUNDS, replay=False, log=print, skin="off", critic=None, stop="model", judge=None, union="off", paint="off", contour="hull"):
    """The stage. unit: {id, name, race, role, rig}; src_run: dir with model.glb (+ silhouette.json); out: the new run dir; ask(prompt, images, check) -> reply.
    critic: ask-like callable of the L16-2 critic (eye_critic.py) or None. skin: --eye-skin technique applied after the last round (L16-4); union: --eye-union (L17-2), instead of the skin.
    Writes out/eye/..., out/model.glb, out/clay.glb; returns the summary dict. stop: "model" ends on the model's {"stop": true}; "never" records it
    and goes on (a measurement run); "judge" also ends after STALLS stalled rounds, judged by judge(run_a, run_b) -> review_pair result."""
    uid, sheet = unit["id"], REFS / unit["id"] / "sheet.jpg"
    eye = out / "eye"
    eye.mkdir(parents=True, exist_ok=True)
    src = eye / "input.glb"      # the input model, kept: --eye on in place overwrites model.glb, replay rebuilds from this
    if not src.exists():
        shutil.copy(src_run / "model.glb", src)
    sil = json.loads((src_run / "silhouette.json").read_text())
    tilts = tilt_text(sil)         # v15's cameras: recorded, not used to measure (see measure)
    sheet_doc = json.loads((REFS / uid / "sheet.json").read_text()) if (REFS / uid / "sheet.json").exists() else {}
    rotate = sheet_doc.get("rotate", [])
    mirrored = [v for v, m in (sheet_doc.get("mirror") or {}).items() if m]
    import parts_fit
    doc = parts_fit.load(sheet)
    EL.run_blender("bones", src, eye / "bones.json")
    rig = json.loads((eye / "bones.json").read_text())
    ctx = context_of(doc, sheet_doc, rig)
    rig_names = set(rig["bones"])
    t_all = time.monotonic()
    summary = {"unit": uid, "from": str(src_run.name), "rounds": [], "llm_calls": 0, "resends": 0, "tilts": tilts, "ctx_box": ctx["box"], "face": ctx["face"], "critic": []}
    with tempfile.TemporaryDirectory() as tmp:
        concept = concept_panels(sheet, rotate, tmp)
        if replay:
            return replay_run(summary, src, eye, out, rotate)
        t0 = time.monotonic()
        base_dir = eye / "base"
        ev = measure(src, base_dir, sheet, unit["rig"])
        summary["base"] = {"seconds": round(time.monotonic() - t0, 1), "parts": ev["parts"], "views": ev["views"], "tris": None}
        stem, label, prev, last_glb = src.stem, "old model", None, None          # the renders are named after the GLB they come from
        imgs_extra = [("sheet", sheet)] + [(k, REFS / uid / f) for k, f in (("hard", "sheet-hard.jpg"), ("props", "sheet-props.jpg")) if (REFS / uid / f).exists()]
        cur = {"work": base_dir, "ev": ev, "dsl": None, "face": ctx["face"]}
        r, builds, note, listed, stalls = 0, 0, "", [], 0
        cap = min(max(rounds, DISASTER_CAP), MAX_ROUNDS)
        while r < cap:
            rd = eye / f"round-{r}"
            rd.mkdir(parents=True, exist_ok=True)
            t0 = time.perf_counter()
            bs = boards(concept, cur["work"], stem, label, rd, mirrored)
            tick(summary, "boards", time.perf_counter() - t0)
            images = (imgs_extra if r == 0 else imgs_extra[:1]) + [("b1", bs[0]), ("b2", bs[1])]
            listed, note, images = critique(critic, unit, r, images, cur, listed, label, rd, summary, note, imgs_extra[:1])
            if listed is None:       # L16-2: the critic said stop
                break
            prompt = make_prompt(unit, ctx, rig, r, images, cur["dsl"], cur["ev"], label, note)
            (rd / "prompt.md").write_text(prompt)
            (rd / "images.txt").write_text("\n".join(str(p) for _, p in images))
            seen = {"failed": 0, "why": []}
            t0 = time.monotonic()
            try:
                reply = ask(prompt, [p for _, p in images], reply_checker(rig_names, ctx, r, seen))
                doc_r = parse_reply(reply)
                if doc_r.get("stop") is not True and EL.validate(doc_r, rig_names, ctx["box"], ctx["roles"], face=ctx.get("face", "eyes")):
                    raise Invalid("the resend is still invalid")
            except (Invalid, RuntimeError, ValueError) as err:
                log(f"eye round {r}: no usable reply ({err}); the stage stops with the last model")
                summary["rounds"].append({"round": r, "error": str(err)[:300], "llm_s": round(time.monotonic() - t0, 1)})
                break
            llm_s = time.monotonic() - t0
            summary["llm_calls"] += 1
            summary["resends"] += seen["failed"]
            tick(summary, "artist", llm_s, 1 + seen["failed"])
            (rd / "why.md").write_text(str(doc_r.get("why", "")) + "\n")
            summary.setdefault("fixed", {})[r] = doc_r.get("fixed", []) if critic else []
            if doc_r.get("stop") is True:
                verdict = stop_verdict(stop, cur["ev"], note)
                log(f"eye round {r}: the model asked to stop ({verdict})")
                summary["rounds"].append({"round": r, "stop": True if verdict == "honour" else verdict, "llm_s": round(llm_s, 1)})
                if verdict == "honour":
                    break
                note = stop_note(verdict, cur["ev"])
                continue
            (rd / "dsl.json").write_text(json.dumps(doc_r, indent=1))
            t0 = time.monotonic()
            glb = rd / "model.glb"
            info = build(src, doc_r, glb)
            build_s = time.monotonic() - t0
            t0 = time.monotonic()
            ev = measure(glb, rd, sheet, unit["rig"])
            (rd / "eval.json").write_text(json.dumps(ev, indent=1))
            tick(summary, "blender_build", build_s)
            tick(summary, "measure", time.monotonic() - t0)
            builds += 1
            summary["rounds"].append({"round": r, "llm_s": round(llm_s, 1), "build_s": round(build_s, 1), "measure_s": round(time.monotonic() - t0, 1), "tris": info["tris"],
                                      "pieces": info["pieces"], "parts": ev["parts"], "views": ev["views"], "disaster": ev["disaster"], "resent": seen["failed"], "resend_why": seen["why"]})
            log(f"eye round {r}: {info['tris']} tris, {info['pieces']} pieces, parts {ev['parts'][0]}/{ev['parts'][1]}, llm {llm_s:.0f}s")
            stalls = judge_step(stop, judge, eye, r, src_run, cur["ev"], ev, stalls, summary)
            cur, last_glb, label, prev, note, stem = {"work": rd, "ev": ev, "dsl": doc_r, "face": ctx["face"]}, glb, f"round {r} model", doc_r, "", glb.stem
            r += 1
            if stalls >= STALLS or (r >= rounds and not (disaster_only(ev) and r < cap)):
                break
        audit(critic, unit, concept, mirrored, cur, listed, label, stem, eye, summary, sheet)
    summary["seconds"] = round(time.monotonic() - t_all, 1)
    return finish(summary, last_glb, prev, src, out, eye, skin, union, paint, contour)


def critique(critic, unit, r, images, cur, listed, label, rd, summary, note, sheet_only):
    """L16-2: one critic call on the model of round r-1 (boards already in `images`); logged in summary['critic']. Returns (defects, note for the
    fixer, the fixer's images), or (None, note, images) when the critic says stop (and the gate sees no disaster): the loop ends.
    Round 0 or no critic: the arguments back, unchanged."""
    if not critic or not r:
        return listed, note, images
    import spec_pipeline as SP
    try:
        doc = eye_critic.review(critic, dict(unit, face_note=FACE_CRITIC[cur.get("face", "eyes")]), r, [p for _, p in images], cur["dsl"], eval_text(cur["ev"]), listed, label, rd, SP.USAGE)
    except (RuntimeError, ValueError, subprocess.TimeoutExpired) as err:       # no critic this round: the artist looks for itself, the error is recorded
        summary["critic"].append({"round": r, "error": str(err)[:300]})
        return [], note, images
    summary["critic"].append({"round": r, "defects": len(doc["defects"]), "verdict": doc["verdict"], "resolved": len(doc["resolved"]),
                              "of_previous": doc["of_previous"], "fix_rate": doc["fix_rate"], "seconds": doc["seconds"], "usage": doc["usage"]})
    summary["llm_calls"] += 1
    tick(summary, "critic", doc["seconds"])
    if doc["verdict"] == "stop" and not disaster_only(cur["ev"]):
        summary["rounds"].append({"round": r, "stop": "critic", "llm_s": 0})
        return None, note, images
    return doc["defects"], note + eye_critic.fixer_note(doc), sheet_only


def audit(critic, unit, concept, mirrored, cur, listed, label, stem, eye, summary, sheet):
    """L16-2: after the last round, one critic call (no fixer) that marks which defects of the last list are gone: the fix rate of the last round.
    Not when there is no critic, no built model, or the critic itself stopped the loop (its call already marked the last list)."""
    if not critic or cur["dsl"] is None or summary["rounds"][-1].get("stop") == "critic":
        return
    bs = boards(concept, cur["work"], stem, label, eye / "audit", mirrored)
    critique(critic, unit, len(summary["rounds"]), [("sheet", sheet), ("b1", bs[0]), ("b2", bs[1])], cur, listed, label, eye / "audit", summary, "", [])
    summary["critic"][-1]["audit"] = True


def replay_run(summary, src, eye, out, rotate):
    """--eye replay: rebuild the last recorded DSL (no model call) and check the vertex hash against the summary."""
    recorded = json.loads((eye / "summary.json").read_text())
    dsl = json.loads((eye / f"round-{recorded['final_round']}" / "dsl.json").read_text())
    glb = eye / "replay.glb"
    info = build(src, dsl, glb)
    same = vertex_hash(glb) == recorded["vertex_hash"]
    print(f"eye replay: {info['tris']} tris, vertex hash {'identical' if same else 'DIFFERENT'} ({recorded['vertex_hash']})")
    summary.update(recorded, replay={"tris": info["tris"], "same": same})
    return summary


def finish(summary, last_glb, dsl, src, out, eye, skin="off", union="off", paint="off", contour="hull"):
    """The files of the stage: model.glb (the last built round, outlined), clay.glb, anim stretch, summary.json, review.md."""
    if last_glb is None:
        summary["final_round"] = None
        (eye / "summary.json").write_text(json.dumps(summary, indent=1))
        return summary
    summary["final_round"] = max(r["round"] for r in summary["rounds"] if "tris" in r)
    final = eye / f"round-{summary['final_round']}" / "model.glb"
    summary["vertex_hash"] = vertex_hash(final)
    clay = dict(dsl, colours={}, pieces=[dict(p, colour=CLAY) for p in dsl["pieces"]])
    t_fin = t0 = time.perf_counter()
    build(src, clay, out / "clay.glb")
    tick(summary, "clay", time.perf_counter() - t0)
    shutil.copy(final, out / "model.glb")
    t0 = time.perf_counter()
    summary["skin"] = eye_skin.apply_stage(src, dsl, out, f"union-{union}" if union != "off" else skin)
    tick(summary, "union", time.perf_counter() - t0, int(union != "off" or skin != "off"))
    t0 = time.perf_counter()
    summary["paint"] = eye_paint.apply_stage(out / "model.glb", paint)      # L17-3: before the contour, which adds a mesh
    tick(summary, "paint", time.perf_counter() - t0, int(paint == "on"))
    t0 = time.perf_counter()
    summary["outline"] = contour in ("hull", "both") and outline.apply(out / "model.glb", hull=True)
    tick(summary, "outline", time.perf_counter() - t0)
    t0 = time.perf_counter()
    summary["stretch"] = stretch_of(out / "model.glb", eye / "anim.json")
    tick(summary, "stretch", time.perf_counter() - t0)
    summary["seconds"] = round((summary.get("seconds") or 0.0) + time.perf_counter() - t_fin, 1)
    timing_file(summary, out)
    (eye / "summary.json").write_text(json.dumps(summary, indent=1))
    (eye / "review.md").write_text(review_text(summary))
    if not (out / "review.md").exists():
        shutil.copy(eye / "review.md", out / "review.md")
    return summary


def stretch_of(glb, out):
    """p99.5 edge stretch per clip (anim_check.py), {} when it did not run."""
    nice(["blender", "-b", "-P", HERE / "anim_check.py", "--", glb, out])
    try:
        return json.loads(pathlib.Path(out).read_text())
    except (OSError, ValueError):
        return {}


def review_text(s):
    lines = [f"# {s['unit']}: eye stage (L15-5), from {s['from']}", "", f"- seconds: {s.get('seconds')}, model calls: {s['llm_calls']}, resends: {s['resends']}",
             f"- final round: {s['final_round']}, vertex hash {s.get('vertex_hash')}", f"- stretch p99.5: {json.dumps(s.get('stretch'))}", "",
             "| round | tris | pieces | parts | llm s | disaster |", "|---|---|---|---|---|---|"]
    lines += [f"| {r['round']} | {r.get('tris', '-')} | {r.get('pieces', '-')} | {'/'.join(map(str, r['parts'])) if 'parts' in r else '-'} | {r.get('llm_s')} | {r.get('disaster', r.get('stop', r.get('error', '')))} |"
              for r in s["rounds"]]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- entry points
def session_ask(model):
    """ask(prompt, images, check) over spec_pipeline.ask; `model` is session:<claude model> (a `claude -p` session)."""
    import spec_pipeline as SP
    return lambda prompt, images, check: SP.ask(model, prompt, images, check=check)


def unit_of(args, spec):
    return {"id": args.id, "name": args.name, "race": args.race, "role": args.role, "rig": args.rig or spec.get("rig") or "biped"}


def seed(src_run, out):
    """Copy the input run's small files into the new run dir (the judge and the compare read them there)."""
    out.mkdir(parents=True, exist_ok=True)
    for f in src_run.iterdir():
        if f.is_file() and f.name not in ("model.glb", "review.md") and not (out / f.name).exists():
            shutil.copy(f, out / f.name)


def run_in_pipeline(args, src_run, ask):
    """spec_pipeline --eye on|replay: the stage on `src_run` into args.out. The summary."""
    spec = json.loads((src_run / "spec.json").read_text()) if (src_run / "spec.json").exists() else {}
    if args.out != src_run:
        seed(src_run, args.out)
    critic = None if getattr(args, "eye_critic", "off") == "off" else session_ask("session:" + args.eye_critic)
    judge = (lambda a, b: judge_pair(a, b, args.id, args.model)) if args.eye_stop == "judge" else None
    return run(unit_of(args, spec), src_run, args.out, ask, rounds=min(max(args.eye_rounds, 1), MAX_ROUNDS), replay=args.eye == "replay",
               skin=args.eye_skin, union=args.eye_union, critic=critic, stop=args.eye_stop, judge=judge,
               paint=args.eye_paint, contour=args.outline)


def from_run(args, ask):
    """spec_pipeline --eye-from RUN: only the stage, on runs/draft/<id>/RUN into args.out. Exit code."""
    s = run_in_pipeline(args, RUNS / args.id / args.eye_from, ask)
    print(f"{args.id}\t{args.run}\teye {args.eye}\tfinal round {s.get('final_round')}\t{s.get('seconds')} s\tparts {(s.get('rounds') or [{}])[-1].get('parts')}")
    return 0 if s.get("final_round") is not None else 1
