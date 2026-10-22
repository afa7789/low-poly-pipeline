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
# Portuguese rigs (coxa, perna, asa ...) and fins read as the English parts
SYNONYMS = {"coxa": "thigh", "perna": "shin", "pe": "foot", "asa": "wing", "fin": "wing", "pescoco": "neck",
            "cranio": "head", "calda": "tail", "cauda": "tail", "peito": "chest", "mouth": "jaw"}
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
    return [SYNONYMS.get(t.lower(), t.lower()) for t in parts if t.lower() not in IGNORE]


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
TOPS = ("clavicle", "shoulder", "scapula", "pelvis", "collar", "collarbone", "base")
CONTROLS = ("ik", "pole", "target", "control", "roll", "chain")   # IK helpers, not the skin's bones


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


def _drops(skel, joints, noise):
    """Distinct three-joint sided chains that hang down, most dropping first: legs do, ears,
    eyelids and brows do not (or barely)."""
    chains = {tuple(_leg_chain(skel, joints, e, noise)) for e in _limb_ends(skel, joints, noise)}

    def drop(c):                                   # to the lowest point: spider knees rise first
        return skel.world_pos[c[0]][1] - min(skel.world_pos[d][1] for d in skel.subtree(c[0]))
    legs = sorted((list(c) for c in chains if len(c) == 3 and drop(c) > 0 and
                   not any(_has(skel, j, "wing") for j in c)), key=drop, reverse=True)
    return [c for c in legs if drop(c) > 0.25 * drop(legs[0])]


def _legs(skel, joints, noise):
    """The four chains that drop the most, two a side."""
    legs = _drops(skel, joints, noise)[:4]
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
            neck = _has(skel, _up(skel, joints, j), "neck")   # Head_Jaw + Head_Top under a neck end
            return _up(skel, joints, j) if len(siblings) > 1 and neck else j
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


# ---------------------------------------------------------------- other bodies
GENERIC = {"drake", "bird", "bird_rider", "spider", "crawler", "ray"}


def _control(skel, j):
    return any(t.startswith(c) for t in tokens(skel.names[j]) for c in CONTROLS)


def _has(skel, j, word):
    """A token of j's name starts with word ("Wing1", "Tail3")."""
    return any(t.startswith(word) for t in tokens(skel.names[j]))


def _main_chain(skel, joints, j, n):
    """j and its biggest-subtree real descendants, n joints; a "base" piece on top is skipped."""
    chain = [j]
    while len(chain) <= n and (kids := [c for c in skel.children(chain[-1]) if c in joints]):
        chain.append(max(kids, key=lambda c: len(skel.subtree(c))))
    if len(chain) > 2 and "base" in tokens(skel.names[chain[0]]):
        chain.pop(0)
    return chain[:n]


def _wings(skel, joints, noise):
    """The topmost wing (or fin) chain on each side."""
    out = []
    for j in sorted(joints, key=skel.depth):
        side = role(skel.names[j], noise)[0]
        if side and side not in {role(skel.names[c[0]], noise)[0] for c in out} and \
                _has(skel, j, "wing") and not _control(skel, j) and not _helper(skel, joints, j):
            chain = _main_chain(skel, joints, j, 3)
            out += [chain] if len(chain) >= 2 else []
    return out


def _named_chain(skel, joints, word, n):
    top = next((j for j in sorted(joints, key=skel.depth) if _has(skel, j, word)), None)
    return _main_chain(skel, joints, top, n) if top is not None else []


def _split(ours, path):
    """Spread our chain of bones over their path of joints: {our bone: (joint, joint)}."""
    out, n = {}, len(ours)
    if len(path) < 2:
        return out
    for k, bone in enumerate(ours):
        a, b = round(k * (len(path) - 1) / n), round((k + 1) * (len(path) - 1) / n)
        if a != b:
            out[bone] = (path[a], path[b])
    return out


def _path(skel, joints, top, bottom):
    """Real joints from top down to bottom, or [] when top is not above bottom."""
    path = [bottom]
    while path[-1] not in (top, -1):
        path.append(_up(skel, joints, path[-1]))
    return path[::-1] if path[-1] == top else []


def _our_chain(family, end):
    """Our bones from below the root down to the parent of `end`."""
    table, chain = P.rest(family), []
    b = table[end][0] if end in table else None
    while b not in (None, "root"):
        chain.append(b)
        b = table[b][0]
    return chain[::-1]


def _limb_slots(family, kind):
    """Our limbs of a kind ("leg"/"wing"): [(name, side, forward)], forward measured like theirs."""
    js = P.joints(family)
    head = js["head"][0] if "head" in js else js["root"][0]
    roots = {b[:-6]: js[b][0] for b in js if b.startswith(kind) and b.endswith(".upper")}
    reach = max([r[1] - head[1] for r in roots.values()], default=0.0) or 1.0
    return [(name, "L" if r[0] > 0 else "R", -(r[1] - head[1]) / reach) for name, r in roots.items()]


def _match(slots, chains, place):
    """Pair each of their chains with the nearest free slot of ours on the same side."""
    out, free = {}, list(slots)
    pairs = sorted(((abs(f - place(c)[1]), i, n) for i, c in enumerate(chains)
                    for n, (_, side, f) in enumerate(slots) if side == place(c)[0]))
    used = set()
    for _, i, n in pairs:
        if i in used or free[n] is None:
            continue
        used.add(i)
        out[free[n][0]] = chains[i]
        free[n] = None
    return out


def creature(skel, joints, family):
    """({our bone: (their joint, joint it points to)}, axes) for a drake, bird, spider, crawler
    or ray; ({}, None) when the head or the limbs are missing."""
    joints = {j for j in joints if not _control(skel, j)}       # IK targets and poles stay put
    noise = noise_tokens([skel.names[j] for j in joints])
    root = min(joints, key=skel.depth)
    legs, wings = _drops(skel, joints, noise), _wings(skel, joints, noise)
    head = _head(skel, joints, root)
    if head is None or not (legs or wings):
        return {}, None
    front = _facing(skel, joints, head, [c[0] for c in legs + wings] or [root])
    left = cross([0.0, 1.0, 0.0], front)
    out = _limbs(skel, family, (legs, wings), (head, front, left), noise)
    rear = min(legs, key=lambda c: sum(skel.world_pos[c[0]][k] * front[k] for k in (0, 2)), default=None)
    hips = _sideless_up(skel, joints, rear[0], noise) if rear else root
    out.update(_spine_tail(skel, joints, family, (hips, head), front))
    return out, (left, [0.0, 1.0, 0.0], front)


def _facing(skel, joints, head, tops):
    """Horizontal front: from the limbs' roots to the head, or from the tail tip when the limbs
    sit at the head (a fish whose fins, head and tail all start at one point)."""
    pos = skel.world_pos
    size = max(math.dist(pos[a], pos[b]) for a in joints for b in (head,))
    for back in ([sum(pos[t][k] for t in tops) / len(tops) for k in range(3)],
                 pos[(_named_chain(skel, joints, "tail", 99) or [head])[-1]]):
        flat = [pos[head][0] - back[0], 0.0, pos[head][2] - back[2]]
        if math.hypot(flat[0], flat[2]) > 0.1 * size:
            return unit(flat)
    return [0.0, 0.0, 1.0]


def _limbs(skel, family, chains, frame, noise):
    head, front, left = frame
    pos = skel.world_pos
    tops = [c[0] for group in chains for c in group]
    reach = max([sum((pos[head][k] - pos[t][k]) * front[k] for k in (0, 2)) for t in tops]) or 1.0

    def place(c):
        return role(skel.names[c[0]], noise)[0], sum((pos[c[0]][k] - pos[head][k]) * front[k] for k in (0, 2)) / reach
    out = {}
    for kind, group in zip(("leg", "wing"), chains):
        for name, c in _match(_limb_slots(family, kind), group, place).items():
            out[f"{name}.upper"] = (c[0], c[1])
            if len(c) == 3:
                out[f"{name}.lower"] = (c[1], c[2])
    return out


def _spine_tail(skel, joints, family, ends, front):
    hips, head = ends
    path = []
    while hips >= 0 and not (path := _path(skel, joints, hips, head)):
        hips = _up(skel, joints, hips)                 # thighs under a pelvis beside the spine
    ours = _our_chain(family, "head") or ["body"]
    out = _split(ours, path) if len(path) > 1 else {}
    tip = _ahead_child(skel, joints, head, front)
    if tip is not None and "head" in P.joints(family):
        out["head"] = (head, tip)
    jaw = _named_chain(skel, joints, "jaw", 2) or _named_chain(skel, joints, "inf", 2)   # boca_inf
    if len(jaw) == 2 and "jaw" in P.joints(family):
        out["jaw"] = tuple(jaw)
    tails = sorted(b for b in P.joints(family) if b.startswith("tail."))
    chain = _named_chain(skel, joints, "tail", 99)
    if chain and math.dist(skel.world_pos[chain[0]], skel.world_pos[head]) < 1e-3 + 0.1 * math.dist(
            skel.world_pos[chain[0]], skel.world_pos[chain[-1]]):
        chain = chain[len(chain) // 2:]                # a fish: its "tail" starts at the head
    if tails:
        out.update(_split(tails, chain[:len(tails) + 1]))
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
    if row["rig"] not in FAMILY_BONES and row["rig"] not in GENERIC | {"quadruped"} and unit_id not in MANUAL:
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
    mapping, axes = body_map(skel, joints, family, unit_id)
    if not mapping:
        return f"skeleton not recognised as {family}"
    renames = FAMILY_BONES.get(family, {})
    hips = _body_root(skel, joints, mapping)
    start = next((mapping[b] for b in ("pelvis", "spine.1", "body") if b in mapping), None)
    height = skel.world_pos[start[0]][1] - min(skel.world_pos[j][1] for j in joints) if start else 0.0
    spec = MANUAL.get(unit_id, {})
    clips = list(M.clips(family, picks))
    idle = next(p for slot, p, *_ in clips if slot == "idle")
    neutral = idle[frames_of(idle)[0][0]]                # their rest pose stands for our idle stance
    rest_dirs = our_dirs(family, neutral, axes) if spec.get("relative") else None
    out = []
    for slot, poses, *_ in clips:
        if slot.rstrip("23") not in wanted:
            continue
        keys, times = frames_of(poses)
        rot = {}
        for k in keys:
            dirs = our_dirs(family, poses[k], axes)
            if rest_dirs:
                dirs = _relative(skel, mapping.items(), renames, rest_dirs, dirs)
            for node, q in solve(skel, list(mapping.items()), dirs, renames).items():
                rot.setdefault(node, []).append(q)
        posed = [poses[k] for k in keys]
        moves = {**_hips_track(skel, doc, (hips, height), family, posed, axes),
                 **_reach_tracks(skel, doc, spec, family, [neutral] + posed, axes)}
        out.append((slot, times, rot, moves))
    return out


# rigs whose joint names say nothing (Bone001 ...) or only abbreviations, mapped by eye:
# front = (joint, joint toward the head); bones = {our bone: (their joint, joint it points to)}
MANUAL = {
    "n007": {"front": ("Bone002", "Bone003"),                                   # dragon turtle
             "bones": {"spine.2": ("Bone002", "Bone004"), "head": ("Bone004", "Bone005"),
                       "leg1.upper": ("Bone007(mirrored)", "Bone008(mirrored)"),
                       "leg1.lower": ("Bone008(mirrored)", "Bone009(mirrored)"),
                       "leg2.upper": ("Bone007", "Bone008"), "leg2.lower": ("Bone008", "Bone009"),
                       "leg3.upper": ("Bone011(mirrored)", "Bone012(mirrored)"),
                       "leg3.lower": ("Bone012(mirrored)", "Bone013(mirrored)"),
                       "leg4.upper": ("Bone011", "Bone012"), "leg4.lower": ("Bone012", "Bone013"),
                       "tail.1": ("Bone015", "Bone016"), "tail.2": ("Bone016", "Bone017")}},
    "h016": {"front": ("main.009", "main.002"),                                  # gryphon (rider unskinned)
             "bones": {"spine.2": ("main.001", "main.002"),
                       "leg1.upper": ("fl01.L", "fl02.L"), "leg2.upper": ("fl01.R", "fl02.R"),
                       "leg3.upper": ("bl01.L", "bl02.L"), "leg3.lower": ("bl02.L", "bl03.L"),
                       "leg4.upper": ("bl01.R", "bl02.R"), "leg4.lower": ("bl02.R", "bl03.R"),
                       "wing1.upper": ("w01.L", "w02.L"), "wing1.lower": ("w02.L", "w03.L"),
                       "wing2.upper": ("w01.R", "w02.R"), "wing2.lower": ("w02.R", "w03.R"),
                       "tail.1": ("main.004", "main.005"), "tail.2": ("main.005", "main.006"),
                       "tail.3": ("main.006", "main.007")}},
    # relative: our motion is added to their rest pose (a crouch stays a crouch)
    "n03J": {"front": ("joint49", "joint53"), "relative": True,                  # panda guardian
             "bones": {"spine.1": ("joint49", "joint53"), "spine.2": ("joint53", "joint57"),
                       "head": ("joint57", "joint94"), "tail.1": ("joint54", "joint55"),
                       "leg1.upper": ("joint65", "joint66"), "leg1.lower": ("joint66", "joint68"),
                       "leg2.upper": ("joint80", "joint81"), "leg2.lower": ("joint81", "joint83"),
                       "leg3.upper": ("joint58", "joint59"), "leg3.lower": ("joint59", "joint61"),
                       "leg4.upper": ("joint73", "joint74"), "leg4.lower": ("joint74", "joint76")}},
    "h04I": {"front": ("Bone.013", "Bone.013_end"), "relative": True,            # crouched incubus
             "bones": {"head": ("Bone.013", "Bone.013_end"),
                       "arm.L": ("Bone.007", "Bone.008"), "forearm.L": ("Bone.008", "Bone.009"),
                       "arm.R": ("Bone.001", "Bone.002"), "forearm.R": ("Bone.002", "Bone.003"),
                       "thigh.L": ("Bone.010", "Bone.011"), "shin.L": ("Bone.011", "Bone.012"),
                       "thigh.R": ("Bone.004", "Bone.005"), "shin.R": ("Bone.005", "Bone.006")}},
    # the golem's fists float free of its body: they move (reach) instead of turning; its "L" is
    # on the viewer's left, so our left arm drives its R fist
    "h03N": {"front": ("B_foot_R", "B_toe_R_end"), "relative": True,
             "bones": {"spine": ("B_Body_1", "B_Body_2"),
                       "thigh.L": ("B_leg_R", "B_knee_R"), "shin.L": ("B_knee_R", "B_foot_R"),
                       "thigh.R": ("B_leg_L", "B_knee_L"), "shin.R": ("B_knee_L", "B_foot_L")},
             "reach": {"B_hand_R": "forearm.L", "B_hand_L": "forearm.R"}},
}


def _by_name(skel, joints, name):
    def base(n):
        return re.sub(r"(?i)_armature$", "", re.sub(r"_\d+$", "", n.split(":")[-1]))
    found = [j for j in joints if base(skel.names[j]) == name]
    if not found:
        raise KeyError(f"MANUAL names a joint the model lacks: {name}")
    return found[0]


def _relative(skel, mapping, renames, rest_dirs, dirs):
    """Our bones' turn from our rest, applied to their rest directions."""
    out = {}
    for ours, (a, b) in mapping:
        name = renames.get(ours, ours)
        if name in dirs:
            out[name] = apply(arc(rest_dirs[name], dirs[name]), [p - q for p, q in zip(skel.world_pos[b],
                                                                                            skel.world_pos[a])])
    return out


def _reach_tracks(skel, doc, spec, family, poses, axes):
    """Translation tracks for joints that follow the tip of one of our bones (floating fists),
    measured from poses[0] (our idle stance)."""
    left, up, front = axes
    rest, poses = P.joints(family, poses[0]), poses[1:]
    ys = [p[1] for p in skel.world_pos.values()]
    scale = (max(ys) - min(ys)) / max(t[2] for _, t in rest.values())
    out = {}
    for name, bone in spec.get("reach", {}).items():
        j = _by_name(skel, set(range(len(skel.names))), name)
        inv = _inverse(skel.world_lin[skel.parent[j]])
        base = doc["nodes"][j].get("translation", [0, 0, 0])
        track = []
        for pose in poses:
            d = [a - b for a, b in zip(P.joints(family, pose)[bone][1], rest[bone][1])]
            world = [(d[0] * left[k] + d[2] * up[k] - d[1] * front[k]) * scale for k in range(3)]
            track.append([base[k] + v for k, v in enumerate(apply(inv, world))])
        out[j] = track
    return out


def manual_map(skel, joints, spec):
    """MANUAL[unit] as joint indices plus axes."""
    a, b = (_by_name(skel, joints, n) for n in spec["front"])
    front = unit([skel.world_pos[b][0] - skel.world_pos[a][0], 0.0, skel.world_pos[b][2] - skel.world_pos[a][2]])
    bones = {ours: tuple(_by_name(skel, joints, n) for n in pair) for ours, pair in spec["bones"].items()}
    return bones, (cross([0.0, 1.0, 0.0], front), [0.0, 1.0, 0.0], front)


def body_map(skel, joints, family, unit_id=None):
    """({our bone: (their joint, joint it points to)}, (left, up, front)), or ({}, None)."""
    if unit_id in MANUAL:
        return manual_map(skel, joints, MANUAL[unit_id])
    if family in GENERIC:
        return creature(skel, joints, family)
    if family == "quadruped":
        m = quadruped(skel, joints)
        return (m, front_of_body(skel, m)) if "spine.1" in m else ({}, None)
    m = humanoid(skel, joints)
    return (m, front_of(skel, m)) if m else ({}, None)


def _body_root(skel, joints, mapping):
    """The joint that carries the whole body: the topmost skin joint above the hips (a Max
    biped hangs the thighs under the spine, so the thighs' parent is not it)."""
    start = next((mapping[b] for b in ("pelvis", "spine.1", "body") if b in mapping), None)
    if start is None:
        return None
    j = start[0]
    while _up(skel, joints, j) >= 0:
        j = _up(skel, joints, j)
    return j


def _hips_track(skel, doc, body, family, poses, axes):
    """The body root follows our root (up and forward), scaled by hip height over the ground."""
    hips, height = body
    anchor = next((b for b in ("pelvis", "spine.2", "body") if b in P.joints(family)), None)
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
