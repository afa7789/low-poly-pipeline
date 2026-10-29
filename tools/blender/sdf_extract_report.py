#!/usr/bin/env python3
"""L10-2: merge mesh_lint (python3.14, on the GLBs) into the ablation.json files of sdf_extract.py; markdown table to stdout.

    python3.14 tools/blender/sdf_extract_report.py <scratch_dir> <runs_dir> [unit ...]

<scratch_dir>/<unit>/ablation.json is read; the union baseline is <runs_dir>/<unit>/v12-r1/clay.glb (sdf_dev measured here, on the
glTF vertices mapped back to Blender axes). Writes <scratch_dir>/<unit>/report.json.
"""
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mesh_lint as ML  # noqa: E402
import sdf_body as SB  # noqa: E402


def dev_of_glb(field, glb):
    doc, blob = ML.read_glb(glb)
    pos = ML.geometry(doc, blob)[0]
    pos = np.stack([pos[:, 0], -pos[:, 2], pos[:, 1]], 1)           # glTF Y-up -> Blender Z-up
    d = np.abs(field.d(pos)) / field.voxel
    return {"mean": round(float(d.mean()), 4), "p95": round(float(np.percentile(d, 95)), 4), "max": round(float(d.max()), 4)}


def lint_row(glb):
    m = ML.lint(glb)
    return {"tris": m["tris"], "sliver_pct": m["sliver_pct"], "nd_mean": m["normal_diff"]["mean"], "nd_p90": m["normal_diff"]["p90"],
            "flipped": m["flipped"], "boundary": m["boundary_edges"], "nonmanifold": m["nonmanifold_edges"],
            "components": m["components"]}


def unit_report(scratch, runs, unit):
    d = scratch / unit
    doc = json.loads((d / "ablation.json").read_text())
    spec = json.loads((runs / unit / "v12-r1/spec.json").read_text())
    cuts_p = runs / unit / "v12-r1/fit/cuts.json"
    cuts = json.loads(cuts_p.read_text()) if cuts_p.exists() else {}
    RF = SB.RF
    RF.scale_rig(spec.get("rig", "biped"), spec.get("rig_measure"))
    f = SB.field([tuple(r) for r in spec["parts"]], cuts, (spec.get("rig", "biped"), spec.get("bones") or ()), 1.0, 96, False)
    union = runs / unit / "v12-r1/clay.glb"
    rows = [{"config": "union-v12", "glb": str(union), **lint_row(union), "sdf_dev": dev_of_glb(f, union)}]
    for r in doc["rows"]:
        r.update({k: v for k, v in lint_row(d / r["glb"]).items() if k != "tris"})
        rows.append(r)
    (d / "report.json").write_text(json.dumps({"unit": unit, "rows": rows}, indent=1))
    return rows


def main():
    scratch, runs = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    units = sys.argv[3:] or ["n005", "n00U", "hfoo", "n017", "n02X"]
    print("| unit | config | tris | sliver % | nd mean | nd p90 | flip | border | non-man | comp | sdf_dev mean/p95/max (vox) | field s | extract s |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for u in units:
        for r in unit_report(scratch, runs, u):
            t = r.get("field_s", "")
            e = r.get("extract_s", r.get("remesh_s", ""))
            s = r["sdf_dev"]
            print(f"| {u} | {r['config']} | {r['tris']} | {r['sliver_pct']} | {r['nd_mean']} | {r['nd_p90']} | {r['flipped']} | "
                  f"{r['boundary']} | {r['nonmanifold']} | {r['components']} | {s['mean']}/{s['p95']}/{s['max']} | {t} | {e} |")


if __name__ == "__main__":
    main()
