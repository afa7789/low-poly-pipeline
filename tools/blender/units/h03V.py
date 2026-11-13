"""Master Of Elements (h03V): medido em artifacts/model-sheets/refs/h03V/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/h03V.py -- <out.glb>
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "stone": 0x4B4543, "stone_dk": 0x36322F, "plate": 0x3C3F46, "boot": 0x6B4332, "boot_dk": 0x553425,
    "lava": 0xFF9A2E, "flame": 0xFF7A1A, "flame_hi": 0xFFD23C, "ring": 0xBFE9EE, "ring_blue": 0x3C4F86,
    "wood": 0x6E5545, "head": 0x5A4638, "glass": 0xF2B84A, "bolt": 0x7FE7FF, "brass": 0x8A6A44,
}

HIP, KNEE, ANKLE, LEG_X = 1.05, 0.62, 0.30, 0.22
WAIST, NECK, TOP = 1.32, 1.90, 2.75
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.50, 1.74, 0.58, 1.34, 1.08
RING_Y, RING_R = 1.97, 0.47


def head():
    # obelisco no lugar da cabeça, chama no topo, anel de halo em volta da base
    H.frustum("head", "stone", (0, 1.88, 0), (0, 2.45, 0), (0.17, 0.15), (0.14, 0.12), sides=4)
    H.frustum("head", "stone", (0, 2.45, 0), (0, 2.70, 0), (0.14, 0.12), (0.08, 0.07), sides=4)
    H.frustum("head", "lava", (0, 2.70, 0), (0, 2.74, 0), (0.09, 0.08), (0.09, 0.08), sides=4)
    H.frustum("head", "flame", (0, 2.74, 0), (0, 2.86, 0), (0.1, 0.08), (0.05, 0.04), sides=6)
    H.frustum("head", "flame_hi", (0, 2.78, 0), (0, 2.98, 0), (0.06, 0.05), (0.0, 0.0), sides=4)
    pts = [(RING_R * math.sin(a), RING_Y, RING_R * math.cos(a)) for a in (i * math.pi / 6 for i in range(13))]
    for i in range(12):
        tone = "ring_blue" if 1 <= i <= 3 else "ring"
        H.frustum("head", tone, pts[i], pts[i + 1], (0.045, 0.07), (0.045, 0.07), sides=4)


def torso():
    H.frustum("spine", "stone", (0, 1.30, 0), (0, 1.62, 0), (0.34, 0.27), (0.42, 0.31), sides=8)     # peito em V
    H.frustum("spine", "stone", (0, 1.62, 0), (0, 1.94, 0), (0.42, 0.31), (0.30, 0.24), sides=8)
    H.frustum("spine", "lava", (0, 1.60, 0.2), (0, 1.62, 0.32), (0.3, 0.02), (0.3, 0.02), sides=4)
    H.frustum("spine", "brass", (0, 1.76, 0.30), (0, 1.76, 0.38), (0.09, 0.09), (0.09, 0.09), sides=8)  # manômetro
    H.frustum("spine", "glass", (0, 1.46, 0.27), (0, 1.46, 0.34), (0.17, 0.11), (0.15, 0.1), sides=4)   # janela da fornalha
    H.frustum("spine", "plate", (0, 1.48, -0.25), (0, 1.90, -0.33), (0.36, 0.05), (0.32, 0.06), sides=4)  # placa das costas
    for s in (-1, 1):       # ombreiras com chama
        H.frustum("spine", "plate", (s * 0.36, 1.84, 0), (s * 0.62, 1.78, 0), (0.18, 0.3), (0.12, 0.26), sides=4)
        H.frustum("spine", "lava", (s * 0.56, 1.86, 0), (s * 0.62, 1.88, 0), (0.1, 0.2), (0.1, 0.2), sides=4)
        H.frustum("spine", "flame", (s * 0.56, 1.88, 0), (s * 0.58, 2.06, 0), (0.1, 0.1), (0.04, 0.04), sides=6)
        H.frustum("spine", "flame_hi", (s * 0.56, 1.9, 0), (s * 0.58, 2.2, 0), (0.05, 0.05), (0.0, 0.0), sides=4)


def hips():
    H.frustum("pelvis", "stone_dk", (0, 0.92, 0), (0, WAIST + 0.02, 0), (0.42, 0.28), (0.36, 0.26), sides=8)
    H.frustum("pelvis", "lava", (0, WAIST - 0.02, 0.2), (0, WAIST + 0.02, 0.3), (0.34, 0.01), (0.34, 0.01), sides=4)
    for s in (-1, 1):       # bolsas de caixa nos quadris
        H.frustum("pelvis", "boot_dk", (s * 0.50, 0.84, 0), (s * 0.50, 1.28, 0), (0.07, 0.18), (0.09, 0.2), sides=4)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * LEG_X
        H.frustum(f"thigh.{side}", "stone_dk", (x, KNEE - 0.04, 0), (x, HIP + 0.05, 0), (0.17, 0.19), (0.23, 0.24), sides=6)
        H.frustum(f"thigh.{side}", "stone", (x, KNEE + 0.02, 0.1), (x, KNEE + 0.14, 0.14), (0.1, 0.07), (0.1, 0.07), sides=4)
        H.frustum(f"shin.{side}", "stone_dk", (x, ANKLE + 0.05, 0), (x, KNEE + 0.04, 0), (0.17, 0.17), (0.17, 0.18), sides=6)
        # bota de rocha: sobe larga, cunha do pé com dedos de pedra
        H.frustum(f"shin.{side}", "boot", (x, 0.28, 0), (x, 0.66, 0), (0.27, 0.27), (0.22, 0.24), sides=6)
        H.frustum(f"shin.{side}", "boot_dk", (x, 0.58, 0), (x, 0.68, 0), (0.25, 0.25), (0.23, 0.23), sides=6)
        H.frustum(f"foot.{side}", "boot", (x, 0.04, -0.12), (x, 0.38, -0.08), (0.30, 0.3), (0.24, 0.26), sides=6)
        H.frustum(f"foot.{side}", "boot", (x, 0.10, 0.1), (x, 0.08, 0.58), (0.3, 0.17), (0.28, 0.07), sides=6)
        H.frustum(f"foot.{side}", "lava", (x, 0.30, -0.05), (x, 0.32, 0.2), (0.17, 0.01), (0.12, 0.01), sides=4)
        for dx in (-0.17, 0, 0.17):
            H.frustum(f"foot.{side}", "boot_dk", (x + dx, 0.06, 0.46), (x + dx, 0.07, 0.68), (0.07, 0.07), (0.07, 0.04), sides=4)


def arms():
    for s, side in ((1, "L"), (-1, "R")):
        H.frustum(f"arm.{side}", "stone", (s * SH_X, SH_Y + 0.08, 0), (s * EL_X, EL_Y - 0.02, 0.04), (0.2, 0.21), (0.15, 0.16), sides=6)
        H.frustum(f"forearm.{side}", "stone", (s * EL_X, EL_Y + 0.02, 0.04), (s * EL_X, WR_Y + 0.1, 0.14), (0.16, 0.17), (0.2, 0.21), sides=6)
        H.frustum(f"forearm.{side}", "stone_dk", (s * EL_X, WR_Y + 0.12, 0.14), (s * EL_X, WR_Y - 0.14, 0.16), (0.21, 0.21), (0.19, 0.19), sides=4)
        H.frustum(f"forearm.{side}", "lava", (s * EL_X, WR_Y + 0.1, 0.16), (s * EL_X, WR_Y + 0.12, 0.16), (0.2, 0.2), (0.2, 0.2), sides=4)
    H.frustum("forearm.L", "bolt", (EL_X + 0.1, EL_Y - 0.1, 0.1), (EL_X + 0.18, WR_Y, 0.2), (0.03, 0.03), (0.02, 0.02), sides=4)


def staff():
    # cajado na mão direita (forearm.R), à frente do corpo, vertical
    x, z = -0.62, 0.5
    H.frustum("forearm.R", "wood", (x, 0.0, z), (x, 2.1, z), (0.045, 0.045), (0.045, 0.045), sides=6)
    H.frustum("forearm.R", "head", (x, 2.1, z), (x, 2.26, z), (0.14, 0.14), (0.2, 0.2), sides=6)
    H.frustum("forearm.R", "head", (x, 2.26, z), (x, 2.42, z), (0.2, 0.2), (0.1, 0.1), sides=6)
    H.frustum("forearm.R", "lava", (x, 2.26, z), (x, 2.28, z), (0.21, 0.21), (0.21, 0.21), sides=6)


def make():
    head()
    torso()
    hips()
    legs()
    arms()
    staff()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.08, 0.5))
    return out


H.build("h03V", "biped", PALETTE, make, joints())
