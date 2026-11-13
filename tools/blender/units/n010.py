"""Dragao Azul (n010, familia drake): medido em artifacts/model-sheets/refs/n010/sheet.jpg (0,0042 m por pixel).

    blender -b --factory-startup -P tools/blender/units/n010.py -- <out.glb>

Pescoco longo e fino, torso largo, cauda reta e fina, asas roxas com borda azul clara. Asa: braco e dedos como
frustos, placas de membrana no osso lower, placa interna macia entre upper e lower.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "blue": 0x3050C0, "blue_dk": 0x24409C, "edge": 0xB0C4FA, "purple": 0x8C38C8, "purple_dk": 0x4C1C8C,
    "cyan": 0x30E8F0, "cream": 0xD8D4D0, "spine": 0xAA44CC, "dark": 0x2C1C4C, "ring": 0x9CA8E8,
}

SPINE = [(0, 0.46, -0.2), (0, 0.62, 0.2), (0, 0.95, 0.55)]
NECK = [(0, 0.98, 0.5), (0, 1.2, 0.65), (0, 1.38, 0.85)]
HEAD_TIP, JAW_A, JAW_B = (0, 1.4, 1.47), (0, 1.3, 0.95), (0, 1.28, 1.4)
TAIL = [(0, 0.45, -0.13), (0, 0.42, -0.6), (0, 0.38, -1.1), (0, 0.35, -1.6)]
FRONT = {"hip": (0.3, 0.75, 0.6), "elbow": (0.36, 0.5, 0.62), "hand": (0.3, 0.35, 0.85)}
HIND = {"hip": (0.24, 0.5, -0.1), "knee": (0.3, 0.28, -0.45), "foot": (0.28, 0.03, -0.2)}
SHOULDER, WRIST, ROOT = (0.3, 1.0, 0.45), (0.55, 1.65, 0.05), (0.25, 0.7, -0.15)
FINGERS = [(0.67, 2.2, -1.1), (1.0, 1.5, -0.9), (0.9, 0.85, -0.6), (0.45, 0.75, -0.2)]


def flip(p, s):
    return (p[0] * s, p[1], p[2])


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def head():
    H.frustum("head", "blue", (0, 1.38, 0.8), (0, 1.4, 1.1), (0.12, 0.11), (0.09, 0.08), sides=6)
    H.frustum("head", "blue", (0, 1.4, 1.08), (0, 1.38, 1.47), (0.09, 0.08), (0.04, 0.035), sides=6)
    H.frustum("jaw", "cream", (0, 1.31, 0.95), (0, 1.3, 1.4), (0.08, 0.04), (0.035, 0.02), sides=6)
    H.frustum("head", "cyan", (0, 1.29, 0.98), (0, 1.29, 1.2), (0.05, 0.03), (0.03, 0.02), sides=4)
    for s in (-1, 1):
        H.box("head", "cyan", (s * 0.09, 1.45, 1.12), (0.04, 0.03, 0.06))
        H.frustum("head", "blue_dk", (s * 0.1, 1.46, 0.86), (s * 0.15, 1.66, 0.74), (0.045, 0.045), (0.01, 0.01), sides=4)
    for z in (0.95, 0.8):
        H.frustum("head", "spine", (0, 1.45, z), (0, 1.58, z - 0.1), (0.015, 0.05), (0.005, 0.01), sides=4)


def body():
    H.frustum("spine.1", "blue", (0, 0.46, -0.25), (0, 0.62, 0.22), (0.19, 0.17), (0.3, 0.26), sides=8)
    H.frustum("spine.2", "blue", (0, 0.6, 0.15), (0, 0.97, 0.58), (0.3, 0.26), (0.24, 0.2), sides=8)
    H.frustum("spine.2", "cream", (0, 0.62, 0.3), (0, 1.0, 0.7), (0.17, 0.05), (0.14, 0.05), sides=6)
    H.frustum("spine.1", "cream", (0, 0.38, -0.25), (0, 0.5, 0.25), (0.07, 0.05), (0.13, 0.05), sides=4)
    H.chain(["neck.1", "neck.2"], "blue", NECK, [(0.17, 0.16), (0.09, 0.09), (0.08, 0.08)], sides=6)
    H.frustum("neck.1", "ring", (0, 1.0, 0.5), (0, 1.12, 0.57), (0.14, 0.14), (0.12, 0.12), sides=8)
    H.box("neck.1", "cyan", (0.16, 1.06, 0.58), (0.07, 0.08, 0.05))
    H.frustum("neck.2", "cyan", (0, 1.22, 0.74), (0, 1.3, 0.85), (0.04, 0.05), (0.04, 0.03), sides=4)
    for z, y, bone in ((0.45, 1.0, "spine.2"), (0.2, 0.86, "spine.2"), (-0.05, 0.72, "spine.1"), (-0.3, 0.62, "spine.1")):
        H.frustum(bone, "spine", (0, y, z), (0, y + 0.13, z - 0.12), (0.045, 0.06), (0.01, 0.01), sides=4)


def tail():
    radii = [(0.14, 0.12), (0.08, 0.07), (0.05, 0.04), (0.012, 0.012)]
    for i in range(3):
        H.frustum(f"tail.{i + 1}", "blue", TAIL[i], TAIL[i + 1], radii[i], radii[i + 1], sides=6)
        a, b = TAIL[i], TAIL[i + 1]
        H.frustum(f"tail.{i + 1}", "spine", (0, a[1] + radii[i][1] - 0.01, a[2]), (0, b[1] + radii[i + 1][1] + 0.03, b[2]), (0.02, 0.02), (0.008, 0.008), sides=4)


def legs():
    for s, n in ((1, 1), (-1, 2)):
        hip, el, hd = (flip(FRONT[k], s) for k in ("hip", "elbow", "hand"))
        H.frustum(f"leg{n}.upper", "blue_dk", hip, el, (0.12, 0.12), (0.08, 0.08), sides=6)
        H.frustum(f"leg{n}.lower", "blue_dk", el, hd, (0.075, 0.075), (0.09, 0.07), sides=6)
        for dx in (-0.04, 0, 0.04):
            H.frustum(f"leg{n}.lower", "dark", (hd[0] + dx, hd[1], hd[2]), (hd[0] + dx, hd[1] - 0.1, hd[2] + 0.08), (0.02, 0.02), (0.005, 0.005), sides=4)
    for s, n in ((1, 3), (-1, 4)):
        hip, kn, ft = (flip(HIND[k], s) for k in ("hip", "knee", "foot"))
        H.frustum(f"leg{n}.upper", "blue", (hip[0], hip[1] + 0.06, hip[2]), kn, (0.18, 0.2), (0.09, 0.09), sides=6)
        H.frustum(f"leg{n}.lower", "blue", kn, (ft[0], ft[1] + 0.06, ft[2]), (0.09, 0.09), (0.065, 0.065), sides=6)
        H.frustum(f"leg{n}.lower", "blue_dk", (ft[0], 0.09, ft[2] - 0.02), (ft[0], 0.02, ft[2] + 0.12), (0.07, 0.05), (0.1, 0.03), sides=6)
        for dx in (-0.05, 0, 0.05):
            H.frustum(f"leg{n}.lower", "dark", (ft[0] + dx, 0.03, ft[2] + 0.1), (ft[0] + dx, 0.0, ft[2] + 0.22), (0.02, 0.02), (0.005, 0.005), sides=4)


def wing(s, n):
    up, low = f"wing{n}.upper", f"wing{n}.lower"
    sh, wr, root = flip(SHOULDER, s), flip(WRIST, s), flip(ROOT, s)
    tips = [flip(f, s) for f in FINGERS]
    H.frustum(up, "edge", sh, wr, (0.1, 0.09), (0.06, 0.06), sides=6)
    H.frustum(low, "edge", wr, tips[0], (0.06, 0.06), (0.02, 0.02), sides=4)
    H.frustum(low, "edge", tips[0], (tips[0][0] - 0.05 * s, tips[0][1] + 0.12, tips[0][2] + 0.08), (0.025, 0.025), (0.006, 0.006), sides=4)
    for tip in tips[1:]:
        H.frustum(low, "edge", wr, tip, (0.04, 0.04), (0.015, 0.015), sides=4)
    for i in range(3):
        a, b = tips[i], tips[i + 1]
        H.panel(low, "purple" if i != 1 else "purple_dk", [wr, a, lerp(lerp(a, b, 0.5), wr, 0.1), b], 0.04)
    inner = H.panel(up, "purple_dk", [sh, wr, tips[3], root], 0.05)
    H.box(low, "dark", lerp(wr, tips[1], 0.5), (0.3, 0.3, 0.05))
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


H.build("n010", "drake", PALETTE, make, joints())
