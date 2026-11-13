"""Ballista (e005): barco sobre rodas com besta gigante, medido em artifacts/model-sheets/refs/e005/sheet.jpg
(perfil: 0.0045 m por pixel).

    blender -b --factory-startup -P tools/blender/units/e005.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "gold": 0xE8B230, "gold_dk": 0xB98620, "brown": 0x6E4529, "brown_dk": 0x4E2F1A, "white": 0xD4E0E6,
    "blue": 0x2A82D8, "black": 0x1E1C1C, "purple": 0x7B58A8,
}

# (osso esquerdo, osso direito, z, raio, x interno, x externo)
AXLES = (("wheel1", "wheel2", 0.4, 0.36, 0.68, 0.92), ("wheel3", "wheel4", -0.8, 0.3, 0.46, 0.66))
PIVOT = (0.0, 1.55, 0.3)
ARM = ((0.15, 1.62, 0.3), (0.55, 1.62, 0.12), (0.9, 1.52, -0.12), (1.2, 1.45, -0.4))     # braco da besta (lado esquerdo)
CRESCENT = ((1.2, 1.45, -0.4), (1.42, 1.58, -0.46), (1.46, 1.82, -0.44), (1.3, 2.0, -0.38))


def wheel(bone, s, z, r, x0, x1):
    y = r
    a, b = s * x0, s * x1
    H.frustum(bone, "gold", (a, y, z), (b, y, z), (r, r), (r, r), sides=10)
    H.frustum(bone, "gold_dk", (b - s * 0.03, y, z), (b + s * 0.02, y, z), (r * 1.03, r * 1.03), (r * 1.03, r * 1.03), sides=10)
    H.frustum(bone, "brown", (b, y, z), (b + s * 0.03, y, z), (r * 0.72, r * 0.72), (r * 0.72, r * 0.72), sides=8)
    H.frustum(bone, "white", (b + s * 0.02, y, z), (b + s * 0.07, y, z), (r * 0.2, r * 0.2), (r * 0.2, r * 0.2), sides=6)
    H.frustum(bone, "white", (b + s * 0.05, y, z), (b + s * 0.5, y, z), (0.1, 0.1), (0.015, 0.015), sides=6)


def hull():
    for (z0, y0, r0), (z1, y1, r1) in zip(((1.28, 1.0, (0.2, 0.3)), (0.7, 0.78, (0.62, 0.42)), (-0.2, 0.72, (0.7, 0.45)), (-0.9, 0.78, (0.6, 0.4))),
                                          ((0.7, 0.78, (0.62, 0.42)), (-0.2, 0.72, (0.7, 0.45)), (-0.9, 0.78, (0.6, 0.4)), (-1.3, 1.0, (0.2, 0.28)))):
        H.frustum("hull", "brown", (0, y0, z0), (0, y1, z1), r0, r1, sides=8)
    H.frustum("hull", "brown_dk", (0, 0.45, 0.9), (0, 0.45, -0.9), (0.3, 0.2), (0.25, 0.18), sides=6)
    for s in (-1, 1):
        H.chain("hull", "gold", [(s * 0.2, 1.3, 1.28), (s * 0.58, 1.14, 0.7), (s * 0.7, 1.1, -0.2), (s * 0.6, 1.14, -0.9), (s * 0.2, 1.4, -1.3)],
                [(0.06, 0.06)] * 5, sides=6)
        H.frustum("hull", "purple", (s * 0.68, 0.98, 0.5), (s * 0.7, 0.96, -0.5), (0.03, 0.04), (0.03, 0.04), sides=4)
    H.frustum("hull", "gold", (0, 1.3, 1.3), (0, 0.4, 1.05), (0.07, 0.05), (0.07, 0.05), sides=4)        # quilha da proa
    H.chain("hull", "gold", [(0, 1.1, -1.2), (0, 1.35, -1.6)], [(0.07, 0.06), (0.05, 0.05)], sides=4)    # garfo da popa
    for s in (-1, 1):
        H.chain("hull", "gold", [(0, 1.35, -1.6), (s * 0.12, 1.5, -1.85)], [(0.05, 0.05), (0.03, 0.03)], sides=4)
    H.frustum("hull", "black", (-0.4, 0.95, -0.25), (-0.4, 1.7, -0.25), (0.1, 0.1), (0.09, 0.09), sides=8)  # escape
    H.frustum("hull", "black", (-0.4, 1.7, -0.25), (-0.5, 1.8, -0.2), (0.1, 0.1), (0.11, 0.11), sides=8)
    for _, _, z, r, x0, _ in AXLES:
        H.frustum("hull", "brown_dk", (-x0, r, z), (x0, r, z), (0.06, 0.06), (0.06, 0.06), sides=6)


def bow():
    for s in (-1, 1):
        pts = [(s * x, y, z) for x, y, z in ARM]
        H.chain("head", "brown", pts, [(0.14, 0.12), (0.15, 0.12), (0.13, 0.1), (0.1, 0.09)], sides=6)
        H.chain("head", "gold", [(s * x, y + 0.08, z) for x, y, z in ARM], [(0.04, 0.05)] * 4, sides=4)
        H.chain("head", "gold", [(s * x, y, z) for x, y, z in CRESCENT], [(0.1, 0.1), (0.1, 0.1), (0.08, 0.08), (0.015, 0.015)], sides=6)


def stock():
    H.frustum("hull", "brown_dk", (0, 1.0, 0.3), (0, 1.5, 0.3), (0.22, 0.22), (0.17, 0.17), sides=8)     # cavalete
    H.frustum("head", "brown", (0, 1.5, 0.3), (0, 1.64, 0.3), (0.2, 0.34), (0.16, 0.3), sides=6)
    H.frustum("head", "gold", (0, 1.52, 0.55), (0, 1.58, -0.2), (0.07, 0.1), (0.1, 0.12), sides=4)
    H.frustum("head", "brown", (0, 1.5, 0.95), (0, 1.54, -0.45), (0.09, 0.09), (0.1, 0.09), sides=6)   # calha
    H.frustum("head", "brown", (0, 1.5, 0.3), (0, 1.62, -0.55), (0.2, 0.22), (0.1, 0.1), sides=6)


def arrow():
    H.frustum("head", "brown_dk", (0, 1.64, -1.2), (0, 1.64, 1.0), (0.045, 0.045), (0.045, 0.045), sides=6)
    H.frustum("head", "white", (0, 1.64, 0.75), (0, 1.64, 1.05), (0.05, 0.04), (0.26, 0.045), sides=4)    # ponta, lamina larga
    H.frustum("head", "white", (0, 1.64, 1.05), (0, 1.64, 1.55), (0.26, 0.045), (0.02, 0.02), sides=4)
    H.frustum("head", "white", (0, 1.64, 0.95), (0, 1.64, 1.1), (0.1, 0.07), (0.1, 0.07), sides=4)
    H.frustum("head", "blue", (0, 1.64, -0.6), (0, 1.64, -1.3), (0.2, 0.02), (0.3, 0.02), sides=4)       # penas
    H.frustum("head", "blue", (0, 1.64, -0.6), (0, 1.64, -1.3), (0.02, 0.2), (0.02, 0.3), sides=4)


def make():
    hull()
    stock()
    bow()
    arrow()
    for bl, br, z, r, x0, x1 in AXLES:
        wheel(bl, 1, z, r, x0, x1)
        wheel(br, -1, z, r, x0, x1)


def joints():
    out = {"head": (PIVOT, (PIVOT[0], PIVOT[1], PIVOT[2] + 0.5))}
    for bl, br, z, r, x0, x1 in AXLES:
        out[bl] = ((x0, r, z), (x1, r, z))
        out[br] = ((-x0, r, z), (-x1, r, z))
    return out


H.build("e005", "vehicle", PALETTE, make, joints())
