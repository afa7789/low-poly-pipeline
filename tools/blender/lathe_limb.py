"""Geometry of the `lathe`, `limb` and `chain` part kinds, in spec axes (x right, y up, z forward), no bpy.

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
chain  bone = the first bone `prefix.k` of a rig chain, dims = (r0..rN) the radius at each joint of
       the N bones prefix.k..prefix.k+N-1 (head to tail; joint i is the head of bone i, joint N the
       tail of the last), or one number = the widest radius, the rest read from the sheet
       (cut_hull.chain_radii) else CHAIN_TAPER. `at` is ignored: the bones place the rings. opts
       bones N (1-8, required), sides 6-8, profile_axis "left" | "front" (the sheet panel read).
       One ring per joint, ring i skinned to bone i (the last ring to the last bone), n-gon caps.
plate  dims = (w, h, t) around `at`, opts axis "front" | "left" | "top" (the sheet panel the outline is
       read from, default "front"; the plate's normal is z, x, y), profile (3-8 [u, v] points in 0-1 of
       w and h, default: the sheet strip of the part's box, else DEFAULT_PLATE), bevel 0-0.3 (the faces
       shrink by that fraction), rot allowed. front: u = x, v = y; left: u = z, v = y; top: u = x,
       v = z (forward). The polygon extruded t along the normal: two faces and a band of quads.
"""
import math

SIDES = 6
SIDES_RANGE = (6, 8)
PROFILE_RANGE = (6, 10)         # rings of a profile
SHEET_RINGS = 6                 # rings of a profile read from the sheet
DEFAULT_PROFILE = (0.6, 0.9, 1.0, 1.0, 0.85, 0.5)
PROFILE_MAX = 1.5               # a ring is at most this many times r
KNEE = (0.5, 0.0, 0.0, 0.0)
PLATE_AXES = ("front", "left", "top")
PLATE_PTS = (3, 8)              # vertices of a plate outline (cut_hull.LIMIT reads at most 8)
PLATE_BEVEL_MAX = 0.3
DEFAULT_PLATE = ((0.5, 0.0), (1.0, 0.25), (1.0, 0.75), (0.5, 1.0), (0.0, 0.75), (0.0, 0.25))
# upper segment word -> lower segment word in a bone name (leg1.upper/.lower, thigh/shin, arm/forearm)
PAIRS = (("upper", "lower"), ("thigh", "shin"), ("arm", "forearm"))
CHAIN_BONES = (1, 8)            # bones of a chain
CHAIN_R = (0.01, 3.0)           # a joint radius, metres
CHAIN_TAPER = 0.35              # radius at the tail, as a fraction of the head's, when the sheet gives none
RIG = ("biped", ())             # (family, extra bones): where a chain finds its joints (set_rig)


def set_rig(family, extras=None):
    """The rig the chains of this process are placed on; every reader of a spec sets it once."""
    global RIG
    RIG = (family, tuple(tuple(e) for e in extras or ()))


def sides_of(opts):
    return int(opts.get("sides", SIDES))


def rings_of(opts):
    """Rings of a lathe: the author's profile, else the sheet's (SHEET_RINGS)."""
    return len(opts["profile"]) if opts.get("profile") else SHEET_RINGS


def tris(kind, opts):
    """Triangles of a lathe or a limb (the ends are triangulated n-gons)."""
    if kind == "plate":
        n = len(opts["profile"]) if opts.get("profile") else PLATE_PTS[1]
        return 2 * (n - 2) + 2 * n * (3 if opts.get("bevel") else 1)
    n = sides_of(opts)
    rings = {"lathe": rings_of, "chain": lambda o: int(o["bones"]) + 1}.get(kind, lambda o: 3)(opts)
    return 2 * n * (rings - 1) + 2 * (n - 2)


def bad_chain(bone, dims, opts):
    """Why a chain part is outside the schema, or None."""
    n = opts.get("bones")
    if not isinstance(n, int) or not CHAIN_BONES[0] <= n <= CHAIN_BONES[1]:
        return f"a chain needs opts bones in {CHAIN_BONES}"
    if len(dims) not in (1, n + 1) or not all(isinstance(v, (int, float)) and CHAIN_R[0] <= v <= CHAIN_R[1] for v in dims):
        return f"a chain takes {n + 1} joint radii (or one) in {CHAIN_R} metres"
    if any(k in opts for k in ("from", "to", "rot")) or opts.get("profile_axis", "left") not in ("front", "left"):
        return "a chain follows its bones: no from, to or rot; profile_axis is front or left"
    try:
        chain_joints(bone, n)
    except ValueError as e:
        return str(e)
    return None


def bad_opts(kind, dims, opts, bone=None):
    """Why a lathe, limb, chain or plate is outside the schema, or None."""
    if kind == "plate":
        return bad_plate(dims, opts)
    n = opts.get("sides", SIDES)
    if not isinstance(n, int) or not SIDES_RANGE[0] <= n <= SIDES_RANGE[1]:
        return f"sides outside {SIDES_RANGE}"
    if kind == "chain":
        return bad_chain(bone, dims, opts)
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


def bad_plate(dims, opts):
    prof, bevel = opts.get("profile"), opts.get("bevel", 0)
    if len(dims) != 3 or not all(isinstance(v, (int, float)) and v > 0 for v in dims) or "from" in opts or "to" in opts:
        return "a plate is dims (w, h, t) > 0 around at: no from or to"
    if opts.get("axis", "front") not in PLATE_AXES:
        return "plate axis is front, left or top"
    if prof is not None and not (isinstance(prof, list) and PLATE_PTS[0] <= len(prof) <= PLATE_PTS[1]
                                 and all(isinstance(q, list) and len(q) == 2
                                         and all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in q) for q in prof)):
        return f"plate profile is {PLATE_PTS[0]}-{PLATE_PTS[1]} points [u, v] in 0-1"
    if isinstance(bevel, bool) or not isinstance(bevel, (int, float)) or not 0 <= bevel <= PLATE_BEVEL_MAX:
        return f"plate bevel is 0-{PLATE_BEVEL_MAX}"
    return None


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


def chain_bones(bone, n):
    """[prefix.k, .., prefix.k+n-1] for a chain starting at the bone `prefix.k`, or None."""
    prefix, _, k = bone.rpartition(".")
    return [f"{prefix}.{int(k) + i}" for i in range(n)] if prefix and k.isdigit() else None


def chain_joints(bone, n):
    """The n+1 joints (head of each bone, tail of the last) of the chain on `bone`, spec axes, from
    the rig set by set_rig. ValueError when the rig lacks a bone of it."""
    import rig_families
    names = chain_bones(bone, n)
    table = {b[0]: b for b in rig_families.with_extras(*RIG)}
    if not names or any(b not in table for b in names):
        raise ValueError(f"{bone} + {n - 1} more is not a chain of the {RIG[0]} rig")
    return [table[b][2] for b in names] + [table[names[-1]][3]]


def chain_radii(dims, opts, sheet=None):
    """The n+1 joint radii: the author's, else dims[0] times the sheet's profile, else a taper."""
    count = int(opts["bones"]) + 1
    if len(dims) == count:
        return list(dims)
    prof = sheet if sheet and len(sheet) == count else [1 - (1 - CHAIN_TAPER) * i / (count - 1) for i in range(count)]
    return [dims[0] * v for v in prof]


def chain_rings(bone, dims, opts, sheet=None):
    """[ring per joint], head to tail: an n-gon of the joint's radius in the plane that bisects the
    two bones meeting there (the end rings take their own bone's direction)."""
    joints = chain_joints(bone, int(opts["bones"]))
    segs = [unit(sub(b, a)) for a, b in zip(joints, joints[1:])]
    dirs = [segs[0]] + [unit(tuple(a[i] + b[i] for i in range(3))) for a, b in zip(segs, segs[1:])] + [segs[-1]]
    n = sides_of(opts)
    phase = 0.0 if n % 4 == 0 else math.pi / (2 * n)     # a ring reads as wide from the side as from above
    rings = []
    for c, d, r in zip(joints, dirs, chain_radii(dims, opts, sheet)):
        ref = (0.0, 1.0, 0.0) if abs(d[1]) < 0.95 else (1.0, 0.0, 0.0)
        u = unit(cross(ref, d))
        rings.append(ngon(c, u, cross(d, u), r, n, phase))
    return rings


def half_extent(kind, dims, at, opts, bone=None):
    """((lo), (hi)) box of the kind around its geometry, in spec axes (preflight.bbox)."""
    rings = {"lathe": lambda: lathe_rings(dims, at, opts), "chain": lambda: chain_rings(bone, dims, opts),
             "plate": lambda: plate_rings(dims, at, opts)}
    pts = [p for ring in rings.get(kind, lambda: limb_rings(dims, opts))() for p in ring]
    return (tuple(min(p[i] for p in pts) for i in range(3)),
            tuple(max(p[i] for p in pts) for i in range(3)))


def plate_rings(dims, at, opts, sheet=None):
    """[ring] of a plate, each the profile polygon at one depth along the normal (before opts rot):
    2 rings, or 4 with a bevel (the cap rings are shrunk toward the centroid and sit at the faces).
    `sheet` is the profile read from the sheet (cut_hull.plate_profiles), used when opts has none."""
    w, h, t = dims
    prof = opts.get("profile") or sheet or DEFAULT_PLATE
    axis, bevel = opts.get("axis", "front"), float(opts.get("bevel", 0.0))
    cu, cv = (sum(q[i] for q in prof) / len(prof) for i in (0, 1))
    layers = [(-t / 2, 1.0), (t / 2, 1.0)]
    if bevel:
        layers = [(-t / 2, 1 - bevel), (-t / 2 * (1 - bevel), 1.0), (t / 2 * (1 - bevel), 1.0), (t / 2, 1 - bevel)]
    place = {"front": lambda a, b, d: (a, b, d), "left": lambda a, b, d: (d, b, a), "top": lambda a, b, d: (a, d, b)}[axis]
    return [[tuple(at[i] + c for i, c in enumerate(place((cu + (q[0] - cu) * s - 0.5) * w,
                                                         (cv + (q[1] - cv) * s - 0.5) * h, d)))
             for q in prof] for d, s in layers]
