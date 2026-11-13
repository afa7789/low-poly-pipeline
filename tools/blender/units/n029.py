"""Bear (n029), quadruped: measured on artifacts/model-sheets/refs/n029/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n029.py -- <out.glb>

Scale read off the profile: 350 px per metre (sheet shown at 1932 px), nose at z=+1.0, ground at y=0.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "fur": 0xB88334, "fur_dk": 0x8E6232, "mane": 0x5E3B1E, "tan": 0xD2A872, "fang": 0xF0E4BE,
    "red": 0xC42B2F, "eye": 0xF0A020, "nose": 0x1A1214, "belly": 0x7A5530,
}

FRONT = ((0.42, 0.95, 0.0), (0.4, 0.5, 0.1), (0.38, 0.1, 0.2))
HIND = ((0.4, 0.95, -0.75), (0.42, 0.5, -0.6), (0.4, 0.1, -0.72))
LEGS = ((1, FRONT, 1), (-1, FRONT, 2), (1, HIND, 3), (-1, HIND, 4))


def mir(p, s):
    return (s * p[0], p[1], p[2])


def mane():
    for bone, z, top, h in (("spine.2", 0.3, 1.4, 0.2), ("spine.2", 0.1, 1.44, 0.26), ("spine.1", -0.1, 1.45, 0.28),
                            ("spine.1", -0.3, 1.38, 0.24), ("spine.1", -0.5, 1.28, 0.2), ("spine.1", -0.7, 1.18, 0.16)):
        H.frustum(bone, "mane", (0, top - 0.08, z), (0, top + h * 0.55, z - 0.06 - h * 0.3), (0.1, 0.1), (0.01, 0.01), sides=4)
    for s in (-1, 1):        # shaggy shoulder fur
        H.frustum("spine.2", "fur_dk", (s * 0.45, 1.1, 0.25), (s * 0.7, 0.95, 0.05), (0.14, 0.25), (0.1, 0.18), sides=6)


def trunk():
    H.frustum("spine.2", "fur", (0, 0.98, 0.5), (0, 1.0, -0.1), (0.34, 0.46), (0.62, 0.52))
    H.frustum("spine.1", "fur", (0, 1.0, -0.1), (0, 0.9, -0.55), (0.62, 0.52), (0.58, 0.44))
    H.frustum("spine.1", "fur", (0, 0.9, -0.55), (0, 0.78, -0.95), (0.58, 0.44), (0.5, 0.36))
    H.frustum("spine.1", "fur", (0, 0.78, -0.95), (0, 0.74, -1.06), (0.5, 0.36), (0.32, 0.25))
    H.frustum("spine.1", "belly", (0, 0.62, -0.05), (0, 0.55, -0.8), (0.42, 0.12), (0.4, 0.1), sides=4)
    H.frustum("tail.1", "fur", (0, 0.85, -1.0), (0, 0.78, -1.22), (0.14, 0.13), (0.1, 0.1), sides=4)
    H.frustum("tail.2", "fur", (0, 0.78, -1.2), (0, 0.6, -1.4), (0.1, 0.1), (0.02, 0.02), sides=4)
    mane()


def crest():
    for z, tip in ((0.66, 1.3), (0.56, 1.4), (0.46, 1.3)):
        H.frustum("head", "red", (0, 1.12, z), (0, tip, z - 0.1), (0.08, 0.06), (0.008, 0.008), sides=4)


def head():
    H.frustum("head", "fur", (0, 0.98, 0.42), (0, 0.98, 0.8), (0.32, 0.3), (0.23, 0.22))
    H.frustum("head", "tan", (0, 0.93, 0.76), (0, 0.84, 1.0), (0.15, 0.13), (0.1, 0.09))
    H.frustum("head", "nose", (0, 0.88, 0.98), (0, 0.88, 1.03), (0.07, 0.06), (0.06, 0.05), sides=4)
    for s in (-1, 1):
        H.frustum("head", "fur_dk", (s * 0.2, 1.12, 0.52), (s * 0.24, 1.26, 0.5), (0.09, 0.07), (0.07, 0.05), sides=6)
        H.frustum("head", "eye", (s * 0.12, 1.04, 0.76), (s * 0.12, 1.04, 0.82), (0.045, 0.03), (0.04, 0.025), sides=4)
        H.frustum("head", "fang", (s * 0.09, 0.84, 0.9), (s * 0.09, 0.56, 0.78), (0.035, 0.035), (0.008, 0.008), sides=4)
    crest()


def paw(bone, s, ank, reach):
    x, _, z = ank
    H.frustum(bone, "fur_dk", (s * x, 0.24, z), (s * x, 0.05, z + 0.08), (0.17, 0.16), (0.22, 0.2))
    H.frustum(bone, "fur_dk", (s * x, 0.07, z + 0.02), (s * x, 0.05, z + reach), (0.2, 0.08), (0.2, 0.06), sides=4)
    for k in (-1, 0, 1):
        H.frustum(bone, "fang", (s * (x + k * 0.08), 0.05, z + reach - 0.02), (s * (x + k * 0.1), 0.03, z + reach + 0.14), (0.035, 0.03), (0.008, 0.008), sides=4)


def leg(s, geo, n):
    hip, knee, ank = (mir(p, s) for p in geo)
    up, lo = f"leg{n}.upper", f"leg{n}.lower"
    hind = geo is HIND
    H.frustum(up, "fur", (hip[0], hip[1] + 0.2, hip[2]), (hip[0], hip[1] - 0.15, hip[2]), (0.26, 0.3), (0.27, 0.29))
    H.frustum(up, "fur", (hip[0], hip[1] - 0.1, hip[2]), knee, (0.26, 0.27), (0.17, 0.17))
    H.frustum(lo, "fur" if hind else "fur_dk", knee, (ank[0], 0.25, ank[2]), (0.2, 0.19), (0.23, 0.22))
    paw(lo, s, geo[2], 0.24)


def make():
    trunk()
    head()
    for args in LEGS:
        leg(*args)


def joints():
    out = {
        "spine.1": ((0, 0.9, -0.95), (0, 1.0, -0.1)), "spine.2": ((0, 1.0, -0.1), (0, 1.0, 0.5)),
        "head": ((0, 1.0, 0.5), (0, 0.9, 1.0)),
        "tail.1": ((0, 0.85, -1.0), (0, 0.78, -1.22)), "tail.2": ((0, 0.78, -1.22), (0, 0.6, -1.4)),
    }
    for s, geo, n in LEGS:
        hip, knee, ank = (mir(p, s) for p in geo)
        out[f"leg{n}.upper"] = (hip, knee)
        out[f"leg{n}.lower"] = (knee, ank)
    return out


H.build("n029", "quadruped", PALETTE, make, joints())
