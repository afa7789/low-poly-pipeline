"""Ancient Wandigoo (n013): medido em artifacts/model-sheets/refs/n013/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n013.py -- <out.glb>

Gorila branco curvado, bracos enormes com punhos roxos e garras, crista cinza nas costas, rabo-cabo com gancho.
A prancha nao desenha arma: o golpe e de punho (antebraco + mao grande + garras).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "fur": 0xDCD8F0, "fur_dk": 0xB9B1DA, "purple": 0x6B5B9A, "purple_dk": 0x4E4177, "crest": 0x8E8E9A,
    "crest_dk": 0x6E6E7A, "claw": 0xE6D0A0, "tusk": 0xEBDDB0, "eye": 0xFFA21C, "mouth": 0x2A1030, "cable": 0x6A6A74,
}

SH, EL, WR = (0.86, 2.0, 0.3), (0.98, 1.2, 0.5), (0.92, 0.42, 0.78)
HIP = (0.3, 1.2, -0.15)
KNEE, ANKLE = (0.34, 0.6, 0.05), (0.34, 0.16, -0.12)


def head():
    H.frustum("head", "fur", (0, 1.9, 0.5), (0, 2.12, 0.8), (0.3, 0.3), (0.26, 0.26), sides=8)               # cranio
    H.frustum("head", "purple", (0, 1.9, 0.72), (0, 1.9, 1.08), (0.24, 0.22), (0.2, 0.16), sides=8)          # face
    H.frustum("head", "purple_dk", (0, 1.62, 0.7), (0, 1.74, 1.08), (0.2, 0.16), (0.2, 0.15), sides=6)       # mandibula
    H.box("head", "mouth", (0, 1.78, 1.1), (0.26, 0.1, 0.05))
    H.frustum("head", "fur", (0, 2.05, 0.55), (0, 2.28, 0.8), (0.16, 0.3), (0.06, 0.1), sides=6)             # testa alta
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.12, 2.04, 1.0), (0.1, 0.05, 0.05))
        H.frustum("head", "tusk", (s * 0.15, 1.74, 1.04), (s * 0.15, 1.58, 1.2), (0.05, 0.05), (0.01, 0.01), sides=4)
        H.frustum("head", "purple", (s * 0.3, 1.95, 0.45), (s * 0.36, 2.0, 0.45), (0.07, 0.07), (0.05, 0.05), sides=6)


def crest():
    # espinhos cinza grossos: o maior sobre a nuca (visto de frente acima da cabeca), fileira descendo nas costas
    spikes = [((0, 2.2, 0.3), (0, 2.85, 0.1), 0.26), ((0, 2.2, 0.1), (0, 2.75, -0.35), 0.24), ((0, 2.0, -0.05), (0, 2.45, -0.6), 0.22),
              ((0, 1.8, -0.15), (0, 2.1, -0.7), 0.2), ((0, 1.6, -0.2), (0, 1.75, -0.7), 0.17)]
    for a, b, r in spikes:
        H.frustum("spine", "crest", a, b, (r, r * 0.8), (0.02, 0.02), sides=4)
    H.frustum("spine", "crest_dk", (0, 1.9, 0.1), (0, 2.3, 0.3), (0.2, 0.25), (0.14, 0.2), sides=4)


def torso():
    H.frustum("pelvis", "fur", (0, 1.0, -0.12), (0, 1.5, -0.1), (0.46, 0.4), (0.52, 0.42), sides=8)           # quadril
    H.frustum("spine", "fur", (0, 1.35, -0.1), (0, 1.95, 0.25), (0.5, 0.42), (0.78, 0.55), sides=8)           # peito em V
    H.frustum("spine", "fur", (0, 1.95, 0.2), (0, 2.3, 0.4), (0.8, 0.55), (0.45, 0.35), sides=8)              # corcova dos ombros
    H.frustum("spine", "fur_dk", (0, 1.45, 0.05), (0, 1.8, 0.3), (0.34, 0.3), (0.5, 0.2), sides=6)            # barriga
    H.frustum("spine", "eye", (-0.55, 1.5, 0.38), (-0.55, 1.78, 0.38), (0.09, 0.09), (0.09, 0.09), sides=6)   # lanterna
    H.chain("pelvis", "cable", [(0.1, 1.2, -0.4), (0.0, 0.9, -0.6), (0.3, 0.5, -0.55), (0.55, 0.55, -0.5), (0.6, 0.3, -0.5)],
            [(0.03, 0.03)] * 5, sides=4)
    H.frustum("pelvis", "cable", (0.6, 0.4, -0.5), (0.45, 0.25, -0.5), (0.03, 0.03), (0.02, 0.02), sides=4)


def arm(s, side):
    a, f = f"arm.{side}", f"forearm.{side}"
    H.frustum(a, "fur", (s * 0.7, 2.05, 0.3), (s * 0.97, 1.8, 0.35), (0.34, 0.34), (0.3, 0.3), sides=8)       # ombro/deltoide
    H.frustum(a, "fur", (s * SH[0], 1.95, SH[2]), (s * EL[0], EL[1] + 0.05, EL[2]), (0.32, 0.3), (0.26, 0.25), sides=8)
    H.frustum(f, "fur", (s * EL[0], EL[1] + 0.05, EL[2]), (s * 0.94, 0.7, 0.68), (0.28, 0.27), (0.32, 0.3), sides=8)
    H.frustum(f, "purple", (s * 0.94, 0.72, 0.66), (s * WR[0], 0.3, WR[2]), (0.4, 0.34), (0.36, 0.3), sides=6)   # punho roxo
    H.frustum(f, "purple_dk", (s * WR[0], 0.34, WR[2]), (s * WR[0], 0.18, WR[2] + 0.06), (0.32, 0.26), (0.3, 0.2), sides=6)
    for dx in (-0.2, -0.07, 0.07, 0.2):
        H.frustum(f, "claw", (s * (WR[0] + dx), 0.22, WR[2] + 0.12), (s * (WR[0] + dx * 1.2), -0.02, WR[2] + 0.34), (0.085, 0.085), (0.012, 0.012), sides=4)


def leg(s, side):
    H.frustum(f"thigh.{side}", "fur", (s * KNEE[0], KNEE[1] - 0.05, KNEE[2]), (s * HIP[0], HIP[1] + 0.05, HIP[2]), (0.26, 0.28), (0.34, 0.36), sides=6)
    H.frustum(f"shin.{side}", "fur", (s * ANKLE[0], 0.3, ANKLE[2]), (s * KNEE[0], KNEE[1] + 0.03, KNEE[2]), (0.24, 0.24), (0.27, 0.27), sides=6)
    H.frustum(f"shin.{side}", "purple", (s * ANKLE[0], 0.1, ANKLE[2]), (s * ANKLE[0], 0.4, ANKLE[2]), (0.26, 0.26), (0.3, 0.3), sides=6)
    H.frustum(f"foot.{side}", "purple", (s * ANKLE[0], 0.12, -0.2), (s * ANKLE[0], 0.1, 0.3), (0.28, 0.26), (0.26, 0.14), sides=6)
    H.frustum(f"foot.{side}", "purple_dk", (s * ANKLE[0], 0.02, -0.25), (s * ANKLE[0], 0.02, 0.42), (0.28, 0.02), (0.26, 0.02), sides=4)


def make():
    head()
    crest()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        arm(s, side)
        leg(s, side)


def joints():
    out = {"pelvis": ((0, 1.2, -0.12), (0, 1.4, -0.1)), "spine": ((0, 1.4, -0.1), (0, 2.1, 0.3)),
           "head": ((0, 2.0, 0.45), (0, 2.2, 0.9))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH[0], SH[1], SH[2]), (s * EL[0], EL[1], EL[2]))
        out[f"forearm.{side}"] = ((s * EL[0], EL[1], EL[2]), (s * WR[0], WR[1], WR[2]))
        out[f"thigh.{side}"] = ((s * HIP[0], HIP[1], HIP[2]), (s * KNEE[0], KNEE[1], KNEE[2]))
        out[f"shin.{side}"] = ((s * KNEE[0], KNEE[1], KNEE[2]), (s * ANKLE[0], ANKLE[1], ANKLE[2]))
        out[f"foot.{side}"] = ((s * ANKLE[0], ANKLE[1], ANKLE[2]), (s * ANKLE[0], 0.06, 0.4))
    return out


H.build("n013", "biped", PALETTE, make, joints())
