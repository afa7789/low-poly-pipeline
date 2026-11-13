"""Sorceress (h07B): medido em artifacts/model-sheets/refs/h07B/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/h07B.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "dress": 0x7E1220, "dress_dk": 0x4A0A14, "gold": 0xE0A82E, "purple": 0xA3268F, "skin": 0xF0B890,
    "hair": 0x72301C, "shoe": 0x9A4A28, "copper": 0xC8652E, "staff": 0x6E5A2E, "crystal": 0x35C6E8,
    "eye": 0xC8F020,
}

HIP, KNEE, ANKLE, LEG_X = 1.2, 0.75, 0.3, 0.12
WAIST, NECK, TOP = 1.65, 2.2, 2.7
SH_X, SH_Y = 0.26, 2.1
EL_L, WR_L = (0.4, 1.85, 0.0), (0.53, 1.75, 0.04)
EL_R, WR_R = (-0.37, 1.8, 0.0), (-0.5, 1.47, 0.0)
STAFF = (0.57, 0.05)       # x, z do cajado na mão esquerda
SKIRT_MID = 1.0


def hem(p):
    """A barra do vestido acompanha a coxa do seu lado."""
    if p[1] > SKIRT_MID:
        return {"pelvis": 1.0}
    return {"pelvis": 0.5, "thigh.L" if p[0] > 0 else "thigh.R": 0.5}


def head():
    H.frustum("head", "skin", (0, 2.14, 0), (0, 2.3, 0), (0.06, 0.06), (0.06, 0.06), sides=6)
    H.frustum("head", "skin", (0, 2.28, 0.01), (0, 2.62, 0.01), (0.1, 0.11), (0.11, 0.12), sides=6)
    H.frustum("head", "hair", (0, 2.3, -0.05), (0, 2.68, -0.04), (0.19, 0.16), (0.14, 0.13), sides=6)
    H.frustum("head", "hair", (0, 2.25, -0.13), (0, 2.5, -0.13), (0.17, 0.07), (0.17, 0.07), sides=6)
    H.box("head", "purple", (0, 2.45, 0.115), (0.3, 0.1, 0.04))
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.07, 2.45, 0.14), (0.07, 0.04, 0.02))
        H.frustum("head", "skin", (s * 0.1, 2.45, 0), (s * 0.28, 2.54, 0), (0.035, 0.035), (0.005, 0.005), sides=4)
        H.frustum("head", "gold", (s * 0.12, 2.52, 0.1), (s * 0.2, 2.66, 0.09), (0.035, 0.03), (0.005, 0.005), sides=4)
    H.frustum("head", "gold", (0, 2.58, 0.09), (0, 2.66, 0.09), (0.05, 0.025), (0.005, 0.005), sides=4)
    H.frustum("head", "gold", (0, 2.57, 0), (0, 2.62, 0), (0.125, 0.13), (0.125, 0.13), sides=6)


def torso():
    H.frustum("spine", "dress", (0, WAIST - 0.03, 0), (0, 1.95, 0), (0.17, 0.13), (0.2, 0.15), sides=8)
    H.frustum("spine", "dress", (0, 1.95, 0), (0, 2.18, 0), (0.2, 0.15), (0.12, 0.09), sides=8)
    H.frustum("spine", "gold", (0, 2.14, 0), (0, 2.2, 0), (0.12, 0.1), (0.1, 0.09), sides=8)
    H.frustum("spine", "hair", (0, 1.68, -0.13), (0, 2.3, -0.11), (0.14, 0.05), (0.2, 0.08), sides=6)
    H.frustum("spine", "hair", (0, 1.62, -0.14), (0, 1.7, -0.13), (0.02, 0.02), (0.1, 0.05), sides=4)


def skirt():
    H.frustum("pelvis", "gold", (0, WAIST - 0.06, 0), (0, WAIST + 0.06, 0), (0.19, 0.15), (0.19, 0.15), sides=8)
    low = H.frustum("pelvis", "dress", (0, 0.42, -0.15), (0, 1.0, -0.06), (0.6, 0.42), (0.3, 0.24), sides=8)
    H.soft(low, hem)
    mid = H.frustum("pelvis", "dress", (0, 1.0, -0.06), (0, WAIST - 0.02, 0), (0.3, 0.24), (0.19, 0.15), sides=8)
    H.soft(mid, hem)
    rim = H.frustum("pelvis", "gold", (0, 0.38, -0.15), (0, 0.46, -0.15), (0.62, 0.44), (0.6, 0.42), sides=8)
    H.soft(rim, hem)
    sash = H.box("pelvis", "purple", (0, 1.15, 0.2), (0.1, 0.9, 0.02))
    H.soft(sash, hem)


def leg(s, side):
    kx = s * LEG_X
    H.frustum(f"thigh.{side}", "skin", (kx, KNEE - 0.04, 0), (kx, HIP + 0.04, 0), (0.07, 0.075), (0.11, 0.11), sides=6)
    H.frustum(f"shin.{side}", "skin", (kx, ANKLE - 0.02, 0), (kx, KNEE + 0.02, 0), (0.05, 0.055), (0.08, 0.085), sides=6)
    H.frustum(f"foot.{side}", "shoe", (kx, ANKLE + 0.04, -0.02), (kx, 0.06, 0.2), (0.075, 0.08), (0.085, 0.07), sides=6)


def right_arm():
    H.frustum("arm.R", "dress", (-SH_X, SH_Y + 0.02, 0), (EL_R[0], EL_R[1], 0), (0.12, 0.12), (0.09, 0.09), sides=6)
    H.frustum("forearm.R", "dress", (EL_R[0], EL_R[1] + 0.02, 0), (WR_R[0], WR_R[1] + 0.04, 0), (0.095, 0.095), (0.1, 0.095), sides=6)
    H.frustum("forearm.R", "gold", (WR_R[0] + 0.01, WR_R[1] + 0.08, 0), (WR_R[0], WR_R[1] + 0.02, 0), (0.07, 0.07), (0.075, 0.075), sides=6)
    H.frustum("forearm.R", "skin", (WR_R[0], WR_R[1] + 0.02, 0), (-0.66, 1.3, 0.02), (0.08, 0.04), (0.12, 0.03), sides=4)


def left_arm():
    H.frustum("arm.L", "dress", (SH_X, SH_Y + 0.02, 0), EL_L, (0.12, 0.12), (0.09, 0.09), sides=6)
    H.frustum("forearm.L", "dress", (EL_L[0], EL_L[1] + 0.02, 0), WR_L, (0.08, 0.08), (0.095, 0.09), sides=6)
    H.frustum("forearm.L", "gold", (0.5, 1.78, 0.03), (0.55, 1.74, 0.04), (0.075, 0.075), (0.08, 0.08), sides=6)
    H.frustum("forearm.L", "skin", (STAFF[0], 1.64, STAFF[1]), (STAFF[0], 1.84, STAFF[1]), (0.095, 0.09), (0.09, 0.09), sides=6)


def staff():
    x, z = STAFF
    f = "forearm.L"
    H.frustum(f, "staff", (x, 0.4, z), (x, 2.3, z), (0.035, 0.035), (0.04, 0.04), sides=6)
    H.frustum(f, "staff", (x, 2.3, z), (x - 0.03, 2.4, z), (0.04, 0.04), (0.03, 0.03), sides=6)
    for y in (2.38, 2.46, 2.54):
        H.frustum(f, "copper", (x, y, z), (x, y + 0.05, z), (0.16, 0.16), (0.14, 0.14), sides=8)
    H.frustum(f, "crystal", (x, 2.42, z), (x, 2.58, z), (0.06, 0.06), (0.09, 0.09), sides=6)
    H.frustum(f, "crystal", (x, 2.58, z), (x, 2.72, z), (0.09, 0.09), (0.005, 0.005), sides=6)


def make():
    head()
    torso()
    skirt()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    right_arm()
    left_arm()
    staff()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.07, 0.2))
    out["arm.L"] = ((SH_X, SH_Y, 0), EL_L)
    out["forearm.L"] = (EL_L, WR_L)
    out["arm.R"] = ((-SH_X, SH_Y, 0), EL_R)
    out["forearm.R"] = (EL_R, WR_R)
    return out


H.build("h07B", "biped", PALETTE, make, joints())
