"""Dragao Faerie (e000, familia drake): medido em artifacts/model-sheets/refs/e000/sheet.jpg (0,0026 m por pixel).

    blender -b --factory-startup -P tools/blender/units/e000.py -- <out.glb>

Lagarto baixo de quatro patas com asas enormes de membrana (laranja, magenta, roxo) erguidas em V, cauda em espiral.
Asa: braco e dedos como frustos, placas de membrana no osso lower, placa interna macia entre upper e lower.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "teal": 0x2A6068, "green": 0x62B868, "cream": 0xCFE0BC, "magenta": 0xB8328A, "orange": 0xF58A32,
    "purple": 0x522870, "red": 0xC83C32, "blue": 0x5AAEDC, "eye": 0x6A2A6A, "white": 0xF4F4F4,
    "ring": 0x9A98A0, "tail": 0x6CBC50, "claw": 0xB8D8A8, "shine": 0xFFFFFF,
}

SPINE = [(0, 0.27, -0.2), (0, 0.3, 0.05), (0, 0.34, 0.3)]
NECK = [(0, 0.34, 0.3), (0, 0.4, 0.5), (0, 0.44, 0.68)]
HEAD_TIP, JAW_A, JAW_B = (0, 0.4, 0.98), (0, 0.38, 0.62), (0, 0.36, 0.92)
TAIL = [(0, 0.26, -0.16), (0, 0.18, -0.5), (0, 0.1, -0.85), (0, 0.12, -1.1)]
CURL = [(0, 0.12, -1.1), (0, 0.28, -1.19), (0, 0.48, -1.1), (0, 0.55, -0.93), (0, 0.45, -0.83), (0, 0.33, -0.9), (0, 0.38, -1.0)]
FRONT = {"hip": (0.12, 0.26, 0.28), "elbow": (0.3, 0.14, 0.32), "hand": (0.18, 0.03, 0.44)}
HIND = {"hip": (0.13, 0.26, -0.15), "knee": (0.4, 0.17, -0.1), "foot": (0.46, 0.03, -0.3)}
SHOULDER, WRIST, ROOT = (0.13, 0.42, 0.25), (0.2, 1.35, 0.1), (0.14, 0.4, -0.35)
FINGERS = [(0.62, 2.0, -0.32), (0.9, 1.5, -0.4), (0.62, 0.9, -0.5), (0.36, 0.62, -0.55)]


def flip(p, s):
    return (p[0] * s, p[1], p[2])


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def head():
    H.frustum("head", "teal", (0, 0.4, 0.55), (0, 0.4, 0.78), (0.15, 0.11), (0.1, 0.08), sides=6)
    H.frustum("head", "teal", (0, 0.4, 0.76), (0, 0.39, 0.98), (0.1, 0.075), (0.035, 0.03), sides=6)
    H.frustum("jaw", "cream", (0, 0.35, 0.62), (0, 0.35, 0.93), (0.09, 0.04), (0.03, 0.02), sides=6)
    for s in (-1, 1):
        H.frustum("head", "eye", (s * 0.1, 0.48, 0.66), (s * 0.16, 0.5, 0.66), (0.065, 0.065), (0.055, 0.055), sides=6)
        H.box("head", "shine", (s * 0.15, 0.53, 0.69), (0.02, 0.02, 0.02))
    H.frustum("head", "red", (0, 0.5, 0.58), (0, 0.66, 0.5), (0.03, 0.06), (0.01, 0.02), sides=4)
    H.frustum("head", "red", (0, 0.49, 0.5), (0, 0.6, 0.38), (0.02, 0.06), (0.01, 0.02), sides=4)


def body():
    H.frustum("spine.1", "teal", (0, 0.27, -0.28), (0, 0.3, 0.05), (0.13, 0.1), (0.2, 0.15), sides=8)
    H.frustum("spine.2", "teal", (0, 0.3, 0.0), (0, 0.34, 0.34), (0.2, 0.15), (0.15, 0.12), sides=8)
    H.frustum("spine.2", "cream", (0, 0.2, 0.02), (0, 0.22, 0.4), (0.1, 0.06), (0.1, 0.05), sides=6)
    H.chain(["neck.1", "neck.2"], "teal", NECK, [(0.14, 0.12), (0.1, 0.09), (0.09, 0.08)], sides=6)
    H.chain(["neck.1", "neck.2"], "cream", [(0, 0.3, 0.32), (0, 0.34, 0.5), (0, 0.38, 0.66)],
            [(0.06, 0.05), (0.05, 0.05), (0.04, 0.04)], sides=4)
    for z, bone in ((0.4, "spine.2"), (0.25, "spine.2"), (0.1, "spine.2"), (-0.1, "spine.1")):
        H.frustum(bone, "red", (0, 0.4, z), (0, 0.55 if z > 0 else 0.5, z - 0.14), (0.015, 0.07), (0.005, 0.01), sides=4)


def tail():
    radii = [(0.13, 0.1), (0.09, 0.07), (0.055, 0.05), (0.035, 0.03)]
    for i in range(3):
        H.frustum(f"tail.{i + 1}", "teal", TAIL[i], TAIL[i + 1], radii[i], radii[i + 1], sides=6)
        a, b = TAIL[i], TAIL[i + 1]
        H.frustum(f"tail.{i + 1}", "cream", (0, a[1] - 0.06, a[2]), (0, b[1] - 0.04, b[2]), (0.035, 0.03), (0.02, 0.02), sides=4)
    H.chain("tail.3", "tail", CURL, [(0.035, 0.03), (0.03, 0.03), (0.027, 0.027), (0.025, 0.025), (0.022, 0.022), (0.018, 0.018), (0.01, 0.01)], sides=4)


def claws(bone, p, s):
    for dx in (-0.05, 0, 0.05):
        H.frustum(bone, "claw", (p[0] + dx * s, 0.03, p[2]), (p[0] + dx * 2.2 * s, 0.01, p[2] + 0.12), (0.022, 0.02), (0.005, 0.005), sides=4)


def legs():
    for s, n in ((1, 1), (-1, 2)):
        hip, el, hd = (flip(FRONT[k], s) for k in ("hip", "elbow", "hand"))
        H.frustum(f"leg{n}.upper", "green", hip, el, (0.085, 0.085), (0.06, 0.06), sides=6)
        H.frustum(f"leg{n}.lower", "green", el, hd, (0.065, 0.065), (0.045, 0.045), sides=6)
        H.frustum(f"leg{n}.lower", "green", (hd[0], 0.05, hd[2] - 0.02), (hd[0], 0.02, hd[2] + 0.05), (0.07, 0.04), (0.08, 0.02), sides=6)
        claws(f"leg{n}.lower", hd, s)
    for s, n in ((1, 3), (-1, 4)):
        hip, kn, ft = (flip(HIND[k], s) for k in ("hip", "knee", "foot"))
        H.frustum(f"leg{n}.upper", "green", (hip[0], hip[1] + 0.02, hip[2]), kn, (0.13, 0.13), (0.07, 0.07), sides=6)
        H.frustum(f"leg{n}.lower", "green", kn, ft, (0.07, 0.07), (0.05, 0.05), sides=6)
        H.frustum(f"leg{n}.lower", "green", (ft[0], 0.05, ft[2] - 0.02), (ft[0], 0.02, ft[2] + 0.06), (0.08, 0.05), (0.1, 0.02), sides=6)
        claws(f"leg{n}.lower", ft, s)


def wing(s, n):
    up, low = f"wing{n}.upper", f"wing{n}.lower"
    sh, wr, root = flip(SHOULDER, s), flip(WRIST, s), flip(ROOT, s)
    tips = [flip(f, s) for f in FINGERS]
    H.frustum(up, "teal", sh, wr, (0.09, 0.08), (0.05, 0.05), sides=6)
    H.frustum(up, "ring", lerp(sh, wr, 0.8), lerp(sh, wr, 0.88), (0.075, 0.075), (0.075, 0.075), sides=6)
    H.frustum(low, "teal", wr, (wr[0] + 0.03 * s, wr[1] + 0.2, wr[2] + 0.12), (0.045, 0.045), (0.01, 0.01), sides=4)
    for tip in tips:
        H.frustum(low, "teal", wr, tip, (0.04, 0.04), (0.012, 0.012), sides=4)
    for i in range(3):
        a, b = tips[i], tips[i + 1]
        edge = lerp(lerp(a, b, 0.5), wr, 0.18)
        H.panel(low, "purple", [wr, a, edge, b], 0.03)
        H.panel(low, "magenta", [wr, lerp(wr, a, 0.82), lerp(edge, wr, 0.2), lerp(wr, b, 0.82)], 0.05)
        H.panel(low, "orange", [wr, lerp(wr, a, 0.45), lerp(wr, b, 0.45)], 0.07)
    inner = H.panel(up, "magenta", [sh, wr, tips[3], root], 0.04)
    H.panel(up, "orange", [sh, lerp(sh, wr, 0.75), lerp(tips[3], wr, 0.3), lerp(root, sh, 0.3)], 0.06)
    key = [(wr, 1.0), (tips[3], 1.0), (sh, 0.0), (root, 0.0)]

    def weigh(p):
        near = min(key, key=lambda k: sum((p[i] - k[0][i]) ** 2 for i in range(3)))[1]
        return {low: near, up: 1.0 - near}

    H.soft(inner, weigh)
    H.box(low, "white", lerp(wr, tips[1], 0.6), (0.08, 0.08, 0.08))


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


H.build("e000", "drake", PALETTE, make, joints())
