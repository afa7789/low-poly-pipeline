"""Ice Queen (n014): medido em artifacts/model-sheets/refs/n014/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n014.py -- <out.glb>

Casaco roxo longo evasê com barra branca, gola-capa branca, capuz, viseira ciano, coroa dourada alta.
Cajado na mao direita (x negativo, esquerda da imagem de frente): haste com anel, braco dourado com lanterna.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "purple": 0x62409A, "purple_dk": 0x48307A, "white": 0xEEEAF8, "gold": 0xD4A244, "black": 0x2A2A30,
    "cyan": 0x2CB8C8, "visor": 0xBDEBEF, "skin": 0xD9A27A, "brown": 0x4A3626,
}

HIP, KNEE, ANKLE, LEG_X = 1.2, 0.6, 0.1, 0.2
WAIST, NECK, TOP = 1.5, 2.1, 2.72
SH_X, SH_Y = 0.44, 1.85
R_EL, R_WR = (-0.5, 1.5, 0.1), (-0.54, 1.28, 0.42)
L_EL, L_WR = (0.5, 1.45, 0.0), (0.54, 1.08, 0.04)
STAFF_X, STAFF_Z = -0.56, 0.45


def hem(p):
    """A barra do casaco segue a coxa do seu lado; o topo fica na pelve."""
    if p[1] > 0.95:
        return {"pelvis": 1.0}
    t = (0.95 - p[1]) / 0.5
    return {"pelvis": 1 - min(1.0, t) * 0.6, "thigh.L" if p[0] > 0 else "thigh.R": min(1.0, t) * 0.6}


def head():
    H.frustum("head", "purple", (0, 2.08, 0), (0, 2.28, 0), (0.2, 0.2), (0.18, 0.18), sides=8)       # gola alta
    H.frustum("head", "purple", (0, 2.2, 0), (0, 2.52, 0), (0.21, 0.2), (0.21, 0.2), sides=8)       # capuz
    H.frustum("head", "purple", (0, 2.45, 0), (0, 2.56, 0), (0.21, 0.2), (0.12, 0.12), sides=8)
    H.box("head", "skin", (0, 2.3, 0.15), (0.16, 0.2, 0.06))
    H.box("head", "visor", (0, 2.4, 0.17), (0.33, 0.1, 0.07))
    H.frustum("head", "gold", (0, 2.5, 0), (0, 2.58, 0), (0.23, 0.23), (0.25, 0.25), sides=8)           # aro da coroa
    for i in range(8):
        a = i * 0.7854
        x, z = 0.2 * math.sin(a), 0.2 * math.cos(a)
        top = 0.72 if i % 2 == 0 else 0.6
        H.frustum("head", "gold", (x, 2.56, z), (x * 1.15, 2.05 + top, z * 1.15), (0.05, 0.05), (0.03, 0.03), sides=4)


def body():
    H.frustum("spine", "purple", (0, WAIST - 0.05, 0), (0, 1.85, 0), (0.24, 0.2), (0.34, 0.23), sides=8)    # tronco, busto leve
    H.frustum("spine", "purple", (0, 1.8, 0), (0, 2.1, 0), (0.36, 0.24), (0.26, 0.2), sides=8)
    H.frustum("spine", "white", (0, 1.78, 0), (0, 1.97, 0), (0.46, 0.34), (0.3, 0.24), sides=4)             # capa-gola larga
    H.box("spine", "gold", (0, 1.93, 0.27), (0.17, 0.1, 0.04))
    H.frustum("pelvis", "purple", (0, 0.95, 0), (0, WAIST, 0), (0.4, 0.31), (0.26, 0.21), sides=8)
    low = H.frustum("pelvis", "purple", (0, 0.66, 0), (0, 0.98, 0), (0.5, 0.4), (0.4, 0.31), sides=8)
    band = H.frustum("pelvis", "white", (0, 0.46, 0), (0, 0.68, 0), (0.54, 0.43), (0.5, 0.4), sides=8)   # barra branca
    H.soft(low, hem)
    H.soft(band, hem)


def leg(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "purple_dk", (x, KNEE, 0), (x, HIP + 0.05, 0), (0.11, 0.11), (0.13, 0.13), sides=6)
    H.frustum(f"shin.{side}", "black", (x, ANKLE - 0.02, 0), (x, KNEE + 0.08, 0), (0.18, 0.2), (0.21, 0.21), sides=6)
    H.frustum(f"foot.{side}", "black", (x, 0.06, -0.08), (x, 0.08, 0.28), (0.2, 0.14), (0.18, 0.1), sides=6)
    H.frustum(f"foot.{side}", "black", (x, 0.0, 0.0), (x, 0.0, 0.34), (0.18, 0.02), (0.16, 0.02), sides=4)


def arm(s, side, el, wr):
    a, f = f"arm.{side}", f"forearm.{side}"
    H.frustum(a, "purple", (s * SH_X, SH_Y + 0.06, 0), (el[0], el[1] + 0.03, el[2]), (0.19, 0.19), (0.15, 0.15), sides=6)
    H.frustum(f, "purple", (el[0], el[1] + 0.03, el[2]), (wr[0], wr[1] + 0.05, wr[2]), (0.15, 0.15), (0.16, 0.16), sides=6)
    H.frustum(f, "black", (wr[0], wr[1] + 0.07, wr[2]), (wr[0], wr[1] - 0.1, wr[2] + 0.02), (0.16, 0.16), (0.13, 0.13), sides=6)   # luva


def staff():
    f = "forearm.R"
    x, z = STAFF_X, STAFF_Z
    H.frustum(f, "brown", (x, 0.0, z), (x, 2.2, z), (0.055, 0.055), (0.045, 0.045), sides=6)
    H.frustum(f, "gold", (x, 0.0, z), (x, 0.1, z), (0.08, 0.08), (0.055, 0.055), sides=6)
    H.frustum(f, "gold", (x, 1.7, z), (x, 1.74, z), (0.19, 0.19), (0.19, 0.19), sides=8)                  # anel
    H.frustum(f, "gold", (x, 2.15, z), (x, 2.42, z + 0.28), (0.06, 0.06), (0.05, 0.05), sides=6)          # braco dourado
    H.frustum(f, "gold", (x, 2.42, z + 0.2), (x, 2.42, z + 0.58), (0.06, 0.06), (0.07, 0.07), sides=6)
    H.frustum(f, "cyan", (x, 2.42, z + 0.55), (x, 2.42, z + 0.66), (0.085, 0.085), (0.085, 0.085), sides=6)
    lz = z + 0.34
    H.frustum(f, "brown", (x, 2.28, lz), (x, 2.4, lz), (0.06, 0.06), (0.05, 0.05), sides=6)                # lanterna pendurada
    H.frustum(f, "cyan", (x, 1.9, lz), (x, 2.28, lz), (0.11, 0.11), (0.12, 0.12), sides=6)
    H.frustum(f, "brown", (x, 1.82, lz), (x, 1.92, lz), (0.07, 0.07), (0.11, 0.11), sides=6)


def make():
    head()
    body()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    arm(1, "L", L_EL, L_WR)
    arm(-1, "R", R_EL, R_WR)
    staff()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)), "head": ((0, NECK, 0), (0, TOP, 0)),
           "arm.L": ((SH_X, SH_Y, 0), L_EL), "forearm.L": (L_EL, L_WR),
           "arm.R": ((-SH_X, SH_Y, 0), R_EL), "forearm.R": (R_EL, R_WR)}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.4))
    return out


H.build("n014", "biped", PALETTE, make, joints())
