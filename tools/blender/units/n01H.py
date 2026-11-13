"""Corrupted Treant (n01H): tronco fino de duas pernas, braços de galho com garras, cabeça-lanterna verde
dentro de um arco de galhos, capa de folhas roxas nas costas. Medido em artifacts/model-sheets/refs/n01H/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n01H.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "bark": 0x5E5A2E, "bark_dk": 0x2C2219, "bark_lt": 0x6F6A38, "claw": 0x3A2E1E, "rust": 0x9A4A2C,
    "glow": 0x5CFF30, "frame": 0x24190F, "leaf": 0x86466F, "leaf_dk": 0x57305A,
}
HIP, KNEE, ANKLE, WAIST, NECK, TOP = 1.0, 0.55, 0.12, 1.3, 1.95, 2.7
HIP_X, KNEE_X, FOOT_X = 0.17, 0.38, 0.48
SH_X, SH_Y, EL_X, EL_Y, WR_X, WR_Y = 0.38, 1.9, 0.70, 1.24, 0.84, 0.82


def head():
    H.frustum("head", "bark_dk", (0, 1.94, 0.18), (0, 2.34, 0.18), (0.17, 0.15), (0.2, 0.17), sides=6)
    H.frustum("head", "bark", (0, 2.3, 0.18), (0, 2.38, 0.18), (0.22, 0.19), (0.14, 0.12), sides=6)
    H.frustum("head", "glow", (0, 2.02, 0.31), (0, 2.28, 0.3), (0.085, 0.04), (0.09, 0.04), sides=6)
    H.frustum("head", "rust", (0, 1.88, 0.1), (0, 2.02, 0.12), (0.33, 0.3), (0.24, 0.22), sides=8)      # gola
    H.frustum("head", "frame", (0, 2.43, 0), (0, 2.6, 0), (0.5, 0.15), (0.3, 0.14), sides=4)           # trave do arco
    H.frustum("head", "frame", (0, 2.58, 0), (0, TOP, 0), (0.3, 0.15), (0.06, 0.12), sides=4)          # cumeeira
    for s in (-1, 1):       # montantes do arco, do ombro até a trave
        H.chain(["spine", "head", "head"], "frame", [(s * 0.34, 1.9, 0), (s * 0.33, 2.15, 0), (s * 0.3, 2.35, 0), (s * 0.27, 2.5, 0)],
                [(0.12, 0.11), (0.1, 0.1), (0.09, 0.09), (0.08, 0.08)], sides=6)
        H.frustum("head", "frame", (s * 0.36, 2.2, 0), (s * 0.5, 2.3, 0), (0.06, 0.06), (0.03, 0.03), sides=4)    # galho lateral


def leaf(bone, tone, x, top, bottom, z0, z1, half=0.16):
    H.frustum(bone, tone, (x, top, z0), (x, bottom, z1), (half, 0.07), (0.03, 0.03), sides=4)


def cape():
    rows = ((1.95, 1.5, "spine", (-0.3, 0.0, 0.3)), (1.7, 1.15, "spine", (-0.45, -0.15, 0.15, 0.45)),
            (1.35, 0.8, "pelvis", (-0.35, -0.12, 0.12, 0.35)), (1.05, 0.62, "pelvis", (-0.18, 0.18)))
    for i, (top, bottom, bone, xs) in enumerate(rows):
        for j, x in enumerate(xs):
            leaf(bone, "leaf" if (i + j) % 2 else "leaf_dk", x, top, bottom, -0.2 - 0.04 * i, -0.4 - 0.07 * i)
    for s in (-1, 1):       # folhas nas laterais do peito
        leaf("spine", "leaf", s * 0.27, 1.8, 1.3, 0.14, 0.1, half=0.1)


def torso():
    H.frustum("spine", "bark", (0, WAIST - 0.05, 0.02), (0, 1.75, 0.03), (0.26, 0.25), (0.36, 0.27), sides=8)
    H.frustum("spine", "bark", (0, 1.75, 0.03), (0, 2.0, 0.05), (0.36, 0.27), (0.24, 0.22), sides=8)
    H.frustum("spine", "bark_lt", (0, 1.4, 0.2), (0, 1.8, 0.2), (0.07, 0.03), (0.1, 0.03), sides=4)
    H.frustum("pelvis", "bark", (0, 0.88, 0), (0, 1.15, 0), (0.3, 0.2), (0.24, 0.2), sides=8)
    H.frustum("pelvis", "bark", (0, 1.15, 0), (0, WAIST, 0.02), (0.24, 0.2), (0.27, 0.21), sides=8)


def toes(side, x):
    f = f"foot.{side}"
    s = 1 if side == "L" else -1
    H.frustum(f, "bark_dk", (x, 0.02, -0.05), (x, 0.26, -0.02), (0.22, 0.2), (0.16, 0.15), sides=8)
    for dx, dz in ((-0.2, 0.36), (0.0, 0.5), (0.2, 0.36)):
        H.chain(f, "bark_dk", [(x, 0.1, 0.02), (x + s * dx * 0.6, 0.07, dz * 0.55), (x + s * dx, 0.03, dz)],
                [(0.1, 0.08), (0.075, 0.05), (0.03, 0.02)], sides=4)
    H.chain(f, "bark_dk", [(x, 0.1, -0.05), (x, 0.06, -0.25)], [(0.1, 0.07), (0.04, 0.03)], sides=4)


def leg(s, side):
    H.frustum(f"thigh.{side}", "bark", (s * KNEE_X, KNEE - 0.04, 0.03), (s * (HIP_X + 0.02), HIP + 0.1, 0), (0.15, 0.22), (0.22, 0.26), sides=6)
    H.frustum(f"shin.{side}", "bark", (s * FOOT_X, ANKLE + 0.02, 0), (s * KNEE_X, KNEE + 0.03, 0.03), (0.17, 0.22), (0.14, 0.2), sides=6)
    H.frustum(f"shin.{side}", "bark_dk", (s * FOOT_X, ANKLE, 0), (s * (FOOT_X - 0.02), 0.3, 0), (0.2, 0.22), (0.15, 0.19), sides=6)
    toes(side, s * FOOT_X)


def claws(side, s):
    x, f = s * WR_X, f"forearm.{side}"
    H.frustum(f, "bark", (x, WR_Y + 0.08, 0.02), (x, WR_Y - 0.14, 0.04), (0.11, 0.1), (0.15, 0.12), sides=6)       # palma
    for dx, dz, ty in ((0.2, 0.02, 0.44), (0.0, 0.1, 0.36), (-0.18, 0.04, 0.46)):
        H.chain(f, "claw", [(x + s * dx * 0.2, WR_Y - 0.1, 0.04), (x + s * dx * 0.7, 0.6, dz), (x + s * dx, ty, dz + 0.06)],
                [(0.06, 0.055), (0.045, 0.04), (0.012, 0.012)], sides=4)


def arm(s, side):
    H.frustum(f"arm.{side}", "bark", (s * SH_X, SH_Y + 0.06, 0), (s * (SH_X + 0.12), 1.62, 0.01), (0.15, 0.15), (0.14, 0.14), sides=6)
    H.frustum(f"arm.{side}", "bark", (s * (SH_X + 0.12), 1.62, 0.01), (s * EL_X, EL_Y - 0.02, 0.02), (0.14, 0.14), (0.1, 0.1), sides=6)
    H.frustum(f"forearm.{side}", "bark", (s * EL_X, EL_Y + 0.04, 0.02), (s * (EL_X + 0.08), 1.0, 0.03), (0.12, 0.12), (0.09, 0.09), sides=6)
    H.frustum(f"forearm.{side}", "bark", (s * (EL_X + 0.08), 1.0, 0.03), (s * WR_X, WR_Y, 0.03), (0.09, 0.09), (0.11, 0.1), sides=6)
    H.frustum(f"arm.{side}", "bark_dk", (s * (EL_X - 0.04), 1.4, 0), (s * (EL_X + 0.14), 1.5, 0), (0.05, 0.05), (0.02, 0.02), sides=4)   # galho
    claws(side, s)


def make():
    head()
    torso()
    cape()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        arm(s, side)


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)), "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * WR_X, WR_Y, 0.03))
        out[f"thigh.{side}"] = ((s * HIP_X, HIP, 0), (s * KNEE_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * FOOT_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * FOOT_X, ANKLE, 0), (s * FOOT_X, 0.06, 0.55))
    return out


H.build("n01H", "biped", PALETTE, make, joints())
