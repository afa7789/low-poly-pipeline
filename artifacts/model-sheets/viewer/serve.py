#!/usr/bin/env python3
"""Local viewer for model-sheet reference images and the roster-v6 final models.

    python3 serve.py [--host 127.0.0.1] [--port 8899] [--render-missing]

Scans artifacts/model-sheets/refs/, artifacts/reference/hive/{renders,mdx,icons},
artifacts/model-sheets/prompts/ and artifacts/model-sheets/runs/draft/,
merging unit metadata from data/compendium.json + wc3-model-map.json.
The FINAL model per id comes from runs/roster/roster-v6/final-models.json and the
5 pseudo-units (Twins, Mortar crew) from runs/roster/roster-v6/extra-units.json.
No network, no deps, no build step, no caching across requests except an
mtime-keyed cache of the per-run summary/silhouette JSON (files change concurrently).

Final renders (front/left/back/top/bottom/wc3) live in
runs/draft/<id>/<run>/views-final/ and are rendered with
`blender -b -P tools/blender/render_unit.py -- <model.glb> <outdir>` when missing:
lazily on first GET /final/<id>/<view>.png, or all at once with --render-missing.

Review contract (POST /api/review, JSON body):
    {"id": "<unit id>", "verdict": "approved" | "rejected", "note": "<str>"}
    {"id": "<unit id>", "clear": true}          # deletes the review entry

Export (GET /api/export -> JSON, GET /api/export.md -> Markdown):
    approved / rejected / pending partitions of the unit list, for handing
    review results to the next generation batch.

Human evaluation (GET /eval, the 30-unit sample of eval/sample-30.json, one unit at a time,
random order, keys 1-5): POST /api/eval {"session": "YYYYMMDD-HHMMSS", "id", "q1", "q2", "q3": 1-5,
"note"} appends to eval/human-<session>.json; GET /api/eval?session=... lists the sample and the
answered ids; GET /api/eval/export merges every human-*.json. The computer score is never served.
"""
import argparse
import datetime
import json
import mimetypes
import os
import pathlib
import re
import shutil
import subprocess
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

ROOT = pathlib.Path(__file__).resolve().parents[3]
REFS = ROOT / "artifacts/model-sheets/refs"
COMPENDIUM = ROOT / "data/compendium.json"
WC3_MAP = ROOT / "artifacts/model-sheets/wc3-model-map.json"
HIVE = ROOT / "artifacts/reference/hive"
RENDERS = HIVE / "renders"
OURS = RENDERS / "ours"
MDX = HIVE / "mdx"
ICONS = HIVE / "icons"
PROMPTS = ROOT / "artifacts/model-sheets/prompts"
DRAFT = ROOT / "artifacts/model-sheets/runs/draft"
ROSTER = ROOT / "artifacts/model-sheets/runs/roster/roster-v6"
FINAL_MODELS = ROSTER / "final-models.json"
EXTRA_UNITS = ROSTER / "extra-units.json"
RENDER_UNIT = ROOT / "tools/blender/render_unit.py"
BLENDER = shutil.which("blender")
INDEX = pathlib.Path(__file__).resolve().parent / "index.html"
EVAL_PAGE = pathlib.Path(__file__).resolve().parent / "eval.html"
REVIEWS = pathlib.Path(__file__).resolve().parent / "reviews.json"
EVAL = ROOT / "artifacts/model-sheets/eval"
EVAL_SAMPLE = EVAL / "sample-30.json"
EVAL_QUESTIONS = ("q1", "q2", "q3")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
FINAL_VIEWS = ("front", "left", "back", "top", "bottom", "wc3", "walkleft")
IOU_VIEWS = ("front", "left", "back", "top", "bottom", "rts")

_RENDER_LOCK = threading.Lock()
_JSON_CACHE = {}


def load_reviews():
    """Read reviews.json (missing/invalid -> {}); never cached across requests."""
    try:
        data = json.loads(REVIEWS.read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_reviews(reviews):
    """Read-modify-write atomically: tmp file in same dir, then os.replace."""
    tmp = REVIEWS.with_name(REVIEWS.name + ".tmp")
    tmp.write_text(json.dumps(reviews, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, REVIEWS)


def cached_json(path):
    """Parsed JSON of `path`, re-read when its mtime changes; None when missing/invalid."""
    try:
        mtime = path.stat().st_mtime
    except OSError:
        _JSON_CACHE.pop(path, None)
        return None
    hit = _JSON_CACHE.get(path)
    if hit and hit[0] == mtime:
        return hit[1]
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        data = None
    _JSON_CACHE[path] = (mtime, data)
    return data


def _stage_num(dirname):
    """Leading stage token of the part after `<id>-` (up to first '-'), its digits."""
    token = dirname.split("-", 1)[1].split("-", 1)[0]
    m = re.search(r"\d+", token)
    return int(m.group()) if m else -1


def scan_ours():
    """Map unit id -> [{name, files}] for OURS subdirs `<id>-<version>` with >=1 png,
    naturally ordered by stage number then dir name (ascending)."""
    entries = []
    if OURS.is_dir():
        for d in OURS.iterdir():
            if not d.is_dir() or "-" not in d.name:
                continue
            files = sorted(
                f.name for f in d.iterdir()
                if f.is_file() and f.suffix.lower() == ".png"
            )
            if files:
                entries.append((d.name, files))
    entries.sort(key=lambda e: (_stage_num(e[0]), e[0]))
    by_id = {}
    for name, files in entries:
        by_id.setdefault(name.split("-", 1)[0], []).append({"name": name, "files": files})
    return by_id


def load_unit_maps():
    """Compendium entries by lowercase id + wc3-model-map dict (missing -> {})."""
    data = json.loads(COMPENDIUM.read_text())
    by_id = {e["id"].lower(): e for r in data["races"] for e in r["entries"]}
    try:
        wc3 = json.loads(WC3_MAP.read_text())
    except (OSError, ValueError):
        wc3 = {}
    return by_id, wc3


def load_final_models():
    """{id: resolved model.glb path} from final-models.json, only files under DRAFT."""
    data = cached_json(FINAL_MODELS)
    out = {}
    if not isinstance(data, dict):
        return out
    base = DRAFT.resolve()
    for uid, rel in data.items():
        if not isinstance(uid, str) or not isinstance(rel, str):
            continue
        p = pathlib.Path(rel)
        p = (p if p.is_absolute() else ROOT / p).resolve()
        if p.is_relative_to(base) and p.is_file():
            out[uid] = p
    return out


def load_extra_units():
    """{id: {name, race, kind, parent}} for the pseudo-units (Twins, Mortar crew)."""
    data = cached_json(EXTRA_UNITS)
    out = {}
    for e in data if isinstance(data, list) else []:
        if isinstance(e, dict) and isinstance(e.get("id"), str):
            out[e["id"]] = e
    return out


def lookup_kind(uid):
    """Compendium kind, falling back to wc3-map kind, then extra-units (None when none)."""
    by_id, wc3 = load_unit_maps()
    entry = by_id.get(uid.lower())
    w = wc3.get(uid)
    w = w if isinstance(w, dict) else None
    extra = load_extra_units().get(uid) or {}
    return (entry or {}).get("kind") or (w or {}).get("kind") or extra.get("kind")


def prompt_path(uid, kind):
    """Resolved prompt file for uid's kind, or None.

    units: prompts/<id>/unit-<id>.txt (fallback prompts/<id>/unit.txt),
    buildings: prompts/building-<id>.txt; null kind tries unit then building.
    """
    cands = []
    if kind != "building":
        cands += [PROMPTS / uid / f"unit-{uid}.txt", PROMPTS / uid / "unit.txt"]
    if kind != "unit":
        cands.append(PROMPTS / f"building-{uid}.txt")
    base = PROMPTS.resolve()
    for c in cands:
        r = c.resolve()
        if r.is_relative_to(base) and r.is_file():
            return r
    return None


def glb_path(uid, kind, finals=None):
    """Resolved model.glb for uid: the roster-v6 FINAL model when listed, else the
    older contract paths (units: roster-v4, buildings: roster-buildings-v2).
    `finals` = load_final_models() when the caller already has it (one load per request)."""
    final = (load_final_models() if finals is None else finals).get(uid)
    if final is not None:
        return final
    cands = []
    if kind != "building":
        cands.append(DRAFT / uid / "roster-v4" / "model.glb")
    if kind != "unit":
        cands.append(DRAFT / uid / "roster-buildings-v2" / "model.glb")
    base = DRAFT.resolve()
    for c in cands:
        r = c.resolve()
        if r.is_relative_to(base) and r.is_file():
            return r
    return None


def _view_scores(views):
    """{view: iou} from a summary round's `views` block (floats only)."""
    out = {}
    for v in IOU_VIEWS:
        d = (views or {}).get(v)
        if isinstance(d, dict) and isinstance(d.get("iou"), (int, float)):
            out[v] = round(float(d["iou"]), 3)
    return out


def final_info(glb):
    """Per-unit summary of the FINAL run dir holding `glb` (eye summary + silhouette)."""
    run_dir = glb.parent
    summary = cached_json(run_dir / "eye" / "summary.json") or {}
    rounds = summary.get("rounds") if isinstance(summary.get("rounds"), list) else []
    final_round = summary.get("final_round")
    if not isinstance(final_round, int) or not (0 <= final_round < len(rounds)):
        final_round = len(rounds) - 1 if rounds else None
    rnd = rounds[final_round] if final_round is not None else {}
    parts = rnd.get("parts") if isinstance(rnd.get("parts"), list) else None
    if parts and len(parts) == 2 and all(isinstance(x, int) for x in parts):
        share = round(parts[0] / parts[1], 3) if parts[1] else None
    else:
        parts, share = None, None
    skin = summary.get("skin") if isinstance(summary.get("skin"), dict) else {}
    tris = skin.get("tris") if isinstance(skin.get("tris"), int) else rnd.get("tris")
    sil = cached_json(run_dir / "silhouette.json") or {}
    sil_iou = _view_scores({v: {"iou": x} for v, x in (sil.get("approved") or {}).items()}
                           if isinstance(sil.get("approved"), dict) else {})
    eye_views = (run_dir / "eye" / f"round-{final_round}" / "views").is_dir() \
        if final_round is not None else False
    views_final = run_dir / "views-final"
    rendered = all((views_final / f"model-{v}.png").is_file() for v in FINAL_VIEWS[:6])
    return {
        "run": run_dir.name,
        "dir": run_dir.relative_to(ROOT).as_posix(),
        "tris": tris if isinstance(tris, int) else None,
        "llm_calls": summary.get("llm_calls") if isinstance(summary.get("llm_calls"), int) else None,
        "rounds": len(rounds),
        "final_round": final_round,
        "parts": parts,
        "share": share,
        "iou": sil_iou or _view_scores(rnd.get("views")),
        "eye_iou": _view_scores(rnd.get("views")),
        "tilts": summary.get("tilts") if isinstance(summary.get("tilts"), str) else None,
        "seconds": summary.get("seconds"),
        "eye_views": eye_views,
        "rendered": rendered,
        "compare": (run_dir / "compare.png").is_file(),
        "review_md": (run_dir / "review.md").is_file(),
    }


def render_final(uid, glb, tilts=None):
    """Render views-final/ for the FINAL glb with Blender (serialised; idempotent).
    Returns the views-final dir, or None when Blender is missing or the render failed."""
    out = glb.parent / "views-final"
    with _RENDER_LOCK:
        if all((out / f"model-{v}.png").is_file() for v in FINAL_VIEWS[:6]):
            return out
        if not BLENDER or not RENDER_UNIT.is_file():
            return None
        cmd = [BLENDER, "-b", "-P", str(RENDER_UNIT), "--", str(glb), str(out)]
        if tilts:
            cmd.append(f"tilt={tilts}")
        print(f"render {uid} -> {out.relative_to(ROOT)}", flush=True)
        try:
            subprocess.run(cmd, cwd=ROOT, check=True, timeout=300,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError) as e:
            print(f"render {uid} FAILED: {e}", flush=True)
            return None
    return out if (out / "model-front.png").is_file() else None


def render_missing():
    """--render-missing: render views-final/ for every FINAL model lacking it."""
    finals = load_final_models()
    todo = [(uid, glb) for uid, glb in sorted(finals.items())
            if not final_info(glb)["rendered"]]
    print(f"render-missing: {len(todo)} of {len(finals)} models", flush=True)
    for i, (uid, glb) in enumerate(todo, 1):
        tilts = (cached_json(glb.parent / "eye" / "summary.json") or {}).get("tilts")
        ok = render_final(uid, glb, tilts if isinstance(tilts, str) else None)
        print(f"  [{i}/{len(todo)}] {uid} {'ok' if ok else 'FAILED'}", flush=True)


def find_icon(filename):
    """ICONS/<filename> by exact name, else one case-insensitive scan; None."""
    exact = safe_plain(ICONS, filename, ".png")
    if exact is not None:
        return exact
    if not filename.lower().endswith(".png"):
        return None
    low = filename.lower()
    if ICONS.is_dir():
        for f in ICONS.iterdir():
            if f.is_file() and f.name.lower() == low:
                return f
    return None


def units_payload():
    by_id, wc3 = load_unit_maps()
    finals = load_final_models()
    extras = load_extra_units()
    ids = set(wc3) | set(finals) | set(extras)
    if REFS.is_dir():
        ids.update(f.name for f in REFS.iterdir() if f.is_dir())
    ours_by_id = scan_ours()
    reviews = load_reviews()
    # Case-insensitive icon map — one scan per request, never cached across them.
    icons_lower = (
        {f.name.lower(): f.name for f in ICONS.iterdir() if f.is_file()}
        if ICONS.is_dir() else {}
    )
    units = []
    stats = {"total": 0, "render": 0, "mdx": 0, "ours": 0, "refs": 0,
             "icons": 0, "glb": 0, "final": 0, "v6": 0, "v6e": 0, "rendered": 0,
             "reviewed": 0, "approved": 0, "rejected": 0}
    for uid in sorted(ids, key=str.lower):
        images = []
        folder = REFS / uid
        if folder.is_dir():
            images = sorted(
                f.name for f in folder.iterdir()
                if f.is_file() and f.suffix.lower() in IMAGE_EXTS
            )
        w = wc3.get(uid)
        if not isinstance(w, dict):
            w = None
        extra = extras.get(uid) or {}
        parent = extra.get("parent") if isinstance(extra.get("parent"), str) else None
        render_id = uid if (RENDERS / f"{uid}.png").is_file() else \
            (parent if parent and (RENDERS / f"{parent}.png").is_file() else None)
        mdx = (MDX / f"{uid}.mdx").is_file()
        ours = ours_by_id.get(uid, [])
        entry = by_id.get(uid.lower())
        kind = (entry or {}).get("kind") or (w or {}).get("kind") or extra.get("kind")
        icon_id = None
        for cand in (uid, parent):
            if cand and ((ICONS / f"{cand}.png").is_file() or f"{cand}.png".lower() in icons_lower):
                icon_id = cand
                break
        prompt = prompt_path(uid, kind) is not None
        gp = glb_path(uid, kind, finals)
        glb = gp.relative_to(DRAFT.parent.parent).as_posix() if gp else None
        final = final_info(finals[uid]) if uid in finals else None
        review = reviews.get(uid.lower())
        review = review if isinstance(review, dict) else None
        units.append({
            "id": uid,
            "name": (entry or {}).get("name") or (w or {}).get("name") or extra.get("name") or uid,
            "race": (entry or {}).get("race") or (w or {}).get("race") or extra.get("race"),
            "tier": (entry or {}).get("tier"),
            "kind": kind,
            "parent": parent,
            "images": images,
            "entry": entry,
            "wc3": w,
            "render": render_id is not None,
            "render_id": render_id,
            "mdx": mdx,
            "ours": ours,
            "icon": icon_id is not None,
            "icon_id": icon_id,
            "prompt": prompt,
            "glb": glb,
            "final": final,
            "review": review,
        })
        stats["total"] += 1
        if render_id:
            stats["render"] += 1
        if mdx:
            stats["mdx"] += 1
        if ours:
            stats["ours"] += 1
        if images:
            stats["refs"] += 1
        if icon_id:
            stats["icons"] += 1
        if glb:
            stats["glb"] += 1
        if final:
            stats["final"] += 1
            stats["v6e" if final["run"].endswith("e") else "v6"] += 1
            if final["rendered"]:
                stats["rendered"] += 1
        if review:
            stats["reviewed"] += 1
            if review.get("verdict") == "approved":
                stats["approved"] += 1
            elif review.get("verdict") == "rejected":
                stats["rejected"] += 1
    return {"units": units, "stats": stats}


def export_data():
    """Partition units_payload() units into approved/rejected/pending for /api/export."""
    units = units_payload()["units"]
    approved, rejected, pending = [], [], []
    for u in units:
        r = u["review"]
        if r and r.get("verdict") == "approved":
            approved.append({"id": u["id"], "name": u["name"], "race": u["race"],
                             "kind": u["kind"], "tier": u["tier"],
                             "images": u["images"], "ts": r.get("ts")})
        elif r and r.get("verdict") == "rejected":
            rejected.append({"id": u["id"], "name": u["name"], "race": u["race"],
                             "kind": u["kind"], "tier": u["tier"],
                             "images": u["images"], "ts": r.get("ts"),
                             "note": r.get("note") or ""})
        else:
            pending.append({"id": u["id"], "name": u["name"], "race": u["race"],
                            "kind": u["kind"], "tier": u["tier"]})
    approved.sort(key=lambda u: u["id"].lower())
    rejected.sort(key=lambda u: u["id"].lower())
    pending.sort(key=lambda u: ((u["race"] or "").casefold(),
                                (u["name"] or "").casefold(), u["id"]))
    return {
        "generated": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "counts": {"approved": len(approved), "rejected": len(rejected),
                   "pending": len(pending)},
        "approved": approved,
        "rejected": rejected,
        "pending": pending,
    }


def export_markdown(data):
    """Render export_data() as a paste-into-an-agent-prompt markdown list."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    def line(u, tail=""):
        race = u.get("race") or "—"
        kind = u.get("kind") or "—"
        return f"- {u['id']} {u['name']} ({race}, {kind}){tail}"

    out = [f"# Concept review export — {now}", "",
           f"Approved ({data['counts']['approved']}):"]
    out += [line(u, f" [{u.get('ts') or ''}]") for u in data["approved"]]
    out += ["", f"Rejected ({data['counts']['rejected']}):"]
    for u in data["rejected"]:
        note = (u.get("note") or "").replace("\r", " ").replace("\n", " ")
        out.append(line(u, f" — {note} [{u.get('ts') or ''}]"))
    out += ["", f"Pending ({data['counts']['pending']}):"]
    out += [line(u) for u in data["pending"]]
    out.append("")
    return "\n".join(out)


def eval_units():
    """The 30-unit evaluation sample (id, name, race, rig, run); [] when missing."""
    data = cached_json(EVAL_SAMPLE) or {}
    units = data.get("units") if isinstance(data, dict) else None
    return [u for u in units if isinstance(u, dict) and isinstance(u.get("id"), str)] if units else []


def eval_session_file(session):
    """eval/human-<session>.json for a plain session token, else None."""
    if not isinstance(session, str) or not re.fullmatch(r"[0-9]{8}-[0-9]{6}", session):
        return None
    return EVAL / f"human-{session}.json"


def eval_load(path):
    data = cached_json(path) if path.is_file() else None
    data = data if isinstance(data, dict) else {}
    data.setdefault("session", path.stem.removeprefix("human-"))
    data.setdefault("answers", [])
    return data


def eval_record(payload):
    """Validate one POST /api/eval body -> (answer dict, file) or (error str, None)."""
    f = eval_session_file(payload.get("session"))
    if f is None:
        return "invalid session", None
    uid = payload.get("id")
    if not isinstance(uid, str) or uid not in {u["id"] for u in eval_units()}:
        return "unknown id", None
    scores = {}
    for q in EVAL_QUESTIONS:
        v = payload.get(q)
        if not isinstance(v, int) or isinstance(v, bool) or not 1 <= v <= 5:
            return f"{q} must be an int 1-5", None
        scores[q] = v
    note = payload.get("note")
    note = note.strip() if isinstance(note, str) else ""
    if len(note) > 2000:
        return "note too long", None
    return {"id": uid, **scores, "note": note,
            "ts": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}, f


def eval_save(answer, f):
    """Append-safe: re-read the session file, replace the unit's answer (or append), write atomically."""
    with _RENDER_LOCK:
        data = eval_load(f)
        data["answers"] = [a for a in data["answers"] if a.get("id") != answer["id"]] + [answer]
        EVAL.mkdir(parents=True, exist_ok=True)
        tmp = f.with_name(f.name + ".tmp")
        tmp.write_text(json.dumps(data, indent=1) + "\n")
        os.replace(tmp, f)
    return len(data["answers"])


def eval_export():
    """Every eval/human-*.json merged: one row per (session, unit) with the unit's metadata."""
    meta = {u["id"]: u for u in eval_units()}
    rows, files = [], []
    for f in sorted(EVAL.glob("human-*.json")) if EVAL.is_dir() else []:
        data = eval_load(f)
        files.append(f.name)
        for a in data["answers"]:
            if isinstance(a, dict) and a.get("id") in meta:
                rows.append({"session": data["session"], **meta[a["id"]], **{k: a.get(k) for k in (*EVAL_QUESTIONS, "note", "ts")}})
    return {"generated": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "sample": len(meta), "files": files, "answers": rows}


def safe_nested(path, root, seg, suffixes):
    """Serve root/<plainseg>/<file> — both segments plain (no separators / traversal)."""
    parts = path.split("/")
    if len(parts) != 4 or parts[1] != seg:
        return None
    dirname, filename = unquote(parts[2]), unquote(parts[3])
    for name in (dirname, filename):
        if not name or name in (".", "..") or "/" in name or "\\" in name:
            return None
    if pathlib.Path(filename).suffix.lower() not in suffixes:
        return None
    resolved = (root / dirname / filename).resolve()
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        return None
    return resolved


def safe_plain(base, filename, suffix):
    """Serve a single file by plain name (no path separators) from base dir."""
    if not filename or filename in (".", "..") or "/" in filename or "\\" in filename:
        return None
    if not filename.endswith(suffix):
        return None
    resolved = (base / filename).resolve()
    if not resolved.is_relative_to(base.resolve()) or not resolved.is_file():
        return None
    return resolved


def plain_id(s):
    """A unit id with no separators / traversal, else None."""
    if not s or s in (".", "..") or "/" in s or "\\" in s or len(s) > 32:
        return None
    return s


def final_view_path(uid, view, render):
    """views-final/model-<view>.png of uid's FINAL run (lazily rendered when `render`),
    or None."""
    glb = load_final_models().get(uid)
    if glb is None or view not in FINAL_VIEWS:
        return None
    out = glb.parent / "views-final"
    p = out / f"model-{view}.png"
    if not p.is_file() and render:
        tilts = (cached_json(glb.parent / "eye" / "summary.json") or {}).get("tilts")
        if render_final(uid, glb, tilts if isinstance(tilts, str) else None) is None:
            return None
    return p if p.is_file() else None


def eye_view_path(uid, view):
    """eye/round-<final>/views/model-<view>.png of uid's FINAL run, or None."""
    glb = load_final_models().get(uid)
    if glb is None or view not in FINAL_VIEWS:
        return None
    info = final_info(glb)
    if info["final_round"] is None:
        return None
    p = glb.parent / "eye" / f"round-{info['final_round']}" / "views" / f"model-{view}.png"
    return p if p.is_file() else None


def run_file(uid, name):
    """A plain file (compare.png / review.md) from uid's FINAL run dir, or None."""
    glb = load_final_models().get(uid)
    if glb is None:
        return None
    p = glb.parent / name
    return p if p.is_file() else None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._handle(head=False)

    def do_HEAD(self):
        self._handle(head=True)

    def do_POST(self):
        route = urlparse(self.path).path
        if route not in ("/api/review", "/api/eval"):
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"")
        except (ValueError, TypeError):
            self._json(400, {"error": "invalid JSON"})
            return
        if not isinstance(payload, dict):
            self._json(400, {"error": "invalid JSON"})
            return
        if route == "/api/eval":
            self._post_eval(payload)
        else:
            self._post_review(payload)

    def _post_eval(self, payload):
        answer, f = eval_record(payload)
        if f is None:
            self._json(400, {"error": answer})
            return
        self._json(200, {"saved": answer, "file": f.name, "answered": eval_save(answer, f)})

    def _post_review(self, payload):
        uid = payload.get("id")
        if not isinstance(uid, str) or not uid or len(uid) > 32:
            self._json(400, {"error": "invalid id"})
            return
        reviews = load_reviews()
        if payload.get("clear") is True:
            reviews.pop(uid.lower(), None)
            _write_reviews(reviews)
            self._json(200, {"cleared": True})
            return
        verdict = payload.get("verdict")
        if verdict not in ("approved", "rejected"):
            self._json(400, {"error": "invalid verdict"})
            return
        note = payload.get("note")
        note = note if isinstance(note, str) else ""
        if verdict == "rejected":
            note = note.strip()
            if not note:
                self._json(400, {"error": "note required"})
                return
            if len(note) > 2000:
                self._json(400, {"error": "note too long"})
                return
        else:
            note = ""
        review = {
            "verdict": verdict,
            "note": note,
            "ts": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        reviews[uid.lower()] = review
        _write_reviews(reviews)
        self._json(200, review)

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self._send(code, "application/json; charset=utf-8", body, head=False, no_store=True)

    def _file_or_404(self, path, ctype, head):
        if path is None:
            self.send_error(404)
            return
        self._send(200, ctype, path.read_bytes(), head, no_store=True)

    def _download(self, path, ctype, filename, head):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(path.stat().st_size))
        self.end_headers()
        if not head:
            self.wfile.write(path.read_bytes())

    def _view_route(self, path, seg):
        """(uid, view) for /<seg>/<id>/<view>.png, else None."""
        parts = path.split("/")
        if len(parts) != 4 or parts[1] != seg or not parts[3].endswith(".png"):
            return None
        uid = plain_id(unquote(parts[2]))
        view = unquote(parts[3])[:-4].removeprefix("model-")
        if uid is None or view not in FINAL_VIEWS:
            return None
        return uid, view

    def _handle(self, head):
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, "text/html; charset=utf-8", INDEX.read_bytes(), head)
        elif path == "/api/units":
            body = json.dumps(units_payload()).encode()
            self._send(200, "application/json; charset=utf-8", body, head, no_store=True)
        elif path == "/api/export":
            body = json.dumps(export_data()).encode()
            self._send(200, "application/json; charset=utf-8", body, head, no_store=True)
        elif path == "/api/export.md":
            body = export_markdown(export_data()).encode()
            self._send(200, "text/markdown; charset=utf-8", body, head, no_store=True)
        elif path == "/eval":
            self._send(200, "text/html; charset=utf-8", EVAL_PAGE.read_bytes(), head)
        elif path == "/api/eval":
            session = parse_qs(urlparse(self.path).query).get("session", [None])[0]
            f = eval_session_file(session)
            answered = [a.get("id") for a in eval_load(f)["answers"]] if f and f.is_file() else []
            body = json.dumps({"units": eval_units(), "answered": answered}).encode()
            self._send(200, "application/json; charset=utf-8", body, head, no_store=True)
        elif path == "/api/eval/export":
            body = json.dumps(eval_export(), indent=1).encode()
            self._send(200, "application/json; charset=utf-8", body, head, no_store=True)
        elif path.startswith("/eval/concept/"):
            uid = plain_id(unquote(path[len("/eval/concept/"):]).removesuffix(".png"))
            p = (EVAL / "stimuli" / uid / "concept-front.png") if uid else None
            self._file_or_404(p if p and p.is_file() else None, "image/png", head)
        elif path.startswith("/icon/"):
            self._file_or_404(find_icon(unquote(path[len("/icon/"):])), "image/png", head)
        elif path.startswith("/prompt/"):
            uid = plain_id(unquote(path[len("/prompt/"):]))
            prompt = prompt_path(uid, lookup_kind(uid)) if uid else None
            self._file_or_404(prompt, "text/plain; charset=utf-8", head)
        elif path.startswith("/glb/"):
            uid = plain_id(unquote(path[len("/glb/"):]))
            glb = glb_path(uid, lookup_kind(uid)) if uid else None
            if glb is None:
                self.send_error(404)
                return
            self._download(glb, "model/gltf-binary", f"{uid}.glb", head)
        elif path.startswith("/model/"):
            # same bytes as /glb/ but inline (for the three.js tab)
            uid = plain_id(unquote(path[len("/model/"):]))
            glb = glb_path(uid, lookup_kind(uid)) if uid else None
            self._file_or_404(glb, "model/gltf-binary", head)
        elif path.startswith("/final/"):
            r = self._view_route(path, "final")
            self._file_or_404(final_view_path(*r, render=True) if r else None, "image/png", head)
        elif path.startswith("/eye/"):
            r = self._view_route(path, "eye")
            self._file_or_404(eye_view_path(*r) if r else None, "image/png", head)
        elif path.startswith("/compare/"):
            uid = plain_id(unquote(path[len("/compare/"):]).removesuffix(".png"))
            self._file_or_404(run_file(uid, "compare.png") if uid else None, "image/png", head)
        elif path.startswith("/review/"):
            uid = plain_id(unquote(path[len("/review/"):]).removesuffix(".md"))
            self._file_or_404(run_file(uid, "review.md") if uid else None,
                              "text/plain; charset=utf-8", head)
        elif path.startswith("/refs/"):
            image = safe_nested(path, REFS, "refs", IMAGE_EXTS)
            if image is None:
                self.send_error(404)
                return
            ctype = mimetypes.guess_type(image.name)[0] or "application/octet-stream"
            self._send(200, ctype, image.read_bytes(), head)
        elif path.startswith("/ours/"):
            self._file_or_404(safe_nested(path, OURS, "ours", {".png"}), "image/png", head)
        elif path.startswith("/render/"):
            self._file_or_404(safe_plain(RENDERS, unquote(path[len("/render/"):]), ".png"),
                              "image/png", head)
        elif path.startswith("/mdx/"):
            mdx = safe_plain(MDX, unquote(path[len("/mdx/"):]), ".mdx")
            if mdx is None:
                self.send_error(404)
                return
            self._download(mdx, "application/octet-stream", mdx.name, head)
        else:
            self.send_error(404)

    def _send(self, code, ctype, body, head, no_store=False):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if no_store:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not head:
            self.wfile.write(body)


class Server(ThreadingHTTPServer):
    allow_reuse_address = True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8899)
    ap.add_argument("--render-missing", action="store_true",
                    help="render views-final/ for every FINAL model lacking it, then serve")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    if args.render_missing:
        render_missing()
    url = f"http://{args.host}:{args.port}/"
    print(f"Serving on {url}" + ("" if BLENDER else "  (blender not found: no lazy renders)"))
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    Server((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
