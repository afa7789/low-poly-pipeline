"""Gyrocopter (h06R): medido em artifacts/model-sheets/refs/h06R/sheet.jpg (perfil ~0.0072 m por pixel).

    blender -b --factory-startup -P tools/blender/units/h06R.py -- <out.glb>
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "tan": 0xC4A26C, "nose": 0xB8885A, "olive": 0x7C8250, "gold": 0xD4A82E, "black": 0x242424, "steel": 0x6E7B88,
    "steel_dk": 0x40484F, "wood": 0xA3502C, "red": 0xB5232A, "teeth": 0xF0F0E0, "shirt": 0x6EA8D8, "skin": 0xE2A0A0,
    "beard": 0x6B4A2E, "cyan": 0x30D0F0, "gun": 0x2F353B, "grey": 0x8A8F94, "jacket": 0x5C3A2A,
}

YC = 1.6             # eixo da fuselagem
HUB = (0, 3.1, -0.2)  # cubo do rotor
ROTOR_R = 2.6
# (z, raio) da fuselagem, do nariz ao ombro do pilone
SPINE = ((1.57, 0.04), (1.3, 0.2), (0.9, 0.3), (0.4, 0.34), (-0.1, 0.31), (-0.5, 0.22))
BOOM = ((-0.5, 1.6, 0.22), (-0.95, 1.8, 0.15), (-1.3, 2.0, 0.1), (-1.62, 2.2, 0.06))


def ring(bone, tone, z0, z1, r0, r1, y=YC, x=0.0, sides=8):
    H.frustum(bone, tone, (x, y, z0), (x, y, z1), (r0, r0), (r1, r1), sides)


def fuselage():
    for i, ((z0, r0), (z1, r1)) in enumerate(zip(SPINE, SPINE[1:])):
        ring("hull", "nose" if i < 2 else "tan", z0, z1, r0, r1)
    ring("hull", "gold", 1.28, 1.34, 0.2, 0.2)
    for (z0, y0, r0), (z1, y1, r1) in zip(BOOM, BOOM[1:]):
        H.frustum("hull", "tan", (0, y0, z0), (0, y1, z1), (r0, r0), (r1, r1), 6)
    H.frustum("hull", "gold", (0, 1.72, 0.1), (0, 1.98, 0.1), (0.4, 0.5), (0.46, 0.56), 8)      # borda da cabine
    H.frustum("hull", "cyan", (0, 1.9, 0.58), (0, 2.14, 0.66), (0.22, 0.04), (0.2, 0.04), 4)    # para-brisa
    H.frustum("hull", "steel_dk", (0, 1.7, -0.25), (0, 2.0, -0.2), (0.3, 0.26), (0.26, 0.24), 6)   # caixa do rotor


def tail():
    for s in (-1, 1):
        H.frustum("hull", "olive", (0.08 * s, 2.0, -1.28), (0.65 * s, 2.0, -1.36), (0.02, 0.15), (0.02, 0.1), 4)
    H.panel("rudder", "tan", [(0, 2.0, -1.2), (0, 2.85, -1.6), (0, 2.85, -1.8), (0, 2.1, -1.7)], 0.08)
    H.panel("rudder", "red", [(0, 2.5, -1.45), (0, 2.85, -1.6), (0, 2.85, -1.8), (0, 2.45, -1.75)], 0.1)


def wing(s):
    H.frustum("hull", "olive", (0.3 * s, 1.6, 0.25), (1.65 * s, 1.68, 0.28), (0.34, 0.08), (0.2, 0.04), 4)
    x = 0.83 * s
    ring("hull", "black", 0.74, -0.06, 0.3, 0.3, y=1.6, x=x, sides=10)                          # nacela
    for z in (0.7, -0.02):
        ring("hull", "gold", z, z + 0.06, 0.33, 0.33, y=1.6, x=x, sides=10)
    ring("hull", "steel", 0.72, 0.78, 0.24, 0.24, y=1.6, x=x, sides=8)                          # face da ventoinha
    ring("hull", "gold", 0.76, 0.84, 0.08, 0.06, y=1.6, x=x, sides=6)
    for a in (0, 1, 2):
        ang = a * math.pi / 3 + 0.3
        H.frustum("hull", "steel_dk", (x - 0.22 * math.cos(ang), 1.6 - 0.22 * math.sin(ang), 0.8),
                  (x + 0.22 * math.cos(ang), 1.6 + 0.22 * math.sin(ang), 0.8), (0.03, 0.03), (0.03, 0.03), 4)
    for z in (0.5, -0.05):                                       # bóia de madeira presa à asa
        H.frustum("hull", "gold", (0.45 * s, 1.58, z), (x, 1.2, z), (0.04, 0.04), (0.04, 0.04), 6)
    ring("hull", "wood", 1.5, 1.1, 0.02, 0.19, y=1.08, x=x)
    ring("hull", "wood", 1.1, -0.2, 0.19, 0.2, y=1.08, x=x)
    ring("hull", "wood", -0.2, -0.68, 0.2, 0.03, y=1.08, x=x)
    ring("hull", "red", 1.2, 1.32, 0.17, 0.17, y=1.08, x=x - 0.03 * s, sides=6)                  # boca de tubarão
    ring("hull", "teeth", 1.18, 1.22, 0.2, 0.2, y=1.08, x=x - 0.03 * s, sides=6)


def tower_and_rotor():
    for sx in (-1, 1):
        for sz in (-1, 1):
            H.frustum("hull", "steel", (0.28 * sx, 1.9, -0.2 + 0.2 * sz), (0.07 * sx, 3.0, -0.2 + 0.05 * sz),
                      (0.065, 0.065), (0.05, 0.05), 4)
    for y, r in ((2.3, 0.22), (2.65, 0.15)):
        ring("hull", "steel_dk", -0.2 - r - 0.02, -0.2 + r + 0.02, r, r, y=y, sides=4)
    ring("prop", "gold", HUB[2] - 0.1, HUB[2] + 0.12, 0.17, 0.17, y=HUB[1] - 0.1)
    for a in (math.radians(48), math.radians(132)):             # duas pás cruzadas em X, vistas de cima
        c, s = math.cos(a), math.sin(a)
        H.frustum("prop", "gold", (-ROTOR_R * c, HUB[1], HUB[2] - ROTOR_R * s), (ROTOR_R * c, HUB[1], HUB[2] + ROTOR_R * s),
                  (0.1, 0.03), (0.1, 0.03), 4)
        H.frustum("prop", "gold", (-ROTOR_R * c * 0.5, HUB[1], HUB[2] - ROTOR_R * s * 0.5),
                  (ROTOR_R * c * 0.5, HUB[1], HUB[2] + ROTOR_R * s * 0.5), (0.2, 0.04), (0.2, 0.04), 4)


def pilot():
    H.frustum("hull", "jacket", (0, 1.65, 0.25), (0, 1.95, 0.25), (0.3, 0.25), (0.38, 0.3), 8)
    H.frustum("hull", "shirt", (0, 1.95, 0.25), (0, 2.18, 0.28), (0.38, 0.3), (0.26, 0.24), 8)
    H.frustum("hull", "skin", (0, 2.1, 0.3), (0, 2.42, 0.32), (0.27, 0.28), (0.24, 0.26), 8)
    H.frustum("hull", "beard", (0, 2.02, 0.45), (0, 2.28, 0.5), (0.22, 0.17), (0.25, 0.19), 8)
    H.frustum("hull", "beard", (-0.3, 2.28, 0.54), (0.3, 2.28, 0.54), (0.04, 0.04), (0.04, 0.04), 4)   # bigode
    for s in (-1, 1):
        ring("hull", "gold", 0.56, 0.62, 0.09, 0.09, y=2.35, x=0.13 * s)
        ring("hull", "cyan", 0.62, 0.65, 0.06, 0.06, y=2.35, x=0.13 * s, sides=6)
        H.frustum("hull", "jacket", (0.38 * s, 2.0, 0.22), (0.3 * s, 1.88, 0.5), (0.15, 0.13), (0.13, 0.12), 8)   # braço


def guns():
    for s in (-1, 1):
        x = 0.14 * s
        H.frustum("gondola", "jacket", (0.3 * s, 1.88, 0.5), (0.14 * s, 2.0, 0.74), (0.13, 0.12), (0.12, 0.11), 8)   # antebraço
        H.frustum("gondola", "skin", (0.14 * s, 2.0, 0.7), (0.13 * s, 2.0, 0.84), (0.11, 0.1), (0.1, 0.1), 6)        # punho
        H.frustum("gondola", "gun", (x, 2.0, 0.55), (x, 2.0, 1.0), (0.1, 0.1), (0.09, 0.09), 4)                      # culatra
        ring("gondola", "grey", 0.98, 1.45, 0.085, 0.085, y=2.0, x=x, sides=6)                                      # camisa do cano
        ring("gondola", "gun", 1.45, 1.85, 0.05, 0.05, y=2.0, x=x, sides=6)
        ring("gondola", "grey", 1.8, 1.92, 0.095, 0.085, y=2.0, x=x, sides=6)                                       # freio de boca
        H.frustum("gondola", "steel", (x, 2.08, 0.7), (x, 2.3, 0.7), (0.12, 0.12), (0.14, 0.13), 8)                  # carregador
    H.frustum("gondola", "gold", (0, 1.86, 0.5), (0, 2.0, 0.9), (0.22, 0.2), (0.28, 0.26), 4)                        # berço


def make():
    fuselage()
    pilot()
    guns()
    tail()
    tower_and_rotor()
    for s in (-1, 1):
        wing(s)


JOINTS = {"hull": ((0, YC, -0.4), (0, YC, 0.6)), "gondola": ((0, 2.0, 0.15), (0, 2.0, 0.9)),
          "rudder": ((0, 2.0, -1.2), (0, 2.7, -1.6)), "prop": ((HUB[0], HUB[1], HUB[2]), (HUB[0], HUB[1], HUB[2] - 0.3))}

H.build("h06R", "aircraft", PALETTE, make, JOINTS)
