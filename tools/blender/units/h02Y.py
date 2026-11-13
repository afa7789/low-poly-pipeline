"""Greater Elemental Of Water (h02Y): medido em artifacts/model-sheets/refs/h02Y/sheet.jpg (familia wraith).

    blender -b --factory-startup -P tools/blender/units/h02Y.py -- <out.glb>

Escala da prancha: 0.0034 m por pixel (prancha mostrada a 1932 px; figura de ~2.55 m); frente = direita no perfil.
Mesma criatura do h02X/h02W com ombreiras marrons de concha de vieira, espinhos d'agua nos ombros e nos punhos,
onda mais alta e grossa com crista de espuma. Menos caixas: mais segmentos, bulges fortes, cintura fina.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "water": 0x3A9BE0, "water_lt": 0xBDEBF0, "foam": 0xFFFFFF, "deep": 0x23599B, "teal": 0x4AB8BE,
    "fist": 0x3F8BA3, "ripple": 0x8DBFCB, "ripple_lt": 0xB6DDE0,
    "plate": 0x7B4A3B, "plate_dk": 0x5C372D, "scallop": 0xF0A765, "coral": 0xE8704F, "spike": 0xA5DDF0,
}

SH_X = 0.72
ARM_Z = 0.0


def ripples():
    H.frustum("root", "ripple", (0, 0.0, 0), (0, 0.03, 0), (1.0, 0.95), (1.0, 0.95), sides=12)
    H.frustum("root", "ripple_lt", (0, 0.03, 0), (0, 0.05, 0), (0.76, 0.72), (0.74, 0.7), sides=12)
    H.frustum("root", "ripple", (0, 0.05, 0), (0, 0.07, 0), (0.52, 0.5), (0.5, 0.48), sides=12)


def column():
    """Pe d'agua: abre no espelho, afina na cintura, miolo turquesa embaixo."""
    H.frustum("base", "water", (0, 0.0, 0.0), (0, 0.3, 0.02), (0.58, 0.52), (0.36, 0.32), sides=8)
    H.frustum("base", "water", (0, 0.28, 0.02), (0, 0.66, 0.04), (0.36, 0.32), (0.25, 0.22), sides=8)
    H.frustum("base", "water", (0, 0.64, 0.04), (0, 1.0, 0.04), (0.25, 0.22), (0.34, 0.28), sides=8)
    H.frustum("base", "teal", (0, 0.0, 0.18), (0, 0.5, 0.18), (0.32, 0.22), (0.11, 0.1), sides=6)
    H.frustum("base", "water_lt", (0.04, 0.4, 0.3), (0.02, 0.9, 0.3), (0.04, 0.03), (0.08, 0.03), sides=4)


def chest():
    H.frustum("spine", "water", (0, 0.95, 0.04), (0, 1.3, 0.02), (0.34, 0.28), (0.54, 0.36), sides=8)
    H.frustum("spine", "water", (0, 1.25, 0.02), (0, 1.6, 0.0), (0.54, 0.36), (0.7, 0.4), sides=8)
    H.frustum("spine", "water", (0, 1.55, 0.0), (0, 2.0, -0.1), (0.66, 0.4), (0.4, 0.32), sides=8)
    for s in (-1, 1):       # peitorais
        H.frustum("spine", "water", (s * 0.26, 1.25, 0.22), (s * 0.3, 1.56, 0.24), (0.24, 0.13), (0.24, 0.11), sides=6)
    H.frustum("spine", "water_lt", (0.0, 1.05, 0.3), (0.0, 1.35, 0.36), (0.04, 0.03), (0.09, 0.03), sides=4)


def wave():
    """Onda alta e grossa: sobe pelas costas, arqueia sobre a cabeca, crista de espuma que quebra na frente."""
    arc = [("spine", (-0.3, 1.35), (-0.42, 1.72), (0.54, 0.24), (0.48, 0.25)),
           ("head", (-0.42, 1.7), (-0.38, 2.02), (0.48, 0.25), (0.44, 0.25)),
           ("head", (-0.39, 2.0), (-0.22, 2.32), (0.44, 0.25), (0.42, 0.24)),
           ("head", (-0.24, 2.3), (0.08, 2.5), (0.42, 0.24), (0.4, 0.23)),
           ("head", (0.04, 2.5), (0.42, 2.5), (0.4, 0.23), (0.37, 0.21)),
           ("head", (0.38, 2.5), (0.68, 2.38), (0.37, 0.21), (0.34, 0.19)),
           ("head", (0.66, 2.4), (0.8, 2.15), (0.34, 0.19), (0.28, 0.15))]
    for bone, (za, ya), (zb, yb), ra, rb in arc:
        H.frustum(bone, "water", (0, ya, za), (0, yb, zb), ra, rb, sides=6)
    H.frustum("head", "deep", (0, 1.95, -0.05), (0, 2.3, 0.42), (0.32, 0.03), (0.3, 0.03), sides=4)
    H.frustum("head", "foam", (0, 2.5, -0.2), (0, 2.58, 0.32), (0.36, 0.2), (0.46, 0.2), sides=8)
    H.frustum("head", "foam", (0, 2.5, 0.3), (0, 2.34, 0.8), (0.4, 0.2), (0.34, 0.17), sides=8)
    H.frustum("head", "foam", (0, 2.4, 0.7), (0, 2.12, 0.86), (0.32, 0.17), (0.26, 0.14), sides=6)
    H.frustum("head", "water_lt", (0.18, 1.5, -0.62), (0.18, 2.2, -0.58), (0.08, 0.02), (0.1, 0.02), sides=4)


def pauldrons():
    """Ombreiras marrons grandes com a vieira na frente e um espinho d'agua saindo pra cima."""
    for s, side in ((1, "L"), (-1, "R")):
        arm = f"arm.{side}"
        H.frustum(arm, "plate", (s * 0.52, 1.35, 0.0), (s * 0.62, 1.62, 0.0), (0.26, 0.28), (0.34, 0.32), sides=6)
        H.frustum(arm, "plate_dk", (s * 0.62, 1.58, 0.0), (s * 0.7, 1.92, 0.0), (0.34, 0.32), (0.26, 0.24), sides=6)
        H.frustum(arm, "scallop", (s * 0.62, 1.62, 0.28), (s * 0.62, 1.66, 0.4), (0.27, 0.25), (0.23, 0.22), sides=8)
        H.frustum(arm, "coral", (s * 0.62, 1.52, 0.4), (s * 0.62, 1.5, 0.46), (0.14, 0.12), (0.1, 0.09), sides=6)
        H.frustum(arm, "spike", (s * 0.74, 1.9, 0.0), (s * 0.98, 2.42, 0.0), (0.08, 0.07), (0.01, 0.01), sides=4)


def arms():
    """Bracos gigantes: biceps cheio, cotovelo fino, antebraco que abre no punho, espinhos d'agua no punho."""
    for s, side in ((1, "L"), (-1, "R")):
        arm, fore = f"arm.{side}", f"forearm.{side}"
        H.frustum(arm, "water", (s * 0.6, 1.55, 0.0), (s * 0.8, 1.22, 0.02), (0.32, 0.3), (0.3, 0.28), sides=8)
        H.frustum(arm, "water", (s * 0.78, 1.28, 0.02), (s * 0.9, 1.05, 0.04), (0.3, 0.28), (0.23, 0.22), sides=8)
        H.frustum(fore, "water", (s * 0.9, 1.08, 0.05), (s * 0.94, 0.86, 0.1), (0.23, 0.23), (0.28, 0.28), sides=8)
        H.frustum(fore, "teal", (s * 0.94, 0.9, 0.1), (s * 0.9, 0.6, 0.14), (0.3, 0.29), (0.34, 0.32), sides=8)
        H.frustum(fore, "fist", (s * 0.9, 0.64, 0.15), (s * 0.84, 0.28, 0.2), (0.36, 0.33), (0.28, 0.28), sides=6)
        H.frustum(fore, "fist", (s * 0.84, 0.42, 0.34), (s * 0.84, 0.3, 0.44), (0.22, 0.05), (0.22, 0.08), sides=4)
        H.frustum(fore, "spike", (s * 1.02, 0.85, 0.0), (s * 1.16, 1.5, 0.0), (0.08, 0.07), (0.01, 0.01), sides=4)
        H.frustum(fore, "spike", (s * 0.96, 0.8, 0.12), (s * 1.0, 1.35, 0.14), (0.07, 0.06), (0.01, 0.01), sides=4)


def make():
    ripples()
    column()
    chest()
    wave()
    pauldrons()
    arms()


def joints():
    out = {}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, 1.65, ARM_Z), (s * SH_X, 1.07, ARM_Z))
        out[f"forearm.{side}"] = ((s * SH_X, 1.07, ARM_Z), (s * SH_X, 0.55, ARM_Z))
    return out


H.build("h02Y", "wraith", PALETTE, make, joints())
