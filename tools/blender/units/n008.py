"""Succubus (n008, familia harpy): medido em artifacts/model-sheets/refs/n008/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n008.py -- <out.glb>

Paira sobre as garras. Mao direita (-x) segura o livro aberto, mao esquerda (+x) o punhal/varinha. Asas de morcego
varridas para tras: braco em frusta nos ossos upper/lower, membrana em H.panel (interna no upper, externa no lower).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "red": 0xB00018, "red_dk": 0x8A0014, "hood": 0x1A1A1C, "wing": 0x6A6A6E, "wing_lt": 0x86868B,
    "steel": 0x78787C, "horn": 0x8A8A8E, "gold": 0xC8A04A, "page": 0xDAD0B4, "cover": 0x58565A,
    "wand": 0x5A3A2E, "boot": 0x6D6D70, "boot_dk": 0x4E4E52, "claw": 0x333336, "belt": 0x151515,
}

# metros do biped; 0,0029 m por pixel na frente e no perfil da prancha
HIP, KNEE, ANKLE, LEG_X = 1.2, 0.7, 0.26, 0.13
WAIST, NECK, TOP = 1.55, 2.2, 2.75
SH = (0.4, 2.05, 0.0)
EL_L, HAND_L = (0.5, 1.72, 0.02), (0.6, 1.62, 0.22)       # esquerda: punhal erguido
EL_R, HAND_R = (-0.5, 1.58, 0.04), (-0.5, 1.45, 0.4)      # direita: livro adiante
ROOT, ELB, TIP = (0.14, 2.05, -0.14), (0.45, 2.8, -0.36), (0.86, 3.5, -0.6)
UP_DIR, LOW_DIR = (0.55, 0.25, -0.10), (0.55, -0.15, -0.25)   # direcao de repouso dos ossos de asa da familia
WIDTH = (-0.36, -0.2, -0.04)                                 # sentido da largura da membrana


def fr(bone, tone, a, b, ra, rb, sides=8):
    """H.frustum com um fator unico de raio para o corpo todo (largura 0,85, profundidade 0,75: a prancha desenha figura esguia de perfil fino)."""
    k, kz = 0.85, 0.75
    return H.frustum(bone, tone, a, b, (ra[0] * k, ra[1] * kz), (rb[0] * k, rb[1] * kz), sides)


def mx(p, s):
    return (p[0] * s, p[1], p[2])


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def along(p, w, k):
    return tuple(p[i] + w[i] * k for i in range(3))


def head():
    fr("head", "red", (0, 2.24, 0.04), (0, 2.6, 0.06), (0.12, 0.13), (0.11, 0.12), sides=6)
    fr("head", "hood", (0, 2.2, -0.07), (0, 2.68, -0.08), (0.21, 0.19), (0.18, 0.18), sides=8)
    fr("head", "hood", (0, 2.66, -0.08), (0, 2.9, -0.2), (0.17, 0.17), (0.02, 0.03), sides=8)
    fr("head", "hood", (0, 2.36, 0.0), (0, 2.5, 0.0), (0.23, 0.12), (0.2, 0.13), sides=6)     # bochechas do capuz
    for s in (-1, 1):
        horn = [(0.15, 2.6, -0.02), (0.22, 2.76, -0.04), (0.17, 2.96, -0.08)]
        H.chain("head", "horn", [mx(p, s) for p in horn], [(0.09, 0.09), (0.07, 0.07), (0.01, 0.01)], sides=6)
    fr("head", "hood", (0, 2.5, -0.15), (0, 2.2, -0.2), (0.17, 0.05), (0.15, 0.05), sides=4)    # cabelo/capuz nas costas
    fr("spine", "hood", (0, 2.2, -0.2), (0, 1.75, -0.24), (0.15, 0.05), (0.1, 0.04), sides=4)


def torso():
    fr("pelvis", "red", (0, 1.0, 0.0), (0, 1.35, 0.0), (0.22, 0.17), (0.19, 0.15), sides=8)
    fr("pelvis", "red", (0, 1.35, 0.0), (0, 1.56, 0.0), (0.21, 0.15), (0.2, 0.15), sides=8)
    fr("pelvis", "belt", (0, 1.5, 0.0), (0, 1.6, 0.0), (0.23, 0.17), (0.23, 0.17), sides=8)
    H.box("pelvis", "gold", (0.04, 1.55, 0.18), (0.09, 0.08, 0.04))
    fr("spine", "red", (0, 1.56, 0.0), (0, 1.9, 0.01), (0.2, 0.15), (0.27, 0.18), sides=8)
    fr("spine", "red", (0, 1.88, 0.01), (0, 2.14, 0.02), (0.27, 0.18), (0.3, 0.18), sides=8)
    fr("spine", "hood", (0, 2.02, 0.0), (0, 2.3, 0.02), (0.34, 0.24), (0.2, 0.2), sides=8)       # gola do capuz
    for s in (-1, 1):
        for i in range(3):   # tassels de ouro no quadril
            fr("pelvis", "gold", (s * 0.27 + 0.045 * i * s, 1.5, 0.05), (s * 0.27 + 0.045 * i * s, 1.2, 0.05), (0.025, 0.025), (0.03, 0.03), sides=4)
    H.box("pelvis", "steel", (0.3, 1.38, 0.2), (0.14, 0.14, 0.04))     # punhal em cruz no quadril


def legs(s, side):
    x = s * LEG_X
    fr(f"thigh.{side}", "red", (x, KNEE - 0.02, 0.0), (x, HIP + 0.06, 0.0), (0.13, 0.14), (0.2, 0.18), sides=6)
    fr(f"shin.{side}", "boot", (x, KNEE - 0.3, 0.0), (x, KNEE + 0.03, 0.02), (0.1, 0.1), (0.15, 0.14), sides=6)
    fr(f"shin.{side}", "boot_dk", (x, ANKLE - 0.02, 0.0), (x, KNEE - 0.28, 0.0), (0.075, 0.07), (0.1, 0.1), sides=6)
    fr(f"foot.{side}", "boot", (x, ANKLE + 0.02, -0.02), (x, 0.1, 0.14), (0.08, 0.08), (0.12, 0.07), sides=6)
    for dx in (-0.07, 0.0, 0.07):
        fr(f"foot.{side}", "claw", (x + dx, 0.14, 0.12), (x + dx * 1.3, 0.02, 0.32), (0.035, 0.03), (0.005, 0.005), sides=4)


def shoulder(s, side):
    bone = f"arm.{side}"
    fr(bone, "steel", (s * 0.22, 2.22, 0.0), (s * 0.54, 2.0, 0.0), (0.2, 0.24), (0.18, 0.22), sides=6)
    fr(bone, "boot_dk", (s * 0.54, 2.0, 0.0), (s * 0.58, 1.96, 0.0), (0.17, 0.22), (0.17, 0.22), sides=6)
    for a, b in (((0.34, 2.28, 0.06), (0.36, 2.52, 0.08)), ((0.52, 2.12, 0.0), (0.64, 2.3, 0.0)), ((0.55, 2.02, 0.15), (0.68, 2.05, 0.3))):
        fr(bone, "horn", mx(a, s), mx(b, s), (0.07, 0.07), (0.01, 0.01), sides=4)


def arms(s, side, el, hand):
    sh = mx(SH, s)
    fr(f"arm.{side}", "red", (sh[0], sh[1] + 0.05, 0.0), el, (0.15, 0.15), (0.12, 0.12), sides=6)
    fr(f"forearm.{side}", "red", (el[0], el[1] + 0.02, el[2]), hand, (0.12, 0.12), (0.09, 0.09), sides=6)
    fr(f"forearm.{side}", "red_dk", (hand[0], hand[1] + 0.02, hand[2]), (hand[0], hand[1] - 0.12, hand[2] + 0.04), (0.1, 0.08), (0.07, 0.06), sides=6)   # mao
    shoulder(s, side)


def book():
    """Livro aberto sobre a mao direita (-x), adiante do corpo."""
    for dy, tone, grow in ((-0.04, "cover", 0.04), (0.0, "page", 0.0)):   # capa e paginas, inclinadas para quem olha
        H.panel("forearm.R", tone, [(-0.5 + sx * (0.34 + grow), 1.46 + dy, 0.74 + grow) for sx in (-1, 1)]
                + [(-0.5 + sx * (0.34 + grow), 1.8 + dy, 0.4 - grow) for sx in (1, -1)], 0.04)
    H.box("forearm.R", "cover", (-0.5, 1.64, 0.57), (0.03, 0.06, 0.3))


def wand():
    """Punhal na mao esquerda, erguido; a lamina aponta para baixo."""
    H.chain("forearm.L", "wand", [(0.62, 1.6, 0.2), (0.62, 1.82, 0.2), (0.62, 2.0, 0.2)], [(0.07, 0.07), (0.06, 0.06), (0.1, 0.1)], sides=6)
    fr("forearm.L", "steel", (0.62, 1.6, 0.2), (0.62, 1.3, 0.2), (0.1, 0.07), (0.01, 0.01), sides=4)


def wing(s, n):
    """Lamina longa e estreita: osso grosso na borda externa, membrana para dentro (interna no upper, externa no lower)."""
    up, low = f"wing{n}.upper", f"wing{n}.lower"
    r, e, t = mx(ROOT, s), mx(ELB, s), mx(TIP, s)
    w = mx(WIDTH, s)
    H.frustum(up, "steel", r, e, (0.1, 0.09), (0.085, 0.07), sides=6)
    H.frustum(low, "steel", e, t, (0.085, 0.07), (0.02, 0.02), sides=6)
    q1, q2 = lerp(e, t, 0.4), lerp(e, t, 0.7)
    H.panel(up, "wing", [r, e, along(e, w, 0.9), along(lerp(r, e, 0.5), w, 0.8), along(r, w, 0.5)], 0.05)
    H.panel(low, "wing_lt", [e, q1, along(q1, w, 0.7), along(e, w, 0.95)], 0.05)
    H.panel(low, "wing", [q1, q2, along(q2, w, 0.45), along(q1, w, 0.7)], 0.05)
    H.panel(low, "wing_lt", [q2, t, along(t, w, 0.08), along(q2, w, 0.45)], 0.05)


def make():
    head()
    torso()
    for s, side, el, hand in ((1, "L", EL_L, HAND_L), (-1, "R", EL_R, HAND_R)):
        legs(s, side)
        arms(s, side, el, hand)
    book()
    wand()
    wing(1, 1)
    wing(-1, 2)


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, WAIST, 0)), "spine": ((0, WAIST, 0), (0, NECK, 0)), "head": ((0, NECK, 0), (0, TOP, 0)),
           "arm.L": (mx(SH, 1), EL_L), "forearm.L": (EL_L, HAND_L), "arm.R": (mx(SH, -1), EL_R), "forearm.R": (EL_R, HAND_R)}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X, KNEE, 0), (s * LEG_X, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X, ANKLE, 0), (s * LEG_X, 0.1, 0.4))
    for s, n in ((1, 1), (-1, 2)):
        r, e = mx(ROOT, s), mx(ELB, s)      # cabecas nas juntas do modelo, caudas na direcao de repouso da familia
        out[f"wing{n}.upper"] = (r, along(r, mx(UP_DIR, s), 0.7))
        out[f"wing{n}.lower"] = (e, along(e, mx(LOW_DIR, s), 0.7))
    return out


H.build("n008", "harpy", PALETTE, make, joints())
