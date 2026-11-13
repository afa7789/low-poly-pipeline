"""Murloc Warrior (n00I): medido em artifacts/model-sheets/refs/n00I/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n00I.py -- <out.glb>

Sapo agachado e curvado, pernas abertas de rã, cabeça enorme de boca aberta, marreta de pedra na mão direita.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "green": 0x11A75C, "green_dk": 0x0C8A4A, "olive": 0xA9A31A, "lime": 0x8DBF1E, "pale": 0xD7E57F,
    "fin": 0xC4E63A, "teal": 0x13927A, "eye": 0x3FE6F0, "tooth": 0xF2DDA0, "mouth": 0x7A1228, "tongue": 0xD84A5A,
    "pink": 0xC0409A, "rope": 0xD9A857, "stone": 0x7C7D82, "wood": 0x6B4428,
}

# juntas (família biped): quadril baixo e atrás, joelhos abertos à frente
HIP, KNEE, ANKLE, TOE = (0.3, 0.95, -0.45), (0.8, 0.68, 0.1), (0.55, 0.15, -0.35), (1.0, 0.07, 0.35)
SH, EL_L, WR_L = (0.62, 1.62, -0.05), (0.8, 1.05, 0.1), (0.4, 0.45, 0.35)
EL_R, FIST = (0.8, 1.05, 0.1), (1.0, 1.35, 0.45)


def mx(s, p):
    return (s * p[0], p[1], p[2])


def head():
    H.frustum("head", "olive", (0, 1.68, 0.1), (0, 2.3, 0.28), (0.6, 0.55), (0.5, 0.46), sides=8)            # crânio
    H.frustum("head", "olive", (0, 1.85, 0.45), (0, 1.84, 1.0), (0.5, 0.36), (0.34, 0.2), sides=8)           # focinho
    H.frustum("head", "pale", (0, 1.58, 0.3), (0, 1.62, 1.0), (0.48, 0.4), (0.33, 0.16), sides=8)             # mandíbula
    H.frustum("head", "mouth", (0, 1.76, 0.5), (0, 1.76, 0.97), (0.34, 0.1), (0.26, 0.07), sides=6)           # boca aberta
    H.box("head", "tongue", (0, 1.7, 0.7), (0.2, 0.06, 0.3))
    H.frustum("head", "pink", (0, 2.28, 0.15), (0, 2.38, 0.15), (0.12, 0.1), (0.08, 0.06), sides=6)
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.36, 2.02, 0.68), (0.24, 0.13, 0.1))
        for x in (0.1, 0.25):                                       # presas de cima e de baixo
            H.frustum("head", "tooth", (s * x, 1.86, 0.93), (s * x, 1.7, 0.95), (0.045, 0.035), (0.005, 0.005), sides=4)
            H.frustum("head", "tooth", (s * x, 1.62, 0.9), (s * x, 1.78, 0.92), (0.04, 0.03), (0.005, 0.005), sides=4)
        H.frustum("head", "tooth", (s * 0.34, 1.62, 0.8), (s * 0.34, 1.8, 0.82), (0.05, 0.04), (0.005, 0.005), sides=4)
        H.panel("head", "fin", [(s * 0.46, 1.95, 0.1), (s * 0.9, 2.12, 0.0), (s * 0.85, 1.72, 0.05)], thickness=0.04)   # barbatana


def torso():
    H.frustum("pelvis", "green", (0, 0.85, -0.5), (0, 1.25, -0.42), (0.58, 0.44), (0.62, 0.46), sides=8)
    H.frustum("spine", "green", (0, 1.25, -0.42), (0, 1.7, -0.12), (0.62, 0.46), (0.68, 0.44), sides=8)
    H.frustum("spine", "green", (0, 1.7, -0.12), (0, 1.9, 0.0), (0.68, 0.44), (0.44, 0.3), sides=8)             # ombros em V
    H.frustum("spine", "pale", (0, 1.3, -0.2), (0, 1.72, 0.08), (0.5, 0.3), (0.52, 0.26), sides=8)            # barriga clara
    for i, (y, z) in enumerate(((1.8, -0.35), (1.6, -0.5), (1.4, -0.62), (1.15, -0.7))):       # crista dorsal
        H.panel("spine", "fin", [(0.0, y + 0.1, z), (0, y + 0.3, z - 0.25 - 0.04 * i), (0, y - 0.15, z - 0.3)], thickness=0.06)
    H.frustum("pelvis", "rope", (0, 0.92, -0.5), (0, 1.06, -0.48), (0.55, 0.47), (0.56, 0.48), sides=8)
    for s in (-1, 1):
        H.box("pelvis", "stone", (s * 0.3, 0.84, -0.02), (0.2, 0.3, 0.16))
        H.box("pelvis", "stone", (s * 0.38, 0.84, -0.96), (0.2, 0.3, 0.16))
        H.panel("spine", "fin", [(s * 0.55, 1.45, -0.55), (s * 0.7, 1.3, -0.8), (s * 0.55, 1.05, -0.65)], thickness=0.04)


def leg(s, side):
    t, sh, f = f"thigh.{side}", f"shin.{side}", f"foot.{side}"
    hip, knee, ank, toe = (mx(s, p) for p in (HIP, KNEE, ANKLE, TOE))
    mid = tuple((a + b) / 2 for a, b in zip(hip, knee))
    H.frustum(t, "green", (hip[0] * 0.8, hip[1] + 0.08, hip[2]), mid, (0.36, 0.36), (0.31, 0.31), sides=6)
    H.frustum(t, "lime", mid, knee, (0.31, 0.31), (0.21, 0.21), sides=6)
    H.frustum(sh, "lime", knee, (knee[0] * 0.9, 0.42, -0.1), (0.21, 0.21), (0.19, 0.18), sides=6)             # panturrilha
    H.frustum(sh, "lime", (knee[0] * 0.9, 0.42, -0.1), ank, (0.19, 0.18), (0.11, 0.11), sides=6)
    H.frustum(f, "lime", (ank[0], 0.17, ank[2] - 0.05), (toe[0] * 0.8, 0.09, 0.0), (0.15, 0.1), (0.14, 0.05), sides=6)
    for k in (-1, 0, 1):          # dedos palmados em leque
        tip = (toe[0] + s * 0.2 * k * 0.5 + s * 0.1, 0.05, toe[2] + 0.25 - 0.1 * abs(k))
        H.frustum(f, "teal" if k else "fin", (toe[0] * 0.8, 0.09, 0.0), tip, (0.09, 0.05), (0.04, 0.02), sides=4)
        H.frustum(f, "fin", (toe[0] * 0.8, 0.07, 0.0), tip, (0.12, 0.02), (0.07, 0.015), sides=4)


def arm_l():
    H.frustum("arm.L", "green", (SH[0], SH[1], SH[2]), EL_L, (0.26, 0.24), (0.17, 0.16), sides=6)
    H.frustum("arm.L", "green", (0.5, 1.75, -0.05), (0.7, 1.45, 0.0), (0.18, 0.2), (0.25, 0.23), sides=6)       # ombro
    H.frustum("forearm.L", "lime", EL_L, (0.55, 0.75, 0.25), (0.17, 0.16), (0.14, 0.12), sides=6)
    H.frustum("forearm.L", "lime", (0.55, 0.75, 0.25), WR_L, (0.14, 0.12), (0.12, 0.09), sides=6)
    for dx, dz in ((-0.07, 0.0), (0.0, 0.03), (0.07, 0.0)):                     # mão pendurada com dedos
        H.frustum("forearm.L", "lime", WR_L, (0.33 + dx, 0.1, 0.4 + dz), (0.11, 0.05), (0.035, 0.03), sides=4)


def arm_r():
    H.frustum("arm.R", "green", (-SH[0], SH[1], SH[2]), (-EL_R[0], EL_R[1], EL_R[2]), (0.26, 0.24), (0.17, 0.16), sides=6)
    H.frustum("arm.R", "green", (-0.5, 1.75, -0.05), (-0.7, 1.45, 0.0), (0.18, 0.2), (0.25, 0.23), sides=6)
    H.frustum("forearm.R", "lime", (-0.8, 1.05, 0.1), (-0.92, 1.2, 0.3), (0.17, 0.16), (0.16, 0.15), sides=6)
    H.frustum("forearm.R", "lime", (-0.92, 1.2, 0.3), (-FIST[0], FIST[1] - 0.05, FIST[2]), (0.16, 0.15), (0.21, 0.2), sides=6)
    H.frustum("forearm.R", "lime", (-FIST[0], FIST[1] - 0.2, FIST[2]), (-FIST[0], FIST[1] + 0.12, FIST[2]), (0.2, 0.2), (0.2, 0.2), sides=6)  # punho
    # marreta de pedra: cabo na mão, cabeça grande no alto
    H.frustum("forearm.R", "wood", (-FIST[0], 0.85, FIST[2]), (-FIST[0], 2.05, FIST[2]), (0.07, 0.07), (0.06, 0.06), sides=6)
    H.frustum("forearm.R", "stone", (-FIST[0], 2.0, FIST[2]), (-FIST[0], 2.42, FIST[2]), (0.2, 0.18), (0.18, 0.17), sides=4)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    arm_l()
    arm_r()


def joints():
    out = {"pelvis": ((0, 0.95, -0.5), (0, 1.25, -0.42)), "spine": ((0, 1.25, -0.42), (0, 1.65, -0.05)),
           "head": ((0, 1.65, -0.05), (0, 1.95, 0.55)),
           "arm.L": (SH, EL_L), "forearm.L": (EL_L, WR_L),
           "arm.R": (mx(-1, SH), mx(-1, EL_R)), "forearm.R": (mx(-1, EL_R), (-0.95, 0.75, 0.3))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = (mx(s, HIP), mx(s, KNEE))
        out[f"shin.{side}"] = (mx(s, KNEE), mx(s, ANKLE))
        out[f"foot.{side}"] = (mx(s, ANKLE), mx(s, TOE))
    return out


H.build("n00I", "biped", PALETTE, make, joints())
