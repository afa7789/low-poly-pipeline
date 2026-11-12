"""Prédios da raça Chaos modelados por script (redesenho de reports/design/race-chaos.md): um GLB por prédio.

Uso:
    blender -b --factory-startup --python tools/blender/buildings_chaos.py -- <id|all> [--out DIR] [--render DIR]

A Indústria do Terror: a corte vende o sangue da terra como combustível, então cada prédio é uma instalação de
frete com plaqueta de lote. Silhueta "a agulha sobre o bloco": uma massa baixa e pesada mais UMA agulha vertical,
e a junta entre as duas é a cruz-de-válvula (cano com volante em cruz). Todo prédio tem a cruz-de-válvula e um
tambor de 200 L com etiqueta de lote. Vermelho (sangue vivo) é o produto e o único acento; latão só em placa de
escritura e só onde não há vermelho; brasa só na fenda da fornalha. Cores do doc com o valor subido (a luz do
jogo escurece). Pegada ~3,5 x 3,5 centrada na origem, a porta virada para +x; o jogo normaliza o tamanho, põe o
prédio no plinto do time e desenha a bandeira.
"""

import math
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import map_castles as kit
from map_castles import beam, box, cyl, dome, mat, prism, ring


def pal():
    return {
        "soot": mat("soot_black", 0x564E48),
        "iron": mat("tartarean_iron", 0x7C7369),
        "iron_lt": mat("iron_light", 0x9E9488),
        "iron_dk": mat("iron_dark", 0x35302D),
        "grey": mat("shift_grey", 0xA39B8E),
        "ivory": mat("dirty_ivory", 0xD2C9B2),
        "blood": mat("blood_live", 0xC8281C),
        "ink": mat("dried_ink", 0x7A4632),
        "brass": mat("contract_brass", 0xC9A95A),
        "brass_old": mat("yellowed_iron", 0xA09064),
        "tar": mat("tar", 0x26211F),
        "mud": mat("mud", 0x5A4D42),
        "glass": mat("dirty_glass", 0x9A9378),
        "smoke": mat("smoke", 0xB9B2A6),
        "ember": mat("seam_ember", 0xFF7A2E, emit=3.0),
    }


# ---------------------------------------------------------------------------------------------------------
# Peças da raça
# ---------------------------------------------------------------------------------------------------------


def pad(p, size=(3.5, 3.5)):
    """Chão do prédio, do tamanho do conteúdo (o jogo normaliza pelo maior lado)."""
    box("pad", p["mud"], (0, 0, 0), (size[0], size[1], 0.1), bevel=0.03)


def arc_band(name, material, center, r_in, r_out, depth, a0=0.0, a1=360.0, segs=12, axis="x"):
    """Faixa em arco (ou aro inteiro) de espessura `depth` ao longo de `axis`: arcos de porta, volantes, mostradores.
    Os ângulos correm no plano perpendicular ao eixo: (y, z) para x, (x, y) para z, (x, z) para y."""
    full = abs(a1 - a0) >= 360.0
    steps = segs if full else segs + 1
    bm = bmesh.new()
    rows = []
    for i in range(steps):
        a = math.radians(a0 + (a1 - a0) * i / segs)
        c, s = math.cos(a), math.sin(a)
        ring_pts = []
        for r, w in ((r_in, -depth / 2), (r_out, -depth / 2), (r_out, depth / 2), (r_in, depth / 2)):
            u, v = r * c, r * s
            xyz = {"x": (w, u, v), "y": (u, w, v), "z": (u, v, w)}[axis]
            ring_pts.append(bm.verts.new(xyz))
        rows.append(ring_pts)
    for i in range(steps if full else steps - 1):
        a, b = rows[i], rows[(i + 1) % steps]
        for k in range(4):
            bm.faces.new((a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k]))
    if not full:
        bm.faces.new(rows[0])
        bm.faces.new(rows[-1][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.translate(bm, verts=bm.verts, vec=center)
    return kit._finish(bm, name, material)


def wheel(rim, spokes, center, r, axis="z", thick=0.07):
    """Volante de válvula: aro com duas travessas em cruz."""
    x, y, z = center
    arc_band("wheel", rim, center, r - 0.055, r, thick, segs=10, axis=axis)
    for ang in (0.0, math.pi / 2):
        c, s = r * 0.97 * math.cos(ang), r * 0.97 * math.sin(ang)
        a, b = ((x - c, y - s, z), (x + c, y + s, z)) if axis == "z" else ((x, y - c, z - s), (x, y + c, z + s))
        beam("wheel_spoke", spokes, a, b, thick=0.045)
    cyl("wheel_hub", spokes, (x, y, z - 0.04) if axis == "z" else (x - 0.04, y, z - 0.04), 0.07, 0.08, sides=6, bevel=0.0)


def valve_cross(p, pos, height=1.2, hand="blood"):
    """A cruz-de-válvula da raça: cano vertical, braço de cano cruzado e volante em cruz no topo."""
    x, y, z = pos
    cyl("vc_pipe", p["iron_lt"], (x, y, z), 0.1, height, sides=8, bevel=0.0)
    arm = 0.5 * height + 0.4
    box("vc_arm", p["iron_lt"], (x, y, z + height * 0.66), (0.14, arm, 0.14), bevel=0.0)
    for s in (-1, 1):
        box("vc_flange", p["iron_dk"], (x, y + s * arm / 2, z + height * 0.66 - 0.04), (0.2, 0.07, 0.22), bevel=0.0)
    wheel(p[hand], p[hand], (x, y, z + height + 0.02), 0.27)


def drum(p, pos, lying=False, band="iron_dk"):
    """Tambor de 200 L com cintas e etiqueta de lote (marcador de frete da raça)."""
    x, y, z = pos
    if lying:
        cyl("drum", p["iron"], (x - 0.22, y, z + 0.17), 0.17, 0.44, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
        box("lot_tag", p["ivory"], (x, y, z + 0.17), (0.03, 0.11, 0.12), bevel=0.0)
        return
    cyl("drum", p["iron"], (x, y, z), 0.17, 0.44, sides=10, bevel=0.0)
    for dz in (0.1, 0.32):
        ring("drum_band", p[band], (x, y, z + dz), 0.17, 0.04, thick=0.015, sides=10)
    cyl("drum_lid", p["iron_lt"], (x, y, z + 0.44), 0.15, 0.03, sides=10, bevel=0.0)
    box("lot_tag", p["ivory"], (x + 0.17, y, z + 0.17), (0.03, 0.11, 0.13), bevel=0.0)


def plate(p, pos, w, h, tone="brass", lines=3):
    """Placa aparafusada na face +x: escritura, plaqueta de lote, número do nível."""
    x, y, z = pos
    box("plate", p[tone], (x, y, z), (0.04, w, h), bevel=0.0)
    for i in range(lines):
        box("plate_line", p["iron_dk"], (x + 0.025, y, z + h * 0.18 + i * h * 0.26), (0.02, w * (0.7 - 0.12 * (i % 2)), h * 0.1), bevel=0.0)


def ledger(p, pos, rot_z=0.0, seal=True):
    """Livro-razão aberto de capa de ferro; o selo de latão é a escritura."""
    x, y, z = pos
    box("ledger_cover", p["iron_dk"], (x, y, z), (0.56, 0.42, 0.04), bevel=0.0, rot_z=rot_z)
    for s in (-1, 1):
        c, sn = math.cos(rot_z), math.sin(rot_z)
        box("ledger_page", p["ivory"], (x - sn * s * 0.12, y + c * s * 0.12, z + 0.04), (0.46, 0.2, 0.03), bevel=0.0, rot_z=rot_z)
    if seal:
        cyl("ledger_seal", p["brass"], (x + 0.08, y + 0.1, z + 0.07), 0.08, 0.03, sides=8, bevel=0.0)


def pipe(p, a, b, r=0.07, tone="iron_lt"):
    beam("pipe", p[tone], a, b, thick=r * 2)


def ampoule(p, pos, height=0.32):
    """Ampola de amostra do lote: vidro sujo cheio de óleo-sangue, tampa de ferro."""
    x, y, z = pos
    cyl("ampoule", p["glass"], (x, y, z), 0.07, height, sides=8, bevel=0.0)
    cyl("ampoule_oil", p["blood"], (x, y, z + 0.03), 0.055, height * 0.6, sides=8, bevel=0.0)
    cyl("ampoule_cap", p["iron_dk"], (x, y, z + height), 0.075, 0.05, sides=8, bevel=0.0)


def pennant(material, pos, w=0.22, h=0.26):
    """Bandeirola de ponta para baixo no plano y-z (vista de +x)."""
    x, y, z = pos
    bm = bmesh.new()
    pts = [(-w / 2, h), (w / 2, h), (0.0, 0.0)]
    front = [bm.verts.new((x - 0.015, y + u, z + v)) for u, v in pts]
    back = [bm.verts.new((x + 0.015, y + u, z + v)) for u, v in pts]
    bm.faces.new(front)
    bm.faces.new(back[::-1])
    for i in range(3):
        j = (i + 1) % 3
        bm.faces.new((front[j], front[i], back[i], back[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit._finish(bm, "pennant", material)


def rivet_row(p, y0, y1, x, z, count, tone="iron_dk"):
    """Fileira de rebites na face +x (corte do casco rebitado)."""
    for i in range(count):
        box("rivet", p[tone], (x, y0 + (y1 - y0) * i / (count - 1), z), (0.04, 0.07, 0.07), bevel=0.0)


def smoke_puff(p, pos, size=0.3):
    x, y, z = pos
    for dx, dy, dz, k in ((0, 0, 0, 1.0), (0.12, 0.08, 0.32, 0.8), (-0.05, 0.14, 0.58, 0.65)):
        cyl("smoke", p["smoke"], (x + dx, y + dy, z + dz), size * k, size * 0.55, sides=7, bevel=0.0)


# ---------------------------------------------------------------------------------------------------------
# Tronco do quartel: Chaos Citadel -> Greater Chaos Citadel
# ---------------------------------------------------------------------------------------------------------


def citadel_body(p, cx, hand):
    """Casco de escritório-matriz: bloco rebitado com arcos corporativos, o volante-maçaneta e os escudos da corte."""
    pad(p)
    box("c_foot", p["iron_dk"], (cx, 0, 0.1), (3.1, 3.1, 0.2), bevel=0.03)
    box("c_body", p["iron"], (cx, 0, 0.3), (2.8, 2.8, 1.2), bevel=0.05, taper=0.96, taper_y=0.96)
    box("c_cornice", p["iron_lt"], (cx, 0, 1.5), (2.95, 2.95, 0.12), bevel=0.02)
    xf = cx + 1.4
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        box("c_pilaster", p["iron_dk"], (cx + sx * 1.38, sy * 1.38, 0.2), (0.26, 0.26, 1.3), bevel=0.02)
    # Porta central com arco e o grande volante de válvula como maçaneta; arcos menores nas pontas.
    box("door", p["tar"], (xf, 0, 0.3), (0.08, 0.9, 0.6), bevel=0.0)
    arc_band("door_fan", p["tar"], (xf, 0, 0.9), 0.01, 0.45, 0.08, 0, 180, axis="x")
    arc_band("door_arch", p["iron_lt"], (xf, 0, 0.9), 0.45, 0.57, 0.14, 0, 180, axis="x")
    wheel(p[hand], p[hand], (xf + 0.1, 0, 0.78), 0.36, axis="x")
    for s in (-1, 1):
        box("arch_door", p["tar"], (xf, s * 1.0, 0.3), (0.08, 0.42, 0.45), bevel=0.0)
        arc_band("arch_fan", p["tar"], (xf, s * 1.0, 0.75), 0.01, 0.21, 0.08, 0, 180, axis="x")
        arc_band("arch_frame", p["iron_lt"], (xf, s * 1.0, 0.75), 0.21, 0.29, 0.12, 0, 180, axis="x")
        for dx in (-0.6, 0.6):
            box("court_shield", p["brass_old"], (cx + dx, s * 1.42, 0.55), (0.34, 0.05, 0.44), bevel=0.0, taper=0.55, taper_y=1.0)
    drum(p, (cx + 1.55, -1.45, 0.1))


def dome_shell(p, pos, r, base_h=0.22):
    """Cúpula-casca rebitada: tambor, calota, cinta e coroa de rebites."""
    x, y, z = pos
    cyl("dome_drum", p["iron_dk"], (x, y, z), r * 1.08, base_h, sides=14, bevel=0.0)
    dome("dome", p["iron_lt"], (x, y, z + base_h), r, squash=0.85, sides=14)
    ring("dome_band", p["iron_dk"], (x, y, z + base_h + 0.02), r, 0.1, thick=0.03, sides=14)
    for i in range(12):
        a = i * math.tau / 12
        box("dome_rivet", p["iron_dk"], (x + math.cos(a) * r * 1.0, y + math.sin(a) * r * 1.0, z + base_h + 0.1), (0.07, 0.07, 0.07), bevel=0.0)
    return z + base_h + r * 0.85


def h01d_chaos_citadel():
    """Arquivo da matriz: cúpula-casca sobre arcos corporativos e uma única agulha com a cruz-de-válvula no topo."""
    p = pal()
    citadel_body(p, 0.0, "blood")
    top = dome_shell(p, (0, 0, 1.62), 1.25)
    valve_cross(p, (0, 0, top - 0.05), 1.4)


def h03g_greater_chaos_citadel():
    """Cidadela maior: segunda cúpula, mastro de estandarte da casa e sacada de avisos sobre a porta."""
    p = pal()
    citadel_body(p, 0.0, "ink")
    dome_shell(p, (-0.5, 0.0, 1.62), 1.05)
    dome_shell(p, (0.75, 0.0, 1.62), 0.7)
    # Sacada de avisos: laje saliente sobre a porta, guarda-corpo e a placa de concessões em latão.
    for y in (-1.0, 0.0, 1.0):
        beam("balcony_brace", p["iron_dk"], (1.4, y, 1.0), (1.8, y, 1.5), thick=0.09)
    box("balcony", p["iron_lt"], (1.62, 0, 1.46), (0.6, 2.4, 0.1), bevel=0.02)
    box("balcony_rail", p["iron_dk"], (1.88, 0, 1.56), (0.05, 2.4, 0.22), bevel=0.0)
    plate(p, (1.92, 0, 1.66), 1.2, 0.34, tone="brass", lines=2)
    # Mastro do estandarte com a cruz-de-válvula da casa no topo.
    box("mast", p["iron_dk"], (-1.25, -1.25, 1.5), (0.1, 0.1, 2.4), bevel=0.0)
    box("standard", p["soot"], (-1.25, -1.0, 2.7), (0.04, 0.45, 0.8), bevel=0.0)
    box("standard_stripe", p["ink"], (-1.22, -1.0, 3.15), (0.04, 0.45, 0.12), bevel=0.0)
    valve_cross(p, (-1.25, -1.25, 3.9), 0.7, hand="ink")


# ---------------------------------------------------------------------------------------------------------
# Altar da Ganância
# ---------------------------------------------------------------------------------------------------------


def h01c_altar_of_greed():
    """Balcão de contrato: laje baixa de ferro fundido com a agulha da cruz-de-válvula, dreno e livro-razão."""
    p = pal()
    pad(p)
    box("slab_foot", p["iron_dk"], (0, 0, 0.1), (3.3, 3.0, 0.18), bevel=0.04)
    box("slab", p["iron"], (0, 0, 0.28), (3.1, 2.8, 0.42), bevel=0.05, taper=0.95, taper_y=0.95)
    box("slab_top", p["iron_lt"], (0, 0, 0.7), (2.8, 2.5, 0.06), bevel=0.0)
    rivet_row(p, -1.2, 1.2, 1.5, 0.5, 7)
    # Anteparo do escriturário atrás e a escritura em latão na frente da laje.
    box("partition", p["iron"], (-1.1, 0, 0.76), (0.5, 2.4, 0.7), bevel=0.04)
    box("partition_cap", p["iron_lt"], (-1.1, 0, 1.46), (0.6, 2.5, 0.08), bevel=0.0)
    plate(p, (1.5, 0.45, 0.32), 0.9, 0.34)
    valve_cross(p, (-0.3, 0, 0.76), 2.5)
    ledger(p, (0.75, 0.55, 0.76), rot_z=0.2)
    # Válvula-ferida: o dreno onde o óleo da oferenda escorre, e seu volante.
    box("drain_slot", p["ink"], (0.8, -0.65, 0.76), (1.1, 0.2, 0.02), bevel=0.0)
    pipe(p, (1.35, -0.65, 0.78), (1.62, -0.65, 0.5), r=0.06)
    wheel(p["iron_lt"], p["ink"], (1.68, -0.65, 0.46), 0.2, axis="x")
    for x in (-0.2, 0.2):
        box("paper_stack", p["ivory"], (x, 1.0, 0.76), (0.4, 0.3, 0.12), bevel=0.0, rot_z=x)
    drum(p, (1.1, 1.0, 0.76))
    drum(p, (1.1, -1.05, 0.76))


# ---------------------------------------------------------------------------------------------------------
# Portão do Inferno: eclusa de fundição
# ---------------------------------------------------------------------------------------------------------


def h007_demon_gate():
    """Eclusa de fundição: arco de fornalha meio enterrado, garganta de piche com fenda de brasa e guindaste de sino."""
    p = pal()
    pad(p)
    box("mound", p["iron_dk"], (-0.9, 0, 0.1), (1.6, 3.2, 1.1), bevel=0.06, taper=0.7, taper_y=0.9)
    arc_band("arch_outer", p["iron_lt"], (-0.05, 0, 0.1), 1.0, 1.65, 1.2, 0, 180, segs=14, axis="x")
    arc_band("arch_inner", p["iron_dk"], (0.45, 0, 0.1), 0.55, 1.0, 0.3, 0, 180, segs=14, axis="x")
    arc_band("throat", p["tar"], (-0.2, 0, 0.1), 0.01, 1.0, 0.8, 0, 180, segs=14, axis="x")
    box("arch_pier", p["iron"], (-0.05, 1.33, 0.1), (1.2, 0.66, 0.2), bevel=0.02)
    box("arch_pier", p["iron"], (-0.05, -1.33, 0.1), (1.2, 0.66, 0.2), bevel=0.02)
    box("ember_slit", p["ember"], (0.22, 0, 0.3), (0.04, 0.8, 0.1), bevel=0.0)
    box("ember_slit", p["ember"], (0.22, 0, 0.55), (0.04, 0.5, 0.07), bevel=0.0)
    # Cratera de piche à frente e a cruz-de-válvula na verga, com o cano de combustível descendo ao chão.
    cyl("crater", p["tar"], (1.05, 0, 0.1), 0.85, 0.03, sides=12, bevel=0.0)
    valve_cross(p, (-0.05, 0, 1.75), 1.5)
    kit.pipe_run(p["iron_lt"], p["iron_dk"], [(-0.05, 0.3, 1.8), (0.1, 1.2, 1.8), (0.45, 1.5, 1.5), (0.45, 1.5, 0.2)], radius=0.08)
    # Guindaste de sino: poste, lança e o tanque de Infernal descendo na corrente.
    box("crane_post", p["iron"], (1.2, 1.35, 0.1), (0.2, 0.2, 2.8), bevel=0.02)
    beam("crane_jib", p["iron_dk"], (1.2, 1.35, 2.85), (1.05, -0.1, 2.85), thick=0.14)
    beam("crane_stay", p["iron_dk"], (1.2, 1.35, 2.0), (1.05, 0.3, 2.85), thick=0.07)
    beam("crane_chain", p["iron_dk"], (1.05, 0, 2.85), (1.05, 0, 1.8), thick=0.05)
    cyl("load_tank", p["soot"], (1.05, 0, 1.0), 0.38, 0.8, sides=8, bevel=0.0)
    ring("load_band", p["iron_dk"], (1.05, 0, 1.4), 0.38, 0.08, sides=8)
    box("load_window", p["blood"], (1.42, 0, 1.2), (0.04, 0.22, 0.28), bevel=0.0)
    drum(p, (1.45, -1.3, 0.1))


# ---------------------------------------------------------------------------------------------------------
# Ninho do Dragão: vaso de pressão
# ---------------------------------------------------------------------------------------------------------


def h009_dragon_nest():
    """Vaso de pressão sobre patins com UMA chaminé axial grossa e a escotilha-ovo de vidro sujo."""
    p = pal()
    pad(p)
    for x in (-0.6, 0.6):
        box("skid", p["iron_dk"], (x, 0, 0.1), (0.35, 3.2, 0.2), bevel=0.02)
    for y in (-1.0, 0.0, 1.0):
        box("skid_cross", p["iron_dk"], (0, y, 0.1), (1.6, 0.16, 0.2), bevel=0.0)
    # Casco horizontal ao longo de y, com cintas e tampos.
    cyl("vessel", p["iron"], (0, -1.45, 1.1), 0.88, 2.9, sides=14, bevel=0.0, rot=("X", math.radians(-90)))
    for y in (-0.9, 0.0, 0.9):
        arc_band("vessel_band", p["iron_dk"], (0, y, 1.1), 0.88, 0.95, 0.12, segs=14, axis="y")
    for s in (-1, 1):
        arc_band("vessel_cap", p["iron_lt"], (0, s * 1.46, 1.1), 0.5, 0.88, 0.1, segs=14, axis="y")
    # A escotilha com o ovo atrás do vidro sujo, virada para +x.
    arc_band("hatch_ring", p["iron_lt"], (0.84, 0, 1.15), 0.3, 0.46, 0.14, segs=12, axis="x")
    cyl("hatch_glass", p["glass"], (0.8, 0, 1.15), 0.31, 0.12, sides=12, bevel=0.0, rot=("Y", math.radians(90)))
    cyl("hatch_egg", p["blood"], (0.9, 0, 1.15), 0.2, 0.06, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
    # A chaminé axial: grossa, com cintas e fumaça (única transparência da raça, aqui opaca).
    cyl("stack_base", p["iron_dk"], (0, 0, 1.9), 0.44, 0.2, sides=10, bevel=0.0)
    cyl("stack", p["iron_lt"], (0, 0, 2.05), 0.3, 1.9, sides=10, top_radius=0.26, bevel=0.0)
    for z in (2.6, 3.4):
        ring("stack_band", p["iron_dk"], (0, 0, z), 0.28, 0.1, sides=10)
    ring("stack_rim", p["iron_dk"], (0, 0, 3.85), 0.26, 0.14, thick=0.05, sides=10)
    smoke_puff(p, (0, 0, 4.0), 0.26)
    valve_cross(p, (0.0, 1.05, 1.95), 0.9)
    # Bicos de mamadeira industrial na tampa +y e a válvula-ferida de onde a escotilha mama.
    for dz in (0.85, 1.1, 1.35):
        cyl("nipple", p["iron_lt"], (0.0, 1.5, dz), 0.05, 0.38, sides=6, bevel=0.0, rot=("X", math.radians(-90)))
        cyl("nipple_bulb", p["blood"], (0.0, 1.88, dz), 0.09, 0.03, sides=6, bevel=0.0, rot=("X", math.radians(-90)))
    drum(p, (1.45, -0.95, 0.1))
    pipe(p, (1.45, -0.95, 0.4), (1.2, -0.6, 0.9), r=0.05)
    wheel(p["iron_lt"], p["blood"], (1.3, -0.8, 0.56), 0.16, axis="x")
    drum(p, (1.35, 1.25, 0.1))


# ---------------------------------------------------------------------------------------------------------
# Apagadores: Eraser nível 1 -> 2 -> 3
# ---------------------------------------------------------------------------------------------------------


def press_head(p, pos, w=1.0, drop=0.5):
    """Cabeça de prensa: bloco, pistão e matriz de estampar, com a placa do nome da vítima na frente."""
    x, y, z = pos
    box("press_head", p["iron_lt"], (x, y, z), (w, w, 0.4), bevel=0.04)
    cyl("press_rod", p["iron_dk"], (x, y, z + 0.4), 0.1, drop, sides=8, bevel=0.0)
    box("press_die", p["iron_dk"], (x, y, z - 0.12), (w * 0.8, w * 0.8, 0.14), bevel=0.0)
    box("die_plate", p["ivory"], (x + w / 2 + 0.01, y, z + 0.08), (0.03, w * 0.55, 0.22), bevel=0.0)
    box("die_name", p["iron_dk"], (x + w / 2 + 0.03, y, z + 0.16), (0.02, w * 0.4, 0.04), bevel=0.0)


def ampoule_rack(p, pos, n=3):
    x, y, z = pos
    box("rack", p["iron_dk"], (x, y, z), (0.16, 0.26 * n + 0.1, 0.12), bevel=0.0)
    for i in range(n):
        ampoule(p, (x, y + (i - (n - 1) / 2) * 0.26, z + 0.12))


def h01m_eraser_l1():
    """Apagador I: prensa de estampar quadrada e baixa sob uma chaminé curta; a silhueta é um bloco com cotoco."""
    p = pal()
    pad(p, (3.0, 3.0))
    box("block", p["iron"], (-0.1, 0, 0.1), (2.4, 2.4, 1.0), bevel=0.05, taper=0.95, taper_y=0.95)
    box("block_top", p["iron_lt"], (-0.1, 0, 1.1), (2.3, 2.3, 0.1), bevel=0.02)
    rivet_row(p, -0.9, 0.9, 1.07, 0.9, 5)
    press_head(p, (0.0, 0, 1.2), w=1.2)
    box("press_frame", p["iron_dk"], (-0.5, 0, 1.2), (0.3, 1.6, 0.9), bevel=0.02)
    kit.chimney(p["iron_lt"], p["iron_dk"], p["iron_dk"], (-0.7, -0.8, 1.2), 1.0, radius=0.2)
    smoke_puff(p, (-0.7, -0.8, 2.25), 0.18)
    # Fenda da ampola (duto de entrada) na frente e a saída da descarga.
    box("slot", p["tar"], (1.1, 0.55, 0.45), (0.05, 0.7, 0.4), bevel=0.0)
    ampoule(p, (1.2, 0.4, 0.5))
    ampoule(p, (1.2, 0.7, 0.5))
    pipe(p, (-0.1, -1.2, 0.6), (-0.1, -1.6, 0.6), r=0.07)
    pipe(p, (1.1, -0.5, 0.35), (1.55, -0.5, 0.35), r=0.07)
    valve_cross(p, (1.3, -1.1, 0.1), 1.0)
    drum(p, (-0.8, 1.35, 0.1))


def h01w_eraser_l2():
    """Apagador II: a prensa se parte em duas colunas com a viga entre elas, um garfo, não um andar a mais."""
    p = pal()
    pad(p, (3.0, 3.0))
    box("foot", p["iron_dk"], (0, 0, 0.1), (2.6, 2.6, 0.3), bevel=0.04)
    for s in (-1, 1):
        box("column", p["iron"], (-0.2, s * 0.9, 0.4), (0.7, 0.6, 2.7), bevel=0.04, taper=0.85, taper_y=0.85)
        box("column_cap", p["iron_lt"], (-0.2, s * 0.9, 3.1), (0.85, 0.75, 0.12), bevel=0.02)
        rivet_row(p, s * 0.9 - 0.2, s * 0.9 + 0.2, 0.2, 1.2, 3)
    box("beam", p["iron_lt"], (-0.2, 0, 3.22), (0.8, 2.6, 0.35), bevel=0.04)
    press_head(p, (0.0, 0, 2.0), w=0.9, drop=0.9)
    cyl("press_rod_up", p["iron_dk"], (0.0, 0, 2.4), 0.1, 0.82, sides=8, bevel=0.0)
    ampoule_rack(p, (0.45, -0.9, 0.7))
    ampoule_rack(p, (0.45, 0.9, 1.6))
    plate(p, (0.17, 0.9, 2.35), 0.4, 0.3, tone="iron_lt", lines=2)
    box("plate_II", p["ivory"], (0.22, 0.9, 2.45), (0.02, 0.07, 0.14), bevel=0.0)
    box("plate_II", p["ivory"], (0.22, 0.99, 2.45), (0.02, 0.07, 0.14), bevel=0.0)
    valve_cross(p, (-0.2, 0, 3.55), 0.9)
    pipe(p, (-0.5, -0.9, 0.5), (-1.2, -1.2, 0.3), r=0.07)
    drum(p, (1.1, 1.1, 0.1))


def h01x_eraser_l3():
    """Apagador III: coroa de três cabeças de prensa em anel com UM mastro central, o mais alto e fino dos três."""
    p = pal()
    pad(p, (3.0, 3.0))
    cyl("foot", p["iron_dk"], (0, 0, 0.1), 1.35, 0.3, sides=12, bevel=0.0)
    cyl("drum_base", p["iron"], (0, 0, 0.4), 1.05, 0.8, sides=12, top_radius=0.85, bevel=0.0)
    arc_band("crown", p["iron_lt"], (0, 0, 2.2), 0.9, 1.15, 0.22, segs=12, axis="z")
    for i in range(3):
        a = math.radians(i * 120 + 20)
        x, y = math.cos(a) * 1.02, math.sin(a) * 1.02
        beam("crown_leg", p["iron_dk"], (x * 0.7, y * 0.7, 1.2), (x, y, 2.2), thick=0.14)
        # Cabeça de prensa sobre o anel, com o pistão descendo e a matriz de sangue virada para fora.
        box("head", p["iron_lt"], (x, y, 2.42), (0.6, 0.6, 0.5), bevel=0.03, rot_z=a)
        cyl("head_rod", p["iron_dk"], (x, y, 1.9), 0.07, 0.35, sides=6, bevel=0.0)
        box("head_die", p["blood"], (x + math.cos(a) * 0.31, y + math.sin(a) * 0.31, 2.5), (0.05, 0.4, 0.2), bevel=0.0, rot_z=a)
    cyl("mast", p["iron_lt"], (0, 0, 1.2), 0.14, 3.0, sides=8, top_radius=0.09, bevel=0.0)
    for i in range(3):
        a = math.radians(i * 120 + 80)
        beam("mast_stay", p["iron_dk"], (0, 0, 3.4), (math.cos(a) * 1.1, math.sin(a) * 1.1, 2.3), thick=0.05)
    # Sino de execução num braço e o estandarte com a cruz-de-válvula no fim da linha.
    beam("bell_arm", p["iron_dk"], (0, 0, 3.3), (0.6, 0, 3.3), thick=0.07)
    cyl("exec_bell", p["brass_old"], (0.6, 0, 2.95), 0.1, 0.32, sides=8, top_radius=0.28, bevel=0.0)
    box("banner", p["soot"], (-0.12, 0, 3.55), (0.04, 0.5, 0.7), bevel=0.0)
    valve_cross(p, (0, 0, 4.2), 0.5)
    pipe(p, (0.9, 0, 0.5), (1.3, 0, 0.3), r=0.07)
    drum(p, (1.15, 0.9, 0.1))
    drum(p, (1.15, -0.9, 0.1))


# ---------------------------------------------------------------------------------------------------------
# Fonte de Sangue: o poço da corte
# ---------------------------------------------------------------------------------------------------------


def h025_fountain_of_blood():
    """Torre de captura: sonda de ferro sobre a bacia aberta de óleo-sangue, a mais alta da raça, com bomba de balancim."""
    p = pal()
    pad(p)
    cyl("basin_rim", p["iron_dk"], (0.3, 0, 0.1), 1.35, 0.22, sides=14, top_radius=1.25, bevel=0.0)
    cyl("basin_blood", p["blood"], (0.3, 0, 0.3), 1.12, 0.04, sides=14, bevel=0.0)
    kit.derrick(p["iron_lt"], p["iron_dk"], p["blood"], (0.3, 0, 0.3), base=1.3, top=0.4, height=3.3)
    # Coroa de volantes no topo da sonda.
    for x, y in ((0.3, 0.3), (0.3, -0.3)):
        cyl("crown_pipe", p["iron_lt"], (x, y, 3.65), 0.05, 0.2, sides=6, bevel=0.0)
        wheel(p["blood"], p["blood"], (x, y, 3.87), 0.22)
    cyl("crown_mast", p["iron_lt"], (0.3, 0, 3.65), 0.07, 0.55, sides=6, bevel=0.0)
    # Bomba de balancim: o volante marca o ritmo de 28 s.
    box("pump_post", p["iron"], (-1.15, 0, 0.1), (0.3, 0.6, 1.05), bevel=0.03, taper=0.5, taper_y=1.0)
    beam("walking_beam", p["iron_dk"], (-1.6, 0, 1.2), (-0.35, 0, 1.4), thick=0.18)
    box("beam_head", p["iron_lt"], (-0.4, 0, 1.2), (0.3, 0.25, 0.4), bevel=0.02)
    wheel(p["iron_lt"], p["blood"], (-1.45, 0.4, 0.75), 0.32, axis="y", thick=0.1)
    beam("pitman", p["iron_dk"], (-1.45, 0.4, 0.75), (-1.5, 0.1, 1.15), thick=0.06)
    # Tambores em volta da bacia, cada um com etiqueta de lote; cruz-de-válvula do medidor.
    for a in (-70, -35, 0, 35, 70):
        r = math.radians(a)
        drum(p, (0.3 + math.cos(r) * 1.5, math.sin(r) * 1.5, 0.1))
    valve_cross(p, (-0.7, -1.3, 0.1), 1.0)
    pipe(p, (-0.7, -1.2, 0.35), (-0.1, -0.8, 0.35), r=0.05)


# ---------------------------------------------------------------------------------------------------------
# Jaulas: Lesser Demon Cage -> Greater Demon Cage
# ---------------------------------------------------------------------------------------------------------


def freight_crate(p, pos, size, slat_gap=0.28):
    """Caixa de frete ferroviário: moldura rebitada, ripas à frente com o escuro entre elas, tampa e olhal."""
    x, y, z = pos
    sx, sy, sz = size
    box("crate_core", p["tar"], (x, y, z), (sx - 0.1, sy - 0.1, sz), bevel=0.0)
    for cx, cy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        box("crate_post", p["iron"], (x + cx * (sx / 2 - 0.08), y + cy * (sy / 2 - 0.08), z), (0.16, 0.16, sz), bevel=0.02)
    for dz in (0.0, sz - 0.14):
        for s in (-1, 1):
            box("crate_rail", p["iron_lt"], (x + s * (sx / 2 - 0.04), y, z + dz), (0.08, sy, 0.14), bevel=0.0)
            box("crate_rail", p["iron_lt"], (x, y + s * (sy / 2 - 0.04), z + dz), (sx, 0.08, 0.14), bevel=0.0)
    n = max(2, int((sy - 0.3) / slat_gap))
    for i in range(n + 1):
        yy = y - (sy - 0.32) / 2 + (sy - 0.32) * i / n
        box("crate_slat", p["iron"], (x + sx / 2 - 0.04, yy, z + 0.1), (0.07, 0.1, sz - 0.2), bevel=0.0)
    box("crate_lid", p["iron_lt"], (x, y, z + sz), (sx + 0.06, sy + 0.06, 0.1), bevel=0.03)
    plate(p, (x + sx / 2 + 0.05, y - sy / 2 + 0.4, z + 0.25), 0.4, 0.3, tone="ivory", lines=2)
    ring_pos = (x, y, z + sz + 0.1)
    box("lift_eye", p["iron_dk"], ring_pos, (0.2, 0.2, 0.18), bevel=0.02)


def h01i_lesser_demon_cage():
    """Caixa de frete de trilho sobre vagão plataforma: gaiola de ripas, gancho de içar e respiro de fumaça."""
    p = pal()
    pad(p)
    for y in (-0.8, 0.8):
        box("rail", p["iron_dk"], (0, y, 0.1), (3.4, 0.1, 0.1), bevel=0.0)
    box("flatcar", p["iron"], (0, 0, 0.22), (2.9, 2.2, 0.2), bevel=0.03)
    for x in (-1.0, 1.0):
        for y in (-0.95, 0.95):
            cyl("car_wheel", p["iron_dk"], (x, y, 0.2), 0.2, 0.1, sides=8, bevel=0.0, rot=("X", math.radians(90)))
    freight_crate(p, (-0.1, 0, 0.42), (2.2, 2.0, 1.55))
    kit.chimney(p["iron_lt"], p["iron_dk"], p["iron_dk"], (-0.7, 0.6, 2.05), 0.8, radius=0.14)
    smoke_puff(p, (-0.7, 0.6, 2.9), 0.14)
    valve_cross(p, (0.7, 0.0, 2.1), 1.3)
    # Gancho de içar: corrente do olhal até o gancho, sobre o telhado.
    beam("hook_chain", p["iron_dk"], (0.7, -0.6, 2.1), (0.7, -0.6, 2.5), thick=0.05)
    arc_band("hook", p["iron_lt"], (0.7, -0.6, 2.7), 0.14, 0.22, 0.07, 40, 320, segs=8, axis="y")
    drum(p, (1.4, 1.3, 0.1))


def h026_greater_demon_cage():
    """Pátio de guindaste: duas caixas de frete lado a lado sob um pórtico com correntes e gancho pendurado."""
    p = pal()
    pad(p)
    for y in (-1.0, 1.0):
        box("rail", p["iron_dk"], (0, y, 0.1), (3.4, 0.1, 0.1), bevel=0.0)
    box("flatcar", p["iron"], (0, 0, 0.2), (2.4, 3.2, 0.2), bevel=0.03)
    for s in (-1, 1):
        freight_crate(p, (-0.3, s * 0.82, 0.4), (1.5, 1.4, 1.1))
    # Pórtico: duas pernas em A de cada lado e a viga ao longo de y, com carrinho, corrente e gancho.
    for x in (-0.9, 0.9):
        for s in (-1, 1):
            beam("gantry_leg", p["iron_lt"], (x, s * 1.62, 0.1), (x * 0.9, s * 1.35, 3.4), thick=0.17)
        beam("gantry_beam", p["iron_dk"], (x * 0.9, -1.35, 3.4), (x * 0.9, 1.35, 3.4), thick=0.24)
        beam("gantry_brace", p["iron_dk"], (x, -1.62, 1.2), (x * 0.9, 1.35, 3.1), thick=0.06)
    for y in (-1.35, 1.35):
        beam("gantry_tie", p["iron_dk"], (-0.81, y, 3.4), (0.81, y, 3.4), thick=0.2)
    box("trolley", p["iron"], (0, 0.3, 3.45), (0.9, 0.5, 0.25), bevel=0.03)
    beam("hoist_chain", p["iron_dk"], (0, 0.3, 3.45), (0, 0.3, 2.5), thick=0.06)
    box("hook_block", p["iron_lt"], (0, 0.3, 2.3), (0.3, 0.3, 0.25), bevel=0.02)
    arc_band("hook", p["iron_lt"], (0, 0.3, 2.1), 0.15, 0.23, 0.07, 40, 320, segs=8, axis="y")
    for dy in (-0.3, 0.3):
        beam("sling", p["iron_dk"], (0, 0.3, 2.3), (-0.3, 0.82 + dy, 1.55), thick=0.04)
    # Escape até o ramal do pátio e a cruz-de-válvula na viga.
    pipe(p, (-1.0, 0.9, 1.5), (-1.0, 0.9, 1.9), r=0.08)
    pipe(p, (-1.0, 0.9, 1.5), (-1.7, 1.2, 0.3), r=0.08)
    valve_cross(p, (0.0, -0.6, 3.5), 0.9)
    drum(p, (1.45, 1.3, 0.1))
    drum(p, (1.45, -1.3, 0.1))


# ---------------------------------------------------------------------------------------------------------
# Ruína Mágica
# ---------------------------------------------------------------------------------------------------------


def h05i_magic_ruin():
    """Refinaria tombada: massa quebrada na diagonal com canos à mostra, governador de pressão e o coletor de 8 portas."""
    p = pal()
    pad(p)
    block = box("broken", p["iron"], (-0.5, 0, 0.1), (2.4, 2.6, 1.3), bevel=0.0)
    for v in block.data.vertices:
        if v.co.z > 1.0:
            v.co.z -= max(0.0, (v.co.x + 1.7)) * 0.38 + abs(v.co.y) * 0.1
    box("broken_foot", p["iron_dk"], (-0.5, 0, 0.1), (2.7, 2.9, 0.18), bevel=0.0)
    # Tanque tombado, apoiado de través sobre a quebra.
    cyl("fallen_tank", p["iron_lt"], (-0.5, -0.5, 0.75), 0.6, 1.8, sides=10, bevel=0.0, rot=("Y", math.radians(62)))
    ring_c = (0.2, -0.5, 1.15)
    arc_band("tank_mouth", p["iron_dk"], ring_c, 0.1, 0.5, 0.1, segs=10, axis="x")
    # Canos à mostra saindo da quebra, rebites soltos.
    kit.pipe_run(p["iron_lt"], p["iron_dk"], [(0.1, 0.8, 0.8), (0.3, 0.9, 1.3), (0.8, 1.1, 1.0), (1.0, 1.1, 0.2)], radius=0.08)
    for dy in (-0.7, -0.3, 0.2):
        beam("rebar", p["iron_dk"], (0.1, dy, 1.0), (0.45, dy + 0.15, 1.5), thick=0.06)
    # Governador de pressão: haste alta com o volante em cruz (sem antena).
    cyl("gov_stack", p["iron"], (-1.2, -0.95, 0.28), 0.26, 2.0, sides=8, top_radius=0.2, bevel=0.0)
    ring("gov_band", p["iron_dk"], (-1.2, -0.95, 1.3), 0.23, 0.1, sides=8)
    cyl("gov_weight", p["iron_dk"], (-1.2, -0.95, 2.25), 0.3, 0.14, sides=8, bevel=0.0)
    valve_cross(p, (-1.2, -0.95, 2.35), 1.1)
    # Coletor de 8 portas: um volante por desfecho do Present of Chaos, em cavaletes.
    pipe(p, (1.2, -1.05, 0.5), (1.2, 1.05, 0.5), r=0.08)
    for y in (-1.2, 1.2):
        box("manifold_leg", p["iron_dk"], (1.2, y, 0.1), (0.14, 0.14, 0.4), bevel=0.0)
    for i in range(8):
        y = -0.98 + i * 0.28
        cyl("port", p["iron_lt"], (1.2, y, 0.5), 0.045, 0.24, sides=6, bevel=0.0)
        wheel(p["blood"] if i % 2 == 0 else p["iron_lt"], p["iron_dk"], (1.2, y, 0.78), 0.12)
    # Bandeirolas de quermesse em sangue vivo: a corte vende a loteria como festa.
    for y in (-1.45, 1.45):
        box("bunting_pole", p["iron_dk"], (1.55, y, 0.1), (0.06, 0.06, 1.2), bevel=0.0)
    beam("bunting_line", p["iron_dk"], (1.55, -1.45, 1.25), (1.55, 1.45, 1.1), thick=0.025)
    for i in range(7):
        t = (i + 0.5) / 7
        pennant(p["blood"], (1.55, -1.45 + 2.9 * t, 1.25 - 0.15 * t - 0.27), w=0.24, h=0.26)
    drum(p, (-0.2, 1.45, 0.1))


# ---------------------------------------------------------------------------------------------------------
# Serenidade: o jardim da corte
# ---------------------------------------------------------------------------------------------------------


def swing(p, pos, rope, seat_shift=0.0):
    """Balanço em A com cordas de comprimento diferente: um cai mais que o outro (assimétrico)."""
    x, y, _ = pos
    for s in (-1, 1):
        beam("swing_leg", p["iron_dk"], (x - 0.3, y + s * 0.4, 0.1), (x, y + s * 0.36, 1.1), thick=0.07)
        beam("swing_leg", p["iron_dk"], (x + 0.3, y + s * 0.4, 0.1), (x, y + s * 0.36, 1.1), thick=0.07)
    beam("swing_top", p["iron_lt"], (x, y - 0.4, 1.1), (x, y + 0.4, 1.1), thick=0.08)
    for s in (-0.15, 0.15):
        beam("swing_rope", p["iron_dk"], (x, y + s, 1.1), (x + seat_shift, y + s, 1.1 - rope), thick=0.025)
    box("swing_seat", p["ivory"], (x + seat_shift, y, 1.1 - rope - 0.04), (0.2, 0.4, 0.05), bevel=0.0)


def mask(p, pos, weeping):
    """Máscara de porcelana na grade: sorriso em sangue ou lágrima de cinza; lida como bloco de valor."""
    x, y, z = pos
    cyl("mask", p["ivory"], (x, y, z), 0.2, 0.06, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
    if weeping:
        box("mask_tear", p["iron_dk"], (x + 0.04, y + 0.08, z - 0.05), (0.02, 0.04, 0.2), bevel=0.0)
        box("mask_tear", p["iron_dk"], (x + 0.04, y - 0.08, z - 0.05), (0.02, 0.04, 0.2), bevel=0.0)
    else:
        box("mask_smile", p["blood"], (x + 0.04, y, z - 0.08), (0.02, 0.26, 0.06), bevel=0.0)


def h06o_serenity():
    """O jardim da corte: casa de telhado alto atrás de muro ortogonal, portão-catraca com duas máscaras e pátio de provas."""
    p = pal()
    pad(p)
    # Muro baixo em volta, com o vão do portão na face +x.
    box("wall_back", p["iron"], (-1.68, 0, 0.1), (0.14, 3.4, 0.55), bevel=0.02)
    for s in (-1, 1):
        box("wall", p["iron"], (0, s * 1.68, 0.1), (3.4, 0.14, 0.55), bevel=0.02)
        box("wall_front", p["iron"], (1.68, s * 1.05, 0.1), (0.14, 1.3, 0.55), bevel=0.02)
        box("gate_post", p["iron_dk"], (1.68, s * 0.5, 0.1), (0.2, 0.2, 1.2), bevel=0.02)
    # Casa de telhado alto: corpo, telhado de duas águas, chaminé e a cruz-de-válvula na cumeeira.
    box("house", p["iron_lt"], (-0.95, 0, 0.1), (1.5, 2.3, 1.3), bevel=0.04)
    prism("house_roof", p["soot"], (-0.95, 0, 1.4), (1.8, 2.5, 1.0), ridge=0.5, bevel=0.03)
    box("house_door", p["tar"], (-0.18, 0, 0.1), (0.06, 0.55, 0.85), bevel=0.0)
    for y in (-0.8, 0.8):
        kit.window(p["iron_dk"], p["glass"], (-0.2, y, 0.65), "x+", w=0.2, h=0.36)
    valve_cross(p, (-0.95, 0, 2.3), 1.4)
    # Portão-catraca: poste com braços de volante e as máscaras sorriso e choro na grade.
    cyl("turnstile_post", p["iron_lt"], (1.68, 0, 0.1), 0.07, 0.8, sides=8, bevel=0.0)
    for ang in (0.0, math.pi / 2):
        c, s = 0.3 * math.cos(ang), 0.3 * math.sin(ang)
        beam("turnstile_arm", p["iron_dk"], (1.68 - c, -s, 0.75), (1.68 + c, s, 0.75), thick=0.05)
    beam("gate_bar", p["iron_dk"], (1.68, -0.5, 1.15), (1.68, 0.5, 1.15), thick=0.07)
    mask(p, (1.8, -0.5, 1.0), weeping=True)
    mask(p, (1.8, 0.5, 1.0), weeping=False)
    # Placa de anúncio "Serenity" com o selo estampado, no muro.
    plate(p, (1.78, 1.2, 0.55), 0.7, 0.4, tone="ivory", lines=2)
    box("ad_seal", p["blood"], (1.82, 1.2, 0.7), (0.02, 0.1, 0.1), bevel=0.0)
    # Pátio de provas: vaso de pressão, dois balanços assimétricos e o ralo.
    cyl("test_vessel", p["iron"], (0.55, 0.55, 0.1), 0.34, 0.9, sides=10, top_radius=0.28, bevel=0.0)
    ring("test_band", p["iron_dk"], (0.55, 0.55, 0.5), 0.31, 0.08, sides=10)
    dome("test_head", p["iron_lt"], (0.55, 0.55, 1.0), 0.28, squash=0.8, sides=10)
    swing(p, (0.65, -0.7, 0), rope=0.75, seat_shift=0.18)
    swing(p, (0.15, 1.1, 0), rope=0.5)
    box("sump", p["tar"], (0.9, -0.05, 0.1), (0.5, 0.5, 0.02), bevel=0.0)
    for y in (-0.15, -0.05, 0.05):
        box("sump_grate", p["iron_dk"], (0.9, y, 0.12), (0.5, 0.03, 0.02), bevel=0.0)
    drum(p, (-0.2, -1.4, 0.1))


# ---------------------------------------------------------------------------------------------------------
# Santuário da Destruição: altar-medidor
# ---------------------------------------------------------------------------------------------------------


def h01e_shrine_of_destruction():
    """Altar-medidor: laje de sacrifício diante de um mostrador gigante com agulha e o martelo de prensa suspenso."""
    p = pal()
    pad(p)
    box("slab_foot", p["iron_dk"], (0.55, 0, 0.1), (2.0, 2.6, 0.22), bevel=0.03)
    box("slab", p["iron"], (0.55, 0, 0.3), (1.8, 2.3, 0.4), bevel=0.04, taper=0.9, taper_y=0.9)
    box("slab_top", p["iron_lt"], (0.55, 0, 0.7), (1.5, 2.0, 0.05), bevel=0.0)
    box("blood_channel", p["ink"], (0.55, 0, 0.75), (1.3, 0.14, 0.02), bevel=0.0)
    # Mostrador gigante em quadro de ferro, virado para +x.
    for y in (-1.35, 1.35):
        box("dial_post", p["iron_dk"], (-1.1, y, 0.1), (0.3, 0.3, 3.1), bevel=0.03, taper=0.8, taper_y=0.8)
    arc_band("dial_rim", p["iron_lt"], (-1.1, 0, 2.2), 1.0, 1.25, 0.3, segs=16, axis="x")
    cyl("dial_face", p["ivory"], (-1.15, 0, 2.2), 1.0, 0.1, sides=16, bevel=0.0, rot=("Y", math.radians(90)))
    for i in range(10):
        a = math.radians(210 - i * 24)
        box("dial_tick", p["iron_dk"], (-1.0, math.cos(a) * 0.86, 2.2 + math.sin(a) * 0.86), (0.04, 0.06, 0.14), bevel=0.0, rot_z=0.0)
    beam("dial_needle", p["blood"], (-0.98, 0, 2.2), (-0.98, 0.55, 2.78), thick=0.07)
    cyl("dial_hub", p["iron_dk"], (-1.0, 0, 2.2), 0.14, 0.14, sides=8, bevel=0.0, rot=("Y", math.radians(90)))
    # Martelo de prensa pendurado no pórtico do mostrador, em cima da laje.
    beam("gantry", p["iron_dk"], (-1.1, -1.35, 3.1), (0.55, -1.35, 3.1), thick=0.14)
    beam("gantry", p["iron_dk"], (-1.1, 1.35, 3.1), (0.55, 1.35, 3.1), thick=0.14)
    beam("gantry_cross", p["iron_dk"], (0.55, -1.35, 3.1), (0.55, 1.35, 3.1), thick=0.16)
    for dy in (-0.3, 0.3):
        beam("hammer_chain", p["iron_dk"], (0.55, dy, 3.05), (0.55, dy, 2.2), thick=0.04)
    box("hammer", p["iron_lt"], (0.55, 0, 1.55), (0.9, 0.8, 0.6), bevel=0.04)
    box("hammer_face", p["iron_dk"], (0.55, 0, 1.4), (0.7, 0.6, 0.16), bevel=0.0)
    # Válvula-mestra acorrentada e o tambor de oferenda ligado ao duto do piso.
    valve_cross(p, (1.3, -0.95, 0.1), 1.3, hand="blood")
    beam("master_chain", p["iron_dk"], (1.3, -1.05, 0.5), (1.3, -0.85, 0.8), thick=0.04)
    drum(p, (1.4, 0.9, 0.1))
    pipe(p, (1.3, 0.8, 0.14), (0.75, 0.0, 0.14), r=0.06)


# ---------------------------------------------------------------------------------------------------------
# Vulcão: poço selado
# ---------------------------------------------------------------------------------------------------------


def h01f_volcano():
    """Poço jorrante selado: cone de basalto com cintas de ferro, canos de alívio, bateria de manômetros e coroa de volantes."""
    p = pal()
    pad(p)
    cyl("footing", p["iron_dk"], (0, 0, 0.1), 1.7, 0.25, sides=8, bevel=0.0)

    def cone_r(z):
        return 1.5 - (z - 0.35) / 2.4 * 0.85

    cyl("cone", p["iron"], (0, 0, 0.35), 1.5, 2.4, sides=8, top_radius=0.65, bevel=0.03)
    cyl("crater_seal", p["iron_dk"], (0, 0, 2.7), 0.72, 0.16, sides=8, bevel=0.0)
    cyl("crater_oil", p["blood"], (0, 0, 2.84), 0.5, 0.04, sides=8, bevel=0.0)
    for z in (0.8, 1.5, 2.2):
        ring("cone_band", p["iron_dk"], (0, 0, z), cone_r(z), 0.12, thick=0.1, sides=8)
    # Gaiola de montantes de ferro em volta do cone.
    for i in range(8):
        a = math.radians(i * 45 + 22.5)
        beam("cage_strut", p["iron_lt"], (math.cos(a) * 1.72, math.sin(a) * 1.72, 0.3), (math.cos(a) * 0.78, math.sin(a) * 0.78, 2.78), thick=0.08)
    # Canos de alívio subindo pelos flancos.
    for deg in (100, 200, 310):
        a = math.radians(deg)
        c, s = math.cos(a), math.sin(a)
        kit.pipe_run(p["iron_lt"], p["iron_dk"], [(c * 1.62, s * 1.62, 0.3), (c * 1.35, s * 1.35, 1.7), (c * 0.85, s * 0.85, 2.85)], radius=0.07)
    # Bateria de manômetros no pé, virada para +x.
    box("gauge_panel", p["iron_dk"], (1.55, 0, 0.3), (0.14, 1.7, 0.6), bevel=0.02)
    for i in range(4):
        y = -0.6 + i * 0.4
        cyl("gauge", p["ivory"], (1.65, y, 0.45), 0.15, 0.05, sides=10, bevel=0.0, rot=("Y", math.radians(90)))
        beam("gauge_needle", p["blood"], (1.68, y, 0.45), (1.68, y + 0.05, 0.56), thick=0.025)
    # Coroa de volantes no cume e a cruz-de-válvula central.
    for k in range(5):
        a = k * math.tau / 5
        x, y = math.cos(a) * 0.5, math.sin(a) * 0.5
        cyl("crown_pipe", p["iron_lt"], (x, y, 2.86), 0.05, 0.3, sides=6, bevel=0.0)
        wheel(p["blood"] if k % 2 == 0 else p["iron_lt"], p["iron_dk"], (x, y, 3.2), 0.2)
    valve_cross(p, (0, 0, 2.86), 1.0)
    drum(p, (1.3, 1.4, 0.1))


BUILDINGS = {
    "h01C": h01c_altar_of_greed,
    "h01D": h01d_chaos_citadel,
    "h03G": h03g_greater_chaos_citadel,
    "h007": h007_demon_gate,
    "h009": h009_dragon_nest,
    "h01M": h01m_eraser_l1,
    "h01W": h01w_eraser_l2,
    "h01X": h01x_eraser_l3,
    "h025": h025_fountain_of_blood,
    "h01I": h01i_lesser_demon_cage,
    "h026": h026_greater_demon_cage,
    "h05I": h05i_magic_ruin,
    "h06O": h06o_serenity,
    "h01E": h01e_shrine_of_destruction,
    "h01F": h01f_volcano,
}


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["all"]
    names = list(BUILDINGS) if args[0] == "all" else [args[0]]
    out_dir = args[args.index("--out") + 1] if "--out" in args else ""
    render_dir = args[args.index("--render") + 1] if "--render" in args else ""
    # Prévia mais folgada que a do kit: o recorte padrão corta o pé do prédio na vista de +x.
    shoot = kit.render
    kit.render = lambda path, yaw, span, top, **kw: shoot(path, yaw, span=span * 1.25, top=top * 0.7, **kw)
    for name in names:
        kit.build(name, out_dir, render_dir, make=BUILDINGS[name], views=(("front", -35.0),))


if __name__ == "__main__":
    main()
