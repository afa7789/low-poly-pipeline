"""Avenging Spirit (e00B): medido em artifacts/model-sheets/refs/e00B/sheet.jpg (familia wraith).

    blender -b --factory-startup -P tools/blender/units/e00B.py -- <out.glb>

Escala da prancha: 0.00212 m por pixel (elmo a 2.42 m, botas no chao a 0); frente = direita no perfil.
Duas laminas em crescente, uma por mao: a da esquerda (x +) curva pra frente, a da direita (x -) pra tras.
As pernas sao pecas do corpo (wraith nao tem pernas); chamas roxas nas costas.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "armor": 0x2E1A3E, "skin": 0x6E4E8F, "trim": 0xB9B8C4, "hair": 0x17201F, "eye": 0xFFFFFF,
    "gold": 0xB58A3C, "helm": 0x2F7C7A, "blade": 0xC9C8D6, "cloth": 0x7C7B86, "paul": 0x4B3A52,
    "cuff": 0x3A2450, "flame": 0x8F5FB8, "gem": 0x3C9BF0, "boot": 0x38223F,
}


def flames():
    """Chamas roxas atras dos ombros e dos bracos: tres linguas finas e curvas de cada lado."""
    for s, x, y0, h in ((1, 0.4, 1.6, 0.7), (-1, 0.4, 1.6, 0.7), (1, 0.55, 1.0, 0.4), (-1, 0.55, 1.0, 0.4)):
        pts = [(s * x, y0, -0.12), (s * (x + 0.05), y0 + h * 0.5, -0.14), (s * (x - 0.02), y0 + h, -0.12)]
        H.chain("spine", "flame", pts, [(0.035, 0.025), (0.03, 0.022), (0.005, 0.005)], sides=4)


def legs():
    """Coxas largas no quadril, botas altas roxas ate o chao com borda prata no joelho e no topo da coxa."""
    for s in (-1, 1):
        H.frustum("base", "skin", (s * 0.12, 1.26, 0.0), (s * 0.13, 0.98, 0.02), (0.17, 0.17), (0.15, 0.15), sides=6)
        H.frustum("base", "trim", (s * 0.13, 0.98, 0.02), (s * 0.13, 0.92, 0.02), (0.16, 0.16), (0.16, 0.16), sides=6)
        H.frustum("base", "boot", (s * 0.13, 0.96, 0.02), (s * 0.13, 0.6, 0.03), (0.15, 0.15), (0.12, 0.13), sides=6)
        H.frustum("base", "boot", (s * 0.13, 0.62, 0.03), (s * 0.13, 0.12, 0.04), (0.12, 0.13), (0.15, 0.16), sides=6)
        H.frustum("base", "boot", (s * 0.13, 0.14, 0.04), (s * 0.13, 0.0, 0.12), (0.15, 0.16), (0.15, 0.2), sides=6)


def hips():
    H.frustum("base", "cloth", (0, 1.34, 0.0), (0, 1.24, 0.0), (0.2, 0.14), (0.24, 0.16), sides=6)
    H.frustum("base", "cloth", (0, 1.28, 0.14), (0, 0.9, 0.17), (0.16, 0.03), (0.03, 0.03), sides=4)


def torso():
    """Cintura fina, peito em V com bustiê, cinto com losango dourado."""
    H.frustum("spine", "armor", (0, 1.22, 0.0), (0, 1.5, 0.0), (0.21, 0.17), (0.17, 0.15), sides=6)
    H.frustum("spine", "armor", (0, 1.46, 0.0), (0, 1.74, 0.0), (0.17, 0.15), (0.28, 0.2), sides=8)
    H.frustum("spine", "armor", (0, 1.7, 0.0), (0, 1.92, 0.0), (0.28, 0.2), (0.22, 0.16), sides=8)
    H.frustum("spine", "trim", (0, 1.42, 0.0), (0, 1.5, 0.0), (0.2, 0.17), (0.19, 0.17), sides=6)
    H.frustum("spine", "gold", (0, 1.4, 0.15), (0, 1.47, 0.15), (0.2, 0.05), (0.2, 0.05), sides=4)
    H.frustum("spine", "trim", (0, 1.6, 0.1), (0, 1.78, 0.13), (0.1, 0.03), (0.15, 0.03), sides=4)


def hair():
    """Cabelo verde comprido, desce pelas costas ate a coxa."""
    H.frustum("spine", "hair", (0, 2.05, -0.12), (0, 1.5, -0.17), (0.2, 0.06), (0.24, 0.07), sides=6)
    H.frustum("spine", "hair", (0, 1.55, -0.17), (0, 1.05, -0.16), (0.24, 0.07), (0.22, 0.06), sides=6)
    H.frustum("spine", "hair", (0, 1.1, -0.16), (0, 0.78, -0.15), (0.18, 0.05), (0.04, 0.02), sides=6)


def head():
    H.frustum("head", "skin", (0, 1.88, 0.0), (0, 2.02, 0.0), (0.07, 0.07), (0.1, 0.1), sides=6)
    H.frustum("head", "helm", (0, 2.0, 0.0), (0, 2.26, 0.0), (0.14, 0.16), (0.16, 0.18), sides=8)
    H.frustum("head", "helm", (0, 2.24, 0.0), (0, 2.42, -0.01), (0.16, 0.18), (0.09, 0.12), sides=8)
    H.frustum("head", "skin", (0, 2.02, 0.12), (0, 2.22, 0.12), (0.09, 0.05), (0.1, 0.05), sides=6)
    H.frustum("head", "trim", (0, 2.2, 0.15), (0, 2.34, 0.15), (0.1, 0.03), (0.08, 0.03), sides=4)
    H.frustum("head", "gem", (0, 2.27, 0.17), (0, 2.34, 0.17), (0.02, 0.02), (0.035, 0.02), sides=4)
    for s in (-1, 1):
        H.frustum("head", "eye", (s * 0.06, 2.15, 0.16), (s * 0.06, 2.18, 0.16), (0.04, 0.02), (0.04, 0.02), sides=4)
        H.frustum("head", "skin", (s * 0.12, 2.15, 0.0), (s * 0.3, 2.22, -0.02), (0.03, 0.05), (0.005, 0.01), sides=4)


def pauldron(s, arm):
    H.frustum(arm, "paul", (s * 0.18, 1.8, 0.0), (s * 0.27, 2.0, 0.0), (0.2, 0.18), (0.14, 0.14), sides=6)
    H.frustum(arm, "trim", (s * 0.2, 1.8, 0.0), (s * 0.26, 1.84, 0.0), (0.22, 0.2), (0.22, 0.2), sides=6)
    H.frustum(arm, "trim", (s * 0.28, 1.96, 0.0), (s * 0.52, 2.1, 0.0), (0.07, 0.06), (0.005, 0.005), sides=6)


def arms():
    """Bracos finos mas cheios no biceps, braçadeira prateada em crescente, punho escuro."""
    for s, side in ((1, "L"), (-1, "R")):
        arm, fore = f"arm.{side}", f"forearm.{side}"
        pauldron(s, arm)
        H.frustum(arm, "skin", (s * 0.2, 1.84, 0.0), (s * 0.28, 1.62, 0.0), (0.12, 0.12), (0.13, 0.125), sides=6)
        H.frustum(arm, "skin", (s * 0.28, 1.64, 0.0), (s * 0.32, 1.42, 0.02), (0.13, 0.125), (0.1, 0.1), sides=6)
        H.frustum(fore, "cuff", (s * 0.32, 1.44, 0.02), (s * 0.34, 1.28, 0.04), (0.11, 0.11), (0.14, 0.13), sides=6)
        H.frustum(fore, "cuff", (s * 0.34, 1.3, 0.04), (s * 0.4, 1.12, 0.07), (0.13, 0.125), (0.13, 0.13), sides=6)
        H.frustum(fore, "skin", (s * 0.4, 1.16, 0.07), (s * 0.41, 1.04, 0.1), (0.105, 0.1), (0.085, 0.085), sides=6)


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
    flames()
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


H.build("e00B", "wraith", PALETTE, make, joints())
