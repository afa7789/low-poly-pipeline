"""Gêmeos (e00E): UMA figura, a magra de máscara sorridente abraçada ao livro-razão (e00E-a).

Medida em artifacts/model-sheets/refs/e00E-a/sheet.jpg (a prancha que mostra só ela); a prancha e00E tem as duas.

    blender -b --factory-startup -P tools/blender/units/e00E.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "suit": 0x1F1B1D, "suit_dk": 0x151214, "suit_lt": 0x2C2629, "mask": 0xEDE3CF, "red": 0xB5202C, "brow": 0x2A2020,
    "book": 0x4A4548, "book_dk": 0x333033, "sole": 0x100E0F,
}

HIP, KNEE, ANKLE = 0.86, 0.48, 0.1
WAIST, NECK, TOP = 1.2, 1.85, 2.72
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.5, 1.74, 0.62, 1.2, 0.8
LEG_X = 0.17
BOOK_WRIST = (0.18, 1.02, 0.38)


def stack(bone, color, pts, sides=8):
    """Pilha de troncos de cone sobrepostos: pts = [(x, y, z, rx, rz), ...]."""
    for a, b in zip(pts, pts[1:]):
        H.frustum(bone, color, a[:3], b[:3], a[3:], b[3:], sides=sides)


def head():
    stack("head", "suit", [(0, 1.84, -0.02, 0.2, 0.2), (0, 2.1, -0.04, 0.33, 0.31), (0, 2.45, -0.04, 0.38, 0.34), (0, 2.72, -0.05, 0.22, 0.22)])
    stack("head", "mask", [(0, 1.93, 0.18, 0.22, 0.07), (0, 2.28, 0.2, 0.36, 0.1), (0, 2.5, 0.2, 0.34, 0.1), (0, 2.7, 0.14, 0.22, 0.07)], 8)
    for s in (-1, 1):
        H.box("head", "brow", (s * 0.14, 2.4, 0.31), (0.17, 0.04, 0.03))       # olhos sorrindo
        H.box("head", "red", (s * 0.2, 2.23, 0.31), (0.11, 0.07, 0.03))          # pontas da boca
    H.box("head", "red", (0, 2.13, 0.31), (0.3, 0.09, 0.03))


def torso():
    stack("pelvis", "suit", [(0, 0.8, 0, 0.3, 0.22), (0, 1.0, 0, 0.32, 0.24), (0, 1.22, 0, 0.3, 0.23)])
    stack("spine", "suit", [(0, 1.2, 0, 0.31, 0.24), (0, 1.5, 0, 0.4, 0.26), (0, 1.74, 0, 0.5, 0.27), (0, 1.9, 0, 0.18, 0.18)])


def leg(s, side):
    x0 = s * LEG_X
    stack(f"thigh.{side}", "suit", [(x0, KNEE - 0.04, 0, 0.14, 0.15), (x0, 0.7, 0.01, 0.16, 0.17), (x0, HIP + 0.06, 0, 0.19, 0.2)], 6)
    stack(f"shin.{side}", "suit", [(x0, ANKLE, 0, 0.12, 0.13), (x0, 0.3, 0, 0.13, 0.14), (x0, KNEE + 0.02, 0, 0.14, 0.15)], 6)
    stack(f"foot.{side}", "suit_dk", [(x0, 0.16, -0.02, 0.14, 0.15), (x0, 0.05, 0.08, 0.15, 0.17), (x0, 0.04, 0.34, 0.12, 0.08)], 6)
    H.frustum(f"foot.{side}", "sole", (x0, 0.015, -0.1), (x0, 0.015, 0.38), (0.15, 0.02), (0.12, 0.02), sides=4)


def free_arm(s, side):
    stack(f"arm.{side}", "suit", [(s * (SH_X + 0.03), SH_Y + 0.08, 0, 0.17, 0.17), (s * 0.58, 1.5, 0, 0.15, 0.15), (s * EL_X, EL_Y + 0.02, 0, 0.13, 0.13)], 6)
    stack(f"forearm.{side}", "suit", [(s * EL_X, EL_Y, 0, 0.13, 0.13), (s * EL_X, 1.0, 0.02, 0.145, 0.14), (s * EL_X, WR_Y + 0.02, 0.03, 0.12, 0.12)], 6)
    stack(f"forearm.{side}", "suit_lt", [(s * EL_X, WR_Y + 0.02, 0.03, 0.12, 0.12), (s * EL_X, 0.62, 0.05, 0.145, 0.09), (s * (EL_X - 0.03), 0.46, 0.06, 0.1, 0.07)], 6)


def book_arm():
    wx, wy, wz = BOOK_WRIST
    stack("arm.L", "suit", [(SH_X + 0.03, SH_Y + 0.08, 0, 0.17, 0.17), (0.58, 1.5, 0.02, 0.15, 0.15), (EL_X, EL_Y + 0.02, 0.06, 0.13, 0.13)], 6)
    stack("forearm.L", "suit", [(EL_X, EL_Y, 0.06, 0.13, 0.13), (0.42, 1.1, 0.22, 0.14, 0.14), (wx, wy, wz, 0.12, 0.12)], 6)
    stack("forearm.L", "suit_lt", [(wx + 0.02, wy + 0.02, wz, 0.12, 0.1), (wx - 0.12, wy - 0.02, wz + 0.04, 0.12, 0.08)], 6)
    # livro-razão grande, de pé contra o peito
    H.box("forearm.L", "book", (0.14, 1.2, 0.4), (0.56, 0.72, 0.09))
    H.box("forearm.L", "book_dk", (0.14, 1.2, 0.345), (0.58, 0.74, 0.03))
    H.box("forearm.L", "book_dk", (-0.12, 1.2, 0.4), (0.05, 0.72, 0.1))          # lombada


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    free_arm(-1, "R")
    book_arm()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0.06 if s > 0 else 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0.06 if s > 0 else 0), BOOK_WRIST if s > 0 else (s * EL_X, WR_Y, 0.03))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.05, 0.4))
    return out


H.build("e00E", "biped", PALETTE, make, joints())
