"""Winged Serpent (n00H, wyrm): measured on artifacts/model-sheets/refs/n00H/sheet.jpg (0.0027 m per pixel).

    blender -b --factory-startup -P tools/blender/units/n00H.py -- <out.glb>

Faces +z like its skeleton: head and snout at the front end of the spine chain, long tail with a black
feather fan behind. Blue body, tan belly, light-green frill and two antennae, big bat wings (arm and
finger frusta, membrane plates in green bands).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "blue": 0x34449A, "blue_dk": 0x2A377E, "frill": 0xC8DC6E, "belly": 0xD9A52E, "tan": 0xE0BE7A,
    "red": 0xA81C2A, "eye": 0xF4F030, "black": 0x1A1A1A,
    "m1": 0xB8DC40, "m2": 0x9CCB3A, "m3": 0x5FA040, "m4": 0x2E7A44, "m5": 0x1E5E3A,
}

# spine chain, one bone per segment: z of each joint and half (x, y) radii there
ZS = (0.38, 0.0, -0.35, -0.7, -1.0, -1.25, -1.5)
RS = ((0.17, 0.15), (0.23, 0.18), (0.11, 0.12), (0.075, 0.08), (0.055, 0.055), (0.04, 0.04), (0.02, 0.02))
SPINE = ("spine.1", "spine.2", "spine.3", "spine.4", "spine.5", "spine.6")
HEAD_A, HEAD_B = (0, 0.46, 0.38), (0, 0.56, 0.86)
S, E = (0.2, 0.5, 0.4), (0.65, 0.66, 0.3)          # shoulder and elbow (left wing)
C, F = (1.22, 0.52, 0.38), (1.22, 0.46, -0.1)          # wrist claw, finger tip
TRAIL = [F, (0.95, 0.56, -0.08), (0.72, 0.6, -0.1), (0.45, 0.58, -0.04)]
ROOT = (0.1, 0.48, -0.37)
BAND = ("m1", "m2", "m3", "m4")


def yc(z):
    return 0.46 + (z - 0.38) * 0.088


def mir(p, s):
    return (p[0] * s, p[1], p[2])


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def body():
    pts = [(0, yc(z), z) for z in ZS]
    H.chain(SPINE, "blue", pts, RS, sides=8)
    for i in range(3):      # tan belly plate under the chest and waist, one piece per bone
        a, b = ZS[i], ZS[i + 1]
        H.frustum(SPINE[i], "belly", (0, yc(a) - RS[i][1] * 0.8, a), (0, yc(b) - RS[i + 1][1] * 0.8, b),
                  (RS[i][0] * 0.62, 0.07), (RS[i + 1][0] * 0.62, 0.06), sides=4)
    H.frustum("spine.1", "blue_dk", (0, yc(0.3) + 0.12, 0.3), (0, yc(-0.0) + 0.14, 0.0), (0.13, 0.05), (0.17, 0.05), sides=4)
    for i, (xr, d) in enumerate(((0.045, 0.1), (0.03, 0.09))):   # tail fan: black feathers, four pairs
        for k in range(2):
            z = -1.12 - 0.12 * (2 * i + k)
            for s in (-1, 1):
                H.frustum(SPINE[4 + i], "black", (s * 0.03, yc(z), z), (s * 0.2, yc(z) + 0.02, z - d - 0.08),
                          (xr, 0.025), (0.012, 0.012), sides=4)


def head():
    h = [(0, 0.47, 0.34), (0, 0.5, 0.5), (0, 0.52, 0.68), (0, 0.55, 0.86)]
    H.chain("head", "blue", h, [(0.16, 0.13), (0.15, 0.12), (0.085, 0.07), (0.035, 0.03)], sides=8)
    H.frustum("head", "tan", (0, 0.4, 0.44), (0, 0.44, 0.84), (0.12, 0.05), (0.04, 0.025), sides=4)     # jaw
    H.frustum("head", "frill", (0, 0.6, 0.4), (0, 0.6, 0.68), (0.17, 0.035), (0.08, 0.03), sides=4)    # crest plate
    H.frustum("head", "frill", (0, 0.58, 0.32), (0, 0.66, 0.42), (0.06, 0.03), (0.02, 0.02), sides=4)   # back spike
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.145, 0.54, 0.6), (0.05, 0.07, 0.07))
        H.frustum("head", "red", (s * 0.08, 0.62, 0.54), (s * 0.15, 0.58, 0.64), (0.03, 0.03), (0.03, 0.03), sides=4)
        H.chain("head", "frill", [(s * 0.06, 0.62, 0.46), (s * 0.1, 0.78, 0.43), (s * 0.19, 0.88, 0.38)],
                [(0.03, 0.03), (0.022, 0.022), (0.008, 0.008)], sides=4)


def hind_legs():
    for s in (-1, 1):
        a, b = (s * 0.14, yc(-0.3) - 0.06, -0.3), (s * 0.3, yc(-0.4) - 0.14, -0.4)
        H.frustum("spine.3", "blue", a, b, (0.07, 0.07), (0.04, 0.04), sides=6)
        for dx in (-0.04, 0.0, 0.04):
            H.frustum("spine.3", "black", (b[0] + dx, b[1], b[2]), (b[0] + dx * 2.2, b[1] - 0.06, b[2] - 0.12),
                      (0.015, 0.015), (0.004, 0.004), sides=4)


def wing(s, n):
    up, low = f"wing{n}.upper", f"wing{n}.lower"
    sh, el, c, f, root = (mir(p, s) for p in (S, E, C, F, ROOT))
    tr = [mir(p, s) for p in TRAIL]
    H.frustum(up, "blue", sh, el, (0.075, 0.07), (0.05, 0.045), sides=6)
    H.frustum(low, "blue", el, c, (0.05, 0.045), (0.025, 0.025), sides=6)
    H.frustum(low, "blue", el, f, (0.04, 0.04), (0.015, 0.015), sides=4)
    for dz in (0.0, 0.07):    # claw hooks at the wrist
        H.frustum(low, "black", c, (c[0] + s * 0.05, c[1] - 0.05, c[2] + 0.1 + dz), (0.025, 0.025), (0.005, 0.005), sides=4)
    H.panel(low, BAND[0], [el, c, f])
    for i in range(3):
        a, b = tr[i], tr[i + 1]
        H.panel(low, BAND[i + 1], [el, a, lerp(lerp(a, b, 0.5), el, 0.2), b])
    inner = H.panel(up, "m5", [sh, el, tr[3], root])
    key = [(el, 1.0), (tr[3], 1.0), (sh, 0.0), (root, 0.0)]

    def weigh(p):
        near = min(key, key=lambda k: sum((p[i] - k[0][i]) ** 2 for i in range(3)))[1]
        return {low: near, up: 1.0 - near}

    H.soft(inner, weigh)


def make():
    body()
    head()
    hind_legs()
    wing(1, 1)
    wing(-1, 2)


def joints():
    out = {"head": (HEAD_A, HEAD_B)}
    for i, name in enumerate(SPINE):
        out[name] = ((0, yc(ZS[i]), ZS[i]), (0, yc(ZS[i + 1]), ZS[i + 1]))
    for s, n in ((1, 1), (-1, 2)):
        out[f"wing{n}.upper"] = (mir(S, s), mir(E, s))
        out[f"wing{n}.lower"] = (mir(E, s), mir((1.19, 0.5, 0.0), s))
    return out


H.build("n00H", "wyrm", PALETTE, make, joints())
