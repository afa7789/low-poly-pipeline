"""Elemental Of Wind (o00D): medido em artifacts/model-sheets/refs/o00D/sheet.jpg (familia shard).

    blender -b --factory-startup -P tools/blender/units/o00D.py -- <out.glb>

Escala da prancha: 0.0043 m por pixel (figura de ~2.8 m). No perfil da prancha a frente e a ESQUERDA
(o olho ambar fica la). Duas lajes escuras em V (wing1 = a longa que tomba para tras, no lado +x,
wing2 = a curta e reta) e um tufo de nuvem no vao do V (body) com o olho de brasa.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "slab": 0x5B5C63, "slab_dk": 0x46474E, "edge": 0xB9BDC0, "cloud": 0xDCDCE3, "cloud_sh": 0xADB0BB,
    "eye": 0xFF9A2E,
}

# laje longa (wing1, +x) e curta (wing2, -x): ponta do V, meio, ombro, topo
TALL = [(0.00, 0.0, 0.3), (0.49, 1.35, 0.1), (0.81, 2.25, -0.2), (0.97, 2.71, -0.4)]
SHORT = [(0.00, 0.0, 0.3), (-0.49, 1.15, 0.32), (-0.84, 2.0, 0.35), (-0.97, 2.32, 0.36)]


def puff(tone, c, r, bone="body", sides=6, tilt=0.0):
    """Bola facetada de nuvem: dois troncos, cintura larga no meio; tilt inclina o eixo para o lado."""
    x, y, z = c
    H.frustum(bone, tone, (x - tilt, y - r * 0.8, z), (x, y, z), (r * 0.62, r * 0.62), (r, r * 0.95), sides=sides)
    H.frustum(bone, tone, (x, y, z), (x + tilt, y + r * 0.8, z), (r, r * 0.95), (r * 0.6, r * 0.6), sides=sides)


LUMPS = (   # massa irregular de nuvem: (x, y, z, raio, lados, inclinacao)
    (0.0, 1.05, 0.05, 0.42, 8, 0.05), (-0.3, 1.3, 0.0, 0.3, 7, -0.08), (0.3, 1.38, 0.0, 0.34, 6, 0.1),
    (0.02, 1.62, 0.0, 0.24, 7, 0.0), (0.05, 0.8, 0.1, 0.26, 6, 0.06), (-0.12, 1.02, 0.28, 0.26, 7, -0.05),
    (0.2, 0.98, 0.3, 0.2, 6, 0.04), (-0.38, 1.0, -0.1, 0.22, 6, 0.0), (0.38, 1.12, -0.2, 0.22, 7, 0.0),
    (0.0, 1.1, -0.34, 0.3, 8, 0.0),
)


def cloud():
    for x, y, z, r, n, t in LUMPS:
        puff("cloud" if n != 6 else "cloud_sh", (x, y - 0.05, z), r * 1.25, sides=n, tilt=t)
    H.frustum("body", "eye", (0, 0.62, 0.7), (0, 0.9, 0.76), (0.09, 0.05), (0.02, 0.02), sides=4)


def blade(bones, pts, width, thick, tone, edge_x):
    """Caco: troncos achatados de largura quase constante que fecham numa ponta curta, fio claro na borda de fora."""
    radii = [(width, thick)] * (len(pts) - 1) + [(0.03, 0.02)]
    H.chain(bones, tone, pts, radii, sides=4)
    edge = [(p[0] + edge_x * width * (0.2 if i == 0 else 0.6), p[1], p[2] + 0.02) for i, p in enumerate(pts)]
    H.chain(bones, "edge", edge, [(0.04, 0.08)] * (len(pts) - 1) + [(0.01, 0.01)], sides=4)


def make():
    blade(["wing1.upper", "wing1.lower", "wing1.lower"], TALL, 0.17, 0.11, "slab", 1)
    blade(["wing2.upper", "wing2.lower", "wing2.lower"], SHORT, 0.17, 0.11, "slab_dk", -1)
    cloud()


def joints():
    return {
        "wing1.upper": (TALL[0], TALL[1]), "wing1.lower": (TALL[1], TALL[3]),
        "wing2.upper": (SHORT[0], SHORT[1]), "wing2.lower": (SHORT[1], SHORT[3]),
    }


H.build("o00D", "shard", PALETTE, make, joints())
