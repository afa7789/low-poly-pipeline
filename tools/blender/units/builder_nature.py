"""Nature Mushroom Builder (builder_nature): homem-arvore com chapeu de cogumelo, balde na mao direita,
braco esquerdo enrolado em cipo com uma torneira.

    blender -b --factory-startup -P tools/blender/units/builder_nature.py -- <out.glb>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "bark": 0x6B4426, "bark_dk": 0x553520, "bark_lt": 0x805434, "moss": 0x6A8A3E, "moss_dk": 0x557030,
    "cap": 0xA89638, "cap_dk": 0x857528, "glow": 0xEEF59A, "eye": 0x1E140C, "vine": 0xB09A50,
    "brass": 0xC9A23C, "bucket": 0x7C6444, "bucket_dk": 0x5E4A30, "iron": 0x4A4640,
}
HIP, KNEE, ANKLE, NECK, TOP = 1.0, 0.5, 0.15, 1.95, 2.75
LEG_X, SH_X, SH_Y, EL_X, EL_Y, WR_Y = 0.33, 0.62, 1.92, 0.8, 1.3, 0.85


def head():
    H.frustum("head", "bark", (0, 1.9, 0), (0, 2.25, 0), (0.34, 0.3), (0.3, 0.27), sides=8)
    H.frustum("head", "bark_lt", (0, 2.0, 0.2), (0, 2.2, 0.2), (0.2, 0.1), (0.2, 0.1), sides=6)
    for s in (-1, 1):
        H.frustum("head", "eye", (s * 0.13, 2.08, 0.27), (s * 0.13, 2.08, 0.34), (0.05, 0.05), (0.045, 0.045), sides=6)
    H.frustum("head", "glow", (0, 2.2, 0), (0, 2.34, 0), (0.78, 0.76), (0.84, 0.82), sides=8)       # lamelas brilhantes
    H.frustum("head", "cap_dk", (0, 2.34, 0), (0, 2.44, 0), (0.84, 0.82), (0.76, 0.74), sides=8)
    H.frustum("head", "cap", (0, 2.44, 0), (0, 2.62, 0), (0.76, 0.74), (0.56, 0.54), sides=8)
    H.frustum("head", "cap", (0, 2.62, 0), (0, TOP, 0), (0.56, 0.54), (0.24, 0.24), sides=8)


def torso():
    H.frustum("spine", "bark", (0, 1.3, 0), (0, 1.8, 0), (0.46, 0.38), (0.64, 0.42), sides=8)
    H.frustum("spine", "bark", (0, 1.8, 0), (0, 2.0, 0), (0.64, 0.42), (0.4, 0.32), sides=8)
    H.frustum("spine", "bark_lt", (0, 1.45, 0.3), (0, 1.75, 0.34), (0.16, 0.05), (0.2, 0.05), sides=6)
    H.frustum("pelvis", "bark", (0, 0.85, 0), (0, 1.35, 0), (0.58, 0.42), (0.5, 0.38), sides=8)
    for s in (-1, 1):       # musgo nos ombros, tufos empilhados
        H.frustum("spine", "moss", (s * 0.6, 1.8, 0), (s * 0.6, 2.06, 0), (0.3, 0.32), (0.38, 0.34), sides=8)
        H.frustum("spine", "moss_dk", (s * 0.6, 2.06, 0), (s * 0.58, 2.2, 0), (0.34, 0.32), (0.2, 0.2), sides=8)


def leg(s, side):
    x = s * LEG_X
    H.frustum(f"thigh.{side}", "bark", (x * 1.1, KNEE - 0.05, 0), (x, HIP + 0.05, 0), (0.34, 0.34), (0.4, 0.38), sides=6)
    H.frustum(f"shin.{side}", "bark", (x * 1.1, ANKLE + 0.05, 0), (x * 1.1, KNEE + 0.05, 0), (0.34, 0.32), (0.34, 0.34), sides=6)
    H.frustum(f"foot.{side}", "bark_dk", (x * 1.1, 0.02, 0), (x * 1.1, 0.24, 0), (0.5, 0.46), (0.33, 0.31), sides=8)   # base de raiz
    for dx, dz in ((-0.34, 0.1), (0.3, 0.2), (0, 0.46)):       # raizes abertas
        H.frustum(f"foot.{side}", "bark_dk", (x * 1.1, 0.1, 0), (x * 1.1 + dx, 0.05, dz + 0.1), (0.13, 0.1), (0.07, 0.04), sides=4)


def arm_bucket():
    H.frustum("arm.R", "bark", (-SH_X, SH_Y + 0.05, 0), (-EL_X, EL_Y - 0.05, 0), (0.28, 0.28), (0.24, 0.24), sides=6)
    H.frustum("forearm.R", "bark", (-EL_X, EL_Y + 0.05, 0), (-EL_X, WR_Y + 0.1, 0.05), (0.24, 0.24), (0.22, 0.22), sides=6)
    H.frustum("forearm.R", "bark_lt", (-EL_X, WR_Y + 0.12, 0.05), (-EL_X, WR_Y - 0.1, 0.05), (0.2, 0.2), (0.17, 0.17), sides=6)   # mao
    H.frustum("forearm.R", "bucket", (-EL_X, 0.28, 0.05), (-EL_X, 0.74, 0.05), (0.22, 0.22), (0.3, 0.3), sides=8)
    H.frustum("forearm.R", "bucket_dk", (-EL_X, 0.28, 0.05), (-EL_X, 0.3, 0.05), (0.22, 0.22), (0.22, 0.22), sides=8)
    H.chain("forearm.R", "iron", [(-EL_X - 0.28, 0.72, 0.05), (-EL_X - 0.12, 0.98, 0.05), (-EL_X + 0.12, 0.98, 0.05), (-EL_X + 0.28, 0.72, 0.05)],
            [(0.03, 0.03)] * 4, sides=4)


def arm_vine():
    H.frustum("arm.L", "bark", (SH_X, SH_Y + 0.05, 0), (EL_X, EL_Y - 0.05, 0), (0.28, 0.28), (0.25, 0.25), sides=6)
    H.frustum("forearm.L", "bark", (EL_X, EL_Y + 0.05, 0), (EL_X, WR_Y + 0.1, 0.05), (0.25, 0.25), (0.22, 0.22), sides=6)
    H.frustum("forearm.L", "bark_lt", (EL_X, WR_Y + 0.12, 0.05), (EL_X, WR_Y - 0.12, 0.05), (0.2, 0.2), (0.17, 0.17), sides=6)
    for y in (1.0, 1.14, 1.28):         # voltas do cipo no antebraco
        H.frustum("forearm.L", "vine", (EL_X, y, 0.0), (EL_X, y + 0.07, 0.0), (0.27, 0.27), (0.27, 0.27), sides=8)
    for y in (1.46, 1.62, 1.78):
        H.frustum("arm.L", "vine", (SH_X + 0.1 + (1.9 - y) * 0.2, y, 0), (SH_X + 0.1 + (1.9 - y) * 0.2, y + 0.07, 0), (0.3, 0.3), (0.3, 0.3), sides=8)
    H.frustum("forearm.L", "brass", (EL_X + 0.2, 1.1, 0), (EL_X + 0.5, 1.1, 0), (0.07, 0.07), (0.06, 0.06), sides=6)  # bico da torneira
    H.frustum("forearm.L", "brass", (EL_X + 0.45, 1.1, 0), (EL_X + 0.5, 1.2, 0), (0.07, 0.07), (0.07, 0.07), sides=6)
    H.frustum("forearm.L", "brass", (EL_X + 0.36, 1.19, 0), (EL_X + 0.52, 1.21, 0), (0.06, 0.03), (0.07, 0.03), sides=4)


def make():
    head()
    torso()
    for s, side in ((1, "L"), (-1, "R")):
        leg(s, side)
    arm_bucket()
    arm_vine()


def joints():
    out = {"pelvis": ((0, HIP, 0), (0, 1.35, 0)), "spine": ((0, 1.35, 0), (0, NECK, 0)), "head": ((0, NECK, 0), (0, TOP, 0))}
    for s, side in ((1, "L"), (-1, "R")):
        out[f"arm.{side}"] = ((s * SH_X, SH_Y, 0), (s * EL_X, EL_Y, 0))
        out[f"forearm.{side}"] = ((s * EL_X, EL_Y, 0), (s * EL_X, WR_Y, 0.05))
        out[f"thigh.{side}"] = ((s * LEG_X, HIP, 0), (s * LEG_X * 1.1, KNEE, 0))
        out[f"shin.{side}"] = ((s * LEG_X * 1.1, KNEE, 0), (s * LEG_X * 1.1, ANKLE, 0))
        out[f"foot.{side}"] = ((s * LEG_X * 1.1, ANKLE, 0), (s * LEG_X * 1.1, 0.06, 0.5))
    return out


H.build("builder_nature", "biped", PALETTE, make, joints())
