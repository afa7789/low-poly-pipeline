"""Grunt (o002): orc brutamontes de capuz, máscara e presas, machado na mão direita;
medido em artifacts/model-sheets/refs/o002/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/o002.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "skin": 0x4B5E48, "skin_dk": 0x3F503E, "hood": 0x25201F, "kilt": 0x5E2A22, "belt": 0x2B2625, "buckle": 0x74737C,
    "mask": 0x8C3D2F, "tusk": 0xE0D4AA, "wood": 0x4A3326, "axe": 0x7A727A, "boot": 0x2B2625, "pack": 0x8C4832,
    "rag": 0x75645F, "eye": 0xFF4A1E, "glow": 0xFF7A2A, "lamp": 0x3C2E22, "horn": 0xC9B88C,
}

HIP, KNEE, ANKLE, LEG_X = 0.98, 0.52, 0.14, 0.33
WAIST, NECK, TOP = 1.3, 2.0, 2.78
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.78, 2.0, 1.02, 1.42, 0.85
SKIRT_MID = 0.85


def hem(p):
    """A saia acompanha a coxa do seu lado; o topo fica na pelve."""
    if p[1] > SKIRT_MID:
        return {"pelvis": 1.0}
    return {"pelvis": 0.45, "thigh.L" if p[0] > 0 else "thigh.R": 0.55}


def head():
    H.frustum("head", "hood", (0, 2.1, 0.12), (0, 2.45, 0.26), (0.3, 0.3), (0.3, 0.3), sides=8)
    H.frustum("head", "hood", (0, 2.45, 0.26), (0, 2.78, 0.2), (0.3, 0.3), (0.05, 0.09), sides=8)
    H.frustum("head", "skin", (0, 2.3, 0.3), (0, 2.42, 0.4), (0.16, 0.12), (0.15, 0.1), sides=6)        # rosto no capuz
    H.frustum("head", "mask", (0, 2.3, 0.36), (0, 2.12, 0.58), (0.17, 0.17), (0.11, 0.1), sides=6)       # máscara de focinho
    H.frustum("head", "belt", (0, 2.17, 0.45), (0, 2.14, 0.56), (0.07, 0.04), (0.05, 0.03), sides=4)
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.09, 2.4, 0.46), (0.08, 0.035, 0.03))
        H.chain("head", "tusk", [(s * 0.14, 2.14, 0.5), (s * 0.28, 2.18, 0.72), (s * 0.3, 2.42, 0.78)],
                [(0.07, 0.07), (0.05, 0.05), (0.012, 0.012)], sides=4)


def torso():
    H.frustum("spine", "skin", (0, WAIST - 0.05, 0), (0, 1.85, 0.02), (0.5, 0.52), (0.78, 0.58), sides=8)        # tronco em V
    H.frustum("spine", "skin_dk", (0, 1.85, 0.02), (0, 2.2, 0.06), (0.78, 0.58), (0.45, 0.4), sides=8)          # trapézios
    H.frustum("spine", "hood", (0, 1.9, 0.1), (0, 2.22, 0.1), (0.52, 0.5), (0.4, 0.4), sides=8)                  # gola do capuz
    H.frustum("spine", "hood", (0, 1.78, 0.34), (0, 2.0, 0.28), (0.12, 0.05), (0.38, 0.1), sides=4)
    H.box("spine", "pack", (0, 1.78, -0.66), (0.5, 0.6, 0.42))
    for s in (-1, 1):
        H.box("spine", "rag", (s * 0.18, 1.4, -0.75), (0.1, 0.45, 0.03))
    H.frustum("pelvis", "skin", (0, 0.9, 0), (0, WAIST, 0), (0.46, 0.5), (0.5, 0.52), sides=8)
    H.frustum("pelvis", "belt", (0, WAIST - 0.02, 0), (0, WAIST + 0.12, 0), (0.54, 0.55), (0.54, 0.55), sides=8)
    H.box("pelvis", "buckle", (0, WAIST + 0.05, 0.54), (0.22, 0.14, 0.05))
    kilt = H.frustum("pelvis", "kilt", (0, 0.55, 0), (0, WAIST - 0.02, 0), (0.54, 0.57), (0.5, 0.53), sides=8)
    H.soft(kilt, hem)
    # corno de guerra no quadril esquerdo, lanterna no direito
    H.chain("pelvis", "horn", [(0.5, 1.2, 0.08), (0.54, 0.98, 0.14), (0.48, 0.88, 0.3)], [(0.1, 0.1), (0.07, 0.07), (0.03, 0.03)], sides=6)
    H.box("pelvis", "lamp", (-0.52, 1.0, 0.3), (0.14, 0.2, 0.14))
    H.box("pelvis", "glow", (-0.52, 1.0, 0.38), (0.07, 0.1, 0.03))


def leg(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "skin", (x, KNEE - 0.04, 0), (x, HIP + 0.06, 0), (0.26, 0.27), (0.31, 0.32), sides=6)
    H.frustum(f"shin.{side}", "skin_dk", (x, KNEE - 0.1, 0), (x, KNEE + 0.04, 0), (0.28, 0.28), (0.27, 0.27), sides=6)
    H.frustum(f"shin.{side}", "boot", (x, ANKLE - 0.02, 0), (x, KNEE - 0.1, 0), (0.28, 0.28), (0.32, 0.33), sides=6)
    H.frustum(f"shin.{side}", "belt", (x, KNEE - 0.2, 0), (x, KNEE - 0.1, 0), (0.33, 0.34), (0.33, 0.34), sides=6)
    H.frustum(f"foot.{side}", "skin", (x, 0.12, -0.04), (x, 0.09, 0.44), (0.3, 0.2), (0.27, 0.1), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.03, -0.18), (x, 0.03, 0.42), (0.3, 0.04), (0.27, 0.04), sides=4)


def arm(s, side):
    H.frustum(f"arm.{side}", "skin", (s * 0.64, 2.1, 0.0), (s * 0.98, 1.78, 0.02), (0.33, 0.33), (0.42, 0.4), sides=6)
    H.frustum(f"arm.{side}", "skin_dk", (s * 0.98, 1.78, 0.02), (s * EL_X, EL_Y - 0.02, 0.05), (0.42, 0.4), (0.34, 0.34), sides=6)
    H.frustum(f"forearm.{side}", "skin", (s * EL_X, EL_Y + 0.04, 0.05), (s * 0.95, 1.05, 0.08), (0.33, 0.33), (0.36, 0.36), sides=6)
    H.frustum(f"forearm.{side}", "skin_dk", (s * 0.95, 1.08, 0.08), (s * 0.9, 0.78, 0.1), (0.36, 0.36), (0.26, 0.27), sides=6)
    H.frustum(f"forearm.{side}", "skin", (s * 0.9, 0.82, 0.1), (s * 0.88, 0.58, 0.12), (0.26, 0.27), (0.31, 0.31), sides=6)   # punho grande
    H.frustum(f"forearm.{side}", "skin", (s * 0.88, 0.6, 0.12), (s * 0.87, 0.4, 0.12), (0.31, 0.31), (0.22, 0.2), sides=6)


def axe():
    pom, end = (-1.4, 0.98, 0.7), (-0.52, 0.4, -0.75)
    H.chain("forearm.R", "wood", [pom, end], [(0.06, 0.06), (0.055, 0.055)], sides=6)
    H.frustum("forearm.R", "axe", (-0.5, 0.42, -0.55), (-0.5, 0.42, -0.98), (0.07, 0.16), (0.12, 0.42), sides=4)
    H.frustum("forearm.R", "axe", (-0.5, 0.4, -0.5), (-0.5, 0.4, -0.58), (0.1, 0.1), (0.1, 0.1), sides=6)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        arm(s, side)
    axe()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0.04))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0.04), (s * 0.9, 0.6, 0.12))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("o002", "biped", PALETTE, make, joints())
