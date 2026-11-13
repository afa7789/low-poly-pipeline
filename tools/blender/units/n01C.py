"""Raised Tentacle (n01C): medido em artifacts/model-sheets/refs/n01C/sheet.jpg (familia pod).

    blender -b --factory-startup -P tools/blender/units/n01C.py -- <out.glb>

Escala da prancha: 0.0058 m por pixel (tronco de ~2.4 m); frente = esquerda no perfil, o gancho aponta para a frente.
Sem a grade de pedra da prancha (e cenario, nao e parte da unidade).
O tronco e cortado em pecas por osso (body / stalk.1 / stalk.2) e o gancho vai todo no stalk.2 (a familia so tem
duas hastes); os dois cachos laterais vao nas cadeias tendril1 e tendril3, que o 'lash' chicoteia.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "bark": 0x5E5A2E, "bark_dk": 0x453F22, "bark_lt": 0x77723A, "glow": 0x6FFF2A, "black": 0x1C1C14,
}

# curl lateral: 4 pontos (x do lado +); primeiros dois segmentos no .1, o ultimo no .2
CURL = [(0.2, 0.85, 0.0), (0.5, 1.2, 0.04), (0.7, 1.3, 0.1), (0.82, 1.1, 0.16)]


def trunk():
    """Tronco: raiz que abre no chao, fuste grosso que afina de leve ate o gancho."""
    rings = [(0.0, (0.46, 0.42)), (0.25, (0.34, 0.3)), (0.6, (0.28, 0.26)), (1.0, (0.3, 0.27)), (1.3, (0.26, 0.24))]
    for (ya, ra), (yb, rb) in zip(rings, rings[1:]):
        H.frustum("body", "bark", (0, ya, 0), (0, yb, 0), ra, rb, sides=8)
    H.frustum("stalk.1", "bark", (0, 1.25, 0), (0, 1.6, 0), (0.26, 0.24), (0.25, 0.23), sides=8)
    H.frustum("stalk.1", "bark_lt", (0, 1.55, 0), (0, 1.9, 0), (0.25, 0.23), (0.24, 0.22), sides=8)
    H.frustum("stalk.2", "bark", (0, 1.85, 0), (0, 2.15, 0.02), (0.24, 0.22), (0.23, 0.21), sides=8)


def hook():
    """O gancho: o topo se curva para a frente e a ponta preta aponta para baixo, grande para chicotear."""
    pts = [(0, 2.1, 0.02), (0, 2.3, 0.1), (0, 2.42, 0.34), (0, 2.34, 0.6), (0, 2.1, 0.76), (0, 1.8, 0.74)]
    radii = [(0.23, 0.21), (0.23, 0.21), (0.21, 0.19), (0.17, 0.15), (0.13, 0.11), (0.06, 0.05)]
    for seg, tone in zip(H.chain("stalk.2", "bark", pts, radii, sides=8), ("bark", "bark", "bark", "bark_dk", "black")):
        seg["tone"] = tone
    H.frustum("stalk.2", "black", (0, 2.0, 0.1), (0, 2.3, 0.3), (0.12, 0.05), (0.14, 0.05), sides=4)


def veins():
    """Veias verdes que brilham na frente e nas costas do tronco."""
    for f in (1, -1):
        H.chain(["body", "body", "stalk.1", "stalk.1"], "glow",
                [(0, 0.1, f * 0.4), (0.04, 0.7, f * 0.29), (-0.03, 1.4, f * 0.27), (0, 1.8, f * 0.25)],
                [(0.05, 0.03), (0.05, 0.03), (0.05, 0.03), (0.04, 0.03)])
        for s in (-1, 1):
            H.chain("body", "glow", [(s * 0.3, 0.1, f * 0.38), (s * 0.12, 0.45, f * 0.31), (0, 0.8, f * 0.28)],
                    [(0.04, 0.03), (0.04, 0.03), (0.035, 0.03)])


def curls():
    """Dois cachos que saem do tronco para os lados e dobram no fim, nas cadeias tendril1 (direita) e tendril3 (esquerda)."""
    for s, n in ((1, 3), (-1, 1)):
        pts = [(s * x, y, z) for x, y, z in CURL]
        bones = [f"tendril{n}.1", f"tendril{n}.1", f"tendril{n}.2"]
        H.chain(bones, "bark", pts, [(0.2, 0.18), (0.17, 0.15), (0.12, 0.11), (0.05, 0.05)], sides=6)
        H.frustum(f"tendril{n}.2", "glow", (s * 0.6, 1.3, 0.1), (s * 0.78, 1.2, 0.14), (0.03, 0.03), (0.03, 0.03), sides=4)


def make():
    trunk()
    hook()
    veins()
    curls()


def joints():
    out = {"body": ((0, 0.3, 0), (0, 1.3, 0)), "stalk.1": ((0, 1.3, 0), (0, 1.85, 0)),
           "stalk.2": ((0, 1.85, 0), (0, 2.4, 0.1))}
    for s, n in ((1, 3), (-1, 1)):
        p = [(s * x, y, z) for x, y, z in CURL]
        out[f"tendril{n}.1"], out[f"tendril{n}.2"] = (p[0], p[2]), (p[2], p[3])
    return out


H.build("n01C", "pod", PALETTE, make, joints())
