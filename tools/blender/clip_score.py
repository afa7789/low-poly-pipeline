#!/usr/bin/env python3
"""CLIP judge for a run: render x concept panel, render x card text, zero-shot top-k (experiment, not a gate).

    python3.14 tools/blender/clip_score.py <run_dir> --id <unit> [--topk 3]   # JSON on stdout
    python3.14 tools/blender/clip_score.py --correlate [--runs artifacts/model-sheets/runs/draft]

ULIP 2023: CLIP as a cross-modal judge, one embedding per view averaged over the views (multi-view
ensemble), text through several templates. Every number is reported as pos - neg, neg being the mean
against the other units' concepts / texts of the roster, so "all low-poly renders look alike" cancels.
Result (PIPELINE 19.E2): does not correlate with the gates, so it stays out of review.md.

Views come from <run>/views/<id>/model-<view>.png when present, else are cropped from <run>/compare.png
(1440x1536 grid: concept rows 0 and 2, model rows 1 and 3).
"""
import argparse
import json
import pathlib
import re
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
SHEETS = HERE.parents[1] / "artifacts" / "model-sheets"
VIEWS = ("front", "left", "back", "top", "bottom", "rts")
TEMPLATES = ("a low-poly render of {}", "a Warcraft III unit, {}", "a 3D game model of {}")
# compare.png grid: (row, col) of each view; model row = concept row + 1
GRID_SIZE = (1440, 1536)
CELL_W, ROW_Y, ROW_H = 480, (0, 366, 730, 1094), 362
CELL = {"front": (0, 0), "left": (0, 1), "back": (0, 2), "top": (2, 0), "bottom": (2, 1), "rts": (2, 2)}


def crop_compare(compare, view, model):
    """One panel of compare.png; None when the file is not the 1440x1536 grid."""
    if compare.size != GRID_SIZE:
        return None
    row, col = CELL[view]
    y = ROW_Y[row + model]
    return compare.crop((col * CELL_W, y, (col + 1) * CELL_W, y + ROW_H)).convert("RGB")


def run_views(run, uid, model=1):
    """{view: PIL image} of the model (model=1) or concept (model=0) side of a run."""
    out = {}
    compare = Image.open(run / "compare.png") if (run / "compare.png").exists() else None
    for view in VIEWS:
        own = run / "views" / uid / f"model-{view}.png"
        if model and own.exists():
            out[view] = Image.open(own).convert("RGB")
        elif compare is not None and (img := crop_compare(compare, view, model)):
            out[view] = img
    return out


def unit_name(uid):
    """'Human Footman' from the first line of the unit's prompt card ('a Human Footman (id hfoo)')."""
    for path in sorted((SHEETS / "prompts" / uid).glob("unit-*.txt")):
        hit = re.search(r"\ba (.+?) \(id " + re.escape(uid), path.read_text()[:600])
        if hit:
            return hit.group(1).replace('"', "")
    return uid


def roster():
    """Unit ids that have an approved sheet and a prompt card."""
    return sorted(p.name for p in (SHEETS / "refs").iterdir() if (p / "sheet.jpg").exists()
                  and (SHEETS / "prompts" / p.name).is_dir())


def unit_concepts(uid, runs_root):
    """Concept panels of a unit, cropped from the first run of it with a grid compare.png."""
    for run in sorted((runs_root / uid).glob("*")):
        views = run_views(run, uid, model=0)
        if len(views) == len(VIEWS):
            return views
    return {}


def unit(vecs):
    v = np.asarray(vecs, dtype=np.float64)
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def ensemble(vecs):
    """Mean of the per-view embeddings, renormalised (the ULIP multi-view average)."""
    return unit(unit(vecs).mean(axis=0))


def pos_neg(query, own, rest):
    """cosine(query, own) minus the mean cosine against the other units' embeddings."""
    pos = float(query @ own)
    neg = float(np.mean([query @ r for r in rest])) if rest else 0.0
    return pos, neg


def score(model_vecs, concept_vecs, text_vecs, uid, topk=3):
    """All numbers for one run. *_vecs: {unit: (n, d)} embeddings; model_vecs is this run's views only."""
    q = ensemble(model_vecs)
    others = [u for u in concept_vecs if u != uid]
    cpos, cneg = pos_neg(q, ensemble(concept_vecs[uid]), [ensemble(concept_vecs[u]) for u in others])
    texts = {u: ensemble(v) for u, v in text_vecs.items()}
    tpos, tneg = pos_neg(q, texts[uid], [texts[u] for u in texts if u != uid])
    ranked = sorted(texts, key=lambda u: -float(q @ texts[u]))
    per_view = {v: float(unit(model_vecs)[i] @ ensemble(concept_vecs[uid])) for i, v in enumerate(VIEWS[:len(model_vecs)])}
    return {"id": uid, "concept": {"pos": cpos, "neg": cneg, "pos_neg": cpos - cneg},
            "text": {"pos": tpos, "neg": tneg, "pos_neg": tpos - tneg},
            "topk": ranked[:topk], "rank": ranked.index(uid) + 1, "roster": len(ranked),
            "per_view_concept": per_view}


class Clip:
    """open_clip ViT-B/32 (OpenAI weights) on CPU."""

    def __init__(self):
        import open_clip
        import torch
        self.torch = torch
        self.model, _, self.prep = open_clip.create_model_and_transforms("ViT-B-32-quickgelu", pretrained="openai")
        self.model.eval()
        self.tok = open_clip.get_tokenizer("ViT-B-32-quickgelu")

    def images(self, imgs):
        with self.torch.no_grad():
            return self.model.encode_image(self.torch.stack([self.prep(i) for i in imgs])).numpy()

    def texts(self, strings):
        with self.torch.no_grad():
            return self.model.encode_text(self.tok(strings)).numpy()


def embed_roster(clip, runs_root):
    """(concept_vecs, text_vecs) of every roster unit."""
    concepts, texts = {}, {}
    for uid in roster():
        views = unit_concepts(uid, runs_root)
        if views:
            concepts[uid] = clip.images([views[v] for v in VIEWS])
            texts[uid] = clip.texts([t.format(unit_name(uid)) for t in TEMPLATES])
    return concepts, texts


def score_run(clip, run, uid, runs_root, topk=3):
    concepts, texts = embed_roster(clip, runs_root)
    views = run_views(run, uid)
    if len(views) < len(VIEWS) or uid not in concepts:
        raise SystemExit(f"{run}: need all {len(VIEWS)} views and a roster concept for {uid}")
    return score(clip.images([views[v] for v in VIEWS]), concepts, texts, uid, topk)


def truth(run, uid):
    """(gates passed of 6, mean IoU, verdict 1/0/None) of a run, from silhouette.json and review.md."""
    sil = json.loads((run / "silhouette.json").read_text()).get("approved", {})
    if len(sil) < len(VIEWS):
        return None
    sys.path.insert(0, str(HERE))
    import silhouette
    spec = json.loads((run / "spec.json").read_text()) if (run / "spec.json").exists() else {}
    gates = silhouette.gates_for(spec.get("rig"))
    passed = sum(sil[v] >= gates[v] for v in VIEWS)
    review = (run / "review.md").read_text() if (run / "review.md").exists() else ""
    hit = re.search(r"verdict: \*\*(PASS|FAIL)", review)
    return passed, float(np.mean([sil[v] for v in VIEWS])), (hit.group(1) == "PASS") if hit else None


def correlate(clip, runs_root):
    """Spearman of the CLIP scores against gates passed / mean IoU / verdict over every textured run."""
    from scipy.stats import spearmanr
    concepts, texts = embed_roster(clip, runs_root)
    rows = []
    for run in sorted(runs_root.glob("*/*")):
        uid = run.parent.name
        tr = truth(run, uid) if (run / "silhouette.json").exists() else None
        views = run_views(run, uid)
        if tr is None or len(views) < len(VIEWS) or uid not in concepts:
            continue
        s = score(clip.images([views[v] for v in VIEWS]), concepts, texts, uid)
        rows.append({"run": f"{uid}/{run.name}", "concept": s["concept"]["pos_neg"], "text": s["text"]["pos_neg"],
                     "rank": s["rank"], "gates": tr[0], "iou": tr[1], "verdict": tr[2]})
    out = {"n": len(rows), "rows": rows}
    for key in ("concept", "text"):
        for tgt in ("gates", "iou"):
            out[f"spearman_{key}_{tgt}"] = float(spearmanr([r[key] for r in rows], [r[tgt] for r in rows])[0])
        voted = [r for r in rows if r["verdict"] is not None]
        out[f"spearman_{key}_verdict"] = float(spearmanr([r[key] for r in voted], [int(r["verdict"]) for r in voted])[0])
        out["n_verdict"] = len(voted)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", nargs="?")
    ap.add_argument("--id")
    ap.add_argument("--topk", type=int, default=3)
    ap.add_argument("--correlate", action="store_true")
    ap.add_argument("--runs", default=str(SHEETS / "runs" / "draft"))
    args = ap.parse_args()
    clip, runs_root = Clip(), pathlib.Path(args.runs)
    if args.correlate:
        result = correlate(clip, runs_root)
    elif args.run_dir and args.id:
        result = score_run(clip, pathlib.Path(args.run_dir), args.id, runs_root, args.topk)
    else:
        ap.error("need <run_dir> --id <unit>, or --correlate")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
