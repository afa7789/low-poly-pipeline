"""Suffocated Zombie (n01K): zumbi curvado com saco na cabeça, poncho azul, bolsa de ar presa ao peito com mangueira
em laço, forcado na mão esquerda. Medido em artifacts/model-sheets/refs/n01K/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n01K.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "sack": 0xB9C4B8, "sack_dk": 0x9AA79C, "poncho": 0x3156B4, "band": 0x1F2F7A, "skin": 0xDCE6F4, "pants": 0x23338A,
    "glove": 0x3A5FC4, "boot": 0x1A2260, "jug": 0x6ED8EA, "hose": 0x7A7F86, "wood": 0x7A4528, "wood_dk": 0x5C3320,
}
HIP, KNEE, ANKLE, WAIST, NECK, TOP = 1.0, 0.55, 0.2, 1.31, 1.95, 2.6
HIP_X, KNEE_X, FOOT_X = 0.24, 0.3, 0.36
SH_X, SH_Y, SH_Z = 0.44, 1.85, 0.4
R_EL, R_WR = (-0.6, 1.3, 0.4), (-0.64, 0.92, 0.46)
L_EL, L_WR = (0.58, 1.45, 0.42), (0.62, 1.1, 0.6)
FORK_X, FORK_Z = 0.76, 0.6
SPZ, HZ = 0.25, 0.7     # coluna e cabeça avançam: corcunda


def fz(y):
    """Avanço em z na altura y: 0 no quadril, cresce até o capuz (corcunda)."""
    t = max(0.0, (y - 1.0) / 1.6)
    return 0.5 * t * t + 0.12 * t


def head():
    z = HZ
    H.frustum("head", "band", (0, 2.0, z - 0.1), (0, 2.1, z - 0.06), (0.3, 0.28), (0.25, 0.24), sides=8)
    H.frustum("head", "sack_dk", (0, 2.08, z - 0.06), (0, 2.3, z), (0.26, 0.26), (0.42, 0.4), sides=8)
    H.frustum("head", "sack", (0, 2.3, z), (0, 2.5, z + 0.04), (0.42, 0.4), (0.4, 0.38), sides=8)
    H.frustum("head", "sack", (0, 2.5, z + 0.04), (0, TOP, z + 0.02), (0.4, 0.38), (0.2, 0.2), sides=8)


def torso():
    H.frustum("pelvis", "pants", (0, 0.92, -0.04), (0, WAIST + 0.02, 0.0), (0.4, 0.27), (0.35, 0.25), sides=8)
    H.frustum("spine", "skin", (0, WAIST - 0.03, fz(1.3)), (0, 1.62, fz(1.62)), (0.33, 0.24), (0.44, 0.28), sides=8)
    H.frustum("spine", "skin", (0, 1.62, fz(1.62)), (0, 1.82, fz(1.82)), (0.44, 0.28), (0.46, 0.3), sides=8)
    H.frustum("spine", "poncho", (0, 1.7, fz(1.7)), (0, 1.88, fz(1.88)), (0.52, 0.4), (0.5, 0.38), sides=8)
    H.frustum("spine", "poncho", (0, 1.88, fz(1.88)), (0, 2.02, fz(2.02) + 0.04), (0.5, 0.38), (0.3, 0.26), sides=8)


def bag():
    z = fz(1.5) + 0.3
    H.frustum("spine", "jug", (0, 1.28, z), (0, 1.54, z + 0.04), (0.17, 0.14), (0.21, 0.16), sides=6)
    H.frustum("spine", "jug", (0, 1.54, z + 0.04), (0, 1.7, z + 0.04), (0.21, 0.16), (0.09, 0.08), sides=6)
    H.frustum("spine", "hose", (0, 1.7, z + 0.04), (0, 1.77, z + 0.04), (0.05, 0.05), (0.05, 0.05), sides=6)
    H.chain("spine", "hose", [(0, 1.76, z + 0.04), (0, 1.92, z - 0.04)], [(0.035, 0.035)] * 2, sides=6)
    for s in (-1, 1):       # alças da bolsa
        H.frustum("spine", "band", (s * 0.22, 1.82, fz(1.82) + 0.1), (s * 0.12, 1.52, z + 0.02), (0.035, 0.02), (0.035, 0.02), sides=4)
    H.chain("spine", "hose", [(-0.15, 1.45, z + 0.06), (-0.55, 1.35, z - 0.04), (-0.64, 1.7, z - 0.3), (-0.56, 2.1, z - 0.5), (-0.3, 2.3, z - 0.64), (0.0, 2.2, z - 0.7)],
            [(0.05, 0.05)] * 6, sides=6)


def tatters(kx, side):
    """Barra rasgada da bermuda: cunhas de tamanhos diferentes."""
    for i, (dx, dz, ln) in enumerate(((-0.14, 0.0, 0.2), (-0.07, 0.14, 0.1), (0.0, -0.14, 0.24), (0.08, 0.13, 0.14), (0.14, -0.02, 0.18))):
        y0 = KNEE - 0.18
        H.frustum(f"shin.{side}", "pants", (kx + dx, y0 + 0.02, 0.1 + dz), (kx + dx, y0 - ln, 0.1 + dz), (0.06, 0.04), (0.0, 0.0), sides=4)


def leg(s, side):
    kx, fx = s * KNEE_X, s * FOOT_X
    H.frustum(f"thigh.{side}", "pants", (kx, KNEE + 0.05, 0.1), (s * (HIP_X + 0.01), HIP + 0.08, 0), (0.21, 0.22), (0.29, 0.28), sides=6)
    H.frustum(f"shin.{side}", "pants", (kx, KNEE - 0.18, 0.08), (kx, KNEE + 0.1, 0.1), (0.17, 0.17), (0.22, 0.22), sides=6)
    tatters(kx, side)
    H.frustum(f"shin.{side}", "skin", (fx, ANKLE, 0), (kx, KNEE - 0.08, 0.1), (0.1, 0.1), (0.13, 0.13), sides=6)
    H.frustum(f"foot.{side}", "boot", (fx, 0.02, -0.04), (fx, 0.36, -0.02), (0.15, 0.2), (0.18, 0.2), sides=6)
    H.frustum(f"foot.{side}", "boot", (fx, 0.1, 0.1), (fx, 0.08, 0.5), (0.17, 0.12), (0.15, 0.07), sides=4)


def right_arm():
    H.frustum("arm.R", "skin", (-SH_X, SH_Y + 0.05, SH_Z), (-0.54, 1.6, 0.4), (0.17, 0.17), (0.15, 0.15), sides=6)
    H.frustum("arm.R", "skin", (-0.54, 1.6, 0.4), (R_EL[0], R_EL[1] - 0.02, R_EL[2]), (0.15, 0.15), (0.12, 0.12), sides=6)
    H.frustum("forearm.R", "glove", (R_EL[0], R_EL[1] + 0.02, R_EL[2]), (-0.62, 1.0, 0.44), (0.13, 0.13), (0.12, 0.12), sides=6)
    H.frustum("forearm.R", "glove", (-0.62, 1.0, 0.44), (R_WR[0], 0.66, 0.48), (0.12, 0.12), (0.17, 0.14), sides=6)


def fork():
    H.frustum("forearm.L", "wood", (FORK_X, 0.0, FORK_Z), (FORK_X, 1.25, FORK_Z), (0.045, 0.045), (0.05, 0.05), sides=6)
    H.frustum("forearm.L", "wood", (FORK_X, 1.25, FORK_Z), (FORK_X, 2.1, FORK_Z), (0.05, 0.05), (0.045, 0.045), sides=6)
    H.frustum("forearm.L", "wood_dk", (FORK_X, 2.06, FORK_Z), (FORK_X, 2.16, FORK_Z), (0.28, 0.05), (0.28, 0.05), sides=4)      # travessa
    for dx in (-0.25, 0.0, 0.25):
        H.frustum("forearm.L", "wood_dk", (FORK_X + dx, 2.14, FORK_Z), (FORK_X + dx, 2.4, FORK_Z), (0.045, 0.045), (0.03, 0.03), sides=4)


def left_arm():
    H.frustum("arm.L", "skin", (SH_X, SH_Y + 0.05, SH_Z), (0.52, 1.62, 0.4), (0.17, 0.17), (0.15, 0.15), sides=6)
    H.frustum("arm.L", "skin", (0.52, 1.62, 0.4), (L_EL[0], L_EL[1] - 0.02, L_EL[2]), (0.15, 0.15), (0.12, 0.12), sides=6)
    H.frustum("forearm.L", "glove", (L_EL[0], L_EL[1] + 0.02, L_EL[2]), (0.6, 1.25, 0.5), (0.13, 0.13), (0.12, 0.12), sides=6)
    H.frustum("forearm.L", "glove", (0.6, 1.25, 0.5), (FORK_X, 1.0, FORK_Z), (0.12, 0.12), (0.18, 0.16), sides=6)       # punho
    fork()


def make():
    head()
    torso()
    bag()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    right_arm()
    left_arm()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, SPZ), (0, NECK, SPZ)), "head": ((0, NECK, HZ), (0, TOP, HZ)),
           "arm.R": ((-SH_X, SH_Y, SH_Z), R_EL), "forearm.R": (R_EL, R_WR), "arm.L": ((SH_X, SH_Y, SH_Z), L_EL), "forearm.L": (L_EL, L_WR)}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * HIP_X, HIP, 0), (s * KNEE_X, KNEE, 0.1))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0.1), (s * FOOT_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * FOOT_X, ANKLE, 0), (s * FOOT_X, 0.06, 0.5))
    return out


H.build("n01K", "biped", PALETTE, make, joints())
