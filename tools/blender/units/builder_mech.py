"""Mech Robot Builder (builder_mech): medido em artifacts/model-sheets/refs/builder_mech/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/builder_mech.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "body": 0x4A4E5C, "body_dk": 0x3A3D49, "cuff": 0x7A7E8A, "glove": 0x4E3C2C, "boot": 0x483828, "belt": 0x6A4A22,
    "gold": 0xC09030, "gold_dk": 0x946E22, "lens": 0x6A4A1A, "glow": 0xFFE850, "steel": 0x80848C, "handle": 0xA07828,
}

HIP, KNEE, ANKLE, LEG_X = 0.78, 0.42, 0.15, 0.25
WAIST, NECK, TOP = 1.0, 1.5, 2.3
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.52, 1.38, 0.66, 1.0, 0.7


def head():
    H.frustum("head", "body", (0, 1.52, 0.02), (0, 1.95, 0.02), (0.28, 0.26), (0.4, 0.34), sides=8)    # mandíbula -> crânio
    H.frustum("head", "body", (0, 1.95, 0.02), (0, 2.2, 0.0), (0.4, 0.34), (0.32, 0.29), sides=8)
    H.frustum("head", "body", (0, 2.2, 0.0), (0, 2.3, 0.0), (0.3, 0.28), (0.14, 0.14), sides=8)
    H.frustum("head", "body_dk", (0, 1.76, 0.28), (0, 1.84, 0.44), (0.07, 0.06), (0.05, 0.05), sides=4)  # nariz
    H.box("head", "gold", (0, 1.98, 0.3), (0.56, 0.26, 0.1))                                            # óculos
    H.box("head", "lens", (0, 1.98, 0.36), (0.46, 0.17, 0.05))
    H.frustum("head", "gold", (0, 2.06, 0.0), (0, 2.14, 0.0), (0.37, 0.34), (0.37, 0.34), sides=8)      # tira
    for s in (-1, 1):
        H.frustum("head", "body", (s * 0.28, 1.98, 0), (s * 0.96, 2.08, -0.28), (0.2, 0.1), (0.01, 0.01), sides=4)   # orelha


def torso():
    H.frustum("spine", "body", (0, WAIST - 0.05, 0), (0, SH_Y, 0), (0.5, 0.4), (0.58, 0.38), sides=8)
    H.frustum("spine", "body", (0, SH_Y, 0), (0, NECK + 0.05, 0), (0.55, 0.36), (0.25, 0.22), sides=8)
    for s in (-1, 1):
        H.box("spine", "body_dk", (s * 0.2, 1.3, 0.34), (0.1, 0.5, 0.06))                                # alças
    H.frustum("pelvis", "belt", (0, WAIST - 0.14, 0), (0, WAIST + 0.04, 0), (0.5, 0.4), (0.5, 0.4), sides=8)
    H.frustum("pelvis", "gold", (0, WAIST - 0.1, 0.4), (0, WAIST - 0.1, 0.46), (0.12, 0.12), (0.12, 0.12), sides=8)
    H.frustum("pelvis", "body", (0, 0.55, 0), (0, WAIST - 0.1, 0), (0.46, 0.36), (0.5, 0.4), sides=8)
    H.frustum("pelvis", "steel", (0.52, 0.86, 0.3), (0.64, 0.5, 0.3), (0.05, 0.03), (0.04, 0.03), sides=4)  # chave de boca
    H.frustum("pelvis", "steel", (0.64, 0.5, 0.3), (0.67, 0.4, 0.3), (0.09, 0.03), (0.05, 0.03), sides=4)
    H.box("spine", "body_dk", (-0.52, 1.5, 0), (0.4, 0.2, 0.46))                                       # ombreira
    H.frustum("spine", "glow", (-0.52, 1.6, 0), (-0.52, 1.86, 0), (0.11, 0.11), (0.11, 0.11), sides=6)  # antena
    H.frustum("spine", "gold", (-0.52, 1.58, 0), (-0.52, 1.68, 0), (0.14, 0.14), (0.14, 0.14), sides=6)


def leg(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "body", (x, KNEE, 0), (x, HIP + 0.04, 0), (0.22, 0.24), (0.26, 0.28), sides=6)
    H.frustum(f"shin.{side}", "cuff", (x, KNEE - 0.04, 0), (x, KNEE + 0.1, 0), (0.22, 0.23), (0.22, 0.23), sides=6)
    H.frustum(f"shin.{side}", "boot", (x, 0.04, 0), (x, KNEE - 0.04, 0), (0.2, 0.22), (0.18, 0.2), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.03, -0.04), (x, ANKLE + 0.04, -0.04), (0.2, 0.24), (0.18, 0.2), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.1, 0.05), (x, 0.08, 0.4), (0.22, 0.13), (0.2, 0.08), sides=4)


def arm(s, side):
    H.frustum(f"arm.{side}", "body", (s * (SH_X + 0.03), SH_Y + 0.04, 0), (s * EL_X, EL_Y, 0.02), (0.2, 0.2), (0.15, 0.15), sides=6)
    H.frustum(f"forearm.{side}", "body_dk", (s * EL_X, EL_Y + 0.04, 0.02), (s * EL_X, EL_Y - 0.1, 0.04), (0.16, 0.16), (0.2, 0.2), sides=6)
    H.frustum(f"forearm.{side}", "glove", (s * EL_X, EL_Y - 0.06, 0.04), (s * (EL_X + 0.03), 0.5, 0.06), (0.26, 0.22), (0.2, 0.19), sides=6)  # luva


def hammer():
    x, y = -(EL_X + 0.03), 0.62
    H.frustum("forearm.R", "handle", (x, y, -0.6), (x, y, 0.8), (0.05, 0.05), (0.05, 0.05), sides=6)
    H.box("forearm.R", "gold", (x, y, 0.45), (0.34, 0.6, 0.3))
    H.box("forearm.R", "gold_dk", (x, y, 0.45), (0.38, 0.22, 0.34))
    H.frustum("forearm.R", "gold_dk", (x, y, -0.55), (x, y, -0.45), (0.08, 0.08), (0.08, 0.08), sides=6)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        arm(s, side)
    hammer()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("builder_mech", "biped", PALETTE, make, joints())
