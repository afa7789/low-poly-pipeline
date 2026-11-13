"""Melee Kodo Rider (o008): orc de colete vermelho com machado erguido na mao direita, sobre rinoceronte de manta verde e placa de ombro.

    blender -b --factory-startup -P tools/blender/units/o008.py -- <out.glb>

Cavaleiro aumentado alem da prancha (assento->cabeca ~46 % da altura, machado incluso); machado grande erguido sobre o ombro direito, longe da montaria.
O braco direito e modelado erguido como na prancha; as juntas dos ossos seguem o corpo modelado.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "hide": 0xA8905E, "hide_dk": 0x8A7448, "blanket": 0x72804A, "belly": 0x4E3A2A, "plate": 0x8E909A, "plate_dk": 0x6E707A,
    "leather": 0x6A3A30, "horn": 0xDCCCA2, "eye": 0xE82020, "skin": 0x5E9A44, "skin_dk": 0x4A7C34,
    "mask": 0xA0243C, "band": 0xA0243C, "vest": 0xB82038, "pants": 0x5A3A28, "shield": 0x7C1E32, "rim": 0xA02C44,
    "pot": 0x80483A, "wood": 0x4F4F56, "steel": 0xA6A8B0, "boot": 0x2E2118,
}

LEG_X, FORE_Z, HIND_Z = 0.42, 0.58, -0.58
K = 1.45  # mount scale: the sheet's kodo is the big mass (back ~62 % of the unit's height with the axe)
R = 0.86  # rider height scale: seat -> head top ~36 % of the unit's height
SEAT = 1.3 * K


def F(bone, tone, a, b, ra, rb, sides=8):
    H.frustum(bone, tone, tuple(v * K for v in a), tuple(v * K for v in b), (ra[0] * K, ra[1] * K), (rb[0] * K, rb[1] * K), sides)


def Bx(bone, tone, c, size):
    H.box(bone, tone, tuple(v * K for v in c), tuple(v * K for v in size))


def C(bones, tone, pts, radii, sides=6):
    H.chain(bones, tone, [tuple(v * K for v in p) for p in pts], [(r[0] * K, r[1] * K) for r in radii], sides)


def m(p):
    return (p[0] * 0.9, SEAT + (p[1] - 1.3) * R, p[2] * 0.9)


def RF(bone, tone, a, b, ra, rb, sides=8):
    H.frustum(bone, tone, m(a), m(b), (ra[0] * 1.1, ra[1] * 1.1), (rb[0] * 1.1, rb[1] * 1.1), sides)


def leg_m(p):
    return (p[0] * K, SEAT + (p[1] - 1.3) * 1.2, p[2])


HEAD_TOP = 2.75


def mount():
    F("spine.1", "hide", (0, 0.92, -1.08), (0, 0.84, -0.02), (0.44, 0.5), (0.52, 0.46), sides=8)
    F("spine.2", "hide", (0, 0.78, -0.04), (0, 0.8, 0.7), (0.52, 0.42), (0.5, 0.44), sides=8)
    F("spine.2", "hide_dk", (0, 0.4, -0.1), (0, 0.4, 0.6), (0.4, 0.3), (0.38, 0.3), sides=8)
    F("spine.2", "hide", (0, 0.82, 0.55), (0, 0.8, 0.95), (0.44, 0.42), (0.36, 0.34), sides=8)
    F("spine.1", "belly", (0, 0.36, -0.7), (0, 0.36, 0.0), (0.4, 0.3), (0.44, 0.3), sides=8)


def plates():
    Bx("spine.2", "blanket", (0, 1.2, -0.05), (0.96, 0.1, 1.5))
    for s in (-1, 1):
        F("spine.2", "blanket", (s * 0.46, 1.2, -0.05), (s * 0.56, 0.78, -0.05), (0.04, 0.75), (0.04, 0.7), sides=4)
    F("spine.2", "plate", (0, 1.12, 0.6), (0, 1.5, 0.6), (0.62, 0.22), (0.4, 0.2), sides=4)
    F("spine.2", "plate_dk", (0, 1.46, 0.6), (0, 1.54, 0.6), (0.4, 0.2), (0.34, 0.18), sides=4)
    Bx("spine.2", "leather", (0, 1.27, -0.02), (0.5, 0.1, 0.4))
    F("spine.2", "leather", (0, 0.4, 0.05), (0, 1.1, 0.05), (0.04, 0.5), (0.04, 0.5), sides=4)


def head():
    F("head", "hide", (0, 0.88, 0.72), (0, 0.72, 1.32), (0.4, 0.38), (0.3, 0.26), sides=8)
    F("head", "hide_dk", (0, 0.58, 1.0), (0, 0.56, 1.34), (0.24, 0.12), (0.22, 0.1), sides=6)
    F("head", "hide", (0, 0.88, 1.2), (0, 0.9, 1.48), (0.2, 0.2), (0.15, 0.13), sides=6)
    F("head", "horn", (0, 0.92, 1.4), (0, 1.5, 1.82), (0.13, 0.15), (0.015, 0.015), sides=6)
    F("head", "horn", (0, 1.0, 1.1), (0, 1.12, 1.18), (0.07, 0.07), (0.03, 0.03), sides=4)
    for s in (-1, 1):
        F("head", "eye", (s * 0.22, 0.95, 1.2), (s * 0.27, 0.97, 1.28), (0.05, 0.04), (0.035, 0.03), sides=4)
        F("head", "horn", (s * 0.18, 0.6, 1.36), (s * 0.26, 0.74, 1.48), (0.04, 0.04), (0.012, 0.012), sides=4)
        C("head", "horn", [(s * 0.3, 0.95, 1.0), (s * 0.62, 1.0, 1.25), (s * 0.55, 1.05, 1.62)], [(0.07, 0.07), (0.05, 0.05), (0.012, 0.012)], sides=6)
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


def bags():
    for s, r in ((1, 0.3), (-1, 0.24)):
        F("spine.2", "pot", (s * 0.66, 0.5, -0.25), (s * 0.7, 0.95, -0.25), (r * 0.8, r), (r, r * 1.1), sides=8)
        F("spine.2", "belly", (s * 0.68, 0.93, -0.25), (s * 0.69, 1.03, -0.25), (r * 0.6, r * 0.6), (r * 0.3, r * 0.3), sides=6)


def rider_body():
    RF("rider.spine", "pants", (0, 1.25, 0.02), (0, 1.6, 0.04), (0.38, 0.3), (0.34, 0.26), sides=8)
    RF("rider.spine", "skin", (0, 1.58, 0.04), (0, 2.34, 0.14), (0.3, 0.24), (0.5, 0.3), sides=8)
    RF("rider.spine", "vest", (0, 1.7, 0.04), (0, 2.3, 0.14), (0.35, 0.3), (0.52, 0.33), sides=8)
    RF("rider.spine", "leather", (0, 1.58, 0.04), (0, 1.68, 0.04), (0.33, 0.26), (0.33, 0.26), sides=8)
    RF("rider.spine", "leather", (0.2, 2.34, 0.4), (-0.2, 1.72, 0.3), (0.05, 0.03), (0.05, 0.03), sides=4)
    RF("rider.spine", "leather", (-0.2, 2.34, 0.4), (0.2, 1.72, 0.3), (0.05, 0.03), (0.05, 0.03), sides=4)
    RF("rider.head", "skin", (0, 2.3, 0.12), (0, 2.62, 0.14), (0.24, 0.24), (0.3, 0.28), sides=8)
    RF("rider.head", "mask", (0, 2.34, 0.3), (0, 2.5, 0.44), (0.16, 0.08), (0.2, 0.1), sides=6)
    RF("rider.head", "band", (0, 2.56, 0.14), (0, 2.68, 0.14), (0.31, 0.29), (0.31, 0.29), sides=8)
    RF("rider.head", "skin_dk", (0, 2.66, 0.14), (0, HEAD_TOP, 0.14), (0.28, 0.26), (0.17, 0.16), sides=8)
    for s in (-1, 1):
        RF("rider.head", "skin", (s * 0.28, 2.52, 0.12), (s * 0.5, 2.68, 0.1), (0.06, 0.04), (0.012, 0.012), sides=4)
        RF("rider.head", "eye", (s * 0.1, 2.52, 0.37), (s * 0.12, 2.53, 0.4), (0.04, 0.025), (0.03, 0.02), sides=4)
        RF("rider.spine", "skin", (s * 0.3, 2.34, 0.1), (s * 0.5, 2.2, 0.1), (0.18, 0.2), (0.2, 0.2), sides=6)


def rider_legs():
    for s in (-1, 1):
        for a, b, ra, rb, tone in (((0.2, 1.4, 0.0), (0.55, 1.12, 0.2), 0.24, 0.19, "pants"), ((0.55, 1.14, 0.2), (0.62, 0.8, 0.14), 0.2, 0.15, "pants"),
                                   ((0.62, 0.82, 0.12), (0.64, 0.62, 0.32), 0.17, 0.2, "boot")):
            H.frustum("spine.2", tone, leg_m((s * a[0], a[1], a[2])), leg_m((s * b[0], b[1], b[2])), (ra, ra), (rb, rb), sides=6)


# the axe: absolute coordinates, oversized, standing clear above the mount; blade inside the sheet's outline (|x| <= 1.3)
SHOULDER_R, ELBOW_R, HAND_R = (-0.45, 2.49, 0.09), (-0.8, 2.62, 0.1), (-0.92, 3.02, 0.1)


def axe_arm():
    H.frustum("rider.arm.R", "skin", SHOULDER_R, ELBOW_R, (0.27, 0.26), (0.23, 0.23), sides=6)
    H.frustum("rider.forearm.R", "skin", ELBOW_R, HAND_R, (0.22, 0.22), (0.2, 0.2), sides=6)
    H.frustum("rider.forearm.R", "boot", (-0.9, 2.9, 0.1), (-0.92, 3.1, 0.1), (0.24, 0.24), (0.2, 0.2), sides=6)
    H.frustum("rider.forearm.R", "wood", (-0.9, 2.55, 0.1), (-0.92, 3.5, 0.1), (0.11, 0.11), (0.1, 0.1), sides=6)
    H.frustum("rider.forearm.R", "steel", (-1.06, 3.08, 0.1), (-1.08, 3.52, 0.1), (0.2, 0.05), (0.3, 0.06), sides=4)
    H.frustum("rider.forearm.R", "plate_dk", (-0.7, 3.34, 0.1), (-0.76, 3.52, 0.1), (0.14, 0.06), (0.1, 0.06), sides=4)


def rein_arm():
    RF("rider.arm.L", "skin", (0.5, 2.2, 0.1), (0.62, 1.82, 0.16), (0.24, 0.23), (0.2, 0.2), sides=6)
    RF("rider.forearm.L", "skin", (0.62, 1.82, 0.16), (0.5, 1.7, 0.5), (0.19, 0.19), (0.17, 0.17), sides=6)
    RF("rider.forearm.L", "boot", (0.5, 1.7, 0.5), (0.45, 1.66, 0.7), (0.2, 0.2), (0.22, 0.22), sides=6)


def make():
    mount()
    plates()
    head()
    tail()
    legs()
    bags()
    rider_body()
    rider_legs()
    axe_arm()
    rein_arm()


def joints():
    out = {"head": ((0, 0.85 * K, 0.7 * K), (0, 0.8 * K, 1.3 * K)),
           "spine.1": ((0, 1.0 * K, -0.55 * K), (0, 1.1 * K, 0)), "spine.2": ((0, 1.1 * K, 0), (0, 1.1 * K, 0.55 * K)),
           "tail.1": ((0, 0.82 * K, -0.9 * K), (0, 0.66 * K, -1.35 * K)), "tail.2": ((0, 0.66 * K, -1.35 * K), (0, 0.5 * K, -1.95 * K)),
           "rider.spine": (m((0, 1.3, 0.02)), m((0, 2.3, 0.12))), "rider.head": (m((0, 2.3, 0.12)), m((0, HEAD_TOP, 0.14))),
           "rider.arm.L": (m((0.5, 2.2, 0.1)), m((0.62, 1.82, 0.16))), "rider.forearm.L": (m((0.62, 1.82, 0.16)), m((0.5, 1.7, 0.5))),
           "rider.arm.R": (SHOULDER_R, ELBOW_R), "rider.forearm.R": (ELBOW_R, HAND_R)}
    for s, f, h in ((1, "leg1", "leg3"), (-1, "leg2", "leg4")):
        for tag, z in ((f, FORE_Z), (h, HIND_Z)):
            out[f"{tag}.upper"] = ((s * LEG_X * K, 0.95 * K, z * K), (s * LEG_X * K, 0.52 * K, z * K))
            out[f"{tag}.lower"] = ((s * LEG_X * K, 0.52 * K, z * K), (s * LEG_X * K, 0.06 * K, z * K))
    return out


H.build("o008", "mounted", PALETTE, make, joints())
