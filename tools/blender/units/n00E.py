"""Flesh Golem (n00E): measured on artifacts/model-sheets/refs/n00E/sheet.jpg.
Fist on the unit's right arm (-x), hook on the left arm (+x), horned helm, dark pauldrons.

    blender -b --factory-startup -P tools/blender/units/n00E.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "skin": 0xD48F7C, "skin_dk": 0xA06272, "face": 0x5A3F45, "armor": 0x30262F, "gold": 0xE0A83A,
    "gauntlet": 0x8A8D92, "gauntlet_dk": 0x5F6166, "blue": 0x2B3A6E, "cloth": 0x1E1A22, "foot": 0x9A8F98,
    "horn": 0x9EA0A8, "helm": 0x2A2229, "eye": 0xFF2A2A, "tooth": 0xEEE8D8, "hook": 0x4A4D52, "blood": 0x7A1E22,
}

LEG_X, KNEE_X, FOOT_X, HIP, KNEE, ANKLE = 0.3, 0.34, 0.38, 1.08, 0.6, 0.2
WAIST, NECK, TOP = 1.2, 2.05, 2.6
SH_X, SH_Y, EL_X, EL_Y, WR_X, WR_Y = 0.62, 2.0, 0.8, 1.62, 0.86, 0.98


def band(bone, y, r, h=0.07, x=0.0, tone="gold"):
    H.frustum(bone, tone, (x, y, 0), (x, y + h, 0), (r, r), (r, r), sides=8)


def head():
    H.frustum("head", "face", (0, 2.0, 0.08), (0, 2.34, 0.1), (0.21, 0.22), (0.23, 0.22), sides=8)
    H.frustum("head", "helm", (0, 2.2, 0), (0, 2.38, 0), (0.27, 0.27), (0.27, 0.27), sides=8)
    H.frustum("head", "helm", (0, 2.38, 0), (0, 2.58, 0), (0.27, 0.27), (0.14, 0.14), sides=8)
    H.box("head", "horn", (0, 2.4, 0.26), (0.06, 0.3, 0.05))
    H.box("head", "cloth", (0, 2.13, 0.3), (0.22, 0.12, 0.04))
    H.box("head", "tooth", (0, 2.17, 0.32), (0.2, 0.04, 0.03))
    H.box("head", "tooth", (0, 2.08, 0.32), (0.16, 0.04, 0.03))
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.1, 2.3, 0.31), (0.1, 0.05, 0.03))
        H.chain("head", "horn", [(s * 0.24, 2.38, 0), (s * 0.4, 2.44, 0), (s * 0.46, 2.62, 0), (s * 0.36, 2.8, 0)],
                [(0.1, 0.1), (0.09, 0.09), (0.07, 0.07), (0.012, 0.012)], sides=6)


def torso():
    H.frustum("spine", "skin", (0, 1.9, 0), (0, 2.12, 0), (0.3, 0.26), (0.24, 0.22), sides=8)
    H.frustum("spine", "skin", (0, WAIST - 0.02, 0), (0, 1.55, 0), (0.4, 0.42), (0.5, 0.5), sides=8)
    H.frustum("spine", "skin", (0, 1.55, 0), (0, 2.0, 0), (0.5, 0.5), (0.58, 0.52), sides=8)
    H.frustum("spine", "skin_dk", (0.18, 1.5, 0.3), (0.2, 1.85, 0.34), (0.17, 0.05), (0.14, 0.05), sides=4)
    H.frustum("pelvis", "skin", (0, 0.86, 0), (0, WAIST, 0), (0.42, 0.42), (0.44, 0.44), sides=8)
    H.frustum("pelvis", "gold", (0, WAIST - 0.1, 0), (0, WAIST + 0.06, 0), (0.46, 0.46), (0.46, 0.46), sides=8)
    H.box("pelvis", "gold", (0, WAIST - 0.02, 0.37), (0.26, 0.17, 0.05))
    H.frustum("pelvis", "cloth", (0, 1.08, 0.34), (0, 0.76, 0.34), (0.2, 0.04), (0.05, 0.04), sides=4)


def leg(s, side):
    H.chain(f"thigh.{side}", "skin", [(s * LEG_X, HIP + 0.05, 0), (s * 0.32, 0.85, 0), (s * KNEE_X, KNEE + 0.03, 0)],
            [(0.27, 0.34), (0.26, 0.32), (0.25, 0.3)])
    H.frustum(f"shin.{side}", "skin", (s * KNEE_X, ANKLE, 0), (s * KNEE_X, KNEE + 0.02, 0), (0.23, 0.28), (0.27, 0.3), sides=6)
    H.frustum(f"shin.{side}", "blue", (s * KNEE_X, 0.3, 0), (s * KNEE_X, 0.58, 0), (0.29, 0.29), (0.3, 0.3), sides=8)
    band(f"shin.{side}", 0.27, 0.31, 0.05, s * KNEE_X)
    band(f"shin.{side}", 0.57, 0.31, 0.05, s * KNEE_X)
    H.frustum(f"foot.{side}", "foot", (s * FOOT_X, 0.1, -0.12), (s * FOOT_X, 0.1, 0.38), (0.28, 0.14), (0.24, 0.1), sides=8)
    H.frustum(f"foot.{side}", "skin", (s * FOOT_X, 0.02, -0.14), (s * FOOT_X, 0.03, 0.42), (0.28, 0.04), (0.25, 0.04), sides=8)


def pauldron(s, side):
    b = f"arm.{side}"
    H.frustum(b, "gold", (s * 0.66, 1.84, 0), (s * 0.66, 1.93, 0), (0.42, 0.4), (0.42, 0.4), sides=8)
    H.frustum(b, "armor", (s * 0.66, 1.93, 0), (s * 0.62, 2.22, 0), (0.41, 0.39), (0.35, 0.33), sides=8)
    H.frustum(b, "armor", (s * 0.62, 2.22, 0), (s * 0.5, 2.42, 0), (0.35, 0.33), (0.16, 0.15), sides=8)


def arm(s, side):
    H.chain(f"arm.{side}", "skin", [(s * SH_X, SH_Y, 0), (s * 0.74, 1.82, 0), (s * EL_X, EL_Y, 0)],
            [(0.3, 0.3), (0.29, 0.29), (0.27, 0.27)])
    pauldron(s, side)
    b, x = f"forearm.{side}", s * WR_X
    H.frustum(b, "gauntlet", (x, EL_Y + 0.04, 0), (x, 1.2, 0), (0.29, 0.3), (0.3, 0.3), sides=8)
    H.frustum(b, "gauntlet", (x, 1.2, 0), (x, WR_Y + 0.04, 0), (0.3, 0.3), (0.27, 0.27), sides=8)
    band(b, 1.52, 0.32, 0.09, x)
    band(b, 1.06, 0.31, 0.09, x)


def fist(s, side):
    b, x = f"forearm.{side}", s * WR_X
    H.frustum(b, "gauntlet_dk", (x, 1.0, 0.0), (x, 0.78, 0.03), (0.27, 0.27), (0.31, 0.3), sides=6)
    H.frustum(b, "gauntlet", (x, 0.8, 0.03), (x, 0.56, 0.07), (0.31, 0.3), (0.26, 0.27), sides=6)
    H.box(b, "gauntlet_dk", (x, 0.66, 0.26), (0.34, 0.22, 0.14))


def hook(s, side):
    b, x = f"forearm.{side}", s * WR_X
    H.frustum(b, "cloth", (x, 1.0, 0), (x, 0.78, 0.01), (0.2, 0.2), (0.17, 0.17), sides=6)
    pts = [(x - 0.03, 0.82, 0.02), (x - 0.02, 0.52, 0.06), (x + 0.03, 0.34, 0.24), (x + 0.04, 0.24, 0.5), (x + 0.0, 0.4, 0.74)]
    H.chain(b, "hook", pts, [(0.11, 0.11), (0.1, 0.1), (0.1, 0.1), (0.085, 0.085), (0.02, 0.02)])
    H.frustum(b, "blood", (x, 0.36, 0.68), (x, 0.48, 0.82), (0.05, 0.05), (0.01, 0.01), sides=4)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        arm(s, side)
    fist(-1, "R")
    hook(1, "L")


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * WR_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * KNEE_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * KNEE_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * KNEE_X, ANKLE, 0), (s * FOOT_X, 0.08, 0.5))
    return out


H.build("n00E", "biped", PALETTE, make, joints())
