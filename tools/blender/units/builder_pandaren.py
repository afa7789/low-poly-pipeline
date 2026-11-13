"""Pandaren Panda Builder (builder_pandaren): round panda in a straw hat and pink vest, mallet in the right paw,
brazier on the left hip, rope coil on the back; measured on artifacts/model-sheets/refs/builder_pandaren/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/builder_pandaren.py -- <out.glb>
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "white": 0xF2F2F0, "sleeve": 0x484A4E, "nose": 0x1A1A1E, "pink": 0xD13A6E, "green": 0x14A06E,
    "hat": 0xD2AE6B, "hat_dk": 0xB08A48, "tan": 0xE9BE96, "wood": 0x6B4A30, "iron": 0x3F3430,
    "brazier": 0x6A4A3A, "flame": 0xE0522A, "flame_hi": 0xFF9A3A, "rope": 0x4A3426,
}

HIP, KNEE, ANKLE, LEG_X = 0.68, 0.38, 0.12, 0.26
WAIST, NECK, TOP = 0.98, 1.8, 2.64
SH_X, SH_Y = 0.56, 1.7
SKIRT_MID = 0.7


def hem(p):
    if p[1] > SKIRT_MID:
        return {"pelvis": 1.0}
    return {"pelvis": 0.5, "thigh.L" if p[0] > 0 else "thigh.R": 0.5}


def head():
    H.frustum("head", "white", (0, 1.72, 0.02), (0, 1.95, 0.03), (0.3, 0.3), (0.38, 0.37), sides=8)
    H.frustum("head", "white", (0, 1.95, 0.03), (0, 2.22, 0.03), (0.38, 0.37), (0.34, 0.33), sides=8)
    H.frustum("head", "white", (0, 1.84, 0.26), (0, 1.88, 0.52), (0.15, 0.12), (0.1, 0.08), sides=6)     # snout
    H.box("head", "nose", (0, 1.92, 0.54), (0.1, 0.07, 0.05))
    for s in (-1, 1):
        H.box("head", "nose", (s * 0.16, 2.0, 0.33), (0.15, 0.17, 0.06))
        H.frustum("head", "nose", (s * 0.3, 2.2, -0.05), (s * 0.34, 2.34, -0.05), (0.09, 0.07), (0.06, 0.05), sides=6)
    H.frustum("head", "hat_dk", (0, 2.22, 0.02), (0, 2.3, 0.02), (0.7, 0.7), (0.6, 0.6), sides=8)
    H.frustum("head", "hat", (0, 2.3, 0.02), (0, 2.66, 0.02), (0.6, 0.6), (0.03, 0.03), sides=8)


def torso():
    H.frustum("spine", "sleeve", (0, 1.62, 0), (0, 1.88, 0.02), (0.32, 0.3), (0.28, 0.26), sides=8)
    H.frustum("spine", "pink", (0, WAIST - 0.05, 0), (0, 1.3, 0.02), (0.5, 0.46), (0.66, 0.52), sides=8)
    H.frustum("spine", "pink", (0, 1.3, 0.02), (0, 1.68, 0.02), (0.66, 0.52), (0.6, 0.46), sides=8)
    H.frustum("spine", "pink", (0, 1.68, 0.02), (0, 1.82, 0.02), (0.6, 0.46), (0.34, 0.3), sides=8)
    H.frustum("pelvis", "green", (0, 0.72, 0), (0, WAIST + 0.04, 0), (0.64, 0.54), (0.64, 0.54), sides=8)
    H.box("pelvis", "green", (0, 0.84, 0.55), (0.2, 0.2, 0.06))
    H.box("pelvis", "green", (0.07, 0.62, 0.56), (0.1, 0.26, 0.04))
    H.frustum("pelvis", "white", (0, 0.45, 0), (0, 0.8, 0), (0.42, 0.38), (0.5, 0.44), sides=8)
    flap = H.frustum("pelvis", "pink", (0, 0.5, 0), (0, 0.74, 0), (0.6, 0.5), (0.62, 0.52), sides=8)
    H.soft(flap, hem)
    # brazier on the left hip
    H.box("pelvis", "brazier", (0.7, 0.72, 0.22), (0.3, 0.34, 0.3))
    H.frustum("pelvis", "flame", (0.7, 0.89, 0.22), (0.7, 1.1, 0.22), (0.11, 0.11), (0.02, 0.02), sides=6)
    H.frustum("pelvis", "flame_hi", (0.7, 0.89, 0.22), (0.7, 1.02, 0.22), (0.06, 0.06), (0.015, 0.015), sides=6)
    # rope coil on the back: a ring standing in the y-z plane beside the spine
    cy, cz, r = 1.5, -0.32, 0.45
    pts = [(0.56, cy + r * math.cos(a * math.pi / 5), cz + r * math.sin(a * math.pi / 5)) for a in range(11)]
    H.chain("spine", "rope", pts, [(0.07, 0.07)] * 11, sides=4)


def leg(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "sleeve", (x, KNEE - 0.02, 0.02), (x, HIP + 0.05, 0), (0.21, 0.23), (0.29, 0.29), sides=6)
    H.frustum(f"thigh.{side}", "sleeve", (x, KNEE + 0.05, 0.02), (x, KNEE + 0.2, 0.02), (0.24, 0.25), (0.28, 0.28), sides=6)
    H.frustum(f"shin.{side}", "sleeve", (x, ANKLE - 0.02, 0), (x, KNEE + 0.02, 0.02), (0.2, 0.21), (0.23, 0.23), sides=6)
    H.frustum(f"foot.{side}", "tan", (x, 0.03, -0.04), (x, ANKLE + 0.04, 0.02), (0.22, 0.24), (0.2, 0.2), sides=6)
    H.frustum(f"foot.{side}", "tan", (x, 0.1, 0.06), (x, 0.08, 0.42), (0.23, 0.18), (0.2, 0.1), sides=4)


def arm(s, side, ex):
    H.frustum(f"arm.{side}", "sleeve", (s * (SH_X - 0.02), SH_Y + 0.04, 0.02), (s * 0.74, 1.38, 0.04), (0.28, 0.3), (0.3, 0.3), sides=6)
    H.frustum(f"arm.{side}", "sleeve", (s * 0.74, 1.4, 0.04), (s * ex, 1.15, 0.06), (0.3, 0.3), (0.27, 0.27), sides=6)
    H.frustum(f"forearm.{side}", "sleeve", (s * ex, 1.2, 0.06), (s * (ex + 0.06), 0.92, 0.1), (0.28, 0.28), (0.23, 0.23), sides=6)
    H.frustum(f"forearm.{side}", "tan", (s * (ex + 0.06), 0.94, 0.1), (s * (ex + 0.08), 0.62, 0.14), (0.2, 0.22), (0.23, 0.21), sides=6)


def mallet():
    H.frustum("forearm.R", "wood", (-0.98, 0.82, 0.12), (-0.8, 1.06, 0.1), (0.06, 0.06), (0.05, 0.05), sides=6)
    H.box("forearm.R", "iron", (-1.02, 0.6, 0.12), (0.5, 0.6, 0.48))
    H.box("forearm.R", "wood", (-1.02, 0.6, 0.12), (0.54, 0.08, 0.52))


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    arm(1, "L", 0.86)
    arm(-1, "R", 0.9)
    mallet()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side, ex in ((1, "L", 0.86), (-1, "R", 0.9)):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * ex, 1.2, 0))
        out[f"forearm.{side}"] = ((s * ex, 1.2, 0), (s * ex, 0.7, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.45))
    return out


H.build("builder_pandaren", "biped", PALETTE, make, joints())
