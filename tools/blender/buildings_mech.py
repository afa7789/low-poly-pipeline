"""Prédios da raça Mech modelados por script (redesenho de reports/design/race-mech.md): um GLB por prédio.

Uso:
    blender -b --factory-startup --python tools/blender/buildings_mech.py -- <id|all> [--out DIR] [--render DIR]
        [--views front,back]

A Casa do Poço: aristocracia que perfura. Ferro fundido rebitado, fuligem, latão de poço com azinhavre nas
juntas, óleo cru só em vazamento, correia de couro, lama até o joelho. Baixo e largo: nada sobe, a não ser
chaminé, derrick ou mastro. Todo prédio leva ao menos dois de rebite / trilho / fumaça, uma única luz acesa
(fresta de fornalha ou lente: chama-piloto; o gerador azul/vermelho troca a cor, nunca soma) e o chão de lama.
Distinto dos Humanos (galpão de duas águas, lona e concreto): aqui é laje plana de chapa, caldeira, chaminé,
treliça e trilho. Pegada ~3,5 x 3,5 centrada na origem, a porta virada para +x; o jogo normaliza o tamanho,
põe o prédio no plinto do time e desenha a bandeira.
"""

import itertools
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


def pal():
    return {
        "iron": mat("cast_iron", 0x909BA5),
        "iron_dk": mat("cast_iron_dark", 0x707A84),
        "iron_lt": mat("cast_iron_light", 0xC6CED4),
        "soot": mat("soot", 0x3A3F46),
        "roof": mat("roof_plate", 0xBCC4CA),
        "roof_dk": mat("roof_soot", 0x69737D),
        "verd_roof": mat("verdigris_roof", 0x66B198),
        "brick_roof": mat("brick_roof", 0x9C5F4C),
        "earth_lt": mat("earth_light", 0xA98F6A),
        "cake": mat("soot_cake", 0x7B838C),
        "brass": mat("well_brass", 0xD2A650),
        "brass_dk": mat("well_brass_dark", 0xA07E3C),
        "verd": mat("verdigris", 0x76BBA2),
        "oil": mat("crude_oil", 0x18151C),
        "belt": mat("belting", 0x97704F),
        "timber": mat("timber", 0xAA8D64),
        "brick": mat("brick", 0xC27A5E),
        "brick_dk": mat("brick_dark", 0x8A5D4C),
        "mud": mat("mud", 0x6E5C46),
        "earth": mat("earth", 0x8A7358),
        "smoke": mat("smoke", 0xC9C9C3),
        "haze": mat("powder_haze", 0xDDD3A8),
        "canvas": mat("doped_canvas", 0xD6CBA4),
        "hazard": mat("hazard", 0xE2B224),
        "glass": mat("glass", 0xA6D0CA),
        "ecru": mat("chalk", 0xEDE8DA),
        "slate": mat("slate", 0x3C4248),
        "flame": mat("pilot_flame", 0xFFE600, emit=3.0),
        "blue": mat("field_blue", 0x66CCFF, emit=3.0),
        "red": mat("field_red", 0xFF4B3A, emit=3.0),
    }


# ---------------------------------------------------------------------------------------------------------
# Peças da raça
# ---------------------------------------------------------------------------------------------------------

_DIR = {"x+": (1, 0, 0), "x-": (-1, 0, 0), "y+": (0, 1, 0), "y-": (0, -1, 0)}
_ROT = {"x+": ("Y", 90), "x-": ("Y", -90), "y-": ("X", 90), "y+": ("X", -90)}


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _plane(facing, h, v):
    """Vetor no plano de uma face: h na horizontal da face, v na vertical."""
    return (0, h, v) if facing[0] == "x" else (h, 0, v)


def tilt(ob, pivot, axis, angle):
    """Gira a malha pronta em torno de um pivô (portas levantadas, placas, tampas)."""
    pv = Vector(pivot)
    ob.data.transform(Matrix.Translation(pv) @ Matrix.Rotation(angle, 4, axis) @ Matrix.Translation(-pv))
    return ob


def shear(ob, along, by, k, origin=0.0):
    """Entorta a malha: soma k * (coord[along] - origin) em coord[by] (galpão torto, telhado de uma água)."""
    for v in ob.data.vertices:
        v.co[by] += k * (v.co[along] - origin)
    return ob


def taper(name, material, a, b, r0, r1, sides=8):
    """Tronco de cone de a até b: foguete, cano grosso, holofote, biruta."""
    a, b = Vector(a), Vector(b)
    d = b - a
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=r0, radius2=max(r1, 1e-4), depth=d.length)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, d.length / 2))
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=d.to_track_quat("Z", "Y").to_matrix())
    bmesh.ops.translate(bm, verts=bm.verts, vec=a)
    return kit._finish(bm, name, material)


def disc(name, material, pos, radius, thick, facing="x+", sides=12):
    """Disco cuja face de trás está em pos e que cresce para fora, na direção facing."""
    axis, deg = _ROT[facing]
    return cyl(name, material, pos, radius, thick, sides=sides, bevel=0.0, rot=(axis, math.radians(deg)))


def pad(p, size=(3.5, 3.5)):
    """Lama até o joelho: o chão do posto, do tamanho do conteúdo (o jogo normaliza pelo maior lado)."""
    box("pad", p["mud"], (0, 0, 0), (size[0], size[1], 0.1), bevel=0.03)


def leak(p, x, y, r=0.2):
    """Poça de óleo cru: o único brilho molhado, sempre vazando."""
    cyl("leak", p["oil"], (x, y, 0.1), r, 0.014, sides=8, bevel=0.0)


def rivets(p, a, b, n, tone="iron_lt", size=0.06):
    a, b = Vector(a), Vector(b)
    for i in range(n):
        c = a.lerp(b, i / (n - 1)) if n > 1 else a
        box("rivet", p[tone], (c.x, c.y, c.z - size / 2), (size, size, size), bevel=0.0)


def smoke(p, pos, scale=1.0, n=3, tone="smoke"):
    """Coluna de fumaça em gomos que crescem e derivam: o único que levita."""
    x, y, z = pos
    for i in range(n):
        r = (0.13 + 0.05 * i) * scale
        cyl("smoke", p[tone], (x + 0.07 * i * scale, y, z + i * 0.25 * scale), r, 0.28 * scale, sides=7, top_radius=r * 1.12, bevel=0.0)


def stack(p, pos, height, radius=0.2, puffs=3):
    """Chaminé de caldeira com cinta de latão e fumaça: a vertical da raça."""
    kit.chimney(p["iron_dk"], p["brass"], p["soot"], pos, height, radius)
    smoke(p, (pos[0], pos[1], pos[2] + height + 0.04), scale=radius / 0.2 * 0.85, n=puffs)


def barrel(p, pos, tone="iron_dk", stripe=False):
    x, y, z = pos
    cyl("barrel", p[tone], pos, 0.17, 0.44, sides=10, bevel=0.0)
    for dz in (0.1, 0.3):
        ring("barrel_band", p["soot"], (x, y, z + dz), 0.17, 0.04, thick=0.015, sides=10)
    if stripe:
        ring("barrel_stripe", p["hazard"], (x, y, z + 0.19), 0.17, 0.06, thick=0.02, sides=10)


def gauge(p, pos, facing="x+", r=0.2):
    """Manômetro de latão com vidro: onde não há rosto, há pressão."""
    d = _DIR[facing]
    disc("gauge_rim", p["brass"], pos, r + 0.05, 0.05, facing, 10)
    face = _add(pos, tuple(c * 0.04 for c in d))
    disc("gauge_face", p["ecru"], face, r, 0.03, facing, 10)
    a = _add(face, tuple(c * 0.03 for c in d))
    beam("gauge_needle", p["soot"], a, _add(a, _plane(facing, r * 0.6, r * 0.45)), thick=0.025)


def gear(p, pos, facing="x+", r=0.4, thick=0.08, tone="brass_dk", teeth=10):
    """Engrenagem exposta: disco, dentes radiais e cubo."""
    d = _DIR[facing]
    kit.begin_part("anim_gear", unique=True)
    disc("gear", p[tone], pos, r, thick, facing, 12)
    mid = _add(pos, tuple(c * thick / 2 for c in d))
    for i in range(teeth):
        a = i * math.tau / teeth
        inner = _add(mid, _plane(facing, math.cos(a) * r * 0.85, math.sin(a) * r * 0.85))
        outer = _add(mid, _plane(facing, math.cos(a) * r * 1.2, math.sin(a) * r * 1.2))
        beam("gear_tooth", p[tone], inner, outer, thick=r * 0.28)
    disc("gear_hub", p["soot"], _add(pos, tuple(c * 0.02 for c in d)), r * 0.28, thick + 0.04, facing, 8)
    kit.end_part()


def spur(p, x0, x1, y=0.0, gauge_w=0.6):
    """Trecho de desvio ferroviário: dormentes e dois trilhos. A cauda horizontal da raça."""
    n = max(2, int((x1 - x0) / 0.3))
    for i in range(n + 1):
        x = x0 + 0.08 + i * (x1 - x0 - 0.16) / n
        box("sleeper", p["timber"], (x, y, 0.1), (0.13, gauge_w + 0.5, 0.05), bevel=0.0)
    for s in (-1, 1):
        box("rail", p["iron_lt"], ((x0 + x1) / 2, y + s * gauge_w / 2, 0.15), (x1 - x0, 0.06, 0.06), bevel=0.0)


def board(p, pos, rot_z=0.0, lines=3):
    """Quadro de giz do turno em dois postes."""
    x, y, z = pos
    c, s = math.cos(rot_z), math.sin(rot_z)
    box("board", p["slate"], (x, y, z + 0.3), (0.06, 0.9, 0.5), bevel=0.0, rot_z=rot_z)
    for sg in (-1, 1):
        box("board_post", p["timber"], (x - s * sg * 0.4, y + c * sg * 0.4, z), (0.07, 0.07, 0.5), bevel=0.0)
    for i in range(lines):
        box("chalk", p["ecru"], (x + c * 0.035, y + s * 0.035, z + 0.4 + i * 0.1), (0.02, 0.6 - 0.1 * i, 0.03), bevel=0.0, rot_z=rot_z)


def plated(p, cx, cy, sx, sy, h, z0=0.1, wall="iron", roof="roof", ribs=True):
    """Bloco de chapa rebitada: rodapé, parede com costuras e duas fiadas de rebites nas faces +x e -y, laje de
    teto de fuligem. A massa baixa e larga da raça."""
    box("foot", p["iron_dk"], (cx, cy, z0), (sx + 0.12, sy + 0.12, 0.14), bevel=0.02)
    box("wall", p[wall], (cx, cy, z0 + 0.1), (sx, sy, h - 0.1), bevel=0.03)
    box("roof", p[roof], (cx, cy, z0 + h), (sx + 0.16, sy + 0.16, 0.1), bevel=0.02)
    fx, fy = cx + sx / 2, cy - sy / 2
    if ribs:
        for i in range(1, max(2, int(sy / 0.8))):
            box("seam", p["iron_dk"], (fx, cy - sy / 2 + i * sy / max(2, int(sy / 0.8)), z0 + 0.16), (0.05, 0.05, h - 0.3), bevel=0.0)
        for i in range(1, max(2, int(sx / 0.8))):
            box("seam", p["iron_dk"], (cx - sx / 2 + i * sx / max(2, int(sx / 0.8)), fy, z0 + 0.16), (0.05, 0.05, h - 0.3), bevel=0.0)
    for z in (z0 + 0.2, z0 + h - 0.12):
        rivets(p, (fx + 0.01, cy - sy / 2 + 0.15, z), (fx + 0.01, cy + sy / 2 - 0.15, z), int((sy - 0.3) / 0.4) + 1)
        rivets(p, (cx - sx / 2 + 0.15, fy - 0.01, z), (cx + sx / 2 - 0.15, fy - 0.01, z), int((sx - 0.3) / 0.4) + 1)


def hull(p, pos, length=1.2, width=1.2):
    """Casco de tanque com lagartas: o marcador de trilho nos pátios dos tanques."""
    x, y, z = pos
    for s in (-1, 1):
        yy = y + s * (width / 2 - 0.15)
        box("tread", p["cake"], (x, yy, z), (length, 0.3, 0.36), bevel=0.04)
        if s < 0:
            for i in range(4):
                disc("road_wheel", p["iron_dk"], (x - length * 0.36 + i * length * 0.24, yy - 0.15, z + 0.18), 0.12, 0.05, "y-", 8)
    box("hull", p["iron"], (x, y, z + 0.15), (length - 0.1, width - 0.5, 0.34), bevel=0.04)
    box("hull_crest", p["brass"], (x + 0.1, y, z + 0.49), (0.3, 0.26, 0.03), bevel=0.0)


def lens(p, pos, facing="x+", r=0.12):
    """A lente acesa: aro de latão e chama-piloto."""
    d = _DIR[facing]
    disc("lens_rim", p["brass"], pos, r + 0.04, 0.05, facing, 10)
    disc("lens", p["flame"], _add(pos, tuple(c * 0.04 for c in d)), r, 0.04, facing, 10)


def slit(p, pos, facing="x+", w=0.5, h=0.1):
    """Fresta de fornalha acesa: a luz permanente da peça."""
    kit.window(p["soot"], p["flame"], pos, facing, w=w, h=h)


# ---------------------------------------------------------------------------------------------------------
# Tronco dos tanques: Tank Factory -> Assault | Heavy -> Rocket | Mine Layer
# ---------------------------------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------------------------------
# Tronco do ar: Aircraft Factory -> Bomber Factory
# ---------------------------------------------------------------------------------------------------------


def striped_beam(p, a, b, n=8, thick=0.16):
    """Viga listrada de amarelo-perigo e fuligem: o braço de guindaste que se lê de cima."""
    a, b = Vector(a), Vector(b)
    for i in range(n):
        beam("stripe", p["hazard"] if i % 2 == 0 else p["soot"], a.lerp(b, i / n), a.lerp(b, (i + 1) / n), thick=thick)


def h05X_tank_factory():
    """Baia-mãe: galpão comprido de teto escuro e uma porta basculante de latão enorme, levantada sobre a rampa."""
    p = pal()
    pad(p)
    plated(p, -0.45, 0.0, 2.7, 2.0, 1.1, roof="roof_dk")
    fx = 0.9
    box("door_hole", p["soot"], (fx, 0.0, 0.2), (0.06, 1.5, 0.85), bevel=0.0)
    leaf = box("door_leaf", p["brass"], (fx + 0.03 + 0.5, 0.0, 1.0), (1.0, 1.9, 0.09), bevel=0.02)
    tilt(leaf, (fx + 0.03, 0, 1.0), "Y", math.radians(-48))
    for y in (-0.85, 0.85):
        beam("door_strut", p["iron_lt"], (fx + 0.7, y, 0.12), (fx + 0.62, y, 1.5), thick=0.07)
    rivets(p, (fx + 0.2, -0.8, 1.1), (fx + 0.2, 0.8, 1.1), 5, tone="brass_dk", size=0.07)
    ramp = box("ramp", p["timber"], (fx + 0.45, 0.0, 0.1), (0.9, 1.4, 0.25), bevel=0.0)
    for v in ramp.data.vertices:
        if v.co.x > fx + 0.6 and v.co.z > 0.2:
            v.co.z = 0.1
    spur(p, -0.2, 1.75, y=-1.25, gauge_w=0.5)
    box("bogie_crate", p["timber"], (1.2, -1.25, 0.16), (0.5, 0.4, 0.28), bevel=0.02)
    box("bogie_band", p["iron_dk"], (1.2, -1.25, 0.36), (0.52, 0.42, 0.05), bevel=0.0)
    stack(p, (-1.4, 0.7, 1.25), 1.3, 0.17)
    slit(p, (-0.45, -1.0, 0.7), "y-", w=0.6, h=0.1)
    box("roof_vent", p["iron_dk"], (-0.7, -0.2, 1.25), (0.5, 0.5, 0.12), bevel=0.0)
    leak(p, fx + 0.2, 1.1, 0.2)


def heavy_bay(p, hull_on_roof=False, comb=False):
    """Baia pesada: galpão largo de teto azinhavre e portas dobradas, desvio de trilho à frente. O acréscimo
    (casco no pórtico do telhado, ou pente de foguetes) fica em cima."""
    pad(p)
    plated(p, -0.85, 0.0, 1.9, 3.3, 1.3, roof="verd_roof")
    fx = 0.1
    for s in (-1, 1):
        yy = s * 0.75
        box("door_hole", p["soot"], (fx, yy, 0.2), (0.06, 1.1, 1.0), bevel=0.0)
        box("door_leaf", p["iron_dk"], (fx + 0.04, yy, 0.2), (0.05, 1.06, 0.95), bevel=0.0)
        for z in (0.4, 0.75, 1.05):
            box("door_strap", p["iron_lt"], (fx + 0.07, yy, z), (0.04, 1.06, 0.07), bevel=0.0)
    box("door_lintel", p["iron_dk"], (fx + 0.05, 0, 1.2), (0.14, 2.9, 0.14), bevel=0.0)
    spur(p, fx, 1.75, y=0.0, gauge_w=0.9)
    stack(p, (-1.5, -1.35, 1.4), 1.1, 0.19)
    slit(p, (-0.85, -1.65, 0.7), "y-", w=0.6, h=0.1)
    leak(p, 1.4, 1.0, 0.2)
    top = 1.5
    if hull_on_roof:
        # Pórtico sobre o telhado com o casco completo no gancho: a assinatura do Heavy.
        for s in (-1, 1):
            box("gantry_post", p["iron"], (-0.6, s * 1.05, top), (0.18, 0.18, 1.5), bevel=0.02)
            beam("gantry_brace", p["iron_dk"], (-0.6, s * 1.05, top + 0.3), (-0.6, s * 0.75, top), thick=0.07)
        box("gantry_beam", p["iron"], (-0.6, 0, top + 1.45), (0.3, 2.5, 0.22), bevel=0.02)
        for s in (-1, 1):
            beam("hull_sling", p["soot"], (-0.6, s * 0.3, top + 1.45), (-0.6, s * 0.4, top + 0.72), thick=0.035)
        hull(p, (-0.6, 0.0, top + 0.05), length=1.7, width=1.5)
        box("turret", p["brass_dk"], (-0.5, 0, top + 0.55), (0.6, 0.6, 0.26), bevel=0.03)
        beam("gun", p["soot"], (-0.3, 0, top + 0.68), (0.7, 0, top + 0.7), thick=0.1)
    if comb:
        rocket_comb(p, top)
    else:
        taper("shift_bell", p["brass"], (1.3, 1.2, 0.8), (1.3, 1.2, 1.05), 0.2, 0.08, 8)
        beam("bell_post", p["iron_dk"], (1.3, 1.2, 0.1), (1.3, 1.2, 1.35), thick=0.06)
        box("hull_cradle", p["timber"], (1.3, -1.2, 0.1), (0.6, 0.4, 0.2), bevel=0.0)
    barrel(p, (1.5, -1.0, 0.1), stripe=True) if comb else None


def rocket_comb(p, top):
    """Pente alto de tubos de latão em pé sobre o telhado, inclinados para a frente: a assinatura do Rocket."""
    box("comb_base", p["iron_dk"], (-0.45, 0, top), (0.8, 2.9, 0.22), bevel=0.02)
    for i in range(8):
        y = -1.3 + i * 0.37
        taper("comb_tube", p["brass"], (-0.45, y, top + 0.2), (0.25, y, top + 1.85), 0.13, 0.13, 6)
        taper("comb_neck", p["brass_dk"], (0.25, y, top + 1.85), (0.3, y, top + 1.97), 0.13, 0.08, 6)
    for z in (0.7, 1.3):
        t = z / 1.65
        x = -0.45 + 0.7 * t
        box("comb_band", p["soot"], (x, 0, top + 0.2 + z), (0.1, 3.0, 0.07), bevel=0.0)
    board(p, (1.45, -1.3, 0.1), rot_z=math.radians(-15), lines=4)
    box("door_rocket", p["hazard"], (0.14, 0.75, 0.4), (0.03, 0.22, 0.6), bevel=0.0)
    box("door_rocket_nose", p["hazard"], (0.14, 0.75, 1.0), (0.03, 0.14, 0.1), bevel=0.0, taper=0.3)


def h09B_heavy_tank_factory():
    heavy_bay(pal(), hull_on_roof=True)


def h09H_rocket_tank_factory():
    heavy_bay(pal(), comb=True)


def h09I_assault_tank_factory():
    """Baia de montagem em L: ala comprida de dente de serra de tijolo e ala baixa da porta; o guindaste de braço listrado cobre o pátio."""
    p = pal()
    pad(p)
    plated(p, -1.15, 0.0, 1.2, 3.3, 1.0, wall="iron_dk", roof="brick_roof")
    for i in range(2):
        x0 = -1.75 + i * 0.6
        prism("sawtooth", p["brick"], (x0 + 0.3, 0, 1.2), (0.6, 3.3, 0.7), ridge=1.0, bevel=0.0)
        box("sawtooth_glass", p["glass"], (x0 + 0.6, 0, 1.28), (0.03, 3.0, 0.45), bevel=0.0)
    plated(p, 0.2, -0.95, 1.5, 1.5, 0.9, roof="brick_roof")
    fx = 0.95
    box("door_hole", p["soot"], (fx, -0.95, 0.2), (0.06, 1.0, 0.7), bevel=0.0)
    for i in range(6):
        box("hazard_band", p["hazard"] if i % 2 == 0 else p["soot"], (fx + 0.03, -1.45 + 0.17 * i, 0.12), (0.04, 0.17, 0.1), bevel=0.0)
    # Guindaste em trilho: torre, braço listrado e contrapeso, placa de casco no gancho sobre o pátio.
    spur(p, 0.6, 1.75, y=1.2, gauge_w=0.5)
    box("crane_base", p["iron_dk"], (1.25, 1.2, 0.2), (0.7, 0.7, 0.18), bevel=0.02)
    box("crane_tower", p["iron"], (1.25, 1.2, 0.38), (0.3, 0.3, 3.0), bevel=0.02, taper=0.8, taper_y=0.8)
    striped_beam(p, (1.25, 1.2, 3.35), (0.0, 0.1, 3.0), n=8, thick=0.2)
    striped_beam(p, (1.25, 1.2, 3.35), (1.7, 1.6, 3.3), n=2, thick=0.2)
    box("crane_weight", p["cake"], (1.65, 1.55, 3.0), (0.3, 0.3, 0.3), bevel=0.02)
    beam("crane_stay", p["iron_dk"], (1.25, 1.2, 3.4), (0.75, 0.75, 2.6), thick=0.05)
    beam("crane_cable", p["soot"], (0.1, 0.15, 3.0), (0.1, 0.15, 1.9), thick=0.035)
    plate = box("hull_plate", p["iron_lt"], (0.1, 0.15, 1.75), (0.8, 0.9, 0.08), bevel=0.02, rot_z=0.3)
    tilt(plate, (0.1, 0.15, 1.75), "X", math.radians(8))
    box("plate_crest", p["brass"], (0.1, 0.15, 1.83), (0.3, 0.3, 0.03), bevel=0.0, rot_z=0.3)
    beam("sling", p["soot"], (0.1, 0.15, 1.95), (-0.15, -0.05, 1.82), thick=0.03)
    beam("sling", p["soot"], (0.1, 0.15, 1.95), (0.35, 0.4, 1.82), thick=0.03)
    stack(p, (-1.5, -1.35, 1.1), 1.0, 0.16)
    slit(p, (0.2, -1.7, 0.55), "y-", w=0.55, h=0.1)
    leak(p, 1.0, 0.3, 0.2)


def h09J_mine_layer_factory():
    """Depósito de minas: galpão baixo e, ao lado, uma torre alta de tremonha amarela; fileira de minas grandes à frente."""
    p = pal()
    pad(p)
    plated(p, -1.2, 0.0, 1.1, 3.1, 0.95, roof="timber")
    box("door_hole", p["soot"], (-0.65, -0.7, 0.2), (0.06, 0.9, 0.7), bevel=0.0)
    hx, hy = 0.0, 0.85
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        beam("tower_leg", p["iron"], (hx + sx * 0.45, hy + sy * 0.45, 0.1), (hx + sx * 0.38, hy + sy * 0.38, 2.1), thick=0.1)
    for z in (0.7, 1.4):
        for s in (-1, 1):
            beam("tower_tie", p["iron_dk"], (hx - 0.42, hy + s * 0.42, z), (hx + 0.42, hy + s * 0.42, z), thick=0.06)
            beam("tower_tie", p["iron_dk"], (hx + s * 0.42, hy - 0.42, z), (hx + s * 0.42, hy + 0.42, z), thick=0.06)
    beam("tower_x", p["iron_dk"], (hx + 0.4, hy - 0.45, 0.2), (hx - 0.4, hy - 0.45, 1.4), thick=0.05)
    cyl("hopper", p["hazard"], (hx, hy, 2.1), 0.2, 1.1, sides=10, top_radius=0.85, bevel=0.0)
    cyl("hopper_mouth", p["soot"], (hx, hy, 3.21), 0.5, 0.01, sides=10, bevel=0.0)
    ring("hopper_band", p["soot"], (hx, hy, 2.5), 0.45, 0.07, thick=0.04, sides=10)
    beam("valve_lever", p["soot"], (hx + 0.2, hy, 2.15), (hx + 0.6, hy, 2.45), thick=0.05)
    box("valve_knob", p["brass"], (hx + 0.6, hy, 2.45), (0.12, 0.12, 0.12), bevel=0.0)
    beam("chute", p["iron_dk"], (hx, hy, 2.1), (1.1, 0.4, 0.5), thick=0.3)
    # Fileira de minas grandes, com pontas de espoleta, ao longo da frente.
    for i in range(5):
        y = -1.35 + i * 0.6
        cyl("mine", p["soot"], (1.35, y, 0.1), 0.3, 0.22, sides=10, top_radius=0.26, bevel=0.0)
        cyl("mine_top", p["hazard"], (1.35, y, 0.32), 0.14, 0.05, sides=8, bevel=0.0)
        for a in range(0, 360, 90):
            r = math.radians(a)
            box("mine_horn", p["brass"], (1.35 + math.cos(r) * 0.27, y + math.sin(r) * 0.27, 0.22), (0.06, 0.06, 0.1), bevel=0.0)
    board(p, (0.7, -1.4, 0.1), rot_z=math.radians(-20), lines=2)
    stack(p, (-1.5, -1.2, 1.05), 0.9, 0.15)
    slit(p, (-1.2, -1.55, 0.6), "y-", w=0.5, h=0.1)
    leak(p, 0.95, 0.4, 0.2)


def h05V_golem_factory():
    """Fundição: bloco baixo e escuro, o cadinho enorme aceso e o pórtico que segura um torso de ferro meio fundido."""
    p = pal()
    pad(p)
    plated(p, -0.95, 0.0, 1.6, 3.3, 1.0, wall="iron_dk", roof="roof_dk")
    # Cadinho grande: tijolo, cinta de latão, boca incandescente e bico de vazamento.
    cx, cy = 0.8, -0.65
    cyl("crucible", p["brick_dk"], (cx, cy, 0.1), 0.6, 0.9, sides=10, top_radius=0.78, bevel=0.0)
    ring("crucible_band", p["brass"], (cx, cy, 0.45), 0.7, 0.1, thick=0.03, sides=10)
    cyl("crucible_glow", p["flame"], (cx, cy, 0.99), 0.74, 0.04, sides=10, bevel=0.0)
    box("spout", p["iron_dk"], (cx + 0.75, cy, 0.8), (0.3, 0.3, 0.12), bevel=0.0)
    rivets(p, (cx + 0.6, cy - 0.3, 0.3), (cx + 0.6, cy + 0.3, 0.3), 4, tone="brass_dk", size=0.07)
    # Pórtico com o torso meio fundido pendurado: metade de cima cinza, metade de baixo ainda em latão.
    for x in (0.45, 1.55):
        box("gantry_post", p["iron"], (x, 1.0, 0.1), (0.18, 0.18, 2.6), bevel=0.02)
    box("gantry_beam", p["iron"], (1.0, 1.0, 2.6), (1.3, 0.24, 0.22), bevel=0.02)
    box("trolley", p["brass_dk"], (1.0, 1.0, 2.35), (0.4, 0.3, 0.24), bevel=0.02)
    for dx in (-0.2, 0.2):
        beam("torso_chain", p["soot"], (1.0 + dx, 1.0, 2.4), (1.0 + dx, 1.0, 1.85), thick=0.04)
    box("torso_chest", p["iron_lt"], (1.0, 1.0, 1.25), (0.7, 0.95, 0.6), bevel=0.03)
    box("torso_low", p["brass_dk"], (1.0, 1.0, 0.85), (0.55, 0.75, 0.4), bevel=0.03)
    for s in (-1, 1):
        box("torso_shoulder", p["iron_lt"], (1.0, 1.0 + s * 0.55, 1.4), (0.35, 0.3, 0.38), bevel=0.03)
    box("torso_plate", p["brass"], (1.37, 1.0, 1.4), (0.03, 0.3, 0.25), bevel=0.0)
    stack(p, (-1.4, 1.2, 1.15), 1.5, 0.3, puffs=3)
    gear(p, (-0.5, -1.65, 0.55), "y-", r=0.3, thick=0.06)
    slit(p, (-1.0, -1.65, 0.75), "y-", w=0.5, h=0.1)
    leak(p, 0.2, -0.3, 0.22)
    leak(p, 1.2, 0.2, 0.2)


def h05T_gun_smith():
    """Forja de campanha aberta: lareira grande de tijolo com o fogo alto à vista, parede de tubos, bigorna e fole."""
    p = pal()
    pad(p)
    box("rack_wall", p["timber"], (-1.55, 0, 0.1), (0.18, 3.2, 1.7), bevel=0.02)
    box("rack_rail", p["iron_dk"], (-1.42, 0, 1.65), (0.1, 3.2, 0.1), bevel=0.0)
    for i in range(9):
        y = -1.4 + i * 0.35
        cyl("torch_tube", p["brass"], (-1.43, y, 0.7), 0.075, 1.0, sides=6, bevel=0.0)
        cyl("torch_nozzle", p["soot"], (-1.43, y, 0.58), 0.055, 0.12, sides=6, bevel=0.0)
    # Cobertura baixa de tábuas só sobre a parede de tubos.
    for sy in (-1, 1):
        box("post", p["timber"], (-0.85, sy * 1.5, 0.1), (0.12, 0.12, 1.6), bevel=0.0)
    roof = box("roof", p["timber"], (-1.2, 0, 1.7), (0.8, 3.3, 0.08), bevel=0.02)
    shear(roof, 0, 2, -0.2, -1.2)
    # Lareira grande de tijolo com o fogo aberto: bocal, brasas e chamas altas.
    box("hearth", p["brick"], (0.1, 0.3, 0.1), (1.6, 1.6, 0.65), bevel=0.04)
    box("hearth_rim", p["brick_dk"], (0.1, 0.3, 0.75), (1.7, 1.7, 0.12), bevel=0.02)
    box("fire_bed", p["soot"], (0.1, 0.3, 0.87), (1.3, 1.3, 0.04), bevel=0.0)
    taper("flame", p["flame"], (0.1, 0.3, 0.88), (0.1, 0.3, 1.95), 0.6, 0.06, 6)
    taper("flame", p["flame"], (-0.2, 0.0, 0.88), (-0.2, 0.0, 1.45), 0.3, 0.04, 5)
    taper("flame", p["flame"], (0.4, 0.55, 0.88), (0.4, 0.55, 1.4), 0.3, 0.04, 5)
    box("hearth_mouth", p["soot"], (0.96, 0.3, 0.2), (0.05, 0.7, 0.3), bevel=0.0)
    rivets(p, (0.97, -0.3, 0.6), (0.97, 0.9, 0.6), 5, tone="brass_dk", size=0.07)
    beam("flue", p["iron_dk"], (-0.5, 0.3, 0.9), (-1.0, 0.3, 1.45), thick=0.25)
    stack(p, (-1.0, 0.3, 1.4), 0.6, 0.12, puffs=3)
    # Fole de couro, bigorna rebitada no cepo, e a bomba de graxa.
    box("bellows", p["belt"], (0.1, -1.0, 0.1), (0.9, 0.55, 0.3), bevel=0.04, taper=0.5, taper_y=0.9)
    beam("bellows_nozzle", p["soot"], (0.1, -0.7, 0.3), (0.1, -0.2, 0.6), thick=0.1)
    cyl("stump", p["timber"], (1.2, -0.6, 0.1), 0.28, 0.4, sides=8, bevel=0.0)
    box("anvil", p["iron_dk"], (1.2, -0.6, 0.5), (0.5, 0.22, 0.16), bevel=0.02)
    box("anvil_face", p["iron_lt"], (1.2, -0.6, 0.66), (0.54, 0.26, 0.05), bevel=0.0)
    beam("anvil_horn", p["iron_dk"], (1.45, -0.6, 0.58), (1.7, -0.6, 0.6), thick=0.1)
    barrel(p, (1.4, 1.35, 0.1), tone="iron")
    beam("pump_rod", p["soot"], (1.4, 1.35, 0.54), (1.4, 1.35, 0.9), thick=0.04)
    beam("pump_handle", p["iron_lt"], (1.15, 1.35, 0.9), (1.65, 1.35, 0.8), thick=0.04)
    leak(p, 1.4, 1.35, 0.25)
    leak(p, 0.7, -1.4, 0.2)
    box("tool_crate", p["timber"], (-0.7, -1.3, 0.1), (0.5, 0.4, 0.26), bevel=0.02)


def h09P_arsenal():
    """Paiol baixo de tijolo vermelho enterrado num anteparo grosso de terra: o U do anteparo é a assinatura."""
    p = pal()
    pad(p)
    box("foot", p["iron_dk"], (-0.2, 0, 0.1), (2.1, 2.4, 0.2), bevel=0.03)
    box("magazine", p["brick"], (-0.2, 0, 0.25), (2.0, 2.3, 0.85), bevel=0.04)
    box("slab", p["brick_roof"], (-0.2, 0, 1.1), (2.2, 2.5, 0.2), bevel=0.04)
    for z in (0.5, 0.85):
        box("course", p["brick_dk"], (-0.2, 0, z), (2.04, 2.34, 0.06), bevel=0.0)
    # Anteparo de terra em U (fundos e flancos), mais alto que o paiol, em talude.
    box("berm_back", p["earth_lt"], (-1.5, 0, 0.1), (0.5, 3.5, 1.3), bevel=0.0, taper=0.55, taper_y=0.95)
    for s in (-1, 1):
        box("berm_side", p["earth_lt"], (-0.55, s * 1.45, 0.1), (2.6, 0.6, 1.2), bevel=0.0, taper=0.95, taper_y=0.5)
    fx = 0.8
    for s in (-1, 1):
        box("door_leaf", p["iron_dk"], (fx + 0.04, s * 0.37, 0.25), (0.07, 0.7, 0.8), bevel=0.0)
        for z in (0.4, 0.65, 0.9):
            box("door_strap", p["iron_lt"], (fx + 0.08, s * 0.37, z), (0.04, 0.7, 0.07), bevel=0.0)
    box("door_frame", p["soot"], (fx + 0.01, 0, 0.25), (0.05, 1.55, 0.9), bevel=0.0)
    rivets(p, (fx + 0.1, -0.7, 0.88), (fx + 0.1, 0.7, 0.88), 5)
    stack(p, (-0.9, 0.7, 1.28), 0.7, 0.24, puffs=3)
    lens(p, (fx + 0.05, 0.0, 0.98), "x+", 0.09)
    # Pátio: estante de cápsulas de latão virada para a porta, barris com a faixa de inspeção.
    box("rack_frame", p["iron_dk"], (1.4, 0, 0.1), (0.1, 2.0, 0.9), bevel=0.02)
    for z in (0.45, 0.8):
        box("rack_shelf", p["iron_lt"], (1.33, 0, z), (0.2, 2.0, 0.04), bevel=0.0)
        for i in range(8):
            cyl("capsule", p["brass"], (1.33, -0.95 + i * 0.27, z + 0.04), 0.07, 0.26, sides=6, bevel=0.0)
    for (bx, by, bz) in ((1.45, 1.3, 0.1), (1.45, 1.6, 0.1), (1.0, 1.5, 0.1), (1.3, 1.45, 0.54)):
        barrel(p, (bx, by, bz), stripe=True)
    leak(p, 1.0, -0.9, 0.2)
    leak(p, 1.0, 0.9, 0.2)


def h05U_lumber_mill():
    """Serraria de poço: galpão de tábuas e uma roda de serra gigante, em pé e verde-azinhavre, com dentes de latão."""
    p = pal()
    pad(p)
    plated(p, -1.2, 0.0, 1.1, 3.0, 1.1, wall="timber", roof="roof_dk")
    wx, wz = 0.1, 1.45
    kit.begin_part("anim_saw")
    disc("saw_disc", p["verd"], (wx, 0.0, wz), 1.0, 0.12, "x+", 14)
    for i in range(16):
        a = i * math.tau / 16
        beam("saw_tooth", p["brass"], (wx + 0.06, math.cos(a) * 0.95, wz + math.sin(a) * 0.95), (wx + 0.06, math.cos(a + 0.18) * 1.32, wz + math.sin(a + 0.18) * 1.32), thick=0.16)
    disc("saw_inner", p["brass_dk"], (wx + 0.1, 0.0, wz), 0.55, 0.05, "x+", 14)
    disc("saw_hub", p["soot"], (wx + 0.12, 0.0, wz), 0.2, 0.08, "x+", 8)
    for a in range(0, 360, 60):
        r = math.radians(a)
        beam("saw_spoke", p["iron_dk"], (wx + 0.13, 0.0, wz), (wx + 0.13, math.cos(r) * 0.9, wz + math.sin(r) * 0.9), thick=0.07)
    kit.end_part()
    for s in (-1, 1):
        beam("saw_stand", p["iron_dk"], (wx - 0.15, s * 0.7, 0.1), (wx, s * 0.12, wz - 0.1), thick=0.12)
    # Esteira de toras em trilho entrando na serra, toras com óleo na fibra.
    spur(p, wx + 0.2, 1.75, y=0.0, gauge_w=0.5)
    for i, z in enumerate((0.16, 0.16, 0.45)):
        cyl("log", p["timber"], (0.9, (-0.2, 0.2, 0.0)[i], z), 0.18, 0.8, sides=8, bevel=0.0, rot=("Y", math.radians(90)))
    box("log_oil", p["oil"], (1.4, 0.0, 0.64), (0.3, 0.1, 0.012), bevel=0.0)
    gear(p, (-1.0, -1.65, 0.7), "y-", r=0.4, thick=0.1, tone="brass_dk", teeth=12)
    gear(p, (-0.3, -1.65, 0.95), "y-", r=0.25, thick=0.08, tone="brass", teeth=8)
    beam("drive_belt", p["belt"], (-1.0, -1.72, 1.1), (-0.3, -1.72, 1.2), thick=0.06)
    stack(p, (-1.5, 1.2, 1.25), 1.3, 0.2)
    slit(p, (-1.2, -1.55, 0.6), "y-", w=0.5, h=0.1)
    barrel(p, (1.4, 1.4, 0.1))
    leak(p, 1.4, 1.4, 0.22)
    leak(p, 1.0, -0.9, 0.2)


def h06Z_protection_center():
    """Clube dos barões: bunker blindado em três degraus de cor (ferro, tijolo, latão) e o holofote gigante no topo."""
    p = pal()
    pad(p)
    plated(p, -0.1, 0.0, 3.2, 3.2, 0.75, wall="iron_dk", roof="brick_roof")
    plated(p, -0.25, 0.0, 2.3, 2.3, 0.7, z0=0.95, wall="iron", roof="brass_dk")
    plated(p, -0.4, 0.0, 1.5, 1.5, 0.65, z0=1.75, wall="iron_dk", roof="brass")
    fx = 1.5
    box("gate", p["soot"], (fx + 0.03, 0.0, 0.2), (0.08, 1.0, 0.6), bevel=0.0)
    box("gate_leaf", p["iron_lt"], (fx + 0.06, 0.0, 0.25), (0.05, 0.9, 0.5), bevel=0.0)
    rivets(p, (fx + 0.1, -0.4, 0.5), (fx + 0.1, 0.4, 0.5), 4, tone="brass", size=0.07)
    for y in (-1.1, 1.1):
        kit.window(p["soot"], p["glass"], (fx, y, 0.45), "x+", w=0.4, h=0.15)
    # Guarda-corpo de ferro no terraço da frente.
    top = 0.95
    for i in range(7):
        box("rail_post", p["iron_lt"], (1.5, -1.3 + i * 0.43, top), (0.06, 0.06, 0.4), bevel=0.0)
    box("rail_top", p["iron_lt"], (1.5, 0, top + 0.38), (0.06, 2.65, 0.05), bevel=0.0)
    kit.horn(p["brass"], (1.3, 1.2, top + 0.1), (1.0, 0.3), length=0.7, radius=0.15)
    box("gallery_glass", p["glass"], (0.91, 0.0, 1.35), (0.05, 1.5, 0.3), bevel=0.0)
    # Holofote gigante: a lente acesa é a única luz.
    roof_z = 2.6
    for s in (-1, 1):
        box("yoke", p["iron_dk"], (-0.5, s * 0.5, roof_z), (0.12, 0.1, 0.55), bevel=0.0)
    a, b = (-0.8, 0.0, roof_z + 0.4), (0.5, 0.0, roof_z + 0.85)
    taper("searchlight", p["iron_lt"], a, b, 0.4, 0.52, 10)
    d = (Vector(b) - Vector(a)).normalized()
    taper("light_rim", p["brass"], tuple(Vector(b) - d * 0.1), tuple(Vector(b) + d * 0.04), 0.6, 0.6, 10)
    taper("light_lens", p["flame"], tuple(Vector(b) - d * 0.02), tuple(Vector(b) + d * 0.1), 0.5, 0.5, 10)
    stack(p, (-1.2, 0.9, 1.75), 0.7, 0.14, puffs=2)
    barrel(p, (1.55, -1.5, 0.1))
    barrel(p, (1.55, 1.5, 0.1), tone="iron")
    leak(p, 1.55, -1.5, 0.22)
    leak(p, 1.55, 0.9, 0.2)


def hangar(p, length, open_end=False):
    """Hangar de bolsa de gás: caixa comprida e baixa de teto plano, porta larga no +x, guincho no telhado."""
    pad(p)
    sy = length
    cx, sx, h = -0.75, 2.0, 1.15
    if open_end:
        # Sem a parede do fim em -y: o berço do dirigível à mostra, com cavernas de ferro.
        box("foot", p["iron_dk"], (cx, 0, 0.1), (sx + 0.12, sy + 0.12, 0.14), bevel=0.02)
        box("wall_back", p["iron"], (cx, sy / 2 - 0.1, 0.2), (sx, 0.2, h - 0.1), bevel=0.02)
        box("wall_side", p["iron"], (cx - sx / 2 + 0.1, 0, 0.2), (0.2, sy, h - 0.1), bevel=0.02)
        box("wall_front", p["iron"], (cx + sx / 2 - 0.1, 0, 0.2), (0.2, sy, h - 0.1), bevel=0.02)
        box("roof", p["roof"], (cx, 0, 0.1 + h), (sx + 0.16, sy + 0.16, 0.1), bevel=0.02)
        for y in (-1.2, -0.3, 0.6):
            box("rib", p["iron_dk"], (cx, y, 0.2), (sx, 0.12, h - 0.1), bevel=0.0)
        box("berth_line", p["hazard"], (cx, -0.4, 0.1), (sx - 0.4, 0.1, 0.012), bevel=0.0)
        rivets(p, (cx + sx / 2, sy / 2 - 0.1, 0.3), (cx + sx / 2, sy / 2 - 0.1, 0.3), 1)
        rivets(p, (cx + sx / 2 + 0.01, -sy / 2 + 0.2, 0.3), (cx + sx / 2 + 0.01, sy / 2 - 0.2, 0.3), 9)
        rivets(p, (cx + sx / 2 + 0.01, -sy / 2 + 0.2, 1.1), (cx + sx / 2 + 0.01, sy / 2 - 0.2, 1.1), 9)
    else:
        plated(p, cx, 0.0, sx, sy, h)
    fx = cx + sx / 2
    # Porta larga com a persiana enrolada em cima.
    box("door_hole", p["soot"], (fx, 0.0, 0.2), (0.06, 1.7, 0.85), bevel=0.0)
    cyl("door_roll", p["iron_dk"], (fx + 0.04, -0.85, 1.12), 0.1, 1.7, sides=8, bevel=0.0, rot=("X", math.radians(-90)))
    return fx, h


def mast(p, x, y, z, height, windsock=False):
    kit.derrick(p["iron"], p["iron_dk"], None, (x, y, z), base=0.55, top=0.22, height=height)
    if windsock:
        taper("windsock", p["canvas"], (x, y, z + height - 0.25), (x + 0.95, y, z + height - 0.4), 0.22, 0.09, 8)
        taper("windsock_band", p["hazard"], (x + 0.35, y, z + height - 0.31), (x + 0.5, y, z + height - 0.34), 0.17, 0.15, 8)
        taper("windsock_band", p["soot"], (x + 0.6, y, z + height - 0.35), (x + 0.72, y, z + height - 0.37), 0.13, 0.12, 8)


def winch_gantry(p, x, y, z):
    """Cavalete de guincho no telhado: A de ferro e tambor de latão."""
    for s in (-1, 1):
        beam("winch_leg", p["iron_dk"], (x - 0.25, y + s * 0.4, z), (x, y + s * 0.4, z + 0.6), thick=0.07)
        beam("winch_leg", p["iron_dk"], (x + 0.25, y + s * 0.4, z), (x, y + s * 0.4, z + 0.6), thick=0.07)
    cyl("winch_drum", p["brass_dk"], (x, y - 0.4, z + 0.52), 0.14, 0.8, sides=8, bevel=0.0, rot=("X", math.radians(-90)))
    disc("winch_flange", p["brass"], (x, y - 0.42, z + 0.52), 0.24, 0.04, "y-", 8)
    beam("winch_crank", p["soot"], (x, y - 0.46, z + 0.52), (x + 0.2, y - 0.46, z + 0.78), thick=0.04)


def h05J_aircraft_factory():
    p = pal()
    fx, h = hangar(p, 2.7)
    top = 0.1 + h + 0.1
    mast(p, -1.25, 1.0, top, 2.7, windsock=True)
    winch_gantry(p, -0.45, -0.3, top)
    # Cabo diagonal do topo do mastro até o canto da frente, e o tirante de pátio.
    beam("cable", p["soot"], (-1.25, 1.0, top + 2.65), (fx - 0.1, -1.3, top), thick=0.035)
    beam("tether", p["soot"], (-1.25, 1.0, top + 2.65), (1.55, 0.7, 0.12), thick=0.03)
    stack(p, (-1.5, -0.95, top), 0.8, 0.15)
    slit(p, (-0.75, -1.45, 0.75), "y-", w=0.6, h=0.1)
    barrel(p, (1.25, -0.9, 0.1), stripe=True)
    leak(p, 1.25, -0.9, 0.22)
    gear(p, (-0.2, -1.42, 0.7), "y-", r=0.2, thick=0.05)
    # Biruta estampada com o número do poço, em placa de giz junto da porta.
    box("well_number", p["ecru"], (fx + 0.03, 1.2, 0.5), (0.03, 0.4, 0.3), bevel=0.0)
    box("well_number_bar", p["soot"], (fx + 0.05, 1.2, 0.62), (0.02, 0.3, 0.05), bevel=0.0)


def h09L_bomber_factory():
    p = pal()
    fx, h = hangar(p, 3.3, open_end=True)
    top = 0.1 + h + 0.1
    mast(p, -1.4, 1.35, top, 2.6)
    mast(p, -1.4, -1.35, top, 2.6, windsock=True)
    beam("mast_span", p["soot"], (-1.4, 1.35, top + 2.55), (-1.4, -1.35, top + 2.55), thick=0.045)
    beam("cable", p["soot"], (-1.4, -1.35, top + 2.5), (fx - 0.05, 1.3, top), thick=0.035)
    winch_gantry(p, -0.45, 0.2, top)
    stack(p, (-1.45, 0.1, top), 0.7, 0.15)
    slit(p, (fx - 0.02, 0.0, 0.2), "x+", w=0.05, h=0.05)
    # Dentro do berço aberto: a cinta do casco e o vão de fuligem.
    box("cradle_sling", p["belt"], (-0.75, -0.9, 0.18), (1.6, 0.18, 0.05), bevel=0.0)
    box("lamp_post", p["iron_dk"], (-0.75, -1.45, 0.1), (0.08, 0.08, 0.6), bevel=0.0)
    lens(p, (-0.75, -1.5, 0.6), "y-", 0.1)
    # Carrinho de bombas em trilho: quatro vãos, um sem caixote.
    spur(p, fx, 1.75, y=0.0, gauge_w=0.7)
    box("trolley", p["iron_dk"], (1.1, 0.0, 0.2), (0.7, 1.1, 0.12), bevel=0.02)
    for i in range(4):
        y = -0.4 + i * 0.27
        if i == 2:
            continue
        cyl("bomb", p["cake"], (1.1, y, 0.32), 0.1, 0.45, sides=8, top_radius=0.1, bevel=0.0, rot=("Y", math.radians(90)))
        cyl("bomb_nose", p["brass_dk"], (1.4, y, 0.32), 0.1, 0.12, sides=8, top_radius=0.02, bevel=0.0, rot=("Y", math.radians(90)))
    barrel(p, (1.45, -1.2, 0.1))
    leak(p, 1.45, -1.2, 0.22)


# ---------------------------------------------------------------------------------------------------------
# Fundição: Golem Factory -> Precious Golem Factory
# ---------------------------------------------------------------------------------------------------------


def crucible_niche(p, x, y, w=1.1, h=0.85):
    """Nicho do cadinho ao rés do chão, onde o corpo é 'acordado': a boca incandescente."""
    box("niche_frame", p["soot"], (x, y, 0.1), (0.14, w + 0.2, h + 0.15), bevel=0.0)
    box("niche_glow", p["flame"], (x + 0.03, y, 0.15), (0.12, w - 0.1, h - 0.15), bevel=0.0)
    box("niche_lintel", p["iron_dk"], (x, y, 0.1 + h + 0.15), (0.2, w + 0.3, 0.12), bevel=0.0)
    leaf = box("niche_door", p["iron_dk"], (x + 0.04, y + w / 2 + 0.38, 0.1), (0.07, 0.62, h), bevel=0.0)
    tilt(leaf, (x + 0.04, y + w / 2 + 0.1, 0.1), "Z", math.radians(-55))


def h097_precious_golem_factory():
    """Torre-forja: a mesma fundição promovida a torre estreita, duas chaminés e a roldana coroada com a corrente."""
    p = pal()
    pad(p)
    plated(p, -0.55, 0.0, 1.9, 2.3, 2.0)
    box("skirt", p["iron_dk"], (-0.2, 0, 0.1), (2.7, 3.0, 0.4), bevel=0.04, taper=0.94, taper_y=0.96)
    fx = 0.4
    crucible_niche(p, fx + 0.1, 0.0, w=1.0, h=0.75)
    for s in (-1, 1):
        stack(p, (-1.4, s * 0.8, 2.1), 1.1, 0.17, puffs=2)
    # Cabeçalho: pernas em A, roldana coroada, lança e corrente sobre o cadinho.
    top = 2.1
    for s in (-1, 1):
        beam("frame_leg", p["iron"], (-0.9, s * 0.55, top), (-0.55, s * 0.28, 3.7), thick=0.12)
        beam("frame_leg", p["iron"], (-0.15, s * 0.55, top), (-0.55, s * 0.28, 3.7), thick=0.12)
    beam("frame_tie", p["iron_dk"], (-0.9, -0.55, top + 0.8), (-0.15, -0.55, top + 0.8), thick=0.07)
    gear(p, (-0.55, -0.34, 3.35), "y-", r=0.5, thick=0.1, tone="brass", teeth=8)
    for i in range(6):
        a = i * math.tau / 6 + 0.2
        beam("wheel_spoke", p["soot"], (-0.55, -0.4, 3.35), (-0.55 + math.cos(a) * 0.45, -0.46, 3.35 + math.sin(a) * 0.45), thick=0.04)
    for i in range(5):
        a = math.radians(40 + i * 25)
        beam("crown", p["brass"], (-0.55 + math.cos(a) * 0.45, -0.3, 3.35 + math.sin(a) * 0.45 + 0.02), (-0.55 + math.cos(a) * 0.7, -0.3, 3.35 + math.sin(a) * 0.7 + 0.1), thick=0.06)
    beam("jib", p["iron"], (-0.55, 0, 3.7), (1.0, 0.0, 3.35), thick=0.13)
    beam("jib_stay", p["iron_dk"], (-0.2, 0, 2.1), (0.55, 0, 3.5), thick=0.06)
    disc("jib_pulley", p["brass_dk"], (1.0, -0.08, 3.25), 0.18, 0.1, "y+", 8)
    for i in range(12):
        z = 3.15 - i * 0.2
        box("chain_link", p["soot"], (1.0, 0.0, z), (0.08, 0.14 if i % 2 == 0 else 0.07, 0.15), bevel=0.0)
    cyl("crucible_bucket", p["brass_dk"], (1.0, 0.0, 0.3), 0.3, 0.4, sides=8, top_radius=0.36, bevel=0.0)
    ring("bucket_band", p["soot"], (1.0, 0.0, 0.5), 0.34, 0.06, sides=8)
    taper("shift_bell", p["brass"], (0.3, 0.35, 3.0), (0.3, 0.35, 3.3), 0.18, 0.07, 8)
    beam("bell_arm", p["iron_dk"], (0.3, 0.35, 3.3), (0.3, 0.0, 3.42), thick=0.05)
    box("bell_clapper", p["iron_lt"], (0.3, 0.35, 2.94), (0.06, 0.06, 0.08), bevel=0.0)
    barrel(p, (1.4, -1.25, 0.1))
    leak(p, 1.4, -1.25, 0.24)
    leak(p, 0.85, 0.45, 0.2)
    rivets(p, (fx + 0.02, -0.85, 1.5), (fx + 0.02, 0.85, 1.5), 7)


# ---------------------------------------------------------------------------------------------------------
# Ferraria e paiol: Gun Smith -> Arsenal
# ---------------------------------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------------------------------
# Serraria: Lumber Mill -> Protection Center
# ---------------------------------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------------------------------
# Geradores de escudo: Blue -> Red
# ---------------------------------------------------------------------------------------------------------


def dynamo(p, red=False):
    """Dínamo de barril rebitado com cúpula de vidro: o escudo é um capacitor carregado queimando óleo."""
    r = 1.05 if red else 0.95
    pad(p, (3.5, 3.5) if red else (3.1, 3.1))
    field = p["red"] if red else p["blue"]
    box("plinth", p["iron_dk"], (0, 0, 0.1), (2.5 if red else 2.3, 2.5 if red else 2.3, 0.26), bevel=0.04, taper=0.94, taper_y=0.94)
    cyl("drum", p["iron"], (0, 0, 0.36), r, 1.0, sides=12, bevel=0.0)
    for z in (0.55, 1.15):
        ring("drum_band", p["brass_dk"], (0, 0, z), r, 0.1, thick=0.03, sides=12)
        for i in range(14):
            a = i * math.tau / 14
            box("drum_rivet", p["iron_lt"], (math.cos(a) * (r + 0.05), math.sin(a) * (r + 0.05), z + 0.1), (0.06, 0.06, 0.06), bevel=0.0, rot_z=a)
    cyl("cap", p["iron_dk"], (0, 0, 1.36), r, 0.14, sides=12, top_radius=r * 0.82, bevel=0.0)
    ring("dome_ring", p["brass"], (0, 0, 1.5), 0.6, 0.1, thick=0.04, sides=12)
    dome("dome", field, (0, 0, 1.6), 0.58, squash=1.0, sides=12)
    # Duas bobinas de latão com bulbos de vidro apagado.
    for sy in (-1, 1):
        bx, by = -0.55, sy * 0.62
        cyl("coil", p["brass"], (bx, by, 1.5), 0.13, 0.5, sides=8, bevel=0.0)
        for z in (1.6, 1.8):
            ring("coil_ring", p["brass_dk"], (bx, by, z), 0.13, 0.06, thick=0.03, sides=8)
        dome("bulb", p["glass"], (bx, by, 2.0), 0.2, squash=1.1, sides=8)
    # Cabos de aterramento descendo até hastes cravadas na lama.
    for pts in (((r - 0.02, -0.35, 0.8), (r + 0.3, -0.5, 0.55), (1.45, -1.0, 0.25)), ((-r + 0.05, 0.3, 0.8), (-r - 0.35, 0.6, 0.5), (-1.4, 1.0, 0.25))):
        for a, b in itertools.pairwise(pts):
            beam("earth_cable", p["soot"], a, b, thick=0.06)
        cyl("earth_rod", p["iron_lt"], (pts[-1][0], pts[-1][1], 0.1), 0.05, 0.4, sides=6, bevel=0.0)
        box("earth_clamp", p["brass"], (pts[-1][0], pts[-1][1], 0.25), (0.14, 0.14, 0.1), bevel=0.0)
    box("live_plate", p["hazard"], (r, 0.0, 0.62), (0.07, 0.8, 0.45), bevel=0.0)
    for i in range(3):
        box("live_text", p["soot"], (r + 0.03, 0.0, 0.7 + i * 0.1), (0.03, 0.55 - 0.1 * i, 0.04), bevel=0.0)
    stack(p, (0.45, 0.65, 1.45), 0.7, 0.1, puffs=2)
    leak(p, 1.2, 0.8, 0.22)
    return r, field


def h06J_blue_shield_generator():
    p = pal()
    dynamo(p)
    barrel(p, (-1.2, -1.0, 0.1))
    leak(p, -1.2, -1.0, 0.2)


def h05R_red_shield_generator():
    """O dínamo azul em sobrecarga: bancos de bobina nos flancos, manivela externa com corrente, domo rachado."""
    p = pal()
    r, _ = dynamo(p, red=True)
    for sy in (-1, 1):
        y = sy * 1.3
        box("bank", p["iron_dk"], (0.0, y, 0.1), (1.1, 0.5, 0.95), bevel=0.04)
        for i in range(4):
            cyl("bank_coil", p["brass"] if i % 2 == 0 else p["brass_dk"], (-0.4 + i * 0.27, y, 1.05), 0.13, 0.3, sides=8, bevel=0.0)
        rivets(p, (-0.4, y - 0.26, 0.9), (0.4, y - 0.26, 0.9), 4, size=0.055)
    # Manivela de sobrecarga no +x, com a corrente pendurada.
    beam("crank_shaft", p["iron_dk"], (r, 0.0, 0.95), (r + 0.5, 0.0, 0.95), thick=0.09)
    disc("crank_wheel", p["brass_dk"], (r + 0.5, -0.06, 0.95), 0.3, 0.06, "y-", 8)
    beam("crank_handle", p["soot"], (r + 0.5, -0.1, 0.95), (r + 0.5, -0.1, 1.25), thick=0.05)
    for i in range(6):
        box("crank_chain", p["soot"], (r + 0.5, -0.1, 0.75 - i * 0.11), (0.06, 0.07 if i % 2 else 0.12, 0.11), bevel=0.0)
    # Rachaduras escuras sobre o domo vermelho e queimaduras na carcaça.
    for pts in (((0.0, 0.05), (0.2, -0.2), (0.15, -0.4)), ((-0.1, 0.1), (-0.3, 0.3), (-0.45, 0.25))):
        zs = [1.6 + math.sqrt(max(0.58**2 - x * x - y * y, 0.0)) + 0.01 for x, y in pts]
        for i in range(len(pts) - 1):
            beam("dome_crack", p["soot"], (pts[i][0], pts[i][1], zs[i]), (pts[i + 1][0], pts[i + 1][1], zs[i + 1]), thick=0.04)
    for ang in (0.4, 2.2, 3.6):
        box("scorch", p["soot"], (math.cos(ang) * (r + 0.02), math.sin(ang) * (r + 0.02), 0.45), (0.1, 0.5, 0.5), bevel=0.0, rot_z=ang)
    leak(p, 0.5, -1.0, 0.3)


# ---------------------------------------------------------------------------------------------------------
# Torre de energia e casa de força
# ---------------------------------------------------------------------------------------------------------


def h05L_energy_tower():
    """Pilha de força: gaiola de treliça de ferro com bobinas de latão empilhadas, isoladores de vidro e bulbos."""
    p = pal()
    pad(p, (2.9, 2.9))
    box("footing", p["iron_dk"], (0, 0, 0.1), (2.0, 2.0, 0.3), bevel=0.04, taper=0.9, taper_y=0.9)
    kit.derrick(p["iron"], p["iron_dk"], None, (0, 0, 0.4), base=1.6, top=0.9, height=3.2)
    cyl("core", p["iron_dk"], (0, 0, 0.4), 0.18, 3.2, sides=8, bevel=0.0)
    for i in range(6):
        z = 0.7 + i * 0.5
        rad = 0.5 - 0.035 * i
        cyl("coil", p["brass"], (0, 0, z), rad, 0.26, sides=10, bevel=0.0)
        ring("coil_ring", p["brass_dk"], (0, 0, z + 0.08), rad, 0.07, thick=0.02, sides=10)
        cyl("insulator", p["glass"], (0, 0, z + 0.26), rad * 0.5, 0.24, sides=8, bevel=0.0)
        ring("insulator_rim", p["verd"], (0, 0, z + 0.34), rad * 0.5, 0.05, thick=0.05, sides=8)
    cyl("cap_plate", p["brass_dk"], (0, 0, 3.7), 0.4, 0.08, sides=10, bevel=0.0)
    kit.begin_part("anim_bulbs")
    for a in (0.0, 2.1, 4.2):
        dome("bulb", p["glass"], (math.cos(a) * 0.25, math.sin(a) * 0.25, 3.78), 0.22, squash=1.2, sides=8)
    dome("bulb", p["glass"], (0, 0, 3.98), 0.24, squash=1.2, sides=8)
    # Para-raios curvo que joga a corrente entre os alvos.
    pts = [(0, 0, 4.2), (0, 0, 4.5), (0.3, 0, 4.72), (0.65, 0, 4.66), (0.9, 0, 4.42)]
    for a, b in itertools.pairwise(pts):
        beam("rod", p["iron_lt"], a, b, thick=0.06)
    box("rod_tip", p["brass"], (0.9, 0, 4.36), (0.1, 0.1, 0.1), bevel=0.0)
    kit.end_part()
    # Queimador dedicado ao pé, com a fresta acesa e o respiro fumegante.
    box("burner", p["iron"], (1.15, 0.0, 0.1), (0.55, 1.0, 0.8), bevel=0.04)
    box("burner_roof", p["roof"], (1.15, 0.0, 0.9), (0.65, 1.1, 0.08), bevel=0.0)
    slit(p, (1.425, 0.0, 0.4), "x+", w=0.6, h=0.14)
    rivets(p, (1.43, -0.4, 0.75), (1.43, 0.4, 0.75), 4)
    stack(p, (1.1, 0.35, 0.98), 0.6, 0.1, puffs=2)
    beam("feed_pipe", p["iron_dk"], (0.9, -0.2, 0.7), (0.5, -0.2, 1.0), thick=0.08)
    barrel(p, (1.2, 1.15, 0.1))
    leak(p, 1.2, 1.15, 0.22)


def h09T_power_plant():
    """Casa da caldeira: bloco largo de três chaminés escalonadas e fendas de fornalha, coluna de fracionamento no flanco."""
    p = pal()
    pad(p, (3.5, 3.6))
    plated(p, -0.45, 0.3, 2.7, 2.7, 1.4)
    fx = 0.9
    # Fendas de fornalha acesas em fiada, no +x e no -y.
    for y in (-0.55, 0.1, 0.75, 1.4):
        slit(p, (fx, y, 0.55), "x+", w=0.4, h=0.1)
    for x in (-1.2, -0.45, 0.3):
        slit(p, (x, -1.05, 0.55), "y-", w=0.4, h=0.1)
    top = 0.1 + 1.4 + 0.1
    for (sx, sy, hh, rr) in ((-1.3, -0.45, 2.0, 0.2), (-0.8, 0.55, 2.5, 0.23), (-1.3, 1.45, 2.2, 0.2)):
        stack(p, (sx, sy, top), hh, rr, puffs=2)
    box("steam_dome", p["iron_dk"], (0.1, 0.3, top), (0.8, 0.8, 0.25), bevel=0.04, taper=0.7, taper_y=0.7)
    cyl("steam_drum", p["iron"], (0.0, 0.3, top + 0.2), 0.3, 0.3, sides=10, bevel=0.0)
    gauge(p, (fx + 0.04, 1.4, 1.1), "x+", 0.18)
    # Coluna de fracionamento baixa no flanco -y, com bandejas, escada e respiro.
    cx, cy = 0.55, -1.38
    cyl("column", p["iron_lt"], (cx, cy, 0.1), 0.38, 2.4, sides=10, top_radius=0.3, bevel=0.0)
    for z in (0.5, 1.1, 1.7):
        ring("column_tray", p["brass_dk"], (cx, cy, z), 0.38 - z * 0.03, 0.08, sides=10)
    cyl("column_cap", p["brass"], (cx, cy, 2.5), 0.2, 0.18, sides=8, top_radius=0.1, bevel=0.0)
    smoke(p, (cx, cy, 2.7), scale=0.7, n=2, tone="smoke")
    beam("ladder", p["iron_dk"], (cx + 0.4, cy - 0.2, 0.1), (cx + 0.3, cy - 0.3, 2.0), thick=0.05)
    # Linhas de vapor rente ao chão rumo aos vizinhos.
    kit.pipe_run(p["iron_dk"], p["brass_dk"], [(cx + 0.2, cy, 0.3), (1.15, cy, 0.3), (1.15, 0.0, 0.3), (1.7, 0.0, 0.3)], radius=0.075)
    # Painel transformador de latão com isoladores de vidro, no pátio da frente.
    box("transformer", p["iron_dk"], (1.35, 1.0, 0.1), (0.5, 0.8, 0.6), bevel=0.03)
    box("transformer_panel", p["brass"], (1.62, 1.0, 0.25), (0.04, 0.55, 0.35), bevel=0.0)
    for y in (0.75, 1.0, 1.25):
        cyl("insulator", p["glass"], (1.35, y, 0.7), 0.07, 0.3, sides=6, bevel=0.0)
        ring("insulator_cap", p["verd"], (1.35, y, 0.95), 0.07, 0.05, thick=0.03, sides=6)
    barrel(p, (1.45, 1.55, 0.1))
    leak(p, 1.45, 1.55, 0.25)


# ---------------------------------------------------------------------------------------------------------
# Subterrâneo e foguetes: Demolition Lab -> Rocket Lab
# ---------------------------------------------------------------------------------------------------------


def h05M_demolition_lab():
    """Adega-bunker semienterrada: um monte baixo com escotilha de ferro aberta, respiro com névoa de pólvora."""
    p = pal()
    pad(p)
    cyl("mound", p["earth"], (-0.15, 0, 0.1), 1.75, 0.8, sides=10, top_radius=1.25, bevel=0.0)
    cyl("mound_plate", p["cake"], (-0.15, 0, 0.9), 1.25, 0.07, sides=10, bevel=0.0)
    for i in range(10):
        a = i * math.tau / 10
        box("plate_rivet", p["iron_lt"], (-0.15 + math.cos(a) * 1.1, math.sin(a) * 1.1, 0.96), (0.07, 0.07, 0.05), bevel=0.0)
    # Escotilha: moldura e tampa levantada, com a brasa da lâmpada lá dentro.
    box("hatch_frame", p["iron_dk"], (-0.5, -0.1, 0.97), (1.0, 1.0, 0.1), bevel=0.02)
    box("hatch_hole", p["soot"], (-0.5, -0.1, 1.07), (0.8, 0.8, 0.02), bevel=0.0)
    lid = box("hatch_lid", p["iron"], (-0.5, -0.1 - 0.5, 1.07), (1.0, 1.0, 0.07), bevel=0.02)
    tilt(lid, (-0.5, -0.6, 1.07), "X", math.radians(58))
    rivets(p, (-0.9, -0.1 - 0.5 - 0.35, 1.17), (-0.1, -0.1 - 0.5 - 0.35, 1.17), 4, size=0.06)
    # Respiro com névoa de pólvora.
    cyl("vent", p["iron_dk"], (-0.9, 0.75, 0.95), 0.12, 0.8, sides=8, bevel=0.0)
    ring("vent_band", p["brass"], (-0.9, 0.75, 1.4), 0.12, 0.07, sides=8)
    smoke(p, (-0.9, 0.75, 1.78), scale=0.9, n=3, tone="haze")
    # Escada de acesso: casinhola de entrada na face +x, porta de ferro e lâmpada pendurada.
    box("head_house", p["iron"], (1.0, 0.0, 0.3), (0.9, 1.3, 0.75), bevel=0.04)
    box("head_roof", p["roof"], (1.0, 0.0, 1.05), (1.0, 1.4, 0.09), bevel=0.02)
    box("door_hole", p["soot"], (1.46, 0.0, 0.3), (0.06, 0.8, 0.6), bevel=0.0)
    box("door_leaf", p["iron_dk"], (1.49, 0.0, 0.3), (0.06, 0.74, 0.58), bevel=0.0)
    for z in (0.45, 0.7):
        box("door_strap", p["iron_lt"], (1.52, 0.0, z), (0.03, 0.74, 0.06), bevel=0.0)
    rivets(p, (1.47, -0.5, 0.9), (1.47, 0.5, 0.9), 5)
    for i in range(3):
        box("step", p["iron_dk"], (1.65 + i * 0.1, 0.0, 0.1), (0.14, 0.9, 0.08 - i * 0.02 + 0.02), bevel=0.0)
    beam("lamp_arm", p["iron_dk"], (1.5, -0.45, 1.0), (1.7, -0.45, 1.0), thick=0.05)
    beam("lamp_chain", p["soot"], (1.7, -0.45, 1.0), (1.7, -0.45, 0.82), thick=0.025)
    box("lamp_cage", p["brass"], (1.7, -0.45, 0.62), (0.18, 0.18, 0.2), bevel=0.0)
    box("lamp_flame", p["flame"], (1.7, -0.45, 0.67), (0.11, 0.11, 0.12), bevel=0.0)
    box("no_fire", p["hazard"], (1.78, -0.45, 0.85), (0.02, 0.24, 0.14), bevel=0.0)
    # Barris de nitroglicerina com o selo de cera e latão do barão.
    for (bx, by, bz) in ((0.4, -1.35, 0.1), (0.8, -1.4, 0.1), (0.6, -1.25, 0.54)):
        barrel(p, (bx, by, bz), tone="iron", stripe=True)
        cyl("wax_seal", p["brick_dk"], (bx + 0.16, by, bz + 0.15), 0.07, 0.03, sides=8, bevel=0.0, rot=("Y", math.radians(90)))
    leak(p, 0.6, -1.0, 0.25)


def h077_rocket_lab():
    """Oficina torta: galpão entortado, trilho de lançamento a pino no céu com o foguete de latão no berço."""
    p = pal()
    pad(p)
    body = box("lab", p["iron"], (-0.9, 0.0, 0.1), (1.9, 2.5, 1.35), bevel=0.0)
    shear(body, 2, 0, 0.45, 0.1)
    foot = box("foot", p["iron_dk"], (-0.9, 0.0, 0.1), (2.0, 2.6, 0.14), bevel=0.0)
    del foot
    roof = box("roof", p["roof"], (-0.65, 0.0, 1.45), (2.1, 2.7, 0.1), bevel=0.0)
    shear(roof, 1, 2, 0.4, 0.0)
    for i in range(6):
        box("rivet", p["iron_lt"], (0.05 + 0.28 * 0.2, -1.0 + i * 0.4, 0.3), (0.06, 0.06, 0.06), bevel=0.0)
    door = box("door", p["soot"], (0.11, 0.1, 0.2), (0.06, 0.95, 0.85), bevel=0.0)
    shear(door, 2, 0, 0.45, 0.1)
    slit(p, (-0.9, -1.3, 0.75), "y-", w=0.55, h=0.1)
    # Trilho de lançamento: dois varais inclinados, escora e dormentes, apontando para o céu.
    for s in (-1, 1):
        beam("launch_rail", p["iron_lt"], (0.75, s * 0.14, 0.15), (1.3, s * 0.14, 3.55), thick=0.07)
    for t in (0.2, 0.45, 0.7, 0.9):
        a = Vector((0.75, 0, 0.15)).lerp(Vector((1.3, 0, 3.55)), t)
        beam("launch_tie", p["iron_dk"], (a.x, -0.14, a.z), (a.x, 0.14, a.z), thick=0.05)
    beam("launch_strut", p["iron_dk"], (1.65, 0.0, 0.1), (1.1, 0.0, 2.3), thick=0.09)
    box("launch_base", p["iron_dk"], (0.9, 0, 0.1), (0.8, 0.7, 0.14), bevel=0.0)
    a, b = Vector((0.9, 0.0, 0.95)), Vector((1.22, 0.0, 2.8))
    taper("rocket", p["brass"], tuple(a), tuple(b), 0.14, 0.14, 8)
    d = (b - a).normalized()
    taper("rocket_nose", p["brass_dk"], tuple(b), tuple(b + d * 0.5), 0.14, 0.01, 8)
    taper("rocket_band", p["soot"], tuple(a + d * 0.6), tuple(a + d * 0.72), 0.15, 0.15, 8)
    for s in (-1, 1):
        beam("rocket_fin", p["iron_dk"], tuple(a + d * 0.05), (a.x - 0.05, s * 0.3, a.z - 0.05), thick=0.05)
    # Pára-quedas de lona pendurado no gancho com a etiqueta TEST LATER, e a chaminé baixa e única.
    beam("hook_arm", p["iron_dk"], (-0.9, -1.3, 1.1), (-0.9, -1.5, 1.1), thick=0.06)
    beam("hook_drop", p["iron_dk"], (-0.9, -1.5, 1.1), (-0.9, -1.5, 0.9), thick=0.04)
    dome("parachute", p["canvas"], (-0.9, -1.5, 0.5), 0.3, squash=0.8, sides=10)
    for a_ in (0.0, 2.1, 4.2):
        beam("chute_line", p["soot"], (-0.9 + math.cos(a_) * 0.35, -1.5 + math.sin(a_) * 0.28, 0.5), (-0.9, -1.5, 0.9), thick=0.015)
    box("test_tag", p["ecru"], (-0.9, -1.55, 0.7), (0.18, 0.02, 0.12), bevel=0.0)
    stack(p, (-1.55, 0.9, 1.5), 0.7, 0.14, puffs=3)
    barrel(p, (1.3, 1.2, 0.1))
    leak(p, 1.3, 1.2, 0.24)
    box("cradle_crate", p["timber"], (0.4, -1.3, 0.1), (0.5, 0.4, 0.28), bevel=0.02)
    leak(p, 0.5, 0.9, 0.2)


# ---------------------------------------------------------------------------------------------------------
# Monte de sucata
# ---------------------------------------------------------------------------------------------------------


def h069_spare_part_heap():
    """O monte de sucata como prédio: chapas, rodas e barril podre, tenda-alçapão, braseiro fumegante e cavalete."""
    p = pal()
    cyl("pad", p["mud"], (0, 0, 0), 1.75, 0.1, sides=9, top_radius=1.7, bevel=0.0)
    rnd = random.Random(11)
    tones = ("iron", "iron_dk", "iron_lt", "brass_dk", "cake", "belt")
    # Monte assimétrico: massa para -x/+y, rala para o lado do cavalete.
    placed = 0
    while placed < 26:
        x, y = rnd.uniform(-1.4, 0.7), rnd.uniform(-0.9, 1.4)
        d = math.hypot(x + 0.5, y - 0.4)
        z = 0.1 + max(0.0, 1.05 - 0.7 * d)
        if d > 1.45:
            continue
        pl = box("scrap", p[rnd.choice(tones)], (x, y, z), (rnd.uniform(0.5, 0.95), rnd.uniform(0.35, 0.7), rnd.uniform(0.07, 0.12)), bevel=0.0, rot_z=rnd.uniform(0, math.pi))
        tilt(pl, (x, y, z), rnd.choice("XY"), rnd.uniform(-0.45, 0.45))
        placed += 1
    for wx, wy, wz, wr in ((0.55, -0.55, 0.1, 0.42), (-1.25, -0.55, 0.45, 0.35), (-0.1, 1.45, 0.1, 0.38)):
        disc("wheel", p["cake"], (wx, wy, wz + wr), wr, 0.14, "y-", 10)
        disc("wheel_hub", p["brass_dk"], (wx, wy - 0.12, wz + wr), wr * 0.45, 0.05, "y-", 8)
    # Barril podre, tombado, e o pé-de-cabra.
    cyl("rot_barrel", p["belt"], (0.35, 0.7, 0.35), 0.2, 0.55, sides=8, bevel=0.0, rot=("X", math.radians(70)))
    leak(p, 0.35, 0.3, 0.3)
    # Tenda de couro com alçapão de tábuas no topo do monte.
    prism("tent", p["belt"], (-0.55, 0.45, 1.05), (0.9, 0.85, 0.5), ridge=0.5, bevel=0.0)
    trap = box("trapdoor", p["timber"], (-0.1, 0.45, 0.95), (0.4, 0.5, 0.05), bevel=0.0)
    tilt(trap, (-0.1, 0.45, 0.95), "Y", math.radians(40))
    # Braseiro com respiro: o monte fuma.
    cyl("brazier", p["iron_dk"], (-1.05, 1.0, 0.6), 0.2, 0.3, sides=8, top_radius=0.28, bevel=0.0)
    box("brazier_fire", p["flame"], (-1.05, 1.0, 0.88), (0.2, 0.2, 0.08), bevel=0.0)
    for i in range(3):
        beam("brazier_leg", p["soot"], (-1.05 + math.cos(i * 2.1) * 0.2, 1.0 + math.sin(i * 2.1) * 0.2, 0.3), (-1.05, 1.0, 0.65), thick=0.05)
    cyl("vent", p["iron_dk"], (-0.75, 1.15, 0.7), 0.1, 1.2, sides=8, bevel=0.0)
    ring("vent_band", p["brass"], (-0.75, 1.15, 1.45), 0.1, 0.06, sides=8)
    smoke(p, (-0.75, 1.15, 1.95), scale=0.9, n=3)
    # Cavalete de madeira com corda e polia, e o quadro de giz sempre errado.
    for s in (-1, 1):
        beam("gantry_leg", p["timber"], (1.1, -0.2 + s * 0.35, 0.1), (1.0, -0.2 + s * 0.1, 2.0), thick=0.1)
    beam("gantry_top", p["timber"], (1.0, -0.4, 2.0), (1.0, 0.0, 2.0), thick=0.1)
    beam("gantry_boom", p["timber"], (1.0, -0.2, 2.0), (0.2, 0.0, 1.7), thick=0.08)
    beam("rope", p["belt"], (0.2, 0.0, 1.7), (0.2, 0.0, 1.1), thick=0.03)
    box("rope_hook", p["brass"], (0.2, 0.0, 1.0), (0.1, 0.1, 0.1), bevel=0.0)
    beam("rope_stay", p["belt"], (1.0, -0.2, 2.0), (1.5, 0.3, 0.1), thick=0.03)
    board(p, (1.3, 1.05, 0.1), rot_z=math.radians(-30), lines=3)
    barrel(p, (1.2, -1.2, 0.1), tone="iron")
    leak(p, 1.2, -1.2, 0.22)
    rivets(p, (0.5, -0.8, 0.3), (0.9, -0.5, 0.3), 3)


BUILDINGS = {
    "h05X": h05X_tank_factory,
    "h09B": h09B_heavy_tank_factory,
    "h09H": h09H_rocket_tank_factory,
    "h09I": h09I_assault_tank_factory,
    "h09J": h09J_mine_layer_factory,
    "h05J": h05J_aircraft_factory,
    "h09L": h09L_bomber_factory,
    "h05V": h05V_golem_factory,
    "h097": h097_precious_golem_factory,
    "h05T": h05T_gun_smith,
    "h09P": h09P_arsenal,
    "h05U": h05U_lumber_mill,
    "h06Z": h06Z_protection_center,
    "h06J": h06J_blue_shield_generator,
    "h05R": h05R_red_shield_generator,
    "h05L": h05L_energy_tower,
    "h09T": h09T_power_plant,
    "h05M": h05M_demolition_lab,
    "h077": h077_rocket_lab,
    "h069": h069_spare_part_heap,
}

VIEWS = {"front": -35.0, "back": 150.0, "game": -90.0}


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["all"]
    names = list(BUILDINGS) if args[0] == "all" else [args[0]]
    out_dir = game_paths.out_arg(args, "--out", "buildings", "mech")
    render_dir = args[args.index("--render") + 1] if "--render" in args else ""
    tags = args[args.index("--views") + 1].split(",") if "--views" in args else ["front"]
    draw = kit.render
    kit.render = lambda path, yaw, **kw: draw(path, yaw, **{**kw, "span": kw["span"] * 1.3})  # prévia com folga
    for name in names:
        kit.build(name, out_dir, render_dir, make=BUILDINGS[name], views=tuple((t, VIEWS[t]) for t in tags))


if __name__ == "__main__":
    main()
