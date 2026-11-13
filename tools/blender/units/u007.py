"""Plague Bearer (u007): medido em artifacts/model-sheets/refs/u007/sheet.jpg. Gordo, avental, gancho com peso na mão direita (a
direita dele, esquerda da prancha): o peso é o ataque (golpe por cima).

    blender -b --factory-startup -P tools/blender/units/u007.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "skin": 0xE0A8A0, "skin_dk": 0xC48A86, "blood": 0x80323E, "apron": 0x776A45, "apron_dk": 0x5F5435,
    "boot": 0x45302A, "sole": 0x1F1511, "beard": 0x8A6448, "hose": 0x2F8A55, "metal": 0x808085,
    "metal_dk": 0x5A5A60, "fume": 0x4FB070,
}

HIP, KNEE, ANKLE, LEG_X = 1.0, 0.5, 0.17, 0.28
WAIST, NECK, TOP = 1.35, 2.15, 2.72
SH_X, SH_Y, EL_X, EL_Y, WR_X, WR_Y = 0.66, 2.02, 0.82, 1.46, 0.8, 0.98


def head():
    H.frustum("head", "skin", (0, 2.14, 0.08), (0, 2.5, 0.08), (0.2, 0.2), (0.22, 0.23), sides=8)
    H.frustum("head", "skin", (0, 2.5, 0.08), (0, 2.68, 0.06), (0.22, 0.23), (0.15, 0.15), sides=8)
    H.frustum("head", "beard", (0, 2.22, 0.24), (0, 2.46, 0.25), (0.16, 0.05), (0.2, 0.06), sides=6)      # máscara
    H.frustum("head", "beard", (0, 1.98, 0.26), (0, 2.24, 0.25), (0.05, 0.04), (0.16, 0.06), sides=6)     # barba em ponta
    H.frustum("head", "skin_dk", (0, 2.0, 0), (0, 2.22, 0), (0.3, 0.26), (0.34, 0.28), sides=8)           # pescoço grosso


def torso():
    H.frustum("pelvis", "apron", (0, 0.7, 0.12), (0, 1.0, 0.18), (0.3, 0.35), (0.5, 0.6), sides=8)
    H.frustum("pelvis", "apron", (0, 1.0, 0.18), (0, WAIST, 0.24), (0.5, 0.6), (0.62, 0.68), sides=8)
    H.frustum("spine", "apron", (0, WAIST, 0.24), (0, 1.62, 0.2), (0.62, 0.68), (0.6, 0.6), sides=8)
    H.frustum("spine", "apron", (0, 1.62, 0.2), (0, 1.88, 0.1), (0.6, 0.6), (0.5, 0.45), sides=8)
    H.frustum("spine", "skin", (0, 1.9, 0.02), (0, 2.2, 0.02), (0.46, 0.38), (0.26, 0.24), sides=8)    # ombros nus
    H.box("spine", "metal", (0, 1.4, 0.92), (0.34, 0.34, 0.06))                                         # placa na barriga
    H.box("spine", "blood", (0, 1.4, 0.89), (0.44, 0.42, 0.04))
    H.box("spine", "metal", (0, 1.4, 0.95), (0.3, 0.3, 0.03))
    pts = [(0.4, 1.74, 0.7), (0.2, 1.94, 0.74), (-0.1, 1.98, 0.74), (-0.4, 1.86, 0.7), (-0.56, 1.62, 0.62)]
    H.chain("spine", "hose", pts, [(0.055, 0.055)] * 5, sides=6)                                       # mangueira
    H.frustum("spine", "metal_dk", (0.4, 1.68, 0.68), (0.4, 1.8, 0.68), (0.1, 0.09), (0.09, 0.08), sides=6)
    # cano de fumaça no ombro esquerdo, com a nuvem verde
    H.frustum("spine", "metal_dk", (0.46, 2.18, -0.02), (0.46, 2.32, -0.02), (0.1, 0.1), (0.09, 0.09), sides=6)
    H.frustum("spine", "fume", (0.46, 2.32, -0.02), (0.48, 2.5, -0.02), (0.1, 0.1), (0.2, 0.2), sides=6)
    H.frustum("spine", "fume", (0.48, 2.5, -0.02), (0.5, 2.68, -0.02), (0.2, 0.2), (0.1, 0.1), sides=6)


def leg(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "apron", (x, KNEE - 0.06, 0.02), (x, HIP + 0.04, 0.02), (0.3, 0.32), (0.3, 0.34), sides=6)
    H.frustum(f"thigh.{side}", "apron_dk", (x, KNEE - 0.1, 0.02), (x, KNEE + 0.04, 0.02), (0.29, 0.31), (0.3, 0.32), sides=6)   # barra rasgada
    H.frustum(f"shin.{side}", "boot", (x, ANKLE - 0.02, 0), (x, KNEE, 0), (0.23, 0.24), (0.26, 0.26), sides=6)
    H.frustum(f"shin.{side}", "boot", (x, 0.26, 0), (x, 0.46, 0), (0.25, 0.26), (0.28, 0.28), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.03, -0.02), (x, ANKLE + 0.05, -0.02), (0.25, 0.27), (0.23, 0.25), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.13, 0.08), (x, 0.1, 0.46), (0.25, 0.14), (0.21, 0.08), sides=4)
    H.frustum(f"foot.{side}", "sole", (x, 0.02, -0.2), (x, 0.02, 0.48), (0.26, 0.022), (0.22, 0.022), sides=4)


def arm(s, side):
    tone = "blood" if side == "R" else "skin"
    H.frustum(f"arm.{side}", "skin", (s * SH_X, SH_Y + 0.05, 0), (s * SH_X, SH_Y - 0.1, 0), (0.2, 0.22), (0.3, 0.3), sides=8)  # ombro
    H.frustum(f"arm.{side}", "skin", (s * SH_X, SH_Y - 0.06, 0), (s * EL_X, EL_Y + 0.04, 0), (0.3, 0.3), (0.24, 0.25), sides=8)
    H.frustum(f"arm.{side}", "blood" if side == "L" else "skin", (s * (SH_X + 0.04), SH_Y - 0.02, 0.03), (s * (SH_X + 0.08), SH_Y - 0.3, 0.03), (0.26, 0.28), (0.29, 0.3), sides=6)
    H.frustum(f"forearm.{side}", tone, (s * EL_X, EL_Y + 0.05, 0), (s * WR_X, 1.12, 0.03), (0.26, 0.26), (0.22, 0.22), sides=8)
    H.frustum(f"forearm.{side}", tone, (s * WR_X, 1.14, 0.03), (s * WR_X, WR_Y - 0.08, 0.05), (0.22, 0.22), (0.25, 0.23), sides=8)   # punho grande
    H.frustum(f"forearm.{side}", tone, (s * WR_X, WR_Y - 0.06, 0.05), (s * WR_X, WR_Y - 0.28, 0.07), (0.25, 0.23), (0.17, 0.15), sides=6)


def hook():
    """Gancho (mão direita) e o peso de ferro pendurado: peça grande, no antebraço que bate."""
    pts = [(-WR_X, 1.1, 0.06), (-WR_X - 0.02, 0.72, 0.1), (-WR_X - 0.12, 0.52, 0.12), (-WR_X - 0.26, 0.58, 0.12), (-WR_X - 0.3, 0.72, 0.12)]
    H.chain("forearm.R", "metal", pts, [(0.055, 0.055)] * 3 + [(0.04, 0.04), (0.012, 0.012)], sides=6)
    H.frustum("forearm.R", "metal_dk", (-WR_X - 0.04, 0.54, 0.12), (-WR_X - 0.04, 0.42, 0.12), (0.04, 0.04), (0.04, 0.04), sides=4)
    H.frustum("forearm.R", "metal", (-WR_X - 0.04, 0.42, 0.12), (-WR_X - 0.04, 0.1, 0.12), (0.2, 0.2), (0.17, 0.17), sides=4)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        arm(s, side)
    hook()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * WR_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.06, 0.5))
    return out


H.build("u007", "biped", PALETTE, make, joints())
