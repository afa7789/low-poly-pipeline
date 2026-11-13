"""Black Spider (n00U), spider family: measured on artifacts/model-sheets/refs/n00U/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n00U.py -- <out.glb>

Scale off the front panel: 308 px per metre (feet span +-0.95), ground y=0, head at +z. A round dark body, red
shell plates, a box head with two green eyes, stubby spiked legs.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402
import rig_families as R  # noqa: E402

PALETTE = {
    "dark": 0x2A201C, "dark_lt": 0x3E3530, "leg": 0x382C25, "red": 0x93443A, "red_dk": 0x7A362E,
    "tan": 0x8A8A5A, "glow": 0x8FEA3C,
}
KNEE_Y = 0.8
# feet read off the top panel (x, z) for the +x side; legs 4, 3, 5, 6 mirror 1, 2, 8, 7
FEET = {1: (0.88, 0.66), 2: (0.55, 1.03), 8: (0.84, 0.06), 7: (0.72, -0.44)}
MIRROR = {4: 1, 3: 2, 5: 8, 6: 7}


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def shell():
    plates = (("body", (0.5, 0.8), (0.0, 1.08), (0.42, 0.54)), ("abdomen", (0.1, 1.1), (-0.4, 0.92), (0.5, 0.5)),
              ("abdomen", (-0.3, 0.95), (-0.68, 0.74), (0.5, 0.36)))
    for bone, (z0, y0), (z1, y1), (w0, w1) in plates:
        H.frustum(bone, "red", (0, y0, z0), (0, y1, z1), (w0, 0.09), (w1, 0.09), sides=6)
        H.frustum(bone, "red_dk", (0, y0 - 0.08, z0), (0, y1 - 0.08, z1), (w0 * 1.04, 0.07), (w1 * 1.04, 0.07), sides=6)
        H.frustum(bone, "red", (0, y0 + 0.07, z0 - 0.05), (0, y1 + 0.07, z1 + 0.05), (w0 * 0.7, 0.05), (w1 * 0.7, 0.05), sides=6)
    H.frustum("abdomen", "tan", (0, 1.04, -0.05), (0, 1.22, -0.05), (0.03, 0.03), (0.04, 0.04), sides=4)
    H.frustum("abdomen", "red", (0, 1.22, -0.05), (0, 1.3, -0.05), (0.16, 0.16), (0.07, 0.07))


def body():
    H.frustum("body", "dark", (0, 0.68, 0.55), (0, 0.7, 0.1), (0.3, 0.3), (0.5, 0.43))
    H.frustum("abdomen", "dark", (0, 0.72, 0.1), (0, 0.72, -0.3), (0.5, 0.43), (0.52, 0.44))
    H.frustum("abdomen", "dark", (0, 0.7, -0.3), (0, 0.64, -0.62), (0.52, 0.44), (0.36, 0.32))
    H.frustum("abdomen", "dark", (0, 0.64, -0.62), (0, 0.56, -0.74), (0.34, 0.3), (0.16, 0.14))


def head():
    H.frustum("head", "dark_lt", (0, 0.6, 0.48), (0, 0.6, 0.76), (0.24, 0.22), (0.26, 0.21), sides=4)
    H.frustum("head", "dark_lt", (0, 0.6, 0.76), (0, 0.58, 0.95), (0.26, 0.21), (0.24, 0.18), sides=4)
    for s in (-1, 1):
        H.frustum("head", "glow", (s * 0.12, 0.66, 0.92), (s * 0.12, 0.66, 1.0), (0.04, 0.04), (0.035, 0.035), sides=6)
        H.chain("head", "tan", [(s * 0.15, 0.46, 0.88), (s * 0.15, 0.32, 0.94), (s * 0.12, 0.2, 0.96)],
                [(0.07, 0.07), (0.06, 0.06), (0.012, 0.012)], sides=6)


def leg_joints(n):
    table = {b[0]: b for b in R.SPIDER}
    hip = table[f"leg{n}.upper"][2]
    fx, fz = FEET.get(n) or FEET[MIRROR[n]]
    foot = (fx if n in FEET else -fx, 0.04, fz)
    k = lerp((hip[0], 0, hip[2]), (foot[0], 0, foot[2]), 0.55)
    return hip, (k[0], KNEE_Y, k[2]), foot


def leg(n):
    hip, knee, foot = leg_joints(n)
    H.chain(f"leg{n}.upper", "leg", [hip, lerp(hip, knee, 0.55), knee], [(0.12, 0.12), (0.105, 0.105), (0.09, 0.09)])
    H.chain(f"leg{n}.lower", "leg", [knee, lerp(knee, foot, 0.4), lerp(knee, foot, 0.8), foot],
            [(0.1, 0.1), (0.09, 0.09), (0.06, 0.06), (0.012, 0.012)])
    dx, dz = foot[0] - hip[0], foot[2] - hip[2]
    d = max((dx * dx + dz * dz) ** 0.5, 1e-6)
    tip = (knee[0] + dx / d * 0.12, knee[1] + 0.2, knee[2] + dz / d * 0.12)
    H.frustum(f"leg{n}.lower", "dark", (knee[0], knee[1] - 0.03, knee[2]), tip, (0.06, 0.06), (0.006, 0.006), sides=4)


def make():
    body()
    shell()
    head()
    for n in range(1, 9):
        leg(n)


def joints():
    out = {}
    for n in range(1, 9):
        hip, knee, foot = leg_joints(n)
        out[f"leg{n}.upper"], out[f"leg{n}.lower"] = (hip, knee), (knee, foot)
    return out


H.build("n00U", "spider", PALETTE, make, joints())
