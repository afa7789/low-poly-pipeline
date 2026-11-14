"""Prédios da raça Elemental modelados por script (redesenho de reports/design/race-elemental.md): um GLB por prédio.

Uso:
    blender -b --factory-startup --python tools/blender/buildings_elemental.py -- <id|all> [--out DIR] [--render DIR]

Primitivos do Subsolo: carvão incandescente e basalto (a massa), ferrugem de sonda engolida pela rocha, cinza
estratigráfica, vidro de quartzo só dentro de fraturas e UM acento, o Âmbar de Fratura, sempre dentro de uma
ruptura (fenda, junta, sumidouro). Nada é emissivo por inteiro, nada é cristal limpo. Todo prédio carrega uma
peça de extração à vista (válvula de poço, anel de revestimento numerado, dormente de trilho, tubo de sondagem,
válvula de gás, poste de aterramento, dínamo queimado, broca). Cada produtor recorta a boca como o negativo da
unidade que gera. Pegada ~3,5 x 3,5 centrada na origem, a frente virada para +x; o jogo normaliza o tamanho,
põe o prédio no plinto do time e desenha a bandeira.
"""

import math
import os
import sys

from mathutils import Euler, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_paths  # noqa: E402
import map_castles as kit
from map_castles import beam, box, cyl, dome, mat, prism

# ponytail: cores do doc com o valor subido (a luz do jogo escurece); o carvão continua o bloco mais escuro.


def pal():
    return {
        "char": mat("char", 0x6E5D52),
        "char_dk": mat("char_dark", 0x453A33),
        "basalt": mat("basalt", 0x838A8E),
        "basalt_dk": mat("basalt_dark", 0x5C6267),
        "rust": mat("rig_rust", 0xB8744C),
        "ash": mat("ash", 0xBDB7A8),
        "ash_dk": mat("ash_dark", 0x948E81),
        "glass": mat("glass", 0xAAC8D0),
        "smoke": mat("smoked_glass", 0x587480),
        "water": mat("dark_water", 0x2F5360),
        "steel": mat("burnt_steel", 0x50555B),
        "mud": mat("mud", 0x4A3F36),
        "oil": mat("oil", 0x1B1717),
        "ember": mat("ember", 0xFF6A1E, emit=2.0),
    }


# ---------------------------------------------------------------------------------------------------------
# Peças da raça
# ---------------------------------------------------------------------------------------------------------


def pad(p, size=(3.5, 3.5)):
    """Chão de lama do tamanho do conteúdo: laje sobrando encolhe o prédio na tela."""
    box("pad", p["mud"], (0, 0, 0), (size[0], size[1], 0.1), bevel=0.03)


def tbox(name, material, center, size, rot=(0.0, 0.0, 0.0), bevel=0.03, taper=1.0, taper_y=None):
    """Caixa girada em torno do centro da sua base (box com Euler XYZ)."""
    ob = box(name, material, (0, 0, 0), size, bevel=bevel, taper=taper, taper_y=taper_y)
    ob.rotation_euler = rot
    ob.location = center
    return ob


def at(origin, rot, local):
    """Ponto no referencial girado de uma laje: origem + R @ local."""
    return tuple(Vector(origin) + Euler(rot).to_matrix() @ Vector(local))


def rock(p, tone, pos, radius, height, sides=6, top=0.7, spin=0.0):
    """Bloco facetado: tronco de pirâmide de poucas faces."""
    return cyl("rock", p[tone], pos, radius, height, sides=sides, top_radius=radius * top, bevel=0.04, rot=("Z", spin))


def gem(p, tone, pos, radius, height, sides=6):
    """Quartzo: dois cones colados pela base (lapidado como uma agulha larga)."""
    x, y, z = pos
    cyl("gem_low", p[tone], (x, y, z), 1e-3, height * 0.4, sides=sides, top_radius=radius, bevel=0.0)
    cyl("gem_high", p[tone], (x, y, z + height * 0.4), radius, height * 0.6, sides=sides, top_radius=1e-3, bevel=0.0)


def needle_down(p, tone, pos, height, radius=0.06):
    """Agulha pendurada: ponta embaixo, base presa em pos.z + height."""
    cyl("needle", p[tone], pos, 1e-3, height, sides=5, top_radius=radius, bevel=0.0)


def loop(p, tone, center, radius, thick, n=10, plane="yz", wobble=0.0, a0=0.0, span=math.tau):
    """Anel de vigas (aro de revestimento, arco, halo). wobble amassa o raio, como aço flambado."""
    cx, cy, cz = center
    closed = abs(span - math.tau) < 1e-6
    pts = []
    for i in range(n + (0 if closed else 1)):
        a = a0 + span * i / n
        r = radius * (1.0 + wobble * ((i * 5) % 3 - 1))
        u, v = math.cos(a) * r, math.sin(a) * r
        pts.append({"yz": (cx, cy + u, cz + v), "xz": (cx + u, cy, cz + v), "xy": (cx + u, cy + v, cz)}[plane])
    for i in range(len(pts) - (0 if closed else 1)):
        beam("loop", p[tone], pts[i], pts[(i + 1) % len(pts)], thick=thick)


def chain(p, a, b, tone="steel", links=7, thick=0.07):
    """Corrente reta entre dois pontos: elos curtos de espessura alternada."""
    a, b = Vector(a), Vector(b)
    for i in range(links):
        t0, t1 = i / links, (i + 0.62) / links
        beam("link", p[tone], a.lerp(b, t0), a.lerp(b, t1), thick=thick * (1.0 if i % 2 else 0.7))


def seam(p, center, size, rot_z=0.0):
    """A fratura: faixa de âmbar rente à pedra. É o único lugar onde a energia aparece."""
    return box("seam", p["ember"], center, size, bevel=0.0, rot_z=rot_z)


def strata(p, pos, size, layers, tones=("char", "basalt_dk"), rot_z=0.0, shrink=0.0):
    """Pilha de estratos deslocados: camadas desalinhadas ao longo do maior eixo, como lascas puxadas."""
    x, y, z = pos
    sx, sy, sz = size
    lh = sz / layers
    c, s = math.cos(rot_z), math.sin(rot_z)
    for i in range(layers):
        jitter = 0.07 * ((i * 7) % 3 - 1)
        k = 1.0 - shrink * i / layers
        box("stratum", p[tones[i % len(tones)]], (x + c * jitter, y + s * jitter, z + i * lh), (sx * k, sy * k, lh * 0.97), bevel=0.03, rot_z=rot_z)


def obelisk(p, tone, pos, w, d, h, rot=(0.0, 0.0, 0.0), tip=True):
    """Lasca de obelisco: fuste afilando e pirâmide quebrada no topo."""
    tbox("obelisk", p[tone], pos, (w, d, h), rot, bevel=0.02, taper=0.62, taper_y=0.62)
    if tip:
        top = at(pos, rot, (0, 0, h))
        tbox("obelisk_tip", p[tone], top, (w * 0.62, d * 0.62, w * 0.5), rot, bevel=0.0, taper=0.12, taper_y=0.12)


def bit(p, pos, height=0.9, radius=0.26, up=False, rot=None):
    """Broca de cones rolantes presa na pedra (a ponta cravada, o fuste para cima). up=True vira agulha de topo."""
    x, y, z = pos
    nose = height * 0.5
    if up:
        cyl("bit_cone", p["steel"], (x, y, z), radius, nose, sides=8, top_radius=1e-3, bevel=0.0)
        cyl("bit_neck", p["rust"], (x, y, z - height * 0.25), radius * 0.7, height * 0.25, sides=8, bevel=0.0)
        for k in range(3):
            box("bit_tooth", p["rust"], (x + math.cos(k * 2.1) * radius * 0.5, y + math.sin(k * 2.1) * radius * 0.5, z + nose * 0.2), (0.07, 0.07, 0.12), bevel=0.0)
        return
    cyl("bit_cone", p["steel"], (x, y, z), 1e-3, nose, sides=8, top_radius=radius, bevel=0.0, rot=rot)
    cyl("bit_neck", p["rust"], (x, y, z + nose), radius, height * 0.18, sides=8, bevel=0.0, rot=rot)
    cyl("bit_shank", p["steel"], (x, y, z + nose + height * 0.18), radius * 0.55, height * 0.32, sides=8, bevel=0.0, rot=rot)


def valve(p, pos, s=1.0):
    """Cabeça de poço: corpo ferrugem, flange, braço lateral e volante (a válvula presa aberta)."""
    x, y, z = pos
    cyl("valve_body", p["rust"], pos, 0.13 * s, 0.5 * s, sides=8, bevel=0.0)
    cyl("valve_flange", p["steel"], (x, y, z + 0.1 * s), 0.2 * s, 0.07 * s, sides=8, bevel=0.0)
    box("valve_stem", p["steel"], (x, y, z + 0.5 * s), (0.05 * s, 0.05 * s, 0.18 * s), bevel=0.0)
    cyl("valve_wheel", p["rust"], (x, y, z + 0.66 * s), 0.19 * s, 0.04 * s, sides=8, bevel=0.0)
    beam("valve_arm", p["steel"], (x, y, z + 0.28 * s), (x + 0.4 * s, y, z + 0.28 * s), thick=0.1 * s)
    cyl("valve_arm_cap", p["rust"], (x + 0.4 * s, y, z + 0.2 * s), 0.1 * s, 0.16 * s, sides=8, bevel=0.0)


def casing(p, pos, radius=0.5, facing="yz", number=True):
    """Anel de revestimento flambado, de pé, com a placa do número do poço."""
    x, y, z = pos
    loop(p, "rust", (x, y, z + radius), radius, 0.1, n=9, plane=facing, wobble=0.07)
    if number:
        box("well_plate", p["ash"], (x + 0.05, y, z + 0.02), (0.06, 0.34, 0.2), bevel=0.0)
        for k in range(3):
            box("well_digit", p["steel"], (x + 0.09, y - 0.1 + k * 0.1, z + 0.06), (0.02, 0.05, 0.11), bevel=0.0)


def sleeper(p, pos, rot_z=0.0, length=1.5):
    """Dormente de trilho enterrado e quebrado, com dois pedaços de trilho."""
    x, y, z = pos
    c, s = math.cos(rot_z), math.sin(rot_z)
    box("sleeper", p["char_dk"], pos, (0.3, length, 0.13), bevel=0.02, rot_z=rot_z)
    for k in (-0.45, 0.45):
        box("rail", p["steel"], (x - s * k, y + c * k, z + 0.13), (0.9, 0.07, 0.07), bevel=0.0, rot_z=rot_z)


def post(p, pos, height=0.85):
    """Poste de aterramento cravado na lama, com a abraçadeira de ferrugem."""
    x, y, z = pos
    cyl("ground_post", p["steel"], pos, 0.05, height, sides=6, bevel=0.0)
    cyl("ground_clamp", p["rust"], (x, y, z + height * 0.55), 0.09, 0.12, sides=6, bevel=0.0)
    box("ground_plate", p["steel"], (x, y, z), (0.3, 0.3, 0.04), bevel=0.0)


def dynamo(p, pos, burnt=True):
    """Dínamo de sonda: caixa de aço com o rotor deitado; queimado = topo de carvão."""
    x, y, z = pos
    box("dynamo", p["steel"], pos, (0.55, 0.42, 0.34), bevel=0.02)
    cyl("dynamo_rotor", p["rust"], (x + 0.1, y, z + 0.34), 0.15, 0.4, sides=8, bevel=0.0, rot=("X", math.radians(90)))
    if burnt:
        box("dynamo_scorch", p["char_dk"], (x - 0.1, y, z + 0.34), (0.3, 0.38, 0.05), bevel=0.0)


def gas_valve(p, pos):
    """Válvula de gás com tubulação: cano que sai do chão, vira e termina em volante."""
    x, y, z = pos
    cyl("gas_pipe", p["steel"], pos, 0.1, 0.7, sides=8, bevel=0.0)
    beam("gas_run", p["steel"], (x, y, z + 0.6), (x - 0.7, y, z + 0.6), thick=0.14)
    cyl("gas_drop", p["steel"], (x - 0.7, y, z), 0.1, 0.6, sides=8, bevel=0.0)
    cyl("gas_wheel", p["rust"], (x, y, z + 0.72), 0.2, 0.05, sides=8, bevel=0.0)
    cyl("gas_flange", p["rust"], (x - 0.35, y, z + 0.6 - 0.1), 0.12, 0.2, sides=8, bevel=0.0)


def cloud(p, pos, size=1.0, tone="ash"):
    """Nuvem comprimida: três cúpulas achatadas de cinza."""
    x, y, z = pos
    dome("cloud", p[tone], (x, y, z), 0.5 * size, squash=0.75, sides=9)
    dome("cloud", p[tone], (x + 0.4 * size, y + 0.15 * size, z), 0.36 * size, squash=0.8, sides=8)
    dome("cloud", p["ash_dk"], (x - 0.32 * size, y - 0.2 * size, z), 0.32 * size, squash=0.8, sides=8)


def horseshoe(p, radius=1.35, height=0.8, gap=0.7, thick=0.7, tone="char", z=0.1):
    """Ferradura de basalto de blocos: a contenção que cresce da Trapped Gale ao Memorial. gap = abertura em +x (rad)."""
    n = 11
    a0 = gap / 2
    span = math.tau - gap
    for i in range(n):
        a = a0 + span * (i + 0.5) / n
        arc = span / n * radius * 1.05
        c = (math.cos(a) * radius, math.sin(a) * radius, z)
        box("horseshoe", p[tone if i % 2 else "basalt_dk"], c, (thick, arc, height * (1.0 - 0.08 * (i % 3))), bevel=0.03, taper=0.82, taper_y=1.0, rot_z=a)


# ---------------------------------------------------------------------------------------------------------
# Terra: Rock Pile -> Greater Fissure
# ---------------------------------------------------------------------------------------------------------


def h040_rock_pile():
    """Pilha de três blocos apertados por uma fenda laranja, com o vazio em cunha do h034 cortado na frente."""
    p = pal()
    pad(p)
    tbox("block_a", p["char"], (-0.75, -0.75, 0.1), (1.6, 1.4, 1.8), (0.04, -0.06, 0.3), bevel=0.05, taper=0.6, taper_y=0.7)
    tbox("block_b", p["basalt_dk"], (-0.65, 0.9, 0.1), (1.4, 1.3, 1.35), (-0.05, 0.05, -0.25), bevel=0.05, taper=0.62, taper_y=0.7)
    tbox("block_c", p["char"], (0.7, 0.05, 0.1), (1.3, 1.5, 1.0), (0.0, 0.0, 0.12), bevel=0.05, taper=0.7, taper_y=0.75)
    # A fenda de âmbar entre os blocos, de ponta a ponta, e o vazio em cunha na face.
    seam(p, (0.0, -0.6, 0.1), (1.0, 0.13, 0.06), rot_z=0.5)
    seam(p, (0.0, 0.62, 0.1), (1.0, 0.13, 0.06), rot_z=-0.5)
    seam(p, (-0.2, 0.0, 0.1), (0.12, 0.8, 0.06))
    seam(p, (0.72, 0.05, 1.08), (0.9, 0.1, 0.04), rot_z=0.12)
    prism("wedge_void", p["oil"], (1.2, 0.05, 0.2), (0.5, 0.7, 0.55), ridge=1.0, bevel=0.0)
    obelisk(p, "ash_dk", (-1.25, 0.1, 0.1), 0.34, 0.3, 1.9, rot=(0.0, 0.1, 0.0))
    bit(p, (0.85, -1.0, 0.1), height=0.8, radius=0.2, rot=("Y", math.radians(-35)))
    rock(p, "basalt", (1.3, 1.05, 0.1), 0.32, 0.35, sides=5)
    valve(p, (0.3, 1.35, 0.1), s=0.8)


def h041_greater_fissure():
    """Ravina em V de duas paredes de estratos altas, câmara de três placas ao fundo, dormente na boca."""
    p = pal()
    pad(p)
    for s in (-1, 1):
        strata(p, (-0.2, s * 1.1, 0.1), (2.7, 0.75, 3.1), 8, rot_z=-s * 0.3, shrink=0.2)
    box("chamber_floor", p["char_dk"], (-0.2, 0, 0.1), (2.1, 1.2, 0.08), bevel=0.0)
    seam(p, (0.1, 0, 0.18), (1.7, 0.45, 0.04))
    # Câmara de três placas empilhadas ao fundo (o negativo do h03N) e o dormente de trilho cruzando a boca.
    for i, (w, h) in enumerate(((1.15, 0.6), (0.85, 1.1), (0.55, 1.6))):
        box("chamber_plate", p["basalt_dk" if i % 2 else "char"], (-1.1, 0, 0.1), (0.5 + 0.05 * (2 - i), w, h), bevel=0.03)
    sleeper(p, (1.45, 0, 0.1), rot_z=0.12, length=1.9)
    # Placa de obelisco pendurada por correntes de uma viga entre as paredes, sobre o âmbar fundo.
    beam("gantry", p["steel"], (-0.1, -0.95, 3.1), (-0.1, 0.95, 3.1), thick=0.15)
    for dy in (-0.25, 0.25):
        chain(p, (-0.1, dy, 3.05), (-0.1, dy, 2.25), links=4)
    tbox("hanging_plate", p["ash_dk"], (-0.1, 0, 1.55), (0.14, 0.8, 0.75), bevel=0.02, taper=0.6, taper_y=1.0)
    valve(p, (1.3, -1.25, 0.1), s=0.8)
    bit(p, (1.45, 1.2, 0.1), height=0.6, radius=0.16, rot=("X", math.radians(40)))


# ---------------------------------------------------------------------------------------------------------
# Fogo: Altar of Fire -> Altar of Blaze
# ---------------------------------------------------------------------------------------------------------


def altar_slab(p, wide):
    """Laje de basalto rachada por uma lágrima de âmbar, com os dois sulcos de canhão do h02Z."""
    box("slab_low", p["basalt_dk"], (0, 0, 0.1), (3.3 if wide else 3.1, 3.2 if wide else 3.0, 0.4), bevel=0.04, taper=0.94, taper_y=0.94)
    box("slab_top", p["char"], (-0.1, 0, 0.5), (2.9, 2.8, 0.3), bevel=0.04, taper=0.94, taper_y=0.94)
    for s in (-1, 1):
        box("cannon_groove", p["oil"], (0.55, s * 0.62, 0.8), (1.4, 0.34, 0.03), bevel=0.0)
    seam(p, (-0.3, 0, 0.8), (0.14, 2.3, 0.04))
    seam(p, (0.2, 0.4, 0.8), (0.9, 0.12, 0.04), rot_z=0.5)
    seam(p, (0.3, -0.5, 0.8), (0.9, 0.12, 0.04), rot_z=-0.4)


def h045_altar_of_fire():
    """Braseiro geológico: laje baixa rachada, anel de revestimento numerado na boca, duas escórias de vidro ao fundo."""
    p = pal()
    pad(p)
    altar_slab(p, wide=False)
    for s in (-1, 1):
        beam("cannon_arm", p["basalt"], (-0.2, s * 0.62, 0.95), (1.3, s * 0.62, 1.25), thick=0.32)
        beam("cannon_mouth", p["oil"], (1.3, s * 0.62, 1.25), (1.4, s * 0.62, 1.27), thick=0.2)
    casing(p, (1.45, 0, 0.8), radius=0.5)
    for y in (-0.8, 0.7):
        gem(p, "smoke", (-1.05, y, 0.8), 0.24, 0.9, sides=5)
    seam(p, (-1.05, 0, 0.8), (0.1, 1.5, 0.04))
    valve(p, (0.6, 1.35, 0.1), s=0.8)
    rock(p, "char_dk", (1.3, -1.25, 0.1), 0.3, 0.3, sides=5)


def h046_altar_of_blaze():
    """Altar-fissura largo: duas placas de carvão em V sobre o sumidouro de brasa, arco de vidro e a broca-ídolo."""
    p = pal()
    pad(p)
    altar_slab(p, wide=True)
    # Duas placas abertas em V, cada uma inclinada para fora a partir da dobradiça central.
    for s in (-1, 1):
        tbox("v_plate", p["char"], (-0.2, s * 0.5, 0.8), (1.4, 0.34, 2.1), (s * -0.42, 0.0, 0.0), bevel=0.04, taper=0.8, taper_y=1.0)
        tbox("v_plate_cap", p["basalt_dk"], at((-0.2, s * 0.5, 0.8), (s * -0.42, 0.0, 0.0), (0, 0, 2.1)), (1.2, 0.3, 0.2), (s * -0.42, 0.0, 0.0), bevel=0.02)
    seam(p, (-0.2, 0, 0.8), (1.1, 0.5, 0.05))
    seam(p, (-0.2, 0, 0.85), (0.6, 0.18, 1.0))
    loop(p, "smoke", (1.25, 0, 0.8), 1.15, 0.12, n=8, plane="yz", a0=0.0, span=math.pi)
    bit(p, (-1.2, 0, 0.8), height=1.3, radius=0.3)
    valve(p, (1.35, 1.2, 0.1), s=0.9)
    gem(p, "smoke", (-1.2, 1.1, 0.8), 0.2, 0.7, sides=5)


# ---------------------------------------------------------------------------------------------------------
# Conjuração: Core Sample Archive -> Rain | Meteor Shower
# ---------------------------------------------------------------------------------------------------------

SLAB_ROLL = 0.5


def archive_slabs(p, roll=SLAB_ROLL, pages=True, sides=(-1, 1)):
    """Duas lajes de xisto abertas em V baixo; as camadas geológicas fazem de páginas. Devolve as origens."""
    origins = []
    for s in sides:
        origin, rot = (0.0, s * 0.8, 0.5), (s * roll, 0.0, 0.0)
        tbox("shale_slab", p["basalt_dk"], origin, (2.7, 1.55, 0.3), rot, bevel=0.04)
        if pages:
            for i in range(5):
                loc = at(origin, rot, (0.0, -0.58 + i * 0.28, 0.3))
                tbox("shale_layer", p["ash_dk" if i % 2 else "char"], loc, (2.5, 0.2, 0.06), rot, bevel=0.0)
        origins.append((origin, rot))
    return origins


def h05Z_archive():
    """Arquivo de testemunhos: duas lajes de xisto em V com camadas por páginas, meteorito acorrentado e nuvem presa."""
    p = pal()
    pad(p)
    (o_l, r_l), (o_r, r_r) = archive_slabs(p)
    seam(p, (0, 0, 0.18), (2.5, 0.1, 0.05))
    # Meteorito acorrentado sobre a laje direita (y+), nuvem presa numa gaiola sobre a esquerda.
    rock(p, "char_dk", at(o_r, r_r, (-0.5, 0.2, 0.3)), 0.5, 0.6, sides=6, top=0.6)
    chain(p, at(o_r, r_r, (-0.5, 0.2, 0.55)), (-0.6, 1.5, 0.28), links=5)
    cloud(p, at(o_l, r_l, (0.4, 0.0, 0.7)), size=0.8)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        loc = at(o_l, r_l, (0.4 + sx * 0.5, sy * 0.35, 0.3))
        cyl("cage_post", p["steel"], loc, 0.03, 0.7, sides=5, bevel=0.0)
    valve(p, (1.45, 0.0, 0.1), s=0.8)


def h06F_elemental_rain():
    """Colapso de veio: o arco baixo por cima das lajes, nuvem acorrentada pingando e sete agulhas minerais."""
    p = pal()
    pad(p)
    archive_slabs(p, roll=0.2, pages=False)
    for s in (-1, 1):
        box("arch_pier", p["char"], (0.3, s * 1.5, 0.1), (0.5, 0.5, 1.2), bevel=0.04)
    loop(p, "char", (0.3, 0, 1.2), 1.5, 0.42, n=8, plane="yz", a0=0.0, span=math.pi)
    chain(p, (0.3, 0, 2.6), (0.3, 0, 2.25), links=3)
    cloud(p, (0.3, 0, 1.95), size=1.0, tone="ash_dk")
    for i, (dy, h) in enumerate(((-0.7, 0.55), (-0.45, 0.85), (-0.2, 0.65), (0.0, 1.0), (0.2, 0.7), (0.45, 0.9), (0.7, 0.5))):
        needle_down(p, "glass", (0.3 + 0.15 * ((i % 3) - 1), dy, 1.95 - h), h)
    seam(p, (0.3, 0, 0.18), (0.14, 1.8, 0.05))
    box("pipe_drop", p["steel"], (1.4, 0.0, 0.1), (0.14, 0.14, 0.9), bevel=0.0)
    valve(p, (1.35, -1.2, 0.1), s=0.8)


def h06E_meteor_shower():
    """Detrito de perfuração em chamas: a laje de lançamento erguida em diagonal contra o céu, meteorito acorrentado."""
    p = pal()
    pad(p)
    archive_slabs(p, roll=0.3, pages=False, sides=(-1,))
    plate_rot = (0.85, 0.0, 0.0)
    plate = (0.0, 0.25, 1.25)
    tbox("launch_plate", p["char"], plate, (1.7, 3.0, 0.3), plate_rot, bevel=0.04)
    for k, dy in enumerate((0.1, 0.55, 1.0)):
        loc = at(plate, plate_rot, (0.0, dy, 0.3))
        tbox("launch_scar", p["ember"], loc, (1.0, 0.1, 0.03), plate_rot, bevel=0.0)
    for s in (-1, 1):
        beam("sling_strut", p["steel"], (s * 0.7, 0.9, 0.1), at(plate, plate_rot, (s * 0.7, 1.2, 0.0)), thick=0.14)
    rock(p, "char_dk", at(plate, plate_rot, (0.0, -0.5, 0.45)), 0.5, 0.6, sides=6, top=0.6)
    chain(p, at(plate, plate_rot, (0.0, -0.5, 0.7)), at(plate, plate_rot, (0.0, 0.4, 0.45)), links=5)
    for sx, sy, h in ((1.2, 1.2, 0.35), (1.1, -1.25, 0.25), (1.6, 0.2, 0.2)):
        rock(p, "char_dk", (sx, sy, 0.1), 0.2, h, sides=5)
    bit(p, (1.35, -0.55, 0.1), height=0.7, radius=0.16, rot=("X", math.radians(-30)))
    seam(p, (1.2, 1.2, 0.1), (0.3, 0.1, 0.05))


# ---------------------------------------------------------------------------------------------------------
# Torres: Discharge Tower e Elemental Guard Tower
# ---------------------------------------------------------------------------------------------------------


def h076_discharge_tower():
    """Haste de fulgurito rastelada a ~30 graus, bifurcada só no terço de cima, sobre um pedestal esmagado e largo."""
    p = pal()
    pad(p, (2.8, 2.8))
    for i, (w, h) in enumerate(((2.5, 0.35), (2.1, 0.35), (1.6, 0.3))):
        box("pedestal", p["char" if i % 2 == 0 else "basalt_dk"], (-0.1, 0, 0.1 + 0.35 * i), (w, w * 0.96, h), bevel=0.04, rot_z=0.2 * i)
    tilt = math.radians(30)
    lean = Vector((0.3, 0.95, 0.0)).normalized()
    axis = lean * math.sin(tilt) + Vector((0, 0, math.cos(tilt)))
    base = Vector((-0.2, -0.9, 1.0))
    fork = base + axis * 2.1
    tip = base + axis * 3.5
    beam("rod_low", p["basalt"], base, fork, thick=0.42)
    beam("rod_up", p["basalt"], fork, tip, thick=0.28)
    kit.begin_part("anim_crystal")
    kit.spike(p["glass"], tuple(tip), height=0.45, radius=0.12)
    for s in (-1, 1):
        end = fork + Vector((0.55 * s, 0.35, 1.05))
        beam("tine", p["basalt"], fork, end, thick=0.2)
        kit.spike(p["glass"], tuple(end), height=0.35, radius=0.09)
    gem(p, "glass", tuple(fork + Vector((0.0, 0.2, 0.45))), 0.3, 0.7)
    kit.end_part()
    seam(p, (-0.1, -0.6, 1.0), (0.1, 0.1, 0.8))
    # Corrente de aterramento descendo da haste ao dínamo queimado.
    chain(p, tuple(base + Vector((0.3, 0.1, 0.5))), (0.75, 0.0, 0.55), links=6)
    dynamo(p, (0.75, -0.2, 0.1))
    post(p, (1.0, 0.8, 0.1))


def h061_guard_tower():
    """Torre-punho baixa e grossa de três estratos que alargam para cima, pedregulho em berço de vidro e calha."""
    p = pal()
    pad(p, (2.8, 2.8))
    for i, (w, d, dx, tone) in enumerate(((2.2, 2.2, 0.0, "char"), (2.45, 2.35, 0.1, "basalt_dk"), (2.65, 2.5, -0.1, "char"))):
        box("stratum_big", p[tone], (dx, 0, 0.1 + 0.85 * i), (w, d, 0.85), bevel=0.04, taper=0.92, taper_y=0.92, rot_z=0.1 * (i - 1))
    seam(p, (1.18, 0.3, 1.05), (0.06, 0.9, 0.06))
    seam(p, (1.28, -0.4, 1.95), (0.06, 0.7, 0.06))
    # Berço de quatro garras de vidro segurando o pedregulho; a calha de fratura aponta para o campo (+x).
    kit.begin_part("anim_rock")
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        beam("cradle_claw", p["smoke"], (-0.1 + sx * 0.5, sy * 0.5, 2.6), (-0.1 + sx * 0.75, sy * 0.75, 3.35), thick=0.14)
    rock(p, "basalt", (-0.1, 0, 2.7), 0.7, 0.95, sides=7, top=0.75)
    seam(p, (-0.1, 0, 3.0), (0.06, 0.5, 0.06), rot_z=0.5)
    chute = (0.85, 0, 2.35)
    tbox("chute", p["char_dk"], chute, (1.3, 0.6, 0.2), (0.0, 0.4, 0.0), bevel=0.02)
    tbox("chute_lip", p["steel"], at(chute, (0.0, 0.4, 0.0), (0.9, 0.0, 0.2)), (0.2, 0.7, 0.2), (0.0, 0.4, 0.0), bevel=0.0)
    kit.end_part()
    gas_valve(p, (1.0, -1.1, 0.1))
    sleeper(p, (1.25, 0.9, 0.1), rot_z=0.5, length=1.0)


# ---------------------------------------------------------------------------------------------------------
# Água: Water Spring -> Golden Fountain -> Spellbound Fountain
# ---------------------------------------------------------------------------------------------------------


def basin(p, center, radius, wall_h, gap=None, tone="basalt_dk", n=10):
    """Bacia anular de blocos de basalto, quebrada num lado quando gap (ângulo central) é dado."""
    cx, cy, cz = center
    cyl("basin_floor", p["char_dk"], (cx, cy, cz), radius, 0.18, sides=n, bevel=0.0)
    for i in range(n):
        a = math.tau * i / n
        if gap is not None and abs(math.remainder(a - gap, math.tau)) < 0.7:
            continue
        pos = (cx + math.cos(a) * radius * 0.92, cy + math.sin(a) * radius * 0.92, cz)
        box("basin_wall", p[tone if i % 2 else "char"], pos, (0.5, radius * math.tau / n * 1.02, wall_h), bevel=0.04, taper=0.85, taper_y=1.0, rot_z=a)


def h03X_water_spring():
    """Depressão baixa de basalto de onde sobe uma lâmina de água mineral escura, com o cano de sondagem quebrado."""
    p = pal()
    pad(p)
    box("spring_slab", p["basalt_dk"], (0, 0, 0.1), (3.2, 3.2, 0.3), bevel=0.04, taper=0.94, taper_y=0.94)
    basin(p, (0, 0, 0.4), 1.15, 0.5)
    cyl("spring_pool", p["oil"], (0, 0, 0.55), 0.95, 0.04, sides=10, bevel=0.0)
    tbox("water_blade", p["water"], (0.0, 0.0, 0.55), (0.18, 1.2, 1.9), (0.0, 0.0, 0.0), bevel=0.02, taper=0.12, taper_y=0.4, )
    tbox("water_blade_back", p["smoke"], (-0.12, 0.0, 0.55), (0.12, 0.7, 1.2), (0.0, 0.0, 0.0), bevel=0.0, taper=0.2, taper_y=0.3)
    gem(p, "smoke", (0.45, -0.4, 0.55), 0.2, 0.4, sides=5)
    # Cano de sondagem quebrado, vertendo na bacia.
    cyl("sounding_pipe", p["steel"], (-1.35, 1.1, 0.4), 0.1, 1.7, sides=8, bevel=0.0)
    beam("sounding_elbow", p["steel"], (-1.35, 1.1, 2.0), (-0.85, 0.85, 1.7), thick=0.18)
    box("pour", p["water"], (-0.8, 0.82, 0.7), (0.1, 0.1, 0.95), bevel=0.0)
    cyl("pipe_collar", p["rust"], (-1.35, 1.1, 0.9), 0.15, 0.14, sides=8, bevel=0.0)
    seam(p, (0.9, -0.9, 0.4), (0.4, 0.06, 0.05), rot_z=0.8)
    valve(p, (1.3, 1.05, 0.1), s=0.7)


def h03Y_golden_fountain():
    """Bacia anular quebrada de um lado, parede de vidro fumê, água preta subindo no perfil de ânfora do h02X."""
    p = pal()
    pad(p)
    basin(p, (0, 0, 0.1), 1.6, 0.85, gap=math.radians(-90))
    for i in range(10):
        a = math.tau * i / 10
        if abs(math.remainder(a - math.radians(-90), math.tau)) < 0.7:
            continue
        pos = (math.cos(a) * 1.15, math.sin(a) * 1.15, 0.28)
        box("glass_wall", p["smoke"], pos, (0.1, 0.72, 0.95), bevel=0.0, rot_z=a)
    cyl("water_belly", p["water"], (0, 0, 0.28), 0.65, 0.55, sides=10, top_radius=1.0, bevel=0.0)
    cyl("water_shoulder", p["water"], (0, 0, 0.83), 1.0, 0.5, sides=10, top_radius=0.5, bevel=0.0)
    cyl("water_neck", p["water"], (0, 0, 1.33), 0.5, 0.65, sides=10, top_radius=0.38, bevel=0.0)
    ring = loop
    ring(p, "rust", (0, 0, 1.45), 0.5, 0.12, n=9, plane="xy", wobble=0.05)
    obelisk(p, "ash_dk", (0.0, 0.0, 1.9), 0.3, 0.3, 0.85)
    seam(p, (1.0, 0.0, 0.3), (0.1, 0.8, 0.05))
    gem(p, "glass", (-0.2, 0.0, 0.3), 0.2, 0.45, sides=5)
    valve(p, (1.2, -1.5, 0.1), s=0.7)


def h03Z_spellbound_fountain():
    """Três bacias quebradas sobrepostas como estratos em torno de um vazio espelhado; placa de obelisco com três cristas."""
    p = pal()
    pad(p)
    basin(p, (0.0, 0.0, 0.1), 1.65, 0.6, gap=math.radians(180), n=10)
    basin(p, (-0.15, 0.1, 0.8), 1.15, 0.6, gap=math.radians(30), n=9, tone="char")
    basin(p, (0.05, -0.05, 1.5), 0.7, 0.55, gap=math.radians(-120), n=7)
    cyl("mirror_void", p["water"], (0, 0, 1.6), 0.5, 0.05, sides=8, bevel=0.0)
    tbox("mirror_plate", p["glass"], (-0.1, 0, 1.6), (0.12, 0.9, 1.5), (0.0, 0.0, 0.0), bevel=0.0, taper=0.7, taper_y=1.0)
    for dy, h in ((-0.35, 0.5), (0.0, 0.8), (0.35, 0.45)):
        kit.spike(p["glass"], (-0.1, dy, 3.0), height=h, radius=0.1)
    # Anel de revestimento aberto em duas metades, de pé na frente.
    loop(p, "rust", (1.7, 0, 0.6), 0.5, 0.1, n=5, plane="yz", a0=0.25, span=math.pi - 0.5)
    loop(p, "rust", (1.7, 0, 0.6), 0.5, 0.1, n=5, plane="yz", a0=math.pi + 0.25, span=math.pi - 0.5)
    box("well_plate", p["ash"], (1.7, 0, 0.06), (0.08, 0.3, 0.16), bevel=0.0)
    seam(p, (0.4, 0.0, 1.22), (0.1, 0.5, 0.04))
    valve(p, (1.5, -1.35, 0.1), s=0.8)


# ---------------------------------------------------------------------------------------------------------
# Relâmpago: pilares
# ---------------------------------------------------------------------------------------------------------


def pillar_base(p, shaft_h):
    """Base de carvão comprimido e fuste de coluna quebrada, em comum nos dois pilares."""
    pad(p, (2.9, 2.9))
    for i, (w, h) in enumerate(((2.6, 0.45), (2.2, 0.4), (1.7, 0.35))):
        box("pillar_step", p["char" if i % 2 == 0 else "basalt_dk"], (-0.05, 0, 0.1 + 0.4 * i - (0.03 if i else 0.0)), (w, w * 0.95, h), bevel=0.04, rot_z=0.15 * i)
    box("shaft", p["basalt_dk"], (0, 0, 1.3), (0.95, 0.95, shaft_h), bevel=0.04, taper=0.85, taper_y=0.85)
    top = 1.3 + shaft_h
    seam(p, (0.46, 0.05, 1.5), (0.04, 0.12, shaft_h * 0.7))
    return top


def wrap(p, tone, radius, z0, z1, turns=4):
    """Cabo queimado enrolado em hélice no fuste."""
    steps = turns * 6
    prev = None
    for i in range(steps + 1):
        t = i / steps
        a = t * turns * math.tau
        pt = (math.cos(a) * radius, math.sin(a) * radius, z0 + (z1 - z0) * t)
        if prev is not None:
            beam("cable", p[tone], prev, pt, thick=0.06)
        prev = pt


def h042_globe_pillar():
    """Coluna curta partida em Y como um fulgurito monumental, globo de quartzo entre as pontas e cabo enrolado."""
    p = pal()
    top = pillar_base(p, 1.3)
    wrap(p, "steel", 0.56, 1.45, top - 0.1)
    for s in (-1, 1):
        beam("y_arm", p["char"], (0, 0, top - 0.1), (-0.1, s * 0.85, top + 1.3), thick=0.34)
        kit.spike(p["glass"], (-0.1, s * 0.85, top + 1.3), height=0.4, radius=0.1)
    kit.begin_part("anim_gem")
    gem(p, "glass", (-0.05, 0, top + 0.55), 0.38, 0.85, sides=7)
    kit.end_part()
    seam(p, (-0.05, 0, top - 0.12), (0.2, 0.2, 0.3))
    chain(p, (0.5, 0.2, top - 0.5), (1.15, 0.9, 0.3), links=5)
    post(p, (1.2, 0.95, 0.1))
    valve(p, (1.15, -0.9, 0.1), s=0.7)


def h044_st_elmos_pillar():
    """Mesmo pilar crescido em cinco agulhas assimétricas em leque aberto, capacitor engaiolado e cadeia dupla."""
    p = pal()
    top = pillar_base(p, 1.7)
    wrap(p, "steel", 0.56, 1.45, top - 0.3, turns=3)
    needles = ((-1.5, 3.4, 0.1), (-0.85, 4.1, 0.0), (0.0, 4.45, -0.05), (0.8, 3.95, 0.05), (1.45, 3.3, 0.1))
    for y, z, x in needles:
        beam("fan_needle", p["char"], (0, 0, top - 0.1), (x, y, z), thick=0.22)
        kit.spike(p["glass"], (x, y, z), height=0.35, radius=0.09)
    gem(p, "glass", (0.0, 0, top + 0.1), 0.34, 0.7, sides=7)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        beam("cage_bar", p["steel"], (sx * 0.34, sy * 0.34, top - 0.05), (sx * 0.34, sy * 0.34, top + 0.9), thick=0.06)
    for s in (-1, 1):
        chain(p, (0.5, s * 0.25, top - 0.4), (1.3, s * 0.9, 0.2), links=6)
        chain(p, (0.5, s * 0.1, top - 0.6), (1.2, s * 0.7, 0.2), links=6, thick=0.05)
    dynamo(p, (1.1, -1.25, 0.1))
    seam(p, (1.2, -1.05, 0.45), (0.2, 0.12, 0.1))
    post(p, (1.4, 1.1, 0.1))


# ---------------------------------------------------------------------------------------------------------
# Vento: Trapped Gale -> Monument of Wind Stream -> Zephyros Memorial
# ---------------------------------------------------------------------------------------------------------


def h04A_trapped_gale():
    """Ferradura baixa de basalto quase fechada sobre um bolsão de cinza, com a fenda do dardo na boca."""
    p = pal()
    pad(p)
    horseshoe(p, radius=1.35, height=1.25, gap=0.36, thick=0.75)
    dome("ash_pocket", p["ash"], (0, 0, 0.5), 0.95, squash=1.3, sides=10)
    box("dart_slot", p["oil"], (1.58, 0, 0.55), (0.1, 0.7, 0.1), bevel=0.0)
    seam(p, (1.62, 0, 0.55), (0.06, 0.4, 0.04))
    # Duas argolas de perfuração flambadas como grade; contrapeso de obelisco rachado na boca.
    loop(p, "rust", (0, 0, 1.45), 0.85, 0.09, n=8, plane="xy", wobble=0.08)
    loop(p, "rust", (0.05, 0, 1.6), 0.55, 0.09, n=7, plane="xy", wobble=0.1)
    obelisk(p, "ash_dk", (1.35, 0.85, 0.1), 0.34, 0.3, 1.3, rot=(0.0, 0.35, 0.0))
    seam(p, (1.5, 0.85, 0.6), (0.05, 0.05, 0.3))
    gas_valve(p, (0.5, -1.65, 0.1))


def h04C_wind_monument():
    """Arco crescente de obelisco quebrado comprimindo uma coluna de cinza horizontal, com o V assimétrico de vidro."""
    p = pal()
    pad(p)
    horseshoe(p, radius=1.35, height=0.55, gap=1.6, thick=0.6, tone="basalt_dk")
    # Arco crescente no plano y-z: perna esquerda subindo mais que a direita.
    loop(p, "char", (-0.2, 0, 0.5), 1.3, 0.42, n=8, plane="yz", a0=math.radians(-10), span=math.radians(190))
    cyl("ash_column", p["ash"], (-1.1, 0, 1.15), 0.42, 2.3, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
    # O V assimétrico: um espar de vidro bem maior que o outro, saindo do vão do arco.
    beam("spar_long", p["glass"], (-0.2, 0.3, 2.4), (-0.2, 1.1, 3.9), thick=0.13)
    beam("spar_short", p["glass"], (-0.2, 0.3, 2.4), (-0.2, -0.55, 3.2), thick=0.13)
    loop(p, "glass", (0.55, 0, 1.15), 0.6, 0.06, n=10, plane="yz")
    seam(p, (-0.2, 0.3, 1.6), (0.12, 0.12, 0.7))
    gas_valve(p, (0.7, 1.55, 0.1))
    rock(p, "char_dk", (1.35, -1.1, 0.1), 0.28, 0.45, sides=5)


def h04D_zephyros_memorial():
    """Obelisco partido ao meio, tempestade horizontal cruzando a fresta, duas placas crescentes de asa, quilha de vidro."""
    p = pal()
    pad(p)
    horseshoe(p, radius=1.4, height=0.5, gap=2.0, thick=0.55, tone="basalt_dk")
    for s in (-1, 1):
        tbox("half", p["char" if s > 0 else "basalt_dk"], (-0.3, s * 0.4, 0.1), (0.9, 0.62, 3.5), (s * 0.05, 0.0, 0.0), bevel=0.03, taper=0.5, taper_y=0.7)
        top = at((-0.3, s * 0.4, 0.1), (s * 0.05, 0.0, 0.0), (0, 0, 3.5))
        tbox("half_tip", p["char" if s > 0 else "basalt_dk"], top, (0.45, 0.43, 0.4), (s * 0.05, 0.0, 0.0), bevel=0.0, taper=0.1, taper_y=0.1)
        # Asa fóssil: crescente grande no plano y-z, aberta para fora.
        loop(p, "ash_dk", (-0.3, s * 0.8, 1.7), 0.95, 0.26, n=6, plane="yz", a0=math.radians(-20 if s > 0 else 200), span=math.radians(130 * s))
    seam(p, (-0.3, 0, 0.14), (0.6, 0.16, 0.04))
    seam(p, (-0.3, 0, 0.5), (0.1, 0.1, 0.7))
    gem(p, "glass", (-0.3, 0, 1.7), 0.14, 1.5, sides=5)
    cyl("storm_band", p["ash"], (0.7, -1.15, 2.0), 0.3, 2.3, sides=9, bevel=0.0, rot=("X", math.radians(-90)))
    for k in range(5):
        a = k * math.tau / 5
        kit.spike(p["glass"] if k % 2 else p["ash_dk"], (-0.3 + math.cos(a) * 0.18, math.sin(a) * 0.18, 3.7), height=0.45, radius=0.06, lean=(math.cos(a) * 0.12, math.sin(a) * 0.12))
    gas_valve(p, (1.0, 1.45, 0.1))


# ---------------------------------------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------------------------------------


def h060_obelisk_of_elements():
    """Obelisco rachado em quatro placas de materiais em torno de um vazio central, com halo de quatro cacos por forma."""
    p = pal()
    pad(p, (3.2, 3.2))
    box("plinth", p["basalt_dk"], (0, 0, 0.1), (2.6, 2.6, 0.3), bevel=0.04, taper=0.92, taper_y=0.92)
    seam(p, (0, 0, 0.4), (0.5, 0.5, 0.04))
    plates = ((-0.5, -0.5, "char", 3.0), (0.5, -0.5, "smoke", 2.5), (0.5, 0.5, "ash", 3.4), (-0.5, 0.5, "rust", 2.8))
    for x, y, tone, h in plates:
        box("elem_plate", p[tone], (x * 0.62, y * 0.62, 0.4), (0.78, 0.78, h), bevel=0.03, taper=0.55, taper_y=0.55)
        box("elem_tip", p[tone], (x * 0.62, y * 0.62, 0.4 + h), (0.43, 0.43, 0.22), bevel=0.0, taper=0.1, taper_y=0.1)
    seam(p, (0, 0, 0.4), (0.22, 0.22, 2.2))
    seam(p, (0.32, -0.32 - 0.38, 1.0), (0.05, 0.02, 1.6))
    # Halo de quatro cacos, cada um com forma própria, nos cantos da base.
    box("shard_cube", p["char"], (1.1, -1.1, 0.4), (0.3, 0.3, 0.3), bevel=0.0, rot_z=0.6)
    gem(p, "smoke", (1.1, 1.1, 0.4), 0.2, 0.55)
    prism("shard_wedge", p["ash"], (-1.1, 1.1, 0.4), (0.45, 0.4, 0.4), ridge=0.8, bevel=0.0, rot_z=0.8)
    kit.spike(p["rust"], (-1.1, -1.1, 0.4), height=0.55, radius=0.16)
    valve(p, (1.35, 0.0, 0.1), s=0.7)


def h063_linker():
    """Anel radial de lajes em torno de um obelisco quebrado, rachaduras unindo os setores e quatro correntes."""
    p = pal()
    pad(p)
    cyl("hub_floor", p["char_dk"], (0, 0, 0.1), 1.1, 0.2, sides=12, bevel=0.0)
    for i in range(8):
        a = math.tau * i / 8 + 0.2
        pos = (math.cos(a) * 1.35, math.sin(a) * 1.35, 0.1)
        box("ring_slab", p["basalt_dk" if i % 2 else "char"], pos, (0.62, 0.95, 0.36 + 0.1 * (i % 3)), bevel=0.04, taper=0.85, taper_y=0.9, rot_z=a)
    for i in range(4):
        a = math.tau * i / 4 + 0.2 + math.pi / 8 + 0.2
        seam(p, (math.cos(a) * 0.62, math.sin(a) * 0.62, 0.3), (1.0, 0.09, 0.04), rot_z=a)
    # Obelisco quebrado: metade alta e metade baixa, o pulso de vidro preso na fenda.
    tbox("obelisk_hi", p["char"], (-0.12, -0.2, 0.3), (0.42, 0.7, 2.7), (0.0, 0.0, 0.0), bevel=0.03, taper=0.55, taper_y=0.7)
    tbox("obelisk_lo", p["basalt_dk"], (0.15, 0.25, 0.3), (0.4, 0.62, 1.9), (0.0, -0.12, 0.0), bevel=0.03, taper=0.5, taper_y=0.7)
    seam(p, (0.03, 0.02, 0.3), (0.08, 0.5, 1.5))
    gem(p, "glass", (0.2, 0.0, 1.0), 0.15, 0.55, sides=5)
    for i in range(4):
        a = math.tau * i / 4 + math.pi / 4
        chain(p, (math.cos(a) * 0.3, math.sin(a) * 0.3, 2.0), (math.cos(a) * 1.65, math.sin(a) * 1.65, 0.46), links=8, tone="steel", thick=0.1)
        cyl("chain_stake", p["steel"], (math.cos(a) * 1.68, math.sin(a) * 1.68, 0.1), 0.06, 0.4, sides=5, bevel=0.0)
    post(p, (1.55, 0.2, 0.1), 0.6)


def h062_pressure_generator():
    """Carcaça esmagada de uma sonda humana entre duas lajes, com nervo horizontal, cápsula de quartzo e cabo de transferência."""
    p = pal()
    pad(p)
    for s in (-1, 1):
        tbox("squeeze_slab", p["char" if s > 0 else "basalt_dk"], (-0.1, s * 1.15, 0.4), (2.7, 0.7, 1.25), (s * -0.18, 0.0, 0.0), bevel=0.04, taper=0.8, taper_y=0.9)
    box("crushed_rig", p["rust"], (-0.1, 0, 0.1), (2.0, 1.3, 0.55), bevel=0.04)
    box("rig_deck", p["char_dk"], (-0.2, 0, 0.65), (1.5, 1.1, 0.12), bevel=0.0, rot_z=0.15)
    for dx in (-0.7, 0.7):
        cyl("rig_wheel", p["steel"], (-0.1 + dx, 0, 0.1), 0.32, 0.12, sides=8, bevel=0.0, rot=("X", math.radians(90)))
    # Treliça amassada sobre a carcaça.
    beam("bent_leg", p["rust"], (-0.8, -0.4, 0.7), (0.0, 0.2, 1.5), thick=0.12)
    beam("bent_leg", p["rust"], (0.7, 0.4, 0.7), (0.2, -0.1, 1.35), thick=0.12)
    # O nervo horizontal e a cápsula de quartzo onde ficava o eixo.
    beam("nerve", p["steel"], (-0.1, -1.5, 0.95), (-0.1, 1.5, 0.95), thick=0.16)
    gem(p, "glass", (-0.1, 0, 0.8), 0.32, 0.95, sides=7)
    seam(p, (-0.1, 0.72, 0.45), (0.9, 0.05, 0.55))
    seam(p, (-0.1, -0.72, 0.45), (0.9, 0.05, 0.55))
    beam("transfer_cable", p["char_dk"], (0.6, 0.0, 0.2), (1.5, 0.0, 0.2), thick=0.2)
    beam("transfer_cable", p["char_dk"], (1.5, 0.0, 0.2), (1.5, -0.8, 0.2), thick=0.2)
    post(p, (1.5, -0.95, 0.1))
    valve(p, (1.3, 1.2, 0.1), s=0.7)


# ---------------------------------------------------------------------------------------------------------
# Tower of Elder Knowledge
# ---------------------------------------------------------------------------------------------------------


def h04E_tower_of_logged_seam():
    """Coluna estratigráfica altíssima de lajes deslocadas em torno de um vazio, halo quebrado e a broca fossilizada."""
    p = pal()
    pad(p, (3.0, 3.0))
    box("tower_foot", p["basalt_dk"], (0, 0, 0.1), (2.8, 2.8, 0.35), bevel=0.04, taper=0.92, taper_y=0.92)
    seam(p, (0, 0, 0.45), (0.3, 0.3, 3.0))
    # Camadas de quatro lajes em volta do vazio central, cada camada girada um pouco: lascas deslocadas.
    for layer in range(6):
        z = 0.45 + layer * 0.55
        spin = 0.15 * layer
        k = 1.0 - 0.07 * layer
        for q in range(4):
            a = spin + q * math.pi / 2
            reach = 0.68 * k
            pos = (math.cos(a) * reach, math.sin(a) * reach, z)
            tone = "char" if (layer + q) % 2 == 0 else "basalt_dk"
            box("tower_slab", p[tone], pos, (0.85 * k, 0.7 * k, 0.5), bevel=0.03, rot_z=a)
    # Halo quebrado em três arcos com quatro núcleos de materiais, presos por escoras.
    zh = 3.95
    for k in range(3):
        loop(p, "steel", (0, 0, zh), 1.15, 0.12, n=4, plane="xy", a0=k * math.tau / 3 + 0.15, span=math.tau / 3 - 0.55)
    cores = (("char", 0), ("smoke", 1), ("ash", 2), ("rust", 3))
    for tone, q in cores:
        a = q * math.pi / 2 + 0.6
        pos = (math.cos(a) * 1.15, math.sin(a) * 1.15, zh - 0.12)
        beam("halo_strut", p["steel"], (math.cos(a) * 0.5, math.sin(a) * 0.5, 3.6), pos, thick=0.07)
        if q == 0:
            box("core_cube", p[tone], pos, (0.26, 0.26, 0.26), bevel=0.0, rot_z=a)
        elif q == 1:
            gem(p, tone, (pos[0], pos[1], pos[2] - 0.1), 0.15, 0.4, sides=5)
        elif q == 2:
            dome("core_cloud", p[tone], pos, 0.19, squash=0.8, sides=7)
        else:
            kit.spike(p[tone], (pos[0], pos[1], pos[2] - 0.1), height=0.42, radius=0.11)
    bit(p, (0, 0, 3.9), height=0.9, radius=0.26, up=True)
    sleeper(p, (1.1, 0.9, 0.1), rot_z=0.2, length=1.0)
    valve(p, (1.4, -1.1, 0.1), s=0.8)


BUILDINGS = {
    "h040": h040_rock_pile,
    "h041": h041_greater_fissure,
    "h045": h045_altar_of_fire,
    "h046": h046_altar_of_blaze,
    "h05Z": h05Z_archive,
    "h06F": h06F_elemental_rain,
    "h06E": h06E_meteor_shower,
    "h076": h076_discharge_tower,
    "h061": h061_guard_tower,
    "h03X": h03X_water_spring,
    "h03Y": h03Y_golden_fountain,
    "h03Z": h03Z_spellbound_fountain,
    "h042": h042_globe_pillar,
    "h044": h044_st_elmos_pillar,
    "h04A": h04A_trapped_gale,
    "h04C": h04C_wind_monument,
    "h04D": h04D_zephyros_memorial,
    "h060": h060_obelisk_of_elements,
    "h063": h063_linker,
    "h062": h062_pressure_generator,
    "h04E": h04E_tower_of_logged_seam,
}


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["all"]
    names = list(BUILDINGS) if args[0] == "all" else [args[0]]
    out_dir = game_paths.out_arg(args, "--out", "buildings", "elemental")
    render_dir = args[args.index("--render") + 1] if "--render" in args else ""
    for name in names:
        kit.build(name, out_dir, render_dir, make=BUILDINGS[name], views=(("front", -35.0),))


if __name__ == "__main__":
    main()
