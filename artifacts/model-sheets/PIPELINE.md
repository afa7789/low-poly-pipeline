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
