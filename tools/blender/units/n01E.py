"""Infernal Tank (n01E, familia vehicle): medido em artifacts/model-sheets/refs/n01E/sheet.jpg (0,0034 m por pixel).

    blender -b --factory-startup -P tools/blender/units/n01E.py -- <out.glb>

Canhao do inferno: casca preta com mascara de olhos verdes, canhao dourado e preto inclinado sobre a casca,
duas rodas grandes douradas com cubo e espinho, placa alta atras, chifres de osso. A familia vehicle nao tem ossos
de roda: as rodas ficam rigidas na espinha. O canhao fica no osso `head`, que recua no disparo.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "black": 0x1C1B20, "black_dk": 0x111114, "gold": 0xE0A82E, "bone": 0xE2DBCC, "green": 0x39F03A, "spoke": 0x7C7B78,
}

WHEEL_R, WHEEL_X, WHEEL_Y = 0.56, 0.76, 0.56
BREECH, MUZZLE = (0, 1.16, -0.34), (0, 1.68, 1.02)


def pod():
    pts = [(0, 0.66, -0.55), (0, 0.66, -0.1), (0, 0.66, 0.35), (0, 0.64, 0.8), (0, 0.58, 0.95)]
    radii = [(0.45, 0.45), (0.68, 0.56), (0.74, 0.58), (0.62, 0.52), (0.44, 0.4)]
    H.chain("hull", "black", pts, radii, sides=8)
    H.frustum("hull", "gold", (0, 0.62, -0.28), (0, 0.62, -0.18), (0.64, 0.5), (0.64, 0.5), sides=8)     # cinta
    H.frustum("hull", "gold", (0, 0.62, 0.42), (0, 0.62, 0.52), (0.7, 0.52), (0.7, 0.52), sides=8)
    H.frustum("hull", "black_dk", (0, 0.52, 0.7), (0, 0.58, 0.95), (0.36, 0.3), (0.3, 0.26), sides=6)   # queixo da mascara
    H.frustum("hull", "gold", (0, 0.32, 0.8), (0, 0.9, 0.92), (0.16, 0.05), (0.38, 0.05), sides=4)     # moldura V
    H.frustum("hull", "green", (0, 0.44, 0.86), (0, 0.66, 0.96), (0.07, 0.03), (0.1, 0.03), sides=4)   # gema
    for s in (-1, 1):
        H.frustum("hull", "green", (s * 0.18, 0.72, 0.84), (s * 0.4, 0.84, 0.88), (0.1, 0.05), (0.07, 0.04), sides=4)
        H.frustum("hull", "gold", (s * 0.4, 0.5, 0.74), (s * 0.58, 0.9, 0.66), (0.05, 0.1), (0.07, 0.12), sides=4)


def plate():
    H.box("hull", "gold", (0, 1.1, -0.6), (0.8, 1.6, 0.1))
    H.box("hull", "black", (0, 1.1, -0.62), (0.64, 1.46, 0.13))
    H.box("hull", "black", (0, 0.5, -0.62), (0.5, 0.3, 0.14))
    for y in (1.5, 1.2, 0.9):
        H.box("hull", "gold", (0, y, -0.69), (0.1, 0.12, 0.03))


def wheel(s):
    bone = "wheel1" if s > 0 else "wheel2"
    c = (s * WHEEL_X, WHEEL_Y, 0.0)
    H.wheel(bone, "gold", c, WHEEL_R, 0.16)
    H.wheel(bone, "black_dk", (c[0] + s * 0.02, c[1], 0), WHEEL_R - 0.09, 0.18)
    for k in range(4):
        a = k * math.pi / 4
        tip = (c[0] + s * 0.1, c[1] + math.sin(a) * 0.42, math.cos(a) * 0.42)
        back = (c[0] + s * 0.1, c[1] - math.sin(a) * 0.42, -math.cos(a) * 0.42)
        H.frustum(bone, "spoke", back, tip, (0.025, 0.04), (0.025, 0.04), sides=4)
    H.wheel(bone, "gold", (c[0] + s * 0.1, c[1], 0), 0.17, 0.22, sides=6)
    H.box(bone, "green", (c[0] + s * 0.14, c[1] + 0.4, 0.0), (0.08, 0.1, 0.1))     # pino fora do centro: mostra o giro
    H.frustum(bone, "bone", (s * (WHEEL_X + 0.12), WHEEL_Y, 0), (s * 1.02, WHEEL_Y, 0), (0.1, 0.1), (0.012, 0.012), sides=6)


def axle():
    H.frustum("hull", "black", (-WHEEL_X, WHEEL_Y, 0.0), (WHEEL_X, WHEEL_Y, 0.0), (0.07, 0.07), (0.07, 0.07), sides=6)


def cannon():
    pts = [BREECH, (0, 1.28, -0.02), (0, 1.5, 0.6), (0, 1.62, 0.9), MUZZLE]
    H.chain("head", "black", pts, [(0.27, 0.27), (0.25, 0.25), (0.21, 0.21), (0.2, 0.2), (0.2, 0.2)], sides=8)
    H.frustum("head", "gold", (0, 1.2, 0.0), (0, 1.3, 0.24), (0.31, 0.31), (0.29, 0.29), sides=8)         # cinta grossa
    H.frustum("head", "gold", (0, 1.64, 0.92), (0, 1.7, 1.06), (0.26, 0.26), (0.27, 0.27), sides=8)     # boca
    H.frustum("head", "gold", (0, 1.66, 0.7), (0, 1.69, 0.78), (0.23, 0.23), (0.23, 0.23), sides=8)
    H.frustum("head", "black_dk", (0, 1.7, 1.06), (0, 1.72, 1.09), (0.17, 0.17), (0.17, 0.17), sides=8)


def horns():
    for s in (-1, 1):
        H.chain("hull", "bone", [(s * 0.45, 1.0, 0.5), (s * 0.78, 1.3, 0.5), (s * 0.68, 1.95, 0.46)],
                [(0.16, 0.12), (0.12, 0.1), (0.015, 0.015)], sides=6)
        for z, h in ((0.5, 0.34), (0.2, 0.3), (-0.1, 0.3)):
            H.frustum("hull", "bone", (s * 0.38, 1.0, z), (s * 0.46, 1.0 + h, z - 0.08), (0.07, 0.07), (0.01, 0.01), sides=4)
    for x, r in ((-0.55, 0.1), (-0.2, 0.09), (0.2, 0.09), (0.55, 0.1)):    # presas na proa
        H.chain("hull", "bone", [(x, 0.45, 0.78), (x * 1.1, 0.3, 1.2), (x * 1.3, 0.12, 1.4), (x * 1.5, 0.02, 1.35)],
                [(r, r), (r * 0.9, r * 0.9), (r * 0.6, r * 0.6), (0.012, 0.012)], sides=6)


def make():
    pod()
    plate()
    axle()
    for s in (-1, 1):
        wheel(s)
    cannon()
    horns()


def joints():
    return {"hull": ((0, 0.65, -0.55), (0, 0.7, 0.8)), "head": (BREECH, (0, 1.3, 0.3)),
            "wheel1": ((WHEEL_X, WHEEL_Y, 0), (WHEEL_X + 0.1, WHEEL_Y, 0)),
            "wheel2": ((-WHEEL_X, WHEEL_Y, 0), (-WHEEL_X - 0.1, WHEEL_Y, 0))}


H.build("n01E", "vehicle", PALETTE, make, joints())
