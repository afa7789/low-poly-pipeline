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
python3 generate.py draft2/prompts/unit-n01N.txt --out draft2 --name n01N
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
  draft1/                first model comparison, kept as-is
  draft2/                the accepted set
    <id>.jpg             one sheet per unit
    prompts/             00-template-{unit,building}.txt + unit-<id>.txt + building-<id>.txt
    audit/               weapon-role-audit.md, unit-chains.md
    glb/                 build_unit.py output: <id>.glb + the six render frames
```

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
three material slots, rigid-skinned (one bone per piece, weight 1) and given four actions:
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
| mesh count / materials | 1 mesh, 3 primitives, 3 materials |
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

A row also fails when the model is not one skin with three materials and four clips. Measured on
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
