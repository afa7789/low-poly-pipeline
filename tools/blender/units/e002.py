"""Glaive Thrower (e002): carro-grifo alado com rotor de laminas, medido em artifacts/model-sheets/refs/e002/sheet.jpg
(perfil: 0.0045 m por pixel).

    blender -b --factory-startup -P tools/blender/units/e002.py -- <out.glb>
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "gold": 0xE0AA2C, "gold_dk": 0xB07F1C, "brown": 0x6B4527, "brown_dk": 0x4E321B, "teal": 0x2E9C84,
    "white": 0xE9E9E4, "red": 0x9A2A1A,
}

R = 0.36                                    # raio do pneu
WX0, WX1 = 0.58, 0.82                       # face interna / externa (lado esquerdo)
AXLES = (("wheel1", "wheel2", 0.7), ("wheel3", "wheel4", -0.7))
HUB = (0.0, 1.0, 0.42)                      # pe do mastro do rotor
ROTOR_Y, ROTOR_R = 2.06, 1.25


def wheel(bone, s, z):
    a, b = s * WX0, s * WX1
    H.frustum(bone, "brown_dk", (a, R, z), (b, R, z), (R * 0.98, R * 0.98), (R * 0.98, R * 0.98), sides=10)
    H.frustum(bone, "gold", (a, R, z), (a + s * 0.07, R, z), (R, R), (R, R), sides=10)
    H.frustum(bone, "gold", (b - s * 0.06, R, z), (b, R, z), (R, R), (R, R), sides=10)
    H.frustum(bone, "white", (b + s * 0.02, R, z), (b + s * 0.07, R, z), (R * 0.2, R * 0.2), (R * 0.2, R * 0.2), sides=6)
    H.frustum(bone, "white", (b, R, z), (b + s * 0.34, R, z), (0.1, 0.1), (0.015, 0.015), sides=6)   # espigao do cubo


def chassis():
    for _, _, z in AXLES:
        H.frustum("hull", "brown", (-0.72, R, z), (0.72, R, z), (0.07, 0.07), (0.07, 0.07), sides=6)
        for s in (-1, 1):       # escora do eixo ate o casco
            H.frustum("hull", "brown", (s * 0.66, R, z), (s * 0.3, 0.62, z), (0.09, 0.1), (0.14, 0.15), sides=6)
    H.frustum("hull", "brown_dk", (0, 0.45, 0.7), (0, 0.45, -0.7), (0.2, 0.08), (0.2, 0.08), sides=6)


def body():
    for (z0, z1, r0, r1, y) in ((0.82, 0.3, (0.3, 0.26), (0.54, 0.34), 0.75), (0.3, -0.6, (0.54, 0.34), (0.6, 0.34), 0.77),
                                (-0.6, -1.25, (0.6, 0.34), (0.3, 0.2), 0.8)):
        H.frustum("hull", "brown", (0, y, z0), (0, y, z1), r0, r1, sides=8)
    H.frustum("hull", "brown_dk", (0, 0.6, 0.6), (0, 0.6, -1.0), (0.3, 0.2), (0.22, 0.14), sides=8)
    for s in (-1, 1):           # bordas douradas
        H.chain("hull", "gold", [(s * 0.34, 1.0, 0.8), (s * 0.58, 1.02, 0.3), (s * 0.62, 1.02, -0.6), (s * 0.34, 1.0, -1.25)],
                [(0.05, 0.05)] * 4, sides=6)
    H.frustum("hull", "gold", (0, 0.98, 0.1), (0, 0.98, -0.2), (0.62, 0.05), (0.62, 0.05), sides=4)      # cinta
    H.frustum("hull", "gold", (0, 0.98, -0.8), (0, 0.98, -0.95), (0.6, 0.05), (0.6, 0.05), sides=4)
    H.frustum("hull", "gold", (0, 0.9, 0.75), (0, 0.6, 0.85), (0.34, 0.3), (0.12, 0.3), sides=6)         # peito
    H.chain("hull", "gold", [(0, 0.95, -1.15), (0, 0.9, -1.45), (0, 0.8, -1.75)], [(0.12, 0.08), (0.08, 0.06), (0.015, 0.015)], sides=4)


def griffin():
    H.chain("hull", "gold", [(0, 0.8, 0.72), (0, 1.1, 0.95), (0, 1.38, 1.12)], [(0.28, 0.24), (0.22, 0.2), (0.2, 0.19)], sides=8)
    H.frustum("hull", "gold", (0, 1.45, 1.0), (0, 1.5, 1.26), (0.22, 0.2), (0.2, 0.2), sides=8)           # cabeca
    H.chain("hull", "gold_dk", [(0, 1.45, 1.24), (0, 1.38, 1.42), (0, 1.22, 1.5)], [(0.12, 0.14), (0.08, 0.09), (0.015, 0.02)], sides=6)  # bico
    for s in (-1, 1):
        H.frustum("hull", "red", (s * 0.1, 1.56, 1.24), (s * 0.12, 1.55, 1.3), (0.03, 0.03), (0.03, 0.03), sides=4)    # olhos
        H.frustum("hull", "gold", (s * 0.08, 1.58, 1.0), (s * 0.14, 1.78, 0.9), (0.05, 0.05), (0.01, 0.01), sides=4)   # penacho


def crescents():
    for s in (-1, 1):
        H.chain("hull", "gold", [(s * 0.5, 0.92, -1.0), (s * 0.95, 0.9, -1.0), (s * 1.2, 1.15, -1.02), (s * 1.12, 1.45, -1.05), (s * 0.95, 1.62, -1.05)],
                [(0.1, 0.1), (0.13, 0.12), (0.12, 0.12), (0.09, 0.09), (0.015, 0.015)], sides=6)


def wing(s):
    def pt(y, z):       # a asa abre para fora com a altura e para tras
        return (s * (0.3 + 0.3 * (y - 1.0) - 0.22 * z), y, z)
    top = [(1.1, 0.45), (1.7, 0.0), (2.4, -0.7), (2.9, -1.35)]      # (y, z) do bordo de ataque
    H.chain("hull", "gold", [pt(y, z) for y, z in top], [(0.07, 0.1), (0.08, 0.11), (0.07, 0.09), (0.02, 0.03)], sides=6)
    for i in range(6):
        u = i / 5
        a = pt(1.05 + 0.12 * i, 0.4 - 0.2 * i)
        e = pt(1.05 + 1.7 * u, -1.25 - 0.08 * u)
        H.frustum("hull", "teal" if i % 2 == 0 else "brown", a, e, (0.16, 0.17), (0.1, 0.1), sides=4)


def rotor():
    cx, cy, cz = HUB
    H.frustum("head", "brown_dk", (cx, cy, cz), (cx, ROTOR_Y - 0.12, cz), (0.1, 0.1), (0.08, 0.08), sides=6)
    H.frustum("head", "teal", (cx, ROTOR_Y - 0.2, cz), (cx, ROTOR_Y - 0.1, cz), (0.1, 0.1), (0.1, 0.1), sides=6)
    H.frustum("head", "gold", (cx, ROTOR_Y - 0.1, cz), (cx, ROTOR_Y + 0.08, cz), (0.16, 0.16), (0.2, 0.2), sides=8)
    for deg in (0, 125, 235):
        a = math.radians(deg)
        tip = (math.sin(a) * ROTOR_R, ROTOR_Y, cz + math.cos(a) * ROTOR_R)
        H.frustum("head", "white", (0, ROTOR_Y, cz), tip, (0.22, 0.03), (0.04, 0.015), sides=4)


def make():
    chassis()
    body()
    griffin()
    crescents()
    for s in (-1, 1):
        wing(s)
    rotor()
    for bl, br, z in AXLES:
        wheel(bl, 1, z)
        wheel(br, -1, z)


def joints():
    out = {"head": ((HUB[0], ROTOR_Y, HUB[2]), (HUB[0], ROTOR_Y, HUB[2] + 0.5))}
    for bl, br, z in AXLES:
        out[bl] = ((WX0, R, z), (WX1, R, z))
        out[br] = ((-WX0, R, z), (-WX1, R, z))
    return out


H.build("e002", "vehicle", PALETTE, make, joints())
