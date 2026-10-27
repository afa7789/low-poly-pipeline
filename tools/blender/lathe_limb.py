"""Geometry of the `lathe` and `limb` part kinds, in spec axes (x right, y up, z forward), no bpy.

One definition for the four readers: build_unit.py makes the mesh from these rings, fit_spec.py
projects their points, preflight.py counts the triangles and bounds the box, cut_hull.py reads the
sheet profile. PIPELINE.md section 21.F2 documents the opts.

lathe  dims = (r, h) at = centre. A profile of radii revolved around the vertical axis through
       `at`: ring i sits at y = at.y - h/2 + i/(n-1)*h with x radius r*profile[i] and z radius
       x radius / squash. opts: profile (6-10 floats, bottom to top; default: the sheet strip, else
       DEFAULT_PROFILE), axis "front" | "left" (the sheet panel the strip is read from, default
       "front"), sides 6-8 (default 6), squash (x/z, default 1). Closed ends, caps are n-gons.
limb   dims = (r_top, r_knee, r_base), opts from/to (required), knee [frac, dx, dz, dy] (default
       [0.5, 0, 0, 0]: knee = from + frac*(to-from) + (dx, dy, dz)), sides 6-8 (default 6). Two
       tapered tubes sharing the knee ring, capped at both ends.
"""
import math

SIDES = 6
SIDES_RANGE = (6, 8)
PROFILE_RANGE = (6, 10)         # rings of a profile
SHEET_RINGS = 6                 # rings of a profile read from the sheet
DEFAULT_PROFILE = (0.6, 0.9, 1.0, 1.0, 0.85, 0.5)
PROFILE_MAX = 1.5               # a ring is at most this many times r
KNEE = (0.5, 0.0, 0.0, 0.0)
# upper segment word -> lower segment word in a bone name (leg1.upper/.lower, thigh/shin, arm/forearm)
PAIRS = (("upper", "lower"), ("thigh", "shin"), ("arm", "forearm"))


def sides_of(opts):
    return int(opts.get("sides", SIDES))


def rings_of(opts):
    """Rings of a lathe: the author's profile, else the sheet's (SHEET_RINGS)."""
    return len(opts["profile"]) if opts.get("profile") else SHEET_RINGS


def tris(kind, opts):
    """Triangles of a lathe or a limb (the ends are triangulated n-gons)."""
    n = sides_of(opts)
    rings = rings_of(opts) if kind == "lathe" else 3
    return 2 * n * (rings - 1) + 2 * (n - 2)


def bad_opts(kind, dims, opts):
    """Why a lathe or limb is outside the schema, or None."""
    n = opts.get("sides", SIDES)
    if not isinstance(n, int) or not SIDES_RANGE[0] <= n <= SIDES_RANGE[1]:
        return f"sides outside {SIDES_RANGE}"
    if kind == "limb":
        knee = opts.get("knee", KNEE)
        if "from" not in opts or "to" not in opts or len(dims) != 3:
            return "a limb needs from, to and dims (r_top, r_knee, r_base)"
        if not (3 <= len(knee) <= 4 and all(isinstance(v, (int, float)) for v in knee)
                and 0.15 <= knee[0] <= 0.85):
            return "knee is [frac 0.15-0.85, dx, dz, optional dy]"
        return None
    prof = opts.get("profile")
    if len(dims) != 2 or "from" in opts or "to" in opts or "rot" in opts:
        return "a lathe stands upright: dims (r, h), no from, to or rot"
    if opts.get("axis", "front") not in ("front", "left"):
        return "axis is front or left"
    if prof is not None and not (PROFILE_RANGE[0] <= len(prof) <= PROFILE_RANGE[1]
                                 and all(isinstance(v, (int, float)) and 0.05 <= v <= PROFILE_MAX for v in prof)):
        return f"profile is {PROFILE_RANGE[0]}-{PROFILE_RANGE[1]} radii (x r) in 0.05-{PROFILE_MAX}"
    squash = opts.get("squash", 1.0)
    return None if isinstance(squash, (int, float)) and 0.5 <= squash <= 2.0 else "squash is x/z in 0.5-2"


def ngon(c, u, v, r, n, phase=0.0):
    """n points of a circle of radius r about c, in the plane spanned by the unit vectors u and v."""
    return [tuple(c[i] + r * (math.cos(phase + 2 * math.pi * k / n) * u[i]
                              + math.sin(phase + 2 * math.pi * k / n) * v[i]) for i in range(3))
            for k in range(n)]


def lathe_rings(dims, at, opts, sheet=None):
    """[ring] bottom to top, each n points (x, y, z) of the lathe. `sheet` is the profile read from
    the sheet (cut_hull.lathe_profiles), used when opts has none."""
    r, h = dims
    prof = opts.get("profile") or sheet or DEFAULT_PROFILE
    n, squash = sides_of(opts), float(opts.get("squash", 1.0))
    out = []
    for i, p in enumerate(prof):
        y = at[1] - h / 2 + i / (len(prof) - 1) * h
        rx = r * p
        out.append([(at[0] + x, y, at[2] + z) for x, _, z in
                    ((rx * math.cos(a), 0, rx / squash * math.sin(a)) for a in
                     (2 * math.pi * k / n for k in range(n)))])
    return out


def unit(v):
    m = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / m for c in v)


def sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def knee_of(opts):
    """The knee point of a limb in spec axes."""
    a, b = opts["from"], opts["to"]
    f, dx, dz, *rest = opts.get("knee", KNEE)
    shift = (dx, rest[0] if rest else 0.0, dz)
    return tuple(a[i] + f * (b[i] - a[i]) + shift[i] for i in range(3))


def limb_rings(dims, opts):
    """[ring at from, ring at the knee, ring at to] of a limb; the knee ring lies in the plane that
    bisects the two segments so the tubes meet without a gap."""
    a, b, k = tuple(opts["from"]), tuple(opts["to"]), knee_of(opts)
    d1, d2 = unit(sub(k, a)), unit(sub(b, k))
    mid = unit(tuple(d1[i] + d2[i] for i in range(3)))
    n = sides_of(opts)
    rings = []
    for c, normal, r in ((a, d1, dims[0]), (k, mid, dims[1]), (b, d2, dims[2])):
        ref = (0.0, 1.0, 0.0) if abs(normal[1]) < 0.95 else (1.0, 0.0, 0.0)
        u = unit(cross(ref, normal))
        rings.append(ngon(c, u, cross(normal, u), r, n))
    return rings


def limb_bones(bone, known):
    """(upper bone, lower bone) a limb on `bone` is skinned to, or None when the rig has no pair:
    leg1.upper / leg1.lower, thigh.L / shin.L, arm.L / forearm.L."""
    tokens = bone.split(".")
    for up, low in PAIRS:
        for have, want in ((up, low), (low, up)):
            if have in tokens:
                other = ".".join(want if t == have else t for t in tokens)
                if other in known:
                    return (bone, other) if have == up else (other, bone)
    return None


def half_extent(kind, dims, at, opts):
    """((lo), (hi)) box of the kind around its geometry, in spec axes (preflight.bbox)."""
    pts = ([p for ring in lathe_rings(dims, at, opts) for p in ring] if kind == "lathe"
           else [p for ring in limb_rings(dims, opts) for p in ring])
    return (tuple(min(p[i] for p in pts) for i in range(3)),
            tuple(max(p[i] for p in pts) for i in range(3)))
