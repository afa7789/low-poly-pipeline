"""Naga Tribal Builder (builder_naga): murloc de capacete de mergulhador com croque (gancho de barco).

    blender -b --factory-startup -P tools/blender/units/builder_naga.py -- <out.glb>

Corpo curvado, sem perna visivel: as pernas sao de calca preta e pes de nadadeira, todas nos ossos do biped.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "coat": 0x1E2527, "coat_dk": 0x14191B, "skin": 0x4F7F80, "skin_dk": 0x3B6667, "brass": 0x9A7A3A, "brass_dk": 0x75602F,
    "verdigris": 0x4E7A66, "glass": 0x4FE0D8, "rope": 0xA88C58, "rope_dk": 0x7E6842, "wood": 0x6B5638,
    "steel": 0x8A8E92, "black": 0x101214,
}
HIP, KNEE, ANKLE, WAIST, NECK, TOP = 1.05, 0.55, 0.14, 1.4, 2.1, 2.72
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.72, 2.0, 0.8, 1.45, 1.05
LEG_X = 0.3
POLE_X = -0.66


def head():
    H.frustum("head", "skin", (0, 2.12, 0.1), (0, 2.42, 0.16), (0.3, 0.3), (0.32, 0.3), sides=8)         # focinho
    H.frustum("head", "skin_dk", (0, 2.2, 0.38), (0, 2.28, 0.42), (0.17, 0.05), (0.15, 0.04), sides=6)    # boca
    for s in (-1, 1):
        H.frustum("head", "glass", (s * 0.19, 2.4, 0.38), (s * 0.19, 2.4, 0.46), (0.07, 0.07), (0.06, 0.06), sides=6)
        H.frustum("head", "brass", (s * 0.46, 2.52, 0.14), (s * 0.54, 2.52, 0.14), (0.15, 0.1), (0.12, 0.08), sides=6)
    H.frustum("head", "brass", (0, 2.3, 0.08), (0, 2.5, 0.08), (0.5, 0.48), (0.5, 0.47), sides=8)        # cuba do capacete
    H.frustum("head", "verdigris", (0, 2.5, 0.08), (0, 2.66, 0.08), (0.5, 0.47), (0.33, 0.31), sides=8)
    H.frustum("head", "brass_dk", (0, 2.66, 0.08), (0, 2.74, 0.08), (0.3, 0.28), (0.24, 0.22), sides=8)
    H.frustum("head", "brass_dk", (0, 2.45, 0.5), (0, 2.45, 0.62), (0.2, 0.2), (0.18, 0.18), sides=8)      # aro da janela
    H.frustum("head", "glass", (0, 2.45, 0.6), (0, 2.45, 0.68), (0.13, 0.13), (0.12, 0.12), sides=8)
    H.frustum("spine", "brass", (0, 2.0, 0.1), (0, 2.2, 0.1), (0.4, 0.36), (0.44, 0.4), sides=8)           # gola


def torso():
    H.frustum("spine", "coat", (0, WAIST - 0.05, -0.05), (0, 1.9, -0.05), (0.5, 0.45), (0.68, 0.65), sides=8)
    H.frustum("spine", "coat", (0, 1.9, -0.05), (0, 2.12, 0.05), (0.68, 0.65), (0.42, 0.4), sides=8)
    H.frustum("spine", "coat_dk", (0, 1.5, -0.45), (0, 2.1, -0.4), (0.5, 0.3), (0.58, 0.32), sides=8)       # corcova
    H.frustum("pelvis", "coat", (0, 0.85, 0), (0, WAIST, 0), (0.46, 0.38), (0.5, 0.4), sides=8)
    # corda enrolada no ombro, em diagonal
    H.chain("spine", "rope", [(0.55, 2.18, 0.1), (0.2, 2.2, 0.38), (-0.3, 1.8, 0.5), (-0.6, 1.5, 0.3)],
            [(0.18, 0.18), (0.17, 0.17), (0.17, 0.17), (0.15, 0.15)], sides=6)
    H.chain("spine", "rope_dk", [(0.6, 2.05, 0.0), (0.55, 2.08, -0.4), (-0.1, 2.0, -0.55), (-0.6, 1.7, -0.3)],
            [(0.17, 0.17), (0.18, 0.18), (0.18, 0.18), (0.15, 0.15)], sides=6)


def leg(s, side):
    kx = s * LEG_X
    H.frustum(f"thigh.{side}", "coat_dk", (kx, KNEE - 0.04, 0.05), (kx, HIP + 0.05, 0), (0.25, 0.26), (0.3, 0.3), sides=6)
    H.frustum(f"shin.{side}", "coat_dk", (kx, ANKLE + 0.15, 0.05), (kx, KNEE + 0.04, 0.05), (0.2, 0.2), (0.25, 0.26), sides=6)
    H.frustum(f"shin.{side}", "skin", (kx, ANKLE - 0.02, 0.05), (kx, ANKLE + 0.2, 0.05), (0.14, 0.14), (0.17, 0.17), sides=6)
    H.frustum(f"foot.{side}", "skin", (kx, 0.07, 0.0), (kx, 0.07, 0.35), (0.2, 0.08), (0.28, 0.05), sides=6)
    for dx in (-0.2, 0, 0.2):      # nadadeira: dedos abertos
        H.frustum(f"foot.{side}", "skin_dk", (kx, 0.05, 0.3), (kx + dx, 0.04, 0.68), (0.06, 0.03), (0.07, 0.02), sides=4)


def arm_free():
    H.frustum("arm.L", "coat", (SH_X, SH_Y + 0.08, 0), (EL_X + 0.05, EL_Y - 0.05, 0), (0.28, 0.27), (0.22, 0.22), sides=6)
    H.frustum("arm.L", "coat", (SH_X, SH_Y + 0.12, 0), (SH_X + 0.02, 1.85, 0), (0.34, 0.3), (0.27, 0.26), sides=6)
    H.frustum("forearm.L", "coat", (EL_X, EL_Y + 0.03, 0), (EL_X, 1.1, 0), (0.22, 0.22), (0.26, 0.26), sides=6)
    H.frustum("forearm.L", "skin", (EL_X, 1.12, 0), (EL_X, 0.82, 0.02), (0.15, 0.17), (0.14, 0.15), sides=6)
    H.frustum("forearm.L", "skin_dk", (EL_X + 0.05, 1.2, -0.1), (EL_X + 0.2, 0.96, -0.2), (0.02, 0.09), (0.02, 0.06), sides=4)  # barbatana


def arm_pole():
    H.frustum("arm.R", "coat", (-SH_X, SH_Y + 0.12, 0), (-EL_X - 0.02, 1.85, 0), (0.34, 0.3), (0.27, 0.26), sides=6)
    H.frustum("arm.R", "coat", (-SH_X, 1.95, 0), (-EL_X, EL_Y - 0.05, 0.15), (0.28, 0.27), (0.22, 0.22), sides=6)
    H.frustum("forearm.R", "coat", (-EL_X, EL_Y + 0.03, 0.15), (-0.7, 1.15, 0.45), (0.22, 0.22), (0.27, 0.26), sides=6)
    H.frustum("forearm.R", "skin", (-0.7, 1.2, 0.45), (POLE_X, 1.0, 0.6), (0.2, 0.2), (0.21, 0.2), sides=6)    # punho grande
    # croque: haste com valvula de latao e gancho no alto, o pe da haste no chao
    base, mid, top = (POLE_X, 0.0, 0.5), (POLE_X, 1.7, 0.62), (POLE_X, 2.62, 0.7)
    H.frustum("forearm.R", "wood", base, mid, (0.065, 0.065), (0.07, 0.07), sides=6)
    H.frustum("forearm.R", "steel", mid, top, (0.07, 0.07), (0.06, 0.06), sides=6)
    H.frustum("forearm.R", "brass", (POLE_X, 1.3, 0.6), (POLE_X, 1.55, 0.61), (0.15, 0.15), (0.15, 0.15), sides=8)
    H.chain("forearm.R", "steel", [top, (POLE_X - 0.05, 2.78, 0.7), (POLE_X - 0.3, 2.95, 0.7), (POLE_X - 0.5, 2.78, 0.7),
                                   (POLE_X - 0.5, 2.55, 0.7)],
            [(0.06, 0.06), (0.07, 0.07), (0.06, 0.06), (0.05, 0.05), (0.01, 0.01)], sides=6)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    arm_free()
    arm_pole()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0.08)),
           "head": ((0, NECK, 0.08), (0, TOP, 0.08)),
           "arm.L": ((SH_X, SH_Y, 0), (SH_X + 0.05, EL_Y, 0)), "forearm.L": ((EL_X, EL_Y, 0), (EL_X, WR_Y, 0)),
           "arm.R": ((-SH_X, SH_Y, 0), (-EL_X, EL_Y, 0.15)), "forearm.R": ((-EL_X, EL_Y, 0.15), (-0.7, WR_Y, 0.45))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("builder_naga", "biped", PALETTE, make, joints())
