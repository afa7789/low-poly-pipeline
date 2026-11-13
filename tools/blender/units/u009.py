"""Mighty Necromancer (u009): medido em artifacts/model-sheets/refs/u009/sheet.jpg. Cajado alto de chama verde na mão direita
(a direita dele, esquerda da prancha), mão livre esquerda com fogo verde; casaco longo, ombreiras, capuz com chifres.

    blender -b --factory-startup -P tools/blender/units/u009.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "coat": 0x5E3A30, "coat_dk": 0x3A2420, "purple": 0x6E4E78, "gold": 0xC09A4A, "bone": 0xE2D3AE, "bone_dk": 0xB9A682,
    "skin_gr": 0x7E8C72, "void": 0x1A1214, "boot": 0x3A2A28, "sole": 0xA88A5A, "pants": 0x2B1E22, "belt": 0x3E2A26,
    "wood": 0x4A4440, "steel": 0x6A6660, "jade": 0x2E9E70, "flame": 0x60E898, "flame_lt": 0xB4FFD0, "eye": 0x38F08C,
}

HIP, KNEE, ANKLE, LEG_X = 1.1, 0.6, 0.17, 0.2
WAIST, NECK, TOP = 1.5, 2.2, 2.78
SH = (0.5, 2.05, 0.0)
EL_L, WR_L = (0.58, 1.6, 0.05), (0.64, 1.38, 0.4)
EL_R, WR_R = (0.55, 1.6, 0.2), (0.58, 1.5, 0.38)
STAFF_X, STAFF_Z = -0.58, 0.38
SKIRT_MID = (0.45 + WAIST) / 2


def hem(p):
    """A barra do casaco acompanha a coxa do seu lado; o topo fica na pelve."""
    if p[1] > SKIRT_MID:
        return {"pelvis": 1.0}
    return {"pelvis": 0.45, "thigh.L" if p[0] > 0 else "thigh.R": 0.55}


def head():
    H.frustum("head", "coat", (0, 2.18, -0.02), (0, 2.52, -0.04), (0.23, 0.24), (0.25, 0.26), sides=8)         # capuz
    H.frustum("head", "coat", (0, 2.52, -0.04), (0, 2.72, -0.04), (0.25, 0.26), (0.13, 0.14), sides=8)
    H.frustum("head", "coat", (0, 2.72, -0.04), (0, 2.8, -0.04), (0.13, 0.14), (0.04, 0.04), sides=8)
    H.frustum("head", "void", (0, 2.2, 0.06), (0, 2.58, 0.06), (0.15, 0.1), (0.17, 0.11), sides=8)             # sombra do capuz
    H.frustum("head", "bone", (0, 2.22, 0.12), (0, 2.52, 0.16), (0.14, 0.12), (0.16, 0.13), sides=6)            # crânio
    H.box("head", "skin_gr", (0.07, 2.4, 0.26), (0.08, 0.2, 0.03))                                              # metade podre
    H.box("head", "bone_dk", (0, 2.25, 0.25), (0.14, 0.07, 0.04))                                               # dentes
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.06, 2.4, 0.265), (0.06, 0.05, 0.03))
        pts = [(s * 0.2, 2.46, 0.0), (s * 0.32, 2.52, 0.0), (s * 0.4, 2.64, 0.0), (s * 0.38, 2.82, 0.0)]
        H.chain("head", "bone", pts, [(0.07, 0.07), (0.06, 0.06), (0.045, 0.045), (0.008, 0.008)], sides=6)     # chifres
    H.frustum("head", "purple", (0, 2.05, -0.12), (0, 2.5, -0.15), (0.36, 0.2), (0.42, 0.26), sides=8)         # gola alta atrás
    H.frustum("head", "coat_dk", (0, 2.02, 0), (0, 2.22, 0), (0.3, 0.26), (0.28, 0.25), sides=8)


def torso():
    H.frustum("spine", "coat", (0, WAIST - 0.05, 0), (0, SH[1], 0), (0.4, 0.28), (0.5, 0.3), sides=8)
    H.frustum("spine", "coat", (0, SH[1], 0), (0, 2.28, 0), (0.5, 0.3), (0.3, 0.22), sides=8)
    H.box("spine", "bone", (0, 1.85, 0.26), (0.26, 0.55, 0.06))                                                # costelas
    H.box("spine", "gold", (0, 1.85, 0.3), (0.1, 0.42, 0.04))
    for s in (-1, 1):
        H.frustum("spine", "purple", (s * 0.22, 1.55, 0.27), (s * 0.2, 2.2, 0.26), (0.05, 0.03), (0.06, 0.03), sides=4)   # lapelas
    H.frustum("pelvis", "belt", (0, WAIST - 0.12, 0), (0, WAIST + 0.04, 0), (0.44, 0.31), (0.44, 0.31), sides=8)
    H.box("pelvis", "gold", (0, WAIST - 0.04, 0.31), (0.13, 0.13, 0.04))
    skirt = H.frustum("pelvis", "coat", (0, 0.42, 0), (0, WAIST - 0.08, 0), (0.62, 0.42), (0.42, 0.3), sides=8)
    H.soft(skirt, hem)
    H.frustum("pelvis", "coat", (0, 0.6, 0), (0, 1.0, 0), (0.56, 0.4), (0.5, 0.36), sides=8)


def leg(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "pants", (x, KNEE - 0.04, 0), (x, HIP + 0.04, 0), (0.16, 0.17), (0.19, 0.2), sides=6)
    H.frustum(f"shin.{side}", "boot", (x, ANKLE - 0.02, 0), (x, 0.38, 0), (0.17, 0.18), (0.18, 0.19), sides=6)
    H.frustum(f"shin.{side}", "boot", (x, 0.38, 0), (x, 0.66, 0), (0.18, 0.19), (0.22, 0.22), sides=6)        # cano largo
    H.frustum(f"foot.{side}", "boot", (x, 0.03, -0.02), (x, ANKLE + 0.04, -0.02), (0.18, 0.2), (0.17, 0.19), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.12, 0.06), (x, 0.09, 0.44), (0.18, 0.12), (0.15, 0.07), sides=4)
    H.frustum(f"foot.{side}", "sole", (x, 0.02, -0.18), (x, 0.02, 0.46), (0.19, 0.022), (0.16, 0.022), sides=4)


def shoulder_and_sleeve(s, side, el, wr):
    sx = s * SH[0]
    H.frustum(f"arm.{side}", "coat_dk", (sx, 2.22, 0), (s * 0.58, 1.9, 0), (0.26, 0.28), (0.34, 0.31), sides=8)     # ombreira
    H.frustum(f"arm.{side}", "gold", (s * 0.58, 1.9, 0), (s * 0.58, 1.84, 0), (0.35, 0.32), (0.34, 0.31), sides=8)
    H.frustum(f"arm.{side}", "coat", (sx, 2.0, 0), (s * el[0], el[1] + 0.04, el[2]), (0.22, 0.2), (0.19, 0.18), sides=8)
    H.frustum(f"forearm.{side}", "coat", (s * el[0], el[1] + 0.04, el[2]), (s * wr[0], wr[1] + 0.12, wr[2] - 0.03), (0.19, 0.18), (0.2, 0.19), sides=8)
    H.frustum(f"forearm.{side}", "purple", (s * wr[0], wr[1] + 0.13, wr[2] - 0.03), (s * wr[0], wr[1] + 0.05, wr[2]), (0.21, 0.2), (0.21, 0.2), sides=8)


def free_hand():
    """Mão esquerda aberta para a frente com fogo verde: o alvo do cast_shoot."""
    x, y, z = 0.64, 1.38, 0.4
    H.frustum("forearm.L", "bone", (x, y + 0.04, z - 0.04), (x, y - 0.14, z + 0.04), (0.12, 0.1), (0.15, 0.09), sides=6)
    H.frustum("forearm.L", "flame", (x, y - 0.12, z + 0.04), (x, y + 0.42, z + 0.1), (0.2, 0.18), (0.03, 0.03), sides=6)
    H.frustum("forearm.L", "flame_lt", (x, y - 0.12, z + 0.06), (x, y + 0.22, z + 0.1), (0.11, 0.1), (0.02, 0.02), sides=6)


def staff():
    x, z = STAFF_X, STAFF_Z
    H.frustum("forearm.R", "bone", (x, 1.42, z), (x, 1.62, z), (0.11, 0.1), (0.12, 0.11), sides=6)               # mão no cajado
    H.frustum("forearm.R", "wood", (x, 0.0, z), (x, 2.0, z), (0.06, 0.06), (0.055, 0.055), sides=6)
    H.frustum("forearm.R", "jade", (x, 1.8, z), (x, 2.04, z), (0.09, 0.09), (0.09, 0.09), sides=6)
    H.frustum("forearm.R", "steel", (x, 2.04, z), (x, 2.2, z), (0.11, 0.11), (0.14, 0.14), sides=6)
    for s in (-1, 1):
        pts = [(x + s * 0.1, 2.2, z), (x + s * 0.28, 2.38, z), (x + s * 0.3, 2.6, z), (x + s * 0.16, 2.84, z)]
        H.chain("forearm.R", "bone", pts, [(0.06, 0.06), (0.055, 0.055), (0.045, 0.045), (0.008, 0.008)], sides=6)
    H.frustum("forearm.R", "flame", (x, 2.2, z), (x, 2.5, z), (0.14, 0.14), (0.27, 0.27), sides=6)
    H.frustum("forearm.R", "flame", (x, 2.5, z), (x, 3.0, z), (0.27, 0.27), (0.02, 0.02), sides=6)
    H.frustum("forearm.R", "flame_lt", (x, 2.3, z), (x, 2.75, z), (0.15, 0.15), (0.02, 0.02), sides=6)


def make():
    head()
    torso()
    leg(1, "L")
    leg(-1, "R")
    shoulder_and_sleeve(1, "L", EL_L, WR_L)
    shoulder_and_sleeve(-1, "R", EL_R, WR_R)
    free_hand()
    staff()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side, el, wr in ((1, "L", EL_L, WR_L), (-1, "R", EL_R, WR_R)):
        out[f"arm.{side}"] = ((s * SH[0], SH[1], SH[2]), (s * el[0], el[1], el[2]))
        out[f"forearm.{side}"] = ((s * el[0], el[1], el[2]), (s * wr[0], wr[1], wr[2]))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("u009", "biped", PALETTE, make, joints())
