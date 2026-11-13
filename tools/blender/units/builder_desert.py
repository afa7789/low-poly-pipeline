"""Desert Cactoro Builder (builder_desert): medido em artifacts/model-sheets/refs/builder_desert/sheet.jpg (familia biped).

    blender -b --factory-startup -P tools/blender/units/builder_desert.py -- <out.glb>

Escala da prancha: 0.00272 m por pixel (ponta da chama a 2.3 m, pes a 0); frente = esquerda no perfil.
Toupeira corcunda de focinho comprido: picareta de duas pontas nas duas maos, outra picareta nas costas.
"""
import pathlib
import sys

from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "skin": 0xCDAA6E, "skin_dk": 0xAA8A55, "cloak": 0x6A4A30, "cloak_dk": 0x56391F, "pants": 0x4A4543,
    "bracer": 0x3F3B3A, "rope": 0x7A5C3A, "barrel": 0x9A7A4E, "wood": 0x5A3A22, "iron": 0x3A3B3F,
    "turban": 0xCBAD76, "cap": 0x3A3A3C, "flame": 0xFF9A1E, "flame_hi": 0xFFC94A, "wax": 0xE8DDB8,
    "lens": 0xB8AA84, "nose": 0x6A4A38, "brass": 0x8A6A3A,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X = 0.76, 0.4, 0.15, 0.2, 0.24
WAIST, NECK, TOP = 0.96, 1.45, 2.0
SHAFT_A, SHAFT_B = Vector((-0.95, 0.62, 0.55)), Vector((0.95, 1.3, 0.55))
BACK_A, BACK_B = Vector((0.62, 1.38, -0.46)), Vector((-0.82, 0.72, -0.5))


def head():
    """Turbante com tampa escura, vela acesa, oculos e focinho comprido pra frente."""
    H.frustum("head", "turban", (0, 1.5, 0.42), (0, 1.68, 0.42), (0.2, 0.2), (0.3, 0.27), sides=8)
    H.frustum("head", "turban", (0, 1.66, 0.42), (0, 1.85, 0.4), (0.3, 0.27), (0.25, 0.23), sides=8)
    H.frustum("head", "cap", (0, 1.83, 0.4), (0, 1.97, 0.4), (0.22, 0.2), (0.14, 0.13), sides=8)
    H.frustum("head", "brass", (0, 1.96, 0.4), (0, 2.06, 0.4), (0.11, 0.11), (0.13, 0.13), sides=6)
    H.frustum("head", "wax", (0, 2.06, 0.4), (0, 2.15, 0.4), (0.04, 0.04), (0.035, 0.035), sides=6)
    H.chain("head", "flame", [(0, 2.14, 0.4), (0, 2.22, 0.4), (0.02, 2.34, 0.4)], [(0.07, 0.07), (0.06, 0.06), (0.005, 0.005)], sides=6)
    H.chain("head", "skin", [(0, 1.62, 0.44), (0, 1.55, 0.7), (0, 1.4, 1.0)], [(0.22, 0.2), (0.16, 0.14), (0.05, 0.05)], sides=6)
    H.frustum("head", "nose", (0, 1.39, 0.98), (0, 1.37, 1.06), (0.055, 0.055), (0.035, 0.035), sides=6)
    H.chain("head", "skin_dk", [(0, 1.3, 0.4), (0, 1.42, 0.3), (0, 1.52, 0.4)], [(0.17, 0.17), (0.2, 0.2), (0.2, 0.2)], sides=6)
    for s in (-1, 1):
        H.frustum("head", "brass", (s * 0.13, 1.66, 0.62), (s * 0.13, 1.66, 0.72), (0.1, 0.1), (0.1, 0.1), sides=8)
        H.frustum("head", "lens", (s * 0.13, 1.66, 0.7), (s * 0.13, 1.66, 0.74), (0.07, 0.07), (0.07, 0.07), sides=8)


def torso():
    """Corpo curvado pra frente: barriga, peito de colete, capa rasgada nas costas, corda na cintura."""
    H.frustum("spine", "skin_dk", (0, WAIST - 0.1, 0.06), (0, 1.22, 0.1), (0.36, 0.3), (0.4, 0.34), sides=8)
    H.frustum("spine", "cloak_dk", (0, 1.2, 0.1), (0, 1.5, 0.12), (0.4, 0.34), (0.34, 0.28), sides=8)
    H.frustum("spine", "cloak", (0, 1.52, 0.0), (0, 1.3, -0.04), (0.34, 0.3), (0.5, 0.4), sides=8)
    H.frustum("spine", "cloak", (0, 1.4, -0.12), (0, 0.9, -0.46), (0.44, 0.08), (0.5, 0.08), sides=4)
    H.frustum("spine", "rope", (0, 0.9, 0.06), (0, 1.02, 0.06), (0.4, 0.34), (0.4, 0.34), sides=8)
    H.frustum("spine", "rope", (-0.3, 1.4, 0.34), (0.3, 1.08, 0.38), (0.06, 0.04), (0.06, 0.04), sides=4)


def pelvis():
    H.frustum("pelvis", "pants", (0, 0.62, 0.0), (0, HIP + 0.24, 0.02), (0.42, 0.34), (0.44, 0.36), sides=8)
    H.frustum("pelvis", "cloak", (0, 0.46, 0.36), (0, 0.95, 0.36), (0.02, 0.03), (0.22, 0.03), sides=4)
    for x, ln in ((-0.3, 0.55), (-0.1, 0.42), (0.1, 0.5), (0.3, 0.58)):
        H.frustum("pelvis", "cloak_dk", (x, 0.95, -0.36), (x * 1.05, ln, -0.5), (0.1, 0.04), (0.01, 0.02), sides=4)
    H.frustum("pelvis", "barrel", (0.42, 0.8, -0.15), (0.42, 0.8, 0.3), (0.18, 0.18), (0.2, 0.2), sides=8)
    H.frustum("pelvis", "wood", (0.42, 0.8, 0.29), (0.42, 0.8, 0.33), (0.12, 0.12), (0.1, 0.1), sides=8)
    H.frustum("pelvis", "barrel", (0.36, 0.74, -0.2), (0.34, 0.7, -0.55), (0.2, 0.2), (0.24, 0.24), sides=8)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x, kx = s * LEG_X, s * KNEE_X
        H.frustum(f"thigh.{side}", "pants", (kx, KNEE - 0.02, 0.02), (x, HIP + 0.08, 0), (0.22, 0.24), (0.27, 0.28), sides=6)
        H.frustum(f"shin.{side}", "skin", (kx, 0.17, 0.0), (kx, KNEE + 0.02, 0.02), (0.1, 0.1), (0.15, 0.15), sides=6)
        H.frustum(f"shin.{side}", "skin_dk", (kx, 0.14, 0.0), (kx, 0.22, 0.0), (0.1, 0.1), (0.13, 0.13), sides=6)
        H.frustum(f"foot.{side}", "skin", (kx, 0.1, -0.1), (kx, 0.05, 0.42), (0.15, 0.12), (0.17, 0.06), sides=6)
        for dx in (-0.1, -0.035, 0.035, 0.1):
            H.frustum(f"foot.{side}", "skin_dk", (kx + dx, 0.04, 0.4), (kx + dx * 1.5, 0.02, 0.62), (0.03, 0.03), (0.008, 0.008), sides=4)


def arms():
    """Direito (x -): ombro, braco e antebraco com munhequeira escura, mao na haste. Esquerdo (x +) idem, mais alto."""
    H.frustum("arm.R", "skin", (-0.28, 1.4, 0.0), (-0.48, 1.14, 0.1), (0.16, 0.16), (0.22, 0.2), sides=8)
    H.frustum("arm.R", "skin", (-0.48, 1.16, 0.1), (-0.5, 0.95, 0.2), (0.22, 0.2), (0.17, 0.16), sides=8)
    H.frustum("forearm.R", "bracer", (-0.5, 0.97, 0.2), (-0.49, 0.86, 0.38), (0.18, 0.17), (0.17, 0.16), sides=8)
    H.frustum("forearm.R", "skin", (-0.49, 0.8, 0.42), (-0.47, 0.82, 0.6), (0.17, 0.16), (0.15, 0.14), sides=6)
    H.frustum("arm.L", "skin", (0.28, 1.4, 0.0), (0.5, 1.16, 0.08), (0.16, 0.16), (0.22, 0.2), sides=8)
    H.frustum("arm.L", "skin", (0.5, 1.18, 0.08), (0.52, 1.0, 0.15), (0.22, 0.2), (0.17, 0.16), sides=8)
    H.frustum("forearm.L", "bracer", (0.52, 1.02, 0.15), (0.47, 1.1, 0.4), (0.18, 0.17), (0.17, 0.16), sides=8)
    H.frustum("forearm.L", "skin", (0.44, 1.1, 0.44), (0.42, 1.14, 0.62), (0.17, 0.16), (0.15, 0.14), sides=6)


def pick(bone, a, b):
    """Picareta de duas pontas: cabo e duas laminas curvas que abraçam as extremidades."""
    d = (b - a).normalized()
    H.chain(bone, "wood", [a - d * 0.08, a.lerp(b, 0.5), b + d * 0.08], [(0.05, 0.05)] * 3, sides=6)
    for end, s in ((a, -1), (b, 1)):
        pts = [end + Vector((-0.2 * s, 0.34, 0)), end + Vector((-0.06 * s, 0.16, 0)), end,
               end + Vector((0.01 * s, -0.17, 0)), end + Vector((-0.03 * s, -0.3, 0))]
        H.chain(bone, "iron", pts, [(0.012, 0.012), (0.05, 0.05), (0.075, 0.07), (0.05, 0.05), (0.012, 0.012)], sides=4)
        H.frustum(bone, "iron", end - d * 0.05 * s * -1, end + d * 0.05 * s * -1, (0.07, 0.07), (0.07, 0.07), sides=6)


def make():
    head()
    torso()
    pelvis()
    legs()
    arms()
    pick("forearm.R", SHAFT_A, SHAFT_B)
    pick("spine", BACK_A, BACK_B)


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0.3), (0, TOP, 0.3)),
           "arm.L": ((0.3, 1.4, 0), (0.3, 1.0, 0)), "forearm.L": ((0.52, 1.02, 0.15), (0.52, 0.55, 0.15)),
           "arm.R": ((-0.3, 1.4, 0), (-0.3, 0.95, 0)), "forearm.R": ((-0.5, 0.97, 0.2), (-0.5, 0.5, 0.2))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * KNEE_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * KNEE_X, ANKLE, 0), (s * KNEE_X, 0.06, 0.5))
    return out


H.build("builder_desert", "biped", PALETTE, make, joints())
