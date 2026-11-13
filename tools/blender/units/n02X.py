"""Ogre (n02X): medido em artifacts/model-sheets/refs/n02X/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n02X.py -- <out.glb>

Bruto de capuz e mascara de gas: barrigudo, ombros enormes, pauldron cinza com X no ombro esquerdo,
chave de valvula (cabo + volante) na mao direita (da unidade), a esquerda vazia, cilindro no quadril.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "skin": 0xC98E5A, "skin_dk": 0xA8744A, "hood": 0xC9A878, "mask": 0x8A6A44, "pants": 0xA8845A,
    "boot": 0x7A5A38, "belt": 0x4A3628, "strap": 0x3C3C40, "steel": 0x333336, "iron": 0x4C4C50,
    "cream": 0xE0C89A, "orange": 0xE07A2A, "black": 0x0E0E10,
}

SH, EL, WR = (0.8, 1.8, 0.0), (0.95, 1.3, 0.1), (0.85, 0.95, 0.4)
POLE = (-0.85, 0.45)        # x, z do cabo
HIP, KNEE, ANKLE, LEG_X = 0.8, 0.48, 0.15, 0.34


def head():
    H.frustum("head", "hood", (0, 1.8, 0.1), (0, 2.12, 0.28), (0.46, 0.4), (0.34, 0.34), sides=8)
    H.frustum("head", "hood", (0, 2.1, 0.25), (0, 2.44, 0.3), (0.32, 0.32), (0.14, 0.16), sides=8)
    H.frustum("head", "mask", (0, 2.08, 0.3), (0, 1.97, 0.55), (0.13, 0.12), (0.11, 0.09), sides=6)
    for s in (-1, 1):
        H.box("head", "black", (s * 0.1, 2.17, 0.46), (0.13, 0.11, 0.07))


def torso():
    H.frustum("spine", "skin", (0, 0.85, 0.05), (0, 1.4, 0.08), (0.52, 0.5), (0.62, 0.52), sides=8)
    H.frustum("spine", "skin", (0, 1.35, 0.05), (0, 1.85, 0.0), (0.64, 0.5), (0.88, 0.48), sides=8)
    H.frustum("spine", "skin", (0, 1.85, 0.0), (0, 2.08, 0.08), (0.88, 0.48), (0.4, 0.36), sides=8)
    H.frustum("spine", "strap", (0, 1.47, 0.04), (0, 1.66, 0.04), (0.7, 0.56), (0.74, 0.56), sides=8)      # faixa do peito
    H.box("spine", "orange", (0.25, 1.22, 0.62), (0.1, 0.12, 0.04))
    H.frustum("pelvis", "belt", (0, 0.92, 0.04), (0, 1.22, 0.06), (0.62, 0.55), (0.6, 0.54), sides=8)
    H.box("pelvis", "iron", (0, 1.07, 0.6), (0.14, 0.16, 0.06))
    for x in (-0.3, 0.3):
        H.box("pelvis", "iron", (x, 1.07, 0.58), (0.1, 0.14, 0.06))
    H.frustum("pelvis", "pants", (0, 0.62, 0), (0, 0.95, 0.02), (0.52, 0.42), (0.52, 0.46), sides=8)
    H.frustum("pelvis", "iron", (-0.64, 0.74, -0.2), (-0.64, 1.08, -0.2), (0.14, 0.14), (0.13, 0.13), sides=8)    # cilindro no quadril


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * LEG_X
        H.frustum(f"thigh.{side}", "pants", (x, KNEE, 0.02), (x, HIP + 0.1, 0), (0.28, 0.28), (0.36, 0.34), sides=8)
        H.frustum(f"shin.{side}", "boot", (x, 0.1, 0), (x, 0.8, 0.02), (0.27, 0.3), (0.36, 0.34), sides=6)
        H.frustum(f"foot.{side}", "boot", (x, 0.1, -0.1), (x, 0.08, 0.2), (0.3, 0.12), (0.3, 0.1), sides=6)
        H.frustum(f"foot.{side}", "boot", (x, 0.08, 0.1), (x, 0.06, 0.58), (0.3, 0.1), (0.24, 0.07), sides=6)


def arms():
    for s, side in ((1, "L"), (-1, "R")):
        H.frustum(f"arm.{side}", "skin", (s * 0.6, 1.9, 0), (s * 0.82, 1.78, 0.02), (0.36, 0.36), (0.4, 0.4), sides=8)
        H.frustum(f"arm.{side}", "skin", (s * SH[0], SH[1], SH[2]), (s * EL[0], EL[1], EL[2]), (0.36, 0.34), (0.3, 0.29), sides=8)
        H.frustum(f"forearm.{side}", "skin", (s * EL[0], EL[1] + 0.05, EL[2]), (s * WR[0], WR[1] + 0.08, WR[2]), (0.3, 0.29), (0.34, 0.33), sides=8)
        H.frustum(f"forearm.{side}", "skin_dk", (s * WR[0], WR[1] + 0.08, WR[2]), (s * WR[0], WR[1] - 0.28, WR[2]), (0.32, 0.3), (0.22, 0.2), sides=8)


def pauldron():
    H.frustum("arm.L", "strap", (0.55, 2.0, 0), (0.98, 1.7, 0.02), (0.3, 0.34), (0.34, 0.36), sides=6)
    H.box("arm.L", "strap", (0.97, 1.78, 0), (0.1, 0.36, 0.7))
    for sgn in (-1, 1):     # o X, na face externa do ombro
        H.panel("arm.L", "cream", [(1.03, 1.95 - 0.02, sgn * 0.3 + 0.0), (1.03, 1.95 + 0.0, sgn * 0.3 + 0.04),
                                   (1.03, 1.6 + 0.0, -sgn * 0.3 + 0.04), (1.03, 1.6 - 0.02, -sgn * 0.3)], thickness=0.03)


def wrench():
    """Chave de valvula: cabo grosso em pe na mao direita, volante de raios no alto."""
    x, z = POLE
    H.frustum("forearm.R", "steel", (x, 0.7, z), (x, 2.25, z), (0.1, 0.1), (0.09, 0.09), sides=8)
    H.frustum("forearm.R", "iron", (x, 0.66, z), (x, 0.76, z), (0.12, 0.12), (0.12, 0.12), sides=8)
    H.frustum("forearm.R", "iron", (x, 2.2, z), (x, 2.4, z), (0.11, 0.11), (0.1, 0.1), sides=8)
    ring = [(x + 0.25 * math.cos(i * math.pi / 4), 2.36, z + 0.25 * math.sin(i * math.pi / 4)) for i in range(9)]
    for a, b in zip(ring, ring[1:]):
        H.frustum("forearm.R", "steel", a, b, (0.04, 0.04), (0.04, 0.04), sides=4)
    for ang in (0, math.pi / 3, 2 * math.pi / 3):
        d = (0.25 * math.cos(ang), 0, 0.25 * math.sin(ang))
        H.frustum("forearm.R", "steel", (x - d[0], 2.36, z - d[2]), (x + d[0], 2.36, z + d[2]), (0.03, 0.03), (0.03, 0.03), sides=4)


def make():
    head()
    torso()
    legs()
    arms()
    pauldron()
    wrench()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, 1.1, 0)), "spine": ((0, 1.1, 0), (0, 1.85, 0.0)),
           "head": ((0, 1.85, 0.2), (0, 2.35, 0.3))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH[0], SH[1], SH[2]), (s * EL[0], EL[1], EL[2]))
        out[f"forearm.{side}"] = ((s * EL[0], EL[1], EL[2]), (s * WR[0], WR[1], WR[2]))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0.02))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0.02), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("n02X", "biped", PALETTE, make, joints())
