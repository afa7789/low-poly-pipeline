"""Lich Ghoul (u00E): medido em artifacts/model-sheets/refs/u00E/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/u00E.py -- <out.glb>

Esqueleto curvado que anda de nocas: manto de pele nas costas, antebracos de pele enormes com garras brancas
longas, orbe verde no peito. Perfil: z = (510 - px) * 0.0072, y = (445 - py) * 0.0072 na prancha.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "bone": 0xD6C29E, "bone_dk": 0xB59D78, "fur": 0x7A4A2A, "fur_dk": 0x5A3520, "fur_lt": 0x8E5A34,
    "boot": 0x4A3626, "claw": 0xF2F0E8, "orb": 0x1FA870, "orb_dk": 0x0E6E4C, "eye": 0x38FF98, "black": 0x1A1412,
}

HIP, KNEE, ANKLE = (0.24, 1.1, -0.15), (0.3, 0.82, 0.0), (0.34, 0.2, -0.45)
SH, EL, WR = (0.62, 1.95, 0.3), (0.72, 1.3, 0.35), (0.8, 0.35, 0.58)


def head():
    dz, dy = -0.1, 0.08
    H.frustum("head", "bone", (0, 1.86 + dy, 0.93 + dz), (0, 2.06 + dy, 0.9 + dz), (0.09, 0.1), (0.14, 0.15), sides=6)      # mandibula
    H.frustum("head", "black", (0, 1.9 + dy, 0.99 + dz), (0, 2.02 + dy, 0.99 + dz), (0.07, 0.04), (0.1, 0.04), sides=4)     # boca
    H.frustum("head", "bone", (0, 2.04 + dy, 0.86 + dz), (0, 2.4 + dy, 0.84 + dz), (0.13, 0.17), (0.18, 0.2), sides=8)      # cranio
    H.frustum("head", "bone_dk", (0, 2.4 + dy, 0.84 + dz), (0, 2.58 + dy, 0.8 + dz), (0.18, 0.2), (0.05, 0.1), sides=8)
    for s in (-1, 1):
        H.box("head", "black", (s * 0.075, 2.22 + dy, 1.0 + dz), (0.1, 0.1, 0.06))
        H.box("head", "eye", (s * 0.075, 2.22 + dy, 1.04 + dz), (0.055, 0.055, 0.03))


def torso():
    H.frustum("spine", "bone", (0, 1.35, -0.05), (0, 1.95, 0.25), (0.28, 0.22), (0.4, 0.26), sides=8)    # caixa toracica
    H.frustum("spine", "bone_dk", (0, 1.62, 0.1), (0, 1.66, 0.12), (0.34, 0.27), (0.36, 0.28), sides=8)  # costelas
    H.frustum("spine", "bone_dk", (0, 1.8, 0.16), (0, 1.84, 0.18), (0.38, 0.28), (0.4, 0.29), sides=8)
    H.frustum("spine", "fur_dk", (0, 1.8, 0.38), (0, 1.8, 0.44), (0.25, 0.25), (0.23, 0.23), sides=8)    # aro do orbe
    H.frustum("spine", "orb_dk", (0, 1.8, 0.43), (0, 1.8, 0.5), (0.2, 0.2), (0.19, 0.19), sides=8)
    H.frustum("spine", "orb", (0, 1.8, 0.49), (0, 1.8, 0.54), (0.16, 0.16), (0.1, 0.1), sides=8)
    H.frustum("spine", "fur", (0, 1.9, 0.0), (0, 2.22, 0.08), (0.78, 0.42), (0.46, 0.34), sides=8)        # mantle de pele
    H.frustum("spine", "fur_lt", (0, 2.0, -0.02), (0, 2.2, 0.0), (0.8, 0.44), (0.52, 0.34), sides=8)
    cape = [(0, 2.3, -0.1), (0, 1.7, -0.32), (0, 1.2, -0.7), (0, 0.8, -0.95)]
    H.chain("spine", "fur", cape, [(0.5, 0.2), (0.46, 0.2), (0.36, 0.1), (0.06, 0.04)], sides=4)
    H.chain("spine", "bone", [(0, 2.27, -0.23), (0, 1.75, -0.43), (0, 1.3, -0.62)],
            [(0.06, 0.05), (0.07, 0.05), (0.025, 0.03)], sides=4)
    for s in (-1, 1):       # farrapos da barra do manto, nas laterais
        H.frustum("spine", "fur_dk", (s * 0.42, 1.8, -0.3), (s * 0.5, 1.05, -0.42), (0.1, 0.08), (0.02, 0.03), sides=4)
    H.frustum("pelvis", "bone", (0, 1.0, -0.15), (0, 1.35, -0.08), (0.3, 0.24), (0.26, 0.22), sides=8)
    H.frustum("pelvis", "fur", (0, 1.28, 0.2), (0, 0.82, 0.22), (0.24, 0.04), (0.02, 0.03), sides=4)     # tanga de pele


def leg(s, side):
    x = s
    H.frustum(f"thigh.{side}", "bone", (x * HIP[0], HIP[1] + 0.04, HIP[2]), (x * (KNEE[0] - 0.02), KNEE[1] + 0.05, KNEE[2]),
              (0.15, 0.17), (0.1, 0.12), sides=6)
    H.frustum(f"thigh.{side}", "bone_dk", (x * KNEE[0], KNEE[1] + 0.08, KNEE[2]), (x * KNEE[0], KNEE[1] - 0.06, KNEE[2] + 0.04),
              (0.13, 0.14), (0.15, 0.15), sides=6)
    H.frustum(f"shin.{side}", "bone", (x * KNEE[0], KNEE[1] - 0.02, KNEE[2] + 0.03), (x * ANKLE[0], 0.42, ANKLE[2] + 0.04),
              (0.14, 0.14), (0.1, 0.1), sides=6)
    H.frustum(f"shin.{side}", "boot", (x * ANKLE[0], 0.14, ANKLE[2]), (x * ANKLE[0], 0.52, ANKLE[2] + 0.03),
              (0.14, 0.14), (0.18, 0.17), sides=6)
    H.frustum(f"foot.{side}", "bone_dk", (x * ANKLE[0], 0.1, ANKLE[2] - 0.05), (x * ANKLE[0], 0.07, 0.05),
              (0.14, 0.1), (0.15, 0.07), sides=6)
    H.frustum(f"foot.{side}", "bone_dk", (x * ANKLE[0], 0.07, 0.0), (x * ANKLE[0], 0.05, 0.3), (0.16, 0.07), (0.15, 0.05), sides=6)
    for dx in (-0.09, 0, 0.09):
        H.frustum(f"foot.{side}", "claw", (x * ANKLE[0] + dx, 0.05, 0.28), (x * ANKLE[0] + dx * 1.2, 0.03, 0.5),
                  (0.035, 0.03), (0.005, 0.005), sides=4)


def arm(s, side):
    a, f = f"arm.{side}", f"forearm.{side}"
    H.frustum(a, "fur", (s * 0.5, 1.98, 0.28), (s * 0.7, 1.95, 0.3), (0.16, 0.2), (0.17, 0.2), sides=8)    # ombro de pele
    H.frustum(a, "bone", (s * SH[0], SH[1] - 0.02, SH[2]), (s * EL[0], EL[1] + 0.04, EL[2]), (0.13, 0.13), (0.1, 0.1), sides=6)
    H.frustum(a, "bone_dk", (s * EL[0], EL[1] + 0.08, EL[2]), (s * EL[0], EL[1] - 0.08, EL[2]), (0.12, 0.12), (0.13, 0.13), sides=6)
    H.frustum(f, "fur", (s * EL[0], 1.22, 0.36), (s * 0.77, 0.7, 0.47), (0.19, 0.19), (0.21, 0.2), sides=6)    # luva de pele
    H.frustum(f, "fur_dk", (s * 0.77, 0.7, 0.47), (s * WR[0], 0.34, WR[2]), (0.21, 0.2), (0.19, 0.17), sides=6)
    H.frustum(f, "bone_dk", (s * WR[0], 0.36, WR[2]), (s * WR[0], 0.24, WR[2] + 0.04), (0.17, 0.15), (0.17, 0.1), sides=6)
    for dx in (-0.12, -0.04, 0.04, 0.12):       # quatro garras brancas longas
        H.frustum(f, "claw", (s * WR[0] + dx, 0.3, WR[2] + 0.04), (s * WR[0] + dx * 1.35, 0.03, 0.98),
                  (0.04, 0.035), (0.005, 0.005), sides=4)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        arm(s, side)


def joints():
    out = {"pelvis": ((0, 1.1, -0.15), (0, 1.35, -0.08)), "spine": ((0, 1.35, -0.08), (0, 2.0, 0.3)),
           "head": ((0, 2.0, 0.5), (0, 2.3, 1.0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH[0], SH[1], SH[2]), (s * EL[0], EL[1], EL[2]))
        out[f"forearm.{side}"] = ((s * EL[0], EL[1], EL[2]), (s * WR[0], WR[1], WR[2]))
        out[f"thigh.{side}"] = ((s * HIP[0], HIP[1], HIP[2]), (s * KNEE[0], KNEE[1], KNEE[2]))
        out[f"shin.{side}"] = ((s * KNEE[0], KNEE[1], KNEE[2]), (s * ANKLE[0], ANKLE[1], ANKLE[2]))
        out[f"foot.{side}"] = ((s * ANKLE[0], ANKLE[1], ANKLE[2]), (s * ANKLE[0], 0.06, 0.5))
    return out


H.build("u00E", "biped", PALETTE, make, joints())
