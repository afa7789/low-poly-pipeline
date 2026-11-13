"""Monstrous Sandkin (n035): grifo-bruto acorrentado, leque de penas, ombreiras de ferro, medido em
artifacts/model-sheets/refs/n035/sheet.jpg. Sem arma: garras grandes. Mesmo corpo do n030, cabeça baixa e à frente.

    blender -b --factory-startup -P tools/blender/units/n035.py -- <out.glb>
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "brown": 0x8E5F3C, "dark": 0x6B4A33, "cream": 0xE9DDBF, "purple": 0x4C3C86, "beak": 0x6B5648, "armor": 0x6A5242,
    "claw": 0x5A4638, "eye": 0xF08A22, "chain": 0x4A3E38, "black": 0x14101A, "fan": 0x94653F, "foot": 0x7A5A44,
}

HIP, KNEE, ANKLE, LEG_X = 0.82, 0.46, 0.14, 0.32
WAIST, NECK, TOP = 1.0, 1.8, 2.8
SH_Y, ARM_X, EL_Y, WR_Y = 1.8, 0.68, 1.15, 0.68
HZ = 0.35      # a cabeça baixa e à frente do tronco


def HF(tone, a, b, ra, rb, sides=8):
    H.frustum("head", tone, (a[0], a[1], a[2] + HZ), (b[0], b[1], b[2] + HZ), ra, rb, sides)


def HC(tone, pts, radii, sides=6):
    H.chain("head", tone, [(p[0], p[1], p[2] + HZ) for p in pts], radii, sides)


def make_fan():
    """Cinco lâminas de penas em leque atrás da cabeça, ponta creme."""
    bx, by, bz = 0.0, 1.95, -0.3
    for deg in (-62, -31, 0, 31, 62):
        a = math.radians(deg)
        d, p = (math.sin(a), math.cos(a)), (math.cos(a), -math.sin(a))

        def pt(dist, half):
            return (bx + d[0] * dist + p[0] * half, by + d[1] * dist + p[1] * half, bz)
        H.panel("head", "fan", [pt(0, -0.06), pt(0, 0.06), pt(0.56, 0.2), pt(0.56, -0.2)], 0.05)
        H.panel("head", "cream", [pt(0.56, -0.2), pt(0.56, 0.2), pt(0.82, 0.24), pt(0.82, -0.24)], 0.05)


def make_head():
    HF("cream", (0, 1.76, 0), (0, 2.0, 0.05), (0.3, 0.28), (0.3, 0.3))
    HF("armor", (0, 1.72, 0), (0, 1.9, 0), (0.42, 0.4), (0.36, 0.34))                                       # gola de ferro
    HF("brown", (0, 1.95, 0.05), (0, 2.12, 0.08), (0.3, 0.3), (0.34, 0.32))
    HF("brown", (0, 2.12, 0.08), (0, 2.38, 0.04), (0.34, 0.32), (0.25, 0.26))
    HC("beak", [(0, 2.12, 0.28), (0, 2.06, 0.42), (0, 1.88, 0.54)], [(0.16, 0.17), (0.13, 0.14), (0.03, 0.04)])
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.17, 2.2, 0.3 + HZ), (0.1, 0.05, 0.05))
    HC("purple", [(0, 2.32, 0.05), (0, 2.55, -0.12), (0, 2.68, -0.45)], [(0.1, 0.16), (0.12, 0.18), (0.02, 0.02)])
    make_fan()


def make_torso():
    H.frustum("pelvis", "brown", (0, 0.7, 0), (0, 1.08, 0), (0.46, 0.4), (0.3, 0.36), sides=8)
    H.frustum("spine", "brown", (0, 1.0, 0), (0, 1.45, 0), (0.32, 0.36), (0.5, 0.45), sides=8)
    H.frustum("spine", "brown", (0, 1.45, 0), (0, 1.85, 0), (0.5, 0.45), (0.58, 0.44), sides=8)
    H.frustum("spine", "cream", (0, 1.0, 0.25), (0, 1.5, 0.34), (0.2, 0.15), (0.34, 0.15), sides=6)
    H.frustum("spine", "cream", (0, 1.5, 0.34), (0, 1.85, 0.36), (0.34, 0.15), (0.38, 0.12), sides=6)
    H.box("spine", "black", (0, 1.6, 0.46), (0.3, 0.22, 0.05))
    H.frustum("spine", "dark", (0, 1.0, -0.1), (0, 1.85, -0.1), (0.4, 0.3), (0.5, 0.28), sides=8)
    H.box("spine", "armor", (0, 1.25, -0.46), (0.5, 0.4, 0.07))
    H.box("spine", "armor", (0, 1.78, -0.42), (0.5, 0.3, 0.07))
    H.frustum("spine", "dark", (0, 1.1, -0.6), (0, 1.32, -0.6), (0.12, 0.12), (0.28, 0.25), sides=8)       # saco nas costas
    H.frustum("spine", "dark", (0, 1.32, -0.6), (0, 1.52, -0.6), (0.28, 0.25), (0.2, 0.2), sides=8)
    H.chain("pelvis", "purple", [(0, 1.0, 0.1), (0, 0.8, 0.2), (0, 0.45, 0.28)], [(0.1, 0.06), (0.15, 0.06), (0.02, 0.02)], sides=6)


def make_arms():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * ARM_X
        H.frustum(f"arm.{side}", "armor", (s * 0.5, 2.05, -0.02), (s * 0.78, 1.6, -0.02), (0.22, 0.33), (0.3, 0.36), sides=6)   # ombreira
        H.frustum(f"arm.{side}", "brown", (x, EL_Y - 0.05, 0), (x, 1.85, 0), (0.25, 0.28), (0.3, 0.33), sides=8)
        H.frustum(f"arm.{side}", "purple", (s * (ARM_X + 0.24), 1.7, -0.08), (s * (ARM_X + 0.24), 0.9, -0.08), (0.05, 0.16), (0.04, 0.1), sides=4)
        H.frustum(f"forearm.{side}", "brown", (x, EL_Y + 0.05, 0), (x, 0.85, 0.03), (0.28, 0.28), (0.26, 0.27), sides=8)
        H.frustum(f"forearm.{side}", "armor", (x, 0.88, 0.03), (x, 0.74, 0.03), (0.28, 0.28), (0.28, 0.28), sides=8)  # algema
        H.frustum(f"forearm.{side}", "brown", (x, 0.76, 0.03), (x, 0.4, 0.08), (0.26, 0.27), (0.22, 0.22), sides=8)
        for k in (-1, 0, 1):
            cx = x + k * 0.11
            H.frustum(f"forearm.{side}", "claw", (cx, 0.44, 0.1), (cx, 0.12, 0.24), (0.055, 0.05), (0.01, 0.01), sides=4)
    H.chain("forearm.R", "chain", [(-ARM_X - 0.05, 0.78, 0.26), (-ARM_X - 0.05, 0.4, 0.3), (-ARM_X - 0.05, 0.05, 0.3)],
            [(0.05, 0.03), (0.05, 0.03), (0.05, 0.03)], sides=4)


def make_legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * LEG_X
        H.frustum(f"thigh.{side}", "brown", (x, KNEE - 0.05, 0), (x, HIP + 0.05, -0.05), (0.22, 0.26), (0.3, 0.34), sides=8)
        H.frustum(f"shin.{side}", "cream", (x, ANKLE, 0), (x, KNEE + 0.04, 0), (0.18, 0.18), (0.22, 0.21), sides=8)
        H.frustum(f"foot.{side}", "foot", (x, 0.1, -0.1), (x, 0.07, 0.34), (0.2, 0.1), (0.21, 0.05), sides=4)
        for k in (-1, 0, 1):
            cx = x + k * 0.1
            H.frustum(f"foot.{side}", "claw", (cx, 0.06, 0.32), (cx, 0.03, 0.5), (0.045, 0.04), (0.01, 0.01), sides=4)


def make():
    make_head()
    make_torso()
    make_arms()
    make_legs()


def joints():
    out = {"pelvis": ((0, HIP - 0.05, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * ARM_X, SH_Y, 0), (s * ARM_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * ARM_X, EL_Y, 0), (s * ARM_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("n035", "biped", PALETTE, make, joints())
