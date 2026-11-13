"""Royal Assassin (n020): medido em artifacts/model-sheets/refs/n020/sheet.jpg (mesmo corpo do n01Z, capa longa).

    blender -b --factory-startup -P tools/blender/units/n020.py -- <out.glb>

Duas adagas, uma em cada mao (forearm.L e forearm.R), apontando para frente e para fora; foices de prata cruzadas nas costas.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "hood": 0x3E3558, "hood_dk": 0x2A2440, "skin": 0x8E6FC0, "silver": 0xA6AAB2, "cape": 0x2F5E5A,
    "belt": 0x7A4A2E, "eye": 0xFFFFFF, "pants": 0x2C2438, "boot": 0x40365A, "grip": 0x3A2A22,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X = 1.2, 0.64, 0.2, 0.18, 0.19
WAIST, NECK, TOP = 1.65, 2.14, 2.72
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.4, 2.08, 0.45, 1.72, 1.4


def head():
    H.frustum("head", "skin", (0, 2.2, 0.08), (0, 2.56, 0.08), (0.12, 0.13), (0.13, 0.13), sides=6)
    H.frustum("head", "hood", (0, 2.12, -0.06), (0, 2.6, -0.06), (0.24, 0.22), (0.24, 0.23), sides=8)
    H.frustum("head", "hood", (0, 2.6, -0.06), (0, 2.76, -0.09), (0.24, 0.23), (0.09, 0.09), sides=8)
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.06, 2.43, 0.205), (0.06, 0.035, 0.03))
        H.chain("head", "skin", [(s * 0.13, 2.46, 0.0), (s * 0.28, 2.55, -0.03), (s * 0.45, 2.62, -0.06)],
                [(0.07, 0.035), (0.05, 0.025), (0.008, 0.008)], sides=4)


def torso():
    H.frustum("spine", "hood", (0, WAIST - 0.05, 0), (0, 2.05, 0), (0.25, 0.17), (0.31, 0.2), sides=8)
    H.frustum("spine", "silver", (0, 1.72, 0.04), (0, 2.08, 0.05), (0.2, 0.17), (0.25, 0.19), sides=8)     # couraca
    H.frustum("spine", "hood", (0, 2.05, 0), (0, 2.26, 0), (0.31, 0.2), (0.18, 0.15), sides=8)
    H.frustum("pelvis", "pants", (0, 1.0, 0), (0, WAIST, 0), (0.28, 0.18), (0.25, 0.17), sides=8)
    H.frustum("pelvis", "hood", (0, 1.12, 0), (0, WAIST - 0.1, 0), (0.4, 0.3), (0.28, 0.2), sides=8)      # saia da tunica
    H.frustum("pelvis", "belt", (0, WAIST - 0.14, 0), (0, WAIST, 0), (0.28, 0.2), (0.27, 0.19), sides=8)
    for s in (-1, 1):
        H.frustum("spine", "hood", (s * 0.18, 2.3, 0), (s * 0.5, 2.06, 0), (0.12, 0.19), (0.16, 0.2), sides=6)


def hooks():
    for s in (-1, 1):
        pts = [(s * 0.5, 2.5, -0.3), (s * 0.4, 2.3, -0.3), (s * 0.18, 2.02, -0.3), (-s * 0.1, 1.8, -0.3), (-s * 0.28, 1.66, -0.3), (-s * 0.36, 1.78, -0.3)]
        H.chain("spine", "silver", pts, [(0.03, 0.03), (0.045, 0.04), (0.05, 0.04), (0.05, 0.04), (0.04, 0.04), (0.012, 0.012)], sides=4)


def hem(p):
    return {"pelvis": 1.0} if p[1] > 1.2 else {"pelvis": 0.3, "thigh.L" if p[0] > 0 else "thigh.R": 0.7}


def cape():
    H.frustum("spine", "cape", (0, 2.26, -0.2), (0, WAIST, -0.26), (0.36, 0.05), (0.42, 0.06), sides=4)
    low = H.frustum("pelvis", "cape", (0, WAIST, -0.26), (0, 0.27, -0.55), (0.42, 0.09), (0.68, 0.1), sides=4)
    H.soft(low, hem)
    for s in (-1, 1):       # abas laterais da capa
        wing = H.frustum("pelvis", "cape", (s * 0.5, 2.0, -0.08), (s * 0.68, 0.3, -0.1), (0.03, 0.14), (0.03, 0.3), sides=4)
        H.soft(wing, hem)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * KNEE_X
        H.frustum(f"thigh.{side}", "pants", (x, KNEE - 0.02, 0), (s * LEG_X, HIP + 0.05, 0), (0.17, 0.17), (0.2, 0.19), sides=6)
        H.frustum(f"thigh.{side}", "boot", (x, KNEE - 0.1, 0), (x, KNEE + 0.08, 0), (0.18, 0.18), (0.19, 0.19), sides=6)   # punho
        H.frustum(f"shin.{side}", "boot", (x, ANKLE, 0), (x, KNEE - 0.05, 0), (0.13, 0.14), (0.17, 0.17), sides=6)
        H.frustum(f"foot.{side}", "boot", (x, 0.03, -0.03), (x, ANKLE + 0.04, -0.03), (0.16, 0.18), (0.13, 0.15), sides=6)
        H.frustum(f"foot.{side}", "boot", (x, 0.11, 0.04), (x, 0.08, 0.44), (0.16, 0.11), (0.13, 0.06), sides=4)


def dagger(s, side):
    x, y = s * EL_X, WR_Y
    bone = f"forearm.{side}"
    H.frustum(bone, "grip", (x, y + 0.1, 0.03), (x, y - 0.04, 0.08), (0.04, 0.04), (0.04, 0.04), sides=6)
    H.frustum(bone, "silver", (x - 0.1, y - 0.04, 0.08), (x + 0.1, y - 0.04, 0.08), (0.04, 0.045), (0.04, 0.045), sides=4)
    pts = [(x, y - 0.05, 0.1), (x + s * 0.13, y - 0.25, 0.3), (x + s * 0.3, y - 0.5, 0.54)]
    H.chain(bone, "silver", pts, [(0.05, 0.04), (0.05, 0.035), (0.012, 0.012)], sides=4)


def arms():
    for s, side in ((1, "L"), (-1, "R")):
        H.frustum(f"arm.{side}", "hood", (s * (SH_X + 0.04), SH_Y, 0), (s * EL_X, EL_Y - 0.02, 0), (0.13, 0.13), (0.11, 0.11), sides=6)
        H.frustum(f"forearm.{side}", "hood", (s * EL_X, EL_Y + 0.02, 0), (s * EL_X, WR_Y + 0.05, 0.03), (0.11, 0.11), (0.1, 0.1), sides=6)
        H.frustum(f"forearm.{side}", "hood_dk", (s * EL_X, WR_Y + 0.16, 0.02), (s * EL_X, WR_Y + 0.02, 0.04), (0.11, 0.11), (0.14, 0.13), sides=6)   # luva
        H.frustum(f"forearm.{side}", "hood_dk", (s * EL_X, WR_Y + 0.03, 0.04), (s * EL_X, WR_Y - 0.14, 0.06), (0.13, 0.13), (0.1, 0.11), sides=6)
        dagger(s, side)


def make():
    head()
    torso()
    hooks()
    cape()
    legs()
    arms()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)), "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * KNEE_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * KNEE_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * KNEE_X, ANKLE, 0), (s * KNEE_X, 0.06, 0.5))
    return out


H.build("n020", "biped", PALETTE, make, joints())
