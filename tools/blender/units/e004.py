"""Amazon (e004): medido em artifacts/model-sheets/refs/e004/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/e004.py -- <out.glb>

Arco longo (1,9 m) na mao ESQUERDA, osso forearm.L, deitado ao longo de z como no perfil e na vista de cima.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "armor": 0x666A70, "armor_lt": 0x8B8F96, "armor_dk": 0x4E5058, "skin": 0x8A74C4, "cloak": 0x8E9094, "hood": 0x15131C,
    "brown": 0x8E4A30, "belt": 0x4F2F22, "hair": 0x2F4FA8, "bow": 0x3A3D44, "string": 0xE6E2EE, "bronze": 0xC08A40,
    "quiver": 0x6B4230, "arrow": 0xF2F2F6, "eye": 0xFF3030, "boot": 0x555961, "mask": 0x34363C, "glove": 0x4A4A66,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X = 1.05, 0.62, 0.17, 0.24, 0.27
WAIST, NECK, TOP = 1.5, 2.12, 2.7
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.5, 2.1, 0.55, 1.5, 1.12


def head():
    H.frustum("head", "skin", (0, 2.2, 0.03), (0, 2.55, 0.03), (0.14, 0.15), (0.15, 0.16), sides=6)
    H.frustum("head", "hood", (0, 2.16, -0.07), (0, 2.6, -0.07), (0.2, 0.2), (0.21, 0.21), sides=8)         # capuz
    H.frustum("head", "hood", (0, 2.6, -0.07), (0, 2.72, -0.08), (0.21, 0.21), (0.1, 0.11), sides=8)
    H.frustum("head", "mask", (0, 2.2, 0.05), (0, 2.38, 0.05), (0.15, 0.16), (0.15, 0.16), sides=6)
    H.chain("head", "arrow", [(-0.05, 2.62, -0.1), (-0.12, 2.85, -0.12), (-0.3, 2.95, -0.1), (-0.5, 2.92, -0.08)],
            [(0.05, 0.03), (0.07, 0.03), (0.06, 0.03), (0.01, 0.01)], sides=4)
    H.frustum("head", "bronze", (0, 2.58, 0.12), (0, 2.62, 0.12), (0.16, 0.05), (0.14, 0.05), sides=4)
    H.frustum("head", "hair", (0, 2.5, 0.17), (0, 2.58, 0.15), (0.1, 0.03), (0.08, 0.03), sides=4)           # franja
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.07, 2.46, 0.2), (0.07, 0.035, 0.03))
        H.chain("head", "skin", [(s * 0.14, 2.45, 0.0), (s * 0.3, 2.55, -0.02), (s * 0.46, 2.64, -0.04)],
                [(0.07, 0.03), (0.05, 0.02), (0.008, 0.008)], sides=4)
    H.chain("head", "hair", [(0, 2.55, -0.2), (0, 2.5, -0.4), (0, 2.2, -0.52), (0, 1.85, -0.46), (0, 1.55, -0.4)],
            [(0.07, 0.07), (0.08, 0.08), (0.075, 0.075), (0.05, 0.05), (0.015, 0.015)], sides=6)


def torso():
    H.frustum("spine", "armor", (0, WAIST - 0.04, 0.02), (0, 2.0, 0.02), (0.34, 0.22), (0.41, 0.24), sides=8)
    H.frustum("spine", "armor", (0, 2.0, 0.02), (0, 2.2, 0.02), (0.41, 0.24), (0.24, 0.19), sides=8)
    H.frustum("spine", "armor_dk", (0, 2.1, 0.0), (0, 2.34, 0.0), (0.3, 0.26), (0.2, 0.2), sides=8)             # gola
    H.frustum("pelvis", "belt", (0, WAIST - 0.12, 0), (0, WAIST + 0.04, 0), (0.37, 0.28), (0.37, 0.28), sides=8)
    H.frustum("pelvis", "brown", (0, 0.92, 0), (0, WAIST - 0.1, 0), (0.37, 0.27), (0.34, 0.26), sides=8)
    H.frustum("pelvis", "belt", (0, WAIST - 0.16, 0.14), (0.04, 1.2, 0.22), (0.3, 0.06), (0.1, 0.06), sides=4)
    for s in (-1, 1):       # ombreiras em cunha, duas camadas
        H.frustum("spine", "armor_lt", (s * 0.28, 2.3, 0), (s * 0.6, 2.1, 0), (0.17, 0.26), (0.21, 0.28), sides=6)
        H.frustum("spine", "armor_lt", (s * 0.46, 2.3, 0), (s * 0.5, 2.55, -0.04), (0.06, 0.06), (0.01, 0.01), sides=4)
        H.frustum("spine", "armor", (s * 0.3, 2.2, 0), (s * 0.58, 1.98, 0), (0.19, 0.27), (0.22, 0.29), sides=6)


def hem(p):
    return {"pelvis": 1.0} if p[1] > 1.1 else {"pelvis": 0.4, "thigh.L" if p[0] > 0 else "thigh.R": 0.6}


def cloak():
    H.frustum("spine", "cloak", (0, WAIST, -0.27), (0, 2.28, -0.24), (0.5, 0.05), (0.4, 0.05), sides=4)
    low = H.frustum("pelvis", "cloak", (0, 0.62, -0.32), (0, WAIST, -0.27), (0.66, 0.05), (0.5, 0.05), sides=4)
    H.soft(low, hem)
    for x, d in ((-0.5, 0.2), (-0.25, 0.32), (0.0, 0.14), (0.28, 0.3), (0.5, 0.18)):      # barra rasgada
        H.soft(H.frustum("pelvis", "cloak", (x, 0.62, -0.32), (x, 0.62 - d, -0.32), (0.13, 0.05), (0.02, 0.04), sides=4), hem)
    H.frustum("spine", "quiver", (0.18, 1.55, -0.34), (-0.3, 2.28, -0.34), (0.1, 0.09), (0.12, 0.1), sides=4)
    for i, x in enumerate((-0.28, -0.4, -0.5)):
        H.frustum("spine", "arrow", (x, 2.25, -0.34), (x - 0.05, 2.6 + 0.04 * i, -0.34), (0.02, 0.02), (0.09, 0.07), sides=6)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * KNEE_X
        H.frustum(f"thigh.{side}", "brown", (x, KNEE - 0.05, 0), (s * LEG_X, HIP + 0.05, 0), (0.19, 0.2), (0.26, 0.27), sides=6)
        H.frustum(f"shin.{side}", "armor_lt", (x, KNEE - 0.1, 0.08), (x, KNEE + 0.14, 0.08), (0.15, 0.13), (0.15, 0.12), sides=6)
        H.frustum(f"shin.{side}", "armor", (x, ANKLE, 0), (x, KNEE - 0.08, 0), (0.17, 0.18), (0.21, 0.2), sides=6)
        H.frustum(f"foot.{side}", "boot", (x, 0.03, -0.02), (x, ANKLE + 0.04, -0.02), (0.19, 0.22), (0.17, 0.19), sides=6)
        H.frustum(f"foot.{side}", "boot", (x, 0.11, 0.06), (x, 0.08, 0.42), (0.19, 0.1), (0.16, 0.06), sides=4)


def arms():
    for s, side in ((1, "L"), (-1, "R")):
        z = 0.04 if s > 0 else 0.0
        H.frustum(f"arm.{side}", "armor_dk", (s * (SH_X + 0.02), SH_Y + 0.02, 0), (s * EL_X, EL_Y - 0.02, 0), (0.15, 0.17), (0.13, 0.14), sides=6)
        H.frustum(f"forearm.{side}", "armor", (s * EL_X, EL_Y + 0.03, 0), (s * EL_X, WR_Y + 0.02, z), (0.14, 0.15), (0.16, 0.17), sides=6)
        H.frustum(f"forearm.{side}", "armor_lt", (s * (EL_X + 0.1), EL_Y - 0.04, z), (s * (EL_X + 0.13), WR_Y + 0.05, z), (0.04, 0.12), (0.04, 0.14), sides=4)
        H.frustum(f"forearm.{side}", "glove", (s * EL_X, WR_Y + 0.03, z), (s * EL_X, WR_Y - 0.2, z + 0.04), (0.14, 0.15), (0.11, 0.12), sides=6)


def bow():
    x = EL_X
    pts = [(x, 1.5, 0.95), (x, 1.34, 0.6), (x, 1.2, 0.25), (x, 1.12, 0.04), (x, 1.15, -0.25), (x + 0.04, 1.26, -0.62), (x + 0.08, 1.38, -1.0)]
    rad = [(0.04, 0.04), (0.05, 0.05), (0.055, 0.055), (0.06, 0.06), (0.055, 0.055), (0.05, 0.05), (0.04, 0.04)]
    H.chain("forearm.L", "bow", pts, rad, sides=6)
    H.frustum("forearm.L", "bronze", (x, 1.12, 0.12), (x, 1.12, -0.05), (0.07, 0.07), (0.07, 0.07), sides=6)      # empunhadura
    H.frustum("forearm.L", "string", (x, 1.5, 0.95), (x + 0.08, 1.38, -1.0), (0.012, 0.012), (0.012, 0.012), sides=4)


def make():
    head()
    torso()
    cloak()
    legs()
    arms()
    bow()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)), "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * KNEE_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * KNEE_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * KNEE_X, ANKLE, 0), (s * KNEE_X, 0.06, 0.5))
    return out


H.build("e004", "biped", PALETTE, make, joints())
