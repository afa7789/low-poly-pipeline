"""blender -b -P anim_check.py -- <glb> <out.json> [actions=walk,attack,death]: p99.5 edge stretch per clip (walk_check.py of L6-5, per action; PIPELINE 28.L10-8, sdf_batch.py)"""
import bpy, sys, json, numpy as np
rest_args = sys.argv[sys.argv.index("--") + 1:]
glb, out = rest_args[0], rest_args[1]
want = next((a[8:].split(",") for a in rest_args if a.startswith("actions=")), ["walk", "attack", "death"])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
meshes = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("Icosphere")]
assert len(meshes) == 1, [m.name for m in meshes]
mesh = meshes[0]
arm.animation_data_create()
arm.data.pose_position = "POSE"
dg = bpy.context.evaluated_depsgraph_get()
def verts():
    ev = mesh.evaluated_get(dg); m = ev.to_mesh()
    p = np.array([v.co[:] for v in m.vertices]); ed = np.array([e.vertices[:] for e in m.edges]); ev.to_mesh_clear(); return p, ed
res = {}
for w in want:
    act = next((a for a in bpy.data.actions if w in a.name.lower()), None)
    if act is None:
        res[w] = None; continue
    arm.animation_data.action = act
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    bpy.context.scene.frame_set(f0); rest, edges = verts()
    rl = np.linalg.norm(rest[edges[:,0]] - rest[edges[:,1]], axis=1) + 1e-9
    key = {}
    for i, p in enumerate(np.round(rest / 1e-4).astype(np.int64)): key.setdefault(tuple(p), []).append(i)
    groups = [g for g in key.values() if len(g) > 1]
    worst, split = 0.0, 0.0
    for f in np.linspace(f0, f1, 12).astype(int):
        bpy.context.scene.frame_set(int(f)); p, _ = verts()
        r = np.linalg.norm(p[edges[:,0]] - p[edges[:,1]], axis=1) / rl
        worst = max(worst, float(np.percentile(r, 99.5)))
        for g in groups: split = max(split, float(np.ptp(p[g], axis=0).max()))
    res[w] = {"action": act.name, "edges": len(edges), "p99.5_stretch": round(worst, 3), "max_dup_split": round(split, 5)}
open(out, "w").write(json.dumps(res))
print("ANIMCHECK", json.dumps(res))
