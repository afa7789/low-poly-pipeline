#!/usr/bin/env python3
"""Capture reference animations from an animated GLB: joint positions per frame, plus
a textured flipbook for people to watch.

    blender -b -P tools/blender/ref_capture.py -- <model.glb> <outdir> <clip,clip,...> [frames]

Writes <outdir>/joints.json: {"rest": {bone: [head, tail]}, "clips": {clip: [{bone:
[head, tail]}, ...]}, "frames": {clip: [start, end]}, "fps": scene fps} for every bone,
IK targets included (a foot target marks the tip of a leg whose bones have no length), in
Blender world axes (x right, y back, z up; the model faces -y),
and <outdir>/<clip>.gif: side view (forward to the right) next to the game's 3/4 view.
Only joints.json is kept in git; the GIFs are for looking and can be made again.
rig_retarget.py turns the joints into our rig families' poses.
"""
import json
import pathlib
import shutil
import subprocess
import sys

import bpy
import mathutils

# the game camera, as in render_anim.py: front-right, above
CAM_34 = mathutils.Vector((-0.66, -0.66, 0.36)).normalized()
CAM_SIDE = mathutils.Vector((-1.0, 0.0, 0.0))


def safe(clip):
    """File name of a clip: Blender prefixes actions with their armature ("Rig|Walk")."""
    return [part for part in clip.split("|") if part][-1]


def load(glb):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    for o in [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name.startswith("Icosphere")]:
        bpy.data.objects.remove(o, do_unlink=True)
    return next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")


def bounds(arm):
    """Box of the deforming bones at rest (IK targets and poles sit far off the body)."""
    pts = [arm.matrix_world @ v for b in arm.data.bones if b.use_deform for v in (b.head_local, b.tail_local)]
    lo = mathutils.Vector([min(p[i] for p in pts) for i in range(3)])
    hi = mathutils.Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


def stage(arm, size=240):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x = sc.render.resolution_y = size
    sc.display.shading.light = "FLAT"
    sc.display.shading.color_type = "TEXTURE"
    sc.display.shading.show_object_outline = True
    sc.view_settings.view_transform = "Standard"
    sc.world = bpy.data.worlds.new("ref")
    sc.world.color = (0.93, 0.93, 0.9)
    lo, hi = bounds(arm)
    centre, extent = (lo + hi) / 2, hi - lo
    target = bpy.data.objects.new("target", None)
    target.location = centre
    sc.collection.objects.link(target)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max(extent) * 1.15         # a little room for a swing past the body
    cam.constraints.new("TRACK_TO").target = target
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam, centre, max(extent)


def world(arm, bone, rest=False):
    """[head, tail] in world space, to 0.1 mm (the file stays small; poses do not care)."""
    if rest:
        b = arm.data.bones[bone]
        ends = (arm.matrix_world @ b.head_local, arm.matrix_world @ b.tail_local)
    else:
        pb = arm.pose.bones[bone]
        ends = (arm.matrix_world @ pb.head, arm.matrix_world @ pb.tail)
    return [[round(c, 4) for c in v] for v in ends]


def capture(arm, clip, frames, cam, centre, reach, out):
    act = bpy.data.actions.get(clip) or next((a for a in bpy.data.actions if clip in a.name), None)
    if act is None:
        print("NO CLIP", clip)
        return None
    arm.animation_data_create()
    arm.animation_data.action = act
    start, end = (int(v) for v in act.frame_range)
    sc = bpy.context.scene
    poses = []
    for i in range(frames):
        sc.frame_set(start + round(i * (end - start) / max(frames - 1, 1)))
        poses.append({b.name: world(arm, b.name) for b in arm.pose.bones})
        for view, direction in (("side", CAM_SIDE), ("34", CAM_34)):
            cam.location = centre + direction * reach * 4
            sc.render.filepath = str(out / "frames" / f"{safe(clip)}_{view}_{i:03d}.png")
            bpy.ops.render.render(write_still=True)
    return poses


def flipbook(out, clip, frames):
    if not shutil.which("magick"):
        return
    pairs = [f"( {out}/frames/{safe(clip)}_side_{i:03d}.png {out}/frames/{safe(clip)}_34_{i:03d}.png +append )"
             for i in range(frames)]
    cmd = ["magick", "-delay", "6", "-loop", "0"]
    for p in pairs:
        cmd += p.split()
    subprocess.run(cmd + [str(out / f"{safe(clip)}.gif")], check=True)


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    glb, out, clips = args[0], pathlib.Path(args[1]), args[2].split(",")
    frames = int(args[3]) if len(args) > 3 else 24
    (out / "frames").mkdir(parents=True, exist_ok=True)
    arm = load(glb)
    cam, centre, reach = stage(arm)
    data = {"model": pathlib.Path(glb).stem, "fps": bpy.context.scene.render.fps,
            "rest": {b.name: world(arm, b.name, rest=True) for b in arm.data.bones}, "clips": {}, "frames": {}}
    for clip in clips:
        poses = capture(arm, clip, frames, cam, centre, reach, out)
        if poses:
            data["clips"][clip] = poses
            data["frames"][clip] = [int(v) for v in arm.animation_data.action.frame_range]
            flipbook(out, clip, frames)
    shutil.rmtree(out / "frames")           # the GIFs keep what people look at
    (out / "joints.json").write_text(json.dumps(data, separators=(",", ":")))
    print("REF_CAPTURED", len(data["clips"]), "clips ->", out)


if __name__ == "__main__":
    main()
