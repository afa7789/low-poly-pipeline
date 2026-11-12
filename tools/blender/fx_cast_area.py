"""Efeito 3D do CastArea (SkillFxKind::CastArea): círculo arcano no chão, cristais, pilar de luz e onda.

    blender -b --python tools/blender/fx_cast_area.py

Grava assets/fx3d/cast_area.glb. Desenhado para raio 2,5 (o motor escala pelo raio do evento). Roxo arcano:
o hexagrama gira devagar no chão, os cristais saem em volta e o pilar marca o centro do impacto.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # o Blender não põe a pasta do script no caminho
from fx_rig import TINY, Fx, annulus, rgb

R = 2.5


def build():
    fx = Fx("cast_area")
    fx.begin("sigil", head=(0, 0, 0.06))  # hexagrama de traços: dois triângulos, um girado 60 graus
    for tri in range(2):
        pts = [(math.cos(tri * math.pi / 3 + i * 2 * math.pi / 3 + math.pi / 6) * R * 0.88,
                math.sin(tri * math.pi / 3 + i * 2 * math.pi / 3 + math.pi / 6) * R * 0.88) for i in range(3)]
        for p0, p1 in zip(pts, pts[1:] + pts[:1]):
            fx.bar(p0, p1, 0.16, 0.06, rgb(0.62, 0.32, 0.95), rgb(0.9, 0.75, 1.0), z=0.04 + 0.03 * tri)
    fx.anim("sigil", [(0, 0.3, 1, 0), (0.15, 1.0, 1, 0.4), (0.8, 1.0, 1, 1.8), (1.0, TINY, 1, 2.2)])

    fx.begin("rim")
    fx.revolve(annulus(R * 0.9, R * 0.98, 0.07, 0.05), rgb(0.7, 0.45, 1.0), rgb(0.92, 0.82, 1.0), sides=16)
    fx.anim("rim", [(0, 0.2), (0.2, 1.0), (0.8, 1.0), (1.0, TINY)])

    for group in range(2):  # cristais: dois grupos de 4, o segundo um pouco depois
        name = f"crystals{group}"
        fx.begin(name)
        for i in range(4):
            a = (i + 0.5 * group) * math.pi / 2 + 0.3 * group
            height = fx.rnd.uniform(1.1, 1.7)
            fx.revolve([(0, 0), (0.3, 0), (0.22, height * 0.6), (0, height)], rgb(0.4, 0.14, 0.7), rgb(0.82, 0.6, 1.0),
                       at=(math.cos(a) * R * 0.62, math.sin(a) * R * 0.62, 0.0), sides=5, yaw=a, pitch=0.3)
        t0 = 0.08 * group
        fx.anim(name, [(t0, 1, TINY), (t0 + 0.08, 1, TINY), (t0 + 0.22, 1, 1.2), (t0 + 0.32, 1, 1.0),
                       (0.75, 1, 1.0), (0.95, 1, TINY)])

    fx.begin("pillar")
    fx.revolve([(0, 0), (0.5, 0), (0.36, 2.4), (0, 2.8)], rgb(0.7, 0.45, 1.0), rgb(1.0, 0.95, 1.0), sides=8)
    fx.anim("pillar", [(0, 1, TINY), (0.08, 1.0, 1.0), (0.3, 0.8, 1.0), (0.6, 0.25, 0.8), (0.7, TINY)])

    fx.begin("wave")
    fx.revolve(annulus(0.8, 1.0, 0.1, 0.06), rgb(0.8, 0.6, 1.0), rgb(1.0, 0.95, 1.0), sides=16)
    fx.anim("wave", [(0, 0.2, 1), (0.3, R * 0.95, 1), (0.45, R, 1), (0.5, TINY)])
    return fx


build().export()
