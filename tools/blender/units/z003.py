"""Flamegunner Sergeant (z003): medido em artifacts/model-sheets/refs/z003/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/z003.py -- <out.glb>

Orc atarracado de capacete de aba com chifres, ombreiras vermelhas, avental de couro; o lanca-chamas (cabo de
madeira, caixa de cobre furada, cano cinza, chama) vai na mao DIREITA do orc (esquerda da imagem de frente), na
altura do quadril, apontando a frente e um pouco para dentro.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "skin": 0x6E9A4A, "skin_dk": 0x56803A, "tusk": 0xF0E6B8, "black": 0x1E1C22, "gold": 0xB08A48, "red": 0x7A2A26,
    "tunic": 0x636772, "tunic_dk": 0x52555F, "apron": 0x5A3A2A, "strap": 0x45301F, "pants": 0x25262B,
    "boot": 0x3A2A2C, "wood": 0x7A4E2A, "copper": 0xB89A6A, "hole": 0x3B2E22, "steel": 0x6A6B6A, "steel_dk": 0x4A4B4C,
    "flame": 0xFFD52A, "plate": 0x7C7D86, "scarf": 0x1F1F24, "steel_lt": 0x8A8B92,
}

HIP_X, KNEE_X, ANK_X = 0.33, 0.38, 0.4
HIP, KNEE, ANKLE = 1.05, 0.58, 0.16
WAIST, NECK, TOP = 1.3, 2.05, 2.72
SH, EL = (0.62, 2.0, -0.05), (0.74, 1.3, -0.25)
WR_L, WR_R = (0.74, 0.88, -0.05), (0.64, 1.0, 0.05)       # mao direita segura o lanca-chamas
ARMS = ((1, "L", WR_L), (-1, "R", WR_R))


def horns():
    for s in (-1, 1):
        H.chain("head", "gold", [(s * 0.3, 2.5, 0), (s * 0.42, 2.58, 0), (s * 0.47, 2.72, 0), (s * 0.4, 2.82, 0)],
                [(0.07, 0.07), (0.06, 0.06), (0.04, 0.04), (0.01, 0.01)], sides=6)


def head():
    H.frustum("head", "skin", (0, 2.02, 0.0), (0, 2.42, 0.04), (0.22, 0.22), (0.25, 0.24), sides=6)       # rosto largo
    H.frustum("head", "skin_dk", (0, 2.2, 0.2), (0, 2.28, 0.3), (0.07, 0.05), (0.05, 0.04), sides=4)      # nariz
    for s in (-1, 1):
        H.frustum("head", "tusk", (s * 0.1, 2.1, 0.2), (s * 0.1, 2.24, 0.24), (0.03, 0.025), (0.012, 0.01), sides=4)
        H.frustum("head", "skin", (s * 0.22, 2.28, 0.0), (s * 0.36, 2.4, -0.02), (0.07, 0.05), (0.02, 0.02), sides=4)
    H.box("head", "black", (0, 2.4, 0.2), (0.46, 0.1, 0.08))                                              # sombra dos olhos
    H.frustum("head", "black", (0, 2.42, 0), (0, 2.5, 0), (0.46, 0.44), (0.4, 0.38), sides=8)            # aba
    H.frustum("head", "black", (0, 2.5, 0), (0, 2.64, 0), (0.32, 0.31), (0.25, 0.24), sides=8)           # copa
    H.frustum("head", "black", (0, 2.64, 0), (0, 2.7, 0), (0.25, 0.24), (0.12, 0.12), sides=8)
    horns()
    H.chain("head", "gold", [(0, 2.66, 0.0), (0, 2.78, 0.0), (0, 2.9, 0.0)], [(0.04, 0.2), (0.03, 0.14), (0.005, 0.01)], sides=4)
    for z in (-0.22, -0.11, 0.0, 0.11, 0.22):       # espinhos do capacete, vistos no perfil
        H.frustum("head", "gold", (0, 2.6, z), (0, 2.88 - abs(z) * 0.4, z * 2.2), (0.04, 0.04), (0.005, 0.005), sides=4)
    H.frustum("head", "scarf", (0, 1.98, 0), (0, 2.14, 0), (0.3, 0.28), (0.34, 0.32), sides=8)           # gola preta


def torso():
    H.frustum("spine", "tunic", (0, WAIST - 0.05, 0), (0, 1.95, 0), (0.5, 0.38), (0.58, 0.4), sides=8)
    H.frustum("spine", "tunic", (0, 1.95, 0), (0, 2.14, 0), (0.55, 0.36), (0.3, 0.26), sides=8)
    H.frustum("spine", "plate", (0, 1.4, 0.0), (0, 1.98, 0.04), (0.44, 0.38), (0.5, 0.4), sides=8)
    H.frustum("spine", "apron", (0, 1.28, 0.3), (0, 1.3, 0.34), (0.32, 0.05), (0.3, 0.05), sides=4)
    H.frustum("pelvis", "apron", (0, 0.66, 0.4), (0, 1.3, 0.36), (0.36, 0.05), (0.34, 0.05), sides=4)
    for s in (-1, 1):       # alcas do avental e x das costas
        H.frustum("spine", "strap", (s * 0.22, 2.1, 0.28), (s * 0.22, 1.9, 0.33), (0.045, 0.03), (0.05, 0.03), sides=4)
        H.frustum("spine", "strap", (s * 0.34, 2.05, -0.36), (-s * 0.3, 1.4, -0.4), (0.07, 0.03), (0.07, 0.03), sides=4)
    H.frustum("pelvis", "strap", (0, WAIST - 0.12, 0), (0, WAIST + 0.04, 0), (0.5, 0.4), (0.5, 0.4), sides=8)   # cinto
    H.box("pelvis", "gold", (0, WAIST - 0.04, 0.42), (0.2, 0.17, 0.04))
    H.frustum("pelvis", "pants", (0, 0.8, 0), (0, 1.15, 0), (0.44, 0.34), (0.5, 0.38), sides=8)


def leg(s, side):
    H.frustum(f"thigh.{side}", "pants", (s * KNEE_X, KNEE + 0.04, 0.02), (s * HIP_X, HIP + 0.06, 0), (0.22, 0.24), (0.29, 0.3), sides=6)
    H.frustum(f"shin.{side}", "strap", (s * ANK_X, ANKLE, 0), (s * KNEE_X, KNEE + 0.02, 0.02), (0.2, 0.2), (0.22, 0.22), sides=6)
    H.frustum(f"shin.{side}", "steel_lt", (s * ANK_X, 0.2, 0.15), (s * KNEE_X, 0.62, 0.17), (0.17, 0.07), (0.2, 0.07), sides=4)    # greva
    H.frustum(f"shin.{side}", "boot", (s * ANK_X, 0.1, 0), (s * ANK_X, 0.36, 0), (0.2, 0.21), (0.24, 0.24), sides=6)         # bota, boca larga
    H.frustum(f"foot.{side}", "boot", (s * ANK_X, 0.03, -0.05), (s * ANK_X, ANKLE + 0.04, -0.05), (0.2, 0.22), (0.19, 0.2), sides=6)
    H.frustum(f"foot.{side}", "boot", (s * ANK_X, 0.11, -0.02), (s * ANK_X, 0.07, 0.34), (0.2, 0.14), (0.18, 0.08), sides=4)
    H.frustum(f"foot.{side}", "black", (s * ANK_X, 0.02, -0.26), (s * ANK_X, 0.02, 0.34), (0.21, 0.02), (0.19, 0.02), sides=4)


def arm(s, side, wr):
    a, f = f"arm.{side}", f"forearm.{side}"
    H.frustum(a, "red", (s * 0.4, 2.12, -0.03), (s * 0.82, 1.78, -0.03), (0.17, 0.3), (0.2, 0.3), sides=6)      # ombreira
    H.frustum(a, "red", (s * 0.5, 2.0, -0.03), (s * 0.9, 1.68, -0.03), (0.2, 0.32), (0.22, 0.32), sides=6)
    H.frustum(a, "gold", (s * 0.8, 1.8, -0.03), (s * 0.86, 1.74, -0.03), (0.2, 0.32), (0.2, 0.32), sides=6)
    H.frustum(a, "tunic", (s * (SH[0] + 0.02), SH[1] - 0.05, SH[2]), (s * EL[0], EL[1] + 0.02, EL[2]), (0.22, 0.24), (0.2, 0.21), sides=6)
    H.frustum(f, "tunic_dk", (s * EL[0], EL[1] + 0.05, EL[2]), (s * wr[0], wr[1] + 0.12, wr[2]), (0.21, 0.22), (0.2, 0.2), sides=6)
    H.frustum(f, "skin", (s * wr[0], wr[1] + 0.14, wr[2]), (s * wr[0], wr[1] - 0.04, wr[2] + 0.02), (0.17, 0.17), (0.19, 0.18), sides=6)
    H.frustum(f, "skin_dk", (s * wr[0], wr[1] - 0.02, wr[2] + 0.02), (s * wr[0], wr[1] - 0.18, wr[2] + 0.04), (0.18, 0.17), (0.12, 0.12), sides=6)


def flamethrower():
    """Cabo na mao direita, caixa de cobre grande e DOIS canos empilhados a frente, chama na ponta (antebraco R)."""
    f = "forearm.R"
    H.frustum(f, "wood", (-0.62, 0.8, -0.38), (-0.56, 1.08, 0.18), (0.06, 0.06), (0.05, 0.05), sides=4)
    a, b = (-0.58, 1.08, 0.12), (-0.54, 1.1, 0.54)
    H.frustum(f, "copper", a, b, (0.2, 0.22), (0.2, 0.22), sides=4)
    H.frustum(f, "hole", (-0.54, 1.1, 0.52), (-0.54, 1.1, 0.56), (0.1, 0.1), (0.09, 0.09), sides=4)
    for dy in (-0.09, 0.09):
        c = (-0.4, 1.1 + dy, 0.98)
        H.frustum(f, "steel", (-0.54, 1.1 + dy, 0.54), c, (0.075, 0.075), (0.075, 0.075), sides=4)
        H.frustum(f, "steel_dk", (c[0], c[1], 0.95), (c[0] + 0.01, c[1], 1.0), (0.085, 0.085), (0.085, 0.085), sides=4)
    H.frustum(f, "flame", (-0.4, 1.28, 1.0), (-0.38, 1.52, 1.04), (0.07, 0.06), (0.005, 0.005), sides=4)


def make():
    head()
    torso()
    for s, side, wr in ARMS:
        leg(s, side)
        arm(s, side, wr)
    flamethrower()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)), "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side, wr in ARMS:
        out[f"arm.{side}"] = ((s * SH[0], SH[1], SH[2]), (s * EL[0], EL[1], EL[2]))
        out[f"forearm.{side}"] = ((s * EL[0], EL[1], EL[2]), (s * wr[0], wr[1], wr[2]))
        out[f"thigh.{side}"] = ((s * HIP_X, HIP, 0), (s * KNEE_X, KNEE, 0.02))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0.02), (s * ANK_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * ANK_X, ANKLE, 0), (s * ANK_X, 0.06, 0.4))
    return out


H.build("z003", "biped", PALETTE, make, joints())
