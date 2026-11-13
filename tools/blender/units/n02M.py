"""Goblin Rocketeer (n02M): medido em artifacts/model-sheets/refs/n02M/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n02M.py -- <out.glb>

Goblin de capacete e mascara de gas, ombreiras vermelhas, luvas enormes (maos vazias) e o tubo de foguete
na diagonal nas costas, preso na coluna (bone spine).
"""
import pathlib
import sys

from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "skin": 0x7E8A3E, "skin_dk": 0x5F6A2E, "helmet": 0x6B7A90, "helmet_dk": 0x56637A, "red": 0xA02C22, "red_dk": 0x7E1F1A,
    "gold": 0xC9A040, "mask": 0x6A4630, "glass": 0xC8CCD4, "glove": 0x85603C, "glove_dk": 0x6A4A2E, "suit": 0x575A68,
    "apron": 0x5A2428, "wrap": 0xC8B58A, "boot": 0x3A3844, "tube": 0x7A8190, "tube_lt": 0x9AA2B0, "fire": 0xFFA020,
    "strap": 0x6E4A32,
}

HIP, KNEE, ANKLE, LEG_X = 0.62, 0.35, 0.13, 0.28
WAIST, NECK, TOP = 0.85, 1.4, 2.16
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.5, 1.28, 0.68, 0.93, 0.55


def head():
    H.frustum("head", "skin", (0, 1.45, 0.05), (0, 1.66, 0.05), (0.22, 0.2), (0.26, 0.24), sides=8)
    H.frustum("head", "skin", (0, 1.66, 0.05), (0, 1.86, 0.05), (0.26, 0.24), (0.24, 0.22), sides=8)
    H.frustum("head", "mask", (0, 1.62, 0.2), (0, 1.52, 0.55), (0.11, 0.11), (0.08, 0.08), sides=6)
    H.frustum("head", "gold", (0, 1.52, 0.52), (0, 1.5, 0.68), (0.1, 0.1), (0.1, 0.1), sides=6)
    for s in (-1, 1):
        H.frustum("head", "mask", (s * 0.11, 1.72, 0.25), (s * 0.11, 1.72, 0.33), (0.115, 0.115), (0.115, 0.115), sides=8)
        H.frustum("head", "glass", (s * 0.11, 1.72, 0.32), (s * 0.11, 1.72, 0.36), (0.085, 0.085), (0.085, 0.085), sides=8)
        H.frustum("head", "skin", (s * 0.2, 1.8, 0.0), (s * 0.74, 1.9, -0.04), (0.1, 0.16), (0.01, 0.02), sides=4)      # orelha
        H.frustum("head", "skin_dk", (s * 0.2, 1.76, 0.0), (s * 0.5, 1.8, -0.02), (0.06, 0.08), (0.03, 0.04), sides=4)
    H.frustum("head", "helmet_dk", (0, 1.83, 0.12), (0, 1.9, 0.12), (0.5, 0.56), (0.42, 0.46), sides=8)        # aba
    H.frustum("head", "helmet", (0, 1.9, 0.06), (0, 2.06, 0.06), (0.34, 0.33), (0.3, 0.3), sides=8)           # copa
    H.frustum("head", "helmet", (0, 2.06, 0.06), (0, 2.16, 0.06), (0.3, 0.3), (0.14, 0.14), sides=8)


def torso():
    H.frustum("spine", "suit", (0, 0.7, 0), (0, 1.0, 0), (0.3, 0.24), (0.34, 0.26), sides=8)
    H.frustum("spine", "suit", (0, 1.0, 0), (0, 1.4, 0), (0.34, 0.26), (0.38, 0.27), sides=8)
    H.frustum("spine", "red", (0, 0.82, 0.2), (0, 1.3, 0.22), (0.34, 0.12), (0.4, 0.13), sides=8)         # peitoral
    H.frustum("spine", "gold", (0, 0.78, 0.2), (0, 0.84, 0.22), (0.33, 0.11), (0.33, 0.11), sides=4)
    H.frustum("pelvis", "apron", (0, 0.3, 0.14), (0, 0.84, 0.1), (0.36, 0.1), (0.31, 0.1), sides=4)       # avental
    H.frustum("pelvis", "suit", (0, 0.55, 0), (0, 0.88, 0), (0.3, 0.24), (0.3, 0.24), sides=8)
    H.frustum("spine", "strap", (0.3, 1.38, 0.02), (-0.3, 0.8, -0.3), (0.05, 0.03), (0.05, 0.03), sides=4)   # tira do tubo


def tube():
    top, bot = Vector((-0.45, 2.42, -0.12)), Vector((0.3, 0.82, -0.58))

    def at(t):
        return tuple(bot.lerp(top, t))
    H.frustum("spine", "gold", at(0.0), at(0.07), (0.1, 0.1), (0.24, 0.24), sides=8)          # bocal do foguete
    H.frustum("spine", "gold", at(0.07), at(0.14), (0.26, 0.26), (0.26, 0.26), sides=8)
    H.frustum("spine", "tube", at(0.14), at(0.9), (0.21, 0.21), (0.21, 0.21), sides=8)
    H.frustum("spine", "tube_lt", at(0.3), at(0.88), (0.14, 0.21), (0.14, 0.21), sides=4)
    H.frustum("spine", "gold", at(0.9), at(0.97), (0.29, 0.29), (0.29, 0.29), sides=6)
    H.frustum("spine", "gold", at(0.95), at(1.04), (0.12, 0.12), (0.0, 0.0), sides=6)        # ponta do foguete
    flame = bot + Vector((-0.02, -0.2, -0.04))
    H.frustum("spine", "fire", tuple(bot), tuple(flame), (0.05, 0.05), (0.0, 0.0), sides=4)


def arm(s, side):
    a, f = f"arm.{side}", f"forearm.{side}"
    H.frustum(a, "red", (s * 0.52, 1.12, 0), (s * 0.52, 1.38, 0), (0.25, 0.24), (0.27, 0.26), sides=8)       # ombreira
    H.frustum(a, "gold", (s * 0.52, 1.1, 0), (s * 0.52, 1.16, 0), (0.27, 0.26), (0.27, 0.26), sides=8)
    H.frustum(a, "red", (s * 0.52, 1.38, 0), (s * 0.52, 1.48, 0), (0.27, 0.26), (0.1, 0.1), sides=8)
    H.frustum(a, "skin", (s * SH_X, 1.3, 0), (s * EL_X, EL_Y, 0.02), (0.15, 0.15), (0.13, 0.12), sides=6)
    H.frustum(f, "skin", (s * EL_X, 1.0, 0.02), (s * EL_X, 0.78, 0.05), (0.1, 0.1), (0.1, 0.1), sides=6)
    H.frustum(f, "glove", (s * EL_X, 0.9, 0.05), (s * EL_X, 0.68, 0.06), (0.12, 0.13), (0.2, 0.17), sides=6)          # punho da luva
    H.frustum(f, "glove_dk", (s * EL_X, 0.7, 0.06), (s * EL_X, 0.64, 0.06), (0.21, 0.18), (0.21, 0.18), sides=6)
    H.frustum(f, "glove", (s * EL_X, 0.66, 0.06), (s * (EL_X + 0.02), 0.4, 0.08), (0.2, 0.17), (0.25, 0.19), sides=6)
    H.frustum(f, "glove", (s * (EL_X + 0.02), 0.42, 0.08), (s * (EL_X + 0.03), 0.16, 0.12), (0.25, 0.19), (0.13, 0.09), sides=6)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * LEG_X
        H.frustum(f"thigh.{side}", "suit", (x, KNEE - 0.03, 0), (x, HIP + 0.05, 0), (0.14, 0.15), (0.19, 0.19), sides=6)
        H.frustum(f"shin.{side}", "wrap", (x, ANKLE, 0), (x, KNEE + 0.02, 0), (0.15, 0.15), (0.13, 0.13), sides=6)
        for y in (0.2, 0.28):
            H.frustum(f"shin.{side}", "glove_dk", (x, y, 0), (x, y + 0.03, 0), (0.155, 0.155), (0.155, 0.155), sides=6)
        H.frustum(f"foot.{side}", "boot", (x, 0.03, -0.04), (x, 0.17, -0.02), (0.18, 0.17), (0.15, 0.15), sides=6)
        H.frustum(f"foot.{side}", "boot", (x, 0.1, 0.0), (x, 0.08, 0.4), (0.18, 0.1), (0.15, 0.06), sides=4)


def make():
    head()
    torso()
    tube()
    legs()
    for s, side in ((1, "L"), (-1, "R")):
        arm(s, side)


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0.05), (0, TOP, 0.05))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.4))
    return out


H.build("n02M", "biped", PALETTE, make, joints())
