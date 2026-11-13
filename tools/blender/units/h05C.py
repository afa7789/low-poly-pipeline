"""Marksman (h05C): medido em artifacts/model-sheets/refs/h05C/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/h05C.py -- <out.glb>
"""
import pathlib
import sys

from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "coat": 0x7A4A38, "coat_dk": 0x5E3A2C, "breech": 0x6E6C45, "breech_dk": 0x5A5838, "helmet": 0x7C7A4C,
    "helmet_dk": 0x63613B, "mask": 0x8E96A0, "lens": 0x3A3C42, "glove": 0x6E5441, "boot": 0x4A3326,
    "belt": 0x4A3228, "brass": 0xD0A24A, "pouch": 0x6B4A34, "wood": 0x6A3A28, "steel": 0x8A8F96,
    "sole": 0x231B18, "glass": 0xFFE29A,
}

HIP, KNEE, ANKLE, LEG_X, FOOT_X = 0.85, 0.50, 0.17, 0.26, 0.32
WAIST, NECK, TOP = 1.22, 1.90, 2.52
SH_X, SH_Y = 0.56, 1.82
R_EL, R_WR = (-0.66, 1.45), (-0.52, 1.05)
L_EL, L_WR = (0.66, 1.42), (0.62, 0.96)


def hem(p):
    """A barra do casaco acompanha a coxa do seu lado."""
    if p[1] > 1.0:
        return {"pelvis": 1.0}
    return {"pelvis": 0.5, "thigh.L" if p[0] > 0 else "thigh.R": 0.5}


def head():
    H.frustum("head", "mask", (0, 1.98, 0.02), (0, 2.28, 0.04), (0.19, 0.2), (0.21, 0.22), sides=6)
    H.frustum("head", "mask", (0, 2.0, 0.2), (0, 2.0, 0.4), (0.13, 0.13), (0.11, 0.11), sides=8)     # filtro
    H.frustum("head", "lens", (0, 2.0, 0.4), (0, 2.0, 0.44), (0.07, 0.07), (0.07, 0.07), sides=8)
    for s in (-1, 1):
        H.frustum("head", "lens", (s * 0.1, 2.2, 0.22), (s * 0.1, 2.2, 0.27), (0.075, 0.075), (0.075, 0.075), sides=8)
    H.frustum("head", "coat", (0, 1.88, 0), (0, 2.08, 0), (0.36, 0.3), (0.3, 0.25), sides=8)             # gola alta
    H.frustum("head", "helmet_dk", (0, 2.2, 0), (0, 2.3, 0), (0.33, 0.33), (0.3, 0.3), sides=8)        # aba
    H.frustum("head", "helmet", (0, 2.3, 0), (0, 2.46, 0), (0.29, 0.29), (0.24, 0.25), sides=8)
    H.frustum("head", "helmet", (0, 2.46, 0), (0, 2.54, 0), (0.24, 0.25), (0.1, 0.1), sides=8)


def torso():
    H.frustum("spine", "coat", (0, WAIST - 0.04, 0), (0, 1.8, 0), (0.46, 0.34), (0.55, 0.38), sides=8)
    H.frustum("spine", "coat", (0, 1.8, 0), (0, 2.0, 0), (0.55, 0.38), (0.3, 0.26), sides=8)
    H.frustum("spine", "coat_dk", (0.05, 1.5, 0.33), (0.05, 1.9, 0.3), (0.22, 0.03), (0.2, 0.03), sides=4)  # lapela
    H.frustum("pelvis", "belt", (0, WAIST - 0.12, 0), (0, WAIST + 0.04, 0), (0.5, 0.4), (0.5, 0.4), sides=8)
    for x in (-0.16, 0, 0.16):      # cartuchos no cinto
        H.frustum("pelvis", "pouch", (x, WAIST - 0.1, 0.4), (x, WAIST + 0.06, 0.4), (0.06, 0.06), (0.06, 0.06), sides=6)
        H.frustum("pelvis", "brass", (x, WAIST + 0.06, 0.4), (x, WAIST + 0.12, 0.4), (0.055, 0.055), (0.055, 0.055), sides=6)
    skirt = H.frustum("pelvis", "coat", (0, 0.86, 0), (0, WAIST - 0.06, 0), (0.62, 0.5), (0.5, 0.4), sides=8)
    H.soft(skirt, hem)
    H.frustum("pelvis", "breech", (0, 0.8, 0), (0, 1.1, 0), (0.42, 0.34), (0.46, 0.38), sides=8)


def lantern():
    c = (-0.62, 0.8, 0.03)
    H.frustum("pelvis", "brass", (c[0], c[1] - 0.17, c[2]), (c[0], c[1] + 0.17, c[2]), (0.17, 0.17), (0.14, 0.14), sides=4)
    H.frustum("pelvis", "glass", (c[0], c[1] - 0.12, c[2]), (c[0], c[1] + 0.12, c[2]), (0.16, 0.12), (0.13, 0.1), sides=4)
    H.frustum("pelvis", "brass", (c[0], c[1] + 0.17, c[2]), (c[0], c[1] + 0.3, c[2]), (0.05, 0.05), (0.03, 0.03), sides=6)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        H.frustum(f"thigh.{side}", "breech", (s * 0.30, KNEE - 0.05, 0), (s * LEG_X, HIP + 0.05, 0), (0.25, 0.26), (0.22, 0.24), sides=6)
        H.frustum(f"thigh.{side}", "breech_dk", (s * 0.30, KNEE - 0.08, 0), (s * 0.30, KNEE + 0.06, 0), (0.27, 0.27), (0.25, 0.26), sides=6)
        H.frustum(f"shin.{side}", "boot", (s * FOOT_X, ANKLE - 0.02, 0), (s * FOOT_X, KNEE + 0.02, 0), (0.18, 0.2), (0.24, 0.25), sides=6)
        H.frustum(f"foot.{side}", "boot", (s * FOOT_X, 0.04, -0.05), (s * FOOT_X, ANKLE + 0.05, -0.05), (0.2, 0.23), (0.18, 0.2), sides=6)
        H.frustum(f"foot.{side}", "boot", (s * FOOT_X, 0.11, 0.06), (s * FOOT_X, 0.09, 0.46), (0.2, 0.12), (0.17, 0.07), sides=4)
        H.frustum(f"foot.{side}", "sole", (s * FOOT_X, 0.02, -0.2), (s * FOOT_X, 0.02, 0.48), (0.21, 0.022), (0.18, 0.022), sides=4)


def arms():
    # direito (forearm.R) segura o fuzil: ombro grosso, manga larga, luva grande
    for s, side, el, wr in ((-1, "R", R_EL, R_WR), (1, "L", L_EL, L_WR)):
        H.frustum(f"arm.{side}", "coat", (s * (SH_X - 0.04), SH_Y + 0.06, 0), (el[0], el[1] - 0.04, 0), (0.24, 0.26), (0.2, 0.21), sides=6)
        H.frustum(f"forearm.{side}", "coat", (el[0], el[1] + 0.05, 0), (wr[0], wr[1] + 0.12, 0.05), (0.2, 0.21), (0.19, 0.2), sides=6)
        H.frustum(f"forearm.{side}", "glove", (wr[0], wr[1] + 0.12, 0.05), (wr[0] + s * 0.02, wr[1] - 0.14, 0.08), (0.17, 0.2), (0.16, 0.18), sides=6)


def rifle():
    # fuzil com luneta, mão direita, empinado como no perfil: coronha atrás/embaixo, boca à frente/alto
    butt, tip = Vector((-0.46, 0.7, -0.4)), Vector((-0.46, 2.9, 1.4))
    stock, grip, muzzle = butt.lerp(tip, 0.28), butt.lerp(tip, 0.5), butt.lerp(tip, 0.97)
    H.frustum("forearm.R", "wood", butt, stock, (0.08, 0.2), (0.09, 0.11), sides=4)
    H.frustum("forearm.R", "wood", stock, grip, (0.09, 0.11), (0.08, 0.09), sides=4)
    H.frustum("forearm.R", "steel", grip, muzzle, (0.06, 0.06), (0.05, 0.05), sides=6)
    scope = butt.lerp(tip, 0.55) + Vector((0, 0.13, 0))
    H.frustum("forearm.R", "lens", scope, scope + (tip - butt).normalized() * 0.5, (0.09, 0.09), (0.09, 0.09), sides=6)
    H.frustum("forearm.R", "brass", scope, scope + (tip - butt).normalized() * 0.08, (0.17, 0.17), (0.17, 0.17), sides=4)


def make():
    head()
    torso()
    lantern()
    legs()
    arms()
    rifle()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side, el, wr in ((-1, "R", R_EL, R_WR), (1, "L", L_EL, L_WR)):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (el[0], el[1], 0))
        out[f"forearm.{side}"] = ((el[0], el[1], 0), (wr[0], wr[1], 0.05))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * 0.30, KNEE, 0))
        out[f"shin.{side}"] = ((s * 0.30, KNEE, 0), (s * FOOT_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * FOOT_X, ANKLE, 0), (s * FOOT_X, 0.08, 0.5))
    return out


H.build("h05C", "biped", PALETTE, make, joints())
