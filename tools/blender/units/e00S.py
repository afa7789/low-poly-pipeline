"""Forest Spirit (e00S): medido em artifacts/model-sheets/refs/e00S/sheet.jpg (familia wraith).

    blender -b --factory-startup -P tools/blender/units/e00S.py -- <out.glb>

Escala da prancha: 0.0048 m por pixel (figura de ~2.2 m, tentaculos nao tocam o chao); frente = direita no perfil.
Casulo flutuante: duas conchas marrons abertas na frente com o orbe verde dentro e tres tentaculos pendurados.
Os tentaculos laterais ficam nos ossos do braco (sobem e avancam no ataque); o do meio fica no tronco.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "shell": 0x7C5646, "shell_lt": 0x9A6D58, "shell_dk": 0x5A3E32,
    "orb": 0xC9E27C, "orb_lt": 0xE6F4B0,
    "stalk": 0x68762F, "stalk_lt": 0x7F8F3A,
}

# nivel da concha: (y, cx, rx, cz, rz); a concha e mais larga no meio e fecha em duas pontas no topo
LEVELS = [(1.03, 0.07, 0.09, -0.05, 0.14), (1.3, 0.17, 0.21, -0.06, 0.25), (1.58, 0.23, 0.25, -0.06, 0.3),
          (1.9, 0.2, 0.17, -0.08, 0.25), (2.2, 0.1, 0.06, -0.14, 0.13)]
SIDE_X = 0.22


def shell():
    for s in (-1, 1):
        for i in range(len(LEVELS) - 1):
            (ya, cxa, rxa, cza, rza), (yb, cxb, rxb, czb, rzb) = LEVELS[i], LEVELS[i + 1]
            bone = "head" if yb > 1.9 else "spine"
            tone = ("shell", "shell_lt", "shell", "shell_dk")[i]
            H.frustum(bone, tone, (s * cxa, ya, cza), (s * cxb, yb, czb), (rxa, rza), (rxb, rzb), sides=6)


def orb():
    """O orbe verde: ovo que entra no casulo e aparece na frente, com um brilho claro."""
    z = 0.17
    rings = [(1.24, 0.06, 0.06), (1.42, 0.2, 0.19), (1.62, 0.25, 0.23), (1.82, 0.2, 0.18), (1.93, 0.07, 0.07)]
    for (ya, rxa, rza), (yb, rxb, rzb) in zip(rings, rings[1:]):
        H.frustum("spine", "orb", (0, ya, z), (0, yb, z), (rxa, rza), (rxb, rzb), sides=8)
    H.frustum("spine", "orb_lt", (0.07, 1.62, 0.37), (0.04, 1.84, 0.34), (0.07, 0.03), (0.05, 0.03), sides=4)


def tendrils():
    radii = [(0.06, 0.06), (0.095, 0.095), (0.125, 0.125), (0.14, 0.14), (0.04, 0.04)]
    for s, side in ((1, "L"), (-1, "R")):
        pts = [(s * SIDE_X, 1.12, -0.08), (s * SIDE_X, 0.9, -0.08), (s * SIDE_X, 0.68, -0.06),
               (s * SIDE_X, 0.46, 0.0), (s * SIDE_X, 0.22, 0.1)]
        H.chain([f"arm.{side}"] * 2 + [f"forearm.{side}"] * 2, "stalk", pts, radii)
    pts = [(0, 1.05, 0.09), (0, 0.8, 0.09), (0, 0.55, 0.1), (0, 0.28, 0.12), (0, 0.0, 0.12)]
    H.chain("spine", "stalk_lt", pts, [(0.065, 0.065), (0.1, 0.1), (0.135, 0.135), (0.155, 0.155), (0.045, 0.045)])


def make():
    shell()
    orb()
    tendrils()


def joints():
    out = {}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SIDE_X, 1.12, -0.08), (s * SIDE_X, 0.68, -0.06))
        out[f"forearm.{side}"] = ((s * SIDE_X, 0.68, -0.06), (s * SIDE_X, 0.22, 0.1))
    return out


H.build("e00S", "wraith", PALETTE, make, joints())
