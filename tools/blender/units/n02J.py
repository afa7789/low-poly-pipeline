"""Goliath (n02J, walker): measured on artifacts/model-sheets/refs/n02J/sheet.jpg (0.0034 m per pixel).

    blender -b --factory-startup -P tools/blender/units/n02J.py -- <out.glb>

A squat armoured machine on two bent legs, a yellow-visored head block on its front, two long
cannons rising from the rear shoulders, brass tanks on the flanks and a missile rack on the back.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "iron": 0x3E4048, "iron_dk": 0x2C2E34, "iron_lt": 0x4C4E57, "brass": 0x8A6A2E, "brass_dk": 0x6A4F22,
    "yellow": 0xFFE81A,
}

LEG_X, HIP_Y, KNEE_Y, ANK_Y, LEG_Z = 0.45, 0.95, 0.58, 0.12, 0.05
BASE, TIP = (0.45, 1.7, -0.25), (0.85, 2.88, 0.74)     # cannon root and muzzle (left side)


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def body():
    H.frustum("pelvis", "iron_dk", (0, 0.77, 0.0), (0, 1.1, 0.0), (0.26, 0.3), (0.36, 0.4), sides=8)
    H.frustum("pelvis", "iron", (0, 1.05, 0.15), (0, 1.5, 0.15), (0.38, 0.5), (0.42, 0.52), sides=8)
    H.frustum("pelvis", "iron_lt", (0, 1.45, 0.1), (0, 1.92, -0.08), (0.42, 0.5), (0.34, 0.36), sides=8)
    H.frustum("pelvis", "brass", (-0.32, 0.84, -0.05), (0.32, 0.84, -0.05), (0.05, 0.07), (0.05, 0.07), sides=6)
    for s in (-1, 1):       # brass tanks lying along z on the flanks, with darker bands
        H.frustum("pelvis", "brass", (s * 0.56, 1.22, -0.44), (s * 0.56, 1.22, -0.02), (0.2, 0.17), (0.19, 0.16), sides=8)
        for z in (-0.38, -0.2, -0.06):
            H.frustum("pelvis", "brass_dk", (s * 0.56, 1.22, z - 0.025), (s * 0.56, 1.22, z + 0.025), (0.215, 0.185), (0.215, 0.185), sides=8)
    for x in (-0.34, -0.14, 0.14, 0.34):   # missile rack on the back
        H.frustum("pelvis", "iron_lt", (x, 1.5, -0.5), (x, 2.0, -0.52), (0.08, 0.07), (0.09, 0.08), sides=6)
        H.frustum("pelvis", "iron_dk", (x, 2.0, -0.52), (x, 2.08, -0.52), (0.06, 0.06), (0.04, 0.04), sides=6)
    H.frustum("pelvis", "iron_dk", (0, 1.5, -0.46), (0, 1.95, -0.46), (0.4, 0.06), (0.36, 0.06), sides=4)


def head():
    H.frustum("head", "iron_dk", (0, 1.92, 0.12), (0, 1.92, 0.62), (0.22, 0.2), (0.18, 0.2), sides=8)
    H.frustum("head", "iron_lt", (0, 1.92, 0.4), (0, 1.92, 0.64), (0.2, 0.21), (0.19, 0.2), sides=8)
    H.frustum("head", "yellow", (0, 1.92, 0.63), (0, 1.92, 0.69), (0.1, 0.15), (0.1, 0.15), sides=8)


def cannon(s, side):
    t = tuple(b - a for a, b in zip(BASE, TIP))
    stops = [(0.0, 0.16), (0.14, 0.13), (0.15, 0.1), (0.42, 0.085), (0.44, 0.052), (0.94, 0.05), (0.95, 0.075), (1.0, 0.07)]
    pts = [tuple(BASE[i] + t[i] * k for i in range(3)) for k, _ in stops]
    pts = [(s * p[0], p[1], p[2]) for p in pts]
    tones = ["iron_lt", "iron_lt", "iron", "iron", "iron_dk", "iron_lt", "iron_lt"]
    for i, tone in enumerate(tones):
        H.frustum(f"barrel.{side}", tone, pts[i], pts[i + 1], (stops[i][1],) * 2, (stops[i + 1][1],) * 2, sides=8)
    a = (s * BASE[0], BASE[1] - 0.02, BASE[2])
    H.frustum(f"barrel.{side}", "iron", a, (s * 0.5, 1.82, -0.08), (0.2, 0.2), (0.16, 0.16), sides=8)   # shoulder housing


def leg(s, side):
    x = s * 0.42
    H.frustum(f"thigh.{side}", "iron", (x, 1.04, -0.1), (s * 0.48, 0.8, 0.1), (0.19, 0.17), (0.17, 0.16), sides=6)
    H.frustum(f"thigh.{side}", "iron_lt", (s * 0.48, 0.82, 0.08), (s * 0.48, 0.6, 0.2), (0.17, 0.16), (0.14, 0.13), sides=6)
    H.frustum(f"thigh.{side}", "iron_dk", (s * 0.34, 1.0, -0.06), (s * 0.34, 1.0, 0.04), (0.1, 0.1), (0.1, 0.1), sides=6)
    H.frustum(f"shin.{side}", "iron_lt", (s * 0.47, 0.64, 0.2), (s * 0.45, 0.48, 0.14), (0.14, 0.13), (0.11, 0.1), sides=6)
    H.frustum(f"shin.{side}", "iron", (s * 0.45, 0.5, 0.14), (s * 0.42, 0.2, 0.0), (0.11, 0.1), (0.07, 0.07), sides=6)
    H.frustum(f"shin.{side}", "iron_dk", (s * 0.42, 0.22, 0.0), (s * 0.43, 0.1, 0.0), (0.08, 0.08), (0.13, 0.12), sides=6)
    H.frustum(f"foot.{side}", "iron_dk", (s * 0.5, 0.15, -0.14), (s * 0.5, 0.08, 0.02), (0.15, 0.1), (0.2, 0.14), sides=6)
    H.frustum(f"foot.{side}", "iron_dk", (s * 0.5, 0.09, 0.0), (s * 0.5, 0.03, 0.66), (0.2, 0.12), (0.18, 0.04), sides=4)


def make():
    body()
    head()
    for s, side in ((1, "L"), (-1, "R")):
        cannon(s, side)
        leg(s, side)


def joints():
    out = {"pelvis": ((0, 0.9, 0), (0, 1.2, 0)), "head": ((0, 1.9, 0.2), (0, 1.95, 0.7))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"barrel.{side}"] = ((s * 0.45, 1.75, -0.2), (s * 0.52, 1.96, 0.29))
        x = s * LEG_X
        out[f"thigh.{side}"] = ((x, HIP_Y, LEG_Z), (x, KNEE_Y, LEG_Z))
        out[f"shin.{side}"] = ((x, KNEE_Y, LEG_Z), (x, ANK_Y, LEG_Z))
        out[f"foot.{side}"] = ((x, ANK_Y, LEG_Z), (x, 0.08, 0.6))
    return out


H.build("n02J", "walker", PALETTE, make, joints())
