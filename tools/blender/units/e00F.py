"""Gigante da Montanha (e00F): medido em artifacts/model-sheets/refs/e00F/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/e00F.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "stone": 0x7E8084, "stone_dk": 0x5E6074, "stone_lt": 0x9A9C9C, "moss": 0x6E8F3A, "moss_lt": 0xB0B84A,
    "brow": 0x3A3C44,
}

HIP, KNEE, ANKLE = 1.0, 0.55, 0.14
WAIST, NECK, TOP = 1.3, 2.1, 2.72
SH_X, SH_Y, EL_X, EL_Y, WR_X, WR_Y = 0.62, 2.0, 0.84, 1.5, 0.84, 0.98
LEG_X = 0.26


def stack(bone, color, pts, sides=8):
    """Pilha de troncos de cone sobrepostos: pts = [(x, y, z, rx, rz), ...]."""
    for a, b in zip(pts, pts[1:]):
        H.frustum(bone, color, a[:3], b[:3], a[3:], b[3:], sides=sides)


def head():
    stack("head", "stone", [(0, 2.12, 0.05, 0.2, 0.2), (0, 2.4, 0.08, 0.24, 0.24), (0, 2.72, 0.1, 0.2, 0.2)], 4)
    H.frustum("spine", "moss_lt", (0, 2.02, 0), (0, 2.34, 0), (0.46, 0.38), (0.34, 0.3), sides=8)         # gola de musgo
    H.box("head", "brow", (0, 2.52, 0.3), (0.34, 0.05, 0.05))
    H.box("head", "brow", (0, 2.3, 0.31), (0.16, 0.04, 0.04))


def torso():
    stack("pelvis", "stone_dk", [(0, 0.88, 0, 0.3, 0.26), (0, 1.05, 0, 0.4, 0.3)])
    stack("pelvis", "moss", [(0, 1.05, 0, 0.4, 0.3), (0, 1.32, 0, 0.44, 0.31)])
    stack("spine", "stone", [(0, 1.3, 0, 0.44, 0.31), (0, 1.7, 0, 0.54, 0.35), (0, 2.05, 0, 0.5, 0.34), (0, 2.25, 0, 0.3, 0.26)])
    H.frustum("spine", "moss", (0.1, 1.35, 0.2), (0.1, 1.7, 0.22), (0.3, 0.2), (0.2, 0.2), sides=6)       # mancha de musgo no peito
    H.box("spine", "stone_dk", (-0.04, 1.85, 0.35), (0.05, 0.6, 0.03))                                  # rachadura


def leg(s, side):
    x0 = s * LEG_X
    stack(f"thigh.{side}", "stone_dk", [(x0, KNEE - 0.03, 0, 0.2, 0.2), (x0, 0.78, 0, 0.22, 0.22), (x0, HIP + 0.05, 0, 0.27, 0.26)], 6)
    stack(f"shin.{side}", "stone", [(x0, ANKLE, 0, 0.27, 0.25), (x0, 0.3, 0, 0.2, 0.2), (x0, KNEE + 0.02, 0, 0.21, 0.21)], 6)
    # pé de raiz: base larga e dedos abertos
    stack(f"foot.{side}", "stone", [(x0, 0.2, -0.04, 0.24, 0.22), (x0, 0.08, 0.04, 0.34, 0.3), (x0, 0.05, 0.22, 0.34, 0.3)], 6)
    for dx, dz in ((0.2, 0.4), (0, 0.5), (-0.2, 0.4)):
        H.frustum(f"foot.{side}", "stone_dk", (x0, 0.07, 0.1), (x0 + dx, 0.03, dz), (0.12, 0.07), (0.06, 0.03), sides=4)


def shoulder_pad(s, side):
    c = s * (SH_X - 0.02)
    stack(f"arm.{side}", "stone_lt", [(c + s * 0.12, 1.95, 0.0, 0.44, 0.4), (c + s * 0.12, 2.18, 0.0, 0.42, 0.38)], 8)
    stack(f"arm.{side}", "moss", [(c + s * 0.12, 2.18, 0.0, 0.42, 0.38), (c + s * 0.1, 2.42, 0.0, 0.32, 0.3), (c + s * 0.06, 2.6, 0.0, 0.12, 0.12)], 8)
    H.frustum(f"arm.{side}", "stone_lt", (s * 0.34, 2.0, 0.0), (s * 0.4, 2.62, 0.0), (0.1, 0.32), (0.06, 0.24), sides=4)   # placa alta interna


def arm(s, side):
    px, ex, gx = s * SH_X, s * EL_X, s * WR_X
    stack(f"arm.{side}", "stone", [(px, 1.95, 0, 0.26, 0.26), (s * 0.76, 1.75, 0, 0.29, 0.28), (ex, EL_Y + 0.04, 0, 0.25, 0.25)], 6)
    stack(f"forearm.{side}", "stone_dk", [(ex, EL_Y + 0.02, 0, 0.25, 0.25), (gx, 1.2, 0.02, 0.3, 0.28), (gx, WR_Y + 0.02, 0.04, 0.27, 0.26)], 6)
    stack(f"forearm.{side}", "stone_lt", [(gx, WR_Y + 0.02, 0.04, 0.27, 0.26), (gx, 0.76, 0.08, 0.32, 0.3), (gx, 0.54, 0.1, 0.26, 0.24)], 6)
    H.box(f"forearm.{side}", "stone_dk", (gx, 0.72, 0.36), (0.36, 0.2, 0.1))                          # nós dos dedos


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        arm(s, side)
        shoulder_pad(s, side)


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * WR_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


if __name__ == "__main__":
    H.build("e00F", "biped", PALETTE, make, joints())
