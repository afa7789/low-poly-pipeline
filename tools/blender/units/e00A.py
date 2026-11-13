"""Avatar of Vengeance (e00A): medido em artifacts/model-sheets/refs/e00A/sheet.jpg (familia wraith).

    blender -b --factory-startup -P tools/blender/units/e00A.py -- <out.glb>

Escala da prancha: 0.00208 m por pixel (elmo a 2.42 m, base de fumaca a 0); frente = direita no perfil.
Duas laminas em crescente, uma por mao: a da esquerda (x +) curva pra frente, a da direita (x -) pra tras.
As pernas e a fumaca sao do corpo (wraith nao tem pernas): a figura paira na nuvem.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "armor": 0x1C1A24, "skin": 0x3A3646, "trim": 0x8E9099, "hair": 0x15301F, "eye": 0x6BFF2A,
    "gold": 0xB58A3C, "smoke": 0x4A4850, "smoke_dk": 0x302F37, "smoke_lt": 0x6A6A72, "blade": 0xA3A9AF,
    "cloth": 0x2C2A38,
}


def smoke():
    """Nuvem escura em que a figura paira: pufes sobrepostos de tres tons."""
    puffs = [((0, 0.0, 0.0), 0.62, 0.34), ((0.35, 0.05, 0.15), 0.4, 0.46), ((-0.35, 0.05, -0.1), 0.4, 0.44),
             ((0.0, 0.1, -0.3), 0.4, 0.5), ((0.1, 0.12, 0.35), 0.38, 0.42), ((-0.2, 0.1, 0.3), 0.32, 0.4)]
    for i, ((x, y, z), r, h) in enumerate(puffs):
        tone = ("smoke_dk", "smoke", "smoke_dk")[i % 3]
        H.frustum("root", tone, (x, y, z), (x, y + h, z), (r, r * 0.9), (r * 0.7, r * 0.65), sides=8)
    H.frustum("root", "smoke_lt", (0, 0.4, 0), (0, 0.6, 0), (0.6, 0.55), (0.4, 0.38), sides=8)


def legs():
    """Coxas largas no quadril, joelheira prata, botas que alargam no cano; somem na fumaca."""
    for s in (-1, 1):
        H.frustum("base", "armor", (s * 0.1, 1.28, 0.0), (s * 0.12, 0.98, 0.02), (0.17, 0.17), (0.14, 0.15), sides=6)
        H.frustum("base", "armor", (s * 0.12, 1.0, 0.02), (s * 0.12, 0.72, 0.03), (0.14, 0.15), (0.12, 0.13), sides=6)
        H.frustum("base", "trim", (s * 0.12, 0.84, 0.08), (s * 0.12, 0.7, 0.1), (0.07, 0.04), (0.06, 0.03), sides=4)
        H.frustum("base", "armor", (s * 0.12, 0.74, 0.03), (s * 0.12, 0.4, 0.04), (0.12, 0.13), (0.15, 0.15), sides=6)
        H.frustum("base", "trim", (s * 0.12, 0.72, 0.03), (s * 0.12, 0.66, 0.03), (0.155, 0.155), (0.155, 0.155), sides=6)


def hips():
    H.frustum("base", "cloth", (0, 1.34, 0.0), (0, 1.24, 0.0), (0.2, 0.14), (0.24, 0.16), sides=6)
    H.frustum("base", "armor", (0, 1.3, 0.12), (0, 1.0, 0.14), (0.1, 0.03), (0.02, 0.03), sides=4)
    H.frustum("base", "trim", (0, 1.3, 0.14), (0, 1.1, 0.15), (0.12, 0.02), (0.03, 0.02), sides=4)


def torso():
    """Cintura fina, peito em V com bustiê, cinto com losango dourado."""
    H.frustum("spine", "armor", (0, 1.22, 0.0), (0, 1.5, 0.0), (0.21, 0.17), (0.17, 0.15), sides=6)
    H.frustum("spine", "armor", (0, 1.46, 0.0), (0, 1.74, 0.0), (0.17, 0.15), (0.28, 0.2), sides=8)
    H.frustum("spine", "armor", (0, 1.7, 0.0), (0, 1.92, 0.0), (0.28, 0.2), (0.22, 0.16), sides=8)
    H.frustum("spine", "trim", (0, 1.42, 0.0), (0, 1.5, 0.0), (0.2, 0.17), (0.19, 0.17), sides=6)
    H.frustum("spine", "gold", (0, 1.4, 0.13), (0, 1.5, 0.14), (0.03, 0.02), (0.07, 0.02), sides=4)
    H.frustum("spine", "trim", (0, 1.6, 0.1), (0, 1.78, 0.13), (0.1, 0.03), (0.15, 0.03), sides=4)


def hair():
    """Cabelo verde comprido, desce pelas costas ate a coxa."""
    H.frustum("spine", "hair", (0, 2.05, -0.12), (0, 1.5, -0.17), (0.2, 0.06), (0.24, 0.07), sides=6)
    H.frustum("spine", "hair", (0, 1.55, -0.17), (0, 1.05, -0.16), (0.24, 0.07), (0.22, 0.06), sides=6)
    H.frustum("spine", "hair", (0, 1.1, -0.16), (0, 0.78, -0.15), (0.18, 0.05), (0.04, 0.02), sides=6)


def head():
    H.frustum("head", "skin", (0, 1.88, 0.0), (0, 2.02, 0.0), (0.07, 0.07), (0.1, 0.1), sides=6)
    H.frustum("head", "armor", (0, 2.0, 0.0), (0, 2.26, 0.0), (0.14, 0.16), (0.16, 0.18), sides=8)
    H.frustum("head", "armor", (0, 2.24, 0.0), (0, 2.42, -0.01), (0.16, 0.18), (0.09, 0.12), sides=8)
    H.frustum("head", "skin", (0, 2.02, 0.12), (0, 2.22, 0.12), (0.09, 0.05), (0.1, 0.05), sides=6)
    H.frustum("head", "trim", (0, 2.2, 0.15), (0, 2.34, 0.15), (0.1, 0.03), (0.08, 0.03), sides=4)
    H.frustum("head", "eye", (0, 2.27, 0.17), (0, 2.34, 0.17), (0.02, 0.02), (0.035, 0.02), sides=4)
    for s in (-1, 1):
        H.frustum("head", "eye", (s * 0.06, 2.15, 0.16), (s * 0.06, 2.18, 0.16), (0.04, 0.02), (0.04, 0.02), sides=4)
        H.frustum("head", "skin", (s * 0.12, 2.15, 0.0), (s * 0.3, 2.22, -0.02), (0.03, 0.05), (0.005, 0.01), sides=4)


def pauldron(s, arm):
    H.frustum(arm, "armor", (s * 0.18, 1.8, 0.0), (s * 0.27, 2.0, 0.0), (0.2, 0.18), (0.14, 0.14), sides=6)
    H.frustum(arm, "trim", (s * 0.2, 1.8, 0.0), (s * 0.26, 1.84, 0.0), (0.22, 0.2), (0.22, 0.2), sides=6)
    H.frustum(arm, "trim", (s * 0.28, 1.96, 0.0), (s * 0.52, 2.1, 0.0), (0.07, 0.06), (0.005, 0.005), sides=6)


def arms():
    """Bracos finos mas cheios no biceps, braçadeira prateada em crescente, punho escuro."""
    for s, side in ((1, "L"), (-1, "R")):
        arm, fore = f"arm.{side}", f"forearm.{side}"
        pauldron(s, arm)
        H.frustum(arm, "skin", (s * 0.2, 1.84, 0.0), (s * 0.28, 1.62, 0.0), (0.12, 0.12), (0.13, 0.125), sides=6)
        H.frustum(arm, "skin", (s * 0.28, 1.64, 0.0), (s * 0.32, 1.42, 0.02), (0.13, 0.125), (0.1, 0.1), sides=6)
        H.frustum(fore, "armor", (s * 0.32, 1.44, 0.02), (s * 0.34, 1.28, 0.04), (0.11, 0.11), (0.14, 0.13), sides=6)
        H.frustum(fore, "trim", (s * 0.4, 1.44, 0.06), (s * 0.4, 1.28, 0.08), (0.025, 0.07), (0.03, 0.08), sides=4)
        H.frustum(fore, "armor", (s * 0.34, 1.3, 0.04), (s * 0.4, 1.12, 0.07), (0.13, 0.125), (0.13, 0.13), sides=6)
        H.frustum(fore, "skin", (s * 0.4, 1.16, 0.07), (s * 0.41, 1.04, 0.1), (0.105, 0.1), (0.085, 0.085), sides=6)
        H.frustum(fore, "smoke_lt", (s * 0.52, 1.28, 0.05), (s * 0.5, 1.02, 0.06), (0.08, 0.07), (0.03, 0.03), sides=6)


def crescent(bone, s, x, scale=1.0):
    """Lamina em crescente no plano y-z: sai da mao, desce e sobe de novo; s = +1 pra frente, -1 pra tras."""
    cz, cy, az, by = 0.5 * scale, 1.28, 0.4 * scale, 0.46 * scale
    angles = [math.pi + i * math.pi / 7 for i in range(8)]
    pts = [(x, cy + by * math.sin(t), s * (cz + az * math.cos(t))) for t in angles]
    pts[0], pts[-1] = (x, 1.2, s * 0.1), (x, 1.36, s * 0.95 * scale)
    widths = [0.012, 0.05, 0.08, 0.1, 0.1, 0.08, 0.05, 0.012]
    H.chain(bone, "blade", pts, [(0.035, w) for w in widths], sides=4)
    H.frustum(bone, "armor", (x, 1.28, s * 0.14), (x, 1.12, s * 0.12), (0.04, 0.04), (0.04, 0.04), sides=6)


def make():
    smoke()
    legs()
    hips()
    torso()
    hair()
    head()
    arms()
    crescent("forearm.L", 1, 0.41)
    crescent("forearm.R", -1, -0.41)


def joints():
    out = {}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * 0.2, 1.86, 0.0), (s * 0.2, 1.44, 0.0))
        out[f"forearm.{side}"] = ((s * 0.32, 1.44, 0.02), (s * 0.32, 1.0, 0.02))
    return out


H.build("e00A", "wraith", PALETTE, make, joints())
