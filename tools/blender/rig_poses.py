"""Joint positions of a rig family in a pose, without Blender: the storyboard's maths.

A pose is the clip format the builder keys ({bone: (rx, ry, rz, lift[, up])}, degrees
and metres, see rig_families). Blender applies it on each pose bone in the bone's own
rest frame: rotation_euler XYZ, then location (0, up, lift). Mind the root: it points
up, so its local Z is the spec FORWARD axis - `lift` on the root slides the body
forward/back, and only the optional `up` (along the bone) raises it. This module repeats that
forward kinematics on the family tables so a drawing of the pose is exactly the
keyframe the builder will write (checked against Blender in tests/tools/blender).

Coordinates come back in Blender axes (x right, y back, z up), like build_unit.bp.
"""
import functools
import math

import rig_families as RF


def bp(p):
    """Spec (right, up, forward) -> Blender (x, y, z), the same as build_unit.bp."""
    return (p[0], -p[2], p[1])


# ---------------------------------------------------------------- 4x4 maths
def _mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def _apply(m, v):
    return tuple(m[i][0] * v[0] + m[i][1] * v[1] + m[i][2] * v[2] + m[i][3] for i in range(3))


def _affine_inverse(m):
    """Inverse of a 4x4 affine matrix. Not a transpose: near -Y Blender's bone frame is
    an approximation and slightly off orthonormal, so the true inverse is needed."""
    a = [row[:3] for row in m[:3]]
    cof = [[a[(i + 1) % 3][(j + 1) % 3] * a[(i + 2) % 3][(j + 2) % 3]
            - a[(i + 1) % 3][(j + 2) % 3] * a[(i + 2) % 3][(j + 1) % 3] for j in range(3)] for i in range(3)]
    det = sum(a[0][j] * cof[0][j] for j in range(3))
    inv = [[cof[j][i] / det for j in range(3)] for i in range(3)]
    t = [-sum(inv[i][k] * m[k][3] for k in range(3)) for i in range(3)]
    return [inv[0] + [t[0]], inv[1] + [t[1]], inv[2] + [t[2]], [0, 0, 0, 1]]


def _frame(axes, origin):
    """4x4 from three column axes and an origin."""
    return [[axes[0][i], axes[1][i], axes[2][i], origin[i]] for i in range(3)] + [[0, 0, 0, 1]]


def bone_axes(direction):
    """Blender's rest frame of a bone with roll 0 (vec_roll_to_mat3_normalized):
    the local Y runs along the bone, X and Z follow the shortest turn from +Y."""
    n = math.sqrt(sum(c * c for c in direction))
    x, y, z = (c / n for c in direction)
    theta, alt = 1.0 + y, x * x + z * z
    if theta <= 6.1e-3 and alt <= 2.5e-4 ** 2:       # straight down -Y: Blender flips X and Y
        return (-1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, 1.0)
    if theta <= 6.1e-3:
        theta = alt * 0.5 + alt * alt * 0.125
    return ((1 - x * x / theta, -x, -x * z / theta), (x, y, z),
            (-x * z / theta, -z, 1 - z * z / theta))


def _basis(rx, ry, rz, lift, up=0.0):
    """matrix_basis of a pose bone: T(0, up, lift) @ Rz @ Ry @ Rx (Euler XYZ)."""
    a, b, c = (math.radians(v) for v in (rx, ry, rz))
    ca, sa, cb, sb, cc, sc = math.cos(a), math.sin(a), math.cos(b), math.sin(b), math.cos(c), math.sin(c)
    return [[cc * cb, cc * sb * sa - sc * ca, cc * sb * ca + sc * sa, 0.0],
            [sc * cb, sc * sb * sa + cc * ca, sc * sb * ca - cc * sa, up],
            [-sb, cb * sa, cb * ca, lift],
            [0.0, 0.0, 0.0, 1.0]]


# ---------------------------------------------------------------- forward kinematics
def rest(family, extras=None):
    """bone -> (parent, rest matrix in armature space, length), in table order (cached for
    the plain family tables; read-only)."""
    return _rest(family) if not extras else _build_rest(family, extras)


@functools.lru_cache(maxsize=None)
def _rest(family):
    return _build_rest(family, None)


def _build_rest(family, extras):
    out = {}
    for name, parent, head, tail in RF.with_extras(family, extras):
        h, t = bp(head), bp(tail)
        d = tuple(t[i] - h[i] for i in range(3))
        out[name] = (parent, _frame(bone_axes(d), h), math.sqrt(sum(c * c for c in d)))
    return out


def _posed(family, pose, extras):
    """bone -> 4x4 pose matrix in armature space."""
    pose, table = pose or {}, rest(family, extras)
    world = {}
    for name, (parent, local, _) in table.items():
        offset = local
        if parent is not None:      # pose.matrix = parent.matrix @ parent.rest^-1 @ rest @ basis
            offset = _mul(world[parent], _mul(_affine_inverse(table[parent][1]), local))
        world[name] = _mul(offset, _basis(*pose.get(name, (0, 0, 0, 0))))
    return world


def joints(family, pose=None, extras=None):
    """bone -> (head, tail) in armature space for `pose` ({bone: (rx, ry, rz, lift)})."""
    table = rest(family, extras)
    return {name: (_apply(m, (0, 0, 0)), _apply(m, (0, table[name][2], 0)))
            for name, m in _posed(family, pose, extras).items()}


def frames(family, pose=None, extras=None):
    """bone -> 3x3 orientation in armature space for `pose` (columns: the bone's x, y, z), twist
    included: what aiming a bone along (head, tail) loses."""
    return {name: [row[:3] for row in m[:3]] for name, m in _posed(family, pose, extras).items()}


# ---------------------------------------------------------------- sampling clips
def _ease(t):
    return t * t * (3 - 2 * t)


def sample(poses, frame):
    """The pose at `frame` between the clip's keys, eased per channel (bones a key
    leaves out are at rest there)."""
    keys = sorted(poses)
    if frame <= keys[0]:
        return dict(poses[keys[0]])
    if frame >= keys[-1]:
        return dict(poses[keys[-1]])
    a = max(k for k in keys if k <= frame)
    b = min(k for k in keys if k >= frame)
    if a == b:
        return dict(poses[a])
    t = _ease((frame - a) / (b - a))
    zero = (0, 0, 0, 0, 0)
    bones = set(poses[a]) | set(poses[b])
    return {n: tuple(p + (q - p) * t for p, q in zip(pad(poses[a].get(n, zero)), pad(poses[b].get(n, zero))))
            for n in bones}


def pad(value):
    return tuple(value) + (0.0,) * (5 - len(value))


def strip(poses, count=10):
    """`count` poses evenly spaced from the clip's first key to its last."""
    keys = sorted(poses)
    lo, hi = keys[0], keys[-1]
    return [sample(poses, lo + (hi - lo) * i / (count - 1)) for i in range(count)]


# ---------------------------------------------------------------- aiming (retarget)
def _euler_xyz(r):
    """Blender Euler XYZ (R = Rz @ Ry @ Rx) of a 3x3 rotation, in degrees."""
    ry = math.asin(max(-1.0, min(1.0, -r[2][0])))
    if abs(r[2][0]) < 0.9999:
        rx, rz = math.atan2(r[2][1], r[2][2]), math.atan2(r[1][0], r[0][0])
    else:                                   # gimbal lock: fold x into z
        rx, rz = 0.0, math.atan2(-r[0][1], r[1][1])
    return tuple(math.degrees(v) for v in (rx, ry, rz))


def _turn_y_to(v):
    """Shortest-arc rotation taking +Y onto the unit vector v (no twist)."""
    x, y, z = v
    if y < -0.999999:
        return [[-1, 0, 0], [0, -1, 0], [0, 0, 1]]
    k = 1.0 / (1.0 + y)
    # Rodrigues with axis (z, 0, -x) and cos = y, written out
    return [[y + z * z * k, x, -x * z * k],
            [-x, y, -z],
            [-x * z * k, z, y + x * x * k]]


def aim(family, directions, root=(0.0, 0.0), extras=None):
    """Pose that points each bone in `directions` ({bone: world vector}) that way,
    twist-free; other bones stay at rest. `root` = (lift, up) in metres."""
    table = rest(family, extras)
    world, pose = {}, {}
    for name, (parent, local, _) in table.items():
        offset = local
        if parent is not None:
            offset = _mul(world[parent], _mul(_affine_inverse(table[parent][1]), local))
        value = (0.0, 0.0, 0.0, root[0], root[1]) if parent is None else (0.0, 0.0, 0.0, 0.0, 0.0)
        target = directions.get(name)
        if target is not None:
            inv = _affine_inverse(offset)
            d = [sum(inv[i][k] * target[k] for k in range(3)) for i in range(3)]
            n = math.sqrt(sum(c * c for c in d)) or 1.0
            value = (*_euler_xyz(_turn_y_to([c / n for c in d])), value[3], value[4])
        pose[name] = value
        world[name] = _mul(offset, _basis(*value))
    return pose


def turn(u, v, x, gain=1.0):
    """Rotate x by the shortest arc that takes direction u onto direction v, the angle
    scaled by `gain` (2 = turn twice as far, for a reference that moves too little)."""
    def unit(w):
        n = math.sqrt(sum(c * c for c in w)) or 1.0
        return [c / n for c in w]
    u, v = unit(u), unit(v)
    k = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
    sin = math.sqrt(sum(a * a for a in k))
    if sin < 1e-9:
        return list(x) if sum(a * b for a, b in zip(u, v)) > 0 else [-a for a in x]
    axis = [a / sin for a in k]
    angle = math.atan2(sin, sum(a * b for a, b in zip(u, v))) * gain
    c, s = math.cos(angle), math.sin(angle)
    ax = [axis[1] * x[2] - axis[2] * x[1], axis[2] * x[0] - axis[0] * x[2], axis[0] * x[1] - axis[1] * x[0]]
    adx = sum(a * b for a, b in zip(axis, x))
    return [x[i] * c + ax[i] * s + axis[i] * adx * (1 - c) for i in range(3)]


def two_bone(hip, target, a, b, bend):
    """Knee and end of a two-bone limb of lengths a, b reaching from `hip` toward
    `target`, the knee pushed along `bend` (a direction). Out of reach: straightens."""
    d = [target[i] - hip[i] for i in range(3)]
    dist = max(min(math.sqrt(sum(c * c for c in d)), a + b - 1e-6), abs(a - b) + 1e-6)
    u = [c / (math.sqrt(sum(x * x for x in d)) or 1.0) for c in d]
    w = [bend[i] - sum(bend[j] * u[j] for j in range(3)) * u[i] for i in range(3)]
    n = math.sqrt(sum(c * c for c in w)) or 1.0
    w = [c / n for c in w]
    cos_hip = (a * a + dist * dist - b * b) / (2 * a * dist)
    sin_hip = math.sqrt(max(0.0, 1 - cos_hip * cos_hip))
    knee = [hip[i] + a * (cos_hip * u[i] + sin_hip * w[i]) for i in range(3)]
    end = [hip[i] + dist * u[i] for i in range(3)]
    return knee, end
