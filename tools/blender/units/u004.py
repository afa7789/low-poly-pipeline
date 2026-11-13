"""Ghoul (u004): measured on artifacts/model-sheets/refs/u004/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/u004.py -- <out.glb>

Hunched knuckle-walker: long arms to the ground, big clawed hands, ragged pants, mask over the jaw, a steel plate strapped to the right forearm.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "skin": 0xCABD9D, "skin_dk": 0xA79B7E, "pants": 0x5A5A48, "pants_dk": 0x44443A, "claw": 0x4A3A34, "mask": 0x6A4430,
    "plate": 0x7A7D86, "strap": 0x7A4A2E, "eye": 0x35E04A,
}

HIP = (0, 1.0, 0)
WAIST = (0, 1.28, 0.2)
NECK = (0, 1.7, 0.62)
SH_X = 0.5
SHOULDER_Z, SHOULDER_Y = 0.55, 1.68
ELBOW = (0.68, 0.9, 0.86)
WRIST = (0.74, 0.42, 1.02)
HAND = (0.75, 0.22, 1.1)
KNEE, ANKLE, LEG_X, KNEE_X, FOOT_X = (0.32, 0.62, 0.2), (0.36, 0.2, -0.1), 0.3, 0.32, 0.37


def head():
    H.frustum("head", "skin", (0, 1.42, 0.9), (0, 1.9, 1.0), (0.24, 0.27), (0.2, 0.24), sides=8)           # skull
    H.frustum("head", "skin_dk", (0, 1.38, 0.96), (0, 1.52, 1.1), (0.18, 0.2), (0.2, 0.22), sides=6)       # jaw
    H.frustum("head", "mask", (0, 1.38, 1.1), (0, 1.62, 1.16), (0.2, 0.1), (0.24, 0.1), sides=6)           # mask
    H.chain("head", "skin", [(0, 1.66, 0.5), (0, 1.62, 0.7), (0, 1.62, 0.92)], [(0.25, 0.22), (0.22, 0.22), (0.2, 0.2)], sides=6)
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.1, 1.7, 1.25), (0.08, 0.08, 0.04))


def torso():
    H.frustum("spine", "skin", (0, 1.26, 0.2), (0, 1.74, 0.62), (0.34, 0.3), (0.5, 0.32), sides=8)         # V chest
    H.frustum("spine", "skin_dk", (0, 1.5, 0.3), (0, 1.74, 0.5), (0.4, 0.3), (0.3, 0.26), sides=6)         # belly shade
    H.frustum("spine", "skin", (0, 1.58, 0.32), (0, 1.95, 0.5), (0.46, 0.3), (0.28, 0.24), sides=8)        # hump
    H.frustum("pelvis", "pants", (0, 0.88, -0.02), (0, 1.3, 0.16), (0.4, 0.3), (0.34, 0.27), sides=8)
    H.frustum("pelvis", "pants_dk", (0, 0.9, -0.2), (0, 1.2, -0.1), (0.36, 0.14), (0.3, 0.14), sides=6)    # seat


def leg(s, side):
    k, a, f = (s * KNEE[0], KNEE[1], KNEE[2]), (s * ANKLE[0], ANKLE[1], ANKLE[2]), s * FOOT_X
    H.chain(f"thigh.{side}", "pants", [(s * LEG_X, 1.02, -0.02), (s * 0.34, 0.82, 0.08), k], [(0.22, 0.22), (0.2, 0.2), (0.16, 0.16)], sides=6)
    H.frustum(f"shin.{side}", "pants_dk", (k[0], 0.7, k[2]), (a[0], 0.34, a[2] + 0.04), (0.17, 0.17), (0.2, 0.2), sides=6)   # ragged cuff
    H.frustum(f"shin.{side}", "skin", (a[0], 0.4, a[2] + 0.02), (a[0], a[1], a[2]), (0.12, 0.12), (0.1, 0.1), sides=6)
    H.frustum(f"foot.{side}", "skin", (f, 0.08, -0.14), (f, 0.2, -0.06), (0.17, 0.2), (0.14, 0.14), sides=6)
    H.frustum(f"foot.{side}", "skin_dk", (f, 0.1, -0.02), (f, 0.07, 0.34), (0.19, 0.15), (0.2, 0.08), sides=6)
    for dx in (-0.12, 0, 0.12):
        H.frustum(f"foot.{side}", "claw", (f + dx, 0.07, 0.3), (f + dx, 0.03, 0.5), (0.04, 0.04), (0.015, 0.015), sides=4)


def claws(s, side):
    x, y, z = s * HAND[0], HAND[1], HAND[2]
    H.frustum(f"forearm.{side}", "skin", (x, y + 0.02, z - 0.1), (x, y + 0.02, z + 0.12), (0.22, 0.2), (0.25, 0.18), sides=6)   # big hand
    for dx in (-0.15, -0.05, 0.05, 0.15):
        H.frustum(f"forearm.{side}", "claw", (x + dx, y, z + 0.08), (x + dx, y - 0.2, z + 0.34), (0.05, 0.05), (0.015, 0.015), sides=4)


def arm(s, side):
    sh = (s * SH_X, SHOULDER_Y, SHOULDER_Z)
    el = (s * ELBOW[0], ELBOW[1], ELBOW[2])
    wr = (s * WRIST[0], WRIST[1], WRIST[2])
    H.frustum(f"arm.{side}", "skin", (s * 0.3, 1.78, 0.5), (s * 0.55, 1.62, 0.55), (0.2, 0.22), (0.2, 0.22), sides=6)      # shoulder cap
    H.chain(f"arm.{side}", "skin", [sh, (s * 0.6, 1.3, 0.7), el], [(0.21, 0.2), (0.19, 0.18), (0.15, 0.15)], sides=6)
    H.chain(f"forearm.{side}", "skin", [el, (s * 0.71, 0.66, 0.94), wr], [(0.17, 0.16), (0.17, 0.16), (0.13, 0.13)], sides=6)
    claws(s, side)


def shield():
    x = -0.92
    H.frustum("forearm.R", "plate", (x, 0.4, 0.96), (x, 1.12, 0.86), (0.05, 0.19), (0.05, 0.19), sides=4)
    for y in (0.68, 0.95):
        H.frustum("forearm.R", "strap", (-0.74, y, 0.9), (-0.74, y + 0.08, 0.9), (0.18, 0.17), (0.18, 0.17), sides=6)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
        arm(s, side)
    shield()


def joints():
    out = {"pelvis": (HIP, WAIST), "spine": (WAIST, NECK), "head": ((0, 1.5, 0.8), (0, 2.0, 0.95))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SHOULDER_Y, SHOULDER_Z), (s * ELBOW[0], ELBOW[1], ELBOW[2]))
        out[f"forearm.{side}"] = ((s * ELBOW[0], ELBOW[1], ELBOW[2]), (s * WRIST[0], WRIST[1], WRIST[2]))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP[1], 0), (s * KNEE[0], KNEE[1], KNEE[2]))
        out[f"shin.{side}"] = ((s * KNEE[0], KNEE[1], KNEE[2]), (s * ANKLE[0], ANKLE[1], ANKLE[2]))
        out[f"foot.{side}"] = ((s * ANKLE[0], ANKLE[1], ANKLE[2]), (s * FOOT_X, 0.06, 0.4))
    return out


H.build("u004", "biped", PALETTE, make, joints())
