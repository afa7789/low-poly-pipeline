"""Sniper (hrif): medido em artifacts/model-sheets/refs/hrif/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/hrif.py -- <out.glb>
"""
import pathlib
import sys

from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "coat": 0x565F4F, "coat_dk": 0x464E41, "sleeve": 0x5A4332, "hood": 0x4A3828, "helmet": 0x5A5C66, "helmet_dk": 0x474952,
    "skin": 0xD1A084, "black": 0x1E1E22, "boot": 0x1B1B1F, "belt": 0x5A4030, "buckle": 0x3A3A40, "pack": 0x9A8460,
    "lantern": 0x4A60E0, "lantern_fr": 0x2A2A30, "wood": 0x5A3A26, "steel": 0x2E3138, "blade": 0x8A8C92, "pants": 0x4D5646,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X = 1.08, 0.50, 0.17, 0.23, 0.26
WAIST, NECK, TOP = 1.42, 2.16, 2.70
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.52, 2.06, 0.66, 1.50, 1.04
SKIRT_MID = 1.05


def hem(p):
    if p[1] > SKIRT_MID:
        return {"pelvis": 1.0}
    return {"pelvis": 0.45, "thigh.L" if p[0] > 0 else "thigh.R": 0.55}


def head():
    H.frustum("head", "skin", (0, 2.12, 0.03), (0, 2.42, 0.03), (0.17, 0.17), (0.2, 0.2), sides=6)
    H.frustum("head", "black", (0, 2.34, 0.2), (0, 2.38, 0.2), (0.17, 0.03), (0.17, 0.03), sides=4)
    H.frustum("head", "helmet_dk", (0, 2.36, 0), (0, 2.44, 0), (0.34, 0.34), (0.31, 0.31), sides=8)
    H.frustum("head", "helmet", (0, 2.42, 0), (0, 2.62, 0), (0.31, 0.3), (0.22, 0.22), sides=8)
    H.frustum("head", "helmet", (0, 2.62, 0), (0, 2.70, 0), (0.22, 0.22), (0.1, 0.1), sides=8)
    H.frustum("head", "hood", (0, 2.0, -0.08), (0, 2.3, -0.08), (0.36, 0.3), (0.4, 0.34), sides=8)


def torso():
    H.frustum("spine", "coat", (0, WAIST - 0.04, 0), (0, 2.05, 0), (0.42, 0.34), (0.5, 0.36), sides=8)
    H.frustum("spine", "coat", (0, 2.05, 0), (0, 2.22, 0), (0.5, 0.36), (0.3, 0.26), sides=8)
    H.frustum("spine", "black", (0, 2.1, 0.05), (0, 2.2, 0.05), (0.27, 0.27), (0.24, 0.24), sides=8)
    for s in (-1, 1):
        H.frustum("spine", "black", (s * 0.4, 2.1, 0.35), (-s * 0.3, 1.5, 0.38), (0.07, 0.03), (0.07, 0.03), sides=4)
        H.frustum("spine", "black", (s * 0.4, 2.1, -0.35), (-s * 0.3, 1.5, -0.38), (0.07, 0.03), (0.07, 0.03), sides=4)
    H.frustum("spine", "pack", (-0.1, 1.4, -0.4), (-0.1, 1.8, -0.5), (0.34, 0.14), (0.32, 0.12), sides=4)
    H.frustum("pelvis", "belt", (0, WAIST - 0.1, 0), (0, WAIST + 0.06, 0), (0.44, 0.36), (0.44, 0.36), sides=8)
    H.box("pelvis", "buckle", (0, WAIST - 0.02, 0.37), (0.18, 0.15, 0.04))
    skirt = H.frustum("pelvis", "coat", (0, 0.66, 0), (0, WAIST - 0.05, 0), (0.62, 0.42), (0.46, 0.36), sides=8)
    H.soft(skirt, hem)
    H.frustum("pelvis", "pants", (0, 0.84, 0), (0, 1.12, 0), (0.38, 0.3), (0.42, 0.34), sides=8)
    H.frustum("pelvis", "lantern_fr", (0.4, 1.02, 0.12), (0.4, 1.3, 0.12), (0.12, 0.12), (0.06, 0.06), sides=4)
    H.frustum("pelvis", "lantern", (0.42, 0.78, 0.14), (0.42, 1.02, 0.14), (0.1, 0.1), (0.14, 0.14), sides=4)
    H.frustum("pelvis", "lantern_fr", (0.42, 0.74, 0.14), (0.42, 0.78, 0.14), (0.15, 0.15), (0.12, 0.12), sides=4)


def limbs():
    for s, side in ((1, "L"), (-1, "R")):
        H.frustum(f"thigh.{side}", "pants", (s * KNEE_X, KNEE - 0.04, 0), (s * LEG_X, HIP + 0.04, 0), (0.25, 0.26), (0.22, 0.26), sides=6)
        H.frustum(f"shin.{side}", "pants", (s * KNEE_X, 0.3, 0), (s * KNEE_X, KNEE + 0.02, 0), (0.18, 0.18), (0.21, 0.2), sides=6)
        H.frustum(f"shin.{side}", "boot", (s * KNEE_X, 0.04, 0), (s * KNEE_X, 0.36, 0), (0.2, 0.22), (0.18, 0.2), sides=6)
        H.frustum(f"foot.{side}", "boot", (s * KNEE_X, 0.1, 0.05), (s * KNEE_X, 0.08, 0.42), (0.2, 0.11), (0.17, 0.07), sides=4)
        H.frustum(f"arm.{side}", "sleeve", (s * (SH_X + 0.03), SH_Y + 0.04, 0), (s * EL_X, EL_Y - 0.03, 0), (0.23, 0.26), (0.21, 0.23), sides=6)
        H.frustum(f"forearm.{side}", "sleeve", (s * EL_X, EL_Y + 0.04, 0), (s * EL_X, WR_Y + 0.1, 0.03), (0.2, 0.21), (0.17, 0.18), sides=6)
        H.frustum(f"forearm.{side}", "black", (s * EL_X, WR_Y + 0.1, 0.03), (s * EL_X, WR_Y - 0.2, 0.06), (0.17, 0.19), (0.2, 0.22), sides=6)


def rifle():
    """Na mão esquerda, ao lado do corpo, no plano do braço: coronha baixa atrás, baioneta no alto à frente (cruzando
    o peito, como na prancha, o clipe de tiro torcia o braço por cima do capacete para nivelar o cano)."""
    butt, tip = Vector((0.8, 0.8, -0.45)), Vector((0.8, 2.6, 1.1))
    grip, muzzle = butt.lerp(tip, 0.3), butt.lerp(tip, 0.82)
    H.frustum("forearm.L", "wood", butt, grip, (0.09, 0.15), (0.06, 0.09), sides=4)
    H.frustum("forearm.L", "steel", grip, muzzle, (0.05, 0.06), (0.05, 0.05), sides=6)
    H.frustum("forearm.L", "blade", muzzle, tip, (0.035, 0.07), (0.005, 0.01), sides=4)
    H.frustum("forearm.L", "black", butt.lerp(tip, 0.55) - Vector((0.1, 0.1, 0)), butt.lerp(tip, 0.55) + Vector((0.1, 0.1, 0)),
              (0.13, 0.13), (0.13, 0.13), sides=6)


def make():
    head()
    torso()
    limbs()
    rifle()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * SH_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * KNEE_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * KNEE_X, ANKLE, 0), (s * KNEE_X, 0.06, 0.5))
    return out


H.build("hrif", "biped", PALETTE, make, joints())
