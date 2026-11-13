# blender -b -P render_gamecam.py -- <models dir> <out tiles dir> <unit> [...]
# Attack actions as the PLAYER sees them: ortho camera at the game's elevation (CameraMath.hpp: AoA 304 = 56 degrees
# above the ground), unit facing its target (screen right in view "g"; up-screen, away from the camera, in view "b"),
# a team disc on the ground under the idle stance and a target post ahead; every 2nd frame of the first 0.8 s (24 fps).
# One fixed framing per unit, so travel across the ground is comparable between frames and actions.
# Prints per action: LEAD (how far the front of the silhouette gets past the idle front, in body lengths), HOLD (frames
# at >= 85% of that), REAR (how far the back end follows, body lengths), END (clip length in frames).
# Env: GC_VIEWS=g,b  GC_PX=200  GC_ACTS=attack (name prefix)  GC_MEASURE=1 (numbers only, no render)
import math
import os
import sys
import traceback

import bpy
import numpy as np
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
models, outdir, units = a[0], a[1], a[2:]
ELEV = 56.0
ALL_VIEWS = {"g": -90.0, "b": 200.0}
VIEWS = {k: ALL_VIEWS[k] for k in os.environ.get("GC_VIEWS", "g").split(",")}
PX = int(os.environ.get("GC_PX", "200"))
PREFIX = os.environ.get("GC_ACTS", "attack")
MEASURE = os.environ.get("GC_MEASURE") == "1"
FRAMES = list(range(1, 21, 2))


def posed(meshes):
    dg = bpy.context.evaluated_depsgraph_get(); out = []
    for o in meshes:
        ev = o.evaluated_get(dg); m = ev.to_mesh()
        out.append(np.array([(ev.matrix_world @ v.co)[:] for v in m.vertices])); ev.to_mesh_clear()
    return np.concatenate(out)


def emit(name, rgb):
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    nt = mat.node_tree; nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (*rgb, 1); e.inputs[1].default_value = 1.0
    o = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(e.outputs[0], o.inputs[0])
    return mat


def scene():
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 6; sc.cycles.device = 'CPU'
    sc.render.resolution_x = sc.render.resolution_y = PX
    sc.world = bpy.data.worlds.new("w"); sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.30, 0.42, 0.30, 1)
    sun = bpy.data.lights.new("sun", 'SUN'); sun.energy = 3.0
    so = bpy.data.objects.new("sun", sun); bpy.context.collection.objects.link(so)
    so.rotation_euler = (math.radians(40), 0, math.radians(30))
    cams = {}
    for name in VIEWS:
        cam = bpy.data.cameras.new(name); cam.type = 'ORTHO'
        co = bpy.data.objects.new(name, cam); bpy.context.collection.objects.link(co); cams[name] = co
    return sc, cams


def stage(idle):
    """Team disc under the idle stance, target post 0.35 body lengths past the idle front (forward is -y)."""
    lo, hi = idle.min(axis=0), idle.max(axis=0)
    length = hi[1] - lo[1]
    cx, cy = 0.0, (lo[1] + hi[1]) / 2
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.55 * length, depth=0.01, location=(cx, cy, 0.0))
    disc = bpy.context.object; disc.data.materials.append(emit("ring", (0.05, 0.2, 0.9)))
    post_y = lo[1] - 0.35 * length
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.06 * length, depth=0.5 * (hi[2] - lo[2]),
                                        location=(cx, post_y, 0.25 * (hi[2] - lo[2])))
    post = bpy.context.object; post.data.materials.append(emit("post", (0.9, 0.1, 0.05)))
    return np.array([[cx - 0.55 * length, cy - 0.55 * length, 0], [cx + 0.55 * length, cy + 0.55 * length, 0],
                     [cx, post_y, 0.5 * (hi[2] - lo[2])]])


def aim(co, az, pts):
    az, el = math.radians(az), math.radians(ELEV)
    d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    lo, hi = Vector(pts.min(axis=0)), Vector(pts.max(axis=0)); center = (lo + hi) / 2
    co.location = center + d * 40
    co.rotation_euler = (center - co.location).to_track_quat('-Z', 'Y').to_euler()
    m = co.rotation_euler.to_matrix()
    right, up = m @ Vector((1, 0, 0)), m @ Vector((0, 1, 0))
    rel = pts - np.array(center)
    co.data.ortho_scale = 2.1 * max(np.abs(rel @ np.array(right)).max(), np.abs(rel @ np.array(up)).max())


def measure(unit, act, clouds, last):
    idle = clouds[0]
    length = idle[:, 1].max() - idle[:, 1].min()
    lead = [(idle[:, 1].min() - c[:, 1].min()) / length for c in clouds]
    rear = [(idle[:, 1].max() - c[:, 1].max()) / length for c in clouds]
    peak = max(lead)
    hold = sum(1 for v in lead if peak > 0.05 and v >= 0.85 * peak)
    print(f"GC {unit} {act} LEAD {peak:.2f} at f{1 + lead.index(peak)} HOLD {hold} BACK {min(lead):.2f} "
          f"REAR {max(rear):.2f} END {last} LEN {length:.2f}", flush=True)


def pose(arm, sc, act, f):
    arm.animation_data_create(); arm.animation_data.action = act
    if act.slots: arm.animation_data.action_slot = act.slots[0]
    for pb in arm.pose.bones: pb.matrix_basis.identity()
    sc.frame_set(f)


for unit in units:
    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=os.path.join(models, unit + ".glb"))
        arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
        if arm.animation_data:
            for t in list(arm.animation_data.nla_tracks): arm.animation_data.nla_tracks.remove(t)
        for o in [o for o in bpy.data.objects if o.type == 'MESH' and not o.vertex_groups]:
            bpy.data.objects.remove(o, do_unlink=True)
        meshes = [o for o in bpy.data.objects if o.type == 'MESH']
        sc, cams = scene()
        os.makedirs(os.path.join(outdir, unit), exist_ok=True)
        acts = sorted((x for x in bpy.data.actions if x.name.startswith(PREFIX)), key=lambda x: x.name)

        dense = {}
        for act in acts:
            last = int(act.frame_range[1])
            dense[act.name] = []
            for f in range(1, last + 1):
                pose(arm, sc, act, f); dense[act.name].append(posed(meshes))
            measure(unit, act.name, dense[act.name], last)
        if MEASURE or not acts:
            continue
        idle = dense[acts[0].name][0]
        extra = stage(idle)
        pts = np.concatenate([c for name in dense for c in dense[name][:20:2]] + [extra])
        for view, co in cams.items(): aim(co, VIEWS[view], pts)
        for act in acts:
            last = int(act.frame_range[1])
            for i, f in enumerate(FRAMES):
                pose(arm, sc, act, min(f, last))
                for view, co in cams.items():
                    sc.camera = co
                    sc.render.filepath = os.path.join(outdir, unit, f"{act.name}_{view}_{i:02d}.png")
                    bpy.ops.render.render(write_still=True)
        print("RENDERED", unit, flush=True)
    except (RuntimeError, StopIteration, OSError, ValueError) as e:
        traceback.print_exc()
        print("RENDERFAIL", unit, repr(e), flush=True)
