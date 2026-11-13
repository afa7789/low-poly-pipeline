"""Ancient Bear (n02B), quadruped: measured on artifacts/model-sheets/refs/n02B/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n02B.py -- <out.glb>

Scale read off the profile: 350 px per metre (sheet shown at 1932 px), nose at z=+1.0, ground at y=0.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "fur": 0xB98A3C, "fur_dk": 0x8E6A30, "mane": 0x3E2D28, "moss": 0x6B7F3E, "tan": 0xD2B08A,
    "fang": 0xF0E4BE, "antler": 0x9B3B30, "crest": 0xB02448, "eye": 0xF5A020, "nose": 0x1A1214,
}

FRONT = ((0.42, 0.95, -0.05), (0.42, 0.5, -0.02), (0.36, 0.1, 0.0))
HIND = ((0.42, 0.95, -0.95), (0.42, 0.5, -0.95), (0.4, 0.1, -0.95))
LEGS = ((1, FRONT, 1), (-1, FRONT, 2), (1, HIND, 3), (-1, HIND, 4))
# mane spikes: bone, z, top of the back there, height
SPIKES = (("spine.2", 0.15, 1.44, 0.25), ("spine.2", -0.05, 1.47, 0.3), ("spine.1", -0.3, 1.45, 0.3),
          ("spine.1", -0.5, 1.42, 0.28), ("spine.1", -0.7, 1.38, 0.25), ("spine.1", -0.9, 1.32, 0.2),
          ("spine.1", -1.1, 1.26, 0.16))


def mir(p, s):
    return (s * p[0], p[1], p[2])


def mane():
    for bone, z, top, h in SPIKES:
        H.frustum(bone, "mane", (0, top - 0.08, z), (0, top + h * 0.8, z - 0.08 - h * 0.4), (0.12, 0.1), (0.01, 0.01), sides=4)
    H.frustum("spine.1", "moss", (0, 1.36, -0.15), (0, 1.3, -0.6), (0.5, 0.2), (0.5, 0.2), sides=6)
    H.frustum("spine.1", "moss", (0, 1.2, -0.95), (0, 1.14, -1.25), (0.44, 0.2), (0.4, 0.2), sides=6)


def trunk():
    H.frustum("spine.2", "fur", (0, 0.98, 0.35), (0, 1.0, -0.25), (0.36, 0.52), (0.62, 0.55))
    H.frustum("spine.1", "fur", (0, 1.0, -0.25), (0, 0.95, -0.8), (0.62, 0.55), (0.6, 0.5))
    H.frustum("spine.1", "fur", (0, 0.95, -0.8), (0, 0.88, -1.25), (0.6, 0.5), (0.52, 0.44))
    H.frustum("spine.1", "fur", (0, 0.88, -1.25), (0, 0.85, -1.36), (0.52, 0.44), (0.32, 0.3))
    H.frustum("spine.1", "mane", (0, 0.62, 0.1), (0, 0.55, -1.0), (0.45, 0.1), (0.45, 0.1), sides=4)
    H.frustum("spine.2", "eye", (0, 0.78, 0.5), (0, 0.6, 0.46), (0.04, 0.012), (0.04, 0.012), sides=4)
    H.frustum("tail.1", "fur", (0, 0.88, -1.3), (0, 0.84, -1.45), (0.14, 0.13), (0.1, 0.1), sides=4)
    H.frustum("tail.2", "fur_dk", (0, 0.84, -1.4), (0, 0.8, -1.58), (0.1, 0.1), (0.02, 0.02), sides=4)
    mane()


def antlers(s):
    pts = [(s * 0.15, 1.35, 0.5), (s * 0.28, 1.65, 0.4), (s * 0.42, 1.85, 0.2), (s * 0.52, 2.02, -0.05)]
    H.chain("head", "antler", pts, ((0.07, 0.07), (0.06, 0.06), (0.045, 0.045), (0.02, 0.02)), sides=6)
    for p, q in ((pts[1], (s * 0.2, 1.9, 0.5)), (pts[2], (s * 0.34, 2.1, 0.32)), (pts[2], (s * 0.62, 1.95, 0.25))):
        H.frustum("head", "antler", p, q, (0.04, 0.04), (0.01, 0.01), sides=4)


def head():
    H.frustum("head", "fur", (0, 1.08, 0.3), (0, 1.08, 0.7), (0.3, 0.28), (0.22, 0.22))
    H.frustum("head", "tan", (0, 1.02, 0.65), (0, 0.96, 1.0), (0.15, 0.13), (0.1, 0.09))
    H.frustum("head", "nose", (0, 0.96, 0.98), (0, 0.96, 1.03), (0.07, 0.06), (0.06, 0.05), sides=4)
    H.frustum("head", "mane", (0, 0.84, 0.5), (0, 0.8, 0.9), (0.13, 0.05), (0.1, 0.04), sides=4)     # open lower jaw
    for s in (-1, 1):
        H.frustum("head", "fur_dk", (s * 0.2, 1.24, 0.42), (s * 0.24, 1.38, 0.4), (0.09, 0.07), (0.07, 0.05), sides=6)
        H.frustum("head", "eye", (s * 0.12, 1.14, 0.66), (s * 0.12, 1.14, 0.72), (0.045, 0.03), (0.04, 0.025), sides=4)
        H.frustum("head", "fang", (s * 0.09, 0.96, 0.9), (s * 0.09, 0.68, 0.82), (0.035, 0.035), (0.008, 0.008), sides=4)
        antlers(s)
    for z, tip in ((0.62, 1.45), (0.52, 1.55), (0.42, 1.45)):
        H.frustum("head", "crest", (0, 1.24, z), (0, tip, z - 0.1), (0.08, 0.06), (0.008, 0.008), sides=4)


def paw(bone, s, ank, reach):
    x, _, z = ank
    H.frustum(bone, "fur_dk", (s * x, 0.24, z), (s * x, 0.05, z + 0.08), (0.18, 0.17), (0.23, 0.21))
    H.frustum(bone, "fur_dk", (s * x, 0.07, z + 0.02), (s * x, 0.05, z + reach), (0.21, 0.08), (0.21, 0.06), sides=4)
    for k in (-1, 0, 1):
        H.frustum(bone, "fang", (s * (x + k * 0.08), 0.05, z + reach - 0.02), (s * (x + k * 0.1), 0.03, z + reach + 0.14), (0.035, 0.03), (0.008, 0.008), sides=4)


def leg(s, geo, n):
    hip, knee, ank = (mir(p, s) for p in geo)
    up, lo = f"leg{n}.upper", f"leg{n}.lower"
    H.frustum(up, "fur", (hip[0], hip[1] + 0.2, hip[2]), (hip[0], hip[1] - 0.15, hip[2]), (0.26, 0.31), (0.28, 0.3))
    H.frustum(up, "fur", (hip[0], hip[1] - 0.1, hip[2]), knee, (0.27, 0.28), (0.18, 0.18))
    H.frustum(lo, "fur", knee, (ank[0], 0.25, ank[2]), (0.2, 0.2), (0.24, 0.23))
    paw(lo, s, geo[2], 0.2)


def make():
    trunk()
    head()
    for args in LEGS:
        leg(*args)


def joints():
    out = {
        "spine.1": ((0, 0.92, -1.05), (0, 1.0, -0.1)), "spine.2": ((0, 1.0, -0.1), (0, 1.05, 0.4)),
        "head": ((0, 1.05, 0.4), (0, 0.98, 1.0)),
        "tail.1": ((0, 0.88, -1.2), (0, 0.84, -1.4)), "tail.2": ((0, 0.84, -1.4), (0, 0.8, -1.58)),
    }
    for s, geo, n in LEGS:
        hip, knee, ank = (mir(p, s) for p in geo)
        out[f"leg{n}.upper"] = (hip, knee)
        out[f"leg{n}.lower"] = (knee, ank)
    return out


H.build("n02B", "quadruped", PALETTE, make, joints())
