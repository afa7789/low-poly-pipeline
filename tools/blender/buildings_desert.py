"""Prédios da raça Desert modelados por script (redesenho de reports/design/race-desert.md): um GLB por prédio.

Uso:
    blender -b --factory-startup --python tools/blender/buildings_desert.py -- <id|all> [--out DIR] [--render DIR]

O Poço a Céu Aberto: 1859 apodrecendo à luz do dia. Cunha larga de areia cozida e lona crua cortada por UM mastro
fino (torre de perfuração, chaminé, cano, biruta); a lama de piche engole a base. Todo prédio mostra um circuito de
fluido (jarra, mangueira, calha, poço) e esconde a boca atrás de lona, ferro ou válvula. Um só acento saturado, a
Chama de Poço, em cada prédio. Sem verde, sem latão, sem brilho. Pegada ~3,5 x 3,5 centrada na origem, a porta
virada para +x; o jogo normaliza o tamanho, põe o prédio no plinto do time e desenha a bandeira.
"""

import itertools
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_paths  # noqa: E402
import map_castles as kit
from map_castles import beam, box, cyl, dome, mat, prism, ring
from map_scenery import wire_coil


def pal():
    """Paleta do doc com o valor suspenso: a luz do jogo escurece, então paredes médias-claras e topos claros."""
    return {
        "sand": mat("baked_sand", 0xDDBE84),
        "sand_lt": mat("sand_light", 0xEBD6A4),
        "sand_dk": mat("sand_dark", 0xB89862),
        "canvas": mat("raw_canvas", 0xD2C4A6),
        "canvas_dk": mat("canvas_dark", 0xA39577),
        "palm": mat("date_palm", 0x9A805B),
        "palm_dk": mat("date_palm_dark", 0x6F5C42),
        "iron": mat("tower_iron", 0x8A877E),
        "iron_dk": mat("tower_iron_dark", 0x57544C),
        "pitch": mat("well_pitch", 0x27221B),
        "mud": mat("pitch_mud", 0x7E6B4E),
        "flame": mat("well_flame", 0xE0602F, emit=3.0),
    }


# ---------------------------------------------------------------------------------------------------------
# Peças da raça
# ---------------------------------------------------------------------------------------------------------


def pad(p, size=(3.5, 3.5)):
    """Chão do posto, do tamanho do conteúdo: laje sobrando encolhe o prédio na tela."""
    box("pad", p["mud"], (0, 0, 0), (size[0], size[1], 0.1), bevel=0.03)


def dust(p, size, h=0.3, taper=0.85, center=(0.0, 0.0)):
    """Poeira de duna até o joelho: a base larga em que o prédio está enterrado."""
    box("dust", p["sand_dk"], (center[0], center[1], 0.1), (size[0], size[1], h), bevel=0.06, taper=taper, taper_y=taper)


def plate(name, material, a, b, width, thick, hint=(1.0, 0.0, 0.0)):
    """Placa achatada de a até b: largura no plano, espessura ao longo de `hint` (a normal da face)."""
    a, b = Vector(a), Vector(b)
    axis = b - a
    length = axis.length
    axis.normalize()
    h = Vector(hint)
    y = (h - axis * h.dot(axis)).normalized()
    x = y.cross(axis)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= width
        v.co.y *= thick
        v.co.z = (v.co.z + 0.5) * length
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix((x, y, axis)).transposed())
    bmesh.ops.translate(bm, verts=bm.verts, vec=a)
    return kit._finish(bm, name, material)


def jar(p, pos, r=0.15, h=0.32):
    """Jarra de piche com cinta de lona e tampa de ferro: o circuito de fluido em miniatura."""
    x, y, z = pos
    cyl("jar", p["pitch"], (x, y, z), r, h, sides=8, top_radius=r * 0.8, bevel=0.0)
    ring("jar_strap", p["canvas_dk"], (x, y, z + h * 0.5), r * 0.88, 0.06, thick=0.03, sides=8)
    cyl("jar_lid", p["iron"], (x, y, z + h), r * 0.55, 0.05, sides=8, bevel=0.0)


def hose(p, pts, thick=0.06):
    for a, b in itertools.pairwise(pts):
        beam("hose", p["pitch"], a, b, thick=thick)


def sump(p, pos, r=0.4):
    """Poço de piche raso, com a borda de areia."""
    x, y, z = pos
    cyl("sump_rim", p["sand_dk"], (x, y, z), r + 0.1, 0.05, sides=10, bevel=0.0)
    cyl("sump", p["pitch"], (x, y, z), r, 0.07, sides=10, bevel=0.0)


def drum(p, pos, tone="iron", h=0.5, r=0.22):
    """Tambor de trilho-tanque: o ferro cintado de sempre."""
    x, y, z = pos
    cyl("drum", p[tone], (x, y, z), r, h, sides=8, bevel=0.0)
    for f in (0.25, 0.7):
        ring("drum_band", p["iron_dk"], (x, y, z + h * f), r, 0.05, thick=0.02, sides=8)


def lying_drum(p, pos, length=0.8, r=0.24, tone="iron"):
    """Tambor deitado ao longo de x, a partir de pos (centro do eixo)."""
    x, y, z = pos
    cyl("drum", p[tone], (x, y, z), r, length, sides=8, bevel=0.0, rot=("Y", math.radians(90)))
    for f in (0.2, 0.75):
        cyl("drum_band", p["iron_dk"], (x + length * f, y, z), r + 0.025, 0.07, sides=8, bevel=0.0, rot=("Y", math.radians(90)))


def flame_lamp(p, pos, size=0.25, post=0.0):
    """A Chama de Poço: o único acento saturado. post > 0 põe a lâmpada num poste de palmeira."""
    x, y, z = pos
    if post > 0.0:
        box("lamp_post", p["palm_dk"], (x, y, z), (0.07, 0.07, post), bevel=0.0)
        z += post
    box("lamp_base", p["iron_dk"], (x, y, z), (0.2, 0.2, 0.05), bevel=0.0)
    kit.flame(p["flame"], p["flame"], (x, y, z + 0.05), size)


def grate(p, x, half_w, z0, z1, cy=0.0, bars=6):
    """Grade de ferro sobre a boca (virada para +x)."""
    for i in range(bars):
        y = cy - half_w + 2 * half_w * i / (bars - 1)
        box("grate_bar", p["iron_dk"], (x, y, z0), (0.05, 0.05, z1 - z0), bevel=0.0)
    for z in (z0, z1 - 0.06):
        box("grate_rail", p["iron_dk"], (x, cy, z), (0.07, 2 * half_w + 0.06, 0.06), bevel=0.0)


def curtain(p, x, cy, half_w, z_top, drop, n=5, tone="canvas"):
    """Cortina de lona em tiras de comprimentos desiguais, presa a uma vara de palmeira."""
    w = 2 * half_w / n
    for i in range(n):
        d = drop * (0.78 + 0.22 * ((i * 7) % 3) / 2)
        box("curtain", p[tone], (x, cy - half_w + w * (i + 0.5), z_top - d), (0.05, w * 0.92, d), bevel=0.0)
    box("curtain_rod", p["palm_dk"], (x, cy, z_top), (0.08, 2 * half_w + 0.1, 0.07), bevel=0.0)


def valve_wheel(p, pos, r=0.3, flat=False, tone="iron_dk"):
    """Volante de válvula: aro de 8 vigas, dois raios e cubo. flat deita o volante (visto de cima)."""
    x, y, z = pos

    def at(a, rad):
        if flat:
            return (x + rad * math.cos(a), y + rad * math.sin(a), z)
        return (x, y + rad * math.cos(a), z + rad * math.sin(a))

    for i in range(8):
        beam("wheel_rim", p[tone], at(i * math.tau / 8, r), at((i + 1) * math.tau / 8, r), thick=0.06)
    for a in (0.0, math.pi / 2):
        beam("wheel_spoke", p[tone], at(a, r), at(a + math.pi, r), thick=0.05)
    box("wheel_hub", p["iron"], (x, y, z - 0.05), (0.12, 0.12, 0.1), bevel=0.0)


def lying_reel(p, pos, r=0.45, length=1.0, tone="iron_dk"):
    """Carretel de arame deitado ao longo de y, a partir de pos: núcleo de arame e dois flanges."""
    x, y, z = pos
    cyl("reel_wire", p["iron"], (x, y, z), r * 0.8, length, sides=10, bevel=0.0, rot=("X", math.radians(-90)))
    for off in (0.0, length - 0.06):
        cyl("reel_flange", p[tone], (x, y + off, z), r, 0.06, sides=10, bevel=0.0, rot=("X", math.radians(-90)))


def tripod(p, base, apex, spread, tone="palm"):
    """Tripé de derrick de palmeira: três pernas de pontos no chão ao redor de base até o ápice."""
    for i in range(3):
        a = math.radians(90 + i * 120)
        beam("tripod_leg", p[tone], (base[0] + spread * math.cos(a), base[1] + spread * math.sin(a), base[2]), apex, thick=0.12)
    for z in (0.35, 0.65):
        pts = []
        for i in range(3):
            a = math.radians(90 + i * 120)
            f = 1 - z * (apex[2] - base[2]) / (apex[2] - base[2])
            pts.append((base[0] + spread * f * math.cos(a), base[1] + spread * f * math.sin(a), base[2] + z * (apex[2] - base[2])))
        for i in range(3):
            beam("tripod_tie", p["palm_dk"], pts[i], pts[(i + 1) % 3], thick=0.06)


# ---------------------------------------------------------------------------------------------------------
# Tenda -> Cabana de fogo (gnolls)
# ---------------------------------------------------------------------------------------------------------


def tent_body(p):
    """Tenda de lona em A com a cumeeira ao longo de x, a porta (triângulo de piche) na empena +x, e o fecho cosido."""
    prism("tent", p["canvas"], (-0.25, 0, 0.1), (2.7, 2.9, 1.6), ridge=0.5, rot_z=math.radians(90), bevel=0.03)
    prism("tent_hem", p["canvas_dk"], (-0.25, 0, 0.1), (2.78, 0.3, 0.22), ridge=0.5, rot_z=math.radians(90), bevel=0.0)
    prism("tent_door", p["pitch"], (1.22, 0, 0.1), (0.95, 0.06, 1.0), ridge=0.5, rot_z=math.radians(90), bevel=0.0)


def jar_rack(p, y=-1.5):
    """Estante de jarras de ombro: duas prateleiras de palmeira com jarras de piche."""
    for x in (-0.95, 0.35):
        box("rack_post", p["palm_dk"], (x, y, 0.1), (0.08, 0.08, 0.85), bevel=0.0)
    box("rack_shelf", p["palm"], (-0.3, y, 0.5), (1.5, 0.34, 0.06), bevel=0.0)
    for i in range(4):
        jar(p, (-0.85 + i * 0.35, y, 0.56), r=0.12, h=0.28)


def g_n02p_gnoll_tent():
    """Tenda larga de lona sobre um tripé de derrick de palmeira: o mastro único é o ápice do tripé, com cabo de ferro."""
    p = pal()
    pad(p)
    tent_body(p)
    tripod(p, (-0.3, 0, 0.1), (-0.3, 0, 3.0), 1.6)
    beam("mast_tip", p["iron_dk"], (-0.3, 0, 3.0), (-0.3, 0, 3.55), thick=0.07)
    beam("cable", p["iron"], (-0.3, 0, 3.0), (1.55, 1.15, 0.12), thick=0.035)
    jar_rack(p)
    sump(p, (1.5, -0.95, 0.1), r=0.3)
    hose(p, [(0.3, -1.4, 0.55), (0.8, -1.5, 0.2), (1.5, -1.2, 0.18), (1.5, -1.0, 0.18)])
    flame_lamp(p, (1.55, 0.7, 0.1), size=0.2, post=0.55)
    for s in (-1, 1):
        box("door_flap", p["canvas_dk"], (1.3, s * 0.34, 0.1), (0.05, 0.36, 0.78), bevel=0.0)


def g_n02n_fire_gnoll_hut():
    """Mesma tenda, agora com a chaminé de tocha alta no fundo e a chama na ponta; calha de imersão e dupla aba na porta."""
    p = pal()
    pad(p)
    tent_body(p)
    cyl("flare_base", p["iron_dk"], (-1.0, 0, 0.1), 0.26, 0.2, sides=8, bevel=0.0)
    cyl("flare", p["iron"], (-1.0, 0, 0.3), 0.14, 3.2, sides=8, bevel=0.0)
    for z in (1.4, 2.4):
        ring("flare_band", p["iron_dk"], (-1.0, 0, z), 0.14, 0.08, thick=0.03, sides=8)
    kit.flame(p["flame"], p["flame"], (-1.0, 0, 3.5), 0.38)
    for sy in (-1, 1):
        beam("flare_stay", p["palm_dk"], (-1.0, sy * 0.1, 2.6), (-0.3, sy * 1.4, 0.12), thick=0.06)
    jar_rack(p)
    for i in range(3):
        jar(p, (0.6 + i * 0.3, 1.5, 0.1), r=0.13, h=0.3)
    box("dip_trough", p["palm"], (1.45, -0.5, 0.1), (0.5, 1.1, 0.3), bevel=0.02)
    box("dip_pitch", p["pitch"], (1.45, -0.5, 0.38), (0.38, 0.95, 0.03), bevel=0.0)
    hose(p, [(0.3, -1.4, 0.6), (1.0, -1.3, 0.45), (1.4, -0.9, 0.42)])
    hose(p, [(0.75, 1.4, 0.3), (1.1, 0.9, 0.2), (1.45, -0.1, 0.4)])
    for s in (-1, 1):
        box("door_flap", p["canvas_dk"], (1.3, s * 0.28, 0.1), (0.05, 0.4, 0.82), bevel=0.0)
        box("door_flap2", p["canvas"], (1.34, -s * 0.12, 0.1), (0.04, 0.3, 0.7), bevel=0.0)


# ---------------------------------------------------------------------------------------------------------
# Ninhos das harpias: n02Q -> n03B | n031
# ---------------------------------------------------------------------------------------------------------


def nest_bowl(p, center, r_top, r_bot, z0, h, n=12, tone="palm", gap=True):
    """Tigela de gravetos e arame: n varas do aro de baixo ao de cima, duas cintas de arame, e fundo de lona com poço."""
    cx, cy = center
    for i in range(n):
        a = i * math.tau / n
        if gap and i == 0:
            continue
        b0 = (cx + r_bot * math.cos(a), cy + r_bot * math.sin(a), z0)
        b1 = (cx + r_top * math.cos(a + 0.12), cy + r_top * math.sin(a + 0.12), z0 + h)
        beam("nest_stick", p[tone], b0, b1, thick=0.1)
    for f, tn in ((0.45, "iron_dk"), (1.0, "iron")):
        r = r_bot + (r_top - r_bot) * f
        z = z0 + h * f
        for i in range(n):
            if gap and i == 0:
                continue
            a0, a1 = i * math.tau / n + 0.12 * f, (i + 1) * math.tau / n + 0.12 * f
            beam("nest_wire", p[tn], (cx + r * math.cos(a0), cy + r * math.sin(a0), z), (cx + r * math.cos(a1), cy + r * math.sin(a1), z), thick=0.05)
    cyl("nest_floor", p["canvas_dk"], (cx, cy, z0), r_bot, 0.08, sides=n, bevel=0.0)
    cyl("nest_lining", p["canvas"], (cx, cy, z0 + 0.05), r_bot * 0.82, 0.05, sides=n, bevel=0.0)


def wire_veil(p, x, cy, half_w, z0, z1, n=6):
    """Véu de arame pendurado sobre a boca do ninho."""
    for i in range(n):
        y = cy - half_w + 2 * half_w * i / (n - 1)
        box("veil_bar", p["iron_dk"], (x, y, z0), (0.04, 0.04, z1 - z0), bevel=0.0)
    box("veil_top", p["iron"], (x, cy, z1), (0.06, 2 * half_w + 0.08, 0.06), bevel=0.0)
    box("veil_rag", p["canvas_dk"], (x + 0.02, cy, z1 - 0.3), (0.04, half_w * 1.2, 0.3), bevel=0.0)


def g_n02q_harpy_nest():
    """Anel baixo de gravetos e arame pendurado num único espeto torto de derrick; farrapo de chama na ponta."""
    p = pal()
    pad(p)
    dust(p, (3.2, 3.2), h=0.32, taper=0.88)
    nest_bowl(p, (0.15, 0), 1.45, 1.0, 0.34, 0.7)
    sump(p, (0.15, 0, 0.4), r=0.35)
    veil_x = 0.15 + 1.45 * math.cos(0.12) * 0.98
    wire_veil(p, veil_x, 0.0, 0.5, 0.42, 1.0)
    # O espeto torto: três lances, o último dobrando para fora, com a jarra pendurada.
    pts = [(-1.05, -1.0, 0.25), (-0.95, -0.7, 1.4), (-0.5, -0.2, 2.5), (-0.3, 0.0, 3.4)]
    for a, b in itertools.pairwise(pts):
        beam("spar", p["palm_dk"], a, b, thick=0.14)
    beam("spar_arm", p["palm"], pts[2], (0.25, -0.05, 2.7), thick=0.09)
    beam("rope", p["canvas_dk"], (0.25, -0.05, 2.7), (0.25, -0.05, 2.2), thick=0.03)
    jar(p, (0.25, -0.05, 1.95), r=0.14, h=0.26)
    box("rag", p["flame"], (-0.3, 0.0, 3.2), (0.5, 0.05, 0.22), bevel=0.0, rot_z=0.4, taper=0.5)
    for a in (2.3, 3.4, 4.5):
        jar(p, (0.15 + 1.2 * math.cos(a) * 1.02, 1.2 * math.sin(a) * 1.02, 0.32), r=0.13, h=0.28)
    for a in (1.0, 1.9):
        box("theft", p["canvas"], (0.15 + 1.3 * math.cos(a), 1.3 * math.sin(a), 0.92), (0.3, 0.3, 0.05), bevel=0.0, rot_z=a)


def g_n03b_harpy_witch_nest():
    """Taça estreita de arame sobre pernas de ferro, sob UM poste alto com a lâmpada de piche; garrafas em tipoias."""
    p = pal()
    pad(p)
    dust(p, (3.0, 3.0), h=0.3, taper=0.88)
    for i in range(3):
        a = math.radians(30 + i * 120)
        beam("bowl_leg", p["iron_dk"], (0.1 + 1.05 * math.cos(a), 1.05 * math.sin(a), 0.2), (0.1 + 0.6 * math.cos(a), 0.6 * math.sin(a), 0.85), thick=0.09)
    nest_bowl(p, (0.1, 0), 0.95, 0.5, 0.85, 0.75, n=10, tone="iron_dk")
    sump(p, (0.1, 0, 0.93), r=0.25)
    wire_veil(p, 0.1 + 0.95 * math.cos(0.12) * 0.98, 0.0, 0.42, 0.95, 1.5, n=5)
    # Poste alto da lâmpada, ao fundo.
    box("pole_foot", p["sand_dk"], (-1.0, 0, 0.1), (0.5, 0.5, 0.3), bevel=0.03, taper=0.7, taper_y=0.7)
    box("pole", p["iron_dk"], (-1.0, 0, 0.4), (0.14, 0.14, 3.4), bevel=0.0)
    beam("pole_arm", p["iron_dk"], (-1.0, 0, 3.6), (-0.5, 0, 3.6), thick=0.07)
    flame_lamp(p, (-0.5, 0, 3.55), size=0.28)
    beam("pole_stay", p["palm_dk"], (-1.0, 0, 2.6), (-1.2, 1.2, 0.2), thick=0.05)
    # Garrafas em tipoias de lona e a calha encapuzada com as mangueiras de pressão.
    for i in range(4):
        a = math.radians(70 + i * 70)
        bx, by = 0.1 + 0.95 * math.cos(a), 0.95 * math.sin(a)
        beam("sling", p["canvas"], (bx, by, 1.6), (bx, by, 1.15), thick=0.03)
        cyl("bottle", p["pitch"], (bx, by, 0.85), 0.1, 0.32, sides=8, top_radius=0.06, bevel=0.0)
    box("trough", p["palm"], (1.3, 0.2, 0.1), (0.7, 1.3, 0.32), bevel=0.02)
    box("trough_pitch", p["pitch"], (1.3, 0.2, 0.4), (0.55, 1.1, 0.03), bevel=0.0)
    prism("trough_hood", p["canvas"], (1.1, 0.2, 0.55), (0.5, 1.4, 0.4), ridge=0.5, rot_z=0.0)
    hose(p, [(0.1, -0.7, 0.9), (0.7, -0.9, 0.5), (1.3, -0.5, 0.45)])
    hose(p, [(0.1, 0.9, 0.9), (0.8, 1.0, 0.5), (1.3, 0.8, 0.45)])


def g_n031_harpy_matriarch_nest():
    """Ninho grande coroando UM mastro de derrick inclinado: asas de lona em V, volantes de válvula e a ventilação-trono."""
    p = pal()
    pad(p)
    dust(p, (3.4, 3.4), h=0.34, taper=0.9)
    nest_bowl(p, (0.3, 0), 1.55, 1.1, 0.36, 0.7, n=14)
    wire_veil(p, 0.3 + 1.55 * math.cos(0.12) * 0.98, 0.0, 0.55, 0.45, 1.05)
    # Trono: banco de lona com a ventilação de ferro e a chama.
    box("throne", p["canvas"], (0.5, 0, 0.44), (0.9, 0.9, 0.35), bevel=0.04, taper=0.7, taper_y=0.7)
    cyl("vent", p["iron_dk"], (0.5, 0, 0.78), 0.2, 0.4, sides=8, top_radius=0.12, bevel=0.0)
    kit.flame(p["flame"], p["flame"], (0.5, 0, 1.18), 0.34)
    # O mastro inclinado e a coroa de volantes.
    kit.derrick(p["palm_dk"], p["iron_dk"], None, (-1.0, 0, 0.3), base=0.9, top=0.28, height=3.6, lean=(0.8, 0.0))
    for z, r in ((1.5, 0.3), (2.6, 0.27), (3.6, 0.24)):
        valve_wheel(p, (-1.0 + 0.8 * (z - 0.3) / 3.6 + 0.3, 0, z), r=r)
    # Asas de lona abertas em V a partir do mastro.
    hub = (-0.55, 0, 2.0)
    for s in (-1, 1):
        for ty, tz, tone in ((1.55, 3.6, "canvas"), (1.7, 3.0, "canvas_dk"), (1.55, 2.4, "canvas")):
            plate("wing_finger", p[tone], hub, (-0.3, s * ty, tz), 0.5, 0.05, hint=(0.0, 0.0, 1.0))
            beam("wing_bone", p["iron_dk"], hub, (-0.3, s * ty, tz + 0.04), thick=0.06)
    for a in (2.2, 3.1, 4.0, 5.0):
        jar(p, (0.3 + 1.35 * math.cos(a), 1.35 * math.sin(a), 0.34), r=0.14, h=0.3)
    hose(p, [(0.3 + 1.35 * math.cos(3.1), 1.35 * math.sin(3.1), 0.55), (-1.5, 0.4, 0.3), (-1.5, 0.9, 0.12)])
    sump(p, (-1.4, 1.2, 0.1), r=0.3)


# ---------------------------------------------------------------------------------------------------------
# Tocas: Ogre Den -> Den of the Ogre Lord
# ---------------------------------------------------------------------------------------------------------


def ogre_cave(p):
    """Caverna escavada: fundo e flancos de rocha, teto só na metade de trás, boca de piche com grade e cortina."""
    box("back_rock", p["sand"], (-1.3, 0, 0.1), (1.0, 3.3, 1.7), bevel=0.12, taper=0.8, taper_y=0.9)
    for s in (-1, 1):
        box("side_rock", p["sand"], (-0.4, s * 1.3, 0.1), (2.4, 0.75, 1.3), bevel=0.1, taper=0.82, taper_y=0.7)
    box("roof_rock", p["sand_lt"], (-0.9, 0, 1.45), (1.9, 2.5, 0.32), bevel=0.08, taper=0.92, taper_y=0.92)
    box("floor_pitch", p["pitch"], (0.3, 0, 0.1), (2.0, 1.8, 0.03), bevel=0.0)
    # Boca: dois montantes de tubo de perfuração e a verga.
    for s in (-1, 1):
        cyl("drill_pipe", p["iron"], (1.05, s * 0.85, 0.1), 0.1, 1.45, sides=8, bevel=0.0)
        ring("pipe_joint", p["iron_dk"], (1.05, s * 0.85, 0.55), 0.1, 0.1, thick=0.03, sides=8)
    beam("lintel", p["iron_dk"], (1.05, -0.9, 1.55), (1.05, 0.9, 1.55), thick=0.16)
    grate(p, 1.12, 0.78, 0.15, 1.45, bars=7)
    curtain(p, 1.18, -0.3, 0.45, 1.45, 1.0, n=4)
    # Tambores amassados em pilha piramidal nos cantos da frente, e a calha de óleo.
    for s in (-1, 1):
        lying_drum(p, (1.15, s * 1.42 + 0.0, 0.34), length=0.55, r=0.24)
        lying_drum(p, (1.15, s * 1.0 + 0.0, 0.34), length=0.55, r=0.24, tone="iron_dk")
        lying_drum(p, (1.15, s * 1.21, 0.78), length=0.55, r=0.24)
    box("trough", p["palm"], (1.75, 0.2, 0.1), (0.4, 1.0, 0.26), bevel=0.02)
    box("trough_pitch", p["pitch"], (1.75, 0.2, 0.34), (0.3, 0.85, 0.03), bevel=0.0)
    hose(p, [(1.15, -1.3, 0.8), (1.6, -0.8, 0.5), (1.75, -0.2, 0.42)])


def g_n033_ogre_den():
    """Caverna de escavação sob UM tubo de perfuração alto; a lâmpada de contagem no topo é o mastro e o acento."""
    p = pal()
    pad(p)
    ogre_cave(p)
    cyl("mast_pipe", p["iron"], (1.05, 0.85, 1.55), 0.1, 2.0, sides=8, bevel=0.0)
    for z in (2.3, 3.0):
        ring("mast_joint", p["iron_dk"], (1.05, 0.85, z), 0.1, 0.1, thick=0.03, sides=8)
    beam("mast_stay", p["palm_dk"], (1.05, 0.85, 2.8), (0.2, 1.4, 1.55), thick=0.06)
    flame_lamp(p, (1.05, 0.85, 3.55), size=0.28)
    for z in (0.6, 1.2):
        box("rail_brace", p["canvas"], (-0.1, 1.72, z), (1.6, 0.05, 0.12), bevel=0.0)
    box("rivets", p["iron_dk"], (0.3, 0.0, 1.75), (0.9, 0.9, 0.05), bevel=0.0)


def g_n02o_ogre_lord_den():
    """A mesma caverna, mais larga no peso: caldeira deitada no teto, chaminé grossa e a fresta da fornalha; sem mastro alto."""
    p = pal()
    pad(p)
    ogre_cave(p)
    lying_drum(p, (-1.55, 0, 2.05), length=2.0, r=0.5, tone="iron")
    for f in (0.2, 0.5, 0.8):
        cyl("boiler_band", p["iron_dk"], (-1.55 + 2.0 * f, 0, 2.05), 0.54, 0.09, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
    box("firebox", p["iron_dk"], (0.4, 0, 1.78), (0.14, 0.7, 0.55), bevel=0.02)
    box("firebox_slit", p["flame"], (0.49, 0, 1.95), (0.04, 0.45, 0.12), bevel=0.0)
    kit.chimney(p["iron"], p["canvas_dk"], p["iron_dk"], (-1.1, 0, 2.4), 1.5, radius=0.3)
    hose(p, [(0.4, 0.35, 1.7), (0.9, 0.5, 1.2), (1.15, 0.5, 0.9)])
    box("gauge", p["canvas"], (0.45, -0.35, 2.15), (0.05, 0.22, 0.22), bevel=0.0)


# ---------------------------------------------------------------------------------------------------------
# Tocas: Quillboar Yard -> Razormane Abode
# ---------------------------------------------------------------------------------------------------------


def pen_fence(p, pts, post_h=0.85):
    """Cerca de arame farpado: estacas de palmeira e uma serpentina baixa entre cada par."""
    for (x0, y0), (x1, y1) in itertools.pairwise(pts):
        wire_coil(p["iron"], (x0, y0, 0.12), (x1, y1, 0.12), radius=0.18, turns=3)
        box("fence_post", p["palm_dk"], (x0, y0, 0.1), (0.1, 0.1, post_h), bevel=0.0)
    x, y = pts[-1]
    box("fence_post", p["palm_dk"], (x, y, 0.1), (0.1, 0.1, post_h), bevel=0.0)


def g_n036_quillboar_yard():
    """Cercado baixo de arame farpado em volta de UM poste de bomba alto (balancim de bombeio); carretel de lado faz o portão."""
    p = pal()
    pad(p)
    box("yard_floor", p["sand_dk"], (0, 0, 0.1), (3.1, 3.1, 0.05), bevel=0.0)
    pen_fence(p, [(1.5, -1.5), (-1.5, -1.5), (-1.5, 1.5), (1.5, 1.5)])
    pen_fence(p, [(1.5, 1.5), (1.5, 0.75)])
    pen_fence(p, [(1.5, -0.75), (1.5, -1.5)])
    lying_reel(p, (1.5, -0.7, 0.55), r=0.5, length=1.4)
    # Bomba: poste de ferro alto com o balancim e o cabeçote; haste de polimento até o poço.
    box("well_base", p["sand"], (-0.9, 0, 0.1), (0.9, 0.9, 0.3), bevel=0.04, taper=0.8, taper_y=0.8)
    for s in (-1, 1):
        beam("pump_leg", p["iron_dk"], (-0.9, s * 0.4, 0.4), (-0.9, s * 0.07, 2.9), thick=0.1)
    beam("walking_beam", p["palm_dk"], (-1.6, 0, 2.7), (0.0, 0, 3.4), thick=0.17)
    box("horse_head", p["iron_dk"], (0.0, 0, 2.95), (0.2, 0.28, 0.65), bevel=0.02)
    box("counterweight", p["iron"], (-1.6, 0, 2.2), (0.35, 0.4, 0.55), bevel=0.03)
    beam("polish_rod", p["iron"], (0.0, 0, 2.95), (0.0, 0, 0.45), thick=0.05)
    box("rod_head", p["sand"], (0.0, 0, 0.1), (0.5, 0.5, 0.35), bevel=0.04, taper=0.7, taper_y=0.7)
    # Calha de ração de piche e a mangueira do poço.
    box("trough", p["palm"], (0.45, 0.5, 0.15), (0.55, 1.3, 0.28), bevel=0.02)
    box("trough_pitch", p["pitch"], (0.45, 0.5, 0.42), (0.42, 1.15, 0.03), bevel=0.0)
    hose(p, [(0.0, 0.2, 0.3), (0.3, 0.2, 0.2), (0.45, -0.1, 0.35)])
    jar(p, (-0.9, 1.2, 0.12), r=0.14, h=0.3)
    flame_lamp(p, (1.5, 1.5, 0.95), size=0.2)
    box("herd_rag", p["flame"], (1.5, 1.5, 1.0), (0.04, 0.35, 0.2), bevel=0.0)


def g_n037_razormane_abode():
    """Abóbada de carretéis de arame empilhados (3-2-1) em volta de UM mastro de carretel torto; malha densa na boca."""
    p = pal()
    pad(p)
    box("abode_floor", p["sand_dk"], (0, 0, 0.1), (3.2, 3.0, 0.05), bevel=0.0)
    # Carretéis deitados ao longo de x: duas fiadas de baixo, duas do meio e uma de cima, com o túnel no meio embaixo.
    for s in (-1, 1):
        cyl("coil_low", p["iron"], (-1.4, s * 1.0, 0.7), 0.6, 2.7, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
        cyl("coil_mid", p["iron_dk"], (-1.4, s * 0.55, 1.6), 0.5, 2.7, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
        for x in (-0.9, 0.3):
            cyl("coil_strap", p["canvas_dk"], (x, s * 1.0, 0.7), 0.64, 0.14, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
    cyl("coil_top", p["iron"], (-1.4, 0, 2.15), 0.5, 2.7, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
    for x in (-0.9, 0.3):
        cyl("coil_strap", p["canvas"], (x, 0, 2.15), 0.54, 0.14, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
    box("mouth", p["pitch"], (1.1, 0, 0.1), (0.1, 0.9, 0.9), bevel=0.0)
    grate(p, 1.35, 0.5, 0.15, 1.0, bars=9)
    box("mesh_rail", p["iron"], (1.35, 0, 0.55), (0.07, 1.06, 0.05), bevel=0.0)
    for s in (-1, 1):
        box("seal", p["canvas"], (1.4, s * 0.7, 0.15), (0.05, 0.3, 0.9), bevel=0.0)
    # O mastro torto com o carretel no topo, ao fundo.
    pts = [(-1.2, 1.25, 0.2), (-1.2, 1.25, 1.5), (-1.45, 0.95, 2.3), (-1.55, 0.8, 3.0)]
    for a, b in itertools.pairwise(pts):
        beam("mast", p["palm_dk"], a, b, thick=0.14)
    lying_reel(p, (-1.55, 0.55, 3.05), r=0.4, length=0.5)
    beam("mast_stay", p["iron"], (-1.55, 0.8, 3.0), (-0.2, 1.4, 0.2), thick=0.035)
    # Lata de óleo e calha na frente, mangueira entre as duas, placa de aviso na chama.
    box("oil_can", p["iron_dk"], (1.5, 1.2, 0.1), (0.4, 0.4, 0.5), bevel=0.04)
    box("can_spout", p["iron"], (1.5, 1.2, 0.58), (0.2, 0.08, 0.16), bevel=0.0)
    box("trough", p["palm"], (1.55, -1.1, 0.1), (0.4, 0.9, 0.25), bevel=0.02)
    box("trough_pitch", p["pitch"], (1.55, -1.1, 0.33), (0.3, 0.75, 0.03), bevel=0.0)
    hose(p, [(1.5, 1.0, 0.45), (1.75, 0.2, 0.2), (1.6, -0.8, 0.3)])
    box("warn_post", p["palm_dk"], (1.55, 0.95, 0.1), (0.07, 0.07, 1.0), bevel=0.0)
    box("warn_plate", p["flame"], (1.55, 0.95, 0.75), (0.05, 0.55, 0.4), bevel=0.0)


# ---------------------------------------------------------------------------------------------------------
# Tocas: Sandkin Burrow -> Monstrous Sandkin Burrow
# ---------------------------------------------------------------------------------------------------------


def g_n039_sandkin_burrow():
    """Depressão longa e baixa de duna sob UMA biruta curta de lona; cortina-peneira na boca e calha de captura."""
    p = pal()
    pad(p)
    box("back_bank", p["sand"], (-1.0, 0, 0.1), (1.2, 3.3, 0.95), bevel=0.1, taper=0.55, taper_y=0.9)
    for s in (-1, 1):
        box("side_bank", p["sand"], (0.15, s * 1.35, 0.1), (2.0, 0.75, 0.7), bevel=0.1, taper=0.7, taper_y=0.6)
    box("hollow", p["pitch"], (0.3, 0, 0.1), (1.9, 1.9, 0.03), bevel=0.0)
    box("crust", p["pitch"], (1.5, 0, 0.1), (0.6, 1.5, 0.04), bevel=0.0)
    # Boca: peneira (barras finas e lona perfurada).
    grate(p, 1.7, 0.75, 0.15, 0.8, bars=11)
    curtain(p, 1.74, 0.0, 0.7, 0.8, 0.55, n=6, tone="canvas_dk")
    # Biruta curta e torta atrás: mastro de palmeira com meia de lona dobrada, e o trapo de chama no pescoço.
    beam("sock_mast", p["palm_dk"], (-1.35, -0.9, 0.2), (-1.3, -0.9, 2.9), thick=0.14)
    for i, (x, r) in enumerate(((-1.2, 0.3), (-0.9, 0.24), (-0.62, 0.18), (-0.38, 0.12))):
        cyl("windsock", p["canvas"] if i % 2 == 0 else p["canvas_dk"], (x, -0.9, 2.65 - i * 0.1), r, 0.3, sides=6, top_radius=r * 0.78, bevel=0.0, rot=("Y", math.radians(90)))
    ring("sock_ring", p["iron_dk"], (-1.3, -0.9, 2.65), 0.3, 0.07, thick=0.02, sides=8)
    box("collar_rag", p["flame"], (-1.36, -0.9, 2.1), (0.1, 0.1, 0.45), bevel=0.0, taper=0.4)
    # Cabrestos, estacas de ferro na soleira, jarras gêmeas seladas e a calha.
    for s in (-1, 1):
        kit.spike(p["iron_dk"], (1.55, s * 1.05, 0.1), height=0.55, radius=0.07, lean=(0.1, s * 0.05))
        jar(p, (0.5, s * 1.4, 0.55), r=0.18, h=0.38)
        hose(p, [(0.5, s * 1.3, 0.62), (0.9, s * 0.9, 0.3), (1.1, s * 0.4, 0.2)])
    box("trough", p["palm"], (1.15, 0, 0.1), (0.45, 0.9, 0.24), bevel=0.02)
    box("trough_pitch", p["pitch"], (1.15, 0, 0.32), (0.35, 0.75, 0.03), bevel=0.0)
    for y in (-0.5, 0.5):
        box("halter", p["palm_dk"], (-0.2, y, 0.1), (0.07, 0.07, 0.8), bevel=0.0)
        box("halter_knot", p["canvas"], (-0.2, y, 0.8), (0.14, 0.14, 0.1), bevel=0.0)


def g_n02r_monstrous_sandkin_burrow():
    """Cratera de ruptura sob UM leque alto de placas de vidro fundido (ferro fosco); grade-focinheira na boca."""
    p = pal()
    pad(p)
    box("back_bank", p["sand"], (-1.1, 0, 0.1), (1.1, 3.4, 1.15), bevel=0.1, taper=0.6, taper_y=0.9)
    for s in (-1, 1):
        box("side_bank", p["sand"], (0.1, s * 1.35, 0.1), (2.1, 0.8, 0.95), bevel=0.1, taper=0.7, taper_y=0.6)
    box("crater", p["pitch"], (0.35, 0, 0.1), (1.9, 1.9, 0.03), bevel=0.0)
    cyl("crater_core", p["pitch"], (0.35, 0, 0.12), 0.7, 0.08, sides=10, bevel=0.0)
    # Canais de sangria: filetes de piche que descem pela frente.
    for y in (-0.5, 0.5):
        box("bleed", p["pitch"], (1.5, y, 0.1), (0.8, 0.18, 0.03), bevel=0.0)
    grate(p, 1.75, 0.8, 0.15, 0.95, bars=8)
    for s in (-1, 1):
        box("grille_post", p["iron_dk"], (1.75, s * 0.82, 0.1), (0.1, 0.1, 1.0), bevel=0.0)
    # O leque: sete placas de ferro fosco, abertas em V amplo a partir do cubo atrás da cratera.
    hub = (-1.1, 0, 1.0)
    for i in range(7):
        a = math.radians(-60 + i * 20)
        tip = (hub[0] - 0.08 * abs(i - 3), hub[1] + 2.0 * math.sin(a), hub[2] + 2.2 * math.cos(a) * (1.0 if i != 3 else 1.15))
        plate("fan_plate", p["iron"] if i % 2 == 0 else p["iron_dk"], hub, tip, 0.42, 0.07)
    cyl("collar", p["iron_dk"], (-1.1, 0, 0.85), 0.35, 0.3, sides=10, bevel=0.0)
    cyl("collar_bleed", p["pitch"], (-1.1, 0, 0.82), 0.4, 0.1, sides=10, bevel=0.0)
    for y in (-1.0, 1.0):
        box("restraint", p["canvas"], (0.35, y * 0.6, 0.2), (1.9, 0.2, 0.05), bevel=0.0, rot_z=math.radians(25 * y))
    box("restraint", p["canvas"], (0.35, 0, 0.2), (0.2, 1.8, 0.05), bevel=0.0)
    flame_lamp(p, (1.7, 1.45, 0.1), size=0.22, post=0.5)


# ---------------------------------------------------------------------------------------------------------
# Choco de lagartos
# ---------------------------------------------------------------------------------------------------------


def g_n038_salamander_hatchery():
    """Poço quente de piche com ovos de ferro fosco, sob UMA bomba de balancim alta; grade-escotilha na boca."""
    p = pal()
    pad(p)
    cyl("crust", p["sand_dk"], (0.1, 0, 0.1), 1.65, 0.2, sides=14, top_radius=1.5, bevel=0.0)
    cyl("sump", p["pitch"], (0.1, 0, 0.3), 1.3, 0.05, sides=14, bevel=0.0)
    # Ovos de ferro semienterrados no piche, um deles rachado.
    for ex, ey, er in ((0.5, 0.35, 0.42), (0.1, -0.5, 0.38), (-0.3, 0.45, 0.34), (0.75, -0.55, 0.3)):
        dome("egg", p["iron"], (ex, ey, 0.3), er, squash=1.25, sides=8)
        ring("egg_band", p["iron_dk"], (ex, ey, 0.3), er * 0.97, 0.06, thick=0.0, sides=8)
    dome("egg_crack", p["iron_dk"], (0.05, 0.05, 0.3), 0.3, squash=0.8, sides=8)
    # Bomba de balancim: poste em A, viga, cabeça de cavalo para o poço e contrapeso atrás.
    box("pump_base", p["sand"], (-1.25, 0, 0.1), (0.9, 1.0, 0.25), bevel=0.04, taper=0.85, taper_y=0.85)
    for s in (-1, 1):
        beam("a_leg_f", p["palm_dk"], (-1.05, s * 0.4, 0.3), (-1.2, s * 0.06, 2.6), thick=0.1)
        beam("a_leg_b", p["palm_dk"], (-1.55, s * 0.4, 0.3), (-1.3, s * 0.06, 2.6), thick=0.1)
    beam("walking_beam", p["iron_dk"], (-2.0 + 0.4, 0, 2.45), (0.1, 0, 3.25), thick=0.17)
    box("horse_head", p["iron_dk"], (0.1, 0, 2.55), (0.22, 0.3, 0.75), bevel=0.02)
    box("counterweight", p["iron"], (-1.65, 0, 2.2), (0.4, 0.5, 0.5), bevel=0.03)
    beam("polish_rod", p["iron"], (0.1, 0, 2.6), (0.1, 0, 0.5), thick=0.05)
    # Escotilha de grade na boca (frente), mangueira sumindo na lama e o medidor da chama no poste.
    grate(p, 1.55, 0.7, 0.3, 0.75, cy=0.0, bars=6)
    box("hatch_rail", p["iron_dk"], (1.3, 0, 0.3), (0.7, 1.4, 0.05), bevel=0.0)
    hose(p, [(-1.0, 0.7, 0.4), (-0.6, 1.3, 0.2), (0.4, 1.35, 0.14)])
    hose(p, [(0.4, 1.35, 0.14), (1.2, 1.3, 0.1)])
    for s in (-1, 1):
        box("pipe_seal", p["canvas"], (-0.7, s * 0.3, 0.9), (0.18, 0.18, 0.12), bevel=0.0)
    box("gauge_mark", p["flame"], (-1.18, 0.0, 1.55), (0.06, 0.2, 0.2), bevel=0.0)
    jar(p, (1.3, -1.0, 0.1), r=0.15, h=0.3)


# ---------------------------------------------------------------------------------------------------------
# Especiais
# ---------------------------------------------------------------------------------------------------------


def g_h07e_ballista_tower():
    """Torre de defesa: tripé enterrado de derrick e UM trilho alto de arpão; mangueira da canastra ao aríete."""
    p = pal()
    pad(p, (2.8, 2.8))
    dust(p, (2.6, 2.6), h=0.35)
    kit.derrick(p["palm_dk"], p["iron_dk"], None, (0, 0, 0.4), base=2.0, top=0.9, height=2.3)
    # Boca: caixa de piche entre as pernas da frente, com grade e cortina.
    box("mouth", p["pitch"], (0.7, 0, 0.4), (0.4, 1.1, 1.1), bevel=0.0)
    grate(p, 1.0, 0.55, 0.45, 1.5, bars=6)
    curtain(p, 1.06, -0.25, 0.28, 1.5, 0.8, n=3)
    box("deck", p["palm"], (0, 0, 2.72), (1.6, 1.6, 0.1), bevel=0.02)
    cyl("canister", p["pitch"], (-0.35, 0.45, 2.82), 0.27, 0.6, sides=10, bevel=0.0)
    ring("canister_band", p["iron_dk"], (-0.35, 0.45, 3.15), 0.27, 0.07, thick=0.03, sides=10)
    cyl("ram", p["iron"], (-0.6, 0, 3.0), 0.13, 0.9, sides=8, bevel=0.0, rot=("Y", math.radians(90)))

    def rz(x):
        return 3.2 + 0.78 * (x + 0.5)

    kit.begin_part("anim_ballista")
    for s in (-1, 1):
        beam("rail", p["iron_dk"], (-0.6, s * 0.17, rz(-0.6)), (1.2, s * 0.17, rz(1.2)), thick=0.12)
        beam("rail_strut", p["palm_dk"], (0.5, s * 0.55, 2.82), (0.5, s * 0.15, rz(0.5) - 0.04), thick=0.07)
    for x in (0.0, 0.5, 0.95):
        box("rail_tie", p["palm"], (x, 0, rz(x) - 0.03), (0.08, 0.4, 0.06), bevel=0.0)
    beam("harpoon", p["palm"], (-0.2, 0, rz(-0.2) + 0.1), (1.2, 0, rz(1.2) + 0.1), thick=0.12)
    beam("harpoon_head", p["iron"], (1.15, 0, rz(1.15) + 0.1), (1.55, 0, rz(1.55) + 0.1), thick=0.2)
    kit.end_part()
    hose(p, [(-0.35, 0.45, 3.35), (-0.5, 0.25, 3.2), (-0.55, 0.05, 3.05)])
    flame_lamp(p, (-0.62, -0.62, 2.82), size=0.22, post=0.7)
    jar(p, (-0.2, -0.5, 2.82), r=0.12, h=0.25)


def g_h079_beacon_of_the_oasis():
    """Salina pálida sob UM mastro de palmeira torto com a luz de aviso; calhas de lona e a bomba de ferro."""
    p = pal()
    pad(p)
    cyl("rim", p["sand_dk"], (0, 0, 0.1), 1.75, 0.16, sides=14, bevel=0.0)
    cyl("salt", p["sand_lt"], (0, 0, 0.2), 1.55, 0.08, sides=14, bevel=0.0)
    cyl("film", p["pitch"], (0.35, -0.1, 0.28), 0.55, 0.02, sides=10, bevel=0.0)
    for s in (-1, 1):
        box("trough", p["canvas"], (0.5, s * 0.85, 0.28), (1.1, 0.42, 0.3), bevel=0.03)
        box("trough_water", p["pitch"], (0.5, s * 0.85, 0.55), (0.95, 0.3, 0.02), bevel=0.0)
    # Bomba: toma blindada de ferro, mangueira para as calhas.
    cyl("pump", p["iron"], (-0.9, 0.2, 0.28), 0.3, 0.9, sides=8, bevel=0.0)
    ring("pump_band", p["iron_dk"], (-0.9, 0.2, 0.7), 0.3, 0.07, thick=0.03, sides=8)
    dome("intake_guard", p["iron_dk"], (-0.9, 0.2, 1.18), 0.34, squash=0.7, sides=8)
    hose(p, [(-0.7, 0.2, 0.5), (-0.2, 0.2, 0.34), (0.3, 0.6, 0.34), (0.5, 0.85, 0.34)])
    hose(p, [(-0.2, 0.2, 0.34), (0.3, -0.5, 0.34), (0.5, -0.85, 0.34)])
    # Mastro de tamareira morta, dobrando, com a lâmpada-farol.
    pts = [(-1.0, -0.8, 0.25), (-1.0, -0.75, 1.6), (-0.7, -0.5, 2.8), (-0.35, -0.3, 3.7)]
    for a, b in itertools.pairwise(pts):
        beam("mast", p["palm_dk"], a, b, thick=0.16)
    box("lamp_cage", p["iron_dk"], (-0.35, -0.3, 3.7), (0.3, 0.3, 0.07), bevel=0.0)
    kit.flame(p["flame"], p["flame"], (-0.35, -0.3, 3.77), 0.36)
    beam("mast_stay", p["iron"], (-0.7, -0.5, 2.8), (0.6, -1.4, 0.2), thick=0.035)
    for a in (-0.4, 0.5):
        cyl("salt_heap", p["canvas"], (-1.3 * math.cos(a), 1.2 * math.sin(a), 0.28), 0.25, 0.14, sides=7, top_radius=0.12, bevel=0.0)


def g_h07a_sacred_peyote():
    """Destilaria do Miragem: alambique de barro espinhoso sob UM escape alto de ferro; capuz de lona na entrada."""
    p = pal()
    pad(p)
    box("base", p["sand_dk"], (-0.2, 0, 0.1), (3.0, 3.0, 0.25), bevel=0.05, taper=0.93, taper_y=0.93)
    cyl("pot", p["sand"], (-0.5, 0.2, 0.35), 1.0, 0.95, sides=12, top_radius=0.8, bevel=0.0)
    cyl("shoulder", p["sand_lt"], (-0.5, 0.2, 1.3), 0.8, 0.45, sides=12, top_radius=0.35, bevel=0.0)
    dome("head", p["sand_lt"], (-0.5, 0.2, 1.75), 0.35, squash=0.9, sides=10)
    for i in range(10):
        a = i * math.tau / 10
        r = 0.98 - 0.0 * i
        kit.spike(p["iron_dk"] if i % 2 else p["sand_dk"], (-0.5 + r * math.cos(a), 0.2 + r * math.sin(a), 0.8), height=0.38, radius=0.08, lean=(0.25 * math.cos(a), 0.25 * math.sin(a)))
    for i in range(5):
        a = i * math.tau / 5 + 0.3
        kit.spike(p["sand_dk"], (-0.5 + 0.55 * math.cos(a), 0.2 + 0.55 * math.sin(a), 1.55), height=0.3, radius=0.06, lean=(0.12 * math.cos(a), 0.12 * math.sin(a)))
    # O escape alto e as braçadeiras.
    cyl("exhaust", p["iron"], (-0.5, 0.2, 1.9), 0.13, 2.2, sides=8, bevel=0.0)
    for z in (2.6, 3.4):
        ring("exhaust_band", p["iron_dk"], (-0.5, 0.2, z), 0.13, 0.09, thick=0.03, sides=8)
    cyl("exhaust_cap", p["iron_dk"], (-0.5, 0.2, 4.0), 0.2, 0.12, sides=8, top_radius=0.1, bevel=0.0)
    # Tubulação de ferro enferrujado até o barril condensador (serpentina deitada).
    beam("lyne", p["iron_dk"], (-0.3, 0.2, 1.75), (0.35, 1.0, 1.1), thick=0.11)
    cyl("condenser", p["palm_dk"], (0.5, 1.1, 0.35), 0.45, 0.85, sides=10, bevel=0.0)
    wire_coil(p["iron_dk"], (0.2, 1.1, 0.45), (0.9, 1.1, 0.45), radius=0.18, turns=3)
    # Funil encapuzado na entrada, forno com a chama-piloto e jarras de reagente.
    box("hopper", p["iron"], (0.95, -0.55, 0.35), (0.6, 0.6, 0.55), bevel=0.04, taper=0.75, taper_y=0.75)
    box("hopper_pitch", p["pitch"], (0.95, -0.55, 0.9), (0.4, 0.4, 0.03), bevel=0.0)
    prism("hood", p["canvas"], (0.8, -0.55, 0.95), (0.7, 0.8, 0.4), ridge=0.5, rot_z=0.0)
    hose(p, [(0.8, -0.55, 0.5), (0.3, -0.35, 0.3), (0.1, -0.05, 0.35)])
    box("firebox", p["iron_dk"], (0.45, 0.2, 0.35), (0.35, 0.6, 0.45), bevel=0.03)
    box("pilot", p["flame"], (0.64, 0.2, 0.45), (0.04, 0.3, 0.14), bevel=0.0)
    for i in range(3):
        jar(p, (-1.4 + i * 0.3, -1.1, 0.35), r=0.13, h=0.3)
    for s in (-1, 1):
        beam("brace", p["palm"], (-1.4, s * 1.0 + 0.2, 0.35), (-1.0, s * 0.4 + 0.2, 1.3), thick=0.1)


def g_n03a_temple_of_storm():
    """Cabeça de poço primordial: coletor enterrado, desvio de trilho e UMA chaminé de alívio altíssima com o alarme."""
    p = pal()
    pad(p)
    box("manifold", p["sand_dk"], (-0.1, 0, 0.1), (3.0, 3.0, 0.4), bevel=0.06, taper=0.92, taper_y=0.92)
    cyl("throat", p["sand"], (0.1, 0, 0.5), 0.75, 0.55, sides=10, bevel=0.0)
    cyl("throat_dark", p["pitch"], (0.1, 0, 1.03), 0.5, 0.03, sides=10, bevel=0.0)
    # Volante de fechamento sobre a garganta e a haste.
    box("spindle", p["iron_dk"], (0.1, 0, 1.0), (0.1, 0.1, 0.35), bevel=0.0)
    valve_wheel(p, (0.1, 0, 1.38), r=0.6, flat=True)
    # Dutos cruzados com flanges de lona, afundando na lama nas pontas, e volantes verticais.
    for s in (-1, 1):
        beam("pipe", p["iron"], (0.1, s * 0.7, 0.85), (0.1, s * 1.45, 0.85), thick=0.2)
        beam("pipe_drop", p["iron"], (0.1, s * 1.45, 0.85), (0.1, s * 1.45, 0.2), thick=0.2)
        box("flange", p["canvas"], (0.1, s * 1.1, 0.72), (0.3, 0.1, 0.3), bevel=0.0)
        valve_wheel(p, (0.5, s * 1.1, 1.0), r=0.26)
        beam("valve_stem", p["iron_dk"], (0.1, s * 1.1, 0.95), (0.5, s * 1.1, 1.0), thick=0.05)
    beam("feed", p["iron"], (-0.6, 0, 0.7), (-0.2, 0, 0.7), thick=0.2)
    # Chaminé de alívio, altíssima, com guias e a chama de alarme no topo.
    kit.chimney(p["sand"], p["canvas_dk"], p["iron_dk"], (-1.1, -0.8, 0.5), 3.7, radius=0.38)
    kit.flame(p["flame"], p["flame"], (-1.1, -0.8, 4.25), 0.34)
    for a in (0.2, 1.5):
        beam("guy", p["iron"], (-1.1, -0.8, 3.1), (-1.1 + 1.3 * math.cos(a), -0.8 + 1.3 * math.sin(a), 0.15), thick=0.035)
    # Desvio de trilho com um vagão-tanque deitado na frente.
    for x in (1.35, 1.8):
        beam("rail", p["iron_dk"], (x, -1.7, 0.16), (x, 1.7, 0.16), thick=0.07)
    for i in range(8):
        box("sleeper", p["palm_dk"], (1.58, -1.5 + i * 0.43, 0.1), (0.7, 0.14, 0.06), bevel=0.0)
    cyl("tank_car", p["iron"], (1.58, -1.0, 0.55), 0.38, 1.4, sides=10, bevel=0.0, rot=("X", math.radians(-90)))
    for off in (0.25, 1.1):
        cyl("tank_gasket", p["canvas"], (1.58, -1.0 + off, 0.55), 0.42, 0.08, sides=10, bevel=0.0, rot=("X", math.radians(-90)))
    for y in (-1.45, -0.45):
        box("tank_cradle", p["palm_dk"], (1.58, y, 0.2), (0.5, 0.12, 0.3), bevel=0.0)
    for a in (0.0, 1.6):
        cyl("seep", p["pitch"], (-0.2 + 0.9 * math.cos(a + 3.5), 0.9 * math.sin(a + 3.5) + 0.9, 0.5), 0.3, 0.02, sides=9, bevel=0.0)


BUILDINGS = {
    "h07E": g_h07e_ballista_tower,
    "h079": g_h079_beacon_of_the_oasis,
    "n02O": g_n02o_ogre_lord_den,
    "n02N": g_n02n_fire_gnoll_hut,
    "n02P": g_n02p_gnoll_tent,
    "n02Q": g_n02q_harpy_nest,
    "n02R": g_n02r_monstrous_sandkin_burrow,
    "n031": g_n031_harpy_matriarch_nest,
    "n03B": g_n03b_harpy_witch_nest,
    "n033": g_n033_ogre_den,
    "n036": g_n036_quillboar_yard,
    "n037": g_n037_razormane_abode,
    "h07A": g_h07a_sacred_peyote,
    "n038": g_n038_salamander_hatchery,
    "n039": g_n039_sandkin_burrow,
    "n03A": g_n03a_temple_of_storm,
}


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["all"]
    names = list(BUILDINGS) if args[0] == "all" else [args[0]]
    out_dir = game_paths.out_arg(args, "--out", "buildings", "desert")
    render_dir = args[args.index("--render") + 1] if "--render" in args else ""
    for name in names:
        kit.build(name, out_dir, render_dir, make=BUILDINGS[name], views=(("front", -35.0),))


if __name__ == "__main__":
    main()
