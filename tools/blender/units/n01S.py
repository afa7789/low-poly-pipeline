"""Mutation (n01S): medido em artifacts/model-sheets/refs/n01S/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n01S.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "tar": 0x262324, "tar_dk": 0x1A1819, "tar_lt": 0x34302F, "bone": 0x7C7873, "bone_dk": 0x5E5A56, "red": 0xC8161E,
}

HIP, KNEE, ANKLE = 1.10, 0.52, 0.14
WAIST, NECK, TOP = 1.37, 2.2, 2.72
SH_X, SH_Y, EL_Y, WR_Y = 0.86, 2.22, 1.55, 1.02
LEG_X, KNEE_X, ANK_X = 0.30, 0.34, 0.42


def head():
    H.frustum("head", "tar", (0, 2.1, 0.5), (0, 2.45, 0.52), (0.26, 0.26), (0.28, 0.27), sides=8)
    H.frustum("head", "tar_lt", (0, 2.4, 0.5), (0, 2.72, 0.46), (0.28, 0.27), (0.18, 0.2), sides=8)
    H.frustum("head", "tar", (0, 2.2, 0.24), (0, 2.6, 0.3), (0.3, 0.2), (0.24, 0.2), sides=8)    # nuca
    H.box("head", "red", (0, 2.52, 0.74), (0.05, 0.4, 0.04))
    for y in (2.08, 1.99):
        H.frustum("head", "tar_dk", (0, y, 0.6), (0, y - 0.1, 0.62), (0.03, 0.03), (0.008, 0.008), sides=4)


def torso():
    H.frustum("spine", "tar", (0, WAIST - 0.05, 0.02), (0, 1.8, 0.1), (0.42, 0.34), (0.62, 0.38))
    H.frustum("spine", "tar", (0, 1.8, 0.1), (0, 2.28, 0.14), (0.62, 0.38), (0.5, 0.34))
    H.frustum("spine", "tar_lt", (0, 2.1, -0.1), (0, 2.5, 0.05), (0.52, 0.3), (0.3, 0.28))        # corcunda
    for s in (-1, 1):       # ombros em declive: trapezio largo ate o braco
        H.frustum("spine", "tar", (s * 0.2, 2.3, 0.08), (s * 0.84, 2.14, 0.16), (0.36, 0.32), (0.3, 0.28), sides=6)
    H.box("spine", "red", (0, 1.95, 0.45), (0.62, 0.55, 0.04))                                      # brilho entre costelas
    for i, y in enumerate((2.18, 2.01, 1.84, 1.67)):
        w = 0.5 - 0.03 * abs(i - 1.5)
        H.frustum("spine", "bone", (-w, y, 0.5), (w, y, 0.5), (0.1, 0.06), (0.1, 0.06), sides=4)
        for s in (-1, 1):
            H.frustum("spine", "bone", (s * w, y, 0.5), (s * (w + 0.1), y + 0.02, 0.18), (0.1, 0.06), (0.1, 0.06), sides=4)
    H.frustum("spine", "bone_dk", (0, 2.2, 0.52), (0, 1.55, 0.5), (0.05, 0.05), (0.07, 0.05), sides=4)     # esterno
    H.frustum("spine", "red", (0.04, 2.35, -0.3), (-0.08, 1.9, -0.36), (0.04, 0.03), (0.06, 0.03), sides=4)
    H.frustum("spine", "red", (-0.08, 1.9, -0.36), (0.06, 1.5, -0.34), (0.06, 0.03), (0.03, 0.03), sides=4)


def pelvis():
    H.frustum("pelvis", "tar", (0, 0.95, 0), (0, WAIST, 0.02), (0.52, 0.38), (0.42, 0.34))
    H.frustum("pelvis", "tar_dk", (0, 1.0, 0.3), (0, 0.78, 0.3), (0.03, 0.03), (0.008, 0.008), sides=4)


def leg(s, side):
    H.frustum(f"thigh.{side}", "tar", (s * KNEE_X, KNEE - 0.04, 0.02), (s * LEG_X, HIP + 0.04, 0), (0.24, 0.27), (0.3, 0.34))
    H.frustum(f"thigh.{side}", "tar_lt", (s * 0.32, 0.75, 0.02), (s * 0.3, 1.1, 0.0), (0.22, 0.26), (0.28, 0.32))
    H.frustum(f"shin.{side}", "tar", (s * ANK_X, ANKLE, 0), (s * KNEE_X, KNEE + 0.04, 0.02), (0.28, 0.3), (0.22, 0.25))
    H.frustum(f"shin.{side}", "tar_lt", (s * 0.38, 0.2, 0.02), (s * 0.36, 0.4, 0.02), (0.3, 0.32), (0.3, 0.33))
    fx = s * 0.46
    H.frustum(f"foot.{side}", "tar", (fx, 0.1, -0.2), (fx, 0.34, 0.0), (0.3, 0.34), (0.24, 0.26))
    H.frustum(f"foot.{side}", "tar", (fx, 0.1, -0.35), (fx, 0.1, 0.3), (0.33, 0.1), (0.35, 0.1), sides=6)
    for t in (-1, 0, 1):        # dedos de piche
        H.frustum(f"foot.{side}", "tar_dk", (fx + t * 0.2, 0.1, 0.2), (fx + t * 0.23, 0.07, 0.6), (0.1, 0.08), (0.09, 0.05), sides=6)


def arm(s, side):
    ax = s * SH_X
    H.frustum(f"arm.{side}", "tar", (ax, SH_Y + 0.14, 0.16), (ax, 1.9, 0.2), (0.3, 0.34), (0.36, 0.38))       # ombro
    H.frustum(f"arm.{side}", "tar_lt", (ax, 1.9, 0.2), (ax, EL_Y + 0.05, 0.24), (0.36, 0.38), (0.24, 0.25))
    H.frustum(f"forearm.{side}", "tar", (ax, EL_Y + 0.1, 0.24), (ax, 1.25, 0.28), (0.25, 0.27), (0.32, 0.34))
    H.frustum(f"forearm.{side}", "tar_lt", (ax, 1.25, 0.28), (ax, WR_Y, 0.3), (0.32, 0.34), (0.23, 0.25))
    H.frustum(f"forearm.{side}", "tar", (ax, WR_Y + 0.04, 0.3), (ax, 0.82, 0.34), (0.27, 0.28), (0.33, 0.34))   # punho
    H.frustum(f"forearm.{side}", "tar_lt", (ax, 0.82, 0.34), (ax, 0.6, 0.36), (0.33, 0.34), (0.2, 0.2))
    for dx in (-0.14, 0.0, 0.14):
        H.frustum(f"forearm.{side}", "tar_dk", (ax + dx, 0.66, 0.36), (ax + dx, 0.3 - abs(dx), 0.38), (0.045, 0.045), (0.008, 0.008), sides=4)
    H.frustum(f"arm.{side}", "red", (ax + s * 0.2, 2.1, 0.0), (ax + s * 0.28, 1.65, 0.1), (0.03, 0.03), (0.04, 0.03), sides=4)


def make():
    head()
    torso()
    pelvis()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        arm(s, side)


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0.3), (0, TOP, 0.3))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0.2), (s * SH_X, EL_Y, 0.2))
        out[f"forearm.{side}"] = ((s * SH_X, EL_Y, 0.2), (s * SH_X, WR_Y, 0.2))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * KNEE_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * ANK_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * ANK_X, ANKLE, 0), (s * ANK_X, 0.06, 0.5))
    return out


H.build("n01S", "biped", PALETTE, make, joints())
