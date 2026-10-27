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
import mathutils
from mathutils import Vector

# ---------------------------------------------------------------- materials
MATERIALS = {
    # Sampled from the approved sheet, not invented: warm iron reads as painted
    # metal at 32 px; the blue-steel accent was what made v9 look like a toy.
    "iron": (0.431, 0.423, 0.408, 1.0),      # #6E6C68 concept iron
    "darkiron": (0.306, 0.251, 0.204, 1.0),  # #4E4034 waist, pelvis, straps
    "brass": (0.647, 0.506, 0.290, 1.0),     # #A5814A muted brass
    "flame": (1.000, 0.824, 0.290, 1.0),     # #FFD24A lamp / pilot light
}
# Keep the old spelling as a read-only alias so older specs still load.
MATERIALS["lamp"] = MATERIALS["flame"]
# material -> painted surface (surfaces.py). The n01X slots above are all "metal",
# so specs written before the palette existed paint exactly as they did.
SURFACE = {}
RAMP = None        # cel: tone change across a cell's vertical ramp (ramp=<x> on the CLI); None = surfaces.RAMP_SLOPE
STYLE = "painted"   # "cel": flat tone per face by orientation (surfaces.paint_cel); style=cel on the CLI
CLAY = False     # clay mode (arg `clay`): one grey material, no texture, decal or glow: the shape alone
CLAY_GREY = (0.62, 0.62, 0.62, 1.0)
RAMPS = {}       # material -> (p10, p90) luma of its sheet zone (palette "ramp"): the cel ramp's width
ALPHA = {}       # material -> opacity below 1: glass, flame tongues (glTF alphaMode BLEND)


def register_palette(palette):
    """A spec's {"slot": {"surface": "skin", "color": "#C08A5E"}}: colour sampled from
    the unit's own sheet, surface from the library. Overrides the n01X defaults."""
    for name, entry in (palette or {}).items():
        hexv = entry["color"].lstrip("#")
        MATERIALS[name] = tuple(int(hexv[i:i + 2], 16) / 255.0 for i in (0, 2, 4)) + (1.0,)
        SURFACE[name] = entry.get("surface", "metal")
        if float(entry.get("alpha", 1.0)) < 1.0:
            ALPHA[name] = float(entry["alpha"])
        if entry.get("ramp"):
            RAMPS[name] = tuple(entry["ramp"])

# ---------------------------------------------------------------- skeleton
# name, parent, head, tail   (spec space: right, up, forward)
_BIPED = [
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
BONES = list(_BIPED)
FAMILY = "biped"


def sibling(module):
    """A module from this folder, importable whether or not Blender put it on sys.path."""
    import importlib
    try:
        return importlib.import_module(module)
    except ModuleNotFoundError:
        import sys as _sys
        _sys.path.append(str(pathlib.Path(__file__).resolve().parent))
        return importlib.import_module(module)


def families():
    return sibling("rig_families")


def load_family(name, extras=None, measure=None):
    """Swap the rig family before building: a spec can ask for spider, quadruped...,
    plus its own prop bones (rig_families.with_extras). A spider spec's "rig_measure" (the
    sheet's numbers, silhouette.measure_spider) scales the skeleton."""
    fam = families()
    if measure and name in fam.SPIDERS:
        fam.scale_spider(name, measure)
    global BONES, BONE_MAP, FAMILY
    FAMILY = name if name in fam.FAMILIES else "biped"
    BONES = fam.with_extras(FAMILY, extras)
    BONE_MAP = {bone: (head, tail) for bone, _, head, tail in BONES}
    sibling("lathe_limb").set_rig(FAMILY, extras)
    return FAMILY

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

# The accepted draft is the source of truth; the literal above is the v9 history.
_REF = pathlib.Path(__file__).resolve().parents[2] / "artifacts/model-sheets/draft11/spec-n01X-v11.json"
if _REF.exists():
    SPECS["n01X"] = [tuple(p) for p in json.loads(_REF.read_text())["parts"]]

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
    rots = rot if isinstance(rot, (tuple, list)) else (0, 0, rot)
    rx, ry, rz = (math.radians(v) for v in rots)
    obj.rotation_euler = (rx, -rz, ry)  # spec right/up/forward -> Blender x/z/y
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


def clean_mesh(body, merge=0.001, angle=6.0):
    """MeshGPT-style pre-clean: weld vertices closer than `merge` (m), then dissolve coplanar
    faces within `angle` degrees, never across materials. Run before UVs/texture."""
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge)
    bm.to_mesh(body.data)
    bm.free()
    dec = body.modifiers.new("Planar", "DECIMATE")
    dec.decimate_type = "DISSOLVE"
    dec.angle_limit = math.radians(angle)
    dec.delimit = {"MATERIAL"}
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.modifier_apply(modifier=dec.name)


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


def srgb(rgb):
    """Blender and glTF store base colour in linear space; the palette is sampled
    in sRGB. Skipping this conversion is why the first renders looked chalk-white."""
    out = []
    for c in rgb[:3]:
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def material(name):
    if CLAY:
        MATERIALS["clay"] = CLAY_GREY
        name = "clay"
    if name in _MAT_CACHE:
        return _MAT_CACHE[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = srgb(MATERIALS[name])
    bsdf.inputs["Roughness"].default_value = 0.85
    if name in ALPHA:
        # opacity lives in the material, not the atlas: the glTF exporter writes it as
        # baseColorFactor alpha with alphaMode BLEND, and the atlas stays opaque RGB
        bsdf.inputs["Alpha"].default_value = ALPHA[name]
        mat.surface_render_method = "BLENDED"
    if name in ("flame", "lamp") or SURFACE.get(name) == "glow":
        bsdf.inputs["Emission Color"].default_value = srgb(MATERIALS[name])
        bsdf.inputs["Emission Strength"].default_value = 1.0
    _MAT_CACHE[name] = mat
    return mat


def build_armature(rest_pose=None):
    """Build the shared rig. `rest_pose` is an optional {bone: [rx, ry, rz]} in
    spec-space degrees; the bone is rotated around its head so an arm authored
    splayed outward also swings outward in the clips. Parts stay in world space:
    the bind pose is unchanged, only the animation axes move."""
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
        if rest_pose and name in rest_pose:
            rx, ry, rz = (D(v) for v in rest_pose[name])
            pivot = b.head.copy()
            rot = (mathutils.Matrix.Rotation(rx, 3, "X")
                   @ mathutils.Matrix.Rotation(rz, 3, "Z")
                   @ mathutils.Matrix.Rotation(ry, 3, "Y"))
            b.tail = pivot + rot @ (b.tail - pivot)
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


BASE_TRIS = {"box": 12, "frustum": 12, "cyl": 44, "wheel": 80, "prism": 28, "dome": 28,
             "ring": 144, "lathe": 68, "limb": 32, "plate": 28}
CHAMFER_EXTRA = 32  # a chamfered box is 44 tris instead of 12


def plan_chamfers(spec, budget):
    """Spend the spare triangles on the biggest masses first. WC3 SD models put the
    roundness in a few large chamfered volumes and the rest in painted texture; a
    chamfer on every box would triple the budget for nothing at 32 px."""
    LL = sibling("lathe_limb")
    room = budget - sum(LL.tris(k, o) if k == "chain" else BASE_TRIS[k] for _, k, _, _, _, o in spec)
    chosen = set()
    for dim, idx in sorted(((max(d), i) for i, (_, kind, d, *_ ) in enumerate(spec) if kind == "box"),
                           reverse=True):
        if room < CHAMFER_EXTRA:
            break
        chosen.add(idx)
        room -= CHAMFER_EXTRA
    return chosen


def prism(dims, at, rot=0.0, sides=8, axis="up", rot_euler=None):
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
    base = ((D(90), 0, 0) if axis == "fwd"
            else (0, D(90), 0) if axis == "side" else (0, 0, 0))
    if rot_euler is None:
        obj.rotation_euler = (base[0], base[1] - rot, base[2])
    else:
        rx, ry, rz = rot_euler
        obj.rotation_euler = (base[0] + rx, base[1] - rz, base[2] + ry)
    return obj


def frustum(dims, at, top=(1.0, 1.0), shift=(0.0, 0.0), rot=(0.0, 0.0, 0.0)):
    """A box with independent top scale and top offset: wedge boots, trapezoid
    pelvis, tapered fists. Six quads, 12 tris - the shape WC3 uses instead of
    bevelling every edge."""
    w, h, d = dims
    sx, sz = top
    dx, dz = shift
    hw, hd, hh = w / 2, d / 2, h / 2
    lo = [(-hw, -hd, -hh), (hw, -hd, -hh), (hw, hd, -hh), (-hw, hd, -hh)]
    hi = [(-hw * sx + dx, -hd * sz + dz, hh), (hw * sx + dx, -hd * sz + dz, hh),
          (hw * sx + dx, hd * sz + dz, hh), (-hw * sx + dx, hd * sz + dz, hh)]
    me = bpy.data.meshes.new("frustum")
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in lo + hi]
    bm.faces.new(vs[3::-1])                 # bottom
    bm.faces.new(vs[4:8])                   # top
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((vs[i], vs[j], vs[4 + j], vs[4 + i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new("frustum", me)
    bpy.context.collection.objects.link(obj)
    obj.location = bp(at)
    rx, ry, rz = (D(v) for v in rot)
    obj.rotation_euler = (rx, -rz, ry)
    return obj


def ring(dims, at, opts):
    """A flat annulus with optional radial spokes and a hub, built as one mesh.

    dims = (outer_radius, radial_width, thickness). This is the WC3 valve-wheel
    primitive: 10 sides, three spokes and an 8-sided hub is 144 tris and reads as
    a wheel from every view. `axis` picks the disc normal (up / fwd / side),
    `tilt` tips it around the lateral axis and `spin` rotates the spokes."""
    outer, width, thick = dims
    inner = max(outer - width, 0.01)
    sides = int(opts.get("sides", 10))
    spokes = int(opts.get("spokes", 0))
    hub_r = float(opts.get("hub", 0.0)) or (inner * 0.32 if spokes else 0.0)
    half = thick / 2
    bm = bmesh.new()
    rings = []
    for r in (outer, inner):
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / sides),
                                    r * math.sin(2 * math.pi * i / sides), z))
                      for z in (-half, half) for i in range(sides)])
    outer_lo, outer_hi = rings[0][:sides], rings[0][sides:]
    inner_lo, inner_hi = rings[1][:sides], rings[1][sides:]
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new((outer_lo[i], outer_lo[j], outer_hi[j], outer_hi[i]))
        bm.faces.new((inner_hi[i], inner_hi[j], inner_lo[j], inner_lo[i]))
        bm.faces.new((outer_hi[i], outer_hi[j], inner_hi[j], inner_hi[i]))
        bm.faces.new((inner_lo[i], inner_lo[j], outer_lo[j], outer_lo[i]))
    if spokes:
        span = inner - hub_r
        mid = (inner + hub_r) / 2
        for k in range(spokes):
            ang = D(90 + 360 * k / spokes)
            mat = (mathutils.Matrix.Translation((mid * math.cos(ang), mid * math.sin(ang), 0))
                   @ mathutils.Matrix.Rotation(ang, 4, "Z")
                   @ mathutils.Matrix.Diagonal((span, width * 0.72, thick * 0.8, 1)))
            bmesh.ops.create_cube(bm, size=1.0, matrix=mat)
    if hub_r:
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=8,
                              radius1=hub_r, radius2=hub_r, depth=thick)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("ring")
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new("ring", me)
    bpy.context.collection.objects.link(obj)
    obj.location = bp(at)
    axis = opts.get("axis", "up")
    base = mathutils.Quaternion((1, 0, 0), D(90)) if axis == "fwd" else (
        mathutils.Quaternion((0, 1, 0), D(90)) if axis == "side" else mathutils.Quaternion())
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = (base
                               @ mathutils.Quaternion((1, 0, 0), D(opts.get("tilt", 0.0)))
                               @ mathutils.Quaternion((0, 0, 1), D(opts.get("spin", 0.0))))
    return obj


def orient_between(obj, a, b):
    """Point a part's local +Z from spec point a to b. Limbs and feet stop being
    axis-aligned stacks: the spec can declare the two joints and the builder solves
    the angle, so the LLM never writes a placement number."""
    d = Vector(bp(b)) - Vector(bp(a))
    if d.length < 1e-6:
        return
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = d.to_track_quat("Z", "Y")


def fit_length(kind, dims, a, b, margin=1.08):
    length = (Vector(b) - Vector(a)).length * margin
    if kind == "prism":
        return (dims[0], dims[1], length)
    if kind == "cyl":
        return (dims[0], length)
    if kind in ("box", "frustum"):
        return (dims[0], length, dims[2])
    return dims


def extrude(poly, lo, hi, swap):
    """The outline `poly` of (a, y) points as a prism from `lo` to `hi` along the third spec axis;
    swap=False: a is x, the prism runs along z; swap=True: a is z, it runs along x."""
    me = bpy.data.meshes.new("cut")
    bm = bmesh.new()
    rings = [[bm.verts.new(bp((a, y, d) if not swap else (d, y, a))) for a, y in poly]
             for d in (lo, hi)]
    for ring_ in rings:
        bm.faces.new(ring_)
    n = len(poly)
    for i in range(n):
        bm.faces.new((rings[0][i], rings[0][(i + 1) % n], rings[1][(i + 1) % n], rings[1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new("cut", me)
    bpy.context.collection.objects.link(obj)
    return obj


def cut_part(bone, mat_name, idx):
    """A part cut by the sheet's silhouette (opts "cut"): the front outline extruded along z
    intersected with the left outline extruded along x (cut_hull.py made the outlines, fitted to
    the part's box). Sano 2026, visual hull."""
    cut = CUTS[str(idx)]
    lo, hi = cut["box"]
    m = [0.1 * (hi[a] - lo[a]) + 0.01 for a in range(3)]
    obj = extrude(cut["front"], lo[2] - m[2], hi[2] + m[2], False)
    other = extrude(cut["left"], lo[0] - m[0], hi[0] + m[0], True)
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new("Hull", "BOOLEAN")
    mod.operation = "INTERSECT"
    mod.solver = "EXACT"
    mod.object = other
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(other, do_unlink=True)
    if cut.get("dissolve"):             # a building's base volume: merge the coplanar triangles
        dis = obj.modifiers.new("Dissolve", "DECIMATE")
        dis.decimate_type, dis.angle_limit = "DISSOLVE", D(1.0)
        bpy.ops.object.modifier_apply(modifier=dis.name)
    obj.name = f"{bone}_{idx}"
    obj.data.materials.clear()          # the boolean leaves an empty slot behind
    obj.data.materials.append(material(mat_name))
    return obj


def swept_part(kind, dims, at, opts, name, idx, bone=None):
    """A lathe, limb, chain or plate (lathe_limb.py makes the rings): quads between consecutive rings,
    n-gon ends. A limb keeps its vertex order (from ring, knee ring, to ring) and a chain its (ring per
    joint) for the skin weights. A plate is built around its own origin at `at` and turned by opts rot
    like a box."""
    LL = sibling("lathe_limb")
    sheet = (CUTS.get(str(idx)) or {}).get("profile")
    rings = {"lathe": lambda: LL.lathe_rings(dims, at, opts, sheet),
             "chain": lambda: LL.chain_rings(bone, dims, opts, (CUTS.get(str(idx)) or {}).get("radii")),
             "plate": lambda: LL.plate_rings(dims, (0, 0, 0), opts, sheet)
             }.get(kind, lambda: LL.limb_rings(dims, opts))()
    me = bpy.data.meshes.new(kind)
    bm = bmesh.new()
    grid = [[bm.verts.new(bp(p)) for p in ring_] for ring_ in rings]
    n = len(grid[0])
    for lo, hi in zip(grid, grid[1:]):
        for i in range(n):
            bm.faces.new((lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]))
    for cap in (grid[0], grid[-1]):
        bm.faces.new(cap)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    if kind == "limb":
        obj["limb_sides"] = n
    if kind == "chain":
        obj["chain_bones"] = LL.chain_bones(bone, opts["bones"])
        obj["chain_sides"] = n
    if kind == "plate":
        rots = opts.get("rot", 0.0)
        rx, ry, rz = (D(v) for v in ((0.0, 0.0, rots) if isinstance(rots, (int, float)) else rots))
        obj.location, obj.rotation_euler = bp(at), (rx, -rz, ry)
    return obj


def skin_part(obj, bone):
    """Rigid skin: weight 1 on the part's bone. A limb whose rig has an upper/lower pair
    (leg1.upper/.lower, thigh/shin, arm/forearm) weights its upper tube on the upper bone, its lower
    tube on the lower bone and the knee ring half and half, so the knee bends. A chain weights
    ring i (n vertices) on bone i, the last ring on the last bone."""
    if obj.get("chain_bones"):
        n, names = obj["chain_sides"], list(obj["chain_bones"])
        for i, b in enumerate(names):
            end = len(obj.data.vertices) if i == len(names) - 1 else (i + 1) * n
            obj.vertex_groups.new(name=b).add(range(i * n, end), 1.0, "REPLACE")
        return
    n = obj.get("limb_sides")
    pair = sibling("lathe_limb").limb_bones(bone, {b[0] for b in BONES}) if n else None
    if not pair:
        obj.vertex_groups.new(name=bone).add(range(len(obj.data.vertices)), 1.0, "REPLACE")
        return
    up, low = (obj.vertex_groups.new(name=b) for b in pair)
    up.add(range(0, 2 * n), 1.0, "REPLACE")
    up.add(range(n, 2 * n), 0.5, "REPLACE")
    low.add(range(n, 3 * n), 1.0, "REPLACE")
    low.add(range(n, 2 * n), 0.5, "REPLACE")


def build_part(bone, kind, dims, at, mat_name, opts, idx, chamfer=False):
    rots = opts.get("rot", 0.0)
    if isinstance(rots, (int, float)):
        rots = (0.0, 0.0, rots)
    rx, ry, rz = (D(v) for v in rots)
    rot_z = rz  # legacy: a single number means "turn around the forward axis"
    axis = opts.get("axis", "fwd")
    has_span = "from" in opts and "to" in opts
    a = b = None
    if has_span:
        a, b = tuple(opts["from"]), tuple(opts["to"])
        at = tuple((a[i] + b[i]) / 2 for i in range(3))
        if opts.get("fit", True):
            dims = fit_length(kind, dims, a, b)
    loc = bp(at)
    if kind in ("prism", "dome"):
        sides = int(opts.get("sides", 8))
        if kind == "dome":
            # a closed dome: taper hard to a small top cap instead of a sphere
            dims = (dims[0], dims[0] * float(opts.get("top", 0.35)), dims[1])
        obj = prism(dims, at, rot_z, sides=sides, axis=opts.get("axis", "up"),
                    rot_euler=(rx, ry, rz))
        if opts.get("spin"):
            obj.rotation_euler.z += D(float(opts["spin"]))
        if opts.get("scale"):
            obj.scale = (float(opts["scale"][0]), float(opts["scale"][1]), 1.0)
        obj.name = f"{bone}_{idx}"
        obj.data.materials.append(material(mat_name))
        if has_span:
            orient_between(obj, a, b)
        return obj
    if kind == "ring":
        obj = ring(dims, at, opts)
        obj.name = f"{bone}_{idx}"
        obj.data.materials.append(material(mat_name))
        return obj
    if kind == "frustum":
        obj = frustum(dims, at, top=opts.get("top", (1.0, 1.0)),
                      shift=opts.get("shift", (0.0, 0.0)), rot=rots)
        if opts.get("spin"):
            obj.rotation_euler.z += D(float(opts["spin"]))
        if opts.get("scale"):
            obj.scale = (float(opts["scale"][0]), float(opts["scale"][1]), 1.0)
        obj.name = f"{bone}_{idx}"
        obj.data.materials.append(material(mat_name))
        if has_span:
            orient_between(obj, a, b)
        return obj
    if kind == "box":
        size = bd(dims)
        if chamfer and not has_span:
            obj = chamfer_cube(size, at, rots, 0.02)
            obj.name = f"{bone}_{idx}"
            obj.data.materials.append(material(mat_name))
            return obj
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=(rx, -rz, ry))
        bpy.context.active_object.scale = size
    elif kind == "wheel":
        bpy.ops.mesh.primitive_torus_add(major_segments=10, minor_segments=4,
                                         major_radius=dims[0], minor_radius=dims[1],
                                         location=loc)
        obj = bpy.context.active_object
        base = mathutils.Quaternion((1, 0, 0), D(90)) if axis == "fwd" else (
            mathutils.Quaternion((0, 1, 0), D(90)) if axis == "side" else mathutils.Quaternion())
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = base @ mathutils.Quaternion((1, 0, 0), D(opts.get("tilt", 0.0)))
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
    if has_span:
        orient_between(obj, a, b)
    return obj





# ---------------------------------------------------------------- skeleton-first spec
BONE_MAP = {name: (head, tail) for name, parent, head, tail in BONES}


def resolve_skeleton(spec):
    """A spec that names a bone and a radius, nothing else. Placement, length and
    overlap come from the rig, so the first build is already connected - the LLM
    cannot put a limb in the wrong place because it never writes a coordinate."""
    parts = []

    def mid_len(head, tail):
        mid = tuple((head[i] + tail[i]) / 2 for i in range(3))
        length = sum((tail[i] - head[i]) ** 2 for i in range(3)) ** 0.5
        return mid, length

    for seg in spec.get("segments", []):
        bone = seg["bone"]
        head, tail = BONE_MAP[bone]
        mid, length = mid_len(head, tail)
        L = length * float(seg.get("extend", 1.15))
        kind = seg.get("kind", "prism")
        if kind in ("prism", "dome"):
            r0, r1 = seg.get("radius", (0.12, 0.10))
            dims = (r0, r1, L) if kind == "prism" else (r0, L)
        else:
            dims = tuple(seg["dims"])
        opts = {k: v for k, v in seg.items() if k in ("sides", "axis", "rot", "top")}
        parts.append([bone, kind, list(dims), list(mid), seg.get("material", "iron"), opts])

    for ex in spec.get("extras", []):
        bone = ex["bone"]
        head, tail = BONE_MAP[bone]
        off = ex.get("offset", (0, 0, 0))
        at = tuple(head[i] + off[i] for i in range(3))
        opts = {k: v for k, v in ex.items() if k in ("sides", "axis", "rot", "top")}
        parts.append([bone, ex.get("kind", "box"), list(ex["dims"]), list(at),
                      ex.get("material", "iron"), opts])
    return parts


def validate_skeleton(spec, budget=700):
    """Hard invariants a first build must satisfy. Prints one line per rule."""
    parts = resolve_skeleton(spec)
    est = sum(BASE_TRIS.get(p[1], 12) for p in parts) + sum(
        12 if p[5].get("sides", 8) > 6 else 0 for p in parts if p[1] == "prism")
    bones_covered = {p[0] for p in parts}
    required = {"pelvis", "spine", "head", "arm.L", "forearm.L", "thigh.L", "shin.L", "foot.L"}
    missing = required - bones_covered
    zs = [p[3][1] for p in parts]
    xs = [abs(p[3][0]) for p in parts]
    shoulder = max(xs) * 2
    height = max(zs) + 0.3
    print(f"  parts {len(parts)} | tris ~{est} (budget {budget}) | bones {len(bones_covered)}")
    print(f"  shoulder/height {shoulder / height:.2f} (sheet 0.62) | "
          f"head at {max(z for z in zs):.2f} of {height:.2f}")
    print(f"  missing bones: {sorted(missing) or 'none'}")
    return not missing and est <= budget


def merge_clips(base, extra):
    """Clip lists merged by name: frames are united and bone poses overlaid, so a
    harpy keeps the biped's walk and adds its wing flap."""
    extra = {name: poses for name, poses, *_ in extra}
    out = []
    for name, poses, cyclic, contacts, lags in base:
        merged = {f: dict(pose) for f, pose in poses.items()}
        for f, pose in extra.get(name, {}).items():
            merged.setdefault(f, {}).update(pose)
        out.append((name, merged, cyclic, contacts, lags))
    return out


ANIM = None     # the spec's "anim": {"attack": "chop", ...} picks from rig_motions; "legacy" = old clips


def clip_set(family, anim=None):
    """The motion library (rig_motions: clips retargeted from reference animations, plus
    a spell clip) by default, picks overridden by the spec's "anim". "anim": "legacy"
    keeps the old clips: biped hand-keyed tables, families with biped limbs those plus
    the clips derived from their other bones, everything else the derived clips."""
    fam = families()
    motions = sibling("rig_motions")
    if anim != "legacy" and family in motions.DEFAULTS:
        return motions.clips(family, anim if isinstance(anim, dict) else None)
    if family == "biped":
        return ACTIONS
    if fam.has_biped_limbs(family):
        return merge_clips(ACTIONS, fam.actions(family))
    return fam.actions(family)


def make_actions(arm):
    """The unit's clips (clip_set): key poses stepped, a hand-made breakdown, then spline."""
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
    arm.animation_data_create()
    anim = load_toolkit("blender-animation", "bx_anim")
    clips = clip_set(FAMILY, ANIM)
    for name, poses, cyclic, contacts, lags in clips:
        act = bpy.data.actions.new(name)
        arm.animation_data.action = act
        frames = sorted(poses)
        for frame in frames:
            bpy.context.scene.frame_set(frame)
            for bone, (rx, ry, rz, ly, *up) in poses[frame].items():
                if bone not in arm.pose.bones:
                    continue
                pb = arm.pose.bones[bone]
                pb.rotation_euler = (D(rx), D(ry), D(rz))
                pb.location = (0, up[0] if up else 0, ly)       # up: along the bone (rig_poses)
                pb.keyframe_insert("rotation_euler", frame=frame)
                pb.keyframe_insert("location", frame=frame)
        for a, b in zip(frames, frames[1:]):
            if b - a >= 6:
                anim.breakdown(arm, a + (b - a) // 2, a, b, factor=0.5,
                               bones=[x for x in poses[a] if x in arm.pose.bones])
        anim.set_interpolation(arm, interpolation="BEZIER", handle="AUTO_CLAMPED")
        act.use_fake_user = True
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.scene.frame_set(1)


# ---------------------------------------------------------------- skin body
def build_skin_body(spec, target=620, subdiv=1):
    """One continuous skin around the skeleton, not a stack of primitives.

    A vertex chain is laid on the bones (a vertex per joint), the Skin modifier grows
    a quad shell around it with the radius of each segment, one subdivision rounds the
    joints and a decimate brings it back to the budget. This is the "skin around a
    skeleton" that WC3 and PS1 bodies are: one surface, no visible part seams.
    """
    rad = {}
    verts, index, edges = [], {}, []

    def vid(p):
        key = tuple(round(c, 4) for c in p)
        if key not in index:
            index[key] = len(verts)
            verts.append(bp(p))
        return index[key]

    for seg in spec.get("segments", []):
        bone = seg["bone"]
        head, tail = BONE_MAP[bone]
        r0, r1 = seg.get("radius", (0.14, 0.12))
        h, tl = vid(head), vid(tail)
        edges.append((h, tl))
        rad.setdefault(h, []).append(r0)
        rad.setdefault(tl, []).append(r1)

    # the Skin modifier grows one continuous surface only when every chain is part
    # of the same graph: bridge each limb root to the torso, then mark the root.
    joints = {b: BONE_MAP[b] for b, *_ in [(seg["bone"],) for seg in spec.get("segments", [])] if b in BONE_MAP}
    anchor = vid(BONE_MAP["spine"][1]) if "spine" in BONE_MAP else None
    for limb in ("arm.L", "arm.R", "thigh.L", "thigh.R"):
        if limb in BONE_MAP and anchor is not None:
            edges.append((vid(BONE_MAP[limb][0]), anchor))
    if "forearm.L" in BONE_MAP:
        pass

    me = bpy.data.meshes.new("skinbody")
    me.from_pydata(verts, edges, [])
    me.update()
    obj = bpy.data.objects.new("skinbody", me)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj

    skin_mod = obj.modifiers.new("Skin", "SKIN")
    skin_mod.use_smooth_shade = True
    layer = me.skin_vertices[0].data
    root_idx = vid(BONE_MAP["pelvis"][0]) if "pelvis" in BONE_MAP else 0
    layer[root_idx].use_root = True
    for i in range(len(me.vertices)):
        r = sum(rad.get(i, [0.12])) / len(rad.get(i, [0.12]))
        layer[i].radius = (r, r)
    bpy.ops.object.modifier_apply(modifier=skin_mod.name)

    if subdiv:
        sub = obj.modifiers.new("Sub", "SUBSURF")
        sub.levels = sub.render_levels = subdiv
        bpy.ops.object.modifier_apply(modifier=sub.name)
    faces = len(obj.data.polygons)
    if faces > target:
        dec = obj.modifiers.new("Dec", "DECIMATE")
        dec.decimate_type = "DISSOLVE"    # merge coplanar faces, keep the facets
        dec.angle_limit = math.radians(12)
        bpy.ops.object.modifier_apply(modifier=dec.name)
    faces = len(obj.data.polygons)
    if faces > target:
        dec = obj.modifiers.new("Dec2", "DECIMATE")
        dec.decimate_type = "COLLAPSE"
        dec.ratio = max(0.05, target / float(faces))
        bpy.ops.object.modifier_apply(modifier=dec.name)

    # material and rigid weights by nearest bone segment, so the shell keeps the
    # palette blocking and still deforms rigidly at the joints
    segs = [(seg["bone"], seg.get("material", "iron"), BONE_MAP[seg["bone"]])
            for seg in spec.get("segments", [])]
    mats = {}
    for _, m, _ in segs:
        if m not in mats:
            mats[m] = len(mats)
    obj.data.materials.clear()
    for m in mats:
        obj.data.materials.append(material(m))
    groups = {b: obj.vertex_groups.new(name=b) for b, _, _ in segs}

    def nearest(co):
        best, bd = segs[0], 1e9
        for bone, m, (h, tl) in segs:
            hb, tb = Vector(bp(h)), Vector(bp(tl))
            ab, ap = tb - hb, co - hb
            t = max(0.0, min(1.0, ab.dot(ap) / max(ab.length_squared, 1e-9)))
            d = (hb + ab * t - co).length
            if d < bd:
                best, bd = (bone, m), d
        return best

    for poly in obj.data.polygons:
        _, m = nearest(poly.center)
        poly.material_index = mats[m]
        poly.use_smooth = True
    for v in obj.data.vertices:
        b, _ = nearest(v.co)
        groups[b].add([v.index], 1.0, "REPLACE")
    return obj


# ---------------------------------------------------------------- union + junction
CHAIN_OF = {"pelvis": "torso", "spine": "torso", "head": "torso",
            "arm.L": "armL", "forearm.L": "armL", "arm.R": "armR", "forearm.R": "armR",
            "thigh.L": "legL", "shin.L": "legL", "foot.L": "legL",
            "thigh.R": "legR", "shin.R": "legR", "foot.R": "legR"}


def union_decimate(body_u, faces_budget, tolerance):
    """Decimate the unioned shell: blind to the face budget, or (`toldec`, PIPELINE 20.M12)
    as far as it stays within height/32 of its own surface. Logs the deviation either way."""
    print("union decimate:", sibling("cull").decimate_union(body_u, faces_budget, blind=not tolerance))


def union_parts(parts, meta, per_chain=False):
    """Boolean-union the plates into one connected shell so the junctions stop showing
    as steps and teeth, then bevel the new intersection edges. Keeps the hard-surface
    read (unlike a remesh) and keeps per-part materials through the material indices."""
    groups = {}
    for obj, bone in parts:
        key = CHAIN_OF.get(bone, bone) if per_chain else "all"
        groups.setdefault(key, []).append(obj)
    merged = []
    for key, objs in groups.items():
        base = objs[0]
        bpy.context.view_layer.objects.active = base
        for obj in objs[1:]:
            mod = base.modifiers.new("Bool", "BOOLEAN")
            mod.operation = "UNION"
            mod.solver = "EXACT"
            mod.object = obj
            bpy.ops.object.modifier_apply(modifier=mod.name)
            bpy.data.objects.remove(obj, do_unlink=True)
        merged.append(base)
    return merged

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


CUTS = {}        # (arg cuts=<json>) {part index: outlines} of the parts with opts "cut", {"profile"} of a lathe (cut_hull.py)
FACE = None      # (arg face=<png>) RGBA array of the approved sheet's head, the "sheet" decal
DECALS = []      # (centre, half, kind, colour, side, owner) of parts whose front face (side 1; a back prop: -1) carries a decal;
#                  owner = the part's meta entry for a prop crop (only that part's faces wear it), else None


def decal_uv(centre_w, normal_w, co, near=None):
    """(cell, u, v) when this face (world centre and normal) is the front of a decal
    part, else None. The front is projected over the part's box, so the decal lands
    where it was placed. `near` = the meta entry nearest the face: a prop crop is worn by its own part only."""
    for i, (centre, half, _, _, side, owner) in enumerate(DECALS):
        if normal_w.y * side > -0.5 or (owner is not None and owner != near):   # front faces look down -Y in Blender
            continue
        if all(abs(centre_w[a] - centre[a]) <= half[a] * 1.02 + 1e-4 for a in range(3)):
            u = (co.x - centre.x + half.x) / max(2 * half.x, 1e-6)
            return 8 + i, (u if side > 0 else 1.0 - u), (co.z - centre.z + half.z) / max(2 * half.z, 1e-6)
    return None


TEX_SLOTS = {"pelvis": 0, "spine": 1, "head": 2, "arm.L": 3, "arm.R": 3,
             "forearm.L": 4, "forearm.R": 4, "thigh.L": 5, "thigh.R": 5,
             "shin.L": 6, "shin.R": 6, "foot.L": 7, "foot.R": 7, "root": 0}


def nearest_part(meta, co):
    """The (bone, material, centre, half) part whose box is closest to `co`."""
    best, best_d = meta[0], 1e9
    for bone, mat_name, centre, half in meta:
        d = sum(max(0.0, abs(co[a] - centre[a]) - half[a]) ** 2 for a in range(3))
        d += 0.02 * sum((co[a] - centre[a]) ** 2 for a in range(3))
        if d < best_d:
            best, best_d = (bone, mat_name, centre, half), d
    return best


def relative_height(meta, co):
    """0 (bottom) .. 1 (top) of `co` inside the vertical extent of the part nearest to it."""
    _, _, centre, half = nearest_part(meta, co)
    return min(1.0, max(0.0, 0.5 + 0.5 * (co[2] - centre[2]) / max(half[2], 1e-6)))


def face_span(mesh, poly, axis):
    """(u, v) per loop of `poly`, its corners normalised over the face's own box in the
    plane of its dominant axis, so a cel face spans its whole cell and the cell's border
    (the ink line) lands on the face's edges."""
    pts = []
    for li in poly.loop_indices:
        co = mesh.vertices[mesh.loops[li].vertex_index].co
        pts.append((co.x, co.y) if axis == 2 else ((co.y, co.z) if axis == 0 else (co.x, co.z)))
    lo = [min(q[i] for q in pts) for i in (0, 1)]
    span = [max(max(q[i] for q in pts) - lo[i], 1e-6) for i in (0, 1)]
    return [((q[0] - lo[0]) / span[0], (q[1] - lo[1]) / span[1]) for q in pts]


def atlas_uvs(body, meta, block, cols, rows):
    """World-planar UVs per face, into the body-slot cell of its material's block.
    Bipeds use TEX_SLOTS; other rig families spread their bones over the same 8 cells."""
    SF = sibling("surfaces")
    mesh = body.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    if mesh.uv_layers.active is None:
        mesh.uv_layers.active = mesh.uv_layers[0]
    uvs = mesh.uv_layers.active.data
    order = {name: i % 8 for i, (name, *_) in enumerate(BONES)}
    slot_base = [ms.material.name.split(".")[0] for ms in body.material_slots]
    world, turn = body.matrix_world, body.matrix_world.to_3x3()   # meta is in world space
    for poly in mesh.polygons:
        centre_w, normal_w = world @ poly.center, (turn @ poly.normal).normalized()
        near = nearest_part(meta, centre_w)
        bone = near[0]
        cell = TEX_SLOTS.get(bone, order.get(bone, 1))
        bx, by = block[slot_base[poly.material_index]]
        tile_x, tile_y = bx * 4 + cell % 4, by * 4 + cell // 4
        axis = max(range(3), key=lambda i: abs(poly.normal[i]))
        if STYLE == "cel":                      # the face's tone cell and ramp slot, flat per face
            cell = SF.tone_index(normal_w.z)
            tile_x, tile_y = bx * 4 + cell % 4, by * 4 + cell // 4
            slot = SF.ramp_slot(normal_w.z, relative_height(meta, centre_w),
                                all(abs(c) > 0.3 for c in normal_w))
        span = face_span(mesh, poly, axis) if STYLE == "cel" else None
        for k, li in enumerate(poly.loop_indices):
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            lu, lv = (co.x * 0.6, co.y * 0.6) if axis == 2 else ((co.x + co.y) * 0.6, co.z * 0.6)
            dec = decal_uv(centre_w, normal_w, world @ co, near)
            if dec:
                cell, du, dv = dec
                tx, ty = bx * 4 + cell % 4, by * 4 + cell // 4
                uvs[li].uv = ((tx + 0.04 + 0.92 * du) / (4.0 * cols), (ty + 0.04 + 0.92 * dv) / (4.0 * rows))
                continue
            if span:                           # cel: the whole ramp slot, ink border included
                uvs[li].uv = ((tile_x + 0.01 + 0.98 * span[k][0]) / (4.0 * cols),
                              (tile_y + SF.slot_v(slot, span[k][1])) / (4.0 * rows))
                continue
            uvs[li].uv = ((tile_x + 0.04 + 0.92 * (lu % 1.0)) / (4.0 * cols),
                          (tile_y + 0.04 + 0.92 * (lv % 1.0)) / (4.0 * rows))


def bind_atlas(body, img):
    """Every material samples the atlas; duplicates of a palette slot are merged."""
    seen = {}
    for slot in body.material_slots:
        base = slot.material.name.split(".")[0]
        if base in seen:
            slot.material = seen[base]
            continue
        nodes = slot.material.node_tree.nodes
        tex_node = nodes.new("ShaderNodeTexImage")
        tex_node.image = img
        bsdf = nodes["Principled BSDF"]
        # glTF multiplies baseColorFactor by the texture: leave the factor white or the
        # palette colour is applied twice and the model goes black.
        bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
        slot.material.node_tree.links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
        if STYLE == "cel":
            tex_node.interpolation = "Closest"   # point filter: flat slots, exported as a NEAREST sampler
        seen[base] = slot.material


def sheet_face(cell):
    """(rgb, alpha) of the sheet's head sampled to a cell x cell decal (nearest); FACE is
    already bottom-up, as Blender hands pixels over and the atlas stores them."""
    import numpy as np
    idx = ((np.arange(cell) + 0.5) * FACE.shape[0] / cell).astype(int)
    face = FACE[idx][:, idx]
    return face[..., :3], face[..., 3]


def crop_face(path, cell, upright):
    """(rgb, alpha) of a props-sheet crop sampled to a cell x cell decal (nearest), bottom-up like the atlas;
    the background is the colour of the crop's border: transparent where a pixel is close to it. The sheet
    draws a club or a spear lying down: on an `upright` part a wider-than-tall crop is turned a quarter, head up."""
    import numpy as np
    img = bpy.data.images.load(path, check_existing=True)
    px = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4)[..., :3]
    if upright and px.shape[1] > 1.2 * px.shape[0]:
        px = np.rot90(px, -1)           # rows run bottom-up: -1 sends the right edge to the top
    border = np.median(np.concatenate([px[0], px[-1], px[:, 0], px[:, -1]]), axis=0)
    alpha = (np.abs(px - border).max(axis=-1) > 0.12).astype(np.float32)
    idx_y = ((np.arange(cell) + 0.5) * px.shape[0] / cell).astype(int)
    idx_x = ((np.arange(cell) + 0.5) * px.shape[1] / cell).astype(int)
    return px[idx_y][:, idx_x], alpha[idx_y][:, idx_x]


def paint_decals(pixels, SF, x0, y0, size):
    """Paint each decal into its spare cell (8 + i) of one material block."""
    cell = size // 4
    for i, (_, half, kind, colour, _, _) in enumerate(DECALS):
        rgb = None
        if colour and kind != "propcrop":
            hexv = colour.lstrip("#")
            rgb = tuple(int(hexv[k:k + 2], 16) / 255.0 for k in (0, 2, 4))
        if kind == "propcrop":
            paint, alpha = crop_face(colour, cell, half.z > 1.3 * half.x)
        else:
            paint, alpha = sheet_face(cell) if kind == "sheet" else SF.decal(kind, rgb, cell)
        cx, cy = x0 + ((8 + i) % 4) * cell, y0 + ((8 + i) // 4) * cell
        region = pixels[cy:cy + cell, cx:cx + cell, :3]
        region[:] = region * (1 - alpha[..., None]) + paint * alpha[..., None]


def paint_slot(SF, base, size):
    """The size x size image of one material slot in the current style. A cel ramp comes from the
    command line (ramp=), else from the slot's measured palette ramp, else it is flat."""
    surface, rgb = SURFACE.get(base, "metal"), MATERIALS[base][:3]
    if STYLE != "cel":
        return SF.paint(surface, rgb, size)
    if RAMP is None and base in RAMPS:
        return SF.paint_cel(surface, rgb, size, slope=SF.ramp_slope(RAMPS[base], rgb))
    return SF.paint_cel(surface, rgb, size) if RAMP is None else SF.paint_cel(surface, rgb, size, slope=RAMP)


def texturize(body, meta, size=256):
    """One painted atlas per unit. Each material slot gets a size x size block of the
    atlas, painted by its surface (surfaces.py: metal plates, skin, cloth, scales...)
    as a 4x4 grid of cells, one per body slot; every face is mapped into the cell of
    the part it belongs to, so the paint separates panels the way a WC3 atlas does -
    with no extra polygons. The materials stay separate (gates count them) but all
    sample the same image, so the GLB carries one texture."""
    import numpy as np
    SF = sibling("surfaces")
    bases = list(dict.fromkeys(ms.material.name.split(".")[0] for ms in body.material_slots))
    cols, rows = SF.atlas_layout(len(bases))
    block = {b: (i % cols, i // cols) for i, b in enumerate(bases)}
    atlas_uvs(body, meta, block, cols, rows)
    pixels = np.ones((rows * size, cols * size, 4))
    for base, (bx, by) in block.items():
        pixels[by * size:(by + 1) * size, bx * size:(bx + 1) * size, :3] = paint_slot(SF, base, size)
        paint_decals(pixels, SF, bx * size, by * size, size)
    img = bpy.data.images.new("tex_atlas", width=cols * size, height=rows * size, alpha=False)
    img.pixels.foreach_set(pixels.astype(np.float32).ravel())
    bind_atlas(body, img)
    return len(bases)


ATLAS_SLOTS = {"pelvis": 2, "spine": 1, "head": 0,
               "arm.L": 3, "arm.R": 3, "forearm.L": 4, "forearm.R": 4,
               "thigh.L": 5, "thigh.R": 5, "shin.L": 6, "shin.R": 6,
               "foot.L": 7, "foot.R": 7, "root": 2}


def texturize_atlas(body, meta, atlas_path, cols=4, rows=2):
    """Project a per-part crop atlas (concept tiles) onto the joined mesh.

    Unlike texturize(), the tile content is painted art, not a sine mottle, and each
    part is mapped inside its own crop, so the background of the sheet cannot bleed
    onto the model. Faces use a box projection in part-local space; left/right parts
    share a tile with mirrored U."""
    mesh = body.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    uv = mesh.uv_layers.active.data
    img = bpy.data.images.load(str(atlas_path), check_existing=True)

    def nearest_part(co):
        best, best_d = meta[0], 1e9
        for m in meta:
            bone, mat_name, centre, half = m
            d = 0.0
            for a in range(3):
                delta = abs(co[a] - centre[a]) - half[a]
                if delta > 0:
                    d += delta * delta
            d += 0.02 * sum((co[i] - centre[i]) ** 2 for i in range(3))
            if d < best_d:
                best, best_d = m, d
        return best

    for poly in mesh.polygons:
        bone, mat_name, centre, half = nearest_part(poly.center)
        slot = ATLAS_SLOTS.get(bone, 2)
        tx, ty = slot % cols, slot // cols
        n = poly.normal
        axis = max(range(3), key=lambda i: abs(n[i]))
        mirror = bone.endswith(".R")
        for li in poly.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            local = [(co[i] - centre[i]) / max(2 * half[i], 1e-6) + 0.5 for i in range(3)]
            if axis == 0:
                u, v = local[1], local[2]
            elif axis == 1:
                u, v = local[0], local[2]
            else:
                u, v = local[0], local[1]
            if mirror:
                u = 1.0 - u
            u = min(0.97, max(0.03, u))
            v = min(0.97, max(0.03, v))
            uv[li].uv = ((tx + u) / cols, (1 - ty) * 0.5 + v * 0.5)

    for slot in body.material_slots:
        mat = slot.material
        base = mat.name.split(".")[0]
        if base in ("flame", "lamp"):
            continue
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        bsdf = nodes.get("Principled BSDF")
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.interpolation = "Linear"
        mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Base Color"].default_value = (1, 1, 1, 1)
    return img.size[:]

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
# The biped's hand-keyed clips live in rig_families (no bpy there, so the storyboard reads them too).
ACTIONS = families().BIPED_ACTIONS


def registry_picks(doc, path):
    """The unit's row in data/unit_anim.tsv, when the spec's rig is the registry's rig
    (otherwise the family defaults, with a warning: the row was written for another body)."""
    motions = sibling("rig_motions")
    unit = doc.get("unit") or motions.unit_in_path(path)
    row = motions.unit_rows().get(unit) if unit else None
    if row is None:
        return None
    rig = doc.get("rig", "biped")
    if row["rig"] != rig:
        print(f"anim: {unit} is {row['rig']} in data/unit_anim.tsv but this spec is {rig}: family defaults")
        return None
    return motions.unit_picks(unit, rig)


def load_spec(target):
    """Either a built-in id (SPECS) or a path to {"parts"|"segments": ...} JSON.
    Returns (unit, spec, rest_pose). rest_pose is optional bone rest rotations. Sets ANIM
    from the doc's "anim", else from the unit's row in data/unit_anim.tsv."""
    global ANIM
    ANIM = None
    p = pathlib.Path(target)
    if p.suffix == ".json":
        doc = json.loads(p.read_text())
        pose = doc.get("rest_pose")
        ANIM = doc.get("anim") or registry_picks(doc, p)
        if doc.get("rig") or doc.get("bones"):
            print("rig family:", load_family(doc.get("rig", "biped"), doc.get("bones"), doc.get("rig_measure")))
        register_palette(doc.get("palette"))
        if "segments" in doc:          # skeleton-first spec: placement comes from the rig
            return p.stem, doc, pose
        return p.stem, [tuple(x) for x in doc["parts"]], pose
    if target not in SPECS:
        sys.exit(f"no spec for {target}")
    return target, SPECS[target], None


def load_cuts(argv):
    """The cuts=<json> argument: the outlines of the parts with opts "cut" (cut_hull.py); propcrops=<json>."""
    for arg in argv:
        if arg.startswith("cuts="):
            CUTS.update(json.loads(pathlib.Path(arg[len("cuts="):]).read_text()))
        if arg.startswith("propcrops="):
            PROPCROPS.update(json.loads(pathlib.Path(arg[len("propcrops="):]).read_text()))


PROPCROPS = {}   # (arg propcrops=<json>) {part index: png of the props sheet's drawing}: a prop part's front face wears it
PROPID = False   # (arg propid) each prop in a flat colour of its own (preflight.PROP_IDS): the ID render's prop_reads reads them


def prop_rows(spec):
    """The spec rows with each prop (opts "prop" + "anchor", PIPELINE 23.L5-3) on its anchor's bone, so its
    skin is 100 % there, and on a material of its own: when the body shares the prop's material the prop
    gets a copy, prop_<name>, in the palette's colour and surface (while the rig has material slots to spare)."""
    PF = sibling("preflight")
    bones = {b[0] for b in BONES}
    body = {row[4] for row in spec if not PF.is_prop(row)}
    rows = []
    for row in spec:
        if PF.is_prop(row):
            bone, mat = PF.anchor_bone(row, bones), row[4]
            if mat in body and len(body | {r[4] for r in rows}) < PF.MATERIAL_SLOTS[1]:
                new = "prop_" + "".join(c if c.isalnum() else "_" for c in str(row[5]["prop"]).lower())
                for table in (MATERIALS, SURFACE, ALPHA, RAMPS):
                    if mat in table:
                        table[new] = table[mat]
                mat = new
            row = (bone, row[1], row[2], row[3], mat, row[5])
        rows.append(row)
    return rows


def build_spec_parts(spec, chamfers):
    """(object, bone) per spec row; a row with opts "decal" marks its object so
    texturize paints that decal on the part's front face."""
    parts = []
    spec = prop_rows(spec)
    PF = sibling("preflight")
    names = PF.prop_names(spec)
    for idx, (bone, kind, dims, at, mat_name, opts) in enumerate(spec):
        if PROPID and (opts or {}).get("prop") and not CLAY:
            mat_name = f"propid{names.index(str(opts['prop']))}"
            MATERIALS[mat_name], SURFACE[mat_name] = (*PF.PROP_IDS[int(mat_name[6:]) % len(PF.PROP_IDS)], 1.0), "metal"
        if (opts or {}).get("cut") == "sheet" and str(idx) in CUTS:
            obj = cut_part(bone, mat_name, idx)
        elif kind in ("lathe", "limb", "chain", "plate"):
            obj = swept_part(kind, tuple(dims), tuple(at), opts or {}, f"{bone}_{idx}", idx, bone)
            obj.data.materials.append(material(mat_name))
        else:
            obj = build_part(bone, kind, tuple(dims), tuple(at), mat_name, opts or {}, idx,
                             idx in chamfers)
        if (opts or {}).get("prop"):
            obj["prop"] = str(opts["prop"])
        if (opts or {}).get("decal") and not CLAY:
            obj["decal"] = "face" if opts["decal"] == "sheet" and FACE is None else opts["decal"]
            obj["decal_color"] = opts.get("decal_color", "")
        elif str(idx) in PROPCROPS and not CLAY:      # the prop wears its drawing on the front face (a decal of its own)
            obj["decal"], obj["decal_color"] = "propcrop", PROPCROPS[str(idx)]
            obj["decal_side"] = "back" if opts.get("anchor") == "back" else "front"      # a tank shows its back to the camera
        parts.append((obj, bone))
    return parts


def parts_meta(parts):
    """(bone, material, centre, half) per part, before the join; records the decals.
    bound_box is in the object's local space: take the corners to world space, or every
    centre comes out at the part's own origin."""
    meta = []
    for obj, bone in parts:
        mat_name = obj.data.materials[0].name.split(".")[0]
        corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        lo = Vector((min(c[i] for c in corners) for i in range(3)))
        hi = Vector((max(c[i] for c in corners) for i in range(3)))
        meta.append((bone, mat_name, (lo + hi) / 2, (hi - lo) / 2))
        if obj.get("decal") and len(DECALS) < 8:
            crop = obj["decal"] == "propcrop"
            DECALS.append(((lo + hi) / 2, (hi - lo) / 2, obj["decal"], obj["decal_color"],
                           -1 if obj.get("decal_side") == "back" else 1, meta[-1] if crop else None))
    return meta


PROP_GAP = 0.03     # attach: a prop's mesh may stand this far (spec metres) off its anchor's before it is loose


def mesh_gap(obj, near, trees):
    """Distance from a prop's mesh to the closest of the `near` parts (0 when they cross)."""
    if any(trees[id(obj)].overlap(trees[id(o)]) for o in near):
        return 0.0
    return min((trees[id(o)].find_nearest(obj.matrix_world @ v.co)[3] for o in near for v in obj.data.vertices),
               default=0.0)


def prop_gaps(parts, parent, trees):
    """{part name: gap} of every prop part to the body on its anchor bone (or its parent); a part of a
    prop that stands off the body but touches a held part of the same prop (a valve on a tank) takes
    the gap to that part instead."""
    props = [(o, b) for o, b in parts if o.get("prop")]
    gaps = {o.name: mesh_gap(o, [q for q, qb in parts if not q.get("prop") and qb in (b, parent.get(b))], trees)
            for o, b in props}
    for _ in props:
        for o, _b in props:
            held = [q for q, _qb in props if q is not o and q["prop"] == o["prop"] and gaps[q.name] <= PROP_GAP]
            if gaps[o.name] > PROP_GAP and held:
                gaps[o.name] = min(gaps[o.name], mesh_gap(o, held, trees))
    return gaps


def attach_report(parts):
    """Parts whose mesh crosses no other part on their bone or on the parent bone: the same
    rule as preflight.overlap, measured on the real meshes instead of the boxes (PIPELINE
    20.N12). A prop (own component, PIPELINE 23.L5-3) only has to stand within PROP_GAP of the body
    on its anchor bone and is listed under "props" with its gap. Never raises: the build goes on and
    the report carries the error."""
    from mathutils.bvhtree import BVHTree
    try:
        bpy.context.view_layer.update()
        parent = {bone: up for bone, up, *_ in BONES if up and up != "root"}
        trees = {id(o): BVHTree.FromPolygons([o.matrix_world @ v.co for v in o.data.vertices],
                                             [tuple(f.vertices) for f in o.data.polygons])
                 for o, _ in parts}               # FromObject would stay in each part's local space
        gaps = prop_gaps(parts, parent, trees)
        loose, props = [], []
        for obj, bone in parts:
            near = [o for o, b in parts if o is not obj and not o.get("prop") and b in (bone, parent.get(bone))]
            if obj.get("prop"):
                props.append({"part": obj.name, "prop": obj["prop"], "bone": bone, "gap": round(gaps[obj.name], 4)})
                if gaps[obj.name] > PROP_GAP:
                    loose.append({"part": obj.name, "bone": bone, "parent": parent.get(bone)})
            elif bone in parent and near and not any(trees[id(obj)].overlap(trees[id(o)]) for o in near):
                loose.append({"part": obj.name, "bone": bone, "parent": parent[bone]})
        return {"parts": len(parts), "loose": loose, "props": props}
    except Exception as err:  # noqa: BLE001 - a report must not stop a build
        return {"parts": len(parts), "loose": [], "error": repr(err)}


def main():
    target, out = sys.argv[sys.argv.index("--") + 1:][:2]
    rest = sys.argv[sys.argv.index("--") + 1:]
    cli = rest[2:]          # after <spec> <out.glb>: budget, mode, target, tex, voxel
    atlas_path = None
    global STYLE, CLAY, FACE, RAMP
    CLAY = "clay" in rest
    global PROPID
    PROPID = "propid" in rest
    for arg in rest:
        if arg.startswith("style="):  # style=cel|painted
            STYLE = arg[len("style="):]
        if arg.startswith("ramp="):   # ramp=0.5: cel cells become vertical ramps
            RAMP = float(arg[len("ramp="):])
        if arg.startswith("face=") and not CLAY:   # face=<rgba png>: the "sheet" decal's image
            import numpy as np
            img = bpy.data.images.load(arg[len("face="):])
            FACE = np.array(img.pixels[:]).reshape(img.size[1], img.size[0], 4)
        if arg.startswith("atlas=") and not CLAY:
            atlas_path = arg[len("atlas="):]
        if arg.startswith("pal="):  # pal=8A8F94,C9A46A,FFE600 overrides the palette
            for name, hexv in zip(("iron", "brass", "flame"), arg[4:].split(",")):
                MATERIALS[name] = tuple(int(hexv[i:i + 2], 16) / 255.0 for i in (0, 2, 4)) + (1.0,)
    load_cuts(rest)
    wipe()                                  # before any branch: the factory cube is not ours
    unit, spec, rest_pose = load_spec(target)
    if isinstance(spec, dict) and spec.get("rig"):
        print("rig family:", load_family(spec["rig"], None, spec.get("rig_measure")))
    if isinstance(spec, dict) and spec.get("mode") == "boxmod":
        import boxmod as BM
        body = BM.build(spec)
        bpy.context.view_layer.objects.active = body
        for m, _ in [("iron", None)]:
            body.data.materials.append(material(m))
        arm = build_armature(rest_pose)
        body.parent = arm
        body.vertex_groups.new(name="spine").add(range(len(body.data.vertices)), 1.0, "REPLACE")
        body.modifiers.new("Armature", "ARMATURE").object = arm
        make_actions(arm)
        print(f"built {unit}: boxmod {len(body.data.polygons)} faces")
        bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_yup=True,
                                  export_animations=True, export_animation_mode="ACTIONS",
                                  export_apply=False, export_skins=True, export_morph=False)
        return
    if isinstance(spec, dict) and spec.get("mode") == "skin":
        body = build_skin_body(spec, target=430, subdiv=2)
        print(f"skin body: {len(body.data.polygons)} faces")
        extra_parts = []
        for idx, ex in enumerate(spec.get("extras", [])):
            head, tail = BONE_MAP[ex["bone"]]
            off = ex.get("offset", (0, 0, 0))
            at = tuple(head[i] + off[i] for i in range(3))
            opts = {k: v for k, v in ex.items() if k in ("sides", "axis", "rot", "top")}
            obj = build_part(ex["bone"], ex.get("kind", "box"), tuple(ex["dims"]), at,
                             ex.get("material", "iron"), opts, idx)
            obj.vertex_groups.new(name=ex["bone"]).add(range(len(obj.data.vertices)), 1.0, "REPLACE")
            extra_parts.append(obj)
        if extra_parts:
            bpy.ops.object.select_all(action="DESELECT")
            for o in extra_parts:
                o.select_set(True)
            body.select_set(True)
            bpy.context.view_layer.objects.active = body
            bpy.ops.object.join()
            print(f"mix: +{len(extra_parts)} hard plates -> {len(body.data.polygons)} faces")
        arm = build_armature(rest_pose)
        body.parent = arm
        body.modifiers.new("Armature", "ARMATURE").object = arm
        make_actions(arm)
        if "tex" in rest:
            meta = []
            for seg in spec.get("segments", []):
                h, tl = BONE_MAP[seg["bone"]]
                r0, r1 = seg.get("radius", (0.14, 0.12))
                mid = tuple((h[i] + tl[i]) / 2 for i in range(3))
                meta.append((seg["bone"], seg.get("material", "iron"),
                             bp(mid), (max(r0, r1),) * 3))
            print("texture:", texturize(body, meta), "tiles")
        bpy.ops.object.select_all(action="DESELECT")
        bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_yup=True,
                                  export_animations=True, export_animation_mode="ACTIONS",
                                  export_apply=False, export_skins=True, export_morph=False)
        print(f"built {unit}: skin mode, {len(body.data.polygons)} faces -> {out}")
        return
    if isinstance(spec, dict):          # skeleton-first spec: rig decides placement
        print("skeleton report:")
        validate_skeleton(spec, 700)
        spec = resolve_skeleton(spec)
    wipe()
    arm = build_armature(rest_pose)

    # chamfer is opt-in: measured on n01X it inflated the plates and read worse than
    # the crisp blockout, because the WC3 roundness comes from painted shading, not
    # from geometry at this budget. Pass a triple budget as the third argument to enable.
    chamfers = plan_chamfers(spec, int(cli[0])) if cli else set()

    parts = build_spec_parts(spec, chamfers)

    # rigid skin (one bone per piece, weight 1), then one joined mesh so the
    # engine draws a single mesh with three material slots
    bpy.ops.object.select_all(action="DESELECT")
    for obj, bone in parts:
        skin_part(obj, bone)
    meta = parts_meta(parts)
    report = attach_report(parts)
    stem = pathlib.Path(out).stem       # the run's clay.glb / model.glb: attach.json; a trial: <name>-attach.json
    name = "attach.json" if stem in ("clay", "model") else f"{stem}-attach.json"
    (pathlib.Path(out).parent / name).write_text(json.dumps(report, indent=2))
    print(f"attach: {len(report['loose'])} loose of {report['parts']} parts")
    if "union" in cli:
        # the flame slit is a lit decal, not a plate: keep it out of the union or the
        # boolean absorbs its faces into the iron material and the accent disappears
        keep = [p for p in parts if p[0].data.materials and p[0].data.materials[0].name.split(".")[0] == "flame"
                or p[0].get("prop")]       # a prop stays its own component too
        union_targets = [p for p in parts if p not in keep]
        merged = union_parts(union_targets, meta, per_chain=True)
        for obj, _ in keep:
            merged.append(obj)
        if len(merged) > 1:
            bpy.ops.object.select_all(action="DESELECT")
            for o in merged:
                o.select_set(True)
            bpy.context.view_layer.objects.active = merged[0]
            bpy.ops.object.join()
        body_u = merged[0]
        parts = [(body_u, parts[0][1])]
        body_u.vertex_groups.clear()
        for bone, *_ in meta:
            if bone not in body_u.vertex_groups:
                body_u.vertex_groups.new(name=bone)
        for v in body_u.data.vertices:
            best, bd = meta[0], 1e9
            for m in meta:
                d = sum((v.co[i] - m[2][i]) ** 2 for i in range(3))
                if d < bd:
                    best, bd = m, d
            body_u.vertex_groups[best[0]].add([v.index], 1.0, "REPLACE")
        if "nobev" not in cli:
            bev = body_u.modifiers.new("Junction", "BEVEL")
            bev.width = 0.006
            bev.segments = 1
            bev.limit_method = "ANGLE"
            bev.angle_limit = math.radians(35)
            bpy.ops.object.modifier_apply(modifier=bev.name)
        plan = body_u.modifiers.new("Planar", "DECIMATE")
        plan.decimate_type = "DISSOLVE"
        plan.angle_limit = math.radians(6)
        bpy.ops.object.modifier_apply(modifier=plan.name)
        budget = int(cli[2]) if len(cli) > 2 and cli[2].isdigit() else 700
        union_decimate(body_u, budget // 2, "toldec" in rest)
        print(f"union: {len(body_u.data.polygons)} faces after boolean + bevel + decimate")
    for obj, _ in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0][0]
    bpy.ops.object.join()
    body = bpy.context.view_layer.objects.active
    body.name = body.data.name = unit

    if "clean" in rest:
        before = len(body.data.polygons)
        clean_mesh(body)
        print(f"clean: {before} -> {len(body.data.polygons)} faces")
    if "cull" in rest or "cull=remove" in rest:
        sibling("cull").cull(body, out, remove="cull=remove" in rest)
    if len(cli) > 1 and cli[1] == "morph":
        faces = morph(body, target=int(cli[2]) if len(cli) > 2 else 650)
        print(f"morph: {faces} faces after subdiv + decimate")
    if atlas_path:
        print("atlas:", texturize_atlas(body, meta, atlas_path))
    elif len(cli) > 3 and cli[3] == "tex":
        n = texturize(body, meta)
        print(f"texture: {n} painted tiles + world-space UVs")
    if len(cli) > 1 and cli[1] == "fuse":
        faces = fuse(body, meta, target=int(cli[2]) if len(cli) > 2 else 650,
                     voxel=float(cli[4]) if len(cli) > 4 else 0.025)
        print(f"fused: {faces} faces after remesh + decimate")
    else:
        soften(body)
    print("shading:", shading_report(body))

    body.parent = arm
    body.modifiers.new("Armature", "ARMATURE").object = arm

    make_actions(arm)
    bpy.context.scene.frame_set(1)

    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_yup=True,
                              export_animations=True, export_animation_mode="ACTIONS",
                              export_apply=False, export_skins=True, export_morph=False)
    tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
    print(f"built {unit}: {len(parts)} parts joined, {len(BONES)} bones, "
          f"{len(bpy.data.actions)} actions, {len(body.data.polygons)} faces, ~{tris} tris, "
          f"{len(body.data.materials)} materials -> {out}")


def load_toolkit(skill, module):
    sys.path.append(str(pathlib.Path.home() / ".config/opencode/skills" / skill / "scripts"))
    return __import__(module)


if __name__ == "__main__":
    main()
