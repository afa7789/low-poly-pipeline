"""Adamant Golem (n024): medido em artifacts/model-sheets/refs/n024/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n024.py -- <out.glb>

Barril de aco com anel dourado, capacete com chifres de marfim, ombros em domo, antebracos-manoplas e punhos enormes.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "steel": 0x6C7D8E, "steel_dk": 0x566676, "steel_lt": 0x7B8C9C, "gold": 0xE0A83C, "horn": 0xEFE8D4,
    "visor": 0x1A1C20, "eye": 0xFF6A1A, "flame": 0xFFB020, "furnace": 0x2A2E36,
}

LEG_X, HIP, KNEE, ANKLE = 0.32, 1.08, 0.6, 0.17
SH_X, SH_Y, EL_X, EL_Y, WR_X, WR_Y = 0.62, 2.0, 0.74, 1.5, 0.77, 0.88


def band(bone, y, r, h=0.07, x=0.0):
    H.frustum(bone, "gold", (x, y, 0), (x, y + h, 0), (r, r), (r, r), sides=8)


def head():
    H.frustum("head", "steel", (0, 2.26, 0), (0, 2.5, 0), (0.19, 0.2), (0.19, 0.2), sides=8)
    H.frustum("head", "steel", (0, 2.5, 0), (0, 2.62, 0), (0.19, 0.2), (0.1, 0.11), sides=8)
    H.box("head", "visor", (0, 2.4, 0.19), (0.3, 0.17, 0.06))
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.07, 2.42, 0.225), (0.075, 0.04, 0.02))
        H.frustum("head", "steel_dk", (s * 0.17, 2.4, 0), (s * 0.26, 2.4, 0), (0.09, 0.09), (0.08, 0.08), sides=6)
        H.chain("head", "horn", [(s * 0.24, 2.42, -0.04), (s * 0.39, 2.5, -0.05), (s * 0.43, 2.63, -0.05), (s * 0.28, 2.77, -0.05)],
                [(0.08, 0.08), (0.075, 0.075), (0.06, 0.06), (0.008, 0.008)], sides=6)


def barrel():
    rings = [(1.15, 0.37), (1.45, 0.46), (1.75, 0.48), (2.05, 0.45), (2.28, 0.38)]
    for (y0, r0), (y1, r1) in zip(rings, rings[1:]):
        H.frustum("spine", "steel", (0, y0, 0), (0, y1, 0), (r0, r0), (r1, r1), sides=8)
    for y, r in ((1.15, 0.41), (1.47, 0.49), (1.98, 0.5), (2.21, 0.42)):
        band("spine", y, r)
    H.box("spine", "furnace", (0, 1.4, 0.45), (0.26, 0.3, 0.07))                # fornalha de frente
    H.box("spine", "flame", (0, 1.38, 0.49), (0.14, 0.2, 0.03))
    H.frustum("pelvis", "steel_dk", (0, 0.88, 0), (0, 1.2, 0), (0.28, 0.24), (0.36, 0.3), sides=8)


def shoulder_arm(s, side):
    H.frustum(f"arm.{side}", "steel", (s * 0.56, 1.76, 0), (s * 0.6, 1.96, 0), (0.24, 0.2), (0.33, 0.24), sides=8)    # domo
    H.frustum(f"arm.{side}", "steel", (s * 0.6, 1.96, 0), (s * 0.55, 2.2, 0), (0.33, 0.24), (0.17, 0.13), sides=8)
    H.frustum(f"arm.{side}", "steel_dk", (s * 0.64, 1.98, 0), (s * EL_X, EL_Y, 0), (0.16, 0.16), (0.15, 0.15), sides=6)
    H.frustum(f"arm.{side}", "steel_lt", (s * 0.7, 1.58, 0), (s * EL_X, 1.4, 0), (0.17, 0.17), (0.19, 0.19), sides=6)


def forearm_fist(s, side):
    b, x = f"forearm.{side}", s * WR_X
    H.frustum(b, "steel", (x, 1.42, 0), (x, 1.15, 0), (0.25, 0.25), (0.27, 0.27), sides=8)
    H.frustum(b, "steel", (x, 1.15, 0), (x, 0.86, 0), (0.27, 0.27), (0.25, 0.25), sides=8)
    band(b, 1.2, 0.29, 0.17, x)
    band(b, 0.82, 0.29, 0.14, x)
    H.frustum(b, "steel_dk", (x, 0.88, 0.02), (x, 0.58, 0.04), (0.24, 0.25), (0.28, 0.27), sides=6)      # punho
    H.frustum(b, "steel", (x, 0.6, 0.04), (x, 0.34, 0.08), (0.28, 0.27), (0.25, 0.26), sides=6)
    H.frustum(b, "steel_lt", (s * (WR_X - 0.22), 0.8, 0.14), (s * (WR_X - 0.2), 0.55, 0.28), (0.1, 0.1), (0.09, 0.09), sides=6)   # polegar


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * LEG_X
        H.frustum(f"thigh.{side}", "steel", (x, KNEE, 0), (x, HIP + 0.05, 0), (0.18, 0.19), (0.23, 0.24), sides=6)
        H.frustum(f"shin.{side}", "steel", (x, ANKLE, 0), (x, KNEE + 0.02, 0), (0.2, 0.2), (0.17, 0.17), sides=6)
        H.frustum(f"shin.{side}", "gold", (x, 0.46, 0), (x, 0.68, 0), (0.2, 0.2), (0.2, 0.2), sides=6)
        H.frustum(f"foot.{side}", "steel", (x, 0.11, -0.12), (x, 0.11, 0.34), (0.24, 0.12), (0.22, 0.09), sides=8)
        H.frustum(f"foot.{side}", "steel_dk", (x, 0.02, -0.14), (x, 0.03, 0.36), (0.25, 0.04), (0.23, 0.04), sides=8)


def make():
    head()
    barrel()
    legs()
    for s, side in ((1, "L"), (-1, "R")):
        shoulder_arm(s, side)
        forearm_fist(s, side)


def joints():
    out = {"pelvis": ((0, 1.0, 0), (0, 1.2, 0)), "spine": ((0, 1.2, 0), (0, 2.25, 0)), "head": ((0, 2.25, 0), (0, 2.75, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * WR_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.08, 0.5))
    return out


H.build("n024", "biped", PALETTE, make, joints())
