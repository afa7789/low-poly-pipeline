"""Geometry of one spec part in the build's Blender axes (x right, y = -forward, z up), numpy only.

Moved out of fit_spec.py so that Blender's Python (numpy, no scipy / PIL) can import it: sdf_body.py needs the same
points the fit projects. fit_spec re-exports every name, so `fit_spec.part_points` & co. keep working.
"""
import math

import numpy as np

import lathe_limb
import preflight

SIDES = 12              # polygon count of a round part's outline
D = math.radians


def spec_to_blender(p):
    """Spec (right, up, forward) -> Blender (x, y, z), as build_unit.bp."""
    return np.array([p[0], -p[2], p[1]], float)


def euler_matrix(ex, ey, ez):
    """Blender XYZ euler (radians): X is applied first, Z last."""
    (sx, cx), (sy, cy), (sz, cz) = ((math.sin(a), math.cos(a)) for a in (ex, ey, ez))
    return (np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
            @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
            @ np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]))


def box_corners(size):
    return np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]) * (np.asarray(size) / 2)


def ring_points(r0, r1, height, n=SIDES):
    """Two n-gons, radius r0 at z = -height/2 and r1 at +height/2."""
    a = np.arange(n) * 2 * math.pi / n
    return np.concatenate([np.stack([r0 * np.cos(a), r0 * np.sin(a), np.full(n, -height / 2)], 1),
                           np.stack([r1 * np.cos(a), r1 * np.sin(a), np.full(n, height / 2)], 1)])


def frustum_points(dims, top, shift, sides=4):
    w, h, d = dims
    sx, sz = top
    dx, dz = shift
    if sides > 4:                   # a rounded frustum: an n-gon inscribed in the w x d box
        a = np.arange(sides) * 2 * math.pi / sides
        lo = np.stack([w / 2 * np.cos(a), d / 2 * np.sin(a), np.full(sides, -h / 2)], 1)
        return np.concatenate([lo, lo * [sx, sz, 1] + [dx, dz, h]])
    lo = [(-w / 2, -d / 2, -h / 2), (w / 2, -d / 2, -h / 2), (w / 2, d / 2, -h / 2), (-w / 2, d / 2, -h / 2)]
    hi = [(-w / 2 * sx + dx, -d / 2 * sz + dz, h / 2), (w / 2 * sx + dx, -d / 2 * sz + dz, h / 2),
          (w / 2 * sx + dx, d / 2 * sz + dz, h / 2), (-w / 2 * sx + dx, d / 2 * sz + dz, h / 2)]
    return np.array(lo + hi)


def spec_rot(opts):
    """opts["rot"] as (right, up, forward) degrees: a bare number turns around forward."""
    return preflight.rot_euler(opts)


def disc_base(axis):
    """Rotation of a disc whose normal is local Z, for the build's axis names."""
    return euler_matrix(D(90), 0, 0) if axis == "fwd" else euler_matrix(0, D(90), 0) if axis == "side" else np.eye(3)


def track_z(d):
    """Rotation that points local +Z along d with local +Y towards world +Z (to_track_quat('Z','Y'))."""
    z = d / np.linalg.norm(d)
    up = np.array([0.0, 0.0, 1.0]) - z[2] * z
    y = up / np.linalg.norm(up) if np.linalg.norm(up) > 1e-6 else np.array([0.0, 1.0, 0.0])
    return np.stack([np.cross(y, z), y, z], 1)


def fitted_dims(kind, dims, a, b):
    """build_unit.fit_length: a from/to part is as long as its two joints are apart, plus 8 %."""
    length = float(np.linalg.norm(np.asarray(b) - np.asarray(a))) * 1.08
    if kind == "prism":
        return (dims[0], dims[1], length)
    if kind == "cyl":
        return (dims[0], length)
    return (dims[0], length, dims[2]) if kind in ("box", "frustum") else dims


def local_shape(kind, dims, opts):
    """(points, rotation matrix) of one part in its own frame, as build_part makes it."""
    rx, ry, rz = (D(v) for v in spec_rot(opts))
    euler = euler_matrix(rx, -rz, ry)
    if kind in ("prism", "dome"):
        if kind == "dome":
            dims = (dims[0], dims[0] * float(opts.get("top", 0.35)), dims[1])
        base = {"fwd": (D(90), 0, 0), "side": (0, D(90), 0)}.get(opts.get("axis", "up"), (0, 0, 0))
        pts = ring_points(dims[0], dims[1], dims[2], int(opts.get("sides", 8)))
        return scaled(pts, opts), euler_matrix(base[0] + rx, base[1] - rz, base[2] + ry + D(float(opts.get("spin", 0))))
    if kind == "frustum":
        pts = frustum_points(dims, opts.get("top", (1.0, 1.0)), opts.get("shift", (0.0, 0.0)), int(opts.get("sides", 4)))
        return scaled(pts, opts), euler_matrix(rx, -rz, ry + D(float(opts.get("spin", 0))))
    if kind == "cyl":
        up = opts.get("axis", "fwd") == "up"
        return ring_points(dims[0], dims[0], dims[1], int(opts.get("sides", 8))), np.eye(3) if up else euler_matrix(D(90), 0, 0)
    if kind in ("wheel", "ring"):
        radius, half = (dims[0] + dims[1], dims[1]) if kind == "wheel" else (dims[0], dims[2] / 2)
        tilt = euler_matrix(D(float(opts.get("tilt", 0.0))), 0, 0)
        spin = euler_matrix(0, 0, D(float(opts.get("spin", 0.0)))) if kind == "ring" else np.eye(3)
        return ring_points(radius, radius, 2 * half), disc_base(opts.get("axis", "fwd" if kind == "wheel" else "up")) @ tilt @ spin
    return box_corners((dims[0], dims[2], dims[1])), euler        # box: bd(dims), and the unknown kinds


def scaled(pts, opts):
    sx, sy = (opts["scale"][0], opts["scale"][1]) if opts.get("scale") else (1.0, 1.0)
    return pts * np.array([sx, sy, 1.0])


def placed(part):
    """(local points, rotation, centre, dims) of a box, prism, frustum, cyl, dome, wheel or ring part: the
    world points are `pts @ rot.T + centre` (dims after the from/to fit)."""
    _, kind, dims, at, _, opts = part
    opts = opts or {}
    span = "from" in opts and "to" in opts
    if span:
        a, b = tuple(opts["from"]), tuple(opts["to"])
        at = tuple((a[i] + b[i]) / 2 for i in range(3))
        if opts.get("fit", True):
            dims = fitted_dims(kind, dims, a, b)
    pts, rot = local_shape(kind, dims, opts)
    if span and kind != "ring":
        d = spec_to_blender(b) - spec_to_blender(a)
        rot = track_z(d) if np.linalg.norm(d) > 1e-6 else rot
    return pts, rot, spec_to_blender(at), dims


def rings_of(part, sheet=None):
    """[ring] of a lathe, limb, chain or plate part, each an (n, 3) array in Blender axes (plate: placed by at and rot).
    `sheet` is the profile / radii read from the sheet (the cuts json), used when the opts have none."""
    bone, kind, dims, at, _, opts = part
    opts = opts or {}
    if kind == "plate":
        rx, ry, rz = (D(v) for v in spec_rot(opts))
        rot = euler_matrix(rx, -rz, ry)
        return [np.array([spec_to_blender(p) for p in ring]) @ rot.T + spec_to_blender(at)
                for ring in lathe_limb.plate_rings(dims, (0, 0, 0), opts, sheet)]
    rings = {"lathe": lambda: lathe_limb.lathe_rings(dims, at, opts, sheet),
             "chain": lambda: lathe_limb.chain_rings(bone, dims, opts, sheet)}.get(kind, lambda: lathe_limb.limb_rings(dims, opts))()
    return [np.array(ring, float)[:, [0, 2, 1]] * [1, -1, 1] for ring in rings]


def part_points(part, sheet=None):
    """World points (Blender axes) whose convex hull is the part's outline."""
    if part[1] in ("lathe", "limb", "chain", "plate"):
        return np.concatenate(rings_of(part, sheet))
    pts, rot, centre, _ = placed(part)
    return pts @ rot.T + centre
