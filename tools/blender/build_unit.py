#!/usr/bin/env python3
"""Build one rigged, animated low-poly unit for Castle Fight, headless.

    blender -b -P tools/blender/build_unit.py -- n01X artifacts/model-sheets/draft2/glb/n01X.glb

The engine contract (src/render/ModelManifest.hpp, tools/model_chart.cpp):
  * one skin, joints in skins[0] order, <=255 joints;
  * animations[] order IS the clip index used by data/models.tsv
    (clip_idle / clip_walk / clip_attack / clip_death), -1 = no clip;
  * the renderer scales the model so max(h, 0.8w, 0.8d) = UnitHeight*size*scale,
    so only proportions matter; yaw_deg fixes the facing (author facing +Y here,
    which Blender's glTF exporter turns into -Z, the raylib forward);
  * rig is rigid per part (one bone per mesh piece, weight 1): correct for
    machines, and it never produces the degenerate skins that automatic weights
    give on intersecting boxes.

Specs live in SPECS below: parts are boxes/cylinders in metres, each bound to one
bone, with a flat material. Bone name -> engine has no naming requirement.
"""
import math
import sys

import bpy
from mathutils import Vector

MATERIALS = {
    "iron": (0.259, 0.282, 0.302, 1.0),   # #42484D boiler iron
    "brass": (0.549, 0.420, 0.200, 1.0),  # #8C6B33 well brass
    "flame": (1.000, 0.902, 0.000, 1.0),  # #FFE600 pilot flame
}

# name, parent, head, tail
BONES = [
    ("root", None, (0, 0, 0), (0, 0.3, 0)),
    ("pelvis", "root", (0, 1.02, 0), (0, 1.36, 0)),
    ("spine", "pelvis", (0, 1.36, 0), (0, 2.10, 0)),
    ("head", "spine", (0, 2.10, 0), (0, 2.62, 0)),
    ("arm.L", "spine", (0.60, 2.02, 0), (0.60, 1.42, 0)),
    ("forearm.L", "arm.L", (0.60, 1.42, 0), (0.60, 0.96, 0)),
    ("arm.R", "spine", (-0.60, 2.02, 0), (-0.60, 1.42, 0)),
    ("forearm.R", "arm.R", (-0.60, 1.42, 0), (-0.60, 0.96, 0)),
    ("thigh.L", "pelvis", (0.30, 1.02, 0), (0.30, 0.58, 0)),
    ("shin.L", "thigh.L", (0.30, 0.58, 0), (0.30, 0.16, 0)),
    ("foot.L", "shin.L", (0.30, 0.16, 0), (0.30, 0.10, 0.52)),
    ("thigh.R", "pelvis", (-0.30, 1.02, 0), (-0.30, 0.58, 0)),
    ("shin.R", "thigh.R", (-0.30, 0.58, 0), (-0.30, 0.16, 0)),
    ("foot.R", "shin.R", (-0.30, 0.16, 0), (-0.30, 0.10, 0.52)),
]

# bone, kind ('box'|'cyl'|'wheel'), size or (radius, depth) or (radius, tube), at (x,y,z), material
SPECS = {
    "n01X": [
        ("pelvis", "box", (0.86, 0.44, 0.56), (0, 1.20, 0), "iron"),
        ("spine", "box", (1.00, 0.78, 0.66), (0, 1.76, 0), "iron"),
        ("spine", "cyl", (0.30, 0.10), (0, 1.80, 0.36), "brass"),      # chest valve disc
        ("spine", "box", (0.30, 0.34, 0.06), (0, 1.46, 0.34), "flame"), # furnace slit
        ("head", "wheel", (0.40, 0.07), (0, 2.36, 0), "brass"),        # valve-wheel head
        ("head", "cyl", (0.10, 0.22), (0, 2.36, 0), "brass"),          # hub
        ("arm.L", "box", (0.26, 0.62, 0.30), (0.60, 1.72, 0.06), "iron"),
        ("forearm.L", "box", (0.32, 0.52, 0.36), (0.60, 1.20, 0.12), "iron"),
        ("forearm.L", "box", (0.46, 0.44, 0.50), (0.60, 0.82, 0.18), "iron"),  # piston fist
        ("arm.R", "box", (0.26, 0.62, 0.30), (-0.60, 1.72, 0.06), "iron"),
        ("forearm.R", "box", (0.32, 0.52, 0.36), (-0.60, 1.20, 0.12), "iron"),
        ("forearm.R", "box", (0.46, 0.44, 0.50), (-0.60, 0.82, 0.18), "iron"),
        ("thigh.L", "box", (0.38, 0.52, 0.38), (0.30, 0.80, 0), "iron"),
        ("shin.L", "box", (0.34, 0.48, 0.34), (0.30, 0.36, 0), "iron"),
        ("foot.L", "box", (0.50, 0.20, 0.68), (0.30, 0.10, 0.10), "iron"),
        ("thigh.R", "box", (0.38, 0.52, 0.38), (-0.30, 0.80, 0), "iron"),
        ("shin.R", "box", (0.34, 0.48, 0.34), (-0.30, 0.36, 0), "iron"),
        ("foot.R", "box", (0.50, 0.20, 0.68), (-0.30, 0.10, 0.10), "iron"),
    ],
}

D = math.radians


def bp(p):
    """Spec (right, up, forward) -> Blender (x, y, z). glTF export then gives the
    engine a model standing along +Y with its front on +Z."""
    return (p[0], -p[2], p[1])


def bd(d):
    """Same conversion for a size triple (no sign changes)."""
    return (d[0], d[2], d[1])


def wipe():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 24


_MAT_CACHE = {}


def material(name):
    if name in _MAT_CACHE:
        return _MAT_CACHE[name]
    mat = bpy.data.materials.new(name)
    _MAT_CACHE[name] = mat
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = MATERIALS[name]
    bsdf.inputs["Roughness"].default_value = 0.9
    if name == "flame":
        bsdf.inputs["Emission Color"].default_value = MATERIALS[name]
        bsdf.inputs["Emission Strength"].default_value = 1.0
    return mat


def build_armature():
    arm_data = bpy.data.armatures.new("rig")
    arm = bpy.data.objects.new("rig", arm_data)
    bpy.context.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for name, parent, head, tail in BONES:
        b = arm_data.edit_bones.new(name)
        b.head, b.tail = Vector(bp(head)), Vector(bp(tail))
        if parent:
            b.parent = arm_data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


def build_part(bone, kind, dims, at, mat_name, idx):
    if kind == "box":
        bpy.ops.mesh.primitive_cube_add(size=1, location=bp(at))
        bpy.context.active_object.scale = bd(dims)
    elif kind == "wheel":  # a valve wheel: low-segment torus rim, faces forward
        bpy.ops.mesh.primitive_torus_add(major_segments=8, minor_segments=4,
                                         major_radius=dims[0], minor_radius=dims[1],
                                         location=bp(at), rotation=(D(90), 0, 0))
    else:  # cylinder, axis along the spec's forward axis: a disc facing the camera
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=dims[0], depth=dims[1],
                                            location=bp(at), rotation=(D(90), 0, 0))
    obj = bpy.context.active_object
    obj.name = f"{bone}_{idx}"
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material(mat_name))
    return obj


def main():
    unit, out = sys.argv[sys.argv.index("--") + 1:][:2]
    if unit not in SPECS:
        sys.exit(f"no spec for {unit}")
    wipe()
    arm = build_armature()

    parts = []
    for idx, (bone, kind, dims, at, mat_name) in enumerate(SPECS[unit]):
        parts.append((build_part(bone, kind, dims, at, mat_name, idx), bone))

    # rigid skin: one bone per piece, weight 1, no automatic weights.
    # then join every piece into one skinned mesh: the engine draws one mesh per
    # material slot, not seventeen per unit.
    bpy.ops.object.select_all(action="DESELECT")
    for obj, bone in parts:
        group = obj.vertex_groups.new(name=bone)
        group.add(range(len(obj.data.vertices)), 1.0, "REPLACE")
    for obj, _ in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0][0]
    if len(parts) > 1:
        bpy.ops.object.join()
    body = bpy.context.view_layer.objects.active
    body.name = unit
    body.data.name = unit
    body.parent = arm
    body.modifiers.new("Armature", "ARMATURE").object = arm

    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"

    def key(action_name, frames, poses):
        """poses: frame -> {bone: (rx, ry, rz, loc_y)}"""
        act = bpy.data.actions.new(action_name)
        arm.animation_data_create()
        arm.animation_data.action = act
        for frame, pose in poses.items():
            bpy.context.scene.frame_set(frame)
            for bone, (rx, ry, rz, ly) in pose.items():
                pb = arm.pose.bones[bone]
                pb.rotation_euler = (D(rx), D(ry), D(rz))
                pb.location = (0, 0, ly)
                pb.keyframe_insert("rotation_euler", frame=frame)
                pb.keyframe_insert("location", frame=frame)
        act.use_fake_user = True
        return act

    idle = {
        1: {"spine": (0, 0, 0, 0), "arm.L": (0, 0, 0, 0), "arm.R": (0, 0, 0, 0), "root": (0, 0, 0, 0)},
        20: {"spine": (-2, 0, 0, 0), "arm.L": (3, 0, 0, 0), "arm.R": (-3, 0, 0, 0), "root": (0, 0, 0, 0.03)},
        40: {"spine": (0, 0, 0, 0), "arm.L": (0, 0, 0, 0), "arm.R": (0, 0, 0, 0), "root": (0, 0, 0, 0)},
    }
    walk = {
        1: {"thigh.L": (-24, 0, 0, 0), "shin.L": (12, 0, 0, 0), "thigh.R": (24, 0, 0, 0), "shin.R": (18, 0, 0, 0),
            "arm.L": (16, 0, 0, 0), "arm.R": (-16, 0, 0, 0), "root": (0, 0, 0, 0)},
        16: {"thigh.L": (24, 0, 0, 0), "shin.L": (18, 0, 0, 0), "thigh.R": (-24, 0, 0, 0), "shin.R": (12, 0, 0, 0),
             "arm.L": (-16, 0, 0, 0), "arm.R": (16, 0, 0, 0), "root": (0, 0, 0, 0.04)},
        32: {"thigh.L": (-24, 0, 0, 0), "shin.L": (12, 0, 0, 0), "thigh.R": (24, 0, 0, 0), "shin.R": (18, 0, 0, 0),
             "arm.L": (16, 0, 0, 0), "arm.R": (-16, 0, 0, 0), "root": (0, 0, 0, 0)},
    }
    attack = {
        1: {"forearm.R": (0, 0, 0, 0), "spine": (0, 0, 0, 0), "root": (0, 0, 0, 0)},
        8: {"forearm.R": (10, 0, 0, 0), "spine": (6, 0, 0, 0), "root": (0, 0, 0, -0.02)},
        14: {"forearm.R": (-74, 0, 0, 0), "spine": (-8, 0, 0, 0), "root": (0, 0, 0, 0.06)},
        24: {"forearm.R": (0, 0, 0, 0), "spine": (0, 0, 0, 0), "root": (0, 0, 0, 0)},
    }
    death = {
        1: {"root": (0, 0, 0, 0), "spine": (0, 0, 0, 0)},
        12: {"root": (26, 0, 0, -0.10), "spine": (10, 0, 0, 0)},
        30: {"root": (84, 0, 0, -0.55), "spine": (6, 0, 0, 0)},
    }
    for name, poses in (("idle", idle), ("walk", walk), ("attack", attack), ("death", death)):
        key(name, 0, poses)

    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.scene.frame_set(1)
    bpy.ops.export_scene.gltf(
        filepath=out, export_format="GLB", export_yup=True,
        export_animations=True, export_animation_mode="ACTIONS",
        export_apply=False, export_skins=True, export_morph=False,
    )
    print(f"built {unit}: {len(parts)} parts joined, {len(BONES)} bones, 4 actions, "
          f"{len(body.data.polygons)} faces, {len(body.data.materials)} materials -> {out}")


if __name__ == "__main__":
    main()
