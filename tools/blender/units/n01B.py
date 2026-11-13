"""Dragao Sombrio (n01B, familia drake): medido em artifacts/model-sheets/refs/n01B/sheet.jpg (0,0042 m por pixel).

    blender -b --factory-startup -P tools/blender/units/n01B.py -- <out.glb>

Roxo escuro, garganta verde brilhante, chifres e espinhos magenta, asas oliva muito abertas, cauda terminando em garra
de duas pontas. Asa: braco e dedos como frustos, placas de membrana no osso lower, placa interna macia entre os dois.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "dark": 0x2A1A4E, "belly": 0x6C3A5C, "green": 0x58F030, "magenta": 0xB840A8, "membrane": 0x5C5A3C,
    "claw": 0x1E1A1A, "collar": 0x6A6A70, "eye": 0x60FF40, "tooth": 0xBFEFEF,
}

SPINE = [(0, 0.85, -0.1), (0, 1.0, 0.3), (0, 1.3, 0.7)]
NECK = [(0, 1.3, 0.72), (0, 1.52, 0.72), (0, 1.74, 0.68)]
HEAD_TIP, JAW_A, JAW_B = (0, 1.76, 1.17), (0, 1.68, 0.8), (0, 1.62, 1.1)
TAIL = [(0, 0.85, -0.1), (0, 0.85, -0.55), (0, 0.88, -1.05), (0, 0.9, -1.6)]
FRONT = {"hip": (0.3, 1.05, 0.55), "elbow": (0.4, 0.7, 0.72), "hand": (0.32, 0.32, 0.9)}
HIND = {"hip": (0.34, 0.85, -0.05), "knee": (0.46, 0.55, -0.4), "foot": (0.36, 0.06, -0.2)}
SHOULDER, WRIST, ROOT = (0.3, 1.6, 0.45), (0.85, 2.0, 0.0), (0.3, 1.0, -0.2)
FINGERS = [(1.45, 2.2, -0.6), (1.15, 1.45, -0.55), (0.75, 1.15, -0.5), (0.4, 1.1, -0.3)]


def flip(p, s):
    return (p[0] * s, p[1], p[2])


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def head():
    H.frustum("head", "dark", (0, 1.77, 0.6), (0, 1.8, 0.92), (0.17, 0.15), (0.12, 0.11), sides=6)
    H.frustum("head", "dark", (0, 1.8, 0.9), (0, 1.76, 1.17), (0.12, 0.1), (0.045, 0.04), sides=6)
    H.frustum("jaw", "dark", (0, 1.68, 0.78), (0, 1.62, 1.1), (0.1, 0.05), (0.04, 0.03), sides=6)
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.1, 1.84, 0.92), (0.05, 0.04, 0.08))
        H.frustum("head", "magenta", (s * 0.1, 1.9, 0.68), (s * 0.2, 2.28, 0.6), (0.05, 0.05), (0.01, 0.01), sides=4)
        H.frustum("head", "tooth", (s * 0.06, 1.72, 1.1), (s * 0.06, 1.66, 1.12), (0.015, 0.015), (0.004, 0.004), sides=4)
    for z, y in ((0.55, 1.86), (0.42, 1.8)):
        H.frustum("head", "magenta", (0, y, z), (0, y + 0.14, z - 0.16), (0.02, 0.06), (0.005, 0.01), sides=4)


def body():
    H.frustum("spine.1", "dark", (0, 0.85, -0.2), (0, 1.0, 0.32), (0.22, 0.2), (0.34, 0.3), sides=8)
    H.frustum("spine.2", "dark", (0, 0.98, 0.25), (0, 1.32, 0.76), (0.34, 0.3), (0.28, 0.24), sides=8)
    H.frustum("spine.2", "belly", (0, 0.92, 0.45), (0, 1.3, 0.92), (0.22, 0.06), (0.2, 0.06), sides=6)
    H.frustum("spine.1", "belly", (0, 0.72, -0.1), (0, 0.84, 0.4), (0.1, 0.06), (0.2, 0.06), sides=6)
    H.chain(["neck.1", "neck.2"], "dark", NECK, [(0.22, 0.2), (0.14, 0.14), (0.12, 0.12)], sides=6)
    H.frustum("neck.1", "green", (0, 1.32, 0.78), (0, 1.62, 0.8), (0.13, 0.1), (0.1, 0.08), sides=6)
    H.frustum("neck.1", "collar", (0, 1.3, 0.72), (0, 1.42, 0.74), (0.25, 0.22), (0.2, 0.18), sides=8)
    for z, y, bone in ((0.6, 1.45, "neck.1"), (0.55, 1.65, "neck.2"), (0.4, 1.3, "spine.2"), (0.15, 1.15, "spine.2"),
                       (-0.1, 1.03, "spine.1"), (-0.4, 0.95, "tail.1"), (-0.8, 0.95, "tail.2")):
        H.frustum(bone, "magenta", (0, y, z - 0.2), (0, y + 0.18, z - 0.36), (0.02, 0.07), (0.005, 0.01), sides=4)


def tail():
    radii = [(0.17, 0.15), (0.1, 0.09), (0.06, 0.055), (0.03, 0.03)]
    for i in range(3):
        H.frustum(f"tail.{i + 1}", "dark", TAIL[i], TAIL[i + 1], radii[i], radii[i + 1], sides=6)
        a, b = TAIL[i], TAIL[i + 1]
        H.frustum(f"tail.{i + 1}", "belly", (0, a[1] - radii[i][1] + 0.02, a[2]), (0, b[1] - radii[i + 1][1] + 0.02, b[2]), (0.04, 0.03), (0.015, 0.015), sides=4)
    for s in (-1, 1):
        H.chain("tail.3", "claw", [TAIL[3], (s * 0.14, 0.9, -1.8), (s * 0.3, 0.9, -2.0)], [(0.04, 0.04), (0.035, 0.035), (0.01, 0.01)], sides=4)


def toes(bone, p, s, y, ln):
    for dx in (-0.05, 0, 0.05):
        H.frustum(bone, "claw", (p[0] + dx, y + 0.03, p[2] + 0.05), (p[0] + dx * 1.6, y - 0.02, p[2] + ln), (0.025, 0.025), (0.005, 0.005), sides=4)


def legs():
    for s, n in ((1, 1), (-1, 2)):
        hip, el, hd = (flip(FRONT[k], s) for k in ("hip", "elbow", "hand"))
        H.frustum(f"leg{n}.upper", "dark", hip, el, (0.14, 0.14), (0.1, 0.1), sides=6)
        H.frustum(f"leg{n}.lower", "dark", el, hd, (0.09, 0.09), (0.11, 0.09), sides=6)
        toes(f"leg{n}.lower", hd, s, hd[1] - 0.02, 0.2)
    for s, n in ((1, 3), (-1, 4)):
        hip, kn, ft = (flip(HIND[k], s) for k in ("hip", "knee", "foot"))
        H.frustum(f"leg{n}.upper", "dark", (hip[0], hip[1] + 0.1, hip[2]), kn, (0.24, 0.26), (0.12, 0.12), sides=6)
        H.frustum(f"leg{n}.lower", "dark", kn, (ft[0], ft[1] + 0.1, ft[2]), (0.11, 0.11), (0.08, 0.08), sides=6)
        H.frustum(f"leg{n}.lower", "dark", (ft[0], ft[1] + 0.1, ft[2]), (ft[0], 0.03, ft[2] + 0.06), (0.08, 0.07), (0.12, 0.05), sides=6)
        toes(f"leg{n}.lower", ft, s, 0.03, 0.22)


def wing(s, n):
    up, low = f"wing{n}.upper", f"wing{n}.lower"
    sh, wr, root = flip(SHOULDER, s), flip(WRIST, s), flip(ROOT, s)
    tips = [flip(f, s) for f in FINGERS]
    H.frustum(up, "dark", sh, wr, (0.11, 0.1), (0.07, 0.07), sides=6)
    H.frustum(up, "magenta", wr, (wr[0] - 0.12 * s, wr[1] + 0.3, wr[2] + 0.1), (0.06, 0.06), (0.01, 0.01), sides=4)
    H.frustum(low, "dark", wr, tips[0], (0.07, 0.07), (0.025, 0.025), sides=4)
    for tip in tips[1:]:
        H.frustum(low, "dark", wr, tip, (0.05, 0.05), (0.02, 0.02), sides=4)
    for i in range(3):
        a, b = tips[i], tips[i + 1]
        H.panel(low, "membrane", [wr, a, lerp(lerp(a, b, 0.5), wr, 0.2), b], 0.04)
    inner = H.panel(up, "membrane", [sh, wr, tips[3], root], 0.05)
    key = [(wr, 1.0), (tips[3], 1.0), (sh, 0.0), (root, 0.0)]

    def weigh(p):
        near = min(key, key=lambda k: sum((p[i] - k[0][i]) ** 2 for i in range(3)))[1]
        return {low: near, up: 1.0 - near}

    H.soft(inner, weigh)


def make():
    head()
    body()
    tail()
    legs()
    wing(1, 1)
    wing(-1, 2)


def joints():
    out = {"spine.1": (SPINE[0], SPINE[1]), "spine.2": (SPINE[1], SPINE[2]),
           "neck.1": (NECK[0], NECK[1]), "neck.2": (NECK[1], NECK[2]),
           "head": (NECK[2], HEAD_TIP), "jaw": (JAW_A, JAW_B)}
    for i in range(3):
        out[f"tail.{i + 1}"] = (TAIL[i], TAIL[i + 1])
    for s, n in ((1, 1), (-1, 2)):
        out[f"leg{n}.upper"] = (flip(FRONT["hip"], s), flip(FRONT["elbow"], s))
        out[f"leg{n}.lower"] = (flip(FRONT["elbow"], s), flip(FRONT["hand"], s))
        out[f"wing{n}.upper"] = (flip(SHOULDER, s), flip(WRIST, s))
        out[f"wing{n}.lower"] = (flip(WRIST, s), flip(FINGERS[0], s))
    for s, n in ((1, 3), (-1, 4)):
        out[f"leg{n}.upper"] = (flip(HIND["hip"], s), flip(HIND["knee"], s))
        out[f"leg{n}.lower"] = (flip(HIND["knee"], s), flip(HIND["foot"], s))
    return out


H.build("n01B", "drake", PALETTE, make, joints())
