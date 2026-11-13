"""Elder Blademaster (n00Y): medido em artifacts/model-sheets/refs/n00Y/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n00Y.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "teal": 0x244C54, "teal_dk": 0x1D3A42, "dark": 0x1E2626, "brass": 0x8C6A3A, "mask": 0x8B2A3A,
    "glove": 0xCDDC9E, "black": 0x14191A, "blade": 0xC6D8C0, "blue": 0x38A6F0, "belt": 0x181F20,
}

HIP, KNEE, ANKLE, LEG_X = 0.95, 0.62, 0.14, 0.17
WAIST, NECK, TOP = 1.5, 2.05, 2.7
SH_X, SH_Y, EL_X, EL_Y, WR_X, WR_Y = 0.42, 2.0, 0.46, 1.62, 0.46, 1.3
SKIRT_MID = 1.05
WZ = {"L": 0.02, "R": 0.2}      # a mão do sabre vai à frente do corpo (perfil: o punho passa do peito)


def hem(p):
    """A barra do casaco acompanha a coxa do seu lado; o topo fica na pelve."""
    if p[1] > SKIRT_MID:
        return {"pelvis": 1.0}
    return {"pelvis": 0.45, "thigh.L" if p[0] > 0 else "thigh.R": 0.55}


def head():
    H.frustum("head", "teal", (0, 1.98, 0), (0, 2.3, 0), (0.24, 0.22), (0.28, 0.24), sides=8)               # gola alta
    H.frustum("head", "mask", (0, 2.3, 0.06), (0, 2.17, 0.4), (0.15, 0.15), (0.12, 0.1), sides=6)           # máscara
    H.box("head", "blue", (0.09, 2.34, 0.2), (0.08, 0.08, 0.06))                                            # olho
    H.frustum("head", "brass", (0, 2.44, 0), (0, 2.5, 0), (0.28, 0.28), (0.24, 0.24), sides=8)              # aba do elmo
    H.frustum("head", "brass", (0, 2.5, 0), (0, 2.6, 0), (0.2, 0.2), (0.17, 0.17), sides=8)
    H.frustum("head", "brass", (0, 2.6, 0), (0, 2.68, 0), (0.17, 0.17), (0.08, 0.08), sides=8)
    H.frustum("head", "brass", (0, 2.62, 0), (0, 2.82, 0), (0.05, 0.05), (0.01, 0.01), sides=4)
    for s in (-1, 1):
        H.frustum("head", "brass", (s * 0.11, 2.6, 0), (s * 0.16, 2.76, 0), (0.04, 0.04), (0.01, 0.01), sides=4)


def torso():
    H.frustum("spine", "teal", (0, WAIST - 0.05, 0), (0, 2.0, 0), (0.26, 0.23), (0.32, 0.25), sides=8)
    H.frustum("spine", "teal", (0, 2.0, 0), (0, 2.15, 0), (0.32, 0.25), (0.22, 0.2), sides=8)
    for z in (0.23, -0.23):         # peitoral e canga de latão
        H.frustum("spine", "brass", (0, 1.78, z), (0, 2.15, z), (0.2, 0.05), (0.3, 0.05), sides=4)
    for s in (-1, 1):
        H.wheel("spine", "dark", (s * 0.37, 2.06, -0.02), 0.32, 0.2, sides=8)                              # ombreira
        H.wheel("spine", "brass", (s * 0.49, 2.0, -0.02), 0.33, 0.05, sides=8)
    H.frustum("pelvis", "belt", (0, 1.44, 0), (0, 1.56, 0), (0.3, 0.26), (0.3, 0.26), sides=8)
    H.frustum("pelvis", "teal_dk", (0, 0.8, 0), (0, 1.2, 0), (0.24, 0.2), (0.28, 0.22), sides=8)
    skirt = H.frustum("pelvis", "teal", (0, 0.58, 0), (0, 1.46, 0), (0.4, 0.3), (0.3, 0.24), sides=8)
    H.soft(skirt, hem)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * LEG_X
        H.frustum(f"thigh.{side}", "teal_dk", (x, KNEE - 0.03, 0), (x, HIP + 0.08, 0), (0.15, 0.16), (0.2, 0.2), sides=6)
        H.frustum(f"thigh.{side}", "brass", (x, KNEE + 0.04, 0.17), (x, KNEE + 0.04, 0.24), (0.11, 0.12), (0.1, 0.11), sides=8)   # joelheira
        H.frustum(f"shin.{side}", "teal_dk", (x, 0.44, 0), (x, KNEE + 0.02, 0), (0.14, 0.14), (0.16, 0.16), sides=6)
        H.frustum(f"shin.{side}", "black", (x, ANKLE - 0.04, 0), (x, 0.52, 0), (0.1, 0.11), (0.16, 0.16), sides=6)                # bota alta
        H.frustum(f"foot.{side}", "black", (x, 0.03, -0.04), (x, ANKLE + 0.04, -0.04), (0.14, 0.15), (0.12, 0.13), sides=6)
        H.frustum(f"foot.{side}", "black", (x, 0.1, 0.0), (x, 0.06, 0.44), (0.14, 0.11), (0.12, 0.05), sides=4)


def arms():
    for s, side in ((1, "L"), (-1, "R")):
        z = WZ[side]
        H.frustum(f"arm.{side}", "teal", (s * SH_X, SH_Y + 0.06, 0), (s * EL_X, EL_Y + 0.02, z / 2), (0.17, 0.18), (0.15, 0.16), sides=6)
        H.frustum(f"forearm.{side}", "glove", (s * EL_X, EL_Y + 0.02, z / 2), (s * WR_X, WR_Y + 0.02, z), (0.14, 0.15), (0.17, 0.18), sides=6)
        H.frustum(f"forearm.{side}", "black", (s * WR_X, WR_Y + 0.04, z), (s * WR_X, WR_Y - 0.26, z + 0.04), (0.14, 0.16), (0.17, 0.18), sides=6)   # punho


def sword():
    x, z = -WR_X - 0.02, 0.34
    H.box("forearm.R", "black", (x, 1.02, z), (0.3, 0.26, 0.26))                                              # motor no punho
    H.frustum("forearm.R", "brass", (x, 1.1, z), (x, 1.16, z), (0.12, 0.12), (0.12, 0.12), sides=6)
    H.chain("forearm.R", "brass", [(x, 1.16, z), (x - 0.08, 1.3, z - 0.02), (x - 0.02, 1.42, z)], [(0.04, 0.04)] * 3, sides=4)
    H.frustum("forearm.R", "blade", (x, 0.93, z), (x, 0.1, z), (0.05, 0.09), (0.04, 0.08), sides=4)       # lâmina, ponta para baixo
    H.frustum("forearm.R", "blade", (x, 0.1, z), (x, 0.0, z), (0.03, 0.07), (0.005, 0.005), sides=4)


def make():
    head()
    torso()
    legs()
    arms()
    sword()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, WZ[side] / 2))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, WZ[side] / 2), (s * WR_X, WR_Y, WZ[side]))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("n00Y", "biped", PALETTE, make, joints())
