"""Frost Wolf (n017), quadruped: measured on artifacts/model-sheets/refs/n017/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n017.py -- <out.glb>

Scale read off the profile: 450 px per metre, nose at z=+1.0, ground at y=0.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "fur": 0xDDE0E6, "grey": 0x8A9098, "black": 0x1E1E22, "paw": 0xF4F4F6, "gold": 0xD9A030,
    "eye": 0x30C8E8, "rope": 0xA89878, "teeth": 0xE8D8B0,
}

# juntas (metros): (x, y, z) do ombro/quadril, cotovelo/joelho e pulso/tornozelo
FRONT = ((0.17, 0.74, 0.12), (0.17, 0.42, 0.2), (0.17, 0.17, 0.28))
HIND = ((0.18, 0.75, -0.5), (0.2, 0.5, -0.32), (0.18, 0.18, -0.58))
LEGS = ((1, FRONT, 1, 0.5), (-1, FRONT, 2, 0.5), (1, HIND, 3, -0.38), (-1, HIND, 4, -0.38))   # lado, perna, numero, ponta dos dedos


def mir(p, s):
    return (s * p[0], p[1], p[2])


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def ring(bone, z, cy, rx, ry, thick):
    """Faixa dourada: anel de 8 cunhas finas em volta do corpo."""
    for i in range(8):
        t0, t1 = (i - 0.5) * math.pi / 4, (i + 0.5) * math.pi / 4
        a = (rx * math.cos(t0), cy + ry * math.sin(t0), z)
        b = (rx * math.cos(t1), cy + ry * math.sin(t1), z)
        H.frustum(bone, "gold", a, b, (thick, thick), (thick, thick), sides=4)


def harness():
    ring("spine.2", 0.5, 0.84, 0.2, 0.2, 0.03)
    ring("spine.2", 0.1, 0.77, 0.27, 0.27, 0.035)
    for s in (-1, 1):
        H.frustum("spine.2", "gold", (s * 0.2, 0.78, 0.5), (s * 0.25, 1.0, 0.1), (0.025, 0.03), (0.025, 0.03), sides=4)


def trunk():
    H.frustum("spine.2", "fur", (0, 0.76, 0.42), (0, 0.78, 0.0), (0.2, 0.22), (0.26, 0.25))      # peito
    H.frustum("spine.2", "fur", (0, 0.8, 0.2), (0, 0.98, 0.55), (0.24, 0.24), (0.17, 0.2))       # pescoco grosso
    H.frustum("spine.1", "fur", (0, 0.78, 0.0), (0, 0.8, -0.3), (0.26, 0.25), (0.2, 0.2))
    H.frustum("spine.1", "fur", (0, 0.8, -0.25), (0, 0.8, -0.62), (0.2, 0.2), (0.15, 0.16))      # garupa
    H.frustum("spine.2", "grey", (0, 0.58, 0.35), (0, 0.55, 0.0), (0.15, 0.05), (0.2, 0.05), sides=6)    # barriga
    H.frustum("spine.1", "grey", (0, 0.55, 0.0), (0, 0.6, -0.45), (0.2, 0.05), (0.14, 0.05), sides=6)
    H.frustum("tail.1", "fur", (0, 0.88, -0.55), (0, 0.84, -0.85), (0.1, 0.14), (0.12, 0.19))
    H.frustum("tail.2", "fur", (0, 0.84, -0.85), (0, 0.88, -1.0), (0.12, 0.19), (0.09, 0.12))
    H.frustum("tail.2", "grey", (0, 0.88, -1.0), (0, 0.91, -1.17), (0.09, 0.12), (0.01, 0.01))
    harness()


def head():
    H.frustum("head", "fur", (0, 1.02, 0.46), (0, 1.0, 0.78), (0.2, 0.2), (0.14, 0.15))
    H.frustum("head", "fur", (0, 0.98, 0.74), (0, 0.95, 1.0), (0.12, 0.11), (0.06, 0.06))
    H.frustum("head", "black", (0, 0.955, 0.98), (0, 0.95, 1.02), (0.05, 0.045), (0.04, 0.035), sides=6)      # nariz
    H.frustum("head", "grey", (0, 0.86, 0.5), (0, 0.88, 0.95), (0.1, 0.04), (0.05, 0.03), sides=6)       # mandibula
    for s in (-1, 1):
        H.frustum("head", "fur", (s * 0.1, 0.98, 0.5), (s * 0.2, 0.92, 0.6), (0.1, 0.12), (0.05, 0.08))   # bochechas
        H.frustum("head", "eye", (s * 0.1, 1.08, 0.72), (s * 0.15, 1.08, 0.7), (0.025, 0.02), (0.03, 0.02), sides=6)
        H.frustum("head", "fur", (s * 0.11, 1.12, 0.52), (s * 0.14, 1.36, 0.46), (0.08, 0.03), (0.012, 0.01), sides=4)   # orelha
        H.frustum("head", "grey", (s * 0.11, 1.14, 0.55), (s * 0.13, 1.3, 0.5), (0.04, 0.012), (0.01, 0.008), sides=4)
        for z in (0.82, 0.9):
            H.frustum("head", "teeth", (s * 0.07, 0.9, z), (s * 0.07, 0.84, z + 0.01), (0.015, 0.015), (0.004, 0.004), sides=4)


def paw(bone, s, p, toe_z):
    x, _, z = p
    H.frustum(bone, "paw", (s * x, 0.12, z - 0.02), (s * x, 0.03, z + 0.08), (0.1, 0.09), (0.11, 0.07), sides=6)
    H.frustum(bone, "paw", (s * x, 0.05, z + 0.05), (s * x, 0.03, toe_z), (0.095, 0.05), (0.085, 0.03), sides=4)


def rope(bone, s):
    """A corda amarrada no tornozelo traseiro esquerdo do desenho."""
    H.frustum(bone, "rope", (s * 0.18, 0.2, -0.57), (s * 0.19, 0.07, -0.62), (0.05, 0.05), (0.05, 0.05), sides=6)
    pts = [(s * 0.19, 0.03, -0.62), (s * 0.22, 0.025, -0.9), (s * 0.2, 0.025, -1.2)]
    H.chain(bone, "rope", pts, [(0.022, 0.02)] * 3, sides=4)


def leg(s, geo, n, toe_z):
    hip, knee, ank = (mir(p, s) for p in geo)
    up, lo = f"leg{n}.upper", f"leg{n}.lower"
    hind = geo is HIND
    radii = [(0.14, 0.2), (0.13, 0.17), (0.08, 0.09)] if hind else [(0.12, 0.15), (0.14, 0.15), (0.08, 0.08)]
    H.chain(up, "fur", [(hip[0], hip[1] + 0.08, hip[2]), lerp(hip, knee, 0.45), knee], radii)
    mid = lerp(knee, ank, 0.45)
    foot = (ank[0], 0.12, ank[2])
    H.frustum(lo, "fur", knee, mid, (0.08, 0.08), (0.07, 0.075))
    H.frustum(lo, "black", mid, foot, (0.08, 0.08), (0.095, 0.09))     # meia preta
    paw(lo, s, geo[2], toe_z)
    if n == 4:
        rope(lo, s)


def make():
    trunk()
    head()
    for args in LEGS:
        leg(*args)


def joints():
    out = {
        "spine.1": ((0, 0.8, -0.55), (0, 0.8, 0.0)), "spine.2": ((0, 0.8, 0.0), (0, 0.85, 0.45)),
        "head": ((0, 0.95, 0.45), (0, 1.0, 1.0)),
        "tail.1": ((0, 0.88, -0.55), (0, 0.84, -0.85)), "tail.2": ((0, 0.84, -0.85), (0, 0.91, -1.17)),
    }
    for s, geo, n, _ in LEGS:
        hip, knee, ank = (mir(p, s) for p in geo)
        out[f"leg{n}.upper"] = (hip, knee)
        out[f"leg{n}.lower"] = (knee, ank)
    return out


H.build("n017", "quadruped", PALETTE, make, joints())
