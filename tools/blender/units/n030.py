"""Sandkin (n030): homem-grifo, medido em artifacts/model-sheets/refs/n030/sheet.jpg. Sem arma: garras grandes.

    blender -b --factory-startup -P tools/blender/units/n030.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "brown": 0xB86A30, "dark": 0x7A4220, "mid": 0x9A5528, "cream": 0xEFE6CC, "purple": 0x5B3A7E, "beak": 0xE0A83A,
    "horn": 0x7B5A44, "claw": 0x1E1A1A, "collar": 0x5A3320, "foot": 0x7A5A44, "eye": 0xF5F0E0,
}

HIP, KNEE, ANKLE, LEG_X = 0.85, 0.5, 0.14, 0.28
WAIST, NECK, TOP = 1.05, 1.95, 2.75
SH_Y, ARM_X, EL_Y, WR_Y = 1.92, 0.72, 1.3, 0.85


HZ = 0.2      # a cabeça fica à frente do tronco: corcunda


def HF(tone, a, b, ra, rb, sides=8):
    H.frustum("head", tone, (a[0], a[1], a[2] + HZ), (b[0], b[1], b[2] + HZ), ra, rb, sides)


def HC(tone, pts, radii, sides=6):
    H.chain("head", tone, [(p[0], p[1], p[2] + HZ) for p in pts], radii, sides)


def HB(tone, c, size):
    H.box("head", tone, (c[0], c[1], c[2] + HZ), size)


def make_head():
    HF("cream", (0, 1.9, 0.02), (0, 2.15, 0.05), (0.3, 0.28), (0.3, 0.28), sides=8)           # papo
    HF("collar", (0, 1.98, 0.02), (0, 2.06, 0.02), (0.33, 0.31), (0.33, 0.31), sides=8)
    HF("brown", (0, 2.1, 0.08), (0, 2.3, 0.1), (0.3, 0.3), (0.34, 0.31), sides=8)
    HF("brown", (0, 2.3, 0.1), (0, 2.5, 0.06), (0.34, 0.31), (0.26, 0.26), sides=8)
    HF("cream", (0, 2.1, 0.2), (0, 2.3, 0.24), (0.2, 0.12), (0.22, 0.12), sides=6)            # face branca
    HC("beak", [(0, 2.3, 0.3), (0, 2.25, 0.5), (0, 2.1, 0.64)], [(0.15, 0.14), (0.11, 0.11), (0.02, 0.03)], sides=6)
    for s in (-1, 1):
        HB("eye", (s * 0.15, 2.38, 0.3), (0.12, 0.05, 0.04))
        HC("horn", [(s * 0.22, 2.38, 0.02), (s * 0.38, 2.5, 0.02), (s * 0.32, 2.7, 0.06)],
                [(0.1, 0.1), (0.08, 0.08), (0.015, 0.015)], sides=6)
    HC("purple", [(0, 2.42, 0.1), (0, 2.62, -0.05), (0, 2.78, -0.35)], [(0.1, 0.16), (0.12, 0.18), (0.02, 0.02)], sides=6)


def make_torso():
    H.frustum("pelvis", "brown", (0, 0.72, 0), (0, 1.08, 0), (0.46, 0.42), (0.3, 0.38), sides=8)
    H.frustum("spine", "mid", (0, 1.0, 0), (0, 1.5, 0), (0.3, 0.38), (0.46, 0.46), sides=8)
    H.frustum("spine", "mid", (0, 1.5, 0), (0, 2.0, 0), (0.46, 0.46), (0.56, 0.48), sides=8)
    H.frustum("spine", "dark", (0, 1.6, -0.18), (0, 2.05, -0.12), (0.5, 0.4), (0.56, 0.4), sides=8)       # costas / ombros
    H.frustum("spine", "cream", (0, 1.1, 0.3), (0, 1.5, 0.36), (0.2, 0.15), (0.34, 0.15), sides=6)         # peito branco
    H.frustum("spine", "cream", (0, 1.5, 0.36), (0, 1.95, 0.36), (0.34, 0.15), (0.4, 0.14), sides=6)
    H.chain("pelvis", "purple", [(0, 1.0, -0.2), (0, 0.75, -0.42), (0, 0.4, -0.65)], [(0.1, 0.08), (0.16, 0.08), (0.02, 0.02)], sides=6)


def make_arms():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * ARM_X
        H.frustum(f"arm.{side}", "dark", (s * 0.5, 2.06, -0.05), (x, 1.82, 0), (0.22, 0.3), (0.3, 0.33), sides=8)   # ombreira de penas
        H.frustum(f"arm.{side}", "dark", (x, EL_Y - 0.05, 0), (x, 1.85, 0), (0.24, 0.28), (0.29, 0.33), sides=8)
        H.frustum(f"forearm.{side}", "mid", (x, EL_Y + 0.05, 0), (x, 1.0, 0.03), (0.26, 0.28), (0.25, 0.27), sides=8)
        H.frustum(f"forearm.{side}", "brown", (x, 1.05, 0.03), (x, 0.62, 0.06), (0.25, 0.27), (0.21, 0.22), sides=8)
        H.frustum(f"forearm.{side}", "purple", (s * (ARM_X + 0.22), 1.25, -0.04), (s * (ARM_X + 0.22), 0.75, -0.04), (0.05, 0.1), (0.03, 0.08), sides=4)
        for k in (-1, 0, 1):
            cx = x + k * 0.11
            H.frustum(f"forearm.{side}", "claw", (cx, 0.68, 0.08), (cx, 0.34, 0.2), (0.05, 0.05), (0.01, 0.01), sides=4)


def make_legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * LEG_X
        H.frustum(f"thigh.{side}", "brown", (x, KNEE - 0.05, 0), (x, HIP + 0.05, -0.05), (0.2, 0.25), (0.28, 0.33), sides=8)
        H.frustum(f"shin.{side}", "cream", (x, ANKLE, 0), (x, KNEE + 0.04, 0), (0.17, 0.17), (0.2, 0.2), sides=8)
        H.frustum(f"foot.{side}", "foot", (x, 0.1, -0.1), (x, 0.07, 0.42), (0.2, 0.1), (0.2, 0.05), sides=4)
        for k in (-1, 0, 1):
            cx = x + k * 0.1
            H.frustum(f"foot.{side}", "claw", (cx, 0.06, 0.4), (cx, 0.03, 0.62), (0.045, 0.04), (0.01, 0.01), sides=4)


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


H.build("n030", "biped", PALETTE, make, joints())
