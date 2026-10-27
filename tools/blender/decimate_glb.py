#!/usr/bin/env python3
"""Decimate every mesh of a GLB by a ratio (collapse), rest pose, no clips: the input of
`mesh_lint.py --decimate` (PIPELINE §20.M10).

    blender -b -P tools/blender/decimate_glb.py -- <in.glb> <out.glb> [ratio=0.5]
"""
import pathlib
import sys

import bpy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from views import rest_pose  # noqa: E402


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    src, dst = args[0], args[1]
    ratio = float(args[2]) if len(args) > 2 else 0.5
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)
    rest_pose()
    for obj in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
        bpy.context.view_layer.objects.active = obj
        mod = obj.modifiers.new("decimate", "DECIMATE")
        mod.ratio = ratio
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB", export_animations=False, export_skins=False)


main()
