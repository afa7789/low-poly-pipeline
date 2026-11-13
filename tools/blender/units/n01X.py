"""Iron Golem (n01X): medido em artifacts/model-sheets/refs/n01X/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n01X.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "iron": 0x46464E, "iron_dk": 0x34343B, "iron_lt": 0x55555E, "brass": 0x8A6A3E, "brass_dk": 0x6E532E,
    "fire": 0xFFE81A, "door": 0x23232A,
}

HIP, KNEE, ANKLE = 1.14, 0.64, 0.2
WAIST, NECK, TOP = 1.3, 2.4, 2.72
SH_X, SH_Y, EL_X, EL_Y, WR_X, WR_Y = 0.64, 2.05, 0.7, 1.5, 0.78, 0.9
LEG_X, KNEE_X, ANK_X = 0.25, 0.28, 0.3


def head():
    H.frustum("head", "iron_dk", (0, 2.4, 0), (0, 2.52, 0), (0.12, 0.12), (0.1, 0.1), sides=4)
    H.frustum("head", "brass", (0, 2.5, 0), (0, 2.64, 0), (0.05, 0.05), (0.04, 0.04), sides=4)
    for s in (-1, 1):
        H.frustum("head", "brass", (s * 0.04, 2.56, 0), (s * 0.26, 2.66, 0), (0.04, 0.04), (0.04, 0.04), sides=4)
    H.frustum("head", "brass", (0, 2.65, 0), (0, 2.72, 0), (0.32, 0.32), (0.3, 0.3), sides=8)


def torso():
    pts = [(1.0, 0.2, 0.2), (1.3, 0.42, 0.42), (1.75, 0.5, 0.48), (2.2, 0.46, 0.45), (2.4, 0.4, 0.4)]
    for (y0, a0, d0), (y1, a1, d1) in zip(pts, pts[1:]):
        H.frustum("spine", "iron", (0, y0, 0), (0, y1, 0), (a0, d0), (a1, d1), sides=8)
    H.frustum("spine", "iron_dk", (0, 2.36, 0), (0, 2.45, 0), (0.46, 0.45), (0.42, 0.42), sides=8)       # tampa
    for y, r in ((1.28, 0.44), (1.55, 0.5), (2.05, 0.48)):
        H.frustum("spine", "iron_dk", (0, y - 0.03, 0), (0, y + 0.03, 0), (r + 0.015, r + 0.01), (r + 0.015, r + 0.01), sides=8)
    # porta da fornalha com chama
    H.box("spine", "iron_dk", (0, 1.42, 0.5), (0.4, 0.34, 0.06))
    H.box("spine", "door", (0, 1.4, 0.535), (0.3, 0.27, 0.04))
    H.box("spine", "fire", (0, 1.38, 0.56), (0.2, 0.2, 0.04))
    H.box("spine", "fire", (0.02, 1.52, 0.56), (0.1, 0.1, 0.04))
    for s in (-1, 1):
        H.frustum("pelvis", "brass", (s * 0.12, 1.05, 0.0), (s * 0.28, 1.2, 0.0), (0.07, 0.1), (0.07, 0.1), sides=4)
    H.frustum("pelvis", "iron_dk", (0, 1.0, 0), (0, 1.3, 0), (0.27, 0.27), (0.4, 0.4), sides=8)


def leg(s, side):
    H.frustum(f"thigh.{side}", "iron", (s * KNEE_X, KNEE + 0.02, 0), (s * LEG_X, HIP + 0.06, 0), (0.14, 0.16), (0.16, 0.18), sides=8)
    H.frustum(f"thigh.{side}", "brass", (s * KNEE_X, KNEE - 0.06, 0), (s * KNEE_X, KNEE + 0.07, 0), (0.18, 0.2), (0.18, 0.2), sides=8)
    H.frustum(f"shin.{side}", "iron", (s * ANK_X, ANKLE, 0), (s * KNEE_X, KNEE - 0.04, 0), (0.17, 0.18), (0.14, 0.16), sides=8)
    H.frustum(f"shin.{side}", "brass", (s * ANK_X, ANKLE - 0.02, 0), (s * ANK_X, ANKLE + 0.06, 0), (0.18, 0.2), (0.18, 0.2), sides=8)
    H.frustum(f"foot.{side}", "iron_dk", (s * ANK_X, 0.16, -0.12), (s * ANK_X, 0.1, 0.0), (0.18, 0.2), (0.2, 0.22), sides=6)
    H.frustum(f"foot.{side}", "iron_dk", (s * ANK_X, 0.11, -0.05), (s * ANK_X, 0.05, 0.52), (0.21, 0.26), (0.18, 0.1), sides=4)


def arm(s, side):
    px = s * SH_X
    H.frustum(f"arm.{side}", "iron", (px, 1.92, 0.02), (px, 2.12, 0.02), (0.27, 0.29), (0.26, 0.28), sides=8)       # ombreira
    H.frustum(f"arm.{side}", "iron_lt", (px, 2.12, 0.02), (px, 2.34, 0.02), (0.26, 0.28), (0.14, 0.17), sides=8)
    H.frustum(f"arm.{side}", "iron", (s * 0.66, 2.0, 0.04), (s * EL_X, EL_Y + 0.02, 0.06), (0.14, 0.16), (0.13, 0.15), sides=8)
    H.frustum(f"arm.{side}", "brass", (s * EL_X, EL_Y - 0.08, 0.06), (s * EL_X, EL_Y + 0.08, 0.06), (0.15, 0.18), (0.15, 0.18), sides=8)
    gx = s * WR_X
    H.frustum(f"forearm.{side}", "iron", (gx, 1.46, 0.08), (gx, 0.9, 0.1), (0.24, 0.26), (0.27, 0.28), sides=6)     # manopla
    H.frustum(f"forearm.{side}", "iron_lt", (gx, 0.92, 0.1), (gx, 0.64, 0.14), (0.28, 0.29), (0.34, 0.32), sides=6)    # punho
    H.frustum(f"forearm.{side}", "iron", (gx, 0.64, 0.14), (gx, 0.38, 0.16), (0.34, 0.32), (0.26, 0.26), sides=6)
    H.frustum(f"forearm.{side}", "iron_dk", (gx, 0.7, 0.4), (gx, 0.42, 0.4), (0.3, 0.06), (0.26, 0.06), sides=4)       # nos dos dedos
    H.frustum(f"forearm.{side}", "brass", (gx + s * 0.26, 0.66, 0.12), (gx + s * 0.34, 0.66, 0.12), (0.17, 0.17), (0.17, 0.17), sides=8)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        arm(s, side)


def joints():
    out = {"pelvis": ((0, 1.0, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0.04), (s * EL_X, EL_Y, 0.06))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0.06), (s * WR_X, WR_Y, 0.1))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * KNEE_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * ANK_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * ANK_X, ANKLE, 0), (s * ANK_X, 0.06, 0.5))
    return out


H.build("n01X", "biped", PALETTE, make, joints())
