"""Sage Druid (e00J): druida de manto e mascara, cajado de foice na mao direita; medido em refs/e00J/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/e00J.py -- <out.glb>

Sem pernas a vista: a bata e macia (pelve + coxas) e as botas vao nos ossos shin/foot, entao o passo anima.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "robe": 0x5F7A3F, "gold": 0xD9A033, "mantle": 0x9A6A30, "hood": 0x8E5E2E, "mask": 0xEADCBC, "eye": 0x1A1A1A,
    "beard": 0x1E9A7A, "coil": 0x8A4A3A, "nail": 0xB0B4BA, "boot": 0x4A2C1E, "glove": 0x8E6AAA, "belt": 0x5A3A22,
    "steel": 0xA0A4AC, "wood": 0x5A3A26, "dark": 0x2A3A1E,
}
HIP, KNEE, ANKLE, LEG_X = 1.18, 0.56, 0.1, 0.28
HAND_R = (-0.64, 1.12, 0.48)


def hem(p):
    """A bata acompanha as coxas embaixo; o topo fica na pelve."""
    if p[1] > 1.1:
        return {"pelvis": 1.0}
    return {"pelvis": 0.5, "thigh.L" if p[0] > 0 else "thigh.R": 0.5}


def head():
    H.frustum("head", "hood", (0, 1.98, -0.06), (0, 2.28, -0.06), (0.34, 0.31), (0.3, 0.29), sides=8)
    H.frustum("head", "hood", (0, 2.28, -0.07), (0, 2.56, -0.12), (0.3, 0.29), (0.17, 0.2), sides=8)
    H.frustum("head", "mask", (0, 2.02, 0.2), (0, 2.46, 0.2), (0.19, 0.11), (0.17, 0.1), sides=6)
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.07, 2.32, 0.3), (0.06, 0.09, 0.03))
    for i in (-2.5, -1.5, -0.5, 0.5, 1.5, 2.5):
        H.frustum("head", "nail", (i * 0.06, 2.52, -0.1), (i * 0.12, 2.72, -0.1), (0.03, 0.03), (0.012, 0.012), sides=4)


def torso():
    H.frustum("spine", "robe", (0, 1.45, 0), (0, 1.95, 0), (0.43, 0.34), (0.5, 0.35), sides=8)
    H.frustum("spine", "mantle", (0, 1.68, 0), (0, 1.98, 0), (0.8, 0.56), (0.5, 0.4), sides=8)
    H.frustum("spine", "mantle", (0, 1.96, 0), (0, 2.14, 0), (0.5, 0.4), (0.28, 0.26), sides=8)
    H.frustum("spine", "gold", (0, 1.62, 0), (0, 1.7, 0), (0.8, 0.56), (0.8, 0.56), sides=8)
    H.frustum("spine", "beard", (0, 1.5, 0.34), (0, 2.1, 0.29), (0.12, 0.04), (0.2, 0.06), sides=4)
    H.frustum("pelvis", "robe", (0, 1.15, 0), (0, 1.5, 0), (0.45, 0.36), (0.43, 0.34), sides=8)
    H.frustum("pelvis", "belt", (0, 1.34, 0), (0, 1.5, 0), (0.46, 0.37), (0.46, 0.37), sides=8)
    H.box("pelvis", "steel", (0.16, 1.05, 0.38), (0.1, 0.55, 0.04))
    H.box("pelvis", "belt", (-0.3, 1.15, 0.37), (0.12, 0.6, 0.04))
    H.soft(H.frustum("pelvis", "robe", (0, 0.27, 0), (0, 1.5, 0), (0.6, 0.42), (0.44, 0.35), sides=8), hem)
    H.soft(H.frustum("pelvis", "gold", (0, 0.27, 0), (0, 0.42, 0), (0.61, 0.43), (0.59, 0.41), sides=8), hem)


def coils():
    for cx, cy, cz, r in ((0.3, 2.2, -0.5, 0.32), (-0.3, 2.25, -0.5, 0.32), (0.0, 1.95, -0.56, 0.36)):
        pts = [(cx + r * math.cos(a * math.pi / 4), cy + r * math.sin(a * math.pi / 4), cz) for a in range(9)]
        H.chain("spine", "coil", pts, [(0.07, 0.07)] * 9)


def boots(s, side):
    kx = s * LEG_X
    H.frustum(f"shin.{side}", "boot", (kx, 0.04, 0), (kx, 0.5, 0), (0.16, 0.17), (0.2, 0.2), sides=6)
    H.frustum(f"foot.{side}", "boot", (kx, 0.03, -0.04), (kx, 0.2, -0.04), (0.19, 0.2), (0.17, 0.18), sides=6)
    H.frustum(f"foot.{side}", "boot", (kx, 0.09, 0.0), (kx, 0.07, 0.5), (0.18, 0.12), (0.17, 0.07), sides=6)


def sleeve(side, pts, fist):
    s = 1 if side == "L" else -1
    sh, el, wr = pts
    H.frustum(f"arm.{side}", "robe", (s * 0.5, 1.98, 0), el, (0.22, 0.24), (0.2, 0.2), sides=6)
    H.frustum(f"forearm.{side}", "robe", el, wr, (0.2, 0.2), (0.25, 0.25), sides=6)
    H.frustum(f"forearm.{side}", "gold", (wr[0], wr[1] + 0.08, wr[2]), (wr[0], wr[1] - 0.04, wr[2]), (0.26, 0.26), (0.27, 0.27), sides=6)
    H.frustum(f"forearm.{side}", "glove", (fist[0], fist[1] + 0.06, fist[2]), (fist[0], fist[1] - 0.14, fist[2]), (0.15, 0.15), (0.13, 0.13), sides=6)


def staff():
    x, _, z = HAND_R
    H.frustum("forearm.R", "wood", (x, 0.0, z), (x, 2.0, z), (0.055, 0.055), (0.05, 0.05), sides=6)
    H.frustum("forearm.R", "steel", (x, 1.85, z), (x, 2.05, z), (0.08, 0.08), (0.08, 0.08), sides=6)
    pts = [(x, 2.0, z), (-0.8, 2.12, z), (-0.93, 2.38, z), (-0.88, 2.66, z), (-0.68, 2.84, z), (-0.45, 2.82, z), (-0.3, 2.74, z)]
    rad = [(0.1, 0.06), (0.1, 0.06), (0.09, 0.06), (0.08, 0.055), (0.06, 0.045), (0.04, 0.03), (0.012, 0.01)]
    H.chain("forearm.R", "steel", pts, rad, sides=4)


def make():
    head()
    torso()
    coils()
    for s, side in ((1, "L"), (-1, "R")):
        boots(s, side)
    sleeve("L", ((0.5, 1.95, 0), (0.62, 1.4, 0.05), (0.56, 1.0, 0.1)), (0.56, 0.98, 0.1))
    sleeve("R", ((-0.5, 1.95, 0), (-0.6, 1.5, 0.2), (-0.62, 1.15, 0.45)), (-0.64, 1.12, 0.48))
    staff()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, 1.45, 0)), "spine": ((0, 1.45, 0), (0, 2.1, 0)), "head": ((0, 2.1, 0), (0, 2.72, 0)),
           "arm.L": ((0.5, 1.95, 0), (0.62, 1.4, 0.05)), "forearm.L": ((0.62, 1.4, 0.05), (0.56, 1.0, 0.1)),
           "arm.R": ((-0.5, 1.95, 0), (-0.6, 1.5, 0.2)), "forearm.R": ((-0.6, 1.5, 0.2), (-0.62, 1.15, 0.45))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("e00J", "biped", PALETTE, make, joints())
