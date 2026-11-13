"""Furbolg Elder Shaman (n028): medido em artifacts/model-sheets/refs/n028/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n028.py -- <out.glb>

Urso curvado com chapeu-piramide de ombros, manto de folha nas costas, bracais e garras pretas grandes.
A prancha nao desenha cajado: o golpe e de garra (antebraco + mao + 4 garras por mao).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "orange": 0xDE6E26, "orange_dk": 0xB85418, "cream": 0xF0E2C0, "stripe": 0x3A1E36, "tan": 0xB8873A, "tan_dk": 0x8E6228,
    "bandage": 0xB59C70, "black": 0x2B2B2D, "claw": 0x4A0F14, "leaf": 0x5CB03E, "leaf_dk": 0x3E8030,
    "yellow": 0xF0DE70, "red": 0xB0202A, "rope": 0xC99A3C, "nose": 0x1A1A1C,
}

SH, EL, WR = (0.7, 1.95, 0.0), (0.85, 1.45, 0.1), (0.86, 0.95, 0.2)
HIP_Z = -0.2


def head():
    H.frustum("head", "orange", (0, 1.95, 0.6), (0, 2.35, 0.55), (0.25, 0.27), (0.21, 0.23), sides=8)
    H.frustum("head", "cream", (0, 2.07, 0.72), (0, 2.02, 1.03), (0.16, 0.14), (0.11, 0.09), sides=6)     # focinho
    H.box("head", "nose", (0, 2.06, 1.05), (0.12, 0.08, 0.06))
    H.frustum("head", "cream", (0, 1.93, 0.66), (0, 1.8, 0.98), (0.14, 0.08), (0.09, 0.05), sides=6)     # mandibula
    H.frustum("head", "red", (0, 1.96, 0.7), (0, 1.94, 0.96), (0.11, 0.06), (0.08, 0.05), sides=6)
    for s in (-1, 1):
        H.frustum("head", "cream", (s * 0.06, 1.9, 0.96), (s * 0.06, 2.0, 0.97), (0.025, 0.02), (0.005, 0.005), sides=4)
        H.frustum("head", "cream", (s * 0.07, 2.0, 0.93), (s * 0.07, 1.9, 0.94), (0.025, 0.02), (0.005, 0.005), sides=4)
        H.box("head", "yellow", (s * 0.11, 2.17, 0.86), (0.07, 0.04, 0.03))
        H.frustum("head", "orange", (s * 0.19, 2.33, 0.5), (s * 0.2, 2.45, 0.5), (0.09, 0.07), (0.07, 0.05), sides=6)
    H.frustum("head", "tan", (0, 2.0, 0.4), (0, 2.6, 0.2), (0.32, 0.26), (0.06, 0.06), sides=4)               # capuz pontudo


def hat():
    apex, left, right, front, back = (0, 2.7, 0.05), (0.9, 2.1, -0.05), (-0.9, 2.1, -0.05), (0, 1.5, 0.42), (0, 2.05, -0.5)
    for tone, tri in (("tan", (apex, left, front)), ("tan", (apex, right, front)),
                      ("tan_dk", (apex, left, back)), ("tan_dk", (apex, right, back))):
        H.panel("spine", tone, tri, thickness=0.05)


def torso():
    H.frustum("spine", "cream", (0, 1.3, -0.15), (0, 1.75, 0.08), (0.42, 0.36), (0.5, 0.38), sides=8)
    H.frustum("spine", "orange", (0, 1.7, 0.05), (0, 2.1, 0.02), (0.56, 0.4), (0.6, 0.38), sides=8)
    H.frustum("spine", "orange", (0, 2.1, 0.02), (0, 2.28, 0.1), (0.5, 0.34), (0.26, 0.22), sides=8)
    leaf = [(0.5, 2.0, -0.32), (-0.5, 2.0, -0.32), (-0.45, 1.6, -0.5), (0, 0.95, -0.62), (0.45, 1.6, -0.5)]
    H.panel("spine", "leaf", leaf, thickness=0.05)
    H.frustum("spine", "leaf_dk", (0, 1.95, -0.34), (0, 1.05, -0.6), (0.02, 0.02), (0.02, 0.02), sides=4)
    H.frustum("pelvis", "orange", (0, 0.95, HIP_Z), (0, 1.25, HIP_Z), (0.44, 0.36), (0.42, 0.34), sides=8)
    H.frustum("pelvis", "rope", (0, 1.1, HIP_Z), (0, 1.24, HIP_Z), (0.46, 0.38), (0.45, 0.37), sides=8)
    H.frustum("pelvis", "black", (0, 1.2, 0.18), (0, 0.34, 0.2), (0.3, 0.04), (0.02, 0.02), sides=4)         # tanga preta
    H.panel("pelvis", "tan", [(0.18, 1.25, -0.4), (-0.18, 1.25, -0.4), (-0.1, 0.55, -0.48), (0.1, 0.55, -0.48)], thickness=0.04)


def arm(s, side):
    a, f = f"arm.{side}", f"forearm.{side}"
    H.frustum(a, "orange", (s * 0.6, 1.72, 0.0), (s * 0.72, 2.02, 0.0), (0.24, 0.24), (0.28, 0.27), sides=8)     # ombro
    H.frustum(a, "orange", (s * SH[0], 1.98, 0), (s * EL[0], EL[1] - 0.05, EL[2]), (0.24, 0.23), (0.21, 0.2), sides=8)
    H.frustum(f, "tan", (s * EL[0], 1.55, 0.09), (s * WR[0], 1.0, 0.2), (0.22, 0.22), (0.26, 0.25), sides=6)     # bracal
    H.frustum(f, "tan_dk", (s * 0.855, 1.32, 0.13), (s * 0.86, 1.2, 0.15), (0.265, 0.26), (0.265, 0.26), sides=6)
    H.frustum(f, "orange", (s * WR[0], 1.0, 0.2), (s * WR[0], 0.76, 0.27), (0.2, 0.19), (0.17, 0.12), sides=6)    # mao
    for dx in (-0.13, -0.045, 0.045, 0.13):
        H.frustum(f, "claw", (s * (WR[0] + dx), 0.8, 0.25), (s * (WR[0] + dx * 1.3), 0.34, 0.36), (0.035, 0.035), (0.004, 0.004), sides=4)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * 0.34
        H.frustum(f"thigh.{side}", "orange", (s * 0.42, 0.6, -0.04), (x, 1.22, HIP_Z), (0.2, 0.2), (0.27, 0.27), sides=6)
        H.frustum(f"shin.{side}", "bandage", (s * 0.45, 0.2, -0.05), (s * 0.42, 0.66, -0.04), (0.21, 0.22), (0.26, 0.25), sides=6)
        H.frustum(f"shin.{side}", "bandage", (s * 0.45, 0.2, -0.05), (s * 0.45, 0.3, -0.05), (0.24, 0.24), (0.22, 0.22), sides=6)
        H.frustum(f"foot.{side}", "orange_dk", (s * 0.45, 0.11, -0.3), (s * 0.45, 0.11, 0.28), (0.19, 0.12), (0.17, 0.08), sides=6)
        for dx in (-0.09, 0, 0.09):
            H.frustum(f"foot.{side}", "claw", (s * (0.45 + dx), 0.07, 0.3), (s * (0.45 + dx * 1.2), 0.04, 0.46), (0.03, 0.03), (0.004, 0.004), sides=4)


def tail():
    H.chain("pelvis", "orange", [(0, 1.1, -0.35), (0, 0.85, -0.7), (0, 0.55, -0.85), (0, 0.3, -0.8)],
            [(0.13, 0.13), (0.11, 0.11), (0.09, 0.09), (0.12, 0.12)])
    H.frustum("pelvis", "stripe", (0, 0.4, -0.84), (0, 0.15, -0.76), (0.13, 0.13), (0.02, 0.02), sides=6)


def stripes():
    H.frustum("spine", "cream", (0, 1.55, 0.14), (0, 2.1, 0.1), (0.36, 0.3), (0.46, 0.3), sides=6)       # peito creme
    for dz in (0.0,):
        H.frustum("spine", "stripe", (0, 2.2, 0.3), (0, 2.28, 0.2), (0.2, 0.03), (0.3, 0.03), sides=4)
    for s in (-1, 1):
        H.frustum("spine", "stripe", (s * 0.3, 1.95, 0.3), (s * 0.5, 1.75, 0.34), (0.09, 0.04), (0.06, 0.04), sides=4)
        H.frustum("spine", "stripe", (s * 0.3, 1.65, 0.3), (s * 0.5, 1.5, 0.28), (0.09, 0.04), (0.06, 0.04), sides=4)
        H.frustum(f"thigh.{'L' if s > 0 else 'R'}", "stripe", (s * 0.5, 0.9, 0.2), (s * 0.4, 0.7, 0.24), (0.07, 0.04), (0.1, 0.04), sides=4)


def make():
    head()
    tail()
    stripes()
    hat()
    torso()
    legs()
    for s, side in ((1, "L"), (-1, "R")):
        arm(s, side)


def joints():
    out = {"pelvis": ((0, 1.15, HIP_Z), (0, 1.35, -0.2)), "spine": ((0, 1.35, -0.2), (0, 2.0, 0.0)),
           "head": ((0, 2.0, 0.3), (0, 2.3, 0.75))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH[0], SH[1], SH[2]), (s * EL[0], EL[1], EL[2]))
        out[f"forearm.{side}"] = ((s * EL[0], EL[1], EL[2]), (s * WR[0], WR[1], WR[2]))
        out[f"thigh.{side}"] = ((s * 0.34, 1.15, HIP_Z), (s * 0.42, 0.6, -0.04))
        out[f"shin.{side}"] = ((s * 0.42, 0.6, -0.04), (s * 0.45, 0.2, -0.05))
        out[f"foot.{side}"] = ((s * 0.45, 0.2, -0.05), (s * 0.45, 0.08, 0.45))
    return out


H.build("n028", "biped", PALETTE, make, joints())
