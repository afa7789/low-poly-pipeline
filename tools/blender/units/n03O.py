"""Drunken Brewmaster (n03O): medido em artifacts/model-sheets/refs/n03O/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n03O.py -- <out.glb>
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "fur": 0x7A3F28, "fur_dk": 0x3E2420, "white": 0xF2EEEA, "white_dk": 0xD8D2CC, "tan": 0xD4B070, "tan_dk": 0xA88850,
    "can": 0x3FA07A, "can_dk": 0x2C7A5C, "hose": 0x1C1A1E, "patch": 0x6F7A48, "eye": 0x7FC4D4, "nose": 0x4A2A20,
    "tip": 0x2E2E34,
}

HIP, WAIST, NECK, TOP = 0.75, 1.3, 2.0, 2.72
KNEE, ANKLE, LEG_X = 0.4, 0.1, 0.31
ARM_X = 0.82
RING = 0.62


def head():
    H.frustum("head", "white", (0, 2.02, 0.1), (0, 2.3, 0.12), (0.3, 0.28), (0.3, 0.28), sides=8)
    H.frustum("head", "white", (0, 2.3, 0.12), (0, 2.44, 0.1), (0.3, 0.28), (0.22, 0.2), sides=8)
    H.frustum("head", "white_dk", (0, 2.15, 0.3), (0, 2.12, 0.46), (0.14, 0.11), (0.09, 0.07), sides=6)      # focinho
    H.box("head", "nose", (0, 2.17, 0.47), (0.09, 0.07, 0.05))
    for s in (-1, 1):
        H.box("head", "patch", (s * 0.13, 2.27, 0.38), (0.14, 0.1, 0.06))
        H.box("head", "eye", (s * 0.12, 2.27, 0.42), (0.07, 0.025, 0.02))
        H.frustum("head", "fur", (s * 0.34, 2.36, 0.04), (s * 0.4, 2.46, 0.04), (0.1, 0.07), (0.08, 0.06), sides=6)
    H.frustum("head", "tan_dk", (0, 2.27, 0.0), (0, 2.34, 0.0), (0.5, 0.5), (0.48, 0.48), sides=8)         # chapéu
    H.frustum("head", "tan", (0, 2.34, 0.0), (0, 2.66, 0.0), (0.48, 0.48), (0.05, 0.05), sides=8)
    H.frustum("head", "tip", (0, 2.6, 0.0), (0, 2.73, 0.0), (0.08, 0.08), (0.01, 0.01), sides=6)


def torso():
    H.frustum("pelvis", "fur", (0, 0.66, 0), (0, WAIST, 0), (0.5, 0.46), (0.62, 0.55), sides=8)
    H.frustum("pelvis", "white", (0, 0.86, 0.14), (0, 1.5, 0.14), (0.5, 0.48), (0.46, 0.45), sides=8)      # barriga branca
    H.frustum("spine", "fur", (0, WAIST, 0), (0, 1.85, 0.0), (0.62, 0.55), (0.68, 0.5), sides=8)
    H.frustum("spine", "fur", (0, 1.85, 0.0), (0, 2.08, 0.02), (0.68, 0.5), (0.4, 0.36), sides=8)       # ombros
    H.frustum("pelvis", "hose", (0, 0.84, 0), (0, 0.94, 0), (RING + 0.02, RING - 0.02), (RING + 0.02, RING - 0.02), sides=8)  # cinto


def kegs():
    for deg in (-62, -31, 0, 31, 62, 105, -105, 145, -145):
        a = math.radians(deg)
        x, z = RING * math.sin(a) * 0.95, RING * math.cos(a)
        H.frustum("pelvis", "tan", (x, 0.64, z), (x, 0.94, z), (0.12, 0.12), (0.15, 0.15), sides=6)
        H.frustum("pelvis", "tan_dk", (x, 0.92, z), (x, 0.96, z), (0.1, 0.1), (0.1, 0.1), sides=6)


def backpack():
    z = -0.8
    H.frustum("spine", "tan", (0, 1.14, z), (0, 1.64, z), (0.3, 0.27), (0.35, 0.31), sides=8)
    H.frustum("spine", "tan", (0, 1.64, z), (0, 2.12, z), (0.35, 0.31), (0.3, 0.27), sides=8)
    H.frustum("spine", "hose", (0, 2.12, z), (0, 2.16, z), (0.16, 0.16), (0.14, 0.14), sides=8)
    H.frustum("spine", "hose", (0, 1.7, z + 0.3), (0, 1.9, -0.45), (0.4, 0.05), (0.4, 0.05), sides=4)     # correias
    H.chain(["spine", "spine", "arm.R", "arm.R", "forearm.R"], "hose",
            [(-0.2, 2.14, -0.78), (-0.75, 2.24, -0.4), (-1.12, 1.9, -0.1), (-1.14, 1.3, 0.0), (-1.1, 0.96, 0.05), (-1.02, 0.78, 0.1)],
            [(0.05, 0.05)] * 6, sides=6)


def legs(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "fur", (x, KNEE - 0.04, 0), (x, HIP + 0.1, 0), (0.22, 0.24), (0.3, 0.3), sides=6)
    H.frustum(f"shin.{side}", "fur_dk", (x, 0.1, 0), (x, KNEE + 0.02, 0), (0.2, 0.21), (0.25, 0.25), sides=6)
    H.frustum(f"foot.{side}", "fur_dk", (x, 0.1, -0.03), (x, 0.08, 0.32), (0.24, 0.17), (0.21, 0.1), sides=6)
    H.frustum(f"foot.{side}", "fur_dk", (x, 0.04, -0.16), (x, 0.04, 0.34), (0.23, 0.04), (0.2, 0.04), sides=4)


def arm(s, side):
    x = s * ARM_X
    H.frustum(f"arm.{side}", "fur", (s * 0.66, 2.0, 0), (x, 1.62, 0.0), (0.24, 0.26), (0.28, 0.28), sides=6)
    H.frustum(f"arm.{side}", "fur", (x, 1.62, 0.0), (x + s * 0.02, 1.32, 0.02), (0.28, 0.28), (0.23, 0.23), sides=6)
    H.frustum(f"forearm.{side}", "fur", (x + s * 0.02, 1.36, 0.02), (x + s * 0.04, 1.0, 0.04), (0.24, 0.24), (0.22, 0.22), sides=6)
    H.frustum(f"forearm.{side}", "fur_dk", (x + s * 0.04, 1.02, 0.04), (x + s * 0.04, 0.82, 0.05), (0.21, 0.22), (0.26, 0.26), sides=6)
    H.frustum(f"forearm.{side}", "fur_dk", (x + s * 0.04, 0.82, 0.05), (x + s * 0.04, 0.5, 0.07), (0.26, 0.26), (0.17, 0.18), sides=6)


def jerrycan():
    b, x = "forearm.R", -0.88
    H.box(b, "can", (x, 0.4, 0.12), (0.5, 0.62, 0.44))
    H.box(b, "can_dk", (x, 0.1, 0.12), (0.5, 0.04, 0.44))
    H.box(b, "can_dk", (x, 0.74, 0.1), (0.12, 0.2, 0.36))                                               # alça no punho
    H.frustum(b, "can", (x, 0.6, 0.3), (x, 0.74, 0.7), (0.06, 0.06), (0.04, 0.04), sides=6)             # bico


def make():
    head()
    torso()
    kegs()
    backpack()
    arm(1, "L")
    arm(-1, "R")
    jerrycan()
    for s, side in ((1, "L"), (-1, "R")):
        legs(s, side)


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * 0.66, 2.0, 0), (s * (ARM_X + 0.02), 1.34, 0.02))
        out[f"forearm.{side}"] = ((s * (ARM_X + 0.02), 1.34, 0.02), (s * (ARM_X + 0.04), 0.6, 0.06))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, -0.04), (s * LEG_X, 0.06, 0.4))
    return out


H.build("n03O", "biped", PALETTE, make, joints())
