"""Elemental Golem Builder (builder_elemental): medido em artifacts/model-sheets/refs/builder_elemental/sheet.jpg (familia biped).

    blender -b --factory-startup -P tools/blender/units/builder_elemental.py -- <out.glb>

Escala da prancha: 0.00284 m por pixel (topo da cabeca a 2.0 m, pes a 0); frente = esquerda no perfil.
Mao direita (x -) leva a picareta, mao esquerda (x +) a laje de pedra em pe.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "clay": 0xB07A5E, "clay_dk": 0x8A5A44, "clay_leg": 0x9A6A50, "stone": 0x9A8E7A, "stone_dk": 0x7A7062,
    "glow": 0xFFA81E, "wood": 0x6B4A32, "pick": 0x8A8272, "spark": 0xA8E4F8,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X = 0.58, 0.36, 0.14, 0.3, 0.4
WAIST, NECK, TOP = 0.8, 1.5, 2.02


def head():
    """Pedregulho redondo sobre o corpo, com faiscas azuis nos ombros."""
    H.frustum("head", "stone", (0, 1.44, 0.08), (0, 1.7, 0.1), (0.22, 0.2), (0.31, 0.3), sides=8)
    H.frustum("head", "stone", (0, 1.7, 0.1), (0, 1.84, 0.1), (0.31, 0.3), (0.31, 0.3), sides=8)
    H.frustum("head", "stone", (0, 1.84, 0.1), (0, 2.02, 0.1), (0.31, 0.3), (0.2, 0.2), sides=8)
    H.frustum("head", "stone_dk", (0, 1.45, 0.08), (0, 1.6, 0.08), (0.2, 0.19), (0.27, 0.25), sides=8)
    for s in (-1, 1):
        H.chain("head", "spark", [(s * 0.34, 1.58, 0.1), (s * 0.4, 1.66, 0.1), (s * 0.44, 1.6, 0.1)], [(0.025, 0.025)] * 3, sides=4)


def torso():
    """Barriga de barro em esfera, com a rachadura de brasa em cruz na frente."""
    H.frustum("spine", "clay", (0, 0.48, 0.0), (0, 0.7, 0.0), (0.3, 0.27), (0.46, 0.41), sides=8)
    H.frustum("spine", "clay", (0, 0.68, 0.0), (0, 1.0, 0.0), (0.46, 0.41), (0.54, 0.46), sides=8)
    H.frustum("spine", "clay", (0, 0.98, 0.0), (0, 1.3, 0.0), (0.54, 0.46), (0.5, 0.44), sides=8)
    H.frustum("spine", "clay", (0, 1.28, 0.0), (0, 1.54, 0.0), (0.5, 0.44), (0.28, 0.25), sides=8)
    H.frustum("spine", "glow", (0, 0.62, 0.42), (0, 1.38, 0.4), (0.025, 0.03), (0.025, 0.03), sides=4)
    H.chain("spine", "glow", [(-0.46, 0.95, 0.05), (-0.3, 0.95, 0.32), (0, 0.95, 0.43), (0.3, 0.95, 0.32), (0.46, 0.95, 0.05)],
            [(0.03, 0.03)] * 5, sides=4)
    H.box("spine", "glow", (0, 0.97, 0.44), (0.13, 0.13, 0.05))


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        kx = s * KNEE_X
        H.frustum(f"thigh.{side}", "clay_leg", (kx, KNEE - 0.02, 0), (s * LEG_X, HIP + 0.06, 0), (0.23, 0.22), (0.3, 0.27), sides=6)
        H.frustum(f"shin.{side}", "clay_leg", (kx, 0.1, 0), (kx, KNEE + 0.02, 0), (0.18, 0.18), (0.21, 0.2), sides=6)
        H.frustum(f"shin.{side}", "stone", (kx, 0.31, 0.12), (kx, 0.43, 0.14), (0.1, 0.1), (0.07, 0.07), sides=6)
        H.frustum(f"foot.{side}", "stone", (kx, 0.07, -0.18), (kx, 0.1, 0.26), (0.23, 0.14), (0.22, 0.1), sides=6)
        H.frustum(f"foot.{side}", "stone_dk", (kx, 0.0, -0.2), (kx, 0.03, 0.27), (0.25, 0.16), (0.24, 0.12), sides=6)


def pick_arm():
    """Direito (x -): ombro de pedra, braco grosso, punho no cabo da picareta virada pra frente."""
    H.frustum("arm.R", "stone", (-0.55, 1.2, 0.0), (-0.55, 1.4, 0.0), (0.17, 0.17), (0.27, 0.25), sides=8)
    H.frustum("arm.R", "stone", (-0.55, 1.38, 0.0), (-0.52, 1.6, 0.0), (0.27, 0.25), (0.15, 0.14), sides=8)
    H.frustum("arm.R", "clay", (-0.52, 1.4, 0.0), (-0.72, 1.0, 0.05), (0.19, 0.19), (0.22, 0.21), sides=8)
    H.frustum("forearm.R", "clay", (-0.72, 1.0, 0.05), (-0.7, 0.72, 0.3), (0.21, 0.2), (0.17, 0.16), sides=8)
    H.frustum("forearm.R", "clay_dk", (-0.7, 0.8, 0.28), (-0.7, 0.56, 0.32), (0.18, 0.18), (0.2, 0.18), sides=8)
    H.frustum("forearm.R", "wood", (-0.5, 0.68, 0.34), (-1.06, 0.7, 0.34), (0.045, 0.045), (0.055, 0.055), sides=6)
    H.chain("forearm.R", "pick", [(-0.95, 1.12, 0.34), (-0.99, 0.82, 0.34), (-0.98, 0.56, 0.34), (-0.9, 0.2, 0.34)],
            [(0.015, 0.03), (0.05, 0.17), (0.05, 0.16), (0.012, 0.03)], sides=4)


def slab_arm():
    """Esquerdo (x +): ombro de pedra, braco, punho fechado segurando a laje em pe."""
    H.frustum("arm.L", "stone", (0.55, 1.2, 0.0), (0.55, 1.4, 0.0), (0.17, 0.17), (0.27, 0.25), sides=8)
    H.frustum("arm.L", "stone", (0.55, 1.38, 0.0), (0.52, 1.6, 0.0), (0.27, 0.25), (0.15, 0.14), sides=8)
    H.frustum("arm.L", "clay", (0.52, 1.4, 0.0), (0.72, 1.06, 0.06), (0.19, 0.19), (0.22, 0.21), sides=8)
    H.frustum("forearm.L", "clay", (0.72, 1.06, 0.06), (0.7, 0.94, 0.2), (0.21, 0.2), (0.19, 0.18), sides=8)
    H.frustum("forearm.L", "clay_dk", (0.7, 0.84, 0.2), (0.68, 1.06, 0.2), (0.2, 0.19), (0.18, 0.17), sides=8)
    H.frustum("forearm.L", "stone", (0.66, 1.0, 0.18), (0.62, 2.0, 0.1), (0.17, 0.14), (0.13, 0.09), sides=4)
    H.frustum("forearm.L", "stone_dk", (0.52, 1.1, 0.12), (0.5, 1.98, 0.04), (0.06, 0.12), (0.02, 0.06), sides=4)


def make():
    head()
    torso()
    legs()
    pick_arm()
    slab_arm()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0.08), (0, TOP, 0.08)),
           "arm.L": ((0.55, 1.4, 0), (0.55, 1.05, 0)), "forearm.L": ((0.72, 1.06, 0.06), (0.72, 0.6, 0.06)),
           "arm.R": ((-0.55, 1.4, 0), (-0.55, 1.0, 0)), "forearm.R": ((-0.72, 1.0, 0.05), (-0.72, 0.55, 0.05))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * KNEE_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * KNEE_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * KNEE_X, ANKLE, 0), (s * KNEE_X, 0.06, 0.4))
    return out


H.build("builder_elemental", "biped", PALETTE, make, joints())
