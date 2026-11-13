"""Forest Spider (n00T), spider family: measured on artifacts/model-sheets/refs/n00T/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n00T.py -- <out.glb>

Scale off the front panel: 145 px per metre (legs span +-1.03), ground y=0, head at +z.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402
import rig_families as R  # noqa: E402

PALETTE = {
    "brown": 0x5B4636, "brown_dk": 0x3E3026, "brown_lt": 0x6E5642, "olive": 0x7A7A2C,
    "olive_dk": 0x5F5F22, "glow": 0xA4EA2C,
}

# abdomen outline, front to back: (z, half width, half height, centre y)
ABD = ((0.12, 0.2, 0.2, 0.74), (-0.05, 0.36, 0.38, 0.76), (-0.3, 0.43, 0.44, 0.76),
       (-0.55, 0.4, 0.41, 0.72), (-0.75, 0.27, 0.28, 0.66), (-0.9, 0.1, 0.1, 0.6))
BANDS = ((-0.0, -0.12), (-0.28, -0.4), (-0.52, -0.64))
KNEE_Y, KNEE_R = 1.0, 0.75
# feet read off the top panel (x, z) for the +x side; legs 4, 3, 5, 6 mirror 1, 2, 8, 7
FEET = {1: (0.95, 0.62), 2: (0.45, 1.05), 8: (1.05, -0.2), 7: (0.75, -0.8)}
MIRROR = {4: 1, 3: 2, 5: 8, 6: 7}   # the sheet's knees stand about a metre up and 0.7 out


def prof(z, grow=1.0):
    for a, b in zip(ABD, ABD[1:]):
        if b[0] <= z <= a[0]:
            t = (a[0] - z) / (a[0] - b[0])
            rx, ry, cy = (a[i] + (b[i] - a[i]) * t for i in (1, 2, 3))
            return (0, cy, z), (rx * grow, ry * grow)
    raise ValueError(z)


def abdomen():
    for a, b in zip(ABD, ABD[1:]):
        H.frustum("abdomen", "brown", (0, a[3], a[0]), (0, b[3], b[0]), (a[1], a[2]), (b[1], b[2]))
    for z0, z1 in BANDS:
        (p0, r0), (p1, r1) = prof(z0, 1.05), prof(z1, 1.05)
        H.frustum("abdomen", "olive", p0, p1, r0, r1)
    for s in (-1, 1):   # the green spinneret tips at the back
        H.frustum("abdomen", "glow", (s * 0.07, 0.7, -0.84), (s * 0.08, 0.62, -1.1), (0.05, 0.05), (0.008, 0.008), sides=4)


def thorax():
    H.frustum("body", "brown_lt", (0, 0.62, 0.42), (0, 0.66, 0.05), (0.2, 0.18), (0.3, 0.26))
    H.frustum("body", "brown_lt", (0, 0.66, 0.05), (0, 0.7, -0.22), (0.3, 0.26), (0.22, 0.2))


def head():
    H.frustum("head", "brown_lt", (0, 0.58, 0.3), (0, 0.56, 0.7), (0.21, 0.19), (0.19, 0.18))
    H.frustum("head", "brown_lt", (0, 0.56, 0.7), (0, 0.5, 0.88), (0.19, 0.18), (0.14, 0.13))
    for x, y in ((0.045, 0.64), (-0.045, 0.64), (0.11, 0.62), (-0.11, 0.62), (0.07, 0.55), (-0.07, 0.55), (0.0, 0.58)):
        H.frustum("head", "glow", (x, y, 0.8), (x, y, 0.92), (0.035, 0.035), (0.025, 0.025), sides=4)
    for s in (-1, 1):
        H.frustum("head", "olive", (s * 0.07, 0.46, 0.84), (s * 0.06, 0.28, 0.94), (0.05, 0.05), (0.01, 0.01), sides=6)
        H.frustum("head", "glow", (s * 0.07, 0.46, 0.84), (s * 0.062, 0.36, 0.92), (0.032, 0.032), (0.012, 0.012), sides=6)


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def leg_joints(bone):
    """hip / knee / foot of a family leg, the knee raised to the sheet's arch."""
    n = bone.split(".")[0]
    table = {b[0]: b for b in R.SPIDER}
    hip, foot = table[f"{n}.upper"][2], table[f"{n}.lower"][3]
    r = math.hypot(hip[0], hip[2])
    k = KNEE_R / r
    m = int(n[3:])
    fx, fz = FEET.get(m) or FEET[MIRROR[m]]
    foot = (fx if m in FEET else -fx, foot[1], fz)
    return hip, (hip[0] * k, KNEE_Y, hip[2] * k), foot


def leg(n):
    hip, knee, foot = leg_joints(f"leg{n}")
    H.chain(f"leg{n}.upper", "brown", [hip, lerp(hip, knee, 0.55), knee], [(0.12, 0.12), (0.11, 0.11), (0.085, 0.085)])
    H.frustum(f"leg{n}.lower", "olive_dk", knee, lerp(knee, foot, 0.2), (0.095, 0.095), (0.08, 0.08))
    H.chain(f"leg{n}.lower", "brown", [lerp(knee, foot, 0.18), lerp(knee, foot, 0.6), foot],
            [(0.08, 0.08), (0.055, 0.055), (0.012, 0.012)])


def make():
    abdomen()
    thorax()
    head()
    for n in range(1, 9):
        leg(n)


def joints():
    out = {}
    for n in range(1, 9):
        hip, knee, foot = leg_joints(f"leg{n}")
        out[f"leg{n}.upper"], out[f"leg{n}.lower"] = (hip, knee), (knee, foot)
    return out


H.build("n00T", "spider", PALETTE, make, joints(), fit=True)
