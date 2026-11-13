"""Footman (hfoo): medido em artifacts/model-sheets/refs/hfoo/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/hfoo.py -- <out.glb>
"""
import pathlib
import sys

from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "tunic": 0x565A4C, "tunic_dk": 0x464A3F, "breech": 0x40443A, "helmet": 0x6C6F7A, "helmet_dk": 0x54565F,
    "strap": 0x6E4A32, "pouch": 0x4E3F2E, "gold": 0xCFA23C, "skin": 0x8E6F62, "blue": 0x4A70C8,
    "puttee": 0xB8A87E, "puttee_dk": 0x93845E, "boot": 0x4A352E, "sole": 0x1F1D1F, "black": 0x17161A, "eye": 0xFFD23C,
    "wood": 0x5A3A26, "steel": 0x3E4249, "blade": 0xD9D6CC,
}

# juntas (metros do biped), medidas na vista de frente/lado da prancha
HIP, KNEE, ANKLE, LEG_X, KNEE_X = 1.08, 0.50, 0.17, 0.23, 0.30
WAIST, NECK, TOP = 1.36, 2.10, 2.70
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.56, 2.02, 0.68, 1.50, 1.04
SKIRT_MID = (0.92 + WAIST - 0.05) / 2


def hem(p):
    """A barra da saia do casaco acompanha a coxa do seu lado; o topo fica na pelve."""
    if p[1] > SKIRT_MID:
        return {"pelvis": 1.0}
    return {"pelvis": 0.45, "thigh.L" if p[0] > 0 else "thigh.R": 0.55}


def make():
    # --- cabeça: capacete de aba larga, faixa preta dos olhos, gola azul alta
    H.frustum("head", "skin", (0, 2.08, 0.02), (0, 2.42, 0.02), (0.19, 0.2), (0.21, 0.22), sides=6)
    H.box("head", "black", (0, 2.31, 0.19), (0.36, 0.11, 0.1))
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.09, 2.31, 0.245), (0.07, 0.045, 0.02))
    H.frustum("head", "blue", (0, 2.04, 0), (0, 2.22, 0), (0.25, 0.24), (0.3, 0.28), sides=8)
    H.frustum("head", "helmet_dk", (0, 2.36, 0), (0, 2.42, 0), (0.45, 0.43), (0.37, 0.35), sides=8)       # aba
    H.frustum("head", "helmet", (0, 2.42, 0), (0, 2.60, 0), (0.29, 0.28), (0.24, 0.23), sides=8)          # copa
    H.frustum("head", "helmet", (0, 2.60, 0), (0, 2.70, 0), (0.24, 0.23), (0.12, 0.12), sides=8)
    # --- tronco em barril, ombros caídos
    H.frustum("spine", "tunic", (0, WAIST - 0.04, 0), (0, 2.0, 0), (0.45, 0.37), (0.54, 0.39), sides=8)
    H.frustum("spine", "tunic", (0, 2.0, 0), (0, 2.15, 0), (0.54, 0.39), (0.3, 0.27), sides=8)
    for s in (-1, 1):       # o X das correias, na frente e nas costas, com as cartucheiras de tampa dourada
        H.frustum("spine", "strap", (s * 0.42, 2.07, 0.375), (-s * 0.38, 1.42, 0.42), (0.085, 0.03), (0.085, 0.03), sides=4)
        H.frustum("spine", "strap", (s * 0.42, 2.07, -0.375), (-s * 0.38, 1.42, -0.42), (0.085, 0.03), (0.085, 0.03), sides=4)
        H.frustum("spine", "strap", (s * 0.42, 2.08, 0.375), (s * 0.42, 2.08, -0.375), (0.085, 0.035), (0.085, 0.035), sides=4)
        top, low = Vector((s * 0.42, 2.07, 0.375)), Vector((-s * 0.38, 1.42, 0.42))
        for t0, t1 in ((0.12, 0.34), (0.62, 0.86)):      # cartucheiras deitadas na correia: o X continua à vista
            a, b = top.lerp(low, t0), top.lerp(low, t1)
            lift = Vector((0, 0, 0.05))
            H.frustum("spine", "gold", a + lift, a.lerp(b, 0.28) + lift, (0.115, 0.05), (0.115, 0.05), sides=4)
            H.frustum("spine", "pouch", a.lerp(b, 0.28) + lift, b + lift, (0.125, 0.055), (0.125, 0.055), sides=4)
    # --- cinto, fivela, saia do casaco (barra macia: acompanha as coxas), calça
    H.frustum("pelvis", "strap", (0, WAIST - 0.09, 0), (0, WAIST + 0.07, 0), (0.475, 0.39), (0.475, 0.39), sides=8)
    H.box("pelvis", "gold", (0, WAIST - 0.01, 0.395), (0.2, 0.17, 0.04))
    H.box("pelvis", "strap", (0, WAIST - 0.01, 0.41), (0.09, 0.08, 0.03))
    skirt = H.frustum("pelvis", "tunic", (0, 0.92, 0), (0, WAIST - 0.05, 0), (0.58, 0.45), (0.46, 0.38), sides=8)
    H.soft(skirt, hem)
    H.frustum("pelvis", "breech", (0, 0.84, 0), (0, 1.12, 0), (0.4, 0.32), (0.44, 0.36), sides=8)
    for s, side in ((1, "L"), (-1, "R")):
        # perna: calça larga no joelho, perneira enfaixada, bota em cunha sobre a sola
        H.frustum(f"thigh.{side}", "breech", (s * KNEE_X, KNEE - 0.04, 0), (s * LEG_X, HIP + 0.04, 0), (0.285, 0.3), (0.23, 0.27), sides=6)
        H.frustum(f"shin.{side}", "puttee", (s * KNEE_X, ANKLE - 0.02, 0), (s * KNEE_X, KNEE + 0.02, 0), (0.18, 0.19), (0.2, 0.21), sides=6)
        for y0 in (0.24, 0.36):         # as faixas da perneira
            H.frustum(f"shin.{side}", "puttee_dk", (s * KNEE_X, y0, 0), (s * KNEE_X, y0 + 0.05, 0), (0.195, 0.205), (0.2, 0.21), sides=6)
        H.frustum(f"foot.{side}", "boot", (s * KNEE_X, 0.03, -0.02), (s * KNEE_X, ANKLE + 0.04, -0.02), (0.19, 0.22), (0.18, 0.2), sides=6)
        H.frustum(f"foot.{side}", "boot", (s * KNEE_X, 0.11, 0.06), (s * KNEE_X, 0.085, 0.42), (0.19, 0.1), (0.165, 0.06), sides=4)
        H.frustum(f"foot.{side}", "sole", (s * KNEE_X, 0.02, -0.2), (s * KNEE_X, 0.02, 0.44), (0.205, 0.022), (0.175, 0.022), sides=4)
        # braço comprido e pesado: ombro em cunha, manga larga escura no antebraço, punho grande
        H.frustum(f"arm.{side}", "tunic", (s * (SH_X + 0.03), SH_Y + 0.04, 0), (s * EL_X, EL_Y - 0.03, 0), (0.21, 0.25), (0.18, 0.2), sides=6)
        H.frustum(f"forearm.{side}", "tunic_dk", (s * EL_X, EL_Y + 0.04, 0), (s * EL_X, WR_Y, 0.04), (0.19, 0.21), (0.18, 0.19), sides=6)
        H.frustum(f"forearm.{side}", "skin", (s * EL_X, WR_Y + 0.03, 0.04), (s * EL_X, WR_Y - 0.24, 0.06), (0.155, 0.18), (0.14, 0.16), sides=6)
    # --- fuzil com baioneta como na prancha: mão esquerda, em pé, inclinado à frente
    butt, tip = Vector((EL_X + 0.03, 0.3, -0.3)), Vector((EL_X + 0.03, 3.0, 1.1))
    grip, muzzle = butt.lerp(tip, 0.5), butt.lerp(tip, 0.8)
    H.frustum("forearm.L", "wood", butt, grip, (0.085, 0.13), (0.065, 0.08), sides=4)
    H.frustum("forearm.L", "steel", grip, muzzle, (0.055, 0.06), (0.045, 0.045), sides=6)
    H.frustum("forearm.L", "blade", muzzle, tip, (0.03, 0.065), (0.005, 0.01), sides=4)


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * SH_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * KNEE_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * KNEE_X, ANKLE, 0), (s * KNEE_X, 0.06, 0.5))
    return out


H.build("hfoo", "biped", PALETTE, make, joints())
