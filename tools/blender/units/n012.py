"""Wandigoo (n012): iéti-gorila branco, corcunda, braços compridos com garras, mochila de toras e lanterna.

    blender -b --factory-startup -P tools/blender/units/n012.py -- <out.glb>

Medido em artifacts/model-sheets/refs/n012/sheet.jpg (~335 px por metro). A prancha não desenha arma:
o golpe é de punho e garra (antebraço com punho roxo grande + 4 garras por mão).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "white": 0xE6E4F0, "white_dk": 0xC4C0D6, "purple": 0x6A5A8A, "fur": 0x78695A, "claw": 0xEADCB8,
    "orange": 0xF2A030, "steel": 0x7A7A82, "wood": 0x8A7A66, "rope": 0x4A3A30, "mouth": 0x3A1020,
    "lamp": 0x3A2E2A, "pink": 0xD25068,
}

HIP, KNEE, ANK = (0.3, 1.0, -0.1), (0.38, 0.5, 0.15), (0.4, 0.1, -0.1)
SH, EL, WR = (0.65, 1.55, 0.2), (0.8, 0.95, 0.15), (0.78, 0.3, 0.3)


def head():
    H.frustum("head", "white", (0, 1.88, 0.15), (0, 1.55, 0.6), (0.3, 0.28), (0.27, 0.25), sides=8)       # crânio
    H.frustum("head", "purple", (0, 1.62, 0.5), (0, 1.46, 0.95), (0.2, 0.17), (0.17, 0.14), sides=8)      # focinho
    H.frustum("head", "mouth", (0, 1.52, 0.78), (0, 1.36, 0.82), (0.14, 0.04), (0.14, 0.04), sides=4)     # boca aberta
    H.frustum("head", "purple", (0, 1.4, 0.55), (0, 1.3, 0.85), (0.14, 0.12), (0.12, 0.1), sides=6)       # queixo
    for s in (-1, 1):
        H.box("head", "orange", (s * 0.12, 1.72, 0.76), (0.07, 0.05, 0.05))
        H.frustum("head", "claw", (s * 0.07, 1.5, 0.92), (s * 0.07, 1.36, 0.95), (0.03, 0.03), (0.005, 0.005), sides=4)


def torso():
    H.frustum("pelvis", "white", (0, 0.92, -0.1), (0, 1.38, 0.0), (0.4, 0.32), (0.34, 0.3), sides=8)
    H.frustum("spine", "white", (0, 1.3, 0.0), (0, 1.72, 0.05), (0.36, 0.3), (0.66, 0.44), sides=8)     # tronco em V
    H.frustum("spine", "white", (0, 1.72, 0.05), (0, 2.05, -0.05), (0.66, 0.44), (0.52, 0.38), sides=8)  # ombros
    H.frustum("spine", "white_dk", (0, 2.0, -0.05), (0, 2.38, -0.12), (0.46, 0.34), (0.04, 0.06), sides=6)   # corcunda
    H.frustum("spine", "white", (0, 1.9, 0.15), (0, 1.7, 0.4), (0.3, 0.22), (0.3, 0.22), sides=8)         # pescoço grosso
    # mochila: toras, chave inglesa e gancho
    H.box("spine", "wood", (0, 1.75, -0.52), (0.55, 0.28, 0.22))
    H.box("spine", "wood", (0.05, 1.55, -0.55), (0.5, 0.26, 0.22))
    H.frustum("spine", "rope", (-0.28, 1.65, -0.55), (0.28, 1.65, -0.55), (0.14, 0.15), (0.14, 0.15), sides=4)
    H.chain("spine", "steel", [(-0.3, 2.0, -0.4), (-0.1, 1.8, -0.55), (0.3, 1.45, -0.62)],
            [(0.05, 0.04), (0.05, 0.04), (0.05, 0.04)], sides=4)
    H.frustum("spine", "steel", (-0.45, 2.1, -0.38), (-0.3, 2.0, -0.4), (0.1, 0.05), (0.06, 0.05), sides=4)
    H.chain("spine", "steel", [(0.15, 2.0, -0.42), (0.25, 2.1, -0.42), (0.32, 1.95, -0.42)],
            [(0.04, 0.04)] * 3, sides=4)
    # lanterna pendurada no quadril direito, presa por uma alça ao quadril
    H.frustum("pelvis", "lamp", (-0.38, 1.0, -0.2), (-0.4, 0.84, -0.34), (0.04, 0.04), (0.04, 0.04), sides=4)
    H.frustum("pelvis", "orange", (-0.42, 0.5, -0.36), (-0.42, 0.84, -0.36), (0.12, 0.12), (0.14, 0.14), sides=6)
    H.frustum("pelvis", "lamp", (-0.42, 0.44, -0.36), (-0.42, 0.5, -0.36), (0.15, 0.15), (0.15, 0.15), sides=6)


def arm(s, side):
    a, f = f"arm.{side}", f"forearm.{side}"
    H.frustum(a, "white", (s * 0.5, 1.72, 0.12), (s * 0.7, 1.45, 0.16), (0.3, 0.28), (0.32, 0.3), sides=8)     # ombro
    H.frustum(a, "white", (s * SH[0], SH[1], SH[2]), (s * EL[0], EL[1], EL[2]), (0.3, 0.28), (0.21, 0.2), sides=8)
    H.frustum(f, "white", (s * EL[0], EL[1] + 0.05, EL[2]), (s * 0.79, 0.75, 0.2), (0.21, 0.2), (0.24, 0.23), sides=8)
    H.frustum(f, "fur", (s * 0.79, 0.8, 0.2), (s * 0.78, 0.28, 0.3), (0.27, 0.25), (0.22, 0.21), sides=6)    # braçadeira de pelo
    H.frustum(f, "purple", (s * WR[0], 0.34, 0.3), (s * WR[0], 0.08, 0.36), (0.22, 0.2), (0.17, 0.14), sides=6)   # punho
    for dx in (-0.1, -0.035, 0.035, 0.1):
        H.frustum(f, "claw", (s * (WR[0] + dx), 0.16, 0.4), (s * (WR[0] + dx * 1.5), -0.12, 0.52), (0.035, 0.035), (0.005, 0.005), sides=4)


def leg(s, side):
    h, k, an = (s * HIP[0], HIP[1], HIP[2]), (s * KNEE[0], KNEE[1], KNEE[2]), (s * ANK[0], ANK[1], ANK[2])
    H.frustum(f"thigh.{side}", "white", k, (h[0], h[1] + 0.08, h[2]), (0.2, 0.19), (0.27, 0.25), sides=6)
    H.frustum(f"shin.{side}", "white", an, (k[0], k[1] + 0.08, k[2]), (0.16, 0.15), (0.21, 0.2), sides=6)
    H.frustum(f"foot.{side}", "purple", (an[0], 0.1, -0.2), (an[0], 0.07, 0.38), (0.2, 0.16), (0.16, 0.08), sides=6)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        arm(s, side)
        leg(s, side)


def joints():
    out = {"pelvis": ((0, 1.0, -0.1), (0, 1.35, 0)), "spine": ((0, 1.35, 0), (0, 1.95, 0.2)),
           "head": ((0, 1.8, 0.3), (0, 1.55, 0.85))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH[0], SH[1], SH[2]), (s * EL[0], EL[1], EL[2]))
        out[f"forearm.{side}"] = ((s * EL[0], EL[1], EL[2]), (s * WR[0], WR[1], WR[2]))
        out[f"thigh.{side}"] = ((s * HIP[0], HIP[1], HIP[2]), (s * KNEE[0], KNEE[1], KNEE[2]))
        out[f"shin.{side}"] = ((s * KNEE[0], KNEE[1], KNEE[2]), (s * ANK[0], ANK[1], ANK[2]))
        out[f"foot.{side}"] = ((s * ANK[0], ANK[1], ANK[2]), (s * ANK[0], 0.06, 0.4))
    return out


H.build("n012", "biped", PALETTE, make, joints())
