"""Wizard (h00W): medido em artifacts/model-sheets/refs/h00W/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/h00W.py -- <out.glb>
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "coat": 0xE4EFE6, "coat_dk": 0xC3D3C9, "glass": 0x49B2D6, "glass_lt": 0x7FCDE0, "face": 0x2F7C86,
    "gold": 0x9A7A30, "gold_lt": 0xC49E42, "strap": 0x1F3A40, "trouser": 0x1E4A4C, "boot": 0x173F42,
    "trim": 0x3AA8D6, "flask": 0x3A3F48, "orange": 0xE8832A, "sole": 0x10282A,
}

HIP, KNEE, ANKLE, LEG_X = 1.05, 0.58, 0.16, 0.18
WAIST, NECK, TOP = 1.4, 2.1, 2.78
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.3, 2.0, 0.36, 1.5, 1.0
ORB = (0.24, 1.56, 0.5)
ZB = 0.08       # o corpo da prancha fica adiantado em relação ao esqueleto: desloca todas as peças e juntas


def _shifted(fn):
    def inner(bone, tone, a, b, ra, rb, sides=8):
        return fn(bone, tone, (a[0], a[1], a[2] + ZB), (b[0], b[1], b[2] + ZB), ra, rb, sides)
    return inner


H.frustum = _shifted(H.frustum)


def head():
    H.frustum("head", "face", (0, 2.3, 0.0), (0, 2.62, 0.0), (0.12, 0.13), (0.14, 0.15), sides=6)
    H.box("head", "face", (0, 2.45, 0.255), (0.22, 0.34, 0.03))
    H.frustum("head", "glass", (0, 2.2, 0), (0, 2.62, 0), (0.23, 0.22), (0.25, 0.24), sides=8)
    H.frustum("head", "glass_lt", (0, 2.62, 0), (0, 2.72, 0), (0.25, 0.24), (0.2, 0.19), sides=8)
    H.frustum("head", "glass_lt", (0, 2.72, 0), (0, 2.79, 0), (0.2, 0.19), (0.1, 0.09), sides=8)
    H.frustum("head", "gold", (0, 2.18, 0), (0, 2.24, 0), (0.3, 0.28), (0.27, 0.25), sides=8)
    H.frustum("head", "coat", (0, 1.98, 0), (0, 2.2, 0), (0.22, 0.2), (0.32, 0.27), sides=8)      # gola alta
    H.frustum("head", "gold", (0, 2.0, 0.1), (0, 2.18, 0.1), (0.2, 0.2), (0.28, 0.24), sides=6)


def torso():
    H.frustum("spine", "coat", (0, WAIST - 0.05, 0), (0, SH_Y, 0), (0.3, 0.23), (0.34, 0.25), sides=8)
    H.frustum("spine", "coat", (0, SH_Y, 0), (0, 2.14, 0), (0.34, 0.25), (0.24, 0.2), sides=8)
    H.frustum("spine", "coat_dk", (0, 1.8, 0.2), (0, 1.5, 0.3), (0.025, 0.02), (0.025, 0.02), sides=4)   # abotoadura
    for s in (-1, 1):       # alça em diagonal, frente e costas
        H.frustum("spine", "strap", (s * 0.34, 2.02, 0.31), (-s * 0.32, 1.45, 0.33), (0.065, 0.03), (0.065, 0.03), sides=4)
    H.frustum("spine", "strap", (0.34, 2.02, -0.31), (-0.32, 1.45, -0.33), (0.07, 0.03), (0.07, 0.03), sides=4)
    for t in (0.2, 0.5, 0.8):       # frascos na alça
        x, y = 0.34 - 0.66 * t, 2.02 - 0.57 * t
        H.frustum("spine", "flask", (x, y - 0.07, 0.36), (x, y + 0.06, 0.36), (0.09, 0.05), (0.07, 0.05), sides=6)
        H.frustum("spine", "orange", (x, y + 0.06, 0.36), (x, y + 0.1, 0.36), (0.04, 0.03), (0.03, 0.025), sides=6)
    H.frustum("spine", "gold", (-0.33, 1.98, 0.0), (-0.45, 2.08, 0.0), (0.07, 0.07), (0.07, 0.07), sides=6)       # manômetro
    H.frustum("spine", "gold_lt", (-0.45, 2.06, 0.0), (-0.52, 2.12, 0.0), (0.05, 0.05), (0.04, 0.04), sides=6)


def coat_skirt():
    H.frustum("pelvis", "coat", (0, 0.95, 0), (0, WAIST, 0), (0.36, 0.27), (0.32, 0.25), sides=8)
    H.frustum("pelvis", "strap", (0, WAIST - 0.08, 0), (0, WAIST + 0.03, 0), (0.34, 0.27), (0.34, 0.27), sides=8)
    H.box("pelvis", "gold", (-0.43, 1.0, 0.02), (0.14, 0.3, 0.26))       # bolsa de latão no quadril
    H.box("pelvis", "gold_lt", (-0.43, 0.96, 0.17), (0.1, 0.12, 0.06))
    H.box("pelvis", "strap", (-0.4, 1.24, 0.02), (0.05, 0.3, 0.05))


def leg(s, side):
    x0, kx = s * LEG_X, s * 0.18
    # aba do casaco que cai sobre a coxa e a canela: abre para a barra azul
    H.frustum(f"thigh.{side}", "coat", (x0, KNEE, 0), (x0, HIP + 0.05, 0), (0.21, 0.27), (0.19, 0.26), sides=6)
    H.frustum(f"shin.{side}", "coat", (kx + s * 0.02, 0.34, 0), (kx + s * 0.01, KNEE + 0.02, 0), (0.21, 0.29), (0.19, 0.27), sides=6)
    H.frustum(f"shin.{side}", "trim", (kx + s * 0.03, 0.29, 0), (kx + s * 0.02, 0.36, 0), (0.225, 0.3), (0.21, 0.29), sides=6)
    H.frustum(f"thigh.{side}", "trouser", (s * 0.21, KNEE - 0.05, 0.12), (s * 0.2, HIP, 0.1), (0.12, 0.1), (0.16, 0.12), sides=6)
    H.frustum(f"shin.{side}", "boot", (kx, ANKLE - 0.02, 0), (kx, 0.5, 0), (0.16, 0.18), (0.19, 0.2), sides=6)
    H.frustum(f"foot.{side}", "boot", (kx, 0.03, -0.02), (kx, ANKLE + 0.04, -0.02), (0.18, 0.2), (0.17, 0.18), sides=6)
    H.frustum(f"foot.{side}", "boot", (kx, 0.1, 0.06), (kx, 0.08, 0.42), (0.18, 0.1), (0.15, 0.06), sides=4)
    H.frustum(f"foot.{side}", "sole", (kx, 0.02, -0.18), (kx, 0.02, 0.44), (0.19, 0.02), (0.16, 0.02), sides=4)


def ring(bone, centre, axis, radius):
    """Anel do astrolábio: 8 segmentos num plano; axis = 0 (yz), 1 (xz) ou 2 (xy)."""
    pts = []
    for i in range(9):
        a = 2 * math.pi * i / 8
        c, s = radius * math.cos(a), radius * math.sin(a)
        d = [(0, c, s), (c, 0, s), (c, s, 0)][axis]
        pts.append(tuple(centre[k] + d[k] for k in range(3)))
    H.chain(bone, "gold_lt", pts, [(0.03, 0.03)] * 9, sides=4)


def astrolabe():
    for axis in (0, 1, 2):
        ring("forearm.L", ORB, axis, 0.21)
    H.frustum("forearm.L", "gold", (ORB[0], ORB[1] - 0.07, ORB[2]), (ORB[0], ORB[1] + 0.07, ORB[2]), (0.07, 0.07), (0.07, 0.07), sides=6)


def arm(s, side):
    # manga larga que desce do ombro, punho do casaco, mão clara
    H.frustum(f"arm.{side}", "coat", (s * SH_X, SH_Y + 0.05, 0), (s * EL_X, EL_Y - 0.02, 0), (0.15, 0.16), (0.14, 0.15), sides=6)
    wrist = (s * 0.26, EL_Y - 0.08, 0.46)
    H.frustum(f"forearm.{side}", "coat", (s * EL_X, EL_Y + 0.03, 0), wrist, (0.15, 0.16), (0.14, 0.14), sides=6)
    cuff_a = (s * 0.3, EL_Y - 0.07, 0.34)
    H.frustum(f"forearm.{side}", "coat_dk", cuff_a, (s * 0.26, EL_Y - 0.09, 0.46), (0.15, 0.15), (0.16, 0.16), sides=6)
    H.frustum(f"forearm.{side}", "coat", (s * 0.26, EL_Y - 0.09, 0.44), (s * 0.25, EL_Y - 0.12, 0.62), (0.15, 0.1), (0.13, 0.09), sides=6)


def make():
    head()
    torso()
    coat_skirt()
    leg(1, "L")
    leg(-1, "R")
    arm(1, "L")
    arm(-1, "R")
    astrolabe()


def joints():
    out = {"pelvis": ((0, HIP, ZB), (0, WAIST, ZB)), "spine": ((0, WAIST, ZB), (0, NECK, ZB)),
           "head": ((0, NECK, ZB), (0, TOP, ZB))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, ZB), (s * SH_X, EL_Y, ZB))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, ZB), (s * EL_X, WR_Y, ZB))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, ZB), (s * LEG_X, KNEE, ZB))
        out[f"shin.{side}"] = ((s * 0.18, KNEE, ZB), (s * 0.18, ANKLE, ZB))
        out[f"foot.{side}"] = ((s * 0.18, ANKLE, ZB), (s * 0.18, 0.06, 0.5 + ZB))
    return out


H.build("h00W", "biped", PALETTE, make, joints())
