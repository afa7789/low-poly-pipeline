#!/usr/bin/env python3
"""Give downloaded rigged models the clips they lack: our animation library (tools/blender/
rig_motions) retargeted onto their own skeleton and appended to the prepared GLB as new
animations (cf_attack, cf_attack2, cf_attack3, cf_spell, cf_death). Mesh, nodes and textures
are not touched, so the .rig/.joints that scripts/fetch_models.mjs made stay valid.

    python3 tools/inject_clips.py [unit_id ...]     # default: every unit whose clip_attack is -1
    python3 tools/inject_clips.py --list            # what would be injected, and what is skipped

The skeleton is recognised by name, whatever the convention (mixamo, 3ds Max Bip01/Bip001,
Rigify metarig, CAT, Cinema 4D, Advanced Skeleton, Quaternius...): the forearm and the shin
are found by keyword (forearm/lowerarm/elbow/arm2, calf/shin/knee/lowerleg/leg2, or mixamo's
"Leg" under an "UpLeg"); the upper arm and thigh are their parents, the hand and foot their
children; hips, spine and neck come from the chain between the legs and the head. Each frame,
every mapped joint is turned (shortest arc, no twist) so the vector to its child joint points
where our bone points. The model's front is measured from its shoulders, not configured.

What was injected is recorded in the glTF extras (start of the appended data, a hash of the
motions), so a rerun replaces it instead of piling up, and skips when nothing changed.
"""
import hashlib
import json
import math
import pathlib
import re
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/blender"))
sys.path.insert(0, str(ROOT / "tools"))

import assign_model_clips as AMC  # noqa: E402
import rig_motions as M  # noqa: E402
import rig_poses as P  # noqa: E402

ASSETS = ROOT / "assets/models"
PREFIX = "cf_"
VERSION = 1
# our biped bone -> the family's bone that drives it (None: that part of the model stays at rest)
_NO_LEGS = {f"{b}.{s}": None for b in ("thigh", "shin", "foot") for s in "LR"}
FAMILY_BONES = {"biped": {}, "harpy": {},
                "wraith": {"pelvis": "base", **_NO_LEGS},
                "naga": {"pelvis": None, **_NO_LEGS},
                "centaur": {"pelvis": None, "spine": "spine.3", **_NO_LEGS}}
IGNORE = {"cat", "rig", "bip", "bip01", "bip001", "def", "org", "jnt", "m", "mixamorig", "metarig", "armature",
          "valvebiped", "golem", "v1"}


# ---------------------------------------------------------------- glb in / out
def read_glb(path):
    data = path.read_bytes()
    chunks, at = [], 12
    while at < len(data):
        length, kind = struct.unpack_from("<I4s", data, at)
        chunks.append((kind, data[at + 8:at + 8 + length]))
        at += 8 + length
    doc = json.loads(chunks[0][1].decode("utf8").rstrip(" \0"))
    return doc, bytearray(chunks[1][1]) if len(chunks) > 1 else bytearray()


def write_glb(path, doc, bin_):
    text = json.dumps(doc, separators=(",", ":")).encode("utf8")
    text += b" " * (-len(text) % 4)
    bin_ = bytes(bin_) + b"\0" * (-len(bin_) % 4)
    body = struct.pack("<I4s", len(text), b"JSON") + text + struct.pack("<I4s", len(bin_), b"BIN\0") + bin_
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)


# ---------------------------------------------------------------- math (row-major 3x3, quaternions x,y,z,w)
def q_to_m(q):
    x, y, z, w = q
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]


def m_to_q(m):
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        return [(m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s, 0.25 * s]
    i = max(range(3), key=lambda k: m[k][k])
    j, k = (i + 1) % 3, (i + 2) % 3
    s = math.sqrt(1.0 + m[i][i] - m[j][j] - m[k][k]) * 2
    q = [0.0, 0.0, 0.0, (m[k][j] - m[j][k]) / s]
    q[i], q[j], q[k] = 0.25 * s, (m[j][i] + m[i][j]) / s, (m[k][i] + m[i][k]) / s
    return q


def mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def tr(a):
    return [[a[j][i] for j in range(3)] for i in range(3)]


def apply(m, v):
    return [sum(m[i][k] * v[k] for k in range(3)) for i in range(3)]


def unit(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return [c / n for c in v]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def arc(u, v):
    """Shortest-arc rotation matrix taking direction u onto direction v."""
    u, v = unit(u), unit(v)
    k, c = cross(u, v), sum(a * b for a, b in zip(u, v))
    if c < -0.999999:                          # opposite: half turn about any perpendicular
        axis = unit(cross(u, [1, 0, 0] if abs(u[0]) < 0.9 else [0, 1, 0]))
        return [[2 * axis[i] * axis[j] - (i == j) for j in range(3)] for i in range(3)]
    f = 1.0 / (1.0 + c)
    vx = [[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]]
    vx2 = mul(vx, vx)
    return [[(i == j) + vx[i][j] + vx2[i][j] * f for j in range(3)] for i in range(3)]


# ---------------------------------------------------------------- skeleton
class Skeleton:
    """Nodes of the glTF in rest pose: parent, local rotation, world rotation and position."""

    def __init__(self, doc):
        nodes = doc["nodes"]
        self.names = [n.get("name", "") for n in nodes]
        self.parent = [-1] * len(nodes)
        for i, n in enumerate(nodes):
            for c in n.get("children", []):
                self.parent[c] = i
        self.local_rot = [q_to_m(n.get("rotation", [0, 0, 0, 1])) for n in nodes]
        self.order = self._order()
        self.world_rot, self.world_pos, self.world_lin = {}, {}, {}
        for i in self.order:
            self._rest(i, nodes[i])

    def _order(self):
        depth = {}

        def d(i):
            if i not in depth:
                depth[i] = 0 if self.parent[i] < 0 else d(self.parent[i]) + 1
            return depth[i]
        return sorted(range(len(self.names)), key=d)

    def _rest(self, i, node):
        s = node.get("scale", [1, 1, 1])
        lin = [[self.local_rot[i][r][c] * s[c] for c in range(3)] for r in range(3)]
        t = node.get("translation", [0, 0, 0])
        p = self.parent[i]
        if p < 0:
            self.world_lin[i], self.world_pos[i], self.world_rot[i] = lin, list(t), self.local_rot[i]
            return
        self.world_lin[i] = mul(self.world_lin[p], lin)
        self.world_pos[i] = [self.world_pos[p][k] + v for k, v in enumerate(apply(self.world_lin[p], t))]
        self.world_rot[i] = mul(self.world_rot[p], self.local_rot[i])

    def children(self, i):
        return [c for c, p in enumerate(self.parent) if p == i]

    def depth(self, i):
        return 0 if self.parent[i] < 0 else self.depth(self.parent[i]) + 1

    def subtree(self, i):
        out = [i]
        for c in self.children(i):
            out += self.subtree(c)
        return out


def tokens(name):
    name = re.sub(r"_\d+$", "", name)
    name = re.sub(r"(?i)(_metarig|_armature|\(mirrored\))", "", name).split(":")[-1].replace("ValveBiped.", "")
    parts = re.findall(r"[A-Z]{2,}(?=[A-Z][a-z]|[0-9]|\b|_)|[A-Z]?[a-z]+[0-9]*|[A-Z][0-9]*|[0-9]+", name)
    return [t.lower() for t in parts if t.lower() not in IGNORE]


def noise_tokens(names):
    """Tokens most joint names share: the armature's own name ("_OgreArm", "Sorcerer_", "B_")."""
    counts = {}
    for name in names:
        for t in set(tokens(name)):
            counts[t] = counts.get(t, 0) + 1
    return {t for t, n in counts.items() if n > 0.6 * len(names)}


def role(name, noise=frozenset()):
    """(side 'L'/'R'/None, key) of a joint name: 'Bip01 L Forearm' -> ('L', 'forearm')."""
    toks = [t for t in tokens(name) if t not in noise]
    side = "L" if {"l", "left"} & set(toks) else "R" if {"r", "right"} & set(toks) else None
    return side, "".join(t for t in toks if t not in ("l", "r", "left", "right"))


FOREARM = {"forearm", "lowerarm", "elbow", "arm2"}
SHIN = {"calf", "shin", "knee", "lowerleg", "leg2"}


def _limb(skel, joints, keys, side, noise):
    return next((j for j in sorted(joints) if role(skel.names[j], noise) in {(side, k) for k in keys}), None)


def _forearm(skel, joints, side, noise):
    """The forearm by name, else the parent of the hand (a rig that names only hands)."""
    fore = _limb(skel, joints, FOREARM, side, noise)
    if fore is None:
        hand = _limb(skel, joints, {"hand", "wrist"}, side, noise)
        fore = _up(skel, joints, hand) if hand is not None else None
        fore = fore if fore is not None and fore >= 0 else None
    return fore


def _chain(skel, low, high):
    """Joints from `low` up to (not including) `high`'s ancestor `low`... the path high -> low."""
    path, j = [], high
    while j >= 0 and j != low:
        path.append(j)
        j = skel.parent[j]
    return list(reversed(path)) if j == low else []


def _helper(skel, joints, j):
    """Not a real joint: outside the skin, or an exporter's scale-compensation node (Maya)."""
    return j not in joints or "scalecompensation" in skel.names[j].lower()


def _up(skel, joints, j):
    """The nearest real joint above j (skips helper nodes), or -1."""
    j = skel.parent[j]
    while j >= 0 and _helper(skel, joints, j):
        j = skel.parent[j]
    return j


def _first_child(skel, joints, j):
    """The first real joint below j, looking through helper nodes."""
    for c in skel.children(j):
        if not _helper(skel, joints, c):
            return c
        deeper = _first_child(skel, joints, c)
        if deeper is not None:
            return deeper
    return None


def humanoid(skel, joints):
    """{our biped bone: (their joint, the joint it points to)}, or {} when not a humanoid."""
    noise = noise_tokens([skel.names[j] for j in joints])
    upleg = {s for s in "LR" if _limb(skel, joints, {"upleg", "thigh", "upperleg"}, s, noise) is not None}
    out = {}
    for s in "LR":
        fore = _forearm(skel, joints, s, noise)
        shin = _limb(skel, joints, SHIN | ({"leg"} if s in upleg else set()), s, noise)
        if fore is None:
            return {}
        hand = _first_child(skel, joints, fore)
        out[f"arm.{s}"] = (_up(skel, joints, fore), fore)
        if hand is not None:
            out[f"forearm.{s}"] = (fore, hand)
        if shin is not None:
            foot = _first_child(skel, joints, shin)
            out[f"thigh.{s}"] = (_up(skel, joints, shin), shin)
            if foot is not None:
                out[f"shin.{s}"] = (shin, foot)
    if out["arm.L"] == out["arm.R"]:         # no arm bones (a golem's hands hang off the body)
        return {}
    out.update(_torso(skel, joints, out, noise))
    return out


def _torso(skel, joints, limbs, noise):
    head = next((j for j in sorted(joints) if role(skel.names[j], noise)[1] == "head"), None)
    neck = next((j for j in sorted(joints) if role(skel.names[j], noise)[1].startswith("neck")), None)
    shoulder = _up(skel, joints, limbs["arm.L"][0])
    top = neck if neck is not None else head if head is not None else shoulder
    hips = _up(skel, joints, limbs["thigh.L"][0]) if "thigh.L" in limbs else None
    out = {}
    if hips is not None:
        path = [j for j in _chain(skel, hips, top) if not _helper(skel, joints, j)]
        if path:
            out["pelvis"] = (hips, path[0])
            out["spine"] = (path[0], top) if path[0] != top else (hips, top)
    if head is not None:
        tip = _first_child(skel, joints, head)
        if tip is not None:
            out["head"] = (head, tip)
    return out


# ---------------------------------------------------------------- quadrupeds
TIPS = ("toe", "ball", "digit", "finger", "end", "nail", "claw")
TOPS = ("clavicle", "shoulder", "scapula", "pelvis", "collar", "collarbone")


def _leg_chain(skel, joints, end, noise):
    """Top -> bottom real joints of the limb ending at `end`, while the names keep a side;
    the shoulder/clavicle/pelvis piece on top is not part of the swing."""
    side = role(skel.names[end], noise)[0]
    chain, j = [], end
    while j >= 0 and role(skel.names[j], noise)[0] == side:
        chain.append(j)
        j = _up(skel, joints, j)
    chain.reverse()
    while len(chain) > 3 and any(t in role(skel.names[chain[0]], noise)[1] for t in TOPS):
        chain.pop(0)
    return chain[:3]


def _limb_ends(skel, joints, noise):
    """The lowest non-tip joint of every sided chain: a foot, ankle or hand."""
    ends = []
    for j in sorted(joints):
        side, key = role(skel.names[j], noise)
        if side is None or _helper(skel, joints, j) or any(t in key for t in TIPS):
            continue
        kid = _first_child(skel, joints, j)
        if kid is None or any(t in role(skel.names[kid], noise)[1] for t in TIPS) or \
                role(skel.names[kid], noise)[0] != side:
            ends.append(j)
    return ends


def _legs(skel, joints, noise):
    """The four distinct three-joint sided chains that drop the most: legs hang down, ears,
    eyelids and brows do not."""
    chains = {tuple(_leg_chain(skel, joints, e, noise)) for e in _limb_ends(skel, joints, noise)}

    def drop(c):
        return skel.world_pos[c[0]][1] - skel.world_pos[c[2]][1]
    legs = sorted((list(c) for c in chains if len(c) == 3 and drop(c) > 0), key=drop, reverse=True)[:4]
    sides = sorted(role(skel.names[c[0]], noise)[0] for c in legs)
    return legs if sides == ["L", "L", "R", "R"] else []


def _sideless_up(skel, joints, j, noise):
    """The nearest joint above j whose name has no side: the spine piece a limb hangs from."""
    j = _up(skel, joints, j)
    while j >= 0 and role(skel.names[j], noise)[0] is not None:
        j = _up(skel, joints, j)
    return j


def _named(skel, joints, word):
    hits = [j for j in sorted(joints) if word in tokens(skel.names[j])]
    return min(hits, key=lambda j: skel.depth(j)) if hits else None


def _head(skel, joints, chest):
    """The joint that turns the whole head: one named head/skull, the parent of a face or jaw
    control, else the last spine/neck joint ahead of the chest."""
    for word, up in (("head", False), ("skull", False), ("face", True), ("jaw", True)):
        j = _named(skel, joints, word)
        if j is not None:
            j = _up(skel, joints, j) if up else j
            siblings = [c for c in skel.children(_up(skel, joints, j)) if "head" in tokens(skel.names[c])]
            return _up(skel, joints, j) if len(siblings) > 1 else j
    path = [chest]
    while (kid := _first_child(skel, joints, path[-1])) is not None and \
            {"spine", "neck"} & set(tokens(skel.names[kid])):
        path.append(kid)
    return path[-1] if len(path) > 1 else None


def _ahead_child(skel, joints, j, front):
    """The real child of j whose subtree reaches farthest along `front` (the snout)."""
    def reach(c):
        far = max((skel.world_pos[d] for d in skel.subtree(c)), key=lambda p: p[0] * front[0] + p[2] * front[2])
        return far[0] * front[0] + far[2] * front[2]
    kids = [c for c in skel.children(j) if c in joints]
    return max(kids, key=reach) if kids else None


def quadruped(skel, joints):
    """{our quadruped bone: (their joint, joint it points to)}, or {} when the rig is not one."""
    noise = noise_tokens([skel.names[j] for j in joints])
    legs = _legs(skel, joints, noise)
    if len(legs) != 4:
        return {}
    tops = sorted({_sideless_up(skel, joints, c[0], noise) for c in legs}, key=skel.depth)
    if len(tops) != 2:
        return {}
    hips, chest = tops
    head = _head(skel, joints, chest)
    if head is None or hips < 0:
        return {}
    front = unit([skel.world_pos[head][0] - skel.world_pos[hips][0], 0.0,
                  skel.world_pos[head][2] - skel.world_pos[hips][2]])
    out = {}
    for c in legs:
        hind = _sideless_up(skel, joints, c[0], noise) == hips
        left = role(skel.names[c[0]], noise)[0] == "L"
        leg = ("leg3" if left else "leg4") if hind else ("leg1" if left else "leg2")
        out[f"{leg}.upper"], out[f"{leg}.lower"] = (c[0], c[1]), (c[1], c[2])
    out["spine.1"], out["spine.2"] = (hips, chest), (chest, head)
    tip = _ahead_child(skel, joints, head, front)
    if tip is not None:
        out["head"] = (head, tip)
    return out


def front_of_body(skel, mapping):
    """(left, up, front) of a four-legged model: front = from the hips toward the head."""
    hips, head = mapping["spine.1"][0], mapping["spine.2"][1]
    front = unit([skel.world_pos[head][0] - skel.world_pos[hips][0], 0.0,
                  skel.world_pos[head][2] - skel.world_pos[hips][2]])
    up = [0.0, 1.0, 0.0]
    return cross(up, front), up, front


# ---------------------------------------------------------------- our motion -> their joints
def front_of(skel, mapping):
    """(left, up, front) unit vectors of the model, measured from its upper arms."""
    left = [a - b for a, b in zip(skel.world_pos[mapping["arm.L"][0]], skel.world_pos[mapping["arm.R"][0]])]
    up = [0.0, 1.0, 0.0]
    left = unit([left[0], 0.0, left[2]])
    return left, up, cross(left, up)


def our_dirs(family, pose, frame_axes):
    """Our bones' directions in the model's world, from our rig (Blender axes)."""
    left, up, front = frame_axes
    out = {}
    for bone, (h, t) in P.joints(family, pose).items():
        bx, by, bz = (t[i] - h[i] for i in range(3))
        out[bone] = [bx * left[k] + bz * up[k] - by * front[k] for k in range(3)]   # canonical: x left, z up, -y front
    return out


def solve(skel, mapping, dirs, renames):
    """Local rotations (quaternions) of the mapped joints for one frame."""
    world, local = {}, {}
    targets = {their: (to, dirs[renames.get(ours, ours)]) for ours, (their, to) in mapping
               if renames.get(ours, ours) in dirs}
    for i in skel.order:
        p = skel.parent[i]
        parent = world.get(p, skel.world_rot[p]) if p >= 0 else None
        current = mul(parent, skel.local_rot[i]) if parent is not None else skel.world_rot[i]
        if i in targets:
            to, d = targets[i]
            rest_vec = [a - b for a, b in zip(skel.world_pos[to], skel.world_pos[i])]
            along = apply(current, apply(tr(skel.world_rot[i]), rest_vec))
            current = mul(arc(along, d), current)
            local[i] = m_to_q(mul(tr(parent), current) if parent is not None else current)
        world[i] = current
    return local


# ---------------------------------------------------------------- write animations
def _append(doc, bin_, values, kind, count, minmax=False):
    view = {"buffer": 0, "byteOffset": len(bin_), "byteLength": 4 * len(values)}
    bin_ += struct.pack(f"<{len(values)}f", *values)
    bin_ += b"\0" * (-len(bin_) % 4)
    doc.setdefault("bufferViews", []).append(view)
    acc = {"bufferView": len(doc["bufferViews"]) - 1, "componentType": 5126, "count": count, "type": kind}
    if minmax:
        acc["min"], acc["max"] = [min(values)], [max(values)]
    doc.setdefault("accessors", []).append(acc)
    return len(doc["accessors"]) - 1


def add_animation(doc, bin_, name, times, rotations, translations):
    """rotations: {node: [quat per time]}; translations: {node: [vec3 per time]}."""
    t_acc = _append(doc, bin_, times, "SCALAR", len(times), minmax=True)
    samplers, channels = [], []
    for path, tracks, kind in (("rotation", rotations, "VEC4"), ("translation", translations, "VEC3")):
        for node, values in tracks.items():
            acc = _append(doc, bin_, [c for v in values for c in v], kind, len(values))
            samplers.append({"input": t_acc, "output": acc, "interpolation": "LINEAR"})
            channels.append({"sampler": len(samplers) - 1, "target": {"node": node, "path": path}})
    doc.setdefault("animations", []).append({"name": PREFIX + name, "samplers": samplers, "channels": channels})


def strip_previous(doc, bin_):
    """Drop a previous injection (its animations, accessors, views and bytes)."""
    mark = doc.get("extras", {}).get("cf_inject")
    if not mark:
        return bin_
    doc["animations"] = [a for a in doc.get("animations", []) if not a.get("name", "").startswith(PREFIX)]
    doc["accessors"] = doc["accessors"][:mark["accessors"]]
    doc["bufferViews"] = doc["bufferViews"][:mark["views"]]
    del doc["extras"]["cf_inject"]
    return bytearray(bin_[:mark["bin"]])


# ---------------------------------------------------------------- per unit
# rigs that map but must not be animated by us (unit id -> why); empty today
SKIP = {}


def plan(unit_id):
    """(family, picks, row) for a unit, or a reason string to skip it."""
    if unit_id in SKIP:
        return SKIP[unit_id]
    rows = M.unit_rows()
    row = rows.get(unit_id)
    if row is None:
        return "no registry row"
    if row["rig"] not in FAMILY_BONES and row["rig"] != "quadruped":
        return f"rig {row['rig']}: no map yet"
    return row["rig"], {slot: row[slot] for slot in M.SLOTS}, row


def frames_of(clip):
    keys = sorted(clip)
    return keys, [(k - 1) / 24.0 for k in keys]


def build(unit_id, glb, wanted):
    """The animations to append: [(name, times, rotations, translations)]; or a skip reason."""
    got = plan(unit_id)
    if isinstance(got, str):
        return got
    family, picks, _ = got
    doc, _ = read_glb(glb)
    if not doc.get("skins"):
        return "static model (no skin)"
    skel = Skeleton(doc)
    joints = set(doc["skins"][0]["joints"])
    four = family == "quadruped"
    mapping = quadruped(skel, joints) if four else humanoid(skel, joints)
    if not mapping or (four and "spine.1" not in mapping):
        return f"skeleton not recognised as {family}"
    axes = front_of_body(skel, mapping) if four else front_of(skel, mapping)
    renames = {} if four else FAMILY_BONES[family]
    hips = _body_root(skel, joints, mapping)
    start = mapping.get("pelvis", mapping.get("spine.1"))
    height = skel.world_pos[start[0]][1] - min(skel.world_pos[j][1] for j in joints) if start else 0.0
    out = []
    for slot, poses, *_ in M.clips(family, picks):
        if slot.rstrip("23") not in wanted:
            continue
        keys, times = frames_of(poses)
        rot = {}
        for k in keys:
            for node, q in solve(skel, list(mapping.items()), our_dirs(family, poses[k], axes), renames).items():
                rot.setdefault(node, []).append(q)
        out.append((slot, times, rot, _hips_track(skel, doc, (hips, height), family, [poses[k] for k in keys], axes)))
    return out


def _body_root(skel, joints, mapping):
    """The joint that carries the whole body: the topmost skin joint above the hips (a Max
    biped hangs the thighs under the spine, so the thighs' parent is not it)."""
    start = mapping.get("pelvis", mapping.get("spine.1"))
    if start is None:
        return None
    j = start[0]
    while _up(skel, joints, j) >= 0:
        j = _up(skel, joints, j)
    return j


def _hips_track(skel, doc, body, family, poses, axes):
    """The body root follows our root (up and forward), scaled by hip height over the ground."""
    hips, height = body
    anchor = next((b for b in ("pelvis", "spine.2") if b in P.joints(family)), None)
    if hips is None or anchor is None:
        return {}
    left, up, front = axes
    ours = P.joints(family)[anchor][0][2]
    scale = height / ours if ours else 1.0
    p = skel.parent[hips]
    inv = _inverse(skel.world_lin[p]) if p >= 0 else [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    rest = doc["nodes"][hips].get("translation", [0, 0, 0])
    track = []
    for pose in poses:
        _, _, _, lift, rise = P.pad(pose.get("root", (0, 0, 0, 0, 0)))
        world = [(rise * up[k] + lift * front[k]) * scale for k in range(3)]
        track.append([rest[k] + v for k, v in enumerate(apply(inv, world))])
    return {hips: track}


def _inverse(m):
    a = m
    cof = [[a[(i + 1) % 3][(j + 1) % 3] * a[(i + 2) % 3][(j + 2) % 3]
            - a[(i + 1) % 3][(j + 2) % 3] * a[(i + 2) % 3][(j + 1) % 3] for j in range(3)] for i in range(3)]
    det = sum(a[0][j] * cof[0][j] for j in range(3)) or 1.0
    return [[cof[j][i] / det for j in range(3)] for i in range(3)]


def wanted_slots(row, names=()):
    """What the model lacks: attack (and its combo) always, spell and death when the model has
    none of its own (a clip that points at one of our cf_ clips is ours, so it counts as none)."""
    def own(column):
        i = int(row.get(column, "-1"))
        return 0 <= i < len(names) and not names[i].startswith(PREFIX) if names else i >= 0
    slots = {"attack"}
    if not own("clip_spell"):
        slots.add("spell")
    if not own("clip_death"):
        slots.add("death")
    return slots


def inject(unit_id, model_row):
    glb = ASSETS / f"{unit_id}.glb"
    if not glb.exists():
        return "no GLB"
    names = [a.get("name", "") for a in read_glb(glb)[0].get("animations", [])]
    anims = build(unit_id, glb, wanted_slots(model_row, names))
    if isinstance(anims, str):
        return anims
    rounded = [(a[0], a[1], {n: [[round(c, 5) for c in q] for q in v] for n, v in a[2].items()},
                {n: [[round(c, 5) for c in t] for t in v] for n, v in a[3].items()}) for a in anims]
    digest = hashlib.sha1(json.dumps([VERSION, rounded], sort_keys=True).encode()).hexdigest()
    doc, bin_ = read_glb(glb)
    if doc.get("extras", {}).get("cf_inject", {}).get("hash") == digest:
        return "up to date"
    bin_ = strip_previous(doc, bin_)
    mark = {"bin": len(bin_), "accessors": len(doc.get("accessors", [])), "views": len(doc.get("bufferViews", [])),
            "hash": digest}
    for slot, times, rot, trans in anims:
        add_animation(doc, bin_, slot, times, rot, trans)
    doc["buffers"][0]["byteLength"] = len(bin_) + (-len(bin_) % 4)
    doc.setdefault("extras", {})["cf_inject"] = mark
    write_glb(glb, doc, bin_)
    return "injected " + ",".join(a[0] for a in anims)


def _injected(unit_id):
    glb = ASSETS / f"{unit_id}.glb"
    return glb.exists() and "cf_inject" in read_glb(glb)[0].get("extras", {})


def targets(argv):
    """The units named, else every unit with no attack clip plus every one injected before
    (once injected, its clip_attack points at cf_attack; a rerun must still refresh it)."""
    head, rows = AMC.rows(AMC.MODELS)
    by_id = {r["unit_id"]: r for r in rows}
    ids = [a for a in argv if not a.startswith("--")] or [
        r["unit_id"] for r in rows if r["clip_attack"] == "-1" or _injected(r["unit_id"])]
    return [(u, by_id[u]) for u in ids if u in by_id]


def main():
    if not ASSETS.exists():
        print("inject_clips: no assets/models (run make assets); skipped")
        return
    listing = "--list" in sys.argv[1:]
    for unit_id, row in targets(sys.argv[1:]):
        if listing:
            got = plan(unit_id)
            print(unit_id, got if isinstance(got, str) else f"{got[0]}: {sorted(wanted_slots(row))}")
            continue
        print(unit_id, inject(unit_id, row))


if __name__ == "__main__":
    main()
