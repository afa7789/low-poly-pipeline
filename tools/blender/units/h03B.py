"""Crusader (h03B): cavaleiro com cutelo sobre cavalo, medido em artifacts/model-sheets/refs/h03B/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/h03B.py -- <out.glb>

Escala da prancha: ~408 px por metro (chao y=918 px, cavalo com o dorso a 1.26 m).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "horse": 0xB5895A, "horse_dk": 0x9C7248, "mane": 0x1B1A1C, "mask": 0x4A4E57, "muzzle": 0x6B4A33,
    "eye": 0xC98B3C, "hoof": 0xB9B9BE, "coat": 0x84202E, "coat_dk": 0x6A1824, "pad": 0xB98A4A,
    "leather": 0x5E4330, "breech": 0x5A4231, "boot": 0x19181B, "iron": 0x8A8C92, "blue": 0x3F4FC0,
    "skin": 0xD0906E, "helmet": 0x4C5058, "steel": 0x565A63, "steel_dk": 0x3C3F46, "wood": 0x6B4A33,
}

BACK = 1.26                      # altura do dorso
HIND_Z, FORE_Z = -0.48, 0.5      # pernas
SEAT = (0.0, 1.25, 0.06)


def neck_w(p):
    """O pescoco acompanha o tronco na base e a cabeca no topo."""
    w = min(1.0, max(0.0, (p[2] - 0.5) / 0.42))
    return {"spine.2": 1 - w, "head": w}


def mount():
    # tronco: garupa (spine.1) e peito fundo (spine.2)
    H.frustum("spine.1", "horse", (0, 0.97, -0.64), (0, 0.96, 0.02), (0.25, 0.29), (0.235, 0.3), sides=8)
    H.frustum("spine.2", "horse", (0, 0.96, -0.02), (0, 0.95, 0.62), (0.235, 0.3), (0.22, 0.31), sides=8)
    H.frustum("spine.2", "horse", (0, 0.9, 0.5), (0, 0.9, 0.72), (0.2, 0.3), (0.12, 0.2), sides=8)
    neck = H.frustum("spine.2", "horse", (0, 1.06, 0.5), (0, 1.35, 0.93), (0.17, 0.2), (0.1, 0.1), sides=8)
    H.soft(neck, neck_w)
    H.soft(H.frustum("spine.2", "mane", (0, 1.3, 0.4), (0, 1.56, 0.9), (0.035, 0.05), (0.03, 0.05), sides=4), neck_w)
    # cabeca: mascara de ferro sobre o focinho, olhos, orelhas
    H.frustum("head", "horse", (0, 1.51, 0.94), (0, 1.17, 1.2), (0.11, 0.13), (0.075, 0.1), sides=6)
    H.frustum("head", "mask", (0, 1.48, 0.96), (0, 1.23, 1.16), (0.12, 0.14), (0.085, 0.108), sides=6)
    H.frustum("head", "muzzle", (0, 1.23, 1.16), (0, 1.13, 1.25), (0.088, 0.1), (0.07, 0.07), sides=6)
    for s in (-1, 1):
        H.frustum("head", "eye", (s * 0.115, 1.37, 1.04), (s * 0.125, 1.39, 1.06), (0.025, 0.03), (0.02, 0.025), sides=4)
        H.frustum("head", "horse", (s * 0.07, 1.51, 0.93), (s * 0.08, 1.74, 0.9), (0.04, 0.035), (0.012, 0.012), sides=4)
    # cauda preta pendurada
    H.frustum("tail.1", "mane", (0, 1.16, -0.6), (0, 0.9, -0.8), (0.07, 0.09), (0.09, 0.1), sides=6)
    H.frustum("tail.2", "mane", (0, 0.9, -0.8), (0, 0.5, -0.86), (0.09, 0.1), (0.05, 0.07), sides=6)
    # manta vermelha com debrum azul, sela
    H.box("spine.2", "coat_dk", (0, BACK + 0.01, 0.0), (0.5, 0.05, 0.62))
    H.box("spine.2", "leather", (0, BACK + 0.06, -0.02), (0.3, 0.07, 0.4))
    for s in (-1, 1):
        H.frustum("spine.2", "coat_dk", (s * 0.255, 1.24, 0.0), (s * 0.255, 0.85, 0.0), (0.022, 0.3), (0.022, 0.28), sides=4)
        H.frustum("spine.2", "blue", (s * 0.26, 0.87, 0.0), (s * 0.26, 0.82, 0.0), (0.022, 0.29), (0.022, 0.27), sides=4)
        H.frustum("spine.2", "leather", (s * 0.262, 1.24, 0.0), (s * 0.262, 1.12, 0.0), (0.022, 0.3), (0.022, 0.3), sides=4)
    legs()


def legs():
    for s, front, hind in ((1, "leg1", "leg3"), (-1, "leg2", "leg4")):
        for tag, z in ((front, FORE_Z), (hind, HIND_Z)):
            fwd = tag == front
            top = (0.1, 0.17) if fwd else (0.11, 0.24)
            H.frustum(f"{tag}.upper", "horse", (s * 0.17, 1.02 if fwd else 1.08, z), (s * 0.13, 0.52, z), top, (0.065, 0.085), sides=6)
            H.frustum(f"{tag}.lower", "horse", (s * 0.13, 0.54, z), (s * 0.13, 0.09, z), (0.062, 0.075), (0.055, 0.065), sides=6)
            H.frustum(f"{tag}.lower", "hoof", (s * 0.13, 0.1, z), (s * 0.13, 0.0, z + 0.01), (0.058, 0.07), (0.075, 0.095), sides=6)


def rider_body():
    H.frustum("rider.spine", "coat", (0, 1.25, 0.06), (0, 1.74, 0.06), (0.2, 0.14), (0.27, 0.15), sides=8)
    H.frustum("rider.spine", "leather", (0, 1.36, 0.06), (0, 1.45, 0.06), (0.236, 0.165), (0.232, 0.162), sides=8)
    H.frustum("rider.spine", "coat_dk", (0, 1.7, 0.06), (0, 1.86, 0.07), (0.15, 0.14), (0.12, 0.12), sides=8)
    # saia do casaco sobre a sela e os flancos, com barra de couro
    H.frustum("spine.2", "coat", (0, 1.3, 0.04), (0, 0.97, 0.04), (0.25, 0.2), (0.36, 0.27), sides=8)
    H.frustum("spine.2", "leather", (0, 1.0, 0.04), (0, 0.9, 0.04), (0.37, 0.275), (0.385, 0.29), sides=8)
    # cabeca: capacete de aco, rosto, barba, cabelo
    H.frustum("rider.head", "skin", (0, 1.76, 0.07), (0, 1.94, 0.07), (0.1, 0.11), (0.105, 0.115), sides=6)
    H.box("rider.head", "mane", (0, 1.8, 0.17), (0.17, 0.12, 0.05))
    H.box("rider.head", "mane", (0, 1.9, 0.0), (0.24, 0.2, 0.07))
    H.frustum("rider.head", "helmet", (0, 1.93, 0.06), (0, 1.96, 0.06), (0.18, 0.2), (0.16, 0.18), sides=8)
    H.frustum("rider.head", "helmet", (0, 1.96, 0.06), (0, 2.08, 0.06), (0.15, 0.16), (0.08, 0.09), sides=8)
    for s, side in ((1, "L"), (-1, "R")):
        # ombreira, braco, antebraco
        H.frustum("rider.spine", "pad", (s * 0.17, 1.82, 0.06), (s * 0.37, 1.7, 0.06), (0.06, 0.15), (0.07, 0.16), sides=4)
        H.frustum(f"rider.arm.{side}", "coat", (s * 0.27, 1.7, 0.06), (s * 0.34, 1.33, 0.08), (0.08, 0.085), (0.065, 0.07), sides=6)
    H.frustum("rider.forearm.L", "coat", (0.34, 1.33, 0.08), (0.2, 1.4, 0.3), (0.065, 0.065), (0.055, 0.055), sides=6)
    H.frustum("rider.forearm.L", "skin", (0.2, 1.4, 0.3), (0.18, 1.4, 0.38), (0.05, 0.05), (0.045, 0.045), sides=6)
    H.frustum("rider.forearm.R", "coat", (-0.34, 1.33, 0.06), (-0.38, 1.2, -0.02), (0.065, 0.065), (0.055, 0.055), sides=6)
    H.frustum("rider.forearm.R", "skin", (-0.38, 1.22, -0.02), (-0.39, 1.1, 0.0), (0.055, 0.055), (0.05, 0.05), sides=6)


def rider_legs():
    for s in (-1, 1):
        H.frustum("spine.2", "breech", (s * 0.17, 1.25, 0.0), (s * 0.28, 1.0, 0.22), (0.1, 0.12), (0.08, 0.09), sides=6)
        H.frustum("spine.2", "boot", (s * 0.28, 1.02, 0.22), (s * 0.3, 0.7, 0.08), (0.08, 0.09), (0.065, 0.07), sides=6)
        H.frustum("spine.2", "boot", (s * 0.3, 0.7, 0.04), (s * 0.3, 0.66, 0.26), (0.07, 0.05), (0.06, 0.03), sides=4)
        H.frustum("spine.2", "iron", (s * 0.3, 0.63, 0.0), (s * 0.3, 0.63, 0.27), (0.075, 0.015), (0.065, 0.015), sides=4)


def cleaver():
    H.frustum("rider.forearm.R", "wood", (-0.38, 1.27, -0.02), (-0.44, 1.0, 0.06), (0.03, 0.03), (0.03, 0.03), sides=4)
    H.frustum("rider.forearm.R", "steel_dk", (-0.44, 1.06, 0.05), (-0.49, 0.9, 0.12), (0.075, 0.06), (0.075, 0.06), sides=4)
    H.frustum("rider.forearm.R", "steel", (-0.49, 0.92, 0.12), (-0.62, 0.5, 0.3), (0.1, 0.03), (0.105, 0.03), sides=4)
    H.frustum("rider.forearm.R", "steel_dk", (-0.44, 1.12, 0.0), (-0.4, 1.2, -0.1), (0.03, 0.03), (0.025, 0.025), sides=4)


def make():
    mount()
    rider_body()
    rider_legs()
    cleaver()


def joints():
    out = {"head": ((0, 1.3, 0.7), (0, 1.4, 1.1)),
           "tail.1": ((0, 1.16, -0.6), (0, 0.9, -0.8)), "tail.2": ((0, 0.9, -0.8), (0, 0.5, -0.86)),
           "rider.spine": (SEAT, (0, 1.74, 0.06)), "rider.head": ((0, 1.74, 0.06), (0, 2.08, 0.06))}
    for s, side, f, h in ((1, "L", "leg1", "leg3"), (-1, "R", "leg2", "leg4")):
        for tag, z in ((f, FORE_Z), (h, HIND_Z)):
            out[f"{tag}.upper"] = ((s * 0.17, 1.0, z), (s * 0.13, 0.55, z))
            out[f"{tag}.lower"] = ((s * 0.13, 0.55, z), (s * 0.13, 0.06, z))
        out[f"rider.arm.{side}"] = ((s * 0.27, 1.7, 0.06), (s * 0.34, 1.33, 0.06))
        out[f"rider.forearm.{side}"] = ((s * 0.34, 1.33, 0.06), (s * 0.34, 1.08, 0.06))
    return out


H.build("h03B", "mounted", PALETTE, make, joints())
