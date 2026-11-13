"""Cloud Ship (h07S): medido em artifacts/model-sheets/refs/h07S/sheet.jpg (perfil ~0.005 m por pixel).

    blender -b --factory-startup -P tools/blender/units/h07S.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "wood": 0x4F312C, "wood_lt": 0x6A453B, "copper": 0xC8693A, "copper_lt": 0xE0894F, "red": 0xB82A32,
    "dark": 0x4A2A26, "teal": 0x1E6B78, "deck": 0xC8A868, "bamboo": 0xCFB46C, "steel": 0x8A8F94,
    "smoke": 0x161412, "cargo": 0xB5502E, "black": 0x201E1C,
}

YC = 1.1                      # eixo do barril
# (z, meia largura) do barril, da proa à popa; a meia altura é 0.82 dela
BARREL = ((1.3, 0.4), (1.0, 0.6), (0.4, 0.69), (-0.4, 0.69), (-1.0, 0.6), (-1.3, 0.42))
SAIL_T = (-1.0, -1 / 3, 1 / 3, 1.0)
SAIL_BILLOW = (0.0, 0.25, 0.25, 0.0)
SAIL_SPAN = (1.25, 1.15)      # meia extensão em x e z da vela, deitada na diagonal


def ring(bone, tone, z0, z1, r0, r1, y=YC, x=0.0, sides=8):
    H.frustum(bone, tone, (x, y, z0), (x, y, z1), (r0, r0), (r1, r1), sides)


def barrel():
    for (z0, r0), (z1, r1) in zip(BARREL, BARREL[1:]):
        H.frustum("hull", "wood", (0, YC, z0), (0, YC, z1), (r0, r0 * 0.82), (r1, r1 * 0.82), 10)
    for z in (0.5, -0.62):
        H.frustum("hull", "copper", (0, YC, z - 0.06), (0, YC, z + 0.06), (0.74, 0.62), (0.74, 0.62), 10)
    H.frustum("hull", "copper", (0, YC, 1.3), (0, YC, 1.36), (0.43, 0.36), (0.43, 0.36), 10)      # aro da proa
    H.frustum("hull", "wood_lt", (0, YC, 1.34), (0, YC, 1.4), (0.3, 0.25), (0.3, 0.25), 10)        # tampa
    H.frustum("hull", "wood_lt", (0, YC, -1.3), (0, YC, -1.36), (0.44, 0.36), (0.4, 0.33), 10)
    H.frustum("hull", "deck", (0, 1.52, 0), (0, 1.68, 0), (0.6, 1.25), (0.58, 1.2), 8)             # convés


def spout():
    pts = ((0, 1.0, 1.25), (0, 1.15, 1.55), (0, 1.36, 1.78), (0, 1.62, 1.92))
    H.chain("hull", "copper", pts, ((0.3, 0.3), (0.22, 0.22), (0.12, 0.12), (0.2, 0.2)), 8)
    H.frustum("hull", "black", (0, 1.62, 1.92), (0, 1.64, 1.96), (0.15, 0.15), (0.15, 0.15), 8)


def chimney():
    pts = ((0, 1.6, -0.95), (0, 1.85, -1.2), (0, 2.12, -1.5))
    H.chain("rudder", "copper", pts, ((0.17, 0.17), (0.13, 0.13), (0.2, 0.2)), 8)
    H.frustum("rudder", "black", (0, 2.12, -1.5), (0, 2.16, -1.54), (0.14, 0.14), (0.14, 0.14), 8)
    for i, (y, z, s) in enumerate(((2.3, -1.62, 0.26), (2.5, -1.78, 0.3), (2.62, -1.95, 0.3), (2.85, -2.1, 0.28))):
        H.box("rudder", "smoke", (0.04 * (-1) ** i, y, z), (s, s, s))                              # fumaça em blocos


def sail():
    def at(t, y, push):
        return (-SAIL_SPAN[0] * t + 0.7 * push, y, SAIL_SPAN[1] * t + 0.7 * push)
    tops, bots = [3.8 + 0.55 * t for t in SAIL_T], [2.35 + 0.55 * t for t in SAIL_T]
    for i in range(3):
        quad = [at(SAIL_T[i], tops[i], SAIL_BILLOW[i]), at(SAIL_T[i + 1], tops[i + 1], SAIL_BILLOW[i + 1]),
                at(SAIL_T[i + 1], bots[i + 1], SAIL_BILLOW[i + 1]), at(SAIL_T[i], bots[i], SAIL_BILLOW[i])]
        H.panel("hull", "red", quad, 0.05)
    for s in (0.0, 1 / 3, 2 / 3, 1.0):                                     # varas horizontais
        pts = [at(t, b + (a - b) * s, o + 0.12) for t, a, b, o in zip(SAIL_T, tops, bots, SAIL_BILLOW)]
        H.chain("hull", "dark", pts, [(0.045, 0.045)] * 4, 6)
    H.frustum("hull", "dark", (0, 1.7, 0), (0, 4.15, 0), (0.07, 0.07), (0.05, 0.05), 6)               # mastro
    H.box("hull", "teal", (0, 1.82, 0.05), (0.58, 0.5, 0.52))                                         # casa da máquina
    ring("hull", "dark", 0.3, 0.72, 0.07, 0.07, y=1.9, sides=6)


def rails():
    for s in (-1, 1):
        for z0, z1 in ((0.7, 1.15), (-1.15, -0.65)):
            H.box("hull", "bamboo", (0.5 * s, 1.84, (z0 + z1) / 2), (0.05, 0.05, z1 - z0))
            for z in (z0, z1):
                H.box("hull", "bamboo", (0.5 * s, 1.76, z), (0.05, 0.2, 0.05))
    H.box("hull", "bamboo", (0, 1.84, 1.15), (1.0, 0.05, 0.05))
    H.box("hull", "bamboo", (0, 1.84, -1.15), (1.0, 0.05, 0.05))


def launchers():
    """Três lanças de bambu na lateral esquerda, apontando à frente: ficam no osso que se mexe no ataque."""
    for y in (1.42, 1.18, 0.94):
        x = 0.86
        ring("gondola", "bamboo", -0.9, 1.15, 0.06, 0.06, y=y, x=x, sides=6)
        ring("gondola", "steel", 1.12, 1.62, 0.15, 0.01, y=y, x=x, sides=4)                            # ponta da lança
        ring("gondola", "dark", -0.2, -0.12, 0.07, 0.07, y=y, x=x, sides=6)
    for y in (1.42, 0.94):
        H.frustum("gondola", "dark", (0.74, y, 0.3), (0.86, 1.18, 0.3), (0.03, 0.03), (0.03, 0.03), 4)  # braçadeira
        H.frustum("gondola", "dark", (0.74, y, -0.5), (0.86, 1.18, -0.5), (0.03, 0.03), (0.03, 0.03), 4)


def basket():
    H.frustum("gondola", "bamboo", (0, 0.2, 0), (0, 0.55, 0), (0.28, 0.3), (0.42, 0.42), 8)
    for x, z in ((-0.13, -0.1), (0.12, 0.08), (0, 0.15)):
        H.box("gondola", "cargo", (x, 0.64, z), (0.22, 0.14, 0.22))
    for sx in (-1, 1):
        for sz in (-1, 1):
            H.frustum("gondola", "bamboo", (0.38 * sx, 0.55, 0.38 * sz), (0.28 * sx, 0.95, 0.28 * sz), (0.025, 0.025), (0.025, 0.025), 4)


def make():
    barrel()
    spout()
    chimney()
    sail()
    rails()
    launchers()
    basket()


JOINTS = {"hull": ((0, YC, -0.4), (0, YC, 0.4)), "gondola": ((0, YC, -0.9), (0, YC, -0.1)),
          "rudder": ((0, 1.6, -0.95), (0, 2.1, -1.5)), "prop": ((0, YC, -1.4), (0, YC, -1.7))}

H.build("h07S", "aircraft", PALETTE, make, JOINTS)
