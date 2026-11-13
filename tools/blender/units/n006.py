"""Blademaster (n006): medido em artifacts/model-sheets/refs/n006/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n006.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "teal": 0x1D4A52, "teal_dk": 0x153840, "apron": 0x1B2C2E, "gold": 0xA8802F, "gold_dk": 0x836224,
    "vest": 0xDDEBA5, "blue": 0x3AB0F0, "skin": 0x93774F, "steel": 0xC9CBC8, "boot": 0x182628,
    "book": 0x24342F, "pages": 0xCDBB8A, "face": 0x0F1D20,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X = 1.1, 0.55, 0.15, 0.2, 0.24
WAIST, NECK, TOP = 1.55, 2.15, 2.72
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.5, 2.05, 0.56, 1.4, 1.0


def head():
    H.frustum("head", "face", (0, 2.2, 0), (0, 2.5, 0), (0.2, 0.2), (0.2, 0.2), sides=6)
    H.frustum("head", "gold", (0, 2.1, 0), (0, 2.4, 0), (0.33, 0.3), (0.31, 0.3), sides=8)             # gola alta
    H.frustum("head", "gold", (0, 2.3, 0.03), (0, 2.5, 0.03), (0.26, 0.25), (0.3, 0.28), sides=8)      # elmo: bojo
    H.frustum("head", "gold", (0, 2.5, 0.03), (0, 2.66, 0.03), (0.3, 0.28), (0.2, 0.19), sides=8)
    H.frustum("head", "gold", (0, 2.66, 0.03), (0, 2.74, 0.03), (0.2, 0.19), (0.06, 0.06), sides=8)
    H.frustum("head", "gold_dk", (0, 2.3, -0.2), (0, 2.66, -0.2), (0.27, 0.06), (0.2, 0.06), sides=6)   # nuca
    H.frustum("head", "blue", (0.1, 2.42, 0.27), (0.1, 2.42, 0.36), (0.11, 0.11), (0.09, 0.09), sides=8)   # olho de vidro


def torso():
    H.frustum("spine", "teal", (0, WAIST - 0.05, 0), (0, 2.05, 0), (0.37, 0.27), (0.46, 0.3), sides=8)
    H.frustum("spine", "teal", (0, 2.05, 0), (0, 2.2, 0), (0.46, 0.3), (0.28, 0.22), sides=8)
    H.frustum("spine", "vest", (0, 1.72, 0.05), (0, 2.15, 0.06), (0.34, 0.3), (0.4, 0.31), sides=6)  # colete claro
    H.frustum("spine", "vest", (0, 1.72, -0.05), (0, 2.15, -0.06), (0.34, 0.3), (0.42, 0.31), sides=6)
    H.box("spine", "gold", (0, 1.95, 0.3), (0.28, 0.17, 0.05))
    H.frustum("pelvis", "apron", (0, 1.52, 0), (0, 1.62, 0), (0.4, 0.3), (0.4, 0.3), sides=8)         # cinto
    H.frustum("pelvis", "gold", (0, 0.78, 0), (0, 1.22, 0), (0.48, 0.38), (0.34, 0.27), sides=8)          # saia pregueada
    H.frustum("pelvis", "teal", (0, 0.95, 0), (0, 1.55, 0), (0.4, 0.3), (0.35, 0.27), sides=8)
    H.frustum("pelvis", "apron", (0, 0.88, 0.2), (0, 1.5, 0.2), (0.2, 0.06), (0.17, 0.06), sides=4)    # avental


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        H.frustum(f"thigh.{side}", "teal_dk", (s * KNEE_X, KNEE - 0.04, 0), (s * LEG_X, HIP + 0.05, 0), (0.17, 0.18), (0.22, 0.23), sides=6)
        H.frustum(f"thigh.{side}", "gold", (s * KNEE_X, KNEE - 0.08, 0.04), (s * KNEE_X, KNEE + 0.14, 0.04), (0.2, 0.2), (0.17, 0.17), sides=6)
        H.frustum(f"shin.{side}", "boot", (s * KNEE_X, ANKLE - 0.02, 0), (s * KNEE_X, KNEE + 0.02, 0), (0.13, 0.14), (0.17, 0.17), sides=6)
        H.frustum(f"shin.{side}", "gold", (s * KNEE_X, 0.2, 0.05), (s * KNEE_X, KNEE + 0.05, 0.05), (0.14, 0.15), (0.19, 0.17), sides=6)
        H.frustum(f"foot.{side}", "boot", (s * KNEE_X, 0.03, -0.03), (s * KNEE_X, ANKLE + 0.04, -0.03), (0.17, 0.18), (0.14, 0.15), sides=6)
        H.frustum(f"foot.{side}", "boot", (s * KNEE_X, 0.1, 0.05), (s * KNEE_X, 0.07, 0.42), (0.17, 0.11), (0.15, 0.06), sides=4)
        H.frustum(f"foot.{side}", "gold", (s * KNEE_X, 0.13, 0.2), (s * KNEE_X, 0.1, 0.38), (0.13, 0.05), (0.12, 0.05), sides=4)


def left_arm_and_book():
    H.frustum("arm.L", "teal", (SH_X + 0.03, SH_Y + 0.05, 0), (EL_X, EL_Y - 0.03, 0), (0.2, 0.23), (0.17, 0.19), sides=6)
    H.frustum("arm.L", "blue", (SH_X + 0.04, 1.85, 0), (SH_X + 0.05, 1.68, 0), (0.18, 0.21), (0.18, 0.21), sides=6)   # braçadeira
    H.frustum("forearm.L", "teal", (EL_X, EL_Y + 0.04, 0), (EL_X, WR_Y, 0.04), (0.17, 0.19), (0.15, 0.16), sides=6)
    H.frustum("forearm.L", "skin", (EL_X, WR_Y + 0.03, 0.04), (EL_X, WR_Y - 0.22, 0.08), (0.13, 0.16), (0.11, 0.15), sides=6)
    H.box("forearm.L", "book", (EL_X - 0.04, 1.0, 0.2), (0.14, 0.4, 0.5))
    H.box("forearm.L", "pages", (EL_X + 0.04, 1.0, 0.2), (0.04, 0.36, 0.46))


def right_arm_and_sword():
    H.frustum("arm.R", "teal", (-SH_X - 0.03, SH_Y + 0.05, 0), (-EL_X, EL_Y - 0.03, 0), (0.2, 0.23), (0.17, 0.19), sides=6)
    H.frustum("forearm.R", "teal", (-EL_X, EL_Y + 0.04, 0), (-EL_X, 1.45, 0.3), (0.17, 0.19), (0.15, 0.16), sides=6)
    H.frustum("forearm.R", "skin", (-EL_X, 1.46, 0.28), (-EL_X, 1.58, 0.52), (0.14, 0.15), (0.17, 0.17), sides=6)   # punho grande
    x = -EL_X
    H.frustum("forearm.R", "gold", (x, 1.4, 0.5), (x, 1.68, 0.52), (0.06, 0.06), (0.06, 0.06), sides=6)              # cabo
    H.frustum("forearm.R", "gold", (x, 1.36, 0.5), (x, 1.44, 0.5), (0.08, 0.08), (0.12, 0.12), sides=6)              # pomo
    H.box("forearm.R", "gold", (x, 1.7, 0.52), (0.34, 0.07, 0.1))
    H.frustum("forearm.R", "steel", (x, 1.72, 0.52), (x, 2.55, 0.55), (0.09, 0.045), (0.08, 0.04), sides=4)          # lâmina
    H.frustum("forearm.R", "steel", (x, 2.55, 0.55), (x, 2.85, 0.56), (0.08, 0.04), (0.005, 0.005), sides=4)


def make():
    head()
    torso()
    legs()
    left_arm_and_book()
    right_arm_and_sword()


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


H.build("n006", "biped", PALETTE, make, joints())
