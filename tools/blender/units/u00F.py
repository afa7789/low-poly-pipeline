"""Greater Elemental Of Fire (u00F): medido em artifacts/model-sheets/refs/u00F/sheet.jpg (familia wraith).

    blender -b --factory-startup -P tools/blender/units/u00F.py -- <out.glb>

Irmao maior do h02Z (mesma estrutura de poca, coluna, tronco e bracos); caveira com chifres e coroa de fogo.
Escala da prancha: 0.0032 m por pixel (figura de ~3 m com a chama); frente = direita no perfil.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "lava": 0xFF7A12, "lava_dk": 0xB5242E, "glow": 0xFFD36B, "flame": 0xFFA21F, "flame_dk": 0xC8202E,
    "rock": 0x453540, "horn": 0x5E4C5E, "bone": 0xFFF1D0, "skull": 0x2A2128, "eye": 0xFFC73A,
}

SH_X = 0.78
ARM_Z = 0.1


def pool():
    """Poca de lava no chao, com placas de rocha em volta da borda."""
    H.frustum("root", "lava_dk", (0, 0.0, 0), (0, 0.06, 0), (1.05, 0.85), (1.0, 0.8), sides=12)
    H.frustum("root", "lava", (0, 0.06, 0), (0, 0.1, 0), (0.92, 0.72), (0.86, 0.66), sides=12)
    H.frustum("root", "glow", (0, 0.1, 0), (0, 0.12, 0), (0.5, 0.4), (0.4, 0.3), sides=12)
    for i in range(7):
        a = i * 2 * math.pi / 7 + 0.2
        x, z = 1.0 * math.cos(a), 0.82 * math.sin(a)
        H.frustum("root", "rock", (x, 0.0, z), (x * 0.97, 0.22, z * 0.97), (0.16, 0.1), (0.1, 0.06), sides=4)


def column():
    """Coluna de lava em trombeta: abre na poca, afina na cintura."""
    H.frustum("base", "lava", (0, 0.05, -0.12), (0, 0.4, -0.06), (0.62, 0.52), (0.38, 0.34), sides=8)
    H.frustum("base", "lava", (0, 0.36, 0), (0, 0.8, 0), (0.38, 0.34), (0.24, 0.22), sides=8)
    H.frustum("base", "lava", (0, 0.76, 0), (0, 1.25, 0), (0.24, 0.22), (0.22, 0.2), sides=8)
    H.frustum("base", "glow", (0, 0.2, 0.3), (0, 1.2, 0.2), (0.14, 0.03), (0.08, 0.03), sides=4)
    H.frustum("base", "flame_dk", (0, 0.2, -0.3), (0, 1.2, -0.2), (0.1, 0.03), (0.05, 0.03), sides=4)


def chest():
    H.frustum("spine", "lava", (0, 1.2, 0), (0, 1.55, 0), (0.22, 0.2), (0.52, 0.34), sides=8)
    H.frustum("spine", "lava", (0, 1.5, 0), (0, 1.95, 0), (0.52, 0.34), (0.58, 0.32), sides=8)
    H.frustum("spine", "glow", (0, 1.25, 0.18), (0, 1.8, 0.28), (0.08, 0.04), (0.2, 0.05), sides=6)    # esterno
    for s in (-1, 1):
        for k in range(4):    # costelas de rocha
            y = 1.35 + k * 0.12
            H.frustum("spine", "rock", (s * 0.08, y, 0.3), (s * (0.42 - k * 0.02), y + 0.1, 0.24), (0.05, 0.04), (0.06, 0.05), sides=4)
        H.frustum("spine", "rock", (s * 0.64, 1.78, 0.0), (s * 0.66, 2.05, 0.0), (0.34, 0.3), (0.24, 0.2), sides=6)   # ombreira
        H.frustum("spine", "horn", (s * 0.62, 2.0, 0.0), (s * 0.74, 2.38, -0.04), (0.14, 0.12), (0.01, 0.01), sides=4)
        H.frustum("spine", "rock", (s * 0.2, 1.7, -0.3), (s * 0.22, 1.9, -0.34), (0.16, 0.2), (0.12, 0.16), sides=6)   # placas das costas
    H.frustum("spine", "rock", (0.0, 1.35, -0.3), (0.0, 1.55, -0.32), (0.12, 0.1), (0.08, 0.08), sides=6)
    H.frustum("spine", "glow", (0, 1.3, -0.34), (0, 1.9, -0.36), (0.04, 0.03), (0.07, 0.03), sides=4)


def horns(s):
    H.frustum("head", "horn", (s * 0.2, 2.34, 0.18), (s * 0.5, 2.44, 0.14), (0.12, 0.1), (0.1, 0.09), sides=6)
    H.frustum("head", "horn", (s * 0.48, 2.42, 0.14), (s * 0.68, 2.64, 0.12), (0.1, 0.09), (0.08, 0.07), sides=6)
    H.frustum("head", "horn", (s * 0.66, 2.62, 0.12), (s * 0.64, 2.92, 0.1), (0.08, 0.07), (0.01, 0.01), sides=6)


def head():
    H.frustum("head", "skull", (0, 1.98, 0.22), (0, 2.28, 0.26), (0.2, 0.18), (0.24, 0.2), sides=8)
    H.frustum("head", "skull", (0, 2.26, 0.24), (0, 2.46, 0.22), (0.24, 0.2), (0.2, 0.16), sides=8)
    for s in (-1, 1):
        H.frustum("head", "eye", (s * 0.09, 2.28, 0.44), (s * 0.12, 2.31, 0.46), (0.06, 0.02), (0.04, 0.015), sides=4)
        horns(s)
    H.frustum("head", "glow", (0, 1.96, 0.3), (0, 2.1, 0.4), (0.16, 0.04), (0.14, 0.04), sides=6)       # dentes
    H.frustum("head", "skull", (0, 2.0, 0.28), (0, 2.1, 0.4), (0.12, 0.03), (0.1, 0.03), sides=4)
    H.frustum("head", "flame_dk", (0, 2.4, -0.1), (0, 2.75, -0.12), (0.4, 0.3), (0.26, 0.2), sides=8)   # coroa de fogo
    H.frustum("head", "flame", (0, 2.5, -0.08), (0, 3.1, -0.1), (0.22, 0.18), (0.01, 0.01), sides=4)
    H.frustum("head", "flame", (0, 2.45, -0.1), (0, 2.85, -0.42), (0.16, 0.14), (0.01, 0.01), sides=4)
    H.frustum("head", "glow", (0, 2.45, -0.04), (0, 2.8, -0.06), (0.12, 0.1), (0.01, 0.01), sides=4)
    for s in (-1, 1):
        H.frustum("head", "flame", (s * 0.2, 2.5, -0.08), (s * 0.34, 2.95, -0.1), (0.12, 0.1), (0.01, 0.01), sides=4)
        H.frustum("head", "flame_dk", (s * 0.3, 2.5, -0.08), (s * 0.5, 2.8, -0.1), (0.1, 0.08), (0.01, 0.01), sides=4)


def arms():
    """Bracos de lava com placas de rocha por fora e punhos enormes."""
    for s, side in ((1, "L"), (-1, "R")):
        arm, fore = f"arm.{side}", f"forearm.{side}"
        H.frustum(arm, "lava", (s * 0.62, 1.9, 0.0), (s * 0.78, 1.55, 0.05), (0.3, 0.28), (0.36, 0.32), sides=8)
        H.frustum(arm, "lava", (s * 0.78, 1.6, 0.05), (s * 0.82, 1.12, 0.1), (0.36, 0.32), (0.26, 0.24), sides=8)
        H.frustum(arm, "rock", (s * 1.0, 1.72, 0.05), (s * 1.02, 1.4, 0.05), (0.14, 0.2), (0.12, 0.18), sides=6)
        H.frustum(arm, "horn", (s * 1.02, 1.5, 0.05), (s * 1.14, 1.76, 0.05), (0.1, 0.1), (0.01, 0.01), sides=4)
        H.frustum(arm, "glow", (s * 0.86, 1.6, 0.2), (s * 0.88, 1.3, 0.22), (0.04, 0.03), (0.04, 0.02), sides=4)
        H.frustum(fore, "lava", (s * 0.82, 1.14, 0.1), (s * 0.8, 0.86, 0.2), (0.26, 0.24), (0.32, 0.3), sides=8)
        H.frustum(fore, "rock", (s * 1.0, 1.1, 0.12), (s * 1.0, 0.8, 0.16), (0.14, 0.2), (0.1, 0.16), sides=6)
        H.frustum(fore, "horn", (s * 1.02, 1.0, 0.12), (s * 1.1, 1.22, 0.12), (0.08, 0.08), (0.01, 0.01), sides=4)
        H.frustum(fore, "lava", (s * 0.8, 0.88, 0.22), (s * 0.76, 0.52, 0.34), (0.34, 0.32), (0.36, 0.34), sides=8)
        H.frustum(fore, "rock", (s * 0.76, 0.66, 0.32), (s * 0.74, 0.44, 0.38), (0.36, 0.34), (0.3, 0.28), sides=6)
        H.frustum(fore, "glow", (s * 0.78, 0.8, 0.46), (s * 0.76, 0.6, 0.5), (0.05, 0.03), (0.08, 0.03), sides=4)


def make():
    pool()
    column()
    chest()
    head()
    arms()


def joints():
    out = {}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, 1.72, ARM_Z), (s * SH_X, 1.1, ARM_Z))
        out[f"forearm.{side}"] = ((s * SH_X, 1.1, ARM_Z), (s * SH_X, 0.6, ARM_Z))
    return out


H.build("u00F", "wraith", PALETTE, make, joints())
