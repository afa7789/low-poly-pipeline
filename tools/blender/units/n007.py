"""Dragon Turtle (n007), quadruped: measured on artifacts/model-sheets/refs/n007/sheet.jpg.

    blender -b --factory-startup -P tools/blender/units/n007.py -- <out.glb>

Scale read off the profile: 330 px per metre, nose at z=+1.0, ground at y=0. The shell rides on spine.1,
the neck on spine.2, the snapping head on its own bone.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import hand_unit as H  # noqa: E402

PALETTE = {
    "red": 0x8C2A20, "red_dk": 0x6E1F1A, "shell": 0x2E0F18, "spike": 0x45161F, "cream": 0xEBD5A8,
    "olive": 0x7B7B50, "orange": 0xF08A28, "mouth": 0x3A0F12,
}

SHELL_Z = -0.33   # centro do casco

# juntas (metros): (x, y, z) do ombro/quadril, cotovelo/joelho e pulso/tornozelo
FRONT = ((0.5, 0.55, 0.2), (0.6, 0.3, 0.25), (0.57, 0.1, 0.32))
HIND = ((0.5, 0.55, -0.62), (0.6, 0.3, -0.58), (0.56, 0.1, -0.65))
LEGS = ((1, FRONT, 1, 0.52), (-1, FRONT, 2, 0.52), (1, HIND, 3, -0.45), (-1, HIND, 4, -0.45))   # lado, perna, numero, ponta dos dedos


def mir(p, s):
    return (s * p[0], p[1], p[2])


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def spike(bone, p, q, base, tone="spike", tip=0.6):
    """A shell spike from p to q: dark base, cream tip."""
    mid = lerp(p, q, tip)
    H.frustum(bone, tone, p, mid, (base, base * 1.2), (base * 0.5, base * 0.6), sides=4)
    H.frustum(bone, "cream", mid, q, (base * 0.5, base * 0.6), (0.006, 0.006), sides=4)


def shell():
    z = SHELL_Z
    H.frustum("spine.1", "cream", (0, 0.5, z), (0, 0.7, z), (0.66, 0.76), (0.6, 0.7))               # borda clara
    H.frustum("spine.1", "shell", (0, 0.66, z), (0, 0.98, z + 0.03), (0.6, 0.7), (0.42, 0.5))       # cupula
    H.frustum("spine.1", "shell", (0, 0.96, z + 0.03), (0, 1.16, z + 0.05), (0.42, 0.5), (0.2, 0.28))
    H.frustum("spine.1", "red_dk", (0, 0.4, z), (0, 0.6, z), (0.45, 0.55), (0.5, 0.6))             # pele sob o casco
    H.frustum("spine.1", "olive", (0, 0.25, z + 0.02), (0, 0.5, z + 0.02), (0.5, 0.62), (0.56, 0.66), sides=8)   # plastrao


def shell_spikes():
    for y, zz, top, lean in ((1.1, 0.03, 1.28, 0.1), (1.14, -0.26, 1.34, 0.12), (1.0, -0.62, 1.2, 0.1), (0.8, -0.9, 0.94, 0.08)):
        spike("spine.1", (0, y - 0.1, zz), (0, top, zz - lean), 0.08)
    for s in (-1, 1):
        for y, zz, dx in ((0.95, 0.0, 0.5), (0.85, -0.55, 0.55)):
            spike("spine.1", (s * (dx - 0.1), y - 0.05, zz), (s * (dx + 0.12), y + 0.28, zz - 0.08), 0.06)
        spike("spine.1", (s * 0.2, 1.0, 0.05), (s * 0.34, 1.28, -0.02), 0.06)


def head():
    H.frustum("head", "red", (0, 0.72, 0.42), (0, 0.68, 1.0), (0.24, 0.19), (0.12, 0.1))
    H.frustum("head", "red", (0, 0.74, 0.5), (0, 0.72, 0.82), (0.22, 0.2), (0.17, 0.15))
    H.frustum("head", "mouth", (0, 0.55, 0.5), (0, 0.57, 0.95), (0.18, 0.05), (0.1, 0.04), sides=6)
    H.frustum("head", "red_dk", (0, 0.52, 0.48), (0, 0.54, 0.9), (0.16, 0.05), (0.09, 0.04), sides=6)
    for s in (-1, 1):
        H.frustum("head", "orange", (s * 0.12, 0.8, 0.7), (s * 0.2, 0.8, 0.66), (0.035, 0.03), (0.04, 0.035), sides=6)
        H.frustum("head", "red_dk", (s * 0.1, 0.86, 0.72), (s * 0.2, 0.85, 0.64), (0.04, 0.03), (0.04, 0.03), sides=4)   # sobrancelha
        for zz in (0.62, 0.78, 0.9):
            H.frustum("head", "cream", (s * 0.1, 0.58, zz), (s * 0.1, 0.5, zz + 0.02), (0.025, 0.025), (0.006, 0.006), sides=4)


def neck_tail():
    H.frustum("spine.2", "red", (0, 0.5, 0.0), (0, 0.66, 0.3), (0.3, 0.3), (0.24, 0.24))
    H.frustum("spine.2", "red", (0, 0.62, 0.22), (0, 0.72, 0.46), (0.25, 0.22), (0.2, 0.2))
    H.frustum("spine.2", "olive", (0, 0.32, 0.0), (0, 0.4, 0.4), (0.3, 0.1), (0.2, 0.08), sides=6)     # papo verde do peito
    H.frustum("tail.1", "red", (0, 0.45, -0.85), (0, 0.42, -1.06), (0.18, 0.15), (0.1, 0.09))
    H.frustum("tail.2", "red", (0, 0.42, -1.06), (0, 0.34, -1.28), (0.1, 0.09), (0.012, 0.012))


def paw(bone, s, p, toe_z):
    x, _, z = p
    H.frustum(bone, "red", (s * x, 0.17, z - 0.02), (s * x, 0.04, z + 0.08), (0.17, 0.15), (0.21, 0.13), sides=6)
    for k in (-1.5, -0.5, 0.5, 1.5):     # 4 garras claras
        base = (s * (x + k * 0.07), 0.06, z + 0.12)
        H.frustum(bone, "cream", base, (s * (x + k * 0.09), 0.03, toe_z), (0.035, 0.03), (0.006, 0.006), sides=4)


def leg(s, geo, n, toe_z):
    hip, knee, ank = (mir(p, s) for p in geo)
    up, lo = f"leg{n}.upper", f"leg{n}.lower"
    H.chain(up, "red", [(hip[0], hip[1] + 0.1, hip[2]), lerp(hip, knee, 0.4), knee], [(0.2, 0.2), (0.25, 0.24), (0.15, 0.15)])
    H.chain(lo, "red_dk", [knee, lerp(knee, ank, 0.45), (ank[0], 0.15, ank[2])], [(0.15, 0.15), (0.12, 0.12), (0.16, 0.15)])
    paw(lo, s, geo[2], toe_z)


def make():
    shell()
    shell_spikes()
    neck_tail()
    head()
    for args in LEGS:
        leg(*args)


def joints():
    out = {
        "spine.1": ((0, 0.6, -0.85), (0, 0.62, -0.3)), "spine.2": ((0, 0.62, -0.3), (0, 0.62, 0.3)),
        "head": ((0, 0.62, 0.3), (0, 0.7, 1.0)),
        "tail.1": ((0, 0.45, -0.85), (0, 0.42, -1.06)), "tail.2": ((0, 0.42, -1.06), (0, 0.34, -1.28)),
    }
    for s, geo, n, _ in LEGS:
        hip, knee, ank = (mir(p, s) for p in geo)
        out[f"leg{n}.upper"] = (hip, knee)
        out[f"leg{n}.lower"] = (knee, ank)
    return out


H.build("n007", "quadruped", PALETTE, make, joints())
