"""Ancient Hydra (n01P), hydra family: measured on artifacts/model-sheets/refs/n01P/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n01P.py -- <out.glb>

Scale read off the profile: 270 px per metre, front paws at z=0, ground at y=0, tail tip at z=-3.55.
The family has no leg or head bones: legs ride the spine bones, each head rides its neck's last bone.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "teal": 0x557E88, "teal_dk": 0x3E6070, "brown": 0x8C6048, "tan": 0xCDB088, "belly": 0xB39A7A,
    "orange": 0xE07A3A, "lime": 0xB8D44A, "magenta": 0xA33B7E, "cyan": 0x50E4F4, "cream": 0xF2DFB8,
}

# necks: (side, four points: base, bend, bend, head base) -- one segment per neck bone
NECKS = (
    (1, "neck1", ((0.3, 0.95, 0.0), (0.5, 1.5, -0.05), (0.7, 2.0, 0.0), (0.8, 2.0, 0.4))),
    (0, "neck2", ((0.0, 0.95, 0.05), (0.0, 1.6, -0.12), (0.0, 2.2, -0.1), (0.0, 2.3, 0.28))),
    (-1, "neck3", ((-0.3, 0.95, 0.0), (-0.5, 1.45, -0.1), (-0.75, 1.9, 0.2), (-0.85, 1.8, 0.8))),
)
NECK_R = ((0.26, 0.24), (0.22, 0.2), (0.19, 0.18), (0.17, 0.16))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def add(a, b, k=1.0):
    return tuple(x + k * y for x, y in zip(a, b))


def unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return tuple(x / n for x in v)


def trunk():
    H.frustum("spine.4", "teal", (0, 0.78, 0.4), (0, 0.8, -0.45), (0.46, 0.4), (0.62, 0.48))
    H.frustum("spine.3", "teal", (0, 0.8, -0.4), (0, 0.78, -0.95), (0.62, 0.48), (0.56, 0.44))
    H.frustum("spine.2", "teal", (0, 0.76, -0.9), (0, 0.68, -1.55), (0.56, 0.44), (0.4, 0.34))
    H.frustum("spine.4", "belly", (0, 0.42, 0.25), (0, 0.44, -0.5), (0.3, 0.12), (0.34, 0.12), sides=6)
    H.frustum("spine.3", "belly", (0, 0.44, -0.5), (0, 0.44, -1.0), (0.34, 0.12), (0.3, 0.1), sides=6)
    H.box("spine.4", "lime", (0, 0.68, 0.31), (0.55, 0.4, 0.06))
    H.chain("spine.1", "teal", ((0, 0.66, -1.45), (0, 0.64, -2.1), (0, 0.62, -2.8), (0, 0.6, -3.2), (0, 0.6, -3.55)),
            ((0.3, 0.26), (0.22, 0.2), (0.13, 0.12), (0.06, 0.06), (0.01, 0.01)))
    H.chain("spine.1", "belly", ((0, 0.52, -1.45), (0, 0.5, -2.1), (0, 0.5, -2.8)),
            ((0.18, 0.1), (0.12, 0.08), (0.06, 0.04)))


def spikes():
    for bone, z, y, h in (("spine.4", -0.15, 1.15, 0.45), ("spine.3", -0.5, 1.17, 0.42), ("spine.3", -0.85, 1.14, 0.36),
                          ("spine.2", -1.2, 1.04, 0.28), ("spine.2", -1.55, 0.93, 0.2)):
        mid = (0, y + h * 0.5, z - 0.08 * h)
        H.frustum(bone, "teal_dk", (0, y - 0.06, z), mid, (0.11, 0.13), (0.06, 0.08), sides=4)
        H.frustum(bone, "cream", mid, (0, y + h, z - 0.2 * h), (0.07, 0.09), (0.005, 0.005), sides=4)


def collar():
    for i in range(9):       # fan of plates over the shoulders, behind the necks
        t = math.radians(-100 + i * 25)
        x, z = math.sin(t), -0.1 - 0.5 * math.cos(t) + 0.0
        top = (0.55 * x, 1.02, 0.5 * (z + 0.1) - 0.1)
        low = (0.8 * x, 0.66, 0.65 * (z + 0.1) - 0.1)
        H.frustum("spine.4", "orange", top, low, (0.12, 0.05), (0.15, 0.06), sides=4)


def paw(bone, s, x, z, toe):
    H.frustum(bone, "teal", (s * x, 0.2, z), (s * x, 0.03, z + 0.1), (0.14, 0.14), (0.18, 0.2), sides=6)
    for k in (-1, 0, 1):
        H.frustum(bone, "cream", (s * (x + k * 0.1), 0.05, z + 0.12), (s * (x + k * 0.15), 0.02, z + toe),
                  (0.04, 0.04), (0.008, 0.008), sides=4)


def front_leg(s):
    H.chain("spine.4", "teal", ((s * 0.5, 0.88, -0.3), (s * 0.6, 0.62, -0.22), (s * 0.62, 0.4, -0.12), (s * 0.62, 0.2, 0.0)),
            ((0.3, 0.3), (0.26, 0.26), (0.2, 0.2), (0.15, 0.15)), sides=6)
    H.frustum("spine.4", "teal_dk", (s * 0.72, 0.7, -0.2), (s * 0.74, 0.3, -0.12), (0.12, 0.26), (0.1, 0.18), sides=4)
    paw("spine.4", s, 0.56, 0.0, 0.4)


def hind_leg(s):
    H.chain("spine.2", "teal", ((s * 0.5, 0.82, -1.2), (s * 0.66, 0.6, -1.05), (s * 0.66, 0.38, -0.88), (s * 0.58, 0.2, -1.2)),
            ((0.34, 0.34), (0.3, 0.3), (0.2, 0.2), (0.14, 0.14)), sides=6)
    H.frustum("spine.2", "teal_dk", (s * 0.7, 0.75, -1.1), (s * 0.7, 0.4, -0.95), (0.1, 0.28), (0.08, 0.2), sides=4)
    paw("spine.2", s, 0.58, -1.2, 0.4)


def neck(side, bone, pts):
    for i in range(3):
        a, b = pts[i], pts[i + 1]
        b2 = add(b, unit(sub(b, a)), 0.08)      # overlap into the next piece so bends show no gap
        H.frustum(f"{bone}.{i + 1}", "brown", a, b2, NECK_R[i], NECK_R[i + 1], sides=6)
        H.frustum(f"{bone}.{i + 1}", "tan", add(a, (0, 0, 0.05)), add(b2, (0, 0, 0.05)),
                  (NECK_R[i][0] * 0.6, NECK_R[i][1] + 0.02), (NECK_R[i + 1][0] * 0.6, NECK_R[i + 1][1] + 0.02), sides=4)
    head(f"{bone}.3", pts[3], side)


def head(bone, p, side):
    f = unit((0, -0.12, 1))

    def at(t, h=0.0, w=0.0):
        return (p[0] + w, p[1] + f[1] * t + h, p[2] + f[2] * t)
    H.frustum(bone, "teal", at(-0.05), at(0.42), (0.3, 0.22), (0.21, 0.15), sides=6)
    H.frustum(bone, "teal", at(0.35, 0.0), at(0.85, -0.04), (0.2, 0.14), (0.11, 0.09), sides=6)
    H.frustum(bone, "magenta", at(0.1, -0.1), at(0.7, -0.12), (0.15, 0.06), (0.09, 0.05), sides=4)
    H.frustum(bone, "tan", at(0.0, -0.14), at(0.72, -0.3), (0.19, 0.08), (0.1, 0.06), sides=4)
    for sx in (-1, 1):
        H.frustum(bone, "cyan", at(0.2, 0.1, sx * 0.22), at(0.32, 0.1, sx * 0.22), (0.05, 0.05), (0.05, 0.05), sides=4)
        H.frustum(bone, "cream", at(0.66, -0.08, sx * 0.09), at(0.68, -0.22, sx * 0.09), (0.025, 0.025), (0.005, 0.005), sides=4)


def make():
    trunk()
    spikes()
    collar()
    for s in (-1, 1):
        front_leg(s)
        hind_leg(s)
    for n in NECKS:
        neck(*n)


def joints():
    out = {
        "spine.1": ((0, 0.7, -1.75), (0, 0.7, -1.5)), "spine.2": ((0, 0.7, -1.5), (0, 0.75, -0.95)),
        "spine.3": ((0, 0.75, -0.95), (0, 0.8, -0.4)), "spine.4": ((0, 0.8, -0.4), (0, 0.85, 0.2)),
    }
    for _, bone, pts in NECKS:
        for i in range(3):
            out[f"{bone}.{i + 1}"] = (pts[i], pts[i + 1])
    return out


H.build("n01P", "hydra", PALETTE, make, joints())
