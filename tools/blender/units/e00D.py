"""Treant (e00D): medido em artifacts/model-sheets/refs/e00D/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/e00D.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "bark": 0x5A3D2B, "bark_dk": 0x47301F, "bark_lt": 0x6B4A35, "moss": 0x6B7A2E, "moss_dk": 0x56632A,
    "glow": 0xB8E22A, "eye": 0xC8F02A,
}

HIP, KNEE, ANKLE = 1.0, 0.52, 0.16
WAIST, NECK, TOP = 1.45, 2.16, 2.72
SH_X, SH_Y, EL_X, EL_Y, WR_X, WR_Y = 0.76, 2.0, 1.02, 1.4, 1.1, 0.9
LEG_X, KNEE_X = 0.34, 0.38


def stack(bone, color, pts, sides=8):
    """Pilha de troncos de cone sobrepostos: pts = [(x, y, z, rx, rz), ...]."""
    for a, b in zip(pts, pts[1:]):
        H.frustum(bone, color, a[:3], b[:3], a[3:], b[3:], sides=sides)


def head():
    stack("head", "bark", [(0, 2.12, 0, 0.3, 0.27), (0, 2.4, 0, 0.27, 0.25), (0, 2.62, 0, 0.3, 0.26)], 6)
    for s in (-1, 1):       # topo quebrado em duas pontas
        H.frustum("head", "bark_dk", (s * 0.1, 2.6, 0), (s * 0.12, 2.72, 0), (0.12, 0.2), (0.07, 0.1), sides=4)
        H.box("head", "eye", (s * 0.11, 2.43, 0.25), (0.06, 0.05, 0.03))


def torso():
    stack("pelvis", "bark", [(0, 0.82, 0, 0.5, 0.38), (0, 1.1, 0, 0.56, 0.42), (0, 1.5, 0, 0.6, 0.44)])
    stack("spine", "bark", [(0, 1.5, 0, 0.6, 0.44), (0, 1.85, 0, 0.68, 0.46), (0, 2.18, 0, 0.5, 0.36)])
    H.frustum("spine", "bark_lt", (0, 1.2, 0.34), (0, 1.8, 0.4), (0.3, 0.1), (0.26, 0.1), sides=6)      # barriga
    H.frustum("spine", "glow", (0, 1.55, 0.42), (0, 1.95, 0.45), (0.15, 0.1), (0.12, 0.1), sides=6)      # gema no peito
    H.frustum("pelvis", "bark_dk", (0, 0.98, 0), (0, 1.1, 0), (0.58, 0.42), (0.58, 0.42), sides=8)


def leg(s, side):
    x0, x1 = s * LEG_X, s * KNEE_X
    stack(f"thigh.{side}", "bark", [(x1, KNEE - 0.04, 0, 0.27, 0.27), (x1, 0.78, 0, 0.25, 0.27), (x0, HIP + 0.05, 0, 0.36, 0.33)], 6)
    stack(f"shin.{side}", "bark_dk", [(x1 + s * 0.04, ANKLE, 0, 0.34, 0.3), (x1, 0.32, 0, 0.24, 0.24), (x1, KNEE + 0.02, 0, 0.27, 0.27)], 6)
    # raízes no lugar do pé: base larga e dedos de raiz abertos
    stack(f"foot.{side}", "bark", [(x1, 0.18, -0.05, 0.3, 0.28), (x1, 0.08, 0.04, 0.42, 0.38), (x1, 0.04, 0.2, 0.42, 0.38)], 6)
    for dx, dz in ((0.3, 0.42), (0, 0.55), (-0.3, 0.42)):
        H.frustum(f"foot.{side}", "bark_dk", (x1, 0.07, 0.1), (x1 + dx, 0.03, dz), (0.13, 0.07), (0.06, 0.03), sides=4)


def claws(s, side, gx):
    for i, dx in enumerate((-0.14, -0.04, 0.06, 0.16)):
        d = (s * 0.0 + dx)
        H.frustum(f"forearm.{side}", "bark_dk", (gx + dx * 0.5, 0.62, 0.0), (gx + d * 2.2, 0.28, 0.12 + 0.03 * i), (0.08, 0.08), (0.03, 0.03), sides=4)
    H.frustum(f"forearm.{side}", "bark_dk", (gx + s * 0.1, 0.65, 0.04), (gx - s * 0.1, 0.38, 0.28), (0.08, 0.08), (0.03, 0.03), sides=4)   # polegar


def arm(s, side):
    px, ex, gx = s * SH_X, s * EL_X, s * WR_X
    stack(f"arm.{side}", "bark", [(px, 2.08, 0, 0.3, 0.3), (s * 0.9, 1.75, 0, 0.26, 0.26), (ex, EL_Y + 0.05, 0, 0.21, 0.22)], 6)
    # musgo caindo do ombro
    stack(f"arm.{side}", "moss", [(px + s * 0.02, 1.88, 0, 0.3, 0.3), (px, 2.12, 0, 0.36, 0.34), (px - s * 0.04, 2.34, 0, 0.2, 0.2)], 6)
    H.frustum(f"arm.{side}", "moss_dk", (px + s * 0.05, 1.7, 0), (px + s * 0.05, 1.9, 0), (0.08, 0.14), (0.2, 0.26), sides=4)
    stack(f"forearm.{side}", "bark", [(ex, EL_Y + 0.02, 0, 0.21, 0.22), (gx, 1.1, 0, 0.29, 0.27), (gx, WR_Y, 0, 0.24, 0.22)], 6)
    stack(f"forearm.{side}", "bark_lt", [(gx, WR_Y + 0.02, 0, 0.24, 0.22), (gx, 0.7, 0.02, 0.3, 0.16), (gx, 0.52, 0.04, 0.24, 0.1)], 6)
    claws(s, side, gx)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        arm(s, side)


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * WR_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * KNEE_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * KNEE_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * KNEE_X, ANKLE, 0), (s * KNEE_X, 0.06, 0.5))
    return out


H.build("e00D", "biped", PALETTE, make, joints())
