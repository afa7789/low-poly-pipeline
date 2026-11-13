"""Skeleton Warrior (u002): measured on artifacts/model-sheets/refs/u002/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/u002.py -- <out.glb>

Spiked club in the right hand (forearm.R), small plate shield strapped to the left forearm (forearm.L), brim helmet, rags.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "bone": 0xD8CDAE, "bone_dk": 0xB0A282, "helmet": 0x6A6B70, "helmet_dk": 0x4E4F54, "rag": 0x6B4630, "rag_dk": 0x4A2F20,
    "eye": 0x35E04A, "black": 0x15151A, "wood": 0x5A3422, "wood_dk": 0x3E2416, "spike": 0x8A8C94, "plate": 0x7A7B80,
    "strap": 0x4A3A34,
}

HIP, KNEE, ANKLE, LEG_X, KNEE_X = 1.25, 0.68, 0.14, 0.26, 0.28
WAIST, NECK, TOP = 1.45, 2.1, 2.72
SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.52, 2.02, 0.62, 1.55, 1.1
GRIP = (-0.64, 1.16, 0.06)       # right fist
CLUB_END = (-0.92, 0.3, 0.72)   # club tip, down and forward as in the sheet


def hem(p):
    if p[1] > 1.2:
        return {"pelvis": 1.0}
    return {"pelvis": 0.4, "thigh.L" if p[0] > 0 else "thigh.R": 0.6}


def head():
    H.frustum("head", "bone", (0, 2.18, 0.04), (0, 2.5, 0.04), (0.2, 0.22), (0.26, 0.27), sides=8)           # big skull
    H.frustum("head", "bone_dk", (0, 2.06, 0.1), (0, 2.22, 0.1), (0.12, 0.12), (0.18, 0.17), sides=6)        # jaw
    H.frustum("head", "bone", (0, 1.96, -0.02), (0, 2.1, -0.02), (0.09, 0.09), (0.12, 0.12), sides=6)       # neck
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.11, 2.37, 0.31), (0.11, 0.1, 0.05))
    H.frustum("head", "helmet_dk", (0, 2.5, 0.02), (0, 2.56, 0.02), (0.5, 0.5), (0.4, 0.4), sides=8)      # brim
    H.frustum("head", "helmet", (0, 2.56, 0.02), (0, 2.68, 0.02), (0.36, 0.36), (0.3, 0.3), sides=8)
    H.frustum("head", "helmet", (0, 2.68, 0.02), (0, 2.74, 0.02), (0.3, 0.3), (0.14, 0.14), sides=8)


def torso():
    for i, y in enumerate((1.64, 1.78, 1.92)):                                                              # rib bands
        H.frustum("spine", "bone" if i % 2 == 0 else "bone_dk", (0, y - 0.06, 0.04), (0, y + 0.06, 0.04), (0.3, 0.22), (0.32, 0.23), sides=8)
    H.frustum("spine", "bone_dk", (0, WAIST, 0), (0, 2.1, -0.04), (0.1, 0.1), (0.12, 0.12), sides=6)       # spine
    H.frustum("spine", "bone", (0, 2.0, 0), (0, 2.12, 0), (0.46, 0.2), (0.3, 0.16), sides=6)                # collar bone yoke
    H.frustum("pelvis", "bone", (0, HIP - 0.1, 0), (0, WAIST + 0.04, 0), (0.34, 0.22), (0.26, 0.2), sides=8)   # pelvis
    H.frustum("pelvis", "bone_dk", (0, HIP - 0.2, 0.05), (0, HIP - 0.06, 0.05), (0.12, 0.1), (0.3, 0.2), sides=6)


def rags():
    H.frustum("spine", "rag", (0, 1.55, -0.1), (0, 2.16, -0.1), (0.5, 0.2), (0.46, 0.2), sides=6)
    H.frustum("spine", "rag_dk", (0, 2.1, -0.02), (0, 2.26, -0.02), (0.46, 0.26), (0.28, 0.2), sides=6)    # collar
    low = H.frustum("pelvis", "rag", (0, 0.72, -0.1), (0, 1.56, -0.1), (0.5, 0.2), (0.5, 0.2), sides=6)
    H.soft(low, hem)


def leg(s, side):
    k = s * KNEE_X
    H.frustum(f"thigh.{side}", "bone", (k, KNEE + 0.02, 0), (s * LEG_X, HIP, 0), (0.1, 0.1), (0.14, 0.14), sides=6)
    H.frustum(f"thigh.{side}", "bone_dk", (k, KNEE - 0.05, 0.02), (k, KNEE + 0.12, 0.02), (0.16, 0.16), (0.12, 0.12), sides=6)   # knee
    H.frustum(f"shin.{side}", "bone", (k, ANKLE + 0.04, 0), (k, KNEE, 0), (0.1, 0.1), (0.13, 0.13), sides=6)
    H.frustum(f"shin.{side}", "bone_dk", (k, ANKLE - 0.02, 0), (k, ANKLE + 0.14, 0), (0.15, 0.15), (0.1, 0.1), sides=6)
    H.frustum(f"foot.{side}", "bone", (k, 0.08, -0.08), (k, 0.08, 0.5), (0.16, 0.1), (0.2, 0.06), sides=6)


def arm(s, side):
    elbow = (s * EL_X, EL_Y, 0.04)
    H.frustum(f"arm.{side}", "bone_dk", (s * 0.34, 2.14, 0), (s * 0.58, 1.92, 0), (0.14, 0.16), (0.17, 0.17), sides=6)   # shoulder cap
    H.chain(f"arm.{side}", "bone", [(s * SH_X, SH_Y + 0.02, 0), (s * 0.58, 1.78, 0.03), elbow], [(0.1, 0.1), (0.1, 0.1), (0.12, 0.12)])
    hx = GRIP[0] if side == "R" else s * EL_X
    H.chain(f"forearm.{side}", "bone", [(elbow[0], EL_Y + 0.02, 0.04), ((elbow[0] + hx) / 2, 1.3, 0.05), (hx, WR_Y + 0.02, 0.06)],
            [(0.12, 0.12), (0.095, 0.095), (0.1, 0.1)])
    H.frustum(f"forearm.{side}", "bone_dk", (hx, WR_Y + 0.12, 0.06), (hx, WR_Y - 0.22, 0.08), (0.17, 0.16), (0.2, 0.18), sides=6)   # big hand


def club():
    g = GRIP
    mid = (g[0] + (CLUB_END[0] - g[0]) * 0.4, g[1] + (CLUB_END[1] - g[1]) * 0.4, g[2] + (CLUB_END[2] - g[2]) * 0.4)
    H.frustum("forearm.R", "wood_dk", (g[0] + 0.03, g[1] + 0.3, g[2] - 0.14), mid, (0.09, 0.09), (0.15, 0.15), sides=6)     # handle
    H.frustum("forearm.R", "wood", mid, CLUB_END, (0.17, 0.17), (0.27, 0.27), sides=6)                                         # head
    for t, off in ((0.55, (-0.2, 0, 0)), (0.75, (0.2, 0, 0.0)), (0.8, (0, 0.2, 0)), (0.95, (-0.18, -0.1, 0.1))):
        c = [mid[i] + (CLUB_END[i] - mid[i]) * t for i in range(3)]
        tip = (c[0] + off[0] * 2.2, c[1] + off[1] * 2.2, c[2] + off[2] * 2.2)
        H.frustum("forearm.R", "spike", tuple(c), tip, (0.1, 0.1), (0.012, 0.012), sides=4)


def shield():
    x = 0.8
    H.box("forearm.L", "plate", (x, 1.4, -0.04), (0.14, 0.78, 0.5))
    H.box("forearm.L", "helmet_dk", (x + 0.08, 1.4, -0.04), (0.04, 0.5, 0.3))
    H.box("forearm.L", "strap", (EL_X + 0.06, 1.62, 0.04), (0.2, 0.08, 0.3))


def make():
    head()
    torso()
    rags()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        arm(s, side)
    club()
    shield()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)),
           "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * KNEE_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * KNEE_X, KNEE, 0), (s * KNEE_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * KNEE_X, ANKLE, 0), (s * KNEE_X, 0.06, 0.5))
    return out


H.build("u002", "biped", PALETTE, make, joints())
