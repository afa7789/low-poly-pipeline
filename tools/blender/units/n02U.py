"""Razormane (n02U): medido em artifacts/model-sheets/refs/n02U/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n02U.py -- <out.glb>

Javali em pe, bruto: ombros enormes, barriga, juba vermelha com espinhos cinza, clava na mao direita
(da unidade), cauda com chama.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "skin": 0xDDA866, "belly": 0xECC99C, "mane": 0x6E0F1C, "horn": 0x8A8C92, "hoof": 0x2C1E1E,
    "leg": 0x9A5C4E, "snout": 0xB07272, "tusk": 0xEFE0C0, "club": 0x4A3024, "band": 0x3E3E42,
    "flame": 0xFF7A1E, "ear": 0x8A6A4A,
}

SH, EL, WR = (0.6, 1.74, 0.0), (0.72, 1.2, 0.05), (0.62, 0.76, 0.12)
HIP, KNEE, ANKLE = 0.9, 0.46, 0.14
# clava: cabo para cima da mao, cabeca para baixo e para a frente
BUTT, END = (-0.62, 1.3, -0.1), (-0.62, 0.05, 0.4)


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def head():
    H.frustum("head", "skin", (0, 2.0, 0.15), (0, 2.2, 0.55), (0.34, 0.32), (0.3, 0.28), sides=8)
    H.frustum("head", "skin", (0, 2.08, 0.45), (0, 1.97, 0.95), (0.22, 0.2), (0.17, 0.15), sides=8)
    H.frustum("head", "snout", (0, 1.97, 0.93), (0, 1.94, 1.05), (0.18, 0.16), (0.16, 0.14), sides=8)
    H.frustum("head", "band", (0, 2.28, 0.5), (0, 2.38, 0.46), (0.3, 0.14), (0.3, 0.14), sides=4)
    H.frustum("head", "mane", (0, 2.2, 0.05), (0, 2.5, -0.15), (0.24, 0.22), (0.14, 0.12), sides=6)
    for s in (-1, 1):
        H.chain("head", "tusk", [(s * 0.15, 1.88, 0.78), (s * 0.27, 1.95, 0.93), (s * 0.24, 2.17, 0.93)],
                [(0.06, 0.06), (0.05, 0.05), (0.01, 0.01)], sides=4)
        H.chain("head", "horn", [(s * 0.28, 2.2, 0.2), (s * 0.48, 2.4, 0.15), (s * 0.44, 2.66, 0.08)],
                [(0.1, 0.09), (0.07, 0.06), (0.01, 0.01)], sides=4)
        H.frustum("head", "ear", (s * 0.22, 2.3, 0.25), (s * 0.3, 2.48, 0.2), (0.1, 0.04), (0.02, 0.01), sides=4)


def torso():
    H.frustum("spine", "skin", (0, 0.75, 0), (0, 1.3, 0.05), (0.42, 0.36), (0.52, 0.42), sides=8)
    H.frustum("spine", "belly", (0, 0.8, 0.3), (0, 1.3, 0.34), (0.3, 0.16), (0.34, 0.16), sides=8)
    H.frustum("spine", "skin", (0, 1.25, 0.02), (0, 1.8, 0.1), (0.5, 0.4), (0.64, 0.44), sides=8)
    H.frustum("spine", "skin", (0, 1.8, 0.1), (0, 2.05, 0.15), (0.64, 0.44), (0.34, 0.3), sides=8)
    H.frustum("spine", "mane", (0, 1.35, -0.38), (0, 2.1, -0.34), (0.28, 0.12), (0.5, 0.15), sides=6)
    for y, z in ((2.02, -0.3), (1.78, -0.4), (1.5, -0.44)):
        H.frustum("spine", "horn", (0, y, z), (0, y + 0.2, z - 0.55), (0.09, 0.08), (0.01, 0.01), sides=4)
    H.frustum("pelvis", "skin", (0, 0.7, 0), (0, 1.0, 0), (0.42, 0.36), (0.44, 0.38), sides=8)
    H.chain("pelvis", "skin", [(0, 0.95, -0.38), (0, 0.85, -0.62), (0, 0.55, -0.7), (0, 0.35, -0.66)],
            [(0.07, 0.07), (0.06, 0.06), (0.05, 0.05), (0.03, 0.03)], sides=6)
    H.frustum("pelvis", "flame", (0, 0.36, -0.66), (0, 0.1, -0.6), (0.1, 0.03), (0.01, 0.01), sides=4)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        H.frustum(f"thigh.{side}", "skin", (s * 0.3, KNEE, 0.04), (s * 0.28, HIP + 0.1, 0), (0.25, 0.25), (0.33, 0.33), sides=8)
        H.frustum(f"shin.{side}", "leg", (s * 0.3, 0.12, -0.02), (s * 0.3, KNEE + 0.06, 0.04), (0.2, 0.2), (0.27, 0.27), sides=8)
        H.frustum(f"foot.{side}", "hoof", (s * 0.3, 0.12, -0.08), (s * 0.3, 0.08, 0.1), (0.2, 0.12), (0.2, 0.1), sides=6)
        H.frustum(f"foot.{side}", "hoof", (s * 0.3, 0.1, 0.05), (s * 0.3, 0.06, 0.46), (0.2, 0.1), (0.14, 0.06), sides=6)


def arms():
    for s, side in ((1, "L"), (-1, "R")):
        H.frustum(f"arm.{side}", "skin", (s * 0.45, 1.85, 0), (s * 0.62, 1.8, 0.02), (0.26, 0.26), (0.3, 0.3), sides=8)
        H.frustum(f"arm.{side}", "skin", (s * SH[0], SH[1], SH[2]), (s * EL[0], EL[1], EL[2]), (0.28, 0.27), (0.23, 0.22), sides=8)
        H.frustum(f"forearm.{side}", "skin", (s * EL[0], EL[1] + 0.05, EL[2]), (s * WR[0], WR[1] + 0.05, WR[2]), (0.24, 0.23), (0.27, 0.26), sides=8)
        H.frustum(f"forearm.{side}", "skin", (s * WR[0], WR[1] + 0.05, WR[2]), (s * WR[0], WR[1] - 0.25, WR[2] + 0.02), (0.27, 0.25), (0.2, 0.18), sides=8)


def club():
    grip, head_start = lerp(BUTT, END, 0.0), lerp(BUTT, END, 0.72)
    H.frustum("forearm.R", "club", grip, head_start, (0.065, 0.065), (0.1, 0.1), sides=6)
    H.frustum("forearm.R", "club", head_start, END, (0.14, 0.14), (0.22, 0.22), sides=8)
    H.frustum("forearm.R", "band", lerp(BUTT, END, 0.74), lerp(BUTT, END, 0.79), (0.17, 0.17), (0.18, 0.18), sides=8)
    H.frustum("forearm.R", "band", lerp(BUTT, END, 0.93), lerp(BUTT, END, 0.98), (0.23, 0.23), (0.24, 0.24), sides=8)


def make():
    head()
    torso()
    legs()
    arms()
    club()


def joints():
    out = {"pelvis": ((0, HIP - 0.05, 0), (0, 1.15, 0)), "spine": ((0, 1.15, 0), (0, 1.85, 0.1)),
           "head": ((0, 1.85, 0.2), (0, 2.2, 0.8))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH[0], SH[1], SH[2]), (s * EL[0], EL[1], EL[2]))
        out[f"forearm.{side}"] = ((s * EL[0], EL[1], EL[2]), (s * WR[0], WR[1], WR[2]))
        out[f"thigh.{side}"] = ((s * 0.28, HIP, 0), (s * 0.3, KNEE, 0.04))
        out[f"shin.{side}"] = ((s * 0.3, KNEE, 0.04), (s * 0.3, ANKLE, -0.02))
        out[f"foot.{side}"] = ((s * 0.3, ANKLE, -0.02), (s * 0.3, 0.06, 0.4))
    return out


H.build("n02U", "biped", PALETTE, make, joints())
