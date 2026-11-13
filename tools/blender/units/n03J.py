"""Ironpaw Guardian (n03J): medido em artifacts/model-sheets/refs/n03J/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n03J.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "fur": 0xDDE1EC, "fur_dk": 0xC3C8D6, "patch": 0x3C4458, "ear": 0x4A5368, "navy": 0x4A5368, "navy_dk": 0x3A4256,
    "maroon": 0x6B3026, "brass": 0xC9A03A, "pauld": 0xA07848, "rim": 0x6B6560, "glove": 0x4E453F, "glove_lt": 0x5E534B,
    "boot": 0x2B2523, "sole": 0x1B1818, "pole": 0x8A8085, "pole_dk": 0x6A6065, "cream": 0xE7D2A0, "red": 0xB85C3E,
    "black": 0x17161A, "nose": 0x2A2A30, "eye": 0xF2F2F2,
}

HIP, WAIST, NECK, TOP = 0.85, 1.4, 2.12, 2.72
KNEE, ANKLE, LEG_X = 0.55, 0.17, 0.39
POLE_X, POLE_Z = -0.93, 0.3


def head():
    H.frustum("head", "fur", (0, 2.0, 0.0), (0, 2.28, 0.02), (0.36, 0.32), (0.3, 0.28), sides=8)        # pescoço grosso
    H.frustum("head", "fur", (0, 2.2, 0.0), (0, 2.46, 0.0), (0.27, 0.27), (0.3, 0.29), sides=8)         # crânio
    H.frustum("head", "fur", (0, 2.46, 0.0), (0, 2.66, 0.0), (0.3, 0.29), (0.2, 0.2), sides=8)
    H.frustum("head", "fur_dk", (0, 2.32, 0.1), (0, 2.28, 0.4), (0.15, 0.12), (0.1, 0.08), sides=6)     # focinho
    H.box("head", "nose", (0, 2.33, 0.41), (0.1, 0.07, 0.05))
    for s in (-1, 1):
        H.frustum("head", "ear", (s * 0.22, 2.6, -0.02), (s * 0.27, 2.74, -0.02), (0.1, 0.07), (0.08, 0.06), sides=6)
        H.frustum("head", "patch", (s * 0.12, 2.5, 0.2), (s * 0.12, 2.38, 0.24), (0.1, 0.05), (0.075, 0.04), sides=4)
        H.box("head", "eye", (s * 0.1, 2.46, 0.26), (0.05, 0.025, 0.03))


def torso():
    H.frustum("pelvis", "navy", (0, 0.8, 0.0), (0, WAIST, 0.04), (0.5, 0.45), (0.58, 0.55), sides=8)     # barriga
    H.frustum("spine", "navy", (0, WAIST, 0.02), (0, 1.9, 0.0), (0.58, 0.52), (0.62, 0.46), sides=8)
    H.frustum("spine", "navy", (0, 1.9, 0.0), (0, 2.18, 0.0), (0.62, 0.46), (0.34, 0.3), sides=8)       # ombros em V
    H.frustum("spine", "maroon", (0, 2.14, 0.4), (0, 1.5, 0.52), (0.28, 0.08), (0.5, 0.09), sides=4)    # avental
    H.frustum("pelvis", "maroon", (0, 1.5, 0.52), (0, 0.62, 0.42), (0.5, 0.09), (0.54, 0.08), sides=4)
    H.frustum("pelvis", "brass", (0, 1.0, 0.54), (0, 0.98, 0.44), (0.17, 0.01), (0.17, 0.01), sides=4)
    for x in (-0.33, 0, 0.33):
        H.frustum("pelvis", "brass", (x, 0.8, 0.45), (x, 0.8, 0.52), (0.11, 0.11), (0.1, 0.1), sides=8)
    H.frustum("spine", "brass", (0.03, 1.55, 0.6), (0.03, 1.78, 0.6), (0.08, 0.08), (0.13, 0.12), sides=6)   # cantil
    H.frustum("spine", "brass", (0.03, 1.78, 0.6), (0.03, 1.92, 0.6), (0.13, 0.12), (0.06, 0.06), sides=6)
    H.frustum("pelvis", "cream", (0, 1.1, 0), (0, 1.24, 0), (0.6, 0.58), (0.6, 0.58), sides=8)         # cinto
    H.frustum("spine", "red", (0, 1.28, -0.58), (0, 2.02, -0.58), (0.5, 0.08), (0.5, 0.08), sides=4)   # mochila
    H.frustum("spine", "cream", (0, 1.32, -0.66), (0, 1.98, -0.66), (0.43, 0.05), (0.43, 0.05), sides=4)


def legs(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "navy_dk", (x, KNEE - 0.04, 0), (x, HIP + 0.08, 0), (0.22, 0.24), (0.3, 0.3), sides=6)
    H.frustum(f"shin.{side}", "navy_dk", (x, 0.4, -0.02), (x, KNEE + 0.04, -0.02), (0.2, 0.21), (0.23, 0.24), sides=6)
    H.frustum(f"shin.{side}", "boot", (x, 0.03, -0.06), (x, 0.4, -0.04), (0.22, 0.24), (0.27, 0.28), sides=6)
    H.frustum(f"shin.{side}", "boot", (x, 0.4, -0.04), (x, 0.58, -0.04), (0.27, 0.28), (0.3, 0.3), sides=6)  # cano alargado
    H.frustum(f"foot.{side}", "boot", (x, 0.11, 0.02), (x, 0.09, 0.3), (0.26, 0.14), (0.22, 0.09), sides=4)
    H.frustum(f"foot.{side}", "sole", (x, 0.02, -0.34), (x, 0.02, 0.32), (0.26, 0.02), (0.23, 0.02), sides=4)


def pauldron(s, side):
    bone = f"arm.{side}"
    H.frustum(bone, "navy", (s * 0.4, 2.12, 0), (s * 0.58, 2.02, 0), (0.3, 0.3), (0.3, 0.3), sides=8)
    H.frustum(bone, "rim", (s * 0.5, 2.2, 0), (s * 0.72, 2.04, 0), (0.34, 0.34), (0.32, 0.32), sides=8)
    H.frustum(bone, "pauld", (s * 0.7, 2.06, 0), (s * 0.84, 1.96, 0), (0.29, 0.29), (0.2, 0.2), sides=8)


def arm_left():
    H.frustum("arm.L", "navy", (0.62, 2.04, 0), (0.8, 1.7, 0.02), (0.22, 0.25), (0.26, 0.27), sides=6)
    H.frustum("arm.L", "navy", (0.8, 1.7, 0.02), (0.86, 1.5, 0.03), (0.26, 0.27), (0.22, 0.23), sides=6)
    H.frustum("forearm.L", "navy_dk", (0.86, 1.52, 0.03), (0.86, 1.2, 0.05), (0.2, 0.22), (0.21, 0.23), sides=6)
    H.frustum("forearm.L", "glove", (0.86, 1.3, 0.05), (0.86, 1.0, 0.07), (0.2, 0.22), (0.27, 0.27), sides=6)   # manopla
    H.frustum("forearm.L", "glove_lt", (0.86, 1.0, 0.07), (0.86, 0.78, 0.1), (0.27, 0.27), (0.2, 0.2), sides=6)  # punho


def arm_right():
    H.frustum("arm.R", "navy", (-0.62, 2.04, 0), (-0.8, 1.78, 0.04), (0.22, 0.25), (0.26, 0.27), sides=6)
    H.frustum("arm.R", "navy", (-0.8, 1.78, 0.04), (-0.84, 1.62, 0.1), (0.26, 0.27), (0.23, 0.24), sides=6)
    H.frustum("forearm.R", "glove", (-0.86, 1.72, 0.14), (-0.92, 1.5, 0.3), (0.22, 0.23), (0.28, 0.28), sides=6)
    H.frustum("forearm.R", "glove_lt", (-0.92, 1.52, 0.3), (-0.92, 1.26, 0.3), (0.28, 0.28), (0.22, 0.22), sides=6)


def pole():
    b = "forearm.R"
    H.frustum(b, "pole", (POLE_X, 0.0, POLE_Z), (POLE_X, 2.86, POLE_Z), (0.055, 0.055), (0.05, 0.05), sides=6)
    H.frustum(b, "pole_dk", (POLE_X, 2.42, POLE_Z), (POLE_X, 2.66, POLE_Z), (0.1, 0.1), (0.1, 0.1), sides=6)   # luva do cabo
    H.frustum(b, "pole_dk", (POLE_X, 2.78, POLE_Z), (POLE_X, 2.84, POLE_Z), (0.14, 0.14), (0.2, 0.2), sides=8)
    H.frustum(b, "pole", (POLE_X, 2.82, POLE_Z), (POLE_X, 2.9, POLE_Z), (0.4, 0.4), (0.4, 0.4), sides=8)      # cabeça do pilão
    H.frustum(b, "pole_dk", (POLE_X, 2.9, POLE_Z), (POLE_X, 2.97, POLE_Z), (0.4, 0.4), (0.34, 0.34), sides=8)


def make():
    head()
    torso()
    pauldron(1, "L")
    pauldron(-1, "R")
    arm_left()
    arm_right()
    for s, side in ((1, "L"), (-1, "R")):
        legs(s, side)
    pole()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0)),
           "arm.L": ((0.68, 2.02, 0), (0.86, 1.52, 0.03)), "forearm.L": ((0.86, 1.52, 0.03), (0.86, 0.9, 0.08)),
           "arm.R": ((-0.68, 2.02, 0), (-0.84, 1.66, 0.1)), "forearm.R": ((-0.84, 1.66, 0.1), (-0.92, 1.3, 0.3))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, -0.04), (s * LEG_X, 0.06, 0.4))
    return out


H.build("n03J", "biped", PALETTE, make, joints())
