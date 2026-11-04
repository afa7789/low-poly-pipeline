#!/usr/bin/env python3
"""One unit, end to end: sheet -> spec (vision model) -> clay GLB -> shape gates -> colour -> GIF.

    python3 tools/blender/spec_pipeline.py --id n01X --race Mech --name "Iron Golem"
    python3 tools/blender/spec_pipeline.py --id hfoo --race Human --name Footman \\
        --model claude-opus-5.5 --tag opus55 --run opus55

Inputs default to refs/<id>/ (sheet.jpg judges, sheet-hard.jpg builds; sheet-hard-clean.jpg
and sheet-props.jpg ride along when present); the run lands in runs/draft/<id>/<run>/.

Triangle budgets, WC3 SD standard (see PIPELINE.md §6):
    mass unit 400-700 · hero 900-1600 · standard building 600-800 · town hall / large 2000-3000

Stage 0, massing (massing.py, PIPELINE.md section 21.F1): before the author, code reads the sheet's
silhouettes and the rig and writes a pre-spec, one mass per bone; it is built and measured alone
(<out>/massing/) and goes into the brief as JSON, so the author EDITS it instead of writing the
mass. --no-massing keeps the old brief.

Two stages, in sequence (PIPELINE.md section 18.F):

    stage 1, shape (this file, stage_shape): the spec is repaired/refined and built in CLAY
        (build_unit.py `clay`: one grey material, no texture, decal or glow). Repair and
        passes only ever see clay renders plus the silhouette overlay. Gate = preflight +
        tris + rig + silhouette.GATES on front/left/back/top/bottom/rts (top/bottom/rts at
        the camera the sweep picked). A spec that fails stage 1 stops here: no texture, no
        turntable, no stage 2; review.md says where it stopped.
    stage 2, colour (tools/blender/colour_stage.py, optional): the approved spec, frozen,
        gets texture, decals and glow. The contract, called by main() only when the module
        imports:

            colour_stage.stage_colour(spec, glb_clay, args, tilts, work) -> (ok, report)

        spec      the stage 1 spec dict (parts never change in stage 2)
        glb_clay  Path of the stage 1 GLB (<out>/clay.glb)
        args      the argparse namespace (out, id, kind, rig, sheet, build, texture, flat,
                  summary = the silhouette.json dict stage 1 wrote)
        tilts     tilts_of() of the stage 1 sweep: {"top": 10, "bottom": 20, "rts": (35, 30)}
        work      scratch dir <out>/stage2
        ok        stage 2 gate; report: str, or a dict that review.md prints as JSON
        It writes <out>/model.glb (main() shoots the turntable from it when ok) and the
        textured views as views/<id>/model-<view>.png. It may add a "zones" key to
        args.summary and to <out>/silhouette.json (zone_rows() prints it in review.md).
    Without colour_stage (or with --shape-only) main() ends cleanly after stage 1.

Writes, under <out>:
    spec.json, clay.glb, model.glb (stage 2)        the result
    review.md, silhouette.json, turntable.gif       the verdict, one section per stage
    views/<id>/clay-<view>.png                      stage 1 renders (lit clay), view in
                                                    front/left/back/top/bottom/rts
    views/<id>/wire-<view>.png                      the same clay with its triangle edges (compare `wire`)
    sil/, passes/                                   local intermediates (gitignored)
and prints one gate line: id, run, tag, tris, budget, skins, anims, smear, preflight, stage 1,
stage 2, verdict. Exit code 1 if a stage fails; a failed gate never stops the run before its
own stage ends, every output is still written.
"""
import argparse
import base64
import collections
import copy
import types
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

import building_hull
import cut_hull
import align_features
import deform_to_sheet
import inscribe
import optimize_verts
import overrides
import diagnose
import lathe_limb
import depth_rule
import look
import loop_stage
import noise as NZ
import author_guard
import dsl_rules
import part_rules
import massing
import mesh_lint
import review_pair
import rig_families as RF
from surfaces import DECALS, SURFACES
import views as view_defs
from views import layout_of

ROOT = pathlib.Path(__file__).resolve().parents[2]
SKILLS = pathlib.Path.home() / ".config" / "opencode" / "skills"
RIG_MEASURE = None            # the sheet's spider numbers when the rig was scaled by them
RIG = "biped"                    # the family every bone name is checked against
BONES = set(RF.bones(RIG))
KINDS = {"box", "cyl", "wheel", "prism", "dome", "frustum", "ring", "lathe", "limb", "chain", "plate"}
MATS = {"iron", "darkiron", "brass", "flame", "lamp"}   # n01X slots, always valid (metal)
from preflight import BUDGETS, CLIPS, SOFT_RULES, bbox, part_tris, ground_fix, identity_items, identity_summary, identity_texts, face_kind, load as load_spec, load_props, misplaced_decals, normalise as snap_parts, split_bands, GROUPS  # noqa: E402  (one table for pipeline and gate)

DSL = """Write a Blender part spec as a JSON object: {{"palette": {{"<slot>": {{"surface": "<surface>", "color": "#RRGGBB"}}, ...}}, "parts": [[bone, kind, dims, at, material, opts], ...]}}

Kinds and dims, exactly:
- "prism": a tapered n-gon tube - THE limb and torso primitive. dims = (radius_bottom, radius_top, height). opts {{"sides": 6 or 8, "axis": "up" | "fwd"}}. Use a smaller radius_top so the limb tapers away from the body.
- "frustum": a box with a scaled, offset top - THE wedge primitive. dims = (width_x, height_y, depth_z). opts {{"top": (scale_x, scale_z), "shift": (offset_x, offset_z), "sides": 4 (default; 6 to 8 = a rounded n-gon inscribed in the width x depth box, 4*sides-4 triangles)}}. Use for boots, trapezoid pelvis, waist taper and stepped fists; a boot or a torso slice with "sides": 8 reads round from above.
- "ring": a flat annulus with optional spokes and hub - THE valve-wheel primitive. dims = (outer_radius, radial_width, thickness). opts {{"sides": 10, "spokes": 3, "hub": 0.05, "axis": "up" | "fwd" | "side", "tilt": degrees, "spin": degrees}}. `axis` is the disc normal; a halo/steering wheel is axis "up" with tilt 20-30, NOT a disc facing the camera.
- "lathe": a body of revolution around the vertical axis through `at` - THE hood, torso and spider-abdomen primitive (a round mass a box or prism cannot draw). dims = (r, height), `at` = its centre. The width of the mass at each height is a profile: opts {{"profile": [6 to 10 radii, bottom to top, each a fraction of r, 0.05 to 1.5], "sides": 6 to 8 (default 8), "squash": x/z ratio (default 1; 1.2 = wider than deep), "axis": "front" | "left" | "z"}}. Without "profile" the build reads it from the sheet: the width of the figure in the part's height band, from the sheet's front panel (or the left one with "axis": "left"), limited to 1.25 r each side of `at` so a neighbouring arm is not read; then r is the radius you expect at the widest row. About 90 triangles. "profile" may also be 3 to 10 RINGS [w, d, zc, xc, t] (the massing pre-spec writes its torso, pelvis and head so): x radius r*w, z radius r*d, ring centre offset (zc, xc)*r from `at`, t = the ring's height in 0-1 of h; keep the ring list and edit its numbers ("corner" 0-1 pushes the 8-gon's corners out). "axis": "z" lays the lathe along z (a quadruped's trunk): dims (r, length), rings [w, hh, yc, xc, t] = x radius r*w, y radius r*hh, centre offset (yc, xc)*r from `at`, t = the ring's place along z in 0-1 of the length, a ring profile is required. No rot, no from/to, no cut. Examples: a hood on the head bone {{"lathe", dims [0.42, 0.6], opts {{"squash": 1.05}}}}; a torso on spine {{"lathe", dims [0.45, 0.75], opts {{"profile": [0.7, 0.85, 0.95, 1.0, 1.0, 0.8], "sides": 8}}}}; a spider abdomen on the abdomen bone {{"lathe", dims [0.3, 0.45], opts {{"profile": [0.4, 0.85, 1.0, 0.9, 0.6, 0.25], "squash": 0.9}}}}.
- "limb": two tapered tubes from `from` to `to` with a knee between them - THE leg and arm primitive, one part where you would put two prisms or cylinders. dims = (r_top, r_knee, r_base), the radii at `from`, at the knee and at `to`. opts {{"from": [x,y,z], "to": [x,y,z], "knee": [fraction 0.15 to 0.85, dx, dz] (default [0.5, 0, 0]), "sides": 6 to 8 (default 8)}}. The knee sits at from + fraction * (to - from) + (dx, 0, dz): dx moves it sideways, dz forward (a bent knee points forward, dz > 0); add a fourth number to lift it (an arched spider leg: [0.5, 0.1, 0, 0.3]). Bind it to the upper bone (thigh.L, arm.L, leg3.upper): the upper tube follows that bone, the lower tube follows its pair (shin.L, forearm.L, leg3.lower) when the rig has one. About 44 triangles. Example: a left leg {{"limb", dims [0.2, 0.17, 0.14], opts {{"from": [0.28, 1.1, 0], "to": [0.28, 0.1, 0.05], "knee": [0.5, 0, 0.08]}}}}; a spider leg {{"limb", dims [0.05, 0.03, 0.018], opts {{"from": [0.17, 0.46, 0.09], "to": [0.39, 0.04, 0.16], "knee": [0.76, 0.05, 0]}}}}.
- "chain": ONE smooth body along a run of the rig's numbered bones (tail.1.., neck.1.., spine.1.. of a serpent, wyrm or naga) - THE tail, neck and serpent-body primitive, one part where you would put a prism per bone. bone = the FIRST bone of the run (tail.1); opts {{"bones": N}} = how many bones it follows (the RIG TABLE lists them), dims = [r0, .. rN] = the radius at each of the N+1 joints, head to tail (a tail tapers: [0.2, 0.17, 0.12, 0.05]); or dims = [r] with the build reading the widths from the sheet's left panel ("profile_axis": "left" | "front"). `at` is ignored (write [0, 0, 0]): the bones place it. Each joint is a ring that bends with its bone. opts "sides": 6 to 8 (default 8). Triangles: 2 * sides * N + 2 * (sides - 2). No rot, no from/to, no cut. Examples: a drake tail {{"tail.1", "chain", dims [0.22, 0.17, 0.11, 0.04], at [0, 0, 0], opts {{"bones": 3}}}}; a drake neck {{"neck.1", "chain", dims [0.2, 0.15, 0.12], at [0, 0, 0], opts {{"bones": 2, "sides": 8}}}}; a serpent body {{"spine.1", "chain", dims [0.34, 0.4, 0.42, 0.4, 0.34, 0.26, 0.17, 0.1, 0.05], at [0, 0, 0], opts {{"bones": 8}}}}.
- ROTATION: a box, prism, frustum or dome that is not a from/to part takes opts {{"rot": [rx, ry, rz]}}, degrees, each within +-60, turning around the part centre. rx: top tips forward (+z). ry: turns around up (front toward +x). rz: top tips toward -x, so the bottom swings toward +x. Examples: a hanging arm 15 degrees out is a prism with "rot": [0, 0, 15] when it stands at +x and [0, 0, -15] at -x; a drooping pauldron slab "rot": [0, 0, 20] at +x; a hood tipped forward a frustum with "rot": [25, 0, 0]; a leg stepping out [0, 0, 12] at +x. The preflight measures the rotated part, so keep `at` at the part centre.
- "plate": a flat polygon extruded along its normal - THE wing, shell-with-overhang, fin, rudder and armour-plate primitive (an outline a box cannot draw). dims = (w, h, t) around `at`: w and h span the polygon, t is the thickness. opts {{"axis": "front" | "left" | "top" (the sheet panel it is read from and the plane the polygon lies in: front = x/y with thickness along z, left = z/y with thickness along x, top = x/z with thickness along y; default "front"), "profile": [3 to 8 points [u, v], each 0 to 1 of w and h] (u runs along x, or z for left; v runs up, or forward for top), "bevel": 0 to 0.3 (the faces shrink by that fraction), "rot": degrees allowed}}. Without "profile" the build reads the outline from the sheet panel in the part's box; with it you draw the shape yourself. 8 to 28 triangles (up to 60 with a bevel). Examples: a harpy wing on arm.L {{"plate", dims [0.7, 0.5, 0.04], opts {{"axis": "front", "profile": [[0, 0.5], [0.3, 1], [1, 0.8], [0.7, 0.3], [0.9, 0], [0.2, 0.15]], "rot": [0, 0, -20]}}}}; a spider carapace on thorax with an overhang over the legs {{"plate", dims [0.5, 0.6, 0.12], opts {{"axis": "top", "bevel": 0.2}}}}; a tail rudder on tail {{"plate", dims [0.25, 0.3, 0.04], opts {{"axis": "left", "profile": [[0, 0], [1, 0], [0.6, 1]]}}}}.
- CUT: a box, prism or frustum with NO rot and no from/to may take opts {{"cut": "sheet"}}: the build then cuts that part to the sheet's own silhouette (the front, left and top outlines of the sheet in the part's height band, each reduced to at most 14 points, extruded and intersected, then fitted to the part's box). The part keeps its `at` and dims as the box it must fill. Use it for the masses whose outline the primitive cannot draw: torso, pelvis, hood or cowl, carapace, abdomen, a bulky chest plate. Never on a limb, hand, foot, weapon, head or thin plate: the strip of a limb would also pick up whatever is drawn beside it. At most 4 cut parts per unit; each costs up to 56 triangles. (The pre-spec already carries cut on the main torso, pelvis and hood: keep it.)
- "dome": only for a genuinely domed organic cap. Never a mechanical pauldron: use a box slab instead.
- "box": for flat plates, slabs, boots, shields and weapon heads. dims = (width_x, height_y, depth_z). Never for a limb.
- "cyl": a straight tube, only when a part is genuinely cylindrical. dims = (radius, depth). opts {{"axis": "up" | "fwd", "sides": 8 (default)}}.
- "wheel": a torus rim. dims = (major_radius, tube_radius).
- at = (x, y, z) in metres: +y is UP, +z is FORWARD (towards the viewer in the front view), x is right. The unit stands on y = 0, about {height} m tall.
- LIMBS/ANGLED PARTS: instead of `at`, use opts {{"from": [x,y,z], "to": [x,y,z]}}. The builder places the midpoint and aims the part's local height axis from `from` to `to`, so the limb angle is solved in code, never guessed. {limb_note}
- material: the name of one palette slot. Declare 3 to 8 slots in "palette", one per colour zone of the sheet - the sheet's colour zones are the contract. Each slot has a "color" taken from the sheet colours measured below and a "surface" saying what the material is, which sets its painted pattern and gloss: {surfaces}. SURFACE BY WHAT THE PART IS (a rule, not a suggestion): an animal, insect or arachnid is "chitin" (hard shell), "fur" or "skin" - never "metal", "polished" or "plastic"; "scales" only for a reptile or a fish; a living tree is "bark", worked timber (planks, beams, crates) is "wood"; an ooze or any gooey creature is "slime"; raw meat, tongues and organs are "flesh"; "stone" for rock; "metal"/"polished" only for armour and machines. Use "glow" for lamps, eyes and crystals that emit light. Only where the unit card asks for alpha (gauge glass, a flame tongue), give that one slot "surface": "glass" and "alpha": 0.3 to 0.7; every other slot stays opaque. The old slot names "iron", "darkiron", "brass" and "lamp" still work as metal.
Sheet colours (code-measured, share of the figure; near-black ink outlines removed): {colours}.
{face}- BOXES: at most a third of the parts may be kind "box"; prefer prism, frustum, dome or cyl for everything else (the preflight rule box_ceiling fails the spec otherwise).
- SYMMETRY: every part on a `.L` bone has a twin on the `.R` bone with the same kind and dims and the mirrored rot ([rx, -ry, -rz]); the preflight rule symmetry fails the spec otherwise. A weapon, shield or lantern carried on one side is the exception: give it opts {{"asym": true}}.
- PROPS: a weapon, tank, pack or lantern is its own part (several parts of one prop share the name), never merged into the body: opts {{"prop": "<name>", "anchor": "hand.R" | "hand.L" | "back" | "belt" | "head"}}. The anchor is where the body holds it; put the part on that anchor's bone (forearm.R/forearm.L, spine, pelvis, head) with its box touching the body there and standing off it: the preflight rule prop_clearance wants at most 20 % of the prop's box inside the torso, pelvis or head. A prop needs no .L/.R twin and keeps its size when the fit runs.
"""

FACE_KIND = "eyes"              # L18-0: preflight.face_kind of the unit being authored (set_face); "none" rejects every decal in validate()
FACE_EYES = """- PAINTED FEATURES: eyes are painted, never modelled. Give the part whose front face carries them opts {"decal": "sheet"}: the DEFAULT, the head cut out of the approved sheet itself and projected on that front face, so the eyes are the sheet's own two dots, never a slit (size the head part's front face like the sheet's head: the cut is stretched to it). The generic decals are for a sheet with no face to show (a valve wheel, a flat visor, a spider): {"decal": "eyes2"} (two eyes), {"decal": "eyes8"} (spider eyes), {"decal": "face"} (two eyes and a mouth) or {"decal": "mask"} (a dark mask with two glowing eyes), plus "decal_color": "#RRGGBB" when they glow. The decal is projected onto that part's front face. A decal goes ONLY on a part bound to the head (head, jaw, rider.head): eyes on the chest or any other bone are rejected.
- HOODS: a hood or cowl is a deep dark frustum or box on the head bone, opening to the front and set back. Paint the face or mask as a decal on the FRONT face of the head part inside the hood, and push that head part slightly forward of the hood's back wall so the hood does not hide it. Never model the eyes as geometry."""
FACE_NONE = """- PAINTED FEATURES: this unit's concept shows NO eyes or face (preflight.face_kind = none): no "decal" on any part, no eye parts, no mouth; the head's front face stays the plain material of the sheet (skin, metal, cloth). A part with "decal" is rejected.
- HOODS: a hood or cowl is a deep dark frustum or box on the head bone, opening to the front and set back, with the plain head part slightly forward of its back wall. Never model eyes as geometry and never paint them: the sheet has none."""


def set_face(unit, parts_path=None):
    """Remember the unit's face kind for the brief and validate(); returns it."""
    global FACE_KIND
    FACE_KIND = face_kind(identity_texts(unit, parts_path))
    return FACE_KIND


def face_text(kind):
    """The brief's PAINTED FEATURES / HOODS lines for a face kind: the decal rules for eyes and lenses, the plain-face rule for none."""
    return FACE_NONE if kind == "none" else FACE_EYES


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
SCALED_NOTE = (" - the skeleton is scaled to this sheet: put each part on its bone, from the bone's head to its tail, "
               "and do not re-guess lengths or heights")
SPIDER_MEASURED_TEXT = ("an eight-legged arthropod: abdomen and thorax mass on body, head and fangs on "
                        "head, legs leg1..leg8 (upper, lower) radiating around the body exactly as the rig "
                        "table lists them: the skeleton is scaled to this sheet, so put each leg part on its "
                        "bone (from the bone's head to its tail) and do not re-guess lengths or heights")
EXTRA_BONES = ("If the card names a prop that moves on its own - a mast, a second head, a "
               "counterweight, a launcher arm - you may add up to 3 extra bones at the top "
               "level: \"bones\": [[name, parent, head, tail]], parent an existing bone, head "
               "and tail in metres. Never add a bone for a part that only rides along.")


def rig_text(family):
    """(limb_note, rig_note) of the brief for this family."""
    if family == "biped":
        limb, rig = RIG_TEXT["biped"]
        return limb, f"{rig} {EXTRA_BONES}"
    note = SPIDER_MEASURED_TEXT if RIG_MEASURE and family in RF.SPIDERS else RIG_TEXT[family] + SCALED_NOTE * bool(RIG_MEASURE)
    return ("Use this for every leg segment, neck, tail and any angled part.",
            f"Parts are rigid-bound: each part follows the bone you name. This unit is "
            f"{note}. Rules that mention arms, hands, elbows, knees or feet apply "
            f"only to the limbs this body has. {EXTRA_BONES}")


def facet_text(m):
    """One line per band of the hard sheet's drawn facets (silhouette.edge_bands), or ''."""
    bands = m.get("edges")
    if not bands:
        return ""
    rows = [f"{b}: {v['facets']} facets{'' if v['direction'] == 'mixed' else ' ' + v['direction']}"
            for b, v in bands.items()]
    return ("\nFACETS drawn on the hard sheet's front view (edge lines a horizontal cut crosses, plus "
            "one; a facet is a flat face, so a band with more of them needs more sides): " + "; ".join(rows) + ".")
def spider_text(s):
    """The spider numbers of the sheet (silhouette.measure_spider) the rig table was scaled by."""
    h = RF.SPIDER_H
    return (f"\nSPIDER BODY (the rig table is already scaled to these, H = {h} m): body radius {s['body_r']} H "
            f"({s['body_r'] * h:.2f} m) seen from the top, body length {s['body_len']} H, belly "
            f"{s['body_under']} H above the ground, knee {s['knee_h']} H high and {s['knee_r']} H from "
            f"the axis, feet {s['foot_r']} H from the axis. Size the shell and abdomen to that radius and "
            "length, and the legs to those bones: a body smaller or legs longer than the table is the "
            "usual failure." + leg_text(s))


def line_text(m):
    """Every 4th point of the sheet's snout-to-tail centre line (silhouette.body_line): x behind the snout, y up, radius."""
    pts = " ".join(f"({x:.2f},{y:.2f},r{r:.2f})" for x, y, r in m["line"][::4])
    return f"centre line from the snout to the tail tip (x behind the snout, y up, radius; fractions of H): {pts}"


def wing_text(w):
    """The sheet's wing numbers (silhouette.wing_measures) as one sentence."""
    return (f" WINGS: tip {w['tip'][0]} H out and {w['tip'][1]} H high, root {w['root_x']} H out at {w['root_y']} H high, "
            f"side view chord {w['chord'][0]}-{w['chord'][1]} H behind the snout.")


def rig_text_of(m):
    """What the scaled quadruped, wyrm or drake rig stands on (silhouette.measure_rig), for the brief."""
    legs = m.get("legs")
    quad = (f" Trunk from {m['trunk'][0]} to {m['trunk'][1]} H behind the snout, belly {m['belly']} H above the ground, legs "
            f"at {legs['x'][0]} and {legs['x'][1]} H, feet {legs['spread']} H from the axis, leg radius {legs['r']} H."
            if legs else "")
    return (f"\nBODY (the rig table is already scaled to these, H = {RF.top(RIG)} m): length {m['len']} H; "
            + line_text(m) + "." + quad + (wing_text(m["wing"]) if "wing" in m else "")
            + " Put each part on its bone, size it to the line's radius there: a body thinner than the line is the usual failure.")


def leg_text(s):
    """The sheet's leg thickness (leg_w median radius, leg_taper tip / base), empty for an old measure."""
    if "leg_w" not in s:
        return ""
    base = 2 * s["leg_w"] / (1 + s["leg_taper"])
    return (f" LEG RADIUS: {base:.3f} H at the body, {base * s['leg_taper']:.3f} H at the tip "
            f"({base * RF.SPIDER_H:.3f} m, {base * s['leg_taper'] * RF.SPIDER_H:.3f} m): legs thinner than "
            "this are the usual failure.")


def joint_text(m):
    """The sheet's readable joints (silhouette.joint_measures), as heights above the feet; empty when none."""
    found = [f"{name} at {m[key]} H" for name, key in (("knee", "knee_h"), ("elbow", "elbow_h")) if key in m]
    return f"\nJOINTS (height above the feet): {', '.join(found)}; thigh meets shin and arm meets forearm there." if found else ""


def measured_text(family, m):
    """Code-derived proportions of the sheet, as the brief states them."""
    profile = ", ".join(f"{v:.2f}" for v in m["front_width_profile"])
    if family != "biped":
        side = ", ".join(f"{v:.2f}" for v in m["left_width_profile"])
        return ("MEASURED FROM THIS SHEET (code-derived, fractions of total height H - obey "
                "these, do not re-guess them):\nFront silhouette width profile, top to bottom, "
                f"in 5% steps: {profile}.\nSide silhouette width profile, top to bottom, in 5% "
                f"steps: {side}." + (spider_text(m["spider"]) if "spider" in m else "") + (rig_text_of(m["rig"]) if "rig" in m else ""))
    return ("MEASURED FROM THIS SHEET (code-derived, fractions of total height H - obey these, "
            "do not\nre-guess them): "
            f"shoulder span {m['shoulder_span']} H, fist-to-fist span {m['fist_span']} H,\n"
            f"foot-to-foot stance {m['stance']} H, chest body depth {m['body_depth']} H, "
            f"foot length {m['foot_length']} H, boot height {m['boot_height']} H, head width "
            f"{m['head_width']} H, neck width {m['neck_width']} H,\n"
            f"arms hang {m['arm_angle']} degrees out from vertical (A-pose when positive), "
            f"shoulder tip to fist {m['arm_length']} H.\n"
            f"Front silhouette width profile, top to bottom, in 5% steps: {profile}." + joint_text(m) + facet_text(m))


OUTLINE_NOTE = {"front": "x right of the centre line", "left": "z forward (the way the feet point)",
                "back": "x right of the centre line, as seen from the front of the unit"}


def outline_text(m):
    """The sheet's simplified silhouette per view as vertices (a, y), in H: the polygon the
    parts together must fill (Sano 2026: contour -> Douglas-Peucker -> axis snap)."""
    lines = [f"{view.capitalize()} outline, {OUTLINE_NOTE[view]}, y up from the feet, clockwise from the top: "
             + " ".join(f"({a:.2f},{y:.2f})" for a, y in poly) for view, poly in m.get("outline", {}).items()]
    if not lines:
        return ""
    return ("\nSILHOUETTE OUTLINES of this sheet (vertices of a polygon, fractions of H, simplified at "
            "1.2% of H). The union of your parts, seen from that side, must fill each polygon - arms "
            "and props included, so the A-pose and the lantern are in the vertices:\n" + "\n".join(lines))


def split_text(family, m, lo, hi):
    """Triangle budget per body group (EdgeRunner 2024: faces bucketed by region); the preflight
    rule budget_split fails a group outside its band. Biped only (the area bands are a biped's)."""
    if family != "biped" or "area_head" not in m:
        return ""
    total = (lo + hi) // 2
    rows = [f"{g}: {round(a * total)}-{round(b * total)} tris ({a:.0%}-{b:.0%})"
            for g, (a, b) in zip(GROUPS, split_bands(m))]
    return (f"\nTRIANGLES PER GROUP of a ~{total} tri unit (head = head/jaw bones, body = spine, pelvis, "
            "arms and what they hold, legs = thigh/shin/foot; a head wheel is not counted here): "
            + "; ".join(rows) + ".")


def props_text(props):
    """The unit's props in the order they are drawn on the props sheet (left to right)."""
    if not props:
        return ""
    lines = [f"{n}. {p['name']} - {p['where']}; on bone {' or '.join(p['bones'])}; "
             f"longest side {p['extent'][0]}-{p['extent'][1]} H"
             for n, p in enumerate(props, start=1)]
    return ("\nPROPS OF THIS UNIT, left to right on the props sheet. Build ONE part (or group of "
            "parts) per prop, on the bone named, sized as listed - the preflight rule "
            "props_present fails a prop with no part of its own:\n" + "\n".join(lines))


def identity_text(items):
    """The identity checklist (preflight.identity_items) as the brief's must-exist list: the preflight rule
    identity_present and the ID-render check identity_reads fail the run's status on any item missing."""
    lines = []
    for it in items:
        how = {"eyes": "a face decal on the head (decal + decal_color, two points, not a slit)" if FACE_KIND != "none" else "as drawn",
               "zone": f"a material of exactly this colour on a part (or a decal_color), visible in {'/'.join(it.get('views', ()))}",
               "prop": "its own part on the bone named above", "text": "as drawn"}[it["kind"]]
        lines.append(f"{len(lines) + 1}. {it['name']} - {how}")
    return ("\nIDENTITY OF THIS UNIT - these must exist as parts or decals, none dropped between runs, the "
            "small coloured ones are what makes the unit read:\n" + "\n".join(lines)) if lines else ""


def set_rig(family, measure=None):
    """Pick the rig family; a spider, quadruped, wyrm or drake with the sheet's measures (silhouette.measure_rig)
    gets its skeleton scaled by them (L14, 22.L4-4b), every other call keeps the fixed table."""
    global RIG, BONES, RIG_MEASURE
    RIG_MEASURE = measure if family in RF.SCALERS else None
    RF.scale_rig(family, RIG_MEASURE)
    RIG, BONES = family, set(RF.bones(family))
    lathe_limb.set_rig(family)


def rig_table():
    lines = []
    for name, _, head, tail in RF.FAMILIES[RIG]:
        head, tail = (tuple(round(v, 2) for v in head), tuple(round(v, 2) for v in tail))
        mid = tuple((head[i] + tail[i]) / 2 for i in range(3))
        length = sum((tail[i] - head[i]) ** 2 for i in range(3)) ** 0.5
        lines.append(f"  {name:10} head {head} tail {tail} midpoint {tuple(round(v, 2) for v in mid)} length {length:.2f}")
    return "\n".join(lines)


EDIT_NOTE = """

EDIT MODE - the mass is already built. A deterministic stage read the sheet's silhouettes and the rig and wrote the spec below: one mass per bone, its palette the sheet's colour zones (z1, z2...). Do not re-measure proportions: they come from the sheet. Return the whole spec as JSON: keep every part unless the sheet says otherwise; add props, decals and materials (rename the slots to what the part is and choose their surface); at most {changes} changes (a change is a part added, removed or edited). The part-count rule above does not apply to this spec; the triangle budget does.

{pre}"""
EDIT_CHANGES = 8


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
{freeze}
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
{freeze}
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


PROP_NOTE = "is a close crop of the prop '{name}' from the props sheet: {where}."


def with_refs(brief, refs, hard_first=False, props=()):
    """Append one line per extra reference image, numbered the way the brief already
    numbers images (image 1 is the construction sheet: the hard one when it exists).
    The n-th "prop" reference is the n-th entry of `props` (preflight.load_props)."""
    lines = [HARD_FIRST] if hard_first else []
    crops = iter(props)
    notes = [PROP_NOTE.format(**next(crops)) if kind == "prop" else REF_NOTES[kind]
             for kind, _ in refs]
    lines += [f"Image {i} {note}" for i, note in enumerate(notes, start=2)]
    if not lines:
        return brief
    return brief + "\nREFERENCE IMAGES\n" + "\n".join(lines) + "\n"


# Few-shot (PIPELINE 21.F5): one approved spec -> render pair per rig family. The images are
# crops of the run's compare.png (concept | clay front) kept in fewshot/ (runs may move on).
FEWSHOT_DIR = ROOT / "artifacts/model-sheets/fewshot"
FEWSHOT = {   # rig family -> (run with the spec, crop, what the run was)
    "biped": ("n01X/hard-v1", "biped.jpg", "an approved biped (stage 1 PASS)"),
    "spider": ("n00U/v6-r3", "spider.jpg", "the best spider so far (front/left/back pass, top/bottom "
                                           "still short: copy its scale and part count, not its flaws)"),
}
FEWSHOT_MARK = "\nWORKED EXAMPLE\n"
FEWSHOT_TEXT = ("Image {n} (left: the concept, right: the clay front render) is {what}, built from "
                "the spec below. This is what a PASS looks like in this DSL: note the scale of dims "
                "against H ({h}) and how few parts it takes. Its parts, in the DSL's slots (opts cut down to from/to):\n{parts}\n")


def fewshot_summary(spec):
    """The spec as the example shows it: one line per part in the DSL's own 6 slots, with only
    the opts that place it (from/to of a limb part) kept; sides, taper and the like dropped."""
    def r(v):
        return [round(x, 2) for x in v]
    def short(opts):
        return {k: r(opts[k]) for k in ("from", "to") if isinstance(opts, dict) and k in opts}
    return "\n".join(json.dumps([b, k, r(d), r(a), m, short(o)], separators=(",", ":"))
                      for b, k, d, a, m, o in spec["parts"])


def with_fewshot(brief, args, first):
    """(brief + the worked example, [its image]); `first` is the number its image gets. Nothing
    changes for --no-fewshot or a rig family without an example. args.fewshot_cost records the
    price (about w*h/750 tokens per image, 4 chars per text token)."""
    shot = FEWSHOT.get(args.rig)
    if args.no_fewshot or not shot:
        return brief, []
    run, crop, what = shot
    spec = json.loads((ROOT / "artifacts/model-sheets/runs/draft" / run / "spec.json").read_text())
    text = FEWSHOT_MARK + FEWSHOT_TEXT.format(n=first, what=what, h=round(RF.top(args.rig), 2),
                                              parts=fewshot_summary(spec))
    from PIL import Image
    w, h = Image.open(FEWSHOT_DIR / crop).size
    args.fewshot_cost = {"run": run, "images": 1, "text_tokens": len(text) // 4, "image_tokens": w * h // 750}
    return brief + text, [FEWSHOT_DIR / crop]


def fewshot_section(args):
    """review.md: what the worked example added to the author's prompt; empty without one."""
    c = getattr(args, "fewshot_cost", None)
    if not c:
        return ""
    return (f"## Few-shot\n\nexample: {c['run']}, {c['images']} image (~{c['image_tokens']} tokens) + "
            f"spec text (~{c['text_tokens']} tokens) per author call\n\n")


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
    refs += [("prop", p) for p in prop_crops(args, work)]
    return first, refs, [first] + [p for _, p in refs]


def prop_crops(args, work):
    """One crop per prop of the unit's props sheet, left to right, when the sheet's drawings
    match the unit's props.json one to one; else none (the whole sheet is still image N)."""
    if not (args.props and args.props.exists() and load_props(args.id)):
        return []
    from prop_measure import crop_props
    crops = crop_props(args.props, work, f".prop-{args.tag}-{args.id}")
    if len(crops) == len(load_props(args.id)):
        return crops
    print(f"props sheet has {len(crops)} drawings, props.json {len(load_props(args.id))}: no crops")
    for p in crops:
        p.unlink(missing_ok=True)
    return []


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


SESSION = "session:"   # --model session:<claude model> = the local Claude Code login, no API credit


# JSON Schemas of the author's replies. Both CLIs that take one validate it as draft-07/2020-12 in
# strict mode, which has no tuple form: a part is "6 positions of string, array or object" and
# validate() types them after. The ppq.ai chat API ignores response_format json_schema and the
# native Gemini response_schema/generationConfig (PIPELINE §20.S1), so there the schema is
# `json_object` + the brief's own text + one resend with the error.
PART_SCHEMA = {"type": "array", "minItems": 6, "maxItems": 6,
               "items": {"anyOf": [{"type": "string"}, {"type": "array"}, {"type": "object"}]}}
SPEC_SCHEMA = {
    "type": "object", "required": ["palette", "parts"],
    "properties": {
        "palette": {"type": "object", "additionalProperties": {
            "type": "object", "required": ["surface", "color"], "additionalProperties": False,
            "properties": {"surface": {"enum": sorted(SURFACES)},
                           "color": {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"},
                           "alpha": {"type": "number", "exclusiveMinimum": 0, "maximum": 1}}}},
        "parts": {"type": "array", "minItems": 1, "items": PART_SCHEMA},
        "bones": {"type": "array", "maxItems": 3, "items": {"type": "array"}}}}
PATCH_SCHEMA = {
    "type": "object", "required": ["set", "add", "drop", "why"],
    "properties": {"set": {"type": "object", "additionalProperties": PART_SCHEMA},
                   "add": {"type": "array", "items": PART_SCHEMA},
                   "drop": {"type": "array", "items": {"type": "integer"}},
                   "why": {"type": "string"}}}
BAD_REPLY = (ValueError, IndexError, KeyError, TypeError)   # json.JSONDecodeError is a ValueError
STATS = collections.Counter()    # asked / resent / frozen (resends caused by a frozen-part edit)
USAGE = collections.Counter()    # token counters of the `claude -p` replies (input_tokens, output_tokens, ...)
RESEND = ("\n\nYOUR PREVIOUS REPLY WAS REJECTED: {err}\nReply again with the whole corrected JSON "
          "object, nothing else.\nPREVIOUS REPLY:\n{reply}")


def ask(model, brief, images, schema=None, check=None):
    """The spec author's reply to one prompt plus images: a Claude Code session for
    `session:<model>`, else the ppq.ai chat API. `schema` is the JSON Schema of the reply;
    `check(reply)` raises BAD_REPLY on a reply the caller would refuse, and costs one resend
    that quotes the error."""
    def send(text):
        if model.startswith(SESSION):
            return ask_session(model[len(SESSION):], text, images, schema)
        return ask_api(model, text, images, schema)
    STATS["asked"] += 1
    reply = send(brief)
    if check is None:
        return reply
    try:
        check(reply)
    except BAD_REPLY as err:
        STATS["resent"] += 1
        STATS["frozen"] += "frozen" in str(err)
        print(f"resend: {err}")
        return send(brief + RESEND.format(err=err, reply=reply[:3000]))
    return reply


def session_command(model, brief, images, schema=None):
    """(argv, stdin prompt) of a one-shot `claude -p` that reads the images (Read only) and
    answers the brief. The prompt goes on stdin: --add-dir would swallow a trailing one.
    `schema` rides as --json-schema: the reply then comes back as structured_output."""
    paths = [str(pathlib.Path(p).resolve()) for p in images]
    listing = "\n".join(f"{i}. {p}" for i, p in enumerate(paths, 1))
    prompt = (f"{brief}\n\nThe images, in order (\"image 1\" is the first): read every one with "
              f"the Read tool before answering.\n{listing}\n\nAnswer with the reply text only.")
    dirs = sorted({str(pathlib.Path(p).parent) for p in paths})
    model, _, effort = (model or "opus").partition("@")      # "claude-fable-5-1@max": --effort max (L16-2)
    return (["claude", "-p", "--model", model, *(["--effort", effort] if effort else []), "--tools", "Read", "--allowedTools", "Read",
             "--no-session-persistence", "--setting-sources", "", "--strict-mcp-config",
             "--output-format", "json"] + (["--json-schema", json.dumps(schema)] if schema else [])
            + [a for d in dirs for a in ("--add-dir", d)], prompt)


def ask_session(model, brief, images, schema=None):
    import tempfile
    with tempfile.TemporaryDirectory() as cwd:     # no project CLAUDE.md, hooks or memory
        argv, prompt = session_command(model, brief, images, schema)
        out = subprocess.run(argv, input=prompt, cwd=cwd, capture_output=True, text=True,
                             timeout=1800)
    try:
        r = json.loads(out.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"claude -p failed: {(out.stderr or out.stdout)[-300:]}") from None
    if r.get("is_error"):
        raise RuntimeError(f"claude -p error: {str(r.get('result'))[-300:]}")
    for k, v in (r.get("usage") or {}).items():       # tokens spent, read by diagnose.py
        USAGE[k] += v if isinstance(v, int) else 0
    USAGE["cost_micro_usd"] += round(1e6 * (r.get("total_cost_usd") or 0))
    if r.get("structured_output") is not None:
        return json.dumps(r["structured_output"])
    return r.get("result") or ""


def post_chat(body):
    req = urllib.request.Request("https://api.ppq.ai/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {api_key()}",
                                          "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=900))


def ask_api(model, brief, images, schema=None):
    content = [{"type": "text", "text": brief}]
    content += [{"type": "image_url", "image_url": {"url": data_url(p)}} for p in images]
    body = {"model": model, "max_tokens": 9000, "temperature": 0.2,
            "messages": [{"role": "user", "content": content}]}
    if schema:
        body["response_format"] = {"type": "json_object"}   # the only one ppq.ai honours
    try:
        r = post_chat(body)
    except urllib.error.HTTPError as err:
        if err.code != 400 or "response_format" not in body:    # a model that refuses json_object
            raise
        r = post_chat({k: v for k, v in body.items() if k != "response_format"})
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
            if not isinstance(opts.get("rot", 0), (int, float, list)):  # [rx, ry, rz] stays
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
    lathe_limb.set_rig(RIG, extras)
    spec = validate(normalise(doc.get("parts")), palette, {b[0] for b in extras})
    ground_fix(spec["parts"])                        # stand on y = 0 by construction
    snap_parts(spec["parts"], RIG, {b[0] for b in extras})   # 1/256 grid, canonical order
    if palette:
        spec["palette"] = palette
    if extras:
        spec["bones"] = extras
    if RIG_MEASURE:
        spec["rig_measure"] = RIG_MEASURE
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


Editable = collections.namedtuple("Editable", "indices bands height")
# indices: the parts a patch may set or drop; bands: [(lo, hi)] fractions of the body height an
# added part must touch (None: an added part may go anywhere); height: the spec's height in metres


def check_editable(editable, sets, drops, added):
    """ValueError unless a patch stays inside the parts (and height bands) left editable."""
    frozen = sorted({int(i) for i in (*sets, *drops)} - editable.indices)
    if frozen:
        raise ValueError(f"patch edits frozen parts {frozen}: only {sorted(editable.indices)} may change")
    for part in added:
        lo, hi = bbox(part)[0][1], bbox(part)[1][1]
        if editable.bands and not any(hi >= a * editable.height and lo <= b * editable.height
                                      for a, b in editable.bands):
            raise ValueError(f"added part {part[0]} lies outside the failing height bands, which are frozen")


def apply_patch(parts, txt, limit=PASS_EDITS, palette=None, extra=(), editable=None):
    """A refinement reply edits a few parts by index; the rest of the spec is untouched,
    so one view cannot rewrite the mass split another view already fixed. With `editable`
    only those parts change: the others are frozen (PIPELINE §20.S1)."""
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
    if editable:
        check_editable(editable, sets, drops, parts[len(parts) - len(adds):])
    ground_fix(parts)
    snap_parts(parts, RIG, extra)
    return parts, patch.get("why", "")


MAX_ROT = 60.0      # degrees per axis of opts "rot"
# validate only refuses a part buried this deep (metres); a boot or shin a few cm under y=0 is
# what ground_fix lifts (2026-10-27: a -0.02 check threw away 9 of 9 author specs of n005)
GROUND_REJECT = -0.30


def bad_rot(opts):
    """True when opts["rot"] is not a number or 3 numbers within MAX_ROT."""
    rot = opts.get("rot", 0.0)
    vals = rot if isinstance(rot, list) else [rot]
    return (len(vals) not in (1, 3) or isinstance(rot, bool)
            or not all(isinstance(v, (int, float)) and abs(v) <= MAX_ROT for v in vals))


def bad_cut(part):
    """True when opts["cut"] is anything but "sheet" on an unrotated box/prism/frustum/lathe (a limb is never cut)."""
    opts = part[5]
    return "cut" in opts and (opts["cut"] != "sheet" or part[1] not in cut_hull.CUT_KINDS
                              or any(k in opts for k in ("rot", "from", "to")))


def validate(parts, palette=None, extra=()):
    if not isinstance(parts, list) or not parts:
        raise ValueError("no parts array")
    for i, p in enumerate(parts):
        if (len(p) != 6 or p[0] not in BONES | set(extra) or p[1] not in KINDS
                or p[4] not in MATS | set(palette or {})
                or not isinstance(p[3], list)):
            raise ValueError(f"part {i} outside the schema: {p}")
        if isinstance(p[5], dict) and p[5].get("decal", "eyes2") not in DECALS:
            raise ValueError(f"part {i} decal outside {sorted(DECALS)}")
        if isinstance(p[5], dict) and bad_cut(p):
            raise ValueError(f"part {i}: opts cut is \"sheet\" on a box, prism or frustum with no rot, from or to")
        if isinstance(p[5], dict) and p[1] in ("lathe", "limb", "chain", "plate") and lathe_limb.bad_opts(p[1], p[2], p[5], p[0]):
            raise ValueError(f"part {i}: {lathe_limb.bad_opts(p[1], p[2], p[5], p[0])}")
        if isinstance(p[5], dict) and bad_rot(p[5]):
            raise ValueError(f"part {i} rot outside +-{MAX_ROT:.0f} degrees: {p[5]['rot']}")
        if bbox(p)[0][1] < GROUND_REJECT:  # the box, not `at`: a span part's `at` is an offset
            raise ValueError(f"part {i} below the ground plane")
    check_decals(parts)
    return {"parts": parts}


def check_decals(parts):
    """ValueError for a decal off the head, or any decal at all when the unit's face is "none" (L18-0)."""
    bad = misplaced_decals(parts)
    if bad:
        raise ValueError(f"decal on a non-head bone {bad}: eyes and faces go on a head/jaw part")
    bad = [i for i, p in enumerate(parts) if isinstance(p[5], dict) and p[5].get("decal")] if FACE_KIND == "none" else []
    if bad:
        raise ValueError(f"decal on parts {bad}: this unit's concept shows no eyes or face (L18-0), the head stays plain")


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
    return subprocess.run(cmd + [str(a) for a in argv] + (overrides.build_args() if name == "build_unit.py" else []),
                          capture_output=True, text=True)


def trial(spec, sheet, kind, work, name):
    """Preflight, build (clay) and measure (shape gates) one candidate spec. A preflight
    failure is reported, not fatal: the model is still built so there is always something
    to look at. Returns (IoU per view or None when no GLB came out, preflight report or
    None, zone report per view: always empty, colour is stage 2)."""
    path = work / f"{name}.json"
    path.write_text(json.dumps(spec, indent=2))
    glb = work / f"{name}.glb"
    pre = tool("preflight.py", path, kind, sheet)     # landmark targets from this sheet
    problem = pre.stdout if pre.returncode else None
    build = tool("build_unit.py", path, glb, *clay_args(kind), *cut_hull.args(spec, sheet, kind, work),
                 blender=True)
    if not glb.exists():
        return None, (problem or "") + build.stderr[-400:], None
    tool("silhouette.py", sheet, glb, work / f"{name}-sil", "--layout", layout_of(kind), "--shape",
         "--rig", spec.get("rig") or "")
    report = json.loads((work / f"{name}-sil" / "silhouette.json").read_text())
    tool("render_unit.py", glb, work / f"{name}-views", tilt_arg(report), "lit", blender=True)
    red = [r["uncovered"] for r in report.values() if "uncovered" in r]
    return ({view: r["iou"] for view, r in report.items()}
            | {"red": sum(red) / len(red) if red else 0.0, "form": form_cost(mesh_lint.lint(glb))},
            problem, {view: r["zones"] for view, r in report.items() if "zones" in r})


def form_cost(m):
    """Lower is a more continuous surface: the sliver share plus the mean normal_diff over 90 degrees
    (mesh_lint.lint dict; PIPELINE 24.L6-6)."""
    return m["sliver_pct"] / 100 + m["normal_diff"]["mean"] / 90


def clay_args(kind):
    """build_unit.py arguments of a stage 1 build: the chamfer budget (the ceiling the gate
    checks), no fuse, and `clay` = one grey material, no texture, decal or glow."""
    hi = str(BUDGETS[kind][1])
    return [hi, "nofuse", hi, "clay", *([f"body={BODY}"] if BODY != DEFAULT_BODY else []),
            *([f"sdf_grid={SDF_GRID}"] if BODY == "sdf" and SDF_GRID else []),
            *([f"sdf_k_mode={SDF_K_MODE}"] if BODY == "sdf" and SDF_K_MODE != "base" else []),
            *([f"sdf_retopo={SDF_RETOPO}"] if BODY == "sdf" and SDF_RETOPO != "qem" else []),
            *([f"sdf_core={SDF_CORE}"] if BODY == "sdf" and SDF_CORE != DEFAULT_SDF_CORE else [])]


def inscribe_args(spec_path, spec, args):
    """build_unit.py arguments of --inscribe cut|on (inscribe.py, PIPELINE 31.L13-5): the visual hull's views and mirrors are the ones the
    gate picks on the uncut body, so the spec is built once without the cut (<out>/inscribe-uncut.glb)."""
    if args.inscribe == "off":
        return []
    uncut = args.out / "inscribe-uncut.glb"
    tool("build_unit.py", spec_path, uncut, *clay_args(args.kind), *cut_hull.args(spec, args.sheet, args.kind, args.out), blender=True)
    return inscribe.build_args(spec, args, args.out, uncut) if uncut.exists() else []


def tilts_of(report):
    """{view: tilt} the silhouette sweep chose, in views.parse_tilts form: top/bottom an int,
    rts an (elevation, azimuth) tuple. What stage 2 shoots its views from."""
    return {v: tuple(r["tilt"]) if isinstance(r["tilt"], (list, tuple)) else r["tilt"]
            for v, r in report.items() if r.get("tilt")}


def tilt_arg(report):
    """render_unit.py argument that shoots top/bottom and the RTS view from the camera
    silhouette.py matched; the RTS camera is an (elevation, azimuth) pair."""
    def value(tilt):
        return "/".join(map(str, tilt)) if isinstance(tilt, (list, tuple)) else str(tilt)
    return "tilt=" + ",".join(f"{v}:{value(r['tilt'])}" for v, r in report.items()
                              if r.get("tilt"))


def numbered(spec, editable=None):
    """The spec as a refinement prompt shows it: the fixed palette, then indexed parts,
    the frozen ones marked."""
    lines = [f"  {i}: {json.dumps(p)}" + ("   [FROZEN]" if editable and i not in editable.indices else "")
             for i, p in enumerate(spec["parts"])]
    if spec.get("bones"):
        lines.insert(0, f"  extra bones (fixed): {json.dumps(spec['bones'])}")
    if spec.get("palette"):
        lines.insert(0, f"  palette (fixed - use only these slot names): {json.dumps(spec['palette'])}")
    return "\n".join(lines)


BANDS = 8                              # height bands the silhouette is cut into
BAND_IOU = 0.65                        # a band under this IoU is where the view fails
BAND_VIEWS = {"front", "left", "back", "right"}   # rts/top/bottom/roof have no height axis
NAMES_PARTS = {"ground", "overlap", "decal_place", "symmetry", "outside_hull"}   # rules whose detail lists bones
FAIL_LINE = re.compile(r"^\s+(\w+)\s+FAIL\s+(.*)$", re.M)


def failing_bands(sil, view):
    """[(lo, hi)] bottom to top, as fractions of the body height from the ground: the bands of
    a side view where the model's mask meets the concept's under BAND_IOU (silhouette.py writes
    both, normalised to the same height, so a row is the same slice of body in each). [] when the
    view has no height axis or `sil` has no masks."""
    import numpy as np
    from silhouette import iou, read_mask
    paths = [sil / f"mask-{who}-{view}.png" for who in ("concept", "model")]
    if view not in BAND_VIEWS or not all(q.exists() for q in paths):
        return []
    concept, model = (read_mask(q) for q in paths)
    rows = np.where((concept | model).any(axis=1))[0]
    if not len(rows):
        return []
    edges = np.linspace(rows[0], rows[-1] + 1, BANDS + 1).astype(int)
    return [(1 - (i + 1) / BANDS, 1 - i / BANDS) for i in range(BANDS - 1, -1, -1)
            if iou(concept[edges[i]:edges[i + 1]], model[edges[i]:edges[i + 1]]) < BAND_IOU]


def band_editable(parts, bands):
    """The parts whose box reaches into a failing band, or None (nothing to freeze) when no band
    fails or every part touches one."""
    if not bands:
        return None
    boxes = [bbox(p) for p in parts]
    height = max(b[1][1] for b in boxes)
    hit = {i for i, b in enumerate(boxes)
           if any(b[1][1] >= lo * height and b[0][1] <= hi * height for lo, hi in bands)}
    return Editable(hit, bands, height) if 0 < len(hit) < len(parts) else None


def rule_editable(parts, problem):
    """The parts a preflight report points at: the bones named in the detail of its failing rules.
    None (everything editable) when one failing rule is global (budget, box_ceiling, ...) or names
    no part: the repair then needs the whole spec."""
    fails = FAIL_LINE.findall(problem or "")
    if not fails or any(name not in NAMES_PARTS for name, _ in fails):
        return None
    words = {w.rstrip(".") for _, detail in fails for w in re.findall(r"[A-Za-z_][\w.]*", detail)}
    hit = {i for i, q in enumerate(parts) if q[0] in words or q[0].rsplit(".", 1)[0] in words}
    return Editable(hit, None, 0.0) if 0 < len(hit) < len(parts) else None


def freeze_text(editable):
    """The prompt's FROZEN paragraph ('' when nothing is frozen)."""
    if not editable:
        return ""
    where = ("" if not editable.bands else " (the parts touching the height bands where this view "
             "fails: " + ", ".join(f"{lo:.0%}-{hi:.0%}" for lo, hi in editable.bands) + " of the height, "
             "from the ground)")
    return (f"\nEDITABLE parts: {sorted(editable.indices)}{where}. Every other part is marked [FROZEN]: "
            "it already matches, and a patch that sets or drops one" +
            (", or adds a part outside those bands," if editable.bands else "") + " is rejected.\n")


def repair(spec, args, brief, work, panels):
    """Pass 0: the preflight's failing rules go back to the model as a patch request.
    A repair is kept only when it still builds; the passes run either way."""
    scores, problem, zones = trial(spec, args.sheet, args.kind, work, "pass0")
    best = "pass0"  # the trial whose renders show the spec held
    for k in range(1, REPAIRS + 1):
        if problem is None:
            break
        print(f"repair {k}: preflight fails\n{problem.strip()}")
        edit = rule_editable(spec["parts"], problem)
        prompt = REPAIR.format(problem=problem, parts=numbered(spec, edit), freeze=freeze_text(edit),
                               limit=REPAIR_EDITS, brief=brief.split(FEWSHOT_MARK)[0])
        patch = lambda txt: apply_patch(spec["parts"], txt, REPAIR_EDITS, spec.get("palette"),
                                        extra_names(spec), edit)
        try:
            cand, _ = patch(ask(args.model, prompt, [panels["front"], panels["left"]], PATCH_SCHEMA, patch))
        except (ValueError, IndexError, KeyError, json.JSONDecodeError) as err:
            print(f"repair {k}: rejected reply: {err}")
            continue
        cur, cur_problem, cur_zones = trial({**spec, "parts": cand}, args.sheet, args.kind, work,
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
            and all(cur[g] >= prev[g] - REGRESSION for g in GATES if g in prev and g in cur)
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
        edit = band_editable(spec["parts"], failing_bands(work / f"{best}-sil", view))
        prompt = REFINE.format(view=view, scores=scores, axes=AXES[view],
                               parts=numbered(spec, edit), freeze=freeze_text(edit),
                               limit=PASS_EDITS, brief=brief.split(FEWSHOT_MARK)[0])
        shot = RENDER_NAME.get(view, view)
        images = [panels[view], work / f"{best}-views" / f"{best}-{shot}.png",
                  work / f"{best}-sil" / f"overlay-{view}.png"]
        try:
            patch = lambda txt: apply_patch(spec["parts"], txt, palette=spec.get("palette"),
                                            extra=extra_names(spec), editable=edit)
            cand, why = patch(ask(args.model, prompt, images, PATCH_SCHEMA, patch))
            cur, cur_problem, cur_zones = trial({**spec, "parts": cand}, args.sheet, args.kind,
                                                work, f"pass{n}")
        except (ValueError, IndexError, KeyError, json.JSONDecodeError) as err:
            cand, why, cur, cur_problem, cur_zones = None, f"rejected reply: {err}", None, None, None
        ok = accepted(scores, cur, view, zones=(zones, cur_zones), problems=(problem, cur_problem))
        if ok:
            spec, scores, problem, zones, best = ({**spec, "parts": cand}, cur, cur_problem,
                                                  cur_zones, f"pass{n}")
        log.append({"pass": n, "view": view, "why": why, "scores": cur, "accepted": ok,
                    "editable": sorted(edit.indices) if edit else None, "of": len(spec["parts"]),
                    "preflight": cur_problem is None, "failing": sorted(failing_rules(cur_problem)),
                    "zones": zone_scores(cur_zones)})
        print(f"pass {n} {view:5} {'ACCEPT' if ok else 'reject'} {cur}  {why}")
    (work / "passes.json").write_text(json.dumps(log, indent=2))
    (work / "asked.json").write_text(json.dumps(dict(STATS)))
    print(f"asked {dict(STATS)}")
    return spec


def fit_accepted(prev, cur, gates, problems, rig=None, cut=False):
    """The fitted spec's real clay against the original's (IoU per view, preflight report of each):
    no view that passed its gate may fall under it, the gated views must gain on the whole and no
    preflight rule that held may break; the family's critical views (VIEW_FLOOR) may not fall more than
    FIT_SLIP even when they were under their gate. The red (uncovered share) may not grow either, except
    for the cut variant: a hull trades red for the shape the IoU and the rules judge (PIPELINE 24.L6-2)."""
    if prev is None or cur is None:
        return False
    if any(cur.get(v, 1.0) < prev.get(v, 0.0) - FIT_SLIP for v in VIEW_FLOOR.get(rig, VIEW_FLOOR[None])):
        return False
    seen = [v for v in gates if v in prev and v in cur]
    # the sum of margins over the gates must grow (what best_of_n ranks by) and a view that
    # passed may slip at most FIT_SLIP under its gate (n00U v6-r1: top 0.653 -> 0.640 was
    # refused while front/back gained 0.08; the stage 1 verdict still gates every view)
    held = all(cur[v] >= gates[v] - FIT_SLIP for v in seen if prev[v] >= gates[v])
    margin = [sum(r[v] - gates[v] for v in seen) - FORM_W * r.get("form", 0.0) for r in (prev, cur)]
    red_ok = cut or cur.get("red", 0.0) <= prev.get("red", 0.0) + RED_SLIP      # the red may not grow (a cut is judged by IoU + form, 24.L6-2)
    return held and red_ok and margin[1] > margin[0] and rules_hold(*problems)


def fit_stage(spec, args):
    """--fit: fit_spec on the first spec, then build the original, the fitted and the fitted-with-cut-
    toggled clay for real and keep the best one that passes fit_accepted against the one before it
    (PIPELINE 21.F4: `cut: sheet` is decided here, not guessed by the author). The trials land in <run>/fit/."""
    import fit_spec
    from silhouette import gates_for, run_report
    fitted, report = fit_spec.fit(spec, args.sheet, args.kind, wide=not args.fit_fast, tilts=run_tilts(args),
                               hard=args.build if args.fit_edges else None,
                               stages=fit_spec.STAGES if args.fit_stages else None,
                               partfit=args.fit_parts or bool(args.parts) or args.depth, parts_path=args.parts,
                               depth=args.depth, grad=args.fit_grad, sheet_rep=run_report(args),
                               constraints=json.loads(args.constraints.read_text()).get("deltas") if args.constraints else None,
                               **({"seconds": 1e9} if getattr(args, "deterministic", False) else {}))
    print(f"fit: proxy IoU {report['before']} -> {report['after']} ({report['evals']} evals)")
    if report["changed"]:
        ground_fix(fitted["parts"])          # the fit may sink a shin 1-2 cm; --spec refuses that
    base = fitted if report["changed"] else spec
    toggled = None if args.fit_fast else fit_spec.toggle_cut(base)
    candidates = [(n, c) for n, c in (("after", fitted if report["changed"] else None), ("cut", toggled)) if c]
    if not candidates:
        return spec
    work = args.out / "fit"
    work.mkdir(parents=True, exist_ok=True)
    best, chosen = trial(spec, args.sheet, args.kind, work, "before"), ("before", spec)
    real = {"before": best[0]}
    for name, cand in candidates:
        cur = trial(cand, args.sheet, args.kind, work, name)
        real[name] = cur[0]
        if fit_accepted(best[0], cur[0], gates_for(args.rig), (best[1], cur[1]), args.rig, name == "cut"):
            best, chosen = cur, (name, cand)
    (work / "fit.json").write_text(json.dumps({**report, "real": real, "accepted": chosen[0] != "before",
                                               "chosen": chosen[0]}, indent=2))
    print(f"fit: real clay {real} -> {chosen[0]}")
    return chosen[1]


def massing_base(args):
    """The massing spec the author is guarded against: this run's pre-spec, or with --spec the massing/spec.json next to it."""
    if args.pre_spec:
        return args.pre_spec
    path = args.spec.parent / "massing" / "spec.json" if args.spec else None
    return {**json.loads(path.read_text()), "rig": args.rig} if path and path.exists() else None


def guard_rows(summary):
    """{view: {iou, spill}} of a stage 1 summary (the approved sheet's)."""
    return {v: {"iou": iou, "spill": summary.get("spill", {}).get(v, 0.0)} for v, iou in summary.get("approved", {}).items()}


def guard_measure(spec, args, layout, work, name):
    """Stage 1 of `spec` as the massing's is measured (build, deform, vertex fit; no numeric fit) on the run's pinned
    cameras, in <work>/<name>/: {view: {iou, spill}}, or None when the clay did not build or was not measured.
    Every candidate sweeps its OWN top/bottom/rts cameras: the run's pinned --tilts belong to the final model (the author's
    spec), and applied to the massing they rotated its top/bottom 180 degrees (hfoo v15: IoU .18, PIPELINE 31.L13-2)."""
    import copy
    a = copy.copy(args)
    a.out, a.summary, a.tilts = work / name, {}, ""
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "spec.json").write_text(json.dumps(spec, indent=2))
    stage_shape(a.out / "spec.json", a, layout)
    return guard_rows(a.summary) or None


def proxy_ious(spec, args):
    """Callable parts -> {view: IoU}: fit_spec's 2D proxy on the run's pinned cameras (no Blender)."""
    import fit_spec
    import views
    from silhouette import run_report
    RF.scale_rig(spec.get("rig", "biped"), spec.get("rig_measure"))
    lathe_limb.set_rig(spec.get("rig", "biped"), spec.get("bones"))
    concept = fit_spec.concept_masks(args.sheet, fit_spec.WIDE_VIEWS, True)
    proxy = fit_spec.Proxy(concept, tuple(concept), rig=spec.get("rig"), sheet_rep=run_report(args))
    proxy.cams = proxy.pick_cams(fit_spec.baked(spec["parts"], args.sheet), views.parse_tilts(args.tilts))
    return types.SimpleNamespace(ious=lambda parts: proxy.ious(fit_spec.baked(parts, args.sheet)))


def guard_steps(spec, mass, args, report):
    """[(action, spec or None)] the guard tries in order: revert the bones that explain the drop (mode revert), reject the
    author's body keeping its props, then the massing's body alone (a prop moves the silhouette too: hfoo's spear in left)."""
    steps = []
    if args.author_guard == "revert":
        gap = {v: report["gap"][v] for v in report["drops"]}
        guarded, report["reverted"] = author_guard.revert(spec, mass, proxy_ious(spec, args), report["drops"], gap)
        steps.append(("revert", guarded if report["reverted"] else None))
    return steps + [("reject", author_guard.reject(spec, mass)), ("reject-bare", author_guard.reject(spec, mass, props=False))]


def noise_kw(args):
    """{noise, unit} for the guards and the loop (L12-7): the sigma table of --noise, or None (they keep their fixed 0.01)."""
    return {"noise": NZ.load(getattr(args, "noise", None)), "unit": getattr(args, "id", None)}


def guard_stage(spec, args, layout):
    """--author-guard (PIPELINE 30.L12-3): the author's spec against the massing's, both measured as stage 1 (build, deform, vertex
    fit) on the run's pinned cameras, before the numeric fit. A view more than AUTHOR_DROP under the massing's: try the steps of
    guard_steps until none falls (the last one is taken unmeasured). Returns (spec, report or None)."""
    mass = massing_base(args)
    if args.author_guard == "off":
        return spec, None
    if not mass:
        print(f"no-op: --author-guard {args.author_guard}: no massing spec to guard against (--no-massing, or --spec without massing/spec.json)")
        return spec, None
    work = args.out / "guard"
    rows = {"massing": guard_measure(mass, args, layout, work, "massing"), "author": guard_measure(spec, args, layout, work, "author")}
    report = {"mode": args.author_guard, "action": "skipped", "rows": rows, "reverted": [], "drops": []}
    if not all(rows.values()):
        return spec, report
    iou = {k: {v: r["iou"] for v, r in row.items()} for k, row in rows.items()}
    report["drops"] = author_guard.drops(iou["massing"], iou["author"], **noise_kw(args))
    report["gap"] = {v: iou["massing"][v] - iou["author"][v] for v in report["drops"]}
    report["action"] = "intact"
    if not report["drops"]:
        return spec, report
    for action, guarded in guard_steps(spec, mass, args, report):
        if guarded is None:
            continue
        report["action"] = action
        if action == "reject-bare":
            return guarded, report
        rows[action] = guard_measure(guarded, args, layout, work, action)
        if rows[action] and not author_guard.drops(iou["massing"], {v: r["iou"] for v, r in rows[action].items()}, **noise_kw(args)):
            return guarded, report
    return spec, report


def guard_repin(args, report):
    """A guard that replaced the author's spec (revert/reject/reject-bare) hands the run the cameras that candidate swept itself: the
    pinned --tilts are the author's, and on the massing's body they turn top/bottom 180 degrees (hfoo: IoU .18, PIPELINE 31.L13-2).
    reject-bare is taken unmeasured, so it reads the massing's."""
    if not report or report["action"] in ("skipped", "intact"):
        return
    own = args.out / "guard" / (report["action"] if report["action"] != "reject-bare" else "massing") / "silhouette.json"
    tilts = json.loads(own.read_text()).get("tilt") if own.exists() else None
    if tilts:
        args.tilts = ",".join(f"{v}:{'/'.join(map(str, t)) if isinstance(t, (list, tuple)) else t}" for v, t in sorted(tilts.items()))
        report["repinned"] = args.tilts


def dsl_stage(spec, args, shape=None):
    """--dsl-repair on (PIPELINE 30.L12-6): dsl_rules.repair on the spec, no model call. Returns (spec, report or None, shape): the report has
    per rule PASS / FAIL / n/a before and after and the repairs [(rule, part, before, after)]; the shape is dropped when the spec changed."""
    if args.dsl_repair == "off":
        return spec, None, shape

    def verdicts(doc):
        got, na = dsl_rules.checks(doc["parts"], {**doc, "rig": doc.get("rig") or args.rig or "biped"}, args.sheet)
        return {**{r: "PASS" if ok else "FAIL" for r, ok, _ in got}, **{r: f"n/a: {why}" for r, why in na.items()}}
    doc = copy.deepcopy(spec)
    before = verdicts(doc)
    doc["parts"], log = dsl_rules.repair(doc["parts"], {**doc, "rig": doc.get("rig") or args.rig or "biped"}, args.sheet, opt_in=args.dsl_repair == "all")
    rows = part_rules.incoherent_parts(args.sheet) if args.sheet else []          # C6: the contradictory panel per part (33.L15-4)
    if rows:
        part_rules.save(args.sheet, rows)
    return doc, {"before": before, "after": verdicts(doc), "repairs": log, "coherence": part_rules.decided(rows, doc["parts"])}, (None if log else shape)


def depth_stage(spec, args, shape):
    """--depth-source tri (PIPELINE 30.L12-8): each spec part whose z centre lies outside the z range of the box3d of the semantic part it is
    (parts.json, triangulated front x left, depth_rule.tri_shifts) moves to the nearest point of the box's middle half, largest move first;
    a move stays when the fast 2D proxy loses no view by more than 2 sigma against the spec as it came (author_guard.drops) and breaks no
    preflight rule that held. Returns (spec, report or None, shape): the shape is dropped when a move was kept."""
    if args.depth_source == "none":
        return spec, None, shape
    import fit_spec
    import parts_fit
    import preflight
    from depth_map import shifted
    doc = parts_fit.load(args.sheet)
    if not doc or not any(p.get("box3d") for p in doc["parts"]):
        print("no-op: --depth-source tri: no refs parts.json, or none of its parts has a box3d (the triangulation found no z)")
        return spec, None, shape
    ious = proxy_ious(spec, args).ious
    parts = spec["parts"]
    centres = [fit_spec.spec_centre(p) for p in parts]
    height = max(max(b[1][1] for b in map(bbox, parts)), 1e-6)
    moves = {i: dz for i, dz in depth_rule.tri_shifts(centres, parts_fit.associate(parts, centres, doc, height), doc, height).items()
             if parts[i][1] != "chain"}                  # a chain's `at` is ignored: its bones place it
    targets, props = preflight.targets_from(args.sheet), load_props(args.id)
    held = fit_spec.broken_rules(parts, spec, args.kind, targets, props)
    base, cur, kept, refused = ious(parts), list(parts), {}, {}
    for i in sorted(moves, key=lambda k: -abs(moves[k])):
        cand = [*cur[:i], shifted(cur[i], moves[i]), *cur[i + 1:]]
        bad = author_guard.drops(base, ious(cand), **noise_kw(args)) or fit_spec.broken_rules(cand, spec, args.kind, targets, props) - held
        (refused if bad else kept)[i] = round(moves[i], 3)
        cur = cur if bad else cand
    report = {"moves": {i: round(dz, 3) for i, dz in moves.items()}, "kept": kept, "refused": refused,
              "parts": {i: f"{parts[i][0]} {parts[i][1]}" for i in moves}}
    if getattr(args, "out", None):
        (args.out / "depth-stage.json").write_text(json.dumps(report, indent=1))
    print(f"depth-source tri: {len(moves)} parts off their triangulated z, {len(kept)} moved, {len(refused)} refused")
    return ({**spec, "parts": cur}, report, None) if kept else (spec, report, shape)


def guard_fit(args, pre_fit, spec, shape, layout):
    """The fit may not push a view under the massing's stage 1 either (PIPELINE 30.L12-3): when it does, the spec stays as it was
    before the fit and is built again. Returns (spec, shape)."""
    r = getattr(args, "guard_report", None)
    if not r or r["action"] == "skipped" or spec is pre_fit:
        return spec, shape
    r["fit_drops"] = author_guard.drops({v: x["iou"] for v, x in r["rows"]["massing"].items()}, args.summary.get("approved", {}), **noise_kw(args))
    if not r["fit_drops"]:
        return spec, shape
    r["rows"]["fitted"] = guard_rows(args.summary)
    (args.out / "spec.json").write_text(json.dumps(pre_fit, indent=2))
    shape = stage_shape(args.out / "spec.json", args, layout)
    add_times(args, shape)
    return pre_fit, shape


def run_tilts(args):
    """The top/bottom/rts cameras this run's approved silhouette chose, when it has measured one."""
    path = args.out / "sil" / "approved" / "silhouette.json"
    return tilts_of(json.loads(path.read_text())) if path.exists() else None


def silhouette_vs(args, glb, layout, sheet, name):
    """(gate passed, per-view report) of the model against one sheet: shape only, the
    colour zones belong to stage 2."""
    sil_dir = args.out / "sil" / name
    pin = ["--tilts", args.tilts] if getattr(args, "tilts", "") and name == "approved" else []
    sil = tool("silhouette.py", sheet, glb, sil_dir, "--layout", layout, "--shape", "--rig", args.rig, "--gate", args.gate, "--orient", args.orient, *pin)
    print(f"vs {name}:\n{sil.stdout.strip()}")
    return sil.returncode == 0, json.loads((sil_dir / "silhouette.json").read_text())


def turn_views(args, glb):
    """{angle: {iou, azim, side, iou_nominal}} of the 3/4 panels of the unit's sheet-turn.jpg (PIPELINE 21.F6),
    report only; {} when the turntable is absent or failed its coherence test (sheet-turn.json "ok")."""
    sheet = args.sheet.with_name("sheet-turn.jpg")
    check = sheet.with_suffix(".json")
    if not (sheet.exists() and check.exists() and json.loads(check.read_text())["ok"]):
        return {}
    from silhouette import turn_report
    return {int(a): r for a, r in turn_report(sheet, glb, args.out / "sil" / "approved").items()}


def shape_review(args, glb, layout):
    """Stage 1 measurement. The verdict is the approved sheet's silhouette gate on every
    view (silhouette.GATES) - the design contract, what the human reviewer compares against
    too. The model is also measured against the hard sheet it was built from (did it follow
    its input?); both land in the run's silhouette.json with the hard-vs-approved drift and
    the cameras the sweep chose. Then the clay views, shot from those cameras, and the
    compare. Returns (gate passed, approved report)."""
    sil_ok, report, summary = True, {}, {"drift": args.drift}
    if not args.no_silhouette:
        from silhouette import gates_for, run_report
        sil_ok, report = silhouette_vs(args, glb, layout, args.sheet, "approved")
        summary["approved"] = {k: r["iou"] for k, r in report.items()}
        summary["tilt"] = tilts_of(report)
        summary["flipped"] = {v: r["flipped"] for v, r in report.items() if "flipped" in r}
        summary["top_orientation"] = {v: report[v]["head"] for v in ("top", "bottom") if v in report}
        summary["chamfer"] = {k: r["chamfer"] for k, r in report.items() if "chamfer" in r}
        for key in ("uncovered", "spill", "red", "contact", "parts", *BODY_PROP):     # coupling (PIPELINE 21.F7); body / prop (30.L12-5)
            summary[key] = {k: r[key] for k, r in report.items() if key in r}
        summary["gates"] = gates_for(args.rig)
        summary["sheet"] = run_report(args)     # r_sym and coherence; incoherent views are not gated
        if args.build != args.sheet:
            _, hard = silhouette_vs(args, glb, layout, args.build, "hard")
            summary["hard"] = {k: r["iou"] for k, r in hard.items()}
        summary["prop"] = prop_report(args)
        summary["turn"] = turn_views(args, glb)
        (args.out / "silhouette.json").write_text(json.dumps(summary, indent=2))
    args.summary = summary
    view_dir = args.out / "views" / args.id
    # lit: an unlit grey solid is one flat blob; the form has to read in the review image
    tool("render_unit.py", glb, view_dir, tilt_arg(report), "lit", blender=True)
    tool("render_wire.py", glb, view_dir, tilt_arg(report), blender=True)     # wire-<view>.png, compare column
    if summary.get("approved") and args.build.exists():
        from silhouette import edge_report
        summary["edges"] = edge_report(args.build, view_dir)     # hard-sheet edges vs the clay's wire
        (args.out / "silhouette.json").write_text(json.dumps(summary, indent=2))
    gameplay = view_dir / f"{glb.stem}-wc3.png"        # render_unit's name for the rts view
    if gameplay.exists():
        shutil.copy(gameplay, view_dir / f"{glb.stem}-rts.png")
    return sil_ok, report


ZONES_CLAY_BLOCKING = False   # report only until calibrated on the runs (PIPELINE 20.N3)


def zones_clay(spec_path, args, layout, tilts, heads=None):
    """{view: {mean, cover, lost}}: the clay shape rebuilt with the spec's palette (one flat
    colour per material, no texture) and compared with the sheet's colour zones, from the
    cameras stage 1 chose. Is the part of material X where the sheet has colour X? {} when the
    build or the measure fails: it is a report, never a stop."""
    from silhouette import HEAD
    work = args.out / "sil" / "ids"
    work.mkdir(parents=True, exist_ok=True)
    glb, hi = work / "ids.glb", str(BUDGETS[args.kind][1])
    spec = json.loads(pathlib.Path(spec_path).read_text())
    tool("build_unit.py", spec_path, glb, hi, "nofuse", hi,
         *cut_hull.args(spec, args.sheet, args.kind, work), blender=True)
    if not glb.exists():
        return {}
    done = tool("silhouette.py", args.sheet, glb, work, "--layout", layout, "--ids",
                "--tilts", ",".join(f"{v}:{t}" for v, t in tilts.items() if v != "rts"),
                "--rotate", ",".join(v for v, h in (heads or {}).items() if h == HEAD[v][1]) or "none")
    print(done.stdout.strip())
    try:
        zones = json.loads((work / "zones_clay.json").read_text())
    except (OSError, ValueError):
        return {}
    return {v: {k: z[k] for k in ("mean", "cover", "lost")} for v, z in zones.items()}


def identity_of(spec_path, args, layout):
    """{"total", "ok", "missing"} of the unit's identity checklist against the spec and the ID render
    (zones_clay wrote sil/ids/identity.json); {} when the sheet has no checklist."""
    items = identity_items(args.id, args.sheet, args.rig == "biped", layout)
    parts, doc = load_spec(spec_path)
    reads = args.out / "sil" / "ids" / "identity.json"
    st = identity_summary(items, parts, doc, load_props(args.id), json.loads(reads.read_text()) if reads.exists() else None)
    return st if st["total"] else {}
PROP_READS_BLOCKING = False   # report only until calibrated (PIPELINE 23.L5-3)


def prop_reads(spec_path, args):
    """{prop name: {view: reads}} (PIPELINE 23.L5-3): the spec rebuilt with every prop in a flat colour of its
    own (build_unit propid), rendered like the ID render; in each view where the sheet shows the prop
    (prop_measure.prop_views) its largest piece must cover PROP_SEEN of the figure. {} when the spec marks no
    prop or the build fails: a report, never a stop."""
    from preflight import PROP_IDS, is_prop, prop_names
    from prop_measure import PROP_SEEN, PROP_WHOLE, prop_seen, prop_views
    from silhouette import read_rgba
    spec = json.loads(pathlib.Path(spec_path).read_text())
    names = prop_names(spec["parts"]) if any(is_prop(p) for p in spec["parts"]) else []
    work = args.out / "sil" / "ids-prop"
    work.mkdir(parents=True, exist_ok=True)
    glb, hi = work / "propid.glb", str(BUDGETS[args.kind][1])
    if names:
        tool("build_unit.py", spec_path, glb, hi, "nofuse", hi, "propid",
             *cut_hull.args(spec, args.sheet, args.kind, work), blender=True)
    if not (names and glb.exists()):
        return {}
    tool("render_silhouette.py", glb, work / "ids", "ids", blender=True)
    props, out = load_props(args.id), {}
    for n, name in enumerate(names):
        for view in prop_views(args.id, name, props, REFS / args.id / "parts.json"):
            png = work / "ids" / f"propid-zone-{view}.png"
            if not png.exists():
                continue
            shot = read_rgba(png, 512)
            share, whole = prop_seen(shot[..., :3].astype(float), shot[..., 3] > 16, PROP_IDS[n % len(PROP_IDS)])
            out.setdefault(name, {})[view] = {"share": round(share, 4), "whole": round(whole, 2),
                                              "reads": share >= PROP_SEEN and whole >= PROP_WHOLE}
    return out


def preflight_ok(pre, sil_ok, tris_ok, summary):
    """The preflight passed, or failed only SOFT_RULES while the clay already covers the sheet
    (silhouette gates met, no critical view too red) and its GLB is within the tri gate: the model
    is the evidence, the estimate and the sheet measure are not (PIPELINE §26.L8-9)."""
    if not pre.returncode:
        return True
    failing = failing_rules(pre.stdout)
    soft = bool(failing) and failing <= set(SOFT_RULES) and sil_ok and tris_ok and not too_red(summary)
    if soft:
        print(f"preflight soft FAIL ({', '.join(sorted(failing))}): silhouette and tris hold, not blocking")
    return soft


def stage_shape(spec_path, args, layout):
    """Stage 1: preflight, clay build, rig/budget stats and the shape gates on the spec at
    `spec_path`. Returns a dict: ok, glb (clay GLB or None), tilts (tilts_of), checks
    ({gate: bool}), failed (names of the gates that failed), pre (preflight stdout) and the
    numbers tris, skins, anims, smear. A failed gate never stops the build: every output is
    still written so there is something to look at."""
    lo, hi = BUDGETS[args.kind]
    t0 = time.monotonic()
    pre = tool("preflight.py", spec_path, args.kind, args.sheet)
    t_pre = time.monotonic() - t0
    print(pre.stdout.strip())
    if pre.returncode:
        print(f"{args.id}\t{args.tag}\tpreflight FAIL - building anyway, verdict will be CHECK")
    glb = args.out / "clay.glb"
    spec = json.loads(pathlib.Path(spec_path).read_text())
    build = tool("build_unit.py", spec_path, glb, *clay_args(args.kind),
                 *cut_hull.args(spec, args.sheet, args.kind, args.out), *inscribe_args(spec_path, spec, args),
                 "cull=remove" if args.cull else "cull", blender=True)
    if not glb.exists():
        print(f"{args.id}\t{args.tag}\tBUILD FAILED\t{build.stderr[-200:]}")
        return {"ok": False, "glb": None, "tilts": {}, "checks": {"build": False},
                "failed": ["build"], "pre": pre.stdout, "tris": 0, "skins": 0, "anims": 0,
                "smear": 0.0, "t_pre": t_pre, "t_build": time.monotonic() - t0 - t_pre}
    deformed = deform_to_sheet.apply(glb, args)       # after the fit, before the texture: stage 2 reads this shape
    if deformed:
        print(f"deform: {deformed['steps']} steps, {deformed['refused']} refused, "
              f"slivers {deformed['slivers_before']} -> {deformed['slivers_after']}")
    aligned = align_features.apply(glb, args)         # after the deformation: sharp edges toward the hard sheet's
    if aligned:
        print(f"align: {aligned['steps']} steps, {aligned['refused']} refused, edge cost "
              f"{aligned['cost_before']} -> {aligned['cost_after']}")
    fitted = optimize_verts.apply(glb, args)          # opt-in: vertex optimisation of the deformed body (24.L6-7)
    if fitted:
        print(f"fit-verts: {fitted['steps']} steps in {fitted['seconds']} s, objective {fitted['objective'][0]} -> "
              f"{fitted['objective'][1]}, slivers {fitted['slivers_before']} -> {fitted['slivers_after']}")
    inscribe.apply(glb, args)                         # L13-5 (--inscribe): the cut's report; on: the vertices the deform and the fit pushed out of the masks go back in
    looked = look.apply(glb, args)                    # L12-9: planar snap / ink of the sheet's lines (opt-in) and the look metrics
    if looked:
        print(look.line(looked))
    depth = depth_rule.apply(glb, args)               # L12-8: z_err against the triangulated landmarks, relief_agreement of the z-pass
    if depth:
        print(depth_rule.line(depth))
    smear = re.search(r"normal smear on \d+ flat faces \(([\d.]+)%", build.stdout + build.stderr)
    smear_pct = float(smear.group(1)) if smear else 0.0
    tris, _, skins, anims = glb_stats(glb)
    sil_ok, report = shape_review(args, glb, layout)
    args.summary["form"] = round(form_cost(mesh_lint.lint(glb)), 4)
    if args.summary.get("approved"):
        args.summary["zones_clay"] = zones_clay(spec_path, args, layout, tilts_of(report),
                                                args.summary.get("top_orientation", {}))
        args.summary["identity"] = identity_of(spec_path, args, layout)
        args.summary["prop_reads"] = prop_reads(spec_path, args)
        (args.out / "silhouette.json").write_text(json.dumps(args.summary, indent=2))
    # the preflight counts estimated tris; the GLB may land a few over the round ceiling
    # (n005 v5-fit-r2: preflight PASS, GLB 704 vs 700). TRI_SLACK keeps that from failing stage 1.
    tris_ok = lo <= tris <= hi * (1 + TRI_SLACK)
    checks = {"preflight": preflight_ok(pre, sil_ok, tris_ok, args.summary), "tris": tris_ok, "skins": skins == 1,
              "anims": anims == 0 if args.rig in RF.STATIC else CLIPS[0] <= anims <= CLIPS[1],
              "smear": smear_pct <= 0.5, "silhouette": sil_ok}
    failed = [k for k, v in checks.items() if not v]
    return {"ok": not failed, "glb": glb, "tilts": tilts_of(report), "checks": checks,
            "failed": failed, "pre": pre.stdout, "tris": tris, "skins": skins, "anims": anims,
            "smear": smear_pct, "cull": cull_stats(glb), "t_pre": t_pre, "t_build": time.monotonic() - t0 - t_pre}


def cull_stats(glb):
    """cull.json that build_unit.py (cull.py) wrote beside `glb`, or None."""
    path = glb.parent / "cull.json"
    return json.loads(path.read_text()) if path.exists() else None


def cull_row(shape):
    """review.md row: tris seen by some of 12 views / all tris (PIPELINE 20.M8)."""
    c = shape.get("cull")
    if not c:
        return ""
    after = f", removed -> {c['tris_after']} tris" if c.get("removed") else ", kept (--cull removes)"
    return f"| visible tris | {c['visible_tris']}/{c['total_tris']} ({c['visible_tris'] / c['total_tris']:.0%}){after} |\n"


def margin_of(summary):
    """Sum over the views of (IoU vs approved - the view's gate): how far above the stage 1
    gates a build sits. 0.0 when the silhouette was not measured."""
    gates = summary.get("gates") or {}
    red = [u for v, u in (summary.get("uncovered") or {}).items() if v in gates]
    return (sum(iou - gates[v] for v, iou in (summary.get("approved") or {}).items() if v in gates)
            - RED_W * (sum(red) / len(red) if red else 0.0) - FORM_W * summary.get("form", 0.0))


def author_specs(args, brief, images):
    """The N specs of --variants N, asked in parallel (the author is the slow part): a list
    of (k, spec); a reply that does not parse is logged and dropped. Raises when none does."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(args.variants) as pool:
        replies = [pool.submit(ask, args.model, brief, images, SPEC_SCHEMA, parse_spec) for _ in range(args.variants)]
    specs = []
    for k, fut in enumerate(replies, 1):
        try:
            specs.append((k, {**parse_spec(fut.result()), "rig": args.rig}))
        except (ValueError, IndexError, KeyError, RuntimeError, json.JSONDecodeError) as err:
            print(f"variant {k}: dropped, {err}")
    if not specs:
        raise SystemExit("--variants: no reply parsed into a spec")
    return specs


def add_times(args, shape):
    """Book one stage_shape run: its preflight is generation, the rest is the build."""
    args.times["gen"] += shape["t_pre"]
    args.times["build"] += shape["t_build"]


def best_of_n(specs, args, layout):
    """Stage 1 on every (k, spec) in variants/<k>/, then the winner: the best (stage 1 ok,
    sum of margins over the gates). Nothing is deleted - the winner is copied into the run dir
    and every variant stays. Returns (spec, shape); args.summary is the winner's and
    args.variants_log lists every variant."""
    out, log, best = args.out, [], None
    try:
        for k, spec in specs:
            args.out = out / "variants" / str(k)
            args.out.mkdir(parents=True, exist_ok=True)
            (args.out / "spec.json").write_text(json.dumps(spec, indent=2))
            shape = stage_shape(args.out / "spec.json", args, layout)
            add_times(args, shape)
            row = {"k": k, "ok": shape["ok"], "margin": margin_of(args.summary),
                   "iou": args.summary.get("approved", {}), "failed": shape["failed"]}
            log.append(row)
            if best is None or (row["ok"], row["margin"]) > (best[0]["ok"], best[0]["margin"]):
                best = (row, spec, shape, args.summary)
    finally:
        args.out = out
    row, spec, shape, args.summary = best
    row["chosen"] = True
    args.variants_log = log
    shutil.copytree(out / "variants" / str(row["k"]), out, dirs_exist_ok=True)
    if shape["glb"]:
        shape["glb"] = out / shape["glb"].name
    return spec, shape


def variants_section(args):
    """review.md: one row per variant, its IoU per view and its margin sum; empty for N=1."""
    log = getattr(args, "variants_log", None)
    if not log:
        return ""
    rows = "".join(f"| {r['k']}{' (chosen)' if r.get('chosen') else ''} | "
                   f"{'ok' if r['ok'] else 'fail: ' + ', '.join(r['failed'])} | "
                   + " / ".join(f"{r['iou'][v]:.3f}" if v in r["iou"] else "-" for v in VIEWS)
                   + f" | {r['margin']:+.3f} |\n" for r in log)
    return (f"## Variants (best of {len(log)}, in variants/<k>/)\n\n"
            f"| k | gates | IoU {' / '.join(VIEWS)} | margin sum |\n|---|---|---|---|\n{rows}\n")


def timing_section(args):
    """review.md: wall seconds per phase and the number of passes (Begemann & Hutson 2026:
    generation, integration, readiness apart). compare_runs.py reads these lines."""
    t = getattr(args, "times", None)
    if not t:
        return ""
    return ("## Timing\n\n" + "".join(f"- t_{k}: {t.get(k, 0.0):.1f} s\n"
                                     for k in ("gen", "build", "passes", "colour"))
            + f"- passes: {t.get('n_passes', 0)}\n\n")


def load_colour_stage():
    """The stage 2 module, or None while tools/blender/colour_stage.py does not exist. Only
    its own absence is tolerated: an import error inside it must surface."""
    try:
        import colour_stage
    except ModuleNotFoundError as err:
        if err.name != "colour_stage":
            raise
        return None
    return colour_stage


def turntable(args, glb):
    frames = args.out / "orbit-frames"      # per run: parallel runs of one unit must not share it
    subprocess.run(["blender", "-b", "-P", str(ROOT / "tools/blender/turntable_color.py"),
                    "--", str(glb), str(frames), "24", "420"], capture_output=True, text=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(frames / "orbit-%03d.png"),
                    "-vf", "fps=12,scale=420:-1:flags=lanczos", "-loop", "0",
                    str(args.out / "turntable.gif")], check=False)
    subprocess.run(["rm", "-rf", str(frames)], check=False)


def hull_for(args, layout):
    """The base volume part of --hull (building_hull.hull_part, built to out/hull.glb so its
    triangles are counted), or None without the flag. Only a building sheet has the elevations."""
    if not args.hull:
        return None
    if layout != "building":
        raise SystemExit("--hull needs --kind building|large: only a building sheet has the elevations")
    from silhouette import concept_panels
    part = building_hull.hull_part(concept_panels(args.sheet, layout=layout), args.height or RF.top(args.rig))
    part[5]["hull"]["tris"] = building_hull.export(part, args.out, args.kind)
    return part
def spider_measure(args):
    """The sheet's numbers for set_rig (silhouette.measure_rig), None for a family without a scaler or with --fixed-rig."""
    if args.rig not in RF.SCALERS or args.fixed_rig:
        return None
    from silhouette import measure_rig
    return measure_rig(args.rig, args.sheet)


def make_brief(args, lo, hi):
    """The spec brief for this sheet: the unit brief, or the building brief for a
    static rig, both around the same part DSL and code-measured numbers."""
    from silhouette import measure, sheet_colours, sheet_report, sheet_text
    limb_note, rig_note = rig_text(args.rig)
    sheet_m = measure(args.sheet)
    if args.rig == "biped" and args.build.exists():
        from silhouette import edge_bands
        sheet_m["edges"] = edge_bands(args.build, sheet_m["shoulder_frac"])
        sheet_m.update({f"edge_{g}": sheet_m["edges"][b]["salience"] for g, b in zip(GROUPS, ("head", "torso", "legs"))})
    if RIG_MEASURE:
        sheet_m["spider" if args.rig in RF.SPIDERS else "rig"] = RIG_MEASURE
    dsl = DSL.format(height=args.height or round(RF.top(args.rig), 2), limb_note=limb_note, face=face_text(set_face(args.id)),
                     surfaces=", ".join(SURFACES),
                     colours=", ".join(f"{h} {round(100 * f)}%" for h, f in sheet_colours(args.build)))
    template = BUILDING_BRIEF if args.rig in RF.STATIC else BRIEF
    return template.format(race=args.race, name=args.name, uid=args.id, role=args.role,
                           dsl=dsl, budget=f"{lo} to {hi}", bones=rig_table(), rig_note=rig_note,
                           measured=measured_text(args.rig, sheet_m) + sheet_text(sheet_report(args.sheet, layout_of(args.kind))) + outline_text(sheet_m)
                           + split_text(args.rig, sheet_m, lo, hi) + props_text(load_props(args.id))
                           + identity_text(identity_items(args.id, args.sheet, args.rig == "biped", layout_of(args.kind)))
                           + (building_hull.brief_text(args.hull_part) if args.hull_part else ""))


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


REDO_TRIES = 2         # paid draws per --redo-rts (PIPELINE 25.L7-2)


def redo_rts(sheet):
    """Redraw sheet-rts.jpg tied to the sheet's three orthographic panels (front, left, back as the reference
    image, the game camera in the prompt). The old image goes to refs/<id>/old/ and the new one replaces it only when
    its coherence with the hull of front x left (silhouette.rts_vs_sheet) rises and it shows one figure."""
    from silhouette import ortho_strip, rts_path, rts_vs_sheet
    dest, old_dir = rts_path(sheet), sheet.parent / "old"
    old_dir.mkdir(exist_ok=True)
    before = rts_vs_sheet(sheet, dest)
    n = len(list(old_dir.glob(f"{dest.stem}-v*.jpg"))) + 1
    keep = old_dir / f"{dest.stem}-v{n}.jpg"
    shutil.copy2(dest, keep)
    strip = old_dir / f"{dest.stem}-in.jpg"
    ortho_strip(sheet, strip)
    best = before[0] if before else 0.0
    for attempt in range(1, REDO_TRIES + 1):
        stem = f"{dest.stem}-redo{n}-{attempt}"
        gen = subprocess.run([sys.executable, str(MSHEETS / "generate.py"), str(TEMPLATES / "00-template-rts-redo.txt"),
                              "--image", str(strip), "--out", str(old_dir), "--name", stem, "--resolution", "1K"],
                             capture_output=True, text=True)
        print(gen.stdout.strip() or f"rts redo not drawn: {gen.stderr.strip()[-200:]}")
        new = old_dir / f"{stem}.jpg"
        score = new.exists() and rts_figures(new) == 1 and rts_vs_sheet(sheet, new)
        print(f"{new.name}: coherence {score[0] if score else 'n/a'} (was {best:.3f})")
        if score and score[0] > best:
            shutil.copy2(new, dest)
            return True
    return False


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


VIEWS = ("front", "left", "back", "top", "bottom", "rts")
BODY_PROP = tuple(f"{part}_{m}" for part in ("body", "prop") for m in ("iou", "spill", "bare"))    # silhouette.body_prop_scores


def sheet_row(summary):
    """review.md row: front r_sym and how each panel agrees with the hull of front x left."""
    if not summary.get("sheet"):
        return ""
    from silhouette import sheet_line
    return f"| sheet (report; an incoherent view is not gated) | {sheet_line(summary['sheet'])} |\n"


def split_rows(summary, row, shape):
    """The body / prop rows, only for a sheet with props: the gate judges the body, the prop is a CHECK (30.L12-5)."""
    return "".join(row(f"{k.replace('_', ' ')} ({'gate' if k.startswith('body') else 'CHECK'})", summary[k], shape)
                   for k in BODY_PROP if summary.get(k))


def signal_rows(summary, row, shape):
    """The report-only rows of the stage 1 table: contour chamfer, edge chamfer, clay zones."""
    out = sheet_row(summary)
    if summary.get("chamfer"):
        out += row("contour chamfer (SD, /H)", summary["chamfer"], shape)
        out += f"| SD mean | {sum(summary['chamfer'].values()) / len(summary['chamfer']):.4f} |\n"
    for key in ("uncovered", "spill", "contact"):
        if summary.get(key):
            out += row(f"{key} (report, /{ {'uncovered': 'sheet area', 'spill': 'model area'}.get(key, 'sheet contour') })", summary[key], shape)
    out += split_rows(summary, row, shape)
    if summary.get("red"):
        from silhouette import red_text
        out += "".join(f"| worst red {v} | {red_text(r)} |\n" for v, r in summary["red"].items())
    if summary.get("edges"):
        out += row("edge chamfer hard->wire (/H)", {v: r["drawn"] for v, r in summary["edges"].items()}, shape)
    if summary.get("turn"):
        out += "| turn views 3/4 (report): IoU @ azimuth, side | " + ", ".join(
            f"{a} {r['iou']:.3f} @ {r['azim']} {r['side']}" for a, r in summary["turn"].items()) + " |\n"
    for name, views in (summary.get("prop_reads") or {}).items():
        out += (f"| prop_reads {name} (report; share of figure, reads) | "
                + ", ".join(f"{v} {r['share']:.3f} {'ok' if r['reads'] else 'HIDDEN'}" for v, r in views.items()) + " |\n")
    for key in ("mean", "cover"):
        if summary.get("zones_clay"):
            out += row(f"zones_clay {key} (report)", {v: z[key] for v, z in summary["zones_clay"].items()}, shape)
    return out


def iou_rows(summary):
    """review.md rows: silhouette IoU per view against each sheet, the gates, the cameras
    the sweep chose for top/bottom/rts, and the drift (front/left/back only)."""
    def row(label, d, views):
        return f"| {label} | " + " / ".join(f"{d[v]:.3f}" if v in d else "-" for v in views) + " |\n"
    shape = ("front", "left", "back", "top", "bottom", "rts")
    out = ""
    if summary.get("approved"):
        out += f"| views | {' / '.join(shape)} |\n"
        out += row("IoU vs approved", summary["approved"], shape)
        if summary.get("gates"):
            out += row("gates", summary["gates"], shape)
        if summary.get("top_orientation"):
            out += "| sheet top / bottom drawn | " + " / ".join(summary["top_orientation"].values()) + " |\n"
        if summary.get("flipped"):
            out += "| side view mirrored (front / left / back) | " + " / ".join(
                str(summary["flipped"].get(v, "-")) for v in ("front", "left", "back")) + " |\n"
        if summary.get("tilt"):
            out += "| camera (tilt, rts elev/azim) | " + ", ".join(
                f"{v} {'/'.join(map(str, t)) if isinstance(t, (list, tuple)) else t}"
                for v, t in summary["tilt"].items()) + " |\n"
    out += signal_rows(summary, row, shape)
    if summary.get("hard"):
        out += row("IoU vs hard", summary["hard"], shape)
    if summary.get("drift"):
        out += row("drift hard vs approved", summary["drift"], ("front", "left", "back"))
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


def massing_spec(args):
    """Stage 0: the pre-spec dict (through parse_spec, so it is on the grid and checked like an
    author's), or None with --no-massing, --spec, a family without a massing, or a sheet it cannot read."""
    if args.no_massing or args.spec or args.rig not in massing.FAMILIES:
        return None
    try:
        spec = parse_spec(json.dumps(massing.build(args.sheet, args.rig, args.race, args.build)))
        return {**spec, "rig": args.rig}    # parse_spec drops it; build_unit reads the rig from the spec (biped otherwise)
    except (ValueError, IndexError, SystemExit) as err:
        print(f"massing: skipped, {err}")
        return None


def massing_stage(args, layout):
    """The pre-spec built and measured alone in <out>/massing/ (the same stage 1 as any spec), so
    review.md says what the author started from. The numbers land in args.massing_report."""
    out = args.out / "massing"
    out.mkdir(parents=True, exist_ok=True)
    (out / "spec.json").write_text(json.dumps(args.pre_spec, indent=2))
    saved, args.out = args.out, out
    try:
        shape = stage_shape(out / "spec.json", args, layout)
        add_times(args, shape)
    finally:
        args.out = saved
    summary = getattr(args, "summary", {})     # a failed massing build never reaches shape_review
    args.massing_report = {"iou": summary.get("approved", {}), "gates": summary.get("gates", {}),
                           "ok": shape["ok"], "failed": shape["failed"], "tris": shape["tris"],
                           "rules": rules_of(shape["pre"])}


def rules_of(pre):
    """'passed/total' of a preflight stdout's '<n>/<m> rules pass' line, '-' when it has none."""
    m = re.search(r"(\d+)/(\d+) rules", pre)
    return f"{m.group(1)}/{m.group(2)}" if m else "-"


def author_brief(args, brief, layout):
    """The brief the author gets: with a pre-spec, stage 0 runs here (built and measured alone) and the
    brief ends with the EDIT note and the pre-spec; without one, the brief as it is."""
    if not args.pre_spec:
        return brief
    massing_stage(args, layout)
    return brief + EDIT_NOTE.format(changes=EDIT_CHANGES, pre=json.dumps(args.pre_spec))


def note_edit(args, spec):
    """Record in the massing report what the author did to the pre-spec (nothing without a pre-spec)."""
    if args.pre_spec:
        args.massing_report["edit"] = edit_changes(args.pre_spec, spec)


def edit_changes(pre, spec):
    """(parts of `spec` that are new or edited, parts of `pre` that are gone): what the author did to the pre-spec."""
    return (sum(p not in pre["parts"] for p in spec["parts"]), sum(p not in spec["parts"] for p in pre["parts"]))


def stage_one(args, brief, images, tmp, layout):
    """Everything up to the approved stage 1: ask the author (N times with --variants, the best
    one wins), repair/passes, stage_shape. Returns (spec, shape); args.times holds the clock."""
    args.times = {"gen": 0.0, "build": 0.0, "passes": 0.0, "colour": 0.0, "n_passes": 0}
    brief_author = author_brief(args, brief, layout)
    t0 = time.monotonic()
    # --spec resumes from an approved spec: only the refinement passes call the model
    if args.spec:
        specs = [(1, {**parse_spec(args.spec.read_text()), "rig": args.rig})]
    elif args.variants > 1:
        specs = author_specs(args, brief_author, images)
    else:
        specs = [(1, {**parse_spec(ask(args.model, brief_author, images, SPEC_SCHEMA, parse_spec)),
                      "rig": args.rig})]
    specs = [(k, massing.lean_props(spec, args.sheet)) for k, spec in specs]      # a pole the author stood upright leans as the sheet draws it (25.L7-4)
    note_edit(args, specs[0][1])
    if args.hull_part:        # the base volume is code's, whatever the author wrote
        specs = [(k, building_hull.with_hull(spec, args.hull_part)) for k, spec in specs]
    args.times["gen"] = time.monotonic() - t0
    for p in tmp:
        p.unlink(missing_ok=True)
    shape = None
    if args.variants > 1 and not args.spec:       # best of N: stage 1 on each, the winner goes on
        spec, shape = best_of_n(specs, args, layout)
    else:
        spec = specs[0][1]
    spec, args.guard_report = guard_stage(spec, args, layout)    # the author's body against the massing's, before anything refits it
    guard_repin(args, args.guard_report)
    if args.guard_report and args.guard_report["action"] in ("revert", "reject"):
        shape = None
    spec, args.dsl_report, shape = dsl_stage(spec, args, shape)        # the DSL rules that were prose, repaired in code (30.L12-6)
    spec, args.depth_report, shape = depth_stage(spec, args, shape)    # z of the parts from the triangulated boxes (30.L12-8)
    # the repair pass (preflight failures -> patch) runs even without --passes: it is
    # what pulls a too-wide body back to its sheet (hfoo shoulders 0.66 -> 0.51, sheet 0.46)
    if args.passes or not args.no_repair:
        views = args.passes.split(",") if args.passes else []
        t0 = time.monotonic()
        spec = run_passes(spec, args, brief, views)
        args.times["passes"], args.times["n_passes"] = time.monotonic() - t0, len(views)
        shape = None         # the spec changed: its stage 1 is measured again below
    # --fit comes last: a numeric fit of dims/at that an LLM repair after it would undo
    # (n005 v5-fit-r1: fit took front 0.72 -> 0.82, the repair pass then put it back at 0.71)
    pre_fit = spec
    if args.fit:
        spec = fit_stage(spec, args)
        shape = None
    spec_path = args.out / "spec.json"
    spec_path.write_text(json.dumps(spec, indent=2))

    # stage 1: forma. A spec that fails here stops: no texture, no turntable, no stage 2.
    if shape is None:
        shape = stage_shape(spec_path, args, layout)
        add_times(args, shape)
    return guard_fit(args, pre_fit, spec, shape, layout)


def build_parser():
    """The argument parser of the pipeline (one definition: main() and tests/tools/blender/test_flag_liveness.py)."""
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
    ap.add_argument("--model", default="google/gemini-4-argon",
                    help="spec author: a ppq.ai model id, or session:<opus|sonnet|...> for the "
                         "local Claude Code login (no API credit)")
    ap.add_argument("--tag", default="argon", help="spec-author label, recorded in review.md")
    ap.add_argument("--rig", default=None, choices=sorted(RF.FAMILIES),
                    help="skeleton family (rig_families.py); default biped, or building "
                         "for --kind building/large")
    ap.add_argument("--fixed-rig", action="store_true",
                    help="spider families: keep the fixed skeleton instead of scaling it by the sheet's measures")
    ap.add_argument("--height", type=float, default=None,
                    help="unit height in metres (default: the rig's own height)")
    ap.add_argument("--kind", default="mass", choices=BUDGETS.keys())
    ap.add_argument("--texture", "--style", dest="texture", choices=("cel", "painted", "sheet"),
                    default="cel",
                    help="stage 2 texture: cel = flat tone per face like the hard sheet (default); "
                         "painted = the older painted gloss and pattern; sheet = the concept's "
                         "panels projected on the model")
    ap.add_argument("--ramp", action="store_true",
                    help="stage 2 cel: each palette slot ramps from dark to light as far as its sheet zone does")
    ap.add_argument("--fit-luma", action="store_true",
                    help="stage 2 cel: per-slot tone multipliers fitted to the sheet's luma by deferred shading "
                         "(fit_luma.py, PIPELINE 26.L8-8; default off, colour_stage.FIT_LUMA)")
    ap.add_argument("--atlas", choices=("own", "shared", "compact", "legacy"), default="own",
                    help="stage 2 cel: own = one atlas per unit (build_unit.COMPACT_ATLAS picks its layout); compact / legacy = "
                         "that layout forced (compact: 2 px ramp slots, 16 px decals, shelf-packed POT image; legacy: "
                         "256 px cells, PIPELINE 27.T1); shared = the race's 128 px atlas, "
                         "tone columns + decal cells, ink as a row only (shared_atlas.py, PIPELINE 27.T3)")
    ap.add_argument("--outline", choices=("hull", "ink", "off", "both"), default="hull",
                    help="stage 2 (default hull; off = no contour): hull = the contour of every silhouette, an inverted black copy of the body as a second mesh (outline.py, PIPELINE 33.L15-3); "
                         "--eye on --eye-paint on: ink = only the line painted in the texture (no hull mesh), both = line + hull (PIPELINE 35.L17-3); ink alone is no contour without the paint")
    ap.add_argument("--face", choices=("decal", "off"), default="off",
                    help="stage 2: decal = the head cut from the concept at 128 px on one quad in front of the head instead of the 64 px lathe decal (PIPELINE 33.L15-3)")
    ap.add_argument("--zone-contrast", choices=("on", "off"), default="off",
                    help="stage 2: palette slots closer than dE 8 push the darker one x.8 in luma (PIPELINE 33.L15-3)")
    ap.add_argument("--materials", choices=("merge", "split"), default="merge",
                    help="stage 2 cel: merge = slots sharing the atlas fold into one material, one draw (build_unit.MERGE_MATERIALS, "
                         "PIPELINE 27.T5); split = one material per palette slot, as before")
    ap.add_argument("--atlas-dir", type=pathlib.Path, default=ROOT / "artifacts/model-sheets/atlas",
                    help="--atlas shared: where the per-race column tables <race>.json live (append only)")
    ap.add_argument("--colour-only", type=pathlib.Path, default=None, metavar="RUN_DIR",
                    help="stage 2 alone on the frozen shape of an existing run (its spec, clay and sidecars are copied to --out; "
                         "no author, no fit; PIPELINE 32.L14-2)")
    ap.add_argument("--shape-only", action="store_true",
                    help="stop after stage 1 (clay + shape gates), even when stage 2 exists")
    ap.add_argument("--colour-on-fail", choices=("on", "off"), default="on",
                    help="stage 2 also runs when stage 1 failed (default on: model.glb, texture and turntable exist in every run, "
                         "the verdict stays CHECK); off = the old rule, stage 2 only after a passing stage 1 (PIPELINE 30.L12-4)")
    ap.add_argument("--colour-pass", type=int, default=0,
                    help="stage 2 colour-pass tries when the zone gate fails (palette/decals only)")
    ap.add_argument("--polish", choices=("on", "off"), default="off",
                    help="after the clay is final and before stage 2, the model polishes it through the MCP server of polish.py "
                         "(5 min, 12 ops, every op gated and reverted when a view gets worse; PIPELINE 31.L13-1); needs --model session:<claude>")
    ap.add_argument("--no-silhouette", action="store_true", help="skip the IoU gate")
    ap.add_argument("--no-rts", action="store_true",
                    help="do not draw the RTS concept view when the sheet has none")
    ap.add_argument("--spec", type=pathlib.Path, default=None,
                    help="start from this spec JSON instead of asking the model for one")
    ap.add_argument("--hull", action="store_true",
                    help="building kinds: the base volume is the sheet's front x left hull "
                         "(building_hull.py); the author only writes roof and props (PIPELINE 20.L13)")
    ap.add_argument("--cull", action="store_true",
                    help="stage 1 build deletes the faces no view sees (cull.py, PIPELINE 20.M8); "
                         "visible/total tris are always reported")
    ap.add_argument("--fit", dest="fit", action="store_true", default=True,
                    help="(default) after repair/passes and before the final build, fit dims/at to the "
                         "sheet's silhouettes (fit_spec.py, PIPELINE 19.D1, 20.N12)")
    ap.add_argument("--fit-edges", action="store_true",
                    help="the fit also pulls part outlines onto the hard sheet's inner edges (fit_spec.edge_term, "
                         "PIPELINE 21.F7)")
    ap.add_argument("--no-fit", dest="fit", action="store_false", help="skip the numeric fit")
    ap.add_argument("--fit-fast", action="store_true",
                    help="the classic fit: front/left/back, dims and at, no cut test (about a third of the time)")
    ap.add_argument("--fit-stages", action="store_true",
                    help="the fit runs trunk, limbs and profiles one after the other, 1/3 of the budget each "
                         "(PIPELINE 22.L4-3: not better than the single Powell, opt-in)")
    ap.add_argument("--fit-grad", action="store_true",
                    help="the fit runs Adam on the differentiable soft-silhouette proxy instead of Powell (fit_grad.py, "
                         "PIPELINE 26.L8-7; fit_accepted still judges on the hard raster, opt-in)")
    ap.add_argument("--constraints", type=pathlib.Path, default=None,
                    help="a diagnosis.json: its scale/radius/move deltas become per-part limits of the --fit (L11-3, via B; "
                         "PIPELINE 29.L11-3); add/remove/rotate are ignored here")
    ap.add_argument("--fit-parts", action="store_true",
                    help="the fit also uses refs/<id>/parts.json: each part inside its 2D mask, depth order as a hard "
                         "constraint (PIPELINE 23.L5-4; neutral on the silhouettes, opt-in)")
    ap.add_argument("--depth", action="store_true",
                    help="the fit starts from Depth Anything V2 small's z and occlusion order (depth_map.py, needs "
                         "parts.json, implies --fit-parts; PIPELINE 23.L5-4b)")
    ap.add_argument("--parts", type=pathlib.Path, default=None,
                    help="a parts.json other than refs/<id>/parts.json for the fit (implies --fit-parts)")
    ap.add_argument("--depth-source", choices=("tri", "none"), default="none",
                    help="tri: a spec part whose z lies outside the box3d refs/<id>/parts.json triangulated for it (front x left, "
                         "the pinned top camera for what one panel shows) moves into it, kept when the 2D proxy loses no view by "
                         "more than 2 sigma (depth_rule.py, PIPELINE 30.L12-8); none: the spec's z stays")
    ap.add_argument("--no-fewshot", action="store_true",
                    help="leave the worked spec -> render example out of the author's prompt "
                         "(PIPELINE 21.F5)")
    ap.add_argument("--no-massing", action="store_true",
                    help="skip stage 0: the author writes the mass from scratch (old brief) instead of editing "
                         "the deterministic pre-spec of massing.py (PIPELINE 21.F1)")
    ap.add_argument("--variants", type=int, default=3,
                    help="best of N: ask the author for N specs, run stage 1 on each (in "
                         "variants/<k>/, kept) and go on with the one with the largest sum of "
                         "margins over the gates (default 3; 1 turns it off)")
    ap.add_argument("--decimate", action="store_true",
                    help="Readiness: decimate the clay 50 %% in Blender and report the IoU lost per 100 tris "
                         "(report only, about 8 s; PIPELINE 20.M10)")
    ap.add_argument("--budgets", type=lambda t: [int(x) for x in t.split(",")], default=None, metavar="400,700,1000",
                    help="ablation (Wiersma 2026 Fig. 10): build the --spec at each triangle budget and write the "
                         "IoU x tris x slivers curve and the knee to review.md; no author, no stage 2 (PIPELINE 24.L6-10)")
    ap.add_argument("--align", dest="align", action="store_true", default=ALIGN_FEATURES,
                    help="pull the unioned body's sharp edges to the hard sheet's inner edges after the "
                         "deformation (align_features.py, PIPELINE 24.L6-12; off by default: no measured gain)")
    ap.add_argument("--no-align", dest="align", action="store_false", help="the opposite of --align")
    for name, what in (("snap", "snap the body's vertices onto the planes of its flat regions (look.py, PIPELINE 30.L12-9)"),
                       ("creases", "with --look-snap: the hard sheet's drawn lines are region borders"),
                       ("ink", "stage 2 cel: ink along the edges that run on the hard sheet's lines")):
        ap.add_argument(f"--look-{name}", choices=("on", "off"), default="off", help=what)
    ap.add_argument("--sdf-grid", type=int, default=0, help="--body sdf: voxels along the longest side (0 = build_unit.SDF_GRID, 96)")
    ap.add_argument("--sdf-k-mode", choices=("base", "class", "hard", "ext"), default="base",
                    help="--body sdf: how each junction's smooth-min k is chosen (sdf_body.K_MODES, PIPELINE 29.L11-5)")
    ap.add_argument("--sdf-retopo", choices=("qem", "cvt"), default="qem",
                    help="--body sdf: the retopology of the dense body (retopo.retopo method; cvt = curvature-guided Voronoi, PIPELINE 29.L11-6)")
    ap.add_argument("--sdf-core", choices=("on", "off"), default=DEFAULT_SDF_CORE,
                    help="--body sdf: only the core (trunk, pelvis, thighs, arms) enters the SDF; head, hands, feet, props and hard plates stay rigid "
                         "pieces with their own material and bone, the retopology budget divided by area (build_unit sdf_core=, PIPELINE 33.L15-2)")
    ap.add_argument("--inscribe", choices=("off", "cut", "on"), default="off",
                    help="inscribe the model in the sheet's visual hull (inscribe.py, PIPELINE 31.L13-5): cut = the SDF body is intersected with the "
                         "coherent views' masks before the retopology (--body sdf), on = cut + the vertices still outside the masks after the "
                         "deform and the vertex fit are pulled in")
    ap.add_argument("--inscribe-erode", type=int, default=inscribe.ERODE_PX, metavar="PX",
                    help="--inscribe: the masks are eroded this many canvas px (default 1)")
    ap.add_argument("--tilts", default="",
                    help="pin the approved silhouette's top/bottom/rts cameras (silhouette.py --tilts, e.g. bottom:20,rts:55/-60): "
                         "lets two builds of one spec be compared on the same cameras (sdf_batch.py)")
    ap.add_argument("--incoherent-weight", type=float, default=None,
                    help="opt-in: the weight in the fit, the deformation and the vertex optimiser of a view the sheet contradicts "
                         "(sheet_report 'incoherent'): 0 ignores it (still measured and printed), 1 drops the rig's extra weight; "
                         "unset = as any view (PIPELINE 30.L12-5)")
    ap.add_argument("--author-guard", choices=author_guard.MODES, default="off",
                    help="the author's spec against the massing before the fit (PIPELINE 30.L12-3): a view more than "
                         "author_guard.AUTHOR_DROP under the massing's plain clay -> revert = the bones that explain it go back to "
                         "the massing's (reject if it still falls), reject = the massing's body with the author's props, off = nothing")
    ap.add_argument("--dsl-repair", choices=("on", "off", "all"), default="on",
                    help="the DSL rules of dsl_rules.py (hood_recess, prop_axis, prop_coverage, leg_joints; PIPELINE 30.L12-6; prop_side, arm_pose, part_exists, incoherent_part: 33.L15-4) are repaired "
                         "in code, with no model call, before the numeric fit; the repairs go to review.md. on = spider legs, "
                         "all = also prop_side, arm_pose, reject-part, the hood and the props (opt-in: n005 front falls .006-.013), off = the author's spec as it is")
    ap.add_argument("--body", choices=("union", "sdf", "join"), default=DEFAULT_BODY,
                    help="how the body parts become one shell: union = boolean + decimate (24.L6-4), sdf = distance field + "
                         "guarded QEM retopology (build_unit sdf_union, PIPELINE 28.L10-7), join = the plates joined, no weld")
    ap.add_argument("--no-deform", dest="deform", action="store_false", default=DEFORM,
                    help="skip the Sketch2Mesh deformation of the unioned body onto the sheet's outlines "
                         "(deform_to_sheet.py, PIPELINE 24.L6-5)")
    ap.add_argument("--fit-verts", dest="fit_verts", action="store_true", default=FIT_VERTS,
                    help="after the deformation, optimise the body's vertex positions against the 6 sheet views at a "
                         "fixed topology (optimize_verts.py, Wiersma 2026; 30 s with the soft gradient; default since "
                         "PIPELINE 26.L8-6b)")
    ap.add_argument("--no-fit-verts", dest="fit_verts", action="store_false", help="skip the vertex optimisation")
    ap.add_argument("--flip-side", action="store_true",
                    help="front/left/back pick the mirror by the shift-tolerant IoU (29.L11-0, opt-in); sets CF_FLIP_SIDE for the tools")
    ap.add_argument("--deterministic", action="store_true",
                    help="no wall-clock budgets in the fit and fit-verts (iteration counts only): two builds of one spec give the "
                         "same IoU; implied by --loop")
    ap.add_argument("--noise", type=pathlib.Path, default=None, metavar="noise.json",
                    help="sigma per view from sdf_batch.py --repeat (L12-7): the loop and the author/fit guards use max(2 sigma, 0.005) "
                         "per view instead of their fixed 0.01; without it nothing changes")
    ap.add_argument("--loop", type=int, default=0, metavar="N",
                    help="guarded VLM loop (L11-2): N rounds of diagnose -> one delta at a time -> rebuild with the round-0 "
                         "cameras -> keep it only if no view falls > 0.01 and the mean rises >= 0.005 (0 = off)")
    ap.add_argument("--frame", choices=("bbox", "body"), default=None,
                    help="frame the sheet panels and the model by the figure's bbox or by its body without the props "
                         "(29.L11-0b, deform + optimize_verts + silhouette); sets CF_FRAME for the tools")
    ap.add_argument("--no-repair", action="store_true",
                    help="skip the pass-0 repair of preflight failures (on by default)")
    ap.add_argument("--passes", default="",
                    help="comma-separated views to refine after the sheet pass, e.g. left,back,front")
    ap.add_argument("--diagnose", dest="diagnose", action="store_true", default=None,
                    help="LLM diagnosis of the finished run (diagnose.py); default on for CHECK, "
                         "off for PASS. An output only: nothing goes back to the model")
    ap.add_argument("--no-diagnose", dest="diagnose", action="store_false", help="no diagnosis, even for CHECK")
    ap.add_argument("--gate", choices=("silhouette", "parts"), default="silhouette",
                    help="stage 1 gate (silhouette.py --gate): silhouette = IoU and spill of every view; parts = they are guards, the acceptance "
                         "is parts >= 80 percent (parts_gate.py, PIPELINE 33.L15-1)")
    ap.add_argument("--orient", choices=("sheet", "model"), default="sheet",
                    help="top/bottom rotation and left mirror from refs/<id>/sheet.json (parts_gate.py freeze) or decided again for each model")
    ap.add_argument("--judge-gate", choices=("on", "off"), default="off",
                    help="on: with --pair, the paired judge is a non-regression gate: losing form or artist 3-1 / 4-0 to the earlier run "
                         "makes a passing verdict CHECK (review_pair.regressed; 1 judge call per unit)")
    ap.add_argument("--pair", type=pathlib.Path, default=None,
                    help="an earlier run dir of this unit: pairwise vision review against it "
                         "(review_pair.py); losing both axes demotes the status one level")
    ap.add_argument("--eye", choices=("off", "on", "replay"), default="off",
                    help="on: the stage with an eye (eye_stage.py, PIPELINE 33.L15-5): the model sees concept x render and redoes the parts by primitive "
                         "(session:<model> only); replay: rebuild from the recorded DSL, no model call")
    ap.add_argument("--eye-skin", choices=("off", "bridge", "blend", "wrap", "weld"), default="off",
                    help="--eye on: skin at the joints of the pieces after the last round (eye_skin.py, PIPELINE 34.L16-4)")
    ap.add_argument("--eye-union", choices=("off", "material", "bone", "group"), default="bone",
                    help="--eye on: the pieces of a group (one material / one bone / touching pieces of one material) united in one welded mesh after the last "
                         "round, instead of --eye-skin (eye_union.py, PIPELINE 35.L17-2); default bone since 37.L19-0 (the v18-cvt recipe, the author's decision "
                         "against the 4-vote judge); off = the pieces as the eye left them")
    ap.add_argument("--eye-paint", choices=("off", "on", "box"), default="box",
                    help="--eye on: UV atlas 256 px painted procedurally (gradient, brush noise, occlusion, 12 colours, ink line) over the flat-colour pieces (eye_paint.py, PIPELINE 35.L17-3); "
                         "box = one chart per welded component and axis, large islands for the united mesh (36.L18-3; default since 37.L19-0); on = grown islands; off = flat colours")
    ap.add_argument("--eye-project", choices=("off", "on", "tight"), default="tight",
                    help="--eye on, with a painted atlas: the concept sheet delit and projected on the atlas from its five panels and the left mirrored (eye_project.py, PIPELINE 39.L20-0); "
                         "texels no view sees keep the procedural paint; tight (default by the author, L20-2): flat, with the colour gate and the per-piece filter, accents kept")
    ap.add_argument("--eye-union-reduce", choices=("qem", "cvt"), default="cvt",
                    help="--eye-union: the reducer from the union's grid to the budget: guarded QEM (retopo.reduce) or curvature-guided CVT (retopo.cvt, 36.L18-2b; default since 37.L19-0: "
                         "always under the 700 budget, 2x faster; a cluster too thin for the CVT falls to the QEM, and to its own pieces when the QEM overshoots)")
    ap.add_argument("--eye-fuse", type=int, default=12, metavar="N",
                    help="--eye on: fuse the near colours of the final DSL (OKLab, same class) down to at most N materials before the union and the paint (eye_fuse.py, 36.L18-1); "
                         "0 = off; default 12 since 37.L19-0")
    ap.add_argument("--eye-critic", default="off", metavar="MODEL[@EFFORT]",
                    help="--eye: a Claude model (claude -p --model, '@max' = --effort max) that finds the defects of each round; the stage's model only fixes "
                         "them (eye_critic.py, PIPELINE 34.L16-2); off = one model looks and fixes")
    ap.add_argument("--eye-fixer", default=None, metavar="MODEL", help="--eye-critic: the Claude model that applies the defects (default: --model)")
    ap.add_argument("--eye-rounds", type=int, default=3, metavar="N", help="--eye on: rounds of look and redo (1-9; a disaster adds rounds up to 4 or N)")
    ap.add_argument("--eye-stop", choices=("judge", "model", "never"), default="model",
                    help="--eye on: who ends the loop early (PIPELINE 34.L16-1). model: the model's {stop}; never: its stop is recorded, not honoured (a measurement run); "
                         "judge: the model's stop, and two rounds in a row that add no part and win neither sheet nor artist against the round before (review_pair, 4 votes a round)")
    ap.add_argument("--eye-from", default=None, metavar="RUN", help="--eye: only the eye stage, on runs/<id>/RUN, into --run")
    ap.add_argument("--out", type=pathlib.Path, default=None,
                    help="run dir; default runs/<id>/<run>")
    return ap


def noop_notes(args):
    """One line per opt-in the arguments switch on whose precondition is missing, so it would run without effect
    ("no-op: <flag>: <why>"); main() prints them. The flags whose precondition is in the data (parts.json without box3d,
    no massing spec, no approved round 0) say so where they find out (fit_spec.attach_parts, guard_stage, run_loop)."""
    cel_only = [f for f, on in (("--ramp", args.ramp), ("--fit-luma", args.fit_luma), ("--atlas", args.atlas != "own"),
                                ("--materials", args.materials != "merge")) if on and args.texture != "cel"]
    fit_only = [f for f, on in (("--fit-edges", args.fit_edges), ("--fit-stages", args.fit_stages), ("--fit-grad", args.fit_grad),
                                ("--fit-fast", args.fit_fast), ("--fit-parts", args.fit_parts), ("--depth", args.depth),
                                ("--parts", args.parts), ("--constraints", args.constraints)) if on and not args.fit]
    stage1_only = [f for f, on in (("--colour-pass", args.colour_pass), ("--ramp", args.ramp), ("--fit-luma", args.fit_luma)) if on and args.shape_only]
    sdf_only = [f for f, on in (("--sdf-grid", args.sdf_grid), ("--sdf-k-mode", args.sdf_k_mode != "base"),
                                ("--sdf-retopo", args.sdf_retopo != "qem"), ("--sdf-core", args.sdf_core != DEFAULT_SDF_CORE), ("--inscribe cut", args.inscribe == "cut")) if on and args.body != "sdf"]
    unioned_only = (["--align"] if args.align and args.body == "join" else [])
    why = [(cel_only, "stage 2 reads it for --texture cel only"), (fit_only, "--no-fit"), (stage1_only, "--shape-only: no stage 2"),
           (sdf_only, f"--body {args.body}, it is for --body sdf"), (unioned_only, "--body join: no unioned body to deform"),
           (["--loop"] if args.loop and args.no_silhouette else [], "--no-silhouette: no approved round 0")]
    return [f"no-op: {', '.join(flags)}: {reason}" for flags, reason in why if flags]


def print_noops(args):
    for note in noop_notes(args):
        print(note)


def utility_command():
    """The two commands that need no other flag; True when one ran."""
    if sys.argv[1:] == ["--check-rts"]:   # figures per existing RTS view
        for name, n in check_rts().items():
            print(f"{n} {name}")
        return True
    if sys.argv[1:2] == ["--redo-rts"]:   # --redo-rts refs/<id>/sheet.jpg: redraw that sheet's rts view
        print("kept the old rts" if not redo_rts(pathlib.Path(sys.argv[2]).resolve()) else "rts redone")
        return True
    return False


def main():
    if utility_command():
        return
    ap = build_parser()
    args = ap.parse_args()
    overrides.apply()          # ablation_matrix.py only (CF_OVERRIDES); nothing without it
    os.environ["CF_FLIP_SIDE"] = str(int(args.flip_side or os.environ.get("CF_FLIP_SIDE") == "1"))   # the tools read it (silhouette.FLIP_SIDE)
    os.environ["CF_FRAME"] = args.frame or os.environ.get("CF_FRAME", "bbox")
    import silhouette
    silhouette.FRAME = os.environ["CF_FRAME"]      # read at import: deform, verts and inscribe imported it before this line ran (L15-1)
    if args.variants < 1:
        ap.error("--variants must be at least 1")
    args.deterministic = args.deterministic or args.loop > 0
    args.style = args.texture        # the old name, for stage 2 code that still reads it
    global BODY, SDF_GRID, SDF_K_MODE, SDF_RETOPO, SDF_CORE
    BODY, SDF_GRID, SDF_K_MODE, SDF_RETOPO, SDF_CORE = args.body, args.sdf_grid, args.sdf_k_mode, args.sdf_retopo, args.sdf_core
    view_defs.INCOHERENT_WEIGHT = args.incoherent_weight
    args.union_body = args.body != "join"

    resolve_paths(args)
    print_noops(args)
    if args.colour_only or args.eye_from:
        return one_stage(args)

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
    if args.budgets:
        set_rig(args.rig, spider_measure(args))
        return run_budgets(args, layout)
    args.drift = check_drift(args, layout)
    sheet, refs, tmp = prompt_images(args, args.out / ".." / "..")
    args.refs = refs
    set_rig(args.rig)
    args.hull_part = hull_for(args, layout)
    set_rig(args.rig, spider_measure(args))
    args.pre_spec = massing_spec(args)
    brief = with_refs(make_brief(args, lo, hi), refs, hard_first=args.build != args.sheet,
                      props=load_props(args.id))
    brief, shots = with_fewshot(brief, args, 2 + len(refs))
    spec, shape = stage_one(args, brief, [sheet] + [p for _, p in refs] + shots, tmp, layout)
    spec, shape = run_loop(args, spec, shape, layout)
    save_guard(args)
    run_polish(args, shape)
    colour = None
    if wants_colour(args, shape):
        t0 = time.monotonic()
        colour = run_colour(spec, shape, args)
        args.times["colour"] = time.monotonic() - t0
    run_eye(args)
    args.infra = infra_check(args, shape, colour)
    save_infra(args)
    verdict = verdict_of(shape, colour, args.infra)
    args.pairwise = pairwise_of(args, shape)
    verdict = judge_verdict(args, verdict)
    write_review(args, shape, colour, verdict)
    run_diagnose(args, verdict)       # after spec.json, review.md and compare.png: reads them, changes none
    stage2 = "-" if colour is None else ("PASS" if colour[0] else "FAIL")
    print(f"{args.id}\t{args.run}\t{args.tag}\ttris {shape['tris']}/{lo}-{hi}\t"
          f"skins {shape['skins']}\tanims {shape['anims']}\tsmear {shape['smear']} %\t"
          f"preflight {'PASS' if shape['checks'].get('preflight') else 'FAIL'}\t"
          f"stage1 {'PASS' if shape['ok'] else 'FAIL'}\tstage2 {stage2}\t{verdict}")
    return exit_code(args, verdict)


def exit_code(args, verdict):
    """2 when a stage did not happen (FAIL(infra), listed), 1 for a failed gate (CHECK), 0 for a pass."""
    if args.infra:
        print("FAIL(infra): " + "; ".join(args.infra))
        return 2
    return 0 if verdict in OK_VERDICTS else 1


def loop_hooks(args, layout):
    """The callbacks loop_stage.run needs, over this run: a rebuild takes the round-0 path (fit_stage -> stage_shape on a copy
    of args whose out is the candidate dir, same --tilts), the current best always lives in args.out."""
    import apply_deltas      # imports this module: lazily
    import copy
    import types
    base = args.out / "loop"

    def rebuild(spec, out):
        a = copy.copy(args)
        a.out, a.summary = out, {}
        out.mkdir(parents=True, exist_ok=True)
        spec = fit_stage(spec, a)
        (out / "spec.json").write_text(json.dumps(spec, indent=2))
        return spec, stage_shape(out / "spec.json", a, layout), a.summary

    def promote(cur):
        shutil.copytree(cur["dir"], args.out, dirs_exist_ok=True)
        cur["shape"]["glb"], args.summary = args.out / "clay.glb", cur["summary"]

    def prepare(cur):
        args.summary, args.pairwise = cur["summary"], None
        write_review(args, cur["shape"], None, verdict_of(cur["shape"], None))

    def diagnose_run():
        try:
            return diagnose.run_diagnosis(args.out, args.id, args.kind, args.model)
        except (RuntimeError, OSError, *BAD_REPLY) as err:
            print(f"loop: diagnosis skipped: {err}")
            return {"deltas": [], "expected": {}, "cost": {"seconds": 0.0, "tokens": {}}}

    return types.SimpleNamespace(
        **noise_kw(args), loop_dir=base, rebuild=rebuild, promote=promote, prepare=prepare, diagnose=diagnose_run,
        apply=lambda spec, deltas: apply_deltas.apply(spec, deltas, diagnose.spec_height(spec)))


def run_loop(args, spec, shape, layout):
    """--loop N after the approved round 0: snapshot round 0 in loop/round0/, run loop_stage, leave the best in args.out.
    Returns (spec, shape); args.summary and args.loop_report are the best's. No-op without --loop or an approved round 0."""
    args.loop_report = None
    if args.loop and not (shape["glb"] is not None and args.summary.get("approved")):
        print("no-op: --loop: no approved round 0 (the build failed or the silhouette was not measured)")
    if not (args.loop and shape["glb"] is not None and args.summary.get("approved")):
        return spec, shape
    hooks = loop_hooks(args, layout)
    r0 = hooks.loop_dir / "round0"
    r0.mkdir(parents=True, exist_ok=True)
    for name in ("clay.glb", "spec.json", "silhouette.json"):
        shutil.copy(args.out / name, r0 / name)
    shutil.copytree(args.out / "views", r0 / "views", dirs_exist_ok=True)
    t0 = time.monotonic()
    spec, shape, args.summary, args.loop_report = loop_stage.run(args.loop, spec, shape, args.summary, hooks)
    args.times["loop"] = time.monotonic() - t0
    print(f"loop: mean {args.loop_report['mean'][0]} -> {args.loop_report['mean'][1]} in {args.times['loop']:.0f} s")
    return spec, shape


def run_diagnose(args, verdict):
    """diagnose.py on the finished run when --diagnose, or (unset) when the verdict is CHECK.
    A failed call costs the diagnosis only, never the run."""
    if not (verdict == "CHECK" if args.diagnose is None else args.diagnose):
        return None
    try:
        r = diagnose.run_diagnosis(args.out, args.id, args.kind, args.model)
    except (RuntimeError, OSError, *BAD_REPLY) as err:
        print(f"diagnosis skipped: {err}")
        return None
    print(f"diagnosis: {len(r['findings'])} findings, owner {r['owner']['who']}, {r['cost']['seconds']} s")
    return r


OK_VERDICTS = ("PASS", "SHAPE-PASS")
TRI_SLACK = 0.02      # stage 1 accepts the GLB this far over the class ceiling
FIT_SLIP = 0.02       # fit_accepted: a passing view may slip this far under its gate when more views pass
VIEW_FLOOR = {None: ("front", "rts"), "spider": ("top", "bottom", "rts"),
              "spider_high": ("top", "bottom", "rts")}   # fit_accepted: the family's critical views never fall > FIT_SLIP
RED_SLIP = 0.02       # fit_accepted: the mean uncovered share (the overlay's red) may not grow more than this
FORM_W = 0.5          # fit_accepted / margin_of: form cost (slivers + mean normal_diff / 90), PIPELINE 24.L6-6
ALIGN_FEATURES = False  # PIPELINE 24.L6-12: sharp edges go to the hard sheet's inner edges after the deformation (--align); NEGATIVE: off
DEFORM = True         # PIPELINE 24.L6-5: the unioned body is deformed onto the sheet's outlines (--no-deform)
FIT_VERTS = True      # PIPELINE 26.L8-6b: default (30 s, soft gradient); the ablation gained 6/6 views on 5/5 units. --no-fit-verts turns it off
# 24.L6-4: the deformation needs the welded body; read build_unit.BODY (union | sdf | join) from its source (it imports bpy)
DEFAULT_BODY = re.search(r'^BODY\s*=\s*"(\w+)"', (ROOT / "tools/blender/build_unit.py").read_text(), re.M).group(1)
SDF_K_MODE = "base"      # --sdf-k-mode: build_unit sdf_k_mode= (sdf_body.K_MODES)
DEFAULT_SDF_CORE = "on" if re.search(r'^SDF_CORE\s*=\s*True', (ROOT / "tools/blender/build_unit.py").read_text(), re.M) else "off"
SDF_CORE = DEFAULT_SDF_CORE   # --sdf-core: build_unit sdf_core= (only the core in the SDF)
SDF_RETOPO = "qem"       # --sdf-retopo: build_unit sdf_retopo= (retopo.retopo method)
SDF_GRID = 0             # --sdf-grid: build_unit sdf_grid= (0 = its SDF_GRID default)
BODY = DEFAULT_BODY      # main() sets it from --body; clay_args passes it to build_unit when it is not the default
RED_W = 1.0           # margin_of: a variant pays its mean uncovered share against its IoU margins
RED_CRITICAL = ("front", "left", "back", "rts")   # too_red: the views whose red caps the status


def run_colour(spec, shape, args):
    """Stage 2 on the approved spec: (ok, report), or None when colour_stage does not
    exist yet. Its turntable is shot here from the model.glb it wrote."""
    stage = load_colour_stage()
    if stage is None:
        print("stage 2: tools/blender/colour_stage.py not found; the run ends after stage 1")
        return None
    work = args.out / "stage2"
    work.mkdir(parents=True, exist_ok=True)
    ok, report = stage.stage_colour(spec, shape["glb"], args, shape["tilts"], work)
    if getattr(args, "polish", "off") == "on" and (args.out / "polish.json").exists():
        import polish
        polish.after_colour(args)          # the textured model.glb was rebuilt from the spec: it gets the clay's polish
    if (args.out / "model.glb").exists():      # whatever the colour gate said: the judge looks at the turntable (L12-4)
        turntable(args, args.out / "model.glb")
    return ok, report


def one_stage(args):
    """--colour-only RUN: stage 2 alone on RUN; --eye-from RUN: the eye stage alone on RUN."""
    return colour_only(args) if args.colour_only else eye_only(args)


def eye_ask(args):
    """The model call of the eye stage (L15-5). Only a Claude session reads the images it is given (SystemExit otherwise)."""
    if not args.model.startswith(SESSION):
        raise SystemExit("--eye needs --model session:<claude model>")
    import eye_stage
    return eye_stage.session_ask(f"session:{args.eye_fixer}" if args.eye_fixer else args.model)


def run_eye(args):
    """--eye on|replay after stage 2: the eye stage on this run's model.glb (PIPELINE 33.L15-5); nothing when off."""
    if args.eye != "off":
        import eye_stage
        eye_stage.run_in_pipeline(args, args.out, eye_ask(args))


def eye_only(args):
    import eye_stage
    return eye_stage.from_run(args, eye_ask(args))


def colour_only(args):
    """--colour-only RUN: copy the frozen shape of RUN (spec, clay and their sidecars, silhouette.json) into args.out and
    run stage 2 on it, with the cameras stage 1 pinned. Prints the zones line; exit 0 when the colour gate holds."""
    src, out = args.colour_only, args.out
    args.rig = args.rig or ("building" if layout_of(args.kind) == "building" else "biped")        # as main() sets them before stage 2
    args.build = args.hard if args.image1 == "hard" and args.hard and args.hard.exists() else args.sheet
    out.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        if f.is_file() and (f.name.startswith("clay") or f.name in ("spec.json", "silhouette.json", "attach.json", "cull.json")):
            shutil.copy(f, out / f.name)
    tilts = {v: tuple(t) if isinstance(t, list) else t for v, t in json.loads((out / "silhouette.json").read_text())["tilt"].items()}
    t0 = time.monotonic()
    ok, _ = run_colour(json.loads((out / "spec.json").read_text()), {"glb": out / "clay.glb", "tilts": tilts}, args)
    print(f"{args.id}\t{args.run}\tcolour-only {args.texture}\tstage2 {'PASS' if ok else 'FAIL'}\t{time.monotonic() - t0:.0f} s")
    return 0 if ok else 1


def run_polish(args, shape):
    """--polish on: the polish stage on the final clay (L13-1); its report, or None (off, no clay, or a model that is not a Claude session)."""
    if args.polish != "on" or shape["glb"] is None or not args.model.startswith(SESSION):
        return None
    import polish
    return polish.run_in_pipeline(args)


def wants_colour(args, shape):
    """Stage 2 runs unless --shape-only, or (--colour-on-fail off) stage 1 failed, or there is no clay to texture."""
    return not args.shape_only and shape["glb"] is not None and (shape["ok"] or args.colour_on_fail == "on")


def infra_check(args, shape, colour):
    """What a finished run is missing, one line each: a stage whose file was not written, a module that
    was not found, a stage 2 that was due and did not run. Empty = the infrastructure held. Not a gate:
    a gate that fails is CHECK, a stage that did not happen is FAIL(infra) (PIPELINE 30.L12-4).
    --shape-only, --colour-on-fail off after a failed stage 1, --no-silhouette, --no-deform, --no-fit-verts
    and a join body justify the files they would have written."""
    out, missing = args.out, []

    def need(stage, *names):
        missing.extend(f"{stage}: {n} not written" for n in names if not (out / n).exists())

    need("author/spec", "spec.json")
    if rules_of(shape["pre"]) == "-":
        missing.append("preflight: no 'rules pass' line in its output")
    if shape["glb"] is None:
        return [*missing, "build/clay: clay.glb not built"]
    need("build/clay", "clay.glb")
    if args.union_body and args.deform:
        need("deform", "clay.deform.json")
    if args.union_body and args.fit_verts:
        need("verts", "clay.verts.json")
    if not args.no_silhouette:
        need("gate stage 1", "silhouette.json")
    if wants_colour(args, shape):
        if colour is None:
            missing.append("colour stage 2: due and not run (tools/blender/colour_stage.py not found)")
        else:
            need("colour stage 2", "model.glb", "stage2/colour.json", "turntable.gif")
    return missing


def save_infra(args):
    """infra.json beside silhouette.json: the list infra_check returned (sdf_batch.py reads it for its verdict column)."""
    (args.out / "infra.json").write_text(json.dumps(args.infra, indent=2))


def verdict_of(shape, colour, infra=()):
    """FAIL(infra) when a stage did not happen; CHECK when a stage failed; SHAPE-PASS when stage 1 passed and
    stage 2 did not run; PASS only when both stages passed."""
    if infra:
        return "FAIL(infra)"
    if not shape["ok"] or (colour is not None and not colour[0]):
        return "CHECK"
    return "SHAPE-PASS" if colour is None else "PASS"


def massing_section(args):
    """review.md: the pre-spec alone (stage 0): IoU per view against the approved sheet, preflight rules,
    tris, and what the author changed in it. Empty without a pre-spec."""
    r = getattr(args, "massing_report", None)
    if not r:
        return ""
    views = ("front", "left", "back", "top", "bottom", "rts")
    iou = " / ".join(f"{r['iou'][v]:.3f}" if v in r["iou"] else "-" for v in views)
    edit = ("" if "edit" not in r else
            f"| author edit | {r['edit'][0]} parts new or edited, {r['edit'][1]} dropped (of {len(args.pre_spec['parts'])}) |\n")
    return (f"## Stage 0 - massing alone (massing/)\n\n| item | value |\n|---|---|\n| views | {' / '.join(views)} |\n"
            f"| IoU vs approved (massing alone) | {iou} |\n"
            f"| stage 1 gates | {'PASS' if r['ok'] else 'FAIL: ' + ', '.join(r['failed'])} |\n"
            f"| preflight rules | {r['rules']} |\n| tris | {r['tris']} |\n{edit}\n")


def save_guard(args):
    """The guard's and the DSL repair's reports into silhouette.json (the tables of a battery read them)."""
    reports = {k: r for k, r in (("guard", getattr(args, "guard_report", None)), ("dsl", getattr(args, "dsl_report", None))) if r}
    if reports and args.summary.get("approved"):
        args.summary.update(reports)
        (args.out / "silhouette.json").write_text(json.dumps(args.summary, indent=2))


def dsl_section(args):
    """review.md: the DSL rules before and after the code repair (PIPELINE 30.L12-6), and each repair (rule, part, before -> after)."""
    r = getattr(args, "dsl_report", None)
    if not r:
        return ""
    rows = "".join(f"| {rule} | {r['before'][rule]} | {r['after'][rule]} |\n" for rule in r["before"])
    fixes = "".join(f"- {rule} {part}: {was} -> {now}\n" for rule, part, was, now in r["repairs"]) or "- none needed\n"
    fixes += "".join(f"- incoherent_part {c['part']}: front {c['front']:+.2f} vs back {c['back']:+.2f}, {c['side']} wins, the gate ignores {c['ignore'][0]} for it\n" for c in r.get("coherence", []))
    return f"## DSL rules (dsl_rules.py, repaired in code)\n\n| rule | before | after |\n|---|---|---|\n{rows}\n{fixes}\n"


def guard_section(args):
    """review.md: the author's spec against the massing (PIPELINE 30.L12-3): IoU / spill per view at each stage
    (stage 1 of the massing, of the author before the fit, of what the guard tried; the final clay), and what was reverted and why."""
    r = getattr(args, "guard_report", None)
    if not r:
        return ""
    views = ("front", "left", "back", "top", "bottom", "rts")
    final = args.summary or {}
    stages = [(k, r["rows"][k]) for k in ("massing", "author", "revert", "reject", "fitted") if r["rows"].get(k)]
    stages.append(("final", {v: {"iou": final["approved"][v], "spill": final.get("spill", {}).get(v, 0.0)}
                             for v in final.get("approved", {})}))

    def line(label, key, fmt):
        return "".join(f"| {k} {label} | " + " / ".join(fmt(row[v][key]) if v in row else "-" for v in views) + " |\n"
                       for k, row in stages)
    why = (f"views under the massing by more than {author_guard.AUTHOR_DROP}: {', '.join(r['drops'])}; bones reverted: "
           f"{', '.join(r['reverted']) or 'none'}" if r["drops"] else "no view under the massing")
    why += f"; the fit put {', '.join(r['fit_drops'])} under it: spec kept as before the fit" if r.get("fit_drops") else ""
    return (f"## Author guard (mode {r['mode']}): {r['action']}\n\n| item | {' / '.join(views)} |\n|---|---|\n"
            f"{line('IoU', 'iou', '{:.3f}'.format)}{line('spill', 'spill', '{:.3f}'.format)}\n{why}\n\n")


def stage1_section(args, shape):
    lo, hi = BUDGETS[args.kind]
    rows = "".join(f"| {name} | {'PASS' if shape['checks'][name] else 'FAIL'} |\n"
                   for name in ("preflight", "silhouette") if name in shape["checks"])
    return (f"## Stage 1 - shape (clay): **{'PASS' if shape['ok'] else 'FAIL'}**\n\n"
            f"| gate | value |\n|---|---|\n{rows}"
            f"| tris | {shape['tris']}/{lo}-{hi} |\n| skins | {shape['skins']} |\n"
            f"| anims | {shape['anims']} |\n| smear | {shape['smear']}% |\n{cull_row(shape)}{look.row(shape['glb'])}{depth_rule.row(shape['glb'])}"
            f"{iou_rows(args.summary)}{prop_row(args.summary)}\n")


def infra_section(args):
    """review.md: the stages that did not happen (infra_check); empty when none."""
    infra = getattr(args, "infra", None)
    return "" if not infra else "## FAIL(infra)\n\n" + "".join(f"- {line}\n" for line in infra) + "\n"


def stage2_section(args, shape, colour):
    if colour is None and not shape["ok"]:
        return (f"## Stage 2 - colour: not run\n\nstage 1 failed ({', '.join(shape['failed'])}) and "
                f"{'--colour-on-fail off' if args.colour_on_fail == 'off' else 'there is no clay'}: no texture or turntable.\n")
    if colour is None:
        return "## Stage 2 - colour: not run\n\nno stage 2 for this run (--shape-only, or no colour_stage.py).\n"
    ok, report = colour
    body = report if isinstance(report, str) else "```json\n" + json.dumps(report, indent=2) + "\n```"
    body = re.sub(r"^## Stage 2[^\n]*\n+", "", body)      # one heading per stage: this one
    return (f"## Stage 2 - colour ({args.texture}): **{'PASS' if ok else 'FAIL'}**\n\n"
            f"{zone_rows(args.summary)}\n{body}\n")


def pairwise_of(args, shape):
    """The review_pair result of this run against --pair, or None (no --pair, no GLB)."""
    if not args.pair or shape["glb"] is None:
        return None
    other = pathlib.Path(args.pair)
    if not other.is_dir():                      # a run name: the sibling run of this unit
        other = args.out.parent / args.pair
    if not (other / "clay.glb").exists():
        print(f"pairwise: no clay.glb under {other}; skipped")
        return None
    return review_pair.compare(other, args.out, args.id, args.kind)


def lint_target(args, shape, colour):
    """(glb, textured): the stage 2 model when it was written, else the clay; (None, False)
    when the build failed."""
    model = args.out / "model.glb"
    if colour is not None and model.exists():
        return model, True
    return shape["glb"], False


def too_red(summary):
    """A critical view whose uncovered share (the overlay's red) is over silhouette.UNCOVERED_MAX."""
    from silhouette import UNCOVERED_MAX
    return any(u > UNCOVERED_MAX.get(v, 1.0) for v, u in (summary.get("uncovered") or {}).items()
               if v in RED_CRITICAL)


def identity_low(summary):
    """The identity checklist (preflight.identity_summary) is not 100 % there: prototype-safe at best."""
    ident = summary.get("identity") or {}
    return ident.get("ok", 0) < ident.get("total", 0)


def status_of(verdict, summary, lint_bad):
    """placeholder | prototype-safe | final-use | rejected (Begemann & Hutson 2026).
    SHAPE-PASS, or PASS with a failed lint gate, is prototype-safe; PASS with a clean lint is
    final-use; a CHECK whose front silhouette is more than 0.10 under its gate is rejected."""
    if verdict == "SHAPE-PASS" or (verdict == "PASS" and (lint_bad or too_red(summary) or identity_low(summary))):
        return "prototype-safe"
    if verdict == "PASS":
        return "final-use"
    front, gate = (summary.get("approved") or {}).get("front"), (summary.get("gates") or {}).get("front")
    return "rejected" if front is not None and gate is not None and front < gate - 0.10 else "placeholder"


def decimate_rows(args, shape):
    """The `--decimate` row of the Readiness table: IoU lost per 100 triangles of the clay at 50 % (report only)."""
    if not getattr(args, "decimate", False):
        return []
    r = mesh_lint.decimate_loss(shape["glb"], args.sheet, args.out / "decimate", layout_of(args.kind), args.rig)
    if r is None or r["lost_per_100_tris"] is None:
        return [("IoU lost per 100 tris (decimate 50 %)", "n/a", "-")]
    return [("IoU lost per 100 tris (decimate 50 %)",
             f"{r['lost_per_100_tris']:.4f} (tris {r['tris'][0]} -> {r['tris'][1]}, mean IoU {r['iou'][0]:.3f} -> {r['iou'][1]:.3f})", "-")]


SIDES_MAX = 16              # budget ablation: no round part gets more sides than this
SIDES_KINDS = {"prism": 8, "cyl": 8, "ring": 10, "lathe": lathe_limb.SIDES, "limb": lathe_limb.SIDES,
               "chain": lathe_limb.SIDES}   # kinds whose `sides` opt buys roundness, with the default
KNEE_SLOPE = 0.003          # a budget step that buys less IoU than this per 100 tris is past the knee
BUDGET_VIEWS = ("front", "left", "back", "top", "bottom", "rts")


def lift_sides(spec, budget):
    """The spec with `sides` raised by 2 on its biggest round parts, one at a time, while the
    preflight estimate stays within `budget`: the same spec spent on a larger budget (Wiersma
    2026 Fig. 10 ablation). Boxes and 4-sided frustums keep their shape; a spec already at or
    over the budget comes back unchanged."""
    parts = [list(p[:5]) + [dict(p[5])] for p in spec["parts"]]
    tris = sum(part_tris(p) for p in parts)
    order = sorted((i for i, p in enumerate(parts) if p[1] in SIDES_KINDS), key=lambda i: -max(parts[i][2]))
    grown = True
    while grown and order:
        grown = False
        for i in order:
            opts = parts[i][5]
            n = int(opts.get("sides", SIDES_KINDS[parts[i][1]]))
            if n >= SIDES_MAX:
                continue
            before = part_tris(parts[i])
            opts["sides"] = n + 2
            gain = part_tris(parts[i]) - before
            if tris + gain > budget:
                opts["sides"] = n
                continue
            tris, grown = tris + gain, True
    return {**spec, "parts": parts}


def budget_curve(rows):
    """[(budget, tris, iou, sliver_pct, lost_per_100)] ascending by real tris; `lost_per_100` is the
    mean IoU the step down from the next row lost per 100 tris removed (None on the last row)."""
    rows = sorted(rows, key=lambda r: r["tris"])
    out = []
    for r, nxt in zip(rows, rows[1:] + [None]):
        lost = None if nxt is None or nxt["tris"] <= r["tris"] else 100 * (nxt["iou"] - r["iou"]) / (nxt["tris"] - r["tris"])
        out.append((r["budget"], r["tris"], r["iou"], r["sliver_pct"], lost))
    return out


def knee_of(rows):
    """The budget at the knee of the IoU x tris curve: the smallest one whose step up to the next
    buys less than KNEE_SLOPE IoU per 100 tris (the last row when no step does). None without rows."""
    curve = budget_curve(rows)
    return next((b for b, _, _, _, lost in curve if lost is not None and lost < KNEE_SLOPE),
                curve[-1][0] if curve else None)


def budget_build(spec, args, budget, bdir):
    """One budget of the ablation, in bdir (laid out like a run, so compare_runs reads it): the spec
    with its sides lifted to `budget`, built as clay with the chamfer budget, collapse-decimated to
    `budget` when the build lands over it, measured against the approved sheet. Returns the row:
    budget, tris, iou (mean), iou_views, uncovered (mean), sliver_pct, seconds; None when no GLB came out."""
    bdir.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    spec = lift_sides(spec, budget)
    path, raw, glb = bdir / "spec.json", bdir / "raw.glb", bdir / "clay.glb"
    path.write_text(json.dumps(spec, indent=2))
    tool("build_unit.py", path, raw, str(budget), "nofuse", str(budget), "clay",
         *cut_hull.args(spec, args.sheet, args.kind, bdir), blender=True)
    if not raw.exists():
        return None
    tris = mesh_lint.lint_tris(raw)
    if tris > budget:
        tool("decimate_glb.py", raw, glb, budget / tris, blender=True)
    else:
        shutil.copy(raw, glb)
    if not glb.exists():
        return None
    saved, args.out = args.out, bdir
    try:
        _, report = silhouette_vs(args, glb, layout_of(args.kind), args.sheet, "approved")
    finally:
        args.out = saved
    seconds = time.monotonic() - t0
    view_dir = bdir / "views" / args.id
    tool("render_unit.py", glb, view_dir, tilt_arg(report), "lit", blender=True)
    if (view_dir / "clay-wc3.png").exists():
        shutil.copy(view_dir / "clay-wc3.png", view_dir / "clay-rts.png")
    ious = {v: r["iou"] for v, r in report.items()}
    red = [r["uncovered"] for r in report.values() if "uncovered" in r]
    row = {"budget": budget, "tris": mesh_lint.lint_tris(glb), "iou": sum(ious.values()) / len(ious), "iou_views": ious,
           "uncovered": sum(red) / len(red) if red else 0.0, "sliver_pct": mesh_lint.lint(glb)["sliver_pct"],
           "seconds": round(seconds, 1)}
    (bdir / "budget.json").write_text(json.dumps(row, indent=2))
    (bdir / "review.md").write_text(f"# {args.id} \u2014 run b{budget} (budgets)\n\n- kind: {args.kind}\n"
                                    f"- judge (approved sheet): {args.sheet}\n- built from (image 1): {args.build}\n")
    return row


def budgets_section(args, rows):
    """`## Budgets`: the IoU x tris x slivers table of the ablation, the IoU lost per 100 tris of each
    step, and the knee as the recommended BUDGETS ceiling for the kind."""
    curve = {c[0]: c for c in budget_curve(rows)}
    body = "".join(
        f"| {r['budget']} | {r['tris']} | {r['iou']:.3f} | " + " / ".join(f"{r['iou_views'].get(v, 0):.3f}" for v in BUDGET_VIEWS)
        + f" | {r['uncovered']:.3f} | {r['sliver_pct']} % | {r['seconds']:.0f} s | "
        + ("-" if curve[r["budget"]][4] is None else f"{curve[r['budget']][4]:.4f}") + " |\n"
        for r in sorted(rows, key=lambda r: r["tris"]))
    return ("## Budgets\n\n| budget | tris | mean IoU | " + " / ".join(BUDGET_VIEWS) + " | uncovered | slivers | time | IoU lost per 100 tris vs next |\n"
            f"|---|---|---|---|---|---|---|---|\n{body}\n"
            f"recommended BUDGETS[{args.kind!r}] ceiling (knee, step < {KNEE_SLOPE} IoU per 100 tris): **{knee_of(rows)}** "
            f"(now {BUDGETS[args.kind][1]})\n")


def run_budgets(args, layout):
    """--budgets: the --spec built at every budget (budgets/<B>/, run-shaped, kept), measured, and the
    curve written to review.md and budgets.json. No author, no repair, no stage 2."""
    if not args.spec:
        raise SystemExit("--budgets needs --spec: it ablates a spec that already exists")
    spec = {**parse_spec(args.spec.read_text()), "rig": args.rig}
    rows = [r for b in args.budgets if (r := budget_build(spec, args, b, args.out / "budgets" / str(b)))]
    if not rows:
        raise SystemExit("--budgets: no budget built")
    (args.out / "budgets.json").write_text(json.dumps(rows, indent=2))
    (args.out / "review.md").write_text(
        f"# {args.id} \u2014 run {args.run or args.out.name} ({args.tag})\n\n- kind: {args.kind}\n- spec: {args.spec}\n\n"
        f"{budgets_section(args, rows)}")
    print(f"{args.id}\tbudgets {','.join(str(r['budget']) for r in rows)}\ttris {','.join(str(r['tris']) for r in rows)}\t"
          f"iou {','.join(f'{r['iou']:.3f}' for r in rows)}\tknee {knee_of(rows)}")
    return 0


def final_status(args, verdict, lint_bad):
    """status_of, one level down when the pairwise review lost both axes."""
    status = status_of(verdict, args.summary, lint_bad)
    pw = getattr(args, "pairwise", None)
    return review_pair.demote(status) if pw and review_pair.lost(pw) else status


def identity_line(summary):
    """`Identity: 5/6 - missing: lantern` (PIPELINE 23.L5-6), or nothing when the unit has no checklist."""
    ident = summary.get("identity")
    if not ident:
        return ""
    return f"Identity: {ident['ok']}/{ident['total']}" + (f" - missing: {', '.join(ident['missing'])}" if ident["missing"] else "") + "\n\n"


def sdf_rows(m):
    """Rows of `### Forma` for the shape against the body's SDF (28.L10-6, report only); '' without the field."""
    if not m.get("nd_bands"):
        return ""
    rows = f"| euler (F - 2V + 4; 0 = casca fechada) | {m['euler']} (por componente: {m['euler_components']}) |\n"
    rows += f"| nd faixas 0-20 / 20-60 / 60-100 / 100+ (% das arestas do corpo) | {' / '.join(map(str, m['nd_bands']))} |\n"
    if m["sdf_dev"]:
        d = m["sdf_dev"]
        rows += (f"| sdf_dev media / p95 / max | {d['pct_h']['mean']} / {d['pct_h']['p95']} / {d['pct_h']['max']} % H "
                 f"({d['vox']['mean']} / {d['vox']['p95']} / {d['vox']['max']} voxels) |\n"
                 f"| normal_consistency (|n . grad d|) | {m['normal_consistency']} |\n")
    return rows


def form_block(m):
    """`### Forma` (PIPELINE 24.L6-6): normal_diff mean / p90 with its 6-band histogram, fairness, body
    components, slivers, and the form cost the variant and fit rankings pay."""
    nd = m["normal_diff"]
    bands = ["0-5", "5-15", "15-30", "30-60", "60-100", "100+"]
    return ("### Forma\n\n| medida | valor |\n|---|---|\n"
            f"| normal_diff media / p90 | {nd['mean']} / {nd['p90']} graus |\n"
            f"| normal_diff faixas (graus: % das arestas) | {', '.join(f'{b}: {h}' for b, h in zip(bands, nd['hist']))} |\n"
            f"| fairness (desvio medio de 60 graus) | {m['fairness']} graus |\n"
            f"| componentes do corpo (sem props) | {m['components_body']} |\n"
            f"| slivers | {m['sliver_pct']} % |\n"
            f"| custo de forma | {form_cost(m):.3f} |\n{sdf_rows(m)}\n")


def readiness_section(args, shape, colour, verdict):
    """`## Readiness`: mesh_lint numbers (criterion | value | gate) and the status."""
    glb, textured = lint_target(args, shape, colour)
    if glb is None:
        return f"## Readiness\n\nno GLB built.\n\nstatus: **{final_status(args, verdict, ['build'])}**\n\n"
    m = mesh_lint.lint(glb, sdf=True)
    bad = mesh_lint.failing(m, textured)
    fa, tx = m["face_area"], m["texel"]
    rows = [("file", glb.name, "-"), ("verts / faces", f"{m['verts']} / {m['faces']} (V/F {m['compactness']})", "-"),
            ("nodes / meshes / skins", f"{m['nodes']} / {m['meshes']} / {m['skins']}", "-"),
            ("face area median / p90 / max-over-median", f"{fa['median']:.4f} / {fa['p90']:.4f} / {fa['max_over_median']:.1f}", "-"),
            ("slivers (<10 deg)", f"{m['sliver_pct']} %", "< 5 %"), ("degenerate faces", m["degenerate"], "-"),
            ("flipped faces", m["flipped"], "== 0"), ("boundary / non-manifold edges", f"{m['boundary_edges']} / {m['nonmanifold_edges']}", "-"),
            ("components / body (without props)", f"{m['components']} / {m['components_body']}", "body == 1"), ("materials / images", f"{m['materials']} / {m['images']}", "images == 1" if textured else "-"),
            ("image size", m["image_size"] or "-", "-"), ("unique colours", m["unique_colours"] or "-", "-"),
            ("uv out of range", m["uv_out_of_range"], "== 0" if textured else "-"),
            ("uv overlap / atlas used", f"{m['uv_overlap_pct']} % / {m['atlas_used_pct']} %", "-"),
            ("texel min / max (ratio)", tx and f"{tx['min']:.0f} / {tx['max']:.0f} ({tx['ratio']:.0f})" or "-", "-"),
            ("atlas KB / texels per height", f"{m['atlas_kb'] or '-'} / {m['texel_per_height'] or '-'}", "-"),
            ("engine import", mesh_lint.engine_import(glb), "-"),
            ("pivot min_y / height", f"{m['pivot']['min_y']:.3f} / {m['pivot']['height']:.2f}", "abs(min_y) <= 0.01 H"),
            ("root scale", m["root_scale"], "== 1")]
    body = "".join(f"| {a} | {b} | {c} |\n" for a, b, c in rows + decimate_rows(args, shape))
    return (f"## Readiness\n\n| criterion | value | gate |\n|---|---|---|\n{body}\n"
            f"lint gates failed: {', '.join(bad) or 'none'}\n\n{form_block(m)}{identity_line(args.summary)}"
            f"status: **{final_status(args, verdict, bad)}**\n\n")


# 1-5 per axis, left empty for the vision reviewer (EdgeRunner 2024: Input Consistency,
# Triangle Aesthetic, Overall; MeshGPT 2024 user study: shape x triangulation)
EVALUATION = ("## Avaliação\n\n| eixo | nota (1-5) |\n|---|---|\n| consistência com o sheet | |\n"
              "| estética da triangulação | |\n| qualidade geral | |\n\n")


def judge_verdict(args, verdict):
    """--judge-gate on: a passing verdict becomes CHECK when the paired judge says the run lost form or artist to --pair (3-1 / 4-0)."""
    pw = getattr(args, "pairwise", None)
    return "CHECK" if args.judge_gate == "on" and pw and review_pair.regressed(pw) and verdict in OK_VERDICTS else verdict


def pairwise_line(args):
    pw = getattr(args, "pairwise", None)
    gate = f"{review_pair.gate_line(pw)}\n\n" if pw and args.judge_gate == "on" else ""
    return f"{review_pair.line(pw)}\n\n{gate}" if pw else ""


def write_review(args, shape, colour, verdict):
    """review.md: the run header, one section per stage, readiness, the verdict."""
    (args.out / "review.md").write_text(
        f"# {args.id} \u2014 run {args.run} ({args.tag})\n\n"
        f"- model: {args.model}\n- spec author: {args.tag}\n- kind: {args.kind}\n"
        f"- judge (approved sheet): {args.sheet}\n- built from (image 1): {args.build}\n"
        f"- extra refs: {', '.join(k for k, _ in args.refs) or '-'}\n\n"
        f"{EVALUATION}{timing_section(args)}{fewshot_section(args)}{variants_section(args)}"
        f"{massing_section(args)}{guard_section(args)}{dsl_section(args)}{stage1_section(args, shape)}{stage2_section(args, shape, colour)}{infra_section(args)}{loop_stage.table(args.loop_report)}\n"
        f"{readiness_section(args, shape, colour, verdict)}"
        f"verdict: **{verdict}**\n\n{pairwise_line(args)}"
        f"artifacts: spec.json, clay.glb, views/{args.id}/clay-<view>.png, compare.png (vs the "
        f"approved sheet; wire and uv columns), compare-hard.png (vs the hard sheet), silhouette.json; stage 2: "
        f"model.glb, turntable.gif\n")
    # the review sheets read review.md (header, stage verdicts) and the run's files, so they
    # come last; compare-hard: the same renders against the faceted drawing the model was
    # built from, where what the silhouette cannot see (a chest disc, a hood) shows up
    tool("make_compare.py", "--run", args.out, "--against", "approved", "--out", args.out / "compare.png")
    if args.build != args.sheet:
        tool("make_compare.py", "--run", args.out, "--against", "hard", "--out", args.out / "compare-hard.png")


if __name__ == "__main__":
    sys.exit(main())
