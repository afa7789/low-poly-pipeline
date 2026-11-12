"""Efeito 3D da explosão de morte (SkillFxKind::DeathExplosion): bola de fogo, onda, línguas de fogo e fumaça.

    blender -b --python tools/blender/fx_death_explosion.py

Grava assets/fx3d/death_explosion.glb. Desenhado para raio 2,5 (o motor escala pelo raio do evento).
O clarão e a onda saem na hora (o acerto cai no 1º quadro); as línguas se espalham pelo chão e a fumaça sobe no fim.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # o Blender não põe a pasta do script no caminho
from fx_rig import TINY, Fx, annulus, blob, cone, disc, rgb

R = 2.5


def build():
    fx = Fx("death_explosion")
    fx.begin("scorch")
    fx.revolve(disc(R * 0.9, 0.01), rgb(0.34, 0.13, 0.05), rgb(0.16, 0.07, 0.04), sides=10, jitter=0.08, flat=True)
    fx.anim("scorch", [(0, 0.3), (0.12, 1.0), (0.75, 1.0), (1.0, TINY)])
    fx.begin("flash")
    fx.revolve(disc(R * 0.85, 0.08), rgb(1.0, 0.95, 0.7), rgb(1.0, 0.55, 0.15), sides=10, flat=True)
    fx.anim("flash", [(0, 0.5), (0.08, 1.0), (0.25, 0.9), (0.3, TINY)])

    fx.begin("wave")
    fx.revolve(annulus(0.8, 1.0, 0.14, 0.05), rgb(1.0, 0.8, 0.35), rgb(1.0, 0.97, 0.75), sides=14)
    fx.anim("wave", [(0, 0.25, 1), (0.35, R, 1), (0.5, R * 1.1, 1), (0.55, TINY)])

    fx.begin("fire", head=(0, 0, 0.9))
    fx.revolve(blob(1.0), rgb(0.85, 0.22, 0.05), rgb(1.0, 0.85, 0.35), at=(0, 0, 0.9), sides=7, jitter=0.12)
    fx.anim("fire", [(0, 0.2), (0.1, 1.2), (0.25, 1.5), (0.55, 1.1), (0.75, TINY)])
    fx.begin("core", head=(0, 0, 0.95))
    fx.revolve(blob(0.6), rgb(1.0, 0.8, 0.3), rgb(1.0, 1.0, 0.85), at=(0, 0, 0.95), sides=6, jitter=0.1)
    fx.anim("core", [(0, 0.3), (0.07, 1.2), (0.2, 0.9), (0.3, TINY)])

    # línguas de fogo: cones deitados para fora; escalar `h` as empurra pelo chão. Dois grupos, tempos diferentes.
    for group, t0 in enumerate([0.0, 0.06]):
        name = f"tongues{group}"
        fx.begin(name, head=(0, 0, 0.1))
        for i in range(5):
            a = (i + 0.5 * group) * 2 * math.pi / 5 + 0.2 * group
            fx.revolve(cone(0.32, 1.5), rgb(0.85, 0.2, 0.05), rgb(1.0, 0.85, 0.3),
                       at=(math.cos(a) * 0.3, math.sin(a) * 0.3, 0.25), sides=5, yaw=a, pitch=1.25, jitter=0.1)
        fx.anim(name, [(t0, 0.2, 0.5), (t0 + 0.18, 1.5, 0.9), (t0 + 0.4, 1.9, 0.8), (t0 + 0.6, TINY)])

    fx.begin("smoke", head=(0, 0, 0.3))
    for i in range(5):
        a = i * 2 * math.pi / 5 + 0.4
        fx.revolve(blob(0.45), rgb(0.22, 0.18, 0.16), rgb(0.46, 0.4, 0.36),
                   at=(math.cos(a) * 0.9, math.sin(a) * 0.9, 0.9), sides=6, jitter=0.15)
    fx.anim("smoke", [(0, TINY), (0.25, TINY), (0.5, 0.9, 1.0), (0.85, 1.4, 1.8), (1.05, TINY)])
    return fx


build().export()
