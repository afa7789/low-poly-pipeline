"""Echofoot Mystic (n03I): medido em artifacts/model-sheets/refs/n03I/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n03I.py -- <out.glb>
"""
import math
import pathlib
import sys

from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "cream": 0xEEE6D2, "brown": 0x5A3A2C, "nose": 0x2A2224, "goggle": 0x3A2E2A, "lens": 0x30E8F0,
    "coat": 0x1F2E6E, "coat_dk": 0x18255A, "collar": 0x4AA0E0, "robe": 0x4A2E26, "boot": 0xC9A870, "boot_dk": 0xA88A58,
    "glove": 0x4A3A34, "fan": 0x8A8A8E, "fan_dk": 0x6E6E74, "fan_rib": 0x3A3A40,
    "pot": 0xC5503E, "pot_dk": 0x9A3A2E,
}

HIP, WAIST, NECK, TOP = 0.85, 1.35, 1.95, 2.6
KNEE, ANKLE, LEG_X = 0.55, 0.16, 0.22
HEM = 0.7


def hem(p):
    """A barra do casaco acompanha a coxa do seu lado; o topo fica na pelve."""
    if p[1] > (HEM + 0.95) / 2:
        return {"pelvis": 1.0}
    return {"pelvis": 0.45, "thigh.L" if p[0] > 0 else "thigh.R": 0.55}


def head():
    H.frustum("head", "collar", (0, 1.9, 0), (0, 2.1, 0), (0.32, 0.3), (0.36, 0.34), sides=8)           # gola azul alta
    H.frustum("head", "collar", (0, 2.1, 0), (0, 2.3, 0), (0.36, 0.34), (0.38, 0.35), sides=8)
    H.frustum("head", "cream", (0, 2.14, 0.0), (0, 2.42, 0.0), (0.22, 0.22), (0.27, 0.27), sides=8)
    H.frustum("head", "cream", (0, 2.42, 0.0), (0, 2.6, 0.0), (0.27, 0.27), (0.2, 0.2), sides=8)
    H.frustum("head", "cream", (0, 2.3, 0.18), (0, 2.28, 0.4), (0.15, 0.12), (0.1, 0.08), sides=6)      # focinho
    H.box("head", "nose", (0, 2.32, 0.42), (0.09, 0.06, 0.05))
    H.frustum("head", "goggle", (0, 2.38, 0.0), (0, 2.5, 0.0), (0.285, 0.285), (0.285, 0.285), sides=8)  # tira dos óculos
    for s in (-1, 1):
        H.box("head", "goggle", (s * 0.11, 2.45, 0.27), (0.18, 0.17, 0.07))
        H.box("head", "lens", (s * 0.11, 2.45, 0.31), (0.13, 0.12, 0.03))
        H.box("head", "brown", (s * 0.13, 2.28, 0.25), (0.12, 0.08, 0.06))
        H.frustum("head", "brown", (s * 0.22, 2.54, -0.02), (s * 0.27, 2.68, -0.02), (0.13, 0.1), (0.1, 0.08), sides=6)


def torso():
    H.frustum("pelvis", "coat", (0, 0.95, 0), (0, WAIST, 0), (0.46, 0.35), (0.42, 0.32), sides=8)
    H.soft(H.frustum("pelvis", "coat", (0, HEM, 0), (0, 0.95, 0), (0.5, 0.4), (0.46, 0.35), sides=8), hem)
    H.frustum("spine", "coat", (0, WAIST - 0.03, 0), (0, 1.8, 0), (0.42, 0.32), (0.44, 0.31), sides=8)
    H.frustum("spine", "coat", (0, 1.8, 0), (0, 2.0, 0), (0.44, 0.31), (0.3, 0.26), sides=8)             # ombros em V


def legs(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "robe", (x, 0.36, 0), (x, HIP + 0.04, 0), (0.3, 0.3), (0.35, 0.34), sides=6)
    H.frustum(f"shin.{side}", "robe", (x, 0.34, 0), (x, KNEE + 0.04, 0), (0.3, 0.3), (0.3, 0.3), sides=6)
    H.frustum(f"shin.{side}", "boot", (x, 0.04, 0), (x, 0.2, 0), (0.18, 0.2), (0.17, 0.19), sides=6)       # bota alargada
    H.frustum(f"shin.{side}", "boot", (x, 0.2, 0), (x, 0.42, 0), (0.17, 0.19), (0.23, 0.23), sides=6)
    H.frustum(f"foot.{side}", "boot_dk", (x, 0.1, 0.04), (x, 0.08, 0.42), (0.19, 0.12), (0.17, 0.09), sides=4)


def arm_left():
    H.frustum("arm.L", "coat", (0.34, 1.95, 0), (0.58, 1.55, 0.05), (0.2, 0.2), (0.19, 0.19), sides=6)
    H.frustum("forearm.L", "coat", (0.56, 1.58, 0.05), (0.68, 1.3, 0.1), (0.2, 0.2), (0.17, 0.17), sides=6)
    H.frustum("forearm.L", "glove", (0.67, 1.32, 0.1), (0.68, 1.2, 0.12), (0.17, 0.17), (0.2, 0.2), sides=6)
    H.frustum("forearm.L", "glove", (0.68, 1.2, 0.12), (0.66, 1.06, 0.12), (0.2, 0.2), (0.14, 0.14), sides=6)


def fan():
    pivot, u, v = Vector((0.66, 1.2, 0.12)), Vector((1, 0, 0.15)).normalized(), Vector((0, -0.9, 0.45)).normalized()
    radius, a0, n, span = 0.66, math.radians(-20), 7, math.radians(125) / 7

    def arc(a, r=radius):
        return tuple(pivot + r * (math.cos(a) * u + math.sin(a) * v))
    for i in range(n):
        a = a0 + i * span
        H.panel("forearm.L", "fan" if i % 2 else "fan_dk", [tuple(pivot), arc(a), arc(a + span / 2, radius * 1.03), arc(a + span)], 0.04)
    H.frustum("forearm.L", "fan_rib", tuple(pivot - u * 0.06), tuple(pivot + u * 0.2 + v * 0.1), (0.05, 0.05), (0.04, 0.04), sides=6)


def arm_right():
    H.frustum("arm.R", "coat", (-0.34, 1.95, 0), (-0.58, 1.55, 0.08), (0.2, 0.2), (0.19, 0.19), sides=6)
    H.frustum("forearm.R", "coat", (-0.56, 1.58, 0.08), (-0.72, 1.3, 0.18), (0.2, 0.2), (0.17, 0.17), sides=6)
    H.frustum("forearm.R", "glove", (-0.72, 1.32, 0.18), (-0.74, 1.22, 0.2), (0.17, 0.17), (0.2, 0.2), sides=6)
    H.frustum("forearm.R", "glove", (-0.74, 1.22, 0.2), (-0.74, 1.1, 0.2), (0.2, 0.2), (0.14, 0.14), sides=6)


def teapot():
    b, x, z = "forearm.R", -0.74, 0.22
    H.frustum(b, "pot", (x, 0.5, z), (x, 0.72, z), (0.16, 0.16), (0.26, 0.26), sides=8)
    H.frustum(b, "pot", (x, 0.72, z), (x, 0.92, z), (0.26, 0.26), (0.16, 0.16), sides=8)
    H.frustum(b, "pot_dk", (x, 0.92, z), (x, 1.0, z), (0.12, 0.12), (0.07, 0.07), sides=6)              # tampa
    H.chain(b, "pot", [(x - 0.14, 0.64, z + 0.06), (x - 0.3, 0.72, z + 0.18), (x - 0.42, 0.88, z + 0.3)],
            [(0.1, 0.1), (0.07, 0.07), (0.04, 0.04)])                                                 # bico
    H.chain(b, "pot", [(x - 0.14, 0.93, z), (x - 0.12, 1.1, z), (x, 1.16, z), (x + 0.12, 1.1, z), (x + 0.14, 0.93, z)],
            [(0.04, 0.04)] * 5)                                                                       # alça


def make():
    head()
    torso()
    arm_left()
    arm_right()
    for s, side in ((1, "L"), (-1, "R")):
        legs(s, side)
    fan()
    teapot()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0)),
           "arm.L": ((0.4, 1.95, 0), (0.58, 1.55, 0.05)), "forearm.L": ((0.58, 1.55, 0.05), (0.68, 1.15, 0.12)),
           "arm.R": ((-0.4, 1.95, 0), (-0.58, 1.55, 0.08)), "forearm.R": ((-0.58, 1.55, 0.08), (-0.74, 1.15, 0.2))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0.0), (s * LEG_X, 0.06, 0.45))
    return out


H.build("n03I", "biped", PALETTE, make, joints())
