"""Giant Spider (n01N), spider_high family: measured on artifacts/model-sheets/refs/n01N/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n01N.py -- <out.glb>

Scale 380 px per metre off the front/profile panels, ground y=0, head at +z. Purple two-segment legs arching
to a knee near 1 m with gold feet, a green head with big gold fangs and four red eyes, a dark abdomen.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402
import rig_families as R  # noqa: E402

PALETTE = {
    "leg": 0x6B5681, "leg_dk": 0x57456B, "abd": 0x2D2231, "green": 0x5A7040, "green_dk": 0x35462F,
    "gold": 0xD9BE78, "red": 0x9A4C38, "eye": 0xB02020,
}
KNEE_Y = 1.02
# feet read off the top panel (x, z) for the +x side; legs 4, 3, 5, 6 mirror 1, 2, 8, 7
FEET = {1: (1.22, 0.75), 2: (0.72, 1.05), 8: (1.15, -0.42), 7: (0.66, -0.9)}
MIRROR = {4: 1, 3: 2, 5: 8, 6: 7}


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def abdomen():
    # (z, y, half width, half height) stacked along the body, widest in front of the middle
    rings = ((0.05, 0.6, 0.2, 0.2), (-0.15, 0.62, 0.33, 0.3), (-0.55, 0.62, 0.34, 0.3), (-0.85, 0.58, 0.26, 0.24),
             (-0.95, 0.54, 0.2, 0.2))
    for (z0, y0, w0, h0), (z1, y1, w1, h1) in zip(rings, rings[1:]):
        y0, y1, h0, h1 = y0 + 0.12, y1 + 0.12, h0 * 1.1, h1 * 1.1
        H.frustum("abdomen", "abd", (0, y0, z0), (0, y1, z1), (w0, h0), (w1, h1))
    H.frustum("abdomen", "red", (0, 0.66, -0.95), (0, 0.62, -1.0), (0.2, 0.2), (0.14, 0.14))
    H.frustum("abdomen", "green", (0, 0.62, -1.0), (0, 0.56, -1.05), (0.1, 0.1), (0.07, 0.07))
    H.frustum("abdomen", "gold", (0, 0.56, -1.05), (0, 0.38, -1.2), (0.07, 0.07), (0.01, 0.01), sides=6)
    H.frustum("abdomen", "green_dk", (0, 0.45, -0.05), (0, 0.43, -0.9), (0.22, 0.05), (0.18, 0.05))


def head():
    H.frustum("body", "green", (0, 0.63, -0.05), (0, 0.64, 0.35), (0.22, 0.18), (0.25, 0.19))
    H.frustum("head", "green", (0, 0.64, 0.3), (0, 0.64, 0.56), (0.25, 0.19), (0.23, 0.18))
    H.frustum("head", "green", (0, 0.64, 0.56), (0, 0.61, 0.72), (0.23, 0.18), (0.19, 0.15))
    for s in (-1, 1):
        for x, y in ((0.07, 0.72), (0.15, 0.68)):
            H.frustum("head", "eye", (s * x, y, 0.7), (s * x, y, 0.76), (0.045, 0.045), (0.04, 0.04), sides=6)
        H.chain("head", "gold", [(s * 0.12, 0.58, 0.66), (s * 0.17, 0.4, 0.84), (s * 0.13, 0.25, 0.98), (s * 0.05, 0.16, 1.05)],
                [(0.12, 0.11), (0.11, 0.1), (0.08, 0.075), (0.012, 0.012)], sides=6)


def leg_joints(n):
    hip = {b[0]: b for b in R.SPIDER_HIGH}[f"leg{n}.upper"][2]
    fx, fz = FEET.get(n) or FEET[MIRROR[n]]
    foot = (fx if n in FEET else -fx, 0.04, fz)
    k = lerp((hip[0], 0, hip[2]), (foot[0], 0, foot[2]), 0.4)
    return hip, (k[0], KNEE_Y, k[2]), foot


def leg(n):
    hip, knee, foot = leg_joints(n)
    H.chain(f"leg{n}.upper", "leg_dk", [hip, lerp(hip, knee, 0.5), knee], [(0.085, 0.085), (0.07, 0.07), (0.06, 0.06)])
    H.chain(f"leg{n}.lower", "leg", [knee, lerp(knee, foot, 0.3), lerp(knee, foot, 0.7)],
            [(0.06, 0.06), (0.052, 0.052), (0.045, 0.045)])
    H.frustum(f"leg{n}.lower", "gold", lerp(knee, foot, 0.7), foot, (0.045, 0.045), (0.01, 0.01), sides=6)
    H.frustum(f"leg{n}.upper", "gold", (knee[0], knee[1] + 0.02, knee[2]), (knee[0], knee[1] + 0.13, knee[2]),
              (0.045, 0.045), (0.008, 0.008), sides=4)


def make():
    abdomen()
    head()
    for n in range(1, 9):
        leg(n)


def joints():
    out = {}
    for n in range(1, 9):
        hip, knee, foot = leg_joints(n)
        out[f"leg{n}.upper"], out[f"leg{n}.lower"] = (hip, knee), (knee, foot)
    return out


H.build("n01N", "spider_high", PALETTE, make, joints())
