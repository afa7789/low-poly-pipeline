"""Efeito 3D dos Espinhos (SkillFxKind::Thorns): espinhos com folhas brotando do chão, parada e recuo.

    blender -b --python tools/blender/fx_thorns.py

Grava assets/fx3d/thorns.glb (pequeno, versionado). Procedural e determinístico: nenhum asset de entrada.
Molde para os próximos efeitos 3D: uma malha só, um osso por peça animada (peso 1 no osso), cor assada nos
vértices (sem material nem textura: o motor desenha com o material padrão do raylib, o shader de pixel art faz
o resto) e um clipe único. O motor (render/SkillFx3d) toca o primeiro clipe pelo skinning do raylib.
"""
import math
import random
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

OUT = Path(__file__).resolve().parents[2] / "assets" / "fx3d" / "thorns.glb"
FPS = 30
SPIKES = 9
LEAVES = 6
# Cores pretendidas na tela (o raylib não converte sRGB): base escura -> ponta clara.
BASE, TIP = Vector((0.30, 0.19, 0.10)), Vector((0.80, 0.66, 0.42))
LEAF, LEAF_TIP = Vector((0.20, 0.50, 0.14)), Vector((0.52, 0.80, 0.28))
DIRT = Vector((0.27, 0.18, 0.11))
SUN = Vector((0.35, -0.3, 0.88)).normalized()  # luz falsa assada: de cima, um pouco de lado


def shade(normal):
    return 0.62 + 0.5 * max(0.0, normal.dot(SUN))


def add_spike(bm, layer, groups, base, height, radius, tilt, yaw, bone):
    """Cone torto de 3 anéis (5 faces) com a base em `base`, inclinado `tilt` rad para `yaw`."""
    rot = Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(tilt, 4, "Y")
    rings = [(0.0, radius, 0.0), (0.5, radius * 0.55, 0.06 * height), (1.0, 0.0, 0.0)]
    sides = 5
    verts = []
    for z, r, bend in rings:
        if r == 0.0:
            verts.append([bm.verts.new(base + rot @ Vector((bend, 0, z * height)))])
            continue
        ring = []
        for i in range(sides):
            a = i * 2 * math.pi / sides
            ring.append(bm.verts.new(base + rot @ Vector((math.cos(a) * r + bend, math.sin(a) * r, z * height))))
        verts.append(ring)
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append(bm.faces.new((verts[0][i], verts[0][j], verts[1][j], verts[1][i])))
        faces.append(bm.faces.new((verts[1][i], verts[1][j], verts[2][0])))
    faces.append(bm.faces.new(list(reversed(verts[0]))))  # fundo, p/ não ver o oco se o chão ceder
    paint(bm, layer, groups, faces, bone, BASE, TIP, base.z, base.z + height)


def add_leaf(bm, layer, groups, base, length, width, pitch, yaw, bone):
    """Folha: bipirâmide achatada (8 triângulos, vista dos dois lados) saindo de `base`."""
    rot = Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(pitch, 4, "Y")
    pts = [(0, 0, 0), (length, 0, 0), (length * 0.4, -width, 0), (length * 0.4, width, 0),
           (length * 0.4, 0, width * 0.25), (length * 0.4, 0, -width * 0.25)]
    v = [bm.verts.new(base + rot @ Vector(p)) for p in pts]
    tris = [(0, 2, 4), (0, 4, 3), (0, 5, 2), (0, 3, 5), (1, 4, 2), (1, 3, 4), (1, 2, 5), (1, 5, 3)]
    faces = [bm.faces.new((v[a], v[b], v[c])) for a, b, c in tris]
    lo, hi = min(p.co.z for p in v), max(p.co.z for p in v)
    paint(bm, layer, groups, faces, bone, LEAF, LEAF_TIP, lo, hi)


def add_dirt(bm, layer, groups, radius, height, bone):
    """Anel de terra revolvida: tronco de 9 lados, borda irregular. Marca o chão sob os espinhos."""
    rnd = random.Random(7)
    sides = 9
    outer = [bm.verts.new((math.cos(a) * radius * rnd.uniform(0.85, 1.0), math.sin(a) * radius * rnd.uniform(0.85, 1.0), 0.0))
             for a in (i * 2 * math.pi / sides for i in range(sides))]
    inner = [bm.verts.new((v.co.x * 0.62, v.co.y * 0.62, height)) for v in outer]
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append(bm.faces.new((outer[i], outer[j], inner[j], inner[i])))
    faces.append(bm.faces.new(list(reversed(inner))))
    for f in faces:
        f.normal_update()
        for loop in f.loops:
            loop[layer] = (*(DIRT * shade(f.normal)), 1.0)
            loop.vert[groups][bone] = 1.0


def paint(bm, layer, groups, faces, bone, low, high, z0, z1):
    """Cor por canto: gradiente por altura (base -> ponta) vezes a luz falsa da face; peso 1 no osso."""
    span = max(z1 - z0, 1e-6)
    for f in faces:
        f.normal_update()
        for loop in f.loops:
            t = min(1.0, max(0.0, (loop.vert.co.z - z0) / span))
            loop[layer] = (*(low.lerp(high, t) * shade(f.normal)), 1.0)
            loop.vert[groups][bone] = 1.0


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rnd = random.Random(11)
    mesh = bpy.data.meshes.new("thorns")
    obj = bpy.data.objects.new("thorns", mesh)
    bpy.context.scene.collection.objects.link(obj)
    arm_data = bpy.data.armatures.new("rig")
    arm = bpy.data.objects.new("rig", arm_data)
    bpy.context.scene.collection.objects.link(arm)

    bm = bmesh.new()
    layer = bm.loops.layers.float_color.new("Col")
    groups = bm.verts.layers.deform.new()
    names = ["dirt"]
    obj.vertex_groups.new(name="dirt")
    add_dirt(bm, layer, groups, 1.2, 0.07, 0)
    plan = []  # (osso, cabeça, cauda) dos espinhos
    for i in range(SPIKES):
        ring = 0.0 if i == 0 else 0.5 + 0.5 * (i % 3) / 2
        yaw = i * 2 * math.pi / (SPIKES - 1) + rnd.uniform(-0.25, 0.25) if i else 0.0
        base = Vector((math.cos(yaw) * ring, math.sin(yaw) * ring, 0.04))
        height = 2.0 if i == 0 else rnd.uniform(1.0, 1.7)
        tilt = 0.0 if i == 0 else rnd.uniform(0.25, 0.5)  # abre para fora
        names.append(f"spike{i}")
        obj.vertex_groups.new(name=names[-1])
        add_spike(bm, layer, groups, base, height, 0.17 if i == 0 else rnd.uniform(0.11, 0.15), tilt, yaw, len(names) - 1)
        tail = base + Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(tilt, 4, "Y") @ Vector((0, 0, height))
        plan.append((names[-1], base, tail))
        if i % 3 == 1 or i == 0:  # folhas na altura do 1º terço, no espinho central e em dois outros
            for k in range(2 if i == 0 else 1):
                ly = yaw + (math.pi / 2 + k * math.pi if i == 0 else math.pi / 2)
                lb = base.lerp(tail, 0.28)
                add_leaf(bm, layer, groups, lb, rnd.uniform(0.55, 0.8), 0.17, -rnd.uniform(0.7, 1.0), ly, len(names) - 1)
    bm.to_mesh(mesh)
    bm.free()
    mesh.color_attributes.active_color = mesh.color_attributes["Col"]

    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    dirt = arm_data.edit_bones.new("dirt")
    dirt.head, dirt.tail = (0, 0, 0), (0, 0, 0.2)
    for name, head, tail in plan:
        bone = arm_data.edit_bones.new(name)
        bone.head, bone.tail = head, tail
    bpy.ops.object.mode_set(mode="POSE")
    animate(arm, [n for n, _, _ in plan])
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.parent = arm
    obj.modifiers.new("Armature", "ARMATURE").object = arm
    return arm, obj


def key_scale(arm, name, frame, value):
    pb = arm.pose.bones[name]
    pb.scale = (value, value, value)
    pb.keyframe_insert("scale", frame=frame)


def animate(arm, spikes):
    """Brota escalonado (com estouro), segura, recua. Tempos em segundos; 1 s no total."""
    sec = lambda s: round(s * FPS)  # noqa: E731
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"  # o raylib amostra a reta
    action = bpy.data.actions.new("erupt")
    arm.animation_data_create().action = action
    tiny = 0.001  # escala 0 deixa a matriz singular; isto já some sob o chão
    key_scale(arm, "dirt", 0, 0.4)
    key_scale(arm, "dirt", sec(0.1), 1.0)
    key_scale(arm, "dirt", sec(0.8), 1.0)
    key_scale(arm, "dirt", sec(1.0), tiny)
    for i, name in enumerate(spikes):
        t0 = 0.0 if i == 0 else 0.03 + 0.012 * i  # o central sai primeiro, o resto em onda
        key_scale(arm, name, 0, tiny)
        key_scale(arm, name, sec(t0), tiny)
        key_scale(arm, name, sec(t0 + 0.14), 1.18)  # estouro
        key_scale(arm, name, sec(t0 + 0.22), 1.0)
        key_scale(arm, name, sec(0.62 + 0.012 * i), 1.0)
        key_scale(arm, name, sec(0.9 + 0.01 * i), tiny)
    bpy.context.scene.render.fps = FPS
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 0, sec(1.0)


def main():
    arm, obj = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=str(OUT), export_format="GLB", export_yup=True,
                              export_animations=True, export_animation_mode="ACTIONS",
                              export_apply=False, export_skins=True, export_morph=False,
                              export_vertex_color="ACTIVE", export_active_vertex_color_when_no_material=True,
                              export_materials="NONE")
    print("fx_thorns:", OUT, OUT.stat().st_size, "bytes")


main()
