"""Chaos Champion (n00Z, irmão maior do n009): medido em artifacts/model-sheets/refs/n009/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n009.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "armor": 0x2B2A2D, "armor_dk": 0x1F1D1F, "armor_lt": 0x3A383C, "skin": 0xD84A26, "skin_dk": 0xBC3C1E,
    "gold": 0xC9A55A, "horn": 0x5C4A3C, "visor": 0xC81414, "belt": 0x4A3A2E, "boot": 0x4A3528,
    "boot_mud": 0x33261D, "steel": 0x8A8A92, "wood": 0x5E4A3A, "badge": 0x9A9AA0, "red": 0x8E2A24, "eye": 0x30FF40,
}

# juntas (metros do biped), medidas na vista de frente/lado da prancha (cabeça e tronco projetados à frente)
HIP, KNEE, ANKLE, LEG_X = 1.15, 0.66, 0.2, 0.31
WAIST, NECK, TOP = 1.38, 2.0, 2.7
SH_X, SH_Y, EL_Y, WR_Y = 0.66, 2.0, 1.47, 0.85
HAND_X = 0.7


def chain(bone, tone, pts, radii, sides=4):
    """Segmentos afunilados ligando pts[i] a pts[i+1]: uma curva feita de cunhas curtas."""
    for i in range(len(pts) - 1):
        H.frustum(bone, tone, pts[i], pts[i + 1], radii[i], radii[i + 1], sides=sides)


def head():
    H.frustum("head", "armor_dk", (0, 1.7, 0.1), (0, 2.3, 0.16), (0.27, 0.25), (0.25, 0.22), sides=8)    # nuca
    H.frustum("head", "armor", (0, 1.66, 0.45), (0, 2.2, 0.4), (0.28, 0.27), (0.31, 0.29), sides=8)       # rosto do elmo
    H.frustum("head", "armor", (0, 2.2, 0.4), (0, 2.5, 0.3), (0.31, 0.29), (0.04, 0.07), sides=8)         # cone
    H.box("head", "visor", (0, 2.0, 0.7), (0.3, 0.1, 0.04))
    H.box("head", "red", (0, 1.82, 0.7), (0.18, 0.12, 0.04))
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.1, 2.0, 0.74), (0.07, 0.05, 0.03))
        chain("head", "horn", [(s * 0.17, 2.0, 0.3), (s * 0.33, 2.3, 0.3), (s * 0.3, 2.6, 0.3), (s * 0.15, 2.88, 0.3)],
              [(0.1, 0.1), (0.09, 0.09), (0.06, 0.06), (0.01, 0.01)])


def torso():
    H.frustum("spine", "skin", (0, 1.28, 0.0), (0, 1.5, 0.0), (0.36, 0.27), (0.43, 0.3), sides=8)
    H.frustum("spine", "skin", (0, 1.5, 0.05), (0, 1.82, 0.12), (0.43, 0.3), (0.56, 0.35), sides=8)
    H.frustum("spine", "skin", (0, 1.82, 0.12), (0, 2.12, 0.2), (0.56, 0.35), (0.5, 0.3), sides=8)
    for s in (-1, 1):
        H.frustum("spine", "skin_dk", (s * 0.2, 1.66, 0.3), (s * 0.2, 1.92, 0.33), (0.17, 0.06), (0.2, 0.06), sides=6)
    H.frustum("spine", "badge", (0.22, 1.84, 0.37), (0.22, 1.98, 0.37), (0.07, 0.025), (0.075, 0.025), sides=4)
    H.frustum("spine", "armor", (0, 1.3, -0.2), (0, 2.26, -0.24), (0.34, 0.17), (0.46, 0.19), sides=6)     # placa das costas
    H.frustum("spine", "gold", (0, 1.28, -0.2), (0, 1.35, -0.2), (0.36, 0.18), (0.36, 0.18), sides=6)
    H.frustum("spine", "gold", (0, 2.2, -0.24), (0, 2.27, -0.24), (0.48, 0.2), (0.48, 0.2), sides=6)


def pelvis():
    H.frustum("pelvis", "belt", (0, 1.2, 0), (0, WAIST, 0), (0.39, 0.31), (0.38, 0.3), sides=8)
    H.frustum("pelvis", "skin", (0, 0.95, 0), (0, 1.22, 0), (0.43, 0.3), (0.39, 0.28), sides=8)
    H.frustum("pelvis", "armor", (0, 0.88, 0.3), (0, 1.26, 0.3), (0.1, 0.05), (0.19, 0.05), sides=4)
    H.frustum("pelvis", "armor", (0, 0.95, -0.26), (0, 1.3, -0.25), (0.3, 0.08), (0.4, 0.08), sides=4)
    for s in (-1, 1):
        H.frustum("pelvis", "armor", (s * 0.43, 0.96, 0.0), (s * 0.43, 1.28, 0.0), (0.08, 0.15), (0.095, 0.15), sides=4)


def legs(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "skin", (x, KNEE - 0.04, 0), (x, HIP + 0.06, 0), (0.2, 0.23), (0.25, 0.26), sides=6)
    H.frustum(f"shin.{side}", "boot_mud", (x, ANKLE - 0.02, 0.02), (x, 0.4, 0.03), (0.25, 0.22), (0.22, 0.2), sides=6)
    H.frustum(f"shin.{side}", "boot", (x, 0.4, 0.03), (x, 0.55, 0.03), (0.22, 0.2), (0.21, 0.2), sides=6)
    H.frustum(f"shin.{side}", "armor_dk", (x, 0.55, 0.03), (x, KNEE + 0.08, 0.03), (0.21, 0.2), (0.225, 0.21), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.09, 0.0), (x, 0.08, 0.44), (0.24, 0.18), (0.2, 0.08), sides=4)
    H.frustum(f"foot.{side}", "armor_dk", (x, 0.02, -0.2), (x, 0.02, 0.45), (0.25, 0.02), (0.21, 0.02), sides=4)


def arms(s, side):
    x, hx = s * SH_X, s * HAND_X
    H.frustum(f"arm.{side}", "skin", (x, SH_Y + 0.02, 0.0), (x, 1.75, 0.02), (0.18, 0.2), (0.21, 0.22), sides=6)   # deltoide
    H.frustum(f"arm.{side}", "skin", (x, 1.75, 0.02), (hx, EL_Y + 0.02, 0.03), (0.21, 0.22), (0.14, 0.15), sides=6)
    H.frustum(f"forearm.{side}", "armor", (hx, EL_Y - 0.04, 0.0), (hx, 1.0, 0.03), (0.18, 0.19), (0.215, 0.2), sides=6)
    H.frustum(f"forearm.{side}", "armor_lt", (hx, EL_Y - 0.06, 0.0), (hx, EL_Y + 0.02, 0.0), (0.2, 0.21), (0.2, 0.21), sides=6)
    H.frustum(f"forearm.{side}", "armor", (hx, 1.02, 0.04), (hx, 0.8, 0.06), (0.21, 0.2), (0.18, 0.18), sides=4)   # punho
    H.frustum(f"forearm.{side}", "armor_lt", (hx, 0.92, 0.14), (hx, 0.9, 0.3), (0.12, 0.06), (0.1, 0.05), sides=4)  # nós dos dedos
    pauldron(s, side)


def pauldron(s, side):
    bone = f"arm.{side}"
    H.frustum(bone, "armor", (s * 0.34, 2.28, 0.05), (s * 0.76, 1.82, 0.05), (0.24, 0.36), (0.2, 0.34), sides=6)
    H.frustum(bone, "gold", (s * 0.76, 1.82, 0.05), (s * 0.8, 1.77, 0.05), (0.24, 0.37), (0.24, 0.37), sides=6)
    for a, b in (((0.55, 2.15, 0.2), (0.66, 2.4, 0.26)), ((0.7, 2.05, -0.1), (0.88, 2.3, -0.12)),
                 ((0.8, 1.95, 0.05), (0.94, 2.0, 0.05))):
        H.frustum(bone, "horn", (s * a[0], a[1], a[2]), (s * b[0], b[1], b[2]), (0.05, 0.05), (0.01, 0.01), sides=4)


def weapon():
    """Alabarda na mão direita: haste vertical atrás do corpo, lâmina em crescente no alto curvando para trás."""
    chain("forearm.R", "wood", [(-0.78, 0.02, -0.25), (-0.78, 1.0, -0.25), (-0.78, 2.3, -0.25)],
          [(0.06, 0.06), (0.06, 0.06), (0.06, 0.06)])
    H.frustum("forearm.R", "gold", (-0.78, 0.0, -0.25), (-0.78, 0.3, -0.25), (0.01, 0.01), (0.07, 0.07), sides=4)
    H.frustum("forearm.R", "steel", (-0.78, 2.2, -0.25), (-0.78, 2.4, -0.25), (0.09, 0.09), (0.09, 0.09), sides=4)
    pts = [(-0.82, 2.35, -0.25), (-0.86, 2.6, -0.25), (-1.0, 2.85, -0.3), (-1.1, 2.95, -0.4)]
    chain("forearm.R", "steel", pts, [(0.17, 0.05), (0.26, 0.05), (0.15, 0.04), (0.02, 0.01)])
    pts = [(-0.85, 2.3, -0.25), (-0.98, 2.0, -0.28), (-1.04, 1.7, -0.32), (-1.0, 1.5, -0.4)]
    chain("forearm.R", "steel", pts, [(0.12, 0.04), (0.14, 0.04), (0.1, 0.03), (0.01, 0.01)])


def make():
    head()
    torso()
    pelvis()
    for s, side in ((1, "L"), (-1, "R")):
        legs(s, side)
        arms(s, side)
    weapon()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * SH_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * HAND_X, EL_Y, 0), (s * HAND_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("n00Z", "biped", PALETTE, make, joints())
