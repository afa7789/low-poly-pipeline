"""Lesser Vampire (h01V): medido em artifacts/model-sheets/refs/h01V/sheet.jpg (escala 0.0052 m/px, uns 2,4 m).

A prancha desenha corpo baixo, casaco de trincheira marrom, asinhas dobradas nas costas e um punhal na mão direita.
Não reaproveita o corpo do h01U: as duas pranchas são figuras diferentes.

    blender -b --factory-startup -P tools/blender/units/h01V.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "coat": 0x6B4A38, "coat_dk": 0x4A3226, "skin": 0xD6CBB6, "skin_dk": 0xB5A890, "eye": 0x2FC27A, "black": 0x1E1816,
    "boot": 0x4A3428, "sole": 0x20160F, "wing": 0x5E4838, "wing_dk": 0x3F2F25, "blade": 0x9AA0A8, "hilt": 0x3A2A22,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X = 0.86, 0.5, 0.13, 0.19, 0.21
WAIST, NECK, TOP = 1.15, 1.8, 2.42
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.4, 1.76, 0.46, 1.34, 1.02
HEM, SKIRT_TOP = 0.58, 1.12
SKIRT_MID = (HEM + SKIRT_TOP) / 2


def hem(p):
    """A barra do casaco acompanha a coxa do seu lado; o topo fica na pelve."""
    if p[1] > SKIRT_MID:
        return {"pelvis": 1.0}
    return {"pelvis": 0.45, "thigh.L" if p[0] > 0 else "thigh.R": 0.55}


def head():
    H.frustum("head", "skin", (0, 1.9, 0.02), (0, 2.1, 0.02), (0.15, 0.15), (0.21, 0.21), sides=8)
    H.frustum("head", "skin", (0, 2.1, 0.02), (0, 2.3, 0.02), (0.21, 0.21), (0.19, 0.19), sides=8)
    H.frustum("head", "skin", (0, 2.3, 0.02), (0, 2.42, 0.02), (0.19, 0.19), (0.1, 0.1), sides=8)
    H.frustum("head", "coat_dk", (0, 2.24, 0.02), (0, 2.31, 0.02), (0.215, 0.215), (0.2, 0.2), sides=8)      # tira dos óculos
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.09, 2.14, 0.215), (0.07, 0.07, 0.03))
        H.box("head", "eye", (s * 0.08, 2.35, 0.2), (0.09, 0.07, 0.05))                # lentes na testa
        H.frustum("head", "skin", (s * 0.19, 2.08, 0.0), (s * 0.34, 2.16, 0.0), (0.04, 0.07), (0.008, 0.012), sides=4)   # orelha em ponta
    H.box("head", "boot", (0, 2.35, 0.19), (0.11, 0.07, 0.04))
    H.frustum("head", "black", (0, 1.76, 0.1), (0, 1.98, 0.1), (0.14, 0.1), (0.15, 0.1), sides=6)           # camisa
    H.frustum("head", "coat", (0, 1.76, -0.02), (0, 1.98, -0.02), (0.3, 0.22), (0.35, 0.27), sides=8)        # gola do casaco
    H.frustum("head", "coat_dk", (0, 1.9, 0.0), (0, 1.99, 0.0), (0.2, 0.2), (0.24, 0.23), sides=8)


def torso():
    H.frustum("spine", "coat", (0, WAIST - 0.05, 0), (0, SH_Y, 0), (0.34, 0.26), (0.42, 0.28), sides=8)
    H.frustum("spine", "coat", (0, SH_Y, 0), (0, 1.9, 0), (0.42, 0.28), (0.26, 0.2), sides=8)
    H.frustum("spine", "coat_dk", (0, 1.15, 0.265), (0, 1.74, 0.275), (0.012, 0.01), (0.012, 0.01), sides=4)   # fecho
    skirt = H.frustum("pelvis", "coat", (0, HEM, 0), (0, SKIRT_TOP, 0), (0.4, 0.3), (0.33, 0.26), sides=8)
    H.soft(skirt, hem)
    H.frustum("pelvis", "coat_dk", (0, WAIST - 0.1, 0), (0, WAIST + 0.04, 0), (0.37, 0.28), (0.37, 0.28), sides=8)    # cinto


def leg(s, side):
    kx = s * KNEE_X
    H.frustum(f"thigh.{side}", "skin", (kx, KNEE, 0), (s * LEG_X, HIP + 0.04, 0), (0.1, 0.11), (0.13, 0.13), sides=6)
    H.frustum(f"shin.{side}", "skin_dk", (kx, 0.3, 0), (kx, KNEE + 0.03, 0), (0.1, 0.1), (0.1, 0.1), sides=6)
    H.frustum(f"shin.{side}", "boot", (kx, ANKLE - 0.02, 0), (kx, 0.26, 0), (0.12, 0.13), (0.14, 0.14), sides=6)
    H.frustum(f"shin.{side}", "boot", (kx, 0.26, 0), (kx, 0.37, 0), (0.14, 0.14), (0.17, 0.17), sides=6)      # cano abre no topo
    H.frustum(f"foot.{side}", "boot", (kx, 0.03, -0.02), (kx, ANKLE + 0.04, -0.02), (0.14, 0.15), (0.13, 0.14), sides=6)
    H.frustum(f"foot.{side}", "boot", (kx, 0.1, 0.05), (kx, 0.08, 0.36), (0.14, 0.1), (0.12, 0.06), sides=4)
    H.frustum(f"foot.{side}", "sole", (kx, 0.02, -0.15), (kx, 0.02, 0.38), (0.15, 0.02), (0.13, 0.02), sides=4)


def arm(s, side):
    H.frustum(f"arm.{side}", "coat", (s * SH_X, SH_Y + 0.05, 0), (s * EL_X, EL_Y - 0.02, 0), (0.18, 0.18), (0.15, 0.15), sides=6)
    H.frustum(f"forearm.{side}", "coat", (s * EL_X, EL_Y + 0.04, 0), (s * 0.48, 1.12, 0), (0.15, 0.15), (0.14, 0.14), sides=6)
    H.frustum(f"forearm.{side}", "coat_dk", (s * 0.48, 1.17, 0), (s * 0.48, 1.05, 0), (0.17, 0.17), (0.18, 0.18), sides=6)    # punho dobrado
    H.frustum(f"forearm.{side}", "skin", (s * 0.48, 1.08, 0), (s * 0.48, 0.88, 0.02), (0.13, 0.13), (0.1, 0.1), sides=6)


def dagger():
    """Punhal em pegada invertida na mão direita (forearm.R): lâmina para baixo e um pouco à frente, bem fora do corpo."""
    H.frustum("forearm.R", "hilt", (-0.48, 1.04, 0.0), (-0.48, 0.9, 0.03), (0.06, 0.06), (0.05, 0.05), sides=4)
    H.box("forearm.R", "boot", (-0.48, 0.9, 0.04), (0.2, 0.05, 0.08))
    H.frustum("forearm.R", "blade", (-0.48, 0.88, 0.05), (-0.48, 0.46, 0.3), (0.085, 0.04), (0.012, 0.012), sides=4)


def wings():
    """Asinhas dobradas nas costas (spine): placa marrom em cada lado e duas nervuras escuras."""
    for s in (1, -1):
        def pt(x, y):
            return (s * x, y, -0.2 - (2.1 - y) * 0.11)
        outline = [(0.04, 1.95), (0.2, 2.12), (0.38, 2.2), (0.52, 1.65), (0.42, 1.2), (0.2, 0.78), (0.04, 0.82)]
        H.panel("spine", "wing", [pt(x, y) for x, y in outline], thickness=0.13)
        for (x0, y0), (x1, y1) in (((0.2, 2.0), (0.2, 0.86)), ((0.36, 2.08), (0.3, 1.0))):
            a, b = pt(x0, y0), pt(x1, y1)
            H.frustum("spine", "wing_dk", (a[0], a[1], a[2] - 0.07), (b[0], b[1], b[2] - 0.07), (0.035, 0.03), (0.02, 0.02), sides=4)


def make():
    head()
    torso()
    leg(1, "L")
    leg(-1, "R")
    arm(1, "L")
    arm(-1, "R")
    dagger()
    wings()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * KNEE_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * KNEE_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * KNEE_X, ANKLE, 0), (s * KNEE_X, 0.06, 0.45))
    return out


H.build("h01V", "biped", PALETTE, make, joints())
