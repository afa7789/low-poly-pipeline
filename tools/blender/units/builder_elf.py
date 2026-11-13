"""Elf Hooded Ranger Builder (builder_elf): medido em artifacts/model-sheets/refs/builder_elf/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/builder_elf.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "coat": 0x8A6A32, "coat_dk": 0x6E5426, "teal": 0x1F5A5E, "sash": 0x3AA0DC, "skin": 0xD9AE86,
    "boot": 0x8A6428, "boot_dk": 0x5E4318, "wood": 0x7F5E22, "brass": 0xC09A30, "paper": 0xE2D3AC,
    "book": 0x6A4A28, "lens": 0x5BB0E0, "eye": 0x6FD0FF, "strap": 0x4A3418,
}

HIP, KNEE, ANKLE, LEG_X = 1.12, 0.62, 0.14, 0.17
WAIST, NECK, TOP = 1.66, 2.26, 2.72
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.40, 2.14, 0.5, 1.62, 1.25
STAFF_X, STAFF_Z = 0.62, 0.42


def hem(p):
    if p[1] > 1.2:
        return {"pelvis": 1.0}
    return {"pelvis": 0.4, "thigh.L" if p[0] > 0 else "thigh.R": 0.6}


def head():
    H.frustum("head", "skin", (0, 2.3, 0.02), (0, 2.66, 0.02), (0.1, 0.13), (0.17, 0.19), sides=6)
    H.frustum("head", "skin", (0, 2.4, 0.02), (0, 2.5, 0.2), (0.07, 0.04), (0.03, 0.03), sides=4)     # nariz
    H.frustum("head", "strap", (0, 2.58, 0), (0, 2.64, 0), (0.2, 0.21), (0.2, 0.21), sides=8)        # faixa dos óculos
    for s in (-1, 1):
        H.frustum("head", "skin", (s * 0.14, 2.5, 0), (s * 0.46, 2.7, -0.04), (0.04, 0.1), (0.01, 0.02), sides=4)  # orelha
        H.frustum("head", "brass", (s * 0.08, 2.67, 0.1), (s * 0.08, 2.67, 0.2), (0.07, 0.07), (0.075, 0.075), sides=6)
        H.frustum("head", "lens", (s * 0.08, 2.67, 0.2), (s * 0.08, 2.67, 0.215), (0.05, 0.05), (0.05, 0.05), sides=6)
        H.box("head", "eye", (s * 0.075, 2.5, 0.17), (0.07, 0.03, 0.03))
    H.frustum("head", "coat", (0, 2.2, 0), (0, 2.34, 0), (0.22, 0.2), (0.3, 0.24), sides=8)           # gola alta
    H.frustum("head", "coat", (0, 2.34, -0.02), (0, 2.44, -0.1), (0.3, 0.1), (0.25, 0.08), sides=4)


def torso():
    H.frustum("spine", "coat", (0, WAIST - 0.04, 0), (0, SH_Y + 0.02, 0), (0.3, 0.21), (0.4, 0.23), sides=8)
    H.frustum("spine", "coat", (0, SH_Y, 0), (0, NECK, 0), (0.4, 0.23), (0.2, 0.17), sides=8)
    H.box("spine", "teal", (0, 2.18, 0.2), (0.12, 0.14, 0.05))
    for s in (-1, 1):
        H.box("spine", "teal", (s * 0.13, 1.95, 0.23), (0.08, 0.62, 0.05))
    H.frustum("pelvis", "sash", (0, WAIST - 0.12, 0), (0, WAIST + 0.1, 0), (0.34, 0.25), (0.33, 0.24), sides=8)
    skirt = H.frustum("pelvis", "coat", (0, 0.68, 0), (0, WAIST - 0.1, 0), (0.42, 0.3), (0.32, 0.23), sides=8)
    H.soft(skirt, hem)
    H.frustum("pelvis", "teal", (0, 0.68, 0.0), (0, 0.76, 0.0), (0.43, 0.31), (0.42, 0.3), sides=8)
    H.frustum("pelvis", "teal", (0, 0.9, 0), (0, 1.2, 0), (0.28, 0.22), (0.3, 0.23), sides=8)


def leg(s, side):
    kx = s * LEG_X
    H.frustum(f"thigh.{side}", "teal", (kx, KNEE - 0.02, 0), (kx, HIP + 0.04, 0), (0.11, 0.12), (0.15, 0.16), sides=6)
    H.frustum(f"shin.{side}", "boot", (kx, ANKLE, 0), (kx, KNEE + 0.04, 0), (0.13, 0.15), (0.19, 0.2), sides=6)
    H.frustum(f"shin.{side}", "boot_dk", (kx, 0.34, 0), (kx, 0.4, 0), (0.17, 0.18), (0.17, 0.18), sides=6)
    H.frustum(f"foot.{side}", "boot", (kx, 0.03, -0.05), (kx, ANKLE + 0.04, -0.05), (0.14, 0.15), (0.13, 0.14), sides=6)
    H.frustum(f"foot.{side}", "boot", (kx, 0.08, 0.0), (kx, 0.07, 0.42), (0.14, 0.1), (0.12, 0.07), sides=4)


def arm(s, side):
    H.frustum(f"arm.{side}", "coat", (s * (SH_X + 0.03), SH_Y + 0.02, 0), (s * EL_X, EL_Y, 0.04), (0.17, 0.17), (0.13, 0.13), sides=6)
    wx, wz = s * (EL_X if s < 0 else STAFF_X - 0.04), (0.1 if s < 0 else STAFF_Z - 0.04)
    H.frustum(f"forearm.{side}", "coat", (s * EL_X, EL_Y + 0.03, 0.04), (wx, WR_Y + 0.12, wz * 0.8), (0.14, 0.14), (0.13, 0.13), sides=6)
    H.frustum(f"forearm.{side}", "teal", (wx, WR_Y + 0.14, wz * 0.8), (wx, WR_Y, wz), (0.13, 0.13), (0.14, 0.14), sides=6)
    H.frustum(f"forearm.{side}", "skin", (wx, WR_Y + 0.02, wz), (wx, WR_Y - 0.18, wz + 0.02), (0.13, 0.13), (0.1, 0.1), sides=6)


def staff():
    x, z = STAFF_X, STAFF_Z
    H.chain("forearm.L", "wood", [(x, 0.5, z), (x, 1.5, z), (x, 2.4, z)], [(0.045, 0.045), (0.05, 0.05), (0.045, 0.045)], sides=6)
    H.frustum("forearm.L", "brass", (x, 0.9, z), (x, 1.0, z), (0.07, 0.07), (0.07, 0.07), sides=6)
    H.frustum("forearm.L", "brass", (x, 2.36, z), (x, 2.5, z), (0.1, 0.1), (0.13, 0.12), sides=6)
    H.frustum("forearm.L", "brass", (x, 2.5, z - 0.02), (x, 2.7, z - 0.02), (0.13, 0.08), (0.12, 0.08), sides=4)
    H.frustum("forearm.L", "brass", (x, 2.62, z), (x, 2.62, z + 0.42), (0.05, 0.05), (0.07, 0.07), sides=6)    # luneta
    H.frustum("forearm.L", "lens", (x, 2.62, z + 0.42), (x, 2.62, z + 0.45), (0.06, 0.06), (0.06, 0.06), sides=6)
    for dx, dz in ((0, 0.45), (0.38, -0.3), (-0.38, -0.3)):       # tripé
        H.frustum("forearm.L", "wood", (x, 0.58, z), (x + dx, 0.0, z + dz), (0.04, 0.04), (0.035, 0.035), sides=4)


def carry():
    H.box("forearm.R", "book", (-0.5, 1.18, 0.12), (0.12, 0.42, 0.34))
    H.box("forearm.R", "paper", (-0.5, 1.18, 0.12), (0.13, 0.36, 0.28))
    H.frustum("forearm.R", "paper", (-0.42, 1.55, -0.12), (-0.42, 1.55, 0.34), (0.08, 0.08), (0.08, 0.08), sides=8)   # pergaminhos


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        arm(s, side)
    staff()
    carry()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * SH_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("builder_elf", "biped", PALETTE, make, joints())
