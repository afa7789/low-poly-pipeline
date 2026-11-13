"""Greater Skeleton Warrior (u00B): measured on artifacts/model-sheets/refs/u00B/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/u00B.py -- <out.glb>

Skeleton in brown plate and a brimmed helmet, both hands on a sledgehammer (shaft on forearm.R, head up at the unit's left).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "bone": 0xD9C9A3, "bone_dk": 0xB3A27B, "plate": 0x5E4A3A, "plate_dk": 0x453527, "strap": 0x4A2E22,
    "shaft": 0x5A3A26, "iron": 0x4C4846, "iron_dk": 0x34312F, "eye": 0x2BE35A, "void": 0x15100D,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X, FOOT_X = 1.1, 0.62, 0.2, 0.3, 0.42, 0.5
WAIST, NECK, TOP = 1.4, 2.1, 2.72
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.46, 2.0, 0.62, 1.33, 0.9
BUTT = (-0.63, 0.9, 0.1)
TIP = (0.97, 1.93, 0.57)
HAND_R = (-0.22, 1.12, 0.3)
HAND_L = (0.46, 1.6, 0.42)


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def head():
    H.frustum("head", "bone", (0, 2.16, 0.03), (0, 2.5, 0.03), (0.2, 0.22), (0.24, 0.25), sides=8)         # skull
    H.frustum("head", "bone_dk", (0, 2.06, 0.1), (0, 2.22, 0.08), (0.12, 0.12), (0.19, 0.17), sides=6)     # jaw
    H.frustum("head", "bone", (0, 1.98, -0.02), (0, 2.14, -0.02), (0.1, 0.1), (0.13, 0.13), sides=6)       # neck
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.1, 2.38, 0.27), (0.1, 0.1, 0.05))
    H.frustum("head", "void", (0, 2.3, 0.2), (0, 2.46, 0.2), (0.17, 0.02), (0.17, 0.02), sides=4)
    H.frustum("head", "plate_dk", (0, 2.5, 0), (0, 2.56, 0), (0.42, 0.42), (0.38, 0.38), sides=8)          # brim
    H.frustum("head", "plate", (0, 2.54, 0), (0, 2.74, 0), (0.3, 0.3), (0.2, 0.2), sides=8)                # crown


def torso():
    H.frustum("spine", "plate", (0, 1.5, 0.03), (0, 2.02, 0.03), (0.34, 0.22), (0.44, 0.26), sides=6)      # breastplate
    H.frustum("spine", "plate_dk", (0, 2.0, 0), (0, 2.18, 0), (0.44, 0.26), (0.26, 0.2), sides=6)
    for y in (1.42, 1.56, 1.7):                                                                             # rib bands
        H.frustum("spine", "bone_dk", (0, y - 0.05, -0.02), (0, y + 0.06, -0.02), (0.3, 0.2), (0.32, 0.22), sides=8)
    H.frustum("spine", "bone", (0, 1.4, -0.14), (0, 2.1, -0.14), (0.08, 0.08), (0.1, 0.1), sides=6)       # spine
    H.frustum("pelvis", "bone", (0, HIP - 0.08, 0), (0, WAIST, 0), (0.34, 0.2), (0.28, 0.18), sides=8)
    H.frustum("pelvis", "bone_dk", (0, HIP - 0.24, 0.02), (0, HIP, 0.02), (0.12, 0.1), (0.34, 0.2), sides=6)


def leg(s, side):
    k, f = s * KNEE_X, s * FOOT_X
    H.frustum(f"thigh.{side}", "bone", (k, KNEE + 0.02, 0), (s * LEG_X, HIP, 0), (0.12, 0.12), (0.15, 0.15), sides=6)
    H.frustum(f"thigh.{side}", "bone_dk", (k, KNEE - 0.06, 0.02), (k, KNEE + 0.14, 0.02), (0.17, 0.16), (0.14, 0.14), sides=6)
    H.frustum(f"shin.{side}", "bone", (f, ANKLE + 0.04, 0), (k, KNEE + 0.02, 0), (0.1, 0.1), (0.14, 0.14), sides=6)
    H.frustum(f"shin.{side}", "bone_dk", (k, KNEE - 0.12, 0.02), (k, KNEE + 0.06, 0.02), (0.15, 0.15), (0.17, 0.16), sides=6)
    H.frustum(f"shin.{side}", "strap", (f, ANKLE - 0.02, 0), (f, ANKLE + 0.14, 0), (0.15, 0.15), (0.14, 0.14), sides=6)
    H.frustum(f"foot.{side}", "bone", (f, 0.02, -0.12), (f, ANKLE + 0.08, -0.04), (0.2, 0.18), (0.16, 0.14), sides=6)
    H.frustum(f"foot.{side}", "bone_dk", (f, 0.09, 0.0), (f, 0.08, 0.5), (0.2, 0.12), (0.18, 0.08), sides=6)


def arm(s, side, hand):
    elbow = (s * EL_X, EL_Y, 0.04)
    H.frustum(f"arm.{side}", "plate", (s * 0.3, 2.34, 0), (s * 0.72, 1.92, 0), (0.3, 0.34), (0.36, 0.4), sides=6)  # pauldron
    H.frustum(f"arm.{side}", "plate_dk", (s * 0.4, 2.2, 0), (s * 0.74, 1.8, 0), (0.22, 0.28), (0.28, 0.32), sides=6)
    H.chain(f"arm.{side}", "bone", [(s * SH_X, SH_Y, 0), (s * 0.56, 1.7, 0.03), elbow],
            [(0.11, 0.11), (0.12, 0.12), (0.13, 0.13)])
    mid = lerp(elbow, hand, 0.5)
    H.chain(f"forearm.{side}", "bone", [elbow, mid, lerp(elbow, hand, 0.85)], [(0.12, 0.12), (0.11, 0.11), (0.11, 0.11)])
    H.frustum(f"forearm.{side}", "strap", lerp(elbow, hand, 0.2), lerp(elbow, hand, 0.5), (0.17, 0.17), (0.16, 0.16), sides=6)  # wristband
    H.frustum(f"forearm.{side}", "bone_dk", (hand[0], hand[1] - 0.12, hand[2]), (hand[0], hand[1] + 0.12, hand[2]),
              (0.17, 0.16), (0.18, 0.16), sides=6)                                                          # fist


def hammer():
    H.frustum("forearm.R", "shaft", BUTT, TIP, (0.09, 0.09), (0.09, 0.09), sides=6)
    H.frustum("forearm.R", "strap", BUTT, lerp(BUTT, TIP, 0.08), (0.12, 0.12), (0.11, 0.11), sides=6)
    a, b = (TIP[0] + 0.19, TIP[1] - 0.12, TIP[2]), (TIP[0] - 0.19, TIP[1] + 0.12, TIP[2])   # head: perpendicular to the shaft
    H.frustum("forearm.R", "iron", lerp(a, b, -0.1), lerp(a, b, 1.1), (0.2, 0.2), (0.2, 0.2), sides=4)
    H.frustum("forearm.R", "iron_dk", lerp(a, b, -0.1), lerp(a, b, 0.05), (0.23, 0.23), (0.23, 0.23), sides=4)
    H.frustum("forearm.R", "iron_dk", lerp(a, b, 0.95), lerp(a, b, 1.1), (0.23, 0.23), (0.23, 0.23), sides=4)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    arm(1, "L", HAND_L)
    arm(-1, "R", HAND_R)
    hammer()


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


H.build("u00B", "biped", PALETTE, make, joints())
