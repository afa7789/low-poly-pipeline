"""Drake das Trevas (n01D, familia drake): medido em artifacts/model-sheets/refs/n01D/sheet.jpg (0,0042 m por pixel).

    blender -b --factory-startup -P tools/blender/units/n01D.py -- <out.glb>

Pescoco longo e reto com a garganta verde brilhando, cabeca horizontal, corpo grosso, cauda longa com pinca
preta, asas largas varridas para tras (braco no osso upper, dedos e membrana no osso lower).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "purple": 0x5B2F85, "purple_dk": 0x3E1F5C, "olive": 0x5E5D3C, "olive_dk": 0x3D3C26, "green": 0x6BFF20,
    "collar": 0x3A3A3C, "black": 0x1D1621,
}

SPINE = [(0, 0.9, -0.46), (0, 1.0, -0.05), (0, 1.12, 0.22)]
NECK = [(0, 1.12, 0.22), (0, 1.5, 0.2), (0, 1.88, 0.12)]
HEAD_TIP, JAW_A, JAW_B = (0, 1.92, 0.68), (0, 1.84, 0.3), (0, 1.82, 0.62)
TAIL = [(0, 0.9, -0.46), (0, 0.9, -0.95), (0, 0.88, -1.45), (0, 0.86, -1.93)]
TAIL_R = [(0.26, 0.22), (0.16, 0.14), (0.09, 0.08), (0.025, 0.025)]
HIP, KNEE, TOE = (0.3, 0.92, -0.45), (0.36, 0.5, -0.65), (0.28, 0.04, -0.5)
SH, EL, HAND = (0.3, 1.08, 0.1), (0.32, 0.85, 0.12), (0.3, 0.65, 0.2)
SHOULDER, WRIST, ROOT = (0.2, 1.3, 0.0), (0.62, 1.9, -0.15), (0.22, 1.05, -0.45)
FINGERS = [(1.4, 2.4, -1.2), (1.1, 1.65, -1.0), (0.72, 1.3, -0.8), (0.45, 1.25, -0.5)]


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def flip(p, s):
    return (p[0] * s, p[1], p[2])


def head():
    H.frustum("head", "purple", (0, 1.9, 0.02), (0, 1.93, 0.4), (0.18, 0.16), (0.12, 0.11), sides=6)
    H.frustum("head", "purple", (0, 1.93, 0.36), (0, 1.9, 0.7), (0.11, 0.1), (0.055, 0.05), sides=6)
    H.frustum("jaw", "purple_dk", (0, 1.84, 0.3), (0, 1.82, 0.62), (0.075, 0.04), (0.04, 0.025), sides=4)
    for s in (-1, 1):
        H.frustum("head", "black", (s * 0.1, 1.97, 0.06), (s * 0.19, 2.12, -0.02), (0.05, 0.05), (0.012, 0.012), sides=4)
        H.box("head", "green", (s * 0.08, 1.97, 0.4), (0.03, 0.03, 0.1))


def neck_torso():
    H.frustum("neck.1", "purple", (0, 1.08, 0.2), (0, 1.5, 0.2), (0.26, 0.23), (0.19, 0.19), sides=8)
    H.frustum("neck.2", "purple", (0, 1.46, 0.2), (0, 1.9, 0.12), (0.19, 0.19), (0.16, 0.16), sides=8)
    H.frustum("neck.1", "green", (0, 1.12, 0.38), (0, 1.5, 0.4), (0.14, 0.1), (0.09, 0.07), sides=6)
    H.frustum("neck.2", "green", (0, 1.46, 0.4), (0, 1.84, 0.3), (0.09, 0.07), (0.07, 0.05), sides=6)
    H.frustum("neck.1", "collar", (0, 1.2, 0.2), (0, 1.32, 0.2), (0.26, 0.24), (0.26, 0.24), sides=8)
    H.frustum("spine.1", "purple", (0, 0.86, -0.46), (0, 1.0, -0.05), (0.3, 0.24), (0.34, 0.26), sides=8)
    H.frustum("spine.2", "purple", (0, 0.96, -0.08), (0, 1.2, 0.24), (0.34, 0.26), (0.34, 0.22), sides=8)
    H.frustum("spine.2", "olive", (0, 0.92, 0.04), (0, 1.2, 0.26), (0.2, 0.05), (0.22, 0.05), sides=4)
    H.frustum("spine.1", "olive", (0, 0.8, -0.2), (0, 0.9, 0.0), (0.12, 0.2), (0.2, 0.24), sides=4)
    H.frustum("spine.2", "green", (0, 1.04, 0.3), (0, 1.16, 0.32), (0.03, 0.02), (0.05, 0.02), sides=4)


def tail():
    for i in range(3):
        H.frustum(f"tail.{i + 1}", "purple", TAIL[i], TAIL[i + 1], TAIL_R[i], TAIL_R[i + 1], sides=6)
        H.frustum(f"tail.{i + 1}", "olive", (0, TAIL[i][1] - 0.08, TAIL[i][2]), (0, TAIL[i + 1][1] - 0.04, TAIL[i + 1][2]),
                  (0.05, 0.05), (0.03, 0.03), sides=4)
    end = TAIL[3]
    for s in (-1, 1):
        H.frustum("tail.3", "black", (0, end[1], end[2] + 0.05), (s * 0.12, end[1], end[2] - 0.2), (0.03, 0.035), (0.04, 0.04), sides=4)
        H.frustum("tail.3", "black", (s * 0.12, end[1], end[2] - 0.18), (s * 0.2, end[1], end[2] - 0.42), (0.04, 0.04), (0.008, 0.008), sides=4)


def hind_legs():
    for s, n in ((1, 3), (-1, 4)):
        x = s * HIP[0]
        k, t = (s * KNEE[0], KNEE[1], KNEE[2]), (s * TOE[0], TOE[1], TOE[2])
        H.frustum(f"leg{n}.upper", "purple", (x, HIP[1] + 0.12, HIP[2]), k, (0.2, 0.22), (0.13, 0.13), sides=6)
        H.frustum(f"leg{n}.upper", "purple_dk", (x * 0.9, HIP[1] - 0.05, HIP[2] + 0.05), (x * 1.0, 0.7, HIP[2] - 0.12), (0.2, 0.2), (0.14, 0.14), sides=6)
        H.frustum(f"leg{n}.lower", "purple", (k[0], k[1] + 0.03, k[2]), (t[0], 0.16, t[2]), (0.15, 0.15), (0.09, 0.09), sides=6)
        H.frustum(f"leg{n}.lower", "purple_dk", (t[0], 0.16, t[2] - 0.02), (t[0], 0.04, t[2] + 0.22), (0.07, 0.06), (0.11, 0.04), sides=6)
        for dx in (-0.07, 0, 0.07):
            H.frustum(f"leg{n}.lower", "black", (t[0] + dx, 0.05, t[2] + 0.2), (t[0] + dx * 1.3, 0.0, t[2] + 0.38), (0.025, 0.03), (0.005, 0.005), sides=4)


def fore_legs():
    for s, n in ((1, 1), (-1, 2)):
        sh, el, hd = flip(SH, s), flip(EL, s), flip(HAND, s)
        H.frustum(f"leg{n}.upper", "purple", (sh[0], sh[1] + 0.1, sh[2]), el, (0.12, 0.12), (0.08, 0.08), sides=6)
        H.frustum(f"leg{n}.lower", "purple_dk", (el[0], el[1] + 0.02, el[2]), hd, (0.08, 0.08), (0.06, 0.06), sides=6)
        for dx in (-0.04, 0.04):
            H.frustum(f"leg{n}.lower", "black", (hd[0] + dx, hd[1], hd[2]), (hd[0] + dx, hd[1] - 0.12, hd[2] + 0.1), (0.02, 0.02), (0.004, 0.004), sides=4)


def wing(s, n):
    up, low = f"wing{n}.upper", f"wing{n}.lower"
    sh, wr, root = flip(SHOULDER, s), flip(WRIST, s), flip(ROOT, s)
    tips = [flip(f, s) for f in FINGERS]
    H.frustum(up, "purple", sh, wr, (0.17, 0.14), (0.1, 0.1), sides=6)
    H.frustum(low, "purple", wr, tips[0], (0.1, 0.1), (0.025, 0.025), sides=6)
    for tip in tips[1:]:
        H.frustum(low, "purple_dk", wr, tip, (0.05, 0.05), (0.02, 0.02), sides=4)
    for i in range(3):
        a, b = tips[i], tips[i + 1]
        H.panel(low, "olive", [wr, a, lerp(lerp(a, b, 0.5), wr, 0.22), b])
    inner = H.panel(up, "olive", [sh, wr, tips[3], root])
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


H.build("n01D", "drake", PALETTE, make, joints())
