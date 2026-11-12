"""Mapa Dunas (docs/maps.md): castelos e cenário do Deserto, modelados por script.

Uso:
    blender -b --factory-startup --python tools/blender/map_desert.py -- <nome|all> [--out assets] [--render DIR]

--out é a pasta assets: castelos vão para castles/sand_*.glb, o resto para scenery/desert/. Usa o kit de map_castles.py
(+x aponta para a lane, z é a altura). Tamanhos seguem o que o Terrain espera de cada peça (ver o brief dos
mapas): muralha 3,2 x 1,1, pilar 1,1 x 1,1, vão do portão em meio-modelo, árvore de 5, peça central em raio 1,5.
Cor chapada por peça, sem textura. Meio-dia duro: areia, ocre, cal nos topos; acento turquesa, carmim e anil.
"""

import itertools
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import map_castles as kit
from map_castles import beam, box, cyl, dome, mat, prism, ring
from map_scenery import normalize, sandbag

SAND_GROUND = 0xD6BA8A  # chão das prévias: a classe "s" do tema


def palette():
    return {
        "sand": mat("sand", 0xD9BC84),
        "sand_lt": mat("sand_light", 0xEBD8A6),
        "sand_dk": mat("sand_dark", 0xB8955C),
        "adobe": mat("adobe", 0xB07B4C),
        "adobe_dk": mat("adobe_dark", 0x86583A),
        "adobe_lt": mat("adobe_light", 0xCFA06C),
        "white": mat("whitewash", 0xF2E9D2),
        "wood": mat("wood", 0x7A5230),
        "wood_dk": mat("wood_dark", 0x4A301E),
        "crimson": mat("crimson", 0xB3262B),
        "indigo": mat("indigo", 0x2D3A8C),
        "turq": mat("turquoise", 0x22B5AE),
        "turq_dk": mat("turquoise_dark", 0x138A8A),
        "gold": mat("gold", 0xE0A82E),
        "red": mat("sandstone", 0xA6563A),
        "red_dk": mat("sandstone_dark", 0x7A3F2C),
        "red_lt": mat("sandstone_light", 0xC9774D),
        "stone": mat("ruin_stone", 0xD5BC92),
        "stone_dk": mat("ruin_stone_dark", 0xA68E68),
        "leaf": mat("palm_leaf", 0x6E9444),
        "leaf_dk": mat("palm_leaf_dark", 0x4F7634),
        "leaf_dry": mat("palm_leaf_dry", 0xB19A52),
        "trunk": mat("palm_trunk", 0x8C6A44),
        "trunk_dk": mat("palm_trunk_dark", 0x634730),
        "date": mat("date", 0xA5552A),
        "twig": mat("twig", 0x8E7A48),
        "twig_dk": mat("twig_dark", 0x5E4C2C),
        "iron": mat("iron", 0x2E3236),
        "steel": mat("steel", 0x59626B),
        "steel_lt": mat("steel_light", 0x9AA3A8),
        "rust": mat("rust", 0x9A4B28),
        "hazard": mat("hazard", 0xE8B21C),
        "concrete": mat("concrete", 0xB2AA94),
        "concrete_dk": mat("concrete_dark", 0x7C766A),
        "paint": mat("bleached_paint", 0xD2C29C),
        "tin": mat("corrugated", 0xB7BEBD),
        "tin_dk": mat("corrugated_dark", 0x8D9594),
        "water": mat("oasis_water", 0x2BC2BA),
        "reed": mat("reed", 0xB59B58),
        "reed_dk": mat("reed_dark", 0x8F7840),
        "pad": mat("lily_pad", 0x4F8A3C),
        "bloom": mat("lily_bloom", 0xD9437A),
        "sack": mat("sack", 0xC9B287),
        "lamp": mat("lamp", 0xFFC658, emit=3.0),
        "fire": mat("fire", 0xFF8A1E, emit=3.5),
        "fire_core": mat("fire_core", 0xFFD860, emit=4.0),
        "void": mat("void", 0x1C1713),
    }


# ---------------------------------------------------------------------------------------------------------
# Ferramentas além do kit
# ---------------------------------------------------------------------------------------------------------


def limb(material, a, b, r1, r2, sides=7):
    """Gomo de tronco/galho afinando de r1 em a até r2 em b."""
    a, b = Vector(a), Vector(b)
    d = b - a
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=r1, radius2=r2, depth=d.length * 1.04)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, d.length / 2))
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=d.to_track_quat("Z", "Y").to_matrix())
    bmesh.ops.translate(bm, verts=bm.verts, vec=a)
    return kit._finish(bm, "limb", material)


def ribbon(material, pts, widths, drop=0.02):
    """Tira plana (folha, pano) seguindo pts; duas faces com um fio de espessura para não brigar na profundidade."""
    pts = [Vector(q) for q in pts]
    bm = bmesh.new()
    rows = []
    for i, q in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        side = t.cross(Vector((0, 0, 1)))
        side = side.normalized() if side.length > 1e-4 else Vector((0, 1, 0))
        w = widths[i] / 2
        rows.append(tuple(bm.verts.new(q + side * s * w) for s in (1, -1)) + tuple(bm.verts.new(q + side * s * w - Vector((0, 0, drop))) for s in (1, -1)))
    for r0, r1 in itertools.pairwise(rows):
        bm.faces.new((r0[0], r1[0], r1[1], r0[1]))
        bm.faces.new((r0[3], r1[3], r1[2], r0[2]))
    bm.faces.new(rows[0][:2] + rows[0][2:][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit._finish(bm, "ribbon", material)


def panel(material, a, b, width, thick=0.05):
    """Chapa de a até b (comprimento), larga na horizontal; serve para chapa de aço e telha inclinadas."""
    a, b = Vector(a), Vector(b)
    d = b - a
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= width
        v.co.y *= thick
        v.co.z = (v.co.z + 0.5) * d.length
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=d.to_track_quat("Z", "Y").to_matrix())
    bmesh.ops.translate(bm, verts=bm.verts, vec=a)
    return kit._finish(bm, "panel", material)


def cloth(material, p0, p1, p2, p3, thick=0.03):
    """Pano: quadrilátero p0..p3 (ordem de contorno) com espessura vertical."""
    pts = [Vector(q) for q in (p0, p1, p2, p3)]
    bm = bmesh.new()
    top = [bm.verts.new(q) for q in pts]
    bot = [bm.verts.new(q - Vector((0, 0, thick))) for q in pts]
    bm.faces.new(top)
    bm.faces.new(bot[::-1])
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((top[i], bot[i], bot[j], top[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit._finish(bm, "cloth", material)


def striped_awning(m1, m2, x0, x1, y0, y1, z_lo, z_hi, stripes=4, along_y=True):
    """Toldo listrado inclinado; z_lo na borda baixa (x0 se along_y, senão y0)."""
    for i in range(stripes):
        a, b = i / stripes, (i + 1) / stripes
        if along_y:
            ya, yb = y0 + (y1 - y0) * a, y0 + (y1 - y0) * b
            cloth(m1 if i % 2 == 0 else m2, (x0, ya, z_lo), (x1, ya, z_hi), (x1, yb, z_hi), (x0, yb, z_lo))
        else:
            xa, xb = x0 + (x1 - x0) * a, x0 + (x1 - x0) * b
            cloth(m1 if i % 2 == 0 else m2, (xa, y0, z_lo), (xa, y1, z_hi), (xb, y1, z_hi), (xb, y0, z_lo))


def jar(body, trim, pos, radius=0.2, height=0.5):
    """Ânfora/pote de barro: barriga, pescoço e boca."""
    x, y, z = pos
    cyl("jar_body", body, (x, y, z), radius * 0.55, height * 0.12, sides=8, bevel=0.0)
    cyl("jar_belly", body, (x, y, z + height * 0.1), radius, height * 0.5, sides=9, top_radius=radius * 0.45, bevel=0.0)
    cyl("jar_neck", body, (x, y, z + height * 0.58), radius * 0.4, height * 0.28, sides=8, top_radius=radius * 0.5, bevel=0.0)
    ring("jar_lip", trim, (x, y, z + height * 0.84), radius * 0.44, height * 0.1, thick=0.02, sides=8)


def rounded_merlons(material, cap, a, b, z, count, fixed, along_x, radius=0.14, height=0.22):
    """Ameias de adobe arredondadas: tambor curto com calota de cal."""
    step = (b - a) / count
    for i in range(count):
        c = a + (i + 0.5) * step
        pos = (c, fixed) if along_x else (fixed, c)
        cyl("merlon", material, (pos[0], pos[1], z), radius, height, sides=8, top_radius=radius * 0.85, bevel=0.0)
        dome("merlon_cap", cap, (pos[0], pos[1], z + height), radius * 0.92, squash=0.55, sides=8)


def beam_ends(material, a, b, z, fixed, along_x, reach, count, size=0.09):
    """Pontas de vigas de madeira que furam o adobe nas duas faces (a cabeça das vigas do forro)."""
    step = (b - a) / count
    for i in range(count):
        c = a + (i + 0.5) * step
        for s in (-1, 1):
            pos = (c, s * fixed, z) if along_x else (s * fixed, c, z)
            dims = (size, reach, size) if along_x else (reach, size, size)
            box("beam_end", material, (pos[0], pos[1], pos[2]), dims, bevel=0.0)


def tumbleweed(material, pos, radius):
    """Bola de galhos: três anéis octogonais cruzados."""
    x, y, z = pos
    for axis in range(3):
        pts = []
        for k in range(9):
            a = k * math.tau / 8
            c, s = math.cos(a) * radius, math.sin(a) * radius
            pts.append(Vector((x, y, z)) + (Vector((c, s, 0)), Vector((0, c, s)), Vector((c, 0, s)))[axis])
        for q0, q1 in itertools.pairwise(pts):
            beam("tumble", material, q0, q1, thick=0.045)


# ---------------------------------------------------------------------------------------------------------
# Muralha de adobe, pilar e vão do portão
# ---------------------------------------------------------------------------------------------------------


def sand_wall():
    """Muralha de tijolo de barro: talude, ameias redondas, cabeças de viga e topo caiado."""
    p = palette()
    length, thick = 3.2, 1.1
    box("foot", p["adobe_dk"], (0, 0, 0), (length, 1.0, 0.25), bevel=0.0, taper=1.0, taper_y=0.94)
    box("body", p["adobe"], (0, 0, 0.2), (length, 0.92, 0.9), bevel=0.04, taper=1.0, taper_y=0.76)
    box("band", p["adobe_lt"], (0, 0, 0.58), (length, 0.84, 0.08), bevel=0.0, taper=1.0, taper_y=0.9)
    box("top", p["white"], (0, 0, 1.05), (length, 0.7, 0.12), bevel=0.03)
    beam_ends(p["wood"], -length / 2 + 0.2, length / 2 - 0.2, 0.86, 0.37, True, 0.2, 5)
    rounded_merlons(p["adobe_lt"], p["white"], -length / 2 + 0.08, length / 2 - 0.08, 1.17, 5, 0.0, True, height=0.18)
    for x in (-1.1, 0.9):
        box("patch", p["adobe_dk"], (x, -0.44, 0.35), (0.5, 0.05, 0.3), bevel=0.0)
    box("drift", p["sand"], (0.4, 0.4, 0.0), (1.4, 0.5, 0.36), bevel=0.1, taper=0.5, taper_y=0.4)
    normalize(length, thick)


def sand_pillar():
    """Pilar de portão: torre quadrada de adobe em talude com nicho de lamparina e estandarte de pano."""
    p = palette()
    box("foot", p["adobe_dk"], (0, 0, 0), (1.1, 1.1, 0.25), bevel=0.04)
    box("shaft", p["adobe"], (0, 0, 0.22), (0.92, 0.92, 1.6), bevel=0.05, taper=0.76, taper_y=0.76)
    box("band", p["adobe_lt"], (0, 0, 1.1), (0.7, 0.7, 0.1), bevel=0.0)
    box("niche", p["void"], (0.24, 0, 1.3), (0.18, 0.3, 0.38), bevel=0.0)
    box("lamp", p["lamp"], (0.3, 0, 1.38), (0.1, 0.14, 0.18), bevel=0.0)
    box("cap", p["white"], (0, 0, 1.78), (0.78, 0.78, 0.14), bevel=0.03)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        box("tooth", p["white"], (sx * 0.28, sy * 0.28, 1.92), (0.2, 0.2, 0.2), bevel=0.04)
        beam("beam_end", p["wood"], (sx * 0.2, sy * 0.4, 1.55), (sx * 0.2, sy * 0.58, 1.55), thick=0.1)
    beam("pole", p["wood_dk"], (-0.1, -0.52, 0.9), (-0.1, -0.52, 2.4), thick=0.06)
    box("banner", p["crimson"], (-0.1, -0.34, 1.6), (0.03, 0.3, 0.72), bevel=0.0)
    box("banner_stripe", p["indigo"], (-0.1, -0.34, 1.9), (0.04, 0.3, 0.16), bevel=0.0)
    normalize(1.1, 1.1, 1.83)


def sand_arch():
    """Meio vão do portão (o Terrain espelha): viga de madeira com panos tingidos pendurados."""
    p = palette()
    z0, z1 = 0.98, 1.22
    for y in (-0.14, 0.14):
        beam("chord", p["wood"], (-0.5, y, z0 + 0.09), (0.0, y, z0 + 0.09), thick=0.17)
    box("lintel", p["wood_dk"], (-0.25, 0, z1 - 0.02), (0.5, 0.4, 0.08), bevel=0.0)
    box("lintel_top", p["white"], (-0.25, 0, z1 + 0.04), (0.5, 0.32, 0.05), bevel=0.0)
    for i, x in enumerate((-0.44, -0.3, -0.16)):
        c = (p["crimson"], p["indigo"], p["turq"])[i]
        box("cloth", c, (x, -0.17, 0.62), (0.1, 0.02, 0.44), bevel=0.0)
        box("cloth_tail", c, (x + 0.02, -0.17, 0.56), (0.06, 0.02, 0.06), bevel=0.0)
    box("lamp", p["lamp"], (-0.05, 0, z0 - 0.06), (0.06, 0.08, 0.07), bevel=0.0)
    box("cord", p["wood_dk"], (-0.05, 0, z0 - 0.0), (0.012, 0.012, 0.03), bevel=0.0)


# ---------------------------------------------------------------------------------------------------------
# Palmeiras, toco
# ---------------------------------------------------------------------------------------------------------


def frond(p, base, angle, length, i, rise=0.5, drop=0.9, width=0.5):
    """Folha de tamareira: eixo arqueado que sobe e despenca, tira serrilhada."""
    dirv = Vector((math.cos(angle), math.sin(angle), 0))
    pts, widths = [], []
    for k in range(7):
        t = k / 6
        pts.append(Vector(base) + dirv * length * t + Vector((0, 0, length * (rise * t - drop * t * t))))
        widths.append(width * math.sin(math.pi * min(1.0, t * 0.9 + 0.1)) * (1.0 if k % 2 == 0 else 0.55) + 0.04)
    ribbon(p["leaf"] if i % 2 == 0 else p["leaf_dk"], pts, widths)
    limb(p["trunk_dk"], pts[0], pts[-1] * 0.0 + pts[3], 0.035, 0.02, sides=4)


def palm_crown(p, top, count=8, length=1.7, seed=0.0):
    for i in range(count):
        a = seed + i * math.tau / count
        frond(p, top, a, length * (0.85 + 0.25 * ((i * 5) % 3) / 2), i)
    for i in range(3):
        a = seed + i * 2.1 + 0.4
        cyl("dates", p["date"], (top[0] + math.cos(a) * 0.14, top[1] + math.sin(a) * 0.14, top[2] - 0.34), 0.1, 0.24, sides=6, top_radius=0.06, bevel=0.0)


def palm_trunk(p, pts, r0, r1):
    """Tronco segmentado: gomos alternando dois tons e uma cinta de cicatriz em cada junta."""
    n = len(pts) - 1
    for i, (a, b) in enumerate(itertools.pairwise(pts)):
        ra = r0 + (r1 - r0) * i / n
        rb = r0 + (r1 - r0) * (i + 1) / n
        limb(p["trunk"] if i % 2 == 0 else p["trunk_dk"], a, b, ra, rb, sides=7)
        ring("scar", p["trunk_dk"], (b[0], b[1], b[2] - 0.05), rb, 0.1, thick=0.03, sides=7)
    cyl("root", p["trunk_dk"], (pts[0][0], pts[0][1], 0), r0 * 1.5, 0.25, sides=7, top_radius=r0 * 1.05, bevel=0.0)


def curve_pts(top, count, bend=(0.0, 0.0)):
    """Pontos do eixo de (0,0,0) até top, abaulados para o lado bend (parábola)."""
    out = []
    for i in range(count + 1):
        t = i / count
        out.append(Vector((top[0] * t + bend[0] * math.sin(math.pi * t), top[1] * t + bend[1] * math.sin(math.pi * t), top[2] * t)))
    return out


def sand_palm_a():
    p = palette()
    pts = curve_pts((0.35, 0.1, 4.45), 8, (0.18, -0.08))
    palm_trunk(p, pts, 0.26, 0.15)
    palm_crown(p, pts[-1], count=9, length=1.8)


def sand_palm_b():
    """Palmeira torta: tronco que sai de lado e volta."""
    p = palette()
    pts = curve_pts((1.25, 0.3, 3.8), 8, (-0.7, 0.2))
    palm_trunk(p, pts, 0.28, 0.16)
    palm_crown(p, pts[-1], count=7, length=1.6, seed=0.5)


def sand_palm_c():
    """Palmeira gêmea: dois troncos da mesma raiz, um mais baixo."""
    p = palette()
    a = curve_pts((0.5, 0.2, 4.4), 8, (0.1, 0.0))
    b = curve_pts((-0.8, -0.3, 3.3), 7, (-0.2, 0.1))
    palm_trunk(p, a, 0.22, 0.14)
    palm_trunk(p, b, 0.2, 0.13)
    palm_crown(p, a[-1], count=7, length=1.55)
    palm_crown(p, b[-1], count=6, length=1.35, seed=1.0)


def sand_stump():
    """Toco de palmeira cortada: gomos, fibras no topo e duas folhas secas no chão."""
    p = palette()
    pts = [Vector((0, 0, 0)), Vector((0.03, 0, 0.3)), Vector((0.0, 0.03, 0.6))]
    palm_trunk(p, pts, 0.32, 0.26)
    cyl("cut", p["sand_lt"], (0, 0.03, 0.58), 0.25, 0.06, sides=7, bevel=0.0)
    for i in range(7):
        a = i * math.tau / 7
        kit.spike(p["trunk_dk"], (math.cos(a) * 0.2, 0.03 + math.sin(a) * 0.2, 0.62), height=0.28 + 0.06 * (i % 2), radius=0.045, lean=(math.cos(a) * 0.06, math.sin(a) * 0.06))
    ribbon(p["leaf_dry"], [(0.5, 0.2, 0.04), (0.9, 0.5, 0.1), (1.3, 0.55, 0.05), (1.7, 0.45, 0.03)], [0.05, 0.3, 0.26, 0.05])
    ribbon(p["leaf_dry"], [(-0.4, -0.3, 0.04), (-0.8, -0.7, 0.1), (-1.0, -1.1, 0.05)], [0.05, 0.28, 0.05])


def sand_fallen():
    """Palmeira caída (tronco da extensão): tronco deitado em gomos, raízes arrancadas e folhas secas no chão."""
    p = palette()
    pts = [Vector((-1.6 + i * 0.4, 0.12 * math.sin(i * 0.8), 0.3)) for i in range(9)]
    for i, (a, b) in enumerate(itertools.pairwise(pts)):
        limb(p["trunk"] if i % 2 == 0 else p["trunk_dk"], a, b, 0.27 - 0.012 * i, 0.27 - 0.012 * (i + 1), sides=7)
    for k in range(6):
        a = k * math.tau / 6
        kit.spike(p["trunk_dk"], (-1.6, 0.0, 0.3), height=0.6, radius=0.07, lean=(-0.35, math.cos(a) * 0.5))
    for k in range(7):
        a = -1.2 + k * 0.4
        ribbon(p["leaf_dry"], [(1.7, 0.0, 0.32), (1.7 + math.cos(a) * 0.8, math.sin(a) * 0.8, 0.2), (1.7 + math.cos(a) * 1.5, math.sin(a) * 1.5, 0.05)], [0.05, 0.34, 0.06])


# ---------------------------------------------------------------------------------------------------------
# "Arbustos": espinheiro seco e toldo de tenda
# ---------------------------------------------------------------------------------------------------------


def sand_thorn():
    """Espinheiro seco com uma bola-de-feno ao lado (lugar do arbusto)."""
    p = palette()
    box("mound", p["sand_dk"], (0, 0, 0), (1.3, 1.0, 0.07), bevel=0.03, taper=0.7, taper_y=0.7)
    for i in range(13):
        a = i * 2.4
        tip = Vector((math.cos(a) * (0.35 + 0.1 * (i % 3)), math.sin(a) * (0.3 + 0.08 * (i % 3)), 0.55 + 0.1 * (i % 4)))
        limb(p["twig"] if i % 2 == 0 else p["twig_dk"], (math.cos(a) * 0.05, math.sin(a) * 0.05, 0.05), tip, 0.045, 0.02, sides=4)
        for k in (-1, 1):
            kit.spike(p["twig"], tip * 0.8 + Vector((0, 0, 0.05)), height=0.2, radius=0.025, lean=(math.cos(a + k) * 0.18, math.sin(a + k) * 0.18))
    for i in range(5):
        a = i * 1.3
        ribbon(p["leaf_dry"], [(math.cos(a) * 0.1, math.sin(a) * 0.1, 0.4), (math.cos(a) * 0.4, math.sin(a) * 0.35, 0.6)], [0.04, 0.12])
    tumbleweed(p["twig"], (0.72, -0.25, 0.3), 0.3)
    tumbleweed(p["twig_dk"], (0.74, -0.22, 0.3), 0.22)


def sand_tent():
    """Toldo baixo de lona listrada com tapetes (lugar do arbusto)."""
    p = palette()
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        beam("pole", p["wood"], (sx * 0.8, sy * 0.55, 0.0), (sx * 0.8, sy * 0.55, 0.78 if sx < 0 else 0.5), thick=0.07)
    striped_awning(p["crimson"], p["white"], -0.85, 0.85, -0.62, 0.62, 0.78, 0.5, stripes=6, along_y=False)
    box("valance", p["indigo"], (0.85, 0.0, 0.34), (0.03, 1.24, 0.16), bevel=0.0)
    box("rug", p["indigo"], (0.0, 0.0, 0.0), (1.5, 0.95, 0.03), bevel=0.0)
    box("rug_band", p["gold"], (0.0, 0.0, 0.03), (1.0, 0.55, 0.01), bevel=0.0)
    box("rug2", p["turq"], (0.35, 0.78, 0.0), (0.7, 0.4, 0.03), bevel=0.0, rot_z=0.2)
    box("cushion", p["crimson"], (-0.4, 0.15, 0.03), (0.3, 0.3, 0.14), bevel=0.05)
    box("cushion", p["gold"], (-0.3, -0.25, 0.03), (0.26, 0.26, 0.12), bevel=0.05, rot_z=0.5)
    jar(p["adobe_lt"], p["turq_dk"], (0.45, -0.1, 0.03), radius=0.17, height=0.42)


# ---------------------------------------------------------------------------------------------------------
# "Pedras": afloramento, ruína soterrada, pilha de carga
# ---------------------------------------------------------------------------------------------------------


def sand_outcrop():
    """Afloramento de arenito vermelho em estratos."""
    p = palette()
    layers = (
        (p["red_dk"], (0.0, 0.0, 0.0), (3.4, 2.8, 0.55), 0.62, 0.1),
        (p["red"], (-0.1, 0.1, 0.5), (2.7, 2.2, 0.5), 0.78, 0.4),
        (p["red_lt"], (-0.2, 0.0, 0.95), (1.9, 1.6, 0.42), 0.8, 0.8),
        (p["red"], (-0.15, -0.05, 1.33), (1.2, 1.0, 0.36), 0.86, 1.1),
    )
    for m, c, size, tp, rz in layers:
        box("strata", m, c, size, bevel=0.1, taper=tp, taper_y=tp, rot_z=rz)
    box("spire", p["red_lt"], (0.9, -0.6, 0.45), (0.8, 0.7, 1.1), bevel=0.08, taper=0.5, taper_y=0.55, rot_z=0.4)
    box("shard", p["red_dk"], (-1.2, -0.9, 0.0), (0.7, 0.5, 0.4), bevel=0.06, taper=0.6, taper_y=0.7, rot_z=1.0)
    box("drift", p["sand"], (1.3, 0.9, 0.0), (1.2, 0.8, 0.3), bevel=0.1, taper=0.5, taper_y=0.5)


def sand_ruin():
    """Ruína meio soterrada: coluna quebrada, tambores caídos e um arco incompleto."""
    p = palette()
    box("mound", p["sand"], (0, 0, 0), (3.3, 2.6, 0.4), bevel=0.2, taper=0.55, taper_y=0.55)
    box("plinth", p["stone_dk"], (-0.7, 0.2, 0.2), (1.1, 1.1, 0.3), bevel=0.04, rot_z=0.2)
    for i, h in enumerate((0.42, 0.4, 0.34)):
        cyl("drum", p["stone"] if i % 2 == 0 else p["stone_dk"], (-0.7, 0.2, 0.48 + sum((0.42, 0.4)[:i])), 0.4 - 0.02 * i, h, sides=10, top_radius=0.38 - 0.02 * i, bevel=0.0)
    box("break", p["stone"], (-0.66, 0.2, 1.66), (0.3, 0.32, 0.12), bevel=0.0, taper=0.4, taper_y=0.5)
    cyl("fallen", p["stone"], (0.3, -0.8, 0.45), 0.38, 1.3, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
    box("block", p["stone_dk"], (1.0, 0.6, 0.0), (0.7, 0.55, 0.45), bevel=0.05, rot_z=0.5)
    # Arco: um pilar em pé e meio arco que sobe e para.
    box("pier", p["stone"], (1.3, -0.1, 0.0), (0.45, 0.5, 1.2), bevel=0.04)
    c = Vector((0.75, -0.1, 1.2))
    for k in range(3):
        a0, a1 = math.radians(k * 38), math.radians((k + 1) * 38)
        beam("voussoir", p["stone"] if k % 2 == 0 else p["stone_dk"], c + Vector((math.cos(a0) * 0.55, 0, math.sin(a0) * 0.5)), c + Vector((math.cos(a1) * 0.55, 0, math.sin(a1) * 0.5)), thick=0.34)


def sand_cargo():
    """Carga de caravana largada: fardos amarrados, ânforas, caixotes e um tapete enrolado."""
    p = palette()
    box("sand", p["sand_dk"], (0, 0, 0), (3.4, 2.5, 0.08), bevel=0.03, taper=0.8, taper_y=0.8)
    bales = (((-0.9, -0.3, 0.05), (1.0, 0.7, 0.62), 0.2), ((0.1, -0.5, 0.05), (0.9, 0.7, 0.56), -0.3), ((-0.45, -0.38, 0.62), (0.9, 0.62, 0.5), 0.1))
    for c, s, rz in bales:
        box("bale", p["sack"], c, s, bevel=0.07, rot_z=rz)
        box("bale_strap", p["crimson"], (c[0], c[1], c[2] + s[2] * 0.35), (s[0] * 0.18, s[1] * 1.03, s[2] * 0.13), bevel=0.0, rot_z=rz)
    box("crate", p["wood"], (0.9, 0.55, 0.05), (0.75, 0.6, 0.55), bevel=0.02, rot_z=0.4)
    box("crate_band", p["wood_dk"], (0.9, 0.55, 0.32), (0.78, 0.63, 0.07), bevel=0.0, rot_z=0.4)
    box("crate2", p["wood"], (1.35, 0.0, 0.05), (0.55, 0.5, 0.42), bevel=0.02, rot_z=-0.2)
    for i, (x, y) in enumerate(((-0.9, 0.7), (-0.4, 0.85), (0.2, 0.75), (-1.35, 0.35))):
        jar(p["adobe_lt"] if i % 2 == 0 else p["red_lt"], p["turq_dk"] if i == 1 else p["wood_dk"], (x, y, 0.05), radius=0.26, height=0.78)
    cyl("rolled_rug", p["crimson"], (-0.3, -1.0, 0.2), 0.2, 1.1, sides=8, bevel=0.0, rot=("X", math.radians(90)))
    cyl("rolled_rug_stripe", p["indigo"], (-0.3, -0.6, 0.2), 0.22, 0.14, sides=8, bevel=0.0, rot=("X", math.radians(90)))
    beam("pole", p["wood"], (1.0, -0.9, 0.05), (1.5, -0.7, 0.9), thick=0.08)
    cloth(p["indigo"], (1.5, -0.7, 0.9), (1.5, -0.9, 0.9), (1.1, -0.95, 0.5), (1.15, -0.75, 0.5), thick=0.02)


# ---------------------------------------------------------------------------------------------------------
# Peça central: poço do oásis
# ---------------------------------------------------------------------------------------------------------


def sand_well():
    """Poço de oásis com shaduf (alavanca de contrapeso); esteiras e vitórias-régias rente à água (<= 0,06)."""
    p = palette()
    cx = 0.6
    cyl("flags", p["stone_dk"], (cx, 0, 0), 1.05, 0.08, sides=14, bevel=0.0)
    cyl("curb", p["stone"], (cx, 0, 0.06), 0.82, 0.5, sides=14, top_radius=0.76, bevel=0.03)
    cyl("curb_water", p["water"], (cx, 0, 0.52), 0.6, 0.03, sides=14, bevel=0.0)
    ring("curb_rim", p["white"], (cx, 0, 0.55), 0.78, 0.07, thick=0.0, sides=14)
    for i in range(6):
        a = i * math.tau / 6 + 0.3
        box("curb_block", p["stone_dk"], (cx + math.cos(a) * 0.81, math.sin(a) * 0.81, 0.2), (0.2, 0.3, 0.18), bevel=0.02, rot_z=a)
    # Shaduf: dois postes de barro, travessa e alavanca com balde de um lado e contrapeso de barro do outro.
    for y in (-0.5, 0.5):
        box("post", p["adobe"], (-0.35, y, 0.0), (0.26, 0.24, 1.7), bevel=0.04, taper=0.7, taper_y=0.7)
    beam("cross", p["wood_dk"], (-0.35, -0.52, 1.62), (-0.35, 0.52, 1.62), thick=0.1)
    a, b = Vector((-1.3, 0, 2.05)), Vector((1.0, 0, 1.45))
    beam("lever", p["wood"], a, b, thick=0.13)
    sph = Vector((-1.3, 0, 1.6))
    box("weight", p["adobe_dk"], (sph.x, sph.y, sph.z), (0.5, 0.5, 0.45), bevel=0.14, taper=0.8, taper_y=0.8)
    beam("rope", p["wood_dk"], (1.0, 0, 1.45), (1.0, 0, 0.88), thick=0.025)
    cyl("bucket", p["wood_dk"], (1.0, 0, 0.68), 0.18, 0.22, sides=8, top_radius=0.14, bevel=0.0)
    ring("bucket_rim", p["gold"], (1.0, 0, 0.9), 0.16, 0.03, thick=0.0, sides=8)
    # Cocho, potes e bandeirolas de pano na ponta dos postes.
    box("trough", p["stone"], (-0.2, -1.05, 0.0), (1.1, 0.4, 0.3), bevel=0.04)
    box("trough_water", p["water"], (-0.2, -1.05, 0.26), (0.94, 0.26, 0.03), bevel=0.0)
    jar(p["adobe_lt"], p["turq_dk"], (-0.2, 1.0, 0.0), radius=0.2, height=0.5)
    jar(p["red_lt"], p["wood_dk"], (0.15, 1.15, 0.0), radius=0.17, height=0.42)
    for y, c in ((-0.5, "crimson"), (0.5, "indigo")):
        beam("flag_pole", p["wood_dk"], (-0.35, y, 1.62), (-0.35, y, 2.2), thick=0.04)
        cloth(p[c], (-0.35, y, 2.18), (-0.35, y + 0.34, 2.12), (-0.35, y + 0.34, 1.86), (-0.35, y, 1.9), thick=0.02)
    # Esteiras de junco e vitórias-régias pela lagoa (chatas, 0,045 de altura).
    pads = ((-3.4, 2.2, 0.55), (-2.1, -3.0, 0.45), (3.3, 2.8, 0.6), (4.6, -1.4, 0.5), (1.5, -4.1, 0.42), (-5.2, -0.8, 0.5), (0.2, 4.2, 0.5), (5.4, 3.9, 0.4), (-4.2, -3.8, 0.45), (2.8, -2.6, 0.35))
    for i, (x, y, r) in enumerate(pads):
        cyl("pad", p["pad"], (x, y, 0.04), r, 0.006, sides=9, bevel=0.0, rot=("Z", i * 0.7))
        cyl("pad_notch", p["water"], (x + r * 0.5, y, 0.047), r * 0.28, 0.004, sides=3, bevel=0.0, rot=("Z", i * 0.7))
        if i % 3 == 0:
            cyl("bloom", p["bloom"], (x - r * 0.2, y + r * 0.2, 0.046), r * 0.22, 0.012, sides=6, bevel=0.0)
    mats = ((-1.9, 3.4, 0.3), (2.3, 3.9, 1.2), (-4.6, 2.4, 2.0), (3.9, -3.5, 0.6), (-3.1, -1.6, 1.6), (5.1, 0.4, 2.4))
    for i, (x, y, rz) in enumerate(mats):
        box("mat", p["reed"], (x, y, 0.04), (1.3, 0.85, 0.012), bevel=0.0, rot_z=rz)
        for k in range(3):
            box("mat_strip", p["reed_dk"], (x + math.cos(rz) * (k - 1) * 0.3, y + math.sin(rz) * (k - 1) * 0.3, 0.052), (0.05, 0.84, 0.006), bevel=0.0, rot_z=rz)
    # Flotsam de uma jangada de caniço.
    box("raft_log", p["wood"], (-3.2, 0.6, 0.04), (1.2, 0.2, 0.02), bevel=0.0, rot_z=0.5)


# ---------------------------------------------------------------------------------------------------------
# Decoração fora do andável
# ---------------------------------------------------------------------------------------------------------


def sand_windpump():
    """Bomba eólica de treliça (kind 0, torre alta): roda de pás, leme e cocho de pedra."""
    p = palette()
    box("pad", p["sand_dk"], (0, 0, 0), (3.6, 3.6, 0.18), bevel=0.06, taper=0.9, taper_y=0.9)
    kit.derrick(p["steel_lt"], p["steel"], None, (0, 0, 0.16), base=2.3, top=0.5, height=6.4)
    box("deck", p["wood_dk"], (0, 0, 6.5), (0.9, 0.9, 0.12), bevel=0.02)
    hub = Vector((0.45, 0, 7.3))
    box("gearbox", p["iron"], (0, 0, 6.6), (0.6, 0.5, 0.5), bevel=0.04)
    beam("axle", p["iron"], (0, 0, 6.95), hub, thick=0.12)
    for i in range(12):
        a = i * math.tau / 12
        tip = hub + Vector((0, math.cos(a) * 1.35, math.sin(a) * 1.35))
        beam("spoke", p["steel"], hub, tip, thick=0.05)
        mid = hub + Vector((0.03, math.cos(a) * 1.0, math.sin(a) * 1.0))
        panel(p["crimson"] if i % 4 == 0 else p["tin"], mid, tip + Vector((0.05, 0, 0)), 0.34, 0.04)
    beam("tail", p["steel"], (0, 0, 7.1), (-2.4, 0, 7.3), thick=0.08)
    box("vane", p["crimson"], (-2.4, 0, 7.0), (0.06, 0.2, 0.9), bevel=0.0, taper=1.0)
    box("vane_stripe", p["white"], (-2.4, 0, 7.5), (0.07, 0.22, 0.2), bevel=0.0)
    cyl("rod", p["iron"], (0.0, 0.0, 0.3), 0.06, 6.3, sides=5, bevel=0.0)
    box("trough", p["stone"], (1.45, 0.4, 0.16), (1.1, 0.55, 0.4), bevel=0.05)
    box("trough_water", p["water"], (1.45, 0.4, 0.52), (0.94, 0.4, 0.03), bevel=0.0)
    cyl("tank", p["adobe_lt"], (-1.1, 0.9, 0.16), 0.4, 0.8, sides=9, top_radius=0.34, bevel=0.0)


def sand_cistern():
    """Cisterna de cúpula (kind 1, volume baixo e redondo): adobe caiado, porta de arco, tenda ao lado."""
    p = palette()
    cyl("foot", p["sand_dk"], (0, 0, 0), 1.9, 0.14, sides=16, bevel=0.03)
    cyl("body", p["adobe_lt"], (0, 0, 0.12), 1.55, 1.3, sides=16, top_radius=1.42, bevel=0.03)
    ring("band", p["adobe"], (0, 0, 0.9), 1.42, 0.1, thick=0.02, sides=16)
    dome("dome", p["white"], (0, 0, 1.4), 1.45, squash=0.78, sides=16)
    ring("dome_ring", p["turq_dk"], (0, 0, 1.38), 1.43, 0.1, thick=0.03, sides=16)
    cyl("finial", p["gold"], (0, 0, 2.5), 0.07, 0.35, sides=6, top_radius=0.02, bevel=0.0)
    box("door", p["void"], (1.45, 0, 0.14), (0.14, 0.62, 0.8), bevel=0.0)
    prism("door_top", p["void"], (1.45, 0, 0.94), (0.62, 0.14, 0.32), ridge=0.5, rot_z=math.radians(90))
    box("door_frame", p["white"], (1.5, 0, 0.1), (0.1, 0.9, 0.12), bevel=0.0)
    for i in range(5):
        a = math.radians(-70 + i * 35)
        beam("beam_end", p["wood"], (math.cos(a) * 1.38, math.sin(a) * 1.38, 1.1), (math.cos(a) * 1.6, math.sin(a) * 1.6, 1.1), thick=0.11)
    # Tenda de nômades encostada e potes.
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        beam("tent_pole", p["wood"], (-1.0 + sx * 0.5, 1.7 + sy * 0.4 + 0.2, 0.0), (-1.0 + sx * 0.5, 1.7 + sy * 0.4 + 0.2, 0.7 if sx < 0 else 0.45), thick=0.06)
    striped_awning(p["indigo"], p["white"], -1.5, -0.5, 1.5, 2.3, 0.7, 0.45, stripes=5, along_y=False)
    jar(p["red_lt"], p["turq_dk"], (0.9, -1.9, 0.0), radius=0.22, height=0.55)
    jar(p["adobe"], p["wood_dk"], (1.25, -1.75, 0.0), radius=0.18, height=0.45)


def sand_beacon():
    """Chama de gás sobre tubo (kind 2, ponto de luz): poste de aço, escoras e chama de poço."""
    p = palette()
    cyl("base", p["sand_dk"], (0, 0, 0), 0.9, 0.14, sides=10, bevel=0.0)
    box("pad", p["concrete"], (0, 0, 0.1), (0.8, 0.8, 0.3), bevel=0.04)
    cyl("stack", p["steel"], (0, 0, 0.35), 0.17, 4.6, sides=8, top_radius=0.12, bevel=0.0)
    for z in (1.4, 2.8):
        ring("band", p["hazard"], (0, 0, z), 0.14, 0.18, thick=0.02, sides=8)
    cyl("tip", p["iron"], (0, 0, 4.9), 0.2, 0.2, sides=8, top_radius=0.14, bevel=0.0)
    for a in (0.3, 2.4, 4.5):
        beam("guy", p["iron"], (math.cos(a) * 1.45, math.sin(a) * 1.45, 0.05), (0, 0, 3.7), thick=0.035)
        box("anchor", p["concrete_dk"], (math.cos(a) * 1.45, math.sin(a) * 1.45, 0.0), (0.3, 0.3, 0.2), bevel=0.03)
    kit.flame(p["fire_core"], p["fire"], (0, 0, 5.05), size=0.7)
    box("ladder", p["rust"], (0.18, 0, 0.4), (0.04, 0.3, 3.2), bevel=0.0)
    box("tube", p["rust"], (-0.5, 0.0, 0.36), (0.9, 0.2, 0.2), bevel=0.0)


def sand_pipeline():
    """Trecho de oleoduto sobre cavaletes (kind 3, 8 de comprimento em x), meio soterrado por duna."""
    p = palette()
    cyl("pipe", p["steel"], (-4.0, 0, 0.9), 0.42, 8.0, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
    for x in (-3.9, -0.1, 3.7):
        cyl("flange", p["rust"], (x, 0, 0.9), 0.52, 0.2, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
    for x in (-2.4, 1.5):
        cyl("band", p["hazard"], (x, 0, 0.9), 0.44, 0.3, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
    for x in (-3.0, 0.0, 3.0):
        for s in (-1, 1):
            beam("trestle", p["wood"], (x, s * 0.7, 0.0), (x, s * 0.12, 0.62), thick=0.14)
        box("saddle", p["wood_dk"], (x, 0, 0.5), (0.24, 0.7, 0.14), bevel=0.0)
    box("drift_a", p["sand"], (-2.0, 0.1, 0.0), (2.8, 2.2, 0.95), bevel=0.2, taper=0.6, taper_y=0.4)
    box("drift_b", p["sand_dk"], (2.5, -0.1, 0.0), (1.8, 1.6, 0.55), bevel=0.15, taper=0.6, taper_y=0.5)
    box("valve", p["rust"], (0.9, 0, 1.2), (0.3, 0.26, 0.4), bevel=0.04)
    cyl("wheel", p["hazard"], (0.9, 0, 1.55), 0.22, 0.05, sides=10, bevel=0.0)


def sand_watchtower():
    """Torre de vigia fina de adobe (kind 4): fuste afunilado, sacada, lanterna e flâmula."""
    p = palette()
    box("foot", p["sand_dk"], (0, 0, 0), (2.4, 2.4, 0.16), bevel=0.05, taper=0.92, taper_y=0.92)
    box("base", p["adobe"], (0, 0, 0.14), (1.6, 1.6, 1.4), bevel=0.05, taper=0.78, taper_y=0.78)
    box("base_band", p["adobe_lt"], (0, 0, 1.54), (1.3, 1.3, 0.1), bevel=0.0)
    box("shaft", p["adobe_lt"], (0, 0, 1.6), (1.1, 1.1, 3.3), bevel=0.04, taper=0.7, taper_y=0.7)
    for z in (2.6, 3.7):
        box("shaft_band", p["adobe"], (0, 0, z), (0.9, 0.9, 0.09), bevel=0.0)
    for z in (2.3, 3.2):
        box("slit", p["void"], (0.4, 0, z), (0.1, 0.16, 0.4), bevel=0.0)
    box("balcony", p["white"], (0, 0, 4.85), (1.5, 1.5, 0.14), bevel=0.04)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        box("corbel", p["wood"], (sx * 0.55, sy * 0.55, 4.55), (0.2, 0.2, 0.32), bevel=0.0, taper=0.5, taper_y=0.5)
    for s in (-1, 1):
        box("rail", p["adobe"], (0, s * 0.68, 4.99), (1.4, 0.1, 0.34), bevel=0.0)
        box("rail", p["adobe"], (s * 0.68, 0, 4.99), (0.1, 1.4, 0.34), bevel=0.0)
    cyl("lantern", p["adobe_lt"], (0, 0, 4.99), 0.38, 1.0, sides=8, top_radius=0.34, bevel=0.0)
    for a in range(4):
        box("arch", p["lamp"], (math.cos(a * math.pi / 2) * 0.33, math.sin(a * math.pi / 2) * 0.33, 5.3), (0.1, 0.2, 0.34) if a % 2 == 0 else (0.2, 0.1, 0.34), bevel=0.0)
    dome("cap", p["turq"], (0, 0, 5.98), 0.46, squash=1.0, sides=8)
    cyl("spire", p["gold"], (0, 0, 6.4), 0.05, 0.6, sides=5, top_radius=0.01, bevel=0.0)
    kit.banner(p["wood_dk"], p["crimson"], (0.0, 0.0, 6.3), height=0.7, facing=0.0)


# ---------------------------------------------------------------------------------------------------------
# Bichos (um GLB estático por espécie; a frente é +x)
# ---------------------------------------------------------------------------------------------------------


def sand_jerboa():
    """Jerbo: corpo de rato, pernas traseiras longas, orelhas enormes e cauda com pincel."""
    fur, belly, dark = mat("jerboa_fur", 0xD6A15E), mat("jerboa_belly", 0xF3E3C2), mat("jerboa_dark", 0x3A2A1E)
    limb(fur, (-0.12, 0, 0.3), (0.18, 0, 0.4), 0.17, 0.15, sides=7)
    limb(belly, (-0.05, 0, 0.24), (0.15, 0, 0.3), 0.13, 0.1, sides=7)
    limb(fur, (0.18, 0, 0.4), (0.34, 0, 0.45), 0.13, 0.08, sides=7)
    box("nose", dark, (0.35, 0, 0.42), (0.06, 0.07, 0.06), bevel=0.0)
    for s in (-1, 1):
        box("ear", fur, (0.18, s * 0.08, 0.5), (0.05, 0.05, 0.3), bevel=0.0, taper=0.7, taper_y=0.7)
        box("ear_in", belly, (0.2, s * 0.08, 0.52), (0.02, 0.04, 0.2), bevel=0.0)
        limb(fur, (-0.1, s * 0.1, 0.3), (-0.05, s * 0.12, 0.0), 0.07, 0.04, sides=5)
        box("foot", dark, (-0.0, s * 0.12, 0.0), (0.18, 0.05, 0.04), bevel=0.0)
        limb(fur, (0.2, s * 0.06, 0.33), (0.26, s * 0.07, 0.15), 0.035, 0.025, sides=4)
        box("eye", dark, (0.3, s * 0.06, 0.46), (0.04, 0.03, 0.04), bevel=0.0)
    limb(fur, (-0.22, 0, 0.3), (-0.55, 0, 0.1), 0.045, 0.03, sides=5)
    limb(dark, (-0.55, 0, 0.1), (-0.7, 0, 0.12), 0.05, 0.065, sides=5)
    limb(belly, (-0.7, 0, 0.12), (-0.78, 0, 0.13), 0.06, 0.03, sides=5)


def sand_scorpion():
    """Escorpião: tronco segmentado, pinças à frente, oito patas e cauda enrolada sobre o dorso."""
    shell, dark, tip = mat("scorp_shell", 0x6B4A2A), mat("scorp_dark", 0x2E2016), mat("scorp_tip", 0xC8441E)
    for i in range(4):
        x = -0.25 + 0.14 * i
        r = 0.13 - 0.01 * i
        cyl("seg", shell if i % 2 == 0 else dark, (x, 0, 0.1), r, 0.09, sides=7, bevel=0.0)
    cyl("head", shell, (0.36, 0, 0.1), 0.14, 0.1, sides=7, top_radius=0.1, bevel=0.0)
    for s in (-1, 1):
        beam("arm", dark, (0.4, s * 0.08, 0.12), (0.64, s * 0.2, 0.12), thick=0.06)
        box("claw", shell, (0.72, s * 0.2, 0.08), (0.22, 0.17, 0.08), bevel=0.0, taper=0.6, taper_y=0.7, rot_z=s * 0.3)
        for i in range(4):
            x = 0.3 - i * 0.14
            beam("leg", dark, (x, s * 0.1, 0.1), (x + 0.05, s * 0.3, 0.02), thick=0.03)
    arc = [(-0.35, 0, 0.12), (-0.52, 0, 0.2), (-0.55, 0, 0.36), (-0.42, 0, 0.5), (-0.25, 0, 0.52), (-0.1, 0, 0.44)]
    for i, (a, b) in enumerate(itertools.pairwise(arc)):
        limb(shell if i % 2 == 0 else dark, a, b, 0.055 - 0.004 * i, 0.05 - 0.004 * i, sides=6)
    kit.spike(tip, (-0.1, 0, 0.44), height=0.14, radius=0.04, lean=(0.1, 0.0))


def sand_lizard():
    """Agama: corpo achatado, cauda longa e cabeça turquesa (o acento legível)."""
    skin, belly, blue = mat("agama_skin", 0xA88A52), mat("agama_belly", 0xD8C690), mat("agama_head", 0x2AA8B8)
    limb(skin, (-0.1, 0, 0.1), (0.15, 0, 0.12), 0.1, 0.09, sides=7)
    limb(skin, (-0.1, 0, 0.1), (-0.65, 0, 0.05), 0.09, 0.015, sides=6)
    limb(blue, (0.15, 0, 0.12), (0.32, 0, 0.15), 0.085, 0.06, sides=6)
    box("snout", blue, (0.33, 0, 0.14), (0.07, 0.08, 0.06), bevel=0.0, taper=0.7, taper_y=0.8)
    for s in (-1, 1):
        beam("fl", skin, (0.08, s * 0.08, 0.1), (0.14, s * 0.2, 0.0), thick=0.045)
        beam("bl", skin, (-0.08, s * 0.08, 0.1), (-0.14, s * 0.2, 0.0), thick=0.045)
        box("eye", mat("agama_eye", 0x1C1713), (0.27, s * 0.05, 0.19), (0.03, 0.03, 0.03), bevel=0.0)
    for i in range(5):
        kit.spike(belly, (-0.12 + i * 0.07, 0, 0.18), height=0.05, radius=0.03)


def sand_scarab():
    """Escaravelho: élitro abaulado turquesa escuro, cabeça com chifrinho e seis patas."""
    shell, dark = mat("scarab_shell", 0x1E7F86), mat("scarab_dark", 0x1A1512)
    dome("elytra", shell, (-0.02, 0, 0.04), 0.22, squash=0.75, sides=10)
    cyl("line", dark, (-0.02, 0, 0.2), 0.02, 0.01, sides=4, bevel=0.0)
    box("seam", dark, (-0.02, 0, 0.2), (0.34, 0.015, 0.02), bevel=0.0)
    box("pronotum", dark, (0.2, 0, 0.05), (0.14, 0.26, 0.12), bevel=0.0, taper=0.8, taper_y=0.9)
    box("head", dark, (0.31, 0, 0.04), (0.1, 0.16, 0.08), bevel=0.0, taper=0.6)
    kit.spike(dark, (0.34, 0, 0.1), height=0.1, radius=0.025, lean=(0.04, 0))
    for s in (-1, 1):
        for x in (0.18, 0.0, -0.16):
            beam("leg", dark, (x, s * 0.14, 0.05), (x + (0.06 if x > 0 else -0.04), s * 0.34, 0.0), thick=0.035)


def sand_vulture():
    """Abutre: corpo escuro, gola clara, cabeça pelada rosada, bico em gancho e asas em V de pontas caídas."""
    body, wing, skin, beak, ruff = mat("vulture_body", 0x4A3A2E), mat("vulture_wing", 0x372A21), mat("vulture_skin", 0xD9948A), mat("vulture_beak", 0xE8D8A0), mat("vulture_ruff", 0xDCD0B4)
    limb(body, (-0.17, 0, 0.3), (0.12, 0, 0.36), 0.16, 0.13, sides=7)
    cyl("ruff", ruff, (0.08, 0, 0.36), 0.14, 0.1, sides=7, top_radius=0.09, bevel=0.0)
    limb(skin, (0.1, 0, 0.42), (0.22, 0, 0.56), 0.05, 0.05, sides=5)
    limb(skin, (0.22, 0, 0.56), (0.31, 0, 0.58), 0.07, 0.06, sides=5)
    kit.spike(beak, (0.34, 0, 0.58), height=0.09, radius=0.035, lean=(0.07, 0.0))
    for s_ in (-1, 1):
        panel(wing, (-0.04, s_ * 0.1, 0.4), (-0.12, s_ * 0.5, 0.5), 0.32, 0.035)
        panel(body, (-0.12, s_ * 0.5, 0.5), (-0.28, s_ * 0.72, 0.34), 0.24, 0.03)
        panel(ruff, (-0.04, s_ * 0.1, 0.42), (-0.12, s_ * 0.5, 0.52), 0.05, 0.02)
        limb(body, (-0.1, s_ * 0.05, 0.3), (-0.04, s_ * 0.06, 0.1), 0.035, 0.025, sides=4)
    panel(wing, (-0.15, 0, 0.3), (-0.45, 0, 0.27), 0.22, 0.03)


def sand_sandgrouse():
    """Cortiçol (sandgrouse): corpo roliço, peito claro com faixa escura, cauda em ponta."""
    back, breast, band, head = mat("grouse_back", 0xB09468), mat("grouse_breast", 0xEFE0BC), mat("grouse_band", 0x3F2F22), mat("grouse_head", 0xD9A03C)
    limb(back, (-0.14, 0, 0.2), (0.12, 0, 0.24), 0.15, 0.13, sides=8)
    limb(breast, (-0.04, 0, 0.14), (0.16, 0, 0.2), 0.11, 0.1, sides=8)
    limb(band, (0.02, 0, 0.17), (0.06, 0, 0.18), 0.12, 0.12, sides=8)
    limb(head, (0.14, 0, 0.3), (0.23, 0, 0.4), 0.07, 0.065, sides=6)
    kit.spike(band, (0.27, 0, 0.4), height=0.07, radius=0.025, lean=(0.06, 0.0))
    box("eye", band, (0.22, 0.04, 0.42), (0.03, 0.02, 0.03), bevel=0.0)
    for s in (-1, 1):
        box("wing", back, (-0.08, s * 0.145, 0.17), (0.4, 0.06, 0.2), bevel=0.0, taper=0.8, taper_y=1.0, rot_z=s * -0.12)
        box("wing_tip", band, (-0.27, s * 0.14, 0.2), (0.14, 0.05, 0.06), bevel=0.0)
    kit.spike(back, (-0.24, 0, 0.2), height=0.3, radius=0.05, lean=(-0.3, 0.0))
    for s in (-1, 1):
        limb(band, (0.0, s * 0.05, 0.12), (0.02, s * 0.05, 0.0), 0.03, 0.025, sides=4)


# ---------------------------------------------------------------------------------------------------------
# Castelo A: caravançará fortificado
# ---------------------------------------------------------------------------------------------------------


def mud_wall(p, a, b, fixed, along_x, height=1.2, thick=0.72, merlons=5, cap_tone="white"):
    """Cortina de adobe em talude: rodapé, cinta, topo caiado, cabeças de viga e ameias redondas."""
    length = abs(b - a)
    mid = (a + b) / 2
    c = (mid, fixed, 0.0) if along_x else (fixed, mid, 0.0)
    dims = (length, thick, height) if along_x else (thick, length, height)
    tp = (1.0, 0.74) if along_x else (0.74, 1.0)
    box("wall", p["adobe"], c, dims, bevel=0.04, taper=tp[0], taper_y=tp[1])
    foot = (length, thick * 1.2, 0.16) if along_x else (thick * 1.2, length, 0.16)
    box("wall_foot", p["adobe_dk"], c, foot, bevel=0.03)
    band = (length, thick * 0.96, 0.07) if along_x else (thick * 0.96, length, 0.07)
    box("wall_band", p["adobe_lt"], (c[0], c[1], height * 0.55), band, bevel=0.0)
    top = (length, thick * 0.74, 0.09) if along_x else (thick * 0.74, length, 0.09)
    box("wall_top", p[cap_tone], (c[0], c[1], height), top, bevel=0.02)
    if along_x:
        beam_ends(p["wood"], a + 0.2, b - 0.2, height * 0.8, thick * 0.4, True, 0.16, max(2, merlons - 1))
    else:
        beam_ends(p["wood"], a + 0.2, b - 0.2, height * 0.8, thick * 0.4, False, 0.16, max(2, merlons - 1))
    rounded_merlons(p["adobe_lt"], p["white"], a + 0.12, b - 0.12, height + 0.09, merlons, fixed, along_x, radius=0.13, height=0.2)


def round_tower(p, pos, radius, height, roof="flat", cap_tone="white"):
    """Torre redonda de adobe em talude com cabeças de viga, cinta e remate."""
    x, y = pos
    cyl("tower_foot", p["adobe_dk"], (x, y, 0), radius * 1.14, 0.2, sides=12, bevel=0.03)
    cyl("tower", p["adobe"], (x, y, 0.16), radius, height, sides=12, top_radius=radius * 0.84, bevel=0.03)
    ring("tower_band", p["adobe_lt"], (x, y, 0.16 + height * 0.5), radius * 0.92, 0.07, thick=0.02, sides=12)
    for k in range(9):
        a = k * math.tau / 9 + 0.2
        beam("beam_end", p["wood"], (x + math.cos(a) * radius * 0.84, y + math.sin(a) * radius * 0.84, height * 0.86), (x + math.cos(a) * (radius * 0.84 + 0.17), y + math.sin(a) * (radius * 0.84 + 0.17), height * 0.86), thick=0.09)
    top = 0.16 + height
    cyl("tower_top", p[cap_tone], (x, y, top - 0.02), radius * 0.9, 0.1, sides=12, bevel=0.02)
    if roof == "dome":
        cyl("kiosk", p["adobe_lt"], (x, y, top + 0.06), radius * 0.6, 0.3, sides=10, bevel=0.0)
        dome("kiosk_dome", p["turq"], (x, y, top + 0.36), radius * 0.66, squash=0.9, sides=10)
        cyl("kiosk_finial", p["gold"], (x, y, top + 0.9), 0.04, 0.22, sides=5, top_radius=0.01, bevel=0.0)
        return
    for k in range(7):
        a = k * math.tau / 7
        cyl("merlon", p["adobe_lt"], (x + math.cos(a) * radius * 0.78, y + math.sin(a) * radius * 0.78, top + 0.08), 0.12, 0.2, sides=8, top_radius=0.1, bevel=0.0)
        dome("merlon_cap", p["white"], (x + math.cos(a) * radius * 0.78, y + math.sin(a) * radius * 0.78, top + 0.28), 0.11, squash=0.55, sides=8)


def gatehouse(p, gx):
    """Portaria saliente com arco ogival, porta de madeira cravejada, nicho de lamparina e panos."""
    box("gate_foot", p["adobe_dk"], (gx, 0, 0), (1.55, 2.05, 0.2), bevel=0.03)
    box("gate_block", p["adobe"], (gx, 0, 0.14), (1.4, 1.9, 1.6), bevel=0.05, taper=0.9, taper_y=0.92)
    box("gate_band", p["adobe_lt"], (gx, 0, 0.9), (1.3, 1.78, 0.08), bevel=0.0)
    box("gate_top", p["white"], (gx, 0, 1.74), (1.34, 1.84, 0.1), bevel=0.03)
    rounded_merlons(p["adobe_lt"], p["white"], -0.8, 0.8, 1.83, 4, gx + 0.52, False, radius=0.13, height=0.2)
    rounded_merlons(p["adobe_lt"], p["white"], -0.8, 0.8, 1.83, 4, gx - 0.52, False, radius=0.13, height=0.2)
    fx = gx + 0.66
    box("arch_frame", p["white"], (fx - 0.01, 0, 0.1), (0.08, 1.12, 1.02), bevel=0.0)
    prism("arch_frame_top", p["white"], (fx - 0.01, 0, 1.12), (1.12, 0.08, 0.42), ridge=0.5, rot_z=math.radians(90))
    box("door", p["wood"], (fx + 0.03, 0, 0.12), (0.08, 0.86, 0.95), bevel=0.0)
    prism("door_top", p["wood"], (fx + 0.03, 0, 1.07), (0.86, 0.08, 0.32), ridge=0.5, rot_z=math.radians(90))
    box("door_split", p["wood_dk"], (fx + 0.075, 0, 0.12), (0.03, 0.04, 1.1), bevel=0.0)
    for z in (0.35, 0.72):
        box("door_strap", p["iron"], (fx + 0.08, 0, z), (0.03, 0.84, 0.07), bevel=0.0)
    for y in (-0.3, -0.12, 0.12, 0.3):
        box("stud", p["gold"], (fx + 0.09, y, 0.52), (0.03, 0.05, 0.05), bevel=0.0)
    box("niche", p["void"], (fx + 0.0, 0, 1.45), (0.1, 0.26, 0.26), bevel=0.0)
    box("niche_lamp", p["lamp"], (fx + 0.04, 0, 1.45), (0.05, 0.1, 0.14), bevel=0.0)
    for s in (-1, 1):
        beam("pole", p["wood_dk"], (fx + 0.12, s * 0.74, 0.9), (fx + 0.12, s * 0.74, 1.62), thick=0.05)
        box("cloth", p["crimson"] if s > 0 else p["indigo"], (fx + 0.13, s * 0.74, 0.88), (0.03, 0.26, 0.7), bevel=0.0)
        box("cloth_hem", p["gold"], (fx + 0.135, s * 0.74, 0.9), (0.03, 0.26, 0.07), bevel=0.0)
        for k in range(3):
            beam("beam_end", p["wood"], (gx + 0.2 * (k - 1), s * 0.93, 1.45), (gx + 0.2 * (k - 1), s * 1.12, 1.45), thick=0.09)
    box("ramp", p["sand_lt"], (gx + 0.95, 0, 0.0), (0.55, 1.1, 0.1), bevel=0.04, taper=0.8, taper_y=0.9)


def domed_hall(p, kx):
    """Menagem: salão com cúpula caiada em degraus, faixa de azulejo turquesa e quatro cúpulas pequenas."""
    box("keep_base", p["adobe"], (kx, 0, 0.12), (2.3, 2.1, 1.05), bevel=0.05, taper=0.9, taper_y=0.9)
    box("keep_band", p["adobe_lt"], (kx, 0, 1.0), (2.2, 2.0, 0.09), bevel=0.0)
    box("keep_roof", p["white"], (kx, 0, 1.1), (2.0, 1.8, 0.08), bevel=0.02)
    box("keep_mid", p["adobe_lt"], (kx - 0.1, 0, 1.17), (1.5, 1.4, 0.55), bevel=0.04, taper=0.9, taper_y=0.9)
    box("keep_mid_top", p["white"], (kx - 0.1, 0, 1.7), (1.4, 1.3, 0.07), bevel=0.02)
    cyl("drum", p["white"], (kx - 0.1, 0, 1.75), 0.58, 0.3, sides=12, bevel=0.02)
    ring("tile_band", p["turq"], (kx - 0.1, 0, 1.9), 0.58, 0.1, thick=0.03, sides=12)
    dome("keep_dome", p["white"], (kx - 0.1, 0, 2.04), 0.62, squash=0.95, sides=14)
    ring("dome_rim", p["turq_dk"], (kx - 0.1, 0, 2.02), 0.6, 0.05, thick=0.02, sides=14)
    cyl("finial", p["gold"], (kx - 0.1, 0, 2.6), 0.05, 0.4, sides=5, top_radius=0.01, bevel=0.0)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        cx, cy = kx + sx * 0.88, sy * 0.78
        cyl("domelet", p["white"], (cx, cy, 1.15), 0.22, 0.14, sides=8, bevel=0.0)
        dome("domelet_top", p["turq"] if sx * sy > 0 else p["crimson"], (cx, cy, 1.28), 0.24, squash=0.9, sides=8)
    # Janelas e porta do salão voltadas para a lane (+x).
    box("hall_door", p["void"], (kx + 1.04, 0, 0.14), (0.08, 0.5, 0.6), bevel=0.0)
    prism("hall_door_top", p["void"], (kx + 1.04, 0, 0.74), (0.5, 0.08, 0.26), ridge=0.5, rot_z=math.radians(90))
    for y in (-0.7, 0.7):
        window(p, (kx + 1.05, y, 0.55))
    for x in (kx - 0.5, kx + 0.4):
        window(p, (x, 1.0, 0.5), "y+")
        window(p, (x, -1.0, 0.5), "y-")


def window(p, pos, facing="x+"):
    kit.window(p["wood_dk"], p["void"], pos, facing, w=0.14, h=0.3)


def lookout(p, pos):
    """Coroa: torre de vigia fina com sacada de madeira e bandeira de pano carmim."""
    x, y = pos
    box("lookout_shaft", p["adobe_lt"], (x, y, 2.2), (0.62, 0.62, 1.7), bevel=0.04, taper=0.74, taper_y=0.74)
    box("lookout_band", p["adobe"], (x, y, 3.0), (0.5, 0.5, 0.08), bevel=0.0)
    box("lookout_balcony", p["wood"], (x, y, 3.55), (1.0, 1.0, 0.1), bevel=0.02)
    for s in (-1, 1):
        box("lookout_rail", p["wood_dk"], (x, y + s * 0.46, 3.7), (0.96, 0.05, 0.18), bevel=0.0)
        box("lookout_rail", p["wood_dk"], (x + s * 0.46, y, 3.7), (0.05, 0.96, 0.18), bevel=0.0)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        beam("lookout_post", p["wood"], (x + sx * 0.38, y + sy * 0.38, 3.6), (x + sx * 0.3, y + sy * 0.3, 4.1), thick=0.07)
    cyl("lookout_roof", p["crimson"], (x, y, 4.05), 0.62, 0.45, sides=4, top_radius=0.02, bevel=0.0, rot=("Z", math.radians(45)))
    kit.banner(p["wood_dk"], p["indigo"], (x, y, 4.45), height=0.85, facing=math.radians(-20))
    box("lookout_lamp", p["lamp"], (x + 0.3, y, 3.2), (0.1, 0.1, 0.1), bevel=0.0)


def court_life(p):
    """Pátio: poço de balde, toldos de pano, fardos, potes e uma rampa de acesso."""
    cyl("well", p["white"], (0.85, 0.9, 0.18), 0.3, 0.3, sides=10, bevel=0.02)
    cyl("well_water", p["water"], (0.85, 0.9, 0.46), 0.22, 0.02, sides=10, bevel=0.0)
    for s in (-1, 1):
        beam("well_post", p["wood"], (0.85, 0.9 + s * 0.32, 0.18), (0.85, 0.9 + s * 0.32, 0.8), thick=0.06)
    beam("well_cross", p["wood_dk"], (0.85, 0.58, 0.8), (0.85, 1.22, 0.8), thick=0.06)
    # Toldos: dois, carmim e anil, no lado da muralha sul.
    for k, (xs, tone) in enumerate(((0.15, "crimson"), (1.35, "indigo"))):
        for sx in (xs - 0.35, xs + 0.35):
            beam("awning_post", p["wood"], (sx, -1.55, 0.18), (sx, -1.55, 0.78), thick=0.05)
        for i in range(4):
            y0, y1 = -1.55 + i * 0.2, -1.55 + (i + 1) * 0.2
            cloth(p[tone] if i % 2 == 0 else p["white"], (xs - 0.42, y0, 0.84 - i * 0.04), (xs + 0.42, y0, 0.84 - i * 0.04), (xs + 0.42, y1, 0.8 - i * 0.04), (xs - 0.42, y1, 0.8 - i * 0.04))
    for i, (x, y) in enumerate(((-1.5, -1.3), (-1.25, -1.45), (-1.55, -0.95))):
        jar(p["adobe_lt"] if i % 2 == 0 else p["red_lt"], p["turq_dk"] if i == 1 else p["wood_dk"], (x, y, 0.16), radius=0.2, height=0.48)
    box("bale", p["sack"], (-1.3, 1.1, 0.16), (0.55, 0.42, 0.34), bevel=0.06, rot_z=0.3)
    box("bale", p["sack"], (-1.1, 1.45, 0.16), (0.5, 0.4, 0.3), bevel=0.06, rot_z=-0.2)
    box("bale_strap", p["crimson"], (-1.3, 1.1, 0.34), (0.1, 0.44, 0.1), bevel=0.0, rot_z=0.3)
    box("crate", p["wood"], (-0.4, 1.5, 0.16), (0.4, 0.4, 0.36), bevel=0.02, rot_z=0.3)


def caravanserai():
    """Dunas, Caravançará (oeste): adobe espesso com torres redondas, portaria ogival, menagem de cúpula e vigia."""
    p = palette()
    box("plinth", p["sand_dk"], (0, 0, 0), (6.2, 6.2, 0.14), bevel=0.06, taper=0.95, taper_y=0.95)
    box("yard", p["sand_lt"], (0, 0, 0.12), (5.1, 5.1, 0.08), bevel=0.03)
    w = 2.0
    mud_wall(p, -w, w, w, True, merlons=6)
    mud_wall(p, -w, w, -w, True, merlons=6)
    mud_wall(p, -w, w, -w, False, merlons=6)
    mud_wall(p, -w, -0.85, w, False, merlons=2)
    mud_wall(p, 0.85, w, w, False, merlons=2)
    # Torres de canto para fora da linha da muralha, de alturas diferentes.
    round_tower(p, (w, w), 0.88, 1.85, roof="dome")
    round_tower(p, (w, -w), 0.8, 1.55)
    round_tower(p, (-w, w), 0.88, 2.1)
    round_tower(p, (-w, -w), 0.76, 1.4, cap_tone="adobe_lt")
    # Contrafortes
    for t in (-1.0, 0.5):
        kit.buttress(p["adobe_dk"], (t, w + 0.3, 0.0), (0, 1), height=0.9)
        kit.buttress(p["adobe_dk"], (t + 0.2, -w - 0.3, 0.0), (0, -1), height=0.8)
    gatehouse(p, w + 0.2)
    domed_hall(p, -0.55)
    lookout(p, (-w, w))
    court_life(p)
    # Convés caiado nas cortinas (o plano que a câmera lê) e panos pendurados.
    for sgn in (-1, 1):
        box("deck", p["white"], (0, sgn * w, 1.22), (2 * w - 1.6, 0.4, 0.04), bevel=0.0)
        for x in (-0.9, 0.9):
            box("hanging", p["crimson"] if (x > 0) == (sgn > 0) else p["indigo"], (x, sgn * (w + 0.36), 0.62), (0.34, 0.03, 0.5), bevel=0.0)
    box("drift", p["sand"], (-w - 0.7, -0.5, 0.0), (1.0, 2.0, 0.4), bevel=0.15, taper=0.5, taper_y=0.5)
    box("drift", p["sand"], (0.3, -w - 0.8, 0.0), (2.4, 0.8, 0.3), bevel=0.15, taper=0.5, taper_y=0.5)


# ---------------------------------------------------------------------------------------------------------
# Castelo B: estação de bombeio
# ---------------------------------------------------------------------------------------------------------


def rivets(material, x0, x1, y, z, count, along_x=True, size=0.045):
    for i in range(count):
        t = x0 + (x1 - x0) * (i + 0.5) / count
        box("rivet", material, (t, y, z) if along_x else (y, t, z), (size, size, size), bevel=0.0)


def plate_wall(p, a, b, fixed, along_x, height=1.0, thick=0.5):
    """Cortina de concreto com chapas de aço rebitadas, sacos de areia no topo e duna encostada por fora."""
    length = abs(b - a)
    mid = (a + b) / 2
    c = (mid, fixed, 0.0) if along_x else (fixed, mid, 0.0)
    dims = (length, thick, height) if along_x else (thick, length, height)
    tp = (1.0, 0.8) if along_x else (0.8, 1.0)
    box("wall", p["concrete"], c, dims, bevel=0.03, taper=tp[0], taper_y=tp[1])
    box("wall_cap", p["steel"], (c[0], c[1], height), (dims[0] * (1.0 if along_x else 0.74), dims[1] * (0.74 if along_x else 1.0), 0.08), bevel=0.01)
    n = max(2, int(length / 0.8))
    step = length / n
    for i in range(n):
        t = a + (i + 0.5) * step
        pos = (t, fixed) if along_x else (fixed, t)
        face = 1 if fixed >= 0 else -1
        ox, oy = (0.0, face * (thick * 0.5 - 0.02)) if along_x else (face * (thick * 0.5 - 0.02), 0.0)
        pd = (step * 0.88, 0.05, height * 0.7) if along_x else (0.05, step * 0.88, height * 0.7)
        box("plate", p["rust"] if i % 3 == 1 else p["steel"], (pos[0] + ox, pos[1] + oy, 0.12), pd, bevel=0.0)
        rivets(p["iron"], t - step * 0.38, t + step * 0.38, (pos[1] + oy * 1.12) if along_x else (pos[0] + ox * 1.12), 0.2, 4, along_x=along_x)
        rivets(p["iron"], t - step * 0.38, t + step * 0.38, (pos[1] + oy * 1.12) if along_x else (pos[0] + ox * 1.12), 0.72, 4, along_x=along_x)
    # Sacos de areia empilhados no topo, duas fiadas.
    bag_n = max(3, int(length / 0.5))
    bs = length / bag_n
    for i in range(bag_n):
        t = a + (i + 0.5) * bs
        pos = (t, fixed, height + 0.08) if along_x else (fixed, t, height + 0.08)
        sandbag(p["sack"] if i % 2 else p["sand_dk"], pos, size=(bs * 0.98, 0.34, 0.17) if along_x else (0.34, bs * 0.98, 0.17))


def pump_house(p, pos, radius, height, tank=False):
    """Casa de bomba cilíndrica e atarracada: cintas rebitadas, teto de chapa, ventilação e faixa de perigo."""
    x, y = pos
    cyl("ph_foot", p["concrete_dk"], (x, y, 0), radius * 1.1, 0.18, sides=14, bevel=0.02)
    cyl("ph", p["steel"], (x, y, 0.14), radius, height, sides=14, bevel=0.02)
    for k, z in enumerate((0.3, height * 0.55)):
        ring("ph_band", p["hazard"] if k == 1 else p["rust"], (x, y, z + 0.14), radius, 0.1 if k else 0.07, thick=0.025, sides=14)
    for k in range(14):
        a = k * math.tau / 14
        box("ph_rivet", p["iron"], (x + math.cos(a) * (radius + 0.02), y + math.sin(a) * (radius + 0.02), height * 0.8), (0.05, 0.05, 0.05), bevel=0.0, rot_z=a)
    top = 0.14 + height
    cyl("ph_lid", p["rust"], (x, y, top), radius * 1.03, 0.1, sides=14, bevel=0.01)
    cyl("ph_lid_dome", p["paint"], (x, y, top + 0.1), radius * 0.9, 0.14, sides=14, top_radius=radius * 0.5, bevel=0.0)
    cyl("ph_vent", p["iron"], (x + radius * 0.3, y, top + 0.2), 0.14, 0.3, sides=8, bevel=0.0)
    cyl("ph_vent_cap", p["rust"], (x + radius * 0.3, y, top + 0.5), 0.2, 0.06, sides=8, bevel=0.0)
    if tank:
        cyl("ph_water", p["water"], (x - radius * 0.2, y, top + 0.1), radius * 0.4, 0.04, sides=10, bevel=0.0)


def manifold(p):
    """Coletor de tubos que atravessa as muralhas: dois cabeçotes, válvulas de roda amarela e flanges."""
    for y in (-0.75, 0.75):
        cyl("pipe", p["steel"], (-3.2, y, 0.55), 0.17, 4.3, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
        for x in (-3.1, -2.3, -1.0):
            cyl("flange", p["rust"], (x, y, 0.55), 0.24, 0.12, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
    cyl("header", p["steel"], (-2.0, -1.0, 0.55), 0.2, 2.0, sides=10, bevel=0.0, rot=("X", math.radians(-90)))
    cyl("header_cap", p["rust"], (-2.0, 1.0, 0.55), 0.26, 0.1, sides=10, bevel=0.0, rot=("X", math.radians(-90)))
    for x, y in ((-1.5, -0.75), (-1.5, 0.75), (-2.0, 0.0)):
        box("valve", p["rust"], (x, y, 0.55), (0.34, 0.3, 0.3), bevel=0.04)
        cyl("valve_stem", p["iron"], (x, y, 0.8), 0.04, 0.2, sides=5, bevel=0.0)
        cyl("valve_wheel", p["hazard"], (x, y, 1.0), 0.18, 0.04, sides=10, bevel=0.0)
    # Pontas expostas do lado de fora, enterradas na areia.
    for y in (-0.75, 0.75):
        box("sand_cover", p["sand"], (-2.95, y, 0.0), (0.9, 0.8, 0.5), bevel=0.15, taper=0.5, taper_y=0.5)


def machine_hall(p, kx):
    """Menagem: galpão de máquinas sob telhado de chapa ondulada (mais claro que o resto), aberto para a lane."""
    box("hall_plinth", p["concrete_dk"], (kx, 0, 0.12), (2.6, 2.2, 0.3), bevel=0.04, taper=0.94, taper_y=0.94)
    box("hall_back", p["steel"], (kx - 1.0, 0, 0.4), (0.12, 1.9, 1.0), bevel=0.0)
    for s in (-1, 1):
        box("hall_side", p["steel"], (kx, s * 0.95, 0.4), (2.0, 0.12, 1.0), bevel=0.0)
        rivets(p["iron"], kx - 0.85, kx + 0.85, s * 1.02, 0.9, 6)
    # Máquina no vão aberto: volante e bloco do motor.
    box("engine", p["rust"], (kx + 0.1, 0, 0.42), (1.0, 0.8, 0.5), bevel=0.05)
    cyl("flywheel", p["iron"], (kx + 0.1, -0.1, 0.85), 0.34, 0.12, sides=12, bevel=0.0, rot=("X", math.radians(90)))
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        beam("post", p["iron"], (kx + sx * 1.1, sy * 0.92, 0.4), (kx + sx * 1.1, sy * 0.92, 1.45), thick=0.1)
    # Telhado de uma água com ondulação: chapas e nervuras claras descendo pela inclinação.
    lo, hi = 1.4, 1.9
    x0, x1 = kx - 1.2, kx + 1.2
    for i in range(7):
        y0 = -1.0 + i * (2.0 / 7)
        panel(p["tin"] if i % 2 == 0 else p["tin_dk"], (x1, y0 + 0.143, lo), (x0, y0 + 0.143, hi), 0.29, 0.05)
    for i in range(14):
        y = -1.0 + i * (2.0 / 13)
        beam("rib", p["steel_lt"], (x1, y, lo + 0.03), (x0, y, hi + 0.03), thick=0.035)
    box("roof_rust", p["rust"], (kx + 0.3, 0.45, 1.64), (0.8, 0.45, 0.03), bevel=0.0)
    for k in range(4):
        box("ridge_stripe", p["hazard"] if k % 2 == 0 else p["iron"], (x0 + 0.1 + k * 0.1, 0, hi + 0.04), (0.1, 2.0, 0.04), bevel=0.0)
    box("roof_edge", p["tin"], (x1, 0, lo - 0.02), (0.08, 2.0, 0.1), bevel=0.0)


def pumpjack(p, pos, height=1.0):
    """Coroa: cavalo de bombeio em balanço sobre plataforma de concreto, com contrapeso e biela."""
    x, y, z = pos
    box("jack_tower", p["concrete"], (x, y, 0.28), (1.3, 0.8, z - 0.28), bevel=0.05, taper=0.85, taper_y=0.9)
    box("jack_pad", p["steel"], (x, y, z), (1.4, 0.8, 0.12), bevel=0.02)
    z += 0.1
    for s in (-1, 1):
        beam("samson", p["rust"], (x - 0.08, y + s * 0.3, z + 0.2), (x, y + s * 0.07, z + 1.55), thick=0.1)
        beam("samson", p["rust"], (x + 0.38, y + s * 0.3, z + 0.2), (x, y + s * 0.07, z + 1.55), thick=0.1)
    beam("walking_beam", p["hazard"], (x - 0.75, y, z + 1.45), (x + 1.0, y, z + 1.95), thick=0.16)
    box("head", p["iron"], (x + 0.96, y, z + 1.55), (0.34, 0.2, 0.62), bevel=0.04, taper=0.7, taper_y=1.0)
    beam("bridle", p["iron"], (x + 1.14, y, z + 1.7), (x + 1.14, y, z + 0.2), thick=0.04)
    box("counter", p["rust"], (x - 0.78, y, z + 1.0), (0.42, 0.3, 0.55), bevel=0.05)
    cyl("crank", p["iron"], (x - 0.45, y - 0.08, z + 0.5), 0.3, 0.1, sides=10, bevel=0.0, rot=("X", math.radians(90)))
    beam("pitman", p["iron"], (x - 0.45, y - 0.12, z + 0.72), (x - 0.78, y - 0.12, z + 1.5), thick=0.05)
    box("motor", p["steel"], (x - 0.5, y + 0.28, z + 0.22), (0.5, 0.26, 0.3), bevel=0.04)


def gate_plate(p, gx):
    """Portão de chapa deslizante entre dois bunkers de concreto com sacos de areia e lâmpada de sinal."""
    for s in (-1, 1):
        box("bunker", p["concrete"], (gx, s * 1.15, 0.12), (1.2, 0.8, 1.0), bevel=0.05, taper=0.88, taper_y=0.88)
        box("bunker_cap", p["steel"], (gx, s * 1.15, 1.12), (1.1, 0.72, 0.07), bevel=0.01)
        for k in range(3):
            sandbag(p["sack"] if k % 2 else p["sand_dk"], (gx + 0.55, s * (0.95 + 0.25 * k), 0.12), size=(0.5, 0.3, 0.17))
        beam("lamp_post", p["iron"], (gx - 0.3, s * 1.4, 1.1), (gx - 0.3, s * 1.4, 1.8), thick=0.07)
        box("lamp", p["lamp"], (gx - 0.3, s * 1.4, 1.8), (0.14, 0.14, 0.12), bevel=0.0)
    box("gate_leaf", p["steel"], (gx + 0.02, 0.0, 0.14), (0.14, 1.3, 0.9), bevel=0.0)
    for k in range(5):
        box("chevron", p["hazard"] if k % 2 == 0 else p["iron"], (gx + 0.1, -0.5 + k * 0.25, 0.14), (0.05, 0.22, 0.9), bevel=0.0)
    box("rail", p["iron"], (gx + 0.0, 0.0, 1.08), (0.12, 2.1, 0.1), bevel=0.0)
    box("steel_road", p["concrete_dk"], (gx + 0.95, 0, 0.0), (0.8, 1.1, 0.1), bevel=0.03, taper=0.85, taper_y=0.9)


def pumping_station():
    """Dunas, Estação de bombeio (leste): aço, concreto e sacos de areia cavados na duna; coletor, casas de bomba e cavalo de bombeio."""
    p = palette()
    # Duna que cava o conjunto: o terreno sobe por fora, a estação fica rebaixada.
    box("dune", p["sand"], (0, 0, 0), (6.4, 6.4, 0.3), bevel=0.15, taper=0.92, taper_y=0.92)
    box("pit", p["concrete_dk"], (0, 0, 0.28), (4.5, 4.5, 0.06), bevel=0.0)
    w = 2.05
    plate_wall(p, -w, w, w, True)
    plate_wall(p, -w, w, -w, True)
    plate_wall(p, -w, w, -w, False)
    plate_wall(p, -w, -0.9, w, False)
    plate_wall(p, 0.9, w, w, False)
    # Casas de bomba como bastiões para fora da muralha, de portes diferentes.
    pump_house(p, (w + 0.05, w + 0.05), 1.0, 1.0)
    pump_house(p, (w + 0.05, -w - 0.05), 0.82, 0.8, tank=True)
    pump_house(p, (-w - 0.05, w + 0.05), 0.9, 1.15)
    pump_house(p, (-0.1, -w - 0.25), 0.62, 0.8)
    # Rampa de areia no portão e a duna que invade a quina sudoeste.
    gate_plate(p, w + 0.3)
    box("drift", p["sand"], (-w - 0.2, -w - 0.2, 0.0), (1.9, 1.7, 0.8), bevel=0.2, taper=0.45, taper_y=0.45)
    box("drift", p["sand_dk"], (0.4, w + 0.65, 0.0), (2.2, 1.0, 0.55), bevel=0.15, taper=0.5, taper_y=0.5)
    manifold(p)
    machine_hall(p, 0.15)
    pumpjack(p, (-0.95, 1.3, 0.95))
    # Bacia de decantação turquesa no pátio e tambores.
    cyl("basin", p["concrete"], (1.55, -0.95, 0.28), 0.62, 0.12, sides=12, bevel=0.0)
    cyl("basin_water", p["water"], (1.55, -0.95, 0.38), 0.5, 0.03, sides=12, bevel=0.0)
    for i, (dx, dy) in enumerate(((0.0, 0.0), (0.26, 0.1), (0.1, 0.3))):
        cyl("drum", p["hazard"] if i == 1 else p["rust"], (1.35 + dx, 0.75 + dy, 0.28), 0.12, 0.32, sides=8, bevel=0.0)
    # Faixas de perigo no pé da muralha e uma torre de caixa-d'água baixa.
    for k in range(6):
        box("hazard_stripe", p["hazard"] if k % 2 == 0 else p["iron"], (-1.3 + k * 0.3, -w + 0.3, 0.28), (0.16, 0.06, 0.04), bevel=0.0, rot_z=0.7)


MODELS = {
    "sand_wall": sand_wall,
    "sand_pillar": sand_pillar,
    "sand_arch": sand_arch,
    "sand_palm_a": sand_palm_a,
    "sand_palm_b": sand_palm_b,
    "sand_palm_c": sand_palm_c,
    "sand_stump": sand_stump,
    "sand_fallen": sand_fallen,
    "sand_thorn": sand_thorn,
    "sand_tent": sand_tent,
    "sand_outcrop": sand_outcrop,
    "sand_ruin": sand_ruin,
    "sand_cargo": sand_cargo,
    "sand_well": sand_well,
    "sand_windpump": sand_windpump,
    "sand_cistern": sand_cistern,
    "sand_beacon": sand_beacon,
    "sand_pipeline": sand_pipeline,
    "sand_watchtower": sand_watchtower,
    "sand_jerboa": sand_jerboa,
    "sand_scorpion": sand_scorpion,
    "sand_lizard": sand_lizard,
    "sand_scarab": sand_scarab,
    "sand_vulture": sand_vulture,
    "sand_sandgrouse": sand_sandgrouse,
    "sand_caravanserai": caravanserai,
    "sand_pumpstation": pumping_station,
}
CASTLE_NAMES = ("sand_caravanserai", "sand_pumpstation")
CRITTER_NAMES = ("sand_jerboa", "sand_scorpion", "sand_lizard", "sand_scarab", "sand_vulture", "sand_sandgrouse")


def build(name, out_dir, render_dir):
    """Como kit.build, mas com o chão da prévia em areia e, nos bichos, câmera mais perto."""
    kit.reset()
    MODELS[name]()
    kit.bake()
    tris, lo, hi = kit.stats()
    print(f"MODEL {name}: tris={tris} min=({lo.x:.2f},{lo.y:.2f},{lo.z:.2f}) max=({hi.x:.2f},{hi.y:.2f},{hi.z:.2f})")
    if render_dir:
        os.makedirs(render_dir, exist_ok=True)
        span = max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, 0.5)
        views = (("front", -35.0), ("back", 150.0), ("game", -90.0)) if name in CASTLE_NAMES else (("front", -35.0),)
        for tag, yaw in views:
            kit.render(os.path.join(render_dir, f"{name}_{tag}.png"), yaw, ground=SAND_GROUND, span=span, top=hi.z)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.export_scene.gltf(filepath=os.path.join(out_dir, f"{name}.glb"), export_format="GLB", use_selection=True, export_yup=True, export_apply=True)


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["all"]
    names = list(MODELS) if args[0] == "all" else [args[0]]
    assets = args[args.index("--out") + 1] if "--out" in args else ""
    render_dir = args[args.index("--render") + 1] if "--render" in args else ""
    for name in names:
        # --out é a pasta assets: castelos em castles/, o resto em scenery/desert/.
        sub = "castles" if name in CASTLE_NAMES else os.path.join("scenery", "desert")
        build(name, os.path.join(assets, sub) if assets else "", render_dir)


if __name__ == "__main__":
    main()
