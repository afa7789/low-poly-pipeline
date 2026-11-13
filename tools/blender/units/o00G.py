"""Blood Shaman (o00G): measured on artifacts/model-sheets/refs/o00G/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/o00G.py -- <out.glb>

Plague-mask orc with a blood cauldron on the back (spine) and a gold-forked staff in the right hand (forearm.R).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "green": 0x6EA82E, "green_dk": 0x558A22, "black": 0x1A1214, "boot": 0xA07848, "red": 0xB01C1C, "blood": 0xD02020,
    "gold": 0xD9A21E, "orange": 0xFF6A1E, "mask": 0xEFE6D6, "hole": 0x0E0A0C, "wood": 0x5A3322, "cauldron": 0x241A1C,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X = 0.98, 0.52, 0.2, 0.3, 0.34
WAIST, NECK, TOP = 1.2, 2.05, 2.55
SH_X, SH_Y = 0.78, 2.0
STAFF_X, STAFF_Z = -1.14, 0.12
ARM_L = ((0.9, 1.5), (0.86, 0.95))         # left arm hangs: (elbow x, y), (wrist x, y)
ARM_R = ((-1.02, 1.55), (-1.12, 1.15))      # right arm reaches out to the staff


def head():
    H.frustum("head", "green", (0, 2.0, 0.0), (0, 2.34, 0.1), (0.3, 0.3), (0.28, 0.28), sides=6)
    H.frustum("head", "red", (0, 2.34, -0.05), (0, 2.5, -0.05), (0.26, 0.26), (0.2, 0.2), sides=6)       # bloody hair
    H.frustum("head", "mask", (0, 1.98, 0.36), (0, 2.5, 0.36), (0.36, 0.16), (0.36, 0.16), sides=6)
    H.frustum("head", "mask", (0, 2.2, 0.46), (0, 1.8, 1.0), (0.12, 0.12), (0.04, 0.04), sides=6)            # beak
    H.frustum("head", "orange", (0, 1.86, 0.88), (0, 1.76, 1.08), (0.06, 0.05), (0.045, 0.04), sides=6)
    for s in (-1, 1):
        H.box("head", "hole", (s * 0.15, 2.3, 0.45), (0.12, 0.14, 0.05))


def torso():
    H.frustum("spine", "green", (0, 0.98, 0), (0, 1.6, 0), (0.5, 0.5), (0.66, 0.54), sides=8)             # belly
    H.frustum("spine", "green", (0, 1.6, 0), (0, 2.08, 0), (0.66, 0.54), (0.7, 0.46), sides=8)            # chest
    H.frustum("spine", "green_dk", (0, 2.08, -0.02), (0, 2.26, -0.04), (0.7, 0.46), (0.3, 0.3), sides=8)  # hunched shoulders
    H.frustum("spine", "red", (0.4, 2.12, 0.5), (-0.34, 1.3, 0.56), (0.12, 0.04), (0.12, 0.04), sides=4)    # sash
    H.frustum("spine", "red", (0.46, 2.18, 0.0), (0.46, 2.2, 0.0), (0.2, 0.5), (0.2, 0.5), sides=4)


def cauldron():
    c = [(0, 1.15, -0.8), (0, 1.35, -0.8), (0, 1.7, -0.8), (0, 2.05, -0.8), (0, 2.2, -0.8)]
    r = [(0.3, 0.26), (0.62, 0.5), (0.8, 0.58), (0.66, 0.52), (0.6, 0.5)]
    H.chain("spine", "cauldron", c, r, sides=8)
    H.frustum("spine", "gold", (0, 2.18, -0.8), (0, 2.28, -0.8), (0.68, 0.56), (0.68, 0.56), sides=8)       # rim
    H.frustum("spine", "blood", (0, 2.26, -0.8), (0, 2.4, -0.8), (0.52, 0.4), (0.4, 0.3), sides=8)
    H.frustum("spine", "gold", (0, 2.22, -0.3), (0, 2.26, -0.5), (0.1, 0.06), (0.1, 0.1), sides=4)       # strap to the neck
    H.frustum("spine", "blood", (0, 1.4, -1.3), (0, 2.1, -1.3), (0.06, 0.03), (0.1, 0.03), sides=4)       # drip


def pants():
    H.frustum("pelvis", "black", (0, 0.8, 0), (0, 1.2, 0), (0.5, 0.42), (0.56, 0.48), sides=8)


def leg(s, side):
    k, f = s * KNEE_X, s * 0.32
    H.frustum(f"thigh.{side}", "black", (k, KNEE - 0.1, 0), (s * LEG_X, HIP + 0.04, 0), (0.3, 0.3), (0.34, 0.34), sides=6)
    H.frustum(f"shin.{side}", "black", (k, 0.3, 0), (k, KNEE + 0.02, 0), (0.24, 0.24), (0.3, 0.3), sides=6)
    H.frustum(f"foot.{side}", "boot", (f, 0.03, -0.02), (f, 0.34, -0.02), (0.26, 0.26), (0.28, 0.28), sides=6)
    H.frustum(f"foot.{side}", "boot", (f, 0.12, 0.06), (f, 0.09, 0.5), (0.26, 0.16), (0.24, 0.1), sides=6)


def arm(s, side, elbow, wrist):
    ex, ey = elbow
    wx, wy = wrist
    H.frustum(f"arm.{side}", "green", (s * SH_X, SH_Y + 0.08, 0), (ex, ey, 0.05), (0.34, 0.34), (0.28, 0.28), sides=6)
    H.frustum(f"forearm.{side}", "green", (ex, ey + 0.04, 0.05), (wx, wy + 0.1, 0.1), (0.28, 0.28), (0.26, 0.26), sides=6)
    H.frustum(f"forearm.{side}", "green", (wx, wy + 0.2, 0.1), (wx, wy - 0.28, 0.12), (0.26, 0.26), (0.28, 0.28), sides=6)   # big fist
    H.frustum(f"forearm.{side}", "green_dk", (wx, wy - 0.25, 0.12), (wx, wy - 0.4, 0.14), (0.28, 0.28), (0.18, 0.18), sides=6)


def staff():
    x, z = STAFF_X, STAFF_Z
    H.frustum("forearm.R", "wood", (x, 0.0, z), (x, 2.5, z), (0.08, 0.08), (0.08, 0.08), sides=6)
    H.frustum("forearm.R", "gold", (x, 2.2, z), (x, 2.5, z), (0.11, 0.11), (0.11, 0.11), sides=6)
    H.box("forearm.R", "gold", (x, 2.58, z), (0.5, 0.14, 0.2))
    H.box("forearm.R", "orange", (x, 2.9, z), (0.42, 0.5, 0.2))
    for s in (-1, 1):
        H.box("forearm.R", "gold", (x + s * 0.26, 2.9, z), (0.1, 0.58, 0.22))


def make():
    head()
    torso()
    cauldron()
    pants()
    for s, side, arms in ((1, "L", ARM_L), (-1, "R", ARM_R)):
        leg(s, side)
        arm(s, side, *arms)
    staff()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side, ((ex, ey), (wx, wy)) in ((1, "L", ARM_L), (-1, "R", ARM_R)):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (ex, ey, 0))
        out[f"forearm.{side}"] = ((ex, ey, 0), (wx, wy, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * KNEE_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * KNEE_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * KNEE_X, ANKLE, 0), (s * KNEE_X, 0.06, 0.5))
    return out


H.build("o00G", "biped", PALETTE, make, joints())
