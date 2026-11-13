"""Fire Gnoll (n02T): medido em artifacts/model-sheets/refs/n02T/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n02T.py -- <out.glb>

Hiena curvada de capuz e mascara de gas, barril preto nas costas, pa na mao direita (da unidade),
balde na esquerda, forcado em chamas preso as costas (osso spine).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "tunic": 0xCDB98E, "tunic_dk": 0xAE9262, "hood": 0xBFA876, "mask": 0x7A5A44, "ear": 0x8A6B50,
    "pants": 0x8A6C46, "boot": 0x2A2420, "glove": 0x4A2A2A, "sleeve": 0xD0A860, "steel": 0x7A7E86,
    "steel_dk": 0x4E5258, "wood": 0x4A3020, "flame": 0xFF8A1E, "flame_y": 0xFFCE3A, "barrel": 0x222224,
    "band": 0x3C3C40, "mane": 0x8A4E22, "bucket": 0xA29078, "bucket_dk": 0x77664E, "strap": 0x5A3A26, "black": 0x111112,
}

HIP_Y = 0.98
SHOULDER = (0.55, 1.62, 0.08)
ELBOW_L, WRIST_L = (0.68, 1.12, 0.2), (0.66, 0.74, 0.28)
ELBOW_R, WRIST_R = (-0.72, 1.25, 0.05), (-0.74, 0.88, -0.1)


def head():
    H.frustum("head", "hood", (0, 1.7, 0.26), (0, 1.92, 0.66), (0.35, 0.34), (0.28, 0.3), sides=8)
    H.frustum("head", "hood", (0, 1.9, 0.25), (0, 2.1, 0.4), (0.22, 0.2), (0.14, 0.14), sides=8)
    H.frustum("head", "mask", (0, 1.84, 0.6), (0, 1.72, 1.08), (0.16, 0.15), (0.11, 0.1), sides=8)
    H.frustum("head", "steel", (0, 1.72, 1.08), (0, 1.71, 1.21), (0.12, 0.11), (0.12, 0.11), sides=8)
    H.frustum("head", "black", (0, 1.71, 1.21), (0, 1.71, 1.23), (0.07, 0.07), (0.07, 0.07), sides=6)
    for s in (-1, 1):
        H.frustum("head", "steel", (s * 0.13, 1.9, 0.56), (s * 0.13, 1.9, 0.72), (0.11, 0.11), (0.1, 0.1), sides=8)
        H.frustum("head", "flame", (s * 0.13, 1.9, 0.71), (s * 0.13, 1.9, 0.75), (0.08, 0.08), (0.07, 0.07), sides=8)
        H.frustum("head", "ear", (s * 0.19, 2.0, 0.34), (s * 0.24, 2.34, 0.3), (0.1, 0.05), (0.02, 0.015), sides=4)


def torso():
    H.frustum("spine", "tunic", (0, 1.0, -0.05), (0, 1.5, 0.08), (0.36, 0.3), (0.5, 0.36), sides=8)
    H.frustum("spine", "tunic", (0, 1.45, 0.08), (0, 1.85, 0.25), (0.52, 0.37), (0.36, 0.3), sides=8)
    H.frustum("spine", "hood", (0, 1.7, 0.15), (0, 1.95, 0.35), (0.38, 0.3), (0.28, 0.26), sides=8)
    H.frustum("spine", "mane", (0, 1.95, 0.05), (0, 2.18, -0.12), (0.09, 0.06), (0.01, 0.01), sides=4)
    H.frustum("spine", "mane", (0, 1.85, -0.08), (0, 2.0, -0.32), (0.08, 0.06), (0.01, 0.01), sides=4)
    for s in (-1, 1):       # correias do barril
        H.frustum("spine", "strap", (s * 0.3, 1.92, 0.2), (s * 0.3, 1.55, -0.38), (0.07, 0.03), (0.07, 0.03), sides=4)
    H.frustum("pelvis", "tunic_dk", (0, 1.06, 0), (0, 1.14, 0), (0.46, 0.38), (0.44, 0.36), sides=8)    # cinto
    H.frustum("pelvis", "tunic", (0, 0.72, 0), (0, 1.08, 0), (0.42, 0.34), (0.38, 0.32), sides=8)       # saia da tunica
    H.frustum("pelvis", "pants", (0, 0.8, 0), (0, 1.0, 0), (0.4, 0.32), (0.4, 0.32), sides=8)


def pack():
    """Barril preto deitado nas costas e forcado em chamas preso ao lado."""
    H.frustum("spine", "barrel", (-0.5, 1.62, -0.46), (0.5, 1.62, -0.46), (0.3, 0.3), (0.3, 0.3), sides=8)
    for x in (-0.33, 0.33):
        H.frustum("spine", "band", (x - 0.04, 1.62, -0.46), (x + 0.04, 1.62, -0.46), (0.32, 0.32), (0.32, 0.32), sides=8)
    H.frustum("spine", "wood", (0.57, 1.2, -0.5), (0.6, 2.45, -0.45), (0.045, 0.045), (0.04, 0.04), sides=6)
    H.frustum("spine", "steel", (0.6, 2.4, -0.45), (0.6, 2.5, -0.45), (0.12, 0.03), (0.12, 0.03), sides=4)
    for dx in (-0.1, 0.1):
        H.frustum("spine", "steel", (0.6 + dx, 2.48, -0.45), (0.6 + dx * 1.2, 2.78, -0.45), (0.035, 0.035), (0.012, 0.012), sides=4)
        H.frustum("spine", "flame", (0.6 + dx * 1.2, 2.72, -0.45), (0.6 + dx * 1.3, 3.05, -0.45), (0.07, 0.05), (0.01, 0.01), sides=4)
    H.frustum("spine", "flame_y", (0.6, 2.82, -0.45), (0.6, 3.15, -0.45), (0.09, 0.05), (0.01, 0.01), sides=4)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        H.frustum(f"thigh.{side}", "pants", (s * 0.27, 0.52, 0.1), (s * 0.22, 1.02, -0.02), (0.21, 0.21), (0.32, 0.32), sides=6)
        H.frustum(f"shin.{side}", "pants", (s * 0.27, 0.38, 0.07), (s * 0.27, 0.6, 0.1), (0.22, 0.22), (0.2, 0.2), sides=6)
        H.frustum(f"shin.{side}", "boot", (s * 0.28, 0.1, -0.05), (s * 0.27, 0.46, 0.08), (0.18, 0.19), (0.25, 0.25), sides=6)
        H.frustum(f"foot.{side}", "boot", (s * 0.28, 0.1, -0.12), (s * 0.28, 0.1, 0.1), (0.17, 0.12), (0.17, 0.1), sides=6)
        H.frustum(f"foot.{side}", "mask", (s * 0.28, 0.1, 0.05), (s * 0.28, 0.07, 0.55), (0.17, 0.1), (0.13, 0.06), sides=6)


def arms():
    for s, side, el, wr in ((1, "L", ELBOW_L, WRIST_L), (-1, "R", ELBOW_R, WRIST_R)):
        sh = (s * SHOULDER[0], SHOULDER[1], SHOULDER[2])
        H.frustum(f"arm.{side}", "sleeve", (s * 0.5, 1.7, 0.05), (s * 0.62, 1.4, 0.1), (0.24, 0.24), (0.24, 0.24), sides=8)     # ombro
        H.frustum(f"arm.{side}", "sleeve", sh, el, (0.24, 0.23), (0.19, 0.19), sides=8)
        H.frustum(f"forearm.{side}", "glove", (el[0], el[1] + 0.06, el[2]), wr, (0.21, 0.21), (0.16, 0.16), sides=6)
        H.frustum(f"forearm.{side}", "glove", wr, (wr[0], wr[1] - 0.2, wr[2]), (0.19, 0.19), (0.14, 0.14), sides=6)       # punho


def bucket():
    H.frustum("forearm.L", "bucket", (0.66, 0.08, 0.28), (0.66, 0.46, 0.28), (0.2, 0.2), (0.17, 0.17), sides=8)
    H.frustum("forearm.L", "bucket_dk", (0.66, 0.44, 0.28), (0.66, 0.5, 0.28), (0.18, 0.18), (0.18, 0.18), sides=8)
    H.frustum("forearm.L", "steel_dk", (0.66, 0.5, 0.28), (0.66, 0.66, 0.28), (0.1, 0.025), (0.08, 0.025), sides=4)


def shovel():
    """Pa em pe, inclinada a frente como no perfil; cabo e lamina na pegada do antebraco direito."""
    def at(y):
        return -0.4 + (y - 0.05) * 0.263
    H.frustum("forearm.R", "wood", (-0.74, 0.05, at(0.05)), (-0.74, 2.3, at(2.3)), (0.055, 0.055), (0.045, 0.045), sides=6)
    pts = [(-0.74 - 0.25, 2.92, at(2.92)), (-0.74 + 0.25, 2.92, at(2.92)), (-0.74 + 0.25, 2.62, at(2.62)), (-0.74, 2.15, at(2.15)), (-0.74 - 0.25, 2.62, at(2.62))]
    H.panel("forearm.R", "steel", pts, thickness=0.06)
    H.frustum("forearm.R", "steel_dk", (-0.74, 2.2, at(2.2)), (-0.74, 2.8, at(2.8)), (0.05, 0.05), (0.03, 0.05), sides=4)


def make():
    head()
    torso()
    pack()
    legs()
    arms()
    bucket()
    shovel()


def joints():
    out = {"pelvis": ((0, HIP_Y, 0), (0, 1.15, 0)), "spine": ((0, 1.15, -0.05), (0, 1.8, 0.2)),
           "head": ((0, 1.75, 0.3), (0, 1.9, 0.75))}
    for s, side, el, wr in ((1, "L", ELBOW_L, WRIST_L), (-1, "R", ELBOW_R, WRIST_R)):
        out[f"arm.{side}"] = ((s * SHOULDER[0], SHOULDER[1], SHOULDER[2]), el)
        out[f"forearm.{side}"] = (el, wr)
        out[f"thigh.{side}"] = ((s * 0.22, HIP_Y, -0.02), (s * 0.27, 0.52, 0.1))
        out[f"shin.{side}"] = ((s * 0.27, 0.52, 0.1), (s * 0.28, 0.17, -0.05))
        out[f"foot.{side}"] = ((s * 0.28, 0.17, -0.05), (s * 0.28, 0.07, 0.5))
    return out


H.build("n02T", "biped", PALETTE, make, joints())
