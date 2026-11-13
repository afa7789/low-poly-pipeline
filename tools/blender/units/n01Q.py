"""Hydra (n01Q), hydra family: a coiled black serpent with three necks, measured on
artifacts/model-sheets/refs/n01Q/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n01Q.py -- <out.glb>

Scale read off the profile: 200 px per metre, coil centre at z=0, ground at y=0. The coil is a spiral of
frusta on spine.1/spine.2, the chest column on spine.3/4, each head rides its neck's last bone.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {"black": 0x2A2A2D, "black_lt": 0x38383C, "teal": 0x4B8F86, "cyan": 0x34EAD2, "grey": 0x4A4A4E}

# (x of the neck, four points: base, bend, bend, head base)
NECKS = (
    ("neck1", ((0.4, 1.25, -0.1), (0.5, 1.65, -0.18), (0.55, 1.95, -0.1), (0.55, 1.95, 0.3))),
    ("neck2", ((0.0, 1.25, -0.1), (0.0, 1.7, -0.2), (0.0, 2.1, -0.12), (0.0, 2.15, 0.28))),
    ("neck3", ((-0.4, 1.25, -0.1), (-0.5, 1.6, -0.16), (-0.55, 1.8, -0.05), (-0.55, 1.75, 0.38))),
)
NECK_R = ((0.2, 0.19), (0.17, 0.16), (0.15, 0.14), (0.14, 0.13))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def add(a, b, k=1.0):
    return tuple(x + k * y for x, y in zip(a, b))


def unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return tuple(x / n for x in v)


def coil():
    """A spiral of fat segments winding inwards, the tail tip flicking up at the back."""
    steps = 14
    prev = None
    for i in range(steps + 1):
        t = i / steps
        a = math.radians(200 + 400 * t)
        rad = 0.62 - 0.3 * t
        p = (rad * math.sin(a), 0.27 + 0.3 * t + (0.35 * t ** 4), rad * math.cos(a) - 0.0)
        r = 0.31 - 0.15 * t ** 1.5
        if prev:
            bone = "spine.1" if i <= 8 else "spine.2"
            q = add(p, unit(sub(p, prev[0])), 0.05)
            H.frustum(bone, "black", prev[0], q, (prev[1], prev[1] * 0.95), (r, r * 0.95))
        prev = (p, r)


def column():
    H.frustum("spine.2", "black", (0, 0.45, -0.12), (0, 0.8, -0.14), (0.4, 0.34), (0.36, 0.32))
    H.frustum("spine.3", "black", (0, 0.75, -0.14), (0, 1.1, -0.12), (0.36, 0.32), (0.32, 0.28))
    H.frustum("spine.4", "black", (0, 1.05, -0.12), (0, 1.35, -0.1), (0.32, 0.28), (0.34, 0.24))


def plates():
    for i, (y, w) in enumerate(((1.12, 0.17), (0.92, 0.15), (0.72, 0.13))):     # V of chest scales
        H.frustum("spine.3" if i else "spine.4", "teal", (0, y + 0.08, 0.14), (0, y - 0.1, 0.2), (w, 0.04), (w * 0.6, 0.05), sides=4)
    for y, z in ((1.15, -0.34), (0.95, -0.4), (0.75, -0.44), (0.55, -0.5)):         # back scales, a staircase
        H.frustum("spine.3", "teal", (0, y + 0.12, z + 0.04), (0, y - 0.08, z - 0.1), (0.2, 0.06), (0.14, 0.07), sides=4)
    for k in range(6):                                                              # plates on the coil
        a = math.radians(30 + k * 55)
        c = (0.62 * math.sin(a), 0.56, 0.62 * math.cos(a))
        d = (0.7 * math.sin(a), 0.4, 0.7 * math.cos(a))
        H.frustum("spine.1", "teal", c, d, (0.12, 0.05), (0.1, 0.06), sides=4)


def head(bone, p):
    f = unit((0, -0.2, 1))

    def at(t, h=0.0, w=0.0):
        return (p[0] + w, p[1] + f[1] * t + h, p[2] + f[2] * t)
    H.frustum(bone, "black_lt", at(-0.05), at(0.3), (0.21, 0.18), (0.16, 0.13), sides=6)
    H.frustum(bone, "black_lt", at(0.25, 0.0), at(0.6, -0.03), (0.17, 0.12), (0.09, 0.07), sides=6)
    H.frustum(bone, "cyan", at(0.15, -0.1), at(0.55, -0.12), (0.12, 0.05), (0.07, 0.04), sides=4)
    H.frustum(bone, "grey", at(0.05, -0.15), at(0.52, -0.25), (0.15, 0.07), (0.08, 0.05), sides=4)
    H.frustum(bone, "teal", at(-0.05, 0.12), at(0.2, 0.2), (0.07, 0.05), (0.03, 0.03), sides=4)
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
    x = pts[0][0]
    H.frustum(f"{bone}.1", "teal", (x, 1.3, -0.1), (x, 1.44, -0.11), (0.26, 0.24), (0.26, 0.24), sides=8)    # cuff
    head(f"{bone}.3", pts[3])


def make():
    coil()
    column()
    plates()
    for n in NECKS:
        neck(*n)


def joints():
    out = {
        "spine.1": ((0, 0.3, -0.6), (0, 0.3, -0.3)), "spine.2": ((0, 0.35, -0.3), (0, 0.6, -0.2)),
        "spine.3": ((0, 0.6, -0.2), (0, 1.0, -0.15)), "spine.4": ((0, 1.0, -0.15), (0, 1.3, -0.1)),
    }
    for bone, pts in NECKS:
        for i in range(3):
            out[f"{bone}.{i + 1}"] = (pts[i], pts[i + 1])
    return out


H.build("n01Q", "hydra", PALETTE, make, joints())
