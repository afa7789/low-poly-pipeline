"""Incubus (h04I, familia harpy): medido em artifacts/model-sheets/refs/h04I/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/h04I.py -- <out.glb>

Demonio roxo de mascara e chifres, capa nas costas. As "asas" da prancha sao laminas em crescente que pendem dos
ombros e varrem para a frente: braco de asa em frusta nos ossos upper/lower, ponta em gancho no lower.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "skin": 0x5E5490, "skin_dk": 0x453A74, "skin_lt": 0x6C629E, "mask": 0x7A6B38, "mask_dk": 0x5A4F2A,
    "horn": 0x1B1C1A, "cloak": 0x524C2E, "fur": 0x34301F, "wing": 0x6A5E32, "wing_dk": 0x4C4426,
    "gem": 0x50F040, "eye": 0x111111, "cord": 0x161616,
}

# metros do biped; 0,0034 m por pixel na frente e no perfil da prancha
LEG_X, HIP, KNEE, ANKLE = 0.24, 1.18, 0.58, 0.14
WAIST, NECK, TOP = 1.4, 2.16, 2.72
SH = (0.5, 2.05, 0.0)
EL = (0.8, 1.76, 0.04)
HAND = (1.04, 1.48, 0.06)
# braco de asa: ombro (costas) -> cotovelo, depois o gancho que varre para a frente
W_SH, W_EL, W_TIP = (0.86, 1.66, -0.12), (0.7, 1.15, 0.06), (1.22, 0.86, 0.6)


def mx(p, s):
    return (p[0] * s, p[1], p[2])


def head():
    H.frustum("head", "skin", (0, 2.18, 0.0), (0, 2.5, 0.04), (0.2, 0.21), (0.21, 0.21), sides=8)
    H.frustum("head", "skin", (0, 2.5, 0.04), (0, 2.68, 0.02), (0.21, 0.21), (0.16, 0.17), sides=8)
    H.frustum("head", "mask", (0, 2.24, 0.2), (0, 2.5, 0.2), (0.07, 0.07), (0.19, 0.08), sides=6)   # queixo da mascara
    H.frustum("head", "mask", (0, 2.5, 0.2), (0, 2.74, 0.12), (0.19, 0.08), (0.14, 0.07), sides=6)
    H.frustum("head", "mask_dk", (0, 2.3, 0.26), (0, 2.5, 0.27), (0.03, 0.03), (0.04, 0.03), sides=4)  # nariz
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.1, 2.52, 0.27), (0.1, 0.04, 0.03))
        H.frustum("head", "skin", (s * 0.18, 2.5, 0.0), (s * 0.4, 2.62, -0.02), (0.07, 0.05), (0.01, 0.01), sides=4)   # orelha
        horn = [(0.14, 2.68, 0.0), (0.36, 2.88, -0.08), (0.3, 3.04, -0.16), (0.18, 3.18, -0.25)]
        H.chain("head", "horn", [mx(p, s) for p in horn], [(0.1, 0.1), (0.085, 0.09), (0.06, 0.07), (0.008, 0.01)], sides=6)


def torso():
    H.frustum("pelvis", "skin_dk", (0, 0.98, 0.0), (0, 1.3, 0.0), (0.33, 0.23), (0.3, 0.22), sides=8)
    H.frustum("pelvis", "skin", (0, 1.3, 0.0), (0, 1.52, 0.0), (0.3, 0.22), (0.31, 0.22), sides=8)
    H.frustum("spine", "skin", (0, 1.5, 0.0), (0, 1.82, 0.02), (0.31, 0.22), (0.42, 0.26), sides=8)
    H.frustum("spine", "skin", (0, 1.8, 0.02), (0, 2.1, 0.03), (0.42, 0.26), (0.5, 0.27), sides=8)
    H.frustum("spine", "skin_lt", (0, 2.08, 0.03), (0, 2.24, 0.04), (0.5, 0.26), (0.2, 0.2), sides=8)    # trapezios
    H.frustum("spine", "fur", (0, 2.1, 0.0), (0, 2.34, 0.04), (0.38, 0.32), (0.22, 0.2), sides=8)       # gola de pele
    H.frustum("spine", "skin_lt", (0, 1.78, 0.2), (0, 1.9, 0.22), (0.3, 0.06), (0.36, 0.06), sides=4)    # peito
    H.box("spine", "gem", (0, 1.9, 0.27), (0.1, 0.14, 0.05))
    cape = [(-0.4, 2.2, -0.2), (0.4, 2.2, -0.2), (0.52, 0.5, -0.46), (0.3, 0.46, -0.46), (0.0, 0.56, -0.46),
            (-0.3, 0.46, -0.46), (-0.52, 0.5, -0.46)]
    H.panel("spine", "cloak", [(x, y, -0.2 - (2.2 - y) * 0.153) for x, y, _ in cape], 0.05)
    for s in (-1, 1):   # abas da capa dos dois lados da frente
        H.panel("spine", "cloak", [(s * 0.34, 1.98, 0.0), (s * 0.48, 1.9, 0.0), (s * 0.5, 0.5, -0.46), (s * 0.4, 0.55, -0.3)], 0.04)


def legs(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "skin", (x, KNEE - 0.02, 0.02), (x, HIP + 0.06, 0.0), (0.15, 0.16), (0.2, 0.2), sides=6)
    H.frustum(f"shin.{side}", "skin_dk", (x, 0.42, 0.0), (x, KNEE + 0.04, 0.02), (0.17, 0.16), (0.16, 0.16), sides=6)
    H.frustum(f"shin.{side}", "skin_dk", (x, ANKLE, 0.0), (x, 0.44, 0.0), (0.12, 0.12), (0.18, 0.17), sides=6)
    H.frustum(f"foot.{side}", "skin_dk", (x, 0.12, -0.1), (x, 0.06, 0.34), (0.15, 0.1), (0.13, 0.05), sides=4)
    H.frustum(f"foot.{side}", "skin", (x, 0.04, -0.12), (x, 0.03, 0.36), (0.15, 0.03), (0.13, 0.03), sides=4)


def arms(s, side):
    sh, el = mx(SH, s), mx(EL, s)
    H.frustum(f"arm.{side}", "skin", (sh[0], sh[1] + 0.12, 0.0), mx((0.64, 1.9, 0.02), s), (0.2, 0.2), (0.2, 0.2), sides=6)    # deltoide
    H.frustum(f"arm.{side}", "skin", mx((0.64, 1.9, 0.02), s), el, (0.2, 0.2), (0.14, 0.14), sides=6)
    H.frustum(f"forearm.{side}", "skin", (el[0], el[1] + 0.03, el[2]), mx((0.96, 1.54, 0.05), s), (0.15, 0.15), (0.11, 0.11), sides=6)
    H.frustum(f"forearm.{side}", "skin_lt", mx((0.94, 1.56, 0.05), s), mx((1.12, 1.4, 0.07), s), (0.1, 0.08), (0.17, 0.06), sides=6)  # mao aberta
    H.frustum(f"forearm.{side}", "skin_lt", mx((1.1, 1.42, 0.07), s), mx((1.2, 1.34, 0.12), s), (0.14, 0.05), (0.06, 0.03), sides=4)


def wing(s, n):
    up, low = f"wing{n}.upper", f"wing{n}.lower"
    sh, el, tip = mx(W_SH, s), mx(W_EL, s), mx(W_TIP, s)
    H.frustum(up, "wing_dk", (sh[0], sh[1] + 0.1, sh[2]), el, (0.13, 0.09), (0.12, 0.08), sides=6)     # ombro da asa
    # laminas: crescente grosso, mais largo no cotovelo, afinando no gancho
    pts = [el, mx((0.66, 1.0, 0.12), s), mx((0.74, 0.88, 0.3), s), mx((1.0, 0.82, 0.46), s), tip]
    H.chain(low, "wing", pts, [(0.12, 0.08), (0.17, 0.1), (0.16, 0.11), (0.1, 0.08), (0.01, 0.01)], sides=6)
    H.frustum(low, "wing_dk", mx((0.8, 0.86, 0.34), s), mx((0.6, 0.7, 0.5), s), (0.06, 0.06), (0.01, 0.01), sides=4)   # espora
    H.frustum(up, "wing", (sh[0], sh[1] + 0.02, sh[2]), mx((1.0, 1.9, -0.2), s), (0.06, 0.06), (0.01, 0.01), sides=4)   # ponta de cima
    H.frustum(up, "wing", mx((0.78, 1.4, -0.03), s), mx((0.98, 1.34, 0.15), s), (0.05, 0.05), (0.01, 0.01), sides=4)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        legs(s, side)
        arms(s, side)
    wing(1, 1)
    wing(-1, 2)


def joints():
    out = {}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = (mx(SH, s), mx(EL, s))
        out[f"forearm.{side}"] = (mx(EL, s), mx(HAND, s))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    for s, n in ((1, 1), (-1, 2)):
        out[f"wing{n}.upper"] = (mx(W_SH, s), mx(W_EL, s))
        out[f"wing{n}.lower"] = (mx(W_EL, s), mx(W_TIP, s))
    return out


H.build("h04I", "harpy", PALETTE, make, joints())
