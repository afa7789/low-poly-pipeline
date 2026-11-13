"""Satyr (n00A): medido em artifacts/model-sheets/refs/n00A/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n00A.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "fur": 0x2B2729, "fur_dk": 0x1D1A1B, "mask": 0x3C3A3F, "glass": 0x8A929A, "horn": 0x8F7F6A, "hoof": 0x7C6B58,
    "belt": 0x6A5C50, "buckle": 0x8A8C90, "case": 0x6E6155, "case_dk": 0x4E443B, "red": 0xA81830, "steel": 0xA6A8AC,
    "shaft": 0x5A4636,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X = 0.98, 0.52, 0.14, 0.26, 0.33
WAIST, NECK, TOP = 1.32, 1.98, 2.56
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.52, 1.95, 0.62, 1.55, 1.2


def head():
    z = 0.14        # cabeça projetada à frente do tronco curvado
    H.frustum("head", "fur", (0, 1.9, 0.05 + z), (0, 2.2, 0.08 + z), (0.26, 0.24), (0.3, 0.27), sides=8)                  # nuca
    H.frustum("head", "mask", (0, 1.88, 0.2 + z), (0, 2.1, 0.22 + z), (0.12, 0.14), (0.22, 0.2), sides=6)                  # focinho
    H.frustum("head", "mask", (0, 2.1, 0.2 + z), (0, 2.46, 0.14 + z), (0.24, 0.22), (0.27, 0.24), sides=6)                 # testa
    for s in (-1, 1):
        H.frustum("head", "glass", (s * 0.12, 2.27, 0.3 + z), (s * 0.12, 2.27, 0.38 + z), (0.1, 0.1), (0.1, 0.1), sides=8)  # óculos
        H.frustum("head", "horn", (s * 0.2, 2.4, 0.06 + z), (s * 0.3, 2.74, z), (0.09, 0.09), (0.015, 0.015), sides=6)
        H.frustum("head", "fur", (s * 0.26, 2.3, z), (s * 0.6, 2.34, z - 0.04), (0.06, 0.12), (0.02, 0.03), sides=4)  # orelhas


def torso():
    H.frustum("spine", "fur", (0, WAIST - 0.05, 0), (0, 1.72, 0.05), (0.34, 0.34), (0.5, 0.4), sides=8)
    H.frustum("spine", "fur", (0, 1.72, 0.05), (0, 2.05, 0.12), (0.5, 0.4), (0.3, 0.3), sides=8)               # ombros caídos
    H.frustum("spine", "fur_dk", (0, 1.85, -0.12), (0, 2.1, -0.06), (0.38, 0.28), (0.22, 0.2), sides=6)           # corcunda
    H.frustum("pelvis", "belt", (0, 1.22, 0), (0, 1.38, 0), (0.37, 0.34), (0.36, 0.33), sides=8)
    H.box("pelvis", "buckle", (0, 1.3, 0.33), (0.16, 0.12, 0.04))
    H.frustum("pelvis", "fur_dk", (0, 0.88, 0), (0, 1.24, 0), (0.4, 0.36), (0.37, 0.34), sides=8)
    H.frustum("pelvis", "steel", (0.36, 1.3, 0.16), (0.5, 1.0, 0.18), (0.05, 0.03), (0.08, 0.03), sides=4)        # chave de boca no cinto
    H.frustum("pelvis", "steel", (0.5, 1.0, 0.18), (0.56, 0.92, 0.18), (0.1, 0.03), (0.06, 0.03), sides=6)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        # coxa larga no quadril, joelho para a frente, canela para trás, casco aberto
        H.frustum(f"thigh.{side}", "fur", (s * KNEE_X, KNEE, 0.1), (s * LEG_X, HIP + 0.05, 0), (0.19, 0.2), (0.27, 0.28), sides=6)
        H.frustum(f"thigh.{side}", "fur_dk", (s * KNEE_X, KNEE - 0.04, 0.1), (s * KNEE_X, KNEE + 0.12, 0.1), (0.2, 0.2), (0.19, 0.19), sides=6)
        H.frustum(f"shin.{side}", "fur", (s * KNEE_X, ANKLE + 0.04, -0.1), (s * KNEE_X, KNEE, 0.1), (0.13, 0.13), (0.19, 0.2), sides=6)
        H.frustum(f"shin.{side}", "fur_dk", (s * KNEE_X, 0.3, -0.06), (s * KNEE_X, 0.5, 0.0), (0.12, 0.13), (0.17, 0.17), sides=6)
        H.frustum(f"foot.{side}", "hoof", (s * KNEE_X, 0.04, -0.12), (s * KNEE_X, ANKLE + 0.02, -0.1), (0.17, 0.18), (0.13, 0.14), sides=6)
        H.frustum(f"foot.{side}", "hoof", (s * KNEE_X, 0.08, 0.0), (s * KNEE_X, 0.05, 0.42), (0.17, 0.12), (0.17, 0.06), sides=4)
        H.box(f"foot.{side}", "hoof", (s * KNEE_X, 0.06, 0.38), (0.04, 0.06, 0.16))


def left_arm_spear():
    H.frustum("arm.L", "fur", (SH_X, SH_Y + 0.05, 0), (EL_X + 0.1, EL_Y, 0.02), (0.24, 0.26), (0.19, 0.21), sides=6)
    H.frustum("forearm.L", "fur", (EL_X + 0.1, EL_Y + 0.04, 0.02), (0.8, 1.32, 0.08), (0.17, 0.19), (0.15, 0.16), sides=6)
    H.frustum("forearm.L", "fur_dk", (0.8, 1.34, 0.08), (0.86, 1.14, 0.1), (0.15, 0.16), (0.2, 0.2), sides=6)      # punho grande
    x, z = 0.88, 0.1
    H.frustum("forearm.L", "shaft", (x, 0.5, z), (x, 2.0, z), (0.05, 0.05), (0.05, 0.05), sides=6)
    H.frustum("forearm.L", "steel", (x, 2.0, z), (x, 2.5, z), (0.13, 0.04), (0.005, 0.01), sides=4)                # ponta
    H.frustum("forearm.L", "steel", (x, 1.96, z), (x, 2.12, z), (0.01, 0.03), (0.17, 0.04), sides=4)               # farpas


def right_arm_case():
    H.frustum("arm.R", "fur", (-SH_X, SH_Y + 0.05, 0), (-EL_X - 0.1, EL_Y - 0.1, 0.02), (0.24, 0.26), (0.19, 0.21), sides=6)
    H.frustum("forearm.R", "fur", (-EL_X - 0.1, EL_Y - 0.06, 0.02), (-0.66, 1.2, 0.04), (0.17, 0.19), (0.15, 0.16), sides=6)
    H.frustum("forearm.R", "fur_dk", (-0.66, 1.22, 0.04), (-0.62, 1.02, 0.04), (0.15, 0.16), (0.2, 0.2), sides=6)
    H.box("forearm.R", "case_dk", (-0.62, 1.1, 0.04), (0.2, 0.06, 0.06))
    H.box("forearm.R", "case", (-0.58, 0.78, 0.04), (0.56, 0.46, 0.2))
    H.box("forearm.R", "red", (-0.5, 0.74, 0.15), (0.1, 0.1, 0.03))


def make():
    head()
    torso()
    legs()
    left_arm_spear()
    right_arm_case()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * KNEE_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * KNEE_X, ANKLE, 0), (s * KNEE_X, 0.06, 0.5))
    return out


H.build("n00A", "biped", PALETTE, make, joints())
