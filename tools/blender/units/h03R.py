"""Greater Elemental Of Lightning (h03R): medido em artifacts/model-sheets/refs/h03R/sheet.jpg (familia wraith).

    blender -b --factory-startup -P tools/blender/units/h03R.py -- <out.glb>

Escala da prancha: 0.00314 m por pixel (figura de ~2.7 m); frente = direita no perfil.
Torso de nuvem-rocha enorme com duas ombreiras, bracos grossos, raios pendurados nos punhos com garfo dourado.
Local helpers: puff (bolha de nuvem em dois troncos) e bolt (raio em zigue-zague de cunhas finas).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "cloud": 0x34396B, "cloud_lt": 0x414A80, "cloud_dk": 0x272B58, "under": 0x4F3A7C, "plate": 0x38403F,
    "gold": 0xB89A4A, "bolt": 0x5CD6F5, "glow": 0xEAFFFF,
}

W = 0.88
SH_X = 0.85 * W
BOLT_HAND = [(0.74, 1.0), (0.56, 0.72), (0.72, 0.58), (0.5, 0.34)]
BOLT_TAIL = [(0.06, 1.15), (-0.22, 0.88), (0.2, 0.8), (0.0, 0.02)]


def puff(bone, tone, x, y, z, r):
    """Bolha de nuvem: dois troncos de 6 lados, largos no meio."""
    H.frustum(bone, tone, (x, y - 0.65 * r, z), (x, y, z), (0.55 * r, 0.5 * r), (r, 0.9 * r), sides=6)
    H.frustum(bone, tone, (x, y, z), (x, y + 0.65 * r, z), (r, 0.9 * r), (0.55 * r, 0.5 * r), sides=6)


def bolt(bone, pts, z, width, sx=1.0, tone="bolt"):
    """Raio em zigue-zague: cunhas finas entre os pontos (x, y); a ultima afina em ponta; sx espelha."""
    last = len(pts) - 2
    for i, ((xa, ya), (xb, yb)) in enumerate(zip(pts, pts[1:])):
        rb = 0.012 if i == last else width
        H.frustum(bone, tone, (sx * xa, ya, z), (sx * xb, yb, z), (width, 0.07), (rb, 0.07), sides=4)


def torso():
    H.frustum("spine", "cloud", (0, 1.1, 0), (0, 1.5, 0), (0.36, 0.3), (0.64, 0.46), sides=8)
    H.frustum("spine", "cloud", (0, 1.45, 0), (0, 2.0, 0), (0.64, 0.46), (0.8, 0.5), sides=8)
    H.frustum("spine", "cloud", (0, 1.95, -0.02), (0, 2.4, -0.04), (0.8, 0.5), (0.5, 0.42), sides=8)
    H.frustum("spine", "under", (0, 0.98, 0), (0, 1.3, 0), (0.32, 0.26), (0.48, 0.36), sides=8)
    for s in (-1, 1):
        puff("spine", "cloud_lt", s * 0.62, 1.55, -0.02, 0.26)
        puff("spine", "cloud_dk", s * 0.34, 1.2, -0.06, 0.22)
    puff("spine", "cloud_dk", 0.0, 1.9, -0.36, 0.5)
    for s in (-1, 1):       # pedras do peito em volta da estrela, com espessura
        for y, r in ((2.08, 0.2), (1.62, 0.17)):
            H.frustum("spine", "plate", (s * 0.34, y, 0.45), (s * 0.34, y, 0.78), (r * 1.2, r), (r, r * 0.8), sides=6)
    H.frustum("spine", "glow", (0, 1.9, 0.5), (0, 1.9, 0.86), (0.26, 0.26), (0.08, 0.08), sides=8)


def head():
    H.frustum("head", "cloud_lt", (0, 2.1, -0.06), (0, 2.45, -0.08), (0.36, 0.34), (0.34, 0.32), sides=6)
    H.frustum("head", "cloud_lt", (0, 2.4, -0.08), (0, 2.72, -0.1), (0.34, 0.32), (0.2, 0.2), sides=6)
    puff("head", "cloud", 0.0, 2.4, -0.3, 0.26)


def tail():
    bolt("base", BOLT_TAIL, 0.05, 0.16)
    bolt("base", [(0.0, 1.1), (-0.05, 0.9)], 0.05, 0.07, tone="glow")


def arm_bolt(fore, s):
    sw = s * W
    bolt(fore, BOLT_HAND, 0.3, 0.1, sx=sw)
    for x, y in ((0.3, 0.08), (0.64, 0.1)):     # garfo dourado
        H.frustum(fore, "gold", (sw * 0.5, 0.36, 0.3), (sw * x, y, 0.3), (0.05, 0.05), (0.012, 0.02), sides=4)
    H.frustum(fore, "bolt", (sw * 1.12, 1.4, 0.1), (sw * 1.28, 1.62, 0.1), (0.06, 0.06), (0.012, 0.02), sides=4)


def arms():
    """Bracos de nuvem-rocha: ombro enorme, biceps cheio, cotovelo para fora, antebraco que fecha num punho grande."""
    for s, side in ((1, "L"), (-1, "R")):
        sw = s * W
        arm, fore = f"arm.{side}", f"forearm.{side}"
        puff(arm, "cloud_lt", sw * 0.95, 1.85, 0.0, 0.3)
        H.frustum(arm, "cloud", (sw * 0.76, 1.8, 0.0), (sw * 1.0, 1.55, 0.04), (0.29, 0.26), (0.27, 0.24), sides=8)
        H.frustum(arm, "cloud_dk", (sw * 1.0, 1.6, 0.04), (sw * 0.76, 1.3, 0.1), (0.27, 0.24), (0.22, 0.20), sides=8)
        H.frustum(fore, "cloud", (sw * 0.76, 1.4, 0.1), (sw * 0.84, 1.1, 0.22), (0.22, 0.20), (0.24, 0.22), sides=8)
        H.frustum(fore, "cloud_lt", (sw * 0.84, 1.15, 0.22), (sw * 0.76, 0.86, 0.3), (0.24, 0.22), (0.22, 0.20), sides=8)
        H.frustum(fore, "cloud_dk", (sw * 0.84, 1.1, 0.34), (sw * 0.76, 0.84, 0.4), (0.22, 0.14), (0.17, 0.13), sides=6)
        arm_bolt(fore, s)


def plates():
    """Ombreiras de pedra com friso dourado, nos dois ombros."""
    for s, arm in ((1, "arm.L"), (-1, "arm.R")):
        sw = s * W
        H.frustum(arm, "gold", (sw * 0.58, 2.2, 0.0), (sw * 1.08, 1.82, 0.0), (0.22, 0.26), (0.29, 0.27), sides=6)
        H.frustum(arm, "plate", (sw * 0.58, 2.26, 0.0), (sw * 1.1, 1.9, 0.0), (0.23, 0.29), (0.32, 0.30), sides=6)


def make():
    torso()
    head()
    tail()
    arms()
    plates()


def joints():
    out = {}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, 1.9, 0.05), (s * SH_X, 1.35, 0.05))
        out[f"forearm.{side}"] = ((s * SH_X, 1.35, 0.05), (s * SH_X, 0.9, 0.05))
    return out


H.build("h03R", "wraith", PALETTE, make, joints())
