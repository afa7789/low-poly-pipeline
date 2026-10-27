"""Hidden-face cull and screen-tolerance decimate for build_unit.py (runs inside Blender).

M8 - which faces does any camera ever see? An ID render in 12 orthographic views: one ray per
pixel, the face it hits is "seen" (the same answer as a flat colour-per-face render, minus the
render engine). Faces never seen are interior or buried under another plate; they cost tris and
atlas texels for nothing. `cull` reports visible/total always; removal is opt-in (`cull=remove`).

M12 - the `union` branch decimates blindly to budget//2 faces. `decimate_union(blind=False)` (build_unit
argument `toldec`) collapses as far as the surface stays within d of the pre-decimate mesh (BVH nearest
point of the vertices and triangle centroids of the result), d = height / 32. Measured: opt-in only.
"""
import json
import math
import pathlib

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

# azimuth, elevation (deg): 4 sides level, 4 sides from above, the poles, 2 low diagonals
VIEWS = [(a, 0) for a in (0, 90, 180, 270)] + [(a, 45) for a in (0, 90, 180, 270)] \
    + [(0, 90), (0, -90), (0, -45), (180, -45)]
RES = 192


def direction(az, el):
    a, e = math.radians(az), math.radians(el)
    return Vector((math.cos(e) * math.sin(a), -math.cos(e) * math.cos(a), math.sin(e)))


def basis(d):
    up = Vector((0, 1, 0)) if abs(d.z) > 0.99 else Vector((0, 0, 1))
    u = d.cross(up).normalized()
    return u, d.cross(u).normalized()


def bm_of(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    return bm


def seen_faces(obj, res=RES):
    """Set of polygon indices some view hits, plus the rays shot."""
    bm = bm_of(obj)
    tree = BVHTree.FromBMesh(bm)
    pts = [v.co for v in bm.verts]
    centre = sum(pts, Vector()) / len(pts)
    radius = max((p - centre).length for p in pts) + 0.1
    seen, rays = set(), 0
    for az, el in VIEWS:
        d = direction(az, el)
        u, v = basis(d)
        lo_u = min((p - centre).dot(u) for p in pts)
        hi_u = max((p - centre).dot(u) for p in pts)
        lo_v = min((p - centre).dot(v) for p in pts)
        hi_v = max((p - centre).dot(v) for p in pts)
        step = max(hi_u - lo_u, hi_v - lo_v) / res
        origin = centre - d * radius
        for i in range(int((hi_u - lo_u) / step) + 1):
            for j in range(int((hi_v - lo_v) / step) + 1):
                o = origin + u * (lo_u + (i + 0.5) * step) + v * (lo_v + (j + 0.5) * step)
                hit = tree.ray_cast(o, d)
                rays += 1
                if hit[2] is not None:
                    seen.add(hit[2])
    bm.free()
    return seen, rays


def tri_count(mesh, keep=None):
    return sum(len(p.vertices) - 2 for p in mesh.polygons if keep is None or p.index in keep)


def measure(obj, seen):
    mesh = obj.data
    return {"visible_tris": tri_count(mesh, seen), "total_tris": tri_count(mesh),
            "visible_faces": len(seen), "total_faces": len(mesh.polygons),
            "views": len(VIEWS), "res": RES}


def remove_hidden(obj, seen):
    """Delete the faces not in `seen` and the vertices left loose. Vertex groups ride on the
    vertices that stay; UVs are made after this call (atlas_uvs reads the surviving faces)."""
    bm = bm_of(obj)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in seen], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def cull(obj, out, remove=False):
    """Measure (always) and remove (opt-in) the never-seen faces; the numbers go to
    `cull.json` beside the GLB for spec_pipeline's review."""
    seen, rays = seen_faces(obj)
    stats = measure(obj, seen)
    stats["rays"] = rays
    stats["removed"] = bool(remove)
    if remove:
        remove_hidden(obj, seen)
        stats["tris_after"] = tri_count(obj.data)
    (pathlib.Path(out).parent / "cull.json").write_text(json.dumps(stats))
    print(f"cull: {stats['visible_tris']}/{stats['total_tris']} tris visible in {len(VIEWS)} views"
          + (f", removed -> {stats['tris_after']} tris" if remove else ""))
    return stats


# ---------------------------------------------------------------- M12

def height_of(obj):
    zs = [v.co.z for v in obj.data.vertices]
    return max(zs) - min(zs)


def deviation(tree, mesh):
    """Largest distance from the vertices and triangle centroids of `mesh` to the BVH `tree`
    (not polygon centres: the centre of a concave n-gon sits off its own surface)."""
    mesh.calc_loop_triangles()
    pts = [v.co for v in mesh.vertices] + [
        sum((mesh.vertices[i].co for i in t.vertices), Vector()) / 3 for t in mesh.loop_triangles]
    return max(tree.find_nearest(p)[3] for p in pts)


def collapsed_copy(obj, ratio):
    """A throw-away COLLAPSE-decimated copy of `obj` at `ratio`."""
    copy = obj.copy()
    copy.data = obj.data.copy()
    bpy.context.collection.objects.link(copy)
    mod = copy.modifiers.new("Dec", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = ratio
    bpy.context.view_layer.objects.active = copy
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return copy


def drop(copy):
    mesh = copy.data
    bpy.data.objects.remove(copy, do_unlink=True)
    bpy.data.meshes.remove(mesh)


def tolerance_ratio(obj, tree, tol, steps=8):
    """Smallest COLLAPSE ratio whose result stays within `tol` of `tree` (bisection):
    (ratio, deviation, faces)."""
    lo, hi = 0.02, 1.0           # hi = no collapse, always inside tol
    best = (1.0, 0.0, len(obj.data.polygons))
    for _ in range(steps):
        mid = (lo + hi) / 2
        copy = collapsed_copy(obj, mid)
        dev, faces = deviation(tree, copy.data), len(copy.data.polygons)
        drop(copy)
        if dev <= tol:
            best, hi = (mid, dev, faces), mid
        else:
            lo = mid
    return best


def decimate_union(obj, budget_faces, tol=None, blind=True, floor=0):
    """Decimate the unioned shell. blind (default, the pre-M12 behaviour): COLLAPSE to the face
    budget. Else: as far as it stays within `tol` (default height/32) of its own pre-decimate
    surface; over the budget at that point -> the budget wins; under `floor` faces -> stop at the
    floor (a tolerance that is loose on a smooth shell would eat the silhouette's detail).
    Either way the deviation of the result is measured. Returns {ratio, dev, tol, faces_before, faces_at_tol, faces, budget_bound}."""
    tol = tol or height_of(obj) / 32.0
    n0 = len(obj.data.polygons)
    bm = bm_of(obj)
    tree = BVHTree.FromBMesh(bm)
    ratio, dev, at_tol = (1.0, 0.0, n0) if blind else tolerance_ratio(obj, tree, tol)
    bound = blind or at_tol > budget_faces
    if bound and n0 > budget_faces:
        ratio = max(0.02, budget_faces / float(n0))
    elif floor and n0 * ratio < floor:
        ratio = min(1.0, floor / float(n0))
    if ratio < 1.0:
        mod = obj.modifiers.new("Dec", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = ratio
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        dev = deviation(tree, obj.data)
    bm.free()
    return {"ratio": round(ratio, 3), "dev": round(dev, 4), "tol": round(tol, 4), "faces_before": n0,
            "faces_at_tol": None if blind else at_tol, "faces": len(obj.data.polygons), "budget_bound": bound}
