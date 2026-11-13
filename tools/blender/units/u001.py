"""Banshee (u001): medido em artifacts/model-sheets/refs/u001/sheet.jpg (familia wraith).

    blender -b --factory-startup -P tools/blender/units/u001.py -- <out.glb>

Escala da prancha: 0.0026 m por pixel (figura de ~2.6 m com o chapeu); frente = esquerda no perfil.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "teal": 0x68B0A8, "navy": 0x262C4E, "grey": 0x6E6E7A, "grey_dk": 0x555561, "hair": 0x232A4A,
    "purple": 0x7B35C0, "eye": 0xBDF4FF,
}

ARM_X = 0.45


def dress():
    """Vestido que alarga ate a barra e escorre em degraus ate a gota roxa."""
    H.frustum("base", "teal", (0, 0.2, 0), (0, 0.45, 0), (0.19, 0.19), (0.2, 0.2), sides=8)
    H.frustum("base", "teal", (0, 0.42, 0), (0, 0.68, 0), (0.2, 0.2), (0.33, 0.28), sides=8)
    H.frustum("base", "teal", (0, 0.66, 0), (0, 0.9, 0), (0.33, 0.28), (0.44, 0.35), sides=8)
    H.frustum("base", "teal", (0, 0.88, 0), (0, 1.25, 0), (0.44, 0.34), (0.3, 0.24), sides=8)
    H.frustum("base", "purple", (0, 0.1, 0), (0, 0.27, 0), (0.07, 0.07), (0.19, 0.19), sides=8)
    H.frustum("base", "purple", (0, 0.0, 0), (0, 0.12, 0), (0.02, 0.02), (0.07, 0.07), sides=4)
    H.frustum("base", "navy", (0, 0.58, 0.3), (0, 1.25, 0.28), (0.26, 0.04), (0.2, 0.04), sides=4)    # avental


def bodice():
    H.frustum("spine", "teal", (0, 1.2, 0), (0, 1.6, 0), (0.28, 0.22), (0.3, 0.22), sides=8)
    H.frustum("spine", "teal", (0, 1.55, 0), (0, 2.0, 0), (0.3, 0.22), (0.4, 0.24), sides=8)
    H.frustum("spine", "navy", (0, 1.25, 0.2), (0, 1.95, 0.2), (0.2, 0.04), (0.18, 0.04), sides=4)
    H.frustum("spine", "navy", (0, 1.5, 0), (0, 1.58, 0), (0.32, 0.25), (0.32, 0.25), sides=8)    # cinto
    H.frustum("spine", "navy", (0, 2.0, -0.12), (0, 1.55, -0.22), (0.2, 0.06), (0.14, 0.05), sides=6)  # cabelo


def head():
    H.frustum("head", "teal", (0, 1.9, 0), (0, 2.05, 0), (0.17, 0.15), (0.13, 0.12), sides=8)
    H.frustum("head", "grey", (0, 2.42, 0.02), (0, 1.97, 0.1), (0.23, 0.14), (0.21, 0.1), sides=8)   # veu de ferro
    H.frustum("head", "grey_dk", (0, 2.1, 0.1), (0, 1.98, 0.1), (0.2, 0.09), (0.2, 0.09), sides=6)
    H.frustum("head", "hair", (0, 2.35, -0.12), (0, 1.9, -0.2), (0.22, 0.07), (0.2, 0.06), sides=6)
    H.frustum("head", "hair", (0, 1.9, -0.2), (0, 1.4, -0.24), (0.2, 0.06), (0.03, 0.04), sides=6)
    for s in (-1, 1):
        H.frustum("head", "eye", (s * 0.1, 2.27, 0.15), (s * 0.12, 2.3, 0.17), (0.07, 0.02), (0.05, 0.015), sides=4)
    H.frustum("head", "teal", (0, 2.4, 0.08), (0, 2.46, 0.08), (0.4, 0.52), (0.34, 0.44), sides=8)      # aba
    H.frustum("head", "teal", (0, 2.44, 0.05), (0, 2.5, 0.05), (0.3, 0.34), (0.22, 0.22), sides=8)
    H.frustum("head", "navy", (0, 2.49, 0.0), (0, 2.55, 0.0), (0.22, 0.22), (0.21, 0.21), sides=8)
    H.frustum("head", "teal", (0, 2.54, 0.0), (0, 2.64, 0.0), (0.21, 0.21), (0.16, 0.16), sides=8)


def arms():
    """Manga cheia, cotovelo que sai pro lado, luva cinza que aponta para a frente e abre num punho."""
    for s, side in ((1, "L"), (-1, "R")):
        arm, fore = f"arm.{side}", f"forearm.{side}"
        H.frustum(arm, "teal", (s * 0.36, 2.0, 0), (s * 0.46, 1.9, 0.02), (0.14, 0.14), (0.17, 0.17), sides=8)
        H.frustum(arm, "teal", (s * 0.46, 1.9, 0.02), (s * 0.5, 1.76, 0.06), (0.17, 0.17), (0.14, 0.14), sides=8)
        H.frustum(fore, "teal", (s * 0.48, 1.78, 0.06), (s * 0.4, 1.72, 0.2), (0.14, 0.14), (0.16, 0.16), sides=8)
        H.frustum(fore, "grey", (s * 0.42, 1.72, 0.18), (s * 0.3, 1.66, 0.4), (0.12, 0.12), (0.15, 0.15), sides=8)
        H.frustum(fore, "grey_dk", (s * 0.3, 1.66, 0.38), (s * 0.24, 1.62, 0.56), (0.17, 0.17), (0.13, 0.13), sides=6)
        for k in (-1, 1):   # dedos em garra
            H.frustum(fore, "grey", (s * (0.24 + 0.05 * k), 1.64, 0.52), (s * (0.24 + 0.06 * k), 1.54, 0.64), (0.045, 0.04), (0.02, 0.02), sides=4)


def make():
    dress()
    bodice()
    head()
    arms()


def joints():
    out = {}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * ARM_X, 1.98, 0.02), (s * ARM_X, 1.74, 0.02))
        out[f"forearm.{side}"] = ((s * ARM_X, 1.74, 0.02), (s * ARM_X, 1.3, 0.02))
    return out


H.build("u001", "wraith", PALETTE, make, joints())
