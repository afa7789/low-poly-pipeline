"""Veteran Grunt (o004): orc in a horned steel helmet and snout mask, crossed bandoliers, kilt, one big hafted
axe in the right hand; measured on artifacts/model-sheets/refs/o004/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/o004.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "skin": 0x4F5E48, "skin_dk": 0x3F4D3B, "helm": 0x6E7078, "gold": 0xC09A4C, "horn": 0xDCCFA4, "mask": 0x7A2E28,
    "eye": 0xFF6A1E, "strap": 0x241E1D, "kilt": 0x5E2A24, "boot": 0x2A2423, "wood": 0x3C2E26, "axe": 0x7A747C,
}

HIP, KNEE, ANKLE, LEG_X = 0.98, 0.52, 0.14, 0.33
WAIST, NECK, TOP = 1.3, 2.0, 2.78
SH_X, SH_Y, EL_X, EL_Y = 0.78, 2.0, 1.02, 1.42
SKIRT_MID = 0.85


def hem(p):
    if p[1] > SKIRT_MID:
        return {"pelvis": 1.0}
    return {"pelvis": 0.45, "thigh.L" if p[0] > 0 else "thigh.R": 0.55}


def head():
    H.frustum("head", "skin", (0, 2.05, 0.05), (0, 2.3, 0.1), (0.22, 0.22), (0.28, 0.28), sides=6)          # neck / skull
    H.frustum("head", "helm", (0, 2.3, 0.08), (0, 2.52, 0.08), (0.34, 0.34), (0.32, 0.32), sides=8)
    H.frustum("head", "helm", (0, 2.5, 0.08), (0, 2.72, 0.06), (0.32, 0.32), (0.12, 0.14), sides=8)
    H.box("head", "gold", (0, 2.58, 0.28), (0.07, 0.32, 0.2))                                                # crest stripe
    H.frustum("head", "helm", (0, 2.46, 0.3), (0, 2.5, 0.5), (0.3, 0.06), (0.28, 0.05), sides=4)              # brim
    H.frustum("head", "mask", (0, 2.28, 0.28), (0, 2.1, 0.5), (0.2, 0.17), (0.14, 0.12), sides=6)            # snout mask
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.11, 2.38, 0.42), (0.1, 0.05, 0.03))
        H.chain("head", "horn", [(s * 0.3, 2.56, 0.06), (s * 0.5, 2.66, 0.06), (s * 0.56, 2.92, 0.06)],
                [(0.08, 0.08), (0.06, 0.06), (0.012, 0.012)], sides=6)
        H.chain("head", "horn", [(s * 0.16, 2.14, 0.46), (s * 0.3, 2.18, 0.64), (s * 0.3, 2.4, 0.7)],
                [(0.07, 0.07), (0.05, 0.05), (0.012, 0.012)], sides=4)


def torso():
    H.frustum("spine", "skin", (0, WAIST - 0.05, 0), (0, 1.85, 0.02), (0.5, 0.6), (0.8, 0.68), sides=8)
    H.frustum("spine", "skin_dk", (0, 1.85, 0.02), (0, 2.2, 0.06), (0.8, 0.68), (0.45, 0.45), sides=8)
    for s in (-1, 1):   # crossed bandoliers
        H.frustum("spine", "strap", (s * 0.4, 2.06, 0.64), (-s * 0.4, 1.36, 0.66), (0.1, 0.06), (0.1, 0.06), sides=4)
    H.frustum("pelvis", "skin", (0, 0.9, 0), (0, WAIST, 0), (0.46, 0.5), (0.5, 0.52), sides=8)
    H.frustum("pelvis", "strap", (0, WAIST - 0.02, 0), (0, WAIST + 0.14, 0), (0.55, 0.58), (0.55, 0.58), sides=8)
    H.box("pelvis", "gold", (0, WAIST + 0.06, 0.6), (0.24, 0.14, 0.05))
    kilt = H.frustum("pelvis", "kilt", (0, 0.55, 0), (0, WAIST - 0.02, 0), (0.54, 0.57), (0.5, 0.53), sides=8)
    H.soft(kilt, hem)


def leg(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "skin", (x, KNEE - 0.04, 0), (x, HIP + 0.06, 0), (0.26, 0.27), (0.31, 0.32), sides=6)
    H.frustum(f"shin.{side}", "skin_dk", (x, KNEE - 0.1, 0), (x, KNEE + 0.04, 0), (0.28, 0.28), (0.27, 0.27), sides=6)
    H.frustum(f"shin.{side}", "boot", (x, ANKLE - 0.02, 0), (x, KNEE - 0.1, 0), (0.28, 0.28), (0.34, 0.35), sides=6)
    H.frustum(f"foot.{side}", "skin", (x, 0.12, -0.04), (x, 0.09, 0.44), (0.3, 0.2), (0.27, 0.1), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.03, -0.18), (x, 0.03, 0.42), (0.3, 0.04), (0.27, 0.04), sides=4)


def arm(s, side):
    H.frustum(f"arm.{side}", "skin", (s * 0.64, 2.1, 0.0), (s * 0.98, 1.78, 0.02), (0.33, 0.33), (0.42, 0.4), sides=6)
    H.frustum(f"arm.{side}", "skin_dk", (s * 0.98, 1.78, 0.02), (s * EL_X, EL_Y - 0.02, 0.05), (0.42, 0.4), (0.34, 0.34), sides=6)
    H.frustum(f"forearm.{side}", "skin", (s * EL_X, EL_Y + 0.04, 0.05), (s * 0.95, 1.05, 0.08), (0.33, 0.33), (0.36, 0.36), sides=6)
    H.frustum(f"forearm.{side}", "skin_dk", (s * 0.95, 1.08, 0.08), (s * 0.9, 0.78, 0.1), (0.36, 0.36), (0.26, 0.27), sides=6)
    H.frustum(f"forearm.{side}", "skin", (s * 0.9, 0.82, 0.1), (s * 0.88, 0.58, 0.12), (0.26, 0.27), (0.32, 0.32), sides=6)
    H.frustum(f"forearm.{side}", "skin", (s * 0.88, 0.6, 0.12), (s * 0.87, 0.4, 0.12), (0.32, 0.32), (0.22, 0.2), sides=6)


def axe():
    pom, end = (-1.3, 1.0, 0.8), (-0.55, 0.4, -0.75)
    H.chain("forearm.R", "wood", [pom, end], [(0.07, 0.07), (0.065, 0.065)], sides=6)
    H.frustum("forearm.R", "axe", (-0.55, 0.4, -0.55), (-0.55, 0.4, -1.05), (0.1, 0.2), (0.12, 0.5), sides=4)
    H.frustum("forearm.R", "gold", (-0.55, 0.4, -1.03), (-0.55, 0.4, -1.1), (0.12, 0.5), (0.12, 0.52), sides=4)
    H.box("forearm.R", "axe", (-0.55, 0.42, -0.5), (0.2, 0.2, 0.2))


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        arm(s, side)
    axe()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0.04))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0.04), (s * 0.9, 0.6, 0.12))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("o004", "biped", PALETTE, make, joints())
