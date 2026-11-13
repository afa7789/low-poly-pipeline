"""Brood Mother (n01W), spider family: measured on artifacts/model-sheets/refs/n01W/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n01W.py -- <out.glb>

Scale off the front panel: 385 px per metre (feet span +-1.03), ground y=0, head at +z. A purple head with
big pale hooked fangs under a red crest, a black abdomen with a magenta heart, long slate legs with
magenta tips and thorns.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402
import rig_families as R  # noqa: E402

PALETTE = {
    "black": 0x2A2030, "purple": 0x6E3FA8, "purple_dk": 0x4A2E6E, "slate": 0x5F6B8A, "slate_dk": 0x4C5775,
    "magenta": 0xB03080, "fang": 0xC7AEDB, "crest": 0xB84058, "eye": 0x151018, "shine": 0xE8E0F0,
}
# abdomen outline, front to back: (z, half width, half height, centre y)
ABD = ((0.15, 0.24, 0.25, 0.7), (0.0, 0.4, 0.36, 0.74), (-0.3, 0.45, 0.4, 0.72),
       (-0.6, 0.37, 0.32, 0.64), (-0.8, 0.16, 0.15, 0.54))
KNEE_Y = 0.95
# feet read off the top panel (x, z) for the +x side; legs 4, 3, 5, 6 mirror 1, 2, 8, 7
FEET = {1: (1.03, 0.57), 2: (0.62, 0.86), 8: (1.0, -0.56), 7: (0.62, -1.0)}
MIRROR = {4: 1, 3: 2, 5: 8, 6: 7}


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def top(x, z):
    """A point just above the abdomen's back at (x, z)."""
    for a, b in zip(ABD, ABD[1:]):
        if b[0] <= z <= a[0]:
            t = (a[0] - z) / (a[0] - b[0])
            rx, ry, cy = (a[i] + (b[i] - a[i]) * t for i in (1, 2, 3))
            return (x, cy + ry * max(1 - (x / rx) ** 2, 0.05) ** 0.5 * 1.05, z)
    raise ValueError(z)


def abdomen():
    for a, b in zip(ABD, ABD[1:]):
        H.frustum("abdomen", "black", (0, a[3], a[0]), (0, b[3], b[0]), (a[1], a[2]), (b[1], b[2]))
    for s in (-1, 1):   # the heart: two arms of a V pointing back
        H.frustum("abdomen", "magenta", top(s * 0.24, 0.02), top(s * 0.03, -0.42), (0.05, 0.04), (0.05, 0.04), sides=4)
        H.frustum("abdomen", "magenta", top(s * 0.24, 0.02), top(s * 0.12, 0.1), (0.05, 0.04), (0.05, 0.04), sides=4)
    H.chain("abdomen", "slate", [(0, 0.56, -0.74), (0, 0.45, -0.88), (0, 0.28, -1.02)], [(0.09, 0.09), (0.06, 0.06), (0.01, 0.01)])


def thorax():
    H.frustum("body", "purple", (0, 0.6, 0.55), (0, 0.62, 0.12), (0.2, 0.16), (0.28, 0.2))
    H.frustum("body", "purple", (0, 0.62, 0.12), (0, 0.64, -0.12), (0.28, 0.2), (0.22, 0.18))
    for x, h in ((-0.26, 0.2), (-0.13, 0.34), (0.0, 0.6), (0.13, 0.46), (0.26, 0.3)):   # the red crest, leaning back
        H.frustum("body", "crest", (x * 0.7, 0.72, 0.42), (x * 1.1, 0.72 + h, 0.22), (0.1, 0.06), (0.01, 0.01), sides=4)


def head():
    H.frustum("head", "purple", (0, 0.56, 0.4), (0, 0.55, 0.72), (0.2, 0.17), (0.24, 0.19))
    H.frustum("head", "purple", (0, 0.55, 0.72), (0, 0.5, 0.92), (0.24, 0.19), (0.18, 0.15))
    for x, y, r in ((0.075, 0.62, 0.05), (-0.075, 0.62, 0.05), (0.15, 0.6, 0.03), (-0.15, 0.6, 0.03), (0.04, 0.55, 0.025), (-0.04, 0.55, 0.025)):
        H.frustum("head", "eye", (x, y, 0.86), (x, y, 0.95), (r, r), (r * 0.8, r * 0.8), sides=6)
    for s in (-1, 1):
        H.chain("head", "fang", [(s * 0.13, 0.46, 0.82), (s * 0.13, 0.34, 1.0), (s * 0.1, 0.2, 1.08), (s * 0.05, 0.1, 1.03)],
                [(0.09, 0.09), (0.08, 0.08), (0.055, 0.055), (0.01, 0.01)])


def leg_joints(n):
    table = {b[0]: b for b in R.SPIDER}
    hip = table[f"leg{n}.upper"][2]
    fx, fz = FEET.get(n) or FEET[MIRROR[n]]
    foot = (fx if n in FEET else -fx, 0.04, fz)
    k = lerp((hip[0], 0, hip[2]), (foot[0], 0, foot[2]), 0.5)
    return hip, (k[0], KNEE_Y, k[2]), foot


def leg(n):
    hip, knee, foot = leg_joints(n)
    H.chain(f"leg{n}.upper", "slate", [hip, lerp(hip, knee, 0.5), knee], [(0.09, 0.09), (0.075, 0.075), (0.062, 0.062)])
    H.chain(f"leg{n}.lower", "slate_dk", [knee, lerp(knee, foot, 0.35), lerp(knee, foot, 0.7)],
            [(0.068, 0.068), (0.06, 0.06), (0.05, 0.05)])
    H.frustum(f"leg{n}.lower", "magenta", lerp(knee, foot, 0.7), foot, (0.05, 0.05), (0.01, 0.01), sides=6)
    dx, dz = foot[0] - hip[0], foot[2] - hip[2]
    d = max((dx * dx + dz * dz) ** 0.5, 1e-6)
    tip = (knee[0] + dx / d * 0.05, knee[1] + 0.2, knee[2] + dz / d * 0.05)
    H.frustum(f"leg{n}.lower", "magenta", knee, tip, (0.05, 0.05), (0.006, 0.006), sides=4)


def make():
    abdomen()
    thorax()
    head()
    for n in range(1, 9):
        leg(n)


def joints():
    out = {}
    for n in range(1, 9):
        hip, knee, foot = leg_joints(n)
        out[f"leg{n}.upper"], out[f"leg{n}.lower"] = (hip, knee), (knee, foot)
    return out


H.build("n01W", "spider", PALETTE, make, joints(), fit=True)
