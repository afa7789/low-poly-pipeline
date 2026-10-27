#!/usr/bin/env python3
"""Clay with its triangle edges drawn on top, for the review sheet's `wire` column.

    blender -b -P tools/blender/render_wire.py -- <unit.glb> <outdir> [tilt=top:20,rts:45/30]

Writes <outdir>/wire-<view>.png for every view in views.VIEWS plus `rts`, from the same cameras
as render_unit.py. Workbench, flat light, no background. The edges are a thin Wireframe
modifier on a triangulated copy of each mesh (a copy, so the clay under it stays solid and
hides the far side); Freestyle would draw only crease/border edges, not the triangulation
the GLB really has, which is what the column is for.
"""
import math
import pathlib
import sys

import bpy
import mathutils

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from views import RTS_DEFAULT, VIEWS, camera, parse_tilts, rest_pose, rts_offset  # noqa: E402

D = math.radians
CLAY, EDGE = (0.62, 0.62, 0.62, 1.0), (0.05, 0.05, 0.05, 1.0)


def material(name, colour):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = colour
    return mat


def bounds():
    lo, hi = mathutils.Vector((1e9,) * 3), mathutils.Vector((-1e9,) * 3)
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            p = obj.matrix_world @ mathutils.Vector(corner)
            lo, hi = mathutils.Vector(map(min, lo, p)), mathutils.Vector(map(max, hi, p))
    return (lo + hi) / 2, (hi - lo)


def add_edges(clay, edge, thickness):
    """One edge-only copy per mesh object, over the same pose as the original."""
    for src in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
        src.data.materials.clear()
        src.data.materials.append(clay)
        copy = src.copy()
        copy.data = src.data.copy()
        copy.data.materials.clear()
        copy.data.materials.append(edge)
        for mod in list(copy.modifiers):
            if mod.type != "ARMATURE":
                copy.modifiers.remove(mod)
        copy.modifiers.new("tri", "TRIANGULATE")
        wire = copy.modifiers.new("wire", "WIREFRAME")
        wire.thickness, wire.offset, wire.use_replace = thickness, 1.0, True
        bpy.context.collection.objects.link(copy)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    glb, outdir = argv[:2]
    tilts = parse_tilts(next((a[5:] for a in argv[2:] if a.startswith("tilt=")), ""))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    rest_pose()
    for o in [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name.startswith("Icosphere")]:
        bpy.data.objects.remove(o, do_unlink=True)
    _, ext = bounds()
    if ext.y > ext.z * 1.5:                     # glTF import is Y-up
        for obj in [o for o in bpy.context.scene.objects if o.parent is None]:
            obj.rotation_euler.x += math.radians(90)
        bpy.context.view_layer.update()
    centre, extent = bounds()
    add_edges(material("clay", CLAY), material("edge", EDGE), 0.004 * max(extent))

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    scene.world = bpy.data.worlds.new("w")
    scene.world.color = (0.8, 0.8, 0.8)
    sh = scene.display.shading
    sh.light, sh.color_type = "FLAT", "MATERIAL"
    sh.show_object_outline = sh.show_shadows = sh.show_cavity = False
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max(extent) * 1.25
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    out = pathlib.Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    def shoot(name):
        scene.render.filepath = str(out / f"wire-{name}.png")
        bpy.ops.render.render(write_still=True)

    for name in VIEWS:
        offset, rot = camera(name, tilts.get(name, 0))
        cam.location = centre + mathutils.Vector(offset)
        cam.rotation_euler = tuple(D(r) for r in rot)
        shoot(name)
    cam.location = centre + mathutils.Vector(rts_offset(*tilts.get("rts", RTS_DEFAULT)))
    cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
    shoot("rts")
    print("wire ->", out)


if __name__ == "__main__":
    main()
