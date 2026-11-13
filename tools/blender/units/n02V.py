"""Quillboar (n02V), quadruped: measured on artifacts/model-sheets/refs/n02V/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n02V.py -- <out.glb>

Scale read off the profile: 400 px per metre, snout tip at z=+1.0, ground at y=0, shoulder hump 1.17 m.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "tan": 0xC9A06E, "tan_dk": 0xAA8660, "belly": 0xB59A78, "leg": 0x70503E, "hoof": 0x362B29,
    "red": 0x8A1A1E, "grey": 0x7C7C82, "snout": 0x9A8A74, "nose": 0x4A2F2F, "tusk": 0xEADFC4,
    "ear": 0x8A6850, "tail": 0xE8742A, "bell": 0xA8A08A,
}

# juntas (x, y, z) do ombro/quadril, joelho e tornozelo
FRONT = ((0.24, 0.82, 0.12), (0.22, 0.46, 0.15), (0.22, 0.12, 0.18))
HIND = ((0.25, 0.78, -0.62), (0.26, 0.42, -0.72), (0.24, 0.12, -0.66))
LEGS = ((1, FRONT, 1), (-1, FRONT, 2), (1, HIND, 3), (-1, HIND, 4))


def mir(p, s):
    return (s * p[0], p[1], p[2])


def trunk():
    H.frustum("spine.2", "tan", (0, 0.78, 0.4), (0, 0.8, -0.1), (0.3, 0.33), (0.4, 0.4))           # peito
    H.frustum("spine.2", "tan", (0, 0.95, 0.15), (0, 0.98, -0.2), (0.28, 0.2), (0.34, 0.2))        # corcova do ombro
    H.frustum("spine.1", "tan", (0, 0.78, -0.1), (0, 0.76, -0.5), (0.4, 0.38), (0.38, 0.36))        # barril
    H.frustum("spine.1", "tan", (0, 0.72, -0.45), (0, 0.66, -0.86), (0.37, 0.34), (0.26, 0.22))     # garupa
    H.frustum("spine.2", "belly", (0, 0.5, 0.25), (0, 0.5, -0.1), (0.3, 0.1), (0.34, 0.1), sides=4)
    H.frustum("spine.1", "belly", (0, 0.5, -0.1), (0, 0.5, -0.6), (0.34, 0.1), (0.28, 0.1), sides=4)
    H.frustum("spine.2", "red", (0, 1.08, 0.3), (0, 1.04, -0.1), (0.2, 0.1), (0.26, 0.1))          # crina vermelha
    H.frustum("spine.1", "red", (0, 1.04, -0.1), (0, 0.92, -0.6), (0.26, 0.1), (0.18, 0.08))


def quills():
    for z, base, top in ((0.52, 1.0, 1.22), (0.4, 1.08, 1.37), (0.26, 1.14, 1.42), (0.1, 1.16, 1.38), (0.0, 1.16, 1.3)):
        H.frustum("spine.2", "grey", (0, base - 0.05, z), (0, top, z - 0.14), (0.07, 0.04), (0.006, 0.006), sides=4)
    for s in (-1, 1):       # espinhos laterais da crina
        H.frustum("spine.2", "grey", (s * 0.12, 1.1, 0.3), (s * 0.2, 1.3, 0.2), (0.04, 0.03), (0.005, 0.005), sides=4)


def head():
    H.frustum("head", "tan", (0, 0.8, 0.38), (0, 0.72, 0.74), (0.31, 0.28), (0.22, 0.2))            # cranio
    H.frustum("head", "snout", (0, 0.62, 0.7), (0, 0.58, 1.0), (0.18, 0.14), (0.15, 0.14))          # focinho
    H.frustum("head", "nose", (0, 0.58, 0.98), (0, 0.58, 1.03), (0.13, 0.12), (0.11, 0.1), sides=6)
    H.frustum("head", "leg", (0, 0.5, 0.33), (0, 0.33, 0.33), (0.025, 0.025), (0.025, 0.025), sides=4)
    H.box("head", "bell", (0, 0.27, 0.33), (0.14, 0.17, 0.05))
    for s in (-1, 1):
        H.chain("head", "tusk", [(s * 0.14, 0.5, 0.8), (s * 0.18, 0.55, 0.95), (s * 0.15, 0.72, 1.0)],
                [(0.045, 0.045), (0.035, 0.035), (0.006, 0.006)])
        H.frustum("head", "ear", (s * 0.17, 0.95, 0.5), (s * 0.33, 1.08, 0.48), (0.08, 0.06), (0.02, 0.015), sides=4)
        H.frustum("head", "snout", (s * 0.12, 0.44, 0.45), (s * 0.12, 0.62, 0.48), (0.06, 0.06), (0.05, 0.05), sides=4)


def tail():
    H.frustum("tail.1", "tan_dk", (0, 0.86, -0.82), (0, 0.8, -0.95), (0.06, 0.06), (0.04, 0.04), sides=6)
    H.frustum("tail.2", "tail", (0, 0.8, -0.95), (0, 0.6, -0.98), (0.03, 0.03), (0.08, 0.025), sides=4)
    H.frustum("tail.2", "tail", (0, 0.62, -0.98), (0, 0.42, -0.97), (0.08, 0.025), (0.01, 0.01), sides=4)


def leg(s, geo, n):
    hip, knee, ank = (mir(p, s) for p in geo)
    up, lo = f"leg{n}.upper", f"leg{n}.lower"
    x, z = ank[0], ank[2]
    H.frustum(up, "tan", hip, knee, (0.2, 0.22), (0.14, 0.15))
    H.frustum(up, "tan", (s * (geo[0][0] + 0.06), 0.56, geo[0][2]), (s * (geo[0][0] + 0.06), 1.0, geo[0][2] - 0.02), (0.13, 0.22), (0.12, 0.2))
    H.frustum(lo, "leg", knee, (x, 0.14, z), (0.15, 0.15), (0.11, 0.12))
    H.frustum(lo, "hoof", (x, 0.15, z), (x, 0.0, z + 0.03), (0.11, 0.12), (0.15, 0.17))


def make():
    trunk()
    quills()
    head()
    tail()
    for args in LEGS:
        leg(*args)


def joints():
    out = {
        "spine.1": ((0, 0.9, -0.8), (0, 1.0, -0.1)), "spine.2": ((0, 1.0, -0.1), (0, 1.0, 0.35)),
        "head": ((0, 1.0, 0.35), (0, 0.8, 1.0)),
        "tail.1": ((0, 0.86, -0.82), (0, 0.8, -0.95)), "tail.2": ((0, 0.8, -0.95), (0, 0.55, -0.98)),
    }
    for s, geo, n in LEGS:
        hip, knee, ank = (mir(p, s) for p in geo)
        out[f"leg{n}.upper"] = (hip, knee)
        out[f"leg{n}.lower"] = (knee, ank)
    return out


H.build("n02V", "quadruped", PALETTE, make, joints())
