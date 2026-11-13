"""Master Archer (n023): medido em artifacts/model-sheets/refs/n023/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n023.py -- <out.glb>

Arco de 2,7 m na mao ESQUERDA, no osso forearm.L (mira longa ao lado do corpo), luneta dourada presa ao arco,
tablet no antebraco direito, aljava inclinada e garrafa nas costas.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {     # cores lidas da prancha
    "teal": 0x3E9AA0, "teal_dk": 0x2F7C83, "skirt": 0x1F2E2E, "pants": 0x5A6B66, "boot": 0x536663,
    "sash": 0xB5BDB5, "wrap": 0xDDE3D8, "bow": 0x7C8A84, "bow_dk": 0x5D6A65, "gold": 0xC49A3A,
    "skin": 0xB79088, "mask": 0xD9E0D2, "hood": 0x243434, "lens": 0x35B5C8, "black": 0x111818,
    "quiver": 0x1B2B2C, "arrow": 0xC9A04A, "bottle": 0xDDE5D6, "cork": 0x8A6040, "tablet": 0xD0DBCB,
    "frame": 0x707B78, "string": 0xE6E8E2,
}

SH_Y, EL_Y, WR_Y = 2.08, 1.70, 1.40
GRIP_X, GRIP_Z = 0.76, 0.27      # a mao esquerda fecha no cabo do arco, a frente do corpo


def head():
    H.frustum("head", "hood", (0, 2.16, -0.03), (0, 2.62, -0.03), (0.16, 0.16), (0.17, 0.18), sides=8)
    H.frustum("head", "hood", (0, 2.62, -0.03), (0, 2.76, -0.03), (0.17, 0.18), (0.09, 0.1), sides=8)
    H.frustum("head", "mask", (0, 2.27, 0.17), (0, 2.5, 0.18), (0.12, 0.1), (0.14, 0.1), sides=6)      # mascara oval
    H.frustum("head", "mask", (0, 2.5, 0.18), (0, 2.72, 0.14), (0.14, 0.1), (0.1, 0.08), sides=6)
    H.frustum("head", "gold", (0.08, 2.5, 0.27), (0.08, 2.5, 0.33), (0.08, 0.08), (0.08, 0.08), sides=8)    # monoculo
    H.frustum("head", "lens", (0.08, 2.5, 0.33), (0.08, 2.5, 0.355), (0.055, 0.055), (0.055, 0.055), sides=8)
    H.box("head", "black", (-0.07, 2.5, 0.285), (0.1, 0.05, 0.03))
    for s in (-1, 1):       # orelhas longas de elfo
        H.chain("head", "skin", [(s * 0.12, 2.46, 0.0), (s * 0.27, 2.58, -0.02), (s * 0.4, 2.67, -0.04)],
                [(0.07, 0.03), (0.05, 0.02), (0.008, 0.008)], sides=4)


def torso():
    H.frustum("spine", "teal", (0, 1.5, 0), (0, 2.0, 0), (0.31, 0.23), (0.43, 0.26), sides=8)
    H.frustum("spine", "teal", (0, 2.0, 0), (0, 2.18, 0), (0.43, 0.26), (0.27, 0.21), sides=8)
    H.frustum("spine", "teal_dk", (0, 2.08, -0.02), (0, 2.4, -0.02), (0.31, 0.25), (0.34, 0.27), sides=6)     # gola alta
    H.frustum("spine", "hood", (0, 2.08, 0.02), (0, 2.34, 0.02), (0.2, 0.2), (0.17, 0.17), sides=6)          # pescoco
    H.box("spine", "black", (0, 1.9, 0.255), (0.16, 0.4, 0.04))                  # peito escuro no V da jaqueta
    H.frustum("pelvis", "sash", (0, 1.42, 0), (0, 1.64, 0), (0.35, 0.27), (0.34, 0.26), sides=8)         # faixa
    H.frustum("pelvis", "pants", (0, 1.0, 0), (0, 1.3, 0), (0.4, 0.3), (0.37, 0.28), sides=8)


def hem(p):
    return {"pelvis": 1.0} if p[1] > 1.0 else {"pelvis": 0.45, "thigh.L" if p[0] > 0 else "thigh.R": 0.55}


def skirt():
    H.frustum("pelvis", "skirt", (0, 1.1, -0.04), (0, 1.58, 0), (0.42, 0.31), (0.34, 0.25), sides=8)
    mid = H.frustum("pelvis", "skirt", (0, 0.8, -0.06), (0, 1.1, -0.04), (0.5, 0.4), (0.42, 0.31), sides=8)
    low = H.frustum("pelvis", "skirt", (0, 0.58, -0.1), (0, 0.84, -0.06), (0.56, 0.46), (0.5, 0.4), sides=8)
    tail = H.frustum("pelvis", "skirt", (0, 0.92, -0.28), (0, 0.38, -0.36), (0.44, 0.3), (0.14, 0.1), sides=4)   # ponta longa atras
    tip = H.frustum("pelvis", "skirt", (0, 0.9, 0.22), (0, 0.5, 0.26), (0.34, 0.2), (0.1, 0.08), sides=4)       # ponta curta na frente
    for piece in (mid, low, tail, tip):
        H.soft(piece, hem)


def legs():
    for s, side in ((1, "L"), (-1, "R")):
        x = s * 0.28
        H.frustum(f"thigh.{side}", "pants", (x, 0.5, 0), (x, 1.2, 0), (0.23, 0.22), (0.29, 0.28), sides=6)
        H.frustum(f"shin.{side}", "wrap", (x, 0.4, 0), (x, 0.62, 0), (0.17, 0.17), (0.22, 0.22), sides=6)
        H.frustum(f"shin.{side}", "boot", (x, 0.32, 0), (x, 0.42, 0), (0.18, 0.18), (0.17, 0.17), sides=6)
        H.frustum(f"shin.{side}", "wrap", (x, 0.2, 0), (x, 0.33, 0), (0.18, 0.18), (0.19, 0.19), sides=6)
        H.frustum(f"foot.{side}", "boot", (x, 0.03, -0.02), (x, 0.24, -0.02), (0.17, 0.19), (0.15, 0.16), sides=6)
        H.frustum(f"foot.{side}", "boot", (x, 0.11, 0.05), (x, 0.08, 0.42), (0.17, 0.1), (0.15, 0.06), sides=4)


def right_arm():
    H.frustum("arm.R", "teal", (-0.46, SH_Y + 0.06, 0), (-0.58, EL_Y - 0.02, 0), (0.2, 0.22), (0.22, 0.24), sides=6)
    H.frustum("forearm.R", "teal", (-0.58, EL_Y + 0.02, 0), (-0.6, 1.58, 0.01), (0.23, 0.25), (0.2, 0.2), sides=6)
    H.frustum("forearm.R", "gold", (-0.6, 1.62, 0.01), (-0.62, 1.34, 0.02), (0.16, 0.17), (0.145, 0.15), sides=6)
    H.frustum("forearm.R", "frame", (-0.62, 1.5, 0.02), (-0.62, 1.44, 0.02), (0.175, 0.18), (0.175, 0.18), sides=6)
    H.frustum("forearm.R", "skin", (-0.62, 1.36, 0.02), (-0.63, 1.12, 0.05), (0.12, 0.1), (0.15, 0.1), sides=6)
    H.frustum("forearm.R", "skin", (-0.63, 1.14, 0.05), (-0.64, 0.95, 0.08), (0.15, 0.1), (0.09, 0.06), sides=6)
    H.box("forearm.R", "frame", (-0.8, 1.5, 0.04), (0.08, 0.46, 0.32))                # tablet
    H.box("forearm.R", "tablet", (-0.84, 1.5, 0.04), (0.04, 0.38, 0.26))


def left_arm():
    H.frustum("arm.L", "teal", (0.46, SH_Y + 0.06, 0), (0.58, EL_Y - 0.02, 0.03), (0.2, 0.22), (0.22, 0.24), sides=6)
    H.frustum("forearm.L", "teal", (0.58, EL_Y + 0.02, 0.03), (0.62, 1.58, 0.1), (0.23, 0.25), (0.2, 0.2), sides=6)
    H.frustum("forearm.L", "gold", (0.62, 1.62, 0.1), (0.7, 1.4, GRIP_Z), (0.16, 0.17), (0.145, 0.15), sides=6)
    H.frustum("forearm.L", "skin", (0.7, 1.5, GRIP_Z), (GRIP_X - 0.02, 1.26, GRIP_Z), (0.12, 0.13), (0.15, 0.15), sides=6)


def bow():
    z = GRIP_Z
    pts = [(0.57, 2.76, z), (0.68, 2.25, z), (0.79, 1.8, z), (GRIP_X, 1.52, z), (GRIP_X, 1.3, z),
           (0.7, 0.95, z), (0.62, 0.5, z), (0.53, 0.05, z)]
    rad = [(0.025, 0.035), (0.04, 0.05), (0.065, 0.07), (0.07, 0.075), (0.07, 0.075), (0.065, 0.07), (0.05, 0.06), (0.03, 0.04)]
    H.chain("forearm.L", "bow", pts, rad, sides=4)
    H.frustum("forearm.L", "bow_dk", (GRIP_X, 1.58, z), (GRIP_X, 1.24, z), (0.065, 0.075), (0.065, 0.075), sides=6)     # cabo
    H.frustum("forearm.L", "string", (0.57, 2.74, z), (0.53, 0.07, z), (0.012, 0.012), (0.012, 0.012), sides=4)
    # luneta de tres tubos presa ao arco
    H.chain("forearm.L", "gold", [(0.9, 1.0, z), (0.9, 1.3, z), (0.9, 1.6, z), (0.9, 1.88, z)],
            [(0.07, 0.07), (0.05, 0.05), (0.07, 0.07), (0.05, 0.05)], sides=6)
    for y in (1.28, 1.62):
        H.frustum("forearm.L", "gold", (0.9, y - 0.05, z), (0.9, y + 0.05, z), (0.09, 0.09), (0.09, 0.09), sides=6)
    H.frustum("forearm.L", "frame", (0.78, 1.45, z), (0.9, 1.45, z), (0.03, 0.03), (0.03, 0.03), sides=4)


def back_gear():
    z = -0.31
    H.frustum("spine", "quiver", (0.2, 1.35, z), (-0.27, 2.2, z), (0.12, 0.11), (0.13, 0.12), sides=4)       # aljava
    for i, x in enumerate((-0.18, -0.29, -0.4)):
        H.frustum("spine", "arrow", (x, 2.2, z), (x - 0.04, 2.55 + 0.04 * i, z), (0.02, 0.02), (0.075, 0.075), sides=6)
    H.frustum("spine", "bottle", (0.22, 1.62, z - 0.02), (0.22, 1.9, z - 0.02), (0.1, 0.1), (0.075, 0.075), sides=6)
    H.frustum("spine", "bottle", (0.22, 1.9, z - 0.02), (0.22, 2.04, z - 0.02), (0.05, 0.05), (0.04, 0.04), sides=6)
    H.frustum("spine", "cork", (0.22, 2.04, z - 0.02), (0.22, 2.12, z - 0.02), (0.045, 0.045), (0.05, 0.05), sides=6)


def make():
    head()
    torso()
    skirt()
    legs()
    right_arm()
    left_arm()
    bow()
    back_gear()


def joints():
    out = {}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * 0.5, SH_Y, 0), (s * 0.58, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * 0.58, EL_Y, 0), (s * 0.62, WR_Y, 0.06 if s > 0 else 0))
    return out


H.build("n023", "biped", PALETTE, make, joints())
