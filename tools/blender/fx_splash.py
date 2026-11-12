"""Efeito 3D do Splash (SkillFxKind::Splash): pancada no chão, rachadura, onda de poeira e monte de terra.

    blender -b --python tools/blender/fx_splash.py

Grava assets/fx3d/splash.glb. Desenhado para raio 2,5 (o motor escala pelo raio do evento). A onda e as
rachaduras abrem pelo chão e a poeira sobe pouco: de cima o dano em área se lê como mancha que se espalha.
"""
import math
import sys
from itertools import pairwise
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # o Blender não põe a pasta do script no caminho
from fx_rig import TINY, Fx, blob, rgb

R = 2.5


def build():
    fx = Fx("splash")
    fx.begin("cracks", head=(0, 0, 0.05))  # rachaduras: 9 traços em zigue-zague saindo do centro
    for i in range(9):
        a = i * 2 * math.pi / 9 + 0.3
        kink = a + fx.rnd.uniform(-0.25, 0.25)
        pts = [(0.18 * R, a), (0.55 * R, a), (fx.rnd.uniform(0.85, 0.98) * R, kink)]
        for (r0, a0), (r1, a1) in pairwise(pts):
            fx.bar((math.cos(a0) * r0, math.sin(a0) * r0), (math.cos(a1) * r1, math.sin(a1) * r1), 0.13, 0.04,
                   rgb(0.16, 0.1, 0.06), rgb(0.3, 0.2, 0.12), z=0.03)
    fx.anim("cracks", [(0, 0.25), (0.09, 1.0), (0.6, 1.0), (0.8, TINY)])

    fx.begin("wave")  # frente de poeira: rampa que sobe e abre
    fx.revolve([(0.84, 0), (1.0, 0), (0.97, 0.25), (0.88, 0.18)], rgb(0.5, 0.4, 0.28), rgb(0.82, 0.72, 0.55), sides=14)
    fx.anim("wave", [(0, 0.3, 0.6), (0.3, R, 1.0), (0.5, R * 1.1, 0.5), (0.6, TINY)])

    fx.begin("mound")
    fx.revolve([(0, 0), (0.5, 0), (0.3, 0.25), (0, 0.4)], rgb(0.33, 0.22, 0.13), rgb(0.62, 0.48, 0.32),
               sides=7, jitter=0.12)
    fx.anim("mound", [(0, 1, TINY), (0.05, 1.1, 1.3), (0.2, 0.9, 0.8), (0.4, TINY)])

    fx.begin("puffs")  # nuvens de poeira: nascem perto do centro e correm para a borda
    for i in range(7):
        a = i * 2 * math.pi / 7 + 0.3
        fx.revolve(blob(0.15), rgb(0.6, 0.5, 0.36), rgb(0.85, 0.78, 0.62),
                   at=(math.cos(a) * 0.9, math.sin(a) * 0.9, 0.3), sides=6, jitter=0.15)
    fx.anim("puffs", [(0, 0.3, 0.4), (0.25, 1.6, 1.2), (0.5, 2.2, 1.4), (0.78, 2.6, 0.5), (0.9, TINY)])
    return fx


build().export()
