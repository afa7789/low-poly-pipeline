"""Re-key chosen clips of prepared unit models from today's motion library, and re-seat or replace
skeletons that do not fit their mesh (data/anim_refresh.tsv). Runs on assets/models after
scripts/fetch_models.mjs and tools/inject_clips.py; meshes and textures are not touched.

    blender -b -P tools/blender/anim_refresh.py [-- unit_id ...]

Per row of data/anim_refresh.tsv (unit_id, refit, slots):
- refit = a rig family (e.g. drake): each bone's pivot moves onto the joint its skinned mesh bends
  at (the centroid of the vertices blended between the bone and its parent; without such a band the
  midpoint of the two clouds' closest points; with no skinned parent, its own centroid), and takes
  the family's rest direction with roll 0, the frame build_unit.make_actions keys clips in.
  rerig:<family> = the skeleton does not fit the body at all (four legs on biped bones): it is
  replaced by the family's, stretched onto the mesh, and every vertex is skinned anew (rerig).
  "-" = neither.
- slots = the actions re-keyed from data/unit_anim.tsv's picks ("all", or e.g. "idle,walk"); every
  other action of the model is kept as it is. A re-keyed death is laid on the ground (settle).
A model changed here loses its .rig/.joints/.cook (they hold the old bind pose): rerun
scripts/fetch_models.mjs to rewrite .rig/.joints, and `make cook`. A stamp <id>.glb.anim holds the
hash of the row and of the motion code, so a rerun skips models already current.
"""
import collections
import hashlib
import pathlib
import sys

import bpy
from mathutils import Vector

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/blender"))

import build_unit as BU  # noqa: E402
import rig_poses as P  # noqa: E402

MODELS = ROOT / "assets/models"
TABLE = ROOT / "data/anim_refresh.tsv"
CODE = [ROOT / "tools/blender" / f for f in ("rig_motions.py", "rig_retarget.py", "rig_poses.py",
                                              "rig_families.py", "anim_refresh.py")] + [ROOT / "data/unit_anim.tsv"]
BLEND = 0.15     # a vertex counts for a bone from this weight up


def rows():
    out = []
    for line in TABLE.read_text().splitlines()[1:]:
        if line.strip() and not line.startswith("#"):
            unit, refit, slots, *_ = line.split("\t")
            out.append((unit, None if refit == "-" else refit, None if slots == "all" else slots.split(",")))
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


def refresh(unit, family, slots):
    path = MODELS / f"{unit}.glb"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    rig = next((r.split("\t")[1] for r in (ROOT / "data/unit_anim.tsv").read_text().splitlines()
                if r.split("\t")[0] == unit), None)
    if rig is None:
        raise SystemExit(f"{unit}: no row in data/unit_anim.tsv")
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
    BU.FAMILY, BU.ANIM = rig, BU.sibling("rig_motions").unit_picks(unit, rig)
    BU.make_actions(arm)
    new = {a.name: a for a in bpy.data.actions if not a.name.startswith("__old_")}
    missing = sorted(set(slots or ()) - set(new))
    if missing:
        raise SystemExit(f"{unit}: make_actions made no {missing}")
    for name in set(old) | set(new):
        if slots is None or name in slots:
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
