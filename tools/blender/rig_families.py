"""Rig families for Castle Fight units. Bones are data, so a new body plan is a new
entry here and not a change to the builder.

Every family uses the same convention so animation clips can be shared inside the
family:

  root                     ground anchor
  <chain>.<n>              spines, tails, tentacles   spine.1, spine.2 ...
  head                     head / turret / cockpit
  leg<N>.upper/.lower/.foot    each leg, numbered from the front-left, clockwise
  wing<N>.upper/.lower     wings
  jaw / tail.<n>           optional extras

A unit's spec picks the family with {"rig": "biped" | "quadruped" | "spider" |
"serpent" | "vehicle"}; the builder reads the bone table from here and the spec
only names bones, never coordinates. Placement, length and overlap come from the rig.
"""
import math

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


def _legs(n, parent, body_y, body_r, reach, up=0.55, phase=0.0):
    """A ring of legs around the body: the generic arthropod plan."""
    bones = []
    for i in range(n):
        a = phase + 2 * math.pi * i / n
        hx, hz = math.cos(a) * body_r, math.sin(a) * body_r
        kx, kz = math.cos(a) * (body_r + reach * 0.55), math.sin(a) * (body_r + reach * 0.55)
        fx, fz = math.cos(a) * (body_r + reach), math.sin(a) * (body_r + reach)
        tag = f"leg{i + 1}"
        bones += [
            (f"{tag}.upper", parent, (hx, body_y, hz), (kx, body_y - up * 0.45, kz)),
            (f"{tag}.lower", f"{tag}.upper", (kx, body_y - up * 0.45, kz), (fx, 0.04, fz)),
        ]
    return bones


SPIDER = ([("root", None, (0, 0, 0), (0, 0.25, 0)),
           ("body", "root", (0, 0.55, 0), (0, 0.95, 0)),
           ("head", "body", (0, 0.55, 0.45), (0, 0.50, 0.85))]
          + _legs(8, "body", 0.60, 0.34, 0.78, phase=math.pi / 8))

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

SERPENT = [("root", None, (0, 0, 0), (0, 0.2, 0)), ("head", "root", (0, 0.55, 0.60), (0, 0.50, 0.95))]
SERPENT += [(f"spine.{i}", "root" if i == 1 else f"spine.{i - 1}",
             (0, 0.50 - 0.08 * i, 0.55 - 0.22 * i), (0, 0.48 - 0.08 * i, 0.33 - 0.22 * i))
            for i in range(1, 9)]

VEHICLE = [("root", None, (0, 0, 0), (0, 0.2, 0)),
           ("hull", "root", (0, 0.35, -0.55), (0, 0.45, 0.55)),
           ("head", "hull", (0, 0.62, 0.10), (0, 0.62, 0.60)),
           ("wheel1", "hull", (0.42, 0.30, 0.38), (0.56, 0.30, 0.38)),
           ("wheel2", "hull", (-0.42, 0.30, 0.38), (-0.56, 0.30, 0.38)),
           ("wheel3", "hull", (0.42, 0.30, -0.38), (0.56, 0.30, -0.38)),
           ("wheel4", "hull", (-0.42, 0.30, -0.38), (-0.56, 0.30, -0.38))]

FAMILIES = {"biped": BIPED, "spider": SPIDER, "quadruped": QUADRUPED,
            "serpent": SERPENT, "vehicle": VEHICLE}
