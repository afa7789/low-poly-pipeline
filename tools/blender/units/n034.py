"""Harpies' Matriarch (n034, familia harpy): medido em artifacts/model-sheets/refs/n034/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n034.py -- <out.glb>

Corpo bordo, mascara cinza de ave com bico, cocar de penas e juba laranja, bracos longos com garras, asas
largas vermelhas e douradas penduradas dos ombros. Os ossos ficam na direcao de repouso da familia; as asas
e os bracos sao angulados nas PECAS (nao com `joints`). Bracos e asas grandes para o ataque aparecer.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "maroon": 0x4A1A22, "maroon_dk": 0x38131A, "red": 0xA3252F, "red_dk": 0x82202A, "gold": 0xD9A93A,
    "gold_dk": 0xB98A2A, "mane": 0xE8501F, "face": 0xA8A39F, "beak": 0x8F8A84, "eye": 0xF2F0E0,
    "gem": 0x9A3CC0, "claw": 0x2A1A1A, "talon": 0xC9992F, "horn": 0xA89E94,
}

LX = 0.22
HIPY, KNEE, HOCK, ANK = 1.3, (1.05, 0.2), (0.76, -0.28), (0.34, -0.1)
ROOT, WRIST, TIP = (0.5, 2.25, -0.14), (1.0, 1.5, -0.3), (1.3, 0.25, -0.75)
W1, W2 = (-0.28, -0.3, -0.55), (-0.28, -0.1, -0.6)
SH, EL, HAND = (0.55, 2.15, 0.02), (0.9, 1.75, 0.08), (1.15, 1.35, 0.14)


def mx(p, s):
    return (p[0] * s, p[1], p[2])


def along(p, w, k):
    return tuple(p[i] + w[i] * k for i in range(3))


def mid(a, b, t=0.5):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def headdress():
    tips = [(-0.6, 2.95), (-0.45, 3.1), (-0.25, 3.2), (0.0, 3.22), (0.25, 3.2), (0.45, 3.1), (0.6, 2.95)]
    for i, (x, y) in enumerate(tips):
        tone = ("red", "gold")[i % 2]
        H.frustum("head", tone, (x * 0.35, 2.62, 0.02), (x, y, -0.02), (0.11, 0.05), (0.03, 0.02), sides=4)
        H.frustum("head", "gold" if tone == "red" else "red", (x * 0.35, 2.62, 0.02), (x * 0.9, y - 0.2, -0.0), (0.045, 0.03), (0.03, 0.02), sides=4)
    H.frustum("head", "gold", (0, 2.6, 0.04), (0, 2.72, 0.04), (0.23, 0.2), (0.22, 0.19), sides=8)
    H.box("head", "gem", (0, 2.66, 0.25), (0.06, 0.07, 0.04))


def mane():
    H.frustum("head", "mane", (0, 2.3, -0.02), (0, 2.65, -0.12), (0.26, 0.22), (0.3, 0.22), sides=8)
    H.chain("head", "mane", [(0, 2.55, -0.1), (0, 2.7, -0.4), (0, 2.62, -0.85)], [(0.2, 0.15), (0.14, 0.1), (0.02, 0.02)], sides=6)
    H.chain("head", "mane", [(0, 2.35, -0.1), (0, 2.25, -0.35), (0, 2.0, -0.5)], [(0.2, 0.12), (0.14, 0.1), (0.03, 0.03)], sides=6)


def head():
    H.frustum("head", "maroon", (0, 2.1, -0.02), (0, 2.38, 0.14), (0.24, 0.2), (0.17, 0.17), sides=6)
    H.frustum("head", "face", (0, 2.3, 0.14), (0, 2.66, 0.2), (0.13, 0.11), (0.2, 0.15), sides=6)
    H.frustum("head", "beak", (0, 2.52, 0.26), (0, 2.3, 0.6), (0.09, 0.08), (0.04, 0.04), sides=4)
    H.frustum("head", "beak", (0, 2.34, 0.55), (0, 2.14, 0.62), (0.04, 0.035), (0.008, 0.008), sides=4)
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.1, 2.54, 0.3), (0.08, 0.04, 0.05))


def torso():
    H.frustum("pelvis", "maroon", (0, 0.95, 0.0), (0, 1.32, 0.0), (0.32, 0.22), (0.24, 0.19), sides=8)
    H.frustum("pelvis", "maroon", (0, 1.3, 0.0), (0, 1.52, 0.0), (0.24, 0.19), (0.22, 0.18), sides=8)
    H.frustum("spine", "maroon", (0, 1.5, 0.0), (0, 1.85, 0.02), (0.22, 0.18), (0.32, 0.22), sides=8)
    H.frustum("spine", "maroon", (0, 1.82, 0.02), (0, 2.16, 0.04), (0.32, 0.22), (0.4, 0.24), sides=8)
    H.frustum("spine", "maroon_dk", (0, 2.0, 0.02), (0, 2.34, 0.1), (0.52, 0.3), (0.3, 0.22), sides=8)
    for i, x in enumerate((-0.22, 0.0, 0.22)):
        tone = ("red", "gold", "red")[i]
        H.frustum("pelvis", tone, (x, 1.05, -0.2), (x * 1.5, 0.15, -0.36), (0.12, 0.05), (0.05, 0.03), sides=4)
        H.frustum("pelvis", "gold", (x, 0.5, -0.3), (x * 1.5, 0.12, -0.36), (0.08, 0.04), (0.03, 0.02), sides=4)
    H.frustum("pelvis", "maroon_dk", (0, 1.0, 0.18), (0, 0.72, 0.18), (0.24, 0.06), (0.05, 0.04), sides=4)


def legs(s, side):
    x = s * LX
    H.frustum(f"thigh.{side}", "maroon", (x * 0.85, HIPY + 0.08, -0.02), (x, KNEE[0], KNEE[1]), (0.22, 0.2), (0.13, 0.13), sides=6)
    H.frustum(f"shin.{side}", "maroon", (x, KNEE[0] + 0.04, KNEE[1]), (x, HOCK[0], HOCK[1]), (0.12, 0.12), (0.09, 0.09), sides=6)
    H.frustum(f"shin.{side}", "talon", (x, HOCK[0] + 0.02, HOCK[1]), (x, ANK[0] + 0.03, ANK[1]), (0.08, 0.08), (0.06, 0.06), sides=6)
    H.frustum(f"foot.{side}", "talon", (x, ANK[0] + 0.02, ANK[1]), (x, 0.08, 0.1), (0.07, 0.07), (0.1, 0.06), sides=6)
    for dx, dz in ((-0.12, 0.26), (0.0, 0.36), (0.12, 0.26)):
        H.frustum(f"foot.{side}", "talon", (x + dx * 0.3, 0.1, 0.1), (x + dx, 0.05, 0.1 + dz), (0.04, 0.035), (0.025, 0.02), sides=4)
        H.frustum(f"foot.{side}", "claw", (x + dx, 0.05, 0.1 + dz), (x + dx * 1.1, 0.0, 0.16 + dz), (0.025, 0.02), (0.005, 0.005), sides=4)
    H.frustum(f"foot.{side}", "talon", (x, 0.12, 0.0), (x, 0.06, -0.22), (0.045, 0.045), (0.012, 0.012), sides=4)


def arms(s, side):
    sh, el, hd = mx(SH, s), mx(EL, s), mx(HAND, s)
    H.frustum(f"arm.{side}", "maroon", (sh[0] - 0.05 * s, sh[1] + 0.12, 0.0), el, (0.17, 0.17), (0.13, 0.13), sides=6)
    H.frustum(f"forearm.{side}", "maroon", (el[0], el[1] + 0.04, el[2]), hd, (0.14, 0.14), (0.12, 0.12), sides=6)
    H.frustum(f"forearm.{side}", "maroon_dk", hd, (hd[0] + 0.1 * s, hd[1] - 0.14, hd[2] + 0.1), (0.13, 0.12), (0.1, 0.09), sides=6)
    for dx, dz in ((-0.07, 0.0), (0.0, 0.08), (0.07, 0.0)):    # garras grandes curvas
        base = (hd[0] + 0.1 * s + dx, hd[1] - 0.12, hd[2] + 0.1 + dz)
        H.chain(f"forearm.{side}", "horn", [base, (base[0] + 0.1 * s, base[1] - 0.2, base[2] + 0.12), (base[0] + 0.05 * s, base[1] - 0.34, base[2] + 0.3)],
                [(0.045, 0.04), (0.03, 0.03), (0.006, 0.006)], sides=4)


def wing(s, n):
    up, low = f"wing{n}.upper", f"wing{n}.lower"
    r, w, t = mx(ROOT, s), mx(WRIST, s), mx(TIP, s)
    w1, w2 = mx(W1, s), mx(W2, s)
    m = mid(w, t, 0.45)
    H.frustum(up, "maroon_dk", r, w, (0.12, 0.1), (0.09, 0.08), sides=6)
    H.frustum(low, "maroon_dk", w, t, (0.09, 0.08), (0.03, 0.03), sides=6)
    H.panel(up, "red", [r, w, along(w, w1, 1.0), along(r, w1, 1.15)], 0.05)
    H.panel(up, "red_dk", [along(r, w1, 1.05), along(w, w1, 0.95), along(w, w1, 1.4), along(r, w1, 1.45)], 0.04)
    H.panel(low, "red", [w, m, along(m, w2, 1.2), along(w, w2, 1.25)], 0.055)
    H.panel(low, "gold", [m, t, along(t, w2, 0.9), along(m, w2, 1.2)], 0.055)
    H.panel(low, "gold_dk", [along(w, w1, 0.5), along(m, w2, 1.2), along(t, w2, 0.9), along(t, w2, 0.5)], 0.035)
    H.panel(low, "gold", [along(w, w2, 1.2), along(m, w2, 1.2), along(m, w2, 1.7), along(w, w2, 1.7)], 0.04)


def make():
    headdress()
    mane()
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        legs(s, side)
        arms(s, side)
    wing(1, 1)
    wing(-1, 2)


def joints():
    out = {"head": ((0, 2.16, 0), (0, 2.72, 0.02))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * 0.6, 2.1, 0), (s * 0.6, 1.5, 0))
        out[f"forearm.{side}"] = ((s * 0.6, 1.5, 0), (s * 0.6, 1.0, 0))
        out[f"thigh.{side}"] = ((s * LX * 0.85, HIPY, -0.02), (s * LX, KNEE[0], KNEE[1]))
        out[f"shin.{side}"] = ((s * LX, KNEE[0], KNEE[1]), (s * LX, ANK[0], ANK[1]))
        out[f"foot.{side}"] = ((s * LX, ANK[0], ANK[1]), (s * LX, 0.06, 0.3))
    return out


H.build("n034", "harpy", PALETTE, make, joints())
