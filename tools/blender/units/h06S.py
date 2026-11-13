"""Heavy Tank (h06S): medido em artifacts/model-sheets/refs/h06S/sheet.jpg (perfil: 0.0036 m por pixel exibido;
z = 0 entre os dois eixos, rosto de pedra na frente).

    blender -b --factory-startup -P tools/blender/units/h06S.py -- <out.glb>
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "gold": 0xC99A3E, "red": 0x8A1C22, "black": 0x222120, "grey": 0x8A8886, "grey_dk": 0x66635F,
    "stone": 0x9A6B3A, "stone_dk": 0x6E4A26, "blue": 0x3E5C92, "orange": 0xC8602E, "orange_dk": 0x8E4220,
    "eye": 0x40C8FF, "steel": 0x77736E, "bore": 0x111111,
}

HALF_W = 0.6                        # meia largura do casco (moldura dourada)
WHEEL_X0, WHEEL_X1 = 0.6, 0.91      # face interna / externa do pneu
WHEEL_R = 0.46
AXLES = (0.53, -0.53)               # z dos dois eixos
HULL_FRONT, HULL_REAR = 0.68, -0.84
HC = (HULL_FRONT + HULL_REAR) / 2
CANNON_Y = 1.42


def wheel(bone, s, z):
    """Pneu cinza, disco dourado por fora com cubo e oito raios; o aro cinza aparece de perfil."""
    r, y = WHEEL_R, WHEEL_R
    a, b = s * WHEEL_X0, s * WHEEL_X1
    H.frustum(bone, "grey", (a, y, z), (b, y, z), (r, r), (r, r), sides=12)
    H.frustum(bone, "red", (b, y, z), (b + s * 0.025, y, z), (r * 0.78, r * 0.78), (r * 0.78, r * 0.78), sides=12)
    H.frustum(bone, "gold", (b + s * 0.02, y, z), (b + s * 0.09, y, z), (r * 0.24, r * 0.24), (r * 0.2, r * 0.2), sides=8)
    for k in range(8):
        ang = k * math.pi / 4
        tip = (b + s * 0.05, y + r * 0.72 * math.sin(ang), z + r * 0.72 * math.cos(ang))
        H.frustum(bone, "gold", (b + s * 0.02, y, z), tip, (0.02, 0.05), (0.02, 0.05), sides=4)


def chassis():
    H.box("hull", "red", (0, 0.65, HC), (2 * HALF_W - 0.08, 0.8, HULL_FRONT - HULL_REAR - 0.04))
    H.box("hull", "black", (0, 1.11, HC), (2 * HALF_W - 0.1, 0.1, HULL_FRONT - HULL_REAR - 0.1))
    for s in (-1, 1):
        H.box("hull", "gold", (s * HALF_W, 1.06, HC), (0.08, 0.1, HULL_FRONT - HULL_REAR))
        H.box("hull", "gold", (s * HALF_W, 0.62, HC), (0.08, 0.1, HULL_FRONT - HULL_REAR))
        H.box("hull", "gold", (s * HALF_W, 0.3, HC), (0.08, 0.08, HULL_FRONT - HULL_REAR))
    H.box("hull", "gold", (0, 0.66, HULL_REAR - 0.02), (2 * HALF_W, 0.84, 0.05))
    H.box("hull", "grey", (0, 0.66, HULL_REAR - 0.06), (0.86, 0.6, 0.05))
    for z in AXLES:
        H.frustum("hull", "steel", (-0.7, WHEEL_R, z), (0.7, WHEEL_R, z), (0.06, 0.06), (0.06, 0.06), sides=6)


def tanks():
    for s in (-1, 1):
        H.frustum("hull", "orange", (s * 0.6, 1.24, -0.68), (s * 0.6, 1.24, -0.12), (0.2, 0.2), (0.2, 0.2), sides=6)
        for z in (-0.58, -0.22):
            H.frustum("hull", "orange_dk", (s * 0.6, 1.24, z - 0.03), (s * 0.6, 1.24, z + 0.03), (0.215, 0.215), (0.215, 0.215), sides=6)


def exhausts():
    for s in (-1, 1):
        pts = [(s * 0.2, 1.08, -0.68), (s * 0.34, 1.5, -0.86), (s * 0.48, 1.88, -1.02)]
        radii = [(0.08, 0.08), (0.1, 0.1), (0.14, 0.14)]
        H.chain("hull", "grey", pts[:2], radii[:2], sides=6)
        H.chain("hull", "black", pts[1:], radii[1:], sides=6)


def face():
    H.frustum("hull", "stone", (0, 0.7, 0.6), (0, 0.7, 0.98), (0.54, 0.44), (0.47, 0.4), sides=8)
    H.frustum("hull", "stone_dk", (0, 1.0, 0.9), (0, 1.0, 1.12), (0.46, 0.08), (0.42, 0.05), sides=4)      # sobrancelha
    H.frustum("hull", "stone", (0, 0.74, 0.92), (0, 0.6, 1.28), (0.1, 0.16), (0.1, 0.08), sides=6)       # nariz
    for s in (-1, 1):
        H.frustum("hull", "stone", (s * 0.32, 0.55, 0.9), (s * 0.32, 0.5, 1.12), (0.16, 0.14), (0.2, 0.1), sides=6)   # bochecha
        H.box("hull", "eye", (s * 0.29, 0.82, 1.0), (0.2, 0.07, 0.1))
    H.box("hull", "stone_dk", (0, 0.36, 1.0), (1.14, 0.16, 0.34))                                           # queixo
    for x in (-0.44, 0.0, 0.44):
        H.frustum("hull", "black", (x, 0.32, 1.08), (x * 1.08, 0.05, 1.4), (0.07, 0.07), (0.012, 0.012), sides=4)


def turret():
    H.frustum("head", "gold", (0, 1.1, -0.07), (0, 1.2, -0.07), (0.44, 0.47), (0.44, 0.47), sides=8)
    H.frustum("head", "blue", (0, 1.2, -0.07), (0, 1.56, -0.07), (0.41, 0.45), (0.3, 0.34), sides=8)
    H.frustum("head", "gold", (0, 1.54, -0.07), (0, 1.68, -0.07), (0.3, 0.34), (0.24, 0.28), sides=8)
    for s in (-1, 1):
        H.box("head", "gold", (s * 0.33, 1.38, 0.0), (0.06, 0.3, 0.5))
    H.frustum("head", "gold", (0, CANNON_Y, 0.08), (0, CANNON_Y, 0.26), (0.2, 0.2), (0.2, 0.2), sides=8)    # culatra
    H.frustum("head", "grey", (0, CANNON_Y, 0.24), (0, CANNON_Y, 0.74), (0.16, 0.16), (0.14, 0.14), sides=8)  # cano
    H.frustum("head", "grey", (0, CANNON_Y, 0.7), (0, CANNON_Y, 0.8), (0.19, 0.19), (0.19, 0.19), sides=8)    # boca
    H.frustum("head", "bore", (0, CANNON_Y, 0.8), (0, CANNON_Y, 0.81), (0.1, 0.1), (0.1, 0.1), sides=8)


def make():
    chassis()
    tanks()
    exhausts()
    face()
    turret()
    for z, (bl, br) in zip(AXLES, (("wheel1", "wheel2"), ("wheel3", "wheel4"))):
        wheel(bl, 1, z)
        wheel(br, -1, z)


def joints():
    xm = (WHEEL_X0 + WHEEL_X1) / 2
    return {"head": ((0, 1.12, -0.1), (0, 1.12, 0.4)),
            "hull": ((0, 0.65, HULL_REAR), (0, 0.7, HULL_FRONT)),
            "wheel1": ((xm, WHEEL_R, AXLES[0]), (xm + 0.1, WHEEL_R, AXLES[0])),
            "wheel2": ((-xm, WHEEL_R, AXLES[0]), (-xm - 0.1, WHEEL_R, AXLES[0])),
            "wheel3": ((xm, WHEEL_R, AXLES[1]), (xm + 0.1, WHEEL_R, AXLES[1])),
            "wheel4": ((-xm, WHEEL_R, AXLES[1]), (-xm - 0.1, WHEEL_R, AXLES[1]))}


H.build("h06S", "vehicle", PALETTE, make, joints())
