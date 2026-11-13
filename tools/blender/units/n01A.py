"""Void Keeper (n01A): medido em artifacts/model-sheets/refs/n01A/sheet.jpg (familia pod).

    blender -b --factory-startup -P tools/blender/units/n01A.py -- <out.glb>

Escala da prancha: 0.0021 m por pixel (broto de ~2.4 m, tentaculos tocam o chao); frente = esquerda no perfil.
As petalas sao cortadas por osso: a base no corpo, o meio na haste.1, a ponta na haste.2, entao o broto ondula.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "petal": 0x2B2A6B, "petal_dk": 0x1F1B3C, "core": 0x16110F, "trim": 0x6A6A3A, "lilac": 0x9B8AC8,
    "eye": 0x39FF14, "root": 0x6A6A3A, "root_dk": 0x55552E,
}

SEG = ["body", "stalk.1", "stalk.2"]            # um pedaco por osso da cadeia
YS = [1.02, 1.5, 1.95, 2.4]
# (x, z) do topo de cada tentaculo e seu gemeo, no mesmo osso
ROOTS = {1: [(-0.24, 0.06), (-0.15, -0.04)], 2: [(0.19, -0.12)], 3: [(0.1, 0.0)]}


def petals():
    """Duas conchas altas: a esquerda do desenho reta e alta, a direita mais baixa e aberta para fora."""
    left = [(-0.05, 0.05), (-0.2, 0.2), (-0.28, 0.18), (-0.34, 0.1)]
    right = [(0.05, 0.05), (0.2, 0.2), (0.3, 0.18), (0.38, 0.1)]
    right_y = [1.02, 1.5, 1.85, 2.1]
    for xs, ys, tone in ((left, YS, "petal"), (right, right_y, "petal")):
        pts = [(x, y, 0.0) for (x, _), y in zip(xs, ys)]
        radii = [(0.1, 0.16), (0.19, 0.24), (0.17, 0.22), (0.09, 0.15)]
        H.chain(SEG, tone, pts, radii, sides=6)
    H.chain(SEG, "petal_dk", [(-0.2, 1.4, 0.1), (-0.25, 1.9, 0.1), (-0.3, 2.3, 0.08)], [(0.1, 0.1), (0.1, 0.1), (0.05, 0.08)],
            sides=6)


def core():
    """Miolo preto entre as petalas, com o olho verde aceso."""
    H.chain(SEG, "core", [(0, 1.0, 0), (0, 1.5, 0), (0, 1.9, 0), (0, 2.12, 0)],
            [(0.05, 0.1), (0.08, 0.15), (0.07, 0.13), (0.02, 0.05)], sides=6)
    H.frustum("stalk.1", "eye", (0, 1.77, 0.12), (0, 1.77, 0.21), (0.06, 0.06), (0.05, 0.05), sides=8)


def bulb():
    """Bulbo lilas nas costas, espiando entre as petalas."""
    H.chain(["stalk.1", "stalk.1"], "lilac", [(0, 1.38, -0.2), (0, 1.62, -0.22), (0, 1.88, -0.2)],
            [(0.05, 0.04), (0.14, 0.12), (0.05, 0.04)], sides=8)


def root_points(n, k):
    x, z = ROOTS[n][k]
    return [(x, 1.1, z), (x * 1.05, 0.55, z * 1.05), (x * 1.1, 0.02, z * 1.1)]


def tendrils():
    for n, twins in ROOTS.items():
        for k in range(len(twins)):
            H.chain([f"tendril{n}.1", f"tendril{n}.2"], "root", root_points(n, k),
                    [(0.045, 0.045), (0.04, 0.04), (0.03, 0.03)])


def make():
    petals()
    core()
    bulb()
    tendrils()


def joints():
    out = {"body": ((0, 0.95, 0), (0, 1.5, 0)), "stalk.1": ((0, 1.5, 0), (0, 1.95, 0)),
           "stalk.2": ((0, 1.95, 0), (0, 2.4, 0))}
    for n in ROOTS:
        a, b, c = root_points(n, 0)
        out[f"tendril{n}.1"], out[f"tendril{n}.2"] = (a, b), (b, c)
    return out


H.build("n01A", "pod", PALETTE, make, joints())
