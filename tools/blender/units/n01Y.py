"""Dragonhawk Rider (n01Y), bird_rider: measured on artifacts/model-sheets/refs/n01Y/sheet.jpg (top view 330 px per
metre, z=0 over the rider's back, bird's beak at z=+1.05, wing tips at x=+-1.4, tail feathers to z=-1.45).

    blender -b --factory-startup -P tools/blender/units/n01Y.py -- <out.glb>

The sheet draws the trench-soldier tiny on a big hawk; here the rider is enlarged (seat 1.25 m to helmet top 2.4 m,
48 % of the unit's height) and the bayonet rifle is oversized, held forward at y=1.8 m, well above the wings.
Rifle on rider.forearm.R, round cross shield on rider.forearm.L, both the rider's own bones.
Bird bones keep the family's table (wings and rider joints are moved onto the model).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "yellow": 0xE2B23C, "yellow_dk": 0xB98B2C, "orange": 0xE0622A, "teal": 0x2E8C7C, "spot": 0x2A2622,
    "helm": 0x586A7C, "steel": 0xA8B0B8, "steel_dk": 0x5A5F66, "olive": 0x5E5C36, "olive_dk": 0x464428,
    "wood": 0x5A3626, "strap": 0x3A2418, "lens": 0x9ED8E0, "mask": 0x34342F, "hair": 0xD8B860,
    "skin": 0x9AA7A0, "boot": 0x2A2218, "shield": 0x62748A, "cross": 0x39475A,
}
SHOULDER, WRIST, TIP = (0.22, 1.2, 0.2), (0.76, 1.4, 0.12), (1.4, 1.27, -0.08)      # wing1; wing2 mirrors x


# Montaria na escala da prancha (x S); piloto ~36 % da altura (x R) sentado no dorso, fuzil exagerado.
S, R = 1.5, 0.9
MOUNT = {"k": S, "piv": (0.0, 0.0, 0.0), "org": (0.0, 0.0, 0.0)}
RIDER = {"k": R, "piv": (0.0, 1.3, 0.1), "org": (0.0, 1.3 * S, 0.1 * S + 0.05)}
XF = dict(MOUNT)


def use(xf):
    XF.update(xf)


def T(p, xf=None):
    xf = xf or XF
    return tuple(o + xf["k"] * (c - v) for c, v, o in zip(p, xf["piv"], xf["org"]))


def rad(r):
    return tuple(v * XF["k"] for v in r)


def fr(bone, tone, a, b, ra, rb, sides=8):
    H.frustum(bone, tone, T(a), T(b), rad(ra), rad(rb), sides)


def chain(bones, tone, pts, radii, sides=6):
    H.chain(bones, tone, [T(p) for p in pts], [rad(r) for r in radii], sides)


def panel(bone, tone, pts, thickness=0.03):
    return H.panel(bone, tone, [T(p) for p in pts], thickness=thickness * XF["k"])


def box(bone, tone, centre, size):
    H.box(bone, tone, T(centre), tuple(v * XF["k"] for v in size))


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def flip(p, s):
    return (p[0] * s, p[1], p[2])


def body():
    fr("spine.1", "yellow", (0, 1.0, -0.45), (0, 1.08, 0.1), (0.14, 0.12), (0.28, 0.27), sides=8)
    fr("spine.2", "yellow", (0, 1.08, 0.1), (0, 1.18, 0.45), (0.28, 0.27), (0.2, 0.2), sides=8)
    fr("spine.2", "teal", (0, 1.0, 0.3), (0, 1.1, 0.56), (0.17, 0.2), (0.14, 0.18), sides=6)
    fr("spine.1", "yellow_dk", (0, 0.8, -0.2), (0, 0.82, 0.12), (0.12, 0.05), (0.2, 0.05), sides=4)
    chain(("neck.1", "neck.2"), "teal", [(0, 1.2, 0.4), (0, 1.4, 0.52), (0, 1.6, 0.64)], [(0.2, 0.2), (0.15, 0.15), (0.11, 0.11)], sides=6)


def head():
    fr("head", "teal", (0, 1.6, 0.6), (0, 1.62, 0.95), (0.12, 0.12), (0.1, 0.1), sides=6)
    fr("head", "orange", (0, 1.58, 0.9), (0, 1.5, 1.2), (0.07, 0.06), (0.01, 0.01), sides=6)
    for s in (-1, 1):
        fr("head", "teal", (s * 0.07, 1.68, 0.68), (s * 0.12, 1.84, 0.46), (0.03, 0.04), (0.008, 0.008), sides=4)
        fr("head", "yellow", (s * 0.1, 1.64, 0.82), (s * 0.11, 1.64, 0.86), (0.03, 0.03), (0.03, 0.03), sides=4)


def bird_legs():
    for s, n in ((1, 1), (-1, 2)):
        fr(f"leg{n}.upper", "yellow", (s * 0.22, 1.0, 0.05), (s * 0.25, 0.8, 0.12), (0.15, 0.14), (0.08, 0.08), sides=6)
        fr(f"leg{n}.lower", "orange", (s * 0.25, 0.82, 0.12), (s * 0.27, 0.66, 0.3), (0.06, 0.06), (0.045, 0.045), sides=6)
        for dx in (-0.08, 0, 0.08):
            fr(f"leg{n}.lower", "orange", (s * 0.27 + dx * 0.4, 0.68, 0.3), (s * 0.27 + dx, 0.56, 0.58), (0.045, 0.035), (0.01, 0.01), sides=4)


def tail():
    zs, ys, bones = (-0.35, -0.75, -1.15, -1.55), (1.0, 0.95, 0.9, 0.85), ("tail.1", "tail.2", "tail.3")
    for dx, tone in ((-1, "yellow"), (0, "yellow"), (1, "yellow")):
        pts = [(dx * k, ys[i] + 0.0, zs[i]) for i, k in enumerate((0.0, 0.08, 0.15, 0.22))]
        chain(bones, tone, pts, [(0.1, 0.025), (0.15, 0.025), (0.16, 0.025), (0.02, 0.02)], sides=4)
        fr("tail.3", "spot", (pts[3][0], 0.86, -1.3), (pts[3][0], 0.86, -1.4), (0.04, 0.04), (0.04, 0.04), sides=6)


def wing(s, n):
    up, low = f"wing{n}.upper", f"wing{n}.lower"
    sh, wr, tip = flip(SHOULDER, s), flip(WRIST, s), flip(TIP, s)
    fr(up, "yellow_dk", sh, wr, (0.12, 0.07), (0.08, 0.06), sides=6)
    fr(low, "yellow_dk", wr, tip, (0.08, 0.06), (0.02, 0.02), sides=6)
    panel(up, "yellow", [sh, wr, (wr[0] - s * 0.02, wr[1] - 0.02, -0.5), (sh[0], sh[1] - 0.0, -0.4)])
    for i in range(5):                   # trailing feathers: yellow, with an orange tip
        b0, b1 = lerp(wr, tip, i / 5), lerp(wr, tip, (i + 1) / 5)
        mid = lerp(b0, b1, 0.5)
        apex = (mid[0] + s * 0.1, mid[1] - 0.04, mid[2] - 0.8 + i * 0.03)
        panel(low, "yellow", [b0, b1, apex], 0.03)
        panel(low, "orange", [apex, lerp(apex, b0, 0.5), lerp(apex, b1, 0.5)], 0.045)


def rider_torso():
    fr("rider.spine", "olive", (0, 1.3, 0.1), (0, 1.6, 0.12), (0.28, 0.22), (0.3, 0.24), sides=8)
    fr("rider.spine", "olive", (0, 1.55, 0.12), (0, 1.95, 0.14), (0.3, 0.24), (0.46, 0.27), sides=8)
    fr("rider.spine", "olive_dk", (0, 1.5, 0.08), (0, 1.14, -0.12), (0.3, 0.24), (0.5, 0.4), sides=8)   # coat skirt
    fr("rider.spine", "strap", (0.3, 1.92, 0.38), (-0.22, 1.48, 0.36), (0.035, 0.02), (0.035, 0.02), sides=4)
    for s in (-1, 1):
        fr("rider.spine", "helm", (s * 0.34, 2.0, 0.12), (s * 0.52, 1.88, 0.12), (0.12, 0.18), (0.18, 0.2), sides=6)   # pauldron
        fr("rider.spine", "olive", (s * 0.2, 1.4, 0.1), (s * 0.4, 1.22, 0.3), (0.14, 0.15), (0.12, 0.13), sides=6)    # thigh
        fr("rider.spine", "olive_dk", (s * 0.4, 1.24, 0.3), (s * 0.42, 1.0, 0.28), (0.12, 0.13), (0.1, 0.11), sides=6)
        fr("rider.spine", "boot", (s * 0.42, 1.02, 0.28), (s * 0.43, 0.86, 0.4), (0.1, 0.1), (0.13, 0.09), sides=6)


def rider_head():
    fr("rider.head", "skin", (0, 1.96, 0.14), (0, 2.2, 0.15), (0.17, 0.16), (0.2, 0.18), sides=8)
    fr("rider.head", "helm", (0, 2.18, 0.15), (0, 2.42, 0.15), (0.25, 0.23), (0.14, 0.13), sides=8)
    fr("rider.head", "helm", (0, 2.2, 0.15), (0, 2.25, 0.15), (0.27, 0.25), (0.25, 0.23), sides=8)
    fr("rider.head", "mask", (0, 2.08, 0.28), (0, 2.04, 0.44), (0.1, 0.1), (0.07, 0.07), sides=6)
    fr("rider.head", "hair", (0, 2.1, 0.0), (0, 1.9, -0.08), (0.12, 0.08), (0.09, 0.05), sides=6)
    for s in (-1, 1):
        fr("rider.head", "lens", (s * 0.09, 2.14, 0.31), (s * 0.09, 2.14, 0.35), (0.05, 0.05), (0.05, 0.05), sides=6)
        fr("rider.head", "skin", (s * 0.18, 2.12, 0.12), (s * 0.4, 2.2, 0.06), (0.05, 0.03), (0.01, 0.01), sides=4)


def rifle_arm():
    """Right arm out in front, the oversized bayonet rifle level at y=1.8 clear of the wings."""
    fr("rider.arm.R", "olive", (-0.5, 1.92, 0.12), (-0.54, 1.78, 0.15), (0.22, 0.21), (0.2, 0.2), sides=6)
    fr("rider.arm.R", "olive", (-0.54, 1.78, 0.15), (-0.62, 1.82, 0.2), (0.2, 0.2), (0.17, 0.17), sides=6)
    fr("rider.forearm.R", "olive", (-0.62, 1.82, 0.2), (-0.5, 1.99, 0.4), (0.17, 0.17), (0.15, 0.15), sides=6)
    fr("rider.forearm.R", "strap", (-0.5, 1.98, 0.38), (-0.44, 2.05, 0.52), (0.13, 0.14), (0.16, 0.16), sides=6)    # glove
    fr("rider.forearm.R", "wood", (-0.42, 1.97, -0.2), (-0.42, 2.05, 0.5), (0.11, 0.15), (0.08, 0.08), sides=6)     # stock
    chain("rider.forearm.R", "steel_dk", [(-0.42, 2.05, 0.45), (-0.42, 2.07, 1.0), (-0.42, 2.09, 1.5)], [(0.08, 0.08), (0.07, 0.07), (0.08, 0.08)], sides=6)
    fr("rider.forearm.R", "steel", (-0.42, 2.10, 1.5), (-0.42, 2.13, 2.3), (0.025, 0.07), (0.006, 0.006), sides=4)  # bayonet


def shield_arm():
    fr("rider.arm.L", "olive", (0.5, 1.92, 0.12), (0.55, 1.78, 0.12), (0.22, 0.21), (0.2, 0.2), sides=6)
    fr("rider.arm.L", "olive", (0.55, 1.78, 0.12), (0.58, 1.66, 0.14), (0.15, 0.15), (0.12, 0.12), sides=6)
    fr("rider.forearm.L", "olive", (0.58, 1.66, 0.14), (0.66, 1.76, 0.26), (0.12, 0.12), (0.13, 0.13), sides=6)
    fr("rider.forearm.L", "strap", (0.64, 1.74, 0.24), (0.7, 1.8, 0.3), (0.14, 0.14), (0.16, 0.16), sides=6)
    fr("rider.forearm.L", "shield", (0.74, 1.8, 0.28), (0.8, 1.8, 0.28), (0.36, 0.36), (0.34, 0.34), sides=12)
    box("rider.forearm.L", "cross", (0.82, 1.8, 0.28), (0.03, 0.56, 0.09))
    box("rider.forearm.L", "cross", (0.82, 1.8, 0.28), (0.03, 0.09, 0.56))


def make():
    use(MOUNT)
    body()
    head()
    bird_legs()
    tail()
    wing(1, 1)
    wing(-1, 2)
    use(RIDER)
    rider_torso()
    rider_head()
    rifle_arm()
    shield_arm()


def joints():
    r = {"rider.spine": ((0, 1.3, 0.1), (0, 1.95, 0.12)), "rider.head": ((0, 1.95, 0.12), (0, 2.42, 0.15)),
         "rider.arm.L": ((0.5, 1.92, 0.12), (0.58, 1.66, 0.14)), "rider.forearm.L": ((0.58, 1.66, 0.14), (0.62, 1.4, 0.14)),
         "rider.arm.R": ((-0.5, 1.92, 0.12), (-0.62, 1.82, 0.2)), "rider.forearm.R": ((-0.62, 1.82, 0.2), (-0.62, 1.4, 0.2))}
    out = {k: tuple(T(p, RIDER) for p in v) for k, v in r.items()}
    for s, n in ((1, 1), (-1, 2)):
        out[f"wing{n}.upper"] = tuple(T(p, MOUNT) for p in (flip(SHOULDER, s), flip(WRIST, s)))
        out[f"wing{n}.lower"] = tuple(T(p, MOUNT) for p in (flip(WRIST, s), flip(TIP, s)))
    return out


H.build("n01Y", "bird_rider", PALETTE, make, joints())
