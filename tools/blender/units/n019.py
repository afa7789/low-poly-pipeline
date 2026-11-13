"""Void Walker (n019): medido em artifacts/model-sheets/refs/n019/sheet.jpg (familia pod).

    blender -b --factory-startup -P tools/blender/units/n019.py -- <out.glb>

Escala da prancha: 0.00288 m por pixel (haste ate 2.1 m, pontas dos tentaculos a 0.2 m).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "void": 0x3A2A50, "void_dk": 0x2C2040, "plate": 0x1E1E1E, "stalk": 0x75703A, "stalk_dk": 0x5A572C,
    "eye": 0x8EF53A, "rim": 0x1A3A12, "pupil": 0x050505,
}

TENDRILS = {1: (-0.15, 0.26), 2: (-0.15, -0.26), 3: (0.30, 0.0)}   # (x, z) do topo, como nos ossos da familia


def body():
    """Cupula roxa achatada: base estreita, ombro largo, topo que fecha em volta da haste."""
    rings = [(0.46, (0.5, 0.52)), (0.62, (0.72, 0.66)), (0.85, (0.76, 0.68)), (1.08, (0.6, 0.66)), (1.3, (0.3, 0.6))]
    for (ya, ra), (yb, rb) in zip(rings, rings[1:]):
        H.frustum("body", "void", (0, ya, 0), (0, yb, 0), ra, rb, sides=8)
    H.frustum("body", "void_dk", (0, 0.4, 0), (0, 0.5, 0), (0.4, 0.36), (0.5, 0.46), sides=8)


def plates():
    """Casco preto nas costas: duas placas inclinadas que sobem ate a haste."""
    H.frustum("body", "plate", (0, 0.86, -0.3), (0, 1.18, -0.26), (0.66, 0.4), (0.5, 0.34), sides=8)
    H.frustum("body", "plate", (0, 1.12, -0.28), (0, 1.36, -0.24), (0.46, 0.3), (0.26, 0.2), sides=8)
    for s in (-1, 1):
        H.frustum("body", "plate", (s * 0.5, 0.9, 0.0), (s * 0.4, 1.12, -0.05), (0.2, 0.34), (0.18, 0.3), sides=6)


def eye():
    H.frustum("body", "rim", (0, 0.9, 0.5), (0, 0.9, 0.7), (0.44, 0.38), (0.4, 0.34), sides=12)
    H.frustum("body", "eye", (0, 0.9, 0.66), (0, 0.9, 0.78), (0.36, 0.3), (0.34, 0.28), sides=12)
    H.frustum("body", "pupil", (0, 0.9, 0.76), (0, 0.9, 0.82), (0.07, 0.14), (0.06, 0.12), sides=6)


def stalk():
    """Haste grossa em duas pecas por osso, afinando para o topo."""
    pts = [(0, 1.15, 0.06), (0, 1.4, 0.05), (0, 1.75, 0.03), (0, 2.1, 0.0)]
    radii = [(0.14, 0.14), (0.11, 0.11), (0.1, 0.1), (0.085, 0.085)]
    H.chain(["body", "stalk.1", "stalk.2"], "stalk", pts, radii, sides=6)
    H.frustum("stalk.2", "stalk_dk", (0, 2.0, 0.01), (0, 2.14, 0.0), (0.09, 0.09), (0.07, 0.07), sides=6)


def tendril_points(n):
    x, z = TENDRILS[n]
    return [(x, 0.55, z), (x * 1.25, 0.37, z * 1.25), (x * 1.5, 0.2, z * 1.5)]


def tendrils():
    for n in TENDRILS:
        H.chain([f"tendril{n}.1", f"tendril{n}.2"], "stalk", tendril_points(n), [(0.09, 0.09), (0.065, 0.065), (0.045, 0.045)])


def make():
    body()
    plates()
    eye()
    stalk()
    tendrils()


def joints():
    out = {"body": ((0, 0.9, 0), (0, 1.3, 0)), "stalk.1": ((0, 1.4, 0.05), (0, 1.75, 0.03)),
           "stalk.2": ((0, 1.75, 0.03), (0, 2.1, 0.0))}
    for n in TENDRILS:
        a, b, c = tendril_points(n)
        out[f"tendril{n}.1"], out[f"tendril{n}.2"] = (a, b), (b, c)
    return out


H.build("n019", "pod", PALETTE, make, joints())
