#!/usr/bin/env python3
"""Raw TRELLIS GLB -> oriented raw + <= TARGET tris (Blender QEM collapse) with colour rebaked from the raw.
    blender -b -P reduce_rebake.py -- <raw.glb> <outdir> [rot_z_deg=0] [target=700] [atlas=1024]
Writes raw-oriented.glb, model.glb (decimated, baked), atlas.png, reduce.json. Frame = Blender Z-up, front -Y."""
import json
import math
import pathlib
import sys

import bpy

sys.path.insert(0, "/Users/afa/Developer/arthur/castle_fight/tools/blender")
from views import make_unlit  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = pathlib.Path(argv[0]), pathlib.Path(argv[1])
ROT = float(argv[2]) if len(argv) > 2 else 0.0
TARGET = int(argv[3]) if len(argv) > 3 else 700
ATLAS = int(argv[4]) if len(argv) > 4 else 1024


def tris(obj):
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def activate(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def export(obj, path):
    activate(obj)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_animations=False, export_skins=False)


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SRC))
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
high = meshes[0]
activate(high)
for o in meshes:
    o.select_set(True)
if len(meshes) > 1:
    bpy.ops.object.join()
bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
high.rotation_mode = "XYZ"
high.rotation_euler.z += math.radians(ROT)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
high_tris = tris(high)
OUT.mkdir(parents=True, exist_ok=True)
export(high, OUT / "raw-oriented.glb")

low = high.copy()
low.data = high.data.copy()
bpy.context.collection.objects.link(low)
low.name = "low"
low.data.materials.clear()
mod = low.modifiers.new("qem", "DECIMATE")
mod.use_collapse_triangulate = True
ratio = min(1.0, TARGET / high_tris)
mod.ratio = ratio
activate(low)
bpy.ops.object.modifier_apply(modifier=mod.name)
for _ in range(8):                       # the modifier can land a few tris above the ratio
    if tris(low) <= TARGET:
        break
    mod = low.modifiers.new("qem", "DECIMATE")
    mod.use_collapse_triangulate = True
    mod.ratio = TARGET / tris(low) * 0.995
    bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.01)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.object.shade_flat()

img = bpy.data.images.new("atlas", ATLAS, ATLAS, alpha=False)
mat = bpy.data.materials.new("baked")
mat.use_nodes = True
tree = mat.node_tree
tex = tree.nodes.new("ShaderNodeTexImage")
tex.image = img
tree.links.new(tex.outputs["Color"], tree.nodes["Principled BSDF"].inputs["Base Color"])
low.data.materials.append(mat)

make_unlit()                             # the raw base colour goes to Emission: bake it with no light
# make_unlit touched the new material too: put its texture back on Base Color after the bake
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 1
span = max(high.dimensions)
activate(low)
high.select_set(True)
tree.nodes.active = tex
bpy.ops.object.bake(type="EMIT", use_selected_to_active=True, cage_extrusion=0.02 * span, max_ray_distance=0.06 * span, margin=8)
img.filepath_raw = str(OUT / "atlas.png")
img.file_format = "PNG"
img.save()
b = tree.nodes["Principled BSDF"]
tree.links.new(tex.outputs["Color"], b.inputs["Base Color"])
for link in list(b.inputs["Emission Color"].links):
    tree.links.remove(link)
b.inputs["Emission Strength"].default_value = 0.0
b.inputs["Roughness"].default_value = 1.0
export(low, OUT / "model.glb")
report = {"raw_tris": high_tris, "tris": tris(low), "first_ratio": ratio, "dimensions": list(high.dimensions), "rot_z": ROT, "atlas": ATLAS}
(OUT / "reduce.json").write_text(json.dumps(report, indent=2))
print("REDUCE", report)
