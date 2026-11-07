#!/usr/bin/env python3
"""Give downloaded models that have no skeleton (a statue-like mesh, a machine made of parts) one of
our rig families, so tools/inject_clips.py animates them like any rigged model; and give the loose
parts of rigged machines (a tank's gun) joints of their own.

    python3 tools/rig_static.py [unit_id ...]     # default: every unit in RIGS
    python3 tools/rig_static.py --list            # what each spec rigs
    python3 tools/rig_static.py --force [unit_id ...]   # rig again even when the spec is unchanged

The skeleton is the family's rest skeleton (tools/blender/rig_families) laid onto the model's
bounding box axis by axis; the bones a spec names are placed by hand in box coordinates
(x across, -1 right .. 1 left; y up, 0 floor .. 1 top; z along, -1 back .. 1 front). Every joint
sits at its bone's head with an end node at the tail, so inject_clips aims it the way it aims a
downloaded rig's. How the mesh follows the bones:
  smooth  each vertex follows its two nearest bones (weight 1/d^4 by distance to the bone), never a
          bone of the other side: organic bodies
  rigid   each connected piece follows one bone: the first spec region holding its centre, else the
          nearest bone: machines
  parts   whole mesh nodes, by name, follow one bone (a staff in the hand, a tank's gun)
A model that already has a skin keeps it: `attach` names the joints of it that play our bones,
the root goes above its top joint, and only the meshes without weights are weighted.

What was added is recorded in extras.cf_rig, with the bone -> (joint, end) map inject_clips reads,
so a rerun with the same spec skips and a changed spec replaces it (clips injected on top go too).
The <id>.rig and <id>.joints next to the GLB are rewritten like scripts/fetch_models.mjs does.
"""
import hashlib
import json
import pathlib
import re
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/blender"))
sys.path.insert(0, str(ROOT / "tools"))

import inject_clips as IC  # noqa: E402
import rig_families as RF  # noqa: E402
import rig_motions as M  # noqa: E402

ASSETS = ROOT / "assets/models"
VERSION = 1
PREFIX = "cf:"
AXES = {"+x": (1.0, 0.0, 0.0), "-x": (-1.0, 0.0, 0.0), "+z": (0.0, 0.0, 1.0), "-z": (0.0, 0.0, -1.0)}

# ---------------------------------------------------------------- per unit
# family: from data/unit_anim.tsv (or of the unit named by "row": a model that moves like that unit);
# front: the model's front, a glTF axis or (x, z); bones: {bone: (head, tail)} in box coordinates;
# omit: family bones the model has no part for; weights: smooth | rigid; regions: [(bone, (x0, x1, y0,
# y1, z0, z1))] for rigid pieces; parts: {mesh node name regex: bone}; attach: {bone: joint name} of a
# skin the model already has; relative (default true): motion from the clip's first pose
EVERYWHERE = (-9, 9, -9, 9, -9, 9)


def _chains(chains, pairs=None):
    """{bone: (head, tail)} from {"bone bone ...": [point, point, ...]} (each bone runs from one point to
    the next); the left bones (.L, or a `pairs` key: {"leg1": "leg2"}) mirrored to the right ones."""
    out = {}
    for names, points in chains.items():
        for k, bone in enumerate(names.split()):
            out[bone] = (points[k], points[k + 1])
    for bone, (h, t) in list(out.items()):
        stem, _, part = bone.partition(".")
        twin = bone[:-2] + ".R" if bone.endswith(".L") else f"{pairs[stem]}.{part}" if stem in (pairs or {}) else None
        if twin and twin not in out:
            out[twin] = ((-h[0], h[1], h[2]), (-t[0], t[1], t[2]))
    return out


_TANK_ONLY = ("track.L", "track.R", "arm.L", "arm.R")
_HULL = ((0, 0.35, -0.8), (0, 0.40, 0.8))
_CRAFT_ONLY = ("gondola", "prop", "rudder")
_WHEELS = ("wheel1", "wheel2", "wheel3", "wheel4")
_NO_WINGS = ("wing1.upper", "wing1.lower", "wing2.upper", "wing2.lower")
_ARMS = ("arm.L", "forearm.L", "arm.R", "forearm.R")
_WING_TIPS = ("wing1.lower", "wing2.lower")          # a huge membrane folding at the wrist wraps the body


def _tank(pivot):
    """A rigged tank (its tracks animate) whose gun and turret are loose meshes: the gun turns on
    `pivot` as our head, the turret rides the hull (their Root joint)."""
    return {"front": "-x", "weights": "rigid", "omit": _TANK_ONLY, "attach": {"hull": "Root"},
            "parts": {"^Tank_Gun$": "head", "^Tank_Turret$": "hull"},
            "bones": {"hull": _HULL, "head": (pivot, (pivot[0], pivot[1], 1.0))}}


_VAMPIRE = _chains({"pelvis spine head": [(0, 0.25, 0), (0, 0.33, 0), (0, 0.45, 0.2), (0, 0.5, 0.6)],
                    "arm.L forearm.L": [(0.1, 0.45, 0.1), (0.25, 0.38, 0.3), (0.3, 0.36, 0.5)],
                    "thigh.L shin.L foot.L": [(0.05, 0.25, 0), (0.07, 0.13, 0.1), (0.06, 0.03, 0), (0.06, 0, 0.2)],
                    "wing1.upper wing1.lower": [(0.12, 0.47, -0.3), (0.32, 0.9, 0.2), (0.95, 0.67, 0.5)]},
                   {"wing1": "wing2"})
_FUNNEL = {"base": ((0, 0, 0), (0, 0.45, 0)), "spine": ((0, 0.45, 0), (0, 1.0, 0))}

RIGS = {
    # tracked: the gun (mantlet and barrel) is the head, so the recoil kicks it up; the rest is hull
    "h099": {"front": "+z", "weights": "rigid", "omit": _TANK_ONLY,
             "bones": {"hull": _HULL, "head": ((0, 0.76, 0.25), (0, 0.76, 1.0))},
             "regions": [("head", (-0.25, 0.25, 0.65, 0.9, 0.2, 1.05)), ("hull", EVERYWHERE)]},
    "n01E": {"front": (0.81, 0.58), "weights": "rigid", "omit": _TANK_ONLY,            # built turned 36 degrees
             "bones": {"hull": ((0.05, 0.30, -0.8), (0.05, 0.35, 0.8)), "head": ((0.08, 0.68, 0.1), (0.08, 0.7, 0.66))},
             "regions": [("head", (-0.1, 0.3, 0.6, 0.76, 0.0, 0.7)), ("hull", EVERYWHERE)]},
    "h06S": _tank((0, 0.86, -0.3)), "h06T": _tank((0, 0.52, -0.05)), "h06U": _tank((0, 0.78, 0.25)),
    "h098": _tank((0, 0.85, 0.16)),
    # aircraft: the whole craft is the hull (it dives, banks, rolls over)
    "h06R": {"front": "+z", "weights": "rigid", "omit": _CRAFT_ONLY, "bones": {"hull": _HULL}},
    "h07S": {"front": "+x", "weights": "rigid", "omit": _CRAFT_ONLY, "attach": {"hull": "_rootJoint"},
             "parts": {".": "hull"}, "bones": {"hull": _HULL}},
    # vehicles: the weapon (bow, crossbow, throwing arm) is the head and turns on its pivot
    "e005": {"front": "+z", "weights": "rigid", "omit": _WHEELS,                           # ballista: the bow
             "bones": {"head": ((0, 0.7, 0.45), (0, 0.7, 1.0))},
             "regions": [("head", (-1.01, 1.01, 0.4, 1.01, 0.25, 0.7)), ("hull", EVERYWHERE)]},
    "e002": {"front": "+z", "weights": "rigid", "omit": _WHEELS,                           # crossbow on a post
             "bones": {"head": ((0, 0.36, -0.14), (0, 0.45, 1.0))},
             "parts": {"group(681242894|1597376112)$": "hull", ".": "head"}},
    "o001": {"front": "+z", "weights": "rigid", "omit": _WHEELS,                           # trebuchet beam
             "bones": {"head": ((0, 0.92, 0.4), (0, 0.92, -0.93))},
             "regions": [("head", (-0.1, 0.1, 0.84, 1.0, -0.95, 0.85)), ("head", (-0.25, 0.25, 0.4, 1.0, 0.58, 1.0)),
                         ("hull", EVERYWHERE)]},
    "n03V": {"front": "+z", "weights": "rigid", "omit": _WHEELS, "row": "o001",           # trebuchet beam
             "bones": {"head": ((0, 0.67, 0.26), (0, 0.14, -0.91))},
             "regions": [("head", (-0.1, 0.1, 0.3, 0.9, -0.5, 0.5)), ("head", (-0.13, 0.13, 0.6, 0.96, 0.45, 1.01)),
                         ("hull", EVERYWHERE)]},
    "o00H": {"front": "-z", "weights": "rigid", "omit": _WHEELS,                           # catapult arm
             "bones": {"head": ((0, 0.28, 0.1), (0, 1.0, -1.0))},
             "regions": [("head", (-0.25, 0.25, 0.25, 1.05, -1.05, 0.15)), ("hull", EVERYWHERE)]},
    # crew: the mortar's barrel kicks on its trunnion, the carriage is the cradle
    "hmtm": {"front": "-z", "weights": "rigid", "omit": ("thigh.L", "shin.L", "thigh.R", "shin.R"),
             "bones": {"barrel": ((0, 0.78, -0.27), (0, 0.8, 1.0))}, "parts": {"^barrel": "barrel", ".": "cradle"}},
    # bipeds: joints laid on the body by eye (box coordinates read off a gridded front and side view)
    "n02T": {"front": "+z", "parts": {"^pSphere": "head"},                               # kobold
             "bones": _chains({"pelvis spine head": [(0, 0.44, -0.1), (0, 0.55, -0.1), (0, 0.77, 0), (0, 1.0, 0.2)],
                               "arm.L forearm.L": [(0.4, 0.73, -0.05), (0.65, 0.54, -0.15), (0.85, 0.37, -0.15)],
                               "thigh.L shin.L foot.L": [(0.25, 0.44, -0.1), (0.36, 0.24, 0), (0.48, 0.07, -0.1),
                                                         (0.5, 0.02, 0.45)]})},
    "n01F": {"front": "+z",                                                               # mimic chest on legs
             "bones": _chains({"pelvis spine head": [(0, 0.45, -0.3), (0, 0.6, -0.2), (0, 0.8, 0), (0, 1.0, 0.1)],
                               "arm.L forearm.L": [(0.45, 0.5, 0.1), (0.85, 0.45, 0.3), (0.6, 0.4, 0.8)],
                               "arm.R forearm.R": [(-0.45, 0.5, 0), (-0.8, 0.4, 0.1), (-0.55, 0.3, 0.3)],
                               "thigh.L shin.L foot.L": [(0.25, 0.47, -0.4), (0.28, 0.25, -0.35), (0.3, 0.04, -0.45),
                                                         (0.3, 0.01, -0.1)]})},
    "h05C": {"front": "+z",                                                               # cowboy, A pose
             "bones": _chains({"pelvis spine head": [(0, 0.5, -0.3), (0, 0.6, -0.3), (0, 0.8, -0.3), (0, 1.0, -0.3)],
                               "arm.L forearm.L": [(0.4, 0.78, -0.3), (0.71, 0.67, 0), (0.9, 0.57, 0.6)],
                               "thigh.L shin.L foot.L": [(0.17, 0.5, -0.3), (0.2, 0.27, -0.3), (0.25, 0.04, -0.4),
                                                         (0.25, 0.01, 0.8)]})},
    "n020": {"front": "-z",                                                               # assassin, crouched
             "bones": _chains({"pelvis spine head": [(0, 0.38, 0.15), (0, 0.5, 0.2), (0, 0.72, 0.45), (0, 0.95, 0.7)],
                               "arm.R forearm.R": [(-0.4, 0.66, 0.35), (-0.6, 0.55, 0.3), (-0.72, 0.47, 0.4)],
                               "arm.L forearm.L": [(0.44, 0.67, 0.35), (0.52, 0.56, 0.35), (0.56, 0.42, 0.4)],
                               "thigh.L shin.L foot.L": [(0.2, 0.38, 0.15), (0.3, 0.25, 0.5), (0.3, 0.05, 0.6),
                                                         (0.3, 0.01, 0.9)],
                               "thigh.R shin.R foot.R": [(-0.2, 0.38, 0.1), (-0.35, 0.28, -0.3), (-0.36, 0.05, -0.8),
                                                         (-0.36, 0.01, -0.6)]})},
    "o003": {"front": "+z", "parts": {"posoh": "forearm.R", "Teeth|eyes|feafers": "head"},   # orc shaman, staff
             "bones": _chains({"pelvis spine head": [(0, 0.4, -0.2), (0, 0.52, -0.2), (0, 0.66, -0.05), (0, 0.8, 0.15)],
                               "arm.R forearm.R": [(-0.42, 0.59, -0.15), (-0.74, 0.47, -0.05), (-0.74, 0.43, 0.15)],
                               "arm.L forearm.L": [(0.47, 0.59, -0.15), (0.79, 0.39, -0.15), (0.82, 0.26, 0)],
                               "thigh.L shin.L foot.L": [(0.2, 0.4, -0.25), (0.33, 0.21, -0.2), (0.37, 0.05, -0.35),
                                                         (0.37, 0.01, 0)]})},
    # wraiths: an upper body on a tail or a stem
    "u00F": {"front": "+z",                                                               # fire elemental
             "bones": _chains({"base spine": [(0, 0.05, 0), (0, 0.5, 0), (0, 0.9, 0.1)],
                               "head": [(0, 0.8, 0.3), (0, 0.75, 0.8)],
                               "arm.L forearm.L": [(0.36, 0.78, 0), (0.76, 0.57, 0), (0.76, 0.33, 0.6)]})},
    "h02Y": {"front": "+x", "parts": {"^Eye": "head"},                                    # water monster, T pose
             "bones": _chains({"base spine head": [(0, 0.02, 0), (0, 0.5, 0), (0, 0.75, 0.1), (0, 0.95, 0.6)],
                               "arm.L forearm.L": [(0.25, 0.71, 0), (0.57, 0.7, 0), (0.95, 0.66, 0)]})},
    # the twins: each figure swings from its shoulders as one arm
    "h03R": {"front": "+z", "weights": "rigid", "omit": ("head", "forearm.L", "forearm.R"),
             "parts": {"^Skull001": "arm.L", "^Skull_": "arm.R"},
             "bones": _chains({"arm.L": [(0.5, 0.9, 0), (0.5, 0.2, 0)]})},
    # tornados: a funnel bending on its stem (wraith) or tilting whole (shard)
    "h02Z": {"front": "+z", "omit": ("head", *_ARMS), "bones": _FUNNEL},
    "h03P": {"front": "+z", "omit": ("head", *_ARMS), "bones": _FUNNEL},
    **{u: {"front": "+z", "weights": "rigid", "omit": (*_NO_WINGS, "plate.1", "plate.2", "plate.3", "tail.1"),
           "bones": {"body": ((0, 0, 0), (0, 1.0, 0))}} for u in ("o00C", "o00D", "o00E")},
    # harpies: the harpy's arms are its wings; the vampire has wings of its own
    "n02W": {"front": "+z", "omit": _NO_WINGS,
             "bones": _chains({"pelvis spine head": [(0, 0.43, 0.3), (0, 0.55, 0.3), (0, 0.76, 0.3), (0, 0.99, 0.3)],
                               "arm.L forearm.L": [(0.12, 0.74, 0.3), (0.5, 0.73, 0.3), (0.98, 0.66, 0.3)],
                               "thigh.L shin.L foot.L": [(0.1, 0.43, 0.3), (0.1, 0.21, 0.3), (0.14, 0.04, 0.3),
                                                         (0.14, 0.01, 0.9)]})},
    "h01U": {"front": "+z", "parts": {"Glassy": "head"}, "bones": _VAMPIRE, "omit": _WING_TIPS},
    "h01V": {"front": "+z", "parts": {"Glassy": "head"}, "bones": _VAMPIRE, "omit": _WING_TIPS, "row": "h01U"},
    # quadruped: the boar
    "n02U": {"front": "+z",
             "bones": _chains({"spine.1 spine.2": [(0, 0.75, -0.6), (0, 0.8, 0), (0, 0.75, 0.5)],
                               "head": [(0, 0.6, 0.55), (0, 0.35, 0.98)],
                               "tail.1 tail.2": [(0, 0.85, -0.92), (0, 0.6, -1.0), (0, 0.5, -1.0)],
                               "leg1.upper leg1.lower": [(0.5, 0.5, 0.35), (0.6, 0.2, 0.33), (0.6, 0, 0.35)],
                               "leg3.upper leg3.lower": [(0.55, 0.55, -0.6), (0.6, 0.2, -0.65), (0.6, 0, -0.6)]},
                              {"leg1": "leg2", "leg3": "leg4"})},
}


# ---------------------------------------------------------------- 4x4 maths (row-major)
def trs(node):
    """Local matrix of a glTF node."""
    if "matrix" in node:
        m = node["matrix"]
        return [[m[c * 4 + r] for c in range(4)] for r in range(4)]
    rot = IC.q_to_m(node.get("rotation", [0, 0, 0, 1]))
    s, t = node.get("scale", [1, 1, 1]), node.get("translation", [0, 0, 0])
    return [[rot[r][c] * s[c] for c in range(3)] + [t[r]] for r in range(3)] + [[0, 0, 0, 1]]


def mmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def minv(m):
    """Inverse of an affine 4x4."""
    inv = IC._inverse([row[:3] for row in m[:3]])
    t = [-sum(inv[i][k] * m[k][3] for k in range(3)) for i in range(3)]
    return [inv[0] + [t[0]], inv[1] + [t[1]], inv[2] + [t[2]], [0, 0, 0, 1]]


def mpoint(m, p):
    return [sum(m[i][k] * p[k] for k in range(3)) + m[i][3] for i in range(3)]


def parents(doc):
    out = [-1] * len(doc["nodes"])
    for i, node in enumerate(doc["nodes"]):
        for c in node.get("children", []):
            out[c] = i
    return out


def worlds(doc):
    """World matrix of every node in rest pose."""
    par, out = parents(doc), {}

    def world(i):
        if i not in out:
            local = trs(doc["nodes"][i])
            out[i] = mmul(world(par[i]), local) if par[i] >= 0 else local
        return out[i]
    return [world(i) for i in range(len(doc["nodes"]))]


# ---------------------------------------------------------------- accessors
FORMATS = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def read(doc, bin_, index):
    """An accessor's elements as tuples (no sparse accessors: the models have none)."""
    acc = doc["accessors"][index]
    view = doc["bufferViews"][acc["bufferView"]]
    fmt, n = FORMATS[acc["componentType"]], WIDTH[acc["type"]]
    size = struct.calcsize("<" + fmt * n)
    stride = view.get("byteStride", size)
    base = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    return [struct.unpack_from("<" + fmt * n, bin_, base + i * stride) for i in range(acc["count"])]


def append(doc, bin_, values, fmt, kind, count):
    """A new accessor over `values` (flat) packed with struct format `fmt`; its index."""
    view = {"buffer": 0, "byteOffset": len(bin_), "byteLength": struct.calcsize("<" + fmt * len(values))}
    bin_ += struct.pack("<" + fmt * len(values), *values)
    bin_ += b"\0" * (-len(bin_) % 4)
    doc.setdefault("bufferViews", []).append(view)
    component = next(k for k, v in FORMATS.items() if v == fmt)
    doc.setdefault("accessors", []).append({"bufferView": len(doc["bufferViews"]) - 1, "componentType": component,
                                            "count": count, "type": kind})
    return len(doc["accessors"]) - 1


def primitives(doc):
    """[(node, mesh index, primitive index)] of every mesh node."""
    return [(i, n["mesh"], k) for i, n in enumerate(doc["nodes"]) if "mesh" in n
            for k in range(len(doc["meshes"][n["mesh"]]["primitives"]))]


def rest_points(doc, bin_, world, node, prim):
    """World positions of a primitive's vertices in rest pose (skinned ones through their skin)."""
    attrs = prim["attributes"]
    local = read(doc, bin_, attrs["POSITION"])
    skin = doc["nodes"][node].get("skin")
    if skin is None or "JOINTS_0" not in attrs:
        return [mpoint(world[node], p) for p in local]
    joints = doc["skins"][skin]["joints"]
    ibm_at = doc["skins"][skin].get("inverseBindMatrices")
    ibm = [[[m[c * 4 + r] for c in range(4)] for r in range(4)] for m in read(doc, bin_, ibm_at)] if \
        ibm_at is not None else [minv(world[j]) for j in joints]
    bind = [mmul(world[j], ibm[k]) for k, j in enumerate(joints)]
    out = []
    for p, js, ws in zip(local, read(doc, bin_, attrs["JOINTS_0"]), read(doc, bin_, attrs["WEIGHTS_0"])):
        total = sum(ws) or 1.0
        out.append([sum(w * mpoint(bind[j], p)[k] for j, w in zip(js, ws) if w > 0) / total for k in range(3)])
    return out


# ---------------------------------------------------------------- the model's box
class Box:
    """The model's frame: left/up/front axes and its extent along them (box coordinates)."""

    def __init__(self, points, front):
        self.front = list(AXES[front]) if isinstance(front, str) else IC.unit([front[0], 0.0, front[1]])
        self.up = [0.0, 1.0, 0.0]
        self.left = IC.cross(self.up, self.front)
        span = []
        for axis in (self.left, self.up, self.front):
            d = [sum(a * b for a, b in zip(p, axis)) for p in points]
            span.append((min(d), max(d)))
        (l0, l1), (self.floor, top), (f0, f1) = span
        self.height = (top - self.floor) or 1.0
        self.mid = ((l0 + l1) / 2, (f0 + f1) / 2)
        self.half = ((l1 - l0) / 2 or 1.0, (f1 - f0) / 2 or 1.0)

    def point(self, n):
        """World point of box coordinates n = (across, up, along)."""
        across = self.mid[0] + n[0] * self.half[0]
        along = self.mid[1] + n[2] * self.half[1]
        rise = self.floor + n[1] * self.height
        return [across * self.left[k] + rise * self.up[k] + along * self.front[k] for k in range(3)]

    def coords(self, p):
        across = sum(a * b for a, b in zip(p, self.left))
        along = sum(a * b for a, b in zip(p, self.front))
        return ((across - self.mid[0]) / self.half[0], (p[1] - self.floor) / self.height,
                (along - self.mid[1]) / self.half[1])


# ---------------------------------------------------------------- our bones on the model
def family_of(unit_id, spec):
    """The rig family of the unit's registry row, or of the unit the spec says it moves like ("row")."""
    row = M.unit_rows().get(spec.get("row", unit_id))
    if row is None:
        raise KeyError(f"{unit_id}: no row in data/unit_anim.tsv")
    return row["rig"]


def layout(family, spec):
    """{bone: (parent, head, tail)} in box coordinates: the family table scaled to the box, the
    spec's bones on top; omitted bones are left out (their children hang from the next one up)."""
    table = RF.FAMILIES[family]
    pts = [p for _, _, h, t in table for p in (h, t)]
    span = [max(abs(p[k]) for p in pts) or 1.0 for k in (0, 2)]
    top = max(p[1] for p in pts) or 1.0
    omit = set(spec.get("omit", ()))
    up = {name: parent for name, parent, *_ in table}
    out = {}
    for name, parent, head, tail in table:
        if name in omit:
            continue
        while parent in omit:
            parent = up[parent]
        h, t = ((p[0] / span[0], p[1] / top, p[2] / span[1]) for p in (head, tail))
        h, t = spec.get("bones", {}).get(name, (h, t))
        out[name] = (parent, tuple(h), tuple(t))
    return out


def side(n):
    """+1 left, -1 right, 0 middle, from box coordinates."""
    return 0 if abs(n[0]) < 0.15 else (1 if n[0] > 0 else -1)


def seg_dist2(p, a, b):
    ab = [b[k] - a[k] for k in range(3)]
    ap = [p[k] - a[k] for k in range(3)]
    den = sum(c * c for c in ab) or 1e-12
    t = max(0.0, min(1.0, sum(x * y for x, y in zip(ap, ab)) / den))
    return sum((ap[k] - t * ab[k]) ** 2 for k in range(3))


# ---------------------------------------------------------------- weights
def smooth(points, box, bones):
    """[[(bone, weight)]] per vertex: the two nearest bones of its side, 1/d^4."""
    eps = (0.01 * box.height) ** 2
    out = []
    for p in points:
        lat = box.coords(p)[0]
        near = sorted((seg_dist2(p, h, t), b) for b, (h, t, s) in bones.items() if s * lat > -0.1)[:2]
        w = [(b, 1.0 / (d + eps) ** 2) for d, b in near]
        total = sum(v for _, v in w)
        out.append([(b, v / total) for b, v in w])
    return out


def pieces(points, triangles):
    """Connected pieces of a primitive: vertices that share a triangle or a position."""
    up = list(range(len(points)))

    def find(i):
        while up[i] != i:
            up[i] = up[up[i]]
            i = up[i]
        return i
    seen = {}
    for i, p in enumerate(points):
        key = tuple(round(c, 5) for c in p)
        up[find(i)] = find(seen.setdefault(key, i))
    for tri in triangles:
        for k in (1, 2):
            up[find(tri[k])] = find(tri[0])
    groups = {}
    for i in range(len(points)):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def _inside(n, box):
    return all(box[2 * k] <= n[k] <= box[2 * k + 1] for k in range(3))


def nearest(p, bones):
    return min((seg_dist2(p, h, t), b) for b, (h, t, _) in bones.items())[1]


def rigid(points, triangles, box, bones, regions):
    """[[(bone, 1.0)]] per vertex: every piece follows the region holding its centre, else the
    bone nearest to it."""
    out = [None] * len(points)
    for piece in pieces(points, triangles):
        centre = [sum(points[i][k] for i in piece) / len(piece) for k in range(3)]
        n = box.coords(centre)
        bone = next((b for b, r in regions if _inside(n, r)), None) or nearest(centre, bones)
        for i in piece:
            out[i] = [(bone, 1.0)]
    return out


def triangles(doc, bin_, prim, count):
    if "indices" not in prim:
        return [(i, i + 1, i + 2) for i in range(0, count - 2, 3)]
    flat = [v[0] for v in read(doc, bin_, prim["indices"])]
    if prim.get("mode", 4) != 4:
        return []
    return [tuple(flat[i:i + 3]) for i in range(0, len(flat) - 2, 3)]


def weigh(doc, bin_, spec, ctx, node, prim):
    """Per-vertex [(bone, weight)] of one primitive."""
    points = rest_points(doc, bin_, ctx["world"], node, prim)
    name = doc["nodes"][node].get("name", "")
    part = next((b for pat, b in spec.get("parts", {}).items() if re.search(pat, name)), None)
    if part is not None:
        return [[(part, 1.0)]] * len(points)
    bones = {b: v for b, v in ctx["bones"].items() if b != "root"}
    if spec.get("weights", "smooth") == "smooth":
        return smooth(points, ctx["box"], bones)
    return rigid(points, triangles(doc, bin_, prim, len(points)), ctx["box"], bones, spec.get("regions", []))


# ---------------------------------------------------------------- nodes
def add_node(doc, name, parent, world_pos, world):
    """A node at `world_pos` under `parent` (-1: a scene root), turned like its parent."""
    local = mpoint(minv(world[parent]), world_pos) if parent >= 0 else list(world_pos)
    doc["nodes"].append({"name": PREFIX + name, "translation": [round(c, 6) for c in local]})
    i = len(doc["nodes"]) - 1
    if parent >= 0:
        doc["nodes"][parent].setdefault("children", []).append(i)
    else:
        doc["scenes"][doc.get("scene", 0)]["nodes"].append(i)
    world.append(mmul(world[parent], trs(doc["nodes"][i])) if parent >= 0 else trs(doc["nodes"][i]))
    return i


def _by_name(doc, name):
    return next(i for i, n in enumerate(doc["nodes"]) if n.get("name") == name)


def _top_joints(doc, par):
    joints = set(doc["skins"][0]["joints"]) if doc.get("skins") else set()
    return [j for j in sorted(joints) if par[j] not in joints]


def add_root(doc, ctx, ground):
    """Our root joint at the ground point; a rig the model had hangs under it (through a node that
    takes the offset back, so its own joints and clips stay as they were)."""
    par = parents(doc)
    tops = _top_joints(doc, par)
    above = par[tops[0]] if tops else -1
    root = add_node(doc, "root", above, ground, ctx["world"])
    if not tops:
        return root
    back = add_node(doc, "root.back", root, mpoint(ctx["world"][above], [0, 0, 0]) if above >= 0 else
                    [0.0, 0.0, 0.0], ctx["world"])
    doc["nodes"][back]["translation"] = [-c for c in doc["nodes"][root]["translation"]]
    for top in tops:
        holder = doc["nodes"][above]["children"] if above >= 0 else doc["scenes"][doc.get("scene", 0)]["nodes"]
        holder.remove(top)
        doc["nodes"][back].setdefault("children", []).append(top)
    if "skeleton" in doc["skins"][0]:
        doc["skins"][0]["skeleton"] = root
    ctx["world"][:] = worlds(doc)
    return root


def add_joints(doc, family, spec, ctx):
    """Joint (head) and end node (tail) of every bone; ctx["bones"] gets their world segments."""
    box, lay = ctx["box"], layout(family, spec)
    attach = {b: _by_name(doc, name) for b, name in spec.get("attach", {}).items()}
    nodes, ends = {}, {}
    for bone, (parent, head, tail) in lay.items():
        h, t = box.point(head), box.point(tail)
        if bone == "root":
            nodes[bone] = add_root(doc, ctx, h)
        elif bone in attach:
            nodes[bone] = attach[bone]
        else:
            nodes[bone] = add_node(doc, bone, nodes[parent], h, ctx["world"])
        ends[bone] = add_node(doc, bone + ".end", nodes[bone], t, ctx["world"])
        ctx["bones"][bone] = (h, t, side(head))
    return nodes, ends


# ---------------------------------------------------------------- skin
def _group(world, node):
    return tuple(round(c, 5) for row in world[node] for c in row)


def bind(doc, bin_, ctx, weights, nodes):
    """Joints for the weights: a bone's own joint for the main mesh frame, an alias joint under it
    for every other frame (a joint's inverse bind matrix fits one mesh frame). Writes the skin,
    JOINTS_0 and WEIGHTS_0; returns the grown bin."""
    world = ctx["world"]
    sizes = {}
    for (node, _, _), w in weights.items():
        sizes[_group(world, node)] = sizes.get(_group(world, node), 0) + len(w)
    main = max(sizes, key=sizes.get)
    joints = doc["skins"][0]["joints"]
    frames = {}                                   # (bone, group) -> (joint slot, a mesh node of the group)
    for (node, mesh, k), per in weights.items():
        group = _group(world, node)
        for bone in sorted({b for v in per for b, _ in v} - {b for b, g in frames if g == group}):
            j = nodes[bone]
            if group != main or j in ctx["old_joints"]:
                j = add_node(doc, f"{bone}~{len(frames)}", j, mpoint(world[j], [0, 0, 0]), world)
                joints.append(j)
            frames[(bone, group)] = (joints.index(j), node)
        flat_j = [c for v in per for c in ([frames[(b, group)][0] for b, _ in v] + [0] * 4)[:4]]
        flat_w = [c for v in per for c in ([w for _, w in v] + [0.0] * 4)[:4]]
        prim = doc["meshes"][mesh]["primitives"][k]
        prim["attributes"]["JOINTS_0"] = append(doc, bin_, flat_j, "B", "VEC4", len(per))
        prim["attributes"]["WEIGHTS_0"] = append(doc, bin_, flat_w, "f", "VEC4", len(per))
        doc["nodes"][node]["skin"] = 0
    _bind_matrices(doc, bin_, 0, frames, world)
    return bin_


def _bind_matrices(doc, bin_, skin, frames, world):
    """skins[skin].inverseBindMatrices for every joint: the old ones kept, ours inv(joint) @ mesh."""
    joints = doc["skins"][skin]["joints"]
    old = doc["skins"][skin].get("inverseBindMatrices")
    mats = [list(m) for m in read(doc, bin_, old)] if old is not None else []
    mesh_of = {slot: node for slot, node in frames.values()}
    for slot in range(len(mats), len(joints)):
        m = mmul(minv(world[joints[slot]]), world[mesh_of[slot]]) if slot in mesh_of else minv(world[joints[slot]])
        mats.append([m[r][c] for c in range(4) for r in range(4)])
    doc["skins"][skin]["inverseBindMatrices"] = append(doc, bin_, [c for m in mats for c in m], "f", "MAT4",
                                                       len(mats))


# ---------------------------------------------------------------- undo
def unrig(doc, bin_):
    """Drop a previous rigging (and the clips injected on top of it): the GLB as it was before."""
    bin_ = IC.strip_previous(doc, bin_)
    mark = doc.get("extras", {}).pop("cf_rig", None)
    if not mark:
        return bin_
    undo = mark["undo"]
    doc["nodes"], doc["scenes"] = undo["nodes"], undo["scenes"]
    doc["skins"] = undo["skins"]
    if not doc["skins"]:
        del doc["skins"]
    for mesh, k in undo["prims"]:
        attrs = doc["meshes"][mesh]["primitives"][k]["attributes"]
        attrs.pop("JOINTS_0", None)
        attrs.pop("WEIGHTS_0", None)
    doc["accessors"], doc["bufferViews"] = doc["accessors"][:undo["accessors"]], doc["bufferViews"][:undo["views"]]
    if not doc["extras"]:
        del doc["extras"]
    doc["buffers"][0]["byteLength"] = undo["bin"]
    return bytearray(bin_[:undo["bin"]])


def _undo_record(doc, bin_, weighted):
    """What rigging changes in place: nodes, scenes, skins (copied), primitives given weights, and the
    sizes the appended accessors, views and bytes start at."""
    def copy(value):
        return json.loads(json.dumps(value))
    return {"nodes": copy(doc["nodes"]), "scenes": copy(doc["scenes"]), "skins": copy(doc.get("skins", [])),
            "prims": [[m, k] for _, m, k in weighted], "accessors": len(doc.get("accessors", [])),
            "views": len(doc.get("bufferViews", [])), "bin": len(bin_)}


# ---------------------------------------------------------------- the .rig/.joints of fetch_models.mjs
def _column_major(node):
    m = trs({k: v for k, v in node.items() if k != "matrix"})
    return [m[r][c] for c in range(4) for r in range(4)]


def _num(v):
    return str(int(v)) if float(v).is_integer() else repr(float(v))


def rig_files(glb, doc, bin_):
    """<id>.rig (node tree, joints, inverse binds, mesh nodes) and <id>.joints (the joint each mesh
    hangs under, -1 none), the same as scripts/fetch_models.mjs writes."""
    par, skin = parents(doc), doc["skins"][0]
    joints = skin["joints"]
    ibm = [list(m) for m in read(doc, bin_, skin["inverseBindMatrices"])] if "inverseBindMatrices" in skin else \
        [[1.0 if k % 5 == 0 else 0.0 for k in range(16)] for _ in joints]
    tri = [i for i, m, k in primitives(doc) if doc["meshes"][m]["primitives"][k].get("mode", 4) == 4]
    lines = ["CF_RIG 1", f"{len(doc['nodes'])} {len(joints)} {len(tri)}"]
    lines += [" ".join([str(par[i])] + [_num(v) for v in _column_major(n)]) for i, n in enumerate(doc["nodes"])]
    lines += [" ".join(map(str, joints))] + [" ".join(_num(v) for v in m) for m in ibm] + [" ".join(map(str, tri))]
    glb.with_suffix(".rig").write_text("\n".join(lines) + "\n")

    def joint_of(n):
        while n >= 0 and n not in joints:
            n = par[n]
        return joints.index(n) if n >= 0 else -1
    glb.with_suffix(".joints").write_text("".join(f"{joint_of(i)}\n" for i in tri))


# ---------------------------------------------------------------- per unit
def digest(unit_id, spec):
    return hashlib.sha1(json.dumps([VERSION, family_of(unit_id, spec), spec], sort_keys=True).encode()).hexdigest()


def _targets(doc):
    """The primitives we weigh: all of a static model; the unweighted ones of a rigged one."""
    return [(i, m, k) for i, m, k in primitives(doc)
            if "JOINTS_0" not in doc["meshes"][m]["primitives"][k]["attributes"]]


def build(unit_id, spec, doc, bin_):
    """Rig the (un-rigged) doc in place; returns the grown bin."""
    family = family_of(unit_id, spec)
    weighted = _targets(doc)
    world = worlds(doc)
    points = [p for i, m, k in primitives(doc) for p in rest_points(doc, bin_, world, i,
                                                                      doc["meshes"][m]["primitives"][k])]
    undo = _undo_record(doc, bin_, weighted)
    doc.setdefault("skins", [{"joints": []}])
    ctx = {"world": world, "box": Box(points, spec["front"]), "bones": {},
           "old_joints": set(doc["skins"][0]["joints"])}
    nodes, ends = add_joints(doc, family, spec, ctx)
    for j in nodes.values():                      # every bone a joint, even one nothing hangs from
        if j not in doc["skins"][0]["joints"]:
            doc["skins"][0]["joints"].append(j)
    weights = {key: weigh(doc, bin_, spec, ctx, key[0], doc["meshes"][key[1]]["primitives"][key[2]])
               for key in weighted}
    bin_ = bind(doc, bin_, ctx, weights, nodes)
    box = ctx["box"]
    doc.setdefault("extras", {})["cf_rig"] = {
        "hash": digest(unit_id, spec), "family": family, "row": spec.get("row", unit_id),
        "relative": spec.get("relative", True),
        "map": {b: [nodes[b], ends[b]] for b in nodes}, "axes": [box.left, box.up, box.front], "undo": undo}
    doc["buffers"][0]["byteLength"] = len(bin_)
    return bin_


def rig(unit_id, spec=None, force=False):
    glb = ASSETS / f"{unit_id}.glb"
    if not glb.exists():
        return "no GLB"
    spec = spec or RIGS[unit_id]
    doc, bin_ = IC.read_glb(glb)
    if not force and doc.get("extras", {}).get("cf_rig", {}).get("hash") == digest(unit_id, spec):
        return "up to date"
    bin_ = build(unit_id, spec, doc, unrig(doc, bin_))
    IC.write_glb(glb, doc, bin_)
    rig_files(glb, doc, bin_)
    return f"rigged {len(doc['extras']['cf_rig']['map'])} bones"


def project_own():
    """Units whose model is ours (license project-own in data/models.tsv): they come rigged."""
    rows = (ROOT / "data/models.tsv").read_text().splitlines()
    cols = rows[0].split("\t")
    return {r.split("\t")[0] for r in rows[1:] if r.split("\t")[cols.index("license")] == "project-own"}


def main():
    if not ASSETS.exists():
        print("rig_static: no assets/models (run make assets); skipped")
        return
    ids = [a for a in sys.argv[1:] if not a.startswith("--")] or sorted(set(RIGS) - project_own())
    for unit_id in ids:
        if "--list" in sys.argv[1:]:
            family = family_of(unit_id, RIGS[unit_id])
            print(unit_id, family, sorted(layout(family, RIGS[unit_id])))
            continue
        print(unit_id, rig(unit_id, force="--force" in sys.argv[1:]))


if __name__ == "__main__":
    main()
