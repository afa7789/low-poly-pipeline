"""Efeito 3D do Stun (SkillFxKind::Stun): a pancada que atordoa (o estado contínuo são as estrelas do sprite).

    blender -b --python tools/blender/fx_stun.py

Grava assets/fx3d/stun.glb. Amarelo-branco: estrela de impacto, clarão, espinhos para fora e duas ondas no chão.
Acerto no 1º quadro; some em 0,6 s.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # o Blender não põe a pasta do script no caminho
from fx_rig import TINY, Fx, annulus, blob, cone, rgb


def build():
    fx = Fx("stun")
    fx.begin("star", head=(0, 0, 0.9))
    fx.star(8, 1.5, 0.38, 0.1, rgb(1.0, 1.0, 0.9), rgb(1.0, 0.82, 0.25), at=(0, 0, 0.9))
    fx.anim("star", [(0, 0.2, 1, 0), (0.07, 1.0, 1, 0.1), (0.3, 0.9, 1, 0.5), (0.5, TINY, 1, 0.7)])
    fx.begin("flash", head=(0, 0, 0.9))
    fx.revolve(blob(0.5), rgb(1.0, 0.95, 0.6), rgb(1.0, 1.0, 1.0), at=(0, 0, 0.9), sides=6)
    fx.anim("flash", [(0, 0.3), (0.05, 1.4), (0.2, 0.8), (0.3, TINY)])

    fx.begin("spikes", head=(0, 0, 0.3))
    for i in range(6):
        a = i * math.pi / 3 + 0.2
        fx.revolve(cone(0.16, 1.0), rgb(1.0, 0.9, 0.4), rgb(1.0, 1.0, 0.9),
                   at=(math.cos(a) * 0.35, math.sin(a) * 0.35, 0.3), sides=5, yaw=a, pitch=1.15)
    fx.anim("spikes", [(0, 0.3, 0.5), (0.1, 1.3, 1.0), (0.35, 1.1, 0.9), (0.5, TINY)])

    fx.begin("puffs")  # poeira da pancada, rente ao chão
    for i in range(6):
        a = i * math.pi / 3
        fx.revolve(blob(0.2), rgb(0.9, 0.84, 0.6), rgb(1.0, 0.98, 0.85),
                   at=(math.cos(a) * 0.5, math.sin(a) * 0.5, 0.2), sides=6, jitter=0.12)
    fx.anim("puffs", [(0, 0.4, 0.5), (0.25, 2.0, 1.2), (0.6, 2.6, 0.3), (0.7, TINY)])

    for n, (t0, top) in enumerate([(0.0, 1.9), (0.1, 1.5)]):
        name = f"wave{n}"
        fx.begin(name)
        fx.revolve(annulus(0.8, 1.0, 0.1, 0.05 + 0.02 * n), rgb(1.0, 0.9, 0.4), rgb(1.0, 1.0, 0.85), sides=12)
        fx.anim(name, [(t0, 0.2, 1), (t0 + 0.3, top, 1), (t0 + 0.4, top * 1.1, 1), (t0 + 0.45, TINY)])
    return fx


build().export()
