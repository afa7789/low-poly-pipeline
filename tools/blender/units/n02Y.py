"""Ogre Lord (n02Y): medido em artifacts/model-sheets/refs/n02Y/sheet.jpg. Duas cabeças de capuz, marreta na mão direita,
escudo redondo no braço esquerdo.

    blender -b --factory-startup -P tools/blender/units/n02Y.py -- <out.glb>
"""
import pathlib
import sys

from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "skin": 0xD98F55, "olive": 0x5A5E3A, "grey": 0x7C7D80, "grey_dk": 0x5E5F63, "black": 0x1E1B1C, "gold": 0xC9A23A,
    "cream": 0xE8DEB8, "pants": 0x74583F, "belt": 0x5E4332, "boot": 0x1A1816, "mud": 0x4A3426, "wood": 0x5A3A26,
    "orange": 0xF0852A, "shield": 0x6B4A38, "eye": 0xFFB03C,
}

HIP, KNEE, ANKLE, LEG_X = 1.15, 0.56, 0.14, 0.34
WAIST, NECK, TOP = 1.45, 2.2, 2.75
SH_Y, ARM_X, EL_Y, WR_Y = 2.05, 0.86, 1.4, 0.92


def make_heads():
    for s in (-1, 1):
        x = s * 0.31
        H.frustum("head", "black", (x, 2.2, 0.03), (x, 2.55, 0.03), (0.21, 0.22), (0.22, 0.23), sides=6)
        H.frustum("head", "cream", (x, 2.3, -0.03), (x, 2.55, -0.03), (0.3, 0.3), (0.28, 0.28), sides=8)     # capuz
        H.frustum("head", "cream", (x, 2.55, -0.03), (x, 2.8, -0.05), (0.28, 0.28), (0.15, 0.15), sides=8)
        H.frustum("head", "grey", (x, 2.3, 0.2), (x, 2.5, 0.2), (0.17, 0.12), (0.19, 0.1), sides=4)           # máscara
        H.frustum("head", "grey_dk", (x, 2.2, 0.3), (x, 2.34, 0.34), (0.1, 0.1), (0.12, 0.12), sides=4)       # respirador
        H.box("head", "eye", (x, 2.45, 0.3), (0.2, 0.04, 0.03))
    H.frustum("head", "grey", (0, 2.18, 0), (0, 2.34, 0), (0.62, 0.5), (0.5, 0.42), sides=8)               # gola


def make_torso():
    H.frustum("pelvis", "pants", (0, 0.95, 0), (0, 1.3, 0), (0.55, 0.5), (0.58, 0.56), sides=8)
    H.frustum("pelvis", "belt", (0, 1.05, 0), (0, 1.3, 0), (0.6, 0.58), (0.6, 0.6), sides=8)
    H.frustum("pelvis", "grey", (0, 1.0, 0.5), (0, 1.5, 0.5), (0.42, 0.2), (0.34, 0.14), sides=6)         # barriga blindada
    H.frustum("spine", "olive", (0, 1.3, 0), (0, 1.75, 0), (0.58, 0.52), (0.64, 0.45), sides=8)
    H.frustum("spine", "olive", (0, 1.75, 0), (0, 2.2, 0), (0.64, 0.45), (0.5, 0.36), sides=8)
    H.frustum("spine", "grey", (0, 1.75, 0.4), (0, 2.15, 0.36), (0.38, 0.08), (0.34, 0.06), sides=6)       # peitoral
    H.box("spine", "cream", (-0.1, 1.95, 0.45), (0.1, 0.1, 0.03))
    H.box("spine", "orange", (0.14, 1.95, 0.45), (0.05, 0.16, 0.03))
    H.frustum("spine", "grey", (0, 1.65, -0.38), (0, 2.1, -0.38), (0.4, 0.08), (0.36, 0.06), sides=6)      # placa das costas


def make_arms():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * ARM_X
        H.frustum(f"arm.{side}", "skin", (x, EL_Y - 0.05, 0), (x, SH_Y + 0.05, 0), (0.24, 0.25), (0.3, 0.3), sides=8)
        H.frustum(f"arm.{side}", "black", (x, 2.28, 0), (x, 2.1, 0), (0.2, 0.26), (0.34, 0.36), sides=8)      # ombreira
        H.frustum(f"arm.{side}", "black", (x, 2.1, 0), (x, 1.8, 0), (0.34, 0.36), (0.36, 0.38), sides=8)
        H.frustum(f"arm.{side}", "gold", (x, 1.84, 0), (x, 1.76, 0), (0.36, 0.38), (0.37, 0.39), sides=8)
        H.box(f"arm.{side}", "cream", (x, 2.0, 0.3), (0.3, 0.3, 0.03))
        H.frustum(f"forearm.{side}", "skin", (x, EL_Y + 0.05, 0), (x, 1.25, 0.02), (0.25, 0.25), (0.27, 0.27), sides=8)
        H.frustum(f"forearm.{side}", "grey", (x, 1.3, 0.02), (x, 0.95, 0.04), (0.28, 0.28), (0.25, 0.25), sides=8)  # braçadeira
        H.frustum(f"forearm.{side}", "gold", (x, 1.32, 0.02), (x, 1.26, 0.02), (0.29, 0.29), (0.29, 0.29), sides=8)
        H.frustum(f"forearm.{side}", "skin", (x, 1.0, 0.04), (x, 0.7, 0.06), (0.24, 0.26), (0.2, 0.22), sides=8)   # punho
        H.frustum(f"forearm.{side}", "skin", (x, 0.86, 0.1), (x, 0.66, 0.12), (0.22, 0.24), (0.18, 0.2), sides=6)


def make_legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * LEG_X
        H.frustum(f"thigh.{side}", "pants", (x, KNEE - 0.04, 0), (x, HIP + 0.05, 0), (0.28, 0.3), (0.36, 0.38), sides=8)
        H.frustum(f"thigh.{side}", "grey", (x, KNEE + 0.02, 0.26), (x, KNEE + 0.32, 0.26), (0.22, 0.1), (0.22, 0.1), sides=6)
        H.frustum(f"shin.{side}", "pants", (x, 0.35, 0), (x, KNEE + 0.04, 0), (0.25, 0.26), (0.3, 0.3), sides=8)
        H.frustum(f"shin.{side}", "boot", (x, 0.1, 0), (x, 0.4, 0), (0.24, 0.26), (0.28, 0.3), sides=8)
        H.frustum(f"foot.{side}", "mud", (x, 0.12, -0.05), (x, 0.1, 0.5), (0.27, 0.15), (0.23, 0.09), sides=4)
        H.frustum(f"foot.{side}", "boot", (x, 0.02, -0.2), (x, 0.02, 0.52), (0.28, 0.03), (0.24, 0.03), sides=4)


def make_gear():
    butt, tip = Vector((-ARM_X - 0.04, 0.95, -0.42)), Vector((-ARM_X - 0.04, 0.28, 0.9))
    cut = (0.55, 0.88)
    H.frustum("forearm.R", "wood", butt, butt.lerp(tip, cut[0]), (0.08, 0.08), (0.08, 0.08), sides=6)
    H.frustum("forearm.R", "grey_dk", butt.lerp(tip, cut[0]), butt.lerp(tip, cut[1]), (0.27, 0.27), (0.27, 0.27), sides=4)
    H.frustum("forearm.R", "wood", butt.lerp(tip, cut[1]), tip, (0.06, 0.06), (0.05, 0.05), sides=6)
    H.wheel("forearm.L", "shield", (ARM_X + 0.2, 1.15, 0.05), 0.42, 0.08)
    H.wheel("forearm.L", "grey", (ARM_X + 0.15, 1.15, 0.05), 0.35, 0.07)


def make():
    make_heads()
    make_torso()
    make_arms()
    make_legs()
    make_gear()


def joints():
    out = {"pelvis": ((0, HIP - 0.05, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * ARM_X, SH_Y, 0), (s * ARM_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * ARM_X, EL_Y, 0), (s * ARM_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("n02Y", "biped", PALETTE, make, joints())
