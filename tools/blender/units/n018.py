"""Polar Bear (n018), quadruped: measured on artifacts/model-sheets/refs/n018/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n018.py -- <out.glb>

Scale read off the profile: 350 px per metre (sheet shown at 1932 px), nose at z=+1.0, ground at y=0.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "fur": 0xE4ECF4, "fur_dk": 0xC9D6E4, "fur_low": 0xB4C6D6, "muzzle": 0xA9B8C6, "paw": 0x3B3733,
    "claw": 0x25221F, "collar": 0x2B3447, "tag": 0xE8A02A, "nose": 0x1E1E22, "ice": 0x9CC8E6,
}

# hip, knee, ankle (x, y, z) per leg pair, measured on the profile and front/back views
FRONT = ((0.38, 0.95, -0.1), (0.37, 0.45, 0.03), (0.33, 0.1, 0.12))
HIND = ((0.4, 0.75, -0.9), (0.42, 0.42, -0.76), (0.4, 0.1, -0.68))
LEGS = ((1, FRONT, 1), (-1, FRONT, 2), (1, HIND, 3), (-1, HIND, 4))


def mir(p, s):
    return (s * p[0], p[1], p[2])


def trunk():
    H.frustum("spine.2", "fur", (0, 1.05, 0.5), (0, 1.18, -0.1), (0.3, 0.42), (0.56, 0.5))
    H.frustum("spine.1", "fur", (0, 1.18, -0.1), (0, 0.98, -0.6), (0.56, 0.5), (0.54, 0.44))
    H.frustum("spine.1", "fur", (0, 0.98, -0.6), (0, 0.8, -0.95), (0.54, 0.44), (0.52, 0.36))
    H.frustum("spine.1", "fur_dk", (0, 0.8, -0.95), (0, 0.76, -1.14), (0.5, 0.34), (0.3, 0.22))       # rump
    H.frustum("spine.1", "fur_dk", (0, 0.72, -0.1), (0, 0.65, -0.85), (0.42, 0.14), (0.4, 0.12), sides=4)   # belly
    H.frustum("tail.1", "fur", (0, 0.85, -1.08), (0, 0.84, -1.2), (0.11, 0.1), (0.07, 0.07), sides=4)
    for s in (-1, 1):        # ice shards on the back
        H.frustum("spine.2", "ice", (s * 0.4, 1.55, 0.0), (s * 0.5, 1.5, -0.2), (0.04, 0.025), (0.01, 0.01), sides=4)
        H.frustum("spine.1", "ice", (s * 0.5, 1.15, -0.72), (s * 0.55, 1.1, -0.9), (0.04, 0.025), (0.01, 0.01), sides=4)


def collar():
    for i in range(8):
        t0, t1 = (i - 0.5) * math.pi / 4, (i + 0.5) * math.pi / 4
        a = (0.33 * math.cos(t0), 1.05 + 0.33 * math.sin(t0), 0.45)
        b = (0.33 * math.cos(t1), 1.05 + 0.33 * math.sin(t1), 0.45)
        H.frustum("head", "collar", a, b, (0.07, 0.08), (0.07, 0.08), sides=4)


def head():
    H.frustum("head", "fur", (0, 1.0, 0.45), (0, 0.98, 0.82), (0.25, 0.24), (0.18, 0.18))
    H.frustum("head", "muzzle", (0, 0.95, 0.78), (0, 0.88, 1.0), (0.14, 0.13), (0.09, 0.09))
    H.frustum("head", "nose", (0, 0.9, 0.98), (0, 0.9, 1.03), (0.07, 0.06), (0.06, 0.05), sides=4)
    for s in (-1, 1):
        H.frustum("head", "fur_dk", (s * 0.16, 1.14, 0.6), (s * 0.19, 1.27, 0.58), (0.07, 0.05), (0.05, 0.04), sides=6)
    H.frustum("head", "tag", (0, 0.78, 0.58), (0, 0.5, 0.58), (0.06, 0.02), (0.06, 0.02), sides=4)
    collar()


def paw(bone, s, ank, hind):
    x, _, z = ank
    H.frustum(bone, "paw", (s * x, 0.22, z), (s * x, 0.05, z + 0.08), (0.17, 0.16), (0.21, 0.2))
    H.frustum(bone, "paw", (s * x, 0.07, z + 0.02), (s * x, 0.05, z + 0.24), (0.2, 0.08), (0.18, 0.06), sides=4)
    for k in (-1, 0, 1):
        H.frustum(bone, "claw", (s * (x + k * 0.07), 0.05, z + 0.22), (s * (x + k * 0.09), 0.03, z + 0.36), (0.03, 0.025), (0.008, 0.008), sides=4)


def leg(s, geo, n):
    hip, knee, ank = (mir(p, s) for p in geo)
    up, lo = f"leg{n}.upper", f"leg{n}.lower"
    hind = geo is HIND
    H.frustum(up, "fur", (hip[0], hip[1] + 0.2, hip[2]), (hip[0], hip[1] - 0.15, hip[2]), (0.24, 0.3), (0.26, 0.29) if hind else (0.25, 0.28))
    H.frustum(up, "fur", (hip[0], hip[1] - 0.1, hip[2]), knee, (0.25, 0.27), (0.16, 0.16))
    H.frustum(lo, "fur_low", knee, (ank[0], 0.25, ank[2]), (0.2, 0.19), (0.23, 0.22))
    paw(lo, s, geo[2], hind)


def make():
    trunk()
    head()
    for args in LEGS:
        leg(*args)


def joints():
    out = {
        "spine.1": ((0, 0.95, -0.95), (0, 1.15, -0.1)), "spine.2": ((0, 1.15, -0.1), (0, 1.1, 0.5)),
        "head": ((0, 1.1, 0.5), (0, 0.95, 1.0)),
        "tail.1": ((0, 0.85, -1.0), (0, 0.85, -1.2)), "tail.2": ((0, 0.85, -1.2), (0, 0.8, -1.35)),
    }
    for s, geo, n in LEGS:
        hip, knee, ank = (mir(p, s) for p in geo)
        out[f"leg{n}.upper"] = (hip, knee)
        out[f"leg{n}.lower"] = (knee, ank)
    return out


H.build("n018", "quadruped", PALETTE, make, joints())
