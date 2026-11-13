"""Brewshock Catapult (o00H): morteiro a vapor, caldeira preta com chaminé sobre duas rodas de madeira e uma cauda,
medido em artifacts/model-sheets/refs/o00H/sheet.jpg (perfil: 0.003 m por pixel exibido; a boca aponta para a esquerda).

    blender -b --factory-startup -P tools/blender/units/o00H.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "black": 0x2A2A2E, "red": 0x9B2128, "tan": 0xB08A55, "tan_dk": 0x8E6B3E, "gold": 0xE3A92B,
    "grey": 0x7C8084, "cream": 0xEFE4C0, "tyre": 0x35333A, "bore": 0x121214,
}

R = 0.5
WX0, WX1 = 0.5, 0.67
BY = 0.95                                   # altura do eixo da caldeira
TUBE_PIVOT = (0.0, 0.85, 0.1)
TUBE_DIR = (0.0, 0.63, 0.77)                # para a frente e para cima (~39 graus)
TUBE_LEN = 0.8


def add(p, d, t):
    return (p[0] + d[0] * t, p[1] + d[1] * t, p[2] + d[2] * t)


def wheel(bone, s):
    a, b = s * WX0, s * WX1
    H.frustum(bone, "tyre", (a, R, 0), (b, R, 0), (R, R), (R, R), sides=12)
    H.frustum(bone, "tan", (a, R, 0), (b + s * 0.015, R, 0), (R * 0.86, R * 0.86), (R * 0.86, R * 0.86), sides=12)
    H.frustum(bone, "tan_dk", (b, R, 0), (b + s * 0.03, R, 0), (R * 0.28, R * 0.28), (R * 0.26, R * 0.26), sides=8)
    H.frustum(bone, "gold", (b + s * 0.02, R, 0), (b + s * 0.07, R, 0), (0.14, 0.14), (0.1, 0.1), sides=8)
    H.frustum(bone, "black", (b + s * 0.06, R, 0), (b + s * 0.08, R, 0), (0.06, 0.06), (0.05, 0.05), sides=6)


def boiler():
    pts = ((0, BY, 0.4), (0, BY, 0.2), (0, BY, 0.0), (0, BY, -0.5), (0, BY, -0.75), (0, BY, -0.9))
    rad = (0.22, 0.31, 0.36, 0.37, 0.34, 0.22)
    H.chain("hull", "black", pts, [(r, r) for r in rad], sides=8)
    for z in (0.0, -0.5):                                   # cintas vermelhas
        H.frustum("hull", "red", (0, BY, z + 0.05), (0, BY, z - 0.05), (0.385, 0.385), (0.385, 0.385), sides=8)
    H.frustum("hull", "gold", (0, BY, -0.88), (0, BY, -0.94), (0.15, 0.15), (0.13, 0.13), sides=8)   # tampa traseira
    H.frustum("hull", "cream", (0, BY + 0.1, -0.9), (0, BY + 0.1, -0.97), (0.14, 0.14), (0.14, 0.14), sides=8)   # manômetro
    H.frustum("hull", "black", (0, 1.2, -0.51), (0, 1.58, -0.51), (0.1, 0.1), (0.085, 0.085), sides=8)         # chaminé
    H.frustum("hull", "gold", (0, 1.56, -0.51), (0, 1.66, -0.51), (0.14, 0.14), (0.15, 0.15), sides=8)
    H.frustum("hull", "gold", (0, 1.28, -0.22), (0, 1.4, -0.22), (0.03, 0.03), (0.03, 0.03), sides=6)       # válvula
    H.frustum("hull", "gold", (-0.11, 1.42, -0.22), (0.11, 1.42, -0.22), (0.025, 0.025), (0.025, 0.025), sides=6)


def carriage():
    for s in (-1, 1):
        pts = ((s * 0.4, 0.78, 0.4), (s * 0.4, 0.5, 0.1), (s * 0.4, 0.34, -0.6), (s * 0.4, 0.34, -1.15))
        H.chain("hull", "tan", pts, [(0.07, 0.1), (0.07, 0.12), (0.07, 0.12), (0.07, 0.1)], sides=4)
    H.box("hull", "tan", (0, 0.5, 0.42), (0.9, 0.34, 0.1))                    # tábua da frente
    H.box("hull", "tan_dk", (0, 0.32, -0.95), (0.86, 0.2, 0.42))               # base da cauda
    H.box("hull", "red", (0, 0.3, 0.3), (0.74, 0.14, 0.3))
    H.box("hull", "red", (0, 0.5, -1.0), (0.26, 0.1, 0.22))                   # bloco na cauda
    H.frustum("hull", "black", (0, 0.0, -1.08), (0, 0.3, -1.08), (0.07, 0.07), (0.09, 0.09), sides=6)     # pé de trás
    H.frustum("hull", "black", (-0.62, R, 0), (0.62, R, 0), (0.05, 0.05), (0.05, 0.05), sides=6)           # eixo


def tube():
    base = TUBE_PIVOT
    tip = add(base, TUBE_DIR, TUBE_LEN)
    H.frustum("head", "grey", base, tip, (0.25, 0.25), (0.26, 0.26), sides=8)
    H.frustum("head", "gold", add(tip, TUBE_DIR, -0.04), add(tip, TUBE_DIR, 0.07), (0.31, 0.31), (0.33, 0.33), sides=8)
    H.frustum("head", "bore", add(tip, TUBE_DIR, 0.05), add(tip, TUBE_DIR, 0.075), (0.2, 0.2), (0.2, 0.2), sides=8)
    H.frustum("head", "black", add(base, TUBE_DIR, 0.0), add(base, TUBE_DIR, 0.2), (0.3, 0.3), (0.27, 0.27), sides=8)   # colar


def make():
    boiler()
    carriage()
    tube()
    wheel("wheel1", 1)
    wheel("wheel2", -1)


def joints():
    return {
        "head": (TUBE_PIVOT, (TUBE_PIVOT[0], TUBE_PIVOT[1], TUBE_PIVOT[2] + 0.5)),
        "wheel1": ((WX0, R, 0), (WX1, R, 0)), "wheel2": ((-WX0, R, 0), (-WX1, R, 0)),
        "wheel3": ((0.4, 0.2, -0.95), (0.5, 0.2, -0.95)), "wheel4": ((-0.4, 0.2, -0.95), (-0.5, 0.2, -0.95)),
    }


H.build("o00H", "vehicle", PALETTE, make, joints())
