"""Ironpaw Militia (n03G): medido em artifacts/model-sheets/refs/n03G/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n03G.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "fur": 0xDDDFE8, "fur_dk": 0xC4C7D2, "patch": 0x50566A, "ear": 0x4A4F5E, "nose": 0x2A2A32, "eye": 0x5CD25C,
    "hat": 0x5C4F47, "hat_rim": 0xC9A978, "vest": 0x6A3328, "cream": 0xE8D8B0, "belly": 0xA85A40,
    "arm": 0x434858, "arm_dk": 0x383D4B, "leg": 0x4F5565, "paw": 0x3F4452, "wood": 0x6B4430, "wood_dk": 0x4F3222,
    "steel": 0x6A6866, "blade": 0xCFD8D6, "barrel": 0x7B6A55, "band": 0x4A3E34, "flask": 0xB0A08A, "cap": 0x5A4A38,
}

HIP, WAIST, NECK, TOP = 0.8, 1.15, 1.9, 2.6
KNEE, ANKLE, LEG_X = 0.42, 0.14, 0.35
GUN_X, GUN_Z = -0.92, 0.27


def head():
    H.frustum("head", "fur", (0, 1.82, 0.0), (0, 2.1, 0.02), (0.34, 0.34), (0.42, 0.4), sides=8)
    H.frustum("head", "fur", (0, 2.1, 0.02), (0, 2.32, 0.0), (0.42, 0.4), (0.34, 0.32), sides=8)
    H.frustum("head", "fur_dk", (0, 1.98, 0.18), (0, 1.96, 0.42), (0.17, 0.12), (0.11, 0.08), sides=6)      # focinho
    H.box("head", "nose", (0, 2.02, 0.43), (0.1, 0.07, 0.05))
    for s in (-1, 1):
        H.box("head", "patch", (s * 0.14, 2.1, 0.3), (0.15, 0.12, 0.07))
        H.box("head", "eye", (s * 0.14, 2.1, 0.345), (0.06, 0.05, 0.02))
        H.frustum("head", "ear", (s * 0.3, 2.4, -0.04), (s * 0.34, 2.62, -0.04), (0.16, 0.12), (0.13, 0.1), sides=6)
    H.frustum("head", "hat_rim", (0, 2.17, 0.0), (0, 2.23, 0.0), (0.76, 0.76), (0.74, 0.74), sides=8)         # chapéu cônico
    H.frustum("head", "hat", (0, 2.22, 0.0), (0, 2.46, 0.0), (0.74, 0.74), (0.3, 0.3), sides=8)
    H.frustum("head", "hat", (0, 2.46, 0.0), (0, 2.56, 0.0), (0.3, 0.3), (0.08, 0.08), sides=8)


def torso():
    H.frustum("pelvis", "belly", (0, 0.46, 0), (0, 0.66, 0), (0.36, 0.38), (0.56, 0.58), sides=8)          # barriga redonda
    H.frustum("pelvis", "belly", (0, 0.66, 0), (0, 0.86, 0), (0.56, 0.58), (0.64, 0.64), sides=8)
    H.frustum("pelvis", "cream", (0, 0.84, 0), (0, 1.14, 0), (0.65, 0.65), (0.62, 0.62), sides=8)         # faixa creme
    H.frustum("spine", "vest", (0, WAIST - 0.03, 0), (0, 1.6, 0), (0.62, 0.62), (0.58, 0.54), sides=8)
    H.frustum("spine", "vest", (0, 1.6, 0), (0, 1.84, 0), (0.58, 0.54), (0.5, 0.42), sides=8)
    H.frustum("spine", "vest", (0, 1.84, 0), (0, 1.98, 0), (0.5, 0.42), (0.3, 0.28), sides=8)             # ombros caídos
    H.frustum("spine", "cream", (0, 1.58, 0), (0, 1.66, 0), (0.59, 0.55), (0.58, 0.54), sides=8)
    H.frustum("spine", "barrel", (0, 1.08, -0.62), (0, 1.5, -0.62), (0.28, 0.17), (0.34, 0.21), sides=8)     # barril
    H.frustum("spine", "barrel", (0, 1.5, -0.62), (0, 1.9, -0.62), (0.34, 0.21), (0.28, 0.17), sides=8)
    for y in (1.28, 1.72):
        H.frustum("spine", "band", (0, y, -0.62), (0, y + 0.06, -0.62), (0.34, 0.22), (0.34, 0.22), sides=8)


def legs(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "leg", (x, KNEE - 0.04, 0), (x, HIP + 0.06, 0), (0.25, 0.26), (0.32, 0.32), sides=6)
    H.frustum(f"shin.{side}", "leg", (x, ANKLE - 0.02, 0), (x, KNEE + 0.04, 0), (0.24, 0.24), (0.27, 0.27), sides=6)
    H.frustum(f"foot.{side}", "paw", (x, 0.04, -0.04), (x, ANKLE + 0.04, -0.04), (0.26, 0.26), (0.24, 0.24), sides=6)
    H.frustum(f"foot.{side}", "paw", (x, 0.12, 0.04), (x, 0.09, 0.46), (0.26, 0.15), (0.22, 0.1), sides=4)


def arm_left():
    H.frustum("arm.L", "arm", (0.46, 1.9, 0), (0.8, 1.5, 0.03), (0.27, 0.3), (0.31, 0.32), sides=6)
    H.frustum("arm.L", "arm", (0.8, 1.5, 0.03), (0.82, 1.36, 0.05), (0.31, 0.32), (0.28, 0.3), sides=6)
    H.frustum("forearm.L", "arm_dk", (0.86, 1.4, 0.05), (0.74, 1.04, 0.1), (0.28, 0.28), (0.29, 0.29), sides=6)
    H.frustum("forearm.L", "arm_dk", (0.74, 1.04, 0.1), (0.62, 0.74, 0.16), (0.3, 0.3), (0.2, 0.2), sides=6)     # punho
    H.frustum("forearm.L", "flask", (0.54, 0.5, 0.24), (0.54, 0.74, 0.24), (0.12, 0.1), (0.22, 0.18), sides=8)    # cantil
    H.frustum("forearm.L", "flask", (0.54, 0.74, 0.24), (0.54, 0.9, 0.24), (0.22, 0.18), (0.08, 0.08), sides=8)
    H.frustum("forearm.L", "cap", (0.54, 0.9, 0.24), (0.54, 0.97, 0.24), (0.08, 0.08), (0.06, 0.06), sides=6)


def arm_right():
    H.frustum("arm.R", "arm", (-0.46, 1.9, 0), (-0.84, 1.58, 0.08), (0.27, 0.3), (0.31, 0.32), sides=6)
    H.frustum("arm.R", "arm", (-0.84, 1.58, 0.08), (-0.9, 1.5, 0.12), (0.31, 0.32), (0.29, 0.3), sides=6)
    H.frustum("forearm.R", "arm_dk", (-0.9, 1.6, 0.1), (-0.92, 1.4, 0.26), (0.28, 0.28), (0.3, 0.3), sides=6)
    H.frustum("forearm.R", "arm_dk", (-0.92, 1.4, 0.26), (-0.92, 1.18, 0.27), (0.31, 0.3), (0.22, 0.2), sides=6)   # punho no fuzil


def rifle():
    b = "forearm.R"
    H.frustum(b, "wood", (GUN_X, 0.0, GUN_Z), (GUN_X, 0.8, GUN_Z), (0.13, 0.17), (0.09, 0.1), sides=4)       # coronha
    H.frustum(b, "wood", (GUN_X, 0.8, GUN_Z), (GUN_X, 2.3, GUN_Z), (0.085, 0.1), (0.07, 0.07), sides=6)
    H.frustum(b, "steel", (GUN_X, 1.0, GUN_Z), (GUN_X, 1.3, GUN_Z), (0.1, 0.11), (0.1, 0.11), sides=6)      # culatra
    H.frustum(b, "wood_dk", (GUN_X, 2.3, GUN_Z), (GUN_X, 2.56, GUN_Z), (0.085, 0.085), (0.075, 0.075), sides=6)  # anel da baioneta
    H.frustum(b, "blade", (GUN_X, 2.56, GUN_Z), (GUN_X, 3.3, GUN_Z), (0.055, 0.04), (0.012, 0.01), sides=4)


def make():
    head()
    torso()
    arm_left()
    arm_right()
    for s, side in ((1, "L"), (-1, "R")):
        legs(s, side)
    rifle()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0)),
           "arm.L": ((0.55, 1.88, 0), (0.86, 1.4, 0.05)), "forearm.L": ((0.86, 1.4, 0.05), (0.62, 0.78, 0.16)),
           "arm.R": ((-0.55, 1.88, 0), (-0.9, 1.6, 0.1)), "forearm.R": ((-0.9, 1.6, 0.1), (-0.92, 1.2, 0.27))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, -0.04), (s * LEG_X, 0.06, 0.46))
    return out


H.build("n03G", "biped", PALETTE, make, joints())
