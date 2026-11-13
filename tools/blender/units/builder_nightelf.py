"""Night Elf Wisp Builder (builder_nightelf): elfa de capuz e poncho, cajado de lua crescente na mao esquerda,
lanterna e bolsa no quadril.

    blender -b --factory-startup -P tools/blender/units/builder_nightelf.py -- <out.glb>
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "cloak": 0x403B60, "cloak_dk": 0x2D2A47, "trim": 0xA2A4AE, "legs": 0x211D30, "boot": 0x4F446C, "boot_dk": 0x3B3253,
    "skin": 0x4C4568, "face": 0x14121C, "ear": 0x7A56A4, "eye": 0xD060FF, "staff": 0x2E2842, "silver": 0xB4B7BF,
    "lantern": 0x17151F, "glow": 0xE6C8FF, "bag": 0x8E9098, "clasp": 0x9A58D0, "belt": 0x2F2A42,
}
HIP, KNEE, ANKLE, WAIST, NECK, TOP = 1.25, 0.68, 0.2, 1.55, 2.2, 2.72
LEG_X, SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.2, 0.36, 2.15, 0.42, 1.6, 1.3
HAND = (0.6, 1.76, 0.47)      # punho esquerdo medido na prancha
STAFF_A, STAFF_B = (0.4, 0.0, 0.27), (0.69, 2.55, 0.56)    # cajado inclinado: pe e topo


def head():
    H.frustum("head", "skin", (0, 2.2, 0.02), (0, 2.5, 0.04), (0.17, 0.17), (0.19, 0.19), sides=6)
    H.frustum("head", "face", (0, 2.3, 0.2), (0, 2.5, 0.2), (0.2, 0.1), (0.21, 0.1), sides=6)          # sombra do capuz
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.09, 2.42, 0.31), (0.07, 0.035, 0.03))
        H.frustum("head", "ear", (s * 0.2, 2.46, 0), (s * 0.4, 2.62, 0), (0.07, 0.04), (0.01, 0.01), sides=4)
    H.frustum("head", "cloak", (0, 2.2, -0.08), (0, 2.5, -0.08), (0.29, 0.28), (0.27, 0.27), sides=8)         # capuz
    H.frustum("head", "cloak", (0, 2.5, -0.08), (0, 2.76, -0.14), (0.27, 0.27), (0.06, 0.07), sides=8)
    H.frustum("head", "cloak_dk", (0, 2.3, -0.2), (0, 2.6, -0.36), (0.2, 0.16), (0.1, 0.1), sides=6)    # ponta caida
    H.frustum("head", "trim", (0, 2.36, 0.24), (0, 2.66, 0.2), (0.26, 0.05), (0.15, 0.05), sides=4)


def torso():
    H.frustum("spine", "legs", (0, WAIST - 0.05, 0), (0, 2.1, 0), (0.28, 0.22), (0.34, 0.24), sides=8)
    H.frustum("pelvis", "belt", (0, WAIST - 0.14, 0), (0, WAIST + 0.04, 0), (0.3, 0.24), (0.3, 0.24), sides=8)
    H.frustum("pelvis", "legs", (0, 1.05, 0), (0, WAIST - 0.1, 0), (0.28, 0.23), (0.3, 0.24), sides=8)
    # poncho: pilha larga e aberta, ombros inclinados, barra com debrum prateado, ponta longa atras
    H.frustum("spine", "cloak", (0, 1.75, -0.03), (0, 2.05, 0), (0.5, 0.36), (0.44, 0.32), sides=8)
    H.frustum("spine", "cloak", (0, 2.05, 0), (0, 2.3, 0), (0.44, 0.32), (0.26, 0.26), sides=8)
    H.frustum("spine", "trim", (0, 1.7, -0.03), (0, 1.8, -0.03), (0.53, 0.38), (0.5, 0.36), sides=8)
    H.frustum("spine", "cloak_dk", (0, 1.3, -0.34), (0, 1.8, -0.1), (0.12, 0.05), (0.4, 0.26), sides=6)
    for s in (-1, 1):       # cintas cruzadas no peito
        H.frustum("spine", "trim", (s * 0.42, 2.0, 0.34), (-s * 0.3, 1.5, 0.36), (0.05, 0.02), (0.05, 0.02), sides=4)
    H.frustum("pelvis", "bag", (-0.28, 1.17, 0.02), (-0.28, 1.5, 0.02), (0.06, 0.22), (0.06, 0.2), sides=4)
    H.box("pelvis", "clasp", (-0.28, 1.35, 0.24), (0.04, 0.12, 0.05))
    H.frustum("pelvis", "lantern", (0.3, 1.05, 0.22), (0.3, 1.3, 0.22), (0.12, 0.12), (0.15, 0.15), sides=6)
    H.frustum("pelvis", "glow", (0.3, 1.12, 0.22), (0.3, 1.24, 0.22), (0.07, 0.07), (0.07, 0.07), sides=6)


def leg(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "legs", (x, KNEE - 0.04, 0), (x, HIP + 0.05, 0), (0.15, 0.16), (0.2, 0.2), sides=6)
    H.frustum(f"shin.{side}", "legs", (x, 0.55, 0), (x, KNEE + 0.04, 0), (0.15, 0.15), (0.15, 0.16), sides=6)
    H.frustum(f"shin.{side}", "boot", (x, ANKLE - 0.06, 0), (x, 0.62, 0), (0.15, 0.16), (0.2, 0.2), sides=6)   # cano da bota, alarga no topo
    H.frustum(f"shin.{side}", "boot_dk", (x, 0.4, 0), (x, 0.46, 0), (0.2, 0.2), (0.2, 0.2), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.09, -0.04), (x, 0.08, 0.4), (0.17, 0.12), (0.1, 0.05), sides=6)


def arm_free():
    H.frustum("arm.R", "cloak_dk", (-SH_X, SH_Y + 0.02, 0), (-EL_X, EL_Y, 0), (0.11, 0.11), (0.09, 0.09), sides=6)
    H.frustum("forearm.R", "skin", (-EL_X, EL_Y + 0.02, 0), (-EL_X, WR_Y - 0.1, 0), (0.09, 0.09), (0.08, 0.08), sides=6)
    H.frustum("forearm.R", "skin", (-EL_X, WR_Y - 0.05, 0), (-EL_X, WR_Y - 0.4, 0.03), (0.1, 0.07), (0.08, 0.05), sides=6)


def arm_staff():
    hx, hy, hz = HAND
    H.frustum("arm.L", "cloak_dk", (SH_X, SH_Y + 0.02, 0), (EL_X, EL_Y, 0.04), (0.11, 0.11), (0.09, 0.09), sides=6)
    H.frustum("forearm.L", "skin", (EL_X, EL_Y + 0.02, 0.04), (hx, hy - 0.06, hz - 0.06), (0.09, 0.09), (0.1, 0.1), sides=6)
    H.frustum("forearm.L", "skin", (hx, hy + 0.1, hz), (hx, hy - 0.1, hz), (0.11, 0.11), (0.1, 0.1), sides=6)    # punho
    # cajado inclinado como na prancha, da ponta no chao ate a lua crescente aberta para fora
    bx, by, bz = STAFF_B
    H.frustum("forearm.L", "staff", STAFF_A, STAFF_B, (0.05, 0.05), (0.045, 0.045), sides=6)
    cx, cy, r = bx + 0.19, by + 0.05, 0.2
    angles = [40, 90, 135, 180, 225, 270, 320]
    pts = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)), bz) for a in angles]
    H.frustum("forearm.L", "staff", (bx, by, bz), (pts[3][0], pts[3][1], bz), (0.045, 0.045), (0.04, 0.04), sides=6)
    H.chain("forearm.L", "silver", pts, [(0.02, 0.03), (0.04, 0.045), (0.05, 0.05), (0.055, 0.05), (0.05, 0.05), (0.04, 0.045), (0.02, 0.03)], sides=6)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    arm_free()
    arm_staff()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)), "head": ((0, NECK, 0), (0, TOP, 0)),
           "arm.L": ((SH_X, SH_Y, 0), (EL_X, EL_Y, 0.04)), "forearm.L": ((EL_X, EL_Y, 0.04), HAND),
           "arm.R": ((-SH_X, SH_Y, 0), (-EL_X, EL_Y, 0)), "forearm.R": ((-EL_X, EL_Y, 0), (-EL_X, WR_Y - 0.1, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.07, 0.45))
    return out


H.build("builder_nightelf", "biped", PALETTE, make, joints())
