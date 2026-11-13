"""Vampire (h01U): medido em artifacts/model-sheets/refs/h01U/sheet.jpg. Sem arma: as garras das duas mãos são o ataque.

    blender -b --factory-startup -P tools/blender/units/h01U.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "coat": 0x40235F, "coat_dk": 0x2A173F, "gold": 0xC9993C, "black": 0x1D1520, "boot": 0x241922,
    "bone": 0xDDC8B4, "bone_dk": 0xB89E8A, "eye": 0xB6F020, "mouth": 0x5A2418, "sole": 0x120C14,
}

HIP, KNEE, ANKLE, LEG_X = 1.12, 0.56, 0.14, 0.17
WAIST, NECK, TOP = 1.5, 2.25, 2.8
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.27, 2.2, 0.37, 1.8, 1.4
HAND_X = 0.45


def head():
    # capuz preto em bola, olhos verdes em fenda, mandíbula óssea com presas dentro da gola alta
    H.frustum("head", "black", (0, 2.4, 0.02), (0, 2.58, 0.02), (0.15, 0.16), (0.2, 0.2), sides=8)
    H.frustum("head", "black", (0, 2.58, 0.02), (0, 2.72, 0.02), (0.2, 0.2), (0.17, 0.17), sides=8)
    H.frustum("head", "black", (0, 2.72, 0.02), (0, 2.8, 0.02), (0.17, 0.17), (0.08, 0.08), sides=8)
    for s in (-1, 1):
        H.frustum("head", "eye", (s * 0.12, 2.57, 0.2), (s * 0.05, 2.55, 0.22), (0.03, 0.025), (0.03, 0.02), sides=4)
    H.frustum("head", "bone", (0, 2.3, 0.07), (0, 2.46, 0.08), (0.1, 0.11), (0.14, 0.12), sides=6)
    H.box("head", "mouth", (0, 2.38, 0.19), (0.1, 0.07, 0.03))
    for s in (-1, 1):
        H.frustum("head", "bone", (s * 0.045, 2.44, 0.19), (s * 0.045, 2.35, 0.2), (0.016, 0.014), (0.004, 0.004), sides=4)
    H.frustum("head", "coat_dk", (0, 2.2, -0.05), (0, 2.5, -0.05), (0.3, 0.22), (0.29, 0.2), sides=8)    # gola alta
    H.frustum("head", "gold", (0, 2.5, -0.05), (0, 2.54, -0.05), (0.3, 0.21), (0.28, 0.19), sides=8)
    H.frustum("head", "coat", (0, 2.1, 0), (0, 2.26, 0), (0.26, 0.2), (0.3, 0.22), sides=8)


def torso():
    H.frustum("spine", "coat", (0, WAIST - 0.05, 0), (0, SH_Y + 0.02, 0), (0.27, 0.22), (0.35, 0.24), sides=8)
    H.frustum("spine", "coat", (0, SH_Y, 0), (0, 2.34, 0), (0.35, 0.24), (0.2, 0.18), sides=8)
    H.frustum("spine", "gold", (0, 1.52, 0.235), (0, 2.18, 0.235), (0.018, 0.012), (0.018, 0.012), sides=4)
    H.frustum("pelvis", "coat", (0, 0.96, 0), (0, WAIST, 0), (0.3, 0.23), (0.27, 0.22), sides=8)
    H.frustum("pelvis", "gold", (0, 0.52, 0.235), (0, 1.5, 0.235), (0.018, 0.012), (0.018, 0.012), sides=4)


def leg(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "black", (x, KNEE, 0), (x, HIP + 0.04, 0), (0.12, 0.12), (0.15, 0.15), sides=6)
    # aba do casaco: estreita no quadril, abre até a barra dourada perto do joelho
    H.frustum(f"thigh.{side}", "coat", (x, 0.82, 0), (x, HIP + 0.04, 0), (0.18, 0.23), (0.15, 0.21), sides=6)
    H.frustum(f"thigh.{side}", "coat", (x + s * 0.01, 0.5, 0), (x, 0.84, 0), (0.2, 0.25), (0.18, 0.23), sides=6)
    H.frustum(f"thigh.{side}", "gold", (x + s * 0.01, 0.5, 0), (x + s * 0.01, 0.54, 0), (0.205, 0.255), (0.2, 0.25), sides=6)
    H.frustum(f"shin.{side}", "boot", (x, ANKLE - 0.02, 0), (x, 0.38, 0), (0.12, 0.13), (0.13, 0.14), sides=6)
    H.frustum(f"shin.{side}", "boot", (x, 0.38, 0), (x, KNEE + 0.02, 0), (0.13, 0.14), (0.16, 0.16), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.03, -0.02), (x, ANKLE + 0.04, -0.02), (0.14, 0.15), (0.13, 0.14), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.1, 0.05), (x, 0.08, 0.4), (0.14, 0.1), (0.12, 0.06), sides=4)
    H.frustum(f"foot.{side}", "sole", (x, 0.02, -0.15), (x, 0.02, 0.42), (0.15, 0.02), (0.13, 0.02), sides=4)


def claws(s, side):
    """Quatro dedos longos e curvos, em 2 segmentos, abertos para a frente e para trás da palma."""
    hx = s * HAND_X
    for z, dx in ((0.17, 0.03), (0.06, 0.06), (-0.05, 0.05), (-0.15, 0.02)):
        pts = [(hx, 1.34, z), (hx + s * dx, 1.05, z + 0.03), (hx + s * (dx - 0.04), 0.74, z + 0.09)]
        H.chain(f"forearm.{side}", "bone", pts, [(0.06, 0.05), (0.045, 0.04), (0.012, 0.012)], sides=4)


def arm(s, side):
    H.frustum(f"arm.{side}", "coat", (s * SH_X, SH_Y + 0.05, 0), (s * EL_X, EL_Y + 0.02, 0), (0.17, 0.15), (0.13, 0.12), sides=6)
    H.frustum(f"forearm.{side}", "coat", (s * EL_X, EL_Y + 0.04, 0), (s * HAND_X, 1.52, 0), (0.13, 0.12), (0.12, 0.11), sides=6)
    H.frustum(f"forearm.{side}", "black", (s * (HAND_X - 0.01), 1.6, 0), (s * HAND_X, 1.3, 0.01), (0.12, 0.11), (0.14, 0.15), sides=6)   # punho largo
    H.frustum(f"forearm.{side}", "bone_dk", (s * HAND_X, 1.34, 0.01), (s * HAND_X, 1.22, 0.02), (0.14, 0.19), (0.12, 0.19), sides=6)    # palma
    claws(s, side)


def make():
    head()
    torso()
    leg(1, "L")
    leg(-1, "R")
    arm(1, "L")
    arm(-1, "R")


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("h01U", "biped", PALETTE, make, joints())
