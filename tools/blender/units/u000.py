"""Serpe de Gelo (u000, familia drake): medido em artifacts/model-sheets/refs/u000/sheet.jpg (0,0042 m por pixel).

    blender -b --factory-startup -P tools/blender/units/u000.py -- <out.glb>

Dragao esqueleto: costelas, pescoco e cauda em aneis alternados osso/preto, crista de espinhos pretos em volta
do cranio, boca e olhos de gelo, asas de membrana roxa pendendo dos bracos de osso (upper / lower).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "bone": 0xD9CCA8, "bone_dk": 0xA89C7A, "black": 0x1B1A22, "ice": 0x70D8F0, "purple": 0x5A2D8C,
    "lav": 0xB08CDA,
}

SPINE = [(0, 0.56, -0.76), (0, 0.7, -0.4), (0, 0.9, 0.05)]
NECK = [(0, 0.9, 0.05), (0, 1.18, 0.12), (0, 1.45, 0.3)]
HEAD_TIP, JAW_A, JAW_B = (0, 1.55, 0.7), (0, 1.4, 0.32), (0, 1.34, 0.64)
TAIL = [(0, 0.56, -0.76), (0, 0.52, -1.5), (0, 0.47, -2.3), (0, 0.45, -3.0)]
TAIL_R = [(0.2, 0.16), (0.13, 0.11), (0.08, 0.07), (0.012, 0.012)]
HIP, KNEE, TOE = (0.17, 0.6, -0.75), (0.2, 0.32, -0.95), (0.15, 0.04, -0.9)
SH, EL, HAND = (0.2, 0.7, -0.1), (0.2, 0.42, 0.0), (0.17, 0.1, 0.05)
SHOULDER, WRIST, ROOT = (0.22, 1.0, -0.1), (0.95, 2.1, -0.3), (0.22, 0.55, -0.7)
FINGERS = [(2.1, 0.7, -0.6), (1.75, 0.1, -0.7), (1.2, 0.2, -0.7), (0.65, 0.75, -0.6)]


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def flip(p, s):
    return (p[0] * s, p[1], p[2])


def bands(bone, a, b, ra, rb, n, tones=("bone", "black")):
    """n stacked frusta from a to b alternating tones: vertebrae / ribs."""
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n + 0.02
        lo, hi = lerp(a, b, t0), lerp(a, b, min(t1, 1.0))
        r0, r1 = lerp(ra, rb, t0), lerp(ra, rb, min(t1, 1.0))
        H.frustum(bone, tones[i % 2], lo, hi, r0, r1, sides=6)


def head():
    H.frustum("head", "bone", (0, 1.5, 0.22), (0, 1.56, 0.56), (0.21, 0.19), (0.14, 0.12), sides=6)
    H.frustum("head", "bone", (0, 1.56, 0.5), (0, 1.5, 0.72), (0.13, 0.11), (0.07, 0.06), sides=6)
    H.frustum("jaw", "bone_dk", (0, 1.4, 0.32), (0, 1.34, 0.64), (0.1, 0.05), (0.05, 0.03), sides=4)
    H.frustum("head", "ice", (0, 1.44, 0.34), (0, 1.43, 0.68), (0.1, 0.035), (0.05, 0.02), sides=4)
    for s in (-1, 1):
        H.box("head", "ice", (s * 0.11, 1.63, 0.48), (0.05, 0.05, 0.1))
    for x, y in ((0.75, 2.15), (0.6, 2.45), (0.34, 2.5), (0.0, 2.55)):
        for s in ((-1, 1) if x else (1,)):
            H.frustum("head", "black", (s * x * 0.2, 1.62, 0.2), (s * x, y, 0.08), (0.1, 0.085), (0.01, 0.01), sides=4)


def neck_torso():
    bands("neck.1", (0, 0.86, 0.03), (0, 1.2, 0.12), (0.24, 0.22), (0.17, 0.16), 3)
    bands("neck.2", (0, 1.16, 0.12), (0, 1.5, 0.3), (0.17, 0.16), (0.15, 0.14), 3)
    bands("spine.2", (0, 0.66, -0.4), (0, 0.9, 0.08), (0.36, 0.3), (0.4, 0.32), 6)
    bands("spine.1", (0, 0.56, -0.8), (0, 0.7, -0.38), (0.26, 0.2), (0.32, 0.25), 4, ("bone_dk", "black"))
    H.frustum("spine.2", "black", (0, 0.88, 0.06), (0, 0.55, 0.14), (0.06, 0.05), (0.025, 0.03), sides=4)  # esterno
    for z in (-0.05, -0.28, -0.5):
        bone = "spine.2" if z > -0.4 else "spine.1"
        H.frustum(bone, "purple", (0, 0.95, z), (0, 1.25, z - 0.2), (0.1, 0.02), (0.01, 0.01), sides=4)


def tail():
    for i in range(3):
        bands(f"tail.{i + 1}", TAIL[i], TAIL[i + 1], TAIL_R[i], TAIL_R[i + 1], 4 if i < 2 else 3)
    end = TAIL[3]
    for k in range(4):
        z = end[2] + 0.5 - k * 0.14
        H.frustum("tail.3", "black", (0, end[1] + 0.02, z), (0, end[1] + 0.2 - k * 0.02, z - 0.16), (0.04, 0.03), (0.005, 0.005), sides=4)


def hind_legs():
    for s, n in ((1, 3), (-1, 4)):
        x = s * HIP[0]
        k, t = (s * KNEE[0], KNEE[1], KNEE[2]), (s * TOE[0], TOE[1], TOE[2])
        H.frustum(f"leg{n}.upper", "bone", (x, HIP[1] + 0.12, HIP[2]), k, (0.17, 0.18), (0.1, 0.1), sides=6)
        H.frustum(f"leg{n}.lower", "bone", (k[0], k[1] + 0.03, k[2]), (t[0], 0.14, t[2]), (0.1, 0.1), (0.06, 0.06), sides=6)
        H.frustum(f"leg{n}.lower", "bone_dk", (t[0], 0.14, t[2]), (t[0], 0.04, t[2] + 0.16), (0.05, 0.05), (0.09, 0.04), sides=6)
        for dx in (-0.06, 0, 0.06):
            H.frustum(f"leg{n}.lower", "black", (t[0] + dx, 0.05, t[2] + 0.14), (t[0] + dx * 1.3, 0.0, t[2] + 0.34), (0.022, 0.025), (0.005, 0.005), sides=4)


def fore_legs():
    for s, n in ((1, 1), (-1, 2)):
        sh, el, hd = flip(SH, s), flip(EL, s), flip(HAND, s)
        H.frustum(f"leg{n}.upper", "bone", (sh[0], sh[1] + 0.12, sh[2]), el, (0.16, 0.16), (0.1, 0.1), sides=6)
        H.frustum(f"leg{n}.lower", "bone", (el[0], el[1] + 0.03, el[2]), (hd[0], hd[1] + 0.04, hd[2]), (0.1, 0.1), (0.07, 0.07), sides=6)
        H.frustum(f"leg{n}.lower", "bone_dk", (hd[0], hd[1] + 0.06, hd[2]), (hd[0], 0.03, hd[2] + 0.1), (0.06, 0.05), (0.09, 0.04), sides=6)
        for dx in (-0.05, 0, 0.05):
            H.frustum(f"leg{n}.lower", "black", (hd[0] + dx, 0.05, hd[2] + 0.08), (hd[0] + dx * 1.3, 0.0, hd[2] + 0.28), (0.02, 0.025), (0.005, 0.005), sides=4)


def wing(s, n):
    up, low = f"wing{n}.upper", f"wing{n}.lower"
    sh, wr, root = flip(SHOULDER, s), flip(WRIST, s), flip(ROOT, s)
    tips = [flip(f, s) for f in FINGERS]
    H.frustum(up, "bone", sh, wr, (0.2, 0.17), (0.11, 0.11), sides=6)
    H.frustum(low, "bone", wr, tips[0], (0.13, 0.11), (0.035, 0.035), sides=6)
    H.frustum(low, "bone", (wr[0], wr[1] - 0.05, wr[2]), (wr[0] - s * 0.12, wr[1] + 0.3, wr[2] + 0.1), (0.05, 0.05), (0.01, 0.01), sides=4)
    for tip in tips[1:]:
        H.frustum(low, "bone", wr, tip, (0.055, 0.055), (0.025, 0.025), sides=4)
    for i in range(3):
        a, b = tips[i], tips[i + 1]
        H.panel(low, "purple", [wr, a, lerp(lerp(a, b, 0.5), wr, 0.25), b])
    inner = H.panel(up, "lav", [sh, wr, tips[3], root])
    key = [(wr, 1.0), (tips[3], 1.0), (sh, 0.0), (root, 0.0)]

    def weigh(p):
        near = min(key, key=lambda k: sum((p[i] - k[0][i]) ** 2 for i in range(3)))[1]
        return {low: near, up: 1.0 - near}

    H.soft(inner, weigh)


def make():
    head()
    neck_torso()
    tail()
    hind_legs()
    fore_legs()
    wing(1, 1)
    wing(-1, 2)


def joints():
    out = {"spine.1": (SPINE[0], SPINE[1]), "spine.2": (SPINE[1], SPINE[2]),
           "neck.1": (NECK[0], NECK[1]), "neck.2": (NECK[1], NECK[2]),
           "head": (NECK[2], HEAD_TIP), "jaw": (JAW_A, JAW_B)}
    for i in range(3):
        out[f"tail.{i + 1}"] = (TAIL[i], TAIL[i + 1])
    for s, n in ((1, 3), (-1, 4)):
        out[f"leg{n}.upper"] = (flip(HIP, s), flip(KNEE, s))
        out[f"leg{n}.lower"] = (flip(KNEE, s), flip(TOE, s))
    for s, n in ((1, 1), (-1, 2)):
        out[f"leg{n}.upper"] = (flip(SH, s), flip(EL, s))
        out[f"leg{n}.lower"] = (flip(EL, s), flip(HAND, s))
        out[f"wing{n}.upper"] = (flip(SHOULDER, s), flip(WRIST, s))
        out[f"wing{n}.lower"] = (flip(WRIST, s), flip(FINGERS[0], s))
    return out


H.build("u000", "drake", PALETTE, make, joints())
