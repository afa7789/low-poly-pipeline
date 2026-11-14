"""Prédios da raça Nightelf modelados por script (redesenho de reports/design/race-nightelf.md): um GLB por prédio.

Uso:
    blender -b --factory-startup --python tools/blender/buildings_nightelf.py -- <id|all> [--out DIR] [--render DIR]

Vigília das Bruxas (Vigil Witches): a raça que trabalha no escuro entre os turnos, sangra o óleo dos outros e
o separa a frio. Prata fosca oxidada, lona oleada azul-violeta, tábuas cinza-lilás, concreto rachado, névoa
no pé. O escuro vem do matiz (azul frio, violeta, prata lunar), nunca do valor: tudo é claro o bastante para
ler no jogo. Acentos pequenos: vidro frio ciano (carga de sal de prata) e a plaqueta de latão do turno.
Regra da raça, cumprida em todo prédio: lama com névoa no pé, uma lanterna morta (vidro sem luz), um crescente
dominante no contorno, e o PREÇO à vista (plaquetas de tendedores mortos, ampola vazia, caixa de cartuchos
gastos, calha de resíduo). Nada queima: não há chama nem forja. Linhas tortas, nunca ortogonais demais.
Pegada ~3,5 x 3,5 centrada na origem, a porta virada para +x; o jogo normaliza o tamanho, põe o plinto do time
e desenha a bandeira. Câmera do jogo olha de -y: os crescentes grandes ficam no plano xz.
"""

import math
import os
import random
import sys

import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_paths  # noqa: E402
import map_castles as kit
from map_castles import beam, box, cyl, dome, mat, prism, ring
from map_scenery import wire_coil


def pal():
    return {
        "silver": mat("moon_silver", 0xC4CCE0),
        "silver_dk": mat("silver_dark", 0x8E99B8),
        "blue": mat("canvas_blue", 0x7487BA),
        "blue_dk": mat("canvas_blue_dark", 0x56649A),
        "violet": mat("violet", 0x9684C4),
        "violet_dk": mat("violet_dark", 0x6A5A98),
        "wood": mat("board", 0x9A93AA),
        "wood_dk": mat("board_dark", 0x6C6682),
        "wood_lt": mat("board_light", 0xB9B3C8),
        "concrete": mat("concrete_n", 0xB0B5C8),
        "concrete_lt": mat("concrete_n_light", 0xD2D6E4),
        "concrete_dk": mat("concrete_n_dark", 0x7F849C),
        "rust": mat("rust", 0x9A7A74),
        "rust_dk": mat("rust_dark", 0x6E5656),
        "char": mat("char", 0x6F6880),
        "char_lt": mat("char_light", 0x8E87A0),
        "soot": mat("soot_n", 0x34323F),
        "mud": mat("mud_n", 0x5C566E),
        "mud_lt": mat("mud_n_light", 0x7E7898),
        "oil": mat("oil_n", 0x2A2838),
        "fog": mat("fog", 0xD3DAEC),
        "lichen": mat("lichen", 0x86B0A0),
        "thatch": mat("thatch", 0xBDB59A),
        "hide": mat("hide", 0xB39A7C),
        "glass_dead": mat("glass_dead", 0x8FA6C4),
        "glass": mat("glass_cold", 0x4FC8E6, emit=1.6),
        "pool": mat("pool_cold", 0x5AB4D2, emit=0.5),
        "oil_sheen": mat("oil_sheen", 0x6A5AA8, emit=0.3),
        "brass": mat("plaque_brass", 0xDDA338),
    }


# ---------------------------------------------------------------------------------------------------------
# Primitivas novas
# ---------------------------------------------------------------------------------------------------------


def slab(name, material, pts, width, center=(0.0, 0.0, 0.0), rot_z=0.0, bevel=0.0):
    """Perfil convexo (x, z) extrudado ao longo de y (largura `width`, centrada): rampas, bacias, empenas."""
    bm = bmesh.new()
    front = [bm.verts.new((x, -width / 2, z)) for x, z in pts]
    back = [bm.verts.new((x, width / 2, z)) for x, z in pts]
    bm.faces.new(front)
    bm.faces.new(reversed(back))
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new((front[j], front[i], back[i], back[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(rot_z, 3, "Z"))
    bmesh.ops.translate(bm, verts=bm.verts, vec=center)
    return kit._finish(bm, name, material, bevel)


def arc(name, material, center, radius, a0, a1, thick=0.1, az=90.0, n=9, taper=True):
    """Arco de tubos de a0 a a1 (graus no plano; 0 = +u, 90 = cima). O plano tem normal em azimute `az`
    (90 = normal em y, plano xz, o que a câmera do jogo vê). taper engrossa o meio: é o crescente."""
    cx, cy, cz = center
    a = math.radians(az)
    ux, uy = math.sin(a), -math.cos(a)
    pts = []
    for i in range(n + 1):
        t = math.radians(a0 + (a1 - a0) * i / n)
        u, v = radius * math.cos(t), radius * math.sin(t)
        pts.append((cx + ux * u, cy + uy * u, cz + v))
    for i in range(n):
        k = 0.35 + 0.65 * math.sin(math.pi * (i + 0.5) / n) if taper else 1.0
        beam(name, material, pts[i], pts[i + 1], thick=thick * k)


def crescent(p, center, radius, thick=0.12, mid=270.0, span=210.0, az=90.0, tone="silver"):
    """O crescente da raça: arco oco de espessura variável. mid = direção do miolo (270 = copo aberto p/ cima)."""
    arc("crescent", p[tone], center, radius, mid - span / 2, mid + span / 2, thick=thick, az=az, n=10)


def valve_wheel(p, center, radius, az=90.0, tone="silver_dk"):
    """Roda de válvula roubada, trincada: arco quase fechado, cubo e raios."""
    kit.begin_part("anim_wheel", unique=True)
    arc("wheel", p[tone], center, radius, 20.0, 350.0, thick=0.07, az=az, n=12, taper=False)
    a = math.radians(az)
    ux, uy = math.sin(a), -math.cos(a)
    for k in range(4):
        t = math.radians(45 + k * 90)
        tip = (center[0] + ux * radius * math.cos(t), center[1] + uy * radius * math.cos(t), center[2] + radius * math.sin(t))
        beam("wheel_spoke", p[tone], center, tip, thick=0.04)
    box("wheel_hub", p[tone], (center[0] - 0.05, center[1] - 0.05, center[2] - 0.05), (0.1, 0.1, 0.1), bevel=0.0)
    kit.end_part()


def chain(p, a, b, links=None, tone="soot"):
    """Corrente de elos alternados de a até b."""
    a, b = Vector(a), Vector(b)
    n = links or max(3, round((b - a).length / 0.1))
    for i in range(n):
        c = a.lerp(b, (i + 0.5) / n)
        d = 0.07 if i % 2 else 0.05
        box("link", p[tone], (c.x, c.y, c.z - 0.05), (d, 0.11 - d, 0.1), bevel=0.0)


def pad(p, size=(3.5, 3.5), tone="mud"):
    """Chão do posto, do tamanho do conteúdo: o jogo normaliza pelo maior lado."""
    box("pad", p[tone], (0, 0, 0), (size[0], size[1], 0.1), bevel=0.03)


FOG_DEFAULT = ((1.3, 1.0, 0.8, 0.5), (1.2, -1.05, 0.6, 0.45), (-1.1, -1.2, 0.7, 0.4))


def fog(p, spots=FOG_DEFAULT):
    """Névoa rasteira no pé: manchas claras chatas sobre a lama."""
    for x, y, sx, sy in spots:
        box("fog", p["fog"], (x, y, 0.1), (sx, sy, 0.05), bevel=0.0, taper=0.7, taper_y=0.7, rot_z=x + y)


def dead_lantern(p, pos, post=0.0, size=1.0, inverted=False):
    """Lanterna morta: gaiola de prata e vidro sem luz. post > 0 põe num poste; inverted a pendura de cabeça p/ baixo."""
    x, y, z = pos
    if post > 0.0:
        box("lantern_post", p["wood_dk"], (x, y, z), (0.07, 0.07, post), bevel=0.0)
        beam("lantern_hook", p["wood_dk"], (x, y, z + post), (x + 0.12 * size, y, z + post + 0.02), thick=0.05)
        x, z = x + 0.12 * size, z + post - 0.2 * size
    s = size
    cap = p["silver"]
    box("lantern_base", p["silver_dk"], (x, y, z), (0.16 * s, 0.16 * s, 0.04 * s), bevel=0.0)
    box("lantern_glass", p["glass_dead"], (x, y, z + 0.04 * s), (0.11 * s, 0.11 * s, 0.15 * s), bevel=0.0)
    if inverted:
        box("lantern_cap", cap, (x, y, z - 0.05 * s), (0.04 * s, 0.04 * s, 0.05 * s), bevel=0.0)
    else:
        box("lantern_cap", cap, (x, y, z + 0.19 * s), (0.18 * s, 0.18 * s, 0.05 * s), bevel=0.0, taper=0.4, taper_y=0.4)


def plaques(p, pos, count=5, step=0.3, along="y", post=0.3):
    """Fileira de estacas com plaquetas de latão: o turno dos tendedores que morreram no condensador."""
    x, y = pos[:2]
    z = pos[2] if len(pos) > 2 else 0.1
    for i in range(count):
        dx, dy = (i * step, 0.0) if along == "x" else (0.0, i * step)
        box("plaque_stake", p["wood_dk"], (x + dx, y + dy, z), (0.05, 0.05, post), bevel=0.0)
        box("plaque", p["brass"], (x + dx + 0.03, y + dy, z + post * 0.55), (0.03, 0.1, 0.09), bevel=0.0)


def jar(p, pos, full=True, r=0.11, h=0.3):
    """Jarra/ampola de condensado: cheia brilha em ciano, vazia é vidro morto."""
    x, y, z = pos
    cyl("jar", p["glass" if full else "glass_dead"], (x, y, z), r, h, sides=7, bevel=0.0)
    cyl("jar_cap", p["silver_dk"], (x, y, z + h), r * 0.7, 0.05, sides=7, bevel=0.0)


def plate(p, pos, w=0.9, h=1.4, lean=0.35, rot_z=0.0, tone="silver"):
    """Placa de condensador prateada, inclinada fora do prumo."""
    slab("plate", p[tone], [(0, 0), (0.08, 0), (0.08 + lean, h), (lean, h)], w, center=pos, rot_z=rot_z)


def half_drum(p, pos, radius=0.78, length=1.8, liquid=True):
    """Tambor de óleo cortado ao meio e deitado: a bacia de condensação. Eixo ao longo de y."""
    x, y, z = pos
    pts = [(radius * math.cos(-math.pi * i / 10), radius * math.sin(-math.pi * i / 10)) for i in range(11)]
    slab("drum_half", p["rust"], pts, length, center=(x, y, z), bevel=0.0)
    for dy in (-length * 0.3, length * 0.3):
        slab("drum_hoop", p["silver_dk"], [(q[0] * 1.04, q[1] * 1.04 - 0.01) for q in pts], 0.08, center=(x, y + dy, z))
    if liquid:
        box("condensate", p["pool"], (x, y, z - 0.02), (radius * 1.74, length * 0.92, 0.05), bevel=0.0)
    for sy in (-1, 1):
        box("drum_rim", p["silver"], (x, y + sy * length / 2, z - 0.03), (radius * 2.0, 0.07, 0.07), bevel=0.0)
    for sx in (-1, 1):
        box("drum_rim", p["silver"], (x + sx * radius, y, z - 0.03), (0.07, length, 0.07), bevel=0.0)


def casings(p, pos, count=4):
    """Cartuchos gastos de sal de prata: cilindros baixos, vidro morto."""
    x, y, z = pos
    for i in range(count):
        cyl("casing", p["silver_dk"], (x + (i % 2) * 0.13, y + (i // 2) * 0.13, z), 0.05, 0.16, sides=6, bevel=0.0)


def trough(p, pos, size=(0.9, 1.2), full=True):
    """Calha de resíduo preto aos pés: o preço guardado."""
    x, y, z = pos
    box("trough", p["concrete_dk"], (x, y, z), (size[0], size[1], 0.14), bevel=0.02)
    box("residue", p["oil"], (x, y, z + 0.1), (size[0] - 0.16, size[1] - 0.16, 0.05 if full else 0.01), bevel=0.0)


def crate(p, pos, size=(0.5, 0.4, 0.3), rot_z=0.0, tone="wood"):
    x, y, z = pos
    box("crate", p[tone], (x, y, z), size, bevel=0.02, rot_z=rot_z)
    box("crate_band", p["wood_dk"], (x, y, z + size[2] * 0.45), (size[0] * 1.03, size[1] * 1.03, 0.05), bevel=0.0, rot_z=rot_z)


def smoke(p, pos, n=3, step=0.28):
    """Fio de fumaça fria e fina: puffs pálidos que se afastam, saindo de coisa morta."""
    x, y, z = pos
    for i in range(n):
        s = 0.2 + 0.05 * i
        box("smoke", p["fog"], (x + 0.07 * i, y + 0.04 * i, z + i * step), (s, s, 0.16), bevel=0.0, taper=0.7, taper_y=0.7, rot_z=0.5 * i)


def rot2(x, y, a):
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


# ---------------------------------------------------------------------------------------------------------
# Tronco dos druidas: Moon Shrine -> Moon Altar; e a Fountain of Wonders
# ---------------------------------------------------------------------------------------------------------


def h088_moon_shrine():
    """Câmara fria: tambor cortado deitado como bacia de condensação, placas prateadas e um crescente alto."""
    p = pal()
    pad(p)
    fog(p)
    for y in (-0.55, 0.55):
        box("cradle", p["wood_dk"], (-0.1, y, 0.1), (1.5, 0.12, 0.34), bevel=0.0)
    half_drum(p, (-0.1, 0.0, 1.0))
    # Crescente alto atrás da bacia, tombado, sobre um poste de prata.
    crescent(p, (-0.2, 1.15, 2.2), 0.95, thick=0.2, mid=265.0, span=215.0)
    beam("crescent_post", p["silver_dk"], (-0.2, 1.15, 0.1), (-0.2, 1.15, 1.35), thick=0.14)
    # Placas e espelhos de estaca em volta.
    plate(p, (-1.45, -0.55, 0.1), w=0.8, h=1.7, lean=0.4)
    plate(p, (-1.4, 0.45, 0.1), w=0.7, h=1.4, lean=0.3, rot_z=0.2)
    for x, y in ((0.7, -1.35), (-0.9, -1.4)):
        beam("stake", p["wood_dk"], (x, y, 0.1), (x + 0.05, y, 1.0), thick=0.06)
        cyl("stake_mirror", p["silver"], (x - 0.05, y + 0.04, 0.95), 0.2, 0.05, sides=8, bevel=0.0, rot=("Y", math.radians(-40)))
    # Bexiga de couro enterrada e mangueira até a bacia.
    dome("bladder", p["hide"], (1.1, 1.35, 0.1), 0.42, squash=0.55, sides=9)
    beam("hose", p["soot"], (1.0, 1.25, 0.4), (0.75, 0.6, 0.55), thick=0.07)
    beam("hose", p["soot"], (0.75, 0.6, 0.55), (0.45, 0.6, 1.0), thick=0.07)
    # Sumidouro de resíduo aos pés e o dreno.
    trough(p, (1.1, -0.15, 0.1), (0.9, 1.3))
    beam("drain", p["silver_dk"], (0.65, -0.15, 0.55), (0.95, -0.15, 0.3), thick=0.08)
    for dy in (-0.3, 0.0, 0.3):
        box("salt_crust", p["fog"], (0.62, dy, 0.98), (0.16, 0.2, 0.06), bevel=0.0, rot_z=dy)
    plaques(p, (1.65, -1.1), count=6, step=0.42)
    dead_lantern(p, (1.4, 1.3, 0.1), post=0.8)


def basin_core(p, pos):
    """Bacia pequena e placas do Moon Shrine, herdadas pelo Moon Altar (cadeia de upgrade)."""
    x, y, z = pos
    half_drum(p, (x, y, z + 0.5), radius=0.5, length=1.1)
    box("basin_legs", p["wood_dk"], (x, y, z), (0.9, 0.9, 0.3), bevel=0.0)
    plate(p, (x - 0.7, y - 0.3, z), w=0.55, h=1.1, lean=0.3)


def h07D_moon_altar():
    """Estaca de interrogatório: laje de fundação rachada, poste central com peças de máquina acorrentadas."""
    p = pal()
    pad(p)
    fog(p, ((1.3, 1.2, 0.7, 0.5), (1.4, -0.4, 0.6, 0.4), (-1.0, 1.4, 0.6, 0.4)))
    box("slab", p["concrete_dk"], (0.0, 0.0, 0.1), (3.0, 3.0, 0.24), bevel=0.04, rot_z=0.05)
    box("slab_top", p["concrete"], (0.0, 0.0, 0.34), (2.7, 2.7, 0.05), bevel=0.0, rot_z=0.05)
    box("crack", p["soot"], (0.1, 0.1, 0.38), (0.06, 2.4, 0.02), bevel=0.0, rot_z=0.9)
    for x, y, lx, ly in ((1.4, 1.2, 0.2, 0.1), (1.35, -1.3, 0.1, -0.25), (-1.4, 1.35, -0.2, 0.25), (-1.35, -1.2, -0.15, -0.2)):
        beam("rebar", p["rust"], (x, y, 0.3), (x + lx, y + ly, 1.0), thick=0.05)
    basin_core(p, (-0.9, 0.95, 0.38))
    # Poste e peças acorrentadas: roda, manômetro, dobradiça.
    box("post", p["wood_dk"], (0.1, -0.2, 0.34), (0.24, 0.24, 3.3), bevel=0.02, taper=0.8, taper_y=0.8)
    for z, tone in ((1.0, "rust_dk"), (2.2, "rust_dk")):
        box("post_strap", p[tone], (0.1, -0.2, z), (0.3, 0.3, 0.07), bevel=0.0)
    valve_wheel(p, (0.1, -0.7, 2.3), 0.4, tone="silver_dk")
    chain(p, (0.1, -0.35, 2.7), (0.1, -0.6, 2.6), links=3)
    cyl("gauge", p["silver"], (0.1, -0.75, 1.35), 0.25, 0.08, sides=10, bevel=0.0, rot=("X", math.radians(90)))
    cyl("gauge_dial", p["soot"], (0.1, -0.84, 1.35), 0.17, 0.02, sides=10, bevel=0.0, rot=("X", math.radians(90)))
    box("hinge", p["rust"], (0.45, -0.3, 1.1), (0.4, 0.14, 0.26), bevel=0.02, rot_z=0.3)
    chain(p, (0.25, -0.2, 1.5), (0.5, -0.3, 1.25), links=3)
    # O crescente: foice de prata pendurada por corrente no poste.
    chain(p, (0.1, -0.2, 3.5), (0.55, -0.2, 3.1), links=5)
    crescent(p, (0.75, -0.2, 3.25), 0.5, thick=0.17, mid=290.0, span=230.0)
    wire_coil(p["soot"], (-0.2, -0.2, 1.7), (0.55, -0.5, 1.5), radius=0.13, turns=4)
    # Espelho em tripé inclinado para a lua.
    for a in (0, 120, 240):
        t = math.radians(a)
        beam("tripod", p["wood_dk"], (1.1 + math.cos(t) * 0.25, -1.0 + math.sin(t) * 0.25, 0.38), (1.1, -1.0, 1.1), thick=0.05)
    cyl("mirror", p["silver"], (1.1, -1.0, 1.05), 0.36, 0.05, sides=10, bevel=0.0, rot=("Y", math.radians(50)))
    box("engine_block", p["rust"], (0.9, 0.5, 0.38), (0.6, 0.5, 0.4), bevel=0.04, rot_z=0.4)
    cyl("engine_cyl", p["rust_dk"], (0.95, 0.5, 0.78), 0.14, 0.28, sides=8, bevel=0.0)
    chain(p, (0.3, -0.1, 0.9), (0.8, 0.45, 0.6), links=6)
    casings(p, (1.2, 1.1, 0.38))
    plaques(p, (1.5, 0.15), count=3, step=0.3)
    dead_lantern(p, (-1.3, -1.35, 0.34), post=0.7)


def h00B_fountain_of_wonders():
    """Piso de carregamento: bacia de decantação afundada no pavimento morto, placa prateada e jarro de prata."""
    p = pal()
    pad(p)
    fog(p, ((1.3, 1.3, 0.7, 0.5), (1.45, -0.3, 0.5, 0.4), (-1.2, -1.3, 0.8, 0.4)))
    box("paving", p["concrete"], (0.0, 0.0, 0.1), (3.3, 3.3, 0.1), bevel=0.02, rot_z=0.04)
    for x, y, sx, sy in ((0.0, 1.0, 2.2, 0.36), (0.0, -1.0, 2.2, 0.36), (1.0, 0.0, 0.36, 2.2), (-1.0, 0.0, 0.36, 2.2)):
        box("basin_wall", p["concrete_dk"], (x, y, 0.2), (sx, sy, 0.3), bevel=0.03)
    box("basin_oil", p["oil_sheen"], (0.0, 0.0, 0.2), (1.72, 1.72, 0.1), bevel=0.0)
    for x, y in ((-0.3, 0.2), (0.35, -0.3)):
        box("oil_swirl", p["glass_dead"], (x, y, 0.3), (0.5, 0.18, 0.01), bevel=0.0, rot_z=x * 2)
    # Placa prateada na borda, fazendo a separação a frio.
    plate(p, (-1.05, -0.3, 0.5), w=1.5, h=1.45, lean=0.6)
    # Gallows: braço em crescente que carrega o jarro de prata por corrente sobre a bacia.
    beam("gallows_post", p["wood_dk"], (-1.5, 1.3, 0.1), (-1.5, 1.3, 2.4), thick=0.16)
    arc("gallows", p["silver"], (-0.1, 1.3, 1.2), 1.4, 15.0, 125.0, thick=0.2, az=90.0, n=8)
    chain(p, (0.05, 1.3, 2.4), (0.05, 0.4, 1.8), links=0)
    cyl("pitcher", p["silver"], (0.05, 0.35, 1.2), 0.15, 0.32, sides=8, top_radius=0.1, bevel=0.0)
    # Racks de ampolas vazias esperando para serem enchidas; uma cheia no fim.
    for x0, sy in ((-0.75, 1), (-0.75, -1)):
        y = sy * 1.55
        for sx in (0, 1.5):
            box("rack_post", p["wood_dk"], (x0 + sx, y, 0.1), (0.07, 0.07, 0.7), bevel=0.0)
        box("rack_rail", p["wood"], (x0 + 0.75, y, 0.74), (1.6, 0.1, 0.06), bevel=0.0)
        for i in range(7):
            jar(p, (x0 + 0.1 + i * 0.22, y, 0.8), full=(i == 6 and sy < 0), r=0.07, h=0.26)
    # Cacos de vidro nas juntas.
    rnd = random.Random(11)
    for _ in range(14):
        box("grit", p["glass_dead"], (rnd.uniform(-1.6, 1.6), rnd.choice((-1, 1)) * rnd.uniform(1.2, 1.65), 0.2), (0.1, 0.07, 0.03), bevel=0.0, rot_z=rnd.uniform(0, 3))
    casings(p, (1.35, 0.55, 0.2), count=3)
    plaques(p, (1.5, -1.2), count=3, step=0.3)
    dead_lantern(p, (1.4, 1.35, 0.2), post=0.7)


# ---------------------------------------------------------------------------------------------------------
# Siege factory
# ---------------------------------------------------------------------------------------------------------


def h011_siege_factory():
    """Dugout de reparo: berma semicircular de entulho, telhado de chapa corrugada numa metade, pernas de
    guindaste com o gancho em crescente içando um disco do barro."""
    p = pal()
    pad(p)
    fog(p, ((1.35, 1.2, 0.8, 0.5), (1.3, -1.3, 0.7, 0.4), (-0.2, -1.55, 0.8, 0.3)))
    cx = 0.1
    for i in range(9):
        a = math.radians(95 + i * 21.25)
        r = 1.45
        tone = "mud_lt" if i % 2 else "char_lt"
        box("berm", p[tone], (cx + r * math.cos(a), r * math.sin(a), 0.1), (0.85, 0.78, 1.15 - 0.05 * (i % 3)), bevel=0.05, taper=0.55, taper_y=0.6, rot_z=a)
    box("pit", p["oil"], (cx + 0.1, 0.0, 0.1), (1.7, 2.1, 0.04), bevel=0.0)
    for i in range(5):
        box("rail_tie", p["wood_dk"], (-0.3 + i * 0.36, 0.0, 0.12), (0.18, 1.7, 0.06), bevel=0.0)
    # Telhado de chapa corrugada cobrindo só a metade de trás.
    slab("sheet_roof", p["rust"], [(-1.45, 1.55), (0.0, 1.05), (0.0, 1.13), (-1.45, 1.63)], 2.3, center=(0.0, 0.0, 0.0))
    for i in range(8):
        slab("sheet_rib", p["rust_dk"], [(-1.4 + i * 0.19, 1.57 - i * 0.065), (-1.32 + i * 0.19, 1.57 - i * 0.065), (-1.32 + i * 0.19, 1.67 - i * 0.065), (-1.4 + i * 0.19, 1.67 - i * 0.065)], 2.3)
    for y in (-1.0, 1.0):
        box("sheet_post", p["wood_dk"], (-0.05, y, 0.1), (0.12, 0.12, 1.05), bevel=0.0)
    # Pernas de guindaste inclinadas para a frente, gancho em crescente e o disco içado.
    apex = (1.0, 0.0, 3.3)
    for y in (-0.85, 0.85):
        beam("shear_leg", p["wood_dk"], (0.1, y, 0.1), apex, thick=0.16)
    beam("shear_brace", p["wood"], (0.45, -0.58, 1.2), (0.45, 0.58, 1.2), thick=0.08)
    crescent(p, (1.0, 0.0, 3.1), 0.38, thick=0.14, mid=270.0, span=220.0)
    chain(p, (1.0, 0.0, 2.73), (1.0, 0.0, 2.25), links=5)
    cyl("disc", p["silver"], (1.0, 0.07, 1.45), 0.78, 0.14, sides=16, bevel=0.0, rot=("X", math.radians(90)))
    cyl("disc_core", p["silver_dk"], (1.0, 0.08, 1.45), 0.5, 0.18, sides=12, bevel=0.0, rot=("X", math.radians(90)))
    arc("disc_void", p["soot"], (1.0, -0.12, 1.45), 0.34, 200.0, 340.0, thick=0.14, az=90.0, n=6)
    box("mud_clump", p["mud"], (1.0, 0.0, 0.1), (1.3, 0.6, 0.18), bevel=0.04)
    # Magazine de quatro lóbulos num bloco fechado, caixa de discos e a lata de solvente acorrentada.
    box("magazine_case", p["wood_dk"], (1.35, 1.25, 0.1), (0.6, 0.6, 0.34), bevel=0.02)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        cyl("lobe", p["silver_dk"], (1.35 + sx * 0.14, 1.25 + sy * 0.14, 0.44), 0.15, 0.3, sides=8, bevel=0.0)
    box("disc_rack", p["wood"], (-0.2, -1.5, 0.1), (1.0, 0.45, 0.5), bevel=0.02)
    for i in range(3):
        cyl("rack_disc", p["silver"], (-0.5 + i * 0.3, -1.5, 0.62), 0.2, 0.05, sides=8, bevel=0.0, rot=("X", math.radians(90)))
    cyl("solvent_can", p["rust"], (1.45, -0.9, 0.1), 0.17, 0.38, sides=8, bevel=0.0)
    chain(p, (1.45, -0.9, 0.3), (1.2, -0.4, 0.2), links=4)
    casings(p, (0.4, -1.5, 0.1))
    dead_lantern(p, (-1.2, 1.35, 1.6), size=1.0)
    box("lantern_bracket", p["wood_dk"], (-1.2, 1.35, 1.0), (0.07, 0.07, 0.65), bevel=0.0)


# ---------------------------------------------------------------------------------------------------------
# Torre
# ---------------------------------------------------------------------------------------------------------


def h073_elunes_lantern():
    """Mastro de sinal ferroviário fora do prumo: lanterna de vidro morto, prato prateado côncavo no pino e
    a culatra de cartucho de sal de prata ao pé."""
    p = pal()
    pad(p, (2.8, 2.8))
    fog(p, ((1.0, 1.0, 0.7, 0.4), (1.1, -0.9, 0.6, 0.4), (-1.0, -1.1, 0.6, 0.4)))
    box("footing", p["concrete_dk"], (0, 0, 0.1), (1.9, 1.9, 0.3), bevel=0.04, taper=0.9, taper_y=0.9)
    box("breech", p["silver_dk"], (0.15, 0, 0.4), (0.9, 0.8, 0.62), bevel=0.04)
    box("breech_hatch", p["concrete_lt"], (0.62, 0, 0.55), (0.06, 0.5, 0.3), bevel=0.0)
    mast = ((-0.1, 0.0, 0.9), (0.3, 0.0, 3.6))
    beam("mast", p["wood_dk"], mast[0], mast[1], thick=0.24)
    for t in (0.25, 0.55, 0.85):
        c = Vector(mast[0]).lerp(Vector(mast[1]), t)
        ring("mast_ring", p["silver_dk"], (c.x, c.y, c.z), 0.09, 0.07, thick=0.04, sides=6)
    # Lanterna morta grande, no braço, e o prato côncavo prateado inclinado para a lane.
    beam("lantern_arm", p["wood_dk"], (0.25, 0.0, 3.0), (0.55, 0.0, 3.0), thick=0.08)
    dead_lantern(p, (0.6, 0.0, 2.7), size=2.2)
    kit.begin_part("anim_dish")
    cyl("swivel_pin", p["silver_dk"], (0.3, 0.0, 3.55), 0.07, 0.35, sides=6, bevel=0.0)
    cyl("dish", p["silver"], (0.3, 0.0, 3.85), 0.12, 0.45, sides=12, top_radius=0.7, bevel=0.0, rot=("Y", math.radians(38)))
    cyl("lens", p["glass"], (0.3 + 0.2, 0.0, 3.85 + 0.38), 0.05, 0.06, sides=8, top_radius=0.36, bevel=0.0, rot=("Y", math.radians(38)))
    kit.end_part()
    # Rack de três cartuchos carregados presos no mastro e a caixa de cartuchos gastos no pé.
    box("rack_clip", p["rust_dk"], (0.4, 0.0, 1.25), (0.3, 0.6, 0.06), bevel=0.0)
    for y in (-0.2, 0.0, 0.2):
        cyl("cartridge", p["glass"], (0.42, y, 1.3), 0.055, 0.34, sides=6, bevel=0.0)
    crate(p, (0.85, 0.8, 0.1), (0.6, 0.5, 0.34), rot_z=0.3)
    casings(p, (0.75, -0.95, 0.1), count=6)
    for dx in (0.0, 0.2):
        box("salt_crust", p["fog"], (1.0 + dx, 0.3, 0.1), (0.18, 0.2, 0.05), bevel=0.0, rot_z=dx)
    # Estais fora do prumo.
    for ax, ay in ((1.05, 1.05), (1.05, -1.05), (-1.05, 0.2)):
        beam("stay", p["soot"], (0.28, 0.0, 3.3), (ax, ay, 0.1), thick=0.03)
        box("stay_stake", p["wood_dk"], (ax, ay, 0.1), (0.08, 0.08, 0.22), bevel=0.0)
    plaques(p, (-0.95, 0.95), count=3, step=0.3, along="x")


# ---------------------------------------------------------------------------------------------------------
# Utilitários: Silver Glade, os dois obeliscos
# ---------------------------------------------------------------------------------------------------------


def h08P_silver_glade():
    """Banco de acumuladores: anel de tocos prateados com uma jarra de condensado em cada; as cheias brilham,
    as vazias ficam como vagas no rack. O arco de trilho em crescente fecha o fundo."""
    p = pal()
    pad(p)
    fog(p, ((1.3, 1.2, 0.8, 0.5), (1.3, -1.25, 0.7, 0.45), (0.0, 0.0, 0.9, 0.7)))
    cyl("hub_foot", p["concrete_dk"], (0, 0, 0.1), 0.62, 0.14, sides=10, bevel=0.0)
    cyl("hub", p["silver_dk"], (0, 0, 0.24), 0.36, 1.3, sides=8, top_radius=0.26, bevel=0.0)
    cyl("hub_top", p["silver"], (0, 0, 1.54), 0.3, 0.08, sides=8, bevel=0.0)
    full = (1, 1, 1, 1, 1, 0, 1, 0)
    for i in range(8):
        a = math.radians(i * 45 + 22.5)
        x, y = 1.2 * math.cos(a), 1.2 * math.sin(a)
        h = 0.62 + 0.12 * (i % 3)
        cyl("stump", p["silver"] if i % 2 else p["silver_dk"], (x, y, 0.1), 0.26, h, sides=7, top_radius=0.2, bevel=0.0)
        jar(p, (x, y, 0.1 + h), full=bool(full[i]), r=0.15, h=0.4)
        beam("link_wire", p["soot"], (x, y, 0.1 + h + 0.2), (0.0, 0.0, 1.5), thick=0.03)
    # Arco de trilho em crescente atrás do banco, com o preço: jarras estouradas e plaquetas.
    arc("rail_arc", p["silver"], (0.0, 1.6, 0.1), 1.5, 5.0, 175.0, thick=0.2, az=90.0, n=10)
    for dx, dy in ((0.5, -1.45), (0.2, -1.55)):
        box("glass_shard", p["glass_dead"], (dx, dy, 0.1), (0.16, 0.1, 0.04), bevel=0.0, rot_z=dx * 4)
    plaques(p, (1.55, -0.45), count=3, step=0.3)
    dead_lantern(p, (-1.5, 1.25, 0.1), post=0.8)


def h07H_obelisk_of_wilderness():
    """Marco de milhagem: monólito fino de lajes de meio-fio empilhadas com espiral de prata e correntes de oferta."""
    p = pal()
    pad(p, (2.6, 2.6))
    fog(p, ((0.7, 0.7, 0.8, 0.5), (0.8, -0.8, 0.7, 0.45), (-0.8, -0.2, 0.7, 0.4)))
    box("plinth", p["concrete_dk"], (0, 0, 0.1), (1.5, 1.5, 0.3), bevel=0.04, taper=0.85, taper_y=0.85)
    z = 0.4
    for i in range(8):
        w = 0.78 - i * 0.04
        h = 0.42
        box("kerb", p["wood_dk" if i % 2 else "concrete_dk"], (0, 0, z), (w, w * 0.92, h), bevel=0.03, rot_z=0.07 * ((i % 3) - 1))
        z += h - 0.02
    top = z + 0.02
    # Espiral de prata subindo o fuste.
    for k in range(40):
        t = k / 39
        ang = t * math.tau * 2.0
        r = 0.4 - t * 0.14
        box("spiral", p["silver"], (r * math.cos(ang), r * math.sin(ang), 0.5 + t * (top - 0.7)), (0.13, 0.13, 0.13), bevel=0.0, rot_z=ang)
    cyl("cap", p["concrete_lt"], (0, 0, top), 0.34, 0.2, sides=4, top_radius=0.1, bevel=0.0, rot=None)
    crescent(p, (0.0, 0.0, top + 0.55), 0.42, thick=0.14, mid=270.0, span=220.0)
    # Correntes de oferta com placas de latão e a lanterna.
    for a in (-0.7, 0.2, 0.9):
        px, py = 0.5 * math.cos(a), 0.5 * math.sin(a)
        chain(p, (px, py, 1.2), (px * 2.1, py * 2.1, 0.2), links=8)
        box("chain_plaque", p["brass"], (px * 2.1, py * 2.1, 0.2), (0.1, 0.1, 0.12), bevel=0.0)
    plaques(p, (1.1, -0.7), count=4, step=0.3)
    dead_lantern(p, (-1.0, 0.9, 0.1), post=0.7)


def h07I_starfall_obelisk():
    """O dente do poço: a broca-mãe do primeiro derrick, plantada de pé, com lente de vidro frio no topo
    rachado, calha circular de cru ao redor e dentes de aço de tributo."""
    p = pal()
    pad(p)
    fog(p, ((1.4, 0.4, 0.6, 0.4), (0.3, -1.45, 0.7, 0.4), (-1.0, 1.4, 0.6, 0.4)))
    # Calha circular de cru em volta, que esvazia quando a broca dispara.
    n = 14
    for i in range(n):
        a = i * math.tau / n
        box("trough_seg", p["concrete_dk"], (1.45 * math.cos(a), 1.45 * math.sin(a), 0.1), (0.46, 0.5, 0.2), bevel=0.02, rot_z=a)
        if i % 7 != 3:
            box("trough_oil", p["oil"], (1.45 * math.cos(a), 1.45 * math.sin(a), 0.22), (0.36, 0.34, 0.04), bevel=0.0, rot_z=a)
    # Broca tricônica de pé: corpo cônico, coroa de três cones dentados.
    cyl("bit_foot", p["concrete_dk"], (0, 0, 0.1), 0.95, 0.2, sides=9, bevel=0.0)
    cyl("bit_body", p["char"], (0, 0, 0.3), 0.8, 1.2, sides=9, top_radius=0.62, bevel=0.0)
    cyl("bit_collar", p["char_lt"], (0, 0, 1.5), 0.66, 0.18, sides=9, bevel=0.0)
    for k in range(3):
        a = math.radians(k * 120 + 30)
        dx, dy = math.cos(a), math.sin(a)
        base = (dx * 0.28, dy * 0.28, 1.68)
        tip = (dx * 0.55, dy * 0.55, 3.1)
        beam("cone_arm", p["char"], base, tip, thick=0.42)
        for j in range(4):
            t = 0.25 + j * 0.2
            c = Vector(base).lerp(Vector(tip), t)
            ring("cone_teeth", p["silver_dk"], (c.x, c.y, c.z - 0.05), 0.2, 0.08, thick=0.06, sides=6)
        kit.spike(p["silver_dk"], tip, height=0.5, radius=0.16, lean=(dx * 0.12, dy * 0.12))
    # Lente de vidro frio no centro rachado.
    cyl("lens_seat", p["char_lt"], (0, 0, 2.0), 0.3, 0.5, sides=8, top_radius=0.34, bevel=0.0)
    dome("lens", p["glass"], (0, 0, 2.5), 0.32, squash=1.1, sides=8)
    box("crack", p["soot"], (0.02, 0.0, 2.5), (0.04, 0.5, 0.04), bevel=0.0, rot_z=0.6)
    # Dentes de aço e correntes de tributo em volta do pé, cada um uma bomba parada.
    for k in range(6):
        a = math.radians(k * 60 + 15)
        kit.spike(p["silver"], (1.05 * math.cos(a), 1.05 * math.sin(a), 0.1), height=0.5, radius=0.1, lean=(0.05, 0.0))
    chain(p, (0.8, -0.2, 1.1), (1.05, 0.5, 0.25), links=6)
    chain(p, (0.5, 0.7, 1.2), (-0.1, 1.05, 0.25), links=6)
    box("chain_plaque", p["brass"], (1.05, 0.5, 0.25), (0.1, 0.1, 0.12), bevel=0.0)
    casings(p, (1.5, -1.45, 0.1), count=4)
    dead_lantern(p, (-1.5, -1.45, 0.1), post=0.7)


# ---------------------------------------------------------------------------------------------------------
# Casas: Hunter's -> Ranger's -> Amazon's; House -> Guild of Shadows; Pillaged Hut -> Scorched Mansion
# ---------------------------------------------------------------------------------------------------------


def hunter_shed(p, tall=False):
    """Galpão baixo do posto de caça, de tábuas cinza-lilás, com a lona em duas águas. A cumeeira corre em y;
    a frente (parede em x = -0,15) dá para a varanda em +x. tall levanta as paredes para a galeria de tiro."""
    wall_h = 1.4 if tall else 1.0
    box("shed_foot", p["concrete_dk"], (-1.0, 0.0, 0.1), (1.9, 2.6, 0.12), bevel=0.02)
    box("shed", p["wood"], (-1.0, 0.0, 0.2), (1.7, 2.4, wall_h), bevel=0.03)
    for y in (-0.8, 0.0, 0.8):
        box("board_seam", p["wood_dk"], (-0.14, y, 0.25), (0.02, 0.03, wall_h - 0.1), bevel=0.0)
    top = 0.2 + wall_h
    w = 2.7 if tall else 2.3
    prism("tarp_roof", p["blue"], (-1.0, 0.0, top), (w, 2.8, 0.85), ridge=0.5, bevel=0.02)
    prism("tarp_fold", p["blue_dk"], (-1.02, 0.0, top + 0.03), (w - 0.5, 2.9, 0.5), ridge=0.5, bevel=0.0)
    box("ridge_pole", p["silver_dk"], (-1.0, 0.0, top + 0.82), (0.1, 3.0, 0.07), bevel=0.0)
    kit.chimney(p["rust"], p["silver_dk"], p["soot"], (-1.6, -0.95, top + 0.1), 0.95, radius=0.11)
    smoke(p, (-1.6, -0.95, top + 1.15), n=3, step=0.2)
    return top


def h00S_hunters_hall():
    p = pal()
    pad(p)
    fog(p)
    hunter_shed(p)
    # Varanda onde as jovens contam respirações, com a cobertura só numa metade.
    box("porch", p["wood_lt"], (0.8, 0.0, 0.1), (1.9, 2.4, 0.1), bevel=0.02)
    for sy in (-1, 1):
        box("porch_post", p["wood_dk"], (1.55, sy * 1.1, 0.2), (0.1, 0.1, 1.15), bevel=0.0)
    slab("porch_roof", p["blue"], [(-0.2, 1.4), (1.65, 1.0), (1.65, 1.08), (-0.2, 1.48)], 1.2, center=(0.0, 0.65, 0.0))
    # Rack de arcos da lua na metade aberta e fileira de lanternas mortas no beiral.
    for y in (-1.05, -0.15):
        box("bow_rack", p["wood_dk"], (1.1, y, 0.2), (0.07, 0.07, 0.95), bevel=0.0)
    box("bow_rail", p["wood_dk"], (1.1, -0.6, 1.1), (0.07, 1.0, 0.06), bevel=0.0)
    for i in range(3):
        crescent(p, (1.1, -0.9 + i * 0.3, 0.7), 0.26, thick=0.06, mid=180.0, span=170.0)
    for i in range(5):
        dead_lantern(p, (0.12, -1.0 + i * 0.5, 1.1), size=0.7)
    plaques(p, (1.7, -1.1), count=4, step=0.3)
    casings(p, (0.6, 1.45, 0.1))
    dead_lantern(p, (1.55, -1.5, 0.1), post=0.8)


def h03D_rangers_hall():
    p = pal()
    pad(p)
    fog(p)
    hunter_shed(p, tall=True)
    # Galeria de tiro contínua na frente, sobre pernas; balaústres em crescentes de prata.
    for sy in (-1, 1):
        for x in (0.1, 1.5):
            box("gallery_post", p["wood_dk"], (x, sy * 1.1, 0.1), (0.1, 0.1, 1.5), bevel=0.0)
    box("gallery_deck", p["wood_lt"], (0.8, 0.0, 1.55), (1.7, 2.6, 0.1), bevel=0.02)
    box("gallery_rail", p["silver_dk"], (1.6, 0.0, 2.05), (0.07, 2.6, 0.07), bevel=0.0)
    for i in range(7):
        crescent(p, (1.6, -1.2 + i * 0.4, 1.78), 0.19, thick=0.05, mid=90.0, span=180.0)
    # Beiral fundo cobrindo só a metade de trás da galeria.
    slab("deep_eave", p["blue"], [(0.2, 2.15), (1.0, 1.95), (1.0, 2.03), (0.2, 2.23)], 2.0, center=(0.0, 0.0, 0.0))
    # Relicários de vidro frio pendurados sob a viga, um por patrulheira.
    for i in range(5):
        y = -1.0 + i * 0.5
        chain(p, (1.6, y, 1.55), (1.6, y, 1.25), links=2)
        box("reliquary", p["glass"], (1.6, y, 1.0), (0.12, 0.12, 0.26), bevel=0.0)
    # Fardo de palha crivado de flechas de prata no pátio.
    box("target_bale", p["thatch"], (1.35, -1.5, 0.1), (0.5, 0.7, 0.55), bevel=0.04, rot_z=0.2)
    for k in range(4):
        beam("silver_shaft", p["silver"], (1.55, -1.7 + k * 0.1, 0.4 + (k % 2) * 0.1), (1.9, -1.7 + k * 0.1, 0.5 + (k % 2) * 0.1), thick=0.03)
    plaques(p, (1.7, 0.2), count=3, step=0.3)
    dead_lantern(p, (1.7, 1.5, 0.1), post=0.8)
    casings(p, (0.6, 1.45, 0.1))


def h03E_amazons_hall():
    """Toca escavada num monte de rejeito: silhueta baixa e redonda, um só mastro de estandarte."""
    p = pal()
    pad(p)
    fog(p, ((1.4, 1.2, 0.8, 0.5), (1.45, -1.2, 0.7, 0.45), (0.0, 1.6, 0.8, 0.3)))
    dome("heap", p["mud_lt"], (-0.35, 0.0, 0.1), 1.75, squash=0.6, sides=12)
    dome("heap_cap", p["char_lt"], (-0.55, 0.2, 0.9), 0.95, squash=0.55, sides=9)
    for x, y, r in ((0.2, 1.3, 0.5), (0.1, -1.4, 0.55), (-1.3, -0.9, 0.5)):
        dome("tailing", p["char_lt" if r > 0.5 else "mud_lt"], (x, y, 0.1), r, squash=0.6, sides=8)
    # Sucata do mundo servindo de teto: chapas e tambores saindo do monte.
    box("scrap_plate", p["rust"], (-0.9, -0.3, 0.95), (0.9, 0.7, 0.07), bevel=0.0, rot_z=0.5)
    cyl("scrap_drum", p["rust_dk"], (-1.2, 0.8, 0.5), 0.2, 0.55, sides=8, bevel=0.0, rot=("Y", math.radians(70)))
    # Boca da toca com moldura e escuridão.
    box("den_mouth", p["soot"], (1.1, 0.0, 0.1), (0.5, 1.0, 0.9), bevel=0.0, taper=0.85, taper_y=0.9)
    for sy in (-1, 1):
        box("den_post", p["wood_dk"], (1.38, sy * 0.58, 0.1), (0.14, 0.14, 1.05), bevel=0.0)
    box("den_lintel", p["wood_dk"], (1.38, 0.0, 1.05), (0.16, 1.4, 0.14), bevel=0.0)
    # Moldura de troféu: três rodas de válvula roubadas e um arco partido.
    for sy in (-1, 1):
        beam("frame_leg", p["wood_dk"], (1.7, sy * 1.15, 0.1), (1.55, sy * 1.0, 1.9), thick=0.1)
    beam("frame_bar", p["wood_dk"], (1.55, -1.0, 1.85), (1.55, 1.0, 1.85), thick=0.1)
    for i, y in enumerate((-0.6, 0.0, 0.6)):
        valve_wheel(p, (1.45, y, 1.35), 0.26 if i != 1 else 0.3, az=90.0, tone="silver_dk")
    arc("broken_bow", p["wood_lt"], (1.75, 0.0, 0.1), 0.45, 20.0, 110.0, thick=0.05, az=0.0, n=4, taper=False)
    # Mastro único: capa rasgada com o crescente de prata costurado.
    beam("banner_pole", p["wood_dk"], (-0.5, 0.2, 0.9), (-0.5, 0.2, 3.9), thick=0.13)
    slab("banner", p["violet"], [(0.0, 0.0), (0.8, 0.0), (0.55, -0.35), (0.8, -0.8), (0.0, -0.9)], 0.04, center=(-0.5, 0.2, 3.85))
    crescent(p, (-0.2, 0.17, 3.5), 0.2, thick=0.06, mid=0.0, span=200.0)
    dead_lantern(p, (1.7, 0.0, 0.1), size=1.0)
    plaques(p, (1.2, 1.4), count=3, step=-0.3, along="x")
    casings(p, (1.05, -1.45, 0.1))


def h07M_house_of_shadows():
    """Meia-água encostada numa árvore morta, cuja copa seca serve de sapé; porta baixa e crescentes sobre ela."""
    p = pal()
    pad(p)
    fog(p, ((1.3, 1.2, 0.8, 0.5), (1.4, -1.0, 0.6, 0.45), (-0.5, -1.45, 0.8, 0.3)))
    # Árvore morta: tronco torto e galhos secos.
    beam("trunk", p["wood_dk"], (-1.25, 0.45, 0.1), (-1.0, 0.3, 3.3), thick=0.3)
    for (dx, dy, dz) in ((0.7, 0.4, 0.8), (-0.5, 0.8, 0.7), (0.4, -0.8, 0.8), (-0.8, -0.5, 0.6), (0.1, 0.1, 0.5)):
        tip = (-1.05 + dx, 0.32 + dy, 2.9 + dz)
        beam("branch", p["wood_dk"], (-1.05, 0.32, 2.9), tip, thick=0.11)
        for tx, ty in ((0.3, 0.15), (-0.15, 0.3)):
            beam("twig", p["wood_dk"], tip, (tip[0] + tx, tip[1] + ty, tip[2] + 0.3), thick=0.06)
    # Corpo em meia-água.
    for sy in (-1, 1):
        slab("side_wall", p["wood"], [(-1.1, 0.1), (0.6, 0.1), (0.6, 1.0), (-1.1, 2.1)], 0.1, center=(0.0, sy * 1.1, 0.0))
    box("back_wall", p["wood_dk"], (-1.1, 0.0, 0.1), (0.12, 2.3, 2.0), bevel=0.0)
    for y in (-0.45, 0.45):
        box("front_wall", p["wood"], (0.55, y * 1.6, 0.1), (0.12, 0.7, 0.9), bevel=0.0)
    box("door_lintel", p["wood_dk"], (0.55, 0.0, 0.62), (0.14, 1.0, 0.38), bevel=0.0)
    box("door_dark", p["soot"], (0.5, 0.0, 0.1), (0.1, 0.8, 0.55), bevel=0.0)
    # Telhado de sapé da copa seca, em declive para a porta, com um dormer vedado de lona.
    slab("thatch_roof", p["thatch"], [(-1.2, 2.2), (0.8, 1.0), (0.8, 1.2), (-1.2, 2.4)], 2.5, center=(0.0, 0.0, 0.0), bevel=0.0)
    for i in range(5):
        beam("thatch_bunch", p["thatch"], (-0.9 + i * 0.4, -1.2, 1.95 - i * 0.28), (-0.9 + i * 0.4, 1.2, 1.95 - i * 0.28), thick=0.12)
    prism("dormer", p["blue"], (-0.35, 0.0, 1.62), (0.7, 0.8, 0.55), ridge=0.5, bevel=0.0, rot_z=0.0)
    # Tábua da casa com três crescentes e a lanterna morta de cabeça para baixo no gancho do poste.
    box("house_board", p["wood_lt"], (0.66, 0.0, 1.05), (0.08, 1.4, 0.3), bevel=0.0)
    for y in (-0.45, 0.0, 0.45):
        crescent(p, (0.74, y, 1.2), 0.1, thick=0.03, mid=270.0, span=200.0, az=0.0)
    beam("hook_post", p["wood_dk"], (1.05, 1.2, 0.1), (1.05, 1.2, 1.5), thick=0.08)
    beam("hook_arm", p["wood_dk"], (1.05, 1.2, 1.5), (1.05, 0.95, 1.55), thick=0.05)
    dead_lantern(p, (1.05, 0.95, 1.2), size=1.0, inverted=True)
    # Tábuas soltas com pregos à mostra no pé: armadilha visual.
    for i, (x, y, r) in enumerate(((1.15, -0.5, 0.4), (1.4, 0.2, -0.3), (1.0, -1.2, 0.9))):
        box("loose_board", p["wood_lt"], (x, y, 0.1), (0.7, 0.16, 0.05), bevel=0.0, rot_z=r)
        kit.spike(p["silver_dk"], (x + 0.1, y, 0.15), height=0.2, radius=0.03)
    plaques(p, (1.55, 0.7), count=3, step=0.3)
    casings(p, (1.5, -1.35, 0.1))


def h07L_guild_of_shadows():
    """Pilha torta de três caixas de tábua, cada andar fora de prumo com o de baixo; janelas de postigo,
    cata-vento em crescente, sino sem badalo e um fio de fumaça na cumeeira."""
    p = pal()
    pad(p, (3.0, 3.0))
    fog(p, ((1.15, 1.1, 0.7, 0.5), (1.2, -1.1, 0.6, 0.45), (-0.9, -1.3, 0.7, 0.35)))
    floors = ((2.0, 2.0, 0.95, 0.0, 0.0, 0.0, "wood"), (1.8, 1.9, 0.9, -0.12, 0.15, 0.12, "wood_lt"), (1.6, 1.7, 0.85, 0.1, -0.12, -0.1, "wood"))
    z = 0.1
    for k, (sx, sy, h, ox, oy, rz, tone) in enumerate(floors):
        box("floor", p[tone], (ox, oy, z), (sx, sy, h), bevel=0.03, rot_z=rz)
        box("floor_band", p["wood_dk"], (ox, oy, z + h - 0.06), (sx + 0.06, sy + 0.06, 0.1), bevel=0.0, rot_z=rz)
        for dy in (-0.45, 0.45):
            bx, by = rot2(sx / 2 + 0.01, dy, rz)
            box("board_seam", p["wood_dk"], (ox + bx, oy + by, z + 0.1), (0.02, 0.03, h - 0.2), bevel=0.0, rot_z=rz)
        for dy in (-0.5, 0.5):
            if k == 0 and abs(dy) < 0.6 and dy > 0:
                continue
            bx, by = rot2(sx / 2, dy, rz)
            box("port_frame", p["silver_dk"], (ox + bx + 0.02, oy + by, z + h * 0.35), (0.06, 0.34, 0.32), bevel=0.0, rot_z=rz)
            box("port_shutter", p["soot"], (ox + bx + 0.05, oy + by, z + h * 0.35 + 0.03), (0.04, 0.26, 0.24), bevel=0.0, rot_z=rz)
        z += h
    # Telhado e cata-vento em crescente de prata.
    prism("roof", p["blue_dk"], (0.1, -0.12, z), (1.75, 1.9, 0.55), ridge=0.5, bevel=0.02, rot_z=-0.1)
    beam("vane_pole", p["silver_dk"], (0.1, -0.12, z + 0.5), (0.1, -0.12, z + 1.1), thick=0.06)
    kit.begin_part("anim_vane")
    crescent(p, (0.1, -0.12, z + 1.25), 0.36, thick=0.11, mid=0.0, span=210.0)
    kit.end_part()
    smoke(p, (-0.55, -0.4, z + 0.2), n=3, step=0.22)
    # Porta baixa no térreo; o sino sem badalo sob o beiral do segundo andar.
    box("door", p["soot"], (1.02, 0.0, 0.1), (0.1, 0.55, 0.62), bevel=0.0)
    box("door_frame", p["wood_dk"], (1.0, 0.0, 0.72), (0.12, 0.7, 0.08), bevel=0.0)
    beam("bell_arm", p["wood_dk"], (0.95, 0.75, 1.7), (1.3, 0.75, 1.75), thick=0.05)
    kit.begin_part("anim_bell")
    cyl("bell", p["silver"], (1.3, 0.75, 1.4), 0.14, 0.26, sides=7, top_radius=0.06, bevel=0.0)
    kit.end_part()
    plaques(p, (1.4, -1.1), count=4, step=0.3)
    casings(p, (1.35, 1.2, 0.1))
    dead_lantern(p, (-1.3, 1.3, 0.1), post=0.9)


def h07O_pillaged_hut():
    """Cabana da primeira chacina: telhado afundado, caibros como costelas, uma só parede de pé quebrando a cumeeira."""
    p = pal()
    pad(p)
    fog(p, ((1.3, 1.0, 0.8, 0.5), (1.3, -1.1, 0.7, 0.4), (-0.3, 1.5, 0.8, 0.3)))
    wide = 2.5
    box("ash_floor", p["char"], (-0.3, 0.0, 0.1), (wide, wide, 0.03), bevel=0.0)
    slab("side_wall", p["char_lt"], [(-1.55, 0.1), (0.95, 0.1), (0.95, 0.45), (0.0, 0.8), (-1.55, 1.05)], 0.14, center=(0.0, -wide / 2, 0.0))
    # A parede de pé, com a empena (y negativo, virada para a câmera).
    box("gable_wall", p["char_lt"], (-0.3, wide / 2 - 0.08, 0.1), (wide, 0.16, 1.35), bevel=0.02)
    prism("gable", p["char_lt"], (-0.3, wide / 2 - 0.08, 1.45), (wide, 0.16, 1.05), ridge=0.45, bevel=0.0)
    box("gable_window", p["soot"], (-0.3, wide / 2 - 0.18, 0.7), (0.36, 0.1, 0.4), bevel=0.0)
    # Costelas de caibro: arcos parciais atravessando o vão.
    for i, x in enumerate((-1.0, -0.4, 0.2, 0.7)):
        arc("rib", p["char"], (x, 0.0, 0.1), 1.15, 18.0 + (i % 2) * 8, 150.0, thick=0.1, az=0.0, n=7, taper=False)
    # Telhado afundado: dois panos mergulhando para dentro.
    slab("sunk_roof", p["wood_dk"], [(-0.9, 1.0), (-0.1, 0.45), (-0.1, 0.53), (-0.9, 1.08)], 0.9, center=(0.0, 0.5, 0.0), rot_z=0.0)
    slab("sunk_roof", p["wood_dk"], [(0.3, 0.7), (1.0, 0.25), (1.0, 0.33), (0.3, 0.78)], 0.8, center=(0.0, -0.1, 0.0))
    # Poste torto com a lanterna morta balançando, pilha de pertences queimados e a plaqueta única.
    beam("lean_post", p["wood_dk"], (1.4, 1.2, 0.1), (1.25, 1.1, 2.0), thick=0.1)
    beam("lean_arm", p["wood_dk"], (1.25, 1.1, 2.0), (1.45, 0.85, 1.95), thick=0.05)
    dead_lantern(p, (1.45, 0.85, 1.6), size=1.1, inverted=True)
    for x, y, s in ((0.7, 0.2, 0.5), (0.9, -0.2, 0.4), (0.5, -0.4, 0.35)):
        box("burnt_pile", p["char"], (x, y, 0.1), (s, s * 0.9, s * 0.6), bevel=0.04, rot_z=x * 3)
    box("brass_plaque", p["brass"], (0.95, 0.0, 0.5), (0.2, 0.14, 0.04), bevel=0.0, rot_z=0.3)
    smoke(p, (0.3, 0.1, 0.5), n=3, step=0.2)
    plaques(p, (1.65, -0.9), count=3, step=0.3)
    casings(p, (1.4, -1.45, 0.1), count=2)


def h07N_scorched_mansion():
    """Mansão do mestre de obras queimada: uma só empena de pé com um buraco em crescente por onde entra a
    luz fria, corrente pesada da empena ao chão, a roda trincada da auréola e cacos de vidro no piso."""
    p = pal()
    pad(p)
    fog(p, ((1.4, 1.1, 0.8, 0.5), (1.4, -0.7, 0.7, 0.4), (0.0, 1.55, 0.8, 0.3)))
    wide = 2.9
    box("ash_floor", p["oil"], (-0.2, 0.0, 0.1), (wide, wide, 0.03), bevel=0.0)
    box("hall_floor", p["concrete_dk"], (-0.2, 0.0, 0.08), (wide + 0.1, wide + 0.1, 0.06), bevel=0.0)
    # Empena única de pé, no lado da câmera, em concreto chamuscado.
    fy = wide / 2 - 0.2  # face da empena virada para a câmera
    box("gable_wall", p["concrete"], (-0.2, wide / 2 - 0.1, 0.1), (wide, 0.2, 2.0), bevel=0.03)
    prism("gable", p["concrete"], (-0.2, wide / 2 - 0.1, 2.1), (wide, 0.2, 1.7), ridge=0.5, bevel=0.0)
    for x in (-1.1, 0.7):
        box("gable_window", p["soot"], (x, fy - 0.02, 0.9), (0.4, 0.12, 0.8), bevel=0.0)
        box("window_sill", p["concrete_dk"], (x, fy - 0.04, 0.85), (0.5, 0.16, 0.07), bevel=0.0)
    # O furo em crescente, com a luz fria atravessando.
    arc("hole_dark", p["soot"], (-0.2, fy - 0.02, 2.6), 0.55, 110.0, 340.0, thick=0.5, az=90.0, n=12)
    arc("hole_light", p["glass"], (-0.2, fy - 0.1, 2.6), 0.55, 130.0, 320.0, thick=0.3, az=90.0, n=12)
    # Paredes laterais quebradas e caibros tombados.
    slab("side_wall", p["concrete_dk"], [(-1.6, 0.1), (1.2, 0.1), (1.2, 0.5), (0.2, 0.95), (-1.6, 1.2)], 0.16, center=(0.0, -wide / 2 + 0.1, 0.0))
    for ang, ln in ((0.3, 1.9), (-0.4, 1.4)):
        beam("fallen_beam", p["char"], (-0.7, 0.3, 0.12), (-0.7 + ln * math.cos(ang), 0.3 + ln * math.sin(ang), 0.9), thick=0.13)
    beam("fallen_beam", p["char"], (0.3, -0.9, 0.12), (0.9, 0.3, 0.55), thick=0.12)
    # Corrente pesada da empena ao chão e a roda trincada caída no entulho.
    chain(p, (0.9, fy - 0.1, 2.6), (0.9, fy - 0.45, 0.3), links=16)
    valve_wheel(p, (0.5, -0.55, 0.55), 0.42, az=70.0, tone="silver_dk")
    box("wheel_rubble", p["char"], (0.4, -0.5, 0.1), (0.7, 0.5, 0.25), bevel=0.04, rot_z=0.5)
    rnd = random.Random(5)
    for _ in range(16):
        box("grit", p["glass_dead"], (rnd.uniform(-1.4, 1.2), rnd.uniform(-1.0, 1.2), 0.12), (0.1, 0.07, 0.03), bevel=0.0, rot_z=rnd.uniform(0, 3))
    plaques(p, (1.65, -0.5), count=4, step=0.3)
    casings(p, (1.45, 1.4, 0.1), count=2)
    dead_lantern(p, (1.4, 1.2, 0.1), post=0.8)
    smoke(p, (-0.5, 0.5, 0.3), n=2, step=0.2)


BUILDINGS = {
    "h088": h088_moon_shrine,
    "h07D": h07D_moon_altar,
    "h00B": h00B_fountain_of_wonders,
    "h011": h011_siege_factory,
    "h073": h073_elunes_lantern,
    "h08P": h08P_silver_glade,
    "h07H": h07H_obelisk_of_wilderness,
    "h07I": h07I_starfall_obelisk,
    "h00S": h00S_hunters_hall,
    "h03D": h03D_rangers_hall,
    "h03E": h03E_amazons_hall,
    "h07M": h07M_house_of_shadows,
    "h07L": h07L_guild_of_shadows,
    "h07O": h07O_pillaged_hut,
    "h07N": h07N_scorched_mansion,
}


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["all"]
    names = list(BUILDINGS) if args[0] == "all" else [args[0]]
    out_dir = game_paths.out_arg(args, "--out", "buildings", "nightelf")
    render_dir = args[args.index("--render") + 1] if "--render" in args else ""
    for name in names:
        kit.build(name, out_dir, render_dir, make=BUILDINGS[name], views=(("front", -35.0), ("game", -90.0)))


if __name__ == "__main__":
    main()
