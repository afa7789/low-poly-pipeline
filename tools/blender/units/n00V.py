"""Troll Berserker (n00V): medido em artifacts/model-sheets/refs/n00V/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n00V.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "skin": 0x84568A, "skin_lt": 0xB994CC, "skin_dk": 0x6E4673, "gaunt": 0x3A3338, "strap": 0x6E6A3A,
    "sash": 0x8B3A32, "loin": 0x5F6199, "wrap": 0xB8A06C, "mohawk": 0xA81B34, "steel": 0x9C9CA0,
    "block": 0x25242A, "tusk": 0xF0E8C8, "eye": 0x1A1618,
}

HIP, KNEE, ANKLE, LEG_X = 1.1, 0.64, 0.2, 0.19
WAIST, NECK, TOP = 1.5, 2.1, 2.75
SH_X, SH_Y, EL_X, EL_Y, WR_X, WR_Y = 0.5, 2.0, 0.55, 1.5, 0.53, 1.1


def head():
    H.frustum("head", "skin", (0, 1.98, 0.02), (0, 2.22, 0.1), (0.22, 0.22), (0.2, 0.2), sides=6)      # pescoço
    H.frustum("head", "skin", (0, 2.2, 0.14), (0, 2.46, 0.16), (0.21, 0.23), (0.18, 0.2), sides=8)    # crânio
    H.frustum("head", "skin", (0, 2.27, 0.25), (0, 2.25, 0.46), (0.17, 0.14), (0.14, 0.1), sides=6)   # focinho
    H.frustum("head", "skin_dk", (0, 2.3, 0.3), (0, 2.22, 0.5), (0.07, 0.06), (0.05, 0.05), sides=4)  # nariz
    H.box("head", "eye", (0, 2.36, 0.33), (0.3, 0.04, 0.04))
    for s in (-1, 1):
        H.frustum("head", "tusk", (s * 0.08, 2.2, 0.4), (s * 0.09, 2.34, 0.41), (0.03, 0.03), (0.015, 0.015), sides=4)
        H.frustum("head", "skin", (s * 0.18, 2.36, 0.12), (s * 0.44, 2.5, 0.05), (0.04, 0.09), (0.01, 0.02), sides=4)   # orelha
    pts = [(0, 2.56, 0.3), (0, 2.74, 0.15), (0, 2.7, -0.05), (0, 2.52, -0.22), (0, 2.3, -0.34)]
    H.chain("head", "mohawk", pts, [(0.03, 0.03), (0.05, 0.13), (0.055, 0.14), (0.05, 0.12), (0.02, 0.05)], sides=4)


def torso():
    H.frustum("spine", "skin", (0, WAIST - 0.05, 0), (0, 1.9, 0), (0.34, 0.27), (0.6, 0.32), sides=8)
    H.frustum("spine", "skin", (0, 1.9, 0), (0, 2.12, 0.02), (0.6, 0.32), (0.3, 0.24), sides=8)
    H.frustum("spine", "skin_lt", (0, 1.68, 0.24), (0, 2.05, 0.26), (0.34, 0.07), (0.44, 0.07), sides=4)   # peito claro
    for z in (0.32, -0.32):         # o X de correias
        H.frustum("spine", "strap", (0.32, 2.12, z), (-0.28, 1.58, z), (0.075, 0.04), (0.075, 0.04), sides=4)
        H.frustum("spine", "strap", (-0.32, 2.12, z), (0.28, 1.58, z), (0.075, 0.04), (0.075, 0.04), sides=4)
    H.frustum("pelvis", "skin", (0, 1.0, 0), (0, WAIST, 0), (0.3, 0.25), (0.3, 0.25), sides=8)
    H.frustum("pelvis", "sash", (0, 1.4, 0), (0, 1.62, 0), (0.34, 0.28), (0.34, 0.28), sides=8)
    for z in (0.24, -0.24):
        H.frustum("pelvis", "loin", (0, 0.94, z), (0, 1.42, z), (0.05, 0.03), (0.22, 0.04), sides=4)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * LEG_X
        H.frustum(f"thigh.{side}", "skin", (x, KNEE - 0.04, 0), (x, 0.88, 0), (0.19, 0.2), (0.24, 0.24), sides=6)
        H.frustum(f"thigh.{side}", "skin", (x, 0.86, 0), (x, HIP + 0.1, 0), (0.24, 0.24), (0.28, 0.28), sides=6)
        H.frustum(f"shin.{side}", "wrap", (x, 0.2, 0), (x, KNEE + 0.02, 0), (0.15, 0.15), (0.18, 0.18), sides=6)
        H.frustum(f"shin.{side}", "skin", (x, ANKLE - 0.04, 0), (x, 0.26, 0), (0.12, 0.12), (0.15, 0.15), sides=6)
        H.frustum(f"foot.{side}", "skin", (x, 0.03, -0.06), (x, ANKLE + 0.04, -0.04), (0.17, 0.2), (0.14, 0.15), sides=6)
        H.frustum(f"foot.{side}", "skin", (x, 0.1, 0.0), (x, 0.06, 0.5), (0.17, 0.12), (0.15, 0.05), sides=4)


def arms():
    for s, side in ((1, "L"), (-1, "R")):
        H.frustum(f"arm.{side}", "skin", (s * SH_X, SH_Y + 0.08, 0), (s * (SH_X + 0.03), 1.76, 0), (0.25, 0.26), (0.28, 0.28), sides=6)
        H.frustum(f"arm.{side}", "skin", (s * (SH_X + 0.03), 1.78, 0), (s * EL_X, EL_Y + 0.02, 0), (0.28, 0.28), (0.2, 0.21), sides=6)
        H.frustum(f"forearm.{side}", "gaunt", (s * EL_X, EL_Y + 0.02, 0), (s * WR_X, WR_Y + 0.02, 0.02), (0.19, 0.2), (0.2, 0.21), sides=6)
        H.frustum(f"forearm.{side}", "skin", (s * WR_X, WR_Y + 0.04, 0.02), (s * (WR_X + 0.01), WR_Y - 0.24, 0.08), (0.14, 0.16), (0.16, 0.18), sides=6)


def cleavers():
    for s in (1, -1):
        side = "L" if s > 0 else "R"
        H.frustum(f"forearm.{side}", "block", (s * 0.55, 0.98, -0.02), (s * 0.58, 0.86, 0.22), (0.06, 0.06), (0.05, 0.05), sides=4)   # cabo
        H.box(f"forearm.{side}", "block", (s * 0.58, 0.88, 0.25), (0.2, 0.2, 0.2))                                                       # cabeça de ferro
        H.frustum(f"forearm.{side}", "steel", (s * 0.6, 0.86, 0.28), (s * 0.76, 0.45, 0.66), (0.08, 0.15), (0.09, 0.19), sides=4)       # lâmina


def make():
    head()
    torso()
    legs()
    arms()
    cleavers()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * WR_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("n00V", "biped", PALETTE, make, joints())
