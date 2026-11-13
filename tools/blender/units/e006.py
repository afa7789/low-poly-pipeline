"""Dryad (e006): medido em artifacts/model-sheets/refs/e006/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/e006.py -- <out.glb>

Corpo de cervo (centauro) na familia centaur: cada uma das quatro patas nos seus ossos legN.upper / legN.lower
(1 = dianteira esquerda, 2 = dianteira direita, 3 = traseira esquerda, 4 = traseira direita); garupa em spine.1,
peito em spine.2; tronco humano em spine.3, bracos e lanca de folha (mao direita, osso forearm.R) seguem a prancha.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "skin": 0xB48CD8, "leaf": 0x5E8E3A, "leaf_dk": 0x4A7430, "fur": 0xB6A3A3, "belly": 0xE0D4D0, "spot": 0xEADFC0,
    "hoof": 0x3A2A20, "glove": 0x1A1A1E, "shaft": 0x6A4630, "blade": 0xC49A62, "gold": 0xC9A23C, "eye": 0xD8F03C,
    "tail": 0xE8DCDC,
}

HIP_Y, KNEE_Y, ANKLE_Y = 1.0, 0.55, 0.2
FRONT_Z, HIND_Z = -0.1, -1.1
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.3, 2.0, 0.4, 1.58, 1.14
SPEAR_X, SPEAR_Z = -0.52, 0.27


def head():
    H.frustum("head", "skin", (0, 2.2, 0.03), (0, 2.52, 0.03), (0.12, 0.13), (0.13, 0.14), sides=6)
    H.frustum("head", "leaf", (0, 2.2, -0.1), (0, 2.62, -0.1), (0.25, 0.2), (0.23, 0.21), sides=8)         # cabelo
    H.frustum("head", "leaf", (0, 2.62, -0.1), (0, 2.7, -0.1), (0.23, 0.21), (0.12, 0.1), sides=8)
    H.chain("head", "leaf", [(0, 2.45, -0.2), (0, 2.1, -0.3), (0, 1.9, -0.35), (0, 1.68, -0.32)],
            [(0.2, 0.1), (0.24, 0.1), (0.2, 0.09), (0.06, 0.04)], sides=6)
    H.frustum("head", "leaf", (0, 2.5, 0.12), (0, 2.58, 0.14), (0.14, 0.05), (0.1, 0.04), sides=4)           # franja
    H.frustum("head", "gold", (0, 2.52, 0.165), (0, 2.58, 0.165), (0.03, 0.02), (0.03, 0.02), sides=6)       # lua
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.065, 2.38, 0.165), (0.06, 0.03, 0.03))
        H.chain("head", "skin", [(s * 0.12, 2.42, 0.0), (s * 0.28, 2.5, -0.01), (s * 0.5, 2.58, -0.03)],
                [(0.07, 0.03), (0.05, 0.02), (0.008, 0.008)], sides=4)
        H.frustum("head", "gold", (s * 0.14, 2.34, 0.02), (s * 0.14, 2.28, 0.02), (0.03, 0.03), (0.03, 0.03), sides=6)


def torso():
    H.frustum("spine.3", "skin", (0, 1.4, 0), (0, 1.75, 0), (0.22, 0.17), (0.2, 0.16), sides=8)
    H.frustum("spine.3", "skin", (0, 1.75, 0), (0, 2.02, 0), (0.2, 0.16), (0.27, 0.19), sides=8)
    H.frustum("spine.3", "skin", (0, 2.02, 0), (0, 2.14, 0), (0.27, 0.19), (0.17, 0.14), sides=8)
    H.frustum("spine.3", "skin", (0, 2.05, 0.0), (0, 2.24, 0.0), (0.08, 0.08), (0.075, 0.075), sides=6)       # pescoco
    H.frustum("spine.3", "leaf", (0, 1.8, 0.015), (0, 2.03, 0.015), (0.235, 0.2), (0.285, 0.215), sides=8)    # faixa de folhas
    H.frustum("spine.3", "leaf_dk", (-0.12, 2.1, 0.12), (0.12, 1.84, 0.17), (0.05, 0.03), (0.05, 0.03), sides=4)


def deer_body():
    H.frustum("spine.2", "fur", (0, 1.2, 0.08), (0, 1.2, -0.5), (0.24, 0.27), (0.3, 0.28), sides=8)
    H.frustum("spine.1", "fur", (0, 1.2, -0.5), (0, 1.2, -1.05), (0.3, 0.28), (0.32, 0.28), sides=8)
    H.frustum("spine.1", "fur", (0, 1.2, -1.05), (0, 1.2, -1.38), (0.32, 0.28), (0.2, 0.22), sides=8)
    H.frustum("spine.2", "belly", (0, 1.08, 0.0), (0, 1.08, -0.6), (0.2, 0.2), (0.22, 0.2), sides=6)
    H.frustum("spine.1", "belly", (0, 1.08, -0.6), (0, 1.08, -1.2), (0.22, 0.2), (0.22, 0.2), sides=6)
    for bone, x, z in (("spine.2", 0.12, -0.35), ("spine.1", -0.15, -0.6), ("spine.1", 0.1, -0.85), ("spine.1", -0.12, -1.1)):
        H.frustum(bone, "spot", (x, 1.46, z), (x, 1.49, z), (0.08, 0.06), (0.06, 0.05), sides=6)
    H.chain(("tail.1", "tail.2"), "tail", [(0, 1.3, -1.36), (0, 1.5, -1.5), (0, 1.76, -1.48)],
            [(0.07, 0.07), (0.08, 0.08), (0.02, 0.02)], sides=6)


def leg(n, x, z, hind):
    """Uma pata de cervo nos ossos legN; a traseira tem coxa grossa e jarrete."""
    up, lo = f"leg{n}.upper", f"leg{n}.lower"
    k = z + (0.1 if hind else 0.0)
    a = z - (0.1 if hind else 0.0)
    top = (0.19, 0.2) if hind else (0.13, 0.14)
    H.frustum(up, "fur", (x, KNEE_Y - 0.05, k), (x, HIP_Y + 0.12, z), (0.09, 0.09), top, sides=6)
    H.frustum(lo, "fur", (x, ANKLE_Y, a), (x, KNEE_Y + 0.04, k), (0.085, 0.085), (0.11, 0.11), sides=6)
    H.frustum(lo, "gold", (x, ANKLE_Y + 0.1, a), (x, ANKLE_Y + 0.04, a), (0.1, 0.1), (0.1, 0.1), sides=6)
    H.frustum(lo, "belly", (x, 0.1, a), (x, ANKLE_Y + 0.05, a), (0.085, 0.09), (0.075, 0.075), sides=6)
    H.frustum(lo, "hoof", (x, 0.0, a - 0.02), (x, 0.12, a), (0.11, 0.14), (0.085, 0.09), sides=6)


def legs():
    leg(1, 0.2, FRONT_Z, False)
    leg(2, -0.2, FRONT_Z, False)
    leg(3, 0.22, HIND_Z, True)
    leg(4, -0.22, HIND_Z, True)


def arms():
    for s, side in ((1, "L"), (-1, "R")):
        z = 0.12 if s < 0 else 0.0
        H.frustum(f"arm.{side}", "skin", (s * (SH_X - 0.02), SH_Y + 0.04, 0), (s * EL_X, EL_Y - 0.02, 0), (0.1, 0.1), (0.08, 0.08), sides=6)
        H.frustum(f"forearm.{side}", "skin", (s * EL_X, EL_Y + 0.02, 0), (s * (EL_X + 0.04), WR_Y + 0.05, z), (0.075, 0.075), (0.065, 0.065), sides=6)
        H.frustum(f"forearm.{side}", "leaf", (s * EL_X, EL_Y + 0.05, 0), (s * (EL_X + 0.04), 1.3, z * 0.5), (0.12, 0.12), (0.16, 0.15), sides=6)
        H.frustum(f"forearm.{side}", "leaf_dk", (s * (EL_X + 0.07), 1.4, z * 0.5), (s * (EL_X + 0.1), 1.56, 0), (0.04, 0.12), (0.01, 0.01), sides=4)
        H.frustum(f"forearm.{side}", "glove", (s * (EL_X + 0.04), 1.36, z), (s * (EL_X + 0.07), WR_Y - 0.12, z), (0.1, 0.1), (0.095, 0.11), sides=6)


def spear():
    x, z = SPEAR_X, SPEAR_Z
    H.frustum("forearm.R", "shaft", (x, 0.0, z), (x, 2.3, z), (0.04, 0.04), (0.045, 0.045), sides=6)
    H.chain("forearm.R", "blade", [(x, 2.3, z), (x, 2.5, z), (x, 2.72, z), (x, 2.9, z)],
            [(0.05, 0.03), (0.17, 0.035), (0.12, 0.03), (0.01, 0.01)], sides=4)
    H.frustum("forearm.R", "gold", (x, 2.2, z), (x, 2.32, z), (0.06, 0.06), (0.06, 0.06), sides=6)
    for s in (-1, 1):
        H.frustum("forearm.R", "leaf", (x, 2.1, z), (x + s * 0.2, 2.42, z), (0.05, 0.04), (0.13, 0.04), sides=4)
        H.frustum("forearm.R", "leaf_dk", (x, 2.0, z), (x + s * 0.17, 2.2, z), (0.05, 0.04), (0.1, 0.04), sides=4)


def make():
    head()
    torso()
    deer_body()
    legs()
    arms()
    spear()


def joints():
    out = {"spine.1": ((0, 1.3, -1.25), (0, 1.3, -0.6)), "spine.2": ((0, 1.3, -0.6), (0, 1.35, 0.0)),
           "spine.3": ((0, 1.45, 0), (0, 2.12, 0)), "head": ((0, 2.12, 0), (0, 2.7, 0)),
           "tail.1": ((0, 1.3, -1.36), (0, 1.5, -1.5)), "tail.2": ((0, 1.5, -1.5), (0, 1.76, -1.48))}
    for s, side in ((1, "L"), (-1, "R")):
        z = 0.12 if s < 0 else 0.0
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * (EL_X + 0.04), WR_Y, z))
    for n, x, z in ((1, 0.2, FRONT_Z), (2, -0.2, FRONT_Z), (3, 0.22, HIND_Z), (4, -0.22, HIND_Z)):
        out[f"leg{n}.upper"] = ((x, HIP_Y, z), (x, KNEE_Y, z))
        out[f"leg{n}.lower"] = ((x, KNEE_Y, z), (x, 0.06, z))
    return out


H.build("e006", "centaur", PALETTE, make, joints())
