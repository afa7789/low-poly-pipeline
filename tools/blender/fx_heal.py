"""Efeito 3D da família de cura (Heal, CastHeal, ChainHeal dividem esta malha; o motor muda escala e ritmo).

    blender -b --python tools/blender/fx_heal.py

Grava assets/fx3d/heal.glb. Verde: poça de luz e anel que abre no chão, três anéis que sobem e uma cruz que
flutua e gira. As luzinhas que sobem são rajada de pixels (render/SkillFxParticles).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # o Blender não põe a pasta do script no caminho
from fx_rig import TINY, Fx, annulus, disc, rgb


def build():
    fx = Fx("heal")
    fx.begin("plate")
    fx.revolve(disc(1.0, 0.01), rgb(0.3, 0.85, 0.4), rgb(0.1, 0.45, 0.2), sides=10, flat=True)
    fx.anim("plate", [(0, 0.4), (0.15, 1.0), (0.7, 1.0), (1.0, TINY)])
    fx.begin("wave")
    fx.revolve(annulus(0.85, 1.0, 0.07, 0.05), rgb(0.5, 1.0, 0.55), rgb(0.9, 1.0, 0.9), sides=12)
    fx.anim("wave", [(0, 0.3, 1), (0.35, 1.6, 1), (0.6, 1.8, 1), (0.65, TINY)])

    for n in range(3):  # anéis finos que sobem esticando a escala vertical; a base fica fixa no chão
        name = f"rise{n}"
        t0 = 0.12 * n
        fx.begin(name)
        fx.revolve(annulus(0.7, 0.82, 0.012, 0.1), rgb(0.3, 0.85, 0.4), rgb(0.8, 1.0, 0.8), sides=10)
        fx.anim(name, [(t0, 1, 1), (t0 + 0.6, 0.6, 9), (t0 + 0.7, TINY)])

    fx.begin("cross")
    fx.box((0.7, 0.22, 0.14), rgb(0.4, 0.9, 0.45), rgb(0.85, 1.0, 0.85), at=(0, 0, 0.8))
    fx.box((0.22, 0.7, 0.14), rgb(0.4, 0.9, 0.45), rgb(0.85, 1.0, 0.85), at=(0, 0, 0.8))
    fx.anim("cross", [(0, TINY, TINY, 0), (0.12, 1.3, 1.0, 0.2), (0.25, 1.0, 1.1, 0.4), (0.8, 1.0, 1.4, 1.1),
                      (0.95, TINY, 1.5, 1.3)])
    return fx


build().export()
