"""Prédios da raça Pandaren Empire modelados por script (redesenho de reports/design/race-pandaren-empire.md): um GLB por prédio.

Uso:
    blender -b --factory-startup --python tools/blender/buildings_pandaren_empire.py -- <id|all> [--out DIR] [--render DIR]

Neutralidade Armada: o balcão que vende o resíduo do diesel aos dois lados. Barril de carvalho recosturado,
porcelana vidrada trincada (o "branco" da raça), ferro fuliginoso, cobre remendado, lona e cestaria de palha;
bambu só como pilar, chapéu e andaime. Silhueta "barriga empilhada": massa redonda embaixo, ombros estreitos e
um objeto duro e pequeno no topo (chaminé de fogareiro, bico de chaleira, torneira). Todo prédio tem um barril
com torneira e fica na lama de óleo até o joelho (pegada de lama com película iridescente). Pegada ~3,5 x 3,5
centrada na origem, a porta virada para +x; o jogo normaliza o tamanho, põe o plinto do time e a bandeira.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import map_castles as kit
from map_castles import beam, box, cyl, dome, mat, prism, ring


def pal():
    return {
        "oak": mat("barrel_oak", 0xC9965C),
        "oak_dk": mat("barrel_oak_dark", 0x93673F),
        "plank": mat("plank", 0xD9B47F),
        "porc": mat("porcelain", 0xEFEAD8),
        "porc_dk": mat("porcelain_chip", 0xC4BCA2),
        "glaze": mat("glaze_teal", 0x72BDB1),
        "glaze_dk": mat("glaze_teal_dark", 0x4B8E8A),
        "reed": mat("reed", 0xE3C272),
        "reed_dk": mat("reed_dark", 0xB89349),
        "bamboo": mat("bamboo_dry", 0xD6C463),
        "bamboo_dk": mat("bamboo_node", 0xA29340),
        "canvas": mat("canvas", 0xE4D3A4),
        "canvas_dk": mat("canvas_patch", 0xB8A57B),
        "iron": mat("iron", 0x848992),
        "iron_dk": mat("iron_dark", 0x5A5E67),
        "soot": mat("soot", 0x2E2C30),
        "copper": mat("copper", 0xDB8D55),
        "brass": mat("brass", 0xEABB4C),
        "brick": mat("brick", 0xCB7A5E),
        "brick_dk": mat("brick_dark", 0x9D5A46),
        "mud": mat("oil_mud", 0x6C5A47),
        "oil": mat("oil_pitch", 0x1C1920),
        "film": mat("oil_film", 0x4F7D8A),
        "smoke": mat("smoke", 0xDAD7D2),
        "zinc": mat("zinc", 0xBCC5C9),
        "clay": mat("clay", 0xCB8A5C),
        "red": mat("accent_red", 0xDD5A3E),
        "flame": mat("flame", 0xFFB347, emit=3.0),
    }


# ---------------------------------------------------------------------------------------------------------
# Peças da raça
# ---------------------------------------------------------------------------------------------------------


def pad(p, size=3.5):
    """Lama de óleo até o joelho, do tamanho do conteúdo (o jogo normaliza pelo maior lado), com poças de película."""
    box("pad", p["mud"], (0, 0, 0), (size, size, 0.1), bevel=0.03)
    for x, y, w, d in ((1.2, 0.9, 0.9, 0.6), (-0.3, -1.2, 0.8, 0.5), (1.0, -0.9, 0.5, 0.5)):
        box("film", p["film"], (x, y, 0.1), (w, d, 0.012), bevel=0.0)


def keg(p, pos, r=0.2, h=0.42, tone="oak", tap=True, lying=False, seal=False):
    """Barril com barriga (dois troncos de cone), cintas de ferro, torneira de latão virada para +x e, se pedido,
    o selo de cera por cima."""
    x, y, z = pos
    if lying:
        cyl("keg", p[tone], (x, y + h / 2, z + r), r, h, sides=10, bevel=0.0, rot=("X", math.radians(90)))
        for dy in (0.2, 0.8):
            cyl("keg_band", p["iron_dk"], (x, y + h * dy, z + r), r * 1.05, 0.04, sides=10, bevel=0.0, rot=("X", math.radians(90)))
        return
    cyl("keg", p[tone], (x, y, z), r * 0.88, h / 2, sides=10, top_radius=r, bevel=0.0)
    cyl("keg", p[tone], (x, y, z + h / 2), r, h / 2, sides=10, top_radius=r * 0.88, bevel=0.0)
    for f in (0.2, 0.8):
        cyl("keg_band", p["iron_dk"], (x, y, z + h * f - 0.02), r * 0.97, 0.05, sides=10, bevel=0.0)
    if tap:
        box("tap", p["brass"], (x + r * 0.95, y, z + h * 0.35), (0.1, 0.05, 0.05), bevel=0.0)
        box("tap_handle", p["brass"], (x + r * 1.12, y, z + h * 0.3), (0.04, 0.04, 0.1), bevel=0.0)
    if seal:
        cyl("wax", p["canvas"], (x, y, z + h), r * 0.55, 0.04, sides=8, bevel=0.0)


def keg_stack(p, base, tone="oak"):
    """Pirâmide de três barris com torneira: o estoque que vira cadeira de cobrança."""
    x, y, z = base
    keg(p, (x, y - 0.22, z), tone=tone)
    keg(p, (x, y + 0.22, z), tone=tone)
    keg(p, (x - 0.02, y, z + 0.42), tone=tone, seal=True)


def steam(p, pos, n=3, r=0.14):
    """Fio de vapor/fumaça: puffs que crescem e se desviam subindo."""
    x, y, z = pos
    for i in range(n):
        cyl("smoke", p["smoke"], (x + i * 0.07, y - i * 0.05, z + i * 0.26), r + i * 0.04, 0.2, sides=6, top_radius=r + i * 0.06, bevel=0.0)


def stove(p, pos, chimney=0.8):
    """Fogareiro de ferro portátil: tripé, boca de fogo acesa virada para +x e chaminé curta com fio de vapor."""
    x, y, z = pos
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        beam("stove_leg", p["iron_dk"], (x + sx * 0.17, y + sy * 0.17, z), (x + sx * 0.2, y + sy * 0.2, z + 0.22), thick=0.05)
    box("stove", p["iron"], (x, y, z + 0.2), (0.5, 0.5, 0.34), bevel=0.02)
    box("stove_mouth", p["flame"], (x + 0.255, y, z + 0.27), (0.04, 0.24, 0.14), bevel=0.0)
    cyl("stove_pipe", p["iron_dk"], (x - 0.1, y, z + 0.54), 0.09, chimney, sides=8, bevel=0.0)
    cyl("stove_cap", p["soot"], (x - 0.1, y, z + 0.54 + chimney), 0.12, 0.05, sides=8, bevel=0.0)
    steam(p, (x - 0.1, y, z + 0.6 + chimney), n=2, r=0.09)


def basket_roof(p, pos, r, h):
    """Telhado de cestaria: tronco de cone de palha com botão arredondado e cintas escuras (sem ponta)."""
    x, y, z = pos
    cyl("basket_roof", p["reed"], (x, y, z), r, h, sides=12, top_radius=r * 0.18, bevel=0.0)
    for f in (0.12, 0.4, 0.7):
        cyl("basket_weave", p["reed_dk"], (x, y, z + h * f), r * (1 - 0.82 * f) + 0.02, 0.05, sides=12, top_radius=r * (1 - 0.82 * f) + 0.02, bevel=0.0)
    dome("basket_knob", p["reed_dk"], (x, y, z + h - 0.02), r * 0.2, squash=0.8, sides=8)


def eave(p, pos, r, h=0.3, glaze="glaze"):
    """Beiral de porcelain vidrada trincada: cone achatado de 8 lados com aba verde e remendos mais escuros."""
    x, y, z = pos
    cyl("eave", p["porc"], (x, y, z), r, h, sides=8, top_radius=r * 0.5, bevel=0.0)
    cyl("eave_rim", p[glaze], (x, y, z), r * 1.04, 0.07, sides=8, bevel=0.0)
    for i in range(3):
        a = 0.6 + i * 2.2
        box("chip", p["porc_dk"], (x + math.cos(a) * r * 0.62, y + math.sin(a) * r * 0.62, z + h * 0.45), (0.18, 0.14, 0.04), bevel=0.0, rot_z=a)


def wounded(p, pos):
    """Paciente sentado: barriga de porcelana, cabeça, orelhas pretas e a atadura vermelha."""
    x, y, z = pos
    cyl("patient", p["porc"], (x, y, z), 0.16, 0.26, sides=8, top_radius=0.13, bevel=0.0)
    dome("patient_head", p["porc"], (x, y, z + 0.26), 0.12, squash=0.9, sides=8)
    for s in (-1, 1):
        box("patient_ear", p["soot"], (x, y + s * 0.1, z + 0.36), (0.06, 0.06, 0.06), bevel=0.0)
    box("bandage", p["red"], (x + 0.02, y, z + 0.31), (0.25, 0.25, 0.04), bevel=0.0)


def cup_row(p, a, b, z, n=4):
    """Fieira de xícaras lascadas no varal/balcão."""
    for i in range(n):
        t = (i + 0.5) / n
        cyl("cup", p["porc"], (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, z), 0.05, 0.07, sides=6, bevel=0.0)


def coin_stack(p, pos, n=4):
    x, y, z = pos
    for i in range(n):
        cyl("coin", p["brass"], (x, y, z + i * 0.04), 0.09, 0.035, sides=8, bevel=0.0)


def bamboo_post(p, pos, h):
    x, y, z = pos
    cyl("bamboo", p["bamboo"], (x, y, z), 0.07, h, sides=6, bevel=0.0)
    for f in (0.25, 0.55, 0.85):
        cyl("bamboo_node", p["bamboo_dk"], (x, y, z + h * f), 0.085, 0.04, sides=6, bevel=0.0)


def worm_coil(p, pos, r=0.2, turns=3, height=0.7):
    """Serpentina de condensador de eixo vertical: hélice de vigas de cobre."""
    x, y, z = pos
    steps = turns * 8
    prev = None
    for i in range(steps + 1):
        t = i / steps
        a = t * turns * math.tau
        pt = (x + math.cos(a) * r, y + math.sin(a) * r, z + t * height)
        if prev is not None:
            beam("worm", p["copper"], prev, pt, thick=0.05)
        prev = pt


# ---------------------------------------------------------------------------------------------------------
# Linha da cerveja: Brew Hut -> Fighting Tavern -> Temple of Ten Thousand Drinks
# ---------------------------------------------------------------------------------------------------------


def n03F_brew_hut():
    """Barril de pé com porta: tonel de carvalho sob telhado de cestaria, porta na barriga e barris na entrada."""
    p = pal()
    pad(p)
    cx = -0.35
    cyl("hut_low", p["oak"], (cx, 0, 0.1), 1.0, 0.85, sides=12, top_radius=1.2, bevel=0.0)
    cyl("hut_up", p["oak"], (cx, 0, 0.95), 1.2, 0.85, sides=12, top_radius=1.0, bevel=0.0)
    for z in (0.25, 0.95, 1.65):
        cyl("hut_band", p["iron_dk"], (cx, 0, z), 1.2 if z == 0.95 else 1.03, 0.07, sides=12, bevel=0.0)
    for i in range(6):
        a = i * math.tau / 6 + 0.3
        box("patch", p["oak_dk"], (cx + math.cos(a) * 1.15, math.sin(a) * 1.15, 0.5 + (i % 2) * 0.7), (0.05, 0.25, 0.3), bevel=0.0, rot_z=a)
    basket_roof(p, (cx, 0, 1.7), 1.45, 0.85)
    # Porta cortada na barriga, com batente e a soleira de louça.
    box("door_frame", p["oak_dk"], (cx + 1.08, 0, 0.1), (0.1, 0.78, 1.05), bevel=0.0)
    box("door", p["soot"], (cx + 1.12, 0, 0.1), (0.1, 0.56, 0.92), bevel=0.0)
    box("sill", p["plank"], (cx + 1.25, 0, 0.1), (0.3, 0.9, 0.1), bevel=0.0)
    cup_row(p, (cx + 1.3, -0.3), (cx + 1.3, 0.3), 0.2, n=3)
    keg_stack(p, (1.2, -1.05, 0.1))
    keg(p, (1.3, 1.2, 0.1), tone="oak_dk", seal=True)
    stove(p, (0.9, 0.78, 0.1), chimney=0.9)
    # Barril do recrutamento com a tábua de dívida.
    box("chit_board", p["canvas"], (1.55, -0.15, 0.1), (0.04, 0.4, 0.5), bevel=0.0)
    box("chit_line", p["red"], (1.58, -0.15, 0.4), (0.02, 0.3, 0.05), bevel=0.0)


def n03K_fighting_tavern():
    """O Brew Hut que cresceu um andar de tábuas afundadas: balcão quebrado atravessado na frente e escudos de tampa."""
    p = pal()
    pad(p)
    cx = -0.4
    cyl("tav_low", p["oak"], (cx, 0, 0.1), 1.1, 0.85, sides=12, top_radius=1.3, bevel=0.0)
    cyl("tav_up", p["oak"], (cx, 0, 0.95), 1.3, 0.55, sides=12, top_radius=1.15, bevel=0.0)
    for z in (0.25, 0.95):
        cyl("tav_band", p["iron_dk"], (cx, 0, z), 1.3 if z == 0.95 else 1.13, 0.07, sides=12, bevel=0.0)
    # Segundo andar de tábuas que desabou de um lado: caixa torta de ripas + remendo de lona.
    box("floor2", p["plank"], (cx, 0, 1.5), (1.9, 1.9, 0.9), bevel=0.03, taper=0.94, rot_z=0.2)
    for i in range(4):
        box("floor2_slat", p["oak_dk"], (cx + 0.96, -0.6 + i * 0.4, 1.5), (0.04, 0.05, 0.9), bevel=0.0, rot_z=0.2)
    box("floor2_patch", p["canvas_dk"], (cx + 0.5, 0.95, 1.65), (0.6, 0.06, 0.45), bevel=0.0, rot_z=0.2)
    kit.window(p["soot"], p["flame"], (cx + 0.97, 0.0, 1.8), "x+", w=0.22, h=0.28)
    # Telhado torto de cestaria, inclinado pelo andar que cedeu.
    roof = cyl("tav_roof", p["reed"], (cx, 0, 2.4), 1.15, 0.6, sides=12, top_radius=0.2, bevel=0.0)
    for v in roof.data.vertices:
        v.co.x += 0.25 * v.co.z
    cyl("tav_roof_rim", p["reed_dk"], (cx, 0, 2.4), 1.17, 0.06, sides=12, bevel=0.0)
    cyl("tav_chimney", p["iron_dk"], (cx - 0.7, -0.6, 2.4), 0.1, 0.6, sides=8, bevel=0.0)
    steam(p, (cx - 0.7, -0.6, 3.05), n=2, r=0.1)
    # Porta e balcão quebrado inclinado sobre a frente, com as xícaras enfileiradas.
    box("door", p["soot"], (cx + 1.1, 0.1, 0.1), (0.1, 0.55, 0.9), bevel=0.0)
    counter = box("counter", p["plank"], (1.15, 0, 0.45), (0.5, 1.8, 0.1), bevel=0.0)
    for v in counter.data.vertices:
        v.co.z += 0.5 * v.co.y * 0.35
    for s in (-1, 1):
        beam("counter_leg", p["oak_dk"], (1.15, s * 0.8, 0.1), (1.15, s * 0.75, 0.48 + s * 0.17), thick=0.08)
    cup_row(p, (1.15, -0.7), (1.15, 0.7), 0.56, n=5)
    # Parede de tampas de barril como escudos, e a lousa de dívidas.
    for i, (y, z) in enumerate(((-1.25, 0.5), (-1.25, 1.1), (-1.25, 1.6))):
        cyl("lid_shield", p["oak_dk" if i % 2 else "oak"], (cx + 0.1 + (i % 2) * 0.2, y - 0.05, z), 0.3, 0.07, sides=10, bevel=0.0, rot=("X", math.radians(90)))
    box("debt_slate", p["soot"], (1.55, 1.0, 0.1), (0.07, 0.6, 0.7), bevel=0.0, rot_z=0.3)
    for i in range(3):
        box("debt_chalk", p["porc"], (1.6, 1.0, 0.35 + i * 0.12), (0.02, 0.4, 0.03), bevel=0.0, rot_z=0.3)
    keg(p, (1.35, -1.35, 0.1), tone="oak_dk", seal=True)
    stove(p, (-1.3, 1.25, 0.1), chimney=0.7)


def n03P_temple():
    """Pagode de beirais trincados sobre pilha circular de barris: o altar é a adega; no topo, a torneira dourada."""
    p = pal()
    pad(p)
    # Anel de 8 barris deitados em pé sustentando a plataforma, mais um anel interno.
    for i in range(8):
        a = i * math.tau / 8
        keg(p, (math.cos(a) * 1.35, math.sin(a) * 1.35, 0.1), r=0.34, h=0.8, tone="oak" if i % 2 else "oak_dk", tap=(i == 0), seal=(i % 2 == 0))
    cyl("deck", p["plank"], (0, 0, 0.9), 1.65, 0.14, sides=16, bevel=0.0)
    # Barril central: a torre.
    cyl("core_low", p["oak"], (0, 0, 1.04), 0.8, 0.5, sides=12, top_radius=0.95, bevel=0.0)
    cyl("core_up", p["oak"], (0, 0, 1.54), 0.95, 0.5, sides=12, top_radius=0.8, bevel=0.0)
    cyl("core_band", p["iron_dk"], (0, 0, 1.52), 0.97, 0.07, sides=12, bevel=0.0)
    box("door", p["soot"], (0.88, 0, 1.04), (0.1, 0.5, 0.8), bevel=0.0)
    # Três beirais de porcelain trincada, cada um menor, com o central subindo entre eles.
    eave(p, (0, 0, 2.0), 1.7, h=0.38)
    cyl("mid_post", p["oak_dk"], (0, 0, 2.38), 0.55, 0.4, sides=10, bevel=0.0)
    eave(p, (0, 0, 2.78), 1.2, h=0.34, glaze="glaze_dk")
    cyl("up_post", p["oak_dk"], (0, 0, 3.12), 0.38, 0.3, sides=10, bevel=0.0)
    eave(p, (0, 0, 3.42), 0.8, h=0.3)
    # Torneira de latão polido como ouro, no topo: a divindade do templo.
    cyl("tap_stem", p["brass"], (0, 0, 3.72), 0.1, 0.35, sides=8, bevel=0.0)
    beam("tap_spout", p["brass"], (0, 0, 4.0), (0.35, 0, 3.9), thick=0.1)
    dome("tap_knob", p["brass"], (0, 0, 4.05), 0.14, squash=0.8, sides=8)
    steam(p, (0.35, 0, 3.4), n=2, r=0.08)
    # Escada de entrada de tábuas e as lanternas de fumaça (incensário a óleo).
    for i in range(3):
        box("step", p["plank"], (1.55 - i * 0.18, 0, 0.1 + i * 0.2), (0.3, 1.1, 0.2), bevel=0.0)
    stove(p, (1.25, 1.2, 0.1), chimney=0.6)


# ---------------------------------------------------------------------------------------------------------
# Linha do chá: Bamboo Dojo -> Sagepaw Sanctum
# ---------------------------------------------------------------------------------------------------------


def _hall_shell(p, cx, sx, sy, wall_h):
    """Salão de madeira sobre piso de tábuas: parede do fundo, meias-paredes laterais e telhado de porcelain."""
    box("hall_floor", p["plank"], (cx, 0, 0.1), (sx + 0.5, sy, 0.14), bevel=0.02)
    box("back_wall", p["oak"], (cx - sx / 2, 0, 0.24), (0.14, sy - 0.2, wall_h), bevel=0.02)
    for s in (-1, 1):
        box("side_wall", p["oak"], (cx, s * (sy / 2 - 0.1), 0.24), (sx, 0.12, wall_h * 0.55), bevel=0.02)


def _porcelain_roof(p, cx, sx, sy, z, cover=1.0):
    """Telhado de duas águas; cover < 1 encurta em x e o recua para o fundo, deixando a frente à vista."""
    w = (sx + 0.5) * cover
    cx = cx - (sx + 0.5 - w) / 2
    prism("hall_roof", p["porc"], (cx, 0, z), (w, sy + 0.3, 0.7), ridge=0.5, bevel=0.03)
    box("roof_ridge", p["glaze"], (cx, 0, z + 0.64), (0.14, sy + 0.34, 0.1), bevel=0.0)
    for i in range(3):
        box("roof_chip", p["porc_dk"], (cx + 0.3 - i * 0.3, -0.8 + i * 0.7, z + 0.3), (0.3, 0.26, 0.05), bevel=0.0, rot_z=i)
    box("roof_eave", p["glaze"], (cx, 0, z - 0.02), (w + 0.04, sy + 0.34, 0.07), bevel=0.0)


def n03D_bamboo_dojo():
    """Salão baixo de pilares de bambu seco, telhado de porcelain trincada e a frente toda aberta: fila de feridos e quadro de preços."""
    p = pal()
    pad(p)
    cx, sx, sy = -0.55, 2.3, 3.1
    _hall_shell(p, cx, sx, sy, 1.4)
    for x in (cx - sx / 2 + 0.1, cx + sx / 2 - 0.05):
        for y in (-sy / 2 + 0.2, 0.0, sy / 2 - 0.2):
            bamboo_post(p, (x, y, 0.24), 1.5)
    _porcelain_roof(p, cx, sx, sy, 1.74, cover=0.62)
    # Quadro de preços no fundo e o banco com os feridos, na ordem de pagamento.
    box("price_board", p["soot"], (cx - sx / 2 + 0.14, 0, 0.7), (0.05, 1.3, 0.6), bevel=0.0)
    for i in range(3):
        box("price_line", p["porc"], (cx - sx / 2 + 0.18, 0, 0.95 - i * 0.14), (0.02, 0.9 - i * 0.18, 0.04), bevel=0.0)
    box("bench", p["oak_dk"], (cx + 0.4, 0, 0.24), (0.4, 2.5, 0.28), bevel=0.02)
    for i in range(5):
        wounded(p, (cx + 0.4, -1.0 + i * 0.5, 0.52))
    # Caldeira de chá na varanda com mangueira, varal de xícaras e o fogareiro.
    cyl("porch_boiler", p["copper"], (1.2, -1.05, 0.1), 0.32, 0.7, sides=10, top_radius=0.26, bevel=0.0)
    cyl("boiler_pipe", p["iron_dk"], (1.2, -1.05, 0.8), 0.07, 0.5, sides=8, bevel=0.0)
    steam(p, (1.2, -1.05, 1.32), n=2, r=0.08)
    beam("hose", p["soot"], (1.2, -0.75, 0.4), (0.95, -0.2, 0.3), thick=0.04)
    box("boiler_fire", p["flame"], (1.52, -1.05, 0.22), (0.04, 0.18, 0.12), bevel=0.0)
    cup_row(p, (1.1, 0.45), (1.1, 1.3), 0.52, n=4)
    beam("cup_line", p["soot"], (1.1, 0.4, 0.5), (1.1, 1.35, 0.5), thick=0.02)
    for y in (0.4, 1.35):
        beam("cup_line_post", p["bamboo"], (1.1, y, 0.1), (1.1, y, 0.9), thick=0.05)
    keg(p, (1.4, 0.0, 0.1), r=0.16, h=0.36, seal=True)


def n03S_sagepaw_sanctum():
    """O mesmo salão, mais baixo e largo, fechado por portas de lona: chaminé de fornalha no telhado e fila de caldeiras na varanda."""
    p = pal()
    pad(p)
    cx, sx, sy = -0.55, 2.4, 3.3
    _hall_shell(p, cx, sx, sy, 1.15)
    # Frente fechada: duas folhas de lona remendada com cordas, em vez de bancada aberta.
    box("front_wall", p["oak"], (cx + sx / 2 - 0.1, 0, 0.24), (0.12, sy - 0.2, 1.15), bevel=0.02)
    for s in (-1, 1):
        box("tarp_door", p["canvas"], (cx + sx / 2 + 0.0, s * 0.33, 0.28), (0.07, 0.6, 0.95), bevel=0.0)
        box("tarp_patch", p["canvas_dk"], (cx + sx / 2 + 0.04, s * 0.33 + s * 0.1, 0.6), (0.03, 0.3, 0.3), bevel=0.0)
        for z in (0.45, 0.8):
            box("tarp_rope", p["oak_dk"], (cx + sx / 2 + 0.05, s * 0.33, z), (0.02, 0.62, 0.03), bevel=0.0)
    for y in (-sy / 2 + 0.2, sy / 2 - 0.2):
        for x in (cx - sx / 2 + 0.1, cx + sx / 2 - 0.05):
            bamboo_post(p, (x, y, 0.24), 1.2)
    _porcelain_roof(p, cx, sx, sy, 1.45, cover=0.8)
    # Chaminé de fornalha industrial atravessando o telhado, com anel de porcelain e fio de vapor.
    cyl("furnace_stack", p["iron"], (cx - 0.3, 0.6, 1.5), 0.3, 1.4, sides=10, top_radius=0.24, bevel=0.0)
    for z in (1.8, 2.4):
        cyl("furnace_band", p["porc"], (cx - 0.3, 0.6, z), 0.33, 0.12, sides=10, bevel=0.0)
    cyl("furnace_cap", p["soot"], (cx - 0.3, 0.6, 2.9), 0.3, 0.1, sides=10, bevel=0.0)
    steam(p, (cx - 0.3, 0.6, 3.0), n=3, r=0.14)
    # Fila de grandes caldeiras na varanda, bocas de fogo em dobro.
    for y in (-1.05, 0.0, 1.05):
        cyl("boiler", p["copper"], (1.25, y, 0.1), 0.38, 0.85, sides=10, top_radius=0.32, bevel=0.0)
        cyl("boiler_band", p["iron_dk"], (1.25, y, 0.45), 0.4, 0.06, sides=10, bevel=0.0)
        dome("boiler_lid", p["iron_dk"], (1.25, y, 0.95), 0.32, squash=0.5, sides=8)
        for dy in (-0.1, 0.1):
            box("fire_mouth", p["flame"], (1.62, y + dy, 0.22), (0.04, 0.1, 0.12), bevel=0.0)
        beam("boiler_hose", p["soot"], (1.25, y, 1.02), (0.7, y, 1.1), thick=0.04)
    keg(p, (1.55, 1.5, 0.1), r=0.16, h=0.36, tone="oak_dk")


# ---------------------------------------------------------------------------------------------------------
# Postos avulsos de produção
# ---------------------------------------------------------------------------------------------------------


def n03L_jade_shrine():
    """Jarro vidrado gigante rachado ao meio: a rachadura é a porta, o beiral vidrado por cima e o prato de chá com moedas ao pé."""
    p = pal()
    pad(p)
    cx = -0.3
    cyl("jar_foot", p["porc_dk"], (cx, 0, 0.1), 0.85, 0.15, sides=12, bevel=0.0)
    cyl("jar_belly", p["glaze"], (cx, 0, 0.25), 0.9, 0.75, sides=12, top_radius=1.4, bevel=0.0)
    cyl("jar_mid", p["glaze"], (cx, 0, 1.0), 1.4, 0.55, sides=12, top_radius=1.2, bevel=0.0)
    cyl("jar_shoulder", p["glaze"], (cx, 0, 1.55), 1.2, 0.55, sides=12, top_radius=0.62, bevel=0.0)
    cyl("jar_neck", p["glaze_dk"], (cx, 0, 2.1), 0.62, 0.3, sides=12, top_radius=0.55, bevel=0.0)
    cyl("jar_band", p["porc"], (cx, 0, 1.05), 1.42, 0.12, sides=12, bevel=0.0)
    ring("jar_band2", p["porc"], (cx, 0, 1.6), 1.0, 0.1, thick=0.03, sides=12)
    # Rachadura em zigue-zague como porta: fenda escura larga, de baixo até o ombro, com lábios lascados de porcelain.
    for k, (z, dy) in enumerate(((0.25, 0.0), (0.75, 0.12), (1.25, -0.1), (1.75, 0.05))):
        box("crack_gap", p["soot"], (cx + 0.98 - 0.1 * k, dy, z), (0.3, 0.5, 0.55), bevel=0.0, taper=0.8)
        box("crack_lip", p["porc"], (cx + 0.9 - 0.1 * k, dy - 0.33, z), (0.2, 0.08, 0.5), bevel=0.0, rot_z=0.15)
        box("crack_lip", p["porc"], (cx + 0.9 - 0.1 * k, dy + 0.33, z), (0.2, 0.08, 0.5), bevel=0.0, rot_z=-0.15)
    # Beiral vidrado por cima, lascado, e o selo de cera do gargalo.
    cyl("jar_mouth", p["soot"], (cx, 0, 2.38), 0.5, 0.05, sides=12, bevel=0.0)
    eave(p, (cx - 0.15, -0.1, 2.5), 0.85, h=0.28)
    dome("eave_knob", p["glaze_dk"], (cx - 0.15, -0.1, 2.76), 0.15, squash=0.8, sides=8)
    cyl("mist", p["smoke"], (cx + 0.5, 0.2, 2.45), 0.2, 0.3, sides=6, top_radius=0.12, bevel=0.0)
    cyl("mist", p["smoke"], (cx + 0.65, 0.25, 2.75), 0.14, 0.3, sides=6, top_radius=0.2, bevel=0.0)
    # Prato de chá com a pilha de moedas ao pé, o altar de petição e pagamento.
    cyl("tea_plate", p["porc"], (1.35, 0.15, 0.1), 0.5, 0.07, sides=10, bevel=0.0)
    for i, (dx, dy) in enumerate(((0.0, 0.0), (0.2, 0.18), (-0.15, 0.2), (0.12, -0.2))):
        coin_stack(p, (1.35 + dx, 0.15 + dy, 0.17), n=3 + i)
    cyl("tea_cup", p["glaze_dk"], (1.55, -0.1, 0.17), 0.09, 0.1, sides=8, bevel=0.0)
    keg(p, (0.9, -1.35, 0.1), r=0.17, h=0.38, seal=True)
    stove(p, (-1.3, 1.3, 0.1), chimney=0.6)


def n03H_residue_distillery():
    """Casa do alambique: caixa de tijolo e vergalhão com alambique de cobre remendado no topo, serpentina, chama-piloto e barris de borra."""
    p = pal()
    pad(p)
    cx = -0.45
    box("still_house", p["brick"], (cx, 0, 0.1), (2.2, 2.2, 1.35), bevel=0.04, taper=0.96, taper_y=0.96)
    for z in (0.5, 1.0):
        box("brick_band", p["brick_dk"], (cx, 0, z), (2.26, 2.26, 0.07), bevel=0.0)
    box("roof_slab", p["iron"], (cx, 0, 1.45), (2.4, 2.4, 0.12), bevel=0.02)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        beam("rebar", p["iron_dk"], (cx + sx * 1.0, sy * 1.0, 1.5), (cx + sx * 1.0, sy * 1.0, 1.95), thick=0.04)
    box("door", p["soot"], (cx + 1.1, 0.1, 0.1), (0.1, 0.55, 0.95), bevel=0.0)
    kit.window(p["soot"], p["flame"], (cx + 1.1, -0.7, 0.75), "x+", w=0.16, h=0.22)
    # O alambique: panela de cobre com remendos, capelo, pescoço de cisne caindo na serpentina.
    ax, ay = cx - 0.2, 0.3
    cyl("pot", p["copper"], (ax, ay, 1.57), 0.7, 0.7, sides=12, top_radius=0.62, bevel=0.0)
    cyl("pot_band", p["brass"], (ax, ay, 1.95), 0.68, 0.08, sides=12, bevel=0.0)
    box("pot_patch", p["brick_dk"], (ax + 0.62, ay + 0.1, 1.85), (0.06, 0.3, 0.3), bevel=0.0)
    dome("pot_head", p["copper"], (ax, ay, 2.27), 0.6, squash=0.9, sides=12)
    cyl("pot_neck", p["copper"], (ax, ay, 2.7), 0.2, 0.3, sides=8, top_radius=0.12, bevel=0.0)
    beam("swan", p["copper"], (ax, ay, 2.95), (ax + 0.6, -0.5, 2.8), thick=0.13)
    beam("swan", p["copper"], (ax + 0.6, -0.5, 2.8), (ax + 0.9, -1.2, 2.2), thick=0.13)
    beam("swan_drop", p["copper"], (ax + 0.9, -1.2, 2.2), (ax + 0.9, -1.35, 1.6), thick=0.13)
    # Condensador: tina com serpentina de cobre, fora da parede.
    cyl("worm_tub", p["oak"], (ax + 0.9, -1.35, 0.1), 0.4, 0.9, sides=10, bevel=0.0)
    cyl("worm_band", p["iron_dk"], (ax + 0.9, -1.35, 0.5), 0.42, 0.06, sides=10, bevel=0.0)
    worm_coil(p, (ax + 0.9, -1.35, 1.0), r=0.28, turns=2, height=0.6)
    beam("spout", p["copper"], (ax + 0.9, -1.35, 0.35), (ax + 1.4, -1.4, 0.35), thick=0.09)
    beam("pilot_stem", p["iron_dk"], (ax + 1.4, -1.4, 0.35), (ax + 1.4, -1.4, 0.7), thick=0.05)
    cyl("pilot_flame", p["flame"], (ax + 1.4, -1.4, 0.7), 0.1, 0.28, sides=6, top_radius=0.02, bevel=0.0)
    # Fileira de barris de borra na parede lateral e a bica pingando no pote de barro.
    for i in range(4):
        keg(p, (cx - 0.9 + i * 0.5, 1.4, 0.1), r=0.22, h=0.46, tone="oak_dk" if i % 2 else "oak", tap=False)
    beam("bica_pipe", p["iron_dk"], (cx + 1.1, 0.8, 0.7), (1.0, 0.8, 0.55), thick=0.07)
    box("drip", p["oil"], (1.02, 0.8, 0.2), (0.04, 0.04, 0.35), bevel=0.0)
    cyl("clay_pot", p["clay"], (1.1, 0.8, 0.1), 0.2, 0.2, sides=8, top_radius=0.15, bevel=0.0)
    cyl("drip_film", p["oil"], (1.15, 0.9, 0.1), 0.5, 0.02, sides=8, bevel=0.0)
    steam(p, (ax, ay, 3.0), n=2, r=0.08)


def n03Q_cloud_hangar():
    """Doca seca de balão: três arcos de madeira altos o bastante para o casco passar, o balão murcho pendurado dentro e os lastros ao pé."""
    p = pal()
    pad(p)
    xs = (-1.2, 0.05, 1.3)
    for x in xs:
        for s in (-1, 1):
            beam("arch_post", p["oak_dk"], (x, s * 1.35, 0.1), (x, s * 1.35, 2.5), thick=0.2)
            beam("arch_curve", p["oak_dk"], (x, s * 1.35, 2.5), (x, s * 0.8, 3.15), thick=0.2)
            beam("arch_curve", p["oak_dk"], (x, s * 0.8, 3.15), (x, 0.0, 3.4), thick=0.2)
            box("arch_foot", p["iron_dk"], (x, s * 1.35, 0.1), (0.35, 0.35, 0.18), bevel=0.0)
    # Cumeeiras e tirantes ao longo do vão, e a quilha de tábuas no chão onde o casco assenta.
    for y in (0.0, -1.35, 1.35):
        z0, z1 = (3.4, 3.4) if y == 0 else (2.5, 2.5)
        beam("ridge_beam", p["oak"], (xs[0], y, z0), (xs[-1], y, z1), thick=0.15)
    for y in (-0.5, 0.5):
        box("keel", p["plank"], (0.0, y, 0.1), (2.9, 0.3, 0.2), bevel=0.0)
    # O balão murcho: lona dobrada em gomos pendurada da cumeeira, com remendos de porcelain.
    dome("balloon", p["canvas"], (0.05, 0, 1.7), 1.25, squash=1.15, sides=12)
    dome("balloon_fold", p["canvas_dk"], (0.4, -0.4, 1.8), 0.9, squash=1.0, sides=8)
    for i in range(4):
        a = i * math.tau / 4 + 0.4
        box("balloon_patch", p["porc"], (0.05 + math.cos(a) * 0.95, math.sin(a) * 0.95, 2.0 + (i % 2) * 0.3), (0.3, 0.3, 0.05), bevel=0.0, rot_z=a)
    for y in (-0.9, 0.9):
        beam("hang_rope", p["oak_dk"], (0.05, y, 2.7), (0.05, y * 0.7, 3.35), thick=0.04)
    beam("hang_rope", p["oak_dk"], (0.05, 0.0, 2.9), (0.05, 0.0, 3.35), thick=0.04)
    # Tensores para estacas e rolos de corda na lama.
    for x, y in ((xs[-1], 1.35), (xs[-1], -1.35), (xs[0], 1.35), (xs[0], -1.35)):
        beam("rig", p["canvas_dk"], (x, y * 0.62, 3.05), (x + (0.35 if x > 0 else -0.35), y * 1.2, 0.2), thick=0.03)
    cyl("rope_coil", p["canvas_dk"], (1.2, -0.6, 0.1), 0.28, 0.14, sides=10, bevel=0.0)
    cyl("rope_coil", p["canvas"], (1.2, -0.6, 0.24), 0.22, 0.1, sides=10, bevel=0.0)
    # Lastro: barris amarrados na base dos arcos.
    for x in (xs[-1] + 0.1, xs[0] - 0.05):
        keg(p, (x, 1.1, 0.1), r=0.2, h=0.44, tone="oak_dk", tap=(x > 0))
        keg(p, (x, -1.1, 0.1), r=0.2, h=0.44, tap=False)
    keg(p, (-0.3, 1.5, 0.1), r=0.17, h=0.38, seal=True)
    stove(p, (-0.2, -1.55, 0.1), chimney=0.5)


def n03N_siege_workshop():
    """Oficina a céu aberto sob zinco torto: o balcão é um barril deitado, a forja acesa no meio e canos usados encostados."""
    p = pal()
    pad(p)
    # Zinco torto cobrindo só o fundo, inclinado nos dois eixos e escorado por postes desiguais; a forja fica a céu aberto.
    roof = box("zinc_roof", p["zinc"], (-1.2, 0, 1.9), (1.2, 3.0, 0.1), bevel=0.0, rot_z=0.06)
    for v in roof.data.vertices:
        v.co.z += 0.35 * (v.co.y / 1.5) + 0.15 * (v.co.x / 0.6)
    for y in (-1.2, -0.6, 0.0, 0.6, 1.2):
        beam("zinc_rib", p["iron"], (-1.75, y, 2.2 + y * 0.2), (-0.65, y + 0.06, 2.12 + y * 0.2), thick=0.07)
    for x, y, h in ((-1.7, -1.35, 2.0), (-1.7, 1.35, 2.4), (-0.7, -1.35, 2.0), (-0.65, 1.35, 2.25)):
        beam("zinc_post", p["oak_dk"], (x, y, 0.1), (x, y, h), thick=0.13)
    box("zinc_patch", p["porc_dk"], (-1.4, 0.2, 2.35), (0.4, 0.5, 0.04), bevel=0.0, rot_z=0.3)
    box("forge", p["brick"], (-0.15, 0, 0.1), (1.0, 1.0, 0.7), bevel=0.04, taper=0.9, taper_y=0.9)
    box("forge_fire", p["flame"], (-0.15, 0, 0.8), (0.6, 0.6, 0.06), bevel=0.0)
    cyl("forge_hood", p["iron_dk"], (-0.15, 0, 0.85), 0.5, 0.5, sides=8, top_radius=0.18, bevel=0.0)
    cyl("forge_stack", p["iron_dk"], (-0.15, 0, 1.3), 0.17, 1.0, sides=8, bevel=0.0)
    cyl("forge_cap", p["soot"], (-0.15, 0, 2.3), 0.22, 0.07, sides=8, bevel=0.0)
    steam(p, (-0.15, 0.02, 2.4), n=3, r=0.12)
    box("anvil", p["iron_dk"], (-1.3, -0.5, 0.1), (0.4, 0.3, 0.3), bevel=0.02)
    box("anvil_top", p["iron"], (-1.3, -0.5, 0.4), (0.55, 0.22, 0.1), bevel=0.0)
    # Barril deitado como bancada, prancha em cima, canos de armas de procedência mista encostados nele.
    keg(p, (0.95, -1.0, 0.1), r=0.42, h=2.0, tone="oak", lying=True)
    box("bench_top", p["plank"], (0.95, 0.0, 0.88), (0.7, 2.0, 0.08), bevel=0.0)
    for i, (dy, tone, th) in enumerate(((-0.9, "soot", 0.1), (-0.6, "iron_dk", 0.08), (0.9, "iron", 0.11))):
        beam("gun_barrel", p[tone], (0.8, dy, 0.96), (0.8 + 0.2 * (i + 1), dy, 0.96), thick=th)
    for i, (x, y, tone) in enumerate(((1.6, 0.5, "soot"), (1.55, 0.8, "iron_dk"), (1.65, 1.1, "iron"), (1.5, -0.3, "soot"))):
        beam("leaning_barrel", p[tone], (x, y, 0.1), (x - 0.35, y + 0.05, 1.25), thick=0.11)
        box("barrel_muzzle", p["brass"], (x - 0.37, y + 0.05, 1.22), (0.14, 0.14, 0.05), bevel=0.0)
    keg(p, (1.5, -1.35, 0.1), r=0.17, h=0.38, seal=True)


# ---------------------------------------------------------------------------------------------------------
# Torres e utilidades
# ---------------------------------------------------------------------------------------------------------


def h07P_steam_tower():
    """Barril alto de aduelas com escada de bambu por fora e plataforma de lona no topo: canhão curto com funil e barris ao pé."""
    p = pal()
    box("pad", p["mud"], (0, 0, 0), (3.0, 3.0, 0.1), bevel=0.03)
    for x, y, w, d in ((1.0, 0.7, 0.7, 0.5), (-0.5, -1.0, 0.8, 0.5)):
        box("film", p["film"], (x, y, 0.1), (w, d, 0.012), bevel=0.0)
    cx = -0.2
    cyl("tw_foot", p["oak_dk"], (cx, 0, 0.1), 1.15, 0.2, sides=12, bevel=0.0)
    cyl("tw_low", p["oak"], (cx, 0, 0.3), 1.0, 1.4, sides=12, top_radius=1.25, bevel=0.0)
    cyl("tw_up", p["oak"], (cx, 0, 1.7), 1.25, 1.4, sides=12, top_radius=0.95, bevel=0.0)
    for z in (0.5, 1.7, 2.9):
        cyl("tw_band", p["iron_dk"], (cx, 0, z), 1.27 if z == 1.7 else 1.05, 0.09, sides=12, bevel=0.0)
    for i in range(6):
        a = i * math.tau / 6 + 0.2
        box("tw_patch", p["oak_dk"], (cx + math.cos(a) * 1.1, math.sin(a) * 1.1, 1.0 + (i % 3) * 0.6), (0.05, 0.28, 0.4), bevel=0.0, rot_z=a)
    # Plataforma de lona e a mureta de ripas.
    cyl("platform", p["canvas"], (cx, 0, 3.1), 1.35, 0.14, sides=12, bevel=0.0)
    cyl("platform_hem", p["canvas_dk"], (cx, 0, 3.1), 1.38, 0.05, sides=12, bevel=0.0)
    for i in range(8):
        a = i * math.tau / 8
        beam("rail_post", p["bamboo"], (cx + math.cos(a) * 1.25, math.sin(a) * 1.25, 3.2), (cx + math.cos(a) * 1.25, math.sin(a) * 1.25, 3.7), thick=0.07)
    for i in range(8):
        a, b = i * math.tau / 8, (i + 1) * math.tau / 8
        beam("rail", p["bamboo_dk"], (cx + math.cos(a) * 1.25, math.sin(a) * 1.25, 3.62), (cx + math.cos(b) * 1.25, math.sin(b) * 1.25, 3.62), thick=0.06)
    # Canhão curto com funil na boca, apontando para a lane e para cima.
    cyl("cannon_base", p["iron_dk"], (cx, 0, 3.24), 0.5, 0.3, sides=8, bevel=0.0)
    beam("cannon", p["soot"], (cx - 0.2, 0, 3.6), (cx + 1.0, 0, 4.15), thick=0.34)
    cyl("funnel", p["iron"], (cx + 1.0, 0, 4.15), 0.15, 0.4, sides=8, top_radius=0.32, bevel=0.0, rot=("Y", math.radians(65)))
    steam(p, (cx - 0.5, -0.4, 3.3), n=2, r=0.1)
    # Escada de bambu escorada na frente e rolo de corda.
    for s in (-1, 1):
        beam("ladder_rail", p["bamboo"], (1.55, s * 0.28, 0.1), (cx + 1.1, s * 0.28, 3.15), thick=0.07)
    for i in range(9):
        t = (i + 0.5) / 9.5
        x = 1.55 + (cx + 1.1 - 1.55) * t
        box("rung", p["bamboo_dk"], (x, 0, 0.1 + 3.05 * t), (0.05, 0.6, 0.05), bevel=0.0)
    cyl("rope_coil", p["canvas_dk"], (1.1, -0.9, 0.1), 0.25, 0.14, sides=10, bevel=0.0)
    # Barris pequenos de estoque ao pé.
    keg(p, (0.95, 0.85, 0.1), r=0.2, h=0.44, seal=True)
    keg(p, (0.6, 1.2, 0.1), r=0.2, h=0.44, tone="oak_dk")
    keg(p, (1.0, 1.3, 0.1), r=0.2, h=0.44, tone="oak_dk")
    keg(p, (-0.2, -1.3, 0.1), r=0.2, h=0.44)
    keg(p, (0.25, -1.35, 0.1), r=0.2, h=0.44, tone="oak_dk", seal=True)


def h07V_gas_chimney():
    """Chaminé de refinaria caseira: pilha de ferro com cintas de porcelain trincada e costuras de cobre, rematada por um globo de vidro com a chama a gás."""
    p = pal()
    box("pad", p["mud"], (0, 0, 0), (2.8, 2.8, 0.1), bevel=0.03)
    for x, y, w, d in ((0.9, 0.7, 0.7, 0.5), (-0.4, -1.0, 0.8, 0.5)):
        box("film", p["film"], (x, y, 0.1), (w, d, 0.012), bevel=0.0)
    box("skid", p["oak_dk"], (0, 0, 0.1), (2.0, 2.0, 0.28), bevel=0.04, taper=0.94, taper_y=0.94)
    cyl("stack_foot", p["iron_dk"], (0, 0, 0.38), 0.85, 0.3, sides=12, top_radius=0.7, bevel=0.0)
    cyl("stack_low", p["iron"], (0, 0, 0.68), 0.7, 1.4, sides=12, top_radius=0.6, bevel=0.0)
    cyl("stack_up", p["iron"], (0, 0, 2.08), 0.6, 1.2, sides=12, top_radius=0.46, bevel=0.0)
    for z, r in ((0.9, 0.7), (1.5, 0.66), (2.15, 0.58), (2.75, 0.5)):
        cyl("porcelain_band", p["porc"], (0, 0, z), r + 0.05, 0.28, sides=12, bevel=0.0)
        box("band_chip", p["porc_dk"], (r * 0.7, r * 0.7, z + 0.05), (0.2, 0.16, 0.18), bevel=0.0, rot_z=0.8)
    for i in range(5):
        a = i * math.tau / 5 + 0.3
        beam("copper_seam", p["copper"], (math.cos(a) * 0.66, math.sin(a) * 0.66, 0.7), (math.cos(a) * 0.5, math.sin(a) * 0.5, 3.2), thick=0.07)
    cyl("stack_neck", p["iron_dk"], (0, 0, 3.28), 0.46, 0.3, sides=10, top_radius=0.32, bevel=0.0)
    # Globo de vidro de boiler com o gás aceso dentro: chama baixa, não mágica.
    cyl("orb_seat", p["iron_dk"], (0, 0, 3.55), 0.42, 0.14, sides=10, bevel=0.0)
    dome("orb", p["flame"], (0, 0, 3.65), 0.5, squash=1.05, sides=10)
    for i in range(6):
        a = i * math.tau / 6
        beam("orb_cage", p["iron_dk"], (math.cos(a) * 0.46, math.sin(a) * 0.46, 3.65), (0, 0, 4.2), thick=0.045)
    cyl("orb_cap", p["soot"], (0, 0, 4.15), 0.14, 0.1, sides=8, bevel=0.0)
    steam(p, (0.0, 0.0, 4.3), n=2, r=0.09)
    # Caldeira de apoio e o tambor de alimentação com mangueira.
    cyl("aux_boiler", p["copper"], (0.2, -1.2, 0.38), 0.34, 0.9, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
    box("aux_fire", p["flame"], (0.95, -1.2, 0.5), (0.04, 0.18, 0.12), bevel=0.0)
    keg(p, (1.1, 0.75, 0.38), r=0.2, h=0.44, tone="oak_dk", seal=True)
    beam("feed_hose", p["soot"], (1.1, 0.75, 0.7), (0.65, 0.3, 0.9), thick=0.05)


def h07R_cable_mast():
    """Mastro de bambu com pipa de ferro e lona no topo, haste de cobre descendo até o barril de óleo aterrado."""
    p = pal()
    box("pad", p["mud"], (0, 0, 0), (3.0, 3.0, 0.1), bevel=0.03)
    for x, y, w, d in ((0.9, 0.6, 0.9, 0.6), (-0.6, -1.0, 0.8, 0.5)):
        box("film", p["film"], (x, y, 0.1), (w, d, 0.012), bevel=0.0)
    cx = -0.35
    box("mast_foot", p["oak_dk"], (cx, 0, 0.1), (1.3, 1.3, 0.3), bevel=0.03, taper=0.85, taper_y=0.85)
    cyl("mast", p["bamboo"], (cx, 0, 0.4), 0.2, 3.1, sides=8, top_radius=0.12, bevel=0.0)
    for z in (0.9, 1.6, 2.3, 3.0):
        cyl("mast_node", p["bamboo_dk"], (cx, 0, z), 0.22 - z * 0.025, 0.08, sides=8, bevel=0.0)
    # Travessa com isoladores de porcelain e a pipa em losango (moldura de ferro, pano de lona remendada).
    beam("crossbar", p["oak_dk"], (cx, -0.8, 2.6), (cx, 0.8, 2.6), thick=0.1)
    for y in (-0.8, 0.8):
        cyl("insulator", p["porc"], (cx, y, 2.65), 0.08, 0.22, sides=6, bevel=0.0)
    kite = cyl("kite", p["canvas"], (cx + 0.15, 0, 3.0), 0.6, 0.07, sides=4, bevel=0.0, rot=("Y", math.radians(90)))
    for v in kite.data.vertices:
        v.co.z *= 1.15
    cyl("kite_patch", p["glaze"], (cx + 0.2, 0.0, 3.0), 0.3, 0.05, sides=4, bevel=0.0, rot=("Y", math.radians(90)))
    beam("kite_spar_v", p["iron_dk"], (cx + 0.25, 0, 3.0 - 0.7), (cx + 0.25, 0, 3.0 + 0.7), thick=0.06)
    beam("kite_spar_h", p["iron_dk"], (cx + 0.25, -0.6, 3.0), (cx + 0.25, 0.6, 3.0), thick=0.06)
    cyl("tip_cap", p["copper"], (cx, 0, 3.5), 0.08, 0.5, sides=6, top_radius=0.02, bevel=0.0)
    # Haste de cobre descendo pela frente do mastro até o barril aterrado, com cabo no chão.
    beam("rod", p["copper"], (cx + 0.24, 0, 2.6), (cx + 0.24, 0, 0.55), thick=0.06)
    beam("cable", p["copper"], (cx + 0.24, 0, 0.5), (0.95, 0.3, 0.55), thick=0.06)
    keg(p, (1.1, 0.3, 0.1), r=0.34, h=0.7, tone="oak_dk", tap=True)
    cyl("keg_plug", p["copper"], (1.1, 0.3, 0.8), 0.1, 0.1, sides=6, bevel=0.0)
    beam("ground_wire", p["copper"], (1.1, 0.3, 0.12), (1.5, 0.9, 0.12), thick=0.04)
    cyl("ground_stake", p["copper"], (1.5, 0.9, 0.1), 0.05, 0.4, sides=6, bevel=0.0)
    # Estais de corda para estacas.
    for sx, sy in ((1, 1), (1, -1), (-1, 0)):
        beam("guy", p["canvas_dk"], (cx, 0, 2.4), (cx + sx * 1.15, sy * 1.15, 0.12), thick=0.03)
        cyl("guy_stake", p["oak_dk"], (cx + sx * 1.15, sy * 1.15, 0.1), 0.06, 0.25, sides=6, bevel=0.0)
    keg(p, (0.9, -1.0, 0.1), r=0.17, h=0.38, seal=True)


def h07T_withering_hall():
    """Casa de penhores com forja: galpão baixo de telhado de uma água, vitrine de porcelain na frente com o tanque confiscado e a fornalha fumegando atrás."""
    p = pal()
    pad(p)
    cx = -0.5
    cx = -0.75
    box("hall_floor", p["plank"], (cx, 0, 0.1), (2.0, 3.0, 0.14), bevel=0.02)
    box("hall", p["oak"], (cx - 0.1, 0, 0.24), (1.7, 2.7, 1.2), bevel=0.03)
    for z in (0.55, 1.0):
        box("hall_band", p["oak_dk"], (cx - 0.1, 0, z), (1.74, 2.74, 0.06), bevel=0.0)
    roof = box("hall_roof", p["iron"], (cx - 0.1, 0, 1.46), (2.0, 3.0, 0.14), bevel=0.0)
    for v in roof.data.vertices:
        v.co.z += 0.5 * (0.5 - (v.co.x + 1.0) / 2.0) * 0.9
    box("roof_edge", p["porc"], (cx + 0.9, 0, 1.5), (0.1, 3.04, 0.12), bevel=0.0)
    box("door", p["soot"], (cx + 0.75, -0.9, 0.24), (0.1, 0.55, 0.9), bevel=0.0)
    # Vitrine de porcelain na frente: cabine aberta no alto, o tanque de combustível vermelho com a marca raspada dentro.
    box("case_base", p["porc"], (1.05, 0.35, 0.1), (0.8, 1.5, 0.4), bevel=0.03)
    for sy in (-1, 1):
        for sx in (-1, 1):
            beam("case_post", p["glaze_dk"], (1.05 + sx * 0.35, 0.35 + sy * 0.68, 0.5), (1.05 + sx * 0.35, 0.35 + sy * 0.68, 1.1), thick=0.07)
    box("case_top", p["glaze"], (1.05, 0.35, 1.1), (0.88, 1.56, 0.08), bevel=0.0)
    cyl("fuel_tank", p["red"], (1.05, 0.0, 0.62), 0.22, 0.7, sides=8, bevel=0.0, rot=("X", math.radians(90)))
    cyl("fuel_tank2", p["canvas_dk"], (1.0, 0.65, 0.5), 0.13, 0.35, sides=8, top_radius=0.1, bevel=0.0)
    box("scratch", p["porc_dk"], (1.05, 0.35, 0.62), (0.3, 0.3, 0.02), bevel=0.0)
    # Moedas no balcão e a balança.
    coin_stack(p, (1.4, -0.7, 0.1), n=4)
    coin_stack(p, (1.55, -0.55, 0.1), n=2)
    box("scale_beam", p["brass"], (1.45, -1.1, 0.7), (0.05, 0.4, 0.04), bevel=0.0)
    beam("scale_post", p["brass"], (1.45, -1.1, 0.1), (1.45, -1.1, 0.7), thick=0.05)
    # Placa de penhorista: três esferas de latão num braço.
    beam("sign_arm", p["iron_dk"], (cx + 0.9, -0.2, 1.1), (cx + 1.3, -0.2, 1.8), thick=0.06)
    for i, (dx, dz) in enumerate(((0.0, 0.0), (0.22, 0.2), (-0.18, 0.22))):
        dome("pawn_ball", p["brass"], (cx + 1.35 + dx, -0.2, 1.72 + dz), 0.17, squash=1.0, sides=8)
    # Fornalha atrás, a chaminé alta com fumaça grossa e baixa.
    box("furnace", p["brick_dk"], (cx - 0.5, 0.7, 1.55), (0.8, 0.8, 0.5), bevel=0.03)
    cyl("furnace_stack", p["iron"], (cx - 0.5, 0.7, 2.0), 0.24, 1.0, sides=8, top_radius=0.2, bevel=0.0)
    cyl("furnace_cap", p["soot"], (cx - 0.5, 0.7, 3.0), 0.27, 0.07, sides=8, bevel=0.0)
    steam(p, (cx - 0.5, 0.7, 3.1), n=3, r=0.17)
    box("furnace_mouth", p["flame"], (cx - 0.08, 0.7, 1.65), (0.04, 0.3, 0.2), bevel=0.0)
    keg(p, (1.55, 1.4, 0.1), r=0.17, h=0.38, seal=True)


BUILDINGS = {
    "n03F": n03F_brew_hut,
    "n03K": n03K_fighting_tavern,
    "n03P": n03P_temple,
    "n03D": n03D_bamboo_dojo,
    "n03S": n03S_sagepaw_sanctum,
    "n03L": n03L_jade_shrine,
    "n03H": n03H_residue_distillery,
    "n03Q": n03Q_cloud_hangar,
    "n03N": n03N_siege_workshop,
    "h07P": h07P_steam_tower,
    "h07V": h07V_gas_chimney,
    "h07R": h07R_cable_mast,
    "h07T": h07T_withering_hall,
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
