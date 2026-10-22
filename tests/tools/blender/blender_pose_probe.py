"""Run inside Blender: pose each family's armature and print the pose bones' world
heads/tails, for test_rig_poses.test_matches_blender_pose_bones.

    blender -b --python tests/tools/blender/blender_pose_probe.py -- "<repr of {family: {bone: (rx, ry, rz, lift)}}>"
"""
import ast
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import bpy  # noqa: E402

import build_unit as BU  # noqa: E402


def probe(family, pose):
    BU.wipe()
    BU.load_family(family)
    arm = BU.build_armature()
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    for pb in arm.pose.bones:
        rx, ry, rz, lift = pose[pb.name]
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
        pb.location = (0, 0, lift)
    bpy.context.view_layer.update()
    out = {pb.name: (tuple(pb.head), tuple(pb.tail)) for pb in arm.pose.bones}
    bpy.ops.object.mode_set(mode="OBJECT")
    return out


poses = ast.literal_eval(sys.argv[sys.argv.index("--") + 1])
print("POSE_PROBE " + repr({fam: probe(fam, pose) for fam, pose in poses.items()}))
