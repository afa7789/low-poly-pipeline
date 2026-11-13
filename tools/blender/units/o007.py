"""Kodo (o007), quadruped: measured on artifacts/model-sheets/refs/o007/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/o007.py -- <out.glb>

Scale read off the profile: 400 px per metre, horn tip at z=+1.0, ground at y=0, hump 1.34 m, tail tip z=-2.25.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "skin": 0x9A8A62, "skin_dk": 0x7C6E4E, "belly": 0x3E3226, "horn": 0xEBDFBC, "red": 0xD01818,
    "gum": 0x7A1822, "wood": 0x7A4E2C, "rope": 0x6C7388,
}

# juntas (x, y, z) do ombro/quadril, cotovelo/joelho e tornozelo
FRONT = ((0.42, 0.85, 0.1), (0.4, 0.46, 0.2), (0.38, 0.14, 0.28))
HIND = ((0.36, 0.78, -0.6), (0.36, 0.4, -0.7), (0.34, 0.14, -0.68))
LEGS = ((1, FRONT, 1), (-1, FRONT, 2), (1, HIND, 3), (-1, HIND, 4))


def mir(p, s):
    return (s * p[0], p[1], p[2])


def trunk():
    H.frustum("spine.2", "skin", (0, 0.85, 0.3), (0, 0.92, -0.15), (0.46, 0.38), (0.62, 0.44))     # ombros, corcova
    H.frustum("spine.1", "skin", (0, 0.9, -0.15), (0, 0.72, -0.65), (0.62, 0.44), (0.48, 0.36))
    H.frustum("spine.1", "skin", (0, 0.72, -0.6), (0, 0.62, -0.95), (0.46, 0.34), (0.3, 0.32))
    H.frustum("spine.2", "belly", (0, 0.52, 0.2), (0, 0.5, -0.15), (0.34, 0.08), (0.46, 0.08), sides=6)
    H.frustum("spine.1", "belly", (0, 0.5, -0.15), (0, 0.46, -0.6), (0.46, 0.08), (0.3, 0.08), sides=6)


def cargo():
    H.box("spine.2", "wood", (0, 1.3, -0.14), (0.32, 0.27, 0.32))
    for s in (-1, 1):       # corda do caixote em volta dos ombros
        H.chain("spine.2", "rope", [(s * 0.14, 1.3, -0.1), (s * 0.5, 1.2, -0.05), (s * 0.63, 0.95, 0.12), (s * 0.58, 0.62, 0.2)],
                [(0.03, 0.03)] * 4)


def tail():
    H.frustum("tail.1", "skin", (0, 0.62, -0.85), (0, 0.42, -1.5), (0.3, 0.32), (0.14, 0.16))
    H.frustum("tail.2", "skin", (0, 0.42, -1.5), (0, 0.17, -2.25), (0.14, 0.16), (0.01, 0.01))
    H.frustum("tail.1", "belly", (0, 0.42, -0.9), (0, 0.34, -1.5), (0.14, 0.05), (0.07, 0.04), sides=4)


def horns():
    H.chain("head", "horn", [(0, 0.62, 0.74), (0, 0.82, 0.86), (0, 1.02, 0.95), (0, 1.2, 0.98)],
            [(0.1, 0.1), (0.085, 0.085), (0.055, 0.055), (0.006, 0.006)])
    H.chain("head", "horn", [(0, 0.78, 0.58), (0, 0.95, 0.67)], [(0.06, 0.06), (0.006, 0.006)])


def head():
    H.frustum("head", "skin", (0, 0.76, 0.28), (0, 0.66, 0.62), (0.34, 0.32), (0.27, 0.23))
    H.frustum("head", "skin", (0, 0.58, 0.6), (0, 0.5, 0.82), (0.26, 0.19), (0.2, 0.13))
    H.frustum("head", "gum", (0, 0.4, 0.5), (0, 0.4, 0.8), (0.19, 0.06), (0.17, 0.05), sides=6)       # maxilar inferior
    for s in (-1, 1):
        H.frustum("head", "red", (s * 0.16, 0.7, 0.62), (s * 0.22, 0.7, 0.58), (0.05, 0.04), (0.05, 0.04), sides=6)
        H.frustum("head", "horn", (s * 0.12, 0.42, 0.74), (s * 0.13, 0.55, 0.78), (0.035, 0.035), (0.006, 0.006), sides=4)
        H.frustum("head", "horn", (s * 0.06, 0.42, 0.8), (s * 0.07, 0.54, 0.83), (0.03, 0.03), (0.006, 0.006), sides=4)


def paw(bone, s, p):
    x, _, z = p
    H.frustum(bone, "skin_dk", (s * x, 0.16, z), (s * x, 0.03, z + 0.03), (0.2, 0.2), (0.25, 0.28))
    for k in (-1, 0, 1):    # tres garras de marfim
        H.frustum(bone, "horn", (s * (x + k * 0.12), 0.07, z + 0.2), (s * (x + k * 0.13), 0.03, z + 0.38), (0.055, 0.05), (0.012, 0.012), sides=4)


def leg(s, geo, n):
    hip, knee, ank = (mir(p, s) for p in geo)
    up, lo = f"leg{n}.upper", f"leg{n}.lower"
    thick = 0.3 if geo is HIND else 0.28
    H.frustum(up, "skin", hip, knee, (thick, thick), (0.22, 0.22))
    H.frustum(lo, "skin_dk" if geo is FRONT else "skin", knee, (ank[0], 0.16, ank[2]), (0.22, 0.22), (0.2, 0.2))
    paw(lo, s, geo[2])


def make():
    trunk()
    cargo()
    tail()
    head()
    horns()
    for args in LEGS:
        leg(*args)


def joints():
    out = {
        "spine.1": ((0, 0.8, -0.85), (0, 0.9, -0.15)), "spine.2": ((0, 0.9, -0.15), (0, 0.9, 0.3)),
        "head": ((0, 0.9, 0.3), (0, 0.6, 0.9)),
        "tail.1": ((0, 0.62, -0.85), (0, 0.45, -1.5)), "tail.2": ((0, 0.45, -1.5), (0, 0.2, -2.25)),
    }
    for s, geo, n in LEGS:
        hip, knee, ank = (mir(p, s) for p in geo)
        out[f"leg{n}.upper"] = (hip, knee)
        out[f"leg{n}.lower"] = (knee, ank)
    return out


H.build("o007", "quadruped", PALETTE, make, joints())
