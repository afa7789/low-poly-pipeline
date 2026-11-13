"""Hrimthrusa (n011): morsa de parka verde com lança de gelo (mão direita) e lanterna (mão esquerda).

    blender -b --factory-startup -P tools/blender/units/n011.py -- <out.glb>

Medido em artifacts/model-sheets/refs/n011/sheet.jpg (~370 px por metro na frente).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "olive": 0x7E7A38, "olive_dk": 0x544F24, "hood": 0x4F4B20, "white": 0xEDE8DC, "belt": 0x4A3226,
    "boot": 0x8A4636, "skin": 0xC98070, "face_dk": 0x4A3524, "cream": 0xEADFC0, "orange": 0xF0A030,
    "blue": 0x86CDEC, "rope": 0xC8A878, "wood": 0xB8864A, "lamp": 0x3A2A22, "flame": 0xFFC040, "pack": 0x4A3228,
}

SH, EL, WR = (0.55, 1.5, 0.0), (0.72, 1.12, 0.05), (0.66, 0.82, 0.22)
RSH, REL, RWR = (-0.55, 1.5, 0.0), (-0.76, 1.15, 0.1), (-0.8, 0.9, 0.3)
HIP, KNEE, ANK, LEG_X = 0.62, 0.36, 0.1, 0.26


def spear_pt(y):
    """Ponto da haste à altura y: encosta no chão atrás do pé e inclina para fora e para a frente."""
    return (-0.65 - 0.125 * y, y, 0.1 + 0.23 * y)


def head():
    H.frustum("head", "hood", (0, 1.62, -0.05), (0, 2.0, -0.1), (0.4, 0.38), (0.36, 0.34), sides=8)       # capuz
    H.frustum("head", "hood", (0, 2.0, -0.1), (0, 2.3, -0.05), (0.36, 0.34), (0.1, 0.12), sides=8)
    H.frustum("head", "olive_dk", (0, 1.7, 0.2), (0, 2.12, 0.2), (0.28, 0.14), (0.26, 0.14), sides=6)     # abertura
    H.frustum("head", "face_dk", (0, 1.72, 0.25), (0, 2.1, 0.3), (0.26, 0.22), (0.24, 0.2), sides=8)      # rosto
    H.frustum("head", "skin", (0, 1.62, 0.34), (0, 1.88, 0.52), (0.2, 0.15), (0.17, 0.12), sides=8)       # focinho
    H.box("head", "orange", (0, 1.98, 0.5), (0.34, 0.07, 0.04))
    H.frustum("head", "face_dk", (0, 1.9, 0.5), (0, 1.84, 0.62), (0.07, 0.06), (0.05, 0.04), sides=6)     # nariz
    for s in (-1, 1):
        H.frustum("head", "cream", (s * 0.09, 1.72, 0.56), (s * 0.1, 1.38, 0.58), (0.05, 0.05), (0.025, 0.025), sides=6)


def torso():
    H.frustum("pelvis", "olive", (0, 0.34, 0), (0, 0.98, 0), (0.7, 0.54), (0.56, 0.48), sides=8)         # saia da parka
    H.frustum("pelvis", "olive_dk", (0, 0.34, 0), (0, 0.42, 0), (0.7, 0.54), (0.7, 0.54), sides=8)
    H.frustum("pelvis", "belt", (0, 0.92, 0), (0, 1.08, 0), (0.58, 0.5), (0.58, 0.5), sides=8)
    H.frustum("spine", "olive", (0, 1.05, 0), (0, 1.45, 0), (0.58, 0.49), (0.62, 0.47), sides=8)
    H.frustum("spine", "olive", (0, 1.45, 0), (0, 1.75, 0), (0.62, 0.47), (0.4, 0.34), sides=8)
    H.frustum("spine", "white", (0, 1.52, 0.02), (0, 1.8, 0.04), (0.56, 0.46), (0.34, 0.3), sides=8)     # gola de pele
    H.frustum("spine", "white", (0, 1.38, 0.3), (0, 1.62, 0.28), (0.1, 0.1), (0.16, 0.1), sides=4)
    H.frustum("pelvis", "rope", (0, 1.0, 0.48), (0, 1.0, 0.56), (0.24, 0.24), (0.24, 0.24), sides=8)     # rolo de corda
    H.frustum("pelvis", "olive", (0, 1.0, 0.56), (0, 1.0, 0.6), (0.12, 0.12), (0.12, 0.12), sides=8)
    H.frustum("pelvis", "rope", (0.08, 0.9, 0.52), (0.2, 0.55, 0.52), (0.04, 0.04), (0.03, 0.03), sides=4)
    # mochila: caixa escura, boia laranja e ganchos azuis
    H.box("spine", "pack", (0.1, 1.45, -0.55), (0.62, 0.55, 0.3))
    H.frustum("spine", "orange", (-0.3, 1.2, -0.6), (-0.3, 1.8, -0.6), (0.12, 0.12), (0.12, 0.12), sides=6)
    for x, y in ((0.0, 1.0), (0.12, 1.45)):
        H.chain("spine", "blue", [(x, y + 0.1, -0.7), (x, y - 0.05, -0.76), (x + 0.1, y - 0.12, -0.78)],
                [(0.03, 0.03), (0.03, 0.03), (0.01, 0.01)], sides=4)


def arm_left():
    H.frustum("arm.L", "olive", (SH[0] - 0.1, 1.6, 0.0), (SH[0] + 0.12, 1.55, 0.0), (0.22, 0.22), (0.26, 0.26), sides=8)
    H.frustum("arm.L", "olive", (SH[0] + 0.05, 1.55, 0.0), (EL[0], EL[1], EL[2]), (0.26, 0.26), (0.2, 0.2), sides=8)
    H.frustum("forearm.L", "olive", (EL[0], EL[1] + 0.05, EL[2]), (WR[0] + 0.02, 0.96, WR[2] - 0.05), (0.2, 0.2), (0.22, 0.22), sides=8)
    H.frustum("forearm.L", "white", (WR[0] + 0.02, 1.0, WR[2] - 0.06), (WR[0], 0.84, WR[2]), (0.24, 0.24), (0.24, 0.24), sides=8)
    H.frustum("forearm.L", "skin", (WR[0], 0.9, WR[2]), (WR[0], 0.68, WR[2] + 0.04), (0.2, 0.19), (0.17, 0.15), sides=8)
    # lanterna pendurada na mão
    c = (WR[0], 0.0, WR[2] + 0.02)
    H.frustum("forearm.L", "lamp", (c[0], 0.7, c[2]), (c[0], 0.6, c[2]), (0.03, 0.03), (0.1, 0.1), sides=6)
    H.frustum("forearm.L", "flame", (c[0], 0.58, c[2]), (c[0], 0.38, c[2]), (0.1, 0.1), (0.13, 0.13), sides=6)
    H.frustum("forearm.L", "lamp", (c[0], 0.38, c[2]), (c[0], 0.3, c[2]), (0.15, 0.15), (0.15, 0.15), sides=6)


def arm_right():
    H.frustum("arm.R", "olive", (RSH[0] + 0.1, 1.6, 0.0), (RSH[0] - 0.12, 1.55, 0.0), (0.22, 0.22), (0.26, 0.26), sides=8)
    H.frustum("arm.R", "olive", (RSH[0] - 0.05, 1.55, 0.0), (REL[0], REL[1], REL[2]), (0.26, 0.26), (0.2, 0.2), sides=8)
    H.frustum("forearm.R", "olive", (REL[0], REL[1] + 0.05, REL[2]), (RWR[0] - 0.02, 1.0, RWR[2] - 0.05), (0.2, 0.2), (0.22, 0.22), sides=8)
    H.frustum("forearm.R", "white", (RWR[0] - 0.02, 1.05, RWR[2] - 0.06), (RWR[0], 0.9, RWR[2]), (0.24, 0.24), (0.24, 0.24), sides=8)
    H.frustum("forearm.R", "skin", (RWR[0], 0.96, RWR[2]), (RWR[0], 0.76, RWR[2]), (0.2, 0.19), (0.19, 0.18), sides=8)
    pts = [spear_pt(y) for y in (0.0, 0.5, 1.0, 1.5, 2.0)]
    H.chain("forearm.R", "wood", pts, [(0.045, 0.045)] * 5, sides=6)
    H.frustum("forearm.R", "blue", spear_pt(1.9), spear_pt(2.4), (0.1, 0.1), (0.005, 0.005), sides=4)  # ponta de gelo
    px, py, pz = spear_pt(2.1)
    H.chain("forearm.R", "blue", [(px - 0.02, py - 0.25, pz), (px - 0.2, py - 0.12, pz), (px - 0.08, py + 0.05, pz)],
            [(0.06, 0.06), (0.05, 0.05), (0.005, 0.005)], sides=4)                                      # farpa
    H.frustum("forearm.R", "blue", spear_pt(1.75), (px - 0.16, 1.95, pz), (0.14, 0.08), (0.26, 0.08), sides=6)   # disco de gelo


def legs(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "white", (x, KNEE - 0.04, 0), (x, HIP + 0.1, 0), (0.2, 0.2), (0.26, 0.26), sides=6)
    H.frustum(f"shin.{side}", "white", (x, 0.28, 0.0), (x, KNEE + 0.06, 0.0), (0.2, 0.2), (0.22, 0.22), sides=6)
    H.frustum(f"shin.{side}", "boot", (x, ANK - 0.06, 0.02), (x, 0.3, 0.02), (0.2, 0.2), (0.25, 0.24), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.12, -0.1), (x, 0.1, 0.38), (0.25, 0.24), (0.2, 0.12), sides=6)
    H.frustum(f"foot.{side}", "face_dk", (x, 0.01, -0.12), (x, 0.01, 0.4), (0.26, 0.02), (0.22, 0.02), sides=4)


def make():
    head()
    torso()
    arm_left()
    arm_right()
    for s, side in ((1, "L"), (-1, "R")):
        legs(s, side)


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, 1.05, 0)), "spine": ((0, 1.05, 0), (0, 1.6, 0)),
           "head": ((0, 1.6, 0.1), (0, 2.3, 0.1))}
    out["arm.L"], out["forearm.L"] = (SH, EL), (EL, WR)
    out["arm.R"], out["forearm.R"] = (RSH, REL), (REL, RWR)
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANK, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANK, 0), (s * LEG_X, 0.06, 0.4))
    return out


H.build("n011", "biped", PALETTE, make, joints())
