"""Magnataur (n016), centaur family: measured on artifacts/model-sheets/refs/n016/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n016.py -- <out.glb>

Scale off the profile panel: 210 px per metre, ground y=0, head top at 3.0. A white goat body (back at 1.8) with
an anvil on it, a hunched blue walrus-faced torso, long ivory tusks, a war hammer in the right hand.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "fur": 0xEDEFF4, "fur_lt": 0xB9C5D6, "blue": 0x4A78B5, "blue_dk": 0x3A5F95, "steel": 0x5E6068,
    "steel_dk": 0x3E3F45, "ivory": 0xCDBF9D, "black": 0x1D1B1E, "gold": 0xB08A2E, "orange": 0xF5A021,
    "belt": 0x2A2A2E, "muzzle": 0x8FA3B5, "wood": 0x4A3A30,
}
ARM_X, SH_Z = 0.92, 0.9
# hip, knee, hoof (x, y, z) of the +x leg of each leg pair; the legs stand vertical on the bones
FRONT = ((0.42, 1.35, 0.9), (0.42, 0.75, 0.9), (0.42, 0.08, 0.9))
HIND = ((0.42, 1.4, -0.72), (0.42, 0.75, -0.72), (0.42, 0.08, -0.72))
LEGS = ((1, FRONT, 1), (-1, FRONT, 2), (1, HIND, 3), (-1, HIND, 4))


def trunk():
    H.frustum("spine.1", "fur", (0, 1.3, -1.0), (0, 1.4, -0.4), (0.4, 0.32), (0.56, 0.4))
    H.frustum("spine.1", "fur", (0, 1.4, -0.4), (0, 1.42, 0.0), (0.56, 0.4), (0.58, 0.4))
    H.frustum("spine.2", "fur", (0, 1.42, 0.0), (0, 1.4, 0.55), (0.58, 0.4), (0.55, 0.4))
    H.frustum("spine.2", "fur", (0, 1.4, 0.55), (0, 1.35, 1.1), (0.55, 0.4), (0.48, 0.36))
    H.frustum("spine.1", "fur_lt", (0, 1.08, -0.8), (0, 1.08, 0.0), (0.46, 0.1), (0.5, 0.1), sides=4)
    H.frustum("spine.2", "fur_lt", (0, 1.08, 0.0), (0, 1.08, 0.9), (0.5, 0.1), (0.44, 0.1), sides=4)
    H.chain(["tail.1", "tail.2"], "fur", [(0, 1.45, -1.0), (0, 1.3, -1.25), (0, 1.0, -1.42)],
            [(0.12, 0.12), (0.1, 0.1), (0.02, 0.02)], sides=6)
    H.frustum("tail.2", "fur_lt", (0, 1.15, -1.3), (0, 0.95, -1.45), (0.1, 0.07), (0.02, 0.02), sides=4)


def anvil():
    H.frustum("spine.1", "steel_dk", (0, 1.76, -0.2), (0, 1.9, -0.2), (0.32, 0.26), (0.2, 0.14))
    H.frustum("spine.1", "steel", (0, 1.9, -0.2), (0, 2.0, -0.2), (0.2, 0.14), (0.2, 0.16))
    H.frustum("spine.1", "steel", (0, 2.0, -0.2), (0, 2.16, -0.2), (0.3, 0.3), (0.4, 0.44))
    H.frustum("spine.1", "steel_dk", (0, 2.08, 0.2), (0, 2.1, 0.5), (0.2, 0.12), (0.06, 0.05), sides=4)


def torso():
    H.frustum("spine.3", "fur", (0, 1.5, 0.85), (0, 2.0, 0.95), (0.5, 0.42), (0.6, 0.42))
    H.frustum("spine.3", "fur", (0, 2.0, 0.95), (0, 2.5, 1.02), (0.6, 0.42), (0.52, 0.38))
    H.frustum("spine.3", "belt", (0, 1.6, 0.85), (0, 1.74, 0.9), (0.55, 0.46), (0.56, 0.46))
    H.box("spine.3", "orange", (0, 1.9, 1.38), (0.18, 0.2, 0.05))
    H.frustum("spine.3", "fur", (0, 2.2, 0.7), (0, 2.85, 0.95), (0.7, 0.42), (0.52, 0.36))
    H.frustum("spine.3", "fur", (0, 2.55, 0.8), (0, 3.02, 1.0), (0.5, 0.3), (0.3, 0.22))


def head():
    H.frustum("head", "blue", (0, 2.62, 1.05), (0, 2.62, 1.45), (0.3, 0.3), (0.33, 0.3))
    H.frustum("head", "blue", (0, 2.58, 1.45), (0, 2.48, 1.7), (0.3, 0.28), (0.24, 0.2))
    H.frustum("head", "muzzle", (0, 2.44, 1.62), (0, 2.34, 1.8), (0.22, 0.15), (0.2, 0.14))
    for s in (-1, 1):
        H.frustum("head", "orange", (s * 0.15, 2.72, 1.5), (s * 0.15, 2.7, 1.62), (0.07, 0.035), (0.06, 0.03), sides=4)
        H.chain("head", "ivory", [(s * 0.16, 2.4, 1.66), (s * 0.2, 2.05, 1.78), (s * 0.18, 1.7, 1.78), (s * 0.12, 1.5, 1.7)],
                [(0.08, 0.08), (0.075, 0.075), (0.06, 0.06), (0.012, 0.012)], sides=6)


def arm(s, side):
    x = s * ARM_X
    H.frustum(f"arm.{side}", "blue", (s * 0.4, 2.7, SH_Z + 0.05), (x, 2.42, SH_Z), (0.28, 0.3), (0.34, 0.34), sides=8)
    H.frustum(f"arm.{side}", "blue", (x, 2.5, SH_Z), (x, 2.0, SH_Z), (0.33, 0.34), (0.37, 0.34), sides=8)
    H.frustum(f"arm.{side}", "blue_dk", (x, 2.05, SH_Z), (x, 1.72, SH_Z + 0.02), (0.37, 0.34), (0.27, 0.27), sides=8)
    H.frustum(f"forearm.{side}", "blue", (x, 1.76, SH_Z + 0.02), (x, 1.4, SH_Z + 0.04), (0.26, 0.26), (0.28, 0.28), sides=8)
    H.frustum(f"forearm.{side}", "blue_dk", (x, 1.45, SH_Z + 0.04), (x, 1.12, SH_Z + 0.06), (0.28, 0.28), (0.38, 0.34), sides=8)
    H.frustum(f"forearm.{side}", "blue", (x, 1.15, SH_Z + 0.06), (x, 0.9, SH_Z + 0.1), (0.38, 0.34), (0.24, 0.22), sides=8)


def hammer():
    x, y = -ARM_X, 1.12
    H.chain("forearm.R", "wood", [(x, y, 0.1), (x, y, 0.85), (x, y + 0.02, 1.55)], [(0.07, 0.07)] * 3, sides=6)
    H.box("forearm.R", "steel", (x, y + 0.08, 1.7), (0.4, 0.38, 0.55))
    H.frustum("forearm.R", "steel_dk", (x, y - 0.05, 1.72), (x, 0.55, 1.78), (0.06, 0.28), (0.05, 0.4), sides=4)
    H.box("forearm.R", "steel_dk", (x, y, 0.1), (0.2, 0.2, 0.22))


def leg(s, geo, n):
    hip, knee, hoof = ((s * p[0], p[1], p[2]) for p in geo)
    up, lo = f"leg{n}.upper", f"leg{n}.lower"
    back = geo is HIND
    top = (hip[0], hip[1] + 0.12, hip[2] + (0.08 if back else -0.05))
    H.frustum(up, "fur", (knee[0], knee[1] + 0.05, knee[2]), top, (0.17, 0.2), (0.3, 0.34), sides=6)
    H.frustum(lo, "fur", (knee[0], 0.55, knee[2]), (knee[0], knee[1] + 0.05, knee[2]), (0.15, 0.17), (0.17, 0.2), sides=6)
    H.frustum(lo, "black", (hoof[0], 0.17, hoof[2]), (knee[0], 0.58, knee[2]), (0.15, 0.17), (0.18, 0.19), sides=6)
    H.frustum(lo, "gold", (hoof[0], 0.0, hoof[2] + 0.03), (hoof[0], 0.18, hoof[2]), (0.19, 0.22), (0.15, 0.17), sides=6)


def make():
    trunk()
    anvil()
    torso()
    head()
    for s, side in ((1, "L"), (-1, "R")):
        arm(s, side)
    hammer()
    for args in LEGS:
        leg(*args)


def joints():
    out = {
        "spine.1": ((0, 1.35, -1.0), (0, 1.4, 0.0)), "spine.2": ((0, 1.4, 0.0), (0, 1.4, 0.85)),
        "spine.3": ((0, 1.5, 0.85), (0, 2.3, 0.95)), "head": ((0, 2.4, 1.1), (0, 2.95, 1.3)),
        "tail.1": ((0, 1.45, -1.0), (0, 1.3, -1.25)), "tail.2": ((0, 1.3, -1.25), (0, 1.0, -1.42)),
    }
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * ARM_X, 2.45, SH_Z), (s * ARM_X, 1.75, SH_Z))
        out[f"forearm.{side}"] = ((s * ARM_X, 1.75, SH_Z), (s * ARM_X, 1.1, SH_Z))
    for s, geo, n in LEGS:
        hip, knee, hoof = ((s * p[0], p[1], p[2]) for p in geo)
        out[f"leg{n}.upper"], out[f"leg{n}.lower"] = (hip, knee), (knee, hoof)
    return out


H.build("n016", "centaur", PALETTE, make, joints())
