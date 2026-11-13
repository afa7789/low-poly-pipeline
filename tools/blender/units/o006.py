"""Defensive Kodo Rider (o006): orc de mascara com escudo redondo erguido e lanca, sobre rinoceronte blindado.

    blender -b --factory-startup -P tools/blender/units/o006.py -- <out.glb>

Cavaleiro aumentado alem da prancha (assento->cabeca ~46 % da altura, escudo incluso); lanca grande a frente, longe da montaria.
Os bracos sao modelados como na prancha (esq. erguido); as juntas dos ossos seguem o corpo modelado.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "hide": 0xB39A62, "hide_dk": 0x8F7A4B, "belly": 0x4E3A2A, "plate": 0x8E909A, "plate_dk": 0x6E707A,
    "leather": 0x7A3E34, "horn": 0xDCCCA2, "eye": 0xE82020, "skin": 0x5BC13C, "skin_dk": 0x46A02C,
    "mask": 0x7A5238, "band": 0xA0243C, "pants": 0x5A3A28, "shield": 0x7C1E32, "rim": 0xA02C44,
    "pot": 0x80483A, "wood": 0x4F4F56, "steel": 0xA6A8B0, "boot": 0x2E2118,
}

LEG_X, FORE_Z, HIND_Z = 0.42, 0.58, -0.58
SEAT = 1.3
HEAD_TOP = 2.75


def mount():
    H.frustum("spine.1", "hide", (0, 0.78, -0.95), (0, 0.78, -0.02), (0.38, 0.4), (0.52, 0.42), sides=8)
    H.frustum("spine.2", "hide", (0, 0.78, -0.04), (0, 0.8, 0.7), (0.52, 0.42), (0.5, 0.44), sides=8)
    H.frustum("spine.2", "hide_dk", (0, 0.4, -0.1), (0, 0.4, 0.6), (0.4, 0.3), (0.38, 0.3), sides=8)
    H.frustum("spine.2", "hide", (0, 0.82, 0.55), (0, 0.8, 0.95), (0.44, 0.42), (0.36, 0.34), sides=8)
    H.frustum("spine.1", "belly", (0, 0.36, -0.7), (0, 0.36, 0.0), (0.4, 0.3), (0.44, 0.3), sides=8)


def plates():
    for bone, z, w in (("spine.1", -0.85, 0.36), ("spine.1", -0.6, 0.46), ("spine.1", -0.35, 0.5),
                       ("spine.2", 0.4, 0.52), ("spine.2", 0.62, 0.5), ("spine.2", 0.84, 0.42)):
        H.frustum(bone, "plate", (0, 1.1, z), (0, 1.42, z), (w + 0.12, 0.13), (w - 0.06, 0.12), sides=4)
        H.frustum(bone, "plate_dk", (0, 1.38, z), (0, 1.46, z), (w - 0.06, 0.12), (w - 0.14, 0.11), sides=4)
    H.box("spine.2", "leather", (0, 1.24, 0.03), (0.78, 0.2, 0.62))
    H.box("spine.2", "leather", (0, 1.34, -0.2), (0.5, 0.18, 0.18))


def head():
    H.frustum("head", "hide", (0, 0.88, 0.72), (0, 0.72, 1.32), (0.4, 0.38), (0.3, 0.26), sides=8)
    H.frustum("head", "hide_dk", (0, 0.58, 1.0), (0, 0.56, 1.34), (0.24, 0.12), (0.22, 0.1), sides=6)
    H.frustum("head", "hide", (0, 0.88, 1.2), (0, 0.9, 1.48), (0.2, 0.2), (0.15, 0.13), sides=6)
    H.frustum("head", "horn", (0, 0.92, 1.4), (0, 1.5, 1.82), (0.13, 0.15), (0.015, 0.015), sides=6)
    H.frustum("head", "horn", (0, 1.0, 1.1), (0, 1.12, 1.18), (0.07, 0.07), (0.03, 0.03), sides=4)
    for s in (-1, 1):
        H.frustum("head", "eye", (s * 0.22, 0.95, 1.2), (s * 0.27, 0.97, 1.28), (0.05, 0.04), (0.035, 0.03), sides=4)
        H.frustum("head", "horn", (s * 0.18, 0.6, 1.36), (s * 0.26, 0.74, 1.48), (0.04, 0.04), (0.012, 0.012), sides=4)
        H.frustum("head", "hide_dk", (s * 0.3, 1.16, 0.84), (s * 0.4, 1.38, 0.82), (0.07, 0.05), (0.03, 0.03), sides=4)


def tail():
    H.chain(("tail.1", "tail.2"), "hide", [(0, 0.82, -0.9), (0, 0.66, -1.35), (0, 0.5, -1.95)],
            [(0.2, 0.18), (0.14, 0.12), (0.02, 0.02)], sides=6)


def legs():
    for s, front, hind in ((1, "leg1", "leg3"), (-1, "leg2", "leg4")):
        for tag, z in ((front, FORE_Z), (hind, HIND_Z)):
            x = s * LEG_X
            H.frustum(f"{tag}.upper", "hide", (x, 0.95, z), (x, 0.5, z), (0.28, 0.3), (0.19, 0.2), sides=8)
            H.frustum(f"{tag}.lower", "hide_dk", (x, 0.55, z), (x, 0.15, z), (0.2, 0.21), (0.19, 0.2), sides=8)
            H.frustum(f"{tag}.lower", "hide", (x, 0.18, z), (x, 0.06, z + 0.02), (0.21, 0.22), (0.26, 0.28), sides=8)
            H.frustum(f"{tag}.lower", "horn", (x, 0.1, z + 0.1), (x, 0.0, z + 0.2), (0.2, 0.05), (0.24, 0.05), sides=6)


def bags():
    for s, r in ((1, 0.3), (-1, 0.24)):
        H.frustum("spine.2", "pot", (s * 0.66, 0.5, -0.25), (s * 0.7, 0.95, -0.25), (r * 0.8, r), (r, r * 1.1), sides=8)
        H.frustum("spine.2", "belly", (s * 0.68, 0.93, -0.25), (s * 0.69, 1.03, -0.25), (r * 0.6, r * 0.6), (r * 0.3, r * 0.3), sides=6)


def rider_body():
    H.frustum("rider.spine", "pants", (0, 1.25, 0.02), (0, 1.6, 0.04), (0.38, 0.3), (0.34, 0.26), sides=8)
    H.frustum("rider.spine", "skin", (0, 1.58, 0.04), (0, 2.34, 0.14), (0.3, 0.24), (0.5, 0.3), sides=8)
    H.frustum("rider.spine", "leather", (0, 1.58, 0.04), (0, 1.68, 0.04), (0.33, 0.26), (0.33, 0.26), sides=8)
    H.frustum("rider.spine", "leather", (0.2, 2.34, 0.4), (-0.2, 1.72, 0.3), (0.05, 0.03), (0.05, 0.03), sides=4)
    H.frustum("rider.spine", "leather", (-0.2, 2.34, 0.4), (0.2, 1.72, 0.3), (0.05, 0.03), (0.05, 0.03), sides=4)
    H.frustum("rider.head", "skin", (0, 2.3, 0.12), (0, 2.62, 0.14), (0.24, 0.24), (0.3, 0.28), sides=8)
    H.frustum("rider.head", "mask", (0, 2.34, 0.3), (0, 2.5, 0.44), (0.16, 0.08), (0.2, 0.1), sides=6)
    H.frustum("rider.head", "band", (0, 2.56, 0.14), (0, 2.68, 0.14), (0.31, 0.29), (0.31, 0.29), sides=8)
    H.frustum("rider.head", "skin_dk", (0, 2.66, 0.14), (0, HEAD_TOP, 0.14), (0.28, 0.26), (0.17, 0.16), sides=8)
    for s in (-1, 1):
        H.frustum("rider.head", "skin", (s * 0.28, 2.52, 0.12), (s * 0.5, 2.68, 0.1), (0.06, 0.04), (0.012, 0.012), sides=4)
        H.frustum("rider.head", "eye", (s * 0.1, 2.52, 0.37), (s * 0.12, 2.53, 0.4), (0.04, 0.025), (0.03, 0.02), sides=4)
        H.frustum("rider.spine", "skin", (s * 0.3, 2.34, 0.1), (s * 0.5, 2.2, 0.1), (0.18, 0.2), (0.2, 0.2), sides=6)


def rider_legs():
    for s in (-1, 1):
        H.frustum("spine.2", "pants", (s * 0.2, 1.4, 0.0), (s * 0.55, 1.12, 0.2), (0.17, 0.2), (0.13, 0.14), sides=6)
        H.frustum("spine.2", "pants", (s * 0.55, 1.14, 0.2), (s * 0.62, 0.8, 0.14), (0.14, 0.15), (0.11, 0.12), sides=6)
        H.frustum("spine.2", "boot", (s * 0.62, 0.82, 0.12), (s * 0.64, 0.62, 0.32), (0.12, 0.13), (0.15, 0.1), sides=6)


def shield_arm():
    H.frustum("rider.arm.L", "skin", (0.5, 2.2, 0.1), (0.76, 2.55, 0.14), (0.2, 0.19), (0.16, 0.16), sides=6)
    H.frustum("rider.forearm.L", "skin", (0.76, 2.55, 0.14), (0.82, 2.88, 0.14), (0.15, 0.15), (0.14, 0.14), sides=6)
    H.frustum("rider.forearm.L", "skin_dk", (0.82, 2.86, 0.14), (0.84, 3.0, 0.14), (0.18, 0.18), (0.14, 0.14), sides=6)
    H.frustum("rider.forearm.L", "wood", (0.3, 2.96, 0.14), (1.2, 2.96, 0.14), (0.06, 0.06), (0.06, 0.06), sides=4)
    H.frustum("rider.forearm.L", "rim", (0.62, 2.9, 0.06), (0.62, 2.9, -0.08), (0.52, 0.52), (0.52, 0.52), sides=12)
    H.frustum("rider.forearm.L", "shield", (0.62, 2.9, 0.07), (0.62, 2.9, 0.1), (0.46, 0.46), (0.4, 0.4), sides=12)


def spear():
    H.frustum("rider.arm.R", "skin", (-0.5, 2.2, 0.1), (-0.72, 1.82, 0.14), (0.2, 0.19), (0.16, 0.16), sides=6)
    H.frustum("rider.forearm.R", "skin", (-0.72, 1.82, 0.14), (-0.8, 1.55, 0.2), (0.15, 0.15), (0.14, 0.14), sides=6)
    H.frustum("rider.forearm.R", "skin_dk", (-0.8, 1.6, 0.2), (-0.82, 1.4, 0.26), (0.18, 0.18), (0.15, 0.15), sides=6)
    H.frustum("rider.forearm.R", "wood", (-0.82, 1.3, -0.5), (-0.84, 1.62, 1.5), (0.06, 0.06), (0.06, 0.06), sides=6)
    H.frustum("rider.forearm.R", "steel", (-0.84, 1.62, 1.5), (-0.84, 1.7, 2.2), (0.16, 0.05), (0.01, 0.01), sides=4)
    H.frustum("rider.forearm.R", "plate_dk", (-0.84, 1.6, 1.42), (-0.84, 1.64, 1.52), (0.1, 0.1), (0.09, 0.09), sides=6)


def make():
    mount()
    plates()
    head()
    tail()
    legs()
    bags()
    rider_body()
    rider_legs()
    shield_arm()
    spear()


def joints():
    out = {"head": ((0, 0.85, 0.7), (0, 0.8, 1.3)),
           "tail.1": ((0, 0.82, -0.9), (0, 0.66, -1.35)), "tail.2": ((0, 0.66, -1.35), (0, 0.5, -1.95)),
           "rider.spine": ((0, SEAT, 0.02), (0, 2.3, 0.12)), "rider.head": ((0, 2.3, 0.12), (0, HEAD_TOP, 0.14)),
           "rider.arm.L": ((0.5, 2.2, 0.1), (0.76, 2.55, 0.14)), "rider.forearm.L": ((0.76, 2.55, 0.14), (0.82, 2.95, 0.14)),
           "rider.arm.R": ((-0.5, 2.2, 0.1), (-0.72, 1.82, 0.14)), "rider.forearm.R": ((-0.72, 1.82, 0.14), (-0.82, 1.4, 0.26))}
    for s, f, h in ((1, "leg1", "leg3"), (-1, "leg2", "leg4")):
        for tag, z in ((f, FORE_Z), (h, HIND_Z)):
            out[f"{tag}.upper"] = ((s * LEG_X, 0.95, z), (s * LEG_X, 0.52, z))
            out[f"{tag}.lower"] = ((s * LEG_X, 0.52, z), (s * LEG_X, 0.06, z))
    return out


H.build("o006", "mounted", PALETTE, make, joints())
