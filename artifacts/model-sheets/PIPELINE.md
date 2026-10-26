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

## 18.1 Measuring the shape inside the contour (2026-10-26)

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
