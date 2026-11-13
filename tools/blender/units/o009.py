"""Wyvern Rider (o009, familia mounted_flyer): goblin de capacete de cranio com fuzil de baioneta sobre leao alado de asas de morcego.

    blender -b --factory-startup -P tools/blender/units/o009.py -- <out.glb>

Montaria na escala da prancha (x1.5); piloto ~36 % da altura; fuzil grande a frente, bem acima da cabeca do leao.
Asas abertas para os lados e para tras (membrana presa ao ombro), sem cobrir o piloto.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "tan": 0xC99A5B, "tan_dk": 0x9A6E3C, "belly": 0xE0B98A, "mane": 0x4A2A1A, "spot": 0x6B3F22, "red": 0x84321E,
    "red_dk": 0x5E1E14, "finger": 0xD05A2A, "tail": 0x5A1E2E, "skin": 0x5BAA3C, "skin_dk": 0x3F7F2A,
    "skull": 0xE8DDC8, "feather": 0xF2EEE0, "vest": 0x6B4A2E, "wood": 0x6B3F26, "metal": 0x7A7C80,
    "steel": 0xB0B4BA, "claw": 0x2A1E18, "eye": 0xFFC010, "wrap": 0xA88458,
}


# Montaria na escala da prancha (x S); piloto menor (x R) sentado no dorso, fuzil exagerado (coordenadas locais do piloto).
S, R = 1.5, 0.9
MOUNT = {"k": S, "piv": (0.0, 0.0, 0.0), "org": (0.0, 0.0, 0.0)}
RIDER = {"k": R, "piv": (0.0, 1.25, 0.0), "org": (0.0, 1.25 * S, 0.0)}
XF = dict(MOUNT)


def use(xf):
    XF.update(xf)


def T(p, xf=None):
    xf = xf or XF
    return tuple(o + xf["k"] * (c - v) for c, v, o in zip(p, xf["piv"], xf["org"]))


def rad(r):
    return tuple(v * XF["k"] for v in r)


def fr(bone, tone, a, b, ra, rb, sides=8):
    ra, rb = (ra, ra) if isinstance(ra, float) else ra, (rb, rb) if isinstance(rb, float) else rb
    H.frustum(bone, tone, T(a), T(b), rad(ra), rad(rb), sides)


def chain(bones, tone, pts, radii):
    H.chain(bones, tone, [T(p) for p in pts], [rad(r) for r in radii])


def panel(bone, tone, pts, thickness):
    return H.panel(bone, tone, [T(p) for p in pts], thickness=thickness * XF["k"])


def torso():
    fr("spine.1", "tan", (0, 0.95, -0.9), (0, 0.95, -0.1), (0.38, 0.4), (0.5, 0.5))
    fr("spine.2", "tan", (0, 0.95, -0.15), (0, 1.0, 0.62), (0.5, 0.5), (0.48, 0.52))
    fr("spine.2", "belly", (0, 0.7, 0.2), (0, 0.8, 0.8), (0.34, 0.3), (0.3, 0.3), sides=6)
    for s, z, bone in ((1, -0.5, "spine.1"), (-1, -0.2, "spine.1"), (1, 0.3, "spine.2"), (-1, 0.1, "spine.2")):
        fr(bone, "spot", (s * 0.4, 1.0, z), (s * 0.55, 1.05, z), (0.12, 0.1), (0.1, 0.08), sides=6)


def neck_head():
    fr("neck.1", "tan", (0, 1.05, 0.6), (0, 1.4, 0.85), (0.38, 0.36), (0.32, 0.32))
    fr("neck.2", "mane", (0, 1.25, 0.65), (0, 1.8, 0.85), (0.6, 0.55), (0.5, 0.46))
    fr("neck.2", "mane", (0, 1.0, 0.6), (0, 1.5, 0.75), (0.5, 0.4), (0.62, 0.5))
    fr("head", "tan", (0, 1.62, 0.95), (0, 1.62, 1.38), (0.38, 0.38), (0.32, 0.33))
    fr("head", "tan", (0, 1.55, 1.3), (0, 1.5, 1.75), (0.26, 0.24), (0.2, 0.17), sides=6)
    fr("head", "claw", (0, 1.56, 1.72), (0, 1.56, 1.82), (0.11, 0.08), (0.1, 0.07), sides=6)
    for s in (-1, 1):
        fr("head", "eye", (s * 0.2, 1.74, 1.2), (s * 0.27, 1.74, 1.3), (0.05, 0.04), (0.035, 0.03), sides=6)
        fr("head", "mane", (s * 0.22, 1.9, 0.95), (s * 0.27, 2.05, 0.95), (0.1, 0.08), (0.07, 0.06), sides=6)


def legs():
    for s, f, h in ((1, "leg1", "leg3"), (-1, "leg2", "leg4")):
        for tag, z, thigh in ((f, 0.47, 0.22), (h, -0.47, 0.27)):
            x = s * 0.36
            fr(f"{tag}.upper", "tan", (x, 1.08, z), (x, 0.55, z + 0.03), (thigh, thigh + 0.02), (0.13, 0.14))
            fr(f"{tag}.lower", "tan_dk", (x, 0.58, z + 0.03), (x, 0.16, z + 0.03), (0.14, 0.14), (0.09, 0.1))
            fr(f"{tag}.lower", "tan_dk", (x, 0.18, z + 0.03), (x, 0.04, z + 0.2), (0.1, 0.1), (0.15, 0.07))
            fr(f"{tag}.lower", "claw", (x, 0.06, z + 0.2), (x, 0.0, z + 0.4), (0.12, 0.03), (0.07, 0.01), sides=6)


TAIL = [(0, 0.98, -0.75), (0, 0.95, -1.15), (0, 0.92, -1.55), (0, 0.9, -1.95)]


def tail():
    chain(("tail.1", "tail.2", "tail.3"), "tail", TAIL, [(0.2, 0.2), (0.14, 0.14), (0.1, 0.1), (0.07, 0.07)])
    fr("tail.3", "claw", (0, 0.9, -1.9), (0, 0.9, -2.35), (0.12, 0.05), (0.01, 0.01), sides=4)


SH, WR = (0.45, 1.5, 0.1), (1.6, 2.7, -0.15)
TIPS = [(2.7, 2.9, -0.5), (2.55, 1.6, -0.9), (1.9, 1.1, -1.3), (1.2, 1.0, -1.55)]
ROOT = (0.4, 1.05, -0.7)


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def flip(p, s):
    return (p[0] * s, p[1], p[2])


def wing(s, n):
    up, low = f"wing{n}.upper", f"wing{n}.lower"
    sh, wr, root = flip(SH, s), flip(WR, s), flip(ROOT, s)
    tips = [flip(t, s) for t in TIPS]
    fr(up, "tan", sh, wr, (0.18, 0.16), (0.12, 0.11), sides=6)
    for i, t in enumerate(tips):
        fr(low, "finger" if i else "tan", wr, t, (0.09, 0.08) if i == 0 else (0.06, 0.05), (0.02, 0.02), sides=4)
    for i in range(3):
        a, b = tips[i], tips[i + 1]
        scallop = lerp(lerp(a, b, 0.5), wr, 0.18)
        panel(low, "red" if i % 2 == 0 else "red_dk", [wr, a, scallop, b], 0.04)
    inner = panel(up, "red", [sh, wr, tips[3], root], 0.04)
    key = [(T(wr), 1.0), (T(tips[3]), 1.0), (T(sh), 0.0), (T(root), 0.0)]

    def weigh(p):
        near = min(key, key=lambda k: sum((p[i] - k[0][i]) ** 2 for i in range(3)))[1]
        return {low: near, up: 1.0 - near}

    H.soft(inner, weigh)
    fr(low, "claw", tips[0], (tips[0][0] + s * 0.05, tips[0][1] + 0.25, tips[0][2] + 0.05), (0.05, 0.05), (0.01, 0.01), sides=4)


def rider_body():
    fr("rider.spine", "wrap", (0, 1.25, 0.0), (0, 1.6, 0.0), (0.4, 0.34), (0.38, 0.3))
    fr("rider.spine", "skin", (0, 1.55, 0.0), (0, 2.3, 0.0), (0.36, 0.3), (0.52, 0.34))
    fr("rider.spine", "vest", (0, 1.7, -0.02), (0, 2.25, -0.02), (0.38, 0.33), (0.52, 0.36), sides=4)
    fr("rider.head", "skin", (0, 2.25, 0.04), (0, 2.8, 0.08), (0.36, 0.32), (0.42, 0.36))
    fr("rider.head", "skull", (0, 2.72, 0.08), (0, 3.0, 0.08), (0.44, 0.4), (0.28, 0.28))
    fr("rider.head", "claw", (0, 2.45, 0.38), (0, 2.62, 0.46), (0.2, 0.08), (0.2, 0.08), sides=4)
    for s in (-1, 1):
        fr("rider.head", "skin", (s * 0.3, 2.5, 0.05), (s * 0.7, 2.62, 0.0), (0.08, 0.06), (0.012, 0.012), sides=4)
        fr("rider.head", "eye", (s * 0.16, 2.55, 0.38), (s * 0.18, 2.55, 0.46), (0.06, 0.04), (0.04, 0.03), sides=4)
        fr("rider.head", "feather", (s * 0.1 + 0.15, 2.95, 0.0), (0.45 + s * 0.12, 3.3, -0.1), (0.07, 0.03), (0.01, 0.01), sides=4)


def rider_legs():
    for s in (-1, 1):
        fr("spine.2", "wrap", (s * 0.26, 1.5, 0.0), (s * 0.62, 1.3, 0.38), (0.2, 0.22), (0.16, 0.16), sides=6)
        fr("spine.2", "skin", (s * 0.62, 1.32, 0.38), (s * 0.7, 0.9, 0.3), (0.17, 0.17), (0.13, 0.13), sides=6)
        fr("spine.2", "skin_dk", (s * 0.7, 0.95, 0.3), (s * 0.72, 0.65, 0.42), (0.13, 0.13), (0.15, 0.1), sides=6)


def arms():
    fr("rider.arm.R", "skin", (-0.5, 2.15, 0.0), (-0.6, 2.2, 0.35), (0.27, 0.25), (0.21, 0.21), sides=6)
    fr("rider.forearm.R", "skin", (-0.6, 2.2, 0.35), (-0.45, 2.75, 0.6), (0.22, 0.22), (0.2, 0.2), sides=6)
    fr("rider.forearm.R", "skin_dk", (-0.45, 2.7, 0.58), (-0.45, 2.95, 0.7), (0.19, 0.19), (0.16, 0.16), sides=6)
    fr("rider.arm.L", "skin", (0.5, 2.15, 0.0), (0.55, 1.85, 0.45), (0.27, 0.25), (0.21, 0.21), sides=6)
    fr("rider.forearm.L", "skin", (0.55, 1.85, 0.45), (-0.3, 2.35, 1.0), (0.17, 0.17), (0.15, 0.15), sides=6)
    fr("rider.forearm.L", "skin_dk", (-0.25, 2.3, 0.98), (-0.42, 2.4, 1.08), (0.19, 0.19), (0.16, 0.16), sides=6)


def rifle():
    x = -0.45
    fr("rider.forearm.R", "wood", (x, 2.95, -0.75), (x, 3.0, 0.3), (0.18, 0.21), (0.15, 0.16), sides=6)
    fr("rider.forearm.R", "metal", (x, 3.0, 0.2), (x, 3.05, 1.2), (0.19, 0.19), (0.15, 0.15), sides=6)
    fr("rider.forearm.R", "wood", (x, 3.02, 1.1), (x, 3.06, 1.8), (0.14, 0.14), (0.12, 0.12), sides=6)
    fr("rider.forearm.R", "metal", (x, 3.06, 1.75), (x, 3.08, 2.5), (0.09, 0.09), (0.08, 0.08), sides=6)
    fr("rider.forearm.R", "steel", (x, 3.1, 2.45), (x, 3.1, 3.6), (0.04, 0.13), (0.012, 0.012), sides=4)


def make():
    use(MOUNT)
    torso()
    neck_head()
    legs()
    tail()
    wing(1, 1)
    wing(-1, 2)
    use(RIDER)
    rider_body()
    rider_legs()
    arms()
    rifle()


def joints():
    m = {"spine.1": ((0, 0.95, -0.7), (0, 1.0, 0.0)), "spine.2": ((0, 1.0, 0.0), (0, 1.0, 0.6)),
         "neck.1": ((0, 1.05, 0.6), (0, 1.4, 0.85)), "neck.2": ((0, 1.4, 0.85), (0, 1.7, 0.98)),
         "head": ((0, 1.7, 0.98), (0, 1.7, 1.6))}
    r = {"rider.spine": ((0, 1.25, 0.0), (0, 2.3, 0.0)), "rider.head": ((0, 2.3, 0.0), (0, 2.95, 0.0)),
         "rider.arm.R": ((-0.5, 2.15, 0.0), (-0.5, 1.65, 0.0)), "rider.forearm.R": ((-0.6, 2.2, 0.35), (-0.6, 1.75, 0.35)),
         "rider.arm.L": ((0.5, 2.15, 0.0), (0.5, 1.65, 0.0)), "rider.forearm.L": ((0.55, 1.85, 0.45), (0.55, 1.4, 0.45))}
    for i in range(3):
        m[f"tail.{i + 1}"] = (TAIL[i], TAIL[i + 1])
    for s, n in ((1, 1), (-1, 2)):
        m[f"wing{n}.upper"] = (flip(SH, s), flip((SH[0] + 0.9, SH[1] + 0.35, SH[2] - 0.14), s))
        m[f"wing{n}.lower"] = (flip(WR, s), flip((WR[0] + 0.9, WR[1] - 0.22, WR[2] - 0.35), s))
    out = {k: tuple(T(p, MOUNT) for p in v) for k, v in m.items()}
    out.update({k: tuple(T(p, RIDER) for p in v) for k, v in r.items()})
    return out


H.build("o009", "mounted_flyer", PALETTE, make, joints())
