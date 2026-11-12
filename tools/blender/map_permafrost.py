"""Permafrost do Norte (docs/maps.md): castelos, cenário e bichos modelados por script.

Uso:
    blender -b --factory-startup --python tools/blender/map_permafrost.py -- <nome|all> [--out DIR] [--render DIR]

Saída: castelos em DIR/castles/frost_*.glb e o resto em DIR/scenery/permafrost/ (frost_*.glb) quando --out é a
raiz assets/. Usa o kit de map_castles.py. Neve é a cor de topo (a câmera de RTS lê o plano de cima): paredes
escuras, topos claros, acento em laranja de lampião e vermelho de sinal. Cor chapada por peça, sem textura.
"""

import itertools
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import map_castles as kit
from map_castles import beam, box, cyl, dome, mat, prism, ring
from map_scenery import normalize

# ---------------------------------------------------------------------------------------------------------
# Paleta e helpers próprios
# ---------------------------------------------------------------------------------------------------------


def palette():
    return {
        "snow": mat("snow", 0xF2F7FC),
        "snow_sh": mat("snow_shade", 0xCFDCEA),
        "ice": mat("ice", 0xA9D0E8),
        "ice_lt": mat("ice_light", 0xD2EAF7),
        "ice_dk": mat("ice_dark", 0x7BA8C8),
        "crack": mat("frost_crack", 0x6E9DBF),
        "wood": mat("wood", 0x6B5238),
        "wood_dk": mat("wood_dark", 0x3F322A),
        "wood_cut": mat("wood_cut", 0xC9A878),
        "stone": mat("stone", 0x7C838B),
        "stone_dk": mat("stone_dark", 0x596068),
        "stone_lt": mat("stone_light", 0xA3AAB1),
        "pine": mat("pine_needles", 0x2F4A40),
        "steel": mat("steel", 0x4A5560),
        "steel_dk": mat("steel_dark", 0x2D343C),
        "rust": mat("rust", 0x8F4A2C),
        "hazard": mat("hazard", 0xE8B820),
        "red": mat("signal_red", 0xD2382A),
        "tarp": mat("tarp", 0x4F7886),
        "lamp": mat("lamp", 0xFFB347, emit=3.0),
        "fire": mat("fire", 0xFF8A1E, emit=3.5),
        "fire_core": mat("fire_core", 0xFFD860, emit=4.0),
        "lag": mat("lagging", 0xA3AFB8),
        "soot": mat("soot", 0x1B1D22),
    }


def blob(material, center, size, sides=8, rings=5, rot_z=0.0):
    """Elipsoide de meio-eixos size/2 em center: massa de neve, corpo de bicho, puff de vapor."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=sides, v_segments=rings, radius=0.5)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(rot_z, 3, "Z"))
    bmesh.ops.translate(bm, verts=bm.verts, vec=center)
    return kit._finish(bm, "blob", material)


def icicle(material, x, y, z_top, length, r=0.045):
    """Pingente pendurado: cone com a ponta para baixo."""
    return cyl("icicle", material, (x, y, z_top - length), 0.004, length, sides=5, top_radius=r, bevel=0.0)


def icicle_row(material, a, b, y, z_top, count, base_len=0.28, r=0.045):
    """Fileira de pingentes de a até b (eixo x) com comprimentos alternados."""
    for i in range(count):
        t = (i + 0.5) / count
        icicle(material, a + (b - a) * t, y, z_top, base_len * (0.55 + 0.45 * ((i * 5) % 3) / 2), r)


def log_x(p, x0, y, z, r, length, tone="wood"):
    """Tora deitada ao longo de x a partir de x0, com o corte claro nas duas pontas."""
    cyl("log", p[tone], (x0, y, z), r, length, sides=7, bevel=0.0, rot=("Y", math.radians(90)))
    for xe in (x0 - 0.005, x0 + length - 0.015):
        cyl("log_cut", p["wood_cut"], (xe, y, z), r * 0.92, 0.02, sides=7, bevel=0.0, rot=("Y", math.radians(90)))


def lantern(p, pos, size=0.2):
    """Lampião: moldura de ferro, vidro aceso, chapéu com neve."""
    x, y, z = pos
    box("lantern_frame", p["steel_dk"], (x, y, z), (size, size, size * 1.3), bevel=0.0)
    box("lantern_glow", p["lamp"], (x, y, z + size * 0.15), (size * 1.12, size * 0.7, size * 0.8), bevel=0.0)
    box("lantern_glow", p["lamp"], (x, y, z + size * 0.15), (size * 0.7, size * 1.12, size * 0.8), bevel=0.0)
    box("lantern_hat", p["snow"], (x, y, z + size * 1.3), (size * 1.25, size * 1.25, size * 0.28), bevel=0.02, taper=0.7, taper_y=0.7)


# ---------------------------------------------------------------------------------------------------------
# Paliçada, pilar e vão do portão
# ---------------------------------------------------------------------------------------------------------


def frost_wall():
    """Paliçada de troncos com capa de neve, travessas e pingentes."""
    p = palette()
    length, thick = 3.2, 1.1
    box("drift", p["snow_sh"], (0, 0, 0), (length, 1.0, 0.22), bevel=0.06, taper_y=0.8)
    box("core", p["wood_dk"], (0, 0, 0.1), (length, 0.5, 1.0), bevel=0.0)
    for row, y in enumerate((-0.24, 0.24)):
        count = 13 - row
        for i in range(count):
            x = -1.5 + i * 0.25 + row * 0.125
            h = 1.16 + 0.09 * ((i * 7 + row * 3) % 3)
            cyl("palisade", p["wood"] if (i + row) % 2 else p["wood_dk"], (x, y, 0.08), 0.1, h, sides=7, top_radius=0.092, bevel=0.0)
    for side in (-1, 1):
        for z in (0.45, 0.85):
            box("rail", p["wood_dk"], (0, side * 0.36, z), (length, 0.06, 0.09), bevel=0.0)
    box("cap", p["snow"], (0, 0, 1.2), (length, 0.9, 0.17), bevel=0.06, taper=0.98, taper_y=0.92)
    for x in (-1.0, 0.1, 1.1):
        blob(p["snow"], (x, 0.0, 1.4), (0.7, 0.5, 0.2))
    for side in (-1, 1):
        icicle_row(p["ice_lt"], -1.5, 1.5, side * 0.4, 1.22, 11)
    normalize(length, thick)


def frost_pillar():
    """Pilar de portão: marco de pedra empilhada com neve nas lajes e lampião aceso no topo."""
    p = palette()
    box("foot", p["stone_dk"], (0, 0, 0), (1.1, 1.1, 0.5), bevel=0.05, taper=0.94, taper_y=0.94)
    box("course2", p["stone"], (0, 0, 0.48), (0.94, 0.94, 0.62), bevel=0.05, rot_z=0.18, taper=0.92, taper_y=0.92)
    box("course3", p["stone_lt"], (0, 0, 1.08), (0.8, 0.8, 0.55), bevel=0.05, rot_z=-0.14, taper=0.9, taper_y=0.9)
    box("slab", p["stone"], (0, 0, 1.6), (0.96, 0.96, 0.18), bevel=0.04, rot_z=0.3)
    box("slab_snow", p["snow"], (0, 0, 1.76), (0.98, 0.98, 0.1), bevel=0.04, taper=0.94, taper_y=0.94, rot_z=0.3)
    for dx, dy, z in ((0.5, 0.2, 0.5), (-0.48, -0.25, 0.48), (0.2, -0.5, 0.0)):
        blob(p["snow"], (dx * 0.8, dy * 0.8, z + 0.06), (0.4, 0.36, 0.2))
    box("post", p["wood_dk"], (0, 0, 1.84), (0.1, 0.1, 0.26), bevel=0.0)
    lantern(p, (0, 0, 2.1), 0.22)
    icicle_row(p["ice_lt"], -0.4, 0.4, 0.46, 1.6, 4, base_len=0.22)
    normalize(1.1, 1.1, 1.83)


def frost_arch():
    """Meio vão do portão (espelhado pelo Terrain): viga de madeira com neve, pingentes e lampião pendurado."""
    p = palette()
    box("beam", p["wood_dk"], (-0.25, 0, 0.96), (0.5, 0.36, 0.26), bevel=0.02)
    box("beam_lt", p["wood"], (-0.25, 0, 1.0), (0.5, 0.26, 0.18), bevel=0.01)
    box("snow", p["snow"], (-0.25, 0, 1.2), (0.5, 0.4, 0.1), bevel=0.03, taper=0.96, taper_y=0.92)
    blob(p["snow"], (-0.3, 0.04, 1.3), (0.34, 0.28, 0.1))
    beam("brace", p["wood_dk"], (-0.5, 0, 0.7), (-0.28, 0, 0.98), thick=0.07)
    icicle_row(p["ice_lt"], -0.46, -0.06, -0.17, 0.97, 5, base_len=0.16, r=0.025)
    icicle_row(p["ice_lt"], -0.4, -0.1, 0.17, 0.97, 4, base_len=0.13, r=0.025)
    beam("hook", p["steel_dk"], (-0.06, 0, 0.96), (-0.06, 0, 0.86), thick=0.015)
    lantern(p, (-0.06, 0, 0.77), 0.09)


# ---------------------------------------------------------------------------------------------------------
# Pinheiros mortos carregados de neve, toco
# ---------------------------------------------------------------------------------------------------------


def trunk(p, pts, radii):
    for i, (a, b) in enumerate(itertools.pairwise(pts)):
        d = b - a
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=radii[i], radius2=radii[i + 1], depth=d.length * 1.04)
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, d.length / 2))
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=d.to_track_quat("Z", "Y").to_matrix())
        bmesh.ops.translate(bm, verts=bm.verts, vec=a)
        kit._finish(bm, "trunk", p["wood_dk"] if i % 2 == 0 else p["wood"])


def drooping_branch(p, root, ang, reach, droop, needles):
    """Galho que cai para fora de root, com massa de neve em cima e, se needles, tufo de agulhas."""
    tip = root + Vector((math.cos(ang) * reach, math.sin(ang) * reach, -droop))
    beam("branch", p["wood_dk"], root, tip, thick=0.1)
    mid = root.lerp(tip, 0.6)
    if needles:
        blob(p["pine"], mid + Vector((0, 0, 0.0)), (reach * 0.95, reach * 0.7, 0.34), sides=6, rings=3, rot_z=ang)
    blob(p["snow"], mid + Vector((0, 0, 0.14 if needles else 0.08)), (reach * 0.85, reach * 0.55, 0.26), sides=7, rings=4, rot_z=ang)


def snow_pine(height, bends, tiers, needle_tiers=(), top_snow=True, broken=False):
    p = palette()
    pts = [Vector((0, 0, 0))]
    for dx, dy, dz in bends:
        pts.append(pts[-1] + Vector((dx, dy, dz)) * height)
    radii = [0.3 - 0.22 * i / (len(pts) - 1) for i in range(len(pts))]
    cyl("root", p["wood_dk"], (0, 0, 0), 0.46, 0.2, sides=7, top_radius=0.32, bevel=0.0)
    blob(p["snow"], (0.0, 0.0, 0.1), (1.5, 1.4, 0.36), sides=9, rings=4)
    trunk(p, pts, radii)
    for ti, (zf, reach, count, turn, droop) in enumerate(tiers):
        root = pts[0].lerp(pts[-1], zf)
        for k in range(count):
            drooping_branch(p, root, turn + k * math.tau / count, reach, droop, ti in needle_tiers)
    top = pts[-1]
    if broken:
        kit.spike(p["wood"], (top.x, top.y, top.z - 0.1), height=0.45, radius=0.1, lean=(0.1, 0.05))
    else:
        kit.spike(p["wood_dk"], (top.x, top.y, top.z - 0.15), height=0.55, radius=0.07, lean=(0.04, 0.0))
    if top_snow:
        blob(p["snow"], (top.x, top.y, top.z - 0.02), (0.5, 0.46, 0.34))


def frost_tree_a():
    """Pinheiro de três andares, metade dos galhos ainda com agulha."""
    snow_pine(4.9, ((0.03, 0.0, 0.34), (-0.05, 0.04, 0.33), (0.04, -0.02, 0.33)),
              ((0.28, 1.05, 4, 0.2, 0.55), (0.52, 0.85, 4, 1.0, 0.5), (0.74, 0.6, 3, 0.4, 0.4)), needle_tiers=(0, 1))


def frost_tree_b():
    """Pinheiro torto e quase pelado: poucos galhos, um deles quebrado para baixo."""
    snow_pine(5.0, ((-0.08, 0.05, 0.36), (0.1, 0.0, 0.3), (-0.03, 0.05, 0.32)),
              ((0.35, 1.0, 3, 0.7, 0.8), (0.6, 0.75, 3, 2.1, 0.5), (0.82, 0.5, 2, 0.1, 0.3)), needle_tiers=(2,))


def frost_tree_c():
    """Tronco partido no alto, galhos curtos pesados de neve."""
    snow_pine(5.0, ((0.05, 0.02, 0.36), (-0.03, -0.04, 0.32), (0.02, 0.03, 0.3)),
              ((0.3, 0.95, 4, 0.0, 0.5), (0.58, 0.7, 3, 0.9, 0.45)), needle_tiers=(0,), broken=True, top_snow=True)


def frost_stump():
    p = palette()
    cyl("root", p["wood_dk"], (0, 0, 0), 0.64, 0.2, sides=7, top_radius=0.46, bevel=0.0)
    cyl("stump", p["wood"], (0, 0, 0.18), 0.44, 0.5, sides=7, top_radius=0.38, bevel=0.0)
    cyl("stump_cut", p["wood_cut"], (0, 0, 0.66), 0.34, 0.03, sides=7, bevel=0.0)
    blob(p["snow"], (0.05, 0.02, 0.76), (0.78, 0.7, 0.3), sides=8, rings=4)
    for dx, dy in ((0.14, 0.05), (-0.12, 0.16), (0.0, -0.2)):
        kit.spike(p["wood_dk"], (dx, dy, 0.6), height=0.4, radius=0.09, lean=(dx * 0.5, dy * 0.5))
    blob(p["snow"], (0.45, -0.25, 0.1), (0.8, 0.6, 0.24))


# ---------------------------------------------------------------------------------------------------------
# "Arbustos" e "pedras"
# ---------------------------------------------------------------------------------------------------------


def frost_drift():
    """Monte de neve soprada contra uma cerca de estacas tortas (lugar do arbusto)."""
    p = palette()
    blob(p["snow_sh"], (0.0, 0.1, 0.1), (2.1, 1.3, 0.55), sides=10, rings=5)
    blob(p["snow"], (-0.1, 0.0, 0.3), (1.6, 0.95, 0.5), sides=10, rings=5, rot_z=0.2)
    blob(p["snow"], (0.55, -0.2, 0.28), (0.9, 0.7, 0.4), sides=8, rings=4)
    for x, tilt in ((-0.85, -0.18), (-0.3, 0.12), (0.3, -0.1), (0.85, 0.2)):
        h = 0.9 + 0.1 * (int(x * 10) % 2)
        beam("stake", p["wood_dk"], (x, 0.36, 0.0), (x + tilt, 0.36, h), thick=0.09)
        blob(p["snow"], (x + tilt, 0.36, h + 0.02), (0.22, 0.2, 0.1), sides=6, rings=3)
    for z in (0.35, 0.65):
        beam("fence_rail", p["wood"], (-0.9, 0.36, z), (0.9, 0.36, z + 0.05), thick=0.06)


def frost_sled():
    """Trenó carregado de caixas e coberto de neve (lugar do arbusto)."""
    p = palette()
    for y in (-0.4, 0.4):
        beam("runner", p["steel_dk"], (-1.0, y, 0.06), (0.9, y, 0.06), thick=0.09)
        beam("runner_tip", p["steel_dk"], (0.9, y, 0.06), (1.12, y, 0.28), thick=0.09)
        for x in (-0.6, 0.5):
            beam("knee", p["wood_dk"], (x, y, 0.06), (x, y, 0.22), thick=0.08)
    box("deck", p["wood"], (-0.05, 0, 0.2), (1.9, 1.0, 0.1), bevel=0.01)
    box("crate", p["wood_dk"], (-0.45, -0.15, 0.3), (0.6, 0.55, 0.45), bevel=0.02, rot_z=0.1)
    box("crate", p["wood"], (0.2, 0.15, 0.3), (0.55, 0.5, 0.4), bevel=0.02, rot_z=-0.2)
    box("crate_red", p["red"], (0.18, 0.13, 0.7), (0.34, 0.3, 0.26), bevel=0.02, rot_z=0.4)
    box("tarp", p["tarp"], (-0.45, -0.15, 0.75), (0.66, 0.6, 0.1), bevel=0.04, taper=0.9, taper_y=0.9, rot_z=0.1)
    blob(p["snow"], (-0.45, -0.15, 0.82), (0.76, 0.66, 0.2))
    blob(p["snow"], (0.18, 0.13, 0.84), (0.46, 0.4, 0.14))
    blob(p["snow_sh"], (-1.0, 0.0, 0.05), (0.9, 1.1, 0.16))


def facet_rock(p, center, radius, height, sides, turn, tone="ice", top="ice_lt"):
    cx, cy, cz = center
    cyl("boulder", p[tone], (cx, cy, cz), radius, height, sides=sides, top_radius=radius * 0.62, bevel=0.02, rot=("Z", turn))
    cyl("boulder_top", p[top], (cx, cy, cz + height), radius * 0.62, 0.05, sides=sides, top_radius=radius * 0.5, bevel=0.0, rot=("Z", turn))


def frost_ice_rocks():
    """Blocos de gelo azul pálido, facetados, com lascas pontudas e neve nos topos (lugar da pedra)."""
    p = palette()
    facet_rock(p, (0.0, 0.0, 0.0), 1.6, 1.15, 6, 0.3)
    facet_rock(p, (1.1, -0.7, 0.0), 1.0, 1.5, 5, 1.1, tone="ice_dk", top="ice")
    facet_rock(p, (-1.0, 0.8, 0.0), 0.9, 0.85, 5, 0.7, tone="ice_lt", top="snow")
    for pos, h, lean in (((0.3, 0.4, 1.05), 0.75, (0.12, 0.1)), ((-0.4, -0.3, 1.0), 0.55, (-0.1, 0.05)), ((1.1, -0.7, 1.4), 0.35, (0.05, -0.08))):
        kit.spike(p["ice_lt"], pos, height=h, radius=0.2, lean=lean)
    blob(p["snow"], (-0.2, 0.1, 1.18), (1.2, 1.0, 0.2))
    blob(p["snow"], (-1.0, 0.8, 0.86), (0.7, 0.6, 0.14))
    blob(p["snow_sh"], (0.1, 0.0, 0.05), (3.0, 2.2, 0.16))


def frost_supply_dump():
    """Depósito de suprimentos sob lona, preso com corda e meio soterrado (lugar da pedra)."""
    p = palette()
    box("pallet", p["wood_dk"], (0, 0, 0), (2.8, 2.0, 0.14), bevel=0.02)
    box("crates", p["wood"], (-0.55, 0.0, 0.12), (1.2, 1.4, 0.7), bevel=0.03)
    box("crates_hi", p["wood_dk"], (0.55, -0.1, 0.12), (1.0, 1.1, 0.95), bevel=0.03)
    box("tarp", p["tarp"], (0.0, 0.0, 0.6), (2.5, 1.7, 0.5), bevel=0.14, taper=0.62, taper_y=0.72)
    box("tarp_hi", p["tarp"], (0.55, -0.1, 0.9), (1.2, 1.2, 0.3), bevel=0.1, taper=0.7, taper_y=0.7)
    for x in (-0.5, 0.4):
        box("rope", p["wood_cut"], (x, 0.0, 0.62), (0.07, 1.78, 0.46), bevel=0.0, taper=0.75, taper_y=1.0)
    blob(p["snow"], (-0.3, 0.1, 1.0), (1.6, 1.2, 0.34))
    blob(p["snow"], (0.65, -0.1, 1.2), (0.9, 0.8, 0.22))
    box("barrel", p["red"], (1.2, 0.65, 0.12), (0.4, 0.4, 0.5), bevel=0.04)
    blob(p["snow_sh"], (1.2, 0.0, 0.05), (1.0, 2.0, 0.18))


def frost_log_pile():
    """Pilha de toras sob uma capa de neve (lugar da pedra)."""
    p = palette()
    blob(p["snow_sh"], (0.0, 0.0, 0.06), (3.2, 2.0, 0.2))
    layers = ((5, 0.0, 0.34), (4, 0.3, 0.76), (3, 0.62, 1.12))
    for li, (n, off, z) in enumerate(layers):
        for i in range(n):
            y = -0.85 + off + i * 0.34 + 0.0
            log_x(p, -1.2 + 0.1 * (i % 2), y, z, 0.17, 2.3, "wood" if (i + li) % 2 else "wood_dk")
    blob(p["snow"], (0.0, 0.0, 1.32), (2.4, 1.0, 0.28), sides=9, rings=4)
    blob(p["snow"], (0.2, -0.5, 0.78), (1.8, 0.4, 0.22))
    kit.spike(p["wood"], (1.0, 0.95, 0.15), height=0.7, radius=0.1, lean=(0.5, 0.0))


# ---------------------------------------------------------------------------------------------------------
# Peça central: cabeça de poço congelada na lagoa do meio
# ---------------------------------------------------------------------------------------------------------


def frost_wellhead():
    """Jorro de óleo que congelou no ar: coluna de gelo irregular, árvore de válvulas e rachaduras no gelo."""
    p = palette()
    cyl("mound", p["ice"], (0, 0, 0), 1.5, 0.34, sides=12, top_radius=1.15, bevel=0.0)
    blob(p["snow"], (0.0, 0.0, 0.34), (1.9, 1.7, 0.2), sides=10, rings=3)
    cyl("casing", p["steel"], (0, 0, 0.3), 0.26, 0.95, sides=10)
    for z in (0.55, 0.95):
        ring("flange", p["steel_dk"], (0, 0, z), 0.26, 0.09, thick=0.08, sides=10)
    beam("arm", p["steel"], (-0.75, 0, 1.12), (0.75, 0, 1.12), thick=0.15)
    for x in (-0.75, 0.75):
        cyl("wheel", p["red"], (x, -0.14, 1.12), 0.2, 0.05, sides=10, bevel=0.0, rot=("X", math.radians(90)))
        cyl("wheel_hub", p["steel_dk"], (x, -0.12, 1.12), 0.05, 0.1, sides=6, bevel=0.0, rot=("X", math.radians(90)))
        blob(p["snow"], (x, 0.0, 1.22), (0.34, 0.26, 0.1), sides=6, rings=3)
    cyl("cap", p["steel_dk"], (0, 0, 1.25), 0.2, 0.2, sides=8)
    # Coluna congelada: gomos de gelo de larguras diferentes, com lascas.
    cyl("column", p["ice"], (0, 0, 1.4), 0.5, 1.3, sides=6, top_radius=0.34, bevel=0.0)
    cyl("column2", p["ice_lt"], (0.05, 0.03, 2.6), 0.36, 1.1, sides=5, top_radius=0.2, bevel=0.0)
    cyl("column3", p["ice"], (0.0, 0.0, 3.6), 0.22, 0.7, sides=5, top_radius=0.08, bevel=0.0)
    kit.spike(p["ice_lt"], (0.0, 0.0, 4.2), height=0.7, radius=0.1, lean=(0.08, 0.04))
    for ang, z, h in ((0.3, 1.5, 1.4), (2.0, 1.7, 1.2), (3.6, 1.55, 1.3), (5.0, 1.9, 1.0), (1.1, 2.4, 0.9), (4.3, 2.6, 0.8)):
        kit.spike(p["ice_lt"], (math.cos(ang) * 0.34, math.sin(ang) * 0.34, z), height=h, radius=0.14,
                  lean=(math.cos(ang) * 0.5, math.sin(ang) * 0.5))
    for ang in (0.9, 2.6, 4.3):
        icicle(p["ice_lt"], math.cos(ang) * 0.4, math.sin(ang) * 0.4, 1.4, 0.5, 0.06)
    blob(p["snow"], (0.0, 0.0, 2.0), (0.55, 0.5, 0.14), sides=6, rings=3)
    # Rachaduras: linhas escuras chatas (<= 0.06) irradiando do poço pela lagoa, com um filete claro ao lado.
    rng = [(0.2, 6.4), (0.75, 5.0), (1.35, 6.8), (1.95, 4.8), (2.5, 6.2), (3.1, 5.4), (3.65, 6.6), (4.25, 4.6), (4.8, 6.0), (5.5, 5.2)]
    for ang, reach in rng:
        crack_line(p, ang, reach)
    for r, a0, a1 in ((3.2, 0.3, 1.3), (4.4, 3.0, 4.2), (2.4, 4.6, 5.9)):
        pts = [(math.cos(a) * r, math.sin(a) * r) for a in (a0 + (a1 - a0) * i / 5 for i in range(6))]
        for (x0, y0), (x1, y1) in itertools.pairwise(pts):
            flat_line(p["crack"], (x0, y0), (x1, y1), 0.05, 0.05)


def flat_line(material, a, b, width, z):
    d = Vector((b[0] - a[0], b[1] - a[1], 0.0))
    mid = (a[0] + d.x / 2, a[1] + d.y / 2, 0.0)
    box("crack", material, mid, (d.length + 0.02, width, z), bevel=0.0, rot_z=math.atan2(d.y, d.x))


def crack_line(p, ang, reach):
    """Rachadura em zigue-zague de ~1,0 até `reach` do centro, com um ramo curto."""
    pts = []
    for i in range(6):
        r = 1.0 + (reach - 1.0) * i / 5
        a = ang + 0.13 * (-1) ** i
        pts.append((math.cos(a) * r, math.sin(a) * r))
    for i, ((x0, y0), (x1, y1)) in enumerate(itertools.pairwise(pts)):
        flat_line(p["crack"], (x0, y0), (x1, y1), 0.16 * (1 - i / 6) + 0.06, 0.055)
        flat_line(p["ice_lt"], (x0 + 0.1, y0 - 0.06), (x1 + 0.1, y1 - 0.06), 0.05, 0.045)
    bx, by = pts[3]
    flat_line(p["crack"], (bx, by), (bx + math.cos(ang + 0.9) * 1.1, by + math.sin(ang + 0.9) * 1.1), 0.06, 0.05)


# ---------------------------------------------------------------------------------------------------------
# Decoração fora da muralha (5 kinds)
# ---------------------------------------------------------------------------------------------------------


def frost_derrick():
    """Kind 0, ~8,5 de altura: torre de perfuração de madeira encapada de gelo, casa de máquinas soterrada."""
    p = palette()
    box("pad", p["snow_sh"], (0, 0, 0), (3.6, 3.6, 0.2), bevel=0.08, taper=0.94, taper_y=0.94)
    kit.derrick(p["wood"], p["wood_dk"], None, (0, 0, 0.2), base=2.6, top=0.7, height=7.4)
    for z, w in ((0.9, 2.3), (2.6, 1.8), (4.3, 1.4)):
        box("ice_sheath", p["ice"], (0, 0, z), (w, w, 0.9), bevel=0.06, taper=0.78, taper_y=0.78)
        box("sheath_snow", p["snow"], (0, 0, z + 0.88), (w * 0.78, w * 0.78, 0.1), bevel=0.04)
    for z, w in ((2.4, 1.9), (4.1, 1.5), (5.8, 1.1)):
        box("platform", p["wood_dk"], (0, 0, z), (w, w, 0.12), bevel=0.01)
        box("platform_snow", p["snow"], (0, 0, z + 0.12), (w * 0.92, w * 0.92, 0.1), bevel=0.04)
        icicle_row(p["ice_lt"], -w / 2 + 0.1, w / 2 - 0.1, -w / 2, z, 5)
    box("crown", p["steel_dk"], (0, 0, 7.6), (1.0, 1.0, 0.25), bevel=0.02)
    prism("crown_roof", p["snow"], (0, 0, 7.85), (1.2, 1.2, 0.5), ridge=0.5)
    box("lamp_mast", p["steel_dk"], (0, 0, 8.3), (0.05, 0.05, 0.3), bevel=0.0)
    box("beacon", p["lamp"], (0, 0, 8.5), (0.18, 0.18, 0.16), bevel=0.0)
    box("shed", p["wood_dk"], (2.4, 0, 0.0), (1.8, 1.5, 1.2), bevel=0.03)
    prism("shed_roof", p["snow"], (2.4, 0, 1.2), (2.1, 1.8, 0.7), ridge=0.5)
    box("shed_door", p["red"], (2.4, -0.76, 0.0), (0.5, 0.04, 0.85), bevel=0.0)
    blob(p["snow"], (2.4, 0.85, 0.15), (1.8, 0.6, 0.4))
    icicle_row(p["ice_lt"], 1.6, 3.2, -0.9, 1.25, 6, base_len=0.3)
    cyl("stack", p["steel_dk"], (3.0, 0.4, 1.4), 0.12, 1.1, sides=8, bevel=0.0)
    blob(p["snow"], (3.0, 0.4, 2.5), (0.34, 0.3, 0.14), sides=6, rings=3)


def frost_tank():
    """Kind 1, redondo e baixo (~3,5 x 3): tanque aquecido sob a neve com cano de vapor e válvula."""
    p = palette()
    r = 1.75
    cyl("foot", p["stone_dk"], (0, 0, 0), r * 1.08, 0.18, sides=16)
    cyl("shell", p["steel"], (0, 0, 0.16), r, 1.9, sides=16, bevel=0.02)
    for z, tone in ((0.6, "rust"), (1.25, "hazard")):
        ring("band", p[tone], (0, 0, z), r, 0.1, sides=16)
    cyl("roof", p["steel_dk"], (0, 0, 2.06), r * 0.99, 0.45, sides=16, top_radius=0.3, bevel=0.0)
    cyl("roof_snow", p["snow"], (0, 0, 2.2), r * 0.96, 0.38, sides=16, top_radius=0.22, bevel=0.0)
    for ang in (0.5, 2.2, 3.9, 5.4):
        blob(p["snow"], (math.cos(ang) * 1.45, math.sin(ang) * 1.45, 1.95), (0.9, 0.7, 0.34), rot_z=ang)
    icicle_row(p["ice_lt"], -1.0, 1.0, -r + 0.05, 1.5, 6, base_len=0.35)
    # Cano de vapor lateral com puffs brancos: o vapor tem portador (a tubulação) e a cor é branco quente.
    pipe = [(r - 0.2, 0.0, 1.5), (r + 0.5, 0.0, 1.5), (r + 0.5, 0.0, 2.5)]
    kit.pipe_run(p["lag"], p["steel_dk"], pipe, radius=0.12)
    cyl("vent", p["steel_dk"], (r + 0.5, 0.0, 2.45), 0.16, 0.16, sides=8)
    for z, s in ((2.75, 0.36), (3.05, 0.5), (3.4, 0.4)):
        blob(p["snow"], (r + 0.55 + 0.08 * (z - 2.75), 0.0, z), (s, s, s * 0.8), sides=7, rings=4)
    box("valve", p["red"], (-r - 0.15, 0, 0.3), (0.34, 0.34, 0.34), bevel=0.04)
    box("door_hatch", p["steel_dk"], (0, -r + 0.02, 0.2), (0.8, 0.12, 1.0), bevel=0.0)
    box("door_snow", p["snow"], (0, -r - 0.1, 0.1), (1.3, 0.5, 0.3), bevel=0.1)


def frost_mast():
    """Kind 2, ponto de luz de ~6: mastro de sinal com lampião laranja, bandeira vermelha e braseiro no pé."""
    p = palette()
    box("base", p["stone_dk"], (0, 0, 0), (1.1, 1.1, 0.3), bevel=0.05, taper=0.8, taper_y=0.8)
    blob(p["snow"], (0.0, 0.0, 0.3), (1.3, 1.3, 0.28), sides=8, rings=3)
    cyl("pole", p["wood_dk"], (0, 0, 0.25), 0.11, 5.2, sides=6, top_radius=0.07, bevel=0.0)
    for sgn in (-1, 1):
        beam("guy", p["steel_dk"], (0, 0, 4.4), (sgn * 1.1, sgn * 0.35, 0.1), thick=0.02)
        box("guy_peg", p["wood"], (sgn * 1.1, sgn * 0.35, 0.0), (0.12, 0.12, 0.3), bevel=0.0)
    beam("crossarm", p["wood"], (-0.55, 0, 5.0), (0.55, 0, 5.0), thick=0.11)
    lantern(p, (0.5, 0, 4.55), 0.26)
    lantern(p, (-0.5, 0, 4.55), 0.2)
    box("flag_pole", p["steel_dk"], (0, 0, 5.4), (0.04, 0.04, 0.9), bevel=0.0)
    box("flag", p["red"], (0.28, 0, 5.85), (0.5, 0.03, 0.32), bevel=0.0)
    box("flag_tail", p["red"], (0.62, 0, 5.9), (0.2, 0.03, 0.14), bevel=0.0)
    blob(p["snow"], (0.0, 0.0, 5.45), (0.3, 0.3, 0.16), sides=6, rings=3)
    # Braseiro no pé: tigela de ferro com brasa e chama.
    cyl("bowl", p["steel_dk"], (0.62, -0.55, 0.3), 0.14, 0.2, sides=8, top_radius=0.26, bevel=0.0)
    kit.flame(p["fire_core"], p["fire"], (0.62, -0.55, 0.5), size=0.24)


def frost_pipe_run():
    """Kind 3, trecho de 8 ao longo de x (x de -4 a 4): cano de aquecimento forrado sobre cavaletes com neve."""
    p = palette()
    z = 0.95
    cyl("pipe", p["lag"], (-4.0, 0.0, z), 0.42, 8.0, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
    for x in (-3.0, -0.9, 1.2, 3.2):
        cyl("strap", p["steel_dk"], (x, 0.0, z), 0.45, 0.14, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
    for x in (-3.5, 0.0, 3.5):
        for y in (-0.35, 0.35):
            beam("trestle_leg", p["wood_dk"], (x, y * 1.5, 0.0), (x, y * 0.4, z - 0.3), thick=0.12)
        beam("trestle_bar", p["wood"], (x, -0.5, z - 0.38), (x, 0.5, z - 0.38), thick=0.14)
        blob(p["snow"], (x, 0.0, 0.05), (1.0, 1.4, 0.24))
    for x in (-2.0, 1.8):
        blob(p["snow"], (x, 0.0, z + 0.42), (1.7, 0.6, 0.2), sides=8, rings=4)
    box("valve_stem", p["steel_dk"], (-1.0, 0.0, z + 0.4), (0.1, 0.1, 0.4), bevel=0.0)
    cyl("valve_wheel", p["red"], (-1.0, 0.0, z + 0.78), 0.2, 0.05, sides=10, bevel=0.0)
    box("hazard_wrap", p["hazard"], (2.4, 0.0, z - 0.05), (0.32, 0.9, 0.9), bevel=0.0, taper=0.98, taper_y=0.98)
    for x in (-1.5, 2.6):
        icicle_row(p["ice_lt"], x - 0.5, x + 0.5, 0.0, z - 0.3, 3, base_len=0.28, r=0.04)


def frost_telegraph():
    """Kind 4, torre fina de ~7: poste de telégrafo com travessas, isoladores e fios caindo para os lados."""
    p = palette()
    box("base", p["stone_dk"], (0, 0, 0), (1.0, 1.0, 0.3), bevel=0.05, taper=0.8, taper_y=0.8)
    for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        beam("brace", p["wood_dk"], (sx * 0.9, sy * 0.9, 0.0), (sx * 0.08, sy * 0.08, 1.6), thick=0.1)
    cyl("pole", p["wood"], (0, 0, 0.2), 0.14, 6.6, sides=6, top_radius=0.09, bevel=0.0)
    for z, w in ((6.4, 1.4), (5.6, 1.1)):
        beam("crossarm", p["wood_dk"], (0, -w / 2, z), (0, w / 2, z), thick=0.1)
        for y in (-w / 2 + 0.08, 0.0, w / 2 - 0.08):
            cyl("insulator", p["ice_lt"], (0, y, z + 0.05), 0.07, 0.2, sides=6, top_radius=0.05, bevel=0.0)
            for sgn in (-1, 1):
                beam("wire", p["steel_dk"], (0, y, z + 0.2), (sgn * 1.2, y, z - 0.35), thick=0.02)
    blob(p["snow"], (0.0, 0.0, 6.85), (0.34, 0.34, 0.2), sides=6, rings=3)
    box("box", p["steel_dk"], (0.2, 0.0, 2.2), (0.26, 0.2, 0.5), bevel=0.02)
    box("box_lamp", p["lamp"], (0.34, 0.0, 2.55), (0.04, 0.1, 0.1), bevel=0.0)
    blob(p["snow"], (0.0, 0.0, 0.3), (1.5, 1.5, 0.28), sides=8, rings=3)
    box("sign", p["red"], (-0.16, 0.0, 3.2), (0.04, 0.3, 0.3), bevel=0.0)
    icicle_row(p["ice_lt"], -0.5, 0.5, -0.5, 6.2, 3, base_len=0.18, r=0.03)


# ---------------------------------------------------------------------------------------------------------
# Bichos (olham para +x; o jogo escala pela maior dimensão)
# ---------------------------------------------------------------------------------------------------------


def wing_pair(material, tip_material, root_x, span, chord, z, sweep=0.0):
    """Par de asas abertas: painel principal e ponta escura, vistos de cima."""
    for s in (-1, 1):
        blob(material, (root_x - sweep * 0.3, s * span * 0.36, z), (chord, span * 0.76, 0.07), sides=8, rings=3)
        blob(tip_material, (root_x - sweep, s * span * 0.62, z + 0.01), (chord * 0.7, span * 0.36, 0.07), sides=6, rings=3)


def frost_hare():
    """Lebre-do-ártico (coelho): corpo cinza-claro, orelhas longas com ponta escura, rabo branco."""
    c = {"fur": mat("hare_fur", 0xBBC0C6), "belly": mat("hare_belly", 0xE6EAEE), "tip": mat("hare_tip", 0x2A2D32), "eye": mat("hare_eye", 0x15171A)}
    blob(c["fur"], (0.0, 0.0, 0.22), (0.58, 0.3, 0.32))
    blob(c["fur"], (-0.2, 0.0, 0.26), (0.34, 0.34, 0.36))
    blob(c["belly"], (0.05, 0.0, 0.1), (0.4, 0.22, 0.12))
    blob(c["fur"], (0.34, 0.0, 0.3), (0.26, 0.2, 0.2))
    for s in (-1, 1):
        beam("ear", c["fur"], (0.3, s * 0.05, 0.38), (0.12, s * 0.07, 0.7), thick=0.065)
        beam("ear_tip", c["tip"], (0.14, s * 0.07, 0.66), (0.1, s * 0.07, 0.72), thick=0.07)
        box("eye", c["eye"], (0.43, s * 0.09, 0.33), (0.04, 0.03, 0.04), bevel=0.0)
        box("foot", c["fur"], (0.22, s * 0.1, 0.0), (0.2, 0.07, 0.07), bevel=0.01)
        box("hind", c["fur"], (-0.18, s * 0.14, 0.0), (0.3, 0.08, 0.08), bevel=0.01)
    blob(c["belly"], (-0.4, 0.0, 0.3), (0.16, 0.16, 0.16), sides=6, rings=3)
    box("nose", c["tip"], (0.47, 0.0, 0.3), (0.04, 0.05, 0.04), bevel=0.0)


def frost_lemming():
    """Lemingue (lagarto): bolinha ocre com listra escura nas costas, orelhas e focinho curtos."""
    c = {"fur": mat("lem_fur", 0xAD7B40), "stripe": mat("lem_stripe", 0x4A3626), "belly": mat("lem_belly", 0xE2CFA6), "eye": mat("lem_eye", 0x15171A)}
    blob(c["fur"], (0.0, 0.0, 0.13), (0.42, 0.3, 0.26))
    blob(c["stripe"], (-0.02, 0.0, 0.25), (0.34, 0.08, 0.05), sides=6, rings=3)
    blob(c["belly"], (0.02, 0.0, 0.04), (0.3, 0.2, 0.08))
    blob(c["fur"], (0.24, 0.0, 0.15), (0.2, 0.18, 0.18))
    for s in (-1, 1):
        blob(c["stripe"], (0.18, s * 0.09, 0.26), (0.07, 0.06, 0.07), sides=5, rings=3)
        box("eye", c["eye"], (0.33, s * 0.06, 0.18), (0.03, 0.03, 0.03), bevel=0.0)
        box("foot", c["stripe"], (0.12, s * 0.12, 0.0), (0.1, 0.05, 0.04), bevel=0.0)
    box("nose", c["stripe"], (0.35, 0.0, 0.14), (0.03, 0.04, 0.03), bevel=0.0)
    blob(c["stripe"], (-0.24, 0.0, 0.1), (0.1, 0.06, 0.06), sides=5, rings=3)


def frost_ptarmigan():
    """Lagópode (sapo): gorducho, costas mosqueadas, peito branco e sobrancelha vermelha."""
    c = {"back": mat("ptar_back", 0x9B8F82), "white": mat("ptar_white", 0xF1F1EE), "dark": mat("ptar_dark", 0x25272B), "comb": mat("ptar_comb", 0xD2382A)}
    blob(c["back"], (-0.02, 0.0, 0.17), (0.4, 0.3, 0.26))
    blob(c["white"], (0.06, 0.0, 0.12), (0.3, 0.26, 0.2))
    blob(c["white"], (0.2, 0.0, 0.26), (0.16, 0.14, 0.16))
    box("beak", c["dark"], (0.3, 0.0, 0.26), (0.06, 0.04, 0.04), bevel=0.0)
    for s in (-1, 1):
        box("comb", c["comb"], (0.22, s * 0.045, 0.34), (0.06, 0.02, 0.03), bevel=0.0)
        blob(c["back"], (-0.02, s * 0.14, 0.19), (0.26, 0.08, 0.14), sides=6, rings=3)
        box("foot", c["white"], (0.1, s * 0.07, 0.0), (0.1, 0.05, 0.05), bevel=0.0)
    box("tail", c["dark"], (-0.26, 0.0, 0.2), (0.1, 0.14, 0.05), bevel=0.0, taper=0.6)


def frost_fox():
    """Raposa-do-ártico em tom de ferrugem (rato): focinho fino, patas escuras, cauda cheia de ponta branca."""
    c = {"fur": mat("fox_fur", 0xD9772B), "white": mat("fox_white", 0xF4EEE4), "dark": mat("fox_dark", 0x2A2018), "eye": mat("fox_eye", 0x15171A)}
    blob(c["fur"], (0.0, 0.0, 0.22), (0.56, 0.22, 0.24))
    blob(c["white"], (0.03, 0.0, 0.13), (0.4, 0.15, 0.1))
    blob(c["fur"], (0.34, 0.0, 0.3), (0.2, 0.18, 0.18))
    blob(c["white"], (0.5, 0.0, 0.27), (0.18, 0.1, 0.09), sides=6, rings=3)
    box("nose", c["dark"], (0.6, 0.0, 0.28), (0.04, 0.05, 0.04), bevel=0.0)
    for s in (-1, 1):
        kit.spike(c["fur"], (0.32, s * 0.06, 0.38), height=0.17, radius=0.05, lean=(-0.02, s * 0.02))
        box("eye", c["eye"], (0.43, s * 0.06, 0.33), (0.03, 0.03, 0.03), bevel=0.0)
        for x in (0.2, -0.2):
            box("leg", c["dark"], (x, s * 0.08, 0.0), (0.06, 0.06, 0.16), bevel=0.0)
    blob(c["fur"], (-0.42, 0.0, 0.24), (0.42, 0.14, 0.14), sides=7, rings=3)
    blob(c["white"], (-0.6, 0.0, 0.24), (0.14, 0.12, 0.12), sides=6, rings=3)


def frost_owl():
    """Coruja-das-neves (pássaro): branca barrada, asas abertas de ponta escura, olho amarelo."""
    c = {"white": mat("owl_white", 0xF3F5F6), "bar": mat("owl_bar", 0x3A3F46), "eye": mat("owl_eye", 0xFFC400), "beak": mat("owl_beak", 0x1B1D22)}
    blob(c["white"], (0.0, 0.0, 0.0), (0.5, 0.3, 0.26))
    blob(c["white"], (0.26, 0.0, 0.06), (0.24, 0.24, 0.24))
    for s in (-1, 1):
        box("eye", c["eye"], (0.36, s * 0.09, 0.1), (0.04, 0.05, 0.06), bevel=0.0)
        box("bar", c["bar"], (0.0, s * 0.12, 0.13), (0.3, 0.04, 0.02), bevel=0.0)
    box("beak", c["beak"], (0.39, 0.0, 0.04), (0.05, 0.04, 0.05), bevel=0.0)
    wing_pair(c["white"], c["bar"], 0.0, 0.8, 0.42, 0.04, sweep=0.1)
    box("tail", c["white"], (-0.34, 0.0, 0.0), (0.2, 0.18, 0.04), bevel=0.0)
    box("tail_bar", c["bar"], (-0.43, 0.0, 0.02), (0.04, 0.18, 0.02), bevel=0.0)


def frost_raven():
    """Corvo (pombo): preto brilhante, asas abertas azuladas, bico grosso."""
    c = {"body": mat("raven_body", 0x1D2026), "wing": mat("raven_wing", 0x303A4C), "beak": mat("raven_beak", 0x6A6C70), "eye": mat("raven_eye", 0xD8E2EC)}
    blob(c["body"], (0.0, 0.0, 0.0), (0.52, 0.22, 0.2))
    blob(c["body"], (0.28, 0.0, 0.04), (0.2, 0.17, 0.17))
    box("beak", c["beak"], (0.42, 0.0, 0.03), (0.14, 0.06, 0.06), bevel=0.01, taper=0.5, taper_y=0.7)
    for s in (-1, 1):
        box("eye", c["eye"], (0.34, s * 0.07, 0.08), (0.03, 0.025, 0.03), bevel=0.0)
    wing_pair(c["wing"], c["body"], 0.02, 0.9, 0.36, 0.03, sweep=0.14)
    box("tail", c["body"], (-0.4, 0.0, 0.0), (0.28, 0.16, 0.04), bevel=0.0, taper=0.6)


# ---------------------------------------------------------------------------------------------------------
# Castelo A (oeste): Northern "Thaw Watch", forte de colina de madeira escura e pedra cinza preso no gelo
# ---------------------------------------------------------------------------------------------------------


def wall_frame(a, b, fixed, along_x, out):
    """Devolve pos(t, off) -> (x, y): t ao longo da cortina a partir do meio, off para fora (out = +-1)."""
    mid = (a + b) / 2
    if along_x:
        return lambda t, off: (mid + t, fixed + out * off)
    return lambda t, off: (fixed + out * off, mid + t)


def log_curtain(p, a, b, fixed, along_x, out, height=1.12, thick=0.74):
    """Cortina de toras sobre embasamento de pedra em talude; capa de neve no topo e pingentes."""
    pos = wall_frame(a, b, fixed, along_x, out)
    length = abs(b - a)
    cx, cy = pos(0, 0)

    def dims(l, t, h):
        return (l, t, h) if along_x else (t, l, h)

    tp = (1.0, 0.8) if along_x else (0.8, 1.0)
    box("footing", p["stone_dk"], (cx, cy, 0.0), dims(length, thick * 1.14, 0.3), bevel=0.04)
    box("curtain_stone", p["stone"], (cx, cy, 0.14), dims(length, thick, 0.62), bevel=0.04, taper=tp[0], taper_y=tp[1])
    box("curtain_wood", p["wood_dk"], (cx, cy, 0.7), dims(length, thick * 0.76, height - 0.7), bevel=0.02)
    n = max(int(length / 0.2), 2)
    for i in range(n):
        x, y = pos(-length / 2 + 0.1 + i * (length - 0.2) / (n - 1), out * thick * 0.4)
        cyl("log", p["wood"] if i % 2 else p["wood_dk"], (x, y, 0.6), 0.075, height - 0.5, sides=6, bevel=0.0)
    box("cap", p["snow"], (cx, cy, height - 0.02), dims(length + 0.04, thick * 0.96, 0.15), bevel=0.05, taper=0.97, taper_y=0.97)
    for t in (-0.38, 0.0, 0.4):
        x, y = pos(t * length * 0.6, 0.0)
        blob(p["snow"], (x, y, height + 0.14), (0.7, 0.5, 0.18) if along_x else (0.5, 0.7, 0.18))
    for i in range(int(length / 0.34)):
        x, y = pos(-length / 2 + 0.2 + i * 0.34, out * thick * 0.43)
        icicle(p["ice_lt"], x, y, height - 0.02, 0.2 + 0.1 * (i % 3), 0.04)


def round_bastion(p, pos, radius, height, roof_h, windows_toward=None):
    """Bastião redondo de pedra com cinta de toras, teto cônico de madeira e neve acumulada no cone."""
    x, y = pos
    cyl("bastion_foot", p["stone_dk"], (x, y, 0.0), radius * 1.14, 0.24, sides=10, bevel=0.03)
    cyl("bastion", p["stone"], (x, y, 0.2), radius * 1.04, height, sides=10, top_radius=radius * 0.9, bevel=0.03)
    ring("bastion_log_band", p["wood_dk"], (x, y, 0.2 + height * 0.7), radius * 0.86, 0.22, thick=0.07, sides=10)
    cyl("eave", p["wood_dk"], (x, y, 0.2 + height), radius * 1.06, 0.1, sides=10, top_radius=radius * 1.0, bevel=0.0)
    base = 0.28 + height
    cyl("roof", p["wood_dk"], (x, y, base), radius * 1.02, roof_h, sides=10, top_radius=0.0, bevel=0.0)
    f0 = 0.3  # a neve cobre o cone do terço de cima para cima e deixa a madeira escura aparecer no beiral
    cyl("roof_snow", p["snow"], (x, y, base + roof_h * f0), radius * 1.02 * (1 - f0) + 0.05, roof_h * (1 - f0) + 0.06, sides=10, top_radius=0.0, bevel=0.0)
    for i in range(10):
        a = i * math.tau / 10 + 0.15
        icicle(p["ice_lt"], x + math.cos(a) * radius, y + math.sin(a) * radius, base + 0.06, 0.18 + 0.1 * (i % 3), 0.04)
    if windows_toward is not None:
        a = math.atan2(windows_toward[1], windows_toward[0])
        box("slit", p["lamp"], (x + math.cos(a) * radius * 0.98, y + math.sin(a) * radius * 0.98, 0.2 + height * 0.45), (0.1, 0.1, 0.34), bevel=0.0, rot_z=a)


def beacon_tower(p, pos, base_z):
    """Coroa: sinal de fogo de toras sobre o bastião de trás, com cesto de ferro e a chama mais alta."""
    x, y = pos
    cyl("beacon_deck", p["wood_dk"], (x, y, base_z), 0.88, 0.12, sides=10, bevel=0.0)
    cyl("beacon_snow", p["snow"], (x, y, base_z + 0.1), 0.82, 0.07, sides=10, bevel=0.0)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        beam("beacon_leg", p["wood"], (x + sx * 0.5, y + sy * 0.5, base_z + 0.1), (x + sx * 0.22, y + sy * 0.22, base_z + 1.55), thick=0.1)
    box("beacon_ring", p["wood_dk"], (x, y, base_z + 1.2), (0.7, 0.7, 0.08), bevel=0.0)
    cyl("basket", p["steel_dk"], (x, y, base_z + 1.5), 0.2, 0.3, sides=8, top_radius=0.4, bevel=0.0)
    cyl("ember", p["lamp"], (x, y, base_z + 1.78), 0.34, 0.05, sides=8, bevel=0.0)
    kit.flame(p["fire_core"], p["fire"], (x, y, base_z + 1.8), size=0.55)
    kit.flame(p["fire_core"], p["fire"], (x + 0.15, y - 0.12, base_z + 1.8), size=0.34)
    for i in range(4):
        a = i * math.tau / 4 + 0.6
        blob(p["snow"], (x + math.cos(a) * 0.55, y + math.sin(a) * 0.55, base_z + 0.2), (0.4, 0.34, 0.16))


def longhouse(p, kx):
    """Menagem em degraus: pedra, salão de toras e teto de duas águas muito íngreme, com chaminé e empenas."""
    box("keep_stone", p["stone"], (kx, 0, 0.18), (2.6, 2.1, 0.92), bevel=0.05, taper=0.94, taper_y=0.94)
    box("keep_ledge", p["snow"], (kx, 0, 1.08), (2.5, 2.0, 0.1), bevel=0.04)
    box("hall_log", p["wood_dk"], (kx - 0.1, 0, 1.14), (2.1, 1.55, 0.66), bevel=0.03)
    for i in range(9):
        cyl("hall_post", p["wood"], (kx + 0.97, -0.7 + i * 0.175, 1.14), 0.065, 0.62, sides=6, bevel=0.0)
    prism("roof", p["wood_dk"], (kx - 0.1, 0, 1.78), (1.95, 2.5, 1.0), ridge=0.5, rot_z=math.pi / 2)
    for i, x in enumerate((kx - 0.95, kx - 0.1, kx + 0.75)):
        prism("roof_snow", p["snow"], (x, 0, 1.84), (1.95, 0.8 if i != 1 else 0.7, 1.0), ridge=0.5, rot_z=math.pi / 2, bevel=0.02)
    for s in (-1, 1):
        beam("finial", p["wood"], (kx + 1.15, 0, 2.5), (kx + 1.42, s * 0.2, 2.92), thick=0.08)
        beam("finial", p["wood"], (kx - 1.35, 0, 2.5), (kx - 1.62, s * 0.2, 2.92), thick=0.08)
        icicle_row(p["ice_lt"], kx - 1.0, kx + 1.0, s * 1.0, 1.82, 6, base_len=0.25)
    box("chimney", p["stone_dk"], (kx - 0.65, 0.4, 2.0), (0.34, 0.34, 0.85), bevel=0.03)
    box("chimney_cap", p["snow"], (kx - 0.65, 0.4, 2.82), (0.42, 0.42, 0.08), bevel=0.02)
    for y in (-0.55, 0.0, 0.55):
        kit.window(p["steel_dk"], p["lamp"], (kx + 1.3, y, 0.62), "x+", w=0.14, h=0.32)
    for t in (-0.4, 0.4):
        kit.window(p["steel_dk"], p["lamp"], (kx + t, 1.05, 0.62), "y+", w=0.14, h=0.3)
        kit.window(p["steel_dk"], p["lamp"], (kx + t, -1.05, 0.62), "y-", w=0.14, h=0.3)


def thaw_watch():
    """Northern, "Thaw Watch": forte de colina de toras e pedra, glacis de gelo, menagem de salão e sinal de fogo."""
    p = palette()
    half = 2.45
    box("glacis", p["ice"], (0, 0, 0), (half * 2 + 0.4, half * 2 + 0.4, 0.22), bevel=0.06, taper=0.95, taper_y=0.95)
    box("yard", p["snow"], (0, 0, 0.2), (half * 2 - 0.5, half * 2 - 0.5, 0.08), bevel=0.03)
    w = 2.0
    for along_x, fixed, out in ((True, w, 1), (True, -w, -1), (False, -w, -1)):
        log_curtain(p, -w + 0.7, w - 0.7, fixed, along_x, out)
    log_curtain(p, -w + 0.7, -0.75, w, False, 1)
    log_curtain(p, 0.75, w - 0.7, w, False, 1)
    # Glacis de gelo encostado nas cortinas: cunhas azuis claras.
    for sgn in (-1, 1):
        box("ice_slope", p["ice_lt"], (0.0, sgn * (w + 0.62), 0.0), (2 * w - 1.5, 0.5, 0.42), bevel=0.05, taper_y=0.35)
        box("ice_slope_foot", p["ice"], (0.0, sgn * (w + 0.82), 0.0), (2 * w - 1.3, 0.38, 0.22), bevel=0.04)
    box("ice_slope", p["ice_lt"], (-w - 0.62, 0.0, 0.0), (0.5, 2 * w - 1.5, 0.42), bevel=0.05, taper=0.35)
    # Bastiões para fora da muralha, de portes e roupas diferentes.
    round_bastion(p, (w + 0.15, w + 0.15), 0.98, 1.45, 0.95, windows_toward=(1, 0))
    round_bastion(p, (w + 0.1, -w - 0.1), 0.88, 1.25, 0.8, windows_toward=(1, 0))
    round_bastion(p, (-w - 0.05, -w - 0.05), 1.04, 1.5, 1.05)
    cyl("nw_foot", p["stone_dk"], (-w - 0.05, w + 0.05, 0.0), 1.2, 0.24, sides=10, bevel=0.03)
    cyl("nw_tower", p["stone"], (-w - 0.05, w + 0.05, 0.2), 1.08, 1.5, sides=10, top_radius=0.95, bevel=0.03)
    ring("nw_band", p["wood_dk"], (-w - 0.05, w + 0.05, 1.2), 0.9, 0.22, thick=0.07, sides=10)
    beacon_tower(p, (-w - 0.05, w + 0.05), 1.7)
    # Portaria saliente: bloco de pedra, porta de toras com cintas de ferro, lampiões e telhado nevado.
    gx = w + 0.14
    box("gate_block", p["stone"], (gx, 0, 0.1), (1.0, 1.6, 1.28), bevel=0.04, taper=0.9, taper_y=0.92)
    box("gate_door", p["wood_dk"], (gx + 0.46, 0, 0.14), (0.08, 0.84, 0.98), bevel=0.0)
    for z in (0.35, 0.8):
        box("gate_strap", p["steel_dk"], (gx + 0.51, 0, z), (0.03, 0.86, 0.07), bevel=0.0)
    for s in (-1, 1):
        box("gate_post", p["wood"], (gx + 0.46, s * 0.55, 0.1), (0.14, 0.14, 1.2), bevel=0.01)
        lantern(p, (gx + 0.52, s * 0.55, 1.28), 0.18)
    prism("gate_roof", p["wood_dk"], (gx, 0, 1.36), (1.4, 1.2, 0.55), ridge=0.5, rot_z=math.pi / 2)
    prism("gate_roof_snow", p["snow"], (gx, 0, 1.4), (1.4, 0.7, 0.55), ridge=0.5, rot_z=math.pi / 2, bevel=0.02)
    box("pennant", p["red"], (gx + 0.62, 0.0, 1.65), (0.03, 0.3, 0.2), bevel=0.0)
    longhouse(p, -0.55)
    # Pátio: pedra rúnica com runas acesas, trenó de carga e pilha de lenha.
    box("runestone", p["stone_lt"], (1.0, -0.95, 0.2), (0.5, 0.2, 1.05), bevel=0.04, taper=0.7, taper_y=0.8, rot_z=0.5)
    for z in (0.5, 0.8):
        box("rune", p["lamp"], (0.9, -1.0, z), (0.08, 0.04, 0.1), bevel=0.0, rot_z=0.5)
    blob(p["snow"], (1.0, -0.95, 1.25), (0.4, 0.2, 0.1), sides=6, rings=3)
    for y in (0.82, 1.14):
        beam("sled_runner", p["steel_dk"], (0.7, y, 0.26), (1.55, y, 0.26), thick=0.05)
    box("sled_bed", p["wood"], (1.12, 0.98, 0.3), (0.8, 0.5, 0.06), bevel=0.0)
    box("sled_crate", p["wood_dk"], (1.0, 0.98, 0.36), (0.36, 0.34, 0.26), bevel=0.02)
    blob(p["snow"], (1.0, 0.98, 0.64), (0.4, 0.38, 0.1), sides=6, rings=3)
    for i, (dy, z) in enumerate(((0.0, 0.0), (0.2, 0.0), (0.1, 0.17))):
        cyl("firewood", p["wood"] if i else p["wood_dk"], (1.55, -0.1 + dy + 0.02, 0.28 + z), 0.08, 0.4, sides=6, bevel=0.0, rot=("Y", math.radians(90)))


# ---------------------------------------------------------------------------------------------------------
# Castelo B (leste): fortaleza da estação de perfuração, cúpulas de pressão e caldeira
# ---------------------------------------------------------------------------------------------------------


def steam_puffs(p, x, y, z, scale=1.0):
    for i, s in enumerate((0.3, 0.42, 0.34)):
        blob(p["snow"], (x + 0.06 * i, y, z + 0.28 * i * scale), (s * scale, s * scale, s * scale * 0.8), sides=7, rings=4)


def plate_wall(p, a, b, fixed, along_x, out, height=1.15, thick=0.64):
    """Cortina de chapa de aço em talude, costuras verticais, convés coberto de neve e pingentes."""
    pos = wall_frame(a, b, fixed, along_x, out)
    length = abs(b - a)
    cx, cy = pos(0, 0)

    def dims(l, t, h):
        return (l, t, h) if along_x else (t, l, h)

    tp = (1.0, 0.76) if along_x else (0.76, 1.0)
    box("wall_foot", p["steel_dk"], (cx, cy, 0.0), dims(length, thick * 1.2, 0.2), bevel=0.04)
    box("wall", p["steel"], (cx, cy, 0.12), dims(length, thick, height - 0.12), bevel=0.03, taper=tp[0], taper_y=tp[1])
    box("wall_band", p["rust"], (cx, cy, 0.62), dims(length, thick * 0.9, 0.1), bevel=0.0)
    for i in range(int((length - 0.2) / 0.45) + 1):
        x, y = pos(-length / 2 + 0.1 + i * 0.45, out * thick * 0.47)
        box("seam", p["steel_dk"], (x, y, 0.2), dims(0.05, 0.05, height - 0.4), bevel=0.0)
    box("deck", p["snow"], (cx, cy, height - 0.02), dims(length, thick * 0.8, 0.12), bevel=0.04)
    for k in range(3):
        x, y = pos(-length * 0.32 + k * length * 0.32, 0.0)
        blob(p["snow"], (x, y, height + 0.1), (0.6, 0.4, 0.16) if along_x else (0.4, 0.6, 0.16))
    for i in range(int(length / 0.4)):
        x, y = pos(-length / 2 + 0.15 + i * 0.4, out * thick * 0.4)
        icicle(p["ice_lt"], x, y, height - 0.02, 0.14 + 0.08 * (i % 3), 0.035)


def pressure_dome(p, pos, radius, drum_h, squash=0.7):
    """Bastião: tambor de aço com cintas e rebites, cúpula de pressão e neve acumulada no alto."""
    x, y = pos
    cyl("dome_foot", p["steel_dk"], (x, y, 0.0), radius * 1.12, 0.22, sides=12, bevel=0.03)
    cyl("drum", p["steel"], (x, y, 0.2), radius * 1.04, drum_h, sides=12, top_radius=radius * 0.98, bevel=0.02)
    ring("drum_hazard", p["hazard"], (x, y, 0.4), radius * 1.02, 0.12, sides=12)
    ring("drum_band", p["rust"], (x, y, 0.2 + drum_h * 0.62), radius * 1.0, 0.1, sides=12)
    top = 0.2 + drum_h
    ring("dome_ring", p["steel_dk"], (x, y, top), radius * 1.0, 0.1, thick=0.06, sides=12)
    for i in range(12):
        a = i * math.tau / 12
        box("rivet", p["steel_dk"], (x + math.cos(a) * radius, y + math.sin(a) * radius, top + 0.08), (0.08, 0.08, 0.07), bevel=0.0, rot_z=a)
    dome("dome", p["steel"], (x, y, top + 0.05), radius * 0.98, squash=squash, sides=12)
    dome("dome_snow", p["snow"], (x, y, top + 0.05 + 0.3 * radius), radius * 0.82, squash=squash * 0.8, sides=10)
    cyl("dome_hatch", p["red"], (x, y, top + radius * squash), 0.1, 0.06, sides=6, bevel=0.0)
    for i in range(7):
        a = i * math.tau / 7 + 0.2
        icicle(p["ice_lt"], x + math.cos(a) * radius * 1.04, y + math.sin(a) * radius * 1.04, top, 0.18 + 0.1 * (i % 3), 0.035)


def searchlight(p, pos, z, aim):
    x, y = pos
    box("light_post", p["steel_dk"], (x, y, z), (0.07, 0.07, 0.3), bevel=0.0)
    box("light_head", p["steel_dk"], (x, y, z + 0.28), (0.24, 0.24, 0.16), bevel=0.01)
    a = math.atan2(aim[1], aim[0])
    box("light_lens", mat("arc", 0xE4F6FF, emit=3.5), (x + math.cos(a) * 0.13, y + math.sin(a) * 0.13, z + 0.28), (0.05, 0.2, 0.12), bevel=0.0, rot_z=a)


def heating_pipe(p, pts):
    """Cano de aquecimento forrado, com cintas de perigo e juntas de aço."""
    for a, b in itertools.pairwise(pts):
        beam("lagged_pipe", p["lag"], a, b, thick=0.17)
        for t in (0.25, 0.7):
            q = Vector(a).lerp(Vector(b), t)
            box("pipe_strap", p["hazard"] if t < 0.5 else p["steel_dk"], (q.x, q.y, q.z - 0.1), (0.22, 0.22, 0.2), bevel=0.0)
    for q in pts[1:-1]:
        box("pipe_elbow", p["steel_dk"], (q[0], q[1], q[2] - 0.12), (0.26, 0.26, 0.26), bevel=0.02)


def boiler_block(p, kx):
    """Caldeira atarracada no fundo: bloco de aço com três tambores deitados, neve em cima e janelas acesas."""
    box("boiler_base", p["steel"], (kx, 0, 0.18), (2.5, 2.1, 1.0), bevel=0.05, taper=0.95, taper_y=0.95)
    box("boiler_band", p["rust"], (kx, 0, 0.62), (2.54, 2.14, 0.12), bevel=0.0)
    box("boiler_deck", p["snow"], (kx, 0, 1.15), (2.3, 1.9, 0.1), bevel=0.04)
    for i, y in enumerate((-0.62, 0.0, 0.62)):
        cyl("boiler_drum", p["steel_dk"] if i == 1 else p["rust"], (kx - 1.0, y, 1.5), 0.3, 2.0, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
        for x in (kx - 0.5, kx + 0.4):
            cyl("drum_strap", p["hazard"], (x, y, 1.5), 0.33, 0.1, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
        blob(p["snow"], (kx, y, 1.82), (1.8, 0.4, 0.14), sides=8, rings=3)
    for y in (-0.7, -0.25, 0.25, 0.7):
        kit.window(p["steel_dk"], p["lamp"], (kx + 1.27, y, 0.6), "x+", w=0.2, h=0.2)
    for x in (kx - 0.7, kx, kx + 0.7):
        kit.window(p["steel_dk"], p["lamp"], (x, 1.07, 0.6), "y+", w=0.2, h=0.2)
        kit.window(p["steel_dk"], p["lamp"], (x, -1.07, 0.6), "y-", w=0.2, h=0.2)


def drill_station():
    """Estação de perfuração do Norte: cúpulas de pressão, caldeira, canos forrados com vapor e a torre congelada."""
    p = palette()
    half = 2.45
    box("pad", p["steel_dk"], (0, 0, 0), (half * 2 + 0.3, half * 2 + 0.3, 0.16), bevel=0.05, taper=0.96, taper_y=0.96)
    box("yard", p["snow_sh"], (0, 0, 0.14), (half * 2 - 0.5, half * 2 - 0.5, 0.08), bevel=0.03)
    w = 2.0
    for along_x, fixed, out in ((True, w, 1), (True, -w, -1), (False, -w, -1)):
        plate_wall(p, -w + 0.75, w - 0.75, fixed, along_x, out)
    plate_wall(p, -w + 0.75, -0.8, w, False, 1)
    plate_wall(p, 0.8, w - 0.75, w, False, 1)
    # Cúpulas de pressão nos cantos, para fora da linha da muralha; as de trás são maiores e desiguais.
    pressure_dome(p, (w + 0.12, w + 0.12), 0.95, 1.0)
    pressure_dome(p, (w + 0.12, -w - 0.12), 0.95, 0.9, squash=0.6)
    pressure_dome(p, (-w - 0.1, w + 0.1), 1.05, 1.15, squash=0.75)
    pressure_dome(p, (-w - 0.05, -w - 0.05), 0.85, 0.85)
    searchlight(p, (w + 0.35, w + 0.5), 1.45, (1, 0.5))
    searchlight(p, (-w - 0.2, w + 0.8), 1.9, (0, 1))
    # Portaria em prisma hexagonal com escotilha pressurizada e luz vermelha de sinal.
    gx = w + 0.18
    cyl("gate_hex", p["steel_dk"], (gx, 0, 0.1), 0.92, 1.35, sides=6, top_radius=0.82, bevel=0.03)
    cyl("gate_hex_snow", p["snow"], (gx, 0, 1.42), 0.84, 0.1, sides=6, bevel=0.03)
    box("gate_frame", p["hazard"], (gx + 0.74, 0, 0.1), (0.05, 1.0, 1.1), bevel=0.0)
    box("gate_hatch", p["steel"], (gx + 0.8, 0, 0.14), (0.08, 0.8, 0.98), bevel=0.02)
    for z in (0.4, 0.85):
        box("gate_bar", p["steel_dk"], (gx + 0.86, 0, z), (0.03, 0.8, 0.07), bevel=0.0)
    box("signal", p["red"], (gx + 0.3, 0, 1.56), (0.16, 0.16, 0.14), bevel=0.0)
    for s in (-1, 1):
        box("gate_lamp", p["lamp"], (gx + 0.82, s * 0.62, 1.0), (0.05, 0.1, 0.1), bevel=0.0)
    # Cano de aquecimento pelas cortinas laterais, com respiros de vapor.
    for s in (-1, 1):
        heating_pipe(p, [(-w + 0.8, s * (w + 0.38), 0.55), (w - 0.9, s * (w + 0.38), 0.55)])
        box("pipe_post", p["steel_dk"], (0.2, s * (w + 0.38), 0.0), (0.16, 0.16, 0.5), bevel=0.0)
    cyl("vent", p["steel_dk"], (-w + 0.8, w + 0.38, 0.55), 0.1, 0.4, sides=8, bevel=0.0)
    steam_puffs(p, -w + 0.8, w + 0.38, 1.0)
    cyl("vent", p["steel_dk"], (0.6, -w - 0.38, 0.55), 0.1, 0.4, sides=8, bevel=0.0)
    steam_puffs(p, 0.6, -w - 0.38, 1.0, scale=0.8)
    kx = -0.5
    boiler_block(p, kx)
    # Coroa: derrick curto encapado de gelo, fora do centro, com lâmpada de aviso.
    kit.derrick(p["steel"], p["steel_dk"], p["lamp"], (kx + 0.55, 0.5, 1.2), base=0.9, top=0.2, height=2.5)
    for z, s in ((1.5, 0.78), (2.2, 0.55), (2.9, 0.36)):
        box("derrick_ice", p["ice"], (kx + 0.55, 0.5, z), (s, s, 0.4), bevel=0.04, taper=0.8, taper_y=0.8)
    box("crown_snow", p["snow"], (kx + 0.55, 0.5, 3.76), (0.5, 0.5, 0.08), bevel=0.02)
    icicle_row(p["ice_lt"], kx + 0.25, kx + 0.85, 0.15, 2.55, 3, base_len=0.3, r=0.035)
    # Pátio: tambores de combustível e um tanque pequeno forrado de neve.
    for i, (dx, dy) in enumerate(((1.15, -0.8), (1.45, -0.62), (1.3, -1.1))):
        cyl("drum", p["hazard"] if i == 0 else p["red"] if i == 1 else p["rust"], (dx, dy, 0.2), 0.14, 0.34, sides=8, bevel=0.0)
        blob(p["snow"], (dx, dy, 0.58), (0.26, 0.26, 0.08), sides=6, rings=3)
    cyl("yard_tank", p["steel"], (1.25, 0.95, 0.2), 0.36, 0.62, sides=12)
    ring("yard_tank_band", p["hazard"], (1.25, 0.95, 0.45), 0.36, 0.1, sides=12)
    dome("yard_tank_top", p["snow"], (1.25, 0.95, 0.8), 0.36, squash=0.5, sides=10)


# ---------------------------------------------------------------------------------------------------------
# Registro e saída
# ---------------------------------------------------------------------------------------------------------

SCENERY = {
    "frost_wall": frost_wall,
    "frost_pillar": frost_pillar,
    "frost_arch": frost_arch,
    "frost_tree_a": frost_tree_a,
    "frost_tree_b": frost_tree_b,
    "frost_tree_c": frost_tree_c,
    "frost_stump": frost_stump,
    "frost_drift": frost_drift,
    "frost_sled": frost_sled,
    "frost_ice_rocks": frost_ice_rocks,
    "frost_supply_dump": frost_supply_dump,
    "frost_log_pile": frost_log_pile,
    "frost_wellhead": frost_wellhead,
    "frost_derrick": frost_derrick,
    "frost_tank": frost_tank,
    "frost_mast": frost_mast,
    "frost_pipe_run": frost_pipe_run,
    "frost_telegraph": frost_telegraph,
    "frost_hare": frost_hare,
    "frost_lemming": frost_lemming,
    "frost_ptarmigan": frost_ptarmigan,
    "frost_fox": frost_fox,
    "frost_owl": frost_owl,
    "frost_raven": frost_raven,
}
CASTLES = {"frost_thaw_watch": thaw_watch, "frost_drill_station": drill_station}
SNOW_GROUND = 0xDCE6F0


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["all"]
    everything = {**CASTLES, **SCENERY}
    names = list(everything) if args[0] == "all" else [args[0]]
    out = args[args.index("--out") + 1] if "--out" in args else ""
    render_dir = args[args.index("--render") + 1] if "--render" in args else ""
    plain_render = kit.render
    kit.render = lambda path, yaw, **kw: plain_render(path, yaw, ground=SNOW_GROUND, **kw)
    for name in names:
        is_castle = name in CASTLES
        dest = os.path.join(out, "castles" if is_castle else "scenery/permafrost") if out else ""
        views = (("front", -35.0), ("back", 150.0), ("game", -90.0)) if is_castle else (("front", -35.0),)
        kit.build(name, dest, render_dir, make=everything[name], views=views)


if __name__ == "__main__":
    main()
