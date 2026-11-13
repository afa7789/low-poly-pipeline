"""Skeleton Archer (n00D): measured on artifacts/model-sheets/refs/n00D/sheet.jpg. The sheet draws a bolt-action
rifle held in both hands, not a bow.

    blender -b --factory-startup -P tools/blender/units/n00D.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "bone": 0xD6CDB0, "bone_dk": 0xA89C78, "cap": 0x6B4A33, "cap_dk": 0x4A3222, "strap": 0x5A3A26,
    "cart": 0xEDEBE3, "wood": 0x6A4228, "steel": 0x2F3136, "eye": 0x35E04A, "black": 0x15151A,
}

HIP, KNEE, ANKLE, LEG_X = 1.3, 0.74, 0.16, 0.2
WAIST, NECK, TOP = 1.55, 2.12, 2.74
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.4, 2.06, 0.5, 1.58, 1.1
BUTT, MUZZLE = (-0.68, 1.1, -0.12), (0.85, 2.3, 0.9)
HAND_R, HAND_L = (-0.3, 1.4, 0.14), (0.27, 1.84, 0.51)


def on_rifle(t):
    return tuple(BUTT[i] + (MUZZLE[i] - BUTT[i]) * t for i in range(3))


def head():
    H.frustum("head", "bone", (0, 2.2, 0.04), (0, 2.52, 0.04), (0.23, 0.24), (0.24, 0.25), sides=8)
    H.frustum("head", "bone_dk", (0, 2.1, 0.1), (0, 2.24, 0.08), (0.12, 0.12), (0.17, 0.16), sides=6)
    for s in (-1, 1):
        H.box("head", "black", (s * 0.1, 2.4, 0.27), (0.13, 0.13, 0.05))
        H.box("head", "eye", (s * 0.1, 2.4, 0.3), (0.08, 0.08, 0.03))
    H.box("head", "black", (0, 2.3, 0.28), (0.05, 0.08, 0.04))
    H.frustum("head", "cap_dk", (0, 2.5, 0), (0, 2.58, 0), (0.3, 0.3), (0.3, 0.3), sides=8)
    H.frustum("head", "cap", (0, 2.58, 0), (0, 2.74, 0), (0.3, 0.3), (0.34, 0.34), sides=8)
    H.frustum("head", "cap_dk", (0, 2.56, 0.26), (0, 2.58, 0.42), (0.2, 0.05), (0.18, 0.03), sides=4)
    H.chain("head", "bone", [(0, 2.0, 0), (0, 2.08, 0), (0, 2.16, 0)], [(0.1, 0.1), (0.085, 0.085), (0.1, 0.1)])


def ribs():
    H.frustum("spine", "bone", (0, 1.52, -0.02), (0, 2.12, -0.02), (0.08, 0.1), (0.09, 0.1), sides=6)
    for i, (y, w) in enumerate(((1.62, 0.29), (1.74, 0.33), (1.86, 0.35), (1.98, 0.33))):
        H.frustum("spine", "bone", (0, y, 0), (0, y + 0.07, 0), (w, 0.2), (w, 0.2), sides=8)
    H.frustum("spine", "bone_dk", (0, 1.6, 0.17), (0, 2.08, 0.17), (0.07, 0.04), (0.09, 0.04), sides=4)
    H.frustum("spine", "bone", (0, 2.04, 0), (0, 2.14, 0), (0.46, 0.2), (0.3, 0.16), sides=8)     # shoulder girdle


def strap():
    a, b = (0.2, 2.05, 0.24), (-0.3, 1.6, 0.26)
    H.frustum("spine", "strap", a, b, (0.07, 0.04), (0.07, 0.04), sides=4)
    for t in (0.2, 0.4, 0.6, 0.8):
        c = tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
        H.box("spine", "cart", (c[0], c[1], c[2] + 0.05), (0.07, 0.1, 0.04))


def pelvis():
    H.frustum("pelvis", "bone", (0, 1.28, 0), (0, 1.56, 0), (0.27, 0.17), (0.2, 0.15), sides=8)
    H.frustum("pelvis", "bone_dk", (0, 1.22, 0.05), (0, 1.3, 0.05), (0.14, 0.08), (0.22, 0.12), sides=6)


def leg(s, side):
    kx = s * LEG_X
    H.chain(f"thigh.{side}", "bone", [(kx, HIP + 0.06, 0), (kx, 1.0, 0), (kx, KNEE + 0.02, 0)],
            [(0.16, 0.16), (0.12, 0.12), (0.16, 0.16)])
    H.chain(f"shin.{side}", "bone", [(kx, KNEE, 0), (kx, 0.45, 0), (kx, ANKLE + 0.02, 0)],
            [(0.16, 0.16), (0.11, 0.11), (0.14, 0.14)])
    H.frustum(f"foot.{side}", "bone", (kx, 0.07, -0.08), (kx, 0.05, 0.3), (0.13, 0.06), (0.15, 0.04), sides=6)
    H.frustum(f"foot.{side}", "bone_dk", (kx, 0.04, 0.28), (kx, 0.04, 0.4), (0.13, 0.04), (0.1, 0.03), sides=6)


def arm(s, side, hand):
    H.chain(f"arm.{side}", "bone", [(s * SH_X, SH_Y, 0), (s * 0.46, 1.84, 0.02), (s * EL_X, EL_Y, 0.06)],
            [(0.13, 0.13), (0.095, 0.095), (0.12, 0.12)])
    mid = ((s * EL_X + hand[0]) / 2, (EL_Y + hand[1]) / 2, (0.06 + hand[2]) / 2)
    H.chain(f"forearm.{side}", "bone", [(s * EL_X, EL_Y, 0.06), mid, (hand[0], hand[1], hand[2] - 0.03)],
            [(0.11, 0.11), (0.09, 0.09), (0.1, 0.1)])
    H.frustum(f"forearm.{side}", "bone_dk", (hand[0], hand[1] - 0.1, hand[2]), (hand[0], hand[1] + 0.1, hand[2]),
              (0.13, 0.12), (0.14, 0.12), sides=6)


def rifle():
    stock, wrist, hand_wood, tip = on_rifle(0.0), on_rifle(0.3), on_rifle(0.72), on_rifle(1.0)
    H.frustum("forearm.L", "wood", stock, wrist, (0.1, 0.16), (0.07, 0.1), sides=4)
    H.frustum("forearm.L", "steel", wrist, on_rifle(0.5), (0.07, 0.08), (0.06, 0.07), sides=4)
    H.frustum("forearm.L", "wood", on_rifle(0.5), hand_wood, (0.065, 0.08), (0.06, 0.07), sides=4)
    H.frustum("forearm.L", "steel", hand_wood, tip, (0.05, 0.055), (0.04, 0.045), sides=6)
    c = on_rifle(0.38)
    H.box("forearm.L", "steel", (c[0], c[1] + 0.08, c[2]), (0.06, 0.08, 0.08))      # bolt knob


def make():
    head()
    ribs()
    strap()
    pelvis()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    arm(1, "L", HAND_L)
    arm(-1, "R", HAND_R)
    rifle()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("n00D", "biped", PALETTE, make, joints())
