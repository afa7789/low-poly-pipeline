#!/usr/bin/env python3
"""Render a 5-view turnaround of one exported unit GLB, plus one walk frame.

    blender -b -P tools/blender/render_unit.py -- <unit.glb> <outdir>

Workbench engine, flat lighting, material colours, orthographic cameras square on
to each axis and a #CCCCCC world, so the frames line up with the AI sheets.
Frames land in <outdir> as <stem>-front.png, -left, -back, -top, -bottom, -walkleft.
"""
import math
import pathlib
import sys

import bpy
import mathutils

D = math.radians
# name, camera offset from the model centre, camera rotation (deg)
VIEWS = [
    ("front", (0, -8, 0), (90, 0, 0)),
    ("left", (-8, 0, 0), (90, 0, -90)),
    ("back", (0, 8, 0), (90, 0, 180)),
    ("top", (0, 0, 8), (0, 0, 0)),
    ("bottom", (0, 0, -8), (180, 0, 0)),
]


def setup_scene():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.film_transparent = False
    shading = scene.display.shading
    shading.light = "FLAT"
    shading.color_type = "MATERIAL"
    shading.show_object_outline = True
    shading.object_outline_color = (0.05, 0.05, 0.05)
    scene.display.render_aa = "8"
    scene.world = bpy.data.worlds.new("sheet")
    scene.world.color = (0.8, 0.8, 0.8)
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    return scene, cam


def bounds():
    """World-space centre and extent of the imported body, so every view frames it."""
    lo, hi = mathutils.Vector((1e9,) * 3), mathutils.Vector((-1e9,) * 3)
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            p = obj.matrix_world @ mathutils.Vector(corner)
            lo, hi = mathutils.Vector(map(min, lo, p)), mathutils.Vector(map(max, hi, p))
    return (lo + hi) / 2, (hi - lo)


def fix_orientation():
    """The imported glTF comes in Y-up; the ortho cameras below assume Z-up."""
    _, ext = bounds()
    if ext.y > ext.z * 1.5:
        for obj in [o for o in bpy.context.scene.objects if o.parent is None]:
            obj.rotation_euler.x += math.radians(90)
        bpy.context.view_layer.update()


def main():
    glb, outdir = sys.argv[sys.argv.index("--") + 1:][:2]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    scene, cam = setup_scene()
    fix_orientation()
    centre, extent = bounds()
    out = pathlib.Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    stem = pathlib.Path(glb).stem

    def shoot(name):
        scene.render.filepath = str(out / f"{stem}-{name}.png")
        bpy.ops.render.render(write_still=True)

    def frame(name, offset, rot):
        cam.location = centre + mathutils.Vector(offset)
        cam.rotation_euler = (D(rot[0]), D(rot[1]), D(rot[2]))
        span = extent.z if name in ("front", "left", "back", "walkleft") else max(extent.x, extent.y)
        cam.data.ortho_scale = max(span, extent.x, extent.y) * 1.25
        shoot(name)

    for name, offset, rot in VIEWS:
        frame(name, offset, rot)

    # rig proof: the walk action, mid-stride, from the left
    arm = next((o for o in bpy.context.scene.objects if o.type == "ARMATURE"), None)
    walk = next((a for a in bpy.data.actions if "walk" in a.name.lower()), None)
    if arm and walk:
        arm.animation_data_create()
        arm.animation_data.action = walk
        scene.frame_set(16)
        frame("walkleft", (-8, 0, 0), (90, 0, -90))
    print("rendered", stem, "->", out)


if __name__ == "__main__":
    main()
