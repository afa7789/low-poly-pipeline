"""Human Peasant Builder (builder_human): medido em artifacts/model-sheets/refs/builder_human/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/builder_human.py -- <out.glb>
"""
import pathlib
import sys

from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "coat": 0x5E6A44, "coat_dk": 0x485338, "puttee": 0x7D7656, "puttee_dk": 0x5F5A40, "boot": 0x232326,
    "helmet": 0x4A4E54, "helmet_dk": 0x383B40, "steel": 0x7C858E, "steel_dk": 0x5A636B, "wood": 0x6B5238,
    "skin": 0xB58A72, "beard": 0x2A221E, "mask": 0x1E1E22, "lens": 0x6A7078, "khaki": 0x948A64,
    "khaki_dk": 0x6E664A, "blue": 0x2040D8, "belt": 0x4A3A2A, "lantern": 0x8A8E92, "glow": 0xFFD060,
}

HIP, KNEE, ANKLE, LEG_X = 0.85, 0.46, 0.15, 0.3
WAIST, NECK, TOP = 1.2, 1.95, 2.5
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.6, 1.85, 0.72, 1.3, 0.95
HAND = (-0.6, 1.8, 0.45)            # mão direita, ombro alto, segura o cabo
BUTT, BLADE_TIP = Vector((-0.95, 1.6, 0.85)), Vector((0.8, 2.5, -0.85))


def hem(p):
    if p[1] > 0.9:
        return {"pelvis": 1.0}
    return {"pelvis": 0.45, "thigh.L" if p[0] > 0 else "thigh.R": 0.55}


def head():
    H.frustum("head", "skin", (0, 1.93, 0.02), (0, 2.3, 0.02), (0.19, 0.2), (0.22, 0.22), sides=6)
    H.frustum("head", "beard", (0, 1.96, 0.1), (0, 2.18, 0.12), (0.19, 0.14), (0.22, 0.12), sides=6)
    H.frustum("head", "helmet_dk", (0, 2.24, 0), (0, 2.3, 0), (0.46, 0.44), (0.4, 0.38), sides=8)      # aba
    H.frustum("head", "helmet", (0, 2.3, 0), (0, 2.44, 0), (0.3, 0.29), (0.26, 0.25), sides=8)
    H.frustum("head", "helmet", (0, 2.44, 0), (0, 2.52, 0), (0.26, 0.25), (0.12, 0.12), sides=8)
    H.frustum("head", "coat", (0, 1.86, -0.02), (0, 2.08, -0.02), (0.3, 0.28), (0.26, 0.24), sides=8)  # gola


def torso():
    H.frustum("spine", "coat", (0, WAIST - 0.05, 0), (0, SH_Y, 0), (0.5, 0.36), (0.62, 0.4), sides=8)
    H.frustum("spine", "coat", (0, SH_Y, 0), (0, 2.0, 0), (0.62, 0.4), (0.3, 0.26), sides=8)
    H.frustum("spine", "mask", (0, 1.56, 0.34), (0, 1.56, 0.52), (0.21, 0.19), (0.16, 0.13), sides=6)
    H.frustum("spine", "mask", (0, 1.4, 0.42), (0, 1.36, 0.58), (0.1, 0.09), (0.09, 0.09), sides=6)
    for s in (-1, 1):
        H.frustum("spine", "lens", (s * 0.07, 1.62, 0.48), (s * 0.07, 1.62, 0.53), (0.065, 0.065), (0.065, 0.065), sides=6)
    H.frustum("spine", "mask", (0.2, 1.4, 0.4), (0.28, 1.42, 0.46), (0.07, 0.07), (0.1, 0.1), sides=6)
    H.frustum("pelvis", "belt", (0, WAIST - 0.1, 0), (0, WAIST + 0.06, 0), (0.54, 0.4), (0.54, 0.4), sides=8)
    H.box("pelvis", "steel_dk", (0, WAIST - 0.02, 0.4), (0.2, 0.14, 0.05))
    skirt = H.frustum("pelvis", "coat", (0, 0.46, 0), (0, WAIST - 0.08, 0), (0.62, 0.44), (0.52, 0.38), sides=8)
    H.soft(skirt, hem)
    H.frustum("pelvis", "coat_dk", (0, 0.7, 0), (0, 1.0, 0), (0.44, 0.34), (0.46, 0.36), sides=8)


def gear():
    H.frustum("pelvis", "khaki", (0.5, 0.92, 0.2), (0.5, 1.38, 0.2), (0.1, 0.2), (0.14, 0.24), sides=4)   # bolsa
    H.frustum("pelvis", "khaki_dk", (0.5, 1.3, 0.2), (0.5, 1.42, 0.2), (0.15, 0.25), (0.15, 0.25), sides=4)
    H.frustum("pelvis", "khaki", (-0.55, 0.88, 0.0), (-0.55, 1.3, 0.0), (0.07, 0.18), (0.09, 0.2), sides=4)
    H.frustum("pelvis", "lantern", (-0.5, 0.86, 0.3), (-0.5, 1.2, 0.3), (0.12, 0.12), (0.14, 0.14), sides=4)  # lanterna
    H.frustum("pelvis", "glow", (-0.5, 0.92, 0.3), (-0.5, 1.12, 0.3), (0.13, 0.13), (0.13, 0.13), sides=4)


def leg(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "coat_dk", (x, KNEE - 0.02, 0), (x, HIP + 0.05, 0), (0.2, 0.22), (0.25, 0.26), sides=6)
    H.frustum(f"shin.{side}", "puttee", (x, ANKLE, 0), (x, KNEE + 0.04, 0), (0.17, 0.18), (0.24, 0.24), sides=6)
    for y in (0.26, 0.36):
        H.frustum(f"shin.{side}", "puttee_dk", (x, y, 0), (x, y + 0.05, 0), (0.2, 0.2), (0.2, 0.2), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.04, -0.03), (x, ANKLE + 0.06, -0.03), (0.2, 0.22), (0.19, 0.2), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.1, 0.05), (x, 0.08, 0.42), (0.21, 0.13), (0.18, 0.08), sides=4)


def arm_left():
    H.frustum("arm.L", "coat", (SH_X + 0.03, SH_Y + 0.05, 0), (EL_X, EL_Y, 0.02), (0.24, 0.24), (0.2, 0.2), sides=6)
    H.frustum("arm.L", "blue", (SH_X + 0.08, SH_Y - 0.25, 0), (EL_X - 0.02, EL_Y + 0.2, 0.01), (0.26, 0.26), (0.24, 0.24), sides=6)
    H.frustum("forearm.L", "coat_dk", (EL_X, EL_Y + 0.05, 0.02), (EL_X - 0.02, WR_Y + 0.02, 0.08), (0.21, 0.21), (0.2, 0.2), sides=6)
    H.frustum("forearm.L", "skin", (EL_X - 0.02, WR_Y + 0.04, 0.08), (EL_X - 0.02, WR_Y - 0.22, 0.12), (0.17, 0.17), (0.15, 0.15), sides=6)


def arm_right():
    H.frustum("arm.R", "coat", (-SH_X - 0.03, SH_Y + 0.05, 0), (-0.74, EL_Y, 0.05), (0.24, 0.24), (0.2, 0.2), sides=6)
    H.frustum("forearm.R", "coat_dk", (-0.74, EL_Y + 0.05, 0.05), (HAND[0] - 0.02, HAND[1] - 0.15, HAND[2] - 0.12), (0.21, 0.21), (0.19, 0.19), sides=6)
    H.frustum("forearm.R", "skin", (HAND[0] - 0.02, HAND[1] - 0.17, HAND[2] - 0.12), (HAND[0], HAND[1] + 0.04, HAND[2]), (0.17, 0.17), (0.16, 0.16), sides=6)


def shovel():
    d = (BLADE_TIP - BUTT).normalized()
    at = lambda t: tuple(BUTT + (BLADE_TIP - BUTT) * t)       # noqa: E731
    H.frustum("forearm.R", "wood", at(0.0), at(0.38), (0.065, 0.065), (0.065, 0.065), sides=6)       # cabo
    H.frustum("forearm.R", "wood", at(0.38), at(0.72), (0.065, 0.065), (0.065, 0.065), sides=6)
    H.frustum("forearm.R", "steel_dk", at(-0.03), at(0.06), (0.09, 0.07), (0.07, 0.07), sides=4)  # punho em T
    H.frustum("forearm.R", "steel_dk", at(0.64), at(0.72), (0.12, 0.08), (0.12, 0.08), sides=4)
    H.frustum("forearm.R", "steel", at(0.7), at(0.92), (0.2, 0.03), (0.36, 0.035), sides=4)     # lâmina
    H.frustum("forearm.R", "steel", at(0.92), at(1.06), (0.36, 0.035), (0.04, 0.015), sides=4)
    return d


def make():
    head()
    torso()
    gear()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    arm_left()
    arm_right()
    shovel()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        ex = EL_X if s > 0 else 0.74
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * ex, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * ex, EL_Y, 0), (s * ex, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("builder_human", "biped", PALETTE, make, joints())
