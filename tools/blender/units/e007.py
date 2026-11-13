"""Druid (e007): medido em artifacts/model-sheets/refs/e007/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/e007.py -- <out.glb>

Elfo de capuz, barba verde, gola de penas, casaco longo, cajado de lua crescente na mao esquerda (antebraco L).
"""
import math
import pathlib
import sys

from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "coat": 0x6B4526, "coat_dk": 0x57391F, "moss": 0x5F6A38, "trim": 0x9078D8, "gold": 0xC09530,
    "fur": 0xEDE5D0, "fur_tip": 0x6B4526, "skin": 0x8F6AAE, "beard": 0x2F5A32, "tunic": 0x2F6B3A,
    "strap": 0x5A3A26, "band": 0x8C8A55, "breech": 0x3B2E3E, "boot": 0x3A2B3A, "sole": 0x1F1A20,
    "staff": 0x4A2E1E, "moon": 0xC4AEDD, "eye": 0xF0E040,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X = 1.0, 0.52, 0.16, 0.2, 0.26
WAIST, NECK, TOP = 1.35, 2.12, 2.70
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.55, 2.0, 0.62, 1.5, 1.2
STAFF = (0.71, 0.38)        # x, z do cajado: a mao esquerda o segura adiante do corpo


def hem(p):
    """A barra do casaco acompanha a coxa do seu lado; o topo fica na pelve."""
    if p[1] > 0.95:
        return {"pelvis": 1.0}
    return {"pelvis": 0.4, "thigh.L" if p[0] > 0 else "thigh.R": 0.6}


def head():
    H.frustum("head", "skin", (0, 2.2, 0.05), (0, 2.52, 0.05), (0.16, 0.2), (0.18, 0.21), sides=6)
    H.frustum("head", "skin", (0, 2.3, 0.2), (0, 2.38, 0.34), (0.04, 0.05), (0.03, 0.03), sides=4)         # nariz
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.08, 2.43, 0.27), (0.08, 0.04, 0.03))
        H.frustum("head", "skin", (s * 0.15, 2.44, -0.02), (s * 0.5, 2.58, -0.06), (0.05, 0.035), (0.008, 0.008), sides=4)
    H.chain("head", "beard", [(0, 2.3, 0.18), (0, 2.1, 0.3), (0, 1.9, 0.38)],
            [(0.17, 0.1), (0.15, 0.11), (0.03, 0.03)], sides=6)
    H.frustum("head", "coat", (0, 2.16, -0.12), (0, 2.5, -0.12), (0.3, 0.27), (0.27, 0.25), sides=8)       # capuz
    H.frustum("head", "coat", (0, 2.5, -0.12), (0, 2.7, -0.02), (0.27, 0.25), (0.07, 0.1), sides=8)
    H.frustum("head", "gold", (0, 2.24, 0.1), (0, 2.6, 0.08), (0.24, 0.05), (0.2, 0.05), sides=4)          # borda do capuz


def torso():
    H.frustum("spine", "coat", (0, WAIST - 0.04, 0), (0, 2.0, 0), (0.44, 0.34), (0.5, 0.36), sides=8)
    H.frustum("spine", "tunic", (0, WAIST, 0.28), (0, 2.0, 0.28), (0.15, 0.06), (0.18, 0.06), sides=4)       # tunica verde aberta
    H.frustum("spine", "strap", (0.35, 2.05, 0.3), (-0.3, 1.45, 0.34), (0.06, 0.03), (0.06, 0.03), sides=4)
    H.frustum("spine", "fur", (0, 1.88, 0), (0, 2.1, 0), (0.62, 0.45), (0.5, 0.38), sides=8)                # gola de penas
    H.frustum("spine", "fur_tip", (0, 1.82, 0), (0, 1.9, 0), (0.62, 0.46), (0.64, 0.47), sides=8)
    H.frustum("spine", "fur", (0, 2.1, 0), (0, 2.3, 0), (0.5, 0.38), (0.28, 0.28), sides=8)
    H.frustum("pelvis", "band", (0, WAIST - 0.14, 0), (0, WAIST + 0.04, 0), (0.43, 0.33), (0.41, 0.31), sides=8)
    skirt = H.frustum("pelvis", "coat", (0, 0.95, 0), (0, WAIST - 0.05, 0), (0.54, 0.35), (0.44, 0.33), sides=8)
    H.soft(skirt, hem)
    mid = H.frustum("pelvis", "moss", (0, 0.66, 0), (0, 1.12, 0), (0.55, 0.36), (0.5, 0.34), sides=8)
    H.soft(mid, hem)
    low = H.frustum("pelvis", "trim", (0, 0.58, 0), (0, 0.68, 0), (0.56, 0.37), (0.55, 0.36), sides=8)
    H.soft(low, hem)
    H.frustum("pelvis", "breech", (0, 0.9, 0), (0, 1.2, 0), (0.36, 0.3), (0.4, 0.32), sides=8)


def arm_pieces(s, side, fwd):
    a, f = f"arm.{side}", f"forearm.{side}"
    H.frustum(a, "coat", (s * SH_X, SH_Y + 0.05, 0), (s * EL_X, EL_Y - 0.03, 0), (0.22, 0.2), (0.18, 0.17), sides=6)
    H.frustum(f, "coat", (s * EL_X, EL_Y + 0.04, 0), (s * (EL_X + 0.03), EL_Y - 0.25, fwd * 0.6), (0.19, 0.18), (0.21, 0.2), sides=6)
    H.frustum(f, "moss", (s * (EL_X + 0.03), EL_Y - 0.25, fwd * 0.6), (s * (EL_X + 0.04), WR_Y - 0.02, fwd), (0.21, 0.2), (0.22, 0.21), sides=6)
    H.frustum(f, "skin", (s * (EL_X + 0.04), WR_Y - 0.02, fwd), (s * (EL_X + 0.04), WR_Y - 0.36, fwd + 0.06), (0.17, 0.12), (0.12, 0.08), sides=6)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        H.frustum(f"thigh.{side}", "breech", (s * KNEE_X, KNEE - 0.04, 0), (s * LEG_X, HIP + 0.04, 0), (0.2, 0.22), (0.24, 0.26), sides=6)
        H.frustum(f"shin.{side}", "band", (s * KNEE_X, ANKLE - 0.02, 0), (s * KNEE_X, KNEE + 0.02, 0), (0.15, 0.16), (0.2, 0.21), sides=6)
        H.frustum(f"shin.{side}", "breech", (s * KNEE_X, KNEE - 0.04, 0), (s * KNEE_X, KNEE + 0.1, 0), (0.2, 0.2), (0.22, 0.22), sides=6)
        H.frustum(f"foot.{side}", "boot", (s * KNEE_X, 0.03, -0.04), (s * KNEE_X, ANKLE + 0.04, -0.04), (0.17, 0.2), (0.16, 0.18), sides=6)
        H.frustum(f"foot.{side}", "boot", (s * KNEE_X, 0.1, 0.04), (s * KNEE_X, 0.08, 0.42), (0.17, 0.1), (0.15, 0.06), sides=4)
        H.frustum(f"foot.{side}", "sole", (s * KNEE_X, 0.02, -0.18), (s * KNEE_X, 0.02, 0.44), (0.18, 0.022), (0.16, 0.022), sides=4)


def staff():
    x, z = STAFF
    H.frustum("forearm.L", "staff", (x, 0.0, z), (x, 2.4, z), (0.05, 0.05), (0.045, 0.045), sides=6)
    cy, cz, r = 2.62, z, 0.26
    pts = [Vector((x + r * math.cos(math.radians(t)), cy + r * math.sin(math.radians(t)), cz)) for t in range(50, 331, 35)]
    widths = [0.025, 0.06, 0.075, 0.08, 0.08, 0.075, 0.06, 0.04, 0.025]
    H.chain("forearm.L", "moon", pts, [(w, 0.05) for w in widths], sides=4)


def make():
    head()
    torso()
    legs()
    arm_pieces(1, "L", 0.38)
    arm_pieces(-1, "R", 0.08)
    staff()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * (EL_X + 0.04), WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * KNEE_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * KNEE_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * KNEE_X, ANKLE, 0), (s * KNEE_X, 0.06, 0.5))
    return out


H.build("e007", "biped", PALETTE, make, joints())
