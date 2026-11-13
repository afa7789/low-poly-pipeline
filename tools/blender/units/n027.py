"""Corrupted Annihilator (n027): medido em artifacts/model-sheets/refs/n027/sheet.jpg (~260 px por metro).

    blender -b --factory-startup -P tools/blender/units/n027.py -- <out.glb>

Arvore podre curvada: copa roxa flutuando sobre dois galhos nas costas, manto de folhas, joia verde no peito,
bracos longos com garras pretas grandes. Sem arma: o golpe e de garra (antebraco + mao + 3 garras).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "wood": 0x6B6232, "wood_dk": 0x4C4526, "wood_lt": 0x80773E, "purple": 0x8A4A7E, "purple_dk": 0x5E2F58,
    "purple_lt": 0xA25E94, "claw": 0x2A1A22, "green": 0x5CE030, "eye": 0xD8E83A, "rust": 0x9A4A2A, "mouth": 0x120A0E,
}
SH, EL, WR = (0.62, 2.05, 0.0), (0.88, 1.5, 0.05), (1.0, 0.95, 0.1)


def head():
    H.frustum("head", "wood", (0, 2.2, 0.5), (0, 2.58, 0.44), (0.32, 0.28), (0.28, 0.25), sides=8)
    H.frustum("head", "wood_dk", (0, 2.3, 0.7), (0, 2.5, 0.66), (0.2, 0.06), (0.22, 0.06), sides=6)     # testa
    H.frustum("head", "mouth", (0, 2.3, 0.72), (0, 2.18, 0.74), (0.17, 0.05), (0.15, 0.05), sides=6)
    H.chain("head", "wood_dk", [(0, 2.25, 0.7), (0, 1.95, 0.78), (0, 1.7, 0.8)], [(0.17, 0.08), (0.12, 0.07), (0.03, 0.03)])
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.12, 2.43, 0.72), (0.1, 0.045, 0.05))
        H.chain("head", "wood_dk", [(s * 0.1, 2.15, 0.72), (s * 0.12, 1.95, 0.76), (s * 0.1, 1.8, 0.78)], [(0.04, 0.04), (0.03, 0.03), (0.01, 0.01)], sides=4)
    H.frustum("head", "rust", (0, 2.1, 0.0), (0, 2.5, -0.02), (0.5, 0.3), (0.4, 0.3), sides=8)          # gola


def crown():
    for s in (-1, 1):
        H.chain("spine", "wood", [(s * 0.3, 2.0, -0.15), (s * 0.55, 2.6, -0.12), (s * 0.85, 3.05, -0.05)], [(0.18, 0.16), (0.13, 0.12), (0.08, 0.08)])
        H.chain("spine", "wood", [(s * 0.55, 2.6, -0.12), (s * 0.3, 3.0, -0.05)], [(0.1, 0.1), (0.05, 0.05)], sides=4)
        for x in (1.1, 0.75):
            H.frustum("spine", "purple_dk", (s * x, 2.95, -0.1), (s * x, 2.25, -0.1), (0.06, 0.03), (0.04, 0.02), sides=4)
    H.frustum("spine", "purple_dk", (0, 2.8, 0), (0, 3.1, 0), (0.9, 0.55), (1.3, 0.7), sides=8)
    H.frustum("spine", "purple", (0, 3.1, 0), (0, 3.4, 0), (1.3, 0.7), (1.15, 0.62), sides=8)
    H.frustum("spine", "purple_lt", (0, 3.4, 0), (0, 3.58, 0), (1.15, 0.62), (0.7, 0.4), sides=8)
    for s in (-1, 1):
        H.frustum("spine", "purple", (s * 0.85, 2.95, 0), (s * 0.9, 3.35, 0), (0.45, 0.5), (0.4, 0.45), sides=8)


def torso():
    H.frustum("spine", "wood", (0, 1.4, -0.05), (0, 1.95, 0.02), (0.36, 0.3), (0.5, 0.34), sides=8)
    H.frustum("spine", "wood_lt", (0, 1.9, 0.02), (0, 2.25, 0.05), (0.52, 0.34), (0.38, 0.3), sides=8)
    H.frustum("spine", "green", (0, 1.62, 0.3), (0, 2.0, 0.3), (0.06, 0.04), (0.14, 0.05), sides=6)       # joia
    H.frustum("pelvis", "wood_dk", (0, 1.05, 0.0), (0, 1.5, 0.0), (0.4, 0.3), (0.36, 0.28), sides=8)
    H.panel("pelvis", "purple_dk", [(0.2, 1.3, 0.3), (-0.2, 1.3, 0.3), (0, 0.85, 0.32)], thickness=0.04)
    H.panel("spine", "purple", [(0.5, 2.15, -0.3), (-0.5, 2.15, -0.3), (-0.5, 1.6, -0.6), (0, 1.2, -0.75), (0.5, 1.6, -0.6)], thickness=0.07)
    H.panel("pelvis", "purple_dk", [(0.45, 1.55, -0.55), (-0.45, 1.55, -0.55), (-0.3, 1.0, -0.8), (0, 0.7, -0.85), (0.3, 1.0, -0.8)], thickness=0.07)
    H.panel("pelvis", "purple_lt", [(0.2, 1.4, -0.62), (-0.2, 1.4, -0.62), (0, 0.85, -0.85)], thickness=0.08)


def arm(s, side):
    a, f = f"arm.{side}", f"forearm.{side}"
    H.frustum(a, "wood_lt", (s * 0.5, 2.0, 0.0), (s * 0.85, 2.3, 0.0), (0.2, 0.2), (0.12, 0.12), sides=6)    # ombro pontudo
    H.frustum(a, "wood", (s * 0.55, 2.1, 0.0), (s * 0.72, 1.8, 0.02), (0.22, 0.22), (0.2, 0.2), sides=8)
    H.frustum(a, "wood", (s * 0.72, 1.85, 0.02), (s * EL[0], EL[1] + 0.02, EL[2]), (0.2, 0.2), (0.16, 0.16), sides=8)
    H.frustum(f, "wood_dk", (s * EL[0], 1.55, 0.06), (s * 0.95, 1.25, 0.08), (0.17, 0.17), (0.2, 0.2), sides=8)
    H.frustum(f, "wood", (s * 0.95, 1.3, 0.08), (s * WR[0], WR[1] + 0.02, WR[2]), (0.2, 0.2), (0.25, 0.22), sides=8)
    H.frustum(f, "claw", (s * WR[0], 1.0, 0.1), (s * WR[0], 0.72, 0.12), (0.22, 0.16), (0.16, 0.1), sides=6)
    for dx, dz in ((-0.14, 0.0), (0.0, 0.06), (0.14, 0.0)):
        x = s * (WR[0] + dx)
        H.chain(f, "claw", [(x, 0.8, 0.1 + dz), (x - s * 0.04 - s * dx * 0.5, 0.5, 0.2 + dz), (x - s * 0.12 - s * dx, 0.28, 0.34 + dz)],
                [(0.06, 0.06), (0.045, 0.045), (0.006, 0.006)], sides=4)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        H.frustum(f"thigh.{side}", "wood", (s * 0.3, 1.3, 0.0), (s * 0.45, 0.62, 0.0), (0.34, 0.32), (0.22, 0.22), sides=8)
        H.frustum(f"thigh.{side}", "wood_lt", (s * 0.4, 0.95, 0.12), (s * 0.45, 0.6, 0.15), (0.12, 0.05), (0.14, 0.06), sides=6)
        H.frustum(f"shin.{side}", "wood_dk", (s * 0.45, 0.66, 0.0), (s * 0.52, 0.35, 0.0), (0.24, 0.22), (0.19, 0.19), sides=8)
        H.frustum(f"shin.{side}", "wood", (s * 0.52, 0.4, 0.0), (s * 0.56, 0.1, 0.0), (0.18, 0.18), (0.3, 0.26), sides=8)
        H.frustum(f"foot.{side}", "wood_dk", (s * 0.56, 0.1, -0.2), (s * 0.58, 0.08, 0.42), (0.3, 0.15), (0.22, 0.1), sides=6)
        for dx in (-0.2, 0.0, 0.2):
            H.frustum(f"foot.{side}", "wood_dk", (s * (0.58 + dx * 0.5), 0.08, 0.3), (s * (0.58 + dx * 1.6), 0.04, 0.58), (0.07, 0.05), (0.01, 0.01), sides=4)


def make():
    head()
    crown()
    torso()
    legs()
    for s, side in ((1, "L"), (-1, "R")):
        arm(s, side)


def joints():
    out = {}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH[0], SH[1], SH[2]), (s * EL[0], EL[1], EL[2]))
        out[f"forearm.{side}"] = ((s * EL[0], EL[1], EL[2]), (s * WR[0], WR[1], WR[2]))
        out[f"thigh.{side}"] = ((s * 0.3, 1.2, 0), (s * 0.45, 0.62, 0))
        out[f"shin.{side}"] = ((s * 0.45, 0.62, 0), (s * 0.56, 0.1, 0))
        out[f"foot.{side}"] = ((s * 0.56, 0.1, 0), (s * 0.58, 0.08, 0.5))
    return out


H.build("n027", "biped", PALETTE, make, joints())
