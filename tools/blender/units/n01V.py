"""Lunatic Goblin (n01V): medido em artifacts/model-sheets/refs/n01V/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n01V.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "skin": 0x7F8F45, "skin_dk": 0x66742F, "hat": 0x7C95A8, "hat_dk": 0x62788A, "brown": 0x8A5A2E, "barrel": 0x3B3C42,
    "barrel_dk": 0x2A2B30, "gold": 0x9A6A32, "apron": 0x6A2E2E, "pants": 0x4A4A50, "puttee": 0xB5A57A,
    "boot": 0x4F5058, "cape": 0x2E2D33, "yellow": 0xFFC52E, "flame": 0xFF8A1E, "lens": 0x25252B, "fuse": 0xC8B27A,
    "grey": 0x6A6B72, "tan": 0xD9B26A,
}

HIP, KNEE, ANKLE = 0.52, 0.3, 0.13
WAIST, NECK, TOP = 0.82, 1.5, 2.52
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.5, 1.42, 0.66, 1.0, 0.85
BZ = 0.5        # centro do barril, a frente do corpo


def head():
    H.frustum("head", "skin", (0, 1.45, 0.0), (0, 1.66, 0.02), (0.18, 0.16), (0.26, 0.22), sides=6)
    H.frustum("head", "skin", (0, 1.66, 0.02), (0, 1.88, 0.04), (0.28, 0.24), (0.46, 0.36), sides=8)
    H.frustum("head", "skin", (0, 1.88, 0.04), (0, 2.12, 0.02), (0.46, 0.36), (0.4, 0.33), sides=8)
    H.chain("head", "skin", [(0, 1.92, 0.28), (0, 1.84, 0.46), (0, 1.74, 0.66)], [(0.07, 0.08), (0.06, 0.07), (0.02, 0.03)], sides=4)
    H.box("head", "yellow", (0, 1.7, 0.31), (0.3, 0.1, 0.04))
    for s in (-1, 1):
        H.chain("head", "skin", [(s * 0.34, 2.0, 0.0), (s * 0.6, 2.1, -0.02), (s * 0.88, 2.32, -0.04)],
                [(0.05, 0.17), (0.035, 0.12), (0.01, 0.03)], sides=4)
        H.box("head", "lens", (s * 0.14, 2.17, 0.33), (0.17, 0.13, 0.04))
        H.box("head", "brown", (s * 0.14, 2.17, 0.31), (0.23, 0.19, 0.03))
    H.frustum("head", "hat_dk", (0, 2.1, 0.02), (0, 2.18, 0.02), (0.58, 0.55), (0.42, 0.4), sides=8)      # aba
    H.frustum("head", "brown", (0, 2.17, 0.02), (0, 2.27, 0.02), (0.36, 0.34), (0.34, 0.32), sides=8)     # fita
    H.frustum("head", "hat", (0, 2.27, 0.02), (0, 2.46, 0.02), (0.34, 0.32), (0.27, 0.26), sides=8)
    H.frustum("head", "hat", (0, 2.46, 0.02), (0, 2.54, 0.02), (0.27, 0.26), (0.12, 0.12), sides=8)


def body():
    H.frustum("spine", "apron", (0, 0.5, 0.0), (0, 1.1, 0.0), (0.38, 0.28), (0.44, 0.3), sides=8)
    H.frustum("spine", "skin_dk", (0, 1.1, 0.0), (0, 1.38, 0.0), (0.44, 0.3), (0.5, 0.3), sides=8)
    H.frustum("spine", "skin", (0, 1.38, 0.0), (0, 1.52, 0.0), (0.5, 0.3), (0.28, 0.22), sides=8)
    H.frustum("pelvis", "pants", (0, 0.4, 0.0), (0, 0.85, 0.0), (0.4, 0.28), (0.4, 0.28), sides=8)
    # capa rasgada: placa que abre para tras
    H.panel("spine", "cape", [(-0.3, 1.5, -0.3), (0.3, 1.5, -0.3), (0.58, 0.4, -0.68), (-0.58, 0.4, -0.68)], 0.05)
    # barril de polvora nos bracos, tampa no topo
    H.frustum("spine", "barrel", (0, 0.45, BZ), (0, 0.95, BZ), (0.38, 0.38), (0.47, 0.47), sides=8)
    H.frustum("spine", "barrel", (0, 0.95, BZ), (0, 1.45, BZ), (0.47, 0.47), (0.38, 0.38), sides=8)
    for y in (0.62, 1.28):
        H.frustum("spine", "barrel_dk", (0, y - 0.04, BZ), (0, y + 0.04, BZ), (0.43, 0.43), (0.43, 0.43), sides=8)
    H.frustum("spine", "barrel_dk", (0, 1.43, BZ), (0, 1.5, BZ), (0.34, 0.34), (0.3, 0.3), sides=8)
    H.frustum("spine", "gold", (0, 0.98, BZ + 0.43), (0, 0.98, BZ + 0.5), (0.16, 0.16), (0.14, 0.14), sides=8)
    H.chain("spine", "fuse", [(0.2, 1.5, BZ), (0.22, 1.7, BZ + 0.04), (0.3, 1.86, BZ)], [(0.035, 0.035)] * 3, sides=4)
    H.frustum("spine", "flame", (0.3, 1.86, BZ), (0.3, 2.14, BZ), (0.09, 0.09), (0.01, 0.01), sides=4)
    H.frustum("spine", "yellow", (0.3, 1.88, BZ), (0.3, 2.04, BZ), (0.05, 0.05), (0.01, 0.01), sides=4)


def leg(s, side):
    x = s * 0.3
    H.frustum(f"thigh.{side}", "pants", (x, KNEE - 0.02, 0), (x, HIP + 0.06, 0), (0.17, 0.18), (0.22, 0.22), sides=6)
    H.frustum(f"shin.{side}", "puttee", (x, ANKLE + 0.02, 0), (x, KNEE + 0.02, 0), (0.16, 0.17), (0.21, 0.21), sides=6)
    H.frustum(f"shin.{side}", "tan", (x, 0.24, 0), (x, 0.3, 0), (0.17, 0.18), (0.22, 0.22), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.2, -0.04), (x, 0.06, 0.0), (0.2, 0.2), (0.24, 0.24), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.1, 0.0), (x, 0.08, 0.5), (0.25, 0.2), (0.22, 0.12), sides=6)
    H.frustum(f"foot.{side}", "barrel_dk", (x, 0.02, -0.2), (x, 0.02, 0.52), (0.27, 0.025), (0.23, 0.025), sides=4)


def arm(s, side):
    H.frustum(f"arm.{side}", "skin_dk", (s * SH_X, SH_Y + 0.04, 0), (s * EL_X, EL_Y, 0.04), (0.18, 0.2), (0.15, 0.16), sides=6)
    H.frustum(f"forearm.{side}", "skin", (s * EL_X, EL_Y + 0.03, 0.03), (s * (EL_X - 0.04), WR_Y, 0.38), (0.15, 0.15), (0.14, 0.14), sides=6)
    glove = (s * (EL_X - 0.06), WR_Y, 0.44)
    H.frustum(f"forearm.{side}", "brown", (s * (EL_X - 0.04), WR_Y + 0.02, 0.34), glove, (0.16, 0.16), (0.25, 0.23), sides=6)
    H.frustum(f"forearm.{side}", "brown", glove, (s * (EL_X - 0.12), WR_Y - 0.02, 0.62), (0.25, 0.23), (0.2, 0.15), sides=6)
    hx, hz = s * (EL_X - 0.08), 0.5
    if s < 0:   # detonador na mao direita do goblin
        H.box(f"forearm.{side}", "grey", (hx, WR_Y + 0.18, hz), (0.14, 0.34, 0.1))
        H.frustum(f"forearm.{side}", "grey", (hx - 0.18, WR_Y + 0.38, hz), (hx + 0.18, WR_Y + 0.38, hz), (0.05, 0.05), (0.05, 0.05), sides=4)
    else:       # punhado de palitos de fosforo
        for dx in (-0.05, 0.0, 0.05):
            H.frustum(f"forearm.{side}", "tan", (hx + dx, WR_Y + 0.1, hz), (hx + dx * 1.6, WR_Y + 0.42, hz), (0.025, 0.025), (0.03, 0.03), sides=4)


def make():
    head()
    body()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        arm(s, side)


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * 0.3, HIP, 0), (s * 0.3, KNEE, 0))
        out[f"shin.{side}"] = ((s * 0.3, KNEE, 0), (s * 0.3, ANKLE, 0))
        out[f"foot.{side}"] = ((s * 0.3, ANKLE, 0), (s * 0.3, 0.06, 0.4))
    return out


H.build("n01V", "biped", PALETTE, make, joints())
