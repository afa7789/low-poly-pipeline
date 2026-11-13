"""Greater Skeleton Archer (n01L): measured on artifacts/model-sheets/refs/n01L/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n01L.py -- <out.glb>

Long rifle held upright in both hands (forearm.L carries it), coat, helmet, green lantern on the hip.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "coat": 0x6B4630, "coat_dk": 0x553826, "collar": 0x5A3C2A, "strap": 0x8A7556, "bone": 0xD8CDAE, "bone_dk": 0xB5A885,
    "helmet": 0x56565C, "helmet_dk": 0x3F3F45, "eye": 0x35E04A, "black": 0x15151A, "wood": 0x4A3222,
    "steel": 0x3B3B40, "steel_lt": 0x6E7076, "glow": 0x2FE06A,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X, FOOT_X = 1.1, 0.5, 0.17, 0.28, 0.36, 0.4
WAIST, NECK, TOP = 1.42, 2.16, 2.72
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.58, 2.12, 0.7, 1.6, 1.1
GUN_X = 0.12


def gz(y):
    """Rifle depth at height y: leans a little forward at the top."""
    return 0.32 + (y - 1.2) / 1.85 * 0.22


def hem(p):
    if p[1] > 0.9:
        return {"pelvis": 1.0}
    return {"pelvis": 0.45, "thigh.L" if p[0] > 0 else "thigh.R": 0.55}


def head():
    H.frustum("head", "bone", (0, 2.2, 0.03), (0, 2.5, 0.03), (0.2, 0.21), (0.21, 0.22), sides=8)
    H.frustum("head", "bone_dk", (0, 2.1, 0.08), (0, 2.26, 0.06), (0.1, 0.1), (0.14, 0.13), sides=6)
    H.box("head", "black", (0, 2.4, 0.2), (0.4, 0.14, 0.1))
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.09, 2.4, 0.26), (0.09, 0.08, 0.03))
    H.frustum("head", "collar", (0, 1.98, 0), (0, 2.34, -0.02), (0.38, 0.3), (0.3, 0.28), sides=8)
    H.frustum("head", "helmet", (0, 2.46, 0), (0, 2.62, 0), (0.37, 0.36), (0.3, 0.29), sides=8)
    H.frustum("head", "helmet", (0, 2.62, 0), (0, 2.72, 0), (0.3, 0.29), (0.14, 0.14), sides=8)
    H.frustum("head", "helmet_dk", (0, 2.3, 0.2), (0, 2.5, 0.2), (0.24, 0.1), (0.26, 0.1), sides=4)   # grille over the face
    H.frustum("head", "helmet_dk", (0, 2.3, -0.24), (0, 2.52, -0.24), (0.34, 0.08), (0.38, 0.08), sides=4)


def torso():
    H.frustum("spine", "coat", (0, WAIST - 0.04, 0), (0, 2.08, 0), (0.5, 0.38), (0.6, 0.4), sides=8)
    H.frustum("spine", "coat", (0, 2.08, 0), (0, 2.26, 0), (0.6, 0.4), (0.32, 0.27), sides=8)
    H.frustum("spine", "strap", (0.36, 2.2, 0.38), (-0.4, 1.5, 0.4), (0.09, 0.04), (0.09, 0.04), sides=4)
    H.frustum("spine", "strap", (0.36, 2.2, -0.38), (-0.4, 1.5, -0.4), (0.09, 0.04), (0.09, 0.04), sides=4)
    H.frustum("pelvis", "coat_dk", (0, WAIST - 0.1, 0), (0, WAIST + 0.05, 0), (0.52, 0.4), (0.52, 0.4), sides=8)
    skirt = H.frustum("pelvis", "coat", (0, 0.56, 0), (0, WAIST - 0.06, 0), (0.66, 0.5), (0.52, 0.4), sides=8)
    H.soft(skirt, hem)


def leg(s, side):
    H.frustum(f"thigh.{side}", "bone", (s * KNEE_X, KNEE - 0.04, 0), (s * LEG_X, HIP, 0), (0.15, 0.15), (0.13, 0.13), sides=6)
    H.frustum(f"shin.{side}", "bone_dk", (s * KNEE_X, KNEE + 0.06, 0), (s * KNEE_X, KNEE - 0.08, 0), (0.17, 0.17), (0.15, 0.15), sides=6)
    H.chain(f"shin.{side}", "bone", [(s * KNEE_X, KNEE - 0.04, 0), (s * 0.38, 0.34, 0), (s * FOOT_X, ANKLE, 0)],
            [(0.14, 0.14), (0.1, 0.1), (0.13, 0.13)])
    H.frustum(f"foot.{side}", "bone", (s * FOOT_X, 0.03, -0.1), (s * FOOT_X, 0.2, -0.02), (0.18, 0.2), (0.14, 0.14), sides=6)
    H.frustum(f"foot.{side}", "bone", (s * FOOT_X, 0.09, 0.0), (s * FOOT_X, 0.07, 0.42), (0.2, 0.1), (0.24, 0.07), sides=6)


def arm(s, side, hand):
    elbow = (s * EL_X, EL_Y, 0.08)
    mid = ((elbow[0] + hand[0]) / 2 + s * 0.08, (EL_Y + hand[1]) / 2, (0.08 + hand[2]) / 2)
    H.chain(f"arm.{side}", "coat", [(s * SH_X, SH_Y + 0.05, 0), (s * 0.66, 1.9, 0.03), elbow],
            [(0.22, 0.24), (0.22, 0.23), (0.18, 0.2)])
    H.chain(f"forearm.{side}", "coat_dk", [(elbow[0], EL_Y + 0.02, 0.08), mid, (hand[0], hand[1] - 0.04, hand[2] - 0.1)],
            [(0.2, 0.2), (0.19, 0.19), (0.15, 0.15)])
    H.frustum(f"forearm.{side}", "bone", (hand[0], hand[1] - 0.14, hand[2]), (hand[0], hand[1] + 0.14, hand[2]), (0.17, 0.16), (0.18, 0.16), sides=6)


def rifle():
    butt, grip, mz, tip = 1.1, 1.75, 2.45, 3.05
    X = GUN_X
    H.frustum("forearm.L", "wood", (X, butt, gz(butt)), (X, grip, gz(grip)), (0.14, 0.17), (0.1, 0.12), sides=4)
    H.frustum("forearm.L", "steel", (X, grip, gz(grip)), (X, mz, gz(mz)), (0.11, 0.11), (0.09, 0.09), sides=6)
    H.frustum("forearm.L", "steel_lt", (X, mz, gz(mz)), (X, tip, gz(tip)), (0.11, 0.11), (0.14, 0.14), sides=6)   # muzzle brake
    H.box("forearm.L", "black", (X + 0.14, 2.45, gz(2.45)), (0.2, 0.36, 0.14))                              # scope / bipod
    H.box("forearm.L", "steel", (X + 0.2, 2.55, gz(2.5)), (0.12, 0.5, 0.1))


def lantern():
    x, y, z = 0.55, 1.1, 0.0
    H.frustum("pelvis", "black", (x, y + 0.1, z), (x, y + 0.34, z), (0.04, 0.04), (0.02, 0.02), sides=4)
    H.box("pelvis", "glow", (x, y - 0.12, z), (0.26, 0.38, 0.26))
    H.box("pelvis", "black", (x, y + 0.1, z), (0.3, 0.06, 0.3))
    H.box("pelvis", "black", (x, y - 0.34, z), (0.3, 0.06, 0.3))


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    arm(1, "L", (GUN_X + 0.02, 1.72, gz(1.72)))
    arm(-1, "R", (GUN_X - 0.06, 1.4, gz(1.4)))
    rifle()
    lantern()


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


H.build("n01L", "biped", PALETTE, make, joints())
