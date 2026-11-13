"""Jade Elder (n03M): medido em artifacts/model-sheets/refs/n03M/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n03M.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "navy": 0x3F4A62, "navy_dk": 0x2C2F3A, "jade": 0xC7D3C2, "jade_dk": 0x9FB19C, "bead": 0x2E9A6A, "bead_dk": 0x1F6F4C,
    "skin": 0xC09878, "skin_dk": 0xA37F62, "hat": 0xC8A060, "hat_dk": 0x9E7C48, "urn": 0x7A4332, "urn_dk": 0x5A2F23,
    "wood": 0x6A4028, "strap": 0x6B4830, "blade": 0x2F8A64, "black": 0x1E1C22, "pants": 0x303038, "tan": 0xD0A869,
}

HIP, WAIST, NECK, TOP = 0.9, 1.4, 1.7, 2.5
KNEE, ANKLE, LEG_X = 0.5, 0.1, 0.34
POLE_X, POLE_Z = -0.82, 0.55


def hem(p):
    """A barra da túnica acompanha a coxa do seu lado; o topo fica na pelve."""
    k = max(0.0, min(0.65, (1.0 - p[1]) * 1.1))
    if k < 0.05:
        return {"pelvis": 1.0}
    return {"pelvis": 1 - k, "thigh.L" if p[0] > 0 else "thigh.R": k}


def head():
    H.frustum("head", "skin", (0, 1.55, 0.0), (0, 2.06, 0.0), (0.22, 0.22), (0.21, 0.21), sides=6)
    H.frustum("head", "bead_dk", (0, 1.52, 0), (0, 1.8, 0), (0.34, 0.31), (0.37, 0.34), sides=8)       # cortina de contas
    H.frustum("head", "bead", (0, 1.8, 0), (0, 2.1, 0), (0.37, 0.34), (0.34, 0.31), sides=8)
    H.frustum("head", "hat_dk", (0, 2.08, -0.06), (0, 2.14, -0.06), (0.64, 0.62), (0.6, 0.58), sides=8)  # aba do chapéu
    H.frustum("head", "hat", (0, 2.14, -0.06), (0, 2.52, -0.06), (0.6, 0.58), (0.04, 0.04), sides=8)    # cone


def torso():
    H.frustum("pelvis", "navy", (0, 0.86, 0), (0, WAIST, 0.02), (0.58, 0.5), (0.62, 0.54), sides=8)
    H.frustum("spine", "navy", (0, WAIST, 0.02), (0, 1.66, 0.0), (0.62, 0.54), (0.55, 0.46), sides=8)
    H.frustum("spine", "navy", (0, 1.66, 0.0), (0, 1.8, 0.0), (0.55, 0.46), (0.3, 0.28), sides=8)
    H.frustum("pelvis", "strap", (0, 1.06, 0), (0, 1.18, 0), (0.64, 0.56), (0.64, 0.56), sides=8)      # cinto
    low = H.frustum("pelvis", "navy_dk", (0, 0.4, 0), (0, 0.56, 0), (0.68, 0.58), (0.65, 0.56), sides=8)
    skirt = H.frustum("pelvis", "navy", (0, 0.56, 0), (0, 1.0, 0), (0.65, 0.56), (0.6, 0.52), sides=8)
    H.soft(low, hem)
    H.soft(skirt, hem)
    H.frustum("spine", "jade_dk", (0, 1.55, 0.56), (0, 1.0, 0.58), (0.4, 0.05), (0.38, 0.05), sides=4)  # peitoral de jade
    H.frustum("spine", "jade", (0, 1.52, 0.6), (0, 1.04, 0.62), (0.35, 0.03), (0.33, 0.03), sides=4)
    for s in (-1, 1):
        H.frustum("pelvis", "jade_dk", (s * 0.48, 1.04, 0.42), (s * 0.5, 0.56, 0.36), (0.17, 0.05), (0.17, 0.05), sides=4)
        H.frustum("pelvis", "jade", (s * 0.48, 1.0, 0.45), (s * 0.5, 0.6, 0.39), (0.14, 0.03), (0.14, 0.03), sides=4)


def urn():
    b = "spine"
    z = -0.66
    H.box(b, "tan", (0, 1.12, z + 0.04), (0.9, 0.06, 0.8))                                              # prateleira
    H.frustum(b, "urn", (0, 1.15, z), (0, 1.5, z), (0.24, 0.24), (0.34, 0.34), sides=8)
    H.frustum(b, "urn", (0, 1.5, z), (0, 1.85, z), (0.34, 0.34), (0.37, 0.37), sides=8)
    H.frustum(b, "urn", (0, 1.85, z), (0, 2.14, z), (0.37, 0.37), (0.15, 0.15), sides=8)
    H.frustum(b, "urn_dk", (0, 2.14, z), (0, 2.3, z), (0.15, 0.15), (0.2, 0.2), sides=8)
    H.frustum(b, "wood", (0, 2.3, z), (0, 2.36, z), (0.2, 0.2), (0.18, 0.18), sides=8)
    H.box(b, "tan", (0, 1.62, z + 0.36), (0.8, 0.9, 0.05))                                              # tábua atrás


def legs(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "pants", (x, KNEE - 0.04, 0), (x, HIP + 0.04, 0), (0.2, 0.22), (0.27, 0.27), sides=6)
    H.frustum(f"shin.{side}", "skin", (x, 0.1, 0), (x, KNEE + 0.02, 0), (0.15, 0.16), (0.2, 0.2), sides=6)
    H.frustum(f"foot.{side}", "black", (x, 0.1, 0.0), (x, 0.08, 0.3), (0.2, 0.12), (0.17, 0.08), sides=4)
    H.frustum(f"foot.{side}", "black", (x, 0.02, -0.16), (x, 0.02, 0.32), (0.21, 0.02), (0.18, 0.02), sides=4)


def arm_left():
    H.frustum("arm.L", "navy", (0.5, 1.7, 0), (0.78, 1.32, 0.0), (0.2, 0.24), (0.27, 0.27), sides=6)
    H.frustum("forearm.L", "navy", (0.78, 1.36, 0), (0.82, 1.02, 0.0), (0.26, 0.26), (0.23, 0.23), sides=6)
    H.frustum("forearm.L", "navy_dk", (0.82, 1.04, 0), (0.82, 0.88, 0.0), (0.23, 0.23), (0.19, 0.19), sides=6)   # punho da manga
    H.frustum("forearm.L", "skin", (0.82, 0.9, 0), (0.82, 0.62, 0.02), (0.14, 0.15), (0.12, 0.13), sides=6)       # mão


def arm_right():
    H.frustum("arm.R", "navy", (-0.5, 1.7, 0), (-0.76, 1.46, 0.1), (0.2, 0.24), (0.27, 0.27), sides=6)
    H.frustum("forearm.R", "navy", (-0.76, 1.5, 0.1), (-0.8, 1.38, 0.34), (0.26, 0.26), (0.22, 0.22), sides=6)
    H.frustum("forearm.R", "navy_dk", (-0.8, 1.38, 0.34), (-0.82, 1.32, 0.44), (0.2, 0.2), (0.17, 0.17), sides=6)
    H.frustum("forearm.R", "skin", (-0.82, 1.5, 0.55), (-0.82, 1.18, 0.55), (0.14, 0.14), (0.13, 0.13), sides=6)  # punho no cabo


def glaive():
    b = "forearm.R"
    H.frustum(b, "wood", (POLE_X, 0.0, POLE_Z), (POLE_X, 2.0, POLE_Z), (0.045, 0.045), (0.04, 0.04), sides=6)
    H.frustum(b, "blade", (POLE_X, 1.98, POLE_Z), (POLE_X, 2.1, POLE_Z), (0.07, 0.07), (0.07, 0.07), sides=6)
    H.chain(b, "blade", [(POLE_X, 2.1, POLE_Z), (POLE_X + 0.01, 2.4, POLE_Z), (POLE_X - 0.03, 2.72, POLE_Z),
                         (POLE_X - 0.06, 2.96, POLE_Z)], [(0.08, 0.03), (0.1, 0.03), (0.07, 0.025), (0.01, 0.01)], sides=4)
    H.chain(b, "blade", [(POLE_X + 0.06, 2.28, POLE_Z), (POLE_X + 0.2, 2.34, POLE_Z), (POLE_X + 0.2, 2.5, POLE_Z)],
            [(0.06, 0.03), (0.05, 0.03), (0.01, 0.01)], sides=4)


def barrel():
    b = "pelvis"
    H.frustum(b, "wood", (-0.84, 0.76, -0.45), (-0.84, 0.76, -0.1), (0.2, 0.2), (0.27, 0.27), sides=8)
    H.frustum(b, "wood", (-0.84, 0.76, -0.1), (-0.84, 0.76, 0.28), (0.27, 0.27), (0.2, 0.2), sides=8)
    H.frustum(b, "strap", (-0.84, 0.76, -0.2), (-0.84, 0.76, -0.14), (0.285, 0.285), (0.285, 0.285), sides=8)
    H.frustum(b, "strap", (-0.84, 0.76, 0.1), (-0.84, 0.76, 0.16), (0.285, 0.285), (0.285, 0.285), sides=8)
    H.frustum(b, "urn_dk", (-0.84, 0.76, 0.28), (-0.84, 0.76, 0.3), (0.19, 0.19), (0.17, 0.17), sides=8)


def make():
    head()
    torso()
    urn()
    arm_left()
    arm_right()
    glaive()
    barrel()
    for s, side in ((1, "L"), (-1, "R")):
        legs(s, side)


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0)),
           "arm.L": ((0.5, 1.7, 0), (0.78, 1.36, 0)), "forearm.L": ((0.78, 1.36, 0), (0.82, 0.9, 0)),
           "arm.R": ((-0.5, 1.7, 0), (-0.76, 1.5, 0.1)), "forearm.R": ((-0.76, 1.5, 0.1), (-0.82, 1.15, 0.5))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, -0.04), (s * LEG_X, 0.06, 0.4))
    return out


H.build("n03M", "biped", PALETTE, make, joints())
