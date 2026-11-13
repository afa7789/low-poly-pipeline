"""Mapa Ghostwood (The Ghostwood Turn, 1898): castelos, cenário e bichos modelados por script.

Uso:
    blender -b --factory-startup --python tools/blender/map_ghostwood.py -- <nome|all> [--out assets] [--render DIR]

Com --out assets, castelos vão para assets/castles (ghost_*.glb); cenário e bichos para assets/scenery/ghostwood. Usa o kit de
map_castles.py e as convenções de tamanho de map_scenery.py (muralha 3,2 x 1,1, pilar 1,1 x 1,1 x 2,4, vão do
portão em meio-modelo, árvore de 5, decoração de 5 kinds, peça central de raio 1,5). Sem magia grátis: todo
brilho tem portador material (resina âmbar e verde, esporos, lanterna).
"""

import functools
import itertools
import math
import os
import sys

import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_paths  # noqa: E402
import map_castles as kit
from map_castles import beam, box, cyl, dome, mat, ring
from map_scenery import normalize

# ---------------------------------------------------------------------------------------------------------
# Paleta e helpers próprios
# ---------------------------------------------------------------------------------------------------------


def palette():
    return {
        "bark": mat("bark", 0x6E5242),
        "bark_lt": mat("bark_light", 0x8E7152),
        "bark_vio": mat("bark_violet", 0x544258),
        "bark_dk": mat("bark_dark", 0x3A2C38),
        "dead": mat("dead", 0x2B2430),
        "dead_lt": mat("dead_light", 0x4A4054),
        "claw": mat("claw", 0xA094B2),
        "stone": mat("stone", 0x403B4E),
        "stone_lt": mat("stone_light", 0x5C566E),
        "stone_dk": mat("stone_dark", 0x2E2A38),
        "bone": mat("bone", 0xDCD3BA),
        "bone_dk": mat("bone_dark", 0xA89E86),
        "moss": mat("moss", 0x566E46),
        "moss_lt": mat("moss_light", 0x7A8A62),
        "leaf": mat("leaf", 0x4E3E6E),
        "leaf_lt": mat("leaf_light", 0x6A5690),
        "leaf_green": mat("leaf_green", 0x86B040),
        "thorn": mat("thorn", 0xCBBB8E),
        "copper": mat("copper", 0xC27A3E),
        "copper_dk": mat("copper_dark", 0x8A5230),
        "iron": mat("iron", 0x2F2B36),
        "wood": mat("wood", 0x8A6A46),
        "wood_dk": mat("wood_dark", 0x5A4430),
        "shingle": mat("shingle", 0xB89A66),
        "fungus": mat("fungus", 0xD9CFE2),
        "fungus_cap": mat("fungus_cap", 0xB69AD0),
        "fungus_dk": mat("fungus_dark", 0x7C6A92),
        "cloth": mat("cocoon", 0xE6E0D0),
        "cloth_dk": mat("cocoon_dark", 0xB8B0A6),
        "void": mat("void", 0x17121C),
        "pad": mat("pad", 0x5EA83E),
        "pad_dk": mat("pad_dark", 0x3A7A3E),
        "pad_pale": mat("pad_pale", 0x9CC85A),
        "resin": mat("resin", 0x7CEA4A, emit=2.6),
        "resin_dk": mat("resin_dark", 0x3F9A3A, emit=1.4),
        "amber": mat("amber", 0xFFB233, emit=3.0),
        "spore": mat("spore", 0xD2F56A, emit=2.4),
    }


def unit_up(d):
    """Evita a direção degenerada do to_track_quat quando o vetor é paralelo a y."""
    return d if abs(d.normalized().y) < 0.999 else d + Vector((1e-3, 0, 0))


def limb(name, material, pts, r0, r1, sides=6):
    """Tubo afunilado por uma polilinha (raízes, troncos tortos, galhos, costelas)."""
    pts = [Vector(p) for p in pts]
    n = len(pts) - 1
    for i, (a, b) in enumerate(itertools.pairwise(pts)):
        d = unit_up(b - a)
        ra, rb = r0 + (r1 - r0) * i / n, r0 + (r1 - r0) * (i + 1) / n
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=ra, radius2=max(rb, 1e-4), depth=d.length * 1.04)
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, d.length / 2))
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=d.to_track_quat("Z", "Y").to_matrix())
        bmesh.ops.translate(bm, verts=bm.verts, vec=a)
        kit._finish(bm, name, material)


def blob(name, material, center, rx, ry=None, rz=None, sides=8, rings=5):
    """Elipsoide baixo-poli (copas, cogumelos, casulos, contas de resina)."""
    ry = rx if ry is None else ry
    rz = rx if rz is None else rz
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=sides, v_segments=rings, radius=1.0)
    for v in bm.verts:
        v.co.x *= rx
        v.co.y *= ry
        v.co.z *= rz
    bmesh.ops.translate(bm, verts=bm.verts, vec=center)
    return kit._finish(bm, name, material)


def along(pts, t):
    """Ponto a fração t (0..1) de uma polilinha, por comprimento de segmentos iguais."""
    pts = [Vector(p) for p in pts]
    f = min(max(t, 0.0), 1.0) * (len(pts) - 1)
    i = min(int(f), len(pts) - 2)
    return pts[i].lerp(pts[i + 1], f - i)


def vein(material, pts, r0, r1, t0=0.05, t1=0.85, turns=0.6, phase=0.0, steps=6, thick=0.07):
    """Veia de resina em espiral rente à casca de um tronco que segue pts (raio r0 na base, r1 no topo)."""
    prev = None
    for i in range(steps + 1):
        t = t0 + (t1 - t0) * i / steps
        r = (r0 + (r1 - r0) * t) * 0.95
        a = phase + turns * math.tau * i / steps
        c = along(pts, t)
        cur = c + Vector((math.cos(a) * r, math.sin(a) * r, 0))
        if prev is not None:
            beam("vein", material, prev, cur, thick=thick)
        prev = cur


def thorn_ring(material, center, radius, count, height=0.4, spike_radius=0.07, tilt=0.35):
    for i in range(count):
        a = i * math.tau / count
        pos = (center[0] + math.cos(a) * radius, center[1] + math.sin(a) * radius, center[2])
        kit.spike(material, pos, height=height, radius=spike_radius, lean=(math.cos(a) * tilt, math.sin(a) * tilt))


def lantern(p, pos, size=0.3, cord=0.45):
    """Lanterna de resina pendurada: corda, armação de ferro e vidro âmbar aceso."""
    x, y, z = pos
    beam("cord", p["iron"], (x, y, z), (x, y, z + cord), thick=0.04)
    box("lamp_cap", p["iron"], (x, y, z - 0.03), (size * 0.9, size * 0.9, 0.06), bevel=0.0)
    box("lamp_glass", p["amber"], (x, y, z - size - 0.03), (size * 0.7, size * 0.7, size), bevel=0.0)
    box("lamp_foot", p["iron"], (x, y, z - size - 0.07), (size * 0.8, size * 0.8, 0.05), bevel=0.0)


def cocoon(p, pos, length=0.7, radius=0.2, cord=0.5):
    """Casulo pendurado: fuso pálido de seda com fita escura e fio."""
    x, y, z = pos
    beam("cord", p["bark_dk"], (x, y, z), (x, y, z + cord), thick=0.04)
    blob("cocoon", p["cloth"], (x, y, z - length / 2), radius, radius, length / 2, sides=7, rings=5)
    cyl("cocoon_band", p["cloth_dk"], (x, y, z - length * 0.55), radius * 1.03, 0.07, sides=7, bevel=0.0)


def root_flare(material, base, radius, count, spread, height, seed=0.0, thick=0.16):
    """Raízes que saem da base de um tronco e mergulham no chão."""
    for i in range(count):
        a = seed + i * math.tau / count + 0.3 * math.sin(i * 2.1)
        s = spread * (0.8 + 0.4 * ((i * 7) % 5) / 4)
        c, sn = math.cos(a), math.sin(a)
        pts = [(base[0] + c * radius * 0.6, base[1] + sn * radius * 0.6, base[2] + height),
               (base[0] + c * (radius + s * 0.5), base[1] + sn * (radius + s * 0.5), base[2] + height * 0.35),
               (base[0] + c * (radius + s), base[1] + sn * (radius + s), base[2])]
        limb("root", material, pts, thick, thick * 0.4, sides=5)


# ---------------------------------------------------------------------------------------------------------
# Muralha de raízes vivas, pilar-totem e vão do portão
# ---------------------------------------------------------------------------------------------------------


def ghost_wall():
    """Paliçada viva: raízes grossas trançadas dos dois lados de um núcleo de casca, espinhos e contas de resina."""
    p = palette()
    length = 3.2
    box("berm", p["bark_dk"], (0, 0, 0), (length, 0.96, 0.22), bevel=0.0, taper_y=0.86)
    box("core", p["bark_vio"], (0, 0, 0.18), (length, 0.6, 0.95), bevel=0.0, taper_y=0.84)
    box("deck", p["moss_lt"], (0, 0, 1.12), (length, 0.5, 0.07), bevel=0.0)
    for side in (-1, 1):
        for k, (z0, ph) in enumerate(((0.34, 0.0), (0.76, math.pi))):
            pts = []
            for i in range(9):
                x = -length / 2 + length * i / 8
                w = math.tau * x / length + ph + (0.9 if side > 0 else 0.0)
                pts.append((x, side * (0.35 + 0.05 * math.cos(w)), z0 + 0.15 * math.sin(w)))
            limb("weave", p["bark"] if k == 0 else p["bark_lt"], pts, 0.15, 0.15, sides=6)
        for x in (-1.0, 0.1, 1.2):
            blob("bead", p["amber"], (x, side * 0.46, 0.62 + 0.1 * math.sin(x * 3)), 0.09, 0.08, 0.1, sides=6, rings=3)
    for i, x in enumerate((-1.4, -0.75, -0.1, 0.55, 1.2)):
        kit.spike(p["thorn"], (x, (-0.1 if i % 2 else 0.1), 1.14), height=0.34 + 0.08 * (i % 2), radius=0.075, lean=(0.05, 0.0))
    normalize(length, 1.1)


def ghost_pillar():
    """Pilar de portão: tronco-totem entalhado com rosto de resina, coroa de espinhos e lanterna pendurada."""
    p = palette()
    box("foot", p["bark_dk"], (0, 0, 0), (1.1, 1.1, 0.25), bevel=0.04, taper=0.82, taper_y=0.82)
    cyl("trunk", p["bark"], (0, 0, 0.2), 0.46, 1.75, sides=8, top_radius=0.38, bevel=0.0)
    for z, tone in ((0.72, "bark_vio"), (1.32, "bark_dk")):
        ring("band", p[tone], (0, 0, z), 0.4, 0.14, thick=0.05, sides=8)
    for ax in (0.0, math.pi / 2, math.pi, 1.5 * math.pi):
        c, s = math.cos(ax), math.sin(ax)
        for sgn in (-1, 1):
            box("eye", p["resin"], (c * 0.42 - s * sgn * 0.14, s * 0.42 + c * sgn * 0.14, 1.0), (0.1, 0.1, 0.1), bevel=0.0, rot_z=ax)
        box("mouth", p["void"], (c * 0.4, s * 0.4, 0.82), (0.08, 0.2, 0.1), bevel=0.0, rot_z=ax)
    cyl("cap", p["moss_lt"], (0, 0, 1.92), 0.4, 0.1, sides=8, bevel=0.0)
    thorn_ring(p["thorn"], (0, 0, 1.98), 0.28, 5, height=0.5, spike_radius=0.08, tilt=0.12)
    beam("arm", p["bark_dk"], (0.28, 0, 1.78), (0.5, 0, 1.78), thick=0.08)
    lantern(p, (0.5, 0, 1.76), size=0.26, cord=0.0)
    root_flare(p["bark_dk"], (0, 0, 0), 0.45, 4, 0.25, 0.3, seed=0.4, thick=0.12)
    normalize(1.1, 1.1, 1.83)


def ghost_arch():
    """Meio vão do portão (espelhado pelo Terrain): raiz em arco com casulos e lanterna pendurados."""
    p = palette()
    z0 = 1.0
    limb("arch", p["bark"], [(-0.5, 0.1, z0 - 0.05), (-0.34, 0.06, z0 + 0.2), (-0.16, 0.02, z0 + 0.3), (0.0, 0.0, z0 + 0.28)], 0.12, 0.1, sides=6)
    limb("arch2", p["bark_lt"], [(-0.5, -0.1, z0 - 0.02), (-0.3, -0.06, z0 + 0.12), (-0.12, -0.02, z0 + 0.2), (0.0, 0.0, z0 + 0.2)], 0.08, 0.07, sides=5)
    box("deck", p["moss_lt"], (-0.22, 0, z0 + 0.3), (0.44, 0.22, 0.04), bevel=0.0)
    kit.spike(p["thorn"], (-0.38, 0.02, z0 + 0.3), height=0.13, radius=0.03)
    cocoon(p, (-0.34, 0.0, z0 - 0.02), length=0.17, radius=0.06, cord=0.04)
    beam("cord", p["bark_dk"], (-0.12, 0, z0 + 0.12), (-0.12, 0, z0 + 0.0), thick=0.02)
    box("lamp", p["amber"], (-0.12, 0, z0 - 0.12), (0.07, 0.07, 0.12), bevel=0.0)


# ---------------------------------------------------------------------------------------------------------
# Árvores, toco, obstáculos
# ---------------------------------------------------------------------------------------------------------


def twisted_tree(height, bends, branches, canopy, veins=(0.0, 3.0)):
    """Tronco torto de 5 de altura, raízes na base, veias de resina em espiral e copa rala violeta."""
    p = palette()
    pts = [Vector((0, 0, 0))]
    for dx, dy, dz in bends:
        pts.append(pts[-1] + Vector((dx, dy, dz)) * height)
    r0, r1 = 0.36, 0.1
    n = len(pts) - 1
    for i, (a, b) in enumerate(itertools.pairwise(pts)):
        limb("trunk", p["bark"] if i % 2 == 0 else p["bark_vio"], [a, b], r0 + (r1 - r0) * i / n, r0 + (r1 - r0) * (i + 1) / n, sides=7)
    root_flare(p["bark_dk"], (0, 0, 0), 0.3, 5, 0.38, 0.5, seed=0.2, thick=0.17)
    for k, ph in enumerate(veins):
        vein(p["amber"] if k % 2 == 0 else p["resin"], pts, r0, r1, t0=0.06 + 0.1 * k, t1=0.7 + 0.1 * k, turns=0.7, phase=ph, thick=0.08)
    tips = [pts[-1]]
    for seg, t, d, length in branches:
        a = pts[seg].lerp(pts[seg + 1], t)
        dv = Vector(d).normalized()
        mid = a + dv * length * height * 0.5 + Vector((0, 0, 0.08 * height * length))
        tip = a + dv * length * height
        limb("branch", p["bark_vio"], [a, mid, tip], 0.12, 0.05, sides=5)
        tips.append(tip)
    for i, (idx, rx, rz) in enumerate(canopy):
        c = tips[idx % len(tips)]
        blob("canopy", p["leaf"] if i % 2 == 0 else p["leaf_lt"], (c.x, c.y, c.z + rz * 0.4), rx, rx * 0.9, rz, sides=7, rings=4)


def ghost_tree_a():
    twisted_tree(5.0, ((0.04, 0.0, 0.34), (-0.06, 0.05, 0.3), (0.05, -0.03, 0.3)),
                 ((0, 0.75, (1, 0.3, 0.6), 0.22), (1, 0.55, (-1, 0.3, 0.7), 0.26), (2, 0.4, (0.3, -1, 0.8), 0.18)),
                 ((0, 0.8, 0.25), (1, 0.7, 0.22), (2, 0.65, 0.22), (3, 0.5, 0.2)))


def ghost_tree_b():
    twisted_tree(5.0, ((-0.05, 0.03, 0.4), (0.1, 0.0, 0.3), (-0.03, 0.06, 0.3)),
                 ((0, 0.6, (-1, -0.3, 0.5), 0.24), (1, 0.4, (0.8, 0.7, 0.6), 0.26), (2, 0.2, (-0.6, 0.8, 0.8), 0.15)),
                 ((1, 0.7, 0.22), (2, 0.8, 0.24)), veins=(1.0, 4.0))


def ghost_tree_c():
    """Quase sem folhas: tronco partido com garras e veias nos dois lados."""
    twisted_tree(5.0, ((0.06, 0.02, 0.36), (-0.04, -0.05, 0.34), (0.05, 0.04, 0.3)),
                 ((0, 0.7, (1, -0.5, 0.5), 0.2), (1, 0.4, (-1, 0.4, 0.4), 0.24), (1, 0.8, (0.2, 1, 0.6), 0.16)),
                 ((2, 0.5, 0.18),), veins=(2.0, 5.0))


def ghost_stump():
    """Toco oco com cogumelos-prateleira e musgo."""
    p = palette()
    cyl("base", p["bark_dk"], (0, 0, 0), 0.62, 0.22, sides=8, top_radius=0.48, bevel=0.0)
    cyl("stump", p["bark"], (0, 0, 0.2), 0.48, 0.62, sides=8, top_radius=0.4, bevel=0.0)
    cyl("rim", p["bone_dk"], (0, 0, 0.82), 0.4, 0.06, sides=8, bevel=0.0)
    cyl("hollow", p["void"], (0, 0, 0.86), 0.25, 0.04, sides=8, bevel=0.0)
    for i, (a, z) in enumerate(((0.4, 0.32), (2.4, 0.5), (4.3, 0.28))):
        blob("shelf", p["fungus"] if i != 1 else p["fungus_cap"], (math.cos(a) * 0.5, math.sin(a) * 0.5, z), 0.2, 0.2, 0.08, sides=7, rings=3)
    blob("moss", p["moss"], (-0.18, 0.2, 0.84), 0.2, 0.18, 0.07, sides=7, rings=3)
    for dx, dy, h in ((0.12, -0.12, 0.28), (0.2, -0.04, 0.2)):
        cyl("stalk", p["fungus"], (dx, dy, 0.84), 0.04, h, sides=5, bevel=0.0)
        blob("cap", p["amber"], (dx, dy, 0.84 + h), 0.09, 0.09, 0.06, sides=6, rings=3)
    for i in range(3):
        a = 1.4 + i * 2.1
        limb("root", p["bark_dk"], [(math.cos(a) * 0.38, math.sin(a) * 0.38, 0.3), (math.cos(a) * 0.62, math.sin(a) * 0.62, 0.1), (math.cos(a) * 0.85, math.sin(a) * 0.85, 0.0)], 0.1, 0.04, sides=5)


def ghost_bramble():
    """Espinheiro (lugar do arbusto): cúpula de varas arqueadas e emaranhadas, espinhos pálidos e frutos de seiva."""
    p = palette()
    cyl("hub", p["bark_dk"], (0, 0, 0), 0.55, 0.3, sides=7, top_radius=0.4, bevel=0.0)
    for k in range(7):
        a = k * math.pi / 7 + 0.2
        rx, h = 0.95 - 0.08 * (k % 3), 0.75 + 0.1 * ((k * 5) % 4) / 3
        pts = []
        for i in range(7):
            t = math.pi * i / 6
            wob = 0.08 * math.sin(t * 3 + k)
            pts.append((math.cos(a) * rx * math.cos(t) - math.sin(a) * wob, math.sin(a) * rx * math.cos(t) + math.cos(a) * wob, 0.1 + h * math.sin(t)))
        limb("vine", p["bark_dk"] if k % 2 else p["bark_vio"], pts, 0.12, 0.1, sides=5)
        for j in (1, 2, 4, 5):
            x, y, z = pts[j]
            kit.spike(p["thorn"], (x, y, z), height=0.3, radius=0.06, lean=(x * 0.35, y * 0.35))
    for x, y, z in ((0.7, 0.3, 0.4), (-0.5, 0.55, 0.55), (0.2, -0.7, 0.35), (-0.75, -0.25, 0.3)):
        blob("berry", p["amber"], (x, y, z), 0.1, 0.1, 0.1, sides=6, rings=3)


def mushroom(p, pos, stalk_h, cap_r, cap_tone="fungus_cap", glow=False):
    x, y, z = pos
    cyl("stalk", p["fungus"], (x, y, z), cap_r * 0.28, stalk_h, sides=6, top_radius=cap_r * 0.2, bevel=0.0)
    blob("cap", p[cap_tone], (x, y, z + stalk_h), cap_r, cap_r, cap_r * 0.5, sides=8, rings=4)
    if glow:
        blob("spot", p["spore"], (x + cap_r * 0.3, y, z + stalk_h + cap_r * 0.42), cap_r * 0.2, cap_r * 0.2, cap_r * 0.12, sides=5, rings=3)


def ghost_mushrooms():
    """Touceira de cogumelos pálidos e altos (lugar do arbusto), com esporos acesos."""
    p = palette()
    cyl("mound", p["bark_dk"], (0, 0, 0), 0.95, 0.14, sides=9, top_radius=0.75, bevel=0.0)
    specs = ((0.0, 0.0, 0.95, 0.4), (0.6, 0.3, 0.6, 0.32), (-0.55, 0.25, 0.7, 0.34), (0.15, -0.55, 0.45, 0.28),
             (-0.6, -0.4, 0.4, 0.24), (0.75, -0.35, 0.34, 0.22))
    for i, (x, y, h, r) in enumerate(specs):
        mushroom(p, (x, y, 0.1), h, r, cap_tone="fungus_cap" if i % 3 else "fungus", glow=(i == 0 or i == 3))


def ghost_boulder():
    """Pedregulho musgoso enrolado em raízes (lugar da pedra): 3,4 de largura, 1,6 de altura."""
    p = palette()
    box("mound", p["stone_dk"], (0, 0, 0), (3.4, 2.8, 0.55), bevel=0.2, taper=0.7, taper_y=0.7)
    blocks = (((-0.5, 0.2, 0.3), (2.0, 1.7, 0.9), 0.4, "stone"), ((0.8, -0.35, 0.3), (1.6, 1.4, 0.7), -0.6, "stone_dk"),
              ((0.1, 0.45, 0.8), (1.3, 1.0, 0.7), 0.9, "stone_lt"))
    for pos, size, rz, tone in blocks:
        box("rock", p[tone], pos, size, bevel=0.08, taper=0.8, taper_y=0.85, rot_z=rz)
    blob("moss", p["moss"], (-0.45, 0.15, 1.15), 0.8, 0.65, 0.18, sides=8, rings=3)
    blob("moss", p["moss_lt"], (0.7, -0.3, 0.98), 0.5, 0.4, 0.12, sides=7, rings=3)
    limb("wrap", p["bark"], [(-1.4, -0.4, 0.1), (-0.8, -0.7, 0.8), (0.2, -0.5, 1.3), (0.9, 0.0, 1.15), (1.4, 0.4, 0.2)], 0.17, 0.1, sides=6)
    limb("wrap", p["bark_vio"], [(-0.5, 1.0, 0.1), (-0.2, 0.5, 0.9), (0.4, 0.3, 1.45), (0.9, 0.5, 0.6)], 0.13, 0.07, sides=6)
    blob("sap", p["amber"], (0.1, -0.52, 1.28), 0.1, 0.1, 0.1, sides=6, rings=3)


def ghost_bones():
    """Pilha de ossos com uma caixa torácica de pé (lugar da pedra): crânio, costelas, ossos longos."""
    p = palette()
    blob("mound", p["bark_dk"], (0, 0, 0), 1.5, 1.2, 0.18, sides=9, rings=3)
    for i in range(5):
        x = -0.8 + i * 0.4
        h = 1.0 - 0.1 * abs(i - 2)
        pts = [(x, -0.2, 0.2), (x, -0.5 * h, 0.25 + 0.6 * h), (x, -0.1, 0.35 + 1.05 * h)]
        limb("rib", p["bone"], pts, 0.08, 0.06, sides=5)
        limb("rib", p["bone"], [(x, 0.2, 0.2), (x, 0.5 * h, 0.25 + 0.6 * h), (x, 0.1, 0.35 + 1.05 * h)], 0.08, 0.06, sides=5)
    limb("spine", p["bone_dk"], [(-1.0, 0.0, 0.3), (0.0, 0.0, 1.45), (1.0, 0.0, 0.3)], 0.1, 0.1, sides=6)
    blob("skull", p["bone"], (1.1, 0.85, 0.52), 0.32, 0.26, 0.26, sides=8, rings=4)
    box("jaw", p["bone_dk"], (1.4, 0.85, 0.3), (0.3, 0.3, 0.12), bevel=0.02)
    for s in (-1, 1):
        box("socket", p["void"], (1.3, 0.85 + s * 0.12, 0.62), (0.1, 0.1, 0.1), bevel=0.0)
    for a, b in (((-1.3, 0.8, 0.28), (-0.4, 1.0, 0.18)), ((-1.2, -0.9, 0.22), (-0.3, -1.1, 0.4)), ((0.4, -1.0, 0.25), (1.3, -0.7, 0.2))):
        beam("longbone", p["bone"], a, b, thick=0.14)
        blob("knob", p["bone"], b, 0.12, 0.12, 0.1, sides=6, rings=3)
    blob("moss", p["moss"], (-1.0, 0.1, 0.34), 0.45, 0.4, 0.08, sides=7, rings=3)


def ghost_idol():
    """Ídolo de pedra tombado (lugar da pedra): cabeça rachada de lado, olhos de resina, raízes e musgo."""
    p = palette()
    blob("mound", p["bark_dk"], (0, 0, 0), 1.7, 1.1, 0.2, sides=9, rings=3)
    box("body", p["stone"], (-0.4, 0, 0.18), (2.7, 1.5, 1.1), bevel=0.08, taper=0.86, taper_y=0.8)
    box("brow", p["stone_lt"], (0.8, 0, 0.9), (0.9, 1.5, 0.35), bevel=0.05, taper=0.9)
    box("crown", p["stone_lt"], (-0.5, 0, 1.22), (2.0, 1.1, 0.16), bevel=0.04)
    box("nose", p["stone_dk"], (1.2, 0, 0.45), (0.45, 0.35, 0.55), bevel=0.04, taper=0.7, taper_y=0.7)
    for s in (-1, 1):
        box("eye", p["resin"], (1.1, s * 0.45, 0.82), (0.2, 0.28, 0.14), bevel=0.0)
    box("mouth", p["void"], (1.28, 0, 0.3), (0.12, 0.7, 0.14), bevel=0.0)
    box("crack", p["void"], (-0.5, 0.2, 1.0), (1.4, 0.07, 0.32), bevel=0.0, rot_z=0.2)
    blob("moss", p["moss"], (-1.0, -0.2, 1.3), 0.7, 0.45, 0.14, sides=7, rings=3)
    limb("root", p["bark"], [(-1.6, 0.7, 0.1), (-0.9, 0.8, 0.9), (0.0, 0.8, 1.35), (0.7, 0.75, 0.3)], 0.15, 0.09, sides=6)
    limb("root", p["bark_vio"], [(-0.4, -1.0, 0.1), (0.2, -0.8, 1.0), (0.9, -0.7, 0.4)], 0.12, 0.07, sides=6)


# ---------------------------------------------------------------------------------------------------------
# Peça central: torneira de resina no toco da lagoa
# ---------------------------------------------------------------------------------------------------------


def bucket(p, pos, radius=0.28, height=0.4):
    x, y, z = pos
    cyl("bucket", p["copper"], (x, y, z), radius, height, sides=9, top_radius=radius * 1.1, bevel=0.0)
    cyl("bucket_fill", p["resin"], (x, y, z + height - 0.03), radius * 0.95, 0.07, sides=9, bevel=0.0)
    ring("bucket_rim", p["copper_dk"], (x, y, z + height - 0.08), radius, 0.09, thick=0.05, sides=9)


def ghost_tap():
    """Torneira de resina num toco colossal: bicas de ferro, baldes de cobre, gotejo verde e películas de resina."""
    p = palette()
    cyl("stump_base", p["bark_dk"], (0, 0, 0), 1.45, 0.4, sides=10, top_radius=1.15, bevel=0.0)
    cyl("stump", p["bark"], (0, 0, 0.36), 1.12, 0.85, sides=10, top_radius=1.0, bevel=0.0)
    cyl("cut", p["bone_dk"], (0, 0, 1.2), 1.0, 0.07, sides=10, bevel=0.0)
    cyl("cut_core", p["amber"], (0, 0, 1.25), 0.55, 0.03, sides=10, bevel=0.0)
    root_flare(p["bark_dk"], (0, 0, 0), 1.2, 6, 0.3, 0.45, seed=0.3, thick=0.2)
    vein(p["resin"], [(0, 0, 0.3), (0, 0, 1.2)], 1.12, 1.0, t0=0.1, t1=0.9, turns=0.9, phase=0.5, thick=0.09)
    # Cuba de cobre sobre três pernas de raiz: coleta a seiva do corte e alimenta as bicas.
    for i in range(3):
        ang = 0.9 + i * math.tau / 3
        limb("leg", p["bark_vio"], [(math.cos(ang) * 0.85, math.sin(ang) * 0.85, 1.2), (math.cos(ang) * 0.55, math.sin(ang) * 0.55, 1.7), (math.cos(ang) * 0.35, math.sin(ang) * 0.35, 2.05)], 0.12, 0.09, sides=5)
    cyl("tank", p["copper"], (0, 0, 1.95), 0.5, 0.55, sides=10, top_radius=0.44, bevel=0.0)
    ring("tank_band", p["copper_dk"], (0, 0, 2.2), 0.46, 0.1, thick=0.04, sides=10)
    cyl("tank_resin", p["resin"], (0, 0, 2.48), 0.38, 0.04, sides=10, bevel=0.0)
    cyl("tank_lid", p["iron"], (0.1, 0.0, 2.52), 0.12, 0.14, sides=6, bevel=0.0)
    # Três bicas de ferro cravadas no toco, cada uma com balde e gota.
    for i, a in enumerate((0.3, 2.5, 4.4)):
        c, s = math.cos(a), math.sin(a)
        beam("spigot", p["iron"], (c * 0.9, s * 0.9, 0.95), (c * 1.35, s * 1.35, 0.78), thick=0.15)
        box("tap_handle", p["copper_dk"], (c * 1.0, s * 1.0, 1.02), (0.3, 0.1, 0.1), bevel=0.0, rot_z=a)
        cyl("drip", p["resin"], (c * 1.36, s * 1.36, 0.45), 0.05, 0.3, sides=5, bevel=0.0)
        bucket(p, (c * 1.36, s * 1.36, 0.0), radius=0.3, height=0.45)
    # Barris coletores e uma escada curta.
    cyl("barrel", p["wood"], (-0.6, 1.45, 0.0), 0.3, 0.5, sides=9, bevel=0.0)
    ring("barrel_hoop", p["iron"], (-0.6, 1.45, 0.25), 0.3, 0.07, sides=9)
    for a in (-0.28, 0.28):
        beam("ladder", p["wood_dk"], (-1.05 + a, -0.95, 0.0), (-0.8 + a, -0.7, 1.1), thick=0.08)
    # Películas de resina na lagoa: discos chatos e rente à água (até ~0,06), em anéis de tons de folha.
    tones = (p["pad"], p["pad_dk"], p["pad_pale"])
    pads = ((-4.6, 3.4, 1.9, 0.3), (3.9, 4.6, 1.5, 1.1), (5.0, -2.4, 2.1, 2.0), (-3.2, -4.8, 1.6, 0.7), (1.2, -5.8, 1.1, 2.6),
            (-5.8, -0.6, 1.2, 0.2), (2.4, 1.8, 0.9, 1.4))
    for i, (x, y, r, turn) in enumerate(pads):
        cyl("pad", tones[i % 3], (x, y, 0.058), r, 0.006, sides=9, bevel=0.0, rot=("Z", turn))
        cyl("pad_notch", tones[(i + 1) % 3], (x + r * 0.35, y - r * 0.25, 0.064), r * 0.45, 0.004, sides=7, bevel=0.0, rot=("Z", turn + 1))
    for x, y, r in ((-2.4, 2.0, 0.4), (3.0, -1.2, 0.35), (-1.2, -3.0, 0.3), (0.8, 3.6, 0.3)):
        blob("bubble", p["spore"], (x, y, 0.06), r * 0.3, r * 0.3, 0.02, sides=6, rings=3)


# ---------------------------------------------------------------------------------------------------------
# Decoração fora do andável (5 kinds)
# ---------------------------------------------------------------------------------------------------------


def ghost_husk():
    """kind 0: casca de um ancião morto, gigante de árvore de pé: pernas de raiz, tronco oco, braço erguido, olhos de resina."""
    p = palette()
    box("pad", p["bark_dk"], (0, 0, 0), (3.6, 3.0, 0.3), bevel=0.15, taper=0.7, taper_y=0.7)
    for s in (-1, 1):
        limb("leg", p["dead"], [(0.1, s * 0.7, 0.25), (-0.2, s * 0.9, 1.6), (0.1, s * 0.6, 3.0)], 0.5, 0.42, sides=7)
        box("foot", p["dead_lt"], (0.3, s * 0.9, 0.15), (1.2, 0.8, 0.3), bevel=0.05, taper=0.8, taper_y=0.8)
        limb("toe", p["dead"], [(0.8, s * 0.9, 0.25), (1.5, s * 1.1, 0.12)], 0.2, 0.08, sides=5)
    cyl("torso", p["dead_lt"], (0, 0, 2.9), 1.15, 3.0, sides=9, top_radius=0.95, bevel=0.0)
    cyl("hollow", p["void"], (0.75, 0, 3.6), 0.4, 1.7, sides=7, top_radius=0.35, bevel=0.0)
    for z in (3.3, 4.6):
        ring("rib", p["bark_vio"], (0, 0, z), 1.0, 0.2, thick=0.1, sides=9)
    vein(p["resin_dk"], [(0, 0, 3.0), (0, 0, 5.8)], 1.15, 0.95, t0=0.0, t1=1.0, turns=1.2, phase=1.0, steps=9, thick=0.12)
    # Braço erguido e braço caído.
    limb("arm", p["dead"], [(0.1, 1.0, 5.4), (0.4, 1.9, 6.4), (0.0, 2.4, 7.6)], 0.38, 0.2, sides=6)
    for dx, dy in ((0.35, 0.2), (-0.1, 0.3), (-0.4, 0.05)):
        limb("finger", p["dead_lt"], [(0.0, 2.4, 7.5), (dx, 2.4 + dy, 8.1), (dx * 1.5, 2.5 + dy, 8.5)], 0.12, 0.04, sides=5)
    limb("arm", p["dead"], [(0.0, -1.0, 5.3), (0.4, -1.6, 4.3), (0.9, -1.9, 3.1)], 0.34, 0.2, sides=6)
    # Cabeça com chifres de galho e olhos de resina.
    blob("head", p["dead_lt"], (0.3, 0.0, 6.35), 0.8, 0.75, 0.8, sides=8, rings=5)
    for s in (-1, 1):
        box("eye", p["resin"], (1.0, s * 0.32, 6.45), (0.2, 0.26, 0.2), bevel=0.0)
        limb("antler", p["dead"], [(0.3, s * 0.5, 6.9), (0.2, s * 1.0, 7.5), (0.4, s * 1.3, 8.4)], 0.16, 0.06, sides=5)
        limb("antler", p["dead_lt"], [(0.2, s * 0.9, 7.4), (0.0, s * 1.5, 7.9)], 0.08, 0.04, sides=5)
    box("mouth", p["void"], (1.0, 0, 6.05), (0.12, 0.5, 0.14), bevel=0.0)
    root_flare(p["bark_dk"], (0, 0, 0), 1.2, 6, 0.55, 0.5, seed=0.5, thick=0.2)


def ghost_vat():
    """kind 1: tina de resina do Blackroot Contract rodeada de barris e caixotes (volume redondo e baixo, ~3,5 x 3)."""
    p = palette()
    cyl("deck", p["wood_dk"], (0, 0, 0), 1.75, 0.2, sides=14, bevel=0.0)
    cyl("vat", p["wood"], (0, 0, 0.18), 1.35, 1.82, sides=14, top_radius=1.25, bevel=0.0)
    for z in (0.55, 1.2, 1.75):
        ring("hoop", p["iron"], (0, 0, z), 1.3 - 0.04 * (z - 0.55), 0.12, thick=0.05, sides=14)
    cyl("surface", p["resin"], (0, 0, 2.0), 1.14, 0.07, sides=14, bevel=0.0)
    for r, a in ((0.5, 0.4), (0.4, 2.2), (0.3, 4.1)):
        blob("bubble", p["spore"], (math.cos(a) * r, math.sin(a) * r, 2.08), 0.14, 0.14, 0.08, sides=6, rings=3)
    # Calha de bica cobre e um balde.
    beam("spout", p["copper"], (1.3, 0, 1.0), (1.8, 0, 0.75), thick=0.2)
    bucket(p, (1.9, 0.0, 0.0), radius=0.34, height=0.5)
    cyl("drip", p["resin"], (1.82, 0, 0.5), 0.05, 0.28, sides=5, bevel=0.0)
    # Barris e caixotes com fita âmbar: a marca do contrato.
    for i, (x, y, tone) in enumerate(((-1.5, 0.9, "wood"), (-1.55, -0.1, "wood_dk"), (-1.2, -1.1, "wood"), (0.4, 1.7, "wood_dk"), (1.1, -1.5, "wood"))):
        cyl("barrel", p[tone], (x, y, 0.0), 0.34, 0.62, sides=9, bevel=0.0)
        ring("barrel_band", p["amber"] if i % 2 == 0 else p["iron"], (x, y, 0.32), 0.34, 0.08, sides=9)
    box("crate", p["wood"], (-0.6, -1.6, 0.0), (0.7, 0.6, 0.55), bevel=0.03, rot_z=0.3)
    box("crate_band", p["amber"], (-0.6, -1.6, 0.25), (0.72, 0.62, 0.08), bevel=0.0, rot_z=0.3)
    # Escada de mão encostada.
    for a in (-0.25, 0.25):
        beam("ladder", p["wood_dk"], (0.9 + a, 1.1, 0.0), (0.5 + a, 0.7, 2.2), thick=0.1)


def ghost_vent():
    """kind 2: tocha de resina (~1 de base, 6,4 de altura): poste de ferro numa garra de raiz, tigela e chama de esporos."""
    p = palette()
    cyl("foot", p["bark_dk"], (0, 0, 0), 0.62, 0.3, sides=8, top_radius=0.45, bevel=0.0)
    root_flare(p["bark_dk"], (0, 0, 0), 0.45, 4, 0.15, 0.35, seed=0.6, thick=0.12)
    cyl("pole", p["iron"], (0, 0, 0.25), 0.2, 4.7, sides=7, top_radius=0.16, bevel=0.0)
    for z in (1.2, 2.6):
        ring("pole_band", p["copper"], (0, 0, z), 0.17, 0.14, thick=0.05, sides=7)
    for i in range(4):
        a = i * math.tau / 4 + 0.4
        limb("claw", p["bark"], [(math.cos(a) * 0.1, math.sin(a) * 0.1, 4.7), (math.cos(a) * 0.55, math.sin(a) * 0.55, 5.0), (math.cos(a) * 0.62, math.sin(a) * 0.62, 5.6)], 0.12, 0.05, sides=5)
    cyl("bowl", p["iron"], (0, 0, 4.85), 0.25, 0.3, sides=8, top_radius=0.5, bevel=0.0)
    cyl("resin_pool", p["resin"], (0, 0, 5.14), 0.45, 0.05, sides=8, bevel=0.0)
    cyl("flame", p["resin"], (0, 0, 5.15), 0.38, 1.1, sides=6, top_radius=0.0, bevel=0.0)
    cyl("flame_side", p["resin_dk"], (0.25, -0.1, 5.15), 0.2, 0.7, sides=5, top_radius=0.0, bevel=0.0)
    cyl("flame_core", p["spore"], (0, 0, 5.2), 0.2, 0.8, sides=5, top_radius=0.0, bevel=0.0)
    for i in range(4):
        a = i * 1.7
        blob("ember", p["spore"], (math.cos(a) * 0.4, math.sin(a) * 0.4, 6.4 + 0.2 * (i % 2)), 0.08, 0.08, 0.08, sides=5, rings=3)


def ghost_fallen():
    """kind 3: tronco colossal caído (8 ao longo de x), prato de raízes numa ponta, cogumelos e musgo no dorso."""
    p = palette()
    r = 0.95
    cyl("log", p["bark_vio"], (-4.0, 0, r), r, 8.0, sides=10, top_radius=r * 0.8, bevel=0.0, rot=("Y", math.radians(90)))
    cyl("log_base", p["bark_dk"], (-4.0, 0, r), r * 1.02, 2.2, sides=10, top_radius=r * 1.0, bevel=0.0, rot=("Y", math.radians(90)))
    cyl("heart", p["bone_dk"], (3.98, 0, r), r * 0.78, 0.05, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
    cyl("heart_core", p["amber"], (4.0, 0, r), r * 0.35, 0.03, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
    for k, a in enumerate((0.0, 1.1, 2.2, 3.4, 4.6, 5.5)):
        c, s = math.cos(a), math.sin(a)
        limb("rootplate", p["bark_dk"], [(-3.9, c * 0.3, r + s * 0.3), (-4.5, c * 1.2, r + s * 1.3), (-4.4, c * 1.7, max(0.0, r + s * 1.0 - 1.1))], 0.3, 0.1, sides=5)
    for x, tone in ((-1.2, "moss"), (1.4, "moss_lt"), (2.6, "moss")):
        blob("moss", p[tone], (x, 0.1, 1.8), 0.8, 0.55, 0.14, sides=7, rings=3)
    for x, y in ((-2.0, 0.4), (0.3, -0.35), (2.0, 0.3)):
        mushroom(p, (x, y, 1.78), 0.4, 0.26, glow=(x > 0))
    for x, s in ((-0.8, 1), (1.0, -1), (2.6, 1)):
        limb("branch", p["bark"], [(x, s * 0.7, 1.4), (x + 0.2, s * 1.4, 1.9), (x + 0.3, s * 1.9, 2.5)], 0.17, 0.06, sides=5)


def ghost_watch():
    """kind 4: torre fina de vigia numa árvore morta: plataforma de tábuas, corrimão, casulos e lanterna pendurados (~7 de altura)."""
    p = palette()
    pts = [(0, 0, 0), (0.12, 0.05, 2.2), (-0.1, 0.0, 4.4), (0.05, -0.05, 6.2)]
    limb("trunk", p["dead"], pts, 0.42, 0.18, sides=7)
    root_flare(p["bark_dk"], (0, 0, 0), 0.35, 5, 0.5, 0.5, seed=0.4, thick=0.17)
    for i in range(3):
        a = i * 2.1
        limb("brace", p["bark"], [(math.cos(a) * 1.0, math.sin(a) * 1.0, 3.7), (math.cos(a) * 0.55, math.sin(a) * 0.55, 4.3), (math.cos(a) * 0.2, math.sin(a) * 0.2, 4.6)], 0.09, 0.07, sides=5)
    cyl("deck", p["wood"], (0, 0, 4.5), 1.25, 0.14, sides=10, bevel=0.0)
    ring("deck_rim", p["wood_dk"], (0, 0, 4.5), 1.2, 0.18, thick=0.07, sides=10)
    for i in range(10):
        a = i * math.tau / 10
        beam("post", p["wood_dk"], (math.cos(a) * 1.15, math.sin(a) * 1.15, 4.6), (math.cos(a) * 1.15, math.sin(a) * 1.15, 5.3), thick=0.07)
    for i in range(10):
        a, b = i * math.tau / 10, (i + 1) * math.tau / 10
        beam("rail", p["wood_dk"], (math.cos(a) * 1.15, math.sin(a) * 1.15, 5.3), (math.cos(b) * 1.15, math.sin(b) * 1.15, 5.3), thick=0.07)
    limb("top", p["dead_lt"], [(0.05, -0.05, 6.1), (0.2, 0.1, 6.7), (0.0, 0.2, 7.3)], 0.14, 0.05, sides=5)
    limb("top", p["dead_lt"], [(0.05, -0.05, 6.1), (-0.5, -0.1, 6.6), (-0.8, 0.0, 7.1)], 0.1, 0.04, sides=5)
    for a, length in ((0.3, 0.9), (1.7, 0.7), (3.0, 1.0), (4.4, 0.7), (5.3, 0.85)):
        cocoon(p, (math.cos(a) * 1.0, math.sin(a) * 1.0, 4.4), length=length, radius=0.24, cord=0.12)
    lantern(p, (0.0, 1.15, 5.3), size=0.3, cord=0.0)
    beam("lamp_arm", p["wood_dk"], (0.0, 1.15, 5.3), (0.0, 1.15, 5.7), thick=0.06)
    for x, y in ((1.2, 0.2), (-1.2, -0.3)):
        blob("pod", p["spore"], (x, y, 4.66), 0.1, 0.1, 0.08, sides=5, rings=3)


# ---------------------------------------------------------------------------------------------------------
# Peças da extensão (floresta fora do jogável): o scatter do jogo escala cada peça por tabelas pensadas para
# modelos do Clássico, então estas seguem os tamanhos que essas tabelas esperam
# ---------------------------------------------------------------------------------------------------------


def ghost_snag():
    """Toco-seco alto de 2,3 (lugar do pinheiro e do pinheiro morto): tronco torto com veia de seiva e garras."""
    p = palette()
    pts = [Vector((0, 0, 0)), Vector((0.08, 0.02, 0.8)), Vector((-0.06, 0.05, 1.5)), Vector((0.05, -0.02, 2.3))]
    for i, (a, b) in enumerate(itertools.pairwise(pts)):
        limb("trunk", p["dead_lt"] if i % 2 else p["bark_vio"], [a, b], 0.34 - 0.08 * i, 0.34 - 0.08 * (i + 1), sides=6)
    root_flare(p["bark_dk"], (0, 0, 0), 0.28, 4, 0.3, 0.4, seed=0.5, thick=0.15)
    vein(p["amber"], pts, 0.34, 0.1, t0=0.1, t1=0.8, turns=0.6, phase=1.0, thick=0.08)
    for a, d in ((0.5, (1, 0.3, 0.7)), (0.8, (-1, 0.2, 0.9)), (0.95, (0.2, 1, 1.0))):
        c = along(pts, a)
        dv = Vector(d).normalized()
        limb("claw", p["dead"], [c, c + dv * 0.4, c + dv * 0.7 + Vector((0, 0, 0.2))], 0.12, 0.04, sides=5)


def ghost_crag():
    """Penhasco de rocha cinza-fungo de ~7,8 de largura (lugar da pedra grande da extensão): blocos, musgo, raízes e cogumelos."""
    p = palette()
    blob("mound", p["stone_dk"], (0, 0, 0), 3.9, 3.0, 0.5, sides=10, rings=3)
    blocks = (((-1.4, 0.3, 0.2), (3.8, 3.0, 1.8), 0.4, "stone"), ((1.8, -0.6, 0.2), (3.2, 2.6, 1.3), -0.6, "stone_dk"),
              ((0.2, 0.9, 1.2), (2.6, 2.0, 1.4), 0.9, "stone_lt"), ((-2.2, -1.4, 0.2), (2.0, 1.8, 1.0), 1.2, "stone_dk"))
    for pos, size, rz, tone in blocks:
        box("rock", p[tone], pos, size, bevel=0.12, taper=0.78, taper_y=0.84, rot_z=rz)
    blob("moss", p["moss"], (-1.1, 0.4, 1.95), 1.4, 1.1, 0.25, sides=8, rings=3)
    blob("moss", p["moss_lt"], (1.4, -0.6, 1.5), 1.0, 0.8, 0.2, sides=8, rings=3)
    limb("wrap", p["bark"], [(-3.2, -0.8, 0.1), (-1.8, -1.4, 1.5), (0.4, -1.0, 2.3), (2.0, 0.2, 1.8), (3.0, 1.0, 0.2)], 0.3, 0.16, sides=6)
    limb("wrap", p["bark_vio"], [(-1.0, 2.0, 0.1), (-0.4, 1.0, 1.5), (0.8, 0.8, 2.5), (1.8, 1.2, 1.0)], 0.24, 0.12, sides=6)
    for x, y, z, h, r in ((2.4, 1.4, 0.2, 0.7, 0.3), (2.9, 1.0, 0.2, 0.5, 0.24), (-2.6, 1.2, 0.2, 0.6, 0.26)):
        mushroom(p, (x, y, z), h, r, glow=(x > 2.5))


def ghost_spire():
    """Pedra-em-pé de ~1 de base (lugar do afloramento alto; o jogo escala 2,6 a 4,6x): lasca de pedra com raiz e veia de seiva."""
    p = palette()
    box("base", p["stone_dk"], (0, 0, 0), (1.1, 1.0, 0.3), bevel=0.05, taper=0.8, taper_y=0.8)
    box("shaft", p["stone"], (0, 0, 0.25), (0.8, 0.7, 0.7), bevel=0.04, taper=0.6, taper_y=0.55, rot_z=0.3)
    box("tip", p["stone_lt"], (0.05, 0, 0.9), (0.45, 0.4, 0.4), bevel=0.03, taper=0.3, taper_y=0.3, rot_z=0.3)
    box("side", p["stone_dk"], (0.3, -0.25, 0.1), (0.5, 0.4, 0.55), bevel=0.04, taper=0.5, taper_y=0.5, rot_z=-0.4)
    limb("wrap", p["bark"], [(-0.5, 0.2, 0.05), (-0.25, 0.3, 0.4), (0.1, 0.3, 0.65), (0.3, 0.1, 0.3)], 0.08, 0.05, sides=5)
    blob("moss", p["moss"], (-0.1, 0.1, 0.32), 0.3, 0.25, 0.08, sides=6, rings=3)
    box("crack", p["amber"], (0.18, -0.12, 0.4), (0.06, 0.06, 0.4), bevel=0.0, rot_z=0.3)


def fallen_log(length, radius, tone="bark_vio", mushrooms=2):
    p = palette()
    cyl("log", p[tone], (-length / 2, 0, radius), radius, length, sides=8, top_radius=radius * 0.85, bevel=0.0, rot=("Y", math.radians(90)))
    cyl("heart", p["bone_dk"], (length / 2 - 0.02, 0, radius), radius * 0.72, 0.05, sides=8, bevel=0.0, rot=("Y", math.radians(90)))
    cyl("heart_core", p["amber"], (length / 2, 0, radius), radius * 0.3, 0.03, sides=8, bevel=0.0, rot=("Y", math.radians(90)))
    for i, a in enumerate((0.3, 2.0, 4.0)):
        c, s = math.cos(a), math.sin(a)
        limb("rootplate", p["bark_dk"], [(-length / 2 + 0.1, c * 0.2, radius + s * 0.2), (-length / 2 - 0.3, c * 0.6, radius + s * 0.7), (-length / 2 - 0.3, c * 0.9, max(0.0, radius + s * 0.5 - 0.6))], 0.14, 0.06, sides=5)
    blob("moss", p["moss"], (-length * 0.15, 0.05, radius * 1.85), radius * 1.0, radius * 0.7, radius * 0.22, sides=7, rings=3)
    for i in range(mushrooms):
        mushroom(p, (length * (0.05 + 0.25 * i), 0.1 - 0.15 * i, radius * 1.8), 0.28, 0.2, glow=(i == 0))
    limb("stub", p["bark"], [(length * 0.3, radius * 0.6, radius * 1.2), (length * 0.32, radius * 1.3, radius * 1.8)], 0.1, 0.05, sides=5)


def ghost_log():
    fallen_log(3.1, 0.42)


def ghost_log_b():
    fallen_log(2.6, 0.36, tone="bark", mushrooms=3)


# ---------------------------------------------------------------------------------------------------------
# Bichos (modelados virados para +x; o manifesto corrige com yaw_deg)
# ---------------------------------------------------------------------------------------------------------


def ghost_hare():
    """Lebre-fungo: corpo curto pálido, orelhas longas, pernas traseiras fortes, rabo de esporo âmbar."""
    p = palette()
    blob("body", p["stone_lt"], (0, 0, 0.45), 0.6, 0.36, 0.38, sides=8, rings=4)
    blob("head", p["stone_lt"], (0.62, 0, 0.66), 0.26, 0.2, 0.22, sides=7, rings=4)
    for s in (-1, 1):
        limb("ear", p["fungus_cap"], [(0.55, s * 0.12, 0.8), (0.4, s * 0.22, 1.2), (0.3, s * 0.26, 1.5)], 0.08, 0.05, sides=5)
        box("hind", p["stone"], (-0.25, s * 0.33, 0.0), (0.6, 0.18, 0.4), bevel=0.0)
        box("fore", p["stone"], (0.45, s * 0.14, 0.0), (0.16, 0.12, 0.4), bevel=0.0)
        box("eye", p["amber"], (0.78, s * 0.16, 0.74), (0.07, 0.07, 0.07), bevel=0.0)
    blob("tail", p["spore"], (-0.65, 0, 0.55), 0.14, 0.14, 0.14, sides=5, rings=3)
    blob("cap", p["fungus"], (-0.05, 0.0, 0.78), 0.14, 0.14, 0.08, sides=5, rings=3)


def ghost_beetle():
    """Besouro-resina: carapaça abaulada verde-negra, chifre, pernas e brilho âmbar nos élitros."""
    p = palette()
    blob("shell", p["dead_lt"], (0, 0, 0.3), 0.55, 0.38, 0.3, sides=9, rings=4)
    blob("shell_hi", p["pad_dk"], (-0.05, 0, 0.42), 0.4, 0.28, 0.2, sides=8, rings=3)
    box("stripe", p["amber"], (-0.05, 0, 0.5), (0.5, 0.1, 0.05), bevel=0.0)
    blob("head", p["dead"], (0.62, 0, 0.26), 0.2, 0.2, 0.17, sides=7, rings=3)
    kit.spike(p["bone_dk"], (0.74, 0, 0.3), height=0.35, radius=0.08, lean=(0.2, 0.0))
    for i, x in enumerate((0.3, 0.0, -0.3)):
        for s in (-1, 1):
            beam("leg", p["dead"], (x, s * 0.3, 0.2), (x + 0.1 * (i - 1), s * 0.62, 0.0), thick=0.07)


def ghost_toad():
    """Sapo-venenoso: gordo, verde-tóxico com verrugas âmbar e olhos saltados."""
    p = palette()
    blob("body", p["pad_dk"], (0, 0, 0.3), 0.5, 0.45, 0.3, sides=9, rings=4)
    blob("belly", p["pad_pale"], (0.05, 0, 0.12), 0.38, 0.34, 0.14, sides=8, rings=3)
    blob("head", p["pad"], (0.42, 0, 0.42), 0.26, 0.3, 0.2, sides=8, rings=4)
    for s in (-1, 1):
        blob("eye", p["amber"], (0.5, s * 0.17, 0.62), 0.09, 0.09, 0.09, sides=6, rings=3)
        box("hind", p["pad_dk"], (-0.28, s * 0.42, 0.0), (0.5, 0.16, 0.22), bevel=0.0)
        box("fore", p["pad_dk"], (0.35, s * 0.34, 0.0), (0.18, 0.12, 0.2), bevel=0.0)
    for x, y in ((-0.1, 0.2), (-0.2, -0.15), (0.1, -0.25), (0.05, 0.28)):
        blob("wart", p["resin"], (x, y, 0.55), 0.07, 0.07, 0.06, sides=5, rings=3)


def ghost_possum():
    """Gambá pálido: corpo comprido, focinho rosado, orelhas redondas e rabo nu enrolado."""
    p = palette()
    blob("body", p["bone_dk"], (0, 0, 0.3), 0.55, 0.3, 0.26, sides=8, rings=4)
    blob("head", p["cloth"], (0.55, 0, 0.32), 0.24, 0.17, 0.17, sides=7, rings=3)
    kit.spike(p["cloth_dk"], (0.7, 0, 0.3), height=0.3, radius=0.09, lean=(0.28, 0.0))
    blob("nose", p["fungus_cap"], (0.95, 0, 0.28), 0.07, 0.07, 0.07, sides=5, rings=3)
    for s in (-1, 1):
        blob("ear", p["fungus_dk"], (0.42, s * 0.14, 0.52), 0.1, 0.05, 0.1, sides=5, rings=3)
        box("leg_f", p["bone_dk"], (0.28, s * 0.2, 0.0), (0.12, 0.1, 0.22), bevel=0.0)
        box("leg_b", p["bone_dk"], (-0.28, s * 0.2, 0.0), (0.12, 0.1, 0.22), bevel=0.0)
    limb("tail", p["fungus_cap"], [(-0.5, 0, 0.35), (-0.9, 0, 0.3), (-1.2, 0.0, 0.5), (-1.1, 0.1, 0.75)], 0.07, 0.04, sides=5)


def ghost_moth():
    """Mariposa de brilho (voa): asas largas violeta-pálidas abertas com manchas de esporo, corpo felpudo e antenas."""
    p = palette()
    blob("body", p["cloth_dk"], (0, 0, 0.1), 0.34, 0.1, 0.1, sides=7, rings=3)
    blob("head", p["bone_dk"], (0.36, 0, 0.12), 0.1, 0.1, 0.1, sides=6, rings=3)
    for s in (-1, 1):
        box("wing", p["fungus_cap"], (0.0, s * 0.45, 0.1), (0.5, 0.75, 0.04), bevel=0.0, taper=0.7, rot_z=0.0)
        box("wing_back", p["fungus_dk"], (-0.15, s * 0.4, 0.07), (0.38, 0.55, 0.035), bevel=0.0, taper=0.6)
        blob("eyespot", p["spore"], (0.02, s * 0.62, 0.15), 0.11, 0.11, 0.03, sides=6, rings=3)
        beam("antenna", p["bone_dk"], (0.42, s * 0.05, 0.18), (0.62, s * 0.2, 0.32), thick=0.04)


def ghost_bat():
    """Morcego (voa): asas de membrana angulosas abertas, corpo pequeno escuro, orelhas pontudas."""
    p = palette()
    blob("body", p["dead_lt"], (0, 0, 0.1), 0.3, 0.14, 0.13, sides=7, rings=3)
    blob("head", p["dead"], (0.3, 0, 0.14), 0.13, 0.12, 0.12, sides=6, rings=3)
    for s in (-1, 1):
        kit.spike(p["dead"], (0.3, s * 0.07, 0.2), height=0.15, radius=0.04)
        limb("arm", p["dead"], [(0.05, s * 0.1, 0.12), (0.0, s * 0.4, 0.2), (-0.1, s * 0.85, 0.12)], 0.05, 0.03, sides=4)
        box("membrane", p["bark_vio"], (-0.12, s * 0.45, 0.1), (0.4, 0.8, 0.03), bevel=0.0, taper=0.4)
        blob("eye", p["resin"], (0.4, s * 0.06, 0.17), 0.04, 0.04, 0.04, sides=4, rings=2)


# ---------------------------------------------------------------------------------------------------------
# Castelo A (oeste): Raiz-Refinaria da Nature, fortaleza crescida
# ---------------------------------------------------------------------------------------------------------


def wall_pt(along_x, fixed, u, v, z):
    """Ponto (u ao longo da muralha, v para fora/dentro) no referencial do castelo."""
    return (u, fixed + v, z) if along_x else (fixed + v, u, z)


def root_wall(p, a, b, fixed, along_x, height=1.2, thick=0.72, out=1.0, deck="moss_lt", spikes=3):
    """Cortina de raízes colossais: núcleo de casca em talude e duas raízes trançadas na face de fora, convés de musgo claro."""
    length = abs(b - a)
    mid = (a + b) / 2
    c = (mid, fixed, 0.0) if along_x else (fixed, mid, 0.0)
    dims = (length, thick, height) if along_x else (thick, length, height)
    tp = (1.0, 0.76) if along_x else (0.76, 1.0)
    box("wall", p["bark_vio"], c, dims, bevel=0.03, taper=tp[0], taper_y=tp[1])
    foot = (length, thick * 1.2, 0.16) if along_x else (thick * 1.2, length, 0.16)
    box("wall_foot", p["bark_dk"], c, foot, bevel=0.03)
    deck_dims = (length, thick * 0.66, 0.08) if along_x else (thick * 0.66, length, 0.08)
    box("wall_deck", p[deck], (c[0], c[1], height), deck_dims, bevel=0.015)
    for k, ph in enumerate((0.0, math.pi)):
        pts = []
        for i in range(8):
            u = a + 0.1 + (length - 0.2) * i / 7
            w = i * 1.25 + ph
            pts.append(wall_pt(along_x, fixed, u, out * (thick * 0.42 + 0.04 * math.cos(w)), 0.28 + 0.4 * k + 0.2 * math.sin(w)))
        limb("weave", p["bark"] if k == 0 else p["bark_lt"], pts, 0.14, 0.13, sides=6)
    for i in range(spikes):
        u = a + length * (i + 0.5) / spikes
        x, y, z = wall_pt(along_x, fixed, u, 0.0, height + 0.06)
        kit.spike(p["thorn"], (x, y, z), height=0.34, radius=0.07, lean=(0.0, 0.0))


def stump_bastion(p, pos, radius, height, roof=False, amber_dir=None):
    """Bastião-toco: tronco largo de raízes expostas, cinta, topo de musgo claro (ou telhado de ripas) e fresta de seiva."""
    x, y = pos
    cyl("bastion_foot", p["bark_dk"], (x, y, 0), radius * 1.18, 0.2, sides=8)
    cyl("bastion", p["bark"], (x, y, 0.16), radius * 1.06, height, sides=8, top_radius=radius * 0.9, bevel=0.03)
    ring("bastion_band", p["bark_vio"], (x, y, 0.16 + height * 0.55), radius * 0.98, 0.14, thick=0.05, sides=8)
    root_flare(p["bark_dk"], (x, y, 0), radius, 5, 0.3, 0.55, seed=x + y, thick=0.15)
    top = 0.16 + height
    if roof:
        cyl("roof_eave", p["shingle"], (x, y, top), radius * 1.08, 0.1, sides=8, bevel=0.0)
        cyl("roof", p["shingle"], (x, y, top + 0.08), radius * 1.0, 0.5, sides=8, top_radius=0.0, bevel=0.0)
        cyl("roof_cap", p["moss_lt"], (x, y, top + 0.5), radius * 0.12, 0.12, sides=6, bevel=0.0)
    else:
        cyl("bastion_cap", p["moss_lt"], (x, y, top), radius * 0.94, 0.1, sides=8, bevel=0.0)
        thorn_ring(p["thorn"], (x, y, top + 0.05), radius * 0.7, 6, height=0.3, spike_radius=0.07, tilt=0.14)
    if amber_dir is not None:
        ang = math.atan2(amber_dir[1], amber_dir[0])
        wx, wy = x + math.cos(ang) * radius * 0.97, y + math.sin(ang) * radius * 0.97
        box("sap_slit", p["amber"], (wx, wy, 0.16 + height * 0.3), (0.12, 0.12, 0.45), bevel=0.0, rot_z=ang)


def still(p, pos, radius=0.3, height=0.5):
    """Alambique de cobre grafitado: caldeira, cúpula e pescoço."""
    x, y = pos
    cyl("still_foot", p["bark_dk"], (x, y, 0.1), radius * 1.15, 0.12, sides=9)
    cyl("still_pot", p["copper"], (x, y, 0.2), radius, height, sides=9, top_radius=radius * 0.9, bevel=0.0)
    ring("still_band", p["copper_dk"], (x, y, 0.2 + height * 0.5), radius * 0.95, 0.07, sides=9)
    dome("still_dome", p["copper"], (x, y, 0.2 + height), radius * 0.85, squash=0.8, sides=9)
    cyl("still_neck", p["copper_dk"], (x, y, 0.2 + height + 0.2), 0.07, 0.35, sides=6, bevel=0.0)


def root_refinery():
    """Nature, Root-Refinery: fortaleza crescida (raízes colossais, tocos bastiões, tronco oco com alambiques e copa viva)."""
    p = palette()
    half = 2.7
    box("plinth", p["bark_dk"], (0, 0, 0), (half * 2 + 0.4, half * 2 + 0.3, 0.16), bevel=0.06, taper=0.94, taper_y=0.94)
    box("yard", p["moss"], (0, 0, 0.14), (half * 2 - 0.5, half * 2 - 0.5, 0.08), bevel=0.03)
    for x, y, rx, ry in ((0.9, -0.2, 1.0, 0.7), (-1.5, 1.2, 0.8, 0.6), (1.5, 1.4, 0.6, 0.5)):
        blob("yard_moss", p["moss_lt"], (x, y, 0.19), rx, ry, 0.04, sides=8, rings=3)

    w = half - 0.55
    root_wall(p, -w + 0.2, w - 0.2, w, True, spikes=4)
    root_wall(p, -w + 0.2, w - 0.2, -w, True, spikes=4)
    root_wall(p, -w + 0.2, w - 0.2, -w, False, height=1.3)
    root_wall(p, 0.85, w - 0.2, w, False, height=1.15, spikes=2)
    root_wall(p, -w + 0.2, -0.85, w, False, height=1.15, spikes=2)
    # Contrafortes de raiz para fora da muralha (sul e fundo).
    for t in (-1.2, 0.2, 1.3):
        limb("buttress", p["bark_dk"], [(t, -w - 0.35, 0.0), (t, -w - 0.15, 0.6), (t, -w + 0.1, 1.2)], 0.17, 0.11, sides=5)
    for t in (-1.0, 1.0):
        limb("buttress", p["bark_dk"], [(-w - 0.35, t, 0.0), (-w - 0.15, t, 0.6), (-w + 0.1, t, 1.2)], 0.17, 0.11, sides=5)

    # Bastiões-toco: dois grandes na frente, um alto atrás, um baixo de telhado de ripas e um saliente no sul.
    stump_bastion(p, (w + 0.1, w), 1.0, 1.55, amber_dir=(1, 0.3))
    stump_bastion(p, (w + 0.1, -w), 0.9, 1.25, amber_dir=(1, -0.3))
    stump_bastion(p, (-w, w), 0.85, 2.0, roof=True, amber_dir=(-0.3, 1))
    stump_bastion(p, (-w, -w), 0.8, 1.15, roof=True, amber_dir=(-1, -0.3))
    stump_bastion(p, (0.3, -w - 0.2), 0.5, 0.85, amber_dir=(0, -1))

    # Portaria: dois toquinhos-pilar, arco de raiz viva, lanterna e portão de seiva.
    gx = w + 0.55
    box("gate_block", p["bark"], (gx - 0.25, 0, 0.1), (0.9, 1.5, 1.1), bevel=0.04, taper=0.9, taper_y=0.92)
    box("gate_deck", p["moss_lt"], (gx - 0.25, 0, 1.2), (0.9, 1.5, 0.08), bevel=0.0)
    box("gate_door", p["bark_dk"], (gx + 0.2, 0, 0.12), (0.1, 0.8, 0.85), bevel=0.0)
    box("gate_glow", p["amber"], (gx + 0.25, 0, 0.9), (0.06, 0.55, 0.12), bevel=0.0)
    for s in (-1, 1):
        cyl("gate_post", p["bark"], (gx + 0.1, s * 0.62, 0.1), 0.34, 1.5, sides=7, top_radius=0.28, bevel=0.02)
        cyl("gate_post_cap", p["moss_lt"], (gx + 0.1, s * 0.62, 1.6), 0.3, 0.08, sides=7, bevel=0.0)
        kit.spike(p["thorn"], (gx + 0.1, s * 0.62, 1.66), height=0.4, radius=0.08, lean=(0.08, s * 0.05))
        root_flare(p["bark_dk"], (gx + 0.1, s * 0.62, 0), 0.34, 4, 0.22, 0.4, seed=s, thick=0.12)
    limb("gate_arch", p["bark_lt"], [(gx + 0.1, -0.62, 1.45), (gx + 0.22, -0.3, 1.85), (gx + 0.22, 0.3, 1.9), (gx + 0.1, 0.62, 1.5)], 0.14, 0.12, sides=6)
    lantern(p, (gx + 0.3, 0.0, 1.78), size=0.26, cord=0.0)
    beam("lamp_arm", p["bark_dk"], (gx + 0.3, 0.0, 1.78), (gx + 0.3, 0.0, 1.9), thick=0.05)
    for s in (-1, 1):
        for t in (0.0, 0.4):
            blob("sap_bead", p["amber"], (gx + 0.35, s * (0.35 + t * 0.6), 1.25 + t * 0.1), 0.08, 0.08, 0.09, sides=5, rings=3)

    # Tronco oco: dois degraus de tronco, fendas de seiva, miolo escuro no topo, copa viva fora do centro.
    kx = -0.5
    cyl("keep_flare", p["bark_dk"], (kx, 0, 0.14), 1.55, 0.4, sides=10, top_radius=1.4, bevel=0.03)
    cyl("keep_base", p["bark"], (kx, 0, 0.3), 1.38, 1.5, sides=10, top_radius=1.18, bevel=0.03)
    ring("keep_band", p["bark_vio"], (kx, 0, 1.25), 1.2, 0.12, thick=0.06, sides=10)
    cyl("keep_ledge", p["bark_lt"], (kx, 0, 1.78), 1.25, 0.1, sides=10, bevel=0.0)
    cyl("keep_top", p["bark_vio"], (kx - 0.1, 0, 1.86), 0.95, 0.95, sides=9, top_radius=0.82, bevel=0.03)
    cyl("keep_rim", p["moss_lt"], (kx - 0.1, 0, 2.8), 0.85, 0.08, sides=9, bevel=0.0)
    cyl("keep_hollow", p["void"], (kx - 0.1, 0, 2.84), 0.5, 0.04, sides=9, bevel=0.0)
    root_flare(p["bark_dk"], (kx, 0, 0), 1.4, 7, 0.55, 0.6, seed=0.7, thick=0.2)
    for y in (-0.6, 0.0, 0.6):
        kit.window(p["bark_dk"], p["amber"], (kx + 1.17, y, 0.75), "x+", w=0.12, h=0.5)
    for ang in (1.6, 2.7, 3.9, 5.0):
        c, sn = math.cos(ang), math.sin(ang)
        box("sap_window", p["amber"], (kx - 0.1 + c * 0.9, sn * 0.9, 2.1), (0.1, 0.1, 0.38), bevel=0.0, rot_z=ang)
    # Coroa: galho vivo torcido, fora do centro, com folhas e lanterna.
    crown = [(kx + 0.2, 0.3, 2.8), (kx + 0.15, 0.45, 3.5), (kx - 0.1, 0.35, 4.1), (kx + 0.05, 0.5, 4.7)]
    limb("crown", p["bark_lt"], crown, 0.2, 0.07, sides=6)
    limb("crown_arm", p["bark"], [crown[1], (kx - 0.55, 0.15, 3.9), (kx - 0.8, 0.1, 4.2)], 0.1, 0.05, sides=5)
    for x, y, z, r, tone in ((kx + 0.05, 0.5, 4.8, 0.36, "leaf_green"), (kx - 0.75, 0.1, 4.25, 0.26, "leaf_green"), (kx + 0.45, 0.4, 4.2, 0.22, "moss_lt")):
        blob("crown_leaf", p[tone], (x, y, z), r, r, r * 0.55, sides=7, rings=4)
    lantern(p, (kx + 0.55, 0.45, 3.9), size=0.22, cord=0.4)

    # Refinaria clandestina: alambiques de cobre no pátio e canos de seiva enxertados no tronco.
    still(p, (0.9, 1.1))
    still(p, (1.0, -1.15), radius=0.26, height=0.4)
    cyl("yard_barrel", p["wood"], (1.35, 0.15, 0.1), 0.19, 0.36, sides=8, bevel=0.0)
    ring("yard_barrel_band", p["amber"], (1.35, 0.15, 0.25), 0.19, 0.06, sides=8)
    cyl("yard_barrel", p["wood_dk"], (1.05, 0.3, 0.1), 0.17, 0.32, sides=8, bevel=0.0)
    kit.pipe_run(p["copper"], p["copper_dk"], [(0.9, 1.1, 1.0), (0.9, 1.3, 1.9), (kx + 0.5, 1.3, 1.9), (kx + 0.5, 1.15, 1.4)], radius=0.08)
    kit.pipe_run(p["copper"], p["copper_dk"], [(1.0, -1.15, 0.8), (1.0, -1.2, 1.5), (kx + 0.4, -1.2, 1.5), (kx + 0.4, -1.1, 1.1)], radius=0.08)
    kit.pipe_run(p["copper_dk"], p["iron"], [(kx - 0.9, 1.0, 2.0), (kx - 1.2, 1.1, 2.4), (kx - 1.0, 1.0, 2.8)], radius=0.07)
    cyl("stack", p["copper_dk"], (kx - 1.0, 1.0, 2.8), 0.1, 0.45, sides=6, bevel=0.0)


# ---------------------------------------------------------------------------------------------------------
# Castelo B (leste): Cidadela da Raiz-Negra, a mesma floresta morta e virada
# ---------------------------------------------------------------------------------------------------------


def dead_bastion(p, pos, radius, height, claws, out, cocoon_len=0.0, crack=False):
    """Bastião-toco morto: tronco negro petrificado, laje violeta clara no topo e garras pálidas em volta."""
    x, y = pos
    cyl("bastion_foot", p["dead"], (x, y, 0), radius * 1.2, 0.2, sides=7)
    cyl("bastion", p["dead_lt"], (x, y, 0.16), radius * 1.08, height, sides=7, top_radius=radius * 0.78, bevel=0.03)
    ring("bastion_band", p["dead"], (x, y, 0.16 + height * 0.5), radius * 0.95, 0.12, thick=0.05, sides=7)
    cyl("bastion_cap", p["stone_lt"], (x, y, 0.16 + height), radius * 0.86, 0.12, sides=7, bevel=0.02)
    if crack:
        cyl("bastion_cap_crack", p["resin"], (x, y, 0.28 + height), radius * 0.28, 0.03, sides=7, bevel=0.0)
    base_ang = math.atan2(out[1], out[0])
    for i in range(claws):
        a = base_ang + (i - (claws - 1) / 2) * (math.tau / 3.0) / max(claws - 1, 1)
        rim = (x + math.cos(a) * radius * 0.85, y + math.sin(a) * radius * 0.85, 0.16 + height * 0.55)
        kit.horn(p["claw"], rim, (math.cos(a), math.sin(a)), length=1.3 + 0.3 * (i % 2), radius=0.2)
    if cocoon_len:
        cocoon(p, (x + math.cos(base_ang) * radius * 0.9, y + math.sin(base_ang) * radius * 0.9, 0.16 + height * 0.5), length=cocoon_len, radius=0.2, cord=0.15)


def slab_wall(p, a, b, height=1.3, thick=0.8, spikes=2):
    """Cortina de pedra em ângulo qualquer (a e b são pontos (x, y)): talude, topo claro, contrafortes de espinho e fenda de resina."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length, ang = math.hypot(dx, dy), math.atan2(dy, dx)
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    nx, ny = -dy / length, dx / length
    if nx * mx + ny * my < 0:
        nx, ny = -nx, -ny
    box("wall", p["dead_lt"], (mx, my, 0), (length, thick, height), bevel=0.03, taper_y=0.76, rot_z=ang)
    box("wall_foot", p["dead"], (mx, my, 0), (length, thick * 1.2, 0.16), bevel=0.03, rot_z=ang)
    box("wall_cap", p["stone_lt"], (mx, my, height), (length, thick * 0.66, 0.1), bevel=0.015, rot_z=ang)
    for i in range(spikes):
        t = (i + 0.5) / spikes - 0.5
        px, py = mx + dx / length * t * length * 0.8, my + dy / length * t * length * 0.8
        kit.spike(p["dead"], (px + nx * (thick / 2 + 0.15), py + ny * (thick / 2 + 0.15), 0.1), height=1.3, radius=0.2, lean=(nx * 0.5, ny * 0.5))
        kit.spike(p["thorn"], (px, py, height + 0.08), height=0.32, radius=0.07, lean=(nx * 0.1, ny * 0.1))
    box("crack", p["resin_dk"], (mx + nx * (thick / 2 * 0.8), my + ny * (thick / 2 * 0.8), 0.25), (0.1, 0.1, 0.7), bevel=0.0, rot_z=ang)


def blackroot_citadel():
    """Corrupted, Blackroot Citadel: cidadela em ponta de flecha (pedra violeta-cinza, tocos com garras, menagem rachada por resina)."""
    p = palette()
    box("plinth", p["dead"], (-0.4, 0, 0), (6.2, 5.8, 0.18), bevel=0.06, taper=0.92, taper_y=0.92)
    box("plinth_tip", p["dead"], (1.9, 0, 0), (3.6, 3.6, 0.18), bevel=0.06, taper=0.9, taper_y=0.9, rot_z=math.radians(45))
    box("yard", p["stone_dk"], (-0.5, 0, 0.14), (5.2, 4.7, 0.07), bevel=0.03)
    box("yard_tip", p["stone_dk"], (1.9, 0, 0.14), (3.0, 3.0, 0.07), bevel=0.03, rot_z=math.radians(45))
    for x, y, rx, ry in ((1.3, 0.5, 0.7, 0.5), (-1.0, -1.5, 0.7, 0.45)):
        blob("yard_pool", p["resin_dk"], (x, y, 0.19), rx, ry, 0.03, sides=8, rings=3)

    w = 2.15
    fx = 1.15  # onde as cortinas laterais viram a ponta
    slab_wall(p, (-w, -w), (-w, w), height=1.4, spikes=3)
    slab_wall(p, (-w, w), (fx, w), spikes=3)
    slab_wall(p, (-w, -w), (fx, -w), spikes=3)
    slab_wall(p, (fx, w), (2.75, 0.85), height=1.2, spikes=1)
    slab_wall(p, (fx, -w), (2.75, -0.85), height=1.2, spikes=1)

    # Bastiões-toco com garras: dois recuados e altos, dois nos ombros da ponta, apontando para a lane.
    dead_bastion(p, (-w, w), 0.9, 2.2, 4, (-0.4, 1), crack=True)
    dead_bastion(p, (-w, -w), 0.8, 1.1, 3, (-0.6, -1), cocoon_len=0.6)
    dead_bastion(p, (fx, w), 0.95, 1.45, 3, (0.6, 1))
    dead_bastion(p, (fx, -w), 0.85, 1.25, 3, (0.6, -1), cocoon_len=0.55)
    dead_bastion(p, (-0.6, -w - 0.2), 0.45, 0.8, 2, (0, -1))

    # Portaria na ponta: boca de garras que se encontram sobre o portão, casulos e resina atrás da grade.
    gx = 2.75
    box("gate_block", p["stone"], (gx - 0.2, 0, 0.1), (1.0, 1.7, 1.2), bevel=0.04, taper=0.88, taper_y=0.92)
    box("gate_cap", p["stone_lt"], (gx - 0.2, 0, 1.3), (1.05, 1.65, 0.1), bevel=0.02)
    box("gate_maw", p["void"], (gx + 0.3, 0, 0.12), (0.1, 0.9, 1.0), bevel=0.0)
    box("gate_glow", p["resin_dk"], (gx + 0.36, 0, 0.14), (0.05, 0.6, 0.55), bevel=0.0)
    for y in (-0.22, 0.0, 0.22):
        box("gate_bar", p["dead"], (gx + 0.38, y, 0.14), (0.05, 0.05, 0.95), bevel=0.0)
    for s in (-1, 1):
        limb("gate_claw", p["claw"], [(gx + 0.2, s * 0.85, 0.0), (gx + 0.4, s * 0.85, 0.9), (gx + 0.65, s * 0.55, 1.8), (gx + 0.6, s * 0.15, 2.2)], 0.22, 0.06, sides=6)
        cocoon(p, (gx + 0.6, s * 0.4, 1.75), length=0.5, radius=0.17, cord=0.2)
        kit.spike(p["thorn"], (gx + 0.15, s * 1.05, 1.0), height=0.5, radius=0.1, lean=(0.2, s * 0.25))
    blob("gate_eye", p["resin"], (gx + 0.45, 0, 1.5), 0.1, 0.18, 0.1, sides=6, rings=3)

    # Torre de menagem: dois cacos de pedra negra separados por uma ferida larga de resina tóxica.
    kx = -0.6
    box("keep_a", p["dead"], (kx, -0.95, 0.18), (2.6, 1.15, 1.5), bevel=0.05, taper=0.92, taper_y=0.9)
    box("keep_b", p["dead_lt"], (kx - 0.1, 0.95, 0.18), (2.4, 1.15, 1.7), bevel=0.05, taper=0.92, taper_y=0.9)
    box("keep_a_top", p["stone_lt"], (kx + 0.05, -0.95, 1.68), (2.2, 0.95, 0.12), bevel=0.02, rot_z=0.05)
    box("keep_b_top", p["stone_lt"], (kx - 0.1, 0.95, 1.88), (2.0, 0.95, 0.12), bevel=0.02, rot_z=-0.06)
    box("keep_up", p["dead"], (kx - 0.3, 0.9, 2.0), (1.2, 0.85, 0.8), bevel=0.04, taper=0.88, taper_y=0.88)
    box("keep_up_top", p["stone_lt"], (kx - 0.3, 0.9, 2.8), (1.0, 0.72, 0.1), bevel=0.02)
    # A ferida: fenda de resina de ponta a ponta, em zigue-zague, com poça e veias.
    # A ferida é uma laje de resina que enche o vão entre os cacos até quase o topo, irregular e torta.
    box("wound", p["resin"], (kx + 0.1, 0.0, 0.18), (2.9, 0.78, 1.4), bevel=0.04, taper=0.96, taper_y=0.9)
    box("wound_b", p["resin_dk"], (kx - 0.5, 0.05, 1.5), (1.1, 0.8, 0.12), bevel=0.0, rot_z=0.2)
    box("wound_up", p["resin"], (kx - 0.7, 0.0, 0.2), (0.3, 0.16, 1.6), bevel=0.0)
    box("wound_up2", p["resin"], (kx + 0.5, 0.02, 0.2), (0.26, 0.14, 1.1), bevel=0.0)
    blob("wound_pool", p["resin_dk"], (kx + 1.8, 0.1, 0.2), 0.45, 0.35, 0.03, sides=8, rings=3)
    for y in (-1.1, -0.8, 1.2, 1.55):
        kit.window(p["void"], p["resin"], (kx + 1.3, y, 0.8), "x+", w=0.12, h=0.38)
    # Contrafortes de espinho na menagem.
    for x, y, sx, sy in ((kx + 1.2, -1.6, 0.3, -0.6), (kx - 1.0, -1.6, -0.2, -0.6), (kx - 1.2, 1.7, -0.3, 0.6), (kx + 0.8, 1.7, 0.3, 0.6)):
        kit.spike(p["dead"], (x, y, 0.1), height=1.5, radius=0.22, lean=(sx, sy))
    # Coroa: braço de ancião morto, torto, que sai do fundo e abre dedos no alto.
    arm = [(kx - 0.9, 1.2, 2.8), (kx - 1.2, 1.0, 3.6), (kx - 0.7, 0.9, 4.2), (kx - 0.9, 0.6, 4.9)]
    limb("dead_arm", p["dead"], arm, 0.26, 0.1, sides=6)
    limb("dead_arm_b", p["claw"], [arm[1], (kx - 1.7, 1.2, 4.3), (kx - 1.8, 1.3, 4.9)], 0.1, 0.05, sides=5)
    top = arm[-1]
    for dx, dy, dz in ((0.35, 0.0, 0.8), (-0.1, 0.35, 0.7), (-0.4, -0.15, 0.6)):
        limb("finger", p["claw"], [top, (top[0] + dx * 0.5, top[1] + dy * 0.5, top[2] + dz * 0.5), (top[0] + dx, top[1] + dy, top[2] + dz)], 0.07, 0.03, sides=4)
    cocoon(p, (kx - 1.7, 1.25, 4.2), length=0.6, radius=0.18, cord=0.3)
    # Estacas de osso no pátio.
    for x, y in ((1.0, 1.3), (1.3, -1.3)):
        kit.spike(p["bone"], (x, y, 0.15), height=0.6, radius=0.07, lean=(0.05, 0.0))


CASTLES = {"ghost_rootrefinery": root_refinery, "ghost_blackroot": blackroot_citadel}


# ---------------------------------------------------------------------------------------------------------
# Saída
# ---------------------------------------------------------------------------------------------------------

SCENERY = {
    "ghost_wall": ghost_wall,
    "ghost_pillar": ghost_pillar,
    "ghost_arch": ghost_arch,
    "ghost_tree_a": ghost_tree_a,
    "ghost_tree_b": ghost_tree_b,
    "ghost_tree_c": ghost_tree_c,
    "ghost_stump": ghost_stump,
    "ghost_bramble": ghost_bramble,
    "ghost_mushrooms": ghost_mushrooms,
    "ghost_boulder": ghost_boulder,
    "ghost_bones": ghost_bones,
    "ghost_idol": ghost_idol,
    "ghost_tap": ghost_tap,
    "ghost_husk": ghost_husk,
    "ghost_vat": ghost_vat,
    "ghost_vent": ghost_vent,
    "ghost_fallen": ghost_fallen,
    "ghost_watch": ghost_watch,
    "ghost_snag": ghost_snag,
    "ghost_crag": ghost_crag,
    "ghost_spire": ghost_spire,
    "ghost_log": ghost_log,
    "ghost_log_b": ghost_log_b,
    "ghost_hare": ghost_hare,
    "ghost_beetle": ghost_beetle,
    "ghost_toad": ghost_toad,
    "ghost_possum": ghost_possum,
    "ghost_moth": ghost_moth,
    "ghost_bat": ghost_bat,
}


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["all"]
    out_dir = game_paths.out_arg(args, "--out")
    render_dir = args[args.index("--render") + 1] if "--render" in args else ""
    # Prévia sobre chão de folhas violeta, não sobre a lama padrão do kit.
    kit.render = functools.partial(kit.render, ground=0x5C4A58)
    everything = {**CASTLES, **SCENERY}
    names = list(everything) if args[0] == "all" else [args[0]]
    for name in names:
        is_castle = name in CASTLES
        target = os.path.join(out_dir, "castles") if out_dir and is_castle else os.path.join(out_dir, "scenery", "ghostwood") if out_dir else ""
        views = (("front", -35.0), ("back", 150.0), ("game", -90.0)) if is_castle else (("front", -35.0),)
        kit.build(name, target, render_dir, make=everything[name], views=views)


if __name__ == "__main__":
    main()
