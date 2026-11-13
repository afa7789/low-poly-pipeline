"""Sagepaw Monk (n03E): medido em artifacts/model-sheets/refs/n03E/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n03E.py -- <out.glb>
"""
import pathlib
import sys

from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "cream": 0xEEE4CC, "patch": 0x1C1B20, "ear": 0x1C1B20, "nose": 0x1C1B20, "whisker": 0xF4F4F0,
    "hat": 0xA67F36, "hat_dk": 0x8A6A2C, "robe": 0x58585E, "robe_dk": 0x4A4A50, "red": 0xB32424,
    "gold": 0xA67F36, "belt": 0x1A1A1E, "glove": 0x7C7E88, "boot": 0x1A1A1E, "sock": 0xF2F2F0,
    "staff": 0xC02626, "disc": 0x4A4448, "disc_dk": 0x38333A,
}

HIP, KNEE, ANKLE, LEG_X = 1.05, 0.55, 0.17, 0.29
WAIST, NECK, TOP = 1.36, 2.0, 2.72
HAND_Y = 1.3
BOT, TIP = Vector((0.74, 0.0, -0.15)), Vector((0.74, 2.3, 0.8))


def head():
    H.frustum("head", "cream", (0, 2.02, 0.0), (0, 2.2, 0.02), (0.3, 0.3), (0.34, 0.34), sides=8)
    H.frustum("head", "cream", (0, 2.2, 0.02), (0, 2.42, 0.02), (0.34, 0.34), (0.32, 0.32), sides=8)
    H.frustum("head", "cream", (0, 2.18, 0.2), (0, 2.18, 0.42), (0.15, 0.12), (0.1, 0.08), sides=6)      # focinho
    H.box("head", "nose", (0, 2.24, 0.44), (0.1, 0.07, 0.05))
    for s in (-1, 1):
        H.box("head", "patch", (s * 0.13, 2.32, 0.27), (0.14, 0.11, 0.07))
        H.frustum("head", "whisker", (s * 0.08, 2.14, 0.44), (s * 0.1, 1.62, 0.46), (0.03, 0.025), (0.015, 0.012), sides=4)
        H.frustum("head", "ear", (s * 0.34, 2.54, 0.0), (s * 0.4, 2.74, 0.0), (0.13, 0.1), (0.1, 0.08), sides=6)
    H.frustum("head", "hat_dk", (0, 2.36, 0.0), (0, 2.42, 0.0), (0.56, 0.6), (0.54, 0.58), sides=8)          # aba
    H.frustum("head", "hat", (0, 2.42, 0.0), (0, 2.62, 0.0), (0.54, 0.58), (0.26, 0.28), sides=8)
    H.frustum("head", "ear", (0, 2.6, 0.0), (0, 2.72, 0.0), (0.08, 0.07), (0.05, 0.05), sides=6)


def torso():
    H.frustum("pelvis", "robe", (0, 0.95, 0), (0, WAIST, 0), (0.46, 0.42), (0.4, 0.36), sides=8)
    H.frustum("pelvis", "belt", (0, WAIST - 0.14, 0), (0, WAIST + 0.04, 0), (0.4, 0.34), (0.39, 0.33), sides=8)
    H.box("pelvis", "gold", (0, WAIST - 0.05, 0.34), (0.16, 0.14, 0.04))
    H.frustum("spine", "robe", (0, WAIST, 0), (0, 1.85, 0), (0.4, 0.36), (0.46, 0.38), sides=8)
    H.frustum("spine", "red", (0, 1.8, 0), (0, 2.0, 0), (0.62, 0.44), (0.5, 0.38), sides=8)           # capa vermelha
    H.frustum("spine", "red", (0, 2.0, 0), (0, 2.14, 0), (0.5, 0.38), (0.3, 0.28), sides=8)
    H.frustum("spine", "belt", (0, 2.0, 0.2), (0, 1.8, 0.3), (0.08, 0.02), (0.16, 0.02), sides=4)      # peito escuro


def legs(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "robe_dk", (x, KNEE - 0.04, 0), (x, HIP + 0.04, 0), (0.3, 0.33), (0.34, 0.38), sides=6)
    H.frustum(f"shin.{side}", "robe_dk", (x, 0.34, 0), (x, KNEE + 0.04, 0), (0.35, 0.36), (0.3, 0.34), sides=6)
    H.frustum(f"shin.{side}", "gold", (x, 0.2, 0), (x, 0.34, 0), (0.37, 0.37), (0.35, 0.36), sides=6)        # barra
    H.frustum(f"shin.{side}", "sock", (x, 0.14, 0), (x, 0.22, 0), (0.12, 0.12), (0.12, 0.12), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.03, -0.02), (x, 0.17, -0.02), (0.18, 0.2), (0.17, 0.19), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.11, 0.05), (x, 0.09, 0.44), (0.19, 0.12), (0.17, 0.09), sides=4)


def arm_left():
    H.frustum("arm.L", "robe", (0.5, 1.92, 0), (0.68, 1.42, 0.04), (0.24, 0.26), (0.26, 0.27), sides=6)
    H.frustum("arm.L", "gold", (0.7, 1.46, 0.04), (0.72, 1.3, 0.08), (0.27, 0.27), (0.27, 0.27), sides=6)
    H.frustum("forearm.L", "robe", (0.72, 1.4, 0.06), (0.72, 1.22, 0.2), (0.25, 0.26), (0.22, 0.22), sides=6)
    H.frustum("forearm.L", "glove", (0.72, 1.3, 0.16), (0.74, 1.18, 0.36), (0.2, 0.2), (0.24, 0.24), sides=6)   # punho no cabo


def arm_right():
    H.frustum("arm.R", "robe", (-0.5, 1.92, 0), (-0.72, 1.3, 0.0), (0.24, 0.26), (0.27, 0.28), sides=6)
    H.frustum("forearm.R", "robe", (-0.74, 1.3, 0), (-0.8, 1.05, 0.02), (0.28, 0.28), (0.24, 0.24), sides=6)
    H.frustum("forearm.R", "gold", (-0.78, 1.14, 0.02), (-0.8, 1.02, 0.03), (0.27, 0.27), (0.27, 0.27), sides=6)
    H.frustum("forearm.R", "glove", (-0.8, 1.02, 0.03), (-0.82, 0.8, 0.06), (0.2, 0.2), (0.24, 0.22), sides=6)  # pata grande
    H.frustum("forearm.R", "glove", (-0.82, 0.8, 0.06), (-0.82, 0.66, 0.08), (0.24, 0.22), (0.15, 0.14), sides=6)


def staff():
    b = "forearm.L"
    H.frustum(b, "staff", BOT, TIP, (0.065, 0.065), (0.065, 0.065), sides=6)
    d = (TIP - BOT).normalized() * 0.09
    H.frustum(b, "disc", TIP - d, TIP + d, (0.3, 0.3), (0.3, 0.3), sides=8)
    H.frustum(b, "disc_dk", TIP + d, TIP + d * 1.7, (0.2, 0.2), (0.12, 0.12), sides=8)
    H.frustum(b, "staff", TIP + d * 1.7, TIP + d * 2.4, (0.07, 0.07), (0.05, 0.05), sides=6)


def make():
    head()
    torso()
    arm_left()
    arm_right()
    for s, side in ((1, "L"), (-1, "R")):
        legs(s, side)
    staff()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0)),
           "arm.L": ((0.6, 1.95, 0), (0.7, 1.42, 0.04)), "forearm.L": ((0.7, 1.42, 0.04), (0.74, 0.98, 0.34)),
           "arm.R": ((-0.6, 1.95, 0), (-0.74, 1.3, 0)), "forearm.R": ((-0.74, 1.3, 0), (-0.82, 0.74, 0.07))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, -0.02), (s * LEG_X, 0.06, 0.45))
    return out


H.build("n03E", "biped", PALETTE, make, joints())
