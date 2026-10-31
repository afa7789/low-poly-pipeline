#!/usr/bin/env python3
"""L15-5 hands of the eye stage (PIPELINE 33.L15-5): a JSON list of primitive pieces -> a GLB on the armature of an input run.

    blender -b -P tools/blender/eye_lib.py -- build <in.glb> <dsl.json> <out.glb>     # pieces on the armature of in.glb
    blender -b -P tools/blender/eye_lib.py -- bones <in.glb> <bones.json>             # {bone: {head, tail, parent}} in world coords

A port of the l14fix_lib of L14-3 (tube / box / ball / between, one flat colour per piece, weight 1.0 on the piece's bone) with the
python of the fix scripts replaced by data, so a model can write it and `--eye replay` can rebuild it. The DSL (Blender frame: x to
the viewer's right in the front view, -y forward, z up):

    {"colours": {"coat": "3A3A3F", ...}, "keep": ["head"], "why": "...",
     "pieces": [{"op": "ball|box|tube|between", "name": "...", "mat": "coat", "bone": "spine", "role": "torso", ...}]}

    ball     r, at, [scale 3, seg 5-12 (8), rings 3-8 (6)]
    box      size 3, at, [rot 3 (deg), top 2 (the top face's scale: a wedge), shift 2 (it slides x, y)]
    tube     r0, r1, length, at, [rot 3, sides 3-12 (8), scale 3]       an n-gon frustum along local z
    between  a, b, r0, r1, [sides, scale]                              the same tube from point a to point b

`keep`: bones whose faces of the input mesh stay (default none: every piece is new). validate() is the deterministic check that runs
before Blender (bones exist, points inside the sheet's box, triangles under the budget, a piece for every role the sheet has).
bpy is imported inside the functions that need it: the rest imports and tests without Blender."""
import json
import math
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
MAX_PIECES = 48         # L16-1: n017 asked for 65 pieces and two resends; a unit reads with fewer
BUDGET = 700            # triangles of the pieces (the outline hull doubles them in the file, as everywhere)
MARGIN = 0.20           # share of the sheet box's size a point may lie outside it
ROLES = ("head", "face", "torso", "pelvis", "arm", "hand", "leg", "foot", "wing", "tail", "prop", "other")
NEED_ROLES = ("head", "hand", "foot", "prop")        # a sheet that has such a part needs a piece with this role
REQUIRED = {"ball": ("r", "at"), "box": ("size", "at"), "tube": ("r0", "r1", "length", "at"), "between": ("a", "b", "r0", "r1")}
OPTIONAL = {"ball": ("scale", "seg", "rings"), "box": ("rot", "top", "shift"), "tube": ("rot", "sides", "scale"), "between": ("sides", "scale")}
VEC = {"at": 3, "a": 3, "b": 3, "size": 3, "rot": 3, "scale": 3, "top": 2, "shift": 2}
HEX = set("0123456789abcdefABCDEF")


def hex_ok(h):
    return isinstance(h, str) and len(h) == 6 and set(h) <= HEX


def tris_of(p):
    """Triangles of one piece as Blender builds it (checked against the GLB in the tests)."""
    if p["op"] == "ball":
        return 2 * p.get("seg", 8) * (p.get("rings", 6) - 1)
    if p["op"] == "box":
        return 12
    return 4 * p.get("sides", 8) - 4


def points_of(p):
    return [p["a"], p["b"]] if p["op"] == "between" else [p["at"]]


def piece_errors(i, p):
    """What is wrong with the shape of piece i (types, keys, ranges); [] when it is buildable."""
    tag = f"piece {i}" + (f" ({p.get('name')})" if isinstance(p, dict) and p.get("name") else "")
    if not isinstance(p, dict) or p.get("op") not in REQUIRED:
        return [f"{tag}: op must be one of {sorted(REQUIRED)}"]
    out = [f"{tag}: missing '{k}'" for k in (*REQUIRED[p["op"]], "name", "mat", "bone", "role") if k not in p]
    out += [f"{tag}: unknown key '{k}'" for k in p if k not in (*REQUIRED[p["op"]], *OPTIONAL[p["op"]], "op", "name", "mat", "bone", "role", "colour")]
    for k, n in VEC.items():
        v = p.get(k)
        if v is not None and not (isinstance(v, list) and len(v) == n and all(isinstance(x, (int, float)) and math.isfinite(x) for x in v)):
            out.append(f"{tag}: '{k}' must be a list of {n} numbers")
    for k in ("r", "r0", "r1", "length"):
        if k in p and not (isinstance(p[k], (int, float)) and p[k] >= 0.005):
            out.append(f"{tag}: '{k}' must be a number >= 0.005")
    for k, lo, hi in (("sides", 3, 12), ("seg", 5, 12), ("rings", 3, 8)):
        if k in p and not (isinstance(p[k], int) and lo <= p[k] <= hi):
            out.append(f"{tag}: '{k}' must be an integer {lo}-{hi}")
    if p.get("role", "other") not in ROLES:
        out.append(f"{tag}: role must be one of {list(ROLES)}")
    if "colour" in p and not hex_ok(p["colour"]):
        out.append(f"{tag}: colour must be 6 hex digits")
    return out


def outside(q, box):
    """True when point q is more than MARGIN of the box's size away from box = (lo xyz, hi xyz) on any axis."""
    return any(c < lo - MARGIN * (hi - lo) or c > hi + MARGIN * (hi - lo) for c, lo, hi in zip(q, *box))


def validate(dsl, bones, box, need_roles=(), budget=BUDGET):
    """Reasons (one string each) the DSL cannot be built, [] when it can. `bones`: names of the rig; `box`: ((lo xyz), (hi xyz))
    in the Blender frame, or None; `need_roles`: roles of the sheet's parts (NEED_ROLES are enforced)."""
    if not isinstance(dsl, dict) or not isinstance(dsl.get("pieces"), list) or not dsl["pieces"]:
        return ["the reply must be an object with a non-empty list 'pieces'"]
    out = []
    for i, p in enumerate(dsl["pieces"]):
        out += piece_errors(i, p)
    if out:
        return out
    if len(dsl["pieces"]) > MAX_PIECES:
        return [f"{len(dsl['pieces'])} pieces, over the limit of {MAX_PIECES}: merge small pieces (one box for a group of fingers, one tube for a row of teeth)"]
    colours = dsl.get("colours") or {}
    bad_keep = [b for b in dsl.get("keep", []) if b not in bones]
    out += [f"keep: bone '{b}' is not in the rig" for b in bad_keep]
    for i, p in enumerate(dsl["pieces"]):
        if p["bone"] not in bones:
            out.append(f"piece {i} ({p['name']}): bone '{p['bone']}' is not in the rig")
        if not hex_ok(p.get("colour", colours.get(p["mat"]))):
            out.append(f"piece {i} ({p['name']}): material '{p['mat']}' has no colour (give 'colours' or 'colour')")
        bad = next((q for q in points_of(p) if box and outside(q, box)), None)
        if bad:
            out.append(f"piece {i} ({p['name']}): point {bad} lies outside the sheet's box {box} (+-20 %)")
    tris = sum(tris_of(p) for p in dsl["pieces"])
    if tris > budget:
        out.append(f"{tris} triangles, over the budget of {budget}: fewer pieces or fewer sides")
    have = {p["role"] for p in dsl["pieces"]}
    out += [f"no piece with role '{r}', and the sheet has one" for r in NEED_ROLES if r in need_roles and r not in have]
    return out


# ---------------------------------------------------------------- Blender side
def srgb(hexv):
    rgb = [int(hexv[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4) for c in rgb) + (1.0,)


def make_piece(p, material):
    """The linked Blender object of one piece; `material` is its bpy material."""
    import bmesh
    import bpy
    from mathutils import Vector
    bm = bmesh.new()
    op, at, rot, scale = p["op"], p.get("at", (0, 0, 0)), p.get("rot", (0, 0, 0)), p.get("scale", (1, 1, 1))
    if op == "ball":
        bmesh.ops.create_uvsphere(bm, u_segments=p.get("seg", 8), v_segments=p.get("rings", 6), radius=p["r"])
    elif op == "box":
        bmesh.ops.create_cube(bm, size=1.0)
        top, shift = p.get("top", (1, 1)), p.get("shift", (0, 0))
        for v in bm.verts:
            if v.co.z > 0:
                v.co.x, v.co.y = v.co.x * top[0] + shift[0], v.co.y * top[1] + shift[1]
            v.co = Vector((v.co.x * p["size"][0], v.co.y * p["size"][1], v.co.z * p["size"][2]))
        scale = (1, 1, 1)
    else:
        a = Vector(p["a"]) if op == "between" else None
        d = Vector(p["b"]) - a if op == "between" else None
        length = d.length if op == "between" else p["length"]
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=p.get("sides", 8), radius1=p["r0"], radius2=p["r1"], depth=length)
        if op == "between":
            at = (a + Vector(p["b"])) / 2
    me = bpy.data.meshes.new(p["name"])
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(p["name"], me)
    bpy.context.collection.objects.link(obj)
    obj.location = Vector(at)
    obj.rotation_euler = d.to_track_quat("Z", "Y").to_euler() if op == "between" else tuple(math.radians(r) for r in rot)
    obj.scale = scale
    me.materials.append(material)
    return obj


def drop_faces(mesh_obj, keep):
    """Delete the faces of the input mesh unless two of their vertices are weighted mostly on a bone of `keep`, then the loose rest."""
    import bmesh
    names = {g.index: g.name for g in mesh_obj.vertex_groups}
    dom = []
    for v in mesh_obj.data.vertices:
        best = max(v.groups, key=lambda g: g.weight, default=None)
        dom.append(names.get(best.group) if best else None)
    bm = bmesh.new()
    bm.from_mesh(mesh_obj.data)
    bm.faces.ensure_lookup_table()
    gone = [f for f in bm.faces if sum(dom[v.index] in keep for v in f.verts) < 2]
    bmesh.ops.delete(bm, geom=gone, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(mesh_obj.data)
    bm.free()


def load_rig(src):
    """Import `src`; (armature, skinned mesh) with the rig in rest pose and the importer's Icosphere marker removed."""
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(src))
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    old = next(o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm and not o.name.startswith(("outline", "face")))
    for o in [o for o in bpy.data.objects if o.type == "MESH" and o.parent != arm]:
        bpy.data.objects.remove(o, do_unlink=True)
    arm.data.pose_position = "REST"
    return arm, old


def build(src, dsl, out):
    """The pieces of `dsl` on the armature of `src`, exported to `out`; {tris, pieces, materials} of what came out."""
    import bpy
    arm, old = load_rig(src)
    colours = dsl.get("colours") or {}
    mats = {}
    for p in dsl["pieces"]:
        if p["mat"] not in mats:
            m = bpy.data.materials.new(p["mat"])
            m.use_nodes = True
            bsdf = m.node_tree.nodes["Principled BSDF"]
            bsdf.inputs["Base Color"].default_value = srgb(p.get("colour", colours.get(p["mat"])))
            bsdf.inputs["Roughness"].default_value = 0.9
            mats[p["mat"]] = m
    parts = [(make_piece(p, mats[p["mat"]]), p["bone"]) for p in dsl["pieces"]]
    keep = set(dsl.get("keep", []))
    drop_faces(old, keep)
    if not keep:
        old.data.materials.clear()
    for obj, bone in parts:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        obj.vertex_groups.new(name=bone).add(range(len(obj.data.vertices)), 1.0, "REPLACE")
    bpy.ops.object.select_all(action="DESELECT")
    for obj, _ in parts:
        obj.select_set(True)
    old.select_set(True)
    bpy.context.view_layer.objects.active = old
    bpy.ops.object.join()
    old.name = old.data.name = "eye"
    for poly in old.data.polygons:
        poly.use_smooth = False
    if not any(m.type == "ARMATURE" for m in old.modifiers):
        old.modifiers.new("Armature", "ARMATURE").object = arm
    old.parent = arm
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB", export_yup=True, export_animations=True,
                              export_animation_mode="ACTIONS", export_apply=True, export_skins=True, export_morph=False)
    return {"tris": sum(len(p.vertices) - 2 for p in old.data.polygons), "pieces": len(parts),
            "materials": sorted({s.material.name for s in old.material_slots if s.material}), "actions": len(bpy.data.actions)}


def bones_of(src):
    """{bones: {bone: {head, tail, parent}}, bbox: [lo, hi]} of `src` in world coordinates (the frame the pieces are written in):
    the rig, and the box of its skinned mesh in rest pose."""
    from mathutils import Vector
    arm, mesh = load_rig(src)
    m = arm.matrix_world
    corners = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]
    return {"bones": {b.name: {"head": [round(c, 4) for c in m @ b.head_local], "tail": [round(c, 4) for c in m @ b.tail_local],
                               "parent": b.parent.name if b.parent else None} for b in arm.data.bones},
            "bbox": [[round(min(c[i] for c in corners), 4) for i in range(3)], [round(max(c[i] for c in corners), 4) for i in range(3)]]}


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    if args[0] == "build":
        info = build(args[1], json.loads(pathlib.Path(args[2]).read_text()), args[3])
        pathlib.Path(args[3]).with_suffix(".json").write_text(json.dumps(info))
        print("EYE", json.dumps(info))
    else:
        pathlib.Path(args[2]).write_text(json.dumps(bones_of(args[1]), indent=1))


def run_blender(*argv):
    """Run this file in Blender (nice 10) with `argv`; the completed process."""
    return subprocess.run(["nice", "-n", "10", "blender", "-b", "-P", str(HERE / "eye_lib.py"), "--", *map(str, argv)], capture_output=True, text=True)


if __name__ == "__main__":
    main()
