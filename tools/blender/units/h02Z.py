"""Elemental Of Fire (h02Z): medido em artifacts/model-sheets/refs/h02Z/sheet.jpg (familia wraith).

    blender -b --factory-startup -P tools/blender/units/h02Z.py -- <out.glb>

Escala da prancha: 0.0032 m por pixel (figura de ~2.7 m com a chama); frente = direita no perfil.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "lava": 0xFF7A12, "lava_dk": 0xC93A1E, "pool": 0x9E1F3A, "glow": 0xFFD36B, "flame": 0xFFA21F,
    "rock": 0x45354A, "face": 0x3A2D3F, "eye": 0xFFF0A8,
}

SH_X = 0.78
ARM_Z, FORE_Z = 0.1, 0.18


def pool():
    """Poca de lava no chao e os respingos soltos."""
    H.frustum("root", "pool", (0, 0.0, 0), (0, 0.05, 0), (1.05, 0.8), (1.0, 0.76), sides=12)
    H.frustum("root", "lava_dk", (0, 0.05, 0), (0, 0.09, 0), (0.92, 0.68), (0.85, 0.62), sides=12)
    for x, z in ((-0.7, 0.75), (0.8, 0.7), (0.1, -0.85)):
        H.frustum("root", "lava", (x, 0.0, z), (x, 0.05, z), (0.16, 0.1), (0.14, 0.09), sides=6)


def skirt():
    """Manto que escorre: alarga no chao, estreita na cintura, enche no peito."""
    H.frustum("base", "lava", (0, 0.05, -0.04), (0, 0.5, -0.02), (0.8, 0.56), (0.58, 0.46), sides=8)
    H.frustum("base", "lava", (0, 0.1, 0.0), (0, 0.55, 0.02), (0.68, 0.48), (0.52, 0.42), sides=8)
    H.frustum("base", "lava", (0, 0.5, 0.0), (0, 0.95, -0.02), (0.52, 0.42), (0.46, 0.4), sides=8)
    H.frustum("base", "lava", (0, 0.9, -0.02), (0, 1.3, -0.04), (0.46, 0.4), (0.5, 0.42), sides=8)
    for s in (-1, 1):       # gotas escorrendo na frente
        H.frustum("base", "glow", (s * 0.3, 0.8, 0.4), (s * 0.3, 0.38, 0.46), (0.05, 0.03), (0.1, 0.04), sides=4)
    H.frustum("base", "glow", (0, 0.9, -0.46), (0, 0.3, -0.5), (0.06, 0.03), (0.2, 0.04), sides=4)


def chest():
    H.frustum("spine", "lava", (0, 1.25, -0.04), (0, 1.62, -0.04), (0.5, 0.42), (0.78, 0.46), sides=8)
    H.frustum("spine", "lava", (0, 1.6, -0.04), (0, 1.84, -0.04), (0.78, 0.46), (0.74, 0.4), sides=8)
    H.frustum("spine", "lava_dk", (0, 1.62, 0.2), (0, 1.8, 0.2), (0.62, 0.3), (0.6, 0.26), sides=6)
    for s in (-1, 1):       # ombros de rocha
        H.frustum("spine", "rock", (s * 0.78, 1.82, -0.02), (s * 0.82, 1.98, -0.02), (0.26, 0.2), (0.16, 0.12), sides=6)
    for x, y in ((0.28, 1.5), (-0.06, 1.2), (-0.3, 1.0)):   # pedras no peito
        H.frustum("spine", "rock", (x, y, 0.36), (x * 1.1, y + 0.1, 0.44), (0.1, 0.08), (0.07, 0.06), sides=6)
    H.frustum("spine", "glow", (0, 1.3, -0.42), (0, 1.85, -0.38), (0.12, 0.1), (0.2, 0.12), sides=6)


def head():
    H.frustum("head", "lava", (0, 1.82, -0.02), (0, 2.1, 0.0), (0.5, 0.42), (0.4, 0.34), sides=8)
    H.frustum("head", "lava", (0, 2.05, -0.02), (0, 2.3, -0.04), (0.4, 0.34), (0.16, 0.14), sides=8)
    H.frustum("head", "face", (0, 1.84, 0.3), (0, 2.14, 0.36), (0.36, 0.05), (0.32, 0.05), sides=8)
    for s in (-1, 1):
        H.frustum("head", "eye", (s * 0.14, 1.98, 0.4), (s * 0.18, 2.02, 0.42), (0.09, 0.02), (0.06, 0.015), sides=4)
    H.frustum("head", "flame", (0, 2.25, -0.04), (0, 2.52, -0.04), (0.17, 0.15), (0.06, 0.05), sides=6)
    H.frustum("head", "glow", (0.0, 2.4, -0.04), (0.04, 2.72, -0.04), (0.1, 0.08), (0.01, 0.01), sides=4)
    H.frustum("head", "flame", (0.03, 2.5, -0.04), (-0.1, 2.68, -0.04), (0.08, 0.06), (0.01, 0.01), sides=4)


def arms():
    """Bracos grossos de lava: ombro cheio, cotovelo fino, antebraco que abre num punho de garra."""
    for s, side in ((1, "L"), (-1, "R")):
        arm, fore = f"arm.{side}", f"forearm.{side}"
        H.frustum(arm, "lava", (s * 0.66, 1.84, 0.0), (s * 0.78, 1.6, 0.04), (0.3, 0.28), (0.34, 0.3), sides=8)
        H.frustum(arm, "lava", (s * 0.78, 1.66, 0.06), (s * 0.84, 1.2, 0.1), (0.34, 0.3), (0.24, 0.24), sides=8)
        H.frustum(arm, "glow", (s * 0.9, 1.6, 0.12), (s * 0.92, 1.3, 0.14), (0.04, 0.03), (0.04, 0.02), sides=4)
        H.frustum(fore, "lava", (s * 0.84, 1.2, 0.1), (s * 0.87, 0.9, 0.14), (0.24, 0.24), (0.3, 0.3), sides=8)
        H.frustum(fore, "lava_dk", (s * 0.87, 0.92, 0.14), (s * 0.84, 0.62, 0.2), (0.3, 0.3), (0.34, 0.34), sides=8)
        H.frustum(fore, "lava_dk", (s * 0.84, 0.66, 0.2), (s * 0.82, 0.36, 0.26), (0.36, 0.34), (0.26, 0.26), sides=6)
        for k in (-1, 0, 1):    # dedos curtos
            H.frustum(fore, "lava", (s * (0.82 + 0.08 * k), 0.42, 0.34), (s * (0.82 + 0.1 * k), 0.24, 0.42), (0.08, 0.08), (0.05, 0.05), sides=4)
        H.frustum(fore, "glow", (s * 1.0, 1.0, 0.2), (s * 1.0, 0.7, 0.24), (0.04, 0.03), (0.06, 0.03), sides=4)


def make():
    pool()
    skirt()
    chest()
    head()
    arms()


def joints():
    out = {}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, 1.72, ARM_Z), (s * SH_X, 1.1, ARM_Z))
        out[f"forearm.{side}"] = ((s * SH_X, 1.1, ARM_Z), (s * SH_X, 0.6, ARM_Z))
    return out


H.build("h02Z", "wraith", PALETTE, make, joints())
