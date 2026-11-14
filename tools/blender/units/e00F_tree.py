"""Gigante da Montanha com a arvore (e00F_tree): o corpo do e00F mais o tronco que a habilidade Grab Tree poe na
mao direita (skill.grab_tree; a sim zera Entity::treeHits depois de 10 golpes e o jogo volta ao modelo e00F nu).
O tronco e uma peca rigida do antebraco R, peso 1.0 no osso da mao: sobe do punho como um porrete, inclinado para
fora e para a frente, e a copa fica na ponta; o golpe do clipe chop/slice sai desse tronco (data/hand_grip.tsv).

    blender -b --factory-startup -P tools/blender/units/e00F_tree.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import e00F as E  # noqa: E402
import hand_unit as H  # noqa: E402

PALETTE = {**E.PALETTE, "bark": 0x6B4A2E, "bark_dk": 0x4A3220, "leaf": 0x3F7A34, "leaf_dk": 0x2E5A2A,
           "leaf_lt": 0x6AA040}

BONE = "forearm.R"
BASE = (-0.84, 0.46, 0.1)       # abaixo do punho: o punho segura o tronco no meio da mao
TOP = (-1.7, 3.0, 1.0)          # a ponta do tronco, onde nasce a copa
CROWN = (  # tom, deslocamento da base da copa em relacao a TOP, raio da base, altura
    ("leaf_dk", (0.0, -0.3, 0.0), 0.62, 0.5), ("leaf", (0.0, 0.1, 0.0), 0.7, 0.5),
    ("leaf_lt", (0.05, 0.55, 0.0), 0.5, 0.45), ("leaf", (-0.45, 0.0, 0.3), 0.38, 0.4),
    ("leaf_dk", (0.4, -0.1, -0.3), 0.36, 0.4))


def lerp(t):
    return tuple(BASE[i] + (TOP[i] - BASE[i]) * t for i in range(3))


def tree():
    H.chain(BONE, "bark", [lerp(0.0), lerp(0.25), lerp(0.6), lerp(1.0)],
            [(0.14, 0.14), (0.15, 0.15), (0.13, 0.13), (0.1, 0.1)], sides=6)
    H.frustum(BONE, "bark_dk", lerp(0.0), lerp(0.05), (0.16, 0.16), (0.16, 0.16), sides=6)          # pe cortado
    H.frustum(BONE, "bark_dk", lerp(0.66), (-1.25, 2.55, 1.75), (0.06, 0.06), (0.02, 0.02), sides=4)  # galho para a frente
    H.frustum(BONE, "bark_dk", lerp(0.5), (-0.5, 2.1, -0.1), (0.06, 0.06), (0.02, 0.02), sides=4)     # galho para dentro
    for tone, (dx, dy, dz), r, h in CROWN:
        c = (TOP[0] + dx, TOP[1] + dy, TOP[2] + dz)
        H.frustum(BONE, tone, c, (c[0], c[1] + h, c[2]), (r, r), (r * 0.55, r * 0.55), sides=8)


def make():
    E.make()
    tree()


if __name__ == "__main__":
    H.build("e00F_tree", "biped", PALETTE, make, E.joints())
