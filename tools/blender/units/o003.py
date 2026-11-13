"""Shaman (o003): orc xamã de máscara de bico de osso, cajado de caveira na mão direita, sinos na cintura;
medido em artifacts/model-sheets/refs/o003/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/o003.py -- <out.glb>
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "skin": 0x67AA2A, "skin_dk": 0x558F22, "skirt": 0xA9703A, "skirt_dk": 0x8C5A2E, "trim": 0xE6D6B4,
    "boot": 0x5A3322, "boot_dk": 0x44261A, "bone": 0xDCCBA8, "bell": 0x7A7A82, "flame": 0xFF6A1E, "pole": 0x5A3A26,
    "quiver": 0x5E3B28, "fan": 0x6B4630, "strap": 0x2A1E1A, "eye": 0x1A1618,
}

HIP, KNEE, ANKLE, LEG_X = 1.02, 0.6, 0.14, 0.32
WAIST, NECK, TOP = 1.42, 2.15, 2.75
SH_X, SH_Y = 0.62, 2.12
STAFF_X, STAFF_Z = -0.8, 0.6
SKIRT_MID = 0.95


def hem(p):
    """A barra da saia acompanha a coxa do seu lado; o topo fica na pelve."""
    if p[1] > SKIRT_MID:
        return {"pelvis": 1.0}
    return {"pelvis": 0.45, "thigh.L" if p[0] > 0 else "thigh.R": 0.55}


def head():
    H.frustum("head", "skin", (0, 2.12, 0.0), (0, 2.35, 0.04), (0.2, 0.2), (0.26, 0.26), sides=8)          # pescoço grosso
    H.frustum("head", "bone", (0, 2.34, 0.04), (0, 2.58, 0.06), (0.28, 0.3), (0.28, 0.3), sides=8)       # máscara de crânio
    H.frustum("head", "bone", (0, 2.58, 0.06), (0, 2.74, 0.04), (0.28, 0.3), (0.14, 0.15), sides=8)
    H.chain("head", "bone", [(0, 2.52, 0.2), (0, 2.38, 0.5), (0, 2.14, 0.82)], [(0.13, 0.15), (0.1, 0.13), (0.02, 0.03)], sides=4)   # bico
    H.frustum("head", "flame", (0, 2.02, 0.9), (0, 2.28, 0.9), (0.09, 0.09), (0.02, 0.02), sides=6)
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.1, 2.52, 0.28), (0.09, 0.07, 0.03))
        H.frustum("head", "skin", (s * 0.22, 2.5, 0.0), (s * 0.4, 2.62, -0.02), (0.07, 0.05), (0.015, 0.02), sides=4)   # orelhas
        H.chain("head", "trim", [(s * 0.14, 2.3, 0.3), (s * 0.26, 2.36, 0.42), (s * 0.28, 2.5, 0.42)], [(0.05, 0.05), (0.04, 0.04), (0.01, 0.01)], sides=4)


def torso():
    H.frustum("spine", "skin", (0, WAIST - 0.05, 0), (0, 1.9, 0.0), (0.46, 0.34), (0.62, 0.36), sides=8)          # peito nu
    H.frustum("spine", "skin_dk", (0, 1.9, 0.0), (0, 2.25, 0.02), (0.62, 0.36), (0.42, 0.28), sides=8)
    H.frustum("pelvis", "skin", (0, 0.95, 0), (0, WAIST, 0), (0.42, 0.34), (0.46, 0.34), sides=8)
    H.frustum("pelvis", "trim", (0, WAIST - 0.05, 0), (0, WAIST + 0.08, 0), (0.5, 0.4), (0.5, 0.4), sides=8)
    skirt = H.frustum("pelvis", "skirt", (0, 0.55, 0), (0, WAIST, 0), (0.58, 0.46), (0.48, 0.38), sides=8)
    H.soft(skirt, hem)
    H.frustum("pelvis", "trim", (0, 0.5, 0), (0, 0.6, 0), (0.6, 0.48), (0.59, 0.47), sides=8)                  # barra clara
    for deg in (-70, -35, 0, 35, 70):       # sinos pendurados na cintura
        a = math.radians(deg)
        x, z = 0.5 * math.sin(a), 0.4 * math.cos(a)
        H.frustum("pelvis", "bell", (x, 1.04, z), (x, 1.3, z), (0.12, 0.12), (0.06, 0.06), sides=6)


def quiver():
    H.frustum("spine", "quiver", (0, 1.55, -0.45), (0, 2.12, -0.45), (0.32, 0.12), (0.38, 0.14), sides=6)
    H.frustum("spine", "fan", (0, 1.8, -0.5), (0, 2.3, -0.85), (0.34, 0.12), (0.5, 0.05), sides=4)           # leque de penas/ossos
    H.frustum("spine", "strap", (0.35, 2.15, 0.0), (0.2, 1.5, -0.35), (0.04, 0.04), (0.04, 0.04), sides=4)
    H.frustum("spine", "strap", (-0.35, 2.15, 0.0), (-0.2, 1.5, -0.35), (0.04, 0.04), (0.04, 0.04), sides=4)


def leg(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "skin", (x, KNEE - 0.04, 0), (x, HIP + 0.05, 0), (0.22, 0.24), (0.27, 0.28), sides=6)
    H.frustum(f"shin.{side}", "skin_dk", (x, 0.45, 0), (x, KNEE + 0.02, 0), (0.22, 0.22), (0.23, 0.23), sides=6)
    H.frustum(f"shin.{side}", "boot", (x, 0.1, 0), (x, 0.5, 0), (0.27, 0.28), (0.33, 0.33), sides=6)           # bota larga
    H.frustum(f"foot.{side}", "boot", (x, 0.12, -0.04), (x, 0.1, 0.4), (0.3, 0.22), (0.26, 0.12), sides=6)
    H.frustum(f"foot.{side}", "boot_dk", (x, 0.03, -0.2), (x, 0.03, 0.4), (0.3, 0.04), (0.26, 0.04), sides=4)


def arm_l():
    H.frustum("arm.L", "skin", (0.5, 2.25, 0), (0.72, 1.82, 0.02), (0.3, 0.3), (0.34, 0.33), sides=6)
    H.frustum("arm.L", "skin_dk", (0.72, 1.82, 0.02), (0.78, 1.5, 0.04), (0.34, 0.33), (0.27, 0.27), sides=6)
    H.frustum("forearm.L", "skin", (0.78, 1.52, 0.04), (0.72, 1.14, 0.06), (0.26, 0.27), (0.3, 0.3), sides=6)
    H.frustum("forearm.L", "skin_dk", (0.72, 1.16, 0.06), (0.7, 0.82, 0.08), (0.3, 0.3), (0.24, 0.24), sides=6)   # mão aberta pendendo


def arm_r():
    H.frustum("arm.R", "skin", (-0.5, 2.25, 0), (-0.76, 1.84, 0.02), (0.3, 0.3), (0.34, 0.33), sides=6)
    H.frustum("arm.R", "skin_dk", (-0.76, 1.84, 0.02), (-0.84, 1.5, 0.06), (0.34, 0.33), (0.27, 0.27), sides=6)
    H.frustum("forearm.R", "skin", (-0.84, 1.52, 0.06), (-0.8, 1.6, 0.36), (0.27, 0.27), (0.3, 0.3), sides=6)    # antebraço à frente
    H.frustum("forearm.R", "skin_dk", (-0.8, 1.6, 0.34), (-0.8, 1.64, 0.55), (0.3, 0.3), (0.27, 0.27), sides=6)
    H.frustum("forearm.R", "skin", (-0.8, 1.64, 0.5), (-0.8, 1.64, 0.7), (0.27, 0.27), (0.2, 0.22), sides=6)     # punho no cajado
    x, z = STAFF_X, STAFF_Z
    H.frustum("forearm.R", "pole", (x, 0.0, z), (x, 2.4, z), (0.07, 0.07), (0.065, 0.065), sides=6)
    H.frustum("forearm.R", "bone", (x, 2.32, z), (x, 2.55, z), (0.18, 0.18), (0.25, 0.24), sides=8)           # caveira
    H.frustum("forearm.R", "bone", (x, 2.55, z), (x, 2.78, z), (0.25, 0.24), (0.15, 0.15), sides=8)
    H.box("forearm.R", "eye", (x + 0.1, 2.58, z + 0.22), (0.08, 0.08, 0.03))
    H.box("forearm.R", "eye", (x - 0.1, 2.58, z + 0.22), (0.08, 0.08, 0.03))


def make():
    head()
    torso()
    quiver()
    arm_l()
    arm_r()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * 0.82, 1.5, 0.05))
        out[f"forearm.{side}"] = ((s * 0.82, 1.5, 0.05), (s * 0.7, 0.9, 0.08))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("o003", "biped", PALETTE, make, joints())
