"""Rocket Tank (h098): tanque de rodas com leao na proa e lancador de 6 foguetes, medido em
artifacts/model-sheets/refs/h098/sheet.jpg (perfil: 0.003 m por pixel).

    blender -b --factory-startup -P tools/blender/units/h098.py -- <out.glb>
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "gold": 0xC79A3C, "yellow": 0xE6BC2E, "red": 0x8A1A24, "black": 0x222020, "grey": 0x80807F, "grey_lt": 0xA9A8A6,
    "orange": 0xD8662E, "orange_dk": 0xA84A1E, "blue_dk": 0x3A4F86, "tan": 0xB07B45, "mane": 0x8B5A2B,
    "eye": 0x39B7FF, "tube_in": 0x3A2A1A,
}

R = 0.37
WX0, WX1 = 0.5, 0.76
AXLES = (("wheel1", "wheel2", 0.44), ("wheel3", "wheel4", -0.44))
PIVOT = (0.0, 1.0, -0.15)
POD_DIR = (0.0, 0.62, 0.78)          # eixo dos tubos: sobe para a frente
POD_LEN = 0.85


def wheel(bone, s, z):
    a, b = s * WX0, s * WX1
    H.frustum(bone, "grey", (a, R, z), (b, R, z), (R, R), (R, R), sides=10)
    H.frustum(bone, "grey_lt", (b - s * 0.04, R, z), (b, R, z), (R * 1.01, R * 1.01), (R * 1.01, R * 1.01), sides=10)
    H.frustum(bone, "red", (b, R, z), (b + s * 0.03, R, z), (R * 0.76, R * 0.76), (R * 0.76, R * 0.76), sides=10)
    H.frustum(bone, "gold", (b + s * 0.02, R, z), (b + s * 0.07, R, z), (0.08, 0.08), (0.08, 0.08), sides=6)
    for k in range(6):
        ang = k * math.pi / 3
        tip = (b + s * 0.04, R + R * 0.74 * math.sin(ang), z + R * 0.74 * math.cos(ang))
        H.frustum(bone, "gold", (b + s * 0.025, R, z), tip, (0.016, 0.04), (0.016, 0.03), sides=4)


def chassis():
    H.box("hull", "black", (0, 0.3, -0.05), (0.8, 0.14, 1.3))
    for _, _, z in AXLES:
        H.frustum("hull", "grey", (-0.52, R, z), (0.52, R, z), (0.06, 0.06), (0.06, 0.06), sides=6)
        H.frustum("hull", "grey", (0, 0.3, z), (0, 0.42, z), (0.18, 0.1), (0.1, 0.08), sides=6)
    H.box("hull", "red", (0, 0.55, -0.05), (0.88, 0.58, 1.3))
    H.box("hull", "black", (0, 0.86, -0.05), (0.8, 0.04, 1.2))
    for s in (-1, 1):
        H.box("hull", "gold", (s * 0.46, 0.86, -0.05), (0.06, 0.06, 1.34))
        H.box("hull", "gold", (s * 0.46, 0.55, 0.0), (0.07, 0.04, 1.2))
    H.box("hull", "gold", (0, 0.86, -0.7), (0.95, 0.07, 0.06))
    H.box("hull", "gold", (0, 0.86, 0.6), (0.95, 0.07, 0.06))
    H.box("hull", "gold", (0, 0.55, -0.71), (0.9, 0.58, 0.04))
    H.box("hull", "grey_lt", (0, 0.55, -0.74), (0.7, 0.4, 0.03))


def lion():
    H.frustum("hull", "mane", (0, 0.52, 0.55), (0, 0.52, 0.72), (0.47, 0.44), (0.44, 0.4), sides=8)
    H.frustum("hull", "tan", (0, 0.5, 0.72), (0, 0.48, 0.86), (0.37, 0.36), (0.31, 0.32), sides=8)
    H.frustum("hull", "tan", (0, 0.4, 0.84), (0, 0.37, 1.04), (0.19, 0.16), (0.15, 0.11), sides=6)         # focinho
    H.frustum("hull", "black", (0, 0.45, 1.0), (0, 0.46, 1.07), (0.07, 0.04), (0.05, 0.03), sides=4)
    H.frustum("hull", "mane", (0, 0.66, 0.84), (0, 0.66, 0.97), (0.34, 0.07), (0.3, 0.06), sides=4)       # sobrancelha
    for s in (-1, 1):
        H.frustum("hull", "eye", (s * 0.17, 0.58, 0.86), (s * 0.17, 0.57, 0.92), (0.07, 0.04), (0.05, 0.03), sides=6)
        H.frustum("hull", "mane", (s * 0.4, 0.78, 0.6), (s * 0.32, 0.92, 0.66), (0.1, 0.1), (0.07, 0.07), sides=6)   # orelha
    for x, z in ((-0.3, 0.8), (0.0, 0.88), (0.3, 0.8)):      # espinhos pretos sob o queixo
        H.frustum("hull", "black", (x, 0.26, z), (x * 1.05, 0.0, z + 0.1), (0.06, 0.06), (0.01, 0.01), sides=4)


def barrels_and_pipes():
    for s in (-1, 1):
        H.frustum("hull", "orange", (s * 0.5, 1.07, -0.5), (s * 0.5, 1.07, -0.1), (0.15, 0.15), (0.15, 0.15), sides=8)
        for z in (-0.46, -0.14):
            H.frustum("hull", "orange_dk", (s * 0.5, 1.07, z - 0.02), (s * 0.5, 1.07, z + 0.02), (0.165, 0.165), (0.165, 0.165), sides=8)
        H.frustum("hull", "grey", (s * 0.15, 0.9, -0.6), (s * 0.28, 1.25, -0.74), (0.07, 0.07), (0.07, 0.07), sides=6)
        H.frustum("hull", "black", (s * 0.28, 1.25, -0.74), (s * 0.4, 1.58, -0.86), (0.07, 0.07), (0.09, 0.09), sides=6)


def add(p, d, t):
    return (p[0] + d[0] * t, p[1] + d[1] * t, p[2] + d[2] * t)


def pod():
    base = (0.0, 1.02, -0.2)
    n = (0.0, POD_DIR[2], -POD_DIR[1])       # normal ao eixo, no plano y-z
    for row in (-1, 1):
        for x in (-0.19, 0.0, 0.19):
            a = add(base, n, row * 0.1)
            a = (a[0] + x, a[1], a[2])
            b = add(a, POD_DIR, POD_LEN)
            H.frustum("head", "gold", a, b, (0.095, 0.095), (0.095, 0.095), sides=8)
            H.frustum("head", "tube_in", b, add(b, POD_DIR, 0.025), (0.07, 0.07), (0.07, 0.07), sides=6)
    under = add(base, n, -0.19)
    H.frustum("head", "blue_dk", under, add(under, POD_DIR, POD_LEN), (0.32, 0.04), (0.32, 0.04), sides=4)
    mid = add(base, POD_DIR, POD_LEN * 0.45)
    H.frustum("head", "yellow", mid, add(mid, POD_DIR, 0.1), (0.31, 0.21), (0.31, 0.21), sides=4)
    H.frustum("head", "black", (0, 0.88, -0.2), (0, 1.1, -0.2), (0.27, 0.16), (0.22, 0.12), sides=6)    # berco
    H.frustum("head", "yellow", (-0.28, 1.0, -0.2), (0.28, 1.0, -0.2), (0.05, 0.05), (0.05, 0.05), sides=6)


def make():
    chassis()
    lion()
    barrels_and_pipes()
    pod()
    for bl, br, z in AXLES:
        wheel(bl, 1, z)
        wheel(br, -1, z)


def joints():
    out = {"head": (PIVOT, (PIVOT[0], PIVOT[1], PIVOT[2] + 0.5))}
    for bl, br, z in AXLES:
        out[bl] = ((WX0, R, z), (WX1, R, z))
        out[br] = ((-WX0, R, z), (-WX1, R, z))
    return out


H.build("h098", "vehicle", PALETTE, make, joints())
