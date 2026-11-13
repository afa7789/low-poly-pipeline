"""Quill Demon (z000), quadruped: measured on artifacts/model-sheets/refs/z000/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/z000.py -- <out.glb>

Scale read off the profile: 0.0033 m per pixel, front = left in the sheet, nose z=+1.18, ground y=0, tail tip z=-1.4.
The two giant curved horns grow from the shoulders (pink stem, cream curve) and are the 'quills' of the volley.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "crimson": 0xA8142E, "pink": 0xB0197A, "pink_lt": 0xC4208F, "dark": 0x3E1A38, "cream": 0xF2D2B0,
    "eye": 0xFF8A20, "claw": 0xEADFC4,
}

# juntas (x, y, z) do ombro/quadril, joelho e tornozelo
FRONT = ((0.3, 0.7, 0.38), (0.33, 0.36, 0.3), (0.34, 0.1, 0.45))
HIND = ((0.3, 0.66, -0.32), (0.34, 0.34, -0.5), (0.3, 0.1, -0.4))
LEGS = ((1, FRONT, 1), (-1, FRONT, 2), (1, HIND, 3), (-1, HIND, 4))


def mir(p, s):
    return (s * p[0], p[1], p[2])


def trunk():
    H.frustum("spine.2", "crimson", (0, 0.68, 0.55), (0, 0.72, 0.0), (0.3, 0.26), (0.36, 0.3))        # peito
    H.frustum("spine.1", "crimson", (0, 0.72, 0.0), (0, 0.68, -0.45), (0.36, 0.3), (0.32, 0.26))        # barril
    H.frustum("spine.1", "pink", (0, 0.68, -0.4), (0, 0.6, -0.62), (0.26, 0.22), (0.1, 0.1))            # garupa
    H.frustum("spine.2", "dark", (0, 0.46, 0.4), (0, 0.46, 0.0), (0.3, 0.06), (0.34, 0.06), sides=4)    # barriga
    H.frustum("spine.1", "dark", (0, 0.46, 0.0), (0, 0.46, -0.45), (0.3, 0.06), (0.26, 0.06), sides=4)
    for bone, z in (("spine.2", 0.4), ("spine.2", 0.22), ("spine.2", 0.04), ("spine.1", -0.12), ("spine.1", -0.28)):
        H.frustum(bone, "crimson", (0, 0.82, z), (0, 0.96, z - 0.11), (0.22, 0.1), (0.2, 0.09), sides=4)   # placas das costas


def quills():
    """Leque de espinhos de osso nas costas: tres de cada lado e dois no meio, inclinados para tras."""
    for s in (-1, 1):
        for z, tx, ty in ((0.0, 0.24, 1.36), (-0.12, 0.3, 1.3), (-0.24, 0.34, 1.2)):
            H.frustum("spine.1", "cream", (s * 0.14, 0.88, z), (s * tx, ty, z - 0.62), (0.05, 0.05), (0.006, 0.006), sides=4)
    for z, ty in ((0.04, 1.4), (-0.1, 1.32)):
        H.frustum("spine.1", "cream", (0, 0.92, z), (0, ty, z - 0.64), (0.05, 0.05), (0.006, 0.006), sides=4)


def horns(s):
    """Haste rosa que sobe do ombro e curva de osso que desce para a frente: o braco do disparo de espinhos."""
    H.chain("spine.2", "pink_lt", [(s * 0.2, 0.9, 0.32), (s * 0.4, 1.35, 0.32), (s * 0.56, 1.76, 0.3)],
            [(0.11, 0.11), (0.085, 0.085), (0.065, 0.065)], sides=6)
    H.chain("spine.2", "cream", [(s * 0.56, 1.76, 0.3), (s * 0.72, 1.7, 0.6), (s * 0.88, 1.42, 0.92), (s * 0.94, 1.0, 1.08), (s * 0.84, 0.55, 1.1)],
            [(0.08, 0.08), (0.075, 0.075), (0.06, 0.06), (0.04, 0.04), (0.006, 0.006)], sides=6)


def head():
    H.frustum("head", "crimson", (0, 0.8, 0.5), (0, 0.72, 0.84), (0.27, 0.24), (0.2, 0.17))             # cranio
    H.frustum("head", "pink", (0, 0.66, 0.8), (0, 0.6, 1.14), (0.15, 0.12), (0.11, 0.09))                # focinho
    H.frustum("head", "dark", (0, 0.58, 1.1), (0, 0.58, 1.18), (0.13, 0.09), (0.1, 0.08), sides=6)
    H.frustum("head", "dark", (0, 0.52, 0.7), (0, 0.5, 1.06), (0.2, 0.05), (0.14, 0.05), sides=4)       # queixo
    H.frustum("head", "crimson", (0, 0.92, 0.55), (0, 0.98, 0.76), (0.14, 0.08), (0.08, 0.06), sides=4)
    for s in (-1, 1):
        H.frustum("head", "claw", (s * 0.1, 0.6, 1.0), (s * 0.1, 0.4, 1.08), (0.045, 0.045), (0.006, 0.006), sides=4)   # presas
        H.frustum("head", "eye", (s * 0.15, 0.84, 0.9), (s * 0.17, 0.86, 0.94), (0.06, 0.025), (0.04, 0.02), sides=4)
        H.frustum("head", "crimson", (s * 0.15, 0.94, 0.6), (s * 0.22, 1.36, 0.5), (0.08, 0.08), (0.006, 0.006), sides=4)  # chifres curtos


def tail():
    H.frustum("tail.1", "pink", (0, 0.6, -0.5), (0, 0.58, -0.95), (0.1, 0.09), (0.06, 0.06), sides=6)
    H.frustum("tail.2", "pink", (0, 0.58, -0.95), (0, 0.56, -1.5), (0.06, 0.06), (0.01, 0.01), sides=6)


def paw(bone, s, p):
    x, _, z = p
    H.frustum(bone, "dark", (x * s, 0.14, z - 0.02), (x * s, 0.03, z + 0.04), (0.12, 0.12), (0.17, 0.18))
    for k in (-1, 0, 1):
        H.frustum(bone, "claw", (s * (x + 0.05 * k), 0.04, z + 0.12), (s * (x + 0.07 * k), 0.02, z + 0.26), (0.03, 0.03), (0.006, 0.006), sides=4)


def leg(s, geo, n):
    hip, knee, ank = (mir(p, s) for p in geo)
    up, lo = f"leg{n}.upper", f"leg{n}.lower"
    front = geo is FRONT
    H.frustum(up, "pink" if front else "crimson", hip, knee, (0.17, 0.2), (0.11, 0.12))
    H.frustum(up, "crimson", (s * (geo[0][0] + 0.02), 0.5, geo[0][2]), (s * (geo[0][0] + 0.02), 0.84, geo[0][2]), (0.14, 0.2), (0.12, 0.18), sides=6)
    H.frustum(lo, "pink_lt" if front else "dark", knee, (ank[0], 0.14, ank[2]), (0.1, 0.1), (0.08, 0.08))
    paw(lo, s, geo[2])


def make():
    trunk()
    quills()
    head()
    tail()
    for s in (-1, 1):
        horns(s)
    for args in LEGS:
        leg(*args)


def joints():
    out = {
        "spine.1": ((0, 0.65, -0.55), (0, 0.7, 0.0)), "spine.2": ((0, 0.7, 0.0), (0, 0.8, 0.55)),
        "head": ((0, 0.8, 0.55), (0, 0.7, 1.15)),
        "tail.1": ((0, 0.6, -0.5), (0, 0.58, -0.95)), "tail.2": ((0, 0.58, -0.95), (0, 0.56, -1.5)),
    }
    for s, geo, n in LEGS:
        hip, knee, ank = (mir(p, s) for p in geo)
        out[f"leg{n}.upper"] = (hip, knee)
        out[f"leg{n}.lower"] = (knee, ank)
    return out


H.build("z000", "quadruped", PALETTE, make, joints())
