"""Orc Peon Builder (builder_orc): hulking orc, axe over the right shoulder, glowing bucket on the left hip,
measured on artifacts/model-sheets/refs/builder_orc/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/builder_orc.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "skin": 0x211E1F, "skin_lt": 0x2F2928, "leather": 0x7A3E26, "leather_lt": 0x9A5B3C, "cloth": 0x6B4630,
    "eye": 0xFF5A1E, "tusk": 0xE8D2A0, "wood": 0x5A3520, "iron": 0x6E5E5C, "iron_dk": 0x4F4243,
    "bucket": 0x7F5238, "glow": 0xFF7A1A,
}

HIP, KNEE, ANKLE, LEG_X = 0.98, 0.5, 0.16, 0.28
WAIST, NECK, TOP = 1.32, 2.05, 2.72
SH_X, SH_Y = 0.55, 2.0
SKIRT_MID = 0.95


def hem(p):
    if p[1] > SKIRT_MID:
        return {"pelvis": 1.0}
    return {"pelvis": 0.45, "thigh.L" if p[0] > 0 else "thigh.R": 0.55}


def head():
    H.frustum("head", "skin", (0, 2.05, 0.06), (0, 2.2, 0.1), (0.2, 0.2), (0.26, 0.26), sides=6)
    H.frustum("head", "skin", (0, 2.18, 0.1), (0, 2.46, 0.12), (0.26, 0.26), (0.23, 0.24), sides=6)
    H.frustum("head", "skin", (0, 2.1, 0.28), (0, 2.22, 0.34), (0.2, 0.08), (0.17, 0.1), sides=6)    # heavy jaw
    H.frustum("head", "leather", (0, 2.38, 0.08), (0, 2.6, 0.06), (0.27, 0.28), (0.18, 0.2), sides=8)  # stitched cap
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.1, 2.34, 0.34), (0.08, 0.04, 0.03))
        H.chain("head", "tusk", [(s * 0.12, 2.12, 0.36), (s * 0.15, 2.28, 0.42)], [(0.04, 0.04), (0.012, 0.012)], sides=4)
        H.frustum("head", "skin", (s * 0.24, 2.3, 0.08), (s * 0.34, 2.42, 0.06), (0.04, 0.07), (0.015, 0.03), sides=4)


def torso():
    H.frustum("spine", "skin", (0, 2.0, 0.02), (0, NECK + 0.1, 0.05), (0.3, 0.3), (0.2, 0.2), sides=8)
    H.frustum("spine", "skin", (0, WAIST - 0.05, 0), (0, 1.75, 0.02), (0.46, 0.36), (0.58, 0.4), sides=8)
    H.frustum("spine", "skin_lt", (0, 1.75, 0.02), (0, 2.02, 0.03), (0.58, 0.4), (0.5, 0.34), sides=8)
    H.frustum("pelvis", "leather", (0, WAIST - 0.15, 0), (0, WAIST + 0.05, 0), (0.5, 0.4), (0.5, 0.4), sides=8)
    H.frustum("pelvis", "skin", (0, 0.86, 0), (0, 1.15, 0), (0.42, 0.34), (0.46, 0.36), sides=8)
    cloth = H.frustum("pelvis", "cloth", (0, 0.66, 0), (0, WAIST - 0.12, 0), (0.46, 0.4), (0.5, 0.42), sides=8)
    H.soft(cloth, hem)
    # bucket on the left hip, hot contents
    H.frustum("pelvis", "bucket", (0.5, 0.64, 0.12), (0.5, 0.92, 0.12), (0.17, 0.17), (0.22, 0.22), sides=8)
    H.frustum("pelvis", "glow", (0.5, 0.92, 0.12), (0.5, 0.95, 0.12), (0.2, 0.2), (0.2, 0.2), sides=8)
    H.chain("pelvis", "iron_dk", [(0.32, 0.92, 0.12), (0.4, 1.12, 0.12), (0.5, 1.18, 0.12), (0.6, 1.12, 0.12), (0.68, 0.92, 0.12)],
            [(0.02, 0.02)] * 5, sides=4)


def leg(s, side):
    kx = s * 0.3
    H.frustum(f"thigh.{side}", "skin", (kx, KNEE - 0.02, 0.03), (s * 0.26, HIP + 0.05, 0), (0.25, 0.28), (0.32, 0.32), sides=6)
    H.frustum(f"thigh.{side}", "skin_lt", (kx, KNEE + 0.1, 0.03), (s * 0.28, KNEE + 0.36, 0.02), (0.27, 0.29), (0.3, 0.31), sides=6)
    H.frustum(f"shin.{side}", "skin", (kx, ANKLE - 0.02, -0.02), (kx, KNEE + 0.02, 0.03), (0.19, 0.22), (0.26, 0.27), sides=6)
    H.frustum(f"shin.{side}", "skin_lt", (kx, 0.2, -0.02), (kx, 0.34, 0), (0.22, 0.24), (0.26, 0.27), sides=6)
    H.frustum(f"foot.{side}", "skin", (kx, 0.03, -0.1), (kx, ANKLE + 0.04, -0.02), (0.22, 0.28), (0.2, 0.22), sides=6)
    H.frustum(f"foot.{side}", "skin", (kx, 0.12, 0.05), (kx, 0.08, 0.5), (0.24, 0.2), (0.22, 0.1), sides=4)


def left_arm():
    H.frustum("arm.L", "skin", (SH_X, SH_Y, 0), (0.74, 1.62, 0), (0.28, 0.3), (0.3, 0.3), sides=6)
    H.frustum("arm.L", "skin_lt", (0.74, 1.62, 0), (0.75, 1.32, 0), (0.3, 0.3), (0.28, 0.28), sides=6)
    H.frustum("arm.L", "leather_lt", (SH_X - 0.04, SH_Y + 0.14, 0), (0.74, SH_Y - 0.2, 0), (0.28, 0.33), (0.32, 0.34), sides=6)
    H.frustum("arm.L", "leather", (SH_X - 0.1, SH_Y + 0.17, 0), (0.7, SH_Y - 0.05, 0), (0.12, 0.16), (0.26, 0.32), sides=6)
    H.frustum("forearm.L", "leather", (0.75, 1.34, 0), (0.75, 0.98, 0.03), (0.35, 0.35), (0.31, 0.31), sides=6)
    H.frustum("forearm.L", "leather_lt", (0.75, 1.24, 0), (0.75, 1.14, 0), (0.37, 0.37), (0.37, 0.37), sides=6)
    H.frustum("forearm.L", "skin", (0.75, 1.0, 0.03), (0.75, 0.84, 0.05), (0.25, 0.26), (0.32, 0.3), sides=6)
    H.frustum("forearm.L", "skin", (0.75, 0.86, 0.05), (0.75, 0.62, 0.08), (0.34, 0.31), (0.28, 0.27), sides=6)


def right_arm():
    H.frustum("arm.R", "skin", (-SH_X, SH_Y, 0), (-0.9, 1.45, 0.1), (0.28, 0.3), (0.32, 0.32), sides=6)
    H.frustum("arm.R", "leather_lt", (-SH_X + 0.04, SH_Y + 0.14, 0), (-0.74, SH_Y - 0.2, 0), (0.28, 0.33), (0.32, 0.34), sides=6)
    H.frustum("arm.R", "leather", (-SH_X + 0.1, SH_Y + 0.17, 0), (-0.7, SH_Y - 0.05, 0), (0.12, 0.16), (0.26, 0.32), sides=6)
    H.frustum("forearm.R", "leather", (-0.9, 1.42, 0.1), (-0.9, 1.78, 0.5), (0.34, 0.33), (0.3, 0.3), sides=6)
    H.frustum("forearm.R", "leather_lt", (-0.9, 1.5, 0.2), (-0.9, 1.62, 0.34), (0.36, 0.36), (0.36, 0.36), sides=6)
    H.frustum("forearm.R", "skin", (-0.9, 1.76, 0.48), (-0.89, 2.18, 0.8), (0.24, 0.26), (0.28, 0.26), sides=6)
    # axe: shaft from the front across the right shoulder to the blade behind the left
    butt, end = (-1.22, 1.84, 1.0), (0.75, 2.78, -0.7)
    H.frustum("forearm.R", "wood", butt, end, (0.06, 0.06), (0.06, 0.06), sides=6)
    H.box("forearm.R", "iron_dk", (0.55, 2.7, -0.55), (0.22, 0.3, 0.2))
    H.frustum("forearm.R", "iron", (0.35, 2.55, -0.58), (0.4, 3.02, -0.52), (0.16, 0.06), (0.36, 0.08), sides=4)
    H.frustum("forearm.R", "iron", (0.35, 2.55, -0.58), (0.2, 2.5, -0.62), (0.16, 0.05), (0.1, 0.04), sides=4)
    H.box("forearm.R", "leather", (0.66, 2.3, -0.58), (0.3, 0.5, 0.04))
    H.box("forearm.R", "iron_dk", (-1.1, 1.8, 0.95), (0.2, 0.2, 0.2))


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    left_arm()
    right_arm()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        ex = 0.75 if s > 0 else 0.9
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * ex, 1.4, 0))
        out[f"forearm.{side}"] = ((s * ex, 1.4, 0), (s * ex, 0.9, 0))
        out[f"thigh.{side}"] = ((s * 0.26, HIP, 0), (s * 0.3, KNEE, 0))
        out[f"shin.{side}"] = ((s * 0.3, KNEE, 0), (s * 0.3, ANKLE, 0))
        out[f"foot.{side}"] = ((s * 0.3, ANKLE, 0), (s * 0.3, 0.06, 0.5))
    return out


H.build("builder_orc", "biped", PALETTE, make, joints())
