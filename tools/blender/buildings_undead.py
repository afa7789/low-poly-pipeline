"""Prédios da raça Undead modelados por script (redesenho de reports/design/race-undead.md): um GLB por prédio.

Uso:
    blender -b --factory-startup --python tools/blender/buildings_undead.py -- <id|all> [--out DIR] [--render DIR]

A Fábrica de Carne: os mortos são a mão de obra recolhida do diesel, e cada prédio é um posto de contagem.
Osso cru (estrutura, gaiolas, costelas, caveiras empilhadas e contadas), couro, lona alcatroada, ferro de
remendo, tijolo e pedra; piche preto só nas juntas e nos detalhes; o único acento é o verde ecto, pequeno e
emissivo. Regras da raça em todo prédio: um tambor de resina com o gotejo ecto, uma mangueira grossa em arco
ligando o tambor à construção (a rede de óleo subterrânea, nunca rádio), lama no chão e osso à vista como
material. A mortalha vem do matiz e dos acentos, não do valor baixo. Pegada até ~3,5 x 3,5 centrada na origem,
a frente/porta virada para +x; o jogo normaliza o tamanho, põe o prédio no plinto do time e desenha a bandeira.
"""

import itertools
import math
import os
import sys

from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_paths  # noqa: E402
import map_castles as kit
from map_castles import beam, box, cyl, mat, prism, ring

HALF_PI = math.radians(90)


def pal():
    return {
        "bone": mat("bone", 0xDDD5BF),
        "bone_dk": mat("bone_dark", 0xB3A98F),
        "bone_lt": mat("bone_light", 0xF1EBDA),
        "leather": mat("leather", 0xA8764F),
        "leather_dk": mat("leather_dark", 0x7A5640),
        "stone": mat("stone", 0xADA896),
        "stone_dk": mat("stone_dark", 0x827E70),
        "stone_lt": mat("stone_light", 0xCCC6B2),
        "brick": mat("brick", 0xB06A50),
        "brick_dk": mat("brick_dark", 0x85503F),
        "canvas": mat("tar_canvas", 0x808C76),
        "canvas_dk": mat("tar_canvas_dark", 0x5B6451),
        "canvas_lt": mat("canvas_light", 0xA3AE95),
        "tar": mat("resin_tar", 0x2C2B33),
        "iron": mat("smoked_iron", 0x8A9098),
        "iron_dk": mat("smoked_iron_dark", 0x5E636B),
        "timber": mat("timber", 0xAA865C),
        "timber_dk": mat("timber_dark", 0x76593F),
        "hay": mat("hay", 0xD6B864),
        "hay_dk": mat("hay_dark", 0xB08F48),
        "sack": mat("sack", 0xC4B088),
        "clay": mat("clay", 0xA27D5A),
        "mud": mat("mud", 0x6E5D48),
        "slate": mat("slate", 0x474E55),
        "smoke": mat("pale_vapor", 0xD3E8DD),
        "ecto_dk": mat("ecto_paint", 0x2E9F5E),
        "ecto": mat("ecto", 0x4DEB7E, emit=3.0),
    }


# ---------------------------------------------------------------------------------------------------------
# Peças da raça
# ---------------------------------------------------------------------------------------------------------


def pad(p, size=(3.5, 3.5)):
    """Chão de lama do tamanho do conteúdo: o jogo normaliza pelo maior lado."""
    box("pad", p["mud"], (0, 0, 0), (size[0], size[1], 0.1), bevel=0.03)


def tilt(obs, axis, angle, pivot):
    """Gira objetos já criados em torno de um pivô (antes dos modificadores): o que está torto."""
    rot = Matrix.Rotation(angle, 3, axis)
    pv = Vector(pivot)
    for ob in obs:
        for v in ob.data.vertices:
            v.co = pv + rot @ (v.co - pv)


def lean(ob, base_z, dx=0.0, dy=0.0):
    """Inclina o objeto cisalhando: cada vértice desliza proporcional à altura sobre base_z."""
    for v in ob.data.vertices:
        h = v.co.z - base_z
        v.co.x += dx * h
        v.co.y += dy * h


def ball(name, material, center, radius, scale=(1, 1, 1), segs=6, rings=4):
    import bmesh

    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=radius)
    for v in bm.verts:
        v.co.x *= scale[0]
        v.co.y *= scale[1]
        v.co.z *= scale[2]
    bmesh.ops.translate(bm, verts=bm.verts, vec=center)
    return kit._finish(bm, name, material)


def barrel(p, pos):
    """Regra da raça: o tambor de resina preta, cintado, com o bujão e o gotejo ecto."""
    x, y, z = pos
    cyl("resin_drum", p["tar"], (x, y, z), 0.17, 0.42, sides=10, bevel=0.0)
    for dz in (0.1, 0.3):
        ring("resin_band", p["iron_dk"], (x, y, z + dz), 0.17, 0.04, thick=0.015, sides=10)
    cyl("resin_bung", p["ecto"], (x + 0.06, y, z + 0.42), 0.05, 0.03, sides=6, bevel=0.0)
    box("resin_drip", p["ecto"], (x + 0.17, y, z + 0.1), (0.03, 0.05, 0.28), bevel=0.0)
    box("resin_pool", p["ecto"], (x + 0.24, y, z), (0.2, 0.2, 0.012), bevel=0.0)


def hose(p, a, b, rise=0.32, n=5, thick=0.075):
    """Mangueira grossa em arco (a rede de óleo): sobe e desce entre dois pontos."""
    pts = [Vector(a).lerp(Vector(b), i / n) + Vector((0, 0, rise * math.sin(math.pi * i / n))) for i in range(n + 1)]
    for s, e in itertools.pairwise(pts):
        beam("hose", p["tar"], s, e, thick=thick)
    for end in (a, b):
        box("hose_clamp", p["iron_dk"], (end[0], end[1], end[2] - 0.05), (0.13, 0.13, 0.1), bevel=0.0)


def lamp(p, pos, post=0.0):
    """Lanterna ecto: vidro verde emissivo, pequena."""
    x, y, z = pos
    if post > 0.0:
        box("lamp_post", p["timber_dk"], (x, y, z), (0.07, 0.07, post), bevel=0.0)
        z += post
    box("lamp_base", p["iron_dk"], (x, y, z), (0.16, 0.16, 0.04), bevel=0.0)
    box("lamp_glass", p["ecto"], (x, y, z + 0.04), (0.11, 0.11, 0.14), bevel=0.0)
    box("lamp_cap", p["iron_dk"], (x, y, z + 0.18), (0.18, 0.18, 0.05), bevel=0.0, taper=0.4, taper_y=0.4)


def skull(p, pos, r=0.2, tone="bone"):
    """Caveira de frente para +x; pos é a base."""
    x, y, z = pos
    ball("skull", p[tone], (x, y, z + r), r, scale=(1.0, 0.9, 0.95))
    box("jaw", p["bone_dk"], (x + r * 0.35, y, z), (r * 0.8, r * 0.9, r * 0.5), bevel=0.0)
    for s in (-1, 1):
        box("eye", p["tar"], (x + r * 0.78, y + s * r * 0.36, z + r * 0.95), (r * 0.18, r * 0.34, r * 0.34), bevel=0.0)


def bone(p, a, b, t=0.06, tone="bone"):
    """Osso longo: viga com as duas cabeças."""
    beam("bone", p[tone], a, b, thick=t)
    for e in (a, b):
        box("bone_knob", p[tone], (e[0], e[1], e[2] - t * 0.9), (t * 2.1, t * 2.1, t * 1.8), bevel=0.0)


def skeleton(p, pos, h=1.0):
    """Esqueleto montado de pé (o produto do posto): coluna, costelas, pelve, braços, pernas e caveira."""
    x, y, z = pos
    beam("spine", p["bone"], (x, y, z + h * 0.4), (x, y, z + h * 0.88), thick=0.05)
    for i in range(3):
        box("rib", p["bone_lt"], (x, y, z + h * (0.55 + i * 0.1)), (0.14, 0.34 - i * 0.06, 0.04), bevel=0.0)
    box("pelvis", p["bone"], (x, y, z + h * 0.36), (0.14, 0.3, 0.08), bevel=0.0)
    for s in (-1, 1):
        bone(p, (x, y + s * 0.1, z + h * 0.36), (x, y + s * 0.14, z + 0.04), t=0.045)
        bone(p, (x, y + s * 0.17, z + h * 0.78), (x + 0.1, y + s * 0.26, z + h * 0.5), t=0.04)
    skull(p, (x, y, z + h * 0.88), r=0.1)


def rib_arch(p, x, half, height, thick=0.17, segs=7):
    """Costela gigante em arco, no plano yz: o arco do pátio de desmanche."""
    pts = [(x, half * math.cos(math.pi * i / segs), height * math.sin(math.pi * i / segs) + 0.1) for i in range(segs + 1)]
    for i, (a, b) in enumerate(itertools.pairwise(pts)):
        beam("rib", p["bone"], a, b, thick=thick * (1.1 - 0.55 * math.sin(math.pi * (i + 0.5) / segs)))
    for end in (pts[0], pts[-1]):
        box("rib_foot", p["bone_dk"], (x, end[1], 0.1), (0.3, 0.3, 0.16), bevel=0.02)


def slate_board(p, pos, rot_z=0.0, lines=3, size=(0.07, 0.6, 0.5)):
    """Lousa de giz num cavalete, de frente para +x quando rot_z = 0."""
    x, y, z = pos
    c, s = math.cos(rot_z), math.sin(rot_z)
    box("slate_leg", p["timber_dk"], (x, y, z), (0.08, size[1] + 0.06, 0.18), bevel=0.0, rot_z=rot_z)
    box("slate_board", p["slate"], (x, y, z + 0.18), size, bevel=0.0, rot_z=rot_z)
    for i in range(lines):
        box("slate_chalk", p["bone_lt"], (x + c * 0.04, y + s * 0.04, z + 0.28 + i * 0.12), (0.02, size[1] * 0.72 - 0.07 * i, 0.03), bevel=0.0, rot_z=rot_z)


def sack(p, pos, rot_z=0.0, tone="sack", size=(0.46, 0.3, 0.2)):
    box("sack", p[tone], pos, size, bevel=0.05, taper=0.86, taper_y=0.86, rot_z=rot_z)


def wheel(p, pos, r, tone="timber_dk"):
    """Roda de carroça com o eixo ao longo de y: aro, cubo e quatro raios."""
    x, y, z = pos
    cyl("wheel", p[tone], (x, y - 0.05, z), r, 0.1, sides=10, bevel=0.0, rot=("X", HALF_PI))
    cyl("wheel_hub", p["iron_dk"], (x, y - 0.09, z), r * 0.22, 0.18, sides=6, bevel=0.0, rot=("X", HALF_PI))
    for k in range(4):
        a = k * math.pi / 4
        beam("spoke", p["timber"], (x - math.cos(a) * r * 0.9, y, z - math.sin(a) * r * 0.9), (x + math.cos(a) * r * 0.9, y, z + math.sin(a) * r * 0.9), thick=0.06)


def chapel(p, cx, cy, w, ln, wall_h, rise, wall="stone", roof="canvas", base=0.1):
    """Corpo de duas águas com a cumeeira ao longo de x (empena na face +x)."""
    box("body", p[wall], (cx, cy, base), (ln, w, wall_h), bevel=0.03)
    prism("roof", p[roof], (cx, cy, base + wall_h), (w + 0.24, ln + 0.2, rise), rot_z=HALF_PI)


def bone_stack(p, x0, y, rows=3, cols=5):
    """Ossos longos empilhados em fiadas, como contabilidade, ao longo de uma parede."""
    for row in range(rows):
        for k in range(cols):
            x = x0 + k * 0.5 + 0.08 * (row % 2)
            bone(p, (x, y - 0.02 * row, 0.2 + row * 0.12), (x + 0.4, y, 0.2 + row * 0.12), t=0.045, tone="bone" if (k + row) % 2 else "bone_dk")


def hooks(p, loaded, empty=()):
    """Ganchos pendurados do trilho em y = 0: os carregados levam uma peça embrulhada em couro."""
    for x in (*loaded, *empty):
        beam("hook_chain", p["tar"], (x, 0, 1.9), (x, 0, 1.55), thick=0.03)
        box("hook", p["iron"], (x, 0, 1.45), (0.07, 0.1, 0.12), bevel=0.0)
    for x in loaded:
        box("carcass", p["leather"], (x, 0, 0.4), (0.38, 0.38, 1.05), bevel=0.05, taper=0.55, taper_y=0.6)


def vapor(p, pos, r=0.2, h=0.7, n=3):
    """Penacho de vapor pálido (a única 'fumaça' permitida): três bolotas que sobem e se afastam."""
    x, y, z = pos
    for k in range(n):
        dx, dy = (0.3, -0.2) if k % 2 else (-0.2, 0.3)
        ball("vapor", p["smoke"], (x + dx * r * k, y + dy * r * k, z + r * 0.6 + h / n * k), r * (1.0 - 0.4 * k / n), scale=(1, 1, 0.9), segs=6, rings=3)


# ---------------------------------------------------------------------------------------------------------
# Prédios
# ---------------------------------------------------------------------------------------------------------


def h01Q_city_of_decay():
    """Catedral-refinaria: nave em cruz com o telhado aberto, quatro chaminés de tijolo, andaime e o sino-tanque."""
    p = pal()
    pad(p)
    box("nave_foot", p["stone_dk"], (-0.35, 0, 0.1), (3.0, 1.5, 0.14), bevel=0.02)
    box("nave", p["stone"], (-0.35, 0, 0.2), (2.9, 1.3, 1.4), bevel=0.03)
    box("transept", p["stone"], (-0.5, 0, 0.2), (1.2, 3.0, 1.25), bevel=0.03)
    prism("nave_roof", p["canvas"], (-1.05, 0, 1.6), (1.5, 1.4, 0.7), rot_z=HALF_PI)
    prism("transept_roof", p["canvas"], (-0.5, 0, 1.45), (1.4, 3.1, 0.6))
    # Nave da frente destelhada: os caibros de osso ficam à mostra.
    for x in (0.35, 0.8):
        for s in (-1, 1):
            beam("rafter", p["bone"], (x, s * 0.68, 1.6), (x, 0, 2.3), thick=0.09)
        beam("tie", p["bone_dk"], (x, -0.68, 1.6), (x, 0.68, 1.6), thick=0.07)
    prism("gable_wall", p["stone"], (1.0, 0, 1.6), (1.45, 0.22, 0.7), rot_z=HALF_PI)
    # Janela-grelha: o vitral virou grade soprando ecto.
    kit.window(p["tar"], p["ecto"], (1.1, 0, 0.85), "x+", w=0.38, h=0.75)
    for y in (-0.12, 0.12):
        box("grille_bar", p["tar"], (1.17, y, 0.5), (0.03, 0.04, 0.72), bevel=0.0)
    for x in (-0.85, -0.2):
        kit.window(p["tar"], p["ecto"], (x, 1.5, 0.8), "y+", w=0.2, h=0.5)
        kit.window(p["tar"], p["ecto"], (x, -1.5, 0.8), "y-", w=0.2, h=0.5)
    # Quatro chaminés de tijolo saindo da nave.
    for pos, h, r in (((-1.4, 0.55, 1.5), 1.9, 0.2), ((-1.4, -0.55, 1.5), 2.3, 0.24), ((-0.5, 1.2, 1.3), 1.8, 0.2), ((-0.5, -1.2, 1.3), 2.1, 0.22)):
        kit.chimney(p["brick"], p["bone_lt"], p["brick_dk"], pos, h, radius=r)
        vapor(p, (pos[0], pos[1], pos[2] + h + 0.05), r=r * 0.8, h=0.45)
    # Contrafortes de osso.
    for x in (0.5, 0.95):
        beam("buttress", p["bone"], (x, -0.65, 1.45), (x, -1.15, 0.12), thick=0.14)
        beam("buttress", p["bone"], (x, 0.65, 1.45), (x, 1.15, 0.12), thick=0.14)
    # Andaime na frente, do lado +y.
    for y in (0.4, 1.05):
        beam("scaffold_pole", p["timber_dk"], (1.4, y, 0.1), (1.4, y, 2.1), thick=0.09)
    for z in (1.0, 1.6):
        box("scaffold_plank", p["timber"], (1.27, 0.72, z), (0.4, 0.8, 0.05), bevel=0.0)
    beam("scaffold_brace", p["timber_dk"], (1.4, 0.4, 0.1), (1.4, 1.05, 1.6), thick=0.06)
    beam("scaffold_brace", p["timber_dk"], (1.4, 1.05, 0.1), (1.4, 0.4, 1.6), thick=0.06)
    # O sino rachado de cabeça para cima, virado tanque de ecto, e o cano que desce ao subsolo.
    cyl("bell_vat", p["iron_dk"], (1.15, -1.2, 0.1), 0.2, 0.62, sides=10, top_radius=0.5, bevel=0.0)
    cyl("vat_liquid", p["ecto"], (1.15, -1.2, 0.68), 0.45, 0.03, sides=10, bevel=0.0)
    box("bell_crack", p["tar"], (1.55, -1.2, 0.3), (0.05, 0.05, 0.4), bevel=0.0)
    kit.pipe_run(p["iron_dk"], p["iron"], [(0.8, -1.2, 0.4), (0.45, -1.2, 0.4), (0.45, -1.2, 0.1)])
    box("shaft_hole", p["tar"], (0.45, -1.2, 0.1), (0.4, 0.4, 0.015), bevel=0.0)
    barrel(p, (1.5, 1.45, 0.1))
    hose(p, (1.5, 1.4, 0.4), (1.2, 0.95, 0.35))
    lamp(p, (1.55, -0.45, 0.1), post=0.6)


def h01N_crypt():
    """Cripta: bloco de pedra com o toldo de lona preta de embarque na frente, o caixão de parede e o sino."""
    p = pal()
    pad(p, (3.4, 3.1))
    box("crypt_foot", p["stone_dk"], (-0.3, 0, 0.1), (2.5, 2.4, 0.2), bevel=0.03)
    box("crypt", p["stone"], (-0.35, 0, 0.28), (2.1, 2.1, 1.25), bevel=0.04, taper=0.95, taper_y=0.95)
    box("crypt_slab", p["stone_lt"], (-0.35, 0, 1.5), (2.2, 2.2, 0.14), bevel=0.03)
    box("crypt_cap", p["stone_dk"], (-0.35, 0, 1.64), (1.2, 1.2, 0.7), bevel=0.03, taper=0.35, taper_y=0.35)
    for s_ in (-1, 1):
        skull(p, (-0.35, s_ * 1.14, 1.28), r=0.12)
    # Portal de osso: duas pilastras, verga e a caveira de aviso.
    box("portal", p["tar"], (0.72, 0, 0.28), (0.08, 0.8, 1.05), bevel=0.0)
    for s in (-1, 1):
        box("portal_post", p["bone"], (0.74, s * 0.52, 0.28), (0.18, 0.2, 1.25), bevel=0.02)
    box("portal_lintel", p["bone"], (0.76, 0, 1.28), (0.2, 1.3, 0.2), bevel=0.02)
    skull(p, (0.86, 0, 1.4), r=0.15)
    # Toldo de lona preta de embarque: desce da cripta até os postes, só sobre a porta.
    awn = box("awning", p["canvas_dk"], (1.3, 0, 1.2), (1.2, 1.9, 0.07), bevel=0.0)
    for v in awn.data.vertices:
        v.co.z -= 0.45 * (v.co.x - 0.7) / 1.2
    for y in (-0.6, 0.0, 0.6):
        box("awning_stripe", p["bone_lt"], (1.3, y, 1.25), (1.2, 0.08, 0.02), bevel=0.0)
    for k in range(5):
        box("valance", p["bone_lt"] if k % 2 else p["canvas_dk"], (1.9, -0.8 + k * 0.4, 0.62), (0.05, 0.36, 0.22), bevel=0.0, taper=0.6)
    for s in (-1, 1):
        beam("awning_pole", p["timber_dk"], (1.92, s * 0.92, 0.1), (1.92, s * 0.92, 0.85), thick=0.08)
    # Caixão aberto na parede lateral, com a tampa de linhas de embarque, e o sino de chamada.
    box("coffin_niche", p["tar"], (-0.2, -1.07, 0.45), (0.6, 0.06, 0.95), bevel=0.0, taper=0.7)
    lid = box("coffin_lid", p["leather"], (-0.2, -1.3, 0.4), (0.55, 0.08, 0.95), bevel=0.0, taper=0.7)
    tilt([lid], "X", math.radians(-28), (-0.2, -1.1, 0.45))
    box("coffin_bone", p["bone_lt"], (-0.2, -1.12, 0.5), (0.2, 0.04, 0.5), bevel=0.0, taper=0.6)
    beam("bell_arm", p["iron_dk"], (0.8, 0.62, 1.0), (1.1, 0.62, 1.0), thick=0.05)
    cyl("call_bell", p["iron"], (1.1, 0.62, 0.72), 0.1, 0.22, sides=8, top_radius=0.04, bevel=0.0)
    barrel(p, (1.25, 1.2, 0.1))
    hose(p, (1.2, 1.15, 0.4), (0.8, 0.95, 0.4))
    lamp(p, (1.0, -0.95, 0.1), post=0.5)


def h00A_death_pit():
    """Escritório de baixas: cova no barro com guindaste giratório, escotilha de ferro e o quadro de nomes."""
    p = pal()
    pad(p)
    cyl("clay_rim", p["clay"], (0, 0, 0.1), 1.5, 0.3, sides=12, top_radius=1.28, bevel=0.0)
    cyl("pit_dark", p["tar"], (0, 0, 0.4), 0.9, 0.02, sides=12, bevel=0.0)
    cyl("pit_glow", p["ecto"], (0, 0, 0.42), 0.55, 0.015, sides=10, bevel=0.0)
    # Escotilha de ferro: meia tampa fechada e meia levantada.
    box("hatch_closed", p["iron_dk"], (-0.45, 0, 0.42), (0.9, 1.6, 0.06), bevel=0.0)
    for y in (-0.45, 0.45):
        box("hatch_rib", p["iron"], (-0.45, y, 0.48), (0.9, 0.06, 0.04), bevel=0.0)
    flap = box("hatch_open", p["iron"], (0.0, 0, 0.42), (0.08, 1.2, 0.5), bevel=0.0)
    tilt([flap], "Y", math.radians(-35), (0.0, 0, 0.42))
    # Ossos assentados no aro, contados.
    for i in range(10):
        a = i * math.tau / 10 + 0.2
        bone(p, (math.cos(a) * 1.15, math.sin(a) * 1.15, 0.45), (math.cos(a) * 1.4, math.sin(a) * 1.4, 0.4), t=0.05)
    # Guindaste giratório com a corrente que desce e não volta.
    box("crane_foot", p["stone_dk"], (-1.05, -1.0, 0.1), (0.5, 0.5, 0.2), bevel=0.02)
    beam("crane_post", p["timber_dk"], (-1.05, -1.0, 0.3), (-1.05, -1.0, 3.2), thick=0.2)
    beam("crane_jib", p["timber"], (-1.05, -1.0, 3.1), (0.1, -0.1, 3.05), thick=0.14)
    beam("crane_brace", p["timber_dk"], (-1.05, -1.0, 2.1), (-0.3, -0.45, 3.0), thick=0.09)
    beam("crane_chain", p["tar"], (0.1, -0.1, 3.0), (0.1, -0.1, 1.0), thick=0.05)
    box("crane_hook", p["iron"], (0.1, -0.1, 0.9), (0.14, 0.14, 0.14), bevel=0.0)
    for z in (1.6, 2.1, 2.6):
        box("chain_link", p["iron_dk"], (0.1, -0.1, z), (0.1, 0.1, 0.06), bevel=0.0)
    # Guincho de mão e o quadro de despacho com os nomes a giz.
    for y in (0.55, 1.15):
        box("winch_post", p["timber_dk"], (1.0, y + 0.35, 0.1), (0.1, 0.1, 0.7), bevel=0.0)
    cyl("winch_drum", p["leather"], (1.0, 0.85 + 0.55 - 0.35 + 0.35, 0.7), 0.17, 0.6, sides=8, bevel=0.0, rot=("X", HALF_PI))
    beam("winch_crank", p["iron_dk"], (1.0, 1.65, 0.78), (1.3, 1.65, 0.9), thick=0.04)
    for y in (-1.5, -0.8):
        box("board_post", p["timber_dk"], (1.45, y, 0.1), (0.08, 0.08, 1.7), bevel=0.0)
    box("board", p["slate"], (1.4, -1.15, 0.9), (0.07, 0.95, 0.85), bevel=0.0)
    for i in range(5):
        box("board_name", p["bone_lt"], (1.45, -1.15 + (0.08 if i % 2 else -0.05), 1.0 + i * 0.14), (0.02, 0.55 - 0.07 * (i % 3), 0.04), bevel=0.0)
    barrel(p, (-1.3, 1.1, 0.1))
    hose(p, (-1.25, 1.05, 0.4), (-0.75, 0.55, 0.45))
    lamp(p, (0.9, -1.45, 0.1), post=0.4)


def h03M_defiled_granary():
    """Silo tombado para dentro: o armazém inclinado escorado com vigas, sacos rasgados na porta e poeira no respiro."""
    p = pal()
    pad(p)
    box("granary_foot", p["stone_dk"], (-0.45, 0, 0.1), (2.0, 2.5, 0.14), bevel=0.02)
    body = box("granary", p["timber"], (-0.5, 0, 0.2), (1.7, 2.2, 1.9), bevel=0.0)
    lean(body, 0.2, dy=-0.3)
    for z in (0.7, 1.4):
        band = box("plank_band", p["timber_dk"], (-0.5, 0, z), (1.76, 2.26, 0.09), bevel=0.0)
        lean(band, 0.2, dy=-0.3)
    roof = prism("roof", p["canvas"], (-0.5, -0.55, 2.1), (1.9, 2.2, 0.7), rot_z=HALF_PI)
    tilt([roof], "X", math.radians(-8), (-0.5, -0.55, 2.1))
    # Porta e sacos empilhados até ela, com os rasgos de grão.
    box("door", p["timber_dk"], (0.36, -0.1, 0.2), (0.08, 0.7, 1.1), bevel=0.0)
    skull(p, (0.4, -0.1, 1.35), r=0.12)
    for k, (x, y, z) in enumerate(((0.62, -0.5, 0.1), (0.62, 0.0, 0.1), (0.62, 0.5, 0.1), (0.62, -0.25, 0.3), (0.62, 0.25, 0.3), (0.68, 0.0, 0.5), (0.95, -0.3, 0.1), (0.95, 0.35, 0.1))):
        sack(p, (x, y, z), rot_z=0.2 * (k % 3 - 1))
    box("grain_spill", p["hay"], (0.95, 0.05, 0.1), (0.5, 0.7, 0.04), bevel=0.0)
    for y in (-0.5, 0.3):
        box("sack_tear", p["hay_dk"], (0.86, y, 0.28), (0.04, 0.14, 0.1), bevel=0.0)
    # Escoras de madeira no lado que tomba.
    for x in (-0.95, -0.1):
        beam("shore", p["timber_dk"], (x, -1.72, 0.1), (x + 0.05, -1.5, 1.5), thick=0.14)
    beam("shore_cross", p["timber"], (-0.95, -1.64, 0.5), (-0.1, -1.64, 0.5), thick=0.08)
    # Respiro com a poeira vazando.
    cyl("vent", p["iron_dk"], (-1.0, -0.55, 2.3), 0.14, 0.45, sides=8, top_radius=0.1, bevel=0.0)
    vapor(p, (-1.0, -0.55, 2.75), r=0.16, h=0.7)
    # Elevador de canecas quebrado e balança de viga com pesos de ferro.
    beam("elevator", p["timber_dk"], (1.05, 1.35, 0.1), (0.45, 1.05, 1.9), thick=0.1)
    for t in (0.25, 0.5, 0.75):
        bx = 1.05 + (0.45 - 1.05) * t
        box("bucket", p["iron_dk"], (bx + 0.1, 1.35 + (1.05 - 1.35) * t, 0.1 + 1.8 * t), (0.16, 0.2, 0.14), bevel=0.0)
    box("bucket_fallen", p["iron_dk"], (1.3, 1.2, 0.1), (0.2, 0.22, 0.14), bevel=0.0, rot_z=0.5)
    beam("scale_post", p["timber_dk"], (1.4, -1.0, 0.1), (1.4, -1.0, 1.2), thick=0.08)
    beam("scale_beam", p["iron_dk"], (1.4, -1.45, 1.2), (1.4, -0.55, 1.2), thick=0.05)
    for y in (-1.45, -0.55):
        beam("scale_cord", p["tar"], (1.4, y, 1.2), (1.4, y, 0.8), thick=0.02)
        cyl("scale_pan", p["iron"], (1.4, y, 0.75), 0.17, 0.05, sides=8, bevel=0.0)
    for k in range(3):
        box("scale_weight", p["iron_dk"], (1.4 + 0.04 * k, -1.45 + 0.07 * k, 0.8), (0.08, 0.08, 0.09), bevel=0.0)
    barrel(p, (-1.5, 1.3, 0.1))
    hose(p, (-1.45, 1.25, 0.4), (-1.0, 1.0, 0.55))
    lamp(p, (0.55, 0.95, 0.1), post=0.55)


def h01S_dragon_cemetery():
    """Pátio de desmanche: costelas de dragão em arcos de doca, pórtico içando uma vértebra e o tanque de resina."""
    p = pal()
    pad(p)
    box("yard_slab", p["stone_dk"], (-0.3, 0, 0.1), (2.7, 2.9, 0.1), bevel=0.02)
    for x, h in ((-1.15, 2.3), (-0.45, 2.9), (0.25, 2.5)):
        rib_arch(p, x, 1.15, h)
    for x0, x1 in ((-1.15, -0.45), (-0.45, 0.25)):
        for i in range(3):
            xm = x0 + (x1 - x0) * (i + 0.5) / 3
            cyl("spine_vert", p["bone_dk"], (xm, 0, 2.2 + 0.2 * (1 if x0 > -1 else 0)), 0.14, 0.2, sides=6, bevel=0.0)
    # Pórtico de viga com a vértebra pendurada no ar.
    for s in (-1, 1):
        beam("gantry_leg", p["iron_dk"], (1.0, s * 1.3, 0.1), (1.0, s * 1.3, 3.3), thick=0.15)
        beam("gantry_brace", p["iron_dk"], (1.0, s * 1.3, 0.5), (1.0, s * 0.9, 3.2), thick=0.07)
    beam("gantry_beam", p["iron"], (1.0, -1.4, 3.3), (1.0, 1.4, 3.3), thick=0.17)
    box("trolley", p["iron_dk"], (1.0, 0.2, 3.1), (0.3, 0.3, 0.18), bevel=0.0)
    beam("hoist_chain", p["tar"], (1.0, 0.2, 3.1), (1.0, 0.2, 2.1), thick=0.05)
    cyl("vertebra", p["bone_lt"], (1.0, 0.2, 1.65), 0.32, 0.32, sides=8, bevel=0.02)
    box("vert_spine", p["bone"], (1.0, 0.2, 1.97), (0.14, 0.12, 0.34), bevel=0.0, taper=0.4)
    for s in (-1, 1):
        box("vert_wing", p["bone"], (1.0, 0.2 + s * 0.38, 1.75), (0.14, 0.34, 0.1), bevel=0.0)
        beam("hoist_strap", p["tar"], (1.0, 0.2, 2.1), (1.0, 0.2 + s * 0.3, 1.97), thick=0.03)
    # Trilho com o carrinho de minério carregado de ossos.
    for x in (1.4, 1.72):
        beam("rail", p["iron_dk"], (x, -1.6, 0.12), (x, 1.6, 0.12), thick=0.05)
    for y in (-1.5, -0.8, -0.1, 0.6, 1.3):
        box("sleeper", p["timber_dk"], (1.56, y, 0.1), (0.5, 0.1, 0.04), bevel=0.0)
    box("cart", p["iron_dk"], (1.56, -0.85, 0.28), (0.5, 0.7, 0.34), bevel=0.02, taper=1.0, taper_y=0.9)
    for k in range(3):
        bone(p, (1.4 + 0.08 * k, -1.1 + 0.2 * k, 0.65), (1.72, -1.0 + 0.2 * k, 0.78), t=0.05)
    # Crânio de dragão no canto e o tanque de resina fervendo em ecto.
    ball("dragon_skull", p["bone"], (-1.2, -1.25, 0.35), 0.45, scale=(1.5, 0.8, 0.8), segs=7, rings=4)
    box("dragon_jaw", p["bone_dk"], (-0.75, -1.25, 0.1), (0.9, 0.5, 0.16), bevel=0.0, taper=0.5)
    kit.horn(p["bone"], (-1.4, -1.0, 0.6), (-0.3, 0.9), length=0.6, radius=0.09)
    kit.horn(p["bone"], (-1.4, -1.5, 0.6), (-0.3, -0.9), length=0.6, radius=0.09)
    cyl("resin_tank", p["iron_dk"], (-1.3, 1.25, 0.1), 0.5, 1.1, sides=10, bevel=0.0)
    ring("tank_band", p["iron"], (-1.3, 1.25, 0.6), 0.5, 0.08, sides=10)
    cyl("tank_ecto", p["ecto"], (-1.3, 1.25, 1.2), 0.42, 0.04, sides=10, bevel=0.0)
    vapor(p, (-1.3, 1.25, 1.25), r=0.25, h=0.8)
    barrel(p, (0.0, 1.45, 0.1))
    hose(p, (-0.05, 1.4, 0.4), (-0.85, 1.25, 0.5))
    lamp(p, (-0.55, -1.7, 0.1), post=0.4)


def h054_graveyard():
    """Cartório: lápides padronizadas em fileiras como gavetas, capela-escritório ao fundo e o carrinho de fichas."""
    p = pal()
    pad(p)
    chapel(p, -1.1, 0, 2.0, 1.3, 1.0, 0.75, wall="bone_lt", roof="leather_dk")
    box("office_foot", p["stone_dk"], (-1.1, 0, 0.1), (1.4, 2.2, 0.12), bevel=0.02)
    box("door", p["leather_dk"], (-0.43, 0.55, 0.22), (0.06, 0.4, 0.75), bevel=0.0)
    # Janela do escritório: a mesa e a lousa à vista.
    box("win_frame", p["tar"], (-0.46, -0.35, 0.42), (0.06, 0.75, 0.62), bevel=0.0)
    box("win_glow", p["ecto"], (-0.43, -0.35, 0.47), (0.05, 0.64, 0.52), bevel=0.0)
    box("desk", p["timber"], (-0.38, -0.35, 0.3), (0.2, 0.5, 0.2), bevel=0.0)
    box("desk_slate", p["slate"], (-0.4, -0.55, 0.5), (0.04, 0.2, 0.24), bevel=0.0)
    # Espada de admissão na parede, de ponta para cima, sobre a empena.
    beam("sword_blade", p["iron"], (-0.46, 0, 0.95), (-0.46, 0, 1.6), thick=0.05)
    box("sword_guard", p["bone"], (-0.46, 0, 1.0), (0.05, 0.4, 0.05), bevel=0.0)
    # Fileiras de lápides-gaveta, todas iguais, cada uma com a plaquinha numerada.
    for ix, x in enumerate((0.1, 0.65, 1.2)):
        for iy in range(5):
            y = -1.3 + iy * 0.65
            box("headstone", p["stone_lt"], (x, y, 0.1), (0.28, 0.4, 0.62), bevel=0.02, taper=0.8, taper_y=0.9)
            box("drawer_tag", p["iron_dk"], (x + 0.145, y, 0.4), (0.03, 0.18, 0.1), bevel=0.0)
            box("drawer_slot", p["ecto_dk"] if (ix + iy) % 4 == 0 else p["tar"], (x + 0.145, y, 0.22), (0.03, 0.2, 0.04), bevel=0.0)
    # Carrinho de fichas e a mancha de lama.
    box("file_cart", p["timber"], (-0.3, 1.45, 0.25), (0.6, 0.5, 0.3), bevel=0.02)
    for x in (-0.5, -0.1):
        cyl("cart_wheel", p["timber_dk"], (x, 1.2, 0.25), 0.14, 0.06, sides=8, bevel=0.0, rot=("X", HALF_PI))
    for k in range(3):
        box("file_card", p["bone_lt"], (-0.45 + 0.15 * k, 1.45, 0.55), (0.1, 0.4, 0.28), bevel=0.0)
    barrel(p, (1.5, 1.45, 0.1))
    hose(p, (1.45, 1.4, 0.4), (1.15, 1.15, 0.2), rise=0.25)
    lamp(p, (1.6, -1.55, 0.1), post=0.5)


def h01L_haunted_mine():
    """Poço drenado: torre de extração inclinada, gaiola torta, boca da mina com vapor e piche escorrendo."""
    p = pal()
    pad(p)
    # Monte de rocha com a boca da mina para +x.
    box("mound", p["stone_dk"], (-0.45, -0.3, 0.1), (1.9, 2.0, 1.0), bevel=0.05, taper=0.62, taper_y=0.72)
    box("mouth_hollow", p["tar"], (0.58, 0.0, 0.1), (0.1, 0.8, 0.9), bevel=0.0)
    for s in (-1, 1):
        beam("mouth_post", p["timber_dk"], (0.65, s * 0.5, 0.1), (0.65, s * 0.5, 1.05), thick=0.12)
    beam("mouth_lintel", p["timber"], (0.65, -0.58, 1.05), (0.65, 0.58, 1.05), thick=0.14)
    vapor(p, (0.55, 0.0, 1.15), r=0.34, h=1.4, n=5)
    skull(p, (0.7, 0.0, 1.2), r=0.12)
    # Piche escorrendo da boca, com o brilho ecto onde a luz pousa.
    box("seep", p["tar"], (1.2, 0.0, 0.1), (1.2, 0.7, 0.02), bevel=0.0)
    box("seep", p["tar"], (1.6, -0.15, 0.1), (0.5, 0.5, 0.02), bevel=0.0)
    for x, y in ((1.0, 0.1), (1.5, -0.2)):
        box("seep_glow", p["ecto"], (x, y, 0.12), (0.18, 0.12, 0.012), bevel=0.0)
    # Torre de extração em treliça, tombando; a gaiola pendurada torta.
    kit.derrick(p["iron"], p["iron_dk"], None, (-1.0, 0.8, 0.1), base=1.1, top=0.5, height=3.3, lean=(0.3, -0.6))
    top = (-1.0 + 0.3, 0.8 - 0.6, 3.4)
    cyl("head_wheel", p["leather_dk"], (top[0], top[1] - 0.12, top[2] + 0.05), 0.4, 0.14, sides=10, bevel=0.0, rot=("X", HALF_PI))
    cyl("head_hub", p["iron_dk"], (top[0], top[1] - 0.2, top[2] + 0.05), 0.1, 0.3, sides=6, bevel=0.0, rot=("X", HALF_PI))
    beam("cable_a", p["tar"], (top[0] + 0.3, top[1], top[2] + 0.05), (top[0] + 0.45, top[1] + 0.1, 2.1), thick=0.03)
    beam("cable_b", p["tar"], (top[0] + 0.3, top[1], top[2] + 0.05), (top[0] + 0.2, top[1] - 0.1, 2.05), thick=0.03)
    cx, cy = top[0] + 0.45, top[1] + 0.35
    cage = [box("cage_floor", p["timber_dk"], (cx, cy, 1.25), (0.7, 0.65, 0.07), bevel=0.0),
            box("cage_roof", p["iron_dk"], (cx, cy, 2.0), (0.7, 0.65, 0.06), bevel=0.0),
            box("cage_glow", p["ecto"], (cx, cy, 1.45), (0.3, 0.3, 0.3), bevel=0.0)]
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        cage.append(beam("cage_bar", p["iron"], (cx + sx * 0.3, cy + sy * 0.28, 1.3), (cx + sx * 0.3, cy + sy * 0.28, 2.0), thick=0.06))
    tilt(cage, "Y", math.radians(-14), (cx, cy, 2.1))
    # Guincho manco com a perna quebrada e o sino de alarme na entrada.
    for y in (0.9, 1.5):
        box("winch_post", p["timber_dk"], (0.5, y, 0.1), (0.12, 0.1, 0.8), bevel=0.0)
    cyl("winch_drum", p["leather"], (0.5, 0.9, 0.6), 0.17, 0.6, sides=8, bevel=0.0, rot=("X", HALF_PI))
    beam("winch_crutch", p["timber_dk"], (0.35, 1.2, 0.1), (0.5, 1.2, 0.55), thick=0.07)
    beam("bell_arm", p["iron_dk"], (0.65, -0.62, 1.0), (0.95, -0.85, 1.0), thick=0.05)
    cyl("alarm_bell", p["iron"], (0.95, -0.85, 0.72), 0.12, 0.26, sides=8, top_radius=0.05, bevel=0.0)
    barrel(p, (1.4, 1.2, 0.1))
    hose(p, (1.35, 1.15, 0.4), (0.9, 0.9, 0.5))
    lamp(p, (1.55, -1.1, 0.1), post=0.5)


def h055_high_citadel():
    """Matriz: dois corpos de fábrica com o núcleo alto, chaminé-mestra, coroa de respiros e as torres de elevador."""
    p = pal()
    pad(p)
    # Dois corpos laterais baixos e o núcleo central, mais alto.
    for s in (-1, 1):
        box("wing", p["stone"], (-0.7, s * 1.2, 0.1), (2.2, 1.1, 1.35), bevel=0.04)
        box("wing_cap", p["stone_dk"], (-0.7, s * 1.2, 1.45), (2.3, 1.2, 0.1), bevel=0.02)
        for x in (-1.5, -0.7, 0.1):
            box("bone_pilaster", p["bone"], (x, s * 1.2 + (-0.58 if s > 0 else 0.58) * 0, 0.1), (0.14, 1.14, 1.45), bevel=0.0)
    box("core", p["stone_lt"], (-0.95, 0, 0.1), (1.5, 1.5, 2.1), bevel=0.04)
    box("core_cap", p["stone_dk"], (-0.95, 0, 2.2), (1.6, 1.6, 0.14), bevel=0.02)
    # Coroa oca de respiros em volta da chaminé-mestra.
    for i in range(8):
        a = i * math.tau / 8
        cyl("crown_stack", p["iron_dk"], (-0.95 + math.cos(a) * 0.62, math.sin(a) * 0.62, 2.34), 0.09, 0.62, sides=6, top_radius=0.07, bevel=0.0)
    kit.chimney(p["brick"], p["bone_lt"], p["brick_dk"], (-0.95, 0, 2.34), 1.5, radius=0.3)
    # Janelas de vidro ecto no andar de cima, onde o Diretor aparece.
    for y in (-0.45, 0, 0.45):
        kit.window(p["tar"], p["ecto"], (-0.2, y, 1.65), "x+", w=0.2, h=0.36)
    # Relógio de ponto gigante na fachada e a escada com o cano descendo.
    cyl("clock_rim", p["iron_dk"], (-0.2, 0, 0.55), 0.46, 0.06, sides=12, bevel=0.0, rot=("Y", HALF_PI))
    cyl("clock_face", p["bone_lt"], (-0.15, 0, 0.55), 0.38, 0.04, sides=12, bevel=0.0, rot=("Y", HALF_PI))
    beam("clock_hand", p["tar"], (-0.12, 0, 0.55), (-0.12, 0.0, 0.85), thick=0.04)
    beam("clock_hand", p["tar"], (-0.12, 0, 0.55), (-0.12, 0.22, 0.45), thick=0.04)
    for i in range(3):
        box("step", p["stone_dk"], (0.05 + i * 0.28, 0, 0.1), (0.3, 1.0, 0.1 + 0.07 * (2 - i)), bevel=0.0)
    kit.pipe_run(p["iron_dk"], p["iron"], [(0.1, 0.55, 0.9), (0.1, 0.55, 0.4), (0.9, 0.55, 0.3)])
    # Torres de elevador nas quinas da frente.
    for s in (-1, 1):
        box("lift_tower", p["iron"], (1.15, s * 1.25, 0.1), (0.7, 0.7, 3.0), bevel=0.04, taper=0.9, taper_y=0.9)
        box("lift_cab", p["ecto"], (1.5, s * 1.25, 1.9), (0.04, 0.35, 0.5), bevel=0.0)
        box("lift_roof", p["iron_dk"], (1.15, s * 1.25, 3.1), (0.84, 0.84, 0.12), bevel=0.0)
        for z in (0.7, 1.3):
            box("lift_band", p["iron_dk"], (1.15, s * 1.25, z), (0.74, 0.74, 0.07), bevel=0.0)
    barrel(p, (1.55, 0.2, 0.1))
    hose(p, (1.5, 0.15, 0.4), (0.9, 0.5, 0.35), rise=0.3)
    lamp(p, (1.6, -0.5, 0.1), post=0.5)


def h01R_rotting_hay_cart():
    """Carroça de recrutamento: gaiola de madeira atrás, feno podre transbordando, rodas desparelhas e varais."""
    p = pal()
    pad(p, (3.3, 2.6))
    box("bed", p["timber"], (-0.35, 0, 0.5), (1.9, 1.2, 0.18), bevel=0.02)
    for s in (-1, 1):
        box("bed_side", p["timber_dk"], (-0.35, s * 0.6, 0.66), (1.9, 0.08, 0.3), bevel=0.0)
    box("bed_front", p["timber_dk"], (0.6, 0, 0.66), (0.08, 1.2, 0.3), bevel=0.0)
    # Eixo e rodas de tamanhos diferentes.
    beam("axle", p["iron_dk"], (-0.2, -0.85, 0.5), (-0.2, 0.85, 0.5), thick=0.08)
    wheel(p, (-0.2, -0.78, 0.55), 0.55)
    wheel(p, (-0.2, 0.78, 0.4), 0.4, tone="timber")
    # Gaiola de ripas na traseira.
    for x in (-1.2, -0.7):
        for y in (-0.55, -0.2, 0.2, 0.55):
            beam("cage_bar", p["timber_dk"], (x, y, 0.68), (x, y, 1.65), thick=0.07)
    for y in (-0.55, 0.55):
        beam("cage_rail", p["timber_dk"], (-1.2, y, 1.65), (-0.7, y, 1.65), thick=0.07)
    for z in (0.95, 1.3):
        beam("cage_slat", p["timber"], (-1.2, -0.55, z), (-1.2, 0.55, z), thick=0.06)
    # Feno podre transbordando pela frente da carga.
    for x, y, z, sx, sy, sz in ((0.15, 0, 0.66, 0.9, 1.0, 0.5), (-0.1, -0.2, 0.9, 0.7, 0.8, 0.4), (0.5, 0.4, 0.66, 0.4, 0.5, 0.3), (0.35, -0.7, 0.4, 0.3, 0.3, 0.2)):
        box("hay", p["hay"], (x, y, z), (sx, sy, sz), bevel=0.06, taper=0.7, taper_y=0.7)
    skull(p, (-0.95, -0.3, 0.66), r=0.13)
    skull(p, (-0.95, 0.25, 0.66), r=0.13)
    box("hay_rot", p["hay_dk"], (0.0, 0.1, 1.2), (0.45, 0.5, 0.22), bevel=0.05, taper=0.6, taper_y=0.6)
    # Varais para os zumbis empurrarem; um tombou.
    beam("shaft", p["timber"], (0.6, -0.35, 0.58), (1.75, -0.35, 0.55), thick=0.09)
    beam("shaft_broken", p["timber"], (0.6, 0.35, 0.58), (1.45, 0.35, 0.2), thick=0.09)
    beam("push_bar", p["timber_dk"], (1.7, -0.45, 0.58), (1.7, -0.15, 0.58), thick=0.09)
    # Forcado fincado no feno e a lanterna ecto pendurada no eixo.
    beam("fork_handle", p["timber_dk"], (-0.05, 0.1, 0.9), (0.3, 0.3, 2.0), thick=0.05)
    for dy in (-0.09, 0.0, 0.09):
        beam("fork_tine", p["iron"], (-0.05 + dy * 0.2, 0.1 + dy, 0.9), (-0.07 + dy * 0.2, 0.1 + dy, 1.2), thick=0.025)
    box("fork_head", p["iron"], (-0.06, 0.1, 1.17), (0.05, 0.22, 0.04), bevel=0.0)
    beam("lamp_hook", p["iron_dk"], (-0.5, -0.5, 0.5), (-0.5, -0.5, 0.35), thick=0.03)
    box("lamp_glass", p["ecto"], (-0.5, -0.5, 0.14), (0.12, 0.12, 0.2), bevel=0.0)
    barrel(p, (1.25, 0.95, 0.1))
    hose(p, (1.2, 0.9, 0.4), (0.6, 0.5, 0.6), rise=0.25)


def h01P_skull_pile():
    """Pilha de moldes: caveiras empilhadas como balas de canhão numa grade de aço, e o guindaste de gancho."""
    p = pal()
    pad(p, (3.3, 3.3))
    box("frame_base", p["iron_dk"], (0, 0, 0.1), (1.9, 1.9, 0.12), bevel=0.0)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        beam("frame_post", p["iron_dk"], (sx * 0.9, sy * 0.9, 0.1), (sx * 0.9, sy * 0.9, 1.5), thick=0.1)
    for z in (0.55, 1.5):
        for s in (-1, 1):
            beam("frame_rail", p["iron"], (-0.9, s * 0.9, z), (0.9, s * 0.9, z), thick=0.07)
            beam("frame_rail", p["iron"], (s * 0.9, -0.9, z), (s * 0.9, 0.9, z), thick=0.07)
    # Camadas 3x3, 2x2, 1, como balas de canhão.
    for i in range(3):
        for j in range(3):
            skull(p, (-0.5 + i * 0.5, -0.5 + j * 0.5, 0.22), r=0.21, tone="bone" if (i + j) % 2 else "bone_lt")
    for i in range(2):
        for j in range(2):
            skull(p, (-0.25 + i * 0.5, -0.25 + j * 0.5, 0.58), r=0.21, tone="bone_lt" if (i + j) % 2 else "bone")
    skull(p, (0, 0, 0.9), r=0.21)
    # Guindaste de gancho que ergue o esqueleto montado do molde.
    box("crane_foot", p["stone_dk"], (-1.3, -1.4, 0.1), (0.45, 0.45, 0.16), bevel=0.02)
    beam("crane_post", p["iron_dk"], (-1.3, -1.4, 0.2), (-1.3, -1.4, 3.2), thick=0.16)
    beam("crane_jib", p["iron"], (-1.3, -1.4, 3.1), (0.1, -1.4, 3.1), thick=0.13)
    beam("crane_brace", p["iron_dk"], (-1.3, -1.4, 2.2), (-0.5, -1.4, 3.05), thick=0.08)
    beam("crane_chain", p["tar"], (0.1, -1.4, 3.05), (0.1, -1.4, 2.0), thick=0.04)
    box("crane_hook", p["iron"], (0.1, -1.4, 1.95), (0.14, 0.14, 0.12), bevel=0.0)
    skeleton(p, (0.1, -1.4, 1.0), h=1.0)
    # Cova do molde, o cepo com o machado de limpeza.
    box("mold_pit", p["tar"], (1.15, 0.55, 0.1), (0.8, 0.9, 0.02), bevel=0.0)
    bone(p, (0.95, 0.35, 0.14), (1.4, 0.55, 0.14), t=0.05)
    cyl("stump", p["timber"], (1.2, -0.95, 0.1), 0.25, 0.4, sides=8, bevel=0.0)
    beam("hatchet_handle", p["timber_dk"], (1.2, -0.95, 0.5), (1.35, -0.95, 0.85), thick=0.05)
    box("hatchet_blade", p["iron"], (1.35, -1.0, 0.77), (0.14, 0.04, 0.16), bevel=0.0)
    barrel(p, (1.35, 1.35, 0.1))
    hose(p, (1.3, 1.3, 0.4), (0.95, 0.95, 0.45), rise=0.25)
    lamp(p, (-1.4, 0.9, 0.1), post=0.5)


def h056_skull_shrine():
    """Forno de têmpera e montagem: corpo baixo de tijolo, rampa, coifa de vapor e o gabarito rebitado com o esqueleto."""
    p = pal()
    pad(p, (3.0, 2.8))
    box("furnace_foot", p["stone_dk"], (-0.5, 0, 0.1), (1.8, 1.9, 0.14), bevel=0.02)
    box("furnace", p["brick"], (-0.5, 0, 0.22), (1.6, 1.7, 0.95), bevel=0.04, taper=0.92, taper_y=0.92)
    box("furnace_cap", p["brick_dk"], (-0.5, 0, 1.17), (1.5, 1.6, 0.1), bevel=0.0)
    box("mouth", p["tar"], (0.27, 0, 0.3), (0.06, 0.7, 0.5), bevel=0.0)
    box("mouth_glow", p["ecto"], (0.3, 0, 0.36), (0.04, 0.5, 0.3), bevel=0.0)
    # Coifa de vapor de resina com o cano de saída.
    cyl("hood", p["iron_dk"], (-0.5, 0, 1.27), 0.7, 0.55, sides=8, top_radius=0.2, bevel=0.0)
    ring("hood_band", p["iron"], (-0.5, 0, 1.4), 0.55, 0.07, sides=8)
    cyl("flue", p["iron"], (-0.5, 0, 1.82), 0.16, 0.5, sides=8, bevel=0.0)
    vapor(p, (-0.5, 0, 2.3), r=0.2, h=0.7)
    # Rampa de entrada do cadáver (embrulho de lona amarrado com osso).
    ramp = box("ramp", p["timber"], (1.1, 0, 0.1), (1.4, 1.0, 0.7), bevel=0.0)
    for v in ramp.data.vertices:
        if v.co.x > 1.1 and v.co.z > 0.5:
            v.co.z = 0.16
    box("corpse", p["canvas_lt"], (0.65, 0, 0.62), (0.7, 0.34, 0.2), bevel=0.06, rot_z=0.0)
    box("corpse_tie", p["bone_lt"], (0.65, 0, 0.82), (0.07, 0.36, 0.04), bevel=0.0)
    # Gabarito rebitado: pórtico baixo que entrega o esqueleto montado.
    for s in (-1, 1):
        beam("jig_leg", p["iron_dk"], (1.45, s * 0.75, 0.1), (1.45, s * 0.75, 1.65), thick=0.1)
    beam("jig_beam", p["iron"], (1.45, -0.8, 1.65), (1.45, 0.8, 1.65), thick=0.12)
    for y in (-0.6, -0.3, 0.3, 0.6):
        box("rivet", p["tar"], (1.5, y, 1.6), (0.04, 0.05, 0.05), bevel=0.0)
    skeleton(p, (1.45, 0, 0.2), h=1.3)
    for k in range(3):
        skull(p, (-0.2 + k * 0.28, -1.15, 0.1), r=0.13)
    barrel(p, (-1.3, 1.1, 0.1))
    hose(p, (-1.25, 1.05, 0.4), (-0.9, 0.7, 0.55), rise=0.25)
    lamp(p, (0.4, -1.15, 0.1), post=0.4)


def h01T_slaughter_house():
    """Açougue industrial: galpão baixo com o trilho de ganchos saindo pela fachada, lona rasgada, chaminé e a cuba."""
    p = pal()
    pad(p)
    box("hall_foot", p["stone_dk"], (-0.8, 0, 0.1), (2.1, 3.0, 0.14), bevel=0.02)
    box("hall", p["bone"], (-0.8, 0, 0.2), (1.9, 2.8, 1.1), bevel=0.04)
    for z in (0.5, 0.9):
        box("hall_course", p["bone_lt"], (-0.8, 0, z), (1.94, 2.84, 0.05), bevel=0.0)
    box("hall_roof", p["canvas"], (-1.2, 0, 1.3), (1.3, 3.0, 0.1), bevel=0.0, taper=0.9, taper_y=0.95)
    for y in (-1.35, 1.35):
        beam("roof_post", p["timber_dk"], (-0.55, y, 1.2), (-0.55, y, 1.32), thick=0.1)
    for y in (-1.0, 0.0, 1.0):
        beam("open_rafter", p["bone"], (-0.55, y, 1.3), (0.1, y, 1.3), thick=0.08)
    box("hall_floor", p["tar"], (-0.2, 0, 0.3), (0.7, 2.6, 0.02), bevel=0.0)
    box("block", p["timber"], (-0.15, 0.7, 0.3), (0.4, 0.5, 0.45), bevel=0.02)
    # O trilho de ganchos: do telhado, para fora pela fachada, com as peças penduradas.
    for x in (0.4, 1.5):
        beam("rail_post", p["iron_dk"], (x, 0.0, 0.1), (x, 0.0, 1.9), thick=0.12)
    beam("hook_rail", p["iron"], (-0.8, 0, 1.9), (1.75, 0, 1.9), thick=0.1)
    beam("rail_brace", p["iron_dk"], (0.4, 0, 1.4), (-0.2, 0, 1.9), thick=0.07)
    hooks(p, (-0.4, 0.0, 0.55, 1.5), empty=(1.05,))
    # Lona rasgada cobrindo só a metade -y, com o rasgo no meio.
    for y0, y1 in ((-1.5, -0.8), (-0.55, -0.1)):
        awn = box("awning", p["canvas_lt"], (0.6, (y0 + y1) / 2, 1.3), (1.0, y1 - y0, 0.05), bevel=0.0, taper=1.0, taper_y=0.7)
        for v in awn.data.vertices:
            v.co.z -= 0.45 * (v.co.x - 0.1) / 1.0
        box("awning_tear", p["canvas_dk"], (1.12, (y0 + y1) / 2, 0.76), (0.04, (y1 - y0) * 0.5, 0.22), bevel=0.0, taper=0.4)
    for y in (-1.5, -0.1):
        beam("awning_pole", p["timber_dk"], (1.05, y, 0.1), (1.05, y, 0.9), thick=0.07)
    # Serra de fita manual sob a lona, chaminé baixa, cuba de resina na porta.
    box("saw_table", p["iron_dk"], (0.85, -1.1, 0.1), (0.5, 0.5, 0.4), bevel=0.0)
    for z in (0.65, 0.95):
        cyl("saw_wheel", p["iron"], (0.85, -1.1, z), 0.14, 0.06, sides=8, bevel=0.0, rot=("X", HALF_PI))
    beam("saw_blade", p["iron"], (0.99, -1.1, 0.65), (0.99, -1.1, 0.95), thick=0.025)
    beam("saw_arm", p["iron_dk"], (0.7, -1.1, 0.5), (0.7, -1.1, 1.0), thick=0.05)
    kit.chimney(p["brick"], p["bone_lt"], p["brick_dk"], (-1.3, 1.0, 1.3), 1.1, radius=0.2)
    kit.window(p["tar"], p["ecto"], (0.15, 0.95, 0.75), "x+", w=0.3, h=0.3)
    box("door", p["tar"], (0.16, -0.3, 0.2), (0.06, 0.7, 0.9), bevel=0.0)
    cyl("vat", p["tar"], (1.1, 1.05, 0.1), 0.45, 0.55, sides=10, bevel=0.0)
    ring("vat_band", p["iron_dk"], (1.1, 1.05, 0.35), 0.45, 0.07, sides=10)
    cyl("vat_ecto", p["ecto"], (1.1, 1.05, 0.62), 0.38, 0.03, sides=10, bevel=0.0)
    barrel(p, (1.55, 0.5, 0.1))
    hose(p, (1.5, 0.55, 0.4), (1.2, 0.95, 0.5), rise=0.25)
    lamp(p, (-0.2, -1.5, 0.1), post=0.5)


def h04Z_tainted_farm():
    """Fazenda de estopa: casa de campo com o sapê despencado, o único espantalho respirador e o poço de resina."""
    p = pal()
    pad(p)
    box("house_foot", p["stone_dk"], (-0.7, 0, 0.1), (1.9, 2.2, 0.14), bevel=0.02)
    box("house", p["sack"], (-0.7, 0, 0.2), (1.7, 2.0, 0.95), bevel=0.03)
    for y in (-0.95, -0.35, 0.35, 0.95):
        beam("frame_post", p["timber_dk"], (0.15, y, 0.2), (0.15, y, 1.15), thick=0.09)
    beam("frame_beam", p["timber_dk"], (0.15, -1.0, 1.12), (0.15, 1.0, 1.12), thick=0.09)
    box("door", p["leather_dk"], (0.16, -0.1, 0.22), (0.06, 0.45, 0.75), bevel=0.0)
    kit.window(p["tar"], p["ecto"], (0.15, 0.6, 0.65), "x+", w=0.25, h=0.28)
    # Sapê despencado: a água de trás ainda de pé, a da frente escorregou para o chão.
    roof = prism("thatch", p["hay"], (-1.1, 0.2, 1.15), (2.2, 1.5, 0.8), rot_z=HALF_PI)
    tilt([roof], "X", math.radians(-7), (-1.1, 0.2, 1.15))
    for y in (-0.6, 0.2, 0.9):
        beam("open_rafter", p["timber_dk"], (-0.35, y, 1.15), (0.15, y, 1.15), thick=0.08)
    fall = prism("thatch_fallen", p["hay_dk"], (0.4, -1.15, 0.1), (0.9, 0.9, 0.45), rot_z=0.5)
    del fall
    for x, y, z, a in ((-0.2, 1.15, 1.0, 0.0), (0.3, 0.4, 1.0, 0.4), (-1.5, -0.9, 0.95, 0.2)):
        box("thatch_lump", p["hay_dk"], (x, y, z), (0.5, 0.45, 0.18), bevel=0.05, taper=0.6, taper_y=0.6, rot_z=a)
    # Espantalho de roupa de operário: pano na boca, carimbo no peito.
    sx, sy = 1.25, 0.25
    beam("scarecrow_post", p["timber_dk"], (sx, sy, 0.1), (sx, sy, 1.9), thick=0.09)
    beam("scarecrow_arms", p["timber_dk"], (sx, sy - 0.6, 1.4), (sx, sy + 0.6, 1.4), thick=0.07)
    box("scarecrow_coat", p["canvas"], (sx, sy, 0.85), (0.3, 0.55, 0.65), bevel=0.04, taper=0.8, taper_y=0.8)
    for s in (-1, 1):
        box("scarecrow_sleeve", p["canvas"], (sx, sy + s * 0.5, 1.12), (0.18, 0.3, 0.3), bevel=0.03)
    ball("scarecrow_head", p["sack"], (sx, sy, 1.68), 0.16, segs=6, rings=4)
    skull(p, (1.5, 1.2, 0.1), r=0.1)
    skull(p, (1.5, 1.4, 0.1), r=0.1)
    cyl("respirator", p["iron"], (sx + 0.12, sy, 1.58), 0.08, 0.12, sides=6, bevel=0.0, rot=("Y", HALF_PI))
    box("respirator_cloth", p["canvas_lt"], (sx + 0.1, sy, 1.5), (0.04, 0.22, 0.12), bevel=0.0)
    box("chest_stamp", p["ecto"], (sx + 0.16, sy, 1.1), (0.03, 0.16, 0.16), bevel=0.0)
    # Poço de resina com o balde e a manivela.
    cyl("well", p["stone"], (1.1, -1.2, 0.1), 0.5, 0.42, sides=10, bevel=0.0, top_radius=0.44)
    cyl("well_tar", p["tar"], (1.1, -1.2, 0.5), 0.36, 0.03, sides=10, bevel=0.0)
    for s in (-1, 1):
        beam("well_post", p["timber_dk"], (1.1, -1.2 + s * 0.45, 0.45), (1.1, -1.2 + s * 0.45, 1.3), thick=0.07)
    beam("well_beam", p["timber"], (1.1, -1.7, 1.3), (1.1, -0.7, 1.3), thick=0.07)
    beam("well_rope", p["tar"], (1.1, -1.2, 1.3), (1.1, -1.2, 0.85), thick=0.025)
    cyl("well_bucket", p["iron_dk"], (1.1, -1.2, 0.62), 0.09, 0.2, sides=7, bevel=0.0)
    barrel(p, (-0.2, 1.5, 0.1))
    hose(p, (-0.15, 1.45, 0.4), (0.15, 1.0, 0.45), rise=0.25)
    lamp(p, (1.55, 1.2, 0.1), post=0.5)


def h01K_temple_of_bone():
    """Posto de campo: capela com a armação de osso à vista, ossos empilhados nas paredes e o guincho na porta."""
    p = pal()
    pad(p)
    box("chapel_foot", p["stone_dk"], (-0.5, 0, 0.1), (2.8, 2.1, 0.14), bevel=0.02)
    box("body", p["stone_lt"], (-0.5, 0, 0.22), (2.6, 1.8, 1.0), bevel=0.03)
    prism("roof", p["leather_dk"], (-1.2, 0, 1.22), (2.04, 1.3, 0.85), rot_z=HALF_PI)
    # Metade da frente destelhada: a armação de osso à mostra e o que há dentro.
    for x in (-0.3, 0.2):
        for s in (-1, 1):
            beam("bone_rafter", p["bone"], (x, s * 0.98, 1.22), (x, 0, 2.05), thick=0.09)
    beam("bone_ridge", p["bone"], (-0.55, 0, 2.05), (0.84, 0, 2.05), thick=0.08)
    box("inner_floor", p["tar"], (0.25, 0, 1.2), (1.2, 1.6, 0.02), bevel=0.0)
    for k in range(3):
        bone(p, (-0.1 + 0.3 * k, -0.5, 1.24), (-0.1 + 0.3 * k, 0.5, 1.28), t=0.05)
    skull(p, (0.4, 0.4, 1.22), r=0.13)
    # Armação de osso exposta: pilares, vigas e o tesoura da empena.
    for x in (-1.6, -1.0, -0.4, 0.2, 0.78):
        for s in (-1, 1):
            beam("bone_post", p["bone"], (x, s * 0.92, 0.2), (x, s * 0.92, 1.3), thick=0.12)
    for s in (-1, 1):
        beam("bone_plate", p["bone_dk"], (-1.8, s * 0.94, 1.25), (0.8, s * 0.94, 1.25), thick=0.1)
    beam("truss_a", p["bone"], (0.84, -0.9, 1.22), (0.84, 0, 2.05), thick=0.1)
    beam("truss_b", p["bone"], (0.84, 0.9, 1.22), (0.84, 0, 2.05), thick=0.1)
    beam("truss_tie", p["bone_dk"], (0.84, -0.9, 1.22), (0.84, 0.9, 1.22), thick=0.09)
    box("gable_fill", p["stone_lt"], (0.8, 0, 1.2), (0.08, 1.8, 0.1), bevel=0.0)
    # Porta dupla e as gavetas de caveira ao lado: cada caveira é uma gaveta.
    box("door", p["leather_dk"], (0.82, 0, 0.22), (0.06, 0.7, 0.85), bevel=0.0)
    box("door_split", p["bone_lt"], (0.86, 0, 0.3), (0.02, 0.03, 0.7), bevel=0.0)
    for s in (-1, 1):
        for k in range(3):
            y, z = s * 0.62, 0.3 + k * 0.28
            box("niche", p["tar"], (0.82, y, z), (0.05, 0.22, 0.22), bevel=0.0)
            skull(p, (0.85, y, z + 0.02), r=0.08)
    # Ossos longos empilhados como contabilidade ao longo da parede lateral.
    bone_stack(p, -1.55, -1.2)
    # Guincho na porta, com a mortalha içada, e a lousa do necrotério na janela.
    beam("hoist_post", p["timber_dk"], (1.1, -0.95, 0.1), (1.1, -0.95, 2.2), thick=0.12)
    beam("hoist_jib", p["timber"], (1.1, -0.95, 2.2), (1.45, 0.0, 2.2), thick=0.1)
    beam("hoist_brace", p["timber_dk"], (1.1, -0.95, 1.6), (1.3, -0.5, 2.15), thick=0.06)
    beam("hoist_rope", p["tar"], (1.45, 0.0, 2.2), (1.45, 0.0, 1.35), thick=0.03)
    box("shroud", p["canvas_lt"], (1.45, 0, 0.7), (0.26, 0.26, 0.62), bevel=0.05, taper=0.6, taper_y=0.6)
    beam("shroud_rope", p["tar"], (1.45, 0, 1.3), (1.45, 0, 1.0), thick=0.03)
    kit.window(p["tar"], p["ecto"], (-0.4, -0.93, 0.75), "y-", w=0.4, h=0.3)
    slate_board(p, (-0.4, -1.55, 0.1), rot_z=HALF_PI, lines=3, size=(0.07, 0.5, 0.36))
    barrel(p, (1.4, 1.35, 0.1))
    hose(p, (1.35, 1.3, 0.4), (0.95, 0.95, 0.35), rise=0.25)
    lamp(p, (1.55, -1.45, 0.1), post=0.5)


def h04B_temple_of_necromancy():
    """Seção de engenharia: salão baixo de dois corpos com dois escapes curvos, doca de carga e relógio de ponto."""
    p = pal()
    pad(p)
    box("hall_foot", p["stone_dk"], (-0.5, 0, 0.1), (2.7, 3.3, 0.14), bevel=0.02)
    for s in (-1, 1):
        box("body", p["stone_lt"], (-0.5, s * 1.0, 0.22), (2.4, 1.35, 0.95), bevel=0.03)
        prism("roof", p["canvas"], (-0.95, s * 1.0, 1.17), (1.6, 1.5, 0.65), rot_z=HALF_PI)
        for x in (0.0, 0.45):
            for t in (-1, 1):
                beam("bone_rafter", p["bone"], (x, s * 1.0 + t * 0.68, 1.17), (x, s * 1.0, 1.75), thick=0.08)
        box("bench", p["timber"], (0.2, s * 1.0, 1.17), (0.8, 0.5, 0.2), bevel=0.02)
        # Osso na argamassa: fiadas claras.
        for z in (0.45, 0.8):
            box("mortar_bone", p["bone"], (-0.5, s * 1.0, z), (2.44, 1.39, 0.05), bevel=0.0)
        for x in (-1.5, -0.5, 0.5):
            beam("bone_post", p["bone"], (x, s * 1.0 - s * 0.7, 0.22), (x, s * 1.0 - s * 0.7, 1.15), thick=0.1)
    # Doca de carga entre os corpos: piso de tábua, portão ecto ao fundo, rampa.
    box("dock", p["timber"], (-0.5, 0, 0.2), (2.4, 0.64, 0.08), bevel=0.0)
    box("dock_gate", p["tar"], (-1.65, 0, 0.28), (0.06, 0.55, 0.8), bevel=0.0)
    box("dock_glow", p["ecto"], (-1.6, 0, 0.5), (0.03, 0.4, 0.3), bevel=0.0)
    ramp = box("dock_ramp", p["timber_dk"], (0.7, 0, 0.1), (0.9, 0.7, 0.2), bevel=0.0)
    for v in ramp.data.vertices:
        if v.co.x > 0.9:
            v.co.z = 0.1
    # Dois escapes curvos nas laterais.
    for s in (-1, 1):
        pts = [(-0.9, s * 1.62, 1.2), (-0.9, s * 1.62, 2.3), (-0.65, s * 1.62, 2.8), (-0.2, s * 1.62, 3.0), (0.2, s * 1.62, 2.95)]
        kit.pipe_run(p["iron_dk"], p["iron"], pts, radius=0.12)
        cyl("exhaust_mouth", p["iron"], (0.2, s * 1.62, 2.82), 0.2, 0.3, sides=8, top_radius=0.12, bevel=0.0)
        vapor(p, (0.2, s * 1.62, 3.15), r=0.15, h=0.5)
    # Relógio de ponto e a lousa de contagem na face da frente.
    cyl("clock_rim", p["iron_dk"], (0.72, 1.0, 0.8), 0.27, 0.05, sides=10, bevel=0.0, rot=("Y", HALF_PI))
    cyl("clock_face", p["bone_lt"], (0.76, 1.0, 0.8), 0.22, 0.03, sides=10, bevel=0.0, rot=("Y", HALF_PI))
    beam("clock_hand", p["tar"], (0.79, 1.0, 0.8), (0.79, 1.0, 0.97), thick=0.03)
    slate_board(p, (1.1, -1.0, 0.1), lines=4, size=(0.07, 0.7, 0.55))
    barrel(p, (1.5, 0.3, 0.1))
    hose(p, (1.45, 0.25, 0.4), (1.05, 0.0, 0.3), rise=0.25)
    lamp(p, (1.55, 1.45, 0.1), post=0.5)


def h01O_turret_of_souls():
    """Torre-forno: fornalha de tijolo com a escada de ferro em espiral por fora e a boca de arremesso horizontal."""
    p = pal()
    pad(p, (3.0, 3.0))
    box("foot", p["stone_dk"], (0, 0, 0.1), (2.3, 2.3, 0.3), bevel=0.04, taper=0.94, taper_y=0.94)
    cyl("furnace", p["brick"], (0, 0, 0.4), 0.98, 2.5, sides=8, top_radius=0.78, bevel=0.0)
    for z in (0.9, 1.7, 2.45):
        ring("furnace_band", p["iron_dk"], (0, 0, z), 0.9 - (z - 0.4) * 0.09, 0.1, sides=8)
    cyl("hearth_rim", p["iron_dk"], (0, 0, 2.9), 0.84, 0.18, sides=8, top_radius=0.86, bevel=0.0)
    cyl("hearth_glow", p["ecto"], (0, 0, 3.05), 0.6, 0.04, sides=8, bevel=0.0)
    # A boca de arremesso: garganta grossa e horizontal, nunca uma agulha.
    cyl("throat", p["iron_dk"], (0.4, 0, 2.2), 0.4, 1.2, sides=8, bevel=0.0, rot=("Y", HALF_PI))
    cyl("throat_lip", p["iron"], (1.52, 0, 2.2), 0.5, 0.14, sides=8, bevel=0.0, rot=("Y", HALF_PI))
    cyl("throat_glow", p["ecto"], (1.62, 0, 2.2), 0.3, 0.04, sides=8, bevel=0.0, rot=("Y", HALF_PI))
    for s in (-1, 1):
        beam("throat_strut", p["iron_dk"], (0.5, s * 0.3, 1.2), (1.3, s * 0.4, 2.0), thick=0.08)
    # Respiro curto e gordo atrás.
    cyl("vent", p["brick_dk"], (-0.45, 0, 3.0), 0.26, 0.55, sides=8, top_radius=0.2, bevel=0.0)
    vapor(p, (-0.45, 0, 3.55), r=0.18, h=0.5)
    # Escada de ferro em espiral por fora.
    n = 14
    for i in range(n):
        a = math.radians(200) + i * math.radians(30)
        r = 1.0
        z = 0.45 + i * 0.145
        box("stair_step", p["iron"], (math.cos(a) * r, math.sin(a) * r, z), (0.55, 0.34, 0.05), bevel=0.0, rot_z=a)
        if i % 3 == 0:
            beam("stair_post", p["iron_dk"], (math.cos(a) * 1.24, math.sin(a) * 1.24, z), (math.cos(a) * 1.24, math.sin(a) * 1.24, z + 0.45), thick=0.045)
    # Paiol embutido na base: nicho escuro com as bolas de resina empilhadas.
    box("magazine", p["tar"], (1.14, 0, 0.4), (0.06, 0.7, 0.55), bevel=0.0)
    for k in range(3):
        ball("shot", p["bone_lt"], (1.25, -0.2 + k * 0.2, 0.28), 0.1, segs=6, rings=4)
    barrel(p, (1.25, -1.2, 0.1))
    hose(p, (1.2, -1.15, 0.4), (0.9, -0.5, 0.7), rise=0.3)
    lamp(p, (1.3, 1.1, 0.1), post=0.4)


BUILDINGS = {
    "h01Q": h01Q_city_of_decay,
    "h01N": h01N_crypt,
    "h00A": h00A_death_pit,
    "h03M": h03M_defiled_granary,
    "h01S": h01S_dragon_cemetery,
    "h054": h054_graveyard,
    "h01L": h01L_haunted_mine,
    "h055": h055_high_citadel,
    "h01R": h01R_rotting_hay_cart,
    "h01P": h01P_skull_pile,
    "h056": h056_skull_shrine,
    "h01T": h01T_slaughter_house,
    "h04Z": h04Z_tainted_farm,
    "h01K": h01K_temple_of_bone,
    "h04B": h04B_temple_of_necromancy,
    "h01O": h01O_turret_of_souls,
}


_render = kit.render


def _wide_render(path, yaw_deg, **kw):
    """Prévia com folga: os prédios altos saíam cortados no quadro do kit."""
    kw["span"] = kw["span"] * 1.3
    _render(path, yaw_deg, **kw)


kit.render = _wide_render


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["all"]
    names = list(BUILDINGS) if args[0] == "all" else [args[0]]
    out_dir = game_paths.out_arg(args, "--out", "buildings", "undead")
    render_dir = args[args.index("--render") + 1] if "--render" in args else ""
    for name in names:
        kit.build(name, out_dir, render_dir, make=BUILDINGS[name], views=(("front", -35.0),))


if __name__ == "__main__":
    main()
