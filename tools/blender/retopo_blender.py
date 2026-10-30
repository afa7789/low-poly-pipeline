"""Blender side of the retopology ablation (PIPELINE 28.L10-3): dense test meshes and the blind COLLAPSE baseline.

    blender -b -P tools/blender/retopo_blender.py -- export <outdir> [grid]     # the 5 v12 units: SDF -> openvdb meshes
    blender -b -P tools/blender/retopo_blender.py -- collapse <in.npz> <out.npz> <target_faces>

export: sdf_body 96^3 of runs/draft/<unit>/v12-r1 (with fit/cuts.json when there is one), the field as <unit>.sdf.json and the
level set as <unit>-a0.npz / <unit>-a5.npz (openvdb convertToPolygons, adaptivity 0 / 0.5; verts in metres, tris).
collapse: Decimate modifier COLLAPSE (what cull.decimate_union does blind) down to target_faces; writes verts + tris.
"""
import json
import pathlib
import sys
import time

import bpy
import numpy as np
import openvdb as vdb

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rig_families as RF  # noqa: E402
import sdf_body  # noqa: E402

UNITS = ("n005", "n00U", "hfoo", "n017", "n02X")
RUNS = HERE.parent.parent / "artifacts/model-sheets/runs/draft"
ADAPT = {"a0": 0.0, "a5": 0.5}


def unit_field(unit, grid):
    run = RUNS / unit / "v12-r1"
    doc = json.loads((run / "spec.json").read_text())
    cuts = run / "fit/cuts.json"
    family, saved = doc.get("rig", "biped"), dict(RF.FAMILIES)
    try:
        RF.scale_rig(family, doc.get("rig_measure"))
        return sdf_body.field([tuple(r) for r in doc["parts"]], json.loads(cuts.read_text()) if cuts.exists() else {},
                              (family, doc.get("bones") or ()), 1.0, grid)
    finally:
        RF.FAMILIES.clear()
        RF.FAMILIES.update(saved)


def level_set(f, adaptivity):
    """(verts in metres, triangles) of the zero set of the Field's grid; quads split."""
    g = vdb.FloatGrid()
    g.copyFromArray(f.grid.astype(np.float32))
    v, tris, quads = g.convertToPolygons(0.0, adaptivity)
    tris, quads = np.asarray(tris, int).reshape(-1, 3), np.asarray(quads, int).reshape(-1, 4)
    return np.asarray(v, float) * f.voxel + f.origin, np.vstack([tris, quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]])


def export(out, grid):
    for unit in UNITS:
        t0 = time.perf_counter()
        f = unit_field(unit, grid)
        (out / f"{unit}.sdf.json").write_text(json.dumps(f.to_json()))
        for name, adaptivity in ADAPT.items():
            v, t = level_set(f, adaptivity)
            np.savez(out / f"{unit}-{name}.npz", verts=v, tris=t, voxel=f.voxel)
            print(unit, name, len(v), len(t), round(time.perf_counter() - t0, 2), flush=True)


def collapse(src, dst, target):
    z = np.load(src)
    mesh = bpy.data.meshes.new("m")
    mesh.from_pydata(z["verts"].tolist(), [], z["tris"].tolist())
    obj = bpy.data.objects.new("m", mesh)
    bpy.context.scene.collection.objects.link(obj)
    mod = obj.modifiers.new("Dec", "DECIMATE")
    mod.decimate_type, mod.ratio = "COLLAPSE", target / len(z["tris"])
    t0 = time.perf_counter()
    out = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    out.calc_loop_triangles()
    seconds = time.perf_counter() - t0
    v = np.array([p.co[:] for p in out.vertices])
    t = np.array([lt.vertices[:] for lt in out.loop_triangles])
    np.savez(dst, verts=v, tris=t, seconds=seconds)
    print("collapse", len(t), round(seconds, 3), flush=True)


def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    if a[0] == "export":
        export(pathlib.Path(a[1]), int(a[2]) if len(a) > 2 else sdf_body.GRID)
    else:
        collapse(a[1], a[2], int(a[3]))


if __name__ == "__main__":
    main()
