"""Elemental Of Earth (h034): medido em artifacts/model-sheets/refs/h034/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/h034.py -- <out.glb>

Golem de pedra escura, ombros cinza, antebracos enormes com garras brancas, espinho de pedra nas costas,
placa enferrujada com broca no ombro direito, joia laranja no peito.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "rock": 0x35292A, "rock_lt": 0x6A5F62, "rock_dk": 0x261D1E, "rust": 0x8F4A32, "drill": 0x7A4A38,
    "gem": 0xF08030, "claw": 0xEDEBE2, "slit": 0x0E0B0C,
}

HIP, KNEE, ANKLE, LEG_X = 1.12, 0.62, 0.17, 0.33
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.7, 2.0, 0.86, 1.42, 0.55
ZC = -0.08      # o tronco e jogado para tras: a cabeca sai a frente do peito


def head():
    H.frustum("head", "rock_lt", (0, 1.62, 0.36), (0, 1.9, 0.4), (0.19, 0.2), (0.22, 0.22), sides=6)
    H.frustum("head", "rock_lt", (0, 1.9, 0.4), (0, 2.16, 0.36), (0.22, 0.22), (0.17, 0.18), sides=6)
    H.box("head", "slit", (0, 1.96, 0.62), (0.26, 0.06, 0.04))
    H.frustum("head", "rock", (0, 1.7, 0.1), (0, 2.1, 0.2), (0.3, 0.2), (0.3, 0.24), sides=6)     # pescoco
    H.box("head", "rock", (0, 1.76, 0.62), (0.22, 0.09, 0.05))                                     # queixo


def torso():
    rings = [(1.2, 0.36, 0.28), (1.55, 0.58, 0.38), (1.95, 0.7, 0.42), (2.25, 0.46, 0.34)]
    for (y0, w0, d0), (y1, w1, d1) in zip(rings, rings[1:]):
        H.frustum("spine", "rock", (0, y0, ZC), (0, y1, ZC), (w0, d0), (w1, d1), sides=8)
    H.frustum("spine", "rock_lt", (0, 2.0, ZC), (0, 2.3, ZC), (0.58, 0.4), (0.3, 0.3), sides=8)    # cume dos ombros
    H.frustum("spine", "gem", (0, 1.3, 0.3), (0, 1.62, 0.32), (0.02, 0.01), (0.02, 0.01), sides=4)
    H.box("spine", "gem", (0, 1.46, 0.345), (0.16, 0.34, 0.04))
    # espinho de pedra nas costas e um menor em baixo
    H.frustum("spine", "rock_lt", (0, 1.6, -0.45), (0, 2.7, -0.4), (0.06, 0.2), (0.005, 0.012), sides=4)
    H.frustum("spine", "rock_lt", (0, 1.3, -0.4), (0, 1.9, -0.62), (0.05, 0.14), (0.005, 0.01), sides=4)
    H.frustum("pelvis", "rock_lt", (0, 0.82, 0), (0, 1.3, 0), (0.34, 0.26), (0.42, 0.3), sides=8)


def shoulder_arm(s, side):
    a = f"arm.{side}"
    H.frustum(a, "rock_lt", (s * 0.66, 1.66, 0), (s * 0.7, 2.1, 0), (0.28, 0.3), (0.3, 0.3), sides=6)
    H.frustum(a, "rock_lt", (s * 0.7, 2.1, 0), (s * 0.55, 2.3, 0), (0.3, 0.3), (0.17, 0.18), sides=6)
    H.frustum(a, "rock", (s * 0.75, 1.9, 0), (s * EL_X, EL_Y, 0), (0.22, 0.24), (0.25, 0.26), sides=6)
    if side == "R":     # placa enferrujada com broca
        H.frustum(a, "rust", (-0.38, 1.98, 0), (-0.84, 2.16, 0), (0.09, 0.34), (0.09, 0.34), sides=4)
        H.chain(a, "drill", [(-0.66, 2.1, 0), (-0.7, 2.28, 0), (-0.76, 2.46, 0)], [(0.1, 0.1), (0.07, 0.07), (0.01, 0.01)], sides=6)


def forearm_fist(s, side):
    b, x = f"forearm.{side}", s * 0.88
    H.frustum(b, "rock", (x, EL_Y + 0.05, 0), (x, 1.05, 0.02), (0.27, 0.3), (0.31, 0.34), sides=6)
    H.frustum(b, "rock", (x, 1.05, 0.02), (x, 0.72, 0.05), (0.31, 0.34), (0.28, 0.32), sides=6)
    H.frustum(b, "rock_dk", (x, 0.78, 0.04), (x, 0.36, 0.1), (0.3, 0.34), (0.26, 0.3), sides=6)       # punho
    H.frustum(b, "rock_lt", (s * 0.62, 0.8, 0.24), (s * 0.62, 0.56, 0.4), (0.12, 0.1), (0.1, 0.1), sides=6)     # polegar
    for dz in (-0.12, 0.04, 0.2):       # garras brancas na ponta do punho, para fora e para frente
        H.frustum(b, "claw", (s * 1.1, 0.5, dz), (s * 1.16, 0.22, dz + 0.1), (0.05, 0.05), (0.005, 0.005), sides=4)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * LEG_X
        H.frustum(f"thigh.{side}", "rock_lt", (x, KNEE, 0), (x, HIP + 0.06, 0), (0.2, 0.22), (0.28, 0.27), sides=6)
        H.frustum(f"thigh.{side}", "rock", (x, KNEE - 0.05, 0.02), (x, KNEE + 0.1, 0.02), (0.24, 0.24), (0.2, 0.22), sides=6)
        H.frustum(f"shin.{side}", "rock", (x, ANKLE, 0), (x, KNEE + 0.04, 0), (0.22, 0.24), (0.2, 0.22), sides=6)
        H.box(f"shin.{side}", "rock_lt", (x, KNEE, 0.2), (0.2, 0.18, 0.1))
        H.frustum(f"foot.{side}", "rock_lt", (x, 0.1, -0.1), (x, 0.09, 0.44), (0.26, 0.17), (0.22, 0.1), sides=6)
        H.frustum(f"foot.{side}", "rock_dk", (x, 0.02, -0.14), (x, 0.03, 0.46), (0.27, 0.04), (0.23, 0.04), sides=6)


def make():
    head()
    torso()
    legs()
    for s, side in ((1, "L"), (-1, "R")):
        shoulder_arm(s, side)
        forearm_fist(s, side)


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, 1.3, 0)), "spine": ((0, 1.3, 0), (0, 2.0, 0)), "head": ((0, 2.0, 0.1), (0, 2.3, 0.1))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X + s * 0.02, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("h034", "biped", PALETTE, make, joints())
