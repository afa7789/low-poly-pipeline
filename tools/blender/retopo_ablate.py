#!/usr/bin/env python3
"""Ablation of the retopology on the 5 v12 units (PIPELINE 28.L10-3 / 28.L10-4): same dense mesh, one row per way to reach B triangles.

    blender -b -P tools/blender/retopo_blender.py -- export <dir>        # the dense meshes + the fields, once
    python3.14 tools/blender/retopo_ablate.py <dir> [--src a0|a5] [--target 600] [--units n005,...] [--json out.json]

Rows: union (the v12 clay.glb), COLLAPSE (Blender Decimate, blind; needs `blender` on the PATH), QEM (plain), + guard (15 degrees,
turn), + SDF projection, + deviation guard (H/50), + features (35 degrees). Columns: tris, sliver_pct, normal_diff (mean, share in 60-100), fairness,
flipped, boundary / non-manifold edges, euler (F - 2V + 4), sdf_dev (mean, p95, max in % of H and the max in voxels), IoU of the
6 views against the approved sheet (silhouette.py panels, cameras of the run's silhouette.json), seconds.
"""
import argparse
import json
import pathlib
import subprocess
import sys
import tempfile

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mesh_lint as ML  # noqa: E402
import retopo  # noqa: E402
import sdf_body  # noqa: E402
import silhouette as SIL  # noqa: E402

ROOT = HERE.parent.parent / "artifacts/model-sheets"
UNITS = ("n005", "n00U", "hfoo", "n017", "n02X")
MASK_PX = 512
Z = np.array([0.0, 0.0, 1.0])

REMESH_DEV = 0.012       # the remesh rows: collapses / relaxations may not leave a triangle's centroid farther than this share of H

# row -> reduce() keywords besides sdf / polish (None: the row is not a reduce() call)
ROWS = {
    "QEM": dict(features_deg=None, min_angle=0, project=False),
    "QEM + guard": dict(features_deg=None, project=False),
    "QEM + guard + proj": dict(features_deg=None, project=True),
    "QEM + guard + proj + dev": dict(features_deg=None, project=True, dev=True),
    "QEM + guard + proj + features": dict(features_deg=35, project=True),
    # PIPELINE 28.L10-4: isotropic remeshing (retopo.remesh), alone / + a short QEM to close the budget / with feature lines
    "remesh": dict(method="remesh", project=True, dev=REMESH_DEV),
    "remesh + QEM": dict(method="hybrid", project=True, dev=REMESH_DEV),
    "remesh + features": dict(method="remesh", project=True, dev=REMESH_DEV, features=35),
    "QEM -> remesh (guided)": dict(method="guided", project=True, dev=REMESH_DEV),
    # PIPELINE 29.L11-6: curvature-guided Voronoi / CVT (retopo.cvt); cvt keywords besides method / project / dev go straight to cvt()
    "cvt": dict(method="cvt", project=True, dev=True),
    "cvt qef": dict(method="cvt", project=True, dev=True, place="qef"),
}
FINAL = ("QEM + guard + proj + dev", "remesh", "remesh + QEM", "remesh + features", "QEM -> remesh (guided)")   # --l10-4: the rows of the 28.L10-4 table
DEV_FRAC = 0.02          # the deviation guard: a collapse may not leave a triangle's centroid farther than this share of H


# ---------------------------------------------------------------- metrics
def height_of(f):
    return float(max(p["hi"][2] for p in f.parts) - min(p["lo"][2] for p in f.parts))


def flipped(f, v, t):
    """Faces whose normal points against the SDF gradient at the centroid (central differences of the exact field)."""
    c = v[t].mean(1)
    h = 0.25 * f.voxel
    g = np.stack([f.d(c + h * e) - f.d(c - h * e) for e in np.eye(3)], 1)
    n = np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]])
    return int((np.einsum("fd,fd->f", n, g) < 0).sum())


def deviation(f, v, t):
    """|d| of the vertices, edge midpoints and centroids of the mesh: (mean, p95, max) in % of H, and the max in voxels."""
    p = v[t]
    pts = np.vstack([v, p.mean(1), (p[:, 0] + p[:, 1]) / 2, (p[:, 1] + p[:, 2]) / 2, (p[:, 2] + p[:, 0]) / 2])
    d, H = np.abs(f.d(pts)), height_of(f)
    return (round(float(d.mean() / H * 100), 3), round(float(np.percentile(d, 95) / H * 100), 3),
            round(float(d.max() / H * 100), 3), round(float(d.max() / f.voxel), 2))


def form(f, v, t):
    p = v[t]
    nd = ML.normal_diff(v, t)
    bnd, nm, comp = ML.topology(v, t)
    mean, p95, top, vox = deviation(f, v, t)
    return {"tris": len(t), "sliver_pct": round(100 * float((ML.angles_min(p) < ML.SLIVER_DEG).mean()), 1),
            "nd": round(float(nd.mean()), 1), "band60_100": round(100 * float(((nd >= 60) & (nd <= 100)).mean()), 1),
            "fairness": round(float(np.abs(ML.angles(p) - 60).mean()), 1), "flipped": flipped(f, v, t), "boundary": bnd,
            "nonmanifold": nm, "components": comp, "euler": retopo.euler(len(np.unique(t)), len(t)),
            "dev_mean_H": mean, "dev_p95_H": p95, "dev_max_H": top, "dev_max_vox": vox}


# ---------------------------------------------------------------- silhouettes
def look(view, tilt):
    """(forward, up) of an orthographic review camera (views.py), Blender axes."""
    t = np.radians(tilt if isinstance(tilt, (int, float)) else 0)
    if view == "top":
        return np.array([0, np.sin(t), -np.cos(t)]), np.array([0, np.cos(t), np.sin(t)])
    if view == "bottom":
        return np.array([0, np.sin(t), np.cos(t)]), np.array([0, -np.cos(t), np.sin(t)])
    if view == "rts":
        e, a = np.radians(tilt[0]), np.radians(tilt[1])
        f = -np.array([np.cos(e) * np.sin(a), -np.cos(e) * np.cos(a), np.sin(e)])
        right = np.cross(f, Z) / np.linalg.norm(np.cross(f, Z))
        return f, np.cross(right, f)
    forward = {"front": (0, 1, 0), "left": (1, 0, 0), "back": (0, -1, 0)}[view]
    return np.array(forward, float), Z


def silhouette(v, t, view, tilt=0):
    """Boolean mask (MASK_PX high at most) of the mesh seen from one review camera, front of the page at the bottom."""
    from PIL import Image, ImageDraw
    f, up = look(view, tilt)
    right = np.cross(f, up)
    xy = np.stack([v @ right, -(v @ up)], 1)
    xy = (xy - xy.min(0)) * ((MASK_PX - 2) / np.ptp(xy, axis=0).max()) + 1
    size = tuple(int(np.ceil(s)) + 2 for s in xy.max(0))
    img = Image.new("L", size, 0)
    draw = ImageDraw.Draw(img)
    for tri in xy[t]:
        draw.polygon([tuple(p) for p in tri], fill=1)
    return np.asarray(img, bool)


def run_cameras(unit):
    """{view: tilt} of the cameras the run's silhouette.json matched (top / bottom tilt, rts (elevation, azimuth))."""
    tilt = json.loads((ROOT / f"runs/draft/{unit}/v12-r1/silhouette.json").read_text()).get("tilt", {})
    return {"front": 0, "left": 0, "back": 0, "top": tilt.get("top", 0), "bottom": tilt.get("bottom", 0),
            "rts": tuple(tilt["rts"]) if tilt.get("rts") else (45, 45)}


def sheet_panels(unit):
    """{view: normalized concept mask} of refs/<unit>/sheet.jpg (+ its gameplay view)."""
    sheet = ROOT / f"refs/{unit}/sheet.jpg"
    panels = {k: SIL.normalize(m) for k, m in SIL.concept_panels(sheet).items()}
    if SIL.rts_path(sheet).exists():
        panels["rts"] = SIL.normalize(SIL.foreground(SIL.rts_path(sheet), 768))
    return panels


def view_iou(panels, cams, v, t):
    """{view: IoU} of the mesh against the sheet panels: best of the mirror (and, top / bottom, the page turned 180)."""
    out = {}
    for view, panel in panels.items():
        mask = SIL.normalize(silhouette(v, t, view, cams[view]))
        turned = [panel, np.rot90(panel, 2)] if view in ("top", "bottom") else [panel]
        out[view] = round(max(SIL.iou(p, m) for p in turned for m in SIL.variants(mask, view)), 4)
    return out


# ---------------------------------------------------------------- clay contact sheet
VIEWS = (("front", 0), ("left", 0), ("rts", (35, 45)))
CELL = 360


def clay(v, t, view, tilt):
    """PIL image (CELL x CELL) of the mesh, flat-shaded clay with dark edges, painter's order, from one review camera."""
    from PIL import Image, ImageDraw
    f, up = look(view, tilt)
    right = np.cross(f, up)
    xy = np.stack([v @ right, -(v @ up)], 1)
    xy = (xy - (xy.min(0) + xy.max(0)) / 2) * ((CELL - 16) / np.ptp(xy, axis=0).max()) + CELL / 2
    n = np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]])
    n /= np.maximum(np.linalg.norm(n, axis=1), 1e-300)[:, None]
    light = -f + 0.6 * up + 0.4 * right
    shade = np.clip(n @ light / np.linalg.norm(light), 0, 1) * 0.65 + 0.3
    img = Image.new("RGB", (CELL, CELL), (236, 236, 232))
    draw = ImageDraw.Draw(img)
    facing = n @ f < 0
    for i in np.argsort(v[t].mean(1) @ f)[::-1]:
        if facing[i]:
            g = int(255 * shade[i])
            draw.polygon([tuple(p) for p in xy[t[i]]], fill=(g, g, int(g * 0.96)), outline=(70, 70, 70))
    return img


def contact_sheet(meshes, path):
    """PNG: one row per (name, (verts, tris)), one column per review view (front, left, rts)."""
    from PIL import Image, ImageDraw
    sheet = Image.new("RGB", (CELL * len(VIEWS), CELL * len(meshes)), (255, 255, 255))
    for r, (name, (v, t)) in enumerate(meshes.items()):
        for c, (view, tilt) in enumerate(VIEWS):
            sheet.paste(clay(v, t, view, tilt), (c * CELL, r * CELL))
        ImageDraw.Draw(sheet).text((6, r * CELL + 4), f"{name} ({len(t)} tris)", fill=(0, 0, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


# ---------------------------------------------------------------- rows
def union_mesh(f, unit, name="clay.glb"):
    """(verts, tris) of a v12 GLB in Blender axes, the prop components dropped (their vertices sit far from the body's field)."""
    doc, blob = ML.read_glb(ROOT / f"runs/draft/{unit}/v12-r1/{name}")
    pos, _, _, tri = ML.geometry(doc, blob)
    v = np.stack([pos[:, 0], -pos[:, 2], pos[:, 1]], 1)
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    n = len(v)
    graph = coo_matrix((np.ones(3 * len(tri)), (tri.ravel(), np.roll(tri, 1, 1).ravel())), shape=(n, n))
    label = connected_components(graph, directed=False)[1]
    d = np.abs(f.d(v))
    keep = np.array([np.median(d[label == c]) < 2 * f.voxel for c in range(label.max() + 1)])[label[tri[:, 0]]]
    used = np.unique(tri[keep])
    remap = np.full(n, -1)
    remap[used] = np.arange(len(used))
    return v[used], remap[tri[keep]]


def collapse_row(src, target):
    out = pathlib.Path(tempfile.mkdtemp()) / "c.npz"
    subprocess.run(["blender", "-b", "-P", str(HERE / "retopo_blender.py"), "--", "collapse", str(src), str(out), str(target)],
                   check=True, capture_output=True)
    z = np.load(out)
    return z["verts"], z["tris"], float(z["seconds"])


def reduce_row(f, z, target, spec):
    sdf = retopo.grid_sdf(f.grid, f.origin, f.voxel) if spec["project"] else None
    kw = {k: v for k, v in spec.items() if k not in ("project", "dev", "method", "features_deg", "features")}
    feat = spec.get("features") or spec.get("features_deg")
    if spec.get("dev"):
        kw["max_dev"] = (DEV_FRAC if spec["dev"] is True else spec["dev"]) * height_of(f)
    if spec.get("method"):
        v, t, rep = retopo.retopo(z["verts"], z["tris"], target, sdf=sdf, polish=f.d if sdf else None, grad_h=0.5 * f.voxel,
                                  method=spec["method"], features=feat, **kw)
    else:
        v, t, rep = retopo.reduce(z["verts"], z["tris"], target, sdf=sdf, polish=f.d if sdf else None, grad_h=0.5 * f.voxel, features_deg=feat, **kw)
    return v, t, rep["seconds"], rep


def unit_rows(unit, folder, src, target, blender=True, only=None, render=None):
    f = sdf_body.load(folder / f"{unit}.sdf.json").compute()
    z = np.load(folder / f"{unit}-{src}.npz")
    panels, cams = sheet_panels(unit), run_cameras(unit)
    rows = {"dense": (z["verts"], z["tris"], 0.0, {}), "union": (*union_mesh(f, unit), 0.0, {}),
            "union raw": (*union_mesh(f, unit, "clay-raw.glb"), 0.0, {})}
    if blender:
        rows["COLLAPSE (blind)"] = (*collapse_row(folder / f"{unit}-{src}.npz", target), {})
    for name, spec in ROWS.items():
        if only is None or name in only:
            rows[name] = reduce_row(f, z, target, spec)
    if render:
        shown = [k for k in rows if k in FINAL]
        contact_sheet({k: rows[k][:2] for k in (shown[0], "remesh")}, render / f"{unit}.png")
    table = {}
    for name, (v, t, seconds, rep) in rows.items():
        table[name] = {**form(f, v, t), "iou": view_iou(panels, cams, v, t), "seconds": round(seconds, 2),
                       "stages": rep.get("stages")}
    return table


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder", type=pathlib.Path)
    ap.add_argument("--src", default="a0", choices=("a0", "a5"))
    ap.add_argument("--target", type=int, default=600)
    ap.add_argument("--units", default=",".join(UNITS))
    ap.add_argument("--no-blender", action="store_true")
    ap.add_argument("--l10-4", action="store_true", help="only the rows of the 28.L10-4 table (QEM final, remesh, remesh + QEM, remesh + features)")
    ap.add_argument("--rows", help="comma list of ROWS names to run (default all; --l10-4 wins)")
    ap.add_argument("--json", type=pathlib.Path)
    ap.add_argument("--render", type=pathlib.Path, help="folder for <unit>.png: clay of the first two rows of the table, 3 views")
    a = ap.parse_args()
    out = {}
    for unit in a.units.split(","):
        out[unit] = unit_rows(unit, a.folder, a.src, a.target, not (a.no_blender or a.l10_4 or a.rows), FINAL if a.l10_4 else (a.rows.split(",") if a.rows else None), a.render)
        print(unit, flush=True)
        for name, m in out[unit].items():
            print(f"  {name:32} {m['tris']:>6} sl {m['sliver_pct']:>5} nd {m['nd']:>5} b {m['band60_100']:>5} fair {m['fairness']:>5} "
                  f"fl {m['flipped']} bnd {m['boundary']} nm {m['nonmanifold']} eul {m['euler']} dev {m['dev_mean_H']}/{m['dev_p95_H']}/"
                  f"{m['dev_max_H']} ({m['dev_max_vox']} vox) iou {m['iou']} {m['seconds']} s", flush=True)
    if a.json:
        a.json.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
