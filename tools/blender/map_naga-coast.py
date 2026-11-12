"""Costa Naga (Black Tide / Mare Negra, docs/maps.md): castelos e cenario modelados por script.

Uso:
    blender -b --factory-startup --python tools/blender/map_naga-coast.py -- <nome|all> \
        [--out DIR] [--castles DIR] [--render DIR]

`--out` grava o GLB (castelos em assets/castles, o resto em assets/scenery/naga-coast). Reusa o kit de
map_castles.py; os ajudantes novos (membro afilado, loft de casco, roda de valvula, corrente) ficam aqui.
Referencial do jogo: +x aponta para a lane, z e a altura.
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
from map_castles import beam, box, cyl, dome, mat, prism
from map_scenery import normalize

PI = math.pi


def pal():
    return {
        "stone": mat("naga_stone", 0x7E9A92),
        "stone_dk": mat("naga_stone_dk", 0x4F6A66),
        "stone_lt": mat("naga_stone_lt", 0xB9CCC2),
        "sea": mat("naga_sea", 0x5F8C80),
        "sea_dk": mat("naga_sea_dk", 0x3F6862),
        "sea_lt": mat("naga_sea_lt", 0xB4D0C2),
        "teal": mat("naga_teal", 0x24474A),
        "verd": mat("naga_verd", 0x5CA592),
        "bronze": mat("naga_bronze", 0xB27B38),
        "bronze_dk": mat("naga_bronze_dk", 0x7A5224),
        "amber": mat("naga_amber", 0xFFB444, emit=3.0),
        "coral": mat("naga_coral", 0xE0674F),
        "coral_pale": mat("naga_coral_pale", 0xF1C0A8),
        "granite": mat("naga_granite", 0x939A9A),
        "granite_dk": mat("naga_granite_dk", 0x646B6E),
        "granite_lt": mat("naga_granite_lt", 0xC4CAC8),
        "tar": mat("naga_tar", 0x3A2F2A),
        "tar_lt": mat("naga_tar_lt", 0x5E4A3A),
        "brass": mat("naga_brass", 0xD2AC4C),
        "red": mat("naga_red", 0xB93A2E),
        "white": mat("naga_white", 0xEBE7DB),
        "iron": mat("naga_iron", 0x30363A),
        "iron_lt": mat("naga_iron_lt", 0x5C676D),
        "wood": mat("naga_wood", 0xB3A78E),
        "wood_dk": mat("naga_wood_dk", 0x6C5C49),
        "mangrove": mat("naga_mangrove", 0x4B3B30),
        "mangrove_lt": mat("naga_mangrove_lt", 0x6E5846),
        "bleach": mat("naga_bleach", 0xDED5C2),
        "dead_coral": mat("naga_dead_coral", 0xE8D2C2),
        "kelp": mat("naga_kelp", 0x56693A),
        "kelp_lt": mat("naga_kelp_lt", 0x7E8D46),
        "olive": mat("naga_olive", 0x6F7352),
        "sand": mat("naga_sand", 0xCBBE9C),
        "sand_dk": mat("naga_sand_dk", 0xA89A7C),
        "barn": mat("naga_barnacle", 0xC4BFAF),
        "rope": mat("naga_rope", 0xB89F66),
        "hull": mat("naga_hull", 0x3D7075),
        "slick_a": mat("naga_slick_a", 0x1B2234),
        "slick_b": mat("naga_slick_b", 0x1F3A44),
        "slick_c": mat("naga_slick_c", 0x2A2C46),
        "foam": mat("naga_foam", 0x8FAAA6),
        "glass": mat("naga_glass", 0xFFD27A, emit=2.5),
        "void": mat("naga_void", 0x0F1F22),
    }


# ---------------------------------------------------------------------------------------------------------
# Ajudantes
# ---------------------------------------------------------------------------------------------------------


def limb(name, material, a, b, r0, r1, sides=6):
    """Membro afilado de a ate b (raiz de mangue, galho, mastro)."""
    a, b = Vector(a), Vector(b)
    d = b - a
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=r0, radius2=max(r1, 1e-4), depth=d.length)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, d.length / 2))
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=d.to_track_quat("Z", "Y").to_matrix())
    bmesh.ops.translate(bm, verts=bm.verts, vec=a)
    return kit._finish(bm, name, material)


def path(name, material, pts, r0, r1, sides=6):
    """Membro por uma lista de pontos, afinando de r0 para r1."""
    n = len(pts) - 1
    for i, (a, b) in enumerate(itertools.pairwise(pts)):
        limb(name, material, a, b, r0 + (r1 - r0) * i / n, r0 + (r1 - r0) * (i + 1) / n, sides)


def loft(name, material, stations):
    """Solido fechado por aneis: stations = [(x, [(y, z), ...])], mesmo numero de pontos em cada anel."""
    bm = bmesh.new()
    rings = [[bm.verts.new((x, y, z)) for y, z in pts] for x, pts in stations]
    n = len(rings[0])
    for r0, r1 in itertools.pairwise(rings):
        for i in range(n):
            bm.faces.new((r0[i], r0[(i + 1) % n], r1[(i + 1) % n], r1[i]))
    bm.faces.new(rings[0])
    bm.faces.new(rings[-1][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit._finish(bm, name, material)


def hull(material, length, width, depth, x0=0.0, z0=0.0, rise=0.25, count=9):
    """Casco de barco fechado (proa em +x): quilha, bojo e borda que sobe nas pontas."""
    stations = []
    for i in range(count):
        t = i / (count - 1) * 2 - 1
        w = max(width / 2 * (1 - abs(t) ** 2.2), 0.05)
        sheer = z0 + depth + rise * abs(t) ** 2
        keel = z0 + max(abs(t) - 0.55, 0.0) * depth * 1.6
        mid = keel + 0.4 * (sheer - keel)
        stations.append((x0 + t * length / 2, [(-w, sheer), (-w * 0.6, mid), (0, keel), (w * 0.6, mid), (w, sheer)]))
    return loft("hull", material, stations)


def frame(name, material, center, axis, radius, thick=0.05, sides=12, phase=0.0):
    """Aro de vigas (roda, boia, aro de farol) no plano perpendicular a `axis` (x, y ou z)."""
    cx, cy, cz = center
    pts = []
    for i in range(sides):
        a = phase + i * math.tau / sides
        u, v = math.cos(a) * radius, math.sin(a) * radius
        pts.append({"x": (cx, cy + u, cz + v), "y": (cx + u, cy, cz + v), "z": (cx + u, cy + v, cz)}[axis])
    for i in range(sides):
        beam(name, material, pts[i], pts[(i + 1) % sides], thick=thick)
    return pts


def wheel(material, center, axis, radius, spokes=6, thick=0.05):
    """Roda de valvula: aro, raios e cubo."""
    pts = frame("wheel_rim", material, center, axis, radius, thick, sides=spokes * 2)
    for i in range(spokes):
        beam("wheel_spoke", material, center, pts[i * 2], thick=thick * 0.8)
        # punho saliente em cada raio
        away = (Vector(pts[i * 2]) - Vector(center)).normalized() * thick * 1.6
        beam("wheel_grip", material, pts[i * 2], Vector(pts[i * 2]) + away, thick=thick * 1.2)
    box("wheel_hub", material, (center[0], center[1], center[2] - thick * 1.2), (thick * 3, thick * 3, thick * 2.4), bevel=0.01)


def chain(material, a, b, sag=0.15, links=8, thick=0.035):
    """Corrente caindo em catenaria de a ate b."""
    a, b = Vector(a), Vector(b)
    prev = a
    for i in range(1, links + 1):
        t = i / links
        pt = a.lerp(b, t) - Vector((0, 0, 4 * sag * t * (1 - t)))
        beam("chain", material, prev, pt, thick=thick)
        prev = pt


def stepped(mats, center, base, heights, shrink, bevel=0.03, taper=0.9, rot_z=0.0):
    """Piramide em degraus: cada nivel menor que o de baixo; devolve o z do topo."""
    cx, cy, z = center
    size = base
    for i, h in enumerate(heights):
        box("tier", mats[min(i, len(mats) - 1)], (cx, cy, z), (size, size, h), bevel=bevel, taper=taper, taper_y=taper, rot_z=rot_z)
        z += h
        size *= shrink
    return z


def bollard(p, pos, height=0.3, radius=0.1):
    cyl("bollard", p["iron"], pos, radius, height, sides=8, top_radius=radius * 0.85)
    cyl("bollard_cap", p["iron_lt"], (pos[0], pos[1], pos[2] + height), radius * 1.35, 0.06, sides=8, bevel=0.0)


def crate(p, pos, size=(0.5, 0.5, 0.4), rot_z=0.0, tone="wood", band="wood_dk"):
    box("crate", p[tone], pos, size, bevel=0.02, rot_z=rot_z)
    box("crate_band", p[band], (pos[0], pos[1], pos[2] + size[2] * 0.4), (size[0] + 0.02, size[1] + 0.02, size[2] * 0.2), bevel=0.0, rot_z=rot_z)


def barrel(p, pos, radius=0.2, height=0.4, tone="wood_dk"):
    cyl("barrel", p[tone], pos, radius, height, sides=9, bevel=0.0)
    for z in (0.18, 0.72):
        cyl("barrel_hoop", p["iron"], (pos[0], pos[1], pos[2] + height * z), radius * 1.05, height * 0.1, sides=9, bevel=0.0)


def lattice(p, material, a, b, width, panels, thick=0.05):
    """Mastro treliçado entre a e b com travessas em X (guindaste, torre de sinais)."""
    a, b = Vector(a), Vector(b)
    legs = []
    for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        off = Vector((sx * width / 2, sy * width / 2, 0))
        legs.append((a + off, b + off * 0.55))
        beam("lat_leg", material, a + off, b + off * 0.55, thick=thick)
    for k in range(1, panels + 1):
        t0, t1 = (k - 1) / panels, k / panels
        for i in range(4):
            j = (i + 1) % 4
            beam("lat_ring", material, legs[i][0].lerp(legs[i][1], t1), legs[j][0].lerp(legs[j][1], t1), thick=thick * 0.8)
            beam("lat_x", material, legs[i][0].lerp(legs[i][1], t0), legs[j][0].lerp(legs[j][1], t1), thick=thick * 0.6)


# ---------------------------------------------------------------------------------------------------------
# Muralha, pilar e vao do portao
# ---------------------------------------------------------------------------------------------------------


def naga_wall():
    """Quebra-mar de blocos encaixados com remate arredondado, cabecos de ferro e corrente."""
    p = pal()
    length = 3.2
    box("foot", p["stone_dk"], (0, 0, 0), (length, 1.1, 0.2), bevel=0.03)
    courses = (((-0.55, 0.9), "stone"), ((-1.0, 0.35), "stone_dk"), ((-0.2, 1.1), "stone"))
    for i, (cuts, tone) in enumerate(courses):
        edges = [-length / 2, *cuts, length / 2]
        for k, (x0, x1) in enumerate(itertools.pairwise(edges)):
            t = p[tone] if (k + i) % 2 == 0 else p["stone_lt" if tone == "stone" else "stone"]
            box("block", t, ((x0 + x1) / 2, 0, 0.2 + i * 0.28), (x1 - x0, 0.94 - 0.05 * i, 0.28), bevel=0.025, taper_y=0.93)
    box("coping_slab", p["stone_lt"], (0, 0, 1.04), (length, 0.8, 0.08), bevel=0.0)
    cyl("coping", p["stone_lt"], (-length / 2, 0, 1.06), 0.3, length, sides=10, bevel=0.0, rot=("Y", PI / 2))
    for x in (-0.95, 0.95):
        bollard(p, (x, 0, 1.22), height=0.18)
    chain(p["iron_lt"], (-0.95, 0, 1.4), (0.95, 0, 1.4), sag=0.08, links=6, thick=0.04)
    for x, w in ((-1.2, 0.5), (0.1, 0.34), (1.3, 0.4)):
        box("kelp_stain", p["kelp"], (x, -0.46, 0.2), (w, 0.04, 0.2), bevel=0.0)
    for x in (-0.5, 0.7, 1.45):
        box("barnacles", p["barn"], (x, -0.5, 0.24), (0.24, 0.04, 0.1), bevel=0.0)
    normalize(length, 1.1)


def naga_pillar():
    """Pilone de pedra com faixa vermelha e lanterna de sinais de bronze."""
    p = pal()
    box("foot", p["stone_dk"], (0, 0, 0), (1.1, 1.1, 0.25), bevel=0.04)
    box("shaft", p["stone"], (0, 0, 0.22), (0.92, 0.92, 0.75), bevel=0.04, taper=0.9, taper_y=0.9)
    box("band", p["coral"], (0, 0, 0.9), (0.8, 0.8, 0.14), bevel=0.0)
    box("shaft_up", p["stone"], (0, 0, 1.0), (0.78, 0.78, 0.62), bevel=0.04, taper=0.9, taper_y=0.9)
    box("cap", p["stone_lt"], (0, 0, 1.58), (0.92, 0.92, 0.13), bevel=0.03)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        beam("lamp_post", p["bronze"], (sx * 0.15, sy * 0.15, 1.7), (sx * 0.15, sy * 0.15, 2.05), thick=0.05)
    box("lamp_glow", p["amber"], (0, 0, 1.76), (0.24, 0.24, 0.26), bevel=0.0)
    cyl("lamp_roof", p["verd"], (0, 0, 2.05), 0.26, 0.26, sides=4, top_radius=0.0, bevel=0.0, rot=("Z", PI / 4))
    cyl("lamp_tip", p["bronze"], (0, 0, 2.3), 0.05, 0.1, sides=6, bevel=0.0)
    for i, (dx, dy, rz) in enumerate(((0.38, 0.3, 0.3), (-0.4, -0.3, 1.1))):
        box("barnacle_rock", p["barn"] if i else p["stone_dk"], (dx, dy, 0), (0.24, 0.2, 0.12), bevel=0.04, rot_z=rz)
    frame("ring", p["iron"], (0.0, -0.47, 0.5), "y", 0.1, thick=0.04, sides=8)
    normalize(1.1, 1.1, 1.83)


def naga_arch():
    """Meio portico de madeira alcatroada com lanterna pendurada (o Terrain espelha no eixo)."""
    p = pal()
    z0, z1 = 0.98, 1.27
    for y in (-0.16, 0.16):
        box("girder", p["tar"], (-0.25, y, z0), (0.5, 0.07, 0.2), bevel=0.0)
        beam("knee", p["tar_lt"], (-0.5, y, z0 - 0.12), (-0.3, y, z0), thick=0.04)
    box("deck", p["tar_lt"], (-0.25, 0, z1 - 0.07), (0.5, 0.4, 0.04), bevel=0.0)
    box("rail_band", p["red"], (-0.25, -0.2, z0 + 0.04), (0.4, 0.02, 0.1), bevel=0.0)
    beam("hang", p["iron_lt"], (-0.03, 0, z0), (-0.03, 0, z0 - 0.1), thick=0.015)
    box("lantern_frame", p["brass"], (-0.025, 0, z0 - 0.26), (0.05, 0.12, 0.17), bevel=0.0)
    box("lantern_glow", p["amber"], (-0.025, 0, z0 - 0.23), (0.04, 0.09, 0.11), bevel=0.0)
    box("lantern_cap", p["verd"], (-0.025, 0, z0 - 0.1), (0.05, 0.14, 0.04), bevel=0.0)


# ---------------------------------------------------------------------------------------------------------
# Arvores: mangues secos, coral morto, poste de amarracao (toco)
# ---------------------------------------------------------------------------------------------------------


def stilt_roots(p, count, reach, top_z, phase=0.0, r=0.08):
    for i in range(count):
        a = phase + i * math.tau / count
        c, s = math.cos(a), math.sin(a)
        path("root", p["mangrove_lt"] if i % 2 else p["mangrove"],
             [(c * 0.1, s * 0.1, top_z), (c * reach * 0.7, s * reach * 0.7, top_z * 0.55), (c * reach, s * reach, 0.0)], r, r * 0.7)


def mangrove(p, lean, branches, roots, clumps):
    stilt_roots(p, roots, 1.0, 1.3, phase=0.4)
    pts = [(0, 0, 1.2), (lean[0] * 0.3, lean[1] * 0.3, 2.5), (lean[0] * 0.7, lean[1] * 0.7, 3.9), (lean[0], lean[1], 4.9)]
    path("trunk", p["mangrove"], pts, 0.27, 0.11)
    cyl("tide_line", p["bleach"], (0, 0, 0.55), 0.12, 0.1, sides=6, bevel=0.0)
    for k, (t, d, ln) in enumerate(branches):
        a = Vector(pts[t])
        b = a + Vector(d).normalized() * ln
        limb("branch", p["mangrove_lt"] if k % 2 else p["mangrove"], a, b, 0.1, 0.03)
        limb("twig", p["mangrove"], b, b + Vector((d[1], -d[0], 0.7)).normalized() * ln * 0.45, 0.04, 0.015)
    for cx, cy, cz, r in clumps:
        dome("dry_leaves", p["olive"], (cx, cy, cz), r, squash=0.55, sides=8)


def naga_tree_a():
    p = pal()
    mangrove(p, (0.2, 0.0), ((1, (1, 0.3, 0.6), 1.3), (2, (-1, 0.5, 0.5), 1.2), (2, (0.2, -1, 0.6), 1.0), (3, (-0.4, 0.9, 0.7), 0.8)), 6,
             ((0.9, 0.3, 3.9, 0.55), (-0.8, 0.5, 4.3, 0.5)))
    kelp_hang(p, (0.5, 0.2, 2.4))


def naga_tree_b():
    """Coral morto branqueado: tronco curto que se abre em garfos rombudos, sobre um monte de areia."""
    p = pal()
    cyl("mound", p["sand_dk"], (0, 0, 0), 0.8, 0.22, sides=9, top_radius=0.5, bevel=0.0)
    trunk = [(0, 0, 0.15), (0.05, 0, 1.2), (0.1, 0.05, 2.0)]
    path("trunk", p["bleach"], trunk, 0.34, 0.2)
    forks = ((1.0, 0.1, 0.9), (-0.9, 0.4, 0.8), (0.1, -1.0, 0.85), (-0.2, 0.9, 1.0))
    for k, f in enumerate(forks):
        a = Vector(trunk[-1])
        m = a + Vector(f).normalized() * 1.3
        tone = p["bleach"] if k % 2 else p["dead_coral"]
        limb("fork", tone, a, m, 0.18, 0.12)
        top = m + Vector((f[0] * 0.3, f[1] * 0.3, 1.0)).normalized() * 1.5
        limb("fork_top", tone, m, top, 0.12, 0.07)
        for s in (-1, 1):
            tip = (m + top) / 2
            limb("nub", p["dead_coral"], tip, tip + Vector((s * 0.5 * f[1], -s * 0.5 * f[0], 0.6)), 0.07, 0.045)
    for dx, dy in ((0.5, 0.4), (-0.4, -0.5)):
        dome("pink_coral", p["coral_pale"], (dx, dy, 0.2), 0.22, squash=0.8, sides=7)


def naga_tree_c():
    """Mangue tombado para um lado, topo quebrado, boia vermelha presa num galho."""
    p = pal()
    mangrove(p, (-0.9, 0.35), ((1, (-1, 0.2, 0.7), 1.2), (2, (1, 0.6, 0.6), 0.9), (3, (0.2, -1, 0.5), 0.8)), 4, ((0.7, 0.6, 3.5, 0.5),))
    kit.spike(p["mangrove_lt"], (-0.9, 0.35, 4.9), height=0.4, radius=0.08, lean=(-0.1, 0.0))
    cyl("buoy", p["coral"], (0.35, 0.5, 2.45), 0.2, 0.34, sides=8, top_radius=0.15, bevel=0.0)
    cyl("buoy_band", p["white"], (0.35, 0.5, 2.58), 0.205, 0.07, sides=8, bevel=0.0)
    kelp_hang(p, (-0.2, 0.3, 2.5))


def kelp_hang(p, top):
    """Fitas de alga secas penduradas de um galho."""
    for i, (dx, dy, ln) in enumerate(((0.0, 0.0, 0.9), (0.18, 0.1, 0.65), (-0.15, -0.08, 0.75))):
        a = Vector(top) + Vector((dx, dy, 0))
        limb("kelp_hang", p["kelp"] if i % 2 else p["kelp_lt"], a, a + Vector((0.05, 0, -ln)), 0.045, 0.02, sides=4)


def naga_post():
    """Toco: poste de amarracao cravado, lapidado pelo mar, com cracas, anel de ferro e cabo."""
    p = pal()
    cyl("base_rocks", p["stone_dk"], (0, 0, 0), 0.7, 0.2, sides=8, top_radius=0.55)
    cyl("post", p["wood_dk"], (0, 0, 0.18), 0.4, 0.95, sides=8, top_radius=0.34, bevel=0.0)
    cyl("tide_line", p["barn"], (0, 0, 0.3), 0.405, 0.18, sides=8, top_radius=0.395, bevel=0.0)
    cyl("top_cap", p["iron"], (0, 0, 1.1), 0.4, 0.09, sides=8, bevel=0.0)
    frame("ring", p["iron_lt"], (0.0, -0.37, 0.85), "y", 0.15, thick=0.045, sides=8)
    for z, r in ((0.7, 0.4), (0.78, 0.4), (0.86, 0.39), (0.94, 0.38)):
        cyl("rope", p["rope"], (0, 0, z), r + 0.01, 0.05, sides=8, bevel=0.0)
    limb("rope_tail", p["rope"], (0.3, -0.2, 0.7), (0.75, -0.45, 0.06), 0.045, 0.04, sides=5)
    for dx, dy in ((0.3, 0.2), (-0.25, 0.25), (0.1, -0.35)):
        dome("barnacle", p["barn"], (dx, dy, 0.28), 0.07, squash=0.8, sides=6)


# ---------------------------------------------------------------------------------------------------------
# "Arbustos" e "pedras"
# ---------------------------------------------------------------------------------------------------------


def naga_kelp():
    """Monte de algas e madeira de deriva com uma boia (lugar do arbusto)."""
    p = pal()
    box("heap", p["sand_dk"], (0, 0, 0), (1.9, 1.3, 0.14), bevel=0.06, taper=0.8, taper_y=0.8)
    for a, b, r in (((-0.9, -0.3, 0.1), (0.8, 0.35, 0.42), 0.08), ((-0.7, 0.4, 0.1), (0.9, -0.4, 0.34), 0.07), ((-0.2, -0.5, 0.15), (0.3, 0.6, 0.5), 0.06)):
        limb("driftwood", p["wood"], a, b, r, r * 0.8, sides=5)
    for i, (x, y, h, lean) in enumerate(((-0.5, 0.2, 0.85, 0.3), (-0.1, -0.2, 0.95, -0.2), (0.3, 0.3, 0.75, 0.25), (0.6, -0.15, 0.85, -0.3), (-0.8, -0.1, 0.6, 0.2), (0.0, 0.1, 0.5, 0.0))):
        path("kelp", p["kelp"] if i % 2 else p["kelp_lt"], [(x, y, 0.1), (x + lean * 0.5, y, h * 0.6), (x + lean, y + 0.1, h)], 0.06, 0.025, sides=4)
    cyl("float", p["coral"], (0.65, 0.4, 0.1), 0.17, 0.26, sides=7, bevel=0.0)
    cyl("float2", p["white"], (-0.55, -0.45, 0.1), 0.13, 0.2, sides=7, bevel=0.0)
    limb("rope", p["rope"], (0.65, 0.4, 0.3), (0.2, -0.1, 0.4), 0.025, 0.025, sides=4)


def naga_pots():
    """Covos de lagosta e rede secando num cavalete (lugar do arbusto)."""
    p = pal()
    for x in (-0.85, 0.85):
        beam("rack_leg", p["wood_dk"], (x - 0.12, -0.2, 0.0), (x, 0.0, 0.95), thick=0.08)
        beam("rack_leg", p["wood_dk"], (x - 0.12, 0.2, 0.0), (x, 0.0, 0.95), thick=0.08)
    beam("rack_bar", p["wood"], (-0.95, 0, 0.95), (0.95, 0, 0.95), thick=0.09)
    for i in range(11):
        x = -0.8 + i * 0.16
        beam("net_v", p["rope"], (x, 0, 0.93), (x, 0, 0.5 + 0.06 * (i % 3)), thick=0.025)
    for z in (0.8, 0.65, 0.52):
        beam("net_h", p["rope"], (-0.8, 0, z), (0.8, 0, z - 0.04), thick=0.025)
    for x, y, rz in ((-0.3, -0.5, 0.2), (0.35, -0.55, -0.3)):
        box("pot", p["wood"], (x, y, 0), (0.62, 0.42, 0.36), bevel=0.03, taper=0.82, taper_y=0.82, rot_z=rz)
        for dx in (-0.2, 0.0, 0.2):
            box("pot_slat", p["wood_dk"], (x + dx * math.cos(rz), y + dx * math.sin(rz), 0.0), (0.04, 0.44, 0.34), bevel=0.0, rot_z=rz)
        box("pot_mouth", p["tar"], (x, y, 0.32), (0.3, 0.2, 0.05), bevel=0.0, rot_z=rz)
    cyl("float", p["coral"], (0.1, -0.45, 0.0), 0.15, 0.22, sides=7, bevel=0.0)
    box("fish_box", p["hull"], (0.0, 0.5, 0.0), (0.5, 0.34, 0.2), bevel=0.02, rot_z=0.5)


def naga_log():
    """Tronco de madeira de deriva branqueado (espalha-se na extensao)."""
    p = pal()
    limb("log", p["wood"], (-1.2, 0.0, 0.3), (1.2, 0.1, 0.34), 0.3, 0.25, sides=7)
    limb("log_cut", p["bleach"], (1.2, 0.1, 0.34), (1.26, 0.1, 0.34), 0.25, 0.25, sides=7)
    for sx, sy, ex, ey in ((-0.4, 0.0, -0.9, 0.7), (0.5, 0.05, 0.9, -0.7), (0.1, 0.1, 0.2, 0.8)):
        limb("stub", p["wood_dk"], (sx, sy, 0.45), (ex, ey, 0.55), 0.08, 0.04, sides=5)
    box("sand", p["sand_dk"], (0, 0, 0), (2.8, 0.9, 0.08), bevel=0.04, taper=0.8, taper_y=0.7)
    dome("barnacle", p["barn"], (-0.2, -0.2, 0.52), 0.1, squash=0.6, sides=6)


def naga_boulder():
    """Rocha com craca e linha de mare: fundo molhado e escuro, topo claro e seco (lugar da pedra)."""
    p = pal()
    box("base", p["stone_dk"], (0, 0, 0), (3.2, 2.5, 0.65), bevel=0.15, taper=0.78, taper_y=0.78, rot_z=0.25)
    box("tide_line", p["barn"], (0.05, 0, 0.62), (2.5, 2.0, 0.14), bevel=0.04, taper=0.96, taper_y=0.96, rot_z=0.25)
    box("mid", p["stone"], (0.1, 0.05, 0.74), (2.4, 1.95, 0.6), bevel=0.12, taper=0.74, taper_y=0.74, rot_z=0.5)
    box("top", p["stone_lt"], (-0.1, -0.05, 1.3), (1.5, 1.2, 0.42), bevel=0.1, taper=0.7, taper_y=0.7, rot_z=0.8)
    box("shelf", p["stone"], (1.0, -0.6, 0.0), (1.2, 0.9, 0.45), bevel=0.1, taper=0.7, taper_y=0.7, rot_z=-0.4)
    for x, y, r in ((-1.2, 0.6, 0.35), (0.6, -1.0, 0.3), (1.3, 0.7, 0.28)):
        dome("barnacles", p["barn"], (x, y, 0.62), r * 0.5, squash=0.5, sides=6)
    for x, y, rz in ((-1.1, -0.5, 0.4), (-0.4, 1.0, 1.2)):
        box("kelp", p["kelp"], (x, y, 0.0), (0.6, 0.3, 0.1), bevel=0.02, rot_z=rz)
    dome("starfish", p["coral"], (0.9, -1.0, 0.5), 0.14, squash=0.4, sides=5)


def naga_boat():
    """Barco a remo encalhado, inclinado na areia, com tabuas, remos e uma faixa vermelha (lugar da pedra)."""
    p = pal()
    box("sand", p["sand_dk"], (0, 0, 0), (3.6, 2.0, 0.22), bevel=0.1, taper=0.7, taper_y=0.7, rot_z=0.1)
    hull(p["hull"], 3.3, 1.35, 0.55, z0=0.2, rise=0.3)
    # borda clara e fita vermelha dos dois lados
    for s in (-1, 1):
        beam("gunwale", p["wood"], (-1.3, s * 0.62, 0.78), (1.5, s * 0.5, 0.95), thick=0.07)
        beam("stripe", p["red"], (-1.2, s * 0.57, 0.62), (1.5, s * 0.4, 0.8), thick=0.05)
    box("floor", p["tar"], (0.0, 0, 0.74), (2.6, 0.8, 0.04), bevel=0.0)
    for x in (-0.7, 0.2, 0.9):
        box("thwart", p["wood"], (x, 0, 0.74), (0.2, 1.1 - abs(x) * 0.3, 0.07), bevel=0.0)
    beam("oar", p["wood"], (-0.5, 0.2, 0.9), (0.9, 1.35, 0.2), thick=0.07)
    box("blade", p["white"], (1.05, 1.5, 0.12), (0.34, 0.2, 0.05), bevel=0.0, rot_z=0.9)
    limb("rope", p["rope"], (1.7, 0.0, 0.8), (2.0, 0.6, 0.18), 0.035, 0.035, sides=4)
    dome("bucket", p["coral"], (-1.0, 0.0, 0.78), 0.14, squash=0.8, sides=7)


def naga_crates():
    """Pilha de caixotes, barril, rolo de cabo e uma ancora de ferro (lugar da pedra)."""
    p = pal()
    box("pallet", p["wood_dk"], (0, 0, 0), (3.0, 2.1, 0.12), bevel=0.02)
    crate(p, (-0.8, -0.35, 0.12), (0.9, 0.8, 0.7), 0.1)
    crate(p, (0.0, -0.4, 0.12), (0.8, 0.7, 0.55), -0.15, tone="tar_lt", band="tar")
    crate(p, (-0.55, -0.3, 0.82), (0.7, 0.6, 0.5), 0.4, tone="wood", band="red")
    crate(p, (-0.9, 0.55, 0.12), (0.6, 0.55, 0.45), 0.5)
    barrel(p, (0.7, 0.5, 0.12), 0.26, 0.55, "tar_lt")
    barrel(p, (1.1, -0.1, 0.12), 0.24, 0.5, "wood_dk")
    box("sack", p["sand"], (0.1, 0.7, 0.12), (0.6, 0.38, 0.28), bevel=0.1, rot_z=0.4)
    cyl("rope_coil", p["rope"], (1.2, 0.65, 0.12), 0.34, 0.14, sides=10, top_radius=0.3, bevel=0.0)
    cyl("rope_hole", p["wood_dk"], (1.2, 0.65, 0.25), 0.14, 0.03, sides=8, bevel=0.0)
    # ancora deitada no chao da pilha
    ax, ay = 0.1, -1.3
    beam("shank", p["iron"], (ax - 0.8, ay, 0.28), (ax + 0.8, ay, 0.28), thick=0.13)
    beam("stock", p["wood_dk"], (ax - 0.6, ay - 0.45, 0.28), (ax - 0.6, ay + 0.45, 0.28), thick=0.1)
    for s in (-1, 1):
        beam("arm", p["iron"], (ax + 0.8, ay, 0.28), (ax + 0.55, ay + s * 0.5, 0.28), thick=0.12)
        box("fluke", p["iron_lt"], (ax + 0.5, ay + s * 0.58, 0.2), (0.26, 0.2, 0.1), bevel=0.0, rot_z=s * 0.5)
    frame("anchor_ring", p["iron_lt"], (ax - 0.88, ay, 0.28), "z", 0.1, thick=0.05, sides=8)


# ---------------------------------------------------------------------------------------------------------
# Peca central: valvula-capitel da piramide
# ---------------------------------------------------------------------------------------------------------


def slick(material, cx, cy, rx, ry, rot, z):
    """Mancha achatada e irregular, rente a agua."""
    ob = cyl("slick", material, (0, 0, z), 1.0, 0.004, sides=9, bevel=0.0)
    c, s = math.cos(rot), math.sin(rot)
    for i, v in enumerate(ob.data.vertices):
        k = 1.0 + 0.22 * math.sin(i * 2.3)
        x, y = v.co.x * rx * k, v.co.y * ry * k
        v.co.x, v.co.y = cx + x * c - y * s, cy + x * s + y * c


def naga_valve():
    """Capitel de piramide: degraus de pedra, roda de valvula de bronze, correntes e manchas escuras na lagoa."""
    p = pal()
    cyl("splash_ring", p["stone_dk"], (0, 0, 0), 1.45, 0.1, sides=12, top_radius=1.35)
    top = stepped([p["sea_dk"], p["sea"], p["sea_lt"]], (0, 0, 0.1), 2.5, (0.36, 0.34, 0.32), 0.78, taper=0.9)
    box("capstone", p["verd"], (0, 0, top), (0.8, 0.8, 0.26), bevel=0.03, taper=0.55, taper_y=0.55)
    cyl("axle_post", p["bronze_dk"], (0, 0, top + 0.2), 0.12, 0.45, sides=8, top_radius=0.1)
    wheel(p["bronze"], (0, -0.05, top + 0.85), "y", 0.52, spokes=6, thick=0.065)
    box("lamp_glow", p["amber"], (0.0, 0.05, top + 1.45), (0.2, 0.2, 0.22), bevel=0.0)
    box("lamp_hood", p["verd"], (0.0, 0.05, top + 1.66), (0.3, 0.3, 0.07), bevel=0.0)
    for sx in (-1, 1):
        chain(p["bronze_dk"], (sx * 0.5, -0.1, top + 0.85), (sx * 1.2, -0.6, 0.3), sag=0.15, links=9, thick=0.045)
        chain(p["iron_lt"], (sx * 0.25, 0.15, top + 0.3), (sx * 1.25, 0.5, 0.3), sag=0.1, links=8, thick=0.04)
    for y, z in ((-1.07, 0.55), (-0.85, 0.9)):
        box("lamp_bronze", p["amber"], (-0.5, y * 0.9, z), (0.1, 0.1, 0.09), bevel=0.0)
    # manchas (achatadas, ate 0,06 de altura): oleo azul-violeta e verde-petroleo, mais escamas claras
    tones = (p["slick_a"], p["slick_b"], p["slick_c"])
    spots = ((-4.6, 3.4, 2.6, 1.3, 0.3), (3.9, 4.8, 2.2, 1.0, 1.1), (4.8, -2.6, 2.7, 1.2, 2.0), (-3.4, -5.0, 2.4, 1.1, 0.7),
             (1.2, -6.4, 1.8, 0.9, 2.6), (-5.4, -0.8, 1.6, 0.8, 1.6), (0.8, 6.2, 2.0, 1.0, 0.1), (5.6, 1.2, 1.4, 0.7, 0.4))
    for i, (x, y, rx, ry, rot) in enumerate(spots):
        slick(tones[i % 3], x, y, rx, ry, rot, 0.045 + 0.003 * (i % 4))
        slick(tones[(i + 1) % 3], x + rx * 0.35, y - ry * 0.2, rx * 0.5, ry * 0.55, rot + 0.8, 0.052 + 0.003 * (i % 3))
    # destrocos boiando: tabuas, barris deitados, boia salva-vidas
    for x, y, rz in ((-2.4, -2.6, 0.5), (3.0, 1.0, 1.6), (-1.6, 3.0, 2.4), (1.6, -4.4, 0.2)):
        box("plank", p["wood"], (x, y, 0.045), (1.4, 0.24, 0.07), bevel=0.0, rot_z=rz)
        box("plank_b", p["wood_dk"], (x + 0.3, y + 0.28, 0.045), (0.9, 0.22, 0.06), bevel=0.0, rot_z=rz + 0.3)
    for x, y in ((-3.6, 0.8), (2.2, 3.6)):
        cyl("barrel", p["tar_lt"], (x, y, 0.05), 0.24, 0.5, sides=8, bevel=0.0, rot=("Y", PI / 2))
    for i in range(10):
        a = i * math.tau / 10
        pos = (-1.8 + math.cos(a) * 0.42, -4.0 + math.sin(a) * 0.42, 0.045)
        box("buoy_seg", p["red"] if i % 2 else p["white"], pos, (0.3, 0.2, 0.06), bevel=0.0, rot_z=a + PI / 2)
    # os nos da corrente soltam argolas de ferro na agua
    for x, y in ((1.4, 0.6), (-1.5, 0.4)):
        frame("loose_ring", p["iron_lt"], (x, y, 0.05), "z", 0.22, thick=0.07, sides=8)


# ---------------------------------------------------------------------------------------------------------
# Castelos
# ---------------------------------------------------------------------------------------------------------


def wall_run(wall, foot, deck, a, b, fixed, along_x, height=1.1, thick=0.7):
    """Cortina em talude com pe e convés claro no topo (o que a camera de RTS le)."""
    length, mid = abs(b - a), (a + b) / 2
    c = (mid, fixed, 0.0) if along_x else (fixed, mid, 0.0)
    dims = (length, thick, height) if along_x else (thick, length, height)
    tp = (1.0, 0.74) if along_x else (0.74, 1.0)
    box("wall", wall, c, dims, bevel=0.03, taper=tp[0], taper_y=tp[1])
    foot_dims = (length, thick * 1.2, 0.16) if along_x else (thick * 1.2, length, 0.16)
    box("wall_foot", foot, c, foot_dims, bevel=0.03)
    deck_dims = (length, thick * 0.76, 0.06) if along_x else (thick * 0.76, length, 0.06)
    box("wall_deck", deck, (c[0], c[1], height), deck_dims, bevel=0.01)


def spikes(material, pos, count, radius, height, z):
    for i in range(count):
        a = i * math.tau / count
        kit.spike(material, (pos[0] + math.cos(a) * radius, pos[1] + math.sin(a) * radius, z), height=height, radius=0.1, lean=(math.cos(a) * 0.18, math.sin(a) * 0.18))


def coral_bastion(p, pos, radius, height, sides):
    """Bastiao de pedra verde com cinta de bronze e coroa de coral."""
    x, y = pos
    cyl("bastion_foot", p["teal"], (x, y, 0), radius * 1.18, 0.2, sides=sides, bevel=0.03)
    cyl("bastion", p["sea_dk"], (x, y, 0.16), radius * 1.06, height, sides=sides, top_radius=radius * 0.88, bevel=0.03)
    kit.ring("bastion_band", p["bronze"], (x, y, height * 0.5), radius * 0.95, 0.09, thick=0.05, sides=sides)
    cyl("bastion_deck", p["sea_lt"], (x, y, height + 0.14), radius * 0.92, 0.07, sides=sides, bevel=0.0)
    spikes(p["coral"], pos, 5, radius * 0.6, 0.38, height + 0.2)
    kit.spike(p["coral_pale"], (x, y, height + 0.2), height=0.6, radius=0.13, lean=(0.05, 0.0))
    box("bastion_lamp", p["amber"], (x + radius * 0.7, y, height + 0.2), (0.1, 0.1, 0.1), bevel=0.0)


def sluice_gate(p, gx):
    """Portaria: bloco de pedra com comporta de bronze meio levantada, roda de cremalheira e escada d'agua."""
    box("gate_block", p["sea_dk"], (gx, 0, 0.1), (1.0, 1.9, 1.35), bevel=0.04, taper=0.9, taper_y=0.92)
    box("gate_deck", p["sea_lt"], (gx, 0, 1.45), (0.94, 1.7, 0.07), bevel=0.0)
    box("gate_channel", p["void"], (gx + 0.46, 0, 0.12), (0.12, 0.84, 0.92), bevel=0.0)
    box("sluice_plate", p["bronze"], (gx + 0.53, 0, 0.62), (0.07, 0.78, 0.55), bevel=0.01)
    for s in (-1, 1):
        box("guide", p["bronze_dk"], (gx + 0.55, s * 0.45, 0.12), (0.1, 0.1, 1.22), bevel=0.0)
        box("gate_lamp", p["amber"], (gx + 0.2, s * 0.8, 1.5), (0.1, 0.1, 0.12), bevel=0.0)
        kit.spike(p["coral"], (gx - 0.1, s * 0.7, 1.5), height=0.5, radius=0.1, lean=(0.05, s * 0.1))
    wheel(p["bronze"], (gx + 0.62, 0, 1.15), "x", 0.3, spokes=6, thick=0.05)
    wheel(p["bronze"], (gx - 0.05, 0, 1.55), "z", 0.36, spokes=6, thick=0.06)  # cabrestante visto de cima
    cyl("capstan_post", p["bronze_dk"], (gx - 0.05, 0, 1.5), 0.09, 0.2, sides=6, bevel=0.0)
    beam("rack", p["bronze_dk"], (gx + 0.58, 0, 1.0), (gx + 0.58, 0, 0.9), thick=0.05)
    # escada d'agua: degraus baixos de pedra clara com um veio de agua escura no meio
    for i, h in enumerate((0.2, 0.12)):
        for s in (-1, 1):
            box("water_step", p["sea_lt"], (gx + 0.95 + i * 0.24, s * 0.42, 0.0), (0.26, 0.4, h), bevel=0.02)
    box("water_run", p["void"], (gx + 1.1, 0, 0.0), (0.5, 0.3, 0.05), bevel=0.0)


def naga_pyramid():
    """Naga, Piramide-Valvula: fortaleza baixa e larga de pedra verde-mar em tres terracos."""
    p = pal()
    half, w = 2.55, 2.1
    box("plinth", p["teal"], (0, 0, 0), (half * 2 + 0.4, half * 2 + 0.4, 0.14), bevel=0.05, taper=0.96, taper_y=0.96)
    box("yard", p["stone"], (0, 0, 0.12), (half * 2 - 0.5, half * 2 - 0.5, 0.08), bevel=0.03)
    for along_x, fixed in ((True, w), (True, -w), (False, -w)):
        wall_run(p["sea"], p["sea_dk"], p["sea_lt"], -w + 0.3, w - 0.3, fixed, along_x, thick=0.74)
    wall_run(p["sea"], p["sea_dk"], p["sea_lt"], -w + 0.3, -0.85, w, False, thick=0.74)
    wall_run(p["sea"], p["sea_dk"], p["sea_lt"], 0.85, w - 0.3, w, False, thick=0.74)
    for sx, sy, r, sides in ((1, 1, 0.82, 10), (1, -1, 0.82, 10), (-1, 1, 0.7, 6), (-1, -1, 0.7, 6)):
        coral_bastion(p, (sx * (w + 0.18), sy * (w + 0.18)), r, 1.45 if sx > 0 else 1.25, sides)
    sluice_gate(p, w + 0.15)
    # anexo do lado do mar: bacia de mare com borda de bronze, roda e cabecos
    box("annex", p["teal"], (-0.8, -half - 0.3, 0), (2.6, 0.9, 0.12), bevel=0.04)
    box("basin_rim", p["bronze"], (-0.8, -half - 0.3, 0.1), (1.9, 0.62, 0.06), bevel=0.02)
    box("basin_water", p["void"], (-0.8, -half - 0.3, 0.14), (1.7, 0.44, 0.03), bevel=0.0)
    wheel(p["bronze"], (-1.6, -half - 0.3, 0.45), "y", 0.28, spokes=6, thick=0.045)
    bollard(p, (-0.2, -half - 0.3, 0.1), 0.2)
    bollard(p, (0.1, -half - 0.1, 0.1), 0.2)
    # terracos (a plataforma de cima e clara) ----------------------------------------------------------
    kx = -0.3
    z1 = 0.14 + 0.95
    box("terrace1", p["sea"], (kx, 0, 0.14), (3.0, 3.0, 0.95), bevel=0.05, taper=0.9, taper_y=0.9)
    box("terrace1_band", p["bronze"], (kx, 0, 0.5), (2.86, 2.86, 0.05), bevel=0.0)
    box("deck1", p["sea_lt"], (kx, 0, z1), (2.62, 2.62, 0.04), bevel=0.0)
    z2 = z1 + 0.04
    box("terrace2", p["sea"], (kx + 0.1, 0, z2), (2.25, 2.25, 0.8), bevel=0.05, taper=0.9, taper_y=0.9)
    box("terrace2_band", p["verd"], (kx + 0.1, 0, z2 + 0.3), (2.15, 2.15, 0.05), bevel=0.0)
    box("deck2", p["sea_lt"], (kx + 0.1, 0, z2 + 0.8), (1.96, 1.96, 0.04), bevel=0.0)
    z3 = z2 + 0.84
    box("terrace3", p["sea"], (kx + 0.15, 0, z3), (1.6, 1.6, 0.65), bevel=0.04, taper=0.88, taper_y=0.88)
    box("deck3", p["sea_lt"], (kx + 0.15, 0, z3 + 0.65), (1.38, 1.38, 0.04), bevel=0.0)
    top = z3 + 0.69
    # escada do lado da lane e veio d'agua do portao ate a piramide
    for i in range(4):
        box("pyr_step", p["sea_lt"], (1.55 - i * 0.12, 0, 0.0), (0.2, 0.7, 0.1 + 0.11 * i), bevel=0.01)
    box("water_run", p["void"], (1.95, 0, 0.12), (0.8, 0.3, 0.03), bevel=0.0)
    # grandes rodas de valvula nas faces e correntes ate o chao
    for y in (-0.72, 0.72):
        wheel(p["bronze"], (1.28, y, 0.62), "x", 0.38, spokes=6, thick=0.055)
        chain(p["bronze_dk"], (1.3, y, 0.3), (1.95, y * 1.4, 0.2), sag=0.1, links=7, thick=0.045)
    wheel(p["bronze"], (kx, -1.62, 0.62), "y", 0.42, spokes=8, thick=0.055)
    wheel(p["verd"], (kx + 0.3, -1.2, z2 + 0.46), "y", 0.3, spokes=6, thick=0.045)
    chain(p["bronze_dk"], (kx - 0.4, -1.65, 0.45), (kx - 1.4, -2.2, 0.2), sag=0.15, links=8, thick=0.045)
    for y in (-0.5, 0.0, 0.5):
        window_slit(p, (kx + 1.16, y, z2 + 0.4))
    # capitel de bronze e a coroa: mastro marcador de mare fora do centro ------------------------------------
    box("capstone", p["bronze"], (kx + 0.45, -0.35, top), (0.6, 0.6, 0.3), bevel=0.02, taper=0.25, taper_y=0.25)
    mx, my = kx - 0.3, 0.45
    beam("gauge_mast", p["bronze_dk"], (mx, my, top), (mx, my, top + 2.2), thick=0.08)
    for i in range(9):
        box("gauge_tick", p["amber"] if i % 4 == 0 else p["bronze"], (mx + 0.1, my, top + 0.15 + i * 0.22), (0.14, 0.05, 0.06), bevel=0.0)
    for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        beam("gauge_brace", p["bronze_dk"], (mx + sx * 0.45, my + sy * 0.45, top), (mx, my, top + 0.75), thick=0.05)
    box("gauge_lamp", p["amber"], (mx, my, top + 2.2), (0.2, 0.2, 0.2), bevel=0.0)
    cyl("gauge_hood", p["verd"], (mx, my, top + 2.4), 0.2, 0.2, sides=4, top_radius=0.0, bevel=0.0, rot=("Z", PI / 4))
    beam("gauge_arm", p["bronze"], (mx - 0.4, my, top + 1.7), (mx + 0.4, my, top + 1.7), thick=0.05)
    chain(p["bronze_dk"], (mx + 0.4, my, top + 1.7), (mx + 0.4, my, top + 1.1), sag=0.0, links=2, thick=0.03)
    dome("plumb", p["bronze"], (mx + 0.4, my, top + 0.95), 0.13, squash=1.0, sides=6)


def window_slit(p, pos):
    kit.window(p["teal"], p["amber"], (pos[0], pos[1], pos[2]), "x+", w=0.14, h=0.3)


def cannon(p, root, tip):
    beam("cannon", p["iron"], root, tip, thick=0.13)
    beam("cannon_muzzle", p["brass"], Vector(root).lerp(Vector(tip), 0.82), tip, thick=0.17)


def keep_lighthouse(p, kx, ky, z):
    """Torre-farol atarracada: fustes brancos com cintas vermelhas, galeria clara e sala da lampada."""
    cyl("tower", p["white"], (kx, ky, z), 0.82, 1.3, sides=12, top_radius=0.66, bevel=0.0)
    kit.ring("tower_band", p["red"], (kx, ky, z + 0.3), 0.74, 0.22, thick=0.04, sides=12)
    kit.ring("tower_band", p["red"], (kx, ky, z + 0.82), 0.7, 0.2, thick=0.04, sides=12)
    top = z + 1.3
    cyl("gallery", p["granite_lt"], (kx, ky, top), 0.88, 0.09, sides=12, bevel=0.0)
    for i in range(10):
        a = i * math.tau / 10
        beam("rail", p["brass"], (kx + math.cos(a) * 0.82, ky + math.sin(a) * 0.82, top + 0.09), (kx + math.cos(a) * 0.82, ky + math.sin(a) * 0.82, top + 0.28), thick=0.03)
    cyl("lamp_glass", p["glass"], (kx, ky, top + 0.09), 0.4, 0.46, sides=8, bevel=0.0)
    for i in range(8):
        a = i * math.tau / 8 + PI / 8
        beam("lamp_bar", p["brass"], (kx + math.cos(a) * 0.41, ky + math.sin(a) * 0.41, top + 0.09), (kx + math.cos(a) * 0.41, ky + math.sin(a) * 0.41, top + 0.55), thick=0.04)
    dome("lamp_dome", p["brass"], (kx, ky, top + 0.55), 0.5, squash=0.7, sides=10)
    kit.spike(p["brass"], (kx, ky, top + 0.9), height=0.3, radius=0.05)
    return top + 0.9


def crane(p, pos, height=1.45, reach=1.3):
    x, y = pos
    box("crane_foot", p["granite_dk"], (x, y, 0.1), (0.6, 0.6, 0.14), bevel=0.03)
    cyl("crane_post", p["tar"], (x, y, 0.2), 0.12, height, sides=8)
    cyl("crane_cab", p["red"], (x, y, 0.2 + height * 0.55), 0.2, 0.34, sides=8, bevel=0.0)
    top = 0.2 + height
    beam("jib", p["red"], (x, y - 0.5, top - 0.05), (x, y + reach, top - 0.2), thick=0.1)
    beam("jib_stay", p["iron"], (x, y, top + 0.35), (x, y + reach, top - 0.2), thick=0.035)
    beam("jib_stay", p["iron"], (x, y, top + 0.35), (x, y - 0.5, top - 0.05), thick=0.035)
    beam("mast_top", p["tar"], (x, y, top), (x, y, top + 0.35), thick=0.07)
    box("counterweight", p["iron"], (x, y - 0.55, top - 0.3), (0.3, 0.3, 0.26), bevel=0.02)
    beam("cable", p["iron_lt"], (x, y + reach, top - 0.2), (x, y + reach, 0.78), thick=0.02)
    crate(p, (x, y + reach, 0.34), (0.42, 0.42, 0.4), 0.3, tone="wood", band="red")
    cyl("hook", p["brass"], (x, y + reach, 0.74), 0.05, 0.08, sides=6, bevel=0.0)


def signal_mast(p, pos, z0, height=2.3):
    """Mastro de sinais fora do centro: verga, adriças e bandeiras de sinalização."""
    x, y = pos
    top = z0 + height
    limb("mast", p["tar"], (x, y, z0), (x, y, top), 0.07, 0.04, sides=6)
    beam("yard", p["wood"], (x, y - 0.55, top - 0.35), (x, y + 0.55, top - 0.35), thick=0.05)
    beam("halyard", p["iron_lt"], (x, y, top), (x, y - 0.55, top - 0.35), thick=0.018)
    beam("halyard", p["iron_lt"], (x, y, top), (x, y + 0.55, top - 0.35), thick=0.018)
    box("mast_lamp", p["amber"], (x, y, top), (0.12, 0.12, 0.12), bevel=0.0)
    for i, tone in enumerate(("red", "white", "brass", "hull", "red", "coral")):
        fx = x + 0.04
        box("flag", p[tone], (fx, y - 0.45 + i * 0.18, top - 0.62 - 0.02 * i), (0.03, 0.17, 0.2), bevel=0.0)
        beam("flag_line", p["iron_lt"], (x, y - 0.46 + i * 0.18, top - 0.35), (x, y - 0.46 + i * 0.18, top - 0.45 - 0.02 * i), thick=0.012)
    box("pennant", p["red"], (x + 0.04, y, top - 0.3), (0.03, 0.4, 0.1), bevel=0.0, taper=0.4, taper_y=0.4)


def boathouse(p, gx):
    """Portaria: galpao de barcos de madeira alcatroada, teto vermelho de sinalizacao e rampa d'agua."""
    box("bh_plinth", p["granite_dk"], (gx, 0, 0.1), (1.7, 2.1, 0.32), bevel=0.04)
    box("bh_walls", p["tar_lt"], (gx, 0, 0.4), (1.5, 1.9, 0.8), bevel=0.03)
    for y in (-0.7, -0.35, 0.35, 0.7):
        box("bh_post", p["tar"], (gx + 0.76, y, 0.4), (0.06, 0.1, 0.8), bevel=0.0)
    prism("bh_roof", p["red"], (gx, 0, 1.2), (2.3, 1.9, 0.75), ridge=0.5, rot_z=PI / 2)
    box("bh_ridge", p["white"], (gx, 0, 1.92), (1.92, 0.12, 0.06), bevel=0.0)
    box("bh_door", p["void"], (gx + 0.76, 0, 0.42), (0.1, 1.0, 0.7), bevel=0.0)
    box("bh_lintel", p["granite_lt"], (gx + 0.78, 0, 1.12), (0.12, 1.2, 0.09), bevel=0.0)
    for i, h in enumerate((0.2, 0.1)):
        box("slip", p["granite_dk"], (gx + 1.0 + i * 0.28, 0, 0.0), (0.3, 1.0, h), bevel=0.02)
    box("slip_water", p["hull"], (gx + 1.25, 0, 0.0), (0.4, 0.6, 0.03), bevel=0.0)
    for s in (-1, 1):
        box("bh_lamp", p["amber"], (gx + 0.82, s * 0.62, 1.16), (0.1, 0.1, 0.12), bevel=0.0)
        bollard(p, (gx + 1.15, s * 0.85, 0.0), 0.22)
    chain(p["iron_lt"], (gx + 1.15, -0.85, 0.2), (gx + 1.15, 0.85, 0.2), sag=0.08, links=8, thick=0.04)


def naga_harbour():
    """Concordia da Mare, Forte do Porto: artilharia costeira de granito com farol, galpao e guindaste."""
    p = pal()
    half, w = 2.6, 2.15
    box("plinth", p["granite_dk"], (0, 0, 0), (half * 2 + 0.4, half * 2 + 0.4, 0.15), bevel=0.05, taper=0.96, taper_y=0.96)
    box("quay", p["granite"], (0, 0, 0.13), (half * 2 - 0.5, half * 2 - 0.5, 0.08), bevel=0.03)
    gr = (p["granite"], p["granite_dk"], p["granite_lt"])
    wall_run(*gr, -w, w - 1.0, -w, False, thick=0.95, height=1.2)  # fundo (o canto de terra e cortado)
    wall_run(*gr, -w, w, -w, True, thick=0.95, height=1.2)  # lado do mar
    wall_run(*gr, -w + 1.0, w, w, True, thick=0.95, height=1.2)  # lado de terra
    box("wall_chamfer", p["granite"], (-w + 0.5, w - 0.5, 0.0), (1.6, 0.95, 1.2), bevel=0.03, taper_y=0.74, rot_z=PI / 4)
    box("wall_chamfer_deck", p["granite_lt"], (-w + 0.5, w - 0.5, 1.2), (1.5, 0.72, 0.06), bevel=0.01, rot_z=PI / 4)
    wall_run(*gr, -w, -0.95, w, False, thick=0.95, height=1.2)
    wall_run(*gr, 0.95, w, w, False, thick=0.95, height=1.2)
    # bastiao arredondado do lado do mar, com bateria de canhoes e canhoneiras
    bx, by, br = w - 0.2, -w - 0.1, 1.3
    cyl("sea_bastion_foot", p["granite_dk"], (bx, by, 0), br * 1.12, 0.2, sides=16, bevel=0.03)
    cyl("sea_bastion", p["granite"], (bx, by, 0.16), br * 1.04, 1.3, sides=16, top_radius=br * 0.9, bevel=0.03)
    cyl("sea_bastion_deck", p["granite_lt"], (bx, by, 1.46), br * 0.9, 0.07, sides=16, bevel=0.0)
    kit.ring("sea_bastion_band", p["red"], (bx, by, 0.4), br * 0.95, 0.1, thick=0.04, sides=16)
    for ang in (-160, -130, -100, -70, -40, -10):
        a = math.radians(ang)
        box("embrasure", p["void"], (bx + math.cos(a) * br * 0.96, by + math.sin(a) * br * 0.96, 0.78), (0.3, 0.1, 0.24), bevel=0.0, rot_z=a + PI / 2)
    cyl("turntable", p["iron"], (bx - 0.1, by - 0.1, 1.52), 0.34, 0.1, sides=10, bevel=0.0)
    cannon(p, (bx - 0.1, by - 0.1, 1.72), (bx + 0.35, by - 0.85, 1.76))
    cannon(p, (bx - 0.45, by + 0.15, 1.62), (bx + 0.1, by - 0.45, 1.66))
    # torre quadrada de sinais na quina de terra (frente), torrinha redonda atras no mar
    box("land_bastion", p["granite"], (w + 0.1, w + 0.1, 0.1), (1.5, 1.5, 1.45), bevel=0.04, taper=0.88, taper_y=0.88)
    box("land_bastion_deck", p["granite_lt"], (w + 0.1, w + 0.1, 1.55), (1.3, 1.3, 0.06), bevel=0.0)
    box("land_bastion_band", p["red"], (w + 0.1, w + 0.1, 0.55), (1.46, 1.46, 0.09), bevel=0.0)
    cannon(p, (w + 0.1, w + 0.2, 1.7), (w + 0.75, w + 0.65, 1.74))
    cyl("rear_turret", p["granite"], (-w - 0.1, -w - 0.1, 0.1), 0.78, 1.3, sides=10, top_radius=0.66, bevel=0.03)
    cyl("rear_turret_deck", p["granite_lt"], (-w - 0.1, -w - 0.1, 1.4), 0.7, 0.07, sides=10, bevel=0.0)
    dome("rear_turret_lamp", p["brass"], (-w - 0.1, -w - 0.1, 1.47), 0.32, squash=0.7, sides=8)
    kit.ring("rear_turret_ring", p["red"], (-w - 0.1, -w - 0.1, 1.4), 0.62, 0.1, thick=0.0, sides=10)
    # galpao de barcos como portaria
    boathouse(p, w + 0.2)
    # torre-farol (menagem) e o convés claro do patio
    kx = -0.55
    box("keep_base", p["granite"], (kx, 0.1, 0.13), (2.3, 2.1, 0.85), bevel=0.05, taper=0.93, taper_y=0.93)
    box("keep_deck", p["granite_lt"], (kx, 0.1, 0.98), (2.1, 1.9, 0.05), bevel=0.0)
    for y in (-0.6, 0.0, 0.6):
        kit.window(p["iron"], p["amber"], (kx + 1.08, 0.1 + y, 0.45), "x+", w=0.18, h=0.3)
    keep_lighthouse(p, kx - 0.2, 0.3, 1.03)
    # patio: guindaste, carga empilhada e canhao de salva
    crane(p, (1.15, -0.85), height=1.9, reach=1.6)
    for dx, dy, rz in ((0.0, 0.0, 0.1), (0.5, 0.05, -0.2), (0.15, 0.5, 0.3)):
        crate(p, (1.15 + dx, 1.35 + dy, 0.13), (0.5, 0.5, 0.42), rz, tone="wood" if dx else "tar_lt", band="tar" if dx else "red")
    crate(p, (1.25, 1.4, 0.55), (0.42, 0.42, 0.36), 0.5, tone="wood", band="red")
    barrel(p, (-1.5, -1.55, 0.13), 0.22, 0.5)
    barrel(p, (-1.1, -1.7, 0.13), 0.22, 0.5, "tar_lt")
    box("tarp", p["hull"], (-1.6, 1.55, 0.13), (0.8, 0.5, 0.2), bevel=0.06, rot_z=0.3)
    # coroa: mastro de sinais fora do centro (sobre o convés do forte)
    signal_mast(p, (kx - 0.9, -0.75), 0.98, height=3.2)


# ---------------------------------------------------------------------------------------------------------
# Decoracao fora do andavel (5 kinds)
# ---------------------------------------------------------------------------------------------------------


def truss(material, a, b, depth, panels, thick=0.05):
    """Trelica plana (no plano xz) entre a e b com banzo de cima, de baixo e diagonais."""
    a, b = Vector(a), Vector(b)
    up = Vector((0, 0, depth))
    beam("chord_lo", material, a, b, thick=thick)
    beam("chord_hi", material, a + up, b + up, thick=thick)
    for i in range(panels):
        p0, p1 = a.lerp(b, i / panels), a.lerp(b, (i + 1) / panels)
        beam("web", material, p0 + (up if i % 2 else Vector()), p1 + (Vector() if i % 2 else up), thick=thick * 0.7)


def decor_crane():
    """Kind 0: guindaste portuario de portico (torre ~8,5), trelica de ferro, cabine vermelha e carga pendurada."""
    p = pal()
    box("quay", p["granite_dk"], (0, 0, 0), (3.6, 3.0, 0.2), bevel=0.04)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        box("leg", p["iron"], (sx * 1.35, sy * 1.1, 0.2), (0.26, 0.26, 2.3), bevel=0.02)
    for sy in (-1, 1):
        beam("portal_beam", p["tar"], (-1.45, sy * 1.1, 2.4), (1.45, sy * 1.1, 2.4), thick=0.24)
        beam("portal_brace", p["iron_lt"], (-1.35, sy * 1.1, 0.4), (1.35, sy * 1.1, 2.3), thick=0.07)
        beam("portal_brace", p["iron_lt"], (1.35, sy * 1.1, 0.4), (-1.35, sy * 1.1, 2.3), thick=0.07)
    for sx in (-1, 1):
        beam("portal_cross", p["tar"], (sx * 1.35, -1.1, 2.4), (sx * 1.35, 1.1, 2.4), thick=0.24)
    box("slewing", p["iron"], (0, 0, 2.5), (1.5, 1.5, 0.3), bevel=0.03)
    lattice(p, p["iron_lt"], (0, 0, 2.8), (0, 0, 6.0), 1.0, 5, thick=0.07)
    box("cab", p["red"], (0.2, 0.9, 4.6), (1.0, 0.9, 0.8), bevel=0.04)
    box("cab_glass", p["glass"], (0.72, 0.9, 4.85), (0.06, 0.6, 0.35), bevel=0.0)
    box("cab_roof", p["white"], (0.2, 0.9, 5.4), (1.1, 1.0, 0.07), bevel=0.0)
    truss(p["red"], (0.0, 0.0, 6.0), (3.4, 0.0, 6.5), 0.5, 7, thick=0.08)
    truss(p["red"], (-1.8, 0.0, 6.0), (0.0, 0.0, 6.0), 0.45, 3, thick=0.07)
    box("counterweight", p["iron"], (-2.0, 0, 5.4), (0.9, 0.9, 0.7), bevel=0.03)
    box("counterweight_band", p["brass"], (-2.0, 0, 5.8), (0.92, 0.92, 0.08), bevel=0.0)
    beam("mast", p["red"], (0, 0, 6.0), (0.0, 0.0, 8.4), thick=0.18)
    for tip in ((3.4, 0, 7.0), (-1.9, 0, 6.5)):
        beam("stay", p["iron"], (0, 0, 8.3), tip, thick=0.045)
    box("beacon", p["amber"], (0, 0, 8.4), (0.24, 0.24, 0.26), bevel=0.0)
    beam("cable", p["iron_lt"], (3.2, 0, 6.2), (3.2, 0, 3.4), thick=0.04)
    crate(p, (3.2, 0, 2.8), (0.8, 0.8, 0.6), 0.2, tone="wood", band="red")
    beam("sling", p["iron_lt"], (3.2, 0, 3.4), (3.0, 0.3, 3.4), thick=0.03)
    cyl("hook", p["brass"], (3.2, 0, 3.35), 0.08, 0.12, sides=6, bevel=0.0)
    for x in (-1.2, 0.3, 1.2):
        crate(p, (x, -0.3, 0.2), (0.45, 0.45, 0.35), x, tone="tar_lt", band="tar")


def decor_pyramid():
    """Kind 1: pequena piramide-valvula em degraus, meio afundada na areia, com a roda de bronze caida de lado."""
    p = pal()
    cyl("sand", p["sand"], (0, 0, 0), 1.9, 0.35, sides=11, top_radius=1.4, bevel=0.0)
    cyl("sand_dk", p["sand_dk"], (0.9, -0.5, 0), 1.2, 0.2, sides=8, top_radius=0.8, bevel=0.0)
    z = 0.15
    z = stepped([p["sea_dk"], p["sea"], p["sea_lt"]], (0, 0, z), 2.7, (0.55, 0.5, 0.45), 0.72, taper=0.9, rot_z=0.15)
    box("capstone", p["verd"], (0, 0, z), (0.6, 0.6, 0.3), bevel=0.02, taper=0.3, taper_y=0.3)
    cyl("axle", p["bronze_dk"], (0, 0, z), 0.09, 0.4, sides=6)
    wheel(p["bronze"], (0, -0.05, z + 0.7), "y", 0.42, spokes=6, thick=0.06)
    wheel(p["bronze"], (1.5, 0.4, 0.34), "z", 0.38, spokes=6, thick=0.06)
    chain(p["bronze_dk"], (0.4, -0.2, z + 0.5), (1.4, -0.8, 0.3), sag=0.12, links=8, thick=0.05)
    for dx, dy, r in ((-1.2, 0.8, 0.3), (-0.8, -1.2, 0.26), (1.1, 1.1, 0.24)):
        dome("kelp_clump", p["kelp"], (dx, dy, 0.3), r, squash=0.6, sides=7)
    dome("coral_tuft", p["coral"], (-1.4, -0.4, 0.3), 0.2, squash=0.9, sides=6)


def decor_lamp():
    """Kind 2: farol de sinais fino de pedra, com sala de vidro ambar e cupula de bronze (~6,2)."""
    p = pal()
    box("base", p["stone_dk"], (0, 0, 0), (1.1, 1.1, 0.3), bevel=0.04)
    box("shaft", p["stone"], (0, 0, 0.28), (0.9, 0.9, 2.6), bevel=0.04, taper=0.62, taper_y=0.62)
    box("band", p["red"], (0, 0, 1.2), (0.72, 0.72, 0.4), bevel=0.0, taper=0.94, taper_y=0.94)
    box("band2", p["white"], (0, 0, 2.0), (0.62, 0.62, 0.35), bevel=0.0, taper=0.94, taper_y=0.94)
    box("gallery", p["stone_lt"], (0, 0, 2.88), (1.2, 1.2, 0.12), bevel=0.02)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        beam("lamp_post", p["bronze"], (sx * 0.28, sy * 0.28, 3.0), (sx * 0.28, sy * 0.28, 3.9), thick=0.07)
        beam("rail", p["bronze_dk"], (sx * 0.55, sy * 0.55, 3.0), (sx * 0.55, sy * 0.55, 3.35), thick=0.05)
    box("lamp_glow", p["amber"], (0, 0, 3.05), (0.5, 0.5, 0.8), bevel=0.0)
    box("lamp_cap", p["verd"], (0, 0, 3.9), (0.8, 0.8, 0.1), bevel=0.02)
    cyl("lamp_roof", p["verd"], (0, 0, 4.0), 0.5, 0.5, sides=4, top_radius=0.06, bevel=0.0, rot=("Z", PI / 4))
    beam("lightning_rod", p["bronze_dk"], (0, 0, 4.5), (0, 0, 5.8), thick=0.05)
    box("vane", p["coral"], (0.12, 0, 5.5), (0.3, 0.03, 0.2), bevel=0.0)
    for i in range(3):
        a = i * math.tau / 3
        box("kelp_foot", p["kelp"], (math.cos(a) * 0.7, math.sin(a) * 0.7, 0.0), (0.4, 0.2, 0.15), bevel=0.02, rot_z=a)


def decor_breakwater():
    """Kind 3: trecho de quebra-mar de 8 de comprimento: blocos encaixados, passadico, tetrapodes e baliza."""
    p = pal()
    box("footing", p["stone_dk"], (0, 0, 0), (8.0, 1.8, 0.3), bevel=0.06, taper_y=0.9)
    for i in range(7):
        x = -3.6 + i * 1.2
        tone = p["stone"] if i % 2 == 0 else p["stone_lt"]
        box("block", tone, (x, 0.05, 0.28), (1.15, 1.0, 0.62 + 0.1 * (i % 3)), bevel=0.06, taper=0.94, taper_y=0.92, rot_z=0.04 * (i % 3 - 1))
    box("walkway", p["granite_lt"], (-0.2, 0.05, 0.9), (6.8, 0.5, 0.07), bevel=0.0)
    for x in (-3.0, 2.2):
        bollard(p, (x, 0.05, 0.97), 0.25)
    chain(p["iron_lt"], (-3.0, 0.05, 1.3), (2.2, 0.05, 1.3), sag=0.25, links=10, thick=0.04)
    for i, (x, y, rz) in enumerate(((-3.4, -1.05, 0.2), (-1.8, -1.2, 0.9), (-0.2, -1.1, 0.4), (1.5, -1.2, 1.2), (3.2, -1.05, 0.6))):
        tetrapod(p, (x, y, 0.0), 0.5, rz, "dead_coral" if i % 2 else "barn")
    # baliza na ponta: poste branco e vermelho com lampada
    cyl("beacon_post", p["white"], (3.7, 0.05, 0.9), 0.1, 1.5, sides=6, bevel=0.0)
    cyl("beacon_band", p["red"], (3.7, 0.05, 1.3), 0.11, 0.35, sides=6, bevel=0.0)
    box("beacon_lamp", p["amber"], (3.7, 0.05, 2.35), (0.3, 0.3, 0.3), bevel=0.0)
    box("beacon_cap", p["verd"], (3.7, 0.05, 2.65), (0.4, 0.4, 0.07), bevel=0.0)
    for x in (-2.0, 0.4):
        dome("kelp_clump", p["kelp"], (x, 0.9, 0.28), 0.28, squash=0.5, sides=7)


def tetrapod(p, pos, size, rot, tone):
    """Tetrapode de concreto: quatro bracos saindo de um ponto central."""
    x, y, z = pos
    c = Vector((x, y, z + size * 0.55))
    dirs = ((0.94, 0, -0.33), (-0.47, 0.82, -0.33), (-0.47, -0.82, -0.33), (0, 0, 1.0))
    for dx, dy, dz in dirs:
        ca, sa = math.cos(rot), math.sin(rot)
        d = Vector((dx * ca - dy * sa, dx * sa + dy * ca, dz)) * size
        limb("tetrapod_arm", p[tone], c, c + d, size * 0.3, size * 0.2, sides=6)
    dome("tetrapod_core", p[tone], (c.x, c.y, c.z - size * 0.15), size * 0.3, squash=1.0, sides=6)


def decor_mast():
    """Kind 4: mastro de um navio naufragado, de pe sobre o casco enterrado, com vergas e enxarcia (~7)."""
    p = pal()
    cyl("sand", p["sand"], (0, 0, 0), 1.6, 0.3, sides=10, top_radius=1.1, bevel=0.0)
    hull(p["hull"], 3.0, 1.4, 0.7, x0=0.2, z0=0.1, rise=0.35)
    for s in (-1, 1):
        beam("gunwale", p["wood_dk"], (-1.1, s * 0.66, 0.84), (1.7, s * 0.5, 1.15), thick=0.09)
        beam("plank_stripe", p["red"], (-1.0, s * 0.62, 0.65), (1.6, s * 0.42, 0.95), thick=0.06)
    box("deck", p["tar_lt"], (0.2, 0, 0.8), (2.5, 1.0, 0.05), bevel=0.0)
    beam("bowsprit", p["wood"], (1.5, 0, 1.1), (2.6, 0, 1.7), thick=0.1)
    limb("mast", p["tar_lt"], (0.1, 0, 0.8), (0.1, 0, 7.0), 0.17, 0.08, sides=7)
    for z, ln in ((3.4, 2.4), (5.2, 1.7)):
        beam("yard", p["wood"], (0.1, -ln / 2, z), (0.1, ln / 2, z), thick=0.1)
        cyl("sail_furled", p["bleach"], (0.1, -ln / 2 + 0.1, z - 0.18), 0.12, ln - 0.2, sides=6, bevel=0.0, rot=("X", -PI / 2))
        for s in (-1, 1):
            beam("shroud", p["iron_lt"], (0.1, s * ln / 2, z), (0.0, s * 0.62, 0.9), thick=0.03)
    for k, (z, s) in enumerate(((1.6, 1), (2.4, -1), (3.0, 1))):
        beam("ratline", p["rope"], (0.1, s * 0.12, z), (0.1, s * 0.5 * (1 - z / 5.0), z + 0.01), thick=0.025)
    frame("crow_nest", p["wood_dk"], (0.1, 0, 5.9), "z", 0.42, thick=0.07, sides=8)
    cyl("crow_floor", p["tar"], (0.1, 0, 5.82), 0.4, 0.06, sides=8, bevel=0.0)
    box("flag", p["coral"], (0.1, 0.25, 6.7), (0.04, 0.5, 0.3), bevel=0.0)
    box("mast_lamp", p["amber"], (0.1, 0, 7.0), (0.14, 0.14, 0.14), bevel=0.0)
    for dx, dy in ((-1.0, 0.9), (1.3, -0.8)):
        dome("kelp_clump", p["kelp"], (dx, dy, 0.28), 0.3, squash=0.5, sides=7)


# ---------------------------------------------------------------------------------------------------------
# Bichos (+x e a frente; o jogo escala para o tamanho da especie)
# ---------------------------------------------------------------------------------------------------------


def blob(name, material, x0, z0, length, width, height, count=8, power=0.5):
    """Corpo ovoide fechado ao longo de x (aneis de 8 pontos)."""
    stations = []
    for i in range(count):
        t = i / (count - 1) * 2 - 1
        k = max((1 - t * t) ** power, 0.15)
        ring_pts = [(width / 2 * k * math.cos(a), z0 + height / 2 * (1 + k * math.sin(a))) for a in (j * math.tau / 8 for j in range(8))]
        stations.append((x0 + t * length / 2, ring_pts))
    return loft(name, material, stations)


def critter_crab():
    p = pal()
    blob("shell", p["coral"], 0.0, 0.12, 0.62, 0.9, 0.3, power=0.6)
    box("belly", p["coral_pale"], (0, 0, 0.1), (0.5, 0.7, 0.06), bevel=0.0)
    for s in (-1, 1):
        for k, x in enumerate((-0.18, 0.0, 0.18)):
            beam("leg", p["coral"], (x, s * 0.4, 0.28), (x - 0.05 * (k - 1), s * 0.78, 0.0), thick=0.07)
        beam("arm", p["coral"], (0.28, s * 0.36, 0.3), (0.6, s * 0.4, 0.3), thick=0.1)
        box("claw", p["coral"], (0.72, s * 0.4, 0.2), (0.3, 0.2, 0.18), bevel=0.02, rot_z=-s * 0.3)
        box("claw_gap", p["coral_pale"], (0.84, s * 0.34, 0.24), (0.14, 0.05, 0.1), bevel=0.0)
        cyl("eye", p["white"], (0.28, s * 0.14, 0.4), 0.05, 0.12, sides=5, bevel=0.0)
    box("eyestalk", p["coral"], (0.28, 0.0, 0.38), (0.06, 0.34, 0.06), bevel=0.0)


def critter_mudskipper():
    p = pal()
    blob("body", p["kelp"], -0.05, 0.05, 0.85, 0.28, 0.24, count=9, power=0.7)
    blob("head", p["olive"], 0.4, 0.07, 0.3, 0.3, 0.24, count=6, power=0.6)
    for s in (-1, 1):
        dome("eye", p["bleach"], (0.45, s * 0.12, 0.27), 0.08, squash=1.0, sides=6)
        beam("fin_front", p["kelp_lt"], (0.2, s * 0.12, 0.12), (0.34, s * 0.34, 0.02), thick=0.08)
    prism("dorsal", p["coral"], (-0.05, 0, 0.27), (0.5, 0.04, 0.3), ridge=0.3)
    beam("tail", p["kelp"], (-0.45, 0, 0.15), (-0.8, 0.08, 0.12), thick=0.1)
    box("tail_fin", p["coral"], (-0.8, 0.08, 0.04), (0.08, 0.04, 0.2), bevel=0.0)


def critter_sandpiper():
    p = pal()
    blob("body", p["sand_dk"], 0.0, 0.34, 0.5, 0.3, 0.3, power=0.6)
    box("belly", p["white"], (0.04, 0, 0.32), (0.34, 0.24, 0.07), bevel=0.0)
    dome("head", p["sand_dk"], (0.3, 0, 0.58), 0.12, squash=1.0, sides=6)
    beam("bill", p["iron"], (0.4, 0, 0.62), (0.85, 0, 0.55), thick=0.04)
    for s in (-1, 1):
        beam("leg", p["bronze"], (0.0, s * 0.07, 0.36), (0.02, s * 0.08, 0.0), thick=0.035)
        box("foot", p["bronze"], (0.07, s * 0.08, 0.0), (0.16, 0.03, 0.02), bevel=0.0)
    beam("tail", p["sand_dk"], (-0.2, 0, 0.5), (-0.4, 0, 0.45), thick=0.08)
    box("wing_bar", p["iron"], (-0.02, 0, 0.58), (0.3, 0.3, 0.04), bevel=0.0)


def critter_rat():
    p = pal()
    blob("body", p["iron_lt"], -0.08, 0.1, 0.62, 0.34, 0.3, power=0.55)
    blob("head", p["iron_lt"], 0.38, 0.12, 0.34, 0.22, 0.2, count=6, power=0.7)
    dome("nose", p["coral_pale"], (0.56, 0, 0.2), 0.05, squash=1.0, sides=5)
    for s in (-1, 1):
        dome("ear", p["coral_pale"], (0.3, s * 0.1, 0.34), 0.07, squash=0.5, sides=6)
        box("leg", p["iron"], (0.12, s * 0.14, 0.0), (0.1, 0.06, 0.14), bevel=0.0)
        box("leg", p["iron"], (-0.26, s * 0.14, 0.0), (0.12, 0.06, 0.14), bevel=0.0)
        dome("eye", p["void"], (0.46, s * 0.07, 0.27), 0.03, squash=1.0, sides=4)
    path("tail", p["coral_pale"], [(-0.38, 0, 0.18), (-0.62, 0.06, 0.1), (-0.85, -0.05, 0.06), (-1.0, 0.0, 0.1)], 0.045, 0.02, sides=4)


def wings(material, tip_material, z, span, chord, sweep=0.35):
    for s in (-1, 1):
        box("wing_in", material, (-0.02, s * span * 0.2, z), (chord, span * 0.4, 0.05), bevel=0.0, rot_z=s * 0.15)
        box("wing_out", tip_material, (-0.12, s * span * 0.46, z + 0.07), (chord * 0.8, span * 0.32, 0.04), bevel=0.0, rot_z=s * sweep)


def critter_gull():
    p = pal()
    blob("body", p["white"], -0.05, 0.12, 0.7, 0.28, 0.26, power=0.6)
    dome("head", p["white"], (0.36, 0, 0.3), 0.12, squash=1.0, sides=6)
    beam("beak", p["brass"], (0.44, 0, 0.32), (0.58, 0, 0.3), thick=0.05)
    box("beak_dot", p["red"], (0.55, 0, 0.27), (0.04, 0.05, 0.04), bevel=0.0)
    wings(p["granite_lt"], p["iron"], 0.3, 1.2, 0.34)
    beam("tail", p["white"], (-0.35, 0, 0.22), (-0.6, 0, 0.2), thick=0.14)
    for s in (-1, 1):
        box("foot", p["coral"], (0.0, s * 0.07, 0.0), (0.12, 0.04, 0.1), bevel=0.0)


def critter_cormorant():
    p = pal()
    blob("body", p["iron"], -0.05, 0.1, 0.72, 0.28, 0.26, power=0.6)
    path("neck", p["iron"], [(0.25, 0, 0.3), (0.38, 0, 0.5), (0.4, 0, 0.66)], 0.075, 0.055, sides=5)
    dome("head", p["iron"], (0.42, 0, 0.66), 0.09, squash=1.0, sides=6)
    beam("beak", p["bronze"], (0.48, 0, 0.66), (0.66, 0, 0.6), thick=0.05)
    box("face", p["amber"], (0.46, 0, 0.62), (0.06, 0.12, 0.06), bevel=0.0)
    wings(p["iron"], p["teal"], 0.3, 1.25, 0.32, sweep=0.2)
    beam("tail", p["iron"], (-0.35, 0, 0.2), (-0.7, 0, 0.14), thick=0.12)


E_SCENERY = {
    "naga_decor_crane": decor_crane,
    "naga_decor_pyramid": decor_pyramid,
    "naga_decor_lamp": decor_lamp,
    "naga_decor_breakwater": decor_breakwater,
    "naga_decor_mast": decor_mast,
    "naga_crab": critter_crab,
    "naga_mudskipper": critter_mudskipper,
    "naga_sandpiper": critter_sandpiper,
    "naga_rat": critter_rat,
    "naga_gull": critter_gull,
    "naga_cormorant": critter_cormorant,
}


SCENERY = {
    "naga_wall": naga_wall,
    "naga_pillar": naga_pillar,
    "naga_arch": naga_arch,
    "naga_tree_a": naga_tree_a,
    "naga_tree_b": naga_tree_b,
    "naga_tree_c": naga_tree_c,
    "naga_post": naga_post,
    "naga_kelp": naga_kelp,
    "naga_pots": naga_pots,
    "naga_log": naga_log,
    "naga_boulder": naga_boulder,
    "naga_boat": naga_boat,
    "naga_crates": naga_crates,
    "naga_valve": naga_valve,
    **E_SCENERY,
}
CASTLES = {"naga_pyramid": naga_pyramid, "naga_harbour": naga_harbour}


def build(name, out_dir, render_dir, make, views, ground=0x8E9A8C, castle=False):
    """Como map_castles.build, mas com chao de areia molhada na previa e saida em castles/ ou scenery/."""
    kit.reset()
    make()
    if castle:
        normalize(1.08, 1.08, 1.08)  # pegada do castelo no porte da Frente do Petroleo (~3,2 de meia-largura)
    kit.bake()
    tris, lo, hi = kit.stats()
    print(f"MODEL {name}: tris={tris} min=({lo.x:.2f},{lo.y:.2f},{lo.z:.2f}) max=({hi.x:.2f},{hi.y:.2f},{hi.z:.2f})")
    if render_dir:
        os.makedirs(render_dir, exist_ok=True)
        span = max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, 0.5) * (1.3 if castle else 1.0)
        for tag, yaw in views:
            kit.render(os.path.join(render_dir, f"{name}_{tag}.png"), yaw, span=span, top=hi.z, ground=ground)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.export_scene.gltf(filepath=os.path.join(out_dir, f"{name}.glb"), export_format="GLB", use_selection=True, export_yup=True, export_apply=True)


ALL = {**CASTLES, **SCENERY}


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["all"]
    names = list(ALL) if args[0] == "all" else args[0].split(",")
    out_dir = args[args.index("--out") + 1] if "--out" in args else ""
    castle_dir = args[args.index("--castles") + 1] if "--castles" in args else ""
    render_dir = args[args.index("--render") + 1] if "--render" in args else ""
    for name in names:
        views = (("game", -90.0), ("back", 150.0)) if name in CASTLES else (("front", -35.0),)
        build(name, castle_dir if name in CASTLES else out_dir, render_dir, ALL[name], views, castle=name in CASTLES)


if __name__ == "__main__":
    main()
