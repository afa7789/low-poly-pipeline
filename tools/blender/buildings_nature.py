"""Prédios da raça Nature modelados por script (redesenho de reports/design/race-nature.md): um GLB por prédio.

Uso:
    blender -b --factory-startup --python tools/blender/buildings_nature.py -- <id|all> [--out DIR] [--render DIR]

A floresta que metaboliza o óleo: casca viva e seca, ferrugem doce por cima (roupa, nunca corpo), musgo de
trincheira, pedra só como esqueleto em fissura e seiva sempre dentro de um vaso. Silhueta: triângulo invertido
enraizado (copa estreita, ombros largos, base num leque de raízes). Regra da raça em todo prédio: um cogumelo-
lanterna (ou a fenda de seiva) como único ponto de luz, e o cano é sempre uma raiz grossa (raiz-tubo), nunca
tubo de metal. Nada de chaminé, engrenagem ou fumaça. Pegada ~3,5 x 3,5 centrada na origem, a frente virada
para +x; o jogo normaliza o tamanho, põe o prédio no plinto do time e desenha a bandeira.
"""

import itertools
import math
import os
import sys

import bmesh
from mathutils import Euler, Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import map_castles as kit
from map_castles import box, cyl, dome, mat, prism, ring

Z0 = 0.1  # topo da laje de lama


def pal():
    return {
        "bark": mat("living_bark", 0x9A7650),
        "bark_dk": mat("bark_dark", 0x6E5236),
        "bark_lt": mat("bark_light", 0xBC9868),
        "moss": mat("trench_moss", 0x8CA854),
        "moss_dk": mat("trench_moss_dark", 0x6C8741),
        "moss_lt": mat("trench_moss_light", 0xA9C06E),
        "rust": mat("sweet_rust", 0xC2703F),
        "rust_dk": mat("sweet_rust_dark", 0x93512D),
        "stone": mat("quarried_stone", 0xA8A292),
        "mud": mat("mud", 0x6E5B44),
        "mud_dk": mat("mud_dark", 0x3A2E22),
        "dark": mat("hollow_dark", 0x2A2018),
        "cream": mat("cap_stalk", 0xEEE4C2),
        "thorn": mat("thorn_bone", 0xD8C79B),
        "web": mat("web_silk", 0xEAE5D2),
        "lantern": mat("lantern_cap", 0xFFA030, emit=1.6),
        "sap": mat("sap_amber", 0xE8922A, emit=1.2),
        "sulfur": mat("sulfur_stone", 0xD8D232, emit=1.6),
    }


# ---------------------------------------------------------------------------------------------------------
# Kit da raça: casca, raiz, placa de ferrugem, espinho, cogumelo-lanterna, raiz-tubo
# ---------------------------------------------------------------------------------------------------------


def pad(p, size=3.5):
    box("pad", p["mud"], (0, 0, 0), (size, size, 0.1), bevel=0.03)


def root(name, material, a, b, r0, r1, sides=6, bevel=0.0):
    """Sólido facetado afunilado de a até b (raiz, galho, espinho, tronco inclinado)."""
    a, b = Vector(a), Vector(b)
    d = b - a
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=r0, radius2=max(r1, 1e-3), depth=d.length)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, d.length / 2))
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=d.to_track_quat("Z", "Y").to_matrix())
    bmesh.ops.translate(bm, verts=bm.verts, vec=a)
    return kit._finish(bm, name, material, bevel)


def slab(name, material, center, size, rx=0.0, ry=0.0, rz=0.0, bevel=0.02, taper=1.0):
    """Caixa inclinada, com `center` no meio da caixa (placa encostada, porta aberta, prateleira)."""
    ob = box(name, material, (0, 0, 0), size, bevel=bevel, taper=taper)
    ob.data.transform(Matrix.Translation((0, 0, -size[2] / 2)))
    ob.data.transform(Matrix.Translation(center) @ Euler((rx, ry, rz)).to_matrix().to_4x4())
    return ob


def tube(p, tone, pts, r0, r1=None, sides=6):
    """Raiz-tubo: segmentos grossos por uma lista de pontos, com um nó em cada joelho."""
    r1 = r0 if r1 is None else r1
    n = len(pts) - 1
    for i in range(n):
        ra, rb = r0 + (r1 - r0) * i / n, r0 + (r1 - r0) * (i + 1) / n
        root("tube", p[tone], pts[i], pts[i + 1], ra, rb, sides=sides)
        if i:
            box("tube_knot", p[tone], (pts[i][0], pts[i][1], pts[i][2] - ra * 0.8), (ra * 1.9, ra * 1.9, ra * 1.9), bevel=0.0)


def trunk(p, pos, r0, r1, h, tone="bark", sides=8, ridges=0):
    """Tronco afunilado e facetado, com cristas de casca verticais."""
    x, y, z = pos
    cyl("trunk", p[tone], pos, r0, h, sides=sides, top_radius=r1, bevel=0.03)
    for i in range(ridges):
        a = i * math.tau / ridges + 0.25
        c, s = math.cos(a), math.sin(a)
        root("ridge", p["bark_dk"], (x + c * r0 * 0.97, y + s * r0 * 0.97, z + 0.04), (x + c * r1 * 0.97, y + s * r1 * 0.97, z + h - 0.06), 0.075, 0.045, sides=4)


def root_fan(p, center, r_in, length, angles, thick=0.2, h=0.35, tone="bark_dk", skirt=True):
    """Leque de raízes largas e baixas, enterradas na lama: o peso fica no tornozelo. skirt põe o musgo da base."""
    cx, cy = center
    if skirt:
        cyl("moss_skirt", p["moss_dk"], (cx, cy, Z0), r_in * 1.05, 0.2, sides=9, top_radius=r_in * 0.9, bevel=0.03)
    for a in angles:
        c, s = math.cos(a), math.sin(a)
        root("root", p[tone], (cx + c * r_in, cy + s * r_in, Z0 + h), (cx + c * (r_in + length), cy + s * (r_in + length), Z0 - 0.02), thick, thick * 0.3, sides=5)


def fan_angles(count, start=0.0):
    return [start + i * math.tau / count for i in range(count)]


def cap(p, pos, r=0.24, stalk=0.3):
    """Cogumelo-lanterna: haste creme e chapéu emissivo. O único ponto de luz da raça."""
    x, y, z = pos
    cyl("cap_stalk", p["cream"], pos, r * 0.3, stalk, sides=6, top_radius=r * 0.22, bevel=0.0)
    dome("cap_head", p["lantern"], (x, y, z + stalk - 0.02), r, squash=0.7, sides=8)
    ring("cap_skirt", p["cream"], (x, y, z + stalk - 0.05), r * 0.8, 0.05, thick=0.0, sides=8)


def cap_hung(p, pos, r=0.2):
    """Cogumelo-lanterna pendurado: cordão da haste de cima e o bulbo aceso embaixo (pos = ponto de prender)."""
    x, y, z = pos
    cyl("cap_cord", p["bark_dk"], (x, y, z - 0.25), 0.025, 0.25, sides=4, bevel=0.0)
    cyl("cap_bulb", p["lantern"], (x, y, z - 0.25 - r * 1.3), r * 0.4, r * 1.3, sides=8, top_radius=r, bevel=0.0)
    cyl("cap_lid", p["cream"], (x, y, z - 0.27), r * 1.05, 0.05, sides=8, bevel=0.0)


def thorn(p, pos, h, r=0.09, lean=(0.0, 0.0), tone="rust"):
    x, y, z = pos
    root("thorn", p[tone], pos, (x + lean[0], y + lean[1], z + h), r, 0.0, sides=4)


def thorn_crown(p, center, radius, count, h, z, tone="rust", r=0.1):
    """Coroa vazada de espinhos de ferrugem: alternam alto e baixo, abrindo para fora."""
    cx, cy = center
    for i in range(count):
        a = i * math.tau / count
        c, s = math.cos(a), math.sin(a)
        hh = h if i % 2 == 0 else h * 0.65
        thorn(p, (cx + c * radius, cy + s * radius, z), hh, r=r, lean=(c * 0.18, s * 0.18), tone=tone)


def moss(p, x, y, z, r=0.3, tone="moss", squash=0.5):
    dome("moss_tuft", p[tone], (x, y, z), r, squash=squash, sides=7)


def plate(p, pos, size=(0.9, 0.08, 0.8), rz=0.0, lean=0.0, tone="rust"):
    """Placa de ferrugem doce: roupa sobre a casca. pos = centro; lean inclina o topo (ry)."""
    slab("rust_plate", p[tone], pos, size, ry=lean, rz=rz, bevel=0.02)
    slab("rust_edge", p["rust_dk"], (pos[0], pos[1], pos[2]), (size[0] * 0.98, size[1] * 0.5, size[2] * 0.12), ry=lean, rz=rz, bevel=0.0)


def flask(p, pos, h=0.26, r=0.1):
    """Frasco de seiva arrolhado: a seiva sempre dentro de um vaso."""
    x, y, z = pos
    cyl("flask", p["sap"], pos, r, h, sides=6, top_radius=r * 0.8, bevel=0.0)
    cyl("flask_stopper", p["cream"], (x, y, z + h), r * 0.4, 0.07, sides=6, bevel=0.0)


def cocoon(p, x, y, r, h, z=Z0 - 0.05):
    """Casulo de casca costurada: dois troncos de cone empilhados, meio enterrado na lama."""
    cyl("cocoon_low", p["bark"], (x, y, z), r * 0.8, h * 0.42, sides=7, top_radius=r, bevel=0.03)
    cyl("cocoon_up", p["bark_lt"], (x, y, z + h * 0.42), r, h * 0.58, sides=7, top_radius=r * 0.22, bevel=0.03)
    ring("cocoon_stitch", p["bark_dk"], (x, y, z + h * 0.4), r * 0.99, 0.07, thick=0.02, sides=7)
    ring("cocoon_stitch", p["bark_dk"], (x, y, z + h * 0.72), r * 0.7, 0.06, thick=0.02, sides=7)


def shingles(p, cx, cy, z, half_w, rise, length, rz=0.0, rows=4, tones=("bark_dk", "bark")):
    """Telhas de casca sobrepostas nas duas águas de um telhado (cumeeira ao longo de y, girada por rz)."""
    slope = math.atan2(rise, half_w)
    seg = math.hypot(half_w, rise) / rows * 1.35
    cr, sr = math.cos(rz), math.sin(rz)
    for side in (-1, 1):
        for k in range(rows):
            t = (k + 0.55) / rows
            u = side * (half_w * t + math.sin(slope) * 0.04)
            zz = z + rise * (1 - t) + math.cos(slope) * 0.04
            tone = tones[k % 2]
            slab("shingle", p[tone], (cx + u * cr, cy + u * sr, zz), (seg, length, 0.06), ry=side * slope, rz=rz, bevel=0.01)


def web(p, a, b, thick=0.04):
    """Fio de teia: opaco e grosso, nunca linha fina."""
    kit.beam("web", p["web"], a, b, thick=thick)


# ---------------------------------------------------------------------------------------------------------
# Aranhas: Clutch -> Nest -> Hatchery (casulos; o mesmo casulo cresce até partir)
# ---------------------------------------------------------------------------------------------------------


def h002_clutch():
    """Ninhada: casulos de casca meio enterrados, placas de ferrugem encostadas de escudo e um cogumelo no maior."""
    p = pal()
    pad(p)
    for x, y, r, h in ((-0.25, 0.0, 0.72, 1.55), (0.3, -0.95, 0.52, 1.05), (0.3, 0.95, 0.54, 1.1), (-1.05, -0.75, 0.46, 0.9), (-1.05, 0.8, 0.43, 0.85), (0.95, 0.1, 0.32, 0.55)):
        cocoon(p, x, y, r, h)
    cap(p, (-0.25, 0.0, Z0 + 1.45), r=0.3, stalk=0.3)
    plate(p, (1.25, -0.8, Z0 + 0.5), (0.1, 0.9, 1.0), rz=-0.35, lean=-0.28)
    plate(p, (1.2, 0.85, Z0 + 0.45), (0.1, 0.8, 0.9), rz=0.35, lean=-0.28)
    for x, y in ((0.85, -1.3), (-0.4, 1.45), (-1.4, 0.0)):
        moss(p, x, y, Z0, r=0.34)
    root_fan(p, (-0.25, 0.0), 0.5, 0.9, fan_angles(5, 0.3), thick=0.15, h=0.1, skirt=False)


def h00q_nest():
    """Ninho: poço de raízes até a linha da seiva, casulos empilhados dentro, teia grossa entre os bordos e dois postes com cogumelo."""
    p = pal()
    pad(p)
    cyl("pit_wall", p["bark_dk"], (0, 0, Z0), 1.62, 0.5, sides=10, top_radius=1.5, bevel=0.03)
    cyl("pit_floor", p["mud_dk"], (0, 0, Z0), 1.28, 0.53, sides=10, bevel=0.0)
    for i in range(10):
        a, b = i * math.tau / 10, (i + 1) * math.tau / 10
        root("rim", p["bark"], (math.cos(a) * 1.45, math.sin(a) * 1.45, Z0 + 0.58), (math.cos(b) * 1.45, math.sin(b) * 1.45, Z0 + 0.58), 0.17, 0.17, sides=5)
    cocoon(p, -0.2, 0.0, 0.62, 1.6, z=Z0 + 0.5)
    cocoon(p, 0.45, -0.6, 0.46, 1.0, z=Z0 + 0.5)
    cocoon(p, 0.45, 0.6, 0.46, 1.0, z=Z0 + 0.5)
    cocoon(p, -0.75, -0.6, 0.38, 0.8, z=Z0 + 0.5)
    cocoon(p, -0.75, 0.6, 0.38, 0.75, z=Z0 + 0.5)
    # Dois postes de raiz na boca do ninho, cada um com seu cogumelo; a teia nasce deles.
    tops = []
    for s in (-1, 1):
        root("post", p["bark_dk"], (1.5, s * 0.8, Z0), (1.35, s * 0.62, Z0 + 2.0), 0.17, 0.1, sides=5)
        cap(p, (1.35, s * 0.62, Z0 + 2.0), r=0.24, stalk=0.25)
        tops.append((1.35, s * 0.62, Z0 + 2.05))
    anchors = [(-1.3, 0.0, Z0 + 0.9), (-0.9, -1.0, Z0 + 0.7), (-0.9, 1.0, Z0 + 0.7)]
    for t in tops:
        for a in anchors:
            web(p, t, a)
    web(p, tops[0], tops[1], 0.05)
    web(p, anchors[1], anchors[2])
    root_fan(p, (0, 0), 1.45, 0.3, fan_angles(8, 0.4), thick=0.15, h=0.3, skirt=False)


def h00r_hatchery():
    """Maternidade: casulo-mestre partido ao meio, o miolo à vista por uma fenda de seiva e uma tampa de ferrugem na metade ainda selada."""
    p = pal()
    pad(p)
    cocoon(p, -0.05, -0.6, 0.95, 2.25)
    cocoon(p, -0.05, 0.6, 0.95, 2.45)
    # A fenda: faixa estreita e vertical de seiva no vale entre as metades, virada para a lane.
    box("sap_slit", p["sap"], (0.52, 0.0, Z0 + 0.25), (0.1, 0.16, 1.75), bevel=0.0)
    box("slit_lip_l", p["bark_dk"], (0.5, -0.17, Z0 + 0.2), (0.08, 0.07, 1.9), bevel=0.0)
    box("slit_lip_r", p["bark_dk"], (0.5, 0.17, Z0 + 0.2), (0.08, 0.07, 1.9), bevel=0.0)
    # Tampa de ferrugem deitada na metade selada (-y), presa por cordas de raiz.
    plate(p, (0.0, -0.6, Z0 + 2.2), (1.3, 1.6, 0.12), rz=0.1, lean=0.12)
    for s in (-1, 1):
        root("lid_strap", p["bark_dk"], (0.62, -0.6 + s * 0.55, Z0 + 2.1), (0.7, -0.6 + s * 0.55, Z0 + 0.35), 0.06, 0.06, sides=4)
    # Cria recém-saída: casulinhos abertos na frente e um cogumelo pequeno.
    for x, y, r, h in ((1.15, -0.95, 0.3, 0.5), (1.2, 0.9, 0.34, 0.6), (0.95, 1.35, 0.24, 0.4)):
        cocoon(p, x, y, r, h)
    cap(p, (1.2, 0.9, Z0 + 0.5), r=0.2, stalk=0.2)
    root_fan(p, (0, 0), 1.0, 0.75, fan_angles(7, 0.5)[1:], thick=0.17, h=0.2, skirt=False)
    moss(p, -1.4, 0.4, Z0, r=0.4)


# ---------------------------------------------------------------------------------------------------------
# Furbolgs: Hut -> Abode | Enigma (cabana de casca costurada sobre estrutura de raiz)
# ---------------------------------------------------------------------------------------------------------


def cabin(p, x, y, sx, sy, wall_h, roof_h, roof_tone="bark_lt", shingle_tones=("bark_dk", "bark")):
    """Cabana de casca costurada, meio afundada na lama, telhado de duas águas com telhas de casca."""
    box("cabin_sill", p["bark_dk"], (x, y, Z0 - 0.1), (sx + 0.16, sy + 0.16, 0.3), bevel=0.04)
    box("cabin", p["bark"], (x, y, Z0 + 0.1), (sx, sy, wall_h), bevel=0.04)
    for i in range(5):
        yy = y - sy / 2 + (i + 0.5) * sy / 5
        box("seam", p["bark_dk"], (x + sx / 2 + 0.01, yy, Z0 + 0.12), (0.03, 0.05, wall_h - 0.04), bevel=0.0)
    for s in (-1, 1):
        for fx in (-1, 1):
            root("post", p["bark_dk"], (x + fx * sx / 2, y + s * sy / 2, Z0 - 0.05), (x + fx * sx / 2, y + s * sy / 2, Z0 + wall_h + 0.3), 0.12, 0.09, sides=5)
    top = Z0 + 0.1 + wall_h
    prism("cabin_roof", p[roof_tone], (x, y, top), (sx + 0.5, sy + 0.4, roof_h), ridge=0.5, bevel=0.02)
    shingles(p, x, y, top, (sx + 0.5) / 2, roof_h, sy + 0.44, rows=4, tones=shingle_tones)
    kit.beam("ridge", p["bark_dk"], (x, y - sy / 2 - 0.25, top + roof_h), (x, y + sy / 2 + 0.25, top + roof_h), thick=0.1)


def door(p, x, y, w, h):
    box("door", p["dark"], (x + 0.02, y, Z0 + 0.05), (0.08, w, h), bevel=0.0)
    box("door_lintel", p["bark_dk"], (x + 0.04, y, Z0 + 0.05 + h), (0.14, w + 0.24, 0.1), bevel=0.0)
    for s in (-1, 1):
        box("door_jamb", p["bark_dk"], (x + 0.04, y + s * (w / 2 + 0.06), Z0 + 0.05), (0.14, 0.1, h), bevel=0.0)


def h00y_hut():
    """Cabana de seiva: a menor das três, baixa e larga, um cogumelo no portão e o cabaço de seiva à porta."""
    p = pal()
    pad(p)
    cabin(p, -0.1, 0.0, 2.0, 2.4, 0.85, 0.75)
    plate(p, (0.5, -0.55, Z0 + 1.5), (0.7, 0.9, 0.07), rz=0.0, lean=0.54, tone="rust")
    door(p, 0.9, 0.0, 0.6, 0.75)
    post_x, post_y = 1.25, 0.8
    root("lantern_post", p["bark_dk"], (post_x, post_y, Z0 - 0.02), (post_x, post_y, Z0 + 1.1), 0.08, 0.06, sides=5)
    cap(p, (post_x, post_y, Z0 + 1.1), r=0.24, stalk=0.2)
    flask(p, (1.25, -0.55, Z0), h=0.38, r=0.17)
    flask(p, (1.4, -0.85, Z0), h=0.24, r=0.12)
    moss(p, -1.3, -1.0, Z0 + 0.2, r=0.45)
    moss(p, 0.5, 1.45, Z0, r=0.35)
    root_fan(p, (-0.1, 0.0), 1.15, 0.45, fan_angles(8, 0.2), thick=0.14, h=0.12)


def h012_abode():
    """Capela da floresta: a mesma cabana, maior e coberta de musgo, mastro de raiz na porta com UM cogumelo pendurado e o ancião em relevo."""
    p = pal()
    pad(p)
    cabin(p, -0.25, 0.0, 2.2, 2.6, 1.1, 0.95, roof_tone="moss", shingle_tones=("moss_dk", "moss"))
    door(p, 0.85, 0.45, 0.62, 0.85)
    # Campanário de casca: agulha de seis faces sobre a cumeeira, com espinho de ferrugem na ponta.
    root("steeple", p["bark"], (-1.0, 0.0, Z0 + 2.0), (-1.0, 0.0, Z0 + 3.0), 0.4, 0.16, sides=6, bevel=0.02)
    thorn(p, (-1.0, 0.0, Z0 + 2.95), 0.5, r=0.12, tone="rust")
    # Relevo do ancião esculpido na parede: manto, capuz sem rosto e o báculo.
    rx = 0.87
    slab("relief_robe", p["bark_lt"], (rx, -0.65, Z0 + 0.5), (0.05, 0.42, 0.7), taper=0.7, bevel=0.0)
    box("relief_hood", p["bark_lt"], (rx, -0.65, Z0 + 0.82), (0.06, 0.24, 0.24), bevel=0.0, taper=0.6)
    box("relief_crozier", p["bark_lt"], (rx, -0.28, Z0 + 0.12), (0.05, 0.05, 1.0), bevel=0.0)
    # Mastro de raiz na porta com o gancho e o cogumelo pendurado.
    root("mast", p["bark_dk"], (1.4, -0.2, Z0 - 0.02), (1.35, -0.2, Z0 + 2.7), 0.14, 0.08, sides=5)
    root("mast_hook", p["bark_dk"], (1.35, -0.2, Z0 + 2.65), (1.35, 0.35, Z0 + 2.5), 0.07, 0.05, sides=5)
    cap_hung(p, (1.35, 0.35, Z0 + 2.5), r=0.24)
    flask(p, (1.3, 1.0, Z0), h=0.38, r=0.17)
    root_fan(p, (-0.25, 0.0), 1.3, 0.35, fan_angles(8, 0.2), thick=0.15, h=0.12)


def h071_enigma():
    """Posto de vigia: tenda de casca costurada sobre arcos de raiz e uma trípode de raiz alta com UM cogumelo no topo."""
    p = pal()
    pad(p)
    prism("tent", p["bark_lt"], (-0.55, 0.0, Z0), (2.0, 2.3, 1.35), ridge=0.5, bevel=0.02, rot_z=math.radians(90))
    shingles(p, -0.55, 0.0, Z0, 1.0, 1.35, 2.34, rz=math.radians(90), rows=4)
    prism("tent_mouth", p["dark"], (0.6, 0.0, Z0), (1.0, 0.1, 1.0), ridge=0.5, bevel=0.0, rot_z=math.radians(90))
    # Arcos de raiz curvos por fora da lona.
    for x in (-1.5, -0.55, 0.55):
        pts = [(x, -1.08, Z0), (x, -1.0, Z0 + 0.55), (x, -0.62, Z0 + 1.0), (x, 0.0, Z0 + 1.42), (x, 0.62, Z0 + 1.0), (x, 1.0, Z0 + 0.55), (x, 1.08, Z0)]
        for a, b in itertools.pairwise(pts):
            root("arch", p["bark_dk"], a, b, 0.07, 0.07, sides=5)
    kit.beam("ridge", p["bark_dk"], (-1.5, 0.0, Z0 + 1.4), (0.6, 0.0, Z0 + 1.4), thick=0.1)
    # Trípode de vigia à frente: três pernas de raiz e a haste central que leva o cogumelo.
    mx, my = 1.0, 1.0
    top = (mx, my, Z0 + 3.1)
    for a in (0.3, 0.3 + math.tau / 3, 0.3 + 2 * math.tau / 3):
        root("tripod", p["bark"], (mx + math.cos(a) * 0.65, my + math.sin(a) * 0.65, Z0 - 0.02), top, 0.12, 0.06, sides=5)
    for a in (0.3, 0.3 + math.tau / 3, 0.3 + 2 * math.tau / 3):
        root("tripod_foot", p["bark_dk"], (mx + math.cos(a) * 0.95, my + math.sin(a) * 0.95, Z0 - 0.02), (mx + math.cos(a) * 0.65, my + math.sin(a) * 0.65, Z0 + 0.5), 0.14, 0.1, sides=5)
    cyl("watch_deck", p["bark_lt"], (mx, my, Z0 + 3.1), 0.42, 0.1, sides=6, top_radius=0.38, bevel=0.02)
    cap(p, (mx, my, Z0 + 3.2), r=0.3, stalk=0.4)
    # Estacas de levantamento com fita de ferrugem, marcando as veias que a floresta vai tampar.
    for x, y in ((1.35, -0.7), (1.0, -1.1), (0.45, -1.4)):
        root("stake", p["bark_dk"], (x, y, Z0), (x, y, Z0 + 0.75), 0.04, 0.03, sides=4)
        box("stake_ribbon", p["rust"], (x, y, Z0 + 0.52), (0.11, 0.11, 0.14), bevel=0.0)
    slab("rust_tarp", p["rust"], (-0.35, -1.2, Z0 + 0.5), (1.1, 0.1, 0.9), rx=0.3, bevel=0.02)
    moss(p, -1.5, 1.4, Z0, r=0.4)


# ---------------------------------------------------------------------------------------------------------
# Ancients da vida: Growth -> Life -> Eternity (o toco, o rebrote, a árvore-mãe)
# ---------------------------------------------------------------------------------------------------------


def h013_growth():
    """Toco serrado: tronco cortado ao meio, face do corte clara com anéis, placas de ferrugem onde a serra passou e um cogumelo brotando."""
    p = pal()
    pad(p)
    trunk(p, (0, 0, Z0), 1.05, 0.9, 1.9, sides=9, ridges=9)
    z = Z0 + 1.9
    cyl("cut_face", p["bark_lt"], (0, 0, z), 0.88, 0.07, sides=9, bevel=0.0)
    ring("cut_ring", p["bark"], (0, 0, z + 0.07), 0.6, 0.015, thick=0.02, sides=9)
    ring("cut_ring", p["bark"], (0, 0, z + 0.07), 0.3, 0.015, thick=0.02, sides=9)
    # O talho da serra: cunha escura entrando pela face da frente.
    slab("kerf", p["dark"], (0.6, 0.0, z + 0.02), (0.6, 0.12, 0.1), bevel=0.0)
    # Placas de ferrugem vestindo a casca logo abaixo do corte.
    for i in range(5):
        a = math.radians(-70 + i * 35)
        plate(p, (math.cos(a) * 0.98, math.sin(a) * 0.98, Z0 + 1.45), (0.55, 0.1, 0.65), rz=a + math.pi / 2, lean=0.0)
    cap(p, (-0.2, 0.15, z + 0.04), r=0.34, stalk=0.4)
    for a in (2.4, 3.3, 4.0):
        thorn(p, (math.cos(a) * 0.7, math.sin(a) * 0.7, z + 0.04), 0.35, r=0.07, lean=(0.04, 0.0), tone="moss_dk")
    moss(p, 0.1, 0.65, z + 0.05, r=0.28, squash=0.4)
    root_fan(p, (0, 0), 0.95, 0.6, fan_angles(9, 0.15), thick=0.24, h=0.5)


def h01h_life():
    """Rebrote: a copa fechada de casca sob musgo denso cresceu sobre o corte, e uma raiz-tubo grossa desce à terra como soro."""
    p = pal()
    pad(p)
    trunk(p, (0, 0, Z0), 1.05, 0.9, 1.5, sides=9, ridges=9)
    # A cicatriz do corte ainda aparece: faixa de ferrugem em volta, coberta de musgo por cima.
    ring("scar_band", p["rust"], (0, 0, Z0 + 1.2), 0.92, 0.3, thick=0.05, sides=9)
    cyl("regrowth", p["bark"], (0, 0, Z0 + 1.5), 0.9, 1.3, sides=9, top_radius=0.62, bevel=0.03)
    for i in range(7):
        a = i * math.tau / 7 + 0.3
        root("ridge", p["bark_dk"], (math.cos(a) * 0.86, math.sin(a) * 0.86, Z0 + 1.55), (math.cos(a) * 0.6, math.sin(a) * 0.6, Z0 + 2.7), 0.07, 0.045, sides=4)
    # Copa fechada, simétrica: três degraus facetados de musgo.
    zc = Z0 + 2.45
    cyl("crown_1", p["moss_dk"], (0, 0, zc), 1.5, 0.45, sides=9, top_radius=1.4, bevel=0.04)
    cyl("crown_2", p["moss"], (0, 0, zc + 0.45), 1.4, 0.5, sides=9, top_radius=0.95, bevel=0.04)
    cyl("crown_3", p["moss_lt"], (0, 0, zc + 0.95), 0.95, 0.4, sides=9, top_radius=0.35, bevel=0.03)
    for i in range(6):
        a = i * math.tau / 6
        plate(p, (math.cos(a) * 1.42, math.sin(a) * 1.42, zc + 0.12), (0.4, 0.07, 0.3), rz=a + math.pi / 2, lean=0.1, tone="bark_lt")
    cap(p, (0.0, 0.0, zc + 1.28), r=0.28, stalk=0.25)
    # Raiz-tubo descendo da copa ao poço do chão, em frente.
    pts = [(0.85, 0.45, Z0 + 2.0), (1.35, 0.55, Z0 + 1.7), (1.65, 0.6, Z0 + 1.0), (1.65, 0.6, Z0 + 0.4), (1.6, 0.6, Z0 - 0.02)]
    tube(p, "bark_lt", pts, 0.14, 0.12)
    cyl("well_collar", p["moss_dk"], (1.6, 0.6, Z0), 0.3, 0.14, sides=7, top_radius=0.22, bevel=0.02)
    root_fan(p, (0, 0), 0.95, 0.65, fan_angles(8, 0.15), thick=0.24, h=0.5)


def h01j_eternity():
    """Árvore-mãe: tronco colossal coroado por um estrado de espinhos de ferrugem, manto de musgo pendurado e um coro de raízes de pé em volta."""
    p = pal()
    pad(p)
    trunk(p, (0, 0, Z0), 1.25, 0.95, 2.55, sides=10, ridges=10)
    zt = Z0 + 2.55
    cyl("shoulder", p["bark"], (0, 0, zt), 0.95, 0.4, sides=10, top_radius=1.2, bevel=0.04)
    for i in range(6):
        a = i * math.tau / 6 + 0.2
        plate(p, (math.cos(a) * 1.12, math.sin(a) * 1.12, zt - 0.5), (0.5, 0.09, 0.6), rz=a + math.pi / 2, lean=0.0)
    cyl("crown_deck", p["moss_dk"], (0, 0, zt + 0.4), 1.2, 0.12, sides=10, top_radius=1.05, bevel=0.02)
    thorn_crown(p, (0, 0), 0.95, 10, 1.2, zt + 0.5, r=0.12)
    thorn_crown(p, (0, 0), 0.5, 6, 0.8, zt + 0.5, r=0.09, tone="rust_dk")
    cap(p, (0, 0, zt + 0.5), r=0.3, stalk=0.35)
    # Manto de musgo pendurado do ombro.
    for i in range(12):
        a = i * math.tau / 12 + 0.1
        d = 0.9 if i % 2 else 1.35
        slab("mantle", p["moss" if i % 3 else "moss_dk"], (math.cos(a) * 1.2, math.sin(a) * 1.2, zt - d / 2 + 0.05), (0.32, 0.1, d), rz=a + math.pi / 2, bevel=0.0, taper=0.4)
    # Coro: raízes de pé em arco em volta da base, inclinadas para o tronco.
    for i in range(7):
        a = i * math.tau / 7 + 0.2
        c, s = math.cos(a), math.sin(a)
        root("choir", p["bark_dk"], (c * 1.62, s * 1.62, Z0 - 0.02), (c * 1.2, s * 1.2, Z0 + 1.45), 0.2, 0.07, sides=5)
        moss(p, c * 1.62, s * 1.62, Z0, r=0.22)
    root_fan(p, (0, 0), 1.2, 0.35, fan_angles(7, 0.2 + math.pi / 7), thick=0.2, h=0.4)


# ---------------------------------------------------------------------------------------------------------
# Ursos: Slumber -> Hibernation (a toca no tronco)
# ---------------------------------------------------------------------------------------------------------


def den(p, size, mouth_w, mouth_h):
    """Tronco-toca: caixa larga de casca em talude, boca escura na frente e moldura de raiz."""
    sx, sh = size
    box("den", p["bark"], (0, 0, Z0), (sx, sx, sh), bevel=0.12, taper=0.78, taper_y=0.85)
    for i in range(7):
        y = -sx * 0.4 + i * sx * 0.8 / 6
        root("den_ridge", p["bark_dk"], (sx / 2 + 0.02, y, Z0 + 0.05), (sx * 0.78 / 2 + 0.02, y * 0.8, Z0 + sh - 0.05), 0.07, 0.05, sides=4)
    fx = sx / 2 - 0.15
    box("mouth", p["dark"], (fx, 0, Z0 - 0.02), (0.3, mouth_w, mouth_h), bevel=0.0)
    for s in (-1, 1):
        root("jamb", p["bark_lt"], (fx + 0.15, s * (mouth_w / 2 + 0.08), Z0 - 0.02), (fx + 0.15, s * (mouth_w / 2 + 0.08), Z0 + mouth_h), 0.1, 0.1, sides=5)
    kit.beam("lintel", p["bark_lt"], (fx + 0.15, -mouth_w / 2 - 0.2, Z0 + mouth_h), (fx + 0.15, mouth_w / 2 + 0.2, Z0 + mouth_h), thick=0.2)
    for i in range(6):
        y = -mouth_w / 2 + 0.1 + i * (mouth_w - 0.2) / 5
        slab("lip_moss", p["moss"], (fx + 0.18, y, Z0 + mouth_h - 0.14 - 0.12 * (i % 3)), (0.1, 0.12, 0.32 + 0.12 * (i % 3)), bevel=0.0, taper=0.4)
    top = Z0 + sh
    dome("den_crown", p["moss"], (-0.3, 0, top - 0.05), sx * 0.4, squash=0.45, sides=9)
    for a in fan_angles(5, 0.9):
        thorn(p, (math.cos(a) * 0.7 - 0.1, math.sin(a) * 0.7, top + 0.1), 0.45, r=0.08, lean=(math.cos(a) * 0.1, math.sin(a) * 0.1), tone="rust_dk")
    root_fan(p, (0, 0), sx * 0.46, 0.4, fan_angles(8, 0.4 + math.pi / 8), thick=0.2, h=0.4)


def h023_slumber():
    """Toca do sono: tronco baixo e largo aberto numa boca escura, meia boca barrada por placas de ferrugem e musgo pendendo do lábio."""
    p = pal()
    pad(p)
    den(p, (2.9, 1.95), 1.15, 1.15)
    # Placas de ferrugem barrando a metade -y da boca.
    plate(p, (1.52, -0.3, Z0 + 0.55), (0.1, 0.5, 1.1), rz=0.05)
    plate(p, (1.52, -0.8, Z0 + 0.45), (0.1, 0.5, 0.95), rz=0.05, lean=-0.1)
    cap(p, (1.45, 0.95, Z0), r=0.22, stalk=0.25)
    moss(p, 1.2, -1.4, Z0, r=0.4)


def h024_hibernation():
    """Toca funda: a mesma boca, maior e mais alta, duas placas de ferrugem como portas entreabertas e um cogumelo aceso lá dentro."""
    p = pal()
    pad(p)
    den(p, (3.1, 2.65), 1.35, 1.7)
    for s in (-1, 1):
        hx, hy = 1.62, s * 0.8
        ang = s * math.radians(-55) + (math.pi if False else 0)
        d = (math.cos(ang), math.sin(ang))
        plate(p, (hx + d[0] * 0.4, hy + d[1] * 0.4, Z0 + 0.8), (0.8, 0.1, 1.6), rz=ang, lean=0.0)
    cap(p, (1.35, 0.0, Z0), r=0.3, stalk=0.45)
    moss(p, 1.3, -1.45, Z0, r=0.4)
    moss(p, 1.3, 1.45, Z0, r=0.4)


# ---------------------------------------------------------------------------------------------------------
# Utilidade e defesa
# ---------------------------------------------------------------------------------------------------------


def h027_roost():
    """Poleiro do dragão: tronco-mestre bifurcado em Y com plataforma de galhos no alto, costelas de raiz na base e uma raiz-tubo de seiva até o chão."""
    p = pal()
    pad(p)
    cyl("fork_base", p["bark"], (0, 0, Z0), 1.0, 1.0, sides=8, top_radius=0.72, bevel=0.04)
    for s in (-1, 1):
        root("fork", p["bark"], (0, s * 0.4, Z0 + 0.9), (0.05, s * 1.05, Z0 + 2.9), 0.55, 0.38, sides=7, bevel=0.03)
        root("fork_ridge", p["bark_dk"], (0.4, s * 0.45, Z0 + 1.0), (0.4, s * 1.0, Z0 + 2.8), 0.07, 0.05, sides=4)
    zp = Z0 + 2.9
    box("platform", p["bark_lt"], (0, 0, zp), (1.6, 3.0, 0.2), bevel=0.04, taper=0.94, taper_y=0.96)
    box("nest_bed", p["moss_dk"], (0, 0, zp + 0.2), (1.2, 2.2, 0.1), bevel=0.0)
    for s_ in (-1, 1):
        root("fork_top", p["bark_dk"], (0, s_ * 1.3, zp), (0.05, s_ * 1.4, zp + 0.9), 0.3, 0.1, sides=6, bevel=0.02)
        thorn(p, (0.1, s_ * 1.4, zp + 0.8), 0.45, r=0.1, tone="rust")
    for y in (-0.7, 0.0, 0.7):
        for x in (-0.65, 0.65):
            thorn(p, (x, y, zp + 0.2), 0.3, r=0.07, lean=(x * 0.2, 0.0), tone="bark_dk")
    for a_, b_ in (((-0.5, -0.8), (0.5, 0.3)), ((-0.5, 0.8), (0.5, -0.3))):
        kit.beam("twig", p["bark_dk"], (a_[0], a_[1], zp + 0.3), (b_[0], b_[1], zp + 0.36), thick=0.1)
    cap(p, (-0.3, 0.3, zp + 0.28), r=0.28, stalk=0.25)
    # Costelas expostas na base: arcos de raiz do chão ao tronco.
    for a in fan_angles(6, 0.5):
        c, s = math.cos(a), math.sin(a)
        pts = [(c * 1.7, s * 1.7, Z0 - 0.02), (c * 1.5, s * 1.5, Z0 + 0.55), (c * 1.1, s * 1.1, Z0 + 0.95)]
        for q, r in itertools.pairwise(pts):
            root("rib", p["bark_dk"], q, r, 0.12, 0.09, sides=5)
    # Raiz-tubo carregando a seiva da plataforma ao chão, pelo lado da lane.
    pts = [(0.85, 1.2, zp + 0.1), (1.2, 1.45, Z0 + 2.1), (1.45, 1.45, Z0 + 1.0), (1.55, 1.3, Z0 - 0.02)]
    tube(p, "bark_lt", pts, 0.14)


def h028_monolith():
    """Menir reclamado: o mesmo bloco de pedra manchado de ferrugem, atravessado de lado a lado por raízes grossas, casca subindo da base e um cogumelo no topo."""
    p = pal()
    pad(p)
    box("stone", p["stone"], (0, 0, Z0), (1.5, 1.2, 3.1), bevel=0.06, taper=0.62, taper_y=0.68)
    for y in (-0.4, 0.05, 0.42):
        box("seep", p["rust_dk"], (0.62 - 0.12 * (y + 0.4), y, Z0 + 1.1), (0.05, 0.1, 1.6 - abs(y)), bevel=0.0)
    # Casca subindo da base pelos cantos e cobrindo a face de trás.
    cyl("bark_mound", p["bark"], (0, 0, Z0), 1.35, 0.7, sides=8, top_radius=0.95, bevel=0.04)
    box("bark_sheath", p["bark"], (0.0, 0.0, Z0 + 0.5), (1.35, 1.1, 1.1), bevel=0.06, taper=0.75, taper_y=0.78)
    for y in (-0.35, 0.0, 0.35):
        root("sheath_ridge", p["bark_dk"], (0.65, y, Z0 + 0.5), (0.5, y * 0.8, Z0 + 1.55), 0.07, 0.05, sides=4)
    moss(p, 0.45, 0.0, Z0 + 1.55, r=0.35, tone="moss_dk")
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        root("bark_climb", p["bark_dk"], (sx * 0.9, sy * 0.7, Z0 + 0.3), (sx * 0.45, sy * 0.4, Z0 + 1.9), 0.2, 0.08, sides=5)
    slab("back_bark", p["bark"], (-0.4, 0.0, Z0 + 1.2), (0.12, 1.0, 2.2), taper=0.7, bevel=0.03)
    moss(p, 0.0, 0.0, Z0 + 3.05, r=0.5, tone="moss_dk")
    for y, d in ((-0.35, 1.2), (0.0, 0.8), (0.32, 1.0)):
        slab("moss_drape", p["moss_dk"], (0.3 - y * 0.0, y, Z0 + 3.0 - d / 2), (0.05, 0.26, d), taper=0.5, bevel=0.0, rx=0.0, ry=0.18)
    # Raízes passando de lado a lado pela pedra.
    tube(p, "bark_lt", [(0.1, -1.5, Z0 + 0.1), (0.15, -0.75, Z0 + 1.0), (0.15, 0.75, Z0 + 1.2), (0.1, 1.55, Z0 + 0.15)], 0.19, 0.13)
    tube(p, "bark", [(-0.1, -1.35, Z0 + 1.4), (-0.15, -0.65, Z0 + 1.95), (-0.15, 0.65, Z0 + 2.15), (-0.1, 1.4, Z0 + 1.55)], 0.15, 0.1)
    cap(p, (0.0, 0.0, Z0 + 3.1), r=0.3, stalk=0.3)
    root_fan(p, (0, 0), 0.9, 0.7, fan_angles(8, 0.2), thick=0.2, h=0.25)


def h02c_guardian():
    """Guardião cego: tronco-torre com os braços de galho cruzados sobre o rosto entalhado e uma placa de ferrugem pendurada no peito como ex-voto."""
    p = pal()
    pad(p)
    trunk(p, (0, 0, Z0), 1.1, 0.9, 2.5, sides=8, ridges=8)
    zt = Z0 + 2.5
    cyl("head", p["bark"], (0, 0, zt), 0.88, 0.75, sides=8, top_radius=1.1, bevel=0.04)
    cyl("head_moss", p["moss_dk"], (0, 0, zt + 0.75), 1.1, 0.12, sides=8, top_radius=0.9, bevel=0.02)
    # O rosto entalhado: máscara clara com duas fendas escuras, quase toda coberta pelos braços.
    box("mask", p["bark_lt"], (0.84, 0, zt + 0.1), (0.14, 0.7, 0.55), bevel=0.02)
    for s in (-1, 1):
        box("mask_slit", p["dark"], (0.94, s * 0.17, zt + 0.35), (0.04, 0.11, 0.07), bevel=0.0)
    # Braços de galho em X sobre o rosto.
    root("arm", p["bark_dk"], (0.8, -1.05, zt - 0.5), (1.02, 0.8, zt + 0.95), 0.2, 0.14, sides=6, bevel=0.02)
    root("arm", p["bark_dk"], (0.8, 1.05, zt - 0.5), (1.02, -0.8, zt + 0.95), 0.2, 0.14, sides=6, bevel=0.02)
    for s in (-1, 1):
        box("shoulder", p["bark_dk"], (0.1, s * 1.0, zt - 0.5), (0.5, 0.45, 0.4), bevel=0.04)
    # Ex-voto: placa de ferrugem presa por cordas.
    plate(p, (1.05, 0, Z0 + 1.3), (0.1, 0.6, 0.75), lean=0.0)
    for s in (-1, 1):
        root("cord", p["bark_dk"], (1.0, s * 0.2, Z0 + 1.75), (0.95, s * 0.2, Z0 + 2.2), 0.03, 0.03, sides=4)
    cap(p, (-0.4, -0.6, zt + 0.82), r=0.26, stalk=0.25)
    root_fan(p, (0, 0), 1.0, 0.65, fan_angles(8, 0.2), thick=0.25, h=0.5)


def h02a_gale():
    """Ancião do vento: copa estática e assimétrica dobrada a favor do vento (+y), galhos poupados curvados para trás e folhas arrancadas em fila."""
    p = pal()
    pad(p)
    base, top = (-0.4, -0.3, Z0), (-0.15, -0.55, Z0 + 2.5)
    root("trunk", p["bark"], base, top, 0.75, 0.42, sides=7, bevel=0.03)
    root("trunk_ridge", p["bark_dk"], (-0.1, -0.7, Z0 + 0.1), (0.05, -0.85, Z0 + 2.2), 0.07, 0.05, sides=4)
    # Copa em três massas facetadas, todas empurradas para +y: a de cima é a maior e a ponta se afina a favor do vento.
    for i, (q, r, tone) in enumerate((((-0.2, -0.45, Z0 + 2.3), 0.8, "moss_dk"), ((-0.1, 0.1, Z0 + 2.8), 0.8, "moss"), ((0.0, 0.75, Z0 + 3.0), 0.62, "moss_lt"), ((0.1, 1.3, Z0 + 2.95), 0.42, "moss"))):
        root("crown_lump", p[tone], q, (q[0] + 0.1, q[1] + 0.55, q[2] - 0.25), r, r * 0.55, sides=7, bevel=0.03)
    # Galhos poupados, de casca nua, curvados para trás sob a copa.
    for x, tip in ((0.45, (0.5, 1.55, Z0 + 2.2)), (-0.6, (-0.7, 1.4, Z0 + 2.55)), (0.0, (0.05, 1.7, Z0 + 2.0))):
        root("branch", p["bark_dk"], (-0.15 + x * 0.3, -0.5, Z0 + 2.2), tip, 0.15, 0.05, sides=5)
    # Folhas arrancadas em fila, presas por fiapos de galho, todas rumo ao vento.
    for i, (x, z0) in enumerate(((0.2, 2.95), (-0.4, 3.25), (0.9, 2.45), (-0.9, 2.55))):
        for k in range(3):
            kit.beam("twig", p["bark_dk"], (x, 1.5 + k * 0.1, Z0 + z0 - k * 0.28), (x, 1.55 + k * 0.1, Z0 + z0 - (k + 1) * 0.28), thick=0.03)
            slab("leaf", p["moss_lt" if (i + k) % 2 else "rust_dk"], (x, 1.62 + k * 0.1, Z0 + z0 - k * 0.28 - 0.14), (0.2, 0.12, 0.04), rx=0.4, rz=0.4 * k, bevel=0.0)
    cap_hung(p, (0.55, 0.2, Z0 + 2.05), r=0.22)
    # Raiz-tubo servindo o tronco onde se escreveria um duto.
    tube(p, "bark_lt", [(1.5, -0.1, Z0 - 0.02), (1.5, -0.1, Z0 + 0.3), (1.0, -0.4, Z0 + 0.9), (0.4, -0.6, Z0 + 1.0)], 0.13, 0.11)
    # Contrafortes de raiz: grossos no lado do vento, finos atrás.
    for a, t in ((-1.3, 0.3), (-1.9, 0.26), (-0.7, 0.24), (2.9, 0.2), (3.5, 0.2)):
        root("root", p["bark_dk"], (-0.4 + math.cos(a) * 0.6, -0.3 + math.sin(a) * 0.6, Z0 + 0.5), (-0.4 + math.cos(a) * 1.35, -0.3 + math.sin(a) * 1.35, Z0 - 0.02), t, t * 0.3, sides=5)
    moss(p, 1.1, 1.1, Z0, r=0.4)


def h02d_wonders():
    """Refinaria clandestina: tronco com a boca aberta em prateleiras de cogumelos-lanterna e frascos de seiva, toldo de casca costurada e raiz-tubo na base."""
    p = pal()
    pad(p)
    box("trunk", p["bark"], (-0.2, 0, Z0), (2.8, 2.9, 3.0), bevel=0.12, taper=0.8, taper_y=0.85)
    for i in range(7):
        y = -1.1 + i * 2.2 / 6
        root("ridge", p["bark_dk"], (1.22, y, Z0 + 0.05), (0.96, y * 0.85, Z0 + 2.95), 0.07, 0.05, sides=4)
    # Alcova na frente.
    box("alcove", p["dark"], (1.12, 0, Z0 + 0.1), (0.25, 1.95, 1.95), bevel=0.0)
    for s in (-1, 1):
        root("alcove_post", p["bark_lt"], (1.3, s * 1.08, Z0 - 0.02), (1.3, s * 1.08, Z0 + 2.2), 0.1, 0.09, sides=5)
    # Prateleiras com cogumelos e frascos.
    for k, z in enumerate((0.5, 1.05, 1.6)):
        box("shelf", p["bark_lt"], (1.3, 0, Z0 + z), (0.5, 1.95, 0.07), bevel=0.0)
        for j in range(5):
            y = -0.78 + j * 0.39
            if (j + k) % 2:
                flask(p, (1.38, y, Z0 + z + 0.07), h=0.26, r=0.1)
            else:
                cap(p, (1.38, y, Z0 + z + 0.07), r=0.13, stalk=0.13)
    # Toldo de casca costurada.
    slab("awning", p["bark_lt"], (1.62, 0, Z0 + 2.28), (0.8, 2.5, 0.07), ry=0.28, bevel=0.0)
    for y in (-0.8, 0.0, 0.8):
        slab("awning_seam", p["bark_dk"], (1.64, y, Z0 + 2.3), (0.8, 0.06, 0.05), ry=0.28, bevel=0.0)
    # Copa de musgo e cogumelos de cima.
    dome("crown", p["moss"], (-0.2, 0, Z0 + 2.95), 1.5, squash=0.5, sides=9)
    cap(p, (-0.4, 0.4, Z0 + 3.55), r=0.3, stalk=0.3)
    # Raiz-tubo entrando pela base com o que os poços tampados pagam.
    tube(p, "bark_lt", [(0.8, -1.7, Z0 - 0.02), (0.8, -1.7, Z0 + 0.35), (0.5, -1.45, Z0 + 0.7), (0.3, -1.3, Z0 + 0.75)], 0.14, 0.12)
    root_fan(p, (-0.2, 0), 1.4, 0.3, fan_angles(8, 0.2)[2:7] + fan_angles(8, 0.2)[0:1], thick=0.2, h=0.4)


def n02d_protector():
    """Árvore-bateria: tronco ereto, couraça de ferrugem, rosto coberto por dois braços cruzados e a coroa vazada de espinhos; a pedra de enxofre carrega o braço de arremesso."""
    p = pal()
    pad(p, 3.0)
    trunk(p, (0, 0, Z0), 0.95, 0.75, 2.5, sides=8, ridges=8)
    zt = Z0 + 2.5
    cyl("head", p["bark"], (0, 0, zt), 0.72, 0.6, sides=8, top_radius=0.82, bevel=0.03)
    # Couraça: peitoral e ombreiras de ferrugem por cima da casca.
    plate(p, (0.82, 0, Z0 + 1.55), (0.1, 0.95, 0.95), lean=0.0)
    for s in (-1, 1):
        box("pauldron", p["rust"], (0.0, s * 0.85, zt - 0.5), (0.55, 0.5, 0.35), bevel=0.04, taper=0.7, taper_y=0.7)
    # Rosto coberto por dois braços de galho cruzados.
    box("mask", p["bark_lt"], (0.72, 0, zt + 0.08), (0.12, 0.55, 0.45), bevel=0.02)
    root("arm", p["bark_dk"], (0.75, -0.85, zt - 0.45), (0.9, 0.6, zt + 0.55), 0.17, 0.12, sides=6, bevel=0.02)
    root("arm", p["bark_dk"], (0.75, 0.85, zt - 0.45), (0.9, -0.6, zt + 0.55), 0.17, 0.12, sides=6, bevel=0.02)
    # Braço de arremesso erguido por trás, segurando a pedra de enxofre.
    root("throw_arm", p["bark_dk"], (-0.1, -0.85, zt - 0.55), (-0.55, -1.0, zt + 1.0), 0.2, 0.13, sides=6, bevel=0.02)
    cyl("sulfur", p["sulfur"], (-0.6, -1.0, zt + 0.98), 0.17, 0.3, sides=6, top_radius=0.12, bevel=0.01)
    for a in (0.5, 2.1, 3.7):
        root("claw", p["bark_dk"], (-0.55, -1.0, zt + 0.95), (-0.55 + math.cos(a) * 0.2, -1.0 + math.sin(a) * 0.2, zt + 1.35), 0.04, 0.02, sides=4)
    # Coroa vazada de espinhos de ferrugem.
    thorn_crown(p, (0, 0), 0.62, 9, 1.35, zt + 0.55, r=0.11)
    cyl("crown_band", p["moss_dk"], (0, 0, zt + 0.55), 0.82, 0.1, sides=8, top_radius=0.75, bevel=0.02)
    root_fan(p, (0, 0), 0.85, 0.5, fan_angles(8, 0.2), thick=0.24, h=0.5)


BUILDINGS = {
    "h002": h002_clutch,
    "h00Q": h00q_nest,
    "h00R": h00r_hatchery,
    "h00Y": h00y_hut,
    "h012": h012_abode,
    "h071": h071_enigma,
    "h013": h013_growth,
    "h01H": h01h_life,
    "h01J": h01j_eternity,
    "h023": h023_slumber,
    "h024": h024_hibernation,
    "h027": h027_roost,
    "h028": h028_monolith,
    "h02C": h02c_guardian,
    "h02A": h02a_gale,
    "h02D": h02d_wonders,
    "n02D": n02d_protector,
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
