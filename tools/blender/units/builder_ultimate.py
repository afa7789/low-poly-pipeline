"""Ultimate Builder (builder_ultimate): medido em artifacts/model-sheets/refs/builder_ultimate/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/builder_ultimate.py -- <out.glb>

O cajado fica na mão direita (x negativo), adiante do corpo e ao lado: a lanterna nunca fica atrás.
"""
import pathlib
import sys

from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "robe": 0x2B2B38, "robe_dk": 0x1F1F29, "brown": 0x45342A, "green": 0x4E5A48, "pink": 0xC8416E,
    "teal": 0x4A7A74, "cream": 0xCBBF9E, "belt": 0x7A4A2A, "steel": 0x8E8E92, "staff": 0x4A4548,
    "glow": 0xF0A830, "horn": 0xC8503C, "eye": 0xFFC030, "glove": 0x1E1E22, "boot": 0x40302A,
    "void": 0x07070B, "sole": 0x1A1A1C,
}

HIP, KNEE, ANKLE, LEG_X = 1.1, 0.6, 0.2, 0.26
WAIST, NECK, TOP = 1.45, 2.1, 2.7
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.5, 2.02, 0.56, 1.5, 0.98
SKIRT_MID = 0.8


def hem(p):
    """A barra do roupão acompanha a coxa do seu lado; o topo fica na pelve."""
    if p[1] > SKIRT_MID:
        return {"pelvis": 1.0}
    return {"pelvis": 0.4, "thigh.L" if p[0] > 0 else "thigh.R": 0.6}


def head():
    H.frustum("head", "robe", (0, 2.0, -0.02), (0, 2.34, -0.03), (0.3, 0.3), (0.34, 0.33), sides=8)      # capuz: base larga
    H.frustum("head", "robe", (0, 2.34, -0.03), (0, 2.62, -0.04), (0.34, 0.33), (0.2, 0.22), sides=8)
    H.frustum("head", "robe", (0, 2.62, -0.04), (0, 2.74, -0.06), (0.2, 0.22), (0.06, 0.08), sides=8)
    H.chain("head", "robe_dk", [(0, 2.55, -0.2), (0, 2.5, -0.34), (0, 2.4, -0.46)], [(0.1, 0.1), (0.07, 0.08), (0.01, 0.01)])  # ponta atrás
    H.frustum("head", "void", (0, 2.16, 0.18), (0, 2.5, 0.2), (0.2, 0.1), (0.22, 0.1), sides=6)           # rosto vazio
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.09, 2.36, 0.3), (0.07, 0.04, 0.02))
        H.chain("head", "horn", [(s * 0.2, 2.56, 0.0), (s * 0.3, 2.68, 0.0), (s * 0.3, 2.86, 0.0)],
                [(0.07, 0.07), (0.05, 0.05), (0.01, 0.01)])


def torso():
    H.frustum("spine", "robe", (0, WAIST - 0.05, 0), (0, 1.85, 0), (0.42, 0.33), (0.5, 0.36), sides=8)
    H.frustum("spine", "robe", (0, 1.85, 0), (0, 2.12, 0), (0.5, 0.36), (0.3, 0.28), sides=8)
    H.frustum("spine", "green", (0.2, 2.0, 0.0), (0.38, 2.14, 0.0), (0.2, 0.37), (0.2, 0.36), sides=4)    # remendo do ombro
    H.frustum("spine", "brown", (-0.3, 1.5, 0.3), (-0.3, 1.9, 0.3), (0.12, 0.07), (0.12, 0.07), sides=4)
    H.frustum("spine", "cream", (-0.2, 1.7, -0.33), (-0.2, 2.1, -0.33), (0.12, 0.05), (0.15, 0.05), sides=4)
    H.frustum("pelvis", "belt", (0, WAIST - 0.1, 0), (0, WAIST + 0.08, 0), (0.46, 0.38), (0.46, 0.38), sides=8)
    H.box("pelvis", "steel", (0, WAIST - 0.02, 0.4), (0.18, 0.14, 0.04))
    for x, y in ((-0.2, 1.18), (0.12, 1.14), (0.3, 1.2)):    # ferramentas penduradas no cinto
        H.frustum("pelvis", "steel", (x, y - 0.14, 0.4), (x, y + 0.1, 0.4), (0.04, 0.03), (0.07, 0.04), sides=4)


def robe():
    skirt = H.frustum("pelvis", "robe", (0, 0.27, 0), (0, WAIST - 0.06, 0), (0.54, 0.46), (0.44, 0.36), sides=8)
    H.soft(skirt, hem)
    for x, tone, lo, hi in ((-0.2, "brown", 0.3, 0.7), (0.2, "brown", 0.3, 0.55)):
        patch = H.frustum("pelvis", tone, (x, lo, 0.4), (x, hi, 0.38), (0.15, 0.04), (0.14, 0.04), sides=4)
        H.soft(patch, hem)
    pink = H.frustum("pelvis", "pink", (0.0, 0.6, -0.4), (0.0, 1.05, -0.36), (0.18, 0.04), (0.17, 0.04), sides=4)
    H.soft(pink, hem)
    teal = H.frustum("pelvis", "teal", (-0.25, 0.4, -0.43), (-0.25, 0.7, -0.41), (0.1, 0.04), (0.1, 0.04), sides=4)
    H.soft(teal, hem)


def legs(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "robe_dk", (x, KNEE - 0.04, 0), (x, HIP + 0.04, 0), (0.22, 0.24), (0.24, 0.26), sides=6)
    H.frustum(f"shin.{side}", "boot", (x, ANKLE - 0.02, 0), (x, KNEE + 0.02, 0), (0.2, 0.2), (0.22, 0.22), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.04, -0.03), (x, ANKLE + 0.04, -0.03), (0.2, 0.23), (0.2, 0.21), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.12, 0.06), (x, 0.09, 0.44), (0.2, 0.12), (0.17, 0.07), sides=4)
    H.frustum(f"foot.{side}", "sole", (x, 0.02, -0.2), (x, 0.02, 0.45), (0.21, 0.022), (0.18, 0.022), sides=4)


def left_arm():
    """Braço esquerdo pende ao lado: manga larga com punho dobrado e luva."""
    H.frustum("arm.L", "robe", (SH_X, SH_Y + 0.04, 0), (EL_X, EL_Y - 0.02, 0), (0.2, 0.22), (0.2, 0.2), sides=6)
    H.frustum("forearm.L", "robe", (EL_X, EL_Y + 0.02, 0), (EL_X, WR_Y + 0.1, 0.03), (0.2, 0.2), (0.24, 0.22), sides=6)
    H.frustum("forearm.L", "belt", (EL_X, WR_Y + 0.12, 0.03), (EL_X, WR_Y + 0.02, 0.03), (0.25, 0.23), (0.25, 0.23), sides=6)
    H.frustum("forearm.L", "glove", (EL_X, WR_Y + 0.02, 0.03), (EL_X, WR_Y - 0.26, 0.05), (0.15, 0.17), (0.13, 0.15), sides=6)


def right_arm():
    """Braço direito dobrado à frente, a luva fecha o cajado; antebraço sobe para frente e para o lado."""
    el, hand = Vector((-EL_X, EL_Y, 0.02)), Vector((-0.7, 1.72, 0.62))
    H.frustum("arm.R", "robe", (-SH_X, SH_Y + 0.04, 0), (-EL_X, EL_Y - 0.02, 0), (0.2, 0.22), (0.2, 0.2), sides=6)
    mid = el.lerp(hand, 0.7)
    H.frustum("forearm.R", "robe", el, mid, (0.2, 0.2), (0.2, 0.2), sides=6)
    H.frustum("forearm.R", "glove", mid, hand + Vector((0, 0.02, 0.05)), (0.16, 0.16), (0.15, 0.15), sides=6)


def staff():
    """Cajado na frente (z ~0.62) e ao lado do corpo: haste, lanterna alta no topo, ponteira embaixo."""
    x, z = -0.7, 0.62
    H.frustum("forearm.R", "staff", (x, 0.04, z), (x, 2.4, z), (0.045, 0.045), (0.04, 0.04), sides=6)
    H.frustum("forearm.R", "steel", (x, 0.0, z), (x, 0.12, z), (0.07, 0.07), (0.05, 0.05), sides=6)
    H.frustum("forearm.R", "staff", (x, 2.3, z), (x, 2.45, z), (0.1, 0.1), (0.14, 0.14), sides=6)
    H.frustum("forearm.R", "glow", (x, 2.45, z), (x, 2.82, z), (0.12, 0.12), (0.12, 0.12), sides=6)
    for dx, dz in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        H.frustum("forearm.R", "staff", (x + dx * 0.15, 2.45, z + dz * 0.15), (x + dx * 0.15, 2.84, z + dz * 0.15),
                  (0.025, 0.025), (0.025, 0.025), sides=4)
    H.frustum("forearm.R", "staff", (x, 2.82, z), (x, 2.94, z), (0.17, 0.17), (0.06, 0.06), sides=6)
    H.frustum("forearm.R", "steel", (x, 2.94, z), (x, 3.04, z), (0.05, 0.02), (0.05, 0.02), sides=4)


def make():
    head()
    torso()
    robe()
    for s, side in ((1, "L"), (-1, "R")):
        legs(s, side)
    left_arm()
    right_arm()
    staff()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * SH_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("builder_ultimate", "biped", PALETTE, make, joints())
