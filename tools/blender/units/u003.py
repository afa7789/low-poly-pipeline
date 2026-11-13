"""Greater Skeletal Mage (u003): measured on artifacts/model-sheets/refs/u003/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/u003.py -- <out.glb>

Hooded skeleton in a flared robe with big shoulder plates, two hands on a forked staff (forearm.R), pack with bottles on the back.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "robe": 0x6B4632, "robe_dk": 0x4A3022, "pad": 0x7C6D4E, "pad_dk": 0x5E523B, "bone": 0xE2D8BA, "bone_dk": 0xB9AD8A,
    "staff": 0x8C7B58, "eye": 0x35E04A, "black": 0x15151A, "pack": 0x6A5F46, "ring": 0xDDD2B2, "cork": 0x5A4A36,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X, FOOT_X = 1.2, 0.72, 0.18, 0.26, 0.28, 0.27
WAIST, NECK, TOP = 1.5, 2.16, 2.72
SH_X, SH_Y, EL_X, EL_Y = 0.5, 2.0, 0.48, 1.5
STAFF_Z = 0.34


def head():
    H.frustum("head", "bone", (0, 2.12, 0.1), (0, 2.46, 0.1), (0.2, 0.22), (0.23, 0.24), sides=8)           # skull
    H.frustum("head", "bone_dk", (0, 2.02, 0.14), (0, 2.16, 0.14), (0.1, 0.1), (0.17, 0.16), sides=6)      # jaw
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.1, 2.32, 0.33), (0.1, 0.1, 0.05))
    H.chain("head", "robe", [(0, 2.0, -0.1), (0, 2.3, -0.12), (0, 2.55, -0.1), (0, 2.76, -0.06)],
            [(0.4, 0.36), (0.36, 0.36), (0.25, 0.26), (0.03, 0.03)])                                     # hood
    H.frustum("head", "robe_dk", (0, 2.4, 0.2), (0, 2.56, 0.12), (0.26, 0.1), (0.14, 0.08), sides=4)      # hood brow


def torso():
    H.frustum("spine", "robe", (0, 1.5, 0), (0, 2.08, 0), (0.42, 0.3), (0.5, 0.3), sides=8)
    H.frustum("spine", "robe_dk", (0, 2.04, 0), (0, 2.22, 0), (0.5, 0.3), (0.3, 0.24), sides=8)           # collar
    H.chain("pelvis", "robe", [(0, 0.34, 0), (0, 0.9, 0), (0, 1.5, 0)], [(0.5, 0.36), (0.42, 0.32), (0.36, 0.28)], sides=8)
    H.frustum("pelvis", "robe_dk", (0, 0.34, 0.2), (0, 1.1, 0.26), (0.06, 0.1), (0.05, 0.08), sides=4)    # front seam


def pack():
    H.frustum("spine", "pack", (0, 1.46, -0.38), (0, 2.02, -0.38), (0.3, 0.16), (0.32, 0.17), sides=6)
    H.frustum("spine", "pad_dk", (0, 1.9, -0.38), (0, 2.04, -0.38), (0.32, 0.18), (0.3, 0.16), sides=6)
    for s in (-1, 1):
        x = s * 0.16
        H.frustum("spine", "cork", (x, 2.0, -0.38), (x, 2.2, -0.38), (0.07, 0.07), (0.06, 0.06), sides=6)
        for y in (2.04, 2.12):
            H.frustum("spine", "ring", (x, y, -0.38), (x, y + 0.06, -0.38), (0.11, 0.11), (0.1, 0.1), sides=6)


def leg(s, side):
    k, f = s * KNEE_X, s * FOOT_X
    H.chain(f"thigh.{side}", "bone", [(s * LEG_X, HIP, 0), (k, 0.9, 0), (k, KNEE, 0.01)], [(0.12, 0.12), (0.1, 0.1), (0.1, 0.1)], sides=6)
    H.chain(f"shin.{side}", "bone", [(k, KNEE + 0.02, 0.01), (s * 0.27, 0.45, 0), (f, ANKLE + 0.06, 0)], [(0.1, 0.1), (0.09, 0.09), (0.1, 0.1)], sides=6)
    H.frustum(f"foot.{side}", "bone_dk", (f, 0.03, -0.1), (f, 0.14, -0.04), (0.2, 0.2), (0.16, 0.16), sides=6)
    H.frustum(f"foot.{side}", "bone", (f, 0.08, 0.0), (f, 0.07, 0.42), (0.2, 0.14), (0.19, 0.08), sides=6)


def arm(s, side, hand):
    H.frustum(f"arm.{side}", "pad", (s * 0.36, 2.32, 0), (s * 0.56, 2.04, 0), (0.17, 0.3), (0.19, 0.32), sides=6)    # pauldron
    H.frustum(f"arm.{side}", "pad_dk", (s * 0.42, 2.16, 0), (s * 0.58, 1.9, 0), (0.16, 0.3), (0.18, 0.3), sides=6)
    H.chain(f"arm.{side}", "robe", [(s * 0.46, 2.0, 0), (s * 0.54, 1.72, 0.02), (s * 0.58, 1.3, 0.04)],
            [(0.14, 0.18), (0.2, 0.2), (0.12, 0.16)], sides=6)                                                 # bell sleeve
    H.chain(f"forearm.{side}", "bone", [(s * 0.46, 1.52, 0.1), (s * 0.26, hand[1] - 0.02, 0.24), (s * 0.12, hand[1], hand[2] - 0.04)],
            [(0.11, 0.11), (0.1, 0.1), (0.1, 0.1)], sides=6)
    H.frustum(f"forearm.{side}", "bone_dk", (s * 0.5, 1.54, 0.08), (s * 0.34, hand[1] - 0.02, 0.2), (0.13, 0.13), (0.16, 0.15), sides=6)
    H.frustum(f"forearm.{side}", "bone", (s * 0.12, hand[1] - 0.12, hand[2]), (s * 0.04, hand[1] + 0.12, hand[2]), (0.15, 0.14), (0.15, 0.14), sides=6)  # fist


def staff():
    z = STAFF_Z
    H.frustum("forearm.R", "staff", (0, 0.69, z), (0, 2.46, z), (0.06, 0.06), (0.07, 0.07), sides=6)
    H.box("forearm.R", "staff", (0, 2.36, z), (0.46, 0.08, 0.1))
    for s in (-1, 1):
        H.chain("forearm.R", "staff", [(s * 0.2, 2.34, z), (s * 0.26, 2.5, z), (s * 0.3, 2.66, z)], [(0.05, 0.05), (0.05, 0.05), (0.045, 0.045)], sides=6)


def make():
    head()
    torso()
    pack()
    for s, side, y in ((1, "L", 1.5), (-1, "R", 1.7)):
        leg(s, side)
        arm(s, side, (s * 0.04, y, STAFF_Z))
    staff()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0.08))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0.08), (s * EL_X, 1.0, 0.08))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * KNEE_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * FOOT_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * FOOT_X, ANKLE, 0), (s * FOOT_X, 0.06, 0.5))
    return out


H.build("u003", "biped", PALETTE, make, joints())
