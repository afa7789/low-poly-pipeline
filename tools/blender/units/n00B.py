"""Zombie (n00B): medido em artifacts/model-sheets/refs/n00B/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n00B.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "skin": 0xCDBFAC, "skin_dk": 0xA89886, "tunic": 0xA2825E, "strap": 0x6B4A30, "glove": 0x6B4F3C, "boot": 0x6A4A32,
    "can": 0x8E9194, "can_dk": 0x4A4A4C, "hose": 0x8B8A5E, "green": 0x6FE06A, "wood": 0x6A4630, "iron": 0x8D8F94,
    "bandage": 0xD2BE8E, "socket": 0x3A3030, "rope": 0xB09A6E,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X = 1.1, 0.6, 0.17, 0.2, 0.24
WAIST, NECK, TOP = 1.5, 2.15, 2.72
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.4, 2.0, 0.46, 1.45, 1.05
HZ = 0.62       # a cabeça pende à frente do tronco curvado
SPZ = 0.3       # a coluna inteira avança: ombros à frente do quadril
ARMZ = 0.3      # os braços pendem à frente do peito curvado


LZ = 0.28       # pés à frente do quadril: as pernas inclinam-se sob o tronco curvado


def fz(y):
    """Avanço em z na altura y: 0 abaixo da cintura, cresce até a cabeça (corcunda)."""
    t = max(0.0, (y - 1.2) / 1.5)
    return 0.55 * t * t + 0.1 * t


def head():
    z = HZ
    H.frustum("head", "skin", (0, 2.2, z - 0.04), (0, 2.45, z), (0.17, 0.2), (0.22, 0.23), sides=8)
    H.frustum("head", "skin", (0, 2.45, z), (0, 2.72, z - 0.06), (0.22, 0.23), (0.12, 0.14), sides=8)               # crânio
    H.frustum("head", "skin_dk", (0, 2.08, z - 0.06), (0, 2.26, z), (0.09, 0.1), (0.12, 0.12), sides=6)             # queixo magro
    H.frustum("head", "bandage", (0, 2.24, z), (0, 2.34, z), (0.2, 0.21), (0.21, 0.22), sides=8)                    # venda na boca
    for s in (-1, 1):
        H.frustum("head", "socket", (s * 0.09, 2.44, z + 0.19), (s * 0.09, 2.44, z + 0.235), (0.045, 0.045), (0.07, 0.07), sides=6)  # olhos: buracos


def torso():
    H.frustum("spine", "skin", (0, 1.85, fz(1.85)), (0, 2.2, fz(2.2) - 0.05), (0.38, 0.3), (0.24, 0.26), sides=8)    # ombros magros
    H.frustum("spine", "tunic", (0, WAIST - 0.05, fz(1.45)), (0, 2.08, fz(2.08)), (0.27, 0.32), (0.31, 0.34), sides=8)
    H.frustum("pelvis", "tunic", (0, 1.1, 0.0), (0, WAIST, 0.0), (0.28, 0.24), (0.27, 0.26), sides=8)         # barra rasgada
    H.frustum("pelvis", "skin", (0, 0.98, 0.02), (0, 1.2, 0.04), (0.22, 0.14), (0.24, 0.15), sides=6)
    for sx in (1, -1):
        H.frustum("spine", "strap", (sx * 0.24, 2.2, fz(2.2) + 0.1), (-sx * 0.24, 1.5, fz(1.5) + 0.2), (0.06, 0.03), (0.06, 0.03), sides=4)  # correia
    H.frustum("spine", "strap", (0.24, 2.2, fz(2.2) - 0.18), (-0.24, 1.5, fz(1.5) - 0.2), (0.06, 0.03), (0.06, 0.03), sides=4)
    H.frustum("spine", "strap", (-0.24, 2.2, fz(2.2) - 0.18), (0.24, 1.5, fz(1.5) - 0.2), (0.06, 0.03), (0.06, 0.03), sides=4)
    cz = fz(1.75) + 0.2
    H.frustum("spine", "can_dk", (0.06, 1.62, cz), (0.06, 1.9, cz + 0.03), (0.13, 0.13), (0.14, 0.14), sides=8)     # lata respirador
    H.frustum("spine", "can", (0.06, 1.66, cz + 0.02), (0.06, 1.9, cz + 0.05), (0.13, 0.13), (0.14, 0.14), sides=8)
    for a, b in (((0.08, 1.6, cz + 0.02), (0.16, 1.4, cz + 0.04)), ((0.16, 1.4, cz + 0.04), (0.3, 1.36, cz)), ((0.3, 1.36, cz), (0.34, 1.44, cz - 0.1))):
        H.frustum("spine", "hose", a, b, (0.045, 0.045), (0.045, 0.045), sides=6)
    H.frustum("spine", "green", (0.33, 1.18, cz - 0.1), (0.33, 1.62, cz - 0.1), (0.09, 0.11), (0.09, 0.11), sides=6)  # frasco verde


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        H.frustum(f"thigh.{side}", "skin", (s * KNEE_X, KNEE - 0.04, LZ), (s * LEG_X, HIP + 0.05, 0.08), (0.1, 0.11), (0.15, 0.15), sides=6)
        H.frustum(f"thigh.{side}", "skin_dk", (s * KNEE_X, KNEE - 0.06, LZ), (s * KNEE_X, KNEE + 0.06, LZ), (0.12, 0.12), (0.1, 0.1), sides=6)
        H.frustum(f"shin.{side}", "skin", (s * KNEE_X, ANKLE - 0.02, LZ), (s * KNEE_X, KNEE + 0.02, LZ), (0.08, 0.08), (0.11, 0.12), sides=6)
    # perna direita: bota; esquerda: pé descalço com corda no tornozelo
    H.frustum("shin.R", "boot", (-KNEE_X, 0.14, LZ), (-KNEE_X, 0.42, LZ), (0.12, 0.13), (0.16, 0.16), sides=6)
    H.frustum("foot.R", "boot", (-KNEE_X, 0.03, LZ + -0.04), (-KNEE_X, 0.3, LZ + -0.04), (0.16, 0.18), (0.14, 0.15), sides=6)
    H.frustum("foot.R", "boot", (-KNEE_X, 0.1, LZ + 0.08), (-KNEE_X, 0.07, LZ + 0.42), (0.16, 0.12), (0.14, 0.06), sides=4)
    H.frustum("foot.L", "skin_dk", (KNEE_X, 0.05, LZ + -0.02), (KNEE_X, ANKLE + 0.02, LZ + -0.02), (0.09, 0.11), (0.08, 0.09), sides=6)
    H.frustum("foot.L", "skin", (KNEE_X, 0.08, LZ + 0.06), (KNEE_X, 0.05, LZ + 0.42), (0.1, 0.09), (0.09, 0.05), sides=4)
    H.frustum("shin.L", "rope", (KNEE_X, 0.14, LZ), (KNEE_X, 0.24, LZ), (0.12, 0.12), (0.13, 0.13), sides=6)


def left_arm():
    z = ARMZ
    H.frustum("arm.L", "skin", (SH_X + 0.02, SH_Y + 0.05, z), (EL_X, EL_Y - 0.02, z), (0.14, 0.15), (0.1, 0.11), sides=6)
    H.frustum("forearm.L", "skin", (EL_X, EL_Y + 0.04, z), (EL_X, WR_Y + 0.1, z + 0.04), (0.1, 0.11), (0.08, 0.09), sides=6)
    H.frustum("forearm.L", "glove", (EL_X, WR_Y + 0.12, z + 0.04), (EL_X, WR_Y - 0.1, z + 0.06), (0.13, 0.17), (0.15, 0.17), sides=6)  # luva enorme
    H.frustum("forearm.L", "glove", (EL_X, WR_Y - 0.08, z + 0.06), (EL_X, WR_Y - 0.36, z + 0.08), (0.16, 0.17), (0.09, 0.11), sides=6)
    H.frustum("forearm.L", "glove", (EL_X - 0.1, WR_Y - 0.02, z + 0.12), (EL_X - 0.14, WR_Y - 0.22, z + 0.14), (0.05, 0.07), (0.04, 0.05), sides=4)  # polegar


def right_arm_and_hoe():
    z = ARMZ
    H.frustum("arm.R", "skin", (-SH_X - 0.02, SH_Y + 0.05, z), (-EL_X, EL_Y - 0.02, z), (0.14, 0.15), (0.1, 0.11), sides=6)
    H.frustum("forearm.R", "skin", (-EL_X, EL_Y + 0.04, z), (-EL_X, WR_Y + 0.05, z + 0.04), (0.1, 0.11), (0.08, 0.09), sides=6)
    H.frustum("forearm.R", "skin", (-EL_X, WR_Y + 0.06, z + 0.04), (-EL_X, WR_Y - 0.18, z + 0.1), (0.11, 0.12), (0.14, 0.14), sides=6)   # punho
    H.frustum("forearm.R", "wood", (-0.7, 1.25, z - 0.3), (-0.2, 0.62, z + 0.52), (0.055, 0.055), (0.06, 0.06), sides=6)                 # cabo da enxada
    H.frustum("forearm.R", "iron", (-0.2, 0.62, z + 0.52), (-0.08, 0.38, z + 0.62), (0.06, 0.06), (0.26, 0.05), sides=4)                   # lâmina
    H.frustum("forearm.R", "iron", (-0.24, 0.66, z + 0.5), (-0.3, 0.52, z + 0.52), (0.22, 0.07), (0.2, 0.07), sides=4)


def make():
    head()
    torso()
    legs()
    left_arm()
    right_arm_and_hoe()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, SPZ), (0, NECK, SPZ)),
           "head": ((0, NECK, HZ), (0, TOP, HZ))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, ARMZ), (s * EL_X, EL_Y, ARMZ))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, ARMZ), (s * EL_X, WR_Y, ARMZ))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, LZ), (s * LEG_X, KNEE, LZ))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, LZ), (s * KNEE_X, ANKLE, LZ))
        out[f"foot.{side}"] = ((s * KNEE_X, ANKLE, LZ), (s * KNEE_X, 0.06, LZ + 0.5))
    return out


H.build("n00B", "biped", PALETTE, make, joints())
