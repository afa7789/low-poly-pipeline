#!/usr/bin/env python3
"""Stage `polish`: the model (Claude) polishes the clay of a finished run through an MCP server, under honest gates (PIPELINE 31.L13-1).

    python3.14 tools/blender/polish.py <run dir> --id <id> [--model session:opus] [--budget-min 5] [--max-ops 12] [--rig spider]
    python3.14 tools/blender/polish.py <run dir> --id <id> --replay <run dir>/polish.py     (no agent: the recorded ops again)

`Session` is the logic (state, apply with gate and automatic revert, overlays, finish); polish_mcp.py is its stdio transport, polish_ops.py
its hands. An op that makes any view spill more than SPILL_UP, drop in IoU by more than 2 sigma (noise.py), push bare over BARE_MAX,
change the triangle count or fail the mesh lint is reverted. Output in the run dir: clay.glb (polished, only when an op was accepted),
clay.prepolish.glb, polish.py (the accepted ops, replayable), polish.json, a "Polimento" section in review.md, and model.glb carried
(polish_ops.carry) when the run has one (model.prepolish.glb keeps the old).
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np
from PIL import Image, ImageDraw

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import mesh_lint as ML  # noqa: E402
import noise as N  # noqa: E402
import polish_ops as PO  # noqa: E402

VIEWS = PO.VIEWS
BUDGET_MIN, MAX_OPS = 5.0, 12   # what --polish on gives the agent
IOU_DROP = 0.003        # tighter than 2 sigma: an op replays on a fixed mesh (no rebuild noise) and "no view may fall" is the acceptance
SPILL_UP = 0.005        # an op may not raise any view's spill by more than this (vs the previous state and vs the start)
BARE_MAX = 0.10         # honest gate: bare over this is refused unless it did not grow
BARE_UP = 0.005
SPILL_GATE = 0.03
SLIVER_UP = 5.0         # percentage points of slivers an op may add
SCALE = 2               # overlay upscale
KEYS = ("uncovered", "spill", "red", "contact", "body_iou", "body_spill", "body_bare", "prop_iou", "prop_spill", "prop_bare")
BRIEF = """You are polishing the 3D clay model of one WC3-style low-poly unit ({id}) so that it fits its concept sheet from six cameras.
The pipeline built it blind and a gate measured it; you can see the result and fix it by hand.

GOAL (honest gates, never rounded): in every one of the 6 views the share of the MODEL that lies outside the sheet silhouette (spill, RED in
the overlays) must be <= 0.03; the sheet area the model leaves uncovered (bare, GREEN) should stay small (<= 0.10, less is better);
yellow = both agree. Red is the worst: the user wants no red from any angle, a little green is tolerated. IoU must not fall.

TOOLS (mcp__polish__*): state(), views(), inspect(view, region), apply(python_code, why, dry_run=False), done(summary). Read the PNG paths views()
and inspect() return with the Read tool. apply() runs your Python on the clay (vertex edits; rig and skin are untouched), re-measures
the gate and REVERTS the op by itself when any view gets worse (spill +{spill_up}, IoU -{iou_drop}, bare over {bare_max}, lint) compared with the previous state AND with the start.
The code sees `scene` (.pos Z-up vertices, .bones, .H, .views) and helpers: parts(), shrink_part(name, axis, amount), move_part(name,
dx, dy, dz), scale_part(name, sx, sy, sz), erode_toward_view(view, px, part=None, margin=1) (pushes the vertices that sit in red into
the sheet silhouette in that view; call it in a short loop with px=1), smooth_region(name, iters), straighten_prop(name, view),
snap_feet_to_ground(). Amounts are fractions of the model height. A part is a bone name or family ('leg3').

HOW TO WORK
1. Call state() and views() first. Before changing anything, write down which views have the most red, where (which part), and why.
2. Work the view with the most red first, body before props. Prefer ops scoped to ONE part (part=...): an op that fixes one view
   usually costs another, because every view shares the same vertices; the gate shows you the trade. Use views() after each accepted op.
   Every view is framed by the model's own bbox: trimming the extreme vertices shrinks the bbox and rescales the whole view, which often
   hides the gain (lock the extreme vertices when you erode, or trim in the view that sets the frame).
3. Coarse fixes only: move, scale, shrink, erode, smooth. No fine sculpting, no new geometry, nothing about rig or skin.
4. At most {max_ops} ops and {budget} minutes. Call done(summary) when nothing more helps; a rejected op costs you budget, so read the reason; apply(..., dry_run=true) shows what the gate would say without spending an op (use it to explore).

CURRENT TABLE (spill / bare / IoU / contact per view):
{table}
"""


def overlay(sil, view, scale=SCALE):
    """RGB overlay of a view from a silhouette.py output dir: yellow both, RED model outside the sheet, green sheet uncovered."""
    def mk(p):
        return np.asarray(Image.open(p).convert("RGBA"))[..., 3] > 0
    c, m = mk(sil / f"mask-concept-{view}.png"), mk(sil / f"mask-model-{view}.png")
    img = np.full(c.shape + (3,), 255, np.uint8)
    img[c & m], img[m & ~c], img[c & ~m] = (235, 200, 40), (220, 30, 30), (40, 180, 60)
    return Image.fromarray(img).resize((c.shape[1] * scale, c.shape[0] * scale), Image.NEAREST)


def compare_image(run, path):
    """before (top row) | after (bottom row) overlays of the six views of a polished run, with spill % per cell."""
    run = pathlib.Path(run)
    res = json.loads((run / "polish.json").read_text())
    rows = [(run / "polish-work/sil/base", res["before"], "before"), (run / "sil/approved", res["after"], "after")]
    views = [v for v in VIEWS if v in res["after"]]
    w, h = 384, 256
    sheet = Image.new("RGB", (w * len(views), h * 2), "white")
    for r, (sil, tab, label) in enumerate(rows):
        for c, v in enumerate(views):
            im = overlay(sil, v, 1)
            ImageDraw.Draw(im).text((4, 3), f"{label} {v} spill {tab[v]['spill'] * 100:.1f}% bare {tab[v]['bare'] * 100:.1f}%", fill=(0, 0, 0))
            sheet.paste(im, (c * w, r * h))
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def fmt(table):
    return "\n".join(f"{v:7} spill {r['spill']:.3f}  bare {r['bare']:.3f}  iou {r['iou']:.3f}  contact {r['contact']:.3f}"
                     for v, r in table.items())


class Session:
    def __init__(self, run, uid, sheet=None, rig=None, layout="unit", budget_min=5.0, max_ops=12, noise_path=None, resume=False):
        self.run, self.id, self.layout = pathlib.Path(run).resolve(), uid, layout
        self.sheet = pathlib.Path(sheet or ROOT / "artifacts/model-sheets/refs" / uid / "sheet.jpg")
        spec = self.run / "spec.json"
        self.rig = rig if rig is not None else (json.loads(spec.read_text()).get("rig") if spec.exists() else "") or ""
        self.work = self.run / "polish-work"
        self.work.mkdir(exist_ok=True)
        self.cur, self.max_ops, self.budget = self.work / "cur.glb", max_ops, budget_min * 60
        noise_path = pathlib.Path(noise_path or ROOT / "artifacts/model-sheets/runs/draft/noise-l12.json")
        self.noise = N.load(noise_path) if noise_path.exists() else None
        sil = self.run / "silhouette.json"
        tilt = json.loads(sil.read_text()).get("tilt") if sil.exists() else None
        self.cams = tilt or {}
        self.t0, self.ops, self.done_summary = time.monotonic(), [], None
        self.base_sil, self.base = self.measure(self.run / "clay.glb", "base")
        self.base_lint = ML.lint(self.run / "clay.glb")
        saved = self.work / "ops.json"
        if resume and saved.exists():                      # the MCP server's session: its ops and its current state
            data = json.loads(saved.read_text())
            self.ops, self.done_summary = data["ops"], data["summary"]
            self.t0 -= data["elapsed"]
            self.sil, self.table = self.measure(self.cur, "resume")
        else:
            shutil.copy(self.run / "clay.glb", self.cur)
            self.sil, self.table = self.base_sil, self.base

    def save(self):
        (self.work / "ops.json").write_text(json.dumps({"ops": self.ops, "summary": self.done_summary, "elapsed": time.monotonic() - self.t0}))

    # ---- gate
    def measure(self, glb, name, outdir=None):
        out = outdir or self.work / "sil" / name
        cmd = [sys.executable, str(HERE / "silhouette.py"), str(self.sheet), str(glb), str(out), "--layout", self.layout, "--shape",
               "--rig", self.rig] + (["--tilts", ",".join(f"{v}:{'/'.join(map(str, c)) if isinstance(c, list) else c}" for v, c in self.cams.items())] if self.cams else [])
        subprocess.run(cmd, capture_output=True, text=True, env={**os.environ, "SOFT_SIL_THREADS": os.environ.get("SOFT_SIL_THREADS", "4")})
        rep = json.loads((out / "silhouette.json").read_text())
        return out, {v: {"iou": r["iou"], "spill": r["spill"], "bare": r["uncovered"], "contact": r["contact"]} for v, r in rep.items()}

    def view_reasons(self, v, a, b, label):
        """Why view `v` (new numbers `a`) may not replace `b` (the state called `label`)."""
        why = []
        if a["spill"] > b["spill"] + SPILL_UP:
            why.append(f"{v} spill {b['spill']:.3f} -> {a['spill']:.3f} (vs {label})")
        if b["iou"] - a["iou"] > min(N.threshold(v, self.noise, unit=self.id), IOU_DROP):
            why.append(f"{v} IoU {b['iou']:.3f} -> {a['iou']:.3f} falls over {IOU_DROP} (vs {label})")
        if a["bare"] > BARE_MAX and a["bare"] > b["bare"] + BARE_UP:
            why.append(f"{v} bare {b['bare']:.3f} -> {a['bare']:.3f} over {BARE_MAX} (vs {label})")
        return why

    def lint_reasons(self, lint):
        base = self.base_lint
        why = [f"tris {base['tris']} -> {lint['tris']}"] if lint["tris"] != base["tris"] else []
        why += [f"mesh_lint {k} {base[k]} -> {lint[k]}" for k in ("flipped", "degenerate", "nonmanifold_edges") if lint[k] > base[k]]
        if lint["sliver_pct"] > base["sliver_pct"] + SLIVER_UP:
            why.append(f"mesh_lint slivers {base['sliver_pct']} -> {lint['sliver_pct']} %")
        return why

    def verdict(self, after, lint):
        """Reasons to refuse a state (empty = accept): against the previous state and against the start."""
        refs = ((self.table, "previous"), (self.base, "start")) if self.accepted() else ((self.table, "start"),)
        why = [r for v, a in after.items() for ref, label in refs if v in ref for r in self.view_reasons(v, a, ref[v], label)]
        return list(dict.fromkeys(why + self.lint_reasons(lint)))

    def left(self):
        return {"seconds": max(0, round(self.budget - (time.monotonic() - self.t0))), "ops": max(0, self.max_ops - len(self.accepted()))}

    def accepted(self):
        return [o for o in self.ops if o["status"] == "accepted"]

    def delta(self, after):
        return {v: {k: round(a[k] - self.table[v][k], 4) for k in ("spill", "bare", "iou")}
                | {"mark": N.mark(v, a["iou"] - self.table[v]["iou"], self.noise, unit=self.id)} for v, a in after.items() if v in self.table}

    # ---- apply
    def apply(self, code, why, dry_run=False):
        """Run `code`, gate it, keep it or revert it. `dry_run`: only report what the gate would say (no op is recorded or kept,
        but the time spent counts): to try an idea without spending one of the ops."""
        try:
            return self._apply(code, why, dry_run)
        finally:
            self.save()

    def _apply(self, code, why, dry_run=False):
        k = len(self.ops) + 1 if not dry_run else 0
        left = self.left()
        if left["seconds"] <= 0 or left["ops"] <= 0 or len(self.ops) >= 2 * self.max_ops:
            return {"result": "rejected: budget exhausted (time, ops or attempts); call done()", "left": left}
        src, out = self.work / f"op{k or 'dry'}.py", self.work / f"op{k or 'dry'}.glb"
        src.write_text(code)
        run = subprocess.run([sys.executable, str(HERE / "polish_ops.py"), "run", str(self.cur), str(out), str(src), "--sheet", str(self.sheet),
                              "--layout", self.layout, "--cams", json.dumps(self.cams)], capture_output=True, text=True, timeout=300)
        rec = {"n": k, "why": why, "code": code}
        if run.returncode or not out.exists():
            rec |= {"status": "rejected", "reason": f"error: {run.stderr.strip()[-600:]}"}
            if not dry_run:
                self.ops.append(rec)
            return {"result": f"rejected: {rec['reason']}", "left": self.left()}
        sil, after = self.measure(out, f"op{k or 'dry'}")
        reasons = self.verdict(after, ML.lint(out))
        delta = self.delta(after)
        rec |= {"delta": delta, "report": json.loads(run.stdout.strip().splitlines()[-1])}
        if dry_run:
            return {"result": "dry run: " + ("would be rejected: " + "; ".join(reasons) if reasons else "would be accepted"), "delta": delta,
                    "table": fmt(after), "left": self.left()}
        if reasons:
            rec |= {"status": "rejected", "reason": "; ".join(reasons)}
            self.ops.append(rec)
            return {"result": f"rejected: {rec['reason']}", "delta": delta, "left": self.left()}
        shutil.copy(out, self.cur)
        self.sil, self.table = sil, after
        self.ops.append(rec | {"status": "accepted"})
        return {"result": "accepted", "table": fmt(after), "delta": delta, "left": self.left()}

    # ---- eyes
    def overlay(self, view, scale=SCALE):
        return overlay(self.sil, view, scale)

    def views(self):
        out = self.work / "overlays"
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir()
        paths, tiles = {}, []
        for v in [v for v in VIEWS if v in self.table]:
            r = self.table[v]
            im = self.overlay(v)
            ImageDraw.Draw(im).text((6, 4), f"{v} spill {r['spill']:.3f} bare {r['bare']:.3f} iou {r['iou']:.3f}", fill=(0, 0, 0))
            paths[v] = str(out / f"{v}-spill{r['spill'] * 100:.1f}-bare{r['bare'] * 100:.1f}.png")
            im.save(paths[v])
            tiles.append(im)
        w, h = tiles[0].size
        sheet = Image.new("RGB", (w * 3, h * ((len(tiles) + 2) // 3)), "white")
        for i, t in enumerate(tiles):
            sheet.paste(t, ((i % 3) * w, (i // 3) * h))
        paths["all"] = str(out / "all.png")
        sheet.save(paths["all"])
        return paths

    def inspect(self, view, region, zoom=4):
        """Crop of a view's overlay, magnified: region = 'x0,y0,x1,y1' canvas px (panel 384 x 256) or a part name."""
        if view not in self.table:
            raise KeyError(f"no view '{view}'; views: {sorted(self.table)}")
        if re.fullmatch(r"\s*-?[\d.]+(\s*,\s*-?[\d.]+){3}\s*", region):
            x0, y0, x1, y1 = (float(x) for x in region.split(","))
        else:
            x0, y0, x1, y1 = self.part_box(view, region)
        im = self.overlay(view, zoom)
        box = tuple(int(round(c * zoom)) for c in (max(x0, 0), max(y0, 0), x1, y1))
        crop = im.crop(box)
        path = self.work / "overlays" / f"inspect-{view}-{re.sub(r'[^\w.-]', '_', region)}.png"
        path.parent.mkdir(exist_ok=True)
        crop.save(path)
        return str(path)

    def part_box(self, view, part, pad=8):
        import deform_to_sheet as D
        import optimize_verts as OV
        pos, tri = D.welded_mesh(self.cur)
        data, doc, base = D.read(self.cur)
        inv = D.weld_mesh(data, doc, base)[5]
        named = np.empty(len(pos), dtype=object)
        named[inv] = PO.vertex_bones(self.cur)
        sc = PO.Scene(pos, tri, named, {v.name: v for v in OV.make_views(pos, tri, self.sheet, VIEWS, self.layout, {k: tuple(c) if isinstance(c, list) else c for k, c in self.cams.items()})})
        xy = D.view_state(pos, tri, sc.view(view))[0][sc.mask(part)]
        return (*(xy.min(0) - pad), *(xy.max(0) + pad))

    def state(self):
        import deform_to_sheet as D
        pos, tri = D.welded_mesh(self.cur)
        data, doc, base = D.read(self.cur)
        inv = D.weld_mesh(data, doc, base)[5]
        named = np.empty(len(pos), dtype=object)
        named[inv] = PO.vertex_bones(self.cur)
        return {"parts": PO.Scene(pos, tri, named, {}).parts(), "height": float(np.ptp(pos[:, 2])), "tris": self.base_lint["tris"],
                "table": self.table, "start": self.base, "gate": {"spill": SPILL_GATE, "bare": BARE_MAX},
                "accepted_ops": len(self.accepted()), "left": self.left()}

    # ---- finish
    def result(self):
        return {"id": self.id, "before": self.base, "after": self.table, "ops": self.ops, "summary": self.done_summary,
                "seconds": round(time.monotonic() - self.t0, 1), "accepted": len(self.accepted()), "budget_s": self.budget, "max_ops": self.max_ops}


# ---- run-level steps
def script_of(ops):
    return "".join(f"\n# --- op {o['n']}\n# why: {o['why']}\n{o['code'].rstrip()}\n" for o in ops if o["status"] == "accepted")


def blocks(text):
    """[(why, code)] of a recorded polish.py."""
    out = []
    for part in re.split(r"^# --- op \d+\n", text, flags=re.M)[1:]:
        m = re.match(r"# why: (.*)\n", part)
        out.append((m.group(1) if m else "", (part[m.end():] if m else part).rstrip() + "\n"))
    return out


def install(s, usage=None, pipeline=False):
    """Make the polished state the run's: clay, silhouette.json, sil/approved, polish.py/json, carried model.glb, review.md."""
    run, res = s.run, s.result()
    res["usage"] = usage or {}
    (run / "polish.py").write_text(script_of(s.ops))
    if s.accepted():
        pre = run / "clay.prepolish.glb"
        if pipeline or not pre.exists():     # in the pipeline clay.glb is the fresh build: any older prepolish is stale
            shutil.copy(run / "clay.glb", pre)
        shutil.copy(s.cur, run / "clay.glb")
        approved = run / "sil" / "approved"
        _, final = s.measure(run / "clay.glb", "final", approved)
        res["after"] = final
        summary_of(run, approved)
        res["model"] = None if pipeline else carry_model(s)
    (run / "polish.json").write_text(json.dumps(res, indent=2))
    review(run, res)
    return res


def summary_of(run, approved):
    """Refresh the run's silhouette.json summary from the new gate report (the keys spec_pipeline.shape_review writes)."""
    path = run / "silhouette.json"
    if not path.exists():
        return
    summary, rep = json.loads(path.read_text()), json.loads((approved / "silhouette.json").read_text())
    summary["approved"] = {k: r["iou"] for k, r in rep.items()}
    for key in KEYS:
        summary[key] = {k: r[key] for k, r in rep.items() if key in r}
    path.write_text(json.dumps(summary, indent=2))


def carry_model(s):
    run, model = s.run, s.run / "model.glb"
    if not (model.exists() and (run / "clay.prepolish.glb").exists()):
        return None
    pre = run / "model.prepolish.glb"
    if not pre.exists():
        shutil.copy(model, pre)
    PO.carry(run / "clay.prepolish.glb", run / "clay.glb", pre, model)
    return {"before": s.measure(pre, "model-before")[1], "after": s.measure(model, "model")[1]}


def review(run, res):
    rows = "\n".join(f"| {v} | {res['before'][v]['spill']:.3f} -> {res['after'][v]['spill']:.3f} | {res['before'][v]['bare']:.3f} -> {res['after'][v]['bare']:.3f} "
                     f"| {res['before'][v]['iou']:.3f} -> {res['after'][v]['iou']:.3f} | {res['before'][v]['contact']:.3f} -> {res['after'][v]['contact']:.3f} |"
                     for v in res["after"] if v in res["before"])
    ops = "\n".join(f"- op {o['n']} {o['status']}: {o['why']}" + (f" ({o['reason']})" if o.get("reason") else "") for o in res["ops"]) or "- none"
    text = (f"## Polimento\n\n{res['accepted']} ops aceites de {len(res['ops'])}, {res['seconds']} s.\n\n| vista | spill | bare | IoU | contact |\n|---|---|---|---|---|\n"
            f"{rows}\n\n{ops}\n")
    path = run / "review.md"
    old = path.read_text() if path.exists() else ""
    path.write_text(re.sub(r"\n## Polimento\n.*?(?=\n## |\Z)", "", old, flags=re.S).rstrip() + "\n\n" + text)


def config(run, args, budget_min, max_ops):
    cfg = {"mcpServers": {"polish": {"command": sys.executable, "args": [str(HERE / "polish_mcp.py"), "--run", str(run), "--id", args.id,
           "--budget-min", str(budget_min), "--max-ops", str(max_ops)] + (["--rig", args.rig] if args.rig is not None else [])
           + (["--sheet", str(args.sheet)] if args.sheet else [])}}}
    path = pathlib.Path(run) / "polish-work" / "mcp.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(cfg))
    return path


def agent(args, run):
    """One `claude -p` that polishes through the MCP server; (usage counters, claude's final text)."""
    (run / "polish-work").mkdir(exist_ok=True)
    (run / "polish-work" / "ops.json").unlink(missing_ok=True)
    probe = Session(run, args.id, args.sheet, args.rig, budget_min=args.budget_min, max_ops=args.max_ops)
    brief = BRIEF.format(id=args.id, spill_up=SPILL_UP, iou_drop=IOU_DROP, bare_max=BARE_MAX, max_ops=args.max_ops, budget=args.budget_min, table=fmt(probe.base))
    cfg = config(run, args, args.budget_min, args.max_ops)
    model = args.model.split(":", 1)[-1] or "opus"
    argv = ["claude", "-p", "--model", model, "--tools", "Read", "--allowedTools", "Read,mcp__polish__*", "--mcp-config", str(cfg),
            "--strict-mcp-config", "--no-session-persistence", "--setting-sources", "", "--output-format", "json", "--add-dir", str(run / "polish-work")]
    with tempfile.TemporaryDirectory() as cwd:
        out = subprocess.run(argv, input=brief, cwd=cwd, capture_output=True, text=True, timeout=int(args.budget_min * 60 + 240))
    try:
        r = json.loads(out.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"claude -p failed: {(out.stderr or out.stdout)[-300:]}") from None
    return {k: v for k, v in (r.get("usage") or {}).items() if isinstance(v, int)}, r.get("result") or ""


def replay(args, run):
    s = Session(run, args.id, args.sheet, args.rig, budget_min=1e6, max_ops=1000)
    for why, code in blocks(pathlib.Path(args.replay).read_text()):
        print(s.apply(code, why)["result"])
    return s


def stage(args, run, pipeline=False):
    """The agent session on `run`, then install; `args`: id, model, budget_min, max_ops, rig, sheet."""
    usage, text = agent(args, run)
    s = Session(run, args.id, args.sheet, args.rig, budget_min=args.budget_min, max_ops=args.max_ops, resume=True)
    s.done_summary = s.done_summary or text[-600:]
    return install(s, usage, pipeline)


def run_in_pipeline(args):
    """spec_pipeline --polish on (before stage 2): `args` is the pipeline's. model.glb does not exist yet: after_colour carries the polish to it."""
    ns = argparse.Namespace(id=args.id, model=args.model, budget_min=BUDGET_MIN, max_ops=MAX_OPS, rig=args.rig, sheet=str(args.sheet))
    return stage(ns, args.out.resolve(), pipeline=True)


def after_colour(args):
    """spec_pipeline --polish on (after stage 2): the textured model.glb was rebuilt from the spec: give it the clay's polish."""
    run = args.out.resolve()
    if not (run / "polish.json").exists():
        return None
    s = Session(run, args.id, str(args.sheet), args.rig)
    res = json.loads((run / "polish.json").read_text())
    res["model"] = carry_model(s)
    (run / "polish.json").write_text(json.dumps(res, indent=2))
    return res["model"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=pathlib.Path)
    ap.add_argument("--id", required=True)
    ap.add_argument("--model", default="session:opus")
    ap.add_argument("--budget-min", type=float, default=5.0)
    ap.add_argument("--max-ops", type=int, default=12)
    ap.add_argument("--rig", default=None)
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--image", type=pathlib.Path, default=None, help="only write the before|after overlay image of an already polished run")
    ap.add_argument("--replay", type=pathlib.Path, default=None, help="apply the ops of a recorded polish.py instead of asking the agent")
    args = ap.parse_args()
    run = args.run.resolve()
    if args.image:
        compare_image(run, args.image)
        return 0
    res = install(replay(args, run)) if args.replay else stage(args, run)
    print(f"polish {args.id}: {res['accepted']}/{len(res['ops'])} ops accepted in {res['seconds']} s")
    print(fmt(res["after"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
