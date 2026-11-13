"""Warlock (n005): medido em artifacts/model-sheets/refs/n005/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n005.py -- <out.glb>

Brutamontes de sobretudo preto e máscara de gás; revólver na mão direita (antebraço R), frasco na esquerda.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "coat": 0x222227, "coat_lt": 0x2E2E35, "lapel": 0x3A3A43, "under": 0x17171A, "boot": 0x34343B, "sole": 0x1A1A1E,
    "mask": 0x151518, "lens": 0xC8404E, "filter": 0x80808A, "metal": 0x72727C, "metal_dk": 0x4A4A52, "glass": 0x55555E,
    "liquid": 0x141418, "glove": 0x2A2A30,
}

HIP, KNEE, ANKLE, LEG_X = 0.98, 0.52, 0.17, 0.3
WAIST, NECK, TOP = 1.3, 2.1, 2.72
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.72, 2.2, 0.82, 1.62, 1.2
SKIRT_MID = 0.95


def hem(p):
    if p[1] > SKIRT_MID:
        return {"pelvis": 1.0}
    return {"pelvis": 0.45, "thigh.L" if p[0] > 0 else "thigh.R": 0.55}


def head():
    H.frustum("head", "mask", (0, 2.0, 0.06), (0, 2.4, 0.1), (0.22, 0.22), (0.25, 0.24), sides=8)
    H.frustum("head", "mask", (0, 2.4, 0.1), (0, 2.72, 0.08), (0.25, 0.24), (0.16, 0.15), sides=8)
    H.frustum("head", "filter", (0, 2.14, 0.24), (0, 2.14, 0.46), (0.11, 0.11), (0.13, 0.13), sides=8)
    H.frustum("head", "mask", (0, 2.14, 0.2), (0, 2.14, 0.26), (0.18, 0.15), (0.12, 0.12), sides=8)
    for s in (-1, 1):
        H.frustum("head", "lens", (s * 0.11, 2.4, 0.3), (s * 0.11, 2.4, 0.36), (0.07, 0.07), (0.07, 0.07), sides=6)


def torso():
    H.frustum("spine", "coat", (0, WAIST - 0.05, 0), (0, 2.0, 0), (0.5, 0.4), (0.62, 0.44), sides=8)
    H.frustum("spine", "coat", (0, 2.0, 0), (0, 2.28, 0), (0.62, 0.44), (0.36, 0.3), sides=8)
    H.frustum("spine", "under", (0, 1.4, 0.3), (0, 2.1, 0.3), (0.2, 0.12), (0.22, 0.12), sides=4)       # peito aberto
    for s in (-1, 1):   # lapelas
        H.frustum("spine", "lapel", (s * 0.18, 1.45, 0.42), (s * 0.46, 2.18, 0.4), (0.09, 0.05), (0.15, 0.06), sides=4)
    H.frustum("spine", "lapel", (0, 2.1, -0.1), (0, 2.34, -0.1), (0.4, 0.32), (0.36, 0.3), sides=8)     # gola
    H.frustum("pelvis", "under", (0, WAIST - 0.1, 0), (0, WAIST + 0.04, 0), (0.46, 0.38), (0.46, 0.38), sides=8)
    skirt = H.frustum("pelvis", "coat", (0, 0.4, 0), (0, WAIST - 0.04, 0), (0.66, 0.46), (0.5, 0.4), sides=8)
    H.soft(skirt, hem)
    H.frustum("pelvis", "under", (0, 0.8, 0), (0, 1.1, 0), (0.4, 0.34), (0.44, 0.36), sides=8)


def arm(s, side):
    H.frustum(f"arm.{side}", "coat", (s * (SH_X - 0.08), SH_Y + 0.12, 0), (s * SH_X, SH_Y - 0.12, 0), (0.28, 0.3), (0.3, 0.32), sides=8)   # ombro
    H.frustum(f"arm.{side}", "coat", (s * SH_X, SH_Y - 0.05, 0), (s * EL_X, EL_Y, 0), (0.3, 0.3), (0.25, 0.25), sides=8)
    H.frustum(f"forearm.{side}", "coat_lt", (s * EL_X, EL_Y + 0.04, 0), (s * EL_X, WR_Y + 0.1, 0.02), (0.26, 0.26), (0.24, 0.24), sides=8)
    H.frustum(f"forearm.{side}", "glove", (s * EL_X, WR_Y + 0.12, 0.02), (s * EL_X, WR_Y - 0.12, 0.05), (0.24, 0.24), (0.27, 0.27), sides=8)    # mão


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * LEG_X
        H.frustum(f"thigh.{side}", "under", (x, KNEE - 0.04, 0), (x, HIP + 0.04, 0), (0.26, 0.28), (0.3, 0.3), sides=6)
        H.frustum(f"shin.{side}", "under", (x, 0.3, 0), (x, KNEE + 0.02, 0), (0.22, 0.24), (0.26, 0.26), sides=6)
        H.frustum(f"shin.{side}", "boot", (x, 0.04, 0), (x, 0.4, 0), (0.24, 0.26), (0.2, 0.22), sides=6)
        H.frustum(f"foot.{side}", "boot", (x, 0.12, 0.0), (x, 0.1, 0.46), (0.25, 0.13), (0.22, 0.09), sides=6)
        H.frustum(f"foot.{side}", "sole", (x, 0.02, -0.1), (x, 0.02, 0.5), (0.26, 0.04), (0.22, 0.04), sides=6)


def revolver():
    """Na mão direita (antebraço R), apontando à frente como no perfil."""
    x, y = -0.7, 1.16
    H.frustum("forearm.R", "metal_dk", (x, y - 0.2, 0.2), (x, y, 0.16), (0.08, 0.07), (0.09, 0.09), sides=4)     # cabo
    H.frustum("forearm.R", "metal", (x, y, 0.1), (x, y, 0.55), (0.14, 0.15), (0.15, 0.14), sides=6)            # tambor/corpo
    H.frustum("forearm.R", "metal", (x, y + 0.02, 0.55), (x, y + 0.02, 1.15), (0.09, 0.09), (0.07, 0.07), sides=6)   # cano


def flask():
    x, y = 0.74, 1.0
    H.frustum("forearm.L", "glass", (x, y - 0.22, 0.4), (x, y + 0.02, 0.4), (0.12, 0.12), (0.2, 0.2), sides=8)
    H.frustum("forearm.L", "liquid", (x, y - 0.22, 0.4), (x, y - 0.08, 0.4), (0.12, 0.12), (0.18, 0.18), sides=8)
    H.frustum("forearm.L", "glass", (x, y + 0.02, 0.4), (x, y + 0.14, 0.4), (0.2, 0.2), (0.07, 0.07), sides=8)
    H.frustum("forearm.L", "metal_dk", (x, y + 0.14, 0.4), (x, y + 0.22, 0.4), (0.07, 0.07), (0.06, 0.06), sides=6)


def make():
    head()
    torso()
    legs()
    for s, side in ((1, "L"), (-1, "R")):
        arm(s, side)
    revolver()
    flask()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)), "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("n005", "biped", PALETTE, make, joints())
