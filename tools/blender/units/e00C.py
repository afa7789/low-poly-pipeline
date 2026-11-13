"""Ancient Keeper (e00C): medido em artifacts/model-sheets/refs/e00C/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/e00C.py -- <out.glb>

Gigante de casca com ombreiras de musgo, crânio de cervo, galhada com lanternas, peito e pernas brilhando em verde.
A prancha nao desenha arma: o golpe e de punho (antebraco + mao enormes). Pernas-raiz: thigh/shin/foot do biped.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "bark": 0x41302A, "bark_lt": 0x56423A, "moss": 0x606E3C, "moss_dk": 0x4C5830, "glow": 0x9AE040,
    "bone": 0x7A6350, "socket": 0x1E1612, "antler": 0x6E5B49, "antler_dk": 0x4E3F34, "wood": 0x5A4332,
}

HIP, KNEE, ANKLE, LEG_X = 0.9, 0.5, 0.14, 0.25
WAIST, NECK = 1.3, 2.15
SH_X, SH_Y, EL_X, EL_Y, WR_X, WR_Y = 0.8, 2.0, 0.88, 1.25, 0.88, 0.8


def head():
    H.frustum("head", "bone", (0, 2.04, 0.2), (0, 2.5, 0.2), (0.21, 0.27), (0.2, 0.24), sides=6)
    H.chain("head", "bone", [(0, 2.3, 0.3), (0, 2.22, 0.42), (0, 2.14, 0.56)], [(0.18, 0.17), (0.14, 0.14), (0.07, 0.07)], sides=6)
    for s in (-1, 1):
        H.box("head", "socket", (s * 0.1, 2.32, 0.46), (0.09, 0.1, 0.06))


def antlers():
    for s in (-1, 1):
        beam = [(0.1, 2.44, 0.15), (0.4, 2.65, 0.08), (0.68, 2.85, 0.0), (0.95, 3.0, -0.06)]
        H.chain("head", "antler", [(s * x, y, z) for x, y, z in beam], [(0.1, 0.1), (0.09, 0.09), (0.07, 0.07), (0.045, 0.045)], sides=4)
        H.chain("head", "antler_dk", [(s * 0.4, 2.65, 0.08), (s * 0.45, 2.98, 0.0)], [(0.05, 0.05), (0.03, 0.03)], sides=4)
        H.chain("head", "antler_dk", [(s * 0.68, 2.85, 0.0), (s * 0.66, 3.05, -0.04)], [(0.05, 0.05), (0.03, 0.03)], sides=4)
        H.box("head", "wood", (s * 0.45, 3.04, 0.0), (0.13, 0.13, 0.13))
        H.box("head", "wood", (s * 0.66, 3.12, -0.04), (0.13, 0.13, 0.13))
        H.box("head", "wood", (s * 0.98, 2.74, -0.06), (0.17, 0.05, 0.17))                  # tampa da lanterna
        H.box("head", "glow", (s * 0.98, 2.6, -0.06), (0.14, 0.22, 0.14))
        H.box("head", "wood", (s * 0.98, 2.47, -0.06), (0.17, 0.05, 0.17))


def torso():
    H.frustum("pelvis", "bark", (0, 0.8, 0), (0, WAIST + 0.05, 0), (0.42, 0.3), (0.46, 0.33), sides=8)
    H.frustum("spine", "bark", (0, WAIST, -0.04), (0, 1.85, -0.04), (0.5, 0.35), (0.8, 0.42), sides=8)
    H.frustum("spine", "bark_lt", (0, 1.85, -0.04), (0, 2.18, -0.02), (0.8, 0.42), (0.5, 0.32), sides=8)
    H.frustum("spine", "bark", (0, 2.1, 0.0), (0, 2.32, 0.2), (0.22, 0.22), (0.17, 0.17), sides=6)                   # pescoço
    H.frustum("spine", "glow", (0, 1.2, 0.3), (0, 1.9, 0.38), (0.07, 0.04), (0.1, 0.04), sides=4)
    H.box("spine", "moss", (0, 1.75, -0.47), (0.7, 0.45, 0.07))
    H.box("spine", "moss_dk", (0, 1.28, -0.4), (0.5, 0.2, 0.07))


def arm(s, side):
    a, f = f"arm.{side}", f"forearm.{side}"
    H.frustum(a, "moss", (s * 0.6, 2.24, 0), (s * 0.9, 1.92, 0), (0.22, 0.36), (0.28, 0.38), sides=6)                 # ombreira
    H.frustum(a, "bark", (s * SH_X, SH_Y + 0.05, 0), (s * EL_X, EL_Y + 0.05, 0), (0.33, 0.31), (0.3, 0.29), sides=8)
    H.frustum(f, "bark", (s * EL_X, EL_Y + 0.05, 0), (s * WR_X, WR_Y + 0.1, 0.05), (0.3, 0.29), (0.34, 0.32), sides=8)
    H.box(f, "moss", (s * 1.15, 1.05, 0.0), (0.08, 0.55, 0.34))                                                         # braçadeira
    H.frustum(f, "bark_lt", (s * WR_X, WR_Y + 0.1, 0.05), (s * WR_X, WR_Y - 0.34, 0.12), (0.36, 0.28), (0.26, 0.18), sides=6)  # punho
    for dx in (-0.14, -0.05, 0.05, 0.14):
        H.frustum(f, "bark", (s * (WR_X + dx), WR_Y - 0.15, 0.1), (s * (WR_X + dx * 1.2), WR_Y - 0.44, 0.2), (0.085, 0.085), (0.05, 0.05), sides=4)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * LEG_X
        H.frustum(f"thigh.{side}", "bark", (x, KNEE + 0.1, -0.03), (x, HIP + 0.08, -0.02), (0.2, 0.2), (0.25, 0.26), sides=6)
        H.frustum(f"shin.{side}", "glow", (x, 0.03, -0.03), (x, KNEE + 0.14, -0.03), (0.2, 0.2), (0.17, 0.17), sides=6)
        H.frustum(f"shin.{side}", "bark", (x, KNEE - 0.04, -0.03), (x, KNEE + 0.14, -0.03), (0.2, 0.2), (0.2, 0.2), sides=6)
        H.frustum(f"foot.{side}", "glow", (x, 0.1, -0.1), (x, 0.06, 0.34), (0.2, 0.1), (0.17, 0.05), sides=4)
    H.panel("pelvis", "bark_lt", [(0.28, 0.95, -0.3), (-0.28, 0.95, -0.3), (-0.2, 0.7, -0.34), (0.2, 0.7, -0.34)], thickness=0.06)


def make():
    head()
    antlers()
    torso()
    legs()
    for s, side in ((1, "L"), (-1, "R")):
        arm(s, side)


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, -0.04), (0, NECK, 0)),
           "head": ((0, NECK, 0.05), (0, 2.55, 0.25))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * WR_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, -0.03))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, -0.03), (s * LEG_X, ANKLE, -0.03))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, -0.03), (s * LEG_X, 0.06, 0.5))
    return out


H.build("e00C", "biped", PALETTE, make, joints())
