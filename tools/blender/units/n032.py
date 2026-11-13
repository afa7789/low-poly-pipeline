"""Harpy Witch (n032, familia harpy): medido em artifacts/model-sheets/refs/n032/sheet.jpg (0.0035 m por pixel).

    blender -b --factory-startup -P tools/blender/units/n032.py -- <out.glb>

Corpo de penas marrom, cabeca de abutre com crista e colar de osso, pernas de ave com garras, asas largas de
4 placas (coberteiras marrons + penas roxas de borda recortada) penduradas atras dos bracos. Os ossos das asas
mantem a direcao de repouso da familia; so as PLACAS pendem. Cajado grande com orbe roxo no antebraco esquerdo.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "brown": 0x4A2D26, "brown_dk": 0x36201B, "wing": 0x7A4B33, "purple": 0x74409A, "yellow": 0xC9922C,
    "claw": 0x25211F, "ivory": 0xB9AFA0, "hair": 0x1E1618, "face": 0xA39C94, "eye": 0xF4F1E2,
    "bone": 0xE8D9B0, "wood": 0x5A3A26, "orb": 0xC25CFF,
}

PELVIS, WAIST, NECK, TOP = 1.3, 1.5, 2.12, 2.7
LX = 0.2
HIPY, KNEE, HOCK, ANK = 1.3, (1.05, 0.2), (0.76, -0.28), (0.34, -0.1)
SH, EL, HAND = (0.45, 2.1, 0.0), (0.68, 1.8, 0.02), (0.98, 1.46, 0.04)
ROOT, WRIST, TIP = (0.4, 2.2, -0.02), (0.96, 1.5, -0.08), (1.12, 1.0, -0.1)
UP_DIR, LOW_DIR = (0.55, 0.25, -0.10), (0.55, -0.15, -0.25)  # direcao de repouso dos ossos de asa da familia
NF = 9          # penas por asa, da raiz do ombro (u=0) ate a ponta (u=1)
BACK = (-0.2, -0.75, -0.75)   # sentido em que as penas descem da borda de ataque (x espelha)
STAFF = ((0.96, 0.3, -0.1), (0.98, 1.2, 0.03), (1.0, 2.1, 0.17), (1.02, 2.75, 0.26))
STAFF_R = ((0.06, 0.06), (0.06, 0.06), (0.05, 0.05), (0.06, 0.06))


def mx(p, s):
    return (p[0] * s, p[1], p[2])


def along(p, w, k):
    return tuple(p[i] + w[i] * k for i in range(3))


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def head():
    H.frustum("head", "brown", (0, 2.0, 0.0), (0, 2.38, 0.26), (0.26, 0.2), (0.17, 0.16), sides=6)      # pescoco curvado a frente
    H.frustum("head", "brown_dk", (0, 2.22, 0.1), (0, 2.58, 0.2), (0.2, 0.2), (0.22, 0.21), sides=6)     # cranio
    H.frustum("head", "face", (0, 2.2, 0.3), (0, 2.56, 0.32), (0.13, 0.11), (0.19, 0.15), sides=6)       # mascara
    H.frustum("head", "ivory", (0, 2.4, 0.36), (0, 2.06, 0.76), (0.12, 0.1), (0.02, 0.02), sides=4)       # bico grosso
    H.frustum("head", "ivory", (0, 2.2, 0.62), (0, 2.02, 0.72), (0.05, 0.045), (0.008, 0.008), sides=4)   # gancho
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
    H.frustum("pelvis", "brown_dk", (0, 1.28, -0.2), (0, 0.9, -0.28), (0.3, 0.07), (0.3, 0.05), sides=4)  # cauda
    H.frustum("spine", "bone", (0, 2.0, 0.3), (0, 1.86, 0.31), (0.03, 0.03), (0.04, 0.04), sides=4)       # colar de osso
    H.panel("pelvis", "purple", [(-0.26, 0.98, -0.3), (0.26, 0.98, -0.3), (0.18, 0.7, -0.33), (0.09, 0.52, -0.35),
                                 (0.0, 0.4, -0.36), (-0.09, 0.52, -0.35), (-0.18, 0.7, -0.33)], 0.04)
    H.frustum("pelvis", "brown_dk", (0, 1.0, 0.18), (0, 0.72, 0.16), (0.24, 0.06), (0.03, 0.03), sides=4)   # saiote de penas


def toes(side, x):
    for dx, dz in ((-0.15, 0.34), (0.0, 0.46), (0.15, 0.34)):
        H.frustum(f"foot.{side}", "yellow", (x + dx * 0.3, 0.1, 0.1), (x + dx, 0.05, 0.1 + dz), (0.06, 0.05), (0.035, 0.03), sides=4)
        H.frustum(f"foot.{side}", "claw", (x + dx, 0.05, 0.1 + dz), (x + dx * 1.1, 0.0, 0.16 + dz), (0.035, 0.03), (0.005, 0.005), sides=4)
    H.frustum(f"foot.{side}", "yellow", (x, 0.12, 0.0), (x, 0.06, -0.22), (0.05, 0.05), (0.012, 0.012), sides=4)


def legs(s, side):
    x = s * LX
    H.frustum(f"thigh.{side}", "brown", (x * 0.85, HIPY + 0.08, -0.02), (x, KNEE[0], KNEE[1]), (0.25, 0.23), (0.16, 0.16), sides=6)
    H.frustum(f"shin.{side}", "brown", (x, KNEE[0] + 0.06, KNEE[1]), (x, HOCK[0], HOCK[1]), (0.14, 0.14), (0.1, 0.1), sides=6)
    H.frustum(f"shin.{side}", "brown", (x, HOCK[0] + 0.04, HOCK[1]), (x, ANK[0] + 0.12, ANK[1]), (0.1, 0.1), (0.07, 0.07), sides=6)
    H.frustum(f"shin.{side}", "yellow", (x, HOCK[0] - 0.08, HOCK[1]), (x, ANK[0] + 0.03, ANK[1]), (0.085, 0.085), (0.065, 0.065), sides=6)
    H.frustum(f"foot.{side}", "yellow", (x, ANK[0] + 0.02, ANK[1]), (x, 0.08, 0.1), (0.08, 0.08), (0.11, 0.06), sides=6)
    toes(side, x)


def arms(s, side):
    sh, el, hd = mx(SH, s), mx(EL, s), mx(HAND, s)
    H.frustum(f"arm.{side}", "brown", (sh[0] - 0.04 * s, sh[1] + 0.12, 0.0), (sh[0] + 0.1 * s, sh[1] - 0.1, 0.0), (0.18, 0.17), (0.17, 0.16), sides=6)   # ombro
    H.frustum(f"arm.{side}", "brown", (sh[0] + 0.08 * s, sh[1] - 0.06, 0.0), el, (0.17, 0.16), (0.12, 0.12), sides=6)
    H.frustum(f"forearm.{side}", "brown", (el[0], el[1] + 0.04, el[2]), (hd[0], hd[1] + 0.02, hd[2]), (0.13, 0.12), (0.1, 0.1), sides=6)
    H.frustum(f"forearm.{side}", "brown_dk", (hd[0], hd[1] + 0.06, hd[2]), (hd[0] + 0.04 * s, hd[1] - 0.1, hd[2] + 0.04), (0.11, 0.1), (0.09, 0.08), sides=6)
    for dx in (-0.05, 0.0, 0.05):
        H.frustum(f"forearm.{side}", "ivory", (hd[0] + dx, hd[1] - 0.08, hd[2] + 0.08), (hd[0] + dx, hd[1] - 0.24, hd[2] + 0.2), (0.025, 0.025), (0.004, 0.004), sides=4)


def staff():
    H.chain("forearm.L", "wood", STAFF, STAFF_R, sides=6)
    top = STAFF[-1]
    for sx in (-1, 1):       # dois dentes de osso em V
        H.frustum("forearm.L", "bone", along(top, (0, 1, 0), -0.04), (top[0] + sx * 0.14, top[1] + 0.26, top[2] + 0.04), (0.045, 0.045), (0.012, 0.012), sides=4)
    H.frustum("forearm.L", "orb", along(top, (0, 1, 0), 0.0), along(top, (0, 1, 0), 0.14), (0.05, 0.05), (0.15, 0.15), sides=6)
    H.frustum("forearm.L", "orb", along(top, (0, 1, 0), 0.14), along(top, (0, 1, 0), 0.3), (0.15, 0.15), (0.03, 0.03), sides=6)


def lead(r, w, t, u):
    """Ponto da borda de ataque e o sentido do osso ali: ombro->pulso->ponta."""
    a, b, k = (r, w, u * 2) if u < 0.5 else (w, t, u * 2 - 1)
    return lerp(a, b, k), tuple(b[i] - a[i] for i in range(3))


def feather(bone, tone, p, tip, a, wid, layer):
    """Pena: base (coberteira escura) ate a metade, ponta clara em seguida; coplanar, a largura segue o braco."""
    off = (0, 0, -0.012 * layer)
    p, tip = along(p, off, 1), along(tip, off, 1)
    q = lerp(p, tip, 0.6)
    lo, hi = (along(p, a, -wid), along(p, a, wid)), (along(q, a, wid), along(q, a, -wid))
    H.panel(bone, "wing", [*lo, *hi], 0.03)
    apex = along(tip, tuple(tip[i] - p[i] for i in range(3)), 0.07)
    H.panel(bone, tone, [along(q, a, -wid), along(q, a, wid), along(tip, a, wid * 0.55), apex, along(tip, a, -wid * 0.55)], 0.03)


def wing(s, n):
    up, low = f"wing{n}.upper", f"wing{n}.lower"
    r, w, t = mx(ROOT, s), mx(WRIST, s), mx(TIP, s)
    H.frustum(up, "wing", r, w, (0.11, 0.1), (0.09, 0.08), sides=6)
    H.frustum(low, "wing", w, t, (0.09, 0.08), (0.03, 0.03), sides=6)
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
        feather(up if u < 0.5 else low, "purple", p, tip, a, 0.17, i)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        legs(s, side)
        arms(s, side)
    staff()
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
    for s, n in ((1, 1), (-1, 2)):      # cabeca nas juntas do modelo, cauda na direcao de repouso da familia
        r, w = mx(ROOT, s), mx(WRIST, s)
        out[f"wing{n}.upper"] = (r, along(r, mx(UP_DIR, s), 0.7))
        out[f"wing{n}.lower"] = (w, along(w, mx(LOW_DIR, s), 0.7))
    return out


H.build("n032", "harpy", PALETTE, make, joints())
