"""Angry Hrimthrusa (n02I): medido em artifacts/model-sheets/refs/n02I/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n02I.py -- <out.glb>

Morsa barriguda: mascara de gas, presas, ombreira dourada so no ombro esquerdo, lanterna na mao direita,
manivela na esquerda, mochila com tanque e 3 lancas de cristal nas costas. A prancha nao poe lanca na mao:
os punhos sao grandes.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "coat": 0x3E2B35, "coat_dk": 0x2E2029, "skin": 0xB5604F, "skin_dk": 0x984B3F, "gold": 0xC79A2E, "gold_dk": 0xA07A20,
    "mask": 0x33353D, "goggle": 0xF0A020, "tusk": 0xE8DEC8, "boot": 0x8A4A33, "fur": 0xEEE6D8, "wood": 0x4A3322,
    "tank": 0xBFE0EE, "crystal": 0x5AA8E8, "crystal_lt": 0xA8D8FA, "lamp": 0xE8A838,
}

HIP, KNEE, ANKLE, LEG_X = 0.85, 0.45, 0.17, 0.37
WAIST, NECK, TOP = 1.1, 2.0, 2.45
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.78, 2.0, 0.98, 1.4, 0.95


def head():
    H.frustum("head", "skin", (0, 2.0, 0.38), (0, 2.18, 0.38), (0.3, 0.28), (0.29, 0.27), sides=8)
    H.frustum("head", "skin", (0, 2.18, 0.38), (0, 2.42, 0.36), (0.29, 0.27), (0.2, 0.19), sides=8)
    H.frustum("head", "mask", (0, 2.02, 0.56), (0, 2.2, 0.6), (0.13, 0.08), (0.17, 0.1), sides=6)
    H.frustum("head", "mask", (0, 2.22, 0.5), (0, 2.38, 0.52), (0.27, 0.1), (0.27, 0.1), sides=8)       # faixa dos oculos
    for s in (-1, 1):
        H.box("head", "goggle", (s * 0.11, 2.3, 0.6), (0.13, 0.1, 0.05))
        H.frustum("head", "tusk", (s * 0.12, 2.0, 0.62), (s * 0.16, 1.4, 0.76), (0.065, 0.065), (0.02, 0.02), sides=6)


def torso():
    H.frustum("pelvis", "coat", (0, 0.7, 0.1), (0, 1.15, 0.14), (0.5, 0.52), (0.64, 0.66), sides=8)
    H.frustum("spine", "coat", (0, 1.1, 0.14), (0, 1.55, 0.12), (0.64, 0.66), (0.7, 0.6), sides=8)
    H.frustum("spine", "coat", (0, 1.55, 0.06), (0, 1.95, 0.02), (0.7, 0.54), (0.74, 0.46), sides=8)
    H.frustum("spine", "coat_dk", (0, 1.95, 0.02), (0, 2.22, 0.04), (0.74, 0.46), (0.36, 0.3), sides=8)
    # mochila: quadro, bobinas, tanque deitado, 3 lancas de cristal
    H.box("spine", "wood", (0, 1.6, -0.6), (0.9, 0.9, 0.2))
    for s in (-1, 1):
        H.frustum("spine", "tusk", (s * 0.42, 1.25, -0.62), (s * 0.42, 1.9, -0.62), (0.07, 0.07), (0.07, 0.07), sides=6)
        H.wheel("spine", "wood", (s * 0.25, 1.02, -0.78), 0.23, 0.05)
        H.frustum("spine", "crystal", (s * 0.26, 1.3, -0.68), (s * 0.26, 2.72, -0.68), (0.045, 0.045), (0.04, 0.04), sides=4)
        H.frustum("spine", "crystal_lt", (s * 0.26, 2.72, -0.68), (s * 0.26, 2.95, -0.68), (0.07, 0.07), (0.0, 0.0), sides=4)
    H.wheel("spine", "tank", (0, 1.02, -0.78), 0.2, 0.8, sides=8)
    H.frustum("spine", "crystal", (0, 1.3, -0.68), (0, 2.8, -0.68), (0.045, 0.045), (0.04, 0.04), sides=4)
    H.frustum("spine", "crystal_lt", (0, 2.8, -0.68), (0, 3.02, -0.68), (0.07, 0.07), (0.0, 0.0), sides=4)


def arm(s, side):
    a, f = f"arm.{side}", f"forearm.{side}"
    H.frustum(a, "coat", (s * 0.7, 1.85, 0), (s * 0.82, 2.12, 0), (0.3, 0.3), (0.34, 0.32), sides=8)
    H.frustum(a, "coat", (s * SH_X, 2.0, 0), (s * EL_X, 1.4, 0.03), (0.34, 0.31), (0.27, 0.26), sides=8)
    H.frustum(f, "coat", (s * EL_X, 1.45, 0.03), (s * EL_X, 1.12, 0.06), (0.28, 0.27), (0.27, 0.26), sides=8)
    H.frustum(f, "skin", (s * EL_X, 1.15, 0.06), (s * EL_X, 0.95, 0.08), (0.22, 0.22), (0.28, 0.26), sides=8)
    H.frustum(f, "skin", (s * EL_X, 0.95, 0.08), (s * EL_X, 0.68, 0.1), (0.28, 0.26), (0.2, 0.2), sides=8)
    H.frustum(f, "skin_dk", (s * (EL_X - 0.1), 0.88, 0.3), (s * (EL_X - 0.1), 0.74, 0.32), (0.13, 0.05), (0.1, 0.04), sides=4)  # dedos


def gold_and_props():
    H.frustum("arm.L", "gold", (0.6, 1.85, 0), (0.98, 2.22, 0), (0.3, 0.42), (0.2, 0.4), sides=4)
    H.frustum("arm.L", "gold_dk", (0.66, 1.78, 0), (0.78, 1.9, 0), (0.28, 0.44), (0.3, 0.44), sides=4)
    H.frustum("arm.L", "gold", (0.9, 2.1, 0), (1.05, 2.0, 0), (0.18, 0.4), (0.2, 0.4), sides=4)
    # lanterna na mao direita
    H.frustum("forearm.R", "wood", (-1.0, 0.82, 0.1), (-1.0, 0.7, 0.1), (0.08, 0.02), (0.1, 0.03), sides=6)
    H.frustum("forearm.R", "wood", (-1.0, 0.72, 0.12), (-1.0, 0.62, 0.12), (0.05, 0.05), (0.07, 0.07), sides=6)
    H.frustum("forearm.R", "lamp", (-1.0, 0.6, 0.12), (-1.0, 0.36, 0.12), (0.13, 0.13), (0.15, 0.15), sides=6)
    H.frustum("forearm.R", "lamp", (-1.0, 0.36, 0.12), (-1.0, 0.24, 0.12), (0.15, 0.15), (0.1, 0.1), sides=6)
    H.frustum("forearm.R", "wood", (-1.0, 0.24, 0.12), (-1.0, 0.16, 0.12), (0.2, 0.2), (0.2, 0.2), sides=8)
    # manivela na mao esquerda
    H.box("forearm.L", "wood", (0.68, 0.86, -0.05), (0.14, 0.4, 0.2))
    H.frustum("forearm.L", "wood", (0.7, 0.72, -0.05), (1.3, 0.72, -0.05), (0.05, 0.05), (0.05, 0.05), sides=4)
    H.frustum("forearm.L", "wood", (1.3, 0.72, -0.05), (1.3, 0.72, 0.2), (0.07, 0.07), (0.07, 0.07), sides=4)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * LEG_X
        H.frustum(f"thigh.{side}", "coat", (x, KNEE - 0.04, 0), (x, HIP + 0.06, 0.02), (0.26, 0.26), (0.34, 0.34), sides=8)
        H.frustum(f"shin.{side}", "coat_dk", (x, ANKLE, 0), (x, KNEE + 0.05, 0), (0.22, 0.22), (0.27, 0.27), sides=8)
        H.frustum(f"shin.{side}", "boot", (x, 0.1, 0), (x, 0.33, 0), (0.26, 0.26), (0.24, 0.24), sides=8)
        H.frustum(f"shin.{side}", "fur", (x, 0.3, 0), (x, 0.42, 0), (0.27, 0.27), (0.33, 0.33), sides=8)
        H.frustum(f"foot.{side}", "boot", (x, 0.14, 0.0), (x, 0.1, 0.42), (0.25, 0.14), (0.21, 0.08), sides=6)
        H.frustum(f"foot.{side}", "fur", (x, 0.03, -0.1), (x, 0.03, 0.46), (0.28, 0.03), (0.24, 0.03), sides=6)


def make():
    head()
    torso()
    legs()
    for s, side in ((1, "L"), (-1, "R")):
        arm(s, side)
    gold_and_props()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0.35), (0, TOP, 0.35))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("n02I", "biped", PALETTE, make, joints())
