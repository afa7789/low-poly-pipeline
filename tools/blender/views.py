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
# PIPELINE 25.L7-1: how much each view counts in fit_spec's objective and deform_to_sheet's acceptance, per rig
# (1 where absent). Legs and tails of the spider / quadruped only read from above and from the gameplay camera.
VIEW_WEIGHTS = {"spider": {"rts": 2.0, "top": 2.0, "bottom": 2.0},
                "quadruped": {"rts": 2.0, "top": 2.0, "bottom": 2.0},
                "biped": {"rts": 1.5}}


# PIPELINE 30.L12-5: how much a view the sheet contradicts (silhouette.sheet_report "incoherent") counts in the fit, the deformation
# and the vertex optimiser. None (default) = as any view (VIEW_WEIGHTS); 0 = ignored, still measured and printed (opt-in
# `--incoherent-weight 0`: it did not meet the acceptance, see the PIPELINE subsection).
INCOHERENT_WEIGHT = None


def weight_of(rig, view, sheet_report=None, incoherent_weight=None):
    """The weight of `view` in the fit's objective and the deformation's acceptance: `incoherent_weight` (default
    INCOHERENT_WEIGHT, when not None) if the sheet report lists the view as incoherent, whatever the rig, else VIEW_WEIGHTS."""
    w = INCOHERENT_WEIGHT if incoherent_weight is None else incoherent_weight
    if w is not None and view in (sheet_report or {}).get("incoherent", ()):
        return w
    return VIEW_WEIGHTS.get(rig, {}).get(view, 1.0)


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


def rest_pose():
    """Every imported armature in its rest pose. The glTF importer activates the first
    clip (alphabetically "attack") and leaves the rig on its frame 1; since the clips
    come from retargeted references that frame is a swing, not the spec, and every
    silhouette and review view measured the swing (n01X 0.87 -> 0.47 on the same spec).
    Blender only: imports bpy when called."""
    import bpy
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            obj.data.pose_position = "REST"


def make_unlit():
    """Review renders show what the game shows: the texture colour, no light. Every
    material's base colour (texture or value) moves to Emission and the Principled
    surface is made black and non-specular, so lights, world and gloss add nothing.
    Alpha is kept. Blender only: imports bpy when called."""
    import bpy
    for mat in bpy.data.materials:
        bsdf = mat.node_tree.nodes.get("Principled BSDF") if mat.use_nodes else None
        if bsdf is None:
            continue
        base, emit = bsdf.inputs["Base Color"], bsdf.inputs["Emission Color"]
        if base.is_linked:
            link = base.links[0]
            mat.node_tree.links.new(link.from_socket, emit)
            mat.node_tree.links.remove(link)   # left linked, the lights shine on the texture too: x2 brighter
        else:
            emit.default_value = base.default_value
        base.default_value = (0.0, 0.0, 0.0, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 1.0
        bsdf.inputs["Specular IOR Level"].default_value = 0.0
        bsdf.inputs["Roughness"].default_value = 1.0
