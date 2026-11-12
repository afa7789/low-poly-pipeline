"""Efeito 3D dos Espinhos (SkillFxKind::Thorns): espinhos com folhas brotando do chão, parada e recuo.

    blender -b --python tools/blender/fx_thorns.py

Grava assets/fx3d/thorns.glb (pequeno, versionado). Procedural e determinístico: nenhum asset de entrada.
A malha, os ossos, a cor nos vértices, o clipe e a exportação vêm de fx_rig.py; aqui só a geometria dos espinhos.
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # o Blender não põe a pasta do script no caminho
from fx_rig import TINY, Fx, rgb
from mathutils import Matrix, Vector

SPIKES = 9
LEAVES = 6
# Cores pretendidas na tela (o raylib não converte sRGB): base escura -> ponta clara.
BASE, TIP = rgb(0.30, 0.19, 0.10), rgb(0.80, 0.66, 0.42)
LEAF, LEAF_TIP = rgb(0.20, 0.50, 0.14), rgb(0.52, 0.80, 0.28)
DIRT = rgb(0.27, 0.18, 0.11)


def add_spike(fx, base, height, radius, tilt, yaw):
    """Cone torto de 3 anéis (5 faces) com a base em `base`, inclinado `tilt` rad para `yaw`."""
    bm = fx.bm
    rot = Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(tilt, 4, "Y")
    rings = [(0.0, radius, 0.0), (0.5, radius * 0.55, 0.06 * height), (1.0, 0.0, 0.0)]
    sides = 5
    verts = []
    for z, r, bend in rings:
        if r == 0.0:
            verts.append([bm.verts.new(base + rot @ Vector((bend, 0, z * height)))])
            continue
        ring = []
        for i in range(sides):
            a = i * 2 * math.pi / sides
            ring.append(bm.verts.new(base + rot @ Vector((math.cos(a) * r + bend, math.sin(a) * r, z * height))))
        verts.append(ring)
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append(bm.faces.new((verts[0][i], verts[0][j], verts[1][j], verts[1][i])))
        faces.append(bm.faces.new((verts[1][i], verts[1][j], verts[2][0])))
    faces.append(bm.faces.new(list(reversed(verts[0]))))  # fundo, p/ não ver o oco se o chão ceder
    fx.paint(faces, BASE, TIP, base.z, base.z + height)


def add_leaf(fx, base, length, width, pitch, yaw):
    """Folha: bipirâmide achatada (8 triângulos, vista dos dois lados) saindo de `base`."""
    bm = fx.bm
    rot = Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(pitch, 4, "Y")
    pts = [(0, 0, 0), (length, 0, 0), (length * 0.4, -width, 0), (length * 0.4, width, 0),
           (length * 0.4, 0, width * 0.25), (length * 0.4, 0, -width * 0.25)]
    v = [bm.verts.new(base + rot @ Vector(p)) for p in pts]
    tris = [(0, 2, 4), (0, 4, 3), (0, 5, 2), (0, 3, 5), (1, 4, 2), (1, 3, 4), (1, 2, 5), (1, 5, 3)]
    faces = [bm.faces.new((v[a], v[b], v[c])) for a, b, c in tris]
    fx.paint(faces, LEAF, LEAF_TIP, min(p.co.z for p in v), max(p.co.z for p in v))


def add_dirt(fx, radius, height):
    """Anel de terra revolvida: tronco de 9 lados, borda irregular. Marca o chão sob os espinhos."""
    bm = fx.bm
    rnd = random.Random(7)
    sides = 9
    outer = [bm.verts.new((math.cos(a) * radius * rnd.uniform(0.85, 1.0), math.sin(a) * radius * rnd.uniform(0.85, 1.0), 0.0))
             for a in (i * 2 * math.pi / sides for i in range(sides))]
    inner = [bm.verts.new((v.co.x * 0.62, v.co.y * 0.62, height)) for v in outer]
    faces = [bm.faces.new((outer[i], outer[(i + 1) % sides], inner[(i + 1) % sides], inner[i])) for i in range(sides)]
    faces.append(bm.faces.new(list(reversed(inner))))
    fx.paint(faces, DIRT, DIRT)


def build():
    fx = Fx("thorns")
    rnd = random.Random(11)
    fx.begin("dirt", tail=(0, 0, 0.2))
    add_dirt(fx, 1.2, 0.07)
    names = []
    for i in range(SPIKES):
        ring = 0.0 if i == 0 else 0.5 + 0.5 * (i % 3) / 2
        yaw = i * 2 * math.pi / (SPIKES - 1) + rnd.uniform(-0.25, 0.25) if i else 0.0
        base = Vector((math.cos(yaw) * ring, math.sin(yaw) * ring, 0.04))
        height = 2.0 if i == 0 else rnd.uniform(1.0, 1.7)
        tilt = 0.0 if i == 0 else rnd.uniform(0.25, 0.5)  # abre para fora
        tail = base + Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(tilt, 4, "Y") @ Vector((0, 0, height))
        names.append(fx.begin(f"spike{i}", base, tail))
        add_spike(fx, base, height, 0.17 if i == 0 else rnd.uniform(0.11, 0.15), tilt, yaw)
        if i % 3 == 1 or i == 0:  # folhas na altura do 1º terço, no espinho central e em dois outros
            for k in range(2 if i == 0 else 1):
                ly = yaw + (math.pi / 2 + k * math.pi if i == 0 else math.pi / 2)
                add_leaf(fx, base.lerp(tail, 0.28), rnd.uniform(0.55, 0.8), 0.17, -rnd.uniform(0.7, 1.0), ly)
    animate(fx, names)
    return fx


def animate(fx, spikes):
    """Brota escalonado (com estouro), segura, recua. Tempos em segundos; 1 s no total."""
    fx.anim("dirt", [(0, 0.4), (0.1, 1.0), (0.8, 1.0), (1.0, TINY)])
    for i, name in enumerate(spikes):
        t0 = 0.0 if i == 0 else 0.03 + 0.012 * i  # o central sai primeiro, o resto em onda
        fx.anim(name, [(0, TINY), (t0, TINY), (t0 + 0.14, 1.18), (t0 + 0.22, 1.0),  # estouro
                       (0.62 + 0.012 * i, 1.0), (0.9 + 0.01 * i, TINY)])


build().export()
