"""Greater Elemental Of Wind (o00E): medido em artifacts/model-sheets/refs/o00E/sheet.jpg (familia shard).

    blender -b --factory-startup -P tools/blender/units/o00E.py -- <out.glb>

Escala da prancha: 0.0041 m por pixel (figura de ~3.9 m). No perfil da prancha a frente e a ESQUERDA (o
topo mais alto da coroa). Um monolito de pedra (body) fino de frente e largo de perfil, com veio ambar nas
faces estreitas, coroa de pilares escalonados (plate.*), tres aletas planas de cada lado (wing1/wing2: a
parte de dentro no upper, a de fora no lower), nuvens em fileira embaixo e a quilha preta em ponta.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "stone": 0x9AA3AD, "stone_dk": 0x7F8993, "ice": 0xCDEEF2, "keel": 0x3A3B41, "keel_lt": 0x55565E,
    "amber": 0xDC9A2C, "cloud": 0xA9B5BE, "cloud_lt": 0xD4EDF2,
}

FIN_Y = (2.2, 1.95, 1.7)        # aleta de cima (mais longa) para a de baixo
FIN_REACH = (1.15, 1.0, 0.8)
FIN_Z = -0.25                   # centro das aletas no eixo da frente
CROWN = [  # (bone, z, x, topo, meia largura em z): pilares em degraus, o da frente e o mais alto
    ("plate.1", 0.62, 0.0, 3.9, 0.1), ("plate.1", 0.45, 0.14, 3.65, 0.1), ("plate.1", 0.4, -0.12, 3.75, 0.1),
    ("plate.2", 0.1, 0.1, 3.6, 0.12), ("plate.2", -0.1, -0.1, 3.7, 0.12), ("plate.2", -0.3, 0.12, 3.55, 0.12),
    ("plate.3", -0.5, -0.08, 3.5, 0.12), ("plate.3", -0.62, 0.1, 3.45, 0.1),
]


def puff(c, r, tone="cloud"):
    """Bola facetada de nuvem: dois troncos, cintura larga no meio."""
    x, y, z = c
    H.frustum("body", tone, (x, y - r * 0.8, z), (x, y, z), (r * 0.62, r * 0.62), (r, r), sides=6)
    H.frustum("body", tone, (x, y, z), (x, y + r * 0.8, z), (r, r), (r * 0.6, r * 0.6), sides=6)


def monolith():
    """A laje: base que estreita, corpo cheio, ombro chanfrado no topo."""
    H.frustum("body", "stone", (0, 0.9, 0.0), (0, 1.7, 0.0), (0.2, 0.62), (0.25, 0.7), sides=4)
    H.frustum("body", "stone", (0, 1.65, 0.0), (0, 2.8, 0.0), (0.25, 0.7), (0.26, 0.72), sides=4)
    H.frustum("body", "stone_dk", (0, 2.75, 0.0), (0, 3.3, 0.0), (0.26, 0.72), (0.22, 0.66), sides=4)
    for s in (-1, 1):       # fio de gelo nas quinas da frente
        H.frustum("body", "ice", (s * 0.25, 1.0, 0.0), (s * 0.27, 3.2, 0.0), (0.03, 0.66), (0.03, 0.62), sides=4)
    for z, tone in ((0.72, "amber"), (-0.74, "amber")):     # veio ambar, torto, nas duas faces estreitas
        xs = (0.0, 0.05, -0.04, 0.06, -0.03, 0.0)
        ys = (0.95, 1.5, 2.0, 2.5, 2.95, 3.3)
        H.chain("body", tone, [(x, y, z) for x, y in zip(xs, ys)], [(0.05, 0.03)] * 6, sides=4)


def keel():
    H.frustum("body", "keel", (0, 1.0, 0.0), (0, 0.6, 0.05), (0.2, 0.68), (0.18, 0.58), sides=4)
    H.frustum("body", "keel", (0, 0.62, 0.05), (0, 0.3, 0.3), (0.18, 0.58), (0.03, 0.08), sides=4)
    H.frustum("body", "keel_lt", (0, 0.9, 0.55), (0, 0.45, 0.45), (0.1, 0.03), (0.05, 0.03), sides=4)


def crown():
    for bone, z, x, top, hz in CROWN:
        H.frustum(bone, "stone", (x, 3.2, z), (x, top - 0.08, z), (0.16, hz * 1.4), (0.13, hz), sides=4)
        H.frustum(bone, "ice", (x, top - 0.1, z), (x, top, z), (0.13, hz), (0.05, hz * 0.5), sides=4)


def fins():
    for s, w in ((1, "wing1"), (-1, "wing2")):
        for y, reach in zip(FIN_Y, FIN_REACH):
            mid = 0.25 + (reach - 0.25) * 0.5
            H.frustum(f"{w}.upper", "stone_dk", (s * 0.2, y, FIN_Z), (s * mid, y, FIN_Z), (0.06, 0.72), (0.05, 0.6), sides=4)
            H.frustum(f"{w}.lower", "stone", (s * (mid - 0.05), y, FIN_Z), (s * reach, y, FIN_Z - 0.05),
                      (0.05, 0.6), (0.02, 0.3), sides=4)
            H.frustum(f"{w}.lower", "ice", (s * mid, y + 0.04, FIN_Z), (s * reach, y + 0.04, FIN_Z - 0.05),
                      (0.025, 0.5), (0.01, 0.22), sides=4)


def clouds():
    for s in (-1, 1):
        for i, z in enumerate((0.4, 0.0, -0.4, -0.78)):
            puff((s * 0.5, 1.3 - 0.04 * i, z), 0.26)
            puff((s * 0.8, 1.38, z - 0.1), 0.2, "cloud_lt")
    puff((0, 1.15, -0.5), 0.2)


def make():
    monolith()
    keel()
    crown()
    fins()
    clouds()


def joints():
    out = {}
    for s, w in ((1, "wing1"), (-1, "wing2")):
        out[f"{w}.upper"] = ((s * 0.2, 2.0, FIN_Z), (s * 0.7, 2.0, FIN_Z))
        out[f"{w}.lower"] = ((s * 0.7, 2.0, FIN_Z), (s * 1.15, 2.0, FIN_Z - 0.05))
    out["plate.1"] = ((0, 3.2, 0.5), (0, 3.8, 0.5))
    out["plate.2"] = ((0, 3.2, -0.05), (0, 3.7, -0.05))
    out["plate.3"] = ((0, 3.2, -0.55), (0, 3.5, -0.55))
    return out


H.build("o00E", "shard", PALETTE, make, joints())
