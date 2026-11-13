"""Roterothopter (h06Q): medido em artifacts/model-sheets/refs/h06Q/sheet.jpg (perfil ~0.0046 m por pixel).

    blender -b --factory-startup -P tools/blender/units/h06Q.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "tan": 0xBE9F6C, "tan_dk": 0x9C7E4E, "olive": 0x7C7C4E, "red": 0xA94430, "gold": 0xC9A23E, "blue": 0x61748C,
    "coat": 0x5C2434, "cream": 0xE5D6A8, "skin": 0xE2A0A0, "beard": 0x6B4A2E, "cyan": 0x30D0F0, "gun": 0x4A5568,
    "gun_lt": 0x7B8794, "black": 0x201E1C,
}

YC = 1.92            # eixo da fuselagem
# (z, meia largura, meia altura) da fuselagem, do nariz à cauda
SPINE = ((1.48, 0.30), (1.2, 0.42), (0.7, 0.53), (0.1, 0.57), (-0.6, 0.43), (-1.1, 0.25), (-1.5, 0.09))
WING_X, WING_Y = 1.5, 1.93
HUB_Z = 0.25


def ring(bone, tone, z0, z1, r0, r1, y=YC, x=0.0, sides=8):
    H.frustum(bone, tone, (x, y, z0), (x, y, z1), (r0, r0), (r1, r1), sides)


def fuselage():
    for i, ((z0, r0), (z1, r1)) in enumerate(zip(SPINE, SPINE[1:])):
        y0, y1 = YC + max(0.0, -z0 - 0.6) * 0.1, YC + max(0.0, -z1 - 0.6) * 0.1
        H.frustum("hull", "blue" if i == 0 else "tan", (0, y0, z0), (0, y1, z1), (r0, r0 * 0.95), (r1, r1 * 0.95), 8)
    ring("hull", "tan_dk", 0.2, 0.24, 0.5, 0.5, y=YC + 0.02)          # costura sob a cabine
    ring("hull", "gold", 1.08, 1.14, 0.425, 0.425)                    # aro do nariz
    H.frustum("hull", "tan_dk", (0, 2.3, 0.25), (0, 2.52, 0.25), (0.5, 0.62), (0.58, 0.68), 8)   # borda da cabine
    H.frustum("hull", "gold", (0, 2.2, -0.2), (0, 3.4, -0.25), (0.07, 0.07), (0.01, 0.01), 6)    # espeto do mastro


def wing(s):
    root, tip = 0.35 * s, WING_X * s
    H.frustum("hull", "olive", (root, 1.92, 0.3), (tip, 1.96, 0.34), (0.4, 0.1), (0.24, 0.05), 4)
    H.frustum("hull", "gold", (tip, 1.96, 0.35), ((WING_X + 0.28) * s, 1.97, 0.35), (0.04, 0.04), (0.01, 0.01), 6)
    hub = (WING_X * s, 1.96, HUB_Z)                                    # hélice da ponta: cubo + duas pás deitadas
    H.frustum("hull", "gold", (hub[0], hub[1], HUB_Z - 0.1), (hub[0], hub[1], HUB_Z + 0.16), (0.2, 0.2), (0.15, 0.15), 8)
    H.frustum("hull", "black", (hub[0], hub[1], HUB_Z + 0.16), (hub[0], hub[1], HUB_Z + 0.2), (0.07, 0.07), (0.07, 0.07), 6)
    for z0, z1 in ((HUB_Z, HUB_Z + 0.75), (HUB_Z, HUB_Z - 0.75)):
        H.frustum("hull", "gold", (hub[0], hub[1], z0), (hub[0], hub[1], z1), (0.07, 0.025), (0.05, 0.02), 4)


def floats(s):
    x = 0.62 * s
    H.frustum("hull", "red", (x, 1.1, 1.4), (x, 1.1, 1.0), (0.08, 0.05), (0.19, 0.12), 6)
    H.frustum("hull", "red", (x, 1.1, 1.0), (x, 1.1, 0.0), (0.19, 0.12), (0.22, 0.13), 6)
    H.frustum("hull", "red", (x, 1.1, 0.0), (x, 1.1, -0.65), (0.22, 0.13), (0.07, 0.05), 6)
    for z in (0.75, 0.05):
        H.frustum("hull", "gold", (0.3 * s, 1.55, z), (x, 1.2, z), (0.05, 0.05), (0.05, 0.05), 6)


def tail():
    H.panel("hull", "olive", [(0.1, 2.0, -1.0), (0.62, 2.0, -1.4), (0.62, 2.0, -1.62), (0.1, 2.0, -1.5)], 0.06)
    H.panel("hull", "olive", [(-0.1, 2.0, -1.0), (-0.62, 2.0, -1.4), (-0.62, 2.0, -1.62), (-0.1, 2.0, -1.5)], 0.06)
    H.panel("rudder", "olive", [(0, 2.1, -0.85), (0, 2.85, -1.3), (0, 2.85, -1.55), (0, 2.1, -1.5)], 0.08)
    H.panel("rudder", "red", [(0, 2.55, -1.15), (0, 2.85, -1.3), (0, 2.85, -1.55), (0, 2.45, -1.52)], 0.1)


def pilot():
    H.frustum("hull", "coat", (0, 2.3, 0.25), (0, 2.55, 0.25), (0.45, 0.38), (0.56, 0.42), 8)      # tronco em V
    H.frustum("hull", "coat", (0, 2.55, 0.25), (0, 2.8, 0.3), (0.56, 0.42), (0.38, 0.34), 8)
    H.frustum("hull", "cream", (0, 2.72, 0.32), (0, 2.88, 0.38), (0.46, 0.4), (0.38, 0.34), 8)      # gola de pele
    H.frustum("hull", "skin", (0, 2.82, 0.38), (0, 3.12, 0.4), (0.3, 0.32), (0.26, 0.28), 8)        # cabeça careca
    H.frustum("hull", "beard", (0, 2.7, 0.52), (0, 2.96, 0.58), (0.27, 0.2), (0.3, 0.22), 8)        # barba
    for s in (-1, 1):
        ring("hull", "gold", 0.66, 0.74, 0.11, 0.11, y=3.0, x=0.15 * s)                            # óculos
        ring("hull", "cyan", 0.74, 0.78, 0.075, 0.075, y=3.0, x=0.15 * s, sides=6)
        H.frustum("hull", "coat", (0.5 * s, 2.66, 0.25), (0.4 * s, 2.45, 0.68), (0.17, 0.15), (0.15, 0.13), 8)   # braço


def gun():
    for s in (-1, 1):
        H.frustum("gondola", "coat", (0.4 * s, 2.45, 0.68), (0.12 * s, 2.5, 0.96), (0.15, 0.13), (0.14, 0.12), 8)  # antebraço
        H.frustum("gondola", "skin", (0.12 * s, 2.5, 0.92), (0.1 * s, 2.5, 1.04), (0.13, 0.12), (0.12, 0.11), 6)   # punho
    ring("gondola", "gun", 0.95, 1.2, 0.12, 0.13, y=2.52)               # corpo do revólver
    ring("gondola", "gun_lt", 1.0, 1.14, 0.19, 0.19, y=2.5)             # tambor
    ring("gondola", "gun", 1.2, 1.8, 0.1, 0.09, y=2.56, sides=6)    # cano
    ring("gondola", "gun_lt", 1.76, 1.9, 0.13, 0.12, y=2.56, sides=6)    # boca
    H.frustum("gondola", "gun", (0, 2.46, 0.98), (0, 2.28, 0.9), (0.08, 0.1), (0.1, 0.12), 6)   # empunhadura


def make():
    fuselage()
    pilot()
    gun()
    tail()
    for s in (-1, 1):
        wing(s)
        floats(s)


JOINTS = {"hull": ((0, YC, -0.4), (0, YC, 0.6)), "gondola": ((0, 2.5, 0.2), (0, 2.5, 0.9)),
          "rudder": ((0, 2.1, -1.0), (0, 2.75, -1.45)), "prop": ((0, YC, -1.45), (0, YC, -1.7))}

H.build("h06Q", "aircraft", PALETTE, make, JOINTS)
