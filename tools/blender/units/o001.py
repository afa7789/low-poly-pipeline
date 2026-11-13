"""Catapult (o001): carroça de telhado preto com braço de arremesso e caldeirão em chamas atrás,
medido em artifacts/model-sheets/refs/o001/sheet.jpg (perfil: 0.0036 m por pixel exibido; a proa e a esquerda).

    blender -b --factory-startup -P tools/blender/units/o001.py -- <out.glb>
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "black": 0x262424, "black_dk": 0x181616, "brown": 0x5E2E26, "rust": 0x8E3C28, "tyre": 0x40353A,
    "orange": 0xF08A1E, "yellow": 0xFFB840, "wood_dk": 0x4A2A24,
}

R = 0.31
WX0, WX1 = 0.62, 0.8
AXLES = (("wheel1", "wheel2", 0.63), ("wheel3", "wheel4", -0.67))
PIVOT = (0.0, 1.34, -0.04)
ARM = ((0, 1.34, -0.08), (0, 1.34, -0.38), (0, 1.5, -0.6), (0, 1.68, -0.82), (0, 1.62, -0.92))
ARM_R = ((0.1, 0.1), (0.09, 0.08), (0.08, 0.07), (0.08, 0.07), (0.08, 0.07))
CUP = (0, 1.64, -0.98)


def wheel(bone, s, z):
    a, b = s * WX0, s * WX1
    H.frustum(bone, "tyre", (a, R, z), (b, R, z), (R, R), (R, R), sides=10)
    H.frustum(bone, "wood_dk", (b - s * 0.03, R, z), (b + s * 0.03, R, z), (R * 0.84, R * 0.84), (R * 0.84, R * 0.84), sides=10)
    H.frustum(bone, "rust", (b, R, z), (b + s * 0.07, R, z), (0.1, 0.1), (0.08, 0.08), sides=6)
    for k in range(4):
        ang = k * math.pi / 2 + math.pi / 4
        tip = (b + s * 0.04, R + R * 0.78 * math.sin(ang), z + R * 0.78 * math.cos(ang))
        H.frustum(bone, "brown", (b + s * 0.03, R, z), tip, (0.035, 0.05), (0.03, 0.04), sides=4)


def body():
    H.box("hull", "black_dk", (0, 0.3, -0.05), (1.0, 0.14, 2.0))                     # chassi
    H.box("hull", "black", (0, 0.5, -0.05), (1.3, 0.3, 1.8))                         # caixa
    for s in (-1, 1):
        H.frustum("hull", "rust", (s * 0.66, 0.3, 0.9), (s * 0.7, 0.72, 0.92), (0.05, 0.07), (0.06, 0.07), sides=4)   # postes
        H.frustum("hull", "rust", (s * 0.66, 0.3, -1.0), (s * 0.7, 0.72, -1.0), (0.05, 0.07), (0.06, 0.07), sides=4)
        for z in (0.63, -0.67):
            H.box("hull", "rust", (s * 0.52, 0.34, z), (0.16, 0.22, 0.2))             # calços do eixo
    for _, _, z in AXLES:
        H.frustum("hull", "brown", (-0.9, R, z), (0.9, R, z), (0.05, 0.05), (0.05, 0.05), sides=6)
    # telhado piramidal de beiral largo
    H.frustum("hull", "black", (0, 0.68, -0.02), (0, 0.74, -0.02), (0.8, 1.17), (0.78, 1.14), sides=4)
    H.frustum("hull", "black", (0, 0.72, -0.02), (0, 1.26, -0.06), (0.77, 1.15), (0.16, 0.22), sides=4)
    H.box("hull", "rust", (0, 1.3, -0.04), (0.36, 0.18, 0.38))                      # cume
    H.frustum("hull", "orange", (0, 1.2, -0.3), (0, 0.78, -1.05), (0.1, 0.02), (0.26, 0.02), sides=4)  # veio de brasa atrás


def torches():
    for sx in (-1, 1):
        for z in (1.0, -1.0):
            x = sx * 0.76
            H.frustum("hull", "rust", (sx * 0.68, 0.7, z), (x + sx * 0.08, 0.98, z), (0.05, 0.05), (0.07, 0.07), sides=6)
            H.frustum("hull", "orange", (x + sx * 0.08, 0.98, z), (x + sx * 0.16, 1.28, z), (0.13, 0.13), (0.02, 0.02), sides=6)
            H.frustum("hull", "yellow", (x + sx * 0.08, 0.98, z), (x + sx * 0.12, 1.14, z), (0.08, 0.08), (0.01, 0.01), sides=6)


def arm():
    H.box("head", "rust", PIVOT, (0.32, 0.3, 0.36))                                  # cubo do eixo
    H.chain("head", "brown", ARM, ARM_R, sides=6)
    x, y, z = CUP
    H.frustum("head", "black_dk", (x, y - 0.26, z), (x, y + 0.02, z), (0.14, 0.14), (0.36, 0.36), sides=8)       # cuba
    H.frustum("head", "rust", (x, y - 0.08, z), (x, y + 0.06, z), (0.38, 0.38), (0.37, 0.37), sides=8)         # cinta
    H.frustum("head", "orange", (x, y + 0.04, z), (x, y + 0.1, z), (0.3, 0.3), (0.32, 0.32), sides=8)         # brasa
    for dx, dz, h in ((0, 0, 0.44), (-0.17, 0.05, 0.3), (0.17, -0.05, 0.3)):      # línguas de chama
        H.frustum("head", "orange", (x + dx, y + 0.08, z + dz), (x + dx * 1.3, y + 0.08 + h, z + dz), (0.2, 0.2), (0.03, 0.03), sides=6)
    H.frustum("head", "yellow", (x, y + 0.1, z), (x, y + 0.32, z), (0.16, 0.16), (0.03, 0.03), sides=6)
    H.frustum("head", "orange", (x, y - 0.1, z - 0.36), (x, y - 0.5, z - 0.38), (0.07, 0.07), (0.03, 0.03), sides=6)  # pingo


def make():
    body()
    torches()
    arm()
    for bl, br, z in AXLES:
        wheel(bl, 1, z)
        wheel(br, -1, z)


def joints():
    out = {"head": (PIVOT, (PIVOT[0], PIVOT[1], PIVOT[2] + 0.5))}
    for bl, br, z in AXLES:
        out[bl] = ((WX0, R, z), (WX1, R, z))
        out[br] = ((-WX0, R, z), (-WX1, R, z))
    return out


H.build("o001", "vehicle", PALETTE, make, joints())
