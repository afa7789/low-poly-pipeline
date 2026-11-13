"""Prédios da raça Elf modelados por script (redesenho de reports/design/race-elf.md): um GLB por prédio.

Uso:
    blender -b --factory-startup --python tools/blender/buildings_elf.py -- <id|all> [--out DIR] [--render DIR]

Academia Nobre: a corte-escola do dia. Latão, vidro, turquesa, livro. Corpo em azul cianótipo e pérola, telhados
e cúpulas em pátina de cobre, o latão como único metal que brilha; geometria reta e ortogonal (nada de curva de
cílio, pano ou prata). Todo prédio assenta num estrado de madeira serrada sobre a lama, tem UM acento turquesa
(vidro ou faixa de prova) e um estágio visível da cadeia de refino: o frasco de óleo escuro sempre dentro de
vidro com tampa de latão (nunca derramado) e o manômetro. O único anel FECHADO da raça é o da Arcane Tower;
os demais anéis (armilar, arco de pouso) são abertos e segmentados. Ouro só no relicário (h059).
Pegada ~3,5 x 3,5 centrada na origem, a porta virada para +x; o jogo normaliza o tamanho, põe o prédio no
plinto do time e desenha a bandeira. Valores subidos em relação ao doc (a luz do jogo escurece).
"""

import itertools
import math
import os
import sys

from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_paths  # noqa: E402
import map_castles as kit
from map_castles import beam, box, cyl, dome, mat, prism, ring

AX, AY, AZ = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
DECK = 0.18  # topo do estrado de madeira


def pal():
    return {
        "ink": mat("plant_ink", 0x55798C),
        "ink_dk": mat("plant_ink_dark", 0x34505F),
        "pearl": mat("lime_pearl", 0xF1E9D3),
        "pearl_dk": mat("lime_pearl_dark", 0xCDC3A6),
        "stone": mat("pale_stone", 0xDDD4BC),
        "brass": mat("workshop_brass", 0xDDAA5C),
        "brass_dk": mat("workshop_brass_dark", 0xA9804A),
        "patina": mat("copper_patina", 0x78B3A0),
        "patina_dk": mat("copper_patina_dark", 0x52877A),
        "turq": mat("deep_turquoise", 0x2FA9A0),
        "glass": mat("turquoise_glass", 0x46DACD, emit=1.2),
        "oil": mat("dark_oil", 0x2D251A),
        "timber": mat("sawn_timber", 0xBC9E70),
        "timber_dk": mat("sawn_timber_dark", 0x8E7249),
        "mud": mat("mud", 0x66543F),
        "steel": mat("gauge_steel", 0xC8D0D4),
        "gold": mat("standard_gold", 0xF6D04D, emit=0.8),
    }


# ---------------------------------------------------------------------------------------------------------
# Peças da raça
# ---------------------------------------------------------------------------------------------------------


def pad(p, size=(3.5, 3.5)):
    """Lama + estrado de madeira serrada (a grade). O jogo normaliza pelo maior lado: laje sobrando encolhe."""
    box("pad", p["mud"], (0, 0, 0), (size[0], size[1], 0.1), bevel=0.03)
    box("deck", p["timber"], (0, 0, 0.1), (size[0] - 0.12, size[1] - 0.12, 0.08), bevel=0.02)
    for i in range(round(size[0] / 0.5) - 1):
        x = -size[0] / 2 + 0.5 * (i + 1)
        box("slat_gap", p["timber_dk"], (x, 0, DECK), (0.035, size[1] - 0.12, 0.012), bevel=0.0)


def disc(name, material, c, radius, thick, sides=12, axis="x"):
    """Disco de face para +x (axis x) ou +y (axis y); c é o centro."""
    x, y, z = c
    if axis == "x":
        return cyl(name, material, (x - thick / 2, y, z), radius, thick, sides=sides, bevel=0.0, rot=("Y", math.radians(90)))
    return cyl(name, material, (x, y + thick / 2, z), radius, thick, sides=sides, bevel=0.0, rot=("X", math.radians(90)))


def jar(p, pos, h=0.5, r=0.15):
    """Regra da raça: o óleo escuro sempre dentro de vidro. Frasco com base e tampa de latão, faixa de vidro."""
    x, y, z = pos
    cyl("jar_base", p["brass"], (x, y, z), r * 1.25, 0.05, sides=8, bevel=0.0)
    cyl("jar_oil", p["oil"], (x, y, z + 0.05), r, h, sides=8, bevel=0.0)
    cyl("jar_glass", p["glass"], (x, y, z + 0.05 + h * 0.62), r * 1.08, h * 0.3, sides=8, bevel=0.0)
    cyl("jar_cap", p["brass"], (x, y, z + 0.05 + h), r * 1.2, 0.05, sides=8, bevel=0.0)
    cyl("jar_stopper", p["brass_dk"], (x, y, z + 0.1 + h), r * 0.45, 0.08, sides=6, bevel=0.0)


def gauge(p, pos, r=0.17, rim="brass"):
    """Manômetro virado para +x: aro, mostrador pérola, ponteiro."""
    x, y, z = pos
    disc("gauge_rim", p[rim], (x, y, z), r * 1.25, 0.05)
    disc("gauge_face", p["pearl"], (x + 0.03, y, z), r, 0.05, sides=10)
    beam("gauge_needle", p["oil"], (x + 0.07, y, z), (x + 0.07, y + r * 0.55, z + r * 0.6), thick=0.03)


def column(p, pos, h=2.0, r=0.11, tone="pearl"):
    """Coluna canelada esbelta com base e capitel quadrados."""
    x, y, z = pos
    box("col_base", p["pearl_dk"], (x, y, z), (r * 3.0, r * 3.0, 0.1), bevel=0.01)
    cyl("col", p[tone], (x, y, z + 0.1), r, h - 0.22, sides=8, top_radius=r * 0.82, bevel=0.0)
    box("col_cap", p["brass"], (x, y, z + h - 0.12), (r * 3.0, r * 3.0, 0.12), bevel=0.01)


def arc(material, c, radius, u, v, a0, a1, n=8, thick=0.08):
    """Arco de a0 a a1 (graus) no plano u,v, feito de vigas. 0..360 fecha o anel."""
    pts = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        pts.append(Vector(c) + u * (radius * math.cos(a)) + v * (radius * math.sin(a)))
    for a, b in itertools.pairwise(pts):
        beam("arc", material, a, b, thick=thick)


def armillary(p, c, radius, tone="brass"):
    """Esfera armilar ABERTA: três anéis inclinados, cada um em dois arcos com vãos (nunca um círculo fechado)."""
    m = p[tone]
    for u, v in ((AY, AZ), (AX, AZ), (AX, AY)):
        arc(m, c, radius, u, v, 15, 165, n=5, thick=0.07)
        arc(m, c, radius, u, v, 195, 345, n=5, thick=0.07)
    box("armillary_core", p["glass"], (c[0] - 0.1, c[1] - 0.1, c[2] - 0.1), (0.2, 0.2, 0.2), bevel=0.0)


def tripod(p, pos, h=0.8, spread=0.3, tone="brass_dk"):
    x, y, z = pos
    for k in range(3):
        a = k * math.tau / 3
        beam("tripod_leg", p[tone], (x + math.cos(a) * spread, y + math.sin(a) * spread, z), (x, y, z + h), thick=0.04)


def tilt_roof(ob, ref_x, k):
    """Inclina a laje: z desce k por unidade de x a partir de ref_x (cobertura de uma água virada para a frente)."""
    for v in ob.data.vertices:
        v.co.z -= k * (v.co.x - ref_x)


def target(p, c, r=0.3, outer="brass", ring_tone="pearl"):
    """Alvo numerado: discos concêntricos virados para +x."""
    disc("target_outer", p[outer], c, r, 0.05)
    disc("target_mid", p[ring_tone], (c[0] + 0.03, c[1], c[2]), r * 0.7, 0.05)
    disc("target_in", p["turq"], (c[0] + 0.06, c[1], c[2]), r * 0.38, 0.05, sides=10)
    disc("target_eye", p["brass"], (c[0] + 0.09, c[1], c[2]), r * 0.12, 0.04, sides=6)


# ---------------------------------------------------------------------------------------------------------
# Torres
# ---------------------------------------------------------------------------------------------------------


def h014_arcane_tower():
    """Torre de aferição: base de pedra com bandas de escala, fuste de latão torneado, domo turquesa e o ÚNICO
    anel fechado graduado da raça no topo (o furo da silhueta)."""
    p = pal()
    pad(p, (2.8, 2.8))
    box("base", p["stone"], (0, 0, DECK), (2.2, 2.2, 0.95), bevel=0.04, taper=0.88, taper_y=0.88)
    for z in (0.5, 0.82):
        box("base_band", p["ink"], (0, 0, z), (2.12, 2.12, 0.07), bevel=0.0, taper=0.97, taper_y=0.97)
    for i in range(5):
        box("scale_cut", p["ink_dk"], (1.0, -0.9 + i * 0.4, 0.4), (0.05, 0.07, 0.4 if i % 2 == 0 else 0.24), bevel=0.0)
    cyl("shaft", p["brass"], (0, 0, 1.13), 0.52, 1.62, sides=10, top_radius=0.34, bevel=0.0)
    for z, r in ((1.55, 0.47), (2.05, 0.4)):
        ring("shaft_band", p["brass_dk"], (0, 0, z), r, 0.1, sides=10)
    cyl("collar", p["brass_dk"], (0, 0, 2.7), 0.5, 0.1, sides=10, bevel=0.0)
    dome("orb", p["glass"], (0, 0, 2.8), 0.42, squash=0.85, sides=10)
    beam("ring_post", p["brass_dk"], (0, 0, 3.05), (0, 0, 3.25), thick=0.1)
    # O anel fechado: 16 vigas, quatro marcas turquesa nos pontos cardeais, tiques nos demais.
    c = (0, 0, 3.95)
    arc(p["brass"], c, 0.72, AY, AZ, 0, 360, n=16, thick=0.1)
    for i in range(16):
        a = i * math.tau / 16
        pos = (0.0, math.cos(a) * 0.72, 3.95 + math.sin(a) * 0.72)
        if i % 4 == 0:
            box("ring_mark", p["turq"], (pos[0] - 0.07, pos[1] - 0.07, pos[2] - 0.07), (0.14, 0.14, 0.14), bevel=0.0)
        else:
            box("ring_tick", p["pearl"], (pos[0] - 0.04, pos[1] - 0.04, pos[2] - 0.04), (0.08, 0.08, 0.08), bevel=0.0)
    for s in (-1, 1):
        beam("ring_arm", p["brass_dk"], (0, s * 0.3, 2.75), (0, s * 0.68, 3.75), thick=0.07)
    box("door", p["ink_dk"], (1.0, -0.15, DECK), (0.05, 0.4, 0.5), bevel=0.0)
    gauge(p, (1.0, 0.55, 0.62))
    jar(p, (1.15, -0.95, DECK))


# ---------------------------------------------------------------------------------------------------------
# Tronco do arco: Archery Range -> Archery Tower
# ---------------------------------------------------------------------------------------------------------


def stand(p, tall):
    """Estande de prova: galpão de ripas atrás, pórtico de treliça aberto na frente, trilho serrado no chão e
    alvos numerados no fundo. tall acrescenta o andar da torre de sinais (mesma massa, uma água a mais)."""
    pad(p)
    box("shed", p["timber"], (-1.2, 0, DECK), (1.2, 3.1, 1.1), bevel=0.03)
    for i in range(11):
        box("slat", p["timber_dk"], (-0.59, -1.4 + i * 0.28, 0.25), (0.03, 0.05, 0.95), bevel=0.0)
    box("shed_door", p["ink_dk"], (-0.58, 0, DECK), (0.05, 0.6, 0.85), bevel=0.0)
    disc("door_hoop", p["turq"], (-0.56, 0, 1.0), 0.2, 0.05)
    # Pórtico de tiro: quatro postes e treliça em X nas laterais, sem teto.
    for sx in (-0.5, 0.5):
        for sy in (-1.45, 1.45):
            box("porch_post", p["timber_dk"], (sx, sy, DECK), (0.1, 0.1, 1.1), bevel=0.0)
    for sy in (-1.45, 1.45):
        beam("lattice", p["timber_dk"], (-0.5, sy, DECK), (0.5, sy, 1.25), thick=0.05)
        beam("lattice", p["timber_dk"], (-0.5, sy, 1.25), (0.5, sy, DECK), thick=0.05)
        beam("porch_rail", p["brass_dk"], (-0.5, sy, 1.28), (0.5, sy, 1.28), thick=0.07)
    beam("porch_rail", p["brass_dk"], (0.5, -1.45, 1.28), (0.5, 1.45, 1.28), thick=0.07)
    # Trilho serrado no piso, do pórtico aos alvos.
    for y in (-0.2, 0.2):
        box("floor_rail", p["brass"], (0.5, y, DECK), (1.0, 0.05, 0.05), bevel=0.0)
    # Alvos numerados na armação do fundo.
    top = 1.9 if tall else 1.35
    box("hoop_frame_beam", p["timber_dk"], (1.45, 0, top), (0.08, 2.5, 0.08), bevel=0.0)
    for sy in (-1.2, 1.2):
        box("hoop_post", p["timber_dk"], (1.45, sy, DECK), (0.1, 0.1, top - 0.1), bevel=0.0)
    for i, y in enumerate((-0.75, 0.0, 0.75)):
        z = top - 0.45 if tall else 0.9
        target(p, (1.5, y, z - (i % 2) * 0.12 + (0.0 if i != 1 else 0.1)), r=0.3 if not tall else 0.34, outer="turq" if tall else "brass")
        beam("hoop_cord", p["ink_dk"], (1.45, y, top), (1.45, y, z + 0.3), thick=0.025)
    # Polia e carretel, quadro de tabelas, frasco.
    disc("spool", p["brass"], (-0.55, -1.2, 0.7), 0.16, 0.08, sides=8)
    disc("spool_core", p["pearl"], (-0.52, -1.2, 0.7), 0.08, 0.1, sides=6)
    beam("spool_cord", p["ink_dk"], (-0.5, -1.2, 0.7), (1.4, -1.0, 0.95), thick=0.02)
    box("table_legs", p["timber_dk"], (0.95, 1.35, DECK), (0.08, 0.8, 0.4), bevel=0.0)
    box("table_board", p["ink_dk"], (0.95, 1.35, 0.5), (0.06, 0.8, 0.6), bevel=0.0)
    for i in range(3):
        box("table_line", p["pearl"], (1.0, 1.35, 0.62 + i * 0.14), (0.02, 0.55 - i * 0.1, 0.04), bevel=0.0)
    jar(p, (0.95, -1.35, DECK), h=0.4)
    gauge(p, (-0.56, 0.95, 0.55), r=0.14)
    if not tall:
        roof = box("shed_roof", p["patina"], (-1.15, 0, 1.28), (1.3, 3.3, 0.1), bevel=0.02)
        tilt_roof(roof, -1.15, 0.28)
        return
    # Andar de cima: balcão sobre o galpão, pequeno andar com telhado de duas águas e clarabóia de vidro.
    box("balcony", p["patina_dk"], (-1.1, 0, 1.28), (1.5, 3.3, 0.1), bevel=0.02)
    box("upper", p["ink"], (-1.2, 0, 1.38), (0.95, 2.3, 1.0), bevel=0.03)
    kit.window(p["ink_dk"], p["glass"], (-0.725, -0.6, 1.75), "x+", w=0.2, h=0.4)
    kit.window(p["ink_dk"], p["glass"], (-0.725, 0.6, 1.75), "x+", w=0.2, h=0.4)
    prism("upper_roof", p["patina"], (-1.2, 0, 2.38), (1.3, 2.5, 0.65), ridge=0.5)
    box("skylight", p["glass"], (-1.35, 0, 2.95), (0.5, 1.1, 0.24), bevel=0.0)
    box("skylight_cap", p["brass"], (-1.35, 0, 3.17), (0.56, 1.16, 0.05), bevel=0.0)
    # Cata-vento de sinais e a bandeira turquesa de prova no topo.
    beam("vane_pole", p["brass_dk"], (-1.35, 0.9, 2.9), (-1.35, 0.9, 3.9), thick=0.05)
    box("vane_flag", p["turq"], (-1.35, 0.9, 3.45), (0.04, 0.55, 0.38), bevel=0.0)
    beam("vane_arrow", p["brass"], (-1.35, 0.9, 3.9), (-0.8, 0.9, 3.9), thick=0.05)
    # Luneta em tripé no balcão, apontada para os alvos.
    tripod(p, (-0.55, -0.9, 1.38), h=0.55)
    beam("scope", p["brass"], (-0.7, -0.9, 1.9), (0.0, -0.9, 2.15), thick=0.1)
    disc("scope_lens", p["glass"], (0.0, -0.9, 2.15), 0.07, 0.04, sides=8)


def h08X_archery_range():
    stand(pal(), tall=False)


def h08Y_archery_tower():
    stand(pal(), tall=True)


# ---------------------------------------------------------------------------------------------------------
# Academia de Bloodthirster e a Cidade da Magia
# ---------------------------------------------------------------------------------------------------------


def h00V_war_academy():
    """Oficina do ricochete: duas naves de telhado reto, capela de fumaça de vidro na fachada, pêndulos-alvo,
    pátio cercado por fita métrica e o armilar aberto no teto."""
    p = pal()
    pad(p)
    for y in (-0.85, 0.85):
        box("bay", p["ink"], (-0.95, y, DECK), (1.4, 1.6, 1.15), bevel=0.03)
        box("bay_band", p["pearl"], (-0.95, y, 1.0), (1.46, 1.66, 0.08), bevel=0.0)
        prism("bay_roof", p["patina"], (-0.95, y, 1.33), (1.7, 1.6, 0.6), ridge=0.5, rot_z=math.radians(90))
    for y in (-0.85, 0.85):
        box("bay_ridge", p["brass"], (-0.95, y, 1.86), (1.5, 0.1, 0.06), bevel=0.0)
    # Capela de fumaça: caixa de latão com vidro turquesa e o cano de escape que sobe pelo beiral.
    box("cupboard", p["brass_dk"], (-0.28, -0.85, DECK), (0.55, 1.1, 1.15), bevel=0.03)
    box("cupboard_glass", p["glass"], (0.0, -0.85, 0.35), (0.05, 0.8, 0.8), bevel=0.0)
    box("cupboard_top", p["brass"], (-0.28, -0.85, 1.3), (0.6, 1.14, 0.06), bevel=0.0)
    beam("vent", p["brass"], (-0.4, -0.85, 1.33), (-0.4, -0.85, 2.3), thick=0.12)
    box("vent_glow", p["glass"], (-0.48, -0.93, 2.25), (0.16, 0.16, 0.16), bevel=0.0)
    # Banca de frascos pela porta aberta da nave de trás.
    box("door", p["ink_dk"], (-0.23, 0.85, DECK), (0.05, 0.7, 0.85), bevel=0.0)
    box("bench", p["timber_dk"], (0.15, 0.85, DECK), (0.4, 1.0, 0.4), bevel=0.02)
    for i in range(4):
        cyl("flask", p["glass"] if i % 2 == 0 else p["pearl"], (0.15, 0.55 + i * 0.2, 0.58), 0.06, 0.2, sides=6, bevel=0.0)
    # Pêndulos-alvo na fachada.
    for y in (0.5, 1.2):
        beam("pendulum_arm", p["brass_dk"], (-0.2, y, 1.5), (0.55, y, 1.5), thick=0.05)
        beam("pendulum_cord", p["ink_dk"], (0.5, y, 1.5), (0.5, y, 0.85), thick=0.02)
        disc("pendulum_target", p["turq"] if y > 1 else p["brass"], (0.5, y, 0.75), 0.16, 0.05, sides=10)
    # Armilar aberto no cume da nave de trás.
    beam("armillary_post", p["brass_dk"], (-0.95, 0.85, 1.9), (-1.0, 0.85, 2.3), thick=0.07)
    armillary(p, (-0.95, 0.85, 2.7), 0.42)
    # Pátio do ricochete: fita métrica em volta (postes + trilho zebrado).
    for i in range(6):
        y = -1.5 + i * 0.6
        box("tape_post", p["timber_dk"], (1.55, y, DECK), (0.07, 0.07, 0.55), bevel=0.0)
        if i < 5:
            box("tape", p["pearl"] if i % 2 == 0 else p["turq"], (1.55, y + 0.3, 0.62), (0.04, 0.58, 0.07), bevel=0.0)
    jar(p, (0.95, -1.45, DECK), h=0.55, r=0.17)
    gauge(p, (-0.22, -0.4, 0.95), r=0.12)


def h00Z_city_of_magic():
    """Casa de dosagem: bloco cúbico baixo, torre do relógio assimétrica na quina, braço projetor de reagente
    com mangueira e o tanque pulsante no teto."""
    p = pal()
    pad(p)
    box("block", p["stone"], (-0.6, 0, DECK), (2.2, 2.7, 1.25), bevel=0.04, taper=0.96, taper_y=0.96)
    box("block_band", p["ink"], (-0.6, 0, 1.3), (2.3, 2.8, 0.1), bevel=0.0)
    # Torre do relógio, projetada na quina da frente.
    box("clock_tower", p["pearl"], (0.35, -1.0, DECK), (0.95, 0.95, 3.0), bevel=0.04, taper=0.88, taper_y=0.88)
    box("clock_band", p["ink"], (0.35, -1.0, 1.4), (1.0, 1.0, 0.08), bevel=0.0)
    disc("clock_rim", p["brass"], (0.8, -1.0, 2.45), 0.4, 0.06, sides=12)
    disc("clock_dial", p["pearl"], (0.84, -1.0, 2.45), 0.33, 0.05, sides=12)
    beam("clock_hand_h", p["oil"], (0.9, -1.0, 2.45), (0.9, -0.78, 2.45), thick=0.04)
    beam("clock_hand_m", p["oil"], (0.9, -1.0, 2.45), (0.9, -1.0, 2.74), thick=0.04)
    box("clock_roof", p["patina"], (0.35, -1.0, 3.2), (1.05, 1.05, 0.55), bevel=0.0, taper=0.12, taper_y=0.12)
    box("clock_vane", p["brass"], (0.35, -1.0, 3.75), (0.04, 0.04, 0.3), bevel=0.0)
    # Tanque de reagente no teto (pulsa em turquesa) e a mangueira até o braço.
    cyl("tank", p["patina_dk"], (-1.1, 0.5, 1.4), 0.5, 0.75, sides=10, bevel=0.0)
    ring("tank_band", p["brass"], (-1.1, 0.5, 1.7), 0.5, 0.08, sides=10)
    dome("tank_cap", p["glass"], (-1.1, 0.5, 2.15), 0.4, squash=0.5, sides=10)
    beam("hose", p["ink_dk"], (-0.7, 0.55, 1.6), (-0.2, 0.8, 1.55), thick=0.1)
    beam("hose", p["ink_dk"], (-0.2, 0.8, 1.55), (0.5, 0.75, 1.1), thick=0.1)
    # Braço projetor: tubo de latão que sai da fachada, bocal na ponta.
    box("arm_mount", p["brass_dk"], (0.4, 0.75, 0.9), (0.36, 0.4, 0.45), bevel=0.02)
    beam("arm", p["brass"], (0.5, 0.75, 1.12), (1.75, 0.75, 1.5), thick=0.2)
    box("nozzle", p["ink_dk"], (1.7, 0.7, 1.4), (0.22, 0.28, 0.28), bevel=0.02)
    disc("nozzle_glow", p["glass"], (1.83, 0.75, 1.5), 0.07, 0.04, sides=6)
    # Porta com a vedação deformada (um batente torto) e fileira de frascos na soleira.
    box("door", p["ink_dk"], (0.4, 0.0, DECK), (0.05, 0.5, 0.85), bevel=0.0)
    box("frame_l", p["brass"], (0.4, -0.3, DECK), (0.1, 0.08, 0.95), bevel=0.0)
    box("frame_r", p["brass"], (0.4, 0.3, DECK), (0.1, 0.08, 0.95), bevel=0.0, rot_z=0.0)
    box("frame_top", p["brass"], (0.4, 0.0, 1.0), (0.12, 0.7, 0.1), bevel=0.0)
    box("seal_bulge", p["turq"], (0.46, 0.0, 0.6), (0.07, 0.12, 0.4), bevel=0.0, taper=1.6, taper_y=1.6)
    box("sill", p["timber_dk"], (0.45, -0.1, 0.5), (0.3, 1.0, 0.05), bevel=0.0)
    for i in range(5):
        cyl("flask", p["glass"] if i % 2 == 0 else p["pearl"], (0.55, -0.45 + i * 0.2, 0.55), 0.055, 0.2, sides=6, bevel=0.0)
    gauge(p, (0.4, 1.1, 0.75), r=0.13)
    jar(p, (1.1, 1.3, DECK), h=0.4)


# ---------------------------------------------------------------------------------------------------------
# Estação aérea e o relicário
# ---------------------------------------------------------------------------------------------------------


def h06Y_dragonhawk_portal():
    """Estação aérea: dois postes de latão segurando um grande arco de pouso numerado, ABERTO e segmentado,
    grade no chão, heliógrafo em tripé e estacas com cabos de amarração."""
    p = pal()
    pad(p)
    for s in (-1, 1):
        box("post_foot", p["ink"], (-0.1, s * 1.38, DECK), (0.5, 0.5, 0.3), bevel=0.03, taper=0.8, taper_y=0.8)
        box("post", p["brass"], (-0.1, s * 1.38, 0.45), (0.28, 0.28, 2.5), bevel=0.03, taper=0.8, taper_y=0.8)
        box("post_cap", p["brass_dk"], (-0.1, s * 1.38, 2.95), (0.4, 0.4, 0.1), bevel=0.0)
    # Lâmpada de sinal no poste do lado direito: o acento turquesa.
    box("lamp_base", p["ink_dk"], (-0.1, 1.38, 3.05), (0.24, 0.24, 0.06), bevel=0.0)
    box("lamp_glass", p["glass"], (-0.1, 1.38, 3.11), (0.2, 0.2, 0.3), bevel=0.0)
    box("lamp_cap", p["brass"], (-0.1, 1.38, 3.41), (0.26, 0.26, 0.05), bevel=0.0, taper=0.4, taper_y=0.4)
    # O arco de pouso: cinco segmentos com vãos, tiques de numeração em pérola.
    c = (-0.1, 0, 1.55)
    for a0, a1 in ((0, 30), (40, 70), (80, 100), (110, 140), (150, 180)):
        arc(p["brass"], c, 1.38, AY, AZ, a0, a1, n=3, thick=0.15)
    for k in range(7):
        a = math.radians(k * 30)
        box("arc_tick", p["pearl"], (-0.1 + 0.08, math.cos(a) * 1.38 - 0.04, 1.55 + math.sin(a) * 1.38 - 0.06), (0.04, 0.08, 0.12), bevel=0.0)
    beam("perch", p["timber_dk"], (-0.1, -1.38, 0.9), (-0.1, 1.38, 0.9), thick=0.1)
    # Heliógrafo em tripé (espelho de latão virado para a frente) e estacas com cabos.
    tripod(p, (1.2, -1.2, DECK), h=0.7, spread=0.28, tone="timber_dk")
    disc("mirror_rim", p["brass"], (1.2, -1.2, 0.98), 0.24, 0.05, sides=10)
    disc("mirror", p["glass"], (1.24, -1.2, 0.98), 0.19, 0.05, sides=10)
    for y in (-0.5, 0.6):
        beam("stake", p["timber_dk"], (1.4, y, DECK), (1.5, y, 0.7), thick=0.07)
        beam("tether", p["ink_dk"], (-0.1, y * 2.3 if abs(y) < 1 else y, 0.5), (1.45, y, 0.65), thick=0.025)
    jar(p, (0.95, 1.2, DECK), h=0.4)
    gauge(p, (0.07, -1.38, 1.0), r=0.12)


def h059_golden_shrine():
    """Cofre do padrão: pavilhão aberto de colunas esbeltas (a única obra vazada da raça) com a urna de vidro e
    a barra-padrão de ouro; cordão turquesa de isolamento, lâmpada-manômetro e foles da bomba."""
    p = pal()
    pad(p)
    spots = [(x, y) for x in (-1.25, 1.25) for y in (-1.25, 0.0, 1.25)] + [(0.0, -1.25), (0.0, 1.25)]
    for x, y in spots:
        column(p, (x, y, DECK), h=2.1)
    # Entablamento e cobertura apenas em vigas (nada de laje: a urna fica à vista de cima).
    for s in (-1, 1):
        box("architrave", p["brass_dk"], (0, s * 1.25, 2.28), (2.7, 0.18, 0.18), bevel=0.01)
        box("architrave", p["brass_dk"], (s * 1.25, 0, 2.28), (0.18, 2.7, 0.18), bevel=0.01)
        beam("rafter", p["patina_dk"], (s * 1.25, 1.25, 2.4), (0, 0, 3.1), thick=0.09)
        beam("rafter", p["patina_dk"], (s * 1.25, -1.25, 2.4), (0, 0, 3.1), thick=0.09)
    box("finial", p["brass"], (-0.07, -0.07, 3.0), (0.14, 0.14, 0.3), bevel=0.0)
    # Cordão turquesa de isolamento entre as colunas, com abertura na frente.
    for a, b in (((-1.25, -1.25), (-1.25, 1.25)), ((-1.25, -1.25), (1.25, -1.25)), ((-1.25, 1.25), (1.25, 1.25)), ((1.25, -1.25), (1.25, -0.4)), ((1.25, 0.4), (1.25, 1.25))):
        beam("cord", p["turq"], (a[0], a[1], 0.75), (b[0], b[1], 0.75), thick=0.05)
    # Urna: pedestal, vidro, a barra de ouro saindo pelo topo (o metro étalon).
    box("pedestal", p["stone"], (0, 0, DECK), (1.0, 1.0, 0.55), bevel=0.03, taper=0.9, taper_y=0.9)
    cyl("urn_base", p["brass"], (0, 0, 0.73), 0.5, 0.08, sides=10, bevel=0.0)
    cyl("urn_glass", p["glass"], (0, 0, 0.81), 0.42, 0.7, sides=10, bevel=0.0)
    cyl("urn_lid", p["brass"], (0, 0, 1.51), 0.46, 0.08, sides=10, bevel=0.0)
    box("standard_bar", p["gold"], (-0.09, -0.09, 0.9), (0.18, 0.18, 1.1), bevel=0.01)
    box("standard_top", p["gold"], (-0.12, -0.12, 2.0), (0.24, 0.24, 0.1), bevel=0.0, taper=0.6, taper_y=0.6)
    # Lâmpada de referência com manômetro, foles da bomba e o tubo até o pedestal.
    box("lamp_post", p["brass_dk"], (0.95, -0.85, DECK), (0.08, 0.08, 0.85), bevel=0.0)
    box("lamp_glass", p["glass"], (0.95, -0.85, 1.03), (0.16, 0.16, 0.2), bevel=0.0)
    gauge(p, (1.0, -0.85, 0.6), r=0.13)
    for i in range(5):
        box("bellows", p["ink_dk"] if i % 2 else p["brass"], (-1.0, 0.85, DECK + i * 0.11), (0.7 - i * 0.04, 0.5, 0.11), bevel=0.0)
    beam("pump_pipe", p["brass_dk"], (-0.7, 0.75, 0.4), (-0.2, 0.3, 0.45), thick=0.07)
    jar(p, (-1.0, -0.85, DECK), h=0.45)


# ---------------------------------------------------------------------------------------------------------
# Tronco da esgrima: Hall of Honor -> Hall of the Eldest
# ---------------------------------------------------------------------------------------------------------


def sword(p, pos, twin=False):
    """Monumento da espada-padrão cravada (ponta para baixo); twin cruza uma segunda."""
    x, y, z = pos
    box("sword_plinth", p["stone"], (x, y, z), (0.6, 0.6, 0.3), bevel=0.03, taper=0.8, taper_y=0.8)
    z += 0.3
    if twin:
        for s in (-1, 1):
            beam("sword_blade", p["steel"], (x, y - s * 0.5, z + 0.1), (x, y + s * 0.5, z + 2.1), thick=0.1)
            beam("sword_guard", p["brass"], (x, y + s * 0.42 - 0.2, z + 1.72), (x, y + s * 0.42 + 0.2, z + 1.72), thick=0.07)
        box("sword_boss", p["brass"], (x - 0.09, y - 0.09, z + 1.0), (0.18, 0.18, 0.18), bevel=0.0)
        return
    cyl("sword_tip", p["steel"], (x, y, z), 0.02, 0.35, sides=4, top_radius=0.1, bevel=0.0)
    box("sword_blade", p["steel"], (x, y, z + 0.35), (0.06, 0.22, 1.6), bevel=0.01)
    for i in range(8):
        box("sword_grad", p["ink_dk"], (x + 0.035, y + 0.07, z + 0.5 + i * 0.18), (0.02, 0.1 if i % 2 else 0.06, 0.03), bevel=0.0)
    box("sword_guard", p["brass"], (x, y, z + 1.95), (0.12, 0.8, 0.1), bevel=0.01)
    box("sword_grip", p["ink_dk"], (x, y, z + 2.05), (0.07, 0.07, 0.3), bevel=0.0)
    box("sword_pommel", p["brass"], (x, y, z + 2.35), (0.14, 0.14, 0.12), bevel=0.0)


def court(p, upgraded):
    """Corte de provas: corpo de oficina com a fachada de frontão em degraus e beiral reto, espada-monumento
    no pátio, banca de registro e o barril de têmpera. upgraded troca o telhado por tambor + cúpula de pátina
    baixa, acrescenta colunata curta, a segunda espada cruzada e as placas de grau."""
    pad(p)
    depth = 1.6
    cx = -depth / 2
    box("hall", p["ink"], (cx, 0, DECK), (depth, 3.2, 1.3), bevel=0.03)
    box("hall_band", p["pearl"], (cx, 0, 1.0), (depth + 0.06, 3.26, 0.08), bevel=0.0)
    box("hall_foot", p["pearl_dk"], (cx, 0, DECK), (depth + 0.08, 3.28, 0.15), bevel=0.02)
    if upgraded:
        box("parapet", p["pearl"], (0.0, 0, 1.45), (0.2, 3.3, 0.22), bevel=0.01)
        box("roof_deck", p["patina_dk"], (cx, 0, 1.46), (depth - 0.05, 3.1, 0.06), bevel=0.0)
        cyl("drum", p["pearl"], (cx, 0, 1.5), 0.78, 0.45, sides=12, bevel=0.0)
        ring("drum_band", p["brass"], (cx, 0, 1.78), 0.78, 0.07, sides=12)
        dome("dome", p["patina"], (cx, 0, 1.95), 0.85, squash=0.7, sides=12)
        box("dome_finial", p["brass"], (cx - 0.04, -0.04, 2.5), (0.08, 0.08, 0.28), bevel=0.0)
        for y in (-1.4, -0.7, 0.7, 1.4):
            column(p, (0.55, y, DECK), h=1.25)
        box("colonnade_beam", p["brass_dk"], (0.55, 0, 1.43), (0.14, 3.2, 0.1), bevel=0.0)
        for i in range(3):
            box("grade_plate", p["brass"], (0.08, 0.0, 0.42 + i * 0.2), (0.03, 0.3 - i * 0.05, 0.1), bevel=0.0)
        sword(p, (1.15, 0.0, DECK), twin=True)
    else:
        prism("hall_roof", p["patina"], (cx, 0, 1.48), (3.3, depth + 0.1, 0.85), ridge=0.5, rot_z=math.radians(90))
        # Frontão em degraus à frente do telhado, na altura da cumeeira.
        for w, top in ((3.2, 1.48), (2.4, 1.78), (1.6, 2.08), (0.8, 2.38)):
            box("gable_step", p["pearl"], (0.0, 0, DECK), (0.16, w, top - DECK), bevel=0.01)
        sword(p, (1.15, 0.0, DECK))
    box("door", p["ink_dk"], (0.09, 0.0, DECK), (0.06, 0.7, 0.9), bevel=0.0)
    box("door_lintel", p["brass"], (0.1, 0.0, 1.05), (0.08, 0.9, 0.1), bevel=0.0)
    # Banca de registro com o bloco de placas, e o barril de têmpera com o óleo à vista.
    box("bench", p["timber_dk"], (0.95, -1.1, DECK), (0.45, 1.0, 0.45), bevel=0.02)
    box("plate_block", p["ink_dk"], (0.95, -1.15, 0.63), (0.3, 0.5, 0.12), bevel=0.0)
    for i in range(3):
        box("plate", p["pearl"], (0.97, -1.15, 0.75 + i * 0.03), (0.26, 0.44, 0.025), bevel=0.0)
    jar(p, (1.05, 1.2, DECK), h=0.5, r=0.2)
    # Bandeira turquesa do pátio.
    beam("flag_pole", p["brass_dk"], (1.45, -1.45, DECK), (1.45, -1.45, 2.3), thick=0.06)
    box("flag", p["turq"], (1.45, -1.12, 1.65), (0.04, 0.55, 0.55), bevel=0.0)


def h00T_hall_of_honor():
    court(pal(), upgraded=False)


def h03F_hall_of_the_eldest():
    court(pal(), upgraded=True)


# ---------------------------------------------------------------------------------------------------------
# Fábrica de cerco
# ---------------------------------------------------------------------------------------------------------


def h070_siege_factory():
    """Oficina de prova de tiro: galpão aberto com pórtico de latão e polias, trilho de prova saindo pela
    porta com a balista no carro, régua pintada cruzando o pátio pela lama e placas de medida cravadas."""
    p = pal()
    box("pad", p["mud"], (0, 0, 0), (3.5, 3.5, 0.1), bevel=0.03)
    box("deck", p["timber"], (-0.55, 0, 0.1), (2.4, 3.36, 0.08), bevel=0.02)
    # Régua pintada: faixas pérola e tinta cruzando o pátio de lama.
    for i in range(5):
        box("paint_scale", p["pearl"] if i % 2 == 0 else p["ink"], (0.95 + i * 0.16, 0, 0.1), (0.1 if i % 2 == 0 else 0.07, 3.3, 0.012), bevel=0.0)
    # Fundo e metade coberta do galpão (y > 0.5): o resto fica aberto para o pórtico aparecer.
    box("back_wall", p["ink"], (-1.65, 0, DECK), (0.15, 3.2, 1.7), bevel=0.02)
    box("side_wall", p["ink"], (-0.9, 1.55, DECK), (1.6, 0.12, 1.1), bevel=0.02)
    roof = box("roof", p["patina"], (-1.0, 1.1, 1.9), (1.5, 1.2, 0.08), bevel=0.01)
    tilt_roof(roof, -1.0, 0.18)
    for x in (-1.6, -0.45):
        box("roof_post", p["brass_dk"], (x, 1.55, DECK), (0.08, 0.08, 1.8), bevel=0.0)
    # Pórtico de latão: quatro pernas, vigas ao longo de x que seguem para fora da porta.
    for x in (-1.3, 0.3):
        for y in (-1.3, 0.1):
            box("gantry_leg", p["brass"], (x, y, DECK), (0.12, 0.12, 2.35), bevel=0.01)
        box("gantry_cross", p["brass"], (x, -0.6, 2.5), (0.12, 1.55, 0.12), bevel=0.01)
    for y in (-1.3, 0.1):
        box("gantry_runway", p["brass"], (-0.5, y, 2.5), (2.0, 0.12, 0.12), bevel=0.01)
        beam("gantry_brace", p["brass_dk"], (-1.3, y, 1.8), (-1.0, y, 2.5), thick=0.05)
    # Polia e talha penduradas do pórtico sobre o carro.
    disc("pulley", p["ink_dk"], (-0.5, -0.6, 2.3), 0.16, 0.1, sides=8, axis="y")
    beam("hoist_rope", p["ink_dk"], (-0.5, -0.6, 2.14), (-0.5, -0.6, 1.5), thick=0.025)
    box("hoist_hook", p["brass"], (-0.55, -0.65, 1.38), (0.1, 0.1, 0.12), bevel=0.0)
    # Trilho de prova até o pátio e o carro com a balista.
    for y in (-0.82, -0.38):
        box("proof_rail", p["ink_dk"], (0.2, y, DECK), (3.1, 0.06, 0.05), bevel=0.0)
    box("cart", p["timber_dk"], (-0.05, -0.6, 0.28), (1.0, 0.78, 0.14), bevel=0.02)
    for x in (-0.4, 0.3):
        for y in (-1.0, -0.2):
            disc("cart_wheel", p["ink_dk"], (x, y, 0.28), 0.1, 0.06, sides=8, axis="y")
    cyl("accumulator", p["brass"], (-0.4, -0.6, 0.42), 0.22, 0.5, sides=8, bevel=0.0)
    box("cradle", p["brass"], (-0.05, -0.6, 0.5), (1.0, 0.16, 0.14), bevel=0.01)
    for y in (-0.7, -0.5):
        beam("launch_rail", p["brass_dk"], (-0.3, y, 0.8), (0.95, y, 0.8), thick=0.07)
    beam("dart", p["steel"], (-0.2, -0.6, 0.86), (1.1, -0.6, 0.86), thick=0.07)
    box("dart_tip", p["steel"], (1.1, -0.64, 0.82), (0.16, 0.08, 0.08), bevel=0.0, taper=0.3, taper_y=0.3)
    cyl("ampoule", p["glass"], (0.5, -0.6, 0.93), 0.07, 0.2, sides=6, bevel=0.0)
    jar(p, (0.2, -0.6, 0.45), h=0.18, r=0.1)
    # Manômetro turquesa do acumulador na parede do fundo.
    gauge(p, (-1.35, 0.9, 1.1), r=0.22, rim="turq")
    cyl("wall_tank", p["brass"], (-1.45, 1.1, DECK), 0.28, 0.7, sides=8, bevel=0.0)
    # Placas de medida cravadas no pátio, empilhadas as já furadas.
    for y in (1.0, 1.35):
        for i in range(3):
            box("plate", p["pearl"] if i != 1 else p["ink"], (1.2, y, DECK + i * 0.18), (0.05, 0.5, 0.14), bevel=0.0)
        box("plate_stake", p["timber_dk"], (1.17, y, 0.1), (0.05, 0.05, 0.72), bevel=0.0)
    beam("vent_pipe", p["pearl_dk"], (-1.55, -1.4, DECK), (-1.55, -1.4, 2.4), thick=0.1)
    box("vent_cap", p["pearl"], (-1.62, -1.47, 2.4), (0.14, 0.14, 0.1), bevel=0.0)


# ---------------------------------------------------------------------------------------------------------
# Obelisco e escola
# ---------------------------------------------------------------------------------------------------------


def h005_obelisk_of_light():
    """Coluna de aferição: fuste de pedra pérola quadrado, escalonado e largo, cortes de escala nos cantos,
    fresta vertical de vidro turquesa em toda a altura (a luz desce como o traço de um nível de bolha)."""
    p = pal()
    pad(p, (2.8, 2.8))
    box("plinth", p["stone"], (0, 0, DECK), (2.2, 2.2, 0.32), bevel=0.04, taper=0.94, taper_y=0.94)
    z = 0.5
    for side, h in ((1.6, 1.3), (1.4, 1.2), (1.2, 1.2)):
        box("shaft", p["pearl"], (0, 0, z), (side, side, h), bevel=0.03)
        box("shaft_ring", p["pearl_dk"], (0, 0, z + h - 0.06), (side + 0.08, side + 0.08, 0.1), bevel=0.0)
        box("slit", p["glass"], (side / 2, 0, z + 0.05), (0.05, 0.16, h - 0.1), bevel=0.0)
        for sy in (-1, 1):
            n = int(h / 0.26)
            for k in range(n):
                box("corner_cut", p["ink_dk"], (side / 2 - 0.04, sy * (side / 2 - 0.04), z + 0.08 + k * 0.26), (0.1, 0.1, 0.04), bevel=0.0)
        z += h
    box("cap", p["brass"], (0, 0, z), (1.0, 1.0, 0.12), bevel=0.01)
    box("cap_top", p["pearl"], (0, 0, z + 0.12), (0.8, 0.8, 0.3), bevel=0.01, taper=0.4, taper_y=0.4)
    # Escala de latão e nível de bolha na base, prumo de bronze ao lado.
    box("scale_plate", p["brass"], (1.12, 0.55, 0.52), (0.05, 0.6, 0.28), bevel=0.0)
    for i in range(6):
        box("scale_tick", p["oil"], (1.16, 0.3 + i * 0.1, 0.55), (0.02, 0.03, 0.14 if i % 2 == 0 else 0.08), bevel=0.0)
    box("level_tube", p["glass"], (1.12, -0.5, 0.52), (0.07, 0.9, 0.09), bevel=0.0)
    box("level_end", p["brass"], (1.12, -0.95, 0.5), (0.09, 0.08, 0.13), bevel=0.0)
    box("level_end", p["brass"], (1.12, -0.05, 0.5), (0.09, 0.08, 0.13), bevel=0.0)
    beam("plumb_arm", p["brass_dk"], (0.8, -1.05, 2.9), (1.3, -1.05, 2.9), thick=0.06)
    beam("plumb_line", p["brass_dk"], (1.3, -1.05, 2.9), (1.3, -1.05, 0.7), thick=0.03)
    cyl("plumb_weight", p["brass"], (1.3, -1.05, 0.5), 0.11, 0.22, sides=6, top_radius=0.01, bevel=0.0)
    jar(p, (1.1, 1.05, DECK), h=0.45)


def h09X_school_of_wizardry():
    """Instituto de cálculo: casa de dois andares de janelas altas, relógio de sol com gnômon no pátio e, no
    telhado, a saída de destilação com vapor fino e claraboias de vidro."""
    p = pal()
    pad(p)
    box("house_low", p["stone"], (-0.95, 0, DECK), (1.6, 3.2, 1.05), bevel=0.03)
    box("house_band", p["brass_dk"], (-0.95, 0, 1.2), (1.66, 3.26, 0.09), bevel=0.0)
    box("house_up", p["ink"], (-0.95, 0, 1.29), (1.5, 3.1, 1.05), bevel=0.03)
    for i, y in enumerate((-1.1, -0.55, 0.0, 0.55, 1.1)):
        kit.window(p["ink_dk"], p["glass"], (-0.15, y, 0.4), "x+", w=0.2, h=0.62)
        kit.window(p["pearl"], p["glass"], (-0.2, y, 1.55), "x+", w=0.2, h=0.62)
    box("roof", p["patina_dk"], (-0.95, 0, 2.34), (1.7, 3.3, 0.35), bevel=0.0, taper=0.62, taper_y=0.7)
    for y in (-0.7, 0.7):
        box("skylight", p["glass"], (-1.25, y, 2.68), (0.55, 0.6, 0.1), bevel=0.0)
    # Saída de destilação: tubo de latão com colar, curva e a coluna de vapor pálido.
    cyl("vent", p["brass"], (-1.55, 0.2, 2.6), 0.2, 0.7, sides=8, top_radius=0.14, bevel=0.0)
    ring("vent_band", p["brass_dk"], (-1.55, 0.2, 3.0), 0.17, 0.07, sides=8)
    cyl("vent_cap", p["pearl"], (-1.55, 0.2, 3.3), 0.13, 0.05, sides=8, bevel=0.0)
    cyl("steam", p["pearl_dk"], (-1.55, 0.2, 3.35), 0.08, 0.45, sides=6, top_radius=0.2, bevel=0.0)
    # Prateleiras de frascos coladas nas janelas de baixo.
    box("shelf", p["timber_dk"], (-0.05, 0, 0.58), (0.25, 3.0, 0.05), bevel=0.0)
    for i in range(10):
        cyl("flask", p["glass"] if i % 2 == 0 else p["pearl"], (0.0, -1.3 + i * 0.29, 0.63), 0.05, 0.17, sides=6, bevel=0.0)
    # Pátio do gnômon: mostrador de pedra, aro de latão, gnômon em cunha e o quadrante solar.
    cyl("dial", p["stone"], (0.95, 0.0, DECK), 0.8, 0.1, sides=12, bevel=0.0)
    ring("dial_rim", p["brass"], (0.95, 0.0, 0.2), 0.78, 0.06, thick=0.03, sides=12)
    for k in range(8):
        a = k * math.tau / 8
        box("hour_mark", p["ink_dk"], (0.95 + math.cos(a) * 0.62 - 0.03, math.sin(a) * 0.62 - 0.03, 0.28), (0.06, 0.06, 0.02), bevel=0.0, rot_z=a)
    prism("gnomon", p["brass"], (0.95, 0.0, 0.28), (0.6, 0.05, 0.6), ridge=0.0)
    arc(p["brass"], (0.95, 0.0, 0.3), 0.4, AX, AZ, 0, 90, n=4, thick=0.04)
    jar(p, (0.4, -1.45, DECK), h=0.4)
    gauge(p, (-0.13, 1.45, 1.2), r=0.12)


def h00X_tower_of_supreme_magic():
    """Torre do meridiano: fuste largo de pátina torneado com escada de ferro em espiral por fora, a cúpula de
    vidro-farol turquesa no topo e o armilar de latão com anéis ABERTOS girando em volta."""
    p = pal()
    pad(p, (2.8, 2.8))
    box("plinth", p["stone"], (0, 0, DECK), (2.4, 2.4, 0.3), bevel=0.04, taper=0.92, taper_y=0.92)
    box("plinth_up", p["pearl"], (0, 0, 0.48), (1.9, 1.9, 0.18), bevel=0.03)
    cyl("shaft", p["patina"], (0, 0, 0.66), 0.88, 2.3, sides=10, top_radius=0.55, bevel=0.0)
    for z, r in ((1.2, 0.8), (1.9, 0.7), (2.5, 0.6)):
        ring("shaft_band", p["brass"], (0, 0, z), r, 0.08, sides=10)
    cyl("collar", p["brass"], (0, 0, 2.96), 0.66, 0.14, sides=10, bevel=0.0)
    dome("beacon", p["glass"], (0, 0, 3.1), 0.5, squash=1.0, sides=10)
    cyl("beacon_cap", p["brass"], (0, 0, 3.6), 0.14, 0.12, sides=6, bevel=0.0)
    kit.spike(p["brass"], (0, 0, 3.7), height=0.85, radius=0.07)
    armillary(p, (0, 0, 3.35), 1.05)
    # Escada de ferro em espiral: degraus colados ao fuste e corrimão de viga.
    steps = 13
    for k in range(steps):
        t = k / (steps - 1)
        z = 0.66 + t * 2.0
        ang = math.radians(-20 + k * 38)
        rr = 0.88 - 0.33 * ((z - 0.66) / 2.3) + 0.3
        box("stair_step", p["pearl_dk"], (math.cos(ang) * rr, math.sin(ang) * rr, z), (0.5, 0.34, 0.07), bevel=0.0, rot_z=ang)
    gauge(p, (0.94, -0.75, 0.62), r=0.15)
    jar(p, (1.15, 0.9, DECK), h=0.5)


BUILDINGS = {
    "h014": h014_arcane_tower,
    "h08X": h08X_archery_range,
    "h08Y": h08Y_archery_tower,
    "h00V": h00V_war_academy,
    "h00Z": h00Z_city_of_magic,
    "h06Y": h06Y_dragonhawk_portal,
    "h059": h059_golden_shrine,
    "h00T": h00T_hall_of_honor,
    "h03F": h03F_hall_of_the_eldest,
    "h070": h070_siege_factory,
    "h005": h005_obelisk_of_light,
    "h09X": h09X_school_of_wizardry,
    "h00X": h00X_tower_of_supreme_magic,
}


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["all"]
    names = list(BUILDINGS) if args[0] == "all" else [args[0]]
    out_dir = game_paths.out_arg(args, "--out", "buildings", "elf")
    render_dir = args[args.index("--render") + 1] if "--render" in args else ""
    for name in names:
        kit.build(name, out_dir, render_dir, make=BUILDINGS[name], views=(("front", -35.0),))


if __name__ == "__main__":
    main()
