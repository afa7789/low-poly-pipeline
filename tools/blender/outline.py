#!/usr/bin/env python3
"""L15-3: the continuous black contour of a WC3 model, as an inverted hull (PIPELINE 33.L15-3).

    blender -b -P tools/blender/outline.py -- <in.glb> <out.glb> [offset=0.012] [face=<rgba.png>]
    outline.apply(glb, hull=True, face=None)   # python side: --outline hull / --face decal, in place, after every GLB edit of stage 2

The body's mesh is copied, each vertex pushed out along its (welded) normal by `offset` x the model's height, the winding
reversed and one black material put on it: with back-face culling the camera sees only the far side of the shell, a dark rim
around every silhouette. The copy keeps the vertex groups and the armature modifier, so it is skinned like the body; the GLB
carries it as a second mesh (the game's loader keeps every mesh). Triangles of the hull = triangles of the body.

`face=<png>` (--face decal): the head's picture, cut from the concept at 128 px, on one flat quad (2 triangles) just in front of the
head bone's verts, skinned to that bone, instead of 64 px stretched over the faces of an 8-sided lathe.
"""
import pathlib
import subprocess
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
OFFSET = 0.012      # share of the model's height; the brief's .01-.015 H


def hull_mesh(pos, tri, offset):
    """(pos', tri'): `pos` (n, 3) pushed `offset` along the area-weighted normal of its welded position (a hard edge's split
    vertices move together, no crack) and `tri` (m, 3) with the winding reversed."""
    pos, tri = np.asarray(pos, float), np.asarray(tri, int)
    face = np.cross(pos[tri[:, 1]] - pos[tri[:, 0]], pos[tri[:, 2]] - pos[tri[:, 0]])
    nor = np.zeros_like(pos)
    for k in range(3):
        np.add.at(nor, tri[:, k], face)
    _, inv = np.unique(np.round(pos / 1e-5).astype(np.int64), axis=0, return_inverse=True)
    inv = inv.reshape(-1)
    summed = np.zeros((inv.max() + 1, 3))
    np.add.at(summed, inv, nor)
    nor = summed[inv]
    nor /= np.maximum(np.linalg.norm(nor, axis=1, keepdims=True), 1e-12)
    return pos + offset * nor, tri[:, ::-1].copy()


def apply(glb, hull=True, face=None, offset=OFFSET):
    """Add the hull (`hull`) and the face quad (`face` = png) to `glb` in place (a Blender round trip). True when the file came out."""
    glb = pathlib.Path(glb)
    tmp = glb.with_name(f"{glb.stem}-outline.glb")
    tmp.unlink(missing_ok=True)
    subprocess.run(["blender", "-b", "-P", str(HERE / "outline.py"), "--", str(glb), str(tmp), f"offset={offset if hull else 0}",
                    *([f"face={face}"] if face else [])], capture_output=True, text=True)
    if tmp.exists():
        tmp.replace(glb)
        return True
    return False


def build_hull(body, offset):
    """In Blender: the hull object of `body`, linked beside it (same parent, groups, armature modifier)."""
    import bpy
    mesh = body.data
    pos = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", pos)
    pos = pos.reshape(-1, 3)
    mesh.calc_loop_triangles()
    tri = np.array([t.vertices[:] for t in mesh.loop_triangles], int)
    height = max(pos[:, 2].max() - pos[:, 2].min(), 1e-6)
    new_pos, new_tri = hull_mesh(pos, tri, offset * height)
    data = bpy.data.meshes.new("outline")
    data.from_pydata(new_pos.tolist(), [], new_tri.tolist())
    data.update()
    mat = bpy.data.materials.new("outline")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Specular IOR Level"].default_value = 0.0
    mat.use_backface_culling = True
    data.materials.append(mat)
    hull = bpy.data.objects.new("outline", data)
    bpy.context.collection.objects.link(hull)
    hull.parent = body.parent
    hull.matrix_parent_inverse = body.matrix_parent_inverse.copy()
    hull.matrix_world = body.matrix_world.copy()
    for group in body.vertex_groups:            # same vertex order as the body: the groups copy index for index
        hull.vertex_groups.new(name=group.name)
    for v in mesh.vertices:
        for g in v.groups:
            hull.vertex_groups[g.group].add([v.index], g.weight, "REPLACE")
    for mod in body.modifiers:
        if mod.type == "ARMATURE":
            hull.modifiers.new("Armature", "ARMATURE").object = mod.object
    return hull, len(new_tri)


def build_face(body, png, lift=0.004):
    """In Blender: a quad textured with `png` in front of the verts `body` weights to its head bone, skinned 100% to that bone.
    None when the body has no head group. Front is -Y, as build_unit.decal_uv."""
    import bpy
    group = next((g for g in body.vertex_groups if g.name == "head"), None)
    if group is None:
        return None
    ids = [v.index for v in body.data.vertices if any(g.group == group.index and g.weight > 0.5 for g in v.groups)]
    if not ids:
        return None
    co = np.array([body.data.vertices[i].co[:] for i in ids])
    lo, hi = co.min(axis=0), co.max(axis=0)
    height = max(np.ptp([v.co.z for v in body.data.vertices]), 1e-6)
    y = lo[1] - lift * height
    quad = [(lo[0], y, lo[2]), (hi[0], y, lo[2]), (hi[0], y, hi[2]), (lo[0], y, hi[2])]
    data = bpy.data.meshes.new("face")
    data.from_pydata(quad, [], [(0, 1, 2, 3)])
    data.uv_layers.new(name="UVMap")
    for uv, loop in zip(((0, 0), (1, 0), (1, 1), (0, 1)), data.loops):
        data.uv_layers[0].data[loop.index].uv = uv
    mat = bpy.data.materials.new("face")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(png)
    bsdf = nodes["Principled BSDF"]
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    mat.node_tree.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 1.0
    data.materials.append(mat)
    obj = bpy.data.objects.new("face", data)
    bpy.context.collection.objects.link(obj)
    obj.parent, obj.matrix_parent_inverse, obj.matrix_world = body.parent, body.matrix_parent_inverse.copy(), body.matrix_world.copy()
    obj.vertex_groups.new(name="head").add(range(4), 1.0, "REPLACE")
    for mod in body.modifiers:
        if mod.type == "ARMATURE":
            obj.modifiers.new("Armature", "ARMATURE").object = mod.object
    return obj


def main():
    import bpy
    args = sys.argv[sys.argv.index("--") + 1:]
    src, out = args[:2]
    offset = next((float(a[7:]) for a in args if a.startswith("offset=")), OFFSET)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)
    bodies = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith(("outline", "face", "Icosphere"))]
    if len(bodies) != 1:
        print("outline: expected one body mesh, found", [o.name for o in bodies])
        return
    # the importer's mesh is in world space already skinned by the armature: the rest pose is the bind pose
    tris = build_hull(bodies[0], offset)[1] if offset > 0 else 0
    png = next((a[5:] for a in args if a.startswith("face=")), None)
    if png and build_face(bodies[0], png) is None:
        print("outline: no head group, no face quad")
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_yup=True, export_animations=True,
                              export_animation_mode="ACTIONS", export_apply=False, export_skins=True, export_morph=False)
    print(f"outline: hull of {tris} tris -> {out}")


if __name__ == "__main__":
    main()
