"""Harpia (n02W, familia harpy): medido em artifacts/model-sheets/refs/n02W/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n02W.py -- <out.glb>

Corpo de pena marrom, cabeca de ave com crista, pernas de ave (joelho a frente, jarrete atras, garras), bracos
escuros nas bordas das asas. Asas largas penduradas dos ombros e varridas para tras: braco em frusta nos ossos
upper/lower, membrana em H.panel (coberteiras na upper, penas claras na lower).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "brown": 0x4A2D26, "brown_dk": 0x39221D, "wing": 0x7A4B33, "wing_dk": 0x634029, "tan": 0xDBA878,
    "tan_dk": 0xB98A5C, "yellow": 0xC9922C, "claw": 0x25211F, "hair": 0x1F1816, "face": 0xA39C94,
    "beak": 0x9B948A, "eye": 0xF2F0E0,
}

# metros do biped; 0,0034 m por pixel na frente e no perfil da prancha
PELVIS, WAIST, NECK, TOP = 1.3, 1.5, 2.12, 2.7
LX = 0.2
HIPY, KNEE, HOCK, ANK = 1.3, (1.05, 0.2), (0.76, -0.28), (0.34, -0.1)
SH, EL, HAND = (0.45, 2.1, 0.0), (0.68, 1.8, 0.02), (0.98, 1.46, 0.04)
ROOT, WRIST, TIP = (0.4, 2.2, -0.02), (0.96, 1.5, -0.08), (1.12, 1.0, -0.1)


def mx(p, s):
    return (p[0] * s, p[1], p[2])


def along(p, w, k):
    return tuple(p[i] + w[i] * k for i in range(3))


def mid(a, b, t=0.5):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def head():
    H.frustum("head", "brown", (0, 2.0, 0.0), (0, 2.38, 0.26), (0.26, 0.2), (0.17, 0.16), sides=6)      # pescoco curvado a frente
    H.frustum("head", "brown_dk", (0, 2.22, 0.1), (0, 2.58, 0.2), (0.2, 0.2), (0.22, 0.21), sides=6)     # cranio
    H.frustum("head", "face", (0, 2.2, 0.3), (0, 2.56, 0.32), (0.13, 0.11), (0.19, 0.15), sides=6)       # mascara
    H.frustum("head", "beak", (0, 2.4, 0.36), (0, 2.06, 0.76), (0.12, 0.1), (0.02, 0.02), sides=4)       # bico grosso
    H.frustum("head", "beak", (0, 2.2, 0.62), (0, 2.02, 0.72), (0.05, 0.045), (0.008, 0.008), sides=4)   # gancho
    for s in (-1, 1):
        H.box("head", "eye", (s * 0.09, 2.48, 0.42), (0.07, 0.04, 0.03))
    for tip in ((-0.24, 3.0, 0.14), (-0.13, 3.1, 0.08), (0.0, 3.14, 0.04), (0.13, 3.1, 0.08), (0.24, 3.0, 0.14), (0.0, 2.95, -0.18), (-0.12, 2.9, -0.14), (0.12, 2.9, -0.14)):
        H.frustum("head", "hair", (tip[0] * 0.4, 2.52, 0.14), tip, (0.1, 0.09), (0.008, 0.008), sides=4)
    H.frustum("head", "hair", (0, 2.46, 0.0), (0, 2.85, -0.25), (0.14, 0.14), (0.05, 0.05), sides=4)


def torso():
    H.frustum("pelvis", "brown", (0, 0.95, 0.0), (0, 1.32, 0.0), (0.32, 0.22), (0.24, 0.19), sides=8)
    H.frustum("pelvis", "brown", (0, 1.3, 0.0), (0, 1.52, 0.0), (0.24, 0.19), (0.22, 0.18), sides=8)
    H.frustum("spine", "brown", (0, 1.5, 0.0), (0, 1.86, 0.06), (0.22, 0.18), (0.32, 0.22), sides=8)       # peito curvado
    H.frustum("spine", "brown", (0, 1.84, 0.06), (0, 2.14, 0.1), (0.32, 0.22), (0.36, 0.22), sides=8)
    H.frustum("spine", "brown_dk", (0, 1.96, 0.1), (0, 2.28, 0.16), (0.46, 0.3), (0.28, 0.22), sides=8)     # gola de penas
    H.frustum("spine", "brown_dk", (0, 2.2, -0.04), (0, 2.0, -0.2), (0.3, 0.2), (0.4, 0.1), sides=6)       # corcunda
    H.frustum("pelvis", "brown_dk", (0, 1.28, -0.2), (0, 0.5, -0.34), (0.34, 0.07), (0.04, 0.04), sides=4)  # leque da cauda
    H.frustum("pelvis", "brown_dk", (0, 1.0, 0.18), (0, 0.72, 0.16), (0.24, 0.06), (0.03, 0.03), sides=4)   # saiote de penas


def legs(s, side):
    x = s * LX
    H.frustum(f"thigh.{side}", "brown", (x * 0.85, HIPY + 0.08, -0.02), (x, KNEE[0], KNEE[1]), (0.23, 0.21), (0.14, 0.14), sides=6)
    H.frustum(f"shin.{side}", "brown", (x, KNEE[0] + 0.04, KNEE[1]), (x, HOCK[0], HOCK[1]), (0.14, 0.14), (0.1, 0.1), sides=6)
    H.frustum(f"shin.{side}", "yellow", (x, HOCK[0] + 0.02, HOCK[1]), (x, ANK[0] + 0.03, ANK[1]), (0.09, 0.09), (0.07, 0.07), sides=6)
    H.frustum(f"foot.{side}", "yellow", (x, ANK[0] + 0.02, ANK[1]), (x, 0.08, 0.1), (0.08, 0.08), (0.12, 0.07), sides=6)
    for dx, dz in ((-0.14, 0.28), (0.0, 0.4), (0.14, 0.28)):      # dedos e garras
        H.frustum(f"foot.{side}", "yellow", (x + dx * 0.3, 0.1, 0.1), (x + dx, 0.05, 0.1 + dz), (0.055, 0.045), (0.035, 0.03), sides=4)
        H.frustum(f"foot.{side}", "claw", (x + dx, 0.05, 0.1 + dz), (x + dx * 1.1, 0.0, 0.18 + dz), (0.035, 0.03), (0.005, 0.005), sides=4)
    H.frustum(f"foot.{side}", "yellow", (x, 0.12, 0.0), (x, 0.06, -0.2), (0.04, 0.04), (0.012, 0.012), sides=4)   # esporao de tras


def arms(s, side):
    sh, el, hd = mx(SH, s), mx(EL, s), mx(HAND, s)
    H.frustum(f"arm.{side}", "brown", (sh[0] - 0.02 * s, sh[1] + 0.1, 0.0), el, (0.15, 0.15), (0.11, 0.11), sides=6)
    H.frustum(f"forearm.{side}", "brown", (el[0], el[1] + 0.03, el[2]), (hd[0], hd[1] + 0.02, hd[2]), (0.11, 0.11), (0.09, 0.09), sides=6)
    H.frustum(f"forearm.{side}", "brown_dk", (hd[0], hd[1] + 0.04, hd[2]), (hd[0] + 0.04 * s, hd[1] - 0.1, hd[2] + 0.06), (0.09, 0.08), (0.06, 0.05), sides=6)  # mao
    for dx in (-0.04, 0.0, 0.04):
        H.frustum(f"forearm.{side}", "claw", (hd[0] + dx, hd[1] - 0.08, hd[2] + 0.06), (hd[0] + dx, hd[1] - 0.2, hd[2] + 0.16), (0.02, 0.02), (0.004, 0.004), sides=4)


NF = 10          # penas por asa, da raiz do ombro (u=0) ate a ponta (u=1)
BACK = (-0.2, -0.75, -0.75)   # sentido em que as penas descem da borda de ataque (para dentro, baixo e tras; x espelha)


def lead(r, w, t, u):
    """Ponto da borda de ataque e o sentido do osso ali: ombro->pulso->ponta."""
    a, b, k = (r, w, u * 2) if u < 0.5 else (w, t, u * 2 - 1)
    return mid(a, b, k), tuple(b[i] - a[i] for i in range(3))


def feather(bone, tone, p, tip, a, wid, layer):
    """Pena: base (coberteira escura) ate a metade, ponta clara em seguida; coplanar, a largura segue o braco."""
    off = (0, 0, -0.012 * layer)
    p, tip = along(p, off, 1), along(tip, off, 1)
    q = mid(p, tip, 0.6)
    lo, hi = (along(p, a, -wid), along(p, a, wid)), (along(q, a, wid), along(q, a, -wid))
    H.panel(bone, "wing", [*lo, *hi], 0.03)
    apex = along(tip, tuple(tip[i] - p[i] for i in range(3)), 0.07)
    H.panel(bone, tone, [along(q, a, -wid), along(q, a, wid), along(tip, a, wid * 0.55), apex, along(tip, a, -wid * 0.55)], 0.03)


def wing(s, n):
    up, low = f"wing{n}.upper", f"wing{n}.lower"
    r, w, t = mx(ROOT, s), mx(WRIST, s), mx(TIP, s)
    H.frustum(up, "wing_dk", r, w, (0.11, 0.1), (0.09, 0.08), sides=6)
    H.frustum(low, "wing_dk", w, t, (0.09, 0.08), (0.03, 0.03), sides=6)
    H.frustum(low, "claw", w, mx((WRIST[0] + 0.12, WRIST[1] + 0.2, WRIST[2] + 0.15), s), (0.05, 0.05), (0.005, 0.005), sides=4)   # garra do pulso
    for i in range(NF):
        u = i / (NF - 1)
        p, d = lead(r, w, t, u)
        ln = sum(c * c for c in d) ** 0.5
        a = tuple(c / ln for c in d)
        bk = mx(BACK, s)
        bn = sum(c * c for c in bk) ** 0.5
        length = 0.6 + 0.55 * u
        tip = along(p, bk, length / bn)
        feather(up if u < 0.5 else low, ("tan", "tan_dk")[i % 2], p, tip, a, 0.17, i)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        legs(s, side)
        arms(s, side)
    wing(1, 1)
    wing(-1, 2)


def joints():
    out = {"pelvis": ((0, PELVIS, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)), "head": ((0, NECK, 0), (0, TOP, 0.2))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = (mx(SH, s), mx(EL, s))
        out[f"forearm.{side}"] = (mx(EL, s), mx(HAND, s))
        out[f"thigh.{side}"] = ((s * LX * 0.85, HIPY, -0.02), (s * LX, KNEE[0], KNEE[1]))
        out[f"shin.{side}"] = ((s * LX, KNEE[0], KNEE[1]), (s * LX, ANK[0], ANK[1]))
        out[f"foot.{side}"] = ((s * LX, ANK[0], ANK[1]), (s * LX, 0.06, 0.3))
    return out


H.build("n02W", "harpy", PALETTE, make, joints())
