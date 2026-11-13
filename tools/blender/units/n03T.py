"""Sagepaw Soulkeeper (n03T): medido em artifacts/model-sheets/refs/n03T/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n03T.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "coat": 0x6A6A72, "coat_dk": 0x55555C, "gold": 0xC89A3C, "red": 0xA82224, "red_dk": 0x6E1418,
    "black": 0x1F1D21, "white": 0xF0ECE6, "hat": 0xC09040, "iron": 0x3A363B, "iron_dk": 0x27242A,
    "glow": 0xD8603C, "ladle": 0x343036, "glove": 0x77777F,
}

HIP, KNEE, ANKLE, LEG_X = 0.78, 0.42, 0.1, 0.28
WAIST, NECK, TOP = 1.25, 1.95, 2.75
SH_X, SH_Y = 0.72, 2.0
SKIRT_MID = 0.85


def hem(p):
    """A barra do casaco acompanha a coxa do seu lado; o topo fica na pelve."""
    if p[1] > SKIRT_MID:
        return {"pelvis": 1.0}
    return {"pelvis": 0.45, "thigh.L" if p[0] > 0 else "thigh.R": 0.55}


def head():
    H.frustum("head", "white", (0, 1.95, 0.02), (0, 2.2, 0.03), (0.24, 0.24), (0.31, 0.3), sides=8)
    H.frustum("head", "white", (0, 2.2, 0.03), (0, 2.45, 0.02), (0.31, 0.3), (0.26, 0.25), sides=8)
    H.frustum("head", "white", (0, 2.12, 0.28), (0, 2.1, 0.5), (0.15, 0.12), (0.1, 0.08), sides=6)     # focinho
    H.box("head", "black", (0, 2.17, 0.52), (0.1, 0.07, 0.05))
    for s in (-1, 1):
        H.box("head", "black", (s * 0.14, 2.28, 0.3), (0.12, 0.14, 0.08))       # manchas dos olhos
        H.box("head", "white", (s * 0.15, 2.29, 0.335), (0.04, 0.04, 0.02))
        H.frustum("head", "black", (s * 0.3, 2.5, 0.0), (s * 0.34, 2.64, 0.0), (0.15, 0.12), (0.12, 0.08), sides=6)  # orelhas
    H.frustum("head", "hat", (0, 2.4, 0.0), (0, 2.5, 0.0), (0.7, 0.6), (0.55, 0.42), sides=8)               # aba do chapéu
    H.frustum("head", "gold", (0, 2.38, 0.0), (0, 2.42, 0.0), (0.7, 0.68), (0.7, 0.68), sides=8)
    H.frustum("head", "hat", (0, 2.5, 0.0), (0, 2.68, 0.0), (0.42, 0.3), (0.3, 0.22), sides=8)
    H.frustum("head", "black", (0, 1.84, 0.0), (0, 2.0, 0.0), (0.4, 0.34), (0.32, 0.28), sides=8)       # gola preta


def torso():
    H.frustum("pelvis", "coat", (0, 0.5, 0), (0, WAIST, 0), (0.64, 0.6), (0.66, 0.6), sides=8)
    skirt = H.frustum("pelvis", "coat", (0, 0.46, 0), (0, 0.9, 0), (0.7, 0.62), (0.66, 0.6), sides=8)
    H.soft(skirt, hem)
    H.frustum("pelvis", "gold", (0, 0.43, 0), (0, 0.5, 0), (0.72, 0.7), (0.71, 0.68), sides=8)        # barra dourada
    H.frustum("pelvis", "red", (0, 0.98, 0), (0, 1.1, 0), (0.67, 0.62), (0.67, 0.62), sides=8)        # faixa
    H.frustum("spine", "coat", (0, WAIST - 0.05, 0), (0, 1.9, 0), (0.64, 0.6), (0.68, 0.55), sides=8)
    H.frustum("spine", "coat", (0, 1.9, 0), (0, 2.12, 0), (0.68, 0.55), (0.34, 0.3), sides=8)         # ombros
    H.frustum("spine", "red", (0.32, 2.08, 0.46), (-0.28, 1.2, 0.58), (0.09, 0.04), (0.09, 0.04), sides=4)   # faixa cruzada
    H.frustum("spine", "red", (-0.32, 2.08, 0.46), (0.28, 1.2, 0.58), (0.09, 0.04), (0.09, 0.04), sides=4)


def pot():
    z = -0.74
    for (y0, y1, r0, r1) in ((1.02, 1.3, 0.34, 0.52), (1.3, 1.75, 0.52, 0.6), (1.75, 2.12, 0.6, 0.5), (2.12, 2.3, 0.5, 0.3)):
        H.frustum("spine", "red", (0, y0, z), (0, y1, z), (r0, r0), (r1, r1), sides=8)
    H.frustum("spine", "red_dk", (0, 1.0, z), (0, 1.04, z), (0.3, 0.3), (0.3, 0.3), sides=8)            # boca de baixo
    H.frustum("spine", "red_dk", (0, 2.28, z), (0, 2.36, z), (0.26, 0.26), (0.2, 0.2), sides=8)         # tampa
    for s in (-1, 1):      # bicos
        H.frustum("spine", "red", (s * 0.3, 2.15, z + 0.12), (s * 0.5, 2.48, z + 0.2), (0.13, 0.1), (0.14, 0.12), sides=6)
        H.frustum("spine", "red_dk", (s * 0.5, 2.48, z + 0.2), (s * 0.52, 2.52, z + 0.21), (0.1, 0.1), (0.07, 0.07), sides=6)
        H.frustum("spine", "red", (s * 0.34, 1.9, -0.2), (s * 0.34, 2.0, -0.55), (0.05, 0.05), (0.05, 0.05), sides=4)   # correia


def stove():
    H.box("pelvis", "iron", (0, 0.92, 0.76), (0.88, 0.5, 0.68))
    H.box("pelvis", "iron_dk", (0, 1.2, 0.76), (0.94, 0.07, 0.74))
    H.box("pelvis", "glow", (0, 0.88, 1.12), (0.46, 0.3, 0.04))
    H.frustum("pelvis", "iron", (-0.05, 1.2, 0.7), (-0.05, 1.62, 0.7), (0.08, 0.08), (0.07, 0.07), sides=4)
    H.frustum("pelvis", "iron_dk", (-0.05, 1.58, 0.7), (-0.05, 1.64, 0.7), (0.1, 0.1), (0.1, 0.1), sides=4)
    for sx in (-1, 1):
        for sz in (0.5, 1.02):
            H.frustum("pelvis", "iron_dk", (sx * 0.38, 0.5, sz), (sx * 0.38, 0.68, sz), (0.04, 0.04), (0.04, 0.04), sides=4)
    H.frustum("pelvis", "iron_dk", (-0.8, 0.98, 0.78), (0.78, 0.98, 0.78), (0.035, 0.035), (0.035, 0.035), sides=6)   # varal


def leg(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "black", (x, KNEE - 0.04, 0), (x, HIP + 0.05, 0), (0.24, 0.25), (0.3, 0.3), sides=6)
    H.frustum(f"shin.{side}", "black", (x, ANKLE + 0.14, 0), (x, KNEE + 0.02, 0), (0.22, 0.25), (0.25, 0.28), sides=6)
    H.frustum(f"shin.{side}", "white", (x, ANKLE, 0.0), (x, ANKLE + 0.18, 0.0), (0.26, 0.24), (0.24, 0.22), sides=6)
    H.frustum(f"foot.{side}", "white", (x, 0.1, -0.03), (x, 0.09, 0.36), (0.26, 0.2), (0.22, 0.12), sides=6)
    H.frustum(f"foot.{side}", "white", (x, 0.04, -0.2), (x, 0.04, 0.42), (0.25, 0.04), (0.2, 0.04), sides=4)


def arm_l():
    H.frustum("arm.L", "coat", (SH_X - 0.04, SH_Y + 0.08, 0), (0.84, 1.7, 0.02), (0.27, 0.29), (0.29, 0.3), sides=6)
    H.frustum("arm.L", "coat", (0.84, 1.7, 0.02), (0.9, 1.4, 0.06), (0.29, 0.3), (0.27, 0.27), sides=6)
    H.frustum("forearm.L", "gold", (0.9, 1.42, 0.06), (0.9, 1.34, 0.08), (0.28, 0.28), (0.27, 0.27), sides=6)
    H.frustum("forearm.L", "glove", (0.9, 1.34, 0.08), (0.92, 1.0, 0.16), (0.22, 0.22), (0.2, 0.2), sides=6)
    H.frustum("forearm.L", "glove", (0.94, 1.12, 0.2), (0.94, 1.72, 0.2), (0.2, 0.24), (0.2, 0.2), sides=6)   # punho
    # concha: cabo vermelho/preto na frente do braco e bojo grande de frente
    px, pz = 0.96, 0.4
    H.frustum("forearm.L", "ladle", (px, 0.4, pz), (px, 1.0, pz), (0.06, 0.06), (0.06, 0.06), sides=6)
    H.frustum("forearm.L", "red", (px, 0.4, pz), (px, 0.8, pz), (0.07, 0.07), (0.07, 0.07), sides=6)
    H.frustum("forearm.L", "red", (px, 1.0, pz), (px, 1.9, pz), (0.065, 0.065), (0.065, 0.065), sides=6)
    H.frustum("forearm.L", "ladle", (px, 1.9, pz), (px, 2.2, pz), (0.06, 0.06), (0.06, 0.06), sides=6)
    H.frustum("forearm.L", "ladle", (px, 2.2, pz), (px, 2.28, pz), (0.06, 0.06), (0.3, 0.3), sides=8)
    H.frustum("forearm.L", "ladle", (px, 2.28, pz), (px, 2.56, pz), (0.3, 0.3), (0.3, 0.3), sides=8)


def arm_r():
    H.frustum("arm.R", "coat", (-SH_X + 0.04, SH_Y + 0.08, 0), (-0.88, 1.7, 0.02), (0.3, 0.32), (0.32, 0.34), sides=6)
    H.frustum("arm.R", "coat", (-0.88, 1.7, 0.02), (-0.9, 1.4, 0.12), (0.32, 0.34), (0.3, 0.3), sides=6)
    H.frustum("forearm.R", "gold", (-0.9, 1.42, 0.12), (-0.88, 1.34, 0.2), (0.31, 0.31), (0.3, 0.3), sides=6)
    H.frustum("forearm.R", "glove", (-0.88, 1.34, 0.2), (-0.8, 1.05, 0.55), (0.24, 0.24), (0.2, 0.2), sides=6)
    H.frustum("forearm.R", "glove", (-0.8, 1.08, 0.55), (-0.78, 0.9, 0.78), (0.2, 0.24), (0.22, 0.22), sides=6)  # punho no varal


def make():
    head()
    torso()
    pot()
    stove()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    arm_l()
    arm_r()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * 0.9, 1.4, 0.04))
        out[f"forearm.{side}"] = ((s * 0.9, 1.4, 0.04), (s * 0.9, 0.9, 0.1))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("n03T", "biped", PALETTE, make, joints())
