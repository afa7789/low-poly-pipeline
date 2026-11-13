"""Skeletal Hero (n00C): measured on artifacts/model-sheets/refs/n00C/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n00C.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "coat": 0x6B4630, "coat_dk": 0x553826, "collar": 0x45454B, "bone": 0xD8CDAE, "bone_dk": 0xB5A885,
    "cap": 0x6A4A32, "visor": 0x33261D, "eye": 0x35E04A, "black": 0x15151A, "haft": 0x3B3B40,
    "blade": 0x6E7076, "blade_lt": 0x9A9CA4, "cap_band": 0x4A3222,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X, FOOT_X = 1.1, 0.5, 0.17, 0.28, 0.43, 0.5
WAIST, NECK, TOP = 1.42, 2.16, 2.72
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.54, 2.12, 0.62, 1.6, 1.1
HAFT_Z = 0.45
SKIRT_MID = 0.95


def hem(p):
    """The coat skirt follows the thigh of its side below the middle."""
    if p[1] > SKIRT_MID:
        return {"pelvis": 1.0}
    return {"pelvis": 0.45, "thigh.L" if p[0] > 0 else "thigh.R": 0.55}


def haft_x(y):
    return -0.06 + (y - 0.46) / 2.24 * 0.4


def head():
    H.frustum("head", "bone", (0, 2.2, 0.03), (0, 2.58, 0.03), (0.25, 0.26), (0.26, 0.27), sides=8)
    H.frustum("head", "bone_dk", (0, 2.1, 0.1), (0, 2.26, 0.08), (0.12, 0.12), (0.17, 0.16), sides=6)
    for s in (-1, 1):
        H.box("head", "black", (s * 0.1, 2.44, 0.28), (0.14, 0.13, 0.06))
        H.box("head", "eye", (s * 0.1, 2.44, 0.31), (0.09, 0.08, 0.03))
    H.box("head", "black", (0, 2.32, 0.3), (0.06, 0.08, 0.04))
    H.frustum("head", "collar", (0, 1.98, 0), (0, 2.22, 0), (0.38, 0.3), (0.3, 0.27), sides=8)
    H.frustum("head", "cap_band", (0, 2.56, 0), (0, 2.62, 0), (0.3, 0.29), (0.31, 0.3), sides=8)
    H.frustum("head", "cap", (0, 2.62, 0), (0, 2.76, 0), (0.31, 0.3), (0.35, 0.33), sides=8)
    H.frustum("head", "visor", (0, 2.58, 0.26), (0, 2.6, 0.5), (0.2, 0.05), (0.18, 0.03), sides=4)


def torso():
    H.frustum("spine", "coat", (0, WAIST - 0.04, 0), (0, 2.08, 0), (0.5, 0.38), (0.6, 0.4), sides=8)
    H.frustum("spine", "coat", (0, 2.08, 0), (0, 2.26, 0), (0.6, 0.4), (0.32, 0.27), sides=8)
    H.frustum("pelvis", "coat_dk", (0, WAIST - 0.1, 0), (0, WAIST + 0.05, 0), (0.52, 0.4), (0.52, 0.4), sides=8)
    skirt = H.frustum("pelvis", "coat", (0, 0.46, 0), (0, WAIST - 0.06, 0), (0.66, 0.48), (0.52, 0.4), sides=8)
    H.soft(skirt, hem)


def leg(s, side):
    H.frustum(f"thigh.{side}", "bone", (s * KNEE_X, KNEE - 0.04, 0), (s * LEG_X, HIP, 0), (0.15, 0.15), (0.13, 0.13), sides=6)
    H.frustum(f"shin.{side}", "bone_dk", (s * KNEE_X, KNEE + 0.06, 0), (s * KNEE_X, KNEE - 0.08, 0), (0.17, 0.17), (0.15, 0.15), sides=6)
    H.chain(f"shin.{side}", "bone", [(s * KNEE_X, KNEE - 0.04, 0), (s * 0.46, 0.34, 0), (s * FOOT_X, ANKLE, 0)],
            [(0.14, 0.14), (0.1, 0.1), (0.13, 0.13)])
    H.frustum(f"foot.{side}", "bone", (s * FOOT_X, 0.03, -0.1), (s * FOOT_X, 0.2, -0.02), (0.18, 0.2), (0.14, 0.14), sides=6)
    H.frustum(f"foot.{side}", "bone", (s * FOOT_X, 0.09, 0.0), (s * FOOT_X, 0.07, 0.42), (0.2, 0.1), (0.24, 0.07), sides=6)
    H.frustum(f"foot.{side}", "bone_dk", (s * FOOT_X, 0.05, 0.38), (s * FOOT_X, 0.05, 0.52), (0.24, 0.05), (0.2, 0.04), sides=6)


def arm(s, side, hand):
    H.chain(f"arm.{side}", "coat", [(s * SH_X, SH_Y + 0.05, 0), (s * 0.6, 1.9, 0.03), (s * EL_X, EL_Y, 0.08)],
            [(0.2, 0.23), (0.19, 0.22), (0.17, 0.19)])
    H.chain(f"forearm.{side}", "coat_dk", [(s * EL_X, EL_Y + 0.02, 0.08), (s * 0.4, (EL_Y + hand[1]) / 2, 0.24), (hand[0], hand[1], hand[2] - 0.04)],
            [(0.2, 0.2), (0.19, 0.19), (0.15, 0.15)])
    H.frustum(f"forearm.{side}", "bone", (hand[0], hand[1] - 0.12, hand[2]), (hand[0], hand[1] + 0.12, hand[2]), (0.15, 0.14), (0.17, 0.15), sides=6)


def axe():
    bot, top = (haft_x(0.46), 0.46, HAFT_Z), (haft_x(2.7), 2.7, HAFT_Z)
    H.frustum("forearm.L", "haft", bot, top, (0.05, 0.05), (0.05, 0.05), sides=6)
    H.frustum("forearm.L", "black", (bot[0] - 0.01, 0.34, HAFT_Z), (bot[0], 0.5, HAFT_Z), (0.04, 0.04), (0.08, 0.08), sides=4)
    H.frustum("forearm.L", "haft", (haft_x(2.7), 2.7, HAFT_Z), (haft_x(2.85), 2.85, HAFT_Z), (0.05, 0.05), (0.02, 0.02), sides=4)
    z = HAFT_Z
    H.panel("forearm.L", "blade", [(0.33, 2.78, z), (0.6, 2.66, z), (0.74, 2.45, z), (0.6, 2.2, z), (0.26, 1.98, z)], thickness=0.08)
    H.panel("forearm.L", "blade_lt", [(0.6, 2.66, z), (0.74, 2.45, z), (0.6, 2.2, z), (0.55, 2.4, z)], thickness=0.1)
    H.box("forearm.L", "black", (haft_x(2.4) + 0.03, 2.4, z), (0.1, 0.5, 0.12))


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    arm(1, "L", (haft_x(1.68), 1.68, HAFT_Z))
    arm(-1, "R", (haft_x(1.43), 1.43, HAFT_Z))
    axe()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * KNEE_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * FOOT_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * FOOT_X, ANKLE, 0), (s * FOOT_X, 0.06, 0.5))
    return out


H.build("n00C", "biped", PALETTE, make, joints())
