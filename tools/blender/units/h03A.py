"""Defender (h03A): medido em artifacts/model-sheets/refs/h03A/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/h03A.py -- <out.glb>

Casaco verde comprido, capacete de ferro com viseira, escudo de torre no braco esquerdo (antebraco para a frente),
faca curta na mao direita, lampiao no cinto. Olha para +z; o escudo fica a frente do corpo.
"""
import pathlib
import sys

from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "coat": 0x4F5B47, "coat_dk": 0x3F4838, "helmet": 0x70757B, "helmet_dk": 0x50555B, "visor": 0x15171A,
    "shield": 0x3B3E46, "shield_dk": 0x2B2D33, "cross": 0xE9DCC0, "strap": 0x5B3E2B, "pouch": 0x4A4C36,
    "boot": 0x1F2022, "breech": 0x2D3030, "glove": 0x5A3E2C, "blade": 0x9AA0A6, "lamp": 0xFFB02A, "lamp_fr": 0x5A4630,
}

HIP, KNEE, ANKLE, LEG_X = 1.12, 0.62, 0.17, 0.2
WAIST, NECK, TOP = 1.4, 2.15, 2.7
SKIRT_MID = 0.95
ZC = -0.03


def hem(p):
    """A barra do casaco acompanha a coxa do seu lado; o topo fica na pelve."""
    if p[1] > SKIRT_MID:
        return {"pelvis": 1.0}
    return {"pelvis": 0.45, "thigh.L" if p[0] > 0 else "thigh.R": 0.55}


def head():
    H.frustum("head", "coat", (0, 2.08, ZC), (0, 2.32, ZC), (0.3, 0.26), (0.28, 0.24), sides=8)          # gola alta
    H.frustum("head", "visor", (0, 2.2, 0.08), (0, 2.42, 0.1), (0.2, 0.2), (0.22, 0.22), sides=8)
    H.frustum("head", "helmet", (0, 2.3, 0.08), (0, 2.5, 0.08), (0.27, 0.28), (0.24, 0.26), sides=8)
    H.frustum("head", "helmet", (0, 2.5, 0.08), (0, 2.7, 0.06), (0.24, 0.26), (0.13, 0.14), sides=8)
    H.frustum("head", "helmet_dk", (0, 2.4, -0.12), (0, 2.34, -0.2), (0.29, 0.2), (0.34, 0.16), sides=8)   # aba de tras
    H.box("head", "visor", (0, 2.4, 0.33), (0.36, 0.07, 0.06))                                             # fenda


def torso():
    rings = [(WAIST, 0.38, 0.3), (1.8, 0.46, 0.32), (2.12, 0.46, 0.28)]
    for (y0, w0, d0), (y1, w1, d1) in zip(rings, rings[1:]):
        H.frustum("spine", "coat", (0, y0, ZC), (0, y1, ZC), (w0, d0), (w1, d1), sides=8)
    H.frustum("pelvis", "strap", (0, WAIST - 0.09, ZC), (0, WAIST + 0.07, ZC), (0.42, 0.34), (0.42, 0.34), sides=8)
    skirt = H.frustum("pelvis", "coat", (0, 0.5, ZC), (0, WAIST - 0.05, ZC), (0.5, 0.46), (0.42, 0.33), sides=8)
    H.soft(skirt, hem)
    H.box("pelvis", "pouch", (0.42, 1.2, -0.22), (0.2, 0.3, 0.22))
    H.box("pelvis", "pouch", (0.2, 1.3, 0.3), (0.2, 0.2, 0.14))
    for s in (-1, 1):       # X de correias nas costas
        H.frustum("spine", "strap", (s * 0.34, 2.08, -0.3), (-s * 0.3, 1.45, -0.3), (0.06, 0.03), (0.06, 0.03), sides=4)
    # lampiao no cinto, lado direito
    H.frustum("pelvis", "lamp_fr", (-0.5, 1.0, 0.0), (-0.5, 1.4, 0.0), (0.1, 0.1), (0.1, 0.1), sides=6)
    H.frustum("pelvis", "lamp", (-0.5, 1.06, 0.0), (-0.5, 1.34, 0.0), (0.13, 0.13), (0.13, 0.13), sides=6)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * LEG_X
        H.frustum(f"thigh.{side}", "breech", (x, KNEE, 0), (x, HIP + 0.04, 0), (0.18, 0.2), (0.21, 0.23), sides=6)
        H.frustum(f"shin.{side}", "boot", (x, ANKLE, 0), (x, KNEE + 0.02, 0), (0.17, 0.19), (0.2, 0.21), sides=6)
        H.frustum(f"foot.{side}", "boot", (x, 0.03, -0.04), (x, ANKLE + 0.04, -0.04), (0.18, 0.21), (0.17, 0.19), sides=6)
        H.frustum(f"foot.{side}", "boot", (x, 0.11, 0.05), (x, 0.08, 0.4), (0.18, 0.1), (0.16, 0.06), sides=4)
        H.frustum(f"foot.{side}", "visor", (x, 0.02, -0.2), (x, 0.02, 0.42), (0.19, 0.022), (0.17, 0.022), sides=4)


def left_arm_shield():
    H.frustum("arm.L", "coat", (0.5, 2.15, -0.02), (0.5, 1.88, 0.14), (0.2, 0.22), (0.19, 0.2), sides=6)
    fa = "forearm.L"
    H.frustum(fa, "coat", (0.5, 1.86, 0.1), (0.5, 1.84, 0.4), (0.18, 0.2), (0.16, 0.17), sides=6)
    H.frustum(fa, "glove", (0.5, 1.84, 0.38), (0.5, 1.82, 0.56), (0.15, 0.16), (0.14, 0.15), sides=6)
    H.box(fa, "shield", (0.33, 1.43, 0.62), (0.96, 1.95, 0.14))
    H.box(fa, "shield_dk", (0.33, 1.43, 0.55), (1.0, 1.99, 0.06))
    H.box(fa, "cross", (0.33, 1.6, 0.7), (0.54, 0.16, 0.02))
    H.box(fa, "cross", (0.33, 1.6, 0.7), (0.17, 0.62, 0.02))


def right_arm_knife():
    H.frustum("arm.R", "coat", (-0.5, 2.14, 0), (-0.58, 1.55, 0.02), (0.2, 0.22), (0.17, 0.19), sides=6)
    fa = "forearm.R"
    H.frustum(fa, "coat", (-0.58, 1.6, 0.02), (-0.62, 1.22, 0.05), (0.17, 0.19), (0.14, 0.15), sides=6)
    H.frustum(fa, "glove", (-0.62, 1.24, 0.05), (-0.63, 1.04, 0.08), (0.14, 0.15), (0.12, 0.13), sides=6)
    grip, hilt, tip = Vector((-0.62, 1.12, 0.08)), Vector((-0.66, 1.0, 0.2)), Vector((-0.88, 0.5, 0.65))
    H.frustum(fa, "strap", grip, hilt, (0.06, 0.06), (0.06, 0.06), sides=4)
    H.frustum(fa, "blade", hilt, tip, (0.11, 0.045), (0.005, 0.005), sides=4)


def make():
    head()
    torso()
    legs()
    left_arm_shield()
    right_arm_knife()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)), "head": ((0, NECK, 0), (0, TOP, 0)),
           "arm.L": ((0.5, 2.15, 0.1), (0.5, 1.86, 0.1)), "forearm.L": ((0.5, 1.86, 0.1), (0.5, 1.45, 0.1)),
           "arm.R": ((-0.5, 2.14, 0), (-0.58, 1.55, 0)), "forearm.R": ((-0.58, 1.55, 0), (-0.62, 1.12, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("h03A", "biped", PALETTE, make, joints())
