"""Gemeo chorao (n02K): a segunda figura da prancha dos Gemeos, a gorda de capuz e mascara chorosa que segura
uma roda de valvula (artifacts/model-sheets/refs/e00E-b/sheet.jpg, frente: 0.005 m por pixel). Par da e00E.

    blender -b --factory-startup -P tools/blender/units/n02K.py -- <out.glb>
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "suit": 0x1F1B1D, "suit_dk": 0x151214, "suit_lt": 0x2C2629, "mask": 0xEDE3CF, "rim": 0xB06A55, "brow": 0x2A2020,
    "iron": 0x6A6468, "iron_dk": 0x2F2A2C, "sole": 0x100E0F,
}

HIP, KNEE, ANKLE = 0.7, 0.4, 0.1
WAIST, NECK, TOP = 1.1, 1.95, 2.7
SH_X, SH_Y = 0.66, 1.95
EL_X, EL_Y = 0.84, 1.3
WRIST_L = (0.8, 0.6, 0.04)
WRIST_R = (-0.76, 0.88, 0.06)
WHEEL_C, WHEEL_R = (-0.76, 0.62, 0.1), 0.3
LEG_TOP, LEG_BOT = 0.26, 0.4          # as pernas abrem para baixo, como na folha


def stack(bone, color, pts, sides=8):
    """Pilha de troncos de cone sobrepostos: pts = [(x, y, z, rx, rz), ...]."""
    for a, b in zip(pts, pts[1:]):
        H.frustum(bone, color, a[:3], b[:3], a[3:], b[3:], sides=sides)


def head():
    stack("head", "suit", [(0, 1.9, -0.02, 0.24, 0.2), (0, 2.1, -0.03, 0.35, 0.26), (0, 2.45, -0.04, 0.38, 0.27), (0, 2.7, -0.05, 0.2, 0.2)])
    stack("head", "rim", [(0, 1.88, 0.15, 0.17, 0.06), (0, 2.12, 0.18, 0.34, 0.07), (0, 2.46, 0.18, 0.37, 0.07), (0, 2.7, 0.13, 0.22, 0.06)])
    stack("head", "mask", [(0, 1.9, 0.19, 0.14, 0.06), (0, 2.12, 0.22, 0.3, 0.07), (0, 2.46, 0.22, 0.33, 0.07), (0, 2.68, 0.16, 0.19, 0.06)])
    for s in (-1, 1):
        H.box("head", "brow", (s * 0.15, 2.42, 0.3), (0.14, 0.04, 0.03))        # olhos caidos
        H.box("head", "brow", (s * 0.12, 2.2, 0.3), (0.06, 0.34, 0.03))           # lagrimas
        H.box("head", "brow", (s * 0.09, 2.0, 0.3), (0.08, 0.05, 0.03))           # cantos da boca
    H.box("head", "brow", (0, 2.06, 0.3), (0.16, 0.05, 0.03))                     # boca triste


def torso():
    stack("pelvis", "suit", [(0, 0.62, 0, 0.42, 0.3), (0, 0.9, 0, 0.56, 0.38), (0, 1.12, 0, 0.62, 0.42)])
    stack("spine", "suit", [(0, 1.1, 0, 0.62, 0.42), (0, 1.4, 0.02, 0.68, 0.44), (0, 1.7, 0, 0.64, 0.4), (0, 2.0, 0, 0.56, 0.3), (0, 2.14, 0, 0.28, 0.24)])
    stack("spine", "suit_lt", [(0, 1.96, -0.1, 0.4, 0.22), (0, 2.1, -0.1, 0.22, 0.2)])      # capuz sobre os ombros


def leg(s, side):
    xt, xk, xa = s * LEG_TOP, s * 0.33, s * LEG_BOT
    stack(f"thigh.{side}", "suit", [(xk, KNEE - 0.04, 0, 0.17, 0.18), (s * 0.3, 0.55, 0, 0.2, 0.21), (xt, HIP + 0.1, 0, 0.23, 0.24)], 6)
    stack(f"shin.{side}", "suit", [(xa, ANKLE, 0, 0.13, 0.14), (s * 0.37, 0.25, 0, 0.15, 0.16), (xk, KNEE + 0.02, 0, 0.17, 0.18)], 6)
    stack(f"foot.{side}", "suit_dk", [(xa, 0.18, -0.02, 0.15, 0.15), (xa, 0.06, 0.1, 0.17, 0.18), (xa, 0.04, 0.34, 0.13, 0.09)], 6)
    H.frustum(f"foot.{side}", "sole", (xa, 0.015, -0.1), (xa, 0.015, 0.4), (0.17, 0.02), (0.13, 0.02), sides=4)


def hand_arm(s, side, wrist):
    wx, wy, wz = wrist
    stack(f"arm.{side}", "suit", [(s * 0.64, SH_Y + 0.1, 0, 0.24, 0.24), (s * 0.78, 1.65, 0, 0.21, 0.21), (s * EL_X, EL_Y + 0.02, 0, 0.17, 0.17)], 6)
    stack(f"forearm.{side}", "suit", [(s * EL_X, EL_Y, 0, 0.17, 0.17), (s * 0.82, 1.0, 0.02, 0.19, 0.18), (wx, wy + 0.04, wz, 0.15, 0.15)], 6)
    stack(f"forearm.{side}", "suit_lt", [(wx, wy + 0.04, wz, 0.15, 0.15), (wx, wy - 0.06, wz + 0.02, 0.19, 0.15), (wx, wy - 0.2, wz + 0.03, 0.12, 0.1)], 6)


def valve_wheel():
    cx, cy, cz = WHEEL_C
    H.frustum("forearm.R", "iron", (cx, cy, cz - 0.05), (cx, cy, cz + 0.05), (WHEEL_R, WHEEL_R), (WHEEL_R, WHEEL_R), sides=12)
    H.frustum("forearm.R", "iron_dk", (cx, cy, cz + 0.04), (cx, cy, cz + 0.07), (0.22, 0.22), (0.22, 0.22), sides=12)
    H.frustum("forearm.R", "iron", (cx, cy, cz + 0.06), (cx, cy, cz + 0.1), (0.09, 0.09), (0.09, 0.09), sides=8)
    for i in range(5):
        a = i * 2 * math.pi / 5 + 0.3
        tip = (cx + 0.26 * math.cos(a), cy + 0.26 * math.sin(a), cz + 0.08)
        H.frustum("forearm.R", "iron", (cx, cy, cz + 0.09), tip, (0.045, 0.045), (0.06, 0.06), sides=4)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    hand_arm(1, "L", WRIST_L)
    hand_arm(-1, "R", WRIST_R)
    valve_wheel()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side, wrist in ((1, "L", WRIST_L), (-1, "R", WRIST_R)):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), wrist)
        out[f"thigh.{side}"] = ((s * LEG_TOP, HIP, 0), (s * 0.33, KNEE, 0))
        out[f"shin.{side}"] = ((s * 0.33, KNEE, 0), (s * LEG_BOT, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_BOT, ANKLE, 0), (s * LEG_BOT, 0.05, 0.4))
    return out


H.build("n02K", "biped", PALETTE, make, joints())
