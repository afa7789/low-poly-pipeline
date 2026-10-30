#!/usr/bin/env python3
"""Signed distance field of a spec's BODY (PIPELINE 28.L10-1): every part that is not a prop or the flame slit.

    python3.14 tools/blender/sdf_body.py spec.json --grid 96 --out campo.npy --json clay.sdf.json [--cuts cuts.json]
        [--k 1.0] [--owner]

numpy only, so it imports in python3.14 and in Blender's Python (numpy, no scipy / PIL; scipy is used for the convex hull
when it is there, else the planes come from a brute-force hull). Blender axes (x right, y = -forward, z up), metres.

A convex piece is `max_j(n_j . p + b_j)` over the planes of its hull: exact zero set, facets like the mesh's (an 8-gon stays an
8-gon). A lathe, limb, chain is a stack of such pieces between consecutive rings (hard min); a plate is the hull of its rings;
a wheel is a torus; a ring an annulus (+ spokes and hub as hulls); `cut: sheet` is `max(part, prism front, prism left, prism top)`
with a 2D polygon (concave ok). A part's pieces are joined by a hard min; two parts are joined by a polynomial smooth-min
(Quilez) only when their bones are the same or parent / child, k = 0.25 x the smaller radius clamped to [0.5 voxel, 0.03 H];
the rest by a hard min. The value is a lower bound of the Euclidean distance (exact on the surface), truncated at `margin`
outside. The same pieces + pairs + k + grid are written to clay.sdf.json, so mesh_lint recomputes the field in python3.14.
"""
import argparse
import itertools
import json
import math
import pathlib
import sys
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lathe_limb  # noqa: E402
import part_geom as PG  # noqa: E402
import rig_families as RF  # noqa: E402

GRID = 96               # voxels along the body's height (64 for budgets, 128 for a wyrm / drake)
PAD = 3                 # voxels of air around the body's box
K_FRAC = 0.25           # smooth-min width, x the smaller radius of the two parts
K_MAX_H = 0.03          # ... at most this share of the height
K_MIN_VOX = 0.5         # ... at least this many voxels
K_MODES = ("base", "class", "hard", "ext")     # PIPELINE 29.L11-5: base = the k above; class = x CLASS_K of the joint; hard = k 0 (union
                                               # in the field); ext = base k blended only where both parts are outside (no fattening)
CLASS_K = {("trunk", "trunk"): 1.0, ("limb", "trunk"): 0.5, ("limb", "limb"): 0.0}    # class mode: k x this, by the joint's classes
LIMB_BONES = ("arm", "forearm", "hand", "thigh", "shin", "foot", "leg", "wing", "wheel")    # a bone's prefix before the first '.' / digit
MARGIN_VOX = 4          # the field is truncated this many voxels (at least 2 k) outside the body
EPS = 1e-9              # plane tolerance of the brute-force hull, x the scale of the points
NO_SDF = ("flame",)     # materials kept out of the body (build_unit: the lit slit)
SWEEPS = ("lathe", "limb", "chain", "plate")
HULLS = ("box", "prism", "frustum", "cyl", "dome")

try:                    # scipy is optional: Blender's Python has none
    from scipy.spatial import ConvexHull, QhullError
except ImportError:
    ConvexHull = QhullError = None


# ---------------------------------------------------------------- hull planes
def _brute_planes(pts, block=20000):
    """[nx, ny, nz, b] of every plane through three of the points that has all the points on one side (outward normals);
    both sides of a flat set. O(n^4): fine for the <= 50 points of a part, chunked for more."""
    scale = max(float(np.ptp(pts, axis=0).max()), 1e-9)
    tri = np.array(list(itertools.combinations(range(len(pts)), 3)))
    out = []
    for i in range(0, len(tri), block):
        a, b, c = (pts[tri[i:i + block, j]] for j in range(3))
        n = np.cross(b - a, c - a)
        ln = np.linalg.norm(n, axis=1)
        good = ln > 1e-12 * scale * scale
        n, a = n[good] / ln[good, None], a[good]
        off = -(n * a).sum(1)
        side = pts @ n.T + off
        eps = EPS * scale
        flat = (np.abs(side) <= eps).all(0)
        keep = (side <= eps).all(0) | (side >= -eps).all(0)
        flip = (side > eps).any(0)
        n, off = np.where(flip[:, None], -n, n)[keep], np.where(flip, -off, off)[keep]
        out.append(np.c_[n, off])
        if flat.any():
            out.append(-np.c_[n, off][flat[keep]])
    return np.concatenate(out) if out else np.zeros((0, 4))


def hull_planes(pts):
    """(m, 4) planes [n, b] (n . p + b <= 0 inside, unit n) of the convex hull of (n, 3) points, duplicates dropped."""
    pts = np.asarray(pts, float)
    _, keep = np.unique(np.round(pts, 9), axis=0, return_index=True)
    pts = pts[np.sort(keep)]
    planes = None
    if ConvexHull is not None and len(pts) >= 4:
        try:
            planes = ConvexHull(pts).equations
        except QhullError:
            planes = None
    if planes is None:
        planes = _brute_planes(pts)
    return np.unique(np.round(planes, 8), axis=0)


# ---------------------------------------------------------------- pieces: JSON-able dicts, Blender axes
def to_blender(p):
    """Spec (right, up, forward) points -> Blender (x, y, z)."""
    p = np.asarray(p, float).reshape(-1, 3)
    return np.stack([p[:, 0], -p[:, 2], p[:, 1]], 1)


def hull_piece(pts):
    pts = np.asarray(pts, float)
    return {"t": "hull", "planes": hull_planes(pts).tolist(), "lo": pts.min(0).tolist(), "hi": pts.max(0).tolist(),
            "c": pts.mean(0).tolist()}


def stack_pieces(rings):
    """One hull per pair of consecutive rings (each (n, 3)); a ring pair is a frustum-like tube and the stack is the part."""
    return [hull_piece(np.concatenate([a, b])) for a, b in zip(rings, rings[1:])]


def triangulate(poly):
    """Ear-clipping triangles (index triples) of a simple polygon, or None when it is convex (one hull is exact)."""
    pts = np.asarray(poly, float)
    sign = 1.0 if (pts[:, 0] * np.roll(pts[:, 1], -1) - np.roll(pts[:, 0], -1) * pts[:, 1]).sum() > 0 else -1.0

    def turn(a, b, c):          # > 0: a -> b -> c turns the way the polygon runs
        return sign * float((pts[b, 0] - pts[a, 0]) * (pts[c, 1] - pts[a, 1]) - (pts[b, 1] - pts[a, 1]) * (pts[c, 0] - pts[a, 0]))

    def is_ear(a, b, c, rest):
        return turn(a, b, c) > 1e-12 and not any(
            all(turn(p, q, m) >= -1e-12 for p, q in ((a, b), (b, c), (c, a))) for m in rest if m not in (a, b, c))

    idx = list(range(len(pts)))
    if all(turn(idx[i - 1], idx[i], idx[(i + 1) % len(idx)]) >= -1e-12 for i in range(len(idx))):
        return None
    tris = []
    while len(idx) > 3:
        n = len(idx)
        k = next((i for i in range(n) if is_ear(idx[i - 1], idx[i], idx[(i + 1) % n], idx)), None)
        if k is None:
            return None
        tris.append((idx[k - 1], idx[k], idx[(k + 1) % n]))
        del idx[k]
    return [*tris, tuple(idx)]


def plate_pieces(part, sheet):
    """A plate's hull; a concave profile (wings) is cut into triangles, each lofted between consecutive rings (the bevel
    scales the rings about one centre, so a triangle's loft is the hull of its two ring triangles), so the concave
    corners stay on the surface."""
    rings = PG.rings_of(part, sheet)
    prof = (part[5] or {}).get("profile") or sheet or lathe_limb.DEFAULT_PLATE
    tris = triangulate(prof)
    if tris is None:
        return [hull_piece(np.concatenate(rings))]
    return [hull_piece(np.concatenate([a[list(t)], b[list(t)]])) for t in tris for a, b in zip(rings, rings[1:])]


def torus_piece(centre, rot, major, minor):
    r = major + minor
    c = np.asarray(centre, float)
    return {"t": "torus", "c": c.tolist(), "m": np.asarray(rot, float).tolist(), "R": float(major), "r": float(minor),
            "lo": (c - r).tolist(), "hi": (c + r).tolist()}


def annulus_piece(centre, rot, outer, inner, thick):
    c, reach = np.asarray(centre, float), outer + thick / 2
    return {"t": "annulus", "c": c.tolist(), "m": np.asarray(rot, float).tolist(), "ro": float(outer), "ri": float(inner),
            "h": float(thick), "lo": (c - reach).tolist(), "hi": (c + reach).tolist()}


def prism_piece(poly, axis, lo, hi):
    """The outline `poly` of (a, b) points extruded from lo to hi along the third spec axis (cut_part's extrude): z: (x, y),
    x: (z, y), y: (x, z). Stored in spec axes (the query is converted), the box in Blender axes."""
    poly = np.asarray(poly, float)
    u, v = poly.min(0), poly.max(0)
    ranges = {"z": ((u[0], v[0]), (u[1], v[1]), (lo, hi)), "x": ((lo, hi), (u[1], v[1]), (u[0], v[0])),
              "y": ((u[0], v[0]), (lo, hi), (u[1], v[1]))}[axis]
    (x0, x1), (y0, y1), (z0, z1) = ranges
    return {"t": "prism", "poly": poly.tolist(), "axis": axis, "a": float(lo), "b": float(hi),
            "lo": [x0, -z1, y0], "hi": [x1, -z0, y1]}


def tilted(kind, opts):
    """Rotation of a ring / wheel's disc: part_geom.local_shape's, so the pieces follow the mesh."""
    return PG.local_shape(kind, (1.0, 1.0, 1.0), opts)[1]


def ring_pieces(part):
    """An annulus (outer radius, radial width, thickness), plus its spokes and hub as hulls (build_unit.ring)."""
    _, _, dims, at, _, opts = part
    outer, width, thick = dims
    inner = max(outer - width, 0.01)
    rot, centre = tilted("ring", opts), PG.spec_to_blender(at)
    pieces = [annulus_piece(centre, rot, outer, inner, thick)]
    spokes = int(opts.get("spokes", 0))
    hub = float(opts.get("hub", 0.0)) or (inner * 0.32 if spokes else 0.0)
    cube = np.array([[x, y, z] for x in (-.5, .5) for y in (-.5, .5) for z in (-.5, .5)])
    for k in range(spokes):
        ang, mid = PG.D(90 + 360 * k / spokes), (inner + hub) / 2
        turn = np.array([[math.cos(ang), -math.sin(ang), 0], [math.sin(ang), math.cos(ang), 0], [0, 0, 1]])
        local = cube * [inner - hub, width * 0.72, thick * 0.8] @ turn.T + [mid * math.cos(ang), mid * math.sin(ang), 0]
        pieces.append(hull_piece(local @ rot.T + centre))
    if hub:
        pieces.append(hull_piece(PG.ring_points(hub, hub, thick, 8) @ rot.T + centre))
    return pieces


def cut_prisms(cut):
    """{front, left, top}: the prisms cut_part intersects, with its margins."""
    lo, hi = cut["box"]
    m = [0.1 * (hi[a] - lo[a]) + 0.01 for a in range(3)]
    axes = {"front": ("z", 2), "left": ("x", 0), "top": ("y", 1)}
    return {k: prism_piece(cut[k], ax, lo[i] - m[i], hi[i] + m[i]) for k, (ax, i) in axes.items() if k in cut}


def part_pieces(part, cut):
    """(pieces, cut prisms, exact): the part's pieces (hard min), the prisms that trim them (max), whether the zero set is
    the mesh's (False: the generic convex hull of part_points)."""
    _, kind, dims, at, _, opts = part
    opts = opts or {}
    sheet = (cut or {}).get({"lathe": "profile", "chain": "radii", "plate": "profile"}.get(kind, ""))
    pieces, exact = [], True
    if kind in ("lathe", "limb", "chain"):
        pieces = stack_pieces(PG.rings_of(part, sheet))
    elif kind == "plate":
        pieces = plate_pieces(part, sheet)
    elif kind in HULLS:
        pieces = [hull_piece(PG.part_points(part))]
    elif kind == "wheel":
        _, rot, centre, _ = PG.placed(part)
        pieces = [torus_piece(centre, rot, dims[0], dims[1])]
    elif kind == "ring":
        pieces = ring_pieces(part)
    else:
        pieces, exact = [hull_piece(PG.part_points(part))], False
    if not (opts.get("cut") == "sheet" and cut and "front" in cut):
        return pieces, [], exact
    prisms = cut_prisms(cut)
    if kind == "lathe":
        return pieces, list(prisms.values()), exact
    return [prisms.pop("front")], list(prisms.values()), exact       # the front prism is the part, the others trim it


# ---------------------------------------------------------------- evaluation: P is (N, 3) in Blender axes
def hull_d(p, P):
    n = np.asarray(p["planes"], P.dtype)
    return (P @ n[:, :3].T + n[:, 3]).max(1)


def disc_coords(p, P):
    q = (P - np.asarray(p["c"], P.dtype)) @ np.asarray(p["m"], P.dtype)
    return np.hypot(q[:, 0], q[:, 1]), q[:, 2]


def torus_d(p, P):
    rho, z = disc_coords(p, P)
    return np.hypot(rho - p["R"], z) - p["r"]


def annulus_d(p, P):
    rho, z = disc_coords(p, P)
    return np.maximum(np.abs(rho - (p["ro"] + p["ri"]) / 2) - (p["ro"] - p["ri"]) / 2, np.abs(z) - p["h"] / 2)


def polygon_sd(poly, uv):
    """Signed distance (negative inside) of (N, 2) points to a simple polygon, concave ok."""
    a, b = poly, np.roll(poly, -1, axis=0)
    e = b - a
    w = uv[:, None, :] - a[None]
    t = np.clip((w * e).sum(2) / np.maximum((e * e).sum(1), 1e-18), 0, 1)
    dist = np.linalg.norm(w - t[..., None] * e, axis=2).min(1)
    py = uv[:, 1:2]
    cross = (a[:, 1] > py) != (b[:, 1] > py)
    xs = a[:, 0] + (py - a[:, 1]) * e[:, 0] / np.where(e[:, 1] == 0, 1e-18, e[:, 1])
    inside = ((cross & (uv[:, :1] < xs)).sum(1) % 2) == 1
    return np.where(inside, -dist, dist)


def prism_d(p, P):
    sx, sy, sz = P[:, 0], P[:, 2], -P[:, 1]              # spec axes
    u, v, depth = {"z": (sx, sy, sz), "x": (sz, sy, sx), "y": (sx, sz, sy)}[p["axis"]]
    d2 = polygon_sd(np.asarray(p["poly"], P.dtype), np.stack([u, v], 1))
    return np.maximum(d2, np.abs(depth - (p["a"] + p["b"]) / 2) - (p["b"] - p["a"]) / 2)


EVAL = {"hull": hull_d, "torus": torus_d, "annulus": annulus_d, "prism": prism_d}


def part_d(part, P):
    """Distance of the (N, 3) points to one normalized part: min of its pieces, trimmed by its cut prisms."""
    d = EVAL[part["pieces"][0]["t"]](part["pieces"][0], P)
    for q in part["pieces"][1:]:
        d = np.minimum(d, EVAL[q["t"]](q, P))
    for q in part["cut"]:
        d = np.maximum(d, EVAL[q["t"]](q, P))
    return d - part.get("inflate", 0.0)


def smin(a, b, k, exterior=False):
    """Polynomial smooth minimum (Quilez); a hard min for k <= 0. `exterior`: the blend only where a and b are both > 0 (outside
    both parts), so the inside of a joint stays the plain min and the blend fills only the crease (PIPELINE 29.L11-5)."""
    if k <= 0:
        return np.minimum(a, b)
    h = np.maximum(k - np.abs(a - b), 0) / k
    if exterior:
        h = h * ((a > 0) & (b > 0))
    return np.minimum(a, b) - h * h * k * 0.25


# ---------------------------------------------------------------- normalize a spec
def inradius(part):
    """A lower bound of the thickness / 2 of a part: the deepest of its pieces at a point inside them."""
    best = 0.0
    for q in part["pieces"]:
        if q["t"] == "torus":
            best = max(best, q["r"])
        elif q["t"] == "annulus":
            best = max(best, min((q["ro"] - q["ri"]) / 2, q["h"] / 2))
        else:
            c = np.asarray(q.get("c", (np.asarray(q["lo"]) + q["hi"]) / 2))[None]
            best = max(best, float(-EVAL[q["t"]](q, c)[0]))
    return best or 0.5 * float(np.ptp([part["lo"], part["hi"]], axis=0).min())


THIN_VOX = 2.0          # a part thinner than this many voxels (2 x inradius) may vanish from the grid (PIPELINE 28.L10-7)
THIN_FLOOR_VOX = 2.5    # ... and "inflate" fattens it to this thickness: d - (2.5 voxel - t) / 2


def thin_inflation(parts, voxel):
    """{row i: inflation} of the normalized `parts` thinner than THIN_VOX voxels: (THIN_FLOOR_VOX voxel - t) / 2 with t = 2 r,
    the amount the part's distance is lowered by. Pure; a "keep" policy uses just the keys."""
    return {p["i"]: max(0.0, (THIN_FLOOR_VOX * voxel - 2 * p["r"]) / 2) for p in parts if 2 * p["r"] < THIN_VOX * voxel}


def part_box(pieces, prisms):
    """(lo, hi) of the part: the pieces' union, cut to the prisms' intersection."""
    lo, hi = np.min([q["lo"] for q in pieces], axis=0), np.max([q["hi"] for q in pieces], axis=0)
    for q in prisms:
        lo, hi = np.maximum(lo, q["lo"]), np.minimum(hi, q["hi"])
    return lo, np.maximum(hi, lo)


RIGID_BONES = ("head", "jaw", "hand", "foot", "toe")      # L15-2: a bone's prefix before the first '.': its parts are rigid pieces, not core
ARTHROPODS = ("spider", "spider_high", "crustacean")      # their lower legs (below the knee) are rigid
HARD_SURFACES = ("metal", "polished")


def is_rigid(row, family="biped", surface=""):
    """L15-2 (PIPELINE 33.L15-2): the ROLE of a spec row, not its name. Rigid = head / hands / feet by bone, any part with a decal, a
    plate or box whose material paints as metal (`surface` = its palette surface), an arthropod's lower leg, a prop. The rest is core
    (trunk, pelvis, thighs, arms): the only rows the SDF fuses when build_unit's sdf_core is on."""
    opts = row[5] if isinstance(row[5], dict) else {}
    base = str(row[0]).split(".")[0]
    lower = family in ARTHROPODS and base.startswith("leg") and str(row[0]).endswith(".lower")
    return bool(opts.get("prop") or opts.get("decal") or base in RIGID_BONES or lower
                or (row[1] in ("plate", "box") and surface in HARD_SURFACES))


def is_body(part):
    opts = part[5] if isinstance(part[5], dict) else {}
    return not opts.get("prop") and not opts.get("rigid") and part[4] not in NO_SDF


def core_rows(rows, family="biped", surfaces=None):
    """(rows with opts "rigid" on the rigid ones, their indices): what field() leaves out. No core row left -> (rows, [])."""
    surfaces = surfaces or {}
    idx = [i for i, r in enumerate(rows) if is_rigid(r, family, surfaces.get(r[4], "")) and is_body(r)]
    if len(idx) == sum(1 for r in rows if is_body(r)):
        return list(rows), []
    out = [(*r[:5], {**(r[5] or {}), "rigid": True}) if i in idx else r for i, r in enumerate(rows)]
    return out, idx


def normalize(parts, cuts=None, rig=("biped", ())):
    """The body parts of a spec as dicts {i, bone, kind, r, exact, pieces, cut, lo, hi}: i = the row, props and flame out.
    `rig` = (family, extra bones), as lathe_limb.set_rig (a chain finds its joints there); the previous one is restored."""
    cuts, kept = cuts or {}, lathe_limb.RIG
    lathe_limb.set_rig(*rig)
    try:
        out = []
        for i, row in enumerate(parts):
            if not is_body(row):
                continue
            row = (row[0], row[1], tuple(row[2]), tuple(row[3]), row[4], row[5] or {})
            pieces, prisms, exact = part_pieces(row, cuts.get(str(i)))
            lo, hi = part_box(pieces, prisms)
            part = {"i": i, "bone": row[0], "kind": row[1], "exact": exact, "pieces": pieces, "cut": prisms,
                    "lo": lo.tolist(), "hi": hi.tolist()}
            part["r"] = inradius(part)
            out.append(part)
        return out
    finally:
        lathe_limb.RIG = kept


def related(parents, a, b):
    return a == b or parents.get(a) == b or parents.get(b) == a


# ---------------------------------------------------------------- the field
class Field:
    """parts (normalized) + pairs [(a, b, k)] smooth-joined + the grid. `grid` float32 (nx, ny, nz), `origin`, `voxel`; `owner`
    int16 (part index in `parts`, -1 where no part is within `margin`) after compute(owner=True)."""

    def __init__(self, parts, pairs, origin, voxel, shape, k_scale=1.0, k_mode="base"):
        self.parts, self.pairs, self.k_scale, self.k_mode = parts, [tuple(p) for p in pairs], k_scale, k_mode
        self.origin, self.voxel, self.shape = np.asarray(origin, float), float(voxel), tuple(int(s) for s in shape)
        self.margin = max(MARGIN_VOX * self.voxel, 2 * max((k for *_, k in self.pairs), default=0.0))
        self.grid = self.owner = None
        self.kept = []      # rows left out of the field as too thin (field(thin="keep"))

    def to_json(self):
        return {"version": 1, "k_scale": self.k_scale, "k_mode": self.k_mode, "origin": self.origin.tolist(), "voxel": self.voxel,
                "shape": list(self.shape), "pairs": [list(p) for p in self.pairs], "parts": self.parts}

    @classmethod
    def from_json(cls, doc):
        return cls(doc["parts"], doc["pairs"], doc["origin"], doc["voxel"], doc["shape"], doc.get("k_scale", 1.0),
                   doc.get("k_mode", "base"))

    def slab(self, part):
        """Index ranges ((i0, i1), ..) of the grid within `margin` of the part's box, or None."""
        lo = np.floor((np.asarray(part["lo"]) - self.margin - self.origin) / self.voxel).astype(int)
        hi = np.ceil((np.asarray(part["hi"]) + self.margin - self.origin) / self.voxel).astype(int) + 1
        lo, hi = np.maximum(lo, 0), np.minimum(hi, self.shape)
        return None if (hi <= lo).any() else tuple(zip(lo.tolist(), hi.tolist()))

    def points(self, rng):
        axes = [(self.origin[a] + self.voxel * np.arange(*rng[a])).astype(np.float32) for a in range(3)]
        return np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)

    def compute(self, owner=False):
        """Fill self.grid (and self.owner): per part on its slab, then the smooth pairs where their slabs overlap."""
        grid = np.full(self.shape, self.margin, np.float32)
        best = np.full(self.shape, np.inf, np.float32)
        self.owner = np.full(self.shape, -1, np.int16) if owner else None
        slabs = {}
        for n, part in enumerate(self.parts):
            rng = self.slab(part)
            if rng is None:
                continue
            d = part_d(part, self.points(rng)).astype(np.float32).reshape([b - a for a, b in rng])
            sl = tuple(slice(a, b) for a, b in rng)
            slabs[n] = (rng, d)
            grid[sl] = np.minimum(grid[sl], d)
            if owner:
                win = d < best[sl]
                best[sl] = np.where(win, d, best[sl])
                self.owner[sl] = np.where(win, n, self.owner[sl])
        for a, b, k in self.pairs:
            if k > 0 and a in slabs and b in slabs:
                self.join(grid, slabs[a], slabs[b], k, self.k_mode == "ext")
        self.grid = grid
        return self

    @staticmethod
    def join(grid, sa, sb, k, exterior=False):
        (ra, da), (rb, db) = sa, sb
        rng = [(max(x0, y0), min(x1, y1)) for (x0, x1), (y0, y1) in zip(ra, rb)]
        if any(hi <= lo for lo, hi in rng):
            return
        cut = lambda r, d: d[tuple(slice(lo - r0, hi - r0) for (lo, hi), (r0, _) in zip(rng, r))]  # noqa: E731
        sl = tuple(slice(lo, hi) for lo, hi in rng)
        grid[sl] = np.minimum(grid[sl], smin(cut(ra, da), cut(rb, db), k, exterior))

    def distances(self, points):
        """(parts, N) hard distance of each part to the (N, 3) points."""
        P = np.asarray(points, float).reshape(-1, 3)
        return np.stack([part_d(p, P) for p in self.parts])

    def d(self, points):
        """The body's field at arbitrary points (smooth pairs included, not truncated)."""
        dm = self.distances(points)
        out = dm.min(0)
        for a, b, k in self.pairs:
            out = np.minimum(out, smin(dm[a], dm[b], k, self.k_mode == "ext"))
        return out

    def ownership(self, points):
        """(index of the nearest part, smallest d, second smallest d) at the (N, 3) points: the weights mix the two when
        the gap is under the junction's k."""
        dm = self.distances(points)
        idx = dm.argmin(0)
        two = np.sort(dm, axis=0)[:2] if len(dm) > 1 else np.stack([dm[0], np.full(dm.shape[1], np.inf)])
        return idx, two[0], two[1]


def bone_class(bone):
    """"limb" for an arm / leg / wing / wheel bone (arm.L, thigh.R, leg3.upper, wing1.lower), else "trunk" (pelvis, spine.1, head,
    body, abdomen, tail.1, neck)."""
    return "limb" if bone.split(".")[0].rstrip("0123456789") in LIMB_BONES else "trunk"


def pair_k(a, b, voxel, height, k_scale, mode="base"):
    """The smooth-min width of two joined parts. `mode` (K_MODES): "hard" 0; "class" x CLASS_K of the two bones' classes; else base."""
    if mode == "hard":
        return 0.0
    k = k_scale * min(max(K_FRAC * min(a["r"], b["r"]), K_MIN_VOX * voxel), K_MAX_H * height)
    if mode == "class":
        k *= CLASS_K[tuple(sorted((bone_class(a["bone"]), bone_class(b["bone"]))))]
    return k


def field(parts, cuts=None, rig=("biped", ()), k=1.0, grid=GRID, owner=False, compute=True, thin="off", k_mode="base"):
    """The body's Field. `parts`: the spec rows [bone, kind, dims, at, material, opts]; `cuts`: cut_hull's json (by row index);
    `rig`: (family, extras), RF already scaled by the caller; k: scale of every junction's k (0: hard union); grid: voxels
    along the height. `thin` (PIPELINE 28.L10-7), for the parts under THIN_VOX voxels: "off" nothing, "inflate" fatten them
    (thin_inflation), "keep" leave them out of the field (their rows are in `Field.kept`: the caller builds them as polygons). `k_mode`: how the junctions' k is chosen
    (K_MODES, PIPELINE 29.L11-5)."""
    if k_mode not in K_MODES:
        raise ValueError(f"k_mode={k_mode}: {', '.join(K_MODES)}")
    body = normalize(parts, cuts, rig)
    if not body:
        raise ValueError("the spec has no body part")
    lo, hi = np.min([p["lo"] for p in body], axis=0), np.max([p["hi"] for p in body], axis=0)
    height = float(hi[2] - lo[2])
    voxel = height / grid
    shape = np.ceil((hi - lo) / voxel).astype(int) + 2 * PAD + 1
    fat = thin_inflation(body, voxel) if thin != "off" else {}
    if thin == "keep":
        body = [p for p in body if p["i"] not in fat]
    for p in body:
        if thin == "inflate" and fat.get(p["i"]):
            p["inflate"] = fat[p["i"]]
    family, extras = rig
    up = RF.parents(family, extras) if family in RF.FAMILIES else {}
    pairs = [(a, b, pair_k(body[a], body[b], voxel, height, k, k_mode))
             for a, b in itertools.combinations(range(len(body)), 2) if related(up, body[a]["bone"], body[b]["bone"])]
    f = Field(body, pairs, lo - PAD * voxel, voxel, shape, k, k_mode)
    f.kept = sorted(fat) if thin == "keep" else []
    return f.compute(owner) if compute else f


# ---------------------------------------------------------------- bones, weights, materials (PIPELINE 28.L10-5)
LIMB_RAMP = 0.15        # a limb's upper -> lower weight ramps over +-this share of its from -> knee -> to length
FREE_SCALE = 10.0       # ... of two parts that are not smooth-joined (siblings: legs of a spider)
BAND_SCALE = 14.0       # the mixing band of a smooth-joined pair, x its k (ablation: PIPELINE 28.L10-5)


def polyline_t(points, joints):
    """(segment, t, share): the nearest segment of the polyline `joints` (J, 3) to each of the (N, 3) points, the point's
    foot on it in [0, 1] and its arclength share of the whole polyline, in [0, 1]."""
    a, b = joints[:-1], joints[1:]
    e = b - a
    ln = np.linalg.norm(e, axis=1)
    w = points[:, None, :] - a[None]
    t = np.clip((w * e).sum(2) / np.maximum(ln * ln, 1e-18), 0, 1)
    seg = np.linalg.norm(w - t[..., None] * e, axis=2).argmin(1)
    t = t[np.arange(len(points)), seg]
    return seg, t, (np.cumsum(ln)[seg] - ln[seg] + t * ln[seg]) / ln.sum()


def part_bones(row, P, cols):
    """(M, B) bone weights of the (M, 3) points on one spec row: its bone; a limb with an upper / lower pair of bones
    ramps from the upper to the lower over +-LIMB_RAMP around the knee (build_unit.skin_part's 1 / .5 / 0 per ring); a chain
    takes the bone of its nearest segment."""
    bone, kind, _, _, _, opts = row
    opts = opts or {}
    out = np.zeros((len(P), len(cols)))
    if kind == "limb":
        pair = lathe_limb.limb_bones(bone, set(cols))
        if pair:
            joints = to_blender([opts["from"], lathe_limb.knee_of(opts), opts["to"]])
            _, _, share = polyline_t(P, joints)
            knee = np.linalg.norm(joints[1] - joints[0]) / (np.linalg.norm(joints[1] - joints[0]) + np.linalg.norm(joints[2] - joints[1]))
            up = np.clip(0.5 - (share - knee) / (2 * LIMB_RAMP), 0, 1)
            out[:, cols[pair[0]]], out[:, cols[pair[1]]] = up, 1 - up
            return out
    if kind == "chain" and opts.get("bones"):
        names = lathe_limb.chain_bones(bone, int(opts["bones"]))
        seg, _, _ = polyline_t(P, to_blender(lathe_limb.chain_joints(bone, int(opts["bones"]))))
        out[np.arange(len(P)), [cols[names[i]] for i in seg]] = 1.0
        return out
    out[:, cols.get(bone, cols.get("root", 0))] = 1.0     # a bone the rig lacks rides the root (union: a group with no bone)
    return out


def piece_d(q, P):
    """One piece's d, raised outside to its box's distance when that is larger: a facet's plane runs on far past the piece, and
    a mixing band wants the distance a point really is from the part (never used for the grid, which keeps the inside)."""
    d = EVAL[q["t"]](q, P)
    out = np.maximum(np.maximum(np.asarray(q["lo"], P.dtype) - P, P - np.asarray(q["hi"], P.dtype)), 0)
    return np.maximum(d, np.linalg.norm(out, axis=1))


def near_distances(field, P):
    """(parts, N) like Field.distances with piece_d for the pieces: not truncated, tighter outside, same on the surface."""
    out = []
    for part in field.parts:
        d = piece_d(part["pieces"][0], P)
        for q in part["pieces"][1:]:
            d = np.minimum(d, piece_d(q, P))
        for q in part["cut"]:
            d = np.maximum(d, EVAL[q["t"]](q, P))
        out.append(d)
    return np.stack(out)


def band_matrix(field, band_scale, free_scale):
    """(parts, parts) mixing band of every pair: pair_k x band_scale for the smooth-joined ones, x free_scale for the rest."""
    height = (field.shape[2] - 2 * PAD - 1) * field.voxel
    joined = {(a, b) for a, b, _ in field.pairs} | {(b, a) for a, b, _ in field.pairs}
    n = len(field.parts)
    k = [[pair_k(field.parts[a], field.parts[b], field.voxel, height, field.k_scale)
          * (band_scale if (a, b) in joined else free_scale) for b in range(n)] for a in range(n)]
    return np.maximum(k, 1e-9)


def weights(points, field, parts, rig, band_scale=BAND_SCALE, free_scale=FREE_SCALE):
    """(bone names, W (N, len(names))) skin weights of the (N, 3) points (Blender axes) on `field`'s body; rows sum to 1.
    `parts`: the spec rows the field was made from; `rig`: (family, extras). The owner is the part with the smallest d (weight
    1); every other part whose d is within its band of the owner's (band_matrix) adds exp(-gap / sigma), sigma = band / 2,
    faded to 0 at the band's edge by a smoothstep, so the skin is continuous across a junction and does not depend on the
    mesh's density."""
    P = np.asarray(points, float).reshape(-1, 3)
    names = [b[0] for b in RF.with_extras(*rig)]
    cols = {b: i for i, b in enumerate(names)}
    dm = near_distances(field, P)
    own = dm.argmin(0)
    bands = band_matrix(field, band_scale, free_scale)
    kept = lathe_limb.RIG
    lathe_limb.set_rig(*rig)
    try:
        W = np.zeros((len(P), len(names)))
        for m, part in enumerate(field.parts):
            gap = dm[m] - dm[own, np.arange(len(P))]
            s = np.clip(gap / bands[own, m], 0, 1)
            w = np.where(own == m, 1.0, np.exp(-2 * gap / bands[own, m]) * (1 - s * s * (3 - 2 * s)) * (s < 1))
            sel = w > 1e-3
            if sel.any():
                W[sel] += part_bones(parts[part["i"]], P[sel], cols) * w[sel][:, None]
    finally:
        lathe_limb.RIG = kept
    return names, W / W.sum(1, keepdims=True)


def materials(points, field, parts):
    """Material name of the part nearest to each of the (N, 3) points (build_unit's transfer_from_parts: the face's centroid)."""
    return [parts[field.parts[m]["i"]][4] for m in field.ownership(points)[0]]


def load(path):
    """The Field of a clay.sdf.json, ready to evaluate (d, ownership) or compute()."""
    return Field.from_json(json.loads(pathlib.Path(path).read_text()))


def index_to_world(idx, origin, voxel):
    """Grid index coordinates (openvdb points, fractional ok) -> world: origin + idx * voxel (PIPELINE 28.L10-2)."""
    return np.asarray(origin, float) + np.asarray(idx, float).reshape(-1, 3) * float(voxel)


def quads_to_tris(points, tris, quads):
    """(m, 3) triangles: openvdb's `tris` plus each quad cut along its shorter diagonal (the fatter triangles)."""
    points = np.asarray(points, float)
    tris = np.asarray(tris, np.int64).reshape(-1, 3)
    quads = np.asarray(quads, np.int64).reshape(-1, 4)
    if not len(quads):
        return tris
    p = points[quads]
    short02 = np.linalg.norm(p[:, 0] - p[:, 2], axis=1) <= np.linalg.norm(p[:, 1] - p[:, 3], axis=1)
    a = np.where(short02[:, None], quads[:, [0, 1, 2]], quads[:, [1, 2, 3]])
    b = np.where(short02[:, None], quads[:, [0, 2, 3]], quads[:, [1, 3, 0]])
    return np.concatenate([tris, a, b])


def stats(f, seconds):
    kinds = {}
    for p in f.parts:
        kinds[p["kind"]] = kinds.get(p["kind"], 0) + 1
    return {"parts": len(f.parts), "kinds": kinds, "fallback": [p["i"] for p in f.parts if not p["exact"]],
            "pieces": sum(len(p["pieces"]) for p in f.parts), "pairs": len(f.pairs), "shape": list(f.shape),
            "voxel": round(f.voxel, 5), "seconds": round(seconds, 3)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("spec")
    ap.add_argument("--grid", type=int, default=GRID, help="voxels along the height (64 / 96 / 128)")
    ap.add_argument("--k", type=float, default=1.0, help="scale of the junctions' k (0: hard union)")
    ap.add_argument("--k-mode", choices=K_MODES, default="base", help="how each junction's k is chosen (PIPELINE 29.L11-5)")
    ap.add_argument("--cuts", help="cuts.json of cut_hull (parts with cut: sheet, sheet profiles)")
    ap.add_argument("--out", help="the grid, .npy float32 (x, y, z)")
    ap.add_argument("--json", help="clay.sdf.json: parts + k + grid, for mesh_lint")
    ap.add_argument("--owner", action="store_true", help="also write <out>.owner.npy (nearest part per voxel)")
    a = ap.parse_args()
    doc = json.loads(pathlib.Path(a.spec).read_text())
    family = doc.get("rig", "biped")
    RF.scale_rig(family, doc.get("rig_measure"))
    cuts = json.loads(pathlib.Path(a.cuts).read_text()) if a.cuts else {}
    t0 = time.perf_counter()
    f = field([tuple(r) for r in doc["parts"]], cuts, (family, doc.get("bones") or ()), a.k, a.grid, a.owner, k_mode=a.k_mode)
    seconds = time.perf_counter() - t0
    if a.out:
        np.save(a.out, f.grid)
        if a.owner:
            np.save(str(pathlib.Path(a.out).with_suffix("")) + ".owner.npy", f.owner)
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(f.to_json()))
    print(json.dumps(stats(f, seconds)))


if __name__ == "__main__":
    main()
