"""Castelos dos mapas (docs/maps.md) modelados por script: um GLB por castelo em assets/castles/.

Uso:
    blender -b --factory-startup --python tools/blender/map_castles.py -- <nome|all> [--out DIR] [--render DIR]

Referencial do jogo: +x aponta para a lane, z é a altura (o exportador glTF troca para Y para cima).
Pegada ~5,2 x 5,2 unidades da sim e altura da massa <= ~0,8 da largura: a fortaleza impõe pela largura e
pela muralha grossa, não pela altura. Cor chapada por peça (um material por cor, sem textura).
"""

import itertools
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_paths  # noqa: E402

# ---------------------------------------------------------------------------------------------------------
# Kit de modelagem
# ---------------------------------------------------------------------------------------------------------

_mats = {}


def mat(name, hex_rgb, emit=0.0):
    if name in _mats:
        return _mats[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    rgb = [((hex_rgb >> s) & 0xFF) / 255.0 for s in (16, 8, 0)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*lin, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    bsdf.inputs["Metallic"].default_value = 0.0
    if emit > 0.0:
        bsdf.inputs["Emission Color"].default_value = (*lin, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emit
    _mats[name] = m
    return m


def _finish(bm, name, material, bevel=0.0):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(material)
    if bevel > 0.0:
        mod = ob.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 1
        mod.limit_method = "ANGLE"
        mod.angle_limit = math.radians(40)
    return ob


def box(name, material, center, size, bevel=0.03, taper=1.0, taper_y=None, rot_z=0.0):
    """Caixa com a base em center.z; taper < 1 afina o topo (muralha em talude)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    ty = taper if taper_y is None else taper_y
    for v in bm.verts:
        top = v.co.z > 0
        v.co.x *= size[0] * (taper if top else 1.0)
        v.co.y *= size[1] * (ty if top else 1.0)
        v.co.z = (v.co.z + 0.5) * size[2]
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(rot_z, 3, "Z"))
    bmesh.ops.translate(bm, verts=bm.verts, vec=center)
    return _finish(bm, name, material, bevel)


def cyl(name, material, center, radius, height, sides=12, top_radius=None, bevel=0.02, rot=None):
    """Cilindro/tronco de cone com a base em center.z. rot = (eixo, ângulo) para deitar (canos)."""
    bm = bmesh.new()
    r2 = radius if top_radius is None else top_radius
    bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=radius, radius2=max(r2, 1e-4), depth=height)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, height / 2))
    if rot is not None:
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(rot[1], 3, rot[0]))
    bmesh.ops.translate(bm, verts=bm.verts, vec=center)
    return _finish(bm, name, material, bevel)


def dome(name, material, center, radius, squash=0.6, sides=12):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=sides, v_segments=6, radius=radius)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-4], context="VERTS")
    for v in bm.verts:
        v.co.z *= squash
    bmesh.ops.translate(bm, verts=bm.verts, vec=center)
    return _finish(bm, name, material)


def prism(name, material, center, size, ridge=0.5, bevel=0.02, rot_z=0.0):
    """Telhado de uma água/duas águas: seção triangular ao longo de y. ridge = posição da cumeeira em x (0..1)."""
    sx, sy, sz = size
    bm = bmesh.new()
    pts = [(-sx / 2, 0.0), (sx / 2, 0.0), (-sx / 2 + ridge * sx, sz)]
    front = [bm.verts.new((x, -sy / 2, z)) for x, z in pts]
    back = [bm.verts.new((x, sy / 2, z)) for x, z in pts]
    bm.faces.new(front)
    bm.faces.new(reversed(back))
    for i in range(3):
        j = (i + 1) % 3
        bm.faces.new((front[j], front[i], back[i], back[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(rot_z, 3, "Z"))
    bmesh.ops.translate(bm, verts=bm.verts, vec=center)
    return _finish(bm, name, material, bevel)


def beam(name, material, a, b, thick=0.06):
    """Viga de seção quadrada de a até b (treliças, escoras, canos finos)."""
    a, b = Vector(a), Vector(b)
    d = b - a
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= thick
        v.co.y *= thick
        v.co.z = (v.co.z + 0.5) * d.length
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=d.to_track_quat("Z", "Y").to_matrix())
    bmesh.ops.translate(bm, verts=bm.verts, vec=a)
    return _finish(bm, name, material)


def merlons(material, a, b, z, count, size, along_x):
    """Fileira de ameias de a até b (coordenada ao longo do eixo), centradas na outra coordenada fixa."""
    lo, hi, fixed = a, b, size[3]
    step = (hi - lo) / count
    for i in range(count):
        c = lo + (i + 0.5) * step
        pos = (c, fixed, z) if along_x else (fixed, c, z)
        dims = (size[0], size[1], size[2]) if along_x else (size[1], size[0], size[2])
        box("merlon", material, pos, dims, bevel=0.02)


def ring(name, material, center, radius, height, thick=0.04, sides=12):
    """Cinta em volta de um tanque/chaminé."""
    return cyl(name, material, center, radius + thick, height, sides=sides, bevel=0.0)


# ---------------------------------------------------------------------------------------------------------
# Peças compostas
# ---------------------------------------------------------------------------------------------------------


def battered_wall(material, trim, a, b, fixed, along_x, height=1.25, thick=0.62, cap=None, n_merlons=5):
    """Cortina em talude com rodapé, faixa de remate e ameias largas e baixas."""
    length = abs(b - a)
    mid = (a + b) / 2
    c = (mid, fixed, 0.0) if along_x else (fixed, mid, 0.0)
    dims = (length, thick, height) if along_x else (thick, length, height)
    tp = (1.0, 0.72) if along_x else (0.72, 1.0)
    box("wall", material, c, dims, bevel=0.03, taper=tp[0], taper_y=tp[1])
    foot = (length, thick * 1.18, 0.16) if along_x else (thick * 1.18, length, 0.16)
    box("wall_foot", trim, c, foot, bevel=0.03)
    band = (length, thick * 0.80, 0.09) if along_x else (thick * 0.80, length, 0.09)
    box("wall_band", cap or trim, (c[0], c[1], height), band, bevel=0.015)
    merlons(cap or material, a + 0.15, b - 0.15, height + 0.09, n_merlons, (length / n_merlons * 0.55, thick * 0.62, 0.2, fixed), along_x)


def buttress(material, pos, toward, height=0.95):
    """Contraforte inclinado encostado na muralha; toward = vetor unitário (x, y) para fora."""
    tx, ty = toward
    size = (0.34 if tx else 0.26, 0.34 if ty else 0.26, height)
    box("buttress", material, (pos[0] + tx * 0.14, pos[1] + ty * 0.14, 0.0), size, bevel=0.03, taper=0.55 if tx else 1.0, taper_y=0.55 if ty else 1.0)


def window(frame, glow, pos, facing, w=0.16, h=0.34):
    """Janela alta embutida: moldura escura + vidro aceso pequeno. facing = 'x+', 'x-', 'y+', 'y-'."""
    ax, sign = facing[0], (1 if facing[1] == "+" else -1)
    d = 0.05
    if ax == "x":
        box("win_frame", frame, (pos[0] + sign * d / 2, pos[1], pos[2]), (d, w + 0.07, h + 0.07), bevel=0.0)
        box("win_glow", glow, (pos[0] + sign * d * 0.8, pos[1], pos[2] + 0.035), (d, w, h), bevel=0.0)
    else:
        box("win_frame", frame, (pos[0], pos[1] + sign * d / 2, pos[2]), (w + 0.07, d, h + 0.07), bevel=0.0)
        box("win_glow", glow, (pos[0], pos[1] + sign * d * 0.8, pos[2] + 0.035), (w, d, h), bevel=0.0)


def chimney(body, band, dark, pos, height, radius=0.2):
    cyl("stack_base", dark, pos, radius * 1.5, 0.22, sides=8)
    cyl("stack", body, (pos[0], pos[1], pos[2] + 0.2), radius * 1.12, height - 0.2, sides=10, top_radius=radius * 0.82)
    ring("stack_band", band, (pos[0], pos[1], pos[2] + height * 0.62), radius * 0.93, 0.09, sides=10)
    ring("stack_rim", dark, (pos[0], pos[1], pos[2] + height - 0.1), radius * 0.84, 0.14, thick=0.05, sides=10)
    cyl("stack_hole", mat("soot", 0x15120F), (pos[0], pos[1], pos[2] + height + 0.02), radius * 0.7, 0.03, sides=10, bevel=0.0)


def tank_bastion(body, band, dark, roof, pos, radius=0.86, height=1.45):
    """Bastião-tanque: tambor rebitado com cintas, teto cônico baixo, escada e guarda-corpo."""
    cyl("tank_foot", dark, pos, radius * 1.1, 0.2, sides=14)
    cyl("tank", body, (pos[0], pos[1], 0.18), radius, height, sides=14, bevel=0.02)
    for z in (0.5, 1.0):
        ring("tank_band", band, (pos[0], pos[1], z + 0.16), radius, 0.07, sides=14)
    ring("tank_lip", dark, (pos[0], pos[1], height + 0.12), radius, 0.1, thick=0.06, sides=14)
    cyl("tank_roof", roof, (pos[0], pos[1], height + 0.2), radius * 0.98, 0.3, sides=14, top_radius=radius * 0.2, bevel=0.0)
    cyl("tank_vent", dark, (pos[0], pos[1], height + 0.45), 0.1, 0.16, sides=8)


def cupola_bastion(concrete, trim, steel, dark, pos, aim, radius=0.9, height=1.3):
    """Bastião de artilharia (forte Brialmont): tambor octogonal de concreto em talude e cúpula de aço com canhão."""
    cyl("bastion_foot", trim, pos, radius * 1.16, 0.2, sides=8)
    cyl("bastion", concrete, (pos[0], pos[1], 0.16), radius * 1.06, height, sides=8, top_radius=radius * 0.9, bevel=0.03)
    ring("bastion_band", trim, (pos[0], pos[1], height + 0.1), radius * 0.86, 0.1, thick=0.06, sides=8)
    dome("cupola", steel, (pos[0], pos[1], height + 0.2), radius * 0.62, squash=0.62, sides=12)
    ring("cupola_ring", dark, (pos[0], pos[1], height + 0.18), radius * 0.62, 0.06, thick=0.05, sides=12)
    ang = math.atan2(aim[1], aim[0])
    tip = (pos[0] + math.cos(ang) * radius * 1.25, pos[1] + math.sin(ang) * radius * 1.25, height + 0.42)
    root = (pos[0] + math.cos(ang) * radius * 0.3, pos[1] + math.sin(ang) * radius * 0.3, height + 0.36)
    beam("gun", dark, root, tip, thick=0.11)
    beam("gun_muzzle", steel, (Vector(root).lerp(Vector(tip), 0.86)), tip, thick=0.15)


def derrick(steel, dark, accent, pos, base=0.62, top=0.14, height=1.7, lean=(0.0, 0.0)):
    """Torre de perfuração em treliça: 4 pernas, 3 anéis, contraventamento em X e coroa. lean tomba o topo."""
    x, y, z = pos
    legs = []
    for sx, sy in ((1, 1), (1, -1), (-1, -1), (-1, 1)):
        a = (x + sx * base / 2, y + sy * base / 2, z)
        b = (x + lean[0] + sx * top / 2, y + lean[1] + sy * top / 2, z + height)
        legs.append((Vector(a), Vector(b)))
        beam("derrick_leg", steel, a, b, thick=0.07)
    levels = (0.0, 0.34, 0.66, 1.0)
    for li, t in enumerate(levels):
        pts = [a.lerp(b, t) for a, b in legs]
        for i in range(4):
            beam("derrick_ring", steel, pts[i], pts[(i + 1) % 4], thick=0.05)
        if li + 1 < len(levels):
            up = [a.lerp(b, levels[li + 1]) for a, b in legs]
            for i in range(4):
                beam("derrick_x", dark, pts[i], up[(i + 1) % 4], thick=0.035)
    box("derrick_crown", dark, (x + lean[0], y + lean[1], z + height), (top * 2.0, top * 2.0, 0.12), bevel=0.02)
    if accent is not None:
        box("derrick_lamp", accent, (x + lean[0], y + lean[1], z + height + 0.12), (0.09, 0.09, 0.09), bevel=0.0)


def horn(material, pos, out, length=1.0, radius=0.16):
    """Chifre de osso em três gomos, curvando para cima a partir da direção `out` (x, y)."""
    p = Vector(pos)
    ox, oy = out
    for i, pitch in enumerate((20.0, 48.0, 76.0)):
        a = math.radians(pitch)
        step = Vector((ox * math.cos(a), oy * math.cos(a), math.sin(a))) * (length / 3)
        r0, r1 = radius * (1 - i / 3), radius * (1 - (i + 1) / 3)
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=r0, radius2=max(r1, 1e-4), depth=step.length * 1.08)
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, step.length / 2))
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=step.to_track_quat("Z", "Y").to_matrix())
        bmesh.ops.translate(bm, verts=bm.verts, vec=p)
        _finish(bm, "horn", material)
        p = p + step


def pipe_run(material, flange, points, radius=0.075):
    """Cano por uma lista de pontos, com flange em cada joelho."""
    for a, b in itertools.pairwise(points):
        beam("pipe", material, a, b, thick=radius * 2)
    for p in points[1:-1]:
        box("pipe_flange", flange, (p[0], p[1], p[2] - radius * 1.3), (radius * 2.8, radius * 2.8, radius * 2.6), bevel=0.01)


# ---------------------------------------------------------------------------------------------------------
# Castelos
# ---------------------------------------------------------------------------------------------------------


def compact_refinery():
    """Frente do Petróleo, Pumpers' Compact: refinaria-fortaleza (aço, concreto, chaminés, tanques, torre)."""
    concrete = mat("concrete", 0x8F897B)
    concrete_dk = mat("concrete_dark", 0x5F5A50)
    steel = mat("steel", 0x56606A)
    iron = mat("iron", 0x2B2F34)
    oxide = mat("oxide", 0xA5502B)
    brick = mat("brick", 0x7C3D2E)
    roof = mat("roof", 0x3A4148)
    lamp = mat("lamp", 0xFFC658, emit=3.0)
    arc = mat("arc", 0x8FE0FF, emit=3.0)
    deck = mat("concrete_light", 0xB3AC97)
    hazard = mat("hazard", 0xE2B224)
    void = mat("void", 0x141518)

    half = 2.6
    # Plataforma em dois degraus: a fortaleza senta num glacis, não direto no chão.
    box("plinth", concrete_dk, (0, 0, 0), (half * 2 + 0.3, half * 2 + 0.3, 0.14), bevel=0.05, taper=0.96, taper_y=0.96)
    box("yard", concrete, (0, 0, 0.12), (half * 2 - 0.5, half * 2 - 0.5, 0.08), bevel=0.03)

    w = half - 0.42  # eixo das cortinas
    for along_x, fixed in ((True, w), (True, -w), (False, -w)):
        battered_wall(concrete, concrete_dk, -w + 0.55, w - 0.55, fixed, along_x, cap=steel)
    # Frente (lado da lane): duas meias cortinas ladeando a portaria.
    battered_wall(concrete, concrete_dk, -w + 0.55, -0.72, w, False, cap=steel, n_merlons=2)
    battered_wall(concrete, concrete_dk, 0.72, w - 0.55, w, False, cap=steel, n_merlons=2)
    # Vista de cima, o que se lê é o plano: convés claro no topo das cortinas e canhoneiras escuras nos flancos.
    for sgn in (-1, 1):
        box("deck", deck, (0, sgn * w, 1.3), (2 * w - 1.6, 0.3, 0.05), bevel=0.0)
        for t in (-1.1, 0.0, 1.1):
            box("embrasure", void, (t, sgn * (w + 0.27), 0.62), (0.42, 0.06, 0.2), bevel=0.0)
            box("embrasure_sill", concrete_dk, (t, sgn * (w + 0.29), 0.54), (0.54, 0.08, 0.07), bevel=0.0)
    box("deck", deck, (-w, 0, 1.3), (0.3, 2 * w - 1.6, 0.05), bevel=0.0)
    for t in (-0.95, 0.95):
        buttress(concrete_dk, (t, w + 0.3, 0.0), (0, 1))
        buttress(concrete_dk, (t, -w - 0.3, 0.0), (0, -1))
        buttress(concrete_dk, (-w - 0.3, t, 0.0), (-1, 0))

    # Bastiões: canhões em cúpula na frente, tanques de óleo atrás.
    cupola_bastion(concrete, concrete_dk, steel, iron, (w, w, 0), (1, 0.45))
    cupola_bastion(concrete, concrete_dk, steel, iron, (w, -w, 0), (1, -0.45))
    tank_bastion(steel, oxide, iron, roof, (-w, w, 0))
    tank_bastion(steel, oxide, iron, roof, (-w, -w, 0))

    # Portaria: bloco saliente com portão de aço em arco, pilastras e lâmpada.
    gx = w + 0.1
    box("gate_block", concrete, (gx, 0, 0.1), (0.95, 1.5, 1.62), bevel=0.04, taper=0.9, taper_y=0.94)
    box("gate_cap", steel, (gx, 0, 1.72), (0.98, 1.44, 0.12), bevel=0.02)
    merlons(steel, -0.62, 0.62, 1.84, 3, (0.26, 0.6, 0.18, gx), False)
    box("gate_door", iron, (gx + 0.46, 0, 0.12), (0.08, 0.82, 0.98), bevel=0.0)
    cyl("gate_arch", iron, (gx + 0.42, 0, 1.1), 0.41, 0.08, sides=12, bevel=0.0, rot=("Y", math.radians(90)))
    for s in (-1, 1):
        box("gate_pilaster", concrete_dk, (gx + 0.44, s * 0.58, 0.1), (0.18, 0.22, 1.5), bevel=0.02, taper_y=0.8)
        box("gate_strap", steel, (gx + 0.5, s * 0.2, 0.2), (0.03, 0.06, 0.85), bevel=0.0)
    box("gate_lamp", arc, (gx + 0.5, 0, 1.56), (0.06, 0.16, 0.08), bevel=0.0)
    box("gate_chevron", hazard, (gx + 0.51, 0, 0.5), (0.03, 0.8, 0.14), bevel=0.0)
    box("gate_emblem", hazard, (gx + 0.5, 0, 1.24), (0.04, 0.3, 0.22), bevel=0.0)
    box("gate_kerb", hazard, (gx + 0.62, 0, 0.1), (0.3, 1.1, 0.05), bevel=0.0)

    # Refinaria (torre de menagem) em três degraus, recuada para o fundo.
    kx = -0.55
    box("keep_base", concrete, (kx, 0, 0.18), (2.5, 2.3, 1.5), bevel=0.05, taper=0.93, taper_y=0.93)
    box("keep_band", steel, (kx, 0, 1.66), (2.4, 2.2, 0.1), bevel=0.02)
    box("keep_mid", concrete, (kx - 0.15, 0, 1.74), (1.75, 1.6, 0.85), bevel=0.04, taper=0.94, taper_y=0.94)
    box("keep_mid_band", steel, (kx - 0.15, 0, 2.58), (1.68, 1.54, 0.08), bevel=0.02)
    merlons(steel, kx - 1.1, kx + 1.1, 1.76, 4, (0.3, 0.14, 0.16, 1.06), True)
    merlons(steel, kx - 1.1, kx + 1.1, 1.76, 4, (0.3, 0.14, 0.16, -1.06), True)
    for y in (-0.7, 0.0, 0.7):
        window(iron, lamp, (kx + 1.25, y, 0.75), "x+")
    for y in (-0.4, 0.4):
        window(iron, lamp, (kx - 0.15 + 0.875, y, 1.98), "x+", w=0.14, h=0.3)
    for x in (kx - 0.75, kx, kx + 0.75):
        window(iron, lamp, (x, 1.15, 0.8), "y+")
        window(iron, lamp, (x, -1.15, 0.8), "y-")

    # Galpão de dente de serra encostado na face da lane: a silhueta de fábrica.
    for i, y in enumerate((-0.72, 0.0, 0.72)):
        prism(f"sawtooth{i}", roof, (kx + 1.05, y, 1.74), (0.62, 0.7, 0.42), ridge=0.12, rot_z=math.radians(90))
        box("sawtooth_glass", lamp, (kx + 1.05, y - 0.3, 1.8), (0.5, 0.03, 0.22), bevel=0.0)

    # Chaminés: três, de alturas diferentes, agrupadas no fundo.
    chimney(brick, oxide, iron, (kx - 0.85, 0.5, 1.74), 1.55, radius=0.19)
    chimney(brick, oxide, iron, (kx - 0.9, -0.15, 1.74), 2.65, radius=0.25)
    chimney(brick, oxide, iron, (kx - 0.45, -0.68, 1.74), 1.2, radius=0.16)

    # Coroa: torre de perfuração sobre o degrau do meio.
    derrick(steel, iron, arc, (kx + 0.35, 0.38, 2.66), base=0.66, top=0.16, height=1.7)
    box("doghouse", roof, (kx + 0.3, -0.42, 2.66), (0.5, 0.42, 0.32), bevel=0.02)
    prism("doghouse_roof", iron, (kx + 0.3, -0.42, 2.98), (0.56, 0.48, 0.16), ridge=0.5)

    # Canos dos tanques até a refinaria, sobre a cortina de trás.
    for s in (-1, 1):
        pipe_run(oxide, iron, [(-w, s * (w - 0.9), 1.25), (-w, s * 0.8, 1.25), (kx - 1.2, s * 0.8, 1.25), (kx - 1.2, s * 0.8, 0.9)])
    pipe_run(oxide, iron, [(kx + 0.6, 1.2, 1.9), (kx + 0.6, 1.75, 1.9), (kx + 0.6, 1.75, 1.5)])

    # Parque de tanques no pátio (lado direito de quem ataca): quebra a simetria e enche o plano.
    cyl("yard_tank", steel, (1.25, -1.05, 0.2), 0.36, 0.72, sides=12)
    ring("yard_tank_band", hazard, (1.25, -1.05, 0.55), 0.36, 0.1, sides=12)
    cyl("yard_tank_roof", roof, (1.25, -1.05, 0.92), 0.36, 0.12, sides=12, top_radius=0.08, bevel=0.0)
    cyl("yard_tank", steel, (1.3, -0.4, 0.2), 0.26, 0.5, sides=10)
    cyl("yard_tank_roof", roof, (1.3, -0.4, 0.7), 0.26, 0.1, sides=10, top_radius=0.06, bevel=0.0)
    for i, (dx, dy) in enumerate(((0.0, 0.0), (0.2, 0.05), (0.08, 0.2))):
        cyl("drum", hazard if i == 1 else oxide, (1.15 + dx, 0.7 + dy, 0.2), 0.085, 0.2, sides=8, bevel=0.0)
    ring("tank_hazard", hazard, (-w, -w, 1.3), 0.86, 0.1, sides=14)
    # Holofotes nos bastiões de trás e lâmpadas no pátio.
    for s in (-1, 1):
        box("searchlight", arc, (-w, s * w, 1.82), (0.1, 0.1, 0.1), bevel=0.0)
        box("yard_lamp_post", iron, (1.0, s * 1.3, 0.2), (0.06, 0.06, 0.7), bevel=0.0)
        box("yard_lamp", lamp, (1.0, s * 1.3, 0.9), (0.1, 0.1, 0.08), bevel=0.0)


def spike(material, pos, height=0.42, radius=0.07, lean=(0.0, 0.0)):
    tip = (pos[0] + lean[0], pos[1] + lean[1], pos[2] + height)
    a, b = Vector(pos), Vector(tip)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=5, radius1=radius, radius2=1e-4, depth=(b - a).length)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, (b - a).length / 2))
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=(b - a).to_track_quat("Z", "Y").to_matrix())
    bmesh.ops.translate(bm, verts=bm.verts, vec=a)
    return _finish(bm, "spike", material)


def flame(core, outer, pos, size=0.3):
    """Chama low-poly: três cones tortos, o de fora laranja e o miolo amarelo."""
    cyl("flame_outer", outer, pos, size * 0.62, size * 1.5, sides=6, top_radius=0.0, bevel=0.0)
    cyl("flame_side", outer, (pos[0] + size * 0.3, pos[1] - size * 0.2, pos[2]), size * 0.36, size * 0.95, sides=5, top_radius=0.0, bevel=0.0)
    cyl("flame_side", outer, (pos[0] - size * 0.28, pos[1] + size * 0.24, pos[2]), size * 0.32, size * 0.8, sides=5, top_radius=0.0, bevel=0.0)
    cyl("flame_core", core, (pos[0], pos[1], pos[2] + size * 0.05), size * 0.34, size * 0.95, sides=5, top_radius=0.0, bevel=0.0)


def brazier(iron, ember, core, outer, pos, radius=0.26, fire=0.26):
    """Braseiro: tripé curto, tigela de ferro, brasa e chama."""
    cyl("brazier_stem", iron, pos, radius * 0.3, 0.22, sides=6, bevel=0.0)
    cyl("brazier_bowl", iron, (pos[0], pos[1], pos[2] + 0.2), radius * 0.5, 0.2, sides=8, top_radius=radius, bevel=0.0)
    cyl("brazier_ember", ember, (pos[0], pos[1], pos[2] + 0.38), radius * 0.86, 0.04, sides=8, bevel=0.0)
    flame(core, outer, (pos[0], pos[1], pos[2] + 0.4), size=fire)


def arrow_bastion(stone, dark, iron, pos, out, radius=1.02, height=1.35):
    """Bastião em ponta de flecha (forte abaluartado): pentágono em talude com a quina para fora e espinhos."""
    ang = math.atan2(out[1], out[0])
    cyl("bastion_foot", dark, pos, radius * 1.16, 0.2, sides=5, bevel=0.03, rot=("Z", ang))
    cyl("bastion", stone, (pos[0], pos[1], 0.16), radius * 1.08, height, sides=5, top_radius=radius * 0.8, bevel=0.04, rot=("Z", ang))
    cyl("bastion_cap", dark, (pos[0], pos[1], height + 0.14), radius * 0.86, 0.14, sides=5, bevel=0.02, rot=("Z", ang))
    for i in range(5):
        a = ang + i * math.tau / 5
        rim = (pos[0] + math.cos(a) * radius * 0.8, pos[1] + math.sin(a) * radius * 0.8, height + 0.24)
        spike(iron, rim, height=0.5, radius=0.08, lean=(math.cos(a) * 0.22, math.sin(a) * 0.22))
        mid = a + math.tau / 10
        edge = (pos[0] + math.cos(mid) * radius * 0.62, pos[1] + math.sin(mid) * radius * 0.62, height + 0.26)
        box("bastion_merlon", stone, edge, (0.24, 0.24, 0.2), bevel=0.02, rot_z=mid)


def banner(pole, cloth, pos, height=1.1, facing=0.0):
    box("banner_pole", pole, pos, (0.05, 0.05, height), bevel=0.0)
    c, s = math.cos(facing), math.sin(facing)
    box("banner_cloth", cloth, (pos[0] + c * 0.17, pos[1] + s * 0.17, pos[2] + height - 0.52), (0.3, 0.03, 0.5), bevel=0.0, rot_z=facing)
    box("banner_tail", cloth, (pos[0] + c * 0.1, pos[1] + s * 0.1, pos[2] + height - 0.68), (0.13, 0.03, 0.18), bevel=0.0, rot_z=facing)


def torchbound_bastion():
    """Frente do Petróleo, Torchbound: bastião queimado (basalto, ferro, espinhos, braseiros, a grande pira)."""
    basalt = mat("basalt", 0x4A433E)
    ash = mat("ash", 0x6A6058)
    char = mat("char", 0x26221F)
    iron = mat("iron", 0x2B2D30)
    rust = mat("rust", 0x7E3C22)
    wood = mat("wood", 0x6E5236)
    cloth = mat("cloth", 0xA8281C)
    ember = mat("ember", 0xFF6A14, emit=3.0)
    fire = mat("fire", 0xFF8A1E, emit=3.5)
    core = mat("fire_core", 0xFFD860, emit=4.0)
    bone = mat("bone", 0xCBBE9C)

    half = 2.6
    box("plinth", char, (0, 0, 0), (half * 2 + 0.4, half * 2 + 0.4, 0.16), bevel=0.06, taper=0.94, taper_y=0.94)
    box("yard", basalt, (0, 0, 0.14), (half * 2 - 0.6, half * 2 - 0.6, 0.08), bevel=0.03)

    w = half - 0.5
    for along_x, fixed in ((True, w), (True, -w), (False, -w)):
        battered_wall(basalt, char, -w + 0.6, w - 0.6, fixed, along_x, height=1.2, thick=0.78, cap=ash, n_merlons=4)
    battered_wall(basalt, char, -w + 0.6, -0.8, w, False, height=1.2, thick=0.78, cap=ash, n_merlons=2)
    battered_wall(basalt, char, 0.8, w - 0.6, w, False, height=1.2, thick=0.78, cap=ash, n_merlons=2)
    # Estacas de ferro fincadas no pé da muralha, apontando para fora.
    for t in (-1.1, -0.55, 0.0, 0.55, 1.1):
        spike(iron, (t, w + 0.42, 0.1), height=0.5, lean=(0.0, 0.3))
        spike(iron, (t, -w - 0.42, 0.1), height=0.5, lean=(0.0, -0.3))
        spike(iron, (-w - 0.42, t, 0.1), height=0.5, lean=(-0.3, 0.0))

    for sy in (1, -1):
        arrow_bastion(basalt, char, iron, (w, sy * w, 0), (1, sy))
        brazier(iron, ember, core, fire, (w, sy * w, 1.62), radius=0.3, fire=0.3)
        horn(bone, (w + 0.55, sy * (w + 0.55), 1.2), (0.707, sy * 0.707), length=1.25, radius=0.2)
    # Fundos desiguais: torre redonda com chapéu de ferro torto de um lado, guarita de madeira do outro.
    cyl("round_foot", char, (-w, w, 0), 1.05, 0.2, sides=10)
    cyl("round_tower", basalt, (-w, w, 0.16), 0.95, 1.9, sides=10, top_radius=0.8, bevel=0.03)
    ring("round_band", ash, (-w, w, 1.5), 0.84, 0.12, thick=0.05, sides=10)
    cyl("round_cap", iron, (-w + 0.05, w, 2.06), 0.95, 0.62, sides=10, top_radius=0.0, bevel=0.0)
    for i in range(6):
        a = i * math.tau / 6
        spike(iron, (-w + math.cos(a) * 0.86, w + math.sin(a) * 0.86, 2.02), height=0.3, radius=0.06, lean=(math.cos(a) * 0.3, math.sin(a) * 0.3))
    horn(bone, (-w - 0.6, w + 0.6, 1.0), (-0.707, 0.707), length=1.1, radius=0.18)
    arrow_bastion(basalt, char, iron, (-w, -w, 0), (-1, -1), radius=0.9, height=1.1)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        beam("watch_leg", wood, (-w + sx * 0.5, -w + sy * 0.5, 1.3), (-w + sx * 0.36, -w + sy * 0.36, 2.25), thick=0.08)
    box("watch_floor", wood, (-w, -w, 2.25), (0.95, 0.95, 0.09), bevel=0.01)
    box("watch_rail", wood, (-w, -w - 0.44, 2.34), (0.95, 0.06, 0.22), bevel=0.0)
    box("watch_rail", wood, (-w - 0.44, -w, 2.34), (0.06, 0.95, 0.22), bevel=0.0)
    prism("watch_roof", char, (-w, -w, 2.86), (1.15, 1.1, 0.26), ridge=0.5)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        beam("watch_post", wood, (-w + sx * 0.4, -w + sy * 0.4, 2.3), (-w + sx * 0.4, -w + sy * 0.4, 2.88), thick=0.06)
    horn(bone, (-w - 0.5, -w - 0.5, 0.9), (-0.707, -0.707), length=0.95, radius=0.16)

    # Portaria: bocarra de pedra queimada com presas de ferro, grade e correntes.
    gx = w + 0.12
    box("gate_block", basalt, (gx, 0, 0.1), (1.1, 1.7, 1.55), bevel=0.05, taper=0.84, taper_y=0.9)
    box("gate_cap", char, (gx, 0, 1.64), (0.98, 1.56, 0.14), bevel=0.03)
    box("gate_maw", char, (gx + 0.5, 0, 0.12), (0.12, 0.9, 1.02), bevel=0.0)
    for y in (-0.3, -0.1, 0.1, 0.3):
        box("gate_bar", iron, (gx + 0.56, y, 0.14), (0.05, 0.06, 0.98), bevel=0.0)
    for z in (0.45, 0.85):
        box("gate_cross", iron, (gx + 0.57, 0, z), (0.05, 0.86, 0.06), bevel=0.0)
    for s in (-1, 1):
        box("gate_tusk", ash, (gx + 0.5, s * 0.66, 0.1), (0.3, 0.3, 1.3), bevel=0.03, taper=0.5, taper_y=0.5)
        horn(bone, (gx + 0.5, s * 0.66, 1.36), (1.0, 0.0), length=0.85, radius=0.15)
        spike(iron, (gx + 0.2, s * 0.6, 1.76), height=0.42, lean=(0.1, s * 0.12))
        banner(iron, cloth, (gx + 0.62, s * 1.02, 0.5), height=1.25, facing=0.0)
    brazier(iron, ember, core, fire, (gx - 0.05, 0, 1.76), radius=0.26, fire=0.24)

    # Torre da pira: zigurate atarracado de três degraus, com tapumes de madeira e a pira no topo.
    kx = -0.45
    box("keep_base", basalt, (kx, 0, 0.18), (2.7, 2.7, 1.25), bevel=0.06, taper=0.84, taper_y=0.84)
    box("keep_lip", char, (kx, 0, 1.41), (2.34, 2.34, 0.12), bevel=0.03)
    box("keep_mid", ash, (kx, 0, 1.5), (1.8, 1.8, 0.8), bevel=0.05, taper=0.84, taper_y=0.84)
    box("keep_mid_lip", char, (kx, 0, 2.28), (1.58, 1.58, 0.1), bevel=0.03)
    box("keep_top", basalt, (kx, 0, 2.36), (1.15, 1.15, 0.5), bevel=0.04, taper=0.86, taper_y=0.86)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        horn(bone, (kx + sx * 1.0, sy * 1.0, 1.45), (sx * 0.707, sy * 0.707), length=0.8, radius=0.13)
        spike(iron, (kx + sx * 0.68, sy * 0.68, 2.36), height=0.5, radius=0.08, lean=(sx * 0.16, sy * 0.16))
    # Seteiras em brasa nas quatro faces do primeiro degrau.
    for t in (-0.6, 0.0, 0.6):
        window(char, ember, (kx + 1.24, t, 0.62), "x+", w=0.1, h=0.36)
        window(char, ember, (kx + t, 1.24, 0.62), "y+", w=0.1, h=0.36)
        window(char, ember, (kx + t, -1.24, 0.62), "y-", w=0.1, h=0.36)
    # Tapume de madeira (hourd) na face da lane do segundo degrau.
    box("hoarding", wood, (kx + 0.86, 0, 1.92), (0.22, 1.5, 0.34), bevel=0.02)
    box("hoarding_roof", char, (kx + 0.9, 0, 2.26), (0.34, 1.6, 0.07), bevel=0.01)
    for y in (-0.6, -0.2, 0.2, 0.6):
        beam("hoarding_strut", wood, (kx + 0.78, y, 1.55), (kx + 0.95, y, 1.92), thick=0.06)
    # A grande pira: tigela de ferro sobre o topo, com correntes e a chama mais alta do castelo.
    cyl("pyre_bowl", iron, (kx, 0, 2.84), 0.36, 0.34, sides=8, top_radius=0.74, bevel=0.0)
    ring("pyre_rim", rust, (kx, 0, 3.14), 0.72, 0.08, thick=0.06, sides=8)
    cyl("pyre_ember", ember, (kx, 0, 3.2), 0.66, 0.05, sides=8, bevel=0.0)
    flame(core, fire, (kx + 0.1, -0.1, 3.22), size=0.55)
    flame(core, fire, (kx - 0.3, 0.25, 3.22), size=0.36)
    # A coroa: a torre de perfuração tomada, fincada na pira e tombando para o fundo, com a ponta em brasa.
    derrick(rust, iron, None, (kx - 0.05, 0.05, 3.1), base=0.62, top=0.2, height=1.75, lean=(-0.55, 0.42))
    flame(core, fire, (kx - 0.6, 0.47, 4.95), size=0.22)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        beam("pyre_chain", iron, (kx + sx * 0.5, sy * 0.5, 3.1), (kx + sx * 0.52, sy * 0.52, 2.4), thick=0.04)

    # Troféu: torre de perfuração tombada e queimada, encostada na muralha de trás.
    base = Vector((-w + 0.2, 0.9, 1.3))
    tip = Vector((-w - 1.5, 1.9, 0.2))
    side = Vector((0.22, 0.2, 0.0))
    for off in (side, -side, Vector((0, 0, 0.3))):
        beam("wreck_leg", rust, base + off, tip + off * 0.3, thick=0.07)
    for t in (0.2, 0.45, 0.7):
        p = base.lerp(tip, t)
        beam("wreck_tie", char, p + side * (1 - t * 0.7), p - side * (1 - t * 0.7), thick=0.05)
        beam("wreck_tie", char, p - side * (1 - t * 0.7), p + Vector((0, 0, 0.3 * (1 - t * 0.7))), thick=0.05)
    flame(core, fire, (-w - 0.9, 1.5, 0.55), size=0.3)

    # Paliçada de troncos queimados nos cantos de trás.
    for s in (-1, 1):
        banner(iron, cloth, (-0.2, s * (w + 0.02), 1.3), height=1.0, facing=s * math.radians(90))
        for i in range(4):
            box("stake", wood, (-w + 0.75 + i * 0.16, s * (w - 0.62), 0.2), (0.12, 0.12, 0.75 + 0.12 * (i % 2)), bevel=0.02, taper=0.6, taper_y=0.6)


CASTLES = {"oil_compact": compact_refinery, "oil_torchbound": torchbound_bastion}

# ---------------------------------------------------------------------------------------------------------
# Saída
# ---------------------------------------------------------------------------------------------------------


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()


def bake():
    """Aplica modificadores, sombreia chapado e junta por material (um mesh por cor = poucas draw calls)."""
    obs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in obs:
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target="MESH")
    by_mat = {}
    for o in obs:
        for p in o.data.polygons:
            p.use_smooth = False
        by_mat.setdefault(o.data.materials[0].name, []).append(o)
    for name, group in by_mat.items():
        bpy.ops.object.select_all(action="DESELECT")
        for o in group:
            o.select_set(True)
        bpy.context.view_layer.objects.active = group[0]
        if len(group) > 1:
            bpy.ops.object.join()
        bpy.context.view_layer.objects.active.name = name


def stats():
    tris = sum(len(p.vertices) - 2 for o in bpy.context.scene.objects if o.type == "MESH" for p in o.data.polygons)
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in bpy.context.scene.objects:
        if o.type != "MESH":
            continue
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            lo, hi = Vector(map(min, lo, w)), Vector(map(max, hi, w))
    return tris, lo, hi


def render(path, yaw_deg, tilt_deg=52.0, ground=0x6B5A45, span=6.4, top=2.6):
    """Prévia na inclinação da câmera do jogo (ortográfica), com chão de lama e sol baixo."""
    scene = bpy.context.scene
    extra = []
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=14.0)
    extra.append(_finish(bm, "ground", mat("ground", ground)))
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = span * 1.5
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    tilt, yaw = math.radians(tilt_deg), math.radians(yaw_deg)
    target = Vector((0, 0, top / 2))
    direction = Vector((math.cos(yaw) * math.cos(tilt), math.sin(yaw) * math.cos(tilt), math.sin(tilt)))
    cam.location = target + direction * 30
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    sun_data = bpy.data.lights.new("sun", "SUN")
    sun_data.energy = 3.2
    sun_data.color = (1.0, 0.86, 0.68)
    sun_data.angle = math.radians(2)
    sun = bpy.data.objects.new("sun", sun_data)
    sun.rotation_euler = (math.radians(58), 0, math.radians(yaw_deg + 55))
    scene.collection.objects.link(sun)
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.42, 0.44, 0.52, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.75
    scene.world = world
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x, scene.render.resolution_y = 1100, 820
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    for o in (*extra, cam, sun):
        bpy.data.objects.remove(o)


def build(name, out_dir, render_dir, make=None, views=(("front", -35.0), ("back", 150.0), ("game", -90.0))):
    reset()
    (make or CASTLES[name])()
    bake()
    tris, lo, hi = stats()
    print(f"MODEL {name}: tris={tris} min=({lo.x:.2f},{lo.y:.2f},{lo.z:.2f}) max=({hi.x:.2f},{hi.y:.2f},{hi.z:.2f})")
    if render_dir:
        os.makedirs(render_dir, exist_ok=True)
        span = max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, 0.5)
        for tag, yaw in views:
            render(os.path.join(render_dir, f"{name}_{tag}.png"), yaw, span=span, top=hi.z)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.export_scene.gltf(filepath=os.path.join(out_dir, f"{name}.glb"), export_format="GLB", use_selection=True, export_yup=True, export_apply=True)


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["all"]
    names = list(CASTLES) if args[0] == "all" else [args[0]]
    out_dir = game_paths.out_arg(args, "--out", "castles")
    render_dir = args[args.index("--render") + 1] if "--render" in args else ""
    for name in names:
        build(name, out_dir, render_dir)


if __name__ == "__main__":
    main()
