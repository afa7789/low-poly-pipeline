#!/usr/bin/env python3
"""One unit, end to end: sheet -> spec (vision model) -> GLB -> gates -> turntable GIF.

    python3 tools/blender/spec_pipeline.py --id n01X --race Mech --name "Iron Golem"
    python3 tools/blender/spec_pipeline.py --id hfoo --race Human --name Footman \\
        --model claude-opus-5.5 --tag opus55 --run opus55

Inputs default to refs/<id>/ (sheet.jpg judges, sheet-hard.jpg builds; sheet-hard-clean.jpg
and sheet-props.jpg ride along when present); the run lands in runs/draft/<id>/<run>/.

Triangle budgets, WC3 SD standard (see PIPELINE.md §6):
    mass unit 400-700 · hero 900-1600 · standard building 600-800 · town hall / large 2000-3000

Writes, under <out>:
    specs/<tag>-<id>.json, glb/<tag>-<id>.glb      versioned: the result
    <tag>/<id>.gif, <tag>/<id>-compare.png          local review (gitignored)
    views/, sil/, passes/                           local intermediates (gitignored)
and prints one gate line: id, tag, tris, budget, materials, smear. Exit code 1 if any gate
fails; a failed gate never stops the run, every output is still written.
"""
import argparse
import base64
import json
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

import rig_families as RF
from surfaces import DECALS, SURFACES
from views import layout_of

ROOT = pathlib.Path(__file__).resolve().parents[2]
SKILLS = pathlib.Path.home() / ".config" / "opencode" / "skills"
RIG = "biped"                    # the family every bone name is checked against
BONES = set(RF.bones(RIG))
KINDS = {"box", "cyl", "wheel", "prism", "dome", "frustum", "ring"}
MATS = {"iron", "darkiron", "brass", "flame", "lamp"}   # n01X slots, always valid (metal)
from preflight import BUDGETS, MATERIAL_SLOTS, ground_fix, misplaced_decals  # noqa: E402  (one table for pipeline and gate)

DSL = """Write a Blender part spec as a JSON object: {{"palette": {{"<slot>": {{"surface": "<surface>", "color": "#RRGGBB"}}, ...}}, "parts": [[bone, kind, dims, at, material, opts], ...]}}

Kinds and dims, exactly:
- "prism": a tapered n-gon tube - THE limb and torso primitive. dims = (radius_bottom, radius_top, height). opts {{"sides": 6 or 8, "axis": "up" | "fwd"}}. Use a smaller radius_top so the limb tapers away from the body.
- "frustum": a box with a scaled, offset top - THE wedge primitive. dims = (width_x, height_y, depth_z). opts {{"top": (scale_x, scale_z), "shift": (offset_x, offset_z)}}. Use for boots, trapezoid pelvis, waist taper and stepped fists.
- "ring": a flat annulus with optional spokes and hub - THE valve-wheel primitive. dims = (outer_radius, radial_width, thickness). opts {{"sides": 10, "spokes": 3, "hub": 0.05, "axis": "up" | "fwd" | "side", "tilt": degrees, "spin": degrees}}. `axis` is the disc normal; a halo/steering wheel is axis "up" with tilt 20-30, NOT a disc facing the camera.
- "dome": only for a genuinely domed organic cap. Never a mechanical pauldron: use a box slab instead.
- "box": for flat plates, slabs, boots, shields and weapon heads. dims = (width_x, height_y, depth_z). Never for a limb.
- "cyl": a straight tube, only when a part is genuinely cylindrical. dims = (radius, depth). opts {{"axis": "up" | "fwd"}}.
- "wheel": a torus rim. dims = (major_radius, tube_radius).
- at = (x, y, z) in metres: +y is UP, +z is FORWARD (towards the viewer in the front view), x is right. The unit stands on y = 0, about {height} m tall.
- LIMBS/ANGLED PARTS: instead of `at`, use opts {{"from": [x,y,z], "to": [x,y,z]}}. The builder places the midpoint and aims the part's local height axis from `from` to `to`, so the limb angle is solved in code, never guessed. {limb_note}
- material: the name of one palette slot. Declare 3 to 8 slots in "palette", one per colour zone of the sheet - the sheet's colour zones are the contract. Each slot has a "color" taken from the sheet colours measured below and a "surface" saying what the material is, which sets its painted pattern and gloss: {surfaces}. SURFACE BY WHAT THE PART IS (a rule, not a suggestion): an animal, insect or arachnid is "chitin" (hard shell), "fur" or "skin" - never "metal", "polished" or "plastic"; "scales" only for a reptile or a fish; a living tree is "bark", worked timber (planks, beams, crates) is "wood"; an ooze or any gooey creature is "slime"; raw meat, tongues and organs are "flesh"; "stone" for rock; "metal"/"polished" only for armour and machines. Use "glow" for lamps, eyes and crystals that emit light. Only where the unit card asks for alpha (gauge glass, a flame tongue), give that one slot "surface": "glass" and "alpha": 0.3 to 0.7; every other slot stays opaque. The old slot names "iron", "darkiron", "brass" and "lamp" still work as metal.
Sheet colours (code-measured, share of the figure; near-black ink outlines removed): {colours}.
- PAINTED FEATURES: eyes are painted, never modelled. Give the part whose front face carries them opts {{"decal": "eyes2"}} (two eyes), {{"decal": "eyes8"}} (spider eyes), {{"decal": "face"}} (two eyes and a mouth) or {{"decal": "mask"}} (a dark mask with two glowing eyes), plus "decal_color": "#RRGGBB" when they glow. The decal is projected onto that part's front face. A decal goes ONLY on a part bound to the head (head, jaw, rider.head): eyes on the chest or any other bone are rejected.
- HOODS: a hood or cowl is a deep dark frustum or box on the head bone, opening to the front and set back. Paint the face or mask as a decal on the FRONT face of the head part inside the hood, and push that head part slightly forward of the hood's back wall so the hood does not hide it. Never model the eyes as geometry.
- BOXES: at most a third of the parts may be kind "box"; prefer prism, frustum, dome or cyl for everything else (the preflight rule box_ceiling fails the spec otherwise).
"""

BUILDING_BRIEF = """You are a technical artist building a low-poly game building in the style of classic Warcraft III. The attached image is a five-view elevation sheet of ONE building: the top row is the front, left and back elevations, the bottom row the right elevation and the roof plan. It is a {race} {name} (id {uid}), {role}, from a dieselpunk dark-fantasy RTS. Study the sheet: footprint, wall heights, roof line, where each prop sits and where the colour zones are.

{dsl}{measured}

RIG TABLE - the building does not move; bind every part to body unless it is a prop that moves on its own:

{bones}

FORM RULES, non-negotiable:
1. The footprint is what the roof plan shows: take its width from the front elevation and its depth from the left elevation.
2. Walls are thick slabs (box or frustum), never a zero-thickness plane; corners are chamfered so primitive lighting catches the edge.
3. The roof is its own mass and must read from the RTS camera at 45 degrees: the overhang, ridge or flat cap exactly as drawn.
4. A knee-high base of mud or stone (a box about 0.08 H tall) runs under the walls so the building sits in the ground.
5. Props at their largest, crudest shape: stacks, tanks, cranes, rails, pumps. The door is a dark recessed box. At most 12 props.
6. The door and the one lit lamp face the front (+z).
7. One flat team-colour zone - a banner or a painted stencil band - covers 10 to 15 percent of the visible surface, never on a small part.
8. Nothing below y = 0; every part touches another part; nothing floats.
9. Use 15 to 30 parts and end near {budget} triangles (box 12, frustum 12, prism about 28, cyl 44). Boxes are the right primitive for a building.
10. The front silhouette must still read as one black shape at 32 x 32 pixels; detail lives in the texture, not the geometry.

{rig_note}

Return ONLY the JSON object, no prose, no code fences."""


BRIEF = """You are a technical artist building a low-poly game unit in the style of classic Warcraft III. The attached image is a 5-view turnaround of ONE unit: a {race} {name} (id {uid}), {role}, from a dieselpunk dark-fantasy RTS. Study the sheet: proportions, the shape of every mass, where the coloured parts are, how the limbs and props are built.

{dsl}{measured}

RIG TABLE - place every part ON these segments. The "at" of a part must be the segment
MIDPOINT, and its length (prism height / cyl depth / box height) must be 105 to 115 percent of
the segment length, so consecutive parts overlap and the body stays connected:

{bones}

FORM RULES, non-negotiable - these are what keep the model from reading as Minecraft:
1. No limb is a box. Thighs, shins, upper arms, forearms, necks and torso are prisms with 6 or 8 sides and a taper along their length.
2. The torso is wider at the shoulders than at the waist (a prism, or two stacked prisms). It is never a cuboid.
3. Mechanical shoulders are upright slabs (box or frustum), not domes; organic caps may use a dome. Match the concept's part language: a box where the sheet draws a box.
4. Boxes (kind "box") may be at most a third of the parts (preflight box_ceiling), and only as flat plates, boots, shields or weapon heads.
5. Nothing is axis-aligned: arms sit 10 to 20 degrees out from the body and slightly bent at the elbow; feet turn 8 to 12 degrees outward.
6. The silhouette is asymmetric: one arm carries the main prop, the other stays free or carries a smaller one.
7. Use 22 to 28 parts, and end near {budget} triangles (prism about 28, dome about 28, box 12, cyl 44). Nothing below y = 0.
8. Joints overlap: every limb segment overlaps its neighbour by at least 10 percent of its length, so no gap opens when the rig rotates.
9. Never lock a joint straight: elbows and knees sit 2 to 4 degrees off the axis (blender-rigging: pre-bend 1 to 3 degrees).
10. Chamfer every edge the silhouette reads, at about 0.5 percent of the unit height; no razor edges, no feature thinner than twice that chamfer.
11. Heroic mass: two thirds of the volume in torso and shoulders, hands and feet oversized (that proportion is what reads at 32 px).
12. Feet are planted flat on y = 0, wider than the shin, and centred under the body (blender-rigging model_check).
13. The front silhouette must still read as one black shape at 32 x 32 pixels; if a part only works with colour, it is decoration, not form.
14. Keep flat faces planar and quad-based; no n-gon with a hole, no geometry that only exists to add a bevel.
15. DETAIL LIVES IN THE TEXTURE, NOT THE GEOMETRY (lowpoly-style skill): no micro-bevels, no weighted normals, no subdivision. Surface is flat-shaded or auto-smooth at 60 degrees or more.
16. No face that does not change the silhouette; merge coplanar faces. If a feature would only read in colour, leave it to the atlas.
17. Hands are mitts - no fingers. Feet are wedges. Fur, cloth, spikes and fangs are flat cards, never modelled strands.
18. Mirror what can be mirrored (arm and leg parts are duplicated across x); asymmetry comes from props, not from different limbs.
19. Separate placed parts are allowed - classic WC3 uses them (ghoul claws, back spikes) - as long as each one overlaps the body mass and the union reads as one silhouette.
19b. A head wheel/halo is a "ring" lying near-horizontal (axis "up", tilt 20-30 degrees), with 3 spokes, never a disc facing the camera and never six spokes.
20. One 256 to 512 pixel atlas per unit (1024 only for a hero). Model the large forms the atlas will describe, nothing finer.

CHUNKIFY - the Blizzard house style (Samwise Didier, WC3 art direction):
21. Exaggerate what carries identity: oversized hands, oversized shoulders, oversized weapon. A limb is never thinner than a sixth of the torso width.
22. Everything is thick. No zero-thickness plane: a plate or a cape is a slab with volume, and its corners are cut so primitive lighting catches the edge.
23. Reserve one big flat zone for team colour, about 10 to 15 percent of the visible surface (pauldron, shield, banner). Never put it on the face or on a small part.
24. Angle the main prop outward from the body, so the silhouette stays readable when units overlap in a fight.
25. The unit must be identifiable as one black shape from the RTS camera (high, top-down, about 35 degrees), not only from the front.

{rig_note}

The silhouette must read at 32x32 pixels: big shapes first, small trims last. Return ONLY the JSON object, no prose, no code fences."""


# Body-plan text of the brief, per rig family. The biped entry is the wording the n01X
# drafts were tuned on; the others describe their own bones and drop the biped landmarks.
RIG_TEXT = {
    "biped": ("Use this for every upper arm, forearm, thigh, shin and foot direction.",
              "Parts are rigid-bound: each part follows the bone you name. Rig reference: the "
              "head bone runs 2.16 to 2.72 up, the arms hang from 2.02 to 0.90, the legs from "
              "1.18 to 0.10. If the creature is not a biped, bind its mass to spine/pelvis and "
              "its limbs to the closest bones."),
    "quadruped": "a four-legged beast: torso mass on spine.1 (rear) and spine.2 (front), the "
                 "head on head, legs leg1..leg4 (upper, lower) numbered from the front-left "
                 "clockwise, an optional tail on tail.1-tail.2",
    "spider": "an eight-legged arthropod: abdomen and thorax mass on body, head and fangs on "
              "head, legs leg1..leg8 (upper, lower) radiating around the body, thin, angled "
              "and touching the ground at y = 0",
    "spider_high": "a long-legged spider: abdomen and thorax mass on body, head and fangs on "
                   "head, legs leg1..leg8 (upper, lower) radiating around the body. Each leg ARCHES: "
                   "the upper segment (femur) leaves the body UP and outward, the knee stands about "
                   "0.55 ABOVE the back line of the body (y about 1.15, the body being y 0.60), and "
                   "the lower segment (tibia) drops steeply from the knee to the ground at y = 0, "
                   "landing about 1.1 from the body axis; every segment thin and angular",
    "serpent": "a limbless body: the head on head, the body a chain of tapering segments "
               "spine.1..spine.8 lying low behind it",
    "vehicle": "a machine: hull mass on hull, turret or cab on head, wheels on wheel1..wheel4 "
               "(kind wheel, axis side); tracks, skids and plating bind to hull",
    "drake": "a four-legged dragon: body on spine.1 and spine.2, neck.1-neck.2 and head with an "
             "optional jaw, tail.1-tail.3, wings wing1 (left, +x) and wing2 (right) each with an "
             "upper and lower spar, legs leg1..leg4",
    "harpy": "a winged biped: the biped bones plus wing1 and wing2 (upper, lower) on the back",
    "wyrm": "a winged serpent: head, spine.1..spine.6 and wing1/wing2 (upper, lower) near the head",
    "mounted": "a rider on a four-legged mount: the quadruped bones plus a smaller seated rider "
               "(rider.spine, rider.head, rider.arm.L/R, rider.forearm.L/R)",
    "mounted_flyer": "a rider on a dragon: the drake bones plus the rider.* bones",
    "naga": "a torso on a snake tail: spine, head, arm.L/R and forearm.L/R standing on "
            "tail.1..tail.6, which lies on the ground behind",
    "centaur": "a torso on a four-legged body: spine.1, spine.2, legs leg1..leg4, an upright "
               "spine.3 carrying head, arm.L/R and forearm.L/R",
    "wraith": "a body with no legs that floats: base (skirt, pool or plume) under spine, head, "
              "arm.L/R and forearm.L/R",
    "pod": "a floating pod: body, stalk.1-stalk.2 rising from it and tendril1..tendril3 "
           "(.1, .2) hanging below",
    "shard": "a rigid abstract flyer: body, wing1/wing2 (upper, lower) spars, plate.1-plate.3 "
             "and tail.1",
    "tracked": "a tracked machine: hull, turret or cab on head, track.L and track.R, optional "
               "arm.L/arm.R tools",
    "walker": "a mech on two legs with no arms: pelvis, thigh/shin/foot L and R, a turret on "
              "head carrying barrel.L and barrel.R",
    "aircraft": "a flying machine: gasbag or fuselage on hull, gondola below it, prop and rudder",
    "sled": "a legless body that bends: spine.1..spine.4 lying on the ground, and head",
    "hydra": "a legless body with three necks: spine.1..spine.4 and neck1..neck3 (.1-.3), each "
             "neck ending in its own head",
    "crew": "a weapon worked by a crew fused into it: cradle, barrel, and the crew's legs "
            "thigh/shin L and R",
    "crawler": "a four-legged scuttler: body, head and leg1..leg4 (upper, lower) around it",
    "crustacean": "a crustacean: body, head, leg1..leg6 (upper, lower), claw.L/R with pincer.L/R, "
                  "tail.1-tail.3",
    "bird": "a two-legged flyer with no arms (bird or wyvern): spine.1, spine.2, neck.1-neck.2, "
            "head, leg1/leg2 (upper, lower), wing1/wing2 (upper, lower), tail.1-tail.3",
    "bird_rider": "a rider on a bird or wyvern: the bird bones plus the rider.* bones",
    "ray": "a flying ray: a flat body, wing1/wing2 (upper, lower) and a stinger tail "
           "tail.1-tail.4",
    "building": "a building: every part binds to body; it never moves",
}
EXTRA_BONES = ("If the card names a prop that moves on its own - a mast, a second head, a "
               "counterweight, a launcher arm - you may add up to 3 extra bones at the top "
               "level: \"bones\": [[name, parent, head, tail]], parent an existing bone, head "
               "and tail in metres. Never add a bone for a part that only rides along.")


def rig_text(family):
    """(limb_note, rig_note) of the brief for this family."""
    if family == "biped":
        limb, rig = RIG_TEXT["biped"]
        return limb, f"{rig} {EXTRA_BONES}"
    return ("Use this for every leg segment, neck, tail and any angled part.",
            f"Parts are rigid-bound: each part follows the bone you name. This unit is "
            f"{RIG_TEXT[family]}. Rules that mention arms, hands, elbows, knees or feet apply "
            f"only to the limbs this body has. {EXTRA_BONES}")


def measured_text(family, m):
    """Code-derived proportions of the sheet, as the brief states them."""
    profile = ", ".join(f"{v:.2f}" for v in m["front_width_profile"])
    if family != "biped":
        side = ", ".join(f"{v:.2f}" for v in m["left_width_profile"])
        return ("MEASURED FROM THIS SHEET (code-derived, fractions of total height H - obey "
                "these, do not re-guess them):\nFront silhouette width profile, top to bottom, "
                f"in 5% steps: {profile}.\nSide silhouette width profile, top to bottom, in 5% "
                f"steps: {side}.")
    return ("MEASURED FROM THIS SHEET (code-derived, fractions of total height H - obey these, "
            "do not\nre-guess them): "
            f"shoulder span {m['shoulder_span']} H, fist-to-fist span {m['fist_span']} H,\n"
            f"foot-to-foot stance {m['stance']} H, chest body depth {m['body_depth']} H, "
            f"foot length {m['foot_length']} H.\n"
            f"Front silhouette width profile, top to bottom, in 5% steps: {profile}.")


def set_rig(family):
    global RIG, BONES
    RIG, BONES = family, set(RF.bones(family))


def rig_table():
    lines = []
    for name, _, head, tail in RF.FAMILIES[RIG]:
        head, tail = (tuple(round(v, 2) for v in head), tuple(round(v, 2) for v in tail))
        mid = tuple((head[i] + tail[i]) / 2 for i in range(3))
        length = sum((tail[i] - head[i]) ** 2 for i in range(3)) ** 0.5
        lines.append(f"  {name:10} head {head} tail {tail} midpoint {tuple(round(v, 2) for v in mid)} length {length:.2f}")
    return "\n".join(lines)


REFINE = """You are refining a low-poly Blender part spec so it matches ONE view of its approved concept.
Image 1: the concept's {view} view. Image 2: the current model rendered from the same {view} view.
Image 3: both silhouettes normalised to the same body height - red is concept only (missing mass:
grow or move a part there), green is model only (excess mass: shrink it or move it away), yellow
is shared.

Measured silhouette IoU of the current model per view: {scores}.
This pass fixes only what the {view} view shows: {axes}. Never trade mass between parts to win
IoU: each part must match the size of the same part in image 1.

Current spec, one part per line, index first - [bone, kind, dims, at, material, opts]:
{parts}

Return ONLY a JSON object, no prose, no code fences:
{{"set": {{"<index>": [bone, kind, dims, at, material, opts]}}, "add": [[...]], "drop": [index, ...], "why": "<one sentence>"}}
Change at most {limit} parts in total. Same bones, kinds, materials and coordinate convention as
the original brief below; every one of its rules still holds.

ORIGINAL BRIEF
{brief}"""

# What each refinement view can see; top and bottom are not passes (the sheet draws them
# off-ortho, PIPELINE.md §13), so they never steer geometry.
AXES = {"front": "widths along x, heights along y, how far arms and legs spread",
        "left": "depths along z, forward/back offsets, foot length, limb lean",
        "back": "back-side masses and their x placement, seen from behind",
        "rts": "how the whole mass reads from the gameplay camera: shoulder and fist bulk, "
               "head ornament, stance - the view the player actually sees",
        "right": "right-side masses and their z placement, seen from the right",
        "roof": "the footprint and the roof shape, seen straight down"}
RENDER_NAME = {"rts": "wc3"}  # render_unit.py's file for the gameplay view
PASS_EDITS = 6
REGRESSION = 0.01
# What a pass may not take away inside the contour (PIPELINE §18): colour zones, per view
ZONE_DROP = 0.05    # the view's area-weighted zone IoU
ZONE_LOSS = 0.15    # one zone's IoU, zones of silhouette.ZONE_SHARE or more
PIECE_LOSS = 0.4    # one drawn piece's cover
PROP_WARN = 0.40    # prop alone vs its drawing, IoU; n02X club 0.83, hfoo spear 0.69
RULE_LINE = re.compile(r"^\s+(\w+)\s+(PASS|FAIL)\b", re.M)   # a preflight.py result line
REPAIRS = 2
REPAIR_EDITS = 12

REPAIR = """The low-poly Blender part spec below was rejected by the preflight before it could be
built. Images: the concept's front and left views. Fix every FAIL line with the fewest part
changes; keep everything that passes.

PREFLIGHT
{problem}

Current spec, one part per line, index first - [bone, kind, dims, at, material, opts]:
{parts}

Return ONLY a JSON object, no prose, no code fences:
{{"set": {{"<index>": [bone, kind, dims, at, material, opts]}}, "add": [[...]], "drop": [index, ...], "why": "<one sentence>"}}
Change at most {limit} parts in total. Same rules as the original brief below.

ORIGINAL BRIEF
{brief}"""


def api_key():
    cfg = pathlib.Path.home() / ".config" / "opencode" / "opencode.json"
    return json.loads(cfg.read_text())["provider"]["ppq"]["options"]["apiKey"]


def data_url(path):
    mime = "image/png" if path.suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


REF_NOTES = {
    "hard": "is the same unit as image 1, redrawn with every mass as a flat polygon: same "
            "design, same pose, same colours, the props still in place. Use it to read the "
            "shape of each block and each prop as faces rather than curves.",
    "hard-clean": "is the same unit with the props removed and the arms in an empty-handed "
                  "A-pose, still faceted: use it to read where each limb starts and ends and "
                  "how far the arms sit from the torso. It has no props.",
    "props": "is the same unit's props drawn detached at body scale. Model those props too, "
             "with the shapes and sizes drawn there, and attach them where image 1 shows them "
             "on the body.",
    "approved": "is the approved design that image 1 was redrawn from, with curves instead of "
                "facets. It is the contract for proportions and colour: where the two disagree "
                "on the size or place of a part, follow this one; build the shapes from image 1.",
}
HARD_FIRST = ("Image 1 is the faceted (hard) redraw of the approved design: every mass is "
              "already drawn as the flat polygons to build, props in place. Read each block's "
              "faces from it.")


def with_refs(brief, refs, hard_first=False):
    """Append one line per extra reference image, numbered the way the brief already
    numbers images (image 1 is the construction sheet: the hard one when it exists)."""
    lines = [HARD_FIRST] if hard_first else []
    lines += [f"Image {i} {REF_NOTES[kind]}" for i, (kind, _) in enumerate(refs, start=2)]
    if not lines:
        return brief
    return brief + "\nREFERENCE IMAGES\n" + "\n".join(lines) + "\n"


def prompt_images(args, work):
    """(image 1, [(kind, path)] extra references, temp files) for the spec author.
    The hard sheet is image 1 when it exists - the shapes are built from it - and the
    approved sheet stays out of the prompt (it is the judge) unless --with-sheet asks
    for it. Missing files are skipped: not every unit has props."""
    def small(src, name):
        p = work / f".{name}-{args.tag}-{args.id}.jpg"   # per run: parallel runs
        subprocess.run(["magick", str(src), "-resize", "1024x1024", "-quality", "88", str(p)],
                       check=True)
        return p
    first = small(args.build, "sheet")
    wanted = [("hard-clean", args.hard_clean), ("props", args.props)]
    if args.build != args.hard and args.hard:
        wanted.insert(0, ("hard", args.hard))           # no hard sheet: old order
    if args.with_sheet and args.build != args.sheet:
        wanted.insert(0, ("approved", args.sheet))
    refs = [(kind, small(src, f"ref-{kind}")) for kind, src in wanted if src and src.exists()]
    return first, refs, [first] + [p for _, p in refs]


def check_drift(args, layout):
    """Hard vs approved silhouettes, before anything is built: a hard sheet that moved
    away from the design is regenerated, not modelled. Reported, never fatal."""
    if args.build == args.sheet:
        return {}
    from silhouette import DRIFT_MIN, DRIFT_VIEWS, sheet_drift
    try:
        drift = sheet_drift(args.sheet, args.build, layout)
    except SystemExit as err:
        # a hard sheet that cannot be cut into its panels (wrong file, wrong layout) must
        # not end the run: build from the approved sheet and say why
        print(f"hard sheet unreadable ({err}): building from {args.sheet.name} instead")
        args.build = args.sheet
        return {}
    low = [v for v in DRIFT_VIEWS if drift.get(v, 1.0) < DRIFT_MIN]
    print(f"drift hard vs approved: {drift}"
          + (f"  - LOW on {low}: regenerate refs/{args.id}/sheet-hard.jpg" if low else "  ok"))
    return drift


def ask(model, brief, images):
    content = [{"type": "text", "text": brief}]
    content += [{"type": "image_url", "image_url": {"url": data_url(p)}} for p in images]
    body = {"model": model, "max_tokens": 9000, "temperature": 0.2,
            "messages": [{"role": "user", "content": content}]}
    req = urllib.request.Request("https://api.ppq.ai/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {api_key()}",
                                          "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=900))
    m = r["choices"][0]["message"]
    return m.get("content") or m.get("reasoning_content") or ""


ALIASES = {"upper_arm.L": "arm.L", "upper_arm.R": "arm.R", "lower_arm.L": "forearm.L",
           "lower_arm.R": "forearm.R", "forearm.L": "forearm.L", "forearm.R": "forearm.R",
           "chest": "spine", "torso": "spine", "hips": "pelvis", "hip": "pelvis",
           "neck": "head", "hand.L": "forearm.L", "hand.R": "forearm.R",
           "shoulder.L": "arm.L", "shoulder.R": "arm.R"}


def normalise(parts):
    out = []
    for p in parts:
        p = list(p)
        if RIG == "biped":
            p[0] = ALIASES.get(p[0], p[0])
        if isinstance(p[5], dict):
            opts = dict(p[5])
            if not isinstance(opts.get("rot", 0), (int, float)):
                opts.pop("rot", None)
            p[5] = opts
            # a from/to limb may leave `at` out: the builder places it at the midpoint
            if p[3] is None and "from" in opts and "to" in opts:
                p[3] = [(opts["from"][i] + opts["to"][i]) / 2 for i in range(3)]
        out.append(p)
    return out


def json_object(txt):
    txt = re.sub(r'\[\s*([A-Za-z_][\w.]*)\s*,',
                 lambda m: f'["{m.group(1)}",' if m.group(1) in BONES else m.group(0), txt)
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        raise ValueError("no JSON in the reply")
    return json.loads(m.group(0))


def parse_spec(txt):
    doc = json_object(txt)
    palette = check_palette(doc.get("palette") or {})
    extras = doc.get("bones") or []
    if len(extras) > 3:
        raise ValueError("more than 3 extra bones")
    RF.with_extras(RIG, extras)                      # ValueError when one does not fit
    spec = validate(normalise(doc.get("parts")), palette, {b[0] for b in extras})
    ground_fix(spec["parts"])                        # stand on y = 0 by construction
    if palette:
        spec["palette"] = palette
    if extras:
        spec["bones"] = extras
    return spec


def extra_names(spec):
    return {b[0] for b in spec.get("bones", [])}


def check_palette(palette):
    """{"slot": {"surface": <surfaces.SURFACES>, "color": "#RRGGBB", "alpha"?: 0-1}}
    or ValueError."""
    for name, entry in palette.items():
        colour = str(entry.get("color", ""))
        alpha = entry.get("alpha", 1.0)
        if (entry.get("surface") not in SURFACES
                or not re.fullmatch(r"#[0-9A-Fa-f]{6}", colour)
                or not (isinstance(alpha, (int, float)) and 0.0 < alpha <= 1.0)):
            raise ValueError(f"palette slot {name} outside the schema: {entry}")
    return palette


def apply_patch(parts, txt, limit=PASS_EDITS, palette=None, extra=()):
    """A refinement reply edits a few parts by index; the rest of the spec is untouched,
    so one view cannot rewrite the mass split another view already fixed."""
    patch = json_object(txt)
    sets, adds = patch.get("set", {}), patch.get("add", [])
    drops = {int(i) for i in patch.get("drop", [])}
    if len(sets) + len(adds) + len(drops) > limit:
        raise ValueError(f"patch edits more than {limit} parts")
    out = [list(p) for p in parts]
    for i, part in sets.items():
        out[int(i)] = part
    out = [p for i, p in enumerate(out) if i not in drops] + list(adds)
    parts = validate(normalise(out), palette, extra)["parts"]
    ground_fix(parts)
    return parts, patch.get("why", "")


def validate(parts, palette=None, extra=()):
    if not isinstance(parts, list) or not parts:
        raise ValueError("no parts array")
    for i, p in enumerate(parts):
        if (len(p) != 6 or p[0] not in BONES | set(extra) or p[1] not in KINDS
                or p[4] not in MATS | set(palette or {})
                or not isinstance(p[3], list)):
            raise ValueError(f"part {i} outside the schema: {p}")
        if p[3][1] < -0.01:
            raise ValueError(f"part {i} below the ground plane")
        if isinstance(p[5], dict) and p[5].get("decal", "eyes2") not in DECALS:
            raise ValueError(f"part {i} decal outside {sorted(DECALS)}")
    bad = misplaced_decals(parts)
    if bad:
        raise ValueError(f"decal on a non-head bone {bad}: eyes and faces go on a head/jaw part")
    return {"parts": parts}


def glb_stats(path):
    data = path.read_bytes()
    doc = json.loads(data[20:20 + int.from_bytes(data[12:16], "little")].decode("utf8", "ignore").rstrip("\0 "))
    tris = sum(doc["accessors"][p["indices"]]["count"] // 3
               for m in doc["meshes"] for p in m["primitives"])
    mats = [m["name"] for m in doc.get("materials", [])]
    return tris, mats, len(doc.get("skins", [])), len(doc.get("animations", []))


def tool(name, *argv, blender=False):
    cmd = (["blender", "-b", "-P", str(ROOT / "tools/blender" / name), "--"] if blender
           else [sys.executable, str(ROOT / "tools/blender" / name)])
    return subprocess.run(cmd + [str(a) for a in argv], capture_output=True, text=True)


def trial(spec, sheet, kind, work, name):
    """Preflight, build and measure one candidate spec. A preflight failure is reported,
    not fatal: the model is still built so there is always something to look at.
    Returns (IoU per view or None when no GLB came out, preflight report or None, zone
    report per view)."""
    path = work / f"{name}.json"
    path.write_text(json.dumps(spec, indent=2))
    glb = work / f"{name}.glb"
    pre = tool("preflight.py", path, kind, sheet)     # landmark targets from this sheet
    problem = pre.stdout if pre.returncode else None
    build = tool("build_unit.py", path, glb, blender=True)
    if not glb.exists():
        return None, (problem or "") + build.stderr[-400:], None
    tool("silhouette.py", sheet, glb, work / f"{name}-sil", "--layout", layout_of(kind))
    report = json.loads((work / f"{name}-sil" / "silhouette.json").read_text())
    tool("render_unit.py", glb, work / f"{name}-views", tilt_arg(report), blender=True)
    return ({view: r["iou"] for view, r in report.items()}, problem,
            {view: r["zones"] for view, r in report.items() if "zones" in r})


def tilt_arg(report):
    """render_unit.py argument that shoots top/bottom and the RTS view from the camera
    silhouette.py matched; the RTS camera is an (elevation, azimuth) pair."""
    def value(tilt):
        return "/".join(map(str, tilt)) if isinstance(tilt, (list, tuple)) else str(tilt)
    return "tilt=" + ",".join(f"{v}:{value(r['tilt'])}" for v, r in report.items()
                              if r.get("tilt"))


def numbered(spec):
    """The spec as a refinement prompt shows it: the fixed palette, then indexed parts."""
    lines = [f"  {i}: {json.dumps(p)}" for i, p in enumerate(spec["parts"])]
    if spec.get("bones"):
        lines.insert(0, f"  extra bones (fixed): {json.dumps(spec['bones'])}")
    if spec.get("palette"):
        lines.insert(0, f"  palette (fixed - use only these slot names): {json.dumps(spec['palette'])}")
    return "\n".join(lines)


def repair(spec, args, brief, work, panels):
    """Pass 0: the preflight's failing rules go back to the model as a patch request.
    A repair is kept only when it still builds; the passes run either way."""
    scores, problem, zones = trial(spec, args.build, args.kind, work, "pass0")
    best = "pass0"  # the trial whose renders show the spec held
    for k in range(1, REPAIRS + 1):
        if problem is None:
            break
        print(f"repair {k}: preflight fails\n{problem.strip()}")
        prompt = REPAIR.format(problem=problem, parts=numbered(spec),
                               limit=REPAIR_EDITS, brief=brief)
        try:
            cand, _ = apply_patch(spec["parts"], ask(args.model, prompt,
                                  [panels["front"], panels["left"]]), REPAIR_EDITS,
                                  spec.get("palette"), extra_names(spec))
        except (ValueError, IndexError, KeyError, json.JSONDecodeError) as err:
            print(f"repair {k}: rejected reply: {err}")
            continue
        cur, cur_problem, cur_zones = trial({**spec, "parts": cand}, args.build, args.kind, work,
                                            f"repair{k}")
        # a repair that builds and breaks no rule that held
        if cur is not None and rules_hold(problem, cur_problem):
            spec, scores, problem, zones, best = ({**spec, "parts": cand}, cur, cur_problem,
                                                  cur_zones, f"repair{k}")
    return spec, scores, problem, zones, best


def failing_rules(problem):
    """Names of the rules a preflight report (its stdout, or None when clean) fails. A report
    with no readable rule line is one unnamed failure, so it never matches a clean one."""
    if problem is None:
        return set()
    return {name for name, result in RULE_LINE.findall(problem) if result == "FAIL"} or {"<unparsed>"}


def rules_hold(prev, cur):
    """No preflight rule that held may start failing: the set of passing rules only grows.
    Generic by rule name, so rules added to preflight.py are covered without a change here."""
    return failing_rules(cur) <= failing_rules(prev)


def zone_view_holds(prev, cur):
    """One view's zone report, before and after: the mean, every zone big enough to weigh and
    every drawn piece may fall only so far. A zone lost whole is a fall of its whole IoU."""
    from silhouette import ZONE_SHARE
    if cur["mean"] < prev["mean"] - ZONE_DROP:
        return False
    zone_lost = any(z["share"] >= ZONE_SHARE and cur["zones"].get(k, {"iou": 0.0})["iou"] < z["iou"] - ZONE_LOSS
                    for k, z in prev["zones"].items())
    piece_lost = any(cur["pieces"].get(k, 0.0) < v - PIECE_LOSS for k, v in prev["pieces"].items())
    return not (zone_lost or piece_lost)


def zones_hold(prev, cur):
    """True when no view measured both times lost colour inside its contour."""
    if not prev or not cur:
        return True
    return all(zone_view_holds(prev[v], cur[v]) for v in prev.keys() & cur.keys())


def accepted(prev, cur, view, *, zones=(None, None), problems=(None, None)):
    """The pass's own view must improve, no gated view may slip, no colour zone or drawn piece
    may be lost (`zones`: before, after) and no preflight rule that held may break
    (`problems`: before, after)."""
    from silhouette import GATES
    return (cur is not None and cur[view] > prev[view]
            and all(cur[g] >= prev[g] - REGRESSION for g in GATES)
            and zones_hold(*zones) and rules_hold(*problems))


def zone_scores(zones):
    """{view: {"mean", "cover", "lost", "zones": {hex: iou}}}: the zone numbers worth a log line."""
    return {v: {**{k: z[k] for k in ("mean", "cover", "lost")},
                "zones": {h: g["iou"] for h, g in z["zones"].items()}}
            for v, z in (zones or {}).items()}


def zones_of(report):
    """zone_scores of a silhouette.json report (views without zones are left out)."""
    return zone_scores({v: r["zones"] for v, r in report.items() if "zones" in r})


def run_passes(spec, args, brief, views):
    """Refine the spec one concept view at a time: concept panel, model render and the
    silhouette overlay of that view go back to the model, which answers with a patch."""
    from split_sheet import split
    if not set(views) <= AXES.keys():
        raise SystemExit(f"--passes takes views from {sorted(AXES)}, got {views}")
    work = args.out / "passes" / f"{args.tag}-{args.id}"
    panels = split(args.build, work / "panels", args.id, layout_of(args.kind))
    spec, scores, problem, zones, best = repair(spec, args, brief, work, panels)
    if scores is None:
        print("passes: no GLB came out of the sheet spec; skipping refinement")
        return spec
    log = [{"pass": 0, "view": "sheet", "scores": scores, "preflight": problem is None,
            "failing": sorted(failing_rules(problem)), "zones": zone_scores(zones)}]
    print(f"pass 0 sheet  {scores}  preflight {'PASS' if problem is None else 'FAIL'}")
    for n, view in enumerate(views, 1):
        prompt = REFINE.format(view=view, scores=scores, axes=AXES[view],
                               parts=numbered(spec),
                               limit=PASS_EDITS, brief=brief)
        shot = RENDER_NAME.get(view, view)
        images = [panels[view], work / f"{best}-views" / f"{best}-{shot}.png",
                  work / f"{best}-sil" / f"overlay-{view}.png"]
        try:
            cand, why = apply_patch(spec["parts"], ask(args.model, prompt, images),
                                    palette=spec.get("palette"), extra=extra_names(spec))
            cur, cur_problem, cur_zones = trial({**spec, "parts": cand}, args.build, args.kind,
                                                work, f"pass{n}")
        except (ValueError, IndexError, KeyError, json.JSONDecodeError) as err:
            cand, why, cur, cur_problem, cur_zones = None, f"rejected reply: {err}", None, None, None
        ok = accepted(scores, cur, view, zones=(zones, cur_zones), problems=(problem, cur_problem))
        if ok:
            spec, scores, problem, zones, best = ({**spec, "parts": cand}, cur, cur_problem,
                                                  cur_zones, f"pass{n}")
        log.append({"pass": n, "view": view, "why": why, "scores": cur, "accepted": ok,
                    "preflight": cur_problem is None, "failing": sorted(failing_rules(cur_problem)),
                    "zones": zone_scores(cur_zones)})
        print(f"pass {n} {view:5} {'ACCEPT' if ok else 'reject'} {cur}  {why}")
    (work / "passes.json").write_text(json.dumps(log, indent=2))
    return spec


def silhouette_vs(args, glb, layout, sheet, name):
    """(gate passed, per-view report) of the model against one sheet."""
    sil_dir = args.out / "sil" / name
    sil = tool("silhouette.py", sheet, glb, sil_dir, "--layout", layout)
    print(f"vs {name}:\n{sil.stdout.strip()}")
    return sil.returncode == 0, json.loads((sil_dir / "silhouette.json").read_text())


def review(args, glb, layout):
    """The verdict is the approved sheet's silhouette gate - the design contract, what
    the human reviewer compares against too. The model is also measured against the
    hard sheet it was built from (did it follow its input?), and both land in the run's
    silhouette.json with the hard-vs-approved drift. Then the colour views and the
    compare, shot from the cameras the approved silhouette matched."""
    sil_ok, report, summary = True, {}, {"drift": args.drift}
    if not args.no_silhouette:
        sil_ok, report = silhouette_vs(args, glb, layout, args.sheet, "approved")
        summary["approved"] = {k: r["iou"] for k, r in report.items()}
        summary["zones"] = {"approved": zones_of(report)}
        if args.build != args.sheet:
            _, hard = silhouette_vs(args, glb, layout, args.build, "hard")
            summary["hard"] = {k: r["iou"] for k, r in hard.items()}
            summary["zones"]["hard"] = zones_of(hard)
        summary["prop"] = prop_report(args)
        (args.out / "silhouette.json").write_text(json.dumps(summary, indent=2))
    args.summary = summary
    view_dir = args.out / "views" / args.tag
    compare = args.out / "compare.png"
    tool("render_unit.py", glb, view_dir, tilt_arg(report), blender=True)
    tool("make_compare.py", args.sheet, view_dir, glb.stem, compare, "--layout", layout)
    if args.build != args.sheet:
        # the same renders against the faceted drawing the model was built from: what the
        # silhouette cannot see (a chest disc, a hood, a club) shows up here
        tool("make_compare.py", args.build, view_dir, glb.stem, args.out / "compare-hard.png",
             "--layout", layout)
    return sil_ok


def make_brief(args, lo, hi):
    """The spec brief for this sheet: the unit brief, or the building brief for a
    static rig, both around the same part DSL and code-measured numbers."""
    from silhouette import measure, sheet_colours
    limb_note, rig_note = rig_text(args.rig)
    dsl = DSL.format(height=args.height or round(RF.top(args.rig), 2), limb_note=limb_note,
                     surfaces=", ".join(SURFACES),
                     colours=", ".join(f"{h} {round(100 * f)}%" for h, f in sheet_colours(args.build)))
    template = BUILDING_BRIEF if args.rig in RF.STATIC else BRIEF
    return template.format(race=args.race, name=args.name, uid=args.id, role=args.role,
                           dsl=dsl, budget=f"{lo} to {hi}", bones=rig_table(), rig_note=rig_note,
                           measured=measured_text(args.rig, measure(args.build)))


RTS_TRIES = 3          # image-to-image draws per RTS view before the warning
FIGURE_MIN = 0.10      # a blob smaller than this share of the foreground is a shadow or a prop bit
FIGURE_ERODE = 9   # px at 512: splits n00U's touching spiders, keeps all 21 good RTS at 1


def count_figures(mask, min_share=FIGURE_MIN):
    """Figures drawn in a foreground mask: connected blobs holding at least `min_share` of
    the foreground, after a FIGURE_ERODE px erosion so figures touching by a leg tip still
    count apart (loose legs fall under `min_share`). A good RTS view is 1; n01N once came
    out as three spiders, n00U's hard RTS as three spiders touching legs."""
    import numpy as np
    from scipy import ndimage as ndi
    lab, n = ndi.label(ndi.binary_erosion(mask, iterations=FIGURE_ERODE))
    if not n:
        return 0
    area = np.bincount(lab.ravel())[1:]
    return int((area >= min_share * area.sum()).sum())


def rts_figures(path):
    """count_figures of an RTS image on disk, keyed like the silhouette gate."""
    from silhouette import foreground
    return count_figures(foreground(path, 512))


def ensure_rts(sheet, building=False, force=False):
    """Draw the gameplay-camera concept from the approved sheet when it is missing (or
    `force`): the compare, the silhouette sweep and the rts pass all need it. The draw is
    repeated up to RTS_TRIES times while it shows more than one figure; a failed call or a
    still-crowded image is reported and the run goes on with it."""
    from silhouette import rts_path
    if rts_path(sheet).exists() and not force:
        return True
    sheets = ROOT / "artifacts/model-sheets"
    if building:
        template = TEMPLATES / "00-template-rts-building.txt"
    else:
        # a hard sheet keeps its facets in the gameplay camera: same angle, same blockout
        hard = "hard" in sheet.stem
        template = TEMPLATES / ("00-template-rts-hard.txt" if hard else "00-template-rts.txt")
    for attempt in range(1, RTS_TRIES + 1):
        gen = subprocess.run([sys.executable, str(sheets / "generate.py"), str(template),
                              "--image", str(sheet), "--out", str(sheet.parent),
                              "--name", rts_path(sheet).stem, "--resolution", "1K"],
                             capture_output=True, text=True)
        print(gen.stdout.strip() or f"rts view not drawn: {gen.stderr.strip()[-200:]}")
        if not rts_path(sheet).exists():
            return False
        figures = rts_figures(rts_path(sheet))
        if figures == 1:
            return True
        print(f"rts view {rts_path(sheet).name}: {figures} figures (try {attempt}/{RTS_TRIES})")
    print(f"WARNING: {rts_path(sheet).name} still shows {figures} figures; the rts view may mislead")
    return True


def check_rts(refs=None):
    """{image name: figures} for every existing RTS view under refs/ (one is right)."""
    return {f"{p.parent.name}/{p.name}": rts_figures(p)
            for p in sorted((refs or REFS).glob("*/*-rts.jpg"))}


MSHEETS = ROOT / "artifacts/model-sheets"
REFS = MSHEETS / "refs"
PROMPTS = MSHEETS / "prompts"
TEMPLATES = PROMPTS   # shared 00-template-*.txt recipes; prompts/<id>/ holds the filled ones
RUNS = MSHEETS / "runs" / "draft"


def iou_rows(summary):
    """review.md rows: front/left/back IoU against each sheet, and the drift."""
    def row(label, d):
        return f"| {label} | " + " / ".join(f"{d.get(v, 0):.3f}" for v in ("front", "left", "back")) + " |\n"
    out = ""
    for key, label in (("approved", "IoU vs approved f/l/b"), ("hard", "IoU vs hard f/l/b"),
                       ("drift", "drift hard vs approved f/l/b")):
        if summary.get(key):
            out += row(label, summary[key])
    return out


def prop_report(args):
    """The held prop built and rendered alone, against the props sheet (prop_measure.py):
    {"parts", "iou", "view", "component"}, or None when the unit has no props sheet. A signal,
    not a gate: which spec parts are the prop is a heuristic, so a low number warns (PROP_WARN)
    and the human looks at the compare."""
    if not args.props.exists() or args.rig != "biped":
        return None
    run = tool("prop_measure.py", args.props, args.out / "spec.json", args.out / "prop")
    try:
        return json.loads(run.stdout)
    except ValueError:
        print(f"prop not measured: {run.stderr.strip()[-200:]}")
        return None


def prop_row(summary):
    """review.md row for the prop-alone IoU, with a warning under PROP_WARN."""
    prop = summary.get("prop")
    if not prop:
        return ""
    if prop["iou"] is None:
        return "| prop alone vs props sheet | no arm-held prop found in the spec |\n"
    warn = " WARN: the prop is off its drawing" if prop["iou"] < PROP_WARN else ""
    return (f"| prop alone vs props sheet (parts {','.join(map(str, prop['parts']))}) | "
            f"{prop['iou']:.3f} ({prop['view']}){warn} |\n")


def zone_rows(summary):
    """review.md rows: colour-zone mean / cover per view and the front's zone IoUs, per sheet."""
    out = ""
    for key in ("approved", "hard"):
        z = summary.get("zones", {}).get(key)
        if not z:
            continue
        views = [v for v in ("front", "left", "back") if v in z]
        out += (f"| colour zones vs {key}, mean / cover f/l/b | "
                + " ; ".join(f"{z[v]['mean']:.2f} / {z[v]['cover']:.2f}" for v in views) + " |\n")
        if "front" in z:
            lost = f" LOST {', '.join(z['front']['lost'])}" if z["front"]["lost"] else ""
            out += (f"| zone IoU, front vs {key} | "
                    + ", ".join(f"{h} {i:.2f}" for h, i in z["front"]["zones"].items()) + f"{lost} |\n")
    return out


def resolve_paths(args):
    """Fill the refs/<id>/ defaults and pick the run dir runs/<id>/<run> (next free vN)."""
    args.sheet = args.sheet or REFS / args.id / "sheet.jpg"
    args.hard = args.hard or (REFS / args.id / "sheet-hard.jpg")
    args.hard_clean = args.hard_clean or (REFS / args.id / "sheet-hard-clean.jpg")
    args.props = args.props or (REFS / args.id / "sheet-props.jpg")
    if args.out is not None:
        return
    rundir = RUNS / args.id
    if not args.run:
        n = 1
        while (rundir / f"v{n}").exists():
            n += 1
        args.run = f"v{n}"
    args.out = rundir / args.run


def main():
    if sys.argv[1:] == ["--check-rts"]:   # figures per existing RTS view; no other flag needed
        for name, n in check_rts().items():
            print(f"{n} {name}")
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--race", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--role", default="game unit")
    ap.add_argument("--run", default=None,
                    help="run/iteration name under runs/<id>/ (default: next vN not taken)")
    ap.add_argument("--sheet", type=pathlib.Path, default=None,
                    help="approved sheet; default refs/<id>/sheet.jpg")
    ap.add_argument("--hard", type=pathlib.Path, default=None,
                    help="hard-edged faceted sheet, props in place; default refs/<id>/sheet-hard.jpg. "
                         "Sent as an extra reference; never replaces --sheet or the gate")
    ap.add_argument("--hard-clean", type=pathlib.Path, default=None,
                    help="same unit faceted, props removed, empty-handed A-pose; default "
                         "refs/<id>/sheet-hard-clean.jpg")
    ap.add_argument("--props", type=pathlib.Path, default=None,
                    help="props drawn detached; default refs/<id>/sheet-props.jpg")
    ap.add_argument("--image1", choices=("hard", "sheet"), default="hard",
                    help="what the spec author builds from: the hard sheet (default) or the "
                         "approved sheet with the hard one as an extra image (PIPELINE §16.1)")
    ap.add_argument("--with-sheet", action="store_true",
                    help="also send the approved sheet to the spec author (A/B against the "
                         "default, where the hard sheet alone is image 1)")
    ap.add_argument("--model", default="google/gemini-4-argon")
    ap.add_argument("--tag", default="argon", help="spec-author label, recorded in review.md")
    ap.add_argument("--rig", default=None, choices=sorted(RF.FAMILIES),
                    help="skeleton family (rig_families.py); default biped, or building "
                         "for --kind building/large")
    ap.add_argument("--height", type=float, default=None,
                    help="unit height in metres (default: the rig's own height)")
    ap.add_argument("--kind", default="mass", choices=BUDGETS.keys())
    ap.add_argument("--flat", action="store_true",
                    help="skip the procedural painted texture (on by default)")
    ap.add_argument("--style", choices=("cel", "painted"), default="cel",
                    help="texture style: cel = flat tone per face like the hard sheet (default); "
                         "painted = the older painted gloss and pattern")
    ap.add_argument("--no-silhouette", action="store_true", help="skip the IoU gate")
    ap.add_argument("--no-rts", action="store_true",
                    help="do not draw the RTS concept view when the sheet has none")
    ap.add_argument("--spec", type=pathlib.Path, default=None,
                    help="start from this spec JSON instead of asking the model for one")
    ap.add_argument("--no-repair", action="store_true",
                    help="skip the pass-0 repair of preflight failures (on by default)")
    ap.add_argument("--passes", default="",
                    help="comma-separated views to refine after the sheet pass, e.g. left,back,front")
    ap.add_argument("--out", type=pathlib.Path, default=None,
                    help="run dir; default runs/<id>/<run>")
    args = ap.parse_args()

    resolve_paths(args)

    lo, hi = BUDGETS[args.kind]
    layout = layout_of(args.kind)
    args.rig = args.rig or ("building" if layout == "building" else "biped")
    args.out.mkdir(parents=True, exist_ok=True)
    if not args.no_rts:
        ensure_rts(args.sheet, building=args.kind in ("building", "large"))
        for ref in (args.hard, args.hard_clean):
            if ref:
                ensure_rts(ref, building=args.kind in ("building", "large"))

    # construction sheet: the hard redraw when there is one; the approved sheet judges
    args.build = (args.hard if args.image1 == "hard" and args.hard and args.hard.exists()
                  else args.sheet)
    args.drift = check_drift(args, layout)
    sheet, refs, tmp = prompt_images(args, args.out / ".." / "..")
    args.refs = refs
    set_rig(args.rig)
    brief = with_refs(make_brief(args, lo, hi), refs, hard_first=args.build != args.sheet)
    # --spec resumes from an approved spec: only the refinement passes call the model
    spec = (parse_spec(args.spec.read_text()) if args.spec
            else parse_spec(ask(args.model, brief, [sheet] + [p for _, p in refs])))
    spec["rig"] = args.rig
    for p in tmp:
        p.unlink(missing_ok=True)
    # the repair pass (preflight failures -> patch) runs even without --passes: it is
    # what pulls a too-wide body back to its sheet (hfoo shoulders 0.66 -> 0.51, sheet 0.46)
    if args.passes or not args.no_repair:
        spec = run_passes(spec, args, brief, args.passes.split(",") if args.passes else [])
    spec_path = args.out / "spec.json"
    spec_path.write_text(json.dumps(spec, indent=2))

    # The spec is cheap to reject; the build is not. Preflight now runs before Blender.
    pre = subprocess.run([sys.executable, str(ROOT / "tools/blender/preflight.py"),
                          str(spec_path), args.kind, str(args.sheet)], capture_output=True, text=True)
    print(pre.stdout.strip())
    if pre.returncode:
        print(f"{args.id}\t{args.tag}\tpreflight FAIL - building anyway, verdict will be CHECK")

    glb = args.out / "model.glb"
    # the first number is what chamfers may spend up to: the budget ceiling, the same
    # one the gate checks (lo + hi let a box-heavy building chamfer itself to 1100+ tris)
    extra = [] if args.flat else [str(hi), "nofuse", str(hi), "tex", f"style={args.style}"]
    build = subprocess.run(["blender", "-b", "-P", str(ROOT / "tools/blender/build_unit.py"),
                            "--", str(spec_path), str(glb)] + extra, capture_output=True, text=True)
    if not glb.exists():
        print(f"{args.id}\t{args.tag}\tBUILD FAILED\t{build.stderr[-200:]}")
        return 1
    smear = re.search(r"normal smear on \d+ flat faces \(([\d.]+)%", build.stdout + build.stderr)
    smear_pct = float(smear.group(1)) if smear else 0.0

    tris, mats, skins, anims = glb_stats(glb)
    frames = pathlib.Path(f"/tmp/orbit-{args.tag}-{args.id}")
    subprocess.run(["blender", "-b", "-P", str(ROOT / "tools/blender/turntable_color.py"),
                    "--", str(glb), str(frames), "24", "420"], capture_output=True, text=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(frames / "orbit-%03d.png"),
                    "-vf", "fps=12,scale=420:-1:flags=lanczos", "-loop", "0",
                    str(args.out / "turntable.gif")], check=False)
    subprocess.run(["rm", "-rf", str(frames)], check=False)

    sil_ok = review(args, glb, layout)
    ok = (not pre.returncode and lo <= tris <= hi and MATERIAL_SLOTS[0] <= len(mats) <= MATERIAL_SLOTS[1] and skins == 1
          and anims == (0 if args.rig in RF.STATIC else 4)
          and smear_pct <= 0.5 and sil_ok)
    verdict = "PASS" if ok else "CHECK"
    (args.out / "review.md").write_text(
        f"# {args.id} \u2014 run {args.run} ({args.tag})\n\n"
        f"- model: {args.model}\n- spec author: {args.tag}\n- kind: {args.kind}\n"
        f"- judge (approved sheet): {args.sheet}\n- built from (image 1): {args.build}\n"
        f"- extra refs: {', '.join(k for k, _ in args.refs) or '-'}\n\n"
        f"| gate | value |\n|---|---|\n"
        f"| preflight | {'FAIL' if pre.returncode else 'PASS'} |\n"
        f"| tris | {tris}/{lo}-{hi} |\n| materials | {len(mats)} |\n| skins | {skins} |\n"
        f"| anims | {anims} |\n| smear | {smear_pct}% |\n"
        f"| silhouette + colour zones (vs approved: the gate) | {'PASS' if sil_ok else 'FAIL'} |\n"
        f"{iou_rows(args.summary)}{zone_rows(args.summary)}{prop_row(args.summary)}\n"
        f"verdict: **{verdict}**\n\n"
        f"artifacts: spec.json, model.glb, compare.png (vs the approved sheet), compare-hard.png "
        f"(vs the hard sheet), turntable.gif, "
        f"silhouette.json\n")
    print(f"{args.id}\t{args.run}\t{args.tag}\ttris {tris}/{lo}-{hi}\tmats {len(mats)}\tskins {skins}\t"
          f"anims {anims}\tsmear {smear_pct} %\tpreflight {'FAIL' if pre.returncode else 'PASS'}\t"
          f"silhouette {'PASS' if sil_ok else 'FAIL'}\t{verdict}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
