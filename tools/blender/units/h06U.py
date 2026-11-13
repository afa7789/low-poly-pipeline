"""Mine Layer (h06U): goblin a pé, medido em artifacts/model-sheets/refs/h06U/sheet.jpg (0.0022 m por pixel exibido,
chão em y=1045, eixo x do painel frontal em 408, eixo z do perfil em 970). Chave inglesa na mão direita (-x), mina
de espinhos na esquerda (+x), mochila com duas garras mecânicas. Família biped: pernas em thigh/shin/foot, braços em arm/forearm (o clip de golpe os levanta e bate).

    blender -b --factory-startup -P tools/blender/units/h06U.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "skin": 0x7F8C3A, "skin_dk": 0x5F6B2A, "apron": 0x8D8E99, "red": 0xB02525, "trouser": 0x56582D,
    "boot": 0x9A9AA6, "belt": 0x6B4226, "gold": 0xC9983A, "black": 0x232222, "mine": 0x2C2B33,
    "spike": 0xC62828, "wrench": 0x8F8F98, "hair": 0x4A2E22, "eye": 0xDDF2F2, "nose": 0xB99A55,
    "pipe": 0x70706E, "tooth": 0xF0E6C8,
}

LEG_X = 0.235
SHOULDER_Y = 1.0
PACK_Z = -0.34


def S(s, p):
    """Espelha um ponto (x, y, z) para o lado s (+1 esquerda, -1 direita)."""
    return (s * p[0], p[1], p[2])


def leg(side, s):
    x = s * LEG_X
    H.frustum("thigh." + side, "trouser", (x, 0.66, 0.0), (x, 0.4, 0.02), (0.17, 0.17), (0.13, 0.13), sides=8)       # coxa
    shin = "shin." + side
    H.frustum(shin, "trouser", (x, 0.46, 0.02), (x, 0.24, 0.0), (0.13, 0.13), (0.1, 0.1), sides=8)      # canela
    H.frustum(shin, "boot", (x, 0.34, 0.0), (x, 0.1, 0.0), (0.1, 0.11), (0.14, 0.14), sides=8)            # cano alarga em cima
    foot = "foot." + side
    H.frustum(foot, "boot", (x, 0.07, -0.16), (x, 0.07, 0.3), (0.15, 0.08), (0.14, 0.06), sides=6)       # sola e biqueira
    H.frustum(foot, "boot", (x, 0.1, 0.18), (x, 0.13, 0.3), (0.13, 0.07), (0.1, 0.05), sides=6)


def torso():
    H.frustum("pelvis", "skin", (0, 0.55, 0.0), (0, 0.78, 0.0), (0.27, 0.19), (0.3, 0.2), sides=8)        # quadril
    H.frustum("spine", "skin", (0, 0.76, 0.0), (0, 1.02, 0.0), (0.3, 0.2), (0.42, 0.22), sides=8)        # peito em V
    H.frustum("spine", "skin_dk", (0, 1.0, 0.0), (0, 1.14, 0.02), (0.14, 0.12), (0.1, 0.1), sides=6)       # pescoço
    H.frustum("spine", "apron", (0, 0.3, 0.2), (0, 0.78, 0.22), (0.27, 0.04), (0.22, 0.04), sides=4)      # avental
    H.frustum("spine", "red", (0, 0.29, 0.19), (0, 0.4, 0.19), (0.29, 0.03), (0.28, 0.03), sides=4)       # barra vermelha
    H.frustum("spine", "apron", (0, 0.78, 0.21), (0, 1.06, 0.2), (0.22, 0.05), (0.2, 0.05), sides=4)      # peitoral
    H.box("spine", "belt", (0, 0.68, 0.24), (0.58, 0.1, 0.07))
    H.box("spine", "gold", (0, 0.68, 0.285), (0.12, 0.08, 0.03))


def backpack():
    H.box("spine", "gold", (0, 0.8, PACK_Z), (0.74, 0.76, 0.26))
    H.box("spine", "black", (0, 0.8, PACK_Z - 0.12), (0.64, 0.66, 0.05))
    for x in (-0.17, 0.17):
        for y in (0.63, 0.97):
            H.frustum("spine", "mine", (x, y, PACK_Z - 0.14), (x, y, PACK_Z - 0.22), (0.14, 0.14), (0.12, 0.12), sides=8)
            H.frustum("spine", "spike", (x, y, PACK_Z - 0.22), (x, y, PACK_Z - 0.27), (0.05, 0.05), (0.01, 0.01), sides=4)
    for s in (-1, 1):       # escapamentos
        H.chain("spine", "pipe", [S(s, (0.15, 1.15, PACK_Z + 0.04)), S(s, (0.28, 1.66, PACK_Z + 0.02))],
                [(0.07, 0.07), (0.09, 0.09)], sides=6)
        H.frustum("spine", "black", S(s, (0.27, 1.62, PACK_Z + 0.02)), S(s, (0.29, 1.7, PACK_Z + 0.02)), (0.09, 0.09), (0.1, 0.1), sides=6)


def claws():
    H.frustum("spine", "gold", (0, 1.15, PACK_Z), (0, 1.64, PACK_Z), (0.06, 0.06), (0.05, 0.05), sides=6)
    H.frustum("spine", "gold", (0, 1.6, PACK_Z), (0, 1.74, PACK_Z), (0.1, 0.1), (0.1, 0.1), sides=8)
    for s in (-1, 1):
        hub, elbow, wrist = (0, 1.72, PACK_Z), (0.28, 2.0, PACK_Z + 0.2), (0.64, 1.95, PACK_Z + 0.46)
        H.chain("spine", "gold", [S(s, hub), S(s, elbow), S(s, wrist)], [(0.06, 0.06), (0.055, 0.055), (0.05, 0.05)], sides=6)
        H.frustum("spine", "gold", S(s, (0.28, 2.0, PACK_Z + 0.14)), S(s, (0.28, 2.0, PACK_Z + 0.26)), (0.11, 0.11), (0.11, 0.11), sides=8)
        H.frustum("spine", "gold", S(s, (0.64, 1.95, PACK_Z + 0.4)), S(s, (0.64, 1.95, PACK_Z + 0.52)), (0.1, 0.1), (0.1, 0.1), sides=8)
        for tip in ((0.84, 2.06), (0.84, 1.78)):
            H.chain("spine", "gold", [S(s, (0.64, 1.95, PACK_Z + 0.46)), S(s, (0.76, (tip[1] + 1.95) / 2, PACK_Z + 0.5)),
                                     S(s, (tip[0], tip[1], PACK_Z + 0.52))],
                    [(0.05, 0.05), (0.04, 0.04), (0.012, 0.012)], sides=4)


def arm_pose(s):
    """Ombro, cotovelo, mão do braço do lado s."""
    return S(s, (0.4, SHOULDER_Y, 0.0)), S(s, (0.52, 0.76, 0.08)), S(s, (0.5, 0.5, 0.2))


def arm(side, s):
    sh, el, hand = arm_pose(s)
    H.frustum("arm." + side, "skin", (sh[0], sh[1] + 0.06, sh[2]), el, (0.18, 0.18), (0.14, 0.14), sides=8)       # ombro grosso
    fore = "forearm." + side
    H.frustum(fore, "skin", el, (hand[0], hand[1] + 0.06, hand[2]), (0.15, 0.15), (0.18, 0.18), sides=8)  # antebraço alarga no punho
    H.frustum(fore, "skin_dk", (hand[0], hand[1] + 0.08, hand[2]), (hand[0], hand[1] - 0.08, hand[2]), (0.18, 0.17), (0.14, 0.14), sides=6)


def mine():
    cx, cy, cz = 0.52, 0.5, 0.3
    for (y0, y1, r0, r1) in ((-0.2, -0.08, 0.1, 0.2), (-0.08, 0.1, 0.2, 0.21), (0.1, 0.2, 0.21, 0.1)):
        H.frustum("forearm.L", "mine", (cx, cy + y0, cz), (cx, cy + y1, cz), (r0, r0), (r1, r1), sides=8)
    for d in ((0, 1, 0), (1, 0.2, 0), (0, 0.2, 1), (0, 0.2, -1), (0.6, 0.8, 0), (0, -1, 0.3)):
        a = (cx + d[0] * 0.19, cy + d[1] * 0.19, cz + d[2] * 0.19)
        b = (cx + d[0] * 0.36, cy + d[1] * 0.36, cz + d[2] * 0.36)
        H.frustum("forearm.L", "spike", a, b, (0.06, 0.06), (0.012, 0.012), sides=4)


def wrench():
    x0, y0, z0 = -0.38, 0.22, 0.14
    x1, y1, z1 = -0.66, 0.86, 0.46
    H.frustum("forearm.R", "wrench", (x0, y0, z0), (x1, y1, z1), (0.055, 0.055), (0.065, 0.065), sides=6)
    H.frustum("forearm.R", "wrench", (x1, y1, z1 - 0.04), (x1, y1, z1 + 0.04), (0.18, 0.18), (0.18, 0.18), sides=8)
    for dx in (-0.09, 0.09):
        H.box("forearm.R", "wrench", (x1 + dx * 1.3, y1 + 0.2, z1), (0.1, 0.24, 0.08))
    H.box("forearm.R", "black", (x1, y1 + 0.2, z1), (0.12, 0.2, 0.09))


def head():
    H.frustum("head", "skin", (0, 1.16, 0.1), (0, 1.32, 0.1), (0.14, 0.15), (0.21, 0.19), sides=8)       # mandíbula
    H.frustum("head", "skin", (0, 1.3, 0.1), (0, 1.5, 0.08), (0.21, 0.19), (0.19, 0.19), sides=8)        # crânio
    H.frustum("head", "skin", (0, 1.49, 0.08), (0, 1.57, 0.08), (0.19, 0.19), (0.1, 0.1), sides=8)
    H.chain("head", "hair", [(0, 1.52, 0.2), (0, 1.69, 0.06), (0, 1.62, -0.16)], [(0.04, 0.05), (0.05, 0.1), (0.03, 0.06)], sides=4)
    H.frustum("head", "nose", (0, 1.31, 0.2), (0, 1.2, 0.46), (0.08, 0.08), (0.03, 0.03), sides=6)         # nariz comprida
    H.box("head", "tooth", (0, 1.22, 0.2), (0.2, 0.05, 0.05))
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.1, 1.4, 0.2), (0.1, 0.05, 0.05))
        H.frustum("head", "skin", (s * 0.18, 1.38, 0.05), (s * 0.66, 1.48, -0.06), (0.14, 0.035), (0.02, 0.02), sides=4)   # orelha


def make():
    torso()
    backpack()
    claws()
    head()
    for side, s in (("L", 1), ("R", -1)):
        leg(side, s)
        arm(side, s)
    mine()
    wrench()


def joints():
    out = {"pelvis": ((0, 0.55, 0.0), (0, 0.78, 0.0)), "spine": ((0, 0.78, 0.0), (0, 1.14, 0.0)),
           "head": ((0, 1.14, 0.0), (0, 1.6, 0.0))}
    for side, s in (("L", 1), ("R", -1)):
        x = s * LEG_X
        out["thigh." + side] = ((x, 0.66, 0.0), (x, 0.4, 0.01))
        out["shin." + side] = ((x, 0.4, 0.01), (x, 0.1, 0.0))
        out["foot." + side] = ((x, 0.1, 0.0), (x, 0.07, 0.3))
        sh, el, hand = arm_pose(s)
        out["arm." + side] = (sh, el)
        out["forearm." + side] = (el, hand)
    return out


H.build("h06U", "biped", PALETTE, make, joints())
