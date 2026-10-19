#!/usr/bin/env python3
"""Render one animation of a unit GLB as a PNG sequence, for a GIF.

    blender -b -P tools/blender/render_anim.py -- <unit.glb> <outdir> <action> [frames] [size]

Three-quarter view, workbench engine, flat material colours on #CCCCCC.
Writes <outdir>/anim-000.png, anim-001.png, ... in order.
"""
import math
import pathlib
import sys

import bpy
import mathutils

D = math.radians


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    glb, outdir, action = args[0], args[1], args[2]
    frames = int(args[3]) if len(args) > 3 else 24
    size = int(args[4]) if len(args) > 4 else 256

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)

    # glTF comes in Y-up; stand it up like the ortho renderer does
    lo, hi = mathutils.Vector((1e9,) * 3), mathutils.Vector((-1e9,) * 3)
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            p = obj.matrix_world @ mathutils.Vector(corner)
            lo, hi = mathutils.Vector(map(min, lo, p)), mathutils.Vector(map(max, hi, p))
    if (hi - lo).y > (hi - lo).z * 1.5:
        for obj in [o for o in bpy.context.scene.objects if o.parent is None]:
            obj.rotation_euler.x += math.radians(90)
        bpy.context.view_layer.update()
        lo, hi = mathutils.Vector((1e9,) * 3), mathutils.Vector((-1e9,) * 3)
        for obj in bpy.context.scene.objects:
            if obj.type != "MESH":
                continue
            for corner in obj.bound_box:
                p = obj.matrix_world @ mathutils.Vector(corner)
                lo, hi = mathutils.Vector(map(min, lo, p)), mathutils.Vector(map(max, hi, p))
    centre, extent = (lo + hi) / 2, (hi - lo)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_object_outline = True
    scene.display.render_aa = "8"
    scene.world = bpy.data.worlds.new("sheet")
    scene.world.color = (0.8, 0.8, 0.8)

    target = bpy.data.objects.new("target", None)
    target.location = centre
    bpy.context.collection.objects.link(target)
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = 50
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)
    # 50mm lens on a 36mm sensor sees 0.72*d at distance d; keep 1.9*max(extent)
    # so the whole figure plus its ground line fits with margin.
    dist = max(extent) * 1.9
    direction = mathutils.Vector((-0.66, -0.66, 0.36)).normalized()
    cam.location = centre + direction * dist
    cam.constraints.new("TRACK_TO").target = target
    scene.camera = cam

    arm = next((o for o in bpy.context.scene.objects if o.type == "ARMATURE"), None)
    act = next((a for a in bpy.data.actions if action.lower() in a.name.lower()), None)
    if not arm or not act:
        sys.exit(f"no armature or no action matching {action}")
    arm.animation_data_create()
    arm.animation_data.action = act
    start, end = (int(v) for v in act.frame_range)
    span = max(end - start, 1)

    out = pathlib.Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    for i in range(frames):
        scene.frame_set(start + round(i * span / frames))
        scene.render.filepath = str(out / f"anim-{i:03d}.png")
        bpy.ops.render.render(write_still=True)
    print(f"rendered {frames} frames of '{act.name}' -> {out}")


if __name__ == "__main__":
    main()
