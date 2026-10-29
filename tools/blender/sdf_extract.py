#!/usr/bin/env python3
"""L10-2 ablation: the SDF body's mesh by openvdb (build_unit.sdf_mesh) against REMESH SHARP over the joined parts.

    blender -b -P tools/blender/sdf_extract.py -- <run_dir> <outdir> [grids=96,128] [adapt=0,0.5,0.9] [octree=6,7]

Reads <run_dir>/spec.json (+ fit/cuts.json when there). For each (grid, adaptivity) writes <outdir>/clay-sdfraw-g<G>-a<A>.glb, for
each octree depth clay-remesh-o<D>.glb (Remesh modifier, mode SHARP, over the body parts only joined, no SDF), and
<outdir>/ablation.json: seconds of the field and of the extraction, verts / tris, sdf_dev (|Field.d| at the vertices, in voxels:
mean / p95 / max; provisional, L10-6 formalizes it in mesh_lint) and the thin parts (thickness 2 r < 2 voxels at 96^3) with the
triangles each one owns. mesh_lint's numbers (python3.14, on the GLBs) are merged in by tools/blender/sdf_extract_report.py.
"""
import json
import pathlib
import sys
import time

import bpy
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_unit as BU  # noqa: E402
import rig_families as RF  # noqa: E402
import sdf_body as SB  # noqa: E402

THIN_VOX = 2.0      # a part thinner than this many voxels (2 x inradius) at 96^3 may vanish in the mesh


def arg(rest, name, default):
    return next((a[len(name) + 1:] for a in rest if a.startswith(name + "=")), default)


def export(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", export_yup=True, use_selection=True,
                              export_animations=False, export_skins=False, export_morph=False)


def world_verts(obj):
    return np.array([tuple(v.co) for v in obj.data.vertices], float).reshape(-1, 3)


def tri_centres(obj):
    pos = world_verts(obj)
    tri = np.array([tuple(p.vertices) for p in obj.data.polygons], int).reshape(-1, 3)
    return pos[tri].mean(1)


def sdf_dev(field, pos):
    """|d| of the body's field at the mesh vertices, in voxels: mean, p95, max."""
    d = np.abs(np.concatenate([field.d(pos[i:i + 4000]) for i in range(0, len(pos), 4000)])) / field.voxel
    return {"mean": round(float(d.mean()), 4), "p95": round(float(np.percentile(d, 95)), 4), "max": round(float(d.max()), 4)}


def thin_parts(field, centres):
    """Per part thinner than THIN_VOX voxels: kind, bone, thickness in voxels, triangles whose centre is nearest to it."""
    owner = field.ownership(centres)[0]
    out = []
    for n, p in enumerate(field.parts):
        thick = 2 * p["r"] / field.voxel
        if thick < THIN_VOX:
            out.append({"i": p["i"], "kind": p["kind"], "bone": p["bone"], "thick_vox": round(thick, 3),
                        "tris_owned": int((owner == n).sum())})
    return out


def row_of(obj, field, seconds, **extra):
    pos = world_verts(obj)
    return {"verts": len(pos), "tris": sum(len(p.vertices) - 2 for p in obj.data.polygons), **extra, **seconds,
            "sdf_dev": sdf_dev(field, pos)}


def body_parts(spec):
    """build_unit's parts of the spec (chamfers off, as in a union build) without the props and the flame slit."""
    parts = BU.build_spec_parts(spec, {})
    return [o for o, _ in parts if not (o.data.materials[0].name.split(".")[0] == "flame" or o.get("prop"))]


def remesh_column(spec, depths, outdir, field):
    rows = []
    for depth in depths:
        BU.wipe()
        BU._MAT_CACHE.clear()        # wipe() frees the materials the cache holds
        objs = body_parts(spec)
        t0 = time.perf_counter()
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.join()
        body = bpy.context.view_layer.objects.active
        mod = body.modifiers.new("remesh", "REMESH")
        mod.mode, mod.octree_depth, mod.use_remove_disconnected = "SHARP", depth, False
        mod.sharpness, mod.scale = 1.0, 0.99
        bpy.ops.object.modifier_apply(modifier=mod.name)
        seconds = time.perf_counter() - t0
        name = f"clay-remesh-o{depth}.glb"
        export(body, outdir / name)
        rows.append(row_of(body, field, {"remesh_s": round(seconds, 3)}, config=f"remesh-sharp-o{depth}", glb=name))
    return rows


def sdf_column(doc, cuts, grids, adapts, outdir):
    rows = []
    fam = doc.get("rig", "biped")
    for grid in grids:
        t0 = time.perf_counter()
        f = SB.field([tuple(r) for r in doc["parts"]], cuts, (fam, doc.get("bones") or ()), 1.0, grid, False)
        t_field = time.perf_counter() - t0
        for a in adapts:
            BU.wipe()
            t1 = time.perf_counter()
            obj = BU.sdf_mesh(f, a)
            seconds = {"field_s": round(t_field, 3), "extract_s": round(time.perf_counter() - t1, 3)}
            name = f"clay-sdfraw-g{grid}-a{a}.glb"
            export(obj, outdir / name)
            row = row_of(obj, f, seconds, config=f"sdf-g{grid}-a{a}", glb=name, voxel=round(f.voxel, 5))
            row["thin"] = thin_parts(f, tri_centres(obj))
            rows.append(row)
    return rows


def main():
    rest = sys.argv[sys.argv.index("--") + 1:]
    run, outdir = pathlib.Path(rest[0]), pathlib.Path(rest[1])
    outdir.mkdir(parents=True, exist_ok=True)
    grids = [int(v) for v in arg(rest, "grids", "96,128").split(",")]
    adapts = [float(v) for v in arg(rest, "adapt", "0,0.5,0.9").split(",")]
    depths = [int(v) for v in arg(rest, "octree", "6,7").split(",")]
    doc = json.loads((run / "spec.json").read_text())
    cuts_path = run / "fit" / "cuts.json"
    cuts = json.loads(cuts_path.read_text()) if cuts_path.exists() else {}
    BU.CLAY = True
    BU.CUTS.update(cuts)
    _, spec, _ = BU.load_spec(str(run / "spec.json"))
    RF.scale_rig(doc.get("rig", "biped"), doc.get("rig_measure"))
    rows = sdf_column(doc, cuts, grids, adapts, outdir)
    ref = SB.field([tuple(r) for r in doc["parts"]], cuts, (doc.get("rig", "biped"), doc.get("bones") or ()), 1.0, 96, False)
    rows += remesh_column(spec, depths, outdir, ref)
    (outdir / "ablation.json").write_text(json.dumps({"unit": run.parent.name, "rows": rows}, indent=1))
    print("sdf_extract:", run.parent.name, len(rows), "rows")


if __name__ == "__main__":
    main()
