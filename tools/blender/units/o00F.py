"""Infostealer (o00F): measured on artifacts/model-sheets/refs/o00F/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/o00F.py -- <out.glb>

Hooded brute with a huge pipe slung on the back (spine), a funnel staff in the left hand (forearm.L).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "cloak": 0x3A2A26, "cloak_dk": 0x2A1E1B, "black": 0x1A1517, "skin": 0x7A3424, "skin_dk": 0x5E2819,
    "orange": 0xFF5A1E, "patch": 0x9A3E22, "pipe": 0x4E4045, "pipe_in": 0x120C0E, "wood": 0x6B3A22,
    "bag": 0x7A5538, "horn": 0xC9B08A, "tusk": 0xEDE3C8, "funnel": 0x5A4A50,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X = 1.08, 0.58, 0.2, 0.3, 0.32
WAIST, NECK, TOP = 1.34, 2.05, 2.72
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.74, 2.0, 0.82, 1.5, 1.04
STAFF_X, STAFF_Z = 0.86, 0.2


def head():
    H.frustum("head", "skin", (0, 2.08, 0.06), (0, 2.42, 0.08), (0.24, 0.24), (0.28, 0.26), sides=6)
    H.box("head", "black", (0, 2.34, 0.32), (0.44, 0.08, 0.04))                  # blindfold
    for s in (-1, 1):
        H.frustum("head", "tusk", (s * 0.1, 2.14, 0.32), (s * 0.12, 2.26, 0.34), (0.04, 0.03), (0.015, 0.015), sides=4)
    for y0, y1, r0, r1 in ((2.0, 2.34, 0.44, 0.42), (2.34, 2.58, 0.42, 0.32), (2.58, 2.74, 0.32, 0.1)):   # hood, open to the front
        H.frustum("head", "cloak", (0, y0, -0.2), (0, y1, -0.2), (r0, 0.3), (r1, 0.3), sides=8)
    H.frustum("head", "cloak_dk", (0, 2.46, 0.14), (0, 2.56, 0.3), (0.3, 0.05), (0.3, 0.05), sides=4)    # hood brim


def torso():
    H.frustum("spine", "black", (0, WAIST - 0.04, 0), (0, 2.0, 0), (0.52, 0.4), (0.66, 0.44), sides=8)
    H.frustum("spine", "cloak", (0, 1.56, 0), (0, 2.1, 0), (0.98, 0.58), (0.74, 0.5), sides=6)           # poncho
    H.frustum("spine", "cloak", (0, 2.1, 0), (0, 2.22, 0), (0.74, 0.5), (0.36, 0.34), sides=6)
    H.frustum("spine", "cloak_dk", (0, 1.48, 0), (0, 1.6, 0), (0.94, 0.58), (0.98, 0.58), sides=6)
    H.box("spine", "orange", (0.82, 1.9, 0.2), (0.3, 0.36, 0.5))                                       # shoulder patch
    H.box("spine", "orange", (-0.82, 1.9, -0.1), (0.3, 0.36, 0.5))
    H.box("spine", "patch", (-0.2, 1.8, 0.58), (0.3, 0.34, 0.08))


def pipe():
    pts = [(0.17, 1.25, -0.86), (0.17, 2.1, -0.68), (0.17, 3.05, -0.48)]
    H.chain("spine", "pipe", pts, [(0.23, 0.23), (0.25, 0.25), (0.21, 0.21)], sides=6)
    H.frustum("spine", "pipe_in", (0.17, 3.03, -0.48), (0.17, 3.08, -0.48), (0.15, 0.15), (0.15, 0.15), sides=6)


def belt():
    H.frustum("pelvis", "patch", (0, WAIST - 0.1, 0), (0, WAIST + 0.08, 0), (0.54, 0.44), (0.54, 0.44), sides=8)
    H.box("pelvis", "bag", (0, WAIST - 0.01, 0.45), (0.22, 0.17, 0.05))
    H.frustum("pelvis", "black", (0, 0.86, 0), (0, 1.14, 0), (0.44, 0.36), (0.5, 0.4), sides=8)
    H.frustum("pelvis", "bag", (-0.6, 0.98, 0.04), (-0.6, 1.22, 0.04), (0.2, 0.18), (0.1, 0.1), sides=6)    # pouch
    H.frustum("pelvis", "horn", (0.58, 1.04, 0.1), (0.54, 1.22, 0.1), (0.07, 0.07), (0.14, 0.14), sides=6)  # horn


def leg(s, side):
    k, f = s * KNEE_X, s * 0.32
    H.frustum(f"thigh.{side}", "black", (k, KNEE - 0.04, 0), (s * LEG_X, HIP + 0.04, 0), (0.27, 0.28), (0.3, 0.3), sides=6)
    H.frustum(f"shin.{side}", "black", (k, ANKLE + 0.06, 0), (k, KNEE + 0.02, 0), (0.22, 0.22), (0.25, 0.25), sides=6)
    H.frustum(f"shin.{side}", "skin_dk", (k, 0.3, 0), (k, 0.62, 0), (0.28, 0.28), (0.3, 0.3), sides=6)      # boot cuff
    H.frustum(f"foot.{side}", "skin", (f, 0.03, -0.02), (f, 0.34, -0.02), (0.27, 0.27), (0.25, 0.25), sides=6)
    H.frustum(f"foot.{side}", "skin", (f, 0.12, 0.06), (f, 0.09, 0.46), (0.26, 0.14), (0.22, 0.08), sides=6)


def arm(s, side):
    elbow = (s * EL_X, EL_Y, 0.04)
    H.frustum(f"arm.{side}", "black", (s * SH_X, SH_Y + 0.04, 0), elbow, (0.34, 0.32), (0.29, 0.28), sides=6)
    H.frustum(f"forearm.{side}", "skin_dk", (s * EL_X, EL_Y + 0.04, 0.04), (s * EL_X, 1.1, 0.07), (0.27, 0.27), (0.23, 0.23), sides=6)
    H.frustum(f"forearm.{side}", "skin", (s * EL_X, 1.12, 0.07), (s * EL_X, 0.74, 0.1), (0.23, 0.23), (0.27, 0.27), sides=6)   # big fist
    H.frustum(f"forearm.{side}", "skin", (s * EL_X, 0.76, 0.1), (s * EL_X, 0.62, 0.12), (0.27, 0.27), (0.17, 0.17), sides=6)


def staff():
    x, z = STAFF_X, STAFF_Z
    H.frustum("forearm.L", "wood", (x, 0.0, z), (x, 2.4, z), (0.08, 0.08), (0.085, 0.085), sides=6)
    H.frustum("forearm.L", "funnel", (x, 2.25, z), (x, 2.75, z), (0.08, 0.08), (0.3, 0.3), sides=8)
    H.frustum("forearm.L", "orange", (x, 2.7, z), (x, 2.98, z), (0.12, 0.12), (0.02, 0.02), sides=4)


def make():
    head()
    torso()
    pipe()
    belt()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        arm(s, side)
    staff()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * KNEE_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * KNEE_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * KNEE_X, ANKLE, 0), (s * KNEE_X, 0.06, 0.5))
    return out


H.build("o00F", "biped", PALETTE, make, joints())
