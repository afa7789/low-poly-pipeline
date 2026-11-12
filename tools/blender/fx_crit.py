"""Efeito 3D do Crit (SkillFxKind::Crit): estrela dourada de impacto com espinhos, clarão e onda no chão.

    blender -b --python tools/blender/fx_crit.py

Grava assets/fx3d/crit.glb. Dourado: duas estrelas de 12 pontas girando em sentidos opostos, clarão branco,
espinhos para cima e para fora e uma onda. Acerto no 1º quadro; some em 0,55 s.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # o Blender não põe a pasta do script no caminho
from fx_rig import TINY, Fx, annulus, blob, cone, rgb


def build():
    fx = Fx("crit")
    fx.begin("star", head=(0, 0, 0.9))
    fx.star(12, 2.1, 0.5, 0.08, rgb(1.0, 0.95, 0.7), rgb(1.0, 0.68, 0.1), at=(0, 0, 0.9))
    fx.anim("star", [(0, 0.2, 1, 0), (0.06, 1.1, 1, 0.1), (0.3, 1.0, 1, 0.5), (0.55, TINY, 1, 0.8)])
    fx.begin("star2", head=(0, 0, 0.96))
    fx.star(12, 1.3, 0.35, 0.08, rgb(1.0, 1.0, 0.95), rgb(1.0, 0.9, 0.45), at=(0, 0, 0.96), yaw=math.pi / 12)
    fx.anim("star2", [(0, 0.2, 1, 0), (0.06, 1.1, 1, -0.1), (0.3, 1.0, 1, -0.6), (0.5, TINY, 1, -0.9)])
    fx.begin("flash", head=(0, 0, 0.95))
    fx.revolve(blob(0.6), rgb(1.0, 0.95, 0.6), rgb(1.0, 1.0, 1.0), at=(0, 0, 0.95), sides=4)
    fx.anim("flash", [(0, 0.3), (0.05, 1.5), (0.2, 0.8), (0.3, TINY)])

    fx.begin("spikes", head=(0, 0, 0.2))
    for i in range(8):
        a = i * math.pi / 4 + 0.15
        fx.revolve(cone(0.18, 1.5 if i % 2 else 1.1), rgb(1.0, 0.65, 0.08), rgb(1.0, 0.95, 0.6),
                   at=(math.cos(a) * 0.3, math.sin(a) * 0.3, 0.2), sides=5, yaw=a, pitch=0.9)
    fx.anim("spikes", [(0, 0.3, 0.4), (0.1, 1.2, 1.2), (0.35, 1.0, 1.0), (0.55, TINY)])

    fx.begin("wave")
    fx.revolve(annulus(0.8, 1.0, 0.1, 0.05), rgb(1.0, 0.75, 0.2), rgb(1.0, 0.97, 0.75), sides=14)
    fx.anim("wave", [(0, 0.2, 1), (0.3, 2.2, 1), (0.45, 2.4, 1), (0.5, TINY)])
    return fx


build().export()
