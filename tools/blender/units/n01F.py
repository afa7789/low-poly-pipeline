"""Infernal Machine (n01F, familia vehicle): canhao infernal de casco preto ovoide sobre rodas douradas, garras e chifres de osso.

    blender -b --factory-startup -P tools/blender/units/n01F.py -- <out.glb>

Medido em artifacts/model-sheets/refs/n01F/sheet.jpg (perfil: 0,0033 m por pixel, roda no z = 0). A familia vehicle tem
ossos de roda: cada roda tem seu osso (wheel1/wheel2); o canhao, grande e erguido, fica no osso head (o que se mexe no tiro).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "black": 0x1E1F24, "black_dk": 0x14151A, "gold": 0xE0AE2A, "bone": 0xE3DDCE, "green": 0x4CF03C,
    "grey": 0x7C7E82,
}

BODY_Y = 0.7
BODY_Z = [-0.75, -0.42, -0.04, 0.34, 0.68]
BODY_RX = [0.4, 0.6, 0.65, 0.55, 0.25]
BODY_RY = [0.4, 0.52, 0.52, 0.45, 0.2]
WHEEL_X, WHEEL_R, WHEEL_Y = 0.86, 0.57, 0.58


def fr(bone, tone, a, b, ra, rb, sides=8):
    H.frustum(bone, tone, a, b, ra if isinstance(ra, tuple) else (ra, ra), rb if isinstance(rb, tuple) else (rb, rb), sides)


def body():
    for i in range(4):
        fr("hull", "black", (0, BODY_Y, BODY_Z[i]), (0, BODY_Y, BODY_Z[i + 1]), (BODY_RX[i], BODY_RY[i]), (BODY_RX[i + 1], BODY_RY[i + 1]))
    for i in (1, 2):    # cintas douradas atravessando o casco
        z = -0.55 if i == 1 else -0.15
        fr("hull", "gold", (0, BODY_Y, z - 0.04), (0, BODY_Y, z + 0.04), (0.64, 0.56), (0.64, 0.56))
    fr("hull", "gold", (0, 0.93, 0.3), (0, 0.93, 0.6), (0.5, 0.05), (0.34, 0.05), sides=4)    # gola dourada na frente
    fr("hull", "green", (0, 0.55, 0.62), (0, 0.65, 0.7), (0.08, 0.12), (0.06, 0.1), sides=6)     # joia
    for s in (-1, 1):
        fr("hull", "green", (s * 0.18, 0.85, 0.5), (s * 0.4, 0.95, 0.4), (0.06, 0.05), (0.14, 0.05), sides=4)   # olhos


def wheels():
    fr("hull", "black_dk", (-WHEEL_X, WHEEL_Y, 0), (WHEEL_X, WHEEL_Y, 0), 0.07, 0.07, sides=6)
    for s in (-1, 1):
        bone = "wheel1" if s > 0 else "wheel2"
        a, b = s * (WHEEL_X - 0.08), s * (WHEEL_X + 0.08)
        fr(bone, "gold", (a, WHEEL_Y, 0), (b, WHEEL_Y, 0), WHEEL_R, WHEEL_R, sides=12)
        fr(bone, "black", (a, WHEEL_Y, 0), (b + s * 0.02, WHEEL_Y, 0), WHEEL_R - 0.09, WHEEL_R - 0.09, sides=12)
        for dy, dz in ((0.46, 0), (0, 0.46), (0.33, 0.33), (0.33, -0.33)):
            fr(bone, "grey", (b + s * 0.03, WHEEL_Y - dy, -dz), (b + s * 0.03, WHEEL_Y + dy, dz), (0.025, 0.04), (0.025, 0.04), sides=4)
        fr(bone, "gold", (b, WHEEL_Y, 0), (b + s * 0.06, WHEEL_Y, 0), 0.14, 0.12, sides=8)
        H.box(bone, "green", (b + s * 0.05, WHEEL_Y + 0.4, 0.0), (0.08, 0.1, 0.1))    # pino fora do centro: mostra o giro
        fr(bone, "bone", (b + s * 0.05, WHEEL_Y, 0), (b + s * 0.3, WHEEL_Y, 0), 0.1, 0.01, sides=6)


def horns():
    for s in (-1, 1):
        pts = [(s * 0.5, 1.05, 0.12), (s * 0.68, 1.3, 0.1), (s * 0.74, 1.58, 0.06), (s * 0.62, 1.85, 0.0)]
        H.chain("hull", "bone", pts, [(0.13, 0.13), (0.11, 0.11), (0.08, 0.08), (0.01, 0.01)])
        fr("hull", "gold", (s * 0.46, 0.98, 0.12), (s * 0.54, 1.1, 0.12), 0.16, 0.14, sides=6)


def claws():
    for s in (-1, 1):
        for x, drop in ((0.15, 0.0), (0.4, 0.05), (0.65, 0.1)):
            pts = [(s * x, 0.5, 0.55), (s * (x + 0.08), 0.3 - drop, 0.9), (s * (x + 0.12), 0.1, 1.12), (s * (x + 0.1), 0.2, 1.3)]
            H.chain("hull", "bone", pts, [(0.08, 0.08), (0.07, 0.07), (0.05, 0.05), (0.01, 0.01)])
        fr("hull", "gold", (s * 0.3, 0.5, 0.52), (s * 0.5, 0.52, 0.6), 0.1, 0.1, sides=6)


def shield():
    fr("hull", "gold", (0, 0.8, -0.64), (0, 1.95, -0.64), (0.4, 0.04), (0.4, 0.04), sides=4)
    fr("hull", "black_dk", (0, 0.85, -0.7), (0, 1.9, -0.7), (0.34, 0.05), (0.34, 0.05), sides=4)
    for dy in (0.95, 1.3, 1.65):
        fr("hull", "gold", (0, dy - 0.08, -0.77), (0, dy + 0.08, -0.77), (0.07, 0.02), (0.07, 0.02), sides=4)


def cannon():
    fr("head", "black_dk", (0, 1.1, -0.55), (0, 1.15, -0.45), 0.3, 0.3, sides=8)       # culatra
    fr("head", "black", (0, 1.13, -0.5), (0, 1.62, 0.78), 0.26, 0.24)
    fr("head", "gold", (0, 1.28, -0.2), (0, 1.3, -0.1), 0.3, 0.3, sides=8)
    fr("head", "gold", (0, 1.52, 0.5), (0, 1.58, 0.62), 0.28, 0.28, sides=8)
    fr("head", "gold", (0, 1.6, 0.74), (0, 1.69, 0.95), 0.34, 0.32, sides=8)        # boca
    fr("head", "black_dk", (0, 1.62, 0.9), (0, 1.7, 0.97), 0.24, 0.24, sides=8)


def make():
    body()
    wheels()
    horns()
    claws()
    shield()
    cannon()


def joints():
    return {"head": ((0, 1.15, -0.5), (0, 1.2, -0.15)),
            "hull": ((0, BODY_Y, BODY_Z[0]), (0, BODY_Y, BODY_Z[-1])),
            "wheel1": ((WHEEL_X, WHEEL_Y, 0), (WHEEL_X + 0.1, WHEEL_Y, 0)),
            "wheel2": ((-WHEEL_X, WHEEL_Y, 0), (-WHEEL_X - 0.1, WHEEL_Y, 0))}


H.build("n01F", "vehicle", PALETTE, make, joints())
