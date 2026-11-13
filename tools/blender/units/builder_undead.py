"""Undead Acolyte Builder (builder_undead): medido em artifacts/model-sheets/refs/builder_undead/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/builder_undead.py -- <out.glb>

Corcunda: tronco e capuz projetados à frente. Pé-de-cabra com gancho na mão direita, caixa de madeira no quadril esquerdo.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "cream": 0xD8CCAA, "cream_dk": 0xB8AB88, "patch": 0xC9BB96, "strap": 0x5E3F2A, "wood": 0x6B4A30, "wood_dk": 0x4E3422,
    "wrap": 0x5A4C36, "boot": 0x4A4440, "sole": 0x1F1D1F, "steel": 0x6E6E74, "skin": 0xD6C4A8, "mask": 0x5A3A2A,
    "green": 0x2FA060, "void": 0x2A1D16,
}

HIP, KNEE, ANKLE, LEG_X = 1.05, 0.52, 0.2, 0.3
WAIST, NECK, TOP = 1.4, 2.05, 2.62
SH_X, SH_Y, EL_Y, WR_Y = 0.46, 2.02, 1.45, 0.98
EL_XL, EL_XR = 0.54, -0.52
SKIRT_MID = 0.95


def hem(p):
    """A barra da túnica acompanha a coxa do seu lado; o topo fica na pelve."""
    if p[1] > SKIRT_MID:
        return {"pelvis": 1.0}
    return {"pelvis": 0.4, "thigh.L" if p[0] > 0 else "thigh.R": 0.6}


def head():
    H.frustum("head", "cream", (0, 2.0, 0.14), (0, 2.28, 0.26), (0.3, 0.3), (0.3, 0.3), sides=8)         # capuz projetado
    H.frustum("head", "cream", (0, 2.28, 0.26), (0, 2.5, 0.2), (0.3, 0.3), (0.2, 0.22), sides=8)
    H.chain("head", "cream", [(0, 2.45, 0.22), (0, 2.56, 0.38), (0, 2.5, 0.56)], [(0.15, 0.15), (0.07, 0.07), (0.01, 0.01)])  # bico à frente
    H.frustum("head", "cream_dk", (0, 2.4, 0.2), (0, 2.6, 0.0), (0.2, 0.2), (0.05, 0.08), sides=6)        # cauda do capuz atrás
    H.frustum("head", "void", (0, 2.12, 0.36), (0, 2.46, 0.38), (0.19, 0.08), (0.2, 0.08), sides=6)       # rosto na sombra
    H.frustum("head", "mask", (0, 2.1, 0.4), (0, 2.32, 0.42), (0.17, 0.1), (0.19, 0.1), sides=6)         # máscara marrom


def torso():
    H.frustum("spine", "cream", (0, WAIST - 0.05, 0), (0, 1.78, 0.06), (0.4, 0.3), (0.46, 0.34), sides=8)
    H.frustum("spine", "cream", (0, 1.78, 0.06), (0, 2.1, 0.16), (0.46, 0.34), (0.34, 0.3), sides=8)
    H.frustum("spine", "cream_dk", (0, 2.0, 0.1), (0, 2.2, 0.16), (0.52, 0.38), (0.34, 0.3), sides=8)    # gola de ombros
    H.frustum("spine", "strap", (-0.3, 2.14, 0.3), (0.34, 1.3, 0.34), (0.045, 0.03), (0.045, 0.03), sides=4)
    H.frustum("spine", "strap", (-0.3, 2.14, -0.2), (0.34, 1.3, -0.3), (0.045, 0.03), (0.045, 0.03), sides=4)
    H.frustum("pelvis", "strap", (0, WAIST - 0.08, 0), (0, WAIST + 0.06, 0), (0.42, 0.34), (0.42, 0.34), sides=8)


def skirt():
    s = H.frustum("pelvis", "cream", (0, 0.55, 0), (0, WAIST - 0.05, 0), (0.42, 0.36), (0.36, 0.3), sides=8)
    H.soft(s, hem)
    p = H.frustum("pelvis", "patch", (-0.2, 0.7, 0.35), (-0.2, 1.0, 0.33), (0.1, 0.03), (0.1, 0.03), sides=4)
    H.soft(p, hem)
    # caixa de madeira com tampa e selo verde, no quadril esquerdo
    H.frustum("pelvis", "wood", (0.5, 1.0, -0.15), (0.5, 1.42, -0.15), (0.2, 0.25), (0.22, 0.27), sides=4)
    H.frustum("pelvis", "wood_dk", (0.5, 1.4, -0.15), (0.5, 1.46, -0.15), (0.24, 0.29), (0.24, 0.29), sides=4)
    H.box("pelvis", "green", (0.73, 1.2, -0.05), (0.03, 0.12, 0.12))


def legs(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "skin", (x, KNEE - 0.04, 0), (x, HIP + 0.04, 0), (0.17, 0.19), (0.2, 0.22), sides=6)
    H.frustum(f"shin.{side}", "wrap", (x, ANKLE - 0.02, 0), (x, KNEE + 0.03, 0), (0.17, 0.17), (0.2, 0.2), sides=6)
    H.frustum(f"shin.{side}", "boot", (x, ANKLE - 0.06, 0), (x, ANKLE + 0.14, 0), (0.2, 0.2), (0.24, 0.23), sides=6)     # cano da bota
    H.frustum(f"foot.{side}", "boot", (x, 0.12, 0.06), (x, 0.09, 0.46), (0.22, 0.14), (0.19, 0.08), sides=4)
    H.frustum(f"foot.{side}", "boot", (x, 0.04, -0.04), (x, ANKLE + 0.04, -0.04), (0.21, 0.23), (0.21, 0.22), sides=6)
    H.frustum(f"foot.{side}", "sole", (x, 0.02, -0.22), (x, 0.02, 0.48), (0.23, 0.022), (0.2, 0.022), sides=4)


def arm(s, side, ex):
    sx = s * SH_X
    H.frustum(f"arm.{side}", "cream", (sx, SH_Y + 0.04, 0.1), (ex, EL_Y - 0.02, 0.12), (0.2, 0.22), (0.17, 0.18), sides=6)
    H.frustum(f"forearm.{side}", "cream", (ex, EL_Y + 0.02, 0.12), (ex, WR_Y + 0.1, 0.14), (0.17, 0.18), (0.2, 0.19), sides=6)
    H.frustum(f"forearm.{side}", "skin", (ex, WR_Y + 0.1, 0.14), (ex, WR_Y - 0.26, 0.16), (0.14, 0.15), (0.13, 0.14), sides=6)


def crowbar():
    """Pé-de-cabra na mão direita: cabo inclinado de fora para baixo, ponta curva em gancho para fora e para a frente."""
    pts = [(-0.34, 1.5, 0.1), (-0.46, 1.2, 0.14), (-0.6, 0.85, 0.18), (-0.76, 0.5, 0.22), (-0.9, 0.28, 0.26),
           (-1.0, 0.2, 0.3), (-1.04, 0.3, 0.34)]
    radii = [(0.075, 0.075)] * 5 + [(0.06, 0.06), (0.015, 0.015)]
    H.chain("forearm.R", "steel", pts, radii, sides=4)
    H.frustum("forearm.R", "steel", (-0.3, 1.52, 0.1), (-0.4, 1.34, 0.1), (0.09, 0.05), (0.06, 0.05), sides=4)


def make():
    head()
    torso()
    skirt()
    for s, side in ((1, "L"), (-1, "R")):
        legs(s, side)
    arm(1, "L", EL_XL)
    arm(-1, "R", EL_XR)
    crowbar()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0.1)),
           "head": ((0, NECK, 0.1), (0, TOP, 0.1))}
    for s, side, ex in ((1, "L", EL_XL), (-1, "R", EL_XR)):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0.1), (ex, EL_Y, 0.1))
        out[f"forearm.{side}"] = ((ex, EL_Y, 0.1), (ex, WR_Y, 0.1))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("builder_undead", "biped", PALETTE, make, joints())
