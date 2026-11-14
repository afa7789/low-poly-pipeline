"""Prédios da raça Orc modelados por script (redesenho de reports/design/race-orc.md): um GLB por prédio.

Uso:
    blender -b --factory-startup --python tools/blender/buildings_orc.py -- <id|all> [--out DIR] [--render DIR]

Os Queimadores de Poço: tudo é sucata capturada e costurada torta (couro, osso, piche, madeira ensopada de
óleo, metal de máquina reusado ao contrário). Diagonais quebradas sob cobertura de couro, cordame grosso,
massas grandes de couro/osso; nada de casca contínua nem grade regular de rebites (isso é Mech). Regra da
raça: todo prédio tem a sua chama viva (pavio, braseiro, caldeirão, forja, tocha, cesto de fogo) como forma,
e a base afunda em lama de óleo com um resto carbonizado. Pegada ~3,5 x 3,5 centrada na origem, a porta
virada para +x; o jogo normaliza o tamanho, põe o prédio no plinto do time e desenha a bandeira.
"""

import itertools
import math
import os
import sys

import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_paths  # noqa: E402
import map_castles as kit
from map_castles import beam, box, cyl, dome, mat, prism, ring


def pal():
    return {
        "hide": mat("orc_hide", 0xB08764),
        "hide_dk": mat("orc_hide_dark", 0x866548),
        "hide_lt": mat("orc_hide_light", 0xD2B48C),
        "bone": mat("orc_bone", 0xEADFC2),
        "bone_dk": mat("orc_bone_dark", 0xBFB08C),
        "tar": mat("orc_tar", 0x3A3430),
        "char": mat("orc_char", 0x564A42),
        "rust": mat("orc_rust", 0xB9633F),
        "rust_dk": mat("orc_rust_dark", 0x8F4B33),
        "timber": mat("orc_timber", 0x9A774F),
        "timber_dk": mat("orc_timber_dark", 0x6B513A),
        "scrap": mat("orc_scrap", 0x9A948E),
        "scrap_dk": mat("orc_scrap_dark", 0x6F6963),
        "mud": mat("orc_mud", 0x5E4C3B),
        "oil": mat("orc_oil", 0x26211E),
        "cord": mat("orc_cord", 0xD2C29A),
        "smoke": mat("orc_smoke", 0xB9B2AA),
        "brush": mat("orc_brush", 0x8A8553),
        "cloth_g": mat("orc_cloth_green", 0x8C9A6E),
        "cloth_b": mat("orc_cloth_blue", 0x7C8FA4),
        "brew": mat("orc_brew", 0x7A4526),
        "ember": mat("orc_ember", 0xFF7A22, emit=3.0),
        "core": mat("orc_core", 0xFFD060, emit=4.0),
        "flame": mat("orc_flame", 0xFF9A30, emit=3.5),
    }


# ---------------------------------------------------------------------------------------------------------
# Peças da raça (a colagem: sucata costurada)
# ---------------------------------------------------------------------------------------------------------


def slab(name, material, quad, thick=0.05, toward=(0.0, 0.0, 1.0)):
    """Placa fina por 4 pontos (couro esticado, telhas de casca, abas): extrusão do quad para o lado `toward`."""
    pts = [Vector(q) for q in quad]
    n = (pts[1] - pts[0]).cross(pts[3] - pts[0]).normalized()
    if n.dot(Vector(toward)) < 0:
        n = -n
    bm = bmesh.new()
    lo = [bm.verts.new(v) for v in pts]
    hi = [bm.verts.new(v + n * thick) for v in pts]
    bm.faces.new(lo[::-1])
    bm.faces.new(hi)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit._finish(bm, name, material)


def pad(p, rem=(-1.4, -1.4), pool=(1.3, 1.2)):
    """Chão: lama misturada com óleo, uma poça e um resto carbonizado (a regra da base da raça)."""
    box("pad", p["mud"], (0, 0, 0), (3.5, 3.5, 0.1), bevel=0.03)
    cyl("oil_pool", p["oil"], (pool[0], pool[1], 0.1), 0.42, 0.012, sides=7, bevel=0.0)
    cyl("oil_pool", p["oil"], (pool[0] - 0.3, pool[1] + 0.18, 0.1), 0.26, 0.012, sides=6, bevel=0.0)
    rx, ry = rem
    beam("charred_log", p["char"], (rx - 0.3, ry - 0.1, 0.17), (rx + 0.3, ry + 0.15, 0.2), thick=0.15)
    box("charred_stub", p["tar"], (rx + 0.15, ry + 0.35, 0.1), (0.14, 0.14, 0.3), bevel=0.0, taper=0.4, taper_y=0.4)


def fire(p, pos, size=0.3):
    kit.flame(p["core"], p["flame"], pos, size)


def fire_pit(p, pos, r=0.4, size=0.34):
    """Fogueira baixa: anel de pedra suja, brasa e língua de fogo."""
    x, y, z = pos
    cyl("pit_stones", p["scrap_dk"], (x, y, z), r, 0.14, sides=8, top_radius=r * 0.9, bevel=0.0)
    cyl("pit_ember", p["ember"], (x, y, z + 0.14), r * 0.78, 0.03, sides=8, bevel=0.0)
    fire(p, (x, y, z + 0.15), size)


def smoke(p, pos, height=1.0, drift=(0.15, 0.0), r=0.2):
    """Coluna de fumaça em troncos de cone que crescem e derivam."""
    x, y, z = pos
    n = 3
    for i in range(n):
        s = r * (0.7 + 0.25 * i)
        cyl("smoke", p["smoke"], (x + drift[0] * i * (1 if i % 2 else 0.4), y + drift[1] * i, z + i * height / n), s, height / n * 1.1, sides=6, top_radius=s * 0.8, bevel=0.0)


def drum(p, pos, tone="rust", lying=False):
    """Tambor de óleo roubado: sempre torto, com cintas de piche."""
    x, y, z = pos
    if lying:
        cyl("drum", p[tone], (x - 0.21, y, z + 0.16), 0.16, 0.42, sides=8, bevel=0.0, rot=("Y", math.radians(90)))
        return
    cyl("drum", p[tone], (x, y, z), 0.16, 0.42, sides=8, bevel=0.0)
    for dz in (0.08, 0.3):
        ring("drum_band", p["tar"], (x, y, z + dz), 0.16, 0.04, thick=0.012, sides=8)


def barrel_stack(p, pos, tones=("rust", "scrap_dk", "rust_dk")):
    x, y, z = pos
    drum(p, (x, y - 0.18, z), tones[0])
    drum(p, (x, y + 0.18, z), tones[1])
    drum(p, (x + 0.02, y, z + 0.42), tones[2])


def skull(p, pos, s=1.0):
    """Caveira de kodo/troll virada para +x: crânio, órbitas de piche, presas."""
    x, y, z = pos
    box("skull", p["bone"], (x, y, z), (0.26 * s, 0.24 * s, 0.2 * s), bevel=0.02, taper=0.8, taper_y=0.9)
    box("skull_jaw", p["bone_dk"], (x + 0.05 * s, y, z - 0.08 * s), (0.2 * s, 0.18 * s, 0.09 * s), bevel=0.0)
    for sy in (-1, 1):
        box("skull_eye", p["tar"], (x + 0.12 * s, y + sy * 0.06 * s, z + 0.08 * s), (0.04, 0.06 * s, 0.07 * s), bevel=0.0)
        kit.spike(p["bone"], (x + 0.1 * s, y + sy * 0.1 * s, z - 0.06 * s), height=0.2 * s, radius=0.03 * s, lean=(0.05, sy * 0.06))


def war_drum(p, pos, r=0.3, h=0.35):
    x, y, z = pos
    cyl("war_drum", p["timber_dk"], (x, y, z), r, h, sides=10, bevel=0.0)
    cyl("war_drum_skin", p["hide_lt"], (x, y, z + h), r * 1.03, 0.04, sides=10, bevel=0.0)
    ring("war_drum_cord", p["cord"], (x, y, z + h * 0.35), r, 0.06, thick=0.015, sides=10)


def cauldron(p, pos, r=0.5, flame=True, legs=True):
    """Caldeirão costurado: bojo de sucata, cinta de couro, borda de piche, caldo escuro com brasas."""
    x, y, z = pos
    base = z + (0.28 if legs else 0.0)
    if legs:
        for i in range(3):
            a = i * math.tau / 3 + 0.4
            box("cauldron_leg", p["scrap_dk"], (x + math.cos(a) * r * 0.62, y + math.sin(a) * r * 0.62, z), (0.1, 0.1, 0.3), bevel=0.0)
        if flame:
            fire(p, (x, y, z + 0.02), r * 0.55)
    h = r * 0.95
    cyl("cauldron", p["scrap_dk"], (x, y, base), r * 0.7, h, sides=10, top_radius=r, bevel=0.0)
    ring("cauldron_stitch", p["hide"], (x, y, base + h * 0.4), r * 0.84, h * 0.22, thick=0.02, sides=10)
    ring("cauldron_rim", p["tar"], (x, y, base + h - 0.06), r, 0.1, thick=0.03, sides=10)
    cyl("cauldron_brew", p["brew"], (x, y, base + h + 0.03), r * 0.9, 0.03, sides=10, bevel=0.0)
    for i in range(3):
        a = i * 2.1 + 0.5
        box("cauldron_ember", p["ember"], (x + math.cos(a) * r * 0.45, y + math.sin(a) * r * 0.45, base + h + 0.05), (0.12, 0.12, 0.04), bevel=0.0, rot_z=a)
    for sy in (-1, 1):
        box("cauldron_ear", p["rust_dk"], (x, y + sy * (r + 0.04), base + h - 0.15), (0.1, 0.08, 0.12), bevel=0.0)


def pipe_stack(p, pos, height, r=0.14):
    """Mastro de tubos de perfuração empilhados e amarrados: o fuste dos totens."""
    x, y, z = pos
    n = max(2, round(height / 0.5))
    seg = height / n
    for i in range(n):
        cyl("drill_pipe", p["rust" if i % 2 == 0 else "scrap_dk"], (x + 0.025 * (i % 2), y, z + i * seg), r, seg * 1.02, sides=8, bevel=0.0)
        if i:
            ring("lash", p["cord"], (x, y, z + i * seg - 0.04), r, 0.08, thick=0.02, sides=8)


def banner_hide(p, pos, height=1.5, facing=0.0, tone="hide_dk", ember=False):
    """Estandarte de pele: mastro torto e pano rasgado em dois dentes."""
    kit.banner(p["timber_dk"], p[tone], pos, height, facing)
    x, y, z = pos
    if ember:
        brazier(p, (x, y, z + height), 0.14, 0.14)


def brazier(p, pos, radius=0.26, fire_size=0.26):
    kit.brazier(p["scrap_dk"], p["ember"], p["core"], p["flame"], pos, radius, fire_size)


def shovel_axe(p, base, tip):
    """Pá-machado: cabo de tubo e lâmina de pá cortada, presa torta."""
    beam("axe_haft", p["timber_dk"], base, tip, thick=0.06)
    box("axe_blade", p["scrap"], (tip[0], tip[1], tip[2] - 0.06), (0.05, 0.27, 0.3), bevel=0.0, taper=0.7, taper_y=0.9)


def cord_line(p, a, b, hang=0.0, n=6, tone="cord"):
    """Corda frouxa de a até b (cai `hang` no meio)."""
    pts = []
    for i in range(n + 1):
        t = i / n
        sag = hang * 4 * t * (1 - t)
        pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t - sag))
    for u, v in itertools.pairwise(pts):
        beam("cord", p[tone], u, v, thick=0.03)
    return pts


def net(p, left, right, drop=0.8, cells=5):
    """Rede de cabo rasgado pendurada entre dois pontos (mesma altura)."""
    for i in range(cells + 1):
        t0, t1 = i / cells, min(1.0, (i + 1) / cells)
        x0, y0 = left[0] + (right[0] - left[0]) * t0, left[1] + (right[1] - left[1]) * t0
        x1, y1 = left[0] + (right[0] - left[0]) * t1, left[1] + (right[1] - left[1]) * t1
        beam("net", p["cord"], (x0, y0, left[2]), (x1, y1, left[2] - drop), thick=0.03)
        beam("net", p["cord"], (x1, y1, left[2]), (x0, y0, left[2] - drop), thick=0.03)
    beam("net_top", p["timber_dk"], left, right, thick=0.06)


def fence_line(p, a, b, n, h=0.8, tone="timber_dk", rail=True):
    """Fileira de estacas tortas com travessa."""
    for i in range(n + 1):
        t = i / n
        kit.spike(p[tone], (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, 0.1), height=h * (0.85 + 0.075 * ((i * 7) % 3)), radius=0.07, lean=(0.04 * (i % 3 - 1), 0.04 * ((i + 1) % 3 - 1)))
    if rail:
        beam("fence_rail", p["timber"], (a[0], a[1], 0.1 + h * 0.45), (b[0], b[1], 0.1 + h * 0.5), thick=0.05)


def spokes(p, center, n=6, reach=1.6, phase=0.2):
    """A rede de tubos enterrada: canos baixos irradiando do totem pela lama."""
    cx, cy = center
    for i in range(n):
        a = phase + i * math.tau / n
        c, s = math.cos(a), math.sin(a)
        beam("spoke", p["rust_dk"], (cx + c * 0.45, cy + s * 0.45, 0.14), (cx + c * reach, cy + s * reach, 0.14), thick=0.11)
        box("spoke_joint", p["scrap_dk"], (cx + c * reach * 0.7, cy + s * reach * 0.7, 0.1), (0.2, 0.2, 0.12), bevel=0.0, rot_z=a)


def tube(material, a, b, radius=0.15, sides=8):
    """Cano redondo de a até b (os tubos grossos que a viga quadrada não faz)."""
    a, b = Vector(a), Vector(b)
    d = b - a
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=radius, radius2=radius, depth=d.length)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, d.length / 2))
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=d.to_track_quat("Z", "Y").to_matrix())
    bmesh.ops.translate(bm, verts=bm.verts, vec=a)
    return kit._finish(bm, "tube", material)


def spiral(p, tone, center, radius, z0, z1, turns=3, thick=0.1):
    """Hélice de cano em volta de um eixo vertical."""
    cx, cy = center
    steps = turns * 8
    prev = None
    for i in range(steps + 1):
        t = i / steps
        a = t * turns * math.tau
        pt = (cx + math.cos(a) * radius * (1 - 0.25 * t), cy + math.sin(a) * radius * (1 - 0.25 * t), z0 + (z1 - z0) * t)
        if prev is not None:
            beam("spiral", p[tone], prev, pt, thick=thick)
        prev = pt


def trough(p, pos, length=1.0, rot_z=0.0, tone="timber"):
    """Cocho de couro sobre cavaletes."""
    x, y, z = pos
    box("trough_legs", p["timber_dk"], (x, y, z), (length * 0.85, 0.22, 0.22), bevel=0.0, rot_z=rot_z)
    box("trough", p[tone], (x, y, z + 0.2), (length, 0.36, 0.2), bevel=0.02, rot_z=rot_z)
    box("trough_fill", p["oil"], (x, y, z + 0.38), (length * 0.88, 0.26, 0.02), bevel=0.0, rot_z=rot_z)


def ribbon(p, top, length, width, tone="hide_lt", axis=(0.0, 1.0), sway=0.15):
    """Fita de couro pendurada, ponta levada pelo vento."""
    x, y, z = top
    ax, ay = axis
    slab("ribbon", p[tone], [(x, y, z), (x + ax * width, y + ay * width, z), (x + ax * width + sway, y + ay * width, z - length), (x + sway, y, z - length)], thick=0.02, toward=(1, 0, 0))


# ---------------------------------------------------------------------------------------------------------
# Salões: Fighters' Hall -> Advanced -> Superior
# ---------------------------------------------------------------------------------------------------------


def hall_shell(p, big):
    """Corpo do salão (paredes, telhado de couro costurado, respiro central): a massa que as três casas compartilham.
    Devolve (cx, sx, sy, fx, top): centro x, tamanho, x da fachada e altura da cumeeira."""
    pad(p, rem=(-1.45, 1.3), pool=(1.45, -1.1))
    sx, sy, sz = (2.3, 2.9, 1.1) if big else (2.0, 2.2, 0.9)
    cx = -0.3 if big else -0.45
    box("hall_foot", p["scrap_dk"], (cx, 0, 0.1), (sx + 0.15, sy + 0.15, 0.18), bevel=0.02)
    box("hall", p["timber"], (cx, 0, 0.1), (sx, sy, sz), bevel=0.03)
    for y in (-sy * 0.3, sy * 0.3):
        beam("hall_cord", p["cord"], (cx + sx / 2 + 0.03, y, 0.15), (cx + sx / 2 + 0.03, y + 0.12, 0.1 + sz), thick=0.04)
    rh = 1.1 if big else 0.85
    ridge = 0.42
    prism("hall_roof", p["hide"], (cx, 0, 0.1 + sz), (sx + 0.4, sy + 0.2, rh), ridge=ridge, bevel=0.02, rot_z=0.05)
    # Costuras do couro (cabos do beiral à cumeeira) e dois remendos escuros.
    xe = cx - (sx + 0.4) / 2
    xr = xe + ridge * (sx + 0.4)
    for y in (-sy * 0.4, 0.0, sy * 0.4):
        beam("roof_seam", p["cord"], (xe + 0.05, y, 0.1 + sz + 0.06), (xr, y, 0.1 + sz + rh + 0.03), thick=0.035)
    for side_y, t0 in ((-sy * 0.22, 0.2), (sy * 0.25, 0.45)):
        quad = [(t, y) for t, y in ((t0, side_y - 0.3), (t0, side_y + 0.3), (t0 + 0.35, side_y + 0.3), (t0 + 0.35, side_y - 0.3))]
        slab("roof_patch", p["hide_dk"], [(xe + (xr - xe) * t, y, 0.1 + sz + rh * t + 0.02) for t, y in quad], thick=0.04)
    top = 0.1 + sz + rh
    if big:
        # Segunda camada do telhado, mais alta e menor.
        prism("hall_roof2", p["hide_dk"], (cx - 0.1, 0, top - 0.25), (sx - 0.2, sy - 0.8, 0.7), ridge=0.45, bevel=0.02)
        top += 0.45
    box("hall_door", p["tar"], (cx + sx / 2, 0, 0.1), (0.1, 1.1 if big else 0.8, 0.95 if big else 0.78), bevel=0.0)
    return cx, sx, sy, cx + sx / 2, top


def hall_vent(p, cx, top):
    """Respiro central: barril sobre a cumeeira, sempre fumegando."""
    cyl("smoke_vent", p["rust_dk"], (cx - 0.1, 0, top - 0.12), 0.17, 0.42, sides=8, bevel=0.0)
    smoke(p, (cx - 0.1, 0, top + 0.3), 0.55, r=0.17)


def hall_furnace(p, cx, sy):
    """Fornalha encostada na parede com a chaminé (o fogo sempre aceso)."""
    fy = -sy / 2 - 0.3
    box("furnace", p["scrap_dk"], (cx + 0.2, fy, 0.1), (0.6, 0.5, 0.62), bevel=0.03)
    box("furnace_mouth", p["ember"], (cx + 0.5, fy, 0.22), (0.05, 0.3, 0.2), bevel=0.0)
    kit.chimney(p["scrap"], p["tar"], p["tar"], (cx + 0.1, fy, 0.65), 1.35, radius=0.14)
    smoke(p, (cx + 0.1, fy, 2.0), 0.55, r=0.16)


def hall_props(p, cx, sy, fx):
    """Pás-machado encostadas na parede (reserva de recrutas), estandarte e tambor."""
    for i in range(4):
        shovel_axe(p, (cx + 0.9 - i * 0.2, sy / 2 + 0.2, 0.1), (cx + 0.7 - i * 0.2, sy / 2 + 0.02, 1.0))
    for a in (0.7, 1.05):
        shovel_axe(p, (fx + 0.7, -a * 0.9 - 0.7, 0.1), (fx + 0.75, -a * 0.9 - 0.7, 0.8))
    banner_hide(p, (fx + 0.4, 1.25, 0.1), height=1.5, facing=0.0)
    drum(p, (fx + 0.5, -1.0, 0.1))


def hall_tusks(p, fx, length, y0, radius, tone="bone", out=(0.5, 0.87), dx=0.1):
    """Boca de presas: duas presas gigantes que fecham sobre a porta."""
    for s in (-1, 1):
        kit.horn(p[tone], (fx + dx, s * y0, 0.1), (out[0], -s * out[1]), length=length, radius=radius)


def h029_fighters_hall():
    p = pal()
    cx, _, sy, fx, top = hall_shell(p, False)
    hall_vent(p, cx, top)
    hall_furnace(p, cx, sy)
    hall_tusks(p, fx, 2.1, 0.9, 0.17)
    hall_props(p, cx, sy, fx)


def h02U_advanced_fighters_hall():
    """O mesmo salão, mais alto por um sótão de couro costurado com a própria chaminé."""
    p = pal()
    cx, _, sy, fx, _ = hall_shell(p, False)
    box("loft", p["hide"], (cx + 0.05, 0.05, 1.55), (1.1, 1.3, 0.75), bevel=0.03, taper=0.9, taper_y=0.9)
    prism("loft_roof", p["hide_dk"], (cx + 0.05, 0.05, 2.3), (1.3, 1.5, 0.4), ridge=0.4)
    for y in (-0.3, 0.3):
        beam("loft_cord", p["cord"], (cx + 0.6, y, 1.6), (cx + 0.6, y + 0.1, 2.3), thick=0.04)
    kit.chimney(p["scrap"], p["tar"], p["tar"], (cx - 0.35, 0.45, 2.1), 1.1, radius=0.12)
    smoke(p, (cx - 0.35, 0.45, 3.25), 0.5, r=0.14)
    hall_vent(p, cx, 2.7)
    hall_furnace(p, cx, sy)
    hall_tusks(p, fx, 2.4, 0.9, 0.17)
    hall_props(p, cx, sy, fx)


def h031_superior_fighters_hall():
    """A sede da horda: o maior salão, telhado em camadas, mandíbula de presas e a forja do coração no portão."""
    p = pal()
    cx, _, _, fx, top = hall_shell(p, True)
    hall_vent(p, cx, top)
    hall_tusks(p, fx, 3.0, 1.0, 0.2)
    hall_tusks(p, fx, 3.5, 1.3, 0.22, tone="bone_dk", out=(0.4, 0.91), dx=-0.2)
    box("heart_forge", p["scrap_dk"], (fx - 0.05, 0, 0.1), (0.7, 0.7, 0.45), bevel=0.03)
    cyl("heart_fire_bed", p["ember"], (fx - 0.05, 0, 0.55), 0.3, 0.04, sides=8, bevel=0.0)
    fire(p, (fx - 0.05, 0, 0.58), 0.4)
    # Coroa de pás-machado enterradas na frente, em volta da fogueira do juramento.
    for i in range(9):
        a = i * math.tau / 9
        shovel_axe(p, (1.15 + math.cos(a) * 0.55, math.sin(a) * 0.55, 0.1), (1.15 + math.cos(a) * 0.78, math.sin(a) * 0.78, 0.95))
    fire_pit(p, (1.15, 0, 0.1), r=0.34, size=0.3)
    kit.chimney(p["scrap"], p["tar"], p["tar"], (cx - 0.6, 1.0, top - 0.3), 1.0, radius=0.13)
    banner_hide(p, (fx + 0.4, 1.5, 0.1), height=1.8, facing=0.0)
    drum(p, (fx + 0.5, -1.4, 0.1))


# ---------------------------------------------------------------------------------------------------------
# Tendas dos xamãs: Shamanic Tent -> Blood Shaman Tent | Infostealer's Place
# ---------------------------------------------------------------------------------------------------------


def h02B_shamanic_tent():
    """A tenda mais baixa e larga da raça: couro esticado em costelas, fumaça pelas costuras e o braseiro à vista na boca."""
    p = pal()
    pad(p, rem=(-1.4, 1.35), pool=(1.4, -1.2))
    c = (-0.15, 0.0)
    R, sq = 1.6, 0.52
    dome("tent", p["hide"], (c[0], c[1], 0.1), R, squash=sq, sides=10)
    # Costelas: costuras do couro seguindo a cúpula, e dois ossos cruzados no ápice.
    for k in range(5):
        a = k * math.tau / 5 + 0.3
        pts = [(c[0] + math.cos(a) * R * math.cos(math.radians(f)), c[1] + math.sin(a) * R * math.cos(math.radians(f)), 0.12 + R * sq * math.sin(math.radians(f)) + 0.04) for f in (0, 30, 60, 90)]
        for u, v in itertools.pairwise(pts):
            beam("rib_seam", p["cord"], u, v, thick=0.045)
    beam("apex_bone", p["bone"], (c[0] - 0.55, c[1] - 0.15, 1.05), (c[0] + 0.5, c[1] + 0.2, 1.3), thick=0.07)
    beam("apex_bone", p["bone"], (c[0] - 0.3, c[1] + 0.4, 1.2), (c[0] + 0.35, c[1] - 0.45, 1.0), thick=0.07)
    smoke(p, (c[0] - 0.35, c[1] + 0.1, 0.95), 0.8, r=0.17)
    # A boca: abertura escura com brasa por dentro.
    box("mouth", p["tar"], (c[0] + 1.42, 0, 0.1), (0.2, 0.85, 0.45), bevel=0.0, taper=0.8, taper_y=0.9)
    box("mouth_glow", p["ember"], (c[0] + 1.55, 0, 0.14), (0.06, 0.5, 0.2), bevel=0.0)
    fire_pit(p, (1.5, 0.0, 0.1), r=0.28, size=0.24)
    # Mastro de caveiras e fole pendurado.
    kit_pole = (1.1, -1.2)
    box("skull_mast", p["timber_dk"], (kit_pole[0], kit_pole[1], 0.1), (0.08, 0.08, 1.9), bevel=0.0)
    skull(p, (kit_pole[0] + 0.1, kit_pole[1], 1.55), 1.2)
    skull(p, (kit_pole[0] + 0.1, kit_pole[1], 1.1), 0.9)
    beam("mast_arm", p["timber_dk"], (kit_pole[0], kit_pole[1], 1.85), (kit_pole[0] - 0.5, kit_pole[1] + 0.3, 1.95), thick=0.05)
    slab("bellows", p["hide_dk"], [(0.5, -0.9, 1.2), (0.5, -1.2, 1.2), (0.62, -1.15, 0.8), (0.62, -0.95, 0.8)], thick=0.12)
    drum(p, (-1.4, -0.6, 0.1))


def h07Q_blood_shaman_tent():
    """Tenda de couro cuja entrada é um caldeirão emborcado: a boca sombreada é a porta e o bojo é a silhueta."""
    p = pal()
    pad(p, rem=(-1.4, -1.4), pool=(1.3, 1.3))
    c = (-0.45, 0.0)
    cyl("belly_low", p["hide_dk"], (c[0], c[1], 0.1), 1.2, 0.35, sides=10, top_radius=1.32, bevel=0.0)
    cyl("belly_mid", p["hide"], (c[0], c[1], 0.45), 1.32, 0.45, sides=10, top_radius=1.05, bevel=0.0)
    cyl("belly_top", p["hide"], (c[0], c[1], 0.9), 1.05, 0.38, sides=10, top_radius=0.5, bevel=0.0)
    ring("belly_stitch", p["cord"], (c[0], c[1], 0.62), 1.28, 0.08, thick=0.03, sides=10)
    ring("belly_rim", p["tar"], (c[0], c[1], 0.1), 1.2, 0.12, thick=0.05, sides=10)
    cyl("lid_ring", p["rust_dk"], (c[0], c[1], 1.26), 0.5, 0.1, sides=8, top_radius=0.42, bevel=0.0)
    box("lid_handle", p["scrap_dk"], (c[0], c[1], 1.36), (0.5, 0.12, 0.14), bevel=0.0)
    box("mouth", p["tar"], (c[0] + 1.05, 0, 0.1), (0.35, 0.95, 0.75), bevel=0.0, taper=0.7, taper_y=0.9)
    box("mouth_glow", p["ember"], (c[0] + 1.22, 0, 0.14), (0.06, 0.4, 0.2), bevel=0.0)
    smoke(p, (c[0], c[1] - 0.2, 1.4), 0.8, r=0.18)
    # A panela gigante fervendo ao lado, sobre fogo vivo.
    cauldron(p, (0.95, -1.0, 0.1), r=0.62)
    smoke(p, (0.95, -1.0, 1.15), 0.55, r=0.2)
    # Ganchos com bexigas de óleo seladas e chifres rolhados.
    box("hook_post", p["timber_dk"], (-1.4, 1.2, 0.1), (0.09, 0.09, 1.9), bevel=0.0)
    beam("hook_arm", p["timber_dk"], (-1.4, 1.2, 1.95), (-0.5, 1.45, 1.9), thick=0.06)
    for i, x in enumerate((-1.1, -0.8, -0.55)):
        beam("hook_cord", p["cord"], (x, 1.3 + 0.08 * i, 1.92), (x, 1.3 + 0.08 * i, 1.55), thick=0.025)
        dome("bladder", p["hide_lt" if i != 1 else "hide_dk"], (x, 1.3 + 0.08 * i, 1.28), 0.22, squash=1.4, sides=8)
    kit.horn(p["bone"], (1.2, 1.2, 0.1), (0.3, 0.9), length=0.7, radius=0.1)
    drum(p, (-1.45, -1.0, 0.1))


def h06I_infostealers_place():
    """Choupana de tecidos roubados cuja espinha é um corno de chaminé amassado que fura o teto, mais o cano de escuta."""
    p = pal()
    pad(p, rem=(-1.4, 1.3), pool=(1.4, 1.1))
    cx = -0.55
    box("wall_g", p["cloth_g"], (cx, -0.7, 0.1), (1.9, 0.8, 1.0), bevel=0.03)
    box("wall_b", p["cloth_b"], (cx, 0.0, 0.1), (1.9, 0.7, 1.0), bevel=0.03)
    box("wall_h", p["hide_lt"], (cx, 0.7, 0.1), (1.9, 0.8, 1.0), bevel=0.03)
    for y in (-0.35, 0.35):
        beam("wall_seam", p["cord"], (cx + 0.96, y, 0.15), (cx + 0.96, y, 1.08), thick=0.04)
    prism("hut_roof", p["hide"], (cx, 0, 1.1), (2.1, 2.5, 0.6), ridge=0.35)
    # Corno de chaminé amassado: três tramos desencontrados e a boca aberta tombada.
    cyl("horn_a", p["scrap_dk"], (cx - 0.2, 0.1, 0.8), 0.34, 1.1, sides=9, top_radius=0.3, bevel=0.0)
    cyl("horn_b", p["scrap"], (cx - 0.12, 0.1, 1.85), 0.3, 0.8, sides=9, top_radius=0.34, bevel=0.0)
    cyl("horn_bell", p["scrap_dk"], (cx - 0.02, 0.1, 2.6), 0.34, 0.9, sides=9, top_radius=0.72, bevel=0.0, rot=("Y", math.radians(12)))
    ring("horn_dent", p["rust_dk"], (cx - 0.16, 0.1, 1.55), 0.31, 0.09, thick=0.03, sides=9)
    smoke(p, (cx + 0.1, 0.1, 3.45), 0.5, r=0.2)
    # Cano de escuta cravado no chão, boca larga, e a fogueira baixa ao pé dele.
    cyl("listen_pipe", p["scrap"], (1.25, -0.9, 0.1), 0.2, 1.0, sides=9, top_radius=0.5, bevel=0.0, rot=("Y", math.radians(-22)))
    ring("listen_lip", p["rust_dk"], (1.12, -0.9, 1.0), 0.45, 0.07, thick=0.02, sides=9)
    fire_pit(p, (1.35, 0.1, 0.1), r=0.3, size=0.28)
    box("door_glow", p["ember"], (cx + 0.97, 0.0, 0.18), (0.06, 0.4, 0.35), bevel=0.0)
    # Varal com bolsas de couro seladas com nó.
    for y in (0.95, 1.55):
        box("line_post", p["timber_dk"], (1.1, y, 0.1), (0.07, 0.07, 1.3), bevel=0.0)
    pts = cord_line(p, (1.1, 0.95, 1.35), (1.1, 1.55, 1.35), hang=0.1, n=4)
    for i in (1, 2, 3):
        box("pouch", p["hide" if i != 2 else "bone_dk"], (pts[i][0], pts[i][1], pts[i][2] - 0.32), (0.14, 0.12, 0.28), bevel=0.0, taper=0.5, taper_y=0.5)
    drum(p, (-1.4, -1.3, 0.1))


# ---------------------------------------------------------------------------------------------------------
# Totens: mastro de tubos, rede de canos enterrada, chama viva
# ---------------------------------------------------------------------------------------------------------


def h02R_ceremonial_totem():
    """Mastro de tubos de perfuração amarrados, coroado por braseiro, com caveiras, fitas e troféus de máquina."""
    p = pal()
    pad(p, rem=(-1.35, -1.35), pool=(1.2, 1.2))
    box("totem_foot", p["scrap_dk"], (-0.1, 0, 0.1), (1.1, 1.1, 0.3), bevel=0.04, taper=0.7, taper_y=0.7)
    pipe_stack(p, (-0.1, 0, 0.4), 2.6, r=0.18)
    brazier(p, (-0.1, 0, 3.0), 0.42, 0.42)
    # Travessa com fitas, caveiras na face da frente.
    beam("cross_arm", p["timber_dk"], (-0.1, -0.8, 2.45), (-0.1, 0.8, 2.6), thick=0.08)
    for y in (-0.7, 0.7):
        ribbon(p, (-0.1, y, 2.5), 0.9, 0.18, tone="hide_lt" if y < 0 else "hide_dk", axis=(0.0, 0.1), sway=0.2)
    skull(p, (0.1, 0, 1.9), 1.5)
    skull(p, (0.08, 0, 1.2), 1.1)
    for sy in (-1, 1):
        skull(p, (-0.1, sy * 0.26, 0.85), 0.7)
    # Troféus de máquina rendida: engrenagem quebrada e manivela torta.
    cyl("gear", p["scrap"], (0.95, 0.8, 0.1), 0.38, 0.1, sides=10, bevel=0.0)
    for i in range(7):
        a = i * math.tau / 7
        box("gear_tooth", p["scrap"], (0.95 + math.cos(a) * 0.4, 0.8 + math.sin(a) * 0.4, 0.1), (0.14, 0.14, 0.1), bevel=0.0, rot_z=a)
    for u, v in (((0.7, -0.8, 0.12), (0.9, -0.55, 0.32)), ((0.9, -0.55, 0.32), (1.2, -0.7, 0.25)), ((1.2, -0.7, 0.25), (1.35, -0.4, 0.12))):
        beam("crank", p["rust_dk"], u, v, thick=0.1)
    cord_line(p, (-0.1, 0, 2.3), (-1.3, 1.1, 0.12), n=2)
    cord_line(p, (-0.1, 0, 2.3), (-1.3, -0.4, 0.12), n=2)
    drum(p, (-1.4, 1.0, 0.1))


def h02O_legendary_totem():
    """O 'não esculpido': mastro de tubo nu com três soquetes vazios e as três máscaras esperando em ganchos."""
    p = pal()
    pad(p, rem=(-1.4, 1.35), pool=(1.4, -1.3))
    box("totem_foot", p["scrap_dk"], (-0.3, 0, 0.1), (1.1, 1.1, 0.3), bevel=0.04, taper=0.7, taper_y=0.7)
    pipe_stack(p, (-0.3, 0, 0.4), 2.4, r=0.13)
    # Três braços tortos de alturas diferentes, cada um com um soquete (taça) vazio na ponta.
    for a, z, ln in ((90.0, 2.2, 0.85), (210.0, 2.55, 0.95), (330.0, 2.0, 0.8)):
        r = math.radians(a)
        tip = (-0.3 + math.cos(r) * ln, math.sin(r) * ln, z + 0.35)
        beam("socket_arm", p["timber_dk"], (-0.3, 0, z), tip, thick=0.08)
        cyl("socket", p["scrap_dk"], (tip[0], tip[1], tip[2] - 0.05), 0.17, 0.2, sides=8, top_radius=0.24, bevel=0.0)
        cyl("socket_void", p["oil"], (tip[0], tip[1], tip[2] + 0.13), 0.19, 0.02, sides=8, bevel=0.0)
    # Cabides de ofertas na frente: caldeirão, tambor e caveira, à espera.
    for s in (-1, 1):
        box("rack_post", p["timber_dk"], (0.9, s * 0.95, 0.1), (0.08, 0.08, 1.5), bevel=0.0)
    beam("rack_bar", p["timber"], (0.9, -0.95, 1.5), (0.9, 0.95, 1.5), thick=0.07)
    for y, kind in ((-0.6, "cauldron"), (0.0, "skull"), (0.6, "drum")):
        beam("hook_cord", p["cord"], (0.9, y, 1.5), (0.9, y, 1.15), thick=0.025)
        if kind == "skull":
            skull(p, (1.0, y, 0.95), 1.4)
        elif kind == "drum":
            war_drum(p, (0.9, y, 0.72), 0.2, 0.2)
        else:
            cauldron(p, (0.9, y, 0.5), r=0.2, flame=False, legs=False)
    beam("brace", p["timber"], (-0.3, 0, 1.2), (-1.4, -0.9, 0.1), thick=0.06)
    beam("brace", p["timber"], (-0.3, 0, 1.2), (-1.3, 0.8, 0.1), thick=0.06)
    fire_pit(p, (0.4, -1.3, 0.1), r=0.25, size=0.16)


def h07X_stasis_totem():
    """Válvula virada sirene: tambor e casca de corno sobre uma bobina de pressão, torta, com o piloto aceso na boca."""
    p = pal()
    pad(p, rem=(-1.4, -1.4), pool=(1.35, 1.3))
    spokes(p, (0.0, 0.0), n=7, reach=1.65)
    cyl("siren_drum", p["timber_dk"], (-0.2, 0, 0.1), 0.85, 0.55, sides=10, top_radius=0.7, bevel=0.0)
    cyl("siren_skin", p["hide_lt"], (-0.2, 0, 0.65), 0.7, 0.05, sides=10, bevel=0.0)
    ring("siren_band", p["cord"], (-0.2, 0, 0.3), 0.8, 0.06, thick=0.02, sides=10)
    spiral(p, "rust_dk", (-0.2, 0), 0.5, 0.7, 1.45, turns=3, thick=0.1)
    cyl("siren_neck", p["scrap_dk"], (-0.2, 0, 0.7), 0.2, 0.9, sides=8, bevel=0.0)
    cyl("horn", p["rust"], (-0.25, 0, 1.4), 0.2, 1.6, sides=10, top_radius=0.62, bevel=0.0, rot=("Y", math.radians(18)))
    cyl("horn_mouth", p["oil"], (0.2, 0, 2.93), 0.5, 0.05, sides=10, bevel=0.0, rot=("Y", math.radians(18)))
    cyl("horn_rim", p["rust_dk"], (0.19, 0, 2.9), 0.66, 0.05, sides=10, top_radius=0.62, bevel=0.0, rot=("Y", math.radians(18)))
    cyl("small_shell", p["scrap_dk"], (-0.5, -0.5, 0.75), 0.18, 0.7, sides=8, top_radius=0.34, bevel=0.0, rot=("Y", math.radians(-30)))
    # Válvula de descarga com o piloto aceso, e abas de pele pesadas penduradas.
    cyl("valve", p["scrap_dk"], (0.95, -0.7, 0.1), 0.14, 0.5, sides=8, bevel=0.0)
    cyl("valve_wheel", p["rust"], (0.95, -0.7, 0.62), 0.22, 0.04, sides=8, bevel=0.0)
    fire(p, (1.05, -0.7, 0.72), 0.2)
    for y in (-0.35, 0.0, 0.35):
        beam("flap_cord", p["cord"], (0.5, y, 2.95), (0.5, y, 2.6), thick=0.025)
        box("flap", p["hide_dk"], (0.5, y, 2.3), (0.04, 0.2, 0.3), bevel=0.0)
    for i in range(12):
        a = i * math.tau / 12
        beam("steam_ring", p["smoke"], (math.cos(a) * 1.25, math.sin(a) * 1.25, 0.12), (math.cos(a + math.tau / 12) * 1.25, math.sin(a + math.tau / 12) * 1.25, 0.12), thick=0.07)
    drum(p, (-1.3, 0.9, 0.1))


def h07Y_healing_totem():
    """Poste de panela: base de tambor, caldeirão costurado fervendo, vapor medicinal e canos que pingam óleo."""
    p = pal()
    pad(p, rem=(-1.4, 1.35), pool=(1.3, -1.2))
    spokes(p, (0.0, 0.0), n=6, reach=1.6, phase=0.5)
    cyl("pot_drum", p["timber_dk"], (-0.2, 0, 0.1), 0.85, 0.7, sides=10, top_radius=0.78, bevel=0.0)
    ring("pot_drum_band", p["cord"], (-0.2, 0, 0.3), 0.82, 0.06, thick=0.02, sides=10)
    ring("pot_drum_band", p["tar"], (-0.2, 0, 0.62), 0.78, 0.06, thick=0.02, sides=10)
    cauldron(p, (-0.2, 0, 0.8), r=0.95, flame=False, legs=False)
    smoke(p, (-0.5, 0.3, 1.8), 0.9, drift=(-0.1, 0.1), r=0.16)
    # Fogo vivo na frente, ligado por cano ao fundo da panela.
    fire_pit(p, (1.1, 0.0, 0.1), r=0.35, size=0.34)
    kit.pipe_run(p["rust_dk"], p["scrap_dk"], [(0.95, 0, 0.35), (0.55, 0, 0.55), (0.45, 0, 0.85)], radius=0.07)
    # Canos de gotejo com contas de óleo, e o trapo costurado espalhando o vapor.
    for y in (-0.9, 0.9):
        kit.pipe_run(p["scrap_dk"], p["rust_dk"], [(-0.6, y * 0.5, 1.2), (-0.7, y, 1.0), (-0.7, y, 0.5)], radius=0.06)
        for k in range(2):
            cyl("oil_bead", p["oil"], (-0.7, y, 0.38 - k * 0.14 + 0.02), 0.04, 0.07, sides=6, bevel=0.0)
    box("rag_pole", p["timber_dk"], (-1.2, 0.9, 0.1), (0.07, 0.07, 1.9), bevel=0.0)
    slab("rag", p["hide_lt"], [(-1.2, 0.9, 1.95), (-0.7, 0.55, 2.0), (-0.65, 0.45, 1.55), (-1.2, 0.85, 1.4)], thick=0.03)
    drum(p, (1.4, -1.2, 0.1))


def h07Z_endurance_totem():
    """Poste de fole: fole de couro gigante sobre fogo de chão alimentando a rede de canos enterrados."""
    p = pal()
    pad(p, rem=(-1.4, 1.35), pool=(1.3, -1.4))
    spokes(p, (0.0, 0.0), n=7, reach=1.65, phase=0.1)
    box("post_foot", p["scrap_dk"], (-0.45, 0, 0.1), (0.8, 0.8, 0.25), bevel=0.04, taper=0.7, taper_y=0.7)
    pipe_stack(p, (-0.45, 0, 0.35), 1.7, r=0.13)
    # Fole inclinado para o fogo: duas tábuas em cunha articuladas no poste, pregas de couro e a alavanca no alto.
    h, far = -0.35, 1.0
    def bx(t):
        return h + (far - h) * t

    for sg in (-1, 1):
        for k in range(3):
            t0, t1 = k / 3, (k + 1) / 3
            tm = (t0 + t1) / 2
            tone = p["hide_lt" if k % 2 == 0 else "hide"]

            def edge(t, bulge=0.0, sg=sg):
                return (bx(t), sg * (0.45 + 0.1 * t + bulge), 2.1 - 0.6 * t), (bx(t), sg * (0.45 + 0.1 * t + bulge), 1.85 - 1.0 * t)

            (a0, a1), (m0, m1), (c0, c1) = edge(t0), edge(tm, 0.22), edge(t1)
            slab("bellows_pleat", tone, [a0, a1, m1, m0], thick=0.04, toward=(0, sg, 0))
            slab("bellows_pleat", tone, [m0, m1, c1, c0], thick=0.04, toward=(0, sg, 0))
    slab("bellows_up", p["hide_dk"], [(h, -0.45, 2.1), (h, 0.45, 2.1), (far, 0.55, 1.5), (far, -0.55, 1.5)], thick=0.09)
    slab("bellows_dn", p["timber_dk"], [(h, -0.45, 1.85), (h, 0.45, 1.85), (far, 0.55, 0.85), (far, -0.55, 0.85)], thick=0.09, toward=(0, 0, -1))
    for t in (0.35, 0.65):
        beam("bellows_cord", p["cord"], (h + (far - h) * t, -0.58, 2.0 - 1.0 * t), (h + (far - h) * t, 0.58, 2.0 - 1.0 * t), thick=0.04)
    beam("lever", p["timber_dk"], (0.2, 0.0, 1.9), (-0.9, 0.0, 2.9), thick=0.07)
    dome("lever_weight", p["hide_dk"], (-0.9, 0.0, 2.75), 0.2, squash=1.2, sides=7)
    cyl("nozzle", p["scrap_dk"], (far + 0.1, 0, 0.5), 0.12, 0.4, sides=8, top_radius=0.2, bevel=0.0)
    fire_pit(p, (far + 0.1, 0, 0.1), r=0.36, size=0.38)
    # Odre de óleo murchando, alimentando o fogo; tambor de guerra e fitas esticadas.
    beam("skin_arm", p["timber_dk"], (-0.45, 0.2, 1.9), (-0.45, 1.0, 1.7), thick=0.06)
    dome("oil_skin", p["hide"], (-0.45, 1.0, 1.1), 0.3, squash=2.0, sides=8)
    beam("skin_drip", p["oil"], (-0.45, 1.0, 1.1), (0.5, 0.5, 0.35), thick=0.025)
    war_drum(p, (0.4, -1.1, 0.1), 0.3, 0.4)
    for sx, sy in ((-1.5, -1.3), (-1.6, 1.0)):
        kit.spike(p["timber_dk"], (sx, sy, 0.1), height=0.35, radius=0.06)
        beam("ribbon_taut", p["hide_lt"], (-0.45, 0, 2.0), (sx, sy, 0.4), thick=0.05)


# ---------------------------------------------------------------------------------------------------------
# Pastos de kodo: Kodo Farm -> Defensive | Melee | Spellbreaker
# ---------------------------------------------------------------------------------------------------------


def pen(p, h=0.8, double=False):
    """Curral de estacas tortas, portão aberto para +x."""
    s = 1.55
    fence_line(p, (-s, -s), (-s, s), 6, h)
    fence_line(p, (-s, s), (s, s), 6, h)
    fence_line(p, (-s, -s), (s, -s), 6, h)
    fence_line(p, (s, -s), (s, -0.65), 2, h)
    fence_line(p, (s, 0.65), (s, s), 2, h)
    for y in (-0.65, 0.65):
        box("gate_post", p["timber_dk"], (s, y, 0.1), (0.12, 0.12, 1.15), bevel=0.0)
    if double:
        for a, b in (((-s, -s), (-s, s)), ((-s, s), (s, s)), ((-s, -s), (s, -s))):
            beam("fence_rail2", p["timber"], (a[0], a[1], 0.1 + h * 0.8), (b[0], b[1], 0.1 + h * 0.82), thick=0.05)


def h02K_kodo_farm():
    """Curral com o arco de torres de poço queimadas por cima, tambores empilhados nos cantos e o cocho sobre o fogo."""
    p = pal()
    pad(p, rem=(0.5, -0.2), pool=(0.9, 0.2))
    pen(p)
    # Arco: duas torres de perfuração carbonizadas que tombam uma para a outra, travadas por uma viga.
    for s in (-1, 1):
        kit.derrick(p["char"], p["tar"], None, (-0.4, s * 1.25, 0.1), base=0.85, top=0.3, height=2.3, lean=(0.0, -s * 0.55))
    beam("arch_beam", p["char"], (-0.4, -0.7, 2.45), (-0.4, 0.7, 2.45), thick=0.14)
    cord_line(p, (-0.4, -0.7, 2.4), (-0.4, 0.7, 2.4), hang=0.35, n=3, tone="rust_dk")
    barrel_stack(p, (-1.25, -1.2, 0.1))
    barrel_stack(p, (-1.25, 1.2, 0.1), ("rust_dk", "rust", "scrap_dk"))
    # Cocho de couro sobre a beira do fogo de cozinha.
    fire_pit(p, (0.5, 1.0, 0.1), r=0.3, size=0.3)
    trough(p, (0.5, 0.5, 0.1), 1.0, rot_z=math.radians(90))
    # Tambor de chamada no portão: poste, couro e caveira.
    box("call_post", p["timber_dk"], (1.55, -0.95, 0.1), (0.1, 0.1, 1.6), bevel=0.0)
    war_drum(p, (1.55, -0.95, 1.5), 0.26, 0.28)
    skull(p, (1.7, -0.95, 1.1), 0.9)


def h036_defensive_kodo_farm():
    """Silhueta vertical: tampa de caldeira como teto-chapa sobre postes e uma torre de tambores, curral mais aberto."""
    p = pal()
    pad(p, rem=(1.0, -0.2), pool=(0.3, -1.3))
    pen(p, h=0.7)
    # Tampa de caldeira emborcada sobre quatro postes de alturas desiguais (tomba para a frente).
    posts = ((-1.4, -1.1, 2.1), (-1.4, 1.1, 2.1), (-0.15, -1.1, 1.7), (-0.15, 1.1, 1.7))
    for x, y, hh in posts:
        box("lid_post", p["timber_dk"], (x, y, 0.1), (0.1, 0.1, hh), bevel=0.0)
    lid = cyl("lid", p["scrap_dk"], (-0.78, 0, 1.95), 0.98, 0.16, sides=10, top_radius=0.88, bevel=0.0)
    for v in lid.data.vertices:
        v.co.z -= 0.25 * (v.co.x + 0.78) / 0.98
    cyl("lid_knob", p["rust"], (-0.78, 0, 2.1), 0.2, 0.2, sides=8, top_radius=0.12, bevel=0.0)
    # Torre de tambor: pernas abertas, plataforma, tambor de guerra no alto.
    tx, ty = 1.1, -1.15
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        beam("tower_leg", p["timber_dk"], (tx + sx * 0.38, ty + sy * 0.38, 0.1), (tx + sx * 0.22, ty + sy * 0.22, 2.4), thick=0.08)
    beam("tower_x", p["timber"], (tx + 0.34, ty - 0.34, 0.5), (tx - 0.2, ty + 0.2, 1.8), thick=0.05)
    beam("tower_x", p["timber"], (tx - 0.34, ty - 0.34, 0.5), (tx + 0.2, ty + 0.2, 1.8), thick=0.05)
    box("tower_deck", p["timber"], (tx, ty, 2.4), (0.7, 0.7, 0.08), bevel=0.0)
    war_drum(p, (tx, ty, 2.48), 0.3, 0.35)
    # Cocho de válvula pingando óleo sobre fogo baixo, e a pilha de chapas de blindagem.
    fire_pit(p, (0.9, 1.1, 0.1), r=0.3, size=0.28)
    for y in (0.95, 1.25):
        box("valve_leg", p["timber_dk"], (0.9, y, 0.1), (0.08, 0.08, 0.55), bevel=0.0)
    box("valve_trough", p["rust_dk"], (0.9, 1.1, 0.65), (0.9, 0.4, 0.18), bevel=0.02)
    beam("valve_pipe", p["scrap_dk"], (0.45, 1.1, 0.8), (0.9, 1.1, 0.9), thick=0.08)
    for dy in (-0.1, 0.1):
        beam("oil_drip", p["oil"], (0.9, 1.1 + dy, 0.65), (0.9, 1.1 + dy, 0.4), thick=0.03)
    for i in range(6):
        box("armor_plate", p["scrap" if i % 2 else "scrap_dk"], (0.1 + 0.02 * (i % 2), -0.1 - 0.5 * (i % 3 == 0), 0.1 + i * 0.07), (0.8, 0.55, 0.07), bevel=0.0, rot_z=0.15 * (i % 3))


def h092_spellbreaker_kodo_farm():
    """Uma manta inteira de couro e chapa pregada arqueia sobre o curral inteiro, corcunda e torta; fogo de piche embaixo."""
    p = pal()
    pad(p, rem=(1.0, -1.35), pool=(1.2, 1.2))
    pen(p, h=0.6)
    a_half = 1.45
    xs = (-1.4, -0.65, 0.1, 0.8)
    heights = (1.9, 2.05, 1.6, 1.15)
    nk = 6

    def pt(i, k):
        ang = k * math.pi / nk
        skew = 0.3 * math.sin(ang) * (1 if i % 2 == 0 else 0.6)
        return (xs[i] + 0.1 * math.sin(ang), a_half * math.cos(ang) * (1.0 - 0.08 * i) + skew, 0.12 + heights[i] * math.sin(ang))

    for i in range(len(xs)):
        for k in range(nk):
            beam("quilt_rib", p["timber_dk"], pt(i, k), pt(i, k + 1), thick=0.09)
        box("rib_foot", p["timber_dk"], (pt(i, 0)[0], pt(i, 0)[1], 0.1), (0.14, 0.14, 0.2), bevel=0.0)
        box("rib_foot", p["timber_dk"], (pt(i, nk)[0], pt(i, nk)[1], 0.1), (0.14, 0.14, 0.2), bevel=0.0)
    tones = ("hide", "hide_dk", "scrap_dk", "hide_lt", "rust_dk")
    for i in range(len(xs) - 1):
        for k in range(nk):
            if (i == 2 and k in (1, 2, 3)) or (i == 1 and k in (2, 3, 4)) or (i == 0 and k == 1):
                continue  # vãos da manta: deixam ver o fogo e o conteúdo
            a, b, c, d = pt(i, k), pt(i, k + 1), pt(i + 1, k + 1), pt(i + 1, k)
            ctr = tuple((a[j] + b[j] + c[j] + d[j]) / 4 for j in range(3))
            slab("quilt_plate", p[tones[(i * 2 + k) % len(tones)]], [a, b, c, d], thick=0.06, toward=(ctr[0] * 0.2, ctr[1], ctr[2] - 0.1))
    # Fogo de piche sob a manta, fumaça escapando pelas costuras.
    fire_pit(p, (-0.3, 0.15, 0.1), r=0.4, size=0.34)
    smoke(p, (-0.7, -0.4, 2.1), 0.6, r=0.17)
    # Chapas empilhadas para costurar nos kodos e panelas de tanque empilhadas.
    for i in range(5):
        box("plate_stack", p["scrap" if i % 2 else "scrap_dk"], (1.15, 1.0, 0.1 + i * 0.07), (0.7, 0.5, 0.07), bevel=0.0, rot_z=0.2 * i)
    for i in range(3):
        cyl("tank_pan", p["rust_dk"], (1.1, -1.0, 0.1 + i * 0.13), 0.38 - 0.03 * i, 0.12, sides=9, bevel=0.0)


def h035_melee_kodo_farm():
    """Curral de agressão: cocho de duto quebrado parte o pátio, cerca reforçada, estandartes rasgados e boneco de blindagem."""
    p = pal()
    pad(p, rem=(1.0, 1.3), pool=(0.5, -1.4))
    pen(p, h=0.9, double=True)
    # Duto quebrado em dois pedaços desencontrados que cortam o pátio.
    for y, ln, rot in ((-0.85, 1.3, -0.25), (0.8, 1.1, 0.3)):
        box("duct", p["rust_dk"], (0.1, y, 0.1), (0.5, ln, 0.38), bevel=0.03, rot_z=rot)
        box("duct_lip", p["tar"], (0.1, y, 0.46), (0.26, ln - 0.1, 0.05), bevel=0.0, rot_z=rot)
    box("duct_gap", p["oil"], (0.1, 0.0, 0.1), (0.55, 0.6, 0.015), bevel=0.0, rot_z=0.5)
    for rz, off in ((0.7, -0.15), (-0.5, 0.2)):
        box("duct_scrap", p["scrap_dk"], (0.35, off, 0.1), (0.3, 0.14, 0.12), bevel=0.0, rot_z=rz)
    # Estandartes rasgados nos cantos da cerca e o grande estandarte de chamada no portão.
    for sx, sy in ((-1.55, -1.55), (-1.55, 1.55)):
        banner_hide(p, (sx, sy, 0.1), height=1.7, facing=math.radians(90) * (1 if sy > 0 else -1), tone="hide_dk")
    box("call_pole", p["timber_dk"], (1.55, 0.85, 0.1), (0.1, 0.1, 2.7), bevel=0.0)
    slab("call_banner", p["rust"], [(1.55, 0.85, 2.7), (1.55, 0.2, 2.6), (1.55, 0.25, 1.9), (1.55, 0.6, 2.05), (1.55, 0.85, 1.8)][:4], thick=0.04, toward=(1, 0, 0))
    box("call_banner_tail", p["hide_dk"], (1.58, 0.25, 1.55), (0.04, 0.25, 0.4), bevel=0.0, taper=0.3)
    beam("call_cross", p["timber_dk"], (1.55, 0.85, 2.7), (1.55, 0.1, 2.7), thick=0.06)
    brazier(p, (1.55, 0.2, 2.7), 0.16, 0.16)
    # Boneco de treino: blindagem batida sobre um poste, machado cravado, fogo de treino ao pé.
    box("dummy_post", p["timber_dk"], (-0.9, 0.0, 0.1), (0.12, 0.12, 1.0), bevel=0.0)
    box("dummy_chest", p["scrap"], (-0.9, 0.0, 0.7), (0.45, 0.6, 0.6), bevel=0.03, taper=0.8, taper_y=0.9)
    cyl("dummy_helm", p["scrap_dk"], (-0.9, 0.0, 1.28), 0.2, 0.28, sides=8, top_radius=0.12, bevel=0.0)
    beam("dummy_arm", p["timber_dk"], (-0.9, -0.5, 1.05), (-0.9, 0.5, 0.95), thick=0.07)
    shovel_axe(p, (-0.7, 0.3, 0.9), (-0.55, 0.05, 1.5))
    fire_pit(p, (-0.9, -0.85, 0.1), r=0.32, size=0.3)


# ---------------------------------------------------------------------------------------------------------
# Tronco dos trolls: Troll Hut -> Trapper's Hut; covil do lendário
# ---------------------------------------------------------------------------------------------------------


def troll_hut(p, center=(-0.6, 0.0), roof_r=1.35):
    """Cabana de troll: paredes de madeira, teto cônico de couro e a chaminé de barris queimados empilhados."""
    cx, cy = center
    box("hut_foot", p["scrap_dk"], (cx, cy, 0.1), (1.8, 1.8, 0.15), bevel=0.02)
    box("hut", p["timber"], (cx, cy, 0.1), (1.65, 1.65, 0.95), bevel=0.03)
    cyl("hut_roof", p["hide"], (cx, cy, 1.0), roof_r, 0.95, sides=8, top_radius=0.12, bevel=0.0)
    for k in range(4):
        a = k * math.tau / 4 + 0.4
        beam("roof_seam", p["cord"], (cx + math.cos(a) * (roof_r - 0.07), cy + math.sin(a) * (roof_r - 0.07), 1.05), (cx + math.cos(a) * 0.2, cy + math.sin(a) * 0.2, 1.88), thick=0.04)
    kit.spike(p["bone"], (cx, cy, 1.9), height=0.4, radius=0.06)
    # Chaminé de barris empilhados e escalonados no canto do fundo.
    bx, by = cx - 0.75, cy - 0.85
    for i in range(6):
        cyl("flue_drum", p["rust" if i % 2 else "scrap_dk"], (bx + 0.04 * ((i * 3) % 3 - 1), by + 0.03 * (i % 2), 0.1 + i * 0.4), 0.2, 0.42, sides=8, bevel=0.0)
    smoke(p, (bx, by, 2.55), 0.6, r=0.2)
    # Crânio enorme na frente com fogo na boca.
    skull(p, (cx + 0.95, cy, 0.62), 2.4)
    box("skull_mouth", p["ember"], (cx + 1.3, cy, 0.38), (0.04, 0.3, 0.12), bevel=0.0)
    box("hut_door", p["tar"], (cx + 0.83, cy, 0.1), (0.06, 0.5, 0.45), bevel=0.0)


def h02H_troll_hut():
    p = pal()
    pad(p, rem=(1.3, -1.35), pool=(0.9, 1.3))
    troll_hut(p)
    war_drum(p, (1.15, -0.85, 0.1), 0.28, 0.36)
    war_drum(p, (1.4, 0.8, 0.1), 0.22, 0.28)
    # Fio de ossos e escamas esticado na frente.
    for y in (-1.3, 1.3):
        box("bone_post", p["timber_dk"], (1.55, y, 0.1), (0.07, 0.07, 1.2), bevel=0.0)
    pts = cord_line(p, (1.55, -1.3, 1.2), (1.55, 1.3, 1.2), hang=0.18, n=8)
    for i in range(1, 8):
        kit.spike(p["bone" if i % 2 else "bone_dk"], (pts[i][0], pts[i][1], pts[i][2] - 0.04), height=-0.28 - 0.06 * (i % 3), radius=0.04)


def h05E_trappers_hut():
    """A mesma cabana de troll, atravessando um poço morto: o cabeçote sabotado rompe o piso e vira o alpendre."""
    p = pal()
    pad(p, rem=(1.0, -1.45), pool=(-0.2, 1.4))
    troll_hut(p, center=(-0.55, 0.0), roof_r=1.2)
    # Alpendre: o cabeçote do poço quebrado, com tubo torto e óleo preto.
    cyl("wellhead", p["scrap_dk"], (0.75, 0.0, 0.1), 0.62, 0.32, sides=10, top_radius=0.55, bevel=0.0)
    cyl("well_oil", p["oil"], (0.75, 0.0, 0.4), 0.45, 0.03, sides=10, bevel=0.0)
    beam("broken_pipe", p["rust"], (0.6, 0.1, 0.4), (0.4, -0.15, 1.45), thick=0.17)
    box("pipe_stump", p["tar"], (0.4, -0.15, 1.45), (0.22, 0.22, 0.08), bevel=0.0)
    for a in (0.3, 1.5, 3.3, 4.6):
        box("porch_plank", p["timber"], (0.75 + math.cos(a) * 0.78, math.sin(a) * 0.78, 0.1), (0.5, 0.2, 0.08), bevel=0.0, rot_z=a)
    fire_pit(p, (1.4, -0.7, 0.1), r=0.3, size=0.3)
    # Redes secando num quadro alto ao lado do fogo de piche; estacas de isca ao longo da cerca.
    for y in (0.7, 1.7):
        box("net_post", p["timber_dk"], (1.45, y - 0.2, 0.1), (0.09, 0.09, 1.9), bevel=0.0)
    net(p, (1.45, 0.5, 1.95), (1.45, 1.5, 1.95), drop=0.9)
    fence_line(p, (-1.65, -1.7), (1.4, -1.7), 6, 0.7, rail=False)
    for x in (-1.2, -0.3, 0.6):
        box("bait", p["hide_dk"], (x, -1.7, 0.78), (0.14, 0.14, 0.14), bevel=0.0)
    drum(p, (-1.5, 1.55, 0.1))


def h06D_forest_trappers_hole():
    """O covil é a boca de um poço velho tomado pelo mato: silhueta de fosso, teto de casca e rede, fogo de piche baixo."""
    p = pal()
    pad(p, rem=(1.2, 1.4), pool=(1.35, -1.3))
    cyl("pit_rim", p["char"], (0, 0, 0.1), 1.62, 0.4, sides=10, top_radius=1.4, bevel=0.0)
    cyl("pit_rim_cap", p["scrap_dk"], (0, 0, 0.5), 1.38, 0.05, sides=10, bevel=0.0)
    cyl("pit_mouth", p["oil"], (0, 0, 0.53), 1.1, 0.03, sides=10, bevel=0.0)
    for a in (0.2, 1.4, 2.5, 3.9, 5.2):
        box("rim_stone", p["scrap_dk"], (math.cos(a) * 1.5, math.sin(a) * 1.5, 0.1), (0.4, 0.35, 0.6), bevel=0.03, taper=0.7, taper_y=0.8, rot_z=a)
    # Teto de casca e mato inclinado só sobre a metade do fundo.
    for x, y, hh in ((-1.55, -1.15, 1.9), (-1.55, 1.15, 1.9), (-0.7, -1.2, 1.5), (-0.7, 1.2, 1.5)):
        box("roof_post", p["timber_dk"], (x, y, 0.1), (0.1, 0.1, hh), bevel=0.0)
    for i, y0 in enumerate((-1.3, -0.45, 0.4)):
        slab("bark", p["timber_dk" if i % 2 == 0 else "timber"], [(-1.7, y0, 2.0), (-1.7, y0 + 0.9, 2.0), (-0.5, y0 + 0.9, 1.6), (-0.5, y0, 1.6)], thick=0.07)
    for i, (x, y) in enumerate(((-1.4, -0.6), (-1.1, 0.5), (-0.9, -0.3))):
        box("brush", p["brush"], (x, y, 1.85 - 0.12 * i), (0.5, 0.45, 0.18), bevel=0.03, rot_z=0.6 * i)
    # Rede secando no quadro da frente, fogo de piche na boca do poço, iscas penduradas.
    for y in (-1.2, 1.2):
        box("net_post", p["timber_dk"], (1.0, y, 0.1), (0.09, 0.09, 1.9), bevel=0.0)
    net(p, (1.0, -1.2, 2.0), (1.0, 1.2, 2.0), drop=0.8, cells=6)
    fire_pit(p, (0.7, 0.2, 0.53), r=0.32, size=0.34)
    pts = cord_line(p, (-0.7, -1.2, 1.4), (-0.7, 1.2, 1.4), hang=0.1, n=4)
    for i in (1, 3):
        cyl("carcass", p["hide_dk"], (pts[i][0], pts[i][1], pts[i][2] - 0.5), 0.13, 0.4, sides=6, top_radius=0.2, bevel=0.0)
        for s in (-1, 1):
            kit.spike(p["bone"], (pts[i][0], pts[i][1] + s * 0.14, pts[i][2] - 0.2), height=-0.2, radius=0.03, lean=(0, s * 0.1))
    beam("old_pipe", p["rust"], (0.3, -0.7, 0.5), (0.55, -0.9, 2.1), thick=0.14)
    skull(p, (1.2, 0.0, 1.0), 1.4)


# ---------------------------------------------------------------------------------------------------------
# Torres e postos avulsos
# ---------------------------------------------------------------------------------------------------------


def o000_anti_air_tower():
    """Aranha de perfuração: treliça de dois lances com plataforma de couro costurado, arpões, bexigas de piche e cesto de fogo."""
    p = pal()
    box("pad", p["mud"], (0, 0, 0), (2.6, 2.6, 0.1), bevel=0.03)
    box("oil_pool", p["oil"], (0.9, 0.85, 0.1), (0.7, 0.6, 0.012), bevel=0.0, rot_z=0.4)
    beam("charred_log", p["char"], (-1.1, -1.1, 0.17), (-0.6, -0.9, 0.2), thick=0.15)
    box("footing", p["scrap_dk"], (0, 0, 0.1), (1.9, 1.9, 0.22), bevel=0.03, taper=0.88, taper_y=0.88)
    kit.derrick(p["rust"], p["rust_dk"], None, (0, 0, 0.32), base=1.5, top=0.85, height=1.9, lean=(0.1, 0.0))
    # Plataforma de couro costurado sobre o primeiro lance.
    box("platform", p["timber"], (0.1, 0, 2.2), (1.2, 1.2, 0.1), bevel=0.02)
    slab("hide_apron", p["hide"], [(0.7, -0.6, 2.28), (0.7, 0.6, 2.28), (1.1, 0.7, 1.75), (1.1, -0.7, 1.75)], thick=0.04, toward=(1, 0, 0))
    cord_line(p, (0.72, -0.5, 2.1), (0.72, 0.5, 1.9), n=4)
    kit.derrick(p["rust_dk"], p["tar"], None, (0.1, 0, 2.3), base=0.75, top=0.3, height=1.6, lean=(-0.12, 0.1))
    # Cesto de fogo no alto (a marca de fumaça), preso num poste torto.
    beam("basket_pole", p["timber_dk"], (-0.02, 0.1, 3.8), (-0.02, 0.1, 4.0), thick=0.08)
    cyl("basket", p["scrap_dk"], (-0.02, 0.1, 3.95), 0.2, 0.22, sides=8, top_radius=0.35, bevel=0.0)
    fire(p, (-0.02, 0.1, 4.15), 0.4)
    # Arpões com pesos de válvula apontando para cima e para fora, e bexigas de piche penduradas.
    kit.begin_part("anim_harpoons")
    for i, y in enumerate((-0.45, 0.0, 0.45)):
        beam("harpoon", p["timber_dk"], (0.5, y, 2.3), (1.2 + 0.1 * i, y * 1.8, 3.3 + 0.15 * i), thick=0.06)
        kit.spike(p["scrap"], (1.2 + 0.1 * i, y * 1.8, 3.3 + 0.15 * i), height=0.3, radius=0.07, lean=(0.1, 0.0))
        cyl("valve_weight", p["rust_dk"], (0.75 + 0.05 * i, y * 1.2, 2.55), 0.07, 0.1, sides=6, bevel=0.0)
    kit.end_part()
    for y in (-0.8, 0.8):
        beam("bladder_cord", p["cord"], (0.1, y * 0.7, 2.25), (0.15, y, 1.95), thick=0.03)
        dome("tar_bladder", p["tar"], (0.15, y, 1.55), 0.24, squash=1.5, sides=8)
    beam("crooked_diag", p["timber_dk"], (-0.9, -0.8, 0.2), (0.0, 0.0, 2.1), thick=0.09)
    drum(p, (1.0, -0.9, 0.1))


def h02P_falcon_clan_encampment():
    """Torre de falcoaria de couro: plataforma alta sobre mastro de tubos, cesto de fogo alto que chama as wyverns."""
    p = pal()
    pad(p, rem=(-1.45, 1.3), pool=(1.4, -1.3))
    # Mastro central de tubos e quatro pernas abertas sustentando a plataforma.
    pipe_stack(p, (-0.4, 0, 0.1), 2.6, r=0.2)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        beam("leg", p["timber_dk"], (-0.4 + sx * 1.0, sy * 0.95, 0.1), (-0.4 + sx * 0.7, sy * 0.65, 2.45), thick=0.11)
    beam("brace", p["timber"], (0.6, -0.95, 0.4), (-1.1, 0.65, 2.0), thick=0.06)
    beam("brace", p["timber"], (0.6, 0.95, 0.4), (-1.1, -0.65, 2.0), thick=0.06)
    box("platform", p["timber"], (-0.4, 0, 2.45), (1.9, 1.9, 0.12), bevel=0.02)
    slab("hide_floor", p["hide"], [(-1.3, -0.9, 2.6), (-1.3, 0.9, 2.6), (0.5, 0.9, 2.6), (0.5, -0.9, 2.6)], thick=0.05)
    for y in (-0.9, 0.9):
        box("rail", p["timber_dk"], (-0.4, y, 2.6), (1.9, 0.07, 0.3), bevel=0.0)
    for s in (-1, 1):
        kit.horn(p["bone"], (0.5, s * 0.6, 2.6), (0.7, s * 0.7), length=0.8, radius=0.08)
    # Cesto de fogo no poste alto: a marca alta da raça.
    box("fire_pole", p["timber_dk"], (-1.1, 0.0, 2.6), (0.1, 0.1, 1.0), bevel=0.0)
    cyl("fire_basket", p["scrap_dk"], (-1.1, 0, 3.55), 0.2, 0.22, sides=8, top_radius=0.42, bevel=0.0)
    cyl("fire_ember", p["ember"], (-1.1, 0, 3.75), 0.36, 0.03, sides=8, bevel=0.0)
    fire(p, (-1.1, 0, 3.77), 0.42)
    # Rede de captura pendurada, troféus de caça no aramado e a rampa de couro.
    for y in (-1.5, -0.4):
        box("net_post", p["timber_dk"], (1.4, y, 0.1), (0.09, 0.09, 1.7), bevel=0.0)
    net(p, (1.4, -1.5, 1.8), (1.4, -0.4, 1.8), drop=1.0)
    beam("ramp", p["timber"], (1.5, 0.5, 0.1), (0.5, 0.5, 2.5), thick=0.2)
    for i in range(5):
        box("ramp_step", p["timber_dk"], (1.45 - 0.2 * i, 0.5, 0.35 + 0.45 * i), (0.28, 0.4, 0.05), bevel=0.0)
    fence_line(p, (-1.65, -1.65), (1.5, -1.65), 6, 0.5, rail=False)
    skull(p, (1.5, 1.2, 0.5), 1.0)
    drum(p, (-1.4, -1.3, 0.1))


def h02I_orcish_siege_factory():
    """Pátio de desmanche: galpão aberto com a catapulta sendo costurada, a roda de tração de poço como guindaste, fila de caldeirões e o fogo de barris."""
    p = pal()
    pad(p, rem=(1.25, 1.35), pool=(0.9, -1.3))
    # Galpão com teto de couro só sobre a metade do fundo.
    for x, y, hh in ((-1.6, -1.4, 1.95), (-1.6, 1.4, 1.95), (-0.85, -1.4, 1.75), (-0.85, 1.4, 1.75)):
        box("shed_post", p["timber_dk"], (x, y, 0.1), (0.12, 0.12, hh), bevel=0.0)
    roof = box("shed_roof", p["hide"], (-1.2, 0, 1.95), (1.1, 3.1, 0.1), bevel=0.0)
    for v in roof.data.vertices:
        v.co.z -= 0.2 * (v.co.x + 1.2) / 0.55
    for y in (-0.9, 0.0, 0.9):
        beam("roof_seam", p["cord"], (-1.75, y, 2.07), (-0.65, y, 1.77), thick=0.04)
    # A catapulta em costura: diagonais tortas, eixo, rodas de carrinho de mina e o braço com caldeirão.
    box("cat_frame", p["timber"], (-0.35, 0, 0.35), (1.3, 0.9, 0.18), bevel=0.02)
    for s in (-1, 1):
        cyl("cat_wheel", p["scrap_dk"], (-0.35, s * 0.55, 0.45), 0.3, 0.1, sides=8, bevel=0.0, rot=("X", math.radians(90)))
        beam("cat_diag", p["timber_dk"], (-0.85, s * 0.35, 0.45), (-0.1, s * 0.12, 1.55), thick=0.1)
    beam("cat_arm", p["timber"], (-0.95, 0.0, 0.7), (0.5, 0.0, 1.75), thick=0.12)
    cauldron(p, (0.5, 0.0, 1.55), r=0.26, flame=False, legs=False)
    # Guindaste: roda de tração de poço num cavalete lateral, corrente e gancho com barril.
    wy = 1.55
    for sx in (-1, 1):
        beam("crane_leg", p["rust_dk"], (0.5 + sx * 0.5, wy, 0.1), (0.5, wy, 1.75), thick=0.1)
    wc = (0.5, wy - 0.05, 1.75)
    n = 10
    for i in range(n):
        a0, a1 = i * math.tau / n, (i + 1) * math.tau / n
        beam("wheel_rim", p["scrap_dk"], (wc[0] + math.cos(a0) * 0.62, wc[1], wc[2] + math.sin(a0) * 0.62), (wc[0] + math.cos(a1) * 0.62, wc[1], wc[2] + math.sin(a1) * 0.62), thick=0.1)
        if i % 2 == 0:
            beam("wheel_spoke", p["rust"], wc, (wc[0] + math.cos(a0) * 0.62, wc[1], wc[2] + math.sin(a0) * 0.62), thick=0.06)
    cyl("wheel_hub", p["rust_dk"], (wc[0], wc[1] - 0.1, wc[2]), 0.12, 0.2, sides=8, bevel=0.0, rot=("X", math.radians(90)))
    cord_line(p, (0.5 + 0.62, wy - 0.05, 1.75), (1.12, wy - 0.4, 0.9), n=2, tone="char")
    drum(p, (1.12, wy - 0.4, 0.45), "rust_dk")
    # Fila de caldeirões esperando o braço, barris roubados e o fogo aberto onde se queimam as pontas.
    for y in (-1.25, -0.65):
        cauldron(p, (1.25, y, 0.1), r=0.3, flame=False, legs=False)
    fire_pit(p, (0.95, 0.35, 0.1), r=0.42, size=0.42)
    barrel_stack(p, (-1.2, 0.95, 0.1))
    drum(p, (1.3, 1.1, 0.1), "scrap_dk", lying=True)
    cyl("barrel_end", p["rust_dk"], (0.6, 0.9, 0.1), 0.15, 0.03, sides=8, bevel=0.0)


def h02N_serpent_rock():
    """Rocha de óleo coroada por cano de poço derretido e torcido em boca de zigue-zague, cuspindo piche em chamas."""
    p = pal()
    pad(p, rem=(-1.4, -1.35), pool=(1.4, 1.2))
    box("rock_base", p["char"], (-0.3, 0, 0.1), (2.1, 1.9, 0.6), bevel=0.06, taper=0.7, taper_y=0.7, rot_z=0.3)
    box("rock_mid", p["scrap_dk"], (-0.35, 0.1, 0.65), (1.2, 1.1, 0.5), bevel=0.06, taper=0.7, taper_y=0.7, rot_z=-0.4)
    for x, y, rz in ((0.9, -0.8, 0.6), (0.8, 0.95, 1.1), (-1.15, 0.9, 0.2), (-1.2, -0.9, 0.9)):
        box("rock_chunk", p["char"], (x, y, 0.1), (0.5, 0.45, 0.45), bevel=0.04, taper=0.6, taper_y=0.6, rot_z=rz)
    # O cano: zigue-zague grosso e alto (a silhueta), de tubo derretido; a cabeça de boca aberta aponta para +x.
    zz = [(-0.3 + 0.57 * 0.95 * sgn, 0.82 * 0.95 * sgn + 0.1, 1.0 + 0.55 * i) for i, sgn in enumerate((-1, 1, -1, 1, -1))]
    for i, (u, v) in enumerate(itertools.pairwise(zz)):
        tube(p["rust" if i % 2 == 0 else "rust_dk"], u, v, 0.2)
        cyl("pipe_knee", p["scrap_dk"], (v[0], v[1], v[2] - 0.2), 0.27, 0.4, sides=8, bevel=0.0)
    hx, hy, hz = zz[-1]
    box("head", p["rust"], (hx + 0.35, hy, hz + 0.05), (0.95, 0.62, 0.3), bevel=0.03, taper=0.75, taper_y=0.9)
    box("jaw_low", p["rust_dk"], (hx + 0.45, hy, hz - 0.3), (0.8, 0.52, 0.2), bevel=0.03, taper=0.7, taper_y=0.9)
    box("head_back", p["rust"], (hx - 0.1, hy, hz - 0.3), (0.32, 0.5, 0.6), bevel=0.02)
    for y in (-0.18, 0.0, 0.18):
        kit.spike(p["bone"], (hx + 1.0, hy + y, hz + 0.05), height=-0.3, radius=0.05)
        kit.spike(p["bone"], (hx + 1.05, hy + y, hz - 0.3), height=0.3, radius=0.05)
    box("mouth_fire", p["ember"], (hx + 0.9, hy, hz - 0.28), (0.22, 0.34, 0.26), bevel=0.0)
    fire(p, (hx + 1.0, hy, hz - 0.28), 0.3)
    # Bolas de piche em chamas já caídas na lama e as válvulas de alívio na base.
    for x, y, s in ((1.3, 0.5, 0.26), (1.0, -0.55, 0.22), (1.55, -0.1, 0.18)):
        dome("tar_clod", p["tar"], (x, y, 0.1), 0.22, squash=0.7, sides=7)
        fire(p, (x, y, 0.28), s)
    for y in (-1.0, 1.0):
        cyl("burst_valve", p["scrap_dk"], (0.5, y, 0.1), 0.12, 0.35, sides=8, bevel=0.0)
        cyl("valve_wheel", p["rust"], (0.5, y, 0.45), 0.2, 0.04, sides=8, bevel=0.0)
    barrel_stack(p, (-1.3, -0.4, 0.1))


BUILDINGS = {
    "h029": h029_fighters_hall,
    "h02U": h02U_advanced_fighters_hall,
    "h031": h031_superior_fighters_hall,
    "o000": o000_anti_air_tower,
    "h07Q": h07Q_blood_shaman_tent,
    "h02R": h02R_ceremonial_totem,
    "h036": h036_defensive_kodo_farm,
    "h07Z": h07Z_endurance_totem,
    "h02P": h02P_falcon_clan_encampment,
    "h06D": h06D_forest_trappers_hole,
    "h07Y": h07Y_healing_totem,
    "h06I": h06I_infostealers_place,
    "h02K": h02K_kodo_farm,
    "h02O": h02O_legendary_totem,
    "h035": h035_melee_kodo_farm,
    "h02I": h02I_orcish_siege_factory,
    "h02N": h02N_serpent_rock,
    "h02B": h02B_shamanic_tent,
    "h092": h092_spellbreaker_kodo_farm,
    "h07X": h07X_stasis_totem,
    "h05E": h05E_trappers_hut,
    "h02H": h02H_troll_hut,
}


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["all"]
    names = list(BUILDINGS) if args[0] == "all" else [args[0]]
    out_dir = game_paths.out_arg(args, "--out", "buildings", "orc")
    render_dir = args[args.index("--render") + 1] if "--render" in args else ""
    for name in names:
        kit.build(name, out_dir, render_dir, make=BUILDINGS[name], views=(("front", -35.0),))


if __name__ == "__main__":
    main()
