"""Infernal (n000): medido em artifacts/model-sheets/refs/n000/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n000.py -- <out.glb>

Golem de pedra com rachaduras verdes: ombros em bola com espinhos, punhos enormes, caveira na frente do peito.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "stone": 0x6E6E50, "stone_lt": 0x7C7C5C, "stone_dk": 0x2E2C20, "glow": 0x9BFF2A, "spike": 0xB09AAC, "eye": 0x66FF22,
    "bone": 0x7C7E5A,
}

LEG_X, HIP, KNEE, ANKLE = 0.36, 1.0, 0.52, 0.2
SH_X, SH_Y, EL_X, EL_Y, WR_X, WR_Y = 0.78, 2.2, 0.9, 1.6, 0.9, 0.8


def spike(bone, a, b, r=0.1):
    H.frustum(bone, "spike", a, b, (r, r), (0.01, 0.01), sides=4)


def head():
    H.frustum("head", "bone", (0, 2.18, 0.1), (0, 2.5, 0.12), (0.22, 0.22), (0.27, 0.25), sides=8)       # crânio
    H.frustum("head", "bone", (0, 2.5, 0.12), (0, 2.66, 0.1), (0.25, 0.23), (0.14, 0.13), sides=8)
    H.frustum("head", "stone_dk", (0, 2.2, 0.3), (0, 2.34, 0.34), (0.14, 0.06), (0.16, 0.07), sides=4)    # boca
    H.frustum("head", "bone", (0, 2.1, 0.3), (0, 2.26, 0.34), (0.15, 0.1), (0.18, 0.12), sides=6)        # mandíbula
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.1, 2.42, 0.34), (0.1, 0.05, 0.03))


def torso():
    H.frustum("spine", "stone", (0, 1.62, 0), (0, 2.0, 0), (0.4, 0.34), (0.58, 0.4), sides=8)
    H.frustum("spine", "stone", (0, 2.0, 0), (0, 2.3, 0), (0.58, 0.4), (0.4, 0.3), sides=8)
    H.frustum("spine", "stone_lt", (0, 1.85, 0.3), (0, 2.1, 0.32), (0.4, 0.12), (0.46, 0.1), sides=6)    # peitoral
    H.frustum("pelvis", "stone_dk", (0, 0.9, 0), (0, 1.66, 0), (0.46, 0.34), (0.42, 0.34), sides=8)
    H.frustum("pelvis", "stone", (0, 1.2, 0.0), (0, 1.62, 0.0), (0.4, 0.38), (0.4, 0.36), sides=8)
    H.frustum("spine", "glow", (0, 1.75, 0.37), (0, 2.1, 0.38), (0.03, 0.02), (0.09, 0.02), sides=4)      # fendas no peito
    H.frustum("spine", "glow", (-0.35, 1.7, 0.34), (0.35, 1.7, 0.34), (0.03, 0.02), (0.03, 0.02), sides=4)
    H.frustum("pelvis", "glow", (0, 1.3, 0.36), (0, 1.6, 0.36), (0.03, 0.02), (0.05, 0.02), sides=4)


def shoulder_arm(s, side):
    b = f"arm.{side}"
    H.frustum(b, "stone_dk", (s * 0.6, 2.1, 0), (s * 0.82, 2.2, 0), (0.3, 0.3), (0.3, 0.3), sides=8)    # base do ombro
    H.frustum(b, "stone", (s * 0.8, 1.96, 0), (s * 0.84, 2.25, 0), (0.26, 0.26), (0.47, 0.45), sides=8)      # bola
    H.frustum(b, "stone", (s * 0.84, 2.25, 0), (s * 0.82, 2.55, 0), (0.47, 0.45), (0.26, 0.26), sides=8)
    spike(b, (s * 0.9, 2.46, 0), (s * 1.1, 2.82, -0.05), 0.12)
    spike(b, (s * 1.0, 2.22, 0.2), (s * 1.28, 2.26, 0.3), 0.1)
    H.frustum(b, "stone_dk", (s * 0.84, 2.0, 0), (s * EL_X, EL_Y + 0.1, 0), (0.22, 0.22), (0.2, 0.2), sides=6)   # braço
    H.frustum(b, "stone", (s * EL_X, 1.75, 0), (s * EL_X, 1.5, 0), (0.2, 0.2), (0.27, 0.26), sides=6)
    H.frustum(b, "glow", (s * EL_X, 1.64, 0), (s * EL_X, 1.7, 0), (0.33, 0.31), (0.33, 0.31), sides=6)


def forearm_fist(s, side):
    b = f"forearm.{side}"
    H.frustum(b, "stone", (s * EL_X, 1.6, 0), (s * WR_X, 1.1, 0), (0.3, 0.3), (0.38, 0.34), sides=6)
    H.frustum(b, "stone_lt", (s * WR_X, 1.2, 0), (s * WR_X, 0.9, 0), (0.38, 0.34), (0.34, 0.32), sides=6)
    H.frustum(b, "glow", (s * WR_X, 0.9, 0), (s * WR_X, 0.96, 0), (0.37, 0.33), (0.37, 0.33), sides=6)
    H.frustum(b, "stone", (s * WR_X, 0.92, 0.04), (s * WR_X, 0.55, 0.08), (0.32, 0.3), (0.42, 0.34), sides=6)   # punho
    H.frustum(b, "stone_dk", (s * WR_X, 0.6, 0.08), (s * WR_X, 0.3, 0.12), (0.42, 0.34), (0.34, 0.3), sides=6)
    spike(b, (s * (WR_X + 0.3), 1.4, 0), (s * (WR_X + 0.48), 1.62, 0), 0.1)
    for k in (-1, 0, 1):    # nós dos dedos
        H.frustum(b, "spike", (s * (WR_X + k * 0.12), 0.34, 0.3), (s * (WR_X + k * 0.12), 0.3, 0.42), (0.05, 0.04), (0.04, 0.03), sides=4)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * LEG_X
        H.frustum(f"thigh.{side}", "stone_dk", (x, KNEE, 0), (x, HIP + 0.06, 0), (0.24, 0.26), (0.3, 0.3), sides=6)
        H.frustum(f"shin.{side}", "stone_dk", (x, 0.3, 0), (x, KNEE + 0.02, 0), (0.24, 0.26), (0.28, 0.28), sides=6)
        H.frustum(f"shin.{side}", "stone", (x, 0.04, 0), (x, 0.32, 0), (0.28, 0.28), (0.24, 0.24), sides=6)
        spike(f"shin.{side}", (s * (LEG_X + 0.12), 0.46, 0.2), (s * (LEG_X + 0.26), 0.66, 0.3), 0.09)
        H.frustum(f"foot.{side}", "stone", (x, 0.12, -0.1), (x, 0.1, 0.46), (0.3, 0.12), (0.28, 0.09), sides=6)
        H.frustum(f"foot.{side}", "stone_dk", (x, 0.02, -0.12), (x, 0.03, 0.5), (0.3, 0.04), (0.3, 0.04), sides=6)
        H.frustum(f"foot.{side}", "stone_lt", (x, 0.1, 0.3), (x, 0.07, 0.56), (0.25, 0.07), (0.24, 0.04), sides=4)


def make():
    head()
    torso()
    legs()
    for s, side in ((1, "L"), (-1, "R")):
        shoulder_arm(s, side)
        forearm_fist(s, side)


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, 1.5, 0)), "spine": ((0, 1.5, 0), (0, 2.2, 0)), "head": ((0, 2.2, 0), (0, 2.7, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * WR_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.08, 0.5))
    return out


H.build("n000", "biped", PALETTE, make, joints())
