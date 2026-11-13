"""Naga Guardian (n002): medido em artifacts/model-sheets/refs/n002/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n002.py -- <out.glb>
"""
import pathlib
import sys

from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "scale": 0x13272B, "scale_lt": 0x1F3A3C, "belly": 0x5AA698, "belly_dk": 0x4A8F82, "olive": 0x6B8456,
    "olive_dk": 0x56703F, "steel": 0x5B8A85, "steel_dk": 0x44706C, "crest": 0xC98A5E, "fin": 0x4F9488,
    "shaft": 0x7D7550, "eye": 0xFFD23C, "black": 0x0C1618,
}

CX = 0.0                        # z da base da coluna


def cz(y):
    """z do eixo do corpo na altura y: a coluna se inclina para trás até o peito (perfil em S)."""
    return -min(max(y - 0.5, 0.0), 1.2) * 0.33

SH_Y, EL_Y, WR_Y = 1.66, 1.10, 0.62
TAIL_Z = [CX, -0.18, -0.38, -0.58, -0.76, -0.9, -1.0]
TAIL_X = [0, 0, 0.0, 0.05, 0.15, 0.3, 0.48]
TAIL_Y = [0.3, 0.28, 0.27, 0.25, 0.21, 0.17, 0.12]
TAIL_R = [0.3, 0.3, 0.28, 0.25, 0.21, 0.15, 0.07]


def tail():
    pts = [(TAIL_X[i], TAIL_Y[i], TAIL_Z[i]) for i in range(7)]
    radii = [(r, r * 0.95) for r in TAIL_R]
    bones = [f"tail.{i}" for i in range(1, 7)]
    H.chain(bones, "scale", pts, radii, sides=8)
    for i in (1, 3, 5):         # anéis de metal
        r = TAIL_R[i] + 0.05
        a, b = pts[i], pts[i + 1]
        mid = tuple(a[k] + (b[k] - a[k]) * 0.45 for k in range(3))
        H.frustum(bones[i], "steel", (mid[0], mid[1], mid[2] + 0.04), (mid[0], mid[1], mid[2] - 0.04), (r, r), (r, r), sides=10)
    tip = pts[6]        # a ponta da cauda vira de lado em duas nadadeiras em foice
    H.frustum("tail.6", "fin", (tip[0] - 0.05, 0.1, tip[2] + 0.1), (tip[0] + 0.38, 0.03, tip[2] - 0.22), (0.05, 0.14), (0.01, 0.01), sides=4)
    H.frustum("tail.6", "scale_lt", (tip[0] - 0.05, 0.1, tip[2] + 0.1), (tip[0] - 0.75, 0.03, tip[2] - 0.2), (0.05, 0.12), (0.01, 0.01), sides=4)


def P(x, y, dz=0.0):
    return (x, y, cz(y) + dz)


def column():
    H.frustum("root", "scale", P(0, 0.3), P(0, 0.72), (0.33, 0.3), (0.3, 0.28), sides=8)
    H.frustum("spine", "scale", P(0, 0.65), P(0, 1.2), (0.3, 0.28), (0.33, 0.3), sides=8)
    for y, tone in ((0.42, "belly"), (0.66, "olive"), (0.9, "belly_dk"), (1.1, "belly")):      # placas do ventre
        H.frustum("root" if y < 0.7 else "spine", tone, P(0, y - 0.11, 0.22), P(0, y + 0.11, 0.22), (0.25, 0.09), (0.28, 0.1), sides=4)


def torso():
    H.frustum("spine", "scale", P(0, 1.15), P(0, 1.72), (0.33, 0.3), (0.42, 0.34), sides=8)
    H.frustum("spine", "olive", P(0, 1.28, 0.15), P(0, 1.76, 0.12), (0.32, 0.2), (0.4, 0.18), sides=6)       # peitoral
    H.frustum("spine", "olive_dk", P(0, 1.6, -0.16), P(0, 1.78, -0.14), (0.42, 0.2), (0.32, 0.16), sides=6)  # placa das costas
    H.frustum("spine", "scale_lt", P(0, 1.2, -0.28), P(0, 1.6, -0.3), (0.26, 0.1), (0.34, 0.1), sides=6)     # escamas das costas
    H.frustum("spine", "scale_lt", P(0, 1.7), P(0, 1.9, 0.08), (0.36, 0.28), (0.22, 0.22), sides=6)          # ombros/pescoço


def head():
    pescoco = [(0, 1.62, cz(1.62)), (0, 1.84, -0.24), (0, 1.94, -0.06)]
    H.chain("head", "scale", pescoco, [(0.25, 0.22), (0.2, 0.19), (0.2, 0.18)], sides=8)
    H.frustum("head", "belly", (0, 1.7, -0.2), (0, 1.88, 0.0), (0.17, 0.08), (0.14, 0.07), sides=6)            # papo
    H.frustum("head", "scale", (0, 1.9, -0.2), (0, 1.93, 0.2), (0.26, 0.2), (0.23, 0.18), sides=8)           # crânio
    H.frustum("head", "scale", (0, 1.88, 0.18), (0, 1.82, 0.5), (0.22, 0.17), (0.12, 0.09), sides=6)          # focinho
    H.frustum("head", "olive", (0, 1.76, 0.1), (0, 1.73, 0.42), (0.13, 0.04), (0.08, 0.03), sides=4)         # mandíbula
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.12, 1.97, 0.2), (0.05, 0.05, 0.06))
    for z, h in ((0.0, 0.38), (-0.1, 0.34), (-0.2, 0.26)):                         # crista laranja
        H.frustum("head", "crest", (0, 2.0, z), (0, 2.0 + h, z - 0.12), (0.025, 0.1), (0.005, 0.02), sides=4)
    H.frustum("head", "fin", (0, 1.98, -0.2), (0, 2.12, -0.46), (0.02, 0.1), (0.01, 0.02), sides=4)


SZ, EZ = -0.3, -0.12            # z do ombro e do cotovelo


def pauldron(side, s):
    H.frustum(f"arm.{side}", "olive", (s * 0.3, 1.86, SZ), (s * 0.6, 1.64, SZ), (0.16, 0.28), (0.22, 0.3), sides=6)
    H.frustum(f"arm.{side}", "olive_dk", (s * 0.56, 1.66, SZ), (s * 0.66, 1.4, SZ + 0.05), (0.22, 0.29), (0.15, 0.24), sides=6)


def trident(base, tip):
    d = (tip - base).normalized()
    sx = (Vector((1, 0, 0)) - d * d.x).normalized()
    head_at = base.lerp(tip, 0.8)
    H.frustum("forearm.R", "shaft", base, head_at, (0.055, 0.055), (0.045, 0.045), sides=6)
    H.frustum("forearm.R", "steel", head_at - d * 0.04, head_at + d * 0.1, (0.09, 0.09), (0.07, 0.07), sides=6)
    H.frustum("forearm.R", "steel_dk", head_at, tip + d * 0.05, (0.05, 0.03), (0.005, 0.005), sides=4)       # ponta central
    bar = head_at + d * 0.1
    for k in (-1, 1):       # dentes laterais com farpa
        a = bar + sx * k * 0.24
        pts = [bar, a, a + d * 0.2 + sx * k * 0.03, a + d * 0.32 - sx * k * 0.08]
        H.chain("forearm.R", "steel_dk", pts, [(0.045, 0.04), (0.04, 0.035), (0.035, 0.03), (0.005, 0.005)], sides=4)


def arm_right():
    s = -1
    pauldron("R", s)
    H.frustum("arm.R", "scale", (s * 0.46, 1.62, SZ), (s * 0.58, EL_Y + 0.02, EZ), (0.18, 0.19), (0.17, 0.18), sides=6)
    H.frustum("forearm.R", "olive", (s * 0.58, EL_Y + 0.06, EZ), (s * 0.64, 1.0, 0.12), (0.21, 0.21), (0.21, 0.21), sides=6)
    H.frustum("forearm.R", "scale", (s * 0.64, 1.04, 0.1), (s * 0.67, 0.9, 0.3), (0.2, 0.2), (0.19, 0.19), sides=6)      # punho grande
    trident(Vector((-0.34, 0.0, -0.25)), Vector((-1.02, 2.1, 0.71)))


def arm_left():
    s = 1
    pauldron("L", s)
    H.frustum("arm.L", "scale", (s * 0.46, 1.62, SZ), (s * 0.6, EL_Y + 0.02, EZ), (0.18, 0.19), (0.17, 0.18), sides=6)
    H.frustum("arm.L", "steel", (s * 0.66, 1.64, SZ), (s * 0.76, 1.64, SZ), (0.17, 0.17), (0.17, 0.17), sides=8)     # disco do ombro
    H.frustum("forearm.L", "olive", (s * 0.6, EL_Y + 0.06, EZ), (s * 0.6, WR_Y + 0.14, EZ + 0.06), (0.21, 0.21), (0.2, 0.2), sides=6)
    H.frustum("forearm.L", "scale", (s * 0.6, WR_Y + 0.18, EZ + 0.06), (s * 0.6, WR_Y - 0.14, EZ + 0.1), (0.21, 0.21), (0.18, 0.18), sides=6)   # punho
    H.frustum("forearm.L", "steel", (s * 0.72, 0.86, -0.34), (s * 0.82, 0.86, -0.34), (0.36, 0.36), (0.36, 0.36), sides=10)      # escudo redondo
    H.frustum("forearm.L", "steel_dk", (s * 0.82, 0.86, -0.34), (s * 0.88, 0.86, -0.34), (0.12, 0.12), (0.08, 0.08), sides=8)    # umbo


def make():
    tail()
    column()
    torso()
    head()
    arm_right()
    arm_left()


def joints():
    out = {"spine": ((0, 0.55, cz(0.55)), (0, 1.62, cz(1.62))), "head": ((0, 1.7, cz(1.7)), (0, 2.1, -0.05)),
           "tail.1": ((0, 0.28, CX), (TAIL_X[1], 0.26, TAIL_Z[1]))}
    for i in range(2, 7):
        out[f"tail.{i}"] = ((TAIL_X[i - 1], TAIL_Y[i - 1], TAIL_Z[i - 1]), (TAIL_X[i], TAIL_Y[i], TAIL_Z[i]))
    for s, side in ((1, "L"), (-1, "R")):
        x_sh, x_el = s * 0.48, s * (0.6 if s > 0 else 0.58)
        out[f"arm.{side}"] = ((x_sh, 1.66, SZ), (x_el, EL_Y, EZ))
        out[f"forearm.{side}"] = ((x_el, EL_Y, EZ), (x_el, WR_Y, EZ + 0.1))
    return out


H.build("n002", "naga", PALETTE, make, joints())
