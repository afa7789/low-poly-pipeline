"""Murloc Assassin (n00K): medido em artifacts/model-sheets/refs/n00K/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n00K.py -- <out.glb>

Corpo preto curvado de braços longos, máscara de crânio com joias turquesa, capa esfarrapada verde-azulada,
gancho (gaff) de haste longa na mão direita e punho esquerdo enorme enfaixado. Sem adagas.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "black": 0x211C1B, "black_lt": 0x322A28, "bone": 0xC9AE7E, "bone_dk": 0x8E7650, "socket": 0x2B221C, "tooth": 0xEDE0BC,
    "teal": 0x587D78, "teal_dk": 0x3F625E, "gem": 0x2BE0CC, "hook": 0x4F7F7A,
}

HIP, KNEE, ANKLE, TOE = (0.28, 0.98, -0.45), (0.36, 0.55, -0.05), (0.34, 0.12, -0.25), (0.42, 0.05, 0.35)
SH_L, EL_L, WR_L = (0.6, 1.9, -0.05), (0.78, 1.3, 0.05), (0.82, 0.62, 0.1)
SH_R, EL_R, WR_R = (-0.6, 1.9, -0.05), (-0.78, 1.3, -0.4), (-0.8, 0.85, -0.65)
POLE_Z = -0.65


def head():
    H.frustum("head", "bone", (0, 1.95, 0.0), (0, 2.42, 0.18), (0.42, 0.44), (0.34, 0.36), sides=8)            # crânio
    H.frustum("head", "bone", (0, 2.0, 0.3), (0, 1.7, 1.05), (0.36, 0.3), (0.2, 0.12), sides=8)             # focinho
    H.frustum("head", "bone_dk", (0, 1.62, 0.3), (0, 1.52, 0.9), (0.26, 0.22), (0.12, 0.07), sides=6)        # mandíbula
    H.frustum("head", "socket", (0, 1.78, 0.98), (0, 1.76, 1.1), (0.09, 0.05), (0.07, 0.04), sides=4)         # nariz
    for s in (-1, 1):
        H.box("head", "socket", (s * 0.17, 2.13, 0.43), (0.16, 0.15, 0.12))                                  # órbitas
        H.frustum("head", "tooth", (s * 0.17, 1.8, 0.95), (s * 0.17, 1.2, 1.05), (0.06, 0.05), (0.008, 0.008), sides=4)   # presas
        H.frustum("head", "tooth", (s * 0.08, 1.74, 0.97), (s * 0.08, 1.5, 1.0), (0.04, 0.035), (0.005, 0.005), sides=4)
        H.frustum("head", "gem", (s * 0.34, 1.92, 0.15), (s * 0.5, 1.92, 0.15), (0.13, 0.13), (0.1, 0.1), sides=8)  # joias
        H.panel("head", "teal", [(s * 0.2, 2.0, -0.05), (s * 0.95, 2.3, -0.2), (s * 0.85, 1.7, -0.05)], thickness=0.04)    # gola


def torso():
    H.frustum("pelvis", "black", (0, 0.85, -0.45), (0, 1.3, -0.35), (0.44, 0.38), (0.38, 0.35), sides=8)
    H.frustum("spine", "black", (0, 1.3, -0.35), (0, 1.8, -0.02), (0.38, 0.34), (0.66, 0.46), sides=8)        # V
    H.frustum("spine", "black_lt", (0, 1.8, -0.02), (0, 2.04, 0.05), (0.66, 0.46), (0.4, 0.3), sides=8)     # ombros caídos
    H.frustum("spine", "teal", (0.4, 1.9, 0.38), (-0.32, 1.25, 0.3), (0.09, 0.03), (0.09, 0.03), sides=4)    # faixa no peito
    H.frustum("pelvis", "teal_dk", (0, 1.15, -0.4), (0, 1.3, -0.35), (0.37, 0.35), (0.36, 0.34), sides=8)    # cinto
    H.panel("pelvis", "teal", [(-0.22, 1.1, 0.0), (0.22, 1.1, 0.0), (0.12, 0.62, 0.02), (-0.1, 0.72, 0.03)], thickness=0.04)  # tanga
    H.panel("spine", "teal", [(-0.95, 2.05, -0.15), (0.95, 2.05, -0.15), (0.6, 1.4, -0.55), (0.0, 1.15, -0.6), (-0.5, 1.4, -0.55)], thickness=0.05)   # capa


def leg(s, side):
    hip, knee, ank, toe = ((s * p[0], p[1], p[2]) for p in (HIP, KNEE, ANKLE, TOE))
    t, sh, f = f"thigh.{side}", f"shin.{side}", f"foot.{side}"
    mid = (s * 0.33, 0.78, -0.25)
    H.frustum(t, "black", (hip[0], hip[1] + 0.1, hip[2]), mid, (0.32, 0.32), (0.26, 0.26), sides=6)
    H.frustum(t, "black_lt", mid, knee, (0.26, 0.26), (0.19, 0.19), sides=6)
    H.frustum(sh, "black", knee, (s * 0.34, 0.35, -0.15), (0.2, 0.2), (0.16, 0.16), sides=6)
    H.frustum(sh, "black", (s * 0.34, 0.35, -0.15), ank, (0.14, 0.14), (0.1, 0.1), sides=6)
    H.frustum(f, "black_lt", (ank[0], 0.14, ank[2] - 0.05), (toe[0], 0.07, 0.1), (0.14, 0.1), (0.15, 0.05), sides=6)
    for k in (-1, 0, 1):
        H.frustum(f, "black", (toe[0], 0.07, 0.1), (toe[0] + s * 0.09 * k + s * 0.04, 0.04, toe[2] + 0.2), (0.07, 0.04), (0.025, 0.02), sides=4)


def arm_l():
    H.frustum("arm.L", "black", (0.5, 2.0, -0.05), (0.75, 1.65, 0.0), (0.28, 0.3), (0.34, 0.31), sides=6)   # ombro
    H.frustum("arm.L", "black_lt", (0.75, 1.65, 0.0), EL_L, (0.31, 0.28), (0.23, 0.22), sides=6)
    H.frustum("forearm.L", "black", EL_L, (0.8, 0.95, 0.07), (0.23, 0.22), (0.25, 0.24), sides=6)
    H.frustum("forearm.L", "teal", (0.8, 1.0, 0.08), (0.82, 0.62, 0.1), (0.3, 0.3), (0.34, 0.33), sides=8)      # punho enfaixado
    H.frustum("forearm.L", "teal_dk", (0.8, 0.9, 0.08), (0.81, 0.82, 0.09), (0.35, 0.34), (0.35, 0.34), sides=8)
    H.frustum("forearm.L", "black", (0.82, 0.62, 0.1), (0.82, 0.3, 0.14), (0.22, 0.2), (0.16, 0.14), sides=6)  # punho preto abaixo


def arm_r():
    H.frustum("arm.R", "black", (-0.5, 2.0, -0.05), (-0.75, 1.65, -0.1), (0.28, 0.3), (0.34, 0.31), sides=6)
    H.frustum("arm.R", "black_lt", (-0.75, 1.65, -0.1), EL_R, (0.31, 0.28), (0.23, 0.22), sides=6)
    H.frustum("forearm.R", "black", EL_R, (-0.8, 1.1, -0.55), (0.23, 0.22), (0.25, 0.24), sides=6)
    H.frustum("forearm.R", "teal", (-0.8, 1.1, -0.55), (-0.8, 0.9, POLE_Z), (0.21, 0.2), (0.23, 0.22), sides=6)   # luva
    H.frustum("forearm.R", "teal_dk", (-0.8, 1.0, POLE_Z), (-0.8, 0.8, POLE_Z), (0.25, 0.24), (0.25, 0.24), sides=6)
    # gaff: haste longa e gancho com farpa
    H.frustum("forearm.R", "hook", (-0.8, 0.45, POLE_Z), (-0.8, 2.3, POLE_Z), (0.06, 0.06), (0.055, 0.055), sides=6)
    pts = [(-0.8, 2.3, POLE_Z), (-0.8, 2.55, POLE_Z - 0.05), (-0.8, 2.65, POLE_Z - 0.3), (-0.8, 2.45, POLE_Z - 0.5), (-0.8, 2.25, POLE_Z - 0.45)]
    H.chain("forearm.R", "hook", pts, [(0.06, 0.06), (0.055, 0.055), (0.05, 0.05), (0.04, 0.04), (0.025, 0.025)], sides=6)
    H.frustum("forearm.R", "hook", (-0.8, 2.25, POLE_Z - 0.45), (-0.8, 2.48, POLE_Z - 0.4), (0.1, 0.03), (0.01, 0.01), sides=4)   # farpa


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    arm_l()
    arm_r()


def joints():
    out = {"pelvis": ((0, 0.95, -0.45), (0, 1.3, -0.35)), "spine": ((0, 1.3, -0.35), (0, 1.85, 0.0)),
           "head": ((0, 1.85, 0.0), (0, 2.2, 0.45)),
           "arm.L": (SH_L, EL_L), "forearm.L": (EL_L, WR_L), "arm.R": (SH_R, EL_R), "forearm.R": (EL_R, WR_R)}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * HIP[0], HIP[1], HIP[2]), (s * KNEE[0], KNEE[1], KNEE[2]))
        out[f"shin.{side}"] = ((s * KNEE[0], KNEE[1], KNEE[2]), (s * ANKLE[0], ANKLE[1], ANKLE[2]))
        out[f"foot.{side}"] = ((s * ANKLE[0], ANKLE[1], ANKLE[2]), (s * TOE[0], TOE[1], TOE[2]))
    return out


H.build("n00K", "biped", PALETTE, make, joints())
