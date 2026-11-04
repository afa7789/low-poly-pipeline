#!/usr/bin/env python3
"""Local viewer for model-sheet reference images.

    python3 serve.py [--host 127.0.0.1] [--port 8899]

Scans artifacts/model-sheets/refs/, artifacts/reference/hive/{renders,mdx,icons},
artifacts/model-sheets/prompts/ and artifacts/model-sheets/runs/draft/,
merging unit metadata from data/compendium.json + wc3-model-map.json.
No network, no deps, no build step, no caching (files change concurrently).

Review contract (POST /api/review, JSON body):
    {"id": "<unit id>", "verdict": "approved" | "rejected", "note": "<str>"}
    {"id": "<unit id>", "clear": true}          # deletes the review entry

Export (GET /api/export -> JSON, GET /api/export.md -> Markdown):
    approved / rejected / pending partitions of the unit list, for handing
    review results to the next generation batch.
"""
import argparse
import datetime
import json
import mimetypes
import os
import pathlib
import re
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

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
INDEX = pathlib.Path(__file__).resolve().parent / "index.html"
REVIEWS = pathlib.Path(__file__).resolve().parent / "reviews.json"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


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


def lookup_kind(uid):
    """Compendium kind, falling back to wc3-map kind (None when neither)."""
    by_id, wc3 = load_unit_maps()
    entry = by_id.get(uid.lower())
    w = wc3.get(uid)
    w = w if isinstance(w, dict) else None
    return (entry or {}).get("kind") or (w or {}).get("kind")


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


def glb_path(uid, kind):
    """Resolved contract model.glb for uid's kind, or None.

    units: runs/draft/<id>/roster-v4/model.glb,
    buildings: runs/draft/<id>/roster-buildings-v2/model.glb;
    null kind allows either (unit path first).
    """
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
    ids = set(wc3)
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
             "icons": 0, "glb": 0, "reviewed": 0, "approved": 0, "rejected": 0}
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
        render = (RENDERS / f"{uid}.png").is_file()
        mdx = (MDX / f"{uid}.mdx").is_file()
        ours = ours_by_id.get(uid, [])
        entry = by_id.get(uid.lower())
        kind = (entry or {}).get("kind") or (w or {}).get("kind")
        icon_name = f"{uid}.png"
        icon = (ICONS / icon_name).is_file() or icon_name.lower() in icons_lower
        prompt = prompt_path(uid, kind) is not None
        gp = glb_path(uid, kind)
        glb = gp.relative_to(DRAFT.parent.parent).as_posix() if gp else None
        review = reviews.get(uid.lower())
        review = review if isinstance(review, dict) else None
        units.append({
            "id": uid,
            "name": (entry or {}).get("name") or (w or {}).get("name") or uid,
            "race": (entry or {}).get("race") or (w or {}).get("race"),
            "tier": (entry or {}).get("tier"),
            "kind": kind,
            "images": images,
            "entry": entry,
            "wc3": w,
            "render": render,
            "mdx": mdx,
            "ours": ours,
            "icon": icon,
            "prompt": prompt,
            "glb": glb,
            "review": review,
        })
        stats["total"] += 1
        if render:
            stats["render"] += 1
        if mdx:
            stats["mdx"] += 1
        if ours:
            stats["ours"] += 1
        if images:
            stats["refs"] += 1
        if icon:
            stats["icons"] += 1
        if glb:
            stats["glb"] += 1
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
        race = u.get("race") or "\u2014"
        kind = u.get("kind") or "\u2014"
        return f"- {u['id']} {u['name']} ({race}, {kind}){tail}"

    out = [f"# Concept review export \u2014 {now}", "",
           f"Approved ({data['counts']['approved']}):"]
    out += [line(u, f" [{u.get('ts') or ''}]") for u in data["approved"]]
    out += ["", f"Rejected ({data['counts']['rejected']}):"]
    for u in data["rejected"]:
        note = (u.get("note") or "").replace("\r", " ").replace("\n", " ")
        out.append(line(u, f" \u2014 {note} [{u.get('ts') or ''}]"))
    out += ["", f"Pending ({data['counts']['pending']}):"]
    out += [line(u) for u in data["pending"]]
    out.append("")
    return "\n".join(out)


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


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._handle(head=False)

    def do_HEAD(self):
        self._handle(head=True)

    def do_POST(self):
        if urlparse(self.path).path != "/api/review":
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
        elif path.startswith("/icon/"):
            image = find_icon(unquote(path[len("/icon/"):]))
            if image is None:
                self.send_error(404)
                return
            self._send(200, "image/png", image.read_bytes(), head, no_store=True)
        elif path.startswith("/prompt/"):
            uid = unquote(path[len("/prompt/"):])
            prompt = None
            if uid and uid not in (".", "..") and "/" not in uid and "\\" not in uid:
                prompt = prompt_path(uid, lookup_kind(uid))
            if prompt is None:
                self.send_error(404)
                return
            self._send(200, "text/plain; charset=utf-8", prompt.read_bytes(),
                       head, no_store=True)
        elif path.startswith("/glb/"):
            uid = unquote(path[len("/glb/"):])
            glb = None
            if uid and uid not in (".", "..") and "/" not in uid and "\\" not in uid:
                glb = glb_path(uid, lookup_kind(uid))
            if glb is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "model/gltf-binary")
            self.send_header("Content-Disposition", f'attachment; filename="{uid}.glb"')
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(glb.stat().st_size))
            self.end_headers()
            if not head:
                self.wfile.write(glb.read_bytes())
        elif path.startswith("/refs/"):
            image = safe_nested(path, REFS, "refs", IMAGE_EXTS)
            if image is None:
                self.send_error(404)
                return
            ctype = mimetypes.guess_type(image.name)[0] or "application/octet-stream"
            self._send(200, ctype, image.read_bytes(), head)
        elif path.startswith("/ours/"):
            image = safe_nested(path, OURS, "ours", {".png"})
            if image is None:
                self.send_error(404)
                return
            self._send(200, "image/png", image.read_bytes(), head, no_store=True)
        elif path.startswith("/render/"):
            image = safe_plain(RENDERS, unquote(path[len("/render/"):]), ".png")
            if image is None:
                self.send_error(404)
                return
            self._send(200, "image/png", image.read_bytes(), head, no_store=True)
        elif path.startswith("/mdx/"):
            mdx = safe_plain(MDX, unquote(path[len("/mdx/"):]), ".mdx")
            if mdx is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{mdx.name}"')
            self.send_header("Content-Length", str(mdx.stat().st_size))
            self.end_headers()
            if not head:
                self.wfile.write(mdx.read_bytes())
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
    args = ap.parse_args()
    url = f"http://{args.host}:{args.port}/"
    print(f"Serving on {url}")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    Server((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
