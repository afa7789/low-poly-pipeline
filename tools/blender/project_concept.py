#!/usr/bin/env python3
"""Project the approved concept sheet onto an exported GLB as a real atlas.

    blender -b -P tools/blender/project_concept.py -- <in.glb> <sheet.jpg> <out.glb>

This is the opposite of the old procedural `texturize()`: no sine mottle, no
per-face random tile. Each face is projected from the concept panel that matches its
dominant normal (front / back / left / top / bottom), using the panel's silhouette
bbox and the model's bbox. Adjacent faces in the same view share continuous UVs, so
painted rivets, rim light and outlines land where the concept put them. Faces on
view boundaries still seam; that is expected for a first pass and is hidden by the
hard-surface corners.
"""
import pathlib
import sys

import bpy
import mathutils

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import silhouette as SIL  # noqa: E402


def bounds(obj):
    lo, hi = mathutils.Vector((1e9,) * 3), mathutils.Vector((-1e9,) * 3)
    for corner in obj.bound_box:
        p = obj.matrix_world @ mathutils.Vector(corner)
        lo, hi = mathutils.Vector(map(min, lo, p)), mathutils.Vector(map(max, hi, p))
    return lo, hi


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    src, sheet, out = args[0], args[1], args[2]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)
    for o in [o for o in bpy.context.scene.objects
              if o.type == "MESH" and o.name.startswith("Icosphere")]:
        bpy.data.objects.remove(o, do_unlink=True)

    mesh_obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
    lo, hi = bounds(mesh_obj)
    if (hi - lo).y > (hi - lo).z * 1.5:  # glTF import is Y-up
        for obj in [o for o in bpy.context.scene.objects if o.parent is None]:
            obj.rotation_euler.x += 90 * 3.141592653589793 / 180
        bpy.context.view_layer.update()
        lo, hi = bounds(mesh_obj)

    img = bpy.data.images.load(str(pathlib.Path(sheet).resolve()), check_existing=False)
    W, H = img.size
    panels = SIL.concept_panels(sheet, 768)
    boxes = {}
    for name, mask in panels.items():
        ys, xs = mask.nonzero()
        sx, sy = W / 768, H / 768
        boxes[name] = (xs.min() * sx, ys.min() * sy, (xs.max() + 1) * sx, (ys.max() + 1) * sy)

    mesh = mesh_obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    uv = mesh.uv_layers.active.data
    # Wipe any pre-existing UVs; they are the old procedural layout.
    for layer in mesh.uv_layers:
        layer.active_render = layer == mesh.uv_layers.active
    for poly in mesh.polygons:
        n = (mesh_obj.matrix_world.to_3x3() @ poly.normal).normalized()
        panel, mirror = "front", False
        if abs(n.y) >= abs(n.x) and abs(n.y) >= abs(n.z):
            panel = "front" if n.y < 0 else "back"
            mirror = n.y > 0
        elif abs(n.x) >= abs(n.z):
            panel = "left"
            mirror = n.x > 0
        else:
            panel = "top" if n.z >= 0 else "bottom"
            mirror = n.z < 0
        x0, y0, x1, y1 = boxes[panel]
        for li in poly.loop_indices:
            co = mesh_obj.matrix_world @ mesh.vertices[mesh.loops[li].vertex_index].co
            x = (co.x - lo.x) / max(hi.x - lo.x, 1e-6)
            y = (co.y - lo.y) / max(hi.y - lo.y, 1e-6)
            z = (co.z - lo.z) / max(hi.z - lo.z, 1e-6)
            if panel in ("front", "back"):
                u, v = x, z
            elif panel == "left":
                u, v = y, z
            else:  # top / bottom
                u, v = x, y
            if mirror:
                u = 1.0 - u
            px = x0 + u * (x1 - x0)
            py = y0 + (1.0 - v) * (y1 - y0)
            uv[li].uv = (px / W, 1.0 - py / H)

    # One concept image on every existing material slot: keeps the engine's 3-5
    # material contract while the sheet supplies all colour and surface detail.
    for slot in mesh_obj.material_slots:
        mat = slot.material
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        bsdf = nodes.get("Principled BSDF")
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.interpolation = "Linear"
        mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Base Color"].default_value = (1, 1, 1, 1)
        bsdf.inputs["Roughness"].default_value = 0.85

    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_yup=True,
                              export_animations=True, export_animation_mode="ACTIONS",
                              export_apply=False, export_skins=True, export_morph=False,
                              export_image_format="AUTO")
    print("projected", sheet, "->", out)


if __name__ == "__main__":
    main()
