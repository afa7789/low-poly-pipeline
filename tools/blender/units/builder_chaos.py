"""Chaos Imp Builder (builder_chaos): medido em artifacts/model-sheets/refs/builder_chaos/sheet.jpg (familia biped).

    blender -b --factory-startup -P tools/blender/units/builder_chaos.py -- <out.glb>

Escala da prancha: 0.00323 m por pixel (pontas dos chifres a 2.5 m, pes a 0); frente = esquerda no perfil.
Mao direita (x -) segura o cabo no ombro: roda de valvula na frente, ancinho atras do ombro esquerdo.
"""
import pathlib
import sys

from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "red": 0xC00F1E, "red_dk": 0x8E0B16, "black": 0x15110F, "apron": 0x6A6465, "helm": 0x4A4547,
    "horn": 0x3C383A, "iron": 0x2E2A2C, "eye": 0xE8E0D8, "claw": 0x3A0A0E, "cross": 0xD01426,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X = 0.84, 0.46, 0.17, 0.28, 0.34
WAIST, NECK, TOP = 1.05, 1.76, 2.52
WHEEL, RAKE = Vector((-1.02, 1.68, 0.8)), Vector((0.62, 2.45, -0.85))


def head():
    """Elmo de ferro com mascara, olhos em fenda e dois chifres curvos."""
    H.frustum("head", "helm", (0, 1.74, 0.1), (0, 1.97, 0.08), (0.15, 0.15), (0.22, 0.23), sides=8)
    H.frustum("head", "helm", (0, 1.95, 0.08), (0, 2.22, 0.06), (0.23, 0.23), (0.19, 0.2), sides=8)
    H.frustum("head", "helm", (0, 2.2, 0.06), (0, 2.32, 0.04), (0.19, 0.2), (0.08, 0.09), sides=8)
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.09, 2.04, 0.3), (0.1, 0.04, 0.03))
        H.chain("head", "horn", [(s * 0.17, 2.18, 0.05), (s * 0.28, 2.3, 0.04), (s * 0.31, 2.52, 0.0)],
                [(0.08, 0.08), (0.06, 0.06), (0.01, 0.01)], sides=6)
    H.frustum("head", "iron", (0, 1.62, 0.02), (0, 1.84, 0.02), (0.3, 0.28), (0.27, 0.25), sides=8)   # gola


def torso():
    """Barril largo com avental de ferro na frente, cruz invertida e alcas."""
    H.frustum("spine", "black", (0, WAIST - 0.05, 0.04), (0, 1.4, 0.04), (0.4, 0.4), (0.47, 0.44), sides=8)
    H.frustum("spine", "black", (0, 1.4, 0.04), (0, 1.66, 0.02), (0.47, 0.42), (0.55, 0.38), sides=8)
    H.frustum("spine", "black", (0, 1.66, 0.02), (0, 1.8, 0.0), (0.55, 0.38), (0.3, 0.28), sides=8)
    H.frustum("spine", "apron", (0, WAIST, 0.4), (0, 1.74, 0.4), (0.36, 0.07), (0.28, 0.06), sides=4)
    H.frustum("spine", "cross", (0, 1.2, 0.47), (0, 1.58, 0.47), (0.035, 0.03), (0.035, 0.03), sides=4)
    H.frustum("spine", "cross", (-0.11, 1.5, 0.47), (0.11, 1.5, 0.47), (0.03, 0.03), (0.03, 0.03), sides=4)
    for s in (-1, 1):
        H.frustum("spine", "apron", (s * 0.22, 1.5, 0.43), (s * 0.2, 1.84, 0.1), (0.05, 0.04), (0.05, 0.05), sides=4)
        H.frustum("spine", "apron", (s * 0.22, 1.76, -0.3), (s * 0.2, 1.4, -0.36), (0.05, 0.04), (0.05, 0.05), sides=4)


def hem(p):
    """Saia do avental: o topo fica na pelve, a barra acompanha a coxa do seu lado."""
    if p[1] > 0.85:
        return {"pelvis": 1.0}
    return {"pelvis": 0.4, "thigh.L" if p[0] > 0 else "thigh.R": 0.6}


def legs():
    H.frustum("pelvis", "black", (0, 0.66, 0.0), (0, HIP + 0.24, 0.0), (0.4, 0.34), (0.46, 0.38), sides=8)
    skirt = H.frustum("pelvis", "apron", (0, 0.58, 0.36), (0, 1.08, 0.38), (0.3, 0.04), (0.36, 0.05), sides=4)
    H.soft(skirt, hem)
    for s, side in ((1, "L"), (-1, "R")):
        H.frustum(f"thigh.{side}", "black", (s * KNEE_X, KNEE - 0.03, 0), (s * LEG_X, HIP + 0.1, 0), (0.22, 0.22), (0.27, 0.27), sides=6)
        H.frustum(f"shin.{side}", "black", (s * KNEE_X, 0.2, 0), (s * KNEE_X, KNEE + 0.02, 0), (0.2, 0.21), (0.24, 0.24), sides=6)
        H.frustum(f"shin.{side}", "red_dk", (s * KNEE_X, 0.12, 0), (s * KNEE_X, 0.24, 0), (0.17, 0.17), (0.2, 0.2), sides=6)
        H.frustum(f"foot.{side}", "red", (s * KNEE_X, 0.08, -0.1), (s * KNEE_X, 0.07, 0.4), (0.2, 0.12), (0.19, 0.07), sides=6)
        H.frustum(f"foot.{side}", "red", (s * KNEE_X, 0.2, -0.04), (s * KNEE_X, 0.1, 0.1), (0.17, 0.16), (0.19, 0.12), sides=6)
        for dx in (-0.1, 0.0, 0.1):
            H.frustum(f"foot.{side}", "claw", (s * KNEE_X + dx, 0.06, 0.38), (s * KNEE_X + dx * 1.2, 0.03, 0.58), (0.04, 0.03), (0.01, 0.01), sides=4)


def left_arm():
    """Braco pendurado: manga curta preta, biceps vermelho grosso, antebraco pesado e punho grande."""
    H.frustum("arm.L", "black", (0.46, 1.8, 0.0), (0.64, 1.52, 0.0), (0.24, 0.22), (0.3, 0.27), sides=8)
    H.frustum("arm.L", "red", (0.62, 1.56, 0.0), (0.66, 1.2, 0.02), (0.25, 0.23), (0.19, 0.19), sides=8)
    H.frustum("forearm.L", "red", (0.72, 1.24, 0.04), (0.74, 0.98, 0.06), (0.19, 0.19), (0.23, 0.22), sides=8)
    H.frustum("forearm.L", "red", (0.74, 1.0, 0.06), (0.74, 0.8, 0.08), (0.22, 0.21), (0.2, 0.19), sides=8)
    H.frustum("forearm.L", "red_dk", (0.74, 0.8, 0.08), (0.74, 0.64, 0.1), (0.2, 0.19), (0.14, 0.13), sides=6)


def right_arm():
    """Braco direito dobrado pra cima: a mao fecha no cabo da ferramenta que descansa no ombro."""
    H.frustum("arm.R", "black", (-0.46, 1.8, 0.0), (-0.66, 1.56, 0.0), (0.24, 0.22), (0.3, 0.27), sides=8)
    H.frustum("arm.R", "red", (-0.62, 1.6, 0.02), (-0.82, 1.36, 0.1), (0.24, 0.22), (0.2, 0.19), sides=8)
    H.frustum("forearm.R", "red", (-0.82, 1.38, 0.1), (-0.74, 1.62, 0.3), (0.2, 0.19), (0.23, 0.22), sides=8)
    H.frustum("forearm.R", "red", (-0.74, 1.62, 0.3), (-0.69, 1.78, 0.45), (0.22, 0.21), (0.2, 0.19), sides=8)
    H.frustum("forearm.R", "red_dk", (-0.7, 1.74, 0.43), (-0.68, 1.9, 0.5), (0.17, 0.16), (0.15, 0.14), sides=6)


def tool():
    """Cabo longo atravessando o ombro: roda de valvula na frente, ancinho de quatro dentes atras."""
    d = (RAKE - WHEEL).normalized()
    H.chain("forearm.R", "iron", [WHEEL, WHEEL + d * 1.2, RAKE - d * 0.1], [(0.05, 0.05)] * 3, sides=6)
    H.frustum("forearm.R", "helm", WHEEL - d * 0.03, WHEEL + d * 0.03, (0.17, 0.17), (0.17, 0.17), sides=8)
    H.frustum("forearm.R", "iron", WHEEL - d * 0.05, WHEEL + d * 0.07, (0.07, 0.07), (0.07, 0.07), sides=6)
    bar_a, bar_b = Vector((0.36, 2.5, -0.8)), Vector((0.9, 2.42, -0.92))
    H.frustum("forearm.R", "iron", bar_a, bar_b, (0.06, 0.06), (0.06, 0.06), sides=4)
    for t in (0.0, 0.33, 0.66, 1.0):
        top = bar_a.lerp(bar_b, t)
        H.frustum("forearm.R", "iron", top, top + Vector((0.08, -0.34, 0.1)), (0.04, 0.04), (0.012, 0.012), sides=4)


def make():
    head()
    torso()
    legs()
    left_arm()
    right_arm()
    tool()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0)),
           "arm.L": ((0.5, 1.74, 0), (0.5, 1.2, 0)), "forearm.L": ((0.72, 1.24, 0.04), (0.72, 0.7, 0.04)),
           "arm.R": ((-0.5, 1.74, 0), (-0.5, 1.2, 0)), "forearm.R": ((-0.82, 1.38, 0.1), (-0.82, 0.85, 0.1))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * KNEE_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * KNEE_X, ANKLE, 0), (s * KNEE_X, 0.06, 0.5))
    return out


H.build("builder_chaos", "biped", PALETTE, make, joints())
