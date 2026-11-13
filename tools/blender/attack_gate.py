"""Does an attack clip read as a weapon strike, or as a body lean? A measurable gate.

    blender -b -P tools/blender/attack_gate.py -- <model.glb> [out.json] [clip+clip+...]
    python3 tools/blender/attack_gate.py --ref <capture> <clip> [blade]      (no Blender)

Per attack action (attack, attack2, ...) of the model:
- strike   how far the striking effector gets in at most WINDOW frames, in body heights, when it
           then holds its place for HOLD_FRAMES frames (the contact pose): a flick that comes
           straight back is no strike. Measured from the root, so a lunge of the whole body does
           not count; the move must end in front of the root and not go backward (the off hand
           swinging back is no strike). Effectors are the limb ends (leaf bones that are not wings,
           tails or legs of a biped) and, on each, the skinned vertex farthest from the joint: a
           blade's tip, a claw, a snout. The one that gets farthest is the striking one.
- line     that reach over the path travelled: 1 is a straight thrust, a swing bends.
- arm      share of the strike the limb itself makes: the same move measured in the frame of the
           trunk the limb hangs from (the first ancestor that carries more than one limb). A lean
           of the torso swings a long weapon's tip a long way without the arm doing anything.
- root     the root's largest horizontal move from the first frame, in body heights.
- torso    range of the torso's pitch, degrees.
- move     the farthest any effector gets from where it started, body included, in body heights.
- gap      the widest gap that opens between the vertices of a bone and of its parent, over what
           is there at rest, in body heights: a forearm or a weapon that floats off its arm.
- ribbon   the summed length, in body heights, of the edges stretched to RIBBON_FROM times their
           rest length or more: an arm or a robe pulled into a band. Both come from joints that do
           not sit where the mesh bends (anim_refresh refits them) or from a pose the skin cannot
           take; an action over GAP or RIBBON fails whatever its kind.
The clips named last (the unit's attack pick of data/unit_anim.tsv, one per attack action) say what
each action is (kind_of): a shot, a spell or a machine's recoil only has to show (MOVES of move, or
a torso or root that visibly rocks); a strike made with the body itself (a bite, a headbutt, a kick,
a pounce) needs BODY of strike, its root within LEAP. Everything else is a melee strike:
PASS: a thrust (line >= STRAIGHT, or a bare limb: no blade reaching ARMED body heights past the
joint) travels THRUST or more, a swing SWING or more, ARM of it or
more by the limb; the root stays within ROOT and the torso within TORSO. Exit code 1 when any attack fails.

--ref grades a captured reference (artifacts/anim-ref/<capture>/joints.json) on its own joints. The
captures hold no weapon, so the effector is the hand, plus, with `blade` (body heights), a blade
held square to the forearm as KayKit's are: its direction is the forward axis of the hanging arm,
carried along by the forearm without twist (an estimate: the capture has no hand roll).
"""
import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

WINDOW = 8          # frames at 24 fps: a strike is over in a third of a second
BACK = 0.25         # share of a strike's reach it may go backward
HOLD, HOLD_FRAMES = 0.12, 2     # the contact pose: the effector stays within HOLD body heights this long
STRAIGHT = 0.85     # chord / path from which a travel counts as a thrust
THRUST, SWING = 0.5, 0.7        # body heights
GAP, RIBBON, RIBBON_FROM = 0.08, 15.0, 2.5      # body heights, body heights of stretched edge, stretch ratio
ARMED = 0.25                    # body heights past the joint from which a tip is a weapon's
MOVES = 0.10                    # body heights something must move for a shot or a recoil to show
BODY, LEAP = 0.3, 0.6           # a snout's or a hoof's strike, and how far a body that strikes may go
RANGED = ("bow", "shoot", "burst", "cast", "keyed_spit", "keyed_recoil", "keyed_shoot", "keyed_fire", "hipfire",
          "breath", "keyed_quill", "keyed_tail_shot", "keyed_back_tube", "keyed_bomb", "keyed_strafe", "keyed_aim",
          "keyed_pulse", "keyed_brace", "pulse", "wyvern_breath", "keyed_warcry", "keyed_roar", "summon", "cheer", "lash",
          "staff_point", "fan_gust", "flail_sling", "hawk", "spit")
BODIES = ("bite", "headbutt", "keyed_ram", "keyed_pounce", "jump", "keyed_rear_up", "keyed_spike_gore", "kick",
          "mount_kick", "lunge", "strike", "keyed_lash", "keyed_arm_slam", "pinch", "sting", "wyvern_sting", "claw",
          "charge", "keyed_sting", "mount_bite", "maul", "gore", "paw_slam", "keyed_bite_volley")
ARM = 0.5                       # share of the strike the limb makes, the trunk held still
ROOT, TORSO = 0.15, 35.0        # body heights, degrees
NOT_STRIKING = ("wing", "tail", "foot", "shin", "thigh", "wheel")
TORSOS = ("spine", "spine.2", "spine.1", "body", "hull", "pelvis", "base")


# ---------------------------------------------------------------- pure: tracks -> verdict
def path(points):
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


def strike(points, height, window=WINDOW):
    """(reach, path, first frame index) of a point's largest move over at most `window` frames that
    ends in a held pose: the HOLD_FRAMES frames after it stay within HOLD body heights of where it
    arrived (a clip's end holds). A flick that comes straight back is no strike, nor is a move
    that ends behind the root or goes backward (BACK of its reach or more): points are measured
    from the root, forward -y. Returns (reach, path, first frame, last frame)."""
    best = (0.0, 0.0, 0, 0)
    for j in range(1, len(points)):
        after = points[j + 1:j + 1 + HOLD_FRAMES]
        if points[j][1] > 0.0 or any(math.dist(points[j], p) > HOLD * height for p in after):
            continue
        for i in range(max(0, j - window), j):
            reach = math.dist(points[i], points[j])
            if reach > best[0] and points[j][1] - points[i][1] <= BACK * reach:
                best = (reach, path(points[i:j + 1]), i, j)
    return best


def pitch_range(directions):
    """Range in degrees of the pitch (side view: forward -y, up z) of a bone's direction."""
    angles = [math.degrees(math.atan2(-d[1], d[2])) for d in directions]
    for i in range(1, len(angles)):                 # no jump at +-180 (a lying body)
        angles[i] -= 360.0 * round((angles[i] - angles[i - 1]) / 360.0)
    return max(angles) - min(angles)


def grade(tips, limbs, root, torso, height, window=WINDOW, kind="melee", armed=None):
    """tips {effector: [point per frame, in armature space]}, limbs the same points in their
    trunks' frames, root [point per frame], torso [direction per frame] ->
    {"effector", "strike", "line", "arm", "at", "root", "torso", "fails"} (lengths in body heights)."""
    def from_root(pts):
        return [(p[0] - r[0], p[1] - r[1], p[2]) for p, r in zip(pts, root)]
    reach, travel, start, end, name = max((*strike(from_root(pts), height, window), name) for name, pts in tips.items())
    out = {"effector": name, "strike": reach / height, "at": start,
           "line": reach / travel if travel > 1e-9 else 1.0,
           "arm": math.dist(limbs[name][start], limbs[name][end]) / reach if reach > 1e-9 else 0.0,
           "root": max(math.hypot(p[0] - root[0][0], p[1] - root[0][1]) for p in root) / height,
           "torso": pitch_range(torso), "kind": kind, "armed": armed is None or name in armed,
           "move": max(math.dist(p, pts[0]) for pts in tips.values() for p in pts) / height}
    out["fails"] = fails(out, kind)
    return out


def kind_of(clip):
    """"ranged", "body" or "melee": what an attack clip of the motion library has to show."""
    if clip.startswith(RANGED):
        return "ranged"
    return "body" if clip.startswith(BODIES) else "melee"


def _fails_other(m, kind):
    if kind == "ranged":
        shows = m["move"] >= MOVES or m["torso"] >= 6.0 or m["root"] >= 0.03
        return [] if shows else [f"nothing moves ({m['move']:.2f} < {MOVES})"]
    return ([f"body strike {m['strike']:.2f} < {BODY}"] if m["strike"] < BODY else []) + (
        [f"root {m['root']:.2f} > {LEAP}"] if m["root"] > LEAP else [])


def torn(m):
    """Reasons a clip tears the mesh (empty: it holds)."""
    return ([f"gap {m['gap']:.2f} > {GAP}"] if m.get("gap", 0.0) > GAP else []) + (
        [f"ribbon {m['ribbon']:.0f} > {RIBBON:.0f}"] if m.get("ribbon", 0.0) > RIBBON else [])


def fails(m, kind="melee"):
    """What a graded attack fails, as short reasons (empty: PASS)."""
    return torn(m) + (_fails_other(m, kind) if kind != "melee" else _fails_melee(m))


def _fails_melee(m):
    thrust = m["line"] >= STRAIGHT or not m.get("armed", True)     # a bare hand has no arc to draw
    need = THRUST if thrust else SWING
    out = []
    if m["strike"] < need:
        out.append(f"{'thrust' if thrust else 'swing'} {m['strike']:.2f} < {need}")
    if m["arm"] < ARM:
        out.append(f"arm {m['arm']:.2f} < {ARM}")
    if m["root"] > ROOT:
        out.append(f"root {m['root']:.2f} > {ROOT}")
    if m["torso"] > TORSO:
        out.append(f"torso {m['torso']:.0f} > {TORSO:.0f}")
    return out


def line(name, m):
    verdict = "PASS" if not m["fails"] else "FAIL (" + "; ".join(m["fails"]) + ")"
    return (f"{name:10s} {m.get('clip', '')} [{m.get('kind', 'melee')}] strike {m['strike']:.2f} H ({m['effector']}, line {m['line']:.2f}, arm {m['arm']:.2f}, "
            f"from frame {m['at'] + 1})  root {m['root']:.2f} H  torso {m['torso']:.0f} deg  {verdict}")


# ---------------------------------------------------------------- a captured reference
def _resample(samples, frames):
    """Evenly captured samples of a clip `frames` long -> one per frame (linear)."""
    out = []
    for f in range(frames + 1):
        t = f * (len(samples) - 1) / max(frames, 1)
        i = min(int(t), len(samples) - 2)
        out.append([samples[i][k] + (samples[i + 1][k] - samples[i][k]) * (t - i) for k in range(3)])
    return out


def _blade(lower, hand, length):
    """Tip of a blade held square to the forearm: the hanging arm's forward axis (-y), carried by
    the shortest turn from straight down to the forearm's direction."""
    import rig_poses as P
    d = [hand[i] - lower[i] for i in range(3)]
    b = P.turn((0.0, 0.0, -1.0), d, (0.0, -1.0, 0.0))
    return [hand[i] + b[i] * length for i in range(3)]


def _chest(f):
    """A reference frame's chest as (origin, [left, back, up] axes): up along the spine, left
    along the shoulders (Blender axes, the figure facing -y)."""
    import rig_poses as P
    up = P.turn((0, 0, 1), [f["spine"][1][i] - f["spine"][0][i] for i in range(3)], (0, 0, 1))
    across = [f["upperarm.l"][0][i] - f["upperarm.r"][0][i] for i in range(3)]
    dot = sum(a * b for a, b in zip(across, up))
    left = [a - dot * b for a, b in zip(across, up)]
    n = math.hypot(*left) or 1.0
    left = [c / n for c in left]
    back = [up[1] * left[2] - up[2] * left[1], up[2] * left[0] - up[0] * left[2], up[0] * left[1] - up[1] * left[0]]
    return f["chest"][0], (left, back, up)


def _local(frame, p):
    origin, axes = frame
    d = [p[i] - origin[i] for i in range(3)]
    return [sum(a * b for a, b in zip(axis, d)) for axis in axes]


def grade_ref(capture, clip, blade=0.0):
    import rig_retarget as RT
    ref = RT.load(capture)
    samples, (start, end) = ref["clips"][clip], ref["frames"][clip]
    height = ref["rest"]["head"][1][2]
    tips = {}
    for s in "lr":
        tips[f"hand.{s}"] = [f[f"hand.{s}"][0] for f in samples]
        if blade:
            tips[f"blade.{s}"] = [_blade(f[f"lowerarm.{s}"][0], f[f"hand.{s}"][0], blade * height) for f in samples]
    chests = [_chest(f) for f in samples]
    limbs = {name: _resample([_local(c, p) for c, p in zip(chests, pts)], end - start) for name, pts in tips.items()}
    tips = {name: _resample(pts, end - start) for name, pts in tips.items()}
    root = _resample([f["hips"][0] for f in samples], end - start)
    torso = _resample([[f["spine"][1][i] - f["spine"][0][i] for i in range(3)] for f in samples], end - start)
    return grade(tips, limbs, root, torso, height)


# ---------------------------------------------------------------- a model (Blender)
def effectors(arm, meshes):
    """({effector: (bone, trunk, rest point)}, body height): each striking leaf bone's tail and the
    vertex it dominates farthest from its head. The height is the top of the vertices of the
    other bones and of the head, over the floor."""
    leaves = [b for b in arm.data.bones if not b.children and b.parent and not b.name.startswith(NOT_STRIKING)]
    far = {b.name: (b.tail_local.copy(), 0.0) for b in leaves}
    to_arm = arm.matrix_world.inverted()
    top, floor = 0.0, float("inf")
    for o in meshes:
        groups = {g.index: g.name for g in o.vertex_groups}
        m = to_arm @ o.matrix_world
        for v in o.data.vertices:
            if not v.groups:
                continue
            bone = groups[max(v.groups, key=lambda g: g.weight).group]
            p = m @ v.co
            floor = min(floor, p.z)
            if bone not in far or bone.startswith("head"):
                top = max(top, p.z)
            if bone in far:
                reach = (p - arm.data.bones[bone].head_local).length
                if reach > far[bone][1]:
                    far[bone] = (p, reach)
    out = {}
    for b in leaves:
        out[b.name] = (b.name, _trunk(b), b.tail_local.copy())
        if far[b.name][1] > 0.0:
            out[b.name + ":tip"] = (b.name, _trunk(b), far[b.name][0])
    return out, (top - floor) or 1.0


def _trunk(bone):
    """The bone a limb hangs from: the first ancestor that carries more than one child."""
    trunk = bone.parent
    while trunk.parent and len(trunk.children) < 2:
        trunk = trunk.parent
    return trunk.name


def mesh_rest(arm, meshes):
    """What mesh_damage compares a pose with: the largest skinned mesh at rest, its edges and
    their lengths, its height, and per bone that has a skinned parent a sample of both vertex sets
    with the distance between them."""
    import bpy
    import numpy as np
    mesh = max(meshes, key=lambda o: len(o.data.vertices))
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    if arm.animation_data:
        arm.animation_data.action = None
    bpy.context.view_layer.update()
    rest = _posed(mesh)
    edges = np.array([e.vertices[:] for e in mesh.data.edges])
    names = {g.index: g.name for g in mesh.vertex_groups}
    sets = {}
    for v in mesh.data.vertices:
        if v.groups:
            sets.setdefault(names[max(v.groups, key=lambda g: g.weight).group], []).append(v.index)
    pairs = []
    for b in arm.data.bones:
        if b.parent and b.name in sets and b.parent.name in sets:
            a, p = (np.array(sets[n][::max(1, len(sets[n]) // 120)]) for n in (b.name, b.parent.name))
            pairs.append((a, p, np.linalg.norm(rest[a][:, None] - rest[p][None], axis=2).min()))
    return {"mesh": mesh, "edges": edges, "pairs": pairs, "height": float(np.ptp(rest[:, 2])) or 1.0,
            "lengths": np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1) + 1e-9}


def _posed(mesh):
    import bpy
    import numpy as np
    ev = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m = ev.to_mesh()
    out = np.array([v.co[:] for v in m.vertices])
    ev.to_mesh_clear()
    return out


def mesh_damage(state):
    """(gap, ribbon) of the pose the scene is in, see the module's docstring."""
    import numpy as np
    p, edges = _posed(state["mesh"]), state["edges"]
    now = np.linalg.norm(p[edges[:, 0]] - p[edges[:, 1]], axis=1)
    ribbon = float(now[now / state["lengths"] > RIBBON_FROM].sum()) / state["height"]
    gap = max((float(np.linalg.norm(p[a][:, None] - p[b][None], axis=2).min() - d) for a, b, d in state["pairs"]),
              default=0.0)
    return gap / state["height"], ribbon


def _torso(arm):
    return next((arm.pose.bones[n] for n in TORSOS if n in arm.pose.bones), arm.pose.bones[0])


def grade_action(arm, act, points, height, kind="melee", state=None):
    import bpy
    arm.animation_data_create()
    arm.animation_data.action = act
    if act.slots:
        arm.animation_data.action_slot = act.slots[0]
    root = next(pb for pb in arm.pose.bones if pb.parent is None)
    torso = _torso(arm)
    tips, limbs, roots, pitches = {name: [] for name in points}, {name: [] for name in points}, [], []
    gap = ribbon = 0.0
    for frame in range(int(act.frame_range[0]), int(act.frame_range[1]) + 1):
        for pb in arm.pose.bones:                   # a channel the clip leaves out is at rest
            pb.matrix_basis.identity()
        bpy.context.scene.frame_set(frame)
        for name, (bone, trunk, rest) in points.items():
            pb = arm.pose.bones[bone]
            world = pb.matrix @ pb.bone.matrix_local.inverted() @ rest
            tips[name].append(tuple(world))
            limbs[name].append(tuple(arm.pose.bones[trunk].matrix.inverted() @ world))
        if state:
            g, r = mesh_damage(state)
            gap, ribbon = max(gap, g), max(ribbon, r)
        roots.append(tuple(root.matrix.translation))
        pitches.append(tuple(torso.tail - torso.head))
    armed = {name for name, (bone, _, rest) in points.items()
             if (rest - arm.data.bones[bone].tail_local).length > ARMED * height}
    out = grade(tips, limbs, roots, pitches, height, kind=kind, armed=armed)
    out.update(gap=gap, ribbon=ribbon)
    out["fails"] = fails(out, kind)
    return out


def grade_model(glb, clips=()):
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    if arm.animation_data:
        for track in list(arm.animation_data.nla_tracks):
            arm.animation_data.nla_tracks.remove(track)
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.vertex_groups]
    points, height = effectors(arm, meshes)
    acts = sorted((a for a in bpy.data.actions if a.name.startswith("attack")), key=lambda a: a.name)
    names = dict(zip((a.name for a in acts), clips))
    state = mesh_rest(arm, meshes) if meshes else None
    out = {a.name: grade_action(arm, a, points, height, kind_of(names.get(a.name, "")), state) for a in acts}
    for name, m in out.items():
        m["clip"] = names.get(name, "")
    return {"height": height, "attacks": out}


def main(argv):
    if argv and argv[0] == "--ref":
        got = {argv[2]: grade_ref(argv[1], argv[2], float(argv[3]) if len(argv) > 3 else 0.0)}
        report = {"attacks": got}
    else:
        report = grade_model(argv[0], argv[2].split("+") if len(argv) > 2 else ())
        got = report["attacks"]
        if len(argv) > 1 and argv[1] != "-":
            pathlib.Path(argv[1]).write_text(json.dumps(report, indent=1))
    for name, m in got.items():
        print("attack_gate:", line(name, m), flush=True)
    return 1 if any(m["fails"] for m in got.values()) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]))
