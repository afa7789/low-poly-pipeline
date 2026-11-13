"""Keeper of the Grove (e009): medido em artifacts/model-sheets/refs/e009/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/e009.py -- <out.glb>

Crânio de cervo com galhada, poncho de pelo marrom com cordas, cajado de cogumelo na mão direita (antebraço R).
Pernas de cervo: o corpo de baixo usa os ossos thigh/shin/foot do biped (coxa, jarrete que dobra para trás, casco).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "skull": 0xE0D6DC, "bone_dk": 0x8E8590, "eye": 0xCCE040, "antler": 0x8B4A2B, "antler_dk": 0x6E3820,
    "cloak": 0x54402F, "cloak_dk": 0x45342A, "rope": 0x7A8A3A, "skin": 0x9A78B8, "skin_dk": 0x7A5690,
    "leg": 0x6A4478, "hoof": 0x3A1F40, "belt": 0x5A3A26, "loin": 0x6B7A3A, "jar": 0xB08A4A, "jar_dk": 0x6A4A2A,
    "staff": 0x4A2E1E, "glow": 0x70F050, "cap": 0x6B7A3A,
}

HIP, KNEE, ANKLE, LEG_X = 1.15, 0.58, 0.24, 0.3
KNEE_Z, ANKLE_Z = -0.12, -0.02
WAIST, NECK, TOP = 1.5, 2.15, 2.7
SH_X, SH_Y = 0.5, 1.95
STAFF = (0.74, 0.68)      # x, z do cajado (mao direita, adiante do corpo)


def skull():
    H.frustum("head", "skin", (0, 2.1, 0), (0, 2.38, 0.02), (0.16, 0.16), (0.14, 0.14), sides=6)                # pescoço
    H.frustum("head", "skull", (0, 2.4, -0.06), (0, 2.7, -0.06), (0.18, 0.21), (0.12, 0.16), sides=6)
    H.chain("head", "skull", [(0, 2.56, 0.05), (0, 2.42, 0.34), (0, 2.26, 0.64)],
            [(0.17, 0.16), (0.1, 0.1), (0.035, 0.035)], sides=6)
    H.frustum("head", "bone_dk", (0, 2.34, 0.3), (0, 2.28, 0.62), (0.05, 0.04), (0.02, 0.02), sides=4)
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.13, 2.55, 0.17), (0.07, 0.04, 0.05))


def antlers():
    for s in (-1, 1):
        beam = [(0.1, 2.66, -0.05), (0.3, 2.78, -0.2), (0.52, 2.95, -0.36), (0.72, 3.22, -0.5)]
        H.chain("head", "antler", [(s * x, y, z) for x, y, z in beam], [(0.06, 0.06), (0.055, 0.055), (0.045, 0.045), (0.02, 0.02)], sides=4)
        for (x, y, z), (tx, ty, tz) in (((0.3, 2.78, -0.2), (0.28, 3.15, -0.25)), ((0.52, 2.95, -0.36), (0.45, 3.3, -0.42)),
                                         ((0.62, 3.07, -0.43), (0.9, 3.2, -0.5))):
            H.chain("head", "antler_dk", [(s * x, y, z), (s * tx, ty, tz)], [(0.04, 0.04), (0.012, 0.012)], sides=4)


def poncho():
    H.frustum("spine", "cloak", (0, 1.45, 0), (0, 1.95, 0), (0.5, 0.38), (0.62, 0.42), sides=8)
    H.frustum("spine", "cloak", (0, 1.95, 0), (0, 2.32, 0), (0.62, 0.42), (0.2, 0.2), sides=8)
    H.frustum("spine", "cloak_dk", (0, 1.38, 0), (0, 1.48, 0), (0.54, 0.4), (0.51, 0.39), sides=8)             # barra
    for y, r in ((1.6, 0.54), (1.85, 0.6)):
        H.frustum("spine", "rope", (0, y, 0), (0, y + 0.07, 0), (r, r * 0.74), (r, r * 0.74), sides=8)
    H.panel("pelvis", "cloak_dk", [(0.5, 1.7, -0.42), (-0.5, 1.7, -0.42), (-0.42, 1.0, -0.46), (0, 0.7, -0.46), (0.42, 1.0, -0.46)], thickness=0.07)


def torso():
    H.frustum("pelvis", "skin", (0, HIP - 0.05, 0), (0, WAIST + 0.05, 0), (0.34, 0.26), (0.38, 0.28), sides=8)
    H.frustum("spine", "skin", (0, WAIST, 0), (0, 1.8, 0), (0.38, 0.28), (0.44, 0.3), sides=8)
    H.frustum("pelvis", "belt", (0, WAIST - 0.12, 0), (0, WAIST + 0.04, 0), (0.4, 0.3), (0.39, 0.29), sides=8)
    H.panel("pelvis", "loin", [(0.22, WAIST - 0.06, 0.3), (-0.22, WAIST - 0.06, 0.3), (-0.17, 0.78, 0.33), (0, 0.7, 0.34), (0.17, 0.78, 0.33)], thickness=0.06)
    H.frustum("pelvis", "jar_dk", (0.4, 1.06, 0.06), (0.4, 1.34, 0.06), (0.13, 0.13), (0.15, 0.15), sides=6)
    H.frustum("pelvis", "jar", (0.4, 1.12, 0.06), (0.4, 1.28, 0.06), (0.155, 0.155), (0.155, 0.155), sides=6)


def arm_hang():
    """Braço esquerdo (+x), pendurado, mão grande aberta."""
    H.frustum("arm.L", "skin", (SH_X, SH_Y, 0), (0.62, 1.4, 0.04), (0.2, 0.19), (0.16, 0.15), sides=6)
    H.frustum("forearm.L", "skin_dk", (0.62, 1.45, 0.04), (0.66, 1.0, 0.12), (0.16, 0.15), (0.13, 0.12), sides=6)
    H.frustum("forearm.L", "skin", (0.66, 1.08, 0.12), (0.66, 0.7, 0.2), (0.17, 0.11), (0.12, 0.07), sides=6)
    for dx in (-0.06, 0.0, 0.06):
        H.frustum("forearm.L", "skin_dk", (0.66 + dx, 0.8, 0.18), (0.66 + dx * 1.5, 0.52, 0.22), (0.035, 0.035), (0.01, 0.01), sides=4)


def arm_staff():
    """Braço direito (-x), estendido adiante segurando o cajado de cogumelo."""
    x, z = STAFF
    H.frustum("arm.R", "skin", (-SH_X, SH_Y, 0), (-0.62, 1.5, 0.12), (0.2, 0.19), (0.16, 0.15), sides=6)
    H.frustum("forearm.R", "skin_dk", (-0.62, 1.52, 0.1), (-0.7, 1.45, 0.45), (0.16, 0.15), (0.14, 0.13), sides=6)
    H.frustum("forearm.R", "skin", (-0.7, 1.45, 0.4), (-x, 1.42, z), (0.16, 0.14), (0.2, 0.2), sides=6)
    H.frustum("forearm.R", "staff", (-x, 0.0, z), (-x, 2.35, z), (0.055, 0.055), (0.045, 0.045), sides=6)
    for s in (-1, 1):
        H.frustum("forearm.R", "staff", (-x, 2.2, z), (-x + s * 0.12, 2.5, z), (0.04, 0.04), (0.025, 0.025), sides=4)
    H.frustum("forearm.R", "glow", (-x, 2.3, z), (-x, 2.58, z), (0.09, 0.09), (0.13, 0.13), sides=6)
    H.frustum("forearm.R", "cap", (-x, 2.55, z), (-x, 2.66, z), (0.17, 0.17), (0.22, 0.22), sides=8)
    H.frustum("forearm.R", "cap", (-x, 2.66, z), (-x, 2.74, z), (0.22, 0.22), (0.06, 0.06), sides=8)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * LEG_X
        H.frustum(f"thigh.{side}", "skin_dk", (x, HIP + 0.05, 0), (x, KNEE + 0.05, KNEE_Z), (0.22, 0.24), (0.17, 0.17), sides=6)
        H.frustum(f"shin.{side}", "leg", (x, KNEE + 0.06, KNEE_Z), (x, ANKLE + 0.1, ANKLE_Z), (0.17, 0.17), (0.14, 0.13), sides=6)
        H.frustum(f"foot.{side}", "hoof", (x, 0.4, ANKLE_Z), (x, 0.06, 0.0), (0.15, 0.14), (0.21, 0.2), sides=6)
        H.frustum(f"foot.{side}", "hoof", (x, 0.1, -0.1), (x, 0.06, 0.34), (0.17, 0.1), (0.14, 0.05), sides=4)


def make():
    skull()
    antlers()
    poncho()
    torso()
    arm_hang()
    arm_staff()
    legs()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    out["arm.L"] = ((SH_X, SH_Y, 0), (0.62, 1.45, 0.04))
    out["forearm.L"] = ((0.62, 1.45, 0.04), (0.66, 0.95, 0.1))
    out["arm.R"] = ((-SH_X, SH_Y, 0), (-0.62, 1.5, 0.1))
    out["forearm.R"] = ((-0.62, 1.5, 0.1), (-STAFF[0], 1.2, STAFF[1] * 0.5))
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, KNEE_Z))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, KNEE_Z), (s * LEG_X, ANKLE, ANKLE_Z))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, ANKLE_Z), (s * LEG_X, 0.08, 0.5))
    return out


H.build("e009", "biped", PALETTE, make, joints())
