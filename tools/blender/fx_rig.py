"""Base comum dos efeitos 3D de skill (tools/blender/fx_*.py): malha única, um osso por peça, cor nos vértices.

Cada fx_<nome>.py importa este módulo (`sys.path` já aponta para a pasta do script quando o Blender o roda) e
grava assets/fx3d/<nome>.glb. Sem material nem textura: o motor (render/SkillFx3d) desenha com o material
padrão do raylib e o shader de pixel art faz o resto. O raylib faz o skinning, então o clipe só usa escala e
giro dos ossos:
  - escala `h` = horizontal (X e Y do mundo), `v` = vertical (Z); o osso aponta para +Z, então no espaço do osso
    o eixo Y é a altura. Com a cabeça do osso no centro, escalar `h` empurra a peça para fora (anel que abre).
  - `spin` gira a peça em volta de Z.
"""
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

FPS = 30
TINY = 0.001  # escala 0 deixa a matriz singular; isto já some sob o chão
SUN = Vector((0.35, -0.3, 0.88)).normalized()  # luz falsa assada: de cima, um pouco de lado
OUT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fx3d"


def rgb(r, g, b):
    return Vector((r, g, b))


def sec(seconds):
    return round(seconds * FPS)


def shade(normal):
    return 0.62 + 0.5 * max(0.0, normal.dot(SUN))


class Fx:
    def __init__(self, name):
        self.name = name
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.mesh = bpy.data.meshes.new(name)
        self.obj = bpy.data.objects.new(name, self.mesh)
        bpy.context.scene.collection.objects.link(self.obj)
        self.bm = bmesh.new()
        self.layer = self.bm.loops.layers.float_color.new("Col")
        self.groups = self.bm.verts.layers.deform.new()
        self.bones = []  # (nome, cabeça, cauda); o índice é o do grupo de vértices
        self.tracks = {}
        self.rnd = random.Random(11)
        self.end = 1.0

    # ---- peças ----------------------------------------------------------------------------------------
    def begin(self, name, head=(0, 0, 0), tail=None):
        """Abre a peça `name`: tudo que for desenhado a seguir pesa 1 neste osso, que gira em torno de `head`."""
        head = Vector(head)
        self.bones.append((name, head, Vector(tail) if tail is not None else head + Vector((0, 0, 0.2))))
        self.obj.vertex_groups.new(name=name)
        self.bone = len(self.bones) - 1
        return name

    def paint(self, faces, low, high, z0=0.0, z1=1.0, along=None):
        """Cor por canto: gradiente `low` -> `high` (por altura, ou por `along(co)` em 0..1) vezes a luz falsa."""
        span = max(z1 - z0, 1e-6)
        for f in faces:
            f.normal_update()
            for loop in f.loops:
                t = along(loop.vert.co) if along else (loop.vert.co.z - z0) / span
                loop[self.layer] = (*(low.lerp(high, min(1.0, max(0.0, t))) * shade(f.normal)), 1.0)
                loop.vert[self.groups][self.bone] = 1.0

    def revolve(self, profile, low, high, at=(0, 0, 0), sides=6, yaw=0.0, pitch=0.0, jitter=0.0, flat=False):
        """Sólido de revolução em torno de Z: `profile` = [(raio, z), ...] fechado pelo último ao primeiro.
        Raio 0 vira um vértice só (ponta). Cone, disco, anel, cilindro e bolha saem daqui. `pitch` inclina a
        peça (rad, em Y) e `yaw` gira em Z; `jitter` entorta os vértices (rocha, fumaça); `flat` pinta por raio.
        A cor sobe de `low` (z mínimo) a `high` (z máximo) da peça, ou do eixo à borda quando `flat`."""
        rot = Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(pitch, 4, "Y")
        at = Vector(at)
        rings = []
        for r, z in profile:
            if r < 1e-6:
                rings.append([self.bm.verts.new(at + rot @ Vector((0, 0, z)))])
                continue
            ring = []
            for i in range(sides):
                a = i * 2 * math.pi / sides
                k = 1.0 + self.rnd.uniform(-jitter, jitter)
                ring.append(self.bm.verts.new(at + rot @ Vector((math.cos(a) * r * k, math.sin(a) * r * k, z))))
            rings.append(ring)
        faces = []
        for a, b in zip(rings, rings[1:] + rings[:1]):
            for i in range(sides):
                j = (i + 1) % sides
                quad = [a[i], a[j], b[j], b[i]] if len(a) > 1 and len(b) > 1 else None
                if quad:
                    faces.append(self.bm.faces.new(quad))
                elif len(a) == 1 and len(b) > 1:
                    faces.append(self.bm.faces.new((a[0], b[j], b[i])))
                elif len(b) == 1 and len(a) > 1:
                    faces.append(self.bm.faces.new((a[i], a[j], b[0])))
        bmesh.ops.recalc_face_normals(self.bm, faces=faces)
        zs = [v.co.z for f in faces for v in f.verts]
        rmax = max(r for r, _ in profile) or 1.0
        along = (lambda co: math.hypot(co.x - at.x, co.y - at.y) / rmax) if flat else None
        self.paint(faces, low, high, min(zs), max(zs), along)
        return faces

    def star(self, tips, r_out, r_in, thick, low, high, at=(0, 0, 0), yaw=0.0):
        """Estrela chata de `tips` pontas, espessura `thick` (a cor vai do centro `low` às pontas `high`)."""
        at = Vector(at)
        ring = []
        for i in range(tips * 2):
            a = yaw + i * math.pi / tips
            r = r_out if i % 2 == 0 else r_in
            ring.append(Vector((math.cos(a) * r, math.sin(a) * r, 0.0)))
        top = [self.bm.verts.new(at + p + Vector((0, 0, thick / 2))) for p in ring]
        bot = [self.bm.verts.new(at + p - Vector((0, 0, thick / 2))) for p in ring]
        hub_t = self.bm.verts.new(at + Vector((0, 0, thick / 2)))
        hub_b = self.bm.verts.new(at - Vector((0, 0, thick / 2)))
        faces = []
        n = len(ring)
        for i in range(n):
            j = (i + 1) % n
            faces.append(self.bm.faces.new((hub_t, top[i], top[j])))
            faces.append(self.bm.faces.new((hub_b, bot[j], bot[i])))
            faces.append(self.bm.faces.new((top[i], bot[i], bot[j], top[j])))
        bmesh.ops.recalc_face_normals(self.bm, faces=faces)
        self.paint(faces, low, high, along=lambda co: math.hypot(co.x - at.x, co.y - at.y) / r_out)
        return faces

    def box(self, size, low, high, at=(0, 0, 0), yaw=0.0):
        """Caixa (sx, sy, sz) centrada em `at`, girada `yaw` em Z; a cor sobe de `low` a `high` pela altura."""
        at = Vector(at)
        matrix = Matrix.Translation(at) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Diagonal((*size, 1.0))
        res = bmesh.ops.create_cube(self.bm, size=1.0, matrix=matrix)
        faces = list({f for v in res["verts"] for f in v.link_faces})
        self.paint(faces, low, high, at.z - size[2] / 2, at.z + size[2] / 2)
        return faces

    def bar(self, p0, p1, width, thick, low, high, z=0.0):
        """Barra chata de `p0` a `p1` (XY), largura `width`, espessura `thick`: traço de runa, rachadura."""
        p0, p1 = Vector(p0), Vector(p1)
        mid, d = (p0 + p1) / 2, p1 - p0
        return self.box((d.length, width, thick), low, high, at=(mid.x, mid.y, z + thick / 2), yaw=math.atan2(d.y, d.x))

    # ---- animação -------------------------------------------------------------------------------------
    def anim(self, name, keys):
        """Chaves (segundos, h[, v[, spin]]) do osso `name`; v = h se omitido. Interpolação linear."""
        self.tracks[name] = keys
        self.end = max(self.end, keys[-1][0])

    def _key(self, bone, frame, h, v, spin):
        bone.scale = (h, v, h)
        bone.keyframe_insert("scale", frame=frame)
        if spin is not None:
            bone.rotation_euler = (0.0, spin, 0.0)
            bone.keyframe_insert("rotation_euler", frame=frame)

    def _animate(self, arm):
        bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"  # o raylib amostra a reta
        arm.animation_data_create().action = bpy.data.actions.new("play")
        for name, keys in self.tracks.items():
            bone = arm.pose.bones[name]
            for key in keys:
                t, h = key[0], key[1]
                v = key[2] if len(key) > 2 and key[2] is not None else h
                spin = key[3] if len(key) > 3 else None
                self._key(bone, sec(t), max(h, TINY), max(v, TINY), spin)
        bpy.context.scene.render.fps = FPS
        bpy.context.scene.frame_start, bpy.context.scene.frame_end = 0, sec(self.end)

    # ---- saída ----------------------------------------------------------------------------------------
    def export(self):
        self.bm.to_mesh(self.mesh)
        self.bm.free()
        self.mesh.color_attributes.active_color = self.mesh.color_attributes["Col"]
        arm_data = bpy.data.armatures.new("rig")
        arm = bpy.data.objects.new("rig", arm_data)
        bpy.context.scene.collection.objects.link(arm)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode="EDIT")
        for name, head, tail in self.bones:
            bone = arm_data.edit_bones.new(name)
            bone.head, bone.tail = head, tail
        bpy.ops.object.mode_set(mode="POSE")
        self._animate(arm)
        bpy.ops.object.mode_set(mode="OBJECT")
        self.obj.parent = arm
        self.obj.modifiers.new("Armature", "ARMATURE").object = arm
        path = OUT_DIR / f"{self.name}.glb"
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", export_yup=True,
                                  export_animations=True, export_animation_mode="ACTIONS",
                                  export_apply=False, export_skins=True, export_morph=False,
                                  export_vertex_color="ACTIVE", export_active_vertex_color_when_no_material=True,
                                  export_materials="NONE")
        print(f"fx_{self.name}:", path, path.stat().st_size, "bytes", file=sys.stderr)


def blob(radius, height=None):
    """Perfil de bolha (elipsoide de 5 anéis) para `Fx.revolve`; `height` = semieixo vertical."""
    h = radius if height is None else height
    return [(0, -h), (radius * 0.75, -h * 0.65), (radius, 0), (radius * 0.75, h * 0.65), (0, h)]


def annulus(inner, outer, thick, z=0.0):
    """Perfil de anel chato (coroa entre dois raios) para `Fx.revolve`."""
    return [(inner, z), (outer, z), (outer, z + thick), (inner, z + thick)]


def disc(radius, z=0.0, thick=0.03):
    """Perfil de disco chato de `radius` com a face de baixo em `z`."""
    return [(0, z), (radius, z), (radius, z + thick), (0, z + thick)]


def cone(radius, height):
    return [(0, 0), (radius, 0), (0, height)]
