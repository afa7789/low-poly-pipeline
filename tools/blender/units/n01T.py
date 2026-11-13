"""Goblin Shredder (n01T): mecha de duas pernas com serra em cada antebraço, piloto goblin no topo. Medido em
artifacts/model-sheets/refs/n01T/sheet.jpg (0.0036 m por pixel exibido, chão em y=885; eixo x do painel frontal em
347; perfil olha para +z = direita). Família biped: pernas em thigh/shin/foot, braço em arm.L/R, antebraço com a serra em forearm.L/R
(o clip de golpe os levanta e bate); a cabeça do piloto no osso head.

    blender -b --factory-startup -P tools/blender/units/n01T.py -- <out.glb>
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "brown": 0x9A5A3A, "brown_dk": 0x6E3E2A, "tan": 0xC49A6C, "tan_dk": 0x9A7650, "black": 0x201E1E,
    "orange": 0xE87A2A, "eye": 0x55E040, "gold": 0xD6A62C, "saw": 0xC8962A, "white": 0xE8E8E0,
    "green": 0x4FBF3A, "panel": 0x3E5545, "goggle": 0x6B4A2A, "yellow": 0xF0D020,
}

LEG_X = 0.46
SHOULDER = (0.8, 1.85, 0.0)
HUB = (0.86, 0.72, 0.32)
SAW_R = 0.5


def S(s, p):
    """Espelha um ponto (x, y, z) para o lado s (+1 esquerda, -1 direita)."""
    return (s * p[0], p[1], p[2])


def leg(side, s):
    x = s * LEG_X
    thigh, shin, foot = "thigh." + side, "shin." + side, "foot." + side
    H.frustum(thigh, "tan", (x, 1.0, 0.0), (x, 1.46, 0.0), (0.2, 0.22), (0.25, 0.26), sides=8)               # coxa alarga no quadril
    H.frustum(thigh, "black", (x, 0.96, 0.0), (x, 1.06, 0.0), (0.2, 0.2), (0.2, 0.2), sides=8)               # junta do joelho
    H.frustum(shin, "brown", (x, 0.72, 0.06), (x, 1.02, 0.12), (0.25, 0.23), (0.3, 0.28), sides=6)           # joelheira
    H.frustum(shin, "brown", (x, 0.14, -0.05), (x, 0.76, 0.0), (0.2, 0.22), (0.27, 0.26), sides=6)          # canela
    H.frustum(foot, "brown_dk", (x, 0.12, -0.38), (x, 0.12, 0.46), (0.28, 0.15), (0.23, 0.1), sides=6)       # pé
    H.frustum(foot, "black", (x, 0.03, -0.42), (x, 0.03, 0.48), (0.27, 0.05), (0.22, 0.04), sides=4)         # sola
    H.frustum(foot, "brown", (x, 0.2, 0.15), (x, 0.17, 0.46), (0.19, 0.12), (0.16, 0.06), sides=4)           # biqueira


def torso():
    H.frustum("pelvis", "tan", (0, 1.22, 0.0), (0, 1.52, 0.0), (0.3, 0.26), (0.4, 0.3), sides=8)               # quadril
    H.frustum("spine", "black", (0, 1.3, 0.0), (0, 1.42, 0.0), (0.46, 0.34), (0.46, 0.34), sides=8)
    H.frustum("spine", "brown", (0, 1.4, 0.0), (0, 1.95, 0.0), (0.44, 0.46), (0.5, 0.48), sides=8)            # barriga
    H.frustum("spine", "brown", (0, 1.9, -0.02), (0, 2.46, -0.02), (0.5, 0.48), (0.46, 0.46), sides=8)        # cabine
    H.frustum("spine", "panel", (0, 1.65, -0.5), (0, 2.1, -0.5), (0.34, 0.06), (0.36, 0.06), sides=4)         # placa verde atrás


def face():
    H.frustum("spine", "tan", (0, 2.12, 0.3), (0, 2.06, 0.8), (0.4, 0.12), (0.34, 0.06), sides=4)           # sobrancelha
    for s in (-1, 1):
        H.box("spine", "eye", (s * 0.22, 1.93, 0.5), (0.2, 0.1, 0.1))
        H.frustum("spine", "white", (s * 0.25, 1.78, 0.74), (s * 0.28, 1.5, 0.86), (0.05, 0.05), (0.012, 0.012), sides=4)   # presas
    H.frustum("spine", "brown_dk", (0, 1.62, 0.3), (0, 1.62, 0.8), (0.36, 0.2), (0.32, 0.16), sides=4)       # mandíbula
    H.box("spine", "orange", (0, 1.62, 0.84), (0.56, 0.3, 0.06))                                              # grelha
    for x in (-0.2, -0.1, 0.0, 0.1, 0.2):
        H.box("spine", "black", (x, 1.62, 0.875), (0.035, 0.3, 0.03))


def pauldrons():
    for s in (-1, 1):
        H.frustum("spine", "black", (s * 0.66, 1.64, 0.0), (s * 0.66, 1.9, 0.0), (0.2, 0.2), (0.22, 0.22), sides=8)    # junta do ombro
        H.frustum("spine", "brown", (s * 0.72, 1.74, 0.0), (s * 0.7, 2.06, 0.0), (0.3, 0.38), (0.26, 0.34), sides=4)  # ombreira
        H.frustum("spine", "brown_dk", (s * 0.72, 1.7, 0.0), (s * 0.72, 1.78, 0.0), (0.32, 0.4), (0.32, 0.4), sides=4)
        for x, y1 in ((0.58, 2.38), (0.84, 2.24)):
            H.frustum("spine", "white", (s * x, 2.0, 0.0), (s * (x + 0.04), y1, 0.0), (0.07, 0.07), (0.012, 0.012), sides=4)


def klaxon():
    pts = [(-0.4, 2.0, -0.54), (-0.45, 2.4, -0.64), (-0.55, 2.72, -0.7), (-0.6, 2.9, -0.62), (-0.6, 2.98, -0.58)]
    H.chain("spine", "gold", pts, [(0.06, 0.06), (0.06, 0.06), (0.08, 0.08), (0.14, 0.14), (0.19, 0.19)], sides=8)


def pilot():
    H.frustum("head", "green", (0, 2.4, -0.05), (0, 2.72, -0.05), (0.26, 0.22), (0.21, 0.19), sides=8)
    H.frustum("head", "green", (0, 2.7, -0.05), (0, 2.84, -0.05), (0.21, 0.19), (0.1, 0.1), sides=6)
    H.box("head", "goggle", (0, 2.74, 0.12), (0.46, 0.11, 0.1))
    H.box("head", "yellow", (0, 2.62, 0.16), (0.26, 0.05, 0.05))
    for s in (-1, 1):
        H.frustum("head", "green", (s * 0.2, 2.68, -0.05), (s * 0.66, 2.82, -0.1), (0.14, 0.035), (0.02, 0.02), sides=4)


def saw(bone, s):
    cx, cy, cz = S(s, HUB)
    w = 0.06
    H.frustum(bone, "saw", (cx - w, cy, cz), (cx + w, cy, cz), (SAW_R * 0.9, SAW_R * 0.9), (SAW_R * 0.9, SAW_R * 0.9), sides=16)
    H.frustum(bone, "brown_dk", (cx - w * 1.4, cy, cz), (cx + w * 1.4, cy, cz), (0.14, 0.14), (0.14, 0.14), sides=8)
    for k in range(12):
        a = k * math.pi / 6
        c, d = math.cos(a), math.sin(a)
        H.frustum(bone, "gold", (cx, cy + d * SAW_R * 0.82, cz + c * SAW_R * 0.82), (cx, cy + d * SAW_R * 1.07, cz + c * SAW_R * 1.07),
                  (w, 0.1), (w, 0.03), sides=4)


ELBOW = (0.82, 1.45, -0.04)
WRIST = (0.85, 0.98, 0.2)


def arm(side, s):
    bone, fore = "arm." + side, "forearm." + side
    sh, el, wr = S(s, SHOULDER), S(s, ELBOW), S(s, WRIST)
    H.frustum(bone, "tan", (sh[0], sh[1] + 0.08, sh[2]), el, (0.12, 0.12), (0.1, 0.1), sides=8)           # braço
    H.frustum(bone, "black", (el[0] - s * 0.1, el[1], el[2]), (el[0] + s * 0.1, el[1], el[2]), (0.13, 0.13), (0.13, 0.13), sides=8)
    H.frustum(fore, "brown", (el[0], el[1] + 0.06, el[2]), wr, (0.17, 0.2), (0.19, 0.22), sides=4)         # carcaça da serra
    H.frustum(fore, "brown_dk", wr, S(s, HUB), (0.13, 0.15), (0.09, 0.12), sides=4)
    saw(fore, s)


def make():
    torso()
    face()
    pauldrons()
    klaxon()
    pilot()
    for side, s in (("L", 1), ("R", -1)):
        leg(side, s)
        arm(side, s)


def joints():
    out = {"pelvis": ((0, 1.22, 0.0), (0, 1.52, 0.0)), "spine": ((0, 1.52, 0.0), (0, 2.3, 0.0)),
           "head": ((0, 2.3, -0.05), (0, 2.85, -0.05))}
    for side, s in (("L", 1), ("R", -1)):
        x = s * LEG_X
        out["thigh." + side] = ((x, 1.46, 0.0), (x, 0.98, 0.0))
        out["shin." + side] = ((x, 0.98, 0.0), (x, 0.14, 0.0))
        out["foot." + side] = ((x, 0.14, 0.0), (x, 0.1, 0.46))
        out["arm." + side] = (S(s, SHOULDER), S(s, ELBOW))
        out["forearm." + side] = (S(s, ELBOW), S(s, HUB))
    return out


H.build("n01T", "biped", PALETTE, make, joints())
