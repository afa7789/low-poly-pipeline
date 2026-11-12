"""Prédios da raça Northern modelados por script (redesenho de reports/design/race-northern.md): um GLB por prédio.

Uso:
    blender -b --factory-startup --python tools/blender/buildings_northern.py -- <id|all> [--out DIR] [--render DIR]

Economia de Óleo Congelado: ferro azulado rebitado, neve suja, lona encerada, madeira e gelo opaco facetado
(o gelo é massa opaca nas quinas e juntas; o único vidro é o da lamparina). Regra da raça: todo prédio é uma
estação com produto à vista (poço, bomba, tambor, poça de cru) e leva UMA lamparina de serviço âmbar acesa e
a peneira de poço (a grade em anel) em algum ponto. Silhueta: o telhado/treliça inclinado ao sotavento (neve
carregada na borda alta) mais uma vertical funcional (sonda, chaminé, totem, poste de lamparina); nenhum
prédio é uma agulha nua. Pegada ~3,5 x 3,5 centrada na origem, porta virada para +x; o jogo normaliza o
tamanho, põe o prédio no plinto do time e desenha a bandeira.
"""

import itertools
import math
import os
import sys

import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import map_castles as kit
from map_castles import beam, box, cyl, dome, mat, prism, ring


def pal():
    return {
        "snow": mat("dust_snow", 0xE6ECF0),
        "snow_dk": mat("dirty_snow", 0xBBC7D1),
        "ice": mat("ice_raw", 0xB4E3F5),
        "ice_dk": mat("ice_brine", 0x82BCD8),
        "iron": mat("iron_blue", 0x7489A0),
        "iron_dk": mat("iron_blue_dark", 0x4D5C6C),
        "soot": mat("soot", 0x2B3036),
        "tarp": mat("oilskin", 0xB3A271),
        "tarp_dk": mat("oilskin_dark", 0x867A56),
        "wood": mat("timber", 0xAD8D64),
        "wood_dk": mat("timber_dark", 0x70573F),
        "rust": mat("rust", 0xBC6B3E),
        "copper": mat("copper", 0xD28B52),
        "bone": mat("whalebone", 0xF0E8D2),
        "hide": mat("hide", 0x9A7F68),
        "rock": mat("frost_rock", 0x92A3B1),
        "rock_dk": mat("frost_rock_dark", 0x6B7B89),
        "mud": mat("frozen_mud", 0x756C66),
        "crude": mat("crude", 0x17151D),
        "fungus": mat("frost_fungus", 0xA7B9E6),
        "fungus_dk": mat("frost_fungus_dark", 0x7A8CC4),
        "lamp": mat("lamp_amber", 0xFFB224, emit=3.0),
    }


# ---------------------------------------------------------------------------------------------------------
# Peças da raça
# ---------------------------------------------------------------------------------------------------------


def pad(p, size=(3.5, 3.5)):
    """Chão de lama congelada, do tamanho do conteúdo: o jogo normaliza pelo maior lado."""
    box("pad", p["mud"], (0, 0, 0), (size[0], size[1], 0.1), bevel=0.03)


def ball(name, material, center, radius, sides=8):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1 if sides <= 8 else 2, radius=radius)
    bmesh.ops.translate(bm, verts=bm.verts, vec=center)
    return kit._finish(bm, name, material)


def lamp(p, pos, post=0.0, lit=True):
    """A lamparina de serviço, o único vidro e o único acento: acesa uma por prédio. post > 0 põe num poste."""
    x, y, z = pos
    if post > 0.0:
        box("lamp_post", p["wood_dk"], (x, y, z), (0.07, 0.07, post), bevel=0.0)
        z += post
    box("lamp_base", p["soot"], (x, y, z), (0.17, 0.17, 0.04), bevel=0.0)
    box("lamp_glass", p["lamp"] if lit else p["iron_dk"], (x, y, z + 0.04), (0.12, 0.12, 0.15), bevel=0.0)
    box("lamp_cap", p["soot"], (x, y, z + 0.19), (0.19, 0.19, 0.05), bevel=0.0, taper=0.4, taper_y=0.4)


def drum(p, pos, tone="rust", lying=False):
    """Tambor de óleo cintado."""
    x, y, z = pos
    if lying:
        cyl("drum", p[tone], (x - 0.21, y, z + 0.16), 0.16, 0.42, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
        return
    cyl("drum", p[tone], (x, y, z), 0.16, 0.42, sides=10, bevel=0.0)
    for dz in (0.1, 0.3):
        ring("drum_band", p["soot"], (x, y, z + dz), 0.16, 0.04, thick=0.015, sides=10)
    cyl("drum_snow", p["snow"], (x, y, z + 0.42), 0.14, 0.03, sides=8, bevel=0.0)


def sump(p, pos, r=0.45):
    """Poça de cru com a borda de neve: o produto à vista."""
    x, y, z = pos
    cyl("sump_rim", p["snow_dk"], (x, y, z), r + 0.1, 0.07, sides=9, bevel=0.0)
    cyl("sump_crude", p["crude"], (x, y, z + 0.05), r, 0.03, sides=9, bevel=0.0)


def drift(p, pos, size, rot_z=0.0, tone="snow"):
    """Duna de neve em cunha: a borda alta fica ao sotavento (-x com rot_z = 0)."""
    prism("drift", p[tone], pos, size, ridge=0.12, bevel=0.02, rot_z=rot_z)


def hollow_ring(p, pos, r, tone="iron", thick=0.07, n=10, bars=True):
    """Peneira de poço: anel de vigas com a grade em cruz; é a forma-mãe da raça."""
    x, y, z = pos
    pts = [(x + math.cos(i * math.tau / n) * r, y + math.sin(i * math.tau / n) * r, z) for i in range(n)]
    for i in range(n):
        beam("sieve_rim", p[tone], pts[i], pts[(i + 1) % n], thick=thick)
    if bars:
        beam("sieve_bar", p[tone], (x - r, y, z), (x + r, y, z), thick=thick * 0.7)
        beam("sieve_bar", p[tone], (x, y - r, z), (x, y + r, z), thick=thick * 0.7)


def rail(p, x0, x1, y, z=0.1):
    """Trilho de bitola estreita sobre dormentes."""
    box("rail", p["iron_dk"], ((x0 + x1) / 2, y - 0.04, z + 0.06), (x1 - x0, 0.08, 0.07), bevel=0.0)
    for x in [x0 + 0.15 + i * 0.4 for i in range(int((x1 - x0) / 0.4))]:
        box("sleeper", p["wood_dk"], (x, y, z), (0.14, 0.62, 0.06), bevel=0.0)


def rail_wheel(p, pos, r=0.17):
    x, y, z = pos
    cyl("rail_wheel", p["soot"], (x, y - 0.04, z), r, 0.08, sides=8, bevel=0.0, rot=("X", math.radians(90)))


def rivets(p, x0, x1, z, y, tone="soot"):
    """Fiada de rebites na face +y/-y."""
    n = max(2, int((x1 - x0) / 0.3))
    for i in range(n):
        box("rivet", p[tone], (x0 + i * (x1 - x0) / (n - 1), y, z), (0.06, 0.03, 0.06), bevel=0.0)


def coil(p, pos, radius, height, turns=4, tone="copper"):
    """Serpentina vertical do condensador."""
    x, y, z = pos
    steps = turns * 6
    prev = None
    for i in range(steps + 1):
        t = i / steps
        a = t * turns * math.tau
        pt = (x + math.cos(a) * radius, y + math.sin(a) * radius, z + t * height)
        if prev:
            beam("coil", p[tone], prev, pt, thick=0.05)
        prev = pt


def dome_ribs(p, center, radius, squash, n=3, tone="iron_dk", thick=0.07):
    """Costelas de ferro rebitado sobre a cúpula: meridianos de vigas que cruzam o topo."""
    cx, cy, cz = center
    steps = 8
    for k in range(n):
        phi = k * math.pi / n
        dx, dy = math.cos(phi), math.sin(phi)
        prev = None
        for i in range(steps + 1):
            ang = i * math.pi / steps
            u = math.cos(ang) * radius * 1.04
            pt = (cx + dx * u, cy + dy * u, cz + math.sin(ang) * radius * squash * 1.06)
            if prev:
                beam("rib", p[tone], prev, pt, thick=thick)
            prev = pt


def block_courses(p, center, radius, squash, levels=(0.22, 0.44, 0.66, 0.84), tone="snow_dk", sides=12):
    """Fiadas de blocos serrados na cúpula do iglu: cintas finas que seguem o perfil."""
    cx, cy, cz = center
    for f in levels:
        z = cz + f * radius * squash
        rr = radius * math.sqrt(max(0.0, 1 - f * f))
        cyl("block_course", p[tone], (cx, cy, z), rr * 1.015, 0.035, sides=sides, bevel=0.0)


# ---------------------------------------------------------------------------------------------------------
# Tronco do vento: dormitórios (Igloo -> Modern Igloo; Ice Troll Hut -> Voodoo Lounge)
# ---------------------------------------------------------------------------------------------------------


def h03U_igloo():
    """Cúpula de blocos serrados tortos, porta de lona encerada, cano de fogão com a lamparina; tripé de arpão."""
    p = pal()
    pad(p)
    c = (-0.25, 0.0, 0.1)
    dome("igloo", p["snow"], c, 1.45, squash=0.78, sides=12)
    block_courses(p, c, 1.45, 0.78)
    # Blocos tortos salientes: serrados, não esculpidos.
    for i, (a, f) in enumerate(((20, 0.25), (95, 0.45), (160, 0.3), (230, 0.5), (300, 0.35))):
        rad = math.radians(a)
        rr = 1.45 * math.sqrt(1 - f * f)
        box("block", p["snow_dk"], (c[0] + math.cos(rad) * rr * 0.97, c[1] + math.sin(rad) * rr * 0.97, c[2] + f * 1.45 * 0.78 - 0.1), (0.38, 0.3, 0.2), bevel=0.02, rot_z=rad + 0.3 * (i % 3 - 1))
    # Túnel de entrada baixo e a porta de lona.
    box("tunnel", p["snow"], (0.9, 0, 0.1), (1.0, 1.0, 0.7), bevel=0.04, taper=0.8, taper_y=0.9)
    box("door_hole", p["soot"], (1.39, 0, 0.1), (0.04, 0.55, 0.5), bevel=0.0)
    box("oilskin_door", p["tarp"], (1.43, 0.1, 0.1), (0.04, 0.4, 0.55), bevel=0.0, rot_z=0.0)
    box("door_beam", p["wood_dk"], (1.45, 0, 0.62), (0.07, 0.7, 0.07), bevel=0.0)
    # Cano de fogão de ferro atravessando o teto, com a lamparina na ponta.
    cyl("stovepipe", p["iron_dk"], (-0.55, 0.45, 0.95), 0.1, 0.75, sides=8, bevel=0.0)
    cyl("stovecap", p["soot"], (-0.55, 0.45, 1.7), 0.14, 0.07, sides=8, bevel=0.0)
    lamp(p, (-0.55, 0.45, 1.77))
    # Tripé de arpão com o arpão-peneira pendurado, tambor na entrada, duna ao sotavento.
    for k in range(3):
        a = math.radians(90 + 120 * k)
        beam("tripod", p["wood_dk"], (1.45 + math.cos(a) * 0.3, -1.0 + math.sin(a) * 0.3, 0.1), (1.45, -1.0, 1.35), thick=0.06)
    beam("harpoon", p["iron"], (1.45, -1.0, 1.2), (1.8, -0.8, 0.35), thick=0.045)
    box("harpoon_head", p["iron_dk"], (1.8, -0.8, 0.3), (0.12, 0.12, 0.12), bevel=0.0)
    drum(p, (1.25, 0.9, 0.1))
    sump(p, (1.7, 0.2, 0.1), 0.3)
    drift(p, (-1.5, 0.0, 0.1), (0.8, 2.2, 0.5))


def h06L_modern_igloo():
    """Bunker de gelo comprimido com casca de ferro rebitado em duas camadas, galpão de destilaria e porta blindada."""
    p = pal()
    pad(p)
    # Duas camadas octogonais rígidas: mais alto e mais duro que o iglu.
    cyl("shell_low", p["iron"], (-0.15, 0, 0.1), 1.55, 0.8, sides=8, top_radius=1.42, bevel=0.03)
    ring("shell_band", p["iron_dk"], (-0.15, 0, 0.75), 1.42, 0.1, sides=8)
    cyl("shell_high", p["ice_dk"], (-0.15, 0, 0.9), 1.3, 0.7, sides=8, top_radius=0.95, bevel=0.03)
    ring("shell_band2", p["iron_dk"], (-0.15, 0, 1.45), 0.98, 0.1, sides=8)
    dome("shell_cap", p["snow"], (-0.15, 0, 1.55), 0.95, squash=0.55, sides=8)
    for a in range(0, 360, 45):
        r = math.radians(a)
        beam("shell_rib", p["iron_dk"], (-0.15 + math.cos(r) * 1.5, math.sin(r) * 1.5, 0.15), (-0.15 + math.cos(r) * 0.95, math.sin(r) * 0.95, 1.5), thick=0.09)
    # Porta blindada baixa, com lamparina.
    box("armor_door", p["soot"], (1.3, 0, 0.1), (0.14, 0.9, 0.7), bevel=0.0)
    box("door_frame", p["iron_dk"], (1.28, 0, 0.8), (0.18, 1.1, 0.1), bevel=0.0)
    for s in (-1, 1):
        box("door_jamb", p["iron_dk"], (1.28, s * 0.55, 0.1), (0.18, 0.1, 0.78), bevel=0.0)
    lamp(p, (1.45, 0.8, 0.1), post=0.8)
    # Galpão de destilaria acoplado atrás, com o alambique de cobre e o tanque de estocagem.
    box("still_shed", p["tarp"], (-1.05, 1.1, 0.1), (1.0, 1.1, 0.8), bevel=0.03)
    prism("still_roof", p["snow"], (-1.05, 1.1, 0.9), (1.2, 1.3, 0.4), ridge=0.75, bevel=0.02, rot_z=math.radians(90))
    cyl("still", p["copper"], (-1.05, 1.1, 1.1), 0.3, 0.55, sides=8, top_radius=0.22, bevel=0.0)
    dome("still_head", p["copper"], (-1.05, 1.1, 1.65), 0.22, squash=0.9, sides=8)
    beam("condenser", p["copper"], (-1.05, 1.1, 1.8), (-0.2, 1.55, 1.3), thick=0.08)
    cyl("tank", p["snow_dk"], (0.6, 1.35, 0.1), 0.38, 1.0, sides=10, bevel=0.0)
    ring("tank_band", p["iron_dk"], (0.6, 1.35, 0.5), 0.38, 0.07, sides=10)
    cyl("tank_cap", p["snow"], (0.6, 1.35, 1.1), 0.36, 0.08, sides=10, bevel=0.0)
    drum(p, (0.0, -1.35, 0.1))
    drum(p, (0.35, -1.45, 0.1), tone="iron_dk")
    sump(p, (1.6, -0.9, 0.1), 0.28)
    drift(p, (-1.55, -0.5, 0.1), (0.7, 1.6, 0.55))


def _hut_dome(p, c, radius, tone="snow_dk"):
    dome("hut", p[tone], c, radius, squash=0.72, sides=12)
    dome_ribs(p, c, radius, 0.72, n=3)
    for a in (35, 215):
        r = math.radians(a)
        rr = radius * 0.93
        box("patch", p["tarp"], (c[0] + math.cos(r) * rr, c[1] + math.sin(r) * rr, c[2] + 0.25), (0.5, 0.4, 0.45), bevel=0.02, rot_z=r)


def h03K_ice_troll_hut():
    """Dormitório de trabalho: cúpula de neve suja com costelas de ferro rebitado, chaminé de fogão em treliça,
    entrada baixa, varal de couros e o garfo de arpão."""
    p = pal()
    pad(p)
    c = (-0.3, 0.0, 0.1)
    _hut_dome(p, c, 1.4)
    # Entrada baixa que obriga a abaixar a cabeça.
    box("tunnel", p["snow_dk"], (0.85, 0, 0.1), (0.9, 0.9, 0.6), bevel=0.04, taper=0.8, taper_y=0.9)
    box("door_hole", p["soot"], (1.3, 0, 0.1), (0.04, 0.5, 0.42), bevel=0.0)
    box("lintel", p["wood_dk"], (1.3, 0, 0.52), (0.1, 0.7, 0.07), bevel=0.0)
    # Chaminé do fogão em treliça, o cru fumegando.
    kit.chimney(p["iron"], p["iron_dk"], p["soot"], (-0.85, 0.5, 0.75), 1.5, radius=0.2)
    for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        beam("stack_stay", p["iron_dk"], (-0.85 + sx * 0.35, 0.5 + sy * 0.35, 0.65), (-0.85, 0.5, 1.7), thick=0.04)
    cyl("smoke", p["soot"], (-0.85, 0.5, 2.3), 0.16, 0.35, sides=7, top_radius=0.32, bevel=0.0)
    # Varal de couros e o garfo de arpão.
    for s in (-1, 1):
        beam("rack_post", p["wood_dk"], (0.95, -1.15 + s * 0.45, 0.1), (0.95, -1.15 + s * 0.45, 1.2), thick=0.07)
    beam("rack_bar", p["wood_dk"], (0.95, -1.6, 1.15), (0.95, -0.7, 1.15), thick=0.07)
    for i, y in enumerate((-1.5, -1.2, -0.9)):
        box("hide", p["hide"], (0.95, y, 0.55), (0.06, 0.22, 0.62 - 0.1 * (i % 2)), bevel=0.0, rot_z=0.1 * i)
    beam("fork", p["wood_dk"], (1.55, 0.95, 0.1), (1.6, 0.95, 1.4), thick=0.05)
    for s in (-1, 1):
        beam("fork_tine", p["iron_dk"], (1.6, 0.95, 1.4), (1.6, 0.95 + s * 0.1, 1.7), thick=0.035)
    lamp(p, (1.45, 0.4, 0.1), post=0.65)
    drum(p, (-1.4, -1.2, 0.1))
    sump(p, (1.5, -0.2, 0.1), 0.25)
    drift(p, (-1.6, 0.4, 0.1), (0.7, 1.9, 0.55))


def h03J_voodoo_lounge():
    """A mesma cúpula coroada pelo mastro-totem de sucata (válvulas, arruelas e caveiras de foca) e o alambique."""
    p = pal()
    pad(p)
    c = (-0.45, 0.0, 0.1)
    _hut_dome(p, c, 1.3)
    ring("tarp_hem", p["tarp"], (c[0], c[1], 0.1), 1.3, 0.28, thick=0.03, sides=12)
    box("tunnel", p["snow_dk"], (0.65, 0, 0.1), (0.8, 0.85, 0.55), bevel=0.04, taper=0.8, taper_y=0.9)
    box("door_hole", p["soot"], (1.04, 0, 0.1), (0.04, 0.45, 0.4), bevel=0.0)
    # O totem: a única vertical do bairro troll.
    top = c[2] + 1.3 * 0.72
    cyl("totem_pole", p["wood_dk"], (c[0], c[1], top - 0.1), 0.12, 2.5, sides=6, bevel=0.0)
    for i, (z, r, tone) in enumerate(((0.15, 0.45, "iron"), (0.8, 0.38, "rust"), (1.35, 0.3, "iron_dk"))):
        cyl("valve_wheel", p[tone], (c[0], c[1], top + z), r, 0.07, sides=8, bevel=0.0)
        for a in (0, 90):
            ar = math.radians(a + 20 * i)
            beam("wheel_spoke", p["soot"], (c[0] - math.cos(ar) * r, c[1] - math.sin(ar) * r, top + z + 0.08), (c[0] + math.cos(ar) * r, c[1] + math.sin(ar) * r, top + z + 0.08), thick=0.04)
    for z in (0.5, 1.05, 1.65):
        ball("seal_skull", p["bone"], (c[0] + 0.0, c[1] + 0.0, top + z), 0.17, 8)
        box("skull_eye", p["soot"], (c[0] + 0.14, c[1], top + z + 0.03), (0.05, 0.2, 0.06), bevel=0.0)
    lamp(p, (c[0], c[1], top + 2.4))
    # Alambique de condensado (barril, tubo de cobre, queimador) e o balcão de peneira voltado para fora.
    cyl("still_barrel", p["wood"], (0.55, 1.2, 0.1), 0.34, 0.65, sides=10, bevel=0.0)
    ring("still_band", p["iron_dk"], (0.55, 1.2, 0.4), 0.34, 0.06, sides=10)
    cyl("still_pot", p["copper"], (0.55, 1.2, 0.75), 0.26, 0.4, sides=8, top_radius=0.12, bevel=0.0)
    beam("still_tube", p["copper"], (0.55, 1.2, 1.15), (1.2, 0.85, 0.85), thick=0.07)
    coil(p, (1.2, 0.85, 0.12), 0.14, 0.7, turns=3)
    box("burner", p["soot"], (0.55, 1.2, 0.0), (0.4, 0.4, 0.1), bevel=0.0)
    box("counter", p["wood"], (1.4, -0.85, 0.1), (0.55, 1.3, 0.55), bevel=0.03)
    hollow_ring(p, (1.4, -0.85, 0.68), 0.4, tone="iron_dk", thick=0.05, n=8)
    box("counter_jug", p["tarp_dk"], (1.45, -0.55, 0.65), (0.14, 0.14, 0.22), bevel=0.0)
    drum(p, (-1.5, -1.3, 0.1))
    sump(p, (1.6, 0.2, 0.1), 0.22)
    drift(p, (-1.65, 0.2, 0.1), (0.6, 1.8, 0.5))


# ---------------------------------------------------------------------------------------------------------
# Tronco das garras: vazamento jovem -> adulto, e rochas -> covil -> geleira
# ---------------------------------------------------------------------------------------------------------


def open_derrick(p, pos, base, top, height, lean=(0.0, 0.0), tone="iron"):
    """Treliça de sonda aberta (4 pernas, anéis, X): sem placa na coroa, para o teto não esconder o conteúdo."""
    x, y, z = pos
    legs = []
    for sx, sy in ((1, 1), (1, -1), (-1, -1), (-1, 1)):
        a = Vector((x + sx * base / 2, y + sy * base / 2, z))
        b = Vector((x + lean[0] + sx * top / 2, y + lean[1] + sy * top / 2, z + height))
        legs.append((a, b))
        beam("derrick_leg", p[tone], a, b, thick=0.09)
    levels = (0.0, 0.34, 0.66, 1.0)
    for li, t in enumerate(levels):
        pts = [a.lerp(b, t) for a, b in legs]
        for i in range(4):
            beam("derrick_ring", p[tone], pts[i], pts[(i + 1) % 4], thick=0.06)
        if li + 1 < len(levels):
            up = [a.lerp(b, levels[li + 1]) for a, b in legs]
            for i in range(4):
                beam("derrick_x", p["iron_dk"], pts[i], up[(i + 1) % 4], thick=0.04)


def _well_cage(p, base, top, height):
    open_derrick(p, (0, 0, 0.1), base, top, height)


def h03T_ice_claws():
    """Vazamento jovem: três dentes de gelo crescendo numa gaiola de poço rebitada, cone de neve na base."""
    p = pal()
    pad(p, (3.2, 3.2))
    cyl("snow_cone", p["snow"], (0, 0, 0.1), 1.25, 0.55, sides=9, top_radius=0.5, bevel=0.0)
    _well_cage(p, 2.1, 1.7, 1.7)
    for k in range(3):
        a = math.radians(30 + 120 * k)
        ux, uy = math.cos(a), math.sin(a)
        h = 1.15 - 0.2 * (k % 2)
        # Dente de gelo em dois lances: sobe inclinado para fora e a ponta volta para dentro.
        base, mid, tip = Vector((ux * 0.3, uy * 0.3, 0.5)), Vector((ux * 0.5, uy * 0.5, 0.5 + h * 0.55)), Vector((ux * 0.4, uy * 0.4, 0.5 + h))
        beam("ice_tooth", p["ice"], base, mid, thick=0.36)
        beam("ice_tooth_tip", p["snow"], mid, tip, thick=0.2)
    # Os dentes passam da borda da gaiola; a sonda abandonada tombada e o poço de cru novo.
    beam("probe", p["iron_dk"], (1.0, -1.1, 0.12), (1.55, -0.5, 0.95), thick=0.09)
    box("probe_head", p["rust"], (1.55, -0.5, 0.9), (0.2, 0.2, 0.14), bevel=0.0)
    sump(p, (1.1, 0.7, 0.1), 0.4)
    drum(p, (-1.3, 1.2, 0.1))
    lamp(p, (1.45, 0.15, 0.1), post=0.7)
    drift(p, (-1.4, -0.6, 0.1), (0.6, 1.5, 0.45))


def h043_frost_claws():
    """Vazamento adulto: os mesmos dentes torcidos em espiral dentro de uma gaiola alta, com canos de perfuração quebrados."""
    p = pal()
    pad(p, (3.2, 3.2))
    cyl("snow_cone", p["snow"], (0, 0, 0.1), 1.2, 0.45, sides=9, top_radius=0.55, bevel=0.0)
    _well_cage(p, 2.2, 1.4, 3.5)
    hollow_ring(p, (0, 0, 3.6), 0.75, tone="iron", thick=0.08, n=8)
    # Três fitas de gelo em hélice, afinando para o topo, ultrapassam a coroa da gaiola.
    for k in range(3):
        prev = None
        for i in range(13):
            t = i / 12
            ang = math.radians(120 * k) + t * 2.6 * math.pi
            r = 0.55 * (1 - t) + 0.12
            pt = (math.cos(ang) * r, math.sin(ang) * r, 0.4 + t * 3.2)
            if prev:
                beam("ice_spiral", p["ice"], prev, pt, thick=0.3 * (1 - t) + 0.08)
            prev = pt
    cyl("ice_core", p["ice_dk"], (0, 0, 0.4), 0.28, 3.4, sides=6, top_radius=0.05, bevel=0.0)
    # Canos de perfuração quebrados, o poço de cru, lamparina.
    beam("broken_pipe", p["iron_dk"], (1.0, -1.15, 0.12), (1.65, -0.35, 1.2), thick=0.12)
    beam("broken_pipe", p["rust"], (1.35, -1.3, 0.12), (0.9, -0.6, 0.8), thick=0.1)
    sump(p, (1.15, 0.85, 0.1), 0.42)
    drum(p, (-1.35, 1.2, 0.1))
    lamp(p, (1.5, 0.1, 0.1), post=0.8)
    drift(p, (-1.4, -0.5, 0.1), (0.6, 1.5, 0.5))


def h04F_icy_rocks():
    """Covil do urso: afloramento de neve suja entre pedras com o arco de costela de baleia na boca da toca."""
    p = pal()
    pad(p)
    box("rock_main", p["rock"], (-0.6, 0.0, 0.1), (2.0, 2.4, 1.3), bevel=0.06, taper=0.62, taper_y=0.7, rot_z=0.15)
    box("rock_back", p["rock_dk"], (-1.1, 0.7, 0.1), (1.3, 1.3, 1.9), bevel=0.06, taper=0.45, taper_y=0.5, rot_z=0.6)
    box("rock_side", p["rock"], (-0.1, -1.05, 0.1), (1.4, 1.1, 1.0), bevel=0.06, taper=0.5, taper_y=0.6, rot_z=-0.4)
    box("rock_front", p["rock_dk"], (0.45, 1.0, 0.1), (0.9, 0.9, 0.7), bevel=0.05, taper=0.55, taper_y=0.55, rot_z=0.9)
    box("snow_main", p["snow"], (-0.6, 0.0, 1.3), (1.2, 1.5, 0.22), bevel=0.04, taper=0.6, taper_y=0.6, rot_z=0.15)
    box("snow_back", p["snow"], (-1.1, 0.7, 1.95), (0.65, 0.65, 0.2), bevel=0.04, taper=0.5, taper_y=0.5, rot_z=0.6)
    drift(p, (-1.55, -0.3, 0.1), (0.7, 1.8, 0.6))
    # Boca da toca e o arco curvo de costela de baleia.
    box("den_mouth", p["soot"], (0.35, 0, 0.1), (0.7, 1.2, 0.85), bevel=0.0, taper=0.85, taper_y=0.7)
    pts = [(1.0, math.cos(a) * 0.82, 0.1 + math.sin(a) * 1.15) for a in [i * math.pi / 8 for i in range(9)]]
    for a, b in itertools.pairwise(pts):
        beam("rib_arch", p["bone"], a, b, thick=0.14)
    box("rib_foot", p["bone"], (1.0, 0.82, 0.1), (0.2, 0.2, 0.1), bevel=0.0)
    box("rib_foot", p["bone"], (1.0, -0.82, 0.1), (0.2, 0.2, 0.1), bevel=0.0)
    # Tambor mordido, poça de cru, lamparina de estaca no portão.
    cyl("bitten_drum", p["rust"], (1.45, 1.1, 0.1), 0.2, 0.46, sides=9, bevel=0.0, rot=("Y", math.radians(18)))
    box("drum_bite", p["soot"], (1.55, 1.1, 0.4), (0.12, 0.2, 0.16), bevel=0.0)
    sump(p, (1.65, 0.65, 0.1), 0.22)
    lamp(p, (1.45, -1.15, 0.1), post=0.7)


def h03W_glacier():
    """Geleira rebocada e assentada como bastião: pirâmide irregular de gelo sujo com corte reto e portão de ferro,
    escoras de madeira, desvio de trilho com trenó e a bigorna de gelo no pátio."""
    p = pal()
    pad(p)
    box("glacier_low", p["ice_dk"], (-0.5, 0.0, 0.1), (3.0, 3.2, 1.2), bevel=0.06, taper=0.74, taper_y=0.78, rot_z=0.05)
    box("glacier_mid", p["ice"], (-0.65, 0.1, 1.2), (2.1, 2.1, 1.1), bevel=0.06, taper=0.7, taper_y=0.7, rot_z=-0.25)
    box("glacier_top", p["snow"], (-0.8, 0.15, 2.2), (1.3, 1.3, 1.0), bevel=0.05, taper=0.55, taper_y=0.55, rot_z=0.35)
    for i, (x, y, h, r) in enumerate(((-0.6, 0.6, 0.8, 0.14), (-0.95, -0.3, 0.55, 0.12), (-1.1, 0.7, 0.45, 0.1))):
        cyl("ice_shard", p["ice"], (x, y, 3.0 - i * 0.35), r, h, sides=5, top_radius=0.02, bevel=0.0)
    drift(p, (-1.6, 0.0, 0.1), (0.7, 2.4, 0.9))
    # Corte industrial reto no lado da lane: face vertical de ferro com o portão.
    box("cut_face", p["iron"], (0.95, 0, 0.1), (0.2, 1.6, 1.45), bevel=0.03)
    box("gate", p["soot"], (1.07, 0, 0.1), (0.12, 0.9, 1.0), bevel=0.0)
    for s in (-1, 1):
        box("gate_post", p["iron_dk"], (1.1, s * 0.52, 0.1), (0.14, 0.1, 1.15), bevel=0.0)
    box("gate_lintel", p["iron_dk"], (1.1, 0, 1.1), (0.16, 1.1, 0.1), bevel=0.0)
    rivets(p, 0.1, 0.1, 1.3, 0.0)
    for s in (-1, 1):
        beam("prop", p["wood_dk"], (1.05, s * 0.95, 0.12), (0.55, s * 0.85, 1.25), thick=0.11)
    # Desvio de trilho entrando no portão, trenó de carga e a bigorna de gelo no pátio.
    for s in (-1, 1):
        rail(p, 1.0, 1.75, s * 0.28)
    box("sled", p["wood"], (1.35, 0, 0.2), (0.7, 0.6, 0.12), bevel=0.02)
    for s in (-1, 1):
        box("sled_runner", p["iron_dk"], (1.35, s * 0.26, 0.14), (0.8, 0.07, 0.07), bevel=0.0)
    box("sled_cargo", p["ice"], (1.35, 0, 0.32), (0.5, 0.45, 0.3), bevel=0.03)
    box("anvil_foot", p["iron_dk"], (1.1, 1.25, 0.1), (0.5, 0.35, 0.18), bevel=0.02)
    box("anvil", p["ice"], (1.1, 1.25, 0.28), (0.7, 0.4, 0.28), bevel=0.04, taper=0.7, taper_y=1.0)
    box("anvil_horn", p["ice_dk"], (1.55, 1.25, 0.45), (0.3, 0.18, 0.12), bevel=0.0, taper=0.3, taper_y=0.5)
    lamp(p, (1.55, -1.1, 0.1), post=0.75)
    sump(p, (1.45, -1.45, 0.1), 0.25)


def h049_snowy_rocks():
    """Marco de lobo: pilha baixa de pedras de neve suja com espinhas de peixe, pegadas no barro e a lamparina apagada na estaca."""
    p = pal()
    pad(p, (3.3, 3.3))
    rocks = (
        (-0.6, -0.5, 1.2, 0.4, 0.3),
        (0.0, 0.3, 1.0, 0.35, 1.0),
        (-1.1, 0.8, 0.8, 0.3, 0.7),
        (0.5, -1.0, 0.8, 0.3, -0.5),
        (-1.3, -1.2, 0.6, 0.22, 0.2),
        (0.4, 1.25, 0.7, 0.25, 0.4),
        (-0.4, 1.3, 0.5, 0.2, 0.9),
        (0.2, -0.3, 0.45, 0.5, 0.5),
    )
    for i, (x, y, s, h, r) in enumerate(rocks):
        box("stone", p["rock" if i % 2 == 0 else "rock_dk"], (x, y, 0.1), (s, s * 0.9, h), bevel=0.06, taper=0.62, taper_y=0.7, rot_z=r)
        box("stone_snow", p["snow"], (x, y, 0.1 + h), (s * 0.55, s * 0.5, 0.12), bevel=0.03, taper=0.6, taper_y=0.6, rot_z=r)
    drift(p, (-1.5, 0.2, 0.1), (0.6, 1.8, 0.4))
    # Espinha de peixe: espinha dorsal e costelas.
    beam("fish_spine", p["bone"], (0.9, 0.2, 0.14), (1.65, 0.45, 0.14), thick=0.05)
    for i in range(5):
        x = 0.95 + i * 0.15
        for s in (-1, 1):
            beam("fish_rib", p["bone"], (x, 0.2 + i * 0.05, 0.14), (x + 0.04, 0.2 + i * 0.05 + s * 0.17, 0.14), thick=0.025)
    box("fish_head", p["bone"], (1.7, 0.47, 0.13), (0.14, 0.12, 0.05), bevel=0.0)
    # Pegadas congeladas no barro, cru derramado, e a lamparina apagada.
    for i in range(5):
        box("track", p["rock_dk"], (1.25 + i * 0.12, -0.85 + i * 0.2 * (-1) ** i * 0.3, 0.1), (0.1, 0.07, 0.015), bevel=0.0)
    sump(p, (1.4, -1.2, 0.1), 0.25)
    lamp(p, (1.4, 1.1, 0.1), post=0.75, lit=False)
    drum(p, (-1.4, 1.3, 0.1))


# ---------------------------------------------------------------------------------------------------------
# Artilharia ferroviária e torre
# ---------------------------------------------------------------------------------------------------------


def _flatcar(p, length, width, y_shift=0.0):
    """Vagão plataforma no trilho de bitola estreita: o chão da artilharia da raça."""
    for s in (-1, 1):
        rail(p, -1.65, 1.75, y_shift + s * width * 0.42)
    box("car_frame", p["iron_dk"], (0, y_shift, 0.28), (length, width, 0.22), bevel=0.03)
    box("car_deck", p["wood"], (0, y_shift, 0.5), (length - 0.1, width - 0.12, 0.07), bevel=0.0)
    for sx in (-1, 1):
        for s in (-1, 1):
            rail_wheel(p, (sx * length * 0.32, y_shift + s * width * 0.42, 0.24), r=0.18)


def _ice_pallet(p, pos, rot=0.0):
    x, y, z = pos
    box("pallet", p["wood"], (x, y, z), (0.8, 0.8, 0.09), bevel=0.0, rot_z=rot)
    for i, (dx, dy) in enumerate(((-0.19, -0.19), (0.19, -0.19), (-0.19, 0.19), (0.19, 0.19))):
        box("ice_block", p["ice"], (x + dx, y + dy, z + 0.09), (0.34, 0.34, 0.3 if i != 1 else 0.22), bevel=0.03)
        box("lifting_eye", p["soot"], (x + dx, y + dy, z + (0.39 if i != 1 else 0.31)), (0.09, 0.09, 0.05), bevel=0.0)


def h048_frost_launcher():
    """Morteiro ferroviário: tubo largo rebitado inclinado sobre vagão, calço em cunha, cilindro de recuo a gás,
    palete de blocos de gelo e a lamparina de leitura de alvo."""
    p = pal()
    pad(p)
    _flatcar(p, 2.3, 1.2)
    # Calço em cunha e o tubo diagonal: a única diagonal de artilharia da raça.
    prism("wedge", p["iron"], (-0.35, 0, 0.55), (1.3, 0.9, 0.62), ridge=0.0, bevel=0.02, rot_z=0.0)
    a, b = Vector((-0.7, 0, 0.8)), Vector((1.0, 0, 2.05))
    beam("tube", p["iron"], a, b, thick=0.55)
    for t in (0.2, 0.5, 0.78):
        q = a.lerp(b, t)
        beam("tube_band", p["iron_dk"], q - (b - a).normalized() * 0.06, q + (b - a).normalized() * 0.06, thick=0.64)
    beam("muzzle", p["iron_dk"], a.lerp(b, 0.93), b, thick=0.7)
    ball("ice_slug", p["ice"], (1.05, 0, 2.15), 0.3, 8)
    box("breech", p["soot"], (-0.85, 0, 0.78), (0.3, 0.55, 0.55), bevel=0.03)
    # Cilindro de recuo a gás, paralelo ao tubo e abaixo dele.
    beam("recoil_cyl", p["snow_dk"], a + Vector((0.15, 0.5, -0.2)), b + Vector((-0.45, 0.5, -0.45)), thick=0.17)
    beam("recoil_rod", p["iron_dk"], a + Vector((0.15, -0.5, -0.2)), b + Vector((-0.45, -0.5, -0.45)), thick=0.1)
    drift(p, (-1.0, 0.0, 0.58), (0.7, 0.9, 0.35), rot_z=math.radians(180))
    _ice_pallet(p, (1.0, 1.15, 0.1), rot=0.2)
    lamp(p, (1.45, -1.15, 0.1), post=0.8)
    sump(p, (0.4, -1.3, 0.1), 0.26)
    drum(p, (-1.4, 1.2, 0.1))


def h03L_greater_frost_launcher():
    """Bateria ferroviária gêmea: dois morteiros curtos paralelos no mesmo berço de aço, coletor de pressão comum,
    guincho de munição e o escudo rebitado atrás."""
    p = pal()
    pad(p)
    _flatcar(p, 2.4, 2.0)
    box("cradle", p["iron_dk"], (-0.2, 0, 0.57), (1.7, 1.7, 0.3), bevel=0.03)
    for s in (-1, 1):
        a, b = Vector((-0.65, s * 0.5, 0.95)), Vector((0.75, s * 0.5, 1.95))
        beam("tube", p["iron"], a, b, thick=0.5)
        for t in (0.25, 0.6):
            q = a.lerp(b, t)
            beam("tube_band", p["iron_dk"], q - (b - a).normalized() * 0.06, q + (b - a).normalized() * 0.06, thick=0.58)
        beam("muzzle", p["iron_dk"], a.lerp(b, 0.92), b, thick=0.64)
        ball("ice_slug", p["ice"], (0.8, s * 0.5, 2.03), 0.26, 8)
        box("breech", p["soot"], (-0.78, s * 0.5, 0.95), (0.3, 0.5, 0.5), bevel=0.03)
    # Coletor de pressão compartilhado, com tomadas para os dois tubos e o manômetro.
    beam("manifold", p["copper"], (-0.5, -0.5, 1.5), (-0.5, 0.5, 1.5), thick=0.17)
    beam("manifold_stem", p["copper"], (-0.5, 0, 1.5), (-0.5, 0, 0.7), thick=0.14)
    cyl("gauge", p["bone"], (-0.2, 0, 1.55), 0.18, 0.06, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
    # Escudo rebitado atrás e o guincho de munição ao lado.
    box("blast_shield", p["iron"], (-1.1, 0, 0.55), (0.12, 1.9, 1.5), bevel=0.03, taper=0.9)
    rivets(p, -1.1, -1.1, 1.4, 0.0)
    box("hoist_post", p["iron_dk"], (0.85, 1.15, 0.1), (0.14, 0.14, 1.9), bevel=0.0)
    beam("hoist_arm", p["iron_dk"], (0.85, 1.15, 1.95), (0.3, 0.8, 1.55), thick=0.1)
    beam("hoist_line", p["soot"], (0.35, 0.8, 1.55), (0.35, 0.8, 0.8), thick=0.03)
    box("hoist_block", p["ice"], (0.35, 0.8, 0.55), (0.3, 0.3, 0.3), bevel=0.03)
    _ice_pallet(p, (1.25, 0.9, 0.1), rot=-0.2)
    drift(p, (-1.35, 0.0, 0.1), (0.5, 1.4, 0.5), rot_z=math.radians(180))
    lamp(p, (1.55, -1.2, 0.1), post=0.8)
    sump(p, (0.5, -1.45, 0.1), 0.25)


def h03Q_icy_tower():
    """Sonda convertida em torre de tiro: A-frame de ferro, plataforma de combate fechada e rebitada e o cone de
    broca voltado para baixo como coroa; compressor de querosene e carretel de mangueira no primeiro andar."""
    p = pal()
    box("pad", p["mud"], (0, 0, 0), (2.8, 2.8, 0.1), bevel=0.03)
    # Dois A-frames (visão lateral em x), ligados por travessas.
    for s in (-1, 1):
        for sx in (-1, 1):
            beam("a_leg", p["iron"], (sx * 1.15, s * 0.8, 0.1), (sx * 0.12, s * 0.62, 3.5), thick=0.14)
        beam("a_cross", p["iron_dk"], (-0.8, s * 0.74, 0.9), (0.8, s * 0.74, 0.9), thick=0.07)
        beam("a_brace", p["iron_dk"], (-0.8, s * 0.74, 0.9), (0.0, s * 0.68, 2.2), thick=0.06)
        beam("a_brace", p["iron_dk"], (0.8, s * 0.74, 0.9), (0.0, s * 0.68, 2.2), thick=0.06)
    for z in (0.5, 2.0):
        beam("tie", p["iron_dk"], (0, -0.8, z), (0, 0.8, z), thick=0.08)
    # Plataforma fechada: caixa rebitada com fresta de tiro e a neve ao sotavento no teto.
    box("platform", p["iron"], (0, 0, 2.25), (1.5, 1.5, 0.85), bevel=0.04, taper=0.92, taper_y=0.92)
    box("platform_floor", p["iron_dk"], (0, 0, 2.15), (1.95, 1.95, 0.12), bevel=0.02)
    for s in (-1, 1):
        box("slit", p["soot"], (0.8, s * 0.38, 2.5), (0.05, 0.4, 0.14), bevel=0.0)
    rivets(p, -0.7, 0.7, 2.65, 0.87)
    rivets(p, -0.7, 0.7, 2.65, -0.87)
    prism("roof_snow", p["snow"], (0, 0, 3.1), (1.6, 1.5, 0.35), ridge=0.15, bevel=0.02)
    # Coroa: cone de broca com a ponta para baixo, num mastro curto.
    cyl("crown_mast", p["iron_dk"], (0, 0, 3.4), 0.1, 0.4, sides=6, bevel=0.0)
    cyl("drill_cone", p["rust"], (0, 0, 3.55), 0.05, 0.9, sides=8, top_radius=0.62, bevel=0.0)
    for z in (3.8, 4.05, 4.3):
        r = 0.05 + (z - 3.55) / 0.9 * 0.57
        cyl("drill_flute", p["iron_dk"], (0, 0, z), r + 0.02, 0.06, sides=8, bevel=0.0)
    lamp(p, (0.0, 0.0, 4.45))
    # Primeiro andar: compressor de querosene e o carretel de mangueira.
    box("compressor", p["rust"], (1.1, 0.1, 0.1), (0.55, 0.7, 0.5), bevel=0.03)
    cyl("air_tank", p["snow_dk"], (1.15, -0.55, 0.32), 0.2, 0.85, sides=8, bevel=0.0, rot=("X", math.radians(90)))
    cyl("hose_reel", p["tarp_dk"], (1.0, 0.95, 0.3), 0.34, 0.2, sides=10, bevel=0.0, rot=("X", math.radians(90)))
    cyl("hose_hub", p["iron_dk"], (1.0, 0.95, 0.3), 0.12, 0.26, sides=6, bevel=0.0, rot=("X", math.radians(90)))
    beam("hose", p["soot"], (1.1, 0.5, 0.55), (0.3, -0.2, 2.1), thick=0.05)
    drum(p, (-0.8, 1.15, 0.1))
    sump(p, (-0.1, -1.1, 0.1), 0.3)


# ---------------------------------------------------------------------------------------------------------
# Âncoras e especiais
# ---------------------------------------------------------------------------------------------------------


def h03I_azure_nest():
    """Plataforma de perfuração tomada pelo ninho: sonda estreita de ferro com o anel de pouso no topo, casa de
    motor e bomba na base e o poço de cru; a silhueta é uma treliça alta com um anel."""
    p = pal()
    pad(p)
    open_derrick(p, (-0.5, 0, 0.1), 1.4, 0.75, 3.1, lean=(-0.2, 0.0))
    top = 3.2
    box("deck", p["iron_dk"], (-0.7, 0, top), (1.2, 1.2, 0.1), bevel=0.02)
    hollow_ring(p, (-0.7, 0, top + 0.1), 0.95, tone="iron", thick=0.1, n=10)
    # Ninho de couro e lona no anel, e a mancha de cru que escorre pelas pernas.
    cyl("nest", p["hide"], (-0.7, 0, top + 0.1), 0.4, 0.22, sides=9, top_radius=0.5, bevel=0.0)
    cyl("nest_snow", p["snow"], (-0.7, 0, top + 0.3), 0.36, 0.06, sides=9, bevel=0.0)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        box("crude_drip", p["crude"], (-0.5 + sx * 0.7 * 0.55 - 0.1, sy * 0.35, 0.9), (0.07, 0.05, 1.4), bevel=0.0)
    box("lamp_arm", p["iron_dk"], (-0.7, 0.95, top + 0.1), (0.07, 0.07, 0.45), bevel=0.0)
    lamp(p, (-0.7, 0.95, top + 0.55))
    # Casa de motor com telhado de lona inclinado ao sotavento, cilindro único e volante.
    box("engine_house", p["tarp"], (0.55, 0.0, 0.1), (1.2, 1.5, 0.85), bevel=0.03)
    prism("engine_roof", p["snow"], (0.55, 0, 0.95), (1.4, 1.7, 0.45), ridge=0.15, bevel=0.02)
    cyl("engine_cyl", p["iron_dk"], (0.75, -0.2, 0.55), 0.17, 0.5, sides=8, bevel=0.0, rot=("Y", math.radians(90)))
    cyl("flywheel", p["rust"], (1.25, -0.2, 0.4), 0.34, 0.1, sides=10, bevel=0.0, rot=("X", math.radians(90)))
    cyl("stack", p["iron"], (0.2, 0.5, 0.95), 0.1, 0.9, sides=6, bevel=0.0)
    # Balancim da bomba e o poço de cru.
    box("pump_post", p["iron_dk"], (1.3, 0.85, 0.1), (0.14, 0.14, 0.8), bevel=0.0)
    beam("walking_beam", p["iron"], (1.0, 0.85, 1.0), (1.7, 0.85, 0.75), thick=0.1)
    beam("pump_rod", p["soot"], (1.7, 0.85, 0.75), (1.7, 0.85, 0.2), thick=0.04)
    sump(p, (1.4, -1.0, 0.1), 0.42)
    drum(p, (0.9, 1.35, 0.1))
    drift(p, (-1.55, -0.2, 0.1), (0.6, 1.4, 0.5))


def h047_chilling_mushroom():
    """Respiro de gás colonizado por fungos de gelo: tubo-morteiro inclinado com a bola de gelo na boca, cogumelo
    câmara de pressão e três chapéus em tripé apontando para o céu; a válvula enferrujada na base."""
    p = pal()
    pad(p)
    cyl("vent_mound", p["snow"], (0, 0, 0.1), 1.35, 0.5, sides=9, top_radius=0.6, bevel=0.0)
    a, b = Vector((-0.5, 0, 0.5)), Vector((0.8, 0, 2.7))
    beam("tube", p["iron"], a, b, thick=0.48)
    d = (b - a).normalized()
    for t in (0.3, 0.65):
        q = a.lerp(b, t)
        beam("tube_band", p["iron_dk"], q - d * 0.05, q + d * 0.05, thick=0.56)
    beam("tube_mouth", p["iron_dk"], a.lerp(b, 0.94), b, thick=0.64)
    ball("ice_ball", p["ice"], (0.85, 0, 2.85), 0.32, 8)
    # Cogumelo câmara de pressão: o maior, atrás do tubo, com a bexiga inchada.
    cyl("stem_big", p["bone"], (-1.0, 0.5, 0.1), 0.24, 0.9, sides=7, top_radius=0.18, bevel=0.0)
    dome("cap_big", p["fungus"], (-1.0, 0.5, 0.95), 0.68, squash=0.62, sides=10)
    ball("bladder", p["fungus_dk"], (-1.0, 0.5, 1.05), 0.28, 8)
    cyl("cap_big_snow", p["snow"], (-1.0, 0.5, 1.3), 0.28, 0.07, sides=7, bevel=0.0)
    beam("bladder_pipe", p["copper"], (-0.7, 0.4, 0.95), (-0.2, 0.15, 1.1), thick=0.09)
    # Os outros dois chapéus fecham o tripé em volta do tubo, inclinados para a boca.
    for x, y, h, r, tone in ((0.7, 1.0, 0.8, 0.45, "fungus_dk"), (0.6, -1.05, 0.6, 0.42, "fungus")):
        cyl("stem", p["bone"], (x, y, 0.1), 0.17, h, sides=7, top_radius=0.12, bevel=0.0)
        dome("cap", p[tone], (x, y, h + 0.05), r, squash=0.6, sides=10)
        cyl("cap_snow", p["snow"], (x, y, h + 0.05 + r * 0.6 - 0.04), r * 0.4, 0.07, sides=7, bevel=0.0)
    # Válvula enferrujada na base, com a roda, o cano e a lamparina de serviço.
    beam("feed_pipe", p["rust"], (1.1, 0.1, 0.25), (0.5, 0.1, 0.45), thick=0.13)
    cyl("valve_wheel", p["rust"], (1.15, 0.1, 0.25), 0.22, 0.06, sides=8, bevel=0.0, rot=("Y", math.radians(90)))
    box("valve_body", p["iron_dk"], (1.0, 0.1, 0.15), (0.22, 0.22, 0.22), bevel=0.0)
    sump(p, (1.4, -0.7, 0.1), 0.3)
    lamp(p, (1.5, 0.9, 0.1), post=0.7)
    drum(p, (-1.4, -1.0, 0.1))


def h03S_crystal_palace():
    """Catedral da companhia: salão longo de alvenaria de gelo cortada em salmoura, amarrado com fiadas de ferro
    rebitado e telhado carregado de neve ao sotavento; o espinhaço de sonda no teto é a vertical verdadeira."""
    p = pal()
    pad(p)
    box("hall_foot", p["iron_dk"], (-0.5, 0, 0.1), (2.2, 3.4, 0.2), bevel=0.02)
    box("hall", p["ice"], (-0.5, 0, 0.28), (2.0, 3.2, 1.35), bevel=0.04)
    for z in (0.55, 1.0, 1.45):
        box("iron_course", p["iron"], (-0.5, 0, z), (2.06, 3.26, 0.09), bevel=0.0)
    for y in (-1.45, -0.7, 0.7, 1.45):
        box("buttress", p["ice_dk"], (-0.5, y * 1.0, 0.28), (2.12, 0.16, 1.35), bevel=0.02)
    # Telhado de uma água com a cumeeira deslocada: borda alta carregada de neve ao sotavento (-x).
    prism("hall_roof", p["iron_dk"], (-0.5, 0, 1.6), (2.2, 3.4, 0.5), ridge=0.2, bevel=0.02)
    prism("roof_snow", p["snow"], (-0.9, 0, 1.78), (1.2, 3.3, 0.36), ridge=0.15, bevel=0.02)
    # A sonda no espinhaço: treliça com coroa de peneira e a lamparina no topo.
    open_derrick(p, (-0.5, 0, 1.75), 1.5, 0.7, 2.0)
    hollow_ring(p, (-0.5, 0, 3.75), 0.6, tone="iron", thick=0.08, n=8)
    lamp(p, (-0.5, 0, 3.8))
    # Portão rebitado na face da lane com a lamparina e as janelas altas de gelo.
    box("gate", p["soot"], (0.5, 0, 0.28), (0.1, 0.95, 1.0), bevel=0.0)
    for s in (-1, 1):
        box("gate_leaf", p["iron_dk"], (0.55, s * 0.24, 0.28), (0.06, 0.42, 0.96), bevel=0.0)
    box("gate_arch", p["iron"], (0.54, 0, 1.28), (0.14, 1.2, 0.12), bevel=0.0)
    for y in (-1.2, 1.2):
        box("slit", p["soot"], (0.52, y, 0.8), (0.05, 0.22, 0.5), bevel=0.0)
    # O gelo sua cru: gotejamento pelas juntas, a poça e o tambor.
    for y in (-1.0, 0.9):
        box("crude_weep", p["crude"], (0.51, y, 0.3), (0.04, 0.07, 0.8), bevel=0.0)
    sump(p, (1.1, -0.9, 0.1), 0.35)
    drum(p, (1.1, 1.2, 0.1))
    drift(p, (-1.7, 0.0, 0.1), (0.5, 3.0, 0.5))


def h07W_snowveil_fountain():
    """Gêiser congelado: prumada de perfuração que estoura numa pluma petrificada de gelo e óleo, com a rede de
    fraturas na superfície, a roda de válvula e as estacas de pressão."""
    p = pal()
    pad(p)
    # Rede de fraturas no chão: rachaduras escuras e a borda de gelo estilhaçado.
    for i in range(7):
        a = math.radians(i * 51 + 10)
        L = 1.5 - 0.15 * (i % 3)
        box("fracture", p["soot"], (math.cos(a) * L * 0.55, math.sin(a) * L * 0.55, 0.1), (L, 0.07, 0.015), bevel=0.0, rot_z=a)
    cyl("crater", p["snow_dk"], (0, 0, 0.1), 1.05, 0.3, sides=10, top_radius=0.75, bevel=0.0)
    cyl("crater_oil", p["crude"], (0, 0, 0.4), 0.55, 0.03, sides=9, bevel=0.0)
    cyl("standpipe", p["iron"], (0, 0, 0.4), 0.2, 1.3, sides=8, bevel=0.0)
    ring("pipe_band", p["iron_dk"], (0, 0, 0.9), 0.2, 0.1, sides=8)
    # A pluma: coluna central de gelo com camadas de cru e o leque de lâminas que cai para fora.
    cyl("plume_core", p["ice"], (0, 0, 1.7), 0.38, 1.35, sides=7, top_radius=0.16, bevel=0.0)
    cyl("plume_crude", p["crude"], (0, 0, 2.2), 0.3, 0.2, sides=7, top_radius=0.22, bevel=0.0)
    cyl("plume_tip", p["snow"], (0, 0, 3.0), 0.16, 0.5, sides=6, top_radius=0.02, bevel=0.0)
    for i in range(8):
        a = math.radians(i * 45 + 8)
        kit.horn(p["ice" if i % 2 == 0 else "ice_dk"], (math.cos(a) * 0.2, math.sin(a) * 0.2, 1.65), (math.cos(a), math.sin(a)), length=1.45 if i % 2 == 0 else 1.1, radius=0.17)
    for i in range(4):
        a = math.radians(i * 90 + 40)
        box("ice_spike", p["snow"], (math.cos(a) * 0.55, math.sin(a) * 0.55, 1.95), (0.1, 0.1, 0.5), bevel=0.0, taper=0.2, taper_y=0.2)
    # Roda de válvula em tubo lateral e as estacas de pressão com bandeirola de aviso.
    beam("side_pipe", p["rust"], (0.3, 0.2, 0.5), (1.2, 0.85, 0.5), thick=0.12)
    box("valve_stem", p["iron_dk"], (1.2, 0.85, 0.1), (0.1, 0.1, 0.65), bevel=0.0)
    hollow_ring(p, (1.2, 0.85, 0.78), 0.3, tone="rust", thick=0.07, n=8)
    for x, y in ((1.2, -0.8), (0.4, -1.4), (-1.3, 1.1)):
        box("stake", p["wood_dk"], (x, y, 0.1), (0.07, 0.07, 0.65), bevel=0.0)
        box("stake_flag", p["rust"], (x, y + 0.08, 0.5), (0.03, 0.2, 0.15), bevel=0.0)
    lamp(p, (1.55, 0.0, 0.1), post=0.8)
    drum(p, (-1.4, -0.9, 0.1))


def h03O_world_freezer():
    """Estação-relógio de pressão: monte cônico de neve sobre três garrafas acumuladoras num coletor ortogonal
    rebitado, com o grande mostrador e o escape; as três órbitas de gelo nos berços são a contagem regressiva."""
    p = pal()
    pad(p)
    cyl("mound", p["snow"], (-0.35, 0, 0.1), 1.6, 1.2, sides=10, top_radius=0.55, bevel=0.0)
    cyl("mound_dirt", p["snow_dk"], (-0.35, 0, 0.1), 1.65, 0.2, sides=10, bevel=0.0)
    # Coletor ortogonal: quadro de tubos sobre o monte, rebitado.
    box("manifold_base", p["iron_dk"], (0, 0, 0.1), (1.0, 2.6, 0.18), bevel=0.02)
    beam("manifold", p["iron"], (0.4, -1.1, 0.55), (0.4, 1.1, 0.55), thick=0.17)
    beam("manifold_back", p["iron"], (-0.4, -1.1, 0.55), (-0.4, 1.1, 0.55), thick=0.14)
    for y in (-0.95, 0.0, 0.95):
        beam("manifold_link", p["iron"], (-0.4, y, 0.55), (0.4, y, 0.55), thick=0.12)
        # Garrafa acumuladora vertical com os anéis, a cúpula e o berço da órbita.
        cyl("bottle", p["iron"], (0.0, y, 0.2), 0.3, 2.0, sides=9, bevel=0.0)
        for z in (0.7, 1.4):
            ring("bottle_band", p["iron_dk"], (0.0, y, z), 0.3, 0.09, sides=9)
        dome("bottle_dome", p["iron"], (0.0, y, 2.2), 0.3, squash=0.7, sides=9)
        for a in range(3):
            ar = math.radians(a * 120 + 30)
            beam("orb_cradle", p["iron_dk"], (math.cos(ar) * 0.1, y + math.sin(ar) * 0.1, 2.35), (math.cos(ar) * 0.3, y + math.sin(ar) * 0.3, 2.65), thick=0.05)
        ball("orb", p["ice"], (0.0, y, 2.7), 0.28, 8)
    # Mostrador grande voltado para a lane, escape de relojoaria ao lado e a lamparina.
    cyl("gauge_post", p["iron_dk"], (1.3, 0, 0.1), 0.1, 0.65, sides=6, bevel=0.0)
    cyl("gauge_rim", p["iron_dk"], (1.3, 0, 0.75), 0.68, 0.14, sides=12, bevel=0.0, rot=("Y", math.radians(90)))
    cyl("gauge_face", p["bone"], (1.38, 0, 0.75), 0.58, 0.05, sides=12, bevel=0.0, rot=("Y", math.radians(90)))
    beam("gauge_needle", p["soot"], (1.45, 0, 0.75), (1.45, 0.28, 1.1), thick=0.05)
    beam("gauge_needle2", p["lamp"], (1.45, 0, 0.75), (1.45, -0.3, 0.55), thick=0.04)
    for i in range(8):
        a = math.radians(i * 45)
        box("gauge_tick", p["soot"], (1.44, math.cos(a) * 0.5, 0.75 + math.sin(a) * 0.5), (0.03, 0.06, 0.06), bevel=0.0)
    cyl("escape_gear", p["rust"], (1.1, -1.2, 0.4), 0.28, 0.12, sides=8, bevel=0.0, rot=("Y", math.radians(90)))
    cyl("escape_gear2", p["iron_dk"], (1.1, -1.55, 0.55), 0.18, 0.12, sides=8, bevel=0.0, rot=("Y", math.radians(90)))
    lamp(p, (1.45, 1.2, 0.1), post=0.7)
    drum(p, (-1.5, 1.35, 0.1))


BUILDINGS = {
    "h03I": h03I_azure_nest,
    "h047": h047_chilling_mushroom,
    "h03S": h03S_crystal_palace,
    "h043": h043_frost_claws,
    "h048": h048_frost_launcher,
    "h03W": h03W_glacier,
    "h03L": h03L_greater_frost_launcher,
    "h03T": h03T_ice_claws,
    "h03K": h03K_ice_troll_hut,
    "h03J": h03J_voodoo_lounge,
    "h04F": h04F_icy_rocks,
    "h03Q": h03Q_icy_tower,
    "h03U": h03U_igloo,
    "h06L": h06L_modern_igloo,
    "h07W": h07W_snowveil_fountain,
    "h049": h049_snowy_rocks,
    "h03O": h03O_world_freezer,
}


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["all"]
    names = list(BUILDINGS) if args[0] == "all" else [args[0]]
    out_dir = args[args.index("--out") + 1] if "--out" in args else ""
    render_dir = args[args.index("--render") + 1] if "--render" in args else ""
    for name in names:
        kit.build(name, out_dir, render_dir, make=BUILDINGS[name], views=(("front", -35.0),))


if __name__ == "__main__":
    main()
