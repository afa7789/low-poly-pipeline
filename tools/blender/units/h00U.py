"""Bloodthirster (h00U): elfo de mascara de latao, casaco azul-petroleo, glaive-flecha na mao esquerda e
placa de latao no antebraco direito; medido em refs/h00U/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/h00U.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "brass": 0xA8802C, "brass_dk": 0x7A5A1E, "eye": 0xE8F5A0, "eye_dk": 0x4A3418, "ear": 0xD9A890, "coat": 0x2C4650,
    "coat_dk": 0x1E3A3C, "lime": 0xC8E890, "sash": 0x3FA5A0, "gold": 0xD9A033, "slab": 0x213A3E, "glass": 0x4A4E52,
    "pole": 0x16191B, "vane": 0xE8E0D0, "book": 0x8A6A3A, "boot": 0xA8802C,
}
HIP, KNEE, ANKLE, LEG_X = 1.1, 0.5, 0.14, 0.25
WAIST, NECK, TOP = 1.4, 2.05, 2.58
POLE = (0.65, 0.32)     # x, z do glaive


def hem(p):
    """A aba do casaco acompanha as coxas embaixo; o topo fica na pelve."""
    if p[1] > 1.1:
        return {"pelvis": 1.0}
    return {"pelvis": 0.5, "thigh.L" if p[0] > 0 else "thigh.R": 0.5}


def head():
    H.frustum("head", "brass", (0, 2.1, 0.02), (0, 2.5, 0.03), (0.19, 0.2), (0.2, 0.2), sides=8)
    H.frustum("head", "brass", (0, 2.5, 0.03), (0, 2.6, 0.03), (0.2, 0.2), (0.1, 0.1), sides=8)
    H.frustum("head", "brass_dk", (0, 2.38, 0.16), (0, 2.14, 0.3), (0.07, 0.05), (0.04, 0.03), sides=4)
    H.box("head", "eye", (0.09, 2.38, 0.22), (0.09, 0.09, 0.03))
    H.box("head", "eye_dk", (-0.09, 2.38, 0.22), (0.08, 0.08, 0.03))
    for s in (-1, 1):
        H.frustum("head", "ear", (s * 0.18, 2.38, 0.0), (s * 0.5, 2.5, -0.02), (0.1, 0.03), (0.012, 0.01), sides=4)
    H.frustum("spine", "coat", (0, 1.98, 0), (0, 2.28, 0), (0.28, 0.23), (0.32, 0.25), sides=8)


def torso():
    H.frustum("spine", "coat", (0, WAIST - 0.04, 0), (0, 2.0, 0), (0.34, 0.26), (0.46, 0.31), sides=8)
    H.frustum("spine", "coat", (0, 2.0, 0), (0, 2.15, 0), (0.46, 0.31), (0.26, 0.22), sides=8)
    H.frustum("spine", "lime", (0, 1.45, 0.25), (0, 2.02, 0.28), (0.06, 0.04), (0.14, 0.04), sides=4)
    for z, ez in ((0.3, 0.3), (-0.3, -0.3)):
        H.frustum("spine", "sash", (-0.33, 2.02, z), (0.3, 1.42, ez), (0.09, 0.03), (0.09, 0.03), sides=4)
    H.frustum("pelvis", "gold", (0, WAIST - 0.1, 0), (0, WAIST + 0.06, 0), (0.4, 0.31), (0.4, 0.31), sides=8)
    H.box("pelvis", "book", (0.28, WAIST - 0.12, 0.34), (0.12, 0.16, 0.06))
    H.frustum("pelvis", "lime", (0, 0.95, 0.27), (0, 1.3, 0.28), (0.12, 0.04), (0.16, 0.04), sides=4)
    H.soft(H.frustum("pelvis", "coat", (0, 0.72, 0), (0, WAIST - 0.05, 0), (0.46, 0.34), (0.36, 0.28), sides=8), hem)
    H.frustum("pelvis", "glass", (-0.3, 0.98, -0.42), (-0.3, 1.28, -0.42), (0.17, 0.17), (0.07, 0.07), sides=6)


def legs(s, side):
    kx = s * LEG_X
    H.frustum(f"thigh.{side}", "coat_dk", (kx, KNEE - 0.06, 0), (kx, HIP + 0.05, 0), (0.2, 0.21), (0.24, 0.26), sides=6)
    H.frustum(f"shin.{side}", "boot", (kx, 0.04, 0), (kx, KNEE + 0.02, 0), (0.15, 0.16), (0.22, 0.22), sides=6)
    H.frustum(f"foot.{side}", "boot", (kx, 0.03, -0.04), (kx, ANKLE + 0.04, -0.03), (0.18, 0.2), (0.15, 0.17), sides=6)
    H.frustum(f"foot.{side}", "boot", (kx, 0.1, 0.0), (kx, 0.08, 0.46), (0.17, 0.12), (0.16, 0.07), sides=6)


def arms():
    H.frustum("arm.L", "coat", (0.46, 2.04, 0), (0.52, 1.58, 0.05), (0.2, 0.22), (0.17, 0.18), sides=6)
    H.frustum("forearm.L", "coat", (0.52, 1.64, 0.05), (0.62, 1.36, 0.3), (0.17, 0.18), (0.14, 0.15), sides=6)
    H.frustum("forearm.L", "brass", (0.62, 1.42, 0.3), (0.62, 1.2, 0.3), (0.16, 0.16), (0.14, 0.14), sides=6)
    H.frustum("arm.R", "coat", (-0.46, 2.04, 0), (-0.56, 1.58, 0), (0.2, 0.22), (0.17, 0.18), sides=6)
    H.frustum("forearm.R", "coat_dk", (-0.56, 1.64, 0), (-0.6, 1.1, 0.03), (0.17, 0.18), (0.14, 0.15), sides=6)
    H.frustum("forearm.R", "brass", (-0.6, 1.1, 0.03), (-0.62, 0.86, 0.06), (0.16, 0.16), (0.13, 0.13), sides=6)


def slab():
    H.box("forearm.R", "slab", (-0.74, 1.3, 0.15), (0.15, 0.9, 0.62))
    for y in (0.95, 1.3, 1.65):
        H.box("forearm.R", "gold", (-0.76, y, 0.15), (0.2, 0.08, 0.68))
    H.box("forearm.R", "gold", (-0.74, 1.3, -0.12), (0.17, 0.95, 0.06))
    H.box("forearm.R", "gold", (-0.74, 1.3, 0.42), (0.17, 0.95, 0.06))


def glaive():
    x, z = POLE
    H.frustum("forearm.L", "pole", (x, 0.8, z), (x, 2.58, z), (0.07, 0.07), (0.06, 0.06), sides=6)
    for y in (1.2, 1.9, 2.3):
        H.frustum("forearm.L", "gold", (x, y, z), (x, y + 0.08, z), (0.09, 0.09), (0.09, 0.09), sides=6)
    for y in (2.1, 2.42):
        for s in (-1, 1):
            H.panel("forearm.L", "vane", [(x + s * 0.02, y, z), (x + s * 0.27, y + 0.16, z), (x + s * 0.27, y + 0.3, z), (x + s * 0.02, y + 0.14, z)], 0.025)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        legs(s, side)
    arms()
    slab()
    glaive()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)), "head": ((0, NECK, 0), (0, TOP, 0)),
           "arm.L": ((0.46, 2.0, 0), (0.52, 1.6, 0.05)), "forearm.L": ((0.52, 1.6, 0.05), (0.62, 1.3, 0.3)),
           "arm.R": ((-0.46, 2.0, 0), (-0.56, 1.6, 0)), "forearm.R": ((-0.56, 1.6, 0), (-0.62, 1.0, 0.05))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("h00U", "biped", PALETTE, make, joints())
