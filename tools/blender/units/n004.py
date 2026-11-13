"""Suumpmolk (n004), quadruped: measured on artifacts/model-sheets/refs/n004/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n004.py -- <out.glb>

Scale read off the profile: 500 px per metre, nose at z=+1.0, ground at y=0. A low sprawling swamp lizard.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "teal": 0x4B7E74, "teal_dk": 0x3A5D5E, "tan": 0xA89070, "orange": 0xD9702F, "orange_dk": 0xBF5A28,
    "lime": 0xB8D04A, "cream": 0xF0DDB8, "eye": 0x40D8F0, "mouth": 0x2E3F3C,
}

# juntas (metros): (x, y, z) do ombro/quadril, cotovelo/joelho e pulso/tornozelo
FRONT = ((0.3, 0.38, 0.25), (0.42, 0.2, 0.2), (0.36, 0.08, 0.3))
HIND = ((0.3, 0.36, -0.34), (0.42, 0.17, -0.2), (0.38, 0.08, -0.3))
LEGS = ((1, FRONT, 1, 0.55), (-1, FRONT, 2, 0.55), (1, HIND, 3, 0.0), (-1, HIND, 4, 0.0))   # lado, perna, numero, ponta dos dedos


def mir(p, s):
    return (s * p[0], p[1], p[2])


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def plate(bone, z, top, lean=0.12):
    """Dorsal fin: dark base, cream tip."""
    base, mid = (0, 0.56, z), (0, 0.56 + (top - 0.56) * 0.55, z - lean * 0.5)
    H.frustum(bone, "teal_dk", base, mid, (0.05, 0.1), (0.03, 0.05), sides=4)
    H.frustum(bone, "cream", mid, (0, top, z - lean), (0.03, 0.05), (0.006, 0.006), sides=4)


def spikes():
    plate("spine.2", 0.27, 0.86)
    plate("spine.1", 0.0, 0.77)
    plate("spine.1", -0.23, 0.68)
    plate("spine.1", -0.46, 0.57, 0.1)
    for s in (-1, 1):        # espinhos dos ombros apontando para fora
        H.frustum("spine.2", "teal_dk", (s * 0.18, 0.55, 0.22), (s * 0.3, 0.7, 0.18), (0.05, 0.06), (0.02, 0.025), sides=4)
        H.frustum("spine.2", "cream", (s * 0.3, 0.7, 0.18), (s * 0.38, 0.78, 0.15), (0.02, 0.025), (0.005, 0.005), sides=4)


def trunk():
    H.frustum("spine.2", "teal", (0, 0.42, 0.42), (0, 0.44, 0.0), (0.2, 0.15), (0.3, 0.18))
    H.frustum("spine.2", "teal", (0, 0.44, 0.3), (0, 0.46, 0.55), (0.26, 0.2), (0.17, 0.15))     # pescoco grosso
    H.frustum("spine.1", "teal", (0, 0.44, 0.0), (0, 0.42, -0.42), (0.3, 0.18), (0.26, 0.16))
    H.frustum("spine.1", "teal", (0, 0.42, -0.35), (0, 0.4, -0.55), (0.27, 0.16), (0.2, 0.13))
    H.frustum("spine.2", "tan", (0, 0.31, 0.35), (0, 0.27, -0.05), (0.16, 0.09), (0.22, 0.09), sides=6)    # barriga
    H.frustum("spine.1", "tan", (0, 0.27, -0.05), (0, 0.28, -0.45), (0.22, 0.09), (0.17, 0.08), sides=6)
    H.frustum("tail.1", "teal", (0, 0.38, -0.5), (0, 0.36, -1.0), (0.2, 0.15), (0.09, 0.08))
    H.frustum("tail.1", "tan", (0, 0.28, -0.5), (0, 0.3, -1.0), (0.1, 0.05), (0.04, 0.03), sides=4)
    H.frustum("tail.2", "teal", (0, 0.36, -1.0), (0, 0.33, -1.57), (0.09, 0.08), (0.01, 0.01))
    spikes()


def frill():
    for i in range(8):       # gola laranja: anel de 8 cunhas em volta do pescoco
        t0, t1 = (i - 0.5) * math.pi / 4, (i + 0.5) * math.pi / 4
        a = (0.22 * math.cos(t0), 0.48 + 0.22 * math.sin(t0), 0.45)
        b = (0.22 * math.cos(t1), 0.48 + 0.22 * math.sin(t1), 0.45)
        H.frustum("head", "orange" if i % 2 else "orange_dk", a, b, (0.06, 0.09), (0.06, 0.09), sides=4)


def head():
    H.frustum("head", "teal", (0, 0.48, 0.5), (0, 0.45, 0.99), (0.17, 0.15), (0.075, 0.06))
    H.frustum("head", "teal", (0, 0.46, 0.7), (0, 0.44, 1.0), (0.12, 0.1), (0.07, 0.055))
    H.frustum("head", "mouth", (0, 0.34, 0.52), (0, 0.35, 0.96), (0.13, 0.04), (0.065, 0.03), sides=6)      # mandibula
    H.frustum("head", "lime", (0, 0.3, 0.78), (0, 0.25, 0.62), (0.09, 0.07), (0.14, 0.1), sides=8)         # papo
    H.frustum("head", "lime", (0, 0.25, 0.62), (0, 0.27, 0.48), (0.14, 0.1), (0.1, 0.08), sides=8)
    for s in (-1, 1):
        H.frustum("head", "eye", (s * 0.1, 0.54, 0.7), (s * 0.18, 0.55, 0.66), (0.03, 0.03), (0.035, 0.03), sides=6)
        for z in (0.62, 0.74, 0.86):
            H.frustum("head", "cream", (s * 0.1, 0.38, z), (s * 0.1, 0.31, z + 0.02), (0.02, 0.02), (0.005, 0.005), sides=4)
    frill()


def paw(bone, s, p, toe_z):
    x, _, z = p
    H.frustum(bone, "teal", (s * x, 0.16, z - 0.02), (s * x, 0.03, z + 0.08), (0.09, 0.09), (0.13, 0.08), sides=6)
    for k in (-1, 0, 1):     # 3 dedos longos abrindo para frente e para fora
        end = (s * (x + k * 0.16), 0.025, toe_z - abs(k) * 0.07)
        H.frustum(bone, "teal_dk", (s * (x + k * 0.05), 0.045, z + 0.07), end, (0.05, 0.035), (0.025, 0.02), sides=4)
        tip = (s * (x + k * 0.2), 0.02, toe_z - abs(k) * 0.07 + 0.07)
        H.frustum(bone, "cream", end, tip, (0.025, 0.02), (0.004, 0.004), sides=4)


def leg(s, geo, n, toe_z):
    hip, knee, ank = (mir(p, s) for p in geo)
    up, lo = f"leg{n}.upper", f"leg{n}.lower"
    top = (hip[0], hip[1] + 0.12, hip[2])
    mid = lerp(hip, knee, 0.4)
    H.chain(up, "teal", [top, mid, knee], [(0.15, 0.17), (0.2, 0.2), (0.1, 0.1)])
    mid2 = lerp(knee, ank, 0.45)
    foot = (ank[0], 0.12, ank[2])
    H.chain(lo, "teal_dk" if geo is HIND else "teal", [knee, mid2, foot], [(0.1, 0.1), (0.075, 0.08), (0.09, 0.09)])
    paw(lo, s, geo[2], toe_z)


def make():
    trunk()
    head()
    for args in LEGS:
        leg(*args)


def joints():
    out = {
        "spine.1": ((0, 0.42, -0.42), (0, 0.44, 0.0)), "spine.2": ((0, 0.44, 0.0), (0, 0.45, 0.5)),
        "head": ((0, 0.46, 0.48), (0, 0.45, 1.0)),
        "tail.1": ((0, 0.38, -0.5), (0, 0.36, -1.0)), "tail.2": ((0, 0.36, -1.0), (0, 0.33, -1.57)),
    }
    for s, geo, n, _ in LEGS:
        hip, knee, ank = (mir(p, s) for p in geo)
        out[f"leg{n}.upper"] = (hip, knee)
        out[f"leg{n}.lower"] = (knee, ank)
    return out


H.build("n004", "quadruped", PALETTE, make, joints())
