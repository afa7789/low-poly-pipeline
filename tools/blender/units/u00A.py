"""Skeletal Mage (u00A): measured on artifacts/model-sheets/refs/u00A/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/u00A.py -- <out.glb>

Hooded brown poncho over a skeleton, gas-mask canister on the chest, tall staff with a green lantern in the right hand (forearm.R).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "bone": 0xDDD2B4, "bone_dk": 0xB8AA84, "robe": 0x74492E, "robe_dk": 0x573621, "void": 0x0E0A0A,
    "eye": 0x2BE35A, "brass": 0x8A6A32, "wood": 0x2E1F1A, "glow": 0x2FE06A, "glass": 0x9FD8C0, "mask": 0xCFC4A4,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X, FOOT_X = 1.2, 0.72, 0.12, 0.24, 0.24, 0.24
WAIST, NECK, TOP = 1.5, 2.16, 2.72
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.46, 2.0, 0.56, 1.5, 1.05
STAFF_X, STAFF_Z = -0.62, 0.45
HAND_R = (STAFF_X, 1.85, STAFF_Z)


def hem(p):
    if p[1] > 1.0:
        return {"pelvis": 1.0}
    return {"pelvis": 0.5, "thigh.L" if p[0] > 0 else "thigh.R": 0.5}


def hood():
    H.frustum("head", "robe", (0, 2.0, -0.02), (0, 2.46, -0.04), (0.46, 0.42), (0.38, 0.36), sides=8)
    H.frustum("head", "robe", (0, 2.4, -0.04), (0, 2.76, -0.12), (0.38, 0.36), (0.06, 0.06), sides=8)       # peak
    H.frustum("head", "robe_dk", (0, 2.1, 0.0), (0, 2.5, 0.02), (0.36, 0.2), (0.28, 0.2), sides=8)
    H.frustum("head", "void", (0, 2.1, 0.14), (0, 2.52, 0.12), (0.26, 0.1), (0.22, 0.1), sides=8)         # dark face opening
    H.frustum("head", "bone", (0, 2.2, 0.0), (0, 2.5, 0.0), (0.16, 0.16), (0.18, 0.18), sides=8)          # skull inside
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.1, 2.38, 0.28), (0.09, 0.1, 0.05))


def body():
    H.frustum("pelvis", "robe", (0, 0.56, 0), (0, 1.1, 0), (0.78, 0.6), (0.54, 0.44), sides=8)           # flared hem
    H.frustum("pelvis", "robe_dk", (0, 0.5, 0), (0, 0.66, 0), (0.8, 0.62), (0.78, 0.6), sides=8)       # ragged edge
    H.frustum("pelvis", "robe", (0, 1.05, 0), (0, WAIST, 0), (0.54, 0.44), (0.4, 0.34), sides=8)
    H.frustum("spine", "robe", (0, 1.45, 0), (0, 2.0, 0), (0.4, 0.34), (0.5, 0.38), sides=8)
    H.frustum("spine", "robe_dk", (0, 1.95, 0), (0, 2.2, 0), (0.6, 0.4), (0.3, 0.26), sides=8)           # shoulders / collar
    H.frustum("spine", "robe", (0, 1.5, -0.2), (0, 2.1, -0.24), (0.52, 0.12), (0.46, 0.1), sides=6)      # cape back fall
    H.frustum("spine", "mask", (0, 1.78, 0.2), (0, 1.78, 0.44), (0.2, 0.2), (0.17, 0.17), sides=8)       # gas mask canister
    H.frustum("spine", "bone_dk", (0, 1.78, 0.42), (0, 1.78, 0.48), (0.11, 0.11), (0.09, 0.09), sides=8)
    H.frustum("spine", "mask", (0, 1.9, 0.16), (0, 2.08, 0.2), (0.1, 0.1), (0.08, 0.08), sides=6)         # filter tube


def leg(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "bone", (x, KNEE, 0), (x, HIP, 0), (0.12, 0.12), (0.15, 0.15), sides=6)
    H.frustum(f"thigh.{side}", "bone_dk", (x, KNEE - 0.06, 0.02), (x, KNEE + 0.1, 0.02), (0.14, 0.14), (0.12, 0.12), sides=6)
    H.frustum(f"shin.{side}", "bone", (x, ANKLE + 0.04, 0), (x, KNEE, 0), (0.1, 0.1), (0.13, 0.13), sides=6)
    H.frustum(f"shin.{side}", "bone", (x, ANKLE, 0), (x, ANKLE + 0.3, 0), (0.12, 0.12), (0.09, 0.09), sides=6)
    H.frustum(f"foot.{side}", "bone", (x, 0.02, -0.1), (x, 0.14, -0.02), (0.14, 0.12), (0.12, 0.1), sides=6)
    H.frustum(f"foot.{side}", "bone_dk", (x, 0.08, 0.0), (x, 0.08, 0.5), (0.15, 0.1), (0.14, 0.08), sides=6)


def left_arm():
    elbow = (EL_X, EL_Y, 0.05)
    H.frustum("arm.L", "robe", (0.3, 2.15, 0), (0.56, 1.9, 0), (0.22, 0.24), (0.2, 0.2), sides=6)        # poncho shoulder
    H.frustum("arm.L", "robe", (0.56, 1.95, 0), (0.6, 1.3, 0), (0.18, 0.18), (0.2, 0.18), sides=6)       # wide sleeve
    H.chain("forearm.L", "bone", [(0.58, 1.3, 0.05), (0.58, 1.18, 0.07), (0.57, WR_Y, 0.08)],
            [(0.1, 0.1), (0.09, 0.09), (0.08, 0.08)])
    H.frustum("forearm.L", "bone_dk", (0.57, 1.12, 0.08), (0.57, 0.84, 0.08), (0.14, 0.12), (0.12, 0.1), sides=6)   # hand
    return elbow


def right_arm():
    elbow = (-0.5, 1.62, 0.05)
    H.frustum("arm.R", "robe", (-0.34, 2.15, 0), (-0.54, 1.92, 0), (0.22, 0.24), (0.22, 0.22), sides=6)
    H.frustum("arm.R", "robe", (-0.56, 1.95, 0.02), (-0.5, 1.58, 0.05), (0.2, 0.2), (0.2, 0.18), sides=6)
    mid = (-0.56, 1.74, 0.26)
    H.chain("forearm.R", "bone", [elbow, mid, (HAND_R[0], HAND_R[1] - 0.08, HAND_R[2] - 0.08)],
            [(0.12, 0.12), (0.1, 0.1), (0.1, 0.1)])
    H.frustum("forearm.R", "robe", (-0.5, 1.6, 0.05), mid, (0.24, 0.22), (0.2, 0.18), sides=6)           # sleeve cuff
    H.frustum("forearm.R", "bone_dk", (STAFF_X, 1.74, STAFF_Z), (STAFF_X, 1.98, STAFF_Z), (0.16, 0.16), (0.17, 0.17), sides=6)  # fist


def staff():
    x, z = STAFF_X, STAFF_Z
    H.frustum("forearm.R", "wood", (x, 0.0, z), (x, 2.7, z), (0.07, 0.07), (0.06, 0.06), sides=6)
    H.frustum("forearm.R", "brass", (x, 0.0, z), (x, 0.2, z), (0.1, 0.1), (0.08, 0.08), sides=6)         # ferrule
    H.frustum("forearm.R", "brass", (x, 2.62, z), (x, 2.84, z), (0.07, 0.07), (0.14, 0.14), sides=6)     # socket
    H.frustum("forearm.R", "glass", (x, 2.82, z), (x, 3.3, z), (0.2, 0.2), (0.2, 0.2), sides=8)          # lantern frame
    H.frustum("forearm.R", "glow", (x, 2.86, z), (x, 3.26, z), (0.24, 0.24), (0.24, 0.24), sides=8)      # green core
    for y in (2.82, 2.98, 3.14):
        H.frustum("forearm.R", "wood", (x, y, z), (x, y + 0.06, z), (0.3, 0.3), (0.3, 0.3), sides=8)     # rings
    H.frustum("forearm.R", "brass", (x, 3.3, z), (x, 3.42, z), (0.22, 0.22), (0.07, 0.07), sides=8)


def make():
    hood()
    body()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    left_arm()
    right_arm()
    staff()


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


H.build("u00A", "biped", PALETTE, make, joints())
