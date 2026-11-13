"""Lesser Elemental Of Wind (o00C): medido em artifacts/model-sheets/refs/o00C/sheet.jpg (familia shard).

    blender -b --factory-startup -P tools/blender/units/o00C.py -- <out.glb>

Escala da prancha: 0.0036 m por pixel (figura de ~2.4 m). No perfil da prancha a frente e a ESQUERDA
(o olho ambar fica la). Dois cacos de aco em V (wing1 = o curto e serrilhado, wing2 = o longo que
tomba para tras), uma nuvem no vao do V (body), a fita ambar do vento (plate.*) e o toco marrom atras (tail.1).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "steel": 0x6E7D8B, "steel_dk": 0x56646F, "edge": 0xDDE3EC, "cloud": 0xDBDEE7, "cloud_sh": 0xB6BCC9,
    "amber": 0xD6A24F, "amber_dk": 0xB07C2E, "brown": 0x5A4332, "eye": 0xF4A21C,
}

# caco longo (wing2) e caco curto (wing1): base na ponta do V, meio, topo
LONG = [(0.0, 0.0, 0.4), (-0.22, 0.8, 0.05), (-0.43, 1.55, -0.35), (-0.55, 2.1, -0.72), (-0.65, 2.45, -0.9)]
SHORT = [(0.0, 0.0, 0.4), (0.3, 0.9, 0.1), (0.62, 1.65, -0.18), (0.7, 1.82, -0.22)]


def puff(tone, c, r, bone="body"):
    """Bola facetada de nuvem: dois troncos, cintura larga no meio."""
    x, y, z = c
    H.frustum(bone, tone, (x, y - r * 0.8, z), (x, y, z), (r * 0.62, r * 0.62), (r, r), sides=6)
    H.frustum(bone, tone, (x, y, z), (x, y + r * 0.8, z), (r, r), (r * 0.6, r * 0.6), sides=6)


def cloud():
    for c, r in (((0, 1.25, 0.0), 0.58), ((-0.4, 1.42, 0.0), 0.34), ((0.4, 1.38, 0.0), 0.34),
                 ((0, 1.72, -0.05), 0.34), ((-0.25, 0.98, 0.12), 0.34), ((0.3, 1.0, 0.0), 0.34),
                 ((0.0, 1.2, 0.36), 0.38), ((0.0, 1.3, -0.36), 0.34)):
        puff("cloud", c, r)
    puff("cloud_sh", (0.0, 0.95, -0.05), 0.3)
    H.frustum("body", "eye", (0, 1.0, 0.55), (0, 1.22, 0.6), (0.07, 0.04), (0.02, 0.02), sides=4)


def blade(bones, pts, width, thick, tone, edge_x):
    """Caco: troncos achatados de largura quase constante que fecham numa ponta curta, fio claro na borda de fora."""
    mid = [(width * 0.4, thick * 0.8), (width, thick), (width * 1.05, thick)]
    radii = [mid[min(i, 2)] for i in range(len(pts) - 1)] + [(0.02, 0.012)]
    H.chain(bones, tone, pts, radii, sides=4)
    edge = [(p[0] + edge_x * width * 0.85, p[1], p[2] + 0.02) for p in pts]
    H.chain(bones, "edge", edge, [(0.04, 0.08)] * (len(pts) - 1) + [(0.01, 0.01)], sides=4)


def jag():
    """Topo serrilhado do caco curto."""
    x, y, z = SHORT[2]
    for dx, dy in ((-0.12, 0.0), (0.1, 0.1), (0.0, 0.2)):
        H.frustum("wing1.lower", "steel", (x + dx, y - 0.1, z), (x + dx * 1.2, y + dy + 0.12, z - 0.03),
                  (0.1, 0.05), (0.01, 0.01), sides=4)


def swirl():
    """A fita de vento: S grosso por cima da nuvem, da frente para tras, afinando num fio."""
    pts = [(-0.25, 1.55, 0.35), (-0.3, 1.9, 0.15), (-0.05, 2.05, -0.2), (0.3, 2.2, -0.5), (0.65, 2.32, -0.85)]
    radii = [(0.14, 0.07), (0.19, 0.07), (0.17, 0.06), (0.11, 0.04), (0.01, 0.01)]
    H.chain(["plate.3", "plate.3", "plate.2", "plate.1"], "amber", pts, radii, sides=4)
    H.frustum("plate.1", "amber_dk", (0.2, 2.18, -0.42), (0.42, 2.28, -0.62), (0.06, 0.02), (0.01, 0.01), sides=4)


def stub():
    H.frustum("tail.1", "brown", (0, 1.28, -0.4), (0, 1.3, -0.82), (0.14, 0.14), (0.17, 0.17), sides=6)
    H.frustum("tail.1", "brown", (0, 1.3, -0.8), (0, 1.32, -0.92), (0.17, 0.17), (0.1, 0.1), sides=6)


def make():
    blade(["wing2.upper", "wing2.lower", "wing2.lower", "wing2.lower"], LONG, 0.17, 0.06, "steel", -1)
    blade(["wing1.upper", "wing1.lower", "wing1.lower"], SHORT, 0.17, 0.06, "steel_dk", 1)
    jag()
    cloud()
    swirl()
    stub()


def joints():
    return {
        "wing2.upper": (LONG[0], LONG[1]), "wing2.lower": (LONG[1], LONG[4]),
        "wing1.upper": (SHORT[0], SHORT[1]), "wing1.lower": (SHORT[1], SHORT[3]),
    }


H.build("o00C", "shard", PALETTE, make, joints())
