#!/usr/bin/env python3
"""Capture reference animations from an animated GLB: joint positions per frame, plus
a textured flipbook for people to watch.

    blender -b -P tools/blender/ref_capture.py -- <model.glb> <outdir> <clip,clip,...> [frames] [mesh.glb]

A clip "A+B" plays A then B as one motion (a bow's draw then release). An animation-only
GLB (no mesh) can borrow a character to film with: pass its mesh GLB last; the actions
are played on that character's armature (same bone names).

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


def _action(name):
    """An action by exact name, else the only one whose name contains it (Blender prefixes
    "Rig|Walk" and truncates long names); ambiguous or missing: None."""
    exact = bpy.data.actions.get(name)
    if exact is not None:
        return exact
    found = [a for a in bpy.data.actions if name in a.name]
    return found[0] if len(found) == 1 else None


def _timeline(clip, frames):
    """[(action, frame)] for `frames` samples of a clip; "A+B" plays A then B (a bow's
    draw and release), each getting samples in proportion to its length."""
    parts = [_action(name) for name in clip.split("+")]
    if not all(parts):
        return None
    spans = [tuple(int(v) for v in act.frame_range) for act in parts]
    total = sum(end - start for start, end in spans) or 1
    out = []
    for i in range(frames):
        t = i * total / max(frames - 1, 1)
        for act, (start, end) in zip(parts, spans):
            if t <= end - start or act is parts[-1]:
                out.append((act, start + round(min(t, end - start))))
                break
            t -= end - start
    return out, total


def capture(arm, clip, frames, cam, centre, reach, out):
    got = _timeline(clip, frames)
    if got is None:
        print("NO CLIP", clip)
        return None, 0
    timeline, total = got
    arm.animation_data_create()
    sc = bpy.context.scene
    poses = []
    for i, (act, frame) in enumerate(timeline):
        arm.animation_data.action = act
        if act.slots:                       # Blender 5: an action made for another armature
            arm.animation_data.action_slot = act.slots[0]            # plays only through its slot
        sc.frame_set(frame)
        poses.append({b.name: world(arm, b.name) for b in arm.pose.bones})
        for view, direction in (("side", CAM_SIDE), ("34", CAM_34)):
            cam.location = centre + direction * reach * 4
            sc.render.filepath = str(out / "frames" / f"{safe(clip)}_{view}_{i:03d}.png")
            bpy.ops.render.render(write_still=True)
    return poses, total


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
    if len(args) > 4:                       # film the clips on a character of the same rig
        bpy.ops.import_scene.gltf(filepath=args[4])
        arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE" and o != arm
                   and any(c.type == "MESH" for c in o.children))
    cam, centre, reach = stage(arm)
    data = {"model": pathlib.Path(glb).stem, "fps": bpy.context.scene.render.fps,
            "rest": {b.name: world(arm, b.name, rest=True) for b in arm.data.bones}, "clips": {}, "frames": {}}
    for clip in clips:
        poses, total = capture(arm, clip, frames, cam, centre, reach, out)
        if poses:
            data["clips"][clip] = poses
            data["frames"][clip] = [0, total]
            flipbook(out, clip, frames)
    shutil.rmtree(out / "frames")           # the GIFs keep what people look at
    (out / "joints.json").write_text(json.dumps(data, separators=(",", ":")))
    print("REF_CAPTURED", len(data["clips"]), "clips ->", out)


if __name__ == "__main__":
    main()
