"""Naga Siren (n00S): medido em artifacts/model-sheets/refs/n00S/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n00S.py -- <out.glb>
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "skin": 0x2A82C8, "skin_dk": 0x2370B0, "claw": 0xBFD8EA, "tail": 0x4A3A88, "tail_dk": 0x3B2E72,
    "belly": 0xEBD9A5, "belly_dk": 0xD9C58E, "hair": 0xE8604A, "hair_dk": 0xCB4A38, "snake": 0x4A3A88,
    "horn": 0x7A5FB0, "wing_y": 0xF2B040, "collar": 0x9A6A30, "eye": 0xFFB030,
}

RING_R, RING_Z = 0.62, -0.62              # a cauda enrola no chão num anel atrás do tronco
TAIL_RAD = [0.27, 0.26, 0.25, 0.22, 0.19, 0.14, 0.06]
SH_Y, EL_Y, WR_Y = 1.74, 1.33, 1.0


def cz(y):
    """z do eixo do tronco na altura y (perfil em S, a barriga avança na base)."""
    return -min(y, 1.0) * 0.15 if y < 1.0 else -0.15 + (y - 1.0) * 0.07


def tail_points():
    pts = []
    for i in range(7):
        a = math.radians(45 * i)
        pts.append((RING_R * math.sin(a), TAIL_RAD[i] * 0.9 + (0.1 if i == 6 else 0), RING_Z + RING_R * math.cos(a)))
    return pts


def tail():
    pts = tail_points()
    bones = [f"tail.{i}" for i in range(1, 7)]
    H.chain(bones, "tail", pts, [(r, r) for r in TAIL_RAD], sides=8)
    for i in range(1, 6):       # nadadeira dorsal laranja, em serrilha
        a, b = pts[i], pts[i + 1]
        m = [(a[k] + b[k]) / 2 for k in range(3)]
        H.frustum(bones[i], "hair", (m[0], m[1] + TAIL_RAD[i] * 0.8, m[2]), (m[0], m[1] + TAIL_RAD[i] + 0.2, m[2]), (0.02, 0.09), (0.005, 0.02), sides=4)


def column():
    H.frustum("root", "tail", (0, 0.25, 0.0), (0, 0.8, cz(0.8)), (0.34, 0.31), (0.31, 0.28), sides=8)
    H.frustum("spine", "tail", (0, 0.7, cz(0.7)), (0, 1.3, cz(1.3)), (0.31, 0.28), (0.2, 0.17), sides=8)
    for y, tone in ((0.4, "belly"), (0.6, "belly_dk"), (0.8, "belly"), (1.0, "belly_dk"), (1.18, "belly")):    # placas do ventre
        bone = "root" if y < 0.75 else "spine"
        w = 0.25 - 0.1 * max(y - 0.7, 0)
        H.frustum(bone, tone, (0, y - 0.11, cz(y) + 0.2 - 0.12 * max(y - 0.8, 0)), (0, y + 0.11, cz(y + 0.1) + 0.2 - 0.12 * max(y - 0.8, 0)), (w, 0.07), (w, 0.07), sides=4)
    for y in (0.5, 0.8, 1.1):       # crista dorsal
        H.frustum("spine" if y > 0.75 else "root", "hair", (0, y, cz(y) - 0.22), (0, y - 0.1, cz(y) - 0.46), (0.02, 0.09), (0.005, 0.02), sides=4)


def torso():
    H.frustum("spine", "skin", (0, 1.22, cz(1.22)), (0, 1.62, cz(1.62)), (0.19, 0.15), (0.26, 0.16), sides=8)
    H.frustum("spine", "skin", (0, 1.58, cz(1.58)), (0, 1.76, cz(1.76)), (0.27, 0.16), (0.14, 0.12), sides=8)       # ombros
    H.frustum("spine", "skin_dk", (0, 1.4, cz(1.4) + 0.1), (0, 1.58, cz(1.58) + 0.1), (0.15, 0.08), (0.2, 0.07), sides=6)   # busto


def head():
    zc = cz(1.8) + 0.04
    H.frustum("head", "skin", (0, 1.7, zc), (0, 1.88, zc), (0.1, 0.1), (0.09, 0.09), sides=6)                    # pescoço
    H.frustum("head", "collar", (0, 1.78, zc), (0, 1.9, zc), (0.17, 0.15), (0.14, 0.13), sides=8)                # gargantilha
    H.frustum("head", "skin", (0, 1.84, zc + 0.03), (0, 2.0, zc + 0.04), (0.1, 0.11), (0.14, 0.14), sides=6)     # queixo
    H.frustum("head", "skin", (0, 1.98, zc + 0.03), (0, 2.26, zc), (0.14, 0.14), (0.15, 0.14), sides=8)          # rosto
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.075, 2.1, zc + 0.17), (0.06, 0.035, 0.03))
        H.chain("head", "horn", [(s * 0.1, 2.24, zc), (s * 0.19, 2.36, zc - 0.02), (s * 0.17, 2.52, zc - 0.05)], [(0.05, 0.05), (0.04, 0.04), (0.01, 0.01)], sides=6)
    H.frustum("head", "hair", (0, 2.02, zc - 0.1), (0, 2.5, zc - 0.1), (0.2, 0.17), (0.22, 0.18), sides=8)       # volume de cabelo
    H.frustum("head", "hair_dk", (0, 2.2, zc - 0.02), (0, 2.46, zc - 0.04), (0.2, 0.1), (0.16, 0.1), sides=6)


def snake(pts):
    """Cobra do cabelo: corpo laranja em 3 segmentos afinando e cabeça roxa na ponta."""
    r = [(0.05, 0.05), (0.045, 0.045), (0.04, 0.04), (0.06, 0.05)]
    H.chain("head", "hair", pts[:4], r[:4], sides=6)
    H.frustum("head", "snake", pts[3], pts[4], (0.065, 0.055), (0.03, 0.025), sides=6)
    H.box("head", "eye", (pts[3][0] * 0.4 + pts[4][0] * 0.6, pts[3][1] + 0.04, pts[3][2] * 0.4 + pts[4][2] * 0.6), (0.025, 0.02, 0.025))


def hair_snakes():
    zc = cz(2.0)
    snake([(0, 2.4, zc - 0.08), (0, 2.55, zc - 0.05), (-0.03, 2.66, zc), (0.0, 2.72, zc + 0.06), (0.0, 2.7, zc + 0.2)])
    for s in (-1, 1):
        snake([(s * 0.1, 2.38, zc - 0.08), (s * 0.24, 2.46, zc - 0.02), (s * 0.34, 2.58, zc + 0.1), (s * 0.3, 2.66, zc + 0.2), (s * 0.22, 2.64, zc + 0.36)])
        snake([(s * 0.16, 2.14, zc - 0.1), (s * 0.34, 2.02, zc - 0.12), (s * 0.5, 1.98, zc - 0.1), (s * 0.62, 2.0, zc - 0.08), (s * 0.76, 2.0, zc - 0.05)])
        snake([(s * 0.12, 2.3, zc - 0.14), (s * 0.2, 2.34, zc - 0.34), (s * 0.3, 2.22, zc - 0.5), (s * 0.42, 2.1, zc - 0.5), (s * 0.5, 2.06, zc - 0.42)])
        H.panel("head", "hair_dk", [(s * 0.14, 2.06, zc - 0.05), (s * 0.15, 2.3, zc - 0.05), (s * 0.66, 2.44, zc - 0.05), (s * 0.5, 2.26, zc - 0.05), (s * 0.58, 2.1, zc - 0.05)])
        H.panel("head", "wing_y", [(s * 0.15, 2.07, zc - 0.03), (s * 0.5, 2.26, zc - 0.03), (s * 0.58, 2.1, zc - 0.03)])


def arm(side, s):
    x_sh, x_el, x_wr = s * 0.27, s * 0.42, s * 0.52
    zs, ze, zw = cz(SH_Y), cz(EL_Y) + 0.04, cz(WR_Y) + 0.18
    H.frustum(f"arm.{side}", "skin", (x_sh, SH_Y + 0.04, zs), (x_sh + s * 0.04, SH_Y - 0.1, zs), (0.12, 0.12), (0.12, 0.12), sides=6)
    H.chain(f"arm.{side}", "skin", [(x_sh, SH_Y - 0.04, zs), ((x_sh + x_el) / 2, (SH_Y + EL_Y) / 2 + 0.02, (zs + ze) / 2), (x_el, EL_Y + 0.04, ze)],
            [(0.12, 0.12), (0.115, 0.11), (0.12, 0.12)], sides=6)
    H.frustum(f"forearm.{side}", "skin", (x_el, EL_Y + 0.05, ze), (x_wr, WR_Y + 0.06, zw), (0.13, 0.13), (0.105, 0.1), sides=6)       # antebraço grosso
    H.frustum(f"forearm.{side}", "skin_dk", (x_el, EL_Y - 0.02, ze), (x_wr, WR_Y + 0.1, zw), (0.1, 0.1), (0.08, 0.07), sides=6)
    palm = (x_wr + s * 0.03, WR_Y - 0.22, zw + 0.08)
    H.frustum(f"forearm.{side}", "skin", (x_wr, WR_Y + 0.05, zw), palm, (0.1, 0.07), (0.15, 0.08), sides=6)                         # mão grande
    for k, dx in enumerate((-0.09, 0.0, 0.09)):
        tip = (palm[0] + s * (0.04 + 0.04 * k) + dx * 0.4, palm[1] - 0.2, palm[2] + 0.08 + 0.02 * k)
        H.frustum(f"forearm.{side}", "claw", (palm[0] + dx, palm[1] + 0.03, palm[2]), tip, (0.04, 0.03), (0.008, 0.008), sides=4)


def make():
    tail()
    column()
    torso()
    head()
    hair_snakes()
    arm("L", 1)
    arm("R", -1)


def joints():
    pts = tail_points()
    out = {"spine": ((0, 0.55, cz(0.55)), (0, 1.76, cz(1.76))), "head": ((0, 1.76, cz(1.76)), (0, 2.4, cz(2.4)))}
    start = (0, TAIL_RAD[0] * 0.9, 0.0)
    out["tail.1"] = (start, pts[1])
    for i in range(2, 7):
        out[f"tail.{i}"] = (pts[i - 1], pts[i])
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * 0.27, SH_Y, cz(SH_Y)), (s * 0.42, EL_Y, cz(EL_Y) + 0.04))
        out[f"forearm.{side}"] = ((s * 0.42, EL_Y, cz(EL_Y) + 0.04), (s * 0.52, WR_Y, cz(WR_Y) + 0.18))
    return out


H.build("n00S", "naga", PALETTE, make, joints())
