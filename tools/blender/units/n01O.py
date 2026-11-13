"""Troll Trapper (n01O): measured on artifacts/model-sheets/refs/n01O/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n01O.py -- <out.glb>

Two cleavers, one per fist (forearm.L / forearm.R), blades pointing forward and down as in the profile.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "skin": 0x84558A, "skin_dk": 0x6E4675, "chest": 0xB78FC9, "vest": 0x2C2F5C, "pauldron": 0x8C8E98, "trim": 0xA68A44,
    "sash": 0x8A3A2A, "wrap": 0xB5A173, "brace": 0x2A2A30, "brace_lt": 0x8C8E98, "mohawk": 0xB0203C, "stripe": 0xE6DCC0,
    "eye": 0xFF9A1C, "tusk": 0xE6DCC0, "blade": 0xA2A4AC, "blade_dk": 0x6E7076, "black": 0x1E1E22, "rust": 0x8A4A2A,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X, FOOT_X = 1.2, 0.64, 0.22, 0.2, 0.26, 0.3
WAIST, NECK, TOP = 1.45, 2.12, 2.76
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.5, 2.0, 0.54, 1.5, 1.06


def head():
    H.frustum("head", "skin", (0, 2.1, 0.12), (0, 2.5, 0.12), (0.19, 0.22), (0.21, 0.22), sides=6)
    H.frustum("head", "skin", (0, 2.2, 0.3), (0, 2.34, 0.4), (0.07, 0.08), (0.05, 0.05), sides=4)       # nose
    H.frustum("head", "skin_dk", (0, 2.0, 0.08), (0, 2.16, 0.1), (0.24, 0.24), (0.2, 0.22), sides=8)    # neck
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.1, 2.36, 0.34), (0.08, 0.04, 0.03))
        H.box("head", "tusk", (s * 0.08, 2.14, 0.34), (0.04, 0.1, 0.04))
        H.chain("head", "skin", [(s * 0.18, 2.4, 0.08), (s * 0.34, 2.5, 0.0), (s * 0.5, 2.62, -0.04)],
                [(0.06, 0.05), (0.05, 0.03), (0.01, 0.01)], sides=4)                                    # pointed ears
    H.chain("head", "mohawk", [(0, 2.46, 0.26), (0, 2.72, 0.14), (0, 2.78, -0.08), (0, 2.5, -0.3)],
            [(0.05, 0.07), (0.06, 0.1), (0.06, 0.1), (0.05, 0.07)], sides=4)
    H.chain("head", "stripe", [(0.0, 2.44, 0.28), (0, 2.5, 0.2)], [(0.12, 0.03), (0.12, 0.03)], sides=4)


def torso():
    H.frustum("spine", "vest", (0, WAIST - 0.04, 0), (0, 2.0, 0), (0.34, 0.26), (0.46, 0.3), sides=8)
    H.frustum("spine", "vest", (0, 2.0, 0), (0, 2.18, 0), (0.46, 0.3), (0.32, 0.25), sides=8)
    H.frustum("spine", "chest", (0, 1.6, 0.2), (0, 2.1, 0.18), (0.06, 0.1), (0.2, 0.1), sides=4)        # open V of the chest
    H.frustum("pelvis", "sash", (0, WAIST - 0.14, 0), (0, WAIST + 0.04, 0), (0.34, 0.27), (0.34, 0.27), sides=8)
    H.frustum("pelvis", "skin", (0, 1.0, 0), (0, WAIST - 0.1, 0), (0.3, 0.22), (0.3, 0.24), sides=8)
    H.frustum("pelvis", "vest", (0, 0.92, 0.2), (0, WAIST - 0.1, 0.2), (0.2, 0.05), (0.26, 0.05), sides=4)  # loincloth front
    H.frustum("pelvis", "vest", (0, 0.9, -0.2), (0, WAIST - 0.1, -0.2), (0.24, 0.05), (0.3, 0.05), sides=4)
    H.box("pelvis", "sash", (0.06, 1.3, 0.3), (0.1, 0.24, 0.05))                                          # knot tail


def leg(s, side):
    k = s * KNEE_X
    H.frustum(f"thigh.{side}", "skin", (k, KNEE - 0.04, 0), (s * LEG_X, HIP + 0.04, 0), (0.17, 0.19), (0.23, 0.24), sides=6)
    H.frustum(f"thigh.{side}", "skin_dk", (k, KNEE + 0.1, 0.04), (k, KNEE + 0.4, 0.06), (0.18, 0.19), (0.21, 0.21), sides=6)
    H.frustum(f"shin.{side}", "skin", (s * 0.29, ANKLE, 0), (k, KNEE + 0.02, 0), (0.15, 0.16), (0.17, 0.18), sides=6)
    H.frustum(f"shin.{side}", "wrap", (s * 0.28, ANKLE + 0.08, 0), (s * 0.27, KNEE - 0.04, 0), (0.17, 0.18), (0.2, 0.2), sides=6)
    f = s * FOOT_X
    H.frustum(f"foot.{side}", "skin", (f, 0.03, -0.1), (f, ANKLE + 0.06, -0.04), (0.17, 0.2), (0.15, 0.17), sides=6)
    H.frustum(f"foot.{side}", "skin", (f, 0.08, 0.0), (f, 0.05, 0.5), (0.19, 0.12), (0.2, 0.05), sides=6)


def arm(s, side):
    elbow = (s * EL_X, EL_Y, 0.04)
    H.frustum(f"arm.{side}", "pauldron", (s * 0.26, 2.32, 0), (s * 0.6, 2.0, 0), (0.24, 0.3), (0.26, 0.3), sides=6)
    H.frustum(f"arm.{side}", "trim", (s * 0.6, 2.0, 0), (s * 0.66, 1.9, 0), (0.25, 0.31), (0.25, 0.31), sides=6)
    H.chain(f"arm.{side}", "skin", [(s * SH_X, SH_Y - 0.04, 0), (s * 0.56, 1.8, 0.01), elbow],
            [(0.22, 0.23), (0.23, 0.24), (0.2, 0.21)])
    wrist = (s * EL_X, WR_Y + 0.02, 0.06)
    H.frustum(f"forearm.{side}", "skin", (elbow[0], EL_Y + 0.02, 0.04), (wrist[0], 1.2, 0.05), (0.17, 0.18), (0.18, 0.19), sides=6)
    for y0, tone in ((1.14, "brace"), (1.22, "brace_lt"), (1.3, "brace"), (1.38, "brace_lt"), (1.46, "brace")):     # stacked bracer bands
        H.frustum(f"forearm.{side}", tone, (wrist[0], y0, 0.05), (wrist[0], y0 + 0.08, 0.05), (0.21, 0.22), (0.21, 0.22), sides=6)
    H.frustum(f"forearm.{side}", "skin", (wrist[0], 1.14, 0.05), (wrist[0], WR_Y - 0.12, 0.08), (0.18, 0.19), (0.17, 0.18), sides=6)


def cleaver(s, side):
    x = s * (EL_X - 0.02)
    H.frustum(f"forearm.{side}", "black", (x, WR_Y + 0.12, 0.0), (x, WR_Y - 0.08, 0.12), (0.06, 0.07), (0.06, 0.07), sides=6)    # grip
    H.box(f"forearm.{side}", "black", (x, WR_Y - 0.12, 0.22), (0.12, 0.22, 0.2))                                                 # bolster
    H.frustum(f"forearm.{side}", "rust", (x + s * 0.1, WR_Y - 0.06, 0.2), (x + s * 0.12, WR_Y - 0.26, 0.2), (0.03, 0.03), (0.03, 0.03), sides=4)
    H.frustum(f"forearm.{side}", "blade", (x, WR_Y - 0.18, 0.3), (x + s * 0.12, WR_Y - 0.5, 0.95), (0.05, 0.17), (0.05, 0.17), sides=4)       # blade
    H.frustum(f"forearm.{side}", "blade_dk", (x + s * 0.12, WR_Y - 0.5, 0.95), (x + s * 0.12, WR_Y - 0.52, 1.0), (0.05, 0.17), (0.03, 0.15), sides=4)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        arm(s, side)
        cleaver(s, side)


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


H.build("n01O", "biped", PALETTE, make, joints())
