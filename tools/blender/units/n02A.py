"""Dragao Esmeralda (n02A, familia drake): medido em artifacts/model-sheets/refs/n02A/sheet.jpg (0,0042 m por pixel).

    blender -b --factory-startup -P tools/blender/units/n02A.py -- <out.glb>

Corpo grosso e verde, pescoco alto e bico marrom com baba corrosiva, peitoral de couraca, escamas marrons no
dorso e na cauda, asas altas e largas (braco no osso upper, dedos e membrana no osso lower).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "green": 0x1F5240, "green_dk": 0x173D30, "belly": 0x5A5A3A, "brown": 0x7A5A3C, "plate": 0x8E4A2A,
    "membrane": 0x6E8040, "eye": 0x6BFF30, "claw": 0x4A3826,
}

SPINE = [(0, 0.98, -0.4), (0, 0.98, 0.05), (0, 1.0, 0.5)]
NECK = [(0, 1.1, 0.5), (0, 1.5, 0.6), (0, 1.9, 0.62)]
HEAD_TIP, JAW_A, JAW_B = (0, 1.84, 1.3), (0, 1.78, 0.8), (0, 1.7, 1.2)
TAIL = [(0, 1.0, -0.4), (0, 0.95, -0.95), (0, 0.88, -1.45), (0, 0.8, -2.1)]
TAIL_R = [(0.3, 0.26), (0.19, 0.17), (0.11, 0.1), (0.02, 0.02)]
HIP, KNEE, TOE = (0.3, 0.9, -0.3), (0.34, 0.55, -0.6), (0.3, 0.04, -0.45)
SH, EL, HAND = (0.34, 0.95, 0.42), (0.34, 0.55, 0.4), (0.3, 0.1, 0.35)
SHOULDER, WRIST, ROOT = (0.3, 1.5, 0.0), (0.47, 2.43, 0.1), (0.28, 1.25, -0.45)
FINGERS = [(1.26, 3.1, -1.1), (1.12, 2.25, -1.05), (0.7, 1.7, -0.75), (0.34, 1.45, -0.5)]


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def flip(p, s):
    return (p[0] * s, p[1], p[2])


def head():
    H.frustum("head", "green", (0, 1.92, 0.5), (0, 1.94, 0.95), (0.19, 0.17), (0.15, 0.14), sides=6)
    H.frustum("head", "brown", (0, 1.9, 0.9), (0, 1.84, 1.3), (0.15, 0.13), (0.07, 0.06), sides=6)
    H.frustum("jaw", "belly", (0, 1.78, 0.8), (0, 1.7, 1.2), (0.1, 0.05), (0.05, 0.03), sides=4)
    H.frustum("head", "eye", (0, 1.8, 1.14), (0, 1.5, 1.12), (0.03, 0.03), (0.02, 0.02), sides=4)  # baba
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.15, 1.99, 0.82), (0.04, 0.05, 0.12))


def neck_torso():
    H.frustum("neck.1", "green", (0, 1.06, 0.48), (0, 1.52, 0.6), (0.3, 0.26), (0.21, 0.2), sides=8)
    H.frustum("neck.2", "green", (0, 1.48, 0.6), (0, 1.95, 0.62), (0.21, 0.2), (0.17, 0.16), sides=8)
    H.frustum("neck.1", "belly", (0, 1.15, 0.7), (0, 1.5, 0.78), (0.1, 0.03), (0.08, 0.03), sides=4)
    H.frustum("neck.2", "belly", (0, 1.5, 0.78), (0, 1.86, 0.78), (0.08, 0.03), (0.06, 0.03), sides=4)
    H.frustum("spine.1", "green", (0, 0.98, -0.5), (0, 0.98, 0.1), (0.36, 0.32), (0.44, 0.34), sides=8)
    H.frustum("spine.2", "green", (0, 0.98, 0.0), (0, 1.0, 0.64), (0.44, 0.34), (0.4, 0.32), sides=8)
    H.frustum("spine.2", "plate", (0, 1.28, 0.62), (0, 0.72, 0.52), (0.3, 0.06), (0.26, 0.06), sides=4)
    H.frustum("spine.1", "belly", (0, 0.68, -0.4), (0, 0.66, 0.1), (0.18, 0.05), (0.22, 0.05), sides=4)
    for i, z in enumerate((0.3, 0.1, -0.1, -0.3)):
        bone = "spine.2" if z > 0.05 else "spine.1"
        H.frustum(bone, "brown", (0, 1.22, z), (0, 1.36, z - 0.08), (0.17 - i * 0.01, 0.07), (0.1, 0.03), sides=4)


def tail():
    for i in range(3):
        H.frustum(f"tail.{i + 1}", "green", TAIL[i], TAIL[i + 1], TAIL_R[i], TAIL_R[i + 1], sides=6)
        a, b = TAIL[i], TAIL[i + 1]
        for t in (0.15, 0.6):
            p = lerp(a, b, t)
            r = TAIL_R[i][1] + 0.0
            H.frustum(f"tail.{i + 1}", "brown", (0, p[1] + r - 0.02, p[2]), (0, p[1] + r + 0.1 - i * 0.02, p[2] - 0.08),
                      (0.12 - i * 0.03, 0.06), (0.06 - i * 0.015, 0.02), sides=4)


def hind_legs():
    for s, n in ((1, 3), (-1, 4)):
        x = s * HIP[0]
        k, t = (s * KNEE[0], KNEE[1], KNEE[2]), (s * TOE[0], TOE[1], TOE[2])
        H.frustum(f"leg{n}.upper", "green", (x, HIP[1] + 0.14, HIP[2] + 0.02), k, (0.27, 0.28), (0.14, 0.14), sides=6)
        H.frustum(f"leg{n}.lower", "green", (k[0], k[1] + 0.03, k[2]), (t[0], 0.16, t[2]), (0.14, 0.14), (0.08, 0.08), sides=6)
        H.frustum(f"leg{n}.lower", "green_dk", (t[0], 0.16, t[2] - 0.02), (t[0], 0.04, t[2] + 0.22), (0.08, 0.06), (0.13, 0.05), sides=6)
        for dx in (-0.08, 0, 0.08):
            H.frustum(f"leg{n}.lower", "claw", (t[0] + dx, 0.05, t[2] + 0.2), (t[0] + dx * 1.3, 0.0, t[2] + 0.4), (0.03, 0.03), (0.005, 0.005), sides=4)


def fore_legs():
    for s, n in ((1, 1), (-1, 2)):
        sh, el, hd = flip(SH, s), flip(EL, s), flip(HAND, s)
        H.frustum(f"leg{n}.upper", "green", (sh[0], sh[1] + 0.16, sh[2]), el, (0.2, 0.2), (0.13, 0.13), sides=6)
        H.frustum(f"leg{n}.lower", "green", (el[0], el[1] + 0.03, el[2]), (hd[0], hd[1] + 0.04, hd[2]), (0.13, 0.13), (0.09, 0.09), sides=6)
        H.frustum(f"leg{n}.lower", "green_dk", (hd[0], hd[1] + 0.06, hd[2]), (hd[0], 0.03, hd[2] + 0.12), (0.09, 0.07), (0.12, 0.06), sides=6)
        for dx in (-0.07, 0, 0.07):
            H.frustum(f"leg{n}.lower", "claw", (hd[0] + dx, 0.05, hd[2] + 0.1), (hd[0] + dx * 1.3, 0.0, hd[2] + 0.3), (0.025, 0.03), (0.005, 0.005), sides=4)


def wing(s, n):
    up, low = f"wing{n}.upper", f"wing{n}.lower"
    sh, wr, root = flip(SHOULDER, s), flip(WRIST, s), flip(ROOT, s)
    tips = [flip(f, s) for f in FINGERS]
    H.frustum(up, "green", sh, wr, (0.17, 0.15), (0.1, 0.1), sides=6)
    H.frustum(low, "brown", wr, tips[0], (0.09, 0.08), (0.025, 0.025), sides=6)
    H.frustum(low, "brown", (wr[0], wr[1] - 0.05, wr[2]), (wr[0] - s * 0.1, wr[1] + 0.3, wr[2] + 0.1), (0.05, 0.05), (0.01, 0.01), sides=4)
    for tip in tips[1:]:
        H.frustum(low, "brown", wr, tip, (0.05, 0.05), (0.02, 0.02), sides=4)
    for i in range(3):
        a, b = tips[i], tips[i + 1]
        H.panel(low, "membrane", [wr, a, lerp(lerp(a, b, 0.5), wr, 0.2), b])
    inner = H.panel(up, "membrane", [sh, wr, tips[3], root])
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


H.build("n02A", "drake", PALETTE, make, joints())
