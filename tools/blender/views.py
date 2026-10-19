"""Orthographic review cameras shared by render_silhouette.py and render_unit.py.

The concept sheet's top and bottom panels are not drawn straight down/up: the image
model tilts them toward the front, so the chest, fists and boot soles show. Those two
views therefore take a tilt; silhouette.py sweeps TILTS and keeps the one whose mask
matches the concept panel, and the colour render reuses that angle for the review.

The RTS view is the gameplay camera, drawn per unit by generate.py --image from the
approved sheet (<sheet>-rts.jpg). Its elevation and azimuth are swept the same way.
"""
import math

DIST = 8.0
# name -> camera offset from the model centre, camera rotation (deg); Z-up, front is -Y
VIEWS = {
    "front": ((0, -DIST, 0), (90, 0, 0)),
    "left": ((-DIST, 0, 0), (90, 0, -90)),
    "back": ((0, DIST, 0), (90, 0, 180)),
    "top": ((0, 0, DIST), (0, 0, 0)),
    "bottom": ((0, 0, -DIST), (180, 0, 0)),
    "right": ((DIST, 0, 0), (90, 0, 90)),
    "roof": ((0, 0, DIST), (0, 0, 0)),          # building roof plan: a true ortho top
}
# panel names of a sheet, in reading order (top row of three, bottom row of two)
LAYOUTS = {"unit": ("front", "left", "back", "top", "bottom"),
           "building": ("front", "left", "back", "right", "roof")}


def layout_of(kind):
    """Sheet layout for a budget kind: buildings are drawn as elevations + roof plan."""
    return "building" if kind in ("building", "large") else "unit"
TILTED = ("top", "bottom")
TILTS = tuple(range(-40, 50, 10))
# (elevation above the ground, azimuth from the front toward +X), degrees. Both sides
# are swept and the match is never mirrored (silhouette.variants), so the IoU picks the
# side: n01X 0.78 at +45 against 0.58 at -45. The image model reads "front-right" as the
# viewer's right (+X), but it is measured, not assumed.
RTS = tuple((e, a) for e in (35, 45, 55, 65) for a in (-60, -45, -30, 30, 45, 60))
RTS_DEFAULT = (45, 45)


def camera(name, tilt=0):
    """Offset and rotation for one view; `tilt` degrees swing top/bottom toward the front."""
    if name not in TILTED or not tilt:
        return VIEWS[name]
    t = math.radians(tilt)
    s, c = DIST * math.sin(t), DIST * math.cos(t)
    if name == "top":
        return (0, -s, c), (tilt, 0, 0)
    return (0, -s, -c), (180 - tilt, 0, 0)


def rts_offset(elev, azim, dist=DIST):
    """Camera offset from the model centre for the gameplay view; aim it at the centre."""
    e, a = math.radians(elev), math.radians(azim)
    return (dist * math.cos(e) * math.sin(a), -dist * math.cos(e) * math.cos(a),
            dist * math.sin(e))


def parse_tilts(arg):
    """'top:20,bottom:30,rts:45/30' -> {'top': 20, 'bottom': 30, 'rts': (45, 30)}."""
    out = {}
    for name, value in (item.split(":") for item in arg.split(",") if item):
        parts = tuple(int(v) for v in value.split("/"))
        out[name] = parts if len(parts) > 1 else parts[0]
    return out
