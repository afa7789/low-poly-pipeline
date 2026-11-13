"""Mortar (hmtm): o morteiro da folha (artifacts/model-sheets/refs/hmtm/sheet.jpg, perfil: 0.0038 m por pixel)
sobre um carrinho de quatro rodas de ferro (a folha o desenha em patins; a familia vehicle precisa de rodas).
Os dois anoes da equipe (o ruivo com o projetil e o de capacete com o martelo) ficam parados atras do morteiro, no hull
(o perfil da folha os poe atras do tubo); o tubo, no head, e a peca que ataca.

    blender -b --factory-startup -P tools/blender/units/hmtm.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "iron": 0x5A5D61, "iron_dk": 0x3E4044, "barrel": 0x74787C, "barrel_dk": 0x4C4F53, "gold": 0xB9954F,
    "black": 0x1C1C1E, "red": 0xB52A22, "wood": 0x6E4A2E,
    "skin": 0xE8A58A, "ginger": 0xD2641E, "apron": 0xC4A06A, "brown": 0x5C3D28, "boot": 0x40281A, "steel": 0x8A8E93,
    "plate": 0x757A80, "blue": 0x3F5F8F, "white": 0xE9E9E4,
}
BREECH, MUZZLE = (0.0, 0.34, -0.42), (0.0, 1.36, 0.52)     # eixo do tubo (y, z), inclinado 47 graus
PIVOT_Y = 0.78
AXLES = (("wheel1", "wheel2", 0.42), ("wheel3", "wheel4", -0.42))
WHEEL_R, WHEEL_X = 0.25, 0.66
RAIL_Y, RAIL_X = 0.28, 0.5


def along(t):
    return tuple(b + t * (m - b) for b, m in zip(BREECH, MUZZLE))


def ring(tone, t0, t1, r0, r1, sides=8):
    H.frustum("head", tone, along(t0), along(t1), (r0 * 1.2, r0 * 1.2), (r1 * 1.2, r1 * 1.2), sides)


def barrel():
    ring("barrel_dk", -0.02, 0.1, 0.2, 0.3)             # culatra arredondada
    ring("barrel", 0.08, 0.3, 0.3, 0.36)
    ring("gold", 0.28, 0.36, 0.38, 0.38)
    ring("barrel", 0.34, 0.62, 0.36, 0.34)
    ring("gold", 0.6, 0.68, 0.36, 0.36)
    ring("barrel", 0.66, 0.9, 0.34, 0.37)
    ring("gold", 0.88, 0.97, 0.4, 0.4)                  # boca com aro
    ring("barrel_dk", 0.95, 1.02, 0.38, 0.36)
    ring("black", 1.0, 1.03, 0.29, 0.29)                # o furo
    p = along(0.3)
    for s in (-1, 1):                                    # munhoes
        H.frustum("head", "gold", (s * 0.36, p[1], p[2]), (s * 0.5, p[1], p[2]), (0.1, 0.1), (0.12, 0.12), sides=6)
    H.frustum("head", "gold", (0.0, along(0.2)[1] - 0.05, along(0.2)[2]), (0.0, 0.05 + PIVOT_Y - 0.5, 0.0), (0.12, 0.12), (0.1, 0.1), sides=6)


def frame():
    for s in (-1, 1):
        x = s * RAIL_X
        H.box("hull", "iron_dk", (x, RAIL_Y, 0.0), (0.12, 0.1, 1.3))                                  # longarina
        H.frustum("hull", "iron", (x, RAIL_Y, 0.52), (x, PIVOT_Y, 0.04), (0.08, 0.09), (0.09, 0.07), sides=4)    # perna da frente
        H.frustum("hull", "iron", (x, RAIL_Y, -0.55), (x, PIVOT_Y, -0.02), (0.08, 0.09), (0.09, 0.07), sides=4)  # perna de tras
        H.frustum("hull", "gold", (x - s * 0.02, PIVOT_Y, 0.0), (x + s * 0.07, PIVOT_Y, 0.0), (0.12, 0.12), (0.12, 0.12), sides=6)   # mancal
    for z in (0.5, -0.5):
        H.box("hull", "iron_dk", (0, RAIL_Y, z), (2 * RAIL_X, 0.1, 0.1))                              # travessas
    H.box("hull", "iron", (0, RAIL_Y + 0.07, -0.05), (0.8, 0.06, 0.5))                               # chapa de apoio
    H.box("hull", "wood", (0, RAIL_Y + 0.14, -0.55), (0.34, 0.12, 0.2))                              # caixa de projeteis
    H.frustum("hull", "red", (0, RAIL_Y + 0.2, -0.55), (0, RAIL_Y + 0.3, -0.55), (0.12, 0.1), (0.07, 0.07), sides=6)  # ponta de projetil
    for z in (0.5, -0.5):                                                                              # eixos
        H.frustum("hull", "iron_dk", (-WHEEL_X, WHEEL_R, z * 0.84), (WHEEL_X, WHEEL_R, z * 0.84), (0.04, 0.04), (0.04, 0.04), sides=6)


def wheel(bone, s, z):
    x = s * WHEEL_X
    H.wheel(bone, "iron_dk", (x, WHEEL_R, z), WHEEL_R, 0.14, sides=10)
    H.wheel(bone, "iron", (x + s * 0.05, WHEEL_R, z), WHEEL_R * 0.78, 0.06, sides=10)
    H.wheel(bone, "gold", (x + s * 0.09, WHEEL_R, z), 0.07, 0.06, sides=6)


def tower(tone, x, z, pts, sides=5):
    """Pilha de troncos de cone no hull: pts = [(y, rx, rz), ...] centrada em (x, z)."""
    for a, b in zip(pts, pts[1:]):
        H.frustum("hull", tone, (x, a[0], z), (x, b[0], z), a[1:], b[1:], sides=sides)


def boots_legs(cx, cz, leg, gap):
    for s in (-1, 1):
        x = cx + s * gap
        tower("boot", x, cz + 0.05, [(0.02, 0.17, 0.24), (0.14, 0.15, 0.17), (0.26, 0.17, 0.17)])
        tower(leg, x, cz, [(0.24, 0.15, 0.15), (0.45, 0.16, 0.16), (0.64, 0.19, 0.18)])


def big_dwarf(cx, cz):
    """O ruivo de avental com o projetil no colo (1,5 m com o topete)."""
    boots_legs(cx, cz, "brown", 0.15)
    tower("apron", cx, cz, [(0.5, 0.3, 0.22), (0.78, 0.38, 0.27), (1.0, 0.33, 0.25)])
    tower("skin", cx, cz, [(0.95, 0.34, 0.25), (1.18, 0.48, 0.28), (1.3, 0.3, 0.22)])
    for s in (-1, 1):
        x = cx + s * 0.46
        tower("skin", x, cz, [(1.2, 0.17, 0.17), (1.08, 0.18, 0.18), (0.95, 0.15, 0.15)])
        tower("skin", x - s * 0.06, cz + 0.12, [(0.97, 0.14, 0.14), (0.88, 0.13, 0.14), (0.8, 0.16, 0.14)])
    H.frustum("hull", "iron_dk", (cx - 0.28, 0.96, cz + 0.3), (cx + 0.2, 1.1, cz + 0.32), (0.11, 0.11), (0.11, 0.11), sides=6)
    H.frustum("hull", "red", (cx + 0.2, 1.1, cz + 0.32), (cx + 0.4, 1.16, cz + 0.32), (0.11, 0.11), (0.02, 0.02), sides=6)
    tower("skin", cx, cz + 0.02, [(1.28, 0.13, 0.13), (1.36, 0.22, 0.2), (1.52, 0.2, 0.2)])
    tower("ginger", cx, cz + 0.12, [(1.5, 0.12, 0.08), (1.28, 0.2, 0.1), (1.0, 0.1, 0.04)])      # barba
    tower("ginger", cx, cz - 0.04, [(1.5, 0.08, 0.08), (1.7, 0.05, 0.05)])                        # topete


def small_dwarf(cx, cz):
    """O de capacete, armadura e martelo (1,3 m)."""
    boots_legs(cx, cz, "blue", 0.13)
    tower("plate", cx, cz, [(0.6, 0.3, 0.22), (0.86, 0.38, 0.26), (1.08, 0.34, 0.22)])
    for s in (-1, 1):
        x = cx + s * 0.4
        tower("plate", x, cz, [(1.06, 0.15, 0.15), (0.98, 0.16, 0.16), (0.84, 0.13, 0.13)])
        tower("skin", x, cz + 0.05, [(0.86, 0.12, 0.12), (0.74, 0.12, 0.12), (0.64, 0.15, 0.13)])
    hx = cx - 0.4
    H.frustum("hull", "wood", (hx, 0.2, cz + 0.08), (hx, 1.5, cz + 0.08), (0.04, 0.04), (0.04, 0.04), sides=4)
    H.box("hull", "gold", (hx, 1.5, cz + 0.08), (0.28, 0.2, 0.2))
    tower("white", cx, cz + 0.1, [(1.05, 0.16, 0.08), (0.9, 0.22, 0.12), (0.7, 0.1, 0.05)])        # barba
    tower("skin", cx, cz + 0.02, [(1.04, 0.12, 0.12), (1.2, 0.17, 0.16)])
    tower("steel", cx, cz, [(1.17, 0.22, 0.22), (1.3, 0.22, 0.21), (1.42, 0.12, 0.12)], 8)        # capacete
    tower("steel", cx, cz + 0.02, [(1.2, 0.27, 0.27), (1.22, 0.29, 0.29)], 8)                       # aba


def crew():
    big_dwarf(0.45, -1.1)
    small_dwarf(-0.45, -1.15)


def make():
    frame()
    barrel()
    crew()
    for bl, br, z in AXLES:
        wheel(bl, 1, z * 0.84)
        wheel(br, -1, z * 0.84)


def joints():
    out = {"head": ((0, PIVOT_Y, -0.1), (0, PIVOT_Y, 0.4))}
    for bl, br, z in AXLES:
        out[bl] = ((WHEEL_X - 0.07, WHEEL_R, z * 0.84), (WHEEL_X + 0.07, WHEEL_R, z * 0.84))
        out[br] = ((-WHEEL_X + 0.07, WHEEL_R, z * 0.84), (-WHEEL_X - 0.07, WHEEL_R, z * 0.84))
    return out


H.build("hmtm", "vehicle", PALETTE, make, joints())
