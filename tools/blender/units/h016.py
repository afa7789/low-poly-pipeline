"""Gryphon Rider (h016, familia mounted_flyer): grifo de cabeca de aguia e corpo de leao, piloto de aviador com garfo de tempestade.

    blender -b --factory-startup -P tools/blender/units/h016.py -- <out.glb>

Montaria na escala da prancha (x1.5); piloto ~36 % da altura (assento -> capacete); garfo grosso e alto, longe das asas
(asas abertas para os lados e varridas para tras, cada uma uma superficie continua presa ao ombro).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "tan": 0xC99A5B, "tan_dk": 0x9A6E3C, "cream": 0xF2E6D0, "lav": 0xA79BB5, "beak": 0xE0A920, "eye": 0xFFD020,
    "red": 0x84321E, "dark": 0x2E2C38, "jacket": 0x30303C, "pants": 0x6A7690, "boot": 0x1E1B1E,
    "helmet": 0x6B4430, "gold": 0xD9A82E, "steel": 0x8795AD, "copper": 0xB8703F, "skin": 0xD9A890, "strap": 0x7A4B2D,
}


# Montaria na escala da prancha (x S); piloto menor (x R) sentado no dorso, arma exagerada (coordenadas locais do piloto).
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
    fr("spine.1", "tan", (0, 0.95, -0.9), (0, 0.95, -0.1), (0.4, 0.4), (0.52, 0.5))
    fr("spine.2", "tan", (0, 0.95, -0.15), (0, 1.0, 0.62), (0.52, 0.5), (0.5, 0.54))
    fr("spine.2", "cream", (0, 0.88, 0.4), (0, 1.1, 0.88), (0.34, 0.38), (0.3, 0.3))
    fr("spine.1", "tan_dk", (0, 1.3, -0.7), (0, 1.36, -0.1), (0.2, 0.06), (0.22, 0.06), sides=4)


def neck_head():
    fr("neck.1", "lav", (0, 1.05, 0.6), (0, 1.4, 0.85), (0.38, 0.36), (0.32, 0.32))
    fr("neck.1", "cream", (0, 0.85, 0.82), (0, 1.4, 1.0), (0.3, 0.2), (0.22, 0.14))
    fr("neck.2", "lav", (0, 1.35, 0.8), (0, 1.74, 0.98), (0.32, 0.32), (0.28, 0.28))
    fr("head", "lav", (0, 1.72, 0.9), (0, 1.74, 1.3), (0.29, 0.29), (0.23, 0.25))
    fr("head", "tan_dk", (0, 1.88, 0.95), (0, 1.9, 1.35), (0.2, 0.06), (0.16, 0.06), sides=4)
    chain("head", "beak", [(0, 1.74, 1.22), (0, 1.7, 1.5), (0, 1.54, 1.68), (0, 1.38, 1.65)],
            [(0.15, 0.16), (0.12, 0.14), (0.07, 0.08), (0.02, 0.02)])
    for s in (-1, 1):
        fr("head", "eye", (s * 0.2, 1.8, 1.2), (s * 0.27, 1.8, 1.3), (0.06, 0.05), (0.04, 0.04), sides=6)
        fr("head", "lav", (s * 0.16, 1.95, 0.95), (s * 0.24, 2.18, 0.85), (0.06, 0.05), (0.01, 0.01), sides=4)


def legs():
    for s, f, h in ((1, "leg1", "leg3"), (-1, "leg2", "leg4")):
        for tag, z, thigh in ((f, 0.47, 0.22), (h, -0.47, 0.27)):
            x = s * 0.34
            fr(f"{tag}.upper", "tan", (x, 1.08, z), (x + s * 0.02, 0.55, z + 0.03), (thigh, thigh + 0.02), (0.13, 0.14))
            fr(f"{tag}.lower", "tan_dk", (x + s * 0.02, 0.58, z + 0.03), (x + s * 0.02, 0.16, z + 0.03), (0.14, 0.14), (0.09, 0.1))
            fr(f"{tag}.lower", "tan_dk", (x + s * 0.02, 0.18, z + 0.03), (x + s * 0.02, 0.04, z + 0.2), (0.1, 0.1), (0.15, 0.07))
            fr(f"{tag}.lower", "beak", (x + s * 0.02, 0.06, z + 0.2), (x + s * 0.02, 0.0, z + 0.4), (0.12, 0.03), (0.07, 0.01), sides=6)


TAIL = [(0, 0.98, -0.75), (0, 0.95, -1.15), (0, 0.92, -1.55), (0, 0.9, -1.95)]


def tail():
    chain(("tail.1", "tail.2", "tail.3"), "tan", TAIL, [(0.2, 0.2), (0.14, 0.14), (0.1, 0.1), (0.07, 0.07)])
    fr("tail.3", "beak", (0, 0.9, -1.9), (0, 0.9, -2.35), (0.12, 0.05), (0.01, 0.01), sides=4)


# asa (lado +x): borda de ataque SH -> WR -> TIP, borda de fuga ROOT -> TM -> TT
SH, WR, TIP = (0.5, 1.5, 0.1), (1.3, 2.6, -0.1), (2.5, 3.3, -0.9)
BACK = [(0.45, 1.2, -0.75), (1.4, 1.55, -1.3), (2.2, 2.0, -1.9)]
BANDS = ((0.0, 0.55, "red"), (0.55, 0.68, "cream"), (0.68, 0.8, "dark"), (0.8, 0.9, "cream"), (0.9, 1.0, "dark"))


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def flip(p, s):
    return (p[0] * s, p[1], p[2])


def weigh(p):
    low = min(max((abs(p[0]) / S - 0.55) / 0.75, 0.0), 1.0)
    return {"low": low, "up": 1.0 - low}


def wing(s, n):
    up, low = f"wing{n}.upper", f"wing{n}.lower"
    lead = [flip(p, s) for p in (SH, WR, TIP)]
    back = [flip(p, s) for p in BACK]
    fr(up, "dark", lead[0], lead[1], (0.17, 0.15), (0.12, 0.11), sides=6)
    fr(low, "dark", lead[1], lead[2], (0.11, 0.1), (0.03, 0.03), sides=6)
    for i in range(2):
        for s0, s1, tone in BANDS:
            quad = [lerp(lead[i], back[i], s0), lerp(lead[i + 1], back[i + 1], s0),
                    lerp(lead[i + 1], back[i + 1], s1), lerp(lead[i], back[i], s1)]
            obj = panel(up, tone, quad, 0.05)
            H.soft(obj, lambda p, up=up, low=low: {low: weigh(p)["low"], up: weigh(p)["up"]})
    for k in range(4):     # dedos de penas na ponta
        a = lerp(lead[1], lead[2], 0.35 + 0.2 * k)
        fr(low, "dark", a, lerp(a, lerp(back[1], back[2], 0.35 + 0.2 * k), 1.0), (0.04, 0.03), (0.015, 0.015), sides=4)


def rider_body():
    fr("rider.spine", "pants", (0, 1.25, 0.0), (0, 1.7, 0.0), (0.4, 0.34), (0.38, 0.3))
    fr("rider.spine", "jacket", (0, 1.65, 0.0), (0, 2.52, 0.0), (0.38, 0.3), (0.52, 0.34))
    fr("rider.spine", "strap", (0.28, 2.4, -0.3), (-0.28, 1.8, -0.32), (0.06, 0.04), (0.06, 0.04), sides=4)
    fr("rider.spine", "strap", (-0.28, 2.4, -0.3), (0.28, 1.8, -0.32), (0.06, 0.04), (0.06, 0.04), sides=4)
    fr("rider.spine", "cream", (0, 2.46, 0.0), (0, 2.66, 0.02), (0.4, 0.34), (0.3, 0.28))
    fr("rider.head", "skin", (0, 2.62, 0.02), (0, 2.95, 0.04), (0.28, 0.28), (0.3, 0.3))
    fr("rider.head", "cream", (0, 2.66, 0.2), (0, 2.9, 0.3), (0.2, 0.08), (0.12, 0.06), sides=6)
    fr("rider.head", "helmet", (0, 2.86, 0.02), (0, 3.22, 0.02), (0.34, 0.33), (0.22, 0.22))
    fr("rider.head", "gold", (0, 2.9, 0.04), (0, 3.0, 0.04), (0.36, 0.35), (0.36, 0.35))
    for s in (-1, 1):
        fr("rider.head", "steel", (s * 0.12, 2.95, 0.3), (s * 0.12, 2.95, 0.4), (0.1, 0.1), (0.1, 0.1), sides=6)


def rider_legs():
    for s in (-1, 1):
        fr("spine.2", "pants", (s * 0.26, 1.5, 0.0), (s * 0.62, 1.3, 0.38), (0.2, 0.22), (0.16, 0.16), sides=6)
        fr("spine.2", "pants", (s * 0.62, 1.32, 0.38), (s * 0.7, 0.9, 0.3), (0.17, 0.17), (0.13, 0.13), sides=6)
        fr("spine.2", "boot", (s * 0.7, 0.95, 0.3), (s * 0.72, 0.65, 0.4), (0.12, 0.13), (0.17, 0.12), sides=6)


def arms():
    # direito (x-): erguido com o garfo; esquerdo: na rédea, a frente
    fr("rider.arm.R", "jacket", (-0.55, 2.4, 0.0), (-0.95, 2.85, 0.1), (0.27, 0.26), (0.21, 0.21), sides=6)
    fr("rider.forearm.R", "jacket", (-0.95, 2.85, 0.1), (-0.85, 3.2, 0.2), (0.22, 0.22), (0.2, 0.2), sides=6)
    fr("rider.forearm.R", "boot", (-0.85, 3.12, 0.2), (-0.85, 3.42, 0.2), (0.2, 0.2), (0.16, 0.16), sides=6)
    fr("rider.arm.L", "jacket", (0.55, 2.4, 0.0), (0.72, 1.95, 0.22), (0.27, 0.26), (0.21, 0.21), sides=6)
    fr("rider.forearm.L", "jacket", (0.72, 1.95, 0.22), (0.52, 1.62, 0.5), (0.22, 0.22), (0.2, 0.2), sides=6)
    fr("rider.forearm.L", "boot", (0.52, 1.64, 0.5), (0.45, 1.5, 0.62), (0.18, 0.18), (0.15, 0.15), sides=6)


def fork():
    x, z = -0.85, 0.2
    fr("rider.forearm.R", "steel", (x, 2.95, z), (x, 3.95, z), (0.1, 0.1), (0.11, 0.11), sides=6)
    fr("rider.forearm.R", "gold", (x, 3.5, z), (x, 3.74, z), (0.2, 0.2), (0.2, 0.2), sides=6)
    fr("rider.forearm.R", "gold", (x, 3.9, z), (x, 4.02, z), (0.4, 0.14), (0.4, 0.14), sides=4)
    for s in (-1, 1):
        fr("rider.forearm.R", "steel", (x + s * 0.14, 4.0, z), (x + s * 0.3, 4.4, z), (0.11, 0.11), (0.08, 0.08), sides=6)
        fr("rider.forearm.R", "copper", (x + s * 0.3, 4.36, z), (x + s * 0.32, 4.7, z), (0.09, 0.09), (0.02, 0.02), sides=6)


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
    fork()


def joints():
    m = {"spine.1": ((0, 0.95, -0.7), (0, 1.0, 0.0)), "spine.2": ((0, 1.0, 0.0), (0, 1.0, 0.6)),
         "neck.1": ((0, 1.05, 0.6), (0, 1.4, 0.85)), "neck.2": ((0, 1.4, 0.85), (0, 1.74, 0.98)),
         "head": ((0, 1.74, 0.98), (0, 1.74, 1.6))}
    r = {"rider.spine": ((0, 1.25, 0.0), (0, 2.5, 0.0)), "rider.head": ((0, 2.5, 0.0), (0, 3.2, 0.0)),
         "rider.arm.R": ((-0.55, 2.4, 0.0), (-0.55, 1.9, 0.0)), "rider.forearm.R": ((-0.95, 2.85, 0.1), (-0.95, 2.35, 0.1)),
         "rider.arm.L": ((0.55, 2.4, 0.0), (0.55, 1.9, 0.0)), "rider.forearm.L": ((0.72, 1.95, 0.22), (0.72, 1.45, 0.22))}
    for i in range(3):
        m[f"tail.{i + 1}"] = (TAIL[i], TAIL[i + 1])
    for s, n in ((1, 1), (-1, 2)):
        m[f"wing{n}.upper"] = (flip(SH, s), flip((SH[0] + 0.9, SH[1] + 0.35, SH[2] - 0.14), s))
        m[f"wing{n}.lower"] = (flip(WR, s), flip((WR[0] + 0.9, WR[1] - 0.22, WR[2] - 0.35), s))
    out = {k: tuple(T(p, MOUNT) for p in v) for k, v in m.items()}
    out.update({k: tuple(T(p, RIDER) for p in v) for k, v in r.items()})
    return out


H.build("h016", "mounted_flyer", PALETTE, make, joints())
