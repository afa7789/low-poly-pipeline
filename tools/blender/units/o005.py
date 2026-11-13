"""Axemaster (o005): lime orc in horned helm, steel pauldrons and bandolier, axe in the right hand, black
gold-edged shield on a pole in the left; measured on artifacts/model-sheets/refs/o005/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/o005.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "skin": 0xBFD21C, "skin_dk": 0xA6B818, "helm": 0x8E9298, "gold": 0xE0A830, "horn": 0xF0DDB8, "mask": 0x5A2A28,
    "eye": 0xFFE040, "leather": 0x7A4A28, "strap": 0x2C1E1A, "kilt": 0xA84820, "wood": 0x5A3322, "axe": 0x9A9EA4,
    "black": 0x1C1614,
}

HIP, KNEE, ANKLE, LEG_X = 0.98, 0.52, 0.14, 0.33
WAIST, NECK, TOP = 1.3, 2.0, 2.78
SH_X, SH_Y, EL_X, EL_Y = 0.78, 2.0, 1.0, 1.4
SKIRT_MID = 0.85


def hem(p):
    if p[1] > SKIRT_MID:
        return {"pelvis": 1.0}
    return {"pelvis": 0.45, "thigh.L" if p[0] > 0 else "thigh.R": 0.55}


def head():
    H.frustum("head", "skin", (0, 2.05, 0.05), (0, 2.3, 0.1), (0.22, 0.22), (0.28, 0.28), sides=6)
    H.frustum("head", "helm", (0, 2.3, 0.08), (0, 2.52, 0.08), (0.34, 0.34), (0.32, 0.32), sides=8)
    H.frustum("head", "helm", (0, 2.5, 0.08), (0, 2.72, 0.06), (0.32, 0.32), (0.12, 0.14), sides=8)
    H.box("head", "gold", (0, 2.58, 0.28), (0.07, 0.32, 0.2))
    H.frustum("head", "mask", (0, 2.28, 0.28), (0, 2.1, 0.5), (0.2, 0.17), (0.14, 0.12), sides=6)
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.11, 2.38, 0.42), (0.1, 0.05, 0.03))
        H.chain("head", "horn", [(s * 0.3, 2.56, 0.06), (s * 0.5, 2.66, 0.06), (s * 0.56, 2.92, 0.06)],
                [(0.08, 0.08), (0.06, 0.06), (0.012, 0.012)], sides=6)
        H.chain("head", "horn", [(s * 0.16, 2.14, 0.46), (s * 0.3, 2.18, 0.64), (s * 0.3, 2.4, 0.7)],
                [(0.07, 0.07), (0.05, 0.05), (0.012, 0.012)], sides=4)


def torso():
    H.frustum("spine", "leather", (0, WAIST - 0.05, 0), (0, 1.85, 0.02), (0.5, 0.58), (0.76, 0.66), sides=8)
    H.frustum("spine", "leather", (0, 1.85, 0.02), (0, 2.2, 0.06), (0.76, 0.66), (0.45, 0.45), sides=8)
    H.frustum("spine", "strap", (0.4, 2.1, 0.64), (-0.3, 1.4, 0.66), (0.1, 0.06), (0.1, 0.06), sides=4)
    H.frustum("spine", "strap", (-0.4, 2.1, -0.62), (0.4, 1.4, -0.62), (0.1, 0.06), (0.1, 0.06), sides=4)
    H.frustum("pelvis", "gold", (0, WAIST - 0.02, 0), (0, WAIST + 0.14, 0), (0.55, 0.58), (0.55, 0.58), sides=8)
    H.frustum("pelvis", "skin_dk", (0, 0.9, 0), (0, WAIST, 0), (0.46, 0.5), (0.5, 0.52), sides=8)
    kilt = H.frustum("pelvis", "kilt", (0, 0.55, 0), (0, WAIST - 0.02, 0), (0.54, 0.57), (0.5, 0.53), sides=8)
    H.soft(kilt, hem)


def leg(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "skin", (x, KNEE - 0.04, 0), (x, HIP + 0.06, 0), (0.3, 0.3), (0.36, 0.36), sides=6)
    H.frustum(f"shin.{side}", "skin_dk", (x, KNEE - 0.1, 0), (x, KNEE + 0.04, 0), (0.32, 0.32), (0.3, 0.3), sides=6)
    H.frustum(f"shin.{side}", "skin", (x, ANKLE - 0.02, 0), (x, KNEE - 0.1, 0), (0.3, 0.3), (0.36, 0.36), sides=6)
    H.frustum(f"foot.{side}", "skin", (x, 0.14, -0.06), (x, 0.09, 0.46), (0.34, 0.26), (0.3, 0.12), sides=6)
    H.frustum(f"foot.{side}", "skin_dk", (x, 0.03, -0.2), (x, 0.03, 0.44), (0.34, 0.04), (0.3, 0.04), sides=4)


def arm(s, side):
    H.frustum(f"arm.{side}", "skin", (s * 0.7, 2.1, 0.0), (s * 0.98, 1.78, 0.02), (0.3, 0.3), (0.38, 0.36), sides=6)
    H.frustum(f"arm.{side}", "kilt", (s * 0.98, 1.8, 0.02), (s * EL_X, EL_Y - 0.02, 0.05), (0.38, 0.36), (0.36, 0.36), sides=6)
    H.frustum(f"arm.{side}", "helm", (s * 0.55, 2.28, 0.0), (s * 1.0, 1.95, 0.0), (0.3, 0.46), (0.36, 0.46), sides=6)   # pauldron
    H.frustum(f"forearm.{side}", "kilt", (s * EL_X, EL_Y + 0.04, 0.05), (s * 0.95, 1.05, 0.08), (0.36, 0.36), (0.38, 0.38), sides=6)
    H.frustum(f"forearm.{side}", "skin", (s * 0.95, 1.08, 0.08), (s * 0.9, 0.78, 0.1), (0.3, 0.3), (0.24, 0.25), sides=6)
    H.frustum(f"forearm.{side}", "skin", (s * 0.9, 0.82, 0.1), (s * 0.88, 0.58, 0.12), (0.26, 0.27), (0.32, 0.32), sides=6)
    H.frustum(f"forearm.{side}", "skin", (s * 0.88, 0.6, 0.12), (s * 0.87, 0.4, 0.12), (0.32, 0.32), (0.22, 0.2), sides=6)


def axe():
    butt, top = (-1.2, 0.3, -0.25), (-0.7, 1.35, 0.8)
    H.chain("forearm.R", "wood", [butt, (-0.9, 0.62, 0.1), top], [(0.07, 0.07)] * 3, sides=6)
    H.frustum("forearm.R", "axe", (-0.7, 1.3, 0.8), (-0.7, 1.3, 1.25), (0.08, 0.2), (0.12, 0.5), sides=4)
    H.frustum("forearm.R", "gold", (-0.7, 1.3, 1.23), (-0.7, 1.3, 1.3), (0.12, 0.5), (0.12, 0.52), sides=4)


def shield():
    pole = [(1.0, 0.45, -0.7), (0.9, 1.0, 0.0), (0.95, 1.9, 1.0)]
    H.chain("forearm.L", "wood", pole, [(0.065, 0.065)] * 3, sides=6)
    cx, cy, cz, d = 1.0, 1.25, 1.0, 0.36
    for tone, grow, off in (("gold", 0.06, 0.0), ("black", 0.0, 0.0)):
        w, h = (d + grow) * 0.7, 0.55 + grow
        x, z = cx + off * 0.7, cz - off * 0.7
        pts = [(x - w, cy + h, z - w), (x + w, cy + h, z + w), (x + w, cy - h, z + w), (x - w, cy - h, z - w)]
        H.panel("forearm.L", tone, pts, thickness=0.05 if grow else 0.1)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        arm(s, side)
    axe()
    shield()


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


H.build("o005", "biped", PALETTE, make, joints())
