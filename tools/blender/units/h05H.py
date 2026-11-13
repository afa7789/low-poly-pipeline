"""Vampire Lord (h05H): medido em artifacts/model-sheets/refs/h05H/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/h05H.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "skin": 0x9A6A86, "skin_dk": 0x7E5470, "armor": 0x28242E, "armor_dk": 0x1D1A23, "purple": 0x4A2C6E,
    "purple_dk": 0x38214F, "gold": 0xD2A23C, "claw": 0xEADAB8, "eye": 0xA8FF2E, "horn": 0x3A3430,
    "membrane": 0x1F1B26, "boot": 0x1F1C24, "hair": 0x15131A, "blood": 0xB02A2A,
}

HIP, KNEE, ANKLE, LEG_X, FOOT_X = 1.0, 0.60, 0.20, 0.20, 0.30
WAIST, NECK, TOP = 1.40, 2.28, 2.75
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.62, 2.22, 0.74, 1.62, 1.05
SKIRT_MID = 0.85


def hem(p):
    """A barra do manto acompanha a coxa do seu lado."""
    if p[1] > SKIRT_MID + 0.3:
        return {"pelvis": 1.0}
    return {"pelvis": 0.4, "thigh.L" if p[0] > 0 else "thigh.R": 0.6}


def wp(x, y, s=1):
    """Ponto no plano da asa: inclina para trás conforme se afasta do corpo."""
    return (s * x, y, -0.32 - 0.1 * (x - 0.4))


def head():
    H.frustum("head", "purple", (0, 2.2, -0.08), (0, 2.66, -0.1), (0.36, 0.2), (0.28, 0.16), sides=6)    # gola alta
    H.frustum("head", "skin", (0, 2.3, 0.04), (0, 2.6, 0.06), (0.17, 0.19), (0.2, 0.21), sides=6)
    H.frustum("head", "skin", (0, 2.3, 0.12), (0, 2.42, 0.2), (0.11, 0.1), (0.1, 0.07), sides=4)        # queixo
    H.frustum("head", "hair", (0, 2.52, 0.0), (0, 2.66, 0.0), (0.22, 0.24), (0.17, 0.19), sides=8)
    H.frustum("head", "hair", (0, 2.66, 0.0), (0, 2.72, 0.0), (0.17, 0.19), (0.1, 0.1), sides=8)
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.085, 2.5, 0.24), (0.075, 0.04, 0.03))
        H.box("head", "claw", (s * 0.045, 2.34, 0.24), (0.025, 0.07, 0.03))
        H.chain("head", "horn", [(s * 0.17, 2.62, 0.0), (s * 0.34, 2.72, 0.0), (s * 0.34, 2.98, 0.0)],
                [(0.07, 0.07), (0.06, 0.06), (0.05, 0.05)], sides=6)
        H.frustum("head", "gold", (s * 0.34, 2.98, 0.0), (s * 0.24, 3.28, 0.0), (0.05, 0.05), (0.008, 0.008), sides=6)


def torso():
    H.frustum("spine", "armor", (0, WAIST - 0.04, 0), (0, 1.85, 0), (0.33, 0.32), (0.47, 0.38), sides=8)
    H.frustum("spine", "armor", (0, 1.85, 0), (0, 2.3, 0), (0.47, 0.38), (0.3, 0.3), sides=8)
    H.frustum("spine", "gold", (0, 2.05, 0.3), (0, 2.12, 0.33), (0.3, 0.02), (0.14, 0.02), sides=4)
    H.frustum("spine", "purple", (0.0, 1.42, 0.22), (0, 1.8, 0.24), (0.14, 0.04), (0.2, 0.04), sides=4)
    for s in (-1, 1):       # ombreiras negras e largas, borda dourada
        H.frustum("spine", "armor_dk", (s * 0.28, 2.34, 0), (s * 0.66, 2.18, 0), (0.19, 0.34), (0.2, 0.32), sides=6)
        H.frustum("spine", "gold", (s * 0.6, 2.2, 0), (s * 0.7, 2.14, 0), (0.15, 0.3), (0.1, 0.26), sides=6)
    H.frustum("pelvis", "armor_dk", (0, WAIST - 0.1, 0), (0, WAIST + 0.06, 0), (0.42, 0.33), (0.42, 0.33), sides=8)    # cinto
    skirt = H.frustum("pelvis", "purple", (0, 0.46, 0), (0, WAIST - 0.05, 0), (0.6, 0.46), (0.38, 0.36), sides=8)
    H.soft(skirt, hem)
    H.frustum("pelvis", "armor", (0, 0.86, 0), (0, 1.15, 0), (0.34, 0.28), (0.36, 0.3), sides=8)


def wings():
    for s in (-1, 1):
        # osso do braço da asa em ouro, membrana negra em placas na coluna
        for a, b in (((0.4, 2.35), (0.46, 3.3)), ((0.4, 2.35), (1.1, 2.0)), ((1.1, 2.0), (0.95, 1.3))):
            H.frustum("spine", "gold", wp(*a, s), wp(*b, s), (0.05, 0.05), (0.035, 0.035), sides=6)
        H.frustum("spine", "claw", wp(0.46, 3.3, s), wp(0.38, 3.52, s), (0.04, 0.04), (0.006, 0.006), sides=6)
        H.panel("spine", "membrane", [wp(0.44, 3.25, s), wp(0.4, 2.35, s), wp(0.95, 1.3, s), wp(1.1, 2.0, s), wp(0.92, 2.8, s)], 0.03)
        H.panel("spine", "membrane", [wp(0.4, 2.35, s), wp(0.4, 1.7, s), wp(0.95, 1.3, s)], 0.03)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        H.frustum(f"thigh.{side}", "armor", (s * 0.27, KNEE - 0.04, 0), (s * LEG_X, HIP + 0.04, 0), (0.17, 0.19), (0.22, 0.24), sides=6)
        H.frustum(f"shin.{side}", "boot", (s * FOOT_X, ANKLE - 0.02, 0), (s * 0.27, KNEE + 0.02, 0), (0.15, 0.17), (0.2, 0.21), sides=6)
        H.frustum(f"shin.{side}", "armor_dk", (s * 0.28, 0.45, 0.02), (s * 0.27, 0.66, 0.02), (0.2, 0.2), (0.23, 0.23), sides=6)
        H.frustum(f"foot.{side}", "boot", (s * FOOT_X, 0.03, -0.05), (s * FOOT_X, ANKLE + 0.04, -0.05), (0.18, 0.21), (0.15, 0.17), sides=6)
        H.frustum(f"foot.{side}", "boot", (s * FOOT_X, 0.1, 0.05), (s * FOOT_X, 0.07, 0.42), (0.18, 0.12), (0.17, 0.06), sides=4)
        for dx in (-0.1, 0, 0.1):
            H.frustum(f"foot.{side}", "claw", (s * FOOT_X + dx, 0.06, 0.4), (s * FOOT_X + dx * 1.3, 0.04, 0.6), (0.04, 0.04), (0.01, 0.01), sides=4)


def arms():
    for s, side in ((1, "L"), (-1, "R")):
        H.frustum(f"arm.{side}", "skin", (s * SH_X, SH_Y + 0.06, 0), (s * EL_X, EL_Y - 0.02, 0), (0.21, 0.22), (0.17, 0.18), sides=6)
        H.frustum(f"arm.{side}", "skin_dk", (s * 0.66, 1.98, 0), (s * 0.7, 1.84, 0), (0.22, 0.23), (0.2, 0.21), sides=6)
        # manopla negra larga que alarga até a mão; garras longas, pálidas
        H.frustum(f"forearm.{side}", "armor", (s * EL_X, EL_Y + 0.04, 0), (s * EL_X, WR_Y + 0.02, 0.02), (0.17, 0.18), (0.23, 0.24), sides=6)
        H.frustum(f"forearm.{side}", "armor_dk", (s * EL_X, WR_Y + 0.06, 0.02), (s * EL_X, WR_Y + 0.12, 0.02), (0.25, 0.26), (0.25, 0.26), sides=6)
        H.frustum(f"forearm.{side}", "armor", (s * EL_X, WR_Y + 0.02, 0.02), (s * EL_X, WR_Y - 0.2, 0.04), (0.2, 0.22), (0.16, 0.18), sides=6)
        for dz, dx in ((-0.12, 0.05), (0.02, 0.0), (0.16, -0.05)):
            H.frustum(f"forearm.{side}", "claw", (s * (EL_X + dx), WR_Y - 0.16, dz), (s * (EL_X + dx - 0.02), WR_Y - 0.7, dz + 0.06), (0.05, 0.05), (0.008, 0.008), sides=4)
        H.frustum(f"forearm.{side}", "claw", (s * (EL_X - 0.14), WR_Y - 0.1, 0.08), (s * (EL_X - 0.2), WR_Y - 0.5, 0.2), (0.04, 0.04), (0.008, 0.008), sides=4)


def make():
    head()
    torso()
    wings()
    legs()
    arms()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * 0.27, KNEE, 0))
        out[f"shin.{side}"] = ((s * 0.27, KNEE, 0), (s * FOOT_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * FOOT_X, ANKLE, 0), (s * FOOT_X, 0.07, 0.5))
    return out


H.build("h05H", "biped", PALETTE, make, joints())
