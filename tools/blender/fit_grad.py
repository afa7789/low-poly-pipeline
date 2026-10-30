"""fit_spec by gradient (PIPELINE 26.L8-7): the proxy of fit_spec in torch, Adam instead of Powell.

    python3.14 tools/blender/fit_spec.py <spec> <sheet> <out> --fit-grad

The same parameters as Powell (fit_spec.apply: unit values in [-1, 1] per dim, `at`, rot, profile, knee, one vector per
left/right pair so the symmetry holds by construction) go through a torch twin of `moved` + `part_points`; every part's
convex outline per view is fan-triangulated (the hull's vertex list is combinatorial, taken from the detached points; the
vertices stay differentiable) and the soft masks (soft_sil.soft_mask, SoftRas Eq. 4: the union comes out of the
aggregation) give the loss of Proxy.loss: weighted views, body against the body mask and props against theirs, 1 - IoU
(the better of the mirrors) + chamfer. Adam with tau annealed 4 px -> 0.5 px; bounds by projection (the start x = 0 sits on
the edge of a (-1, 0) no-grow interval, where a sigmoid has no gradient). The soft loss only proposes: every CHECK steps the
point goes through fit_spec.Objective (hard raster, preflight rules, loose parts, depth, zones): a break reverts to the last
good point with half the step; the best exact point is what fit_spec keeps, and spec_pipeline.fit_accepted still judges.
"""
import math
import pathlib
import sys
import time
import types

import numpy as np
import torch
from scipy.spatial import ConvexHull, QhullError

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fit_spec as F  # noqa: E402
import lathe_limb as L  # noqa: E402
import preflight  # noqa: E402
import silhouette  # noqa: E402
import soft_sil  # noqa: E402

DT = torch.float32
TAUS = (4.0, 2.0, 1.0, 0.7, 0.5)    # px of the edge band, annealed
STEPS = 12                          # Adam steps per tau (60 in all: 100 gave the same loss within 0.005 in 1.6x the time)
LR = 0.08                           # step in unit parameters (1 = DIMS_RANGE of a dim)
GROUND_W = 20.0                     # hinge on the preflight `ground` rule (no part under y = 0), per H below it
LINK_W = 20.0                       # hinge on the preflight `overlap` rule (a part touches its bone's or its parent's parts), per H apart
SLACK = 0.1                         # a checked point may cost this much more than the best exact one and still be the base of the next steps
FEET_W = 20.0                       # hinge on the preflight `feet_mass` / `boot_height` rules (boot height and length bands), per H outside
FEET_IN = 0.03                      # ... stay this share inside the band
SYM_W = 50.0                        # hinge on the preflight `symmetry` rule for twins that do not share a parameter group
SYM_TOL = 0.04                      # relative dims gap (the rule allows 5 %) ...
SYM_ROT = 4.0                       # ... and rot gap in degrees (the rule allows 5) that costs nothing
CHECK = 6                         # steps between two exact checks (rules, hard loss)
SUPPORTED = ("box", "prism", "frustum", "cyl", "dome", "ring", "wheel", "lathe", "limb", "chain", "plate")
RAD = math.pi / 180


def T(v):
    return torch.as_tensor(v, dtype=DT)


def vec(vals):
    return torch.stack([T(v) for v in vals])


def to_blender(p):
    """Spec (right, up, forward) -> Blender, as fit_spec.spec_to_blender; p [..., 3]."""
    return torch.stack([p[..., 0], -p[..., 2], p[..., 1]], -1)


def euler_t(ex, ey, ez):
    """fit_spec.euler_matrix on radians (floats or 0-d tensors)."""
    (sx, cx), (sy, cy), (sz, cz) = ((torch.sin(T(a)), torch.cos(T(a))) for a in (ex, ey, ez))
    o, z = T(1.0), T(0.0)
    rz = torch.stack([cz, -sz, z, sz, cz, z, z, z, o]).reshape(3, 3)
    ry = torch.stack([cy, z, sy, z, o, z, -sy, z, cy]).reshape(3, 3)
    rx = torch.stack([o, z, z, z, cx, -sx, z, sx, cx]).reshape(3, 3)
    return rz @ ry @ rx


def ring_t(r0, r1, h, n=F.SIDES):
    """fit_spec.ring_points: n-gons of radius r0 at z = -h/2 and r1 at +h/2."""
    a = T(np.arange(n) * 2 * math.pi / n)
    z = (h / 2).expand(n)
    return torch.cat([torch.stack([r0 * torch.cos(a), r0 * torch.sin(a), -z], 1),
                      torch.stack([r1 * torch.cos(a), r1 * torch.sin(a), z], 1)])


def frustum_t(dims, top, shift, sides):
    w, h, d = dims
    if sides > 4:
        a = np.arange(sides) * 2 * math.pi / sides
        ux, uz = np.cos(a), np.sin(a)
    else:
        ux, uz = np.array([-1.0, 1, 1, -1]), np.array([-1.0, -1, 1, 1])
    ux, uz = T(ux), T(uz)
    lo = torch.stack([ux * w / 2, uz * d / 2, (-h / 2).expand(len(ux))], 1)
    hi = torch.stack([ux * w / 2 * top[0] + shift[0], uz * d / 2 * top[1] + shift[1], (h / 2).expand(len(ux))], 1)
    return torch.cat([lo, hi])


def scaled_t(pts, opts):
    sx, sy = (opts["scale"][0], opts["scale"][1]) if opts.get("scale") else (1.0, 1.0)
    return pts * T([sx, sy, 1.0])


def local_t(kind, dims, opts, rot):
    """fit_spec.local_shape in torch: (points, rotation matrix) of a part in its frame. rot: degrees (right, up, forward)."""
    rx, ry, rz = (T(v) * RAD for v in rot)
    spin = RAD * float(opts.get("spin", 0))
    if kind in ("prism", "dome"):
        if kind == "dome":
            dims = (dims[0], dims[0] * float(opts.get("top", 0.35)), dims[1])
        base = {"fwd": (math.pi / 2, 0, 0), "side": (0, math.pi / 2, 0)}.get(opts.get("axis", "up"), (0, 0, 0))
        pts = ring_t(dims[0], dims[1], dims[2], int(opts.get("sides", 8)))
        return scaled_t(pts, opts), euler_t(base[0] + rx, base[1] - rz, base[2] + ry + spin)
    if kind == "frustum":
        pts = frustum_t(dims, opts.get("top", (1.0, 1.0)), opts.get("shift", (0.0, 0.0)), int(opts.get("sides", 4)))
        return scaled_t(pts, opts), euler_t(rx, -rz, ry + spin)
    if kind == "cyl":
        pts = ring_t(dims[0], dims[0], dims[1], int(opts.get("sides", 8)))
        return pts, T(np.eye(3)) if opts.get("axis", "fwd") == "up" else euler_t(math.pi / 2, 0, 0)
    if kind in ("wheel", "ring"):
        radius, half = (dims[0] + dims[1], dims[1]) if kind == "wheel" else (dims[0], dims[2] / 2)
        tilt = euler_t(RAD * float(opts.get("tilt", 0.0)), 0, 0)
        turn = euler_t(0, 0, RAD * float(opts.get("spin", 0.0))) if kind == "ring" else T(np.eye(3))
        return ring_t(radius, radius, 2 * half), T(F.disc_base(opts.get("axis", "fwd" if kind == "wheel" else "up"))) @ tilt @ turn
    corners = T(np.array([[a, b, c] for a in (-1, 1) for b in (-1, 1) for c in (-1, 1)], float)) / 2
    return corners * vec([dims[0], dims[2], dims[1]]), euler_t(rx, -rz, ry)


def track_z_t(d):
    """fit_spec.track_z."""
    z = d / torch.linalg.norm(d)
    up = T([0.0, 0.0, 1.0]) - z[2] * z
    y = up / torch.linalg.norm(up) if float(torch.linalg.norm(up.detach())) > 1e-6 else T([0.0, 1.0, 0.0])
    return torch.stack([torch.linalg.cross(y, z), y, z], 1)


def fitted_t(kind, dims, a, b):
    """fit_spec.fitted_dims: the length of a from/to part is the distance of its joints, plus 8 %."""
    length = torch.linalg.norm(b - a) * 1.08
    return {"prism": (dims[0], dims[1], length), "cyl": (dims[0], length)}.get(
        kind, (dims[0], length, dims[2]) if kind in ("box", "frustum") else dims)


def simple_points(part, st):
    """box, prism, frustum, cyl, dome, wheel, ring: fit_spec.part_points past the lathe/limb/chain/plate branches."""
    kind, opts = part[1], part[5]
    dims, at, ends = st["dims"], st["at"], st["ends"]
    span = "from" in ends and "to" in ends
    if span:
        a, b = ends["from"], ends["to"]
        at = (a + b) / 2
        dims = fitted_t(kind, dims, a, b) if opts.get("fit", True) else dims
    pts, rot = local_t(kind, dims, opts, st["rot"])
    if span and kind != "ring":
        d = to_blender(b) - to_blender(a)
        rot = track_z_t(d) if float(torch.linalg.norm(d.detach())) > 1e-6 else rot
    return pts @ rot.T + to_blender(at)


def lathe_points(part, st):
    opts = part[5]
    r, h = st["dims"]
    at = st["at"]
    prof = st["profile"] if "profile" in st else T(opts.get("profile") or L.DEFAULT_PROFILE)
    n = L.sides_of(opts)
    ang = T(np.arange(n) * 2 * math.pi / n)
    count = len(prof)
    if prof.dim() == 1:
        squash = st["squash"] if "squash" in st else float(opts.get("squash", 1.0))
        y = at[1] - h / 2 + T(np.arange(count) / (count - 1)) * h
        rx = r * prof[:, None]
        rings = torch.stack([at[0] + rx * torch.cos(ang), y[:, None].expand(count, n), at[2] + rx / squash * torch.sin(ang)], -1)
        return to_blender(rings).reshape(-1, 3)
    corner = float(opts.get("corner", 0.0))
    push = 1 + corner * (math.sqrt(2) - 1) * torch.abs(torch.sin(2 * ang))
    t = prof[:, 4] if prof.shape[1] == 5 else T(np.arange(count) / (count - 1))
    ex, ey = (r * prof[:, k, None] * push * f(ang) for k, f in ((0, torch.cos), (1, torch.sin)))
    if opts.get("axis") == "z":
        rings = torch.stack([at[0] + r * prof[:, 3, None] + ex, at[1] + r * prof[:, 2, None] + ey,
                             (at[2] - h / 2 + t * h)[:, None].expand(count, n)], -1)
    else:
        rings = torch.stack([at[0] + r * prof[:, 3, None] + ex, (at[1] - h / 2 + t * h)[:, None].expand(count, n),
                             at[2] + r * prof[:, 2, None] + ey], -1)
    return to_blender(rings).reshape(-1, 3)


def unit_t(v):
    return v / torch.linalg.norm(v)


def ngon_t(c, d, r, n, phase=0.0):
    """lathe_limb.ngon about c in the plane normal to d, with the reference axis of limb_rings / chain_rings."""
    ref = T([0.0, 1.0, 0.0]) if abs(float(d[1].detach())) < 0.95 else T([1.0, 0.0, 0.0])
    u = unit_t(torch.linalg.cross(ref, d))
    v = torch.linalg.cross(d, u)
    a = T(phase + 2 * math.pi * np.arange(n) / n)
    return c + r * (torch.cos(a)[:, None] * u + torch.sin(a)[:, None] * v)


def limb_points(part, st):
    opts, dims = part[5], st["dims"]
    a, b = st["ends"]["from"], st["ends"]["to"]
    frac, dx, dz, *rest = st["knee"] if "knee" in st else opts.get("knee", L.KNEE)
    k = a + frac * (b - a) + vec([dx, rest[0] if rest else 0.0, dz])
    d1, d2 = unit_t(k - a), unit_t(b - k)
    n = L.sides_of(opts)
    rings = [ngon_t(c, d, r, n) for c, d, r in ((a, d1, dims[0]), (k, unit_t(d1 + d2), dims[1]), (b, d2, dims[2]))]
    return to_blender(torch.cat(rings))


def chain_points(part, st):
    opts = part[5]
    joints = [T(j) for j in L.chain_joints(part[0], int(opts["bones"]))]
    segs = [unit_t(b - a) for a, b in zip(joints, joints[1:])]
    dirs = [segs[0]] + [unit_t(a + b) for a, b in zip(segs, segs[1:])] + [segs[-1]]
    n = L.sides_of(opts)
    phase = 0.0 if n % 4 == 0 else math.pi / (2 * n)
    radii = L.chain_radii(st["dims"], opts)
    return to_blender(torch.cat([ngon_t(c, d, r, n, phase) for c, d, r in zip(joints, dirs, radii)]))


def plate_points(part, st):
    """fit_spec.part_points, plate branch: the profile polygon at each layer, turned by the constant rot, moved to `at`."""
    opts = part[5]
    w, h, t = st["dims"]
    prof = st["profile"] if "profile" in st else T(opts.get("profile") or L.DEFAULT_PLATE)
    bevel = float(opts.get("bevel", 0.0))
    cu, cv = prof[:, 0].mean(), prof[:, 1].mean()
    layers = [(-t / 2, 1.0), (t / 2, 1.0)]
    if bevel:
        layers = [(-t / 2, 1 - bevel), (-t / 2 * (1 - bevel), 1.0), (t / 2 * (1 - bevel), 1.0), (t / 2, 1 - bevel)]
    rows = []
    for depth, s in layers:
        a, b = (cu + (prof[:, 0] - cu) * s - 0.5) * w, (cv + (prof[:, 1] - cv) * s - 0.5) * h
        d = depth.expand(len(a))
        rows.append({"front": (a, b, d), "left": (d, b, a), "top": (a, d, b)}[opts.get("axis", "front")])
    local = to_blender(torch.stack([torch.stack(r, 1) for r in rows]).reshape(-1, 3))
    rx, ry, rz = (T(v) * RAD for v in F.spec_rot(opts))
    return local @ euler_t(rx, -rz, ry).T + to_blender(st["at"])


POINTS = {**{k: simple_points for k in ("box", "prism", "frustum", "cyl", "dome", "ring", "wheel")},
          "lathe": lathe_points, "limb": limb_points, "chain": chain_points, "plate": plate_points}


# ---------------------------------------------------------------- the extras of fit_spec.EXTRAS, in torch
def rot_t(part, st, v, mirror):
    sign = (1, -1, -1) if mirror else (1, 1, 1)
    st["rot"] = [r + F.ROT_RANGE * v[k] * sign[k] for k, r in enumerate(st["rot"])]


def profile_t(part, st, v, mirror):
    prof = T(part[5].get("profile") or [])
    count = len(prof)
    if not count:                 # no profile written yet: only the squash moves
        st["squash"] = (float(part[5].get("squash", 1.0)) * (1 + F.PROFILE_RANGE * v[0])).clamp(0.5, 2.0)
        return
    if L.is_ring_profile(part[5].get("profile")):
        deep = 1 + F.PROFILE_RANGE * v[count]
        grow = 1 + F.PROFILE_RANGE * v[:count]
        w = (prof[:, 0] * grow).clamp(0.05, L.RING_MAX)
        d = (prof[:, 1] * grow / deep).clamp(0.05, L.RING_MAX)
        st["profile"] = torch.cat([w[:, None], d[:, None], prof[:, 2:]], 1)
        return
    st["profile"] = (prof * (1 + F.PROFILE_RANGE * v[:count])).clamp(0.05, L.PROFILE_MAX)
    st["squash"] = (float(part[5].get("squash", 1.0)) * (1 + F.PROFILE_RANGE * v[count])).clamp(0.5, 2.0)


def knee_t(part, st, v, mirror):
    frac, dx, dz, *rest = part[5].get("knee", L.KNEE)
    step = F.AT_RANGE * st["height"]
    st["knee"] = ((frac + F.KNEE_RANGE * v[0]).clamp(0.15, 0.85), dx + step * v[1] * (-1 if mirror else 1),
                  dz + step * v[2], *rest)


def plate_profile_t(part, st, v, mirror):
    prof = T(part[5]["profile"])
    c = prof.mean(0)
    st["profile"] = (c + (prof - c) * (1 + F.PROFILE_RANGE * v[:2])).clamp(0, 1)


EXTRA_T = {"rot": rot_t, "profile": profile_t, "knee": knee_t, "plate": plate_profile_t}


def dynamic(part, x, height, mirror, names):
    """fit_spec.moved in torch: the part's dims, at, from/to, rot, ... as tensors of the unit parameters x."""
    dims, at, opts = part[2], part[3], part[5]
    n = len(dims)
    delta = F.AT_RANGE * height * x[n:n + 3] * T([-1.0 if mirror else 1.0, 1.0, 1.0])
    st = {"dims": [d * (1 + F.DIMS_RANGE * x[k]) for k, d in enumerate(dims)], "at": T(at) + delta, "delta": delta,
          "ends": {e: T(opts[e]) + delta for e in ("from", "to") if e in opts}, "rot": list(F.spec_rot(opts)),
          "height": height}
    k = n + 3
    for name in names:
        size = F.extra_size(part, name)
        EXTRA_T[name](part, st, x[k:k + size], mirror)
        k += size
    return st


# ---------------------------------------------------------------- the soft loss
def fan(xy, offset):
    """Triangles (vertex ids + offset) fanning the convex hull of the 2D points; none for a flat part."""
    try:
        hull = ConvexHull(xy).vertices
    except QhullError:
        return []
    return [(hull[0] + offset, hull[k] + offset, hull[k + 1] + offset) for k in range(1, len(hull) - 1)]


def best_variant(mask, concept, view):
    """(mask, soft IoU, flipped): the better of the mask and its mirror, as Proxy.best_variant."""
    options = [mask] if view == "rts" else [mask, torch.flip(mask, [1])]
    k = silhouette.pick_variant(concept.detach().cpu().numpy() > 0.5, [o.detach().cpu().numpy() > 0.5 for o in options], view)
    return options[k], soft_sil.soft_iou(options[k], concept), k == 1


def edge_cost(mask, dist):
    """Differentiable half of the chamfer: mean distance, in canvas heights, from the mask's edge (mask - its 3x3 erosion)
    to the sheet's contour (Proxy.view_score's dist[edge].mean())."""
    m = mask[None, None]
    edge = (m + torch.nn.functional.max_pool2d(-m, 3, 1, 1)).reshape(mask.shape).clamp(min=0)
    return (edge * dist).sum() / edge.sum().clamp(min=1e-6) / mask.shape[0]


class Scene:
    """What the gradient sees of a fit: which parts move (and with which slice of x), the constants of the others."""

    def __init__(self, proxy, parts, groups, extra, height, parent_of=None, loose0=(), feet=None):
        self.proxy, self.parts, self.height = proxy, parts, height
        self.links, self.twins = links_of(parts, parent_of or {}, loose0), twins_of(parts)
        self.state, self.feet = {}, feet_of(parts, feet)
        self.fixed_parts, self.slots, k = [], [], 0
        for i, j in groups:
            names, n = extra.get(i, ()), F.group_size(parts[i], extra.get(i, ()))
            if not (supported(parts[i]) and (j is None or supported(parts[j]))):
                self.fixed_parts += [i] if j is None else [i, j]
            else:
                self.slots += [(i, False, slice(k, k + n), names)] + ([(j, True, slice(k, k + n), names)] if j is not None else [])
            k += n
        self.size = k
        moving = {s[0] for s in self.slots}
        self.const = {i: T(F.part_points(p)) for i, p in enumerate(parts) if i not in moving}
        self.bones = {p[0] for p in parts}
        self.props = [i for i, p in enumerate(parts) if preflight.is_prop(p)]
        self.axes = {v: types.SimpleNamespace(mirror=1.0, **dict(zip(("ru", "rv"), (
            a.astype(float) for a in F.project(v, np.eye(3), proxy.cams.get(v)))))) for v in proxy.views}
        self.concept = {v: T(m) for v, m in proxy.concept.items()}
        self.split = {v: (T(s[0]), T(s[1]), T(s[3])) for v, s in proxy.split.items()}
        self.dist = {v: T(d) for v, d in proxy.dist.items()}

    def points(self, x):
        """[points [N_i, 3] per part] for the unit vector x; a prop rides the mean shift of the parts on its anchor."""
        out, shifts = dict(self.const), {}
        for i, mirror, sl, names in self.slots:
            st = dynamic(self.parts[i], x[sl], self.height, mirror, names)
            out[i], shifts[i], self.state[i] = POINTS[self.parts[i][1]](self.parts[i], st), st["delta"], st
        for i in self.props:
            bone = preflight.anchor_bone(self.parts[i], self.bones)
            moved = [shifts[j] for j, q in enumerate(self.parts) if q[0] == bone and not preflight.is_prop(q) and j in shifts]
            n_bone = sum(1 for q in self.parts if q[0] == bone and not preflight.is_prop(q))
            if moved:                 # fit_spec.carry_props: the mean over every non-prop part of the bone, the fixed ones at 0
                out[i] = self.const[i] + to_blender(torch.stack(moved).sum(0) / n_bone)
        return [out[i] for i in range(len(self.parts))]

    def view_loss(self, view, pts, tau):
        """(1 - IoU) + chamfer of one view (Proxy.score_view) with the soft masks at tau."""
        px = soft_sil.project(torch.cat(pts), self.axes[view])
        flat, tris, start = px.detach().numpy(), {False: [], True: []}, 0
        for i, p in enumerate(pts):
            tris[preflight.is_prop(self.parts[i])] += fan(flat[start:start + len(p)], start)
            start += len(p)

        def mask(ids):
            return soft_sil.soft_mask(px[torch.as_tensor(np.array(ids, int))], tau=tau) if ids else px.new_zeros(soft_sil.SHAPE)
        split = self.split.get(view)
        if not split:
            best, iou, _ = best_variant(mask(tris[False] + tris[True]), self.concept[view], view)
            return 1 - iou + F.CHAMFER_W * edge_cost(best, self.dist[view])
        best, iou, flipped = best_variant(mask(tris[False]), split[0], view)
        if tris[True]:
            prop = mask(tris[True])
            share = (split[1].sum() / (split[0].sum() + split[1].sum()).clamp(min=1)).item()
            iou = (1 - share) * iou + share * soft_sil.soft_iou(torch.flip(prop, [1]) if flipped else prop, split[1])
        return 1 - iou + F.CHAMFER_W * edge_cost(best, split[2])

    def boots(self, pts):
        """How far the smallest boot's height and length (H) are outside the bands of preflight.biped_checks (0 without feet)."""
        if not self.feet:
            return T(0.0)
        size = torch.stack([(pts[i].max(0).values - pts[i].min(0).values) for i in self.feet["ids"]]).amin(0) / self.height
        (h0, h1), (l0, l1) = self.feet["height"], self.feet["length"]
        return torch.relu(h0 * (1 + FEET_IN) - size[2]) + torch.relu(size[2] - h1 * (1 - FEET_IN)) \
            + torch.relu(l0 * (1 + FEET_IN) - size[1]) + torch.relu(size[1] - l1 * (1 - FEET_IN))

    def unlike(self):
        """Sum over the twins (.L / .R parts that move on their own) of how far dims and rot are past what preflight's mirror_gap tolerates."""
        total = T(0.0)
        for i, q in self.twins:
            a, b = (self.state.get(k) or {"dims": self.parts[k][2], "rot": F.spec_rot(self.parts[k][5])} for k in (i, q))
            for x, y in zip(a["dims"], b["dims"]):
                total = total + torch.relu((T(x) - T(y)).abs() / torch.maximum(T(x).abs(), T(y).abs()).clamp(min=1e-6) - SYM_TOL)
            for x, y, sign in zip(a["rot"], b["rot"], (1, -1, -1)):
                total = total + torch.relu((T(x) - sign * T(y)).abs() - SYM_ROT) / 100
        return total

    def apart(self, pts):
        """Sum over the linked parts of the distance (L1 of the per-axis gaps) to the nearest part they must touch, from the points' boxes."""
        lo, hi = torch.stack([p.min(0).values for p in pts]), torch.stack([p.max(0).values for p in pts])
        mid, half = (lo + hi) / 2, (hi - lo) / 2
        return sum(torch.stack([torch.relu((mid[i] - mid[q]).abs() - k * (half[i] + half[q])).sum() for q in sibs]).min()
                   for i, sibs, k in self.links)

    def loss(self, x, tau):
        """Proxy.loss (weighted views) + the hinges of the preflight rules the fit may not break: ground, overlap, symmetry."""
        pts = self.points(x)
        w = self.proxy.weight
        rules = (GROUND_W * sum(torch.relu(-p[:, 2].min()) for p in pts) + LINK_W * self.apart(pts)) / self.height \
            + SYM_W * self.unlike() + FEET_W * self.boots(pts)
        return sum(w[v] * self.view_loss(v, pts, tau) for v in self.proxy.views) / sum(w[v] for v in self.proxy.views) + rules


def links_of(parts, parent_of, loose0=()):
    """[(part, [parts it must touch], k)]: preflight.floating_parts' siblings (the parts on its bone and its parent's, props out) of
    every part with a parent, boxes at k = OVERLAP_SHRINK (a bone that was loose at the start: 1, the rule `overlap`); descend
    passes {} when `overlap` already fails at the start."""
    out = []
    for i, p in enumerate(parts):
        parent = parent_of.get(p[0])
        if not parent or preflight.is_prop(p):
            continue
        sibs = [j for j, q in enumerate(parts) if q[0] in (p[0], parent) and j != i and not preflight.is_prop(q)]
        if sibs:
            out.append((i, sibs, 1.0 if p[0] in loose0 else preflight.OVERLAP_SHRINK))
    return out


def feet_of(parts, feet):
    """{"ids", "height", "length"}: the foot parts and the bands (H) preflight.biped_checks asks of the smallest one, or None
    (`feet` = (targets, held rule names), or None for a unit that is not a biped / whose rules fail already)."""
    if not feet or feet[1] & {"feet_mass", "boot_height"}:
        return None
    targets = feet[0]
    ids = [i for i, p in enumerate(parts) if p[0] in ("foot.L", "foot.R")]
    if not ids or "foot_length" not in targets or "boot_height" not in targets:
        return None
    band = preflight.BOOT_BAND
    return {"ids": ids, "length": (0.8 * targets["foot_length"], preflight.FOOT_MOST * targets["foot_length"]),
            "height": (max(0.045, band[0] * targets["boot_height"]), band[1] * targets["boot_height"])}


def twins_of(parts):
    """[(left, right)] part indices preflight.asymmetric would pair (same kind, nearest in y, z) where one of them moves alone."""
    out = []
    for i, p in enumerate(parts):
        if not p[0].endswith(".L") or preflight.is_prop(p) or p[5].get("asym"):
            continue
        rest = [j for j, q in enumerate(parts) if q[0] == p[0][:-2] + ".R" and q[1] == p[1] and len(q[2]) == len(p[2])
                and not q[5].get("asym")]
        if rest:
            out.append((i, min(rest, key=lambda j: abs(parts[j][3][1] - p[3][1]) + abs(parts[j][3][2] - p[3][2]))))
    return out


def supported(part):
    """A kind the torch twin has and no `cut: sheet` (the cut hull is a Blender op the proxy never sees): else the part stays fixed."""
    return part[1] in SUPPORTED and not (isinstance(part[5], dict) and part[5].get("cut"))


# ---------------------------------------------------------------- the descent
def descend(objective, groups, bounds, parts, extra, proxy, height, seconds):
    """Adam on the soft loss from x = 0, tau annealed; every CHECK steps `objective` (the exact one) judges the point and keeps
    the best. Returns the report entries (steps, fixed parts, checks that reverted)."""
    scene = Scene(proxy, parts, groups, extra, height, {} if "overlap" in objective.ctx["held"] else objective.ctx["parent_of"], objective.ctx["loose0"],
                  (objective.ctx["targets"], objective.ctx["held"]))
    lo, hi = (torch.tensor([b[k] for b in bounds], dtype=DT) for k in (0, 1))
    x = torch.minimum(torch.maximum(torch.zeros(scene.size, dtype=DT), lo), hi).requires_grad_(True)   # x = 0, or the nearest point of the limits (L11-3)
    good, steps, reverts = x.detach().clone(), 0, 0
    ctx = objective.ctx
    lr = LR
    opt = torch.optim.Adam([x], lr=lr)
    try:
        objective(x.detach().double().numpy())  # the start point is a candidate too
        for tau in TAUS:
            for step in range(STEPS):
                if time.monotonic() > ctx["deadline"]:
                    raise F.Stop
                opt.zero_grad()
                value = scene.loss(x, tau)
                value.backward()
                steps += 1
                if not torch.isfinite(x.grad).all():
                    x.grad = torch.nan_to_num(x.grad)
                opt.step()
                x.data = torch.minimum(torch.maximum(x.data, lo), hi)
                if (step + 1) % CHECK == 0:
                    good, backed = settle(objective, x, good)
                    reverts += backed
                    if backed == 2:             # even a short step toward x broke a rule: smaller steps from here
                        lr /= 2
                        opt = torch.optim.Adam([x], lr=lr)
    except F.Stop:
        pass
    return {"grad_steps": steps, "grad_fixed": [parts[i][0] for i in scene.fixed_parts], "grad_reverts": reverts}


def settle(objective, x, good, tries=3):
    """Judge x with the exact objective. A point that breaks a rule that held (PENALTY) or costs more than the best so far + SLACK
    is pulled back toward the last good point, halving the distance up to `tries` times, then to the good point itself.
    Returns (new good point, 0 kept / 1 backed off / 2 back at the good point)."""
    for k in range(tries + 1):
        if objective(x.detach().double().numpy()) < min(F.PENALTY, objective.best["f"] + SLACK):
            return x.detach().clone(), int(k > 0)
        x.data = good + (x.data - good) * 0.5 if k < tries else good.clone()
    return good, 2
