"""Paladin (h03C): cavaleiro de capacete de aco, ombreiras de oliva, facao e estandarte nas costas, sobre cavalo robusto.

    blender -b --factory-startup -P tools/blender/units/h03C.py -- <out.glb>

Base de h03B (Crusader); cavalo mais fundo e grosso, cavaleiro aumentado alem da prancha (assento->capacete ~47 % da altura).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "horse": 0xC0834F, "horse_dk": 0xA06A3E, "mane": 0x1B1A1C, "mask": 0x4A4E57, "muzzle": 0xB5764A,
    "eye": 0xE0A040, "hoof": 0xB9B9C8, "coat": 0x8A1E3A, "coat_dk": 0x6A1830, "olive": 0x6F7240, "pad": 0x8A7A3C,
    "leather": 0x5E4330, "boot": 0x19181B, "iron": 0x8A8C92, "cream": 0xE8D2A8, "skin": 0xD0906E,
    "helmet": 0x555A64, "steel": 0x676B76, "steel_dk": 0x3C3F46, "wood": 0x6B4A33, "wrap": 0x7C8048,
    "seal": 0xC02040,
}

BACK = 1.26
HIND_Z, FORE_Z = -0.5, 0.52
SEAT = (0.0, 1.22, 0.06)
TOP = 2.46


def neck_w(p):
    w = min(1.0, max(0.0, (p[2] - 0.5) / 0.42))
    return {"spine.2": 1 - w, "head": w}


def body():
    H.frustum("spine.1", "horse", (0, 0.98, -0.7), (0, 0.98, 0.0), (0.27, 0.31), (0.32, 0.34), sides=8)
    H.frustum("spine.2", "horse", (0, 0.97, -0.02), (0, 0.97, 0.66), (0.32, 0.34), (0.27, 0.36), sides=8)
    H.frustum("spine.2", "horse", (0, 0.92, 0.5), (0, 0.95, 0.8), (0.27, 0.34), (0.15, 0.22), sides=8)
    neck = H.frustum("spine.2", "horse", (0, 1.05, 0.5), (0, 1.38, 0.95), (0.21, 0.26), (0.12, 0.14), sides=8)
    H.soft(neck, neck_w)
    H.soft(H.frustum("spine.2", "mane", (0, 1.3, 0.4), (0, 1.62, 0.9), (0.045, 0.07), (0.04, 0.06), sides=4), neck_w)
    H.soft(H.frustum("spine.2", "leather", (0, 1.0, 0.62), (0, 1.0, 0.72), (0.29, 0.36), (0.28, 0.36), sides=8), neck_w)


def head():
    H.frustum("head", "horse", (0, 1.52, 0.95), (0, 1.15, 1.24), (0.14, 0.16), (0.095, 0.12), sides=6)
    H.frustum("head", "mask", (0, 1.5, 0.97), (0, 1.22, 1.2), (0.15, 0.17), (0.105, 0.128), sides=6)
    H.frustum("head", "muzzle", (0, 1.23, 1.19), (0, 1.1, 1.3), (0.105, 0.12), (0.085, 0.085), sides=6)
    for s in (-1, 1):
        H.frustum("head", "eye", (s * 0.14, 1.38, 1.06), (s * 0.15, 1.4, 1.08), (0.03, 0.036), (0.024, 0.03), sides=4)
        H.frustum("head", "horse", (s * 0.08, 1.52, 0.94), (s * 0.095, 1.78, 0.9), (0.05, 0.045), (0.014, 0.014), sides=4)
    H.frustum("tail.1", "mane", (0, 1.16, -0.68), (0, 0.9, -0.9), (0.09, 0.11), (0.11, 0.12), sides=6)
    H.frustum("tail.2", "mane", (0, 0.9, -0.9), (0, 0.45, -0.98), (0.11, 0.12), (0.06, 0.08), sides=6)


def tack():
    H.box("spine.2", "olive", (0, BACK + 0.02, -0.02), (0.74, 0.06, 0.78))
    H.box("spine.2", "leather", (0, BACK + 0.07, -0.02), (0.38, 0.08, 0.46))
    for s in (-1, 1):
        H.frustum("spine.2", "olive", (s * 0.34, 1.24, 0.0), (s * 0.4, 0.8, 0.0), (0.03, 0.34), (0.03, 0.3), sides=4)


def legs():
    for s, front, hind in ((1, "leg1", "leg3"), (-1, "leg2", "leg4")):
        for tag, z in ((front, FORE_Z), (hind, HIND_Z)):
            fwd = tag == front
            top = (0.17, 0.22) if fwd else (0.2, 0.3)
            H.frustum(f"{tag}.upper", "horse", (s * 0.2, 1.05 if fwd else 1.1, z), (s * 0.15, 0.52, z), top, (0.085, 0.1), sides=6)
            H.frustum(f"{tag}.lower", "horse", (s * 0.15, 0.55, z), (s * 0.15, 0.3, z), (0.085, 0.095), (0.07, 0.08), sides=6)
            H.frustum(f"{tag}.lower", "wrap", (s * 0.15, 0.36, z), (s * 0.15, 0.14, z), (0.095, 0.105), (0.095, 0.105), sides=6)
            H.frustum(f"{tag}.lower", "hoof", (s * 0.15, 0.13, z), (s * 0.15, 0.0, z + 0.02), (0.075, 0.085), (0.095, 0.12), sides=6)


def rider_body():
    H.frustum("rider.spine", "coat", (0, 1.22, 0.06), (0, 1.95, 0.06), (0.27, 0.19), (0.34, 0.2), sides=8)
    H.frustum("rider.spine", "leather", (0, 1.42, 0.06), (0, 1.54, 0.06), (0.3, 0.215), (0.3, 0.215), sides=8)
    H.frustum("rider.spine", "coat_dk", (0, 1.9, 0.06), (0, 2.08, 0.07), (0.2, 0.18), (0.15, 0.15), sides=8)
    H.frustum("spine.2", "coat", (0, 1.34, 0.04), (0, 0.98, 0.04), (0.3, 0.24), (0.44, 0.33), sides=8)
    H.frustum("spine.2", "leather", (0, 1.0, 0.04), (0, 0.9, 0.04), (0.45, 0.335), (0.47, 0.35), sides=8)
    H.frustum("rider.head", "skin", (0, 1.95, 0.08), (0, 2.2, 0.08), (0.13, 0.14), (0.135, 0.145), sides=6)
    H.box("rider.head", "mane", (0, 2.0, 0.21), (0.2, 0.14, 0.06))
    H.frustum("rider.head", "helmet", (0, 2.18, 0.07), (0, 2.23, 0.07), (0.23, 0.25), (0.2, 0.22), sides=8)
    H.frustum("rider.head", "helmet", (0, 2.23, 0.07), (0, TOP, 0.07), (0.19, 0.2), (0.09, 0.1), sides=8)


def rider_arms():
    for s, side in ((1, "L"), (-1, "R")):
        H.frustum("rider.spine", "olive", (s * 0.2, 2.02, 0.06), (s * 0.5, 1.84, 0.06), (0.1, 0.22), (0.1, 0.24), sides=4)
        H.frustum("rider.spine", "pad", (s * 0.3, 2.07, 0.06), (s * 0.58, 1.9, 0.06), (0.05, 0.19), (0.05, 0.2), sides=4)
        H.frustum("rider.spine", "seal", (s * 0.56, 1.88, 0.2), (s * 0.57, 1.88, 0.26), (0.06, 0.06), (0.05, 0.05), sides=6)
        H.frustum(f"rider.arm.{side}", "coat", (s * 0.44, 1.78, 0.06), (s * 0.5, 1.4, 0.08), (0.13, 0.13), (0.1, 0.1), sides=6)
    H.frustum("rider.forearm.L", "coat", (0.5, 1.4, 0.08), (0.3, 1.38, 0.34), (0.1, 0.1), (0.085, 0.085), sides=6)
    H.frustum("rider.forearm.L", "leather", (0.3, 1.38, 0.34), (0.26, 1.34, 0.5), (0.085, 0.085), (0.11, 0.11), sides=6)
    H.frustum("rider.forearm.R", "coat", (-0.5, 1.4, 0.08), (-0.54, 1.22, 0.04), (0.1, 0.1), (0.085, 0.085), sides=6)
    H.frustum("rider.forearm.R", "leather", (-0.54, 1.24, 0.04), (-0.56, 1.06, 0.04), (0.09, 0.09), (0.12, 0.12), sides=6)


def rider_legs():
    for s in (-1, 1):
        H.frustum("spine.2", "leather", (s * 0.22, 1.25, 0.0), (s * 0.36, 1.0, 0.24), (0.14, 0.16), (0.1, 0.11), sides=6)
        H.frustum("spine.2", "boot", (s * 0.36, 1.04, 0.24), (s * 0.4, 0.7, 0.1), (0.1, 0.11), (0.08, 0.085), sides=6)
        H.frustum("spine.2", "boot", (s * 0.4, 0.72, 0.04), (s * 0.4, 0.66, 0.32), (0.09, 0.06), (0.08, 0.04), sides=4)
        H.frustum("spine.2", "iron", (s * 0.4, 0.63, 0.0), (s * 0.4, 0.63, 0.33), (0.09, 0.02), (0.08, 0.02), sides=4)


def machete():
    H.frustum("rider.forearm.R", "steel_dk", (-0.56, 1.14, 0.05), (-0.6, 0.98, 0.1), (0.07, 0.07), (0.1, 0.07), sides=4)
    H.frustum("rider.forearm.R", "steel", (-0.6, 1.0, 0.1), (-0.76, 0.55, 0.3), (0.14, 0.035), (0.15, 0.04), sides=4)
    H.frustum("rider.forearm.R", "steel", (-0.76, 0.58, 0.3), (-0.86, 0.3, 0.42), (0.15, 0.04), (0.06, 0.03), sides=4)


def banner():
    H.frustum("rider.spine", "steel_dk", (0, 1.5, -0.2), (0, 2.78, -0.2), (0.04, 0.04), (0.04, 0.04), sides=4)
    H.frustum("rider.spine", "steel_dk", (-0.05, 2.76, -0.2), (0.6, 2.76, -0.2), (0.03, 0.03), (0.03, 0.03), sides=4)
    H.frustum("rider.spine", "coat", (0.3, 2.72, -0.2), (0.3, 2.0, -0.2), (0.25, 0.03), (0.25, 0.03), sides=4)
    H.frustum("rider.spine", "pad", (0.3, 2.52, -0.2), (0.3, 2.42, -0.2), (0.26, 0.035), (0.26, 0.035), sides=4)


def make():
    body()
    head()
    tack()
    legs()
    rider_body()
    rider_arms()
    rider_legs()
    machete()
    banner()


def joints():
    out = {"head": ((0, 1.3, 0.7), (0, 1.4, 1.1)),
           "tail.1": ((0, 1.16, -0.68), (0, 0.9, -0.9)), "tail.2": ((0, 0.9, -0.9), (0, 0.45, -0.98)),
           "rider.spine": (SEAT, (0, 1.95, 0.06)), "rider.head": ((0, 1.95, 0.06), (0, TOP, 0.06))}
    for s, side, f, h in ((1, "L", "leg1", "leg3"), (-1, "R", "leg2", "leg4")):
        for tag, z in ((f, FORE_Z), (h, HIND_Z)):
            out[f"{tag}.upper"] = ((s * 0.2, 1.05, z), (s * 0.15, 0.55, z))
            out[f"{tag}.lower"] = ((s * 0.15, 0.55, z), (s * 0.15, 0.06, z))
        out[f"rider.arm.{side}"] = ((s * 0.44, 1.8, 0.06), (s * 0.5, 1.4, 0.06))
        out[f"rider.forearm.{side}"] = ((s * 0.5, 1.4, 0.06), (s * 0.54, 1.1, 0.06))
    return out


H.build("h03C", "mounted", PALETTE, make, joints())
