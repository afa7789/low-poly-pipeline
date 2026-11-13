"""Re-key chosen clips of prepared unit models from today's motion library, and re-seat or replace
skeletons that do not fit their mesh (data/anim_refresh.tsv). Runs on assets/models after
scripts/fetch_models.mjs and tools/inject_clips.py; meshes and textures are not touched.

    blender -b -P tools/blender/anim_refresh.py [-- unit_id ...]

Per row of data/anim_refresh.tsv (unit_id, refit, slots, note, hand, skin):
- hand = L or R (optional): the hand that holds the weapon, when the mesh alone would say the
  shield arm (grips takes whatever reaches farthest from a forearm). "R:out,forward,up": and the
  weapon points there at rest, that many metres (armature axes, out = away from the body on that
  side), where the measure misreads the mesh (a blade along the arm's line, a pick whose head is
  the low end); "R:-": that hand strikes bare; "R:still": that arm waits in the stance while the
  other strikes (the mesh fuses it to the body: it tears when swung). Several: "L:...;R:still".
- refit = a rig family (e.g. drake): each bone's pivot moves onto the joint its skinned mesh bends
  at (the centroid of the vertices blended between the bone and its parent; without such a band the
  midpoint of the two clouds' closest points; with no skinned parent, its own centroid), and takes
  the family's rest direction with roll 0, the frame build_unit.make_actions keys clips in.
  rerig:<family> = the skeleton does not fit the body at all (four legs on biped bones): it is
  replaced by the family's, stretched onto the mesh, and every vertex is skinned anew (rerig).
  "-" = neither.
- slots = the actions re-keyed from data/unit_anim.tsv's picks ("all", or e.g. "idle,walk"); every
  other action of the model is kept as it is. A re-keyed death is laid on the ground (settle).
  Strikes are keyed on the weapons the mesh holds (grips, rig_strike): the hand that carries the
  weapon strikes, and the blade points where the strike needs it.
- skin (optional, joined by ";"): weights the build left wrong for a strike, put right before the
  bones are touched. "limbs": a hand that hangs by the hip is blended into it, and a raised arm
  pulls a sheet of hip along (unfuse). "caps": a plate that floats over a shoulder is skinned to
  the upper arm and swings behind the back with it (caps).
A model changed here loses its .rig/.joints/.cook (they hold the old bind pose): rerun
scripts/fetch_models.mjs to rewrite .rig/.joints, and `make cook`. A stamp <id>.glb.anim holds the
hash of the row and of the motion code, so a rerun skips models already current.
"""
import collections
import hashlib
import math
import pathlib
import sys

import bpy
from mathutils import Vector

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/blender"))

import attack_gate as AG  # noqa: E402
import build_unit as BU  # noqa: E402
import rig_poses as P  # noqa: E402

MODELS = ROOT / "assets/models"
TABLE = ROOT / "data/anim_refresh.tsv"
CODE = [ROOT / "tools/blender" / f for f in ("rig_motions.py", "rig_retarget.py", "rig_poses.py", "rig_strike.py",
                                              "rig_families.py", "anim_refresh.py", "attack_gate.py")] + [ROOT / "data/unit_anim.tsv"]
BLEND = 0.15     # a vertex counts for a bone from this weight up
WEAPON = 0.5     # metres from the forearm's bone beyond which a vertex is a weapon, not a sleeve (a refit bone's length varies)
MID_GRIP = 0.45  # metres the other end of what a hand holds must be from the wrist for the thing's own axis to count
FOREARM = 0.55   # metres from the elbow to the wrist on the families' arms
UPRIGHT_MIN = 1.3    # metres: a shorter "blade" pointing back up the arm is a pauldron or a sleeve, not a carried polearm


def rows():
    out = []
    for line in TABLE.read_text().splitlines()[1:]:
        if line.strip() and not line.startswith("#"):
            unit, refit, slots, *more = line.split("\t")
            hand = more[1] if len(more) > 1 and more[1][:1] in ("L", "R") else None
            skin = more[2] if len(more) > 2 and more[2] else None
            out.append((unit, None if refit == "-" else refit, None if slots == "all" else slots.split(","), hand, skin))
    return out


def stamp(row):
    """Hash of the row, the motion code and the fetched model's own stamp (a new download re-runs)."""
    h = hashlib.sha256(repr(row).encode())
    for f in CODE + [MODELS / f"{row[0]}.glb.sha256"]:
        h.update(f.read_bytes() if f.exists() else b"-")
    return h.hexdigest()


def clouds(arm):
    """(bone -> points it dominates, {bone, other} -> points blended between them), armature space."""
    own, band = collections.defaultdict(list), collections.defaultdict(list)
    to_arm = arm.matrix_world.inverted()
    for o in (o for o in bpy.data.objects if o.type == "MESH"):
        vg = {g.index: g.name for g in o.vertex_groups}
        m = to_arm @ o.matrix_world
        for v in o.data.vertices:
            gs = sorted(((g.weight, vg[g.group]) for g in v.groups if g.weight > BLEND), reverse=True)
            if gs:
                p = m @ v.co
                own[gs[0][1]].append(p)
                if len(gs) > 1:
                    band[frozenset((gs[0][1], gs[1][1]))].append(p)
    return own, band


def _tip(far, wrist):
    """The striking end of what a hand holds, among the vertices `far` from the forearm: the one
    farthest from the wrist, unless the thing stands well above the hand at rest: shafts (spear,
    staff, rifle, polearm) are carried head up, so their tip is the end that is up, however long
    the butt below the hand is."""
    if not far:
        return None
    up = max(far, key=lambda p: p.z)
    if up.z - wrist.z > 0.6 and (up - wrist).length > 0.8:
        return up
    return max(far, key=lambda p: (p - wrist).length)


def grips(arm):
    """{side: blade or None}: what each hand holds, for the strikes keyed on it (rig_strike). The
    blade is the vector from the wrist to the vertex the forearm carries farthest from its own
    bone, in the bone's rest frame; nothing farther than WEAPON metres: a bare hand, as is
    a short reach back up the arm (a pauldron, a wide sleeve)."""
    own, _ = clouds(arm)
    out = {}
    for bone in arm.data.bones:
        if not bone.name.endswith(("forearm.L", "forearm.R")):
            continue
        head = bone.head_local
        axis = (bone.tail_local - head).normalized()
        tail = head + axis * min(bone.length, FOREARM)       # the wrist: a refit bone runs on down the weapon
        far = [p for p in own.get(bone.name, ()) if _segment_distance(p, head, tail) > WEAPON]
        tip = _tip(far, tail)
        armed = tip is not None
        other = max(far, key=lambda p: (p - tip).length) if armed else None
        if armed and (other - tail).length > MID_GRIP:      # held in its middle (a bow, a staff): its own axis
            tip = tail + (tip - other).normalized() * (tip - tail).length
        if armed and (tip - tail).length < UPRIGHT_MIN and (tip - tail).normalized().dot(axis) < -0.5:
            armed = ((tip - head) - axis * (tip - head).dot(axis)).length > WEAPON       # off the arm's line: no sleeve
        armed = armed and (tip - tail).length > 1e-3        # a lone far vertex is no weapon
        out[bone.name[-1]] = tuple(bone.matrix_local.to_3x3().inverted() @ (tip - tail)) if armed else None
    return out


def held(arm, grip, hand):
    """The measured grips with the table's word on them (the `hand` column): only the hands it
    names hold a weapon; "R:out,forward,up" gives the blade as it lies at rest, "R:-" a bare hand."""
    out = dict.fromkeys(grip)
    for word in hand.split(";"):
        side, _, aim = word.partition(":")
        out[side] = grip.get(side)
        if aim == "-":
            out[side] = ()          # bare, and the hand that strikes (rig_strike.hands)
        elif aim == "still":
            out[side] = BU.sibling("rig_strike").STILL
        elif aim:
            away, forward, up = (float(c) for c in aim.split(","))
            bone = next(b for b in arm.data.bones if b.name.endswith("forearm." + side))
            blade = Vector((away if side == "L" else -away, -forward, up))
            out[side] = tuple(bone.matrix_local.to_3x3().inverted() @ blade)
    return out


def _centroid(ps):
    return sum(ps, Vector()) / len(ps)


def _closest_mid(a, b):
    best = min(((p - q).length, p, q) for p in a[:: max(1, len(a) // 200)] for q in b[:: max(1, len(b) // 200)])
    return (best[1] + best[2]) / 2


def refit(arm, family):
    own, band = clouds(arm)
    rest = {b: Vector(t) - Vector(h) for b, (h, t) in P.joints(family).items()}
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    order = [b for b in arm.data.edit_bones if b.parent is None]
    for b in order:
        order.extend(b.children)
    for b in order:
        pts = own.get(b.name, ())
        if len(pts) < 4:
            continue
        parent = b.parent
        shared = band.get(frozenset((b.name, parent.name)), ()) if parent else ()
        if len(shared) >= 3:
            head = _centroid(shared)
        elif parent and len(own.get(parent.name, ())) >= 4:
            head = _closest_mid(pts, own[parent.name])
        else:
            head = _centroid(pts)
        d = rest.get(b.name, b.tail - b.head)
        d = d.normalized() if d.length > 1e-6 else Vector((0, 0, 1))
        reach = max((p - head).dot(d) for p in pts)
        b.use_connect = False
        b.head, b.tail = head, head + d * max(reach, 0.02)
        b.roll = 0.0
    bpy.ops.object.mode_set(mode="OBJECT")


def _percentile(values, q):
    s = sorted(values)
    return s[min(len(s) - 1, max(0, int(q * (len(s) - 1))))]


def _segment_distance(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-12)))
    return (p - (a + ab * t)).length


def rerig(arm, family):
    """Replace a skeleton that does not fit its mesh (a four-legged body on biped bones) by the
    family's own, laid on the mesh: the rest joints are stretched per axis onto the mesh's extent
    (2nd to 98th percentile, so a stray vertex does not stretch it); then the bones along the middle
    (spine, neck, head, tail) sit at the median height of the mesh across their length, and each leg
    runs from that height down to the ground (a raised tail would otherwise lift the spine above a
    low body). Each vertex is skinned to its two nearest bones by inverse squared distance. Returns
    the new armature; the mesh is not moved."""
    meshes = [o for o in bpy.data.objects if o.type == "MESH"
              and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)]
    to_arm = arm.matrix_world.inverted()
    pts = [to_arm @ o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
    joints = P.joints(family)
    span = []
    for i in range(3):
        lo, hi = _percentile([p[i] for p in pts], 0.02), _percentile([p[i] for p in pts], 0.98)
        flo = min(min(h[i], t[i]) for h, t in joints.values())
        fhi = max(max(h[i], t[i]) for h, t in joints.values())
        span.append((flo, fhi, lo, hi))
    slab = 0.06 * (span[1][3] - span[1][2])

    def stretch(v):
        return Vector([lo + (v[i] - flo) / max(fhi - flo, 1e-6) * (hi - lo)
                       for i, (flo, fhi, lo, hi) in enumerate(span)])

    def midline(y):
        zs = [p[2] for p in pts if abs(p[1] - y) < slab]
        return _percentile(zs, 0.5) if len(zs) >= 5 else None

    # one lift for the whole middle chain, measured at mid-body: the bones keep the family's
    # directions (the frames its clips are keyed in), only their height follows the mesh
    centre = min((v for n, (h, t) in joints.items() if n != "root" for v in (h, t) if abs(v[0]) < 0.05),
                 key=lambda v: abs(v[1]))
    body = midline(stretch(centre)[1])
    lift = body - stretch(centre)[2] if body is not None else 0.0

    def place(name, v):
        p = stretch(v)
        chain = name.split(".")[0]
        if chain.startswith("leg"):             # the leg runs from the lifted body down to the ground
            top, foot = joints[chain + ".upper"][0], joints[chain + ".lower"][1]
            ground, hip = stretch(foot)[2], stretch(top)[2] + lift
            p[2] = ground + (hip - ground) * (v[2] - foot[2]) / max(top[2] - foot[2], 1e-6)
        elif name != "root":
            p[2] += lift
        return p

    data = bpy.data.armatures.new("rig")
    new = bpy.data.objects.new("rig", data)
    bpy.context.collection.objects.link(new)
    new.matrix_world = arm.matrix_world.copy()
    bpy.context.view_layer.objects.active = new
    bpy.ops.object.mode_set(mode="EDIT")
    table = P.rest(family)
    for name, (h, t) in joints.items():
        b = data.edit_bones.new(name)
        b.head, b.tail = place(name, h), place(name, t)
    for name, (parent, *_) in table.items():
        if parent is not None:
            data.edit_bones[name].parent = data.edit_bones[parent]
    segs = {b.name: (b.head.copy(), b.tail.copy()) for b in data.edit_bones if b.name != "root"}
    bpy.ops.object.mode_set(mode="OBJECT")
    for o in meshes:
        m = to_arm @ o.matrix_world
        o.vertex_groups.clear()
        groups = {name: o.vertex_groups.new(name=name) for name in segs}
        for v in o.data.vertices:
            p = m @ v.co
            near = sorted((_segment_distance(p, a, b), name) for name, (a, b) in segs.items())[:2]
            w = [1.0 / max(d, 1e-4) ** 2 for d, _ in near]
            for (_, name), wi in zip(near, w):
                groups[name].add([v.index], wi / sum(w), "REPLACE")
        for mod in o.modifiers:
            if mod.type == "ARMATURE":
                mod.object = new
        world = o.matrix_world.copy()
        o.parent = new
        o.matrix_world = world
    bpy.data.objects.remove(arm)
    return new


_ARMS, _LOWER = ("arm.", "forearm."), ("pelvis", "thigh.", "shin.", "foot.")


def _islands(mesh):
    """The mesh's connected pieces as lists of vertices; vertices at one place are one (glTF
    splits them along seams)."""
    parent = list(range(len(mesh.vertices)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    seen = {}
    for v in mesh.vertices:
        parent[find(v.index)] = find(seen.setdefault(tuple(round(c, 4) for c in v.co), v.index))
    for e in mesh.edges:
        parent[find(e.vertices[0])] = find(e.vertices[1])
    out = collections.defaultdict(list)
    for v in mesh.vertices:
        out[find(v.index)].append(v)
    return list(out.values())


def _weights(obj, verts):
    """{bone: weight summed over the vertices}."""
    names = {g.index: g.name for g in obj.vertex_groups}
    total = collections.Counter()
    for v in verts:
        for g in v.groups:
            total[names[g.group]] += g.weight
    return total


def _drop(arm, obj, verts, prefixes):
    """Take the vertices off the bones named by `prefixes`; what each keeps is scaled back to 1,
    and one that keeps nothing goes to the nearest of the piece's other bones."""
    others = [arm.data.bones[name] for name in _weights(obj, verts) if not name.startswith(prefixes)]
    to_arm = arm.matrix_world.inverted() @ obj.matrix_world
    for v in verts:
        held = [(obj.vertex_groups[g.group], g.weight) for g in v.groups]
        kept = [(group, w) for group, w in held if not group.name.startswith(prefixes)]
        if len(kept) == len(held):
            continue
        if sum(w for _, w in kept) < 1e-6:
            near = min(others, key=lambda bone: _segment_distance(to_arm @ v.co, bone.head_local, bone.tail_local))
            kept = [(obj.vertex_groups[near.name], 1.0)]
        for group, _ in held:
            group.remove([v.index])
        total = sum(w for _, w in kept)
        for group, w in kept:
            group.add([v.index], w / total, "REPLACE")


def unfuse(arm, obj):
    """skin "limbs": an arm that hangs against the hip is skinned to it where the two touch (each
    vertex takes the bone of the nearest part), and raised to strike it pulls a sheet from the
    hip. A piece of the mesh the arms carry more of than the hips and legs is the arm's own:
    it lets go of those; every other piece lets go of the forearms."""
    for verts in _islands(obj.data):
        total = _weights(obj, verts)
        arms = sum(w for bone, w in total.items() if bone.startswith(_ARMS))
        lower = sum(w for bone, w in total.items() if bone.startswith(_LOWER))
        if arms and lower:
            _drop(arm, obj, verts, _LOWER if arms > lower else ("forearm.",))


def caps(arm, obj):
    """skin "caps": a piece skinned wholly to an upper arm that lies wholly above its shoulder (a
    plate, a lid floating over it) rides the bone the arm hangs from: on the arm it swings
    behind the back as the arm goes up."""
    to_arm = arm.matrix_world.inverted() @ obj.matrix_world
    for verts in _islands(obj.data):
        total = _weights(obj, verts)
        name = max(total, key=total.get, default="")
        bone = arm.data.bones.get(name)
        if not name.startswith("arm.") or bone.parent is None or total[name] < 0.99 * sum(total.values()):
            continue
        axis = bone.tail_local - bone.head_local
        if all((to_arm @ v.co - bone.head_local).dot(axis) < 0 for v in verts):
            index = [v.index for v in verts]
            obj.vertex_groups[name].remove(index)
            (obj.vertex_groups.get(bone.parent.name) or obj.vertex_groups.new(name=bone.parent.name)).add(index, 1.0, "REPLACE")


SKIN = {"limbs": unfuse, "caps": caps}


def reskin(arm, words):
    """The row's skin fixes ("limbs;caps"; None: nothing) on every mesh the armature carries."""
    for obj in [o for o in bpy.data.objects if o.type == "MESH" and o.vertex_groups]:
        for word in filter(None, (words or "").split(";")):
            SKIN[word](arm, obj)


SOFTER = (1.0, 0.9, 0.8, 0.7, 0.55)      # shares of a strike's arc tried in turn until the mesh holds


def _tears(arm, state, acts):
    """True when an attack action opens a gap or pulls a ribbon in the mesh (attack_gate.torn)."""
    worst = {"gap": 0.0, "ribbon": 0.0}
    for act in acts:
        arm.animation_data.action = act
        for frame in range(int(act.frame_range[0]), int(act.frame_range[1]) + 1):
            bpy.context.scene.frame_set(frame)
            gap, ribbon = AG.mesh_damage(state)
            worst = {"gap": max(worst["gap"], gap), "ribbon": max(worst["ribbon"], ribbon)}
    arm.animation_data.action = None
    return bool(AG.torn(worst))


def fit(arm, family):
    """(reach, legs) of the unit for rig_motions.clips, or None for a family whose strikes do not travel:
    its length along the body (the skinned meshes' boxes) over the length the family's strikes were
    drawn for (rig_motions.FITTED), and its legs' length over the family's (their feet are held by IK
    solved in the family's proportions)."""
    drawn = BU.sibling("rig_motions").FITTED.get(family)
    ys = [(o.matrix_world @ Vector(c)).y for o in bpy.data.objects if o.type == "MESH" and o.vertex_groups
          for c in o.bound_box]
    if drawn is None or not ys:
        return None
    joints = P.joints(family)
    legs = sorted(b.length / math.dist(*joints[b.name]) for b in arm.data.bones
                  if b.name.startswith("leg") and b.name in joints)
    reach = min(max((max(ys) - min(ys)) / drawn, 0.6), 3.5)
    return (round(reach, 2), round(min(max(legs[len(legs) // 2], 0.3), 1.5), 2) if legs else 1.0)


def keyed(arm):
    """build_unit.make_actions, the strikes' arcs backed off (SOFTER) for a mesh that tears on the
    full ones: a smaller swing that still reads beats an arm pulled into a ribbon. Returns the
    share kept."""
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.vertex_groups]
    state = AG.mesh_rest(arm, meshes) if meshes else None
    for soft in SOFTER:
        BU.SOFT = soft
        BU.make_actions(arm)
        made = [a for a in bpy.data.actions if not a.name.startswith("__old_")]
        if state is None or soft == SOFTER[-1] or not _tears(arm, state, [a for a in made if a.name.startswith("attack")]):
            break
        for act in made:
            bpy.data.actions.remove(act)
    BU.SOFT = 1.0
    return soft


def to_quaternion(arm, act):
    """make_actions keys rotation_euler with the bones in XYZ; the kept glTF actions key
    rotation_quaternion. Re-key `act` as quaternions so one rotation mode serves both. Each
    sample starts from rest: a bone the action leaves unkeyed would otherwise keep the pose the
    previous action left on it (a death's roll-over baked into an idle)."""
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
    arm.animation_data.action = act
    curves = [f for layer in act.layers for s in layer.strips for cb in s.channelbags for f in cb.fcurves]
    frames = sorted({int(round(k.co[0])) for f in curves for k in f.keyframe_points})
    samples = []
    for fr in frames:
        for pb in arm.pose.bones:
            pb.rotation_euler, pb.location = (0, 0, 0), (0, 0, 0)
        bpy.context.scene.frame_set(fr)
        samples.append((fr, {pb.name: (pb.rotation_euler.to_quaternion(), pb.location.copy()) for pb in arm.pose.bones}))
    for layer in act.layers:
        for s in layer.strips:
            for cb in s.channelbags:
                for f in [f for f in cb.fcurves if f.data_path.endswith("rotation_euler")]:
                    cb.fcurves.remove(f)
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    last = {}
    for fr, pose in samples:
        for name, (q, loc) in pose.items():
            if name in last:
                q.make_compatible(last[name])
            last[name] = q
            pb = arm.pose.bones[name]
            pb.rotation_quaternion, pb.location = q, loc
            pb.keyframe_insert("rotation_quaternion", frame=fr)
            pb.keyframe_insert("location", frame=fr)
    arm.animation_data.action = None


def _lowest(meshes):
    """World height of the lowest skinned vertex in the current pose."""
    graph = bpy.context.evaluated_depsgraph_get()
    low = float("inf")
    for o in meshes:
        ev = o.evaluated_get(graph)
        mesh = ev.to_mesh()
        low = min(low, min((ev.matrix_world @ v.co).z for v in mesh.vertices))
        ev.to_mesh_clear()
    return low


def settle(arm, act):
    """Lay a death on the ground: on every keyed frame the root is raised until the lowest skinned
    vertex is back at the rest pose's floor (never lowered). rig_motions.plant measures joints and
    skips the hovering families, so a body rolled over its root ends half under the ground."""
    meshes = [o for o in bpy.data.objects if o.type == "MESH"
              and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)]
    root = next(pb for pb in arm.pose.bones if pb.parent is None)
    to_bone = (arm.matrix_world.to_3x3() @ root.bone.matrix_local.to_3x3()).inverted()
    for pb in arm.pose.bones:
        pb.rotation_quaternion, pb.location = (1, 0, 0, 0), (0, 0, 0)
    arm.animation_data.action = None
    bpy.context.view_layer.update()
    floor = min(_lowest(meshes), 0.0)
    arm.animation_data.action = act
    curves = [f for layer in act.layers for s in layer.strips for cb in s.channelbags for f in cb.fcurves]
    for fr in sorted({round(k.co[0]) for f in curves for k in f.keyframe_points}):
        bpy.context.scene.frame_set(fr)
        sunk = floor - _lowest(meshes)
        if sunk > 1e-4:
            root.location = root.location + to_bone @ Vector((0, 0, sunk))
            root.keyframe_insert("location", frame=fr)
    arm.animation_data.action = None


def refresh(unit, family, slots, hand=None, skin=None):
    path = MODELS / f"{unit}.glb"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    rig = next((r.split("\t")[1] for r in (ROOT / "data/unit_anim.tsv").read_text().splitlines()
                if r.split("\t")[0] == unit), None)
    if rig is None:
        raise SystemExit(f"{unit}: no row in data/unit_anim.tsv")
    reskin(arm, skin)
    if family and family.startswith("rerig:"):
        if slots is not None:
            raise SystemExit(f"{unit}: a new skeleton needs every clip re-keyed (slots = all)")
        arm = rerig(arm, family[len("rerig:"):])
    elif family:
        refit(arm, family)
    if arm.animation_data:                  # the importer stacks every clip on NLA tracks: they would
        for track in list(arm.animation_data.nla_tracks):    # blend into the samples; ACTIONS export
            arm.animation_data.nla_tracks.remove(track)       # writes the actions without them
    old = {}
    for act in list(bpy.data.actions):
        name, act.name = act.name, "__old_" + act.name
        act.use_fake_user = True
        old[name] = act
    BU.FAMILY, BU.ANIM, BU.GRIP = rig, BU.sibling("rig_motions").unit_picks(unit, rig), grips(arm)
    if hand:                # the table names the weapon hand: what the other one carries is a shield
        BU.GRIP = held(arm, BU.GRIP, hand)
    BU.FIT = fit(arm, rig)
    print(f"anim_refresh: {unit}: fit (reach, legs) {BU.FIT}", flush=True)
    soft = keyed(arm)
    BU.FIT = None
    if soft < 1.0:
        print(f"anim_refresh: {unit}: strikes at {soft:.2f} of their arc (the mesh tears on more)", flush=True)
    new = {a.name: a for a in bpy.data.actions if not a.name.startswith("__old_")}
    missing = sorted(set(slots or ()) - set(new))
    if missing:
        raise SystemExit(f"{unit}: make_actions made no {missing}")
    for name in set(old) | set(new):
        if slots is None or name.rstrip("0123456789") in slots:     # "attack" names a combo's attack2, attack3 too
            if name in old:
                bpy.data.actions.remove(old[name])
            if name in new:
                to_quaternion(arm, new[name])
                if name == "death":
                    settle(arm, new[name])
        else:
            if name in new:
                bpy.data.actions.remove(new[name])
            old[name].name = name
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion, pb.location = (1, 0, 0, 0), (0, 0, 0)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", export_yup=True,
                              export_animations=True, export_animation_mode="ACTIONS",
                              export_apply=False, export_skins=True, export_morph=False)
    for side in (".rig", ".joints", ".cook"):
        (MODELS / f"{unit}{side}").unlink(missing_ok=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    done = 0
    for row in rows():
        unit = row[0]
        if argv and unit not in argv:
            continue
        mark = MODELS / f"{unit}.glb.anim"
        want = stamp(row)
        if mark.exists() and mark.read_text() == want:
            continue
        refresh(*row)
        mark.write_text(want)
        done += 1
        print(f"anim_refresh: {unit}", flush=True)
    print(f"anim_refresh: {done} model(s) re-keyed")


if __name__ == "__main__":
    main()
