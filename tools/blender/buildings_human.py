"""Prédios da raça Human modelados por script (redesenho de reports/design/race-human.md): um GLB por prédio.

Uso:
    blender -b --factory-startup --python tools/blender/buildings_human.py -- <id|all> [--out DIR] [--render DIR]

Estado-Maior Industrial: galpão, concreto, lona oliva, madeira umbra, aço de fuzil; informação em ecru (giz,
cruz de estêncil) e um só acento, o latão da lanterna. Todo prédio tem um ponto de óleo à vista (tambor
cintado, bomba manual ou poço). Pegada ~4 x 4 centrada na origem, a porta virada para +x; o jogo normaliza o
tamanho, põe o prédio no plinto do time e desenha a bandeira.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_paths  # noqa: E402
import map_castles as kit
from map_castles import beam, box, cyl, dome, mat, merlons, prism, ring
from map_scenery import sandbag, wire_coil

GROUND = 0x5E5444  # chão das prévias


def pal():
    return {
        "olive": mat("staff_olive", 0x829779),
        "olive_dk": mat("staff_olive_dark", 0x5F7262),
        "canvas": mat("canvas", 0x9DAE80),
        "umber": mat("trench_umber", 0x8E7152),
        "umber_dk": mat("trench_umber_dark", 0x5E4A38),
        "plank": mat("plank", 0xA68A62),
        "steel": mat("rifle_steel", 0x7C8590),
        "steel_dk": mat("rifle_steel_dark", 0x59626E),
        "soot": mat("soot", 0x2E3136),
        "concrete": mat("concrete", 0xB4AD99),
        "concrete_lt": mat("concrete_light", 0xD6CEB8),
        "concrete_dk": mat("concrete_dark", 0x878172),
        "ecru": mat("doctrine_ecru", 0xE7E2D4),
        "brass": mat("lantern_brass", 0xDDA338),
        "copper": mat("copper", 0xCC7C44),
        "bag": mat("sandbag", 0xA89A74),
        "bag_dk": mat("sandbag_dark", 0x86795A),
        "mud": mat("mud", 0x66543F),
        "oil": mat("oil", 0x15131A),
        "slate": mat("slate", 0x3A4046),
        "flame": mat("flame", 0xFFC658, emit=3.0),
    }


# ---------------------------------------------------------------------------------------------------------
# Peças da raça
# ---------------------------------------------------------------------------------------------------------


def pad(p, size=(3.5, 3.5), tone="mud"):
    """Chão do posto, do tamanho do conteúdo: o jogo normaliza pelo maior lado, então laje sobrando encolhe o
    prédio na tela."""
    box("pad", p[tone], (0, 0, 0), (size[0], size[1], 0.1), bevel=0.03)


def drum(p, pos, tone="steel_dk", lying=False):
    """O ponto de óleo: tambor cintado de 200 litros."""
    x, y, z = pos
    if lying:
        cyl("drum", p[tone], (x - 0.21, y, z + 0.16), 0.16, 0.42, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
        return
    cyl("drum", p[tone], (x, y, z), 0.16, 0.42, sides=10, bevel=0.0)
    for dz in (0.1, 0.3):
        ring("drum_band", p["soot"], (x, y, z + dz), 0.16, 0.04, thick=0.015, sides=10)
    cyl("drum_cap", p["brass"], (x + 0.07, y, z + 0.42), 0.035, 0.03, sides=6, bevel=0.0)


def lantern(p, pos, post=0.0):
    """Chama em vidro: o único acento da raça. post > 0 põe a lanterna num poste dessa altura."""
    x, y, z = pos
    if post > 0.0:
        box("lantern_post", p["umber_dk"], (x, y, z), (0.07, 0.07, post), bevel=0.0)
        z += post
    box("lantern_base", p["soot"], (x, y, z), (0.16, 0.16, 0.04), bevel=0.0)
    box("lantern_glass", p["flame"], (x, y, z + 0.04), (0.11, 0.11, 0.14), bevel=0.0)
    box("lantern_cap", p["brass"], (x, y, z + 0.18), (0.18, 0.18, 0.05), bevel=0.0, taper=0.4, taper_y=0.4)


def slate(p, pos, rot_z=0.0, lines=3):
    """Lousa de giz do turno: quadro escuro em cavalete com linhas em ecru."""
    x, y, z = pos
    c, s = math.cos(rot_z), math.sin(rot_z)
    box("slate_board", p["slate"], (x, y, z + 0.18), (0.06, 0.5, 0.42), bevel=0.0, rot_z=rot_z)
    box("slate_frame", p["umber_dk"], (x, y, z), (0.08, 0.56, 0.18), bevel=0.0, rot_z=rot_z)
    for i in range(lines):
        box("slate_chalk", p["ecru"], (x + c * 0.035, y + s * 0.035, z + 0.26 + i * 0.1), (0.02, 0.34 - 0.06 * i, 0.03), bevel=0.0, rot_z=rot_z)


def crate(p, pos, size=(0.5, 0.36, 0.3), rot_z=0.0, rifles=False):
    x, y, z = pos
    box("crate", p["plank"], (x, y, z), size, bevel=0.02, rot_z=rot_z)
    box("crate_band", p["umber_dk"], (x, y, z + size[2] * 0.45), (size[0] * 1.03, size[1] * 1.03, 0.05), bevel=0.0, rot_z=rot_z)
    if rifles:
        for i in range(3):
            beam("rifle", p["steel_dk"], (x - 0.12 + i * 0.12, y, z + size[2]), (x - 0.06 + i * 0.12, y + 0.05, z + size[2] + 0.5), thick=0.035)


def bag_wall(p, a, b, z=0.1, rows=2, dark=False):
    """Parapeito de sacos de areia de a até b (x, y), fiadas alternadas."""
    ax, ay = a
    bx, by = b
    length = math.hypot(bx - ax, by - ay)
    count = max(2, round(length / 0.5))
    rot = math.atan2(by - ay, bx - ax)
    for r in range(rows):
        n = count - (r % 2)
        for i in range(n):
            t = (i + 0.5 + 0.5 * (r % 2)) / count
            tone = p["soot"] if dark and (i + r) % 3 == 0 else (p["bag"] if (i + r) % 2 == 0 else p["bag_dk"])
            sandbag(tone, (ax + (bx - ax) * t, ay + (by - ay) * t, z + r * 0.16), size=(length / count * 0.98, 0.3, 0.17), rot_z=rot)


def gable(p, center, size, wall="olive", roof="steel_dk", door=True, cross=False):
    """Galpão de duas águas com a cumeeira ao longo de y, rodapé, e porta na face +x."""
    x, y, z = center
    sx, sy, sz = size
    box("shed_foot", p["concrete_dk"], (x, y, z), (sx + 0.1, sy + 0.1, 0.14), bevel=0.02)
    box("shed", p[wall], (x, y, z + 0.12), (sx, sy, sz), bevel=0.03)
    prism("shed_roof", p[roof], (x, y, z + 0.12 + sz), (sx + 0.24, sy + 0.2, sx * 0.34), ridge=0.5, bevel=0.02)
    box("shed_ridge", p["soot"], (x, y, z + 0.12 + sz + sx * 0.34 - 0.03), (0.12, sy + 0.24, 0.06), bevel=0.0)
    if door:
        box("shed_door", p["umber_dk"], (x + sx / 2, y, z + 0.12), (0.06, min(0.7, sy * 0.4), sz * 0.72), bevel=0.0)
        box("shed_lintel", p["steel_dk"], (x + sx / 2 + 0.01, y, z + 0.12 + sz * 0.72), (0.08, min(0.84, sy * 0.48), 0.08), bevel=0.0)
    if cross:
        box("stencil_v", p["ecru"], (x + sx / 2 + 0.02, y, z + sz * 0.95), (0.03, 0.09, 0.36), bevel=0.0)
        box("stencil_h", p["ecru"], (x + sx / 2 + 0.02, y, z + sz * 1.08), (0.03, 0.28, 0.09), bevel=0.0)


def beam_cross(p, pos, height=0.7, tone="ecru"):
    x, y, z = pos
    box("cross_v", p[tone], (x, y, z), (0.09, 0.09, height), bevel=0.0)
    box("cross_h", p[tone], (x, y, z + height * 0.6), (0.09, height * 0.62, 0.09), bevel=0.0)


def bell_tower(p, pos, height=2.6, side=0.74, body="steel", bell=True):
    """Torre de sino de aço: fuste, lanternim aberto com o sino de latão, telhado piramidal e cruz de viga."""
    x, y, z = pos
    box("tower_foot", p["concrete_dk"], (x, y, z), (side + 0.14, side + 0.14, 0.16), bevel=0.02)
    box("tower", p[body], (x, y, z + 0.14), (side, side, height * 0.62), bevel=0.03, taper=0.92, taper_y=0.92)
    top = z + 0.14 + height * 0.62
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        box("tower_post", p["steel_dk"], (x + sx * side * 0.36, y + sy * side * 0.36, top), (0.08, 0.08, height * 0.2), bevel=0.0)
    if bell:
        cyl("bell", p["brass"], (x, y, top + 0.04), 0.2, 0.26, sides=8, top_radius=0.09, bevel=0.0)
    box("tower_cap", p["steel_dk"], (x, y, top + height * 0.2), (side + 0.12, side + 0.12, 0.07), bevel=0.0)
    box("tower_roof", p["olive_dk"], (x, y, top + height * 0.2 + 0.07), (side + 0.06, side + 0.06, height * 0.2), bevel=0.0, taper=0.1, taper_y=0.1)
    beam_cross(p, (x, y, top + height * 0.4 + 0.02), height=0.42)


# ---------------------------------------------------------------------------------------------------------
# Tronco do quartel: Barracks -> Stronghold
# ---------------------------------------------------------------------------------------------------------


def h000_barracks():
    """Galpão industrial comprido e baixo com chaminé curta e pátio em ordem: a horizontal da raça."""
    p = pal()
    pad(p)
    gable(p, (-0.7, 0.0, 0.1), (1.9, 3.5, 1.05), cross=True)
    for y in (-1.15, 1.15):
        kit.window(p["soot"], p["flame"], (0.25, y, 0.62), "x+", w=0.2, h=0.3)
    kit.chimney(p["steel"], p["soot"], p["soot"], (-1.0, -1.2, 1.2), 1.15, radius=0.16)
    # Pátio: estaleiro de fuzis, bomba do tambor na porta, lousa do turno.
    crate(p, (1.2, -1.2, 0.1), rifles=True)
    crate(p, (1.25, -0.65, 0.1), size=(0.42, 0.42, 0.24), rot_z=0.3)
    drum(p, (0.55, 0.7, 0.1))
    beam("pump_handle", p["soot"], (0.55, 0.7, 0.55), (0.85, 0.82, 0.75), thick=0.04)
    slate(p, (1.35, 1.2, 0.1), rot_z=math.radians(200))
    for x in (0.9, 1.5):
        box("yard_line", p["ecru"], (x, 0.0, 0.1), (0.05, 1.5, 0.012), bevel=0.0)
    lantern(p, (0.62, -0.55, 0.1), post=0.9)


def h039_stronghold():
    """Bastião industrial: cubo de concreto com duas torres quadradas curtas (orelhas) e portão de aço."""
    p = pal()
    pad(p)
    box("glacis", p["concrete_dk"], (-0.15, 0, 0.1), (3.3, 3.3, 0.22), bevel=0.05, taper=0.93, taper_y=0.93)
    box("cube", p["concrete"], (-0.25, 0, 0.3), (2.7, 2.8, 1.5), bevel=0.05, taper=0.93, taper_y=0.93)
    box("deck", p["concrete_lt"], (-0.25, 0, 1.8), (2.4, 2.5, 0.06), bevel=0.0)
    merlons(p["concrete"], -1.4, 0.9, 1.86, 4, (0.34, 0.2, 0.2, 1.24), True)
    merlons(p["concrete"], -1.4, 0.9, 1.86, 4, (0.34, 0.2, 0.2, -1.24), True)
    for s in (-1, 1):
        box("ear_foot", p["concrete_dk"], (1.0, s * 1.1, 0.1), (1.0, 1.0, 0.24), bevel=0.03)
        box("ear", p["concrete"], (1.0, s * 1.1, 0.3), (0.86, 0.86, 2.1), bevel=0.04, taper=0.9, taper_y=0.9)
        box("ear_brim", p["steel_dk"], (1.0, s * 1.1, 2.4), (0.92, 0.92, 0.08), bevel=0.0)
        merlons(p["concrete_lt"], 0.66, 1.34, 2.48, 2, (0.24, 0.7, 0.16, s * 1.1), True)
        box("ear_slit", p["soot"], (1.4, s * 1.1, 1.5), (0.04, 0.36, 0.12), bevel=0.0)
    # Portão de duas folhas com travessas e cruz de estêncil.
    for s in (-1, 1):
        box("gate_leaf", p["steel_dk"], (1.12, s * 0.21, 0.3), (0.07, 0.4, 1.05), bevel=0.0)
        box("gate_rib", p["steel"], (1.16, s * 0.21, 0.72), (0.03, 0.4, 0.08), bevel=0.0)
    box("gate_lintel", p["concrete_dk"], (1.1, 0, 1.36), (0.14, 1.0, 0.16), bevel=0.02)
    box("stencil_v", p["ecru"], (1.13, 0, 1.56), (0.03, 0.08, 0.3), bevel=0.0)
    box("stencil_h", p["ecru"], (1.13, 0, 1.66), (0.03, 0.24, 0.08), bevel=0.0)
    drum(p, (1.6, -0.45, 0.1))
    lantern(p, (1.62, 0.45, 0.1), post=0.8)
    box("sunk_mud", p["oil"], (1.55, 0.0, 0.1), (0.6, 1.5, 0.015), bevel=0.0)


# ---------------------------------------------------------------------------------------------------------
# Tronco sagrado: Chapel -> Church -> Holy Altar
# ---------------------------------------------------------------------------------------------------------


def h037_chapel():
    """Capela de campanha: uma nave estreita com torre de sino de aço e cruz de viga, a vertical fina."""
    p = pal()
    pad(p)
    gable(p, (-0.55, 0.0, 0.1), (1.35, 2.5, 1.2), wall="olive", roof="olive_dk", door=False)
    for y in (-0.7, 0.0, 0.7):
        kit.window(p["soot"], p["flame"], (0.125, y, 0.6), "x+", w=0.12, h=0.44)
    bell_tower(p, (0.75, 0.0, 0.1), height=3.1, side=0.78)
    box("door", p["umber_dk"], (1.14, 0, 0.26), (0.05, 0.36, 0.62), bevel=0.0)
    box("porch", p["plank"], (1.45, 0, 0.1), (0.6, 0.9, 0.08), bevel=0.0)
    bag_wall(p, (1.25, 0.62), (1.85, 0.62), rows=2)
    bag_wall(p, (1.25, -0.62), (1.85, -0.62), rows=2)
    drum(p, (1.55, 1.1, 0.1))
    lantern(p, (1.72, 0.0, 0.18))


def h038_church():
    """Catedral da doutrina: nave dupla, duas torres e a rosácea industrial (engrenagem cruzada por cruz)."""
    p = pal()
    pad(p)
    for s in (-1, 1):
        gable(p, (-0.5, s * 0.72, 0.1), (1.35, 3.0, 1.35), wall="olive", roof="olive_dk", door=False)
    box("nave_join", p["olive"], (-0.5, 0, 0.22), (0.4, 3.0, 1.35), bevel=0.0)
    box("west_front", p["concrete"], (0.75, 0, 0.1), (0.5, 1.5, 2.0), bevel=0.03, taper_y=0.92)
    prism("west_gable", p["olive_dk"], (0.75, 0, 2.1), (1.5, 0.56, 0.5), ridge=0.5, rot_z=math.radians(90))
    # Rosácea: aro de latão dentado com a cruz em ecru.
    cyl("rose_rim", p["brass"], (1.0, 0, 1.45), 0.36, 0.06, sides=12, bevel=0.0, rot=("Y", math.radians(90)))
    cyl("rose_glass", p["flame"], (1.03, 0, 1.45), 0.27, 0.04, sides=12, bevel=0.0, rot=("Y", math.radians(90)))
    for i in range(8):
        a = i * math.tau / 8
        box("rose_tooth", p["brass"], (1.02, math.cos(a) * 0.4, 1.4 + math.sin(a) * 0.4), (0.06, 0.1, 0.1), bevel=0.0)
    box("rose_cross_v", p["ecru"], (1.08, 0, 1.2), (0.03, 0.07, 0.5), bevel=0.0)
    box("rose_cross_h", p["ecru"], (1.08, 0, 1.44), (0.03, 0.42, 0.07), bevel=0.0)
    for s in (-1, 1):
        bell_tower(p, (0.75, s * 1.15, 0.1), height=3.3 if s > 0 else 2.9, side=0.72, bell=s > 0)
    # Portão de ferro com estandartes de estêncil e o tambor atrás do sino.
    box("iron_gate", p["soot"], (1.02, 0, 0.12), (0.06, 0.6, 0.85), bevel=0.0)
    for y in (-0.2, 0.0, 0.2):
        box("gate_bar", p["steel"], (1.06, y, 0.14), (0.03, 0.04, 0.8), bevel=0.0)
    for s in (-1, 1):
        box("standard", p["ecru"], (1.3, s * 0.52, 0.5), (0.03, 0.2, 0.5), bevel=0.0)
        box("standard_pole", p["umber_dk"], (1.3, s * 0.52, 0.1), (0.05, 0.05, 1.05), bevel=0.0)
    drum(p, (-1.5, 1.6, 0.1))
    lantern(p, (1.6, 0.0, 0.1), post=0.55)


def h072_holy_altar():
    """Púlpito de ordens: plataforma em L de pedra e aço, altar-mapa e o grande turíbulo-lanterna na coluna."""
    p = pal()
    pad(p)
    box("dais_low", p["concrete_dk"], (-0.2, 0, 0.1), (3.3, 3.3, 0.3), bevel=0.05, taper=0.95, taper_y=0.95)
    box("dais_long", p["concrete"], (-0.55, 0, 0.4), (2.3, 3.0, 0.34), bevel=0.04)
    box("dais_arm", p["concrete"], (0.75, -0.95, 0.4), (1.1, 1.1, 0.34), bevel=0.04)
    box("dais_top", p["concrete_lt"], (-0.55, 0, 0.74), (2.1, 2.8, 0.04), bevel=0.0)
    for i in range(3):
        box("step", p["concrete_dk"], (0.9 + i * 0.26, 0.55, 0.1), (0.3, 1.3, 0.3 - i * 0.1), bevel=0.02)
    # Altar-mapa com régua e bandeirolas, sobre a plataforma.
    box("map_altar", p["steel"], (-0.5, 0.45, 0.78), (1.0, 1.5, 0.5), bevel=0.03)
    box("map_sheet", p["ecru"], (-0.5, 0.45, 1.28), (0.86, 1.3, 0.02), bevel=0.0)
    for x, y in ((-0.7, 0.2), (-0.3, 0.75), (-0.55, 0.9)):
        box("map_pin", p["brass"], (x, y, 1.3), (0.05, 0.05, 0.14), bevel=0.0)
    box("pulpit", p["umber"], (0.75, -0.95, 0.74), (0.7, 0.7, 0.7), bevel=0.03, taper=0.86, taper_y=0.86)
    box("pulpit_rail", p["steel_dk"], (0.75, -0.95, 1.44), (0.78, 0.78, 0.06), bevel=0.0)
    box("pulpit_book", p["ecru"], (0.95, -0.95, 1.5), (0.2, 0.34, 0.04), bevel=0.0, rot_z=0.2)
    # Coluna do turíbulo-lanterna: a peça mais alta, fora do centro.
    box("column_foot", p["concrete_dk"], (-1.25, -1.0, 0.74), (0.5, 0.5, 0.2), bevel=0.02)
    cyl("column", p["concrete"], (-1.25, -1.0, 0.92), 0.17, 1.9, sides=8, top_radius=0.13, bevel=0.0)
    beam("censer_arm", p["steel_dk"], (-1.25, -1.0, 2.75), (-0.75, -0.75, 2.9), thick=0.06)
    beam("censer_chain", p["soot"], (-0.75, -0.75, 2.9), (-0.75, -0.75, 2.45), thick=0.03)
    cyl("censer_bowl", p["brass"], (-0.75, -0.75, 2.12), 0.12, 0.2, sides=8, top_radius=0.22, bevel=0.0)
    box("censer_flame", p["flame"], (-0.75, -0.75, 2.3), (0.2, 0.2, 0.16), bevel=0.0, taper=0.4, taper_y=0.4)
    cyl("basin", p["brass"], (-0.6, -1.0, 0.78), 0.2, 0.2, sides=8, top_radius=0.3, bevel=0.0)
    drum(p, (-1.55, 1.4, 0.1))
    drum(p, (-1.2, 1.55, 0.1), tone="olive_dk")


# ---------------------------------------------------------------------------------------------------------
# Árvore de tiro: Sniper Nest -> Marksmen's Encampment | Gunner's Hall
# ---------------------------------------------------------------------------------------------------------


def h003_sniper_nest():
    """Ninho raso: plataforma de madeira afundada na lama, parapeito de sacos e cobertura de pranchas."""
    p = pal()
    pad(p)
    box("pit", p["oil"], (0, 0, 0.1), (2.6, 2.6, 0.02), bevel=0.0)
    box("deck", p["plank"], (0, 0, 0.1), (2.2, 2.2, 0.14), bevel=0.02)
    for i in range(5):
        box("deck_gap", p["umber_dk"], (-0.88 + i * 0.44, 0, 0.24), (0.03, 2.2, 0.01), bevel=0.0)
    bag_wall(p, (1.25, -1.2), (1.25, 1.2), rows=3)
    bag_wall(p, (-1.0, 1.25), (1.2, 1.25), rows=2)
    bag_wall(p, (-1.0, -1.25), (1.2, -1.25), rows=2)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        box("post", p["umber_dk"], (sx * 0.45 - 0.6, sy * 0.85, 0.24), (0.1, 0.1, 1.2 if sx < 0 else 1.0), bevel=0.0)
    cover = box("cover", p["umber"], (-0.6, 0, 1.3), (1.1, 2.0, 0.08), bevel=0.0)
    for v in cover.data.vertices:
        v.co.z += -0.2 * (v.co.x + 0.6)
    for y in (-0.6, 0.0, 0.6):
        box("cover_plank_gap", p["umber_dk"], (-0.6, y, 1.39), (1.1, 0.03, 0.01), bevel=0.0)
    beam("rifle_rest", p["steel_dk"], (0.6, -0.3, 0.75), (1.75, -0.3, 0.86), thick=0.045)
    crate(p, (-0.6, 0.5, 0.24), rifles=True)
    drum(p, (-1.5, -1.4, 0.1))
    box("mast", p["umber_dk"], (-1.5, 1.4, 0.1), (0.08, 0.08, 2.2), bevel=0.0)
    lantern(p, (-1.5, 1.4, 2.3))


def h0A1_marksmen_encampment():
    """Posto de tiro de precisão: bancada sob lona oliva, sacos em degraus e o mastro da flâmula de alça."""
    p = pal()
    pad(p)
    box("deck", p["plank"], (-0.1, 0, 0.1), (2.6, 2.8, 0.12), bevel=0.02)
    for step, x in enumerate((1.1, 1.45)):
        bag_wall(p, (x, -1.3), (x, 1.3), z=0.1, rows=4 - step * 2)
    bag_wall(p, (-0.9, -1.4), (1.0, -1.4), rows=2)
    bag_wall(p, (-0.9, 1.4), (1.0, 1.4), rows=2)
    box("bench", p["umber"], (0.45, 0, 0.22), (0.5, 2.0, 0.5), bevel=0.02)
    for y in (-0.6, 0.0, 0.6):
        beam("long_rifle", p["steel_dk"], (0.3, y, 0.78), (1.75, y, 1.5), thick=0.045)
        beam("reticle", p["brass"], (1.2, y - 0.07, 1.22), (1.2, y + 0.07, 1.36), thick=0.025)
    for sx, sy, h in ((-1.15, -1.1, 1.75), (-1.15, 1.1, 1.75), (-0.1, -1.1, 1.45), (-0.1, 1.1, 1.45)):
        box("awning_post", p["umber_dk"], (sx, sy, 0.2), (0.08, 0.08, h), bevel=0.0)
    awning = box("awning", p["canvas"], (-0.62, 0, 1.78), (1.25, 2.5, 0.06), bevel=0.0)
    for v in awning.data.vertices:
        v.co.z += -0.3 * (v.co.x + 0.62)
    box("awning_stripe", p["olive_dk"], (-0.02, 0, 1.6), (0.1, 2.5, 0.07), bevel=0.0)
    # Mastro alto com a flâmula de alça e a lousa de distâncias.
    box("mast", p["umber_dk"], (-1.55, 1.5, 0.1), (0.08, 0.08, 3.2), bevel=0.0)
    box("pennant", p["ecru"], (-1.3, 1.5, 2.9), (0.5, 0.03, 0.26), bevel=0.0, taper=0.2)
    box("pennant_band", p["brass"], (-1.5, 1.5, 2.9), (0.08, 0.04, 0.26), bevel=0.0)
    slate(p, (-1.2, -0.6, 0.22), rot_z=math.radians(180), lines=4)
    crate(p, (-0.7, 0.6, 0.22), size=(0.5, 0.4, 0.26))
    drum(p, (-0.2, -0.9, 0.22), lying=True)
    lantern(p, (-1.55, -1.5, 0.1), post=0.9)


def h05D_gunners_hall():
    """Estande de prova e escola de artilheiros: galpão de teste de lona rasgada e espaldão de sacos chamuscado."""
    p = pal()
    pad(p)
    # Galpão aberto na frente: três paredes, tesouras e lona rasgada (dois panos com um rasgo entre eles).
    box("back_wall", p["olive"], (-1.5, 0, 0.1), (0.14, 3.0, 1.5), bevel=0.02)
    for s in (-1, 1):
        box("side_wall", p["olive"], (-0.7, s * 1.5, 0.1), (1.7, 0.14, 1.5), bevel=0.02)
        box("side_post", p["umber_dk"], (0.2, s * 1.5, 0.1), (0.12, 0.12, 1.7), bevel=0.0)
    for y in (-1.5, -0.5, 0.5, 1.5):
        beam("truss", p["umber_dk"], (-1.5, y, 1.6), (0.25, y, 1.9), thick=0.07)
    for y0, y1, tone in ((-1.55, -0.2, "canvas"), (0.15, 1.55, "canvas")):
        cloth = box("canvas", p[tone], (-1.0, (y0 + y1) / 2, 1.7), (1.1, y1 - y0, 0.05), bevel=0.0)
        for v in cloth.data.vertices:
            v.co.z += 0.17 * (v.co.x + 1.0)
    box("canvas_flap", p["olive_dk"], (-0.7, -0.02, 1.6), (0.7, 0.3, 0.04), bevel=0.0, rot_z=0.5)
    # Bancada de prova com a peça curta e grossa no berço, e a bandeja de gotejamento por baixo.
    box("bench", p["steel"], (-0.6, 0, 0.1), (0.7, 1.8, 0.6), bevel=0.03)
    beam("barrel", p["soot"], (-0.7, 0, 0.92), (0.75, 0, 1.12), thick=0.2)
    box("muzzle_brake", p["steel_dk"], (0.78, 0, 1.0), (0.2, 0.3, 0.24), bevel=0.02)
    box("cradle", p["steel_dk"], (-0.4, 0, 0.7), (0.5, 0.44, 0.22), bevel=0.02)
    box("drip_tray", p["oil"], (-0.6, 0, 0.1), (1.0, 2.0, 0.02), bevel=0.0)
    cyl("ammo_drum", p["brass"], (-0.75, 0.6, 0.7), 0.2, 0.14, sides=10, bevel=0.0)
    # Espaldão do estande, enegrecido, na ponta da linha de tiro.
    bag_wall(p, (1.65, -1.2), (1.65, 1.2), rows=5, dark=True)
    bag_wall(p, (1.35, -1.0), (1.35, 1.0), rows=3, dark=True)
    box("scorch", p["soot"], (1.0, 0, 0.1), (0.7, 1.1, 0.015), bevel=0.0)
    drum(p, (-1.1, -1.05, 0.1))
    crate(p, (-1.0, 1.0, 0.1), size=(0.55, 0.4, 0.3))
    lantern(p, (0.2, 1.5, 1.8))


# ---------------------------------------------------------------------------------------------------------
# Postos avulsos de produção
# ---------------------------------------------------------------------------------------------------------


def h004_weapon_lab():
    """Laboratório de armas de trincheira: caixote de aço rebitado com a única chaminé declarada da raça."""
    p = pal()
    pad(p)
    box("lab_foot", p["concrete_dk"], (-0.4, 0, 0.1), (2.7, 2.7, 0.16), bevel=0.03)
    box("lab", p["steel"], (-0.4, 0, 0.24), (2.5, 2.5, 1.5), bevel=0.04)
    for z in (0.6, 1.2):
        box("lab_band", p["steel_dk"], (-0.4, 0, z), (2.54, 2.54, 0.07), bevel=0.0)
    for x in (-1.4, -0.9, -0.4, 0.1, 0.6):
        box("lab_rivet", p["soot"], (x, 1.27, 1.5), (0.07, 0.03, 0.07), bevel=0.0)
        box("lab_rivet", p["soot"], (x, -1.27, 1.5), (0.07, 0.03, 0.07), bevel=0.0)
    box("lab_roof", p["steel_dk"], (-0.4, 0, 1.74), (2.6, 2.6, 0.1), bevel=0.02)
    prism("lab_monitor", p["olive_dk"], (-0.2, 0.5, 1.84), (0.8, 1.3, 0.3), ridge=0.5)
    # A chaminé desproporcional.
    kit.chimney(p["concrete_dk"], p["ecru"], p["soot"], (-1.1, -0.75, 1.8), 2.7, radius=0.3)
    # Porta de carreta com trilho, e a bancada de fora com o tubo de morteiro inacabado.
    box("cart_door", p["umber_dk"], (0.86, -0.45, 0.24), (0.06, 1.0, 1.1), bevel=0.0)
    for y in (-0.75, -0.15):
        box("rail", p["soot"], (1.4, y, 0.1), (1.2, 0.05, 0.04), bevel=0.0)
    box("cart", p["plank"], (1.5, -0.45, 0.18), (0.6, 0.7, 0.22), bevel=0.02)
    box("bench", p["umber"], (1.3, 1.05, 0.1), (0.6, 1.0, 0.45), bevel=0.02)
    beam("mortar_tube", p["soot"], (1.15, 1.05, 0.55), (1.55, 1.05, 1.15), thick=0.17)
    box("mortar_plate", p["steel_dk"], (1.15, 1.05, 0.55), (0.34, 0.34, 0.05), bevel=0.0)
    for i in range(3):
        drum(p, (0.95 + i * 0.36, 1.75, 0.1), tone="olive_dk" if i == 1 else "steel_dk")
    box("sunk_mud", p["oil"], (-0.4, 0, 0.1), (2.9, 2.9, 0.012), bevel=0.0)
    lantern(p, (0.9, 0.35, 1.2))


def h015_gryphon_rock():
    """Pombal de guerra: torre-poleiro de madeira umbra com teto de lona oliva e rampa de terra batida."""
    p = pal()
    pad(p)
    # Rampa de decolagem em cunha, virada para a lane.
    ramp = box("ramp", p["mud"], (0.9, 0, 0.1), (2.0, 1.5, 0.9), bevel=0.0)
    for v in ramp.data.vertices:
        if v.co.x > 0.9 and v.co.z > 0.5:
            v.co.z = 0.14
    box("ramp_planks", p["plank"], (0.0, 0, 0.98), (0.5, 1.3, 0.05), bevel=0.0)
    # Torre-poleiro: quatro pernas abertas, plataforma, poleiro e teto cônico de lona.
    tx = -0.95
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        beam("leg", p["umber_dk"], (tx + sx * 0.8, sy * 0.8, 0.1), (tx + sx * 0.55, sy * 0.55, 1.9), thick=0.13)
        beam("brace", p["umber"], (tx + sx * 0.76, sy * 0.76, 0.5), (tx - sx * 0.6, sy * 0.6, 1.5), thick=0.06)
    box("loft_floor", p["plank"], (tx, 0, 1.9), (1.5, 1.5, 0.1), bevel=0.02)
    cyl("nest", p["bag"], (tx, 0, 2.0), 0.5, 0.2, sides=9, top_radius=0.6, bevel=0.0)
    cyl("egg", p["ecru"], (tx + 0.1, 0.05, 2.14), 0.14, 0.2, sides=7, top_radius=0.06, bevel=0.0)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        box("roof_post", p["umber_dk"], (tx + sx * 0.62, sy * 0.62, 2.0), (0.08, 0.08, 0.8), bevel=0.0)
    cyl("canvas_roof", p["canvas"], (tx, 0, 2.8), 1.1, 0.75, sides=8, top_radius=0.08, bevel=0.0)
    ring("canvas_hem", p["olive_dk"], (tx, 0, 2.78), 1.08, 0.06, thick=0.02, sides=8)
    beam("perch", p["umber"], (tx + 0.6, -0.9, 2.3), (tx + 0.6, 0.9, 2.3), thick=0.08)
    # Sino de chamada na corda (família do sino da Church) e o tambor de óleo de isca.
    beam("bell_arm", p["umber_dk"], (tx - 0.7, 0.75, 1.95), (tx - 1.1, 1.15, 2.2), thick=0.06)
    cyl("call_bell", p["brass"], (tx - 1.1, 1.15, 1.9), 0.14, 0.2, sides=8, top_radius=0.06, bevel=0.0)
    drum(p, (tx - 0.2, -1.5, 0.1))
    crate(p, (tx + 0.5, -1.45, 0.1), size=(0.4, 0.4, 0.26))
    lantern(p, (1.6, 1.2, 0.1), post=0.7)


def h00K_hjordhejmen():
    """Refinaria de Campanha nº 3: galpão de destilação com alambique de cobre no teto e o poço negro."""
    p = pal()
    pad(p)
    gable(p, (-0.6, 0.3, 0.1), (2.0, 2.4, 1.2), wall="umber", roof="steel_dk")
    # Alambique de cobre no telhado, com o capacete e o pescoço de cisne.
    cyl("still", p["copper"], (-0.6, 0.3, 1.7), 0.5, 0.75, sides=10, bevel=0.02)
    dome("still_head", p["copper"], (-0.6, 0.3, 2.45), 0.5, squash=0.8, sides=10)
    ring("still_band", p["brass"], (-0.6, 0.3, 2.0), 0.5, 0.07, sides=10)
    beam("swan_neck", p["copper"], (-0.6, 0.3, 2.8), (0.5, -0.7, 2.6), thick=0.1)
    beam("swan_drop", p["copper"], (0.5, -0.7, 2.6), (0.5, -0.7, 1.5), thick=0.1)
    # Serpentina do condensador num barril, e o cano de sucção descendo ao poço.
    cyl("condenser", p["umber_dk"], (0.5, -0.7, 0.1), 0.42, 0.9, sides=10, bevel=0.0)
    wire_coil(p["copper"], (0.5, -0.7, 1.0), (0.5, -0.7, 1.55), radius=0.22, turns=4)
    beam("suction", p["steel_dk"], (0.5, -1.05, 0.5), (1.2, -1.2, 0.5), thick=0.1)
    beam("suction_drop", p["steel_dk"], (1.2, -1.2, 0.5), (1.2, -1.2, 0.06), thick=0.1)
    cyl("well_rim", p["concrete_dk"], (1.2, -1.2, 0.1), 0.62, 0.16, sides=10, top_radius=0.55, bevel=0.0)
    cyl("well_oil", p["oil"], (1.2, -1.2, 0.2), 0.48, 0.05, sides=10, bevel=0.0)
    box("sunk_mud", p["oil"], (0.2, -0.2, 0.1), (3.0, 3.0, 0.012), bevel=0.0)
    drum(p, (1.3, 0.9, 0.1), tone="olive_dk")
    drum(p, (1.6, 0.55, 0.1))
    slate(p, (1.2, 1.5, 0.1), rot_z=math.radians(240))
    lantern(p, (-0.6, -0.95, 1.72))


# ---------------------------------------------------------------------------------------------------------
# Especiais
# ---------------------------------------------------------------------------------------------------------


def h001_artillery():
    """Plataforma de obuseiro: o cano a 45 graus é a diagonal assinatura, a única que aponta para cima."""
    p = pal()
    pad(p)
    cyl("emplacement", p["concrete_dk"], (0, 0, 0.1), 1.75, 0.22, sides=12, top_radius=1.6, bevel=0.0)
    cyl("turntable", p["concrete_lt"], (0, 0, 0.3), 1.2, 0.06, sides=12, bevel=0.0)
    for i in range(7):
        a = math.radians(-100 + i * 33)
        sandbag(p["bag"] if i % 2 else p["bag_dk"], (math.cos(a) * 1.5, math.sin(a) * 1.5, 0.3), rot_z=a + math.pi / 2)
        sandbag(p["bag_dk"] if i % 2 else p["bag"], (math.cos(a + 0.28) * 1.5, math.sin(a + 0.28) * 1.5, 0.46), rot_z=a + 0.28 + math.pi / 2)
    box("carriage", p["olive"], (-0.15, 0, 0.36), (1.3, 0.9, 0.36), bevel=0.04)
    for s in (-1, 1):
        cyl("wheel", p["umber_dk"], (-0.1, s * 0.6, 0.72), 0.44, 0.12, sides=10, bevel=0.0, rot=("X", math.radians(90)))
        cyl("hub", p["steel"], (-0.1, s * 0.68, 0.72), 0.12, 0.06, sides=8, bevel=0.0, rot=("X", math.radians(90)))
        beam("trail", p["olive_dk"], (-0.5, s * 0.3, 0.5), (-1.5, s * 0.75, 0.32), thick=0.14)
    beam("barrel", p["steel_dk"], (-0.45, 0, 0.75), (1.35, 0, 2.55), thick=0.3)
    beam("barrel_jacket", p["steel"], (-0.45, 0, 0.75), (0.35, 0, 1.55), thick=0.42)
    box("muzzle", p["soot"], (1.36, 0, 2.47), (0.3, 0.38, 0.3), bevel=0.02)
    box("shield", p["olive"], (0.15, 0, 0.9), (0.08, 1.1, 0.75), bevel=0.0, rot_z=0.0)
    box("breech", p["soot"], (-0.55, 0, 0.6), (0.4, 0.44, 0.4), bevel=0.03)
    for i, (x, y) in enumerate(((-1.2, -1.1), (-0.85, -1.3), (-1.05, -1.42))):
        cyl("shell", p["brass"], (x, y, 0.3), 0.09, 0.4, sides=7, top_radius=0.02 if i == 2 else 0.09, bevel=0.0)
    drum(p, (-1.1, 1.1, 0.3))
    drum(p, (-0.72, 1.3, 0.3), tone="olive_dk")
    slate(p, (0.6, -1.35, 0.3), rot_z=math.radians(110), lines=2)
    lantern(p, (0.75, 1.3, 0.3), post=0.6)


def h010_gjallarhorn():
    """Sirene do turno: corneta industrial de latão num cavalete de madeira umbra com o quadro do turno."""
    p = pal()
    pad(p)
    box("frame_foot", p["concrete_dk"], (-0.2, 0, 0.1), (2.4, 2.4, 0.14), bevel=0.02)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        beam("trestle_leg", p["umber_dk"], (-0.2 + sx * 1.0, sy * 1.0, 0.2), (-0.2 + sx * 0.5, sy * 0.6, 2.2), thick=0.15)
    for s in (-1, 1):
        beam("trestle_x", p["umber"], (0.8, s * 1.0, 0.4), (-0.7, s * 0.6, 2.1), thick=0.07)
        beam("trestle_x", p["umber"], (-1.2, s * 1.0, 0.4), (0.3, s * 0.6, 2.1), thick=0.07)
    box("trestle_deck", p["plank"], (-0.2, 0, 2.2), (1.3, 1.5, 0.1), bevel=0.02)
    prism("shed_roof", p["olive_dk"], (-0.2, 0, 3.05), (1.7, 1.9, 0.4), ridge=0.5)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        box("roof_post", p["umber_dk"], (-0.2 + sx * 0.55, sy * 0.65, 2.3), (0.08, 0.08, 0.76), bevel=0.0)
    # A corneta: cone de latão deitado, apontado para a lane, com o bocal preso ao reservatório.
    cyl("horn", p["brass"], (-0.55, 0, 2.62), 0.1, 1.9, sides=10, top_radius=0.62, bevel=0.0, rot=("Y", math.radians(82)))
    cyl("horn_bell_rim", p["soot"], (1.32, 0, 2.89), 0.63, 0.05, sides=10, bevel=0.0, rot=("Y", math.radians(82)))
    cyl("air_tank", p["steel"], (-0.75, 0, 2.3), 0.26, 0.5, sides=8, bevel=0.0)
    # Bomba manual ao pé do cavalete (ponto de óleo) e o quadro do turno.
    drum(p, (0.9, -1.35, 0.1))
    beam("pump_rod", p["soot"], (0.9, -1.35, 0.55), (0.9, -1.35, 1.0), thick=0.05)
    beam("pump_lever", p["steel_dk"], (0.6, -1.35, 1.0), (1.35, -1.35, 0.85), thick=0.05)
    beam("air_line", p["steel_dk"], (0.9, -1.2, 0.3), (-0.6, -0.2, 2.3), thick=0.05)
    box("shift_board", p["slate"], (1.25, 0.9, 0.5), (0.07, 0.9, 0.9), bevel=0.0, rot_z=0.3)
    for i in range(4):
        box("shift_chalk", p["ecru"], (1.31, 0.9, 0.62 + i * 0.18), (0.02, 0.6, 0.05), bevel=0.0, rot_z=0.3)
    box("board_legs", p["umber_dk"], (1.25, 0.9, 0.1), (0.09, 0.96, 0.42), bevel=0.0, rot_z=0.3)
    lantern(p, (-1.4, 1.4, 0.1), post=0.8)


def h05G_heroic_shrine():
    """Memorial de guerra industrial: obelisco de aço com a placa de nomes e a chama perpétua em vidro."""
    p = pal()
    pad(p)
    for i, (s, h) in enumerate(((3.2, 0.24), (2.4, 0.24), (1.6, 0.3))):
        box("plinth", p["concrete_dk" if i % 2 == 0 else "concrete"], (0, 0, 0.1 + sum((0.24, 0.24, 0.3)[:i])), (s, s, h), bevel=0.04, taper=0.96, taper_y=0.96)
    box("obelisk", p["steel"], (0, 0, 0.88), (0.85, 0.85, 2.6), bevel=0.03, taper=0.5, taper_y=0.5)
    box("obelisk_band", p["steel_dk"], (0, 0, 1.5), (0.74, 0.74, 0.08), bevel=0.0)
    box("obelisk_tip", p["steel_dk"], (0, 0, 3.48), (0.42, 0.42, 0.1), bevel=0.0)
    # Chama perpétua na lanterna do topo.
    box("lamp_glass", p["flame"], (0, 0, 3.58), (0.26, 0.26, 0.3), bevel=0.0)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        box("lamp_bar", p["soot"], (sx * 0.14, sy * 0.14, 3.58), (0.04, 0.04, 0.3), bevel=0.0)
    box("lamp_cap", p["brass"], (0, 0, 3.88), (0.4, 0.4, 0.12), bevel=0.0, taper=0.3, taper_y=0.3)
    # Placa de latão cheia de nomes na face da lane, e a lousa de baixas, sempre maior, ao lado.
    box("name_plate", p["brass"], (0.44, 0, 1.0), (0.05, 0.6, 1.0), bevel=0.0)
    for i in range(7):
        box("name_line", p["soot"], (0.47, 0, 1.08 + i * 0.12), (0.02, 0.44, 0.03), bevel=0.0)
    box("casualty_slate", p["slate"], (1.15, 0.95, 0.34), (0.07, 0.75, 1.3), bevel=0.0, rot_z=0.35)
    for i in range(9):
        box("casualty_line", p["ecru"], (1.2, 0.93, 0.44 + i * 0.13), (0.02, 0.55, 0.03), bevel=0.0, rot_z=0.35)
    for s in (-1, 1):
        cyl("wreath", p["olive"], (0.95, s * 0.35 - 0.3, 0.58), 0.2, 0.07, sides=8, bevel=0.0)
    drum(p, (-1.25, -1.2, 0.1))
    beam("feed_line", p["steel_dk"], (-1.25, -1.2, 0.5), (-0.3, -0.3, 0.9), thick=0.045)
    lantern(p, (1.4, -1.3, 0.34))


def h07U_vessel_of_purity():
    """Relicário industrial: caldeirão-lâmpada de latão selado sobre base de concreto, com escape e manômetro."""
    p = pal()
    pad(p)
    box("base", p["concrete_dk"], (0, 0, 0.1), (2.6, 2.6, 0.3), bevel=0.05, taper=0.94, taper_y=0.94)
    box("base_top", p["concrete"], (0, 0, 0.4), (2.0, 2.0, 0.26), bevel=0.04)
    cyl("burner", p["soot"], (0, 0, 0.66), 0.55, 0.2, sides=10, bevel=0.0)
    cyl("burner_glow", p["flame"], (0, 0, 0.8), 0.42, 0.08, sides=10, bevel=0.0)
    # O bojo: urna farta em três troncos de cone.
    cyl("urn_low", p["brass"], (0, 0, 0.9), 0.5, 0.5, sides=12, top_radius=0.95, bevel=0.0)
    cyl("urn_mid", p["brass"], (0, 0, 1.4), 0.95, 0.5, sides=12, bevel=0.0)
    cyl("urn_high", p["brass"], (0, 0, 1.9), 0.95, 0.45, sides=12, top_radius=0.45, bevel=0.0)
    ring("urn_band", p["steel_dk"], (0, 0, 1.6), 0.95, 0.1, sides=12)
    cyl("urn_neck", p["steel_dk"], (0, 0, 2.35), 0.45, 0.22, sides=10, bevel=0.0)
    cyl("urn_lid", p["soot"], (0, 0, 2.57), 0.52, 0.1, sides=10, top_radius=0.2, bevel=0.0)
    for i in range(6):
        a = i * math.tau / 6
        box("lid_bolt", p["soot"], (math.cos(a) * 0.5, math.sin(a) * 0.5, 2.5), (0.09, 0.09, 0.14), bevel=0.0)
    # Cano de escape e a coluna pálida de vapor; manômetro virado para a lane.
    beam("exhaust", p["steel_dk"], (-0.5, 0.5, 2.3), (-1.0, 1.0, 2.6), thick=0.16)
    beam("exhaust_up", p["steel_dk"], (-1.0, 1.0, 2.6), (-1.0, 1.0, 3.5), thick=0.16)
    cyl("steam", p["ecru"], (-1.0, 1.0, 3.55), 0.14, 0.5, sides=6, top_radius=0.3, bevel=0.0)
    cyl("gauge", p["ecru"], (0.97, 0, 1.62), 0.18, 0.05, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
    cyl("gauge_rim", p["soot"], (0.95, 0, 1.62), 0.22, 0.04, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
    beam("gauge_needle", p["soot"], (1.03, 0, 1.62), (1.03, 0.1, 1.74), thick=0.025)
    drum(p, (1.0, -1.0, 0.4))
    beam("feed", p["steel_dk"], (1.0, -1.0, 0.8), (0.4, -0.4, 0.75), thick=0.05)
    lantern(p, (1.0, 1.0, 0.4), post=0.5)


# ---------------------------------------------------------------------------------------------------------
# Torres
# ---------------------------------------------------------------------------------------------------------


def h081_tiny_watch_tower():
    """Posto de vigia de campanha: torre de treliça de aço (a única da raça) com plataforma de pranchas."""
    p = pal()
    box("pad", p["mud"], (0, 0, 0), (2.4, 2.4, 0.1), bevel=0.03)
    box("footing", p["concrete_dk"], (0, 0, 0.1), (1.9, 1.9, 0.3), bevel=0.04, taper=0.9, taper_y=0.9)
    kit.derrick(p["steel"], p["steel_dk"], None, (0, 0, 0.4), base=1.5, top=1.0, height=2.9)
    box("platform", p["plank"], (0, 0, 3.3), (1.6, 1.6, 0.1), bevel=0.02)
    for s in (-1, 1):
        box("rail", p["umber_dk"], (0, s * 0.76, 3.4), (1.6, 0.06, 0.34), bevel=0.0)
        box("rail", p["umber_dk"], (s * 0.76, 0, 3.4), (0.06, 1.6, 0.34), bevel=0.0)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        box("roof_post", p["steel_dk"], (sx * 0.7, sy * 0.7, 3.4), (0.06, 0.06, 0.95), bevel=0.0)
    box("roof", p["olive_dk"], (0, 0, 4.35), (1.8, 1.8, 0.3), bevel=0.0, taper=0.2, taper_y=0.2)
    # Escada externa, lanterna no braço de içar e o sino de alarme.
    for i in range(9):
        box("rung", p["umber"], (-0.8 + i * 0.012, 0, 0.5 + i * 0.32), (0.05, 0.4, 0.05), bevel=0.0)
    for s in (-1, 1):
        beam("ladder_rail", p["umber_dk"], (-0.86, s * 0.2, 0.4), (-0.7, s * 0.2, 3.35), thick=0.05)
    beam("jib", p["steel_dk"], (0.7, 0.7, 4.2), (1.3, 1.0, 4.35), thick=0.06)
    lantern(p, (1.3, 1.0, 4.05))
    cyl("alarm_bell", p["brass"], (0.5, -0.5, 3.75), 0.14, 0.2, sides=8, top_radius=0.06, bevel=0.0)
    drum(p, (0.8, -0.85, 0.1))


def h082_tiny_multishot_tower():
    """Torre de metralhadora: cubo de concreto com três canos em leque num berço elevável a 30 graus."""
    p = pal()
    box("pad", p["mud"], (0, 0, 0), (2.4, 2.4, 0.1), bevel=0.03)
    box("footing", p["concrete_dk"], (0, 0, 0.1), (2.0, 2.0, 0.3), bevel=0.04, taper=0.92, taper_y=0.92)
    box("shaft", p["concrete"], (0, 0, 0.4), (1.5, 1.5, 2.4), bevel=0.05, taper=0.88, taper_y=0.88)
    box("brim", p["concrete_dk"], (0, 0, 2.8), (1.7, 1.7, 0.14), bevel=0.02)
    box("deck", p["concrete_lt"], (0, 0, 2.94), (1.5, 1.5, 0.05), bevel=0.0)
    bag_wall(p, (0.72, -0.6), (0.72, 0.6), z=2.98, rows=2)
    for s in (-1, 1):
        bag_wall(p, (-0.5, s * 0.72), (0.6, s * 0.72), z=2.98, rows=1)
    # Berço e os três canos em leque, apontando para cima e para a lane.
    box("cradle", p["steel_dk"], (0.05, 0, 2.98), (0.6, 0.8, 0.4), bevel=0.03)
    for dy in (-0.42, 0.0, 0.42):
        beam("barrel", p["soot"], (0.1, dy * 0.4, 3.3), (1.45, dy * 1.5, 4.08), thick=0.11)
        beam("jacket", p["steel"], (0.1, dy * 0.4, 3.3), (0.75, dy * 0.93, 3.68), thick=0.17)
    cyl("ammo_drum", p["brass"], (-0.3, 0, 3.38), 0.26, 0.16, sides=10, bevel=0.0, rot=("X", math.radians(90)))
    # Teto de lona enrolado atrás, tambor preso ao lado, sacos e o tambor de munição na base.
    cyl("furled_canvas", p["canvas"], (-0.65, -0.7, 3.2), 0.14, 1.4, sides=8, bevel=0.0, rot=("X", math.radians(-90)))
    for s in (-1, 1):
        box("canvas_post", p["umber_dk"], (-0.65, s * 0.65, 2.98), (0.07, 0.07, 0.9), bevel=0.0)
    box("slit", p["soot"], (0.72, 0, 1.6), (0.04, 0.5, 0.14), bevel=0.0)
    drum(p, (0.0, -0.9, 0.4))
    box("drum_strap", p["soot"], (0.0, -0.82, 0.6), (0.4, 0.05, 0.06), bevel=0.0)
    bag_wall(p, (1.05, -0.7), (1.05, 0.7), z=0.1, rows=2)
    lantern(p, (-0.6, 0.6, 2.98))


def h006_watch_tower():
    """Torre de defesa de concreto: caponeira embaixo, plataforma de tiro em cima sob marquise de chapa."""
    p = pal()
    box("pad", p["mud"], (0, 0, 0), (2.8, 2.8, 0.1), bevel=0.03)
    box("caponier", p["concrete_dk"], (0, 0, 0.1), (2.4, 2.4, 1.1), bevel=0.06, taper=0.86, taper_y=0.86)
    for s in (-1, 1):
        box("capo_slit", p["soot"], (1.1, s * 0.5, 0.6), (0.06, 0.44, 0.14), bevel=0.0)
        box("capo_slit", p["soot"], (s * 0.5, 1.1, 0.6), (0.44, 0.06, 0.14), bevel=0.0)
        box("capo_slit", p["soot"], (s * 0.5, -1.1, 0.6), (0.44, 0.06, 0.14), bevel=0.0)
    box("shaft", p["concrete"], (0, 0, 1.2), (1.55, 1.55, 1.8), bevel=0.05, taper=0.9, taper_y=0.9)
    box("band", p["concrete_dk"], (0, 0, 2.0), (1.5, 1.5, 0.1), bevel=0.0)
    box("gallery", p["concrete_dk"], (0, 0, 3.0), (2.0, 2.0, 0.16), bevel=0.03)
    box("gallery_deck", p["concrete_lt"], (0, 0, 3.16), (1.8, 1.8, 0.04), bevel=0.0)
    merlons(p["concrete"], -0.9, 0.9, 3.2, 3, (0.4, 0.16, 0.3, 0.9), True)
    merlons(p["concrete"], -0.9, 0.9, 3.2, 3, (0.4, 0.16, 0.3, -0.9), True)
    merlons(p["concrete"], -0.9, 0.9, 3.2, 3, (0.4, 0.16, 0.3, 0.9), False)
    merlons(p["concrete"], -0.9, 0.9, 3.2, 3, (0.4, 0.16, 0.3, -0.9), False)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        box("canopy_post", p["steel_dk"], (sx * 0.75, sy * 0.75, 3.2), (0.08, 0.08, 0.9), bevel=0.0)
    box("canopy", p["steel"], (0, 0, 4.1), (2.3, 2.3, 0.1), bevel=0.02)
    box("canopy_top", p["olive_dk"], (0, 0, 4.2), (2.0, 2.0, 0.22), bevel=0.0, taper=0.5, taper_y=0.5)
    beam("gun", p["soot"], (0.3, 0, 3.55), (1.5, 0, 3.7), thick=0.12)
    # Lanterna de assalto com refletor, armário de munição de aço e o tambor na base.
    cyl("reflector", p["ecru"], (0.9, 0.7, 3.62), 0.2, 0.08, sides=8, top_radius=0.26, bevel=0.0, rot=("Y", math.radians(90)))
    lantern(p, (0.78, 0.7, 3.5))
    box("locker", p["steel_dk"], (1.05, -0.95, 0.1), (0.5, 0.6, 0.7), bevel=0.03)
    box("locker_band", p["brass"], (1.31, -0.95, 0.5), (0.02, 0.2, 0.08), bevel=0.0)
    drum(p, (1.1, 0.95, 0.1))


BUILDINGS = {
    "h000": h000_barracks,
    "h039": h039_stronghold,
    "h037": h037_chapel,
    "h038": h038_church,
    "h072": h072_holy_altar,
    "h003": h003_sniper_nest,
    "h0A1": h0A1_marksmen_encampment,
    "h05D": h05D_gunners_hall,
    "h004": h004_weapon_lab,
    "h015": h015_gryphon_rock,
    "h00K": h00K_hjordhejmen,
    "h001": h001_artillery,
    "h010": h010_gjallarhorn,
    "h05G": h05G_heroic_shrine,
    "h07U": h07U_vessel_of_purity,
    "h081": h081_tiny_watch_tower,
    "h082": h082_tiny_multishot_tower,
    "h006": h006_watch_tower,
}


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["all"]
    names = list(BUILDINGS) if args[0] == "all" else [args[0]]
    out_dir = game_paths.out_arg(args, "--out", "buildings", "human")
    render_dir = args[args.index("--render") + 1] if "--render" in args else ""
    for name in names:
        kit.build(name, out_dir, render_dir, make=BUILDINGS[name], views=(("front", -35.0),))


if __name__ == "__main__":
    main()
