"""Elemental Of Lightning (h03P): medido em artifacts/model-sheets/refs/h03P/sheet.jpg (familia wraith).

    blender -b --factory-startup -P tools/blender/units/h03P.py -- <out.glb>

Escala da prancha: 0.00314 m por pixel (figura de ~2.7 m, da ponta do raio ao topo da nuvem); frente = direita no perfil.
Nuvem de tempestade flutuando sobre um raio de cauda; bracos longos segurando um raio cada; ombreira so no ombro esquerdo.
Local helpers: puff (bolha de nuvem em dois troncos) e bolt (raio em zigue-zague de cunhas finas).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "cloud": 0x56607F, "cloud_dk": 0x464D70, "under": 0x6A5A80, "limb": 0x3F4366,
    "bolt": 0xC8F4F4, "glow": 0xFFFFFF, "plate": 0x3F494A, "gold": 0x9A8548,
}

SH_X = 0.6
BOLT_ARM = [(1.16, 1.52), (0.9, 1.16), (1.0, 1.12), (0.66, 0.7), (0.76, 0.66), (0.42, 0.33)]
BOLT_TAIL = [(0.08, 1.12), (-0.18, 0.86), (0.18, 0.78), (0.0, 0.02)]


def puff(bone, tone, x, y, z, r):
    """Bolha de nuvem: dois troncos de 6 lados, largos no meio."""
    r *= 1.15
    H.frustum(bone, tone, (x, y - 0.65 * r, z), (x, y, z), (0.55 * r, 0.5 * r), (r, 0.9 * r), sides=6)
    H.frustum(bone, tone, (x, y, z), (x, y + 0.65 * r, z), (r, 0.9 * r), (0.55 * r, 0.5 * r), sides=6)


def bolt(bone, pts, z, width, sx=1.0, tone="bolt"):
    """Raio em zigue-zague: cunhas finas entre os pontos (x, y); as pontas afinam; sx espelha."""
    last = len(pts) - 2
    for i, ((xa, ya), (xb, yb)) in enumerate(zip(pts, pts[1:])):
        ra = 0.012 if i == 0 and tone == "bolt" and pts is BOLT_ARM else width
        rb = 0.012 if i == last else width
        H.frustum(bone, tone, (sx * xa, ya, z), (sx * xb, yb, z), (ra, 0.06), (rb, 0.06), sides=4)


def torso():
    H.frustum("spine", "cloud", (0, 1.1, 0), (0, 1.6, 0), (0.36, 0.32), (0.56, 0.4), sides=8)
    H.frustum("spine", "cloud", (0, 1.55, 0), (0, 2.12, -0.02), (0.56, 0.4), (0.46, 0.34), sides=8)
    H.frustum("spine", "under", (0, 1.0, 0), (0, 1.3, 0), (0.3, 0.26), (0.4, 0.32), sides=8)
    for s in (-1, 1):
        puff("spine", "cloud", s * 0.5, 1.95, 0.0, 0.24)
        puff("spine", "cloud_dk", s * 0.44, 1.55, 0.02, 0.2)
        puff("spine", "cloud", s * 0.3, 1.2, 0.0, 0.2)
    puff("spine", "cloud", 0.0, 1.15, -0.1, 0.28)
    H.frustum("spine", "glow", (0, 1.62, 0.34), (0, 1.7, 0.42), (0.1, 0.03), (0.02, 0.01), sides=4)
    H.frustum("spine", "glow", (0, 1.55, 0.36), (0, 1.85, 0.4), (0.03, 0.02), (0.1, 0.03), sides=4)


def head():
    puff("head", "cloud", 0.0, 2.42, 0.0, 0.4)
    for s in (-1, 1):
        puff("head", "cloud", s * 0.3, 2.35, 0.0, 0.26)
        puff("head", "cloud_dk", s * 0.18, 2.6, 0.02, 0.22)
    puff("head", "cloud", 0.0, 2.62, 0.0, 0.3)
    puff("head", "cloud_dk", 0.0, 2.3, -0.2, 0.3)


def tail():
    bolt("base", BOLT_TAIL, 0.05, 0.18, tone="bolt")
    H.frustum("base", "glow", (0.0, 1.08, 0.05), (0.06, 1.0, 0.05), (0.07, 0.03), (0.03, 0.02), sides=4)


def arms():
    """Bracos compridos e finos de fumaca escura, punho grande agarrando o raio."""
    for s, side in ((1, "L"), (-1, "R")):
        arm, fore = f"arm.{side}", f"forearm.{side}"
        H.frustum(arm, "limb", (s * 0.5, 1.9, 0.08), (s * 0.58, 1.66, 0.1), (0.2, 0.18), (0.15, 0.14), sides=6)
        H.frustum(arm, "limb", (s * 0.58, 1.7, 0.1), (s * 0.68, 1.4, 0.12), (0.15, 0.14), (0.1, 0.1), sides=6)
        H.frustum(fore, "limb", (s * 0.68, 1.4, 0.12), (s * 0.74, 1.18, 0.18), (0.1, 0.1), (0.13, 0.12), sides=6)
        H.frustum(fore, "limb", (s * 0.74, 1.2, 0.18), (s * 0.78, 1.0, 0.26), (0.13, 0.12), (0.12, 0.12), sides=6)
        H.frustum(fore, "limb", (s * 0.78, 1.08, 0.26), (s * 0.78, 0.88, 0.3), (0.17, 0.16), (0.12, 0.12), sides=6)
        bolt(fore, BOLT_ARM, 0.3, 0.12, sx=s)


def plate():
    """Ombreira escura com friso dourado, so no ombro esquerdo (+x), na frente e no perfil."""
    H.frustum("arm.L", "gold", (0.44, 1.98, 0.0), (0.74, 1.72, 0.0), (0.3, 0.3), (0.36, 0.3), sides=6)
    H.frustum("arm.L", "plate", (0.44, 2.08, 0.0), (0.74, 1.8, 0.0), (0.36, 0.36), (0.44, 0.38), sides=6)


def make():
    torso()
    head()
    tail()
    arms()
    plate()


def joints():
    out = {}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, 1.9, 0.1), (s * SH_X, 1.4, 0.1))
        out[f"forearm.{side}"] = ((s * SH_X, 1.4, 0.1), (s * SH_X, 0.9, 0.1))
    return out


H.build("h03P", "wraith", PALETTE, make, joints())
