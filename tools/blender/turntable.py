#!/usr/bin/env python3
"""Matcap turntable of one unit GLB, as an H.264 mp4 (convert to GIF with ffmpeg).

    blender -b -P tools/blender/turntable.py -- <unit.glb> <out.mp4>

Uses bx_review.turntable from the blender-expert skill. The importer leaves the model
Y-up and adds an unlinked "Icosphere" bone-shape helper, so the orientation is fixed
here and only scene objects are measured.
"""
import math
import pathlib
import sys

import bpy
import mathutils

SKILLS = pathlib.Path.home() / ".config" / "opencode" / "skills"
sys.path.append(str(SKILLS / "blender-expert" / "scripts"))
import bx_review  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from views import rest_pose  # noqa: E402


def extent():
    lo, hi = mathutils.Vector((1e9,) * 3), mathutils.Vector((-1e9,) * 3)
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            p = obj.matrix_world @ mathutils.Vector(corner)
            lo, hi = mathutils.Vector(map(min, lo, p)), mathutils.Vector(map(max, hi, p))
    return lo, hi


def main():
    glb, out = sys.argv[sys.argv.index("--") + 1:][:2]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    rest_pose()                     # the importer leaves the rig on clip frame 1
    lo, hi = extent()
    if (hi - lo).y > (hi - lo).z * 1.5:  # came in Y-up
        for obj in [o for o in bpy.context.scene.objects if o.parent is None]:
            obj.rotation_euler.x += math.radians(90)
        bpy.context.view_layer.update()
    mesh = next(o for o in bpy.context.scene.objects if o.type == "MESH")
    print("turntable:", bx_review.turntable(mesh, out, frames=36, res=512, mode="matcap"))


if __name__ == "__main__":
    main()
