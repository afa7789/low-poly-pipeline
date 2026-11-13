"""Review renders of a unit GLB: the rest pose from five cameras, and frames of its clips.

    blender -b -P tools/blender/hand_views.py -- <unit.glb> <out prefix> [px=420] [clip,clip,...] [frames=6]

Writes <prefix>_{front,side,back,q,game}.png (game = the match camera's tilt) and, per clip,
<prefix>_<clip>_{s,q}_NN.png (side and three-quarter views).
"""
import math
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
GLB, OUT = args[0], args[1]
PX = int(args[2]) if len(args) > 2 else 420
CLIPS = args[3].split(",") if len(args) > 3 and args[3] else []
FRAMES = int(args[4]) if len(args) > 4 else 6
REST = (("front", 0, 3), ("side", 90, 3), ("back", 180, 3), ("q", 35, 15), ("game", 30, 52))
CLIP_VIEWS = (("s", 90, 4), ("q", 35, 12))


def rest(arm):
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()


def bounds():
    pts = [o.matrix_world @ v.co for o in bpy.data.objects if o.type == "MESH" for v in o.data.vertices]
    lo = Vector(min(p[i] for p in pts) for i in range(3))
    hi = Vector(max(p[i] for p in pts) for i in range(3))
    return (lo + hi) / 2, max(hi - lo)


def aim(cam, sun, centre, azimuth, elevation):
    az, el = math.radians(azimuth), math.radians(elevation)
    cam.location = centre + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * 30
    cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
    sun.rotation_euler = (math.radians(50), 0, az + math.radians(35))


def shoot(scene, path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=GLB)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    arm.animation_data_create()
    arm.animation_data.action = None
    for track in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(track)
    rest(arm)
    bpy.context.view_layer.update()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x = scene.render.resolution_y = PX
    scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.58, 0.55, 0.56, 1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0.9
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 2.6
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.type = "ORTHO"
    cam.data.clip_end = 200
    for obj in (sun, cam):
        scene.collection.objects.link(obj)
    scene.camera = cam
    centre, size = bounds()
    cam.data.ortho_scale = size * 1.3
    for tag, azimuth, elevation in REST:
        aim(cam, sun, centre, azimuth, elevation)
        shoot(scene, f"{OUT}_{tag}.png")
    cam.data.ortho_scale = size * 1.7           # room for a lunge or a fall
    scene.render.resolution_x = scene.render.resolution_y = min(PX, 300)     # 70+ frames: small is enough
    for clip in CLIPS:
        action = bpy.data.actions.get(clip)
        if action is None:
            print("hand_views: no clip", clip)
            continue
        arm.animation_data.action = action
        first, last = (int(f) for f in action.frame_range)
        for i in range(FRAMES):
            rest(arm)                           # a channel the clip omits stays at rest
            scene.frame_set(first + round(i * (last - first) / FRAMES))
            for tag, azimuth, elevation in CLIP_VIEWS:
                aim(cam, sun, centre, azimuth, elevation)
                shoot(scene, f"{OUT}_{clip}_{tag}_{i:02d}.png")


main()
