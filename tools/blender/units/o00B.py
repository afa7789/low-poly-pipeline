"""Spellbreaker Kodo Rider (o00B): orc de capacete de aco com lanca vertical sobre rinoceronte blindado.

    blender -b --factory-startup -P tools/blender/units/o00B.py -- <out.glb>

Montaria no tamanho da prancha (copia da o006); cavaleiro aumentado (assento->capacete ~46 % da altura com a lanca),
lanca alta e grossa de pe na mao direita, mao esquerda apoiada na montaria. Placas de aco nos flancos, chifre longo.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "hide": 0xA08868, "hide_dk": 0x7A664C, "belly": 0x4E3A2A, "plate": 0x8E909A, "plate_dk": 0x6E707A,
    "leather": 0x9A1E38, "horn": 0xDCCCA2, "eye": 0xE82020, "skin": 0x5BC13C, "skin_dk": 0x46A02C,
    "mask": 0x7A5238, "band": 0xA0243C, "pants": 0x5A3A28, "shield": 0x7C1E32, "rim": 0xA02C44,
    "pot": 0x80483A, "wood": 0x4F4F56, "steel": 0xA6A8B0, "boot": 0x2E2118, "strap": 0x6B4630,
}

LEG_X, FORE_Z, HIND_Z = 0.42, 0.58, -0.58
KX, KY, KZ = 2.1, 1.95, 1.4  # the sheet's kodo is the big mass: back ~60 % of the unit's height, deep chest, long legs
R = 1.05  # rider height scale: seat -> helmet top ~34 % of the unit's height
SEAT = 2.15


def sc(p):
    return (p[0] * KX, p[1] * KY, p[2] * KZ)


def rad(r):
    return (r[0] * KX, r[1] * (KY + KZ) / 2)


def F(bone, tone, a, b, ra, rb, sides=8):
    H.frustum(bone, tone, sc(a), sc(b), rad(ra), rad(rb), sides)


def Bx(bone, tone, c, size):
    H.box(bone, tone, sc(c), sc(size))


def C(bones, tone, pts, radii, sides=6):
    H.chain(bones, tone, [sc(p) for p in pts], [rad(r) for r in radii], sides)


def m(p):
    return (p[0] * 0.9, SEAT + (p[1] - 1.3) * R, p[2] * 0.9)


def RF(bone, tone, a, b, ra, rb, sides=8):
    H.frustum(bone, tone, m(a), m(b), (ra[0] * 1.1, ra[1] * 1.1), (rb[0] * 1.1, rb[1] * 1.1), sides)


def leg_m(p):
    return (p[0] * KX, SEAT + (p[1] - 1.3) * 1.3, p[2])
HEAD_TOP = 2.85


def mount():
    F("spine.1", "hide", (0, 0.78, -0.95), (0, 0.78, -0.02), (0.38, 0.4), (0.52, 0.42), sides=8)
    F("spine.2", "hide", (0, 0.78, -0.04), (0, 0.8, 0.7), (0.52, 0.42), (0.5, 0.44), sides=8)
    F("spine.2", "hide_dk", (0, 0.4, -0.1), (0, 0.4, 0.6), (0.4, 0.3), (0.38, 0.3), sides=8)
    F("spine.2", "hide", (0, 0.82, 0.55), (0, 0.8, 0.95), (0.44, 0.42), (0.36, 0.34), sides=8)
    F("spine.1", "belly", (0, 0.36, -0.7), (0, 0.36, 0.0), (0.4, 0.3), (0.44, 0.3), sides=8)


def plates():
    for bone, z in (("spine.2", 0.42), ("spine.1", -0.62)):
        for s in (1, -1):
            F(bone, "plate", (s * 0.6, 0.5, z), (s * 0.68, 1.12, z - 0.04), (0.06, 0.34), (0.05, 0.26), sides=4)
            F(bone, "plate_dk", (s * 0.68, 1.1, z - 0.04), (s * 0.7, 1.2, z - 0.05), (0.05, 0.24), (0.04, 0.2), sides=4)
    Bx("spine.2", "leather", (0, 1.1, 0.03), (0.9, 0.22, 0.7))
    Bx("spine.2", "leather", (0, 1.15, -0.25), (0.6, 0.2, 0.3))


def head():
    F("head", "hide", (0, 0.88, 0.72), (0, 0.72, 1.32), (0.42, 0.4), (0.32, 0.28), sides=8)
    F("head", "hide_dk", (0, 0.58, 1.0), (0, 0.56, 1.34), (0.26, 0.12), (0.24, 0.1), sides=6)
    F("head", "hide", (0, 0.88, 1.2), (0, 0.9, 1.5), (0.22, 0.2), (0.16, 0.13), sides=6)
    C("head", "horn", [(0, 0.92, 1.38), (0, 1.15, 1.7), (0, 1.42, 1.85), (0, 1.68, 1.78)],
            [(0.17, 0.17), (0.12, 0.12), (0.08, 0.08), (0.012, 0.012)], sides=6)
    F("head", "horn", (0, 1.0, 1.05), (0, 1.3, 1.2), (0.08, 0.08), (0.02, 0.02), sides=4)
    for s in (-1, 1):
        F("head", "eye", (s * 0.22, 0.95, 1.2), (s * 0.27, 0.97, 1.28), (0.05, 0.04), (0.035, 0.03), sides=4)
        F("head", "horn", (s * 0.18, 0.6, 1.36), (s * 0.26, 0.74, 1.48), (0.05, 0.05), (0.012, 0.012), sides=4)
        F("head", "hide_dk", (s * 0.3, 1.16, 0.84), (s * 0.4, 1.38, 0.82), (0.07, 0.05), (0.03, 0.03), sides=4)


def tail():
    C(("tail.1", "tail.2"), "hide", [(0, 0.82, -0.9), (0, 0.66, -1.35), (0, 0.5, -1.95)],
            [(0.2, 0.18), (0.14, 0.12), (0.02, 0.02)], sides=6)


def legs():
    for s, front, hind in ((1, "leg1", "leg3"), (-1, "leg2", "leg4")):
        for tag, z in ((front, FORE_Z), (hind, HIND_Z)):
            x = s * LEG_X
            F(f"{tag}.upper", "hide", (x, 0.95, z), (x, 0.5, z), (0.28, 0.3), (0.19, 0.2), sides=8)
            F(f"{tag}.lower", "hide_dk", (x, 0.55, z), (x, 0.15, z), (0.2, 0.21), (0.19, 0.2), sides=8)
            F(f"{tag}.lower", "hide", (x, 0.18, z), (x, 0.06, z + 0.02), (0.21, 0.22), (0.26, 0.28), sides=8)
            F(f"{tag}.lower", "horn", (x, 0.1, z + 0.1), (x, 0.0, z + 0.2), (0.2, 0.05), (0.24, 0.05), sides=6)





def rider_body():
    RF("rider.spine", "pants", (0, 1.25, 0.02), (0, 1.62, 0.04), (0.4, 0.32), (0.36, 0.28), sides=8)
    RF("rider.spine", "skin", (0, 1.6, 0.04), (0, 2.46, 0.14), (0.34, 0.26), (0.56, 0.32), sides=8)
    RF("rider.spine", "leather", (0, 1.6, 0.04), (0, 1.7, 0.04), (0.36, 0.28), (0.36, 0.28), sides=8)
    RF("rider.spine", "strap", (0.22, 2.46, 0.44), (-0.2, 1.72, 0.32), (0.06, 0.03), (0.06, 0.03), sides=4)
    RF("rider.spine", "strap", (-0.22, 2.46, 0.44), (0.2, 1.72, 0.32), (0.06, 0.03), (0.06, 0.03), sides=4)
    RF("rider.head", "skin", (0, 2.42, 0.12), (0, 2.72, 0.14), (0.27, 0.26), (0.32, 0.3), sides=8)
    RF("rider.head", "skin_dk", (0, 2.5, 0.32), (0, 2.64, 0.46), (0.2, 0.08), (0.24, 0.1), sides=6)
    RF("rider.head", "plate", (0, 2.72, 0.14), (0, 2.8, 0.14), (0.5, 0.48), (0.46, 0.44), sides=10)
    RF("rider.head", "plate", (0, 2.78, 0.14), (0, HEAD_TOP, 0.14), (0.36, 0.34), (0.2, 0.19), sides=10)
    for s in (-1, 1):
        RF("rider.head", "eye", (s * 0.11, 2.62, 0.4), (s * 0.13, 2.63, 0.44), (0.045, 0.03), (0.035, 0.025), sides=4)
        RF("rider.spine", "skin", (s * 0.34, 2.46, 0.1), (s * 0.55, 2.3, 0.1), (0.2, 0.22), (0.22, 0.22), sides=6)


def rider_legs():
    for s in (-1, 1):
        for a, b, ra, rb, tone in (((0.2, 1.4, 0.0), (0.55, 1.12, 0.2), 0.24, 0.19, "pants"), ((0.55, 1.14, 0.2), (0.62, 0.8, 0.14), 0.2, 0.15, "pants"),
                                   ((0.62, 0.82, 0.12), (0.64, 0.62, 0.32), 0.17, 0.2, "boot")):
            H.frustum("spine.2", tone, leg_m((s * a[0], a[1], a[2])), leg_m((s * b[0], b[1], b[2])), (ra, ra), (rb, rb), sides=6)


# arms and spear in absolute coordinates: the spear is oversized, held upright on the forearm, clear above the mount
SHOULDER_L, ELBOW_L, HAND_L = (0.5, 3.1, 0.1), (0.85, 2.85, 0.35), (0.6, 2.55, 0.85)
SHOULDER_R, ELBOW_R, HAND_R = (-0.5, 3.1, 0.1), (-0.95, 2.95, 0.25), (-1.0, 2.6, 0.35)


def left_hand():
    H.frustum("rider.arm.L", "skin", SHOULDER_L, ELBOW_L, (0.28, 0.27), (0.24, 0.24), sides=6)
    H.frustum("rider.forearm.L", "skin", ELBOW_L, HAND_L, (0.22, 0.22), (0.2, 0.2), sides=6)
    H.frustum("rider.forearm.L", "skin_dk", (0.62, 2.62, 0.8), (0.58, 2.46, 0.92), (0.24, 0.24), (0.2, 0.2), sides=6)


def spear():
    H.frustum("rider.arm.R", "skin", SHOULDER_R, ELBOW_R, (0.28, 0.27), (0.24, 0.24), sides=6)
    H.frustum("rider.forearm.R", "skin", ELBOW_R, HAND_R, (0.22, 0.22), (0.2, 0.2), sides=6)
    H.frustum("rider.forearm.R", "skin_dk", (-1.0, 2.7, 0.33), (-1.0, 2.5, 0.35), (0.25, 0.25), (0.2, 0.2), sides=6)
    H.frustum("rider.forearm.R", "wood", (-1.0, 2.1, 0.35), (-1.0, 3.6, 0.35), (0.12, 0.12), (0.11, 0.11), sides=6)
    H.frustum("rider.forearm.R", "steel", (-1.0, 3.6, 0.35), (-1.0, 4.1, 0.35), (0.3, 0.08), (0.012, 0.012), sides=4)
    H.frustum("rider.forearm.R", "plate_dk", (-1.0, 3.55, 0.35), (-1.0, 3.65, 0.35), (0.13, 0.13), (0.11, 0.11), sides=6)


def make():
    mount()
    plates()
    head()
    tail()
    legs()
    rider_body()
    rider_legs()
    left_hand()
    spear()


def joints():
    out = {"head": (sc((0, 0.85, 0.7)), sc((0, 0.8, 1.3))),
           "spine.1": (sc((0, 1.0, -0.55)), sc((0, 1.1, 0))), "spine.2": (sc((0, 1.1, 0)), sc((0, 1.1, 0.55))),
           "tail.1": (sc((0, 0.82, -0.9)), sc((0, 0.66, -1.35))), "tail.2": (sc((0, 0.66, -1.35)), sc((0, 0.5, -1.95))),
           "rider.spine": (m((0, 1.3, 0.02)), m((0, 2.42, 0.12))), "rider.head": (m((0, 2.42, 0.12)), m((0, HEAD_TOP, 0.14))),
           "rider.arm.L": (SHOULDER_L, ELBOW_L), "rider.forearm.L": (ELBOW_L, HAND_L),
           "rider.arm.R": (SHOULDER_R, ELBOW_R), "rider.forearm.R": (ELBOW_R, HAND_R)}
    for s, f, h in ((1, "leg1", "leg3"), (-1, "leg2", "leg4")):
        for tag, z in ((f, FORE_Z), (h, HIND_Z)):
            out[f"{tag}.upper"] = (sc((s * LEG_X, 0.95, z)), sc((s * LEG_X, 0.52, z)))
            out[f"{tag}.lower"] = (sc((s * LEG_X, 0.52, z)), sc((s * LEG_X, 0.06, z)))
    return out


H.build("o00B", "mounted", PALETTE, make, joints())
