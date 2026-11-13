"""Holy Warrior (h074): medido em artifacts/model-sheets/refs/h074/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/h074.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "armor": 0x77757C, "armor_dk": 0x5A585F, "olive": 0x6E6A3C, "brown": 0x6E4426, "under": 0x2B2B30,
    "cream": 0xC9B98E, "cream_dk": 0xA3946B, "skin": 0xD09B80, "hair": 0x2E2A2A, "boot": 0x4A352E,
    "sole": 0x1F1D1F, "strap": 0x4A3326, "gold": 0xB8944A, "steel": 0x8A8D94, "guard": 0x3A3C42,
}

HIP, KNEE, ANKLE, LEG_X = 1.08, 0.55, 0.17, 0.23
WAIST, NECK, TOP = 1.53, 2.2, 2.7
SH_X, SH_Y, EL_Y = 0.5, 2.2, 1.72
HAND = (0.64, 1.47, 0.45)      # a mão esquerda segura a espada, ponta para baixo
SWORD_X, SWORD_Z = 0.66, 0.45
SKIRT_MID = 1.15


def hem(p):
    """A barra da túnica acompanha a coxa do seu lado."""
    if p[1] > SKIRT_MID:
        return {"pelvis": 1.0}
    return {"pelvis": 0.45, "thigh.L" if p[0] > 0 else "thigh.R": 0.55}


def head():
    H.frustum("head", "under", (0, 2.1, 0), (0, 2.3, 0), (0.21, 0.2), (0.17, 0.17), sides=8)
    H.frustum("head", "skin", (0, 2.24, 0.01), (0, 2.58, 0.02), (0.14, 0.16), (0.155, 0.17), sides=6)
    H.frustum("head", "hair", (0, 2.5, 0.0), (0, 2.7, 0.0), (0.16, 0.18), (0.13, 0.15), sides=6)
    H.frustum("head", "hair", (0, 2.3, -0.1), (0, 2.58, -0.1), (0.14, 0.09), (0.16, 0.1), sides=6)


def torso():
    H.frustum("spine", "olive", (0, 1.5, 0), (0, 2.1, 0), (0.3, 0.23), (0.41, 0.27), sides=8)
    H.frustum("spine", "armor_dk", (0, 2.1, 0), (0, 2.3, 0), (0.41, 0.27), (0.22, 0.2), sides=8)
    H.box("spine", "brown", (-0.17, 1.8, -0.255), (0.3, 0.6, 0.03))
    for s in (-1, 1):
        H.frustum("spine", "strap", (s * 0.34, 2.15, 0.27), (-s * 0.3, 1.55, 0.3), (0.07, 0.03), (0.07, 0.03), sides=4)
        H.frustum("spine", "strap", (s * 0.34, 2.15, -0.27), (-s * 0.3, 1.55, -0.3), (0.07, 0.03), (0.07, 0.03), sides=4)
    for t in (0.2, 0.4, 0.6):       # cartucheiras no X do peito
        H.box("spine", "gold", (0.34 - 0.64 * t, 2.15 - 0.6 * t, 0.31), (0.1, 0.1, 0.07))


def pelvis():
    H.frustum("pelvis", "strap", (0, 1.43, 0), (0, 1.58, 0), (0.33, 0.27), (0.33, 0.27), sides=8)
    H.frustum("pelvis", "under", (0, 0.95, 0), (0, 1.2, 0), (0.3, 0.24), (0.34, 0.26), sides=8)
    skirt = H.frustum("pelvis", "olive", (0, 0.82, 0), (0, 1.46, 0), (0.4, 0.3), (0.31, 0.26), sides=8)
    H.soft(skirt, hem)
    band = H.frustum("pelvis", "brown", (0, 0.74, 0), (0, 0.86, 0), (0.42, 0.32), (0.4, 0.3), sides=8)
    H.soft(band, hem)


def leg(s, side):
    kx = s * LEG_X
    H.frustum(f"thigh.{side}", "under", (kx, KNEE - 0.04, 0), (kx, HIP + 0.04, 0), (0.18, 0.2), (0.23, 0.25), sides=6)
    H.frustum(f"shin.{side}", "cream", (kx, ANKLE - 0.02, 0), (kx, KNEE + 0.02, 0), (0.15, 0.16), (0.19, 0.2), sides=6)
    for y0 in (0.26, 0.38):
        H.frustum(f"shin.{side}", "cream_dk", (kx, y0, 0), (kx, y0 + 0.05, 0), (0.165, 0.175), (0.17, 0.18), sides=6)
    H.frustum(f"foot.{side}", "boot", (kx, 0.03, -0.02), (kx, ANKLE + 0.05, -0.02), (0.2, 0.22), (0.18, 0.2), sides=6)
    H.frustum(f"foot.{side}", "boot", (kx, 0.11, 0.06), (kx, 0.085, 0.42), (0.2, 0.11), (0.17, 0.06), sides=4)
    H.frustum(f"foot.{side}", "sole", (kx, 0.02, -0.2), (kx, 0.02, 0.44), (0.21, 0.022), (0.18, 0.022), sides=4)


def shoulder(s, side):
    """Ombreira grande em três placas e espigão, sobre o osso do braço."""
    a = f"arm.{side}"
    H.frustum(a, "armor_dk", (s * 0.5, 1.88, 0), (s * 0.52, 2.08, 0), (0.25, 0.28), (0.27, 0.3), sides=6)
    H.frustum(a, "armor", (s * 0.52, 2.06, 0), (s * 0.52, 2.26, 0), (0.27, 0.3), (0.22, 0.26), sides=6)
    H.frustum(a, "armor", (s * 0.52, 2.26, 0), (s * 0.46, 2.4, 0), (0.22, 0.26), (0.12, 0.16), sides=6)
    H.frustum(a, "armor", (s * 0.38, 2.38, -0.05), (s * 0.3, 2.64, -0.08), (0.09, 0.07), (0.01, 0.01), sides=4)


def arm_upper(s, side):
    a = f"arm.{side}"
    H.frustum(a, "under", (s * 0.5, 1.7, 0), (s * 0.5, 2.1, 0), (0.14, 0.15), (0.19, 0.2), sides=6)
    H.frustum(a, "cream", (s * 0.54, 1.9, 0), (s * 0.54, 2.0, 0), (0.18, 0.19), (0.18, 0.19), sides=6)


def right_forearm():
    H.frustum("forearm.R", "armor", (-0.52, EL_Y + 0.04, 0), (-0.53, 1.3, 0), (0.15, 0.16), (0.17, 0.18), sides=6)
    H.frustum("forearm.R", "skin", (-0.53, 1.34, 0), (-0.53, 1.1, 0.02), (0.16, 0.17), (0.14, 0.15), sides=6)


def left_forearm_and_sword():
    f = "forearm.L"
    H.frustum(f, "armor", (0.52, EL_Y + 0.04, -0.02), (0.63, 1.5, 0.41), (0.15, 0.16), (0.17, 0.18), sides=6)
    H.frustum(f, "skin", (HAND[0], 1.4, HAND[2]), (HAND[0], 1.6, HAND[2]), (0.14, 0.14), (0.14, 0.14), sides=6)
    x, z = SWORD_X, SWORD_Z
    H.frustum(f, "steel", (x, 0.02, z), (x, 0.16, z), (0.005, 0.01), (0.075, 0.04), sides=4)
    H.frustum(f, "steel", (x, 0.16, z), (x, 1.15, z), (0.075, 0.04), (0.08, 0.045), sides=4)
    H.box(f, "guard", (x, 1.26, z), (0.27, 0.2, 0.18))
    H.frustum(f, "guard", (x, 1.15, z), (x, 1.8, z), (0.05, 0.05), (0.045, 0.045), sides=6)
    H.frustum(f, "guard", (x, 1.78, z), (x, 1.94, z + 0.1), (0.045, 0.045), (0.04, 0.04), sides=6)


def make():
    head()
    torso()
    pelvis()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        shoulder(s, side)
        arm_upper(s, side)
    right_forearm()
    left_forearm_and_sword()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * 0.52, EL_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    out["forearm.L"] = ((0.52, EL_Y, 0), HAND)
    out["forearm.R"] = ((-0.52, EL_Y, 0), (-0.53, 1.2, 0))
    return out


H.build("h074", "biped", PALETTE, make, joints())
