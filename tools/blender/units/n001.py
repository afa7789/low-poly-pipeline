"""Dragao Vermelho (n001, familia drake): medido em artifacts/model-sheets/refs/n001/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n001.py -- <out.glb>

Em pe sobre as patas de tras, como na prancha. As asas sao superficies continuas: braco (ombro -> pulso) no osso
upper, dedos e paineis de membrana no osso lower, o painel interno macio entre os dois.
"""
import pathlib
import sys

import bmesh
import bpy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "red": 0xA82A1E, "red_dk": 0x7C1A14, "orange": 0xE5701A, "tan": 0xCDA568, "wing_arm": 0xC8421A,
    "membrane": 0x2E3537, "black": 0x1B1A1E, "grey": 0x4A4D55, "steel": 0x6A6D75, "eye": 0xFFD020,
    "white": 0xE8E2D0, "mouth": 0x6A1010,
}

# juntas (metros), medidas no perfil / frente / topo da prancha (0,0042 m por pixel na frente e no perfil)
SPINE = [(0, 0.9, -0.38), (0, 1.3, -0.08), (0, 1.66, 0.05)]
NECK = [(0, 1.66, 0.05), (0, 1.92, 0.26), (0, 2.2, 0.3)]
HEAD_TIP, JAW_A, JAW_B = (0, 2.4, 0.9), (0, 2.3, 0.45), (0, 2.2, 0.8)
TAIL = [(0, 0.9, -0.38), (0, 0.68, -0.95), (0, 0.45, -1.6), (0, 0.27, -2.15)]
TAIL_R = [((0.2, 0.24), (0.14, 0.17)), ((0.14, 0.17), (0.09, 0.11)), ((0.09, 0.11), (0.015, 0.015))]
HIP_X, HIP, KNEE, TOE = 0.3, (0.98, -0.38), (0.66, -0.06), (0.05, -0.2)
ANKLE = (0.4, -0.48)
SH_X, SH_Y, SH_Z, EL, HAND = 0.56, 1.6, 0.06, (0.62, 1.22, 0.2), (0.58, 0.95, 0.3)
SHOULDER, WRIST, ROOT_REAR = (0.36, 1.68, 0.0), (0.8, 2.8, 0.1), (0.34, 1.32, -0.5)
FINGERS = [(1.85, 1.0, -0.95), (1.35, 1.05, -1.2), (0.85, 1.15, -1.1), (0.46, 1.4, -0.8)]


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def flip(p, s):
    return (p[0] * s, p[1], p[2])


def panel(bone, tone, pts, thick=0.02):
    """Thin flat wedge from a polygon in family coordinates, rigid on `bone`."""
    p = [H.to_blender(q) for q in pts]
    n = (p[1] - p[0]).cross(p[2] - p[0]).normalized()
    bm = bmesh.new()
    lo = [bm.verts.new(q - n * thick) for q in p]
    hi = [bm.verts.new(q + n * thick) for q in p]
    for i in range(len(p)):
        j = (i + 1) % len(p)
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bm.faces.new(lo[::-1])
    bm.faces.new(hi)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(tone)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(f"{tone}.{len(H.PIECES)}", mesh)
    bpy.context.collection.objects.link(obj)
    obj["tone"] = tone
    H.PIECES.append((obj, bone))
    return obj


def spike(bone, base, tip, r=0.035):
    H.frustum(bone, "black", base, tip, (r, r), (0.004, 0.004), sides=4)


def head():
    H.frustum("head", "red", (0, 2.36, 0.26), (0, 2.42, 0.62), (0.25, 0.22), (0.17, 0.14), sides=6)
    H.frustum("head", "red", (0, 2.42, 0.58), (0, 2.4, 0.9), (0.16, 0.12), (0.1, 0.07), sides=6)
    H.frustum("jaw", "red_dk", (0, 2.3, 0.45), (0, 2.2, 0.82), (0.15, 0.065), (0.08, 0.035), sides=4)
    H.frustum("head", "mouth", (0, 2.33, 0.5), (0, 2.31, 0.86), (0.11, 0.025), (0.065, 0.025), sides=4)
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.14, 2.52, 0.62), (0.07, 0.05, 0.09))
        H.frustum("head", "white", (s * 0.06, 2.34, 0.88), (s * 0.06, 2.27, 0.89), (0.012, 0.012), (0.003, 0.003), sides=4)
        H.frustum("jaw", "white", (s * 0.05, 2.22, 0.78), (s * 0.05, 2.31, 0.8), (0.012, 0.012), (0.003, 0.003), sides=4)
        H.frustum("head", "red", (s * 0.2, 2.38, 0.36), (s * 0.38, 2.44, 0.3), (0.07, 0.07), (0.01, 0.01), sides=4)  # bochecha
        for a, b, r in (((0.16, 2.56, 0.38), (0.26, 2.84, 0.2), 0.09), ((0.26, 2.82, 0.21), (0.34, 3.05, -0.02), 0.06)):
            H.frustum("head", "black", flip(a, s), flip(b, s), (r, r), (r * 0.65, r * 0.65), sides=4)
    spike("head", (0, 2.5, 0.34), (0, 2.66, 0.24))


def neck_torso():
    H.frustum("neck.1", "red", (0, 1.62, 0.04), (0, 1.94, 0.27), (0.24, 0.24), (0.17, 0.17), sides=6)
    H.frustum("neck.2", "red", (0, 1.9, 0.25), (0, 2.24, 0.3), (0.17, 0.17), (0.14, 0.15), sides=6)
    H.frustum("neck.1", "tan", (0, 1.7, 0.21), (0, 1.94, 0.38), (0.09, 0.03), (0.09, 0.03), sides=4)
    H.frustum("neck.2", "tan", (0, 1.92, 0.38), (0, 2.18, 0.42), (0.09, 0.03), (0.07, 0.03), sides=4)
    H.frustum("neck.1", "grey", (0, 1.86, 0.2), (0, 2.04, 0.25), (0.3, 0.3), (0.3, 0.3), sides=8)    # coleira
    H.frustum("spine.1", "red", (0, 0.84, -0.38), (0, 1.32, -0.08), (0.36, 0.36), (0.42, 0.38), sides=6)
    H.frustum("spine.2", "red", (0, 1.28, -0.08), (0, 1.72, 0.06), (0.42, 0.38), (0.5, 0.36), sides=6)
    H.frustum("spine.1", "tan", (0, 0.92, -0.04), (0, 1.3, 0.18), (0.07, 0.02), (0.08, 0.02), sides=4)
    H.box("spine.2", "grey", (0, 1.42, 0.3), (0.6, 0.5, 0.15))                                       # peitoral
    for s in (-1, 1):
        H.frustum("spine.2", "steel", (s * 0.17, 1.64, 0.32), (-s * 0.17, 1.2, 0.32), (0.025, 0.025), (0.025, 0.025), sides=4)
    for y, z in ((1.7, 0.0), (1.5, -0.1), (1.28, -0.2), (1.05, -0.3), (2.0, 0.17), (2.2, 0.2)):
        bone = "spine.2" if y > 1.4 else "spine.1"
        bone = "neck.2" if y > 1.95 else bone
        spike(bone, (0, y, z - 0.2 if y < 1.95 else z - 0.1), (0, y + 0.12, z - 0.34 if y < 1.95 else z - 0.2))


def tail():
    for i, (rs, re) in enumerate(TAIL_R):
        a, b = TAIL[i], TAIL[i + 1]
        bone = f"tail.{i + 1}"
        H.frustum(bone, "red", a, b, rs, re, sides=6)
        H.frustum(bone, "tan", (0, a[1] - rs[1] + 0.03, a[2]), (0, b[1] - re[1] + 0.02, b[2]), (0.035 - i * 0.01, 0.02), (0.015, 0.012), sides=4)
        mid = lerp(a, b, 0.5)
        spike(bone, (0, mid[1] + rs[1] - 0.02, mid[2]), (0, mid[1] + rs[1] + 0.1 - i * 0.02, mid[2] - 0.08), 0.03 - i * 0.006)


def hind_legs():
    for s, n, side in ((1, 3, "L"), (-1, 4, "R")):
        x = s * HIP_X
        H.frustum(f"leg{n}.upper", "orange", (x, HIP[0] + 0.04, HIP[1] - 0.02), (x * 1.04, KNEE[0], KNEE[1]), (0.25, 0.3), (0.18, 0.2), sides=6)
        low = f"leg{n}.lower"
        H.frustum(low, "red", (x * 1.04, KNEE[0] + 0.02, KNEE[1]), (x, ANKLE[0], ANKLE[1]), (0.15, 0.15), (0.09, 0.09), sides=6)
        H.frustum(low, "red_dk", (x, ANKLE[0] + 0.03, ANKLE[1]), (x, TOE[0] + 0.03, TOE[1]), (0.1, 0.09), (0.15, 0.07), sides=6)
        for dx in (-0.07, 0, 0.07):
            H.frustum(low, "black", (x + dx, 0.05, TOE[1]), (x + dx * 1.3, 0.0, TOE[1] + 0.12), (0.02, 0.03), (0.004, 0.004), sides=4)


def fore_legs():
    for s, n in ((1, 1), (-1, 2)):
        sh, el, hd = (s * SH_X, SH_Y, SH_Z), (s * EL[0], EL[1], EL[2]), (s * HAND[0], HAND[1], HAND[2])
        H.frustum(f"leg{n}.upper", "orange", (sh[0], sh[1] + 0.1, sh[2]), el, (0.23, 0.23), (0.14, 0.14), sides=6)
        H.frustum(f"leg{n}.lower", "red", (el[0], el[1] + 0.03, el[2]), hd, (0.13, 0.13), (0.09, 0.09), sides=6)
        for dx in (-0.04, 0, 0.04):
            H.frustum(f"leg{n}.lower", "black", (hd[0] + dx, hd[1] + 0.02, hd[2]), (hd[0] + dx, hd[1] - 0.12, hd[2] + 0.07), (0.018, 0.02), (0.004, 0.004), sides=4)


def wing(s, n):
    up, low = f"wing{n}.upper", f"wing{n}.lower"
    sh, wr, root = flip(SHOULDER, s), flip(WRIST, s), flip(ROOT_REAR, s)
    tips = [flip(f, s) for f in FINGERS]
    H.frustum(up, "wing_arm", sh, wr, (0.12, 0.12), (0.07, 0.07), sides=6)
    H.frustum(up, "orange", flip((0.2, 1.7, 0.02), s), flip((0.4, 2.2, 0.12), s), (0.17, 0.14), (0.11, 0.1), sides=6)
    spike(low, wr, flip((0.78, 2.92, 0.5), s), 0.045)
    for tip in tips:
        H.frustum(low, "wing_arm", wr, tip, (0.055, 0.055), (0.025, 0.025), sides=4)
    for i in range(3):
        a, b = tips[i], tips[i + 1]
        scallop = lerp(lerp(a, b, 0.5), wr, 0.22)
        panel(low, "membrane", [wr, a, scallop, b])
    inner = panel(up, "membrane", [sh, wr, tips[3], root])
    key = [(wr, 1.0), (tips[3], 1.0), (sh, 0.0), (root, 0.0)]

    def weigh(p):
        near = min(key, key=lambda k: sum((p[i] - k[0][i]) ** 2 for i in range(3)))[1]
        return {low: near, up: 1.0 - near}

    H.soft(inner, weigh)


def make():
    head()
    neck_torso()
    tail()
    hind_legs()
    fore_legs()
    wing(1, 1)
    wing(-1, 2)


def joints():
    out = {"spine.1": (SPINE[0], SPINE[1]), "spine.2": (SPINE[1], SPINE[2]),
           "neck.1": (NECK[0], NECK[1]), "neck.2": (NECK[1], NECK[2]),
           "head": (NECK[2], HEAD_TIP), "jaw": (JAW_A, JAW_B)}
    for i in range(3):
        out[f"tail.{i + 1}"] = (TAIL[i], TAIL[i + 1])
    for s, n in ((1, 3), (-1, 4)):
        out[f"leg{n}.upper"] = ((s * HIP_X, HIP[0], HIP[1]), (s * HIP_X * 1.04, KNEE[0], KNEE[1]))
        out[f"leg{n}.lower"] = ((s * HIP_X * 1.04, KNEE[0], KNEE[1]), (s * HIP_X, TOE[0], TOE[1]))
    for s, n in ((1, 1), (-1, 2)):
        out[f"leg{n}.upper"] = ((s * SH_X, SH_Y, SH_Z), (s * EL[0], EL[1], EL[2]))
        out[f"leg{n}.lower"] = ((s * EL[0], EL[1], EL[2]), (s * HAND[0], HAND[1], HAND[2]))
    for s, n in ((1, 1), (-1, 2)):
        out[f"wing{n}.upper"] = (flip(SHOULDER, s), flip(WRIST, s))
        out[f"wing{n}.lower"] = (flip(WRIST, s), flip(FINGERS[0], s))
    return out


H.build("n001", "drake", PALETTE, make, joints())
