"""Feathered Friend (perk_bird), bird family: measured on artifacts/model-sheets/refs/perk_bird/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/perk_bird.py -- <out.glb>

Scale 103 px per metre off the front/profile panels, ground y=0, head at +z. A round dark-grey bird with a
blue satchel on the breast, gold goggles, a pointed beak, swept-back wings drooping to feathered trailing
edges, a drooping tail fan and tiny legs.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "body": 0x4B534D, "body_lt": 0x5C665D, "feather": 0x3B403C, "dark": 0x2F3330, "beak": 0x3A3C3A,
    "blue": 0x2D62D0, "blue_dk": 0x234FAE, "gold": 0xB08A3A, "eye": 0x0E0E0E, "claw": 0x2A2A2A,
}
SH, WR, TIP, ROOT = (0.42, 1.05, 0.15), (1.0, 1.1, -0.05), (1.65, 1.0, -0.45), (0.4, 0.7, -0.5)
FEATHERS = [(1.64, 0.85, -0.7), (1.52, 0.74, -0.88), (1.36, 0.64, -1.02), (1.18, 0.58, -1.12), (0.98, 0.55, -1.1)]
TAIL = [(0, 0.5, -0.45), (0, 0.4, -0.75), (0, 0.3, -1.0), (0, 0.22, -1.2)]
LEG = ((0.12, 0.3, 0.1), (0.12, 0.15, 0.12), (0.12, 0.03, 0.15))


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def flip(p, s):
    return (p[0] * s, p[1], p[2])


def body():
    H.frustum("spine.1", "body", (0, 0.68, -0.55), (0, 0.66, -0.25), (0.3, 0.3), (0.44, 0.5))
    H.frustum("spine.1", "body", (0, 0.66, -0.25), (0, 0.66, 0.1), (0.44, 0.5), (0.46, 0.54))
    H.frustum("spine.2", "body", (0, 0.66, 0.1), (0, 0.7, 0.48), (0.46, 0.54), (0.34, 0.42))
    H.frustum("spine.2", "body_lt", (0, 0.5, -0.1), (0, 0.52, 0.5), (0.3, 0.08), (0.26, 0.08), sides=4)
    H.frustum("neck.1", "body", (0, 1.0, 0.3), (0, 1.2, 0.38), (0.34, 0.3), (0.28, 0.26))
    H.frustum("neck.2", "body", (0, 1.2, 0.38), (0, 1.32, 0.4), (0.28, 0.26), (0.24, 0.24))


def head():
    for (z0, r0), (z1, r1) in zip(((0.12, 0.22), (0.3, 0.3), (0.5, 0.28)), ((0.3, 0.3), (0.5, 0.28), (0.64, 0.18))):
        H.frustum("head", "body", (0, 1.36, z0), (0, 1.37, z1), (r0, r0), (r1, r1))
    H.frustum("head", "gold", (0, 1.46, 0.37), (0, 1.54, 0.37), (0.32, 0.3), (0.3, 0.28))
    H.frustum("head", "dark", (0, 1.31, 0.6), (0, 1.27, 0.95), (0.13, 0.11), (0.012, 0.012), sides=4)
    for s in (-1, 1):
        H.frustum("head", "gold", (s * 0.12, 1.5, 0.52), (s * 0.12, 1.5, 0.66), (0.1, 0.1), (0.09, 0.09), sides=6)
        H.frustum("head", "eye", (s * 0.12, 1.4, 0.6), (s * 0.12, 1.4, 0.7), (0.05, 0.05), (0.04, 0.04), sides=6)


def satchel():
    H.box("spine.2", "blue", (0, 0.58, 0.58), (0.46, 0.4, 0.22))
    H.box("spine.2", "blue_dk", (0, 0.72, 0.6), (0.46, 0.1, 0.24))
    for s in (-1, 1):
        H.frustum("spine.2", "blue", (s * 0.3, 1.02, 0.28), (s * 0.2, 0.72, 0.58), (0.05, 0.05), (0.05, 0.05), sides=4)


def tail():
    radii = [(0.2, 0.06), (0.28, 0.055), (0.3, 0.045), (0.24, 0.035)]
    H.chain(["tail.1", "tail.2", "tail.3"], "feather", TAIL, radii, sides=4)


def legs():
    for s, n in ((1, 1), (-1, 2)):
        hip, knee, foot = (flip(p, s) for p in LEG)
        H.frustum(f"leg{n}.upper", "claw", hip, knee, (0.07, 0.07), (0.055, 0.055), sides=6)
        H.frustum(f"leg{n}.lower", "claw", knee, foot, (0.055, 0.055), (0.045, 0.045), sides=6)
        for dx in (-0.06, 0, 0.06):
            H.frustum(f"leg{n}.lower", "claw", (foot[0], 0.05, foot[2]), (foot[0] + dx, 0.01, foot[2] + 0.2),
                      (0.035, 0.03), (0.01, 0.01), sides=4)


def wing(s, n):
    up, low = f"wing{n}.upper", f"wing{n}.lower"
    sh, wr, tip, root = (flip(p, s) for p in (SH, WR, TIP, ROOT))
    tips = [flip(p, s) for p in FEATHERS]
    H.frustum(up, "body", sh, wr, (0.14, 0.12), (0.1, 0.09), sides=6)
    H.frustum(low, "feather", wr, tip, (0.1, 0.08), (0.03, 0.03), sides=6)
    for i in range(len(tips) - 1):
        a, b = tips[i], tips[i + 1]
        H.panel(low, "feather", [wr, a, lerp(lerp(a, b, 0.5), wr, 0.18), b])
    inner = H.panel(up, "body_lt", [sh, wr, tips[-1], root])
    key = [(wr, 1.0), (tips[-1], 1.0), (sh, 0.0), (root, 0.0)]

    def weigh(p):
        near = min(key, key=lambda k: sum((p[i] - k[0][i]) ** 2 for i in range(3)))[1]
        return {low: near, up: 1.0 - near}

    H.soft(inner, weigh)


def make():
    body()
    head()
    satchel()
    tail()
    legs()
    wing(1, 1)
    wing(-1, 2)


def joints():
    out = {"spine.1": ((0, 0.68, -0.55), (0, 0.66, 0.1)), "spine.2": ((0, 0.66, 0.1), (0, 0.7, 0.48)),
           "neck.1": ((0, 1.0, 0.3), (0, 1.2, 0.38)), "neck.2": ((0, 1.2, 0.38), (0, 1.32, 0.4)),
           "head": ((0, 1.32, 0.4), (0, 1.36, 0.95))}
    for i in range(3):
        out[f"tail.{i + 1}"] = (TAIL[i], TAIL[i + 1])
    for s, n in ((1, 1), (-1, 2)):
        out[f"leg{n}.upper"] = (flip(LEG[0], s), flip(LEG[1], s))
        out[f"leg{n}.lower"] = (flip(LEG[1], s), flip(LEG[2], s))
        out[f"wing{n}.upper"] = (flip(SH, s), flip(WR, s))
        out[f"wing{n}.lower"] = (flip(WR, s), flip(TIP, s))
    return out


H.build("perk_bird", "bird", PALETTE, make, joints())
