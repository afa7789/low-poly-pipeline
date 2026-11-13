"""Felhound (n01G), quadruped: measured on artifacts/model-sheets/refs/n01G/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n01G.py -- <out.glb>

Scale read off the profile: 370 px per metre, nose at z=+1.0, ground at y=0.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "purple": 0x6A5A82, "purple_dk": 0x4E4064, "olive": 0x716E4C, "olive_dk": 0x5A583B,
    "black": 0x1C1B1E, "spine": 0x6E7A4E,
}

# juntas (metros), medidas na vista de lado/frente: (x, y, z) do quadril, joelho e pata
FRONT = ((0.37, 0.95, 0.08), (0.32, 0.5, 0.11), (0.38, 0.06, 0.16))
HIND = ((0.38, 0.92, -0.62), (0.42, 0.42, -0.93), (0.39, 0.06, -0.72))
PAW_Y = 0.2
LEGS = ((1, FRONT, 1, 0.4), (-1, FRONT, 2, 0.4), (1, HIND, 3, -0.45), (-1, HIND, 4, -0.45))   # lado, perna, numero, ponta dos dedos


def mir(p, s):
    return (s * p[0], p[1], p[2])


def spikes(bone):
    for z, base, h in ((0.17, 1.3, 0.26), (0.0, 1.27, 0.32), (-0.17, 1.22, 0.24), (-0.35, 1.15, 0.17), (-0.5, 1.08, 0.12)):
        H.frustum(bone, "spine", (0, base - 0.05, z), (0, base + h, z - 0.12 - h * 0.3), (0.05, 0.07), (0.006, 0.006), sides=4)
    for s in (-1, 1):
        H.frustum(bone, "spine", (s * 0.2, 1.22, 0.12), (s * 0.4, 1.48, 0.03), (0.04, 0.05), (0.005, 0.005), sides=4)
        H.frustum(bone, "spine", (s * 0.3, 1.12, 0.05), (s * 0.5, 1.32, -0.02), (0.035, 0.04), (0.005, 0.005), sides=4)


def ribs(s):
    for i in range(5):       # placas inclinadas que contornam o flanco
        z = 0.02 - i * 0.1
        H.frustum("spine.1", "olive", (s * 0.4, 0.74 + i * 0.01, z), (s * 0.43, 1.12 - i * 0.03, z - 0.09), (0.05, 0.045), (0.05, 0.04), sides=4)


def trunk():
    H.frustum("spine.2", "purple", (0, 0.92, 0.5), (0, 1.0, -0.1), (0.28, 0.2), (0.46, 0.37))
    H.frustum("spine.1", "purple", (0, 1.0, -0.1), (0, 0.86, -0.45), (0.46, 0.37), (0.4, 0.27))
    H.frustum("spine.1", "purple", (0, 0.88, -0.4), (0, 0.9, -0.93), (0.38, 0.26), (0.44, 0.22))
    H.frustum("spine.1", "purple_dk", (0, 0.72, -0.05), (0, 0.72, -0.85), (0.44, 0.12), (0.46, 0.12), sides=4)   # barriga recolhida
    for s in (-1, 1):
        H.frustum("spine.2", "olive", (s * 0.41, 0.72, 0.18), (s * 0.45, 1.1, 0.12), (0.06, 0.2), (0.06, 0.16), sides=4)
        H.frustum("spine.1", "olive", (s * 0.4, 0.78, -0.62), (s * 0.45, 1.0, -0.66), (0.06, 0.22), (0.06, 0.2), sides=4)
        ribs(s)
    spikes("spine.2")
    H.frustum("tail.1", "purple", (0, 0.9, -0.85), (0, 0.88, -1.0), (0.1, 0.1), (0.06, 0.06), sides=4)
    H.frustum("tail.2", "purple", (0, 0.88, -1.0), (0, 0.84, -1.1), (0.06, 0.06), (0.03, 0.03), sides=4)


def collar():
    for i in range(8):       # anel grosso de 8 cunhas curtas em volta do pescoco
        t0, t1 = (i - 0.5) * math.pi / 4, (i + 0.5) * math.pi / 4
        a = (0.3 * math.cos(t0), 0.93 + 0.31 * math.sin(t0), 0.42)
        b = (0.3 * math.cos(t1), 0.93 + 0.31 * math.sin(t1), 0.42)
        H.frustum("head", "olive_dk", a, b, (0.06, 0.07), (0.06, 0.07), sides=4)


def head():
    H.frustum("head", "purple", (0, 0.94, 0.4), (0, 0.93, 0.85), (0.24, 0.18), (0.2, 0.17))
    H.frustum("head", "black", (0, 0.85, 0.82), (0, 0.84, 1.0), (0.19, 0.15), (0.14, 0.13))
    collar()


def paw(bone, s, p, toe_z):
    x, _, z = p
    H.frustum(bone, "olive", (s * x, PAW_Y + 0.1, z), (s * x, 0.04, z + 0.02), (0.1, 0.1), (0.15, 0.14))       # calcanhar
    H.frustum(bone, "olive", (s * x, 0.05, z - 0.03), (s * x, 0.03, z + 0.12), (0.15, 0.1), (0.17, 0.08), sides=4)
    for k in (-1, 0, 1):     # 3 dedos longos abrindo para frente e para fora
        end = (s * (x + k * 0.17), 0.02, toe_z - abs(k) * 0.05)
        H.frustum(bone, "olive_dk", (s * (x + k * 0.05), 0.04, z + 0.08), end, (0.045, 0.03), (0.012, 0.01), sides=4)


def leg(s, geo, n, toe_z):
    hip, knee, ank = (mir(p, s) for p in geo)
    up, lo = f"leg{n}.upper", f"leg{n}.lower"
    front = geo is FRONT
    H.frustum(up, "purple", hip, knee, (0.19, 0.22), (0.11, 0.12))
    H.frustum(lo, "purple" if front else "purple_dk", knee, (ank[0], PAW_Y, ank[2]), (0.11, 0.12), (0.09, 0.09))
    # massa do ombro / anca: maior que o tronco, o A visto de frente
    top = (s * (geo[0][0] + 0.02), geo[0][1] + 0.14, geo[0][2] - 0.04)
    H.frustum(up, "purple", (s * (geo[0][0] + 0.02), 0.52, geo[0][2]), top, (0.17, 0.26), (0.14, 0.22), sides=6)
    H.frustum(up, "purple_dk", (s * (geo[0][0] + 0.06), 0.6, geo[0][2]), (s * (geo[0][0] + 0.04), 1.0, geo[0][2]), (0.08, 0.25), (0.07, 0.2), sides=4)
    paw(lo, s, geo[2], toe_z)


def make():
    trunk()
    head()
    for args in LEGS:
        leg(*args)


def joints():
    out = {
        "spine.1": ((0, 0.95, -0.85), (0, 1.0, -0.15)), "spine.2": ((0, 1.0, -0.15), (0, 1.0, 0.45)),
        "head": ((0, 1.0, 0.45), (0, 0.9, 1.0)),
        "tail.1": ((0, 0.92, -0.85), (0, 0.9, -1.0)), "tail.2": ((0, 0.9, -1.0), (0, 0.85, -1.15)),
    }
    for s, geo, n, _ in LEGS:
        hip, knee, ank = (mir(p, s) for p in geo)
        out[f"leg{n}.upper"] = (hip, knee)
        out[f"leg{n}.lower"] = (knee, ank)
    return out


H.build("n01G", "quadruped", PALETTE, make, joints())
