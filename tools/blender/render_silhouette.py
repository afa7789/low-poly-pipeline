#!/usr/bin/env python3
"""Render five orthographic silhouette frames of one GLB, RGBA with transparent film.

    blender -b -P tools/blender/render_silhouette.py -- <unit.glb> <outdir> [size]

Top and bottom are also rendered at every tilt in views.TILTS, as
<stem>-sil-top@<tilt>.png, and the gameplay camera at every views.RTS angle as
<stem>-sil-rts@<elev>_<azim>.png, so silhouette.py can find the concept's camera.

The silhouette is the only thing that survives at 32 px, so it gets its own render
pass: flat white geometry, no lights, no background. `silhouette.py` compares these
masks with the concept panels.
"""
import math
import pathlib
import sys

import bpy
import mathutils

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from views import RTS, TILTED, TILTS, VIEWS, camera, rest_pose, rts_offset  # noqa: E402

D = math.radians
ZONE_VIEWS = ("front", "left", "back")


def bounds():
    lo, hi = mathutils.Vector((1e9,) * 3), mathutils.Vector((-1e9,) * 3)
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            p = obj.matrix_world @ mathutils.Vector(corner)
            lo, hi = mathutils.Vector(map(min, lo, p)), mathutils.Vector(map(max, hi, p))
    return (lo + hi) / 2, (hi - lo)


def zones(scene, cam, centre, out, stem):
    """<stem>-zone-<view>.png: front/left/back in flat material colours, no light and no
    anti-aliasing (every pixel is one slot's colour), for silhouette.py's colour zones.
    Run after the silhouette shots: it changes the shading and leaves it changed."""
    scene.display.render_aa = "OFF"
    scene.view_settings.view_transform = "Standard"   # the default tone map darkens every colour
    scene.display.shading.color_type = "TEXTURE"
    for name in ZONE_VIEWS:
        offset, rot = camera(name)
        cam.location = centre + mathutils.Vector(offset)
        cam.rotation_euler = (D(rot[0]), D(rot[1]), D(rot[2]))
        scene.render.filepath = str(out / f"{stem}-zone-{name}.png")
        bpy.ops.render.render(write_still=True)
    scene.display.render_aa = "8"
    scene.display.shading.color_type = "SINGLE"


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    glb, outdir = args[0], args[1]
    size = int(args[2]) if len(args) > 2 else 512

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    rest_pose()                     # the importer leaves the rig on clip frame 1
    for o in [o for o in bpy.context.scene.objects
              if o.type == "MESH" and o.name.startswith("Icosphere")]:
        bpy.data.objects.remove(o, do_unlink=True)

    _, ext = bounds()
    if ext.y > ext.z * 1.5:  # glTF import is Y-up
        for obj in [o for o in bpy.context.scene.objects if o.parent is None]:
            obj.rotation_euler.x += math.radians(90)
        bpy.context.view_layer.update()
    centre, extent = bounds()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.film_transparent = True
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.display.render_aa = "8"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.single_color = (1.0, 1.0, 1.0)
    scene.display.shading.show_object_outline = False
    scene.display.shading.show_shadows = False
    scene.display.shading.show_cavity = False
    scene.display.shading.show_specular_highlight = False

    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    out = pathlib.Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    stem = pathlib.Path(glb).stem
    span = max(extent) * 1.15

    shots = [(name, 0, f"{stem}-sil-{name}.png") for name in VIEWS]
    shots += [(name, t, f"{stem}-sil-{name}@{t}.png") for name in TILTED for t in TILTS if t]
    for name, tilt, filename in shots:
        offset, rot = camera(name, tilt)
        cam.location = centre + mathutils.Vector(offset)
        cam.rotation_euler = (D(rot[0]), D(rot[1]), D(rot[2]))
        cam.data.ortho_scale = span
        scene.render.filepath = str(out / filename)
        bpy.ops.render.render(write_still=True)
    zones(scene, cam, centre, out, stem)
    for elev, azim in RTS:
        cam.location = centre + mathutils.Vector(rts_offset(elev, azim))
        cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(out / f"{stem}-sil-rts@{elev}_{azim}.png")
        bpy.ops.render.render(write_still=True)
    print("silhouettes ->", out)


if __name__ == "__main__":
    main()
