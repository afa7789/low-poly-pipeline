"""Greater Ghoul (u008): medido em artifacts/model-sheets/refs/u008/sheet.jpg. Gorila de osso curvado, caveira em argola de
couro, manoplas com garras enormes nas duas mãos (o ataque: o golpe de manopla).

    blender -b --factory-startup -P tools/blender/units/u008.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "bone": 0xCFC3A8, "bone_dk": 0xA89C84, "brown": 0x6A4630, "brown_dk": 0x4A2F20, "claw": 0x7A5538,
    "eye": 0x2FE08A, "skull": 0xE6DEC8, "tooth": 0xF2EEDC, "void": 0x1E1812,
}

PEL, SPN = (0, 0.95, -0.5), (0, 1.38, -0.45)
NECK, TOP = (0, 1.95, -0.05), (0, 2.25, -0.2)
SH, EL, WR = (0.5, 1.95, -0.1), (0.76, 1.15, 0.1), (0.74, 0.72, 0.4)
HIP, KNEE, ANK, TOE = (0.26, 1.05, -0.5), (0.3, 0.58, -0.25), (0.3, 0.15, -0.5), (0.3, 0.06, 0.0)


def head():
    H.frustum("head", "brown", (0, 1.58, -0.05), (0, 2.1, -0.05), (0.31, 0.31), (0.36, 0.36), sides=8)        # argola de couro
    H.frustum("head", "brown_dk", (0, 1.58, -0.05), (0, 1.66, -0.05), (0.34, 0.34), (0.31, 0.31), sides=8)
    H.frustum("head", "skull", (0, 1.8, 0.1), (0, 1.82, 0.5), (0.26, 0.28), (0.22, 0.23), sides=8)             # crânio
    H.frustum("head", "bone_dk", (0, 1.78, 0.48), (0, 1.68, 0.62), (0.12, 0.1), (0.09, 0.08), sides=6)       # mandíbula
    H.box("head", "void", (0, 1.82, 0.52), (0.13, 0.05, 0.04))
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.1, 1.9, 0.5), (0.08, 0.06, 0.04))
        H.box("head", "tooth", (s * 0.04, 1.69, 0.63), (0.04, 0.05, 0.03))


def torso():
    H.frustum("pelvis", "bone", (0, 0.82, -0.5), (0, 1.3, -0.45), (0.34, 0.34), (0.4, 0.36), sides=8)
    H.frustum("spine", "bone", (0, 1.3, -0.45), (0, 1.7, -0.3), (0.4, 0.36), (0.48, 0.42), sides=8)
    H.frustum("spine", "bone", (0, 1.7, -0.3), (0, 2.05, -0.12), (0.48, 0.42), (0.48, 0.4), sides=8)
    H.frustum("spine", "bone_dk", (0, 2.0, -0.2), (0, 2.3, -0.28), (0.44, 0.38), (0.26, 0.24), sides=8)      # corcunda
    H.frustum("pelvis", "brown", (0, 1.18, -0.47), (0, 1.38, -0.44), (0.48, 0.44), (0.5, 0.45), sides=8)    # cinto
    for s in (-1, 1):      # X de correias na frente e nas costas
        H.frustum("spine", "brown", (s * 0.42, 1.95, 0.34), (-s * 0.38, 1.42, 0.08), (0.13, 0.04), (0.13, 0.04), sides=4)
        H.frustum("spine", "brown", (s * 0.46, 2.1, -0.62), (-s * 0.4, 1.45, -0.8), (0.1, 0.035), (0.1, 0.035), sides=4)


def leg(s, side):
    h, k, a, t = (tuple([s * p[0], *p[1:]]) for p in (HIP, KNEE, ANK, TOE))
    H.frustum(f"thigh.{side}", "bone", (h[0], h[1] + 0.05, h[2]), k, (0.27, 0.27), (0.19, 0.19), sides=6)
    H.frustum(f"shin.{side}", "bone", k, a, (0.2, 0.2), (0.12, 0.12), sides=6)
    H.frustum(f"foot.{side}", "bone", (a[0], 0.12, a[2] - 0.05), (a[0], 0.07, 0.0), (0.14, 0.1), (0.15, 0.04), sides=6)
    for dx in (-0.1, 0, 0.1):
        H.frustum(f"foot.{side}", "tooth", (a[0] + dx, 0.08, -0.02), (a[0] + dx * 1.2, 0.05, 0.2), (0.04, 0.035), (0.005, 0.005), sides=4)


def arm(s, side):
    sh, el, wr = (tuple([s * p[0], *p[1:]]) for p in (SH, EL, WR))
    f = f"forearm.{side}"
    H.frustum(f"arm.{side}", "bone", (s * 0.36, 2.1, -0.15), (s * 0.56, 1.78, -0.1), (0.22, 0.24), (0.27, 0.26), sides=8)      # ombro
    H.frustum(f"arm.{side}", "bone", (s * 0.54, 1.85, -0.1), el, (0.27, 0.26), (0.22, 0.22), sides=8)
    H.frustum(f"arm.{side}", "bone_dk", (s * 0.68, 1.5, -0.02), el, (0.24, 0.23), (0.22, 0.22), sides=8)
    H.frustum(f, "bone", (el[0], el[1] + 0.05, el[2]), (wr[0], wr[1] + 0.1, wr[2] - 0.03), (0.2, 0.2), (0.24, 0.24), sides=8)
    # manopla: bloco grande de couro na ponta do antebraço, quatro garras para a frente e para baixo
    H.frustum(f, "brown", (wr[0], 0.75, 0.38), (wr[0], 0.3, 0.52), (0.27, 0.27), (0.29, 0.27), sides=4)
    H.frustum(f, "brown_dk", (wr[0], 0.34, 0.5), (wr[0], 0.24, 0.54), (0.29, 0.27), (0.27, 0.25), sides=4)
    for dx in (-0.2, -0.07, 0.07, 0.2):
        H.frustum(f, "claw", (wr[0] + dx, 0.42, 0.68), (wr[0] + dx, 0.06, 0.98), (0.075, 0.075), (0.008, 0.008), sides=4)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        arm(s, side)


def joints():
    out = {"pelvis": (PEL, SPN), "spine": (SPN, NECK), "head": ((0, 1.8, 0.0), (0, 1.85, 0.6))}
    for s, side in ((1, "L"), (-1, "R")):
        m = lambda p: (s * p[0], p[1], p[2])  # noqa: E731
        out[f"arm.{side}"] = (m(SH), m(EL))
        out[f"forearm.{side}"] = (m(EL), m(WR))
        out[f"thigh.{side}"] = (m(HIP), m(KNEE))
        out[f"shin.{side}"] = (m(KNEE), m(ANK))
        out[f"foot.{side}"] = (m(ANK), m(TOE))
    return out


H.build("u008", "biped", PALETTE, make, joints())
