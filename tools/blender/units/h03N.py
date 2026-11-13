"""Greater Elemental Of Earth (h03N): medido em artifacts/model-sheets/refs/h03N/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/h03N.py -- <out.glb>

Bruto de pedra com ombros enormes, veio de lava no peito e nas costas, argolas de aco nos pulsos,
cabeca com tres lajes, broca de ferrugem no peito e viga de madeira amarrada nas costas. Sem arma: punhos grandes.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "stone": 0x5F5757, "stone_dk": 0x3A302F, "stone_mid": 0x4B4141, "slab": 0x74625B, "rust": 0x8A4A30,
    "beam": 0x7B4130, "ring": 0x5F7378, "lava": 0xFF7A1E,
}

HIP, KNEE, ANKLE, LEG_X = 0.98, 0.54, 0.2, 0.3
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.92, 2.1, 1.0, 1.32, 0.62
ZC = -0.05


def head():
    H.frustum("head", "stone_dk", (0, 2.06, 0.22), (0, 2.34, 0.2), (0.2, 0.2), (0.25, 0.23), sides=6)
    H.frustum("head", "stone", (0, 2.34, 0.2), (0, 2.5, 0.12), (0.25, 0.23), (0.22, 0.24), sides=6)
    H.frustum("head", "stone_mid", (0, 1.95, 0.0), (0, 2.3, 0.05), (0.4, 0.34), (0.34, 0.3), sides=6)      # pescoco grosso
    for s in (-1, 1):
        H.box("head", "lava", (s * 0.1, 2.3, 0.42), (0.09, 0.04, 0.03))
        H.box("head", "slab", (s * 0.27, 2.62, 0.1), (0.22, 0.12, 0.7))
    H.box("head", "slab", (0, 2.66, 0.1), (0.26, 0.14, 0.76))


def torso():
    rings = [(0.95, 0.42, 0.32), (1.3, 0.66, 0.42), (1.8, 0.84, 0.48), (2.25, 0.88, 0.44), (2.5, 0.5, 0.32)]
    for (y0, w0, d0), (y1, w1, d1) in zip(rings, rings[1:]):
        H.frustum("spine", "stone", (0, y0, ZC), (0, y1, ZC), (w0, d0), (w1, d1), sides=8)
    H.frustum("spine", "stone_mid", (0, 1.1, ZC), (0, 1.8, ZC), (0.6, 0.44), (0.72, 0.5), sides=8)     # ventre escuro
    H.box("spine", "lava", (0, 1.62, 0.395), (0.07, 0.95, 0.05))
    H.box("spine", "lava", (0, 1.7, -0.5), (0.07, 1.1, 0.05))
    H.frustum("spine", "rust", (0, 1.45, 0.38), (0, 1.42, 0.9), (0.2, 0.2), (0.012, 0.012), sides=6)   # broca do peito
    H.box("spine", "beam", (0, 1.05, -0.5), (1.9, 0.24, 0.16))                                         # viga nas costas
    H.frustum("spine", "rust", (0, 1.3, -0.45), (0, 1.35, -1.0), (0.1, 0.1), (0.01, 0.01), sides=6)
    H.frustum("pelvis", "stone_dk", (0, 0.78, 0), (0, 1.12, 0), (0.4, 0.3), (0.46, 0.34), sides=8)


def shoulder_arm(s, side):
    a = f"arm.{side}"
    H.frustum(a, "stone", (s * 0.9, 1.6, ZC), (s * SH_X, 2.2, ZC), (0.32, 0.34), (0.42, 0.4), sides=8)      # ombro enorme
    H.frustum(a, "stone", (s * SH_X, 2.2, ZC), (s * 0.78, 2.4, ZC), (0.42, 0.4), (0.32, 0.3), sides=8)
    H.frustum(a, "stone_dk", (s * 0.96, 2.0, 0), (s * EL_X, EL_Y, 0), (0.3, 0.32), (0.28, 0.3), sides=8)


def forearm_fist(s, side):
    b, x = f"forearm.{side}", s * 0.99
    H.frustum(b, "stone_dk", (x, EL_Y + 0.05, 0), (x, 0.95, 0.02), (0.28, 0.3), (0.31, 0.32), sides=8)
    H.frustum(b, "ring", (x, 0.88, 0.02), (x, 1.0, 0.02), (0.37, 0.37), (0.37, 0.37), sides=8)
    H.frustum(b, "stone", (x, 0.92, 0.02), (x, 0.7, 0.06), (0.3, 0.3), (0.34, 0.34), sides=8)
    H.frustum(b, "stone_dk", (x, 0.72, 0.06), (x, 0.46, 0.1), (0.34, 0.34), (0.28, 0.3), sides=8)       # punho


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * LEG_X
        H.frustum(f"thigh.{side}", "stone_dk", (x, KNEE, 0), (x, HIP + 0.06, 0), (0.24, 0.26), (0.32, 0.32), sides=6)
        H.frustum(f"thigh.{side}", "stone", (x, KNEE + 0.1, 0.02), (x, KNEE + 0.4, 0.02), (0.26, 0.28), (0.3, 0.3), sides=6)
        H.frustum(f"shin.{side}", "stone_dk", (x, ANKLE, 0), (x, KNEE + 0.04, 0), (0.25, 0.27), (0.28, 0.3), sides=6)
        H.frustum(f"foot.{side}", "stone", (x, 0.1, -0.12), (x, 0.09, 0.5), (0.3, 0.2), (0.25, 0.1), sides=6)
        H.frustum(f"foot.{side}", "stone_dk", (x, 0.02, -0.16), (x, 0.03, 0.52), (0.31, 0.05), (0.26, 0.05), sides=6)


def make():
    head()
    torso()
    legs()
    for s, side in ((1, "L"), (-1, "R")):
        shoulder_arm(s, side)
        forearm_fist(s, side)


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, 1.3, 0)), "spine": ((0, 1.3, 0), (0, 2.05, 0)), "head": ((0, 2.05, 0.1), (0, 2.5, 0.1))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * (EL_X - 0.02), WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("h03N", "biped", PALETTE, make, joints())
