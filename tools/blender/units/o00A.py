"""Ice Troll Witch Doctor (o00A): lean teal troll, white tuft, big tusks, gold winged collar and back blades,
black V tabard and cape, hooked gold staff with silver orbs in the right hand; measured on
artifacts/model-sheets/refs/o00A/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/o00A.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "skin": 0x4E9A98, "skin_dk": 0x3F8483, "hair": 0xE8ECF2, "tusk": 0xEDE2C2, "eye": 0xFFFFFF, "gold": 0xC09A44,
    "gold_hi": 0xF2A830, "black": 0x1E1D22, "pants": 0x39373C, "maroon": 0x703A3C, "boot": 0x3C6488,
    "orb": 0xB8BCC8,
}

SH_X = 0.55
STAFF_X, STAFF_Z = -0.87, 0.62


def head():
    H.frustum("head", "skin", (0, 2.14, 0.0), (0, 2.3, 0.1), (0.14, 0.14), (0.2, 0.2), sides=6)
    H.frustum("head", "skin", (0, 2.3, 0.1), (0, 2.62, 0.1), (0.22, 0.22), (0.2, 0.2), sides=6)
    H.frustum("head", "skin", (0, 2.2, 0.28), (0, 2.38, 0.3), (0.17, 0.12), (0.19, 0.1), sides=6)          # chin / jaw
    H.chain("head", "skin_dk", [(0, 2.44, 0.3), (0, 2.34, 0.44), (0, 2.26, 0.5)], [(0.06, 0.06), (0.045, 0.045), (0.03, 0.03)], sides=4)
    H.frustum("head", "hair", (0, 2.52, 0.0), (0, 2.9, -0.08), (0.18, 0.24), (0.09, 0.2), sides=6)         # tuft
    H.frustum("head", "hair", (0, 2.62, -0.1), (0, 2.2, -0.26), (0.17, 0.1), (0.1, 0.08), sides=6)         # mane down the back
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.1, 2.46, 0.31), (0.09, 0.04, 0.03))
        H.chain("head", "tusk", [(s * 0.13, 2.22, 0.3), (s * 0.2, 2.08, 0.48), (s * 0.22, 2.22, 0.62)],
                [(0.07, 0.07), (0.05, 0.05), (0.012, 0.012)], sides=6)
        H.chain("head", "skin", [(s * 0.2, 2.46, 0.04), (s * 0.5, 2.55, 0.0), (s * 0.85, 2.85, -0.04)],
                [(0.1, 0.05), (0.08, 0.04), (0.01, 0.01)], sides=4)                                       # long ears


def torso():
    H.frustum("spine", "skin", (0, 1.45, 0), (0, 1.9, 0.02), (0.3, 0.3), (0.42, 0.34), sides=8)
    H.frustum("spine", "gold", (0, 1.92, 0), (0, 2.12, 0.02), (0.86, 0.5), (0.4, 0.3), sides=8)               # winged collar
    H.box("spine", "gold_hi", (0, 1.88, 0.3), (0.2, 0.14, 0.05))
    H.frustum("spine", "black", (0, 1.98, 0.28), (0, 1.3, 0.3), (0.5, 0.06), (0.3, 0.05), sides=4)            # tabard top
    H.frustum("spine", "black", (0, 2.0, -0.24), (0, 1.3, -0.44), (0.52, 0.08), (0.34, 0.08), sides=4)        # cape top
    H.frustum("pelvis", "black", (0, 1.4, 0.3), (0, 0.15, 0.32), (0.3, 0.05), (0.03, 0.04), sides=4)          # tabard tip
    H.frustum("pelvis", "black", (0, 1.3, -0.44), (0, 0.25, -0.5), (0.34, 0.08), (0.04, 0.05), sides=4)       # cape tip
    H.frustum("pelvis", "pants", (0, 1.05, 0), (0, 1.35, 0), (0.34, 0.26), (0.3, 0.24), sides=8)
    H.frustum("pelvis", "maroon", (0, 1.32, 0), (0, 1.5, 0), (0.32, 0.26), (0.32, 0.26), sides=8)
    for s in (-1, 1):   # gold blades behind the shoulders
        H.chain("spine", "gold", [(s * 0.22, 2.0, -0.2), (s * 0.4, 2.3, -0.2), (s * 0.58, 2.62, -0.2)],
                [(0.07, 0.04), (0.07, 0.04), (0.012, 0.012)], sides=4)


def leg(s, side):
    x = s * 0.3
    H.frustum(f"thigh.{side}", "pants", (x, 0.62, 0.02), (s * 0.27, 1.2, 0), (0.21, 0.22), (0.29, 0.28), sides=6)
    H.frustum(f"thigh.{side}", "maroon", (x, 0.68, 0.1), (x, 0.52, 0.1), (0.2, 0.18), (0.2, 0.18), sides=6)  # knee pad
    H.frustum(f"shin.{side}", "pants", (x, 0.3, 0), (x, 0.58, 0.02), (0.19, 0.19), (0.21, 0.21), sides=6)
    H.frustum(f"shin.{side}", "boot", (x, 0.08, 0), (x, 0.5, 0), (0.22, 0.24), (0.28, 0.3), sides=6)
    H.frustum(f"foot.{side}", "boot", (x, 0.1, -0.12), (x, 0.08, 0.36), (0.22, 0.2), (0.2, 0.1), sides=6)
    for k in (-1, 0, 1):
        H.frustum(f"foot.{side}", "tusk", (x + k * 0.1, 0.07, 0.34), (x + k * 0.12, 0.05, 0.58), (0.04, 0.04), (0.012, 0.012), sides=4)


def left_arm():
    H.frustum("arm.L", "skin", (SH_X, 2.0, 0), (0.7, 1.5, 0.02), (0.21, 0.21), (0.18, 0.18), sides=6)
    H.frustum("forearm.L", "skin", (0.7, 1.5, 0.02), (0.72, 1.3, 0.04), (0.15, 0.15), (0.14, 0.14), sides=6)
    H.frustum("forearm.L", "maroon", (0.72, 1.3, 0.04), (0.76, 0.98, 0.08), (0.2, 0.2), (0.22, 0.22), sides=6)
    H.frustum("forearm.L", "skin", (0.76, 1.0, 0.08), (0.8, 0.8, 0.12), (0.22, 0.22), (0.3, 0.28), sides=6)    # big fist
    H.frustum("forearm.L", "skin", (0.8, 0.82, 0.12), (0.8, 0.6, 0.12), (0.3, 0.28), (0.2, 0.2), sides=6)


def right_arm():
    H.frustum("arm.R", "skin", (-SH_X, 2.0, 0), (-0.76, 1.5, 0.05), (0.21, 0.21), (0.18, 0.18), sides=6)
    H.frustum("forearm.R", "maroon", (-0.76, 1.5, 0.05), (-0.84, 1.42, 0.5), (0.2, 0.2), (0.22, 0.22), sides=6)
    H.frustum("forearm.R", "skin", (STAFF_X, 1.2, STAFF_Z), (STAFF_X, 1.58, STAFF_Z), (0.2, 0.2), (0.23, 0.22), sides=6)


def staff():
    H.frustum("forearm.R", "gold", (STAFF_X, 0.04, STAFF_Z), (STAFF_X, 2.3, STAFF_Z), (0.06, 0.06), (0.055, 0.055), sides=6)
    arc = [(STAFF_X, 2.3), (STAFF_X, 2.46), (-0.7, 2.62), (STAFF_X, 2.76), (-1.08, 2.62), (-1.1, 2.42)]
    H.chain("forearm.R", "gold", [(x, y, STAFF_Z) for x, y in arc], [(0.06, 0.06)] * 5 + [(0.045, 0.045)], sides=6)
    for i, (x, y) in enumerate(((-1.1, 2.3), (-1.14, 2.08))):
        H.frustum("forearm.R", "orb", (x, y - 0.1, STAFF_Z), (x, y + 0.1, STAFF_Z), (0.11, 0.11), (0.11, 0.11), sides=8)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    left_arm()
    right_arm()
    staff()


def joints():
    return {"arm.L": ((SH_X, 2.0, 0), (0.7, 1.5, 0.02)), "forearm.L": ((0.7, 1.5, 0.02), (0.78, 0.8, 0.1)),
            "arm.R": ((-SH_X, 2.0, 0), (-0.76, 1.5, 0.05)), "forearm.R": ((-0.76, 1.5, 0.05), (-0.82, 0.95, 0.15))}


H.build("o00A", "biped", PALETTE, make, joints())
