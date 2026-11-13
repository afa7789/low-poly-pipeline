"""Summoned Lobster (n00W), crawler: measured on artifacts/model-sheets/refs/n00W/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n00W.py -- <out.glb>

Scale read off the profile: 300 px per metre, ground at y=0, body centre z=0, claw tips at z=+0.75.
The claws ride on extra bones claw.L / claw.R (the pinch clip keys them); the arm stubs sit on `body`; the extra side legs ride on the nearest walking leg bone.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {"teal": 0x5F8884, "teal_dk": 0x4B706D, "dark": 0x262522, "dark_lt": 0x3A3835, "cyan": 0x22D2E0}

# direction of the family's leg bones (upper, lower) per unit of `a`: kept, the pieces are angled instead
HIP_Y, A = 0.27, 0.5
UP = (0.2722, -0.2525, 0.2722)
LO = (0.2228, -0.2625, 0.2228)
LEGS = ((1, 1, 1), (2, -1, 1), (3, -1, -1), (4, 1, -1))     # bone number, side x, side z


def shell():
    H.chain("body", "dark", [(0, 0.32, -0.36), (0, 0.32, -0.2), (0, 0.33, 0.05), (0, 0.33, 0.25), (0, 0.32, 0.38)],
            [(0.1, 0.09), (0.27, 0.2), (0.3, 0.22), (0.25, 0.2), (0.15, 0.12)], sides=8)
    H.frustum("body", "dark_lt", (0, 0.22, -0.3), (0, 0.22, 0.3), (0.2, 0.05), (0.24, 0.05), sides=6)
    for z0, z1, w in ((0.22, 0.04, 0.22), (0.06, -0.12, 0.25), (-0.1, -0.28, 0.2)):      # dorsal plates
        H.frustum("body", "teal", (0, 0.52, z0), (0, 0.5, z1), (w, 0.04), (w + 0.03, 0.045), sides=6)
        H.frustum("body", "teal_dk", (0, 0.56, z0 - 0.02), (0, 0.54, z1 + 0.02), (w - 0.07, 0.03), (w - 0.04, 0.03), sides=6)
    for i, ang in enumerate((-0.36, -0.18, 0, 0.18, 0.36)):      # tail fan
        H.frustum("body", "teal", (0, 0.28, -0.33), (ang * 0.7, 0.26, -0.58 - 0.03 * (2 - abs(i - 2))), (0.05, 0.03), (0.09, 0.03), sides=4)


def eyes():
    for s in (-1, 1):
        H.chain("head", "dark", [(s * 0.1, 0.42, 0.26), (s * 0.1, 0.54, 0.29), (s * 0.1, 0.64, 0.3)], [(0.045, 0.045), (0.03, 0.03), (0.028, 0.028)])
        H.frustum("head", "cyan", (s * 0.1, 0.63, 0.3), (s * 0.1, 0.72, 0.3), (0.06, 0.06), (0.06, 0.06))
    H.frustum("head", "dark", (0, 0.3, 0.3), (0, 0.3, 0.46), (0.14, 0.08), (0.07, 0.05))


def claw(s):
    """Arm in two dark stubs on the body; the big palm and both jaws ride on the claw bone (claw.L / claw.R)."""
    bone = "claw.L" if s > 0 else "claw.R"
    H.frustum("body", "dark", (s * 0.18, 0.3, 0.28), (s * 0.3, 0.32, 0.4), (0.09, 0.09), (0.12, 0.11))
    H.frustum(bone, "dark_lt", (s * 0.3, 0.32, 0.38), (s * 0.38, 0.33, 0.52), (0.1, 0.1), (0.13, 0.13))
    H.frustum(bone, "teal", (s * 0.38, 0.33, 0.48), (s * 0.44, 0.34, 0.8), (0.14, 0.16), (0.21, 0.22))        # palm
    H.frustum(bone, "teal", (s * 0.44, 0.34, 0.78), (s * 0.42, 0.34, 0.95), (0.21, 0.22), (0.12, 0.12))
    H.chain(bone, "teal", [(s * 0.44, 0.42, 0.8), (s * 0.4, 0.43, 0.96), (s * 0.3, 0.4, 1.14)], [(0.1, 0.09), (0.08, 0.08), (0.015, 0.015)])
    H.chain(bone, "teal_dk", [(s * 0.44, 0.26, 0.8), (s * 0.4, 0.26, 0.96), (s * 0.3, 0.3, 1.12)], [(0.09, 0.07), (0.07, 0.06), (0.015, 0.015)])


def leg(n, sx, sz, dz):
    hx, hz = sx * 0.22, sz * 0.2 + dz
    hip = (hx, HIP_Y, hz)
    knee = (hx + sx * 0.26, HIP_Y + 0.08, hz + sz * 0.1)       # pieces splay wider than the bones' pivots
    foot = (knee[0] + sx * 0.2, 0.02, knee[2] + sz * 0.1)
    H.frustum(f"leg{n}.upper", "dark", (hx, HIP_Y + 0.02, hz), knee, (0.07, 0.07), (0.055, 0.055))
    H.frustum(f"leg{n}.lower", "teal", (knee[0] - sx * 0.02, knee[1] + 0.02, knee[2]), foot, (0.07, 0.07), (0.012, 0.012))
    return hip, knee, foot


def make():
    shell()
    eyes()
    for s in (-1, 1):
        claw(s)
    for n, sx, sz in LEGS:
        leg(n, sx, sz, 0)
        leg(n, sx, sz, -sz * 0.15)


def joints():
    out = {"body": ((0, 0.3, -0.36), (0, 0.32, 0.2)), "head": ((0, 0.32, 0.2), (0, 0.34, 0.4))}
    for n, sx, sz in LEGS:
        hip, knee, foot = (leg_geo(n, sx, sz))
        out[f"leg{n}.upper"] = (hip, knee)
        out[f"leg{n}.lower"] = (knee, foot)
    return out


def leg_geo(n, sx, sz):
    hx, hz = sx * 0.22, sz * 0.2
    hip = (hx, HIP_Y, hz)
    knee = (hx + sx * UP[0] * A, HIP_Y + UP[1] * A, hz + sz * UP[2] * A)
    return hip, knee, (knee[0] + sx * LO[0] * A, HIP_Y + (UP[1] + LO[1]) * A, knee[2] + sz * LO[2] * A)


EXTRAS = [("claw.L", "body", (0.2, 0.32, 0.3), (0.34, 0.34, 1.0)),
          ("claw.R", "body", (-0.2, 0.32, 0.3), (-0.34, 0.34, 1.0))]
H.build("n00W", "crawler", PALETTE, make, joints(), extras=EXTRAS)
