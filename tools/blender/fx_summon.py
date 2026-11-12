"""Efeito 3D do Summon (SkillFxKind::Summon): fumaça clara e círculo que somem onde a invocação nasce.

    blender -b --python tools/blender/fx_summon.py

Grava assets/fx3d/summon.glb. Branco e cinza claro: nuvens que abrem pelo chão, fio de fumaça que sobe,
círculo no chão e clarão. Termina antes de 1 s para não esconder a unidade recém-nascida.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # o Blender não põe a pasta do script no caminho
from fx_rig import TINY, Fx, annulus, blob, disc, rgb


def build():
    fx = Fx("summon")
    fx.begin("plate")
    fx.revolve(disc(1.2, 0.01), rgb(0.8, 0.82, 0.95), rgb(0.55, 0.58, 0.75), sides=10, flat=True)
    fx.anim("plate", [(0, 0.4), (0.15, 1.0), (0.6, 1.0), (0.9, TINY)])
    fx.begin("rim", head=(0, 0, 0.05))
    fx.revolve(annulus(1.0, 1.2, 0.06, 0.05), rgb(0.85, 0.88, 1.0), rgb(1.0, 1.0, 1.0), sides=12)
    fx.anim("rim", [(0, 0.3, 1, 0), (0.2, 1.0, 1, 0.5), (0.7, 1.0, 1, 1.5), (0.95, TINY, 1, 1.8)])

    fx.begin("puffs")
    for i in range(8):
        a = i * math.pi / 4 + 0.2
        fx.revolve(blob(0.38), rgb(0.55, 0.57, 0.68), rgb(0.97, 0.98, 1.0),
                   at=(math.cos(a) * 0.5, math.sin(a) * 0.5, 0.35), sides=6, jitter=0.15)
    fx.anim("puffs", [(0, 0.4, 0.4), (0.2, 1.6, 1.0), (0.5, 2.0, 1.4), (0.75, 2.3, 1.1), (0.95, TINY)])

    fx.begin("wisp")
    fx.revolve([(0, 0), (0.26, 0), (0.16, 1.5), (0, 2.1)], rgb(0.8, 0.82, 0.95), rgb(1.0, 1.0, 1.0), sides=6, jitter=0.1)
    fx.anim("wisp", [(0, 1, TINY), (0.1, 1.0, 0.6), (0.3, 0.9, 1.0), (0.55, 0.3, 1.1), (0.65, TINY)])
    fx.begin("flash", head=(0, 0, 0.6))
    fx.revolve(blob(0.5), rgb(1.0, 1.0, 1.0), rgb(0.9, 0.93, 1.0), at=(0, 0, 0.6), sides=6)
    fx.anim("flash", [(0, 0.3), (0.06, 1.3), (0.2, 0.8), (0.3, TINY)])
    return fx


build().export()
