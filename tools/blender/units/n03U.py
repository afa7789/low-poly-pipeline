"""Winged Riptide Serpent (n03U, ray): measured on artifacts/model-sheets/refs/n03U/sheet.jpg (0.0031 m per pixel
in the top view).

    blender -b --factory-startup -P tools/blender/units/n03U.py -- <out.glb>

Manta-ray body with a horned, wide-jawed head at the +z end (on the body bone: the family has no head bone),
muscular wing roots on the upper wing bones, thin blades with a green underside on the lower ones, a long
tail in four segments ending in a cyan-jewelled diamond between two ivory crescents.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "blue": 0x3A4A96, "blue_dk": 0x2C3875, "tan": 0xC9A070, "belly": 0xD6A62C, "frill": 0xC0DC5A,
    "red": 0x8A1A2A, "eye": 0xFFE020, "ivory": 0xD8D2B8, "cyan": 0x30D8C8, "fang": 0xF0EBD0,
    "m1": 0xB8DC40, "m2": 0x6AA84A, "m3": 0x1E5E3A,
}

BODY_Z = (-0.3, 0.0, 0.3, 0.5)
BODY_R = ((0.2, 0.15), (0.36, 0.21), (0.34, 0.21), (0.26, 0.17))
TAIL_Z = (-0.3, -0.69, -1.07, -1.46, -1.84)
TAIL_R = ((0.12, 0.1), (0.085, 0.07), (0.06, 0.05), (0.045, 0.035), (0.03, 0.025))
TAIL = ("tail.1", "tail.2", "tail.3", "tail.4")
TAIL_BONES = ("body", "tail.1", "tail.2", "tail.3", "tail.4")


def yb(z):
    return 1.21 + (z - 0.1) * 0.01


def yt(z):
    return 1.2 - 0.0857 * (-0.3 - z)


def body():
    H.chain("body", "blue", [(0, yb(z), z) for z in BODY_Z], BODY_R, sides=8)
    H.chain("body", "belly", [(0, 1.0, 0.55), (0, 1.0, 0.2), (0, 1.0, -0.3)], [(0.14, 0.05), (0.27, 0.06), (0.1, 0.05)], sides=4)
    for i, z in enumerate((0.25, 0.05, -0.15, -0.35)):    # dorsal spikes
        H.frustum("body", "blue_dk", (0, 1.38 - i * 0.03, z + 0.05), (0, 1.5 - i * 0.04, z - 0.07), (0.04, 0.06), (0.005, 0.01), sides=4)


def head():
    H.chain("body", "blue", [(0, 1.24, 0.4), (0, 1.2, 0.62), (0, 1.14, 0.8)], [(0.27, 0.18), (0.23, 0.16), (0.15, 0.1)], sides=8)
    H.frustum("body", "tan", (0, 1.13, 0.66), (0, 1.1, 0.88), (0.17, 0.1), (0.12, 0.08), sides=8)      # blunt snout
    H.frustum("body", "tan", (0, 1.03, 0.4), (0, 1.05, 0.84), (0.22, 0.06), (0.14, 0.05), sides=6)     # lower jaw
    H.frustum("body", "belly", (0, 1.0, 0.36), (0, 1.0, 0.5), (0.2, 0.06), (0.14, 0.05), sides=4)
    H.box("body", "red", (0, 1.34, 0.66), (0.4, 0.05, 0.1))                                            # heavy brow
    H.frustum("body", "frill", (0, 1.36, 0.42), (0, 1.4, 0.58), (0.12, 0.03), (0.07, 0.025), sides=4)
    for s in (-1, 1):
        H.box("body", "eye", (s * 0.15, 1.27, 0.7), (0.07, 0.06, 0.06))
        H.frustum("body", "fang", (s * 0.09, 1.1, 0.84), (s * 0.09, 1.0, 0.86), (0.018, 0.018), (0.005, 0.005), sides=4)
        H.chain("body", "frill", [(s * 0.24, 1.3, 0.5), (s * 0.31, 1.42, 0.5), (s * 0.3, 1.55, 0.48), (s * 0.22, 1.63, 0.46)],
                [(0.05, 0.05), (0.04, 0.04), (0.03, 0.03), (0.008, 0.008)], sides=4)


def wing(s, n):
    up, low = f"wing{n}.upper", f"wing{n}.lower"
    p = lambda x, y, z: (s * x, y, z)  # noqa: E731
    H.frustum(up, "blue", p(0.2, 1.24, 0.1), p(0.85, 1.3, 0.1), (0.18, 0.44), (0.09, 0.3), sides=8)      # muscular root
    H.frustum(low, "blue", p(0.85, 1.3, -0.02), p(1.4, 1.26, -0.22), (0.28, 0.05), (0.02, 0.012), sides=4)  # blade
    trail = [p(1.39, 1.25, -0.21), p(1.1, 1.27, -0.2), p(0.8, 1.29, -0.3)]
    H.panel(low, "blue", [p(0.85, 1.29, 0.26), *trail])
    under = [p(1.41, 1.2, -0.21), p(1.1, 1.22, -0.17), p(0.8, 1.24, -0.27)]
    for tone, a, b in (("m1", 0, 1), ("m2", 1, 2)):
        H.panel(low, tone, [p(0.85, 1.21, 0.2), under[a], under[b]])
    H.panel(up, "blue", [p(0.25, 1.26, 0.38), p(0.85, 1.31, 0.26), p(0.8, 1.29, -0.3), p(0.5, 1.26, -0.32), p(0.15, 1.22, -0.5)])
    H.panel(up, "m3", [p(0.3, 1.15, 0.1), p(0.85, 1.22, 0.2), p(0.8, 1.22, -0.27), p(0.5, 1.18, -0.3), p(0.15, 1.12, -0.48)])


def tail():
    pts = [(0, yt(z), z) for z in TAIL_Z]
    H.chain(TAIL, "blue", pts, TAIL_R, sides=6)
    for i in range(3):
        a, b = TAIL_Z[i], TAIL_Z[i + 1]
        H.frustum(TAIL[i], "belly", (0, yt(a) - TAIL_R[i][1] * 0.8, a), (0, yt(b) - TAIL_R[i + 1][1] * 0.8, b),
                  (TAIL_R[i][0] * 0.6, 0.04), (TAIL_R[i + 1][0] * 0.6, 0.035), sides=4)
    for s in (-1, 1):     # ivory crescents
        pts = [(s * 0.04, yt(-1.28), -1.28), (s * 0.2, yt(-1.4), -1.4), (s * 0.3, yt(-1.6), -1.6), (s * 0.26, yt(-1.82), -1.82)]
        H.chain(["tail.3", "tail.4", "tail.4"], "ivory", pts, [(0.04, 0.05), (0.04, 0.05), (0.03, 0.04), (0.008, 0.01)], sides=4)
    y = yt(-1.7)      # diamond tip
    H.frustum("tail.4", "blue", (0, y, -1.5), (0, y, -1.7), (0.02, 0.025), (0.12, 0.04), sides=4)
    H.frustum("tail.4", "blue", (0, y, -1.7), (0, y, -1.92), (0.12, 0.04), (0.01, 0.015), sides=4)
    H.frustum("tail.4", "cyan", (0, y + 0.03, -1.65), (0, y + 0.03, -1.77), (0.04, 0.025), (0.04, 0.025), sides=4)


def make():
    body()
    head()
    tail()
    wing(1, 1)
    wing(-1, 2)


def joints():
    return {name: (a, b) for name, a, b in (
        (f"tail.{i + 1}", (0, yt(TAIL_Z[i]), TAIL_Z[i]), (0, yt(TAIL_Z[i + 1]), TAIL_Z[i + 1])) for i in range(4))}


H.build("n03U", "ray", PALETTE, make, joints())
