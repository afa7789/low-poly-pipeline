# Model-sheet pipeline — how to build the prompt and how to call the model

Verified 2026-10-18 against `https://api.ppq.ai`. No FLUX 3 Klein on this gateway: the flux
models served are `flux-2-pro`, `flux-2-flex`, `flux-kontext-pro/max`, `flux-pro`, `flux-2-pro-i2i`
(`GET /v1/models?type=image`). **Default model: `nano-banana-2-1`** — the only one tested that
obeys the five-panel layout and the viewpoint of each panel.

| model | list price | verdict on a 5-panel sheet |
|---|---|---|
| `nano-banana-2-1` | $0.046 | **use this.** Correct 3+2 layout, distinct viewpoints, correct palette |
| `krea-2-turbo` | $0.013 | silhouette-only sheet with a real cast shadow; no colour read |
| `flux-2-pro` | $0.029 | ignores the panel wording, repeats one viewpoint |
| `gpt-image-2` / `2.5-flare` | $0.012 / $0.010 | obeyed the layout, over-detailed for low poly |
| `flux-kontext-pro`, `flux-2-pro-i2i` | — | broken on this gateway (502 `Provider returned no result URLs`, 400 schema) |

All 15 nano-banana calls returned `cost: 0` although the endpoint lists $0.046. Check the ppq
statement before running the remaining 162 units.

## 1. Call

```bash
cd artifacts/model-sheets
python3 unit_facts.py n01N                 # facts for the prompt, no API call
python3 generate.py prompts/n01N/unit.txt --id n01N --out refs/n01N
```

`generate.py` posts `{"model", "prompt", "aspect_ratio": "1:1", "resolution": "2K", "n": 1}` to
`/v1/images/generations`, downloads the returned URL and writes `<out>/<name>.jpg`. Key comes from
`$PPQ_API_KEY`, else `provider.ppq.options.apiKey` in `~/.config/opencode/opencode.json`.
`--dry-run` prints the payload without spending. One 2K sheet per unit; never write both a jpg and
a png of the same sheet.

## 2. Prompt anatomy

Two templates, filled by hand from `unit_facts.py` output:

- `draft2/prompts/00-template-unit.txt` — five panels: top row front / left profile / back,
  bottom row top-down / bottom-up.
- `draft2/prompts/00-template-building.txt` — five panels: top row front / left / back elevation,
  bottom row right elevation / roof plan. No bottom-up for a building.

Blocks, in order:

| block | content | source |
|---|---|---|
| 1 | canvas, flat-art disclaimer, id + race + unit name, the panel layout sentence | template |
| 2 | one `Panel N` line per view: viewpoint **and what is visible in that view** | written per unit — never leave the viewpoint bare |
| 3 | one figure per panel, same proportions/props/height/ground line, squared-on projection | template |
| 4 | style budget: heavy line, few big blocks, no small hardware, readable at 32×32 | template |
| 5 | `<Race> <Unit>: <silhouette ≤20 words>; props: <≤4, largest crudest shape>` | card, "Low-poly redesign (target)" |
| 6 | palette as a **suggestion** (dominant / sub-accent / one warm accent), never forced per unit | art bible §1.4 via `unit_facts.py` |
| 7 | `Face:` — one of: hidden by hood/respirator, no face at all, or visible-because-it-is-the-message | card + art bible §5 |
| 8 | `Weapon match:` | compendium `stats.range` |
| 9 | `Rank in its chain:` | compendium `predecessorId` + the sibling's card |
| 10 | closing line: panels otherwise empty, no text, no labels, no frame, no shadow | template |

Mandatory lines 8 and 9, verbatim shape:

```
Weapon match: this unit attacks at range <N — write "melee" when stats.range is null>, so its
weapon is <a physical melee weapon with no firearm, bow or launcher | a ranged implement held in
one hand>.
Rank in its chain: this is the <base / upgraded> body of the <family> family. The silhouette event
that marks the upgrade — <the upgrade's cue> — belongs to the higher tier and does not appear here.
Compared with <sibling>, this body is the <simpler | heavier> one: <mass / event delta>.
```

`{blocks}` in block 3 names the body's main masses for its rig family, so a non-biped
sheet is never asked for arms: biped "head, torso, two arms, two legs"; quadruped "head,
torso, four legs, tail"; spider "head, body, eight legs"; serpent "head and a long
segmented body"; vehicle "hull, turret or cab, wheels or tracks".

### 2.1 RTS view, after the sheet is approved

One image-to-image call per unit or building draws the same design from the gameplay
camera; the pipeline measures its angle (`views.RTS`) and refines against it:

```bash
cd artifacts/model-sheets
python3 generate.py draft2/prompts/00-template-rts.txt --image draft2/<id>.jpg \
  --out draft2 --name <id>-rts --resolution 1K                 # unit
python3 generate.py draft2/prompts/00-template-rts-building.txt --image draft2/<id>.jpg \
  --out draft2 --name <id>-rts --resolution 1K                 # building
```

The file must sit next to the sheet as `<sheet>-rts.jpg`; split, silhouette, compare and
`--passes rts` pick it up from there.

## 3. Failure log — what went wrong and the fix that worked

| symptom | cause | fix |
|---|---|---|
| spider read as "a plot of land with weeds" | nothing asserted the body was **carried above the ground**; legs came out thin | state the spatial relation ("clear daylight under the body"), and the card's own rule (no thin legs in this race) |
| ogre read as a generic brute, no species cue | the genus was never **proved** by a trait; the card's rail-company mark had been cut with the small props | name the genus plus one proving trait (two lower tusks) and keep one large painted marking |
| building looked like a plain box, off-theme | the v1 template forbade exactly the race vocabulary ("no rivet rows, no signage, at most two add-ons") | require the race's mandatory markers: riveted plate seams, a stencilled band/number, a smoke plume, a rail or track at the foot, one oil drum or pump, knee-high mud |
| `flux-2-pro` repeated the same viewpoint five times | it does not honour Klein's `front[80,40,560,340]` box syntax | plain `Panel N` sentences; do not use the box syntax on this gateway |
| layout drifted to 2-1-2, or an extra duplicate panel appeared | the model counts panels loosely | add "The layout is exactly three drawings side by side in one top row and exactly two side by side in one bottom row, with empty background between the rows", then count the panels in the result |
| 32×32 gate inconclusive | the crop-and-threshold proof keyed the figure instead of the background on 5 of 6 sheets | gate not finished: needs background keying plus a per-panel split before it is trustworthy |

Root rule: **the model draws what is asserted as physical mass, not what the card knows elsewhere.**
Detail limits do not fix a missing mass — a missing spatial relation does.

## 4. Layout

```
artifacts/model-sheets/
  PIPELINE.md            this file
  unit_facts.py          card + compendium + palette facts for one id (no API call)
  generate.py            prompt file -> jpg via ppq
  refs/                  concept art, keyed by unit id (versioned)
    <id>/
      sheet.jpg          approved 5-view sheet ............................ §16
      sheet-hard.jpg     hard-edged, props in place ....................... §16
      sheet-hard-clean.jpg  hard-edged, empty-handed A-pose, no props .... §16
      sheet-props.jpg    props detached at body scale (props units only) .. §16
      sheet-rts.jpg      RTS gameplay view of the approved sheet .......... §14
      sheet-hard-rts.jpg hard sheet from the 45/45 gameplay camera ....... §16
      refsheet.png       all of the above on one contact sheet (human) .... §16
      concepts/          early concept arts / model comparisons (n01X)
  prompts/               art prompts, keyed by unit id (one folder per id)
    <id>/
      unit.txt           approved sheet prompt
      unit-hard.txt      hard-edged prompt ............................... §16
      unit-hard-clean.txt  A-pose, no-props prompt ....................... §16
      unit-props.txt     detached-props prompt (props units only) ........ §16
    building-<id>.txt    building prompts (no per-id folder)
    BRIEF*.txt           spec-author brief templates carried from drafting
  runs/draft/            build runs, keyed by unit id then run (versioned)
    <id>/<run>/          run = draft name (v1, v2, argon, opus55, v-ref ...)
      spec.json          part spec from the spec author
      model.glb          built mesh
      compare.png        concept vs model overlay (versioned)
      turntable.gif      rotating preview (versioned)
      review.md          gate verdict + per-run metadata
      sil/               silhouette masks + silhouette.json (scratch)
      views/             per-view model renders (scratch)
```

The draft name is the run: `runs/draft/<id>/<run>/`. Concept art and prompts live beside the
runs under `refs/<id>/` and `prompts/<id>/`; both are keyed by unit id, not by run, because the
art is reused across runs. `compare.png`, `turntable.gif`, `refsheet.png`, `silhouette.json`
and `review.md` are committed; `sil/`, `views/`, `passes/`, `argon/` are scratch (see
`artifacts/model-sheets/.gitignore`).
## 5. 3D — Blender stage

Blender 5.2.2 is installed (`/opt/homebrew/bin/blender`); everything below runs headless.

```bash
# built-in spec by id, or any external {"parts": [...]} JSON
blender -b -P tools/blender/build_unit.py  -- n01X artifacts/model-sheets/draft2/glb/n01X.glb
blender -b -P tools/blender/build_unit.py  -- draft3/specs/n01X-5.5.json draft3/n01X-5.5.glb
blender -b -P tools/blender/render_unit.py -- draft3/n01X-5.5.glb /tmp/views
blender -b -P tools/blender/render_anim.py -- draft3/n01X-5.5.glb /tmp/anim walk 20 320
```

`build_unit.py` holds a `SPECS` dict per unit: parts are boxes / cylinders / valve wheels in a
`(right, up, forward)` convention, each bound to one bone of the shared 14-bone humanoid rig.
`bp()`/`bd()` convert to Blender's Z-up axes — **without that conversion the model exports lying
on its back**, because glTF up is +Y while Blender up is +Z. Pieces are joined into one mesh with
material slots (3-5 from the warm palette), rigid-skinned (one bone per piece, weight 1) and given four actions:
`idle`, `walk`, `attack`, `death`.

`render_unit.py` renders front / left / back / top / bottom plus one mid-stride walk frame with the
workbench engine on a #CCCCCC world, so the frames compare directly against the AI sheets.

Engine contract the export must satisfy (`src/render/ModelManifest.hpp`, `tools/model_chart.cpp`,
`scripts/fetch_models.mjs`):

| requirement | value in `n01X.glb` |
|---|---|
| one skin, joints in `skins[0]` order, ≤255 joints | 1 skin, 14 joints |
| `animations[]` order defines `clip_idle/walk/attack/death` | `attack, death, idle, walk` → walk 3, attack 0, death 1, idle 2 |
| renderer scales by `max(h, 0.8w, 0.8d)` | proportions only; authored height 2.7 |
| facing corrected by `yaw_deg` in the TSV | authored facing glTF +Z |
| mesh count / materials | 1 mesh, N primitives, 3-5 palette materials |
| triangle budget | 612 tris built-in spec; 608 with the opus-5.5 spec (card budget 500–650) |

Outstanding wiring, not done yet: copy the GLB to `assets/models/<id>.glb`, add its `.rig` and
`.joints` (produced by `scripts/fetch_models.mjs`, which currently expects a download URL), add the
`data/models.tsv` row, and render it through `model_chart` for the in-engine check.

## 6. Spec authors — which model writes the parts

The mesh is built by `build_unit.py` from a JSON part spec, so a stronger model can author the
spec while the pipeline stays deterministic. Tested 2026-10-19 on `n01X`, same brief
(`draft3/specs/BRIEF.txt`), same sheet, same builder and gates.

**Verdict (decided 2026-10-19): `google/gemini-4-argon` for the whole roster — ~$0.011 per unit,
cheaper than opus-5.5 ($0.048) with a spec that already passes the 400–700 budget.** `claude-opus-5.5`
stays as the quality reference: use it only if a single unit keeps failing the gates after an argon
re-run.

| model | US$/M in · out | cost/unit | parts | tris | mats | smear | JSON | verdict |
|---|---|---|---|---|---|---|---|---|
| `claude-opus-5.5` | 4.22 · 21.10 | $0.0482 | 37 | **608 ✓** | 3 ✓ | **0.06%** | clean | **best artefact**, inside the tri budget |
| `google/gemini-4-argon` | 1 · 5 | **$0.0114** | 40 | 676 | 3 ✓ | 0.10% | clean | **best value**, +4% over budget |
| `openai/gpt-5.4` | 2.64 · 15.83 | $0.0352 | 41 | 1044 | 2 (no flame) | 1.44% | clean | loses the accent, 60% over |
| `anthropic/claude-opus-4.8` | 5.28 · 26.38 | $0.0602 | 38 | 716 | 3 | 0.98% | invalid (bare bone names) | thin figure, floating feet |
| `google/gemini-3.1-pro-preview` | 1 · 6 | $0.0134 | — | — | — | — | truncated | failed |
| `grok-4.6` | 2.11 · 6.33 | $0.0159 | — | — | — | — | empty | failed |
| `moonshotai/kimi-k3` | 3.17 · 15.83 | $0.0361 | — | — | — | — | empty | failed |
| `deepseek/deepseek-v4-pro-0813` | 0.70 · 2.09 | $0.0052 | — | — | — | — | — | no image input (404) |

Costs are list price × the measured payload (1,703 in / 1,943 out tokens); the gateway reported
`cost: 0` for most calls, so reconcile against the ppq statement before a batch run.

Operational rules learned:

- The vision endpoint rejects images over 5 MB: resize the sheet to 1024 px (134 KB) first.
- Validate the spec, never trust it: bone / kind / material in the allowed sets, `parts` arity 6,
  no part below `y = 0`. Repairable sloppiness includes bare identifiers (`[root, ...]`).
- Empty responses are common on strong models (grok, kimi): treat empty as a failure, not a retry
  prompt.
- Two models can draw well and still fail the gates (gpt-5.4 lost the flame accent and doubled the
  budget); the gates, not the render, decide.

## 7. The WC3 read — measured, not assumed

Tested on `n01X` (`draft5/compare/n01X-antes.gif` vs `n01X-depois.gif`): chamfering the big masses
(1 segment, +32 tris each) with 48° smoothing **made it read worse** — the plates inflate and lose
the hard silhouette. Conclusion: at 400–700 tris the WC3 look does not come from smoothing or
chamfers; it comes from painted shading (light and shadow painted into the model or its texture) and
from fewer, larger parts. Chamfering is therefore opt-in (`build_unit.py ... 700` as a third
argument) and off by default.

## 8. Triangle budgets (Warcraft III SD standard)

Every unit and building description follows the original WC3 standard-definition budget for its
class, scaled by importance. `check_gates.py --kind <class>` enforces it.

| class | tris | applies to |
|---|---|---|
| mass unit | **400–700** | every non-hero unit (Footman, Ogre, Spider, Ent, Golem…) |
| hero | **900–1600** | legendary / hero units |
| standard building | **600–800** | production, tower, utility buildings |
| town hall / large structure | **2000–3000** | castle, main hall, wonders |

A row also fails when the model is not one skin with 3-5 palette materials and four clips. Measured on
`draft4` (6 units × 2 spec authors): **12 of 12 inside 400–700**, 452–664 tris, all 3 materials,
1 skin, 4 clips.

## 9. Batch runner and delegation

```bash
# one unit, end to end: sheet -> spec -> glb -> gates -> gif
python3 tools/blender/spec_pipeline.py --id n01X --race Mech --name "Iron Golem" \
    --sheet artifacts/model-sheets/draft2/n01X.jpg \
    --model google/gemini-4-argon --tag argon --height 2.7 --kind mass

# gate a whole folder
python3 tools/blender/check_gates.py artifacts/model-sheets/draft4/glb --kind mass
```

`spec_pipeline.py` prints one gate line per unit and exits non-zero on failure, so it is safe to
loop or to hand to a subagent. A subagent needs only: the id, race, name, sheet path, model id,
`--tag` (one folder per author) and `--kind` for the budget. It must not edit the design cards or
the animation; those stay with the parent.

## 10. Outstanding review work

- `audit/weapon-role-audit.md` — 5 melee units whose props name a ranged weapon (`hfoo` fixed in
  the prompt; `n03G` rifle at range 60, `h06U` carbine at range 100 are errors **in the design
  cards**; `n002` harpoon and `z003` flamethrower are short-range weapons used at melee range).
  64 ranged units name no ranged weapon and need a manual read.
- `audit/unit-chains.md` — 71 unit chains, 17 three-step. Generate base first, upgrade second, so
  the rank line has something to be compared against.
- 156 units still have no prompt file.


## 11. What classic WC3 actually does (measured + sourced)

Measured from the models in `~/Documents` with `tools/blender/mdx_inspect.py`:

| model | vertices | triangles | geosets | texture |
|---|---|---|---|---|
| Footman (custom, RoC style) | 154 | 141 | 1 | `Textures\Footman.blp` |
| Ballista (RoC) | 431 | 301 | 1 | `Textures\Ballista.blp` |
| Knight (custom, RoC style) | 38 | 26 | 1 | `Textures\Knight.blp` |

So the classic budget is **140–300 tris**, one geoset, one small .blp per unit. The detail
(gold trim, rivets, folds, metal highlights) is painted, not modelled.

Confirmed by a WC3 modeller (r/wc3 thread) and the `lowpoly-style` skill:

- "very low poly count, go for triangles … there's no shading, just a base texture" — the mesh
  carries no vertex shading; the atlas carries the light and shadow.
- parts **are** placed separately (ghoul claws, back spikes) and rigid-bound; they do not need to
  be one welded shell.
- fangs, fur and cloth are **planes with alpha**, not geometry; hands have no fingers.
- texture 64–256 px is normal; anything duplicable is mirrored to save atlas space.
- `lowpoly-style`: "texture carries detail, not geometry", no micro-bevels (0 or 1 segment max),
  flat shading or auto-smooth ≥60°, merge coplanar faces, vertex colours preferred for variation.

Consequence for this pipeline: **the missing stage is the atlas, not more geometry.** A voxel-remesh
"fuse" pass was prototyped (`build_unit.py ... fuse`) and rejected — it produced 2,030 tris and WC3
does not weld its parts. Chamfering was rejected for the same reason. The next stage is a 256–512 px
hand-painted-style atlas per unit (AI-generated and box-projected, or baked from vertex colours),
and the silhouette test is a solid-colour render at gameplay distance.


### The Blizzard house style (Samwise Didier, quoted in the WC3 retrospective)

- **14,000 polygons on screen for the whole scene** — terrain, buildings, effects and every active
  unit; an individual character is usually **under 300 to 700**.
- **"Chunkifying"**: smooth curves replaced by pronounced angles, massive weapons, bloated hands and
  shoulders, exaggerated proportions so an Orc Grunt reads apart from a Tauren at RTS distance.
  Parchment was modelled thick like cardboard with accentuated corners, so primitive lighting
  catches the edge — the same rule applies to every plate and cape.
- **The texture carries the depth**: shadows, highlights, gradients and AO were painted by hand in
  Photoshop; rivets and creases were painted, never modelled, because the engine had no normal maps
  or dynamic AO.
- **Colour organisation**: every unit reserves one zone for the player's team colour, and major
  props are angled outward so the profile survives when units overlap.

Our engine has a per-model `tint` (RGB multiplier) but no per-material tint, so the team-colour zone
needs a decision: a fourth material slot named `team`, or the tint applied to the whole model.


### Iteration log — what actually worked on n01X (fewest passes, fewest tris)

| recipe | tris | verdict |
|---|---|---|
| box parts, flat colours | 612 | Lego: right angles read as blocks |
| 6-sided prisms, separate parts | 684 | limbs read as tubes; still assembled |
| **6 sides on limbs + 8 on the largest masses, separate parts, painted tiles** | **716** | **best: shaped, rigid-bound, atlas on** |
| subdiv (1) + decimate ("morph") | 1240 | rejected: each part shrinks inward, parts detach, tris explode |
| voxel fuse 0.045 + decimate | 656 | rejected: one blob, colour blocking and detail lost |

Rules that came out of it:

1. **Shaping belongs in the cage, not in a post pass.** Taper the prism radii and pick the side
   count per mass (6 for limbs, 8 for the torso/shoulders). Subdividing afterwards only shrinks
   and separates what you already placed.
2. **Do not weld the body.** Classic WC3 keeps parts separate and rigid-bound; the union reads as
   one silhouette once the texture is on. The skeleton (14 bones) carries the motion, not a smooth
   skin.
3. **The atlas is the last 50% of the look.** Without it the same mesh reads as cardboard.
4. **Budget check after every pass**, not at the end: `check_gates.py` on the folder.


## 12. First-attempt protocol (what ten iterations taught, in the order to apply it)

The point of this section is that none of it should be discovered again by iterating.

### 12.1 Measure the sheet before writing any prompt

Take five numbers off the front view, as a fraction of the unit height H:

| measure | sheet (n01X) | how to read it |
|---|---|---|
| shoulder span | 0.62 H | outer edge of the pauldrons |
| hip height | 0.47 H | where the legs meet the pelvis |
| head element | 0.19 H diameter | the valve wheel |
| wrist height | 0.39 H | where the gauntlet starts |
| foot length | 0.23 H | heel to toe, in profile |

These five numbers replaced every adjective in the brief. The prompt says `shoulder 0.62 H`,
never "chunky shoulders".

### 12.2 Placement is code, never a coordinate from the model

`resolve_skeleton()` takes `{bone, radius, material}` and derives position (bone midpoint),
length (1.15 x bone length) and overlap. The LLM cannot float a limb because it never writes a
number for a position. Rig families (`rig_families.py`) cover biped, quadruped, spider, serpent and
vehicle, so the same rule works for the whole roster.

### 12.3 Run the preflight before building

`python3 tools/blender/preflight.py <spec> mass` prints seven rules and exits non-zero. On our
4.6 spec it reports 3/7 pass and names the defects that took ten review rounds to find:

```
budget        FAIL  732 tris vs 416-700
shoulderness  FAIL  0.83 (sheet 0.62)
head_sunk     FAIL  head 2.66 vs shoulder 2.20
overlap       FAIL  detached: forearm.L, forearm.R, foot.L, foot.R
```

### 12.4 Gates, in the order that they save the most time

1. `preflight.py` — proportions, coverage, overlap, budget. Costs 0.1 s.
2. `check_gates.py` — tris by class, 3-5 materials, 1 skin, 4 clips, on the built GLB.
3. **Five-view comparison against the sheet, never a 3/4 render.** Measured: the same model
   scores 5.5 on a three-quarter view and 4.0 on the five-view comparison, because the profile
   collapse is invisible from 3/4. The comparison is `render_unit.py` + a 3+2 montage with the
   concept sheet above it.
4. Claude review only after 1-3 pass, and always with both sheets side by side.

### 12.5 What still has to change to clear 5.5

Geometry has plateaued: ten dial iterations moved Claude's score 4.8 to 5.5 and no further. The
remaining gap is the surface. The atlas must be built **from the concept sheet itself** — crop the
chest, pauldron, gauntlet, boot and wheel regions of the approved art into a 512 atlas and box-map
each part into its crop. That transports the painted rivets, crevices and rim light instead of
inventing a gradient, which is what the classic WC3 texture does.

Hard-surface beats skin for machines, measured on the same unit: stacked parts 7.0, skeleton-placed
parts 5.5, skin body 1.5, skin-plus-plates 3.5. Do not re-litigate that.

## 13. Pipeline v2 — measured on draft11 (2026-10-19)

The v9 review (4.5/10, saved in `draft9/claude-review/review-claude.md`) split the gap
as 50% geometry/pose, 30% proportion, 20% surface and named what the pipeline could
not express. Draft11 applies the pipeline-side fixes, not per-unit hand edits.

### 13.1 Spec DSL v2

| addition | shape | why |
|---|---|---|
| `frustum` | box with `top: [sx, sz]` and `shift: [dx, dz]` | wedge boots, trapezoid pelvis, stepped fists; 12 tris |
| `ring` | flat annulus, `spokes`, `hub`, `axis: up/fwd/side`, `tilt`, `spin` | the valve-wheel halo; 10 sides + 3 spokes + hub = 144 tris |
| `from` / `to` | any box/prism/frustum: builder solves midpoint, length (`fit`) and orientation | limb angles are code, not an LLM-supplied coordinate |
| `spin`, `scale` | prism axial rotation and elliptical scale | octagonal chest, non-circular torso |
| warm palette | `iron #8A8780`, `darkiron #5A4A3A`, `brass #B08A4A`, `lamp #FFD24A` | concept has four colour zones, not three; the old blue steel was wrong |
| linear colour | sRGB palette converted before Blender/glTF | fixes the chalk-white renders; glTF baseColorFactor is linear |

`rest_pose` is supported (`{bone: [rx, ry, rz]}` rotates the bone rest around its head)
but draft11 authors the splay with `from`/`to` instead.

### 13.2 New gates

`preflight.py` now has 13 rules: budget, 3-5 palette slots, bone coverage, shoulder
span 0.55-0.70 H, fist span 0.78-0.95 H, stance 0.45-0.62 H, foot mass, shin width,
head top (0.25 H over shoulders when the head carries a wheel), wheel axis/tilt,
ornament tri share <=22%, ground, overlap. It runs before Blender in
`spec_pipeline.py`.

`silhouette.py` keys the concept sheet background, splits the 3+2 panels on the empty
bands, renders five ortho masks from the GLB, normalizes both by body height and
reports IoU, width-profile L1 and 32x32 IoU. Gates: front >=0.75, left >=0.65.
Top and bottom are reported but not gated: the concept's bottom panel is a low-angle
perspective and even the "top" panel is not a true ortho, so those two IoUs are noise
(width-profile L1 1.3 at the end versus 0.04 on front). `silhouette.py --measure`
prints the code-derived landmark table that is now injected into the spec prompt.

`render_unit.py` adds a 55-degree WC3 gameplay render and uses the Standard view
transform with the linear palette. `make_compare.py` builds the scale-normalized
review sheet (concept/model at the same body height, plus a 32 px row); the old
compare sheet scaled each half as a whole and hid the proportion error.

### 13.3 Draft11 result — n01X

```
preflight 13/13 PASS
GLB       696 tris · 4 materials · 1 skin · 4 clips   PASS
silhouette front 0.771 · left 0.694   (gates 0.75 / 0.65)
          32px   front 0.788
measured  shoulder 0.635 H · fist 0.863 H · stance 0.506 H
          body depth 0.222 H · foot length 0.228 H
```

Baseline v9 silhouette was front 0.551 / left 0.627 / top 0.715 (top passed because
the body dominates the mask; the spec rule `wheel_axis` is what blocks the edge-on
wheel). Draft4 `opus55-n01X.glb`, the best earlier artefact, measures 0.774 / 0.787 /
0.693, so the new gate is calibrated around a model that was already accepted.

What raised front IoU from 0.551 to 0.771, in order: wheel lying near-horizontal
(axis up, tilt 25) with three spokes; torso top raised and neck shortened; chest
narrowed to its real 0.31 H body width (the first pass filled the silhouette with a
0.55 H chest and oversize fists, which passed the gate but was the wrong mass split);
upper arms tucked under the pads and bowing out to the fists; fists moved down to
knee height; boots enlarged to 0.22 H tall, 0.23 H long; stance widened to 0.51 H.

The silhouette gate is a shape check, not a mass check: front IoU 0.755 coexisted
with a torso almost twice the concept width, and the first correction moved the
excess into the pads and pelvis without moving IoU. Final pass re-measured those
parts against the concept: pads 0.40 x 0.50 x 0.36 m, belt 0.27 H, forearm 0.176 H,
fist 0.176 H, legs straightened, palette darkened to the sampled #6E6C68 / #4E4034 /
#A5814A. Front IoU held at 0.771, left moved 0.721 -> 0.694 (still passing) and the
32 px front rose to 0.788. That is why the next gate must be per-material-class IoU
plus per-part width/depth landmarks; the atlas waits for that.

The Claude follow-up reviews are `draft11/claude-review/review-claude-v11.md`
(5.0 on the first pass), `draft11/review-final/review-final.md` (5.5 after the
torso fix) and `draft11/review-final/review-final-check.md` (6.0 after the part-size
and palette corrections, +1.5 over v9).

The closing check names the next pipeline step, and it is not the atlas: a **closed-loop
part-box gate**. Render each part with a flat ID colour, segment the concept by
material class plus landmark bands, compare each part's centre and W/H/D against the
concept at +/-15%, and feed the failing numbers back into the spec prompt. That is the
only way to stop mass migration between parts (the reason front IoU stayed at 0.771
while the torso was halved). The current silhouette and preflight gates can pass
floating pads and a wide pelvis because both only see envelopes. Build that gate
before any UV/atlas work; a 512 atlas on this geometry is worth about +0.5 (6.0 ->
6.5), while the part gate plus lint is worth about +1.5 and keeps its value when the
atlas lands.

### 13.4 Commands

```bash
# spec -> preflight -> GLB -> gates -> render -> compare -> silhouette -> GIF
python3 tools/blender/spec_pipeline.py --id n01X --race Mech --name "Iron Golem" \
  --sheet artifacts/model-sheets/draft2/n01X.jpg \
  --model google/gemini-4-argon --tag argon --height 2.7 --kind mass \
  --out artifacts/model-sheets/draft12

# independent gates on an existing GLB
python3 tools/blender/preflight.py  artifacts/model-sheets/draft11/spec-n01X-v11.json mass
python3 tools/blender/check_gates.py artifacts/model-sheets/draft11 --kind mass
python3 tools/blender/silhouette.py artifacts/model-sheets/draft2/n01X.jpg \
  artifacts/model-sheets/draft11/n01X-v11.glb artifacts/model-sheets/draft11/sil
```

## 14. Per-view passes, calibrated cameras, RTS view (2026-10-19)

- `split_sheet.py` cuts the 3+2 sheet into `<id>-front/left/back/top/bottom.png`
  (plus `<id>-rts.png` when the RTS concept exists).
- `spec_pipeline.py --passes rts,left,back,front`: after the sheet spec, each pass
  sends the concept view + the model render of that view + the silhouette overlay
  and gets back a patch of at most 6 parts. A patch is kept only if its own view's
  IoU rises, no gated view drops more than 0.01 and the preflight does not break.
  Pass 0 repairs a preflight failure (up to 2 patches of 12 parts). `--spec` resumes
  from an approved spec.
- Never stop on a failed gate: the GLB, compare and GIF always come out; gates set
  the verdict (PASS/CHECK) and the exit code.
- Procedural painted texture (`texturize`) is the default; `--flat` opts out. Do not
  project the concept onto the model: it copies the sheet background.
- Top/bottom panels are drawn tilted toward the front. `silhouette.py` sweeps the
  camera tilt (`views.TILTS`) and keeps the best match; the colour review renders at
  that tilt. Vertical flips are no longer tried (a flipped back-side view used to win).
- RTS view: `generate.py <template-rts> --image <sheet>` draws the same unit from the
  gameplay camera with `nano-banana-2-1-edit` (saved as `<sheet>-rts.jpg`).
  `silhouette.py` sweeps elevation x azimuth (`views.RTS`); the `wc3` render uses that
  camera, orthographic like the sweep (the old close perspective looked steeper than
  the matched angle). Elevation = height of the camera above the ground, azimuth = turn
  around the unit from the front; n01X asked 45/45, the drawing measures 35/+45. The
  match is never mirrored: with a mirror allowed, a symmetric body scored the same from
  both sides and the review rendered the wrong side (an earlier 35/-45 here was that).
- Commit per draft only `specs/*.json` and `glb/*.glb`. `passes/`, `sil/`, `views/` and
  every PNG/GIF (compare, turntable) are local-only (`artifacts/model-sheets/.gitignore`).

| n01X | front | left | back | top | bottom | rts |
|---|---|---|---|---|---|---|
| v11 (manual) | 0.771 | 0.694 | — | — | — | — |
| v12 sheet + passes | 0.829 | 0.829 | 0.823 | 0.782 @10° | 0.791 @20° | 0.778 @35°/−45° |
| v13 = v12 + rts,left,back | **0.857** | 0.832 | **0.854** | 0.785 | 0.804 | 0.783 |

v13: only the back pass was accepted (it closed the thigh-pelvis gap); the rts pass
did not raise the rts IoU and the left pass broke the preflight.

## 15. Rig families, surfaces, palette, decals, buildings (2026-10-19)

### 15.1 Rig families (`tools/blender/rig_families.py`)

A spec names its skeleton with `"rig"`; the builder, the preflight and the brief all
read the same table. Families are composed from parts (quadruped body, wings, rider,
chains), and the four clips are derived from the bone names: `leg<N>` walk (four legs
on a spine trot, rings alternate), `wing<N>` flap, tails/necks/tentacles wave, `wheel<N>`
spin, `HOVER` families bob on the root. Families with biped limbs (`arm.L`, `thigh.L`)
get the hand-keyed biped clips merged under the derived ones. `building` is static.

| family | body plan | example units (cards) |
|---|---|---|
| biped | the n01X skeleton | 88 cards |
| quadruped / spider / serpent / vehicle | as before; the spider body now lies along z, abdomen optional | 12 / 3 / 0 / 7 |
| drake | quadruped body + neck + jaw + tail + wings | n001, n01D, n01B, n02A, n010 |
| harpy | biped + wings | n034, n02W, n032, n008 |
| wyrm | serpent + wings | n00H, e000 |
| mounted / mounted_flyer | quadruped or drake + rider.* | h03B, h03C, o006, o008, o00B / h016, o009 |
| bird / bird_rider | two legs + wings + neck + tail, no arms (also wyverns) | u000 / n01Y |
| naga | torso on a tail chain | n002, n00X, n00S |
| centaur | quadruped + upright torso | n016 |
| wraith | torso on a base, no legs, floats | 13 cards (e00A, u001, h03R ...) |
| pod | floating body + stalk + 3 tendrils | n019, n01A, h06B |
| shard | rigid abstract flyer | o00C, o00D, o00E |
| ray | flat body + wings + stinger tail | n03U |
| crawler / crustacean | 4-leg ring / 6 legs + claws + tail | n01U / n00W |
| tracked / walker / aircraft | tracks + tools / mech legs + barrels / gasbag + gondola | h06S, n01T, h06U / n02J / h06R, h06Q, h07S |
| sled / hydra / crew | bending legless body / + 3 necks / weapon + fused crew legs | n01E, n01F / n01P / hmtm |
| building | static: everything on body | buildings |

Per-unit props that move (a mast, a second head, a counterweight, a catapult arm) are
`"bones": [[name, parent, head, tail]]` in the spec (max 3) - never a new family.
Two passes over all 167 cards found no squad or beast+cart unit: every multi-figure WC3
unit was redesigned as one composite body (hmtm = `crew`) or split into separate units.

`{blocks}` in the unit sheet template: biped "head, torso, two arms, two legs";
quadruped "head, torso, four legs, tail"; spider "head, body, eight legs"; serpent "head
and a long segmented body"; vehicle "hull, turret or cab, wheels or tracks"; for the
composed families, name the masses of the table above.

### 15.2 Surfaces, palette, decals, glass

- `surfaces.py` paints 14 surfaces: metal (the approved n01X painter, pixel-identical),
  polished, skin, leather, cloth, silk, scales, chitin, wood, stone, fur, plastic, glass,
  glow. The engine draws albedo only, so gloss is painted: a hard highlight on silk,
  plastic, chitin, polished; a broad faint one on skin; none on cloth.
- One atlas per unit: every material slot gets a block, all materials sample one image.
- `"palette": {"slot": {"surface": ..., "color": "#hex", "alpha"?: 0-1}}` in the spec;
  colours come from `silhouette.sheet_colours` (k-means of the sheet's flat tones), so
  each unit is coloured from its own sheet. Old slot names (iron/darkiron/brass/lamp)
  stay valid as metal.
- `"alpha" < 1` with surface `glass` exports `alphaMode BLEND` (gauge glass, flame tongue).
- Decals: opts `{"decal": "eyes2" | "eyes8", "decal_color": "#hex"}` paint eyes on the
  part's front face, in a spare atlas cell - no geometry.

### 15.3 Buildings

`--kind building|large` switches the sheet layout to elevations + roof plan
(`views.LAYOUTS`: front/left/back/right/roof), the rig to `building`, the brief to
`BUILDING_BRIEF`, the budget to 600-800 (preflight and pipeline share `BUDGETS`), and the
gate to 0 animations (the game never animates buildings). Passes may use `right` and
`roof`. The RTS concept is drawn automatically from the sheet when it is missing
(`ensure_rts`, `--no-rts` to skip), for units and buildings.

## 16. Hard variant — two sheets, props both ways (2026-10-19)

The approved sheet draws its masses as curves and puts the weapon in the hand. A modeller
then has to read every curve as a plane, and the arm carrying the weapon is half hidden.
The hard variant redraws the **same design** with every mass rebuilt as flat polygons. It is
produced in two forms, both image-to-image from `<id>.jpg`, plus the detached props:

| file | template | pose | props | use |
|---|---|---|---|---|
| `<id>-hard.jpg` | `00-template-unit-hard.txt` | same as approved | in place, faceted | faithful hard silhouette; source of the hard RTS view |
| `<id>-hard-clean.jpg` | `00-template-unit-hard-clean.txt` | empty-handed A-pose | removed | limb/block read, clean body measures |
| `<id>-props.jpg` | `00-template-props.txt` | — | detached, body scale | prop shapes |
| `<id>-hard-rts.jpg` | `00-template-rts-hard.txt` | 45/45 gameplay camera | in place | gameplay read of the hard design |
| `<id>-refsheet.png` | `ref_sheet.py` | — | — | all of the above on one page, for a human |

Both hard sheets are needed. The **with-props** one is what a modeller axes to: complete
silhouette, nothing missing, every prop faceted in the place it is worn or held. The **clean**
one is what shows where the arms actually are — an A-pose with clear daylight at the armpit
and mitt hands. Dropping the props from the hard sheet alone loses the pack and the weapon
from the silhouette, and a detached props sheet fixes the shape question but not the
placement one.

```bash
cd artifacts/model-sheets
# hard, props in place (style transfer: same sheet, faceted)
python3 generate.py prompts/hfoo/unit-hfoo-hard.txt --id hfoo --image refs/hfoo/sheet.jpg --out refs/hfoo
# hard, empty-handed A-pose, no props
python3 generate.py prompts/hfoo/unit-hfoo-hard-clean.txt --id hfoo --image refs/hfoo/sheet.jpg --out refs/hfoo
# props detached, same scale
python3 generate.py prompts/hfoo/unit-hfoo-props.txt --id hfoo --image refs/hfoo/sheet.jpg --out refs/hfoo
# the hard RTS view is drawn automatically by spec_pipeline.py --hard; by hand:
python3 generate.py prompts/hfoo/00-template-rts-hard.txt \
    --id hfoo --image refs/hfoo/sheet-hard.jpg --out refs/hfoo --name sheet-hard-rts --resolution 1K
# one contact sheet for a human
python3 tools/blender/ref_sheet.py refs/hfoo/sheet.jpg refs/hfoo/refsheet.png
```

`00-template-unit-hard.txt` is a pure style transfer: it asks for the identical sheet —
same panels, pose, props, colours — and changes only how the forms are built, so the only
per-unit inputs are `{keep}` (the identity parts) and `{facets}` (one polygon per mass).
`00-template-unit-hard-clean.txt` also changes the pose and removes the props, so it carries
`{pose}` per rig family:

| rig | `{pose}` |
|---|---|
| biped | A-pose; arms 45° off the torso, elbow as far from the ribcage as the shoulder is wide; mitt hands; legs 1.5 shoulder-widths |
| quadruped | four legs planted symmetrically, body level and clear of the ground, nothing in the mouth or on the back |
| spider | eight legs splayed in a full circle, body carried high with daylight under it, chelicerae closed |
| serpent | one flat S, head raised, no limbs |
| vehicle | hull level, wheels/tracks straight and symmetric, no stowage |

Units whose "props" are body parts (n01X fists and chest disc, n00U/n01N carved plates,
n01I snag and root claw) get no props file; their hard prompt says so explicitly, and the
with-props sheet is just the faceted approved sheet.

### 16.1 The approved sheet is still the gate

> Superseded for the spec author's input by §16.5: the hard sheet is now image 1 and the
> approved sheet stays out of the prompt; the approved sheet is still the gate.

`--sheet` stays `<id>.jpg`. It is what `measure()`, `sheet_colours()` and the silhouette gate
read, and it is the design contract. Pass the hard sheets **alongside** it:

```bash
python3 tools/blender/spec_pipeline.py --id hfoo --race Human --name Footman \
  --sheet artifacts/model-sheets/refs/hfoo/sheet.jpg \
  --hard  artifacts/model-sheets/refs/hfoo/sheet-hard.jpg \
  --hard-clean artifacts/model-sheets/refs/hfoo/sheet-hard-clean.jpg \
  --props artifacts/model-sheets/refs/hfoo/sheet-props.jpg \
  --model google/gemini-4-argon --tag argon --kind mass \
  --run v1 --out artifacts/model-sheets/runs/draft/hfoo/v1
```

`--hard`, `--hard-clean` and `--props` are resized to 1024 px and appended as images 2, 3 and
4; `with_refs()` adds one line per image to the brief, telling the spec author which
reference answers which question (block shape, limb position, prop shape). The DSL's "each
part must match image 1" rule still points at the approved sheet, so no gate moves.
`--hard` and `--hard-clean` also trigger their `<sheet>-rts.jpg` through `ensure_rts()`,
which picks `00-template-rts-hard.txt` whenever the stem contains `-hard`.

Measured on all seven units in `draft2`, same model (`google/gemini-4-argon`), same brief:
`draft4` = sheet only, `draft16` = sheet + `--hard` + `--hard-clean` + `--props`. Front/left
are the silhouette IoU against the approved sheet; tri counts come from the gate.

| unit | front no-ref -> ref | left no-ref -> ref | tris | mats | view gates |
|---|---|---|---|---|---|
| hfoo | 0.523 -> **0.702** | 0.505 -> 0.540 | 556 | 5 | 0/2 |
| n005 | 0.761 -> 0.720 | 0.581 -> **0.796** | 604 | 5 | 1/2 |
| n00U | 0.604 -> **0.739** | 0.608 -> **0.676** | 548 | 4 | 1/2 |
| n01I | 0.719 -> 0.692 | 0.428 -> **0.574** | 500 | 4 | 0/2 |
| n01N | n/a (no draft4 model) | n/a | 528 | 4 | 0/2 |
| n01X | 0.604 -> **0.793** | 0.735 -> **0.816** | 584 | 4 | **2/2** |
| n02X | 0.711 -> 0.708 | 0.523 -> **0.620** | 640 | 5 | 0/2 |

All seven land inside the 400-700 mass budget with 4-5 materials, 1 skin and 4 clips. The
references raise the cluttered views most (front on hfoo/n00U/n01X, left on n005/n01I/n02X)
and the part count drops (hfoo 34 -> 27) because the faceted sheet reads as fewer, larger
blocks. They do not fix the preflight defects the brief never addressed: every humanoid
still reports `shoulder_span 0.00`, `head_top` ~0.3 m over the allowance and `shin` parts
below y=0; the two spiders fail `ground` on every lower leg. n01N is the outlier: the spec
author drew a body far smaller than the sheet (0.246 front), a model-quality failure, not a
reference-file failure. The references sharpen the read; they do not repair a spec-author
error.

### 16.2 RTS on the concept page?

No — keep the RTS as its own file, and put it on the **contact sheet** instead.
`concept_panels()` splits a sheet on its 3+2 empty bands and the gates expect exactly five
panels; a sixth RTS panel would be read as part of the bottom row and corrupt the top/bottom
masks. `split_sheet.py`, `silhouette.py` and the per-view passes all assume one projection
per cell as well. `ref_sheet.py` gives the human (or a reviewer) the single page without
touching anything the code reads.

### 16.3 Failure log

| symptom | cause | fix |
|---|---|---|
| first hard sheet was a different character (fedora brim, blue pauldrons, shin plates that do not exist) | it was text-to-image from the card, so it obeyed the style rules and invented the design | **a variant is an edit pass**: `generate.py --image <id>.jpg`, open with "redraw that identical sheet", list the identity parts in `{keep}`, and forbid any part not already drawn |
| props vanished from the hard sheet | the prompt asked for an empty-handed A-pose *and* no props, and the spec author faithfully followed | keep two sheets: `-hard` (props in place) and `-hard-clean` (A-pose, no props); the props file alone does not tell the model where they attach |
| hands came out with five slender fingers | "block hand" is read as a style, not as one shape | say fingerless mitt: one solid slab for all four fingers plus one thumb block, no line between digits; on units whose approved sheet has fingers, say the mitt replaces them |
| arms stayed near the body | a 45° angle is not a spatial constraint the model can check | tie the pose to a distance: "the elbow sits as far from the ribcage as the shoulder is wide, with daylight between the whole arm and the body" |
| bottom-up panel reads as a cut-open body | the sheet draws top/bottom tilted toward the front (§14) | accepted: that panel is for sole and palm read, not for silhouette gating |

### 16.4 What the batch produced

Seven units with an approved sheet in `draft2`; every one now has `<id>-hard.jpg`,
`<id>-hard-clean.jpg`, `<id>-hard-rts.jpg` and `<id>-refsheet.png`. Detached props exist for
the three units that carry them — hfoo (pike, pack, lantern), n005 (tank, vaporiser, lantern),
n02X (club). n00U, n01N, n01I and n01X have no detached props because their "props" are body
parts (shell plates, snag, root claw, piston fists, chest disc).

The two buildings in `draft2` (`h05X`, `h09B`) were left alone: the A-pose and the props rules
do not apply to a building, and their elevation sheets are already drawn as flat blockouts.
A `building-hard` variant would be a separate template if it is ever wanted.

### 16.5 Roles: the hard sheet builds, the approved sheet judges (2026-10-20)

| image | who reads it | for what |
|---|---|---|
| `refs/<id>/hard.jpg` | spec author, **image 1** | the faces to build; `measure()` and `sheet_colours()` read it too, so the numbers match the picture |
| `refs/<id>/hard-clean.jpg`, `props.jpg` | spec author, extra images | limb positions; props whole and at scale (skipped when the file does not exist) |
| `refs/<id>/sheet.jpg` | silhouette gate + human review | the design contract: the verdict, `compare.png` |

- Refinement passes measure against the hard sheet (an outline a low-poly model can reach);
  the verdict measures against the approved sheet, so a hard redraw that drifted cannot
  pass its own error. `runs/<id>/<run>/silhouette.json` holds both (`approved`, `hard`) plus
  the drift; `review.md` lists them.
- **Drift check before anything is built** (`silhouette.sheet_drift`): IoU of the hard sheet
  against the approved one on front/left/back; below `DRIFT_MIN` 0.90 the run prints
  "regenerate refs/<id>/hard.jpg" and goes on (never fatal). Calibrated on the 7 units:
  0.90-0.98, with n01N left 0.76 and n01I left 0.88 under the line. The RTS pair is reported
  only: two independent draws differ in camera (0.49-0.89), not in design.
- No hard sheet: the approved sheet is image 1, as before. `--with-sheet` also sends the
  approved sheet as an extra image (the "both" variant), for an A/B against the default -
  unmeasured so far; the expectation is that a near-duplicate image with different edges
  makes the spec author average the two.
- `rts_path()` is `<stem>-rts.jpg` next to the sheet (`sheet.jpg -> sheet-rts.jpg`,
  `sheet-hard.jpg -> sheet-hard-rts.jpg`). `ensure_rts()` reads the RTS templates from
  `TEMPLATES` in spec_pipeline.py (`prompts/00-template-*.txt`).


### 16.6 Landmarks from the unit's own sheet, 3-8 materials, ground by construction (2026-10-20)

- **Biped landmarks come from the unit's approved sheet.** The preflight used to hold every
  biped to n01X's numbers (shoulders 0.55-0.70 H, fists 0.78-0.95 H, stance 0.45-0.62 H), so
  every humanoid failed and nobody could tell a wide Footman from a right one. Now
  `preflight.py <spec> <kind> <sheet>` measures the spec in the same height bands
  `silhouette.measure` reads on the sheet (shoulders 10-30% from the top, fists 60-80%,
  stance the bottom 5%) and asks for +/-15% of that sheet; foot length >= 0.8 x the sheet's;
  the head may rise as far over the shoulders as the sheet's shoulder line sits below its
  top. Without a sheet it falls back to the n01X numbers. Calibration: n01X v1 and n00U v1
  are within 9% of their sheets; every hfoo run so far is 30-53% too wide at the shoulders
  (sheet 0.46 H, models 0.60-0.70 H) - that is the "not there yet" on the other units.
- **3 to 8 material slots** (`preflight.MATERIAL_SLOTS`, shared by the pipeline gate and
  `check_gates.py`): the atlas packs every slot into one image, so more slots cost no texture.
- **Ground by construction:** `preflight.ground_fix` lifts any part whose box dips below
  y = 0 by exactly its dip, after every parse and every patch; the shins that kept failing
  `ground` no longer depend on the spec author.
- `--image1 hard|sheet` picks what the spec author builds from (default hard, §16.5);
  `sheet` is the §16.1 arrangement, approved sheet first with the hard sheet as an extra.
- **The repair pass runs by default** (`--no-repair` to skip): preflight failures, now with
  the sheet's own targets, go back to the spec author as a patch even without `--passes`.
  hfoo `abR1`: shoulders 0.66 -> 0.54 -> 0.51 (sheet 0.46), fists 0.71 -> 0.56, stance
  0.49 -> 0.41; the first humanoid to pass 12/12, front 0.63 against the approved sheet.
- A/B on hfoo, no repair (runs/draft/hfoo/ab*): hard as image 1 front 0.50/0.62/0.54, left
  0.57/0.56/0.54; approved as image 1 front 0.58/0.59, left 0.53/0.55. Within run-to-run
  noise (0.12 between two hard runs): image 1 is not the lever, the width error is.

## 17. Animation library: retargeted references per rig family (2026-10-21)

Every animated rig family gets its clips from professional reference animations already in
`assets/models` (CC0 first, CC-BY when clearly better; sources and licenses in
`artifacts/anim-ref/SOURCES.md`), transferred onto our skeleton. Hand-keyed poses are the
fallback for machines and bodies with no reference.

| step | tool | output |
|---|---|---|
| capture | `blender -b -P tools/blender/ref_capture.py -- <model.glb> artifacts/anim-ref/<model> <clip,...> 24` | `joints.json` (joints per frame, clip length, fps; versioned) + a textured GIF per clip (ignored) |
| retarget | `rig_retarget.py` (maps, no bpy) | our poses: each bone aimed where its counterpart points (`rig_poses.aim`); relative maps turn our rest pose as much as the reference turned from its idle; legs with very different proportions (spider, rat, robot) use foot IK on the reference foot's movement |
| library | `rig_motions.py` | per family: `today_*` (the old derived clips), reference motions, `keyed_*` (hand poses); `DEFAULTS[family]` = idle/walk/attack/death/spell |
| review | `python3 tools/blender/rig_storyboard.py artifacts/anim-storyboard --json` | per-family JSON for the review page (10-frame strip + live player, side and game 3/4 views) |
| build | `build_unit.py` | idle, walk, attack (+ attack2, attack3 for a combo), death, spell: 5-7 actions, with the reference's own timing; loops never key the closing (= first) sample twice |

Layers: a motion can stack references on disjoint bones (a mount's gallop + a KayKit chop on
`rider.*`; a snake tail + KayKit upper body for naga; three apatosaurus necks out of step
for the hydra). Picks per unit: `data/unit_anim.tsv` (176 units: rig + motion per slot);
the builder uses the spec's `"anim"` first (`{"attack": "stab"}`, or `"legacy"` for the
old clips), else the unit's row when its rig matches, else the family defaults.

Contract checks (`tests/tools/blender/test_rig_poses.py`): the pure-python FK matches
Blender's pose bones (< 0.1 mm), `aim` reproduces any direction exactly, grounded frames
are planted on the floor, every map's bones exist on both sides, every default and every
unit-table pick names a real motion, `clips()` gives the five slots on real bones, flyers are not
pinned, hand-keyed clips end exactly at rest.

Plant (grounded motions): each frame not marked `air` moves the root so the lowest joint sits at
its rest height; a positive authored root `up` is added on top (a hop), negative ones are not
used. Flying families (`rig_families.HOVER`) are never planted. A motion's length is its driving
layer's: the first layer that is not a companion loop (`rig_motions.COMPANIONS`: wings beating,
a mount or rider standing, a snake swaying).

Found while drawing today's clips: the root's `lift` moves along the root bone's local Z,
which is the spec FORWARD axis (the old hover "bob" slides instead of rising; poses now
carry an optional fifth value `up` along the bone); the biped death falls face-down; old
walk/death clips sink up to 0.2 m (spider death 1.1 m) under the floor. The serpent/wyrm
head now hangs on `spine.1` (it was on the root and left the body when the chain bent).

### 17.1 In the game: combos and the spell clip (2026-10-21)

The registry `data/unit_anim.tsv` says, per unit, its rig and the motion of each slot; the
attack slot is a combo (`chop+slice_diagonal+slice_horizontal`, `stab_2h+slice_2h+stab_2h`,
`bow`, `shoot_2h+burst_2h`, builders `tool_hammer+tool_chop`). `tools/assign_model_clips.py`
turns it into `data/models.tsv`:

- `clip_attack` is a list of clip indices (`2,5,7`): the motions found by name in the unit's
  GLB (KayKit names exact; otherwise the model's own strikes/shots/spells by kind). A melee unit
  whose model has more strikes than its combo names gets up to three (Attack1/2/3, Punch L/R).
  Models we build carry `attack`, `attack2`, `attack3`, `spell` and are read as such.
- `clip_spell` (new, optional column; the parser finds columns by header name) is played once.
- `make model-clips-check` fails when `models.tsv` drifts from the registry (skipped without assets).

`UnitModels` hands the choice to `render/ClipPlayer` (pure, tested in `tests/render/ClipPlayer_test.cpp`;
render only, sim/hash/replays untouched): each sim hit (`Entity::attackTimer` rises) starts the next clip
of the combo from its first frame, sped up when it is longer than the cooldown, and the last frame holds
until the next hit; a swing in progress finishes even if the target steps out of range; 1.5 s out of
combat restarts the combo; a rise of any `Entity::castTimers` entry plays the spell clip once over
everything else; walk runs at the measured speed over the unit's base speed (0.5x-2x). Clip lengths
are read when the model loads, so offscreen units never trigger a GLB load.

The biped library now comes from KayKit Character Animations 1.1 (CC0, the free itch.io download,
same Rig_Medium as the KayKit characters): melee 1H/2H/dual-wield/unarmed, bow (draw + release as one
motion), guns, magic, tools; `ref_capture.py` films animation-only GLBs on its mannequin (Blender 5:
an action from another file plays through its slot) and joins clips with `A+B`.

## 18. Before v2-hard (2026-10-26)

### 18.A Cel texture, organic surfaces, unlit review renders (2026-10-26)

The game draws albedo only, so the hard sheet's flat facets have to live in the texture.
- **`--style cel|painted`** (`spec_pipeline.py`, default `cel`; `build_unit.py` arg `style=`, default
  `painted` so old CLI calls rebuild as before). `cel`: a slot image is three flat tone cells (light /
  mid / dark = x1.20 / x1.00 / x0.68 of the sheet colour); each face maps into the cell given by its
  world normal (`surfaces.tone_index`: up > 0.55, down < -0.35, else side). No pattern, no gloss.
  The surface only nudges the tones (`CEL_SURFACE`: glow stays one tone; slime/flesh brighter tops;
  bark a darker underside). Decal cells and alpha/glow are untouched. `painted` is the old look.
- **Surfaces** (painted style): `chitin` is matte now (gloss 0.55 -> 0.10), new `bark` (vertical
  furrows + a knot per tile), `slime` (drip streaks + wet highlight), `flesh` (veins, moist sheen);
  `wood` reads as three boards with dark joints and per-board grain.
- **Brief**: the DSL has an explicit surface-by-kind rule (animals chitin/fur/skin, scales only reptile
  or fish, living tree bark, timber wood, ooze slime, meat flesh, metal only armour and machines).
- **Unlit review**: `views.make_unlit()` moves the base colour to Emission and zeroes specular, so
  `render_unit.py` (all views, wc3, walkleft) and `turntable_color.py` show the pure texture colour,
  as the game does. Pass `lit` to either script for the old key/fill look. Silhouette masks and the
  matcap `turntable.py` (form only) are unchanged.

### 18.B1 Measuring the shape inside the contour (2026-10-26)

n01X hard-v1 against v13: the silhouette rose (front 0.871) while the octagonal chest disc
vanished, the shoulder pads became one bar and the club/fists lost blocks. Everything moved
inside the contour, so no silhouette IoU could see it. Three additions, all code, no LLM.

**Colour zones (`silhouette.py`, `render_silhouette.py`).** The sheet's figure pixels are
k-means clustered (k=4, in a hue/chroma space where lightness weighs 0.35: `zone_feature`)
into 2-4 zones; outlines are grown over from the zones beside them and a 5x5 mode filter
removes outline slivers and texture grain. The model is rendered flat, unlit, no AA, with its
painted texture (`<stem>-zone-{front,left,back}.png`, Standard view transform), its luma
histogram is matched to the sheet figure's (the render is unlit albedo, the sheet is lit) and
each pixel takes the nearest sheet zone. Both label maps are normalized exactly like the
silhouettes (same crop, same mirror variant as `best_match` chose). Per view, in
`silhouette.json` under `<view>.zones`:

| key | meaning |
|---|---|
| `mean` | area-weighted IoU of the zones |
| `cover` | area-weighted share of each *drawn piece* (connected zone region, >= 0.5 % of the figure) that the model's same-colour zone reaches within 4 px. Unlike the zone IoU it cannot be hidden by a same-colour part elsewhere: the chest disc is one piece, the shoulder pad another |
| `lost` | zones of >= 3 % of the figure under IoU 0.02: a colour the model lacks entirely (n01N's carapace, n02X's metal trim). A small zone has little weight in `mean`, so it is named here |
| `zones`, `pieces` | per zone `{iou, share}` and per piece `{"<hex>@x,y": cover}` |

Gate (front and left, vs the approved sheet, `ZONE_GATES`): `mean >= 0.08` and `cover >= 0.30`.
Calibrated on the 7 hard-v1 GLBs re-rendered (no LLM): lowest values are mean 0.100 (n01N left)
and cover 0.340 (n01N back); typical 0.15-0.60 / 0.4-0.9. The gate is a floor against a
wholesale colour miss; absolute zone IoU is low on thin-legged units (spiders) for geometric
reasons. `lost` only warns. The sharp use is the passes.

**Acceptance proof (n01X, front, chest-disc piece cover, vs hard / vs approved sheet):**
hard-v1 **0.316 / 0.291**, v13 **1.000 / 1.000**. Whole-figure `cover` is 0.640 vs 0.611 (the
disc is one piece among many): only the piece level sees it, which is why the passes check pieces.

**Passes (`spec_pipeline.accepted`).** A pass is rejected when, in any of front/left/back, the
zone `mean` falls > 0.05, a zone of >= 3 % loses > 0.15 IoU (a whole zone lost is a loss of its
whole IoU), or any drawn piece's cover falls > 0.4 (the hard-v1 -> v13 disc is -0.68). Numbers
go to `passes.json` (`zones`, `failing`) and the zone/prop rows to `review.md`.

**Preflight rule by rule (item 13).** `run_passes` compared whole preflights (None vs not
None), so a spec that already failed one rule let a pass break `shoulder_span` again (hfoo,
n005, n01I, n02X ended with wide shoulders). `failing_rules()` parses the result lines of
`preflight.py` (`  <rule>  PASS|FAIL`, INFO lines ignored) and `rules_hold()` requires that the
failing set never grows: the set of passing rules cannot shrink. It is generic by rule name,
so `box_ceiling`, `decal_place` and any later rule are covered. The pass-0 repair obeys the
same rule. An unparsable report counts as one failure (`<unparsed>`), never as a pass.

**Prop alone (`prop_measure.py`, review only).** When `refs/<id>/sheet-props.jpg` exists, the
spec's arm-held prop (a part >= 0.4 H long on an arm/forearm/hand bone, not the arms' own
material, plus the parts of that bone touching it) is built alone on the static `building`
rig, rendered front/left and compared, height-normalized, with every drawing of the props
sheet in 8 orientations (the sheet draws the club lying down). Best IoU goes to `review.md` and
`silhouette.json` (`prop`): n02X club **0.83**, hfoo spear **0.69**; n005 has no arm-held prop.
A signal, not a gate (warns under 0.40): which spec parts are the prop is a heuristic.
ponytail: props worn on spine/pelvis (backpack, tank, lantern) are not measured; add when a
spec marks its prop parts.

### 18.B2 Shape rules: box ceiling, decal placement, hoods (2026-10-26)

- `preflight.py` `box_ceiling`: parts of kind `box` <= 1/3 of the spec's parts (the rig mirrors by
  bone, so the parts list is the count; buildings are exempt). Measured on the 7 `hard-v1` specs and
  n01X `v13`: all 8 pass (0-3 boxes of 24-28). The "squareness" lives in `frustum`s, not boxes
  (n01X v13: 13 frustums, 7 of them with top scale within 15% of 1.0), so the ceiling alone will
  not push shape; it stops regressions into box-built limbs.
- `preflight.py` `decal_place` + `spec_pipeline.validate`: a part with a `decal` must be bound to a
  head/jaw/face/skull bone (last dotted segment, so `rider.head` counts). Validate rejects with
  "decal on a non-head bone"; the REPAIR prompt gets the preflight line like any rule.
- `surfaces.DECALS` new kinds `face` (eyes + 3-dot mouth) and `mask` (dark mask, two always-lit eyes,
  pale when no `decal_color`). Dots take an optional 4th field `"dark"` / `"lit"`. `build_unit` needed
  no change (it projects any kind onto the part's front face).
- DSL text: HOODS (deep dark frustum/box on the head bone, open and set back; face/mask decal on the
  head part's front face, pushed slightly ahead of the hood back wall) and BOXES lines.
- Proof: n005 hard-v1 with the head part swapped for a decal-`mask` frustum in front of the hood:
  two red glowing eyes on a dark face inside the hood, visible from the front in the colour turntable.

### 18.C Reference check and the high-knee spider (2026-10-26)

- **One figure per RTS view.** `spec_pipeline.count_figures(mask)` counts connected blobs of the
  `silhouette.foreground` key (3 px close, blobs under 10% of the foreground ignored).
  `ensure_rts` now redraws up to 3 times while the count is above 1, then warns and goes on.
  `python3.14 tools/blender/spec_pipeline.py --check-rts` lists the count of every
  `refs/*/*-rts.jpg` (all 1 except `n00U/sheet-rts.jpg`, still 3 spiders). n01N `sheet-rts.jpg`
  was 3 and was redrawn (the bad pair is not kept in the repo).
- **Rig family `spider_high`**: the spider's bones with the knee 0.55 above the back line
  (`_legs(arch=...)`): femur up and out, tibia down to the floor, as in the n01N sheet. Clips
  are the spider's (retargeted references with foot IK, keyed combos), so `spider` is
  untouched; `data/unit_anim.tsv` has n01N on `spider_high` and `RIG_TEXT` tells the spec author
  about the arch. Look at it: `python3.14 tools/blender/rig_storyboard.py <out> spider_high`.

### 18.E Review renders at rest pose; 5-7 clips (2026-10-26)

Found by rebuilding `runs/draft/n01X/hard-v1/spec.json` on today's code: front 0.47 against
0.87 on the code that built it. The animation library (§17) changed what the first clip's
frame 1 looks like, and the glTF importer leaves the rig on it, so every silhouette, view
and turntable measured a swing. `views.rest_pose()` now runs after every import (the
`walkleft` shot alone switches back to POSE), and the rebuild gives 0.875 / 0.771 / 0.874
again. The verdict also pinned `anims == 4`; animated rigs now carry 5-7 (`preflight.CLIPS`,
shared with `check_gates.py --static` for rigs without clips). The §18.B1 zone thresholds
were calibrated on the swung renders, so they are a floor: at rest the n01X views give
mean 0.39-0.49 and cover 0.80-0.85.

### 18.D Spec author on the local Claude Code login (2026-10-26)

`--model session:<opus|sonnet|...>` sends every spec-author call (the first spec, the repairs
and the per-view passes) to a one-shot `claude -p` instead of the ppq.ai chat API, so it runs
on the Claude Code login with no API credit. Same brief, same images (listed by path and read
with the Read tool), same reply parsing; any other `--model` value stays on the API.
`review.md` records the model as given. The call runs in an empty temp dir with no setting
sources, so no project CLAUDE.md, hooks or MCP servers reach the spec author. Image generation
(`generate.py`, nano-banana) stays on the API.

### 18.F Stage 1: shape in clay (2026-10-26)

`spec_pipeline.py` runs in two stages. Stage 1 (`stage_shape`) builds the spec in clay
(`build_unit.py clay`: one grey material, no texture, decal or glow) and gates the shape only:
preflight, tris, rig, and `silhouette.GATES` on all five views plus the RTS view (top/bottom/rts
at the camera the sweep picks). Repair and the per-view passes see clay renders (lit; an unlit
grey solid is one flat blob) and the overlay, never colour. A spec that fails stage 1 stops
there: no texture, turntable or stage 2, and `review.md` says what failed. Stage 2 is
`colour_stage.stage_colour(spec, glb_clay, args, tilts, work)`, called only when the module
exists; without it, or with `--shape-only`, the run ends at `SHAPE-PASS`. Clay renders land in
`views/<id>/clay-<view>.png` (rts = `clay-rts.png`); `silhouette.json` gains `tilt` and `gates`.

Gates, clay rebuilds of the 22 existing specs (7 hard-v1, 14 v2-hard-r1/r2, n01X v13; min IoU):

| view | gate | n01X hard-v1 / v13 | n01X r1 / r2 | n01N (worst) |
|---|---|---|---|---|
| front | 0.75 | 0.873 / 0.862 | 0.769 / 0.762 | 0.344-0.506 |
| left | 0.65 | 0.771 / 0.830 | 0.751 / 0.773 | 0.367-0.452 |
| back | 0.70 | 0.871 / 0.858 | 0.764 / 0.756 | 0.353-0.508 |
| top | 0.65 | 0.798 / 0.792 | 0.863 / 0.837 | 0.346-0.359 |
| bottom | 0.65 | 0.780 / 0.799 | 0.783 / 0.805 | 0.320-0.488 |
| rts | 0.70 | 0.785 / 0.781 | 0.765 / 0.756 | 0.429-0.473 |

Front/left stay at 0.75/0.65 (no evidence to move them); the new gates sit about 0.05-0.10 under
the weakest n01X view. All four n01X runs pass; only n005 hard-v1 passes elsewhere (every other
unit fails at least one view, n01N all six). `--texture` replaces `--style` (kept as an alias).

### 18.G Professional compare (2026-10-26)

`make_compare.py` now draws one grid per run: a row per view (front, left, back, top, bottom,
rts), columns concept | clay | overlay | textured, a footer per row with the view's numbers
(IoU, gate, 32 px, L1, tilt, zones) and a header with unit, run, spec author and the verdict per
stage. Overlay: concept green, model red, hit grey, drawn from `sil/<against>/mask-*`.
`compare_runs.py <out> <run>...` lays the runs side by side on the same grid (concept first, then
one column per run; `--show textured|clay|overlay`). Both read only run-directory files (contract
in the `make_compare.py` docstring); the spec_pipeline call is unchanged. The clay column needs
`views/<tag>/clay-<view>.png` (rts: `clay-wc3.png`); until S1 writes it the cell is empty with a
warning. Stage verdicts are read from `review.md` lines naming "stage 1"/"stage 2" with PASS/FAIL
(older runs show n/a). Text is drawn with Pillow, which `python3.14` must have installed.
### 18.H Stage 2 - colour on a frozen shape (2026-10-26)

`tools/blender/colour_stage.py`: `stage_colour(spec, glb_clay, args, tilts, work) -> (ok, markdown)`;
the markdown is review.md's "Stage 2 - colour" section, the final GLB is `<out>/model.glb`, the review
renders `<out>/views/<tag>/model-<view>.png`.
- **`--texture cel|painted|sheet`** (`--colour-pass N` = colour-pass tries). `sheet` is
  `project_concept.py` run on the clay GLB: each face is painted from the sheet-hard panel it faces,
  inside that panel's figure box. Fixed on the way: the left panel and the bottom panel were mirrored
  against the review cameras (`face_panel` now follows `views.VIEWS`), and the sheet's background
  between limbs showed as white slivers, so each panel's background is filled with the nearest plate
  colour on its row (`bleed`).
- **Zones on 5 views.** `render_silhouette.py` also shoots `-zone-top@<t>`/`-zone-bottom@<t>`;
  `silhouette.py --tilts top:10,bottom:20,rts:35/30` pins the cameras stage 1 chose (`pin_tilts`), and
  `ZONE_GATED` (all 5 views, mean 0.08 / cover 0.30) gates the colour. Measured on the 7 v2-hard-r2 cel
  builds the lowest top/bottom is mean 0.098 (n01N top) / cover 0.355 (n01X bottom), so the floors hold.
- **Colour pass** (optional, needs `--model`): the reply may carry only `palette` (colour, surface) and
  `decals` (decal, decal_color). `validate_colour` rejects any other change: a part, its material, a
  slot added or dropped, the alpha, a decal off the head. Accepted only if the zone mean rises and no
  view that held fails.
- **Why the cel looked washed (two causes).** (1) `views.make_unlit` moved the texture to Emission but
  left it linked to Base Color, so the sun and world lit it again: every review render was ~2x too
  bright in linear light (brass #A98451 shown as #F6C27A; hfoo's helmet and fists white). Now the link
  is removed and the render is the palette colour exactly. (2) `CEL_TONES` x1.20 on top faces
  overshot: measured as render luma / sheet luma per view over the 7 runs (before -> after, tones
  1.20/1.0/0.68 -> 1.08/1.0/0.90): front .950 -> .953, left .931 -> .948, back .934 -> .940,
  top 1.071 -> 1.010, bottom .686 -> .829 (the sheet's undersides are not dark). Zones mean
  (luma-matched, so moves little): hfoo top .189 -> .217, n02X front .311 -> .338, rest within .003.
- Sheet vs cel vs painted (n01X hard-v1, zones mean/cover front, top): cel .42/.83, .33/.67; painted
  .32/.62, .27/.59; sheet .40/.91, .22/.61. `sheet` carries the drawn plates and outlines but smears
  where the model's limbs do not sit on the drawn ones and is weakest from above; `cel` is cleaner.

### 18.L Gates per rig family; clay in the compare when stage 2 does not run (2026-10-26)

- `silhouette.RIG_GATES` overrides `GATES` per rig family; `gates_for(rig)` merges them and
  `silhouette.py --rig <family>` gates with it. `spider` and `spider_high`: front and back 0.65
  (default 0.75/0.70), the rest unchanged. The pipeline passes `args.rig` (`trial` uses
  `spec["rig"]`) in the stage 1 trial/measure and in stage 2's `measure`; `silhouette.json`
  `gates` and the review row show the family's values.
- Calibration (n00U, f/l/b): v2-hard-r1 0.667/0.658/0.675 passes; v2-hard-r2 0.611 front,
  v3-stages-r1 0.640 front, v3-stages-r2 0.530/0.639/0.530 fail. n01N (best 0.506/0.452/0.508) fails.
- `make_compare.render_cell`: a run with no stage 2 shows the clay render in the textured column,
  with a strip "stage 2 not run (clay)"; `compare_runs.py` inherits it (same cell function).
- Proof: e2e `--spec` of n00U v3-stages-r2 with `--rig spider` reproduces 0.531/0.639/0.530/0.586/
  0.586/0.564 (reference 0.530/0.639/0.530), gates 0.65/0.65/0.65/0.65/0.65/0.70 in review.md.

### 18.I Per-part rotation in the DSL (2026-10-26)

- `opts {"rot": [rx, ry, rz]}` (degrees: right, up, forward; one number = forward) is now in the
  spec brief with examples (arm out, drooping pauldron, tipped hood, stepped leg). Works on box,
  prism, frustum, dome that are not from/to parts (those are aimed by the endpoints).
- `preflight.bbox` rotates the part's box (`rot_matrix`, same order as the build: right, forward,
  up) and takes the envelope, so `band_span`, `ground_fix` and `overlaps` see the tilted part.
- `validate` rejects |angle| > 60 and a malformed `rot`; `normalise` used to drop any non-number
  `rot`, now it keeps a list.
- Root-cause fix in `build_unit.build_part`: frustum and chamfered boxes got radians and converted
  them again, so their rotation was ~0. Only old `opus55` specs with `rot` on chamfered boxes or
  frustums change on rebuild (hard-v1 and v13 of n01X have none; hard-v1 rebuilt: .878/.769/.875).
- Proof (n01X hard-v1, shoulder frustums, upper-arm prisms and hand boxes at +-15 deg around forward,
  `at` in place of from/to): preflight 15/15, build ok, 6/6 gates, front .870 left .763 back .868.

### 18.K Props in the brief and the preflight; new sheet measures with floor and ceiling (2026-10-26)

- **Props.** `prompts/<id>/props.json` (hfoo, n005, n02X) lists the unit's props in the order drawn
  on `refs/<id>/sheet-props.jpg`, left to right: `{name, where, bones, extent: [min, max]}`, `extent` =
  longest side of the prop's part in fractions of H, calibrated on the existing specs. The brief gets
  the list (`PROPS OF THIS UNIT`, bone and size per prop) and one crop per prop as an extra image
  (`prop_measure.crop_props`: foreground components of the props sheet, cut from the full-resolution
  sheet with a 5% margin; used only when the drawings match props.json one to one).
- **Convention, rule `props_present`** (`preflight.props_missing`): each prop, in order, claims one
  unclaimed part on one of its bones whose longest side is inside its bracket; a part serves one prop.
  A prop with no part fails the rule, naming it. It is a presence check: it does not compare shapes
  (`prop_measure.py` does, on the built model), and a body part of the right size on the right bone
  can satisfy it. The sheet id comes from the `<sheet>` argument's folder name; no props.json = no rule.
- **Measures** in `silhouette.measure` (approved sheet, fractions of H): `boot_height` (rows from the
  ground whose side-view length stays >= 0.7 x the sole), `head_width` (widest row in the top 70% of
  the way to the shoulder line), `neck_width` (narrowest row below the first 30%), `arm_angle` (degrees
  from vertical, outward positive, outer edge from shoulder to fist) and `arm_length`. All go to
  `measured_text`. Biped only; the spider sheets give meaningless values (no boot, no neck).
- **Floor and ceiling.** `boot_height` 0.7-1.6 x the sheet's, `head_width` 0.6-1.4 x the sheet's.
  n01X hard-v1 and v13 pass both (boot .074/.063 vs .070, head .243/.258 vs .237). Across the existing
  specs `boot_height` fails where `feet_mass` fails (n005 v2-hard-r2 .152 H, hfoo abH1 .063 H vs .136).
- Arm angle and length are in the brief only; no rule uses them yet (needs T1's rotation to be hit).

### 18.J Sheet face as a decal, ink line on cel faces (2026-10-26)

Both are stage 2 (colour); the shape is untouched.
- **`"decal": "sheet"`** on a head/jaw part (same bone rule as every decal; in `surfaces.DECALS` as an
  empty kind, so the validators and the colour pass accept it). `split_sheet.head_face(sheet, out)`
  cuts the head of the approved sheet's front figure (its top down to the shoulder line,
  `measure()["head_clear"]`) into a 64x64 RGBA png, the flat background keyed to alpha 0 as
  `silhouette.foreground` does it (premultiplied resize, no halo). `colour_stage.face_args` passes it as
  `face=<png>` to `build_unit.py`, which paints it into the decal cell and projects it on the part's
  front face by the normal decal path. Without the png (or in clay) the kind falls back to `"face"`.
  The author brief lists it next to `eyes2/eyes8/face/mask`. The crop is stretched to the head part's
  front face: size that face like the sheet's head. Valve-wheel heads (n01X) have no face to show.
- **Ink line.** In cel each face now spans its whole cell (`build_unit.face_span`: corners normalised
  over the face's own box in its dominant plane, 1 % inset) and `surfaces.paint_cel` darkens the cell
  border (1-2 px of 64, tone `INK` 0.55); a `glow` slot gets no line, alpha is not touched. The line
  is relative to the face, so a bevel is mostly ink and a big plate gets a thin edge.
- **Proof (no LLM, `--texture cel`, cameras of stage 1):** n005 and n01X v3-stages-r2, before/after in
  `scratchpad/t2/zoom-n005.png` (before | ink | ink + sheet face) and `zoom-n01X.png`. Zones mean
  front/left/back, n005 .531/.561/.586 -> .533/.581/.585; n01X .373/.372/.424 -> .38/.38/.42 (full
  pipeline, stage 1 and 2 PASS). The line is subtle on dark palettes (n005) and clear on n01X.

## 19. Papers (2026-10-27)

Dez papers de `~/Desktop/genAI` (lista e ordem em `ROADMAP-papers.md`), 14 itens implementados em worktrees
paralelos e integrados em `feat/models-v2-hard`. Bateria de prova `v5` nas 3 unidades de teste, autor
session:opus, sem passes (imagens em `history/2026-10-27-v5/`):

| unidade | v4-oneshot | v5-oneshot | v5 + `--fit` | veredito v5+fit |
|---|---|---|---|---|
| n01X | .776/.782/.774/.856/.804/.777 | .768/.777/.766/.830/.789/.797 | **.832/.802/.829/.840/.811/.796** | PASS, final-use |
| n005 | .695/.700/.746/.669/.727/.817 | .721/.795/.758/.707/.775/.811 | **.853/.826/.894/.746/.773/.864** | **PASS** (primeiro do n005) |
| n00U | .398/.555/.392/.514/.531/.516 | .254/.368/.257/.411/.404/.490 | .618/.569/.612/.630/.599/.610 | CHECK (gate spider .65) |

O ganho é do `--fit` (§19.D1, numérico, sem LLM), que agora roda depois do repair (`2748a218`: antes, o patch do
LLM desfazia o ajuste: n005 .82 → .71). O estágio 1 aceita o GLB 2 % acima do teto de tris (`TRI_SLACK`), porque
o preflight estima e o GLB conta (n005: 704 vs 700). Ficou opt-in sem ganho medido: C1/C2 (rampa), B3 (limpeza),
B4 (`cut`), B5 (`outside_hull`, só relatório). Negativos: A2 (chamfer como gate), E2 (CLIP, Spearman 0.27).
Aranha: corpo pequeno e pernas longas vêm do rig `spider`; próximo passo é o rig, não o autor.

### 19.A1 `mesh_lint.py`, the Readiness block and the four statuses (2026-10-27)

Papers: Chen 2023 (manifold / self-intersection table), Wiersma 2026 (sliver < 10 deg), Begemann &
Hutson 2026 (technical matrix, four statuses), MeshGPT 2024 (|V|/|F|, face area), EdgeRunner 2024 (face
orientation, degenerates, components; watertight is not required, a unit is a union of closed parts).
- **`tools/blender/mesh_lint.py`**: numpy over the glTF JSON + BIN (no Blender; `check_gates.stats`
  only reads the JSON, so the accessor reader is new). `lint(glb)` returns verts, faces, nodes, meshes,
  skins, `compactness` (|V|/|F|), `face_area{median,p90,max_over_median}`, `sliver_pct`, `degenerate`,
  `flipped` (accessor normal . geometric normal < 0), `boundary_edges` / `nonmanifold_edges` /
  `components` (on welded vertices, 1e-5), `uv_out_of_range`, `uv_overlap_pct` and `atlas_used_pct`
  (1024 raster, the decal cells 8-15 of each 256 px block excluded; glTF v is top-down, the cells are
  bottom-up), `texel{min,max,ratio}`, materials, images, `image_size`, `unique_colours`
  (Pillow), `pivot{min_y,height}`, `root_scale`. About 0.3 s per GLB. `python3.14 tools/blender/mesh_lint.py a.glb`
  prints the JSON.
- **Gates on** (`mesh_lint.GATES`, the obvious ones): `flipped == 0`, `uv_out_of_range == 0`,
  `images == 1`, `abs(min_y) <= 0.01 H`, `root_scale == 1`. The three texture ones only count on the
  textured model (not on `clay.glb`). Everything else is reported only.
- **`check_gates.py`** prints flipped / sliver % / components and fails on the lint gates.
  **`spec_pipeline.write_review`** adds `## Readiness` (criterion | value | gate, from `model.glb` when
  stage 2 wrote it, else `clay.glb`) and `status:` from `status_of`: SHAPE-PASS -> `prototype-safe`;
  PASS + clean lint -> `final-use`; PASS + a failed lint gate -> `prototype-safe` (a choice not in the
  roadmap: the shape and colour are fine, the file is not); CHECK with front IoU < front gate - 0.10 ->
  `rejected`; any other CHECK -> `placeholder`. The lint never changes the verdict or the exit code of
  `spec_pipeline`, only the status.
- **Calibration (68 committed GLBs, 47 textured, `runs/draft/*/*/*.glb`).** Failures per gate:
  `abs(min_y) <= 0.01 H` 28, `images == 1` 20 (legacy runs: 0 images in `opus55`/`v3`, 3-4 in
  v8-v13), `uv_out_of_range` 14 (1-3 vertices slightly under 0 or over 1, planar UVs of the old
  texturizer), `flipped` 0. Not gated: non-manifold edges in 2 files (v6/v10 hand models), degenerate faces in none.
- **Negative: `image_size <= 512` is NOT a gate** (the roadmap listed it). 33 of 47 textured GLBs
  are 768 x 512 or 768 x 768, because `texturize` gives each of 5-8 materials a 256 px block (3 columns),
  and the current pipeline's own `v4-oneshot-r1/model.glb` of n01X (6 materials) is 768 x 512. A gate would
  fail every legitimate run. Re-enable when the atlas is packed to 512 (fewer blocks or 128 px blocks).
- **Not usable yet:** `uv_overlap_pct` is 60-85 % on healthy models (cels and planar UVs share cells
  on purpose, the face spans a whole cell) and 100 % with 0 % atlas used on the v2-hard runs
  (degenerate UVs, 1 unique colour); `texel.ratio` is 20-90000 (cel `face_span` stretches a cell over any
  face). Neither separates good from bad as the texturizer maps today; they stay as columns.
- `abs(min_y)` at 0.01 H is tight for the spider: n00U v4-oneshot-r1 clay is 0.0104 H and v3-stages-r1
  clays of n005 / n01X are 0.019 / 0.041 H (feet floating: real, `ground_fix` territory). Not relaxed.

Calibration table (min_y as a fraction of H; sliver = % of faces with a smallest angle < 10 deg;
V/F = |V|/|F|; gate = failed lint gates on that file, texture gates only if textured):

| run | tris | V/F | sliver % | comp. | bnd/nm edges | images | image size | uv oor | uv overlap % | min_y/H | gate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| n01X hard-v1 | 620 | 1.65 | 0.0 | 32 | 0/0 | 1 | 512x512 | 0 | 77.7 | 0.000 | none |
| n01X v13 | 652 | 1.45 | 2.5 | 32 | 0/0 | 4 | 256x256 | 0 | 97.0 | 0.000 | images == 1 |
| n01X v4-oneshot-r1 clay | 640 | 1.53 | 7.5 | 31 | 0/0 | 0 | - | 0 | - | 0.000 | none |
| n01X v4-oneshot-r1 model | 640 | 1.83 | 7.5 | 31 | 0/0 | 1 | 768x512 | 0 | 83.5 | 0.000 | none (768 reported) |
| n005 hard-v1 | 600 | 1.63 | 0.7 | 31 | 0/0 | 1 | 768x512 | 1 | 60.9 | 0.000 | uv_out_of_range |
| n005 v4-oneshot-r1 clay | 668 | 1.30 | 10.8 | 27 | 0/0 | 0 | - | 0 | - | 0.000 | none |
| n00U hard-v1 | 512 | 1.74 | 37.5 | 24 | 0/0 | 1 | 768x512 | 2 | 50.0 | 0.025 | uv_out_of_range, min_y |
| n00U v4-oneshot-r1 clay | 496 | 1.65 | 42.7 | 24 | 0/0 | 0 | - | 0 | - | 0.010 | min_y (0.0104) |
| hfoo hard-v1 | 528 | 1.68 | 3.0 | 28 | 0/0 | 1 | 768x512 | 0 | 63.0 | 0.000 | none |
| hfoo v2-hard-r1 | 648 | 1.38 | 18.8 | 28 | 0/0 | 1 | 768x768 | 0 | 100.0 | 0.020 | min_y |
| n01X v10 | 884 | 1.55 | 2.7 | 36 | 0/16 | 3 | 256x256 | 0 | 99.9 | 0.000 | images == 1 |
| n01X v6 hand-n01X | 684 | 1.58 | 5.3 | 32 | 0/12 | 0 | - | 0 | - | 0.000 | images == 1 |

Sliver % splits by design more than by quality: the spider (thin legs) is 37-43 % in every run, the
biped 0-15 %, the v2-hard runs 10-25 % (more than hard-v1 of the same unit). That is the only
column that moved with the v2-hard regression; it is not gated until a ceiling per rig family is chosen.
Proof of the block: `scratchpad/papers-a1/readiness.md` (n01X v4-oneshot-r1). Tests:
`tests/tools/blender/test_mesh_lint.py` (synthetic cube: clean, flipped, open, lifted, scaled; the
n01X hard-v1 calibration; the four statuses).

### 19.A2 Chamfer 2D de contorno por vista (2026-10-27)
- **O que mudou:** `silhouette.chamfer(a, b)`: média bidirecional da distância (EDT) entre pixels de borda das duas
  máscaras, dividida por H (256 px do canvas). Coluna `chamfer` por vista em `silhouette.json`; linha "contour chamfer"
  + "SD mean" (média das vistas) no `review.md`; `SD` no rodapé de cada linha e `SD mean` no cabeçalho do compare.
  Não é gate. Papers: Sketch2Mesh 2021 (Eq. 5), Chen 2023 (SD multi-vista).
- **Prova (sem LLM; `silhouette.py --shape` sobre os `clay.glb`, sheet aprovado; saídas em
  `scratchpad/papers-a2/<id>-<run>/`; as máscaras de runs antigos não estavam guardadas, foram recalculadas):**

  | run | IoU médio | SD mean | gates |
  |---|---|---|---|
  | n01X v3-r1 / v3-r2 / v4 | .807 / .802 / .795 | .0199 / .0221 / .0200 | 6 / 6 / 6 |
  | n005 v3-r1 / v3-r2 / v4 | .656 / .744 / .726 | .0477 / .0348 / .0390 | 3 / 5 / 5 |
  | n00U v3-r1 / v3-r2 / v4 | .616 / .572 / .484 | .0406 / .0471 / .0585 | 1 / 0 / 0 |

- **Resultado (negativo):** Spearman contra nº de gates passados, 9 runs: IoU .97, SD .91. Só n005 x n00U (6 runs):
  IoU .97, SD .77. O SD **não** separa n00U de n005 melhor que o IoU: n005 v3-r1 (3/6 gates) tem SD .0477, pior que
  n00U v3-r1 (1/6) com .0406. Motivo: o chamfer pesa só o contorno; o n00U tem perna fina e longe do concept (área
  errada, contorno perto), o IoU pune a área. Útil como complemento (diz o quão longe, em %H, o contorno está: o n00U
  v4 tem 7% de H de erro em front/left/back), não como substituto. Fica como sinal, sem gate.

### 19.A3 Compare com colunas `wire` e `uv`, status no cabeçalho, eixos de avaliação (2026-10-27)
Papers: MeshGPT 2024 (forma x triangulação avaliadas à parte), EdgeRunner 2024 (Input Consistency / Triangle
Aesthetic / Overall, 1-5), Begemann & Hutson 2026 (UV screenshot no relatório de prontidão).
- **`tools/blender/render_wire.py`** (Blender, Workbench): importa o GLB clay, troca o material por um cinza,
  e põe sobre cada malha uma cópia triangulada com modifier Wireframe (espessura 0.4 % da maior dimensão,
  material escuro). Escolhido em vez de Freestyle: Freestyle só traça arestas de borda/vinco, não a triangulação
  real do GLB, que é o objetivo da coluna; a cópia sólida por baixo esconde o lado de trás. Grava
  `views/<id>/wire-<view>.png` nas 7 vistas do `views.VIEWS` + `rts`, com os mesmos tilts de `render_unit`
  (~1 s por GLB). `spec_pipeline.shape_review` chama logo após `render_unit`.
- **`mesh_lint.uv_image(glb)`**: atlas do GLB com cada triângulo UV desenhado em PIL e os pixels cobertos por 2+
  triângulos em vermelho (`cover_map`, extraído de `raster_uv`, que agora o reutiliza; mesmas células de decal
  excluídas). `None` sem UV/atlas (clay).
- **`make_compare.py`**: colunas `concept | clay | wire | overlay | textured | uv` (a `uv` só na 1ª linha: é uma
  imagem por modelo); cabeçalho com `verdict` e `status` (lido de `status: **x**` do review.md). `compare_runs.py`
  ganha `--show wire|uv` e `status` na cabeça de cada run. `find_views` ignora `wire-*.png` como stem textured.
- **`review.md`**: `## Avaliação` logo após o cabeçalho, 3 eixos (consistência com o sheet, estética da triangulação,
  qualidade geral) com nota 1-5 vazia, para o reviewer de visão; nada o preenche ainda.
- **Prova (rebuild sem LLM, sem repair):** `scratchpad/papers-a3/{n01X-hard-v1,n005-v4,n00U-v4}/compare.png`
  (n01X hard-v1: 6/6 gates, final-use; n005 v4: 5/6, placeholder; n00U v4: 0/6, rejected). Números de silhouette
  de n01X hard-v1 iguais ao de referência (.875/.771/.874).
- **O que o `uv` mostra (e nada melhora por isso):** nas células de cel o atlas do texturizer cobre as mesmas
  células com dezenas de triângulos sobrepostos (vermelho): é o `uv_overlap_pct` de 60-85 % do §19.A1 visto
  a olho. Útil para o reviewer, não gate. Compare de runs só clay mostra "no UV atlas (clay run)".
- **Fora:** nenhum reviewer de visão preenche a Avaliação ainda; wire de vistas `right`/`roof` de prédios existe
  mas só as linhas do layout do run são mostradas.

### 19.B3 Limpeza da malha no join padrão (2026-10-27) - NEGATIVO, flag desligada
- **O que:** `build_unit.clean_mesh(body)`: `remove_doubles` 1 mm + DECIMATE DISSOLVE 6° com `delimit={MATERIAL}`,
  logo depois do `join` final e antes de morph/texturize/atlas (UVs nascem depois, então não há UV para fundir).
  Liga com o argumento `clean` do `build_unit.py`; **default desligado**. Paper: MeshGPT 2024 (pré-processo).
- **Medida (clay, sem LLM, budget 700, sheet.jpg):** n01X hard-v1 faces 264 -> 252, **tris GLB 620 -> 620**;
  n005 v4-oneshot-r1 faces 274 -> 250, **tris 668 -> 668**. IoU das 6 vistas idêntico à 3ª casa
  (n01X .873/.771/.871/.798/.780/.785; n005 .695/.700/.746/.669/.727/.817), gates iguais.
- **Por quê não rende:** as peças são caixas/prismas separados; o dissolve só funde triângulos de um mesmo plano
  em quads/n-gons, que voltam a ser os mesmos triângulos na exportação. Vértice sobrando (valência 2) quase não
  existe. O ramo `union` ganha porque o boolean cria costuras; o join padrão não cria.
- **Não verificado (fica para quem ligar):** pesos de pele no merge de vértices entre peças de ossos diferentes
  (remove_doubles pode misturar pesos na costura) e textura cel/atlas com `clean`. Só ligar com ganho de tris medido.
- Provas: `scratchpad/papers-b3/{n01X-hard-v1,n005-v4-oneshot-r1}-{base,clean}/` (m.glb, sil.txt, build.log).

Itens do `ROADMAP-papers.md`. Tudo medido sem LLM, nos specs existentes (`runs/draft/*/*/spec.json`, 53 no total, sheet de `refs/<id>/sheet.jpg`).

### 19.B1 Contorno do sheet no brief (2026-10-27)
- **O que.** `silhouette.outline(mask)`: fecha buracos (closing 2 + fill), maior blob, contorno Moore, Douglas-Peucker com eps 1,2 % de H, segmentos a menos de 4 graus de V/H viram V/H; se passar de 24 vértices o eps cresce x1,25. `measure()["outline"]` devolve front/left/back em (x/H, y/H) nos eixos do spec (x à direita do centro, z para onde apontam os pés, y a partir dos pés; o back é espelhado). `spec_pipeline.outline_text` injeta as três listas no brief ("the outline you must fill").
- **Paper.** Sano 2026 §3.3-3.4. Sem dependência nova (scipy já era usada).
- **Medida.** n005: 18 / 22 / 21 vértices (front/left/back), n01X 23 / 26 / 23 antes do teto de 24, agora <= 24. O front do n005 traz o braço em A (`(0.33,0.28) (0.28,0.45)`), a lanterna no cinto e o tanque nas costas. Brief completo em `scratchpad/papers-b12/brief-n005-measured.txt`.
- **Piorou.** O brief cresce ~1,2 kB. O polígono é só o contorno externo: o vão entre braço e tronco fechado por baixo é preenchido pelo closing. O sinal de z do left vem da média dos vértices rasos (a ponta da bota), heurística.

### 19.B2 Orçamento por grupo, simetria, grade e ordem (2026-10-27)
- **budget_split** (EdgeRunner). `measure()` ganha `area_head/body/legs` (fração da área do front: acima do ombro, ombro-quadril, abaixo do quadril). Alvo por grupo = 0,5 x área + 0,5 x prior do corpus (0,13 / 0,63 / 0,24), faixa +-25 % e +-0,08 absolutos (`preflight.split_bands`). A roda da cabeça não conta (é do `ornament_cost`). O brief lista a tabela em tris (`split_text`, só biped). **Desvio do roadmap:** só 3 grupos, não 5; o braço é 0-1 % da área do front (pendurado junto ao tronco), a silhueta não o separa, e área pura não prevê tris (pernas são cilindros, 0,4 x a área em tris; n01X hard-v1 gasta 28 % na cabeça por causa da roda) — por isso o prior.
- **symmetry** (Wiersma). Para cada osso `X.L`, as peças ordenadas por (kind, y, z) têm de ter gêmea em `X.R` com mesmo kind, dims (5 %) e rot `[rx, -ry, -rz]` (5 graus); `opts.asym: true` em qualquer peça do par isenta. Linha nova no DSL do brief.
- **normalise** (EdgeRunner, MeshGPT). `preflight.normalise(parts, family, extra)`: at/dims/from/to na grade (altura do rig)/256 (dim nunca abaixo de 1 célula); ordem = osso do rig (+ extras), y, L antes de R. Idempotente (grade fixa do rig, não da altura do spec). Chamado em `parse_spec` e `apply_patch`, depois do `ground_fix`.
- **Medida (53 specs, preflight com o sheet do id).** n01X hard-v1: 17/17 antes, 19/19 agora (as duas regras novas passam). FAIL por regra antes -> depois: `overlap` 3 -> 3, `ground` 10 -> 10 (iguais; a normalise não mexe neles), `symmetry` 0 -> 28, `budget_split` 0 -> 16. Specs com algum FAIL: 35 -> 40; 5 só falham nas regras novas. Aplicar a normalise antes do preflight muda 2 vereditos antigos de `shoulder_span`, um para cada lado (n01I hard-v1 FAIL->PASS, n02X v2-hard-r1 PASS->FAIL; ambos na borda da tolerância).
- **Piorou / pendente.** `symmetry` dispara em 28 specs antigos, quase sempre arma/lanterna numa mão só (`forearm: 4 parts left, 2 right`) sem `asym`, que não existia: é o comportamento certo, mas o repair precisa do aviso no brief (já está no DSL). `budget_split` pega pernas magras (< 20 %) e corpo inchado (> 71 %); o prior sai de 37 specs de 6 unidades, recalibrar quando houver mais sheets. Não rodei LLM: o efeito no one-shot (menos repair) não foi medido.

### 19.C1 Rampa vertical nas células do cel, filtro point (2026-10-27)

Paper: Le 2026 (gradient texturing: rampa escuro-claro, ilha esticada, chanfro no topo, point filter).
- `surfaces.paint_cel`: cada célula de tom (claro/médio/escuro) é uma rampa vertical de `RAMP_SLOTS` = 8 faixas planas de
  8 px (atlas 256), com ink line de 1 px em volta de cada faixa (`slot_v` mapeia a face em 80 % da faixa: a linha cobre ~3 % da face,
  como antes). Uma face ocupa UMA faixa, então continua chapada e com linha nos 4 lados. `ramp_slot(nz, altura, chanfro)`:
  v = 0.6·(0.5+0.5·nz) + 0.4·altura relativa na peça (`build_unit.relative_height`, centro da face no bbox da peça mais próxima);
  face de chanfro (3 componentes da normal > 0.3) = topo da rampa.
- `bind_atlas`: `interpolation = "Closest"` (sampler NEAREST no glTF) quando o estilo é cel. Os outros estilos seguem linear
  (cell painted tem padrão, ponto não ajuda). A margem de célula do cel já era 1 %; a das decais (4 %) ficou, não há ganho.
- Inclinação `RAMP_SLOPE` (variação de tom ao longo da rampa, fração do tom) calibrada para ser neutra em luma numa caixa:
  `TONE_V` = (1, .5, 0) = v de uma face de topo/lado/fundo de um cubo (altura 1/.5/0).
- **Medida** (n01X hard-v1, n005 v4-oneshot-r1, cel, câmeras do estágio 1; luma = luma média do render / do sheet; zonas
  mean front/left/back/top/bottom), antes -> rampa 0.5 (`ramp=0.5`):
  n01X zonas .41/.39/.48/.32/.19 -> .29/.40/.47/.29/.20 (o front cai .41 -> .29; com 0.1 e 0.2 o mesmo .30), luma 1.04/1.03/1.05/1.07/1.03 -> 1.03/1.05/1.03/1.04/1.06.
  n005 zonas .51/.56/.60/.44/.49 -> .51/.56/.59/.44/.37 (bottom .49 -> .37), luma .90/.91/.87/.96/.72 -> .89/.93/.89/.93/.74.
  A rampa mexe a luz por face e o k-means do sheet é quase plano: uma região na fronteira de duas zonas muda de rótulo.
  O top sobe (n01X .32 -> .35 com 0.2), mas as outras vistas caem: **o zone mean não se sustenta, então `RAMP_SLOPE = 0` é o default**:
  o cel sai plano como antes (as faixas, o ink por faixa e o point filter ficam; n01X mean/cover front .4137/.833 contra .4145/.836 antes).
  Ligar: `build_unit.py ... ramp=0.5` (e C2 abaixo).
- O que piorou/ficou: com o default, luma n005 front/left/back/bottom -0.01 (a linha de tinta agora cai em 1 texel inteiro, sem blur);
  n01X +-0.00. Look: em modelos de caixas, só peças rotacionadas mudam de faixa (lado de caixa = v .5 sempre), então a rampa quase
  não aparece onde as faces são axiais; `compare` antes | default | ramp 0.5 em `scratchpad/papers-c12/c1-compare-{n01X,n005}.png`.
- Testes: `test_surfaces.Cel` (rampa monótona e flat ao longo de u, tom exato em `TONE_V`, ink por faixa, `ramp_slot`, default plano).

### 19.C2 Rampa medida do sheet, L1 de luma por zona, Oklab (2026-10-27)

Papers: Le 2026 (a rampa da arte), Wiersma 2026 (cor em Oklab).
- `silhouette.zone_palette` devolve `(names, centres, ramps)`, `ramps[i] = (p10, p90)` de luma dos pixels da zona no sheet.
  `colour_stage.with_ramps(spec, sheet)` põe `palette[slot]["ramp"] = [p10, p90]` na zona de cor mais próxima da cor do slot;
  `colour_stage.valid_ramp`/`check_palette` aceitam o campo (`0 <= p10 <= p90 <= 1`; o pass de cor pode carregá-lo).
  `build_unit.register_palette` lê `ramp`; `surfaces.ramp_slope(ramp, rgb)` = largura / luma do slot, no máximo `RAMP_MAX` = 0.6, vira a
  inclinação da célula daquele material. Ligar: `spec_pipeline --ramp` (só `--texture cel`). **Default desligado**.
- Métrica nova `luma_l1` (silhouette, por vista): L1 entre os quantis p10/p50/p90 de luma do render e do sheet por zona, pesado
  pela área da zona no sheet, medido sobre o render ANTES do `match_luma`; linha "luma L1 vs sheet" no review (estágio 2).
  Valor de referência n01X hard-v1 cel plano: .029/.031/.024/.046/.043 (front/left/back/top/bottom).
- Medida da rampa do sheet nos 7 v2-hard-r2 (cel, 35 vistas, tilt do sweep): zone mean .2792 -> .2784, cover .606 -> .599,
  luma L1 .0429 -> .0454. Não melhora (as rampas medidas são estreitas, p10-p90 ~.04 de luma = inclinação ~.1, e o front do n01X
  cai de novo: .41 -> .30; n005 igual, .507/.559/.596/.441/.490). Nos dois alvos nomeados o L1 do n01X piora (front .029 -> .035).
  **Fica opt-in.**
- `zone_feature` em Oklab (`oklab`, `zone_feature_oklab`, a/b x 3, L x 0.35): nos 7 v2-hard-r2, cel plano, mean .2792 -> .2929
  (diferença pareada +.0137, t = 2.15, 23 de 35 vistas melhoram), std entre vistas .1067 -> .1044, cover .606 -> .610. O ganho vem quase todo de
  n00U (+.059) e hfoo (+.026); sem o n00U ~ +.007. n01X front .356 -> .346, cover mínimo de hfoo left .302 -> .276, abaixo do piso 0.30 do gate
  (calibrado no espaço antigo). Variância não melhora o bastante e o gate recalibrado seria outro trabalho: **o antigo é o default**;
  `silhouette.py --space oklab` mede no novo (`ZONE_SPACE`).
- Testes: `test_silhouette.ZoneRamp` (Oklab contra os valores de Ottosson, `luma_l1`), `test_colour_stage.Ramp`, `test_surfaces.Cel.test_ramp_slope...`.

### 19.D1 `fit_spec.py`: dims/at ajustados contra a silhueta, antes do build (2026-10-27)
- **O que mudou:** `tools/blender/fit_spec.py spec.json sheet.jpg out.json [--views front,left,back] [--kind mass]
  [--margin 0.02]`. Proxy numpy do build (contorno convexo de cada peça, com os mesmos eixos/rotações/afunilamentos do
  `build_unit`: prism/dome/frustum/box/cyl/wheel/ring e from/to), projetado em front/left/back, preenchido (PIL) já no
  layout de `silhouette.normalize` (256x384, melhor de espelho). Objetivo por vista: `(1 - IoU) + chamfer` (mesma conta de
  `silhouette.chamfer`, com o EDT do concept em cache). `scipy.optimize.minimize(Powell)` com limites: dims +-20 %, `at`
  +-0.05 H, **só** nas peças cujas linhas cruzam a faixa de maior erro das vistas abaixo do gate + 0.02 (o resto fica
  congelado); pares espelhados (arm.L/arm.R...) andam juntos. As regras do preflight que passavam são restrição dura
  (`preflight.checks_of`, extraída do `main`, roda em 0.5 ms; regra nova quebrada = custo 10). Sem vista abaixo do gate,
  ou sem ganho, devolve o spec intacto.
- **Gancho:** `spec_pipeline.py --fit` (default desligado), logo depois do spec e antes do repair/primeiro build:
  `fit_stage` constrói o clay real do original e do ajustado (`<run>/fit/`, `fit.json`) e fica com o ajustado só se
  `fit_accepted`: nenhuma vista que passava cai abaixo do gate, a soma dos IoUs gateados sobe, nenhuma regra do preflight
  quebra. Senão mantém o original.
- **Passo 1, proxy x render (22 specs de `runs/draft`, front/left/back, os `silhouette.json` guardados; script
  `scratchpad/papers-d1/validate.py`):** 117 pares, **correlação 0.998**, erro médio absoluto 0.006, viés -0.0002;
  só os 27 pares dos runs clay (com `tilt`): 0.998. Pior caso: hfoo hard-v1 back, proxy .709 x render .665. Não precisou
  melhorar o proxy (hull de prism/frustum afunilados e rotações já bastam). Por isso a margem de 0.02 no gate.
- **Passo 2, prova sem LLM (rebuild real do spec original e do ajustado, `spec_pipeline --spec ... --shape-only`,
  saídas em `scratchpad/papers-d1/<id>-{base,fit}/`; o base reproduz o `silhouette.json` guardado do run):**

  | run | front | left | back | top | bottom | rts | gates |
  |---|---|---|---|---|---|---|---|
  | n005 v4-oneshot-r1 base | .694 | .700 | .746 | .670 | .724 | .816 | 5/6 |
  | n005 ajustado (1817 avaliações, 30 s) | **.832** | **.802** | **.876** | .705 | .753 | .828 | 6/6 |
  | n00U v4-oneshot-r1 base | .398 | .555 | .392 | .512 | .531 | .516 | 0/6 |
  | n00U ajustado (4000 avaliações, 2 min) | **.581** | **.626** | **.577** | .510 | .536 | .570 | 0/6 |

  Proxy previu n005 .838/.809/.881 (render .832/.802/.876) e n00U .576/.622/.572 (render .581/.626/.577). n005 sai de
  CHECK para SHAPE-PASS; o chamfer de front cai de .030 para .017. n00U melhora +0.18 em front/back mas continua longe do
  gate 0.65 do spider: a forma (pernas finas, longe do concept) precisa de peças novas, não de dims.
- **Gancho de ponta a ponta** (`--fit --shape-only` sobre o n005, `scratchpad/papers-d1/n005-hook/`): clay real
  .694/.700/.746/.670/.724/.816 -> .834/.803/.877/.705/.754/.828, `fit_accepted` aceitou, veredito SHAPE-PASS.
- **O que piorou / limites:** n00U top -0.002 (já falhava). Só front/left/back entram no objetivo (top/bottom/RTS não
  têm proxy: o tilt é varrido no render), então eles sobem por correlação, não por medida. `wheel` e `ring` entram
  como disco cheio (o furo não conta); spec com `segments` não é ajustado. Powell bate o teto de 4000 avaliações no n00U.
  Custo do `--fit` no pipeline: fit (30-120 s) + 2 builds clay extras (~80 s cada).
- Papers: Sketch2Mesh 2021 (refinar parâmetros com Chamfer 2D de contorno; só onde o contorno falha), Wiersma 2026
  (regularizadores como restrição dura), MeshGPT 2024 (congelar o que já está bom).

### 19.B4 Peça cortada pela silhueta do sheet (2026-10-27) - NEUTRO no IoU, opt-in
- **O que.** `opts {"cut": "sheet"}` em box/prism/frustum sem `rot`/`from`/`to` (`spec_pipeline.bad_cut` rejeita o resto). `cut_hull.py` (Python do sistema, antes do Blender) lê as máscaras front e left do sheet aprovado (`silhouette.concept_panels`), pega a faixa de linhas e colunas que o bbox da peça cobre (+10 %), `silhouette.outline(limit=8)` reduz cada contorno a <= 8 vértices e o encaixa no bbox (`preflight.bbox`); grava `cuts.json` e passa `cuts=<json>` ao `build_unit.py` (`cut_hull.args`, chamado em `trial`, `stage_shape` e `colour_stage.build_textured`). `build_unit.cut_part`: extrude o contorno front ao longo de z, o left ao longo de x, `BOOLEAN INTERSECT` EXACT. Sem sheet legível ou faixa < 6 px a peça sai como a primitiva (sem erro). `preflight.part_tris` conta `CUT_TRIS = 60`. DSL no brief: torso, pelvis, capuz, carapaça, abdômen; nunca membro, mão, pé, arma, cabeça (a faixa de um membro pega o que está desenhado ao lado); máx. 3 por unidade.
- **Paper.** Sano 2026 §3.5 (visual hull = front extrudado ∩ left extrudado).
- **Medida (sem LLM, `--shape-only --no-repair`, specs v4-oneshot-r1 reconstruídos; IoU front/left/back/top/bottom/rts; provas em `scratchpad/papers-b4/`).**

| spec | variante | tris | IoU vs approved |
|---|---|---|---|
| n005 | antes | 668 | 0.698 / 0.699 / 0.749 / 0.668 / 0.723 / 0.819 |
| n005 | torso(3)+pelvis prism(2) com cut | 734 | 0.695 / 0.696 / 0.746 / 0.672 / 0.742 / 0.832 |
| n005 | + capuz (head frustum sem rot) | 758 | 0.701 / 0.695 / 0.749 / 0.670 / 0.740 / 0.829 |
| n00U | antes | 496 | 0.398 / 0.554 / 0.393 / 0.513 / 0.531 / 0.517 |
| n00U | 2 frustums da carapaça com cut | 556 | 0.391 / 0.552 / 0.385 / 0.515 / 0.531 / 0.519 |

  Cada peça cortada custa 42-61 tris (vs 28 do prisma, 12 do frustum), polígonos de 6-8 lados nos dois eixos.
- **Piorou / pendente.** O IoU não sobe: front -0.003 / +0.003 (capuz), n00U front -0.007. Torso e pelvis são faixas pequenas da silhueta e o erro dominante do n005/n00U está em outras massas (capuz alto, braço, pernas do spider); o cut só ganha forma local (ombro mais largo que a cintura, vista left visivelmente mais fiel). Fica opt-in, nenhum default muda. O cut não herda `rot` (por isso o capuz do n005 perdeu o `rot [10,0,0]` na prova); o left assume o mesmo sentido de z do render (frente à direita), sem tentar o espelho. Custo em tris sobe 60-66 por unidade com 2 cuts: o gate de orçamento da n005 passou de 668 para 734 (> 700, FAIL), então o brief limita a 3 e o `part_tris` já avisa. Falta medir o efeito com LLM (decidir se a faixa melhora o one-shot) e rever o `B5` (`outside_hull`), que reusa as máscaras.

### 19.B5 Regra `outside_hull` no preflight (2026-10-27)

Paper: Sano 2026 (visual hull como volume válido). Fecha o "closed-loop part-box gate" de §13.3 sem renderizar.

- **O que.** `preflight.py <spec> <kind> <sheet>`: hull = `front[y, x]` e `left[y, z]` do sheet aprovado (`silhouette.concept_panels`, crop da figura, escala = altura do próprio spec, como `normalize`); amostra uma grade de célula H/64 por peça (caixa rotacionada de `preflight.bbox`; prism/cyl/dome sem rot ficam na elipse, from/to só no eixo, ring/wheel fora: o disco é `ornament_cost`). FAIL se > 25 % dos pontos de uma peça caem fora do hull; a linha nomeia a peça, a % e `too wide|tall|deep`. Sem sheet a regra não existe.
- **Convenção de eixos.** Front: coluna cresce com +x (spec right = Blender x, câmera front em -Y). Left: coluna = +z (forward) ou -z, o que errar menos: o sheet do biped olha para a direita, o da aranha para a esquerda (mesmo espelho que `silhouette.variants`).
- **Folgas (calibradas, sem elas hard-v1 falhava).** Hull dilatado 3 % de H (placa saliente, linha de tinta) e painel deslizável ±12 % de H por vista, escolhendo o deslize com menos pontos fora: o sheet pode ter arma/pose que o spec não tem e a caixa do sheet fica torta. Escala pela altura do spec, não do rig (a aranha tem 1,15 contra 0,74 do rig); logo `too tall` só aparece se a peça passa do topo.
- **Medida (53 specs de `runs/draft`, sheet do id).** 11 PASS, 42 FAIL. n01X: 8 de 10 passam (hard-v1 e v13 incluídos); v3-stages-r1 e v4-oneshot-r1 falham com `spine 33 % too deep` (torso fundo demais). hfoo hard-v1 passa. Antes de dilatar/deslizar: 53/53 falhavam, inclusive hard-v1 (nem o ground truth passava: prova de que o gate cru era estrito demais).
- **O que pega.** `forearm` (braço/arma fora do corpo do sheet, too wide) em hfoo, n005, n02X (~35 specs); torso `spine/pelvis` fundo ou largo demais; spiders n00U/n01N: `head`, `leg*.lower/upper` too deep/wide (modelo 2x mais comprido que o sheet para a mesma altura, pernas longe do corpo).
- **Piorou / pendente.** 42/53 falhando: a regra é rígida para biped fora do n01X; só o repair a usa como alvo (REPAIR já lê qualquer linha FAIL). Componente solto no painel (n005 left tem fragmentos) infla o crop; manter só o maior componente fica para depois. Prova: `scratchpad/b5-run5.txt`.

- **Integração (2026-10-27, merge):** `HULL_BLOCKING = False` em `preflight.py`: a regra imprime as peças fora
  do hull mas não reprova (42 de 53 specs falhavam). Liga quando o teto de 25 % estiver calibrado por família.
  `checks_of(..., sheet=None)` recebe o sheet do `main`; `fit_spec` chama sem sheet e por isso não vê a regra.

### 19.D2 Melhor-de-N no estágio 1: `--variants N` (2026-10-27)
Papers: EdgeRunner 2024 (Fig. 15: a variância por seed é grande), Zhao 2026 (K variantes + curadoria), Begemann & Hutson 2026 (curadoria automática).
- **O que mudou.** `spec_pipeline.py --variants N` (default 1 = fluxo de antes). `author_specs` pede N specs ao autor em paralelo (threads; é a parte lenta); resposta que não vira spec é descartada e logada. `best_of_n` roda o estágio 1 (`stage_shape`: preflight + clay + silhueta) em cada um, em série (Blender), cada um em `variants/<k>/` com spec, clay, `sil/`, `views/`, `silhouette.json`. Vence a variante com maior `(estágio 1 ok, soma das margens)`; a margem é `sum(IoU_v - gate_v)` sobre as vistas de `silhouette.gates_for(rig)` (`margin_of`). O vencedor é copiado para a raiz do run, nenhuma variante é apagada. Repair/`--passes`, se ligados, rodam depois, só no vencedor, e o estágio 1 é medido de novo. `review.md` ganha `## Variants` (gates, IoU por vista, margem de cada uma, a escolhida marcada). A função `stage_one` saiu de `main` (complexidade).
- **Desvio do roadmap.** O desempate é `ok` antes da margem: uma variante que passa todos os gates ganha de uma que falha mesmo com soma maior (a soma deixa um IoU alto compensar uma vista abaixo do gate).
- **Prova (autor local `session:opus`, sem passes nem repair, `--shape-only`, uma rodada):** `runs/draft/n005/v5-variants-r1/` (variantes em `variants/{1,2,3}/`). Tempo: 89 s para pedir as 3 + preflight, 34 s para os 3 builds.

  | run | front / left / back / top / bottom / rts | gates | soma das margens | preflight |
  |---|---|---|---|---|
  | v4-oneshot-r1 (N=1) | .695 / .700 / .746 / .669 / .727 / .817 | 5/6 | +0.254 | PASS |
  | v5 variante 1 (escolhida) | .686 / .780 / .769 / .784 / .749 / .807 | 5/6 | +0.476 | FAIL |
  | v5 variante 2 | .703 / .718 / .792 / .751 / .714 / .760 | 5/6 | +0.338 | FAIL |
  | v5 variante 3 | .719 / .731 / .808 / .699 / .758 / .770 | 5/6 | +0.386 | FAIL |

- **Resultado.** O melhor de 3 tem IoU médio .766 contra .726 do one-shot (margem +0.476 contra +0.254): a variância existe e a escolha a pega. **Mas o gate da frente (.75) continua falhando nas 3** (.686-.719; o v4 tinha .695) e as 3 falham o preflight (`shoulder_span` .71-.73 contra .46 do sheet, `fist_span`; a variante 3 ainda `budget_split` e `overlap`), que o v4 passava. A margem em soma não enxerga o preflight, que só entra no desempate `ok`; como todas falham, a soma decidiu. N=3 numa rodada é uma amostra: não prova ganho no veredito, só no IoU médio. n00U não foi rodado (pedido só n005).
- **Custo.** N pedidos ao autor (3x créditos no modo API) e N builds de ~11 s. Fica default 1.
- Fora: pedir as N com temperatura/seed diferentes (o `ask_api` fixa 0.2; no modo `session` a variância vem do próprio modelo).

### 19.E1 Tempos e score ponderado (2026-10-27)
Papers: Begemann & Hutson 2026 (geração / integração / prontidão medidas à parte), Zhao 2026 (30 % tempo / 70 % qualidade).
- **`review.md`, `## Timing`** (segundos de parede): `t_gen` = pedir o spec (todas as N variantes) + preflight; `t_build` = Blender + render + silhueta (soma das N variantes); `t_passes` = repair e `--passes` (inclui os builds de teste deles); `t_colour` = estágio 2; e `passes: <n>` (nº de vistas de `--passes`).
- **`compare_runs.py`** lê essas linhas (`times_of`) e `silhouette.json` do run (`score_of`):
  `score = 0.3·f(t) + 0.7·g(IoU, zonas)`, `t = t_gen+t_build+t_passes+t_colour`, `f(t) = max(0, 1 − t/1200 s)`,
  `IoU` = média das vistas contra o sheet aprovado, `zonas` = média das vistas da média de zona, `/0.5` e teto 1;
  `g = IoU` sem zonas (run só de estágio 1), `g = 0.6·IoU + 0.4·zonas` com zonas. f e g são absolutos em [0, 1]: o score de um run não muda com os vizinhos. Aparece no cabeçalho de cada run do sheet (`score 0.803 (f 0.90 g 0.76, 123 s)`) e a lista ranqueada sai no stdout. Run sem `## Timing` (antes de 2026-10-27) ou sem IoU mostra `score n/a`.
- **Constantes escolhidas por mim** (o roadmap só dá 0.3/0.7): `T_MAX = 1200 s` (um run completo com autor `session` leva 3-10 min), `ZONE_FULL = 0.5` (hard-v1 fica perto de .37), pesos 0.6/0.4 de IoU/zonas. Mudar em `compare_runs.py`; os testes fixam a fórmula, não os números.
- **Prova:** `scratchpad/papers-d2e1/cmp.png`, `compare_runs.py ... v4-oneshot-r1 v5-variants-r1 --show clay` imprime `v5-variants-r1 score 0.803 f 0.90 g 0.76 123 s` e `v4-oneshot-r1 score n/a` (o v4 não tem tempos: não inventei).
- **Limite.** O score só ranqueia o que tem tempo gravado; os runs antigos não entram. O tempo do autor depende da máquina e da fila do `claude -p`, ruído entre runs. As zonas dos runs só de estágio 1 não existem, então um run só de forma e um completo não são comparáveis em g.

### 19.E2 CLIP render × concept (2026-10-27) - NEGATIVO, fora do fluxo

`tools/blender/clip_score.py` (open_clip ViT-B/32 OpenAI, CPU; ULIP 2023: CLIP como juiz cross-modal, média das vistas, vários
templates de texto). `clip_score.py <run_dir> --id <unit>` dá JSON: cosine render×concept (embedding médio das 6 vistas contra o
painel do concept da unidade), render×texto da card ("a low-poly render of X", "a Warcraft III unit, X", "a 3D game model of X";
X = nome na 1ª linha de `prompts/<id>/unit-<id>.txt`), top-k zero-shot entre as 7 unidades com sheet. Tudo reportado como
**pos − neg** (neg = média contra os concepts/textos das outras unidades). Vistas: `views/<id>/model-<v>.png` ou recorte do
`compare.png` 1440x1536 (os 9 compares 1536x2112 antigos ficam fora). `--correlate` roda a prova.

Prova (29 runs com `silhouette.json` e compare em grade, 7 unidades; saída em `scratchpad/papers-e2/correlate.json`):

| alvo | Spearman concept pos−neg | Spearman texto pos−neg |
|---|---|---|
| nº de vistas que passam o gate (0-6) | **+0.27** | −0.27 |
| IoU médio das 6 vistas | +0.27 | −0.25 |
| veredito PASS/FAIL | n/a (só 3 runs têm `verdict:` no review.md, todos PASS) | n/a |

Dentro de uma unidade (hfoo n=9, n01X n=5): concept +0.10 / +0.30, texto +0.02 / +0.30 (IoU). Top-1 zero-shot da unidade certa
(render × texto): 20 de 29 runs; rank 4-6 em 6 runs. Limiar do roadmap: Spearman ≥ 0.6. **Não atinge** (melhor 0.27), então o
script **não** entra no `review.md` e fica como experimento. O CLIP separa unidades (pos−neg do n01X hard-v1: concept +0.091,
texto +0.042, rank 1/7), mas não mede fidelidade de forma: renders low-poly de qualquer unidade ficam em cosine ~0.80-0.89 entre si,
e o gate de silhueta já captura o que o CLIP não vê. Texto negativo é esperado (nomes de raça/papel dominam, não a forma).
Teste: `test_clip_score.py` (embeddings stub, sem baixar pesos; o modelo roda só na CLI).

## 20. Leva 2 (2026-10-27)

Vinte itens (os que ficaram da leva 1 + o que a bateria v5 ensinou), 10 worktrees em paralelo, integrados em
`feat/models-v2-hard`. Estado por item em `ROADMAP-papers.md` ("Leva 2"). Bateria `v6` nas 3 unidades, autor
session:opus, tudo ligado por default (`--fit` com âncora, `--pair` contra o melhor v5; imagens em
`history/2026-10-27-v6/`):

| unidade | v5-fit | v6 (run final) | veredito | pareado v6 × v5 (sheet / artist) |
|---|---|---|---|---|
| n01X | .832/.802/.829/.840/.811/.796 | .787/.823/.787/.782/.833/.795 (`v6-r5`) | PASS, prototype-safe | v5 3-0 / v5 3-0 |
| n005 | .853/.826/.894/.746/.773/.864 | .823/.810/.870/.723/.774/.835 (`v6-r4`) | PASS, final-use | **v6 3-0 / v6 3-0** |
| n00U | .618/.569/.612/.630/.599/.610 | **.781/.686/.789**/.640/.620/.643 (`v6-r3`) | CHECK (top/bottom/rts) | v5 3-0 / v5 3-0 |

A bateria achou e corrigiu quatro bugs de integração (commits `1e49aea0`, `450cc6a4`, `65d71970`, e o dos gêmeos no
`fit_spec`): `--pair` não resolvia o nome do run irmão; `validate` media o chão pelo `at` (nos spans é offset) e
recusava o spec ajustado; `fit_accepted` recusava por 0.01 numa vista que já passava enquanto duas ganhavam 0.08
(agora soma das margens, deslize máximo 0.02); gêmeos .L/.R saíam com 1 passo de grade de diferença e `symmetry`
reprovava (o fit copia as dims). Os runs intermediários `v6-r1..r4` ficaram guardados.

### 20.E15 Arestas internas do hard sheet, facetas no brief, Chamfer no review (2026-10-27) - budget_split por saliência NEGATIVO, desligado

**O que mudou.** `silhouette.edges(path, mask)`: Sobel do luma suavizado (sigma 1), limiar relativo (30 % do percentil 99 do painel, então sombra mole fica de fora), menos um anel de 7 px na borda da máscara (o contorno não é aresta interna), fechamento de 1 px (a linha de tinta dá duas cristas). `edge_bands(hard, shoulder_frac)`: por faixa (cabeça acima do ombro, torso até o quadril, pernas, os mesmos cortes de `band_areas`) devolve `salience` (parcela dos pixels de aresta), `facets` (mediana de linhas de aresta cruzadas por uma linha de varredura, mais 1) e `direction` (vertical/horizontal/mixed, por abertura 9x1 vs 1x9 com razão 1.5). `measure` ganhou `shoulder_frac`. `spec_pipeline.facet_text` põe a linha `FACETS drawn on the hard sheet's front view ...` no `measured_text` (só biped); `make_brief` calcula as bordas do `args.build`. `silhouette.edge_chamfer/edge_report`: Chamfer entre `edges(hard)` e o `wire-<view>.png` do clay (ambos recortados na caixa da figura e ajustados ao mesmo canvas; melhor dos dois espelhos). Linha nova no review: `edge chamfer hard->wire (/H)` (= `drawn`: distância média de uma aresta desenhada à aresta de wire mais próxima), e `silhouette.json` guarda também `extra` (wire -> desenho; grande por construção, o wire traz a triangulação).

**Números (hard sheet).** Facetas por faixa (cabeça/torso/pernas): n01X 3/7/5, n005 5/7/5, hfoo 3/6/4. Salience: n01X 0.03/0.43/0.54, n005 0.21/0.37/0.42, hfoo 0.13/0.48/0.39. Direção: quase tudo `mixed` (as linhas fechadas dão quadros, 9x1 e 1x9 empatam); só a cabeça do n01X deu `horizontal`. Então "torso: 6 facetas verticais" do roadmap virou "torso: 7 facets" sem direção na maioria dos casos: a direção por abertura morfológica não separa.

Chamfer hard->wire por vista (front/left/back/top/bottom, /H do canvas) nos rebuilds sem LLM: n01X hard-v1 0.011/0.009/0.011/0.010/0.011 (extra 0.016-0.029); n005 v4-oneshot-r1 0.013/0.013/0.012/0.021/0.020 (extra 0.024-0.034); hfoo hard-v1 0.008/0.018/0.010/0.011/0.011 (extra 0.025-0.030). O wire é denso, então `drawn` é pequeno sempre; só vale como comparação entre runs de uma unidade (n005 top/bottom 2x as outras vistas: o desenho faceta onde o modelo não). Sinal, não gate. Silhueta de n01X hard-v1 no rebuild: 0.870/0.770/0.869, PASS (referência 0.875/0.771/0.874).

**budget_split com 50 % área + 50 % saliência: pior, ligado só por `preflight.SPLIT_SALIENCE = True` (padrão False).** Nos 49 specs biped de `runs/draft` com sheet (um spec por run; os 63 do glob incluem não-biped), FAIL do `budget_split`:

| pesos área / saliência / prior | FAIL (de 49) | n01X hard-v1 |
|---|---|---|
| 0.5 / 0 / 0.5 (atual) | 16 | passa |
| 0.5 / 0.5 / 0 (roadmap) | 45 | falha (head 10 % vs 0-12 %, legs 29 % vs 31-73 %) |
| 0.34 / 0.33 / 0.33 | 30 | passa |
| 0.4 / 0.2 / 0.4 | 26 | passa |
| 0.25 / 0.25 / 0.5 | 8 | passa |

Causa: densidade de aresta desenhada põe ~50 % nas pernas (tinta de bota e canela), mas pernas são cilindros e custam ~0.4x da área em tris; o prior fixo existe por isso. Com taxa de FAIL de 45/49 a regra nem poderia virar gate. A última linha (menos falhas) só alarga as faixas; não adotada sem evidência de que pega spec ruim. Mantido o comportamento antigo; `targets_from` já traz `edge_head/body/legs` quando o `sheet-hard.jpg` existe.

**Brief do n005 (linha nova).** `FACETS drawn on the hard sheet's front view (...): head: 5 facets; torso: 7 facets; legs: 5 facets.` Brief completo: `scratchpad/leva2-e15/brief-n005.txt`. Efeito sobre o autor não medido (sem LLM nesta rodada).

**O que piorou/ficou.** Sheet escuro sobre fundo escuro (casaco do n005) perde linhas: mapa de arestas esparso no torso; olhar `edges-n005.png`. Provas: `scratchpad/leva2-e15/edges-{n01X,n005,hfoo}.png` (linha 1 painel do hard sheet, linha 2 `edges`, linha 3 wire do clay, colunas front/left/back/top/bottom).

### 20.S5 Ruído entre runs iguais: `compare_runs.py --stability` (2026-10-27)
Paper: Sketch2Mesh 2021 (Chamfer como distância entre formas). `compare_runs.py --stability <run_a> <run_b>`: Chamfer 3D entre os
`clay.glb` (5000 pontos por GLB, triângulo sorteado por área, simétrico, em % da altura de A; `scipy.cKDTree`) e |ΔIoU| por vista do
`silhouette.json`. Só relatório. Medido (`clay.glb`, 3 unidades):

| unidade | par | Chamfer % H | \|ΔIoU\| média / máx | pior vista |
|---|---|---|---|---|
| n01X | v3-stages-r1 × r2 | 1.75 | .017 / .042 | top .042, left .039 |
| n01X | v4-oneshot-r1 × v5-oneshot-r1 | 1.50 | .014 / .026 | top .026 |
| n005 | v3-stages-r1 × r2 | 2.50 | .092 / .251 | left .251, rts .139 |
| n005 | v4-oneshot-r1 × v5-oneshot-r1 | 2.13 | .038 / .096 | left .096 |
| n00U | v3-stages-r1 × r2 | 3.58 | .053 / .109 | front .109, back .108 |
| n00U | v4-oneshot-r1 × v5-oneshot-r1 | 9.02 | .120 / .187 | left .187 |

Piso do estimador: o mesmo spec reconstruído (v5-oneshot-r1 original × rebuild) dá |ΔIoU| ≤ .005 (build e silhueta são
determinísticos) e Chamfer 1.1 / 1.3 / 2.3 % H (n01X / n005 / n00U): são duas amostragens independentes de 5k pontos, não diferença de
forma. Leitura: Chamfer abaixo de ~2 % H é o mesmo modelo. O ruído de geração (autor, mesma receita) é pequeno no n01X (média .015, vista
.04) e grande nas outras: n005 até .25 numa vista, n00U .11 (r1 × r2). Uma melhora de IoU numa vista abaixo de ~.05 (n01X) ou ~.10-.25
(n005, n00U) não prova nada com N=1; a média das 6 vistas precisa de ~.02 (n01X) ou ~.05-.09 (n005, n00U). Os pares v4 × v5 não são
"iguais": o v5 mudou receita (preflight, orçamento), então o .12 do n00U mistura ruído e efeito. Isso reforça `--variants` (§19.D2).
Teste: `test_mesh_lint.py::Protocol::test_chamfer_3d`.

### 20.S7 KB do atlas e texels por altura no Readiness (2026-10-27)
Paper: Begemann & Hutson 2026 (matriz técnica: orçamento de textura). `mesh_lint.lint` ganha `atlas_kb` (bytes do PNG embutido / 1024) e
`texel_per_height` (texel mediano em px por unidade de mundo × altura: pixels do atlas ao longo do modelo). Linha nova no Readiness:
`atlas KB / texels per height`. Só relatório. n01X v5-oneshot-r1: 10.2 KB / 206 (texel min/max 27/761). Clay: `- / -` (sem atlas).
Os KB são pequenos (atlas de células chapadas comprime bem); os texels por altura de um modelo celado dependem de `face_span` (§19.A1),
então não viram gate.

### 20.S6 `engine import`: o GLB pelo loader do jogo (2026-10-27)
O jogo carrega modelos com raylib (`LoadModel` + `LoadModelAnimations`, `UnitModels::LoadModelFiles`). `tools/glb_import_check.cpp`
(único arquivo, só raylib) faz as mesmas duas chamadas e valida como o jogo (malhas > 0, vértices > 0, clipes batem com o
esqueleto); janela oculta, porque o raylib sobe malha e textura na GPU (`LoadGLTF` chama `UploadMesh`). Saída por arquivo:
`ok meshes=N verts=V anims=A` ou `error <primeiro aviso do raylib>`; exit 1 se algum falha. `mesh_lint.engine_import(glb)` roda o
binário (`$GLB_IMPORT_CHECK`, `build/glb_import_check` do CMake, `make glb-check`; na falta, compila uma cópia em `$TMPDIR` com
`c++` + `pkg-config raylib`, ~1 s) e vira a linha `engine import` do Readiness; sem compilador/raylib/janela: `n/a (...)`.
Custo ~0.4 s por GLB, então roda sempre (sem `--engine-check`). Só relatório, não muda status.
Prova (v5-oneshot-r1 reconstruído): n01X `ok meshes=6 verts=1181 anims=7`, n005 `ok meshes=1 verts=877 anims=7`, n00U `ok meshes=1 verts=874 anims=5`;
arquivo ausente: `error FILEIO: ... Failed to open file`; lixo: `error MODEL: ...`.
Não verificado: o alvo CMake (`glb_import_check` dentro do `CF_BUILD_GAME`) e `make glb-check`: o configure baixa dependências (FetchContent)
e não rodei aqui; o binário de prova veio do caminho `c++`. Teste: `test_mesh_lint.py::Protocol::test_engine_import_lines` (binário falso).

### 20.M10 `mesh_lint.py --decimate`: o que os triângulos compram (2026-10-27)
Paper: Chen 2023 (malha baixa por simplificação). `tools/blender/decimate_glb.py` (Blender, DECIMATE collapse 0.5 em cada malha, pose de
repouso, sem clipes) + `mesh_lint.decimate_loss`: mede a IoU média (silhouette.py, mesmas vistas) do GLB e do decimado, e devolve
`lost_per_100_tris = 100 * (IoU antes - IoU depois) / tris removidos`. CLI: `mesh_lint.py <clay.glb> --decimate <sheet.jpg> [--rig]`; no
pipeline, `spec_pipeline.py --decimate` põe a linha `IoU lost per 100 tris (decimate 50 %)` no Readiness (~8 s, opt-in). Só relatório.

| unidade (v5-oneshot-r1, clay) | tris | IoU média | IoU perdida por 100 tris |
|---|---|---|---|
| n01X | 632 -> 316 | .790 -> .745 | **0.0141** |
| n005 | 740 -> 370 | .761 -> .751 | 0.0026 |
| n00U | 556 -> 278 | .364 -> .356 | 0.0028 |

Leitura: o n01X usa os triângulos (perde .045 ao cortar metade); n005 e n00U perdem ~.01 com metade dos triângulos, ou seja, boa parte do
orçamento deles não aparece na silhueta (n00U está longe do gate por outro motivo, §19). Não há limiar: sem gate. Limite: a decimação
colapsa arestas sem olhar o sheet, e a IoU só vê o contorno (o que some dentro dele não conta).

Arquivos da prova: `scratchpad/leva2-s5/{n01X,n005,n00U}/review.md` (Readiness com as linhas novas), `*.log`.


### 20.S4 `review_pair.py`: review pareado de visão (2026-10-27)

**O que mudou.** `tools/blender/review_pair.py <runA> <runB> --id <unit>`: por voto, uma imagem de 2 linhas (front, rts) com 3
células `candidato | painel do sheet aprovado | candidato`; textured (`model.glb`) se as duas runs têm, senão clay (lit). Os
renders saem do GLB das runs (os `views/` não ficam nos runs commitados) com a câmera rts do `silhouette.json` de cada uma. O
reviewer (`spec_pipeline.ask`, `session:opus`, lê a imagem com Read) responde JSON: `sheet` (parece o sheet) e `artist` (parece
feito por artista), left/right + 1 frase cada. 3 votos, lados A/B embaralhados (sempre as duas ordens), maioria por eixo; resposta
inválida é pedida de novo uma vez. Grava `<runB>/pairwise.json` (votos, frases, imagens em `pairwise/`) e uma linha no
`review.md`: `pairwise vs <runA>: sheet A 2-1, artist B 3-0`. Gancho: `spec_pipeline.py ... --pair <run-anterior>` (default: nenhum)
roda o review da run nova (B) contra a anterior (A), escreve a linha no `review.md` e **rebaixa o `status` um nível** (final-use ->
prototype-safe -> placeholder -> rejected) se A vencer os 2 eixos; o veredito não muda. Teste: `test_review_pair.py` (reviewer stub).
Por quê: S4 + N5 do roadmap (juiz de visão pareado em vez de nota absoluta; MeshGPT 2024 avalia por preferência pareada em
forma x triangulação).

**Achado: viés de posição.** Na primeira bateria, o reviewer escolheu o candidato da ESQUERDA em 3/3 votos nos dois eixos no n005,
e na esquerda em 3/3 no eixo artista do n00U; com 3 votos e ordem 2+1, isso vira "A 2-1" que é só posição. Regra nova: eixo cujos
votos pegaram todos o mesmo lado físico = `tie (position bias)`. Sem essa regra o n00U sheet saiu "A 2-1" numa leitura e "B 3-0" nas
outras.

**Medida** (A = v4-oneshot-r1, B = v5-fit; 2 repetições cada com o código final, renders e ordem fixos, só o reviewer varia;
`.../scratchpad/leva2-s4/runs/<id>/<B>/final-rep{1,2}.json`, imagens em `work-<id>/vote*.png`):

| unidade | B | modo | rep 1 | rep 2 |
|---|---|---|---|---|
| n005 | v5-fit-r3 | clay | sheet tie 2-1 (viés), artist tie 2-1 (viés) | idem |
| n01X | v5-fit-r1 | textured | sheet B 3-0, artist B 3-0 | sheet tie 2-1 (viés), artist B 3-0 |
| n00U | v5-fit-r2 | clay | sheet B 3-0, artist tie 2-1 (viés) | sheet B 2-1, artist tie 2-1 (viés) |

Estabilidade: nenhuma repetição trocou o vencedor (A <-> B); só caiu de B para tie. As 3 repetições de um mesmo voto concordam
(3-0) só no n01X artist e n00U sheet (1ª leitura); o resto é 2-1. Leitura: v5-fit > v4 no n01X (textured, forte) e no n00U na forma;
n005 sem sinal (clay, o reviewer escolhe sempre a esquerda). Nenhum par perde os 2 eixos, então o gate não rebaixaria nenhuma das 3.

**O que piorou / limites.** Clay-vs-clay dá sinal fraco (n005, n00U artist): o reviewer não vê cor nem detalhe. 3 votos com ordem
2+1 não cancelam o viés de posição; a regra só o detecta, não corrige (4 votos 2+2 seria o passo seguinte, custo +1 chamada).
Custo: 3 chamadas `claude -p` em paralelo, ~30 s por par. O gate é opt-in (`--pair`) e só rebaixa status; não bloqueia a run.

### 20.N4 Sheets top/bottom ortográficos (2026-10-27) - NEGATIVO, sheets antigos continuam o default

**O que mudou.** `redo_topbottom.py <id> --race R --name N [--sheet sheet.jpg]` + `prompts/00-template-topbottom.txt`:
copia o sheet para `refs/<id>/old/` (nunca sobrescreve), pinta a fileira de baixo de cinza, manda o resto ao
`nano-banana-2-1-edit` (mesma chave/endpoint do `generate.py`) pedindo só os dois painéis de baixo como plantas
ortográficas ("câmera exatamente acima/abaixo, sem perspectiva, sem inclinação, mesma pose e escala") e cola só a
fileira de baixo da resposta sob a fileira de cima original. Custo: ~$0.004 por chamada (6 chamadas, sem erro de API).
Sem a pintura da fileira, o modelo devolve o sheet inalterado (diff médio 1.5/255): a primeira tentativa não mudou nada.
Os sheets novos ficam em `refs/<id>/sheet-ortho.jpg` (opt-in); `sheet.jpg` voltou ao original.
O template de 5 painéis (`00-template-unit.txt`) não foi alterado: o prompt já dizia "orthographic".

**Medida** (clay do melhor run v5 de cada unidade, `silhouette.py --shape`, IoU top/bottom @ tilt escolhido; meta tilt 0 ± 5):

| unidade (clay) | antes top / bottom | v1 (prompt ortográfico) | v2 (+ "planta, não frente virada") |
|---|---|---|---|
| n01X v5-fit-r1 | .840 @10 / .811 @20 | .572 @20 / .741 @40 | .653 @20 / .819 @10 |
| n005 v5-fit-r3 | .746 @-30 / .773 @30 | .767 @-20 / .769 @30 | .789 @-10 / .731 @30 |
| n00U v5-fit-r2 | .630 @-30 / .599 @10 | .554 @0 / .568 @20 | .528 @-30 / .597 @30 |

Tilt dentro de ±5: antes 0/6, v1 1/6, v2 0/6. IoU melhora em 1 de 6 células no v1 (n005 top) e em 2 de 6 no v2 (n005 top, n01X bottom), piora
nas outras; o n01X top cai de .84 para .65. Imagens (antigo / v1 / v2, só a fileira de baixo):
`history/2026-10-27-n4/<id>-bottom-row-old-v1-v2.jpg`; sheets completos em `refs/<id>/old/` (antigo, v1) e `refs/<id>/sheet-ortho.jpg` (v2).

**Por quê não funcionou.** O modelo de imagem não sabe projetar: redesenha o frontal "visto de cima" com inclinação
(n01X: braços e punhos longos, rodas à vista) e ainda piora o que já era certo (a aranha antiga já era uma planta verdadeira;
a nova mostra a cabeça de frente). O tilt que o sweep acha também mede o desacordo modelo × desenho, não só a câmera do
desenho: com a aranha já ortográfica ele escolhe -30. Não foi regenerado `sheet-hard.jpg` (sem ganho no judge, sem motivo).
**Próximo passo se importar:** derivar top/bottom do modelo (render ortográfico do clay aprovado como referência de
imagem-para-imagem) em vez de pedir ao modelo de imagem a projeção; ou calcular o tilt do sheet e aplicá-lo na câmera.
Teste: `test_redo_topbottom.py` (corte na faixa vazia entre as fileiras, sem API).

### 20.L13 Massing de edifício por hull: `building_hull.py`, `--hull` (2026-10-27)
- **O que.** `building_hull.py` lê as máscaras front e left do sheet de edifício (`concept_panels`, layout building), tira as pontas finas (linhas/colunas com < 75 % do pixel count da mais cheia, nas duas pontas: chaminé, rampa, trilhos, braço de guindaste, telhado mais estreito), traça o contorno, Douglas-Peucker (eps 2 % da altura do corpo), snap H/V (10°), arestas < 6 % da altura viram canto reto, vértices colineares saem. Resultado: uma peça `["body","box",dims,at,"hull",{"cut":"sheet","hull":{"front":..,"left":..}}]` em metros, pés em y=0, x/z centrados. Caminho de build é o do `cut_hull`/`cut_part` (extrude front ∩ extrude left, BOOLEAN EXACT) mais `DECIMATE` DISSOLVE 1° (faces coplanares, 12-28 tris). `cut_hull.hull_cut` usa os contornos como estão (sem sheet); `preflight.part_tris` usa `hull.tris`.
- **Fluxo.** CLI: `python3.14 tools/blender/building_hull.py <sheet> <out>` grava `hull-spec.json` (spec parcial), `hull.glb` (clay) e `hull-iou.json`. `spec_pipeline.py --kind building --hull`: constrói o hull em `<out>/hull.glb`, o brief ganha "BASE VOLUME, READY ... do NOT recreate it", e a peça é inserida em toda spec do autor (`with_hull`, idempotente com `--spec`). Teste de registro: `tests/tools/blender/test_building_hull.py`.
- **Paper.** Sano 2026 §3.4-3.5 (contorno regularizado, visual hull); Gao, Wu, Pan 2022 (edifício como massa ortogonal de faces planas).
- **Medida sem LLM (hull sozinho; IoU pelo mesmo `best_match` do gate; provas em `scratchpad/leva2-l13/{h09B,h05X}/hull-iou.json`).** Só há dois edifícios com sheet (h09B, h05X). O sheet do h05X não segue o 3+2 (2+1+2, legendas dentro da máscara): `concept_panels` erra o corte; a prova usou os 5 painéis recortados e remontados no layout 3+2 (`scratchpad/leva2-l13/h05X-reflow/sheet.jpg`).

| edifício | hull (m) / tris | IoU front/left/back/roof, hull | idem, 1 box do bbox | hull vs corpo do sheet (sem pontas) |
|---|---|---|---|---|
| h09B | 4.13x3.41x4.32 / 16 | 0.794 / 0.729 / 0.856 / 0.726 | 0.714 / 0.783 / 0.756 / 0.853 | 0.992 / 0.994 / 1.000 / 0.995 |
| h05X | 5.92x3.02x6.64 / 12 | 0.818 / 0.596 / 0.772 / 0.624 | 0.800 / 0.621 / 0.800 / 0.916 | 0.980 / 0.978 / 0.948 / 0.557 |

  O hull traça o corpo com fidelidade (0.98-1.00), mas contra o sheet inteiro (props incluídos, bbox normalizado) não bate uma caixa simples em left/roof: ele descarta de propósito rampa, trilhos e braço, e o bbox do sheet os conta. No h05X o roof 0.557 é inconsistência do próprio sheet (a profundidade do left, 350 px, não bate com a da planta, ~215 px): o hull confia em front x left. Os dois edifícios são caixas quase puras, então o teste do contorno não-retangular é sintético (`test_building_hull.py`, L e torre).
- **Medida com LLM (session:opus, 1 amostra por braço, h09B, `--shape-only --no-repair --no-rts`; runs em `runs/draft/h09B/leva2-l13-base` e `leva2-l13-r1`).**

| braço | partes | tris GLB | IoU front/left/back | estágio 1 |
|---|---|---|---|---|
| sem hull | 28 | 752 | 0.746 / 0.918 / 0.809 | FAIL (front < 0.75; preflight budget) |
| `--hull` | 24 | 628 | 0.823 / 0.777 / 0.860 | silhueta PASS; FAIL só no preflight budget (468 estimado vs 600-800) |

  n=1: a variância do autor é maior que a diferença. O ganho é front/back e menos tris; o left piorou (o autor sem hull desenhou o braço do guindaste e a plataforma sobre a lateral).
- **Piorou / pendente.** Um volume de duas vistas ignora pisos mais baixos e alas (a "ponta fina" também leva uma ala baixa: o autor tem de recolocá-la). O estimador do preflight conta caixa chanfrada abaixo do GLB (468 vs 628): vale para as duas runs. Pulado: QEM (`-> skipped: QEM, add when hull > 1/4 do orçamento`; dissolve basta com 12-28 tris), `hull` como kind no DSL (a peça é box + `cut`, nada muda no schema). Falta rodar nos 53 specs; os dois sheets de edifício são o que existe, mais sheets de edifício antes de decidir `--hull` como default.

### 20.M8 Faces nunca vistas: `cull` (2026-10-27) - relatório sempre, remoção opt-in

`tools/blender/cull.py` (novo, chamado por `build_unit.py` com `sibling("cull")`). Argumento `cull` no `build_unit.py`: depois do
join (e do `clean`), antes de `morph`/`atlas_uvs`/`texturize`, atira raios ortográficos, um por pixel (192 px no maior lado), em
12 vistas (4 laterais a 0°, 4 laterais a 45°, topo, fundo, 2 diagonais por baixo) contra um BVH da malha; a face atingida é "vista".
É a mesma resposta de um render-ID (uma cor por face, sem sombra), sem motor de render: 0.8 s por unidade. Grava `cull.json` ao
lado do GLB (`visible_tris`, `total_tris`, `visible_faces`, `total_faces`, `rays`, `removed`) e imprime `cull: 534/620 tris visible`.
`cull=remove` apaga as faces não vistas e os vértices soltos (`bmesh.ops.delete`); os grupos de vértice ficam nos vértices que
sobram e os UVs nascem depois (`atlas_uvs` lê só as faces que restam), então peso e atlas não são tocados.

`spec_pipeline`: o estágio 1 sempre passa `cull` ao build; `review.md` ganha a linha `visible tris | 540/620 (87%), kept (--cull removes)`.
`--cull` passa `cull=remove` (default desligado). Só o build final do estágio 1 mede; os trials de repair/passes não (ficam rápidos).

Medida (specs existentes, clay, mesmos args do estágio 1; saída em `scratchpad/leva2-m8/{n01X,n005}/{base,cull}`):

| unidade (run) | tris | visíveis | com `--cull` | IoU 6 vistas (front/left/back/top/bottom/rts) |
|---|---|---|---|---|
| n01X hard-v1 | 620 | 540 (87 %) | 540 | idêntico nas 6 (0.870/0.770/0.869/0.803/0.781/0.789, Δ 0.0000) |
| n005 v5-fit-r3 | 704 | 577 (82 %) | 577 | idêntico nas 6 (0.853/0.825/0.894/0.746/0.774/0.865, Δ 0.0000) |

Textura cel (`build_unit ... tex style=cel`, render_unit 5 vistas, pixels que diferem > 8/255): n01X 0.000-0.031 %, n005 0.000-0.002 %;
`mesh_lint`: 1 skin, 1 imagem, `uv_out_of_range` igual ao sem cull (0 e 1). n01X 620 -> 534 tris texturizado, n005 584 -> 497.
Os números do build do estágio 1 e do standalone diferem um pouco (540 x 534) porque o estágio 1 inclui o `cuts=` do hull.

O que piorou / limite: nada na silhueta nem na cor. O raio tem pixel de ~1 % de H: uma face menor que isso pode ser marcada
escondida sem ser (a remoção é opt-in por isso). Costas de face contam como vistas (sem back-face culling), então uma face
visível só por dentro de um oco fica. Faces escondidas são 13-18 % dos tris nas duas unidades: espaço de orçamento para o autor,
mas hoje o orçamento do preflight conta tris antes do cull, então `--cull` encolhe o GLB para baixo do que o autor planejou
(n005: 704 -> 577); se cair abaixo do piso de tris (400) o gate `tris` reprova, por isso fica fora do default.
Papers: nenhum da lista identificado para este item (técnica padrão de ID buffer / visibilidade por raio).

### 20.M12 Decimate do `union` com tolerância de tela (2026-10-27) - NEGATIVO, opt-in `toldec`

`cull.decimate_union(obj, budget_faces, tol=None, blind=True)`: o ramo `union` do `build_unit` chama `union_decimate`. `blind` (default,
o comportamento de antes): COLLAPSE até `budget//2` faces. `toldec`: bisseção (8 passos) no ratio do COLLAPSE sobre cópias; para no
menor ratio cuja distância máxima, dos vértices e centróides de triângulo do resultado à malha pré-decimate (BVH `find_nearest`), fica
em `d = H/32`; se isso ainda estoura o orçamento, o orçamento vence. A distância do resultado é medida e impressa nos dois modos
(`union decimate: {...}`). Centróide de triângulo e não centro de polígono: o centro de um n-gono côncavo cai fora da própria superfície
(a primeira versão media 0.185 numa malha sem decimar).

Medida (union, clay, IoU contra `sheet.jpg`, 6 vistas front/left/back/top/bottom/rts; orçamento 700 e 1600):

| unidade | modo | tris | dev (H/32 = tol) | IoU |
|---|---|---|---|---|
| n01X hard-v1, orç. 700 | blind | 683 | 0.017 (tol 0.081) | .875/.769/.873/.801/.779/.786 |
| | toldec | 358 | 0.061 | .862/.791/.862/.799/.778/.769 |
| n01X, orç. 1600 | blind | 1588 | 0.011 | .872/.768/.870/.800/.781/.782 |
| | toldec | 219 | 0.078 | .837/.783/.836/.777/.777/.764 |
| n005 v5-fit-r3, orç. 700 | blind | 708 | 0.007 (tol 0.085) | .855/.820/.896/.736/.741/.865 |
| | toldec | 284 | 0.079 | .823/.788/.841/.725/.735/.876 |
| n005, orç. 1600 | blind | 1634 | 0.001 | .856/.820/.896/.736/.742/.864 |
| | toldec | 284 | 0.079 | idem a 700 |

Leitura: o decimate cego ao orçamento já fica dentro de H/32 (desvio 0.001-0.017, 2-20 % da tolerância), então a tolerância
de tela nunca é o limite ativo no orçamento; sozinha ela só deixa a malha cair para 220-360 tris, abaixo do piso 400 do gate `tris`,
e perde IoU (front -0.013 a -0.035, back -0.011 a -0.055, rts -0.017). Dois lados: left de n01X sobe (+0.022) e rts de n005 sobe (+0.011);
a média das 6 vistas cai em todos os casos. H/32 (~3 % da altura) é folgado demais para a silhueta, que pena desvios de ~1 %.
Fica `blind` como default; `toldec` só serve para medir quantos tris a unidade "precisa" (a coluna dev do blind já responde:
o orçamento está folgado em geometria, apertado em leitura). Se voltar a tentar: tolerância H/128 e piso de faces por orçamento.
Papers: Garland, Heckbert 1997 (o COLLAPSE do Blender é quadric error metrics; aqui só se mede o erro do resultado).

### 20.N3 Zonas de cor no estágio 1: render "ID" do clay (2026-10-27)

**O que mudou.** O clay é cinza de um material só, então a pergunta "a peça do material X está onde o sheet tem a cor X?" só
aparecia no estágio 2 (depois da textura). Agora o estágio 1 reconstrói o mesmo spec **sem `clay` e sem `tex`** (`sil/ids/ids.glb`:
um material chapado por slot, na cor da `palette` do spec, mesmos cortes) e mede as zonas desse render contra o sheet:
`spec_pipeline.zones_clay` -> `silhouette.py --ids` -> `silhouette.ids_zones` -> `zone_views` (as mesmas `zone_*` do estágio 2,
sem código novo de zona) -> `render_silhouette.py ... ids` (só os tiros `zone`, front/left/back/top/bottom nos tilts do estágio 1).
O mapeamento material -> cor é a própria paleta do spec (o autor a tira do sheet); o k-means de zonas do sheet faz o resto.
Saída: `silhouette.json["zones_clay"] = {view: {mean, cover, lost}}`, linhas `zones_clay mean/cover (report)` no review.md e
`sil/ids/zones_clay.json` completo (zonas e peças). **Só relatório**: `ZONES_CLAY_BLOCKING = False`; falha de build/medida vira `{}`.
Custo: um build Blender (~2 s) + 1 render (~4 s) por estágio 1. O clay, o veredito e o `silhouette.json` antigo não mudam.

**Calibração (sem LLM, spec guardado de cada run; `scratchpad/leva2-n3/table.json`, `all53.json`).** mean/cover, limiares do
estágio 2 (0.08 / 0.30), tilts do `silhouette.json` do run:

| run | front | left | back | top | bottom |
|---|---|---|---|---|---|
| n005 v5-fit-r1 | 0.49/0.80 | 0.58/0.81 | 0.59/0.86 | 0.37/0.62 | 0.42/0.65 |
| n005 v5-fit-r2 | 0.62/0.89 | 0.56/0.81 | 0.67/0.93 | 0.40/0.68 | 0.29/0.52 |
| n005 v5-fit-r3 | 0.62/0.88 | 0.56/0.82 | 0.70/0.95 | 0.40/0.68 | 0.28/0.52 |
| n005 v5-oneshot-r1 | 0.52/0.83 | 0.52/0.78 | 0.55/0.85 | 0.08/**0.26** | 0.28/0.51 |
| n005 v5-variants-r1 | 0.50/0.85 | 0.58/0.81 | 0.25/0.51 | 0.16/0.33 | 0.24/0.46 |
| n00U v5-fit-r1 | 0.16/0.34 | 0.15/0.31 | 0.16/**0.29** | 0.29/0.54 | 0.04/**0.15** |
| n00U v5-fit-r2 | 0.16/0.39 | 0.10/0.30 | 0.18/0.35 | 0.16/0.33 | 0.05/**0.18** |
| n00U v5-oneshot-r1 | 0.08/**0.19** | 0.13/0.31 | 0.05/**0.15** | 0.12/0.30 | 0.20/0.43 |
| n01X v5-fit-r1 | 0.47/0.85 | 0.40/0.76 | 0.49/0.83 | 0.29/0.66 | 0.30/0.63 |
| n01X v5-oneshot-r1 | 0.39/0.71 | 0.33/0.65 | 0.41/0.70 | 0.28/0.61 | 0.16/0.36 |

**Prova n005 v5-fit-r3.** No front, a zona cinza do sheet (placa da máscara, `#5D6568`) tem duas peças com cover **0.00**
(`@43,25` = rosto, `@59,30`): o clay pinta o capuz (material `coat`, escuro) por cima da zona da cabeça, e a peça da máscara
só aparece como retângulo pequeno dentro do capuz (`sil/ids/ids-zone-front.png`). Zona cinza no front: IoU 0.03 (share 0.14);
a escura (`coat`+`trousers`) 0.72. No left a mesma zona tem cover 0.00 em `@53,19` e `@59,29`. O número agregado (front 0.62/0.88)
esconde isso, as peças mostram.

**Decisão: relatório, não gate.** Com os limiares do estágio 2 em todos os 63 specs guardados (top/bottom em tilt 0 quando o
run não tem `silhouette.json`): 17/63 runs falham em alguma das 5 vistas (27%), 9/63 só em front/left/back; por vista front 2,
left 5, back 6, top 8, bottom 10. Mas nos 10 runs v5 (a geração atual, tilts reais) falham 4/10 = 40% (n00U 3/3, n005 oneshot
no top), acima de 1/3, e o n00U (aranha, preto/marrom quase sem contraste entre zonas) falha por zona ambígua, não por forma. Fica
como `*_BLOCKING = False` até haver mais runs v5 e uma calibração por rig. Limite honesto: o ID usa a `palette` do spec, então
uma paleta com cores do sheet trocadas entre materiais mede a paleta, não a peça; e as vistas top/bottom são as mais ruidosas
(clay sem cor distinta nas costas e solas).

Testes: `test_spec_pipeline.test_zones_clay_rows_and_failed_build` (linhas do review + build falho vira `{}`); `ids_zones` roda
Blender, provado nas CLI acima. Sem referência nova em `docs/references.md` (reusa as `zone_*`, já registradas).

### 20.N12 Conexão na malha e fit com âncora (2026-10-27) - regra nova só relatório, fit mais curto
- **O que mudou:**
  - `preflight.overlaps(a, b, k)` / `floating_parts(parts, parents, k)` comparam as caixas encolhidas a `k` do tamanho
    (centro fixo). A regra `overlap` continua em `k = 1` (gate). Regra nova `overlap_80` (`k = OVERLAP_SHRINK = 0.8`),
    **só relatório** (`OVERLAP_BLOCKING = False`).
  - `build_unit.attach_report`: depois de montar as peças e antes do join/union, BVH (`BVHTree.FromPolygons` em
    coordenadas de mundo; `FromObject` fica no espaço local da peça e dava 19 soltas de 24 num spec ligado) de cada peça
    contra as outras no osso dela e no osso pai; peça sem cruzamento é solta. Grava `attach.json` ao lado do GLB do run
    (`clay.glb`/`model.glb` -> `attach.json`; trial -> `<nome>-attach.json`): `{"parts": n, "loose": [{part, bone,
    parent}]}`. Nunca aborta: erro vira `"error"` no JSON.
  - `fit_spec`: dims +-10 % (era 20), `at` +-0.03 H (era 0.05); partes dos ossos spine/pelvis/body/abdomen e a maior
    peça do osso head (capuz/elmo) só encolhem em x/z (limites do scipy; `HORIZONTAL` diz quais dims são x/z por tipo);
    a âncora: o conjunto de ossos soltos a 80 % não pode crescer (restrição dura, custo 10 +1 por osso) e cada osso solto
    custa `LOOSE_W = 0.3` no objetivo, então o fit pode reconectar. O fit guarda o melhor ponto avaliado (Powell com
    cliffs de penalidade terminou 12.0 > start 0.87 no n00U r2). A ordem em `stage_one` não mudou (fit depois do repair).
- **Taxa de FAIL do `overlap_80` nos 63 specs de `runs/draft/*/*/spec.json`** (o roadmap dizia 53; hoje são 63):
  `overlap` (k = 1) 3/63 = 5 %; `overlap_80` **48/63 = 76 %** (gate só abaixo de 1/3). Caixa de eixo é proxy ruim para
  peça rotacionada ou `from/to`: o fêmur/`forearm` encosta de verdade e a caixa a 80 % não vê. Fica relatório; a
  verdade é o `attach.json` (BVH). Pior: spider `leg*.upper`/`leg*.lower` (n00U v5-fit-r1: 12 ossos), `forearm.*` do
  hfoo, `spine` de todo n005/n01X.
- **Prova sem LLM** (`fit_spec` a partir de `runs/draft/<id>/v5-fit-r*/fit/before.json`, depois
  `spec_pipeline --spec ... --no-repair`; saídas em `scratchpad/leva2-n12/refit-*`). Colunas por vista:
  antes do fit | run guardado (fit antigo) | refeito (Δ vs guardado), front/left/back/top/bottom/rts:

  | run | front | left | back | top | bottom | rts | soltas no attach.json |
  |---|---|---|---|---|---|---|---|
  | n00U r1 | .281 / .365 / .329 (-.036) | .351 / .396 / .372 (-.023) | .285 / .367 / .333 (-.034) | .580 / .601 / .597 | .608 / .620 / .617 | .558 / .581 / .569 | guardado 10, refeito 6 (as 6 já estavam no before) |
  | n00U r2 | .395 / .618 / .462 (-.156) | .479 / .569 / .507 (-.062) | .390 / .612 / .456 (-.156) | .590 / .630 / .587 (-.043) | .608 / .599 / .613 | .575 / .610 / .579 (-.032) | guardado 10, refeito 2 (as 2 já estavam no before) |
  | n005 r1 | .719 / .714 / .824 (+.110) | .799 / .839 / .812 (-.027) | .797 / .734 / .889 (+.155) | .766 / .694 / .765 | .783 / .738 / .767 | .745 / .832 / .804 (-.028) | 0 / 0 |
  | n005 r2 | .735 / .846 / .803 (-.043) | .796 / .830 / .834 | .792 / .891 / .863 (-.028) | .711 / .744 / .726 | .796 / .775 / .811 | .760 / .864 / .850 | 0 / 0 |

  O `spec.json` guardado do n00U v5-fit-r2 reconstruído dá 10 soltas de 24 (as pernas `lower` e 2 `upper`): o fit antigo
  ganhou front/back +.22 soltando as pernas do pai. O n005 v5-fit-r3 reconstruído: 0 soltas de 26.
- **O que piorou / limites:** o critério "IoU não cai mais que 0.03 vs o run guardado" **não fecha no n00U** (r1 -.036,
  r2 -.156 em front/back) nem no n005 r2 front (-.043): o ganho guardado vinha de mover além do limite e de soltar a
  peça do pai, e os limites novos (10 % / 0.03 H) o proíbem. Com 5 % de custo por osso solto (`LOOSE_W` 0.05) o n00U r2
  saía igual (.449/.503/.443), com 0.3 reconecta 2 ossos a mais sem perder IoU. "Zero soltas" vale para o n005; no n00U
  as 6 (r1) e 2 (r2) pernas `upper` soltas já vêm do spec do autor (o `overlap` do preflight acusa 4 no r1) e o fit só
  não piora: reconectar de verdade é trabalho do repair. O attach usa BVH real, o fit usa caixas a 80 %: o conjunto de
  caixas soltas (n00U r2: 4) é maior que o de BVH (2).
- Papers: Wiersma 2026 (restrição dura, agora também a ligação com o pai), Sketch2Mesh 2021 (só onde o contorno falha).

### 20.L14 Rig spider medido do sheet (2026-10-27)

Sem paper novo: é o estágio de medição do §19 (Sano 2026: números do sheet no brief) aplicado ao esqueleto. A bateria v5
mostrou o rig fixo como causa no n00U: corpo pequeno e pernas longas e finas, ~2x o comprimento do sheet na mesma altura.
- **`silhouette.measure_spider(sheet)`** (frações da altura H da vista front): `body_r` e `body_len` (top, com as pernas
  abertas fora por `binary_opening`; o painel top é calibrado pela largura da abertura das pernas, igual no front), `body_under`
  (barriga sobre o chão, no back, onde as presas não pendem), `knee_h`/`knee_r` (linha mais larga do front entre a casca e os
  pés), `foot_r` (meia largura nos pés). n00U: .323/.853/.238/.172/.578/.580. n01N: .182/.869/.382/.465/.672/.438.
- **`rig_families.scale_spider(family, m)`** troca `FAMILIES[spider|spider_high]` por um esqueleto feito dessas medidas
  (mesmos ossos e nomes; topo fixo em `SPIDER_H` = 0.74 m, o H da medida; joelho nunca abaixo de metade da barriga, porque as
  pernas que alargam em linha reta não mostram joelho). Sem sheet a tabela fixa continua; `--fixed-rig` força a fixa.
- **Fluxo:** `set_rig(family, measure)` (spider, sem `--fixed-rig`) escala o rig, `parse_spec` grava `rig_measure` no
  `spec.json`, `build_unit.load_family` re-escala no Blender (rebuild reproduzível). O brief ganha `SPIDER BODY (...)` em
  `measured_text` com os números em H e em metros, e o `RIG_TEXT` fixo (joelho "y 1.15") dá lugar a "siga a tabela".
- **Preflight (relatório primeiro):** `spider_body`, `spider_reach`, `spider_leg` comparam o spec com `rig_measure`
  (banda 0.7-1.4x). Taxa de FAIL nos 15 specs spider de `runs/draft/*/*/` (os outros 38 não são spider): `spider_leg` 3/15
  (bloqueia: pega v5-oneshot-r1/v5-fit-r1, pernas 1.43-1.48x, e n01N v2-hard-r2), `spider_body` 7/15 e `spider_reach` 11/15
  (> 1/3, só relatório; a maioria dos specs antigos tem altura 1.1-1.3 m, não 0.74).
- **`rig_remap.py`** (prova sem LLM): as peças ficam em coordenadas de modelo, não relativas ao osso, então o rig novo
  **não** as move. O script leva cada peça de perna do osso fixo para o osso escalado (mesma fração, mesmo desvio) na altura do
  próprio spec; corpo/cabeça/abdômen ficam. Teste em `test_rig_remap.py`.

Prova (clay, 6 vistas, front/left/back/top/bottom/rts; baseline = mesmo spec com `--fixed-rig`; baseline n00U v5 reproduz o
v5 do §19 .254/.368/.257/.411/.404/.490):

| spec | rig fixo | rig medido (pernas remapeadas) |
|---|---|---|
| n00U v5-oneshot-r1 | .254/.368/.257/.411/.404/.490 | **.630/.585/.636/.579/.592/.627** |
| n00U v4-oneshot-r1 | .400/.554/.394/.513/.531/.516 | **.616/.596/.620/.557/.595/.575** (top/rts pioram) |
| n01N v2-hard-r2 | .502/.452/.506/.361/.486/.474 | .417/.475/.394/.354/.351/.354 (**pior**) |

O n01N piora porque o corpo do spec antigo (1.29 m, barril longo) é o erro dominante; o remap só mexe nas pernas. Não é
prova contra o rig: é prova de que o remap não conserta o autor. Comparar em `scratchpad/leva2-l14/{l14-v5,l14-v4,l14-n01N,base-*}/compare.png`.

Run com LLM (`session:opus`, `--fit`, `--shape-only`, `--run leva2-l14-r1`, `runs/draft/n00U/leva2-l14-r1/`): front/left/back/top/bottom/rts
**.627/.601/.636/.705/.666/.623**; top e bottom passam o gate (.65), front/back ficam a .02 da meta .65. Antes: v5-oneshot-r1 .254/.368/.257/.411/.404/.490,
v5-fit-r2 .618/.569/.612/.630/.599/.610. Os 3 `spider_*` do preflight passam (.73/.60/.70 H contra .65/.58/.70). O que resta no overlay é
espessura: as pernas do sheet são ~2x mais grossas que as do modelo (o rig mede comprimento, não diâmetro) e o corpo é uma
caixa onde o sheet tem um ovo; próximo passo: `leg_w` em `measure_spider` (largura da perna no front, linha dos pés) e passá-la ao brief.

Animação: o clay do run tem 5 clips (attack, death, idle, spell, walk); `render_anim` de walk/attack/death/idle em 8 quadros
(`scratchpad/leva2-l14/clips.png`): as pernas andam, o ataque levanta a frente, a morte tomba; o retarget é relativo ao idle do
Quaternius, não depende do comprimento do osso. Default: rig medido ligado para spider quando há sheet.

### 20.S1 Autor com schema, repair/REFINE parcial com peças congeladas (S1+S3+M11, 2026-10-27)
Papers: Sketch2Mesh 2021 (Eq. 6: refinar só perto da região que falha), MeshGPT 2024 (completion = congelar o que está bom e gerar o resto; vocabulário fechado = gramática de decodificação).
- **Schema (S1).** `ask(model, brief, images, schema=None, check=None)`. `SPEC_SCHEMA` (palette com `surface` enum e `color` `#RRGGBB`, `parts` = array de arrays de 6 posições, `bones` até 3) para o autor e `PATCH_SCHEMA` (`set`/`add`/`drop`/`why`) para repair e passes.
  - `claude -p`: `--json-schema` existe; o CLI valida em strict mode (draft-07) e a API exige 2020-12, então **não há forma de tupla** (`prefixItems` é recusado pelo CLI, `items: [..]` pela API): a peça é "array de exatamente 6 itens string/array/objeto" e `validate()` tipa as posições. A resposta vem em `structured_output` (usado quando presente, senão `result`).
  - ppq.ai (Gemini): medido com `google/gemini-3.8-flash` e um pedido tentador a escrever prosa. `response_format: json_schema` (OpenAI) e `response_mime_type`/`response_schema`/`generationConfig` (nativos) **são aceitos sem erro e ignorados** (resposta em prosa ou vazia). Só `response_format: {"type": "json_object"}` é honrado, sem schema. Então o caminho API manda `json_object` (HTTP 400 de um modelo que não aceita: repete sem ele) e confia na validação.
  - Em qualquer backend: `check(reply)` (o `parse_spec`/`apply_patch` do chamador) que falha custa **1 reenvio** com o erro e a resposta anterior no prompt (`RESEND`); o contador `STATS` (asked/resent/frozen) vai para `asked.json` ao lado de `passes.json`.
- **Peças congeladas (S3+M11).** `Editable(indices, bands, height)`.
  - REFINE: `failing_bands(sil, view)` corta as máscaras conceito/modelo (já normalizadas à mesma altura por `silhouette.normalize`) em 8 faixas de altura e marca as de IoU < `BAND_IOU = 0.65`; `band_editable` deixa editável a peça cuja caixa (`preflight.bbox`) toca uma faixa que falha. Só front/left/back/right (rts/top/bottom/roof não têm eixo de altura: nada congelado). Nenhuma faixa falha, ou todas as peças tocam uma: nada congelado.
  - REPAIR: `rule_editable` pega os ossos nomeados no detalhe das regras que falham, só das regras que listam ossos (`ground`, `overlap`, `decal_place`, `symmetry`, `outside_hull`). Regra global (`budget`, `budget_split`, `box_ceiling`, `shoulder_span`...) ou nome sem peça: tudo editável.
  - O prompt lista `EDITABLE parts: [...]` e marca as demais linhas `[FROZEN]`; `apply_patch(..., editable=)` rejeita `set`/`drop` fora do conjunto e `add` fora das faixas (`ValueError`, que dispara o reenvio).
  - Limiar: com 0.75 a vista front do n005 v5-oneshot-r1 deixava 52-85 % das peças editáveis (pouco congelado); 0.65 deixa 12-64 % (um caso de 100 %, 5 de 12 vistas sem faixa falha); 0.55 quase nunca falha (v5-fit-r3, v5-oneshot-r1, v4-oneshot-r1, v3-stages-r1 de n005, `sil/approved`, front/left/back).
- **Medida (`session:opus`, n005, `--passes front[,left,back,rts] --shape-only`).** Prova em `runs/draft/n005/leva2-s1-r{1,2,3}/` (`passes/*/passes.json` tem `editable`/`of` por passe; `asked.json`). r1 parte do autor com schema; r2 e r3 partem do mesmo spec de r1 (`pass0.json`). Base: o código de `fbb2fc0f` no mesmo spec (`scratchpad/leva2-s1/`).

  | | patches | rejeitados "fora da lista" | reenvios | passes aceitos | vista que passava e caiu |
  |---|---|---|---|---|---|
  | novo r1 (front) | 1 | 0 | 0 | 1/1 | nenhuma (front .741 -> .772, back .790 -> .828, left -.0002) |
  | novo r2 (4 vistas) | 4 | 0 | 0 | 1/4 | nenhuma (final front .742 left .782 back .795) |
  | novo r3 (4 vistas) | 4 | 0 | 0 | 2/4 | nenhuma (top .698 -> .721, rts .777 -> .817) |
  | base (4 vistas) | 4 | n/a | n/a | 0/4 | nenhuma (`accepted()` já protege) |

  Peças editáveis por passe: 8-16 de 28-29 (28-57 %). Autor: 4 pedidos novos e 4 de `fbb2fc0f` (`--no-repair`, só autor), 8/8 viram spec sem reenvio, taxa de spec malformado 0/4 contra 0/4: **o schema não mede ganho com `session:opus`**, que já devolvia JSON válido; o ganho esperado é no Gemini, e lá o schema não existe (ver acima), só o reenvio.
- **Piorou / pendente.** (1) N pequeno: 9 patches, nenhum tocou peça congelada; não provo que o `[FROZEN]` segura um modelo mais solto, só que `opus` respeita a lista, e o `apply_patch` cobre o caso nos testes. (2) A diferença de passes aceitos (3/9 contra 0/4) é ruído de LLM, não prova de ganho. (3) Nas runs de n005 as regras do repair eram globais (`shoulder_span`, `fist_span`, `budget_split`): o repair nunca congelou nada; mapear `shoulder_span`/`fist_span` aos ossos `arm`/`forearm` é o próximo passo se o repair parcial importar. (4) A banda usa a altura do modelo; um conceito com adereço alto (capuz, antena) desloca as faixas. (5) O `[FROZEN]` custa linhas no prompt, não tokens de imagem.
- **Testes.** `test_spec_pipeline.py`: `AuthorSchema` (flag do CLI, `structured_output`, `json_object` e fallback 400, reenvio uma vez) e `FrozenParts` (bones das regras, `set`/`drop`/`add` fora da lista, faixas sobre máscaras sintéticas, marcação `[FROZEN]`).

## 21. Leva 3 (2026-10-27)

Sete frentes em paralelo (F1 massing, F2 lathe/limb, F3 leg_w, F4 fit largo, F5 few-shot+variants, F6 turntable,
F7 acoplamento), integradas em `feat/models-v2-hard`. Bateria `v7` nos 3 de teste + 2 unidades nunca vistas
(n02X, hfoo); `v7-r2` = o vermelho decide (`margin_of` paga o uncovered médio, `fit_accepted` recusa fit que o
aumenta, PASS com vermelho acima de `UNCOVERED_MAX` numa vista crítica fica em prototype-safe; commit `9af56ccf`).
Imagens em `history/2026-10-27-v7/`.

| unidade | v6 | v7-r2 | veredito | vermelho f/l/b |
|---|---|---|---|---|
| n01X | .787/.823/.787/.782/.833/.795 | **.839/.809/.839/.812/.775/.779** | PASS final-use | 8/10/8 % |
| n005 | .823/.810/.870/.723/.774/.835 | .838/.785/.841/.688/.792/.749 | PASS final-use, juiz prefere r2 3-0 | 11/17/13 % |
| n00U | .781/.686/.789/.640/.620/.643 | **.780/.742/.787/.707/.676**/.622 | CHECK (só rts) | 9/9/9 % |
| n02X (novo) | hard-v1 .705/.638/.749 | **.806/.724/.786/.722/.696/.728** (v7-r1) | PASS final-use | 8/14/11 % |
| hfoo (novo) | hard-v1 .820/.551/.665 | .765/.606/.694/.699/.768/.702 (v7-r1) | CHECK (left, back) | 7/18/13 % |

Depois da bateria: massing com 4 fatias no torso (era 8, lia como pilha de degraus; IoU igual ±0.02, runs
`leva3-massing-few`), massing com lathe medido e deixado opt-in (`LATHE_MASSING`: perde 0.03-0.06 em
left/top/bottom porque o eixo do lathe não segue o centro de profundidade). Próximo salto de forma é de kinds de
superfície (leva 4: `chain`, `plate`), não de regras.

### 21.F3 `leg_w` da aranha (2026-10-27) - medida e brief ligados, crescimento de perna no fit NEGATIVO (desligado)

Sem paper novo: fecha a pendência do §20.L14 (o rig mede comprimento, não diâmetro de perna).
- **`silhouette.measure_spider`** ganha `leg_w` (raio mediano da perna, fração de H) e `leg_taper` (raio na ponta / na base).
  `leg_ridge(mask)`: máscara menos a abertura por disco de 0.6 do raio máximo (o corpo), distance transform do resto, cristas
  (máximos locais) = raio da perna naquele ponto e distância ao corpo. `leg_measures` junta front e top (top calibrado por `k`,
  igual ao `body_r`), mediana de tudo = `leg_w`; taper = mediana do terço mais longe do corpo / do terço mais perto.
  n00U: `leg_w` .044, taper 1.38 (front e top concordam: .044 e .045 H). n01N: `leg_w` .032, taper .86 (front .034, top .031).
  **O taper do n00U não é confiável** (>1: a base some na dilatação do corpo e sobra ruído); `leg_w` é.
- **Brief:** `spider_text` ganha `LEG RADIUS: X H at the body, Y H at the tip (... m): legs thinner than this are the usual
  failure.` (X = 2 leg_w / (1+taper), Y = X taper). Medida antiga sem `leg_w`: sem a frase.
- **Preflight `spider_leg_w` (só relatório):** raio médio das peças `leg*` (prism = média de dims[0], dims[1]) / altura contra
  `leg_w`, banda 0.6-1.4x. Taxa de FAIL nos 16 specs spider de `runs/draft/*/*/` (os outros 63 não são spider): **3/16** (n00U
  v5-fit-r1 .065 vs .044; n01N hard-v1 .069 e v1 .064 vs .032). Abaixo de 1/3, mas as 3 pegam perna **grossa demais**, não a falha
  de interesse (fina); fica relatório (`SPIDER_BLOCKING` não muda).
- **`fit_spec.leg_grow` + `LEG_GROW`:** o limite de dims horizontais (+10 %) de uma peça `leg*` sobe até o raio do `leg_w` quando a
  perna está abaixo da medida (n00U v6-r3: pernas `lower` até +33 %). **`LEG_GROW = False` por padrão.**

Prova sem LLM, refit do n00U v6-r3 (`fit/before.json`, build real, 6 vistas front/left/back/top/bottom/rts); pernas do spec já
estão em .051 H (upper) e .033 H (lower), a mediana .051 contra .044 da medida:

| fit | front | left | back | top | bottom | rts |
|---|---|---|---|---|---|---|
| antes (before.json) | .7064 | .6897 | .7072 | .6526 | .6183 | .6409 |
| limite +-10 % (v6-r3 original, `fit.json`) | .7796 | .6850 | .7880 | .6404 | .6177 | .6411 |
| `LEG_GROW` ligado | .7757 | .6774 | .7860 | .6427 | .6164 | .6347 |

`attach.json` do refit: 24 peças, `loose: []`. O limite novo não ajuda aqui: as pernas do spec já têm o raio do sheet, o fit
não usou a folga (mediana de raio .051 -> .046) e o resultado ficou 0.001-0.008 abaixo em 5 de 6 vistas (ruído do Powell, mesmo
orçamento de 4000 avaliações). Fica desligado; liga quando houver spec com perna fina (n00U v2-hard-r2 .035 H, v3-stages-r1 .040 H
são os candidatos; não refitei: a prova pedida é o v6-r3). Saídas: `scratchpad/leva3-f3/refit/` (`fit/fit.json`, `attach.json`).
Testes: `LegMeasures` (silhouette), `test_leg_w_reports_thin_legs_without_blocking` (preflight), `LegGrowth` (fit), brief (spec_pipeline).

### 21.F6 Turntable 8 vistas: `redo_turntable.py`, `turn_panels`/`turn_check`, varredura de azimute (2026-10-27) - coerente só no n01X; n005 e n00U NEGATIVOS

**O que mudou.** `redo_turntable.py <id> --race R --name N` + `prompts/00-template-turntable.txt`: 1 chamada ao `nano-banana-2-1-edit` (mesmo `generate.py`/chave, 16:9 porque a API não aceita 2:1; ~$0.0036 por chamada, 3 chamadas) com o `sheet.jpg` aprovado como imagem, pedindo `refs/<id>/sheet-turn.jpg`: grade 4x2, lida da esquerda para a direita, fileira de cima primeiro, **0 (frente), 45, 90 (o "left" do sheet), 135 / 180 (costas), 225, 270, 315**, câmera de nível ortográfica, mesma figura, escala e linha de chão, fundo liso. `sheet.jpg` nunca é escrito. O script roda o teste de coerência e grava `sheet-turn.json` (`ok`, números); sai com código 1 se falhar. `--check-only` só reroda o teste.
- **Layout para o F4:** `silhouette.turn_panels(path)` -> `{ângulo: máscara booleana}` (ângulos em `TURN_ANGLES`, todas na mesma imagem chaveada de 1024 px de largura, aspecto nativo; linhas cortadas na faixa vazia mais larga, colunas nas 3 faixas mais largas, quartos iguais se faltar). Ângulo = azimute do desenho; 90/270 = perfis. O modelo é fotografado com `views.rts_offset(0, azimute)` (azimute da frente para +X); `silhouette.TURN_3Q`, `turn_azimuths()` (36 câmeras) e `turn_match()` são a API.
- **Coerência `silhouette.turn_check(panels)`:** altura dos 8 painéis dentro de ±10 % da mediana; largura dentro de ±10 % entre 0/180 e entre 90/270 (a largura de um painel muda com o ângulo, então "8 larguras iguais" reprovaria qualquer figura; o par oposto tem de ter a mesma); IoU de cada painel de um par com o espelho do oposto >= 0.85 (0/180 e 90/270 gate; 45/315 e 135/225 só relatados).
- **Varredura de azimute:** `render_silhouette.py -- glb out turn <az>...` (câmera de nível, só as silhuetas pedidas), `silhouette.turn_report(sheet_turn, glb, outdir)` / `silhouette.py ... --turn refs/<id>/sheet-turn.jpg`: para cada painel 3/4 (45, 135, 225, 315) o melhor IoU do clay em ±20° (passo 5°) em torno do ângulo e do seu espelho (360 - ângulo; que lado do modelo é o "45" do desenho é medido, não suposto, como no RTS); máscaras nunca invertidas. Grava `sil/<against>/turn/{turn.json,mask-*-<ângulo>.png,overlay-<ângulo>.png}`.
- **Fluxo:** `spec_pipeline.shape_review` chama `turn_views` (só se `sheet-turn.jpg` e `sheet-turn.json` com `ok` existem ao lado do sheet; senão `{}`): `silhouette.json["turn"]` e a linha `turn views 3/4 (report)` no `review.md`; `make_compare.turn_rows` acrescenta uma linha (4 overlays + rodapé `TURN 3/4  45: iou @ azimute ...`). Só relatório, não gate.

**Medida de coerência** (`artifacts/model-sheets/refs/<id>/sheet-turn.json`):

| unidade | altura dev | largura dev | espelho 0/180 | 90/270 | (45/315) | (135/225) | veredito |
|---|---|---|---|---|---|---|---|
| n01X | 0.012 | 0.014 | .953 | .961 | .864 | .584 | **OK** |
| n005 | 0.016 | 0.032 | .942 | **.600** | .621 | .846 | FAIL mirror 90/270 |
| n00U | 0.050 | 0.018 | **.837** | .898 | .722 | .707 | FAIL mirror 0/180 |

Por que falham: no n005 o desenho 270 repete o 90 (a figura olha para o mesmo lado nos dois perfis, o 270 devia olhar para o outro): o modelo de imagem copiou o perfil em vez de girar. No n00U front x back não são espelho por construção (cabeça x abdômen, .837 < .85): o sheet é coerente a olho, o critério "frente x costas espelhados" é que não vale para uma aranha; o limiar não foi afrouxado. Regra do roteiro: incoerente = negativo, arquivos mantidos (`refs/n005/sheet-turn.*`, `refs/n00U/sheet-turn.*`), o pipeline segue 3+2 nessas duas (o `turn_views` devolve `{}` e o review não ganha a linha). O n01X segue com o turntable.

**Medida 3/4** (clay v6: n01X v6-r1, n005 v6-r1, n00U v6-r3; IoU no azimute do melhor ajuste / no ângulo nominal; provas em `scratchpad/leva3-f6/<id>/turn/`). n005/n00U com sheet incoerente, só para referência:

| clay | 45 | 135 | 225 | 315 | média melhor / nominal |
|---|---|---|---|---|---|
| n01X v6-r1 | .805 @335 (esp) / .674 | .799 @155 / .637 | .767 @140 (esp) / .734 | .779 @25 (esp) / .643 | .787 / .672 |
| n005 v6-r1 (sheet incoerente) | .841 @335 / .768 | .875 @210 (esp) / .840 | .816 @155 (esp) / .745 | .741 @25 (esp) / .679 | .818 / .758 |
| n00U v6-r3 (sheet incoerente) | .680 @320 / .665 | .674 @225 / .674 | .709 @205 / .657 | .710 @65 / .685 | .693 / .670 |

(esp = lado espelho: o "45" do desenho é o lado -X do modelo, o "left" do sheet.) O n01X 3/4 fica em .77-.81, no nível das vistas 3+2 (.77-.83): o clay v6 não é pior em 3/4 do que nas vistas de gate. A varredura dá +.11 sobre o ângulo nominal e escolhe quase sempre perto do limite da janela (25, 155, 335...): os desenhos 3/4 do modelo de imagem não estão em 45 exatos (nem a "frente" está em 0), então o azimute medido é um deslocamento do desenho, não uma câmera confiável; o F4 deve tratar o azimute como parâmetro do desenho (como o tilt), não fixá-lo.

**O que piorou / limites.** Só 1 de 3 unidades passa o teste de coerência com o prompt atual; os 3/4 só são relatório. Frente x costas espelhados só vale para figuras de simetria esquerda-direita (aranha reprova por construção; um critério por unidade, ex. IoU contra o espelho do próprio painel, seria o passo seguinte). Prompt de 1 chamada sem repetição: o n005 pode passar numa segunda tentativa (custo +$0.004). Teste: `tests/tools/blender/test_turn.py` (ordem dos painéis, subcases de altura/largura/espelho, janelas de azimute, `turn_match`; sem API nem Blender).

### 21.F7 Acoplamento apertado: `uncovered` / `spill` por vista, por faixa de altura (2026-10-27) - relatório, `COUPLING_BLOCKING = False`

O IoU diz quanto, não onde nem de que lado. Duas razões de área separam o erro: **`uncovered`** = área do sheet sem modelo / área do
sheet (a mancha do overlay que só o concept cobre) e **`spill`** = área do modelo fora do sheet / área do modelo. Mesmo IoU front 0.77,
o n01X v5-oneshot-r1 é u18 s8 (magro) e o n01X v2-hard-r1 é u12 s14 (gordo). Sem paper novo: é a união
decomposta (Sketch2Mesh, Eq. 5-6, a mesma região que o `failing_band` do fit já usa).

- **O que mudou.**
  - `silhouette.coupling(concept, model)`: `uncovered`, `spill`, `bands` (8 faixas de altura a partir dos pés; as mesmas duas
    áreas por faixa, como fração do sheet / do modelo, então somam o total) e `red` = pior faixa do `uncovered` (`band`, `lo`,
    `hi`, `share`) + `blob` (bbox da maior peça vermelha, depois de uma abertura de 2 px que tira o anel fino de contorno: `x`
    em frações de H a partir do centro, `y` em frações de H a partir dos pés, `share` do sheet). É o "a lanterna" / "a perna 3"
    do relatório: n005 left aponta `x -0.38..-0.29 H, y 0.22..0.57 H` = o braço longe que o modelo não tem.
  - `silhouette.json` por vista ganha os campos; o resumo do run ganha `uncovered`, `spill`, `red` por vista.
  - `review.md`: linhas `uncovered (report, /sheet area)`, `spill (report, /model area)` e uma `worst red <vista>` por vista
    (`band 5 (0.62-0.75 H), 9 % of sheet; largest piece x ..., y ... H`).
  - `make_compare.py` / `compare_runs.py`: rodapé `bare x% spill y%` com as cores do overlay do compare. Atenção: no compare
    o concept é **verde** e o modelo **vermelho** (`OVERLAY`); nos `overlay-<vista>.png` do `silhouette.py` é o contrário (concept
    em R). `uncovered` = a mancha que só o concept cobre em ambos.
  - Gate: `COUPLING_BLOCKING = False`; `UNCOVERED_MAX` / `SPILL_MAX` por vista existem e `coupling_ok` os aplica só se ligar.
  - `fit_spec.edge_term(outlines, hard)` + `hard_canvas_edges`, gancho de 2 linhas em `Proxy.loss` (`+ EDGE_W * ...` só quando o
    proxy tem `hard`); `--fit-edges` no `spec_pipeline` (e `--hard <sheet-hard>` no `fit_spec.py`). Função separada: o objetivo
    do F4 não muda de forma.
- **Calibração** (`runs/draft/*/*` com `silhouette.json`, 65 runs; recalculado com `silhouette.py --shape` no `clay.glb`/GLB do
  run, mesma `sheet.jpg`, tilts do próprio `silhouette.json`; o IoU refeito bate o guardado em 63/65, os 2 com `*` são hard-v1
  antigos sem tilt guardado, varredura refeita). Células `uncovered/spill` em %:

| run | front u/s | left u/s | back u/s | top u/s | bottom u/s | rts u/s | IoU gates |
|---|---|---|---|---|---|---|---|
| h09B leva2-l13-base | 0/25 | 4/4 | 1/19 | - | - | - | FAIL |
| h09B leva2-l13-r1 | 1/17 | 2/21 | 3/12 | - | - | - | PASS |
| hfoo abH1 | 26/39 | 33/20 | 28/40 | 19/11 | 21/16 | 35/28 | FAIL |
| hfoo abH2 | 18/28 | 35/20 | 16/25 | 10/15 | 11/20 | 21/26 | FAIL |
| hfoo abR1 | 19/26 | 31/26 | 20/26 | 5/18 | 5/21 | 15/29 | FAIL |
| hfoo abS1 | 18/34 | 30/31 | 18/33 | 28/7 | 28/11 | 24/44 | FAIL |
| hfoo abS2 | 22/30 | 36/21 | 22/29 | 23/7 | 20/15 | 18/21 | FAIL |
| hfoo hard-v1 | 7/12 | 35/22 | 18/22 | 15/6 | 16/11 | 19/27 | FAIL |
| hfoo hardfirst | 21/37 | 35/24 | 23/37 | 18/8 | 13/19 | 21/38 | FAIL |
| hfoo v2 | 15/31 | 32/23 | 14/30 | 9/13 | 16/16 | 27/28 | FAIL |
| hfoo v2-hard-r1 | 14/16 | 38/26 | 22/23 | 21/7 | 8/16 | 14/29 | FAIL |
| hfoo v2-hard-r2 | 35/20 | 47/23 | 41/27 | 19/6 | 15/7 | 16/29 | FAIL |
| n005 hard-v1 | 11/15 | 14/10 | 9/10 | 22/10 | 20/5 | 11/8 | PASS |
| n005 leva2-s1-r1 | 12/14 | 18/7 | 10/9 | 15/16 | 13/9 | 8/11 | PASS |
| n005 leva2-s1-r2 | 13/17 | 18/6 | 11/12 | 15/16 | 14/8 | 9/12 | FAIL |
| n005 leva2-s1-r3 | 11/17 | 16/6 | 9/13 | 14/18 | 15/7 | 7/13 | PASS |
| n005 v2-hard-r1 | 14/17 | 17/12 | 10/10 | 22/13 | 16/11 | 7/16 | FAIL |
| n005 v2-hard-r2 | 15/19 | 19/31 | 17/18 | 23/14 | 22/10 | 15/20 | FAIL |
| n005 v3-stages-r1 | 16/17 | 31/38 | 15/14 | 29/8 | 31/5 | 28/11 | FAIL |
| n005 v3-stages-r2 | 17/18 | 17/13 | 15/13 | 19/15 | 16/9 | 9/13 | FAIL |
| n005 v4-oneshot-r1 | 15/21 | 14/21 | 13/16 | 27/11 | 23/7 | 7/13 | FAIL |
| n005 v5-fit-r1 | 19/15 | 14/3 | 19/12 | 23/12 | 23/6 | 9/10 | FAIL |
| n005 v5-fit-r2 | 7/10 | 14/4 | 6/5 | 15/14 | 14/11 | 5/10 | PASS |
| n005 v5-fit-r3 | 7/9 | 15/4 | 6/5 | 15/15 | 14/12 | 4/10 | PASS |
| n005 v5-oneshot-r1 | 15/17 | 17/4 | 14/13 | 16/18 | 18/7 | 8/13 | FAIL |
| n005 v5-variants-r1 | 11/25 | 17/7 | 7/19 | 15/9 | 21/7 | 5/16 | FAIL |
| n005 v6-r1 | 7/13 | 13/8 | 6/8 | 14/18 | 17/8 | 11/8 | PASS |
| n005 v6-r3 | 8/13 | 13/8 | 6/8 | 14/18 | 17/8 | 10/8 | PASS |
| n005 v6-r4 | 7/12 | 13/8 | 6/8 | 14/18 | 17/8 | 10/8 | PASS |
| n00U hard-v1* | 40/16 | 27/17 | 41/17 | 28/22 | 34/14 | 29/24 | FAIL |
| n00U leva2-l14-r1 | 32/12 | 30/19 | 31/11 | 12/22 | 14/25 | 24/22 | FAIL |
| n00U v2-hard-r1 | 26/12 | 19/23 | 26/12 | 25/20 | 23/24 | 29/22 | FAIL |
| n00U v2-hard-r2 | 30/17 | 26/16 | 30/16 | 28/14 | 35/13 | 30/22 | FAIL |
| n00U v3-stages-r1 | 25/18 | 22/18 | 25/18 | 32/15 | 36/19 | 25/26 | FAIL |
| n00U v3-stages-r2 | 44/10 | 27/16 | 44/10 | 35/15 | 37/11 | 35/19 | FAIL |
| n00U v4-oneshot-r1 | 58/10 | 37/17 | 59/11 | 44/14 | 43/11 | 40/22 | FAIL |
| n00U v5-fit-r1 | 61/15 | 56/19 | 61/15 | 26/24 | 30/15 | 33/19 | FAIL |
| n00U v5-fit-r2 | 34/9 | 38/13 | 35/9 | 27/17 | 33/16 | 24/25 | FAIL |
| n00U v5-oneshot-r1 | 73/16 | 62/10 | 73/15 | 52/26 | 51/29 | 42/24 | FAIL |
| n00U v6-r1 | 18/16 | 17/20 | 18/16 | 5/32 | 4/36 | 16/28 | FAIL |
| n00U v6-r2 | 18/16 | 17/20 | 18/16 | 5/32 | 4/36 | 16/28 | FAIL |
| n00U v6-r3 | 12/13 | 19/19 | 11/12 | 6/33 | 4/36 | 12/30 | FAIL |
| n01I hard-v1 | 9/13 | 17/17 | 5/17 | 23/19 | 5/49 | 20/17 | FAIL |
| n01I v2-hard-r1 | 12/14 | 29/25 | 10/20 | 13/21 | 17/36 | 23/14 | FAIL |
| n01I v2-hard-r2 | 14/17 | 31/36 | 10/21 | 21/15 | 26/23 | 24/15 | FAIL |
| n01N hard-v1* | 54/38 | 28/47 | 52/39 | 21/62 | 25/64 | 31/45 | FAIL |
| n01N v2-hard-r1 | 54/42 | 39/52 | 52/43 | 38/54 | 32/49 | 31/47 | FAIL |
| n01N v2-hard-r2 | 37/28 | 31/43 | 35/29 | 33/56 | 24/43 | 30/40 | FAIL |
| n01X hard-v1 | 6/8 | 7/18 | 6/8 | 14/8 | 9/16 | 6/17 | PASS |
| n01X v12 | 11/7 | 13/6 | 11/8 | 18/6 | 9/14 | 13/12 | PASS |
| n01X v13 | 9/6 | 12/6 | 9/7 | 17/6 | 8/14 | 12/12 | PASS |
| n01X v2-hard-r1 | 12/14 | 10/18 | 13/14 | 5/10 | 3/20 | 8/18 | PASS |
| n01X v2-hard-r2 | 14/13 | 9/16 | 14/13 | 6/11 | 3/17 | 9/18 | PASS |
| n01X v3-stages-r1 | 12/12 | 11/14 | 11/12 | 5/7 | 3/15 | 8/17 | PASS |
| n01X v3-stages-r2 | 14/10 | 12/8 | 13/10 | 8/9 | 2/16 | 11/16 | PASS |
| n01X v4-oneshot-r1 | 18/6 | 11/13 | 18/6 | 10/5 | 8/13 | 12/13 | PASS |
| n01X v5-fit-r1 | 11/7 | 13/9 | 11/8 | 10/8 | 3/17 | 5/17 | PASS |
| n01X v5-oneshot-r1 | 18/8 | 17/8 | 18/8 | 11/7 | 6/17 | 6/16 | PASS |
| n01X v6-r1 | 18/4 | 12/8 | 18/4 | 19/5 | 10/8 | 10/13 | PASS |
| n01X v6-r3 | 19/4 | 11/7 | 19/4 | 18/5 | 10/8 | 10/13 | PASS |
| n01X v6-r4 | 20/5 | 12/7 | 20/5 | 19/5 | 11/8 | 11/12 | PASS |
| n01X v6-r5 | 18/4 | 11/8 | 18/4 | 19/5 | 10/8 | 10/13 | PASS |
| n02X hard-v1 | 11/23 | 18/26 | 10/19 | 25/12 | 18/13 | 6/17 | FAIL |
| n02X v2-hard-r1 | 10/23 | 34/26 | 9/19 | 15/15 | 12/18 | 14/20 | FAIL |
| n02X v2-hard-r2 | 14/8 | 34/22 | 17/8 | 22/15 | 18/18 | 15/6 | FAIL |

- **O que os melhores runs atingem** (n01X v5-fit-r1, v13; n005 v5-fit-r2, v6-r4): `uncovered` e `spill` entre 3 e 18 %; por vista o
  máximo desses quatro: front u11 s12, left u14 s9, back u11 s8, top u17 s18, bottom u17 s17, rts u12 s17. Média das 6 vistas
  u 0.087-0.113, s 0.085-0.109. A pior faixa deles tem 5-6 % do sheet.
- **Caps propostos** (máximo dos melhores + 0.03, arredondado para cima a 0.05), `uncovered` / `spill`: front .15/.20 (o n01X
  v6 tem 18-20 % de uncovered e passa do cap), left .20/.15, back .15/.15, top .25/.25, bottom .25/.20, rts .20/.25. Hoje isso marca
  **50/65** runs (quase todos já falham no IoU) e **10/23 dos runs que passam o IoU** (43 %, acima de 1/3): n01X hard-v1, v2-hard-r1/r2
  (left spill), n01X v4/v5-oneshot, v6-r1/r3/r4/r5 (front/back uncovered: magro nas costas e na frente), h09B l13-r1 (left
  spill). Regra: só vira gate com < 1/3, então **fica relatório**. O que ele pega e o IoU não: modelo magro (u alto, s baixo) com
  IoU ainda acima do limiar. É o n01X v6, cuja IoU front .77-.79 passa e cujo `uncovered` 18-20 % passa a ser dito.
- **PASS "bom" x PASS "feio": nenhum gate de acoplamento separa.** n005 v5-fit-r3 (PASS e feio) e v5-fit-r2: u/s por vista
  7/9, 15/4, 6/5, 15/15, 14/12, 4/10 contra 7/12, 13/8, 6/8, 14/18, 17/8, 10/8 do v6-r4 (o "bom"): o r3 é *melhor* nas seis. A pior
  faixa e a maior peça vermelha são as mesmas nos dois (left: o braço do outro lado, `x -0.38..-0.29 H`; top: a mochila/braço
  direito). O feio do r3 é interno (caixas grandes, inchadas contra a malha que o r4 tem em capuz e casaco), que a silhueta não vê:
  o acoplamento mede a mesma coisa que o IoU, com sinal. O que sobra para separar é `zones_clay` / `cover` (§20.N3), o review
  pareado (§20.S4) e `edge_chamfer`; resultado negativo, registrado.
- **`--fit-edges` (n005 v6-r4, `--margin 0.2`, front/left/back; só o spec do n005, sem LLM).** `edge_term` hard->part outline
  (canvas heights): guardado .0108/.0140/.0095; fit sem o termo .0115/.0153/.0094 (IoU .881/.863/.904, 2876 avaliações, 53 s);
  fit com o termo .0108/.0138/.0087 (IoU .875/.867/.904, 4000 avaliações = orçamento todo, 151 s). Ganho de arestas ~0.001 H, IoU
  -0.006 no front, 3x mais lento: **opt-in, default desligado**. O contorno das peças já cobre quase toda aresta desenhada
  (convexas), então o termo quase não tem gradiente.
- **O que piorou / limites.** (1) O `red` só tem sentido na vista do tilt escolhido; top/bottom contam "altura" como o eixo vertical
  da imagem. (2) A abertura de 2 px descarta fatias finas (um braço de 3 px de largura não aparece em `blob`, só na faixa).
  (3) `uncovered` e `spill` são funções do IoU e das áreas: sozinhos não acrescentam gate útil com os limiares atuais.
  (4) Runs antigos não guardam `sil/approved/`, então o compare só mostra `bare/spill` nos runs refeitos depois deste commit.
- **Testes.** `test_silhouette.Coupling` (bandas, blob, texto, chave do gate), `test_make_compare.test_footer_coupling`,
  `test_spec_pipeline.test_coupling_rows`, `test_fit_spec.EdgeTerm`.

### 21.F4 Fit largo: rot, top/bottom/rts, dims 20 % ligadas, zonas, `cut` decidido pelo fit (2026-10-27)
- **O que mudou** (`fit_spec.py`, `spec_pipeline.fit_stage`; `--fit` continua default, `--fit-fast` = fit clássico):
  - **Vistas no objetivo:** front/left/back + top/bottom/rts (`WIDE_VIEWS`). `project(view, pts, cam)` projeta
    ortográfico como `views.camera`/`rts_offset`: top `v = y cos t + z sin t`, bottom `v = -y cos t + z sin t`, rts e
    painéis de turntable por câmera olhando o centro. A câmera: a do `silhouette.json` do run quando ele existe
    (`run_tilts`), senão varredura (`TILTS`, `RTS`) pelo IoU do proxy do spec inicial (`Proxy.pick_cams`, ~0.4 s).
  - **`rot` (+-20 graus por eixo, eixos do DSL):** peças dos ossos arm/forearm/hand/thigh/shin/foot/leg e a maior peça de
    `head` (capuz), que não sejam from/to (esses ignoram `rot`). O gêmeo `.R` gira `(right, -up, -forward)`.
  - **Parâmetros por tipo:** `PARAMS[kind]` lista os nomes extras (hoje `("rot",)` em box/prism/frustum/dome) e
    `EXTRAS[nome]` diz tamanho, quando vale e como mexe na peça. Kind novo (lathe/limb de F2) só acrescenta entradas.
  - **Dims 20 %** (`ATTACHED_RANGE`) para peça cujo osso tem pai e não está solto a 80 % (`loose0`); o resto continua
    10 %; spine/pelvis/body/abdomen e o capuz continuam só encolhendo x/z. A âncora (§20.N12) não mudou.
  - **Zonas** (`Zones`, `ZONE_W = 0.1`): por peça móvel e vista, fração da projeção dentro da zona do sheet (`zone_labels`
    do sheet, com tinta) do material da peça (cor do `palette` -> zona mais próxima). Peso pequeno por desenho.
  - **`cut: sheet`:** o proxy não modela o corte, então `fit_stage` constrói o clay real do original, do ajustado e do
    ajustado com `fit_spec.toggle_cut` (corte tirado se há algum; senão no maior box/prism/frustum liso de
    spine/pelvis/body/abdomen e no capuz, no máximo 3) e fica com o melhor por `fit_accepted` em cadeia (soma de margens,
    deslize 0.02, regras do preflight). `fit.json` ganha `real.cut` e `chosen`.
  - **Orçamento:** `MAX_EVALS` 4000 e `MAX_SECONDS = 150` (`Stop` na função objetivo; o melhor ponto vale). `--fit-fast`:
    3 vistas, sem rot/zonas/dims 20 %, 1500 avaliações, sem teste de `cut` (~40 s).
  - **Turntable (F6):** `turn_masks` lê `refs/<id>/sheet-turn.jpg` só se existir e se `silhouette.turn_panels(path)`
    for chamável e devolver `{azimute em graus (0 = frente): máscara}`; os painéis a 45/135/225/315 entram no objetivo
    como `turn<az>`, azimute varrido +-20 (passos de 10). Sem o arquivo (hoje), ignorado: **não medido**, só teste unitário.
- **Proxy x render, top/bottom/rts** (33 runs de `runs/draft`, 99 pares, `scratchpad/leva3-f4/validate.py`): com a tilt do
  `silhouette.json` correlação **0.996**, erro médio 0.006, viés -0.002; com a tilt varrida pelo proxy 0.996, 0.006,
  -0.0006 (mesma qualidade, então sem o `silhouette.json` a varredura serve).
- **Prova sem LLM** (`spec_pipeline --spec runs/draft/<id>/v6-r1/fit/before.json --no-repair --shape-only`, clay real das
  6 vistas; saídas em `scratchpad/leva3-f4/<id>/`). antes = spec do autor; v6 = o `fit.json` guardado (fit clássico);
  F4 = escolhido (n005 `after`, n00U e n01X `cut`):

  | | front | left | back | top | bottom | rts | soltas (attach) |
  |---|---|---|---|---|---|---|---|
  | n005 antes | .724 | .780 | .774 | .715 | .780 | .810 | 2 |
  | n005 v6 | .816 | .810 | .868 | .723 | .775 | .838 | 1 |
  | n005 **F4** | .826 | .806 | .869 | .763 | .805 | .859 | 1 |
  | n00U antes | .706 | .690 | .707 | .653 | .618 | .641 | 0 |
  | n00U v6 (rejeitado) | .780 | .686 | .789 | .640 | .618 | .641 | 0 |
  | n00U **F4** | .783 | .705 | .790 | .707 | .675 | .659 | 0 |
  | n01X antes | .707 | .787 | .709 | .759 | .793 | .763 | 0 |
  | n01X v6 | .790 | .828 | .791 | .789 | .835 | .796 | 0 |
  | n01X **F4** | .816 | .832 | .817 | .834 | .857 | .812 | 0 |

  Tempo do fit (só a busca, 6 fits em paralelo): n005 114 s (2577 avaliações), n01X 71 s (2161), n00U 153 s (3084, parou
  no orçamento); `--fit-fast` 37-42 s (1500). Pipeline inteiro (3 clays do `fit_stage` + build final + sil), 3 unidades em
  paralelo: 125-213 s por unidade.
  `cut` real, por unidade (soma das margens): n005 ajustado .826/.806/.869/.763/.805/.859 contra com corte
  .804/.820/.857/.770/.821/.849, o ajustado ganha (rts e front); n00U o corte recupera left (.665 -> .705); n01X o corte
  ganha front/back/top (+.004).
- **Zonas (ablação, `ZONE_W` 0 contra 0.1, fração média das peças dentro da zona do material):** n005 .647 -> .659, n00U
  .318 -> .329, n01X .347 -> .358, e o IoU não paga: front n005 .839 -> .830, n01X .829 -> .828, n00U ~igual. Ganho de
  +0.01 em fração, dentro do ruído; o peso fica em 0.1. A fração é baixa (.3-.66) porque o mapeamento material -> zona
  é a cor do `palette` contra 4 centros k-means do sheet, e muitas peças pequenas cruzam duas zonas.
- **O que piorou / limites:** o n00U `after` sem corte perdeu left (.690 -> .665) ao ganhar front/back: quem salvou foi o
  teste de `cut`. n005 continua com 1 solta (foot.R) como no fit antigo (vem do spec do autor). O `rot` não foi isolado
  numa ablação própria (as 6 vistas melhoram juntas; `rot` e dims 20 % entram na mesma busca). n00U rts .659 segue
  abaixo do gate 0.70 e o veredito dele é CHECK (stage 1 FAIL só por rts). O n00U gasta o orçamento de 150 s.
  O teste de `cut` custa 1 clay a mais (~60 s) por unidade.
- Papers: Sketch2Mesh 2021 (contorno 2D multi-vista, só onde falha), Wiersma 2026 (restrições duras: regras do preflight e
  ligação ao pai), MeshGPT 2024 (congelar o que já está bom: peças fora da faixa não entram na busca).

### 21.F2 Kinds `lathe` e `limb` (2026-10-27)

**Interface (F1 `massing.py` usa isto; código único em `tools/blender/lathe_limb.py`, eixos do spec: x direita, y cima, z frente).**

| kind | dims | opts (default) | tris |
|---|---|---|---|
| `lathe` | `(r, h)`, `at` = centro | `profile`: 6-10 raios em fração de r (0.05-1.5), de baixo para cima (sem ele: lido do sheet; sem sheet: `DEFAULT_PROFILE`); `axis` `front` ou `left` = painel lido (`front`); `sides` 6-8 (6); `squash` = raio x / raio z, 0.5-2 (1). Sem `rot`, `from/to`, `cut`. | `2*sides*(anéis-1) + 2*(sides-2)`: 68 com os defaults (6 anéis) |
| `limb` | `(r_topo, r_joelho, r_base)` | `from`, `to` (obrigatórios); `knee` `[frac 0.15-0.85, dx, dz, dy opcional]` (`[0.5,0,0,0]`): joelho = `from + frac*(to-from) + (dx, dy, dz)`; `sides` 6-8 (6). | `4*sides + 2*(sides-2)`: 32 com os defaults |

O raio de cada anel do lathe é `r * profile[i]` no eixo x e esse valor dividido por `squash` no eixo z. Perfil lido do sheet: `cut_hull.lathe_profile` pega, em 6 faixas da altura `[y0,y1]` da peça, a largura da máscara do painel (colunas só dentro de `1.25 r` de `at`, para não ler o braço ao lado), dividida por `r` e limitada a 0.1-1.25; viaja no mesmo `cuts.json`. Então **`r` = o raio esperado na linha mais larga**; 1.25 em várias faixas = `r` pequeno demais. `limb` pesa o tubo de cima no osso `bone` (`.upper`, `thigh`, `arm`), o de baixo no par (`.lower`, `shin`, `forearm`) e o anel do joelho meio a meio, quando o rig tem o par; senão tudo no osso. A regra `bones` do preflight conta o par como coberto; `shin_mass` lê um limb em `thigh.*`.

- **O que mudou.** `lathe_limb.py` (geometria, schema `bad_opts`, tris, par de ossos), `build_unit.swept_part`/`skin_part` (malha, pesos; entra por `build_spec_parts`), `preflight` (`part_tris`, `bbox`, `bones`, `shin_mass`), `spec_pipeline` (`KINDS`, `validate`, DSL com capuz, torso, abdômen de aranha, perna biped e perna de aranha), `fit_spec` (`part_points`; parâmetros extras: raios do profile e squash ±15 %, knee frac ±0.15 e dx/dz; torso `NO_GROW` só encolhe o profile; o fit grava o perfil do sheet no spec antes de mexer), `cut_hull` (`lathe_profiles`; peças `cut` continuam só box/prism/frustum). Os dois kinds levam tampa nas pontas (n-gon), senão o limb deixava buraco visto de baixo: 32 tris, não os 2×(sides×2) = 24 do roadmap. Papers: Sano 2026 (perfil de largura por faixa), Sketch2Mesh (parâmetros contínuos no contorno).
- **Prova sem LLM** (`spec_pipeline --spec ... --no-repair --no-fit`; saídas em `scratchpad/leva3-f2/`; IoU contra o sheet aprovado):

| run | tris | front | left | back | top | bottom | rts | média | solta em `attach.json` |
|---|---|---|---|---|---|---|---|---|---|
| n005 v6-r4 (base) | 608 | 0.822 | 0.809 | 0.870 | 0.722 | 0.775 | 0.833 | 0.805 | 1 (foot.R) |
| n005 capuz + torso em `lathe` | 640 | 0.826 | 0.784 | 0.862 | 0.715 | 0.772 | 0.827 | 0.798 | 1 (foot.R) |
| n005 lathe + `fit_spec` (3 vistas) | 640 | 0.870 | 0.798 | 0.891 | 0.722 | 0.735 | 0.823 | 0.807 | 0 |
| n00U v6-r3 (base) | 550 | 0.777 | 0.686 | 0.778 | 0.640 | 0.617 | 0.631 | 0.688 | 0 |
| n00U abdômen `lathe` + 8 `limb` (24 -> 16 peças) | 500 | 0.778 | 0.683 | 0.784 | 0.624 | 0.618 | 0.633 | 0.687 | 0 |

- **Leitura.** Sem fit os kinds trocam peças sem mexer no IoU (±0.01 por vista; média 0.805 -> 0.798 e 0.688 -> 0.687): a forma não melhora sozinha, o ganho é estrutural. O n00U perde 8 peças e 50 tris com cada perna em um limb, mesma silhueta, nenhuma solta; o n005 gasta 32 tris a mais (torso 28 -> 68, capuz 12 -> 68), o que derruba `budget_split` (pernas 19 % no piso da faixa) e o preflight desse spec de prova: o massing precisa decidir o orçamento por osso. O fit com os parâmetros novos subiu front 0.826 -> 0.870 e back 0.862 -> 0.891 no render real (o proxy deu 0.870/0.884), ao custo de bottom 0.772 -> 0.735 (o fit só olha front/left/back; F4 amplia). Os perfis lidos do sheet do n005 saturam em 1.25 no torso (`r` = 0.48 é pequeno para a barra do casaco): o massing deve passar `r` = largura máxima medida.
- **Piorou / pendente.** n00U continua FAIL no estágio 1 (top/bottom/rts, igual à base; é F3/F4). O perfil lido não segmenta: um braço colado ao torso dentro da janela entra na largura. O proxy do fit usa o casco convexo dos anéis. Sem teste Blender automático dos kinds: a prova é o rebuild acima; `test_lathe_limb.py` cobre geometria, schema, preflight, perfil do sheet e fit.

### 21.F5 Few-shot no brief e `--variants 3` por default (2026-10-27) - few-shot ligado, sem prova de ganho

- **O que mudou** (`spec_pipeline.py`). (a) `with_fewshot` acrescenta ao prompt do autor, depois das referências, um exemplo
  spec→render por família de rig: o spec resumido (uma linha por peça nos 6 slots da DSL; dos opts só `from`/`to`) e uma
  imagem `fewshot/<família>.jpg` (concept | clay front, recorte do `compare.png`). biped: `n01X/hard-v1` (PASS); spider:
  `n00U/v6-r3`, a melhor aranha até agora (nenhuma passou o estágio 1; o texto diz que front/left/back passam e top/bottom
  não: "copie escala e número de peças, não os defeitos"). Texto: "this is what a PASS looks like in this DSL: note the scale
  of dims against H and how few parts it takes". Outras famílias (edifícios) e `--no-fewshot`: brief antigo. O exemplo fica
  atrás de `FEWSHOT_MARK`; repair e passes cortam o texto (as imagens deles são outras, a numeração não vale).
  (b) `--variants` default 3 (`1` desliga); `best_of_n` inalterado, perdedores em `variants/<k>/`.
- **Custo** (registrado em `review.md`, seção Few-shot): 1 imagem extra (~460 tokens, w*h/750) + ~680 tokens de texto por
  chamada do autor; `--variants 3` triplica as chamadas (paralelas) e os builds do estágio 1 (~80 s cada, em série).
- **Medida** (n005, `session:opus`, `--shape-only --no-repair`, `runs/draft/n005/leva3-f5-r1`). O vencedor (1 de 3 variantes
  que passaram a validação) depois do fit: IoU front/left/back/top/bottom/rts **.825/.773/.887/.680/.702/.812**, contra
  v6-r4 .823/.810/.870/.723/.774/.835 (v6-r4 teve repair/passes; este não): melhor em front e back, pior em left, top,
  bottom e rts; preflight FAIL, estágio 1 FAIL. Margem da variante vencedora antes do fit: +0.253.
- **Piorou / achado.** (1) Primeira versão do resumo omitia `from/to` (peças de membro ficavam com `at` 0,0,0 e dims de
  offset): 3/3 variantes caíram; consertado (`fewshot_summary` mantém `from`/`to`). A segunda mostrava `from/to` no lugar de
  `at` e o autor copiou o formato (schema inválido): por isso o resumo segue os 6 slots. (2) **Falha que já existia:** o
  autor erra "part N below the ground plane" em quase todo pedido do n005 neste HEAD. Sem few-shot (`--no-fewshot`, 3 runs
  de 3 variantes = 9/9 variantes caíram, mesmo após o reenvio); com few-shot (versão final) 1 de 3 sobreviveu. Com
  `--variants 3` um run morre ("no reply parsed into a spec") quando as 3 caem, igual ao run único de antes; o certo é
  atacar essa validação (candidato: `ground_fix` antes de rejeitar), não é desta frente. (3) N=1 por braço: o sinal
  few-shot 1/3 contra 0/9 é fraco e o IoU não prova ganho; sem controle pareado de margens (o braço sem few-shot nunca
  produziu spec). Few-shot fica ligado por pedido do roadmap; reavaliar na bateria v7.
- **Testes.** `test_spec_pipeline.py`: `FewShot` (exemplo por família, `--no-fewshot`, família sem exemplo, o corte do
  texto pelos passes, resumo sem opts e com `from/to`).

### 21.F1 Massing determinístico, estágio 0: `massing.py` (2026-10-27)
Papers: Sano 2026 (visual hull como volume base), Gao 2022 (massa regularizada, o LLM só põe o detalhe), EdgeRunner 2024 (orçamento por região). Roadmap: "o autor edita, não inventa".
- **O que mudou.** `tools/blender/massing.py`: do sheet aprovado (painéis front/left via `concept_panels`, `silhouette.measure`, `zone_palette`) e do rig (`rig_families`, spider já escalado por `scale_spider`, §20.L14) sai um pré-spec com uma massa por osso, sem LLM e sem Blender (~3 s).
  - **Biped.** Cabeça, torso e pelve = pilhas de `frustum` (um lathe linear por trechos): a largura vem do front, a profundidade e o centro z do left, e os pontos de quebra ficam onde o perfil dobra (Douglas-Peucker nos 3 canais; degrau = fatia reta sem afunilamento). Braços e pernas = `prism` de junta a junta (`from`/`to`); raio do braço = metade da corrida externa onde o braço pende livre (3 corridas na linha), senão a borda externa menos o raio; cotovelo limitado a 1,1 x o `shoulder_span` do sheet (o preflight lê a caixa de toda peça que toca a faixa 0,70-0,90 H: um braço inclinado e grosso estoura a regra); mãos e botas = `frustum`. Centro do front = ponto médio dos pés (uma arma pendurada de um lado puxa a caixa e a pelve do n005 saía deslocada).
  - **Spider.** As 16 pernas do rig medido como `prism` hexagonal (raio = 1,8 x a corrida mediana perto do chão: as juntas do rig estão perto das pernas do sheet, não nelas; F3 troca por `leg_w`); casco = 8 fatias em z (cauda para cabeça) com largura do top com as pernas "abertas" (`binary_opening` como `measure_spider`), y do perfil lateral (topo real = altura do modelo), 3 `frustum` por fatia estreitando como o front. A fatia que passa por cima dos quadris é do osso `body` (a regra `overlap` exige a perna tocando o pai).
  - **Materiais.** Slots `z1..zk` = as zonas de `zone_palette`; cada peça leva a zona dominante da sua faixa no front. Se menos de 3 ficam em uso (n005 é uma cor só), `ensure_slots` passa as sobras a pés, cabeça, abdômen. Superfície: `metal` para Mech, `cloth`/`chitin` senão; o autor troca.
  - **Props.** O preflight exige uma peça por prop de `props.json`; a silhueta não diz onde o prop está: uma caixa no meio do osso, do tamanho médio da faixa (`placeholder_props`), que o autor move. Com prop nas costas (n005, tanque) a profundidade do torso é cortada em 0,75 x a largura (cabeça +0,3) mantendo a linha do peito (`BACK_PROP_DEPTH`).
  - **Ponto único de troca.** `KIND_FOR = {"head": "frustum", "torso": "frustum", ..., "arm": "prism", "leg": "prism", "shell": "frustum"}` + `EMIT = {kind: emissor}`; quando F2 existir, `KIND_FOR["torso"] = "lathe"` e um emissor em `EMIT` (um kind sem emissor cai no que existe, testado).
- **`spec_pipeline`.** Estágio 0 antes do autor (`--no-massing` desliga; `--spec` e famílias sem massing também): `massing_spec` passa o pré-spec por `parse_spec` (grade 1/256, `ground_fix`, rig_measure); `massing_stage` o constrói e mede sozinho em `<run>/massing/` (o mesmo `stage_shape`, clay + 6 vistas + preflight); o brief do autor (só dele: repair/REFINE não veem) termina com `EDIT_NOTE` + o pré-spec em JSON: "keep every part unless the sheet says otherwise; add props, decals, materials; at most 8 changes; the part-count rule does not apply". `review.md` ganha `## Stage 0 - massing alone` (IoU 6 vistas, gates, regras do preflight, tris, quantas peças o autor mexeu).
- **Prova sem LLM: só o pré-spec** (`spec_pipeline --spec <massing> --no-repair --no-fit --shape-only`; `scratchpad/leva3-f1/{n01X,n005,n00U}-massing/`). IoU front/left/back/top/bottom/rts; entre parênteses v6 (o clay v6 com autor + fit):

  | | massing | v6 | preflight | stage 1 |
  |---|---|---|---|---|
  | n01X | .841 / .839 / .842 / .793 / .735 / .774 | r5 .787 / .823 / .788 / .782 / .833 / .795 | 20/20 | PASS |
  | n005 (sem corte de profundidade) | .754 / .816 / .806 / .699 / .763 / .732 | r4 .823 / .810 / .870 / .723 / .774 / .835 | 21/21 | PASS |
  | n005 (com corte, o default) | .756 / .552 / .809 / .707 / .801 / .746 | idem | 21/21 | FAIL (left .552 < .65) |
  | n00U | .760 / .726 / .765 / .626 / .620 / .601 | r3 .781 / .686 / .789 / .640 / .620 / .643 | 10/10 | FAIL (top, bottom, rts; o v6-r3 também fica abaixo nelas) |

  O massing sozinho **bate o v6 em 4 de 6 vistas no n01X, em 1 de 6 no n005 (left) e em 1 de 6 no n00U (left; bottom empata)**; não bate "≥ v6 em tudo". O que perde são as vistas de cima/baixo/rts (a profundidade de braços e pés vem só do left; pés do n01X saem curtos no bottom) e as pernas do spider (o rig não as põe onde o sheet as desenha). O v6 tem o fit por cima; o massing ainda não.
- **Prova com LLM** (`session:opus`, n005, `--shape-only` não, rodada completa; `runs/draft/n005/leva3-f1-r{1,2}/`, `massing/` dentro de cada um):

  | n005 | front / left / back / top / bottom / rts | autor mexeu | tempo gen / passes |
  |---|---|---|---|
  | v6-r4 (sem massing) | .823 / .810 / .870 / .723 / .774 / .835 | - | - |
  | r1 massing sem corte + edit + fit | .851 / .706 / .865 / .654 / .710 / .740 | 8 novas/editadas, 1 tirada (de 31) | 84 s / 47 s |
  | r2 massing com corte + edit (sem fit: nenhuma vista abaixo do gate) | .838 / .780 / .842 / .684 / .798 / .731 | 7 novas/editadas, 2 tiradas (de 31) | 92 s / 11 s |

  Os dois passam estágio 1 e 2 (PASS, 21/21, tris 668 e 644). r1 mostrou o defeito: o torso do pré-spec já carregava o volume do tanque (profundidade do left) e o autor adicionou o tanque de novo (prisma em z = -0,92): left .816 -> .608 depois do edit, o fit levou a .708. Daí o corte de profundidade com prop nas costas: r2 left .780 (+0,07), bottom .798, top .684. Front e back ficam 0,01-0,02 abaixo do r1. Contra o v6-r4 (autor do zero): front +.015, left -.03, back -.03, top -.04, bottom +.02, rts -.10; o ganho real do edit é tempo de autoria (7-8 edits em vez de 28 peças) e preflight 21/21 de saída, não IoU.
- **Piorou / pendente.** (1) Não atingi "massing sozinho ≥ v6": top/bottom/rts perdem. (2) N=1 run com LLM por configuração; a diferença r1 x r2 (+0,07 no left) é maior que o ruído medido em §20.S5 (~0,03) mas é um run. (3) O n005 com corte falha o gate do left sozinho (a massa sem o tanque), o que só importa na seção "massing alone" do review. (4) Pés e mãos dependem de heurísticas de corrida (`nearest_run`); sheets com pé fora do padrão podem sair com o pé do tamanho da perna. (5) Quadrúpede, serpente, veículo e edifício: sem massing (`None`, brief antigo); edifício tem `--hull`. (6) `LEG_FAT` = 1,8 é calibração em 1 spider.
- **Testes.** `test_massing.py` (View/specks/recentre, `breakpoints`, pilha, fallback de kind, `ensure_slots`, pré-spec do n01X passa `checks_of` sem falhas e cobre os ossos exigidos, família sem massing) e a classe `Pipeline` no mesmo arquivo (`edit_changes`, `rules_of`, `--no-massing`, seção do review).

## 22. Leva 4 (2026-10-28)

### 22.L4-4a Sheets para quadruped, wyrm e drake (2026-10-28) - sheets prontos, `measure` só vale em parte, n00H sem RTS

Miniaturas (`history/2026-10-28-l4-4a/miniaturas.jpg`): linha 1 `sheet.jpg` n017 | n00H | n010, linha 2 `sheet-hard.jpg`, linha 3 `sheet-rts.jpg` (n017, vazio no n00H, n010).

- **Unidades.** `n017` Frost Wolf (rig `quadruped`), `n00H` Winged Serpent (`wyrm`: corpo serpentino + asas), `n010` Azure Drake (`drake`). Nenhuma tinha `refs/<id>/sheet.jpg`. Prompts escritos à mão a partir de `unit_facts.py` e dos templates (sem LLM de spec): `prompts/<id>/unit-<id>.txt`, `unit-<id>-hard.txt`, `n017/unit-n017-props.txt`. Layout 3+2, fundo #CCCCCC, `{blocks}` da família no lugar de "two arms, two legs", pose neutra por família (§16), linha "Weapon match" e "Rank in its chain".
- **Chamadas (nano banana, ppq.ai, custo informado pela API: US$ 0,0034 sheet, 0,0036 edit 2K, 0,0025 edit 1K; total ~ US$ 0,04).** 12 de 12 permitidas: n017 sheet, hard, rts, props; n00H sheet, sheet r2, hard, rts (falhou); n010 sheet, sheet r2, hard, rts. Nada foi sobrescrito: as primeiras tentativas de n00H/n010 e o RTS ruim do n00H foram para `refs/<id>/old/` e `prompts/<id>/old/`.
- **Refeitos.** n00H e n010 saíram na 1a tentativa com asas abertas largas demais (n010: a asa do front invade a coluna do perfil; n00H: o S aparece também em front/back). A 2a tentativa trocou "wings spread" por "half-folded in a narrow V" e pediu o S só no perfil. n00H ficou bom (front/back = coluna reta, S só no left). n010 ficou com **top/bottom girados 90° (cabeça à esquerda)**, defeito aberto: sem chamada sobrando. Corrigir regenerando o sheet com "top-down: head toward the top of the page" antes de qualquer massing/compare de top e bottom desse id.
- **`silhouette.concept_panels(blob=True)` (novo, opt-in).** O corte padrão acha as duas lacunas verticais do topo, mas ordena por largura e as margens da página (0-55 px e 731-768 px) ganham das lacunas internas (28 e 9 px): sobra `inner` com 0 itens e o fallback é terços iguais, que corta um perfil de quadrúpede (mais largo que 1/3 da página) em 256 px e põe o focinho no painel front. `blob=True` separa por componente conexo (dilatação 6 px; 3 maiores em cima, 2 embaixo, ordem pela posição x). Não é o default: medido com `blob` só no lugar do fallback de terços, 18 dos 23 sheets de unidade/edifício existentes (todos menos hfoo hard-clean, n005 hard-clean e os 3 do n01X) caem nesse fallback e mudariam de máscara (e o n005 hard deixaria de achar 3 figuras); fica para quando alguém recalibrar os gates. Teste: `test_silhouette.BlobPanels` (suíte 339 OK; ruff limpo nos dois arquivos).

Tabela de coerência (768 px; alturas em linhas ocupadas por painel, `blob=True`):

| id | painéis não vazios | h front / left / back | desvio da mediana | RTS: figuras | hard x sheet (IoU front/left/back/top/bottom) | `props.json` |
|---|---|---|---|---|---|---|
| n017 wolf | 5/5 | 242 / 237 / 259 | 0 / -2,1 / +7,0 % | 1 | .946 / .946 / .943 / .949 / .965 | sim (2 itens, `sheet-props.jpg` com 2 desenhos, `crop_props` = 2) |
| n00H wyrm | 5/5 | 329 / 329 / 329 | 0 / 0 / 0 % | **5 (falhou, movido p/ old/)** | .944 / .933 / .932 / .961 / .954 | não (card lista props de corpo; sem chamada p/ sheet-props) |
| n010 drake | 5/5 | 255 / 259 / 253 | 0 / +1,6 / -0,8 % | 1 | **.894 / .933 / .885** / .944 / .963 | não (idem) |

Todos dentro de +-10 % de altura. `DRIFT_MIN = 0.90`: n010 front (.894) e back (.885) ficam abaixo (o hard redesenhou o fecho das asas); n017 e n00H passam. `props.json` do n017: extents são estimativa do sheet (`[0.2, 0.6]` nos dois), sem spec para calibrar; ajustar quando houver run. `check_rts` global: tudo 1 figura, exceto o n00H, que foi retirado para o pipeline (`ensure_rts` desenha de novo).

**`silhouette.measure` em quadruped, wyrm, drake** (valores com `blob=True`; sem ele o n017 dá `boot_height` .764, `shoulder_span` .802, `area_head` .007, pior):

| medida | quadruped (n017) | wyrm (n00H) | drake (n010) | veredito |
|---|---|---|---|---|
| `area_head/body/legs` (faixas do front por `shoulder_row`) | .138/.374/.488 | .011/.572/.417 | .019/.455/.526 | só ordem de grandeza: a faixa "cabeça" sai do primeiro degrau largo, não da cabeça; no wyrm não existem pernas |
| `boot_height` (perfil, bota) | .131 | .271 | .412 | sem sentido: não há bota; seria altura do casco/pata |
| `head_width`, `neck_width` | .302 / .285 | .559 / .523 | .698 / .675 | sem sentido: leem a largura do corpo no topo do front (n010: a abertura das asas) |
| `arm_angle`, `arm_length`, `fist_span`, `shoulder_span` | 2,1 / .448 / .401 / .397 | -11,2 / .825 / .191 / .483 | -11,8 / .826 / .318 / .624 | sem sentido: não há braço; no drake `shoulder_span` é o vão das asas (útil, com outro nome) |
| `stance` | .413 | .176 | .341 | vale no quadruped (afastamento das patas da frente); nos outros, largura do corpo |
| `body_depth`, `foot_length` (perfil / front) | 1,28 / 1,24 | .535 / .678 | 1,22 / .482 | `body_depth` = comprimento do perfil / H: vale (wolf 1,72 em largura de perfil sobre H); `foot_length` não |
| `shoulder_frac`, `head_clear` | .20 / .25 | .04 / .10 | .04 / .10 | sem sentido: constantes de bípede |

O que uma `measure_quadruped` precisaria (a `measure_spider` é o modelo: lê o left, não o front): (1) comprimento total/H e comprimento do tronco (peito à garupa) no left; (2) altura da cernelha e da garupa/H e folga da barriga ao chão (vão sob o corpo, como o `daylight` da aranha); (3) comprimento e espessura do pescoço e do focinho (cabeça: comprimento/altura no left, largura no front); (4) comprimento da cauda e ângulo (nível x caída); (5) afastamento das patas de frente e de trás no top e no front, comprimento do cano (upper/lower) pelo left; (6) para drake: envergadura/H e área da asa no top, altura da ponta da asa sobre a cernelha no front, e se as asas sobem (V) ou abrem (plano); (7) para wyrm/serpente: comprimento da linha central, espessura ao longo dela (afilamento), número e amplitude das curvas do S no left, relação cabeça/corpo, envergadura. Todas saem das mesmas máscaras; o pré-requisito é o `blob=True` como split.

- **Pendente.** (1) n00H sem `sheet-rts.jpg`; (2) n010 top/bottom girados; (3) hard-clean não gerado (não pedido); (4) massing dessas famílias espera `chain`/`plate`; (5) `props.json` de n00H/n010 só com sheet-props (estourava o limite de chamadas).

### 20.L4-6 Landmarks de junta: `joint_measures`, regra `joint_place` (2026-10-28) - relatório, massing opt-in

- **O que mudou.** `silhouette.joint_measures` (chamado por `measure`): do painel front, a perna +x é seguida do topo da bota para cima (`limb_widths`, a corrida mais próxima de 0,2 H do centro, que acaba onde as pernas se juntam ou a corrida passa de 0,2 H) e o braço +x do punho para o ombro (a corrida mais externa); a junta é a linha do maior degrau da largura suavizada (`knee_row`, meio do platô, só no miolo 20-80 % do trecho, só se o degrau >= 0,25 x a largura mediana). Saem `knee_h` e `elbow_h` (altura sobre os pés, em H; mesmo nome que `measure_spider` já usa); junta que o desenho não mostra fica de fora (sem chute). `_runs` junta corridas separadas por <= 3 px (quebras do contorno). `spec_pipeline.joint_text` põe "JOINTS: knee at X H, elbow at Y H" no brief do biped. O spider já tinha `knee_h/knee_r` em `measure_spider` e o texto "knee ... H high"; nada novo ali.
- **Medidas** (`scratchpad/leva4-joints/joints-front.png`, linha sobre o painel front): n01X knee 0,311 (a olho: o degrau coxa fina -> joelheira/canela larga, ok); n005 elbow 0,467 (ok a olho: braço entre 0,65 e 0,35); hfoo e n02X: nenhuma. Calças, capas e braços colados ao tronco não têm degrau de largura no contorno: 2 de 8 juntas lidas. Limiar menor (0,12) lê mais (n005 knee 0,186, hfoo knee 0,179) mas são a barra da calça/bota, não joelho: ficou 0,25.
- **`preflight` `joint_place`** (biped): a junta do spec (média entre o y mais baixo das peças thigh/arm e o y mais alto das shin/forearm; ou o ponto `knee` de um `limb` no osso de cima) a +-0,06 H da medida; só roda para a junta que o sheet mostra. `JOINT_BLOCKING = False`: relatório (passa sempre, detalhe `- OUT`). **Taxa de FAIL** nos 73 specs biped de `runs/draft` (os de n005 e n01X são os 46 com junta lida): n01X 10 de 20 specs, n005 16 de 26 (elbow): 26 de 46 = 57 % (> 1/3), então não vira gate. O n005 fica quase sempre 0,05-0,10 H acima do 0,467 (cotovelo do spec em 0,52-0,58), o n01X 0,04-0,08 abaixo (0,22-0,28 contra 0,311): regra pega um viés real do autor, mas o limiar 0,06 é apertado para uma medida de 1 px por linha.
- **`massing`**: `MEASURED_JOINTS` (default `False`): `landmarks` passa `knee`/`elbow` a `leg_geometry`/`arm_geometry` (`joint_between`: dentro do osso, 15 % de folga) em vez do ponto médio. Massing sozinho, `--shape-only`, 6 vistas (front/left/back/top/bottom/rts):

  | | IoU antes | IoU depois | média | uncovered médio |
  |---|---|---|---|---|
  | n01X | .842 .825 .842 .794 .733 .777 | .846 .832 .847 .794 .733 .776 | .8022 -> .8045 | .0915 -> .0888 |
  | n005 | .756 .579 .811 .697 .813 .742 | .750 .579 .795 .697 .812 .741 | .7332 -> .7291 | .1718 -> .1744 |

  Misto (+0,002 e -0,004): o cotovelo medido do n005 (0,467) desce o antebraço e perde o back. Fica opt-in; default idêntico ao antigo (JSON do pré-spec igual byte a byte nas 2 unidades).
- **`fit_spec`**: `joint_term` (`JOINT_W` = 0,5, `--fit-joints`, `fit(..., joints=True)`): distância média em H entre a junta do spec e a do sheet; gancho de 2 linhas no `Objective`. Só testado em unidade (sem run de fit com o termo ligado); `spec_pipeline` não tem a flag ainda.
- **Piorou / pendente.** (1) 2 de 8 juntas lidas: vestuário comum não mostra a junta no contorno; o próximo passo é a vista left (o joelho dobrado de lado) ou o sheet-hard (arestas internas, `edges`). (2) Cotovelo = degrau da corrida mais externa do braço, que em braços colados ao tronco falha. (3) Quadrúpede/serpente/spider: sem `joint_place` (o spider tem `spider_leg`). (4) `--fit-joints` não chega em `spec_pipeline`.
- **Testes.** `test_silhouette.JointMeasures` (degrau, sem degrau, quebra de contorno), `test_preflight.JointPlace` (dentro/fora, silêncio sem medida, `limb`), `test_massing.Joints` (`joint_between`, flag), `test_fit_spec.JointTerm`, `test_spec_pipeline.JointText`.

### 22.L4-1 Kind `chain`: um sweep ao longo dos ossos `prefix.k..` do rig (2026-10-27)

- **O que mudou.** Parte `[bone0, "chain", [r0..rN], [0,0,0], mat, {"bones": N, "sides": 6-8, "profile_axis": "left"|"front"}]`. `bone0` = `prefix.k`; a cadeia passa pelos ossos `prefix.k..prefix.k+N-1`, um anel por junta (cabeça de cada osso + cauda do último), raio r_i, plano do anel bissetor dos dois ossos, tampas n-gon. `at` é ignorado (os ossos posicionam). Peso: anel i no osso i, último anel no último osso (conferido no GLB: um grupo por osso). Um número em `dims` = raio máximo; os outros vêm do sheet (`cut_hull.chain_widths`, corrida de máscara perpendicular ao osso, janela 1,25 r) ou, sem sheet, de um afunilamento até 0,35.
- **Onde.** `lathe_limb.py` (`chain_joints/rings/radii/bones`, `bad_chain`, `set_rig`, `tris`, `half_extent`), `build_unit.swept_part/skin_part/plan_chamfers/load_family`, `preflight` (`part_tris`, `bbox`, `bones` cobre os ossos da cadeia, `load` faz `set_rig`), `spec_pipeline` (KINDS, validate, DSL com cauda/pescoço/serpente), `fit_spec` (`part_points`; `dims` já são os raios, então o fit os move ±10 % sem `PARAMS["chain"]`), `cut_hull.chain_profiles`, `massing._chain_run` (emissor opt-in por papel `tail`/`neck`; nenhuma família de `FAMILIES` o chama antes do L4-4). Estado do rig: `lathe_limb.set_rig(family, extras)`, chamado por quem lê um spec (build_unit, preflight.load, fit, spec_pipeline), porque `bbox(part)` não recebe o doc.
- **Fase do anel.** Hexágono com vértice na horizontal media 0,866 r na vertical (left IoU -0,12 contra o corpo liso); com fase π/(2n) (n não múltiplo de 4) os dois eixos medem 0,966 r.
- **Medida (sem LLM, sem sheet dessas famílias).** Referência = corpo liso sintético (tubos de 16 lados, 8 subtrechos por osso, tampas planas); 6 vistas front/left/back/top/bottom/rts 45_45; chain vs um prisma por osso (`from/to`), mesmos raios. Arquivos em `scratchpad/leva4-chain/`.

| caso | sides | IoU média chain / prisms | pior delta por vista | tris chain / prisms |
|---|---|---|---|---|
| serpent 8 ossos | 6 | .9345 / .9243 | -0,025 (left) | 104 / 160 (-35 %) |
| drake tail 3 + neck 2 | 6 | .9349 / .9133 | -0,050 (rts) | 76 / 100 (-24 %) |
| serpent | 8 | .9801 / .9799 | -0,004 | 140 / 224 (-37 %) |
| drake | 8 | .9804 / .9706 | -0,001 | 104 / 140 (-26 %) |

  `attach.json` loose=0 nos quatro (cabeça/corpo sobrepostos à cadeia); tris = 2·sides·N + 2·(sides−2) confere.
- **Piorou / pendente.** Com 6 lados o pior delta por vista passa de -0,01 (média sobe); com 8 lados passa. Cadeias curtas (N ≤ 3) não chegam a -30 % em tris (tampas pesam). A serpent do rig desce abaixo do chão no fim (y < 0): o raio final tem de ser pequeno. Sem sheet de serpent/drake: a leitura de largura do sheet só foi provada com máscara sintética. `PARAMS["chain"]=("radii",)` não criado: dims já cumprem o papel. Sem papers novos em `docs/references.md`.
- **Testes.** `test_lathe_limb.py::Chain` (tris, anéis nas juntas, raios, validate, cobertura de ossos, fit, emissor do massing, larguras do sheet). Suíte 345 OK; ruff sem achado novo (10 antigos iguais ao base).

### 22.L4-3 Fit hierárquico (`--fit-stages`) e piso por vista (`VIEW_FLOOR`) (2026-10-27) - hierárquico NEGATIVO (opt-in), piso ligado

**O que mudou.** `fit_spec.fit(..., stages=("trunk","limbs","profiles"))`: em vez de um Powell sobre todos os parâmetros, um Powell por estágio sobre o seu subconjunto (tronco = dims/`at` das partes em ossos spine/pelvis/torso/chest/body/abdomen/head/neck; membros = dims/`at` do resto + `rot` + `knee`; perfis = `profile`/squash do lathe), mesmo `Objective`, os outros parâmetros presos no melhor ponto até ali, 1/3 das avaliações e dos segundos por estágio (`stage_masks`, `descend`). `stages=None` (default) é o Powell único de antes, byte a byte. Flag `spec_pipeline --fit-stages` liga; não existe `--fit-flat` porque o flat segue como default. Parâmetros de kinds novos (`chain`/`plate`): extra desconhecido cai no estágio dos membros, `STAGE_OF_EXTRA` mapeia o resto; `PARAMS`/`EXTRAS` não foram tocados.

`spec_pipeline.fit_accepted(..., rig)` ganhou `VIEW_FLOOR`: a vista crítica da família (spider: top/bottom/rts; biped e demais: front/rts) não pode cair mais que `FIT_SLIP` (0.02) frente ao spec anterior, mesmo que não passasse o gate. Antes só vistas que passavam eram protegidas. Os 3 `before -> after` reais acima aceitam (nenhuma vista crítica cai).

**Medida** (`fit/before.json` -> clay real, 6 vistas; soma de margens sobre os gates; 3 provas em paralelo, máquina carregada, por isso os 150 s cortam em 1800-2500 avaliações):

| unidade (run) | modo | front | left | back | top | bottom | rts | margens | red | evals | s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| n00U (v7-r2) | antes | .7547 | .7189 | .7595 | .6881 | .6632 | .6157 | .2501 | .088 | - | - |
| | flat (atual) | .7786 | .7426 | .7856 | .7060 | .6772 | .6217 | .3617 | .100 | 1839 | 152 |
| | hierárquico | .7841 | .7481 | .7932 | .7052 | .6758 | .6173 | .3737 | .096 | 1782 | 152 |
| n005 (v6-r1) | antes | .7239 | .7800 | .7741 | .7153 | .7804 | .8101 | .4838 | .139 | - | - |
| | flat | .8209 | .8056 | .8546 | .7652 | .7846 | .8660 | .7969 | .101 | 2448 | 153 |
| | hierárquico | .8100 | .8012 | .8625 | .7615 | .7931 | .8724 | .8007 | .095 | 2465 | 153 |
| n01X (v6-r1) | antes | .7070 | .7867 | .7091 | .7592 | .7925 | .7626 | .4171 | .196 | - | - |
| | flat | .8252 | .8336 | .8291 | .8570 | .8490 | .8074 | .9013 | .106 | 2485 | 153 |
| | hierárquico | .8114 | .8354 | .8170 | .8143 | .8610 | .7982 | .8373 | .121 | 2120 | 119 |

n005/n01X em v7-r2 não têm vista abaixo de gate + margem: o fit não roda (0 avaliações), por isso a prova usa v6-r1. n00U com câmeras fixadas do `fit.json`; n005/n01X com o sweep. Sem limite de tempo (900 s, só n00U, 4000 avaliações = o teto): flat margens .4175 (front .7921, top .7112, bottom .6870, rts .6239), hierárquico .3938 (.7863 / .7098 / .6768 / .6284).

**Veredito: negativo.** Critério era margens >= flat com <= 2/3 das avaliações no n00U. Avaliações: iguais (cada estágio usa o seu 1/3 inteiro; o Powell não converge cedo em nenhum dos dois, o teto é o orçamento). Margens: hierárquico +.012 (n00U) e +.004 (n005) no corte de 150 s, mas -.064 no n01X e -.024 no n00U sem limite de tempo. Sem ganho consistente, o default continua o Powell único e `--fit-stages` fica opt-in. Se voltar a testar: dar ao estágio que converge cedo o saldo (hoje o saldo some) e rodar com a máquina livre.

Arquivos: `tools/blender/fit_spec.py` (`STAGES`, `stage_masks`, `descend`, `fit(stages=)`), `tools/blender/spec_pipeline.py` (`VIEW_FLOOR`, `fit_accepted(rig=)`, `--fit-stages`), `tests/tools/blender/test_fit_spec.py`. Provas: `scratchpad/leva4-fit/{n00U,n005-v6-r1,n01X-v6-r1,n00U-v7-r2-long}/table.json` e logs.

### 22.L4-8 Diagnóstico LLM como saída: `diagnose.py`, `--diagnose` (2026-10-27)

- **O que mudou.** `tools/blender/diagnose.py <run> --id <u>`: o reviewer (`spec_pipeline.ask`, `session:opus` lê imagens) recebe `compare.png` (concept | clay | wire | overlay | textured), as seções de estágio do `review.md` (uncovered/spill, `worst red` por vista e faixa, zones_clay, preflight; sem Avaliação/Timing/Few-shot/Readiness), as regras de preflight que falham, os `loose` do `attach.json` e um resumo do `spec.json` (por nome de peça: n, kinds, chave de paleta, faixa dos centros). Responde 4 perguntas: (1) por vista que falha ou tem vermelho grande, que peças causam o vermelho e o verde; (2) identidade que falta; (3) três mudanças no spec, em ordem, com ganho esperado; (4) dono do problema: author | massing | fit | dsl. Saída com `--json-schema`: `diagnosis.json` (`findings` = lista de {view, part, colour red|green, cause, fix}, mais `identity`, `changes`, `owner`, `cost`), `diagnosis.md` e o bloco `## Diagnosis (LLM, not fed back)` no `review.md` (substituído, não empilhado, num rerun).
- **Gancho.** `spec_pipeline --diagnose` / `--no-diagnose`: sem flag liga só para CHECK; PASS/SHAPE-PASS só com `--diagnose`. Roda DEPOIS de `write_review` (que gera `compare.png`), logo depois de `spec.json`. Falha da chamada imprime e segue: o diagnóstico nunca derruba o run. `spec_pipeline.USAGE` soma os tokens de `claude -p` (só contador).
- **Nada volta ao modelo.** Testes (`test_diagnose.py`): `spec.json` byte a byte igual com e sem `--diagnose`; o fonte de `stage_one`, `stage_shape`, `repair`, `run_passes`, `fit_stage`, `author_specs`, `best_of_n`, `author_brief`, `make_brief`, `with_fewshot` não menciona diagnóstico; gate default (CHECK sim, PASS/SHAPE-PASS não, flags vencem); resposta inválida recusada; rerun substitui o bloco. Reviewer stub. 345 testes OK; ruff sem achados novos (os 10 existentes são de arquivos não tocados).
- **Prova (session:opus, cópias dos runs em `runs/draft/<id>/leva4-diag-r1/`).**

| run | achados | dono | tempo | tokens (in / cache criado / cache lido / out) |
|---|---|---|---|---|
| n00U v7-r2 (CHECK, rts 0.622 < 0.70) | 9 | author | 56,7 s | 10 / 15 834 / 20 122 / 5 527 |
| hfoo v7-r1 (CHECK, left 0.606 e back 0.694 abaixo do gate) | 14 | author | 54,5 s | 10 / 13 525 / 21 799 / 5 570 |

  Sem custo em API (sessão). Dá ~1 min e ~35 mil tokens de entrada (quase todos de cache) + 5,5 mil de saída por run.
- **Bate com o overlay? (conferido a olho no compare.png).** n00U: sim em quase tudo. Pernas retas "de barraca" dão o vermelho externo no front/back e o verde entre elas; o rts tem verde nos joelhos altos (alto-esquerda/direita) e vermelho na cunha das pernas próximas; top/bottom: cantos vermelhos do casco retangular contra o oval do sheet; left: bloco vermelho do abdômen contra o bulbo. Erros: não cita o back (parecido com o front); a hipótese "joelho a ~0,6 da altura" é plausível, não medida. hfoo: sim. Vermelho atrás das costas no left/back = mochila funda e larga; o verde diagonal da lança no left/rts; o verde do boné (aba Brodie) no left e o espeto no topo do capacete que sai em vermelho no back; os lóbulos verdes dos braços abertos no top/bottom. Notou que o sheet é inconsistente na lança (vertical no front/back, diagonal no left/rts), o que é verdade. Omissões: o vermelho do front (19 %) no ombro/mochila, vista que passa o gate.
- **Limites.** `part` é atribuição por nome + posição no resumo; o reviewer não vê um render por peça, então é hipótese, não medida (hfoo atribui a lança a `forearm.R`). Os "ganhos esperados" são palpites, sem verificação: a fase seguinte é rodar a mudança 1 e comparar. O dono "author" nos dois casos concorda com a leitura do §21 (a lacuna é do spec, não do DSL).
- **Não feito.** Nenhum uso do diagnóstico no autor/repair/fit/variants (decisão do usuário). Sem paper novo em `docs/references.md` (item sem fonte nomeada no ROADMAP).

### 22.L4-2 Kind `plate`: perfil extrudado (2026-10-27)

- **O que mudou.** Parte `[bone, "plate", [w, h, t], at, mat, {"axis": "front|left|top", "profile": 3-8 pts [u, v] em 0-1 de w e h, "bevel": 0-0.3, "rot": ...}]`: o polígono extrudado t ao longo da normal (front: x/y, espessura z; left: z/y, espessura x; top: x/z, espessura y, v = frente), 2 faces n-gon + faixa de quads; bevel = 4 anéis, faces encolhidas pela fração. Sem `profile` o build lê o contorno do sheet na caixa da peça (como `cut`/`lathe`): front/left por `cut_hull.strip_outline`, top por `cut_hull.top_outline` (abertura morfológica `TOP_OPEN` tira as pernas). Geometria em `lathe_limb.py` (`plate_rings`, `bad_plate`, tris = 2(n-2) + 2n·(1 ou 3); sem perfil conta 8 pontos, o build usa ≤ 8), `build_unit.swept_part` (objeto com origem em `at`, rot como o box), `preflight` (`plate_box`: bbox com rot), `spec_pipeline` (KINDS, validate, DSL com asa/carapaça/leme), `fit_spec` (`part_points`; `PARAMS["plate"]=("plate",)`: escala do perfil em u,v ±15 % em torno do centroide, só com perfil gravado por `baked`; w, h, t já andam com `dims`).
- **Orientação do painel top.** O sheet do n00U desenha o top com a cabeça em cima, não embaixo (`views.py` assume frente embaixo). `cut_hull.top_flipped` sobrepõe a união das caixas das peças ao painel nos dois sentidos e lê no melhor. Achado, fora do escopo: o IoU de top/bottom do n00U compara o modelo (cabeça embaixo) com o sheet (cabeça em cima) sem flip.
- **Prova (a), harpy sintético** (n01X hard-v1 + rig harpy + 3 plates em wing1/wing2.upper/wing1.lower, 2 com perfil e rot espelhados, 1 lida do sheet no top): build OK, `attach loose=[]`, tris 740 reais vs 752 estimados (a lida tem 5 pontos, a estimativa 8), asas espelhadas visíveis em front/top/rts (`scratchpad/leva4-plate/harpy3.png`). Estouro de budget (740 > 700) é do n01X já em 620.
- **Prova (b), n00U sobre `v7-r2/spec.json`** (rebuild sem LLM, `--no-fit --no-massing`; Base reproduz .779/.743/.786/.707/.676/.623):

| variante | front / left / back / top / bottom / rts | unc top / bottom |
|---|---|---|
| Base (v7-r2) | .779 .743 .786 .707 .676 .623 | .079 / .075 |
| A: shell (11,13-19) trocado por 1 plate top, lido (sem flip) | .689 .637 .696 .703 .666 .633 | .087 / .099 |
| B: A mantendo o domo 15 | .689 .637 .696 .712 .672 .636 | .073 / .086 |
| C: só o aro (11) vira plate lida | .774 .737 .781 .675 .651 .615 | .126 / .128 |
| C2: aro com flip detectado | .778 .730 .785 .664 .646 .600 | .136 / .153 |
| F: aro + domo viram plates | .754 .720 .761 .644 .620 .595 | .186 / .197 |
| G: base + plate sob o shell, perfil do sheet (flip) | .778 .733 .785 .690 .670 .627 | .078 / .100 |
| H: idem, perfil sem flip | .778 .733 .785 .687 .653 .637 | .072 / .099 |

- **Resultado: negativo na meta.** Nenhuma variante dá top/bottom +0.02 sem perder front: a pilha de frustums do v7-r2 já cobre o top (unc .079), e o plate oval lido do sheet cobre menos que o aro retangular (unc sobe) ou, somado, só aumenta o spill. O que melhora: tris (A: 656 vs 700) e rts +0.01 (A/B). Plate de carapaça sozinho perde o front (-0.09) porque a pirâmide de frustums some. O kind fica opt-in (nenhum default muda); o ganho esperado é em asas/placas/leme, onde a alternativa é um box.
- **Pendente.** Prova com LLM de asa (harpy/drake) em L4-4; `rot` não entra no fit (`rot_allowed` é por osso); a leitura do top assume que as caixas das peças desenham a mesma massa que o painel.
- **Testes.** `test_lathe_limb.py::Plate` (tris, eixos, bevel, rot, validate, `top_outline`, `top_flipped`, pontos e params do fit).

### 22.L4-9 Orientação do painel top/bottom lida uma vez, antes do IoU (2026-10-27)

- **O que mudou.** `silhouette.detect_rotated(panels, model)`: para top e bottom, o melhor IoU (varredura de tilt + espelho) com o painel do CONCEITO girado 180° (`np.rot90(.., 2)`, antes do crop) contra o painel como desenhado; gira só se ganhar por mais de `FLIP_MARGIN = 0.10`. O render nunca é girado e `variants` continua só com o espelho (sem busca em duas orientações: a decisão é uma, antes). `oriented()` aplica a rotação a IoU/uncovered/spill/red (main) e às zonas (`zone_views(rotate=)`, `ids_zones`). `silhouette.json` grava `head` por vista (`top`: `head-down` é o padrão de `views.py`, `bottom`: `head-up`); `spec_pipeline` copia para `top_orientation`, uma linha no review ("sheet top / bottom drawn") e repassa `--rotate` ao estágio de cor (`zones_clay`) para a cor usar a mesma decisão. Flags: `--rotate top,bottom|none` força, sem flag detecta. Escolhi o modelo (não o perfil do sheet) como árbitro: um perfil largura(top) x altura(left) não decide porque o sentido da cabeça no painel left também varia (os quadrúpedes desenham o left olhando para a esquerda, o `views.py` põe a frente à direita); correlação testada nos 9 sheets: 0.4-0.9, sem separação.
- **Prova sem LLM** (`silhouette.py --shape` sobre os GLBs guardados, sheet-hard; `scratchpad/leva4-topflip/{base,new}`). Diferença rotado - como desenhado (melhor IoU, todos os tilts):

| unidade (run) | top | bottom | decisão | IoU top / bottom antes -> depois |
|---|---|---|---|---|
| n00U (v7-r2 clay) | -0.021 | -0.007 | não gira | .707 / .678 -> idem |
| n01N (v2-hard-r2 model) | +0.122 | -0.138 | top gira (head-up), bottom não (head-up) | top .363 -> .496 (uncovered/cover da zona top: cover .346 -> .415, luma L1 .087 -> .273 pior); bottom .500 idem |
| n01X (v7-r2) | +.017 | +.061 | não gira | .816 / .778 idem |
| n005 (v7-r2) | +.036 | -.027 | não gira | .686 / .792 idem |
| n02X (v7-r1) | -.024 | +.017 | não gira | .722 / .700 idem |
| hfoo (v7-r1) | -.037 | -.098 | não gira | .693 / .760 idem |

  Os 4 bípedes e o n00U: todos os campos de `silhouette.json` idênticos aos de antes (comparado chave a chave), só `head` é novo.
- **n00U: negativo.** O sheet desenha o top com a cabeça em cima, mas girar dá .686 contra .707 como está (o clay v7-r2 é um domo de frustums quase simétrico no top): sem confiança, não gira. O ganho do item aparece onde o modelo tem cabeça/cauda assimétrica no top (n01N, quadrúpede: +.13).
- **Sheets novos (sem modelo, o detector não roda): leitura visual.** n017 (lobo): top head-up, bottom head-up (como o n01N). n00H (wyrm): top head-up, bottom head-up. n010 (drake): top e bottom com a cabeça à ESQUERDA (girados 90°, não 180°): não resolvido, o detector só testa 180° e a rotação de 90° fica para quando houver modelo. Quando houver modelo dessas unidades o detector decide sozinho; esperado n017/n00H top girar, bottom não.
- **Pendente.** Luma L1 da zona top do n01N piorou ao girar (o shading do modelo não gira com o painel); `make_compare` e `fit_spec` ainda leem o painel top sem rotação; `cut_hull.top_flipped` (leitura de perfil do plate) não foi unificado, usa as caixas das peças e continua independente.
- **Testes.** `test_silhouette.py::PanelOrientation` (gira só o painel claramente invertido; painel simétrico fica; `oriented` gira antes do crop).

## 23. Leva 5 (2026-10-28)

Sete frentes (L5-1 segmentação, L5-2/2b massing por partes, L5-3 props, L5-4 profundidade, L5-5 superfície, L5-6
identidade, L5-7 juiz), integradas em `feat/models-v2-hard`. Bateria `v9-r1` em 8 unidades (3 de teste, n02X,
hfoo, lobo n017, wyrm n00H, drake n010), gate de acoplamento ligado; imagens em `history/2026-10-28-v9/`
(`*-full.png`: concept | clay | overlay | textured por run).

| unidade | anterior | v9-r1 | veredito | por quê | juiz v9 × anterior |
|---|---|---|---|---|---|
| n01X | .836/.774/.836/.821/.775/.775 | .793/.804/.794/.797/.777/.776 | CHECK | preflight: pés soltos no spec final | sheet v9 3-1; artist/wc3 v8 3-1 |
| n005 | .849/.721/.832/.696/.780/.778 | .795/.803/.814/.717/.716/.879 | CHECK | tris 748; vermelho top/bottom 23/26 % | empate |
| n00U | .770/.744/.782/.688/.666/.609 | **.805/.738/.811**/.664/.654/.622 | CHECK | rts .622; spill rts 31 % | **v9 4-0 nos 3 eixos** |
| n02X | .779/.715/.778/.735/.729/.736 | .777/.732/.755/.683/.678/.751 | CHECK | tris 768; bottom vermelho 20 % | **v9 4-0 nos 3** |
| hfoo | .711/.638/.692/.669/.757/.690 | .766/.637/.666/.786/.817/.634 | CHECK | left .637, back .666, rts .634 | **v9 4-0 nos 3** |
| n017 | .833/.733/.778/.821/.843/.693 | .829/.721/.776/.831/.842/.692 | CHECK | rts .692 | — |
| n00H | .815/.663/.809/.728/.682/– | .813/.633/.807/.736/.685/– | CHECK | spine.3 solta; left .633 | — |
| n010 | .685/.891/.575/.441/.449/.559 | .685/.877/.589/.456/.465/.556 | CHECK | sheet top/bottom girados 90° | — |

0/8 PASS com os gates novos; o juiz de visão prefere o v9 por 4-0 nos três eixos em 3 das 5 comparadas. O que
reprova agora: tris acima de 700 (8 lados + chanfro + lathe), spill/vermelho de top/bottom/rts, `overlap` no spec
final (a edição do autor + fit desprendem pés/pescoço). Próximo: orçamento por grupo recalibrado para os kinds
novos, contato por parte depois do fit, e sheets corrigidos das famílias novas.

### 23.L5-7 Juiz pareado: 4 votos 2+2 e eixo `wc3` (2026-10-27)

- **O que mudou** (`review_pair.py`, `compare_runs.py`). (1) `VOTES = 4`, ordem fixa A|B, A|B, B|A, B|A (`sides()` não embaralha mais; os votos rodam em paralelo, a ordem só rotula). Empate só em 2-2; os 4 votos no mesmo lado físico = viés de posição = empate marcado `(position bias)`. (2) Eixo novo `wc3` ("qual dos dois candidatos lê mais como um modelo de jogo nesse estilo: silhueta limpa, massas claras, nada de caixas empilhadas"): a imagem do voto ganha uma 4ª célula (`left | sheet | right | wc3`, só na linha front) com uma referência WC3 da mesma classe de rig (`WC3_REFS`, rig lido do `spec.json` da run B, recortada ao boneco por `crop_figure`). (3) `pairwise.json` grava os 3 eixos (+ `wc3_proxy`); `lost()` = a run nova perde 2 de 3 eixos (resultado antigo de 2 eixos: perde os dois) e `spec_pipeline.final_status` rebaixa um nível como antes (nenhuma mudança em `spec_pipeline.py`, o gancho já chamava `lost`). (4) `compare_runs.py`: o cabeçalho de cada run mostra `pair vs <A> S B3-1 R B3-1 W tie2-2` (S sheet, R artist, W wc3).
- **Referência WC3.** Só existe render real de biped (`artifacts/reference/wc3-footman.png`, sem textura própria do projeto). Rig sem render (spider, quadruped, ...) usa o `sheet-hard.jpg` front da unidade como PROXY do estilo alvo (`wc3_proxy: true` no JSON): nesses o eixo `wc3` não é independente do eixo `sheet`. Pendente: render de um WC3 de spider/quadruped (`mdx_inspect.py` não achou modelo; `anim-ref/` guarda só `joints.json`).
- **Prova** (`session:opus`, cópias dos runs em `scratchpad/leva5-judge/runs/`, originais intocados; v7-r2 = A, v8-r1 = B; 2 repetições; JSONs `scratchpad/leva5-judge/<id>-rep{1,2}.json`, imagem de voto `work/<id>/vote0.png`):

| unidade (render) | rep 1 | rep 2 | viés | status |
|---|---|---|---|---|
| n005 (clay, ref footman) | sheet B 2-1, artist B 3-0, wc3 B 3-0 (1 voto sem resposta válida) | sheet B 3-1, artist B 4-0, wc3 B 4-0 | não | B ganha 3/3 |
| n01X (textured, ref footman) | sheet tie 2-2 (position bias), artist B 4-0, wc3 B 4-0 | idem | sheet: os 4 votos no lado esquerdo | B ganha 2/3, sheet empata |
| n00U (clay, proxy sheet-hard) | sheet A 4-0, artist A 4-0, wc3 A 4-0 | idem | não | B perde 3/3: rebaixaria |

  - **Estabilidade.** Os vencedores por eixo coincidem nas 2 repetições nas 3 unidades (9/9 eixos); os votos individuais também (as 4 respostas de cada lado idênticas em n01X e n00U; n005 só difere por 1 voto inválido na rep 1, que com 3 votos deu 2-1 em vez de 3-1).
  - **Viés.** n01X no eixo sheet: lado físico esquerdo nos 4 votos nas 2 repetições (escolhe pela cor do torso, a mesma célula, não pela ordem): com 3 votos e lados sorteados isso passava por maioria 2-1 ou empate conforme o sorteio; agora é empate marcado. Artist e wc3 do n01X trocam de lado com a ordem: sem viés.
  - **wc3 separa onde sheet empata?** Sim no n01X (sheet empata por viés, wc3 B 4-0: "massas mais simples e chunky, silhueta mais clara"), MAS o eixo artist dá o mesmo 4-0: nas 6 comparações wc3 e artist concordam sempre (23/23 votos válidos). Informação independente do `wc3` sobre o `artist`: nenhuma nesta amostra. Com proxy (n00U) wc3 = sheet, como esperado.
  - **Custo por par.** 4 chamadas `session:opus` em paralelo, 1 imagem 1792x896 por chamada (≈ 2,1 mil tokens de entrada cada, ≈ 9 mil por par + ~600 de saída), 13-29 s de parede (render Blender em cache incluso nas repetições; 1ª repetição inclui os renders), sem crédito ppq. Antes (3 votos, 1344x896): ≈ 6 mil de entrada.
- **O que piorou / limites.** +33 % de chamadas por par; o eixo `wc3` com biped usa um footman vermelho e brilhante como alvo, o que não separa de `artist` aqui; com 3 eixos, "perde 2 de 3" rebaixa mais fácil que "perde os 2" (n005 e n01X não rebaixam; n00U rebaixa como antes). Resultados de `pairwise.json` antigos (2 eixos) continuam legíveis (`line`, `lost`, `pair_text` ignoram eixo ausente).
- **Testes.** `test_review_pair.py`: ordem 2+2, tally/empate 2-2/viés com 4 votos, `lost` 2 de 3 e resultado antigo, `wc3_ref`/`crop_figure`, imagem de 4 células, `compare_runs.pair_text`.


### 23.L5-6 Consistência de identidade: `identity_present` (preflight) + `identity_reads` (render ID), status (2026-10-27) - relatório, status rebaixa

Feedback n005 (v6-r4, v7-r1, v7-r2): o detalhe azul, os olhos e a lanterna somem entre runs; IoU e zonas grandes não veem (< 3 % da figura).

- **Checklist** (`preflight.identity_items`): `refs/<id>/parts.json` `identity` quando existir (string com "eye/lens/visor" = olhos; palavra de um nome do `props.json` = aquele prop; resto = texto, vai no brief e não é pontuado; fixture à mão `tests/tools/blender/fixtures/parts-n005.json`), senão `props.json` + olhos (decal numa peça de cabeça, só biped). Sempre somados os **detalhes de identidade** do sheet (`silhouette.identity_details`): cor saturada (croma Oklab > 0,04, bins de 40 graus de matiz) com < 3 % da figura em front/left/back e >= 0,1 % em alguma, ou seja crachá, válvula, lentes, lanterna. n005: vermelho `#50252E` (lentes), laranja `#89704B` (válvula), azul `#586B87` (lanterna; o sheet não tem crachá no peito, o "crachá azul" do feedback é o vidro da lanterna). hfoo: azul `#4C6997`. n02X: amarelo pálido `#CBBB9B`. n01X, n00U, h09B: nenhum.
- **`identity_present`** (preflight, `IDENTITY_BLOCKING = False`): prop com peça (`props_missing`), olhos com decal numa osso de cara, detalhe com material usado (ou `decal_color`) de matiz até 30 graus. Linha `k/n, missing: [...]`.
- **`identity_reads`** (`silhouette.py`, gravada em `sil/ids/identity.json` pelo `--ids`): no render ID (cores chapadas) a fração da figura no matiz do detalhe / a do sheet, melhor vista entre as que o sheet mostra, `read` com razão >= 0,5. Detalhe só por decal não é medido no ID (decal não entra no clay): conta pela presença.
- **review/status**: `Identity: 5/6 - missing: ...` no `## Readiness`; `status_of`: PASS com identidade < 100 % fica `prototype-safe` (como o vermelho). Brief: bloco `IDENTITY OF THIS UNIT - these must exist as parts or decals` com a lista. `mesh_lint` não mudou (medida precisa de render, vive em `silhouette.py`).
- **Prova sem LLM** (rebuild de `spec.json` + render ID; `scratchpad/leva5-identity/prove.py`):

| run | identidade | falta |
|---|---|---|
| n005 v6-r4 | 7/7 | - |
| n005 v7-r1 | **4/7** | lentes vermelhas (decal `sheet` sem `decal_color`), válvula (brass `#BFBBBD` cinza), lanterna (sem material azul) |
| n005 v7-r2 | 7/7 | - |
| n005 v7-r3 | 7/7 | - |
| n005 v8-r1 | 7/7 | - |
| hfoo v8-r1 | 5/5 | - |
| n02X v8-r1 | 3/3 | - |

  Bate com o feedback: v7-r1 perde olhos e lanterna (e a válvula, que o feedback não citou); v6-r4, v7-r2 e v8-r1 têm tudo. Leituras no render ID (razão render/sheet): lanterna azul 0,94 (v6-r4), 0,89 (v7-r2), 1,16 (v8-r1); válvula 1,5-3,9; v7-r1 0,0 nas três.
- **Taxa de FAIL** nos specs de `runs/draft` com sheet (83 bípedes/quadrúpedes, só presença): 46/83 = 55 %, dos quais 39 são "olhos" (n01X, golem mecânico, 22/22 sem decal de cara). Sem a linha de olhos: 13/61 = 21 % (< 1/3). Fica relatório (`IDENTITY_BLOCKING = False`); o status, porém, rebaixa como pedido, e um mech sem `parts.json` nunca passa de prototype-safe por causa dos olhos.
- **O que piorou / limites.** (1) "olhos sempre" é injusto com unidades sem rosto até o L5-1 trazer `parts.json` (lista explícita decide). (2) Casamento por matiz: uma cor pequena no mesmo bin de uma zona grande (n02X: pálido `#CBBB9B` ao lado do laranja da pele; o brass `#C8963A` do n02X nem é detectado) infla a leitura (razão 7598) e é satisfeita por qualquer material do mesmo matiz. (3) Bins fixos de 40 graus: cor na borda do bin parte em duas. (4) Decal fora do ID.
- **Testes.** `test_preflight.py::Identity`, `test_silhouette.py::IdentityReads`, `test_spec_pipeline.py::Identity`. `test_preflight.Landmarks` passou a usar regex na coluna (a linha nova alarga a tabela).

### 23.L5-1 Segmentação semântica do sheet: juntas e partes em 2D, triangulação para 3D (2026-10-27)

`tools/blender/segment_sheet.py <id> [--rig ...] [--masks] [--reply parts-reply.json]`. **Uma** chamada ao VLM por sheet (`spec_pipeline.ask`, `session:opus`, schema JSON estrito + `check_reply` com um reenvio): front e left do `sheet.jpg` aprovado (`split_sheet.split`), cada painel com régua 0-1 desenhada (grade a cada 0.1, y para cima) e a card (parágrafo `Redesign` do compendium + `prompts/<id>/props.json`). O VLM só aponta: juntas da família (biped 14 = cabeça/queixo + 6 tipos x L/R; spider raiz+joelho x 8 pernas; quadruped cabeça/focinho/cauda + 4 pernas x raiz/joelho/pé; demais: 5 pontos genéricos), caixa 2D por parte (com `role`, `bone`, `prop`, `anchor`, `depth_hint`) e a lista de identidade. O código faz o resto: x do front, z do left (mesmo quadro de `massing.View`/`side_of`: metros do spec, +z para onde os pés apontam), y = média (gap > 0.05 H vai para `incoherent`, não é escondido); junta `.R` que o left esconde pega o z do gêmeo `.L` (`z_from: "mirror"`); `depth_order` = sinal e faixa (0.04 / 0.12 H) do z do centro da parte contra o torso, ou o `depth_hint` do VLM quando o left não mostra a parte (`depth_src`); `zone` = zona de cor de maior *lift* dentro de caixa x silhueta (uma peça cinza sobre casaco escuro é a zona rara, não a dominante); `--masks` grava caixa x zona x figura em `refs/<id>/parts/<parte>-<vista>.png` (quadrado 768). Saídas versionadas: `refs/<id>/parts.json` (contrato do brief + `incoherent`, `joints_read`, `meta` com segundos e tokens), `parts-reply.json` (a resposta crua: `--reply` retriangula sem chamar o VLM), `parts-overlay.png`.

`preflight.joint_place` lê `refs/<id>/parts.json` (`parts_joints`, `targets["vlm_joints"]`) e compara os 8 tipos (cabeça, queixo, ombro, cotovelo, punho, quadril, joelho, tornozelo; `own_joints` lê o topo/fundo das caixas das peças nos ossos) em vez dos 2 do degrau de largura. Sem o arquivo: comportamento antigo. Continua só relatório (`JOINT_BLOCKING = False`).

**Prova (olhei os 8 overlays em `refs/<id>/parts-overlay.png`).** Juntas: `xyz` = lidas nas duas vistas; `1 vista` = só uma; `na silhueta` = pontos 2D que caem sobre a figura.

| unidade | rig | juntas xyz / 1 vista / nenhuma (esperadas) | na silhueta | incoerências | partes | s | tokens saída |
|---|---|---|---|---|---|---|---|
| n005 | biped | 14 / 0 / 0 (14) = 8/8 tipos | 21/22 | 2 | 18 | 35.8 | 4020 |
| n01X | biped | 14 / 0 / 0 = 8/8 | 22/22 | 2 | 20 | 35.8 | 4074 |
| n02X | biped | 14 / 0 / 0 = 8/8 | 23/24 | 2 | 21 | 44.0 | 4981 |
| hfoo | biped | 14 / 0 / 0 = 8/8 | 22/22 | 6 | 15 | 35.7 | 3780 |
| n00U | spider | 6 / 8 / 2 (16) | 20/20 | 3 | 13 | 30.9 | 3314 |
| n017 | quadruped | 8 / 7 / 0 (15) | 21/23 | 6 | 13 | 35.3 | 3603 |
| n00H | generic | 4 / 1 / 0 (5) | 8/9 | 1 | 7 | 19.8 | 1960 |
| n010 | generic | 4 / 0 / 1 (5) | 7/8 | 3 | 17 | 44.5 | 5292 |

Custo por sheet: 20-45 s, 2-5 mil tokens de saída, ~6-13 mil de cache criado e ~6-16 mil lidos (sessão, sem crédito de API); 1 chamada, 0 reenvios. Os 3 sheets novos (n017, n00H, n010) funcionaram sem card de props (n017 tem `props.json`; os três têm o parágrafo do compendium).

O que o VLM acertou / errou (a olho):
- **n005.** Certo: capuz, máscara (com o focinho/mangueira), tanque com z -0.83..-0.23 contra o torso (`depth_order` -2: atrás), máscara na frente do capuz (+1), joelho/quadril/cotovelo/cabeça a menos de 0.03 H do desenho, lanterna, bolsa e vaporizador no front. Errado: o vaporizador sai cortado na borda do painel; vaporizador/lanterna/bolsa não aparecem no left, então `box3d` é `null` e a profundidade vem do `depth_hint`; punho L com 0.09 H de gap front x left; caixas de braço do left frouxas.
- **n01X.** Quase tudo certo nas duas vistas (cabeça-volante, ombreiras, pistões, fornalha); gaps 0.056-0.067 H (pelve, canela); fornalha sem caixa no left.
- **n02X.** Certo: clava, óculos, respirador, placa de ombro com o X, pano da fusível; o braço L fica cortado na borda do painel (cotovelo/punho L no limite); caixas de antebraço do left frouxas.
- **hfoo.** Certo: capacete, mochila, lanterna, plaquinha; a lança diagonal vira uma caixa que cobre a diagonal inteira no left (caixa 3D enorme: uma caixa alinhada ao eixo não descreve prop inclinado); 6 incoerências de 0.056-0.08 H (cabeça/queixo/capacete: a régua do left leu 0.03 H mais baixo).
- **n00U (spider).** Certo: carapaça, boné-lanterna, olhos, presas, cefalotórax. Errado/limite: oito pernas não se separam em front+left (as pernas escondem umas às outras): 6 de 16 juntas com xyz, 8 numa vista só, 2 nulas; a numeração das pernas é a do rig (dica em texto), mas a identidade de cada uma no desenho é incerta. Não serve para ancorar perna a perna sem a vista top.
- **n017 (lobo).** Certo: cabeça, rabo, arreio laranja, patas; pernas traseiras só no left (7 juntas numa vista). Errado: caixa de torso do front invade a cabeça (gap front x left 0.138 H, arreio 0.171 H: o front vê o peito, o left o corpo todo).
- **n00H.** Certo: cabeça-concha, asas, hoses, válvula da cauda (só no left); `hose_body_upper` com gap 0.10 H (o front vê o S de frente).
- **n010 (drake).** Certo: asas, colar, lâmpada, exaustor; pernas do front com gap 0.123 H; sem a junta `wing_root`/`snout` equivalente no front (1 nula).
- **Zona.** Em casaco todo escuro (n005) as partes escuras caem na mesma zona (#2E2F31); o tanque, o vaporizador e a mão pegam o cinza (#5D6568). A zona só distingue o que a paleta distingue.

`joint_place` (relatório) antes -> depois nos specs existentes: n005 `v4-oneshot-r1` 1 junta (cotovelo 0.51 contra 0.47) -> 8 juntas (cabeça 1.00/0.99, quadril 0.50/0.49, joelho 0.22/0.20 dentro; queixo, ombro, cotovelo, punho, tornozelo OUT); n01X `hard-v1` 1 (joelho) -> 8 (cabeça, queixo, cotovelo, quadril, joelho dentro; ombro, punho, tornozelo OUT). Esses OUT são em parte definição crua do lado do modelo (`own_joints`: o topo do braço é a ombreira, o fundo do antebraço inclui punho/arma, o fundo da canela é o chão sob a bota), não só erro do modelo: por isso fica relatório; calibrar antes de virar gate (taxa de FAIL com 8 juntas é alta).

- **Negativo/limites.** (1) Precisão do VLM na régua: ±0.03-0.06 H por vista (daí `COHERENT = 0.05` marcar 1-6 itens por sheet). (2) Prop inclinado (lança) e prop só visível no front (n005) não têm caixa 3D fiável. (3) Spider: 6/16. (4) Zona não discrimina partes da mesma cor. (5) Os painéis do `split` sobrepõem a borda da vista vizinha (o left do n005 mostra um pedaço do prop do front); o VLM ignorou, mas o painel ideal seria a máscara do `concept_panels`.
- **Fora do item.** Nenhum consumidor além de `joint_place` lê o `parts.json` ainda (L5-2/3/4/6).
- **Testes.** `test_segment_sheet.py` (triangulação com quadro linear: xyz, gap, espelho, caixa 3D, `depth_order`; `check_reply`; schema; ponta a ponta no n005 com VLM stub) e 2 casos em `test_preflight.py::JointPlace`.

### 23.L5-2 Massing por partes: `parts.json` -> uma peça por parte semântica (2026-10-27) - n005 forte, n01X misto; fixtures provisórias

**O que mudou.** `massing.build` lê `refs/<id>/parts.json` (contrato do L5-1) quando existe e, num biped, o pré-spec nasce das `box3d`: `head`/`mask` e prop com nome de cilindro (tank, bottle...) -> `lathe` com perfil lido do sheet DENTRO da caixa (front para o corpo, left para o prop que o corpo esconde); `torso`/`pelvis` -> pilha de frustums (4/3 fatias) com largura, profundidade e centro da faixa cortados pela caixa; `leg` -> `limb` com o joelho de `joints`; `arm` -> dois prismas unidos no cotovelo de `joints` (flag `ARM_LIMB`, removida em 23.L5-2b); `foot`/`hand` -> frustum; `prop` -> peça própria no `bone` (`hand.X` vira `forearm.X`), `box`, fora do volume do torso (a folga/âncora é do L5-3). Material = a cor do slot da paleta mais próxima de `zone`. Sem `parts.json` (ou `parts=False`, `--no-parts`) o massing por faixa fica igual (teste: `build` sem arquivo == `parts=False`); `parts.json` sem peça para algum osso obrigatório cai no massing por faixa. `massing.py ... --parts <json>` roda com outro arquivo. Spider ignora o arquivo.

**Fixtures provisórias.** `tests/tools/blender/fixtures/parts-n005.json` e `parts-n01X.json`: caixas e juntas LIDAS A OLHO no `sheet-hard.jpg` (metros, eixos do spec; sem `box2d`), depois ajustadas até o preflight passar (cabeça do capuz mais larga, cotovelo e punho dentro do alcance). Não são medida: valem até o L5-1 gerar os `parts.json` reais. Os números abaixo medem o PIPELINE com essas caixas, não o L5-1.

**Prova sem LLM** (`spec_pipeline --spec <massing> --no-repair`, estágio 1 do pré-spec sozinho; antes = massing por faixa de hoje, depois = por partes; `scratchpad/leva5-massing/run-*`):

| unidade | | IoU front / left / back / top / bottom / rts | zones_clay mean front / left / back / top / bottom | uncovered front / left / back / top / bottom / rts |
|---|---|---|---|---|
| n005 | faixa | .819 / .674 / .854 / .723 / .837 / .756 | .643 / .072 / .106 / .062 / .325 | .113 / .284 / .107 / .206 / .062 / .100 |
| n005 | partes | .803 / .807 / .854 / .739 / .767 / .839 | .634 / .696 / .672 / .406 / .240 | .089 / .170 / .075 / .199 / .191 / .059 |
| n01X | faixa | .814 / .881 / .815 / .817 / .790 / .805 | .275 / .233 / .248 / .164 / .170 | .076 / .052 / .075 / .083 / .150 / .044 |
| n01X | partes | .806 / .845 / .803 / .785 / .770 / .756 | .288 / .116 / .348 / .175 / .285 | .090 / .082 / .090 / .154 / .065 / .122 |

Preflight 22/22 (n005) e 21/21 (n01X); tris 624 (n005 partes). `attach.json`: 22 peças, 0 soltas (faixa: 23 / 0 em n005; n01X faixa tinha 2 coxas soltas); o tanque é um `lathe` próprio na `spine` atrás do torso (z < -0.5) e a arma uma `box` própria em `forearm.L`.

**Leitura.** n005 (o caso do feedback): left IoU .674 -> .807, zones_clay do left .07 -> .70 e do back .11 -> .67, uncovered left .28 -> .17, rts +.08; custo: bottom -.07 (uncovered .06 -> .19: a caixa do tanque/pé deixa buraco embaixo) e front -.016. n01X (sem props, corpo de blocos): IoU cai .01-.04 em tudo e zones do left piora (.23 -> .12), zones back/bottom sobem; é o fixture a olho (profundidades do braço no left) e não a ideia, mas não há ganho medido neste. Não vira default para ninguém: só liga onde `refs/<id>/parts.json` existe.

**O que piorou / achados.** (1) `arm` como UM limb quebra `shoulder_span`/`fist_span` do preflight (0.79 vs sheet 0.46): a regra lê a caixa do membro inteiro na faixa do ombro; por isso `ARM_LIMB = False` (2 prismas) e ombro/cotovelo respeitam o `REACH` do massing por faixa. (2) Lathe de oito lados no tanque faz `budget_split` falhar (pernas 18 % < 19 %): cabeça, máscara e tanque saem em 6 lados (L5-5 refaz a superfície). (3) O `overlap` com o tanque encostando 0.02 m no torso passa; a regra de âncora é do L5-3. (4) `limb`/`lathe` aceitam 6-8 lados: o laço de lados do massing (10, 12) é cortado em 8.

**Testes.** `test_massing.py::PartsBuild` (sem arquivo == `parts=False`; tanque lathe atrás do torso e arma própria; parts.json incompleto cai no massing por faixa; joelho do `limb` == junta).

### 23.L5-2b Massing por partes robusto com o `parts.json` REAL (2026-10-27) - `PARTS_MASSING = True`

**O que mudou** (`massing.py`, só ele e os testes). Com o L5-1 real o pré-spec dos 4 bípedes reprovava symmetry, fist/shoulder_span, boot_height/feet_mass, budget_split e (hfoo) overlap. Agora `parts_prespec`: (1) `symmetric_doc`: centra a figura em x = 0 (mediana do ponto médio dos pares L/R de juntas; hfoo vinha 0.13 m deslocado), faz a média espelhada de cada par de juntas e, por par (role, osso) de peças do corpo, toma o lado melhor lido (mais juntas do segmento dentro da caixa, depois o maior volume) e o espelha no outro. (2) Tamanhos vêm do sheet, a `box3d` só dá posição/ordem: raio de braço/perna = caixa cortada a 1.2x o raio que o sheet mostra (`arm_geometry`/`leg_geometry`), bota = altura/comprimento do `measure` (faixas 0.85-1.2 / 0.9-1.25, piso 0.05 H), cabeça = união das partes do osso `head` (capuz + máscara; some o "head solta" do hfoo) com largura cortada a 0.7-1.3 do `head_width` só se sairia de `HEAD_BAND`, cotovelo no `REACH`, punho na `fist_span`; um braço = UM par de prismas (antes cada parte `arm` emitia os dois: 4 prismas por braço e simetria quebrada). (3) `clamp_widths`: peça cujo bordo externo passa do teto da banda (shoulder_span/fist_span/stance) entra (o pique do hfoo e o porrete do n02X); `touch`: peça de corpo cujo box a 80 % não cruza o pai/osso anda até o vizinho (prop nunca anda). Prop-bastão inclinado (x fino, y e z longos: o box é a diagonal) vira prisma de canto a canto. (4) `balance`: se a fatia de tris (cabeça, corpo, pernas) sai da banda do `budget_split`, tira lados de quem passa e dá a quem falta (lathe da cabeça, prismas do braço, limb da perna). (5) `settle`: antes de tudo preenche o grupo (head/trunk/arms/legs) que o `parts.json` deixou vazio com o massing por faixa, e depois, regra a regra do preflight, troca SÓ o grupo culpado (`CULPRIT`) pelo da faixa; só `None` se nenhum grupo sobra. `PARTS_MASSING = True`; `load_parts` só para biped (spider e as 3 famílias nem abrem o arquivo; teste).

**Prova sem LLM** (`spec_pipeline --spec <massing> --shape-only`, estágio 1 do pré-spec sozinho, sheet.jpg; faixa = `parts=False`; `scratchpad/leva5-massing2/before-after.md`, `<unit>-<band|parts>/compare.png` lado a lado):

| unidade | | IoU front/left/back/top/bottom/rts | média | uncovered médio | zones_clay médio f/l/b/t/bo | tris | soltas (attach) | preflight |
|---|---|---|---|---|---|---|---|---|
| n005 | faixa | .76/.58/.81/.70/.81/.74 | .733 | .172 | .58/.07/.11/.06/.32 | 468 | 3 | 23/23 |
| n005 | partes | .76/.81/.80/.74/.74/.83 | .778 | .145 | .59/.67/.65/.48/.08 | 480 | 0 | 23/23 |
| n01X | faixa | .84/.83/.84/.79/.73/.78 | .802 | .092 | .26/.21/.24/.12/.18 | 456 | 2 | 21/21 |
| n01X | partes | .78/.83/.78/.78/.74/.73 | .775 | .143 | .20/.16/.26/.26/.28 | 432 | 0 | 21/21 |
| n02X | faixa | .58/.62/.56/.71/.69/.73 | .648 | .162 | .29/.16/.21/.23/.16 | 468 | 0 | 22/23 (fist_span) |
| n02X | partes | .79/.71/.74/.64/.67/.72 | .712 | .155 | .38/.30/.34/.24/.32 | 528 | 0 | 23/23 |
| hfoo | faixa | .37/.46/.37/.70/.69/.53 | .519 | .168 | .01/.03/.01/.06/.02 | 468 | 4 | 21/23 (fist_span, overlap) |
| hfoo | partes | .70/.55/.61/.51/.54/.48 | .564 | .294 | .28/.20/.16/.10/.11 | 444 | 0 | 23/23 |

Preflight PASS nas 4 unidades, nenhum grupo caiu para a faixa (antes: 17-19/23). Mesma tabela das 4 com `SLOW=1 python3.14 -m unittest tests.tools.blender.test_massing.RealParts`.

**O que piorou.** n01X perde .03 de IoU médio e ganha uncovered (.09 -> .14): as caixas de punho/ombreira do VLM em n01X são maiores que o que o corte `HAND_MAX`/raio mantém. hfoo: uncovered .17 -> .29 (o pique vira prisma fino; o sheet o conta como silhueta) e top/rts caem; o "bastão" assume sempre inclinação para a frente (`ponytail`). O `measure` do `sheet-hard.jpg` é lixo (boot .01, foot_length .76 no n005): os testes e o pipeline usam o `sheet.jpg` como régua. O preflight de hfoo/n02X só passa porque a banda `stance` conta o pique/porrete: fixar isso é do `measure`, não do massing. Descartado: braço como UM limb (continua quebrando shoulder_span).

**Testes.** `test_massing.py`: `PartsBuild` (default ligado, grupo ausente vem da faixa, joelho == junta, não-biped não lê o arquivo), `Conform` (centragem, espelho do lado melhor lido, teto de banda, balance), `RealParts` (`SLOW=1`).

### 22.L4-4b Massing e medidas de quadruped, wyrm e drake (2026-10-28) - massing pronto, LLM melhora mas nenhum passa o estágio 1

- **O que mudou.**
  - `silhouette.centreline` / `body_line`: linha central focinho -> ponta da cauda do painel left, caminho de custo mínimo (`(R/(d+1))^2`, d = distância à borda, Dijkstra em `scipy.sparse.csgraph`; asa e perna são galhos que o caminho não toma). 17 pontos `[x, y, raio]` em frações de H (x desde o focinho, y para cima). `floor` (0,25 no quadruped) descarta o que está no chão: a corda do n017 não vira a cauda.
  - `measure_quadruped` (tronco = pontos com raio >= 0,6 do maior, barriga, colunas das pernas em altura de joelho, afastamento e raio das patas pelo front/left), `measure_chain` (linha + asa: `wing_numbers` do front, `wing_blob` do left = o maior blob que sobra tirando os discos de 1,3 x raio da linha), `measure_rig(family, sheet)` (spider, quadruped, wyrm, drake; o resto `None`). `concept_panels` usa `blob=True` sozinho para `BLOB_SHEETS = (n017, n00H, n010)` (pelo nome da pasta; os outros sheets seguem no corte antigo, ver 22.L4-4a).
  - `rig_families`: `scale_quadruped/wyrm/drake(m)` refazem a tabela com os mesmos ossos (clipes e retargets seguem), topo = `HEIGHT` (o da tabela fixa), `SCALERS`, `scale_rig(family, measure)` (os spiders entram no mesmo despacho; sem medida a tabela fixa fica). Chamado em `build_unit.load_family`, `preflight.load`, `fit_spec.fit`, `spec_pipeline.set_rig` (agora `RIG_MEASURE` vale para toda família de `SCALERS`; `--fixed-rig` desliga) e `massing.build`. O spec leva `rig_measure` (a linha inteira) e `massing_spec` põe `"rig"` no pré-spec (sem ele a cadeia procurava ossos no biped).
  - `spec_pipeline.measured_text`: `rig_text_of(m)` (comprimento, linha a cada 4 pontos, tronco/barriga/pernas, asa) e `SCALED_NOTE` no brief.
  - `massing.py` (`FAMILIES` + 3): quadruped = 8 tijolos `frustum` em z (altura pelo contorno do left sem as pernas, largura = min(top aberto, front) x `WIDTH` 0,9), 4 `limb` nas pernas do rig + pata (tijolo), cabeça em 4 tijolos, cauda `chain`; wyrm = `chain` nos 6 ossos `spine.k` (raio = raio da linha x `CHAIN_FAT` 1,1) + cabeça em 3 prismas + 4 `plate`; drake = tronco em tijolos (altura = a da barriga espelhada na linha, a asa esconde o dorso), pescoço e cauda `chain`, cabeça em prismas, asas. Asa = lâmina: `plate` eixo `left` com o contorno do blob do left (metade interna no osso `upper`, externa no `lower`, 8 % de sobreposição), inclinada (`rot` z = -/+ atan(dx/dy) do eixo da asa no front), espessura = largura média das linhas do front x `WING_FAT` 1,3 x cos. A metade interna ganha um vértice dentro do corpo (ponto da linha mais perto do pé da asa, >= 0,06 H abaixo do blob) para o mesh encostar no corpo: sem isso `attach` dava `loose` nos dois. `DETAIL = ((6, 0), (8, 0), (8, 0,15))` (lados, bisel) até passar o piso de 400 tris.
  - `preflight.family_place` (relatório, `FAMILY_BLOCKING = False`): comprimento (extensão z das peças que não são plate) e vão das asas (extensão x dos plates) dentro de x0,8-1,25 do sheet. Taxa de FAIL: 0 de 12 (3 pré-specs + 9 variantes do autor); não há spec antigo dessas famílias, então fica relatório.
  - `fit_spec`: sem mudança além de `scale_rig`; `part_points` de `limb`/`chain`/`plate` já existiam.
- **Prova sem LLM** (massing sozinho, `--shape-only`, 6 vistas; n00H sem RTS, `--no-rts`; n010 top/bottom estão girados no sheet, fora do que o gate sabe ler):

  | | IoU front / left / back / top / bottom / rts | média | uncovered médio | tris | preflight | attach loose |
  |---|---|---|---|---|---|---|
  | n017 quadruped | .800 .701 .742 .775 .856 .680 | .759 | .102 | 412 | 12/12 | 0 |
  | n00H wyrm | .739 .650 .739 .665 .639 - | .687 | .199 | 400 | 11/11 | 0 |
  | n010 drake | .681 .852 .528 .439 .445 .545 | .582 | .336 | 520 | 11/11 | 0 |

  Sem número "antes": essas famílias não tinham massing. Com o fit (`fit-<id>`, mesmo spec, 1500-1800 avaliações; clay real antes -> depois): n017 front .800 -> .831, left .701 -> .721, back .742 -> .776, top .775 -> .786, bottom .856 -> .856, rts .680 -> .692; n00H .739 -> .801, .650 -> .651, .739 -> .797, .666 -> .732, .640 -> .678; n010 .681 -> .681, .852 -> .859, .528 -> .571, .439 -> .458, .445 -> .466, .545 -> .582. O fit não quebrou nenhuma das três (`bones`, orçamento e preflight seguem; n017 e n010 `loose` 0).
- **Prova com LLM** (`session:opus`, 1 run, tudo default menos `--rig` e `--no-rts` no n00H; `runs/draft/<id>/leva4-fam-r1/`): todos CHECK, estágio 1 FAIL na silhueta, preflight PASS, `family_place` PASS.

  | unidade | variante escolhida | IoU final | média (massing -> autor) | tris | attach | o que reprova |
  |---|---|---|---|---|---|---|
  | n017 | 1 de 3 | .833 .733 .778 .821 .843 .693 | .759 -> .783 | 568 | 0 | só rts (.693 < .70) |
  | n00H | 2 de 3 | .815 .663 .809 .728 .682 - | .687 -> .739 | 628 | 1 (`spine.2_2`, peça do autor) | nenhuma vista medida abaixo do gate; a silhueta ainda reprova (o RTS ausente é a hipótese, não conferida) |
  | n010 | 3 de 3 | .685 .891 .575 .441 .449 .559 | .582 -> .600 | 636 | 0 | front .685, back .575, rts .559, top/bottom |

  O autor melhora o massing em +0,02 a +0,05 de média, sem tirar nenhuma unidade do CHECK. O diagnóstico automático (CHECK) do n00H aponta a raiz da asa interna como caixa funda atrás da borda de ataque (`diagnosis.md` da run).
- **Piorou / limites.**
  - n010: top/bottom (.44/.45) estão no sheet girado 90° (cabeça à esquerda). Girar o conceito só soma +0,03 (top .473) e +0,10 (bottom .542): a lâmina não desenha a planta da asa. Front/back baixos (.68/.53) porque a lâmina é reta e a asa do sheet alarga na base; back também porque o sheet desenha as duas asas diferentes.
  - Asa = lâmina de espessura constante; planta larga exigiria 2 plates por asa (um no plano do front, outro no do top) ou `rot` em y. Não feito.
  - n017: a linha termina na ponta da cauda fofa (acima de 0,25 H); a corda no chão fica como `uncovered` no left (.207). Pernas retas (sem joelho dobrado: o fit move `knee`), tronco em degraus (aparece no RTS: .680).
  - Larguras do tronco pelo top aberto/front: o sheet do n017 desenha o top mais largo que o front (spill de 16-21 % no front/back no massing sozinho).
  - O fit pode soltar o plate interno do corpo no mesh (n00H: `loose` 2 após o fit; o `loose_of` do fit usa caixas). Não corrigido.
  - Efeito colateral: `concept_panels` mudou para n017/n00H/n010 (blob). `ensure_rts` desenhou `refs/n017/sheet-hard-rts.jpg` e `refs/n010/sheet-hard-rts.jpg` na prova (2 chamadas de imagem, ~US$ 0,005; o n00H foi com `--no-rts`).
- **Não feito.** Leitura de pata/pé (tijolo fixo), cauda do wyrm (a ponta com hélice é prop), `props.json` do n00H/n010, plano `top` das asas, RTS do n00H (precisa de sheet), recalibrar `GATES` por família (o front do drake só chega perto com asa de planta larga).
- **Testes.** `test_silhouette.Families` (linha central e chão, asa, `measure_rig`), `BlobPanels` (nome da pasta), `test_rig_families.ScaledByLine`, `test_massing.Families` (ossos cobertos, orçamento, asas espelhadas), `test_preflight.FamilyPlace`, `test_spec_pipeline.MassingCarriesItsRig`. Suíte 385 OK; ruff: 10 achados antigos, nenhum novo.

### 23.L5-3 Props separados do corpo: `opts {"prop", "anchor"}`, `prop_clearance`, `prop_reads` (2026-10-27) - regras novas só relatório

- **O que mudou.**
  - DSL: `opts {"prop": "<nome>", "anchor": "hand.R|hand.L|back|belt|head"}` em qualquer kind (brief: item PROPS). Várias peças com o mesmo nome formam um prop (tanque + válvula). `preflight.PROP_ANCHORS` liga a âncora ao osso (`forearm.R/L`, `spine`, `pelvis`, `head`); sem o osso no rig, vale o osso da peça.
  - `preflight`: `overlap`/`overlap_80` não pedem mais que o prop cruze o pai; ele precisa chegar à caixa do corpo na âncora (peças não-prop do osso; mão = os 40 % de baixo) com folga `PROP_REACH = 0.05`, ou tocar uma peça já presa do mesmo prop (`loose_props`). Peças prop não contam como "irmã" que conecta um membro. `symmetry` ignora peça prop (o par `.L/.R` com `asym` continua isento). `props_present` deixa a peça marcada reivindicar o prop primeiro. Regra nova `prop_clearance` (`CLEARANCE_MAX = 0.20`, `CLEARANCE_BLOCKING = False`): fração da caixa do prop dentro da união das caixas não-prop de spine/pelvis/head/body/abdomen (grade 12^3).
  - `build_unit`: `prop_rows` move o prop para o osso da âncora (skin 100 % nele) e, se o corpo usa o mesmo material, dá a ele `prop_<nome>` (cópia da cor e da superfície, só enquanto restar slot abaixo de 8); o prop fica fora do `union` (componente próprio); `attach.json` ganhou `props: [{part, prop, bone, gap}]` e o prop só é `loose` se a malha ficar a mais de `PROP_GAP = 0.03` do corpo da âncora ou de uma peça presa do mesmo prop. Textura: arg `propcrops=<json>` (`colour_stage.prop_args`: `prop_measure.crop_props` + `match_prop` liga o nome da peça à n-ésima entrada de `props.json`/n-ésimo recorte) projeta o recorte do `sheet-props` na face da frente da peça (de trás para âncora `back`; recorte deitado vira em pé numa peça alta), como decal de célula própria e só nas faces daquela peça. Fundo do recorte = cor da borda.
  - `fit_spec`: peça prop nunca fica livre (dims congeladas) e `carry_props` leva `at`/`from`/`to` pelo deslocamento médio das peças não-prop do osso da âncora (dentro do objetivo, o cache de hulls não guarda prop).
  - `prop_reads` (relatório, `PROP_READS_BLOCKING = False`): `spec_pipeline.prop_reads` reconstrói o spec com cada prop numa cor chapada própria (`build_unit propid`, `preflight.PROP_IDS`), renderiza como o render ID e exige, nas vistas em que o sheet mostra o prop (`prop_measure.prop_views`: `refs/<id>/parts.json` se existir e nomear o prop, senão `props.json`: "back" no `where` -> left+back, resto -> front+left), um pedaço do prop com >= 0.2 % da figura e >= 50 % do que aparece dele. Linha `prop_reads` no review e `prop_reads` no `silhouette.json`.
  - `prop_measure.prop_parts` usa as peças marcadas com âncora de mão antes da heurística de tamanho.
- **Prova sem LLM** (`scratchpad/leva5-props/`; specs `runs/draft/<id>/v8-r1/spec.json` com as peças de prop marcadas à mão por `mark.py`: n005 tanque+válvula (back), vaporizador (hand.L), lanterna (belt); hfoo lança (hand.R), mochila (back), lanterna (belt); n02X clava (hand.R)).
  - Rebuild (`spec_pipeline --spec ... --no-fit`, clay, 6 vistas): IoU idêntica à do spec sem marcas, delta 0.000 nas 18 medidas (n005 .849/.720/.832/.696/.780/.777; hfoo .711/.641/.697/.665/.752/.690; n02X .775/.712/.779/.732/.729/.736). Esperado: marcar não mexe em geometria; o que muda é bookkeeping, skin, material, textura e regras.
  - `fit_spec --margin 0.2 --seconds 70` no spec marcado (IoU antes -> depois, front/left/back/top/bottom/rts): n005 .853/.719/.828/.693/.779/.783 -> .865/.772/.858/.700/.773/.810; hfoo .710/.646/.687/.670/.754/.687 -> .721/.655/.711/.717/.798/.688; n02X .784/.693/.790/.734/.705/.735 -> .807/.683/.798/.779/.743/.778. Pior queda: n02X left -0.010 (limite 0.02). Dims dos props idênticas antes/depois nas 3 unidades (15 a 22 peças do corpo mudaram); sem marcas o fit do n005 encolheu tanque, válvula e lanterna (dims .361 -> .357, .223 -> .220, .085 -> .079) e a mesma execução deu .863/.784/.831/.703/.776/.799.
  - `prop_clearance` (% da caixa do prop dentro do corpo), spec marcado antes do fit -> depois: n005 lanterna 42 -> 33, tanque 26 -> 24, vaporizador 0; hfoo lanterna 67 -> 67, mochila 19 -> 26, lança 51 -> 42; n02X clava 12 -> 0. (A caixa de um frustum cobre o maior dos dois topos: a lança em pé ao lado do tronco larga do hfoo conta 51 %; medida por caixa, como pedido.)
  - Calibração da regra nos 52 specs biped com `props.json` de `runs/draft/*/*/spec.json`, peças reivindicadas por `props_present` marcadas em memória (âncora `back` se "back" no `where`, `belt` no pelvis, `hand.<lado do osso>` no resto): `prop_clearance` OUT em 43/52 (83 %; mediana 37 %, quartis 3/37/58, máx 100) -> **fica relatório** (limite 1/3). `overlap` pela âncora reprova 41/52 contra 2/52 pela regra antiga: a calibração é pessimista (as peças do autor ficam no osso `arm.*` ou soltas por um vão de 0.05+ do tronco, e a âncora de mão é a metade de baixo do antebraço) e nenhum spec existente tem marca; a regra só vale para peça marcada. Vigiar a taxa de preflight FAIL nos primeiros runs que usarem a marca.
  - `attach.json` dos 3 rebuilds: gap da malha ao corpo da âncora n005 lanterna 0.171 (solta), tanque 0, vaporizador 0; hfoo lanterna 0.214 (solta), mochila 0, lança 0 e 0.016; n02X clava 0, 0, 0. As lanternas do n005/hfoo flutuam ao lado do quadril: o `overlap` antigo não via (o osso `pelvis` não tem pai no `parents`); é o sintoma "a lanterna some" do feedback.
  - `prop_reads` (parcela da figura): n005 lanterna f .014 / l .016, tanque l .184 / b .303, vaporizador f .033 / **l .000 HIDDEN** (preso à mão `.L`, atrás do corpo na vista left); hfoo lanterna .015 / .005, mochila .111 / .220, lança .054 / .047; n02X clava .050 / .076. 1 de 14 pares prop x vista reprova (7 % de FAIL, sensato: o vaporizador sumiu na left), por isso a regra pode virar gate depois de mais runs (hoje 3 unidades).
  - Compare lado a lado (antes sem marca | depois com marca, textura cel, vistas front/left/back/wc3, mais a coluna `sheet-props`): `scratchpad/leva5-props/compare-{n005,hfoo,n02X}.png`. O prop lê como objeto próprio: tanque (costas) e mochila (costas) ganham o desenho do sheet-props na face de trás; a lança e a clava são peças finas, o recorte vira uma tira. O vaporizador do n005 ganha o recorte da arma.
- **O que piorou / negativo.** (1) A textura do recorte é tosca: célula de 64 px do atlas, projeção de caixa esticada sobre a caixa da peça (lathe do tanque mostra o contorno do desenho dentro da peça), lança/clava viram tira; só vale como placeholder de alpha. (2) `prop_clearance` por caixa superestima frustums largos (83 % OUT). (3) O material `prop_<nome>` nasce com a mesma cor: no render ID o prop e o corpo do mesmo material continuam da mesma zona (a vantagem é a skin/slot, a leitura separada vem do `propid`). (4) `fuse` (remesh) ainda funde tudo; só `join` e `union` respeitam o prop. (5) Prop em osso sem peça de corpo (âncora sem peça) não é julgado.
- **Pendente.** Brief do autor com a lista `props.json` já pede uma peça por prop; falta o autor aprender a marcar (rodar `--variants` com `session:opus` depois da leva). `refs/<id>/parts.json` (L5-1) só é lido por `prop_views`, sem fixture ainda. Gate: `CLEARANCE_BLOCKING` e `PROP_READS_BLOCKING` quando houver runs com marca.
- **Testes.** `test_preflight.py::PropParts` (alcance da âncora, válvula presa ao tanque, fração dentro do corpo, relatório, par `.L/.R`), `test_fit_spec.py::FitProps` (dims e seguimento da âncora), `test_prop_measure.py::MarkedProps` (nome -> recorte, vistas, `prop_seen`). 389 testes OK; ruff com os mesmos 10 achados anteriores (nenhum novo).


### 23.L5-4 Profundidade e oclusão no fit: máscara por parte e ordem z dura (2026-10-27) - opt-in `--fit-parts`, NEUTRO nas silhuetas

- **O que mudou** (`tools/blender/parts_fit.py` novo, ganchos em `fit_spec.py`, flags em `spec_pipeline.py`; tudo opcional, sem `parts.json` nada muda):
  - `refs/<id>/parts.json` (contrato do brief da leva 5; `--parts <arquivo>` aponta outro) lido por `parts_fit.load`. Fixture provisória, **feita a olho** do sheet até o L5-1 existir: `tests/tools/blender/fixtures/parts-n005.json` e `parts-hfoo.json` (12 partes cada, caixas 2D em fração do crop do `split_sheet`, `box3d` triangulada de front x left, `depth_order`; o campo `_note` diz que é provisória). Não é medida do VLM: as caixas são grosseiras.
  - `associate`: cada peça do spec ganha a parte semântica mais próxima: custo = distância do centro à `box3d` (em H) + 0,15 se o osso é de outra família (`forearm/hand` = `arm`, `thigh/shin/foot` = `leg`) - 0,05 se a zona de cor da parte é a do material da peça; empate pela menor caixa; > 0,1 H de toda caixa = sem parte. n005: 28 de 28 peças associadas, a arma (`forearm.L` material tank) cai em `pistol` e o tanque em `tank`.
  - **(a) máscara por parte:** `PartTerms.term`: 1 - fração da projeção *visível* de cada peça que cai dentro da máscara da sua parte (front e left), máscara = `box2d` x figura x zona de cor (`fit_spec.Zones.labels`). Peso `PART_W = 0.2`. É o termo de zonas (§21.F4) generalizado de uma cor para uma parte. Nunca espelha (a caixa está na esquerda/direita da imagem, a câmera é fixa); o IoU pode preferir o espelho, o termo não.
  - **(b) ordem de profundidade:** pares (A na frente de B) de `depth_order` diferente com caixas front sobrepostas viram restrição na z do centro das peças (`near` da vista front). Par que valia e quebra = penalidade `PENALTY` (mesma regra do preflight); par que já estava quebrado custa `DEPTH_W = 0.3` cada, para o fit poder consertar. n005: 41 pares, 2 quebrados no spec do autor (hfoo: 21 e 4).
  - **(c) oclusão no proxy:** `PartTerms.visible` pinta as peças de trás para a frente (z por vista: front `-y`, left `-x`) num mapa de rótulos; a parte de trás só é julgada onde aparece (o tanque atrás do tronco não é cobrado pela máscara do tronco). Peça totalmente escondida vale 1.
  - **Quem se mexe:** além das peças da faixa que falha, entram as peças com fração < `PART_POOR = 0.85` ou numa quebra de ordem (`misplaced`): o fit roda mesmo com todas as vistas acima do gate (o spec do n005 estava, e o fit padrão devolvia o spec intacto).
  - Flags: `spec_pipeline.py --fit-parts` / `--parts <json>`; `fit_spec.py --fit-parts` / `--parts`; `fit(partfit=False, parts_path=None)`. `fit_accepted` não mudou.
- **Prova sem LLM** (spec do autor `runs/draft/<id>/v8-r1/fit/before.json`; `spec_pipeline --spec ... --no-repair --shape-only --variants 1`, fit ligado, clay real das 6 vistas, saídas em `scratchpad/leva5-depth/`). Padrão = fluxo de hoje; n005 não roda fit nenhum (nenhuma vista abaixo do gate + 0,02), o teste de `cut` rejeita:

  | | front | left | back | top | bottom | rts | uncovered left | uncovered top | soltas (attach) |
  |---|---|---|---|---|---|---|---|---|---|
  | n005 padrão | .849 | .720 | .832 | .696 | .780 | .777 | **.215** | .105 | 3 |
  | n005 `--fit-parts` (escolheu `cut`) | .848 | **.802** | .881 | .689 | .810 | .817 | **.142** | .211 | 0 |
  | hfoo padrão (fit clássico) | .691 | .642 | .668 | .670 | .761 | .691 | .174 | .277 | 3 |
  | hfoo `--fit-parts` | .713 | .635 | .688 | .658 | .751 | .683 | .189 | .293 | 3 |

  n005: left uncovered 21,5 % -> **14,2 %** (meta < 15 % batida), soltas 3 -> 0, left +.082, rts +.040. Mas **o top piorou**: uncovered 10,5 % -> 21,1 % (IoU .696 -> .689), spill top melhorou (.242 -> .156); a malha do top fica mais amassada no compare (`compare-n005-final.png`). hfoo: front/back +.02, left/top/bottom -.01, uncovered pior em todas as vistas que importam: **negativo**.
- **Ablação (n005, mesmo spec; fit forçado a rodar em todas as peças com o objetivo antigo = `margin 0.5`; clay real, sem o teste de `cut`):** left/uncovered left/soltas: antes .720 / .215 / 3; objetivo antigo forçado .792 / .167 / 2; só ordem z (`PART_W = 0`) .780 / .170 / 3; termo + ordem .772 / .173 / 1 (depois da correção do espelho, abaixo); com `--depth` .772 / .174 / 1. **Ou seja: quase todo o ganho de silhueta vem de o fit rodar nas peças todas, não do termo de parte**; o termo + ordem mexe pouco no IoU/uncovered e sobe a fração de parte dentro da máscara (proxy, caixas a olho, vale só como direção): n005 .459 (antes) -> .567 (objetivo antigo) -> .597 (parte); hfoo .342 -> .408 -> .460 (pares quebrados 4 -> 1 -> 0). As linhas "só termo" e "termo + cut" da primeira rodada foram feitas com o termo espelhado pelo `flipped` do IoU (bug: em n005 o front prefere o espelho por 0.002 porque o painel está cortado, abaixo) e não entram na tabela; o `cut` do fluxo real da tabela de cima foi rodado depois da correção.
- **Arma e máscara deixam de fundir?** Não de forma que o olho veja: no n005 a arma continua colada no antebraço no front (`compare-n005-final.png`, `compare-n005.png`), a máscara continua dentro do capuz; o tanque ganha um bloco próprio no left. A fração de parte dentro da máscara da arma sobe de .13 (antes) e .19 (objetivo antigo forçado) para **.38**; máscara .44 / .57 / .49 e tanque .32 / .40 / .38 (não melhoram sobre o objetivo antigo; caixas a olho, uma peça de 100 px). Sem ground truth de parte (L5-1 não existe) isto é o que dá para dizer.
- **Achado fora do escopo (não corrigido, `silhouette.concept_panels`):** nos sheets cuja arma encosta na borda do painel o corte do front/left cai no terço da página e **fatia a arma do n005**: `gaps(...)` devolve (0,30), (287,298), (477,511), (758,768); o código pega os 2 maiores vãos *antes* de filtrar os internos e sobra só um, então usa `size // 3`. O painel front perde o cano (cortado em x = 256) e o left ganha uma lasca verde de arma (`scratchpad/leva5-depth/panels-n005.png`). Correção de uma linha: filtrar os vãos internos antes de `sorted(...)[:2]`. Muda os números do n005 (e de qualquer sheet que hoje cai no fallback); por isso não foi aplicada aqui. Parte do "arma some" do feedback pode ser isto.
- **Limites:** associação por centro de peça é grosseira (peça `head` coat em 2,5 m cai em `mask`, par de ordem falso); a ordem é por centro, não por superfície; só front e left; spans (`from/to`) ignoram `rot`; o fit gasta o teto de 150 s (1600-2100 avaliações, ~90 ms cada com a máquina carregada: o termo e as vistas de turntable custam ~2x). Decisão: **opt-in** (`--fit-parts`); virar default só com parts.json real do L5-1 e se o top não piorar.
- Papers: Sketch2Mesh 2021 (contorno 2D multi-vista; aqui a máscara de parte é a generalização da zona), Wiersma 2026 (ordem z como restrição dura).

### 23.L5-4b `--depth`: Depth Anything V2 small inicializa z e ordem (2026-10-27) - NEGATIVO/neutro, opt-in
- **Instalação:** `transformers` 5.4 e `torch` 2.14 já estavam no `python3.14`; `depth-anything/Depth-Anything-V2-Small-hf` baixou do HF (pipeline `depth-estimation`, MPS), 8 s para carregar, ~3 s por painel. Sem dependência nova no repo. Pesos ficam em `~/.cache/huggingface` (fora do repo).
- **O que mudou** (`tools/blender/depth_map.py`): `disparity(sheet)` roda o modelo no crop (o mesmo do `split_sheet`) do front e do left e devolve o mapa de disparidade relativa (0..1, maior = mais perto) no layout do canvas do fit; `part_disparity` = mediana dentro da máscara de cada peça; `calibrate` ajusta z = a x disparidade + b nas peças que têm também máscara left (z da `box3d`); `depth_init` (chamado por `fit(depth=True)`, `--depth`) (1) move em z, no máximo 0,1 H, as peças **sem** máscara left (alinhadas no eixo, o left não resolve) só se |r| >= 0,3; (2) se o `parts.json` não traz `depth_order`, os pares vêm da disparidade (degrau 0,12 contra o tronco). `python3.14 tools/blender/depth_map.py <sheet> <out>` grava `depth-front.png` / `depth-left.png`.
- **Correlação do z do Depth Anything com o z do left** (a mediana por parte só existe para o n005, o único com parts.json): n005 por parte, front DA x z da `box3d` (left): Pearson 0,37, Spearman 0,38 (n = 13); contra `depth_order`: Spearman 0,60. Sem `parts.json`, por linha de altura nos 5 sheets (borda da frente da silhueta do left x disparidade do front, `corr_rows.py`; n02X olha para a esquerda, usado o módulo da correlação da borda esquerda): n005 r = 0,54 (média da linha) / 0,78 (p90), n00U 0,44 / 0,50, n01X 0,50 / 0,64, hfoo 0,35 / 0,33, n02X 0,74 (borda esquerda). Moderada: o DA acerta a ordem que importa (tanque atrás do tronco: 0,71 contra 0,82; máscara e lanterna na frente: 0,93 e 0,94) e erra o que um humano nem vê (pés "longe" por estarem embaixo: 0,50).
- **Prova (clay real, mesmo spec, `--fit-parts` com e sem `--depth`):** n005 r = 0,26 (< 0,3): nenhuma peça movida, resultado igual ao sem `--depth` (.772 left, uncovered .174 contra .173). hfoo r = 0,60: 7 peças movidas (-0,28 a +0,09 m em z), IoU .700/.639/.682/.668/.761/.690, uncovered left .183 contra .189 sem `--depth` e .174 do fit padrão (nenhum ganho consistente). Fração de parte dentro da máscara: hfoo .460 -> .496, n005 .597 -> .599.
- **Veredito:** o mapa dá uma ordem plausível, mas o z métrico que o fit usa tem de vir da calibração com o left, e ela só vale (|r| >= 0,3) em 1 de 2 sheets; onde vale, o ganho de IoU é zero. Fica opt-in. Se voltar: calibrar com a `box3d` real do L5-1 (juntas triangulatas) em vez da caixa a olho.
- Paper: Depth Anything V2 (NeurIPS 2024). Não é gerador 3D: só inferência, sem malha, rede pré-treinada de profundidade relativa; decisão do usuário registrada no ROADMAP.
- Arquivos: `tools/blender/parts_fit.py`, `tools/blender/depth_map.py`, `tools/blender/fit_spec.py` (`PART_W`, `DEPTH_W`, `PART_POOR`, `Proxy.hull_list/part_shares/polygons`, `attach_parts`, `misplaced`, `spec_centre`, `fit(partfit, parts_path, depth)`), `tools/blender/spec_pipeline.py` (`--fit-parts`, `--parts`, `--depth`), `tests/tools/blender/test_parts_fit.py`, `test_depth_map.py`, `fixtures/parts-{n005,hfoo}.json`.

### 23.X Corte dos painéis: vãos interiores antes dos dois maiores (2026-10-28) - NÃO APLICADO, misto
- **O que:** `concept_panels` escolhe os 2 maiores vãos de colunas e só depois filtra os interiores; as margens da página
  ganham e 18 de 23 sheets caem no corte em terços iguais (que fatia o cano da arma do n005, achado em 23.L5-4).
  Testei filtrar os interiores antes de escolher os 2 maiores.
- **Medida (clays v8-r1, mesma régua):** n005 front .849→.815, left .721→.775, back .832→.844; n00U left .744→.685;
  n02X front .779→.758, left .715→.740, back .778→.752; n01X e hfoo iguais. Quebra `BlobPanels`.
- **Decisão:** revertido. Troca a régua de todas as comparações com ganho só no left e perda no front e na aranha;
  o cano fatiado fica como limitação conhecida do sheet do n005 (o vão entre painéis é pequeno). Reabrir se a leva 6
  regenerar sheets com vão maior.

### 23.L5-5 Superfície por default (2026-10-27) - 8 lados no que o orçamento segura, cabeça em `lathe`, botas/punhos redondos, face do sheet; tronco octogonal e `limb` com joelho NEGATIVOS (opt-in)

Feedback do n005: máscara plana nas laterais, pés blocados, olhos viram fenda ou somem. Papers: Sano 2026 (perfil de largura do sheet como seção redonda), EdgeRunner (orçamento de faces: 8 lados só onde cabem em 400-700).

- **O que mudou.**
  - **8 lados por default.** `lathe_limb.SIDES` 6 -> 8 (`lathe` 68 -> 92 tris, `limb` 32 -> 44, `chain` idem; 6 continua válido, faixa 6-8); `cyl` ganha `opts.sides` (default 8, era 12 fixo: 44 -> 28 tris; `build_unit`, `preflight.part_tris`, `fit_spec`); `frustum` ganha `opts.sides` (4 = a caixa de sempre; 6-8 = n-gon inscrito na caixa w x d, topo escalado/deslocado como antes, `4 * sides - 4` tris; `build_unit.frustum`, `part_tris`, `fit_spec.frustum_points`). `prism` já era 8. Texto da DSL (`spec_pipeline.DSL`) atualizado (defaults, `sides` do `frustum`/`cyl`, tris do lathe/limb).
  - **Chanfro por default nas caixas.** `build_unit.main`: sem argumento de orçamento, `plan_chamfers` usa 700 (antes: só com o orçamento na linha de comando; o estágio 1 e o 2 sempre passaram o teto, então o efeito real é só em chamada solta). Os pré-specs do massing não têm caixa (só o placeholder de prop): nada a chanfrar.
  - **Massing** (`massing.py`): cabeça = `lathe` (`KIND_FOR["head"]`, perfil de largura do sheet em 6 anéis, squash = largura/profundidade, 8 lados); botas e punhos = `frustum` de 8 lados, topo menor (`FOOT_SIDES`); a peça da cabeça leva `"decal": "sheet"` (§18.J: os olhos são os dois pontos do próprio sheet, não `eyes2`/`face`); torso e pelve continuam pilhas de frustum de 4 fatias, caixas. Flags: `TRUNK_SIDES` (vazio) e `LIMB_KNEE` (False), ver abaixo. O brief do autor passa a pedir `"decal": "sheet"` como default (as genéricas só para sheet sem rosto: roda de válvula, aranha).
- **Prova sem LLM** (massing sozinho e rebuild de `runs/draft/<id>/v8-r1/spec.json`, clay, `--no-fit --no-repair --shape-only`; código em `tools/blender`, saídas em `scratchpad/leva5-surface/{base,g1}/`). IoU front/left/back/top/bottom/rts, tris, spill top/bottom, `edge_chamfer` front/left/back/top/bottom (`review.md`, hard -> wire, /H):

| unidade (massing) | tris | IoU 6 vistas | média | spill top / bottom | edge_chamfer |
|---|---|---|---|---|---|
| n01X antes | 456 | .842 .825 .842 .794 .733 .777 | .802 | .141 / .145 | .012 .011 .012 .017 .016 |
| n01X depois | 512 | .841 .833 .841 .814 .735 .789 | .809 | .088 / **.217** | .011 .007 .011 .011 .014 |
| n005 antes | 500 | .756 .579 .811 .697 .813 .742 | .733 | .186 / .150 | .020 .020 .020 .022 .022 |
| n005 depois | 556 | .765 .563 .809 .699 .817 .760 | .736 | .178 / .134 | .018 .020 .019 .022 .021 |
| n02X antes | 500 | .580 .615 .561 .707 .687 .735 | .647 | .218 / .261 | .026 .017 .028 .024 .029 |
| n02X depois | 556 | .575 .675 .559 .722 .693 .718 | .657 | .194 / .245 | .026 .017 .029 .020 .026 |
| hfoo antes | 500 | .369 .457 .369 .705 .690 .528 | .520 | .243 / .269 | .040 .035 .036 .031 .040 |
| hfoo depois | 556 | .371 .470 .372 .711 .698 .508 | .522 | .234 / .258 | .040 .034 .036 .030 .037 |
| n00U (spider) | 608 | igual | .683 | .281 / .271 | igual: `LEG_SIDES` = 6 fica |

  Tris +56 em todo biped (`part_tris` n005: cabeça 36 -> 92, botas 24 -> 56; braços e pernas com os punhos 312 -> 280: os prismas caem de 10 para 8 lados e os punhos sobem de 12 para 28, porque o laço `MIN_TRIS` do `build` antes subia os prismas a 10 lados para chegar ao piso de 400 e agora as peças redondas chegam lá com 8), dentro de 400-700. Spill de top: média .197 -> .174 (4 bípedes); de bottom: .206 -> .214 (n01X piora, os outros 3 melhoram); IoU médio de 6 vistas sobe .002-.010 em 4/4. `edge_chamfer` cai em 13 de 20 células, fica igual em 6 e sobe em 1 (n02X back .028 -> .029).
- **Orçamento de 8 lados nos specs dos autores** (v8-r1 com todo `prism`/`lathe`/`limb` de `sides` < 8 forçado a 8, `scratchpad/leva5-surface/h1/`): tris n01X 684 -> 684, n005 664 -> **704**, n00U 700 -> **844**, n02X 690 -> 690, hfoo 648 -> 672; IoU igual dentro de ±0.01 (n005 left .720 -> .727, n00U bottom .666 -> .658). O 8 lados sozinho não compra IoU e estoura o teto em 2 de 5 (o aranha com 18 prismas de 6 lados: +144 tris), então o default vale para a DSL/pré-spec do biped e **não** para as pernas do spider (`LEG_SIDES` = 6, o fallback do roadmap). Os v8-r1 rebuildados sem forçar ficam iguais (684/664/700/674/648 tris, IoU igual a ±.001; só o n02X perde 16 tris: o `cyl` de 12 -> 8 lados).
- **Rosto.** `head_face` já cortava a cabeça do front em 64x64 com os olhos como dois discos vermelhos (`scratchpad/leva5-surface/face-n005-x6.png`); o que os escondia era a parte que levava o decal: no v8-r1 do n005 o decal cai num frustum de cabeça enterrado no capuz (olhos ~6 px, `face-zoom-n005.png` esquerda e meio); no pré-spec novo a cabeça é um `lathe` de capuz e o decal ocupa a frente toda: dois pontos vermelhos grandes mais a máscara (direita). Sem ajuste de recorte nem escala. O n01X (cabeça roda de válvula) também recebe o decal do sheet: sai uma roda de válvula pequena na testa, inofensiva; sem rosto a mostrar o autor troca.
- **Negativos, desligados.**
  - `TRUNK_SIDES = {"torso": 8, "pelvis": 8}` (fatias octogonais): spill de top cai muito (n01X .141 -> .069, n005 .186 -> .116) mas o bottom piora: n005 bottom IoU .813 -> .779 / .767 (só torso) e n01X bottom spill .145 -> .221, acima do teto 0,20 do `coupling_ok` (estágio 1 do pré-spec PASS -> FAIL). Fica `{}` (caixas).
  - `LIMB_KNEE = True` (`limb` com joelho/cotovelo medido de `joint_measures`: n01X 2 coxas, n005 2 braços; emissor `_limb_bent` testado): média -.003 (n01X) e -.008 (n005), front/back caem. Fica opt-in, à espera das juntas de L5-1 (`parts.json`).
- **Piorou / pendente.** (1) n01X massing sozinho: PASS -> FAIL no estágio 1, por spill de bottom .217 > .20. É a câmera: a varredura de tilt escolhe só por IoU e cai em 20 graus (.145 com tilt 10; IoU .733 contra .735, empate); mesma geometria, outra câmera. Quebrar o empate do tilt por spill é de `silhouette.py` (não toquei). (2) Juiz pareado contra o run anterior: não rodei (sem LLM nesta prova); o compare textured/clay lado a lado está em `scratchpad/leva5-surface/cmp-{n01X,n005,n02X,hfoo}-mass.png` e `cmp-n005-v8.png` (sheet | antes clay | antes tex | depois clay | depois tex, front/left/top/bottom). (3) A cabeça do n02X (careca, topo largo) sai afunilada em ponta: o perfil lido inclui o pescoço; é ajuste de `cut_hull.lathe_profile`, não de superfície. (4) Os pés só ganham o 8 lados de `bottom`/`top`; o `shift` do topo (bico) não está no octógono, a ponta da bota é a mesma das duas versões.
- **Testes.** `test_lathe_limb` (tris dos defaults 8 lados e do `sides` 6), `test_preflight.RoundKinds` (tris do `cyl`/`frustum`/`prism`, a caixa do frustum redondo não muda), `test_fit_spec.Proxy.test_outlines` (frustum 8 e cyl 12 lados), `test_massing.Surface` (emissor de `limb` com joelho projetado no eixo e `sides` limitado a 8, defaults do pré-spec do n005: cabeça `lathe` + `decal sheet`, botas de 8 lados, sem `limb`, 400-700 tris).

### 23.Y Corte dos painéis por blob para toda unidade (2026-10-28)
- **O que:** `concept_panels` (layout `unit`) monta cada painel pelos componentes conexos: as 3 maiores manchas da
  fileira de cima e as 2 de baixo são as figuras (ordem por x), e cada mancha menor vai com a figura de centro mais
  próximo. Sem linha de corte, um prop ligado à mão (cano da arma do n005, clava do n02X, ponta da lança do hfoo)
  fica inteiro no painel certo. Fallback para o corte em colunas quando o blob acha menos figuras que painéis
  (sheet-hard com figuras coladas); `columns=True` força o corte antigo (testes, diffs).
- **Medida (clays v9-r1, régua nova × guardada; o vazamento era da régua):** n005 left .803→.861 (vermelho 11→4 %),
  front .795→.808; n02X left .732→.786, front .777→.719 e back .755→.730 (a clava deixa de ser contada no left e
  o modelo foi ajustado contra a clava vazada); hfoo left .637→.508 (vermelho 22→33 %: a lança diagonal inteira
  entra no left) e back .666→.769; n00U left .738→.704 (um pedaço de perna do front saía no left); n01X igual.
- **Leitura:** a régua anterior premiava modelo que enchia o vazamento. Toda comparação com runs anteriores a
  2026-10-28 na vista left/back dos três bípedes com prop usa régua diferente; os números do v9 na tabela de §23
  são os da régua antiga. A bateria seguinte mede tudo na nova.

## 24. Leva 6 (2026-10-28)

Doze frentes: os papers de forma (Sano, Chen, Sketch2Mesh, Wiersma) aplicados como MÉTODO depois da auditoria
`analysis/2026-10-28-auditoria-papers-vs-codigo.md`. Bateria `v10-r1` em 8 unidades, pareada contra v9 nos 4
eixos; imagens em `history/2026-10-28-v10/`.

| unidade | v9 f/l/b | v10 f/l/b | vermelho f/l/b | veredito | juiz v10 × v9 |
|---|---|---|---|---|---|
| n01X | .793/.804/.794 | .773/.841/.776 | 12/11/12 % | PASS | misto; form v10 4-0 |
| n005 | .795/.803/.814 | **.909/.926/.909** | **3/4/3 %** | PASS | v10 4-0 nos 4 eixos |
| n00U | .805/.738/.811 | .833/.739/.832 | 9/10/9 % | CHECK (rts .617) | v10 3-1 artist/wc3 |
| n02X | .777/.732/.755 | .863/.813/.889 | 5/9/4 % | PASS | v10 4-0 artist/wc3 |
| hfoo | .766/.637/.666 | .858/.450/.858 | 7/38/6 % | CHECK (left: lança diagonal) | v10 4-0 nos 4 |
| n017 | .829/.721/.776 | .872/.719/.807 | 1/19/3 % | CHECK (rts .692) | v9 4-0 artist/wc3 |
| n00H | .813/.633/.807 | .882/.681/.877 | 7/24/7 % | CHECK (rts .232) | v10 4-0 nos 4 |
| n010 | .685/.877/.589 | .874/.876/.613 | 2/4/24 % | CHECK (sheet girado) | v10 4-0 em 3 |

PASS 3/8 (v9: 0/8 com os mesmos gates); IoU médio front/back .760 → .851; vermelho médio front/back 10.6 → 6.3 %;
o juiz prefere o v10 em 22 de 28 eixos decididos. Falta: rts (aranha, lobo, wyrm), placas soltas que seguram
`components_body`, slivers da união (19-37 %), e sheets que divergem por construção (lança do hfoo, drake girado).

### 24.L6-6 Gates de FORMA: `normal_diff`, `fairness`, `components_body`, slivers (2026-10-27)
- **O que mudou:** `mesh_lint.lint` ganha `normal_diff` (Chen 2023: ângulo entre as normais das duas faces de cada aresta;
  média, p90 e histograma em 6 faixas 0-5/5-15/15-30/30-60/60-100/100+), `fairness` (Wiersma 2026: desvio médio dos
  ângulos internos de 60°) e `components_body` (componentes sem os props: material `prop_*`, senão as peças `props` do
  `attach.json` ao lado do GLB; nunca < 1). `GATES` ganha `components_body == 1` e `sliver_pct < 5`: entram em
  `lint_bad`, logo `status_of` não deixa o run chegar a final-use sem eles. `review.md` ganha `### Forma` no Readiness.
  `spec_pipeline.form_cost` = slivers (fração) + normal_diff médio/90; `FORM_W = 0.5` entra em `margin_of`
  (best_of_n) e na soma de margens de `fit_accepted` (`trial` devolve `form`). `compare_runs` mostra por default
  `clay+wire+overlay+textured` e uma linha FORM com os 4 números por run. `review_pair`: 4º eixo `form` (superfície
  contínua, sem degraus nem caixas atravessadas); `lost` = perde a maioria dos eixos (2 de 3; 3 de 4, 2-2 não é perda).
- **Calibração (139 GLBs guardados, clay + model; tabela em scratchpad `leva6-formgates/calib.md`):** `normal_diff`
  média 36-58° (todo modelo é pilha de caixas: ~40 % das arestas em 0-5°, ~40 % em 60-100°); p90 satura em 90-99°
  (não discrimina; ficam média e histograma). fairness 26-36°. Gates: `components_body == 1` falha em 139/139
  (corpo é caixa solta até o L6-4 unir), `sliver < 5 %` falha em 130/139. Ou seja, TODO run cai de final-use para
  prototype-safe até o L6-4 integrar: esperado, é o ponto do gate.
- **Separação onde o IoU empata (n005):** v6-r4 (PASS, feio) IoU médio .806, nd 45.1°, 60+°: 38.4 % das arestas,
  28 componentes de corpo, fairness 29.3, slivers 13.2 %, custo de forma .633. v9-r1 (juiz prefere) IoU .787, nd 38.5°,
  60+°: 30.5 %, 20 componentes, fairness 27.8, slivers 15.9 %, custo .586. O IoU favorece o v6-r4; normal_diff,
  componentes e fairness favorecem o v9-r1 (certo, segundo o juiz). Slivers vão no sentido errado (+2.7 pt), por isso
  o termo soma slivers e normal_diff: líquido a favor do v9-r1 (-.047, -.023 na margem com `FORM_W` .5).
- **O que piorou / limites:** o termo de forma é pequeno (~.02 na margem): desempata, não decide sozinho.
  `components_body` com clay conta props pelo `attach.json` (cada prop = 1 componente após a união); build sem união
  que funda um prop ao corpo subconta. Sem prova de LLM no eixo `form` (sem `--model`).


### 20.L6-10 Ablação por orçamento de triângulos: `spec_pipeline --budgets` (2026-10-27) - relatório, `BUDGETS` NÃO mudou

- **O que é.** `--budgets 400,700,1000 --spec <spec.json>` (sem autor, sem repair, sem estágio 2): o mesmo spec construído em cada
  orçamento B, em `<run>/budgets/<B>/` (formato de run: `spec.json`, `clay.glb`, `sil/approved/`, `views/<id>/clay-*.png`,
  `budget.json`). Por B: `lift_sides` sobe `sides` de 2 em 2 (até 16) nas maiores peças redondas (prism, cyl, ring, lathe, limb,
  chain; caixa e frustum de 4 lados ficam) enquanto a estimativa do preflight cabe em B; `build_unit` em clay com B como orçamento
  de chanfro; se a malha passou de B, `decimate_glb.py` (collapse) leva a B. Mede: tris reais, IoU nas 6 vistas, `uncovered`
  médio, slivers (`mesh_lint`), tempo. `<run>/review.md` ganha `## Budgets` (tabela + "IoU perdido por 100 tris" de cada trecho +
  joelho) e `budgets.json`. `compare_runs.py <out.png> <run> --show budgets`: uma coluna clay por orçamento, cabeçalho com B/tris/slivers.
- **Joelho (`knee_of`).** O menor B cujo passo para o próximo compra < `KNEE_SLOPE` = 0,003 de IoU por 100 tris (Wiersma Fig. 10:
  a curva achata; Chen: parar quando o erro de tela não cai mais). Sem LLM: ~30 s por unidade em 3 orçamentos.
- **Prova, 8 specs v9-r1 em 150/250/400/700/1000** (IoU médio das 6 vistas / slivers %; tris reais = B, +-4):

| unit (rig) | 150 | 250 | 400 | 700 | 1000 | joelho |
|---|---|---|---|---|---|---|
| n01X (biped) | .692 / 0 | .774 / 0.4 | .782 / 3.3 | .790 / 8.6 | .787 / 15.6 | 400 |
| n005 (biped) | .727 / 0 | .776 / 1.6 | .798 / 8.5 | .804 / 16.4 | .804 / 21.4 | 400 |
| n02X (biped) | .721 / 4.0 | .720 / 4.0 | .727 / 5.5 | .726 / 13.7 | .726 / 16.9 | 150 (curva plana: ruído) |
| hfoo (biped) | .676 / 0 | .695 / 2.0 | .711 / 11.2 | .713 / 11.7 | .715 / 33.7 | 400 |
| n00U (spider) | .640 / 0 | .703 / 0 | .704 / 18.0 | .712 / 18.7 | .709 / 22.0 | 250 |
| n017 (quadruped) | .701 / 8.7 | .774 / 6.0 | .778 / 9.0 | .782 / 26.4 | .782 / 38.9 | 250 |
| n00H (wyrm) | .629 / 8.7 | .635 / 7.2 | .660 / 6.5 | .679 / 5.7 | .684 / 15.0 | 700 |
| n010 (drake) | .526 / 0.7 | .553 / 4.8 | .586 / 13.8 | .604 / 9.6 | .605 / 15.4 | 700 |

- **IoU perdido por 100 tris, por trecho (700→1000 / 400→700 / 250→400 / 150→250)**: bípedes ~0 (-0,001..0,0007) / 0,0005..0,0027 /
  0,005..0,011 / ~0 a 0,08; n00H 0,0016 / 0,0066 / 0,0167 / 0,005; n010 0,0001 / 0,0061 / 0,0221 / 0,0277. Acima de 400 tris o bípede
  não compra nada; abaixo de 250 perde 0,03-0,08 de IoU.
- **Recomendação por classe (`BUDGETS[kind][1]` hoje 700 para `mass`)**: biped 400; spider 250-400; quadruped 250-400; wyrm 700;
  drake 700. A mediana dos 8 é 400, mas wyrm/drake (silhuetas finas, muitos pedaços) ainda ganham até 700: um teto único de 400 os
  prejudicaria. `BUDGETS` **não foi alterado**: só silhueta foi medida, não textura/rampa/animação, e o `lo`=400 do gate de tris
  fica; mudar o teto por rig é decisão da bateria v10 (L6-8) com o pareado.
- **O que piorou / limites.** Slivers sobem com o orçamento (n005 8,5 % → 21 %, hfoo 11 → 34 %): mais lados por `lift_sides` fazem
  triângulos finos; a faixa 400 é também a de menos slivers por IoU. A estimativa do preflight subestima a malha real em ~10 %
  (build a B=400 saiu com 652 tris), então quase todo B é fechado pelo decimate, não só por `sides`: a curva mede "spec + lados +
  collapse", não uma reescrita do spec com menos peças. Decimate é por razão, sem tolerância em espaço de tela (a `toldec` só existe
  no caminho `union` de `build_unit`, ainda não usado no clay); quando L6-4 ligar a união, trocar o collapse por `toldec`.
  Silhueta insensível acima de 400 não prova que o olho não veja facetas: o juiz pareado decide.
- Provas: `/private/tmp/claude-501/-Users-afa-Developer-arthur-castle-fight/9830c746-7a9c-4c31-80db-2e0ef88f25b7/scratchpad/leva6-budgets/<id>/` (400-1000), `low-<id>/` (150-400), `n005/cmp.png`.

### 24.L6-9 Sano: simetria e coerência entre painéis do sheet (2026-10-27)

**O que mudou.** `silhouette.py`: `r_sym(mask)` (IoU do recorte com o espelho horizontal, Sano §3.3) e
`sheet_report(sheet)`: hull 64³ de front x left (`hull_voxels`, a mesma ideia do `preflight.hull_masks`, mas
voxelizada aqui), projetado em back (espelhado), top e bottom e comparado com o painel desenhado. Top/bottom: IoU
após esticar os dois ao mesmo quadrado (extensões iguais por construção, a vista é desenhada inclinada e em escala
própria) e melhor dos 4 flips (cabeça para cima ou para baixo, left virado para qualquer lado). `COHERENCE_MIN = 0.6`:
abaixo disso o painel não é uma vista da figura de front x left e `silhouette.py` não o conta no veredito
(`PASS/FAIL (sheet incoherent: report)`, `incoherent: true` no `silhouette.json` da vista, `sheet.json` ao lado). Vai
para o `silhouette.json` do run (`sheet`), uma linha no review (`sheet (report...)`) e para o brief
(`sheet_text`: figura assimétrica no front, painel que não deve ser usado). `massing.clean_side`: com `r_sym` do front
< `SYM_MIN = 0.85`, o front é espelhado de modo que o lado +x (de onde braços e pernas são lidos e depois espelhados)
seja o mais leve, dividido no centro dos pés: o lado do prop não vira braço nos dois lados. `silhouette.py <sheet> x x --measure` imprime a tabela (chave `sheet`).

**Medida (12 sheets de `refs/`, `silhouette.py <sheet> x x --measure`).**

| sheet | front r_sym | back | top | bottom | incoerente |
|---|---|---|---|---|---|
| h05X | .93 | .60 | .68 | .87 | back (.5975, no limite) |
| h09B | .96 | .79 | .68 | .89 | - |
| hfoo | **.66** | .83 | .78 | .75 | - |
| n005 | **.76** | .88 | .65 | .72 | - |
| n00H | .94 | .89 | .39 | .38 | top, bottom |
| n00U | .97 | .91 | .53 | .49 | top, bottom (spider: pernas radiais; o hull cheio de front x left é gordo) |
| n010 | .84 | .57 | .60 | .62 | back, top (.5989; bottom .62 passa por pouco) |
| n017 | .94 | .80 | .67 | .69 | - |
| n01I | .90 | .79 | .61 | .45 | bottom |
| n01N | .96 | .80 | .29 | .30 | top, bottom |
| n01X | .98 | .89 | .74 | .71 | - |
| n02X | **.72** | .91 | .73 | .63 | - |

hfoo, n005, n02X saem assimétricos no front (clava/escudo/vaporizador de um lado). n00H e n010 saem incoerentes como
esperado (n010: back e top; o bottom .62 fica a .02 do corte, o back tem r_sym .30 contra o front: outra pose).
n00U: top/bottom baixos (.53/.49) por ser aranha: registrado, o corte os trata como incoerentes.

**Veredito (n00U, spec `v4-oneshot-r1` reconstruído sem LLM).** top .562 e bottom .537 (gate .65) saem
`FAIL (sheet incoherent: report)` e não contam: 2/6 gates passam em vez de 0/6; front, left, back e rts
seguem FAIL. A linha do review: `sheet (report...) | front r_sym 0.97, back-vs-hull 0.91, top-vs-hull 0.53 (incoherent), bottom-vs-hull 0.49 (incoherent)`.

**Negativo / limites.** (1) Uma primeira versão comparava os painéis em escala de altura (aspect preservado): 8 de
12 sheets saíam incoerentes em top/bottom, porque o top é inclinado e em perspectiva; o esticado separa n01X/n017
(.67-.74) de n00H/n01N (.29-.39), mas n010 e h05X ficam a ~0.02 do limiar (0.60 é do brief, não calibrado). (2) A
contenção (painel dentro do hull) não discrimina nada: o hull é gordo e contém tudo (.93-1.0 em todas). (3) Efeito do
`clean_side` nos massings sem LLM (`--no-massing --spec`, clay, sem repair): hfoo front .434 -> .437, left .473 -> .430,
rts .512 -> .553, `fist_span` 1.29 -> 1.20 (alvo 0.55); n005 front .877 -> .877, left .736 -> .728, top .749 -> .747: neutro
(o massing de hfoo é ruim com e sem a mudança; o ganho é só a mão sair do prop). n02X e n01X: sem mudança (0 de 13/12 peças
diferentes; n02X é assimétrico mas o front não foi espelhado: o desequilíbrio de massa é pequeno, 24550 x 24182 px, a assimetria é de pose). (4) Só o veredito de `silhouette.py` ignora a vista incoerente;
`margin_of`/`fit_accepted` ainda usam `GATES` inteiro. (5) O brief fala inglês (o autor lê inglês): o texto do roadmap em
português está em `sheet_text`.

### 24.L6-1 Tronco, pelve e cabeça como UMA superfície contínua: `STACK_LATHE` (2026-10-27) - ligado; casca da aranha NEGATIVA (fica em fatias)

- **O que mudou.** `lathe_limb`: `profile` de um `lathe` pode ser lista de anéis `[w, d, zc, xc(, t)]` (x = r*w, z = r*d, centro deslocado r*(xc, zc), `t` = altura 0-1 de h; sem `t`, uniforme), 3-10 anéis, `corner` 0-1 empurra os vértices diagonais do 8-gon para o canto da caixa (0 = círculo: de cima enche 71 % da caixa; 1 = retângulo). `massing._ring_stack` (emissor `ring`, roteado por `emit` quando `STACK_LATHE and role in RING_ROLES`) emite UM `lathe` por torso/pelve/cabeça com os anéis nos `breakpoints` que a pilha já calculava (4-5 anéis) e w/d/zc lidos do sheet; os anéis das pontas saem `RING_OVERLAP = 5 %` da altura para a parte vizinha sobrepor a 80 % (`overlap`). `lathe_part` (cabeça/máscara do `parts.json`) lê 5 anéis na caixa (largura do front, profundidade e centro z do left). `fit_spec.apply_profile` move w/d dos anéis ±15 % (último valor = papel do squash); `preflight.part_tris`/`bbox`, `build_unit.swept_part`, `cut_hull.lathe_profiles` leem a mesma `lathe_rings` e não mudaram. `touch` deixou de mover o corpo na direção de um prop (bug exposto: o torso único foi puxado 0.13 m para o tanque). Flag `STACK_LATHE = False` volta às fatias.
- **Por quê.** Chen 2023 (superfície contínua, sem cascas que se atravessam) e Sano 2026 (volume de base regular): na pilha de `frustum` cada fatia tem a sua largura e toda junta vira degrau; anéis compartilhados dão uma junta só.
- **Medido** (massing sozinho, `--no-fit --no-repair`, IoU vs sheet front/left/back/top/bottom/rts; antes -> depois; provas em `scratchpad/leva6-surface/{base,fin}`):

| unidade | IoU antes | IoU depois | média | tris | slivers | componentes |
|---|---|---|---|---|---|---|
| n005 | .824 .874 .823 .752 .744 .856 | .826 .899 .824 .756 .777 .843 | .812 -> .821 | 592 -> 628 | 8.1 -> 5.1 % | 20 -> 15 |
| hfoo | .708 .669 .698 .495 .527 .488 | .700 .675 .691 .493 .526 .486 | .597 -> .595 | 564 -> 600 | 10.6 -> 8.0 % | 21 -> 16 |
| n02X | .742 .769 .743 .638 .681 .709 | .759 .797 .760 .640 .679 .716 | .714 -> .725 | 768 -> 772 | 17.2 -> 13.7 % | 24 -> 19 |
| n00U (aranha) | .765 .681 .760 .628 .619 .606 | .765 .681 .760 .629 .619 .607 | .676 -> .677 | 608 -> 656 | 17.4 -> 16.2 % | 40 -> 36 |
| n017 (quadrúpede) | = | = | .759 | 412 | 10.2 % | 21 |

  Todas dentro de ±0.02 por vista (n005 left +.025 e bottom +.033, a favor); n005 passa o estágio 1 como antes. Wire no compare (`compare_runs --show clay+wire+overlay`, `cmp-n005.png`): capuz, torso e pelve são uma malha contínua, sem os degraus da pilha.
- **O que piorou / não entrou.**
  - Octógono puro (`corner 0`) perdeu 0.05 em top/bottom (n005 .752 -> .698, estágio 1 FAIL): de cima ele enche 71 % da caixa que a pilha de 4 lados enchia; por isso `corner` (tronco 1.0, cabeça 0.5).
  - Casca da aranha: o corpo todo (`body`) como UM lathe perdeu 0.044 no left (.681 -> .637; a pilha de fatias carrega a linha de barriga e costas de cada fatia, um lathe é reto), top/bottom +0.02, tris 608 -> 500. Fica em fatias; só `abdomen` e `head` viram anéis (`SHELL_RINGS`), IoU neutro, +48 tris. Média de alturas por fatia em vez de min/max foi pior (.610).
  - n017: o tronco é uma sequência de tijolos em z (`slab`); um lathe em pé não representa isso, nada mudou. Um lathe deitado (eixo z) seria um item à parte.
  - hfoo -0.002 (neutro); stage 1 segue FAIL por top/bottom/rts já antes.
  - Tris sobem 4-8 % (8 lados por anel x 4-5 anéis); n02X já estava acima de 700 antes.

### 24.L6-4 Chen por default: união do corpo + limpeza + decimate com tolerância (2026-10-27)
- **Mudou** (`build_unit.py`, `UNION_BODY = True`, argumento `nounion` volta ao join): as peças sem `prop` (e sem
  `flame`) passam por `union_body`: `union_parts` (BOOLEAN EXACT, depois MANIFOLD, depois join só daquela peça se
  nenhum dos dois passar em `union_holds`: caixa dentro das duas caixas e volume entre max e soma) -> `transform_apply`
  -> pesos de osso e material por face transferidos da peça de origem mais próxima (`transfer_from_parts`; junta =
  média) -> `clean_mesh` (1 mm + planar 6°) -> triangula (BEAUTY) -> `cull.decimate_union(floor=)` com tolerância H/32,
  piso `UNION_FLOOR = 0.9` do orçamento (0.6 deu IoU -0.08 no n01X) e teto = orçamento menos os tris dos props. Sharp
  por ângulo 35° (`soften`). Sem chanfro por caixa (o decimate o desfaria). Props e flame seguem componentes próprios,
  com o skin da âncora. `attach.json` ganha `union` (placas, `joined_instead`, `components_body`, props);
  `mesh_lint` lê `components_body` dele (sem arquivo: total) e `components_body == 1` é gate.
- **Bug achado:** `obj.bound_box` fica velho até o próximo update da cena para peças feitas por bmesh (prism, ring):
  a checagem do boolean usa os vértices. O anel do peito do n01X fazia o EXACT devolver um casco com buraco e
  vértices longe; `union_holds` pega e cai no MANIFOLD.
- **Medido** (8 `v9-r1/spec.json` reconstruídos sem LLM, clay, antes -> depois; `scratchpad/leva6-union/{before,after}`):

| id | comps total -> corpo | tris | IoU front/left/back/top/bottom/rts antes -> depois | slivers % |
|---|---|---|---|---|
| n01X | 33 -> 4 | 684 -> 630 | .794/.802/.796/.795/.775/.777 -> .794/.806/.795/.795/.771/.775 | 8.8 -> 14.4 |
| n005 | 25 -> 6 (corpo 1 + 5 props) | 716 -> 630 | .804/.860/.824/.718/.715/.879 -> .804/.860/.824/.719/.715/.880 | 15.9 -> 11.0 |
| n00U | 34 -> 1 | 664 -> 628 | .811/.699/.807/.662/.656/.624 -> .805/.708/.804/.663/.658/.621 | 14.5 -> 18.5 |
| n02X | 24 -> 3 (corpo 1) | 736 -> 630 | .715/.784/.726/.681/.677/.751 -> .717/.787/.728/.679/.678/.751 | 13.6 -> 19.5 |
| hfoo | 23 -> 5 (corpo 1) | 604 -> 630 | .770/.511/.758/.786/.818/.635 -> .768/.512/.756/.786/.818/.638 | 12.9 -> 14.1 |
| n017 | 24 -> 5 (corpo 2) | 556 -> 629 | .828/.721/.776/.831/.843/.692 -> .821/.723/.768/.830/.843/.690 | 11.2 -> 27.7 |
| n00H | 17 -> 3 | 672 -> 625 | .812/.635/.804/.734/.685/.235 -> .809/.638/.801/.735/.684/.432 | 6.0 -> 10.1 |
| n010 | 31 -> 3 (corpo 2) | 684 -> 627 | .690/.861/.600/.455/.464/.557 -> .689/.849/.598/.457/.461/.564 | 8.9 -> 15.6 |

  IoU dentro de +-0.01 (exceto n00H rts, que antes tinha normal virada, e n010 left -0.012). Os corpos > 1 são placas
  que o spec deixa soltas (`attach.json` `loose`: pés do n01X, `spine.2` do n010): a união não as solda, o gate
  `components_body == 1` as acusa de verdade. Gate nas 8 reconstruções: 4 passam (n005, n02X, hfoo, n00U), 4 falham por
  placa solta; nos runs antigos (join) falha sempre.
- **Piorou:** slivers (ângulo < 10°) SOBEM em 7 de 8 (meta < 5 % não atingida): a triangulação das interseções e o QEM
  fazem triângulos finos. Beautify global entortava as caixas (n01X front 0.794 -> 0.779); beautify só em arestas planas
  e dissolve + re-triangulação depois do decimate não mexeram o número: não ficaram. Fica para L6-6 (`slivers`) e um
  remesh planar. Piso de faces 0.6 do brief foi para 0.9: com 0.6 o n01X perdia 0.08 de IoU (QEM encolhe as caixas).
- **Textura/UV/decal/animação:** `texture cel` rebuild de n01X/n005/hfoo: 1 imagem, `uv_out_of_range` 4 -> 1 (n005) e
  2 -> 1 (hfoo), decals (olhos) intactos; `render_anim walk` n005/n01X antes/depois sem rasgo (`scratchpad/leva6-union/anim/walk.png`).

### 20.L6-2 Hull visual de Sano: 14 vértices, arcos, terceiro prisma, QEM; `cut` por default NEGATIVO em n02X (2026-10-27)

**O que mudou** (`cut_hull.py`, `build_unit.py`, `massing.py`, `fit_spec.py`, `spec_pipeline.py`, `preflight.py`):
- `cut_hull.LIMIT` 8 -> 14; contorno por faixa da peça = Douglas-Peucker + `snap_axes` (já existiam) + **arcos** (`arcs`: em três vértices
  consecutivos, ajuste de círculo Kasa nos pontos densos do contorno entre eles; troca o vértice por 2 pontos do arco quando o resíduo do
  círculo é < 0,5 do resíduo das duas arestas e há vértice sobrando, senão 1). Placas continuam em 8 (`PLATE_LIMIT`).
- Terceiro prisma (top, `top_poly`, eixo y) em `build_unit.cut_part`; `cut_part` decimata (QEM, `DECIMATE COLLAPSE`) ao orçamento `preflight.CUT_TRIS` = 56 por parte.
- `cut: sheet` vale também em `lathe` (build o lathe e os prismas o cortam: pós-build, funciona sobre o lathe de L6-1); `cuttable`/`cut_picks`/`hood_index` em `cut_hull` (a maior peça do torso/pelve/abdômen e o capuz, `CUT_MAX` = 4; props nunca); `fit_spec.toggle_cut` usa `cut_picks`.
- `fit_accepted(cut=True)` não veta mais pelo vermelho (compara IoU + regras).
- `massing.CUT_DEFAULT` marca os `cut_picks` no pre-spec: **False** (ver abaixo). `cut_hull.TOP_PRISM` = False.
- `refs/<id>/parts.json`: a faixa é a caixa da própria peça, que o massing já tira da `box3d`; não leio o json no `cut_hull` (ponytail: add quando uma peça cortada for maior que a caixa da parte).

**Prova** (massing do sheet-hard, `--no-fit --no-repair`, IoU do aprovado; antes -> depois com `CUT_DEFAULT`; tris do GLB; `scratchpad/leva6-hull/out/<id>-nf-m{before,after}/`):

| unidade | front | left | back | top | bottom | rts | tris |
|---|---|---|---|---|---|---|---|
| n005 (capuz lathe, pelve, tronco lathe) | .777->.765 | .856->.858 | .785->.788 | .719->.725 | .729->.774 | .819->.806 | 616->586 |
| n00U (corpo, cabeça) | = | = | = | .336->.337 | .364->.361 | .478->.477 | 608->696 |
| n02X (cabeça, tronco, pelve) | .732->.667 | .775->.717 | .733->.665 | .635->.636 | .681->.682 | .709->.680 | 768->772 |
| hfoo (cabeça, pelve, tronco) | .706->.701 | .666->.678 | .702->.698 | .492->.528 | .524->.561 | .489->.454 | 564->584 |

Sem o terceiro prisma (o default atual): n005 .768/.884/.788/.722/.766/.806, n02X .737/.717/.736/.636/.682/.699, hfoo ~igual ao com. Uncovered top/bottom
(com top): n005 .229/.233 -> .201/.195, hfoo .494/.464 -> .459/.427.
Spec v9-r1 já fitado (n005): left .860 -> .882, bottom .715 -> .757, rts .879 -> .850, mas 716 -> 840 tris (estoura 700 com CUT_TRIS 80).

**O que piorou.** (1) O terceiro prisma abriu um buraco na barriga do n02X (front .667) e custou .03 no left do n005: desligado. (2) n02X left -.058 mesmo
sem top: a faixa do tronco no painel left traz o cacete colado e o contorno encolhido para a caixa estreita o corpo (a limitação do DSL: "a faixa de um membro pega o que está ao lado"). (3) rts cai .01-.035. (4) n00U: nada muda (spider; corpo
de 0,26 m), +88 tris. Pela regra da leva (IoU não pode cair > .02) `massing.CUT_DEFAULT` fica **False**; o `fit_stage` continua testando o `cut` e agora sem veto de vermelho. Ganho real: top/bottom em n005 e hfoo (+.04), contorno do capuz arredondado (arcos) em vez de caixa.
Próximo: separar o cacete/braço da faixa (componente conexa da faixa ao redor do eixo da peça) antes de ligar o default.


### 24.L6-3 Props ancorados com folga, por default: kind por nome, `clear_props`, `prop_clearance` vira gate (2026-10-27) - IoU fora de ±0.02 só no left do hfoo (-0.033) e do n005/v9 (-0.032)

- **O que mudou.**
  - `massing.prop_rows` (substitui `block_part`/`lathe_prop`): a peça de `parts.json` com `prop` vira, pelo nome e pela caixa, (a) `lathe` (`PROP_LATHE`: tanque, garrafa, cilindro, barril; a lanterna é caixa), (b) `plate` (`PLATE_WORDS`: escudo, espada, lâmina, machado, pistola, vaporizador, placa; fina no menor de x/z; perfil = casco convexo de <= 6 pontos do desenho do prop no `sheet-props`, `hull_profile`/`prop_outline`, transposto se o desenho deita e a caixa em pé), (c) pólo `prism` de 2 anéis hexagonais (pique, clava: `is_pole`; `pole_lean` lê o left do sheet: a tinta mais alta no quinto da frente ou de trás da caixa decide se sobe para a frente ou para trás; sem tinta, frente como antes), (d) caixa. Toda linha sai com `opts {"prop": nome, "anchor": ...}` (L5-3), então o build dá material próprio (`prop_<nome>`), skin 100 % no osso da âncora, componente próprio no `union`. **Não usei o kind `chain`**: ele exige ossos `prefix.k..` do rig, que não existem no antebraço; o prisma from/to é o mesmo sweep de 2 anéis.
  - `unmark_worn` / `merge_props`: peça `prop` cujo centro cai dentro de uma caixa do corpo (cinto, óculos) ou com âncora `shoulder.*` (ombreira) é corpo, não prop (sem marca, sem empurrão); props de mesma âncora com caixas que se tocam viram um prop só (disco de latão na clava: o `loose_props` exige o mesmo nome).
  - `preflight.clear_props(parts, H)` (chamado em `massing.parts_prespec` antes do `settle` e no fim, em `massing.build` para o biped e em `fit_spec.apply` depois de `carry_props`): cada prop (partes de mesmo nome andam juntas) fica a `PROP_GAP = 0.02 H` fora das caixas do corpo do seu osso de âncora (`PROP_BODY`: spine/pelvis/head/body/abdomen) e, se ainda tiver > `CLEARANCE_MAX / 2` da caixa dentro de qualquer parte do corpo, sai dessas também. É empurrado, nunca o corpo vai até ele: `push_out` escolhe o (eixo, sinal) de menor custo entre `PUSH_DIRS` (mochila/tanque `back`: só -z; lanterna `belt`: ±x; resto: os 6), `sweep` testa contra todas as caixas (um empurrão não cai em outra). Caixa avulsa sem rot é CORTADA no lado do corpo (a face de trás fica onde o sheet a tem) enquanto sobrar `PROP_CUT = 0.4` do tamanho; senão anda inteira. Mão e ombro não têm corpo na âncora: só o segundo nível (sem folga). `fit_spec` portanto nunca deixa o corpo crescer para dentro do prop (teste: torso +20 % contra o tanque).
  - `preflight`: `CLEARANCE_BLOCKING = True`; `PROP_REACH` 0.05 -> 0.08 m (a folga de 0.02 H = 0.054 m num H de 2.72 não cabia no alcance antigo: o prop ficaria `loose`); `build_unit.PROP_GAP` (attach, malha a que distância do corpo da âncora conta como solta) 0.03 -> 0.1 pelo mesmo motivo. `placeholder_props` agora marca `prop`/`anchor` (`PLACEHOLDER_ANCHOR`) e passa por `clear_props` (a lanterna nasce no meio do osso, dentro do tronco).
  - `massing.touch` ignora prop ao escolher o vizinho e ao decidir que osso flutua (um prop solto movia as peças do tronco), e roda 2x (uma peça que anda até o pai pode deixar o filho para trás: a cabeça do hfoo sobre o tronco abaixado). Sem isso o hfoo caía no fallback "head falls back to the band massing" assim que a mochila passou a ser prop marcado (a mochila sem marca era a "irmã" que mantinha a cabeça presa).
- **Gate: calibração.** `prop_clearance` só olha peça marcada; nos 120 `runs/draft/*/*/spec.json` só 5 têm marca (os `v9-r1`) e 0/5 reprovam (0 %, < 1/3) antes e depois de `clear_props`; massing sozinho (3 unidades): lanterna/tanque/mochila/pique/clava/pano de fogo 0-8 % dentro do corpo (limite 20 %). A taxa de 83 % de §23.L5-3 era das peças reivindicadas em memória, sem push. Gate ligado.
- **Prova sem LLM** (`scratchpad/leva6-props/`; `spec_pipeline --spec ... --no-fit --no-massing --shape-only`, clay, 6 vistas, juiz = sheet; antes = massing do commit-base, depois = este; front/left/back/top/bottom/rts).

| unidade | antes | depois | pior delta |
|---|---|---|---|
| n005 massing | .777 .856 .785 .719 .729 .819 | .781 .838 .789 .714 .721 .826 | left -0.018 |
| hfoo massing | .706 .666 .702 .492 .524 .490 | .711 .633 .707 .494 .526 .490 | **left -0.033** |
| n02X massing | .732 .775 .732 .636 .681 .709 | .768 .764 .788 .669 .675 .701 | left -0.011 (back +0.056) |
| n005 v9-r1 | .804 .859 .824 .718 .715 .879 | .804 .827 .824 .703 .704 .871 | **left -0.032** |
| hfoo v9-r1 | .770 .511 .758 .786 .818 .635 | .766 .497 .753 .787 .816 .635 | left -0.014 |
| n02X v9-r1 | .715 .784 .726 .681 .677 .751 | igual (clava já fora do corpo) | 0 |

  `preflight` do massing: regras que reprovavam antes continuam as mesmas (n005 `boot_height`/`feet_mass`, vindas das pernas), `prop_clearance` PASS nas 3 (tanque 4 %, lanterna 0 %; mochila 0 %, pique 2 %, lanterna 8 %; clava 0 %). `attach.json` (build real): `loose` igual ao antes (só os pés do n005, antigos); gap malha-corpo: lanterna n005 0.096, tanque 0; mochila 0.054, lanterna 0.055, pique 0 (hfoo); pano 0.064, clava 0 (n02X). Compare lado a lado: `scratchpad/leva6-props/run/{base,new}/<unidade>/compare.png` (o prop aparece como objeto separado: mochila com vão do tronco no left, pique/clava diagonais lidas do left, lanterna do lado do quadril); v9: `run/{v9b,v9n}/`.
- **O que piorou / negativo.** (1) A folga custa IoU onde o sheet cola o prop ao corpo: left -0.033 (hfoo, mochila sai 0.14 m do tronco; a face de trás fica, a da frente recua) e -0.032 (n005 v9, o tanque `lathe` não é cortado, anda inteiro 0.055 m): o critério "IoU ±0.02" falha nessas duas vistas, mantive porque a folga é o pedido; a saída barata é `PROP_GAP = 0` ou cortar o `lathe` (squash). (2) O pique do hfoo aparece no rts diferente do sheet (o left só decide o ângulo no plano left; o rts depende da direção em x, não lida). (3) `chain` não entrou (ver acima). (4) O perfil do `plate` é o casco convexo: não tem vazados; nenhuma das 3 unidades tem arma-placa com `box3d` (o vaporizador do n005 e a pistola não têm caixa em `parts.json`), então o `plate` só foi provado em teste e no n02X (nenhum) - o perfil lido do sheet-props não foi visto num build real. (5) `unmark_worn` deixa cinto/óculos/ombreira como peça de corpo (por design: caixa que envolve o corpo não é objeto separado). (6) A taxa 0/5 do gate vem de poucas amostras marcadas; vigiar nos primeiros runs com marca do autor.
- **Testes.** `test_massing.py::Props` (tipo por nome, plate fina, casco, lean, `clear_props` com válvula junta, worn, merge), `test_fit_spec.py::FitProps` (o ajuste não cresce o corpo para dentro do prop), `test_preflight.py::PropParts` (alcance 0.08). 448 testes OK; ruff com os mesmos 10 achados anteriores.

### 24.L6-5 Sketch2Mesh por default: deformação da malha unida ao contorno (2026-10-27)

**O que mudou.** `tools/blender/deform_to_sheet.py <glb> <sheet> <out.glb> [--views front,left,back] [--iters 4] [--band lo-hi]`
(python3.14 + numpy/scipy/PIL, sem Blender: lê/escreve o GLB direto). Só mexe nos bytes de POSITION e NORMAL (e, em triângulos
quase degenerados, na ordem dos 3 índices); skin, UVs, materiais e clipes ficam como estão.
1. Contorno externo do modelo por vista (Sketch2Mesh Fig. 2c): vértices (soldados por posição, para não rasgar costura de
   normal/UV) cuja projeção cai a <= 1.5 px da borda externa da máscara rasterizada (PIL, mesma normalização por bbox do
   `silhouette.normalize`, espelho escolhido pelo IoU como em `variants`).
2. Alvo = ponto mais próximo do contorno do painel do sheet (`concept_panels`); deslocamento no plano da vista, <= 0.05 H por
   passo; vértice a mais de 0.10 H do contorno do sheet não é puxado (é outra parte: a lança do hfoo no left).
3. O interior segue por Laplaciano uniforme: minimiza |L d|² + Σ a|d − alvo|² + Σ b|d|² (`scipy.sparse.linalg.spsolve`), a = 10 só nos
   vértices de contorno, b = âncora onde o peso é 0. Rodadas (`--iters`, 4) de 1 passo por vista, alternando front/left/back.
4. Eq. 6: o peso de cada faixa de altura (8, de `silhouette.coupling`) = clip((vermelho+verde da faixa − 0.003) / 0.012, 0, 1),
   interpolado na altura do vértice; `--band 0.4-0.7` força 1 dentro da faixa e 0 fora. Solas (2 % H) não mudam de altura (pivô).
5. Um passo vale se: nenhuma face real (> 2 % da área mediana) vira a normal (vértices das faces viradas voltam pela metade até
   nenhuma virar; o sentido de uma face de área zero vem das normais dos cantos), slivers (ângulo < 10°) <= max(5 %, antes + 5 pp),
   nenhuma vista (inclusive top/bottom, só vigiadas: tilt/giro/espelho de melhor IoU) cai > 0.01 de IoU abaixo do começo, e o IoU
   médio das vistas puxadas não cai. Recusado: tenta com 1/2 e 1/4 do passo. Normais recalculadas (soma das faces novas por índice
   de vértice: face chata continua chata); faces quase degeneradas viradas contra as normais trocam o enrolamento (gate
   `flipped == 0` do `mesh_lint`).
6. Gancho: `spec_pipeline.DEFORM = True` (`--no-deform`), `deform_to_sheet.apply` em `stage_shape` logo depois do build do clay
   (depois do fit, antes da textura; guarda `clay-raw.glb` e `clay.deform.json`) e em `colour_stage.build_textured` (a textura
   cel/painted reconstrói o corpo do spec; `sheet` projeta do clay já deformado). **Só roda com `UNION_BODY = True`** (constante em
   `spec_pipeline`, hoje `False`: o L6-4 liga); a malha de 25 cascas não tem um corpo para deformar. `fit_accepted` não muda.

**Prova sem LLM** (8 specs v9-r1 reconstruídos com `build_unit ... clay cull union`, 650-700 tris; juiz = `refs/<id>/sheet.jpg`;
silhouette.py com render real, antes = union, depois = union deformada; tabela completa e overlays em
`history/2026-10-28-l6-5/`):

| unidade | IoU f/l/b antes | depois | vermelho médio f/l/b | verde médio f/l/b | Δ IoU top/bottom/rts | slivers % | flipped |
|---|---|---|---|---|---|---|---|
| n005 | .807/.854/.824 | .861/.876/.872 | 8.6 → 5.7 % | 10.2 → 8.2 % | +.054/+.069/−.003 | 28.4 → 29.4 | 0 → 0 |
| n00H | .813/.633/.807 | .807/.657/.802 | 14.1 → 12.8 % | 14.3 → 14.8 % | 0/+.009/– | 26.6 → 27.5 | 0 → 1 |
| n00U | .811/.705/.812 | .843/.744/.847 | 8.7 → 6.2 % | 16.2 → 14.2 % | +.026/+.001/+.007 | 21.5 → 23.7 | 0 → 0 |
| n010 | .687/.740/.599 | .778/.748/.615 | 18.4 → 15.4 % | 20.5 → 18.3 % | −.013/−.013/−.007 | 23.0 → 23.7 | 0 → 0 |
| n017 | .823/.728/.768 | .876/.754/.814 | 8.4 → 8.3 % | 16.5 → 12.1 % | −.011/+.001/+.001 | 37.0 → 39.8 | 0 → 0 |
| n01X | .721/.769/.723 | .789/.834/.791 | 20.2 → 14.1 % | 9.4 → 7.3 % | +.022/+.011/+.008 | 18.9 → 23.8 | 2 → 3 |
| n02X | .720/.785/.731 | .852/.855/.870 | 11.5 → 7.2 % | 17.6 → 7.9 % | +.031/+.016/+.010 | 23.3 → 24.1 | 0 → 0 |
| hfoo | .767/.504/.770 | .770/.512/.779 | 18.7 → 19.6 % | 20.7 → 18.9 % | +.002/−.002/−.015 | 27.0 → 27.7 | 0 → 0 |

- IoU f/l/b sobe em 7 dos 8 (média das 3 vistas .746 → .789; n02X +.114, n01X +.067, n010 +.039); hfoo e n00H ficam parados.
  Nenhuma das 6 vistas cai mais que .015 (guarda 0.01 + folga do proxy raster). O vermelho médio das 3 vistas cai de 13.6 % para
  11.2 % e o verde de 15.7 % para 12.7 %. Passes de 4 rodadas: 2 a 10 passos aceitos, 2 a 10 recusados por unidade.
- **Meta não atingida:** vermelho E verde < 8 % em front/left/back em **0 das 8** unidades (2 de 24 vistas: n005 left, n02X back).
  Os dois lados batem em limites do que a deformação alcança: (a) o sheet tem peça que a malha não tem (lança diagonal do hfoo,
  lanterna do n01X, cauda do n00H left: o contorno do modelo não chega e o alvo mais próximo é de outra parte; por isso o alcance
  de 0.10 H), (b) a malha unida decimada tem 19-37 % de slivers e ~250 faces: poucos vértices no contorno para seguir o desenho,
  (c) front e back puxam o mesmo eixo x e o modelo é simétrico onde o sheet não é (n02X back 7.5 %). Passo seguinte = L6-7
  (vértices com otimização, só o que passou de 8 %): todas as unidades menos n005 entram.
- **Piorou / custos:** slivers sobem 0.7-4.9 pp (o teto relativo é antes + 5 pp: a união de hoje já passa de 19 %, um teto absoluto
  de 5 % recusaria todo passo; o teto absoluto é do L6-4); `flipped` do mesh_lint 0 → 1 (n00H) e 2 → 3 (n01X), faces
  quase degeneradas; n010 top/bottom −.013 e hfoo rts −.015 (as vistas só vigiadas); 6 vistas puxadas (`--views
  front,left,back,top,bottom`) dão +.04-.10 em top/bottom do n005/n01X/n00U mas perdem até .013 no left do n017: opt-in, não default.
- Animação (`walk`, 12 quadros, malha deformada vs unida, `walk_check.py` na scratchpad): nenhum vértice soldado se separa
  (`max_dup_split` 0.0 nas 8), esticão p99.5 das arestas igual ±5 % exceto n017 (4.4 → 6.0; pele rígida por osso, o esticão já é
  3-8× na união) — sem rasgo.
- Tempo: ~1 s por GLB de 700 tris (5 s com top/bottom), sem Blender. Reproduzir: `build_unit.py <spec> out.glb 700 nofuse 700 clay <cut_hull args> cull union`
  e `deform_to_sheet.py out.glb refs/<id>/sheet.jpg deformed.glb`.
- Fora: top/bottom puxados por default (só opt-in), `cotangent` (Laplaciano uniforme; trocar se a malha ganhar anéis regulares no L6-1),
  Chamfer 3D, qualquer termo de aresta interna (L6-12 entra depois deste passo).
- Papers: Sketch2Mesh 2021 (§3.3 Chamfer de contornos externos, Fig. 2c, Eq. 6), Wiersma 2026 (slivers, recusa de inversão).

### 24.L6-12 Chen/Sketch2Mesh: alinhamento de features ao desenho (2026-10-27) - NEGATIVO, opt-in `--align`

**O que mudou.** `tools/blender/align_features.py <glb> <sheet.jpg> <sheet-hard.jpg> <out.glb>` (python3.14, sem Blender; mesma
leitura/escrita de GLB do `deform_to_sheet`, que ganhou `transform(glb, out, fn)` extraído de `run`, sem mudar comportamento).
1. Arestas vivas: arestas da malha soldada com 2 faces e ângulo diedro > 35° (faces de área quase zero não contam).
2. Por vista (front/left/back, câmeras e espelho de `deform_to_sheet.make_views` sobre o `sheet.jpg`): vértices de arestas vivas cujas
   DUAS faces olham a câmera (normal · direção da câmera > 0.2; sem teste de oclusão) são projetados no canvas e puxados no
   plano da vista para o pixel mais próximo de `silhouette.edges(sheet-hard.jpg)` (mesmo canvas de `fit_spec.edge_term`),
   só se estiver a < 0.06 H, no máximo 0.02 H por passo. Peso do puxão 3 contra "ficar" 1 nos demais; interior pelo mesmo
   Laplaciano uniforme (`deform_to_sheet.solve`). Solas (2 % H) não mudam de altura.
3. Passo recusado (tenta 1, 1/2, 1/4) se: vira face, slivers sobem > 2 pp, `flipped` (contagem do gate do mesh_lint, na malha
   soldada) sobe, qualquer das 5 vistas (f/l/b/top/bottom) cai > 0.005 de IoU contra o `sheet.jpg`, ou a distância média dos
   vértices de aresta viva às arestas desenhadas (cortada em 0.06 H) não cai. 3 rodadas.
4. Gancho: `spec_pipeline.ALIGN_FEATURES` (`--align` / `--no-align`), `align_features.apply` logo depois de `deform_to_sheet.apply`
   em `stage_shape` e em `colour_stage.build_textured`; guarda `clay-prealign.glb` e `clay.align.json`. Só roda com `UNION_BODY`
   e hard sheet. **Default `False`** (resultado abaixo).

**Prova sem LLM** (união + deformação do L6-5 dos v9-r1 como entrada; Blender `render_wire.py` antes/depois,
`silhouette.edge_report(sheet-hard.jpg, wire)`; wires lado a lado em `scratchpad/leva6-features/wire-before-after.png`,
por unidade `<id>/wire-{deformed,aligned}/`):

| unidade | passos/recusas | custo vértice-aresta f/l/b (interno) | edge_chamfer `drawn` f/l/b (hard→wire real) | IoU f/l/b depois-antes | slivers % | flipped |
|---|---|---|---|---|---|---|
| n01X | 3/6 | .0120→.0100 / .0137→.0101 / .0124→.0121 | .0290→.0313 / .0274→.0235 / .0295→.0330 | +.002/+.006/+.003 | 23.8→24.0 | 3→3 |
| n005 | 2/7 | .0248→.0219 / .0236→.0235 / .0206→.0186 | .0163→.0211 / .0151→.0178 / .0209→.0277 | +.004/−.006/+.004 | 29.4→29.3 | 0→0 |
| n02X | 1/8 | .0208→.0209 / .0218→.0219 / .0233→.0214 | .0300→.0284 / .0472→.0265 / .0433→.0434 | −.005/+.002/−.004 | 24.1→24.1 | 0→0 |
| hfoo | 1/8 | .0177→.0176 / .0173→.0174 / .0217→.0198 | .0167→.0113 / .0163→.0163 / .0211→.0164 | −.000/+.000/−.001 | 27.7→27.3 | 0→0 |

- IoU das 6 vistas: nenhuma se move mais que .006 (top/bottom/rts ≤ .005). `flipped` não sobe, slivers ±0.4 pp.
- **Negativo:** o `edge_chamfer` do wire real melhora em 2 de 4 unidades (n02X, hfoo: f/l/b médio −.0074 e −.0034) e fica igual/PIORA nas outras
  2 (n01X +.0006, n005 +.0048): média das 4 −.0014, dentro do ruído. A métrica é dominada pela triangulação (~700 tris cobrem o
  canvas com linhas a ~.02 H umas das outras; um deslocamento ≤ 0.02 H de poucos vértices é do tamanho do erro) e o wire real tem
  linhas de sliver compridas e escolha de espelho que o passo não enxerga. Uma proxy do wire (faces visíveis pintadas de trás para
  frente, mesmo canvas) tentada como guarda não previu o sinal do wire real (0.007-0.02 contra .016-.047) e foi retirada. Só 1 a 3 de
  9 passos por unidade são aceitos: o resto bate em `flipped`/IoU/custo.
- Não feito: occlusão real na visibilidade (só normal); peso maior (WEIGHT 3) e mais rodadas; arestas que o desenho tem e a malha
  não (nenhuma aresta viva perto: o termo só desloca arestas que já existem; criar faceta é papel do L6-7 / fit).
- Testes: `tests/tools/blender/test_align_features.py` (arestas vivas, visibilidade, puxão com teto e sola, sem desenho nada
  se mexe, `apply` só com as chaves). Ruff: sem achados novos.
- Papers: Chen 2023 §4 (alinhamento de features), Sketch2Mesh 2021 (Chamfer de arestas internas com distance transform).

### 24.L6-11 Le/MeshGPT na malha unida: rampa por altura, faces escondidas, atlas partilhado (2026-10-27) - rampa e `cull` NEGATIVOS (ficam desligados); `--atlas shared` opt-in

Rebuild textured (`--texture cel`) e clay de `runs/draft/{n01X,n005,n02X,hfoo}/v9-r1/spec.json` sobre a malha UNIDA (`UNION_BODY`, 630 tris), sem LLM; juiz pareado `review_pair.py` (session:opus, 4 votos) em cópias. Provas: `scratchpad/leva6-texture/` (`drive.py`, `clay.py`, `anim_shots.py`, `pair/`); imagens em `artifacts/model-sheets/leva6-texture/`.

**(a) `ramp` (v = normal + altura) sobre a malha unida: NEGATIVO, `RAMP_SLOPE` fica 0.** Média das zonas de cor nas 5 vistas (`colour_stage`, tilts do estágio 1) com `ramp` 0 / 0.5 / 1.0:

| id | zonas 0 | 0.5 | 1.0 | luma L1 0 / 0.5 / 1.0 |
|---|---|---|---|---|
| n01X | .212 | .188 (back .41 -> .27) | .208 | .044 / .037 / .049 |
| n005 | .519 | .530 | .540 | .054 / .048 / .048 |
| n02X | .304 | .280 | .276 | .069 / .087 / .125 |
| hfoo | .196 | .204 | .197 | .054 / .067 / .069 |

  Pareado (A = ramp 0, B = rampa; por eixo sheet/artist/wc3/form, só vitórias de 3-1 ou mais): ramp 0.5 B ganha 4 eixos (n01X sheet, n005 form, n02X artist e wc3), A ganha 4 (n01X, n005 e hfoo artist; hfoo wc3), o resto empata; ramp 1.0 B ganha 2 (sheet em n01X e n005), A ganha 7 (n005 artist e form; n02X sheet e artist; hfoo sheet, artist, wc3). Zonas caem em n01X e n02X e o juiz não prefere: regra do brief (preferir E zonas não caírem) não vale. Causa visível (`ramp-n01X.png`, `ramp-n02X.png`): cada triângulo da casca decimada cai num slot de rampa por `relative_height` do centro, então uma face plana grande vira dois triângulos de tons diferentes (manchas diagonais). **Rampa contínua** (v por vértice, só no atlas partilhado, ver (c)): `ramp 0.5` empata em 3 de 4 (viés de posição), n02X a favor (3-1 em 3 eixos), mas as zonas caem em n005 (.562 -> .502), n02X (.306 -> .270), hfoo (.196 -> .187), n01X +.004: também fica desligada (`ramp=` continua opt-in no CLI do build). Edge glow no chanfro: a união não chanfra por caixa (`plan_chamfers` fica vazio), só as faces com 3 componentes de normal > .3 (arestas sharp 35°) pegam o topo da rampa; sem ganho mensurável separado.

**(b) `cull=remove` depois da união: NEGATIVO, fica opt-in (`--cull`).** Tris visíveis / total em 12 vistas, join -> união: n01X 594/684 (87 %) -> 615/630 (98 %); n005 593/716 (83 %) -> 611/630 (97 %); n02X 626/736 (85 %) -> 586/630 (93 %); hfoo 557/604 (92 %) -> 581/630 (92 %). A união já come os escondidos (90/118/110/47 -> 15/19/44/49 tris). Remover o que sobra: IoU das 6 vistas idêntico (delta 0.000 nos 4: `silhouette.py` clay `cull` vs `cull=remove`), zonas idênticas, UV/skin intactos (1 imagem, `uv_out_of_range` 0, engine import ok). Animação (`anim_shots.py`: 7 clipes x 5 quadros x 4 câmeras = 140 imagens por unidade, máscara alfa e cor): walk quase igual (<= 55 px de 65k diferentes), mas **rasga** em outros clipes: n005 death/spell/attack3 (IoU da máscara min .968, fresta visível em `n005-death4.png`), hfoo spell/idle/attack (até 193 px), n02X <= 88 px, n01X <= 4 px. A face "nunca vista" no rest pode ser a de dentro de um membro que gira. Ganho: 15-49 tris (2-7 %) contra rasgo nos clipes: não liga. Mudança: `colour_stage.build_textured` passa `cull=remove` quando `--cull` (antes o GLB final da cor reconstruía sem o cull do estágio 1: clay e textured divergiam). Upgrade: ver as faces também nas poses extremas dos clipes (armature avaliada) antes de remover.

**(c) `--atlas shared`: atlas de rampas de 1 px por coluna por raça (Le), opt-in.** `tools/blender/shared_atlas.py` + `build_unit.texturize_shared` (argumento `shared=<tabela.json>`; `spec_pipeline --atlas shared [--atlas-dir]`, tabela `<dir>/<raça>.json`, padrão `artifacts/model-sheets/atlas/`): uma imagem **64 x 64** por raça, coluna i = um slot da paleta (cor + superfície), rampa vertical dos tons escuro/médio/claro (`surfaces.ramp_column`, mesma interpolação dos `CEL_TONES`); a face mapeia para a coluna do material e a linha do tom (`TONE_V`), v por vértice mais `ramp` x (altura - .5) quando `ramp` > 0. A tabela só cresce (coluna nunca muda: modelo antigo segue válido); passou de 64, a unidade volta ao atlas próprio com aviso. Sem decais (olhos, rosto do sheet) e sem linha de tinta: é o preço.

| id | atlas próprio | partilhado | verts | engine import (`mesh_lint.engine_import`) |
|---|---|---|---|---|
| n01X | 768x512, 9.9 KB | 64x64, 0.7 KB | 1757 -> 1020 | ok meshes=5 anims=7 |
| n005 | 768x768, 86.0 KB | 64x64, 0.8 KB | 1554 -> 932 | ok meshes=6 anims=7 |
| n02X | 768x768, 65.7 KB | 64x64, 0.8 KB | 1696 -> 1024 | ok meshes=7 anims=7 |
| hfoo | 768x768, 88.1 KB | 64x64, 1.1 KB | 1676 -> 932 | ok meshes=7 anims=7 |

  n005 e hfoo (Human) saem com a MESMA imagem (sha1 `96a9c695ff`, 12 colunas de 64); a do n005 construída antes do hfoo tinha só 6 colunas: reconstruir as unidades da raça com a tabela final antes de exportar. Zonas (média 5 vistas) próprio -> partilhado: n01X .212 -> .178, n005 .519 -> .562, n02X .304 -> .306, hfoo .196 -> .196. Pareado (A = próprio, B = partilhado): sheet A (4-0, 4-0, 3-1; n02X empate): o sheet tem os olhos/placas que o partilhado não pinta; artist/wc3/form B em n02X e hfoo (4-0 nos três), n01X wc3 e form B 3-1, n005 form B 4-0 mas artist A 3-1 (superfície mais limpa, sem as linhas de tinta). `shared-n005.png`, `shared-n02X.png` (linhas: próprio, partilhado, partilhado ramp 0.5).

- **Piorou:** decais e tinta somem no partilhado (por isso opt-in e não default); a rampa por face e o `cull` não ligam. **Fora:** quantizar cores quase iguais numa só coluna (ΔE) quando a tabela da raça passar de 64, e colocar os decais num segundo atlas partilhado (hoje `images == 1` é gate); add quando uma raça encher a tabela.

## 25. Leva 7 (2026-10-29)

RTS e laterais. Bateria `v11-r1` (4 unidades de prova, pareada contra v10) com L7-2 (coerência do rts) e L7-4 (lathe
deitado) integrados; L7-3 opt-in; L7-1 e L7-5 integrados depois da bateria. Imagens em `history/2026-10-29-v11/`.

| unidade | v10 f/l/b · rts | v11 f/l/b · rts | veredito | juiz v11 × v10 |
|---|---|---|---|---|
| n005 | .909/.926/.909 · .862 | .909/.935/.905 · .872 | CHECK (tris 764 > 700) | empates; form v11 3-1 |
| n00U | .833/.739/.832 · .617 | .843/.700/.840 · .630 | CHECK (rts) | v10 4-0 |
| hfoo | .858/.450/.858 · .648 | .855/.530/.849 · .652 | CHECK (left: lança) | v11 4-0 sheet |
| n017 | .872/.719/.807 · .692 | **.882/.746/.830** · .671 | **PASS** (1º quadrúpede) | **v11 4-0 nos 4** |

### 25.L7-2 Coerência do rts: hull front x left na câmera do jogo, `--redo-rts` (2026-10-27)

- **Mudou:** `silhouette.sheet_report` ganha `coherence.rts` e `rts_cam`: o hull front⊗left (64³, `hull_voxels`) é projetado
  (ortográfico, `hull_rts_mask`) em cada câmera de `views.RTS` x os 2 sentidos do painel left, e o melhor IoU com
  `sheet-rts.jpg` é a coerência (`rts_coherence`). < 0.6 entra em `incoherent`: o veredito do estágio 1 ignora o rts
  (como top/bottom, L6-9), `sheet_line`/`sheet_text` o dizem no review/brief. Sem run: varre os candidatos; `cams=` fixa.
  `spec_pipeline.py --redo-rts refs/<id>/sheet.jpg` (`redo_rts`): referência = faixa front+left+back do sheet
  (`silhouette.ortho_strip`), prompt `prompts/00-template-rts-redo.txt` (35° de elevação, 30° de azimute, mesma figura e
  escala), até 2 chamadas; o antigo vai para `refs/<id>/old/sheet-rts-v<N>.jpg`, o novo só entra se a coerência subir e
  mostrar 1 figura.
- **Coerência do rts nos sheets (antes):** n005 .714, n00H .290, n00U .663, n010 .567, n017 .575, n01I .715, n01N .388,
  n01X .744, n02X .714, hfoo .566; h05X sem rts. Incoerentes (<0.6): n00H, n010, n017, n01N, hfoo.
- **Regeneração (6 chamadas de 8, ~$0.015):** n00H .290 -> .548 (aceito); n010 .567 -> .589 (aceito, 2ª tentativa; 1ª .560);
  n017 .575 -> .588 (aceito pela regra, mas ver abaixo, revertido); n00U coerente (.663), não regenerado.
- **IoU do rts no clay v10 (`silhouette.py --shape`):** n00H .232 -> .502; n010 .547 -> .671; n017 .692 -> .574 (-0.118);
  n00U .617 (sem mudança). Nenhum passa o gate .70 (incoerência continua sendo reportada: n00H .548 < .6).
- **Piorou / negativo:** n017: ganho de coerência +0.013 é ruído e o rts do modelo caiu; refs/n017/sheet-rts.jpg foi
  restaurado do `old/` (o novo ficou em `old/sheet-rts-redo1-1.jpg`). Aceitar "coerência subiu" sem margem não basta:
  adicionar margem (ex. +0.03) quando houver mais amostras. Nenhuma regeneração chega a 0.6 com 1-2 tentativas.

### 24.L6-7 Wiersma: otimização de vértices de topologia fixa, opt-in `--fit-verts` (2026-10-27)

**O que mudou.** `tools/blender/optimize_verts.py <glb> <sheet> <out.glb> [--views front,left,back,top,bottom,rts] [--iters 30] [--seconds 120]`
(python3.14 + numpy/scipy/PIL, sem Blender, sem SDS). Só POSITION/NORMAL mudam (skin e UV ficam; `deform_to_sheet.rewrite` virou
o leitor/escritor comum). Variáveis = vértices soldados da maior componente (o corpo); props (outras componentes) ficam parados.
1. Objetivo (em alturas): Σ vistas (1 − IoU suave do raster 4x dos triângulos) + 10·chamfer de contorno (vértices de contorno → contorno do
   painel, Sketch2Mesh Eq. 5) + 0.05·fairness (média de ((ângulo − π/3)/(π/3))², Wiersma §3) + 10·|L(x − x0)|² (Laplaciano do deslocamento).
2. Gradiente do IoU por diferença finita **local por vértice**: re-rasteriza só o 1-anel numa janela (contagem de cobertura em 4x, soma
   incremental de interseção/união): ~1-2 s por gradiente completo. Fairness: diferenças finitas por canto de triângulo; chamfer e
   Laplaciano analíticos. Vistas com IoU inicial < 0.5 (rts de um voador, top/bottom do n010) saem do objetivo.
3. Passo máximo 0.02 H; line search em 6 frações; se o passo inteiro não baixa o objetivo, tenta por 8 blocos de altura (coordinate
   descent). Recusa/repara: face virada (contra a orientação inicial) ou sliver novo (< 10°): os vértices da face têm o passo
   cortado ao meio 3 vezes e depois zerado; nenhuma vista cai > 0.01 de IoU abaixo do começo. No fim `settled` puxa de volta as
   faces que o `mesh_lint` contaria como `flipped` (cosseno face × normal dos cantos do arquivo < 0 e pior que no começo).
4. Multi-resolução: 35 % do tempo só com âncoras (1 vértice em 4; o resto segue por interpolação harmônica), depois todos.
   Medido (n005, 90 s): objetivo final 0.754 com âncoras, 0.772 sem.
5. Gancho: `spec_pipeline --fit-verts` (`FIT_VERTS = False`), depois do `deform_to_sheet.apply` (guarda `clay-prefit.glb`, `clay.verts.json`)
   e em `colour_stage.build_textured`; só com `UNION_BODY`. ~2 min por unidade.

**Prova sem LLM** (8 specs v9-r1 reconstruídos com `spec_pipeline --spec ... --no-repair --no-fit --shape-only` no HEAD, corpo = 1 casca +
props; antes = clay deformado do L6-5, depois = `optimize_verts` 120 s; silhouette.py com render real; `history/2026-10-28-l6-7/`):

| unidade | IoU f/l/b antes | depois | vermelho médio f/l/b | verde médio f/l/b | ΔIoU top/bottom/rts | slivers % | flipped | normal_diff médio | vistas <8 % (v+v) | s |
|---|---|---|---|---|---|---|---|---|---|---|
| n005 | .854/.920/.859 | .893/.923/.906 | 4.1 → 3.5 % | 8.8 → 6.2 % | +.054/+.043/+.029 | 14.1 → 11.4 | 0 → 0 | 44.16 → 48.44 | 1 → 3 | 123 |
| n00H | .804/.678/.800 | .859/.805/.854 | 12.5 → 4.0 % | 14.4 → 13.0 % | +.096/+.036/+.018 | 10.7 → 6.6 | 0 → 0 | 47.38 → 53.58 | 0 → 0 | 124 |
| n00U | .853/.747/.853 | .875/.788/.869 | 6.4 → 4.3 % | 13.3 → 12.3 % | +.032/+.056/+.016 | 21.7 → 15.8 | 0 → 0 | 44.25 → 49.48 | 0 → 0 | 122 |
| n010 | .778/.842/.607 | .815/.869/.653 | 13.2 → 7.7 % | 16.9 → 17.1 % | -.003/-.009/+.043 | 17.1 → 13.2 | 0 → 0 | 50.48 → 52.87 | 0 → 0 | 122 |
| n017 | .884/.731/.816 | .884/.765/.824 | 7.9 → 6.5 % | 13.0 → 12.6 % | +.013/+.039/+.027 | 29.3 → 24.8 | 0 → 0 | 46.35 → 49.38 | 0 → 0 | 122 |
| n01X | .845/.875/.848 | .883/.851/.885 | 9.0 → 6.0 % | 6.5 → 7.6 % | +.056/+.048/+.026 | 19.4 → 15.2 | 0 → 0 | 51.48 → 51.65 | 0 → 2 | 125 |
| n02X | .837/.866/.850 | .849/.866/.863 | 5.7 → 5.5 % | 10.3 → 9.5 % | +.025/+.034/+.061 | 19.8 → 15.2 | 1 → 1 | 52.64 → 53.91 | 0 → 0 | 127 |
| hfoo | .796/.515/.814 | .828/.546/.822 | 18.6 → 15.9 % | 17.0 → 16.4 % | +.016/-.005/+.028 | 17.6 → 15.4 | 0 → 0 | 44.73 → 47.78 | 0 → 0 | 127 |
IoU mean f/l/b before 0.8031 after 0.8323
red mean f/l/b before 0.0968 after 0.0668
green mean f/l/b before 0.1253 after 0.1183
views <8%: 1 -> 5 of 24

- IoU f/l/b médio .803 → .832 (sobe em 7 das 8 unidades nas 3 vistas médias; top/bottom/rts sobem em quase todas: n00H top +.096).
  Vermelho médio f/l/b 9.7 → 6.7 % (abaixo de 8 %); **verde 12.5 → 11.8 %: a meta (vermelho E verde < 8 % em front/left/back) não
  fecha**: 5 de 24 vistas (1 antes), só o n005 (3 de 3) e n01X (2 de 3). O verde é malha fora do contorno do sheet (proporção da
  figura, corpo largo demais no left do hfoo/n00U); com a mesma malha de ~630 faces o otimizador só troca vermelho por IoU. Por isso
  **continua opt-in** (`FIT_VERTS = False`).
- Slivers (mesh_lint) caem em todas: 14.1 → 11.4, 10.7 → 6.6, 21.7 → 15.8, 17.1 → 13.2, 29.3 → 24.8, 19.4 → 15.2, 19.8 → 15.2, 17.6 → 15.4 %
  (a fairness e a recusa de sliver novo). `flipped` 0 → 0 em 7 unidades (n02X já tinha 1, fica 1).
- **Piorou:** `normal_diff` médio sobe 0.2-5.3° (44.2 → 48.4 no n005, 47.4 → 53.6 no n00H): a malha segue o contorno e dobra mais; n010 top/bottom
  −.003/−.009 e hfoo bottom −.005 (vistas só vigiadas); esticão p99.5 do `walk` igual ±0.6 (n005 3.80 → 4.44, n00H 2.65 → 2.96; as demais iguais
  ou menores), `max_dup_split` 0.0 nas 8: sem rasgo (`history/.../walk.txt`).
- Tempo: 120 s por unidade (para por prazo; ainda descendo: 90 s dá objetivo ~3 % pior). Tentativas que NÃO ajudaram: sem o gate de
  `flipped` o `mesh_lint` marcava 1-3 faces `flipped` por unidade (slivers de ~150° que viravam de lado); fazer esse teste a cada passo
  (normais soldadas) recusava a maior parte dos passos e perdia metade do ganho; ficou como passe final.
- Fora: SDS/difusão, fabricação, cotangente, aresta interna (L6-12), props como variáveis, `normal_diff` no objetivo (próximo passo se o corpo dobrar demais).
- Papers: Wiersma 2026 §3-4 (orçamento fixo, posição de vértices, line search que recusa inversão, fairness), Sketch2Mesh 2021 (chamfer Eq. 5).


### 20.L7-4 Lathe deitado (`axis: "z"`) ligado; prop inclinado (`lean_props`) NEGATIVO, desligado (2026-10-27)

- **Lathe deitado.** `lathe_limb`: `opts.axis = "z"` com perfil de anéis `[w, hh, yc, xc, t]` (obrigatório): elipse de raio x `r*w` e y `r*hh`, centro `(xc, yc)*r`, em `z = at.z - h/2 + t*h`; 8 lados, tampas. Todo leitor usa `lathe_rings` (build_unit.swept_part, preflight.part_tris/bbox, fit_spec.part_points); o fit já move `w`/`hh` por ±15 % (`apply_profile`); `cut_hull.cuttable` exclui `axis z`. `massing._trunk_lathe`: o tronco de quadrúpede/drake (antes `TRUNK_SLABS` = 8 `_brick`) vira UM lathe deitado por osso (`spine.1` atrás, `spine.2` à frente; os dois são ossos exigidos), 5 anéis nos breakpoints da altura (left), centro e meia-largura (top), sobrepostos em 10 % do comprimento (sem a sobreposição o fit os separa e `overlap` reprova). Flag `massing.HORIZONTAL_LATHE = True`; False = os tijolos. Wyrm: o corpo já é `chain` (sem `_brick`), não muda; a cabeça de tijolos do quadrúpede sem asa fica.
- **Medida (rebuild do massing sozinho, `--no-repair`, sem LLM; antes -> depois; `runs` em scratchpad `leva7-horizontal/`).**

| | front | left | back | top | bottom | rts |
|---|---|---|---|---|---|---|
| n017 `--no-fit` | .865 -> .880 | .711 -> .712 | .794 -> .818 | .759 -> .800 | .832 -> .878 | .662 -> .646 |
| n017 com fit (padrão) | .871 -> .884 | .713 -> .751 | .803 -> .831 | .783 -> .817 | .853 -> .880 | .665 -> .678 |
| n010 (drake) `--no-fit` | .847 -> .863 | .842 -> .837 | .572 -> .574 | .440 -> .444 | .441 -> .450 | .540 -> .542 |

  n017 left +0.038 com o fit (meta +0.03; sozinho o massing só dá +0.001: o ganho vem de o fit ter anéis para mexer), front +0.013. n017 rts -0.016 sem o fit (+0.012 com). n010: dentro de ±0.02 salvo left -0.005. Tris n017 630 -> 562. n00H (wyrm) não muda: sem tijolos de tronco; o +0.03 de left dele depende de outro item (corpo em S, uma `chain`). Ruído: o fit varia ±0.03 entre rodadas (n010 com fit mostrou front -0.05 numa rodada e +0.016 sem fit), compare sempre `--no-fit` para o efeito do massing.
- **Prop inclinado: NEGATIVO.** `massing.lean_props` / `lean_poles` (`LEAN_PROPS = False`): o grupo de linhas de um prop longo (haste + ponta, mesmo `prop`) é girado como corpo rígido em torno do pé da haste até a diagonal que `pole_part` dá (box3d de `parts.json` + `pole_lean` do left; o x fica o do autor), com a altura do topo mantida (primeira versão, com a haste esticada à diagonal da caixa, subiu o prop a 2.93 m e encolheu todas as vistas, front -0.11). hfoo v10-r1 (spec do autor, pique em pé), rebuild:

| hfoo | front | left | back | top | bottom | rts |
|---|---|---|---|---|---|---|
| v10-r1 `--no-fit` | .852 | .450 | .862 | .830 | .797 | .648 |
| com lean `--no-fit` | .827 | **.759** | .837 | .586 | .630 | .486 |
| com lean, fit | .839 | **.670** | .847 | .635 | .700 | .526 |
| lean pela metade (`LEAN_SHARE` .5) `--no-fit` | .846 | .531 | .848 | .694 | .656 | .608 |

  left passa a meta (> .65) mas top -0.24, bottom -0.17, rts -0.16: o top do sheet não desenha o pique com 2 m de profundidade, a caixa do `parts.json` (z -0.77..1.38) vem do left; o comprimento em z domina o contorno do top/bottom/rts. A metade do lean também perde top -0.14. Fica desligado; add quando o top/rts do sheet mostrarem o pique (ou quando o fit/deformação do L7-1 tratar top/rts do prop). `lean_poles` tem teste (haste e ponta giram juntas, topo mantido).
- **Fora:** o `rot` em 2 eixos do prop (o pique é `prism` `from`/`to`, que já é qualquer direção); leitura do eixo maior da máscara do prop por painel (o box3d do VLM já a traz).


### 25.L7-3 Pernas no top e no rts (2026-10-27) - NEGATIVO, opt-in (`rig_families.TOP_LEGS`, `fit_spec.LEG_SPILL_W`)

**O que mudou.**
1. `silhouette.leg_branches(top, k)` (e a chave `legs` de `measure_spider`): cada perna é um ramo do painel top fora do corpo (abertura dos finos
   como em `leg_ridge`, máscara menos o corpo dilatado, componentes conexos; fang/palpo < 0.6 da área mediana saem). Por perna:
   `[ângulo, base x/z, joelho x/z, ponta x/z, raio]` em frações de H, relativo ao centro do corpo; o joelho é o ponto 0.6 da corda mais o
   desvio lateral médio do ramo. `None` se não sobram exatamente 8 ramos (pernas coladas): o anel regular fica. n00U: 8 pernas, 4 por lado.
   n01N (`spider_high`) devolve None (tronco coberto), n017 não tem pernas no top (ficam sob o corpo).
2. `rig_families._legs_top` (+ `spider_leg_len` pela mediana das pernas): cada osso `leg<i>` pega a perna medida mais próxima do seu ângulo
   do anel; `massing.spider` emite UM `limb` por perna (hip -> joelho do top -> pé; altura do joelho = `knee_h` da frente; raio do painel,
   ponta 0.8x) em vez de dois prismas. Preflight: `leg_length` conta hip-joelho-pé para `limb` e `leg_radius` lê os 3 raios (senão `spider_leg`
   e `spider_leg_w` falhariam por construção). Ligado só com `TOP_LEGS = True`.
3. `fit_spec.leg_spill` + `LEG_SPILL_W`: a parte `leg*` cujo contorno no rts sai da máscara do sheet em mais de `LEG_SPILL` (0.2) da própria
   área custa `LEG_SPILL_W` por excesso no objetivo. Desligado (`LEG_SPILL_W = 0`).
4. Fora: rts como fonte da medida (o rts é uma 3/4 desenhada com a câmera que a varredura escolhe, as pernas somem sob o corpo; `ponytail`: ler
   quando houver câmera fixa), quadrúpede (as pernas não aparecem no top; o `left` já dá a coluna do joelho em `legs.x`), `family_place` (não mudou).

**Prova sem LLM** (`spec_pipeline --spec ... --no-repair`, fit + deform ligados, juiz `sheet.jpg`; runs em `scratchpad/leva7-legs/`):

| caso | front | left | back | top | bottom | rts IoU | rts spill |
|---|---|---|---|---|---|---|---|
| n00U massing antigo (prismas, anel) | .843 | .700 | .844 | .672 | .656 | .641 | .249 |
| n00U massing `TOP_LEGS` | .841 | .676 | .827 | **.771** | **.756** | .590 | .210 |
| n00U massing `TOP_LEGS` + spill | .795 | .664 | .777 | .728 | .737 | .528 | .283 |
| n00U v10-r1 antes | .855 | .759 | .857 | .711 | .686 | .652 | .283 |
| n00U v10-r1 + spill (`TOP_LEGS` on) | .842 | .761 | .842 | .701 | .659 | .657 | .209 |
| n00U v10-r1 + spill (default de hoje) | .842 | .746 | .839 | .694 | .661 | .646 | .268 |
| n00U v10-r1 + spill estrito (0.05, peso 3) | .833 | .734 | .838 | .697 | .671 | .645 | .250 |
| n017 v10-r1 antes -> + spill | .877 -> .880 | .732 -> .735 | .813 -> .809 | .808 -> .809 | .847 -> .845 | .685 -> .689 | .261 -> .258 |

- **Ganho real:** o massing com as pernas do top leva top/bottom de .672/.656 para .771/.756 (+.10, as pernas caem onde o desenho as tem).
- **Piorou:** left -.024, back -.017, e o rts cai .05 (.641 -> .590): o rts do sheet é uma vista 3/4 desenhada, as 8 pernas do top (simétricas
  esq./dir.) não casam com as do desenho, e a câmera que a varredura escolhe muda entre as variantes (tilt 65/60 na base, 35/30 nas novas).
  Com o termo de spill ligado junto, front/back caem .05: o Powell paga a perna com a silhueta do corpo.
- **Meta não atingida:** spill rts n00U 31 % -> < 15 % e IoU rts > .70 (v10-r1: .283 -> .209 só na combinação que não é o default, .268 no
  default). O spill do rts é do corpo (casca em 3/4) mais que das pernas; a perna sozinha não fecha o número.
- Decisão: comportamento antigo é o default (`TOP_LEGS = False`, `LEG_SPILL_W = 0.0`); o código, o preflight e os testes ficam para quando o
  rts tiver câmera fixada (L7-2: rts regenerado amarrado aos 3 painéis).
- Papers: Sano 2026 (volume por parte a partir de vistas), Sketch2Mesh 2021 (termo de contorno por parte).


### 25.L7-5 Corpo contra o corpo, props contra os props (2026-10-27)

**Achado.** Nos overlays do hfoo v10-r1 (left/rts/bottom) as pernas e os pés eram arrastados para a lança diagonal do desenho,
uma parte que a malha não tem: `fit_spec` (proxy) e `deform_to_sheet` usavam a silhueta inteira do painel como alvo.

**O que mudou** (Sketch2Mesh, Fig. 2c / Eq. 5: o contorno-alvo é do que se está ajustando).
1. `silhouette.prop_masks(sheet, view)` = `{prop: máscara}` de `refs/<id>/parts.json` (`box2d` da vista): pixels do painel dentro da
   caixa do prop, dilatados 2 px (`PROP_PAD`). Caixa grande (> 25 % do painel, a lança diagonal: a caixa cobre a figura)
   perde os pixels das caixas das peças de corpo (+ 2 %); caixa compacta (tanque) fica inteira, mas só vale se >= 50 % dela está
   fora das caixas do corpo (óculos, cinto dentro do corpo não são contorno). `silhouette.body_mask(sheet, view)` = painel
   normalizado menos os props (o painel inteiro quando não há máscara). Sem `parts.json` / sem caixa na vista: comportamento antigo.
2. `deform_to_sheet`: o corpo = maior componente soldada; seus vértices só têm alvo nos pixels do contorno do sheet fora das
   máscaras dos props (`View.goal(0)`; o contorno é filtrado, não o corte da máscara, para não puxar para a borda artificial).
   `--no-split` = antes. O relatório (`*.deform.json`) traz `uncovered_body/prop`, `spill_body/prop` por vista com máscara.
3. `fit_spec.Proxy.set_split` / `score_view`: nas vistas com máscara de prop, as peças não-prop contam contra o `body_mask`
   (IoU + chamfer), os props que o modelo tem contra a máscara dos props, no mesmo espelho, IoU pesado pela área; o raster das
   peças parciais usa o canvas do modelo inteiro (`raster(outs, canvas)`). `ious()`, o gate e as demais vistas seguem na silhueta inteira.
4. `silhouette.py`: cada vista com máscara ganha `uncovered_body/prop` (parcelas do sheet, somam o total) e `spill_body/prop` (parcelas do
   modelo; spill a <= 6 px de um prop é do prop). O gate continua no total.

**Prova** (rebuild `--spec runs/draft/<id>/v10-r1/spec.json --no-repair`, fit + deform ligados, antes = código de `cddf0f0c`; IoU f/l/b/top/bottom/rts, mesma `silhouette.py`):

| unidade | antes | depois |
|---|---|---|
| hfoo | .854 .501 .842 .854 .802 .661 | .883 .477 .887 .856 .797 .655 |
| n005 | .909 .926 .910 .745 .774 .859 | .902 .925 .907 .748 .780 .860 |
| n02X | .873 .805 .889 .758 .730 .723 | .871 .805 .887 .759 .732 .724 |
| n00U | .851 .765 .856 .711 .686 .653 | .842 .802 .846 .703 .689 .643 |

- **hfoo, o arrasto some:** o ajuste movia `thigh.L`/`thigh.R` em z -0.052 / -0.072 m (rumo ao pique); agora 0.001 / 0.000 (e `shin`/`foot` iguais). Front/back +0.029/+0.045.
  Left -0.024: o pique que o modelo não tem era 0.266 do `uncovered` do left e continua (corpo 0.075 -> 0.080, prop 0.266 -> 0.280); o IoU do left cai porque o ajuste deixou de
  inflar o corpo para cobrir a lança. `uncovered` corpo/prop do front: 0.053/0.026 -> 0.037/0.033.
- n005 (não cai): -0.007/-0.001/-0.003 f/l/b, dentro do ruído do ajuste (limite de tempo: o mesmo spec varia ~0.01-0.03 entre runs). n02X igual (±0.002; rts +0.001). n00U: front/back -0.01, left +0.037
  (o spec do ajuste mudou; é a unidade com mais variação entre runs).
- Testes: `test_silhouette.BodyOnly`, `test_deform_to_sheet` (alvos por componente), `test_fit_spec.BodySplit`. 492 testes OK; ruff com os mesmos 10 achados anteriores (nenhum em arquivo tocado).

**O que piorou / negativo.**
- `PROPS_OWN_MASK = False`: puxar cada prop só para a própria máscara (item 2 do pedido) custou n005 left 0.925 -> 0.896 em deform isolado e 0.926 -> 0.899 no pipeline (o tanque,
  cortado pela caixa da saia na máscara, perde alvo; dilatar a máscara de alvo 2-10 px oscila 0.896-0.912). Fica desligado: os props mantêm o contorno inteiro (antes). O código e o teste
  estão (`target_keys`); ligar quando a máscara do prop não for cortada pelas caixas do corpo.
- No deform o arrasto do hfoo não vinha de lá (o left nunca moveu as pernas nesse GLB): a correção que mexe nas pernas é a do `fit_spec`. A restrição do corpo no deform é inofensiva (±0.005) e fica.
- Sem `parts.json` não há máscara de prop (`props.json` + `prop_measure` exigiria render do prop e achar sua posição no painel): comportamento antigo. Só front/left têm caixa; back/top/bottom/rts seguem na silhueta inteira.
- Máscara do prop é aproximada por caixas (o corte na caixa da saia come ~13 % do tanque do n005 no left).
Diagnóstico do v10: front/back passam em 7 de 8; o erro ficou no rts e no left. Provas: rebuild sem LLM dos specs
`runs/draft/<id>/v10-r1/spec.json` (n00U, n017, n00H, hfoo, n005 como controle) com `--no-repair`; fit e deformação rodam.

### 25.L7-1 Seis vistas no fit e na deformação (2026-10-27) - rts +.01 a +.02 (meta +.05 NÃO atingida); front/left/back sem perda pareada

**Resultado medido: rts +0.01, front/left/back -0.008; por isso as 6 vistas são OPT-IN (`--views front,left,back,top,bottom,rts`), o default continua 3.**

**O que mudou.**
1. `views.VIEW_WEIGHTS[rig]` / `weight_of(rig, view)`: spider e quadruped rts, top, bottom x2; biped rts x1.5; o resto 1.
2. `fit_spec.Proxy(rig=...)`: o `loss` é a média PONDERADA dos custos por vista (`1 - IoU + chamfer`); `fit` passa `doc["rig"]`.
   (O fit já via top/bottom/rts desde 21.F4; só faltava o peso.)
3. `deform_to_sheet`: rts entra como vista (`rts_axes(cam)` = a projeção de `fit_spec.project("rts")`: câmera ortográfica
   com `views.rts_offset(elev, azim)` olhando o centro; `sheet_panels` lê `sheet-rts.jpg` quando "rts" está em `views`;
   sem espelho, a varredura de azimute cobre os dois lados). Câmera: a do `silhouette.json` da run (`run_cams`: `tilt`) ou,
   sem ele (a deformação roda antes da silhueta da run), a melhor das 24 de `views.RTS` / 9 tilts x 2 giros. `--views`
   com as 6 (`--views front,left,back,top,bottom,rts`) liga isto; `--rig` escolhe os pesos. `apply` passa `args.rig` e as câmeras.
4. Duas fases em `deform`: (1) front/left/back sozinhos, idêntico ao 24.L6-5 (slivers +5 pp, top/bottom só vigiadas, sem guarda de
   rts); (2) as 6 vistas, IoU médio ponderado, guarda 0.01 contra o que a fase 1 deixou em TODAS as vistas (nenhuma ortográfica cai
   > 0.01 pelo que o rts/top/bottom pedem) e slivers `+EXTRA_SLIVER = 2 pp` sobre a fase 1. Vista extra que COMEÇA com IoU < `PULL_MIN`
   (0.4: n00H rts .22, o desenho não concorda com os 3 painéis) só é vigiada, não puxa.
   Por que duas fases: uma só com 6 vistas e +2 pp total custava n005 left .925 -> .905 e n017 front/back -.02 só do teto de slivers
   e do rts como guarda (medido; versão intermediária descartada).

**Projeção conferida.** IoU da máscara projetada do GLB (`rts_axes` + `view_state`) contra o render real `sil-rts@e_a.png`
(Blender, ortho): n017 .971-.988 nas 4 câmeras testadas (65/60, 35/-60, 45/45, 55/-30); n00U 35/-60 .979, 55/-30 .904,
45/45 .857, 65/60 .833. O erro do n00U é do RENDER, não da projeção: `render_silhouette` usa `ortho_scale = 1.15 x` a maior
extensão em repouso e a aranha aberta sai do quadro nas câmeras altas (linha 511 do PNG 512 ocupada; o overlay das duas máscaras
coincide exceto pelo corte). Vale um `ortho_scale` por câmera em `render_silhouette` (não toquei; é do pipeline de silhueta).

**Medida A: pipeline inteiro (fit + deform), v10 = código de antes x código novo, mesmos specs** (silhueta real; IoU antes>depois; o
fit tem orçamento de tempo, então o spec de entrada do deform varia entre rodadas: ruído de ~.01-.02, ver B):

| unidade | front | left | back | top | bottom | rts | rts vermelho / verde |
|---|---|---|---|---|---|---|---|
| n00U | .855>.857 | .771>.792 | .856>.858 | .715>.721 | .691>.708 | .649>.642 | 12.7>15.1 % / 28.3>27.6 % |
| n017 | .877>.864 | .732>.714 | .813>.795 | .808>.803 | .847>.878 | .685>.696 | 9.6>9.4 % / 26.1>25.0 % |
| n00H | .850>.882 | .665>.664 | .851>.879 | .712>.703 | .692>.682 | .226>.226 | 59.6>59.9 % / 66.1>66.0 % |
| hfoo | .854>.887 | .501>.497 | .842>.881 | .854>.844 | .802>.810 | .661>.650 | 14.0>15.0 % / 26.0>26.6 % |
| n005 | .909>.896 | .926>.929 | .910>.908 | .745>.758 | .774>.786 | .859>.871 | 6.2>5.9 % / 9.0>7.9 % |

**Medida B: só a deformação, mesma entrada (`after-<id>/clay-raw.glb`), IoU raster do próprio módulo (projeção ~.97-.99 do render)**,
`old` = 3 vistas (24.L6-5), `six` = 6 vistas com pesos (rts antes>depois; `old` não mede o rts):

| unidade | front old / six | left old / six | back old / six | top old / six | bottom old / six | rts antes>depois six | rts vermelho / verde six |
|---|---|---|---|---|---|---|---|
| n00U (spider) | .862/.862 | .743/.743 | .870/.870 | .730/.730 | .698/.698 | .686>.688 | 18.7>18.4 / 18.5>18.6 % |
| n017 (quadruped) | .876/.869 | .725/.716 | .807/.799 | .866/.883 | .841/.864 | .689>.700 | 10.2>9.9 / 25.2>24.2 % |
| n00H (wyrm) | .844/.876 | .657/.656 | .845/.873 | .716/.708 | .705/.696 | .223>.224 (só vigiada) | 60.7>60.4 / 66.0>65.9 % |
| hfoo | .875/.881 | .494/.494 | .881/.885 | .845/.841 | .801/.812 | .661>.649 | 14.1>15.7 / 25.8>26.2 % |
| n005 (controle) | .911/.903 | .925/.925 | .906/.906 | .738/.750 | .769/.780 | .855>.870 | 6.1>6.5 / 9.4>7.4 % |

Slivers: fase 1 igual ao v10; a fase 2 soma 0 a 1.7 pp (n017 27.8 > 29.4 %, n005 14.6 > 16.4 %, hfoo 16.1 > 16.7 %).

**Leitura.**
- **Meta rts +.05 em n00U/n017: NÃO atingida.** Deformação sozinha: +.002 (n00U), +.011 (n017), +.015 (n005); o fit com peso: n00U proxy rts
  .671 > .691 numa rodada, +.013 a +.023 nas rodadas A. Os passos do rts são recusados (22-31 por unidade): o IoU médio
  ponderado não sobe (um corpo só não acompanha o rts quando as pernas finas do rts da aranha não têm vértice para seguir: 68 recusas
  por `mean` no n00U, 11 por sliver + 12 por face virada no n017). O ganho de rts de verdade é L7-3 (pernas lidas no rts/top) e
  L7-2 (rts coerente: n00H .23).
- Guarda das ortográficas: na prova B front/left/back caem no máximo .009 (n017 front .876 > .869, left .725 > .716, n005 front .911 > .903)
  contra o `old`, e sobem em n00H (front/back +.03) e hfoo. Na prova A (pipeline inteiro) front/back de n017 e n005 caem .013-.018 e o left
  do n017 .018: vem da variação do fit entre rodadas (o mesmo `clay-raw` da B só perde .009), não da deformação; fica como risco.
- Top/bottom: + .011 a + .023 em n017/n005 (B); n00H e hfoo perdem .004-.012 (só guarda).
- Não feito: `ortho_scale` por câmera no render (n00U rts cortado), peso por vista no `accept` do fit real (o `fit_accepted` usa as
  margens sobre os gates, sem peso), 8 iterações (a deformação satura em 4: mesmos passos aceitos), `REACH` 0.2 / `STEP` 0.1 (rts caiu
  ou ficou igual).
- Papers: Sketch2Mesh 2021 (Eq. 5-6: contorno em várias vistas com regularização parcial; aqui, peso por vista), Wiersma 2026
  (recusa de passo que piora o que já estava bom: guarda entre fases).
- Testes: `test_deform_to_sheet` (`rts_axes` = `fit_spec.project`, candidatos de câmera pinada, média ponderada, rts puxado sem espelho,
  rts desconhecido só vigiado, `run_cams`), `test_fit_spec.ViewWeights` (peso por rig no `loss`). 493 testes OK; ruff nos 5 arquivos
  tocados limpo (10 achados antigos em outros arquivos).
- Reproduzir: `build_unit`/`spec_pipeline --spec runs/draft/<id>/v10-r1/spec.json --no-repair` (fit e deform rodam) e
  `deform_to_sheet.py clay-raw.glb refs/<id>/sheet.jpg out.glb --rig spider`.

## 26. Leva 8 (2026-10-29)

Renderização diferenciável como otimizador (papers em `analysis/2026-10-29-papers-diffrender.md`). Bateria `v12-r1` (5 unidades,
`--fit-grad --fit-verts`, pareada contra v11/v10) em `history/2026-10-29-v12/`; detalhe em 26.L8-6. IoU approved f/l/b · rts.

| unidade | antes | v12 | veredito | juiz v12 × antes |
|---|---|---|---|---|
| n005 | .909/.935/.905 · .872 | .909/.942/.917 · .882 | **PASS** | antes em 3 eixos |
| n00U | .843/.700/.840 · .630 | .859/**.777**/.858 · .683 | CHECK (bottom .700, rts .646) | forma v12 4-0 |
| hfoo | .855/.530/.849 · .652 | .832/**.659**/.838 · .645 | CHECK (left acoplamento, top .687) | v12 em 3 eixos |
| n017 | .882/.746/.830 · .671 | .875/.775/.834 · .692 | **PASS** | v12 em 3 eixos |
| n02X | .863/.813/.889 · .724 | .885/**.884**/.898 · .784 | CHECK (preflight shoulder_span) | v10 em 3 eixos |

Defaults depois da leva: `GRAD=soft` (L8-2), `PIPELINE_SECONDS=30` e **`FIT_VERTS=True`** (L8-6b: `--no-fit-verts` desliga); `--fit-grad`, τ anelado,
`--dist/--agg`, `--dihedral`, `--loss asym`, `--fit-luma` opt-in.

### 26.L8-1 Raster suave de silhueta (`tools/blender/soft_sil.py`)

- O que é: o gêmeo diferenciável (torch) do raster duro de `optimize_verts.Ctx`, só para o gradiente; gates e vereditos seguem em
  `silhouette.py`. `project(pos, view)` repete `View.uv` + `frame` (mirror, bbox ajustada ao canvas) em torch, então vale para
  front/left/back e para as câmeras rts/top/bottom (`make_views` com `cams`). `soft_mask(xy_tris, shape, tau, dist, agg, ss)`:
  distância assinada pixel→triângulo só na janela bbox+3τ de cada triângulo (SoftRas Eq. 1, `D=F(δ d²/τ²)`, τ em px do canvas),
  janelas ragged sem padding à la PyTorch3D (blocos de 2M pixels), `dist` logistic|uniform, `agg` prob (`1−∏(1−D)`, Eq. 4, em
  soma de logs) | yager2 (`min(1,√ΣD²)`, GenDR), `ss` = supersample + `avg_pool2d` (como `optimize_verts.pool`). `soft_iou` =
  `Σmin/Σmax`; `loss = 1 − soft_iou`, `mode="asym"` reservado para L8-5 (levanta NotImplementedError). Autograd até `pos` 3D.
- Sem flag: módulo novo, nada o chama ainda (base de L8-2..L8-7). `optimize_verts.py` e `fit_spec.py` intocados.
  CLI: `python3.14 tools/blender/soft_sil.py <run> <sheet.jpg> [--tau 0.5] [--dist] [--agg] [--device]`.
- Medição, τ = 0.5 px, logística/prob, ss=1: |IoU suave − IoU do raster duro `Ctx` (SS=4)| por vista
  (front / left / back / top / bottom / rts); contra `silhouette.iou` o máximo é 0.0080 (n017 bottom).

| unidade | front | left | back | top | bottom | rts |
|---|---|---|---|---|---|---|
| n005 | .0001 | .0048 | .0017 | .0017 | .0004 | .0025 |
| n00U | .0008 | .0004 | .0008 | .0003 | .0004 | .0002 |
| hfoo | .0040 | .0018 | .0002 | .0001 | .0005 | .0001 |
| n017 | .0015 | .0038 | .0040 | .0002 | .0075 | .0029 |
| n02X (v10-r1) | .0001 | .0064 | .0023 | .0007 | .0017 | .0005 |

- Tempo forward+backward por vista (~630 tris, float32, mediana de 18 chamadas depois de aquecer): CPU 33 / 59 / 36 / 37 / 44 ms
  (n005 / n00U / hfoo / n017 / n02X; máximo 88 ms em n00U front, triângulos grandes), MPS 8–18 ms. Meta ≤ 50 ms CPU: cumprida
  em 4 de 5 na mediana; n00U (59 ms) passa por causa de triângulos grandes (janelas de ~10^5 px). Janelas ragged já são a
  vetorização; não precisou de mais.
- Testes: `test_soft_sil.py` (4 rápidos: projeção = frame duro com mirror ±1, τ→0 de logistic/uniform/yager2 = raster duro ≤ 0.01,
  gradiente reduz a loss, asym ainda não; 1 lento `SLOW=1` com n005 v11-r1 nas 6 vistas ≤ 0.01).
- Negativos/limites: τ pequeno (< ~0.3 px) sem `ss` dá gradiente esparso (só pixels de borda); DIB-R (alpha de fundo) não usado.

### 26.L8-8 Luma do cel por shading diferido (2026-10-29)

Paper: Chen et al. 2021, DIB-R++ (só a ideia de shading diferido: a rasterização fixa vira G-buffer, a luz é ajustada depois).
- `render_silhouette.py --ids` agora também grava `<stem>-nrm-<vista>.png` (normal de mundo da face por pixel, mesma câmera dos
  `zone`). `tools/blender/fit_luma.py`: `luma(p) = tom[slot(p)] x ((1-b) + b x max(0, n.L))`, incógnitas L (azimute, elevação),
  b, um tom por slot; `scipy.optimize.least_squares` (soft_l1, 4 inícios de azimute) contra os quantis p10/p50/p90 de luma de
  cada zona do sheet (as mesmas de `silhouette.luma_l1`; modelo e sheet não casam pixel a pixel, então o alvo é a
  distribuição). Saída por slot: multiplicadores claro/médio/escuro (`tones`) por média do luma ajustado em cada classe de
  `surfaces.tone_index`, refinados contra o mesmo alvo com a luma do slot e o clip em branco. Slot `glow` fica de fora.
- `palette[slot]["tones"] = [up, side, down]` (validado em `colour_stage.valid_tones`, 0 < v <= 3); `build_unit.register_palette`
  lê e `surfaces.paint_cel(tones=...)` usa no lugar de `CEL_TONES`/`CEL_SURFACE`. Ligar: `spec_pipeline --fit-luma` (só
  `--texture cel`) ou `colour_stage.FIT_LUMA = True`. **Default desligado.** Linha "luma fit" no review (luz az/el, b, perda,
  DEGENERATE quando b < 0.05).
- Medida (stage 2 cel sobre o `clay.glb` mais recente com spec, câmeras do estágio 1; ~14 s sem, ~18 s com o fit):

| unidade | | luma_l1 f/l/b/top/bottom | zones mean f/l/b/top/bottom | cover f/l/b/top/bottom |
|---|---|---|---|---|
| n005 v11-r1 | antes | .049/.035/.035/.033/.072 | .62/.72/.65/.43/.31 | .92/.96/.92/.68/.63 |
| n005 v11-r1 | depois | .037/.022/.022/.005/.069 | .62/.71/.67/.43/.32 | .94/.96/.94/.68/.64 |
| n01X v9-r1 | antes | .024/.024/.059/.044/.071 | .24/.19/.41/.16/.06 | .50/.46/.75/.45/.21 |
| n01X v9-r1 | depois | .039/.024/.046/.026/.043 | .24/.18/.24/.18/.08 | .51/.47/.48/.49/.27 |

- Luz ajustada: n005 az -139 / el 58, b .22; n01X az -2 / el 0, b .45 (luz rasante: a perda cai de 1.63 para .29 mas a direção
  é pouco confiável com 5 slots, e o `darkiron` bate no teto 1.6).
- **Aceite (.029/.031/.024 e zone mean não cai): NÃO atendido.** n005 f .037 (falha), l .022, b .022 passam; n01X f .039 e b .046
  falham e o zone mean do back cai de .41 para .24 (o back "antes" do n01X é alto por sorte de limiar de matiz; o tom
  fitado clareia/escurece a ponto de mudar a zona). Ganho real no n005 (todas as vistas menos bottom por pouco) e em top/bottom
  do n01X; perda em front/back do n01X. b não é ~0 em nenhuma (não degenerou). **Fica opt-in, desligado.**
- Não feito: fitar L/b por unidade só com os slots de zonas bem cobertas; restringir tons a uma faixa mais estreita que
  [0.2, 1.6]; medir nas outras 5 unidades.
- Testes: `test_fit_luma` (ajuste sintético de 8 materiais recupera luz, b e tons; tons de classe no intervalo; flag desligada
  não chama o fit; stage_colour pinta com os tons; schema `tones`).

### 26.L8-2 `optimize_verts` com gradiente do raster suave (`GRAD = "soft"`)

- O que mudou: o gradiente da silhueta em `optimize_verts` deixa de ser a diferença finita por 1-anel (`iou_gradient`, mantida) e vira
  `loss.backward()` de `soft_sil.loss` somado nas vistas ativas (`soft_gradient`: uma passada de autograd até as posições 3D, bbox do
  enquadramento incluída). Chamfer, Laplaciano e fairness seguem em numpy (analíticos / diferença por canto) e somam ao gradiente;
  `Ctx` (raster duro 4x), `evaluate`, `holds`, aceite, line search, recusa de flip/sliver, `settled`, blocos e âncoras intactos: o
  duro decide, o suave só dá a direção. `FIT_VERTS` continua False (L8-6 liga).
- Constantes/flags: `GRAD = "soft" | "fd"` (default soft; `fd` = L6-7 para comparar), `TAU = 0.5` px, `DEVICE = "cpu" | "mps"`,
  `DETACH = False` (bbox do enquadramento constante no gradiente). CLI: `--grad`, `--tau`, `--device`. Âncoras/blocos ficam ligados
  (ablação: `COARSE=0` não ganha, n005 .914/.944/.920 vs .926/.945/.923 em 30 s).
- Tempo do gradiente completo (n005, 6 vistas, ~630 tris, todos os vértices): soft 0.46 s CPU vs fd 1.52 s. O soft converge antes
  de 120 s (84-112 s reais).
- Escolha de τ (soft-30, f/l/b): 2.0 px piora (n005 .904/.937/.906); 1.0 px .918/.940/.916 (n005), .865/.728/.868 (n00U);
  **0.5 px** .926/.945/.923 (n005), .872/.742/.871 (n00U), melhor ou igual; 0.35 px igual a 0.5 (±.004). `DETACH=1`: n00U sobe
  (.893-.900/.755/.887) mas n005 left e n017 left caem 0.01-0.015: fica desligado.
- Medição (clay de entrada = `runs/draft/<id>/v11-r1/clay.glb`, n02X v10-r1; IoU duro do raster de `optimize_verts` em f/l/b;
  τ=0.5 CPU; outros agentes carregavam a máquina (load ~3), então os segundos são pessimistas). Depois: fd-120 | soft-120 | soft-30;
  flipped / slivers % / normal_diff médio / segundos reais:

| unidade | antes | fd 120 | soft 120 | soft 30 | entrada (flip / sliver / nd) | fd 120 | soft 120 | soft 30 |
|---|---|---|---|---|---|---|---|---|
| n005 | .910/.935/.905 | .926/.928/.925 | .924/.942/.926 | .924/.945/.926 | 0 / 15.9 / 42.6 | 0 / 11.6 / 46.9 / 125 | 0 / 12.2 / 45.7 / 95 | 0 / 12.9 / 45.0 / 33 |
| n00U | .844/.696/.840 | .875/.753/.865 | .892/.751/.892 | .873/.737/.873 | 0 / 20.4 / 50.8 | 0 / 16.1 / 56.8 / 122 | 0 / 16.9 / 54.4 / 84 | 0 / 17.8 / 52.5 / 31 |
| hfoo | .838/.534/.850 | .863/.582/.859 | .877/.589/.884 | .859/.573/.865 | 0 / 11.3 / 47.0 | 0 / 8.3 / 49.1 / 121 | 0 / 8.9 / 49.6 / 112 | 0 / 9.4 / 48.4 / 31 |
| n017 | .882/.745/.833 | .887/.765/.828 | .901/.787/.854 | .899/.784/.850 | 0 / 31.5 / 45.5 | 0 / 25.9 / 50.2 / 120 | 0 / 27.2 / 49.4 / 87 | 0 / 27.9 / 48.2 / 34 |
| n02X | .866/.810/.890 | .888/.817/.909 | .881/.831/.903 | .883/.828/.901 | 0 / 15.4 / 47.1 | 0 / 12.4 / 51.7 / 127 | 0 / 13.0 / 52.7 / 94 | 0 / 13.7 / 51.2 / 30 |

  MPS (n005, 30 s): .926/.943/.926, objetivo 0.689 (CPU 0.716): sem ganho relevante de IoU; CPU basta.
- Aceite (soft-30 ≥ tabela L6-7 em f/l/b, flipped 0, slivers não sobem): n005 (.893/.923/.906) **sim**; hfoo (.828/.546/.822) **sim**;
  n017 (.884/.765/.824) **sim**; n00U (.875/.788/.869) **não**: .873/.737/.873 (a entrada v11 já começa em .844/.696/.840, abaixo do
  clay da L6-7, .853/.747/.853; soft-120 chega a .892/.751/.892 e fd-120 a .875/.753/.865 na mesma entrada); n02X (.849/.866/.863
  na L6-7, entrada v9-r1) **não** no left: .828 (a entrada v10-r1 começa em .810). flipped 0 nas 15 saídas; slivers caem em todas.
  Contra fd-120 na mesma entrada, soft-30 (4x menos tempo) empata ou ganha em n005 left, hfoo e n017 e perde 0.002-0.025 em n00U f/l e
  n005 f; soft-120 ganha ou empata (±.003) em 13 de 15 f/l/b.
- Achado: o `iou_gradient` por diferença para frente só vê o movimento +x/+y/+z do vértice; numa parede esquerda de caixa, cujo
  movimento útil é para fora (-x) e cujo movimento para dentro é encoberto pelas outras faces, dá 0 (medido na malha sintética), e
  ignora a renormalização do enquadramento pela bbox; o gradiente suave é simétrico e inclui a bbox (pico ±1.15 nos vértices extremos
  da caixa; no modelo real a busca de linha filtra).
- Negativos: `normal_diff` ainda sobe (n005 42.6 → 45.0 em 30 s, +1.4 a +4 nas cinco): o L8-4 trata; n00U left não fecha em 30 s;
  DIB-R (Cheng et al. 2019) não usado (fundo/alpha não entram), sem linha em `docs/references.md`.
- Testes: `test_optimize_verts.py` +4 (cosseno soft × fd > 0.5 na parede direita da caixa sintética; um passo soft baixa o objetivo e
  sobe o IoU duro; `GRAD` inválido levanta; lento `SLOW=1`: n005 30 s, turned 0, slivers e IoU f/l/b não pioram). 525 testes OK (3
  pulados).

### 26.L8-5 Perda assimétrica vermelho/verde (`LOSS = "asym"`)

- O que mudou: `soft_sil.soft_asym(mask, concept, w_red, w_green)` = `w_red · ΣC(1−S)/ΣC + w_green · ΣS(1−C)/ΣS` (vermelho = sheet
  descoberto = occupancy; verde = modelo fora do sheet = freespace; DVR Eq. 14-15 em máscara; os dois termos são o `uncovered`/`spill`
  suaves de `silhouette.coupling`). `soft_sil.soft_iou(mode="asym")` (o gancho) devolve `1 − soft_asym`, e `soft_sil.loss(mode="asym")`
  sem pesos usa `asym_weights(view.name)`. `optimize_verts`: `LOSS = "iou"` (default) | `"asym"`; com `asym` o gradiente (`soft_gradient`)
  E o termo de silhueta do objetivo duro (`Problem.evaluate`, via `Ctx.asym` no raster duro 4x) trocam de IoU para a perda assimétrica,
  senão a busca de linha recusaria os passos que o gradiente propõe. As guardas (`holds`, piso de IoU por vista) seguem em IoU duro.
  `asym` exige `GRAD = "soft"` (levanta com `fd`).
- Pesos por vista (`asym_weights`): `w_red ∝ 1/UNCOVERED_MAX[v]`, `w_green ∝ 1/SPILL_MAX[v]`, normalizados a `w_red + w_green = 2`
  (escala da perda simétrica): uma fatia no teto custa o mesmo de cada lado. front .15/.20 → (1.14, .86); left .20/.15 → (.86, 1.14);
  back (1, 1); top (1, 1); bottom .25/.20 → (.89, 1.11); rts .20/.25 → (1.11, .89). `RED_BOOST` multiplica o `w_red` de todas as vistas.
- Flags: `--loss iou|asym`, `--red-boost` (default 1.0). `clay.verts.json` ganha `"loss"`; `uncovered`/`spill` por vista antes/depois já
  estavam em `before`/`after` (`D.measure`), com `uncovered_body`/`spill_body` quando há `parts.json` na vista.
- Medição (soft-30, mesma entrada do L8-2, CPU, 3 execuções em paralelo; IoU duro f/l/b; `*` = a vista passa o gate de acoplamento só
  com o `uncovered`/`spill` de cima, f/l/b). Formato `IoU (uncovered/spill)`; "asym2" = `--red-boost 2`:

| unidade | entrada | iou | asym | asym2 |
|---|---|---|---|---|
| n005 f | .910 (.040/.055) | .924 (.035/.044) | .922 (.030/.051) | .916 (.026/.061) |
| n005 l | .935 (.023/.044) | .946 (.021/.035) | .941 (.020/.040) | .939 (.021/.042) |
| n005 b | .905 (.038/.062) | .920 (.032/.051) | .918 (.027/.058) | .914 (.022/.067) |
| n00U f/l/b | .844/.696/.840 | .863/.722/.866 | .866/.731/.867 | .865/.736/.860 |
| n00U l (u/s) | .140/.214 | .129/.192 | .121/.187 | .111/.190 |
| hfoo f/l/b | .838/.534/.850 | .856/.562/.860 | .855/.572/.863 | .852/.565/.862 |
| hfoo l (u/s) | .313/.294 | .283/.278 | .274/.270 | .275/.280 |
| n017 f/l/b | .882/.745/.833 | .894/.773/.844 | .893/.785/.843 | .883/.763/.837 |
| n017 l (u/s) | .176/.114 | .170/.081 | .167/.068 | .167/.099 |
| n02X f | .866 (.057/.086) | .871 (.049/.089) | .873 (.043/.091) | .872 (.039/.096) |
| n02X l | .810 (.093/.117) | .826 (.084/.106) | .828 (.082/.106) | .827 (.081/.108) |
| n02X b | .890 (.046/.070) | .896 (.037/.072) | .896 (.033/.076) | .892 (.030/.082) |

  Tempo 31-34 s nas 15 execuções; turned 0; slivers: asym ≤ iou em n005, n00U, hfoo, n02X (n017 igual).
- Gate de acoplamento (left: uncovered ≤ .20, spill ≤ .15): n005 e n02X passam em **todas** as variantes, inclusive na entrada e
  em `iou` (o left deles já estava dentro dos tetos; a queda do v8 vinha de outra versão do clay, não medida aqui). n00U e hfoo left seguem
  fora (spill .187 e uncovered .274; o clay é que não cobre/ultrapassa, 1-2 pontos de otimização de vértice não fecham). n017 left
  uncovered .167, spill .068: passa nas três.
- Aceite: o gate no left passa (sem depender da perda); n005 f/l/b com asym cai .002/.005/.002 contra `iou` (todas acima da
  entrada, a do left no limite do −0.005). Efeito real: asym baixa o **uncovered** em 15 de 15 vistas f/l/b contra `iou` (n005
  −.005 f/b, n00U −.014/−.008/−.014, hfoo −.003/−.009/−.005, n02X −.006/−.002/−.004) e sobe o IoU em n00U, hfoo e n017 left (+.009,
  +.010, +.012); o preço é spill +.003..+.007 e n005 −.002..−.005. `asym2` empurra o vermelho mais (n005 f .026) mas o spill sobe
  +.01 e o IoU cai: pior. **Decisão: fica opt-in** (`LOSS = "iou"` default); o ganho é pequeno, de sinal misto no IoU e não muda
  nenhum veredito do gate nesta amostra.
- Negativos: nenhum veredito muda; `RED_BOOST = 2` piora o IoU em 4 das 5 unidades; n005 perde até .005 no left.
- Testes: `test_soft_sil.py` +2 líquido (máscara só vermelha → termo verde 0 e o inverso, pesos vindos dos gates, gradiente asym
  desce, modo inválido levanta; o teste do gancho `NotImplementedError` foi substituído), `test_optimize_verts.py` +1 (termo e passo
  asym, `asym` com `GRAD=fd` levanta).

### 26.L8-4 Regularizador de diedro em `optimize_verts` (`LAMBDA["dihedral"]`, opt-in, default 0)

- O que mudou (aditivo): `flat_edges(pos, tri)` seleciona, no corpo soldado e na malha INICIAL, as arestas internas de duas faces cujo
  diedro é < `align_features.FEATURE_DEG` (35°); as vivas do WC3 (>= 35°) não entram, e a seleção fica fixa (`Problem.flat`).
  `dihedral_term(pos, tri, faces)` = média de `(cos θ + 1)² = (1 - n0·n1)²` (NMR Eq. 6; plano = π) e seu gradiente por autograd de
  torch (float64), somado em `Problem.gradient`/`evaluate` só quando `LAMBDA["dihedral"] != 0`. Média, não soma, para o λ não depender
  do número de arestas. CLI `--dihedral λ`. DIB-R (Eq. 11, a mesma regularização de normais) não foi usado como código: sem linha própria.
- Medição (soft-30, mesma entrada do L8-2; 5 processos em paralelo, então poucos passos por rodada: λ=0 é a coluna de controle sob a mesma
  carga). IoU duro f/l/b | `normal_diff` médio entrada > saída | slivers % entrada > saída; flipped 0 em todas as saídas:

| unidade | λ=0 | λ=1 | λ=3 | λ=10 | λ=30 |
|---|---|---|---|---|---|
| n005 (nd 42.6, sl 15.9) | .921/.943/.918 (descarregado; nd 44.8, sl 13.5) | .915/.941/.918 · 43.2 · 14.8 | .911/.940/.913 · 42.6 · 15.6 | .908/.937/.907 · 42.2 · 15.6 | .907/.936/.904 · 41.9 · 15.9 |
| n00U (50.8, 20.4) | .861/.716/.863 · 51.4 · 19.9 | .862/.718/.864 · 51.2 · 19.3 | .860/.717/.859 · 51.0 · 19.3 | .848/.699/.845 · 50.8 · 20.4 | .846/.697/.842 · 50.7 · 20.4 |
| hfoo (47.0, 11.3) | .852/.556/.855 · 47.1 · 9.8 | .855/.559/.858 · 47.1 · 10.2 | .851/.551/.861 · 47.1 · 10.5 | .846/.540/.850 · 46.9 · 11.1 | .842/.542/.847 · 46.8 · 11.1 |
| n017 (45.5, 31.5) | .894/.773/.844 · 46.8 · 29.0 | .885/.775/.847 · 46.1 · 29.3 | .887/.770/.843 · 45.6 · 30.0 | .880/.764/.844 · 45.7 · 29.2 | .883/.753/.839 · 45.2 · 30.3 |
| n02X (47.1, 15.4) | .871/.826/.896 · 49.1 · 14.9 | .874/.824/.896 · 47.8 · 14.6 | .882/.825/.899 · 47.7 · 14.1 | .877/.825/.891 · 47.3 · 14.6 | .874/.824/.891 · 46.7 · 14.5 |

  Confirmação com 120 s (n005, n017; λ=0 > λ=30): n005 .921/.941/.923, nd 45.0, sl 12.7 > .911/.941/.909, nd 41.6, sl 15.1;
  n017 .901/.788/.853, nd 49.1, sl 26.9 > .888/.770/.846, nd 45.1, sl 28.9.
- Aceite (`normal_diff` saída <= entrada nas 5 E IoU f/l/b dentro de -0.005 do λ=0): **não atendido**. `normal_diff` só fica <= entrada
  nas cinco com λ=30 (41.9, 50.7, 46.8, 45.2, 46.7), e aí o IoU cai 0.010-0.020 em f/l/b (n005 f -.014, b -.014; n017 l -.020;
  hfoo f -.010); com λ<=3 o IoU quase não muda mas o `normal_diff` ainda sobe 0.2-1.4 (n017, n02X, n00U). O termo troca silhueta
  por suavidade quase um por um: não há λ que cumpra os dois. Slivers: λ>=10 devolve o ganho que o λ=0 tinha (n005 13.5 > 15.6-15.9).
- Decisão: `LAMBDA["dihedral"] = 0` (desligado, comportamento anterior idêntico: nenhuma chave nova em `terms`). Ligar com
  `--dihedral 30` se um aceite futuro priorizar forma sobre IoU. O L8-6 (fit_verts ligado por default) deve decidir com o `normal_diff`
  da saída, não com este termo. Não testado: λ entre 3 e 10 (a curva é monótona nas cinco), diedro com normais suavizadas por grupo.
- Testes: `test_optimize_verts.py` +3 (`TestDihedral`: arestas de 90° da caixa fora da seleção; grade com vértice central levantado:
  termo > 0, um passo contra o gradiente o reduz, sem arestas vale 0; λ=0 não cria a chave `dihedral`).

### 26.L8-3 Anelamento de τ e ablação de distribuição/agregação em `optimize_verts` (2026-10-29)

- O que mudou (aditivo): `optimize_verts.TAU_SCHEDULE = None` (None = `TAU` constante; tupla de px, um degrau por parcela igual do
  progresso da corrida, ex. `(4, 2, 1, 0.5, 0.5)`), `DIST = "logistic"`, `AGG = "prob"` (passados ao `soft_sil.loss`), `tau_at`,
  `next_level`, `run_progress`; `soft_gradient(..., tau=None)` e `Problem.gradient(..., tau=None)`; `stage(..., span)` calcula o progresso
  global (parcela do estágio de âncoras `(0, COARSE)`, fino `(COARSE, 1)`; maior entre iteração/iters e tempo/orçamento) e, quando nada
  baixa o objetivo naquele τ, pula para o próximo degrau em vez de encerrar. CLI: `--tau-schedule 4,2,1,0.5`, `--dist`, `--agg`.
  `soft_sil.gamma_inv` (Gamma p=0.5 invertida, GenDR: massa toda fora do triângulo, `D = 1` dentro e `erfc(d/τ)` fora) como `dist="gamma_inv"`.
  Sem schedule o comportamento é idêntico ao L8-2.
- Ablação (soft-30 s CPU, entrada = clay v11-r1, n02X v10-r1; IoU duro f/l/b | vermelho+verde % f/l/b do `D.measure`; 3 processos em
  paralelo, load ~5, então os absolutos do n00U ficam .01 abaixo do L8-2; só a comparação entre linhas vale). Grade completa em
  n005 e n00U (18 configurações); sliver 13-15 % (n005) e 19-20 % (n00U), turned 0 em todas:

| schedule | dist / agg | n005 IoU | n005 verm+verd % | n00U IoU | n00U verm+verd % |
|---|---|---|---|---|---|
| const .5 | logistic / prob (L8-2) | .921/.944/.921 | 8.2/5.7/8.2 | .862/.718/.864 | 14.7/32.4/14.6 |
| const .5 | logistic / yager2 | .924/.946/.924 | 7.9/5.6/7.8 | .862/.719/.862 | 14.8/32.4/14.7 |
| const .5 | uniform / prob | .927/.942/.921 | 7.5/6.0/8.2 | .863/.719/.866 | 14.7/32.5/14.4 |
| const .5 | uniform / yager2 | .925/.946/.921 | 7.7/5.6/8.2 | .864/.720/.865 | 14.6/32.3/14.4 |
| const .5 | gamma_inv / prob | .921/.945/.925 | 8.2/5.7/7.8 | .863/.717/.865 | 14.7/32.6/14.4 |
| const .5 | gamma_inv / yager2 | .924/.943/.921 | 7.9/5.9/8.2 | .863/.716/.864 | 14.7/32.8/14.5 |
| 4→.5 | logistic / prob | .919/.943/.919 | 8.4/5.8/8.4 | .866/.715/.864 | 14.4/32.9/14.5 |
| 4→.5 | logistic / yager2 | .920/.942/.922 | 8.3/6.0/8.1 | .865/.718/.863 | 14.5/32.5/14.7 |
| 4→.5 | uniform / prob | .916/.940/.909 | 8.8/6.2/9.5 | .860/.707/.860 | 15.0/34.1/15.0 |
| 4→.5 | uniform / yager2 | .918/.942/.915 | 8.6/6.0/8.8 | .861/.717/.862 | 14.9/32.8/14.8 |
| 4→.5 | gamma_inv / prob | .919/.945/.917 | 8.5/5.7/8.6 | .857/.715/.856 | 15.5/33.1/15.5 |
| 4→.5 | gamma_inv / yager2 | .919/.945/.922 | 8.4/5.6/8.1 | .865/.715/.863 | 14.5/32.9/14.6 |
| 2→.5 | logistic / prob | .914/.939/.913 | 9.0/6.3/9.1 | .865/.717/.865 | 14.5/32.7/14.4 |
| 2→.5 | logistic / yager2 | .914/.943/.914 | 8.9/5.9/8.9 | .861/.721/.862 | 15.0/32.3/14.9 |
| 2→.5 | uniform / prob | .913/.942/.910 | 9.1/5.9/9.4 | .866/.724/.865 | 14.4/31.9/14.4 |
| 2→.5 | uniform / yager2 | .916/.943/.911 | 8.7/5.8/9.3 | .867/.725/.866 | 14.2/31.6/14.3 |
| 2→.5 | gamma_inv / prob | .914/.942/.909 | 8.9/6.0/9.5 | .865/.718/.865 | 14.4/32.5/14.5 |
| 2→.5 | gamma_inv / yager2 | .917/.943/.913 | 8.6/5.9/9.1 | .868/.730/.866 | 14.1/30.8/14.3 |

  Confirmação nas outras três (const .5, mais 4→.5 logistic/yager2; IoU f/l/b | verm+verd % f/l/b | sliver):

| unidade | const logistic/prob | const logistic/yager2 | const uniform/yager2 | const gamma_inv/yager2 | 4→.5 logistic/yager2 |
|---|---|---|---|---|---|
| hfoo | .853/.566/.859 · 15.9/55.5/15.1 | .858/.566/.866 · 15.3/55.4/14.4 | .860/.566/.865 · 15.1/55.4/14.5 | .860/.570/.866 · 15.0/54.7/14.3 | .856/.564/.865 · 15.6/55.8/14.5 |
| n017 | .892/.779/.849 · 11.4/24.4/16.2 | .894/.777/.843 · 11.1/24.6/16.8 | .894/.774/.847 · 11.1/25.0/16.3 | .896/.776/.843 · 10.9/24.8/16.8 | .896/.770/.852 · 11.0/25.8/15.8 |
| n02X | .881/.832/.900 · 12.6/18.4/10.4 | .878/.828/.899 · 12.8/18.8/10.5 | .877/.830/.898 · 13.0/18.5/10.7 | .882/.827/.900 · 12.5/18.9/10.4 | .886/.829/.904 · 12.0/18.6/10.0 |

  Tempo: 30-33 s em todas (gamma_inv 33-38 s sob load; `erfc` e sqrt custam pouco). Slivers: iguais entre as configurações da mesma
  unidade (hfoo 9.7-10.2 %, n017 28.7-29.0 %, n02X 14.2-14.9 %).
- Resultado: **nenhuma variante vira default.** Todas as diferenças ficam em ±.005 de IoU duro (ruído do orçamento de tempo sob
  load); o anelamento de 4 ou 2 px **não ganha** do τ constante 0.5 em n005 (perde .003-.010 em f/b) nem em n00U/hfoo/n017 (±.005),
  e só ajuda um pouco em n02X (4→.5 front +.005, back +.004). Yager(2) rende +.003 em n005 f/b e ±.004 nas outras: dentro do ruído.
  A distribuição (logística, uniforme, Gamma-inv) não separa: no regime τ=0.5 px as três se parecem (banda de ~1 px).
  Aceite (vermelho+verde < 8 % em ≥ 12 de 15 f/l/b; n017 left ≥ .75): **NÃO atendido** por nenhuma configuração; o melhor tem 3
  de 15 (n005 f/l/b com const logistic/yager2: 7.9/5.6/7.8 %); n00U, hfoo, n017 e n02X ficam em 10-55 %, e o limite é a entrada
  (silhueta do clay v11 longe do painel) e não o gradiente, como já via o L8-2. n017 left ≥ .75 passa em todas (.770-.779). Defaults
  mantidos: `TAU_SCHEDULE=None`, `DIST="logistic"`, `AGG="prob"`; tudo opt-in via flags.
- Âncoras (`COARSE`): com o anelamento elas **não ficam redundantes**. `COARSE=0` (só o estágio fino) em n005: const logistic/yager2
  .918/.942/.921 vs .924/.946/.924 com âncoras; 4→.5 .913/.939/.916 vs .920/.942/.922; n00U igual (±.003). Ficam ligadas.
- Negativos: schedule de τ grande não ajuda porque o line search e o aceite já estão no raster duro e o passo é limitado a
  `STEP*H`; o gradiente com τ=4 px move vértices para fora do contorno que o passo seguinte desfaz. `uniform` com 4→.5 foi a pior
  combinação em n005 back (.909).
- Testes: `test_soft_sil` (τ→0 também para `gamma_inv`, ≤ .01 na caixa sintética), `test_optimize_verts` +2 (schedule decrescente pelo
  progresso e `next_level`; gradiente anelado com `gamma_inv` finito e não nulo).

### 26.L8-7 `fit_spec` por gradiente (`tools/blender/fit_grad.py`, `--fit-grad`)

- O que é: o proxy de `fit_spec` em torch. `dynamic` + `POINTS` são o gêmeo de `moved` + `part_points` para box/prism/frustum/cyl/dome/ring/wheel/lathe/limb/chain/plate (dims, `at`, from/to, rot, profile, squash, knee, perfil de plate contínuos; erro < 1e-4 contra o numpy em 89 partes/poses). O contorno convexo de cada parte por vista vira leque de triângulos (a lista de vértices do casco sai dos pontos destacados, os vértices seguem diferenciáveis) e `soft_sil.soft_mask` faz a união pela agregação `1-prod(1-D)`; a canvas é a bbox de todos os vértices, como `canvas_of`. Perda = a de `Proxy.loss`: média ponderada por vista (`weight`), melhor espelho, corpo contra a máscara do corpo e props contra a deles (`split`), `1-IoU` + meia chamfer (só o termo contorno-do-modelo -> mapa de distância da sheet; o outro meio exige distância do contorno predito). Adam, tau 4 -> 2 -> 1 -> 0.7 -> 0.5 px (GenDR), 12 passos por tau (60), lr 0.08; bounds por projeção (clamp), não sigmoide: x0 = 0 fica na borda dos intervalos (-1, 0) de `NO_GROW`, onde a sigmoide não tem gradiente. Um vetor por par L/R (simetria por construção) e props pegam o deslocamento médio da âncora (`carry_props`).
- Regras: a cada 6 passos o ponto passa pelo `Objective` exato (raster duro, preflight, partes soltas, zonas, profundidade); regra quebrada ou custo > melhor + 0.1 puxa o ponto para o último bom (meia distância até 3x, depois o próprio); sem sucesso, lr/2. O `Objective` guarda o melhor ponto exato, e `fit_accepted` segue julgando o clay real. Hinges diferenciáveis na perda das regras que o gradiente quebrava: `ground`, `overlap`/partes soltas (bboxes dos pontos, k=0.8 como `loose_of`), `symmetry` de gêmeos fora de grupo, `feet_mass`/`boot_height`. Partes de kind desconhecido ou `cut: sheet` ficam fixas e vão em `grad_fixed` no report.
- Flags: `fit_spec.py --fit-grad`, `spec_pipeline.py --fit-grad` (opt-in; Powell segue default). `--fit-stages` não vale com grad.
- Medição (mesma entrada `fit/before.json`; n005 `spec.json` já passa todos os gates, então margem 0.1 para forçar o fit). IoU duro do clay real (Blender) depois - antes em f/l/b/top/bottom/rts; `fit_accepted` True em todos (Powell e grad). Tempo: rodada 1 (máquina quase livre) / rodada 2 (outros agentes rodando; carga até 7).

| unidade | Powell (1 run) | grad r1 | grad r2 |
|---|---|---|---|
| n017 | 24 s: +.023 -.006 +.021 +.002 -.013 +.009 | 20 s: +.073 .000 +.099 +.023 -.026 +.013 | 28 s: +.085 +.013 +.099 +.021 -.012 +.021 |
| hfoo | 124 s: +.172 +.100 +.167 +.103 +.109 +.083 | 23 s: +.157 +.036 +.149 +.088 +.105 +.082 | 63 s: +.153 +.034 +.145 +.091 +.105 +.083 |
| n02X (v10-r1) | 54 s: +.036 +.027 +.029 +.057 +.042 +.014 | 25 s: +.040 +.033 +.040 +.106 +.053 +.033 | 115 s: +.045 +.035 +.044 +.099 +.050 +.034 |
| n00U | 153 s: +.022 +.039 +.025 +.021 +.039 +.019 | 47 s: +.043 +.084 +.049 +.049 +.032 +.060 | 75 s: +.043 +.084 +.050 +.049 +.032 +.061 |
| n005 (margem 0.1) | 144 s: +.024 +.023 +.012 +.015 +.021 +.021 | 46 s: +.038 +.034 +.035 +.028 +.010 +.013 | 87 s: +.036 +.034 +.031 +.028 +.013 +.014 |

- Veredito: critério "IoU f/l/b maior no mesmo tempo ou menos" cumprido em n017, n02X, n00U e n005 (n00U e n005 também em ~1/3 do tempo na rodada limpa). **hfoo não cumpre**: f/l/b ficam .015/.064/.018 abaixo do Powell (em 1/5 do tempo; o Powell longo acha o left). Powell é determinístico (rodadas idênticas); o grad varia (n017 loss 1.48-1.79, n02X 0.33-0.63 em f exato, IoU real quase igual). Recomendação: virar default quando hfoo fechar a diferença (ex. Powell curto de polimento depois do Adam); o default NÃO foi mudado.
- Negativos/limites: sem termos de zona/partfit/edges/leg_spill na perda suave (`LEG_SPILL_W = 0`; zonas e partfit entram só no julgamento exato dos checkpoints); metade da chamfer; a bbox dos pontos não é a do preflight (hinges conservadores, 3% de folga nos pés); o ponto fica preso quando uma regra sem hinge (outras bandas biped) bloqueia; sem hinge de `budget`. Tempos da rodada 2 contaminados por carga alheia. CPU, 0.2-0.4 s por passo.
- Testes: `test_fit_grad.py` (paridade torch x numpy em todos os kinds + 3 specs reais, um passo Adam reduz a loss, gêmeos espelhados, flag nos dois CLIs; lento `SLOW=1`: n005 com margem 0.1 sobe o IoU de proxy nos gates).

### 26.L8-6 Bateria v12: `--fit-grad --fit-verts` nas 5 unidades

- Protocolo: autor session:opus, 1 run, `--pair` contra v11-r1 (n02X: v10-r1), fit por gradiente (26.L8-7) e optimize_verts
  soft-30 (26.L8-2, `PIPELINE_SECONDS`). A rede caiu no passe de reparo em 4 unidades; elas foram relançadas com `--spec` do
  próprio spec autorado (pastas `v12-r1-partial` guardadas), n017 saiu de uma vez.
- Resultado: tabela na abertura do §26 e em `history/2026-10-29-v12/README.md`. PASS 2/5 (v11 1/4; meta ≥ 3/5 não atingida).
  Left sobe em 5/5 (+.007 n005, +.077 n00U, +.129 hfoo, +.029 n017, +.071 n02X) e rts em 4/5; custo em front/back de hfoo
  (−.023/−.011) e n017 (−.007) e no top/bottom do hfoo (−.090/−.132). Juiz: v12 vence 3 eixos em n017 e hfoo, perde 3 em n005
  e n02X (o n005 "antes" já era o melhor modelo do projeto; o n02X cai por `shoulder_span` do autor, não pela forma).
- Decisão: `--fit-grad` e `--fit-verts` ficam opt-in. Uma rodada não separa o efeito dos dois nem o ruído do autor; próxima
  tarefa: ablação grad × verts sobre o mesmo spec (sem LLM) nas 5 unidades e, se o top/bottom do hfoo for do fit-grad, pesar
  as vistas top/bottom no `fit_grad` como o `Proxy` já faz.
- Negativo de infraestrutura: 5 processos torch em paralelo (14 núcleos cada) fizeram um passo do optimize_verts levar 227 s e
  1994 s (o orçamento de 30 s é checado entre passos). `soft_sil.THREADS` (env `SOFT_SIL_THREADS`, default 4) limita os threads
  por processo; com 4 processos a rodada ficou em 30–32 s.

### 26.L8-9 Regras de estimativa/medida do sheet não derrubam sozinhas um clay que cobre o sheet (2026-10-29)

**O que mudou.** `preflight.SOFT_RULES = (budget, budget_split, shoulder_span, stance)`; `spec_pipeline.preflight_ok` (usado em
`stage_shape`): o check `preflight` do estágio 1 passa quando o preflight reprova **apenas** regras de `SOFT_RULES` **e** a
silhueta passou (`sil_ok`), o GLB está no gate de tris (`tris`, 400-700 +2 %) e nenhuma vista crítica está acima de
`UNCOVERED_MAX` (`too_red`). Imprime `preflight soft FAIL (...)`. Qualquer outra regra (`bones`, `symmetry`, `joint_place`...)
continua bloqueando; o preflight em si e o loop de repair não mudam (ainda veem o FAIL). Sem flag: para desligar, `SOFT_RULES = ()`.

**Por que não mudei o teto 700 nem as tolerâncias.** O `budget` do preflight é uma *estimativa* (`part_tris`) e o clay é
decimado/construído com orçamento próprio: nos 17 runs v10-v12 o GLB final tem 610-630 tris sempre (n005 v11: estimativa 764,
GLB 630, gate de tris PASS). O teto real é o gate `tris` do GLB, que já existe; a estimativa só serve ao repair. Teto por rig
(L6-10: biped 400, spider/quadruped 250-400, wyrm/drake 700) não foi aplicado: a ablação mediu só silhueta, e baixá-lo reprovaria
mais specs; ficou como recomendação. `shoulder_span`: modelo/sheet em 9 runs de biped = 1,02 / 1,11 / 1,11 / 1,13 / 1,13 / 1,13 /
1,15 / 1,18 / 1,20 (sempre >= 1): a banda 10-30 % do sheet mede estreito (ombro inclinado/capa), a tolerância ±15 % cai na
cauda; alargar sem a silhueta como juiz esconderia o hfoo v11 (1,20), que a silhueta já reprova (left 0,53 < 0,65).

**Levantamento (17 runs `runs/draft/*/v1{0,1,2}-r1`, preflight re-rodado sem LLM, IoU/uncovered do `silhouette.json`).**
Só 3 runs têm FAIL de preflight, todos só em regras soft:

| run | regras FAIL | IoU f/l/b | uncovered f/l | veredito antes | depois |
|---|---|---|---|---|---|
| n005 v11-r1 | budget (764), budget_split (legs 19 % < 20 %) | .909/.935/.905 | .037/.019 | CHECK | PASS (gates cobertos) |
| n02X v12-r1 | shoulder_span (.71 vs .60) | .885/.884/.898 | .029/.054 | CHECK | PASS |
| hfoo v11-r1 | shoulder_span (.55 vs .46), stance (.53 vs .42) | .855/.530/.849 | .083/.311 | CHECK | CHECK (left abaixo do gate, uncovered left > .20) |

Os outros 14 runs não mudam (nenhum FAIL de preflight). 2 de 3 CHECK por preflight viram PASS; nenhum modelo com IoU abaixo do
gate ou vista vermelha passa. Os outros CHECK da lista (hfoo v10/v12, n00H, n00U, n010, n017 v10) são por silhueta, não por
estas regras. Provas: `scratchpad/l8-budget/{survey.py,before.json}`.

**Limites.** A prova é offline sobre os `silhouette.json` já gravados (o `preflight_ok` não foi rodado numa bateria nova); os
verdes de n005 v11 e n02X v12 assumem o mesmo `sil_ok` do run. Teste: `PreflightSoftTest` (8 casos).

### 26.L8-6b Ablação `--fit-grad` × `--fit-verts` (sem LLM, 2026-10-29)

- Protocolo: entrada fixa por unidade = spec **pré-fit** do v12-r1 (`runs/draft/<id>/v12-r1/fit/before.json`; é o spec que entrou no
  `fit_stage`; o `spec.json` final do v12 já vem depois do fit, e refitá-lo contaminaria `none`/`verts`). Câmeras top/bottom/rts do
  `silhouette.json` do v12-r1 semeadas em `sil/approved/`. Comando: `spec_pipeline.py --id <id> --rig <rig> --kind mass --spec <spec>
  --shape-only --no-repair --no-diagnose [--fit-grad] [--fit-verts]`; saída `runs/draft/<id>/l8-abl-{none,grad,verts,both}/`. `none` =
  pipeline default (fit Powell, sem optimize_verts). Autor nunca rodou. 2 processos por vez (`SOFT_SIL_THREADS=4`). Sanidade: `both`
  reproduz o v12 (hfoo .826/.659/.831 vs .832/.659/.838; n00U .857/.780/.861 vs .859/.777/.858). IoU approved, raster duro do review.
  `fit s` = tempo do fit (Powell em `none`/`verts`, Adam em `grad`/`both`, sem os 2 builds reais do `fit_stage`); `verts s` = optimize_verts.
  `fit aceito` = o que `fit_accepted` escolheu (before = fit recusado).

| unidade | cond | front | left | back | top | bottom | rts | sliver % | nd | tris | fit s | verts s | fit aceito |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| n005 | none | 0.895 | 0.928 | 0.897 | 0.752 | 0.773 | 0.857 | 11.6 | 41.2 | 630 | 5 | - | before |
| n005 | grad | 0.895 | 0.928 | 0.897 | 0.752 | 0.773 | 0.857 | 11.6 | 41.2 | 630 | 5 | - | before |
| n005 | verts | 0.910 | 0.941 | 0.914 | 0.770 | 0.821 | 0.876 | 10.0 | 43.5 | 630 | 5 | 31 | before |
| n005 | both | 0.903 | 0.944 | 0.916 | 0.774 | 0.837 | 0.883 | 9.8 | 45.0 | 630 | 5 | 31 | before |
| n00U | none | 0.821 | 0.725 | 0.825 | 0.677 | 0.671 | 0.636 | 22.2 | 49.5 | 630 | 160 | - | after |
| n00U | grad | 0.832 | 0.745 | 0.835 | 0.688 | 0.667 | 0.638 | 19.5 | 48.8 | 625 | 53 | - | after |
| n00U | verts | 0.866 | 0.771 | 0.870 | 0.678 | 0.738 | 0.673 | 20.2 | 51.2 | 630 | 160 | 30 | after |
| n00U | both | 0.857 | 0.780 | 0.861 | 0.731 | 0.693 | 0.682 | 17.8 | 49.7 | 625 | 52 | 30 | after |
| hfoo | none | 0.770 | 0.635 | 0.779 | 0.625 | 0.664 | 0.631 | 22.5 | 49.4 | 630 | 20 | - | cut |
| hfoo | grad | 0.770 | 0.635 | 0.779 | 0.625 | 0.664 | 0.631 | 22.5 | 49.4 | 630 | 22 | - | cut |
| hfoo | verts | 0.826 | 0.659 | 0.831 | 0.695 | 0.739 | 0.644 | 20.8 | 49.5 | 630 | 20 | 30 | cut |
| hfoo | both | 0.826 | 0.659 | 0.831 | 0.695 | 0.739 | 0.644 | 20.8 | 49.5 | 630 | 23 | 30 | cut |
| n017 | none | 0.874 | 0.744 | 0.809 | 0.782 | 0.839 | 0.685 | 29.2 | 47.1 | 630 | 30 | - | after |
| n017 | grad | 0.888 | 0.747 | 0.831 | 0.794 | 0.863 | 0.674 | 33.1 | 48.9 | 622 | 19 | - | before |
| n017 | verts | 0.895 | 0.765 | 0.849 | 0.816 | 0.873 | 0.720 | 25.6 | 51.4 | 630 | 31 | 36 | after |
| n017 | both | 0.895 | 0.770 | 0.844 | 0.811 | 0.892 | 0.703 | 30.9 | 50.4 | 622 | 20 | 32 | before |
| n02X | none | 0.875 | 0.862 | 0.887 | 0.703 | 0.688 | 0.739 | 19.4 | 53.0 | 629 | 5 | - | cut |
| n02X | grad | 0.875 | 0.862 | 0.887 | 0.703 | 0.688 | 0.739 | 19.4 | 53.0 | 629 | 5 | - | cut |
| n02X | verts | 0.885 | 0.885 | 0.899 | 0.750 | 0.735 | 0.781 | 16.9 | 54.5 | 629 | 5 | 30 | cut |
| n02X | both | 0.884 | 0.883 | 0.899 | 0.752 | 0.735 | 0.781 | 16.9 | 54.5 | 629 | 5 | 32 | cut |


Uncovered/spill por vista (f/l/b/top/bottom/rts) em `silhouette.json` de cada run; exemplo hfoo `none` unc .12/.22/.11/.36/.32/.15, `verts`
.08/.20/.07/.28/.23/.11 (spill ±.01); n00U `none` unc .11/.12/.10/.13/.14/.15, `both` .06/.09/.05/.09/.13/.10.

Ruído do `grad`: 2 runs extras (`-r2`) de n00U e n017 (grad e both) dão IoU idênticos ao 3º decimal ao r1 (Adam com seed fixo; só o tempo
varia: n00U 53/59 s, n017 19/25 s). Faixa de IoU = 0 nessas duas.

Deltas vs `none` (milésimos, f/l/b/top/bottom/rts):

| unidade | grad−none (f/l/b/top/bot/rts) | verts−none | both−none |
|---|---|---|---|
| n005 | +0 +0 +0 +0 +0 +0 | +15 +12 +17 +18 +48 +19 | +7 +16 +18 +22 +64 +26 |
| n00U | +10 +20 +10 +11 -4 +2 | +45 +46 +45 +2 +67 +38 | +36 +56 +36 +54 +21 +46 |
| hfoo | +0 +0 +0 +0 +0 +0 | +56 +24 +51 +70 +75 +12 | +56 +24 +51 +70 +75 +12 |
| n017 | +14 +3 +22 +11 +24 -11 | +21 +21 +39 +33 +34 +35 | +21 +26 +34 +29 +53 +18 |
| n02X | +0 +0 +0 +0 +0 +0 | +10 +23 +12 +48 +46 +41 | +9 +21 +12 +49 +47 +42 |

- (a) Quem dá o ganho do left e do rts: **`--fit-verts`**. Left +.012/+.046/+.024/+.021/+.023 e rts +.019/+.038/+.012/+.035/+.041 nas 5
  unidades, e também f/b/top/bottom (+.01..+.07) em 5/5; `both` ≈ `verts` (n005, hfoo, n02X ±.01; n00U left .780 vs .771, top .731 vs .678
  mas bottom .693 vs .738). `--fit-grad` sozinho: efeito nulo em n005, hfoo e n02X (o fit não muda nada; hfoo: 60 passos, 20 reverts, sem
  ponto aceito; igual ao Powell, que também não muda), +.01/+.02 em n00U (3x mais rápido que o Powell, 53 vs 160 s) e em n017 o fit é
  recusado por `fit_accepted` (volta ao spec original, +.014/+.003/+.022 vs o Powell aceito que piora o clay final; rts −.011).
- (b) Perda de top/bottom do hfoo e de front/back do hfoo/n017 **não vem de nenhum flag**. `none` já está em top .625 / bottom .664
  (v11: .777/.862) e front .770 (v11 .855): vem do spec autorado do v12 (reparo/autor), não do fit nem do optimize_verts. Os dois flags
  só melhoram o hfoo contra `none` (verts +.070/+.075 em top/bottom, +.056/+.051 em front/back). Logo a correção do top/bottom em
  `fit_grad.py` não se aplica: nem é causa, e as 6 vistas já entram na perda do Adam com `proxy.weight` (`VIEW_WEIGHTS`, biped rts 1.5).
  Nada foi mudado em `fit_grad.py`.
- Custos de `--fit-verts`: +30 s por unidade; `normal_diff` sobe +0.2..+2.3 (n005 41.2 -> 43.5; n02X 53.0 -> 54.5; `both` n005 45.1);
  slivers caem (-1.4..-3.6 pt) exceto n017 `both` (30.9 vs 29.2 `none`; `grad` sozinho 33.1, tris 622 vs 630).
- (c) Recomendação (não aplicada no código; um spec por unidade, sem ruído de autor): **`--fit-verts` ligar por default** (todos os
  rigs: biped n005/hfoo/n02X, spider n00U, quadruped n017; 5/5 ganham em 6/6 vistas); custo: 30 s e `normal_diff` +1..2 (L8-4 não
  resolveu). **`--fit-grad` manter opt-in**; só vale por rig em spider (n00U: +.01..+.02, 3x mais rápido; 1 unidade) e não muda nada
  em biped (3 unidades, nula) nem ajuda em quadruped (recusado). Para decidir o default do grad falta mais de uma unidade spider/quadruped.
- Negativos/limites: 1 spec por unidade (sem variação de autor); a aranha e o quadruped têm 1 unidade cada; o Powell `none` em n017
  piora o clay final (fit aceito mas pior depois da deformação), o que torna n017 `grad` (fit recusado) "melhor" por pular o fit.
- Sem mudança de código: sem testes novos nem ruff. Compares em `history/2026-10-29-l8-abl/<id>.png`.

## 27. Leva 9 (2026-10-29)

Textura: atlas compacto, paleta partilhada, um material (papers/tutoriais de atlas e packing em
`analysis/2026-10-29-papers-atlas.md`). Forma não muda. Resultado por item:

| item | antes | depois | default |
|---|---|---|---|
| T1 atlas cel compacto (shelf FFD, slots 2 px) | 768² / 84 KB (n005), 7 materiais | ≤ 128² / ≤ 6.5 KB nas 5; `luma_l1` ±.008, `zones` −.011 pior caso | **sim** (`COMPACT_ATLAS`, `--atlas legacy`) |
| T6 mip-safe (`mesh_lint.mip_bleed`) | — | 0 texels mistos até 1/4 nas 5 | relatório |
| T2 fusão por ΔE Oklab no atlas partilhado | Human 13 colunas | 12 colunas (fusão rende 1) | sem flag; `--atlas shared` opt-in |
| T4 espelho L/R | — | gêmeos já partilham célula e tom; `uv_overlap_mirror_pct` 2–3 % | relatório |
| T5 um material por unidade (`merge_materials`) | 7–8 prims | 1–2 prims (flame emissivo separado); render igual | **sim** (`--materials split`) |
| T3+T7 atlas partilhado 128² com decais + paleta por raça | sem decais/ink (L6-11 perdia 4-0) | juiz 4-0 pró shared em 3/5, empates nos outros; 10–16 unidades/raça; imagem única por raça ainda não gerada | opt-in (`--atlas shared`, `palette_snap`) |

Pendente de outra leva: sidecar PNG único por raça (engine precisa de bind partilhado) e quantizar `WEIGHTS_0` (25 KB, maior bloco do GLB depois do T1).

### 27.T2 Paleta mínima partilhada por raça (2026-10-29)

Fontes: Saved Pixel (workflow de paleta), Halladay 2016 (atlas com mips: padding >= 2^níveis). `shared_atlas.py` (`--atlas shared`, §24.L6-11):
- `MERGE_DE = 0.02`: `find(table, key)` devolve a coluna exata, senão a mais próxima em Oklab (`silhouette.oklab`) da MESMA superfície com
  ΔE < 0.02, senão None. `extend` só anexa chave sem coluna (append-only mantido: coluna nunca move; tabela JSON antiga, lista de chaves, carrega igual).
  `build_unit.texturize_shared` mapeia material -> `find(table, key)` (antes `table.index`).
- Coluna de `COL = 2` px (os dois texels iguais; `u_of(i)` = costura entre eles, mip-safe um nível acima): 32 colunas em 64² (antes 64 de 1 px).
  Estourou 32: ValueError, a unidade volta ao atlas próprio (como antes).
- Default continua `--atlas own`; nada de flag nova.

Capacidade (specs `runs/draft/*/v12-r1`, raça do compendium; script em scratchpad, `shared_atlas.key`/`find`):

| raça | unidades | slots (soma) | colunas sem fusão | com fusão ΔE<0.02 | unidades em 64² (32 col) |
|---|---|---|---|---|---|
| Human | hfoo + n005 | 13 | 13 | 12 | ~5 (6 col/unidade) |
| Nature | n00U | 5 | 5 | 5 | ~6 |
| Northern | n017 | 4 | 4 | 4 | ~8 |
| Desert | n02X | 6 | 6 | 6 | ~5 |

Sensibilidade (hfoo+n005 / as 5 unidades juntas, 28 slots): ΔE .02 -> 12 / 27; .03 -> 12 / 26; .05 -> 11 / 24; .08 -> 11 / 23; .12 -> 7 / 17.
Render (Blender, `build_unit shared=`, 630 faces, cor da textura no centro de UV de cada face, antes x depois): hfoo 0 faces diferentes; n005
21 faces diferentes (`z3` #232324 fundiu com `belt` #292725, ΔE .019), delta máximo 6/255. `luma_l1`/zones não remedidos (delta de cor <= 6/255 em 3 %
das faces).
- NEGATIVO no aceite: Human 12 -> 12 colunas reais (13 -> 12), não <= 9, e 64² cabe ~5-8 unidades por raça, não >= 16. As paletas
  autoradas diferem em mais que ΔE .02 (mesma superfície, cores distintas de propósito); só ΔE ~.12 chega a 7 colunas, mas isso muda a cor
  visivelmente. Para >= 16 unidades: 128² (64 colunas de 2 px, ~10 unidades) ou paleta fixa por raça imposta ao autor (cor do slot escolhida
  da paleta da raça, não livre) - não feito.

### 27.T4 Espelho L/R: o symmetric overlap já está feito (Knodt & Gao, TOG 2025)

Prova, sem mudar UV/células. Knodt & Gao sobrepõem charts espelhados no atlas (a metade espelhada reusa os mesmos texels) e cortam
texels vazios. Aqui: em `build_unit.atlas_uvs` a célula de cada face em cel NÃO vem do osso (`TEX_SLOTS` só vale para
`painted`): é `tone_index(normal.z)` e o slot de rampa (`ramp_slot`) sai de normal + altura relativa na peça; o bloco é o do
material. Peças `.L/.R` são gêmeas do spec (mesmo material, geometria espelhada, normal.z igual) → caem na mesma célula, no mesmo
tom, logo no mesmo texel. Em `painted`, `TEX_SLOTS` mapeia explicitamente `arm/forearm/thigh/shin/foot.L/.R` → mesmo slot (3..7).
- `mesh_lint.uv_report` ganha `uv_overlap_mirror_pct` (só relatório, sem gate; `tri_bones` = osso dominante por triângulo pelo
  skin; `mirror_overlap_pct`): % dos pixels cobertos cuja sobreposição some ao tratar `.L` e `.R` como uma camada só. `None`
  sem skin.
- Medição (raster 1024, v12-r1; hfoo e n00U re-texturizados com `build_unit.py ... tex style=cel` sobre o `spec.json`, pois o
  v12-r1 só tem clay):

| unidade | atlas | tris L / R / outros | `uv_overlap_pct` | `uv_overlap_mirror_pct` | pixels cobertos por L **e** R | pares gêmeos com célula+tom iguais |
|---|---|---|---|---|---|---|
| n005 | 768² | 122 / 110 / 398 | 64.7 | 2.1 | 25.3 % | arm, foot, shin 100 %; forearm 50 % |
| hfoo | 768² | 124 / 156 / 350 | 74.7 | 2.7 | 35.6 % | arm, foot, shin, thigh 100 %; forearm 45 % |
| n00U (spider) | 768×512 | 0 / 0 / 625 | 80.8 | 0.0 | n/a (sem `.L/.R`) | n/a |
| n017 (quadruped) | 512² | 0 / 0 / 626 | 81.2 | 0.0 | n/a (sem `.L/.R`) | n/a |

- Conclusão: **já feito.** Os gêmeos partilham célula, tom e texel (25-36 % dos pixels cobertos recebem L e R). Mas o espelho é
  a menor parte da sobreposição: 64-81 % dos pixels cobertos têm 2+ triângulos porque o cel já é "1 texel por tom" — toda face
  do mesmo material, tom e rampa cai no mesmo slot, de qualquer osso, inclusive no mesmo lado. Por isso `mirror_pct` (só o que
  é explicado pelos gêmeos) fica em 2-3 %: sobreposição "não simétrica" ≈ 97 %, por projeto e esperada. O carving de Knodt & Gao
  ("1 texel por tom", cortar texels vazios) é o que T1 faz (slot de rampa 2 px); nada a fazer em T4.
- Gêmeos que NÃO partilham célula/tom (não corrigidos; T1/T2 mexem no atlas): só `forearm.L/.R` em n005 e hfoo, por conteúdo
  assimétrico legítimo, não por mapeamento: o prop na mão (n005 `prop_vaporiser` na `forearm.L`; hfoo `steel`/
  `prop_trench_pike` na `forearm.R`) é skinado no antebraço e usa material/bloco próprio. O corpo (`z1/z2/z3`, `tunic`, `skin`...)
  do antebraço é idêntico dos dois lados. n00U e n017 (spider/quadruped, ossos `leg1..4`) não têm gêmeos `.L/.R`: o mesmo
  ganho vem do compartilhamento por tom, não de espelho.
- Testes: `test_mesh_lint.MirrorOverlap` (gêmeos sintéticos 100 %, mesmo lado 0 %, sem skin `None`, `TEX_SLOTS` com `.L/.R` no
  mesmo slot, lido do fonte porque `build_unit` importa `bpy`). Sem flag nem default novos.

Textura: atlas compacto, paleta partilhada, 1 material (`analysis/2026-10-29-papers-atlas.md`, ROADMAP-papers.md "Leva 9").

### 27.T1 Atlas cel compacto (`--atlas compact`, `build_unit.COMPACT_ATLAS`)

**Decisão do integrador (2026-10-29):** `COMPACT_ATLAS = True` por default (16× menor; `luma_l1` ±.008 e `zones mean` −.011 no pior caso são ruído para o alvo alpha; forma não muda). `--atlas legacy` mantém o antigo.

- O que mudou: `texturize` ganhou o caminho `texturize_compact` (só `style=cel`, atlas próprio). Cada (material, tom usado) ganha uma
  célula de tom `surfaces.tone_cell` de 16 px de largura: 1 coluna de ink por lado (a face começa 0.65 px dentro,
  `INK_EDGE_PX`, então o ink aparece em ~2.3 % dela, como na célula de 256 px) e **4 linhas** (1 de ink + 3 de cor) quando a rampa é
  plana (`slope == 0` ou `glow`, o caso padrão: `RAMP_SLOPE = 0`); com rampa medida (`--ramp`, `ramp=`) a célula tem os 8 slots de
  **2 px** (a linha de baixo de cada slot é o ink, a face amostra só a de cima, `face_row`). Decal procedural (olhos): célula de
  16 px; decal de figura (`sheet`, `propcrop`): 32 px (a 16 vira mancha; era 64). Só entram as células usadas. `surfaces.pack_cells`
  (shelf first-fit-decreasing, origens e tamanhos múltiplos de `align` = 4, `pad` opcional) devolve a imagem POT mínima, retangular
  (64x128, 128x128...). Os UVs são recalculados pelo layout (`compact_uvs`); nenhum vértice se move. A base de uma célula de decal é
  a célula de tom do meio repetida (ink a cada 4ª linha, como a célula de decal de 256 px antiga). O paint dos decais é arredondado
  a 16 níveis por canal (`POSTERIZE = 15`): sem isso a figura do decal é o PNG inteiro (n005 8.1 KB, hfoo 8.6 KB; com: 5.2, 6.5).
  Um decal que passava da caixa da peça é preso à célula (`du, dv` em 0..1): o antigo vazava para a célula vizinha.
- Flags: `--atlas compact|legacy` (`own` = o que `COMPACT_ATLAS` diz), no build `cel_atlas=compact|legacy`. **Default
  continua legado (`COMPACT_ATLAS = False`)**: o aceite de fidelidade não passou ao pé da letra (abaixo).
- Bateria (estágio 2 cel sobre o spec do v12-r1, `deform`/`fit-verts` desligados nos dois braços para o mesmo clay; compare
  f/l/b; `luma_l1` menor é melhor):

| unit | atlas | size | KB | luma_l1 f/l/b | zones mean f/l/b | uv_overlap % | oob | images |
|---|---|---|---|---|---|---|---|---|
| n005 | legacy | 768x768 | 83.9 | 0.053/0.035/0.034 | 0.618/0.692/0.608 | 64.7 | 0 | 1 |
| n005 | compact | 128x128 | 5.2 | 0.041/0.039/0.024 | 0.616/0.681/0.611 | 2.2 | 0 | 1 |
| n017 | legacy | 512x512 | 55.5 | 0.137/0.044/0.069 | 0.143/0.221/0.241 | 81.2 | 0 | 1 |
| n017 | compact | 32x128 | 3.5 | 0.104/0.044/0.076 | 0.140/0.214/0.241 | 0.0 | 0 | 1 |
| hfoo | legacy | 768x768 | 94.6 | 0.090/0.073/0.118 | 0.267/0.240/0.176 | 68.6 | 0 | 1 |
| hfoo | compact | 128x128 | 6.5 | 0.089/0.047/0.098 | 0.267/0.241/0.178 | 0.1 | 0 | 1 |
| n00U | legacy | 768x512 | 13.8 | 0.034/0.045/0.049 | 0.310/0.240/0.292 | 80.8 | 1 | 1 |
| n00U | compact | 32x64 | 0.7 | 0.036/0.045/0.049 | 0.315/0.238/0.291 | 66.6 | 0 | 1 |
| n02X | legacy | 768x768 | 62.9 | 0.038/0.052/0.035 | 0.337/0.234/0.291 | 74.7 | 0 | 1 |
| n02X | compact | 64x128 | 4.1 | 0.034/0.052/0.036 | 0.341/0.237/0.289 | 0.0 | 0 | 1 |

- Aceite: imagem ≤ 128² (5/5, de 768² a 512²), `atlas_kb` ≤ 8 (5/5: 3.5 .. 6.5; n005 83.9 → 5.2), `uv_out_of_range == 0` (5/5; o n00U
  legado tinha 1), `images == 1`. `zones mean`: pior queda -0.011 (n005 left .692 → .681), as outras ≥ -0.007. `luma_l1` por vista
  fica em ±0.003 em 7 das 15 células; 6 melhoram (n005 f/b, n017 f, hfoo l/b, n02X f; até -.033) e 2 pioram (n005 left +.004, n017 back +.007): vem
  da resolução do decal de figura (32 contra 64 px) e do posterize, não do ink. Por isso o default NÃO virou compacto; virar é
  `COMPACT_ATLAS = True` e `own` passa a compacto (`legacy` fica opt-in).
- `uv_overlap_pct` não é comparável: `mesh_lint.cover_map` usa a grade 4x4 de blocos de 256 px para excluir as células de decal; no
  atlas compacto essa exclusão cai em células quaisquer (T4 reescreve a medida).
- Render pixel-comparado (mesma câmera, 512², n005 front/left, n00U front/top, n02X front): 1.3-2 % dos pixels diferem > 8/255 e
  0.1-0.3 % > 40; diferenças em cantos de face (ink agora só nas colunas laterais da célula; a linha de cima/baixo da face sumiu:
  ela caía no slot de 8 linhas, agora o slot é só de cor) e no decal de figura (32 px). Olhos do n005 legíveis (vermelhos, no compare).
- Negativos: decal de figura dividido entre materiais (um por material que o veste, o fundo transparente mostra a cor do material:
  dividir entre materiais trocou a cor da mochila do hfoo); 16 px para figura (borrado); compressão PNG 100 do Blender não muda o
  tamanho (o exportador não a usa).
- Evidência: `scratchpad/l9-atlas/` (run.py, table.py, cmp-*.png, `<unit>-{legacy,compact}/`).

### 27.T3 Decais no atlas partilhado, 128² (`--atlas shared`, `shared_atlas.py`, `build_unit.texturize_shared`)

- O que mudou: `shared_atlas.SIZE = 128` (T7), 64 colunas de 2 px. **Faixa inferior** (`TONE_ROWS = 12`): por coluna (cor + superfície) as 3
  células de tom planas de `surfaces.tone_cell` (4 linhas: 1 de ink + 3 de cor; claro / médio / escuro), cortadas a 2 px (`width=4`,
  colunas do meio): o ink é só a linha (as colunas laterais de ink não cabem em 2 px). **Faixa superior**: células de decal (16 px procedural,
  32 px figura/prop crop) na grade de 4 px, **first-fit** sobre as células já na tabela. Tabela JSON `{"columns": [...], "decals": {hash:
  [x, y, w, h]}}` (a lista de chaves antiga carrega igual), append-only: coluna e célula nunca se movem. Chave do decal =
  sha1 curto de (tipo, fonte, tamanho, chave da coluna) (`decal_hash`); a fonte de figura é o pixel do rosto / o crop do prop. Duas unidades
  da raça com o mesmo decal sobre a mesma coluna partilham a célula.
- Reuso: `compact_faces` / `compact_uvs` / `paint_compact` / `paint_decal` do T1 (UV e pintura do decal iguais ao compacto, nada duplicado); a
  rampa (`shared_uvs`, RAMP) saiu: era negativa (L6-11) e o tom plano é o do compacto. **Não usa `pack_cells`**: ele reempacota tudo
  (origens mudam quando uma célula entra), e a tabela é append-only; `place` é o first-fit de grade que não move nada.
- Célula de figura usada por < 3 faces (`SHARED_PICTURE_FACES`) e que não é o crop do próprio prop (`prop_*`) vira 16 px: 11 células de 32
  não cabem na faixa (12 de 32 por 116 linhas) com as duas unidades Human; sem a exceção do prop o juiz perdeu a pistola do n005 (4-0 sheet).
  O decal pintado é posterizado depois do blend (`POSTERIZE`): o PNG cai de 6.8 para 4.5 KB (união Human).
- Só a imagem DE CADA GLB carrega os decais da própria unidade; a tabela reserva as células das outras (a imagem da raça inteira é a união, `min`
  das imagens, sem sidecar: **não feito**, adicionar quando o motor carregar uma imagem por raça, T5).
- Flags: `--atlas shared` continua opt-in (`build_unit shared=<raça>.json`); `palette_snap` no build (T7, desligado).
- Bateria (`runs/draft/*/v12-r1/spec.json`, estágio 2 cel, `deform`/`fit-verts` desligados; Human: n005 depois hfoo na mesma tabela; compacto =
  T1 default, mesmo clay; `luma_l1` menor é melhor):

| unit | atlas | size | KB | luma_l1 f/l/b | zones mean f/l/b | oob | images |
|---|---|---|---|---|---|---|---|
| n005 | compacto | 128x128 | 5.2 | 0.041/0.039/0.024 | 0.616/0.681/0.611 | 0 | 1 |
| n005 | shared | 128x128 | 3.6 | 0.044/0.039/0.021 | 0.617/0.682/0.611 | 0 | 1 |
| hfoo | compacto | 128x128 | 6.5 | 0.089/0.047/0.098 | 0.267/0.241/0.178 | 0 | 1 |
| hfoo | shared | 128x128 | 4.3 | 0.056/0.047/0.098 | 0.276/0.244/0.177 | 0 | 1 |
| n00U | compacto | 32x64 | 0.7 | 0.036/0.045/0.049 | 0.315/0.238/0.291 | 0 | 1 |
| n00U | shared | 128x128 | 1.1 | 0.036/0.045/0.049 | 0.316/0.239/0.289 | 0 | 1 |
| n017 | compacto | 32x128 | 3.5 | 0.104/0.044/0.076 | 0.140/0.214/0.241 | 0 | 1 |
| n017 | shared | 128x128 | 2.9 | 0.105/0.050/0.084 | 0.142/0.214/0.240 | 0 | 1 |
| n02X | compacto | 64x128 | 4.1 | 0.034/0.052/0.036 | 0.341/0.237/0.289 | 0 | 1 |
| n02X | shared | 128x128 | 3.0 | 0.038/0.054/0.036 | 0.346/0.235/0.289 | 0 | 1 |

- Aceite: `images == 1` (5/5), `uv_out_of_range == 0` (5/5), imagem 128² (5/5; n00U/n017/n02X são maiores que o compacto, mas a imagem é a da raça).
  `luma_l1` ±.008: 14 de 15 (n005 f +.003, hfoo f −.034 melhora, n017 l/b +.006/+.007; n02X f +.004); `zones mean` (média de f/l/b) de −.0001 a
  +.0037, nunca perde .011. KB por GLB 1.1..4.3 (Blender codifica ~1.2x o PIL). **NÃO atendido**: ≤ 4 KB por raça no Human (união das duas
  unidades = 5.0 KB com PIL, ~6 KB no Blender: as imagens de figura pesam); Desert/Nature/Northern (1 unidade) ficam em 1.1..3.0 KB.
- Juiz `review_pair` (4 votos, A = compacto, B = shared; `scratchpad/l9-decals/pair/`), 3ª rodada, sem rampa nem snap:
  n005 sheet/artist/wc3 empate 2-2 (viés de posição), form B 3-1; hfoo B 4-0 nos 4 eixos; n00U B 4-0; n017 B 4-0; n02X empate 2-2. **Nenhuma
  perda de 4-0 no eixo sheet** (o ink só em linha lê mais limpo para o juiz: "carapaça lisa" contra "lajes sobrepostas" no n00U).
  Rodadas anteriores (negativos): (1) com `palette_snap` ligado o hfoo perdeu o eixo sheet 4-0 (botas cinza escuro viraram o verde escuro da paleta
  Human, ΔE < .03 mas visível ao juiz); (2) com a célula de 1 face do prop da pistola a 16 px o n005 perdeu o eixo sheet 4-0 (pistola esverdeada).
- Testes: `test_shared_atlas` (tabela com `decals` carrega/anexa sem mover, hash igual partilha célula, `place` sem sobreposição e banda cheia
  recusa, 64 colunas, imagem = células do compacto sem ink lateral); `test_colour_stage.RaceHint`.
- Evidência: `scratchpad/l9-decals/` (`run.py`, `table.py`, `sim.py`, `pair/`, `atlas/*.json`).

### 27.T7 Paleta por raça (`race_palettes.json`, `shared_atlas.palette_hint/snap/snap_new`)

- `race_palettes.json`: 15 raças, as 8 cores mais frequentes (quantizadas a 5 bits, > ΔE .06 entre si, Oklab) do ícone `assets/icons/png/race/<raça>.png`
  (`shared_atlas.make_palettes`, PIL). `palette_hint(race)` devolve a lista (`[]` para raça desconhecida); `hint_text(race)` é a frase do brief.
- Brief do estágio de cor (`colour_stage.colour_brief(spec, scores, race)`): só com `--atlas shared`, a linha "Prefer these <raça> palette tones when
  the sheet allows (soft, not a rule): ..." antes de "Parts with a decal"; o autor pode ignorar, nada bloqueia. Sem `--atlas shared` o brief é o mesmo de antes.
- Snap: `snap(k, palette)` troca a cor da chave pela da paleta se ΔE < `SNAP_DE = 0.03`; `snap_new(columns, k, palette)` só se nenhuma coluna
  já serve a chave (a fusão T2 ganha). No build é `palette_snap` (argumento, `PALETTE_SNAP = False`): **desligado**.
- Simulação de capacidade (`scratchpad/l9-decals/sim.py`; specs v12-r1, v11-r1 onde faltou; n01X/n00H só têm spec v10-r1 com palette): colunas
  da raça somando as unidades, e unidades por 128² = 64 x unidades / colunas:

| raça | unidades | slots | sem fusão | fusão ΔE .02 (T2) | + snap ΔE .03 (T7) | snap de tudo (limite) | unidades em 128² (T2 / T7 / limite) |
|---|---|---|---|---|---|---|---|
| Human | hfoo, n005 | 13 | 13 | 12 | 13 | 9 | 10 / 9 / 14 |
| Nature | n00U | 5 | 5 | 5 | 5 | 4 | 12 / 12 / 16 |
| Northern | n017 | 4 | 4 | 4 | 4 | 4 | 16 / 16 / 16 |
| Desert | n02X | 6 | 6 | 6 | 6 | 6 | 10 / 10 / 10 |
| Mech | n01X (v10-r1) | 5 | 5 | 5 | 5 | 5 | 12 / 12 / 12 |
| Naga | n00H (v10-r1) | 5 | 5 | 5 | 5 | 4 | 12 / 12 / 16 |

- NEGATIVO no aceite "≥ 16 unidades/raça": 10-16 unidades por raça em 128² (≥ 16 só no Northern, 1 unidade, e no "limite" de Nature/Naga). O snap
  ΔE < .03 move 0-3 slots por raça (Human 3 de 13, Nature 1, Naga 2) e não junta colunas (Human 12 -> 13: o slot que a fusão T2 juntava foi para a
  paleta); as cores autoradas (escuras, sujas) ficam longe das do ícone (vivas, com contorno). Só a paleta imposta ao autor (limite: tudo
  no snap, ΔE livre) chega a 9 colunas Human (14 unidades) - sem medida de fidelidade e depende do autor seguir a dica, que é suave.
- `zones mean` (T3, snap desligado) nunca cai > .004 nas 5 unidades; com o snap ligado (rodada 1) caiu ≤ .004 também, mas o juiz viu a cor trocada (acima).
- Recomendação (`--atlas shared`, decisão de default é do integrador): manter opt-in. 128² com decais fecha o aceite visual (sheet sem 4-0 contra, KB por GLB ≤ 4.3,
  1 imagem), não fecha 4 KB por raça (Human) nem ≥ 16 unidades/raça; a imagem da raça só ganha quando o motor carregar UMA imagem por raça (T5, `merge_materials`).
  Quem ligar a dica de paleta ao autor deve medir a cor do slot depois (não medido: sem LLM nesta tarefa).

### 27.T6 `mesh_lint.mip_bleed` (medida mip-safe, só relatório)

- `mip_bleed(image, layout)`: mapa de id de célula por pixel (`layout` = retângulos `(x, y, w, h)`), blocos 2x2 / 4x4 / 8x8
  (box filter 1/2, 1/4, 1/8) e contagem dos blocos com ≥ 2 células distintas. Pixels fora de qualquer célula (padding) não
  misturam com nada. Chaves `"1/2" "1/4" "1/8"`. `build_unit` imprime o relatório (`compact atlas: ... mixed texels ...`) e
  `pack_cells(align=, pad=)` garante células alinhadas; o motor não usa mips hoje (`ModelCook.BuildMaterial` mipmaps=1).
- Aceite: 0 texels mistos em 1/2 e 1/4 nas 5 unidades (alinhamento 4, sem padding); em 1/8 sobram 12-20 (as células planas têm 4
  linhas: 1/8 mistura vertical é inevitável sem padding; `pack_cells(align=8, pad=2)` zera, ao custo de área). Teste: atlas sintético
  fora da grade mistura, com padding de 2 px não.

## 28. Leva 10 (2026-10-29)

Plano: `analysis/2026-10-29-leva10-sdf.md`. CSG → SDF → malha → retopologia guardada. Bateria `v13-r1` (5 unidades, autor
session:opus, `--body sdf`, pareada contra v12) em `history/2026-10-29-v13/`; controle no mesmo spec em `v13-r1-union`; detalhe
em 28.L10-9. IoU approved f/l/b · rts; slivers e nd do clay final.

| unidade | v12 (união) | v13 (sdf) | veredito | slivers | nd | juiz v13 × v12 (forma) |
|---|---|---|---|---|---|---|
| n005 | .909/.942/.917 · .882 | .921/.947/.932 · .878 | **PASS** | 9.0 → 4.3 % | 44.7 → 35.7° | 3-1 |
| n00U | .859/.777/.858 · .683 | .886/.782/.885 · .665 | CHECK (rts, bottom, comp 2 do spec) | 16.0 → 0.9 % | 50.3 → 45.3° | 4-0 |
| hfoo | .832/.659/.838 · .645 | .847/.415/.853 · .703 | CHECK (left: spec do autor, união .417) | 21.1 → 5.4 % | 49.4 → 37.9° | 4-0 |
| n017 | .875/.775/.834 · .692 | .924/.775/.870 · .700 | **PASS** | 32.4 → 4.9 % | 50.5 → 34.3° | 4-0 |
| n02X | .885/.884/.898 · .784 | .907/.837/.918 · .805 | **PASS** | 17.0 → 4.4 % | 54.9 → 39.7° | 4-0 |

Resultado da leva: `BODY = "sdf"` default; `--body union` opcional. Itens L10-1…L10-9 abaixo.

### 28.L10-1 `sdf_body.py`: o campo de distância do corpo (numpy puro)
- **O que mudou.** `tools/blender/sdf_body.py` (novo): `field(parts, cuts, rig, k, grid, owner)` devolve um `Field` com `grid`
  float32 (nx, ny, nz), `origin`, `voxel`, `owner` opcional (int16, índice da peça mais próxima), `d(points)` (campo exato em
  pontos), `ownership(points)` → (peça mais próxima, menor d, 2º menor d) para a mistura de pesos de L10-5, e `to_json` /
  `load` (`clay.sdf.json`: peças normalizadas + pares + k + grade, para o `mesh_lint` recomputar em python3.14).
  `tools/blender/part_geom.py` (novo): a geometria numpy-pura de uma peça (`local_shape`, `part_points`, `placed`, `rings_of`...)
  que estava em `fit_spec.py`, movida porque o Python do Blender não tem scipy nem PIL (o `fit_spec` re-exporta os nomes; 394
  peças das 17 specs dão pontos idênticos antes/depois).
- **Eixos e valor.** Eixos do Blender (x, y = −frente, z cima), metros. O valor é cota inferior da distância euclidiana, exata na
  superfície, truncada em `margin = max(4 voxels, 2 k)` fora do corpo; dentro é o `max` dos planos.
- **Por kind.** convexo (box, prism, frustum, cyl, dome, plate convexo) = `max_j(n_j·p + b_j)` dos planos do casco (scipy
  `ConvexHull` se existir, senão casco por força bruta O(n⁴) em blocos; os dois dão o mesmo campo, testado); lathe (raios ou
  anéis, `axis z`), limb, chain = pilha de cascos entre anéis consecutivos, `min` duro (o lathe escalar fica facetado como a malha,
  não revolução suave: 8-gon continua 8-gon, e squash/corner saem exatos); plate côncavo (asas: 9 dos 12 plates das 17 specs) =
  triangulação por orelhas, um casco por triângulo e par de anéis (o casco único enchia a concavidade, d = −0.007 num vértice);
  wheel = torus; ring = anulus + raios e cubo como cascos; `cut: sheet` = `max(peça, prisma front, prisma left, prisma top)` com
  polígono 2D côncavo (a peça é o prisma front quando não é lathe); kind desconhecido = casco de `part_points` (`exact: false`).
  Props (`opts.prop`) e material `flame` ficam fora.
- **União.** `smin` polinomial (Quilez) só entre peças cujos ossos são o mesmo ou pai/filho (`rig_families.parents`; o
  `CHAIN_OF` do `build_unit` não é importável sem bpy e é coberto pelos pais); `k = K_FRAC (0.25) × min(raio_a, raio_b)` com
  `raio` = profundidade interna da peça, preso a [0.5 voxel, 0.03 H], × `--k`; `--k 0` = união dura. O resto é `min` duro. O campo
  é `min(todas as peças, smin dos pares ligados)`.
- **Grade.** bbox do corpo + 3 voxels, voxel cúbico `H/N`, N = 96 (64 e 128 por `--grid`). Cada peça só é avaliada na sua laje
  (bbox + margem), os pares onde as lajes se cruzam.
- **CLI.** `python3.14 tools/blender/sdf_body.py spec.json --grid 96 --out campo.npy --json clay.sdf.json [--cuts cuts.json]
  [--k 1.0] [--owner]`; imprime peças por kind, peças de fallback, nº de pares e tempo. Também importa e roda no Python do Blender
  5.2 (3.13, sem scipy): hfoo 96³ em 0.16 s lá.
- **Medida (M4 Pro, numpy, v12-r1 com `fit/cuts.json`, melhor de 3; peças do corpo / peças convexas / pares smin).**

| unidade | rig | peças | cascos | pares | 64³ | 96³ | 128³ | fallback |
|---|---|---|---|---|---|---|---|---|
| n005 | biped | 16 | 26 | 23 | 0.019 s | 0.040 s | 0.084 s | 0 |
| n00U | spider | 35 | 39 | 296 | 0.040 s | 0.079 s | 0.168 s | 0 |
| hfoo | biped | 15 | 25 | 18 | 0.073 s | 0.161 s | 0.322 s | 0 |
| n017 | quadruped | 17 | 28 | 31 | 0.035 s | 0.095 s | 0.208 s | 0 |
| n02X | biped | 16 | 26 | 22 | 0.160 s | 0.388 s | 0.885 s | 0 |

  Por kind nas 5 unidades: frustum 37, prism 34, lathe 13, limb 10, box 3, chain 1, plate 1; nenhum fallback. O n00U passa de
  1.5 s de folga: 96³ em 0.08 s (o plano estimava 0.6 s com 20 primitivas; as lajes por peça explicam). Torch não implementado
  (não instalado; `--device torch` só quando a grade 128³ pesar: o pior caso é 0.9 s).
- **Paridade.** Todo vértice emitido tem |d| ≤ 1e-6 (pior 1.7e-7 sem scipy, arredondamento dos planos em 1e-8) nos 14 casos
  sintéticos (box, prism, frustum, cyl, dome, ring, wheel, lathe escalar, lathe de anéis `axis z`, limb com knee, chain, plate com
  bevel, plate côncavo, cut) e nas 17 specs (`SLOW=1`), e o centróide tem d < 0 (menos ring/wheel, cujo centro é o furo). Raios e
  cubo do ring: só `d ≤ 1e-6` (os cantos ficam dentro da parede). Render rápido do nível zero (openvdb `convertToPolygons`
  0.5, só inspeção, não é o L10-2): hfoo fechado e conexo, 3.9 k verts.
- **Negativos / não feito.** Sem torch. `plate` com perfil não-simples (auto-interseção) cai no casco único (não aparece nas
  specs). Pontos longe da peça valem `margin` (não a distância): L10-3 que reprojetar precisa de `Field.d` (exato) e não da grade.
  `inradius` de uma peça cortada usa −d no centro da caixa. Sem ligação ao `build_unit` (L10-2).
- **Testes.** `tests/tools/blender/test_sdf_body.py` (paridade por kind, fallback, props/flame, casco bruto × qhull, smin
  pai/filho × duro, `k` preso, `k = 0`, grade × exato e JSON ida e volta; `SLOW=1`: 17 specs e 96³ do n00U ≤ 1.5 s).

### 28.L10-6 `mesh_lint`: forma contra o SDF do próprio spec (relatório, 2026-10-29)

Plano `analysis/2026-10-29-leva10-sdf.md` §2.7. Nenhum gate novo (`GATES` intacto). Ideia: Chamfer/Hausdorff/non-manifold como relatório (Meshy T2, `docs/references.md`).
- **O que mudou.** `mesh_lint.shape_report(pos, tri, d, voxel)` e `sdf_field(glb)`: o campo vem de `clay.sdf.json` ao lado do GLB; sem ele
  é recomputado de `spec.json` + `fit/cuts.json` (`sdf_body.field`, grade 96, ~0.1-0.4 s; `RF.scale_rig` por spec e `FAMILIES`/`lathe_limb.RIG`
  restaurados); sem nenhum dos dois as métricas do campo ficam `None`. Medidas no corpo soldado (maior componente por nº de faces):
  `sdf_dev` {pct_h, vox} × {mean, p95, max} de |d| em vértices + 10 k pontos uniformes por área (seed 0); `hausdorff_sdf` = máx em % H;
  `normal_consistency` = média de |n_face · ∇d/|∇d|| nos centróides (diferença central, passo 0.25 voxel); `euler` = F − 2V + 4 (0 =
  casca fechada de gênero 0; 4 × gênero em geral) do corpo e `euler_components` de todos; `nd_bands` = % das arestas do corpo a
  0-20 / 20-60 / 60-100 / >100° (alvo "quinas presentes": 60-100° em 10-20 %). `boundary_edges`/`nonmanifold_edges` já existiam (malha inteira).
- **Flags.** `lint(glb, sdf=False)` por padrão (o campo custa ~1 s e `lint` roda nos laços de `form_cost`); `sdf=True` em `review.md ### Forma`
  (`spec_pipeline.sdf_rows`), em `compare_runs` (linha FORM ganha `sdf_dev p95 x%H`) e no CLI (`--no-sdf` desliga). `euler` e `nd_bands`
  saem sempre (não dependem do campo).
- **Baseline numérico (v12-r1, campo do próprio spec, 96³: voxel = H/96; é a régua que L10-3/L10-7 têm de bater).** `clay` = depois de
  deform + verts; `clay-raw` = união booleana crua; `clay-prefit` = antes do fit.

| unidade | GLB | tris | sdf_dev média / p95 / máx (% H) | p95 / máx (voxels) | normal_consistency | euler (corpo) | non-manifold / borda | nd 0-20 / 20-60 / 60-100 / 100+ (%) |
|---|---|---|---|---|---|---|---|---|
| n005 | clay | 630 | 0.783 / 2.376 / 5.081 | 2.273 / 4.86 | 0.8297 | 0 | 0 / 0 | 41.0 / 23.0 / 25.4 / 10.6 |
| n005 | clay-raw | 630 | 0.069 / 0.351 / 0.712 | 0.337 / 0.684 | 0.9815 | 0 | 0 / 0 | 48.4 / 18.1 / 30.6 / 2.9 |
| n005 | clay-prefit | 630 | 0.659 / 1.863 / 3.866 | 1.769 / 3.672 | 0.8631 | 0 | 0 / 0 | 43.2 / 24.7 / 23.3 / 8.8 |
| n00U | clay | 625 | 1.13 / 3.468 / 6.898 | 3.313 / 6.589 | 0.8337 | 8 | 5 / 8 | 36.9 / 22.2 / 29.0 / 12.0 |
| n00U | clay-raw | 625 | 0.365 / 1.096 / 2.55 | 1.055 / 2.453 | 0.9276 | 8 | 5 / 8 | 41.3 / 17.9 / 33.0 / 7.8 |
| n00U | clay-prefit | 625 | 0.964 / 2.978 / 5.791 | 2.821 / 5.486 | 0.8524 | 8 | 5 / 8 | 39.4 / 19.7 / 29.2 / 11.8 |
| hfoo | clay | 630 | 1.295 / 3.829 / 8.113 | 3.472 / 7.357 | 0.7521 | 0 | 0 / 0 | 37.5 / 26.3 / 23.6 / 12.7 |
| hfoo | clay-raw | 630 | 0.078 / 0.348 / 1.038 | 0.334 / 0.996 | 0.9856 | 0 | 0 / 0 | 49.2 / 16.8 / 28.0 / 5.9 |
| hfoo | clay-prefit | 630 | 1.213 / 3.555 / 6.979 | 3.208 / 6.297 | 0.7659 | 0 | 0 / 0 | 39.5 / 24.5 / 24.1 / 11.9 |
| n017 | clay | 622 | 1.143 / 3.267 / 11.825 | 3.135 / 11.347 | 0.7824 | 0 | 1 / 0 | 36.0 / 22.8 / 28.4 / 12.7 |
| n017 | clay-raw | 622 | 0.261 / 0.721 / 12.094 | 0.693 / 11.61 | 0.9654 | 0 | 1 / 0 | 49.0 / 10.2 / 38.7 / 2.1 |
| n017 | clay-prefit | 622 | 1.153 / 3.306 / 12.068 | 3.108 / 11.343 | 0.7834 | 0 | 1 / 0 | 39.1 / 18.2 / 29.0 / 13.8 |
| n02X | clay | 629 | 1.383 / 3.906 / 7.709 | 3.573 / 7.051 | 0.7106 | 7 | 1 / 2 | 32.2 / 27.9 / 22.0 / 17.9 |
| n02X | clay-raw | 629 | 0.23 / 0.664 / 6.864 | 0.638 / 6.59 | 0.9527 | 7 | 1 / 2 | 44.2 / 17.8 / 30.6 / 7.4 |
| n02X | clay-prefit | 629 | 1.215 / 3.557 / 7.264 | 3.262 / 6.662 | 0.7251 | 7 | 1 / 2 | 35.3 / 25.6 / 22.7 / 16.4 |

- **Leitura.** A união crua (`clay-raw`) já está colada ao campo (p95 0.35-1.1 % H, ≈ 0.3-1 voxel; consistência 0.93-0.99), exceto o máx de n017 (12 %, p95 0.72: poucos vértices longe do campo, causa não investigada) e n02X (6.9 %). O `clay` final se afasta (p95 2.4-3.9 % H, 2.3-3.6 voxels; consistência
  0.71-0.83) porque o deform/fit move vértices para a folha: a meta de L10-3 ("p95 ≤ H/64 = 1.56 %, máx ≤ H/32 = 3.1 %") é
  mais estrita que o `clay` atual e mais frouxa que a união crua; é o `clay-raw` que mede a fidelidade da extração, o `clay` o que o fit
  pede de deslocamento. `euler`: 0 em n005/hfoo/n017 (corpo fechado gênero 0); n00U 8 (≠ 0: gênero ≥ 2 ou casca aberta; 5 arestas non-manifold, 8 de borda); n02X 7
  (casca com borda 2 e non-manifold 1); n017 tem um componente pequeno com 4 (corpo 0). nd 60-100°: 28-39 % no clay-raw, 22-29 % no
  `clay`: acima da faixa-alvo 10-20 % (a união tem mais quinas que o alvo; o alvo 60-100 % é o que L10-3 tem de baixar).
- **Negativos.** O campo recomputado vem do spec atual: se o spec mudou depois do GLB (ou o clay passou por `cut`), a medida mede o spec, não o
  que gerou o GLB. Props/flame fora do campo mas dentro do GLB: só o maior componente entra, por isso um corpo partido em vários pedaços
  mede só o maior. `normal_consistency` usa |·| (não detecta normal invertida: isso é o gate `flipped`).
- **Testes.** `tests/tools/blender/test_mesh_lint.py`: cubo contra SDF de box exato (dev ≈ 0, consistência 1, euler 0, nd 33.3/0/66.7/0),
  vértice puxado (p95 > 1 % H), casca aberta (euler −2, `sdf_dev` None), sem campo nem spec (None sem erro).

### 27.T5 Um material por (imagem, emissivo, opacidade) no export (2026-10-29)

Fonte: Android, Optimize textures (https://developer.android.com/games/optimize/textures): menos materiais/texturas = menos draw calls.
`UnitBatch` faz 1 `DrawMeshInstances` por mesh/primitive, então cada material do GLB custa 1 draw por tipo de unidade.
- `build_unit.merge_materials(body)` roda após `texturize` em cel (`MERGE_MATERIALS = True`; `materials=split` no `build_unit`,
  `--materials split` no `spec_pipeline`, restaura 1 material por slot). Agrupa por `surfaces.merge_groups` (função pura, testada):
  chave `(imagem, cor de emissão ou None, alpha)`. As faces vão para o primeiro slot do grupo, `material_slot_remove_unused` limpa.
  Forma e UVs intactas (já estão no espaço do atlas único). painted (4 imagens) não é tocado.
- Slots emissivos (flame/lamp/glow) e translúcidos (glass, alphaMode BLEND) ficam separados: glTF soma `emissiveFactor` sem
  multiplicar pela textura, então fundir com o iron acenderia o corpo todo. Por isso n005/hfoo/n00U ficam com 2 (corpo + flame/glow).

Medição (`spec.json` v12-r1 -> `build_unit ... tex style=cel`, split x merge; render_unit 9 vistas, mesma câmera):

| unidade | prims/draws | bufferViews | GLB KB | `mesh_lint` (images, uv_oor, skins, tris) | render |
|---|---|---|---|---|---|
| n005 | 7 -> 2 | 215 -> 186 | 166.3 -> 160.6 | 1, 0, 1, 630 iguais | 0 em 9 vistas |
| hfoo | 8 -> 2 | 279 -> 243 | 200.4 -> 193.3 | iguais | 3/255 em <= 7 px |
| n017 | 4 -> 1 | 219 -> 201 | 173.3 -> 169.8 | iguais | 7/255 em 16 px |
| n00U | 5 -> 2 | 267 -> 249 | 218.4 -> 214.9 | iguais | 0 |
| n02X | 7 -> 1 | 292 -> 256 | 212.5 -> 205.4 | iguais | 0 |

- Clipes idênticos por nome (5 ou 7 por unidade), `mesh_lint.engine_import` ok (meshes 7->2 etc.), `render_anim walk` roda.
- Diferença de render = ruído de ordem de desenho/AA (<= 16 px de 262144). Default virou merge.
- Não medido: stage 2 completo (deform/fit_verts pós-build) nem o draw count in-engine; as unidades hfoo/n00U/n02X não têm
  `spec-colour.json` no v12-r1, então usei `spec.json` sem props crops (como em 27.T4).


### 28.L10-2 Extração da malha do campo SDF (openvdb, bruta)
- **O que mudou.** `build_unit.sdf_mesh(field, adaptivity=0.0)` (função nova, isolada; `main()` e `union_body` intactos, a troca é
  L10-7): `openvdb.FloatGrid.copyFromArray(field.grid)` (background = `field.margin`, `GridClass.LEVEL_SET`) →
  `convertToPolygons(isovalue=0, adaptivity)` → pontos em índice → mundo `origin + idx·voxel` → quads cortados em dois triângulos
  pela diagonal mais curta → `from_pydata`, `remove_doubles` 1e-6, `recalc_face_normals`. As partes puras (numpy) estão em
  `sdf_body.index_to_world` e `sdf_body.quads_to_tris`. Sem pele, material ou UV (L10-5). Nenhum flag novo no `build_unit`:
  `tools/blender/sdf_extract.py` (`blender -b -P tools/blender/sdf_extract.py -- <run_dir> <outdir> [grids=96,128]
  [adapt=0,0.5,0.9] [octree=6,7]`) chama `field` + `sdf_mesh` e grava `clay-sdfraw-g<G>-a<A>.glb`, a coluna REMESH SHARP
  (`clay-remesh-o<D>.glb`: peças do corpo só juntadas, sem props/flame, modificador Remesh modo SHARP, `scale` 0.99) e
  `ablation.json`. `tools/blender/sdf_extract_report.py <scratch> <runs>` roda o `mesh_lint` (python3.14) nos GLBs e imprime a
  tabela. `sdf_dev` provisório = |`Field.d`(vértices)| / voxel (média, p95, máx); L10-6 o move para o `mesh_lint`.
- **Ablação** (5 unidades v12-r1, `fit/cuts.json` onde existe, 96³ salvo dito; faixa mínimo–máximo nas 5; malha bruta, sem retopo).
  `flip / borda / non-manifold / comp` = soma nas 5 (comp = máximo).

| config | tris | sliver % | nd média ° | nd p90 ° | flip/borda/non-man/comp | `sdf_dev` p95 (vox) | `sdf_dev` máx (vox) | extração s |
|---|---|---|---|---|---|---|---|---|
| união v12 (baseline) | 622–630 | 10–32 | 44–55 | 99–121 | 1/10/7/5 | 3.7–23.7 (a união não é o campo) | 6.3–29.7 | — |
| SDF adapt 0 | 32 856–123 300 | 0.1–0.6 | 3.8–6.2 | 12.9–20.1 | 0/0/0/1 | 0.16–0.22 | 0.50–0.61 | 0.06–0.23 |
| **SDF adapt 0.5** | **6 776–24 068** | **1.2–2.2** | 13.7–14.7 | 40–43 | **0/0/0/1** | **0.27–0.35** | 0.53–1.45 | 0.015–0.047 |
| SDF adapt 0.9 | 4 382–17 086 | 1.4–2.9 | 15.4–16.1 | 45–49 | 0/0/0/1 | 0.31–0.35 | 0.75–1.26 | 0.011–0.034 |
| SDF adapt 0.5 a 128³ | 9 994–32 818 | 1.4–3.1 | 13.0–14.5 | 39–45 | 0/0/0/1 | 0.29–0.32 | 0.73–1.36 | 0.02–0.07 |
| REMESH SHARP octree 6 | 14 604–53 280 | 2.0–3.1 | 9.8–11.8 | 44–59 | 625/0/3116/2 | 3.0–34 | 6.6–41 | 0.03–0.08 |
| REMESH SHARP octree 7 | 60 296–227 752 | 0.9–1.3 | 5.1–5.9 | 0–3.4 (poucas arestas de 2 faces) | 871/0/7731/3 | 2.9–34 | 6.7–41 | 0.07–0.27 |

  Tempo do `field` 96³: 0.05–0.40 s (128³: 0.09–0.88 s); `field` + extração ≤ 0.45 s nas 5 a 96³ (adapt 0.5: 0.07–0.44 s).
  Por unidade (adapt 0.5, 96³): n005 6 776 tris, n00U 24 068, hfoo 7 754, n017 8 376, n02X 12 946.
- **Aceite.** Fechada (borda 0, non-manifold 0, flipped 0, 1 componente) nas 5/5 em todas as 6 configurações SDF; slivers brutos
  ≤ 3.3 % (< 4 %) em todas; `sdf_dev` p95 ≤ 0.35 voxel (≤ 0.5) em todas, máx ≤ 1.45 voxel.
- **Default escolhido: 96³, adaptividade 0.5.** `adapt 0` dá a melhor fidelidade (p95 0.16–0.22) mas 33 k–123 k tris para o QEM do
  L10-3 reduzir a ~620 (n00U: 123 k); `adapt 0.9` poupa só ~25 % de tris sobre 0.5 e sobe slivers (até 2.9 %) e nd; 128³ não ganha
  em p95 (0.29–0.32 vs 0.27–0.35) e custa 1.4–1.6× os tris. 0.5 fica com `sdf_dev` p95 ≤ 0.35 voxel e 6.8 k–24 k tris, ~11–39×
  o orçamento (reduz o L10-3). nd ainda alto (média 14°, p90 40–43°) porque o adaptativo funde coplanares: é a entrada do retopo,
  não o resultado.
- **REMESH SHARP: descartado como substituto.** Sem SDF: arestas non-manifold (3 k–8 k por unidade a 6–7), flipped 625–871, 2–3
  componentes no n02X e `sdf_dev` p95 3–34 voxels (n00U 14 vox médios: as pernas finas de aranha deformam). Só serve como
  comparação barata do quanto o SDF ganha.
- **Peças finas** (`thin_parts`: 2·inradius < 4 voxels a 96³, flag `lt2` = < 2 voxels). Nenhuma peça tem < 2 voxels nas 5 unidades
  (a mais fina: n017 head frustum 2.7 voxels, as duas "chifres" 0.08 m); as que passam de 4 voxels não são listadas. Triângulos da
  malha mais próximos de cada peça fina (adapt 0 / 0.5 / 0.9): n005 head prism 3.6 vox 162 / 82 / 64; hfoo pelvis prism 3.4 vox
  429 / 207 / 98; n017 os 2 frustums de head (2.7 vox) **0 / 0 / 0**: estão inteiros dentro de outra peça da cabeça (d do campo
  total ≤ −1 voxel em todas as amostras do interior), enterrados e não perdidos pela resolução. n00U e n02X: nenhuma peça < 4 voxels
  (o único plate, n02X, tem 11.8 voxels). Política de peça fina: L10-7, não implementada.
- **Renders.** `history/2026-10-29-l10-extract/<id>.png`: união v12 (linha de cima) | SDF bruto 96³ adapt 0.5 (de baixo), front /
  left / tq (`render_unit.py lit`). Silhuetas coincidem; a superfície bruta é ruidosa (degraus do adaptativo na carapaça do n00U,
  facetas do n005): é o que o retopo L10-3 resolve.
- **Negativos / não feito.** Sem pele, material, UV nem separação de props/flame (L10-5); `sdf_mesh` não entra no `main()`;
  `body=sdf-raw` não é flag do `build_unit` (o `sdf_extract.py` o substitui); `sdf_dev` só neste script (L10-6); sem
  adaptividade por região; GLB do REMESH sem pele (só a malha, para medir).
- **Testes.** `tests/tools/blender/test_sdf_extract.py`: índice→mundo, quad→tri (diagonal curta, orientação, área) rápidos;
  `SLOW=1` roda o Blender no n005 (fechada, 1 componente, flipped 0, slivers < 4 %, `sdf_dev` p95 ≤ 0.5).

### 28.L10-3 `retopo.py`: QEM com guarda, reprojeção no SDF e rodadas independentes (numpy puro)
- **O que mudou.** `tools/blender/retopo.py` (novo): `reduce(verts, tris, target_faces, sdf=None, features_deg=None, min_angle=15,
  floor=0.9, polish=None, grad_h=None, max_dev=None)` → `(verts, tris, report)`; `grid_sdf(grid, origin, voxel)` (d por interpolação
  trilinear de `Field.grid`, o campo barato do laço). `retopo_mc.py` (novo): `surface_nets(grid, origin, voxel)`, malha densa só
  para teste em python3.14 (naive surface nets; tem 4 arestas não-manifold no n005 a 96³, o openvdb não). `retopo_blender.py` (novo,
  Blender): `export` (SDF 96³ das 5 unidades → `convertToPolygons` adaptividade 0 e 0.5, `.npz`) e `collapse` (Decimate COLLAPSE
  cego, a linha de base). `retopo_ablate.py` (novo): a tabela abaixo. Nada em `build_unit.py`, `mesh_lint.py`, `sdf_body.py`.
- **Algoritmo.** Garland & Heckbert: quádrica por vértice = soma dos planos das faces (peso = área); custo de uma aresta = v^T (Qa+Qb) v
  no ponto ótimo (sistema 3x3 amortecido a partir do ponto médio, preso a 1 comprimento de aresta) + `(LEN_REG·tam)²·len²`
  (`LEN_REG = 1e-2`: empates entre arestas planas vão para a mais curta, senão o QEM faz triângulos longos). Guarda por colapso:
  ângulo mínimo dos triângulos que sobrevivem ≥ `min_angle` (ou não pior do que já era), normal não vira (dot < 0), área não some,
  condição de link (vizinhos comuns = 2, senão a casca belisca). Se o ótimo falha, tenta o lugar de a, o de b, o ponto médio, e só
  aceita se o erro quádrico ≤ `SLACK = 1` × o do ótimo. Reprojeção de Newton `p ← p − d∇d/|∇d|²` (2 passos, diferenças centrais, passo ≤
  comprimento da aresta) antes da guarda, e passo final (`polish`, o campo exato `Field.d`) em todo vértice, desfeito onde vira uma
  face. `max_dev`: recusa o colapso que deixa o centróide de um triângulo mais longe do SDF do que isso (e do que já estava).
  Alvo F ≤ B = `target_faces`, nunca abaixo de `floor·B` (a última rodada é cortada para cair em [0.9 B, B]; V* = (B+4)/2 em casca
  fechada de gênero 0). Se nada colapsável sobra acima de B, o `min_angle` é relaxado por estágios (×0.8, 0.6, 0.4, 0.2, 0; a guarda de
  normal fica) e o `report` diz (`stages`, `relaxed_min_angle`): nas 5 unidades a 600 nunca foi preciso. O `euler` de entrada é mantido
  (nenhuma alça nasce nem some).
- **Rodadas, não heap (desvio da spec).** O protótipo com `heapq` e poucas chamadas numpy por colapso levou 9.7 s no n005 (34 k tris;
  18 s com reprojeção): 47 k tentativas × ~200 µs de overhead numpy. Agora cada rodada custa todas as arestas de uma vez (vetorizado),
  escolhe as arestas mais baratas da sua 2-vizinhança (conjunto independente: aplicar juntas = aplicar uma a uma), projeta e guarda
  todas de uma vez, aplica as que passam; as que falham ficam banidas até a vizinhança mudar; 4 conjuntos por rodada. n005 34 k → 600 em
  0.8 s, n00U 123 k → 600 em 2.7 s. O protótipo ficou no histórico git (`4ab27344`).
- **Entrada.** Malha do openvdb `convertToPolygons` do campo 96³ (`retopo_blender.py export`): a0 = adaptividade 0 (densa: 34 k / 123 k /
  33 k / 69 k / 57 k tris), a5 = adaptividade 0.5 (6.8 k / 24 k / 7.8 k / 8.4 k / 12.9 k). Mesma malha bruta em todas as linhas; os
  specs de `runs/draft/{n005,n00U,hfoo,n017,n02X}/v12-r1` com `fit/cuts.json` (n017 não tem), rig do spec escalado e restaurado.
  Reproduzir: `blender -b -P tools/blender/retopo_blender.py -- export <dir>` e
  `python3.14 tools/blender/retopo_ablate.py <dir> --src a0|a5 [--target 600] [--json out.json]`.
- **Ablação (média das 5 unidades, B = 600, a0; sdf_dev em % de H medido em vértices + pontos médios de aresta + centróides com o
  `Field.d` exato; IoU = pior vista menos o `clay-raw` da união, contra `refs/<id>/sheet.jpg`, câmeras do `silhouette.json`).**

| linha | tris | sliver % (min–max) | nd | faixa 60–100 % | fairness | flipped | borda/nm | sdf_dev p95 (máx unid.) | sdf_dev máx (máx unid.) | IoU pior Δ | tempo soma (máx) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| união v12 `clay.glb` | 527 | 11.3–33.8 | 48.2 | 25.1 | 31.9 | 383 | 244/6 | 2.74 (3.02) | 7.47 (11.73) | −0.055 (deformado ao sheet) | – |
| união `clay-raw.glb` | 564 | 10.9–34.5 | 41.7 | 32.2 | 31.3 | 99 | 81/6 | 0.87 (1.60) | 5.68 (12.75) | 0 | – |
| COLLAPSE cego (Blender) | 600 | 6.3–23.5 | 37.2 | 25.0 | 31.2 | 14 | 0/0 | 0.46 (0.97) | 2.06 (4.20) | −0.014 | 0.5 s (0.23) |
| QEM puro | 600 | 1.3–3.5 | 34.2 | 21.1 | 24.8 | 27 | 0/0 | 0.87 (1.52) | 2.58 (3.99) | −0.020 | 4.9 s (1.87) |
| + guarda 15° | 600 | 0.0 | 34.9 | 22.2 | 23.9 | 19 | 0/0 | 0.78 (1.37) | 2.35 (3.59) | −0.011 | 5.5 s (2.08) |
| + reprojeção SDF | 600 | 0.0–0.5 | 34.2 | 22.3 | 24.0 | 16 | 0/0 | 0.83 (1.45) | 2.66 (3.74) | −0.013 | 6.5 s (2.40) |
| **+ guarda de desvio H/50 (final)** | 600 | 0.0–0.5 | 34.5 | 22.7 | 24.0 | 14 | 0/0 | 0.83 (1.44) | 2.09 (2.87) | −0.013 | 7.5 s (2.69) |
| + features 35° (pesos 100, regras) | 600 | 0.0–28.0 | 39.8 | 19.8 | 32.7 | 209 | 0/0 | 2.05 (3.46) | 7.48 (13.46) | −0.341 | 31 s (9.7) |

  `flipped` = faces com normal contra o gradiente do SDF no centróide (ruído nas junções: a malha densa tem 4–254). O `euler`
  (F − 2V + 4) é 0, 12, 0, 0, 8 em todas as linhas COLLAPSE/QEM (= o da malha de entrada: o n00U e o n02X já nascem com alças, ver
  abaixo). Mesma tabela a5 (entrada adaptividade 0.5): final sliver 0.0–0.8, nd 34.9, p95 1.03 (1.67), máx 2.46 (3.06), tempo 2.7 s
  somado (1.09 máx); COLLAPSE sliver 4.7–17.5.

- **Linha final por unidade (a0, B = 600).**

| unidade | tris | sliver % | nd (união `clay.glb`) | faixa 60–100 | fairness | sdf_dev p95 / máx % H (máx em voxels) | euler (entrada) | IoU pior Δ vs `clay-raw` | s |
|---|---|---|---|---|---|---|---|---|---|
| n005 | 600 | 0.0 | 29.8 (45.0) | 20.9 | 22.3 | 0.46 / 2.00 (1.9) | 0 (0) | −0.003 | 0.83 |
| n00U | 600 | 0.0 | 41.8 (48.8) | 27.1 | 26.0 | 1.44 / 2.87 (2.8) | 12 (12) | −0.002 | 2.69 |
| hfoo | 600 | 0.5 | 33.6 (46.3) | 20.6 | 24.6 | 0.62 / 1.83 (1.8) | 0 (0) | −0.013 (left) | 0.93 |
| n017 | 600 | 0.0 | 29.7 (48.3) | 22.3 | 23.9 | 0.88 / 1.79 (1.7) | 0 (0) | −0.009 | 1.57 |
| n02X | 600 | 0.0 | 37.8 (52.8) | 22.4 | 23.4 | 0.73 / 1.94 (1.9) | 8 (8) | −0.005 | 1.45 |

- **Aceite do plano.** `sliver_pct < 5`: 5/5. `sdf_dev` p95 ≤ H/64 (1.56 %) e máx ≤ H/32 (3.13 %): 5/5 (sem a guarda de desvio o máx do
  n00U era 3.58 % e o do n02X 3.74 %; a guarda custa 0.3 s no n00U). tris em [540, 600]: 5/5 (600 exatos). ≤ 3 s: 5/5 (n00U 2.7 s a
  0 de adaptividade, 1.1 s a 0.5; medido com outros agentes rodando). `normal_diff` ≤ união −10°: 4/5 (−15.2, **−7.0**, −12.7, −18.6,
  −15.0; o n00U falha por 3°: a aranha tem muito osso fino). IoU 6 vistas ≥ `clay-raw` −0.01: 4/5 (hfoo `left` −0.0126; a malha
  densa do SDF já está −0.018 nessa vista, a diferença vem do corpo SDF e não da retopologia, que devolve +0.005 sobre a densa).
  `euler == 0`: 3/5; n00U (12) e n02X (8) mantêm o `euler` da malha de entrada (genus 3 e 2: alças que a união também tem), o que
  é o critério honesto. **Faixa 60–100° em 10–20 %: 0/5** (20.6–27.1 %; a linha de base cega dá 22.7–31.6 e a união 28–38): perto,
  não dentro; não foi forçado.
- **Decisões.** (1) Default da retopologia = QEM + guarda + reprojeção + guarda de desvio, `features_deg=None` (a spec pedia 35°).
  (2) Entrada recomendada para o L10-2: a0 se o tempo couber (n00U 2.7 s); a5 é 2.5× mais rápida e troca duas coisas: p95 do n00U 1.67 % (> 1.56 %) e IoU 4/5
  (n017 `bottom` −0.013 em vez do hfoo `left`). (3) Campo do laço = grade trilinear (barato, vetorizado); campo exato só no `polish` e na medida.
- **Negativos.** *Features (diedro ≥ 35° da entrada, quádrica perpendicular com peso 100, cantos fixos, absorção, sem corda):* pior em
  tudo (sdf_dev máx 7.5 % vs 2.1 %, slivers até 28 %, IoU −0.34 no n00U). Os corpos são facetados (n005: 1563 arestas ≥ 35° na malha
  densa, 747 mesmo em 2400 tris; n00U 5767): não cabem em 600 triângulos, a parte lisa é devorada primeiro e as pernas finas somem;
  em malha de marching cubes o canto vira um friso duplo (a corda entre os dois frisos é proibida). Pesos 1/5/20, só quádrica ou
  sem regras, limiar 45/60°: nenhum bate "sem features". *Flips de aresta por diedro mínimo* depois dos colapsos (protótipo,
  removido): fairness 24 → 20 mas sdf_dev ×2–3 (n00U p95 1.44 → 4.13 %) e nd +1–9°. *Posições de fallback sem teto (`SLACK` 1e9):* slivers 0 mas sdf_dev máx
  +60 % na soma das 5 unidades; teto 1 foi o melhor dos {1, 3, 10, ∞}. `LEN_REG` {2e-3, 5e-3, 1e-2, 3e-2} (a5, SLACK 1): 5e-3–1e-2 melhor equilíbrio de
  sdf_dev × fairness × tempo (2e-3 é 3× mais lento e piora fairness; 3e-2 sobe o sdf_dev). Fairness 24 (alvo ≤ 20 do plano para QEM) não atingida; é o que a remalhagem do L10-4 deve ganhar.
  O n00U/n02X a 600 estão no limite do orçamento (pernas de 8-gon): se o L10-7 subir o orçamento para 700 sobra folga. Heap: ver acima.
- **Testes.** `tests/tools/blender/test_retopo.py` (10, 2 s; `SLOW=1` + n005 96³ → surface nets → 600 em ≤ 3 s, sdf_dev ≤ H/64 / H/32):
  cubo subdividido (300 tris) → 12 tris exatos com os 8 cantos; esfera densa → alvo, 0 slivers, euler 0, manifold; guarda recusa
  normal virada e sliver; Newton reduz |d|; reprojeção no laço aproxima da esfera; guarda de desvio; `grid_sdf`; surface nets.

### 28.L10-5 Osso, pesos e material da malha SDF (`sdf_body.weights`, `build_unit.sdf_body_object`)
- **O que mudou.** `sdf_body.weights(points, field, parts, rig)` (numpy puro) → (nomes de ossos, W (N, ossos), linhas somam 1) e
  `sdf_body.materials(points, field, parts)`. O dono do ponto é a peça de menor d; toda outra peça com d dentro da faixa do par
  soma `exp(−2 gap / faixa)` (σ = faixa/2) com fade `smoothstep` até 0 na borda, então a pele é contínua (a mistura de 2 do plano
  truncava em duas peças e dava degrau com a terceira) e não depende da densidade da malha. `faixa = pair_k × BAND_SCALE (14)`
  para peças ligadas por `smin` (pai/filho), `× FREE_SCALE (10)` para as demais (pernas da aranha). As distâncias vêm de
  `near_distances` (cada casco com `max(plano, distância à caixa)`: o plano de uma face segue longe da peça e misturava a perna
  oposta; o grid continua com `part_d`). Limb com par upper/lower: `share` do arco from→joelho→to, `upper = clip(0.5 − (share − joelho)/0.3)`
  (rampa ±0.15, 1 / .5 / 0 como o `skin_part`); chain: osso do segmento mais próximo; resto: o osso da peça.
  `build_unit.sdf_body_object(spec, cuts, grid=96, adaptivity=0.5, k=1, **bands)` → `(objeto, field)`: `field` → `sdf_mesh` → solda
  de vértices a < 0.03 voxel (`SDF_WELD`; a extração adaptativa deixa arestas de 1e-3 voxel que um vértice de dois ossos estica) →
  `skin_sdf` (vertex groups por osso com peso ≥ 0.01, uma ranhura por material único, material da face = peça mais próxima do
  centróide, como `transfer_from_parts`). Props e `flame` seguem componentes separados, pele 100 % na âncora. `main()` NÃO chama
  (L10-7). `sdf_extract.py -- <run> <out> skin=1 [clay=0|1] [grid=96] [adapt=0.5] [name=clay-sdfskin] [band=] [free=] [weld=]`
  grava `<name>.glb` (armadura, clipes, props), `<name>.json` e `<name>-attach.json` (`union.components_body`, para o `mesh_lint`).
- **Ablação da faixa** (anterior ao `near_distances` e à solda; esticão p99.5 das arestas, `walk` / `attack` / `death`, 12 quadros, relativo à união v12; n005 e n00U;
  `walk_check.py` da L6-5 por ação): faixa 1×k (só a mistura de 2): n005 5.54 / 2.83 / 4.10 (união 2.53 / 2.05 / 2.84); o esticão
  vem de arestas curtas (2–8 mm) em degraus de peso (o mesmo ∇w dá a mesma razão em qualquer comprimento), logo a faixa tem que
  ser larga: 4×: 3.94 / 2.16 / 2.89; 10×: 2.77 / 1.84 / 3.16; 16×: 2.20 / 1.98 / 3.29. Suavização topológica dos pesos (n passos no 1-anel)
  ajudava na malha bruta, mas depende da densidade (o retopo L10-3 a estragaria): removida. Misturar longe demais piora a aranha
  (faixa livre 32×: n00U `death` 17 vs união 4.97) e a distância de plano sem a caixa misturava a perna oposta (n017 `death` 7.9 com 16×).
  Escolha: 14× (pares ligados) e 10× (livres), a que deixa as 5 ≤ 1.1× exceto o `walk` do n017.
- **Prova** (v12-r1, `fit/cuts.json`, 96³ adapt 0.5, solda 0.03 voxel; esticão = `anim_check.py` na scratchpad, o `walk_check.py` da
  L6-5 por ação; zonas = `silhouette.py --ids` das mesmas câmeras sobre o rebuild em cores chapadas, `spec.json`, união
  `build_unit nofuse 700` × `sdf_extract skin=1 clay=0`):

| unidade | tris | `skins` / `images` / mats (união) | `components_body` (união) | fechada | engine_import | esticão `walk` união→SDF | `attack` | `death` | `max_dup_split` | zonas Δ máx (união→SDF) |
|---|---|---|---|---|---|---|---|---|---|---|
| n005 | 6 912 | 1 / 0 / 7 (7) | 1 (1) | 0 / 0 | ok, 5 clipes | 2.53→2.40 (0.95×) | 2.05→1.43 (0.70×) | 2.84→1.82 (0.64×) | 0 | +0.012 front (.653→.665) |
| n00U | 24 028 | 1 / 0 / 5 (5) | 1 (2) | 0 / 0 | ok, 5 | 1.47→1.40 (0.95×) | 1.85→1.59 (0.86×) | 4.97→3.71 (0.75×) | 0 | −0.005 bottom |
| hfoo | 7 810 | 1 / 0 / 8 (8) | 1 (1) | 0 / 0 | ok, 7 | 2.24→1.98 (0.88×) | 2.12→1.90 (0.90×) | 2.16→2.08 (0.96×) | 0 | +0.004 front |
| n017 | 8 480 | 1 / 0 / 4 (4) | 1 (1) | 0 / 0 | ok, 5 | **1.82→2.23 (1.22×)** | 6.34→1.52 (0.24×) | 3.98→2.41 (0.61×) | 0 | −0.007 left |
| n02X | 12 990 | 1 / 0 / 7 (7) | 1 (1) | 0 / 0 | ok, 7 | 4.39→3.40 (0.77×) | 3.04→1.88 (0.62×) | 3.14→2.01 (0.64×) | 0 | +0.014 back |

  `fechada` = boundary / non-manifold do `mesh_lint`. `skins == 1`, `uv_out_of_range 0`, slivers 1.1–2.0 %, 0 flipped. Mesmo número de
  materiais da união em cada unidade. A união do n00U tem 2 componentes de corpo; o SDF, 1. Zonas por view em
  `scratchpad/l10-skin/zones/*/{union,sdf}/zones_clay.json`; o maior desvio negativo é −0.007 (n017 left), os dois acima de +0.01
  (n005 front +0.012, n02X back +0.014) são ganhos. Renders: `render_anim` n005 walk/attack/death em 12 quadros roda.
- **Não passou.** `walk` do n017 fica em 1.22× a união (2.23 vs 1.82; a união é baixa nessa unidade): o resto do esticão é o
  gradiente de peso na junção tronco/perna/cauda (três ossos), mais largo piora `death` (faixa 16×: 3.58, 1.29× no `walk`). As outras
  14 medidas ficam em 0.24–0.96×.
- **Negativos / não feito.** Sem textura (a UV/atlas do SDF é L10-7: o `texturize` usa `parts_meta` das peças originais, que o
  `sdf_extract` não monta); `main()` e `union_body` intactos; sem metrica `sdf_dev` aqui (L10-6). O esticão é de uma malha bruta
  de 7–24 k tris: o retopo (L10-3) muda a razão das arestas, repetir a medida depois dele. Mais de 4 influências por vértice
  possíveis (o exportador glTF guarda as 4 maiores). Chain com degrau duro entre segmentos (só o n017 tem; sem rampa).
- **Testes.** `tests/tools/blender/test_sdf_body.py::Skin` (boxes pai/filho: osso certo e mistura no vinco; irmãos distantes não
  misturam; limb sintético: rampa upper→lower monótona 1/.5/0; material da peça mais próxima) e, `SLOW=1`,
  `test_sdf_extract.py::test_skin_is_one_skin_one_body_with_the_clips` (n005: `skins 1`, `components_body 1`, fechada, grupos, importa).


### 28.L10-4 `retopo.remesh`: remalhagem isotrópica com projeção no SDF (alternativa ao QEM; default NÃO muda)
- **O que mudou.** `tools/blender/retopo.py`: `remesh(verts, tris, target_faces, sdf, iters=10, features=None, polish=None, grad_h=None,
  max_dev=None, guide=None)` (Botsch & Kobbelt 2004) e `retopo(verts, tris, target, sdf, method=None, features=None, **kw)`, a entrada
  única: `method` ∈ `METHOD` = `"qem"` (default) | `"remesh"` (aponta a `AIM`=0.96 × alvo) | `"hybrid"` (remesh a 1.2 × alvo + `reduce` curto) |
  `"guided"` (`reduce`, depois remesh com o comprimento de aresta dele como campo de tamanho); todos menos `qem` fecham com `reduce` se
  ficarem acima do alvo. `retopo_ablate.py`: linhas novas, `--l10-4` (só as linhas da tabela), `--render <pasta>` (clay 3 vistas em PIL, sem
  Blender). Nada em `build_unit.py`, `mesh_lint.py`, `sdf_body.py`. A constante `METHOD` registra a recomendação: `"qem"`.
- **Algoritmo (por iteração, numpy, vetorizado por rodadas como o `reduce`; 600 tris em 1.1–5.2 s).** L0 = √(4A/(√3·F*)); (1) *split* das
  arestas > 4/3 L no ponto médio projetado, no máximo uma por face (`best_of_faces`: a aresta de maior necessidade em cada face de suas
  duas); (2) *collapse* das < 4/5 L: `Shorts(Reducer)` reaproveita o `reduce` (conjuntos independentes da 2-vizinhança, link, guarda de
  ângulo 15°/normal, projeção) com custo = comprimento, e recusa deixar aresta > 4/3 L; (3) *flip* para valência 6 (soma |val−6| cai, val > 3,
  a aresta nova não existe, normais novas a < 25° da média das duas antigas, ângulo mínimo ≥ 20°, nunca em feature), conjuntos independentes por
  face; (4) *relax* tangencial (`SMOOTH`=0.6 × (centróide dos vizinhos − p), sem a componente normal), 3 passos com projeção de Newton no SDF
  (grade trilinear no laço, `Field.d` exato no fim) e as moves que viram ou afastam uma face acima de `max_dev` desfeitas. L segue a
  contagem: L ← L·√(F/alvo) nas iterações até as 2 últimas (congela). `features` (opt-in, diedro da entrada): cantos (≥ 3 arestas) fixos,
  vértice com 2 desliza só entre os 2 vizinhos de feature, as regras corner/absorb/chord do `reduce`, flip nunca em feature.
  `max_dev` = o mesmo parâmetro do `reduce`, mas aqui é o que decide: collapse e relax só valem se o centróide de cada triângulo ficar a
  ≤ `max_dev` do zero (ou não piorar); com o 2 % do QEM o remesh dá p95 1.5–2.9 % e máx até 5.6 % (a malha isotrópica atravessa as quinas);
  `REMESH_DEV` = 1.2 % de H na ablação (1.0 %: p95 −0.1, fairness +2; 0.6 %: n00U vira 932 tris).
- **Entrada e reprodução.** A mesma malha openvdb a0 (96³) do L10-3. `python3.14 tools/blender/retopo_ablate.py <dir> --l10-4 [--target 700]
  [--render artifacts/model-sheets/history/2026-10-29-l10-remesh] [--json x.json]` (`<dir>` = o `retopo_blender.py export`).
- **Ablação (média das 5 unidades, a0; sdf_dev em % de H com `Field.d` exato; IoU pior vista Δ vs `clay-raw`; fairness = média |ângulo − 60|).**
  B = 600:

| linha | tris | sliver % | nd | 60–100 % | fairness (máx unid.) | sdf_dev p95 (máx) | sdf_dev máx (máx) | IoU Δ médio (pior) | euler = entrada | s soma (máx) |
|---|---|---|---|---|---|---|---|---|---|---|
| QEM (L10-3 final) | 600 | 0.0–0.5 | 34.5 | 22.7 | 24.0 (26.0) | 0.83 (1.44) | 2.09 (2.87) | −0.006 (−0.013) | 5/5 | 7.8 (2.9) |
| remesh | 573 (≤ 578) | 0.0 | 29.8 | 13.4 | **12.1 (20.1)** | 1.47 (1.61) | 2.51 (3.31) | −0.014 (−0.056) | 5/5 | 12.8 (5.2) |
| remesh + QEM curto (1.2 × B → B) | 600 | 0.0–0.3 | 30.7 | 13.7 | 15.4 (21.1) | 1.43 (1.61) | 2.77 (4.10) | −0.009 (−0.022) | 5/5 | 12.1 (4.9) |
| remesh + features 35° | 583 (≤ 600) | 0.2–6.3 | 36.8 | 19.2 | 20.6 (28.4) | 1.32 (1.44) | 3.21 (3.62) | −0.007 (−0.017) | 5/5 | 16.1 (6.1) |
| QEM → remesh guiado | 577 (≤ 582) | 0.0 | 31.2 | 14.4 | 13.1 (21.7) | 1.43 (1.54) | 2.59 (3.55) | −0.009 (−0.030) | 5/5 | 70 (27) |

  B = 700 (n00U/n02X no limite a 600): QEM 700, fairness 23.4 (24.7), p95 0.71 (1.18), máx 2.00 (2.74); remesh 673 tris, fairness 10.6 (17.7),
  p95 1.38 (1.53), máx 2.68 (**4.04**), IoU pior −0.036 (hfoo); remesh + QEM 700, fairness 14.5 (19.4), p95 1.35 (1.54), máx 2.27 (2.78), IoU
  pior −0.042; + features fairness 19.3, slivers até 6.1 %; guiado fairness 11.7 (19.1). Faixa 60–100° em 10–20 %: remesh 6.2–20.0 % (B 600:
  4/5 dentro, só o n005 6.2 abaixo; n00U 20.0 na borda), QEM 20.6–27.1 (0/5).
  Remesh por unidade, B = 600: n005 570 tris, fairness 7.8, p95 1.34 / máx 2.11, IoU −0.007; n00U 578, **20.1**, **1.61 / 3.31**, +0.003; hfoo 574,
  8.7, 1.34 / 2.15, **−0.056** (left); n017 572, 12.1, 1.55 / 2.72, **−0.014**; n02X 570, 11.7, 1.50 / 2.26, +0.001. Slivers 0 e euler = o da
  entrada (0/12/0/0/8) em todas.
- **Aceite do plano (fairness ≤ 15°, slivers < 2 %, p95 ≤ H/64 = 1.56 %, máx ≤ H/32 = 3.13 %, IoU ≥ raw −0.01), remesh a 600.** Slivers 5/5;
  fairness 4/5 (n00U 20.1); p95 4/5 (n00U 1.61); máx 4/5 (n00U 3.31); IoU 3/5 (hfoo −0.056, n017 −0.014). Passam todos os critérios só
  n005 e n02X (2/5). O QEM passa tudo menos fairness (24, 0/5) e a faixa de nd. **O híbrido não fecha a conta** (fairness 15.4, máx 4.10 no n00U).
- **Decisão: `METHOD = "qem"` (default inalterado), remesh/hybrid/guided opt-in via `retopo(method=)`.** O remesh dá o que o QEM não dá
  (fairness 24 → 12, triângulos equiláteros, sem sliver, nd 34 → 30, faixa 60–100 mais perto de 10–20 %), mas paga com desvio e silhueta: um L uniforme não
  segue facetas nem ossos finos (n00U: 8 pernas finas, p95/máx acima do teto), arredonda as quinas das armaduras caixa (`history/2026-10-29-l10-remesh/<id>.png`: clay
  QEM em cima | remesh embaixo; hfoo/n00U mostram o look "caixa facetada" virar "bolha") e o hfoo `left` perde 0.056 de IoU contra a folha. Pelos números
  é 2/5 unidades no aceite; sem o aceite o default não muda. **Juiz `review_pair` (eixo forma ≥ 3/5) NÃO rodado:** compara duas runs texturizadas e o retopo
  ainda não está ligado ao `build_unit` (L10-5/L10-7); decisão só pelos números e pela inspeção visual do clay. Se o L10-7 ligar o retopo, repetir com juiz
  em `remesh + QEM` (candidato) × QEM.
- **Negativos / experimentos.** (1) *Tamanho adaptativo por curvatura* (L = √(8ε/κ), κ = maior |autovalor| do Hessiano do campo por 19 pontos, ε seguindo a
  contagem; removido): p95 1.5/3.5/2.9 % em n005/n00U/n017, 4–5 % de slivers no n00U/n017, 6–25× mais lento (as quinas da união fazem κ explodir e comem o orçamento).
  (2) *Divisão por sag* (dividir a aresta cujo ponto médio está a > ε do zero): n00U 1624–2726 tris a 0.7–1 % de H: o orçamento não aguenta. (3) *Guiado*
  (campo de tamanho do QEM): sdf_dev igual ao remesh uniforme (o desvio vem de não alinhar com as facetas, não da densidade) e 5× mais lento (distância
  densa aos vértices do guia, até 27 s no n00U). (4) *QEM + flips/relax com guarda de desvio* (tol 1 %, 4–8 passes, 0.06–0.12 s; não implementado, só experimento):
  fairness 24 → 14–25 (n005 13.6, hfoo 16.7, n017/n02X 19.5, n00U 24.6), p95 0.46–0.85 → 1.0–1.5 %: está na mesma curva fairness × desvio, e o n00U não sai de 24.
  (5) *Features 35° no remesh:* igual ao L10-3, mais slivers (até 6.3 %) e máx 3.2 %: corpos facetados têm arestas vivas demais para o orçamento.
  (6) *Sem a guarda de desvio no collapse/relax* (`max_dev` 2 %): fairness 5–7 (n00U 7.4) mas p95 1.55/2.87/1.64/2.26/2.02 e máx n00U 5.55 %; o botão
  fairness × desvio é o `max_dev`. Sem pontos de projeção, a malha densa openvdb tem fairness 21 (a grade a 45°): o QEM herda isso, o remesh não.
- **Testes.** `test_retopo.py::Remesh` (4, +0.8 s): esfera densa → ±10 % do alvo, fairness < 15, 0 slivers, euler 0, manifold; cubo com `features=35` → os 8 cantos
  ficam a ≤ `max_dev`; projeção leva os vértices a |d| < 1e-6 e reduz o |d| médio; `retopo` fecha o orçamento nos 4 métodos com euler 0.

### 28.L10-7 `build_unit.BODY = "sdf"`: o corpo SDF no pipeline (`--body sdf|union|join`)
- **O que mudou.** `build_unit.BODY = "union" | "sdf" | "join"` (constante + `body=` na linha de comando; `body_flags` deriva `UNION_BODY` e
  `NOUNION`; a linha `UNION_BODY = True` fica, o `spec_pipeline` lê `BODY` por regex como lia `UNION_BODY`; a palavra antiga `nounion` = `body=join`).
  `main()`, ramo `sdf` no lugar de `union_body()`: `sdf_union` = `sdf_dense` (campo → openvdb → solda) → `sdf_retopo` (`retopo.reduce` com `grid_sdf` no
  laço, `Field.d` no polish, `max_dev` H/50, alvo B = orçamento − tris dos props/flame/peças mantidas, piso `UNION_FLOOR` 0.9 do orçamento)
  → `skin_sdf` **depois** da retopo (pesos e materiais saem das posições finais: um passo só, sem recomputar) → `soften` 35° como na união →
  props/flame como componentes à parte (lista `keep`) → UVs/atlas/merge (ver abaixo) → export. `sdf_body_object` continua (denso + pele; o `sdf_extract skin=1`).
  `attach.json["union"]` = `method: sdf`, `grid`, `k`, `adaptivity`, `thin`, `kept`, `inflated`, `voxel`, `dense_tris`, `tris`, `components_body`, `props`,
  `retopo` (o relatório do `reduce`), `seconds`; grava `clay.sdf.json` (o campo, que o `mesh_lint` lê; uma build `union` apaga um `clay.sdf.json` velho).
  Argumentos: `sdf_grid=96 sdf_adapt=0 sdf_k=1 sdf_thin=off|inflate|keep` (`SDF_*` em `build_unit.py`). `spec_pipeline --body sdf|union|join`
  (`args.union_body = BODY != "join"`; `clay_args` passa `body=` só quando difere do default; `colour_stage.build_textured` passa `body=`);
  deform + optimize_verts rodam sobre a malha SDF sem mudança (pegam o maior componente). **Default continua `union`** (decide a bateria v13 = L10-9).
- **Peça fina (§3 do plano).** `sdf_body.thin_inflation(parts, voxel)` (pura): peça com `2 r < 2 voxels` → `d − max(0, (2.5·voxel − t)/2)`;
  `sdf_body.field(..., thin="off"|"inflate"|"keep")`: *inflate* abaixa o `d` da peça (campo e malha), *keep* tira a peça do campo (`Field.kept`) e a
  build a mantém poligonal e skinada na âncora, como um prop. Medido com `spec_pipeline.trial` (build clay + silhouette, sem deform), specs `v10-r1` (não há v11 de n00H/n010):

| unidade | peças < 2 vox | política | IoU f/l/b/top/bot/rts | média | red | forma (sliver+nd/90) | tris (corpo + mantidas) | sliver % |
|---|---|---|---|---|---|---|---|---|
| n00H | 4 (2 anéis, 2 pratos) | união | .824/.647/.814/.697/.663/.484 | .688 | .227 | .667 | 629 | 20.0 |
| n00H | | off | .846/.666/.841/.710/.662/.512 | .706 | .209 | .419 | 695 | 0.6 |
| n00H | | **inflate** | .850/.636/.853/.686/.639/.556 | .703 | .220 | .420 | 696 | 1.1 |
| n00H | | keep | .861/.648/.848/.685/.651/.486 | .697 | .231 | .517 | 471 + 229 | 7.6 |
| n010 | 1 (prato) | união | .714/.836/.586/.452/.454/.673 | .619 | .273 | .687 | 630 | 16.3 |
| n010 | | off / **inflate** | .717/.841/.582/.445/.452/.692 | .622 | .277 | .506 | 700 | 0.0 |
| n010 | | keep | .718/.842/.583/.445/.450/.692 | .622 | .277 | .512 | 684 + 16 | 0.1 |

  **Decisão: `inflate` é o default (`SDF_THIN`).** Mantém a peça no campo (nada de peça que o openvdb perde por amostragem), custa 0 tris, e a
  forma fica igual à de `off` (sliver ≤ 1.1 %); `keep` gasta 229 de 700 tris em anéis/chain poligonais no n00H e o corpo ficou grosseiro (sliver 7.6 %,
  forma .517, IoU médio −.009). Os números de IoU entre off/inflate/keep andam ±0.03 por vista sem tendência: a evidência é n00H + n010 (2 unidades) e
  as 5 do v12 **não têm** peça < 2 voxels (a mais fina: 2.7 voxels, a cabeça-frustum do n017), então no lote das 5 a política não muda nada (`inflated: []`).
  `off` empatou em IoU no n00H; fica como ablação. Reavaliar com a bateria v13 se houver peça fina (asas do n00H têm 1.9–3.5 voxels).
- **k por junta (`sdf_k=0 / 1 / 2`, 5 unidades, `trial`, 96³, a0).** IoU médio das 6 vistas (união → k0 / k1 / k2): n005 .816 → .819 / .821 / .819;
  n00U .722 → .732 / .735 / .734; hfoo .641 → .641 / .632 / .640; n017 .761 → .765 / .763 / .763; n02X .743 → .748 / .748 / .748. nd médio: k2 é
  0.5–1.5° menor que k1 (n005 30.7 vs 31.9, n00U 39.8 vs 40.6, hfoo 33.1 vs 34.5, n017 31.1 vs 32.6) e a `uncovered` média cai 0–0.003; slivers 0–2.3 % em
  todos. Diferenças ≤ 0.003 de IoU: **k = 1 fica** (o desenho do L10-1; `k2` é o candidato se a bateria v13 quiser nd menor, `k0` não ganha em nada).
- **Prova nas 5 unidades (sem LLM)** `spec_pipeline.py --id <id> --rig <rig> --kind mass --spec runs/draft/<id>/v12-r1/spec.json --shape-only --no-repair --no-diagnose
  --run l10-body-{union,sdf} --body union|sdf` (deform + `--fit-verts` default; 2 processos; runs em `runs/draft/<id>/l10-body-{union,sdf}/`). IoU aprovado, raster duro.

| unidade | corpo | f / l / b | top / bot / rts | uncov / spill (média 6) | sliver % (cru → final) | nd | `sdf_dev` p95 % H (cru → final) | euler | comp | tris | verts: passos / unsafe / worse | build s | total s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| n005 | união | .910 / .941 / .914 | .770 / .821 / .877 | .065 / .074 | 8.7 → 10.0 | 43.5 | .35 → 2.26 | 0 | 1 | 630 | 24 / 0 / 51 | – | 102 |
| n005 | **sdf** | .907 / **.949** / **.926** | .764 / **.841** / **.890** | .062 / .068 | 0.0 → 1.4 | 34.0 | .49 → 2.53 | 0 | 1 | 700 | 27 / 0 / 32 | 1.1 | 103 |
| n00U | união | .874 / .771 / .877 | .743 / .731 / .693 | .070 / .171 | 18.2 → 17.9 | 51.8 | 1.13 → 2.47 | 40 | 2 | 627 | 24 / 0 / 9 | – | 266 |
| n00U | **sdf** | **.889 / .805 / .890** | **.764 / .739 / .706** | .063 / .157 | 0.0 → 0.3 | 45.9 | 1.05 → 2.82 | 16 | 2 | 699 | 27 / 0 / 18 | 3.6 | 276 |
| hfoo | união | .832 / .658 / .839 | .691 / .735 / .644 | .164 / .135 | 21.7 → 21.0 | 49.4 | .35 → 3.89 | 0 | 1 | 630 | 33 / 0 / 43 | – | 118 |
| hfoo | **sdf** | **.849 / .659 / .853** | .688 / .723 / .639 | .177 / .121 | 2.3 → 5.7 | 38.6 | .40 → 3.90 | 0 | 1 | 700 | 31 / 0 / 57 | 1.0 | 117 |
| n017 | união | .894 / .760 / .839 | .810 / .880 / .704 | .089 / .115 | 28.3 → 26.3 | 49.4 | .48 → 2.67 | 0 | 1 | 630 | 29 / 0 / 57 | – | 115 |
| n017 | **sdf** | **.915 / .797 / .865** | .807 / **.889** / .693 | .082 / .106 | 1.7 → 4.6 | 37.6 | .81 → 3.69 | 0 | 1 | 700 | 28 / 0 / 82 | 1.9 | 121 |
| n02X | união | .884 / .883 / .899 | .752 / .735 / .781 | .082 / .114 | 17.2 → 16.9 | 54.6 | .66 → 3.82 | 7 | 1 | 629 | 27 / 0 / 31 | – | 106 |
| n02X | **sdf** | **.893 / .896 / .906** | .757 / **.746** / **.804** | .077 / .105 | 1.7 → 4.7 | 43.4 | .69 → 5.83 | 8 | 1 | 700 | 30 / 0 / 39 | 2.0 | 107 |

  `--body union` byte-idêntico ao código anterior: `build_unit` do HEAD (`git archive`) e o atual, mesmos argumentos, `clay.glb` e `attach.json`
  iguais com `cmp` nas 5 unidades; o `union` do `spec_pipeline` reproduz o v12 (n005 .910/.941/.914 contra .903/.944/.916 da ablação `both`: o spec final já vem do fit).
  `comp` = `components_body` (n00U: 2 nas duas, as pernas finas da aranha; o `trial` clay sem deform dá 1 no sdf e 2 na união). Tempo total = pipeline inteiro
  (deform, `--fit-verts` ≈ 31 s, silhouette/render); o build do corpo SDF é 1–3.6 s (60 s de teto).

  Esticão p99.5 dos clipes no clay final (`anim_check`, união → sdf): n005 walk 2.61 → 2.34, attack 2.05 → 1.33, death 2.82 → 1.73; n00U 1.56 → 1.28 /
  1.63 → 1.41 / 6.20 → 3.66; hfoo 2.24 → 2.06 / 2.12 → 1.93 / 2.16 → 1.95; n017 **1.85 → 1.93** / 2.80 → 1.55 / 3.64 → 2.40; n02X 4.40 → 3.38 / 3.08 → 1.87 / 3.16 → 1.77:
  sdf ≤ união em 14 de 15 (a exceção, n017 `walk`, 1.04×; os números absolutos são do corpo deformado pelo fit, não do §28.L10-5).
- **Aceite.** IoU f/l/b ≥ v12 −0.01: 5/5 (o pior, n005 front −0.003; **left ≥ v12 em 5/5**, mais 0.001 a 0.037; rts ≥ em 3/5, n017 −0.011 e hfoo −0.005; IoU médio das 6
  vistas +0.008 / +0.018 / +0.002 / +0.013 / +0.012). Slivers finais < 5 %: 3/5 (n005 1.4, n00U 0.3, n017 4.6, n02X 4.7) e **hfoo 5.7 %** (2.3 % cru; deform e `optimize_verts` os
  recriam, união 21 %); todos os crus < 2.3 %. nd −5.9 (n00U) a −11.8° (n017). Build ≤ 60 s: 5/5 (1–3.6 s). `--body union` idêntico: 5/5.
  **`unsafe` −50 %: não mensurável**, a união já tem `unsafe` 0 nas 5 (0 → 0). O que o `optimize_verts` recusa por piora do objetivo (`worse`) soma 191 (união) → 228 (sdf) e os
  passos aceitos 137 → 143: **sem melhora medida** no otimizador de vértices (o ganho do sdf está no cru, não no que o fit recupera).
  `sdf_dev` final p95 igual ou pior (2.5–5.8 % H contra 2.3–3.9): o fit puxa a malha ao sheet, que é o que ele deve fazer; o cru (antes do deform) fica em 0.4–1.0 % H.
- **UV / atlas (T1, T5) sobre materiais por face: confirmado.** Build `tex style=cel cel_atlas=compact materials=merge body=sdf` (n005 / n017): atlas 32×64 / 16×64
  (como a união), `materials merged: 7 -> 2` / `4 -> 1`, `images 1`, `uv_out_of_range 0`, `mesh_lint` sem gate falhando (a união falha o gate `sliver_pct < 5` nas duas: 8.7 / 33.1 %). As UVs vêm da
  geometria (parte mais próxima, normal), não da junção das peças: não dependem de como o corpo foi feito.
- **Negativos / limites.** (1) O corpo SDF gasta o orçamento todo (700 com props; a união parava em 625–630 pela tolerância); o gate de tris passa (≤ 700) sem folga. (2) `unsafe` não
  discrimina (0 → 0). (3) A política de peça fina foi medida só em n00H/n010 sem deform; as asas (1.9–3.5 voxels) precisam da bateria v13 com LLM. (4) glTF guarda 4 influências por vértice
  (o `skin_sdf` pode dar mais; aviso do exportador, mesmo efeito do §28.L10-5). (5) Sem `--body sdf` no `fit_stage` (o `fit_spec` ainda constrói em união) nem nos builds de ID/zonas (`zones_clay`, `propid`): o ID
  render de zonas e o fit usam a união; só o clay final e o texturizado usam `body=`.
- **Recomendação de default.** `sdf` como default na v13 (L10-9): IoU ≥ união em f/l/b 5/5, slivers crus ≤ 2.3 % e finais 0.3–5.7 %, nd −6 a −12°, componentes iguais ou menores, esticão ≤ união, build 1–4 s.
  Condição aberta: hfoo 5.7 % (> 5 %) e `unsafe` sem efeito. **Não mudei o default.**
- **Testes.** `tests/tools/blender/test_body_sdf.py` (7, < 1 s; `SLOW=1` + Blender: n005 `body=sdf` fecha `mesh_lint`: 1 pele, `components_body` 1, 0 borda/non-manifold/flipped, sliver < 5, tris ≤ 700, `attach.json["union"]` e
  `clay.sdf.json`): `BODY` deriva `UNION_BODY`/`NOUNION`, a linha `UNION_BODY = True` e o `DEFAULT_BODY` do `spec_pipeline`, `sdf_args`, `--body` chega a `clay_args` e `colour_stage.body_args`, política de peça fina numa cena sintética
  (caixa + prato de 0.004: `thin_inflation`, off/inflate/keep, voxels internos a mais).

### 28.L10-8 Robustez em lote: `sdf_batch.py` (`--body sdf` × `union` em todos os specs, sem LLM)
- **O que mudou.** `tools/blender/sdf_batch.py` (ferramenta de regressão permanente): `python3.14 tools/blender/sdf_batch.py [--units a,b] [--body sdf,union] [--jobs 2]
  [--grid 128] [--no-anim] [--collect-only] [--compare DIR] [--json F]`. Descobre o spec mais recente de cada unidade (`runs/draft/<id>/v12-r1`, senão `v11-r1`, `v10-r1`; `n01I`/`n01N`
  só têm `v2-hard-r2`; `h09B` é building e fica de fora), roda `spec_pipeline.py --kind mass --shape-only --no-repair --no-diagnose --spec <spec> --body <b>` (rig lido do spec,
  câmeras top/bottom/rts **fixadas** nas do `silhouette.json` da origem com `--tilts`, para sdf e união medirem nas mesmas câmeras) em `runs/draft/<id>/l10-batch-{sdf,union}[g<N>]/`
  (`batch.log`, `batch.json`; o diretório de uma bateria anterior é apagado antes: o pipeline reusa `fit/` e `spec.json` de um run existente e o resultado deixava de ser o do spec de origem,
  n00H/n010/n01N se mexeram 0.03–0.2 de IoU entre duas execuções), mede (`silhouette.json`, `attach.json`, `mesh_lint.lint(sdf=True)` do `clay.glb` e do `clay-raw.glb`,
  `anim_check.py` = esticão p99.5 de `walk/attack/death`, triângulos por `plate` por ownership no campo) e imprime as tabelas em markdown + `runs/draft/l10-batch.json`
  (`rows` + `acceptance`; 128³: `l10-batch-g128.json`). Falha de build = linha `FAIL` com a causa (última exceção do traceback + frame). Novas flags no `spec_pipeline`:
  `--tilts top:10,bottom:20,rts:55/-60` (só o silhouette `approved`) e `--sdf-grid N` (`build_unit sdf_grid=`). `tools/blender/anim_check.py` (o script de esticão da sessão, agora versionado).
  Lotes de ~25 min (2 processos; 96 s–275 s por run, quase tudo é deform + `--fit-verts`).
- **Unidades.** Existem **10** (não 17): os 17 *specs* são as versões v10/v11/v12 de 8 unidades (hfoo, n005, n00H, n00U, n010, n017, n01X, n02X), mais n01I e n01N (`v2-hard-r2`, sem v1x),
  que entram como extras; `h09B` (building) não. 10/10 constroem (nenhuma falha de build, nenhuma causa a corrigir).
- **Bug do pipeline corrigido (n00U).** Uma peça que o fit encolheu a 0.3 voxel (parte 33) deixava uma ilha de 12 triângulos no campo (`components_body` 2 nas duas, e a
  retopo a reduzia a 1 triângulo solto). `build_unit.drop_specks` (em `sdf_dense`, `SDF_SPECK = 2` voxels de diagonal, nunca a maior peça; `attach.json["union"]["specks"]` = triângulos
  removidos): n00U 2 → 1 componente; as outras 9 unidades têm `specks` 0 (resultado igual ao da primeira bateria).
- **Tabela (96³, sdf × união, mesmo spec e mesmas câmeras).** build s = só o corpo SDF; total s = o pipeline todo; sliver = cru → final (deform + `optimize_verts`); thin = peças < 2 voxels
  (`inflate` em ação); plates (0 tris, enterradas) = triângulos por `plate` por ownership; gates = `mesh_lint.failing` + silhouette `GATES` do rig.

| unit | rig | body | build s | total s | tris | sliver % (raw→final) | nd | sdf_dev p95 / max % H | euler | comp | IoU f/l/b/top/bot/rts | unc / spill | thin (<2 vox) | plates (0 tris, buried) | walk p99.5 | gates |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hfoo | biped | sdf | 1.0 | 116.5 | 700 | 2.3 → 5.7 | 38.6 | 3.90 / 7.66 | 0 | 1 | .849 / .659 / .853 / .688 / .723 / .635 | 0.171 / 0.126 | 0 (0 inflated) | 0 (0, 0) | 2.06 | FAIL sliver_pct < 5, sil:rts |
| hfoo | biped | union | – | 117.2 | 630 | 21.7 → 20.8 | 49.5 | 3.90 / 8.42 | 0 | 1 | .826 / .659 / .831 / .695 / .739 / .644 | 0.163 / 0.138 | 0 (0 inflated) | 0 (0, 0) | 2.24 | FAIL flipped == 0, sliver_pct < 5, sil:rts |
| n005 | biped | sdf | 1.1 | 101.8 | 700 | 0.0 → 1.4 | 34.0 | 2.53 / 5.61 | 0 | 1 | .907 / .949 / .926 / .762 / .841 / .890 | 0.056 / 0.075 | 0 (0 inflated) | 0 (0, 0) | 2.34 | PASS |
| n005 | biped | union | – | 101.0 | 630 | 8.7 → 10.0 | 43.5 | 2.26 / 4.70 | 0 | 1 | .910 / .941 / .914 / .764 / .821 / .876 | 0.059 / 0.080 | 0 (0 inflated) | 0 (0, 0) | 2.61 | FAIL sliver_pct < 5 |
| n00H | wyrm | sdf | 1.0 | 159.3 | 700 | 0.0 → 0.1 | 37.9 | 5.56 / 8.60 | 8 | 3 | .857 / .851 / .858 / .762 / .694 / .407 | 0.170 / 0.146 | 4 (4 inflated) | 5 (0, 0) | 1.84 | FAIL components_body == 1, sil:rts |
| n00H | wyrm | union | – | 155.0 | 629 | 13.7 → 16.2 | 49.4 | 4.80 / 8.59 | 7 | 4 | .868 / .760 / .872 / .728 / .699 / .415 | 0.162 / 0.174 | 0 (0 inflated) | 5 (0, 0) | 2.51 | FAIL components_body == 1, sliver_pct < 5, sil:rts |
| n00U | spider | sdf | 3.5 | 274.6 | 700 | 0.0 → 0.1 | 46.4 | 2.48 / 7.65 | 16 | 1 | .888 / .783 / .892 / .743 / .740 / .689 | 0.067 / 0.165 | 0 (0 inflated) | 0 (0, 0) | 1.34 | FAIL abs(min_y) <= 0.01 H, sil:rts |
| n00U | spider | union | – | 265.0 | 626 | 18.4 → 17.3 | 53.4 | 2.35 / 6.90 | 41 | 2 | .874 / .779 / .877 / .748 / .729 / .690 | 0.076 / 0.164 | 0 (0 inflated) | 0 (0, 0) | 1.69 | FAIL abs(min_y) <= 0.01 H, components_body == 1, sliver_pct < 5, sil:rts |
| n010 | drake | sdf | 1.6 | 249.8 | 700 | 0.0 → 0.1 | 40.6 | 1.98 / 3.80 | 4 | 1 | .863 / .910 / .677 / .450 / .469 / .457 | 0.275 / 0.172 | 1 (1 inflated) | 5 (0, 1) | 2.12 | FAIL sil:back, sil:top, sil:bottom, sil:rts |
| n010 | drake | union | – | 249.2 | 630 | 12.7 → 11.1 | 50.2 | 1.80 / 5.74 | 16 | 1 | .818 / .907 / .676 / .449 / .462 / .470 | 0.277 / 0.177 | 0 (0 inflated) | 5 (0, 1) | 2.01 | FAIL sliver_pct < 5, sil:back, sil:top, sil:bottom, sil:rts |
| n017 | quadruped | sdf | 1.9 | 120.1 | 700 | 1.7 → 4.6 | 37.7 | 3.70 / 7.50 | 0 | 1 | .920 / .797 / .859 / .805 / .889 / .694 | 0.082 / 0.107 | 0 (0 inflated) | 0 (0, 0) | 1.93 | FAIL sil:rts |
| n017 | quadruped | union | – | 116.1 | 630 | 28.3 → 26.3 | 49.5 | 2.67 / 6.19 | 0 | 1 | .896 / .760 / .841 / .799 / .881 / .704 | 0.088 / 0.117 | 0 (0 inflated) | 0 (0, 0) | 1.85 | FAIL sliver_pct < 5 |
| n01I | biped | sdf | 2.0 | 163.4 | 700 | 1.4 → 0.0 | 44.4 | 2.73 / 7.05 | 0 | 2 | .885 / .765 / .816 / .806 / .739 / .800 | 0.092 / 0.128 | 0 (0 inflated) | 0 (0, 0) | 3.47 | FAIL components_body == 1 |
| n01I | biped | union | – | 160.6 | 630 | 18.1 → 15.2 | 49.7 | 1.96 / 5.24 | 0 | 2 | .857 / .743 / .810 / .775 / .746 / .802 | 0.101 / 0.134 | 0 (0 inflated) | 0 (0, 0) | 3.12 | FAIL components_body == 1, sliver_pct < 5 |
| n01N | spider_high | sdf | 3.4 | 268.9 | 700 | 0.3 → 0.1 | 52.4 | 3.56 / 6.68 | 4 | 1 | .784 / .469 / .781 / .602 / .611 / .634 | 0.185 / 0.251 | 0 (0 inflated) | 0 (0, 0) | 1.66 | FAIL sil:left, sil:top, sil:bottom, sil:rts |
| n01N | spider_high | union | – | 257.6 | 630 | 32.5 → 31.9 | 54.7 | 4.50 / 7.75 | 0 | 1 | .746 / .478 / .743 / .598 / .602 / .577 | 0.180 / 0.283 | 0 (0 inflated) | 0 (0, 0) | 2.85 | FAIL sliver_pct < 5, sil:left, sil:top, sil:bottom, sil:rts |
| n01X | biped | sdf | 1.1 | 99.9 | 700 | 0.3 → 0.7 | 40.5 | 2.66 / 6.10 | 4 | 1 | .880 / .922 / .883 / .893 / .901 / .859 | 0.042 / 0.074 | 1 (1 inflated) | 0 (0, 0) | 2.20 | PASS |
| n01X | biped | union | – | 96.5 | 629 | 11.6 → 8.3 | 48.1 | 2.93 / 5.55 | 13 | 2 | .870 / .908 / .872 / .900 / .891 / .846 | 0.045 / 0.081 | 0 (0 inflated) | 0 (0, 0) | 2.21 | FAIL components_body == 1, sliver_pct < 5 |
| n02X | biped | sdf | 2.0 | 109.1 | 700 | 1.7 → 4.7 | 43.4 | 5.79 / 9.46 | 8 | 1 | .889 / .896 / .905 / .744 / .748 / .805 | 0.081 / 0.105 | 0 (0 inflated) | 1 (0, 0) | 3.38 | PASS |
| n02X | biped | union | – | 107.8 | 629 | 17.2 → 16.5 | 54.7 | 3.88 / 7.27 | 7 | 1 | .880 / .884 / .896 / .749 / .738 / .787 | 0.078 / 0.116 | 0 (0 inflated) | 1 (0, 0) | 4.36 | FAIL sliver_pct < 5 |

  sdf − união (IoU por vista, slivers finais, nd, componentes, esticão walk p99.5):

| unit | rig | ΔIoU f/l/b/top/bot/rts | Δ mean | Δ sliver % | Δ nd ° | comp (union → sdf) | walk p99.5 (union → sdf) |
|---|---|---|---|---|---|---|---|
| hfoo | biped | 0.023 / -0.000 / 0.022 / -0.007 / -0.016 / -0.009 | 0.002 | -15.1 | -10.9 | 1 → 1 | 2.24 → 2.06 |
| n005 | biped | -0.003 / 0.008 / 0.012 / -0.002 / 0.020 / 0.014 | 0.008 | -8.6 | -9.5 | 1 → 1 | 2.61 → 2.34 |
| n00H | wyrm | -0.012 / 0.091 / -0.014 / 0.034 / -0.005 / -0.007 | 0.015 | -16.1 | -11.4 | 4 → 3 | 2.51 → 1.84 |
| n00U | spider | 0.014 / 0.004 / 0.016 / -0.005 / 0.011 / -0.001 | 0.006 | -17.2 | -7.1 | 2 → 1 | 1.69 → 1.34 |
| n010 | drake | 0.045 / 0.003 / 0.001 / 0.001 / 0.007 / -0.013 | 0.008 | -11.0 | -9.6 | 1 → 1 | 2.01 → 2.12 |
| n017 | quadruped | 0.024 / 0.037 / 0.018 / 0.006 / 0.008 / -0.010 | 0.014 | -21.7 | -11.8 | 1 → 1 | 1.85 → 1.93 |
| n01I | biped | 0.028 / 0.022 / 0.006 / 0.031 / -0.008 / -0.002 | 0.013 | -15.2 | -5.4 | 2 → 2 | 3.12 → 3.47 |
| n01N | spider_high | 0.038 / -0.009 / 0.038 / 0.003 / 0.008 / 0.057 | 0.023 | -31.8 | -2.2 | 1 → 1 | 2.85 → 1.66 |
| n01X | biped | 0.010 / 0.014 / 0.011 / -0.007 / 0.010 / 0.013 | 0.009 | -7.6 | -7.6 | 2 → 1 | 2.21 → 2.20 |
| n02X | biped | 0.009 / 0.012 / 0.008 / -0.005 / 0.011 / 0.018 | 0.009 | -11.8 | -11.3 | 1 → 1 | 4.36 → 3.38 |

  Esticão p99.5 `attack` / `death` (união → sdf): hfoo 2.12 → 1.93 / 2.16 → 1.95; n005 2.05 → 1.33 / 2.82 → 1.73; n00H 2.94 → 2.57 / 1.79 → 1.74; n00U 1.75 → 1.39 / 7.19 → 4.17;
  n010 2.35 → 2.19 / 3.49 → 2.94; n017 2.80 → 1.54 / 3.64 → 2.40; n01I 2.34 → 2.98 / 4.17 → 4.56; n01N 21.5 → 9.3 / 19.0 → 11.2; n01X 2.35 → 2.49 / 1.64 → 1.89; n02X 3.07 → 1.87 / 3.07 → 1.77.
  sdf ≤ união em 23 de 30 (walk 7/10; as 7 exceções: n010 walk +6 %, n017 walk +4 %, n01I walk +11 % / attack +27 % / death +9 %, n01X attack +6 % / death +15 %); n01N attack/death 9–11× nas duas
  é do rig `spider_high` (clipes), não do corpo.
- **Aceite (por rig).** Build médio **1.9 s** (máx 3.5 s, n00U) contra ≤ 15 / 30 s: ok. 10/10 constroem.

| unit | rig | acceptance |
|---|---|---|
| hfoo | biped | sliver 5.7 % >= 5.0 |
| n005 | biped | nd 33.99 > union 43.49 - 10 |
| n00H | wyrm | ok |
| n00U | spider | rts 0.6888 < union 0.6897 |
| n010 | drake | ok |
| n017 | quadruped | ok |
| n01I | biped | nd 44.36 > union 49.71 - 10 |
| n01N | spider_high | ok |
| n01X | biped | nd 40.46 > union 48.06 - 10 |
| n02X | biped | ok |
| * | all | ok |

- **Causas (uma linha por unidade fora do aceite).**
  - **hfoo** (biped, sliver 5.7 % ≥ 5): *deform / optimize_verts*. Cru 2.3 %; o fit puxa vértices ao sheet e recria os slivers (já em §28.L10-7; união 20.8 %).
  - **n005** (biped, nd −9.5° em vez de −10°): *retopo (QEM) + deform*. nd cru 31.9 contra 37.9 da união (−6.1°); o fit reabre o gap; falta 0.5°. Alavanca conhecida: `sdf_k=2` (−0.5…−1.5° de nd, §28.L10-7), não ligada ao `spec_pipeline`.
  - **n01X** (biped, nd −7.6°) e **n01I** (biped, nd −5.4°): *retopo + deform*, idem n005 (nd cru 36.4 / 41.9 contra 41.5 / 44.4 da união: o ganho cru já é só −5.1 / −2.6°). O aceite de nd −10° foi medido nas 5 unidades do v12 (L10-3), não é uma propriedade de qualquer spec.
  - **n00U** (spider, rts .6888 contra .6897 da união, −0.0009): empate dentro do ruído do fit (`components_body` 1, passou depois do `drop_specks`); falha só pela comparação estrita. IoU médio +0.006.
  - Passam: n00H (wyrm: 5/5 plates com triângulos, left +0.091, top +0.034), n010 (drake: 5 plates, 1 enterrada, left −0.000, top +0.001), n017 (quadruped: sliver 4.6 %), n01N (spider: comp 1, rts +0.057), n02X, e
    os gates de forma só de silhueta (rts, top/bottom do n010/n01N) que **a união também falha** (spec do autor, não o corpo).
  - Não são do corpo SDF (a união tem o mesmo): **n010 plate 7 = 0 triângulos** (a peça está dentro das outras: d das outras < −1 voxel nos 27 pontos da sua caixa; é *spec*, 1 enterrada e nenhuma
    perdida por amostragem); **n01I `components_body` 2** (a peça 0, 240 triângulos densos, está solta no spec); **n00H `components_body` 3** a 96³ (as duas asas, `wing1/wing2`, não tocam o corpo
    no spec; união 4); **n00U `abs(min_y) <= 0.01 H`** (pivô do spec/fit).
- **96³ × 128³ (wyrm / drake, sdf).** `l10-batch-g128.json`: n00H 128³ f/l/b/top/bot/rts .899/.777/.892/.761/.685/.401, comp **1** (as asas passam a tocar), slivers 0.0 → 0.0, nd 36.1, build 1.6 s,
  2 peças < 2 voxels (4 a 96³); 96³ .857/.851/.858/.762/.694/.407, comp 3. n010 128³ .846/.914/.663/.459/.480/.479 contra 96³ .863/.910/.677/.450/.469/.457, build 2.6 s contra 1.6 s, a mesma plate enterrada.
  Left/top ≥ união −0.01 nos dois tamanhos (união n00H left .760 / top .728; n010 .907 / .449). 128³ junta as asas do n00H (comp 1), top igual (.761), mas left cai de .851 para .777 (ainda +.017 sobre a união)
  e rts .401 (união .415, 96³ .407): **96³ fica**; 128³ é o botão quando um wyrm precisa de 1 componente.
- **Peças finas.** `inflate` em ação: n00H 4 peças < 2 voxels (2 anéis, 2 pratos; slivers 0.1 %, todas as 5 plates com triângulos), n010 1 (o prato), n01X 1 (sliver 0.7 %). Nenhuma
  peça perdida. Os outros 7 não têm peça < 2 voxels.
- **Testes.** `tests/tools/blender/test_sdf_batch.py` (7 sem Blender, < 0.1 s: `discover`, `tilts_arg`/`command`, `cause_of`, `make_row`, tabelas, aceite por rig, regra de tempo; `SLOW=1`: n010 de ponta a ponta, 1 unidade).
  `test_body_sdf.py` continua OK. Ruff (C901,F,E9, ≤ 10) limpo em `sdf_batch.py`/`spec_pipeline.py`; `build_unit.py` com os mesmos 7 achados antigos.
- **Recomendação.** O corpo SDF constrói 10/10, em 1–3.5 s, com slivers finais 0.0–5.7 % (união 8–32 %), nd −2…−13° e componentes ≤ união em 10/10; as exceções de aceite são o nd −10° (n005/n01X/n01I)
  e o sliver do hfoo, ambas do estágio de deform/fit, não do corpo. A decisão do default continua no L10-9.

### 28.L10-9 Bateria v13 (autor LLM, `--body sdf`, pareada contra v12) e o default `BODY = "sdf"`
- **Protocolo.** 5 unidades (n005, n00U, hfoo, n017, n02X), `spec_pipeline.py --model session:opus --kind mass --run v13-r1
  --pair v12-r1 --body sdf` com os defaults da leva 8/9 (`fit-verts` ligado, `--fit-grad` desligado, atlas compacto, 1 material);
  4 processos + 1, `SOFT_SIL_THREADS=4`. Controle no mesmo spec: `--spec runs/draft/<id>/v13-r1/spec.json --body union --tilts
  <câmeras da v13>` → `v13-r1-union`, sem LLM, para separar corpo de spec. Imagens e tabelas completas em
  `history/2026-10-29-v13/README.md`; linhas v13 em `IA_gen_paper/results.csv`.
- **Bug achado e corrigido na primeira tentativa.** O pré-spec de massing (`massing_spec`) só levava `"rig"` para
  quadruped/wyrm/drake; a aranha construía como biped (preflight dizia `bones FAIL biped`), e a união engolia (grupo de vértices
  sem osso). Com `--body sdf` o `sdf_body.part_bones` estourava em `cols["body"]`, o build caía e `massing_stage` morria em
  `args.summary`. Correções: o pré-spec leva o rig de qualquer família; osso que o rig não tem cai no `root` (igual ao que a
  união fazia); `massing_stage` tolera build falhado (`getattr(args, "summary", {})`). Teste
  `Skin.test_a_bone_the_rig_lacks_rides_the_root`. Pasta da tentativa: `n00U/v13-r1-invalid`.
- **Resultado contra v12 (specs diferentes).** PASS 3/5 (n005, n017, n02X; v12 2/5). IoU f/l/b: n005 +.012/+.004/+.015, n00U
  +.026/+.004/+.027, hfoo +.015/−.244/+.015, n017 +.049/0/+.036, n02X +.022/−.048/+.021. Slivers finais 0.9–5.4 % (v12
  9–32 %), nd −5…−16°, gates de lint PASS em 3/5 (v12 0/5). Juiz (4 votos, A/B trocados): artista 4-0 pró v13 em 5/5, forma
  4-0 em 4/5 e 3-1 em 1/5, wc3 ≥ 3-1 em 4/5; sheet divide (hfoo 4-0 pró v12).
- **Controle no mesmo spec (união → sdf).** Média das 6 vistas: n005 −.002, n00U +.025, hfoo −.004, n017 +.003, n02X +.019.
  O hfoo left .415 é do spec (união .417: tronco e mochila à frente da linha do sheet); n02X left idem (união .838). As quedas
  reais do corpo SDF: rts −.031 (hfoo) e −.033 (n017), top −.022 (hfoo) — o `smin` engorda as juntas (peito/pernas do lobo:
  spill 21 → 24 % no rts). Componentes: n017 2 → 1; n00U 2 → 2 porque `leg6` do spec não toca o corpo (ilha de 6 tris no SDF,
  10 na união). Build do corpo 1.0–3.7 s (união 25–35 s).
- **Critérios do L10-9 e decisão.** PASS ≥ 3/5 ✓; slivers < 5 % em ≥ 4/5 ✓ (hfoo 5.4); juiz forma ≥ 3-1 em ≥ 3/5 ✓ (5/5);
  comp 1 em 5/5 ✗ (n00U: spec, igual na união); nenhuma vista cai > 0.01 ✗ (rts −.03 em 2/5 no mesmo spec). Decisão de líder:
  **`build_unit.BODY = "sdf"` default** — os dois critérios que faltam são um erro de spec e um custo de .03 numa vista
  oblíqua contra +.02 de média em 2 unidades, slivers 4× menores, nd −10° e lint limpo em 3/5; `--body union` continua
  disponível e byte-idêntico (L10-7). `spec_pipeline.DEFAULT_BODY` lê a linha por regex; `clay_args` só passa `body=` quando
  difere do default (testes `Flags` ajustados).
- **Aberto (Leva 11 ou L10-10).** (1) Engorda das juntas pelo `smin` (rts/top −.02…−.03): `k` por junta ou `k = 0` nas
  pernas, medir no controle `v13-r1-union`. (2) hfoo sliver 5.4 % e n005 nd −9.5° vêm do deform/fit-verts sobre a malha SDF.
  (3) Peça do spec sem contacto (n00U `leg6`, n01I, n00H): regra de preflight "toda peça do corpo toca o pai" ou ponte SDF.
  (4) `fit_stage`, zonas e propid continuam a usar a união (câmeras/IDs), inofensivo mas duplica build.

## 29. Leva 11 (2026-10-29)

Plano: `analysis/2026-10-29-leva11-vlm-loop.md`. O VLM só entra pelo laço guardado (aceite por rodada sem queda de vista).
Bateria `v14-r1` (5 unidades, autor session:opus, corpo sdf, `--loop 2`, pareada contra v13) em `history/2026-10-29-v14/`; controle
`v14-r1-clock` (mesmo spec, sem `--deterministic`); detalhe em 29.L11-4. IoU approved f/l/b · rts.

| unidade | v13 | v14 | veredito | laço tentados / aceites | juiz v14 × v13 (forma) |
|---|---|---|---|---|---|
| n005 | .921/.947/.932 · .878 | .923/.946/.934 · .886 | **PASS** | 3 / 0 | v14 4-0 |
| n00U | .886/.782/.885 · .665 | .874/.792/.876 · .654 | CHECK | 3 / 0 | v13 4-0 |
| hfoo | .847/.415/.853 · .703 | .831/.408/.843 · .681 | CHECK | 6 / 1 (+.033) | v13 4-0 |
| n017 | .924/.775/.870 · .700 | .918/.839/.842 · .685 | **PASS** | 4 / 0 | v14 3-1 |
| n02X | .907/.837/.918 · .805 | .896/.830/.911 · .759 | **PASS** | 3 / 0 | v13 4-0 |

Resultado da leva: PASS 3/5 (= v13); `--loop` opt-in (1 delta aceite em 19); `--deterministic` custa até .020 de média (8 iterações
< relógio). Itens: L11-0 flip (opt-in), L11-0b enquadramento pelo corpo (opt-in), L11-1 deltas (default do laço), L11-2 laço
(opt-in), L11-3 deltas como limites do fit (opt-in, negativo), L11-5 k do smin (opt-in, neutro), L11-6 retopo CVT e L11-7 matriz
de opt-ins (extras, abaixo quando entrarem).

### 29.L11-1 Deltas por peça (schema, limites, peças congeladas) e `apply_deltas.py`
- **O que mudou.** Novo `tools/blender/apply_deltas.py` (json puro, sem Blender): `apply(spec, deltas, height) -> (spec2, log)`;
  CLI `apply_deltas.py <spec.json> <diagnosis.json> [--out spec2.json]`. `diagnose.py`: o prompt traz a tabela de peças com
  endereço e pede `deltas` (até 6) e `expected` (`{vista: ganho de IoU}`); `check_reply` valida a forma (lista de objetos;
  `expected` com vistas e números), `diagnosis.json`/`.md` guardam os dois; o CLI fixa o rig antes de medir as peças.
- **Endereço de peça** `<osso>#<k>`: k-ésima peça (0-based, ordem do arquivo) ligada ao osso, ex. `spine#2`; osso nu só vale com
  uma peça (senão "ambígua"). Os endereços valem para o spec que ENTRA (nunca para o meio da rodada: remover `spine#2` não muda
  `spine#3`). Em `add`, `part` é o osso. Uma peça recebe no máximo um delta por rodada.
- **Ações e limites.** `scale` [0.7, 1.4] (uniforme; com eixo: box/frustum, comprimento de prism/cyl, altura ou `squash` do lathe;
  eixo em peça from/to é rejeitado), `radius` [0.7, 1.4] (lathe, cyl, frustum, prism, limb, chain), `move` |v| ≤ 0.08 H por
  delta, `rotate` ≤ 25° somado ao `rot` (só `preflight.ROT_KINDS` sem from/to/cut), `add` ≤ 2 por rodada, caixa ≤ 10 % do volume
  da figura (soma das caixas das peças), `remove` só caixa < 2 %. Peça em osso `.L/.R` com gêmea espelhada (mesmo kind e
  dims) leva o delta espelhado na gêmea (`add` cria o par), para a regra `symmetry` seguir valendo.
- **Rejeição.** Campo fora do schema, ação/eixo/valor fora do limite, peça inexistente/ambígua, validação da peça
  (`spec_pipeline.validate`) ou delta repetido na mesma peça rejeitam SÓ aquele delta: `{delta, status, why}` no log. O resultado
  passa por `spec_pipeline.parse_spec` (grade 1/256, ground fix); se falhar, devolve o spec de entrada e marca tudo rejeitado.
  Peças não citadas saem byte-iguais (só as editadas são ajustadas à grade); `spec2` não reordena (o `--spec` do pipeline re-normaliza).
- **Deltas reais (4 chamadas session:opus, 34–57 s, 2.9–5.0 k tokens de saída cada; sobre cópias dos runs v13-r1).**

| unidade | deltas | aplicados | rejeitados | `expected` |
|---|---|---|---|---|
| hfoo | 4 | 3 (+gêmeas) | 1: `forearm.R#3` scale z, peça from/to (a lança) | front/back/bottom/rts .01, top .02 |
| n00U | 6 | 6 | 0 | rts .03, left/top/bottom .02 |
| n017 | 5 | 5 (1 add) | 0 | left .02, rts .015, back .005, front .003 |
| n02X | 4 | 4 (+gêmea) | 0 | left .02, top .03, bottom .025, rts .015 |

  Arquivos em `analysis/2026-10-29-l11-1-deltas/<id>/` (`diagnosis.json`, `spec2.json`, `applied.log`).
- **Reconstrução sem LLM** (`spec_pipeline --spec … --shape-only --no-repair --no-diagnose --body sdf --tilts <câmeras da v13-r1>`,
  runs `l11-deltas-base` = spec original e `l11-deltas` = spec com deltas, mesmas câmeras). IoU aprovado:

| vista | hfoo base → deltas (Δ) | n02X base → deltas (Δ) |
|---|---|---|
| front | .864 → .862 (−.002) | .898 → .883 (−.016) |
| left | .435 → .448 (+.013) | .834 → .833 (−.001) |
| back | .868 → .870 (+.002) | .910 → .889 (−.021) |
| top | .812 → .798 (−.014) | .757 → .749 (−.008) |
| bottom | .834 → .848 (+.013) | .774 → .751 (−.023) |
| rts | .733 → .699 (−.034) | .789 → .816 (+.027) |
| média | .7578 → .7540 (−.004) | .8271 → .8202 (−.007) |

  (O rebuild do spec original difere do `v13-r1` publicado porque o `--spec` pula o fit de estágios: hfoo média .758 vs .745.)
- **Leitura / negativo.** Aplicar os deltas do VLM às cegas NÃO sobe a média (−.004, −.007) e derruba vistas > .01 (hfoo top e rts,
  n02X front/back/bottom): o `expected` do VLM (+.01…+.03) não se realiza. Duas rodadas rejeitadas pelo guarda de L11-2 por
  construção — é o que o guarda existe para fazer; L11-2 tenta o delta seguinte da lista (até 3 por rodada). Em n02X os dois
  deltas do taco (`move z 0.2`) ficaram no limite 0.08 H = 0.21 e o resto é redimensionamento de fist/cinto: pouco sinal visual.
- **Testes.** `tests/tools/blender/test_apply_deltas.py` (10, 0.01 s); `test_diagnose.py` atualizado (deltas/expected no REPLY e
  rejeição de `deltas`/`expected` malformados). Não feito: `--loop` (L11-2), deltas como limites do fit (L11-3).


### 29.L11-5 `k` do smin por junta (`sdf_k_mode`)

**O que mudou.** `sdf_body.field(..., k_mode=)` / `pair_k(a, b, voxel, height, k_scale, mode)` com `K_MODES`: `base` (o k da
28.L10-1, default, inalterado), `class` (k x `CLASS_K` pela classe dos dois ossos: tronco-tronco 1.0, tronco-membro 0.5,
membro-membro 0; membro = prefixo `arm forearm hand thigh shin foot leg wing wheel`, `bone_class`), `hard` (k = 0 em todas as
juntas: união dura no campo) e `ext` (`smin(..., exterior=True)`: o blend só onde d_a > 0 e d_b > 0). O modo vai para
`clay.sdf.json` (`k_mode`, ausente = `base`; mesh_lint recomputa igual). Flags: `build_unit ... sdf_k_mode=base|class|hard|ext`,
`spec_pipeline.py --sdf-k-mode`, `sdf_body.py --k-mode`. Os pesos de pele continuam com a banda do k `base` (`band_matrix`): o
modo muda só a geometria. Testes: `test_sdf_body.py` (`test_k_by_joint_class`, `test_exterior_blend_does_not_fatten_the_inside`).

**Geometria sem pipeline** (grid 96, volume do campo, L): base / class / hard / ext = n005 1599.1 / 1595.7 / 1587.0 / 1599.1;
n00U 106.7 / 106.5 / 105.4 / 106.7; hfoo 917.2 / 916.4 / 915.3 / 917.2; n017 305.8 / 305.3 / 304.2 / 305.8; n02X 2285.5 /
2281.7 / 2277.2 / 2285.5. O smin completo engorda 0.2-0.7 % do volume (hard é o piso); **`ext` tem o mesmo conjunto zero que
`base`** (fora das duas peças o blend é igual; dentro de uma o min já é < 0): só muda o valor interno do campo, não a malha. É um
no-op geométrico, mantido como controle.

**Pipeline** (`--body sdf --kind mass --no-repair --no-diagnose --shape-only`, câmeras da v13 fixadas por `--tilts`, spec
v13-r1; runs `l11-smink-{D,A,B,C}`; D = `base` reconstruído com a mesma linha). IoU(variante) − IoU(`v13-r1-union`), f/l/b/top/bot/rts:

| unid. | D base | A class | B hard | C ext |
|---|---|---|---|---|
| hfoo | +.018 +.010 +.030 −.009 −.002 +.003 | +.014 +.017 +.029 −.009 +.010 −.015 | +.017 +.081 +.030 −.010 −.001 +.004 | +.013 +.006 +.024 .000 +.018 −.025 |
| n017 | +.008 +.038 −.009 +.014 +.007 −.011 | +.010 +.023 −.011 +.018 +.003 −.008 | +.004 +.037 −.010 +.007 +.008 −.003 | +.008 +.046 +.007 +.017 −.008 −.006 |

Slivers % / nd (°) nas 5 unidades (n005 n00U hfoo n017 n02X), união 12.2-19.5 % / 44-52°: D 4.4 0.7 2.6 4.4 3.9 / 35.4 43.9 39.4
37.4 37.4; A 4.3 0.1 6.7 3.9 4.3 / 36.1 45.1 41.5 35.9 40.1; B 4.3 0.1 3.7 3.6 4.7 / 37.8 45.0 39.9 35.9 40.1. C (hfoo, n017):
4.4 5.6 / 39.7 37.2. IoU dos 5 specs: n005/n00U/n02X variam ≤ .02 entre modos (ruído do fit-verts/deform).

**Leitura.** (1) A premissa "o smin engorda e custa rts −.03" não se reproduz na linha mínima: D está a −.009 (top hfoo) e −.011
(rts n017) da união; o −.031/−.033 da v13 vinha do pipeline completo (fit-verts etc.), e o ruído entre builds do mesmo spec é de
± .02 (C, que é geometricamente igual a D, mexe hfoo rts −.025). (2) Aceite: **nenhuma variante passa limpo.** A: hfoo rts
−.015, hfoo slivers 6.7 %. B: slivers < 5 % em 5/5 e hfoo/n017 dentro de −.01 da união, mas nd piora +2.4° (n005), +2.7° (n02X)
contra D e n00U top −.015 contra D. C: no-op, hfoo rts −.025 é ruído. (3) Decisão: default continua `base`; `hard` fica
opt-in (a melhor: hfoo left +.07 contra D, n017 rts +.008), `class` e `ext` sem ganho medido. Para medir de verdade o efeito
das juntas é preciso comparar com o pipeline completo e N ≥ 3 repetições; não feito (cada build 2-5 min).

### 29.L11-0 Flip lateral medido (hfoo left)

- **Pergunta.** `diagnosis.md` do hfoo v13 diz que a figura "left" do sheet está espelhada (pack do lado oposto) e o left fica em
  .415 (união .417: não é o corpo). `silhouette.variants` já testa `np.fliplr` no left. Causa (a) o espelho é escolhido e o problema é
  outro, (b) a escolha não chega ao fit/deform/verts, ou (c) escolha por vista contradiz o rts?
- **Medida (clay `v13-r1`, rasterização de `deform_to_sheet.view_state`, sheet.jpg; vale igual para sheet-hard.jpg).**
  (b) e (c) descartadas: `fit_spec.best_variant`, `fit_grad.best_variant`, `deform_to_sheet.make_views` (e `optimize_verts` via
  `make_views`) escolhem o espelho pelo mesmo critério (melhor IoU de bbox enquadrado) que `silhouette.best_match`; o rts nunca
  espelha. A decisão é consistente e **errada**:

  | left | IoU normal | IoU espelho | escolhe | IoU normal, melhor deslocamento | espelho, melhor deslocamento | só corpo (sem props) deslocado n/e |
  |---|---|---|---|---|---|---|
  | hfoo | .344 | .409 | espelho | **.664** | .530 | .699 / .693 |
  | n005 | .944 | .596 | normal | .944 | .617 | .834 / .626 |
  | n00U | .610 | .780 | espelho | .694 | .783 | .685 / .776 |
  | n017 | .564 | .773 | espelho | .565 | .781 | .568 / .775 |
  | n02X | .837 | .436 | normal | .837 | .579 | .771 / .635 |

  Imagem: `scratchpad/l11-flip/hfoo-left-both.png` (vermelho sheet, verde modelo; esquerda normal, direita espelho). No normal o pack
  (atrás, image-left) e o rosto (image-right) batem com o sheet; o espelho "ganha" porque o bbox do sheet inclui a diagonal do
  pique (alarga a figura e desloca o corpo), então o corpo espelhado cai por cima do contorno deslocado e o pack vai ao lado
  errado. Causa: **(d) enquadramento por bbox** (`silhouette.normalize`) com um prop desenhado fora da coluna do corpo.
- **O que mudou (atrás de flag, desligada).** `silhouette.side_iou` (IoU no melhor deslocamento, correlação por FFT, grade a cada
  4 px: só decide o lado) e `silhouette.pick_variant`: nas vistas front/left/back com `FLIP_SIDE`, o espelho é o que `side_iou`
  separa por `SIDE_MARGIN = 0.05`; empate/quase-simetria (frente de aranha) e as outras vistas ficam no IoU simples. Usado por
  `best_match` (retorna agora `(iou, máscara, tilt, flipped)`), `fit_spec.Proxy.best_variant`/`failing_band`,
  `fit_grad.best_variant`, `deform_to_sheet.best_option` (`make_views`). `silhouette.json` ganha `"flipped": {view: bool}`
  (por vista no relatório de `silhouette.py`, resumo na run) e o `review.md` a linha "side view mirrored". Flags:
  `--flip-side` em `silhouette.py` e `spec_pipeline.py` (este exporta `CF_FLIP_SIDE=1` aos subprocessos). Teste
  `SideMirror` (sheet sintético com pique diagonal, sem Blender).
- **Antes × depois (rebuild `--body sdf --tilts <v13> --shape-only --no-repair --no-diagnose`, IoU f/l/b/top/bot/rts).**

  | un. | v13-r1 | `--flip-side` desligado (controle) | `--flip-side` ligado |
  |---|---|---|---|
  | hfoo | .847/.415/.853/.796/.859/.703 | .857/.430/.861/.816/.853/.711 | .864/**.324**/.868/.812/.834/.733 |
  | n005 | .921/.947/.932/.764/.833/.878 | .924/.946/.925/.763/.829/.877 | .922/.944/.930/.762/.827/.877 |
  | n00U | .886/.782/.885/.738/.704/.665 | .899/.779/.893/.683/.737/.619 | .895/.791/.897/.736/.690/.611 |
  | n017 | .924/.775/.870/.822/.871/.700 | .905/.796/.866/.814/.861/.744 | .909/.823/.850/.800/.870/.718 |
  | n02X | .907/.837/.918/.766/.774/.805 | .899/.836/.913/.764/.776/.800 | .900/.832/.912/.755/.771/.785 |

  Acima de ±.005 nas 4 unidades NÃO é efeito da flag: a decisão do lado é idêntica ao IoU simples em 12/12 vistas (clay v13 e clay
  do controle), e o `optimize_verts` para por relógio (`--seconds 120`), então rebuilds com a máquina carregada variam .02–.05
  (n00U top .683/.738/.736). Só o hfoo left muda de decisão (espelho → normal) e piora: .430 → .324.
- **Por que a orientação certa não dá ≥ .60.** Com o lado certo o IoU enquadrado continua .32–.34: o sheet tem o pique diagonal
  (do chão atrás até acima do ombro, bbox largo) e o modelo o tem vertical (bbox estreito), então os dois enquadramentos diferem
  em ~40 px e nenhum passo (fit/deform/verts, todos contra a máscara enquadrada) consegue encostar corpo e pack. Mesma figura
  deslocada daria .66 (corpo .70). Teste de spec (cópia em `scratchpad/l11-flip/hfoo-pike-spec.json`: pique de (z −.55, y .09) a
  (z 1.0, y 2.47) em vez de vertical, run `hfoo/l11-flip-pike`, `--flip-side` desligado): left .321 → **.464**, front/back
  iguais (.851/.857), mas rts .711 → **.588** (o sheet rts já era incoerente: .56) e top .816 → .749. Não passa de .60.
- **Correção real, para L11-1/2.** (1) delta de spec: pose do pique, base atrás (z ≈ −.55) e ponta à frente/acima do ombro
  (z ≈ +1), conciliando com o rts (sheet incoerente entre left e rts: não dá para satisfazer os dois); profundidade do pack
  (z −.30, caixa) como no sheet. (2) enquadrar o left pelo corpo (bbox sem os props de `prop_masks`) em vez do bbox da figura,
  mudança em `silhouette.normalize`/`concept_panels` que mexe em todas as unidades (próprio item, medir 15 vistas).
  Enquanto isso `--flip-side` fica opt-in: só vale ligar junto com (1) ou (2).

### 29.L11-3 Deltas como limites do fit (via B) contra edição do spec (via A)
- **O que mudou (atrás de flag).** `apply_deltas.fit_limits(spec, deltas, height) -> {índice: {"dims"|"at": {slot: (lo, hi)}}}`:
  `scale`/`radius` viram o intervalo `valor ± 0.1` sobre o fator da dim (`scale 0.8` em `spine#2` x → [0.7, 0.9] da largura atual), `move` o
  intervalo `valor ± 0.02 H` metros sobre o deslocamento do `at`; a gêmea recebe o limite espelhado (x do move com sinal trocado).
  `add`, `remove`, `rotate`, peça inexistente/ambígua, valor fora do schema e `scale` por eixo sem dim correspondente (squash do
  lathe, peça from/to) não têm via B e são ignorados. `fit_spec.fit(..., constraints=deltas)`: `limit_bounds` troca nos `bounds` só os
  slots citados (s = (f − 1)/`DIMS_RANGE`, s = m/(`AT_RANGE`·H)); a peça citada entra nas livres; o melhor ponto DENTRO dos limites é
  devolvido mesmo que o início sem limite fosse mais barato (se nenhum ponto viável, devolve o spec: `best["x"] is None`);
  `report["constrained"]`. `fit_grad.descend` começa no ponto de x = 0 projetado nos limites (igual a antes quando 0 está dentro).
  Flags: `fit_spec.py --constraints diagnosis.json`, `spec_pipeline.py --constraints diagnosis.json` (com `--fit`, default). Sem a flag nada muda.
- **Ablação (sem LLM; `--spec` v13-r1 / `spec2.json` de 29.L11-1, `--fit` ligado nas três vias, câmeras da v13 fixas, `--body sdf`,
  `--shape-only`, runs `runs/draft/<id>/l11-fitc-{base,A,B}[-grad]`; IoU aprovado, raster duro, Δ vs base).** base = spec v13 sem deltas;
  A = deltas aplicados ao spec (L11-1) e depois o fit; B = spec v13 + fit com os deltas como limites (Powell).

| unid. | via | front | left | back | top | bottom | rts | média (Δ) |
|---|---|---|---|---|---|---|---|---|
| hfoo | base | .866 | .427 | .873 | .809 | .834 | .736 | .7576 |
| | A | −.002 | **+.014** | −.002 | −.008 | **+.020** | **−.024** | .7571 (−.0005) |
| | B | −.005 | −.011 | −.003 | +.001 | +.019 | **−.034** | .7522 (−.0054) |
| n02X | base | .899 | .832 | .903 | .757 | .774 | .786 | .8252 |
| | A | **−.018** | +.003 | **−.013** | **−.013** | **−.020** | +.036 | .8211 (−.0042) |
| | B | 0 | 0 | 0 | 0 | 0 | 0 | .8252 (0): nenhum ponto viável dentro dos limites, o fit devolve o spec |
| n00U | base | .885 | .761 | .883 | .682 | .714 | .609 | .7560 |
| | A | +.010 | −.009 | +.013 | +.001 | +.012 | −.007 | .7592 (+.0033) |
| | B | +.002 | +.017 | −.001 | +.036 | **−.026** | +.034 | .7663 (+.0103) |
| n017 | base | .909 | .822 | .848 | .800 | .869 | .715 | .8271 |
| | A | +.009 | **−.014** | +.015 | +.040 | −.002 | +.003 | .8357 (+.0086) |
| | B | 0 | **−.017** | +.002 | +.022 | **−.013** | +.003 | .8264 (−.0007) |

  Com `--fit-grad` (hfoo, n00U; base-grad = o mesmo caminho sem deltas): hfoo base-grad .7488, B-grad .7525 (+.004 sobre base-grad);
  n00U base-grad .7828, B-grad .7729 (−.010; bottom −.055 vs Powell-base). O grad sozinho muda mais que os deltas (n00U +.027).
- **Veredito.** Aceite (sobe a média sem queda > .01 em mais unidades): A 1 unidade (n00U), B 0. A soma das médias: A +.0072, B +.0042;
  unidades com média acima da base: A 2/4, B 1/4 (n00U com o maior ganho, +.010, mas bottom −.026); unidades com alguma vista
  caindo > .01: A 3, B 3 (A: hfoo rts, n02X ×4, n017 left; B: hfoo left/rts, n00U bottom, n017 left/bottom). **Nenhuma via sobe a
  média de forma confiável; a hipótese "B evita as quedas de A" NÃO se confirma** (hfoo rts −.034 em B, pior que A; n017 left
  continua caindo). A vantagem real de B é só estrutural: limites inviáveis degradam para a base (n02X) em vez de piorar.
  **Recomendação para L11-2: via A como default** (aplica em 1.5 s, sem fit de 1–3 min por rodada; empata ou ganha em média) com o
  guarda de rodada decidindo; B fica como opção (`--constraints`) para ablações, não como default.
- **Testes.** `FitLimits` em `tests/tools/blender/test_apply_deltas.py` (3, ~0.01 s): scale/radius/move → intervalos com gêmea
  espelhada; add/rotate/peça inexistente/fora de faixa ignorados; `limit_bounds` troca só os slots citados.
- **Não feito.** n005 (sem deltas gravados em L11-1); `--deltas-as fit|spec` (o L11-2 escolhe a via; hoje A = `apply_deltas`,
  B = `--constraints`); `rotate` como limite do extra `rot`; `--fit-grad` na ablação de n02X/n017; 1 rodada por via (sem repetição:
  o Powell é determinístico, o grad não foi repetido).

### 29.L11-2 Laço guardado `--loop N` (diagnose -> um delta por vez -> rebuild -> aceite)
- **O que mudou.** Novo `tools/blender/loop_stage.py` (orquestração pura, callbacks: testável sem Blender/LLM) e `spec_pipeline.py --loop N`
  (default 0 = como antes). Após a rodada 0 (stage 1 aprovado, câmeras fixadas por `--tilts`): `diagnose` (1 chamada session:opus por rodada,
  custo em `loop.json`), deltas ordenados pelo `expected` (nota do delta = maior `expected` entre as vistas que o `why` nomeia; sem vista
  = 0, mantém a ordem do VLM), até 3 rebuilds por rodada; cada delta é aplicado SOZINHO (`apply_deltas.apply`) sobre o spec corrente e
  reconstruído pelo MESMO caminho da rodada 0 (`fit_stage` -> `stage_shape`: fit, sdf, deform, fit-verts, silhouette 6 vistas) numa cópia
  de `args` com `out = loop/round<k>/delta<j>/`. Aceite (`loop_accept`): nenhuma vista cai > 0.01 E (média sobe >= 0.005 OU uma vista abaixo do gate
  passa). Aceito vira o spec corrente e é copiado para o run (`clay.glb`, `spec.json`, `silhouette.json`, views); rejeitado é descartado.
  `add`/`remove` aceito encerra a lista da rodada (endereços `osso#k` mudaram). Delta não aplicável (limites) não gasta vaga. Rodada sem
  aceite encerra o laço. Saída: `loop/round0/` (cópia da rodada 0 para o juiz L11-4), `loop/round<k>/{diagnosis.json,delta<j>/}`, `loop.json`
  (por delta: status, motivo, IoU antes/depois, Δ por vista, segundos; custo da diagnose) e secção "Laço" no `review.md`. Estágio de cor só no fim, como hoje.
- **Ruído medido e removido (`--deterministic`, implícito em `--loop`).** hfoo v13, o mesmo spec 3x pelo caminho exato do laço (SOFT_SIL_THREADS=4),
  sob carga diferente: IoU por vista variou até .013 (left .4272/.4226/.4352; back .8729/.8675/.8680; mean .757-.759). Fonte: o
  `fit-verts` pára por relógio (PIPELINE_SECONDS = 30 s; 26, 33 e 34 passos nas três); o fit de escalas/`deform` não (o fit usa MAX_EVALS, o
  deform não tem relógio). Com `--deterministic`: `fit_spec.fit(seconds=1e9)` e `optimize_verts` sem prazo, ritmo só pela iteração, 8 iterações por estágio
  (`DETERMINISTIC_ITERS`; 30 dava 166 passos e 161 s, 8 dá 44 passos e 33 s). Dois rebuilds: IoU idêntico nas 6 vistas (Δ = 0.000, 2 pares). Ruído medido 0, então o guard
  fica em 0.01 / 0.005 (`loop.json`: `deterministic`, `noise: 0`). Consequência: a rodada 0 do laço NÃO é o v13 publicado (fit-verts
  mais curto: hfoo média .7517 contra .745/.758 conforme o caminho); o laço compara sempre contra a sua própria rodada 0.
- **Prova (3 chamadas VLM no total após o ajuste; antes dele 3 chamadas descartadas, runs renomeados `l11-loop-clock-invalid`).**
  `--spec runs/draft/<id>/v13-r1/spec.json --body sdf --tilts <câmeras v13> --run l11-loop --no-repair --no-diagnose --shape-only --loop 1`.

| unidade | deltas tentados / aceitos | Δ por vista rodada 0 -> final (fr/le/ba/to/bo/rts) | média | diagnose | s por delta |
|---|---|---|---|---|---|
| hfoo | 3 / 1 (`spine#2` scale x) | +.014 -.002 +.013 +.023 +.004 -.004 | .7517 -> .7600 | 69 s, 6.3 k tok saída | 135-169 |
| n017 | 3 / 0 (+1 não aplicável: scale z em peça from/to) | 0 | .8317 | 46 s, 3.5 k | 119-306 (2 processos pesados em paralelo, quadrúpede) |
| n02X | 3 / 0 | 0 | .8235 | 55 s, 5.5 k | 85-90 (sozinho) |

  Rejeições (todas por queda de vista, exceto uma): hfoo rts -.031, top/rts -.011/-.019; n017 left -.024 top -.020 bottom -.032, bottom -.018, top/bottom -.011/-.012;
  n02X front -.015, rts -.028, rts -.023. Sem o guard, o primeiro delta do hfoo teria derrubado o rts em .03. Por construção nenhuma vista do run final cai > .01 (hfoo: a pior é rts -.004).
- **Leitura / negativo.** 1 aceito em 9 deltas (11 %): o `expected` do VLM (+.01-.03) quase nunca se realiza, o rts é a vista que mais cai (pernas/
  tronco largos mexem na visão de jogo). Custo: o alvo de <= 3 min por delta só vale com a máquina livre (hfoo 135-169, n02X ~90, n017 até 306 sob carga); uma rodada de 3 deltas custa 6-12 min + diagnose ~1 min.
  Não feito: `--loop` não corre diagnose final nem o juiz pareado (L11-4); sem `loop_hooks` testado fora da prova real (os testes cobrem `loop_stage`).
- **Testes.** `tests/tools/blender/test_loop_stage.py` (9: regra de aceite, ordenação, limite de 3, vaga de não-aplicável, paradas, add/remove, tabela). Suíte: 635 OK.


### 29.L11-0b Enquadramento pelo corpo (bbox sem props) -- opt-in, aceite NÃO atendido

- **O que mudou (atrás de `--frame body`, default `bbox`).** `silhouette.framed_panels` devolve painéis `Framed` (máscara + caixa do
  corpo = figura menos `prop_masks`, só nas vistas com caixa em `parts.json`); `normalize` enquadra por essa caixa (props continuam
  na máscara e no IoU, caindo fora do quadro se passarem). `prop_masks` reenquadra as máscaras de props para o quadro do corpo.
  Modelo: `deform_to_sheet.body_fractions` (corpo = maior componente soldado, o mesmo critério do split de props do deform) ->
  `silhouette.model_boxes` (render) e `View.frame_on` (`deform`/`optimize_verts` enquadram só os vértices do corpo). Flags:
  `silhouette.py --frame`, `spec_pipeline.py --frame` (exporta `CF_FRAME`); `silhouette.json` ganha `"frame"` por vista;
  `CF_VERTS_SECONDS` (default 30) para o optimize_verts rodar por passos, sem relógio. Estágio de cor, `fit_spec`, `fit_grad` seguem
  em bbox (o colour stage re-casa as máscaras em bbox: `silhouette.bbox_masks`).
- **Medida** (rebuild `--body sdf --shape-only --no-repair --no-diagnose`, specs/câmeras v13, `CF_VERTS_SECONDS=1e6`; IoU f/l/b/top/bot/rts;
  bbox reproduz a v13 no clay existente: .846/.415/.853/.796/.859/.703; o rebuild bbox é a linha de controle).

  | un. | bbox (controle) | body | body + `--flip-side` |
  |---|---|---|---|
  | hfoo | .883/.428/.881/.827/.838/.747 | .832/**.458**/.881/.827/.838/.747 | = body |
  | n005 | .931/.945/.938/.747/.858/.888 | .912/**.607**/.938/.747/.858/.888 | .912/.600/... |
  | n00U | .879/.838/.877/.770/.724/.652 | .803/.816/.880/.745/.714/.616 | .902/.722/.896/.671/.740/.610 |
  | n017 | .915/.843/.847/.807/.892/.744 | = bbox (sem props em parts.json) | = bbox |
  | n02X | .901/.868/.911/.776/.783/.814 | .711/.720/.911/.776/.783/.814 | = body |

- **Veredito: não passa.** hfoo left .428 -> .458 (alvo .60); n005 left -.34, n02X front -.19 e left -.15, n00U front -.08.
  Causa vista nos overlays: os dois lados definem "props" diferente. O sheet exclui só os props de `parts.json` (n02X: um disco
  de 179 px; o clube fica no corpo), o modelo exclui todo componente solto (o clube do n02X, o tanque do n005 ficam de fora ou
  dentro de forma oposta), então os dois corpos são enquadrados por caixas de coisas diferentes e a escala diverge. No hfoo o
  corpo alinha (pack do lado certo, overlay em `scratchpad/l11-frame/cmp.png`) mas o pique do modelo (vertical) continua sem
  casar com o do sheet (diagonal), o que limita o IoU. `--flip-side` não ajuda (hfoo igual; n00U piora left, melhora front/back).
- **Próximo passo possível.** Definir o corpo do modelo pelos mesmos props do sheet (`attach.json["props"]` por peça do spec ->
  vértices do corpo, não componente) antes de reabrir; sem isso, manter `bbox`. Testes: `BodyFrame` (test_silhouette),
  `TestBodyFrame` (test_deform_to_sheet). Runs: `runs/draft/<un.>/l11-frame-{bbox,body,bodyflip}` (`-bbox-invalid` de hfoo/n00U =
  escrita concorrente, refeitos).

### 29.L11-4 Bateria v14 (autor LLM, `--loop 2`, pareada contra v13) e a decisão do laço
- **Protocolo.** 5 unidades, `spec_pipeline.py --model session:opus --kind mass --run v14-r1 --pair v13-r1 --loop 2` (corpo sdf default;
  `--loop` implica `--deterministic`: fit e fit-verts por iterações, 8 por estágio), 3 + 2 processos, `SOFT_SIL_THREADS=4`. Controle
  `v14-r1-clock`: `--spec runs/draft/<id>/v14-r1/spec.json --tilts <câmeras da v14> --no-repair --no-diagnose` sem `--deterministic`
  e sem laço. Imagens e tabelas em `history/2026-10-29-v14/README.md`; linhas v14 em `IA_gen_paper/results.csv`.
- **Resultado.** PASS 3/5 (n005, n017, n02X; v13 3/5). Laço: 19 deltas tentados, 1 aceite (hfoo `foot.L#0` scale z 0.7, média +.033);
  14 rejeitados por "uma vista cai" (left −.012…−.054, top/bottom −.011…−.029, rts −.024), 2 por média < +.005, 1 não aplicável. Juiz:
  forma pró-v13 4-0 em n00U/hfoo/n02X, pró-v14 em n005 (4-0) e n017 (3-1); sheet pró-v14 4-0 em n00U/n02X. Custo: 1 chamada VLM por
  rodada (45–104 s, 3.7–8.8 k tokens) + 85–450 s por delta (n00U 1344 s em 3 deltas, máquina carregada).
- **Controle do `--deterministic`.** Relógio 30 s − 8 iterações, mesmo spec e câmeras, Δ média: n005 +.001, n00U +.020, hfoo −.002,
  n017 +.012 (rts +.069), n02X +.003. O orçamento por iterações fica abaixo do pipeline normal onde há mais vértices a mover; o ruído
  0 do L11-2 custou forma em 2/5.
- **Critérios do L11-4 e decisão.** PASS ≥ 4/5 ✗ (3/5); média ≥ v13 em 5/5 ✗ (specs novos: n017 +.004, outras −.002…−.013); juiz
  forma ≥ 3-1 em ≥ 3/5 ✗ (2/5); custo ≤ +4 min/unidade ✗ (+5…+24 min). **`--loop` fica opt-in** e `--deterministic` só para
  experimentos. O guard está certo (sem ele 14 deltas teriam piorado uma vista); o que falta é a qualidade do delta proposto: o VLM
  acerta a direção (o `why` nomeia a vista certa) mas não a magnitude, e a vista oblíqua (rts) paga.
- **Aberto.** (1) `DETERMINISTIC_ITERS` igual aos passos que o relógio dá (~15 por estágio) e remedir o ruído; (2) deltas de magnitude
  pequena com busca de linha (0.9, 0.8, 0.7) em vez do valor do VLM — 3 rebuilds por delta, caro; melhor como restrição do fit (L11-3
  mostrou que a via B também cai, mas sem busca de linha); (3) o laço deve vir DEPOIS do polimento MCP (Leva 12) ou substituí-lo —
  decidir na v15.

### 29.L11-6 `retopo.cvt`: retopologia por Voronoi/CVT guiada por curvatura -- opt-in, aceite NÃO atendido
- **O que mudou.** `tools/blender/retopo.py`: `cvt(verts, tris, target_faces, sdf, polish, grad_h, max_dev, eps, alpha, iters, smooth, place, seed, tries)` e
  `retopo(method="cvt")` (Chatterjee, Soni, Bhowmick, ICVGIP 2022; Valette & Chassery 2004; Valette, Chassery & Prost 2008). `build_unit sdf_retopo=qem|cvt`
  (`sdf_retopo(..., method=)` chama `RT.retopo`), `spec_pipeline --sdf-retopo qem|cvt` (default `qem`, nada muda). `retopo_ablate.py`: linhas `cvt`, `cvt qef` e `--rows`.
  numpy puro: o Python do Blender não tem scipy, então `voronoi` (Dijkstra multi-fonte por rodadas de fronteira) e `components` são próprios.
- **Algoritmo.** (1) curvatura por vértice da malha densa openvdb = ângulo diédrico médio das arestas incidentes, suavizado 2 anéis (`CVT_SMOOTH`; o diédrico cru
  tem mediana 0.09 rad só pelo degrau de 45° da grade); densidade ρ = (ε + κ)^α, `CVT_EPS` = 0.3 rad, `CVT_ALPHA` = 1; (2) N = (B + 4 − euler_in)/2 sementes por
  amostragem ponderada por área·ρ (mínimo 4 por componente conexa, resto proporcional ao peso); (3) Lloyd discreto até 30 iterações (para quando nenhuma semente mexe):
  células = Voronoi **geodésico ao longo das arestas** (não kd-tree euclidiano: ele junta duas pernas que se tocam no espaço e funde alças que o corpo tem), semente <-
  vértice da célula mais perto do centróide ponderado; (4) um vértice por célula = minimizador da quádrica das faces da célula, amortecido ao centróide
  (`place="qef"`, `CVT_QEF_REG` = 0.5; `"centroid"` = só o centróide), projetado no SDF (Newton, `polish` = `Field.d` no fim); (5) faces = cada triângulo denso com 3 células
  distintas vira uma face (`dual_faces`, orientação do denso). Células que se tocam em dois lugares repetem uma aresta orientada: `drop_overloaded` deixa a maior face,
  `fill_holes` fecha os laços com leque (cordas novas). Até `CVT_TRIES` = 4 sorteios de semente (para após `CVT_SECONDS` = 2 s): vence o de menos `defects`
  (bordas, arestas sobrecarregadas, euler − euler_in) e depois o de menor |sdf| médio nos centróides das faces. `max_dev` só é relatado (`dev_over`): o dual não tem guarda por operação.
- **Ablação rápida (malha densa v12 a0, B = 600, `retopo_ablate.py --rows`, QEM = L10-3 final).** Lloyd converge em 11–19 iterações; 0.17 s (n005, hfoo), 0.5 (n017), 1–2.5 s (n00U, 4 sorteios).
  centróide × qef: centróide dá fairness 13–15 e p95 1.3–3.0 % H; qef reg 0.5 dá fairness 14–16 e p95 1.1–2.9 (reg 0.02: p95 1.0 mas slivers até 1.9 %); ε 0.1 → 1.0 e α 0.5 → 2
  mexem fairness ±2 e p95 ±0.2 (α 2: slivers até 1.4 %, nd +4). A pior vista de IoU contra o QEM varia −0.002…−0.047 só pela semente (n017): um sorteio não decide.
- **Prova no pipeline (v13, câmeras fixadas, sem LLM, 5 un.; controle = rebuild qem `l11-cvt-qem`, cvt = `l11-cvt`; `--body sdf --shape-only --no-repair --no-diagnose`, `CF_VERTS_SECONDS=1e6`).**
  IoU cvt − qem por vista (f / l / b / top / bot / rts):

| un. | f | l | b | top | bot | rts | média | slivers % cru→final qem / cvt | nd final qem / cvt | fairness final qem / cvt | euler entrada / qem / cvt | sdf_dev p95 % H final qem / cvt | retopo s qem / cvt |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| n005 | −.004 | −.002 | +.001 | +.020 | **−.012** | +.012 | +.003 | 0.0→4.3 / 0.0→3.1 | 36.4 / 31.4 | 25.6 / 18.0 | 0 / 0 / 0 | 2.43 / 2.42 | 1.0 / 0.6 |
| n00U | −.001 | +.005 | .000 | +.069 | −.006 | **−.018** | +.008 | 0.0→1.1 / 0.1→0.3 | 46.2 / 41.8 | 27.0 / 17.2 | 4 / 4 / 2 | 4.77 / 4.66 | 2.9 / 2.1 |
| hfoo | −.005 | **−.025** | +.002 | +.004 | +.044 | +.009 | +.005 | 2.6→2.7 / 2.6→4.0 | 40.9 / 38.3 | 24.3 / 19.1 | 8 / 8 / 0 | 1.60 / 2.77 | 0.9 / 0.6 |
| n017 | +.013 | −.005 | +.023 | .000 | **−.026** | +.001 | +.001 | 1.7→3.7 / 1.7→3.6 | 38.8 / 35.0 | 25.7 / 19.3 | 0 / 0 / 0 | 2.99 / 4.13 | 1.5 / 1.9 |
| n02X | +.013 | **−.027** | +.008 | −.010 | +.008 | **−.028** | −.006 | 1.7→3.6 / 1.7→3.0 | 39.3 / 33.2 | 23.7 / 17.5 | 4 / 4 / 2 | 5.97 / 4.53 | 1.3 / 1.1 |

  (euler = o do `report` do retopo, só do corpo; o `mesh_lint` do glb cru soma os props e dá outros números.)
- **Aceite do plano.** Slivers finais < 5 % em 5/5: **sim** (3.1 / 0.3 / 4.0 / 3.6 / 3.0). nd ≤ qem + 1°: **sim** (−3…−5° em 5/5). ≤ 5 s: **sim** (≤ 2.1 s no pipeline). Fairness 24–27 → 17–19
  em 5/5 (o que o QEM não dá). IoU ≥ qem − 0.01 em todas as vistas: **não**: 6 vistas abaixo (n005 bot −.012, n00U rts −.018, hfoo left −.025, n017 bot −.026, n02X left −.027 e rts −.028);
  médias por unidade +.003 +.008 +.005 +.001 −.006 (ruído de ±.03 por sorteio, ver acima). Euler = entrada: **não** em 3/5 (hfoo 8 → 0, n00U 4 → 2, n02X 4 → 2) e o n00U fecha com 4 arestas de borda
  (`defects (4, 0, −2)`).
- **Decisão: `METHOD = "qem"` (default inalterado), `cvt` opt-in (`retopo(method="cvt")`, `--sdf-retopo cvt`).** Onde perde: (a) **topologia**: alças finas (pernas do n00U/n02X, o anel do hfoo) ficam abaixo da resolução da célula,
  e o dual as perde (menos 4 a 8 de euler); a guarda de link do QEM as mantém; (b) **desvio**: p95 do `sdf_dev` cru 1.0–2.3 % H contra 0.5–1.0 do QEM (o vértice da célula projetado no SDF não vê a corda da face; o QEM controla por `max_dev`),
  o que custa IoU em uma vista por unidade; (c) sorteio de semente: um único Lloyd varia −0.002…−0.047 na pior vista. Ganhos reais: fairness −7…−10°, nd −3…−5°, slivers finais iguais ou menores, sem LLM, ≤ 2 s.
  Candidato a revisitar: cvt como malha inicial do `fit_grad`/`optimize_verts` (fairness boa, desvio a ser consertado pelo fit) ou cvt só em unidades sem alças finas.
- **Negativos.** Kd-tree euclidiano não foi implementado (a geodésica é barata: 30 ms por Voronoi a 60 k vértices). Mais iterações de Lloyd (60) não mudam nada (converge antes de 30). `place="centroid"`: melhor fairness (−2) e pior p95 (+0.2).
  Escolher o sorteio pelo |sdf| médio dos centróides não reduz a variação de IoU. Euler: até 4 sorteios por unidade não recuperam a alça perdida em hfoo/n00U/n02X (melhor sorteio guardado; o `report` traz `tries` e `defects`).
- **Testes.** `test_retopo.py::Cvt` (4, < 0.1 s): sementes se concentram nas arestas do cubo (α = 1 vs 0), esfera -> fechada, euler 0, V ≈ V*, vértices em |d| < 1e-3 e sem sliver, `retopo(method="cvt")` aceita o `floor` do `build_unit`, duas cascas disjuntas ganham sementes cada.
  Runs: `runs/draft/<id>/l11-cvt-qem` e `l11-cvt` (+ `-invalid*`: runs que o SIGTERM do ambiente interrompeu, mantidos).


### 29.L11-7 Matriz de ablação (fecho: o que a phase (a) antiga mediu e a decisão)
- **O que foi.** `tools/blender/ablation_matrix.py` + `overrides.py` (`CF_OVERRIDES`/`CF_BUILD_ARGS`, no-op sem as variáveis): cada opt-in
  sozinho, 5 unidades (specs `v13-r1`, câmaras pinadas, `--deterministic`, sem LLM), 28 variantes, 140 runs, no código ANTES da Leva 12
  (câmara do otimizador desalinhada do gate, gates frouxos, flags mortas). Runs em `l11-mx-*` do worktree `leva11-matrix` (não
  versionados); tabela da época em `scratchpad/l11-matrix/phase-a.md`. O agente foi interrompido antes da phase (b) e da escrita do doc.
- **Resultado (critério da época: ganha em >= 3/5 unidades com média +.005 e nenhuma vista cai > .01).** Nenhum opt-in ganhou: 0 variantes
  "default"; `verts-asym`, `verts-gamma`, `verts-tau` ficaram opt-in (+.0008 / +.0004 / -.0024 de IoU médio, 2-3 vistas caindo); controles
  confirmaram o default (`no-verts` -.026, `no-deform` -.018, `body-union` -.008, `frame-body` -.023). `thin-keep`/`thin-off`/`leg-grow`
  não mexeram em nada (no-op nessas unidades). Fim de L11-7: **decisão = nenhum default muda por esta matriz**; ela media com câmara
  desalinhada e flags mortas (peer review §7.8), então a Leva 12 a re-executa (§30.L12-10a, que substitui esta tabela).
- **Tabela antiga (IoU, só forma; reproduzida com as colunas novas em §30.L12-10a "antes").**

| variant | units | Δ mean IoU | units won (≥ +.005, no fall) | views falling > .01 | units worse | Δ slivers % | Δ nd ° | Δ seconds | worst view | decision |
|---|---|---|---|---|---|---|---|---|---|---|
| fit-grad | 5 | -0.0026 | 0/5 | 5 | 1 | +0.5 | -1.1 | -77 | left -0.045 | no (loses left -0.045; 1/5 units worse) |
| fit-stages | 5 | -0.0048 | 0/5 | 6 | 2 | +0.3 | +0.0 | -18 | left -0.058 | no (loses left -0.058; 2/5 units worse) |
| fit-edges | 5 | -0.0003 | 0/5 | 4 | 0 | +0.2 | -1.0 | +78 | bottom -0.044 | no (loses bottom -0.044; 0/5 units worse) |
| fit-parts | 5 | -0.0042 | 0/5 | 5 | 1 | +0.0 | -1.2 | +21 | left -0.082 | no (loses left -0.082; 1/5 units worse) |
| fit-depth | 5 | -0.0048 | 0/5 | 5 | 1 | +0.3 | -0.8 | +41 | left -0.082 | no (loses left -0.082; 1/5 units worse) |
| constraints | 4 | -0.0062 | 0/4 | 6 | 2 | +0.8 | +0.7 | +0 | rts -0.045 | no (loses rts -0.045; 2/4 units worse) |
| leg-spill | 2 | -0.0169 | 0/2 | 6 | 2 | -0.1 | -0.9 | -139 | bottom -0.056 | no (loses bottom -0.056; 2/2 units worse) |
| leg-grow | 1 | +0.0000 | 0/1 | 0 | 0 | +0.0 | +0.0 | -1 | back +0.000 | neutral |
| body-union | 5 | -0.0080 | 0/5 | 11 | 3 | +13.5 | +9.7 | -19 | left -0.044 | no (loses left -0.044; 3/5 units worse) |
| k-class | 5 | -0.0053 | 0/5 | 6 | 2 | +0.7 | +0.6 | -17 | top -0.053 | no (loses top -0.053; 2/5 units worse) |
| k-hard | 5 | -0.0035 | 0/5 | 9 | 2 | +0.4 | +1.2 | -12 | left -0.042 | no (loses left -0.042; 2/5 units worse) |
| thin-keep | 5 | +0.0000 | 0/5 | 0 | 0 | +0.0 | +0.0 | -10 | back +0.000 | neutral |
| thin-off | 5 | +0.0000 | 0/5 | 0 | 0 | +0.0 | +0.0 | -11 | back +0.000 | neutral |
| grid-128 | 5 | -0.0056 | 0/5 | 8 | 3 | +1.2 | +0.7 | -7 | top -0.055 | no (loses top -0.055; 3/5 units worse) |
| no-deform | 5 | -0.0183 | 0/5 | 18 | 5 | -2.0 | -1.6 | -20 | left -0.073 | no (loses left -0.073; 5/5 units worse) |
| no-verts | 5 | -0.0257 | 0/5 | 24 | 5 | +0.2 | -1.2 | -34 | back -0.074 | no (loses back -0.074; 5/5 units worse) |
| align | 5 | -0.0017 | 0/5 | 3 | 1 | +0.0 | +0.0 | -10 | rts -0.019 | no (loses rts -0.019; 1/5 units worse) |
| props-own | 5 | -0.0009 | 0/5 | 3 | 0 | -0.2 | -0.0 | -9 | left -0.020 | no (loses left -0.020; 0/5 units worse) |
| verts-fd | 5 | -0.0003 | 1/5 | 8 | 2 | -0.4 | +1.4 | +5 | back -0.055 | no (loses back -0.055; 2/5 units worse) |
| verts-tau | 5 | -0.0024 | 0/5 | 4 | 1 | -0.1 | -0.3 | -7 | bottom -0.028 | no (loses bottom -0.028; 1/5 units worse) |
| verts-asym | 5 | +0.0008 | 0/5 | 2 | 0 | -0.1 | +0.2 | -11 | back -0.012 | opt-in (loses back -0.012; 2 view(s) > 0.01) |
| verts-dihedral | 5 | -0.0081 | 0/5 | 9 | 3 | -0.3 | -2.2 | -10 | rts -0.034 | no (loses rts -0.034; 3/5 units worse) |
| verts-gamma | 5 | +0.0004 | 1/5 | 1 | 1 | +0.0 | -0.0 | -8 | front -0.011 | opt-in (loses front -0.011; 1 view(s) > 0.01) |
| verts-uniform | 5 | -0.0010 | 0/5 | 1 | 0 | -0.2 | -0.1 | -7 | front -0.013 | no (loses front -0.013; 0/5 units worse) |
| verts-yager | 5 | -0.0014 | 0/5 | 2 | 1 | -0.1 | -0.2 | -2 | back -0.022 | no (loses back -0.022; 1/5 units worse) |
| flip-side | 5 | -0.0021 | 0/5 | 1 | 1 | +0.0 | +0.0 | -1 | left -0.064 | no (loses left -0.064; 1/5 units worse) |
| frame-body | 5 | -0.0231 | 0/5 | 6 | 3 | +0.0 | +0.0 | -2 | left -0.337 | no (loses left -0.337; 3/5 units worse) |

## 30. Leva 12 (2026-10-29/30): consertar o que o peer review achou

Fonte: `analysis/2026-10-29-peer-review-v14.md`; critério do usuário: vermelho (spill) <= .03 em cada uma das 6 vistas, verde (bare) pouco, "PASS != certo".
Itens L12-1 a L12-9 em worktrees próprios, integrados em `feat/models-v2-hard`; L12-10a (matriz de ablação, outro worktree) e L12-10b (bateria v15, abaixo).
**Defaults que mudaram:** câmera pinada no otimizador e no deform (L12-1), gate de spill .03 / bare .10 por vista sem média + `contact` no relatório (L12-2), stage 2 sempre e
`FAIL(infra)` com exit 2 (L12-4), gate no corpo com prop em CHECK e colunas corpo/prop (L12-5), regras da DSL no preflight e reparo de `leg_joints` (L12-6),
régua `z_err`/`relief_agreement` e métricas `look` sempre ligadas (L12-8, L12-9). **Opt-in com número:** `CF_SPILL_W=3` (spill −.00..−.06 por vista, bare +.03..+.10, IoU até −.10), `--author-guard revert` (L12-3; medido com autor novo em 30.L12-10b),
`--incoherent-weight 0|1` (L12-5, peso 0 piora left/top do n017), `--dsl-repair all` (capuz/props: n005 front −.006..−.013), `--depth-source tri` (L12-8), `--look-snap/--look-creases/--look-ink` (L12-9, crease recall +.08 contra +.15),
`--noise` (σ por vista, L12-7). **Resultado da bateria v15 (6 unidades, autor session:opus): PASS honesto 0/6, spill <= .03 em 0/36 vistas (2/36 com a guarda); o aceite do roadmap não foi atendido.**
O limite é a forma (volume de prismas/SDF contra a silhueta desenhada), não o peso do custo; ver 30.L12-10b. L12-11 (polimento MCP) é a próxima leva.

### 30.L12-1 Câmara pinada: otimizador e deform medem com a câmara do gate (2026-10-29)

- **Diagnóstico (6 unidades, v13-r1).** A lacuna `verts.after − gate` (.06–.09 em n005/n017/n02X top, .13 em n00U rts) tinha **duas** causas, não uma:
  (1) o tilt: `optimize_verts.make_views` varria o tilt de top/bottom e o azimute/elevação do rts sobre a malha *pré-fit* e escolhia outro que o gate na malha final
  (n005 top −30 contra −20; n017 +10 → −20; n02X −20 → −10; n01X coincidia e tinha lacuna 0); `--tilts` só pinava o gate; (2) a **orientação do painel**:
  `deform_to_sheet.candidates` tenta o painel de top/bottom como desenhado *e* girado 180°, e o otimizador escolhia o girado numa vantagem pequena
  (n017 top: 0.828 como desenhado, 0.864 girado, gate 0.823; n02X top 0.773 contra 0.832, gate 0.771), enquanto o gate só gira com `detect_rotated`
  (margem `FLIP_MARGIN` = .10). Pinar só o tilt (`l12-cams-pin`) deixou 3 lacunas ≥ .01 (n017 top .041, n02X top .061, n00U rts .030).
- **Mudança.** `deform_to_sheet.run_cams(args)`: `--tilts` (a câmara do gate, `views.parse_tilts`) primeiro, depois o `silhouette.json` do run, depois varrimento;
  `optimize_verts.apply/run/optimize/make_views/rts_view` recebem `cams` e o repassam (`rts_view` pina `(elevação, azimute)`; o relatório `.verts.json` ganha `"cams"`);
  `deform_to_sheet.best_oriented`: top/bottom só giram o painel quando ganham por `silhouette.FLIP_MARGIN` (a regra do gate), com ou sem tilt pinado.
  Sem flag nova: `--tilts` e o `silhouette.json` já existiam. Primeira rodada sem tilt pinado ainda varre (pela IoU do raster enquadrado, o mesmo score do `best_match`),
  então a lacuna só fecha quando a câmara é pinada (rodadas seguintes, `--tilts`, laço).
- **Medida (sem LLM, `spec_pipeline.py --spec v13-r1/spec.json --no-repair --no-diagnose --body sdf --deterministic --tilts <do v13-r1>`; controle = HEAD sem a mudança,
  `l12-ctl`, num worktree temporário; depois = `l12-cams`; rig e nomes como em `v13.sh`).** Antes → depois, por vista.

lacuna verts.after - gate (antes -> depois)
| un. | front | left | back | top | bottom | rts |
|---|---|---|---|---|---|---|
| n005 | +.002 -> +.004 | +.001 -> +.000 | +.000 -> -.004 | +.060 -> -.002 | -.005 -> -.002 | -.001 -> -.001 |
| n00U | +.000 -> +.002 | -.001 -> -.001 | +.000 -> +.001 | +.002 -> +.001 | -.001 -> +.000 | +.126 -> +.030 |
| hfoo | -.001 -> -.001 | - -> - | +.001 -> +.001 | +.002 -> +.002 | -.001 -> -.001 | +.002 -> +.002 |
| n017 | -.000 -> -.000 | -.003 -> -.006 | -.003 -> +.003 | +.092 -> +.001 | -.008 -> +.001 | +.001 -> +.001 |
| n02X | -.001 -> +.001 | -.002 -> -.002 | -.001 -> -.001 | +.073 -> +.001 | +.001 -> -.001 | +.001 -> +.001 |
| n01X | +.003 -> +.003 | +.001 -> +.001 | +.004 -> +.004 | -.001 -> -.001 | +.006 -> +.006 | -.002 -> -.002 |

IoU do gate
| un. | front | left | back | top | bottom | rts |
|---|---|---|---|---|---|---|
| n005 | .919 -> .920 | .943 -> .946 | .931 -> .933 | .761 -> .797 | .823 -> .820 | .876 -> .878 |
| n00U | .882 -> .878 | .823 -> .818 | .878 -> .876 | .732 -> .734 | .707 -> .709 | .624 -> .653 |
| hfoo | .862 -> .862 | .412 -> .412 | .865 -> .865 | .802 -> .802 | .836 -> .836 | .733 -> .733 |
| n017 | .911 -> .908 | .831 -> .831 | .848 -> .849 | .803 -> .870 | .878 -> .861 | .719 -> .710 |
| n02X | .901 -> .900 | .836 -> .839 | .905 -> .905 | .752 -> .780 | .769 -> .762 | .778 -> .764 |
| n01X | .841 -> .841 | .883 -> .883 | .845 -> .845 | .905 -> .905 | .875 -> .875 | .838 -> .838 |

spill do gate
| un. | front | left | back | top | bottom | rts |
|---|---|---|---|---|---|---|
| n005 | .053 -> .053 | .033 -> .038 | .051 -> .051 | .163 -> .116 | .079 -> .060 | .079 -> .073 |
| n00U | .064 -> .066 | .132 -> .134 | .071 -> .072 | .226 -> .217 | .239 -> .238 | .290 -> .272 |
| hfoo | .078 -> .078 | .392 -> .392 | .080 -> .080 | .097 -> .097 | .143 -> .143 | .206 -> .206 |
| n017 | .073 -> .070 | .060 -> .054 | .120 -> .119 | .088 -> .050 | .051 -> .060 | .214 -> .218 |
| n02X | .067 -> .067 | .096 -> .096 | .062 -> .061 | .205 -> .171 | .130 -> .123 | .131 -> .143 |
| n01X | .111 -> .111 | .080 -> .080 | .111 -> .111 | .040 -> .040 | .104 -> .104 | .124 -> .124 |

bare do gate
| un. | front | left | back | top | bottom | rts |
|---|---|---|---|---|---|---|
| n005 | .031 -> .030 | .026 -> .017 | .020 -> .018 | .108 -> .110 | .114 -> .135 | .054 -> .056 |
| n00U | .061 -> .064 | .060 -> .065 | .058 -> .060 | .069 -> .079 | .091 -> .090 | .162 -> .136 |
| hfoo | .070 -> .070 | .439 -> .439 | .065 -> .065 | .122 -> .122 | .028 -> .028 | .095 -> .095 |
| n017 | .018 -> .026 | .122 -> .128 | .042 -> .041 | .130 -> .088 | .079 -> .089 | .106 -> .115 |
| n02X | .037 -> .038 | .082 -> .079 | .037 -> .038 | .067 -> .070 | .132 -> .147 | .118 -> .124 |
| n01X | .060 -> .060 | .043 -> .043 | .056 -> .056 | .059 -> .059 | .026 -> .026 | .049 -> .049 |

- **Aceite |verts.after − gate| < .01 em 6 vistas × 6 unidades: 34 de 35 células medidas** (hfoo left não tem vista no otimizador: sheet incoerente, `VIEW_MIN`; gate .41 nos dois).
  A que sobra: **n00U rts +.030** (de +.126). Não é câmara: a máscara que o Blender gera (40 549 px, bbox 285 px de largura) é mais larga que o raster do glb nas mesmas
  coordenadas (35 730 px, 267 px); só o rts da aranha. Aberto: renderizador contra raster em pernas finas / pose do rig no rts.
- **IoU do gate subiu onde a lacuna era grande**: n005 top .761 → .797, n017 top .803 → .870, n02X top .752 → .780, n00U rts .624 → .653; spill de top cai em n005
  (.163 → .116), n017 (.088 → .050), n02X (.205 → .171). Custos pequenos: n017 bottom .878 → .861 e n02X rts .778 → .764, n02X bottom .769 → .762, bare de n017 bottom/rts +.01 e de n005 bottom +.02
  (o otimizador deixou de ganhar vista que o gate não mede; a conta fica honesta).
- **Decisão: default** (cumpre o aceite exceto uma célula documentada; não há flag). Não toquei em gates, pesos, SPILL/UNCOVERED nem `fit_spec` (L12-2/3).
- **Testes.** `test_optimize_verts.py` (3: `make_views` devolve a câmara pinada e a varrida difere; `optimize` relata os `cams`; `rts_view` pinado), `test_deform_to_sheet.py`
  (`best_oriented` só gira com margem; `run_cams` com `--tilts`). Suite completa: 655 testes OK.
  Runs: `runs/draft/<id>/l12-cams` (final), `l12-cams-pin` (só tilt pinado), controle `l12-ctl` fora do repo.

### 30.L12-2 Spill como gate, custo assimétrico, métrica `contact` (2026-10-29)

- **Regra do usuário.** "Pode ter verde sobrando, e pouco; vermelho não pode, em nenhum ângulo." Refinamento: modelo **inscrito e tangente** (dentro do verde, a encostar na borda por dentro).
- **Gate (default).** `silhouette.SPILL_MAX` = .03 e `UNCOVERED_MAX` = .10 por vista (antes .15–.25), as 6 vistas, sem média; `coupling_ok` já bloqueava, só os números mudaram.
  A linha do gate imprime `spill bare cont` ao lado do IoU (`(contact CHECK)` abaixo de `CONTACT_MIN` = .70); `silhouette.json` ganha `contact` por vista; `summary` e `review.md` (linha `contact`) também.
  `sdf_batch.py`: colunas spill / bare / contact por vista (antes média `unc / spill`) e `sil_fail` inclui vista acima dos tetos.
- **Custo assimétrico (opt-in).** `silhouette.asym_cost = (SPILL_W·spill px + BARE_W·bare px) / união px`: com os dois pesos em 1 é exatamente `1 − IoU`. Usado em
  `fit_spec.Proxy.view_score` (4.º valor; `loss` usa o custo em vez de `1 − IoU`), `optimize_verts.Ctx.cost` (objetivo duro) e `soft_sil.soft_iou` modo `sym` (gradiente suave, mesma fórmula), `deform_to_sheet.measure` (`score`,
  que `mean_iou`/`accept` usam; o guard "nenhuma vista cai" continua no IoU). `SPILL_W` lê `CF_SPILL_W` (default **1.0**), `BARE_W` = 1. `GRAD=fd` e `fit_grad.py` seguem simétricos.
- **`contact`.** `silhouette.contact`: fração dos pixels do contorno do sheet com contorno do modelo, **dentro do sheet**, a ≤ `CONTACT_EPS` (2 px) no canvas do gate. Quadrado igual ao sheet = 1; encolhido 4 px = 0; vazando = 0.
  Nota: encolhido exatamente 2 px ainda conta 1 (distância = eps, `≤`). Gate só CHECK nesta leva. Não entrou no custo do otimizador (`CONTACT_W` não existe): o custo já não fecha a lacuna, ver abaixo.
- **Medida** (6 unidades, sem LLM, bateria do L12-1; controle `l12-cams`, depois `l12-spill` com `CF_SPILL_W=3`; `contact` do controle recalculado das máscaras `sil/approved`). Antes -> depois, vistas f / l / b / top / bot / rts.

IoU
| un. | front | left | back | top | bottom | rts |
|---|---|---|---|---|---|---|
| n005 | .920 -> .898 | .946 -> .931 | .933 -> .921 | .797 -> .773 | .820 -> .765 | .878 -> .868 |
| n00U | .878 -> .860 | .818 -> .720 | .876 -> .865 | .734 -> .689 | .709 -> .669 | .653 -> .654 |
| hfoo | .862 -> .850 | .412 -> .387 | .865 -> .862 | .802 -> .765 | .836 -> .825 | .733 -> .704 |
| n017 | .908 -> .891 | .831 -> .789 | .849 -> .864 | .870 -> .814 | .861 -> .840 | .710 -> .700 |
| n02X | .900 -> .889 | .839 -> .831 | .905 -> .889 | .780 -> .759 | .762 -> .742 | .764 -> .760 |
| n01X | .841 -> .820 | .883 -> .889 | .845 -> .826 | .905 -> .859 | .875 -> .872 | .838 -> .843 |

spill
| un. | front | left | back | top | bottom | rts |
|---|---|---|---|---|---|---|
| n005 | .053 -> .047 | .038 -> .036 | .051 -> .039 | .116 -> .086 | .060 -> .039 | .073 -> .065 |
| n00U | .066 -> .061 | .134 -> .209 | .072 -> .064 | .217 -> .193 | .238 -> .202 | .272 -> .235 |
| hfoo | .078 -> .053 | .392 -> .422 | .080 -> .051 | .097 -> .071 | .143 -> .101 | .206 -> .208 |
| n017 | .070 -> .045 | .054 -> .057 | .119 -> .079 | .050 -> .064 | .060 -> .043 | .218 -> .217 |
| n02X | .067 -> .055 | .096 -> .099 | .061 -> .052 | .171 -> .114 | .123 -> .077 | .143 -> .101 |
| n01X | .111 -> .102 | .080 -> .047 | .111 -> .101 | .040 -> .020 | .104 -> .069 | .124 -> .096 |

bare
| un. | front | left | back | top | bottom | rts |
|---|---|---|---|---|---|---|
| n005 | .030 -> .060 | .017 -> .036 | .018 -> .043 | .110 -> .166 | .135 -> .210 | .056 -> .077 |
| n00U | .064 -> .088 | .065 -> .111 | .060 -> .081 | .079 -> .176 | .090 -> .194 | .136 -> .181 |
| hfoo | .070 -> .108 | .439 -> .461 | .065 -> .096 | .122 -> .187 | .028 -> .091 | .095 -> .137 |
| n017 | .026 -> .069 | .128 -> .171 | .041 -> .067 | .088 -> .138 | .089 -> .127 | .115 -> .132 |
| n02X | .038 -> .063 | .079 -> .085 | .038 -> .065 | .070 -> .159 | .147 -> .209 | .124 -> .169 |
| n01X | .060 -> .095 | .043 -> .070 | .056 -> .090 | .059 -> .126 | .026 -> .067 | .049 -> .074 |

contact
| un. | front | left | back | top | bottom | rts |
|---|---|---|---|---|---|---|
| n005 | .554 -> .500 | .614 -> .569 | .587 -> .615 | .127 -> .159 | .196 -> .118 | .281 -> .300 |
| n00U | .352 -> .344 | .299 -> .241 | .317 -> .342 | .133 -> .165 | .217 -> .161 | .110 -> .114 |
| hfoo | .456 -> .603 | .120 -> .102 | .496 -> .733 | .162 -> .112 | .179 -> .195 | .201 -> .172 |
| n017 | .471 -> .455 | .372 -> .394 | .331 -> .494 | .522 -> .383 | .438 -> .395 | .130 -> .117 |
| n02X | .496 -> .552 | .498 -> .495 | .504 -> .441 | .116 -> .078 | .138 -> .143 | .124 -> .164 |
| n01X | .512 -> .472 | .430 -> .546 | .506 -> .463 | .303 -> .205 | .204 -> .243 | .269 -> .291 |

- Vistas com spill ≤ .03 (antes -> depois, W=3): 0 -> 0 em n005, n00U, hfoo, n017, n02X; n01X 0 -> 1. Vistas com bare ≤ .10: n005 4 -> 4, n00U 5 -> 2, hfoo 4 -> 2, n017 4 -> 2, n02X 4 -> 3, n01X 6 -> 5.
  Pior IoU por unidade: n005 −.055 (bottom), n00U −.098 (left), hfoo −.036, n017 −.056, n02X −.021, n01X −.046; pior alta de bare: +.076, +.103, +.065, +.050, +.088, +.067.
- **Curva do peso** (n00U / hfoo / n02X; média das 6 vistas; W=1 = controle):

| un. | W | IoU | spill | bare | vistas spill ≤ .03 | vistas bare ≤ .10 |
|---|---|---|---|---|---|---|
| n00U | 1 | .778 | .166 | .082 | 0 | 5 |
| n00U | 1.5 / 3 / 5 / 10 | .754 / .743 / .733 / .724 | .159 / .161 / .158 / .159 | .125 / .139 / .155 / .165 | 0 / 0 / 0 / 0 | 2 / 2 / 1 / 0 |
| hfoo | 1 | .752 | .166 | .137 | 0 | 4 |
| hfoo | 1.5 / 3 / 5 / 10 | .745 / .732 / .729 / .725 | .152 / .151 / .148 / .150 | .160 / .180 / .185 / .188 | 0 / 0 / 0 / 0 | 3 / 2 / 0 / 0 |
| n02X | 1 | .825 | .110 | .083 | 0 | 4 |
| n02X | 1.5 / 3 / 5 / 10 | .824 / .812 / .806 / .799 | .087 / .083 / .085 / .087 | .107 / .125 / .130 / .136 | 0 / 0 / 0 / 0 | 3 / 3 / 3 / 3 |

- **Veredito: aceite NÃO cumprido.** O spill cai em ≥ 4 vistas em 5 de 6 unidades (n005 6, n00U 5, hfoo 4, n02X 5, n01X 6; n017 3), mas só por .00–.06 (nenhuma vista chega a .03) e à custa de bare: sobe > .03 em ≥ 3 vistas de cada unidade e o IoU perde até .10 (n00U left). A curva satura em W≈1.5:
  mais peso só troca vermelho por bare, o spill médio fica em ~.15. Causa: o contorno do modelo (vértices + SDF) não consegue encostar por dentro do sheet; encolher o spill vira bare quase 1:1 (n005 front verts: spill .065→.044, bare .039→.060).
  O limite está na capacidade de forma (L12-3/L12-4: preflight e massing), não no peso. **Decisão:** gate .03/.10 default (regra do usuário; todas as 6 unidades agora FAIL honesto no stage 1); custo assimétrico e `contact` no custo ficam fora: `CF_SPILL_W` opt-in, `contact` só relatório.
- **SDF (item 3).** Não re-medi o volume: `sdf_thin`/`drop_specks` só removem; o smin (L11-5) acrescentou +0.2–0.7 % de volume, ordem de grandeza menor que o spill de .03–.2 medido aqui; sem proposta de k por spill.
- **Testes.** `test_silhouette.SpillGate` (contact: igual = 1, encolhido = 0, vazando = 0, vazio = 0; gate .04 falha e .03 passa; bare .11 falha; vazar 2 % custa mais que deixar 2 % descoberto; pesos 1 = 1 − IoU),
  `test_optimize_verts` (`Ctx.cost` = 1 − IoU com pesos 1 e pesa o lado certo com W=3); ajustados `test_soft_sil` (tetos uniformes), `test_sdf_batch` (front agora FAIL), `test_optimize_verts` (IoU sobe com `SPILL_W=1`).
  Regressão do default (W=1, `l12-spill-w1`, n00U / hfoo / n02X): n00U e n02X idênticos ao `l12-cams` (IoU das 6 vistas, diferença 0); hfoo ≤ .016 (orçamento por relógio do `fit-verts`, lição L11-2).
  Runs: `runs/draft/<id>/l12-spill` (W=3, 6 unidades), `l12-spill-w{1.5,5,10}` (3 unidades), `l12-spill-w1` (default, regressão = `l12-cams`).

### 30.L12-3 Guarda autor-vs-massing (2026-10-29)

- **Por que.** O pré-spec determinístico (`massing.py`) já dava 90-100 % do IoU final e o autor LLM piorou vistas (v13-r1: hfoo left .719 -> .415, n017 top .920 -> .822), mas só o final era tabelado. A guarda do laço v14 (`loop_accept`) olha round 0 contra rounds, não o autor contra o massing.
- **Mudança.** `tools/blender/author_guard.py` (funções puras sobre dicts de spec + um proxy com `ious(parts)`): `drops` (vista do autor > `AUTHOR_DROP` = .01 abaixo do massing), `revert` (guloso sobre o proxy 2D de `fit_spec.Proxy`: reverte ao massing o osso que mais ganha IoU nas vistas caídas, até o ganho estimado cobrir a queda real), `reject` (corpo do massing + props e paleta do autor; `props=False` = o próprio massing).
  `spec_pipeline.py`: `--author-guard revert|reject|off` (**default `off`**, ver decisão), `guard_stage` (depois do autor/best-of-N, antes do reparo e do fit), `guard_fit` (depois do fit), `guard_section` em `review.md` ("Author guard": IoU e spill por vista em cada estágio: massing, autor pré-fit, o que a guarda tentou, fit descartado, final; ossos revertidos e vistas que caíram), `silhouette.json` ganha `guard` (linhas por estágio, ação, quedas, ossos).
  Escada: `revert` (modo revert) -> medir de novo -> `reject` (massing + props do autor) -> medir -> `reject-bare` (o massing inteiro, sem medir: é o que o estágio 0 já mediu). Massing e autor são medidos como estágio 1 (build + deform + verts, **sem** fit) nas **mesmas câmaras pinadas** (`--tilts`); com `--spec` o massing vem de `<spec>/../massing/spec.json`. `guard_fit`: se o fit empurra uma vista > .01 abaixo do massing, o spec fica como estava antes do fit e é construído de novo (o fit sobre o massing puro, avaliado em clay liso, piorou hfoo e n02X no final).
- **Duas medidas descartadas no caminho** (runs `l12-guard-plain`, `-nofitguard`, `-bareprops`, mantidos): (1) comparar o clay liso (só `build_unit`) do massing e do autor: o massing liso é muito pior que o final (hfoo top .49 contra .80), deform/verts só rodam no massing final; não vê o n017 top. (2) o "massing final" tabelado no v13 (n017 top .920) usa o tilt que o massing varreu; com a câmara pinada o massing dá .849 e o autor .854: a queda "n017 top .920 -> .822" do peer review era em boa parte câmara diferente (a mesma lacuna do L12-1), não o autor.
- **Medida** (6 unidades, sem LLM, `--spec v13-r1/spec.json --tilts` do v13-r1, `--no-repair --no-diagnose --body sdf --deterministic --author-guard revert`; controle `l12-cams`). Vistas front / left / back / top / bottom / rts.

IoU (massing / autor pré-fit / final sem guarda = `l12-cams` / final com guarda = `l12-guard`)

| un. | estágio | front | left | back | top | bottom | rts | média |
|---|---|---|---|---|---|---|---|---|
| n005 | massing | .899 | .945 | .921 | .809 | .839 | .831 | .874 |
|  | autor | .921 | .946 | .933 | .797 | .819 | .878 | .883 |
|  | sem guarda | .920 | .946 | .933 | .797 | .820 | .878 | .882 |
|  | guarda (revert) | .925 | .946 | .934 | .799 | .833 | .880 | .886 |
| n00U | massing | .871 | .747 | .874 | .697 | .638 | .621 | .741 |
|  | autor | .877 | .793 | .879 | .711 | .677 | .631 | .761 |
|  | sem guarda | .878 | .818 | .876 | .734 | .709 | .653 | .778 |
|  | guarda (intact) | .878 | .818 | .876 | .734 | .709 | .653 | .778 |
| hfoo | massing | .794 | .707 | .791 | .655 | .703 | .619 | .712 |
|  | autor | .864 | .406 | .868 | .815 | .853 | .709 | .752 |
|  | sem guarda | .862 | .412 | .865 | .802 | .836 | .733 | .752 |
|  | guarda (reject-bare) | .794 | .707 | .791 | .655 | .703 | .619 | .712 |
| n017 | massing | .908 | .793 | .861 | .849 | .897 | .725 | .839 |
|  | autor | .904 | .792 | .860 | .854 | .858 | .730 | .833 |
|  | sem guarda | .908 | .831 | .849 | .870 | .861 | .710 | .838 |
|  | guarda (reject-bare) | .909 | .823 | .857 | .847 | .898 | .720 | .842 |
| n02X | massing | .877 | .847 | .887 | .791 | .758 | .750 | .818 |
|  | autor | .898 | .839 | .905 | .779 | .762 | .764 | .825 |
|  | sem guarda | .900 | .839 | .905 | .780 | .762 | .764 | .825 |
|  | guarda (reject-bare) | .877 | .843 | .887 | .793 | .758 | .748 | .818 |
| n01X | massing | .839 | .895 | .841 | .833 | .821 | .838 | .844 |
|  | autor | .847 | .885 | .850 | .904 | .875 | .838 | .867 |
|  | sem guarda | .841 | .883 | .845 | .905 | .875 | .838 | .865 |
|  | guarda (intact) | .841 | .883 | .845 | .905 | .875 | .838 | .865 |

spill (massing / autor pré-fit / final sem guarda = `l12-cams` / final com guarda = `l12-guard`)

| un. | estágio | front | left | back | top | bottom | rts | média |
|---|---|---|---|---|---|---|---|---|
| n005 | massing | .059 | .031 | .052 | .107 | .052 | .135 | .073 |
|  | autor | .053 | .039 | .051 | .116 | .060 | .074 | .066 |
|  | sem guarda | .053 | .038 | .051 | .116 | .060 | .073 | .065 |
|  | guarda (revert) | .045 | .038 | .045 | .123 | .057 | .067 | .062 |
| n00U | massing | .089 | .210 | .092 | .251 | .272 | .287 | .200 |
|  | autor | .075 | .163 | .079 | .240 | .274 | .310 | .190 |
|  | sem guarda | .066 | .134 | .072 | .217 | .238 | .272 | .166 |
|  | guarda (intact) | .066 | .134 | .072 | .217 | .238 | .272 | .166 |
| hfoo | massing | .129 | .192 | .131 | .037 | .022 | .312 | .137 |
|  | autor | .064 | .406 | .066 | .108 | .107 | .230 | .163 |
|  | sem guarda | .078 | .392 | .080 | .097 | .143 | .206 | .166 |
|  | guarda (reject-bare) | .129 | .192 | .131 | .037 | .022 | .312 | .137 |
| n017 | massing | .064 | .073 | .107 | .078 | .073 | .221 | .103 |
|  | autor | .069 | .092 | .110 | .087 | .062 | .202 | .103 |
|  | sem guarda | .070 | .054 | .119 | .050 | .060 | .218 | .095 |
|  | guarda (reject-bare) | .065 | .055 | .106 | .075 | .064 | .216 | .097 |
| n02X | massing | .096 | .081 | .088 | .178 | .154 | .118 | .119 |
|  | autor | .067 | .096 | .060 | .172 | .121 | .141 | .110 |
|  | sem guarda | .067 | .096 | .061 | .171 | .123 | .143 | .110 |
|  | guarda (reject-bare) | .096 | .085 | .088 | .175 | .154 | .121 | .120 |
| n01X | massing | .136 | .079 | .136 | .046 | .156 | .125 | .113 |
|  | autor | .113 | .079 | .113 | .041 | .104 | .123 | .096 |
|  | sem guarda | .111 | .080 | .111 | .040 | .104 | .124 | .095 |
|  | guarda (intact) | .111 | .080 | .111 | .040 | .104 | .124 | .095 |

- **Ação por unidade.** n005: revert (forearm.L/R; top e bottom do autor caíam .012/.020, +.002/+.014 depois). n00U, n01X: intactos (nenhuma vista abaixo do massing; resultado = `l12-cams`). hfoo: a queda é left (.406 contra .707) e nenhum osso a explica sozinho no proxy (cada reversão ganha <= .01); `revert` e `reject` (com props) seguem caindo (.416 / .383) -> `reject-bare`; o fit sobre o massing derrubava top/bottom/rts -> `guard_fit` descarta -> final = massing. n017: queda bottom (.858 contra .897); revert e reject não resolvem (bottom .851 / .865) -> `reject-bare`, o fit mantém (sem queda). n02X: top .779 contra .791 (-.012); revert/reject não resolvem -> `reject-bare`; o fit derrubava left -> descartado -> final = massing.
- **Aceite.** hfoo left >= massing - .01: **sim** (.707 = massing). n017 top >= massing - .01: **sim** (.847 contra .849). Nenhuma unidade com vista abaixo do massing - .01 no final: **sim** (n005 top .799 contra .809 é o limite exato). IoU médio não cai: **NÃO**: média das 6 unidades .823 (sem guarda) -> .817; n005 +.004, n017 +.004, n00U/n01X 0, n02X -.007, **hfoo -.040** (o autor ganha .16 em top/bottom/rts e perde .30 em left; o piso por vista abre mão disso). Spill: não é objetivo da guarda; hfoo left .392 -> .192 (por rejeitar o autor), n005 .065 -> .062, n017 .095 -> .097, n02X .110 -> .120; o gate (spill <= .03) segue FAIL nas 6, sem arredondar.
- **Decisão: opt-in** (`--author-guard revert`; default `off`), porque o aceite do IoU médio falha em hfoo (e n02X -.007). A guarda cumpre o piso por vista; o preço é o autor inteiro nas unidades em que uma vista cai. Para virar default falta atribuir a queda por parte com mais de um osso (hfoo left é global: o autor deslocou o z de todas as peças) ou um `reject` parcial por região.
- **Aberto.** (a) Atribuição multi-osso (busca por pares ou por grupo de simetria) para o hfoo left; (b) quando `massing_stage` já rodou (sem `--spec`) a medida do massing é refeita em `guard/massing/` (um estágio 1 a mais; reaproveitar `massing_report` exigiria spill nele); (c) `sdf_batch.py` não tem as colunas massing/autor/final: a tabela acima foi montada do `silhouette.json["guard"]`; (d) o autor LLM de verdade (v15) com a guarda ligada não foi medido (sem LLM nesta leva).
- **Testes.** `test_author_guard.py` (11, sem Blender): `drops` no limite; `revert` reverte o osso da vista caída e mantém props/paleta, nada cai -> nada muda, nenhum osso ajuda; `reject` com e sem props; `guard_stage` com os builds simulados (`off` não faz nada, sem queda deixa o spec, queda -> revert, revert que não resolve -> reject-bare); `guard_fit` (fit mantido / fit descartado). Suite completa: ver commit.
  Runs: `runs/draft/<id>/l12-guard` (final), `l12-guard-plain`, `l12-guard-nofitguard`, `l12-guard-bareprops` (versões descartadas, fora do repo se ignorados).

### 30.L12-4 Stage 2 sempre, FAIL(infra), teste "flag viva" (2026-10-29)

- **Por que.** Com o gate honesto do L12-2 as 6 unidades falham o estágio 1 e `run_colour` só corria com `shape["ok"]`: nenhuma ganhava textura, `model.glb` nem turntable, e o juiz de look (e a ficha) avaliava o clay cinzento, o que invalida qualquer comparação de look entre runs. Um estágio que não escreve o ficheiro virava `None`/"skipped" e o veredito seguia (`CHECK`/`SHAPE-PASS`). Flags opt-in sem teste podiam não fazer nada sem ninguém ver (`--fit-parts`/`--depth` corriam sem efeito).
- **Mudança** (`tools/blender/spec_pipeline.py`, `fit_spec.py`, `parts_fit.py`, `sdf_batch.py`).
  1. Stage 2 corre sempre (`wants_colour`: não `--shape-only`, há `clay.glb`, e stage 1 ok **ou** `--colour-on-fail on`, default). `--colour-on-fail off` = regra antiga. A semântica do veredito não muda: stage 1 FAIL + stage 2 ok = `CHECK`, nunca `PASS`. O turntable passa a ser filmado sempre que `model.glb` existe (antes só com o gate de cor ok). `review.md` mostra a secção de cor também nos runs que falharam o estágio 1.
  2. `infra_check(args, shape, colour) -> list[str]` no fim do run: preflight sem linha "rules pass", `clay.glb` não construído, `clay.deform.json` (deform on, corpo unido), `clay.verts.json` (fit-verts on), `silhouette.json` (sem `--no-silhouette`), `spec.json`, e se o stage 2 era devido: módulo `colour_stage` ausente, `model.glb`, `stage2/colour.json`, `turntable.gif`. Lista não vazia = veredito **`FAIL(infra)`** (linha impressa, secção `## FAIL(infra)` no `review.md`, `infra.json` no run, coluna de veredito do `sdf_batch.py`), **exit 2** (gate = exit 1). `--shape-only`, `--colour-on-fail off` após estágio 1 falho, `--no-silhouette`, `--no-deform`, `--no-fit-verts` e `--body join` justificam a ausência do que cada um não escreve.
  3. `tests/tools/blender/test_flag_liveness.py` (sem Blender): `SP.build_parser()` (extraído de `main`) é introspectado; cada argumento tem de estar na tabela como `live` (ligar muda uma chamada/número do módulo que o consome: família do fit via `fit_stage` com `fit_spec.fit` falso, `clay_args`/`sdf_body.pair_k`/`retopo.retopo` para `--body/--sdf-*`, `guard_stage`, `run_loop`, `stage_colour` para `--fit-luma`, `silhouette.asym_cost` para `CF_SPILL_W`, `wants_colour`), `noop` (`noop_notes(args)` imprime `no-op: <flag>: <razão>` quando a precondição falta: `--ramp/--fit-luma/--atlas/--materials` fora do `cel`, flags do fit com `--no-fit`, `--colour-pass` com `--shape-only`, `--sdf-*` fora de `--body sdf`, `--align` com `--body join`, `--loop` sem round 0 aprovado, `--author-guard` sem massing, `--fit-parts/--depth/--parts` sem `parts.json` ou sem `box3d`) ou `plain` (entrada/rótulo lido em todo run); mais uma varredura estática: todo `dest` é lido (`args.<dest>`) por algum módulo de `tools/blender`, e todo `CF_*` do código está na tabela `ENV`. Um argumento novo sem linha, uma linha órfã ou um `dest` que ninguém lê falha o teste.
- **Flags mortas encontradas.**

| flag | achado | ação |
|---|---|---|
| `--flat` | nenhum módulo lê `args.flat` (texto: "stage 2: skip the painted texture"; a textura painted já não é o default) | removida do parser |
| `--fit-parts` / `--depth` / `--parts` | `refs/<id>/parts.json` com `box3d: null` em **7 de 8** ficheiros (hfoo 1/15 partes, n005 3/18, n00H 3/7, n00U 5/13, n010 9/17, n017 6/13, n01X 3/20; só n02X 0/21); `associate` iterava `None` | `parts_fit.associate` pula parte sem `box3d`; `fit_spec.attach_parts` imprime `no-op: ... parts.json has no box3d` e segue sem termos de parte quando **todas** são nulas, e `no-op: ... no parts.json` quando não há ficheiro. Raiz = o dado (a regeneração dos box3d nulos fica aberta), a flag deixou de falhar calada |
| `--author-guard` sem massing | `guard_stage` voltava em silêncio | imprime `no-op: --author-guard ...: no massing spec` |
| `--loop` sem round 0 aprovado | `run_loop` voltava em silêncio | imprime `no-op: --loop: no approved round 0` |
| `--ramp`, `--fit-luma`, `--atlas`, `--materials` com `--texture painted/sheet` | só o `cel` os lê | `noop_notes` |
| `--sdf-grid/--sdf-k-mode/--sdf-retopo` com `--body union/join` | `clay_args` só os passa com `--body sdf` | `noop_notes` |
| `CF_SPILL_W`, `--sdf-k-mode`, `--sdf-retopo`, `--fit-grad`, `--fit-luma`, `--loop`, `--author-guard` | vivos: o teste prova que mudam a chamada/o número do consumidor | `live` na tabela |

  Limite do teste: para as flags do fit prova que chegam ao parâmetro de `fit_spec.fit` (a fronteira do módulo), não que o parâmetro mexa no número; isso é dos testes de `fit_spec`/`fit_grad`. Para `--flip-side`/`--frame` e as de `colour_stage` só a leitura estática (lidas por `silhouette.py`/`colour_stage.py` via `args`/`os.environ`).
- **Medida** (bateria das 6, sem LLM, `--spec v13-r1/spec.json --no-repair --no-diagnose --body sdf --deterministic --tilts` do v13-r1, run `l12-stage2`; controlo `l12-cams` = mesmo estágio 1 sem stage 2).

| un. | veredito antes | veredito depois | stage 1 | stage 2 (gate de cor) | model.glb / turntable | t stage 2 | infra |
|---|---|---|---|---|---|---|---|
| n005 | CHECK, sem textura | CHECK com textura | FAIL (gates L12-2) | PASS (front .71 / left .73 / back .68 / top .48 / bottom .31 de média por zona) | sim / sim | 37.6 s | [] |
| n00U | CHECK, sem textura | CHECK com textura | FAIL | PASS | sim / sim | 38.7 s | [] |
| hfoo | CHECK, sem textura | CHECK com textura | FAIL | PASS | sim / sim | 45.2 s | [] |
| n017 | CHECK, sem textura | CHECK com textura | FAIL | PASS | sim / sim | 36.8 s | [] |
| n02X | CHECK, sem textura | CHECK com textura | FAIL | PASS | sim / sim | 38.3 s | [] |
| n01X | CHECK, sem textura | CHECK com textura | FAIL | PASS | sim / sim | 35.3 s | [] |

  IoU do estágio 1 igual ao `l12-cams` (|Δ| = 0.000 em 5 de 6; hfoo +.005..+.016 por vista, ruído do fit entre rodadas: não investigado). Exit 1 (CHECK) nas 6, nenhum 2. Custo: ~36-45 s por unidade (o gate de cor, uma build `cel` e o turntable).
- **Aceite.** 6/6 texturizados com turntable: **sim**. 0 flags mortas (teste verde, `--flat` removida): **sim**. 0 `FAIL(infra)` na bateria: **sim**.
- **Decisão: default** (`--colour-on-fail on`). Não toquei nos gates do estágio 1 (L12-2), na guarda (L12-3), na câmara (L12-1), nos pesos de vista (L12-5) nem no preflight (L12-6).
- **Aberto.** (a) Regenerar os `box3d` nulos de `refs/*/parts.json` (7 de 8 ficheiros) para `--fit-parts/--depth` terem efeito; (b) o teste prova a ligação ao consumidor, não o ganho: a ablação de cada opt-in segue sendo medida; (c) o `sdf_batch.py` não gera `results.csv` (só `l10-batch.json` + tabela): a coluna de veredito mostra `FAIL(infra)`; (d) `infra_check` não vê exceção engolida dentro de um estágio que ainda escreve o ficheiro.
- **Testes.** `test_flag_liveness.py` (10), `test_spec_pipeline.py` (+3: `verdict_of` com infra, `wants_colour`, `infra_check`), `test_sdf_batch.py` (+1). Runs: `runs/draft/<id>/l12-stage2`.

### 30.L12-5 Vista incoerente com peso 0 (opt-in) e gate no corpo, prop em CHECK (2026-10-29)

- **Por que.** (1) `VIEW_WEIGHTS` dava peso 2 a top/bottom/rts de spider/quadruped, também quando `sheet_report` marca a vista como `incoherent` (n00U top .53 / bottom .49; n017 rts .58; hfoo rts .57): o fit puxava com força dupla para um desenho que não é do boneco. (2) O gate misturava corpo e prop (hfoo left: o pique atravessa o painel).
- **Mudança.**
  1. `views.weight_of(rig, view, sheet_report=None, incoherent_weight=None)`: vista em `sheet_report["incoherent"]` pesa `views.INCOHERENT_WEIGHT` (ou o argumento) qualquer que seja o rig; senão `VIEW_WEIGHTS`. Quem fitta recebe o relatório: `fit_spec.Proxy(sheet_rep=)` / `fit(sheet_rep=)` (vista de peso 0 também sai de `failing`), `deform_to_sheet.deform/run(sheet_rep=)` (peso 0 = não puxa, não vigia a `GUARD`, não entra no `mean_iou`), `optimize_verts.optimize/run(sheet_rep=)` (peso 0 = vista fora do objetivo; peso > 0 = vista a 1, `ponytail: escalar o custo quando uma matriz pedir 0 < w < 1`). `silhouette.run_report(args)` calcula `sheet_report` uma vez por run. Flag `spec_pipeline --incoherent-weight <float>`, default **None** (= como qualquer vista, comportamento anterior).
  2. Gate: a vista incoerente já era isenta (`verdict_of`); agora imprime `(incoherent, not gated)` e `sdf_batch.sil_fail` também a isenta (antes n00U/n017/hfoo falhavam por ela na tabela). `sdf_batch` marca com `†` IoU/spill/bare/contact das vistas incoerentes; os números brutos continuam todos impressos.
  3. Corpo vs prop (`silhouette.body_prop_scores`, só onde há `prop_masks`): `body_{iou,spill,bare}` e `prop_{iou,spill,bare}` por vista, no `silhouette.json`, no `review.md` (linhas `body iou (gate)`/`prop iou (CHECK)`...) e em `sdf_batch.split_table`. O **gate** (`gated_values`: IoU mínimo, `SPILL_MAX`, `UNCOVERED_MAX`) aplica-se ao corpo; o prop é CHECK impresso (`[body ... | prop CHECK ...]` na linha da vista). Nomes com prefixo (`body_spill`) porque `spill_body`/`spill_prop` já existiam com outra semântica (partição do total, `coupling_split`).
  4. **Limite da separação (importante).** O modelo é um mesh só (`spec`, skin) e o prop não é marcável depois do weld/deform; não renderizei o prop à parte. A separação é por pixel (a mesma atribuição de `coupling_split`): sheet-corpo = painel menos máscaras de prop; modelo-prop = pixels do modelo dentro de uma máscara de prop ou fora do sheet a ≤ `PROP_NEAR` (6 px) de uma. Um prop desenhado longe da sua máscara (o pique vertical do modelo contra o diagonal do sheet) cai como **spill do corpo**, e as colunas de prop dele (hfoo left: IoU .09, bare .90) dizem só "o pique do sheet não está coberto".
- **Medida** (bateria das 6, sem LLM, `v13-r1/spec.json --no-repair --no-diagnose --body sdf --deterministic --tilts`; controlo `l12-stage2`; runs `l12-views` (default, `None`), `l12-views-w0` (`--incoherent-weight 0`), `l12-views-w1` (`1.0`, só n00U/n017/hfoo)). IoU / spill / bare, vistas coerentes e incoerentes (†).

| un. | vista | controlo = default | `w=0` | `w=1` |
|---|---|---|---|---|
| hfoo | front | .867 / .061 / .081 | .858 / .064 / .089 | .870 / .073 / .066 |
| hfoo | left | .418 / .387 / .432 | .409 / .403 / .436 | .411 / .380 / .451 |
| hfoo | back | .874 / .061 / .074 | .867 / .063 / .080 | .874 / .072 / .062 |
| hfoo | top | .818 / .105 / .095 | .812 / .104 / .103 | .829 / .105 / .082 |
| hfoo | bottom | .843 / .139 / .024 | .857 / .098 / .055 | .849 / .112 / .049 |
| hfoo | rts † | .730 / .200 / .107 | .675 / .245 / .135 | .701 / .237 / .105 |
| n00U | front | .878 / .066 / .064 | .883 / .064 / .060 | .874 / .076 / .058 |
| n00U | left | .818 / .134 / .065 | .812 / .135 / .070 | .809 / .121 / .090 |
| n00U | back | .876 / .072 / .060 | .884 / .068 / .055 | .873 / .082 / .053 |
| n00U | top † | .734 / .217 / .079 | .700 / .248 / .091 | .706 / .236 / .098 |
| n00U | bottom † | .709 / .238 / .090 | .652 / .302 / .091 | .694 / .269 / .069 |
| n00U | rts | .653 / .272 / .136 | .635 / .301 / .125 | .649 / .287 / .121 |
| n017 | front | .908 / .070 / .026 | .899 / .074 / .032 | .917 / .064 / .022 |
| n017 | left | .831 / .054 / .128 | .796 / .094 / .133 | .850 / .059 / .102 |
| n017 | back | .849 / .119 / .041 | .864 / .110 / .033 | .864 / .109 / .033 |
| n017 | top | .870 / .050 / .088 | .845 / .085 / .084 | .885 / .063 / .059 |
| n017 | bottom | .861 / .060 / .089 | .851 / .059 / .102 | .865 / .058 / .087 |
| n017 | rts † | .710 / .218 / .115 | .682 / .262 / .100 | .727 / .217 / .090 |

  n005, n02X, n01X (sem vista incoerente): idênticas ao controlo nas 3 colunas de números (|Δ| = 0.000; o default não mexe em nada). Com o default (`None`) as 6 unidades reproduzem o controlo `l12-stage2` exatamente.

  Corpo / prop onde há prop (default; `corpo IoU / spill / bare`, `prop IoU / spill / bare`):

| un. | vista | corpo (gate) | prop (CHECK) |
|---|---|---|---|
| hfoo | front | .906 / .059 / .039 (inteiro .867 / .061 / .081) | .47 / .08 / .51 |
| hfoo | left | .544 / .373 / .195 (inteiro .418 / .387 / .432) | .09 / .54 / .90 |
| n005 | front, left | .923 / .053 / .027, .948 / .036 / .017 | .73 / .01 / .27, .94 / .05 / .02 |
| n00U | front, left | .863 / .074 / .073, .817 / .135 / .064 | .93 / .04 / .03, .85 / .05 / .11 |
| n02X | front, left | .908 / .065 / .031, .840 / .096 / .077 | .80 / .10 / .13, .69 / .00 / .31 |
| n01X | front | .854 / .112 / .044 | .75 / .11 / .18 |

- **Porquê falha** (default; letras = o que quebra no corpo/inteiro: I = IoU < gate, S = spill > .03, B = bare > .10).

| un. | falha por corpo | falha só por prop | vista incoerente (não gated) |
|---|---|---|---|
| n005 | front S, left S, back S, top SB, bottom SB, rts S | nenhuma | nenhuma |
| hfoo | front S, **left ISB**, back S, top S, bottom S | nenhuma | rts (SB) |
| n00U | front S, left S, back S, rts ISB | nenhuma | top (S), bottom (S) |
| n017 | front S, left SB, back S, top S, bottom S | nenhuma | rts (SB) |
| n02X | front S, left S, back S, top S, bottom SB, rts SB | nenhuma | nenhuma |
| n01X | as 6 vistas S | nenhuma | nenhuma |

  Em nenhuma vista o prop sozinho explica a falha: o corpo já excede `SPILL_MAX` (.03) em todas, e em hfoo left o corpo falha em tudo (IoU .54, spill .37). O que a separação muda é o número: hfoo front IoU .867 → .906 (corpo), left .418 → .544, bare .43 → .20.
- **Aceite.** `hfoo left (corpo) >= .70`: **não** (.544; o spec v13-r1 tem o pique/mochila fora do painel; a guarda L12-3 que o levava a .707 precisa do autor LLM). Vistas coerentes de n00U/n017/hfoo não caem (> ruído .016) e uma sobe: **default** (sem mudança) trivial; **`w=0` não** (n017 left −.035, top −.025, front −.009 com spill +.04 em left/top; é pior que o controlo, porque tirar o rts do otimizador solta o resto); **`w=1`** sim em IoU (n017 melhora 5/5 coerentes: left +.019, top +.015, back +.015; n00U ≥ −.009; hfoo ≥ −.007) mas o spill de front/back sobe +.010 em hfoo e n00U. FAIL por "sheet incoerente" vs "modelo errado" tabelado por unidade: **sim**. Aceite global: **não**.
- **Decisão: opt-in** (`--incoherent-weight`, default `None` = comportamento anterior). O gate no corpo e as colunas corpo/prop são default (só mudam o veredito onde há prop e só a favor do corpo; n005/hfoo/n00U/n02X/n01X: o corpo é igual ou melhor que o inteiro nos números de gate, nenhum veredito virou PASS: o spill de corpo > .03 em todas). Não mexi em `COHERENCE_MIN`, `SPILL_MAX`/`UNCOVERED_MAX`, guarda, câmara, stage 2 nem preflight.
- **Aberto.** (a) Separar o prop de verdade: marcar as faces de prop (material/atributo) em `build_unit` e renderizá-las à parte, para o pique mal posto não cair como spill do corpo; (b) n=3 unidades, 1 repetição de `w=1`; o ruído do fit entre rodadas é ~.016: repetir antes de ligar; (c) peso 0 < w < 1 no `optimize_verts` (hoje todo w > 0 vale 1); (d) hfoo left só passa com a guarda e o autor.
- **Testes.** `test_views.WeightOf`, `test_fit_spec.ViewWeights` (+1: mudar o painel de uma vista incoerente não muda o custo), `test_silhouette.BodyProp` (3: corpo certo + prop errado passa o corpo e deixa o prop em CHECK; corpo vaza falha; sem prop = inteiro), `test_sdf_batch` (+1), `test_flag_liveness` (+1: `incoherent_weight` viva). Runs: `runs/draft/<id>/l12-views{,-w0,-w1}`.


### 30.L12-6 Regras da DSL viram preflight: `hood_recess`, `prop_axis`/`prop_coverage`, `leg_joints` (2026-10-29)

- **Por que.** HOODS, props com eixo e patas de aranha eram prosa em `spec_pipeline.DSL` sem nenhuma função no preflight ("regra sem preflight não existe"). O autor violou as três nos specs v13 e nada acusou.
- **Mudança.** `tools/blender/dsl_rules.py` (novo): `checks(parts, doc, sheet, na=)` -> `([(regra, passou, detalhe)], {regra: razão n/a})` e `repair(parts, doc, sheet, opt_in=)` -> `(parts, [(regra, peça, antes, depois)])`. `preflight.checks_of` anexa as regras (duras onde se aplicam; `preflight.py` imprime `n/a: <razão>`, nunca PASS, quando não se aplicam), `preflight.py --fix <out.json> [--dsl-repair on|off|all]` escreve o spec reparado. `spec_pipeline.dsl_stage` corre o reparo depois da guarda do autor e antes do fit (também com `--no-repair`: é código, não LLM), `--dsl-repair off|on|all` (default `on`), seção `## DSL rules` no `review.md` (regra, antes -> depois, cada reparo) e `dsl` no `silhouette.json`.
  1. `hood_recess` (biped com capuz: `parts.json` nomeia `hood|cowl|capuz` no osso head, ou opts `hood`): FAIL se (a) não há peça de cara (osso head, opts `decal`) além do capuz, (b) a face da frente da cara não está >= `HOOD_RECESS_MIN` (.15) da profundidade do capuz à frente da parede de trás e >= `HOOD_MOUTH_GAP` (.05 H) atrás da boca, (c) capuz com profundidade < `HOOD_DEEP_MIN` (.6) x largura. Reparo: aprofunda o capuz (parede de trás fixa), move a cara em z para a janela, ou cria uma `frustum` de cara (dims da peça `face` do `parts.json`) que leva o decal.
  2. `prop_axis` / `prop_coverage` (peças `is_prop`, máscaras de `silhouette.prop_masks` em front/left): a peça projetada no canvas do painel (`frame_of`: bbox do spec -> 256x384, melhor espelho e deslize como `hull_outside`, máscara e projeção crescidas `PROP_PAD`=2 px) tem eixo PCA a <= 15 graus do da máscara (só se os dois têm elongação >= 2) e IoU >= .50. Reparo: gira o grupo do prop (posições de `at`/`from`/`to`, `rot` onde a DSL deixa) pelo ângulo medido no plano da vista e escala o comprimento ao da máscara (0.6-1.6); só age quando a regra falha, desfaz se piora ângulo e IoU.
  3. `leg_joints` (rig spider/spider_high): cada pata (`legN.upper` + `legN.lower`, ou `limb`) tem junta >= `LEG_BEND_MIN` (15 graus) **e** a tíbia (joelho -> pé em planta) alcança >= .5 x a do sheet (`rig_measure.legs`, casadas por azimute do pé). Reparo: joelho e pé nas posições (x, z) do sheet para aquela pata e o joelho em `knee_h`; pata de 1 peça é dividida em 2 (25 graus a meio da corda se o sheet não dá linha).
- **Medida** (bateria das 6, sem LLM, `v13-r1/spec.json --no-repair --no-diagnose --body sdf --deterministic --tilts`; controlo `l12-stage2`; run `l12-preflight` = default `on`, `l12-preflight-all` = `--dsl-repair all` só n005; ruído `noise-l12.json`, marca quando |Δ| > max(2σ, .005)).

Regras novas, antes -> depois do reparo (default `on`):

| un. | hood_recess | prop_axis | prop_coverage | leg_joints |
|---|---|---|---|---|
| n005 | **FAIL** (sem peça de cara) -> FAIL (`all`: PASS) | PASS | **FAIL** (vaporiser .23) -> FAIL (`all`: .32) | n/a: biped |
| n017 | n/a: quadruped | n/a: sem máscara de prop | n/a: sem máscara de prop | n/a: quadruped |
| n00U | n/a: spider | n/a: sem prop | n/a: sem prop | **FAIL** (tíbia .00-.05 H vs .12-.16 do sheet, 8/8 patas) -> **PASS** |
| hfoo | n/a: sem capuz | PASS | **FAIL** (lança front .56, left .21) -> FAIL | n/a: biped |
| n02X | n/a: sem capuz | PASS | **FAIL** (clava .45) -> FAIL | n/a: biped |
| n01X | n/a | n/a: sem prop | n/a: sem prop | n/a: biped |

IoU / spill / bare por vista, controlo -> `l12-preflight` (as 6 unidades; só n00U muda, as outras reproduzem o controlo bit a bit com `|Δ| = 0.000`: n005 com o default não tem nada a reparar porque os reparos de capuz e props são opt-in):

| un. | vista | IoU | spill | bare |
|---|---|---|---|---|
| n00U | front | .878 -> .902 | .066 -> .047 melhora | .064 -> .056 |
| n00U | left | .818 -> .784 (dentro de 2σ=.047) | .134 -> .152 | .065 -> .088 |
| n00U | back | .876 -> .887 | .072 -> .061 | .060 -> .059 |
| n00U | top † | .734 -> .762 | .217 -> .160 melhora | .079 -> .108 |
| n00U | bottom † | .709 -> .785 melhora | .238 -> .185 melhora | .090 -> .044 melhora |
| n00U | rts | .653 -> .682 melhora | .272 -> .226 melhora | .136 -> .148 piora |

Opt-in `all` (n005; vistas que passam 2σ/.005): hood + props: front .920 -> .907, back .933 -> .922 (pioram), top .797 -> .803, bottom .820 -> .831, rts .878 -> .899 (melhoram); spill bottom .060 -> .055, rts .073 -> .059. Só props (run `l12-preflight-props`): front .920 -> .914, left .946 -> .941, back .933 -> .926, rts .878 -> .885. Só capuz (run intermediário, apagado): front -.011, back -.007, top -.019, spill top .116 -> .139.

- **Variantes medidas e descartadas.** (1) Joelho de n00U pela semelhança da corda do spec (pé do spec mantido): back .876 -> .853 (pior que 2σ), por isso o reparo usa joelho e pé do sheet; (2) quadruped: `leg_joints` com dobra de 25 graus (frente para a frente, trás para trás), invertida, e 15 graus: n017 left spill .054 -> .09-.10 nas três, top .050 -> .08-.09; o sheet do lobo desenha colunas retas, a dobra só acrescenta spill: **quadruped fica n/a**.
- **Aceite.** Specs v13 rejeitados: n005 **sim** (`hood_recess`), n00U **sim** (`leg_joints`), n017 **não**: as máscaras de prop do n017 são vazias (`prop_masks` descarta corda e arnês por estarem dentro das caixas do corpo) e as pernas não se medem; a caixa `left` da corda nem contém o eixo (y da corda .04 H, caixa .08-.38 H), mas uma regra por caixa seria ruído. Reparo sem LLM faz as regras passarem: n00U `leg_joints` sim; n005 `hood_recess` sim (com `all`), `prop_coverage` **não** (.23 -> .32; o vaporiser da caixa do sheet é metade do comprimento do spec e a máscara é só o que sobra fora das caixas do corpo); hfoo/n02X `prop_coverage` sem reparo (a lança de hfoo tem máscara não elongada; a clava de n02X está em .45). Nenhuma vista coerente cai > 2σ: **sim** no default (n00U left -.034 < .047); no `all` n005 front/back caem .013/.011 (> .005): por isso os reparos de capuz e props são opt-in.
- **Decisão.** Regras: duras (default). Reparo: `leg_joints` default (n00U: top/bottom spill -.057/-.053, bottom IoU +.076); capuz e props atrás de `--dsl-repair all`. Efeito colateral a saber: `prop_coverage` dura reprova hoje n005, hfoo e n02X no preflight (estágio 1 já reprovava as 6 pela silhueta no controlo; o veredito não muda).
- **Aberto.** (a) O capuz é um `lathe` fechado: a cara recuada fica dentro do sólido e o decal some; precisa de abertura real do capuz no build (território do L12-9, `build_unit`) e só então `hood_recess` vale a pena como default; (b) `prop_coverage` precisa da máscara completa do prop (`prop_masks` perde o que cai nas caixas do corpo: n017, hfoo left); (c) pés das patas do spec ainda vêm do autor (aqui vêm do sheet por regra, não por triangulação); (d) 1 repetição por variante.
- **Testes.** `tests/tools/blender/test_dsl_rules.py` (13: capuz sem cara -> FAIL + reparo passa, cara na boca e capuz raso, biped sem capuz n/a; pata de 1 peça -> 2 peças, dobra mínima, biped n/a; lança a 30 graus -> `prop_axis` FAIL + reparo passa, sem prop n/a; specs reais v13-r1: n005 e n00U rejeitados e reparados, n017 n/a de pernas), `test_flag_liveness` (+`dsl_repair`).

### 30.L12-7 Piso de ruído: determinismo medido, σ por vista, guardas por 2σ (2026-10-29)

- **Por que.** Os aceites eram constantes (`loop_stage.DROP/GAIN`, `author_guard.AUTHOR_DROP` = .01) sobre um ruído suposto de .013-.016 por vista (L11-2; L12-2 e L12-4 "viram hfoo variar até .016 com `--deterministic`"). Sem σ publicado, um guard de .01 pode ser sorteio ou pode ser folgado demais.
- **Determinismo (a parte mais valiosa): `--deterministic` já é determinístico, bit a bit.** hfoo 2× pelo caminho exato (`spec_pipeline --spec v13-r1 --tilts … --deterministic`, `SOFT_SIL_THREADS=4`, as duas ao mesmo tempo e com outro Blender na máquina): `clay.glb`, `clay-raw.glb` e `clay-prefit.glb` com o mesmo md5, |Δ IoU| = 0.000 nas 6 vistas; idem n00U (|Δ| = 0.000, mesmo md5). Ambas também idênticas ao `l12-stage2` (build de horas antes). O ".016 do hfoo" do L12-2/L12-4 era comparação entre **versões de código** (`l12-cams` -> `l12-spill-w1`: o peso de spill e o `contact` mudaram o fit), não ruído; o texto do L12-4 ("ruído do fit entre rodadas") estava errado.
  Fontes de não-determinismo achadas no caminho e o que foi feito:

  | fonte | onde | efeito | ação |
  |---|---|---|---|
  | relógio do `fit-verts` (30 s) | `optimize_verts.PIPELINE_SECONDS` | até .013 por vista (L11-2); em n00U ainda σ .024 em `left` sem `--deterministic` | já resolvido em L11-2: `--deterministic` = 8 iterações/estágio, deadline 1e9. Sem a flag continua relógio (é o caminho default) |
  | relógio do `fit` (Powell, 150 s) | `fit_spec.MAX_SECONDS`, `fit_grad.descend` | idem | `--deterministic` passa `seconds=1e9` (já era) |
  | `time.time()/(deadline-t0)` em `run_progress` | `optimize_verts.run_progress` | com deadline 1e9 a fração de tempo vale ~1e-9 e não muda o resultado (md5 igual) | nada; documentado |
  | nº de threads do torch | `soft_sil.THREADS` (`SOFT_SIL_THREADS`, default 4) | a redução paralela muda a soma em ponto flutuante: hfoo com `SOFT_SIL_THREADS=2` ≠ com 4, |Δ| até .004 (bottom), md5 diferente | o default é fixo em 4 (independe dos núcleos); **comparações exigem a mesma `SOFT_SIL_THREADS`**. Não forcei: o limite é da máquina. Run `hfoo/l12-noise-thr2` |
  | `retopo.CVT_SECONDS` (2 s) | `retopo.cvt` (`--sdf-retopo cvt`, opt-in) | o nº de tentativas de semente depende do relógio | não é o caminho default (qem); ponytail: passar a contagem fixa quando cvt virar default |
  | `np.random` | `retopo.cvt` (`default_rng(seed + k)`), `mesh_lint` (`default_rng(0)`), `silhouette` (seed), `compare_runs` (seed) | nenhum: todos com seed | nada |

- **σ publicado.** `noise.py` (novo, 40 linhas, puro): `sigmas`, `table`, `threshold(view, noise, default, unit)` = `max(2σ, .005)` com tabela, o `default` antigo sem tabela. `sdf_batch.py --repeat N --spec-run v13-r1` reconstrói cada unidade N vezes em `l12-noise-r1..rN` (shape-only, **sem** `--deterministic`: o ruído do caminho default), imprime a tabela σ por vista/unidade e grava `noise.json` ao lado do `--json` (`--noise-out`): `{unit: {view: σ}, "global": {view: mediana dos σ das unidades}}`. Bateria das 6 × 3, `artifacts/model-sheets/runs/draft/noise-l12.json` (+ `noise-l12-batch.json`):

  | unidade | front | left | back | top | bottom | rts | σ_max |
  |---|---|---|---|---|---|---|---|
  | n005 | .000 | .000 | .000 | .000 | .000 | .000 | .000 |
  | n00U | .009 | .024 | .006 | .018 | .003 | .002 | .024 |
  | hfoo | .000 | .000 | .000 | .000 | .002 | .002 | .002 |
  | n017 | .003 | .001 | .001 | .000 | .003 | .001 | .003 |
  | n02X | .002 | .001 | .007 | .004 | .004 | .006 | .007 |
  | n01X | .002 | .004 | .002 | .003 | .003 | .001 | .004 |
  | global (mediana) | .002 | .001 | .002 | .002 | .003 | .001 | .003 |

  Leitura: o ruído do caminho default é **menor** que o .01 suposto em 5 de 6 unidades (σ ≤ .007; 2σ ≤ .015); a exceção é n00U (aranha, o fit-verts mais lento: 280 s), σ até .024 em `left` (2σ = .047). O `global` (mediana) subestima n00U: **use o σ da unidade** (as guardas já usam `unit` e caem no `global` só se a unidade não tem σ). Com a tabela, o piso .005 vale em 5 das 6 unidades (guard mais estrito que .01); n00U fica folgado (.012-.047).
- **Guardas por 2σ.** `loop_stage.loop_accept(before, after, gates, noise=None, unit=None)`, `author_guard.drops(mass, author, drop, noise=None, unit=None)` e as três chamadas em `spec_pipeline` (`guard_stage` ×2, `guard_fit`; `loop_hooks`) leem o limiar por vista de `noise.threshold`. `spec_pipeline --noise noise.json` propaga (`noise_kw(args)`). Sem `--noise` nada muda (constantes antigas); nenhum default numérico mudou. `GAIN` (ganho da média, .005) ficou: ele é um ganho, não uma queda; ver Aberto.
- **`compare_runs.py --stability a b --noise noise.json`** marca cada Δ por vista `> 2σ` ou `ruído`.
- **Linhas tocadas em arquivos do L12-5** (só `spec_pipeline.py`, 15 linhas +/-, todas aditivas exceto 4 chamadas que ganham `**noise_kw(args)`): `import noise as NZ`; helper `noise_kw` (4 linhas); `--noise` no parser (3 linhas); `**noise_kw(args)` nas 3 chamadas de `author_guard.drops` e em `loop_hooks`. Nada em `views.py`, `fit_spec.py`, `optimize_verts.py`, `deform_to_sheet.py`, `silhouette.py`.
- **Aceite.** σ publicado 6×6: **sim**. `--deterministic` Δ = 0 em hfoo (e n00U): **sim, já era** (bit a bit; a causa do ".016" documentada acima). Guardas leem 2σ: **sim** (opt-in via `--noise`, sem arquivo = constante antiga).
- **Decisão: opt-in** (`--noise`): não mudei defaults numéricos. Quando o L12-5 mudar as vistas/pesos, refazer `noise-l12.json` (σ depende do caminho).
- **Aberto.** (a) `GAIN` do laço e os aceites "nenhuma vista cai > .01" dos itens da Leva 12 seguem constantes; (b) σ medido só no estágio 1 (shape-only) e sobre 3 amostras (σ amostral de n=3 é ele mesmo ruidoso: ±50 %); (c) n00U: investigar por que o fit-verts por relógio varia .024 só nela (carga? mais passos por segundo no spider?) ou aceitar 8 iterações fixas como default do caminho de aceite; (d) `SOFT_SIL_THREADS` não é registrado no `clay.verts.json`.
- **Testes.** `test_noise.py` (9: limiar com/sem arquivo, marca ruído/>2σ, `loop_accept` e `drops` por 2σ, σ e tabela, `sdf_batch --repeat 3` com builder mockado, nomes dos runs), `test_flag_liveness.py` (+`noise`). Runs: `runs/draft/<id>/l12-noise-r1..r3`, `hfoo|n00U/l12-noise-det{A,B}`, `hfoo/l12-noise-thr2`.

### 30.L12-9 Look low-poly: planaridade, creases do sheet-hard, tinta nas arestas (2026-10-29)

- **Por que.** "Estamos melhorando, mas está longe de um low poly legal." No v14 (n02X) o wire é sopa de triângulos (MC + QEM), não há crease (o smin suaviza tudo) e a textura não tem linha de tinta. Faltava até a métrica: nada media "look".
- **Métricas (`look.py`, numpy puro, sem Blender; `look.py metrics <run> --id <u>` mede qualquer `clay.glb`).** Na câmara do gate (`D.frame`, a mesma de `align_features`), vistas front/left/back:
  `crease_chamfer` = (precisão, recall) a 4 px entre as arestas duras do modelo (diedro ≥ 30°, as duas faces vistas) e a tinta interior do sheet-hard (`AF.hard_edges`, `silhouette.edges`); `planarity` = fração da área em patches planos (≥ 4 faces conectadas com normal a ≤ 2° da semente; cubo = 1.0, esfera UV < .1, testes); `wire_entropy` = entropia (0..1) da direção das arestas medida no plano da face (grade < sopa aleatória, teste) + arestas por 1000 tris. Impressas na linha `look:` do log, na linha `| look |` do `review.md` (Stage 1) e na coluna `look` do `sdf_batch`; `<run>/clay.look.json` (e `stage2/texture/model.look.json`) guarda antes/depois. **Medidas sempre ligadas** (flags off só medem). Desvio do brief: `wire_entropy` é entropia do histograma, não o desvio-padrão dos ângulos (o desvio de uma grade 0/60/120° já é alto).
- **Snap planar (`--look-snap on`).** `regions`: k-means das normais (k = 8, centróides a < 8° juntos), componentes conexos, e cada região que não é plana a `SNAP_TOL` = .01 H (ou tem normais a > 25° do plano) é partida em duas (2-means das normais, ou ao longo do eixo maior); regiões de ≥ 4 faces fixam um plano (PCA). `snap_regions`: 3 rodadas de refit + cada vértice vai à interseção dos planos das suas regiões (QEF com puxão 1e-3 para onde estava; 1 plano = projeção, 2 = linha, 3 = ponto), deslocamento ≤ 1.5 × tol. `guarded`: as regiões entram uma a uma (movimento mais barato primeiro) e ficam se o snap de tudo que já ficou passa na guarda (nenhuma face virada, slivers ≤ +.02, nenhuma vista perde > .003 de IoU nem ganha > .003 de spill ou bare; D.measure em 6 vistas). `.005` perdeu .006-.009 em 3 vistas (o raster do gate lê até .004 diferente do `D.measure`), por isso .003. Gancho: `look.apply` depois de `optimize_verts.apply` em `stage_shape` e em `colour_stage.build_textured` (o corpo do stage 2 é reconstruído). Não dissolve arestas coplanares (editar o GLB no lugar não muda a contagem de índices): os triângulos ficam, então `wire_entropy` e tris não mudam.
- **Creases (`--look-creases on`).** `mark_sharp`: aresta com as duas pontas e o meio a ≤ 3 px da tinta, direção ao longo dela (|cos| com o gradiente da tinta suavizada ≤ .42), diedro ≥ 8°, as duas faces vistas; vira fronteira de região (o snap não a atravessa). Sem a flag o snap não conhece a tinta.
- **Tinta (`--look-ink on`, só stage 2 cel compacto).** `bake_ink`: as arestas marcadas ao longo das linhas do sheet-hard recebem a coluna de tinta da célula de tom (o atlas já tem `surfaces.INK` = .55 na primeira/última coluna e a face usa a célula inteira): o `u` dos dois vértices da aresta vai ao menor `u` do triângulo, o do terceiro ao maior. Só faces de célula de tom (span de `u` = `TONE_W − 2·INK_EDGE_PX` texels, o que deixa de fora as de decal) cujos 3 vértices não são de outro triângulo; o `v` (rampa) e as zonas de cor não mudam. Sem UV (clay do stage 1) é no-op.
- **Medida (bateria das 6, sem LLM, `--deterministic --tilts` do v13-r1; controle = `l12-stage2` do worktree v2-hard; depois = `l12-look` = `--look-snap on --look-creases on`; `l12-look-ink` = + `--look-ink on`: o stage 1 sai idêntico ao `l12-look`, bit a bit nas métricas).** `*` = queda/alta > max(2σ, .005) de `noise-l12.json`.

look (controle -> `l12-look`)
| un. | planarity | wire_entropy | tris | crease P/R front | left | back | regiões snap / marcadas |
|---|---|---|---|---|---|---|---|
| n005 | .04 -> .40 | .97 -> .97 | 700 | .59/.46 -> .61/.46 | .69/.56 -> .70/.57 | .63/.51 -> .64/.49 | 41/48, 49 |
| n00U | .04 -> .25 | .99 -> .98 | 700 | .59/.36 -> .62/.41 | .53/.35 -> .55/.36 | .57/.49 -> .55/.52 | 37/37, 35 |
| hfoo | .07 -> .25 | .98 -> .98 | 700 | .66/.25 -> .62/.25 | .61/.55 -> .59/.53 | .50/.39 -> .48/.36 | 34/47, 35 |
| n017 | .04 -> .32 | .98 -> .98 | 700 | .44/.28 -> .45/.29 | .47/.31 -> .49/.32 | .40/.61 -> .42/.69 | 37/41, 31 |
| n02X | .09 -> .43 | .99 -> .99 | 700 | .65/.39 -> .62/.37 | .57/.48 -> .55/.46 | .56/.27 -> .55/.28 | 41/43, 46 |
| n01X | .02 -> .38 | .99 -> .99 | 700 | .71/.47 -> .71/.43 | .76/.78 -> .77/.76 | .76/.52 -> .79/.52 | 46/62, 77 |

IoU do gate (controle -> depois)
| un. | front | left | back | top | bottom | rts |
|---|---|---|---|---|---|---|
| n005 | .920 -> .923 | .946 -> .945 | .933 -> .927* | .797 -> .795 | .820 -> .816 | .878 -> .876 |
| n00U | .878 -> .878 | .818 -> .817 | .876 -> .876 | .734 -> .733 | .709 -> .709 | .653 -> .653 |
| hfoo | .867 -> .864 | .418 -> .417 | .874 -> .871 | .818 -> .816 | .843 -> .842 | .730 -> .732 |
| n017 | .908 -> .906 | .831 -> .831 | .849 -> .848 | .870 -> .869 | .861 -> .860 | .710 -> .710 |
| n02X | .900 -> .898 | .839 -> .839 | .905 -> .906 | .780 -> .778 | .762 -> .764 | .764 -> .762 |
| n01X | .841 -> .843 | .883 -> .883 | .845 -> .846 | .905 -> .903 | .875 -> .873 | .838 -> .838 |

spill do gate (controle -> depois)
| un. | front | left | back | top | bottom | rts |
|---|---|---|---|---|---|---|
| n005 | .053 -> .053 | .038 -> .040 | .051 -> .056 | .116 -> .117 | .060 -> .063 | .073 -> .076 |
| n00U | .066 -> .066 | .134 -> .134 | .072 -> .072 | .217 -> .219 | .238 -> .237 | .272 -> .272 |
| hfoo | .061 -> .064 | .387 -> .388 | .061 -> .064 | .105 -> .106 | .139 -> .136 | .200 -> .196 |
| n017 | .070 -> .070 | .054 -> .055 | .119 -> .119 | .050 -> .049 | .060 -> .061 | .218 -> .223 |
| n02X | .067 -> .069 | .096 -> .095 | .061 -> .062 | .171 -> .175 | .123 -> .124 | .143 -> .142 |
| n01X | .111 -> .115 | .080 -> .080 | .111 -> .115 | .040 -> .040 | .104 -> .104 | .124 -> .125 |

O bare (uncovered) tem 3 células fora de max(2σ, .005): hfoo bottom .024 -> .030* e n017 rts .115 -> .109 e n01X front/back .060 -> .054 / .056 -> .050 (as três últimas melhoram). Tinta (`l12-look-ink`, `stage2/texture/model.look.json`): faces com tinta / arestas marcadas n005 41/52, n00U 58/39, hfoo 44/33, n017 44/34, n02X 51/38, n01X 93/72 (um triângulo pode ter 2 arestas marcadas e conta uma; arestas marcadas no stage 2 diferem das do clay porque o corpo é reconstruído). Imagens antes/depois (wire front/back, modelo front/back/rts; controle em cima, `l12-look-ink` embaixo): `artifacts/model-sheets/history/2026-10-29-l12-look/<id>.png`.
- **Tentativa que não entrou: "ridge" nas creases.** Empurrar os vértices das arestas marcadas a `h` H ao longo da normal (ou em direção à câmara) para fazer o diedro passar de 30°: em n02X, `h` = .01 H sobe o recall de back .27 -> .36 mas baixa o de front .39 -> .35 e custa −.007…−.012 de IoU e +.011…+.016 de spill; `h` ≥ .02 H custa > −.017 de IoU. Sem o sinal de relevo (L12-8, z-pass) a direção (crista ou vale) é chute. Ficou de fora.
- **Aceite (roadmap).** `crease_chamfer` recall ≥ +.15 em ≥ 4/6: **não** (melhor célula: n017 back +.08, n00U front +.05; as outras ±.03: o snap planar não cria diedro ≥ 30° onde o corpo é liso, e as regiões separadas pelas linhas continuam com diedro < 30°). Planaridade sobe: **sim, 6/6** (.02–.09 -> .25–.43). Nenhuma vista cai > 2σ: **quase** (1 de 36 células de IoU, n005 back −.006; 1 de 36 de bare, hfoo bottom +.006; as demais dentro, spill sem marca). Tris dentro do orçamento: **sim** (700 -> 700). Juiz de forma ≥ 3/5: fica para L12-10 (precisa do VLM).
- **Decisão: opt-in** (`--look-snap/--look-creases/--look-ink`, default `off`; as métricas ficam sempre ligadas). O aceite de crease recall falha, então nenhum default muda.
- **Aberto.** (a) `wire_entropy` não se mexe: a sopa de triângulos fica (a topologia não muda); dissolver as arestas coplanares / re-triangular as regiões pede mexer no `build_unit` (decimação planar depois do QEM) ou escrever o GLB com índices novos; (b) recall de crease depende de relevo real (L12-8); (c) o raster do gate difere do `D.measure` em até .004: uma guarda com o IoU do Blender fecha a célula n005 back; (d) `crease_chamfer` conta a tinta de sombreado do sheet-hard como linha (o recall tem teto baixo, .27–.78 já no controle); (e) visibilidade de aresta por faces voltadas à câmara, sem z-buffer (aresta atrás de outra parte conta); (f) com `--look-ink` o stage 2 refaz as marcas no corpo reconstruído (consistente, não idêntico ao clay).
- **Linhas tocadas em `spec_pipeline.py` (território do L12-6 evitado): 10.** `import look`; 3 linhas depois de `optimize_verts.apply` (`look.apply` + `print(look.line(...))`); 5 linhas das flags `--look-snap/--look-creases/--look-ink` (laço sobre os 3 nomes); `{look.row(shape['glb'])}` no `stage1_section`. Fora disso: `colour_stage.py` (+2: import, `look.apply` depois de `optimize_verts.apply`), `sdf_batch.py` (coluna `look`), `look.py` novo.
- **Testes.** `test_look.py` (11: chamfer 0 px = 1.0 / 8 px = 0, planaridade cubo 1.0 / esfera < .1, entropia grade < aleatória, cubo com ruído -> 6 regiões e 6 planos exatos, linha marcada como borda de região, guarda aceita/recusa, `along_ink`, `ink_faces` e decal intocado, `bake_ink` sem UV, célula do batch), `test_flag_liveness.py` (+3 flags vivas). Suite completa OK. Runs: `runs/draft/<id>/l12-look` (final), `l12-look-ink`, `l12-look-g005` (guarda .005), `l12-look-ink-invalid` (crash em clay sem UV, corrigido), `l12-look-ink-partial` (interrompido para reinício).

### 30.L12-8 Profundidade a partir da arte: régua `z_err`, `relief_agreement`, z da peça pela triangulação (2026-10-29)

- **Pergunta do usuário.** "Como descobrir profundidades na arte (ex. o rosto do encapuzado n005) para usar no modelo?" O modelo tem a silhueta meio certa e o relevo errado (n01X top IoU .893 com luma L1 .146) e não havia régua de profundidade: `--fit-parts/--depth` eram no-op (7 de 8 `parts.json` com `box3d` null) e o L5-4b calibrou o Depth Anything com caixas a olho.
- **Régua `z_err` (`depth_rule.py`, numpy puro; `depth_rule.py measure <run> --id <u>` mede qualquer clay; sai em `clay.depth.json`, na linha `depth:` do log, na linha `| depth |` do `review.md` e na coluna `depth` do `sdf_batch`).** Marcos triangulados **front × left** (painéis desenhados retos: a triangulação é exata): as juntas que os dois painéis mostram (sem o .R espelhado), o centro das caixas de cabeça / torso / pelve / prop que os dois mostram e a **frente** da caixa do rosto, do queixo e do focinho (marco de superfície: o centro de uma placa sobre um capuz grosso não é o centro de nenhum sólido; a primeira versão dava .11 H de erro de artefato na máscara do n005). 11–20 marcos por unidade. `z_err` = média |z do clay − z triangulado| / H; o z do clay é o centro do sólido que a reta (x, y) cruza mais perto do z triangulado (a primeira superfície, nos marcos de superfície). Validação na 3.ª vista, o painel de topo na câmara pinada do gate: o marco é descartado e contado se os dois painéis discordam da altura em mais de `RESID_MAX` = .04 H ou se ele cai a mais disso da figura do topo; o relatório diz `n_used/n_total`. O sinal do z do sheet (`massing.side_of`, a linha do dedo do pé) erra em aranha e quadrúpede (n017 head_top z −.64, clay +.54): o erro é lido com o sinal que serve ao clay e o relatório diz qual (`z_sign`). As frações do VLM valem no recorte que ele leu (`meta.panel_crop`) e a escala vem da máscara de hoje: `frames_for` usa o recorte gravado.
- **Câmara pinada.** O painel de topo é desenhado inclinado: com a câmara de `views.camera` a linha de um ponto é v = y sin(tilt) − z cos(tilt). Lido como vista reta (tilt 0), um ponto a 2,5 m com tilt −30 cai 1,2 m fora do lugar; com o tilt pinado o z sai exato (teste sintético; top e bottom). `fit_top` ajusta o hull front × left (voxels de H/90) ao painel de topo por IoU: escala pela largura, deslocamento e as 4 maneiras de o painel estar desenhado (como está / espelhado / girado 180° / os dois). Achou girado em n005, n00U e hfoo, como está em n017 e n01X, girado e espelhado em n02X; IoU do ajuste .77 / .67 / .62 / .76 / .77 / .88 (n005 / n00U / hfoo / n017 / n02X / n01X; o hfoo tem tilt 0 e o topo incoerente).
- **Linha de base (antes de tocar em peça; clay do controle).** Dentro de .05 H em n005, hfoo e n01X; fora em n02X, n00U e n017 (tabela abaixo). O que a régua aponta: n005 queixo e frente da máscara .042 H (11 cm atrás do sheet), tornozelo .026; n02X queixo .223, respirador .169, pano do pavio .163; n00U fangs .138, centro da carapaça .102; n017 leg2.root .393 e cabeça .195 (pose e sinal do quadrúpede); hfoo só 6 de 14 marcos úteis (5 caem por incoerência dos painéis, 3 sem clay na reta: o braço do clay não está onde o sheet o põe). Controle: `l12-stage2` do worktree v2-hard, exceto n00U e n017, que têm `l12-depth-none` (o default deste HEAD; o `l12-stage2` do n00U é anterior ao reparo `leg_joints` default do L12-6: front .878 -> .902, bottom .709 -> .785 entre os dois, não é deste item).
- **`relief_agreement` (`depth_rule.relief`; check, não gate).** O z-pass do clay (z-buffer em numpy, câmara do gate de `D.make_views`, front/left/back; não precisou de Blender) -> degraus (pixels vizinhos a mais de `STEP_MIN` = .02 H em profundidade, longe do contorno) contra a tinta interior do sheet-hard (`silhouette.edges` via `AF.hard_edges`, a de `look.py`), precisão/recall a `SLACK` = 4 px do canvas. Precisão alta (.5–.9), recall baixo (.06–.38): quase toda linha de tinta (olhos, lentes, costuras, dobras do pano) não é degrau no clay, que é liso por dentro; o recall é o relevo que falta.
- **Triangulação por peça (`segment_sheet.py --reply <parts-reply.json> --run <run>`; sem VLM).** Re-triangula a resposta salva com o recorte que ela leu e, para a peça que um só painel mostra, tenta o intervalo que falta no hull front × left × topo menos as caixas das outras peças (`complete_box`; guardas: ≥ 50 % dos voxels da janela fora das outras peças e intervalo ≤ 0,6 × a maior medida conhecida). Cada `box3d` null ganha `z_why`; os `parts.json` antigos ficam em `refs/<id>/parts.json.pre-l12-8` (o corte dos painéis de hoje difere do gravado em 5 de 6 sheets; as juntas mexem ≤ .018 H, n00U e n017, o resto igual). **Resultado: 0 das 18 caixas null das 6 unidades foram preenchidas** (9 `inside-other-parts`, 9 `envelope`): dentro da janela de uma peça o hull inclui o corpo. Sem as guardas, a validação cruzada (esconder o left de uma peça que os dois painéis mostram e ler o z do topo) erra o centro em z em média .053 H (n005; .077 com tilt 0: a câmara pinada ajuda) / .075 (hfoo, tilt 0) / .246 (n00U) / .408 (n017) / .127 (n02X; .114 com tilt 0) / .013 (n01X): o hull valida um marco, não cria uma caixa. n00H e n010 (sem run com tilt de topo) ficam `no-top`. Patas do n00U pelo topo, lança do hfoo e abertura do capuz do n005 **não** saem daqui: pata e corpo dividem as mesmas colunas do topo (n00U leg3/4/5/7 `envelope`), a lança e o capuz já têm caixa front × left e o recesso não está em nenhum painel.
- **z do spec a partir das caixas (`--depth-source tri|none`, default `none`).** `depth_stage` depois do `dsl_stage`: a peça do spec cujo centro em z fica a mais de `DZ_MIN` = .05 H **fora** do intervalo z da `box3d` da peça semântica que ela é (`parts_fit.associate`; só caixas front × left: o z espelhado do .R erra em pose assimétrica, n02X segura o porrete atrás e o outro braço à frente e o primeiro teste, com z espelhado, piorou o front -.013; `chain` fica de fora, o `at` dela é ignorado) vai ao meio do intervalo (cap .25 H). O movimento fica se o proxy 2D não perde vista em mais de 2σ contra o spec como veio e nenhuma regra do preflight que valia quebra; escreve `depth-stage.json`. Movimentos propostos / mantidos: n00U 3 / 1 (`body frustum` −.119 m; os 2 do `leg8` recusados pelo proxy), n02X 1 / 0 (recusado), as outras 0 / 0.
- **Depth Anything recalibrado (`depth_map.landmark_calibration`; `--depth` agora usa a reta dos marcos, `MIN_R` = .7 e r > 0).** Pearson r entre a disparidade (mediana 5 × 5 no painel front) e o z triangulado dos marcos: n005 −.22 (n = 9), hfoo .17 (9), n00U −.79 (5), n017 −.98 (4), n02X −.22 (17), n01X .38 (10). Nenhuma unidade chega a .7 com o sinal certo (n00U e n017: |r| alto com o z do sheet invertido e n de 4–5). O alvo errado do L5-4b não era o problema: a rede não dá z confiável nesses sheets. `--depth` não move peça; opt-in como era.
- **Medida (bateria das 6, sem LLM, `--deterministic --tilts` do v13-r1, `--depth-source tri`; run `l12-depth`; controle acima).** Só o n00U muda (uma peça mexida); as outras 5 saem bit a bit iguais ao controle (IoU, spill, bare, z_err, relief).

IoU do gate (controle -> depois; `*` = mudança acima de 2σ de `noise-l12.json`)

| un. | front | left | back | top | bottom | rts |
|---|---|---|---|---|---|---|
| n005 | .920 -> .920 | .946 -> .946 | .933 -> .933 | .797 -> .797 | .820 -> .820 | .878 -> .878 |
| n00U | .902 -> .896 | .784 -> .803 | .887 -> .882 | .762 -> .765 | .785 -> .770 * | .682 -> .687 |
| hfoo | .867 -> .867 | .418 -> .418 | .874 -> .874 | .818 -> .818 | .843 -> .843 | .730 -> .730 |
| n017 | .908 -> .908 | .831 -> .831 | .849 -> .849 | .870 -> .870 | .861 -> .861 | .710 -> .710 |
| n02X | .900 -> .900 | .839 -> .839 | .905 -> .905 | .780 -> .780 | .762 -> .762 | .764 -> .764 |
| n01X | .841 -> .841 | .883 -> .883 | .845 -> .845 | .905 -> .905 | .875 -> .875 | .838 -> .838 |

spill do gate

| un. | front | left | back | top | bottom | rts |
|---|---|---|---|---|---|---|
| n005 | .053 -> .053 | .038 -> .038 | .051 -> .051 | .116 -> .116 | .060 -> .060 | .073 -> .073 |
| n00U | .047 -> .049 | .152 -> .139 | .061 -> .062 | .160 -> .145 | .185 -> .168 * | .226 -> .218 * |
| hfoo | .061 -> .061 | .387 -> .387 | .061 -> .061 | .105 -> .105 | .139 -> .139 | .200 -> .200 |
| n017 | .070 -> .070 | .054 -> .054 | .119 -> .119 | .050 -> .050 | .060 -> .060 | .218 -> .218 |
| n02X | .067 -> .067 | .096 -> .096 | .061 -> .061 | .171 -> .171 | .123 -> .123 | .143 -> .143 |
| n01X | .111 -> .111 | .080 -> .080 | .111 -> .111 | .040 -> .040 | .104 -> .104 | .124 -> .124 |

bare (uncovered) do gate

| un. | front | left | back | top | bottom | rts |
|---|---|---|---|---|---|---|
| n005 | .030 -> .030 | .017 -> .017 | .018 -> .018 | .110 -> .110 | .135 -> .135 | .056 -> .056 |
| n00U | .056 -> .060 | .088 -> .078 | .059 -> .064 | .108 -> .121 | .044 -> .088 * | .148 -> .151 |
| hfoo | .081 -> .081 | .432 -> .432 | .074 -> .074 | .095 -> .095 | .024 -> .024 | .107 -> .107 |
| n017 | .026 -> .026 | .128 -> .128 | .041 -> .041 | .088 -> .088 | .089 -> .089 | .115 -> .115 |
| n02X | .038 -> .038 | .079 -> .079 | .038 -> .038 | .070 -> .070 | .147 -> .147 | .124 -> .124 |
| n01X | .060 -> .060 | .043 -> .043 | .056 -> .056 | .059 -> .059 | .026 -> .026 | .049 -> .049 |

relief_agreement (precisão/recall, front / left / back) e caixas null

| un. | z_err antes (n_used/n_total) | z_err depois | relief P/R antes f/l/b | relief P/R depois f/l/b | box3d null antes -> depois |
|---|---|---|---|---|---|
| n005 | .019 (11/13) | .019 (11/13) | .53/.11 .77/.27 .69/.23 | .53/.11 .77/.27 .69/.23 | 3 -> 3 of 18 |
| n00U | .071 (7/11) | .070 (7/11) | .73/.35 .82/.22 .62/.29 | .80/.36 .72/.23 .62/.33 | 5 -> 5 of 13 |
| hfoo | .027 (6/14) | .027 (6/14) | .77/.20 .71/.36 .86/.25 | .77/.20 .71/.36 .86/.25 | 1 -> 1 of 15 |
| n017 | .165 (4/11) | .165 (4/11) | .72/.38 .54/.10 .49/.27 | .72/.38 .54/.10 .49/.27 | 6 -> 6 of 13 |
| n02X | .068 (19/20) | .068 (19/20) | .60/.13 .75/.24 .69/.25 | .60/.13 .75/.24 .69/.25 | 0 -> 0 of 21 |
| n01X | .018 (11/12) | .018 (11/12) | .74/.10 .87/.20 .79/.06 | .74/.10 .87/.20 .79/.06 | 3 -> 3 of 20 |

- **Rosto do encapuzado (n005), em 5 linhas.** (1) A régua mede a frente do rosto no clay a .042 H do que as caixas front × left dizem, nos dois marcos, em sentidos opostos: máscara .50 no clay contra .61 no sheet (11 cm atrás) e queixo .56 contra .44 (11 cm à frente); o centro do capuz a .024 H. O clay tem a frente do rosto quase vertical, o sheet a inclina (focinho do respirador saliente em cima, queixo recuado): a profundidade **externa** do rosto está dentro de .05 H, o que falta é a inclinação. (2) O recesso (máscara atrás da borda do capuz) não está em painel nenhum: as caixas do VLM dão capuz e máscara com a mesma frente (z .612); front, left e topo só veem o contorno externo. (3) Com `hood_recess` à mão (`l12-preflight-all`, rosto de 0,08 m com a frente em z .467) o `z_err` fica em .018 e a máscara vai de .042 a .034 H, o `relief_agreement` front cai de .53/.11 a .42/.11: a régua mexe na direção certa, mas na resolução dela (~.01 H), e o modelo não ficou visivelmente mais certo (front .920 -> .907, L12-6). (4) O sinal do recesso no sheet é a tinta: o contorno fechado da abertura do capuz é um degrau, e o recall do relevo no front é .11 (89 % das linhas de tinta não têm degrau no clay). (5) Falta a magnitude: uma vista em que a borda do capuz apareça (3/4 com elevação, `sheet-turn`) ou o prior por família (recesso .08–.15 H, L12-6); a posição do degrau vem da tinta, a profundidade, de um prior ou de uma pergunta ao VLM por classe, uma vez, offline.
- **Aceite (roadmap): NÃO atendido.** `z_err` ≤ .05 H: 3 de 6 (n005, hfoo, n01X), n00U .070, n02X .068, n017 .165. n00U/hfoo/n005 melhoram top/bottom/rts: só o n00U se mexe e com sinal misto (spill bottom −.017 e rts −.008, acima de 2σ, mas bottom IoU −.015 e bare bottom +.044 também acima de 2σ; hfoo e n005 não têm peça fora do intervalo). Vista coerente caindo > 2σ: sim, n00U bottom. n01X ± σ: igual bit a bit. A régua não se mexeu com um modelo visivelmente melhor (a peça mexida do n00U move .02 H de IoU para um lado e para outro): pelo critério do experimento de 1 dia, **a régua serve para apontar (marcos acima), não para consertar**; o que falta é um z que não dependa das caixas do VLM.
- **Decisão: `--depth-source` fica `none` (opt-in `tri`); a régua e o `relief_agreement` ficam sempre ligados** (checks, ~4 s por clay, sem Blender). `parts.json` regenerado (o default não mexe: n00U com o `parts.json` antigo e com o novo dão silhueta idêntica).
- **Aberto.** (a) z de peça que o hull não separa do corpo (patas da aranha, lança, braço segurando o porrete): precisa de uma segmentação por cor/zona do topo ou do rts (a tinta e o `zone_labels` já existem) ou de um 4.º painel; (b) a calibração do Depth Anything com sinal e n maiores (as juntas do n00U/n017 vêm de poucos marcos: o VLM leu 6 de 16 e 8 de 15); (c) marcos de n017 e n00U: o sinal do z do sheet precisa de um decisor melhor que a linha do dedo do pé (`side_of`) para rig de quadrúpede/aranha; (d) `relief_agreement` com os degraus medidos em unidades de H por pixel em vez de salto fixo, e T-junções da tinta como ordem de oclusão (candidato 2 do peer review); (e) a validação do marco pelo topo é fraca para marcos dentro do corpo (qualquer ponto interno cai na figura): só pega marcos fora do hull.
- **Testes.** `test_depth_rule.py` (18: z exato com tilt pinado e erro grande com tilt 0, top e bottom; `fit_top` acha o painel girado e o resíduo separa marco dentro e fora da figura; z_err de clay deslocado .1 H = .1, marco incoerente descartado e contado, reta sem clay = miss, sinal do z trocado, frente do rosto; `zbuffer`, degraus só no contorno da placa, `agreement` 1 com degrau e tinta juntos e 0 a 8 px; `tri_shifts`; `complete_box`; célula do `sdf_batch`), `test_segment_sheet.py` (+2: parte de um painel ganha z do hull ou diz por que fica null), `test_depth_map.py` (+2: reta dos marcos, r < .7 ou negativo não move), `test_flag_liveness.py` (+`depth_source`). Suite completa: 744 testes OK (11 skipped). Ruff com complexidade ≤ 10 limpo nos arquivos tocados.
- **Arquivos.** `tools/blender/depth_rule.py` (novo), `segment_sheet.py` (`complete_boxes`, `--reply` com o recorte gravado, `--run`), `depth_map.py` (`landmark_calibration`, `MIN_R` .7), `fit_spec.py` (`--depth` passa a reta dos marcos), `spec_pipeline.py` (`depth_stage`, `--depth-source`, hook `depth_rule.apply` depois do `look.apply`, linha no `review.md`), `sdf_batch.py` (coluna `depth`), `refs/<id>/parts.json` (8 unidades; `*.pre-l12-8` = os antigos), testes. Runs: `runs/draft/<id>/l12-depth` (tri), `l12-depth-none` (n00U, n017: controle do HEAD), `l12-depth-none-oldparts` (n00U), `l12-depth-mirror` (n02X com z espelhado, front −.013), `l12-depth-v1` (n00U, mesma coisa antes de `depth-stage.json`) / `l12-depth-chain` (n017 com a `chain` mexida: sem efeito, o `at` é ignorado), `-invalid*` / `-partial` (baterias sobrepostas, descartadas).

### 30.L12-10a Matriz de ablação re-executada sobre o código da Leva 12 (2026-10-30)
- **O que mudou.** `tools/blender/ablation_matrix.py` (reescrito): 6 unidades (`n005 n00U hfoo n017 n02X n01X`, specs `v13-r1`, `--tilts` do
  v13-r1, `--no-repair --no-diagnose --deterministic --shape-only --body sdf`, rigs/race/name como em `v13.sh`), **43 variantes de forma** = todos os opt-ins
  vivos de `test_flag_liveness` (L8/L10/L11 + `CF_SPILL_W=3`, `--author-guard revert`, `--incoherent-weight 1.0` e `0`, `--dsl-repair all` (e `off` como controle),
  `--look-snap/-creases/-ink on`, `--depth-source tri`, `--depth`, `--noise noise-l12.json`, `--sdf-retopo cvt`, `--body join`, `--fit-fast`) e variável de ambiente por variante
  (`var(env=...)`). Teste `tests/tools/blender/test_ablation_matrix.py`: falha se uma flag viva (LIVE_PAIRS/LIVE_CUSTOM) não é coberta por uma variante nem tem razão em
  `NOT_A_VARIANT` (`loop` = precisa do LLM; `deterministic` = base; `parts` = entrada do fit-parts; `shape_only`/`colour_on_fail` = seletores de estágio; `fit_luma` = onda de cor).
  Colunas por variante, sobre as 6 unidades (e por unidade no csv): Δ spill médio (números do gate: corpo onde há prop), **vistas com spill <= .03**, Δ IoU, Δ bare, vistas que caem
  > 2σ (`noise-l12.json`, `noise.threshold`), Δ contact, Δ z_err, Δ planarity, Δ recall de crease, Δ tris, Δ segundos. Veredito: `default-candidate` = spill médio cai (> .002)
  e nenhuma vista cai > 2σ; `opt-in` = spill ou IoU melhora mas uma vista cai; `no`. `--legacy DIR` mede os runs `l11-mx-*` do mesmo jeito (tabela antes/depois).
  Runs: `runs/draft/<id>/l12-mx-<variante>/` (43 de forma + 3 combinações = 265 runs medidos, 11 células "não aplicável" por `units`/`needs`; 0 falhas de build). Obs.: `spec_pipeline` sai com código 1 quando um gate dá FAIL; o runner tratava isso como "não terminou" e, ao relançar com `--jobs 4`, refez ~50 runs (renomeados `-invalid<ts>`, nunca apagados): as 50 reconstruções têm `approved` bit a bit igual ao run original, prova extra de determinismo com a matriz inteira (corrigido: `batch.json` com `returncode` basta para pular).
- **Fase (a): cada variante sozinha, 6 unidades (resumo; por unidade em `analysis/2026-10-30-l12-matrix.{csv,md}`, copiado para `IA_gen_paper/ablation-matrix-2026-10-30-l12-matrix.*`).**

| variant | units | Δ spill | views spill ≤ .03 (base) | Δ IoU | Δ bare | views fall > 2σ | Δ contact | Δ z_err | Δ planarity | Δ crease R | Δ tris | Δ s | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| spill-w3 | 6 | -0.0181 | 2/36 (0) | -0.0191 | +0.0418 | 28 | -0.0026 | -0.0055 | +0.019 | -0.008 | +0 | +23 | opt-in (28 view(s) fall > 2σ) |
| author-guard | 6 | -0.0024 | 1/36 (0) | -0.0077 | +0.0095 | 10 | -0.0188 | -0.0091 | -0.010 | -0.005 | +0 | +278 | opt-in (10 view(s) fall > 2σ) |
| incoh-1 | 6 | +0.0010 | 0/36 (0) | +0.0008 | -0.0008 | 4 | -0.0011 | +0.0021 | +0.007 | +0.001 | -0 | +11 | opt-in (4 view(s) fall > 2σ) |
| incoh-0 | 6 | +0.0101 | 0/36 (0) | -0.0105 | +0.0028 | 13 | -0.0170 | -0.0066 | +0.003 | -0.015 | -0 | +38 | no |
| dsl-all | 6 | -0.0003 | 0/36 (0) | +0.0003 | -0.0001 | 2 | -0.0003 | -0.0001 | +0.002 | -0.005 | +0 | +14 | opt-in (2 view(s) fall > 2σ) |
| dsl-off | 6 | +0.0047 | 0/36 (0) | -0.0037 | +0.0000 | 3 | +0.0017 | +0.0034 | -0.004 | -0.009 | +0 | +22 | no |
| look-snap | 6 | +0.0014 | 0/36 (0) | -0.0011 | -0.0004 | 1 | -0.0083 | -0.0009 | +0.319 | -0.002 | +0 | +25 | no |
| look-creases | 6 | +0.0011 | 0/36 (0) | -0.0011 | +0.0001 | 1 | -0.0091 | -0.0009 | +0.307 | -0.003 | +0 | +22 | no |
| look-ink | 6 | +0.0000 | 0/36 (0) | +0.0000 | +0.0000 | 0 | +0.0000 | +0.0000 | +0.000 | +0.000 | +0 | +1 | no (no-op: nothing moved) |
| depth-tri | 6 | -0.0015 | 0/36 (0) | +0.0000 | +0.0018 | 1 | -0.0033 | -0.0001 | -0.007 | -0.004 | +0 | -6 | no |
| noise | 6 | +0.0000 | 0/36 (0) | +0.0000 | +0.0000 | 0 | +0.0000 | +0.0000 | +0.000 | +0.000 | +0 | -2 | no (no-op: nothing moved) |
| fit-grad | 6 | +0.0007 | 0/36 (0) | -0.0023 | +0.0031 | 7 | -0.0065 | -0.0083 | +0.003 | -0.003 | +0 | -50 | no |
| fit-stages | 6 | +0.0036 | 0/36 (0) | -0.0024 | -0.0000 | 6 | -0.0051 | -0.0008 | +0.006 | -0.007 | +0 | -0 | no |
| fit-edges | 6 | -0.0019 | 0/36 (0) | +0.0003 | +0.0016 | 6 | -0.0082 | +0.0004 | +0.009 | -0.002 | +0 | +71 | opt-in (6 view(s) fall > 2σ) |
| fit-fast | 6 | +0.0013 | 0/36 (0) | -0.0021 | +0.0020 | 6 | -0.0070 | +0.0052 | +0.000 | -0.013 | -0 | -85 | no |
| fit-parts | 6 | -0.0054 | 1/36 (0) | +0.0048 | +0.0010 | 6 | +0.0204 | +0.0005 | +0.006 | -0.005 | -0 | +60 | opt-in (6 view(s) fall > 2σ) |
| fit-depth | 6 | -0.0054 | 1/36 (0) | +0.0048 | +0.0010 | 6 | +0.0204 | +0.0005 | +0.006 | -0.005 | -0 | +70 | opt-in (6 view(s) fall > 2σ) |
| constraints | 4 | +0.0037 | 0/24 (0) | -0.0039 | +0.0013 | 6 | -0.0161 | +0.0091 | +0.014 | +0.019 | +0 | +3 | no |
| leg-spill | 2 | +0.0031 | 0/12 (0) | -0.0038 | +0.0020 | 3 | -0.0134 | -0.0236 | +0.024 | -0.037 | +0 | -32 | no |
| leg-grow | 1 | +0.0000 | 0/6 (0) | +0.0000 | +0.0000 | 0 | +0.0000 | +0.0000 | +0.000 | +0.000 | +0 | -23 | no (no-op: nothing moved) |
| body-union | 6 | +0.0017 | 0/36 (0) | -0.0056 | +0.0057 | 14 | -0.0113 | -0.0042 | -0.003 | +0.004 | -71 | -10 | no |
| body-join | 6 | +0.0296 | 0/36 (0) | -0.0507 | +0.0300 | 32 | -0.1124 | -0.0176 | – | – | -5 | -38 | no |
| k-class | 6 | -0.0026 | 0/36 (0) | +0.0046 | -0.0051 | 5 | -0.0025 | +0.0001 | +0.013 | +0.011 | +0 | -6 | opt-in (5 view(s) fall > 2σ) |
| k-hard | 6 | -0.0014 | 0/36 (0) | +0.0013 | +0.0006 | 9 | +0.0050 | -0.0039 | +0.009 | +0.000 | +0 | -3 | opt-in (9 view(s) fall > 2σ) |
| cvt | 6 | -0.0026 | 0/36 (0) | -0.0032 | +0.0077 | 12 | -0.0038 | +0.0133 | -0.018 | +0.018 | -6 | -9 | opt-in (12 view(s) fall > 2σ) |
| thin-keep | 6 | -0.0011 | 0/36 (0) | +0.0016 | -0.0005 | 0 | +0.0049 | -0.0005 | +0.000 | +0.002 | +0 | -7 | opt-in (spill does not fall) |
| thin-off | 6 | -0.0004 | 0/36 (0) | +0.0009 | -0.0005 | 1 | +0.0024 | -0.0002 | +0.002 | -0.000 | +0 | -7 | opt-in (1 view(s) fall > 2σ) |
| grid-128 | 6 | -0.0031 | 0/36 (0) | +0.0005 | +0.0033 | 10 | +0.0080 | +0.0016 | +0.012 | -0.003 | +0 | +0 | opt-in (10 view(s) fall > 2σ) |
| no-deform | 6 | +0.0076 | 0/36 (0) | -0.0109 | +0.0054 | 16 | -0.0388 | +0.0027 | +0.039 | +0.012 | +0 | -12 | no |
| no-verts | 6 | +0.0186 | 0/36 (0) | -0.0275 | +0.0125 | 31 | -0.0737 | +0.0014 | +0.041 | -0.004 | +0 | -28 | no |
| align | 6 | -0.0008 | 0/36 (0) | +0.0012 | -0.0014 | 3 | +0.0063 | +0.0009 | -0.002 | +0.006 | +0 | -4 | opt-in (3 view(s) fall > 2σ) |
| props-own | 6 | -0.0020 | 0/36 (0) | -0.0014 | +0.0025 | 8 | -0.0042 | +0.0005 | -0.001 | +0.013 | +0 | -7 | no |
| verts-fd | 6 | +0.0052 | 1/36 (0) | +0.0023 | -0.0098 | 12 | -0.0130 | +0.0000 | -0.015 | +0.021 | +0 | +12 | opt-in (12 view(s) fall > 2σ) |
| verts-tau | 6 | -0.0022 | 1/36 (0) | -0.0026 | +0.0053 | 9 | -0.0046 | -0.0006 | +0.001 | +0.002 | +0 | +7 | opt-in (9 view(s) fall > 2σ) |
| verts-asym | 6 | -0.0167 | 2/36 (0) | -0.0155 | +0.0351 | 26 | -0.0055 | -0.0003 | -0.003 | +0.008 | +0 | +5 | opt-in (26 view(s) fall > 2σ) |
| verts-dihedral | 6 | +0.0025 | 0/36 (0) | -0.0057 | +0.0044 | 16 | -0.0165 | +0.0004 | -0.013 | -0.038 | +0 | -6 | no |
| verts-gamma | 6 | -0.0003 | 0/36 (0) | +0.0003 | -0.0010 | 6 | -0.0034 | +0.0011 | -0.008 | +0.004 | +0 | -6 | opt-in (6 view(s) fall > 2σ) |
| verts-uniform | 6 | -0.0008 | 0/36 (0) | -0.0017 | +0.0024 | 7 | -0.0092 | -0.0003 | -0.012 | +0.001 | +0 | -8 | no |
| iters-15 | 6 | -0.0044 | 0/36 (0) | +0.0091 | -0.0061 | 0 | +0.0209 | -0.0001 | -0.007 | +0.007 | +0 | +14 | default-candidate |
| iters-15+fit-parts | 6 | -0.0084 | 1/36 (0) | +0.0093 | -0.0014 | 7 | +0.0332 | +0.0014 | -0.010 | -0.013 | -0 | +92 | opt-in (7 view(s) fall > 2σ) |
| iters-15+spill-w3 | 6 | -0.0230 | 2/36 (0) | -0.0125 | +0.0391 | 23 | +0.0131 | -0.0047 | +0.022 | -0.010 | +0 | +50 | opt-in (23 view(s) fall > 2σ) |
| iters-15+spill-w3+fit-parts | 6 | -0.0191 | 1/36 (0) | -0.0140 | +0.0368 | 23 | +0.0074 | +0.0002 | +0.019 | -0.015 | +0 | +65 | opt-in (23 view(s) fall > 2σ) |
| verts-yager | 6 | +0.0006 | 0/36 (0) | -0.0019 | +0.0012 | 8 | -0.0037 | -0.0002 | -0.006 | +0.003 | +0 | -5 | no |
| flip-side | 6 | +0.0039 | 0/36 (0) | -0.0058 | +0.0068 | 6 | -0.0078 | +0.0002 | -0.003 | -0.005 | -0 | -2 | no |
| frame-body | 6 | +0.0180 | 0/36 (0) | -0.0244 | +0.0110 | 9 | -0.0501 | +0.0002 | -0.003 | -0.005 | -0 | -6 | no |

- **Leitura.** (1) Spill: nenhuma variante deixa o spill <= .03 em mais de 2 de 36 vistas (base: 0/36); o spill médio do base é ~.10, então o teto do aceite L12-10 (3 %) segue longe.
  (2) O único `default-candidate` é `iters-15` (15 iterações do fit-verts por estágio em vez de 8): Δ spill -.0044, Δ IoU +.0091, 0 vistas caem > 2σ, contact +.021, +14 s por unidade;
  não vira default aqui (o brief proíbe mudar defaults), fica como candidato a ser provado na bateria v15/v16. (3) O alavanca de spill é o custo assimétrico (`spill-w3`: Δ spill -.0181,
  `verts-asym` -.0167), mas as duas pagam em IoU (-.019/-.016) e em bare (+.042/+.035) e 26-28 vistas caem > 2σ: troca spill por bare, não é ganho (confirma L12-2). (4) `fit-parts` ==
  `fit-depth` (números idênticos: causa não investigada: `--depth` e `--fit-parts` chegam aos mesmos termos de parts.json nestas unidades): Δ spill -.0054, Δ IoU +.0048, contact +.020, mas 6 vistas caem > 2σ.
  (5) `author-guard` (massing de `v13-r1/massing` contra o spec do autor) custa +278 s (3 builds) e piora (IoU -.008, 10 vistas). (6) `look-snap`/`look-creases`:
  planarity +.32/+.31 (a métrica de k-means de normais, ver L12-9), IoU -.001, contact -.008: neutro em forma. `look-ink` e `noise` são no-op por construção na matriz (tinta só entra no atlas
  do stage 2; 2σ só é lido por laço/guarda). `incoh-1` ~ base; `incoh-0` piora (IoU -.011, 13 vistas). `dsl-all` ~ base (Δ IoU +.0003); `dsl-off` pior (-.004). `depth-tri`: z_err -.0001 (a régua L12-8 não se mexe),
  IoU 0. `cvt`: Δ spill -.0026 mas IoU -.003, 12 vistas caem. `body-join` (sem casca única) é o pior (-.051, contact -.11). Controles: `no-verts` -.0275, `no-deform` -.0109, `frame-body` -.0244, `body-union` -.0056 (default confirmado).
- **Antes (L11-7, código pré-L12) vs depois (L12), mesmas variantes, mesmo critério novo aplicado aos runs `l11-mx-*` (5 unidades)** — só as que mudaram de classe de veredito:

| variant | verdict before (L11-7) | verdict after (L12) | Δ spill before → after | Δ IoU before → after | views fall > 2σ before → after |
|---|---|---|---|---|---|
| fit-parts | no | opt-in (6 view(s) fall > 2σ) | +0.0008 → -0.0054 | -0.0042 → +0.0048 | 6 → 6 |
| fit-depth | no | opt-in (6 view(s) fall > 2σ) | +0.0020 → -0.0054 | -0.0048 → +0.0048 | 6 → 6 |
| k-class | no | opt-in (5 view(s) fall > 2σ) | +0.0005 → -0.0026 | -0.0053 → +0.0046 | 6 → 5 |
| k-hard | no | opt-in (9 view(s) fall > 2σ) | -0.0020 → -0.0014 | -0.0035 → +0.0013 | 10 → 9 |
| thin-keep | no (no-op: nothing moved) | opt-in (spill does not fall) | +0.0000 → -0.0011 | +0.0000 → +0.0016 | 0 → 0 |
| thin-off | no (no-op: nothing moved) | opt-in (1 view(s) fall > 2σ) | +0.0000 → -0.0004 | +0.0000 → +0.0009 | 0 → 1 |
| grid-128 | no | opt-in (10 view(s) fall > 2σ) | +0.0046 → -0.0031 | -0.0056 → +0.0005 | 9 → 10 |
| align | no | opt-in (3 view(s) fall > 2σ) | +0.0002 → -0.0008 | -0.0017 → +0.0012 | 4 → 3 |
| verts-fd | no | opt-in (12 view(s) fall > 2σ) | +0.0057 → +0.0052 | -0.0003 → +0.0023 | 8 → 12 |

  Por quê: as 9 variantes passam de `no` a `opt-in` porque o spill passa a cair e o IoU deixa de cair em média; a causa é atribuída, não isolada (não há run com só uma das mudanças L12): câmara do otimizador alinhada ao gate (L12-1), gates e custo novos (L12-2), flags que passam a chegar ao build (L12-4). O `base` novo tem IoU médio .8208 nas mesmas 5 unidades contra .8114 do L11-7 (+.009). `thin-keep/off` deixam de ser no-op (fecham um pouco de spill). Nenhuma passa a `default-candidate` por esta mudança; `iters-15` não foi medida na phase (a) antiga (interrompida).
- **Fase (b): combinações dos `default-candidate`.** Só há um (`iters-15`), então combinei com as duas alavancas de spill/contact mais fortes: `iters-15+spill-w3` (Δ spill -.0230, Δ IoU -.0125, 23 vistas caem),
  `iters-15+fit-parts` (-.0084, +.0093, 7 vistas, contact +.033, +92 s), `iters-15+spill-w3+fit-parts` (-.0191, -.0140, 23 vistas). Nenhuma é `default-candidate`: os ganhos de spill vêm de bare (IoU), não somam.
  Melhor trade: `iters-15` sozinha.
- **Fase (c) (cor: `--ramp`, `--fit-luma`, `--atlas`, `--materials`, `palette_snap`, `--texture painted`): NÃO corrida** (a phase (a) levou ~5 h a 2-4 jobs com a máquina compartilhada); os variantes `c-*` ficam definidos
  em `VARIANTS` e `python3.14 tools/blender/ablation_matrix.py --variants c-base,c-legacy,... --units ...` os mede (aberto).
- **Aceite do brief.** Matriz completa de forma (a) feita; (b) feita; (c) aberta; csv+md copiados ao paper. Defaults não mudaram. Teste de cobertura verde.

### 30.L12-10b Bateria v15 (autor LLM + tudo da Leva 12) pareada com v13, e a guarda sobre o spec novo (2026-10-30)

- **Protocolo.** `spec_pipeline.py --model session:opus --kind mass --run v15-r1 --pair v13-r1` nas 6 unidades (2 a 2, `nice -n 10`, `SOFT_SIL_THREADS=4`; defaults atuais, sem `--tilts`). Controle de guarda
  `v15-r1-guard`: o spec da v15 reconstruído sem LLM (`--spec`, `--no-repair --no-diagnose`) com `--author-guard revert --incoherent-weight 1.0 --noise runs/draft/noise-l12.json` e as câmeras da v15 pinadas
  (hfoo sem pinar, ver abaixo). 0 `FAIL(infra)` (a regra do L12-4 não disparou); exit 1 em 6/6 (gate de forma), nenhum bug bloqueou, código intocado. v13-r1 foi remedido com os gates novos: IoU idêntico
  ao original; `contact` recalculado (`sil-recheck`). Imagens e tabelas em `history/2026-10-30-v15/` (README com a tabela completa, `<id>-full.png`, `<id>-spill.png`).
- **Resultado (spill/bare/IoU/contact por vista na README).** Média das 6 unidades (6 vistas): IoU .823 (v13) / .814 (v15) / .823 (guard); spill .118 / .117 / .104; bare .081 / .092 / .090.
  Vistas com spill <= .03: 0 / 0 / 2 de 36. Vistas com bare <= .10: ver README. **PASS honesto 0/6 nas três versões.**
- **Aceite do roadmap (L12-10): NÃO.** spill <= 3 % em >= 5 vistas/unidade em >= 4/6: 0/6. PASS honesto >= 3/6: 0/6. Número real: o spill por vista fica em .05–.30 (v15), 2–10 vezes o teto.
- **Juiz pareado v15 x v13.** Forma: v13 4/6 (4-0 em n00U, hfoo, n017, n02X), v15 1/6 (n005 4-0), empate n01X. Sheet/artista/wc3: v13 8 de 18 eixos, v15 3, empate 7 (n01X artista/wc3 v15 4-0; n02X sheet v15 3-1). O stage 2 agora existe nas
  duas versões (L12-4), então a comparação de look é de texturizado contra texturizado; ainda assim a v13 ganha em forma.
- **z_err** (régua L12-8) <= .05 H em 2/6 (n005 .020, n01X .024; n00U .135, n017 .141): aceite de z não atendido, a régua só mede. **planarity** .010–.059 (sem look opt-in).
- **Guarda (L12-3 "não medido com autor novo").** Ações: n005, n017, hfoo `reject-bare`; n00U `intact`; n02X, n01X `revert`. Média IoU +.009 sobre a v15 (igual à v13) e spill .117 -> .104; hfoo left .626 -> .729, n005 bottom +.026;
  perde n005 rts (.884 -> .831, spill .067 -> .135) e n02X front −.014. Nenhuma unidade vira PASS (spill/bare ainda 3–10x o teto): a guarda protege contra o spec do autor, não cria forma.
  **Bug de protocolo achado (não corrigido, fora do território):** pinar `--tilts` de um spec cujo painel top/bottom tem orientação oposta à do massing faz o massing/`reject-bare` medir o modelo girado
  180º (hfoo top .177 / bottom .186, bare .82); o run foi guardado como `hfoo/v15-r1-guard-pintilt-invalid` e refeito sem `--tilts`. A guarda deveria pinar o tilt do massing para o massing.
- **Onde está o vermelho (tabela da L12-5, v15).** corpo: n005 (ombros/braços no top), n00U (pernas largas, rts .247, left .180), n02X (placas do peito/cinto no top/bottom .20/.17), n01X (antebraço e pés); prop: hfoo (pique em left/top/bottom/rts,
  mochila no left), n02X (clava atrás do corpo); vista incoerente: n017 rts (.268, sheet .58), hfoo rts (.376, sheet .57), n00U top/bottom (.53/.49).
  Em front/back de todas as unidades o spill é .05–.13 só do corpo (v15), sem prop nem incoerência: o corpo de prismas/SDF não encosta por dentro do contorno.
- **Decisão.** Nenhum default muda. `--author-guard revert` continua opt-in: IoU médio +.009, spill médio −.013, mas perde rts no n005; fica para depois do polimento. A causa do vermelho que sobra é de forma, não de peso: próximo
  trabalho é o polimento MCP (L12-11) com o spill por vista como gate e as listas de partes vermelhas do `diagnosis` como brief.
- **Aberto.** (1) pinar o tilt do massing na guarda; (2) spill <= .03 exige um passo de forma que encoste por dentro (L12-11 ou prismas com inscrição por construção); (3) hfoo: o pique inclinado do sheet (front vertical + left diagonal) com `rot` por peça; (4) tokens do autor não são logados; (5) matriz de ablação L12-10a (outro worktree) não incluída aqui.

v15-r1-guard = o spec da v15 reconstruído sem LLM com `--author-guard revert --incoherent-weight 1.0 --noise noise-l12.json`.

| un. | versão | IoU f/l/b/top/bot/rts | spill | bare | contact | spill ≤ .03 | bare ≤ .10 | veredito honesto |
|---|---|---|---|---|---|---|---|---|
| n005 | v13 | .921 / .947 / .932 / .764 / .833 / .878 | .050 / .031 / .049 / .159 / .071 / .074 | .032 / .024 / .021 / .106 / .110 / .056 | .553 / .628 / .613 / .090 / .219 / .284 | 0/6 | 4/6 | FAIL (spill > .03 em 6/6) |
| n005 | v15 | .913 / .944 / .934 / .807 / .822 / .884 | .056 / .039 / .050 / .117 / .062 / .067 | .034 / .019 / .018 / .096 / .131 / .057 | .496 / .624 / .657 / .147 / .233 / .331 | 0/6 | 5/6 | FAIL (spill > .03 em 6/6) |
| n005 | v15-guard | .909 / .946 / .917 / .814 / .848 / .831 | .055 / .027 / .055 / .114 / .061 / .135 | .040 / .029 / .031 / .090 / .103 / .045 | .529 / .649 / .527 / .214 / .271 / .272 | 1/6 | 5/6 | FAIL (spill > .03 em 5/6) |
| n00U | v13 | .886 / .782 / .885 / .738 / .704 / .665 | .073 / .176 / .079 / .212 / .241 / .273 | .048 / .061 / .043 / .079 / .094 / .113 | .348 / .256 / .323 / .153 / .163 / .089 | 0/6 | 5/6 | FAIL (spill > .03 em 6/6) |
| n00U | v15 | .897 / .770 / .887 / .785 / .778 / .702 | .050 / .180 / .060 / .132 / .182 / .247 | .058 / .073 / .059 / .109 / .058 / .089 | .303 / .233 / .263 / .254 / .229 / .180 | 0/6 | 5/6 | FAIL (spill > .03 em 6/6) |
| n00U | v15-guard | .906 / .775 / .895 / .754 / .799 / .722 | .051 / .165 / .061 / .138 / .149 / .205 | .048 / .085 / .049 / .143 / .072 / .113 | .296 / .225 / .274 / .196 / .238 / .194 | 0/6 | 4/6 | FAIL (spill > .03 em 6/6) |
| hfoo | v13 | .847 / .415 / .853 / .796 / .859 / .703 | .081 / .404 / .081 / .109 / .092 / .217 | .086 / .422 / .078 / .118 / .059 / .128 | .606 / .107 / .631 / .201 / .233 / .152 | 0/6 | 3/6 | FAIL (spill > .03 em 6/6) |
| hfoo | v15 | .853 / .626 / .854 / .661 / .695 / .450 | .123 / .288 / .129 / .122 / .118 / .376 | .031 / .163 / .022 / .272 / .233 / .382 | .611 / .240 / .557 / .090 / .107 / .068 | 0/6 | 2/6 | FAIL (spill > .03 em 6/6) |
| hfoo | v15-guard | .785 / .729 / .789 / .655 / .700 / .593 | .128 / .185 / .128 / .039 / .026 / .345 | .113 / .127 / .107 / .328 / .287 / .137 | .386 / .297 / .401 / .131 / .115 / .072 | 1/6 | 0/6 | FAIL (spill > .03 em 5/6) |
| n017 | v13 | .924 / .775 / .870 / .822 / .871 / .700 | .048 / .077 / .095 / .077 / .057 / .242 | .030 / .171 / .043 / .117 / .081 / .098 | .503 / .382 / .317 / .434 / .509 / .161 | 0/6 | 4/6 | FAIL (spill > .03 em 6/6) |
| n017 | v15 | .918 / .797 / .861 / .881 / .861 / .684 | .059 / .083 / .107 / .076 / .064 / .268 | .027 / .141 / .040 / .050 / .085 / .087 | .475 / .366 / .306 / .488 / .438 / .176 | 0/6 | 5/6 | FAIL (spill > .03 em 6/6) |
| n017 | v15-guard | .903 / .802 / .858 / .862 / .893 / .730 | .072 / .079 / .114 / .084 / .048 / .213 | .029 / .139 / .036 / .064 / .065 / .091 | .394 / .336 / .308 / .411 / .468 / .159 | 0/6 | 5/6 | FAIL (spill > .03 em 6/6) |
| n02X | v13 | .907 / .837 / .918 / .766 / .774 / .805 | .070 / .098 / .061 / .185 / .127 / .095 | .026 / .080 / .023 / .072 / .128 / .120 | .502 / .492 / .533 / .108 / .152 / .239 | 0/6 | 4/6 | FAIL (spill > .03 em 6/6) |
| n02X | v15 | .896 / .852 / .898 / .757 / .760 / .747 | .048 / .059 / .044 / .204 / .169 / .097 | .061 / .100 / .063 / .061 / .101 / .188 | .499 / .455 / .464 / .056 / .080 / .222 | 0/6 | 4/6 | FAIL (spill > .03 em 6/6) |
| n02X | v15-guard | .882 / .862 / .892 / .810 / .759 / .748 | .069 / .063 / .061 / .146 / .147 / .092 | .056 / .085 / .053 / .059 / .127 / .191 | .365 / .452 / .450 / .145 / .113 / .200 | 0/6 | 4/6 | FAIL (spill > .03 em 6/6) |
| n01X | v13 | .866 / .881 / .869 / .908 / .901 / .840 | .101 / .086 / .101 / .042 / .075 / .129 | .041 / .039 / .038 / .055 / .028 / .042 | .558 / .511 / .548 / .316 / .299 / .250 | 0/6 | 6/6 | FAIL (spill > .03 em 6/6) |
| n01X | v15 | .821 / .892 / .822 / .912 / .836 / .859 | .102 / .068 / .103 / .054 / .095 / .113 | .095 / .046 / .092 / .038 / .084 / .036 | .434 / .460 / .414 / .356 / .230 / .271 | 0/6 | 6/6 | FAIL (spill > .03 em 6/6) |
| n01X | v15-guard | .849 / .934 / .851 / .905 / .873 / .853 | .104 / .043 / .104 / .062 / .059 / .116 | .058 / .025 / .055 / .037 / .077 / .039 | .462 / .646 / .443 / .284 / .284 / .288 | 0/6 | 6/6 | FAIL (spill > .03 em 6/6) |

Colunas por vista na ordem front / left / back / top / bottom / rts. Gates da L12-2: spill <= .03 e bare <= .10 por vista, sem média; **veredito honesto =
FAIL se alguma vista passa do teto** (os `PASS` que o `compare_runs` mostra para v13-r1 são do gate antigo; o v13 foi remedido aqui com os tetos novos,
IoU idêntico ao `silhouette.json` original). `contact` do v13-r1 recalculado das máscaras (`silhouette.py` sobre `v13-r1/clay.glb` com as câmeras
pinadas do próprio run; IoU de 6/6 vistas × 6 unidades diferença 0.000; saída em `runs/draft/<id>/v13-r1/sil-recheck`, `contact-v13.json`; `v13-r1/sil/approved` e `views/`
foram regenerados para as imagens, os originais tinham sido podados).

Médias das 6 unidades (média das 6 vistas): IoU .823 / .814 / .823 (v13 / v15 / v15-guard); spill .118 / .117 / .104; bare .081 / .092 / .090.
Vistas com spill <= .03 no total (36 vistas): **0 / 0 / 2** (n005 left .027 e hfoo bottom .026 na guarda).

**Aceite do roadmap L12-10**

- spill <= 3 % em >= 5 vistas/unidade em >= 4/6 unidades: **NÃO, 0/6** (v15) e 0/6 (v15-guard; melhor unidade: 1 vista).
- PASS honesto >= 3/6: **NÃO, 0/6** nas duas versões (e 0/6 no v13 com o gate novo).
- Stage 2 (cor) PASS em 5/6 (hfoo stage 2 FAIL por cobertura de zonas do top/bottom, verdito real, não infra); 0 FAIL(infra), exit 1 em 6/6 (gate de forma).

**Juiz pareado v15 x v13 (4 votos, A/B trocados; vencedor e votos; 'v13' = A, 'v15' = B)**

| un. | sheet | artista | wc3 | forma |
|---|---|---|---|---|
| n005 | v13 4-0 | v13 4-0 | v13 4-0 | **v15 4-0** |
| n00U | 2-2 | v13 4-0 | v13 4-0 | v13 4-0 |
| hfoo | 2-2 | 2-2 | 2-2 | v13 4-0 |
| n017 | v13 3-1 | v13 4-0 | v13 4-0 | v13 4-0 |
| n02X | **v15 3-1** | 2-2 | 2-2 | v13 4-0 |
| n01X | 2-2 | **v15 4-0** | **v15 4-0** | 2-2 |

O juiz prefere v13 em forma em 4/6 (empata em 1, v15 em 1). Cor/estilo: v13 em 8 eixos, v15 em 3, empate em 7 de 18 (stage 2 agora existe nas duas, 6/6).

**Métricas novas (v15-r1)**

| un. | z_err (H) | marcos | planarity | wire entropy | tempo autor / build / passes / cor (s) | verdito |
|---|---|---|---|---|---|---|
| n005 | .020 | 11/13 | .059 | .965 | 88 / 360 / 160 / 53 | CHECK |
| n00U | .135 | 7/11 | .010 | .991 | 95 / 352 / 64 / 57 | CHECK |
| hfoo | .056 | 6/14 | .016 | .988 | 104 / 366 / 312 / 54 | CHECK |
| n017 | .141 | 4/11 | .027 | .990 | 82 / 357 / 15 / 59 | CHECK |
| n02X | .061 | 18/20 | .048 | .986 | 128 / 378 / 86 / 56 | CHECK |
| n01X | .024 | 11/12 | .018 | .991 | 68 / 349 / 66 / 53 | CHECK |

z_err <= .05 H em 2/6 (n005, n01X). Tokens do autor não são registrados pela chamada `session:opus` (só o tempo `t_gen`).

**Guarda (v15-r1-guard; `--author-guard revert --incoherent-weight 1.0 --noise noise-l12.json`, spec do autor da v15, câmeras pinadas da v15)**

Ação da guarda: n005 `reject-bare`, n00U `intact`, hfoo `reject-bare` (6 ossos revertidos e ainda abaixo do massing em left/top/bottom/rts), n017 `reject-bare`, n02X `revert`, n01X `revert`.
IoU médio .823 (= v13, +.009 sobre a v15) e spill médio .117 -> .104. Ganhos: hfoo left .626 -> .729 (corpo), n005 top/bottom +.007/+.026, n00U bottom +.021.
Perdas: n005 rts .884 -> .831 (spill .067 -> .135), n02X front −.014, hfoo rts/top. Nenhuma unidade vira PASS; spill por vista continua 3–10x o teto.
**Protocolo hfoo:** o primeiro guard do hfoo (`v15-r1-guard-pintilt-invalid`) usou as câmeras pinadas da v15 (top −20/bottom +20); o massing do hfoo escolhe o espelho oposto
(+20/−20, painel girado), então com a câmera pinada o massing e o `reject-bare` mediam top .177 / bottom .186 (modelo girado 180º contra o painel). Medida inválida; o `v15-r1-guard` do hfoo foi refeito sem `--tilts`
(a câmera sai do próprio varrimento). Aberto: `--tilts` copiado de um spec com orientação de painel diferente do massing quebra a guarda; a guarda deveria pinar o tilt **do massing** para o massing.

**Onde está o vermelho (v15, por causa; tabela da L12-5)**

| un. | vistas piores (spill) | causa (corpo / prop / vista incoerente) |
|---|---|---|
| n005 | top .117, front .056 | corpo: ombros/braços (arm.L, forearm) grossos no top; botas no top; sem recesso do capuz |
| n00U | rts .247, bottom .182, left .180 | corpo: pernas largas (prismas) — top/bottom incoerentes (.53/.49), por isso não gateadas para IoU, mas o spill continua medido |
| hfoo | rts .376, left .288, top/bottom .12 | prop: pique (left, top, bottom, rts); corpo: mochila e botas (left); rts incoerente (.57) |
| n017 | rts .268, back .107 | vista incoerente (rts .58) + placas do dorso largas, corda reta no chão (left) |
| n02X | top .204, bottom .169 | corpo: placas do peito e cinto (1.10 x 1.04) no top/bottom; clava atrás do corpo (prop left IoU .12) |
| n01X | front/back .10, rts .113, bottom .095 | corpo: antebraço colado ao torso, cabeça deslocada, pés fundos em z |

**Imagens**

`<id>-full.png`: colunas concept | clay | wire | overlay | textured para v13-r1 | v15-r1 | v15-r1-guard, 6 vistas. `<id>-spill.png`: overlay das 6 vistas por versão
(amarelo = acerto, vermelho = modelo fora do sheet, verde = sheet descoberto), com spill% e bare% por célula (vermelho se spill > 3 %).


## 31. Leva 13 (2026-10-30): polir o 3D criado

### 31.L13-1 Estágio `polish`: o modelo (Claude) polui o clay por MCP, com gates honestos (2026-10-30)

**O que entrou.** `tools/blender/polish.py` (estágio + `Session`: estado, `apply` com gate e reversão, overlays, instalação), `polish_mcp.py` (servidor MCP stdio, JSON-RPC 2.0 à mão: o pacote `mcp` não existe no python3.14; `initialize`, `tools/list`, `tools/call`), `polish_ops.py` (as mãos), `--polish on|off` em `spec_pipeline.py` (default off; só com `--model session:<claude>`; antes do stage 2, e depois dele o `model.glb` recebe o polimento). Ferramentas MCP: `state`, `views`, `inspect(view, region)`, `apply(python_code, why, dry_run)`, `done(summary)`. Helpers no código do agente: `parts`, `shrink_part`, `move_part`, `scale_part`, `erode_toward_view`, `smooth_region`, `straighten_prop`, `snap_feet_to_ground`.

**Desvio do brief, de propósito:** sem Blender. As ops editam os bytes POSITION/NORMAL do GLB (`deform_to_sheet.rewrite`, o mesmo caminho do deform e do optimize_verts): skin, pesos, UV, materiais e clipes ficam como estão, o rig sobrevive por construção, e uma op custa ~1 s mais ~7 s do gate (`silhouette.py`, o Blender só renderiza as máscaras). Parte = osso dominante do vértice (`abdomen`, `leg3.upper`; família `leg3`). `erode_toward_view` projeta pela câmara pinada do gate (`optimize_verts.make_views`), empurra no plano da imagem (empurrar ao longo do raio não muda a projeção) os vértices em vermelho para dentro do contorno do sheet, e o resto da parte segue por um solve laplaciano (o de `deform_to_sheet`).

**Gate de cada op** (contra o estado anterior E contra o início; reverte sozinho, devolve "rejected: <razão>"): spill de qualquer vista +.005; IoU −.003 (mais apertado que 2σ do `noise-l12.json`: a op repete sobre malha fixa, sem ruído de rebuild, e o aceite é "nenhuma vista cai"); bare > .10 e subindo > .005; tris diferente; `mesh_lint` (flipped, degenerate, não-manifold, slivers +5 pp). Orçamento: 5 min, 12 ops aceitas, 24 tentativas; `dry_run` mede sem gastar op. Saída no run: `clay.glb` novo só se alguma op passou, `clay.prepolish.glb`, `polish.py` (ops aceitas, `# why:`, replay com `polish.py <run> --id <id> --replay <run>/polish.py`), `polish.json` (ops, razões, tabela antes/depois, tokens), seção "Polimento" no `review.md`, `sil/approved` e `silhouette.json` remedidos, `model.glb` com o deslocamento carregado do clay (`polish_ops.carry`: vizinho mais próximo, deslocamento por vértice de ARQUIVO; a ordem dos vértices soldados muda quando eles se movem, e a primeira versão, por índice soldado, piorou o `model.glb` em até .08 de spill) e `model.prepolish.glb`.

**Piloto** (6 unidades, `v15-r1` copiado para `v15-r1-polish`, `session:opus`, `--budget-min 6 --max-ops 12`; imagens antes|depois em `history/2026-10-30-l13-polish/<id>.png`; verde = sheet descoberto, vermelho = modelo fora do sheet):

| unidade | ops aceitas/tentadas | tempo | tokens saída | vistas com spill menor (> .001) | pior IoU | spill ≤ .03 antes→depois |
|---|---|---|---|---|---|---|
| n005 | 1/1 | 299 s | 14.5 k | 1 | −.0016 | 0→0 |
| n00U | 2/2 | 305 s | 11.4 k | 5 | −.0028 | 0→0 |
| hfoo | 1/1 | 281 s | 15.2 k | 2 | −.0003 | 0→0 |
| n017 | 3/3 | 301 s | 12.4 k | 5 | −.0024 | 0→0 |
| n02X | 2/2 | 301 s | 13.9 k | 6 | −.0011 | 0→0 |
| n01X | 3/6 | 341 s | 11.9 k | 5 | −.0011 | 0→0 |

Spill por vista (antes → depois): n005 .056→.055 / .039→.039 / .050→.049 / .117→.117 / .062→.060 / .067→.066; n00U .050→.047 / .180→.174 / .060→.057 / .132→.127 / .182→.174 / .247→.247; hfoo .123→.122 / .288→.287 / .129→.128 / .122→.122 / .118→.118 / .376→.376; n017 .059→.059 / .083→.071 / .107→.105 / .076→.073 / .064→.056 / .268→.261; n02X .048→.047 / .059→.053 / .044→.042 / .204→.189 / .169→.164 / .097→.091; n01X .102→.074 / .068→.067 / .103→.074 / .054→.046 / .095→.091 / .113→.102. O maior ganho real é n01X front/back (−.028). Bare sobe em quase toda vista (+.001..+.012), contact varia ±.02..±.04.

**Aceite: NÃO atendido.** Vistas com spill ≤ .03: 0/36 → 0/36 (pedia ≥ 12/36). Spill cai em ≥ 4 vistas em 4/6 unidades, mas por .001..–.03 (pedia ≥ 4/6 com efeito). "Nenhuma vista cai": o IoU cai até .0028 em algumas vistas (dentro da tolerância .003 do gate). `model.glb` carregado acompanha o clay (n00U: front .053→.047, left .186→.180, bottom .182→.175).

**Por que não resolveu.** Os 342–364 vértices são compartilhados entre as seis vistas e cada vista é enquadrada pelo bbox do próprio modelo: apertar um vértice extremo encolhe o bbox, a vista reescala e o ganho some; uma op que limpa o vermelho em left suja top/bottom/rts (n00U: erode em left −.027 de spill, +.03 em top/bottom/rts, revertida). É o mesmo 1:1 da matriz L12-10a, agora medido com um agente olhando as imagens. O agente achou sozinho o truque de travar os vértices que definem o bbox e de escopo por parte (n00U), e mesmo assim o teto foi −.008. O que o polimento grosso não alcança: forma errada por vista (patas n00U rts, lança hfoo, placas n02X top).

**Custo.** ~5 min e ~12–15 k tokens de saída (+ 250–490 k de cache lido) por unidade com `session:opus`.

### 31.L13-2 A guarda do autor mede cada candidato com o tilt dele (bug hfoo 180) e remedição (2026-10-30)

**Bug (L12-10b, confirmado em `runs/draft/hfoo/v15-r1-guard-pintilt-invalid`):** `--tilts` pinado vale para o modelo final, mas
`guard_measure` o repassava a TODOS os candidatos da guarda. O spec do autor do hfoo varre top -20 / bottom +20; o massing varre
+20 / -20 (painel de orientação oposta). Com o pin, `guard/massing/silhouette.json` mediu top .177 / bottom .186 / bare .82 (modelo girado 180
graus contra o painel); sem pin, o mesmo massing dá top .678 / bottom .730. Segunda ponta do mesmo erro: quando a guarda devolve o corpo do massing
(`reject`, `reject-bare`, `revert`), o run seguia com o pin do autor, e o modelo final saía girado (guard2 so com o fix 1: top .176, bottom .185).

**Fix (2 pontos, ambos em `spec_pipeline.py`):**
1. `guard_measure`: cada candidato varre as próprias câmeras (`a.tilts = ""` na cópia dos args; o pin do run fica intacto).
2. `guard_repin` (novo, chamado logo depois de `guard_stage`): se a guarda trocou o spec, `args.tilts` passa a ser o `tilt` do `silhouette.json` do candidato
   mantido (`guard/<ação>/`; `reject-bare` sai sem medir e lê o do massing). `intact`/`skipped` mantêm o pin. Grava `guard.repinned` no relatório.
Testes (`test_author_guard.py`): `MeasureTilt` (vermelho sem o fix 1, verde com) e `Repin`. Suite 760 OK (11 skip), ruff limpo.

**Remedição** (`v15-r1-guard2`, specs v15, `--author-guard revert --incoherent-weight 1.0 --noise noise-l12.json`, tilts pinados da v15, 6 unidades; `v15-r1-guard2-fix1only` = so o fix 1, guardado como medida intermediária em hfoo/n017/n02X/n01X). Médias das 6 unidades (6 vistas):

| versão | IoU | spill | bare | contact | vistas spill<=.03 (de 36) |
|---|---|---|---|---|---|
| v15-r1 (controle) | .814 | .117 | .092 | .328 | 0 |
| v15-r1-guard (antigo, hfoo refeito sem pin) | .823 | .104 | .090 | .319 | 2 |
| guard2 so fix 1 | .766 | .109 | .142 | .306 | - |
| **guard2 (fix 1 + 2)** | .821 | .110 | .086 | .324 | 1 (e bare<=.10: 0) |

Por unidade (IoU front/left/back/top/bottom/rts de guard2; ação da guarda; `*` = queda > 2 sigma contra v15-r1):
n005 `intact` (identico a v15-r1, +-.003); n00U `intact` (.904/.772/.896/.750/.797/.723; top -.034 sem marca de queda real); hfoo `reject-bare` (.792/.742/.797 top **.658** bottom **.705** rts .601; front -.068* e back -.067* contra o autor, left +.109*, rts +.151*);
n017 `reject-bare` (front -.016*, top/bottom/rts +.037/+.042/+.037); n02X `reject-bare` (front -.015*, left -.012*, top +.030, bottom +.018, rts +.024);
n01X `reject` (front/left/back +.028/+.029/+.029, **top -.091***, rts -.044*). Tabela completa por vista (IoU/spill/bare/contact) nos logs do run; os silhouette.json estão em cada `v15-r1-guard2*/`.

**Aceite (roadmap):** (a) hfoo top/bottom coerentes IoU >= .6: **SIM** (.658/.705; antes do fix .177/.185). (b) guard2 >= guard em spill médio: **NAO** (.110 contra .104, diferença dentro do ruído, mas pior). (c) nenhuma vista coerente cai > 2 sigma: **NAO** (n01X top -.091, rts -.044; hfoo front/back -.068; n017 front, n02X front/left, ~-.015).
**Resposta:** com a medição certa a guarda NÃO ajuda: spill .117 -> .110 (dentro de 2 sigma), bare .092 -> .086, 1/36 vistas com spill <= .03 contra 0, e troca vistas coerentes (front/back do hfoo, top do n01X) por ganhos nas incoerentes. Fica **opt-in** (`--author-guard off` default). O bug está corrigido e coberto por teste; o ganho da guarda continua o que a L12-10b mediu (marginal).
Aberto: a guarda decide por IoU de 6 vistas contra o massing, sem olhar spill; uma guarda por spill por vista (não por IoU) seria a próxima tentativa, mas a matriz L12-10a já mostrou que spill e bare trocam 1:1.

### 31.L13-3 `--depth` igual a `--fit-parts`: diagnóstico e veredito (2026-10-30)

- **Pergunta.** Na matriz L12-10a `fit-parts` e `fit-depth` deram IoU/spill/bare idênticos nas 6 unidades (Δ spill −.0054, Δ IoU +.0048 as duas). `--depth` morto, ou sem dados?
- **Onde os caminhos se juntam.** `spec_pipeline.fit_stage` passa `partfit=args.fit_parts or bool(args.parts) or args.depth`: `--depth` sozinho já liga o `partfit`; a única diferença para `--fit-parts` é `fit_spec.fit` (linha `if depth and proxy.partfit:`) chamar `depth_map.depth_init`. Essa função só tem dois efeitos: (1) mover a peça sem máscara left por `z = a*disp + b`, **só se r >= MIN_R (.7)**; (2) refazer os pares de oclusão, **só se nenhum `depth_order` do `parts.json` for != 0**. Devolvendo as mesmas peças e os mesmos pares, a busca (determinística) é a mesma.
- **Prova (dos `fit/fit.json` da matriz `l12-mx-fit-depth` e de `depth_init` remedido nos specs v15 com a sonda do scratchpad).** `moved` = {} e `pairs_from_depth` ausente nas 6; `depth_pairs`, `loss`, `evals`, `free` iguais ao `fit-parts` (hfoo [21,1] 1.1229->1.0886 1250 evals; n005 [20,0]; n00U [39,36]; n017 [32,0]; n02X [21,7]; n01X [1,0]). r (marcos): hfoo .17 (9), n005 −.22 (9), n00U −.79 (5), n017 −.98 (4), n02X −.22 (17), n01X .38 (10): nenhuma >= .7; n00U e n017 ainda têm todas as peças com máscara com caixa left (nada a colocar). Peças devolvidas idênticas (`out == parts`) nas 6.
- **Veredito: (a), não é bug.** A flag chega, a calibração roda, o termo não é zerado; é um no-op por dados (r < MIN_R + `depth_order` já preenchido), como o L12-8 dizia ("`--depth` não move peça") mas sem avisar. O que mudou: `depth_init` agora põe `report["noop"]` (vai a `fit/fit.json`) e imprime `no-op: --depth: r=0.17, r < 0.7; parts.json already has depth_order: the fit is --fit-parts`. Sem mudar default nem número do fit.
- **`test_flag_liveness` provava só chegada do kwarg.** `live_depth` agora exige também que, com r >= .7 num fixture sintético, `depth_init` mude o z de uma peça (par off/on = z antes/depois); `test_depth_map` (+1) cobre a mensagem de no-op e o seu silêncio quando a peça se move.
- **`--depth-source tri` (mesma pergunta).** Só o n00U mexe (3 propostas, 1 mantida: `body frustum` −.119 m; as 2 do `leg8` recusadas pelo proxy), n02X 1 proposta recusada, as outras 0. Matriz `depth-tri`: Δ spill −.0015, z_err igual, 0/36 vistas > 2σ de ganho; as 5 unidades restantes bit a bit iguais ao controle. Razão: a triangulação só move peça cujo z cai >.05 H fora de uma `box3d` existente, e 0 das 18 `box3d` null foram preenchidas (L12-8: 9 `inside-other-parts`, 9 `envelope`; o casco não cria caixa). Flag viva, efeito de uma peça numa unidade; fica opt-in.
- **Aberto.** Uma calibração que passe de .7 precisa de sinal de z confiável (L12-8 aberto b/c); até lá `--depth` só é útil para sheets cujo `parts.json` não traz `depth_order` (aí refaz os pares).
- **Arquivos.** `tools/blender/depth_map.py` (`no_effect`, `report["noop"]`), `tests/tools/blender/test_depth_map.py`, `tests/tools/blender/test_flag_liveness.py`.
