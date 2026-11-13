"""Lich King (u00D): measured on artifacts/model-sheets/refs/u00D/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/u00D.py -- <out.glb>

Open brown coat over a gold-plumbed skeleton, skull in a glass dome, green-canister cane in the right hand (forearm.R),
book in the left, big boots, green wisps at the feet.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "bone": 0xDCCDA8, "bone_dk": 0xB8A87E, "coat": 0x5A3A2E, "coat_dk": 0x3A241C, "boot": 0x33211A, "sole": 0x8A7550,
    "gold": 0xC09A4A, "brass": 0x9A8A62, "skull": 0xD4DCC4, "glass": 0x9CCFB8, "eye": 0x2BE35A, "green": 0x0E8A58,
    "wisp": 0x7BE0A4, "book": 0xDCCBA0, "cover": 0x8F7A55,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X, FOOT_X = 1.3, 0.8, 0.22, 0.18, 0.17, 0.2
WAIST, NECK, TOP = 1.55, 2.2, 2.72
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.4, 2.1, 0.56, 1.5, 1.0
CANE_X, CANE_Z = -0.57, 0.46
HAND_L = (0.5, 1.12, 0.06)


def hem(p):
    if p[1] > 1.3:
        return {"pelvis": 1.0}
    return {"pelvis": 0.6, "thigh.L" if p[0] > 0 else "thigh.R": 0.4}


def head():
    H.frustum("head", "coat", (0, 2.08, -0.14), (0, 2.5, -0.16), (0.46, 0.34), (0.38, 0.3), sides=8)
    H.frustum("head", "coat", (0, 2.44, -0.16), (0, 2.76, -0.2), (0.38, 0.3), (0.07, 0.07), sides=8)
    H.frustum("head", "coat_dk", (0, 2.2, -0.08), (0, 2.6, -0.08), (0.3, 0.2), (0.28, 0.2), sides=8)         # hood inside
    H.frustum("head", "skull", (0, 2.3, 0.12), (0, 2.6, 0.12), (0.2, 0.2), (0.23, 0.23), sides=8)            # skull
    H.frustum("head", "bone_dk", (0, 2.2, 0.18), (0, 2.34, 0.16), (0.1, 0.1), (0.17, 0.15), sides=6)        # jaw
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.09, 2.47, 0.33), (0.09, 0.1, 0.05))
    H.frustum("head", "glass", (0, 2.2, 0.0), (0, 2.66, 0.0), (0.3, 0.06), (0.3, 0.06), sides=8)        # dome front
    H.frustum("head", "gold", (0, 2.14, 0.1), (0, 2.2, 0.1), (0.32, 0.18), (0.34, 0.2), sides=8)          # rim
    H.frustum("head", "gold", (0, 2.62, 0.1), (0, 2.68, 0.1), (0.34, 0.2), (0.3, 0.18), sides=8)


def skeleton():
    for i, y in enumerate((1.7, 1.82, 1.94, 2.06)):                                                        # ribs
        H.frustum("spine", "bone", (0, y - 0.05, 0.02), (0, y + 0.05, 0.02), (0.26 - i * 0.02, 0.18), (0.28 - i * 0.02, 0.19), sides=8)
    H.frustum("spine", "gold", (0, 1.6, 0.0), (0, 2.1, 0.0), (0.07, 0.08), (0.09, 0.09), sides=6)          # sternum / spine plate
    H.frustum("spine", "bone_dk", (0, 1.55, -0.1), (0, 2.1, -0.1), (0.24, 0.12), (0.26, 0.12), sides=8)
    for s in (-1, 1):                                                                                      # gold pipes over shoulders
        H.frustum("spine", "gold", (s * 0.36, 2.3, 0.02), (s * 0.12, 1.84, 0.18), (0.07, 0.07), (0.06, 0.06), sides=6)
    H.frustum("pelvis", "bone", (0, HIP - 0.08, 0), (0, WAIST, 0), (0.3, 0.16), (0.24, 0.14), sides=8)
    H.frustum("pelvis", "bone_dk", (0, HIP - 0.24, 0.02), (0, HIP, 0.02), (0.1, 0.1), (0.3, 0.16), sides=6)
    H.frustum("pelvis", "coat_dk", (0, 0.8, 0.1), (0, HIP - 0.02, 0.1), (0.14, 0.04), (0.18, 0.05), sides=4)  # loincloth


def coat():
    for s in (-1, 1):
        low = H.frustum("pelvis", "coat", (s * 0.35, 0.55, 0.06), (s * 0.35, 1.5, 0.04), (0.17, 0.28), (0.16, 0.24), sides=6)
        H.soft(low, hem)
        H.frustum("spine", "coat", (s * 0.38, 1.45, 0.04), (s * 0.38, 2.1, 0.02), (0.16, 0.25), (0.2, 0.24), sides=6)
    low = H.frustum("pelvis", "coat", (0, 0.55, -0.22), (0, 1.5, -0.18), (0.5, 0.1), (0.46, 0.1), sides=6)
    H.soft(low, hem)
    H.frustum("spine", "coat", (0, 1.45, -0.18), (0, 2.18, -0.16), (0.46, 0.1), (0.5, 0.1), sides=6)
    H.frustum("spine", "coat", (0, 2.0, -0.18), (0, 2.5, -0.2), (0.36, 0.14), (0.26, 0.12), sides=6)       # tall collar


def leg(s, side):
    k, f = s * KNEE_X, s * FOOT_X
    H.frustum(f"thigh.{side}", "bone", (k, KNEE + 0.02, 0), (s * LEG_X, HIP, 0), (0.1, 0.1), (0.13, 0.13), sides=6)
    H.frustum(f"thigh.{side}", "bone_dk", (k, KNEE - 0.06, 0.02), (k, KNEE + 0.1, 0.02), (0.14, 0.14), (0.12, 0.12), sides=6)
    H.frustum(f"shin.{side}", "bone", (f, ANKLE + 0.1, 0), (k, KNEE, 0), (0.09, 0.09), (0.12, 0.12), sides=6)
    H.frustum(f"shin.{side}", "boot", (f, 0.04, 0), (f, 0.5, 0), (0.17, 0.2), (0.2, 0.22), sides=6)       # boot shaft, flares at the top
    H.frustum(f"foot.{side}", "boot", (f, 0.04, -0.14), (f, 0.2, 0.2), (0.2, 0.18), (0.18, 0.16), sides=6)
    H.frustum(f"foot.{side}", "boot", (f, 0.08, 0.1), (f, 0.1, 0.5), (0.2, 0.15), (0.16, 0.1), sides=6)
    H.frustum(f"foot.{side}", "sole", (f, 0.0, -0.1), (f, 0.04, 0.5), (0.2, 0.1), (0.17, 0.08), sides=6)
    H.frustum(f"foot.{side}", "wisp", (f + s * 0.12, 0.0, 0.1), (f + s * 0.2, 0.6, 0.1), (0.07, 0.03), (0.01, 0.01), sides=4)
    H.frustum(f"foot.{side}", "wisp", (f - s * 0.04, 0.0, 0.5), (f - s * 0.04, 0.4, 0.5), (0.06, 0.03), (0.01, 0.01), sides=4)


def arm_l():
    elbow = (EL_X, EL_Y, 0.04)
    H.frustum("arm.L", "coat", (0.3, 2.28, 0), (0.54, 2.0, 0), (0.2, 0.24), (0.2, 0.2), sides=6)
    H.frustum("arm.L", "coat", (0.5, 2.05, 0), elbow, (0.2, 0.2), (0.21, 0.19), sides=6)                  # sleeve
    H.frustum("forearm.L", "coat", elbow, (0.52, 1.1, 0.05), (0.22, 0.2), (0.2, 0.18), sides=6)
    H.frustum("forearm.L", "bone", (0.5, 1.2, 0.06), (0.5, 0.9, 0.06), (0.13, 0.13), (0.15, 0.14), sides=6)  # hand
    H.box("forearm.L", "book", (HAND_L[0] + 0.02, HAND_L[1] - 0.1, 0.1), (0.15, 0.44, 0.46))
    H.box("forearm.L", "cover", (HAND_L[0] + 0.1, HAND_L[1] - 0.1, 0.1), (0.04, 0.46, 0.48))


def arm_r():
    elbow = (-0.58, 1.5, 0.05)
    H.frustum("arm.R", "coat", (-0.3, 2.28, 0), (-0.52, 2.0, 0), (0.2, 0.24), (0.2, 0.2), sides=6)
    H.frustum("arm.R", "coat", (-0.5, 2.05, 0), elbow, (0.2, 0.2), (0.21, 0.19), sides=6)
    mid = (CANE_X, 1.48, 0.24)
    H.frustum("forearm.R", "coat", elbow, mid, (0.22, 0.2), (0.19, 0.18), sides=6)                       # sleeve forward
    H.frustum("forearm.R", "bone", mid, (CANE_X, 1.46, CANE_Z + 0.08), (0.12, 0.12), (0.12, 0.12), sides=6)
    H.frustum("forearm.R", "bone_dk", (CANE_X, 1.36, CANE_Z), (CANE_X, 1.62, CANE_Z), (0.16, 0.16), (0.17, 0.17), sides=6)  # fist


def cane():
    x, z = CANE_X, CANE_Z
    H.frustum("forearm.R", "brass", (x, 0.1, z), (x, 1.62, z), (0.07, 0.07), (0.06, 0.06), sides=6)
    H.frustum("forearm.R", "brass", (x, 0.04, z), (x, 0.14, z), (0.14, 0.14), (0.08, 0.08), sides=6)      # foot
    H.frustum("forearm.R", "green", (x, 0.95, z), (x, 1.36, z), (0.14, 0.14), (0.15, 0.15), sides=8)      # canister
    H.frustum("forearm.R", "brass", (x, 1.36, z), (x, 1.42, z), (0.17, 0.17), (0.17, 0.17), sides=8)
    H.frustum("forearm.R", "brass", (x, 0.9, z), (x, 0.96, z), (0.17, 0.17), (0.17, 0.17), sides=8)
    H.frustum("forearm.R", "green", (x, 1.6, z), (x, 1.72, z), (0.08, 0.08), (0.06, 0.06), sides=6)       # plunger knob
    H.frustum("forearm.R", "wisp", (x - 0.12, 0.0, z), (x - 0.18, 0.7, z), (0.07, 0.03), (0.01, 0.01), sides=4)


def make():
    head()
    skeleton()
    coat()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    arm_l()
    arm_r()
    cane()


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


H.build("u00D", "biped", PALETTE, make, joints())
