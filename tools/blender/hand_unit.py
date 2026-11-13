"""Unit models built by hand from the approved concept sheet: faceted wedge pieces, each rigid on one bone
of a rig family (tools/blender/rig_families), the family's clips keyed the way anim_refresh keys them, one
64x64 palette texture with a flat colour per piece.

A unit is a script in tools/blender/units/<id>.py:

    import hand_unit as H
    PALETTE = {"tunic": 0x565A4C, ...}                 # tone -> sRGB hex, read off the sheet
    def make():
        H.frustum("spine", "tunic", (0, 1.3, 0), (0, 2.0, 0), (0.45, 0.37), (0.54, 0.39))
    H.build("hfoo", "biped", PALETTE, make, joints={"arm.L": ((0.56, 2.02, 0), (0.56, 1.5, 0))})

    blender -b --factory-startup -P tools/blender/units/<id>.py -- <out.glb>

Coordinates are the families': x left (+) / right (-), y up, z front, metres (a biped stands about 2.7).
`joints` moves a family bone's head and tail onto the model's own joint; the bone keeps its parent and
should keep its rest direction, since the clips turn it from there.
"""
import math
import pathlib
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import anim_refresh as AR  # noqa: E402
import build_unit as BU  # noqa: E402

CELLS = 8           # the palette is CELLS x CELLS flat cells
HANDS = pathlib.Path(__file__).resolve().parents[2] / "data/hand_grip.tsv"     # unit_id, hand (anim_refresh.held's words), note
PIECES = []         # (object, bone)
WEIGHTS = {}        # object name -> {vertex index: {bone: weight}} for the few soft pieces


def to_blender(p):
    return Vector((p[0], -p[2], p[1]))


def _ring(centre, u, v, radii, sides):
    ru, rv = radii
    if sides == 4:
        return [centre + u * x + v * y for x, y in ((ru, rv), (-ru, rv), (-ru, -rv), (ru, -rv))]
    step = 2 * math.pi / sides
    return [centre + u * ru * math.cos((i + 0.5) * step) + v * rv * math.sin((i + 0.5) * step) for i in range(sides)]


def _piece(bm, bone, tone):
    mesh = bpy.data.meshes.new(tone)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(f"{tone}.{len(PIECES)}", mesh)
    bpy.context.collection.objects.link(obj)
    obj["tone"] = tone
    PIECES.append((obj, bone))
    return obj


def frustum(bone, tone, a, b, ra, rb, sides=8):
    """A tapered prism from a to b, rigid on `bone`, painted `tone`. ra / rb are (half width, half depth)
    at each end, measured across x and across the other axis; 4 sides is a tapered box, more is a polygon
    with a flat face to the front."""
    a, b = to_blender(a), to_blender(b)
    d = (b - a).normalized()
    u = Vector((1, 0, 0)) - d * d.x
    u = u.normalized() if u.length > 1e-4 else Vector((0, 0, 1))
    v = d.cross(u)
    bm = bmesh.new()
    low, high = ([bm.verts.new(p) for p in _ring(c, u, v, r, sides)] for c, r in ((a, ra), (b, rb)))
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new((low[i], low[j], high[j], high[i]))
    bm.faces.new(low[::-1])
    bm.faces.new(high)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _piece(bm, bone, tone)


def box(bone, tone, centre, size):
    """An upright box: size is (x, y, z)."""
    x, y, z = centre
    half = (size[0] / 2, size[2] / 2)
    return frustum(bone, tone, (x, y - size[1] / 2, z), (x, y + size[1] / 2, z), half, half, sides=4)


def chain(bones, tone, points, radii, sides=6):
    """Consecutive frusta through `points`, radii[i] = (half width, half depth) at points[i]: a curved blade,
    a horn, a tail, a neck. `bones` is one bone for all segments or one per segment."""
    names = [bones] * (len(points) - 1) if isinstance(bones, str) else list(bones)
    return [frustum(names[i], tone, points[i], points[i + 1], radii[i], radii[i + 1], sides)
            for i in range(len(points) - 1)]


def wheel(bone, tone, centre, radius, width, sides=12):
    """A wheel lying on its axle (the x axis), centred on `centre`: put the wheel bone's head there."""
    x, y, z = centre
    return frustum(bone, tone, (x - width / 2, y, z), (x + width / 2, y, z), (radius, radius), (radius, radius), sides)


def panel(bone, tone, points, thickness=0.03):
    """A thin flat plate with the outline `points` (coplanar, any order around the outline): a wing
    membrane, a cloak, a fin, a banner."""
    pts = [to_blender(p) for p in points]
    centre = sum(pts, Vector()) / len(pts)
    normal = sum(((pts[i] - centre).cross(pts[(i + 1) % len(pts)] - centre) for i in range(len(pts))), Vector())
    half = normal.normalized() * thickness / 2
    bm = bmesh.new()
    front, back = [bm.verts.new(p + half) for p in pts], [bm.verts.new(p - half) for p in pts]
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new((front[i], front[j], back[j], back[i]))
    bm.faces.new(front)
    bm.faces.new(back[::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _piece(bm, bone, tone)


def soft(obj, weigh):
    """Blend one piece between bones: weigh((x, y, z) in family coordinates) -> {bone: weight}."""
    WEIGHTS[obj.name] = {v.index: weigh((v.co.x, v.co.z, -v.co.y)) for v in obj.data.vertices}
    return obj


def _palette(palette, out):
    names = list(palette)
    if len(names) > CELLS * CELLS:
        raise SystemExit(f"palette has {len(names)} tones, the atlas holds {CELLS * CELLS}")
    size, cell = 64, 64 // CELLS
    img = bpy.data.images.new("palette", size, size, alpha=False)
    px = []
    for y in range(size):
        for x in range(size):
            i = (y // cell) * CELLS + x // cell
            rgb = palette[names[i]] if i < len(names) else 0
            px += [((rgb >> shift) & 0xFF) / 255.0 for shift in (16, 8, 0)] + [1.0]
    img.pixels = px
    img.filepath_raw = str(out.with_suffix(".palette.png"))
    img.file_format = "PNG"
    img.save()
    img.pack()
    mat = bpy.data.materials.new("paint")
    mat.use_nodes = True
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image, tex.interpolation = img, "Closest"
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9
    return mat, {n: ((i % CELLS + 0.5) / CELLS, (i // CELLS + 0.5) / CELLS) for i, n in enumerate(names)}


def _skin(obj, bone):
    custom = WEIGHTS.get(obj.name)
    if custom is None:
        obj.vertex_groups.new(name=bone).add(range(len(obj.data.vertices)), 1.0, "REPLACE")
        return
    groups = {}
    for index, weights in custom.items():
        for name, weight in weights.items():
            groups.setdefault(name, obj.vertex_groups.new(name=name) if name not in groups else groups[name])
            groups[name].add([index], weight, "REPLACE")


def _join(palette, out):
    mat, cells = _palette(palette, out)
    bpy.ops.object.select_all(action="DESELECT")
    for obj, bone in PIECES:
        for poly in obj.data.polygons:
            poly.use_smooth = False
        for loop in obj.data.uv_layers.new(name="UVMap").data:
            loop.uv = cells[obj["tone"]]
        obj.data.materials.append(mat)
        _skin(obj, bone)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = PIECES[0][0]
    bpy.ops.object.join()
    body = bpy.context.view_layer.objects.active
    body.name = "body"
    return body


FAMILY_REST = {}    # arm bone -> its rest orientation in the family's own skeleton (_family_rest)


def _arm_bone(name):
    return name.endswith((".L", ".R")) and name[:-2].endswith("arm")       # arm, forearm, a rider's


def _family_rest():
    """The family's own arm bones at rest (their orientation), before the unit's joints move them."""
    rig = BU.build_armature()
    FAMILY_REST.clear()
    FAMILY_REST.update({b.name: b.matrix_local.to_3x3() for b in rig.data.bones if _arm_bone(b.name)})
    data = rig.data
    bpy.data.objects.remove(rig)
    bpy.data.armatures.remove(data)


def _turns(arm):
    """{arm bone: (family rest -> unit rest) as a quaternion, in the unit bone's frame}. A unit's arm is modelled
    where its sheet draws it (a forearm folded up to carry a staff), the clips are keyed for the family's hanging
    arm: turned by these, a clip's rotation moves the unit's bone as it moves the family's, seen from outside."""
    return {b.name: (b.matrix_local.to_3x3().inverted() @ FAMILY_REST[b.name]).to_quaternion()
            for b in arm.data.bones if b.name in FAMILY_REST}


def _family_grip(arm, grip):
    """The grips (blades in the unit's forearm frames) in the family's forearm frames: the strikes are solved on
    the family's arm, where the weapon must lie as it lies in the world at rest."""
    out = dict(grip)
    for bone in arm.data.bones:
        blade = grip.get(bone.name[-1]) if bone.name.endswith(("forearm.L", "forearm.R")) else None
        if blade and any(blade) and bone.name in FAMILY_REST:
            out[bone.name[-1]] = tuple(FAMILY_REST[bone.name].inverted() @ bone.matrix_local.to_3x3() @ Vector(blade))
    return out


def _as_family(arm, act, turns):
    """Re-key a strike's arm bones so each turns in the world as the family's does (_turns)."""
    arm.animation_data.action = act
    curves = [f for layer in act.layers for s in layer.strips for cb in s.channelbags for f in cb.fcurves]
    frames = sorted({round(k.co[0]) for f in curves for k in f.keyframe_points})
    keys = []
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        keys.append({name: q @ arm.pose.bones[name].rotation_quaternion @ q.inverted() for name, q in turns.items()})
    last = {}
    for frame, pose in zip(frames, keys):
        for name, q in pose.items():
            q.make_compatible(last.get(name, q))
            last[name] = q
            arm.pose.bones[name].rotation_quaternion = q
            arm.pose.bones[name].keyframe_insert("rotation_quaternion", frame=frame)
    arm.animation_data.action = None


def _armature(family, joints, extras):
    BU.load_family(family, extras)
    _family_rest()
    unknown = set(joints or ()) - {b[0] for b in BU.BONES}
    if unknown:
        raise SystemExit(f"joints name bones the {family} family lacks: {sorted(unknown)}")
    BU.BONES = [(name, parent, *(joints or {}).get(name, (head, tail))) for name, parent, head, tail in BU.BONES]
    BU.BONE_MAP = {name: (head, tail) for name, _, head, tail in BU.BONES}
    used = {bone for _, bone in PIECES} | {b for w in WEIGHTS.values() for per in w.values() for b in per}
    missing = used - set(BU.BONE_MAP)
    if missing:
        raise SystemExit(f"pieces sit on bones the {family} family lacks: {sorted(missing)}")
    return BU.build_armature()


def _animate(unit, arm, fit=False):
    BU.ANIM = BU.sibling("rig_motions").unit_picks(unit, BU.FAMILY)
    BU.FIT = AR.fit(arm, BU.FAMILY) if fit else None
    BU.GRIP = AR.grips(arm)
    hand = next((r[1] for r in (line.split("\t") for line in HANDS.read_text().splitlines()[1:]) if r[0] == unit), None)
    if hand:                # the table's word on which hand strikes and whether it is bare, where the measure misreads the pieces
        BU.GRIP = AR.held(arm, BU.GRIP, hand)
    BU.GRIP = _family_grip(arm, BU.GRIP)
    kept = AR.keyed(arm)
    turns = _turns(arm)
    for act in list(bpy.data.actions):
        AR.to_quaternion(arm, act)
        if act.name.startswith("attack"):
            _as_family(arm, act, turns)
        if act.name == "death":
            AR.settle(arm, act)
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion, pb.location = (1, 0, 0, 0), (0, 0, 0)
    return kept


def build(unit, family, palette, make, joints=None, out=None, extras=None, fit=False):
    """Build the unit and export <out.glb> (default: the path after `--`). `extras` adds the unit's own prop
    bones to the family, [(name, parent, head, tail)]: a claw the pinch clip closes, a second head. `fit`: the
    strikes travel in proportion to the unit's own length (anim_refresh.fit) instead of the family's, for a
    body much longer than the one its family's lunges were drawn for."""
    out = pathlib.Path(out or sys.argv[sys.argv.index("--") + 1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    PIECES.clear()
    WEIGHTS.clear()
    make()
    pieces = len(PIECES)
    arm = _armature(family, joints, extras)
    body = _join(palette, out)
    tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
    body.parent = arm
    body.modifiers.new("rig", "ARMATURE").object = arm
    kept = _animate(unit, arm, fit)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB", export_yup=True, export_animations=True,
                              export_animation_mode="ACTIONS", export_apply=False, export_skins=True,
                              export_morph=False)
    print(f"HAND_UNIT {unit}: family={BU.FAMILY} tris={tris} pieces={pieces} grip={BU.GRIP} strike_arc={kept:.2f} "
          f"actions={sorted(a.name for a in bpy.data.actions)}", flush=True)
    return out
