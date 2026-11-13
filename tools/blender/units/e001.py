"""Huntress (e001): medido em artifacts/model-sheets/refs/e001/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/e001.py -- <out.glb>

Arco recurvo na mão esquerda (antebraço L, atravessado à frente); lanterna na mão direita; aljava e capa nas costas.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "hood": 0x403650, "hood_dk": 0x2E2840, "skin": 0xC9A0E0, "eye": 0xD8C890, "leather": 0x5A4558, "leather_dk": 0x453340,
    "armor": 0x8C8F9A, "armor_dk": 0x6E717C, "cape": 0x1E1A2C, "boot": 0x4A3A48, "pants": 0x2E2842, "fang": 0xE8DCB0,
    "glow": 0xB080E0, "bow": 0x9A9CA6, "string": 0xCFCFD6, "glove": 0x4E3A3A, "strap": 0x3C2C36,
}

HIP, KNEE, ANKLE, LEG_X = 1.1, 0.64, 0.24, 0.25
WAIST, NECK, TOP = 1.45, 2.08, 2.7
SH_X, SH_Y, EL_Y, WR_Y = 0.45, 2.02, 1.5, 1.0
EL_X = 0.5
HAND_L = (0.42, 1.12, 0.3)      # mão do arco
HAND_R = (-0.56, 1.0, 0.0)      # mão da lanterna


def drape(p):
    """A capa: topo no tronco, meio na pelve, barra acompanha as coxas."""
    if p[1] > WAIST:
        return {"spine": 1.0}
    if p[1] > 1.0:
        return {"pelvis": 1.0}
    return {"pelvis": 0.4, "thigh.L" if p[0] > 0 else "thigh.R": 0.6}


def head():
    H.frustum("head", "skin", (0, 2.02, 0.0), (0, 2.2, 0.03), (0.09, 0.1), (0.11, 0.11), sides=6)       # pescoço
    H.frustum("head", "skin", (0, 2.2, 0.17), (0, 2.5, 0.17), (0.13, 0.12), (0.14, 0.12), sides=6)      # rosto
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.07, 2.36, 0.2), (0.07, 0.035, 0.02))
        H.frustum("head", "skin", (s * 0.15, 2.33, 0.04), (s * 0.4, 2.52, 0.0), (0.04, 0.05), (0.005, 0.01), sides=4)  # orelha
    H.frustum("head", "hood", (0, 2.1, -0.12), (0, 2.42, -0.12), (0.26, 0.26), (0.25, 0.26), sides=8)    # capuz
    H.frustum("head", "hood", (0, 2.42, -0.12), (0, 2.62, -0.14), (0.25, 0.26), (0.15, 0.17), sides=8)
    H.frustum("head", "hood", (0, 2.62, -0.14), (0, 2.76, -0.26), (0.15, 0.17), (0.02, 0.03), sides=8)    # ponta atrás
    H.frustum("head", "fang", (0, 2.08, 0.1), (0, 2.0, 0.12), (0.03, 0.02), (0.01, 0.01), sides=4)        # colar de presas


def torso():
    H.frustum("spine", "leather", (0, WAIST - 0.05, 0), (0, 1.8, 0.02), (0.34, 0.26), (0.4, 0.28), sides=8)
    H.frustum("spine", "leather", (0, 1.8, 0.02), (0, 2.1, 0.02), (0.4, 0.28), (0.3, 0.24), sides=8)
    H.frustum("spine", "hood", (0, 2.0, 0), (0, 2.14, 0), (0.42, 0.3), (0.2, 0.2), sides=8)          # gola
    H.frustum("spine", "strap", (-0.28, 2.0, 0.27), (0.28, 1.55, 0.3), (0.04, 0.025), (0.04, 0.025), sides=4)
    H.frustum("spine", "strap", (0.28, 2.0, 0.27), (-0.28, 1.55, 0.3), (0.04, 0.025), (0.04, 0.025), sides=4)
    H.frustum("pelvis", "leather_dk", (0, WAIST - 0.12, 0), (0, WAIST + 0.04, 0), (0.37, 0.3), (0.37, 0.3), sides=8)   # cinto
    H.frustum("pelvis", "leather", (0, 0.95, 0), (0, WAIST - 0.1, 0), (0.38, 0.3), (0.38, 0.3), sides=8)             # túnica
    H.frustum("pelvis", "pants", (0, 0.9, 0), (0, 1.2, 0), (0.34, 0.27), (0.38, 0.29), sides=8)
    H.frustum("spine", "armor", (0.28, 2.28, 0), (0.54, 1.84, 0), (0.22, 0.24), (0.2, 0.22), sides=6)      # ombreira esquerda grande
    H.frustum("spine", "armor_dk", (0.34, 1.92, 0), (0.58, 1.68, 0), (0.22, 0.23), (0.19, 0.21), sides=6)


def cape_and_quiver():
    cape = H.frustum("spine", "cape", (0, 0.45, -0.5), (0, 2.12, -0.3), (0.5, 0.04), (0.3, 0.05), sides=4)
    H.soft(cape, drape)
    H.frustum("spine", "armor_dk", (-0.1, 1.35, -0.4), (0.3, 2.35, -0.38), (0.11, 0.07), (0.1, 0.06), sides=4)   # aljava
    H.frustum("spine", "string", (0.28, 2.35, -0.38), (0.32, 2.5, -0.38), (0.08, 0.04), (0.02, 0.02), sides=4)   # penas


def legs(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "pants", (x, KNEE - 0.04, 0), (x, HIP + 0.04, 0), (0.2, 0.22), (0.23, 0.25), sides=6)
    H.frustum(f"thigh.{side}", "armor", (x, KNEE - 0.12, 0.04), (x, KNEE + 0.14, 0.04), (0.21, 0.23), (0.2, 0.22), sides=6)   # joelheira
    H.frustum(f"shin.{side}", "armor", (x, ANKLE + 0.08, 0.02), (x, KNEE + 0.04, 0.02), (0.17, 0.19), (0.22, 0.22), sides=6)  # grevas
    H.frustum(f"shin.{side}", "boot", (x, ANKLE - 0.02, 0), (x, ANKLE + 0.14, 0), (0.18, 0.19), (0.2, 0.21), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.04, -0.03), (x, ANKLE + 0.04, -0.03), (0.19, 0.22), (0.19, 0.2), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.11, 0.06), (x, 0.08, 0.44), (0.19, 0.12), (0.16, 0.07), sides=4)
    H.frustum(f"foot.{side}", "pants", (x, 0.02, -0.2), (x, 0.02, 0.46), (0.2, 0.022), (0.17, 0.022), sides=4)


def right_arm():
    """Braço direito (x-) pende: luva forte, lanterna roxa pendurada no punho."""
    H.frustum("arm.R", "hood", (-SH_X, SH_Y + 0.04, 0), (-EL_X, EL_Y - 0.02, 0), (0.17, 0.19), (0.17, 0.18), sides=6)
    H.frustum("forearm.R", "glove", (-EL_X, EL_Y + 0.02, 0), (-0.54, WR_Y + 0.08, 0), (0.17, 0.18), (0.2, 0.2), sides=6)
    H.frustum("forearm.R", "glove", (-0.54, WR_Y + 0.08, 0), (-0.56, WR_Y - 0.12, 0.02), (0.2, 0.2), (0.14, 0.15), sides=6)
    H.frustum("forearm.R", "armor_dk", (-0.58, WR_Y - 0.12, 0.02), (-0.58, WR_Y - 0.2, 0.02), (0.11, 0.1), (0.11, 0.1), sides=6)   # argola
    H.frustum("forearm.R", "glow", (-0.58, 0.5, 0.02), (-0.58, 0.8, 0.02), (0.15, 0.15), (0.13, 0.13), sides=6)
    H.frustum("forearm.R", "armor", (-0.58, 0.42, 0.02), (-0.58, 0.52, 0.02), (0.17, 0.17), (0.17, 0.17), sides=6)
    H.frustum("forearm.R", "armor", (-0.58, 0.8, 0.02), (-0.58, 0.86, 0.02), (0.15, 0.15), (0.06, 0.06), sides=6)


def left_arm():
    """Braço esquerdo (x+) dobrado à frente: luva e braçadeira cinza segurando o arco."""
    H.frustum("arm.L", "hood", (SH_X, SH_Y + 0.04, 0), (EL_X, EL_Y - 0.02, 0.04), (0.17, 0.19), (0.17, 0.18), sides=6)
    H.frustum("forearm.L", "armor", (EL_X, EL_Y + 0.02, 0.04), (0.46, 1.22, 0.24), (0.17, 0.2), (0.2, 0.21), sides=6)
    H.frustum("forearm.L", "glove", (0.46, 1.22, 0.24), (HAND_L[0], HAND_L[1] - 0.06, HAND_L[2] + 0.06), (0.2, 0.2), (0.17, 0.17), sides=6)


def bow():
    """Arco recurvo atravessado: empunhadura na mão, um braço sobe para o lado e para trás, o outro desce para a frente."""
    grip = HAND_L
    upper = [grip, (0.55, 1.22, 0.05), (0.72, 1.45, -0.25), (0.8, 1.62, -0.52)]
    lower = [grip, (0.2, 1.2, 0.4), (-0.05, 1.32, 0.58), (-0.22, 1.5, 0.66)]
    radii = [(0.06, 0.06), (0.06, 0.05), (0.045, 0.04), (0.012, 0.012)]
    H.chain("forearm.L", "bow", upper, radii, sides=4)
    H.chain("forearm.L", "bow", lower, radii, sides=4)
    H.frustum("forearm.L", "string", upper[-1], lower[-1], (0.012, 0.012), (0.012, 0.012), sides=4)


def make():
    head()
    torso()
    cape_and_quiver()
    for s, side in ((1, "L"), (-1, "R")):
        legs(s, side)
    left_arm()
    right_arm()
    bow()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("e001", "biped", PALETTE, make, joints())
