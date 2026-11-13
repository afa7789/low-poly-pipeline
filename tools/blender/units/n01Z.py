"""Assassin (n01Z): medido em artifacts/model-sheets/refs/n01Z/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n01Z.py -- <out.glb>

Uma espada longa na mao DIREITA (forearm.R), inclinada para frente e para fora como no perfil; mao esquerda vazia.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "green": 0x7AA56F, "green_dk": 0x4F7E4A, "cape": 0x23513A, "gold": 0xC4A050, "black": 0x1B1B20,
    "skin": 0x8E6FC0, "hair": 0x2B2A6B, "steel": 0xB4BAC2, "grip": 0x3A2A22, "eye": 0xFFFFFF,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X = 1.28, 0.78, 0.19, 0.16, 0.17
WAIST, NECK, TOP = 1.55, 2.14, 2.72
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.38, 2.0, 0.44, 1.5, 1.22


def head():
    H.frustum("head", "skin", (0, 2.2, 0.08), (0, 2.56, 0.08), (0.13, 0.14), (0.14, 0.14), sides=6)
    H.frustum("head", "cape", (0, 2.12, -0.06), (0, 2.6, -0.06), (0.25, 0.23), (0.25, 0.24), sides=8)      # capuz
    H.frustum("head", "cape", (0, 2.6, -0.06), (0, 2.76, -0.09), (0.25, 0.24), (0.1, 0.1), sides=8)
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.065, 2.43, 0.215), (0.06, 0.035, 0.03))
        H.chain("head", "skin", [(s * 0.13, 2.46, 0.0), (s * 0.28, 2.54, -0.03), (s * 0.44, 2.6, -0.06)],
                [(0.07, 0.035), (0.05, 0.025), (0.008, 0.008)], sides=4)


def hair():
    for s in (-1, 1):
        H.chain("spine", "hair", [(s * 0.1, 2.3, 0.1), (s * 0.13, 2.1, 0.19), (s * 0.12, 1.85, 0.2), (s * 0.1, 1.68, 0.18)],
                [(0.05, 0.05), (0.06, 0.05), (0.05, 0.04), (0.012, 0.012)], sides=6)


def torso():
    H.frustum("spine", "black", (0, WAIST - 0.05, 0), (0, 2.0, 0), (0.24, 0.17), (0.3, 0.19), sides=8)
    H.frustum("spine", "green", (0, 1.62, 0.0), (0, 2.02, 0.0), (0.22, 0.15), (0.28, 0.17), sides=8)       # peitoral em V
    H.frustum("spine", "green", (0, 2.02, 0.0), (0, 2.26, -0.01), (0.28, 0.17), (0.17, 0.13), sides=8)
    H.frustum("pelvis", "black", (0, 1.0, 0), (0, WAIST, 0), (0.26, 0.17), (0.23, 0.16), sides=8)
    H.frustum("pelvis", "gold", (0, WAIST - 0.1, 0), (0, WAIST + 0.03, 0), (0.25, 0.18), (0.24, 0.17), sides=8)
    H.frustum("pelvis", "green", (0, 1.3, 0.04), (0, WAIST - 0.1, 0.04), (0.1, 0.13), (0.2, 0.15), sides=6)
    for s in (-1, 1):       # ombreiras em cunha
        H.frustum("spine", "green", (s * 0.18, 2.28, 0), (s * 0.48, 2.04, 0), (0.12, 0.2), (0.17, 0.22), sides=6)
        H.frustum("spine", "gold", (s * 0.4, 2.1, 0), (s * 0.5, 2.0, 0), (0.1, 0.22), (0.1, 0.23), sides=6)


def hem(p):
    return {"pelvis": 1.0} if p[1] > 1.2 else {"pelvis": 0.35, "thigh.L" if p[0] > 0 else "thigh.R": 0.65}


def cape():
    H.frustum("spine", "cape", (0, 2.18, -0.2), (0, WAIST, -0.26), (0.32, 0.045), (0.37, 0.05), sides=4)
    low = H.frustum("pelvis", "cape", (0, WAIST, -0.26), (0, 0.57, -0.46), (0.37, 0.09), (0.52, 0.1), sides=4)
    H.soft(low, hem)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * KNEE_X
        H.frustum(f"thigh.{side}", "black", (x, KNEE - 0.05, 0), (s * LEG_X, HIP + 0.05, 0), (0.14, 0.15), (0.19, 0.18), sides=6)
        H.frustum(f"thigh.{side}", "green", (x, KNEE - 0.1, 0.09), (x, KNEE + 0.14, 0.09), (0.12, 0.08), (0.11, 0.07), sides=6)  # joelheira
        H.frustum(f"shin.{side}", "black", (x, ANKLE, 0), (x, KNEE - 0.04, 0), (0.11, 0.12), (0.13, 0.13), sides=6)
        H.frustum(f"shin.{side}", "green", (x, ANKLE + 0.06, 0.04), (x, KNEE - 0.06, 0.05), (0.12, 0.11), (0.16, 0.13), sides=6)  # grevas
        H.frustum(f"foot.{side}", "black", (x, 0.03, -0.03), (x, ANKLE + 0.04, -0.03), (0.15, 0.17), (0.12, 0.14), sides=6)
        H.frustum(f"foot.{side}", "black", (x, 0.11, 0.04), (x, 0.08, 0.42), (0.15, 0.1), (0.13, 0.06), sides=4)


def arms():
    for s, side in ((1, "L"), (-1, "R")):
        H.frustum(f"arm.{side}", "black", (s * (SH_X + 0.03), SH_Y, 0), (s * EL_X, EL_Y - 0.02, 0), (0.12, 0.12), (0.1, 0.1), sides=6)
        H.frustum(f"arm.{side}", "green", (s * (EL_X + 0.01), EL_Y + 0.14, 0), (s * (EL_X + 0.02), EL_Y - 0.06, 0), (0.12, 0.13), (0.13, 0.13), sides=6)
        H.frustum(f"forearm.{side}", "black", (s * EL_X, EL_Y + 0.02, 0), (s * EL_X, WR_Y + 0.04, 0.02), (0.1, 0.1), (0.09, 0.09), sides=6)
        H.frustum(f"forearm.{side}", "green", (s * EL_X, EL_Y - 0.04, 0.02), (s * EL_X, WR_Y + 0.06, 0.03), (0.12, 0.12), (0.14, 0.13), sides=6)
        H.frustum(f"forearm.{side}", "skin", (s * EL_X, WR_Y + 0.05, 0.03), (s * EL_X, WR_Y - 0.14, 0.05), (0.1, 0.11), (0.1, 0.12), sides=6)


def sword():
    x, y = -EL_X, WR_Y
    H.frustum("forearm.R", "grip", (x, y + 0.1, 0.03), (x - 0.01, y - 0.04, 0.09), (0.04, 0.04), (0.04, 0.04), sides=6)
    H.frustum("forearm.R", "gold", (x - 0.12, y - 0.04, 0.09), (x + 0.12, y - 0.04, 0.09), (0.04, 0.045), (0.04, 0.045), sides=4)  # guarda
    pts = [(x - 0.01, y - 0.05, 0.1), (x - 0.22, y - 0.38, 0.32), (x - 0.43, y - 0.72, 0.58)]
    H.chain("forearm.R", "steel", pts, [(0.05, 0.04), (0.05, 0.035), (0.012, 0.012)], sides=4)


def make():
    head()
    hair()
    torso()
    cape()
    legs()
    arms()
    sword()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)), "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * KNEE_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * KNEE_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * KNEE_X, ANKLE, 0), (s * KNEE_X, 0.06, 0.5))
    return out


H.build("n01Z", "biped", PALETTE, make, joints())
