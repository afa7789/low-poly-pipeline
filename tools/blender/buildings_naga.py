"""Prédios da raça Naga modelados por script (redesenho de reports/design/race-naga.md): um GLB por prédio.

Uso:
    blender -b --factory-startup --python tools/blender/buildings_naga.py -- <id|all> [--out DIR] [--render DIR]

Frente do Abismo: ferro de âncora enferrujado, couro de mergulho, coral morto, mangueira de sifão; a informação é
verdigris e o único acento é a turquesa de válvula (a lente). Regras da raça: (1) nada é reto: a silhueta é a
curva do sifão (base larga e baixa, tronco em S, topo de equipamento de pressão); (2) o motivo é pirâmide =
válvula, e quase todo prédio tem um volante; (3) uma só lente acesa por prédio, e a posição dela diz a função
(boca, isca, válvula, mira); (4) toda base fica na lama oleosa com a linha d'água de lodo. Pegada ~3,5 x 3,5
centrada na origem, frente para +x; o jogo normaliza o tamanho, põe o plinto do time e a bandeira.
"""

import itertools
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import map_castles as kit
from map_castles import beam, box, cyl, dome, mat, prism, ring

TAU = math.tau


def pal():
    # Hex do doc clareados: a luz do jogo escurece. Paredes médio-claras, topos mais claros, escuro só em detalhe.
    return {
        "rust": mat("anchor_rust", 0xB27350),
        "rust_dk": mat("anchor_rust_dark", 0x82523C),
        "rust_lt": mat("dry_rust", 0xD08A5C),
        "plate": mat("naval_plate", 0x8C9A9C),
        "plate_dk": mat("naval_plate_dark", 0x616E72),
        "plate_lt": mat("naval_plate_light", 0xB4C0C0),
        "verdi": mat("verdigris", 0x76B8A8),
        "verdi_dk": mat("verdigris_dark", 0x4E8C86),
        "coral": mat("dead_coral", 0xDDD3BC),
        "coral_dk": mat("dead_coral_dark", 0xB9AC90),
        "lime": mat("limestone", 0xCFC8B2),
        "bone": mat("bone", 0xEDE6D2),
        "volcanic": mat("volcanic", 0x8F8A94),
        "leather": mat("tanned_leather", 0xA27B52),
        "leather_dk": mat("tanned_leather_dark", 0x6F5439),
        "sail": mat("sailcloth", 0xCFC5A5),
        "slime": mat("slime", 0x5C7E64),
        "slime_dk": mat("slime_dark", 0x45614F),
        "tar": mat("tar", 0x3B3E45),
        "oil": mat("oil", 0x24272D),
        "water": mat("oil_water", 0x3D7476),
        "vapour": mat("vapour", 0xC9D6D2),
        "lens": mat("valve_lens", 0x3CF2DA, emit=3.0),
    }


# ---------------------------------------------------------------------------------------------------------
# Peças da raça
# ---------------------------------------------------------------------------------------------------------


def pad(p, r=1.75):
    """Chão: lama e lodo do tamanho do conteúdo, com a mancha de óleo; o jogo normaliza pelo maior lado."""
    cyl("slime", p["slime"], (0, 0, 0), r, 0.1, sides=16, bevel=0.0)
    cyl("slick", p["oil"], (0.5, -0.45, 0.1), r * 0.42, 0.012, sides=10, bevel=0.0)


def skirt(p, r, z=0.1, h=0.26):
    """Linha d'água de lodo na base de um corpo redondo."""
    cyl("waterline", p["slime_dk"], (0, 0, z), r, h, sides=16, top_radius=r * 0.94, bevel=0.0)


def tube(name, material, a, b, r1, r2=None, sides=6):
    """Tronco de cone de a até b (mangueira, haste, buzina)."""
    a, b = Vector(a), Vector(b)
    d = b - a
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=r1, radius2=max(r1 if r2 is None else r2, 1e-4), depth=d.length)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, d.length / 2))
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=d.to_track_quat("Z", "Y").to_matrix())
    bmesh.ops.translate(bm, verts=bm.verts, vec=a)
    return kit._finish(bm, name, material)


def curve(pts, n=3):
    """Catmull-Rom pelos pontos: a curva em S do sifão."""
    q = [Vector(v) for v in pts]
    q = [q[0] * 2 - q[1], *q, q[-1] * 2 - q[-2]]
    out = [q[1]]
    for i in range(1, len(q) - 2):
        p0, p1, p2, p3 = q[i - 1], q[i], q[i + 1], q[i + 2]
        for k in range(1, n + 1):
            t = k / n
            out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (3 * p1 - p0 - 3 * p2 + p3) * t**3))
    return out


def hose(p, pts, r, tone="plate_dk", n=3, r_end=None, ribbed=True, sides=5):
    """Mangueira corrugada de sifão: tubos em fila pela curva, alternando o raio para marcar as nervuras."""
    path = curve(pts, n)
    m = len(path) - 1
    r_end = r if r_end is None else r_end
    for i in range(m):
        ra, rb = r + (r_end - r) * i / m, r + (r_end - r) * (i + 1) / m
        k = 1.18 if ribbed and i % 2 else 1.0
        tube("hose", p[tone], path[i], path[i + 1], ra * k, rb * k, sides)


def wheel(p, pos, r=0.25, axis="z", tone="verdi"):
    """Volante de válvula: aro octogonal, dois raios e cubo. axis = normal do plano do volante."""
    x, y, z = pos

    def at(a, rad):
        c, s = math.cos(a) * rad, math.sin(a) * rad
        return {"z": (x + c, y + s, z), "x": (x, y + c, z + s), "y": (x + c, y, z + s)}[axis]

    for i in range(8):
        beam("wheel_rim", p[tone], at(i * TAU / 8, r), at((i + 1) * TAU / 8, r), thick=0.05)
    for a in (0.0, math.pi / 2):
        beam("wheel_spoke", p[tone], at(a, r), at(a + math.pi, r), thick=0.04)
    box("wheel_hub", p["plate_dk"], (x - 0.05, y - 0.05, z - 0.05), (0.1, 0.1, 0.1), bevel=0.0)


def chain(p, a, b, sag=0.15, n=6, tone="rust_dk"):
    """Corrente de âncora: elos alternando de tom, com a barriga."""
    a, b = Vector(a), Vector(b)
    pts = [a.lerp(b, i / n) - Vector((0, 0, sag * 4 * (i / n) * (1 - i / n))) for i in range(n + 1)]
    for i in range(n):
        beam("chain", p[tone if i % 2 else "tar"], pts[i], pts[i + 1], thick=0.05)


def lens(p, pos, r=0.13, axis="x"):
    """A lente acesa: o único ponto emissivo do prédio. Moldura de verdigris e vidro turquesa."""
    """axis: "x", "y", "z" ou um vetor (lente inclinada, como a da buzina)."""
    if not isinstance(axis, str):
        d = Vector(axis).normalized()
        a = Vector(pos)
        tube("lens_frame", p["verdi_dk"], a, a + d * 0.06, r * 1.55, sides=8)
        tube("lens", p["lens"], a + d * 0.05, a + d * 0.11, r, sides=8)
        return
    rot = {"x": ("Y", math.pi / 2), "y": ("X", -math.pi / 2), "z": None}[axis]
    off = {"x": (0.05, 0, 0), "y": (0, 0.05, 0), "z": (0, 0, 0.05)}[axis]
    cyl("lens_frame", p["verdi_dk"], pos, r * 1.55, 0.06, sides=8, bevel=0.0, rot=rot)
    cyl("lens", p["lens"], (pos[0] + off[0], pos[1] + off[1], pos[2] + off[2]), r, 0.06, sides=8, bevel=0.0, rot=rot)


def coral(p, pos, h=0.5, n=5, tone="coral", seed=0.0):
    """Tufo de coral morto: pedra baixa e espinhos tortos."""
    x, y, z = pos
    dome("coral_base", p[tone], (x, y, z), h * 0.38, squash=0.7, sides=7)
    for i in range(n):
        a = seed + i * 2.4
        kit.spike(
            p[tone],
            (x + math.cos(a) * h * 0.22, y + math.sin(a) * h * 0.22, z + h * 0.05),
            height=h * (0.75 + 0.25 * math.sin(i * 1.7)),
            radius=h * 0.09,
            lean=(math.cos(a) * h * 0.25, math.sin(a) * h * 0.25),
        )


def rivets(p, center, radius, z, count=14, tone="plate_dk", size=0.07):
    """Fileira circular de rebites no topo de um tambor."""
    for i in range(count):
        a = i * TAU / count
        box("rivet", p[tone], (center[0] + math.cos(a) * radius - size / 2, center[1] + math.sin(a) * radius - size / 2, z), (size, size, size * 0.8), bevel=0.0)


def band(p, center, radius, z, tone="plate_dk", sides=14, h=0.07):
    ring("band", p[tone], (center[0], center[1], z), radius, h, thick=0.03, sides=sides)


def trunc_pyramid(p, pos, base, top, h, tone, cap_tone=None):
    """Pirâmide truncada: o motivo da raça (pirâmide = válvula)."""
    x, y, z = pos
    box("pyramid", p[tone], (x, y, z), (base, base, h), bevel=0.03, taper=top / base, taper_y=top / base)
    if cap_tone:
        box("pyramid_cap", p[cap_tone], (x, y, z + h), (top * 1.06, top * 1.06, 0.06), bevel=0.0)


def net_y(p, pos, w, h, nx=4, nz=3, tone="leather_dk"):
    """Rede esticada no plano x-z em y fixo; pos = canto inferior esquerdo (x, y, z)."""
    x, y, z = pos
    for i in range(nx + 1):
        box("net_v", p[tone], (x + w * i / nx - 0.015, y, z), (0.03, 0.03, h), bevel=0.0)
    for j in range(nz + 1):
        box("net_h", p[tone], (x, y, z + h * j / nz - 0.015), (w, 0.03, 0.03), bevel=0.0)


def anchor(p, pos, h=1.0, tone="plate_dk"):
    """Âncora de pé: haste, cepo, argola e os dois braços curvos com as patas."""
    x, y, z = pos
    tube("anchor_shank", p[tone], (x, y, z), (x, y, z + h), 0.06, sides=6)
    beam("anchor_stock", p[tone], (x, y - h * 0.3, z + h * 0.78), (x, y + h * 0.3, z + h * 0.78), thick=0.07)
    wheel(p, (x, y, z + h + 0.1), 0.1, "x", tone)
    for s in (-1, 1):
        hose(p, [(x, y, z + 0.02), (x, y + s * h * 0.2, z + h * 0.06), (x, y + s * h * 0.38, z + h * 0.28)], 0.05, tone, n=2, ribbed=False)
        kit.spike(p[tone], (x, y + s * h * 0.38, z + h * 0.28), height=h * 0.22, radius=0.1, lean=(0, s * 0.05))


def conch(p, pos, whorls, r0, h0, tone="coral", rib="coral_dk", twist=0.9):
    """Concha em espiral: troncos de cone empilhados, cada voluta menor e girada. Devolve o topo (x, y, z)."""
    x, y, z = pos
    r = r0
    for i in range(whorls):
        off = (r0 - r) * 0.55
        cx, cy = x + math.cos(twist * i) * off * 0.5, y + math.sin(twist * i) * off * 0.5
        cyl("whorl", p[tone], (cx, cy, z), r, h0, sides=9, top_radius=r * 0.82, bevel=0.02, rot=("Z", twist * i))
        ring("whorl_rib", p[rib], (cx, cy, z + h0 * 0.62), r * 0.9, 0.07, thick=0.03, sides=9)
        z += h0 * 0.92
        r *= 0.74
    kit.spike(p[tone], (x + math.cos(twist * whorls) * r0 * 0.12, y + math.sin(twist * whorls) * r0 * 0.12, z), height=r0 * 0.6, radius=r * 0.8, lean=(0.08, 0.05))
    return (x, y, z + r0 * 0.6)


# ---------------------------------------------------------------------------------------------------------
# Tronco do desovadouro: Spawning Grounds -> Royal Spawning Grounds
# ---------------------------------------------------------------------------------------------------------


def spawn_platform(p, slab_tone, hatch_x, slab_r=1.5, wheel_pos=(0.85, 0.95)):
    """Plataforma de válvula: laje circular rebitada com a escotilha do abismo aberta, vapor e correntes."""
    pad(p)
    skirt(p, slab_r + 0.15)
    cyl("slab", p[slab_tone], (0, 0, 0.1), slab_r, 0.34, sides=16, top_radius=slab_r * 0.97, bevel=0.02)
    rivets(p, (0, 0), slab_r * 0.93, 0.44, count=18)
    # Escotilha: batente de chapa, abismo escuro, tampa encostada e a lente na boca.
    cyl("coaming", p["plate_dk"], (hatch_x, 0, 0.44), 0.7, 0.14, sides=12, bevel=0.0)
    cyl("abyss", p["oil"], (hatch_x, 0, 0.6), 0.56, 0.02, sides=12, bevel=0.0)
    box("lid", p["plate"], (hatch_x - 0.2, 0.62, 0.5), (0.7, 0.08, 0.7), bevel=0.02, rot_z=0.5)
    lens(p, (hatch_x + 0.7, 0, 0.5), 0.1, "x")
    for i, (dx, dy, s) in enumerate(((0.0, 0.0, 0.14), (0.1, -0.08, 0.2), (-0.05, 0.1, 0.27))):
        dome("vapour", p["vapour"], (hatch_x + dx, dy, 0.62 + i * 0.2), s, squash=0.9, sides=7)
    # Correntes de gancho descendo para a água, e o volante ao lado da escotilha.
    chain(p, (hatch_x + 0.55, 0.55, 0.5), (hatch_x + 0.8, 1.15, 0.1), sag=0.1, n=4)
    chain(p, (hatch_x + 0.6, -0.55, 0.5), (hatch_x + 0.85, -1.15, 0.1), sag=0.1, n=4)
    tube("wheel_stem", p["plate_dk"], (wheel_pos[0], wheel_pos[1], 0.44), (wheel_pos[0], wheel_pos[1], 1.0), 0.06)
    wheel(p, (wheel_pos[0], wheel_pos[1], 1.02), 0.27, "z")


def n_h00f_spawning_grounds():
    """Poço de válvula: laje circular rebitada, escotilha aberta soltando vapor e o guindaste em J das correntes."""
    p = pal()
    spawn_platform(p, "rust", hatch_x=0.45)
    # Guindaste em J: coluna curva e lança que pende sobre a escotilha, com a corrente e o gancho.
    tube("crane_post", p["rust_dk"], (-0.95, -0.85, 0.44), (-0.95, -0.85, 1.9), 0.13, 0.1, sides=7)
    hose(p, [(-0.95, -0.85, 1.85), (-0.55, -0.55, 2.35), (0.0, -0.15, 2.4), (0.45, 0.0, 2.1)], 0.075, "rust_dk", n=3, ribbed=False)
    chain(p, (0.45, 0.0, 2.1), (0.45, 0.0, 1.2), sag=0.0, n=4)
    hose(p, [(0.45, 0.0, 1.2), (0.45, 0.14, 1.0), (0.45, 0.0, 0.88), (0.45, -0.14, 1.0)], 0.05, "plate_dk", n=2, ribbed=False)
    coral(p, (-0.7, 0.8, 0.44), 0.5, seed=1.0)


def n_h032_royal_spawning():
    """O mesmo poço um passo maior: coroa de pirâmide truncada com volante e o estandarte de rede içado."""
    p = pal()
    spawn_platform(p, "plate_dk", hatch_x=0.7, slab_r=1.55, wheel_pos=(1.0, 1.0))
    trunc_pyramid(p, (-0.65, 0.0, 0.44), 1.6, 0.8, 1.2, "plate", cap_tone="plate_lt")
    trunc_pyramid(p, (-0.65, 0.0, 1.64), 0.8, 0.5, 0.35, "plate_dk")
    box("crown_rivets", p["plate_dk"], (-0.65 + 0.78, -0.45, 0.8), (0.04, 0.9, 0.06), bevel=0.0)
    box("crown_rivets", p["plate_dk"], (-0.65 + 0.58, -0.35, 1.5), (0.04, 0.7, 0.06), bevel=0.0)
    tube("valve_stem", p["plate_dk"], (-0.65, 0.0, 1.99), (-0.65, 0.0, 2.3), 0.07)
    wheel(p, (-0.65, 0.0, 2.32), 0.4, "z")
    # Estandarte: mastro com travessa e a rede içada, lado do fundo.
    tube("standard_pole", p["leather_dk"], (-1.15, -1.1, 0.44), (-1.15, -1.1, 2.75), 0.06)
    beam("standard_bar", p["leather_dk"], (-1.15, -1.1, 2.7), (-1.15, -0.1, 2.7), thick=0.06)
    net_y(p, (-1.15, -1.1, 1.75), 1.0, 0.95, nx=4, nz=3, tone="leather")
    for i in range(4):
        box("net_float", p["rust_lt"], (-1.15 + i * 0.25 - 0.05, -1.13, 1.7), (0.1, 0.1, 0.1), bevel=0.0)


# ---------------------------------------------------------------------------------------------------------
# Tronco do poço: Swamp Well -> Lernaean Fountain
# ---------------------------------------------------------------------------------------------------------


def n_h00j_swamp_well():
    """Boca de sumidouro: poço de calcário afundado no lodo, bomba de balancim e o cano torto cuspindo borra."""
    p = pal()
    pad(p)
    skirt(p, 0.95)
    cyl("well", p["lime"], (0.5, 0, 0.1), 0.72, 0.7, sides=10, top_radius=0.7, bevel=0.02)
    cyl("well_oil", p["oil"], (0.5, 0, 0.82), 0.52, 0.02, sides=10, bevel=0.0)
    band(p, (0.5, 0), 0.72, 0.4, "coral_dk", sides=10)
    # Balancim: cavalete em A, viga com contrapeso atrás e cabeça de cavalo na frente, haste descendo ao poço.
    for s in (-1, 1):
        beam("a_leg", p["rust_dk"], (-0.7, s * 0.55, 0.1), (-0.6, s * 0.08, 1.95), thick=0.11)
    box("pivot", p["plate_dk"], (-0.65, -0.3, 1.88), (0.14, 0.6, 0.14), bevel=0.0)
    beam("walking_beam", p["rust"], (-1.3, 0, 1.55), (0.5, 0, 2.4), thick=0.17)
    box("counterweight", p["rust_dk"], (-1.55, -0.25, 0.95), (0.5, 0.5, 0.55), bevel=0.03)
    beam("cw_hanger", p["tar"], (-1.3, 0, 1.55), (-1.3, 0, 1.5), thick=0.07)
    tube("horse_head", p["rust"], (0.5, 0, 2.4), (0.62, 0, 2.05), 0.16, 0.09, sides=6)
    tube("pump_rod", p["plate"], (0.55, 0, 2.05), (0.55, 0, 0.8), 0.045)
    # Corda com balde enferrujado no cavalete do poço.
    for s in (-1, 1):
        beam("bucket_post", p["leather_dk"], (0.5, s * 0.62, 0.1), (0.5, s * 0.62, 1.35), thick=0.08)
    beam("bucket_beam", p["leather_dk"], (0.5, -0.65, 1.35), (0.5, 0.65, 1.35), thick=0.08)
    chain(p, (0.5, 0.3, 1.35), (0.5, 0.3, 0.98), sag=0.0, n=2, tone="leather_dk")
    cyl("bucket", p["rust_dk"], (0.5, 0.3, 0.8), 0.14, 0.2, sides=8, top_radius=0.17, bevel=0.0)
    # Cano torto cuspindo borra, com o volante; a lente fica na boca do cano.
    hose(p, [(0.95, 0.4, 0.5), (1.2, 0.65, 0.95), (1.4, 0.35, 0.95), (1.5, -0.15, 0.62)], 0.1, "plate", n=3)
    tube("valve_stem", p["plate_dk"], (1.2, 0.62, 0.95), (1.2, 0.62, 1.3), 0.05)
    wheel(p, (1.2, 0.62, 1.32), 0.2, "z")
    lens(p, (1.5, -0.15, 0.5), 0.07, "z")
    cyl("sludge", p["oil"], (1.45, -0.2, 0.1), 0.3, 0.03, sides=9, bevel=0.0)
    coral(p, (-0.2, 1.2, 0.1), 0.5, seed=0.4)


def n_h05f_lernaean_fountain():
    """Cabeça de poço da hidra: boca de ferro, três mangueiras em S em volta da broca antiga e o óleo transbordando."""
    p = pal()
    pad(p)
    skirt(p, 1.5)
    cyl("mouth", p["rust"], (0, 0, 0.1), 1.35, 0.7, sides=14, top_radius=1.3, bevel=0.02)
    band(p, (0, 0), 1.35, 0.35, "rust_dk", sides=14)
    rivets(p, (0, 0), 1.2, 0.8, count=14)
    for i in range(10):
        a = 0.5 + i * TAU / 10
        coral(p, (math.cos(a) * 1.0, math.sin(a) * 1.0, 0.8), 0.34, n=3, tone="coral_dk", seed=a)
    cyl("oil_basin", p["oil"], (0, 0, 0.82), 0.78, 0.04, sides=12, bevel=0.0)
    # Óleo preto transbordando pela frente: língua inclinada e poça.
    flow = box("oil_flow", p["oil"], (0.9, -0.3, 0.1), (0.6, 0.6, 0.7), bevel=0.0)
    for v in flow.data.vertices:
        if v.co.z > 0.3:
            v.co.z = max(0.14, 0.72 - (v.co.x - 0.65) * 1.5) if v.co.x > 0.7 else 0.72
    cyl("spill", p["oil"], (1.35, -0.05, 0.1), 0.4, 0.03, sides=10, bevel=0.0)
    # Broca antiga como obelisco central: seções hexagonais torcidas.
    cyl("bit_base", p["plate_dk"], (0, 0, 0.82), 0.4, 0.22, sides=8, bevel=0.0)
    z = 1.04
    for i in range(6):
        cyl("bit", p["plate" if i % 2 else "plate_lt"], (0, 0, z), 0.36 - 0.045 * i, 0.42, sides=6, top_radius=0.32 - 0.045 * i, bevel=0.0, rot=("Z", i * 0.45))
        z += 0.4
    kit.spike(p["plate_dk"], (0, 0, z), height=0.4, radius=0.1)
    # Três mangueiras em S saindo da boca, cada uma com a cabeça de máscara opaca de coral; nenhuma é acesa.
    for k, ang in enumerate((0.0, 2.3, -2.3)):
        c, s = math.cos(ang), math.sin(ang)
        tx, ty = -s, c
        wob = 0.28 if k else 0.22
        pts = [(c * 1.0, s * 1.0, 0.85), (c * 1.25 + tx * wob, s * 1.25 + ty * wob, 1.5), (c * 0.85 - tx * wob, s * 0.85 - ty * wob, 2.3), (c * 0.95 + tx * wob, s * 0.95 + ty * wob, 3.0), (c * 1.25, s * 1.25, 3.3)]
        hose(p, pts, 0.17, "plate_dk", n=3, r_end=0.2)
        tip = Vector(pts[-1])
        dirn = (Vector(pts[-1]) - Vector(pts[-2])).normalized()
        tube("mask", p["coral"], tip, tip + dirn * 0.32, 0.26, 0.15, sides=6)
        tube("mask_mouth", p["oil"], tip + dirn * 0.3, tip + dirn * 0.35, 0.1, sides=6)
    # Mostrador de pressão na boca do poço: a única lente, e um volante pequeno ao lado.
    cyl("gauge_dial", p["coral"], (1.33, -0.55, 0.42), 0.24, 0.07, sides=10, bevel=0.0, rot=("Y", math.pi / 2))
    lens(p, (1.4, -0.55, 0.42), 0.1, "x")
    wheel(p, (1.4, 0.6, 0.5), 0.2, "x")


# ---------------------------------------------------------------------------------------------------------
# Tronco murloc: Camp -> Village -> Fortress
# ---------------------------------------------------------------------------------------------------------


def hull(p, tone, stations):
    """Casco de navio em estações (x, meia-boca no convés, z da quilha, z do convés): loft fechado."""
    bm = bmesh.new()
    rows = []
    for x, wt, zb, zt in stations:
        wb = wt * 0.5
        rows.append([bm.verts.new(v) for v in ((x, -wt, zt), (x, wt, zt), (x, wb, zb), (x, -wb, zb))])
    for a, b in itertools.pairwise(rows):
        for k in range(4):
            bm.faces.new((a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k]))
    bm.faces.new(rows[0])
    bm.faces.new(reversed(rows[-1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit._finish(bm, "hull", p[tone], 0.03)


def n_h020_murloc_camp():
    """Barraca de sucata: meia cúpula de chapa corrugada afundada no lodo, claraboia, gancho gigante e o monte à venda."""
    p = pal()
    pad(p)
    cx, radius, sq = -0.2, 1.45, 0.8
    skirt(p, 1.55, h=0.3)
    dome("shack", p["rust"], (cx, 0, 0.1), radius, squash=sq, sides=14)
    for k in range(8):
        a = k * TAU / 8 + 0.2
        pts = [(cx + math.cos(a) * radius * math.cos(math.radians(e)), math.sin(a) * radius * math.cos(math.radians(e)), 0.1 + radius * sq * math.sin(math.radians(e)) + 0.02) for e in (4, 25, 45, 65, 82)]
        for u, v in itertools.pairwise(pts):
            beam("plate_rib", p["rust_dk"], u, v, thick=0.06)
    # Claraboia de lente no alto: a única luz do prédio.
    cyl("skylight", p["verdi_dk"], (cx, 0, 1.2), 0.36, 0.12, sides=8, top_radius=0.3, bevel=0.0)
    lens(p, (cx, 0, 1.31), 0.2, "z")
    # Porta de madeira de naufrágio virada para +x, com viga e lintel.
    box("door", p["leather_dk"], (1.0, -0.35, 0.1), (0.3, 0.7, 0.8), bevel=0.02)
    for y in (-0.42, 0.42):
        box("door_post", p["leather"], (0.98, y - 0.05, 0.1), (0.2, 0.1, 0.95), bevel=0.0)
    box("door_lintel", p["leather"], (0.98, -0.5, 0.95), (0.22, 1.0, 0.1), bevel=0.0)
    # Gancho gigante sobre a porta: mastro, braço curvo e o J pendurado.
    tube("hook_post", p["plate_dk"], (1.4, 0.95, 0.1), (1.4, 0.95, 2.2), 0.09, sides=6)
    hose(p, [(1.4, 0.95, 2.2), (1.55, 0.55, 2.4), (1.55, 0.05, 2.25)], 0.07, "plate_dk", n=3, ribbed=False)
    chain(p, (1.55, 0.05, 2.25), (1.55, 0.05, 1.7), sag=0.0, n=3)
    hose(p, [(1.55, 0.05, 1.7), (1.55, 0.05, 1.35), (1.55, -0.28, 1.2), (1.55, -0.45, 1.5)], 0.075, "rust_dk", n=3, ribbed=False)
    # Forja de tambor (apagada, só ferrugem seca) com o cano torto, e o monte de sucata.
    cyl("forge", p["rust_dk"], (-1.0, 1.15, 0.1), 0.32, 0.55, sides=9, bevel=0.0)
    cyl("forge_coal", p["rust_lt"], (-1.0, 1.15, 0.64), 0.26, 0.03, sides=9, bevel=0.0)
    hose(p, [(-1.05, 1.15, 0.6), (-1.2, 1.0, 1.2), (-1.0, 0.95, 1.6)], 0.08, "plate_dk", n=3)
    for k, (dx, dy, rz) in enumerate(((0.0, 0.0, 0.3), (0.2, 0.15, 1.2), (-0.15, 0.25, 2.0))):
        box("scrap_plank", p["leather" if k % 2 else "leather_dk"], (0.9 + dx, -1.05 + dy, 0.1 + k * 0.1), (0.8, 0.14, 0.1), bevel=0.0, rot_z=rz)
    box("scrap_plate", p["plate"], (0.95, -1.15, 0.1), (0.45, 0.4, 0.14), bevel=0.02, rot_z=0.4)
    cyl("scrap_pipe", p["plate_dk"], (0.5, -1.05, 0.14), 0.09, 0.8, sides=6, bevel=0.0, rot=("Y", math.pi / 2))
    wheel(p, (1.0, -1.3, 0.62), 0.24, "y", "verdi_dk")
    wheel(p, (-0.2, 1.3, 0.55), 0.18, "y", "verdi")


def n_h021_murloc_village():
    """Vila de palafita: três barracos de chapa empilhados em pilhas de corrente de âncora, torre torta sob a vela rasgada."""
    p = pal()
    pad(p)
    # Pilhas: troncos de corrente com cintas, ligadas por correntes caídas.
    pile = [(-0.9, -0.85), (-0.9, 0.85), (0.55, -0.85), (0.55, 0.85)]
    for x, y in pile:
        cyl("pile", p["plate_dk"], (x, y, 0.1), 0.14, 1.0, sides=7, bevel=0.0)
        ring("pile_band", p["rust_dk"], (x, y, 0.3), 0.14, 0.08, thick=0.03, sides=7)
        ring("pile_band", p["rust_dk"], (x, y, 0.7), 0.14, 0.08, thick=0.03, sides=7)
        coral(p, (x, y, 0.1), 0.34, n=3, seed=x)
    chain(p, (-0.9, -0.85, 0.85), (0.55, -0.85, 0.85), sag=0.22, n=5)
    chain(p, (-0.9, 0.85, 0.85), (0.55, 0.85, 0.85), sag=0.22, n=5)
    # Três barracos, cada um deslocado e torcido: a torre de lata que se inclina.
    tiers = [
        ((-0.2, 0.0), 0.0, (2.0, 2.0, 0.85), "rust", "verdi_dk", 1.05),
        ((-0.1, 0.18), 0.12, (1.55, 1.55, 0.8), "plate", "rust_dk", 2.0),
        ((0.05, 0.38), 0.25, (1.15, 1.15, 0.75), "verdi", "plate_dk", 2.9),
    ]
    for (x, y), rz, size, wall, roof, z in tiers:
        box("hut", p[wall], (x, y, z), size, bevel=0.03, rot_z=rz)
        for i in range(6):
            t = -size[1] / 2 + (i + 0.5) * size[1] / 6
            c, s = math.cos(rz), math.sin(rz)
            box("corrugation", p["rust_dk" if wall != "rust" else "rust_lt"], (x + c * size[0] / 2 - s * t - 0.03, y + s * size[0] / 2 + c * t - 0.03, z + 0.05), (0.06, 0.06, size[2] - 0.1), bevel=0.0, rot_z=rz)
        prism("hut_roof", p[roof], (x, y, z + size[2]), (size[0] + 0.15, size[1] + 0.1, 0.32), ridge=0.5, rot_z=rz)
    # Escada externa de pranchas subindo à porta do primeiro barraco, sob a vela rasgada.
    for i in range(5):
        box("step", p["leather"], (1.55 - i * 0.19, -0.75, 0.1), (0.3, 0.6, 0.15 + i * 0.17), bevel=0.0)
    for s in (-1, 1):
        tube("awning_post", p["leather_dk"], (1.7, -0.75 + s * 0.35, 0.1), (1.7, -0.75 + s * 0.35, 1.7), 0.05)
    sail = box("sail", p["sail"], (0.85, -1.15, 1.9), (0.95, 0.9, 0.04), bevel=0.0)
    for v in sail.data.vertices:
        v.co.z += -0.45 * (v.co.x - 0.85) if v.co.x > 0.85 else 0.0
    for i in range(3):
        box("sail_rag", p["sail"], (1.55 + i * 0.01, -1.1 + i * 0.28, 1.15 - i * 0.07), (0.05, 0.16, 0.45 + 0.1 * i), bevel=0.0, taper=0.2, taper_y=0.5)
    # Lanterna de lente pendurada na viga do topo: a única luz.
    beam("lamp_beam", p["leather_dk"], (0.5, 0.5, 3.4), (1.15, 0.5, 3.35), thick=0.07)
    chain(p, (1.15, 0.5, 3.35), (1.15, 0.5, 3.1), sag=0.0, n=1)
    lens(p, (1.15, 0.5, 3.05), 0.1, "x")
    wheel(p, (1.0, 0.95, 0.65), 0.2, "y", "verdi_dk")


def n_h022_murloc_fortress():
    """Casco naufragado fundido à margem: quilha em escada, convés em paliçada, rede, guindaste e âncora no cume."""
    p = pal()
    pad(p)
    stations = [(-1.7, 0.8, 0.1, 1.0), (-1.0, 0.82, 0.1, 1.05), (-0.2, 0.78, 0.15, 1.15), (0.6, 0.62, 0.4, 1.4), (1.3, 0.36, 0.8, 1.8), (1.72, 0.06, 1.2, 2.12)]
    hull(p, "rust", stations)
    skirt(p, 1.55, h=0.22)
    for z in (0.35, 0.65):
        box("hull_strake", p["rust_dk"], (-0.6, -0.84, z), (2.2, 0.04, 0.07), bevel=0.0)
        box("hull_strake", p["rust_dk"], (-0.6, 0.8, z), (2.2, 0.04, 0.07), bevel=0.0)

    def z_at(x):
        for (xa, _, _, za), (xb, _, _, zb) in itertools.pairwise(stations):
            if xa <= x <= xb:
                return za + (zb - za) * (x - xa) / (xb - xa)
        return stations[-1][3]

    # Paliçada de estacas pontudas ao longo das bordas do convés.
    for i in range(9):
        x = -1.5 + i * 0.36
        w = 0.8 * max(0.35, 1.0 - max(0.0, x - 0.1) * 0.5) - 0.06
        for s in (-1, 1):
            box("stake", p["leather_dk" if i % 2 else "leather"], (x, s * w, z_at(x)), (0.12, 0.1, 0.62), bevel=0.0, taper=0.3, taper_y=0.3)
    # Quilha-escada: degraus de lama a convés pelo costado de bombordo.
    for i in range(6):
        box("keel_step", p["rust_lt"] if i % 2 else p["leather"], (-0.95 + i * 0.27, 1.02, 0.1), (0.3, 0.5, 0.2 + i * 0.19), bevel=0.0)
    # Rede de carga pendurada para fora, a defesa.
    net_y(p, (-0.7, -0.88, 0.45), 1.4, 0.75, nx=6, nz=3, tone="leather")
    # Guindaste de lança: mastro, lança curva, linga de couro içando o entulho, volante de guincho.
    tube("crane_mast", p["plate_dk"], (-1.3, 0.0, 1.0), (-1.15, 0.0, 2.7), 0.11, 0.08, sides=7)
    hose(p, [(-1.15, 0.0, 2.7), (-0.7, -0.45, 2.95), (-0.2, -0.95, 2.75), (0.05, -1.2, 2.55)], 0.07, "plate_dk", n=3, ribbed=False)
    chain(p, (0.05, -1.2, 2.55), (0.05, -1.2, 1.95), sag=0.0, n=3, tone="leather_dk")
    box("spoil_bundle", p["leather"], (-0.12, -1.32, 1.5), (0.5, 0.45, 0.45), bevel=0.04)
    box("spoil_plate", p["plate"], (-0.05, -1.3, 1.92), (0.35, 0.3, 0.08), bevel=0.0, rot_z=0.4)
    lens(p, (0.05, -1.2, 2.58), 0.1, "z")
    wheel(p, (-1.2, 0.3, 1.35), 0.22, "y", "verdi_dk")
    # Âncora de proa no ponto mais alto.
    anchor(p, (1.5, 0.0, 2.0), 1.1, "plate_dk")
    coral(p, (-1.55, 0.0, 1.0), 0.45, seed=2.0)


# ---------------------------------------------------------------------------------------------------------
# Especiais de poço e som
# ---------------------------------------------------------------------------------------------------------


def n_h01z_naga_spring():
    """Nascente de sonar: bacia vulcânica rachada, buzina de concha sobre o jorro e anéis de sifão na borda."""
    p = pal()
    pad(p)
    skirt(p, 1.6, h=0.3)
    cyl("basin", p["volcanic"], (0, 0, 0.1), 1.5, 0.55, sides=9, top_radius=1.4, bevel=0.03)
    cyl("water", p["water"], (0, 0, 0.67), 1.18, 0.02, sides=9, bevel=0.0)
    for a in (0.3, 2.2, 4.0):
        box("crack", p["tar"], (math.cos(a) * 1.28 - 0.3, math.sin(a) * 1.28 - 0.025, 0.64), (0.6, 0.05, 0.02), bevel=0.0, rot_z=a)
    # Anéis de sifão: mangueira em volta da borda e dois anéis de ondas sobre a água.
    for rad, z, rr, tone in ((1.35, 0.7, 0.07, "verdi_dk"), (0.92, 0.69, 0.04, "verdi")):
        pts = [(math.cos(i * TAU / 12) * rad, math.sin(i * TAU / 12) * rad, z) for i in range(13)]
        for u, v in itertools.pairwise(pts):
            tube("siphon_ring", p[tone], u, v, rr, sides=4)
    # Jorro, volante, e a buzina de concha: tubo em S que se abre em funil virado ao céu, com a lente na garganta.
    tube("spout", p["rust"], (0, 0, 0.6), (0, 0, 1.3), 0.18, 0.15, sides=8)
    band(p, (0, 0), 0.18, 0.9, "rust_dk", sides=8, h=0.09)
    wheel(p, (0.0, 0.22, 0.9), 0.2, "y", "verdi")
    horn = [(0, 0, 1.3), (0.0, 0, 1.7), (0.1, 0, 2.1), (0.35, 0, 2.45), (0.7, 0, 2.75)]
    path = curve(horn, 3)
    m = len(path) - 1
    for i in range(m):
        f0, f1 = i / m, (i + 1) / m
        tube("conch_horn", p["verdi" if i % 3 else "coral"], path[i], path[i + 1], 0.2 + 0.4 * f0, 0.2 + 0.4 * f1, 8)
    top, aim = Vector(path[-1]), (Vector(path[-1]) - Vector(path[-2])).normalized()
    tube("horn_rim", p["coral"], top, top + aim * 0.05, 0.66, sides=8)
    tube("horn_inner", p["tar"], top + aim * 0.04, top + aim * 0.08, 0.52, sides=8)
    lens(p, top + aim * 0.07, 0.17, aim)
    chain(p, (0.3, 0.0, 1.95), (0.1, 1.3, 0.78), sag=0.15, n=5)
    chain(p, (0.3, 0.0, 1.95), (0.1, -1.3, 0.78), sag=0.15, n=5)


def n_h00m_oracle_of_sirens():
    """Oráculo de captura: tridacna aberta num grapnel de âncora, corrente da concha ao cercado e a pérola-lente na boca."""
    p = pal()
    pad(p)
    # Base: pedestal com quatro garras de âncora que se cravam no lodo.
    cyl("pedestal", p["rust"], (-0.35, 0, 0.1), 0.85, 0.5, sides=10, top_radius=0.7, bevel=0.02)
    for k in range(4):
        a = k * TAU / 4 + 0.4
        hose(p, [(-0.35 + math.cos(a) * 0.6, math.sin(a) * 0.6, 0.45), (-0.35 + math.cos(a) * 1.0, math.sin(a) * 1.0, 0.45), (-0.35 + math.cos(a) * 1.35, math.sin(a) * 1.35, 0.2)], 0.1, "rust_dk", n=2, ribbed=False)
        kit.spike(p["rust_dk"], (-0.35 + math.cos(a) * 1.35, math.sin(a) * 1.35, 0.12), height=0.2, radius=0.14)
    # Valva de baixo: tigela de coral com costelas e a pérola; valva de cima: cúpula aberta no gonzo de trás.
    cyl("shell_low", p["coral"], (-0.35, 0, 0.55), 0.55, 0.55, sides=10, top_radius=1.15, bevel=0.02)
    for k in range(10):
        a = k * TAU / 10
        beam("shell_rib", p["coral_dk"], (-0.35 + math.cos(a) * 0.55, math.sin(a) * 0.55, 0.58), (-0.35 + math.cos(a) * 1.17, math.sin(a) * 1.17, 1.08), thick=0.07)
    cyl("mantle", p["water"], (-0.35, 0, 1.12), 1.0, 0.02, sides=10, bevel=0.0)
    dome("pearl_bed", p["verdi_dk"], (-0.2, 0, 1.1), 0.34, squash=0.5, sides=8)
    dome("pearl", p["lens"], (-0.2, 0, 1.12), 0.2, squash=0.9, sides=8)
    hinge = Vector((-1.45, 0, 1.1))
    rot = Matrix.Rotation(-math.radians(58), 3, "Y")
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=1.2)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-4], context="VERTS")
    for v in bm.verts:
        v.co = rot @ (Vector((v.co.x * 0.96 + 1.2, v.co.y, v.co.z * 0.7))) + hinge
    kit._finish(bm, "shell_up", p["coral"], 0.0)
    for k in range(7):
        a = -math.pi / 2 + (k + 0.5) * math.pi / 7
        pts = [rot @ Vector((1.2 + 1.2 * math.cos(el) * math.cos(a) * 0.96, 1.2 * math.cos(el) * math.sin(a), 1.2 * 0.7 * math.sin(el) + 0.02)) + hinge for el in (0.15, 0.55, 0.95, 1.35)]
        for u, v in itertools.pairwise(pts):
            beam("lid_rib", p["coral_dk"], u, v, thick=0.07)
    # Sirene de pressão: tubo em S da base ao gonzo.
    hose(p, [(-1.3, 1.0, 0.2), (-1.5, 0.55, 0.7), (-1.45, 0.2, 1.0)], 0.1, "verdi_dk", n=3)
    # Cercado do cativo aos pés: estacas, barras, estaca central e a corrente que desce da concha.
    for k in range(9):
        a = k * TAU / 9
        px, py = 1.25 + math.cos(a) * 0.5, math.sin(a) * 0.6
        if math.cos(a) > 0.85 and abs(math.sin(a)) < 0.3:
            continue
        tube("pen_post", p["leather_dk"], (px, py, 0.1), (px, py, 0.7), 0.05, 0.04)
    cyl("pen_floor", p["slime_dk"], (1.25, 0, 0.1), 0.52, 0.03, sides=10, bevel=0.0)
    tube("pen_stake", p["plate_dk"], (1.2, 0, 0.1), (1.2, 0, 0.75), 0.07)
    wheel(p, (1.2, 0, 0.78), 0.1, "x", "verdi_dk")
    chain(p, (0.75, 0.0, 1.0), (1.2, 0.0, 0.78), sag=0.2, n=4)
    chain(p, (0.7, 0.4, 0.95), (1.2, 0.05, 0.7), sag=0.15, n=4, tone="tar")
    for y in (-0.5, 0.5):
        beam("pen_rail", p["plate"], (1.4, y, 0.62), (1.4 + 0.3, y * 1.05, 0.62), thick=0.04)
    wheel(p, (1.7, 0.0, 0.5), 0.18, "x", "verdi")
    tube("gate_stem", p["plate_dk"], (1.7, 0, 0.1), (1.7, 0, 0.5), 0.045)


# ---------------------------------------------------------------------------------------------------------
# Cadeia aérea e piscina
# ---------------------------------------------------------------------------------------------------------


def n_h01b_reptile_pool():
    """Dique de criação: tanque redondo rebitado com borda de coral, portal submerso, rampa sobre trilhos e a boia."""
    p = pal()
    pad(p)
    cx = -0.45
    skirt(p, 1.45, h=0.22)
    cyl("tank", p["rust"], (cx, 0, 0.1), 1.3, 0.8, sides=14, top_radius=1.3, bevel=0.02)
    for z in (0.3, 0.6):
        band(p, (cx, 0), 1.3, z, "rust_dk", sides=14)
    rivets(p, (cx, 0), 1.22, 0.9, count=14)
    cyl("pool_water", p["water"], (cx, 0, 0.91), 1.12, 0.02, sides=14, bevel=0.0)
    cyl("pool_slick", p["oil"], (cx - 0.6, -0.3, 0.93), 0.3, 0.012, sides=8, bevel=0.0)
    for i in range(12):
        a = i * TAU / 12 + 0.2
        dome("coral_rim", p["coral"], (cx + math.cos(a) * 1.2, math.sin(a) * 1.2, 0.88), 0.2, squash=0.75, sides=6)
    for i in range(0, 12, 3):
        a = i * TAU / 12 + 0.2
        kit.spike(p["coral"], (cx + math.cos(a) * 1.2, math.sin(a) * 1.2, 0.9), height=0.4, radius=0.08, lean=(0.05, 0.05))
    # Portal submerso no costado da frente e a rampa de doca sobre trilhos descendo ao chão.
    box("portal", p["tar"], (cx + 1.25, -0.38, 0.1), (0.14, 0.76, 0.55), bevel=0.0)
    box("portal_frame", p["plate_dk"], (cx + 1.3, -0.5, 0.1), (0.08, 1.0, 0.68), bevel=0.0)
    ramp = box("ramp", p["leather"], (cx + 1.35, -0.45, 0.1), (0.8, 0.9, 0.8), bevel=0.0)
    for v in ramp.data.vertices:
        v.co.z = 0.2 + (cx + 1.75 - v.co.x) / 0.8 * 0.45 if v.co.z > 0.3 else v.co.z
    for y in (-0.88, -0.02):
        beam("ramp_rail", p["plate_dk"], (cx + 1.35, y, 0.7), (cx + 2.15, y, 0.28), thick=0.06)
    # Boia de amarração na água com a lente de isca no topo, e o mastro de amarração com mangueira.
    bx, by = cx + 0.1, 0.25
    cyl("buoy_low", p["rust_lt"], (bx, by, 0.9), 0.1, 0.1, sides=8, top_radius=0.34, bevel=0.0)
    cyl("buoy_mid", p["sail"], (bx, by, 1.0), 0.34, 0.18, sides=8, top_radius=0.3, bevel=0.0)
    cyl("buoy_top", p["rust_lt"], (bx, by, 1.18), 0.3, 0.14, sides=8, top_radius=0.12, bevel=0.0)
    tube("buoy_mast", p["plate_dk"], (bx, by, 1.32), (bx, by, 1.55), 0.04)
    lens(p, (bx, by, 1.56), 0.1, "z")
    tube("mooring_mast", p["plate_dk"], (cx - 0.7, 0.85, 0.85), (cx - 0.7, 0.85, 2.4), 0.09, 0.07, sides=6)
    hose(p, [(cx - 0.7, 0.85, 2.3), (cx - 0.6, 0.8, 1.6), (cx - 0.2, 0.5, 1.25), (bx, by, 1.1)], 0.05, "verdi_dk", n=3, ribbed=False)
    wheel(p, (cx - 0.7, 1.0, 1.3), 0.18, "y", "verdi")


def conch_legs(p, deck_z, spread, top, leg_tone="plate_dk"):
    """Pernas de âncora abertas com patas: o apoio dos templos."""
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        foot, head = (sx * spread, sy * spread, 0.1), (sx * top, sy * top, deck_z)
        tube("leg", p[leg_tone], foot, head, 0.15, 0.11, sides=6)
        kit.spike(p["rust_dk"], (sx * (spread + 0.1), sy * (spread + 0.1), 0.1), height=0.28, radius=0.16, lean=(sx * 0.1, sy * 0.1))
        ring("leg_band", p["rust_dk"], (sx * (spread + top) / 2, sy * (spread + top) / 2, deck_z * 0.5), 0.12, 0.09, thick=0.03, sides=6)


def n_h080_temple_of_riptide():
    """Plataforma que avança para o mar: portal de concha sobre pernas de âncora, viga de lançamento e farol no ápice."""
    p = pal()
    pad(p)
    conch_legs(p, 1.5, 1.15, 0.78)
    cyl("deck", p["plate"], (0, 0, 1.45), 1.1, 0.14, sides=12, bevel=0.0)
    rivets(p, (0, 0), 1.0, 1.59, count=12)
    # Concha-portal em duas voltas, boca virada para +x.
    top = conch(p, (-0.2, 0, 1.59), 3, 0.98, 0.66)
    box("mouth_arch", p["tar"], (0.55, -0.3, 1.59), (0.2, 0.6, 0.75), bevel=0.0, taper=0.7, taper_y=0.8)
    box("mouth_lip", p["coral_dk"], (0.5, -0.4, 1.59), (0.12, 0.8, 0.12), bevel=0.0)
    # Viga de lançamento por cima da água: treliça em balanço com a ponta e o pórtico.
    beam("launch_beam", p["rust"], (0.5, -0.5, 1.7), (1.7, -0.5, 1.82), thick=0.14)
    beam("launch_beam", p["rust"], (0.5, 0.5, 1.7), (1.7, 0.5, 1.82), thick=0.14)
    for x in (0.8, 1.15, 1.5):
        beam("launch_rung", p["rust_dk"], (x, -0.5, 1.76), (x, 0.5, 1.8), thick=0.07)
    beam("launch_brace", p["plate_dk"], (0.4, -0.5, 1.3), (1.65, -0.5, 1.75), thick=0.07)
    beam("launch_brace", p["plate_dk"], (0.4, 0.5, 1.3), (1.65, 0.5, 1.75), thick=0.07)
    # Farol grande no ápice: gaiola de verdigris e a lente.
    tube("beacon_post", p["verdi_dk"], (top[0], top[1], top[2] - 0.05), (top[0], top[1], top[2] + 0.25), 0.07)
    cyl("beacon_cage", p["verdi_dk"], (top[0], top[1], top[2] + 0.25), 0.34, 0.1, sides=8, bevel=0.0)
    lens(p, (top[0], top[1], top[2] + 0.35), 0.26, "z")
    wheel(p, (0.95, 0.95, 0.75), 0.2, "x", "verdi")


def n_h01y_temple_of_snakes():
    """Poleiro de sentinela: concha baixa só sobre o fundo, pórtico aberto à frente com as correntes de poleiro e a lanterna."""
    p = pal()
    pad(p)
    for sx, sy, h in ((-1.15, 0.8, 1.35), (-1.15, -0.8, 1.35), (0.65, 0.9, 1.35), (0.65, -0.9, 1.35)):
        cyl("pillar", p["plate_dk"], (sx, sy, 0.1), 0.17, h, sides=7, top_radius=0.14, bevel=0.0)
        ring("pillar_band", p["rust_dk"], (sx, sy, 0.6), 0.15, 0.08, thick=0.03, sides=7)
        kit.spike(p["rust_dk"], (sx + 0.1, sy * 1.12, 0.1), height=0.28, radius=0.16, lean=(0.1, 0.1 if sy > 0 else -0.1))
    cyl("roof_slab", p["plate"], (-0.65, 0, 1.4), 1.05, 0.16, sides=12, bevel=0.0)
    rivets(p, (-0.65, 0), 0.95, 1.56, count=12)
    conch(p, (-0.7, 0, 1.56), 3, 0.85, 0.5)
    # Pórtico da frente: viga de pilar a pilar e os poleiros em corrente, ao ar livre.
    beam("gantry", p["rust"], (0.65, -0.9, 1.45), (0.65, 0.9, 1.45), thick=0.14)
    for y in (-0.45, 0.45):
        chain(p, (0.65, y, 1.45), (0.65, y, 0.8), sag=0.0, n=3)
        beam("perch", p["leather_dk"], (0.15, y, 0.8), (1.15, y, 0.8), thick=0.09)
    # Lanterna de lente na entrada, num poste torto.
    hose(p, [(1.45, -1.2, 0.1), (1.5, -1.1, 0.6), (1.45, -1.2, 1.0), (1.55, -1.15, 1.3)], 0.045, "plate_dk", n=3, ribbed=False)
    lens(p, (1.55, -1.15, 1.3), 0.13, "x")
    wheel(p, (1.1, 1.3, 0.45), 0.17, "y", "verdi")
    coral(p, (-1.3, -0.3, 0.1), 0.5, seed=1.0)


# ---------------------------------------------------------------------------------------------------------
# Marcos da raça: pirâmide, estátua, torre de válvula
# ---------------------------------------------------------------------------------------------------------


def n_h00i_ancient_pyramide():
    """A válvula em pessoa: pirâmide escalonada de chapa sobre concreto de coral, com volante no ápice e o olho-mostrador."""
    p = pal()
    pad(p)
    skirt(p, 1.75, h=0.18)
    box("base_slab", p["coral_dk"], (0, 0, 0.1), (3.3, 3.3, 0.3), bevel=0.04)
    # Degraus: dois de concreto de coral embaixo, dois de chapa rebitada em cima.
    tiers = [(2.8, 0.75, "coral", "coral_dk"), (2.2, 0.7, "coral", "coral_dk"), (1.6, 0.65, "rust", "rust_dk"), (1.05, 0.6, "rust", "rust_dk")]
    z = 0.4
    for i, (w, h, tone, ledge) in enumerate(tiers):
        box("tier", p[tone], (0, 0, z), (w, w, h), bevel=0.04)
        box("ledge", p[ledge], (0, 0, z + h), (w * 1.04, w * 1.04, 0.07), bevel=0.0)
        if tone == "rust":
            for k in range(5):
                t = -w / 2 + (k + 0.5) * w / 5
                box("rivet", p["plate_dk"], (w / 2, t - 0.03, z + h - 0.12), (0.04, 0.06, 0.06), bevel=0.0)
        # Costuras que choram óleo: faixas escuras descendo em cada degrau.
        for dy in (-0.35 * w, 0.28 * w):
            box("oil_seam", p["tar"], (w / 2, dy, z + 0.05), (0.03, 0.07, h * (0.9 if i % 2 else 0.6)), bevel=0.0)
        z += h + 0.07
    # Olho-mostrador no segundo degrau: aro de verdigris, mostrador de coral e a lente no centro.
    cyl("gauge_rim", p["verdi_dk"], (1.1, -0.0, 1.55), 0.43, 0.06, sides=10, bevel=0.0, rot=("Y", math.pi / 2))
    cyl("gauge_dial", p["coral"], (1.15, 0, 1.55), 0.36, 0.05, sides=10, bevel=0.0, rot=("Y", math.pi / 2))
    lens(p, (1.2, 0, 1.55), 0.16, "x")
    # Volante no ápice: haste e roda grande, a pirâmide-válvula inteira.
    tube("apex_stem", p["plate_dk"], (0, 0, z), (0, 0, z + 0.6), 0.1, 0.08)
    wheel(p, (0, 0, z + 0.62), 0.6, "z", "verdi")
    for k in range(4):
        a = k * TAU / 4 + 0.78
        coral(p, (math.cos(a) * 1.5, math.sin(a) * 1.5, 0.4), 0.4, n=3, tone="coral_dk", seed=a)


def n_h00g_coral_statue():
    """Relicário do mergulhador perdido: sino de mergulho preso por três correntes sobre ossuário de calcário."""
    p = pal()
    pad(p)
    skirt(p, 1.35, h=0.2)
    box("ossuary", p["lime"], (0, 0, 0.1), (2.3, 2.3, 0.6), bevel=0.04, taper=0.94, taper_y=0.94)
    box("ossuary_lid", p["coral"], (0, 0, 0.7), (2.0, 2.0, 0.12), bevel=0.03)
    for i in range(5):
        for j in range(2):
            cyl("bone_end", p["bone"], (1.12, -0.8 + i * 0.4, 0.22 + j * 0.25), 0.07, 0.16, sides=6, bevel=0.0, rot=("Y", math.pi / 2))
    for y in (-0.55, 0.55):
        dome("skull", p["bone"], (1.12, y, 0.55), 0.1, squash=0.9, sides=6)
    cyl("drip_bowl", p["oil"], (0, 0, 0.82), 0.4, 0.07, sides=10, top_radius=0.5, bevel=0.0)
    # Tripé de ferro: três pernas inclinadas ao ápice com argola.
    apex = Vector((0, 0, 3.7))
    for a in (1.05, 3.14, 5.23):
        foot = Vector((math.cos(a) * 1.4, math.sin(a) * 1.4, 0.1))
        tube("tripod_leg", p["rust"], foot, apex, 0.12, 0.08, sides=6)
        ring("tripod_band", p["rust_dk"], (math.cos(a) * 0.9, math.sin(a) * 0.9, 1.5), 0.1, 0.09, thick=0.03, sides=6)
    wheel(p, (0, 0, 3.72), 0.2, "z", "verdi_dk")
    # Sino: cúpula de latão afogado, cinta, escotilha, porta-lente e incrustação de coral; três correntes o seguram.
    cyl("bell_rim", p["rust_dk"], (0, 0, 1.45), 0.84, 0.16, sides=12, bevel=0.0)
    cyl("bell_body", p["verdi"], (0, 0, 1.6), 0.76, 0.5, sides=12, top_radius=0.62, bevel=0.0)
    dome("bell_dome", p["verdi"], (0, 0, 2.1), 0.62, squash=0.75, sides=12)
    band(p, (0, 0), 0.74, 1.8, "verdi_dk", sides=12)
    cyl("bell_gland", p["rust_dk"], (0, 0, 2.5), 0.12, 0.2, sides=6, bevel=0.0)
    lens(p, (0.74, 0, 1.85), 0.13, "x")
    for k, a in enumerate((0.9, 2.3, 4.0, 5.3)):
        coral(p, (math.cos(a) * 0.62, math.sin(a) * 0.62, 1.6 + (k % 2) * 0.35), 0.38, n=3, seed=a)
    for a in (0.0, 2.1, 4.2):
        chain(p, (math.cos(a) * 0.12, math.sin(a) * 0.12, 3.65), (math.cos(a) * 0.3, math.sin(a) * 0.3, 2.55), sag=0.0, n=5)
    # Gotejar do óleo pela glândula do sino, e os ex-votos: ganchos cravados com fichas.
    tube("drip", p["oil"], (0, 0, 1.45), (0, 0, 0.9), 0.04)
    for k, a in enumerate((0.3, 1.6, 2.9, 4.6, 5.8)):
        hx, hy = math.cos(a) * 0.88, math.sin(a) * 0.88
        hose(p, [(hx, hy, 1.7 + 0.05 * k), (hx * 1.15, hy * 1.15, 1.55 + 0.05 * k), (hx * 1.1, hy * 1.1, 1.4 + 0.05 * k)], 0.03, "plate", n=2, ribbed=False)
        box("ex_voto", p[("leather", "rust_lt", "sail", "verdi", "leather_dk")[k]], (hx * 1.1 - 0.05, hy * 1.1 - 0.05, 1.28 + 0.05 * k), (0.1, 0.1, 0.12), bevel=0.0)


def n_h00n_tidal_guardian():
    """Torre de válvula: cotovelo de 90 graus em pé, coroado pela figura de proa; volante mestre no peito e tronco de sifão."""
    p = pal()
    pad(p)
    skirt(p, 1.5, h=0.3)
    cyl("foot", p["coral_dk"], (0, 0, 0.1), 1.3, 0.35, sides=10, top_radius=1.1, bevel=0.03)
    cyl("flange", p["rust_dk"], (0, 0, 0.45), 0.9, 0.14, sides=10, bevel=0.0)
    rivets(p, (0, 0), 0.8, 0.59, count=10)
    cyl("pipe", p["rust"], (0, 0, 0.59), 0.68, 2.35, sides=10, top_radius=0.6, bevel=0.02)
    for z in (1.2, 2.0, 2.7):
        band(p, (0, 0), 0.65 - (z - 0.6) * 0.03, z, "rust_dk", sides=10, h=0.1)
    # Coral subindo pela chapa, no lado do fundo.
    for k, (a, z) in enumerate(((2.4, 0.6), (3.4, 0.8), (4.0, 0.6), (2.9, 1.5))):
        coral(p, (math.cos(a) * 0.62, math.sin(a) * 0.62, z), 0.5, n=4, seed=a)
    # Volante mestre no peito, numa placa rebitada.
    box("chest_plate", p["plate_dk"], (0.55, -0.45, 1.05), (0.14, 0.9, 0.95), bevel=0.03)
    cyl("chest_boss", p["rust_dk"], (0.66, 0, 1.52), 0.16, 0.14, sides=8, bevel=0.0, rot=("Y", math.pi / 2))
    wheel(p, (0.82, 0.0, 1.52), 0.4, "x", "verdi")
    # Cotovelo: junta esférica, tubo horizontal à frente e o funil da boca.
    cyl("elbow_flange", p["plate_dk"], (0, 0, 2.9), 0.74, 0.12, sides=10, bevel=0.0)
    dome("elbow_low", p["rust"], (0, 0, 3.02), 0.76, squash=1.0, sides=10)
    dome("elbow_cap", p["rust_dk"], (0, 0, 3.02), 0.7, squash=0.5, sides=10)
    tube("neck", p["rust"], (0, 0, 3.55), (1.05, 0, 3.55), 0.52, 0.5, sides=10)
    band_tube = Vector((0.55, 0, 3.55))
    tube("neck_band", p["rust_dk"], band_tube, band_tube + Vector((0.12, 0, 0)), 0.56, sides=10)
    tube("neck_flare", p["verdi"], (1.05, 0, 3.55), (1.55, 0, 3.55), 0.5, 0.82, sides=10)
    cyl("mouth_inner", p["tar"], (1.57, 0, 3.55), 0.66, 0.04, sides=10, bevel=0.0, rot=("Y", math.pi / 2))
    lens(p, (1.6, 0, 3.55), 0.22, "x")
    # Mandíbula e sobrancelha da figura de proa, e a crista de coral na nuca.
    box("jaw", p["rust_dk"], (1.1, -0.45, 2.92), (0.65, 0.9, 0.16), bevel=0.02, taper=0.8, taper_y=0.5)
    for s in (-1, 1):
        kit.spike(p["coral"], (1.45, s * 0.38, 2.95), height=0.3, radius=0.07, lean=(0.08, s * 0.03))
    box("brow", p["plate_dk"], (1.0, -0.5, 4.05), (0.6, 1.0, 0.12), bevel=0.02, taper=0.8)
    for k in range(5):
        kit.spike(p["coral"], (-0.1 - k * 0.0, -0.3 + k * 0.15, 4.0), height=0.35 + 0.05 * (k % 2), radius=0.08, lean=(-0.12, 0.0))
    # Tronco de sifão articulado, subindo atrás até o cotovelo, e outra mangueira sangrando óleo.
    hose(p, [(-0.7, -0.95, 0.5), (-1.25, -0.5, 1.5), (-0.95, -0.3, 2.5), (-0.6, -0.1, 3.3)], 0.2, "plate", n=4)
    tube("siphon_collar", p["rust_dk"], (-0.6, -0.1, 3.25), (-0.5, -0.05, 3.5), 0.28, 0.24)
    cyl("bleed", p["oil"], (-1.1, 0.7, 0.1), 0.3, 0.03, sides=8, bevel=0.0)


BUILDINGS = {
    "h00F": n_h00f_spawning_grounds,
    "h032": n_h032_royal_spawning,
    "h00J": n_h00j_swamp_well,
    "h05F": n_h05f_lernaean_fountain,
    "h020": n_h020_murloc_camp,
    "h021": n_h021_murloc_village,
    "h022": n_h022_murloc_fortress,
    "h01Z": n_h01z_naga_spring,
    "h00M": n_h00m_oracle_of_sirens,
    "h01B": n_h01b_reptile_pool,
    "h080": n_h080_temple_of_riptide,
    "h01Y": n_h01y_temple_of_snakes,
    "h00I": n_h00i_ancient_pyramide,
    "h00G": n_h00g_coral_statue,
    "h00N": n_h00n_tidal_guardian,
}


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["all"]
    names = list(BUILDINGS) if args[0] == "all" else [args[0]]
    out_dir = args[args.index("--out") + 1] if "--out" in args else ""
    render_dir = args[args.index("--render") + 1] if "--render" in args else ""
    for name in names:
        kit.build(name, out_dir, render_dir, make=BUILDINGS[name], views=(("front", -35.0), ("game", -90.0)))


if __name__ == "__main__":
    main()
