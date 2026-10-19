"""Box modelling by cuts and extrusions: one connected cage, not a kit of primitives.

The torso is a single block; shoulders, arms, hips and legs are extruded out of it and
then cut back, which is how PS1/WC3 bodies were built. Every step is data, so a unit's
recipe is a list of operations, not a modelling session.
"""
import math

import bmesh
import bpy
from mathutils import Vector

D = math.radians


def _face(bm, axis, sign, min_co=None, max_co=None):
    """The face whose normal points along `axis`*`sign`, optionally filtered by centroid."""
    best, best_d = None, -2.0
    for f in bm.faces:
        d = f.normal[axis] * sign
        if d > best_d:
            c = f.calc_center_median()
            if min_co is not None and c[axis] * sign > min_co * sign:
                continue
            if max_co is not None and c[axis] * sign < max_co * sign:
                continue
            best, best_d = f, d
    return best


def _inset(bm, face, thickness):
    r = bmesh.ops.inset_individual(bm, faces=[face], thickness=thickness, depth=0.0)
    return r["faces"][0] if r.get("faces") else face


def _extrude(bm, face, offset, scale=1.0):
    r = bmesh.ops.extrude_discrete_faces(bm, faces=[face])
    new = r["faces"][0]
    c = new.calc_center_median()
    for v in new.verts:
        v.co = c + (v.co - c) * scale
        v.co += Vector(offset)
    bm.normal_update()
    return new


def build(recipe):
    """recipe: {size:(w,h,d), torso_cuts:[...], limbs:[{side, shoulder, upper, fore, fist}]}"""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    w, h, d = recipe["size"]
    bmesh.ops.scale(bm, vec=Vector((w, h, d)), verts=bm.verts)
    bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) < 1e-6],
                              cuts=1, use_grid_fill=True)
    bm.normal_update()

    # shoulders and arms out of the side faces
    for side in (1, -1):
        axis = 0
        face = _face(bm, axis, side)
        if face:
            f = _inset(bm, face, 0.18)
            f = _extrude(bm, f, (side * 0.10, 0, 0), 0.85)      # shoulder
            f = _extrude(bm, f, (0, -0.45, 0), 0.55)            # upper arm
            f = _extrude(bm, f, (0, -0.40, 0.02), 1.15)         # forearm
            f = _extrude(bm, f, (0, -0.28, 0.04), 1.30)         # fist

    # legs out of the bottom face, bisected at x = 0
    bottom = _face(bm, 1, -1)
    if bottom:
        geom = list(bottom.edges) + list(bottom.verts)
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0), plane_no=(1, 0, 0))
        bm.normal_update()
        for side in (1, -1):
            face = None
            for f in bm.faces:
                if f.normal.z < -0.9 and f.calc_center_median().x * side > 0:
                    face = f
            if not face:
                continue
            f = _inset(bm, face, 0.10)
            f = _extrude(bm, f, (0, -0.18, 0), 0.80)            # hip
            f = _extrude(bm, f, (0, -0.40, 0), 0.72)            # thigh
            f = _extrude(bm, f, (0, -0.36, 0), 0.85)            # shin
            f = _extrude(bm, f, (0, -0.16, 0.10), 1.25)         # boot

    # head out of the top face
    top = _face(bm, 2, 1)
    if top:
        f = _inset(bm, top, 0.22)
        _extrude(bm, f, (0, 0, 0.30), 0.55)

    me = bpy.data.meshes.new("boxmod")
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new("boxmod", me)
    bpy.context.collection.objects.link(obj)
    return obj
