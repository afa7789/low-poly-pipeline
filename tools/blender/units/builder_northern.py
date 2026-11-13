"""Northern Builder (builder_northern): parka dwarf with a pickaxe over the shoulder, measured on
artifacts/model-sheets/refs/builder_northern/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/builder_northern.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "coat": 0x3A4152, "coat_lt": 0x566077, "hood": 0x2B303B, "fur": 0xDCDDE2, "beard": 0xDDEBF3,
    "goggle": 0xA9C8DA, "skin": 0xC9B79A, "belt": 0x242932, "gold": 0xE8A030, "boot": 0x363C4A,
    "boot_lt": 0x4F596C, "steel": 0x3E4658, "iron": 0x2A303A, "glove": 0x333A49,
}

HIP, KNEE, ANKLE, LEG_X = 0.95, 0.56, 0.2, 0.27
WAIST, NECK, TOP = 1.24, 1.92, 2.72
SH_X, SH_Y = 0.56, 1.8
SKIRT_MID = 0.98


def hem(p):
    """Parka skirt and fur hem follow the thigh of their side."""
    if p[1] > SKIRT_MID:
        return {"pelvis": 1.0}
    return {"pelvis": 0.45, "thigh.L" if p[0] > 0 else "thigh.R": 0.55}


def head():
    H.frustum("head", "hood", (0, 2.0, -0.12), (0, 2.72, -0.12), (0.38, 0.34), (0.2, 0.2), sides=8)
    H.frustum("head", "fur", (0, 1.96, -0.12), (0, 2.2, -0.12), (0.38, 0.36), (0.46, 0.4), sides=8)
    H.frustum("head", "fur", (0, 2.2, -0.12), (0, 2.5, -0.12), (0.46, 0.4), (0.44, 0.38), sides=8)
    H.frustum("head", "fur", (0, 2.5, -0.12), (0, 2.68, -0.12), (0.44, 0.38), (0.26, 0.24), sides=8)
    H.frustum("head", "hood", (0, 2.4, -0.3), (0, 2.66, -0.3), (0.28, 0.12), (0.18, 0.1), sides=6)
    H.frustum("head", "skin", (0, 2.1, 0.1), (0, 2.4, 0.1), (0.22, 0.24), (0.23, 0.26), sides=6)
    H.box("head", "goggle", (0, 2.3, 0.36), (0.42, 0.18, 0.1))
    H.frustum("head", "beard", (0, 2.15, 0.26), (0, 1.55, 0.36), (0.3, 0.16), (0.14, 0.12), sides=6)
    H.frustum("head", "beard", (0, 2.2, 0.2), (0, 2.0, 0.28), (0.24, 0.1), (0.3, 0.12), sides=6)


def torso():
    H.frustum("spine", "coat", (0, WAIST - 0.04, 0), (0, 1.82, 0), (0.46, 0.4), (0.54, 0.42), sides=8)
    H.frustum("spine", "coat", (0, 1.82, 0), (0, 1.98, 0), (0.54, 0.42), (0.36, 0.3), sides=8)
    H.frustum("spine", "coat_lt", (0, 1.42, 0.3), (0, 1.8, 0.3), (0.26, 0.14), (0.4, 0.14), sides=6)
    H.frustum("spine", "fur", (0, 1.86, -0.02), (0, 2.02, -0.02), (0.5, 0.42), (0.4, 0.34), sides=8)
    H.frustum("pelvis", "belt", (0, WAIST - 0.1, 0), (0, WAIST + 0.07, 0), (0.49, 0.43), (0.49, 0.43), sides=8)
    H.box("pelvis", "steel", (0, WAIST - 0.02, 0.44), (0.2, 0.15, 0.05))
    skirt = H.frustum("pelvis", "coat", (0, 0.9, 0), (0, WAIST - 0.05, 0), (0.58, 0.48), (0.5, 0.42), sides=8)
    fur = H.frustum("pelvis", "fur", (0, 0.78, 0), (0, 0.98, 0), (0.62, 0.52), (0.58, 0.48), sides=8)
    H.soft(skirt, hem)
    H.soft(fur, hem)
    H.frustum("pelvis", "boot", (0, 0.84, 0), (0, 1.12, 0), (0.4, 0.34), (0.44, 0.36), sides=8)
    # lantern on the right hip
    H.frustum("pelvis", "gold", (-0.42, 0.88, 0.3), (-0.42, 1.1, 0.3), (0.08, 0.08), (0.12, 0.12), sides=6)
    H.frustum("pelvis", "gold", (-0.42, 1.1, 0.3), (-0.42, 1.2, 0.3), (0.12, 0.12), (0.05, 0.05), sides=6)


def leg(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "boot", (s * 0.28, KNEE - 0.04, 0), (x, HIP + 0.04, 0), (0.22, 0.24), (0.27, 0.28), sides=6)
    H.box(f"thigh.{side}", "boot_lt", (s * 0.28, KNEE + 0.06, 0.24), (0.22, 0.3, 0.12))
    H.frustum(f"shin.{side}", "boot", (s * 0.28, 0.06, 0), (s * 0.28, KNEE + 0.02, 0), (0.2, 0.22), (0.27, 0.27), sides=6)
    H.frustum(f"shin.{side}", "boot_lt", (s * 0.28, 0.36, 0), (s * 0.28, 0.5, 0), (0.28, 0.28), (0.28, 0.28), sides=6)
    H.frustum(f"foot.{side}", "boot", (s * 0.28, 0.07, 0.02), (s * 0.28, 0.2, 0.3), (0.22, 0.26), (0.2, 0.18), sides=6)
    H.frustum(f"foot.{side}", "boot_lt", (s * 0.28, 0.1, 0.2), (s * 0.28, 0.12, 0.5), (0.22, 0.16), (0.19, 0.08), sides=4)
    for dz in (0.0, 0.22, 0.44):
        H.box(f"foot.{side}", "iron", (s * 0.28, 0.02, dz + 0.04), (0.38, 0.06, 0.07))


def left_arm():
    H.frustum("arm.L", "coat", (SH_X + 0.02, SH_Y + 0.05, 0), (0.76, 1.22, 0), (0.24, 0.26), (0.28, 0.27), sides=6)
    H.frustum("forearm.L", "coat", (0.76, 1.28, 0), (0.76, 1.0, 0.02), (0.28, 0.27), (0.24, 0.24), sides=6)
    H.frustum("forearm.L", "fur", (0.76, 1.2, 0.02), (0.76, 1.06, 0.02), (0.27, 0.27), (0.29, 0.29), sides=6)
    H.frustum("forearm.L", "glove", (0.76, 1.04, 0.04), (0.76, 0.76, 0.08), (0.2, 0.21), (0.27, 0.25), sides=6)


def right_arm():
    H.frustum("arm.R", "coat", (-SH_X - 0.02, SH_Y + 0.05, 0), (-0.8, 1.2, 0.08), (0.24, 0.26), (0.27, 0.26), sides=6)
    H.frustum("forearm.R", "coat", (-0.8, 1.2, 0.1), (-0.72, 1.55, 0.35), (0.27, 0.26), (0.22, 0.22), sides=6)
    H.frustum("forearm.R", "fur", (-0.74, 1.46, 0.3), (-0.72, 1.62, 0.38), (0.26, 0.26), (0.27, 0.27), sides=6)
    H.frustum("forearm.R", "glove", (-0.72, 1.6, 0.38), (-0.7, 1.92, 0.48), (0.2, 0.22), (0.27, 0.26), sides=6)
    # pickaxe: handle from the front across the right shoulder, curved head behind the left shoulder
    butt, end = (-1.08, 1.68, 0.92), (0.62, 2.35, -0.57)
    H.frustum("forearm.R", "iron", butt, end, (0.05, 0.05), (0.05, 0.05), sides=6)
    H.box("forearm.R", "steel", (-1.08, 1.68, 0.92), (0.22, 0.2, 0.32))
    H.chain("forearm.R", "steel", [(0.38, 2.66, -0.42), (0.58, 2.42, -0.55), (0.7, 2.1, -0.62), (0.76, 1.8, -0.7)],
            [(0.07, 0.08), (0.12, 0.12), (0.1, 0.1), (0.03, 0.03)], sides=6)
    H.box("forearm.R", "steel", (0.6, 2.38, -0.56), (0.18, 0.2, 0.2))


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    left_arm()
    right_arm()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * 0.76, 1.2, 0))
        out[f"forearm.{side}"] = ((s * 0.76, 1.2, 0), (s * 0.76, 0.8, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * 0.28, KNEE, 0))
        out[f"shin.{side}"] = ((s * 0.28, KNEE, 0), (s * 0.28, ANKLE, 0))
        out[f"foot.{side}"] = ((s * 0.28, ANKLE, 0), (s * 0.28, 0.06, 0.5))
    return out


H.build("builder_northern", "biped", PALETTE, make, joints())
