"""Cenário dos mapas (docs/maps.md) modelado por script: um GLB por peça em assets/scenery/<mapa>/.

Uso:
    blender -b --factory-startup --python tools/blender/map_scenery.py -- <nome|all> [--out DIR] [--render DIR]

Usa o kit de modelagem de map_castles.py. Tamanhos seguem o que o Terrain espera de cada peça:
  - muralha e pilar: caixa unitária (x de -0,5 a 0,5; o Terrain escala para 3,2 x 1,1 e 1,1 x 1,1);
  - vão do portão: meio-modelo em x de -0,5 a 0, altura 1,31;
  - árvore: 5 unidades de altura; arbusto, pedra e decoração: tamanho real em unidades da sim.
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import itertools

import map_castles as kit
from map_castles import beam, box, cyl, mat, prism, ring


def palette():
    return {
        "wood": mat("wood", 0x6A5238),
        "wood_dk": mat("wood_dark", 0x46362A),
        "bag": mat("sandbag", 0xA89A74),
        "bag_dk": mat("sandbag_dark", 0x86795A),
        "iron": mat("iron", 0x2B2D30),
        "steel": mat("steel", 0x56606A),
        "rust": mat("rust", 0x8A4526),
        "concrete": mat("concrete", 0x8F897B),
        "concrete_dk": mat("concrete_dark", 0x5F5A50),
        "char": mat("char", 0x2A2420),
        "ash": mat("ash", 0x5A5048),
        "hazard": mat("hazard", 0xE2B224),
        "brick": mat("brick", 0x7C3D2E),
        "oil": mat("oil", 0x16131A),
        "lamp": mat("lamp", 0xFFC658, emit=3.0),
        "fire": mat("fire", 0xFF8A1E, emit=3.5),
        "fire_core": mat("fire_core", 0xFFD860, emit=4.0),
    }


def normalize(sx, sy, sz=1.0):
    """Divide a cena pelos tamanhos reais: a peça sai na caixa unitária que o Terrain escala de volta."""
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH":
            continue
        for v in ob.data.vertices:
            v.co.x /= sx
            v.co.y /= sy
            v.co.z /= sz


def sandbag(material, pos, size=(0.52, 0.32, 0.17), rot_z=0.0):
    return box("sandbag", material, pos, size, bevel=0.055, rot_z=rot_z)


def sandbag_row(p, x0, x1, y, z, count, flip=False):
    step = (x1 - x0) / count
    for i in range(count):
        m = p["bag"] if (i + (1 if flip else 0)) % 2 == 0 else p["bag_dk"]
        sandbag(m, (x0 + (i + 0.5) * step, y, z), size=(step * 0.98, 0.34, 0.17))


def wire_coil(material, a, b, radius=0.2, turns=5):
    """Arame farpado: hélice de segmentos retos de a até b."""
    a, b = Vector(a), Vector(b)
    axis = (b - a).normalized()
    side = axis.cross(Vector((0, 0, 1))).normalized()
    up = Vector((0, 0, 1))
    steps = turns * 6
    prev = None
    for i in range(steps + 1):
        t = i / steps
        ang = t * turns * math.tau
        pt = a.lerp(b, t) + side * math.cos(ang) * radius + up * (math.sin(ang) * radius + radius)
        if prev is not None:
            beam("wire", material, prev, pt, thick=0.03)
        prev = pt


# ---------------------------------------------------------------------------------------------------------
# Muralha de trincheira, pilar e vão do portão
# ---------------------------------------------------------------------------------------------------------


def oil_wall():
    """Revestimento de trincheira: estacas e pranchas, duas fiadas de sacos de areia e arame no topo."""
    p = palette()
    length, thick = 3.2, 1.1
    box("berm", p["wood_dk"], (0, 0, 0), (length, 0.78, 0.2), bevel=0.0, taper_y=0.9)
    box("core", p["wood_dk"], (0, 0, 0.18), (length, 0.5, 0.74), bevel=0.0)
    for side in (-1, 1):
        for i, z in enumerate((0.22, 0.46, 0.7)):
            tone = p["wood"] if i != 1 else p["wood_dk"]
            box("plank", tone, (0, side * 0.27, z), (length, 0.07, 0.21), bevel=0.0)
        for x in (-1.2, -0.4, 0.4, 1.2):
            box("post", p["wood"], (x, side * 0.33, 0.0), (0.15, 0.13, 1.06), bevel=0.02)
    sandbag_row(p, -length / 2, length / 2, -0.12, 0.92, 6)
    sandbag_row(p, -length / 2, length / 2, 0.14, 0.92, 6, flip=True)
    sandbag_row(p, -length / 2 + 0.27, length / 2 - 0.27, 0.0, 1.08, 5)
    for x in (-0.8, 0.8):
        box("picket", p["iron"], (x, 0.0, 1.22), (0.05, 0.05, 0.3), bevel=0.0)
    wire_coil(p["iron"], (-1.55, 0.0, 1.22), (1.55, 0.0, 1.22), radius=0.11, turns=9)
    normalize(length, thick)


def oil_pillar():
    """Pilar de portão: pilone de concreto em talude com cinta de perigo, chapéu de aço e lâmpada."""
    p = palette()
    box("foot", p["concrete_dk"], (0, 0, 0), (1.1, 1.1, 0.25), bevel=0.04)
    box("shaft", p["concrete"], (0, 0, 0.22), (0.92, 0.92, 1.75), bevel=0.05, taper=0.8, taper_y=0.8)
    box("band", p["hazard"], (0, 0, 0.75), (0.9, 0.9, 0.16), bevel=0.0, taper=0.985, taper_y=0.985)
    box("cap", p["steel"], (0, 0, 1.95), (0.86, 0.86, 0.14), bevel=0.02)
    box("lamp_post", p["iron"], (0, 0, 2.08), (0.1, 0.1, 0.2), bevel=0.0)
    box("lamp", p["lamp"], (0, 0, 2.26), (0.22, 0.22, 0.14), bevel=0.0)
    for i, (dx, dy, rz) in enumerate(((0.5, 0.2, 0.3), (-0.48, -0.25, 1.2), (0.1, -0.55, 0.0))):
        sandbag(p["bag"] if i % 2 else p["bag_dk"], (dx, dy, 0.0), rot_z=rz)
    normalize(1.1, 1.1, 1.83)


def oil_arch():
    """Meio vão do portão (o Terrain espelha no eixo): viga treliçada de aço com faixa de perigo e lâmpada."""
    p = palette()
    # Unidades do modelo: x de -0,5 a 0 ao longo do vão, altura até 1,31, profundidade +-0,5.
    z0, z1 = 0.98, 1.27
    for y in (-0.16, 0.16):
        beam("chord", p["steel"], (-0.5, y, z0), (0.0, y, z0), thick=0.05)
        beam("chord", p["steel"], (-0.5, y, z1), (0.0, y, z1), thick=0.05)
        for i in range(4):
            x0, x1 = -0.5 + i * 0.125, -0.5 + (i + 1) * 0.125
            a, b = ((x0, y, z0), (x1, y, z1)) if i % 2 == 0 else ((x0, y, z1), (x1, y, z0))
            beam("web", p["iron"], a, b, thick=0.03)
    box("deck", p["iron"], (-0.25, 0, z1), (0.5, 0.4, 0.03), bevel=0.0)
    box("sign", p["hazard"], (-0.25, -0.19, z0 + 0.06), (0.36, 0.02, 0.14), bevel=0.0)
    box("lamp", p["lamp"], (-0.06, 0, z0 - 0.07), (0.07, 0.1, 0.06), bevel=0.0)


# ---------------------------------------------------------------------------------------------------------
# Árvores queimadas, tocos e obstáculos
# ---------------------------------------------------------------------------------------------------------


def burnt_tree(height, bends, branches, split=False):
    p = palette()
    pts = [Vector((0, 0, 0))]
    for dx, dy, dz in bends:
        pts.append(pts[-1] + Vector((dx, dy, dz)) * height)
    radii = [0.34 - 0.24 * i / (len(pts) - 1) for i in range(len(pts))]
    cyl("root", p["char"], (0, 0, 0), 0.5, 0.22, sides=7, top_radius=0.36, bevel=0.0)
    for i, (a, b) in enumerate(itertools.pairwise(pts)):
        d = b - a
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=radii[i], radius2=radii[i + 1], depth=d.length * 1.04)
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, d.length / 2))
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=d.to_track_quat("Z", "Y").to_matrix())
        bmesh.ops.translate(bm, verts=bm.verts, vec=a)
        kit._finish(bm, "trunk", p["char"] if i % 2 == 0 else p["ash"])
    for seg, t, (bx, by, bz), length in branches:
        a = pts[seg].lerp(pts[seg + 1], t)
        tip = a + Vector((bx, by, bz)).normalized() * length * height
        kit.spike(p["char"], a, height=(tip - a).length, radius=0.11, lean=(tip.x - a.x, tip.y - a.y))
    if split:
        top = pts[-1]
        for dx, dy in ((0.1, 0.05), (-0.08, 0.1), (0.0, -0.12)):
            kit.spike(p["ash"], (top.x + dx, top.y + dy, top.z - 0.1), height=0.55, radius=0.07, lean=(dx, dy))


def oil_tree_a():
    burnt_tree(5.0, ((0.03, 0.0, 0.36), (-0.05, 0.04, 0.34), (0.04, -0.02, 0.3)),
               ((0, 0.8, (1, 0.2, 0.6), 0.2), (1, 0.5, (-1, 0.4, 0.7), 0.24), (1, 0.9, (0.3, -1, 0.8), 0.16), (2, 0.4, (-0.4, -0.8, 0.9), 0.14)))


def oil_tree_b():
    burnt_tree(5.0, ((-0.04, 0.03, 0.4), (0.08, 0.0, 0.3), (-0.02, 0.05, 0.3)),
               ((0, 0.6, (-1, -0.3, 0.5), 0.22), (1, 0.3, (0.8, 0.7, 0.6), 0.26), (2, 0.2, (-0.6, 0.8, 0.8), 0.15)))


def oil_tree_c():
    """Tronco partido ao meio: estilhaços no topo e um galho só."""
    burnt_tree(5.0, ((0.05, 0.02, 0.3), (-0.03, -0.04, 0.24)), ((0, 0.7, (1, -0.5, 0.5), 0.2),), split=True)


def oil_stump():
    p = palette()
    cyl("root", p["char"], (0, 0, 0), 0.62, 0.2, sides=7, top_radius=0.44, bevel=0.0)
    cyl("stump", p["ash"], (0, 0, 0.18), 0.42, 0.5, sides=7, top_radius=0.36, bevel=0.0)
    for dx, dy in ((0.14, 0.05), (-0.1, 0.16), (0.0, -0.18)):
        kit.spike(p["char"], (dx, dy, 0.62), height=0.5, radius=0.1, lean=(dx * 0.5, dy * 0.5))


def oil_wire():
    """Rede de arame farpado: três estacas cruzadas e duas hélices (lugar do arbusto)."""
    p = palette()
    for x in (-0.85, 0.0, 0.85):
        beam("stake", p["wood"], (x - 0.18, -0.2, 0.0), (x + 0.18, 0.2, 0.95), thick=0.08)
        beam("stake", p["wood"], (x + 0.18, -0.2, 0.0), (x - 0.18, 0.2, 0.95), thick=0.08)
    wire_coil(p["iron"], (-1.0, 0.0, 0.25), (1.0, 0.0, 0.25), radius=0.26, turns=6)
    wire_coil(p["iron"], (-1.0, 0.12, 0.0), (1.0, -0.12, 0.0), radius=0.16, turns=7)


def oil_sandbags():
    """Ninho de sacos de areia em arco (lugar do arbusto)."""
    p = palette()
    for layer, (count, z) in enumerate(((6, 0.0), (5, 0.17), (4, 0.34))):
        for i in range(count):
            a = math.radians(-70 + 140 * (i + 0.5 + 0.5 * (layer % 2)) / (count + (layer % 2)))
            pos = (math.sin(a) * 1.0, -math.cos(a) * 1.0 + 0.6, z)
            sandbag(p["bag"] if (i + layer) % 2 else p["bag_dk"], pos, rot_z=a)
    box("crate", p["wood"], (0.1, 0.35, 0.0), (0.5, 0.4, 0.36), bevel=0.02, rot_z=0.3)
    box("crate_band", p["wood_dk"], (0.1, 0.35, 0.14), (0.52, 0.42, 0.07), bevel=0.0, rot_z=0.3)


def oil_rubble():
    """Entulho de casamata: lajes de concreto tombadas com vergalhão (lugar da pedra)."""
    p = palette()
    box("mound", p["concrete_dk"], (0, 0, 0), (3.6, 3.0, 0.5), bevel=0.2, taper=0.6, taper_y=0.6)
    slabs = (((-0.7, 0.3, 0.3), (1.9, 1.3, 0.34), 0.4), ((0.8, -0.4, 0.35), (1.6, 1.5, 0.3), -0.7),
             ((0.1, 0.5, 0.7), (1.3, 0.9, 0.3), 1.1), ((-0.3, -0.7, 0.55), (1.0, 0.8, 0.28), 0.1))
    for i, (pos, size, rz) in enumerate(slabs):
        box("slab", p["concrete"] if i % 2 == 0 else p["concrete_dk"], pos, size, bevel=0.05, taper=0.86, rot_z=rz)
    for a, b in (((0.4, 0.6, 0.9), (0.9, 1.0, 1.7)), ((-0.9, 0.1, 0.6), (-1.4, -0.3, 1.4)), ((0.9, -0.6, 0.6), (1.5, -0.4, 1.2))):
        beam("rebar", p["rust"], a, b, thick=0.06)


def oil_drums():
    """Depósito de tambores: seis em pé, um amarelo, dois tombados e um estrado (lugar da pedra)."""
    p = palette()
    box("pallet", p["wood_dk"], (0, 0, 0), (2.6, 2.0, 0.14), bevel=0.02)
    spots = ((-0.8, -0.4), (-0.2, -0.5), (0.4, -0.4), (-0.6, 0.25), (0.05, 0.2), (0.7, 0.3))
    for i, (x, y) in enumerate(spots):
        tone = p["hazard"] if i == 4 else (p["rust"] if i % 2 else p["steel"])
        cyl("drum", tone, (x, y, 0.14), 0.3, 0.86, sides=10, bevel=0.0)
        for z in (0.36, 0.72):
            ring("drum_rib", p["iron"], (x, y, z), 0.3, 0.05, thick=0.02, sides=10)
    cyl("drum_top", p["steel"], (-0.25, -0.1, 1.0), 0.3, 0.86, sides=10, bevel=0.0)
    cyl("drum_fallen", p["rust"], (1.25, -0.9, 0.3), 0.3, 0.86, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
    box("spill", p["oil"], (1.5, -0.9, 0.0), (1.2, 0.9, 0.03), bevel=0.0, rot_z=0.3)


def oil_hedgehog():
    """Ouriço tcheco: três vigas de aço cruzadas (lugar da pedra)."""
    p = palette()
    r = 1.2
    for a, b in (((-r, -r * 0.3, 0.0), (r, r * 0.3, 1.5)), ((r * 0.3, -r, 0.0), (-r * 0.3, r, 1.5)), ((-r * 0.7, r * 0.7, 0.75), (r * 0.7, -r * 0.7, 0.75))):
        beam("girder", p["rust"], a, b, thick=0.2)
        beam("girder_web", p["iron"], a, b, thick=0.26 if a[2] == b[2] else 0.08)
    wire_coil(p["iron"], (-1.3, 0.9, 0.0), (1.3, 1.1, 0.0), radius=0.2, turns=6)


# ---------------------------------------------------------------------------------------------------------
# Decoração industrial fora do andável
# ---------------------------------------------------------------------------------------------------------


def oil_derrick():
    """Torre de perfuração de madeira (Baku, 1900): pirâmide tabuada, casa de máquinas e balancim."""
    p = palette()
    box("pad", p["wood_dk"], (0, 0, 0), (3.6, 3.6, 0.2), bevel=0.03)
    kit.derrick(p["wood"], p["wood_dk"], None, (0, 0, 0.2), base=2.6, top=0.7, height=7.6)
    for t, tone in ((0.0, p["wood_dk"]), (0.34, p["wood"])):
        s0, s1 = 2.6 - (2.6 - 0.7) * t, 2.6 - (2.6 - 0.7) * (t + 0.3)
        for ang in (0.0, math.pi / 2):
            box("board", tone, (0, 0, 0.2 + 7.6 * t), (s0 * (1.0 if ang == 0.0 else 0.05), s0 * (0.05 if ang == 0.0 else 1.0), 7.6 * 0.3),
                bevel=0.0, taper=s1 / s0 if ang == 0.0 else 1.0, taper_y=1.0 if ang == 0.0 else s1 / s0)
    box("crown", p["iron"], (0, 0, 7.8), (1.0, 1.0, 0.25), bevel=0.02)
    prism("crown_roof", p["wood_dk"], (0, 0, 8.05), (1.2, 1.2, 0.4), ridge=0.5)
    box("shed", p["wood"], (2.4, 0, 0.0), (1.8, 1.5, 1.2), bevel=0.03)
    prism("shed_roof", p["wood_dk"], (2.4, 0, 1.2), (2.0, 1.7, 0.6), ridge=0.5)
    box("shed_door", p["wood_dk"], (2.4, -0.76, 0.0), (0.5, 0.04, 0.85), bevel=0.0)
    beam("sampson", p["wood_dk"], (1.1, 0, 0.2), (1.1, 0, 2.0), thick=0.22)
    beam("walking_beam", p["rust"], (0.1, 0, 2.3), (2.3, 0, 1.75), thick=0.18)
    cyl("flywheel", p["iron"], (2.4, 0.9, 0.9), 0.55, 0.12, sides=12, bevel=0.0, rot=("X", math.radians(90)))
    cyl("stack", p["iron"], (3.0, 0.4, 1.3), 0.13, 1.3, sides=8, bevel=0.0)


def oil_tank():
    """Tanque de armazenamento rebitado: cintas, teto cônico, escada em espiral e mancha de óleo."""
    p = palette()
    r, h = 1.7, 2.5
    cyl("foot", p["concrete_dk"], (0, 0, 0), r * 1.1, 0.2, sides=16)
    cyl("shell", p["steel"], (0, 0, 0.18), r, h, sides=16, bevel=0.02)
    for z in (0.7, 1.4, 2.1):
        ring("band", p["rust"] if z != 1.4 else p["hazard"], (0, 0, z), r, 0.1, sides=16)
    ring("lip", p["iron"], (0, 0, h + 0.1), r, 0.12, thick=0.07, sides=16)
    cyl("roof", p["iron"], (0, 0, h + 0.18), r * 0.99, 0.5, sides=16, top_radius=0.25, bevel=0.0)
    cyl("vent", p["iron"], (0, 0, h + 0.6), 0.2, 0.3, sides=8)
    for i in range(9):
        a = i * 0.22
        pos = (math.cos(a) * (r + 0.2), math.sin(a) * (r + 0.2), 0.25 + i * 0.27)
        box("stair", p["iron"], pos, (0.4, 0.3, 0.06), bevel=0.0, rot_z=a)
    box("valve", p["rust"], (-r - 0.2, 0, 0.3), (0.5, 0.35, 0.4), bevel=0.03)
    beam("outlet", p["rust"], (-r - 0.3, 0, 0.5), (-r - 1.4, 0, 0.5), thick=0.2)
    box("spill", p["oil"], (-r - 1.2, 0.3, 0.0), (1.3, 1.1, 0.03), bevel=0.0, rot_z=0.4)


def oil_chimney():
    """Chaminé de tijolo sobre a casa da caldeira."""
    p = palette()
    box("house", p["brick"], (0, 0, 0), (2.6, 2.0, 1.5), bevel=0.04)
    prism("house_roof", p["iron"], (0, 0, 1.5), (2.8, 2.2, 0.7), ridge=0.5)
    for x in (-0.7, 0.0, 0.7):
        kit.window(p["iron"], p["lamp"], (x, -1.0, 0.55), "y-", w=0.26, h=0.5)
    kit.chimney(p["brick"], p["rust"], p["iron"], (0.6, 0.2, 1.4), 5.6, radius=0.42)


def oil_wellhead():
    """Cabeça de poço no meio da poça de óleo: bacia de concreto, árvore de válvulas e jorro negro."""
    p = palette()
    cyl("basin", p["concrete_dk"], (0, 0, 0), 1.5, 0.4, sides=14, top_radius=1.4)
    cyl("basin_oil", p["oil"], (0, 0, 0.38), 1.2, 0.04, sides=14, bevel=0.0)
    cyl("casing", p["steel"], (0, 0, 0.3), 0.26, 1.0, sides=10)
    for z in (0.6, 1.0):
        ring("flange", p["rust"], (0, 0, z), 0.26, 0.09, thick=0.08, sides=10)
    beam("arm", p["steel"], (-0.8, 0, 1.15), (0.8, 0, 1.15), thick=0.16)
    for x in (-0.8, 0.8):
        cyl("wheel", p["hazard"], (x, -0.14, 1.15), 0.2, 0.05, sides=10, bevel=0.0, rot=("X", math.radians(90)))
    cyl("cap", p["iron"], (0, 0, 1.3), 0.2, 0.22, sides=8)
    cyl("gusher", p["oil"], (0, 0, 1.5), 0.1, 0.9, sides=6, top_radius=0.2, bevel=0.0)
    # Manchas iridescentes boiando na poça (+-7 em volta do poço): discos chatos, rente ao óleo, em anéis de
    # violeta, verde-petróleo e âmbar. São chatos e ficam no chão: quem atravessa a poça passa por cima.
    tones = (mat("sheen_violet", 0x2C2440), mat("sheen_teal", 0x1F3436), mat("sheen_amber", 0x3A2E1C))
    slicks = ((-4.6, 3.4, 2.2, 0.3), (3.9, 4.6, 1.7, 1.1), (5.0, -2.4, 2.4, 2.0), (-3.2, -4.8, 1.9, 0.7), (1.2, -5.8, 1.2, 2.6))
    for i, (x, y, r, turn) in enumerate(slicks):
        # Duas línguas alongadas e descentradas por mancha: lê como película, não como alvo.
        for ring_i, (k, dx, dy) in enumerate(((1.0, 0.0, 0.0), (0.5, 0.5, -0.3))):
            blob = cyl("slick", tones[(i + ring_i) % 3], (x + dx * r, y + dy * r, 0.045 + 0.004 * ring_i),
                       r * k, 0.004, sides=7, bevel=0.0, rot=("Z", turn + ring_i * 0.9))
            cx = x + dx * r
            for v in blob.data.vertices:
                v.co.x = cx + (v.co.x - cx) * (1.7 if ring_i == 0 else 2.2)
    for (x, y, rz) in ((-2.4, 1.8, 0.4), (4.4, 1.2, 1.3), (-1.2, -3.2, 2.2)):
        box("flotsam", p["wood"], (x, y, 0.04), (1.3, 0.22, 0.07), bevel=0.0, rot_z=rz)


MODELS = {
    "oil_wall": oil_wall,
    "oil_pillar": oil_pillar,
    "oil_arch": oil_arch,
    "oil_tree_a": oil_tree_a,
    "oil_tree_b": oil_tree_b,
    "oil_tree_c": oil_tree_c,
    "oil_stump": oil_stump,
    "oil_wire": oil_wire,
    "oil_sandbags": oil_sandbags,
    "oil_rubble": oil_rubble,
    "oil_drums": oil_drums,
    "oil_hedgehog": oil_hedgehog,
    "oil_derrick": oil_derrick,
    "oil_tank": oil_tank,
    "oil_chimney": oil_chimney,
    "oil_wellhead": oil_wellhead,
}


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["all"]
    names = list(MODELS) if args[0] == "all" else [args[0]]
    out_dir = args[args.index("--out") + 1] if "--out" in args else ""
    render_dir = args[args.index("--render") + 1] if "--render" in args else ""
    for name in names:
        kit.build(name, out_dir, render_dir, make=MODELS[name], views=(("front", -35.0),))


if __name__ == "__main__":
    main()
