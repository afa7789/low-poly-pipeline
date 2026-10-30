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
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
BIG = 10 ** 9
BG_DIST = 0.3           # summed scene-linear distance from the flat background: under it a pixel is background (it has a vignette)
INK_LINEAR = 0.012      # scene-linear: the sheet's black outline is ~0.003, its darkest plate 0.03
sys.path.insert(0, str(HERE))
import silhouette as SIL  # noqa: E402


def bounds(obj):
    lo, hi = mathutils.Vector((1e9,) * 3), mathutils.Vector((-1e9,) * 3)
    for corner in obj.bound_box:
        p = obj.matrix_world @ mathutils.Vector(corner)
        lo, hi = mathutils.Vector(map(min, lo, p)), mathutils.Vector(map(max, hi, p))
    return lo, hi


def nearest_along_rows(ok):
    """Per row, the column of the nearest True in `ok`; the row's own column when it has none."""
    cols = np.arange(ok.shape[1])[None, :]
    left = np.maximum.accumulate(np.where(ok, cols, -1), axis=1)
    right = np.minimum.accumulate(np.where(ok, cols, BIG)[:, ::-1], axis=1)[:, ::-1]
    near = np.where((left >= 0) & ((right == BIG) | (cols - left <= right - cols)), left, right)
    return np.where(near == BIG, cols, near)


def bleed(img, panels):
    """Paint the sheet's background inside each panel's box with the nearest plate colour on
    the same row (not the black outline). A face whose projected spot lands on a gap (an arm
    hanging in front of the torso, a hand off the drawing) then shows the neighbouring plate,
    not a grey sliver."""
    W, H = img.size
    px = np.empty(W * H * 4, np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(H, W, 4)[::-1]                      # Blender stores rows bottom-up
    n = panels["front"].shape[0]
    bg = np.median(np.concatenate([px[0], px[-1], px[:, 0], px[:, -1]]), axis=0)[:3]
    for mask in panels.values():
        ys, xs = mask.nonzero()
        y0, y1, x0, x1 = (ys.min() * H // n, (ys.max() + 1) * H // n,
                          xs.min() * W // n, (xs.max() + 1) * W // n)
        fig = mask[(np.arange(y0, y1) * n // H)[:, None], (np.arange(x0, x1) * n // W)[None, :]]
        box = px[y0:y1, x0:x1]
        dark = box[..., :3].max(axis=2) <= INK_LINEAR
        plate = ~dark & (np.abs(box[..., :3] - bg).sum(axis=2) > BG_DIST)
        near = nearest_along_rows(fig & plate)
        gap = ~dark & ~plate                              # background, vignette and halo; ink stays
        box[gap] = np.take_along_axis(box, near[..., None], axis=1)[gap]
    img.pixels.foreach_set(np.ascontiguousarray(px[::-1]).ravel())


def face_panel(n):
    """(panel, mirrored) a face with world normal n is painted from. The review cameras
    (views.VIEWS) fix the image axes: the left camera sees the front on the right, the back
    camera sees +X on the left, top has the front at the bottom of the image and bottom
    (the camera flipped about X) has it at the top."""
    if abs(n.y) >= abs(n.x) and abs(n.y) >= abs(n.z):
        return ("front", False) if n.y < 0 else ("back", True)
    if abs(n.x) >= abs(n.z):
        return "left", n.x < 0
    return ("top" if n.z >= 0 else "bottom"), False


def panel_uv(panel, mirror, x, y, z):
    """(u, v) in 0..1 of a point at normalized model coordinates (x, y, z) on its panel."""
    if panel in ("front", "back"):
        u, v = x, z
    elif panel == "left":
        u, v = y, z
    else:  # top / bottom
        u, v = x, (y if panel == "top" else 1.0 - y)
    return (1.0 - u if mirror else u), v


def load_model(src):
    """The GLB's mesh object and its world bounds, Z-up, without the bone-shape helper."""
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
    return mesh_obj, lo, hi


def project_uvs(mesh_obj, lo, hi, boxes, size):
    """Give every face the UVs of the panel it faces, inside that panel's figure box."""
    W, H = size
    mesh = mesh_obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    uv = mesh.uv_layers.active.data
    # Wipe any pre-existing UVs; they are the old procedural layout.
    for layer in mesh.uv_layers:
        layer.active_render = layer == mesh.uv_layers.active
    span = [max(hi[i] - lo[i], 1e-6) for i in range(3)]
    for poly in mesh.polygons:
        panel, mirror = face_panel((mesh_obj.matrix_world.to_3x3() @ poly.normal).normalized())
        x0, y0, x1, y1 = boxes[panel]
        for li in poly.loop_indices:
            co = mesh_obj.matrix_world @ mesh.vertices[mesh.loops[li].vertex_index].co
            u, v = panel_uv(panel, mirror, *((co[i] - lo[i]) / span[i] for i in range(3)))
            uv[li].uv = ((x0 + u * (x1 - x0)) / W, 1.0 - (y0 + (1.0 - v) * (y1 - y0)) / H)


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    src, sheet, out = args[0], args[1], args[2]
    mesh_obj, lo, hi = load_model(src)

    img = bpy.data.images.load(str(pathlib.Path(sheet).resolve()), check_existing=False)
    W, H = img.size
    panels = SIL.concept_panels(sheet, 768, columns=True)   # the column cut: the blob split needs scipy, which Blender's Python lacks (it crashed every sheet run since 10-28; PIPELINE 32.L14-2)
    boxes = {}
    for name, mask in panels.items():
        ys, xs = mask.nonzero()
        sx, sy = W / 768, H / 768
        boxes[name] = (xs.min() * sx, ys.min() * sy, (xs.max() + 1) * sx, (ys.max() + 1) * sy)

    bleed(img, panels)
    project_uvs(mesh_obj, lo, hi, boxes, (W, H))

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
