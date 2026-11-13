"""Assault Tank (h099): medido em artifacts/model-sheets/refs/h099/sheet.jpg (perfil: 0.0036 m por pixel exibido).

    blender -b --factory-startup -P tools/blender/units/h06T.py -- <out.glb>
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "gold": 0xD4A82E, "red": 0xC21414, "grey": 0x8C8984, "grey_dk": 0x6C6862, "black": 0x201E1C,
    "orange": 0xC8693A, "smoke": 0x161412, "steel": 0x77736E, "copper_dk": 0x8E4A26,
}

HALF_W = 0.57                       # meia largura do casco
HULL_LO, HULL_HI = 0.55, 1.1
HULL_FRONT, HULL_REAR = 0.8, -0.62
HC = (HULL_FRONT + HULL_REAR) / 2
WHEEL_X0, WHEEL_X1 = 0.60, 0.94     # face interna / externa do pneu (lado esquerdo)
# (osso esquerdo, osso direito, z do eixo, raio do pneu)
AXLES = (("wheel1", "wheel2", 0.45, 0.36), ("wheel3", "wheel4", -0.39, 0.42))
PLOW = ((1.0, 1.15), (1.1, 0.9), (1.25, 0.55), (1.42, 0.2), (1.55, 0.03))   # (z, y) da lâmina curva
SPOKES = 6
TURRET_RING = ((0, 1.1, 0.0), (0, 1.1, 0.5))


def wheel(bone, s, z, r):
    y = r
    a, b = s * WHEEL_X0, s * WHEEL_X1
    H.frustum(bone, "grey", (a, y, z), (b, y, z), (r, r), (r, r), sides=12)
    mid = (a + b) / 2
    H.frustum(bone, "gold", (mid - s * 0.02, y, z), (mid + s * 0.02, y, z), (r * 1.03, r * 1.03), (r * 1.03, r * 1.03), sides=12)
    H.frustum(bone, "black", (b, y, z), (b + s * 0.03, y, z), (r * 0.74, r * 0.74), (r * 0.74, r * 0.74), sides=8)
    H.frustum(bone, "gold", (b + s * 0.02, y, z), (b + s * 0.06, y, z), (r * 0.26, r * 0.26), (r * 0.26, r * 0.26), sides=6)
    for k in range(SPOKES):     # leque de raios dourados, cada um do eixo até o aro
        ang = k * math.pi / SPOKES * 2
        tip = (b + s * 0.04, y + r * 0.7 * math.sin(ang), z + r * 0.7 * math.cos(ang))
        H.frustum(bone, "gold", (b + s * 0.025, y, z), tip, (0.012, 0.045), (0.012, 0.03), sides=4)


ROW_W = (0.78, 0.8, 0.82, 0.84, 0.86)        # meia largura da casca em cada ponto da curva (arredonda a borda de baixo)
BOW = 0.25                                   # quanto as colunas das pontas recuam: a proa é redonda na planta
RIM_DZ = BOW * 0.68 ** 2 - 0.04                # o aro fica à frente das colunas das pontas
COLS = (-0.68, 0.0, 0.68)


def plow():
    """Casca facetada: cada trecho da curva do perfil é dividido em 3 colunas, as das pontas recuadas."""
    for i, ((z0, y0), (z1, y1)) in enumerate(zip(PLOW, PLOW[1:])):
        w = (ROW_W[i] + ROW_W[i + 1]) / 2
        for c in COLS:
            dz = -BOW * c * c
            H.frustum("hull", "grey", (c * w, y0, z0 + dz), (c * w, y1, z1 + dz), (w * 0.42, 0.09), (w * 0.42, 0.09), sides=4)
    for s in (-1, 1):       # aro dourado de cada lado, seguindo a borda da casca
        for i, ((z0, y0), (z1, y1)) in enumerate(zip(PLOW, PLOW[1:])):
            H.frustum("hull", "gold", (s * ROW_W[i], y0, z0 - RIM_DZ), (s * ROW_W[i + 1], y1, z1 - RIM_DZ),
                      (0.05, 0.06), (0.05, 0.06), sides=4)
    H.frustum("hull", "gold", (0, 0.04, 1.4), (0, 0.04, 1.58), (0.8, 0.03), (0.6, 0.03), sides=4)    # lábio
    H.frustum("hull", "gold", (0, 1.16, 0.98), (0, 1.0, 1.02), (0.8, 0.04), (0.82, 0.04), sides=4)    # aro de cima


def hull():
    H.box("hull", "black", (0, HULL_LO - 0.04, HC), (0.9, 0.12, 1.3))                    # chassi
    H.box("hull", "red", (0, (HULL_LO + HULL_HI) / 2, HC), (2 * HALF_W - 0.04, 0.5, HULL_FRONT - HULL_REAR - 0.06))
    H.box("hull", "black", (0, HULL_HI - 0.01, HC), (2 * HALF_W - 0.14, 0.04, 1.3))      # convés escuro
    for s in (-1, 1):
        H.box("hull", "gold", (s * HALF_W, HULL_HI, HC), (0.07, 0.06, HULL_FRONT - HULL_REAR))    # longarinas
        H.box("hull", "gold", (s * HALF_W, 0.9, HULL_FRONT - 0.03), (0.07, 0.6, 0.06))
        H.box("hull", "gold", (s * HALF_W, 0.9, HULL_REAR + 0.03), (0.07, 0.6, 0.06))
    H.box("hull", "gold", (0, HULL_HI, HULL_REAR + 0.03), (2 * HALF_W, 0.06, 0.07))
    H.box("hull", "gold", (0, HULL_HI, HULL_FRONT - 0.03), (2 * HALF_W, 0.06, 0.07))
    H.box("hull", "gold", (0, 0.9, HULL_REAR - 0.015), (2 * HALF_W - 0.04, 0.5, 0.05))     # moldura traseira
    H.box("hull", "grey", (0, 0.9, HULL_REAR - 0.045), (0.82, 0.4, 0.03))
    for s in (-1, 1):       # tanques de cobre nas laterais do convés, com cintas
        H.frustum("hull", "orange", (s * 0.62, 1.15, -0.5), (s * 0.62, 1.15, 0.12), (0.16, 0.16), (0.16, 0.16), sides=8)
        for z in (-0.38, -0.1):
            H.frustum("hull", "copper_dk", (s * 0.62, 1.15, z - 0.03), (s * 0.62, 1.15, z + 0.03), (0.175, 0.175), (0.175, 0.175), sides=8)
        H.frustum("hull", "grey_dk", (s * 0.34, 1.1, -0.58), (s * 0.5, 1.4, -0.7), (0.1, 0.1), (0.12, 0.12), sides=6)     # escapamento
        H.frustum("hull", "grey", (s * 0.5, 1.4, -0.7), (s * 0.7, 1.72, -0.82), (0.12, 0.12), (0.15, 0.15), sides=6)
        H.frustum("hull", "smoke", (s * 0.68, 1.68, -0.81), (s * 0.78, 1.84, -0.86), (0.15, 0.15), (0.17, 0.17), sides=6)
    H.frustum("hull", "black", (0, 0.72, -0.1), (0, 0.72, HULL_REAR - 0.02), (0.5, 0.42), (0.46, 0.4), sides=8)    # corpo escuro atrás
    for _, _, z, r in AXLES:
        H.frustum("hull", "steel", (-0.62, r, z), (0.62, r, z), (0.05, 0.05), (0.05, 0.05), sides=6)   # eixo


def turret():
    H.frustum("head", "gold", (0, 1.08, 0.0), (0, 1.2, 0.0), (0.48, 0.48), (0.5, 0.5), sides=8)      # anel
    H.frustum("head", "grey", (0, 1.2, 0.0), (0, 1.42, 0.0), (0.5, 0.5), (0.52, 0.52), sides=8)      # cúpula
    H.frustum("head", "grey", (0, 1.42, 0.0), (0, 1.6, 0.0), (0.52, 0.52), (0.4, 0.4), sides=8)
    H.frustum("head", "gold", (0, 1.58, 0.0), (0, 1.66, 0.0), (0.4, 0.4), (0.34, 0.34), sides=8)
    H.frustum("head", "grey_dk", (0, 1.64, 0.0), (0, 1.7, 0.0), (0.26, 0.26), (0.22, 0.22), sides=6)  # escotilha
    H.frustum("head", "gold", (0, 1.3, -0.1), (0, 1.38, 0.38), (0.2, 0.2), (0.22, 0.22), sides=6)     # culatra
    H.frustum("head", "gold", (0, 1.38, 0.38), (0, 1.58, 1.0), (0.22, 0.22), (0.19, 0.19), sides=6)   # cano
    H.frustum("head", "gold", (0, 1.56, 0.92), (0, 1.62, 1.12), (0.26, 0.26), (0.26, 0.26), sides=6)  # boca
    H.frustum("head", "black", (0, 1.62, 1.12), (0, 1.63, 1.14), (0.17, 0.17), (0.17, 0.17), sides=6)


def make():
    hull()
    plow()
    turret()
    for bl, br, z, r in AXLES:
        wheel(bl, 1, z, r)
        wheel(br, -1, z, r)


def joints():
    out = {"head": TURRET_RING}
    for (bl, br, z, r) in AXLES:
        out[bl] = ((WHEEL_X0, r, z), (WHEEL_X1, r, z))
        out[br] = ((-WHEEL_X0, r, z), (-WHEEL_X1, r, z))
    return out


H.build("h06T", "vehicle", PALETTE, make, joints())
