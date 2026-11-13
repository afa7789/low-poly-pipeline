"""Salamander (n02Z), quadruped: measured on artifacts/model-sheets/refs/n02Z/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n02Z.py -- <out.glb>

Scale read off the profile: 400 px per metre, nose at z=+1.0, ground at y=0, back 0.72 m, lamp top 1.28 m.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "brown": 0x70573E, "brown_dk": 0x5C4630, "tan": 0xC2A878, "dark": 0x383A3C, "orange": 0xF28A1E,
    "dial": 0xD4B886,
}

# juntas (x, y, z) do ombro/quadril, cotovelo/joelho e tornozelo: pernas abertas de lagarto
FRONT = ((0.3, 0.4, 0.35), (0.4, 0.26, 0.32), (0.42, 0.12, 0.34))
HIND = ((0.3, 0.42, -0.35), (0.4, 0.26, -0.35), (0.42, 0.12, -0.33))
LEGS = ((1, FRONT, 1), (-1, FRONT, 2), (1, HIND, 3), (-1, HIND, 4))


def mir(p, s):
    return (s * p[0], p[1], p[2])


def trunk():
    H.frustum("spine.2", "brown", (0, 0.45, 0.45), (0, 0.47, -0.05), (0.24, 0.27), (0.27, 0.28))
    H.frustum("spine.1", "brown", (0, 0.47, -0.05), (0, 0.5, -0.5), (0.27, 0.28), (0.3, 0.3))
    H.frustum("spine.2", "tan", (0, 0.27, 0.42), (0, 0.27, -0.05), (0.2, 0.09), (0.24, 0.1), sides=6)
    H.frustum("spine.1", "tan", (0, 0.27, -0.05), (0, 0.28, -0.5), (0.24, 0.1), (0.24, 0.1), sides=6)
    for s in (-1, 1):       # anca grossa: a bola redonda que se ve atras e de cima
        H.frustum("spine.1", "brown", (s * 0.3, 0.5, -0.28), (s * 0.31, 0.5, -0.62), (0.2, 0.18), (0.16, 0.15))
        H.chain("spine.2", "brown_dk", [(s * 0.25, 0.52, 0.42), (s * 0.31, 0.4, 0.25), (s * 0.31, 0.46, 0.0), (s * 0.3, 0.4, -0.2)],
                [(0.035, 0.035)] * 4)       # tubo de gas do capacete ate a anca
    for z, top in ((0.3, 0.9), (0.0, 0.92), (-0.28, 0.84)):
        H.frustum("spine.2" if z > -0.1 else "spine.1", "dark", (0, 0.68, z), (0, top, z - 0.04), (0.04, 0.1), (0.025, 0.07), sides=4)
    H.frustum("spine.1", "dark", (0, 0.7, -0.46), (0, 0.82, -0.5), (0.04, 0.07), (0.025, 0.05), sides=4)


def tail():
    H.frustum("tail.1", "brown", (0, 0.55, -0.5), (0, 0.78, -0.76), (0.2, 0.2), (0.14, 0.14))
    H.frustum("tail.1", "tan", (0, 0.5, -0.6), (0, 0.76, -0.84), (0.1, 0.06), (0.07, 0.05), sides=4)
    H.frustum("tail.2", "brown", (0, 0.76, -0.74), (0, 1.0, -0.88), (0.14, 0.14), (0.1, 0.1))
    H.frustum("tail.2", "brown", (0, 1.0, -0.88), (0, 1.14, -0.78), (0.1, 0.1), (0.07, 0.07))
    H.box("tail.2", "dark", (0, 1.2, -0.62), (0.22, 0.18, 0.2))                    # caixa do bocal
    H.frustum("tail.2", "dial", (0, 1.22, -0.51), (0, 1.22, -0.5), (0.06, 0.06), (0.06, 0.06), sides=8)
    H.frustum("tail.2", "orange", (0, 1.2, -0.52), (0, 1.2, -0.38), (0.04, 0.04), (0.07, 0.07))   # bico brilhante
    H.chain("tail.2", "brown_dk", [(0, 1.1, -0.74), (0, 1.14, -0.58), (0, 1.0, -0.5)], [(0.03, 0.03)] * 3)


def head():
    H.frustum("head", "dark", (0, 0.52, 0.46), (0, 0.5, 0.9), (0.3, 0.19), (0.24, 0.15))          # capacete
    H.frustum("head", "dark", (0, 0.5, 0.86), (0, 0.46, 1.0), (0.24, 0.15), (0.2, 0.1))
    H.frustum("head", "dark", (0, 0.66, 0.66), (0, 0.63, 1.02), (0.17, 0.04), (0.1, 0.03), sides=4)  # viseira
    H.frustum("head", "orange", (0, 0.39, 0.9), (0, 0.39, 1.0), (0.22, 0.03), (0.19, 0.03), sides=4)  # fenda da boca
    H.frustum("head", "tan", (0, 0.35, 0.48), (0, 0.36, 0.9), (0.21, 0.06), (0.16, 0.05), sides=6)
    H.frustum("head", "brown", (0, 0.48, 0.3), (0, 0.5, 0.52), (0.2, 0.22), (0.3, 0.19))           # pescoco


def paw(bone, s, p):
    x, _, z = p
    H.frustum(bone, "dark", (s * x, 0.1, z), (s * x, 0.03, z + 0.08), (0.12, 0.1), (0.15, 0.08), sides=6)
    for k in (-1, 0, 1):
        end = (s * (x + k * 0.1), 0.02, z + 0.3 - abs(k) * 0.04)
        H.frustum(bone, "dark", (s * (x + k * 0.04), 0.04, z + 0.1), end, (0.04, 0.03), (0.012, 0.01), sides=4)


def leg(s, geo, n):
    hip, knee, ank = (mir(p, s) for p in geo)
    up, lo = f"leg{n}.upper", f"leg{n}.lower"
    H.frustum(up, "brown", hip, knee, (0.16, 0.17), (0.13, 0.13))
    H.frustum(lo, "dark", knee, (ank[0], 0.1, ank[2]), (0.14, 0.14), (0.1, 0.1))
    paw(lo, s, geo[2])


def make():
    trunk()
    tail()
    head()
    for args in LEGS:
        leg(*args)


def joints():
    out = {
        "spine.1": ((0, 0.5, -0.5), (0, 0.5, -0.05)), "spine.2": ((0, 0.5, -0.05), (0, 0.5, 0.45)),
        "head": ((0, 0.5, 0.45), (0, 0.5, 1.0)),
        "tail.1": ((0, 0.55, -0.5), (0, 0.78, -0.76)), "tail.2": ((0, 0.78, -0.76), (0, 1.12, -0.84)),
    }
    for s, geo, n in LEGS:
        hip, knee, ank = (mir(p, s) for p in geo)
        out[f"leg{n}.upper"] = (hip, knee)
        out[f"leg{n}.lower"] = (knee, ank)
    return out


H.build("n02Z", "quadruped", PALETTE, make, joints())
