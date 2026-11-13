"""Necromancer (u005): measured on artifacts/model-sheets/refs/u005/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/u005.py -- <out.glb>

Stooped old man in a tattered hooded coat, cane with a green lantern in the right hand (forearm.R), book under the left hand (forearm.L).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "robe": 0x5E3A30, "robe_dk": 0x3A2420, "skin": 0xDCC4A8, "skin_dk": 0xB89E84, "pants": 0x33201C, "boot": 0x45342D,
    "sole": 0xA68B5E, "cane": 0x6A655F, "cane_dk": 0x45423E, "glow": 0x2FD47C, "cover": 0xA88A5E, "pages": 0xE6D2AE,
    "eye": 0x2B2220,
}

HIP, KNEE, ANKLE, LEG_X, FOOT_X = 1.1, 0.62, 0.18, 0.24, 0.24
WAIST, NECK, TOP = 1.42, 2.0, 2.6
CANE_X, CANE_Z = -0.58, 0.46


def head():
    H.frustum("head", "skin", (0, 2.08, 0.26), (0, 2.42, 0.28), (0.15, 0.14), (0.17, 0.15), sides=8)         # face
    H.box("head", "skin_dk", (0, 2.26, 0.43), (0.06, 0.14, 0.08))                                          # nose
    H.box("head", "eye", (0, 2.33, 0.41), (0.3, 0.05, 0.04))                                               # heavy brows
    H.chain("head", "robe", [(0, 1.96, 0.02), (0, 2.28, 0.06), (0, 2.5, 0.1), (0, 2.66, 0.02)],
            [(0.36, 0.3), (0.34, 0.3), (0.26, 0.24), (0.06, 0.06)], sides=8)                               # hood
    H.frustum("head", "robe_dk", (0, 2.1, -0.02), (0, 2.42, 0.02), (0.2, 0.2), (0.22, 0.2), sides=6)       # hood lining


def torso():
    H.frustum("spine", "robe", (0, 1.4, -0.02), (0, 2.14, 0.0), (0.4, 0.3), (0.48, 0.3), sides=8)
    H.frustum("spine", "robe", (0, 1.7, -0.24), (0, 2.1, -0.14), (0.36, 0.22), (0.4, 0.22), sides=6)          # stooped back
    H.chain("pelvis", "robe", [(0, 0.55, -0.04), (0, 0.9, -0.03), (0, 1.42, 0)], [(0.52, 0.38), (0.46, 0.34), (0.4, 0.29)], sides=8)
    H.frustum("pelvis", "robe_dk", (0, 0.5, 0.3), (0, 0.8, 0.3), (0.2, 0.05), (0.14, 0.04), sides=4)       # torn hem
    for x in (-0.3, 0.3):
        H.frustum("pelvis", "robe_dk", (x, 0.46, -0.04), (x, 0.62, -0.04), (0.1, 0.38), (0.16, 0.38), sides=4)


def leg(s, side):
    k, f = (s * 0.25, KNEE, 0.02), s * FOOT_X
    H.chain(f"thigh.{side}", "pants", [(s * LEG_X, HIP, 0), (s * 0.25, 0.85, 0), k], [(0.13, 0.13), (0.11, 0.11), (0.1, 0.1)], sides=6)
    H.frustum(f"shin.{side}", "pants", (k[0], KNEE, 0.02), (f, 0.44, 0.0), (0.1, 0.1), (0.1, 0.1), sides=6)
    H.frustum(f"shin.{side}", "boot", (f, 0.12, 0.0), (f, 0.46, 0.0), (0.16, 0.16), (0.2, 0.19), sides=6)      # boot shaft
    H.frustum(f"foot.{side}", "boot", (f, 0.08, -0.14), (f, 0.2, -0.06), (0.18, 0.2), (0.17, 0.17), sides=6)
    H.frustum(f"foot.{side}", "boot", (f, 0.1, 0.0), (f, 0.1, 0.42), (0.19, 0.15), (0.18, 0.1), sides=6)
    H.frustum(f"foot.{side}", "sole", (f, 0.0, -0.14), (f, 0.06, 0.42), (0.19, 0.2), (0.18, 0.12), sides=6)


def arm_l():
    H.chain("arm.L", "robe", [(0.4, 2.1, 0), (0.5, 1.8, 0), (0.54, 1.45, 0.0)], [(0.18, 0.2), (0.17, 0.2), (0.16, 0.18)], sides=6)
    H.chain("forearm.L", "robe", [(0.54, 1.5, 0), (0.55, 1.35, 0.0), (0.56, 1.22, 0.0)], [(0.16, 0.17), (0.15, 0.16), (0.14, 0.14)], sides=6)
    H.frustum("forearm.L", "skin", (0.57, 1.2, 0.0), (0.58, 1.0, 0.04), (0.12, 0.1), (0.13, 0.1), sides=6)    # hand
    H.box("forearm.L", "cover", (0.52, 1.1, 0.04), (0.16, 0.4, 0.5))                                     # book
    H.box("forearm.L", "pages", (0.52, 1.1, 0.04), (0.12, 0.36, 0.46))
    H.box("forearm.L", "cover", (0.6, 1.1, 0.04), (0.04, 0.42, 0.52))


def arm_r():
    H.chain("arm.R", "robe", [(-0.4, 2.1, 0), (-0.52, 1.82, 0), (-0.6, 1.55, 0.0)], [(0.18, 0.2), (0.17, 0.2), (0.16, 0.18)], sides=6)
    H.chain("forearm.R", "robe", [(-0.6, 1.58, 0.0), (-0.59, 1.5, 0.2), (-0.58, 1.42, 0.36)], [(0.17, 0.17), (0.15, 0.15), (0.14, 0.14)], sides=6)
    H.frustum("forearm.R", "skin", (CANE_X, 1.28, CANE_Z - 0.04), (CANE_X, 1.54, CANE_Z - 0.04), (0.13, 0.14), (0.15, 0.14), sides=6)   # hand on cane


def cane():
    x, z = CANE_X, CANE_Z
    H.chain("forearm.R", "cane", [(x, 0.04, z), (x, 0.7, z), (x, 1.5, z)], [(0.06, 0.06), (0.04, 0.04), (0.045, 0.045)], sides=6)
    H.frustum("forearm.R", "cane_dk", (x, 0.0, z), (x, 0.1, z), (0.05, 0.05), (0.07, 0.07), sides=6)       # ferrule
    H.box("forearm.R", "glow", (x, 1.04, z), (0.2, 0.3, 0.2))                                              # lantern
    for y in (0.87, 1.21):
        H.box("forearm.R", "cane_dk", (x, y, z), (0.25, 0.06, 0.25))
    H.box("forearm.R", "cane", (x, 1.56, z), (0.12, 0.08, 0.1))


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    arm_l()
    arm_r()
    cane()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0.05)),
           "head": ((0, NECK, 0.05), (0, TOP, 0.12)),
           "arm.L": ((0.42, 2.02, 0), (0.54, 1.48, 0)), "forearm.L": ((0.54, 1.48, 0), (0.56, 1.0, 0)),
           "arm.R": ((-0.42, 2.02, 0), (-0.6, 1.56, 0)), "forearm.R": ((-0.6, 1.56, 0), (-0.58, 1.1, 0.4))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * 0.25, KNEE, 0.02))
        out[f"shin.{side}"] = ((s * 0.25, KNEE, 0.02), (s * FOOT_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * FOOT_X, ANKLE, 0), (s * FOOT_X, 0.06, 0.45))
    return out


H.build("u005", "biped", PALETTE, make, joints())
