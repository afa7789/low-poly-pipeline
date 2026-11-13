"""Mapa Clássico (docs/maps.md) modelado por script: os dois castelos, as peças de muralha e o campo em volta.

Uso:
    blender -b --factory-startup --python tools/blender/map_classic.py -- <nome|all|castles|scenery>
        [--out DIR_CENARIO] [--castles-out DIR_CASTELOS] [--render DIR]

Região de castelos medievais de um mundo de 1914: pedra, telhado de ardósia, feno, flores. Só uma sombra de
guerra (rolo de arame, ninho de sacos, caixotes) entra, em ~3% das peças. Tamanhos seguem map_castles.py.
"""

import math
import os
import sys

from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_paths  # noqa: E402
import map_castles as kit
from map_castles import beam, box, cyl, mat, prism, ring
from map_scenery import normalize, sandbag, wire_coil

# ---------------------------------------------------------------------------------------------------------
# Kit de pedra medieval
# ---------------------------------------------------------------------------------------------------------


def pyramid(material, center, half, height, rot_z=0.0):
    """Telhado piramidal (quatro águas) sobre uma torre quadrada de meia-largura `half`."""
    return cyl("pyramid", material, center, half * math.sqrt(2), height, sides=4, top_radius=0.0, bevel=0.0, rot=("Z", math.pi / 4 + rot_z))


def cone_roof(material, trim, center, radius, height, finial=None, eave=0.14, sides=12):
    """Telhado cônico com beiral e (opcional) esfera/ponta dourada."""
    x, y, z = center
    cyl("eave", trim, (x, y, z), radius + eave, 0.07, sides=sides, bevel=0.0)
    cyl("cone_roof", material, (x, y, z + 0.05), radius + eave * 0.6, height, sides=sides, top_radius=0.0, bevel=0.0)
    if finial is not None:
        cyl("finial", finial, (x, y, z + height * 0.98), 0.06, 0.22, sides=6, top_radius=0.0, bevel=0.0)
        cyl("finial_ball", finial, (x, y, z + height * 0.9), 0.08, 0.1, sides=6, bevel=0.0)


def crown_merlons(stone, center, radius, z, count, size=(0.2, 0.12, 0.17)):
    """Ameias em volta de uma torre redonda."""
    for i in range(count):
        a = i * math.tau / count
        pos = (center[0] + math.cos(a) * radius, center[1] + math.sin(a) * radius, z)
        box("merlon", stone, pos, size, bevel=0.015, rot_z=a)


def slits(dark, center, radius, z, count, h=0.34, w=0.07, start=0.0):
    """Seteiras estreitas e escuras em volta de uma torre redonda."""
    for i in range(count):
        a = start + i * math.tau / count
        pos = (center[0] + math.cos(a) * (radius - 0.01), center[1] + math.sin(a) * (radius - 0.01), z)
        box("slit", dark, pos, (0.05, w, h), bevel=0.0, rot_z=a)


def round_tower(p, pos, r, h, roof=None, roof_h=1.0, crenel=0, sides=12, stone="stone", trim="trim", slit_n=3, finial="gold"):
    """Torre redonda em talude com cinta, balcão, convés claro e telhado cônico ou ameias."""
    x, y = pos
    cyl("tower_foot", p["foot"], (x, y, 0), r * 1.2, 0.2, sides=sides, top_radius=r * 1.1, bevel=0.0)
    cyl("tower", p[stone], (x, y, 0.16), r * 1.08, h - 0.16, sides=sides, top_radius=r * 0.94, bevel=0.0)
    ring("tower_band", p[trim], (x, y, h * 0.52), r * 1.0, 0.09, thick=0.05, sides=sides)
    cyl("corbel", p[trim], (x, y, h - 0.12), r * 1.12, 0.14, sides=sides, top_radius=r * 1.2, bevel=0.0)
    cyl("deck", p["deck"], (x, y, h + 0.02), r * 1.18, 0.05, sides=sides, bevel=0.0)
    slits(p["dark"], (x, y), r * 1.0, h * 0.36, slit_n, start=0.5)
    if roof is not None:
        cone_roof(p[roof], p[trim], (x, y, h + 0.07), r * 1.0, roof_h, finial=p[finial] if finial else None, sides=sides)
    elif crenel:
        crown_merlons(p["deck"], (x, y), r * 1.14, h + 0.07, crenel)


def square_tower(p, pos, half, h, roof, roof_h, stone="stone", trim="trim", finial="gold"):
    """Torre quadrada em talude com cinta, convés claro, janelas e telhado piramidal."""
    x, y = pos
    box("sq_foot", p["foot"], (x, y, 0), (half * 2.5, half * 2.5, 0.2), bevel=0.02, taper=0.94, taper_y=0.94)
    box("sq_tower", p[stone], (x, y, 0.16), (half * 2.1, half * 2.1, h - 0.16), bevel=0.03, taper=0.9, taper_y=0.9)
    box("sq_band", p[trim], (x, y, h * 0.55), (half * 2.0, half * 2.0, 0.08), bevel=0.0)
    box("sq_corbel", p[trim], (x, y, h - 0.1), (half * 2.35, half * 2.35, 0.14), bevel=0.02)
    box("sq_deck", p["deck"], (x, y, h + 0.03), (half * 2.4, half * 2.4, 0.05), bevel=0.0)
    for sx in (-1, 1):
        kit.window(p["dark"], p["glass"], (x + sx * half * 0.95, y, h * 0.7), "x+" if sx > 0 else "x-", w=0.1, h=0.3)
        kit.window(p["dark"], p["glass"], (x, y + sx * half * 0.95, h * 0.7), "y+" if sx > 0 else "y-", w=0.1, h=0.3)
    pyramid(p[roof], (x, y, h + 0.08), half * 1.25, roof_h)
    if finial:
        cyl("sq_finial", p[finial], (x, y, h + 0.08 + roof_h * 0.95), 0.07, 0.3, sides=6, top_radius=0.0, bevel=0.0)


def flag(p, pos, height=0.9, facing=0.0, cloth="cloth"):
    kit.banner(p["pole"], p[cloth], pos, height=height, facing=facing)


def courtyard_well(p, pos):
    x, y = pos
    cyl("well", p["stone"], (x, y, 0.1), 0.26, 0.26, sides=10, bevel=0.0)
    cyl("well_water", p["water"], (x, y, 0.33), 0.2, 0.02, sides=10, bevel=0.0)
    for s in (-1, 1):
        box("well_post", p["wood"], (x, y + s * 0.22, 0.1), (0.05, 0.05, 0.5), bevel=0.0)
    prism("well_roof", p["roof"], (x, y, 0.6), (0.34, 0.6, 0.18), ridge=0.5)


# ---------------------------------------------------------------------------------------------------------
# Sentinel: calcário claro, ardósia azul, ouro; capela com campanário
# ---------------------------------------------------------------------------------------------------------


def sentinel_palette():
    return {
        "stone": mat("limestone", 0xD3CAB2),
        "foot": mat("limestone_foot", 0xA89F89),
        "trim": mat("limestone_trim", 0xB9B09A),
        "deck": mat("limestone_deck", 0xEEE7D2),
        "yard": mat("yard_flag", 0xCBC2A8),
        "path": mat("yard_path", 0xE6DEC6),
        "plinth": mat("plinth_stone", 0x8F8A79),
        "roof": mat("slate_blue", 0x3C69B4),
        "roof_lt": mat("slate_light", 0x6A97D6),
        "gold": mat("gold", 0xE8B93A),
        "dark": mat("window_dark", 0x2F3A4C),
        "glass": mat("window_glow", 0xF6D27A, emit=1.2),
        "door": mat("oak_door", 0x5A4128),
        "wood": mat("oak", 0x6E5236),
        "cloth": mat("banner_blue", 0x2E5EBB),
        "pole": mat("pole", 0x3A3028),
        "water": mat("well_water", 0x4A86C8),
        "moss": mat("moss", 0x6E8A4A),
    }


def sentinel():
    """Castelo azul (oeste): fortaleza clara, cortina com bastiões redondos, portaria saliente e capela com campanário."""
    p = sentinel_palette()
    half = 2.6
    box("plinth", p["plinth"], (0, 0, 0), (half * 2 + 0.5, half * 2 + 0.3, 0.14), bevel=0.05, taper=0.96, taper_y=0.96)
    box("yard", p["yard"], (0, 0, 0.12), (half * 2 - 0.4, half * 2 - 0.6, 0.07), bevel=0.02)
    w = 2.1
    # Cortinas em talude: fundo e laterais inteiros; a frente em duas metades ladeando a portaria.
    for along_x, fixed in ((True, w), (True, -w), (False, -w)):
        kit.battered_wall(p["stone"], p["foot"], -w + 0.7, w - 0.7, fixed, along_x, height=1.2, thick=0.7, cap=p["deck"], n_merlons=5)
    kit.battered_wall(p["stone"], p["foot"], -w + 0.7, -0.85, w, False, height=1.2, thick=0.7, cap=p["deck"], n_merlons=2)
    kit.battered_wall(p["stone"], p["foot"], 0.85, w - 0.7, w, False, height=1.2, thick=0.7, cap=p["deck"], n_merlons=2)
    # Convés claro e musgo no pé: o plano de cima é o que a câmera lê.
    for s in (-1, 1):
        box("walk", p["deck"], (0, s * w, 1.22), (2 * w - 1.7, 0.36, 0.05), bevel=0.0)
        for t in (-1.2, 0.2, 1.1):
            box("moss", p["moss"], (t, s * (w + 0.3), 0.0), (0.5, 0.1, 0.22), bevel=0.02, taper=0.7)
    box("walk", p["deck"], (-w, 0, 1.22), (0.36, 2 * w - 1.7, 0.05), bevel=0.0)
    # Bastiões nos cantos, para fora da linha da muralha, cada um de um jeito.
    round_tower(p, (w, w), 0.92, 1.95, roof="roof", roof_h=1.2)
    round_tower(p, (w, -w), 0.78, 1.5, crenel=9, slit_n=2)
    flag(p, (w, -w, 1.55), height=0.95, facing=0.0)
    square_tower(p, (-w, w), 0.72, 2.2, "roof", 1.05)
    round_tower(p, (-w, -w), 1.0, 2.05, roof="roof", roof_h=1.45, slit_n=4)
    # Guarita (bartizã) pendurada no flanco do torreão de trás.
    round_tower(p, (-w - 0.75, -w + 0.75), 0.3, 1.35, roof="roof_lt", roof_h=0.55, sides=8, slit_n=1)

    # Portaria saliente virada para a lane: bloco, arco escuro, duas torrinhas, telhado de ardósia e estandartes.
    gx = w + 0.45
    box("gate_block", p["stone"], (gx, 0, 0.1), (1.05, 1.7, 1.55), bevel=0.04, taper=0.92, taper_y=0.94)
    box("gate_trim", p["trim"], (gx, 0, 1.0), (1.0, 1.62, 0.09), bevel=0.0)
    box("gate_cap", p["deck"], (gx, 0, 1.64), (1.1, 1.78, 0.1), bevel=0.02)
    kit.merlons(p["deck"], -0.78, 0.78, 1.74, 4, (0.22, 0.14, 0.18, gx + 0.38), False)
    box("gate_door", p["door"], (gx + 0.49, 0, 0.1), (0.07, 0.78, 0.86), bevel=0.0)
    cyl("gate_arch", p["door"], (gx + 0.49, 0, 0.92), 0.39, 0.07, sides=12, bevel=0.0, rot=("Y", math.radians(90)))
    for dy in (-0.25, 0.0, 0.25):
        box("gate_plank", p["wood"], (gx + 0.54, dy, 0.12), (0.03, 0.02, 1.05), bevel=0.0)
    box("gate_keystone", p["gold"], (gx + 0.5, 0, 1.28), (0.06, 0.16, 0.14), bevel=0.0)
    for s in (-1, 1):
        round_tower(p, (gx + 0.15, s * 1.05), 0.34, 1.9, roof="roof_lt", roof_h=0.8, sides=8, slit_n=2)
        flag(p, (gx + 0.6, s * 0.62, 1.0), height=1.0, facing=0.0)
    # Telhado de duas águas da casa do portão, atrás das ameias.
    prism("gate_roof", p["roof"], (gx - 0.1, 0, 1.74), (0.8, 1.2, 0.5), ridge=0.5, rot_z=math.radians(90))

    # Torre de menagem em degraus: base, andar menor, campanário esguio com flecha de ardósia e capela de lado.
    kx = -0.55
    box("keep_base", p["stone"], (kx, 0.1, 0.14), (2.5, 2.3, 1.45), bevel=0.05, taper=0.93, taper_y=0.93)
    box("keep_band", p["trim"], (kx, 0.1, 1.5), (2.45, 2.2, 0.1), bevel=0.02)
    box("keep_deck", p["deck"], (kx, 0.1, 1.6), (2.4, 2.18, 0.05), bevel=0.0)
    kit.merlons(p["deck"], kx - 1.0, kx + 1.0, 1.68, 5, (0.2, 0.13, 0.17, 1.08), True)
    kit.merlons(p["deck"], kx - 1.0, kx + 1.0, 1.68, 5, (0.2, 0.13, 0.17, -0.88), True)
    for y in (-0.55, 0.1, 0.75):
        kit.window(p["dark"], p["glass"], (kx + 1.25, y, 0.75), "x+", w=0.14, h=0.4)
    for x in (kx - 0.6, kx + 0.15):
        kit.window(p["dark"], p["glass"], (x, 1.25, 0.75), "y+", w=0.14, h=0.4)
    box("keep_mid", p["stone"], (kx - 0.2, -0.1, 1.6), (1.55, 1.45, 0.85), bevel=0.04, taper=0.92, taper_y=0.92)
    box("keep_mid_trim", p["trim"], (kx - 0.2, -0.1, 2.42), (1.6, 1.5, 0.08), bevel=0.0)
    box("keep_mid_deck", p["deck"], (kx - 0.2, -0.1, 2.5), (1.5, 1.4, 0.05), bevel=0.0)
    for y in (-0.4, 0.2):
        kit.window(p["dark"], p["glass"], (kx - 0.2 + 0.78, y, 2.0), "x+", w=0.12, h=0.34)
    bx, by = kx - 0.35, -0.1
    box("belfry", p["stone"], (bx, by, 2.5), (0.9, 0.9, 0.9), bevel=0.03, taper=0.92, taper_y=0.92)
    box("belfry_band", p["gold"], (bx, by, 3.0), (0.94, 0.94, 0.06), bevel=0.0)
    for s in (-1, 1):
        box("belfry_arch", p["dark"], (bx + s * 0.44, by, 3.02), (0.04, 0.24, 0.32), bevel=0.0)
        box("belfry_arch", p["dark"], (bx, by + s * 0.44, 3.02), (0.24, 0.04, 0.32), bevel=0.0)
    box("belfry_eave", p["trim"], (bx, by, 3.4), (1.08, 1.08, 0.08), bevel=0.02)
    pyramid(p["roof"], (bx, by, 3.46), 0.62, 1.15)
    cyl("spire_tip", p["gold"], (bx, by, 4.5), 0.07, 0.22, sides=6, top_radius=0.0, bevel=0.0)
    # Capela: nave de duas águas na laje da base, com cruz dourada, de frente para a lane.
    box("chapel", p["stone"], (kx + 0.7, -0.62, 1.6), (1.0, 0.8, 0.55), bevel=0.03)
    prism("chapel_roof", p["roof"], (kx + 0.7, -0.62, 2.12), (1.14, 0.9, 0.5), ridge=0.5, rot_z=0.0)
    kit.window(p["dark"], p["glass"], (kx + 1.2, -0.62, 1.8), "x+", w=0.14, h=0.28)
    box("chapel_cross", p["gold"], (kx + 0.7, -0.62, 2.6), (0.05, 0.05, 0.22), bevel=0.0)
    box("chapel_cross", p["gold"], (kx + 0.7, -0.62, 2.7), (0.05, 0.15, 0.05), bevel=0.0)
    # Pátio: caminho claro até a porta, poço e estandarte alto.
    box("path", p["path"], (1.0, 0.1, 0.17), (2.0, 0.55, 0.03), bevel=0.0)
    courtyard_well(p, (0.9, 1.1))
    for i, (dx, dy) in enumerate(((1.2, -1.2), (0.7, -1.45), (1.5, -0.8))):
        box("crate", p["wood"], (dx, dy, 0.17), (0.26, 0.26, 0.24), bevel=0.02, rot_z=0.4 * i)
    flag(p, (kx - 1.1, 0.7, 1.65), height=1.3, facing=math.pi / 2)


# ---------------------------------------------------------------------------------------------------------
# Scourge: basalto, carmesim, ferro; menagem soturna com agulha e olho
# ---------------------------------------------------------------------------------------------------------


def scourge_palette():
    return {
        "stone": mat("basalt_wall", 0x433F4D),
        "foot": mat("basalt_foot", 0x2A2733),
        "trim": mat("basalt_trim", 0x332F3C),
        "deck": mat("basalt_deck", 0x7C768B),
        "yard": mat("yard_dark", 0x6A657A),
        "path": mat("yard_path_dk", 0x8D8799),
        "plinth": mat("plinth_dark", 0x2A2731),
        "roof": mat("crimson_roof", 0x9A2433),
        "roof_lt": mat("crimson_light", 0xC23A48),
        "gold": mat("iron_spike", 0x1D1B25),
        "dark": mat("slit_dark", 0x15131B),
        "glass": mat("ember_glass", 0xFF6A30, emit=2.5),
        "door": mat("iron_door", 0x24222C),
        "wood": mat("black_oak", 0x4A3828),
        "cloth": mat("banner_crimson", 0xB02A3C),
        "pole": mat("pole_iron", 0x1D1B25),
        "water": mat("moat", 0x2C3A44),
        "bone": mat("bone", 0xD9D1BA),
        "moss": mat("lichen", 0x55603E),
    }


def spike_crown(p, pos, r, z, count, height=0.32):
    """Coroa de espinhos de ferro numa torre."""
    for i in range(count):
        a = i * math.tau / count
        kit.spike(p["gold"], (pos[0] + math.cos(a) * r, pos[1] + math.sin(a) * r, z), height=height, radius=0.045, lean=(math.cos(a) * 0.05, math.sin(a) * 0.05))


def gothic_tower(p, pos, r, h, roof_h, sides=8, lean=0.0):
    """Torre octogonal esguia de basalto com cinta, convés claro e cone carmesim eriçado de espinhos."""
    x, y = pos
    round_tower(p, pos, r, h, roof="roof", roof_h=roof_h, sides=sides, slit_n=sides // 2, finial=None)
    kit.spike(p["gold"], (x, y, h + 0.07 + roof_h - 0.05), height=0.5, radius=0.05, lean=(lean, 0))
    spike_crown(p, pos, r * 1.15, h + 0.07, sides, height=0.28)


def scourge():
    """Castelo vermelho (leste): fortaleza de basalto, bastiões em planta quebrada, portão com ponte levadiça, menagem e agulha."""
    p = scourge_palette()
    half = 2.6
    box("plinth", p["plinth"], (0, 0, 0), (half * 2 + 0.5, half * 2 + 0.2, 0.16), bevel=0.06, taper=0.94, taper_y=0.94)
    box("yard", p["yard"], (0, 0, 0.14), (half * 2 - 0.5, half * 2 - 0.8, 0.07), bevel=0.02)
    w = 2.15
    # Cortinas: o fundo encurtado e dois flancos; no canto de trás-direita a muralha corta em diagonal.
    kit.battered_wall(p["stone"], p["foot"], -w + 0.6, w - 0.6, w, True, height=1.25, thick=0.78, cap=p["deck"], n_merlons=5)
    kit.battered_wall(p["stone"], p["foot"], -w + 0.5, w - 0.7, -w, True, height=1.25, thick=0.78, cap=p["deck"], n_merlons=5)
    kit.battered_wall(p["stone"], p["foot"], -w + 0.9, w - 0.9, -w, False, height=1.25, thick=0.78, cap=p["deck"], n_merlons=4)
    kit.battered_wall(p["stone"], p["foot"], -w + 0.7, -0.9, w, False, height=1.25, thick=0.78, cap=p["deck"], n_merlons=2)
    kit.battered_wall(p["stone"], p["foot"], 0.9, w - 0.7, w, False, height=1.25, thick=0.78, cap=p["deck"], n_merlons=2)
    for s in (-1, 1):
        box("walk", p["deck"], (0, s * w, 1.27), (2 * w - 1.7, 0.4, 0.05), bevel=0.0)
        for t in (-1.4, -0.5, 0.4, 1.3):
            kit.spike(p["gold"], (t, s * (w + 0.5), 0.1), height=0.55, radius=0.07, lean=(0.0, s * 0.3))
    box("walk", p["deck"], (-w, 0, 1.27), (0.4, 2 * w - 1.7, 0.05), bevel=0.0)
    # Torres góticas: duas altas na frente, uma esguia e torta atrás, uma atarracada de canto cortado.
    gothic_tower(p, (w, w), 0.82, 2.3, 1.2)
    gothic_tower(p, (w, -w), 0.7, 1.85, 1.0, lean=0.05)
    gothic_tower(p, (-w, w), 0.66, 2.7, 1.55, lean=-0.06)
    round_tower(p, (-w, -w), 1.05, 1.5, crenel=10, slit_n=3)
    spike_crown(p, (-w, -w), 1.2, 1.57, 10, height=0.3)
    # Portão gótico com grade de ferro, dois dentes de osso e ponte levadiça baixada sobre o fosso.
    gx = w + 0.4
    box("gate_block", p["stone"], (gx, 0, 0.1), (1.0, 1.8, 1.7), bevel=0.04, taper=0.88, taper_y=0.92)
    box("gate_trim", p["trim"], (gx, 0, 1.05), (1.04, 1.74, 0.09), bevel=0.0)
    box("gate_cap", p["deck"], (gx, 0, 1.78), (1.08, 1.84, 0.1), bevel=0.02)
    kit.merlons(p["deck"], -0.8, 0.8, 1.88, 4, (0.22, 0.14, 0.2, gx + 0.38), False)
    box("gate_maw", p["dark"], (gx + 0.46, 0, 0.12), (0.1, 0.84, 1.0), bevel=0.0)
    cyl("gate_arch", p["dark"], (gx + 0.46, 0, 1.0), 0.42, 0.1, sides=3, bevel=0.0, rot=("Y", math.radians(90)))
    for y in (-0.3, -0.1, 0.1, 0.3):
        box("gate_bar", p["door"], (gx + 0.53, y, 0.14), (0.04, 0.05, 1.1), bevel=0.0)
    for z in (0.4, 0.8):
        box("gate_cross", p["door"], (gx + 0.54, 0, z), (0.04, 0.84, 0.05), bevel=0.0)
    for s in (-1, 1):
        kit.horn(p["bone"], (gx + 0.5, s * 0.75, 1.3), (1.0, 0.0), length=0.8, radius=0.14)
        flag(p, (gx + 0.5, s * 1.0, 1.0), height=1.3, facing=0.0)
    box("bridge", p["wood"], (gx + 0.8, 0, 0.02), (0.6, 0.9, 0.06), bevel=0.01)
    for x in (0.65, 0.8, 0.95):
        box("bridge_plank", p["door"], (gx + x, 0, 0.07), (0.03, 0.9, 0.02), bevel=0.0)
    for s in (-1, 1):
        beam("bridge_chain", p["door"], (gx + 0.5, s * 0.42, 1.0), (gx + 1.05, s * 0.42, 0.1), thick=0.03)

    # Menagem soturna em degraus, com torrinhas de canto, telhado carmesim e uma agulha de ferro com o olho.
    kx = -0.5
    box("keep_base", p["stone"], (kx, -0.05, 0.16), (2.6, 2.5, 1.5), bevel=0.05, taper=0.88, taper_y=0.88)
    box("keep_lip", p["trim"], (kx, -0.05, 1.62), (2.4, 2.3, 0.1), bevel=0.02)
    box("keep_deck", p["deck"], (kx, -0.05, 1.72), (2.3, 2.2, 0.05), bevel=0.0)
    kit.merlons(p["deck"], kx - 1.0, kx + 1.0, 1.78, 5, (0.2, 0.13, 0.17, 1.02), True)
    kit.merlons(p["deck"], kx - 1.0, kx + 1.0, 1.78, 5, (0.2, 0.13, 0.17, -1.12), True)
    for y in (-0.7, -0.05, 0.6):
        kit.window(p["dark"], p["glass"], (kx + 1.27, y, 0.75), "x+", w=0.12, h=0.42)
    for x in (kx - 0.6, kx + 0.2):
        kit.window(p["dark"], p["glass"], (x, 1.2, 0.75), "y+", w=0.12, h=0.42)
    box("keep_mid", p["stone"], (kx - 0.25, 0.1, 1.72), (1.55, 1.5, 0.95), bevel=0.04, taper=0.9, taper_y=0.9)
    box("keep_mid_trim", p["trim"], (kx - 0.25, 0.1, 2.62), (1.62, 1.56, 0.09), bevel=0.0)
    box("keep_mid_deck", p["deck"], (kx - 0.25, 0.1, 2.71), (1.5, 1.44, 0.05), bevel=0.0)
    for sx, sy, hh in ((1, 1, 0.75), (1, -1, 1.0), (-1, 1, 0.9), (-1, -1, 0.7)):
        tx, ty = kx - 0.25 + sx * 0.72, 0.1 + sy * 0.7
        cyl("turret", p["stone"], (tx, ty, 2.7), 0.2, hh, sides=8, top_radius=0.17, bevel=0.0)
        cyl("turret_roof", p["roof"], (tx, ty, 2.7 + hh), 0.27, 0.45, sides=8, top_radius=0.0, bevel=0.0)
    kit.window(p["dark"], p["glass"], (kx - 0.25 + 0.77, 0.1, 2.15), "x+", w=0.12, h=0.4)
    # Salão de telhado carmesim encostado na face da lane e agulha central de ferro.
    box("hall", p["stone"], (kx + 0.62, 0.55, 1.72), (0.9, 0.7, 0.55), bevel=0.03)
    prism("hall_roof", p["roof"], (kx + 0.62, 0.55, 2.27), (1.04, 0.84, 0.46), ridge=0.5)
    sx_, sy_ = kx - 0.3, 0.12
    cyl("spire_base", p["trim"], (sx_, sy_, 2.76), 0.34, 0.5, sides=8, top_radius=0.26, bevel=0.0)
    cyl("spire", p["gold"], (sx_, sy_, 3.2), 0.12, 1.5, sides=6, top_radius=0.05, bevel=0.0)
    for i in range(4):
        a = i * math.pi / 2 + 0.4
        kit.spike(p["gold"], (sx_ + math.cos(a) * 0.2, sy_ + math.sin(a) * 0.2, 3.3), height=0.6, radius=0.05, lean=(math.cos(a) * 0.25, math.sin(a) * 0.25))
    # Pátio: caminho escuro, gaiola de ferro, barris e estandarte rasgado.
    box("path", p["path"], (0.95, 0.0, 0.2), (2.0, 0.55, 0.03), bevel=0.0)
    cyl("brazier_bowl", p["gold"], (1.0, -1.15, 0.2), 0.14, 0.2, sides=8, top_radius=0.22, bevel=0.0)
    cyl("brazier_fire", p["glass"], (1.0, -1.15, 0.38), 0.16, 0.05, sides=8, bevel=0.0)
    for i, (dx, dy) in enumerate(((1.2, 1.2), (0.8, 1.45))):
        cyl("barrel", p["wood"], (dx, dy, 0.2), 0.14, 0.3, sides=8, bevel=0.0)
    flag(p, (kx - 1.15, -0.8, 1.8), height=1.4, facing=math.pi / 2)


# ---------------------------------------------------------------------------------------------------------
# Muralha, pilar, vão do portão e fonte (pedra clara com musgo)
# ---------------------------------------------------------------------------------------------------------


def field_palette():
    return {
        "stone": mat("c_stone", 0xB1A890),
        "stone_dk": mat("c_stone_dark", 0x857E6E),
        "stone_lt": mat("c_stone_light", 0xD0C7AE),
        "moss": mat("c_moss", 0x6C8A48),
        "slate": mat("c_slate", 0x4F6E9E),
        "slate_lt": mat("c_slate_light", 0x7A9ACB),
        "gold": mat("c_gold", 0xE2B23A),
        "wood": mat("c_wood", 0x7A5A38),
        "wood_dk": mat("c_wood_dark", 0x4C3826),
        "thatch": mat("c_thatch", 0xCFAA58),
        "thatch_dk": mat("c_thatch_dark", 0xA8843F),
        "plaster": mat("c_plaster", 0xE6DDC4),
        "water": mat("c_water", 0x4C95DA),
        "spray": mat("c_spray", 0xBFE2F8),
        "lamp": mat("c_lamp", 0xFFC658, emit=3.0),
        "dark": mat("c_dark", 0x2B2F3A),
        "banner": mat("c_banner", 0xC8A03A),
        "leaf": mat("c_leaf", 0x468A3C),
        "leaf_lt": mat("c_leaf_light", 0x6CA848),
        "pink": mat("c_pink", 0xE0679A),
        "white": mat("c_white", 0xF6F1E2),
        "yellow": mat("c_yellow", 0xF2CC3E),
        "purple": mat("c_purple", 0x8E62CC),
        "red": mat("c_red", 0xD0382E),
        "hay": mat("c_hay", 0xDDBE60),
        "hay_dk": mat("c_hay_dark", 0xB89A44),
        "iron": mat("c_iron", 0x34373C),
        "canvas": mat("c_canvas", 0xB2A57E),
        "olive": mat("c_olive", 0x6E6E4C),
        "earth": mat("c_earth", 0x7E6444),
    }


def cls_wall():
    """Cortina de pedra: talude, fiadas, seteiras, musgo, convés claro e ameias nos dois lados."""
    p = field_palette()
    length = 3.2
    box("foot", p["stone_dk"], (0, 0, 0), (length, 1.0, 0.3), bevel=0.04)
    box("body", p["stone"], (0, 0, 0.22), (length, 0.82, 0.95), bevel=0.04, taper_y=0.86)
    for s in (-1, 1):
        for z in (0.52, 0.86):
            box("course", p["stone_dk"], (0, s * 0.385, z), (length * 0.99, 0.05, 0.035), bevel=0.0)
        for x in (-0.9, 0.9):
            box("slit", p["dark"], (x, s * 0.375, 0.62), (0.07, 0.05, 0.3), bevel=0.0)
        for x, w in ((-1.2, 0.5), (0.25, 0.7), (1.3, 0.4)):
            box("moss", p["moss"], (x, s * 0.43, 0.0), (w, 0.1, 0.3), bevel=0.02, taper=0.6)
    box("deck", p["stone_lt"], (0, 0, 1.15), (length, 0.88, 0.07), bevel=0.0)
    for s in (-1, 1):
        for i in range(8):
            box("merlon", p["stone_lt"], (-1.4 + i * 0.4, s * 0.32, 1.2), (0.26, 0.2, 0.28), bevel=0.02)
    normalize(length, 1.1)


def cls_pillar():
    """Torre redonda de portão (1,1 x 1,1 x ~2,4): talude, balcão, telhado de ardósia, lanterna e estandarte."""
    p = field_palette()
    cyl("foot", p["stone_dk"], (0, 0, 0), 0.58, 0.28, sides=10, top_radius=0.52, bevel=0.0)
    cyl("shaft", p["stone"], (0, 0, 0.24), 0.52, 1.45, sides=10, top_radius=0.43, bevel=0.0)
    ring("band", p["stone_lt"], (0, 0, 0.9), 0.46, 0.08, thick=0.04, sides=10)
    for a in (0.5, 2.6, 4.7):
        box("slit", p["dark"], (math.cos(a) * 0.46, math.sin(a) * 0.46, 1.1), (0.05, 0.07, 0.32), bevel=0.0, rot_z=a)
    cyl("corbel", p["stone_dk"], (0, 0, 1.6), 0.5, 0.14, sides=10, top_radius=0.56, bevel=0.0)
    cyl("deck", p["stone_lt"], (0, 0, 1.73), 0.56, 0.05, sides=10, bevel=0.0)
    cyl("roof", p["slate"], (0, 0, 1.76), 0.52, 0.66, sides=10, top_radius=0.0, bevel=0.0)
    cyl("roof_eave", p["slate_lt"], (0, 0, 1.76), 0.6, 0.06, sides=10, bevel=0.0)
    cyl("finial", p["gold"], (0, 0, 2.38), 0.05, 0.2, sides=6, top_radius=0.0, bevel=0.0)
    beam("bracket", p["iron"], (0.4, 0, 1.45), (0.74, 0, 1.45), thick=0.04)
    box("lantern", p["lamp"], (0.74, 0, 1.2), (0.14, 0.14, 0.2), bevel=0.0)
    box("lantern_cap", p["iron"], (0.74, 0, 1.4), (0.18, 0.18, 0.05), bevel=0.0)
    box("pole", p["wood_dk"], (-0.45, 0.0, 1.0), (0.04, 0.04, 0.7), bevel=0.0)
    box("banner", p["banner"], (-0.45, 0.14, 1.0), (0.03, 0.26, 0.46), bevel=0.0)
    box("banner_tail", p["banner"], (-0.45, 0.1, 0.86), (0.03, 0.12, 0.16), bevel=0.0)
    normalize(1.1, 1.1, 1.83)


def cls_arch():
    """Meio vão do portão (espelhado pelo Terrain): lintel de pedra com ameias, aduelas e fecho dourado."""
    p = field_palette()
    box("lintel", p["stone"], (-0.25, 0, 0.92), (0.5, 0.8, 0.3), bevel=0.0)
    box("soffit", p["stone_dk"], (-0.25, 0, 0.88), (0.5, 0.62, 0.05), bevel=0.0)
    box("deck", p["stone_lt"], (-0.25, 0, 1.2), (0.5, 0.86, 0.04), bevel=0.0)
    for s in (-1, 1):
        for i in range(4):
            box("merlon", p["stone_lt"], (-0.44 + i * 0.13, s * 0.31, 1.22), (0.07, 0.14, 0.09), bevel=0.0)
        box("string", p["stone_dk"], (-0.25, s * 0.4, 1.05), (0.5, 0.04, 0.05), bevel=0.0)
    box("keystone", p["gold"], (-0.02, 0, 0.84), (0.05, 0.3, 0.1), bevel=0.0)
    box("lantern", p["lamp"], (-0.08, 0, 0.8), (0.04, 0.1, 0.07), bevel=0.0)


def basin(p, r, z, h, water_r):
    cyl("basin", p["stone"], (0, 0, z), r, h, sides=14, top_radius=r * 0.93, bevel=0.0)
    cyl("basin_lip", p["stone_lt"], (0, 0, z + h * 0.8), r, h * 0.22, sides=14, bevel=0.0)
    cyl("basin_water", p["water"], (0, 0, z + h * 0.8), water_r, h * 0.28, sides=14, bevel=0.0)


def cls_fountain():
    """Fonte de três bacias com estátua de cavaleiro: água azul plana, esguichos pálidos fixos e musgo."""
    p = field_palette()
    cyl("plinth", p["stone_dk"], (0, 0, 0), 1.5, 0.12, sides=14, bevel=0.0)
    basin(p, 1.4, 0.1, 0.42, 1.18)
    cyl("stem", p["stone"], (0, 0, 0.45), 0.3, 0.55, sides=10, top_radius=0.22, bevel=0.0)
    basin(p, 0.82, 0.95, 0.2, 0.66)
    cyl("stem2", p["stone"], (0, 0, 1.12), 0.2, 0.5, sides=8, top_radius=0.15, bevel=0.0)
    basin(p, 0.44, 1.58, 0.14, 0.34)
    cyl("column", p["stone_lt"], (0, 0, 1.7), 0.14, 0.42, sides=8, top_radius=0.1, bevel=0.0)
    cyl("statue_body", p["stone_lt"], (0, 0, 2.1), 0.1, 0.3, sides=8, top_radius=0.07, bevel=0.0)
    kit.dome("statue_head", p["stone_lt"], (0, 0, 2.38), 0.09, squash=1.0, sides=8)
    beam("statue_spear", p["gold"], (0.1, 0, 2.05), (0.1, 0, 2.75), thick=0.03)
    for i in range(8):
        a = i * math.tau / 8
        c, s = math.cos(a), math.sin(a)
        beam("spray", p["spray"], (0.0, 0.0, 1.98), (c * 0.36, s * 0.36, 1.74), thick=0.035)
        beam("spray", p["spray"], (c * 0.36, s * 0.36, 1.74), (c * 0.6, s * 0.6, 1.62), thick=0.03)
        if i % 2 == 0:
            beam("spray", p["spray"], (c * 0.5, s * 0.5, 1.2), (c * 0.75, s * 0.75, 1.1), thick=0.03)
    for a, r in ((0.4, 1.38), (2.2, 1.35), (4.0, 1.4)):
        box("moss", p["moss"], (math.cos(a) * r, math.sin(a) * r, 0.0), (0.45, 0.14, 0.34), bevel=0.02, taper=0.6, rot_z=a)


# ---------------------------------------------------------------------------------------------------------
# Adereços do campo (no lugar do arbusto e da pedra)
# ---------------------------------------------------------------------------------------------------------


def bloom(p, tone, x, y, z, r=0.11):
    kit.dome("bloom", p[tone], (x, y, z), r, squash=0.8, sides=6)


def flower_bed(variant):
    """Canteiro de pedra com folhagem e flores: 0 rosa e branco, 1 amarelo e roxo."""
    p = field_palette()
    tones = (("pink", "white", "red"), ("yellow", "purple", "white"))[variant]
    box("curb", p["stone"], (0, 0, 0), (2.0, 1.1, 0.2), bevel=0.04)
    box("soil", p["earth"], (0, 0, 0.14), (1.8, 0.9, 0.06), bevel=0.0)
    for i in range(7):
        kit.dome("leaf", p["leaf"] if i % 2 else p["leaf_lt"], (-0.75 + i * 0.25, 0.22 * math.sin(i * 1.7), 0.16), 0.2, squash=0.9, sides=6)
    for i in range(16):
        x = -0.8 + (i % 8) * 0.23
        y = (-0.25 if i < 8 else 0.25) + 0.08 * math.sin(i * 2.3)
        bloom(p, tones[i % 3], x, y, 0.34 + 0.05 * (i % 3))
    if variant == 1:
        for i, x in enumerate((-0.55, 0.0, 0.55)):
            beam("tulip_stem", p["leaf"], (x, 0.0, 0.16), (x, 0.0, 0.62), thick=0.03)
            bloom(p, tones[i], x, 0.0, 0.64, 0.1)


def cls_berry():
    """Moita de frutos vermelhos: cúpulas de folha e bagas."""
    p = field_palette()
    for i, (x, y, r) in enumerate(((0, 0, 0.55), (0.55, 0.25, 0.4), (-0.5, -0.2, 0.42), (0.1, -0.5, 0.34))):
        kit.dome("bush", p["leaf"] if i % 2 == 0 else p["leaf_lt"], (x, y, 0.05), r, squash=0.85, sides=8)
    for x, y, z in ((0.3, -0.35, 0.45), (-0.3, 0.2, 0.5), (0.5, 0.3, 0.4), (-0.6, -0.2, 0.35), (0.0, 0.1, 0.56), (0.7, 0.1, 0.3)):
        bloom(p, "red", x, y, z, 0.07)


def cls_hay():
    """Duas medas redondas deitadas, dois fardos quadrados e um monte cônico de feno."""
    p = field_palette()
    for x, y in ((-0.6, -0.25), (0.1, -0.55)):
        cyl("bale", p["hay"], (x, y, 0.4), 0.4, 0.7, sides=10, bevel=0.0, rot=("Y", math.pi / 2))
    box("square_bale", p["hay_dk"], (-0.2, 0.3, 0.0), (0.7, 0.5, 0.42), bevel=0.05, rot_z=0.3)
    box("square_bale", p["hay"], (-0.15, 0.3, 0.42), (0.6, 0.45, 0.38), bevel=0.05, rot_z=0.1)
    cyl("stack", p["hay"], (0.75, 0.35, 0.0), 0.55, 0.9, sides=9, top_radius=0.12, bevel=0.0)
    cyl("stack_top", p["hay_dk"], (0.75, 0.35, 0.82), 0.14, 0.2, sides=6, top_radius=0.0, bevel=0.0)
    beam("pitchfork", p["wood"], (0.3, 0.9, 0.0), (0.5, 0.75, 0.95), thick=0.04)


def cls_barrels():
    """Três barris de carvalho com aros, um caixote e um barril tombado."""
    p = field_palette()
    for x, y in ((-0.5, 0.0), (0.1, 0.25), (0.1, -0.35)):
        cyl("barrel", p["wood"], (x, y, 0.0), 0.3, 0.7, sides=10, top_radius=0.26, bevel=0.0)
        for z in (0.16, 0.5):
            ring("hoop", p["iron"], (x, y, z), 0.28, 0.05, thick=0.02, sides=10)
        cyl("lid", p["wood_dk"], (x, y, 0.69), 0.24, 0.03, sides=10, bevel=0.0)
    box("crate", p["wood_dk"], (0.75, 0.0, 0.0), (0.5, 0.5, 0.42), bevel=0.02, rot_z=0.4)
    box("crate_band", p["wood"], (0.75, 0.0, 0.3), (0.52, 0.52, 0.06), bevel=0.0, rot_z=0.4)
    cyl("barrel_fallen", p["wood"], (-0.2, -0.75, 0.28), 0.26, 0.62, sides=10, bevel=0.0, rot=("Y", math.pi / 2))


def cls_cart():
    """Carroça de feno: caixa, dois rodões, varais e carga de feno."""
    p = field_palette()
    box("bed", p["wood"], (0, 0, 0.3), (1.5, 0.9, 0.12), bevel=0.02)
    for s in (-1, 1):
        box("side", p["wood_dk"], (0, s * 0.43, 0.38), (1.5, 0.05, 0.32), bevel=0.0)
        cyl("wheel", p["wood_dk"], (0.1, s * 0.5, 0.34), 0.34, 0.08, sides=10, bevel=0.0, rot=("X", math.pi / 2))
        cyl("hub", p["iron"], (0.1, s * 0.5, 0.34), 0.07, 0.12, sides=6, bevel=0.0, rot=("X", math.pi / 2))
        beam("shaft", p["wood"], (0.7, s * 0.3, 0.32), (1.55, s * 0.18, 0.16), thick=0.06)
    box("front", p["wood_dk"], (0.72, 0, 0.38), (0.05, 0.9, 0.32), bevel=0.0)
    kit.dome("hay_load", p["hay"], (-0.05, 0, 0.42), 0.62, squash=0.55, sides=9)
    box("bag", p["canvas"], (-0.5, 0.15, 0.7), (0.3, 0.2, 0.18), bevel=0.05)


def cls_stall():
    """Barraca de feira de lona listrada, bancada com frutas e um caixote."""
    p = field_palette()
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        beam("post", p["wood_dk"], (sx * 0.7, sy * 0.45, 0.0), (sx * 0.7, sy * 0.45, 1.15), thick=0.06)
    box("counter", p["wood"], (0, -0.38, 0.0), (1.5, 0.4, 0.55), bevel=0.02)
    box("counter_top", p["wood_dk"], (0, -0.38, 0.55), (1.6, 0.46, 0.05), bevel=0.0)
    for i in range(6):
        tone = p["red"] if i % 2 == 0 else p["white"]
        box("awning", tone, (-0.625 + i * 0.25, 0, 1.12), (0.25, 1.15, 0.05), bevel=0.0)
        box("valance", tone, (-0.625 + i * 0.25, -0.62, 1.02), (0.25, 0.04, 0.12), bevel=0.0)
    for i, tone in enumerate(("red", "yellow", "leaf", "red", "yellow")):
        bloom(p, tone, -0.55 + i * 0.28, -0.38, 0.64, 0.09)
    box("crate", p["wood"], (0.55, 0.3, 0.0), (0.4, 0.4, 0.3), bevel=0.02, rot_z=0.2)
    box("sack", p["canvas"], (-0.5, 0.3, 0.0), (0.3, 0.26, 0.3), bevel=0.06)


def cls_well():
    """Poço de pedra com telhadinho de ardósia, roldana e balde."""
    p = field_palette()
    cyl("well", p["stone"], (0, 0, 0), 0.55, 0.6, sides=10, bevel=0.0)
    cyl("well_lip", p["stone_lt"], (0, 0, 0.58), 0.55, 0.08, sides=10, bevel=0.0)
    cyl("well_water", p["water"], (0, 0, 0.62), 0.38, 0.03, sides=10, bevel=0.0)
    for s in (-1, 1):
        beam("post", p["wood"], (0, s * 0.5, 0.58), (0, s * 0.5, 1.45), thick=0.09)
    beam("roller", p["wood_dk"], (0, -0.55, 1.2), (0, 0.55, 1.2), thick=0.08)
    prism("roof", p["slate"], (0, 0, 1.42), (1.0, 1.4, 0.45), ridge=0.5)
    box("bucket", p["wood_dk"], (0.0, 0.2, 0.75), (0.15, 0.15, 0.16), bevel=0.02)
    for i in range(3):
        box("stone", p["stone_dk"], (math.cos(i * 2.1) * 0.8, math.sin(i * 2.1) * 0.8, 0.0), (0.3, 0.26, 0.14), bevel=0.04)


def cls_lamp():
    """Poste de lampião de ferro com lanterna acesa e base de pedra."""
    p = field_palette()
    cyl("base", p["stone"], (0, 0, 0), 0.3, 0.25, sides=8, top_radius=0.22, bevel=0.0)
    cyl("pole", p["iron"], (0, 0, 0.2), 0.07, 1.6, sides=6, top_radius=0.05, bevel=0.0)
    beam("arm", p["iron"], (0, 0, 1.6), (0.35, 0, 1.7), thick=0.05)
    box("lantern", p["lamp"], (0.35, 0, 1.45), (0.2, 0.2, 0.28), bevel=0.0)
    box("lantern_cap", p["iron"], (0.35, 0, 1.73), (0.26, 0.26, 0.06), bevel=0.0)
    cyl("lantern_top", p["iron"], (0.35, 0, 1.79), 0.12, 0.12, sides=4, top_radius=0.0, bevel=0.0)
    for a in (0.0, 2.1, 4.2):
        bloom(p, "yellow", math.cos(a) * 0.42, math.sin(a) * 0.42, 0.04, 0.1)


def boulder(variant):
    """Pedra grande com musgo e samambaias: 0 laje arredondada, 1 duas pedras empilhadas."""
    p = field_palette()
    if variant == 0:
        box("rock", p["stone_dk"], (0, 0, 0), (3.0, 2.3, 1.2), bevel=0.35, taper=0.6, taper_y=0.6, rot_z=0.3)
        box("rock_top", p["stone"], (-0.2, 0.1, 0.9), (1.8, 1.4, 0.7), bevel=0.25, taper=0.55, taper_y=0.55, rot_z=-0.2)
        box("rock_side", p["stone_dk"], (1.1, -0.9, 0.0), (1.2, 1.0, 0.6), bevel=0.15, taper=0.6, taper_y=0.6, rot_z=0.8)
    else:
        box("rock", p["stone_dk"], (0, 0, 0), (2.8, 2.4, 0.9), bevel=0.3, taper=0.65, taper_y=0.65, rot_z=-0.3)
        box("rock_up", p["stone"], (0.3, 0.2, 0.7), (1.5, 1.2, 1.1), bevel=0.2, taper=0.5, taper_y=0.5, rot_z=0.5)
        box("rock_small", p["stone"], (-1.0, -0.8, 0.0), (0.9, 0.8, 0.5), bevel=0.1, taper=0.6, taper_y=0.6)
    box("moss_cap", p["moss"], (0.0, 0.1, 1.0 if variant == 0 else 1.2), (1.2, 1.0, 0.18), bevel=0.06, taper=0.6, taper_y=0.6)
    for a in (0.6, 2.4, 4.4):
        kit.dome("fern", p["leaf_lt"], (math.cos(a) * 1.35, math.sin(a) * 1.1, 0.02), 0.28, squash=0.7, sides=6)
    bloom(p, "white", 1.3, 0.9, 0.3, 0.08)


# --- os ~3% de guerra: um sinal do front que chegou à região ---------------------------------------------


def cls_wire():
    """Rolo de arame farpado sobre três cavaletes cruzados."""
    p = field_palette()
    for x in (-0.85, 0.0, 0.85):
        beam("stake", p["wood"], (x - 0.18, -0.2, 0.0), (x + 0.18, 0.2, 0.95), thick=0.08)
        beam("stake", p["wood"], (x + 0.18, -0.2, 0.0), (x - 0.18, 0.2, 0.95), thick=0.08)
    wire_coil(p["iron"], (-1.0, 0.0, 0.25), (1.0, 0.0, 0.25), radius=0.26, turns=6)


def cls_sandbags():
    """Ninho de sacos de areia em arco com um caixote."""
    p = field_palette()
    for layer, (count, z) in enumerate(((6, 0.0), (5, 0.17), (4, 0.34))):
        for i in range(count):
            a = math.radians(-70 + 140 * (i + 0.5 + 0.5 * (layer % 2)) / (count + (layer % 2)))
            pos = (math.sin(a) * 1.0, -math.cos(a) * 1.0 + 0.6, z)
            sandbag(p["canvas"] if (i + layer) % 2 else p["hay_dk"], pos, rot_z=a)
    box("crate", p["wood"], (0.1, 0.35, 0.0), (0.5, 0.4, 0.36), bevel=0.02, rot_z=0.3)


def cls_crates():
    """Pilha de caixotes de suprimento sob lona."""
    p = field_palette()
    for x, y, z, rz in ((-0.4, 0.0, 0.0, 0.1), (0.25, 0.1, 0.0, -0.15), (-0.1, 0.05, 0.42, 0.3), (0.7, -0.4, 0.0, 0.5)):
        box("crate", p["wood"], (x, y, z), (0.55, 0.5, 0.42), bevel=0.02, rot_z=rz)
        box("crate_band", p["wood_dk"], (x, y, z + 0.3), (0.57, 0.52, 0.06), bevel=0.0, rot_z=rz)
    box("tarp", p["olive"], (0.2, 0.55, 0.0), (0.8, 0.5, 0.3), bevel=0.1, taper=0.7, rot_z=0.2)


def cls_fieldgun():
    """Canhão de campanha com escudo, dois rodões e cauda."""
    p = field_palette()
    for s in (-1, 1):
        cyl("wheel", p["wood_dk"], (0, s * 0.62, 0.55), 0.55, 0.1, sides=12, bevel=0.0, rot=("X", math.pi / 2))
        cyl("rim", p["iron"], (0, s * 0.62, 0.55), 0.57, 0.06, sides=12, bevel=0.0, rot=("X", math.pi / 2))
        cyl("hub", p["iron"], (0, s * 0.62, 0.55), 0.1, 0.16, sides=6, bevel=0.0, rot=("X", math.pi / 2))
        beam("trail", p["wood"], (-0.2, s * 0.12, 0.6), (-1.5, s * 0.6, 0.08), thick=0.08)
    beam("axle", p["iron"], (0, -0.65, 0.55), (0, 0.65, 0.55), thick=0.08)
    beam("barrel", p["olive"], (-0.3, 0, 0.72), (1.25, 0, 0.82), thick=0.2)
    beam("muzzle", p["iron"], (1.05, 0, 0.81), (1.3, 0, 0.83), thick=0.26)
    box("shield", p["olive"], (0.35, 0, 0.45), (0.06, 1.0, 0.65), bevel=0.02)


# ---------------------------------------------------------------------------------------------------------
# Decoração fora da muralha: o campo (um modelo por kind)
# ---------------------------------------------------------------------------------------------------------


def cls_watchtower():
    """Torre de vigia de pedra sobre um morro: tapume de madeira, telhado de ardósia e estandarte (kind 0)."""
    p = field_palette()
    cyl("mound", p["moss"], (0, 0, 0), 1.8, 0.35, sides=12, top_radius=1.4, bevel=0.0)
    cyl("foot", p["stone_dk"], (0, 0, 0.2), 1.3, 0.5, sides=10, top_radius=1.15, bevel=0.0)
    cyl("shaft", p["stone"], (0, 0, 0.6), 1.12, 3.8, sides=10, top_radius=0.92, bevel=0.0)
    for z in (2.0, 3.4):
        ring("band", p["stone_dk"], (0, 0, z), 1.0, 0.12, thick=0.05, sides=10)
    for a, z in ((0.3, 1.4), (2.4, 2.6), (4.4, 1.8), (5.5, 3.2)):
        box("slit", p["dark"], (math.cos(a) * 1.0, math.sin(a) * 1.0, z), (0.08, 0.12, 0.5), bevel=0.0, rot_z=a)
    box("door", p["wood_dk"], (1.1, 0, 0.3), (0.12, 0.5, 0.8), bevel=0.0)
    cyl("corbel", p["stone_dk"], (0, 0, 4.4), 1.0, 0.2, sides=10, top_radius=1.3, bevel=0.0)
    cyl("hoarding", p["wood"], (0, 0, 4.6), 1.28, 0.9, sides=10, top_radius=1.3, bevel=0.0)
    for i in range(10):
        a = i * math.tau / 10
        box("window", p["dark"], (math.cos(a) * 1.3, math.sin(a) * 1.3, 4.9), (0.06, 0.3, 0.35), bevel=0.0, rot_z=a)
    cyl("roof_eave", p["stone_lt"], (0, 0, 5.5), 1.5, 0.12, sides=10, bevel=0.0)
    cyl("roof", p["slate"], (0, 0, 5.6), 1.4, 2.0, sides=10, top_radius=0.0, bevel=0.0)
    cyl("finial", p["gold"], (0, 0, 7.5), 0.07, 0.6, sides=6, top_radius=0.0, bevel=0.0)
    box("pole", p["wood_dk"], (0, 0, 7.4), (0.05, 0.05, 0.9), bevel=0.0)
    box("flag", p["banner"], (0.2, 0, 8.05), (0.4, 0.04, 0.26), bevel=0.0)
    normalize(1 / 0.72, 1 / 0.72, 1 / 0.72)  # kind 4 é a torre fina: base ~2,6 e ~6 de altura


def cls_farm():
    """Casa de fazenda de enxaimel com telhado de palha, chaminé, monte de feno e cerquinha (kind 1)."""
    p = field_palette()
    box("floor", p["earth"], (0, 0, 0), (3.5, 3.2, 0.1), bevel=0.04, taper=0.94, taper_y=0.94)
    box("walls", p["plaster"], (-0.2, 0.1, 0.1), (2.3, 1.7, 1.0), bevel=0.03)
    for x in (-1.1, -0.2, 0.7):
        box("timber", p["wood_dk"], (x, -0.76, 0.1), (0.1, 0.05, 1.0), bevel=0.0)
        box("timber", p["wood_dk"], (x, 0.96, 0.1), (0.1, 0.05, 1.0), bevel=0.0)
    box("timber_h", p["wood_dk"], (-0.2, -0.76, 0.55), (2.3, 0.05, 0.08), bevel=0.0)
    box("door", p["wood"], (0.55, -0.78, 0.1), (0.4, 0.06, 0.7), bevel=0.0)
    for x in (-0.6, 0.0):
        kit.window(p["wood_dk"], p["lamp"], (x - 0.2, -0.82, 0.68), "y-", w=0.2, h=0.24)
    prism("roof", p["thatch"], (-0.2, 0.1, 1.1), (2.1, 2.7, 1.2), ridge=0.5, bevel=0.05, rot_z=math.radians(90))
    box("roof_ridge", p["thatch_dk"], (-0.2, 0.1, 2.25), (2.5, 0.2, 0.1), bevel=0.0)
    box("chimney", p["stone"], (-1.0, 0.5, 1.2), (0.3, 0.3, 1.3), bevel=0.02)
    cyl("haystack", p["hay"], (1.2, 0.8, 0.1), 0.62, 1.0, sides=9, top_radius=0.12, bevel=0.0)
    cyl("hay_tip", p["hay_dk"], (1.2, 0.8, 1.0), 0.14, 0.24, sides=6, top_radius=0.0, bevel=0.0)
    for i in range(6):
        box("fence", p["wood"], (-1.5 + i * 0.5, -1.4, 0.1), (0.07, 0.07, 0.5), bevel=0.0)
    box("rail", p["wood_dk"], (-0.25, -1.4, 0.35), (2.6, 0.04, 0.06), bevel=0.0)
    for x, tone in ((-1.2, "pink"), (-0.9, "yellow"), (1.5, "white")):
        bloom(p, tone, x, -1.1, 0.25, 0.12)


def cls_beacon():
    """Santuário de beira de estrada com lampião no alto: pilar de pedra, nicho com telhadinho e lanterna acesa (kind 2)."""
    p = field_palette()
    cyl("foot", p["stone_dk"], (0, 0, 0), 0.7, 0.3, sides=8, top_radius=0.55, bevel=0.0)
    cyl("pier", p["stone"], (0, 0, 0.25), 0.42, 1.9, sides=8, top_radius=0.34, bevel=0.0)
    box("niche", p["stone_lt"], (0, 0, 2.1), (0.8, 0.8, 0.8), bevel=0.04)
    box("niche_dark", p["dark"], (0.38, 0, 2.3), (0.08, 0.4, 0.5), bevel=0.0)
    box("niche_figure", p["gold"], (0.34, 0, 2.3), (0.1, 0.14, 0.3), bevel=0.0)
    prism("niche_roof", p["slate"], (0, 0, 2.9), (1.0, 1.0, 0.5), ridge=0.5, rot_z=math.radians(90))
    cyl("pole", p["iron"], (0, 0, 3.3), 0.08, 1.7, sides=6, top_radius=0.06, bevel=0.0)
    beam("arm", p["iron"], (0, 0, 4.8), (0.55, 0, 4.9), thick=0.07)
    box("lantern", p["lamp"], (0.55, 0, 4.4), (0.34, 0.34, 0.5), bevel=0.0)
    box("lantern_cap", p["iron"], (0.55, 0, 4.9), (0.44, 0.44, 0.08), bevel=0.0)
    cyl("lantern_roof", p["iron"], (0.55, 0, 4.98), 0.26, 0.28, sides=4, top_radius=0.0, bevel=0.0)
    for a in (0.5, 2.6, 4.7):
        bloom(p, "yellow" if a < 3 else "pink", math.cos(a) * 0.75, math.sin(a) * 0.75, 0.04, 0.12)


def cls_fence():
    """Trecho de 8 unidades de muro de pedra seca com cerca de ripas e flores (kind 3, eixo x)."""
    p = field_palette()
    box("wall", p["stone"], (0, 0, 0), (8.0, 0.55, 0.55), bevel=0.05, taper=0.95, taper_y=0.75)
    for i in range(16):
        box("cap", p["stone_lt"] if i % 3 else p["stone"], (-3.75 + i * 0.5, 0.0, 0.55), (0.42, 0.36, 0.12 + 0.04 * (i % 3)), bevel=0.03)
    for i in range(9):
        box("post", p["wood"], (-4.0 + i, 0.0, 0.6), (0.1, 0.1, 0.55), bevel=0.01)
    for z in (0.85, 1.05):
        box("rail", p["wood_dk"], (0, 0.0, z), (8.0, 0.05, 0.07), bevel=0.0)
    for i, x in enumerate((-3.1, -1.4, 0.3, 1.9, 3.3)):
        kit.dome("tuft", p["leaf"], (x, 0.35, 0.0), 0.28, squash=0.7, sides=6)
        bloom(p, ("pink", "yellow", "white", "purple", "pink")[i], x, 0.38, 0.2, 0.09)


def cls_windmill():
    """Moinho de vento: torre de reboco em talude, cúpula de madeira e quatro velas de ripas (kind 4)."""
    p = field_palette()
    cyl("foot", p["stone_dk"], (0, 0, 0), 1.45, 0.4, sides=8, top_radius=1.3, bevel=0.0)
    cyl("tower", p["plaster"], (0, 0, 0.35), 1.3, 3.8, sides=8, top_radius=0.85, bevel=0.0)
    ring("tower_band", p["wood_dk"], (0, 0, 2.2), 1.05, 0.12, thick=0.04, sides=8)
    box("door", p["wood_dk"], (0.0, -1.2, 0.3), (0.5, 0.1, 0.85), bevel=0.0)
    box("window", p["dark"], (1.0, 0.0, 2.6), (0.08, 0.3, 0.45), bevel=0.0)
    box("gallery", p["wood"], (0, 0, 4.0), (2.0, 2.0, 0.12), bevel=0.0, rot_z=math.pi / 8)
    cyl("cap", p["wood_dk"], (0, 0, 4.1), 0.95, 0.7, sides=8, top_radius=0.8, bevel=0.0)
    cyl("cap_roof", p["slate"], (0, 0, 4.8), 1.0, 0.8, sides=8, top_radius=0.0, bevel=0.0)
    cyl("hub", p["iron"], (0.9, 0, 4.1), 0.18, 0.3, sides=8, bevel=0.0, rot=("Y", math.pi / 2))
    hub = Vector((1.1, 0.0, 4.55))
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        d = Vector((0.0, math.cos(a), math.sin(a)))
        side = Vector((0.0, -d.z, d.y))
        beam("sail_arm", p["wood_dk"], hub, hub + d * 2.4, thick=0.1)
        for t in (0.35, 0.6, 0.85):
            beam("sail_rung", p["wood"], hub + d * 2.4 * t, hub + d * 2.4 * t + side * 0.4, thick=0.05)
        beam("sail_edge", p["wood"], hub + d * 0.7 + side * 0.4, hub + d * 2.4 + side * 0.4, thick=0.05)
        beam("sail_cloth", p["canvas"], hub + d * 0.8 + side * 0.2, hub + d * 2.3 + side * 0.2, thick=0.2)
    normalize(1 / 1.2, 1 / 1.2, 1 / 1.2)  # kind 0 é a torre alta: base ~3,5 e ~7,9 de altura


CASTLES = {"cls_sentinel": sentinel, "cls_scourge": scourge}
MODELS = {
    "cls_wall": cls_wall,
    "cls_pillar": cls_pillar,
    "cls_arch": cls_arch,
    "cls_fountain": cls_fountain,
    "cls_flowerbed_a": lambda: flower_bed(0),
    "cls_flowerbed_b": lambda: flower_bed(1),
    "cls_berry": cls_berry,
    "cls_hay": cls_hay,
    "cls_barrels": cls_barrels,
    "cls_cart": cls_cart,
    "cls_stall": cls_stall,
    "cls_well": cls_well,
    "cls_lamp": cls_lamp,
    "cls_boulder_a": lambda: boulder(0),
    "cls_boulder_b": lambda: boulder(1),
    "cls_wire": cls_wire,
    "cls_sandbags": cls_sandbags,
    "cls_crates": cls_crates,
    "cls_fieldgun": cls_fieldgun,
    "cls_watchtower": cls_watchtower,
    "cls_farm": cls_farm,
    "cls_beacon": cls_beacon,
    "cls_fence": cls_fence,
    "cls_windmill": cls_windmill,
}


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["all"]
    out_dir = game_paths.out_arg(args, "--out", "scenery", "classic")
    castle_dir = game_paths.out_arg(args, "--castles-out", "castles")
    render_dir = args[args.index("--render") + 1] if "--render" in args else ""
    pick = args[0]
    for name, make in CASTLES.items():
        if pick in ("all", "castles", name):
            kit.build(name, castle_dir, render_dir, make=make)
    for name, make in MODELS.items():
        if pick in ("all", "scenery", name):
            kit.build(name, out_dir, render_dir, make=make, views=(("front", -35.0),))


if __name__ == "__main__":
    main()
