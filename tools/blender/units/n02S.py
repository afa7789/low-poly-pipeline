"""Gnoll (n02S): medido em artifacts/model-sheets/refs/n02S/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n02S.py -- <out.glb>

Hiena magra e curvada, cabeca bem a frente do tronco, botas pretas digitigradas. Pa nas duas maos (cabo na
antebraco direito, que a prancha mostra mais baixo), besta com bomba-pavio nas costas (bone spine).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "fur": 0xA89070, "fur_dk": 0x8E7858, "muzzle": 0xD2BE98, "black": 0x1E1C1E, "steel": 0x808088, "steel_dk": 0x5C5C64,
    "wood": 0x6A4A32, "bomb": 0x222226, "flame": 0xFF7A30, "mane": 0x4A3A2A, "rope": 0xD8C8A0, "string": 0xD8D8D8,
}

HIP, KNEE, ANKLE, LEG_X = 1.1, 0.62, 0.2, 0.28
WAIST, NECK, TOP = 1.3, 1.95, 2.5
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.55, 2.0, 0.7, 1.43, 0.95
HEAD_Z = 0.55


def head():
    z = HEAD_Z
    H.frustum("head", "fur", (0, 1.98, z - 0.05), (0, 2.2, z - 0.02), (0.18, 0.2), (0.24, 0.23), sides=8)
    H.frustum("head", "muzzle", (0, 2.2, z - 0.02), (0, 2.38, z - 0.05), (0.24, 0.23), (0.19, 0.2), sides=8)
    H.frustum("head", "muzzle", (0, 2.17, z + 0.1), (0, 2.08, z + 0.42), (0.16, 0.16), (0.09, 0.08), sides=6)      # focinho
    H.box("head", "black", (0, 2.07, z + 0.45), (0.1, 0.07, 0.07))
    H.frustum("head", "fur_dk", (0, 2.0, z + 0.1), (0, 1.94, z + 0.4), (0.1, 0.05), (0.07, 0.04), sides=4)       # mandibula
    H.box("head", "flame", (-0.08, 2.34, z + 0.17), (0.06, 0.07, 0.04))
    for s in (-1, 1):
        H.frustum("head", "fur", (s * 0.19, 2.3, z - 0.12), (s * 0.27, 2.55, z - 0.14), (0.11, 0.05), (0.07, 0.03), sides=6)
        H.frustum("head", "fur_dk", (s * 0.19, 2.34, z - 0.1), (s * 0.24, 2.5, z - 0.12), (0.07, 0.03), (0.04, 0.02), sides=4)
    H.frustum("head", "mane", (0, 2.3, z - 0.15), (0, 2.58, z - 0.2), (0.04, 0.12), (0.01, 0.05), sides=4)


def torso():
    H.frustum("pelvis", "fur", (0, 0.95, -0.05), (0, 1.32, -0.05), (0.32, 0.26), (0.3, 0.24), sides=8)
    H.frustum("spine", "fur", (0, 1.3, -0.07), (0, 1.75, -0.04), (0.34, 0.27), (0.42, 0.3), sides=8)
    H.frustum("spine", "fur", (0, 1.75, -0.04), (0, 2.02, 0.0), (0.42, 0.3), (0.58, 0.34), sides=8)
    H.frustum("spine", "fur_dk", (0, 2.0, 0.0), (0, 2.14, 0.0), (0.58, 0.34), (0.34, 0.24), sides=8)
    H.chain("spine", "fur", [(0, 1.95, 0.0), (0, 2.02, 0.25), (0, 2.1, 0.5)], [(0.2, 0.2), (0.17, 0.17), (0.16, 0.16)], sides=6)  # pescoco
    H.frustum("spine", "mane", (0, 1.45, -0.3), (0, 2.12, -0.2), (0.04, 0.1), (0.05, 0.14), sides=4)        # crina
    H.frustum("pelvis", "rope", (0, 1.16, -0.05), (0, 1.3, -0.05), (0.35, 0.28), (0.34, 0.27), sides=8)
    H.frustum("pelvis", "rope", (0.1, 1.2, 0.26), (0.12, 0.98, 0.28), (0.04, 0.03), (0.03, 0.02), sides=4)


def crossbow():
    bx = (0.78, 2.45, -0.28)
    H.frustum("spine", "wood", (0.32, 1.85, -0.18), (0.55, 2.15, -0.23), (0.05, 0.05), (0.06, 0.06), sides=4)
    H.frustum("spine", "steel", (0.55, 2.15, -0.23), (0.74, 2.4, -0.27), (0.06, 0.06), (0.07, 0.07), sides=4)
    H.frustum("spine", "bomb", (0.78, 2.3, -0.28), (0.78, 2.46, -0.28), (0.09, 0.09), (0.14, 0.14), sides=8)
    H.frustum("spine", "bomb", (0.78, 2.46, -0.28), (0.78, 2.62, -0.28), (0.14, 0.14), (0.09, 0.09), sides=8)
    H.frustum("spine", "flame", (bx[0], 2.62, bx[2]), (bx[0] + 0.03, 2.8, bx[2]), (0.06, 0.06), (0.0, 0.0), sides=4)
    H.chain("spine", "steel_dk", [(0.35, 2.4, -0.2), (0.7, 2.37, -0.22), (1.0, 1.8, -0.2)], [(0.03, 0.03), (0.05, 0.05), (0.03, 0.03)], sides=4)
    H.frustum("spine", "string", (0.35, 2.4, -0.2), (1.0, 1.8, -0.2), (0.012, 0.012), (0.012, 0.012), sides=4)


def shovel():
    top, foot = (0.3, 1.88, 0.28), (-0.62, 0.9, 0.2)
    H.frustum("forearm.R", "wood", foot, top, (0.055, 0.055), (0.06, 0.06), sides=4)
    H.frustum("forearm.R", "steel_dk", foot, (-0.72, 0.78, 0.2), (0.06, 0.06), (0.06, 0.06), sides=4)
    H.frustum("forearm.R", "steel", (-0.72, 0.8, 0.22), (-0.8, 0.64, 0.22), (0.2, 0.04), (0.34, 0.04), sides=4)    # lamina
    H.frustum("forearm.R", "steel", (-0.8, 0.66, 0.22), (-0.9, 0.45, 0.22), (0.34, 0.04), (0.04, 0.03), sides=4)


def arm(s, side):
    a, f = f"arm.{side}", f"forearm.{side}"
    H.frustum(a, "fur", (s * 0.52, 1.9, 0), (s * 0.58, 2.1, 0), (0.17, 0.17), (0.15, 0.15), sides=8)
    H.frustum(a, "fur", (s * SH_X, 2.0, 0), (s * EL_X, EL_Y, 0), (0.18, 0.18), (0.12, 0.12), sides=6)
    wrist = (-0.35, 1.17, 0.26) if s < 0 else (0.28, 1.84, 0.3)
    H.frustum(f, "fur", (s * EL_X, EL_Y, 0), (wrist[0] - s * 0.05, wrist[1], wrist[2] - 0.02), (0.1, 0.1), (0.13, 0.11), sides=6)
    H.frustum(f, "fur_dk", (wrist[0] - s * 0.05, wrist[1] - 0.12, wrist[2] - 0.02), (wrist[0] + s * 0.02, wrist[1] + 0.1, wrist[2] + 0.04),
              (0.15, 0.14), (0.12, 0.1), sides=6)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * LEG_X
        H.frustum(f"thigh.{side}", "fur", (s * 0.33, KNEE - 0.03, 0), (x, HIP + 0.04, -0.03), (0.16, 0.17), (0.24, 0.24), sides=6)
        H.frustum(f"shin.{side}", "black", (x, ANKLE, -0.03), (s * 0.33, KNEE + 0.05, 0), (0.12, 0.12), (0.18, 0.18), sides=6)
        H.frustum(f"shin.{side}", "black", (x, 0.3, -0.04), (s * 0.31, 0.45, -0.02), (0.17, 0.17), (0.12, 0.12), sides=6)    # barriga da perna
        H.frustum(f"foot.{side}", "black", (x, 0.04, -0.12), (x, 0.2, -0.05), (0.16, 0.16), (0.12, 0.12), sides=6)
        H.frustum(f"foot.{side}", "black", (x, 0.1, -0.02), (x, 0.07, 0.44), (0.17, 0.12), (0.2, 0.06), sides=6)


def make():
    head()
    torso()
    crossbow()
    shovel()
    legs()
    for s, side in ((1, "L"), (-1, "R")):
        arm(s, side)


def joints():
    out = {"pelvis": ((0, HIP, -0.05), (0, WAIST, -0.05)), "spine": ((0, WAIST, -0.05), (0, NECK, 0.0)),
           "head": ((0, NECK, HEAD_Z), (0, TOP, HEAD_Z))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, -0.03), (s * 0.33, KNEE, 0))
        out[f"shin.{side}"] = ((s * 0.33, KNEE, 0), (s * LEG_X, ANKLE, -0.03))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, -0.03), (s * LEG_X, 0.06, 0.45))
    return out


H.build("n02S", "biped", PALETTE, make, joints())
