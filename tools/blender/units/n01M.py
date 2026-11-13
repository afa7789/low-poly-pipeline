"""Skeletal General (n01M): measured on artifacts/model-sheets/refs/n01M/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n01M.py -- <out.glb>

Sword upright in the right hand (forearm.R), green lantern hanging from the left hand (forearm.L), plate and cape.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "bone": 0xD8CDAE, "bone_dk": 0xB5A885, "plate": 0x73737B, "plate_dk": 0x55555C, "cape": 0x6B4630, "cape_dk": 0x3E2A20,
    "boot": 0x4A3A34, "cap": 0x5A3E2C, "cap_band": 0x2E2A2A, "eye": 0x35E04A, "black": 0x15151A, "blade": 0x8A8C94,
    "glow": 0x2FE06A, "badge": 0xC8C2B0,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X, FOOT_X = 1.25, 0.76, 0.2, 0.28, 0.4, 0.5
WAIST, NECK, TOP = 1.45, 2.14, 2.72
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.56, 2.0, 0.72, 1.55, 1.1
SWORD_X, SWORD_Z = -0.74, 0.3
LAN_X = 0.78


def hem(p):
    if p[1] > 1.0:
        return {"pelvis": 1.0}
    return {"pelvis": 0.5, "thigh.L" if p[0] > 0 else "thigh.R": 0.5}


def head():
    H.frustum("head", "bone", (0, 2.2, 0.03), (0, 2.52, 0.03), (0.21, 0.23), (0.23, 0.24), sides=8)        # skull
    H.frustum("head", "bone_dk", (0, 2.08, 0.1), (0, 2.24, 0.08), (0.1, 0.1), (0.16, 0.15), sides=6)       # jaw
    H.frustum("head", "bone", (0, 1.98, -0.02), (0, 2.14, -0.02), (0.08, 0.08), (0.11, 0.11), sides=6)     # neck
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.1, 2.38, 0.27), (0.1, 0.1, 0.04))
    H.frustum("head", "cap_band", (0, 2.5, 0), (0, 2.58, 0), (0.28, 0.29), (0.3, 0.3), sides=8)
    H.frustum("head", "cap", (0, 2.58, 0), (0, 2.72, 0), (0.3, 0.3), (0.38, 0.34), sides=8)
    H.frustum("head", "black", (0, 2.52, 0.24), (0, 2.56, 0.46), (0.22, 0.05), (0.2, 0.03), sides=4)       # visor
    H.box("head", "badge", (0, 2.62, 0.34), (0.1, 0.1, 0.03))


def torso():
    H.frustum("spine", "plate", (0, 1.64, 0), (0, 2.02, 0), (0.34, 0.27), (0.46, 0.3), sides=6)           # breastplate
    H.frustum("spine", "plate_dk", (0, 2.02, 0), (0, 2.2, 0), (0.46, 0.3), (0.28, 0.22), sides=6)
    for i, y in enumerate((1.46, 1.55)):                                                                      # rib cage bands
        H.frustum("spine", "bone" if i == 0 else "bone_dk", (0, y - 0.04, 0), (0, y + 0.06, 0), (0.28, 0.19), (0.3, 0.2), sides=8)
    H.frustum("pelvis", "bone", (0, HIP - 0.06, 0), (0, WAIST, 0), (0.3, 0.2), (0.28, 0.19), sides=8)
    H.frustum("pelvis", "bone_dk", (0, HIP - 0.2, 0.03), (0, HIP, 0.03), (0.1, 0.1), (0.3, 0.2), sides=6)    # pelvis wedge
    H.frustum("spine", "cape", (0, 2.0, -0.05), (0, 2.34, -0.12), (0.44, 0.3), (0.36, 0.26), sides=8)       # high collar


def cape():
    H.frustum("spine", "cape", (0, 1.5, -0.3), (0, 2.22, -0.26), (0.66, 0.05), (0.6, 0.05), sides=4)
    low = H.frustum("pelvis", "cape", (0, 0.44, -0.46), (0, 1.5, -0.3), (0.9, 0.05), (0.66, 0.05), sides=4)
    H.soft(low, hem)


def leg(s, side):
    k = s * KNEE_X
    H.frustum(f"thigh.{side}", "bone", (k, KNEE + 0.02, 0), (s * LEG_X, HIP, 0), (0.12, 0.12), (0.12, 0.12), sides=6)
    H.frustum(f"thigh.{side}", "bone_dk", (k, KNEE - 0.04, 0.02), (k, KNEE + 0.12, 0.02), (0.17, 0.17), (0.14, 0.14), sides=6)  # knee
    H.frustum(f"shin.{side}", "plate", (s * 0.44, ANKLE + 0.06, 0), (k, KNEE + 0.04, 0.02), (0.17, 0.19), (0.25, 0.25), sides=6)  # greave
    H.frustum(f"shin.{side}", "plate_dk", (k, KNEE - 0.2, 0.2), (k, KNEE + 0.1, 0.22), (0.17, 0.05), (0.2, 0.05), sides=4)
    f = s * FOOT_X
    H.frustum(f"foot.{side}", "boot", (f, 0.03, -0.12), (f, ANKLE + 0.12, -0.04), (0.24, 0.24), (0.2, 0.2), sides=6)
    H.frustum(f"foot.{side}", "boot", (f, 0.1, 0.0), (f, 0.09, 0.48), (0.25, 0.14), (0.22, 0.09), sides=6)


def arm(s, side, hand, bracer):
    elbow = (s * EL_X, EL_Y, 0.06)
    H.frustum(f"arm.{side}", "plate", (s * 0.34, 2.28, 0), (s * 0.7, 1.96, 0), (0.22, 0.3), (0.26, 0.32), sides=6)       # pauldron
    H.frustum(f"arm.{side}", "plate_dk", (s * 0.4, 2.12, 0), (s * 0.7, 1.86, 0), (0.2, 0.3), (0.24, 0.3), sides=6)
    H.chain(f"arm.{side}", "bone", [(s * SH_X, SH_Y + 0.02, 0), (s * 0.66, 1.78, 0.03), elbow],
            [(0.1, 0.1), (0.11, 0.11), (0.13, 0.13)])
    mid = ((elbow[0] + hand[0]) / 2, (EL_Y + hand[1]) / 2, (0.06 + hand[2]) / 2)
    H.chain(f"forearm.{side}", "bone", [(elbow[0], EL_Y + 0.02, 0.06), mid, (hand[0], hand[1] - 0.06, hand[2] - 0.06)],
            [(0.11, 0.11), (0.1, 0.1), (0.1, 0.1)])
    H.frustum(f"forearm.{side}", "plate_dk", (elbow[0], EL_Y - 0.02, 0.06), mid, bracer, (bracer[0] - 0.02, bracer[1] - 0.02), sides=6)
    H.frustum(f"forearm.{side}", "bone", (hand[0], hand[1] - 0.14, hand[2]), (hand[0], hand[1] + 0.12, hand[2]), (0.16, 0.15), (0.17, 0.15), sides=6)


def sword():
    x, z = SWORD_X, SWORD_Z
    H.frustum("forearm.R", "black", (x, 1.5, z), (x, 1.78, z), (0.06, 0.06), (0.06, 0.06), sides=6)      # grip
    H.box("forearm.R", "black", (x, 1.82, z), (0.36, 0.07, 0.1))                                           # guard
    H.frustum("forearm.R", "blade", (x, 1.85, z), (x, 2.55, z), (0.09, 0.03), (0.08, 0.025), sides=4)
    H.frustum("forearm.R", "blade", (x, 2.55, z), (x, 3.05, z), (0.08, 0.025), (0.01, 0.01), sides=4)


def lantern():
    x, z = LAN_X, 0.12
    H.frustum("forearm.L", "black", (x, 1.22, z), (x, 1.34, z), (0.09, 0.05), (0.03, 0.03), sides=4)
    H.box("forearm.L", "glow", (x, 0.86, z), (0.32, 0.44, 0.3))
    H.box("forearm.L", "black", (x, 1.1, z), (0.36, 0.06, 0.34))
    H.box("forearm.L", "black", (x, 0.62, z), (0.36, 0.06, 0.34))


def make():
    head()
    torso()
    cape()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    arm(1, "L", (LAN_X, 1.28, 0.12), (0.17, 0.17))
    arm(-1, "R", (SWORD_X, 1.72, SWORD_Z), (0.17, 0.17))
    sword()
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


H.build("n01M", "biped", PALETTE, make, joints())
