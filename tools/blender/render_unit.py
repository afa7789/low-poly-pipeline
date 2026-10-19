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
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16
    if scene.world is None:
        scene.world = bpy.data.worlds.new("world")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.62, 0.63, 0.65, 1.0)
    bg.inputs[1].default_value = 0.9
    for nm, rot, energy in (("key", (55, 0, -35), 3.2), ("fill", (70, 0, 140), 1.1)):
        li = bpy.data.lights.new(nm, "SUN")
        li.energy = energy
        li.angle = math.radians(25)
        ob = bpy.data.objects.new(nm, li)
        ob.rotation_euler = tuple(math.radians(v) for v in rot)
        bpy.context.collection.objects.link(ob)
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.film_transparent = False

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
    # the importer links a bone-shape helper called Icosphere; it is not part of the
    # model and its unit sphere drags the bounding box, so the camera framed empty air.
    for o in [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name.startswith("Icosphere")]:
        bpy.data.objects.remove(o, do_unlink=True)
    scene, cam = setup_scene()
    fix_orientation()
    centre, extent = bounds()
    print("BOUNDS extent", [round(v, 2) for v in extent], "centre", [round(v, 2) for v in centre])
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
