"""Corrupted Ent (n01I): tronco-bruto de pernas curtas, cabeça de toco oco com olho verde, braço esquerdo
preto e enorme com garras que arrastam no chão, braço direito curto e grosso. Medido em
artifacts/model-sheets/refs/n01I/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n01I.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "moss": 0x5D5A32, "moss_dk": 0x4B4A2A, "collar": 0x4A3D30, "collar_lt": 0x5E4E3C, "rim": 0xA89A6A,
    "inner": 0x241E16, "glow": 0x5CFF30, "black": 0x1A1410, "black_lt": 0x2C231B, "stone": 0x6C6B68,
    "bark": 0x5B4B38, "rust": 0x9A4A2C, "spike": 0x3B3022,
}
HIP, KNEE, ANKLE, WAIST, NECK, TOP = 0.6, 0.35, 0.1, 0.95, 1.75, 2.45
LEG_X = 0.32
SH_X, SH_Y = 0.62, 1.7
R_EL = (-0.8, 1.2, 0.0)
R_WR = (-0.76, 0.78, 0.05)
L_EL = (0.86, 1.15, 0.05)
L_WR = (0.9, 0.58, 0.15)


def head():
    H.frustum("head", "moss", (0, 1.78, 0.2), (0, 2.2, 0.3), (0.34, 0.33), (0.4, 0.36), sides=8)
    H.frustum("head", "moss", (0, 2.2, 0.3), (0, TOP, 0.3), (0.4, 0.36), (0.37, 0.34), sides=8)
    H.frustum("head", "rim", (0, TOP - 0.03, 0.3), (0, TOP + 0.03, 0.3), (0.37, 0.34), (0.37, 0.34), sides=8)
    H.frustum("head", "inner", (0, TOP + 0.02, 0.3), (0, TOP + 0.04, 0.3), (0.29, 0.27), (0.29, 0.27), sides=8)
    H.frustum("head", "glow", (0, 2.02, 0.55), (0, 2.02, 0.65), (0.13, 0.13), (0.11, 0.11), sides=8)
    H.frustum("head", "collar", (0, 1.7, 0.05), (0, 1.84, 0.1), (0.62, 0.55), (0.5, 0.46), sides=8)            # gola de casca
    H.frustum("head", "collar_lt", (0, 1.84, 0.1), (0, 1.96, 0.14), (0.46, 0.42), (0.38, 0.36), sides=8)
    H.chain("head", "spike", [(-0.22, 1.95, -0.22), (-0.32, 2.4, -0.2), (-0.42, 2.95, -0.1)],
            [(0.11, 0.1), (0.08, 0.07), (0.02, 0.02)], sides=4)       # galho quebrado nas costas


def torso():
    H.frustum("pelvis", "moss_dk", (0, 0.58, 0.05), (0, WAIST, 0.05), (0.4, 0.34), (0.5, 0.4), sides=8)
    H.frustum("spine", "moss", (0, WAIST - 0.05, 0.02), (0, 1.4, 0.03), (0.5, 0.4), (0.62, 0.42), sides=8)
    H.frustum("spine", "moss", (0, 1.4, 0.03), (0, 1.74, 0.05), (0.62, 0.42), (0.66, 0.38), sides=8)
    H.frustum("spine", "moss", (0, 1.74, 0.05), (0, 1.88, 0.08), (0.66, 0.38), (0.38, 0.3), sides=8)
    H.frustum("spine", "rust", (0.02, 1.28, 0.42), (0.02, 1.46, 0.42), (0.09, 0.03), (0.07, 0.03), sides=4)    # machadinha cravada


def leg(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "bark", (x, KNEE - 0.02, 0.02), (x, HIP + 0.1, 0.02), (0.2, 0.22), (0.27, 0.28), sides=6)
    H.frustum(f"shin.{side}", "bark", (x, ANKLE + 0.05, 0), (x, KNEE + 0.02, 0.02), (0.22, 0.22), (0.2, 0.2), sides=6)
    H.frustum(f"foot.{side}", "stone", (x, 0.02, -0.02), (x, ANKLE + 0.12, -0.02), (0.3, 0.28), (0.21, 0.2), sides=8)
    for dx, dz in ((-0.2, 0.34), (0.0, 0.46), (0.2, 0.34)):
        H.chain(f"foot.{side}", "stone", [(x, 0.1, 0.02), (x + dx * 0.6, 0.07, dz * 0.55), (x + dx, 0.03, dz)],
                [(0.11, 0.09), (0.08, 0.05), (0.03, 0.02)], sides=4)


def right_arm():
    H.frustum("arm.R", "moss", (-SH_X, SH_Y + 0.08, 0), (R_EL[0], R_EL[1], 0), (0.26, 0.28), (0.21, 0.23), sides=6)
    H.frustum("forearm.R", "moss", (R_EL[0], R_EL[1] + 0.06, 0), (-0.78, 0.9, 0.03), (0.22, 0.23), (0.2, 0.21), sides=6)
    H.frustum("forearm.R", "moss_dk", (-0.78, 0.92, 0.03), (R_WR[0], 0.6, 0.08), (0.2, 0.21), (0.17, 0.18), sides=6)      # punho
    H.frustum("forearm.R", "moss", (R_WR[0], 0.7, 0.07), (R_WR[0], 0.52, 0.1), (0.22, 0.2), (0.14, 0.14), sides=6)


def claw(x, tip_x, tip_z):
    H.chain("forearm.L", "black", [(x, 0.55, 0.12), (x + (tip_x - x) * 0.5, 0.28, 0.12 + tip_z * 0.4), (tip_x, 0.03, tip_z)],
            [(0.07, 0.06), (0.055, 0.045), (0.012, 0.012)], sides=4)


def left_arm():
    H.frustum("arm.L", "moss", (SH_X, SH_Y + 0.08, 0), (L_EL[0], L_EL[1] + 0.04, 0.03), (0.26, 0.28), (0.22, 0.24), sides=6)
    H.frustum("arm.L", "black_lt", (0.74, 1.5, 0.02), (L_EL[0], L_EL[1] - 0.04, 0.05), (0.2, 0.22), (0.22, 0.24), sides=6)
    H.frustum("forearm.L", "black", (L_EL[0], L_EL[1] + 0.05, 0.05), (0.88, 0.8, 0.1), (0.23, 0.25), (0.2, 0.22), sides=6)
    H.frustum("forearm.L", "black", (0.88, 0.82, 0.1), (L_WR[0], L_WR[1] - 0.04, 0.14), (0.2, 0.22), (0.18, 0.2), sides=6)
    for x, tx, tz in ((0.72, 0.62, 0.7), (0.84, 0.82, 0.78), (0.96, 1.02, 0.62), (1.04, 1.2, 0.35)):
        claw(x, tx, tz)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    right_arm()
    left_arm()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)), "head": ((0, NECK, 0), (0, TOP, 0))}
    out["arm.R"] = ((-SH_X, SH_Y, 0), R_EL)
    out["forearm.R"] = (R_EL, R_WR)
    out["arm.L"] = ((SH_X, SH_Y, 0), L_EL)
    out["forearm.L"] = (L_EL, L_WR)
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("n01I", "biped", PALETTE, make, joints())
