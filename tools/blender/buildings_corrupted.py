"""Prédios da raça Corrupted modelados por script (redesenho de reports/design/race-corrupted.md): um GLB por prédio.

Uso:
    blender -b --factory-startup --python tools/blender/buildings_corrupted.py -- <id|all> [--out DIR] [--render DIR]

Floresta Fantasma: natureza envenenada a serviço da Corte. Tronco ferido (casca, cerne afogado), seiva negra
por dentro (rachaduras, cavidades, bexigas), liquens e raízes; o ferro é só estilhaço engolido (quase nada).
Um único acento saturado por prédio: a resina (olho, coração, diafragma, bolha). Regra da raça: todo prédio tem
um barril de tributo de madeira e uma estaca de concessão com a placa marcada. Sem tubo externo, roda, pistão,
fumaça contínua nem cogumelo. Pegada ~3,5 x 3,5 centrada na origem, a porta/frente virada para +x; o jogo
normaliza o tamanho, põe o prédio no plinto do time e desenha a bandeira.
"""

import math
import os
import sys

import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_paths  # noqa: E402
import map_castles as kit
from map_castles import box, cyl, mat

Z0 = 0.1  # topo do chão


def pal():
    return {
        "bark": mat("putrid_bark", 0x8B7D69),
        "bark_lt": mat("bark_light", 0xB3A387),
        "bark_dk": mat("bark_dark", 0x5E5445),
        "heart": mat("drowned_heartwood", 0x6A7069),
        "heart_dk": mat("heartwood_dark", 0x484D48),
        "heart_lt": mat("heartwood_light", 0x858C84),
        "lichen": mat("ash_lichen", 0x9AA08C),
        "lichen_lt": mat("ash_lichen_light", 0xBFC4AE),
        "sap": mat("black_sap", 0x2E251E),
        "sap_lt": mat("black_sap_wet", 0x4A3D33),
        "resin": mat("sick_resin", 0xE2CB3A, emit=2.0),
        "rust": mat("swallowed_rust", 0xA6694A),
        "mud": mat("mud", 0x5D5446),
    }


# ---------------------------------------------------------------------------------------------------------
# Peças da raça
# ---------------------------------------------------------------------------------------------------------


def limb(name, material, a, b, r0, r1, sides=7):
    """Tronco de cone de a até b (galho, raiz, tronco): o tijolo de tudo que é madeira."""
    a, b = Vector(a), Vector(b)
    d = b - a
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=r0, radius2=max(r1, 1e-3), depth=d.length)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, d.length / 2))
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=d.to_track_quat("Z", "Y").to_matrix())
    bmesh.ops.translate(bm, verts=bm.verts, vec=a)
    return kit._finish(bm, name, material)


def curve(name, material, pts, r0, r1, sides=7):
    """Cadeia de limbs por uma lista de pontos, o raio indo de r0 a r1."""
    n = len(pts) - 1
    for i in range(n):
        ra = r0 + (r1 - r0) * i / n
        rb = r0 + (r1 - r0) * (i + 1) / n
        limb(name, material, pts[i], pts[i + 1], ra, rb, sides)
        if i:  # junta redonda para o joelho não abrir fresta
            blob(name, material, pts[i], ra, ra, ra, sides=sides, rings=3)


def blob(name, material, c, rx, ry, rz, sides=8, rings=5):
    """Elipsoide inteiro (bexiga, bulbo, ovo, vagem)."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=sides, v_segments=rings, radius=1.0)
    for v in bm.verts:
        v.co.x *= rx
        v.co.y *= ry
        v.co.z *= rz
    bmesh.ops.translate(bm, verts=bm.verts, vec=c)
    return kit._finish(bm, name, material)


def pad(p, size=(3.5, 3.5)):
    """Chão do posto, do tamanho do conteúdo (o jogo normaliza pelo maior lado)."""
    box("pad", p["mud"], (0, 0, 0), (size[0], size[1], 0.1), bevel=0.03)


def puddle(p, x, y, rx=0.4, ry=0.3):
    """Mancha de seiva negra no chão: ancora o peso e conta a drenagem."""
    blob("sap_puddle", p["sap"], (x, y, Z0), rx, ry, 0.02, sides=9, rings=3)


def root(p, x, y, ang, length, h0, r=0.2, hook=0.0, tone="bark_dk"):
    """Raiz que sai do tronco em (x, y) rumo ao ângulo, mergulha na lama; hook > 0 acaba virada para cima."""
    c, s = math.cos(ang), math.sin(ang)
    pts = [
        (x, y, Z0 + h0),
        (x + c * length * 0.45, y + s * length * 0.45, Z0 + h0 * 0.55),
        (x + c * length, y + s * length, Z0 + 0.04 + hook),
    ]
    if hook > 0:
        pts.append((x + c * length * 1.12, y + s * length * 1.12, Z0 + hook * 2.2))
    curve("root", p[tone], pts, r, r * 0.3, sides=6)


def crust(p, x, y, z, r=0.14, tone="lichen"):
    """Crosta de líquen (ou resina seca) sobre a casca."""
    blob("crust", p[tone], (x, y, z), r * 1.3, r * 1.3, r * 0.5, sides=7, rings=3)


def cask(p, x, y, z=Z0, rot=0.0):
    """Barril de tributo de madeira com cintas de seiva (a regra da raça)."""
    cyl("cask_lo", p["bark_lt"], (x, y, z), 0.18, 0.2, sides=9, top_radius=0.23, bevel=0.0)
    cyl("cask_hi", p["bark_lt"], (x, y, z + 0.2), 0.23, 0.2, sides=9, top_radius=0.18, bevel=0.0)
    for dz, rr in ((0.04, 0.19), (0.2, 0.235), (0.36, 0.19)):
        cyl("cask_band", p["sap"], (x, y, z + dz), rr, 0.045, sides=9, bevel=0.0)
    cyl("cask_lid", p["bark_dk"], (x, y, z + 0.4), 0.16, 0.03, sides=9, bevel=0.0)
    puddle(p, x + 0.2, y, 0.3, 0.22)


def stake(p, x, y, h=1.0, lean=0.0):
    """Estaca de concessão: poste de madeira com a placa marcada (traço de seiva e entalhes)."""
    top = (x + lean, y, Z0 + h)
    limb("stake", p["bark_dk"], (x, y, Z0), top, 0.06, 0.045, sides=5)
    box("stake_plank", p["bark_lt"], (x + lean + 0.035, y, Z0 + h - 0.38), (0.04, 0.36, 0.3), bevel=0.0)
    box("stake_mark", p["sap"], (x + lean + 0.06, y, Z0 + h - 0.3), (0.02, 0.26, 0.05), bevel=0.0)
    box("stake_mark", p["sap"], (x + lean + 0.06, y - 0.06, Z0 + h - 0.22), (0.02, 0.05, 0.12), bevel=0.0)
    box("stake_notch", p["bark_dk"], (x + lean + 0.06, y + 0.1, Z0 + h - 0.42), (0.02, 0.1, 0.04), bevel=0.0)


def tribute(p, spots, stake_at, h=1.0):
    """Barris de tributo e a estaca de concessão do prédio."""
    for x, y in spots:
        cask(p, x, y)
    stake(p, stake_at[0], stake_at[1], h, lean=0.05)


def vein(p, x, y, z, h, facing=0.0, w=0.07):
    """Nervo de seiva negra numa fenda do tronco (por dentro, nunca cano): faixa fina sobre a casca."""
    c, s = math.cos(facing), math.sin(facing)
    box("vein", p["sap"], (x + c * 0.01, y + s * 0.01, z), (0.03, w, h), bevel=0.0, rot_z=facing)


def splinters(p, x, y, z, r, count=4, h=0.5, tone="bark"):
    """Coroa quebrada: lascas em leque no topo de um toco."""
    for i in range(count):
        a = i * math.tau / count + 0.4
        limb("splinter", p[tone], (x + math.cos(a) * r * 0.5, y + math.sin(a) * r * 0.5, z),
             (x + math.cos(a) * r * 1.0, y + math.sin(a) * r * 1.0, z + h * (0.6 + 0.4 * ((i * 7) % 3) / 2)), r * 0.28, 0.01, sides=4)


# ---------------------------------------------------------------------------------------------------------
# Tronco das Ents: Ancient of Battle -> Ancient of War -> Ancient of Annihilation
# ---------------------------------------------------------------------------------------------------------


def h04V_ancient_of_battle():
    """Toco largo e baixo: cavidade de nascimento no chão, uma copa quebrada de lado. A massa escura horizontal."""
    p = pal()
    pad(p)
    cyl("stump", p["heart"], (-0.2, 0, Z0), 1.35, 1.0, sides=10, top_radius=1.05, bevel=0.02)
    cyl("stump_cap", p["bark"], (-0.2, 0, Z0 + 1.0), 1.05, 0.1, sides=10, top_radius=0.9, bevel=0.0)
    splinters(p, -0.2, 0, Z0 + 1.1, 0.85, count=5, h=0.4, tone="bark_dk")
    # Cavidade de nascimento ao nível do chão, com o saco de resina dentro e o lintel de raiz.
    box("cavity", p["sap"], (0.98, 0, Z0), (0.3, 0.9, 0.62), bevel=0.0)
    blob("birth_sac", p["resin"], (1.08, 0, Z0 + 0.3), 0.11, 0.22, 0.14, sides=8, rings=4)
    for s in (-1, 1):
        limb("jamb", p["bark_dk"], (1.0, s * 0.62, Z0), (1.02, s * 0.48, Z0 + 0.74), 0.17, 0.12)
    box("lintel", p["heart_dk"], (1.0, 0, Z0 + 0.66), (0.26, 1.1, 0.16), bevel=0.02)
    # Uma copa quebrada para o lado: o galho-torre torto.
    curve("side_crown", p["bark"], [(-0.7, -0.8, Z0 + 0.8), (-0.85, -1.0, Z0 + 1.7), (-0.7, -1.2, Z0 + 2.4)], 0.34, 0.16)
    splinters(p, -0.7, -1.2, Z0 + 2.4, 0.3, count=3, h=0.5)
    limb("side_branch", p["bark_dk"], (-0.85, -1.0, Z0 + 1.6), (-0.3, -1.45, Z0 + 2.0), 0.1, 0.03)
    vein(p, 0.85, 0.7, Z0 + 0.5, 0.8, facing=math.radians(40))
    vein(p, 0.5, -1.05, Z0 + 0.6, 0.6, facing=math.radians(-60))
    for i, a in enumerate((60, 120, 200, 250, 300)):
        root(p, -0.2 + math.cos(math.radians(a)) * 1.15, math.sin(math.radians(a)) * 1.15, math.radians(a), 0.7, 0.55, r=0.2)
    crust(p, -0.1, 0.5, Z0 + 1.15, 0.2)
    crust(p, -0.7, 0.2, Z0 + 1.1, 0.17)
    tribute(p, [(1.2, 1.15), (1.4, 0.8)], (1.35, -1.2))


def h04W_ancient_of_war():
    """Tronco alto com ninho de ombro fora do eixo e o portão de raízes em A: contorno em pé, não escala."""
    p = pal()
    pad(p)
    cyl("stump", p["heart"], (-0.3, 0, Z0), 0.9, 0.8, sides=10, top_radius=0.6, bevel=0.02)
    curve("trunk", p["heart"], [(-0.3, 0, Z0 + 0.7), (-0.15, 0.15, Z0 + 1.8), (-0.4, 0.25, Z0 + 2.9), (-0.25, 0.2, Z0 + 3.9)], 0.55, 0.28, sides=9)
    for z in (1.2, 2.1, 2.9):
        crust(p, -0.1, -0.35, Z0 + z, 0.17, "lichen")
    splinters(p, -0.25, 0.2, Z0 + 3.9, 0.25, count=3, h=0.45, tone="bark_dk")
    # Ninho de ombro: cesto de galhos fora do eixo, com bolsa de seiva.
    nx, ny, nz = -0.2, -0.95, Z0 + 2.4
    limb("shoulder", p["bark"], (-0.2, -0.2, nz - 0.4), (nx, ny, nz), 0.28, 0.22)
    blob("nest_sap", p["sap"], (nx, ny, nz + 0.2), 0.45, 0.45, 0.22, sides=8, rings=4)
    for i in range(9):
        a = i * math.tau / 9
        limb("nest_twig", p["bark_dk"], (nx + math.cos(a) * 0.3, ny + math.sin(a) * 0.3, nz), (nx + math.cos(a) * 0.6, ny + math.sin(a) * 0.6, nz + 0.55 + 0.2 * (i % 2)), 0.09, 0.04, sides=5)
    # Portão de raízes em A sobre a cavidade da porta.
    for s in (-1, 1):
        curve("gate_root", p["bark_dk"], [(1.05, s * 1.0, Z0), (1.0, s * 0.75, Z0 + 1.2), (0.85, s * 0.25, Z0 + 2.15)], 0.24, 0.16)
    box("gate_keystone", p["heart_dk"], (0.8, 0, Z0 + 2.1), (0.34, 0.7, 0.24), bevel=0.02)
    box("door", p["sap"], (0.62, 0, Z0), (0.16, 0.9, 1.0), bevel=0.0)
    blob("door_sac", p["resin"], (0.72, 0, Z0 + 0.3), 0.08, 0.14, 0.12, sides=6, rings=3)
    vein(p, 0.38, 0.45, Z0 + 1.5, 1.2, facing=math.radians(20))
    for a in (70, 130, 200, 240, 300):
        root(p, -0.3 + math.cos(math.radians(a)) * 0.9, math.sin(math.radians(a)) * 0.9, math.radians(a), 0.7, 0.5, r=0.17)
    tribute(p, [(1.25, 1.2), (1.45, 0.85)], (1.4, -1.25), h=1.1)


def h09Y_ancient_of_annihilation():
    """Tronco aberto em coroa de galhadas largas em volta de uma ferida circular de resina; anel de estacas."""
    p = pal()
    pad(p)
    cyl("trunk", p["heart"], (-0.2, 0, Z0), 1.05, 1.6, sides=10, top_radius=0.8, bevel=0.02)
    # Galhadas: cinco hastes abertas para fora e para cima, cada uma com um dente.
    cx, cz = -0.2, Z0 + 1.5
    for i, (ang, rise, reach) in enumerate(((0, 2.3, 1.2), (72, 2.7, 1.5), (144, 2.2, 1.6), (216, 2.9, 1.3), (288, 2.5, 1.6))):
        a = math.radians(ang + 20)
        c, s = math.cos(a), math.sin(a)
        pts = [(cx + c * 0.4, s * 0.4, cz), (cx + c * reach * 0.55, s * reach * 0.55, cz + rise * 0.45), (cx + c * reach, s * reach, cz + rise)]
        curve("antler", p["bark"], pts, 0.3, 0.1)
        limb("tine", p["bark_dk"], pts[1], (cx + c * reach * 0.3, s * reach * 0.3, cz + rise * 0.95), 0.1, 0.03, sides=5)
    # A ferida aberta: aro de cerne, fundo de seiva e disco de resina.
    cyl("wound_rim", p["heart_dk"], (0.74, 0, Z0 + 0.9), 0.52, 0.12, sides=12, bevel=0.0, rot=("Y", math.radians(90)))
    cyl("wound_sap", p["sap"], (0.84, 0, Z0 + 0.9), 0.4, 0.05, sides=12, bevel=0.0, rot=("Y", math.radians(90)))
    cyl("wound_resin", p["resin"], (0.88, 0, Z0 + 0.9), 0.24, 0.05, sides=12, bevel=0.0, rot=("Y", math.radians(90)))
    for i in range(9):  # anel de estacas de raiz, aberto na frente
        a = math.radians(40 + i * 35)
        x, y = -0.2 + math.cos(a) * 1.6, math.sin(a) * 1.6
        limb("root_stake", p["bark_dk"], (x, y, Z0), (x * 0.96, y * 0.96 + 0.0, Z0 + 0.45 + 0.15 * (i % 3)), 0.09, 0.015, sides=5)
    for a in (35, 100, 160, 220, 270, 320):
        root(p, -0.2 + math.cos(math.radians(a)) * 1.0, math.sin(math.radians(a)) * 1.0, math.radians(a), 0.5, 0.45, r=0.2)
    vein(p, 0.45, -0.7, Z0 + 1.1, 1.0, facing=math.radians(-40))
    crust(p, -0.6, 0.6, Z0 + 1.55, 0.2)
    tribute(p, [(1.4, 1.0), (1.5, 0.65), (1.4, -1.0)], (1.55, -1.45), h=1.2)


# ---------------------------------------------------------------------------------------------------------
# Defesa: Corrupted Protector
# ---------------------------------------------------------------------------------------------------------


def n01J_protector():
    """Torre: tronco em espiral que pende para a frente e acaba numa vagem de pressão redonda; raízes em gancho."""
    p = pal()
    box("pad", p["mud"], (0, 0, 0), (2.7, 2.7, 0.1), bevel=0.03)
    axis = [(-0.2, -0.8, Z0), (-0.2, -0.75, Z0 + 0.9), (-0.2, -0.45, Z0 + 1.8), (-0.15, 0.0, Z0 + 2.5), (-0.1, 0.4, Z0 + 2.95)]
    curve("trunk", p["heart"], axis, 0.5, 0.32, sides=9)
    # Nervura espiral enrolada no tronco.
    spiral = []
    for i in range(13):
        t = i / 12
        k = t * (len(axis) - 1)
        j = min(int(k), len(axis) - 2)
        pt = Vector(axis[j]).lerp(Vector(axis[j + 1]), k - j)
        rad = 0.5 - 0.18 * t + 0.03
        ang = t * math.tau * 1.4
        spiral.append((pt.x + math.cos(ang) * rad, pt.y + math.sin(ang) * rad * 0.35, pt.z))
    curve("spiral_rib", p["bark_dk"], spiral, 0.1, 0.07, sides=5)
    # Vagem de pressão: esfera redonda, cinta de seiva e a boca de onde sai o glóbulo.
    px, pz = 0.0, Z0 + 3.45
    blob("pod", p["heart_lt"], (px, 0.55, pz), 0.68, 0.68, 0.64, sides=10, rings=6)
    cyl("pod_seam", p["sap"], (px, 0.5, pz), 0.71, 0.08, sides=10, bevel=0.0, rot=("X", math.radians(90)))
    cyl("pod_mouth", p["heart_dk"], (px + 0.55, 0.55, pz - 0.18), 0.24, 0.2, sides=8, bevel=0.0, rot=("Y", math.radians(90)), top_radius=0.18)
    cyl("pod_sap", p["sap"], (px + 0.72, 0.55, pz - 0.18), 0.17, 0.04, sides=8, bevel=0.0, rot=("Y", math.radians(90)))
    blob("globe", p["resin"], (px + 0.72, 0.55, pz - 0.18), 0.1, 0.12, 0.12, sides=6, rings=4)
    vein(p, px + 0.55, 0.2, pz + 0.2, 0.4, facing=math.radians(10))
    crust(p, px - 0.2, 0.3, pz + 0.55, 0.14)
    # Raízes em gancho, torcidas para um lado só.
    for a, ln, hk in ((20, 0.8, 0.35), (100, 0.6, 0.3), (180, 0.7, 0.25), (250, 0.75, 0.35), (320, 0.7, 0.2)):
        root(p, -0.2 + math.cos(math.radians(a)) * 0.35, -0.8 + math.sin(math.radians(a)) * 0.35, math.radians(a), ln, 0.5, r=0.2, hook=hk)
    tribute(p, [(0.7, -0.6)], (0.85, -1.05), h=0.9)


# ---------------------------------------------------------------------------------------------------------
# Estátua, Olho, Canil, Raiz Enterrada
# ---------------------------------------------------------------------------------------------------------


def h04U_demonic_statue():
    """Sentinela Petrificada: figura ajoelhada sem rosto, madeira doente e pedra, com a espinha-toco bifurcada atrás."""
    p = pal()
    pad(p)
    box("dais", p["lichen"], (0, 0, Z0), (3.2, 2.6, 0.22), bevel=0.04, taper=0.94, taper_y=0.94)
    z = Z0 + 0.22
    for s in (-1, 1):
        box("shin", p["bark"], (-0.1, s * 0.4, z), (1.2, 0.4, 0.28), bevel=0.04)
        limb("thigh", p["heart"], (0.5, s * 0.4, z + 0.25), (-0.2, s * 0.36, z + 1.05), 0.26, 0.3)
        limb("arm", p["bark"], (-0.1, s * 0.78, z + 1.95), (0.45, s * 0.62, z + 0.95), 0.17, 0.14)
        blob("fist", p["bark_dk"], (0.5, s * 0.6, z + 0.85), 0.16, 0.16, 0.14)
    box("torso", p["heart"], (-0.3, 0, z + 0.9), (0.85, 1.05, 1.2), bevel=0.05, taper=0.85, taper_y=0.8)
    blob("shoulders", p["heart_lt"], (-0.3, 0, z + 2.0), 0.4, 0.8, 0.22, sides=8, rings=4)
    blob("head", p["heart_lt"], (-0.15, 0, z + 2.5), 0.3, 0.28, 0.34)
    box("head_split", p["sap"], (0.1, 0, z + 2.3), (0.03, 0.04, 0.5), bevel=0.0)
    # Cavidade do peito: seiva, o reliquário de resina e o fio de vapor que pinga.
    box("chest_cavity", p["sap"], (0.12, 0, z + 1.2), (0.12, 0.5, 0.65), bevel=0.0)
    blob("reliquary", p["resin"], (0.22, 0, z + 1.5), 0.08, 0.15, 0.17, sides=8, rings=4)
    box("chest_drip", p["sap"], (0.15, 0, z + 0.7), (0.05, 0.1, 0.55), bevel=0.0)
    puddle(p, 0.7, 0, 0.25, 0.2)
    # Espinha-toco bifurcada nas costas.
    curve("snag_a", p["bark_dk"], [(-0.7, -0.05, z + 1.4), (-0.95, -0.2, z + 2.6), (-0.9, -0.4, z + 3.6)], 0.26, 0.07)
    curve("snag_b", p["bark"], [(-0.75, 0.05, z + 1.9), (-0.85, 0.35, z + 2.8), (-0.65, 0.5, z + 3.2)], 0.2, 0.06)
    crust(p, -0.5, 0.45, z + 1.7, 0.14)
    crust(p, 0.3, -0.55, z + 0.6, 0.12)
    tribute(p, [(1.0, 0.95), (1.2, 0.65)], (1.3, -1.0), h=1.1)


def h04T_eye_of_corruption():
    """Válvula da Veia: toco baixo sustenta um diafragma de resina dentro de um aro de galhos, calibre de pressão."""
    p = pal()
    pad(p)
    cyl("stump", p["heart"], (-0.5, 0, Z0), 1.1, 0.9, sides=10, top_radius=0.85, bevel=0.02)
    cx, cz, rr = -0.05, Z0 + 2.4, 1.0
    n = 12
    ring_pts = [(cx, math.cos(i * math.tau / n) * rr, cz + math.sin(i * math.tau / n) * rr) for i in range(n + 1)]
    curve("rib_ring", p["bark"], ring_pts, 0.15, 0.15, sides=6)
    cyl("diaphragm_back", p["sap"], (cx - 0.05, 0, cz), 0.85, 0.1, sides=14, bevel=0.0, rot=("Y", math.radians(90)))
    cyl("diaphragm_sap", p["sap_lt"], (cx + 0.02, 0, cz), 0.72, 0.06, sides=14, bevel=0.0, rot=("Y", math.radians(90)))
    cyl("diaphragm", p["resin"], (cx + 0.05, 0, cz), 0.4, 0.07, sides=14, bevel=0.0, rot=("Y", math.radians(90)))
    cyl("diaphragm_core", p["sap"], (cx + 0.11, 0, cz), 0.1, 0.04, sides=8, bevel=0.0, rot=("Y", math.radians(90)))
    # Costelas que firmam o aro no toco; dentes de galho saindo para fora.
    for s in (-1, 1):
        limb("cradle", p["bark_dk"], (-0.5, s * 0.6, Z0 + 0.8), (cx, s * 0.95, cz - 0.4), 0.2, 0.13)
    limb("cradle_back", p["bark_dk"], (-0.7, 0, Z0 + 0.8), (cx - 0.1, 0, cz - 0.95), 0.22, 0.14)
    for i in range(6):
        a = math.radians(30 + i * 60)
        limb("rib_tooth", p["bark_dk"], (cx, math.cos(a) * rr, cz + math.sin(a) * rr), (cx, math.cos(a) * (rr + 0.4), cz + math.sin(a) * (rr + 0.4)), 0.08, 0.02, sides=5)
    vein(p, 0.25, 0.3, Z0 + 0.4, 0.9, facing=math.radians(20))
    crust(p, -0.9, 0.7, Z0 + 0.95, 0.17)
    for a in (60, 120, 200, 260, 310):
        root(p, -0.5 + math.cos(math.radians(a)) * 1.0, math.sin(math.radians(a)) * 1.0, math.radians(a), 0.45, 0.5, r=0.18)
    tribute(p, [(1.2, 1.1), (1.35, 0.75)], (1.3, -1.2), h=1.0)


def h04S_felhound_shrine():
    """Canil da Praga: tronco caído rachado forma a toca baixa, um galho morto vertical atrás, cintas de raiz."""
    p = pal()
    pad(p)
    # Tronco rachado deitado ao longo de y: costas altas atrás, tora de cima fechando a toca e a frente aberta
    # no meio (a porta), de modo que a boca escura vira para +x.
    cyl("log_back", p["bark"], (-0.8, -1.55, Z0 + 0.62), 0.62, 3.1, sides=9, bevel=0.0, rot=("X", math.radians(-90)))
    cyl("log_top", p["heart"], (0.0, -1.35, Z0 + 1.0), 0.4, 2.7, sides=9, bevel=0.0, rot=("X", math.radians(-90)))
    for y0, ln in ((-1.6, 1.05), (0.6, 1.05)):
        cyl("log_front", p["bark"], (0.85, y0, Z0 + 0.45), 0.45, ln, sides=9, bevel=0.0, rot=("X", math.radians(-90)))
        splinters(p, 0.85, y0 + (ln if y0 < 0 else 0.0), Z0 + 0.45, 0.4, count=4, h=0.3)
    box("den", p["sap"], (0.1, 0.03, Z0), (2.0, 1.15, 0.7), bevel=0.0)
    box("den_lip", p["heart_dk"], (1.35, 0, Z0), (0.16, 1.2, 0.08), bevel=0.0)
    box("split", p["bark_dk"], (-0.8, 1.0, Z0 + 1.2), (0.05, 0.9, 0.1), bevel=0.0)
    # Galho morto vertical, torto, atrás da toca, com cotos.
    curve("snag", p["bark_dk"], [(-0.9, 1.5, Z0), (-1.0, 1.55, Z0 + 1.5), (-0.8, 1.45, Z0 + 2.7), (-0.95, 1.4, Z0 + 3.8)], 0.26, 0.05)
    limb("snag_stub", p["bark_dk"], (-1.0, 1.55, Z0 + 1.9), (-0.5, 1.3, Z0 + 2.4), 0.08, 0.02, sides=5)
    limb("snag_stub", p["bark_dk"], (-0.8, 1.45, Z0 + 3.0), (-1.3, 1.1, Z0 + 3.4), 0.07, 0.02, sides=5)
    for z in (0.35, 0.9):
        cyl("scent_collar", p["lichen"], (-0.9, 1.5, Z0 + z), 0.34, 0.12, sides=8, top_radius=0.3, bevel=0.0)
    crust(p, 0.3, 0.7, Z0 + 1.35, 0.1, "resin")
    crust(p, -0.8, -0.5, Z0 + 1.25, 0.2)
    # Pegadas fundas de sulco de lama para a porta, e a estaca.
    box("drag_groove", p["sap_lt"], (1.4, 0, Z0), (0.6, 0.5, 0.012), bevel=0.0)
    tribute(p, [(1.45, 1.3)], (1.5, -1.5), h=1.0)


def h04R_forgotten_one():
    """Raiz Enterrada: bulbo semi-submerso, um toco rachado em pé, seis módulos de raiz saindo de fendas no solo."""
    p = pal()
    pad(p)
    kit.dome("mound", p["mud"], (-0.2, 0, Z0), 1.6, squash=0.12, sides=12)
    kit.dome("bulb", p["heart"], (-0.3, 0, Z0), 1.3, squash=0.75, sides=12)
    # Olho enterrado: cavidade na frente do bulbo com o brilho de resina.
    blob("eye_socket", p["sap"], (0.78, 0, Z0 + 0.5), 0.18, 0.42, 0.34, sides=8, rings=4)
    blob("eye", p["resin"], (0.88, 0, Z0 + 0.5), 0.07, 0.16, 0.2, sides=8, rings=4)
    # Toco em pé, rachado ao meio.
    curve("stump", p["bark"], [(-0.7, -0.2, Z0 + 0.6), (-0.75, -0.15, Z0 + 1.6), (-0.7, -0.1, Z0 + 2.3)], 0.5, 0.36, sides=8)
    limb("crack_l", p["bark_dk"], (-0.75, -0.05, Z0 + 2.25), (-1.0, 0.35, Z0 + 3.5), 0.26, 0.04, sides=5)
    limb("crack_r", p["bark"], (-0.65, -0.2, Z0 + 2.25), (-0.3, -0.55, Z0 + 3.1), 0.24, 0.04, sides=5)
    box("crack_gap", p["sap"], (-0.72, -0.12, Z0 + 2.2), (0.12, 0.12, 0.3), bevel=0.0)
    box("crack_sap", p["sap"], (-0.47, -0.17, Z0 + 1.6), (0.03, 0.08, 1.4), bevel=0.0)
    # Seis módulos de raiz: arcos meio enterrados sobre fendas de seiva radiais.
    for i in range(6):
        a = math.radians(i * 60 + 15)
        c, s = math.cos(a), math.sin(a)
        r0, r1 = 0.95, 1.7
        box("soil_crack", p["sap"], (c * 1.35 - 0.2, s * 1.35, Z0 + 0.005), (0.75, 0.07, 0.012), bevel=0.0, rot_z=a)
        curve("root_module", p["bark_dk"], [(c * r0 - 0.2, s * r0, Z0 - 0.02), (c * (r0 + r1) / 2 - 0.2, s * (r0 + r1) / 2, Z0 + 0.75), (c * r1 - 0.2, s * r1, Z0 - 0.02)], 0.24, 0.17, sides=6)
    crust(p, 0.1, 0.8, Z0 + 0.95, 0.2)
    crust(p, -0.9, 0.8, Z0 + 0.75, 0.15)
    tribute(p, [(1.45, 0.35)], (1.5, -0.55), h=0.9)


# ---------------------------------------------------------------------------------------------------------
# Siege: Hell's Gate -> Hell's Portal
# ---------------------------------------------------------------------------------------------------------


def pressure_pod(p, base, tip, r0, r1):
    """Vagem de pressão inclinada: gomo grosso com bolsa na base e nó escuro na boca."""
    limb("pod", p["bark"], base, tip, r0, r1, sides=8)
    blob("pod_bulb", p["bark"], base, r0 * 1.1, r0 * 1.1, r0 * 1.05, sides=8, rings=4)
    d = (Vector(tip) - Vector(base)).normalized()
    mid = Vector(base).lerp(Vector(tip), 0.55)
    blob("pod_knot", p["heart_dk"], mid, r0 * 0.85, r0 * 0.85, r0 * 0.85, sides=8, rings=4)
    blob("pod_mouth", p["sap"], Vector(tip) + d * 0.04, r1 * 1.1, r1 * 1.1, r1 * 0.8, sides=7, rings=3)


def h04Q_hells_gate():
    """Leito de Pressão Raso: um arco de raiz curvo e baixo cobre duas vagens de lançamento inchadas."""
    p = pal()
    pad(p)
    curve("arch", p["heart"], [(-0.8, -1.5, Z0), (-0.9, -1.2, Z0 + 1.2), (-0.7, -0.4, Z0 + 1.9), (-0.7, 0.4, Z0 + 2.1), (-0.8, 1.1, Z0 + 1.5), (-0.9, 1.45, Z0)], 0.32, 0.26, sides=8)
    limb("arch_spur", p["bark_dk"], (-0.7, 0.4, Z0 + 2.1), (-0.3, 0.9, Z0 + 1.5), 0.13, 0.04, sides=5)
    # Leito de seiva e as duas vagens inclinadas rumo a +x; a maior leva o acento de resina.
    blob("bed", p["sap_lt"], (0.15, 0, Z0), 1.4, 1.5, 0.04, sides=10, rings=3)
    pressure_pod(p, (-0.3, -0.7, Z0 + 0.35), (0.85, -0.7, Z0 + 1.35), 0.4, 0.25)
    pressure_pod(p, (-0.3, 0.7, Z0 + 0.3), (0.65, 0.7, Z0 + 1.0), 0.33, 0.2)
    blob("seed", p["resin"], (0.97, -0.7, Z0 + 1.47), 0.13, 0.13, 0.13, sides=6, rings=4)
    blob("seed_dk", p["lichen"], (0.76, 0.7, Z0 + 1.1), 0.1, 0.1, 0.1, sides=6, rings=4)
    crust(p, -0.1, -1.0, Z0 + 0.9, 0.14)
    crust(p, -0.2, 1.05, Z0 + 0.75, 0.12)
    for a in (-30, 30, 200, 150):
        root(p, 0.0 + math.cos(math.radians(a)) * 1.4, math.sin(math.radians(a)) * 1.2, math.radians(a), 0.35, 0.3, r=0.13)
    tribute(p, [(1.3, 1.1)], (1.45, -1.2), h=0.9)


def h04P_hells_portal():
    """Leito de Pressão Profundo: dois pilares de raiz altos e fendidos cercam uma bexiga funda em forma de coração."""
    p = pal()
    pad(p)
    for s in (-1, 1):
        curve("pylon", p["heart"], [(-0.4, s * 1.2, Z0), (-0.45, s * 1.15, Z0 + 1.6), (-0.4, s * 1.1, Z0 + 2.9)], 0.5, 0.3, sides=8)
        limb("fork_in", p["bark"], (-0.4, s * 1.1, Z0 + 2.9), (-0.35, s * 0.75, Z0 + 4.0), 0.26, 0.04, sides=5)
        limb("fork_out", p["bark_dk"], (-0.4, s * 1.1, Z0 + 2.9), (-0.5, s * 1.45, Z0 + 3.75), 0.24, 0.04, sides=5)
        box("pylon_vein", p["sap"], (-0.1, s * 1.1, Z0 + 0.8), (0.03, 0.07, 1.5), bevel=0.0)
        crust(p, -0.1, s * 1.2, Z0 + 1.9, 0.15, "lichen")
        for a in (35, 100, 150):
            root(p, -0.4 + math.cos(math.radians(a * s + 90 * (s - 1) / -1)) * 0.5, s * 1.15, math.radians(a * s), 0.5, 0.4, r=0.15)
    # Bexiga em coração: dois lóbulos sobre uma ponta funda, presa aos pilares por raízes-tirante.
    blob("lobe", p["sap_lt"], (0.0, -0.42, Z0 + 1.75), 0.55, 0.52, 0.55, sides=9, rings=6)
    blob("lobe", p["sap_lt"], (0.0, 0.42, Z0 + 1.75), 0.55, 0.52, 0.55, sides=9, rings=6)
    cyl("heart_tip", p["sap_lt"], (0.0, 0, Z0 + 0.3), 0.14, 1.1, sides=8, top_radius=0.62, bevel=0.0)
    blob("heart_core", p["resin"], (0.4, 0, Z0 + 1.75), 0.12, 0.2, 0.22, sides=8, rings=4)
    for s in (-1, 1):
        limb("tie", p["bark_dk"], (-0.4, s * 1.1, Z0 + 1.9), (0.0, s * 0.6, Z0 + 2.0), 0.1, 0.08, sides=5)
    blob("bed", p["sap"], (0.1, 0, Z0), 1.1, 0.9, 0.03, sides=10, rings=3)
    # Estaca-medidor alta com entalhes: quanto sangue virou tributo.
    limb("meter", p["bark_dk"], (1.45, 0.0, Z0), (1.45, 0.0, Z0 + 2.2), 0.08, 0.06, sides=5)
    for i in range(7):
        box("meter_notch", p["bark_lt"], (1.5, 0.0, Z0 + 0.5 + i * 0.22), (0.04, 0.22 if i % 2 else 0.14, 0.05), bevel=0.0)
    box("meter_mark", p["sap"], (1.52, 0.0, Z0 + 1.9), (0.03, 0.2, 0.16), bevel=0.0)
    tribute(p, [(1.2, 1.2), (1.4, 0.85)], (1.45, -1.25), h=1.0)


# ---------------------------------------------------------------------------------------------------------
# Drakes: Nether Ancient -> Shadow Ancient
# ---------------------------------------------------------------------------------------------------------


def leaf_slab(p, pos, size, tilt, rot_z=0.0, tone="lichen_lt"):
    """Folha rasgada mineralizada: lasca fina e chata, com um furo de seiva."""
    x, y, z = pos
    sl = box("torn_leaf", p[tone], (x, y, z), size, bevel=0.0, rot_z=rot_z)
    for v in sl.data.vertices:
        v.co.z += tilt * v.co.x
    return sl


def h04O_nether_ancient():
    """Ninho de Fuligem: ninho em anel caído sob um poleiro alto e torto; bolsa de incubação em resina."""
    p = pal()
    pad(p)
    n = 12
    for i in range(n):
        a = i * math.tau / n
        c, s = math.cos(a), math.sin(a)
        limb("nest_log", p["bark"] if i % 2 else p["bark_dk"], (c * 1.35 + 0.2 - s * 0.45, s * 1.35 + c * 0.45, Z0 + 0.12), (c * 1.35 + 0.2 + s * 0.45, s * 1.35 - c * 0.45, Z0 + 0.3 + 0.12 * (i % 3)), 0.17, 0.15, sides=6)
    blob("nest_floor", p["sap_lt"], (0.2, 0, Z0 + 0.04), 1.2, 1.2, 0.08, sides=12, rings=3)
    blob("sac", p["resin"], (0.4, 0.1, Z0 + 0.22), 0.2, 0.2, 0.2, sides=8, rings=5)
    blob("egg", p["lichen"], (-0.2, 0.5, Z0 + 0.25), 0.22, 0.2, 0.26, sides=7, rings=4)
    blob("egg", p["lichen_lt"], (0.0, -0.55, Z0 + 0.22), 0.2, 0.2, 0.24, sides=7, rings=4)
    # Poleiro alto e torto com um galho de pouso sobre o ninho.
    curve("perch", p["heart"], [(-1.0, -0.7, Z0), (-1.2, -0.6, Z0 + 1.4), (-0.8, -0.3, Z0 + 2.7), (-0.9, -0.2, Z0 + 3.9)], 0.42, 0.1, sides=8)
    curve("perch_arm", p["bark_dk"], [(-0.9, -0.3, Z0 + 2.9), (-0.2, -0.3, Z0 + 3.1), (0.6, -0.1, Z0 + 2.85)], 0.15, 0.05, sides=6)
    limb("perch_fork", p["bark_dk"], (0.1, -0.3, Z0 + 3.1), (0.4, -0.7, Z0 + 3.5), 0.08, 0.03, sides=5)
    # Folhas mineralizadas rasgadas penduradas no poleiro e caídas no ninho.
    leaf_slab(p, (-0.7, -0.4, Z0 + 1.9), (0.9, 0.05, 0.4), -0.3, rot_z=0.3)
    leaf_slab(p, (-1.5, -0.3, Z0 + 0.12), (0.7, 0.5, 0.04), 0.1, rot_z=0.5, tone="lichen")
    leaf_slab(p, (0.9, 0.9, Z0 + 0.3), (0.6, 0.4, 0.04), 0.15, rot_z=-0.4, tone="lichen")
    puddle(p, -0.9, -0.2, 0.5, 0.4)
    crust(p, -1.1, -0.5, Z0 + 1.9, 0.16)
    tribute(p, [(1.45, 1.1)], (1.55, -1.1), h=1.0)


def crescent(p, ang, trunk_x, z, reach, droop, tone="bark"):
    """Poleiro em crescente caído: arco que passa pelo tronco e tomba nas duas pontas."""
    c, s = math.cos(ang), math.sin(ang)
    pts = []
    for i in range(-3, 4):
        t = i / 3
        pts.append((trunk_x + c * reach * t, s * reach * t, z - droop * t * t + 0.25 * (1 - abs(t))))
    curve("crescent", p[tone], pts, 0.24, 0.2, sides=6)
    for e in (-1, 1):
        a, b = Vector(pts[3 + e * 3]), Vector(pts[3 + e * 3]) + Vector((c * e * 0.15, s * e * 0.15, -0.35))
        limb("crescent_tip", p["bark_dk"], a, b, 0.2, 0.04, sides=5)


def h04M_shadow_ancient():
    """Ninho Guardião: tronco central alto e dois poleiros em crescente caído que se cruzam; cisterna na base."""
    p = pal()
    pad(p)
    curve("trunk", p["heart"], [(-0.2, 0, Z0), (-0.25, 0.05, Z0 + 1.6), (-0.15, 0, Z0 + 3.0), (-0.2, -0.1, Z0 + 3.9)], 0.65, 0.2, sides=9)
    crescent(p, math.radians(25), -0.2, Z0 + 2.9, 1.65, 0.9)
    crescent(p, math.radians(-40), -0.2, Z0 + 2.3, 1.6, 0.8, tone="bark_dk")
    box("crown_knot", p["heart_dk"], (-0.3, 0, Z0 + 2.15), (0.7, 0.7, 0.2), bevel=0.04)
    # Cisterna presa ao tronco: reserva de seiva com o nível de resina na janela.
    cyl("cistern", p["heart_dk"], (0.5, 0.0, Z0), 0.5, 1.1, sides=10, top_radius=0.42, bevel=0.0)
    cyl("cistern_band", p["sap"], (0.5, 0.0, Z0 + 0.55), 0.48, 0.1, sides=10, bevel=0.0)
    box("cistern_window", p["sap"], (0.9, 0, Z0 + 0.25), (0.06, 0.2, 0.6), bevel=0.0)
    box("cistern_level", p["resin"], (0.94, 0, Z0 + 0.3), (0.04, 0.12, 0.3), bevel=0.0)
    limb("cistern_root", p["bark_dk"], (0.1, 0.0, Z0 + 1.0), (-0.2, 0, Z0 + 1.5), 0.12, 0.2, sides=6)
    for a in (40, 100, 160, 220, 270, 330):
        root(p, -0.2 + math.cos(math.radians(a)) * 0.9, math.sin(math.radians(a)) * 0.9, math.radians(a), 0.7, 0.55, r=0.2)
    leaf_slab(p, (-0.6, 1.2, Z0 + 0.12), (0.6, 0.4, 0.04), 0.1, rot_z=0.5, tone="lichen")
    puddle(p, 0.2, 0.0, 0.6, 0.5)
    crust(p, -0.6, -0.3, Z0 + 1.2, 0.17)
    tribute(p, [(1.3, 1.0), (1.45, 0.65)], (1.45, -1.2), h=1.1)


# ---------------------------------------------------------------------------------------------------------
# Cisternas e poço: Void Portal -> Portal of the Abyss, Well of Pain
# ---------------------------------------------------------------------------------------------------------


def h04L_void_portal():
    """Cisterna de Fermentação: bacia redonda e baixa sob um arco de raiz; bolha de pressão em resina."""
    p = pal()
    pad(p)
    cyl("basin", p["bark"], (0, 0, Z0), 1.45, 0.6, sides=12, top_radius=1.3, bevel=0.0)
    cyl("basin_rim", p["bark_dk"], (0, 0, Z0 + 0.55), 1.4, 0.1, sides=12, top_radius=1.4, bevel=0.0)
    cyl("basin_sap", p["sap"], (0, 0, Z0 + 0.62), 1.2, 0.05, sides=12, bevel=0.0)
    blob("bubble", p["resin"], (0.35, 0.2, Z0 + 0.82), 0.18, 0.18, 0.2, sides=8, rings=5)
    blob("sap_mound", p["sap_lt"], (-0.4, -0.3, Z0 + 0.68), 0.5, 0.45, 0.14, sides=8, rings=3)
    # Arco de raiz único sobre a bacia e os brotos de Sapling pendurados nele.
    curve("arch", p["heart"], [(-0.3, -1.3, Z0), (-0.4, -1.05, Z0 + 1.4), (-0.35, -0.3, Z0 + 2.4), (-0.35, 0.5, Z0 + 2.5), (-0.45, 1.1, Z0 + 1.5), (-0.3, 1.3, Z0)], 0.28, 0.24, sides=8)
    for y in (-0.45, 0.35):
        limb("bud_stalk", p["bark_dk"], (-0.35, y, Z0 + 2.4), (-0.15, y, Z0 + 1.7), 0.06, 0.04, sides=5)
        blob("bud", p["sap_lt"], (-0.15, y, Z0 + 1.55), 0.18, 0.18, 0.2, sides=7, rings=4)
    for i in range(7):
        a = i * math.tau / 7 + 0.2
        crust(p, math.cos(a) * 1.4, math.sin(a) * 1.4, Z0 + 0.62, 0.13, "lichen")
    tribute(p, [(1.3, 1.35), (1.45, 1.0)], (1.5, -1.3), h=1.0)


def husk(p, x, y, h, r, lean, tone="heart"):
    """Casca alta fendida: um lobo largo que abre em duas pontas, de costas para a bacia."""
    curve("husk", p[tone], [(x, y, Z0), (x + lean * 0.3, y, Z0 + h * 0.5), (x + lean, y, Z0 + h * 0.85)], r, r * 0.7, sides=8)
    top = (x + lean, y, Z0 + h * 0.85)
    limb("husk_prong", p["bark"], top, (x + lean * 1.2, y - r * 0.9, Z0 + h), r * 0.6, 0.03, sides=5)
    limb("husk_prong", p["bark_dk"], top, (x + lean * 0.8, y + r * 0.9, Z0 + h * 0.93), r * 0.5, 0.03, sides=5)
    box("husk_slit", p["sap"], (x + r * 0.9, y, Z0 + h * 0.2), (0.03, 0.12, h * 0.6), bevel=0.0)


def h04N_portal_of_the_abyss():
    """Cisterna Profunda: casca dupla alta e fendida, desigual, em volta de uma bacia escura; duas bexigas."""
    p = pal()
    pad(p)
    cyl("basin", p["bark"], (0.4, 0, Z0), 1.0, 0.45, sides=12, top_radius=0.9, bevel=0.0)
    cyl("basin_sap", p["sap"], (0.4, 0, Z0 + 0.42), 0.75, 0.05, sides=12, bevel=0.0)
    husk(p, -0.6, -0.9, 4.0, 0.55, -0.1)
    husk(p, -0.6, 0.95, 3.1, 0.5, 0.15, tone="heart_dk")
    # Duas bexigas de fermentação, uma em cada casca, presas por raiz.
    blob("bladder", p["sap_lt"], (0.0, -0.95, Z0 + 1.2), 0.5, 0.45, 0.55, sides=9, rings=5)
    blob("bladder", p["sap_lt"], (0.05, 0.9, Z0 + 0.95), 0.42, 0.4, 0.46, sides=9, rings=5)
    blob("bubble", p["resin"], (0.5, 0.0, Z0 + 0.62), 0.2, 0.2, 0.2, sides=8, rings=5)
    cyl("lift_band", p["bark_dk"], (0.0, -0.95, Z0 + 1.15), 0.52, 0.1, sides=9, bevel=0.0)
    limb("bridge", p["bark_dk"], (-0.5, -0.8, Z0 + 2.6), (-0.4, 0.8, Z0 + 2.4), 0.12, 0.1, sides=6)
    crust(p, -0.2, -1.3, Z0 + 1.9, 0.17)
    crust(p, -0.2, 1.35, Z0 + 1.2, 0.13)
    for a in (200, 260, 100, 150):
        root(p, -0.6 + math.cos(math.radians(a)) * 0.7, math.sin(math.radians(a)) * 1.05, math.radians(a), 0.55, 0.5, r=0.16)
    tribute(p, [(1.35, 1.2), (1.5, 0.85)], (1.45, -1.2), h=1.1)


def h04K_well_of_pain():
    """Poço da Ferida: bacia baixa de seiva, um espigão de semente vertical com a ponta de resina e o cavalete de vagens."""
    p = pal()
    pad(p)
    cyl("basin", p["bark"], (-0.3, 0, Z0), 1.2, 0.4, sides=10, top_radius=1.05, bevel=0.0)
    cyl("basin_rim", p["bark_dk"], (-0.3, 0, Z0 + 0.38), 1.12, 0.1, sides=10, top_radius=1.1, bevel=0.0)
    cyl("basin_sap", p["sap"], (-0.3, 0, Z0 + 0.46), 0.95, 0.05, sides=10, bevel=0.0)
    # Espigão de semente: fuste fino, ponta de resina.
    curve("spike", p["heart"], [(-0.3, 0, Z0 + 0.4), (-0.28, 0.02, Z0 + 1.6), (-0.3, 0, Z0 + 2.6)], 0.26, 0.12, sides=7)
    limb("spike_tip", p["resin"], (-0.3, 0, Z0 + 2.6), (-0.3, 0, Z0 + 3.5), 0.12, 0.01, sides=6)
    vein(p, -0.03, 0.0, Z0 + 0.9, 1.4, facing=0.0, w=0.07)
    # Cavalete de cargas: duas estacas e uma trave com vagens penduradas.
    for s in (-1, 1):
        limb("rack_post", p["bark_dk"], (1.05, s * 1.3, Z0), (1.05, s * 1.3, Z0 + 1.45), 0.08, 0.07, sides=5)
    box("rack_beam", p["bark"], (1.05, 0, Z0 + 1.38), (0.14, 2.8, 0.13), bevel=0.0)
    for i in range(5):
        y = -1.0 + i * 0.5
        limb("pod_stalk", p["bark_dk"], (1.05, y, Z0 + 1.38), (1.05, y, Z0 + 1.15), 0.04, 0.04, sides=4)
        blob("charge_pod", p["heart_dk"] if i % 2 else p["heart"], (1.05, y, Z0 + 0.9), 0.17, 0.17, 0.26, sides=7, rings=4)
        blob("pod_cap", p["lichen"], (1.05, y, Z0 + 1.1), 0.12, 0.12, 0.07, sides=6, rings=3)
    crust(p, -1.1, 0.4, Z0 + 0.5, 0.14)
    crust(p, -0.7, -0.9, Z0 + 0.5, 0.12)
    for a in (120, 180, 240, 300):
        root(p, -0.3 + math.cos(math.radians(a)) * 1.1, math.sin(math.radians(a)) * 1.1, math.radians(a), 0.5, 0.3, r=0.15)
    tribute(p, [(1.45, 0.95)], (1.5, -1.3), h=0.95)


BUILDINGS = {
    "h04V": h04V_ancient_of_battle,
    "h04W": h04W_ancient_of_war,
    "h09Y": h09Y_ancient_of_annihilation,
    "n01J": n01J_protector,
    "h04U": h04U_demonic_statue,
    "h04T": h04T_eye_of_corruption,
    "h04S": h04S_felhound_shrine,
    "h04R": h04R_forgotten_one,
    "h04Q": h04Q_hells_gate,
    "h04P": h04P_hells_portal,
    "h04O": h04O_nether_ancient,
    "h04N": h04N_portal_of_the_abyss,
    "h04M": h04M_shadow_ancient,
    "h04L": h04L_void_portal,
    "h04K": h04K_well_of_pain,
}


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["all"]
    names = list(BUILDINGS) if args[0] == "all" else [args[0]]
    out_dir = game_paths.out_arg(args, "--out", "buildings", "corrupted")
    render_dir = args[args.index("--render") + 1] if "--render" in args else ""
    for name in names:
        kit.build(name, out_dir, render_dir, make=BUILDINGS[name], views=(("front", -35.0), ("game", -90.0)))


if __name__ == "__main__":
    main()
