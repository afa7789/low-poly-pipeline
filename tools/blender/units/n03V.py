"""Long Range Catapult (n03V): na folha e um canhao de campanha de cano longo, carreta verde-oliva e duas rodas de raios
(artifacts/model-sheets/refs/n03V/sheet.jpg, perfil: 0.0072 m por pixel). As rodas wheel3/wheel4 nao tem peca.

    blender -b --factory-startup -P tools/blender/units/n03V.py -- <out.glb>
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "olive": 0x6B6E3A, "olive_dk": 0x4D5029, "iron": 0x4E5054, "iron_dk": 0x333437, "wood": 0x3A3A3C,
    "blue": 0x2F6DB5, "bore": 0x111111,
}
R = 0.46                           # raio da roda
AXLE_Y, AXLE_X = R, 0.64
BARREL_Y = 1.04
SPOKES, RIM = 8, 12


def ring_pt(x, ang, r):
    return (x, AXLE_Y + r * math.sin(ang), r * math.cos(ang))


def wheel(bone, s):
    x = s * AXLE_X
    for k in range(RIM):
        a0, a1 = k * 2 * math.pi / RIM, (k + 1) * 2 * math.pi / RIM
        H.frustum(bone, "wood", ring_pt(x, a0, R * 0.95), ring_pt(x, a1, R * 0.95), (0.13, 0.07), (0.13, 0.07), sides=4)
    for k in range(SPOKES):
        a = k * 2 * math.pi / SPOKES
        H.frustum(bone, "iron", (x, AXLE_Y, 0), ring_pt(x, a, R * 0.95), (0.05, 0.05), (0.04, 0.04), sides=4)
    H.frustum(bone, "iron_dk", (x - s * 0.1, AXLE_Y, 0), (x + s * 0.12, AXLE_Y, 0), (0.1, 0.1), (0.1, 0.1), sides=8)


def carriage():
    H.frustum("hull", "olive", (0, 0.78, 0.35), (0, 0.7, -1.0), (0.36, 0.3), (0.33, 0.27), sides=4)     # corpo
    H.frustum("hull", "olive_dk", (0, 0.6, 0.3), (0, 0.55, -0.95), (0.36, 0.14), (0.32, 0.12), sides=4)   # fundo
    H.frustum("hull", "olive", (0, 0.98, 0.3), (0, 0.9, -0.5), (0.3, 0.1), (0.28, 0.1), sides=4)        # lombo
    H.frustum("hull", "iron_dk", (-AXLE_X - 0.18, AXLE_Y, 0), (AXLE_X + 0.18, AXLE_Y, 0), (0.07, 0.07), (0.07, 0.07), sides=6)   # eixo
    for s in (-1, 1):
        H.frustum("hull", "olive_dk", (s * 0.34, AXLE_Y, 0), (s * 0.5, AXLE_Y, 0), (0.16, 0.18), (0.13, 0.16), sides=6)   # cubo da carreta
        H.box("hull", "blue", (s * 0.345, 0.74, -0.4), (0.03, 0.3, 0.26))                                                  # losango
    H.box("hull", "blue", (0, 0.96, -0.3), (0.12, 0.03, 0.5))
    H.frustum("hull", "iron", (0, 0.5, -1.0), (0, 1.25, -1.38), (0.18, 0.12), (0.18, 0.14), sides=4)                       # haste de trás
    H.frustum("hull", "iron_dk", (0, 0.28, -1.5), (0, 0.46, -1.0), (0.2, 0.2), (0.18, 0.14), sides=6)                    # pé da cauda


def barrel():
    pts = (-0.92, -0.55, -0.3, 0.2, 0.5, 0.75, 1.15, 1.32, 1.4)
    rad = (0.12, 0.17, 0.17, 0.13, 0.15, 0.12, 0.12, 0.17, 0.17)
    tone = ("iron_dk", "iron", "iron", "iron", "iron_dk", "iron", "iron", "iron_dk", "iron_dk")
    for i in range(len(pts) - 1):
        H.frustum("head", tone[i], (0, BARREL_Y, pts[i]), (0, BARREL_Y, pts[i + 1]), (rad[i],) * 2, (rad[i + 1],) * 2, sides=8)
    H.frustum("head", "bore", (0, BARREL_Y, 1.4), (0, BARREL_Y, 1.42), (0.09, 0.09), (0.09, 0.09), sides=8)
    for s in (-1, 1):
        H.frustum("head", "iron_dk", (s * 0.15, BARREL_Y - 0.1, 0.1), (s * 0.3, BARREL_Y - 0.1, 0.1), (0.1, 0.1), (0.1, 0.1), sides=6)   # munhão


def make():
    carriage()
    barrel()
    wheel("wheel1", 1)
    wheel("wheel2", -1)


def joints():
    out = {"head": ((0, BARREL_Y, -0.2), (0, BARREL_Y, 0.4))}
    out["wheel1"] = ((AXLE_X - 0.08, AXLE_Y, 0), (AXLE_X + 0.08, AXLE_Y, 0))
    out["wheel2"] = ((-AXLE_X + 0.08, AXLE_Y, 0), (-AXLE_X - 0.08, AXLE_Y, 0))
    out["wheel3"] = ((0.1, 0.3, -1.45), (0.2, 0.3, -1.45))
    out["wheel4"] = ((-0.1, 0.3, -1.45), (-0.2, 0.3, -1.45))
    return out


H.build("n03V", "vehicle", PALETTE, make, joints())
