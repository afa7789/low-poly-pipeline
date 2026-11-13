"""Corrupted Thrall Builder (builder_corrupted): medido em artifacts/model-sheets/refs/builder_corrupted/sheet.jpg (familia wraith).

    blender -b --factory-startup -P tools/blender/units/builder_corrupted.py -- <out.glb>

Escala da prancha: 0.00314 m por pixel (capuz a 2.42 m, pontas da barra a 0); frente = esquerda no perfil.
Mao direita (x -) leva a lanterna, mao esquerda (x +) leva o cajado.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "robe": 0x544C31, "robe_dk": 0x3C3622, "robe_lt": 0x6A6040, "void": 0x16120F, "staff": 0x2A221A,
    "eye": 0x4DFF2A, "iron": 0x1E1814, "flame": 0x66F53B,
}


def hood():
    """Capuz alto com ponta pra tras e rosto escuro com dois olhos verdes."""
    H.frustum("head", "robe", (0, 1.7, 0.0), (0, 1.98, 0.04), (0.4, 0.34), (0.32, 0.32), sides=8)
    H.frustum("head", "robe", (0, 1.96, 0.04), (0, 2.26, 0.0), (0.32, 0.32), (0.22, 0.24), sides=8)
    H.frustum("head", "robe", (0, 2.22, 0.0), (0, 2.42, -0.06), (0.22, 0.24), (0.08, 0.1), sides=6)
    H.frustum("head", "robe_dk", (0, 2.3, -0.08), (0, 2.22, -0.38), (0.12, 0.12), (0.02, 0.02), sides=4)
    for s in (-1, 1):
        H.frustum("head", "robe_lt", (s * 0.28, 1.98, 0.12), (s * 0.22, 2.22, 0.1), (0.07, 0.2), (0.05, 0.16), sides=6)
    H.frustum("head", "void", (0, 1.86, 0.24), (0, 2.3, 0.22), (0.21, 0.1), (0.17, 0.09), sides=6)
    for s in (-1, 1):
        H.frustum("head", "eye", (s * 0.1, 2.02, 0.31), (s * 0.1, 2.14, 0.31), (0.05, 0.03), (0.05, 0.03), sides=6)


def torso():
    """Capa de ombros rasgada, peito em V e cintura estreita."""
    H.frustum("spine", "robe_lt", (0, 1.88, 0.0), (0, 1.66, 0.0), (0.38, 0.32), (0.58, 0.42), sides=8)
    H.frustum("spine", "robe", (0, 1.7, 0.0), (0, 1.3, 0.0), (0.5, 0.34), (0.42, 0.3), sides=8)
    H.frustum("spine", "robe", (0, 1.34, 0.0), (0, 0.98, 0.0), (0.42, 0.3), (0.34, 0.26), sides=8)
    H.frustum("spine", "robe_dk", (0, 1.62, 0.28), (0, 1.0, 0.27), (0.07, 0.04), (0.1, 0.04), sides=4)
    for s in (-1, 1):
        H.frustum("spine", "robe_lt", (s * 0.5, 1.72, -0.02), (s * 0.62, 1.58, 0.0), (0.1, 0.3), (0.06, 0.34), sides=4)


def hem():
    """Barra: saia que alarga, tiras rasgadas pra baixo na frente e arrastadas pra tras."""
    H.frustum("base", "robe", (0, 1.05, 0.0), (0, 0.7, 0.0), (0.34, 0.26), (0.42, 0.3), sides=8)
    H.frustum("base", "robe", (0, 0.72, 0.0), (0, 0.4, -0.04), (0.46, 0.3), (0.56, 0.34), sides=8)
    for x, ln in ((-0.5, 0.1), (-0.34, 0.0), (-0.17, 0.08), (0.0, 0.02), (0.17, 0.1), (0.34, 0.0), (0.5, 0.12)):
        H.chain("base", "robe_dk", [(x, 0.5, 0.1), (x * 1.05, 0.28, 0.07), (x * 1.1, ln, 0.0)],
                [(0.1, 0.08), (0.08, 0.06), (0.015, 0.015)], sides=4)
    for x, z in ((-0.3, 0.9), (0.0, 0.7), (0.3, 0.85)):
        H.chain("base", "robe", [(x, 0.55, -0.2), (x * 1.1, 0.34, -0.45 * z), (x * 1.2, 0.16, -0.85 * z)],
                [(0.14, 0.1), (0.1, 0.07), (0.015, 0.015)], sides=4)


def lantern_arm():
    """Braco direito (x -): manga larga, antebraco pra frente e a lanterna pendurada."""
    arm, fore = "arm.R", "forearm.R"
    H.frustum(arm, "robe", (-0.5, 1.72, 0.0), (-0.6, 1.46, 0.1), (0.17, 0.18), (0.2, 0.19), sides=8)
    H.frustum(arm, "robe", (-0.6, 1.5, 0.1), (-0.68, 1.22, 0.24), (0.2, 0.19), (0.17, 0.16), sides=8)
    H.frustum(fore, "robe", (-0.68, 1.24, 0.22), (-0.68, 1.1, 0.42), (0.15, 0.15), (0.21, 0.2), sides=8)
    H.frustum(fore, "robe_lt", (-0.68, 1.12, 0.42), (-0.68, 1.04, 0.54), (0.2, 0.19), (0.12, 0.12), sides=6)
    H.frustum(fore, "iron", (-0.68, 1.02, 0.58), (-0.68, 0.94, 0.58), (0.05, 0.03), (0.07, 0.03), sides=4)
    H.frustum(fore, "iron", (-0.68, 0.92, 0.58), (-0.68, 0.84, 0.58), (0.2, 0.2), (0.14, 0.14), sides=6)
    H.frustum(fore, "flame", (-0.68, 0.84, 0.58), (-0.68, 0.48, 0.58), (0.15, 0.15), (0.17, 0.17), sides=6)
    H.frustum(fore, "iron", (-0.68, 0.48, 0.58), (-0.68, 0.3, 0.58), (0.2, 0.2), (0.03, 0.03), sides=6)
    for s in (-1, 1):
        H.frustum(fore, "iron", (-0.68 + s * 0.16, 0.84, 0.58), (-0.68 + s * 0.16, 0.48, 0.58), (0.025, 0.2), (0.025, 0.2), sides=4)


def staff_arm():
    """Braco esquerdo (x +): mao fechada no cajado alto de gancho."""
    arm, fore = "arm.L", "forearm.L"
    H.frustum(arm, "robe", (0.5, 1.72, 0.0), (0.56, 1.46, 0.04), (0.17, 0.18), (0.2, 0.19), sides=8)
    H.frustum(arm, "robe", (0.56, 1.5, 0.04), (0.6, 1.2, 0.1), (0.2, 0.19), (0.17, 0.16), sides=8)
    H.frustum(fore, "robe", (0.6, 1.22, 0.1), (0.72, 1.3, 0.28), (0.15, 0.15), (0.21, 0.2), sides=8)
    H.frustum(fore, "robe_lt", (0.72, 1.3, 0.28), (0.76, 1.34, 0.32), (0.2, 0.19), (0.17, 0.17), sides=8)
    H.frustum(fore, "robe", (0.76, 1.34, 0.32), (0.76, 1.46, 0.32), (0.15, 0.15), (0.17, 0.17), sides=6)
    pts = [(0.76, 0.02, 0.32), (0.77, 0.9, 0.32), (0.75, 1.7, 0.32), (0.78, 2.15, 0.32), (0.72, 2.4, 0.32),
           (0.56, 2.44, 0.32), (0.44, 2.32, 0.32), (0.43, 2.18, 0.32)]
    H.chain(fore, "staff", pts, [(0.045, 0.045)] * 5 + [(0.04, 0.04), (0.035, 0.035), (0.02, 0.02)], sides=6)


def make():
    hood()
    torso()
    hem()
    lantern_arm()
    staff_arm()


def joints():
    """Bracos na vertical (direcao de repouso da familia); cotovelo/ombro nas posicoes da prancha."""
    return {
        "arm.R": ((-0.5, 1.72, 0.0), (-0.5, 1.22, 0.0)),
        "forearm.R": ((-0.68, 1.22, 0.24), (-0.68, 0.7, 0.24)),
        "arm.L": ((0.5, 1.72, 0.0), (0.5, 1.2, 0.0)),
        "forearm.L": ((0.6, 1.2, 0.1), (0.6, 0.7, 0.1)),
    }


H.build("builder_corrupted", "wraith", PALETTE, make, joints())
