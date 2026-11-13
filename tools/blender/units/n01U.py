"""Gobbo Machinist (n01U), crawler rig used as a two-legged goblin: measured on
artifacts/model-sheets/refs/n01U/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n01U.py -- <out.glb>

Scale read off the profile: 600 px per metre, ground at y=0, z=0 over the legs, beak tip at z=+0.475.
Bones: leg1 = left leg (+x), leg2 = right leg (-x), the whole leg rigid on its upper bone (leg3/leg4 are unused);
`body` carries torso, arms, wrench and winding key; `head` carries the head, hat and the rivet cannon,
the part the shoot clip kicks up.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "gray": 0x8E9AA6, "gray_dk": 0x707C88, "red": 0x822228, "brown": 0x553525, "brown_dk": 0x3A2418,
    "black": 0x1E1E22, "gold": 0xC9A04A, "cyan": 0x40C8DC, "steel": 0x80858A, "steel_dk": 0x4E535A,
    "lamp": 0xF6CF68, "ember": 0xFF7A1C,
}
UP, LO = (0.2722, -0.2525, 0.2722), (0.2228, -0.2625, 0.2228)     # the family's leg directions, kept
LEGS = ((1, 1, 1), (2, -1, 1), (3, -1, -1), (4, 1, -1))


def torso():
    pts = [(0, 0.28, -0.05), (0, 0.5, -0.07), (0, 0.72, -0.1), (0, 0.9, -0.1), (0, 1.0, -0.08)]
    rad = [(0.2, 0.15), (0.23, 0.18), (0.3, 0.2), (0.34, 0.2), (0.22, 0.14)]
    H.chain("body", "gray", pts, rad, sides=8)
    H.frustum("body", "brown", (0, 0.88, 0.1), (0, 0.22, 0.1), (0.21, 0.035), (0.24, 0.035), sides=4)           # apron
    for s in (-1, 1):
        H.frustum("body", "brown", (s * 0.17, 1.0, 0.11), (s * 0.12, 0.84, 0.115), (0.04, 0.02), (0.05, 0.02), sides=4)   # apron strap
        H.frustum("body", "brown", (s * 0.15, 1.0, -0.22), (s * 0.04, 0.72, -0.3), (0.04, 0.02), (0.04, 0.02), sides=4)    # back X


def key():
    H.frustum("body", "gold", (0, 0.76, -0.2), (0, 0.76, -0.4), (0.03, 0.03), (0.04, 0.04))
    H.frustum("body", "gold", (0, 0.76, -0.38), (0, 0.76, -0.5), (0.04, 0.12), (0.05, 0.08), sides=4)
    for y in (0.88, 0.64):
        H.frustum("body", "gold", (-0.025, y, -0.52), (0.025, y, -0.52), (0.08, 0.08), (0.08, 0.08), sides=8)


def arm(s):
    """Sloped pad, thick arm in 3 frusta, flared cuff and a big glove."""
    H.frustum("body", "gray_dk", (s * 0.18, 0.99, -0.1), (s * 0.34, 0.92, -0.08), (0.09, 0.15), (0.13, 0.17))
    H.frustum("body", "gray", (s * 0.34, 0.93, -0.08), (s * 0.37, 0.76, -0.06), (0.12, 0.13), (0.09, 0.1))
    H.frustum("body", "gray", (s * 0.37, 0.78, -0.06), (s * 0.38, 0.58, -0.06), (0.09, 0.1), (0.075, 0.08))
    H.frustum("body", "black", (s * 0.38, 0.62, -0.06), (s * 0.38, 0.5, -0.07), (0.1, 0.1), (0.13, 0.14))       # cuff flares
    H.frustum("body", "black", (s * 0.38, 0.52, -0.07), (s * 0.38, 0.3, -0.07), (0.13, 0.14), (0.11, 0.12))     # glove
    H.frustum("body", "black", (s * 0.38, 0.3, -0.07), (s * 0.38, 0.14, -0.05), (0.11, 0.12), (0.06, 0.08))     # fingers
    H.frustum("body", "black", (s * 0.38, 0.4, -0.01), (s * 0.38, 0.3, 0.05), (0.1, 0.06), (0.09, 0.07), sides=6)  # knuckles


def wrench():
    x = 0.38
    H.frustum("body", "steel", (x, 0.3, -0.34), (x, 0.3, 0.3), (0.04, 0.035), (0.045, 0.045), sides=6)
    H.frustum("body", "steel", (x, 0.3, 0.26), (x, 0.3, 0.34), (0.05, 0.14), (0.05, 0.14), sides=4)
    H.frustum("body", "steel", (x, 0.41, 0.32), (x, 0.4, 0.58), (0.05, 0.045), (0.04, 0.03), sides=4)
    H.frustum("body", "steel", (x, 0.19, 0.32), (x, 0.2, 0.58), (0.05, 0.045), (0.04, 0.03), sides=4)


def head():
    H.chain("head", "gray", [(0, 1.02, -0.1), (0, 1.03, 0.03), (0, 1.0, 0.14)], [(0.16, 0.15), (0.18, 0.16), (0.12, 0.12)], sides=8)
    H.chain("head", "gray", [(0, 0.99, 0.1), (0, 0.86, 0.3), (0, 0.74, 0.5)], [(0.09, 0.1), (0.06, 0.08), (0.008, 0.01)], sides=6)
    H.chain("head", "red", [(0, 1.18, -0.12), (0, 1.2, 0.05), (0, 1.17, 0.22)], [(0.17, 0.1), (0.2, 0.12), (0.17, 0.1)], sides=8)
    H.frustum("head", "red", (0, 1.1, 0.12), (0, 1.09, 0.42), (0.19, 0.025), (0.13, 0.015), sides=4)           # visor
    H.frustum("head", "gold", (0, 1.19, 0.2), (0, 1.19, 0.34), (0.085, 0.085), (0.08, 0.08))                  # lamp cup
    H.frustum("head", "lamp", (0, 1.19, 0.33), (0, 1.19, 0.36), (0.065, 0.065), (0.06, 0.06))
    for s in (-1, 1):
        H.chain("head", "gray", [(s * 0.14, 1.07, -0.02), (s * 0.26, 1.12, -0.07), (s * 0.36, 1.15, -0.1)], [(0.07, 0.05), (0.06, 0.03), (0.008, 0.008)], sides=4)
        H.frustum("head", "gold", (s * 0.1, 1.04, 0.12), (s * 0.1, 1.04, 0.16), (0.075, 0.075), (0.075, 0.075))   # goggle rim
        H.frustum("head", "cyan", (s * 0.1, 1.04, 0.155), (s * 0.1, 1.04, 0.175), (0.055, 0.055), (0.055, 0.055))


def cannon():
    """The ranged weapon: a brass-and-steel rivet cannon on the right shoulder, muzzle past the beak. On `head`,
    so the shoot clip kicks it up."""
    x, y = -0.44, 1.0
    H.chain("head", "steel_dk", [(x, y, -0.2), (x, y, 0.15), (x, y, 0.55), (x, y, 0.7), (x, y, 0.84)],
            [(0.09, 0.09), (0.075, 0.075), (0.065, 0.065), (0.075, 0.075), (0.115, 0.115)], sides=8)
    H.frustum("head", "gold", (x, y, 0.1), (x, y, 0.22), (0.1, 0.1), (0.1, 0.1))                              # brass band
    H.frustum("head", "gold", (x, y + 0.05, 0.0), (x, y + 0.2, 0.0), (0.12, 0.12), (0.1, 0.1))                # ammo drum
    H.frustum("head", "ember", (x, y, 0.83), (x, y, 0.88), (0.075, 0.075), (0.06, 0.06))
    H.frustum("head", "brown", (x, y - 0.02, -0.2), (x, y - 0.08, -0.38), (0.07, 0.09), (0.06, 0.07), sides=6)   # stock


def leg(n, sx, sz):
    x = sx * 0.19
    H.frustum(f"leg{n}.upper", "gray", (x, 0.38, 0.0), (x, 0.2, 0.0), (0.1, 0.1), (0.075, 0.075))
    H.frustum(f"leg{n}.upper", "gray_dk", (x, 0.22, 0.0), (x, 0.12, 0.0), (0.075, 0.075), (0.1, 0.09))
    H.frustum(f"leg{n}.upper", "gray", (x, 0.08, -0.14), (x, 0.08, 0.18), (0.11, 0.08), (0.12, 0.05), sides=6)  # boot
    H.frustum(f"leg{n}.upper", "gray_dk", (x, 0.07, -0.15), (x, 0.05, 0.19), (0.12, 0.05), (0.12, 0.03), sides=4)


def make():
    torso()
    key()
    for s in (-1, 1):
        arm(s)
    wrench()
    head()
    cannon()
    leg(1, 1, 1)
    leg(2, -1, 1)


def joints():
    out = {"body": ((0, 0.55, -0.25), (0, 0.57, 0.2)), "head": ((0, 1.0, -0.05), (0, 1.02, 0.3))}
    for n, sx, sz in LEGS:
        hip = (sx * 0.19, 0.4, 0.0)
        knee = (hip[0] + sx * UP[0] * 0.3, hip[1] + UP[1] * 0.3, sz * UP[2] * 0.3)
        out[f"leg{n}.upper"] = (hip, knee)
        out[f"leg{n}.lower"] = (knee, (knee[0] + sx * LO[0] * 0.3, knee[1] + LO[1] * 0.3, knee[2] + sz * LO[2] * 0.3))
    return out


H.build("n01U", "crawler", PALETTE, make, joints())
