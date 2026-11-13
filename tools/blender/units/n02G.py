"""Forest Troll Trapper (n02G): medido em artifacts/model-sheets/refs/n02G/sheet.jpg (~405 px por metro).

    blender -b --factory-startup -P tools/blender/units/n02G.py -- <out.glb>

Troll magro e alto: mascara de bico de passaro, capuz, capa preta, lanca nas costas (osso spine), corda
laranja enrolada no antebraco direito (a mao que joga), bomba e cranio no cinto. Sem arma na mao.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "green": 0x5A8466, "green_dk": 0x486C54, "black": 0x1A1618, "rust": 0x8A3A22, "bone": 0xD8CCA8, "rope": 0xE8561A,
    "wood": 0x6B3A22, "iron": 0x6A6468, "belt": 0x7A4A2A, "bomb": 0x4A4040, "flame": 0xFF7A20, "dark": 0x1E1C1E,
}
SH, EL, WR = (0.5, 2.0, 0.0), (0.56, 1.4, 0.03), (0.55, 0.88, 0.06)


def head():
    H.frustum("head", "green", (0, 2.3, 0.1), (0, 2.62, 0.08), (0.2, 0.22), (0.17, 0.2), sides=8)
    H.frustum("head", "rust", (0, 2.5, 0.02), (0, 2.78, 0.0), (0.26, 0.27), (0.22, 0.23), sides=8)         # capuz
    H.frustum("head", "bone", (0, 2.62, 0.24), (0, 2.42, 0.28), (0.14, 0.04), (0.1, 0.04), sides=4)         # mascara
    H.chain("head", "bone", [(0, 2.56, 0.28), (0, 2.5, 0.45), (0, 2.43, 0.66)], [(0.07, 0.07), (0.05, 0.05), (0.008, 0.008)], sides=4)
    H.box("head", "dark", (0, 2.5, 0.3), (0.2, 0.04, 0.03))
    H.frustum("head", "bone", (0, 2.35, 0.26), (0, 2.3, 0.3), (0.05, 0.03), (0.02, 0.02), sides=4)           # presas
    for s in (-1, 1):
        H.frustum("head", "green", (s * 0.15, 2.52, 0.0), (s * 0.45, 2.7, -0.02), (0.07, 0.03), (0.01, 0.01), sides=4)
        H.frustum("head", "bone", (s * 0.07, 2.32, 0.28), (s * 0.07, 2.25, 0.3), (0.025, 0.02), (0.005, 0.005), sides=4)
    H.frustum("head", "rust", (0, 2.0, 0.0), (0, 2.3, 0.04), (0.3, 0.25), (0.17, 0.17), sides=8)           # cachecol


def cape():
    H.frustum("spine", "black", (0, 1.6, -0.05), (0, 2.1, -0.02), (0.6, 0.34), (0.32, 0.24), sides=8)     # ombros
    H.frustum("spine", "black", (0, 1.9, -0.05), (0, 2.12, -0.02), (0.6, 0.3), (0.5, 0.28), sides=8)
    H.panel("spine", "black", [(0.58, 1.95, -0.22), (-0.58, 1.95, -0.22), (-0.55, 0.9, -0.4), (0, 0.8, -0.42), (0.55, 0.9, -0.4)], thickness=0.06)
    H.panel("pelvis", "black", [(0.5, 1.2, -0.3), (-0.5, 1.2, -0.3), (-0.5, 0.85, -0.4), (0.5, 0.85, -0.4)], thickness=0.06)


def spear():
    H.chain("spine", "wood", [(0, 0.8, -0.42), (0.2, 1.8, -0.42), (0.38, 2.5, -0.42)], [(0.03, 0.03), (0.035, 0.035), (0.03, 0.03)], sides=6)
    H.chain("spine", "iron", [(0.38, 2.45, -0.42), (0.42, 2.7, -0.42), (0.46, 2.95, -0.42)], [(0.04, 0.03), (0.1, 0.04), (0.01, 0.01)], sides=4)


def torso():
    H.frustum("spine", "green", (0, 1.45, 0.0), (0, 1.95, 0.0), (0.28, 0.2), (0.36, 0.22), sides=8)
    H.frustum("pelvis", "green", (0, 1.1, 0.0), (0, 1.5, 0.0), (0.3, 0.22), (0.27, 0.19), sides=8)
    H.frustum("pelvis", "belt", (0, 1.44, 0.0), (0, 1.56, 0.0), (0.3, 0.22), (0.3, 0.22), sides=8)
    H.box("pelvis", "flame", (0, 1.5, 0.23), (0.1, 0.09, 0.03))
    H.panel("pelvis", "rust", [(0.26, 1.46, 0.2), (-0.26, 1.46, 0.2), (-0.2, 1.1, 0.22), (0.05, 0.95, 0.22)], thickness=0.04)
    H.frustum("pelvis", "bomb", (-0.3, 1.32, 0.22), (-0.3, 1.46, 0.22), (0.11, 0.11), (0.05, 0.05), sides=6)
    H.frustum("pelvis", "flame", (-0.3, 1.46, 0.22), (-0.3, 1.56, 0.22), (0.03, 0.03), (0.005, 0.005), sides=4)
    H.frustum("pelvis", "bone", (0.3, 1.45, 0.22), (0.32, 1.15, 0.24), (0.1, 0.07), (0.07, 0.06), sides=6)  # cranio


def arm(s, side):
    a, f = f"arm.{side}", f"forearm.{side}"
    H.frustum(a, "green", (s * SH[0], 2.02, 0.0), (s * 0.54, 1.7, 0.01), (0.17, 0.17), (0.15, 0.15), sides=8)
    H.frustum(a, "green_dk", (s * 0.54, 1.75, 0.01), (s * EL[0], EL[1], EL[2]), (0.15, 0.15), (0.11, 0.11), sides=8)
    H.frustum(f, "green", (s * EL[0], 1.45, 0.03), (s * WR[0], 1.0, 0.06), (0.12, 0.12), (0.15, 0.14), sides=8)
    H.frustum(f, "green_dk", (s * WR[0], 1.0, 0.06), (s * WR[0], 0.82, 0.08), (0.15, 0.13), (0.13, 0.1), sides=6)
    H.frustum(f, "green", (s * WR[0], 0.85, 0.08), (s * WR[0], 0.6, 0.1), (0.13, 0.1), (0.08, 0.07), sides=6)
    if s < 0:
        for y in (1.32, 1.18, 1.04):
            H.frustum(f, "rope", (s * 0.55, y, 0.05), (s * 0.55, y + 0.07, 0.05), (0.21, 0.21), (0.21, 0.21), sides=8)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        H.frustum(f"thigh.{side}", "green", (s * 0.22, 1.3, 0.0), (s * 0.25, 0.65, 0.02), (0.21, 0.2), (0.15, 0.15), sides=8)
        H.frustum(f"shin.{side}", "green_dk", (s * 0.25, 0.7, 0.02), (s * 0.27, 0.3, 0.0), (0.16, 0.15), (0.11, 0.11), sides=8)
        H.frustum(f"shin.{side}", "green", (s * 0.27, 0.35, 0.0), (s * 0.27, 0.08, 0.0), (0.11, 0.11), (0.14, 0.12), sides=8)
        H.frustum(f"foot.{side}", "green", (s * 0.27, 0.1, -0.12), (s * 0.27, 0.06, 0.5), (0.15, 0.09), (0.16, 0.05), sides=6)


def make():
    head()
    cape()
    spear()
    torso()
    legs()
    for s, side in ((1, "L"), (-1, "R")):
        arm(s, side)


def joints():
    out = {"head": ((0, 2.2, 0.08), (0, 2.72, 0.1))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH[0], SH[1], SH[2]), (s * EL[0], EL[1], EL[2]))
        out[f"forearm.{side}"] = ((s * EL[0], EL[1], EL[2]), (s * WR[0], WR[1], WR[2]))
        out[f"thigh.{side}"] = ((s * 0.22, 1.25, 0), (s * 0.25, 0.65, 0.02))
        out[f"shin.{side}"] = ((s * 0.25, 0.65, 0.02), (s * 0.27, 0.1, 0))
        out[f"foot.{side}"] = ((s * 0.27, 0.1, 0), (s * 0.27, 0.06, 0.5))
    return out


H.build("n02G", "biped", PALETTE, make, joints())
