"""Lesser Hydra (n01R), hydra family: a coiled black serpent with two necks and a bronze band, measured on
artifacts/model-sheets/refs/n01R/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n01R.py -- <out.glb>

Scale read off the profile: 175 px per metre, coil centre at z=0, ground at y=0. The coil is a spiral of
frusta on spine.1/spine.2, the chest column on spine.3/4, each head rides its neck's last bone.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {"black": 0x2A2A2D, "black_lt": 0x38383C, "band": 0x5F6E50, "teal": 0x4B8F86, "cyan": 0x34EAD2, "grey": 0x4A4A4E}

# (x of the neck, four points: base, bend, bend, head base)
NECKS = (
    ("neck1", ((0.12, 1.15, -0.05), (0.2, 1.55, -0.07), (0.3, 1.85, -0.02), (0.32, 1.98, 0.12))),
    ("neck3", ((-0.12, 1.15, -0.05), (-0.2, 1.55, -0.07), (-0.3, 1.85, -0.02), (-0.32, 1.98, 0.12))),
)
NECK_R = ((0.2, 0.19), (0.18, 0.17), (0.16, 0.15), (0.15, 0.14))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def add(a, b, k=1.0):
    return tuple(x + k * y for x, y in zip(a, b))


def unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return tuple(x / n for x in v)


def coil():
    """Two turns of a fat spiral winding inwards, the tail tip flicking up at the back."""
    steps = 20
    prev = None
    for i in range(steps + 1):
        t = i / steps
        a = math.radians(200 + 640 * t)
        rad = 0.7 - 0.36 * t
        p = (rad * math.sin(a), 0.32 + 0.5 * t + 0.4 * t ** 8, rad * math.cos(a))
        r = 0.33 - 0.14 * t ** 1.5
        if prev:
            q = add(p, unit(sub(p, prev[0])), 0.05)
            H.frustum("spine.1" if i <= 12 else "spine.2", "black", prev[0], q, (prev[1], prev[1] * 0.95), (r, r * 0.95))
        prev = (p, r)


def column():
    H.frustum("spine.2", "black", (0, 0.6, -0.05), (0, 0.9, -0.05), (0.44, 0.4), (0.38, 0.34))
    H.frustum("spine.3", "black", (0, 0.8, -0.05), (0, 1.1, -0.05), (0.36, 0.34), (0.3, 0.28))


def band():
    H.frustum("spine.4", "band", (0, 0.92, -0.05), (0, 1.22, -0.05), (0.44, 0.36), (0.44, 0.36))
    H.frustum("spine.4", "band", (0, 1.07, 0.28), (0, 1.07, 0.37), (0.17, 0.17), (0.17, 0.17), sides=8)
    H.frustum("spine.4", "black", (0, 1.15, -0.1), (0, 1.4, -0.08), (0.28, 0.24), (0.22, 0.2))


def head(bone, p):
    f = unit((0, -0.1, 1))

    def at(t, h=0.0, w=0.0):
        return (p[0] + w, p[1] + f[1] * t + h, p[2] + f[2] * t)
    H.frustum(bone, "black_lt", at(-0.05), at(0.3), (0.21, 0.18), (0.16, 0.13), sides=6)
    H.frustum(bone, "black_lt", at(0.25, 0.0), at(0.6, -0.03), (0.17, 0.12), (0.09, 0.07), sides=6)
    H.frustum(bone, "cyan", at(0.15, -0.1), at(0.55, -0.12), (0.12, 0.05), (0.07, 0.04), sides=4)
    H.frustum(bone, "grey", at(0.05, -0.15), at(0.52, -0.25), (0.15, 0.07), (0.08, 0.05), sides=4)
    for k in (-1, 1):       # crest spikes flaring off the back of the skull
        H.frustum(bone, "black", at(0.0, 0.1, k * 0.12), at(-0.1, 0.28, k * 0.2), (0.05, 0.05), (0.01, 0.01), sides=4)
    H.frustum(bone, "black", at(0.0, 0.14), at(-0.12, 0.34), (0.05, 0.05), (0.01, 0.01), sides=4)
    for sx in (-1, 1):
        H.frustum(bone, "cyan", at(0.12, 0.07, sx * 0.18), at(0.2, 0.07, sx * 0.18), (0.035, 0.035), (0.035, 0.035), sides=4)


def curve(pts, i, t):
    p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
    return tuple(0.5 * (2 * b + (c - a) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (3 * b - a - 3 * c + d) * t ** 3)
                 for a, b, c, d in zip(p0, p1, p2, p3))


def neck(bone, pts):
    for i in range(3):
        s = [curve(pts, i, t) for t in (0.0, 0.5, 1.0)]
        for j in range(2):
            ra, rb = (tuple(NECK_R[i][k] + (NECK_R[i + 1][k] - NECK_R[i][k]) * w for k in (0, 1)) for w in (j / 2, (j + 1) / 2))
            H.frustum(f"{bone}.{i + 1}", "black", s[j], add(s[j + 1], unit(sub(s[j + 1], s[j])), 0.06), ra, rb)
    head(f"{bone}.3", pts[3])


def make():
    coil()
    column()
    band()
    for n in NECKS:
        neck(*n)


def joints():
    out = {
        "spine.1": ((0, 0.3, -0.6), (0, 0.3, -0.3)), "spine.2": ((0, 0.35, -0.3), (0, 0.6, -0.1)),
        "spine.3": ((0, 0.6, -0.1), (0, 1.0, -0.05)), "spine.4": ((0, 1.0, -0.05), (0, 1.15, -0.05)),
    }
    for bone, pts in NECKS:
        for i in range(3):
            out[f"{bone}.{i + 1}"] = (pts[i], pts[i + 1])
    return out


H.build("n01R", "hydra", PALETTE, make, joints())
