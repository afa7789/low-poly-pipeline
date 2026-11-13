"""Elemental Of Water (h02X): medido em artifacts/model-sheets/refs/h02X/sheet.jpg (familia wraith).

    blender -b --factory-startup -P tools/blender/units/h02X.py -- <out.glb>

Escala da prancha: 0.00343 m por pixel (figura de ~2.45 m); frente = direita no perfil.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "water": 0x1CA3E8, "water_lt": 0x9FE3E6, "foam": 0xFFFFFF, "deep": 0x15578F, "teal": 0x2DBFBF,
    "fist": 0x2A8497, "ripple": 0x7FBFC4, "ripple_lt": 0xB3E6E0,
}

SH_X = 0.78
ARM_Z, FORE_Z = 0.1, 0.22


def ripples():
    """A agua em volta: discos rasos no chao, so o espelho d'agua da prancha (o corpo nao pousa nele)."""
    H.frustum("root", "ripple", (0, 0.0, 0), (0, 0.03, 0), (1.1, 1.0), (1.1, 1.0), sides=12)
    H.frustum("root", "ripple_lt", (0, 0.03, 0), (0, 0.05, 0), (0.9, 0.82), (0.88, 0.8), sides=12)
    H.frustum("root", "ripple", (0, 0.05, 0), (0, 0.07, 0), (0.7, 0.64), (0.68, 0.62), sides=12)


def column():
    """Pe d'agua que se estreita na cintura fina (o V do torso) e abre de novo no espelho."""
    H.frustum("base", "water", (0, 0.0, 0), (0, 0.55, 0.0), (0.56, 0.4), (0.27, 0.26), sides=8)
    H.frustum("base", "teal", (0, 0.0, 0.1), (0, 0.65, 0.12), (0.36, 0.3), (0.13, 0.2), sides=6)
    H.frustum("base", "water", (0, 0.5, 0), (0, 1.05, 0.02), (0.27, 0.26), (0.27, 0.22), sides=8)
    H.frustum("base", "water", (0, 1.0, 0.02), (0, 1.25, 0.04), (0.27, 0.22), (0.34, 0.27), sides=8)
    H.frustum("base", "water_lt", (0.0, 0.7, 0.2), (0.0, 1.2, 0.24), (0.04, 0.03), (0.07, 0.03), sides=4)


def chest():
    H.frustum("spine", "water", (0, 1.2, 0.04), (0, 1.62, 0.06), (0.32, 0.26), (0.68, 0.4), sides=8)
    H.frustum("spine", "water", (0, 1.6, 0.06), (0, 1.9, 0.02), (0.68, 0.4), (0.74, 0.34), sides=8)
    H.frustum("spine", "water", (0, 1.85, 0.0), (0, 2.1, -0.1), (0.5, 0.3), (0.3, 0.24), sides=6)
    for s in (-1, 1):       # peitorais em cunha
        H.frustum("spine", "water", (s * 0.28, 1.42, 0.3), (s * 0.3, 1.74, 0.3), (0.26, 0.12), (0.24, 0.1), sides=6)
    H.frustum("spine", "water_lt", (0.22, 1.76, 0.4), (-0.18, 1.86, 0.36), (0.05, 0.03), (0.22, 0.04), sides=4)
    H.frustum("spine", "water_lt", (0.0, 1.3, 0.3), (0.0, 1.55, 0.4), (0.04, 0.03), (0.09, 0.03), sides=4)
    H.frustum("spine", "deep", (0, 1.52, 0.33), (0, 1.58, 0.42), (0.42, 0.04), (0.46, 0.03), sides=4)


def wave():
    """A onda: curva em S grossa, sobe pelas costas, arqueia sobre a cabeca e quebra a frente em espuma."""
    arc = [("spine", (-0.24, 1.35), (-0.31, 1.85), (0.45, 0.2), (0.55, 0.22)),
           ("head", (-0.31, 1.8), (-0.25, 2.12), (0.55, 0.22), (0.55, 0.22)),
           ("head", (-0.26, 2.08), (-0.02, 2.27), (0.55, 0.22), (0.5, 0.2)),
           ("head", (-0.05, 2.29), (0.4, 2.31), (0.5, 0.19), (0.45, 0.17)),
           ("head", (0.35, 2.29), (0.75, 2.2), (0.45, 0.17), (0.4, 0.15)),
           ("head", (0.7, 2.22), (0.95, 2.0), (0.4, 0.15), (0.36, 0.14))]
    for bone, (za, ya), (zb, yb), ra, rb in arc:
        H.frustum(bone, "water", (0, ya, za), (0, yb, zb), ra, rb, sides=6)
    H.frustum("head", "deep", (0, 1.95, 0.0), (0, 2.2, 0.45), (0.32, 0.03), (0.3, 0.03), sides=4)
    H.frustum("head", "water_lt", (0.1, 1.5, -0.45), (0.1, 1.85, -0.52), (0.07, 0.02), (0.07, 0.02), sides=4)
    H.frustum("head", "water_lt", (0.0, 2.47, -0.05), (0.0, 2.49, 0.4), (0.06, 0.015), (0.06, 0.015), sides=4)
    H.frustum("head", "foam", (0, 2.05, 0.85), (0, 1.88, 1.05), (0.4, 0.2), (0.3, 0.18), sides=6)
    for s in (-1, 1):
        H.frustum("head", "foam", (s * 0.24, 2.28, 0.6), (s * 0.24, 2.1, 0.84), (0.2, 0.16), (0.18, 0.14), sides=6)
    H.frustum("head", "foam", (0, 2.4, 0.15), (0, 2.42, 0.5), (0.24, 0.09), (0.28, 0.08), sides=6)


def arms():
    """Bracos de gorila: ombro redondo, biceps cheio, cotovelo fino, antebraco que abre num punho enorme."""
    for s, side in ((1, "L"), (-1, "R")):
        arm, fore = f"arm.{side}", f"forearm.{side}"
        H.frustum(arm, "water", (s * 0.48, 1.88, 0.06), (s * 0.53, 1.6, 0.08), (0.31, 0.3), (0.31, 0.3), sides=8)
        H.frustum(arm, "water", (s * 0.55, 1.66, 0.08), (s * 0.69, 1.2, 0.14), (0.3, 0.3), (0.26, 0.27), sides=8)
        H.frustum(arm, "water_lt", (s * 0.58, 1.8, 0.36), (s * 0.68, 1.4, 0.4), (0.05, 0.02), (0.05, 0.02), sides=4)
        H.frustum(fore, "water", (s * 0.69, 1.25, 0.16), (s * 0.73, 1.0, 0.2), (0.24, 0.25), (0.22, 0.23), sides=8)
        H.frustum(fore, "water", (s * 0.73, 1.05, 0.2), (s * 0.75, 0.82, 0.24), (0.22, 0.23), (0.27, 0.29), sides=8)
        H.frustum(fore, "teal", (s * 0.75, 0.85, 0.24), (s * 0.77, 0.5, 0.3), (0.28, 0.3), (0.3, 0.32), sides=8)
        H.frustum(fore, "water_lt", (s * 0.7, 0.9, 0.5), (s * 0.72, 0.55, 0.56), (0.05, 0.02), (0.05, 0.02), sides=4)
        H.frustum(fore, "fist", (s * 0.77, 0.55, 0.3), (s * 0.71, 0.22, 0.38), (0.31, 0.33), (0.26, 0.3), sides=6)
        H.frustum(fore, "fist", (s * 0.71, 0.34, 0.5), (s * 0.70, 0.2, 0.62), (0.22, 0.05), (0.22, 0.09), sides=4)


def make():
    ripples()
    column()
    chest()
    wave()
    arms()


def joints():
    out = {}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, 1.72, ARM_Z), (s * SH_X, 1.1, ARM_Z))
        out[f"forearm.{side}"] = ((s * SH_X, 1.1, ARM_Z), (s * SH_X, 0.6, ARM_Z))
    return out


H.build("h02X", "wraith", PALETTE, make, joints())
