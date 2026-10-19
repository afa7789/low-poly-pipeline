#!/usr/bin/env python3
"""Build one rigged, animated low-poly unit for Castle Fight, headless.

    blender -b -P tools/blender/build_unit.py -- n01X out.glb

Follows the blender-hard-surface / blender-rigging / blender-animation skills:
real size in metres, flat shapes with a micro bevel and weighted normals, rigid
islands bound 1.0 (a machine deforms in blocks, never with bone-heat smears),
key poses first, then breakdowns, then spline.

Engine contract (src/render/ModelManifest.hpp, tools/model_chart.cpp):
  * one skin, joints in skins[0] order, <=255 joints;
  * animations[] order IS the clip index in data/models.tsv;
  * the renderer scales by max(h, 0.8w, 0.8d), so only proportions matter;
  * authored facing glTF +Z; yaw_deg in the TSV fixes the rest.
"""
import json
import math
import pathlib
import sys

import bmesh
import bpy
from mathutils import Vector

# ---------------------------------------------------------------- materials
MATERIALS = {
    "iron": (0.431, 0.486, 0.549, 1.0),   # #6E7C8C steel mid
    "brass": (0.784, 0.573, 0.180, 1.0),  # #C8922E gold mid
    "flame": (1.000, 0.902, 0.000, 1.0),  # #FFE600 pilot flame
}

# ---------------------------------------------------------------- skeleton
# name, parent, head, tail   (spec space: right, up, forward)
BONES = [
    ("root", None, (0, 0, 0), (0, 0.3, 0)),
    ("pelvis", "root", (0, 1.20, 0), (0, 1.50, 0)),
    ("spine", "pelvis", (0, 1.50, 0), (0, 2.16, 0)),
    ("head", "spine", (0, 2.16, 0), (0, 2.72, 0)),
    ("arm.L", "spine", (0.78, 2.02, 0), (0.78, 1.40, 0)),
    ("forearm.L", "arm.L", (0.78, 1.40, 0), (0.78, 0.90, 0)),
    ("arm.R", "spine", (-0.78, 2.02, 0), (-0.78, 1.40, 0)),
    ("forearm.R", "arm.R", (-0.78, 1.40, 0), (-0.78, 0.90, 0)),
    ("thigh.L", "pelvis", (0.28, 1.18, 0), (0.28, 0.56, 0)),
    ("shin.L", "thigh.L", (0.28, 0.56, 0), (0.28, 0.10, 0)),
    ("foot.L", "shin.L", (0.28, 0.10, 0), (0.28, 0.06, 0.55)),
    ("thigh.R", "pelvis", (-0.28, 1.18, 0), (-0.28, 0.56, 0)),
    ("shin.R", "thigh.R", (-0.28, 0.56, 0), (-0.28, 0.10, 0)),
    ("foot.R", "shin.R", (-0.28, 0.10, 0), (-0.28, 0.06, 0.55)),
]

# ---------------------------------------------------------------- specs
# bone, kind, dims, at, material, opts
#   kind box     dims = (x, y, z)
#   kind cyl     dims = (radius, depth), opts axis='fwd'|'up'
#   kind wheel   dims = (major_radius, tube)
#   opts rot = degrees around the spec forward axis (spokes)
SPECS = {
    # The well-pump golem of the concept sheet: spoked valve wheel on a stem,
    # brass pauldrons wider than the chest, big chest disc, trapezoid pelvis,
    # cylindrical forearms, stepped brass fists, brass knee and ankle joints.
    "n01X": [
        # head: valve wheel with spokes on a stem
        ("head", "box", (0.17, 0.24, 0.17), (0, 2.28, 0), "iron", {}),
        ("head", "wheel", (0.34, 0.055), (0, 2.64, 0), "brass", {}),
        ("head", "box", (0.66, 0.055, 0.055), (0, 2.64, 0), "brass", {"rot": 0}),
        ("head", "box", (0.66, 0.055, 0.055), (0, 2.64, 0), "brass", {"rot": 60}),
        ("head", "box", (0.66, 0.055, 0.055), (0, 2.64, 0), "brass", {"rot": 120}),
        ("head", "cyl", (0.085, 0.15), (0, 2.64, 0), "brass", {"axis": "fwd"}),
        # torso
        ("spine", "box", (1.10, 0.84, 0.62), (0, 1.88, 0), "iron", {}),
        ("spine", "cyl", (0.34, 0.10), (0, 1.94, 0.33), "brass", {"axis": "fwd"}),
        ("spine", "box", (0.15, 0.21, 0.07), (0, 1.53, 0.33), "flame", {}),
        ("spine", "cyl", (0.045, 0.06), (0.30, 1.74, 0.33), "brass", {"axis": "fwd"}),
        # pelvis: trapezoid body plus a band
        ("pelvis", "box", (0.80, 0.42, 0.54), (0, 1.30, 0), "iron", {}),
        ("pelvis", "box", (0.88, 0.12, 0.58), (0, 1.06, 0), "brass", {}),
        # pauldrons ride the arms
        ("arm.L", "box", (0.46, 0.54, 0.58), (0.80, 2.04, 0), "brass", {}),
        ("arm.L", "box", (0.27, 0.54, 0.29), (0.80, 1.60, 0), "iron", {}),
        ("forearm.L", "cyl", (0.20, 0.50), (0.80, 1.14, 0.02), "iron", {"axis": "up"}),
        ("forearm.L", "box", (0.42, 0.34, 0.44), (0.80, 0.80, 0.06), "brass", {}),
        ("forearm.L", "box", (0.44, 0.16, 0.32), (0.80, 0.62, 0.10), "brass", {}),
        ("arm.R", "box", (0.46, 0.54, 0.58), (-0.80, 2.04, 0), "brass", {}),
        ("arm.R", "box", (0.27, 0.54, 0.29), (-0.80, 1.60, 0), "iron", {}),
        ("forearm.R", "cyl", (0.20, 0.50), (-0.80, 1.14, 0.02), "iron", {"axis": "up"}),
        ("forearm.R", "box", (0.42, 0.34, 0.44), (-0.80, 0.80, 0.06), "brass", {}),
        ("forearm.R", "box", (0.44, 0.16, 0.32), (-0.80, 0.62, 0.10), "brass", {}),
        # legs
        ("thigh.L", "box", (0.35, 0.54, 0.37), (0.28, 0.86, 0), "iron", {}),
        ("shin.L", "box", (0.36, 0.15, 0.39), (0.28, 0.55, 0), "brass", {}),
        ("shin.L", "box", (0.33, 0.46, 0.35), (0.28, 0.30, 0), "iron", {}),
        ("foot.L", "box", (0.37, 0.14, 0.41), (0.28, 0.10, 0.02), "brass", {}),
        ("foot.L", "box", (0.46, 0.17, 0.64), (0.28, 0.05, 0.14), "iron", {}),
        ("thigh.R", "box", (0.35, 0.54, 0.37), (-0.28, 0.86, 0), "iron", {}),
        ("shin.R", "box", (0.36, 0.15, 0.39), (-0.28, 0.55, 0), "brass", {}),
        ("shin.R", "box", (0.33, 0.46, 0.35), (-0.28, 0.30, 0), "iron", {}),
        ("foot.R", "box", (0.37, 0.14, 0.41), (-0.28, 0.10, 0.02), "brass", {}),
        ("foot.R", "box", (0.46, 0.17, 0.64), (-0.28, 0.05, 0.14), "iron", {}),
    ],
}

D = math.radians



# ---------------------------------------------------------------- WC3 surface
def chamfer_cube(dims, at, rot, width):
    """A cube with its 12 edges chamfered: 6 + 12 quads and 8 corner tris (44 tris).
    This, not smooth shading alone, is what stops a model reading as Minecraft."""
    me = bpy.data.meshes.new("chamfer")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(dims), verts=bm.verts)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(width, 0.25 * min(dims)),
                    segments=1, affect="EDGES", profile=0.5)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new("chamfer", me)
    bpy.context.collection.objects.link(obj)
    obj.location = bp(at)
    obj.rotation_euler = (0, 0, rot)
    return obj


def soften(body, angle=48.0):
    """Smoothing groups by angle: every face smooth, every edge sharper than `angle`
    marked sharp. Flat faces stay flat, chamfers blend - the WC3 read."""
    bm = bmesh.new()
    bm.from_mesh(body.data)
    for f in bm.faces:
        f.smooth = True
    thr = math.radians(angle)
    for e in bm.edges:
        e.smooth = not (len(e.link_faces) == 2 and e.calc_face_angle(0.0) > thr)
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()


def shading_report(body):
    faces = len(body.data.polygons)
    smooth = sum(1 for p in body.data.polygons if p.use_smooth)
    sharp = sum(1 for e in body.data.edges if not e.use_edge_sharp)
    return f"{smooth}/{faces} faces smooth, {len(body.data.edges)} edges, {sharp} soft edges"

def bp(p):
    """Spec (right, up, forward) -> Blender (x, y, z); glTF then gives +Y up, +Z front."""
    return (p[0], -p[2], p[1])


def bd(d):
    """Same conversion for a size triple."""
    return (d[0], d[2], d[1])


def bf(v):
    """A direction along the spec forward axis, in Blender axes."""
    return (0, -1, 0)


def bu(v):
    """A direction along the spec up axis, in Blender axes."""
    return (0, 0, 1)


# ---------------------------------------------------------------- scene
def wipe():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 24


_MAT_CACHE = {}


def material(name):
    if name in _MAT_CACHE:
        return _MAT_CACHE[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = MATERIALS[name]
    bsdf.inputs["Roughness"].default_value = 0.85
    if name == "flame":
        bsdf.inputs["Emission Color"].default_value = MATERIALS[name]
        bsdf.inputs["Emission Strength"].default_value = 1.0
    _MAT_CACHE[name] = mat
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


BASE_TRIS = {"box": 12, "cyl": 44, "wheel": 80, "prism": 28, "dome": 28}
CHAMFER_EXTRA = 32  # a chamfered box is 44 tris instead of 12


def plan_chamfers(spec, budget):
    """Spend the spare triangles on the biggest masses first. WC3 SD models put the
    roundness in a few large chamfered volumes and the rest in painted texture; a
    chamfer on every box would triple the budget for nothing at 32 px."""
    room = budget - sum(BASE_TRIS[k] for _, k, *_ in spec)
    chosen = set()
    for dim, idx in sorted(((max(d), i) for i, (_, kind, d, *_ ) in enumerate(spec) if kind == "box"),
                           reverse=True):
        if room < CHAMFER_EXTRA:
            break
        chosen.add(idx)
        room -= CHAMFER_EXTRA
    return chosen


def prism(dims, at, rot, sides=8, axis="up"):
    """A tapered n-gon tube: the WC3 limb primitive. dims = (r_bottom, r_top, height).
    Eight sides read as round at 32 px and cost 28 tris (16 side + 12 cap)."""
    r0, r1, height = dims
    me = bpy.data.meshes.new("prism")
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=sides,
                          radius1=r0, radius2=r1, depth=height)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new("prism", me)
    bpy.context.collection.objects.link(obj)
    obj.location = bp(at)
    obj.rotation_euler = (D(90), 0, 0) if axis == "fwd" else (0, 0, rot)
    return obj


def build_part(bone, kind, dims, at, mat_name, opts, idx, chamfer=False):
    rot_z = D(opts.get("rot", 0.0))
    axis = opts.get("axis", "fwd")
    loc = bp(at)
    if kind in ("prism", "dome"):
        sides = int(opts.get("sides", 8))
        if kind == "dome":
            # a closed dome: taper hard to a small top cap instead of a sphere
            dims = (dims[0], dims[0] * float(opts.get("top", 0.35)), dims[1])
        obj = prism(dims, at, rot_z, sides=sides, axis=opts.get("axis", "up"))
        obj.name = f"{bone}_{idx}"
        obj.data.materials.append(material(mat_name))
        return obj
    if kind == "box":
        size = bd(dims)
        if chamfer:
            obj = chamfer_cube(size, at, rot_z, 0.02)
            obj.name = f"{bone}_{idx}"
            obj.data.materials.append(material(mat_name))
            return obj
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=(0, 0, rot_z))
        bpy.context.active_object.scale = size
    elif kind == "wheel":
        bpy.ops.mesh.primitive_torus_add(major_segments=10, minor_segments=4,
                                         major_radius=dims[0], minor_radius=dims[1],
                                         location=loc, rotation=(D(90), 0, 0))
    else:
        if axis == "up":
            # axis along the spec's up: cylinder default axis is +Z, already up
            bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=dims[0], depth=dims[1], location=loc)
        else:
            bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=dims[0], depth=dims[1],
                                                location=loc, rotation=(D(90), 0, 0))
    obj = bpy.context.active_object
    obj.name = f"{bone}_{idx}"
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material(mat_name))
    return obj




# ---------------------------------------------------------------- painted atlas
def painted_image(name, rgb, size=64):
    """Three tiles side by side: shadow, mid and lit. Each tile is the palette colour with
    the light painted in (vertical gradient, a crease, low-frequency mottle). Faces are
    mapped into one tile by height band, which is the cheap version of WC3's painted
    panels: value changes between parts without a single extra polygon."""
    width, height = size * 3, size
    img = bpy.data.images.new(f"tex_{name}", width=width, height=height, alpha=False)
    px = [0.0] * (width * height * 4)
    tones = (0.55, 0.85, 1.18)
    for x in range(width):
        tile = x // size
        u = (x % size) / (size - 1.0)
        for y in range(height):
            v = y / (height - 1.0)
            light = (0.82 + 0.30 * v) * tones[tile]
            crease = 1.0 - 0.16 * math.exp(-((v - 0.40) ** 2) / 0.0016)
            mottle = 1.0 + 0.045 * math.sin(u * 19.0 + v * 11.0) * math.sin(v * 7.0 + tile)
            k = light * crease * mottle
            i = (y * width + x) * 4
            px[i] = min(1.0, rgb[0] * k)
            px[i + 1] = min(1.0, rgb[1] * k)
            px[i + 2] = min(1.0, rgb[2] * k)
            px[i + 3] = 1.0
    img.pixels = px
    return img


def texturize(body, meta, size=256):
    """Per-part atlas: a 4x4 grid per material, one tile per body slot (pelvis, spine,
    head, arm, forearm, thigh, shin, foot), each painted with a trim band, a crease and
    mottling. Every face is mapped into the tile of the part it belongs to, so the paint
    separates panels the way a WC3 atlas does - with no extra polygons."""
    mesh = body.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    if mesh.uv_layers.active is None:
        mesh.uv_layers.active = mesh.uv_layers[0]
    uvs = mesh.uv_layers.active.data

    SLOTS = {"pelvis": 0, "spine": 1, "head": 2, "arm.L": 3, "arm.R": 3,
             "forearm.L": 4, "forearm.R": 4, "thigh.L": 5, "thigh.R": 5,
             "shin.L": 6, "shin.R": 6, "foot.L": 7, "foot.R": 7, "root": 0}

    def nearest_part(co):
        best, best_d = meta[0], 1e9
        for bone, mat_name, centre, half in meta:
            d = 0.0
            for a in range(3):
                delta = abs(co[a] - centre[a]) - half[a]
                if delta > 0:
                    d += delta * delta
            d += 0.02 * ((co[0] - centre[0]) ** 2 + (co[1] - centre[1]) ** 2 + (co[2] - centre[2]) ** 2)
            if d < best_d:
                best, best_d = (bone, mat_name, centre, half), d
        return best

    zs = [v.co.z for v in mesh.vertices] or [0.0, 1.0]
    z0, z1 = min(zs), max(zs)
    span = max(1e-4, z1 - z0)

    for poly in mesh.polygons:
        bone, mat_name, _, _ = nearest_part(poly.center)
        slot = SLOTS.get(bone, 1)
        tile_x, tile_y = slot % 4, slot // 4
        n = poly.normal
        axis = max(range(3), key=lambda i: abs(n[i]))
        band = min(1, int(2.0 * (poly.center.z - z0) / span))
        for li in poly.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            if axis == 2:
                lu, lv = co.x * 0.6, co.y * 0.6
            else:
                lu, lv = (co.x + co.y) * 0.6, co.z * 0.6
            u = (tile_x + 0.04 + 0.92 * (lu % 1.0)) / 4.0
            v = (tile_y + 0.04 + 0.92 * (lv % 1.0)) / 4.0
            uvs[li].uv = (u, v)

    images = {}
    for slot in body.material_slots:
        base = slot.material.name.split(".")[0]
        if base in images:
            slot.material = images[base]["material"]
            continue
        rgb = MATERIALS[base][:3]
        img = bpy.data.images.new(f"tex_{base}", width=size, height=size, alpha=False)
        px = [0.0] * (size * size * 4)
        cell = size // 4
        for x in range(size):
            tx, u = (x // cell), (x % cell) / (cell - 1.0)
            for y in range(size):
                ty = y // cell
                v = (y % cell) / (cell - 1.0)
                # WC3 read: one key light from above, 4:1 from shadow to highlight,
                # a narrow bright band as the trim, a dark crease low on the tile.
                ramp = 0.42 + 1.25 * (v ** 1.15)
                trim = 1.35 if 0.62 < v < 0.70 else 1.0
                crease = 1.0 - 0.30 * math.exp(-((v - 0.22) ** 2) / 0.0022)
                mottle = 1.0 + 0.07 * math.sin(u * 17 + tx) * math.sin(v * 9 + ty)
                k = ramp * trim * crease * mottle
                i = (y * size + x) * 4
                px[i] = min(1.0, rgb[0] * k)
                px[i + 1] = min(1.0, rgb[1] * k)
                px[i + 2] = min(1.0, rgb[2] * k)
                px[i + 3] = 1.0
        img.pixels = px
        nodes = slot.material.node_tree.nodes
        tex_node = nodes.new("ShaderNodeTexImage")
        tex_node.image = img
        bsdf = nodes["Principled BSDF"]
        # glTF multiplies baseColorFactor by the texture: leave the factor white or the
        # palette colour is applied twice and the model goes black.
        bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
        slot.material.node_tree.links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
        images[base] = {"material": slot.material, "image": img}
    return len(images)

# ---------------------------------------------------------------- fusion
def fuse(body, parts_meta, voxel=0.025, target=650, angle=52.0):
    """Turn a stack of primitives into ONE continuous shell, the way a WC3 model reads.

    Voxel remesh welds the overlapping parts into a single surface; decimate brings the
    count back to the budget; then every face and vertex is re-labelled from the part it
    came from, so the colour blocking and the bone binding survive the merge.

    parts_meta: [(bone, material_name, centre, half_extents)] in Blender space.
    """
    bpy.context.view_layer.objects.active = body
    body.data.remesh_voxel_size = voxel
    bpy.ops.object.voxel_remesh()

    faces = len(body.data.polygons)
    if faces:
        dec = body.modifiers.new("Decimate", "DECIMATE")
        dec.decimate_type = "COLLAPSE"
        dec.ratio = min(1.0, max(0.05, target / float(faces)))
        bpy.ops.object.modifier_apply(modifier=dec.name)

    # re-label: nearest part wins the face material and the vertex group
    mesh = body.data
    slots = {}
    for name, _ in [(m, None) for m in [p[1] for p in parts_meta]]:
        pass
    for i, (bone, mat_name, centre, half) in enumerate(parts_meta):
        if mat_name not in slots:
            slots[mat_name] = len(slots)
    body.data.materials.clear()
    for mat_name in slots:
        body.data.materials.append(material(mat_name))
    groups = {}
    for bone, *_ in parts_meta:
        if bone not in groups:
            groups[bone] = body.vertex_groups.new(name=bone)

    def nearest(co):
        # score = distance outside the part box + a tie-break on the distance to the
        # part centre; without the tie-break every surface point on a seam picks the
        # first part and the whole model comes out in one material.
        best, best_d = 0, 1e9
        for i, (bone, mat_name, centre, half) in enumerate(parts_meta):
            d = 0.0
            for a in range(3):
                delta = abs(co[a] - centre[a]) - half[a]
                if delta > 0:
                    d += delta * delta
            d += 0.02 * ((co[0] - centre[0]) ** 2 + (co[1] - centre[1]) ** 2 + (co[2] - centre[2]) ** 2)
            if d < best_d:
                best, best_d = i, d
        return parts_meta[best]

    for poly in mesh.polygons:
        bone, mat_name, _, _ = nearest(poly.center)
        poly.material_index = slots[mat_name]
        poly.use_smooth = True

    for v in mesh.vertices:
        bone, _, _, _ = nearest(v.co)
        groups[bone].add([v.index], 1.0, "REPLACE")

    thr = math.radians(angle)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    for e in bm.edges:
        e.smooth = not (len(e.link_faces) == 2 and e.calc_face_angle(0.0) > thr)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return len(mesh.polygons)

# ---------------------------------------------------------------- animation
# Blocking follows the blender-animation skill: key poses first (stepped), a
# breakdown between them, spline only at the end. Contacts and impacts get
# VECTOR handles; holds get AUTO_CLAMPED so they stay flat.
IDLE = {
    1: {"root": (0, 0, 0, 0.0), "spine": (0, 0, 0, 0.0), "head": (0, 0, 0, 0.0),
        "arm.L": (0, 0, 0, 0.0), "arm.R": (0, 0, 0, 0.0)},
    24: {"root": (0, 0, 0, 0.0), "spine": (-1.5, 0, 0, 0.0), "head": (0, 4, 0, 0.0),
         "arm.L": (2, 0, 0, 0.0), "arm.R": (-2, 0, 0, 0.0)},
    48: {"root": (0, 0, 0, 0.0), "spine": (0, 0, 0, 0.0), "head": (0, 0, 0, 0.0),
         "arm.L": (0, 0, 0, 0.0), "arm.R": (0, 0, 0, 0.0)},
}

# heavy two-step walk: contact 1/13, down 4/16, passing 7/19, up 10/22, loop 25
WALK = {
    1: {"thigh.L": (-26, 0, 0, 0), "shin.L": (16, 0, 0, 0), "foot.L": (-8, 0, 0, 0),
        "thigh.R": (22, 0, 0, 0), "shin.R": (22, 0, 0, 0), "foot.R": (14, 0, 0, 0),
        "arm.L": (14, 0, 0, 0), "arm.R": (-14, 0, 0, 0), "spine": (3, 0, 0, 0),
        "head": (-3, 0, 0, 0), "root": (0, 0, 0, -0.02)},
    4: {"thigh.L": (-14, 0, 0, 0), "shin.L": (24, 0, 0, 0), "foot.L": (0, 0, 0, 0),
        "thigh.R": (14, 0, 0, 0), "shin.R": (14, 0, 0, 0), "foot.R": (6, 0, 0, 0),
        "arm.L": (9, 0, 0, 0), "arm.R": (-9, 0, 0, 0), "spine": (5, 0, 0, 0),
        "head": (-2, 0, 0, 0), "root": (0, 0, 0, -0.06)},
    7: {"thigh.L": (0, 0, 0, 0), "shin.L": (10, 0, 0, 0), "foot.L": (0, 0, 0, 0),
        "thigh.R": (0, 0, 0, 0), "shin.R": (6, 0, 0, 0), "foot.R": (0, 0, 0, 0),
        "arm.L": (0, 0, 0, 0), "arm.R": (0, 0, 0, 0), "spine": (1, 0, 0, 0),
        "head": (0, 0, 0, 0), "root": (0, 0, 0, 0.02)},
    10: {"thigh.L": (16, 0, 0, 0), "shin.L": (6, 0, 0, 0), "foot.L": (10, 0, 0, 0),
         "thigh.R": (-18, 0, 0, 0), "shin.R": (12, 0, 0, 0), "foot.R": (-6, 0, 0, 0),
         "arm.L": (-9, 0, 0, 0), "arm.R": (9, 0, 0, 0), "spine": (3, 0, 0, 0),
         "head": (-2, 0, 0, 0), "root": (0, 0, 0, 0.0)},
    13: {"thigh.L": (22, 0, 0, 0), "shin.L": (22, 0, 0, 0), "foot.L": (14, 0, 0, 0),
         "thigh.R": (-26, 0, 0, 0), "shin.R": (16, 0, 0, 0), "foot.R": (-8, 0, 0, 0),
         "arm.L": (-14, 0, 0, 0), "arm.R": (14, 0, 0, 0), "spine": (3, 0, 0, 0),
         "head": (-3, 0, 0, 0), "root": (0, 0, 0, -0.02)},
    16: {"thigh.L": (14, 0, 0, 0), "shin.L": (14, 0, 0, 0), "foot.L": (6, 0, 0, 0),
         "thigh.R": (-14, 0, 0, 0), "shin.R": (24, 0, 0, 0), "foot.R": (0, 0, 0, 0),
         "arm.L": (-9, 0, 0, 0), "arm.R": (9, 0, 0, 0), "spine": (5, 0, 0, 0),
         "head": (-2, 0, 0, 0), "root": (0, 0, 0, -0.06)},
    19: {"thigh.L": (0, 0, 0, 0), "shin.L": (6, 0, 0, 0), "foot.L": (0, 0, 0, 0),
         "thigh.R": (0, 0, 0, 0), "shin.R": (10, 0, 0, 0), "foot.R": (0, 0, 0, 0),
         "arm.L": (0, 0, 0, 0), "arm.R": (0, 0, 0, 0), "spine": (1, 0, 0, 0),
         "head": (0, 0, 0, 0), "root": (0, 0, 0, 0.02)},
    22: {"thigh.L": (-18, 0, 0, 0), "shin.L": (12, 0, 0, 0), "foot.L": (-6, 0, 0, 0),
         "thigh.R": (16, 0, 0, 0), "shin.R": (6, 0, 0, 0), "foot.R": (10, 0, 0, 0),
         "arm.L": (9, 0, 0, 0), "arm.R": (-9, 0, 0, 0), "spine": (3, 0, 0, 0),
         "head": (-2, 0, 0, 0), "root": (0, 0, 0, 0.0)},
    25: {"thigh.L": (-26, 0, 0, 0), "shin.L": (16, 0, 0, 0), "foot.L": (-8, 0, 0, 0),
         "thigh.R": (22, 0, 0, 0), "shin.R": (22, 0, 0, 0), "foot.R": (14, 0, 0, 0),
         "arm.L": (14, 0, 0, 0), "arm.R": (-14, 0, 0, 0), "spine": (3, 0, 0, 0),
         "head": (-3, 0, 0, 0), "root": (0, 0, 0, -0.02)},
}

# piston thrust: settle, wind back (anticipation), snap, hold, recover
ATTACK = {
    1: {"root": (0, 0, 0, 0.0), "spine": (0, 0, 0, 0), "arm.R": (0, 0, 0, 0), "forearm.R": (0, 0, 0, 0),
        "arm.L": (0, 0, 0, 0), "head": (0, 0, 0, 0)},
    7: {"root": (0, 0, 0, -0.03), "spine": (7, 0, 0, 0), "arm.R": (26, 0, 0, 0), "forearm.R": (30, 0, 0, 0),
        "arm.L": (-10, 0, 0, 0), "head": (5, 0, 0, 0)},
    10: {"root": (0, 0, 0, 0.02), "spine": (-9, 0, 0, 0), "arm.R": (-30, 0, 0, 0), "forearm.R": (-78, 0, 0, 0),
         "arm.L": (16, 0, 0, 0), "head": (-8, 0, 0, 0)},
    16: {"root": (0, 0, 0, 0.01), "spine": (-8, 0, 0, 0), "arm.R": (-28, 0, 0, 0), "forearm.R": (-76, 0, 0, 0),
         "arm.L": (15, 0, 0, 0), "head": (-6, 0, 0, 0)},
    30: {"root": (0, 0, 0, 0.0), "spine": (0, 0, 0, 0), "arm.R": (0, 0, 0, 0), "forearm.R": (0, 0, 0, 0),
         "arm.L": (0, 0, 0, 0), "head": (0, 0, 0, 0)},
}

# stagger back, knees buckle, fall on the back, settle
DEATH = {
    1: {"root": (0, 0, 0, 0.0), "spine": (0, 0, 0, 0), "thigh.L": (0, 0, 0, 0), "thigh.R": (0, 0, 0, 0)},
    6: {"root": (0, 0, 0, 0.0), "spine": (12, 0, 0, 0), "thigh.L": (-10, 0, 0, 0), "thigh.R": (8, 0, 0, 0)},
    14: {"root": (18, 0, 0, -0.16), "spine": (16, 0, 0, 0), "thigh.L": (26, 0, 0, 0), "thigh.R": (20, 0, 0, 0)},
    26: {"root": (72, 0, 0, -0.62), "spine": (10, 0, 0, 0), "thigh.L": (34, 0, 0, 0), "thigh.R": (28, 0, 0, 0)},
    40: {"root": (86, 0, 0, -0.78), "spine": (4, 0, 0, 0), "thigh.L": (18, 0, 0, 0), "thigh.R": (14, 0, 0, 0)},
}

ACTIONS = [("idle", IDLE, True, (), ()), ("walk", WALK, True, (1, 5, 17, 21), (("head", 2), ("forearm.L", 1), ("forearm.R", 1))),
           ("attack", ATTACK, False, (10,), ()), ("death", DEATH, False, (26,), ())]


def load_spec(target):
    """Either a built-in id (SPECS) or a path to {"parts": [...]} JSON."""
    p = pathlib.Path(target)
    if p.suffix == ".json":
        parts = json.loads(p.read_text())["parts"]
        return p.stem, [tuple(x) for x in parts]
    if target not in SPECS:
        sys.exit(f"no spec for {target}")
    return target, SPECS[target]


def main():
    target, out = sys.argv[sys.argv.index("--") + 1:][:2]
    unit, spec = load_spec(target)
    wipe()
    arm = build_armature()

    # chamfer is opt-in: measured on n01X it inflated the plates and read worse than
    # the crisp blockout, because the WC3 roundness comes from painted shading, not
    # from geometry at this budget. Pass a triple budget as the third argument to enable.
    rest = sys.argv[sys.argv.index("--") + 1:]
    for arg in rest:
        if arg.startswith("pal="):  # pal=8A8F94,C9A46A,FFE600 overrides the palette
            for name, hexv in zip(("iron", "brass", "flame"), arg[4:].split(",")):
                MATERIALS[name] = tuple(int(hexv[i:i + 2], 16) / 255.0 for i in (0, 2, 4)) + (1.0,)
    chamfers = plan_chamfers(spec, int(rest[2])) if len(rest) > 2 else set()
    parts = []
    for idx, (bone, kind, dims, at, mat_name, opts) in enumerate(spec):
        parts.append((build_part(bone, kind, tuple(dims), tuple(at), mat_name, opts or {}, idx,
                                 idx in chamfers), bone))

    # rigid skin (one bone per piece, weight 1), then one joined mesh so the
    # engine draws a single mesh with three material slots
    bpy.ops.object.select_all(action="DESELECT")
    for obj, bone in parts:
        obj.vertex_groups.new(name=bone).add(range(len(obj.data.vertices)), 1.0, "REPLACE")
    meta = []
    for obj, bone in parts:
        mat_name = obj.data.materials[0].name.split(".")[0]
        corners = [Vector(c) for c in obj.bound_box]
        lo = Vector((min(c[i] for c in corners) for i in range(3)))
        hi = Vector((max(c[i] for c in corners) for i in range(3)))
        meta.append((bone, mat_name, (lo + hi) / 2, (hi - lo) / 2))
    for obj, _ in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0][0]
    bpy.ops.object.join()
    body = bpy.context.view_layer.objects.active
    body.name = body.data.name = unit

    if rest and len(rest) > 3 and rest[3] == "morph":
        faces = morph(body, target=int(rest[4]) if len(rest) > 4 else 650)
        print(f"morph: {faces} faces after subdiv + decimate")
    if rest and len(rest) > 5 and rest[5] == "tex":
        n = texturize(body, meta)
        print(f"texture: {n} painted tiles + world-space UVs")
    if rest and rest[3] == "fuse":
        faces = fuse(body, meta, target=int(rest[4]) if len(rest) > 4 else 650,
                     voxel=float(rest[6]) if len(rest) > 6 else 0.025)
        print(f"fused: {faces} faces after remesh + decimate")
    else:
        soften(body)
    print("shading:", shading_report(body))

    body.parent = arm
    body.modifiers.new("Armature", "ARMATURE").object = arm

    # animation: key poses stepped, breakdown, then spline
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
    arm.animation_data_create()

    anim = load_toolkit("blender-animation", "bx_anim")
    for name, poses, cyclic, contacts, lags in ACTIONS:
        act = bpy.data.actions.new(name)
        arm.animation_data.action = act
        frames = sorted(poses)
        for frame in frames:
            bpy.context.scene.frame_set(frame)
            for bone, (rx, ry, rz, ly) in poses[frame].items():
                pb = arm.pose.bones[bone]
                pb.rotation_euler = (D(rx), D(ry), D(rz))
                pb.location = (0, 0, ly)
                pb.keyframe_insert("rotation_euler", frame=frame)
                pb.keyframe_insert("location", frame=frame)
        # mid-keys between the poses so the motion has a breakdown, not a
        # straight interpolation; contacts stay VECTOR, holds stay flat
        for a, b in zip(frames, frames[1:]):
            if b - a >= 6:
                anim.breakdown(arm, a + (b - a) // 2, a, b, factor=0.5,
                               bones=list(poses[a]), keytype="BREAKDOWN")
        anim.set_interpolation(arm, interpolation="BEZIER", handle="AUTO_CLAMPED")
        act.use_fake_user = True
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.scene.frame_set(1)

    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_yup=True,
                              export_animations=True, export_animation_mode="ACTIONS",
                              export_apply=False, export_skins=True, export_morph=False)
    tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
    print(f"built {unit}: {len(parts)} parts joined, {len(BONES)} bones, "
          f"{len(ACTIONS)} actions, {len(body.data.polygons)} faces, ~{tris} tris, "
          f"{len(body.data.materials)} materials -> {out}")


def load_toolkit(skill, module):
    sys.path.append(str(pathlib.Path.home() / ".config/opencode/skills" / skill / "scripts"))
    return __import__(module)


if __name__ == "__main__":
    main()
