#!/usr/bin/env python3
"""Colour turntable of one unit GLB: workbench, material colours, flat light, orbiting camera.

    blender -b -P tools/blender/turntable_color.py -- <unit.glb> <out_dir> [frames] [size]

Writes <out_dir>/orbit-000.png ... The matcap turntable shows form only; this one shows the
palette, which is what decides whether a model reads as its faction.
"""
import math
import pathlib
import sys

import bpy
import mathutils

D = math.radians


def bounds():
    lo, hi = mathutils.Vector((1e9,) * 3), mathutils.Vector((-1e9,) * 3)
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            p = obj.matrix_world @ mathutils.Vector(corner)
            lo, hi = mathutils.Vector(map(min, lo, p)), mathutils.Vector(map(max, hi, p))
    return lo, hi


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    glb, outdir = args[0], args[1]
    frames = int(args[2]) if len(args) > 2 else 36
    size = int(args[3]) if len(args) > 3 else 384

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    lo, hi = bounds()
    if (hi - lo).y > (hi - lo).z * 1.5:  # import came in Y-up
        for obj in [o for o in bpy.context.scene.objects if o.parent is None]:
            obj.rotation_euler.x += math.radians(90)
        bpy.context.view_layer.update()
        lo, hi = bounds()
    centre, extent = (lo + hi) / 2, hi - lo

    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16
    sun = bpy.data.lights.new("key", "SUN")
    sun.energy = 3.2
    sun.angle = math.radians(25)
    sun_obj = bpy.data.objects.new("key", sun)
    sun_obj.rotation_euler = (math.radians(55), 0, math.radians(-35))
    bpy.context.collection.objects.link(sun_obj)
    fill = bpy.data.lights.new("fill", "SUN")
    fill.energy = 1.1
    fill_obj = bpy.data.objects.new("fill", fill)
    fill_obj.rotation_euler = (math.radians(70), 0, math.radians(140))
    bpy.context.collection.objects.link(fill_obj)
    if scene.world is None:
        scene.world = bpy.data.worlds.new("world")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.62, 0.63, 0.65, 1.0)
    bg.inputs[1].default_value = 0.9
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.display.shading.light = "STUDIO"
    has_tex = any(n.type == "TEX_IMAGE" for m in bpy.data.materials if m.use_nodes
                  for n in m.node_tree.nodes)
    scene.display.shading.color_type = "TEXTURE" if has_tex else "MATERIAL"
    scene.display.shading.show_object_outline = True
    scene.display.shading.object_outline_color = (0.06, 0.06, 0.06)
    scene.display.shading.studio_light = "rim.sl"
    scene.display.render_aa = "8"
    scene.world = bpy.data.worlds.new("sheet")
    scene.world.color = (0.8, 0.8, 0.8)

    target = bpy.data.objects.new("target", None)
    target.location = centre
    bpy.context.collection.objects.link(target)
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = max(extent) * 1.25
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    cam.constraints.new("TRACK_TO").target = target
    dist = max(extent) * 3.0

    out = pathlib.Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    for i in range(frames):
        a = 2 * math.pi * i / frames
        cam.location = centre + mathutils.Vector((math.sin(a) * dist, -math.cos(a) * dist, dist * 0.28))
        bpy.context.view_layer.update()
        scene.render.filepath = str(out / f"orbit-{i:03d}.png")
        bpy.ops.render.render(write_still=True)
    print(f"rendered {frames} orbit frames -> {out}")


if __name__ == "__main__":
    main()
