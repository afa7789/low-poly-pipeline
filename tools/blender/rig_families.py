"""Rig families for Castle Fight units. Bones are data, so a new body plan is a new
entry here and not a change to the builder.

Every family uses the same convention so animation clips can be shared inside the
family, and the clips themselves are derived from the bone names:

  root                         ground anchor (hovering bodies bob on it)
  <chain>.<n>                  spines, tails, necks, tentacles: they wave
  head                         head / turret / cockpit
  leg<N>.upper/.lower          each leg, numbered from the front-left, clockwise: they walk
  wing<N>.upper/.lower         wing1 on the left (+x), wing2 on the right: they flap
  wheel<N>                     they spin
  arm.L/R, thigh.L/R ...       biped limbs: they take the biped's hand-keyed clips
  rider.*                      a rider's body on a mount
  jaw, abdomen                 optional extras

A unit's spec picks the family with {"rig": <name in FAMILIES>}; families are composed
from the parts below (a drake is a quadruped body + neck + wings, a mounted unit is a
quadruped + rider). A spec may add its own prop bones with "bones" (with_extras), so a
mast, a second head or a counterweight never needs a family of its own.
"""
import math
import sys

# name, parent, head, tail  (x right, y up, z forward)
BIPED = [
    ("root", None, (0, 0, 0), (0, 0.3, 0)),
    ("pelvis", "root", (0, 1.20, 0), (0, 1.50, 0)),
    ("spine", "pelvis", (0, 1.50, 0), (0, 2.16, 0)),
    ("head", "spine", (0, 2.16, 0), (0, 2.72, 0)),
    ("arm.L", "spine", (0.78, 2.02, 0), (0.78, 1.40, 0)),
    ("forearm.L", "arm.L", (0.78, 1.40, 0), (0.78, 0.90, 0)),
    ("arm.R", "spine", (-0.78, 2.02, 0), (-0.78, 1.40, 0)),
    ("forearm.R", "arm.R", (-0.78, 1.40, 0), (-0.78, 0.90, 0)),
    ("thigh.L", "pelvis", (0.28, 1.18, 0), (0.28, 0.56, 0)),
    ("shin.L", "thigh.L", (0.28, 0.56, 0), (0.28, 0.10, 0)),
    ("foot.L", "shin.L", (0.28, 0.10, 0), (0.28, 0.06, 0.55)),
    ("thigh.R", "pelvis", (-0.28, 1.18, 0), (-0.28, 0.56, 0)),
    ("shin.R", "thigh.R", (-0.28, 0.56, 0), (-0.28, 0.10, 0)),
    ("foot.R", "shin.R", (-0.28, 0.10, 0), (-0.28, 0.06, 0.55)),
]


def _legs(n, parent, body_y, body_r, reach, up=0.55, phase=0.0, arch=None):
    """A ring of legs around the body: the generic arthropod plan. `arch` lifts the knee
    that far ABOVE the hip (femur up and out, tibia down to the ground) instead of
    letting it sag below it."""
    bones = []
    for i in range(n):
        a = phase + 2 * math.pi * i / n
        hx, hz = math.cos(a) * body_r, math.sin(a) * body_r
        kr = body_r + reach * (0.55 if arch is None else 0.4)
        kx, kz = math.cos(a) * kr, math.sin(a) * kr
        ky = body_y - up * 0.45 if arch is None else body_y + arch
        fx, fz = math.cos(a) * (body_r + reach), math.sin(a) * (body_r + reach)
        tag = f"leg{i + 1}"
        bones += [
            (f"{tag}.upper", parent, (hx, body_y, hz), (kx, ky, kz)),
            (f"{tag}.lower", f"{tag}.upper", (kx, ky, kz), (fx, 0.04, fz)),
        ]
    return bones


SPIDER = ([("root", None, (0, 0, 0), (0, 0.25, 0)),
           # the thorax lies along the body, not up it: a spider is long and low
           ("body", "root", (0, 0.60, -0.15), (0, 0.62, 0.35)),
           ("head", "body", (0, 0.58, 0.35), (0, 0.52, 0.72)),
           ("abdomen", "body", (0, 0.66, -0.15), (0, 0.74, -0.85))]
          + _legs(8, "body", 0.60, 0.34, 0.78, phase=math.pi / 8))

# same bones as SPIDER, legs arched like the n01N sheet: the knee stands 0.55 above the
# back line of the body and the shin comes down to the floor
SPIDER_HIGH = SPIDER[:4] + _legs(8, "body", 0.60, 0.34, 0.78, phase=math.pi / 8, arch=0.55)

SPIDERS = ("spider", "spider_high")
SPIDER_H = 0.74   # the fixed spiders' height in metres: the H a sheet measurement is a fraction of


def _legs_measured(by, hip_r, knee_r, knee_y, foot_r, phase=math.pi / 8):
    """The ring of 8 legs from measures: hip at (hip_r, by), knee at (knee_r, knee_y), foot at foot_r."""
    bones = []
    for i in range(8):
        a = phase + 2 * math.pi * i / 8
        c, s = math.cos(a), math.sin(a)
        hip, knee, foot = (c * hip_r, by, s * hip_r), (c * knee_r, knee_y, s * knee_r), (c * foot_r, 0.04, s * foot_r)
        bones += [(f"leg{i + 1}.upper", "body", hip, knee), (f"leg{i + 1}.lower", f"leg{i + 1}.upper", knee, foot)]
    return bones


def scale_spider(family, m):
    """Replace FAMILIES[family] (spider or spider_high) by a skeleton built from the sheet's
    measures (silhouette.measure_spider, fractions of H) and return it. Same bones and names as
    the fixed table, so clips and retargets keep working; the top stays SPIDER_H."""
    H = SPIDER_H
    by = H * (m["body_under"] + 1) / 2                         # the body bone: middle of the shell
    zs = min(max(m["body_len"] * H / 1.57, 0.3), 1.5)          # the fixed thorax+head+abdomen run 1.57 long
    knee_y = H * max(m["knee_h"], m["body_under"] / 2)         # a lower leg never shorter than half the belly height
    table = [("root", None, (0, 0, 0), (0, 0.25, 0)),
             ("body", "root", (0, by, -0.15 * zs), (0, by + 0.02, 0.35 * zs)),
             ("head", "body", (0, by - 0.02, 0.35 * zs), (0, by - 0.08, 0.72 * zs)),
             ("abdomen", "body", (0, by + 0.06, -0.15 * zs), (0, H, -0.85 * zs))]
    table += _legs_measured(by, 0.9 * m["body_r"] * H, m["knee_r"] * H, knee_y, m["foot_r"] * H)
    FAMILIES[family] = table
    _drop_caches()
    return table


def spider_leg_len(m):
    """hip -> knee -> foot length of a scaled spider's leg, fractions of H."""
    hip, by = 0.9 * m["body_r"], (1 + m["body_under"]) / 2
    kh = max(m["knee_h"], m["body_under"] / 2)
    return math.hypot(m["knee_r"] - hip, by - kh) + math.hypot(m["foot_r"] - m["knee_r"], kh)


def _drop_caches():
    """rig_poses caches its rest matrices per family name: a replaced table must not reuse them."""
    mod = sys.modules.get("rig_poses")
    if mod is not None:
        mod._rest.cache_clear()


QUADRUPED = [("root", None, (0, 0, 0), (0, 0.3, 0)),
             ("spine.1", "root", (0, 1.00, -0.55), (0, 1.10, 0.00)),
             ("spine.2", "spine.1", (0, 1.10, 0.00), (0, 1.10, 0.55)),
             ("head", "spine.2", (0, 1.10, 0.55), (0, 1.20, 0.95)),
             ("tail.1", "spine.1", (0, 1.00, -0.55), (0, 0.95, -0.95)),
             ("tail.2", "tail.1", (0, 0.95, -0.95), (0, 0.90, -1.30))]
QUADRUPED += [("leg1.upper", "spine.2", (0.32, 1.00, 0.45), (0.36, 0.55, 0.50)),
              ("leg1.lower", "leg1.upper", (0.36, 0.55, 0.50), (0.36, 0.06, 0.50)),
              ("leg2.upper", "spine.2", (-0.32, 1.00, 0.45), (-0.36, 0.55, 0.50)),
              ("leg2.lower", "leg2.upper", (-0.36, 0.55, 0.50), (-0.36, 0.06, 0.50)),
              ("leg3.upper", "spine.1", (0.32, 1.00, -0.45), (0.36, 0.55, -0.50)),
              ("leg3.lower", "leg3.upper", (0.36, 0.55, -0.50), (0.36, 0.06, -0.50)),
              ("leg4.upper", "spine.1", (-0.32, 1.00, -0.45), (-0.36, 0.55, -0.50)),
              ("leg4.lower", "leg4.upper", (-0.36, 0.55, -0.50), (-0.36, 0.06, -0.50))]

# the head rides on the front of the chain (spine.1's head), so it stays on the body when the chain bends
SERPENT = [("root", None, (0, 0, 0), (0, 0.2, 0)), ("head", "spine.1", (0, 0.42, 0.33), (0, 0.50, 0.75))]
SERPENT += [(f"spine.{i}", "root" if i == 1 else f"spine.{i - 1}",
             (0, 0.50 - 0.08 * i, 0.55 - 0.22 * i), (0, 0.48 - 0.08 * i, 0.33 - 0.22 * i))
            for i in range(1, 9)]
SERPENT = [SERPENT[0]] + SERPENT[2:] + [SERPENT[1]]

VEHICLE = [("root", None, (0, 0, 0), (0, 0.2, 0)),
           ("hull", "root", (0, 0.35, -0.55), (0, 0.45, 0.55)),
           ("head", "hull", (0, 0.62, 0.10), (0, 0.62, 0.60)),
           ("wheel1", "hull", (0.42, 0.30, 0.38), (0.56, 0.30, 0.38)),
           ("wheel2", "hull", (-0.42, 0.30, 0.38), (-0.56, 0.30, 0.38)),
           ("wheel3", "hull", (0.42, 0.30, -0.38), (0.56, 0.30, -0.38)),
           ("wheel4", "hull", (-0.42, 0.30, -0.38), (-0.56, 0.30, -0.38))]


def _chain(prefix, parent, start, step, n, first=1):
    """n bones prefix.first.. laid head-to-tail from `start`, each `step` long."""
    out, at = [], start
    for i in range(first, first + n):
        tip = tuple(at[k] + step[k] for k in range(3))
        out.append((f"{prefix}.{i}", parent if i == first else f"{prefix}.{i - 1}", at, tip))
        at = tip
    return out


def _wings(parent, root, span, lift=0.25):
    """wing1 on +x, wing2 mirrored on -x, each an upper and lower spar."""
    out = []
    for n, side in ((1, 1), (2, -1)):
        x0, y0, z0 = root
        elbow = (side * (abs(x0) + span * 0.5), y0 + lift, z0 - 0.10)
        tip = (side * (abs(x0) + span), y0 + lift * 0.4, z0 - 0.35)
        out += [(f"wing{n}.upper", parent, (side * abs(x0), y0, z0), elbow),
                (f"wing{n}.lower", f"wing{n}.upper", elbow, tip)]
    return out


def _upper_body(parent, base, prefix=""):
    """A torso, head and two arms standing on `base`: the top half of a biped."""
    x, y, z = base
    sp = f"{prefix}spine"
    return [(sp, parent, (x, y, z), (x, y + 0.66, z)),
            (f"{prefix}head", sp, (x, y + 0.66, z), (x, y + 1.22, z)),
            (f"{prefix}arm.L", sp, (x + 0.78, y + 0.52, z), (x + 0.78, y - 0.10, z)),
            (f"{prefix}forearm.L", f"{prefix}arm.L", (x + 0.78, y - 0.10, z), (x + 0.78, y - 0.60, z)),
            (f"{prefix}arm.R", sp, (x - 0.78, y + 0.52, z), (x - 0.78, y - 0.10, z)),
            (f"{prefix}forearm.R", f"{prefix}arm.R", (x - 0.78, y - 0.10, z), (x - 0.78, y - 0.60, z))]


def _rider(parent, seat, scale=0.55):
    """A smaller seated rider (rider.spine, rider.head, rider.arm/forearm.L/R)."""
    def place(point):
        return tuple(seat[k] + point[k] * scale for k in range(3))
    return [(n, p, place(h), place(t))
            for n, p, h, t in _upper_body(parent, (0, 0, 0), prefix="rider.")]


def _without(table, names):
    return [b for b in table if b[0] not in names]


_QUAD_BODY = _without(QUADRUPED, {"head", "tail.1", "tail.2"})

DRAKE = (_QUAD_BODY
         + _chain("neck", "spine.2", (0, 1.10, 0.55), (0, 0.22, 0.18), 2)
         + [("head", "neck.2", (0, 1.54, 0.91), (0, 1.56, 1.30)),
            ("jaw", "head", (0, 1.48, 0.95), (0, 1.40, 1.26))]
         + _chain("tail", "spine.1", (0, 1.00, -0.55), (0, -0.05, -0.40), 3)
         + _wings("spine.2", (0.30, 1.30, 0.20), 1.30))

HARPY = BIPED + _wings("spine", (0.25, 2.00, -0.12), 1.10)

WYRM = (_without(SERPENT, {f"spine.{i}" for i in (7, 8)})
        + _wings("spine.1", (0.20, 0.62, 0.30), 0.90))

MOUNTED = QUADRUPED + _rider("spine.2", (0, 1.25, 0.05))
MOUNTED_FLYER = DRAKE + _rider("spine.2", (0, 1.30, 0.05))

NAGA = ([("root", None, (0, 0, 0), (0, 0.2, 0))]
        + _chain("tail", "root", (0, 0.30, 0.10), (0, -0.04, -0.38), 6)
        + _upper_body("root", (0, 0.40, 0.10)))

CENTAUR = (_without(QUADRUPED, {"head"})
           + [("spine.3", "spine.2", (0, 1.10, 0.55), (0, 1.80, 0.60))]
           + [b for b in _upper_body("spine.3", (0, 1.80, 0.60)) if b[0] != "spine"])
CENTAUR = [(n, "spine.3" if p == "spine" else p, h, t) for n, p, h, t in CENTAUR]

WRAITH = ([("root", None, (0, 0, 0), (0, 0.3, 0)),
           ("base", "root", (0, 0.20, 0), (0, 1.20, 0))]
          + _upper_body("base", (0, 1.20, 0)))

POD = ([("root", None, (0, 0, 0), (0, 0.3, 0)),
        ("body", "root", (0, 0.90, 0), (0, 1.40, 0))]
       + _chain("stalk", "body", (0, 1.40, 0), (0, 0.35, -0.05), 2)
       + [b for n in (1, 2, 3) for b in _chain(
           f"tendril{n}", "body",
           (0.25 * math.cos(2 * math.pi * n / 3), 0.90, 0.25 * math.sin(2 * math.pi * n / 3)),
           (0.05 * math.cos(2 * math.pi * n / 3), -0.35, 0.05 * math.sin(2 * math.pi * n / 3)), 2)])

SHARD = ([("root", None, (0, 0, 0), (0, 0.3, 0)),
          ("body", "root", (0, 1.30, -0.30), (0, 1.40, 0.40))]
         + _wings("body", (0.15, 1.40, 0.05), 0.90, lift=0.15)
         + [(f"plate.{i}", "body", (0, 1.50, 0.30 - 0.25 * i), (0, 1.75, 0.20 - 0.25 * i))
            for i in (1, 2, 3)]
         + _chain("tail", "body", (0, 1.30, -0.30), (0, -0.05, -0.40), 1))

TRACKED = [("root", None, (0, 0, 0), (0, 0.2, 0)),
           ("hull", "root", (0, 0.40, -0.55), (0, 0.50, 0.55)),
           ("head", "hull", (0, 0.70, 0.00), (0, 0.70, 0.45)),
           ("track.L", "hull", (0.45, 0.22, -0.60), (0.45, 0.22, 0.60)),
           ("track.R", "hull", (-0.45, 0.22, -0.60), (-0.45, 0.22, 0.60)),
           ("arm.L", "hull", (0.30, 0.55, 0.50), (0.35, 0.40, 0.95)),
           ("arm.R", "hull", (-0.30, 0.55, 0.50), (-0.35, 0.40, 0.95))]

WALKER = (_without(BIPED, {"spine", "arm.L", "forearm.L", "arm.R", "forearm.R", "head"})
          + [("head", "pelvis", (0, 1.50, -0.10), (0, 1.60, 0.40)),
             ("barrel.L", "head", (0.25, 1.65, 0.20), (0.35, 1.95, 0.90)),
             ("barrel.R", "head", (-0.25, 1.65, 0.20), (-0.35, 1.95, 0.90))])

AIRCRAFT = [("root", None, (0, 0, 0), (0, 0.3, 0)),
            ("hull", "root", (0, 2.60, -0.90), (0, 2.60, 0.90)),
            ("gondola", "hull", (0, 1.90, -0.40), (0, 1.90, 0.40)),
            ("prop", "hull", (0, 2.60, -0.90), (0, 2.60, -1.20)),
            ("rudder", "hull", (0, 2.70, -0.80), (0, 3.10, -1.10))]

SLED = ([("root", None, (0, 0, 0), (0, 0.2, 0))]
        + _chain("spine", "root", (0, 0.35, -0.80), (0, 0.0, 0.38), 4)
        + [("head", "spine.4", (0, 0.35, 0.72), (0, 0.40, 1.05))])

HYDRA = (_without(SLED, {"head"})
         + [b for n, x in ((1, 0.30), (2, 0.0), (3, -0.30)) for b in _chain(
             f"neck{n}", "spine.4", (x * 0.5, 0.40, 0.70), (x * 0.25, 0.30, 0.15), 3)])

CREW = [("root", None, (0, 0, 0), (0, 0.2, 0)),
        ("cradle", "root", (0, 0.35, -0.40), (0, 0.45, 0.30)),
        ("barrel", "cradle", (0, 0.55, 0.00), (0, 0.80, 0.90)),
        ("thigh.L", "cradle", (0.30, 0.45, -0.30), (0.30, 0.25, -0.30)),
        ("shin.L", "thigh.L", (0.30, 0.25, -0.30), (0.30, 0.05, -0.30)),
        ("thigh.R", "cradle", (-0.30, 0.45, -0.30), (-0.30, 0.25, -0.30)),
        ("shin.R", "thigh.R", (-0.30, 0.25, -0.30), (-0.30, 0.05, -0.30))]

CRAWLER = ([("root", None, (0, 0, 0), (0, 0.25, 0)),
            ("body", "root", (0, 0.55, -0.20), (0, 0.58, 0.25)),
            ("head", "body", (0, 0.60, 0.25), (0, 0.62, 0.55))]
           + _legs(4, "body", 0.55, 0.28, 0.70, phase=math.pi / 4))

CRUSTACEAN = ([("root", None, (0, 0, 0), (0, 0.25, 0)),
               ("body", "root", (0, 0.45, -0.25), (0, 0.48, 0.30)),
               ("head", "body", (0, 0.48, 0.30), (0, 0.46, 0.55))]
              + _legs(6, "body", 0.45, 0.30, 0.60, phase=math.pi / 6)
              + [b for side, x in (("L", 1), ("R", -1)) for b in (
                  (f"claw.{side}", "body", (x * 0.25, 0.50, 0.35), (x * 0.40, 0.55, 0.80)),
                  (f"pincer.{side}", f"claw.{side}", (x * 0.40, 0.55, 0.80), (x * 0.45, 0.55, 1.10)))]
              + _chain("tail", "body", (0, 0.45, -0.25), (0, 0.02, -0.30), 3))

BIRD = ([("root", None, (0, 0, 0), (0, 0.3, 0)),
         ("spine.1", "root", (0, 1.00, -0.35), (0, 1.10, 0.10)),
         ("spine.2", "spine.1", (0, 1.10, 0.10), (0, 1.20, 0.40))]
        + _chain("neck", "spine.2", (0, 1.20, 0.40), (0, 0.20, 0.12), 2)
        + [("head", "neck.2", (0, 1.60, 0.64), (0, 1.62, 0.95))]
        + [("leg1.upper", "spine.1", (0.22, 1.00, 0.00), (0.25, 0.55, 0.08)),
           ("leg1.lower", "leg1.upper", (0.25, 0.55, 0.08), (0.25, 0.05, 0.10)),
           ("leg2.upper", "spine.1", (-0.22, 1.00, 0.00), (-0.25, 0.55, 0.08)),
           ("leg2.lower", "leg2.upper", (-0.25, 0.55, 0.08), (-0.25, 0.05, 0.10))]
        + _wings("spine.2", (0.25, 1.25, 0.15), 1.40)
        + _chain("tail", "spine.1", (0, 1.00, -0.35), (0, -0.05, -0.40), 3))

BIRD_RIDER = BIRD + _rider("spine.2", (0, 1.35, 0.10))

RAY = ([("root", None, (0, 0, 0), (0, 0.3, 0)),
        ("body", "root", (0, 1.20, -0.30), (0, 1.22, 0.45))]
       + _wings("body", (0.30, 1.22, 0.10), 1.10, lift=0.10)
       + _chain("tail", "body", (0, 1.20, -0.30), (0, -0.03, -0.35), 4))

# a building does not move: one body bone carries every part; props that do move
# (a crane arm, a smoke stack) come in as the spec's own extra bones
BUILDING = [("root", None, (0, 0, 0), (0, 0.3, 0)),
            ("body", "root", (0, 0, 0), (0, 4.0, 0))]

FAMILIES = {"building": BUILDING, "biped": BIPED, "spider": SPIDER, "spider_high": SPIDER_HIGH, "quadruped": QUADRUPED,
            "serpent": SERPENT, "vehicle": VEHICLE, "drake": DRAKE, "harpy": HARPY,
            "wyrm": WYRM, "mounted": MOUNTED, "mounted_flyer": MOUNTED_FLYER, "naga": NAGA,
            "centaur": CENTAUR, "wraith": WRAITH, "pod": POD, "shard": SHARD,
            "tracked": TRACKED, "walker": WALKER, "aircraft": AIRCRAFT, "sled": SLED,
            "hydra": HYDRA, "crew": CREW, "crawler": CRAWLER, "crustacean": CRUSTACEAN,
            "bird": BIRD, "bird_rider": BIRD_RIDER, "ray": RAY}
# bones a spec may leave out: tails are always optional (see required())
OPTIONAL = {"spider": {"abdomen"}, "spider_high": {"abdomen"}, "drake": {"jaw"}, "mounted_flyer": {"jaw"},
            "vehicle": {"wheel1", "wheel2", "wheel3", "wheel4"}, "shard": {"plate.2", "plate.3"},
            "aircraft": {"prop", "rudder"}, "tracked": {"arm.L", "arm.R"}}


# ---------------------------------------------------------------- rigs scaled by the sheet (PIPELINE 22.L4-4b)
# quadruped, wyrm and drake: like the spiders, the table can be rebuilt from the sheet's measures
# (silhouette.measure_quadruped / measure_chain: a snout-to-tail centre line [x, y, r] in fractions of H, x from the
# snout, y up). Same bones and names as the fixed table, so clips and retargets keep working; the top stays the
# fixed table's (HEIGHT). A family without measures keeps the fixed table.
SCALABLE = ("quadruped", "wyrm", "drake")
FIXED = {f: FAMILIES[f] for f in SCALABLE}
HEIGHT = {f: max(max(h[1], t[1]) for _, _, h, t in FIXED[f]) for f in SCALABLE}
HEAD_FRAC = {"wyrm": 0.12, "drake": 0.10}      # share of the line the head bone takes, from the snout
WYRM_SPINES = 6


def _line_at(line, t):
    """[x, y, r] at fraction t (0 = snout, 1 = tail tip) of the centre line."""
    f = min(max(t, 0.0), 1.0) * (len(line) - 1)
    i = min(int(f), len(line) - 2)
    return [a + (b - a) * (f - i) for a, b in zip(line[i], line[i + 1])]


def _t_of_x(line, x):
    """Fraction of the line where it passes x (the first crossing)."""
    xs = [p[0] for p in line]
    i = next((k for k in range(len(xs) - 1) if xs[k] <= x <= xs[k + 1]), len(xs) - 2 if x > xs[-1] else 0)
    return (i + (x - xs[i]) / max(xs[i + 1] - xs[i], 1e-6)) / (len(xs) - 1)


class Frame:
    """Sheet fractions (x from the snout, y up) -> rig metres: z forward from `x0`, y up, both x H."""

    def __init__(self, m, family, x0):
        self.line, self.H, self.x0 = m["line"], HEIGHT[family], x0

    def pt(self, t, dy=0.0):
        x, y, _ = _line_at(self.line, t)
        return (0.0, round((y + dy) * self.H, 4), round((self.x0 - x) * self.H, 4))

    def xyz(self, x, y, z):
        return (round(x * self.H, 4), round(y * self.H, 4), round((self.x0 - z) * self.H, 4))


def _chain_bones(prefix, parent, f, ts, first=1):
    """Bones prefix.first.. along the line from ts[0] to ts[-1] (one bone per interval)."""
    return [(f"{prefix}.{first + i}", parent if i == 0 else f"{prefix}.{first + i - 1}", f.pt(a), f.pt(b))
            for i, (a, b) in enumerate(zip(ts[:-1], ts[1:]))]


def _spaced(a, b, n):
    return [a + (b - a) * i / n for i in range(n + 1)]


def _wings_measured(parent, m, f):
    """wing1 on +x, wing2 mirrored: root at the front panel's inner edge and height, the side panel's line
    point (z), tip at the sheet's highest pixel; the elbow halfway, a little higher."""
    w = m["wing"]
    z_root = _line_at(m["line"], w["root"] / (len(m["line"]) - 1))[0]
    out = []
    for n, side in ((1, 1), (2, -1)):
        root = f.xyz(side * w["root_x"], w["root_y"], z_root)
        tip = f.xyz(side * w["tip"][0], w["tip"][1], w["top"])
        elbow = tuple(round((a + b) / 2, 4) for a, b in zip(root, tip))
        out += [(f"wing{n}.upper", parent, root, elbow), (f"wing{n}.lower", f"wing{n}.upper", elbow, tip)]
    return out


def _quad_body(m, f, family):
    """root, spine.1/.2 over the trunk, the four legs: the quadruped rig without head and tail. Returns (table,
    (t_front, t_rear))."""
    t0, t1 = _t_of_x(m["line"], m["trunk"][0]), _t_of_x(m["line"], m["trunk"][1])
    table = [("root", None, (0, 0, 0), (0, 0.3, 0)),
             ("spine.1", "root", f.pt(t1), f.pt((t0 + t1) / 2)), ("spine.2", "spine.1", f.pt((t0 + t1) / 2), f.pt(t0))]
    legs = m["legs"]
    fx = [legs["x"][0] if legs["x"][0] is not None else m["trunk"][0] + 0.25 * (m["trunk"][1] - m["trunk"][0]),
          legs["x"][1] if legs["x"][1] is not None else m["trunk"][1] - 0.25 * (m["trunk"][1] - m["trunk"][0])]
    foot = 0.05 * f.H
    for pair, (zx, parent) in enumerate(zip(fx, ("spine.2", "spine.1"))):
        hip_y = _line_at(m["line"], _t_of_x(m["line"], zx))[1] * f.H
        for k, side in enumerate((1, -1)):
            x, z = side * legs["spread"] * f.H, round((f.x0 - zx) * f.H, 4)
            name = f"leg{2 * pair + k + 1}"
            hip, knee, ankle = (x, round(hip_y, 4), z), (x * 1.05, round((hip_y + foot) / 2, 4), z), (x * 1.05, foot, z)
            table += [(f"{name}.upper", parent, hip, knee), (f"{name}.lower", f"{name}.upper", knee, ankle)]
    return table, (t0, t1)


def scale_quadruped(m):
    """FAMILIES["quadruped"] rebuilt from measure_quadruped: spine over the trunk, the head from its front to the
    snout, two tail bones to the tail tip, legs at the measured columns and spread."""
    f = Frame(m, "quadruped", sum(m["trunk"]) / 2)
    table, (t0, t1) = _quad_body(m, f, "quadruped")
    table += [("head", "spine.2", f.pt(t0), f.pt(0.0))]
    table += _chain_bones("tail", "spine.1", f, _spaced(t1, 1.0, 2))
    FAMILIES["quadruped"] = table
    _drop_caches()
    return table


def scale_drake(m):
    """FAMILIES["drake"]: the quadruped body, a 2-bone neck and the head up to HEAD_FRAC of the line, a 3-bone tail,
    wings from the sheet (_wings_measured)."""
    f = Frame(m, "drake", sum(m["trunk"]) / 2)
    table, (t0, t1) = _quad_body(m, f, "drake")
    hb = HEAD_FRAC["drake"]
    table += _chain_bones("neck", "spine.2", f, _spaced(t0, hb, 2))
    head, tip = f.pt(hb), f.pt(0.0)
    table += [("head", "neck.2", head, tip),
              ("jaw", "head", (0, head[1] - 0.04 * f.H, head[2] - 0.03 * f.H), (0, tip[1] - 0.1 * f.H, tip[2] - 0.05 * f.H))]
    table += _chain_bones("tail", "spine.1", f, _spaced(t1, 1.0, 3))
    table += _wings_measured("spine.2", m, f)
    FAMILIES["drake"] = table
    _drop_caches()
    return table


def scale_wyrm(m):
    """FAMILIES["wyrm"]: the head bone on the first HEAD_FRAC of the line, WYRM_SPINES spine bones along the rest,
    wings from the sheet. The line is the S of the side panel."""
    f = Frame(m, "wyrm", m["len"] / 2)
    hb = HEAD_FRAC["wyrm"]
    table = [("root", None, (0, 0, 0), (0, 0.2, 0))]
    table += _chain_bones("spine", "root", f, _spaced(hb, 1.0, WYRM_SPINES))
    table += [("head", "spine.1", f.pt(hb), f.pt(0.0))]
    table += _wings_measured("spine.1", m, f)
    FAMILIES["wyrm"] = table
    _drop_caches()
    return table


SCALERS = {"quadruped": scale_quadruped, "wyrm": scale_wyrm, "drake": scale_drake,
           "spider": lambda m: scale_spider("spider", m), "spider_high": lambda m: scale_spider("spider_high", m)}


def scale_rig(family, measure):
    """Rebuild the table of `family` from the sheet's measures when it has a scaler and a measure (otherwise the
    fixed table stays); True when it did."""
    if not measure or family not in SCALERS:
        return False
    SCALERS[family](measure)
    return True


def with_extras(family, extras):
    """The family table plus a spec's own prop bones [[name, parent, head, tail]]:
    a mast, a second head, a counterweight. Names must be new, parents must exist."""
    table = list(FAMILIES[family])
    known = {b[0] for b in table}
    for name, parent, head, tail in extras or []:
        if name in known or parent not in known:
            raise ValueError(f"extra bone {name} (parent {parent}) does not fit {family}")
        table.append((name, parent, tuple(head), tuple(tail)))
        known.add(name)
    return table


def bones(family):
    """Bone names of a family, in table order."""
    return [name for name, *_ in FAMILIES[family]]


def parents(family, extras=None):
    """bone -> parent, skipping bones that hang straight off the root."""
    return {name: parent for name, parent, *_ in with_extras(family, extras)
            if parent and parent != "root"}


def required(family):
    """Bones a spec must cover: everything but the root, tails and the family's
    optional extras."""
    return {b for b in bones(family) if b != "root" and not b.startswith("tail")
            } - OPTIONAL.get(family, set())


def top(family):
    """Highest bone point: the rig's natural height in spec metres."""
    return HEIGHT.get(family) or max(max(head[1], tail[1]) for _, _, head, tail in FAMILIES[family])


def has_biped_limbs(family):
    """Families whose arms or legs take the biped's hand-keyed clips."""
    return bool({"arm.L", "thigh.L"} & set(bones(family)))


# ---------------------------------------------------------------- clips
# Each clip is {frame: {bone: (rx, ry, rz, lift)}}, the format build_unit.make_actions
# keys. Gaits are sine cycles over 24 frames, phased per leg so the classic patterns
# fall out: trot (diagonal pairs) for four legs, alternating neighbours for rings,
# a travelling wave for chains, a flap for wings, spinning wheels, a bob for hoverers.
CYCLE = 24
STEP = 3
TROT = {"leg1": 0.0, "leg4": 0.0, "leg2": 0.5, "leg3": 0.5}
CHAINS = ("tail.", "neck", "tendril", "stalk.")       # always wave
BODY = ("hull", "body", "spine.1", "base", "cradle", "pelvis")
# no ground contact: these bob on the root in idle and walk; the winged ones also flap
HOVER = {"wraith", "pod", "shard", "aircraft", "wyrm", "drake", "harpy", "mounted_flyer",
         "bird", "bird_rider", "ray"}


def _cycle(channels, frames=CYCLE, step=STEP):
    """channels: {bone: (axis 0-2, amplitude deg, phase in cycles, lift metres)}. The
    root's lift goes in the pose's `up` slot: the root points up, so its local Z (where
    `lift` moves it) is the forward axis, and a bob must rise, not slide."""
    out = {}
    for f in range(1, frames + 2, step):
        t = 2 * math.pi * (f - 1) / frames
        pose = {}
        for bone, (axis, amp, phase, lift) in channels.items():
            rot = [0.0, 0.0, 0.0]
            rot[axis] = amp * math.sin(t + 2 * math.pi * phase)
            rise = lift * max(0.0, math.sin(t + 2 * math.pi * phase))
            pose[bone] = (*rot, 0.0, rise) if bone == "root" else (*rot, rise)
        out[f] = pose
    return out


def _gait(names):
    legs = sorted({b.split(".")[0] for b in names if b.startswith("leg")})
    ch = {}
    for i, leg in enumerate(legs):
        four = len(legs) == 4 and "spine.1" in names     # a quadruped body trots
        ph = TROT[leg] if four else 0.5 * (i % 2)
        fore_aft = four or len(legs) == 2
        ch[f"{leg}.upper"] = (0 if fore_aft else 2, 24.0, ph, 0.0)   # fore-aft vs. sweep
        ch[f"{leg}.lower"] = (0, 14.0, ph + 0.25, 0.0)
    return ch


def _flap(names, amp=28.0):
    ch = {}
    for b in names:
        if b.startswith("wing") and b.endswith(".upper"):
            ch[b] = (0, amp if b.startswith("wing1") else -amp, 0.0, 0.0)
        elif b.startswith("wing") and b.endswith(".lower"):
            ch[b] = (0, amp * 0.5 if b.startswith("wing1") else -amp * 0.5, 0.15, 0.0)
    return ch


def _wave(names, amp=14.0):
    """Tails, necks and tentacles wave; a spine chain waves only on a legless body
    (serpent, sled) - on a quadruped it is the rigid back."""
    legged = any(b.startswith(("leg", "thigh")) for b in names)
    chain = [b for b in names
             if b.startswith(CHAINS) or (b.startswith("spine.") and not legged)]
    return {b: (2, amp, i / max(len(chain), 1), 0.0) for i, b in enumerate(chain)}


def walk(family):
    names = bones(family)
    if any(b.startswith("wheel") for b in names):
        out = _cycle({_body(names): (0, 1.5, 0.0, 0.01)})
        # wheels spin monotonically around their own axis, not back and forth
        for f, pose in out.items():
            for w in (b for b in names if b.startswith("wheel")):
                pose[w] = (0.0, 360.0 * (f - 1) / CYCLE, 0.0, 0.0)
        return out
    ch = {**_wave(names), **_gait(names), **_flap(names)}
    ch[_body(names)] = (0, 2.0, 0.0, 0.02)
    if "rider.spine" in names:
        ch["rider.spine"] = (0, 3.0, 0.25, 0.0)      # the rider rocks with the mount
    if family in HOVER:
        ch["root"] = (0, 0.0, 0.0, 0.06)
    if "head" in names and "head" not in ch:
        ch["head"] = (0, 4.0, 0.5, 0.0)
    return _cycle(ch)


def _body(names):
    return next((b for b in BODY if b in names), "root")


def idle(family):
    names = bones(family)
    ch = {k: (a, amp * 0.25, ph, lift * 0.5)
          for k, (a, amp, ph, lift) in {**_wave(names), **_flap(names)}.items()}
    ch[_body(names)] = (0, 2.5, 0.0, 0.0)
    if "head" in names:
        ch["head"] = (2, 6.0, 0.25, 0.0)
    if family in HOVER:
        ch["root"] = (0, 0.0, 0.0, 0.04)
    return _cycle(ch, frames=48, step=6)


def attack(family):
    """Wind back, strike forward with the head (bite, ram, recoil), recover."""
    names = bones(family)
    body = _body(names)
    strike = "head" if "head" in names else body
    keys = {1: (0, 0), 7: (12, 8), 10: (-20, -14), 16: (-18, -12), 30: (0, 0)}
    return {f: {strike: (h, 0, 0, 0), body: (b, 0, 0, 0)} for f, (h, b) in keys.items()}


def death(family):
    """Roll onto the side and settle; legs curl for the arthropods."""
    curl = {b: (30, 0, 0, 0) for b in bones(family) if b.endswith(".lower")}
    keys = {1: (0, 0.0), 6: (8, -0.02), 14: (35, -0.10), 26: (80, -0.20), 40: (90, -0.24)}
    out = {}
    for f, (roll, drop) in keys.items():
        k = roll / 90
        pose = {"root": (0, 0, roll, 0, drop)}          # drop along the root bone: down
        pose.update({b: (r[0] * k, 0, 0, 0) for b, r in curl.items()})
        out[f] = pose
    return out


# ---------------------------------------------------------------- biped clips
# Blocking follows the blender-animation skill: key poses first (stepped), a
# breakdown between them, spline only at the end. Contacts and impacts get
# VECTOR handles; holds get AUTO_CLAMPED so they stay flat.
IDLE = {
    1: {"root": (0, 0, 0, 0.0), "spine": (0, 0, 0, 0.0), "head": (0, 0, 0, 0.0),
        "arm.L": (0, 0, 0, 0.0), "arm.R": (0, 0, 0, 0.0)},
    24: {"root": (0, 0, 0, 0.0), "spine": (-1.5, 0, 0, 0.0), "head": (0, 4, 0, 0.0),
         "arm.L": (2, 0, 0, 0.0), "arm.R": (-2, 0, 0, 0.0)},
    48: {"root": (0, 0, 0, 0.0), "spine": (0, 0, 0, 0.0), "head": (0, 0, 0, 0.0),
         "arm.L": (0, 0, 0, 0.0), "arm.R": (0, 0, 0, 0.0)},
}

# heavy two-step walk: contact 1/13, down 4/16, passing 7/19, up 10/22, loop 25
WALK = {
    1: {"thigh.L": (-26, 0, 0, 0), "shin.L": (16, 0, 0, 0), "foot.L": (-8, 0, 0, 0),
        "thigh.R": (22, 0, 0, 0), "shin.R": (22, 0, 0, 0), "foot.R": (14, 0, 0, 0),
        "arm.L": (22, 0, 0, 0), "arm.R": (-22, 0, 0, 0), "spine": (3, 0, 0, 0),
        "head": (-3, 0, 0, 0), "root": (0, 0, 0, -0.02)},
    4: {"thigh.L": (-14, 0, 0, 0), "shin.L": (24, 0, 0, 0), "foot.L": (0, 0, 0, 0),
        "thigh.R": (14, 0, 0, 0), "shin.R": (14, 0, 0, 0), "foot.R": (6, 0, 0, 0),
        "arm.L": (14, 0, 0, 0), "arm.R": (-14, 0, 0, 0), "spine": (5, 0, 0, 0),
        "head": (-2, 0, 0, 0), "root": (0, 0, 0, -0.06)},
    7: {"thigh.L": (0, 0, 0, 0), "shin.L": (10, 0, 0, 0), "foot.L": (0, 0, 0, 0),
        "thigh.R": (0, 0, 0, 0), "shin.R": (6, 0, 0, 0), "foot.R": (0, 0, 0, 0),
        "arm.L": (0, 0, 0, 0), "arm.R": (0, 0, 0, 0), "spine": (1, 0, 0, 0),
        "head": (0, 0, 0, 0), "root": (0, 0, 0, 0.02)},
    10: {"thigh.L": (16, 0, 0, 0), "shin.L": (6, 0, 0, 0), "foot.L": (10, 0, 0, 0),
         "thigh.R": (-18, 0, 0, 0), "shin.R": (12, 0, 0, 0), "foot.R": (-6, 0, 0, 0),
         "arm.L": (-14, 0, 0, 0), "arm.R": (14, 0, 0, 0), "spine": (3, 0, 0, 0),
         "head": (-2, 0, 0, 0), "root": (0, 0, 0, 0.0)},
    13: {"thigh.L": (22, 0, 0, 0), "shin.L": (22, 0, 0, 0), "foot.L": (14, 0, 0, 0),
         "thigh.R": (-26, 0, 0, 0), "shin.R": (16, 0, 0, 0), "foot.R": (-8, 0, 0, 0),
         "arm.L": (-22, 0, 0, 0), "arm.R": (22, 0, 0, 0), "spine": (3, 0, 0, 0),
         "head": (-3, 0, 0, 0), "root": (0, 0, 0, -0.02)},
    16: {"thigh.L": (14, 0, 0, 0), "shin.L": (14, 0, 0, 0), "foot.L": (6, 0, 0, 0),
         "thigh.R": (-14, 0, 0, 0), "shin.R": (24, 0, 0, 0), "foot.R": (0, 0, 0, 0),
         "arm.L": (-14, 0, 0, 0), "arm.R": (14, 0, 0, 0), "spine": (5, 0, 0, 0),
         "head": (-2, 0, 0, 0), "root": (0, 0, 0, -0.06)},
    19: {"thigh.L": (0, 0, 0, 0), "shin.L": (6, 0, 0, 0), "foot.L": (0, 0, 0, 0),
         "thigh.R": (0, 0, 0, 0), "shin.R": (10, 0, 0, 0), "foot.R": (0, 0, 0, 0),
         "arm.L": (0, 0, 0, 0), "arm.R": (0, 0, 0, 0), "spine": (1, 0, 0, 0),
         "head": (0, 0, 0, 0), "root": (0, 0, 0, 0.02)},
    22: {"thigh.L": (-18, 0, 0, 0), "shin.L": (12, 0, 0, 0), "foot.L": (-6, 0, 0, 0),
         "thigh.R": (16, 0, 0, 0), "shin.R": (6, 0, 0, 0), "foot.R": (10, 0, 0, 0),
         "arm.L": (14, 0, 0, 0), "arm.R": (-14, 0, 0, 0), "spine": (3, 0, 0, 0),
         "head": (-2, 0, 0, 0), "root": (0, 0, 0, 0.0)},
    25: {"thigh.L": (-26, 0, 0, 0), "shin.L": (16, 0, 0, 0), "foot.L": (-8, 0, 0, 0),
         "thigh.R": (22, 0, 0, 0), "shin.R": (22, 0, 0, 0), "foot.R": (14, 0, 0, 0),
         "arm.L": (22, 0, 0, 0), "arm.R": (-22, 0, 0, 0), "spine": (3, 0, 0, 0),
         "head": (-3, 0, 0, 0), "root": (0, 0, 0, -0.02)},
}

# piston thrust: settle, wind back (anticipation), snap, hold, recover
ATTACK = {
    1: {"root": (0, 0, 0, 0.0), "spine": (0, 0, 0, 0), "arm.R": (0, 0, 0, 0), "forearm.R": (0, 0, 0, 0),
        "arm.L": (0, 0, 0, 0), "head": (0, 0, 0, 0)},
    7: {"root": (0, 0, 0, -0.03), "spine": (7, 0, 0, 0), "arm.R": (26, 0, 0, 0), "forearm.R": (30, 0, 0, 0),
        "arm.L": (-10, 0, 0, 0), "head": (5, 0, 0, 0)},
    10: {"root": (0, 0, 0, 0.02), "spine": (-9, 0, 0, 0), "arm.R": (-30, 0, 0, 0), "forearm.R": (-78, 0, 0, 0),
         "arm.L": (16, 0, 0, 0), "head": (-8, 0, 0, 0)},
    16: {"root": (0, 0, 0, 0.01), "spine": (-8, 0, 0, 0), "arm.R": (-28, 0, 0, 0), "forearm.R": (-76, 0, 0, 0),
         "arm.L": (15, 0, 0, 0), "head": (-6, 0, 0, 0)},
    30: {"root": (0, 0, 0, 0.0), "spine": (0, 0, 0, 0), "arm.R": (0, 0, 0, 0), "forearm.R": (0, 0, 0, 0),
         "arm.L": (0, 0, 0, 0), "head": (0, 0, 0, 0)},
}

# stagger back, knees buckle, fall on the back, settle
DEATH = {
    1: {"root": (0, 0, 0, 0.0), "spine": (0, 0, 0, 0), "thigh.L": (0, 0, 0, 0), "thigh.R": (0, 0, 0, 0)},
    6: {"root": (0, 0, 0, 0.0), "spine": (12, 0, 0, 0), "thigh.L": (-10, 0, 0, 0), "thigh.R": (8, 0, 0, 0)},
    14: {"root": (18, 0, 0, -0.16), "spine": (16, 0, 0, 0), "thigh.L": (26, 0, 0, 0), "thigh.R": (20, 0, 0, 0)},
    26: {"root": (72, 0, 0, -0.62), "spine": (10, 0, 0, 0), "thigh.L": (34, 0, 0, 0), "thigh.R": (28, 0, 0, 0)},
    40: {"root": (86, 0, 0, -0.78), "spine": (4, 0, 0, 0), "thigh.L": (18, 0, 0, 0), "thigh.R": (14, 0, 0, 0)},
}

BIPED_ACTIONS = [("idle", IDLE, True, (), ()),
                 ("walk", WALK, True, (1, 5, 17, 21), (("head", 2), ("forearm.L", 1), ("forearm.R", 1))),
                 ("attack", ATTACK, False, (10,), ()), ("death", DEATH, False, (26,), ())]


STATIC = {"building"}          # no clips: the game never animates these models


def actions(family):
    """(name, poses, cyclic, contacts, lags) for every clip derived from the bones.
    Families with biped limbs get these merged over the biped's hand-keyed tables
    (build_unit.make_actions); the biped itself adds nothing; static families none."""
    if family in STATIC:
        return []
    return [("idle", idle(family), True, (), ()), ("walk", walk(family), True, (), ()),
            ("attack", attack(family), False, (10,), ()), ("death", death(family), False, (26,), ())]
