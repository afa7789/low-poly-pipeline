"""Archer (n022): medido em artifacts/model-sheets/refs/n022/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n022.py -- <out.glb>

Mascara de gas, bloco enorme de ombros/mochila, casaco longo. Bracos pendurados na direcao de repouso dos ossos; arco
vertical ao lado do corpo no punho direito (forearm.R); o clipe de ataque o levanta.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "slab": 0x2E4A5A, "coat": 0x233648, "coat_dk": 0x16283A, "teal": 0x3A6272, "belt": 0x1E7378, "cream": 0xE8DEC4,
    "brass": 0xA07840, "mask": 0x4C7A84, "lens": 0x1E8B8F, "glass": 0x2B6E78, "bow": 0x1B2B3B, "string": 0xEFE8D4, "helm": 0x1F3446,
}

HIP, KNEE, ANKLE, LEG_X = 1.0, 0.56, 0.14, 0.21
WAIST, NECK, TOP = 1.5, 2.1, 2.72


def head():
    H.frustum("head", "helm", (0, 2.14, 0.08), (0, 2.6, 0.08), (0.19, 0.22), (0.2, 0.22), sides=8)
    H.frustum("head", "helm", (0, 2.6, 0.08), (0, 2.74, 0.04), (0.2, 0.22), (0.11, 0.12), sides=8)
    H.frustum("head", "cream", (0, 2.58, 0.08), (0, 2.66, 0.08), (0.205, 0.225), (0.2, 0.22), sides=8)      # faixa
    H.frustum("head", "mask", (0, 2.22, 0.24), (0, 2.46, 0.4), (0.1, 0.07), (0.07, 0.09), sides=6)           # filtro
    H.frustum("head", "coat_dk", (0, 2.2, 0.0), (0, 2.5, 0.0), (0.12, 0.1), (0.14, 0.12), sides=6)
    H.frustum("head", "brass", (-0.13, 2.42, 0.27), (-0.13, 2.58, 0.27), (0.01, 0.01), (0.01, 0.01), sides=4)
    H.frustum("head", "lens", (-0.09, 2.52, 0.27), (-0.09, 2.52, 0.34), (0.075, 0.075), (0.07, 0.07), sides=8)  # lentes
    H.frustum("head", "lens", (0.1, 2.52, 0.27), (0.1, 2.52, 0.34), (0.06, 0.06), (0.055, 0.055), sides=8)
    for s in (-1, 1):
        H.chain("head", "cream", [(s * 0.16, 2.42, 0.0), (s * 0.34, 2.54, -0.02), (s * 0.54, 2.68, -0.05)],
                [(0.07, 0.035), (0.05, 0.025), (0.008, 0.008)], sides=4)


def torso():
    H.frustum("spine", "coat", (0, WAIST - 0.05, 0), (0, 2.1, 0), (0.28, 0.2), (0.36, 0.24), sides=8)
    H.frustum("spine", "coat", (0, 2.05, 0), (0, 2.28, 0), (0.34, 0.24), (0.2, 0.18), sides=8)
    H.box("spine", "slab", (0, 2.05, -0.06), (1.34, 0.5, 0.6))                                           # bloco de ombros
    H.box("spine", "coat_dk", (0, 2.02, -0.07), (0.62, 0.4, 0.62))
    H.frustum("spine", "brass", (0.05, 1.86, 0.25), (0.05, 1.86, 0.3), (0.09, 0.09), (0.09, 0.09), sides=8)   # manometro
    H.frustum("pelvis", "belt", (0, WAIST - 0.14, 0), (0, WAIST + 0.02, 0), (0.37, 0.27), (0.36, 0.26), sides=8)
    H.frustum("pelvis", "brass", (0.46, 1.3, 0), (0.46, 1.46, 0), (0.1, 0.12), (0.1, 0.12), sides=8)        # carretel
    H.frustum("pelvis", "glass", (-0.5, 1.15, 0), (-0.5, 1.4, 0), (0.12, 0.12), (0.08, 0.08), sides=6)      # frasco


def hem(p):
    return {"pelvis": 1.0} if p[1] > 1.0 else {"pelvis": 0.35, "thigh.L" if p[0] > 0 else "thigh.R": 0.65}


def coat():
    low = H.frustum("pelvis", "coat", (0, 0.58, 0), (0, WAIST - 0.1, 0), (0.46, 0.3), (0.3, 0.22), sides=8)
    H.soft(low, hem)
    H.frustum("pelvis", "teal", (0, 0.62, 0.22), (0, 1.3, 0.2), (0.28, 0.05), (0.14, 0.05), sides=4)       # avental


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * LEG_X
        H.frustum(f"thigh.{side}", "teal", (x, KNEE - 0.04, 0), (x, HIP + 0.05, 0), (0.14, 0.15), (0.19, 0.18), sides=6)
        H.frustum(f"shin.{side}", "coat_dk", (x, ANKLE, 0), (x, KNEE + 0.02, 0), (0.13, 0.14), (0.16, 0.16), sides=6)
        H.frustum(f"foot.{side}", "coat_dk", (x, 0.03, -0.03), (x, ANKLE + 0.04, -0.03), (0.15, 0.17), (0.13, 0.15), sides=6)
        H.frustum(f"foot.{side}", "coat_dk", (x, 0.11, 0.04), (x, 0.08, 0.46), (0.16, 0.1), (0.13, 0.06), sides=4)


def arms():
    H.frustum("arm.L", "coat", (0.55, 2.04, 0), (0.64, 1.58, 0), (0.15, 0.16), (0.12, 0.13), sides=6)
    H.frustum("forearm.L", "coat", (0.64, 1.62, 0), (0.68, 1.3, 0.02), (0.13, 0.13), (0.14, 0.14), sides=6)
    H.frustum("forearm.L", "coat_dk", (0.68, 1.32, 0.02), (0.7, 1.04, 0.04), (0.14, 0.14), (0.13, 0.14), sides=6)
    H.frustum("arm.R", "coat", (-0.55, 2.04, 0), (-0.66, 1.6, 0.02), (0.15, 0.16), (0.12, 0.13), sides=6)
    H.frustum("forearm.R", "coat", (-0.66, 1.64, 0.02), (-0.72, 1.3, 0.06), (0.13, 0.13), (0.14, 0.14), sides=6)
    H.frustum("forearm.R", "coat_dk", (-0.72, 1.32, 0.06), (-0.74, 1.04, 0.1), (0.14, 0.14), (0.13, 0.14), sides=6)


def bow():
    """Arco vertical ao lado do corpo, no punho direito (forearm.R); o ataque levanta o antebraco."""
    x, z = -0.82, 0.12
    pts = [(x, 2.2, z - 0.12), (x, 1.7, z - 0.02), (x, 1.12, z), (x, 0.55, z - 0.02), (x, 0.0, z - 0.12)]
    H.chain("forearm.R", "bow", pts, [(0.05, 0.05), (0.06, 0.06), (0.075, 0.075), (0.06, 0.06), (0.05, 0.05)], sides=6)
    for y, dz in ((2.22, -0.12), (0.0, -0.12)):
        H.frustum("forearm.R", "brass", (x, y, z + dz), (x, y + (0.1 if y > 1 else -0.1), z + dz), (0.07, 0.07), (0.06, 0.06), sides=6)
    H.frustum("forearm.R", "brass", (x, 1.04, z), (x, 1.24, z), (0.1, 0.1), (0.1, 0.1), sides=6)       # empunhadura
    H.frustum("forearm.R", "string", (x, 2.2, z - 0.12), (x, 0.0, z - 0.12), (0.02, 0.02), (0.02, 0.02), sides=4)


def make():
    head()
    torso()
    coat()
    legs()
    arms()
    bow()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)), "head": ((0, NECK, 0), (0, TOP, 0)),
           "arm.L": ((0.55, 2.04, 0), (0.64, 1.6, 0)), "forearm.L": ((0.64, 1.6, 0), (0.7, 1.04, 0.04)),
           "arm.R": ((-0.55, 2.04, 0), (-0.66, 1.62, 0.02)), "forearm.R": ((-0.66, 1.62, 0.02), (-0.74, 1.04, 0.1))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("n022", "biped", PALETTE, make, joints())
