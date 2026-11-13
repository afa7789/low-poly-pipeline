"""Lesser Elemental Of Water (h02W): medido em artifacts/model-sheets/refs/h02W/sheet.jpg (familia wraith).

    blender -b --factory-startup -P tools/blender/units/h02W.py -- <out.glb>

Escala da prancha: 0.00343 m por pixel (prancha mostrada a 1932 px; figura de ~2.45 m); frente = direita no perfil.
Mesma criatura do h02X, so que mais magra no torso e com bracos abertos; menos caixas: mais segmentos por membro,
cintura bem fina, ombro/biceps cheios, cotovelo fino, antebraco que abre num punho largo, onda grossa.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "water": 0x13A7EA, "water_lt": 0xB5EEE6, "foam": 0xFFFFFF, "deep": 0x14598F, "teal": 0x26C6BE,
    "fist": 0x2A8497, "ripple": 0x73C3C7, "ripple_lt": 0xA6E3DF,
}

SH_X = 0.66
ARM_Z, FORE_Z = 0.0, 0.14


def ripples():
    H.frustum("root", "ripple", (0, 0.0, 0), (0, 0.03, 0), (0.85, 0.8), (0.85, 0.8), sides=12)
    H.frustum("root", "ripple_lt", (0, 0.03, 0), (0, 0.05, 0), (0.62, 0.58), (0.6, 0.56), sides=12)


def column():
    """Pe d'agua: abre no espelho, afina na cintura (o V do torso), com o miolo turquesa embaixo."""
    H.frustum("base", "water", (0, 0.0, 0.0), (0, 0.3, 0.02), (0.56, 0.5), (0.34, 0.3), sides=8)
    H.frustum("base", "water", (0, 0.28, 0.02), (0, 0.62, 0.04), (0.34, 0.3), (0.22, 0.2), sides=8)
    H.frustum("base", "water", (0, 0.6, 0.04), (0, 0.95, 0.04), (0.22, 0.2), (0.3, 0.26), sides=8)
    H.frustum("base", "teal", (0, 0.0, 0.16), (0, 0.45, 0.16), (0.3, 0.2), (0.1, 0.1), sides=6)
    H.frustum("base", "water_lt", (0.04, 0.35, 0.28), (0.02, 0.85, 0.28), (0.04, 0.03), (0.07, 0.03), sides=4)


def chest():
    """Torso em V: peito largo em cima, ombros em rampa que sobem pros lados da onda."""
    H.frustum("spine", "water", (0, 0.9, 0.04), (0, 1.25, 0.02), (0.3, 0.26), (0.5, 0.33), sides=8)
    H.frustum("spine", "water", (0, 1.22, 0.02), (0, 1.55, 0.0), (0.5, 0.33), (0.66, 0.36), sides=8)
    H.frustum("spine", "water", (0, 1.5, 0.0), (0, 1.95, -0.1), (0.64, 0.36), (0.4, 0.3), sides=8)
    for s in (-1, 1):       # peitorais
        H.frustum("spine", "water", (s * 0.24, 1.2, 0.2), (s * 0.28, 1.52, 0.22), (0.22, 0.12), (0.22, 0.1), sides=6)
    H.frustum("spine", "water_lt", (0.34, 1.62, 0.28), (-0.12, 1.5, 0.3), (0.05, 0.03), (0.2, 0.04), sides=4)
    H.frustum("spine", "water_lt", (0.0, 1.0, 0.28), (0.0, 1.3, 0.34), (0.04, 0.03), (0.08, 0.03), sides=4)


def wave():
    """A onda: curva em C grossa, sobe pelas costas, arqueia sobre a cabeca e quebra a frente em espuma."""
    arc = [("spine", (-0.28, 1.35), (-0.36, 1.68), (0.5, 0.2), (0.44, 0.22)),
           ("head", (-0.36, 1.65), (-0.32, 1.98), (0.44, 0.22), (0.4, 0.22)),
           ("head", (-0.33, 1.95), (-0.18, 2.26), (0.4, 0.22), (0.36, 0.21)),
           ("head", (-0.2, 2.23), (0.12, 2.43), (0.36, 0.21), (0.34, 0.2)),
           ("head", (0.08, 2.42), (0.46, 2.4), (0.34, 0.2), (0.32, 0.18)),
           ("head", (0.42, 2.4), (0.72, 2.24), (0.32, 0.18), (0.3, 0.16)),
           ("head", (0.7, 2.26), (0.84, 1.95), (0.3, 0.16), (0.24, 0.13))]
    for bone, (za, ya), (zb, yb), ra, rb in arc:
        H.frustum(bone, "water", (0, ya, za), (0, yb, zb), ra, rb, sides=6)
    H.frustum("head", "deep", (0, 1.9, -0.05), (0, 2.25, 0.4), (0.3, 0.03), (0.28, 0.03), sides=4)
    H.frustum("head", "foam", (0, 2.3, 0.55), (0, 1.98, 0.88), (0.34, 0.2), (0.28, 0.17), sides=6)
    H.frustum("head", "foam", (0, 2.46, 0.0), (0, 2.46, 0.45), (0.3, 0.15), (0.32, 0.12), sides=6)
    H.frustum("head", "water_lt", (0.18, 1.5, -0.55), (0.18, 2.0, -0.52), (0.08, 0.02), (0.1, 0.02), sides=4)


def arms():
    """Bracos abertos: ombro redondo, biceps cheio, cotovelo fino, antebraco que abre num punho largo."""
    for s, side in ((1, "L"), (-1, "R")):
        arm, fore = f"arm.{side}", f"forearm.{side}"
        H.frustum(arm, "water", (s * 0.5, 1.7, 0.0), (s * 0.58, 1.45, 0.0), (0.3, 0.28), (0.34, 0.3), sides=8)
        H.frustum(arm, "water", (s * 0.57, 1.5, 0.0), (s * 0.72, 1.12, 0.03), (0.34, 0.3), (0.24, 0.23), sides=8)
        H.frustum(arm, "water_lt", (s * 0.6, 1.62, 0.28), (s * 0.7, 1.3, 0.3), (0.05, 0.02), (0.05, 0.02), sides=4)
        H.frustum(fore, "water", (s * 0.72, 1.14, 0.05), (s * 0.8, 0.92, 0.12), (0.22, 0.22), (0.26, 0.26), sides=8)
        H.frustum(fore, "teal", (s * 0.8, 0.95, 0.12), (s * 0.84, 0.62, 0.15), (0.28, 0.27), (0.31, 0.3), sides=8)
        H.frustum(fore, "fist", (s * 0.84, 0.66, 0.16), (s * 0.8, 0.28, 0.2), (0.33, 0.31), (0.25, 0.26), sides=6)
        H.frustum(fore, "fist", (s * 0.8, 0.42, 0.34), (s * 0.79, 0.3, 0.42), (0.2, 0.05), (0.2, 0.08), sides=4)
        H.frustum(fore, "water_lt", (s * 0.76, 0.98, 0.34), (s * 0.78, 0.62, 0.38), (0.05, 0.02), (0.05, 0.02), sides=4)


def make():
    ripples()
    column()
    chest()
    wave()
    arms()


def joints():
    out = {}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, 1.6, ARM_Z), (s * SH_X, 1.05, ARM_Z))
        out[f"forearm.{side}"] = ((s * SH_X, 1.05, ARM_Z), (s * SH_X, 0.55, ARM_Z))
    return out


H.build("h02W", "wraith", PALETTE, make, joints())
