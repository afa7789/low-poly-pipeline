"""Ice Troll Shadow Priest (n015): medido em artifacts/model-sheets/refs/n015/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n015.py -- <out.glb>

Troll curvado de capuz marrom e orelhas enormes, casaco longo, bolsas pretas, tubos de osso no pescoco.
Cajado de martelo branco na mao direita (x negativo), lanterna de gelo na mao esquerda (x positivo).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "brown": 0x7A4C2C, "brown_dk": 0x3E2A20, "green": 0x3E9A8C, "green_dk": 0x2D7A70, "cream": 0xE8DCB8,
    "gold": 0xF0A020, "black": 0x22222A, "ice": 0xA9D3EE, "wood": 0xB08850, "white": 0xEFE9D8, "eye": 0xBFE0F5,
}

HIP, KNEE, ANKLE = 1.15, 0.62, 0.12
HIP_X, KNEE_X, ANK_X = 0.26, 0.36, 0.4
HZ = -0.15           # a pelve fica atras: o tronco curva para a frente
SH = (0.5, 1.85, 0.08)
R_EL, R_WR = (-0.62, 1.55, 0.1), (-0.8, 1.3, 0.3)
L_EL, L_WR = (0.62, 1.4, 0.45), (0.68, 0.98, 0.62)
STAFF_X, STAFF_Z = -0.82, 0.3


def hem(p):
    """A barra do casaco acompanha a coxa do seu lado; o topo fica na pelve."""
    if p[1] > 1.0:
        return {"pelvis": 1.0}
    t = min(1.0, (1.0 - p[1]) / 0.5) * 0.5
    return {"pelvis": 1 - t, "thigh.L" if p[0] > 0 else "thigh.R": t}


def head():
    H.frustum("head", "brown", (0, 1.95, 0.35), (0, 2.45, 0.35), (0.34, 0.34), (0.3, 0.3), sides=6)          # capuz
    H.frustum("head", "brown", (0, 2.4, 0.35), (0, 2.68, 0.3), (0.3, 0.3), (0.08, 0.1), sides=6)
    H.frustum("head", "green", (0, 1.88, 0.45), (0, 2.18, 0.62), (0.2, 0.2), (0.2, 0.2), sides=6)          # rosto
    H.frustum("head", "green", (0, 2.1, 0.66), (0, 1.98, 0.9), (0.06, 0.07), (0.04, 0.04), sides=4)         # nariz comprida
    H.frustum("head", "green_dk", (0, 1.82, 0.5), (0, 1.84, 0.72), (0.17, 0.14), (0.14, 0.1), sides=6)      # queixo
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.1, 2.12, 0.74), (0.09, 0.04, 0.04))
        H.frustum("head", "cream", (s * 0.1, 1.9, 0.68), (s * 0.1, 2.0, 0.72), (0.03, 0.03), (0.005, 0.005), sides=4)
        H.frustum("head", "green", (s * 0.22, 2.3, 0.4), (s * 0.68, 2.58, 0.18), (0.1, 0.07), (0.05, 0.02), sides=4)    # orelha


def body():
    H.frustum("spine", "brown", (0, 1.45, HZ), (0, 1.95, 0.1), (0.34, 0.3), (0.52, 0.36), sides=8)
    H.frustum("spine", "brown", (0, 1.9, 0.08), (0, 2.12, 0.2), (0.52, 0.36), (0.3, 0.26), sides=8)         # ombros caidos
    H.frustum("spine", "gold", (0, 1.9, 0.16), (0, 2.02, 0.22), (0.3, 0.28), (0.28, 0.26), sides=8)          # gola laranja
    for s in (-1, 1):       # tubos de osso do pescoco ao peito e as costas
        H.chain("spine", "cream", [(s * 0.1, 2.0, 0.75), (s * 0.2, 1.78, 0.62), (s * 0.3, 1.8, 0.45), (s * 0.34, 2.15, 0.35), (s * 0.3, 2.2, 0.05)],
                [(0.045, 0.045)] * 5, sides=4)
        H.box("spine", "black", (s * 0.4, 1.0, -0.45), (0.34, 0.36, 0.22))                                    # bolsas
    H.frustum("pelvis", "brown", (0, 0.98, HZ), (0, 1.5, -0.15), (0.4, 0.34), (0.32, 0.3), sides=8)
    low = H.frustum("pelvis", "brown", (0, 0.48, HZ), (0, 1.02, HZ), (0.54, 0.46), (0.4, 0.34), sides=8)
    H.soft(low, hem)
    H.frustum("pelvis", "black", (0, 0.45, HZ), (0, 1.05, HZ), (0.34, 0.3), (0.34, 0.3), sides=8)         # forro escuro sob a barra
    H.box("pelvis", "black", (0.4, 1.12, -0.12), (0.16, 0.3, 0.26))
    H.box("pelvis", "black", (-0.4, 1.12, -0.12), (0.16, 0.3, 0.26))


def leg(s, side):
    H.frustum(f"thigh.{side}", "black", (s * KNEE_X, KNEE, 0), (s * HIP_X, HIP + 0.05, HZ), (0.14, 0.14), (0.2, 0.2), sides=6)
    H.frustum(f"shin.{side}", "black", (s * ANK_X, 0.3, 0), (s * KNEE_X, KNEE + 0.05, 0), (0.15, 0.15), (0.14, 0.14), sides=6)
    H.frustum(f"shin.{side}", "green", (s * ANK_X, 0.06, 0), (s * ANK_X, 0.42, 0), (0.2, 0.2), (0.22, 0.22), sides=6)   # cano da bota
    H.frustum(f"foot.{side}", "green_dk", (s * ANK_X, 0.1, -0.12), (s * ANK_X, 0.08, 0.38), (0.21, 0.16), (0.19, 0.11), sides=6)


def arm(s, side, el, wr):
    a, f = f"arm.{side}", f"forearm.{side}"
    H.frustum(a, "brown", (s * SH[0], SH[1] + 0.07, SH[2]), (el[0], el[1] + 0.03, el[2]), (0.17, 0.17), (0.14, 0.14), sides=6)
    H.frustum(f, "brown", (el[0], el[1] + 0.03, el[2]), (wr[0], wr[1] + 0.1, wr[2]), (0.14, 0.14), (0.12, 0.12), sides=6)
    H.frustum(f, "green", (wr[0], wr[1] + 0.12, wr[2]), (wr[0], wr[1] - 0.1, wr[2]), (0.13, 0.13), (0.12, 0.12), sides=6)    # mao


def staff():
    f, x, z = "forearm.R", STAFF_X, STAFF_Z
    H.frustum(f, "wood", (x, 0.0, z), (x, 2.3, z), (0.055, 0.055), (0.05, 0.05), sides=6)
    H.frustum(f, "white", (x, 2.15, z), (x, 2.4, z), (0.1, 0.1), (0.1, 0.1), sides=4)
    H.box(f, "white", (x, 2.42, z), (0.55, 0.14, 0.14))                                               # cabeca do martelo
    for dy, dx in ((1.62, -0.13), (1.46, 0.12), (1.3, -0.12)):
        H.frustum(f, "ice", (x + dx, dy + 0.08, z), (x + dx * 1.3, dy - 0.14, z), (0.06, 0.04), (0.01, 0.01), sides=4)   # gelo na mao


def lantern():
    f, x, z = "forearm.L", 0.7, 0.64
    H.frustum(f, "ice", (x, 0.28, z), (x, 0.52, z), (0.12, 0.12), (0.2, 0.2), sides=6)
    H.frustum(f, "ice", (x, 0.52, z), (x, 0.76, z), (0.2, 0.2), (0.12, 0.12), sides=6)
    H.frustum(f, "wood", (x, 0.74, z), (x, 0.9, z), (0.03, 0.03), (0.03, 0.03), sides=4)           # alca


def make():
    head()
    body()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    arm(1, "L", L_EL, L_WR)
    arm(-1, "R", R_EL, R_WR)
    staff()
    lantern()


def joints():
    out = {"pelvis": ((0, HIP, HZ), (0, 1.5, -0.15)), "spine": ((0, 1.5, -0.12), (0, 2.0, 0.15)),
           "head": ((0, 2.0, 0.3), (0, 2.62, 0.4)),
           "arm.L": (SH, L_EL), "forearm.L": (L_EL, L_WR),
           "arm.R": ((-SH[0], SH[1], SH[2]), R_EL), "forearm.R": (R_EL, R_WR)}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * HIP_X, HIP, HZ), (s * KNEE_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * ANK_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * ANK_X, ANKLE, 0), (s * ANK_X, 0.06, 0.45))
    return out


H.build("n015", "biped", PALETTE, make, joints())
