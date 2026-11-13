"""Blood Fiend (n00L): medido em artifacts/model-sheets/refs/n00L/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n00L.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "maroon": 0x7A1A30, "maroon_dk": 0x5A1224, "dark": 0x2E1F22, "dark_dk": 0x231719, "gray": 0x7B7673,
    "gray_dk": 0x57524F, "red": 0xE01822, "tag": 0xD9CFB8, "hoof": 0x3A1519, "eye": 0xFF3030,
}

HIP, KNEE_Y, ANKLE, WAIST, NECK, TOP = 1.1, 0.64, 0.17, 1.36, 2.0, 2.5
SH_X, SH_Y, EL_X, EL_Y, WR_X, WR_Y = 0.62, 1.95, 0.72, 1.42, 0.77, 0.95


def head():
    H.frustum("head", "maroon", (0, 2.0, 0.3), (0, 1.97, 0.88), (0.25, 0.24), (0.14, 0.12), sides=6)     # focinho
    H.frustum("head", "maroon_dk", (0, 1.88, 0.3), (0, 1.84, 0.8), (0.16, 0.14), (0.1, 0.07), sides=6)  # mandíbula
    H.frustum("head", "maroon", (0, 1.82, 0.05), (0, 2.02, 0.4), (0.25, 0.22), (0.23, 0.21), sides=6)     # pescoço grosso
    H.frustum("head", "gray_dk", (0, 2.17, 0.28), (0, 2.27, 0.26), (0.22, 0.2), (0.14, 0.13), sides=8)  # base do espeto
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.1, 2.07, 0.62), (0.08, 0.05, 0.05))
        H.frustum("head", "gray", (s * 0.12, 2.18, 0.3), (s * 0.44, 2.25, 0.3), (0.07, 0.07), (0.09, 0.09), sides=6)  # chifre-cano
    H.frustum("head", "gray", (0, 2.26, 0.26), (0, 2.9, 0.2), (0.08, 0.08), (0.015, 0.015), sides=6)    # espeto do elmo
    H.box("head", "tag", (-0.14, 1.76, 0.5), (0.11, 0.22, 0.03))


def torso():
    H.frustum("spine", "dark", (0, WAIST - 0.04, 0), (0, 1.78, 0), (0.3, 0.25), (0.4, 0.3), sides=8)
    H.frustum("spine", "maroon", (0, 1.7, 0), (0, 2.1, 0.04), (0.42, 0.33), (0.6, 0.4), sides=8)
    H.frustum("spine", "maroon", (0, 2.1, 0.04), (0, 2.28, 0.06), (0.6, 0.4), (0.3, 0.26), sides=8)
    H.frustum("spine", "maroon", (0, 1.8, -0.2), (0, 2.25, -0.15), (0.4, 0.2), (0.46, 0.22), sides=6)    # corcunda
    H.frustum("spine", "maroon_dk", (0.3, 1.7, 0.36), (0.3, 1.7, 0.44), (0.17, 0.17), (0.17, 0.17), sides=8)  # válvula
    H.box("spine", "maroon", (0.3, 1.7, 0.45), (0.3, 0.05, 0.03))
    H.box("spine", "maroon", (0.3, 1.7, 0.45), (0.05, 0.3, 0.03))
    H.frustum("spine", "gray", (0.5, 2.25, -0.3), (-0.3, 1.5, -0.42), (0.06, 0.06), (0.06, 0.06), sides=4)  # corrente
    for s in (-1, 1):
        H.wheel("spine", "gray", (s * 0.64, 2.0, 0.05), 0.3, 0.17, sides=10)                             # tambor do ombro
        H.wheel("spine", "gray_dk", (s * 0.75, 2.0, 0.05), 0.24, 0.05, sides=10)
    H.frustum("pelvis", "dark_dk", (0, 0.9, 0), (0, WAIST, 0), (0.28, 0.24), (0.3, 0.25), sides=8)
    H.frustum("pelvis", "maroon_dk", (0, 1.06, 0.18), (0, 1.3, 0.2), (0.12, 0.05), (0.2, 0.06), sides=4)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        H.frustum(f"thigh.{side}", "dark", (s * 0.42, KNEE_Y, 0), (s * 0.27, HIP + 0.06, 0), (0.23, 0.23), (0.3, 0.28), sides=6)
        H.frustum(f"thigh.{side}", "red", (s * 0.42, KNEE_Y - 0.01, 0), (s * 0.42, KNEE_Y + 0.1, 0), (0.16, 0.16), (0.16, 0.16), sides=8)
        H.frustum(f"shin.{side}", "gray", (s * 0.4, ANKLE, 0), (s * 0.42, KNEE_Y + 0.03, 0), (0.13, 0.13), (0.2, 0.2), sides=6)
        H.frustum(f"shin.{side}", "red", (s * 0.4, 0.3, 0), (s * 0.4, 0.38, 0), (0.15, 0.15), (0.15, 0.15), sides=8)
        H.frustum(f"foot.{side}", "hoof", (s * 0.4, 0.03, -0.04), (s * 0.4, ANKLE + 0.04, -0.04), (0.18, 0.2), (0.14, 0.15), sides=6)
        H.frustum(f"foot.{side}", "hoof", (s * 0.4, 0.1, 0.0), (s * 0.4, 0.06, 0.5), (0.19, 0.14), (0.14, 0.05), sides=4)


def arms():
    for s, side in ((1, "L"), (-1, "R")):
        H.frustum(f"arm.{side}", "dark", (s * (SH_X + 0.02), SH_Y + 0.05, 0), (s * EL_X, EL_Y + 0.02, 0), (0.22, 0.24), (0.19, 0.21), sides=6)
        H.frustum(f"arm.{side}", "red", (s * EL_X, EL_Y + 0.1, 0), (s * EL_X, EL_Y - 0.02, 0), (0.22, 0.23), (0.22, 0.23), sides=6)
        H.frustum(f"forearm.{side}", "dark", (s * EL_X, EL_Y, 0), (s * WR_X, WR_Y + 0.05, 0.03), (0.2, 0.21), (0.19, 0.2), sides=6)
        H.frustum(f"forearm.{side}", "red", (s * WR_X, WR_Y + 0.08, 0.03), (s * WR_X, WR_Y + 0.02, 0.03), (0.17, 0.17), (0.17, 0.17), sides=6)
        H.frustum(f"forearm.{side}", "dark_dk", (s * WR_X, WR_Y + 0.03, 0.03), (s * (WR_X + 0.03), WR_Y - 0.33, 0.1), (0.18, 0.2), (0.25, 0.27), sides=6)  # punho


def make():
    head()
    torso()
    legs()
    arms()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * WR_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * 0.27, HIP, 0), (s * 0.42, KNEE_Y, 0))
        out[f"shin.{side}"] = ((s * 0.42, KNEE_Y, 0), (s * 0.4, ANKLE, 0))
        out[f"foot.{side}"] = ((s * 0.4, ANKLE, 0), (s * 0.4, 0.06, 0.5))
    return out


H.build("n00L", "biped", PALETTE, make, joints())
