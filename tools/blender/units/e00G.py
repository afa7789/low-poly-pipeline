"""Visioneer (e00G): gnoll hiena de capuz, peso de ferro na corrente na mao direita; medido em refs/e00G/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/e00G.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "skin": 0xD9C4D6, "spot": 0x8E6A8A, "hood": 0xA97C86, "hood_dk": 0x6A3A5E, "leaf": 0x6FA85A, "leaf_dk": 0x2E4A2A,
    "loin": 0x3A3438, "rope": 0xB8975A, "cuff": 0xA87C3C, "cuff_dk": 0x7A5A28, "steel": 0x8A8A90, "steel_dk": 0x4A4A50,
    "eye": 0xFFA030, "nose": 0x2A2630, "tooth": 0xF0E6C0, "ear": 0xD8707E, "wrap": 0xC9A56E, "tail": 0x9A7A92,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X = 1.12, 0.56, 0.17, 0.26, 0.30
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.62, 2.0, 0.74, 1.5, 1.0


def head():
    H.frustum("head", "skin", (0, 1.95, 0.37), (0, 2.38, 0.45), (0.2, 0.22), (0.23, 0.25), sides=6)
    H.frustum("head", "skin", (0, 2.1, 0.55), (0, 2.12, 0.91), (0.17, 0.15), (0.1, 0.09), sides=6)
    H.box("head", "nose", (0, 2.15, 0.94), (0.14, 0.1, 0.33))
    H.box("head", "tooth", (0, 2.04, 0.83), (0.15, 0.05, 0.33))
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.12, 2.26, 0.65), (0.09, 0.05, 0.32))
        H.frustum("head", "ear", (s * 0.23, 2.34, 0.30), (s * 0.3, 2.62, 0.25), (0.1, 0.06), (0.06, 0.04), sides=4)
    H.frustum("head", "hood", (0, 2.0, 0.11), (0, 2.78, 0.15), (0.7, 0.5), (0.03, 0.03), sides=4)
    H.frustum("head", "hood_dk", (0, 2.0, 0.05), (0, 2.5, 0.05), (0.3, 0.34), (0.26, 0.3), sides=6)
    H.frustum("spine", "hood", (0, 1.5, 0.52), (0, 2.08, 0.52), (0.03, 0.1), (0.62, 0.13), sides=4)


def torso():
    H.frustum("spine", "skin", (0, 1.15, 0), (0, 1.55, 0), (0.3, 0.26), (0.4, 0.3), sides=8)
    H.frustum("spine", "skin", (0, 1.55, 0.0), (0, 2.02, 0.12), (0.4, 0.3), (0.64, 0.42), sides=8)
    H.frustum("spine", "skin", (0, 2.02, 0.12), (0, 2.2, 0.2), (0.64, 0.42), (0.3, 0.3), sides=8)
    H.frustum("spine", "leaf", (0, 1.25, -0.4), (0, 2.08, -0.38), (0.04, 0.05), (0.52, 0.06), sides=4)
    H.frustum("spine", "leaf_dk", (0, 1.3, -0.45), (0, 2.05, -0.42), (0.025, 0.03), (0.04, 0.03), sides=4)
    H.frustum("pelvis", "skin", (0, 0.95, 0), (0, 1.25, 0), (0.38, 0.3), (0.36, 0.28), sides=8)
    H.frustum("pelvis", "loin", (0, 0.8, 0), (0, 1.22, 0), (0.4, 0.32), (0.4, 0.31), sides=8)
    H.frustum("pelvis", "loin", (0, 0.62, 0.3), (0, 1.1, 0.3), (0.04, 0.04), (0.28, 0.05), sides=4)
    H.frustum("pelvis", "rope", (0, 1.16, 0), (0, 1.3, 0), (0.42, 0.33), (0.42, 0.33), sides=8)
    H.chain("pelvis", "tail", [(0, 1.05, -0.3), (0, 0.8, -0.52), (0, 0.5, -0.72), (0, 0.28, -0.98)],
            [(0.1, 0.1), (0.09, 0.09), (0.07, 0.07), (0.03, 0.03)])


def leg(s, side):
    H.frustum(f"thigh.{side}", "skin", (s * KNEE_X, KNEE - 0.04, 0.02), (s * LEG_X, HIP + 0.05, 0), (0.2, 0.24), (0.29, 0.3), sides=6)
    H.frustum(f"thigh.{side}", "skin", (s * 0.28, 0.75, 0.0), (s * 0.27, 1.0, 0), (0.2, 0.23), (0.25, 0.26), sides=6)
    H.frustum(f"shin.{side}", "skin", (s * KNEE_X, ANKLE, 0), (s * KNEE_X, KNEE + 0.03, 0), (0.12, 0.13), (0.19, 0.2), sides=6)
    H.frustum(f"shin.{side}", "wrap", (s * KNEE_X, 0.2, 0), (s * KNEE_X, 0.48, 0), (0.15, 0.16), (0.16, 0.17), sides=6)
    H.frustum(f"foot.{side}", "skin", (s * KNEE_X, 0.03, -0.05), (s * KNEE_X, ANKLE + 0.04, -0.03), (0.17, 0.19), (0.13, 0.14), sides=6)
    H.frustum(f"foot.{side}", "skin", (s * KNEE_X, 0.09, 0.02), (s * KNEE_X, 0.06, 0.46), (0.17, 0.1), (0.15, 0.05), sides=6)


def arm(s, side):
    H.chain(f"arm.{side}", "skin", [(s * (SH_X + 0.02), SH_Y + 0.05, 0), (s * 0.68, 1.78, 0), (s * EL_X, EL_Y - 0.03, 0)],
            [(0.21, 0.22), (0.23, 0.22), (0.17, 0.17)], sides=6)
    H.chain(f"forearm.{side}", "skin", [(s * EL_X, EL_Y + 0.04, 0), (s * EL_X, 1.25, 0.02), (s * EL_X, WR_Y + 0.12, 0.03)],
            [(0.18, 0.18), (0.2, 0.2), (0.16, 0.16)], sides=6)
    H.frustum(f"forearm.{side}", "cuff", (s * EL_X, WR_Y + 0.18, 0.03), (s * EL_X, WR_Y - 0.04, 0.03), (0.2, 0.21), (0.23, 0.23), sides=6)
    H.frustum(f"forearm.{side}", "cuff_dk", (s * EL_X, WR_Y + 0.07, 0.03), (s * EL_X, WR_Y + 0.12, 0.03), (0.215, 0.225), (0.215, 0.225), sides=6)
    H.frustum(f"forearm.{side}", "skin", (s * EL_X, WR_Y - 0.02, 0.04), (s * EL_X, WR_Y - 0.3, 0.07), (0.19, 0.2), (0.15, 0.17), sides=6)


def weight():
    H.chain("forearm.R", "steel_dk", [(-0.74, 0.76, 0.07), (-0.78, 0.64, 0.1), (-0.82, 0.52, 0.1), (-0.85, 0.42, 0.1)],
            [(0.05, 0.05)] * 4, sides=4)
    H.box("forearm.R", "steel", (-0.86, 0.22, 0.1), (0.46, 0.44, 0.44))
    H.box("forearm.R", "steel_dk", (-0.86, 0.45, 0.1), (0.2, 0.06, 0.2))


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        arm(s, side)
    weight()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, 1.4, 0)), "spine": ((0, 1.4, 0), (0, 2.1, 0)), "head": ((0, 2.1, 0), (0, 2.72, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * SH_X + s * 0.12, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * KNEE_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * KNEE_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * KNEE_X, ANKLE, 0), (s * KNEE_X, 0.06, 0.5))
    return out


H.build("e00G", "biped", PALETTE, make, joints())
