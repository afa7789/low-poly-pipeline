"""Heavy Gunner (h0A2): medido em artifacts/model-sheets/refs/h0A2/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/h0A2.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "coat": 0x3E4636, "coat_dk": 0x2E352A, "hood": 0x545B46, "belt": 0x6A4630, "steel": 0x3A3C42,
    "steel_lt": 0x6E7078, "gold": 0xD0A040, "skin": 0x6E4A38, "trouser": 0x6E4C38, "boot": 0x5A5D66,
    "sole": 0x25262A, "wood": 0x6A4630, "black": 0x17181B,
}

HIP, KNEE, ANKLE, LEG_X = 0.95, 0.55, 0.2, 0.4
WAIST, NECK, TOP = 1.3, 2.0, 2.7
SH_X, SH_Y = 0.72, 1.95
EL, WR = (0.88, 1.5, 0.0), (0.74, 1.1, 0.0)
SKIRT_MID = 0.95


def hem(p):
    """A barra do casaco acompanha a coxa do seu lado."""
    if p[1] > SKIRT_MID:
        return {"pelvis": 1.0}
    return {"pelvis": 0.4, "thigh.L" if p[0] > 0 else "thigh.R": 0.6}


def head():
    H.frustum("head", "hood", (0, 2.0, 0), (0, 2.55, 0), (0.34, 0.34), (0.32, 0.32), sides=8)
    H.frustum("head", "hood", (0, 2.55, 0), (0, 2.72, 0), (0.32, 0.32), (0.1, 0.1), sides=8)
    H.box("head", "skin", (0, 2.3, 0.28), (0.3, 0.32, 0.08))
    H.box("head", "black", (0, 2.36, 0.325), (0.24, 0.05, 0.02))


def torso():
    H.frustum("spine", "coat", (0, WAIST - 0.04, 0), (0, 1.9, 0), (0.55, 0.46), (0.7, 0.5), sides=8)
    H.frustum("spine", "coat", (0, 1.9, 0), (0, 2.1, 0), (0.7, 0.5), (0.4, 0.36), sides=8)
    H.frustum("spine", "hood", (0, 1.95, 0), (0, 2.12, 0), (0.46, 0.42), (0.34, 0.32), sides=8)
    H.box("spine", "gold", (0.25, 1.8, 0.5), (0.2, 0.1, 0.04))
    H.frustum("spine", "belt", (-0.35, 1.95, 0.42), (0.3, 1.35, 0.5), (0.07, 0.03), (0.07, 0.03), sides=4)
    # caixa de munição nas costas, aberta, com as balas douradas
    H.box("spine", "wood", (0, 1.85, -0.58), (0.84, 0.8, 0.4))
    H.box("spine", "gold", (0, 2.27, -0.58), (0.7, 0.06, 0.3))


def pelvis():
    H.frustum("pelvis", "belt", (0, WAIST - 0.1, 0), (0, WAIST + 0.06, 0), (0.58, 0.49), (0.58, 0.49), sides=8)
    H.frustum("pelvis", "trouser", (0, 0.8, 0), (0, 1.1, 0), (0.45, 0.35), (0.5, 0.4), sides=8)
    skirt = H.frustum("pelvis", "coat", (0, 0.6, 0), (0, WAIST - 0.06, 0), (0.64, 0.52), (0.52, 0.46), sides=8)
    H.soft(skirt, hem)


def leg(s, side):
    kx = s * LEG_X
    H.frustum(f"thigh.{side}", "trouser", (kx, KNEE - 0.04, 0), (kx, HIP + 0.04, 0), (0.28, 0.3), (0.33, 0.33), sides=6)
    H.frustum(f"shin.{side}", "boot", (kx, ANKLE - 0.02, 0), (kx, 0.5, 0), (0.2, 0.22), (0.24, 0.26), sides=6)
    H.frustum(f"foot.{side}", "boot", (kx, 0.03, -0.05), (kx, ANKLE + 0.05, -0.05), (0.23, 0.27), (0.21, 0.25), sides=6)
    H.frustum(f"foot.{side}", "boot", (kx, 0.12, 0.05), (kx, 0.1, 0.5), (0.23, 0.14), (0.2, 0.1), sides=4)
    H.frustum(f"foot.{side}", "sole", (kx, 0.02, -0.25), (kx, 0.02, 0.52), (0.24, 0.025), (0.21, 0.025), sides=4)


def arm(s, side):
    """Manga bufante, antebraço e manopla grande e cinza."""
    sx, ex, wx = s * SH_X, s * EL[0], s * WR[0]
    H.frustum(f"arm.{side}", "coat", (sx - s * 0.1, 2.02, 0), (sx, 1.85, 0), (0.3, 0.3), (0.32, 0.32), sides=6)
    H.frustum(f"arm.{side}", "coat", (sx, 1.9, 0), (ex, EL[1], 0), (0.32, 0.32), (0.26, 0.27), sides=6)
    H.frustum(f"forearm.{side}", "coat", (ex, EL[1] + 0.05, 0), (wx, WR[1] + 0.2, 0), (0.26, 0.27), (0.23, 0.24), sides=6)
    H.frustum(f"forearm.{side}", "steel_lt", (wx, WR[1] + 0.3, 0), (wx - s * 0.02, WR[1] - 0.12, 0.04), (0.2, 0.2), (0.27, 0.25), sides=6)


def gun():
    """Metralhadora pesada no quadril: cano elevado, caixa, tambor lateral, barra de empunhadura e coronha."""
    f = "forearm.L"
    breech, muzzle, mid = (0, 1.5, 0.35), (0, 2.3, 1.85), (0, 1.95, 1.1)
    H.frustum(f, "steel", breech, mid, (0.22, 0.22), (0.22, 0.22), sides=8)
    H.frustum(f, "steel", mid, muzzle, (0.22, 0.22), (0.28, 0.28), sides=8)
    H.frustum(f, "black", (0, 2.2, 1.62), (0, 2.3, 1.85), (0.17, 0.17), (0.13, 0.13), sides=8)
    H.frustum(f, "steel", (0, 1.2, 0.1), (0, 1.6, 0.55), (0.3, 0.26), (0.32, 0.3), sides=6)
    H.wheel(f, "steel", (0.74, 1.12, 0.4), 0.34, 0.34, sides=8)
    H.frustum(f, "steel_lt", (-0.85, 1.05, 0.5), (0.7, 1.05, 0.5), (0.07, 0.07), (0.07, 0.07), sides=6)
    H.frustum(f, "wood", (0, 1.3, 0.05), (0, 0.9, -0.5), (0.14, 0.2), (0.18, 0.28), sides=4)
    H.frustum(f, "steel", (0, 1.15, 0.5), (0, 1.05, 0.5), (0.12, 0.12), (0.14, 0.14), sides=6)


def make():
    head()
    torso()
    pelvis()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        arm(s, side)
    gun()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL[0], EL[1], 0))
        out[f"forearm.{side}"] = ((s * EL[0], EL[1], 0), (s * WR[0], WR[1], 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("h0A2", "biped", PALETTE, make, joints())
