# draft4 — `argon` vs `opus55`, unit by unit

Two spec authors, same 6 units, same brief, same builder (`tools/blender/build_unit.py`), same
gates. Everything below is read off the files in this folder; nothing is estimated.

- Build/gate numbers: `python3 tools/blender/check_gates.py artifacts/model-sheets/draft4/glb --kind mass`
  (mass budget 400–700 tris, and 3 materials / 1 skin / 4 clips — `tools/blender/check_gates.py`).
- Spec numbers: `specs/{argon,opus55}-<id>.json`, counted over the `parts` array.
- Render paths: `argon/<id>.gif`, `opus55/<id>.gif`, existence and byte size checked on disk.

All 12 GLBs PASS the mass gate. All 12 turntable GIFs exist.

## Table 1 — build size and gate result

| unit | name | argon tris | opus55 tris | argon parts | opus55 parts | argon gate | opus55 gate |
|---|---|---|---|---|---|---|---|
| hfoo | Footman (Human) | 664 | 540 | 34 | 37 | PASS | PASS |
| n005 | Warlock (Human) | 660 | 616 | 39 | 38 | PASS | PASS |
| n02X | Ogre (Desert) | 636 | 616 | 37 | 38 | PASS | PASS |
| n00U | Black Spider (Nature) | 452 | 512 | 35 | 40 | PASS | PASS |
| n01X | Iron Golem (Mech) | 460 | 616 | 30 | 38 | PASS | PASS |
| n01I | Corrupted Ent | 516 | 552 | 35 | 38 | PASS | PASS |
| **total** | | **3388** | **3452** | **210** | **229** | 6/6 | 6/6 |

Gate output, verbatim (`tris`, `budget`, `mats`, `skin`, `anims`):

```
file                          tris     budget  mats skin anims  gate
argon-hfoo.glb                 664    400-700     3    1     4  PASS
argon-n005.glb                 660    400-700     3    1     4  PASS
argon-n00U.glb                 452    400-700     3    1     4  PASS
argon-n01I.glb                 516    400-700     3    1     4  PASS
argon-n01X.glb                 460    400-700     3    1     4  PASS
argon-n02X.glb                 636    400-700     3    1     4  PASS
opus55-hfoo.glb                540    400-700     3    1     4  PASS
opus55-n005.glb                616    400-700     3    1     4  PASS
opus55-n00U.glb                512    400-700     3    1     4  PASS
opus55-n01I.glb                552    400-700     3    1     4  PASS
opus55-n01X.glb                616    400-700     3    1     4  PASS
opus55-n02X.glb                616    400-700     3    1     4  PASS

12 models, 0 failing
```

## Table 2 — turntable renders (paths relative to repo root)

Both columns verified present on disk; sizes in KiB.

| unit | argon render | opus55 render |
|---|---|---|
| hfoo | `artifacts/model-sheets/draft4/argon/hfoo.gif` (172 KiB) | `artifacts/model-sheets/draft4/opus55/hfoo.gif` (164 KiB) |
| n005 | `artifacts/model-sheets/draft4/argon/n005.gif` (192 KiB) | `artifacts/model-sheets/draft4/opus55/n005.gif` (188 KiB) |
| n02X | `artifacts/model-sheets/draft4/argon/n02X.gif` (209 KiB) | `artifacts/model-sheets/draft4/opus55/n02X.gif` (199 KiB) |
| n00U | `artifacts/model-sheets/draft4/argon/n00U.gif` (203 KiB) | `artifacts/model-sheets/draft4/opus55/n00U.gif` (241 KiB) |
| n01X | `artifacts/model-sheets/draft4/argon/n01X.gif` (232 KiB) | `artifacts/model-sheets/draft4/opus55/n01X.gif` (212 KiB) |
| n01I | `artifacts/model-sheets/draft4/argon/n01I.gif` (179 KiB) | `artifacts/model-sheets/draft4/opus55/n01I.gif` (174 KiB) |

No row is MISSING — all 12 files exist.

## Table 3 — what is measurably different in the specs

Primitive counts come straight from the `kind` field (`box` / `cyl` / `wheel`); materials from the
material field. `bbox` is WxHxD in spec units (x = right, y = up, z = forward), computed from each
part's dims and position — cylinders are treated as their axis-aligned extent, so it is a
±0.05 approximation. "mirror pairs" counts parts that appear exactly twice with mirrored x and
otherwise identical shape, dims and material — a proxy for how much of the figure is built
bilaterally.

### Geometry counts (argon / opus55)

| unit | parts | boxes | cylinders | wheels | mirror pairs |
|---|---|---|---|---|---|
| hfoo | 34 / 37 | 26 / 34 | 8 / 3 | 0 / 0 | 8 / 9 |
| n005 | 39 / 38 | 33 / 33 | 6 / 5 | 0 / 0 | 8 / 9 |
| n02X | 37 / 38 | 31 / 33 | 6 / 5 | 0 / 0 | 6 / 6 |
| n00U | 35 / 40 | 34 / 39 | 1 / 1 | 0 / 0 | 14 / 15 |
| n01X | 30 / 38 | 28 / 33 | 1 / 5 | **1 / 0** | 10 / 13 |
| n01I | 35 / 38 | 32 / 35 | 3 / 3 | 0 / 0 | 10 / 12 |
| **total** | **210 / 229** | **184 / 207** | **25 / 22** | **1 / 0** | **56 / 64** |

### Materials (argon / opus55)

| unit | brass | iron | flame |
|---|---|---|---|
| hfoo | 14 / 16 | 19 / 20 | 1 / 1 |
| n005 | 4 / 2 | 32 / 33 | 3 / 3 |
| n02X | 16 / 14 | 19 / 22 | 2 / 2 |
| n00U | 3 / 6 | 29 / 33 | 3 / 1 |
| n01X | 13 / 18 | 16 / 18 | 1 / 2 |
| n01I | 24 / 30 | 10 / 7 | 1 / 1 |
| **total** | **74 / 86** | **125 / 133** | **11 / 10** |

### Proportions (WxHxD, spec units, argon / opus55)

| unit | argon | opus55 |
|---|---|---|
| hfoo | 1.02 x 2.47 x 0.70 | 1.10 x 3.16 x 0.82 |
| n005 | 1.58 x 2.35 x 1.18 | 1.45 x 2.74 x 1.18 |
| n02X | 2.11 x 2.82 x 1.16 | 2.01 x 2.68 x 1.13 |
| n00U | 0.96 x 0.63 x 0.91 | 1.74 x 1.18 x 1.53 |
| n01X | 1.98 x 2.51 x 0.87 | 2.18 x 2.69 x 0.69 |
| n01I | 2.18 x 3.02 x 1.87 | 1.94 x 3.01 x 1.33 |

## Concrete differences, in words

- **Triangle profile.** Both sit in the 400–700 budget, with nearly the same total (3388 vs 3452).
  The spread differs: `argon` spans 452–664 (a 212-tri range, and its hfoo is 36 tris off the
  ceiling at 664), `opus55` spans 512–616 (a 104-tri range). `opus55` is the more predictable
  author to budget with; `argon` is the one that can go near the cap.
- **Part count.** `opus55` writes more parts on 5 of 6 units and is tighter (37–40 parts, all 6
  units within 3). `argon` ranges 30–39 and is the only one to come in under 34 parts (n01X, 30).
- **Cylinders vs boxes.** `argon` uses more cylinders overall (25 vs 22), most heavily on the
  humanoid hfoo (8 cyl vs 3) — limbs and joints are rounder. Per unit `argon` leads on 3 (hfoo,
  n005, n02X), the two tie on 2 (n00U, n01I at 1 and 3), and `opus55` leads only on the Mech Iron
  Golem (5 cyl vs 1).
- **The valve wheel.** `argon-n01X` is the only spec of the twelve that emits a `wheel` primitive
  (a torus, `build_unit.py` line 55) — the spoked valve wheel on the golem's head that the concept
  sheet calls for and the built-in reference spec carries. `opus55` builds no wheels at all.
- **Spoke/detail rotations.** `argon` uses the `rot` option 60 times across the six specs,
  `opus55` 30 times. `argon` is the author that fans detail into spokes and radial patterns;
  `argon-n00U` alone uses `rot` 26 times (spider legs), more than any `opus55` unit's entire spec.
- **Material lean.** `opus55` uses more brass overall (86 vs 74) and more iron (133 vs 125); flame
  accent counts are effectively tied (11 vs 10). Per unit the brass split goes `opus55` on 4
  (hfoo, n00U, n01X, n01I) and `argon` on 2 (n005, n02X); the iron split goes `opus55` on 5 of 6,
  with n01I the exception (`argon` 10 iron vs 7). The biggest single divergence is n01I Corrupted
  Ent: `opus55` 30 brass / 7 iron, `argon` 24 brass / 10 iron.
- **Silhouette scale.** `opus55` builds bigger small units and smaller large ones: its hfoo is
  28% taller (3.16 vs 2.47), its spider is nearly twice the size in every axis (1.74 x 1.18 x 1.53
  vs 0.96 x 0.63 x 0.91), while its Desert Ogre is the shorter of the two (2.68 vs 2.82) and its
  Corrupted Ent is narrower (1.94 vs 2.18). If the sheet is drawn at a consistent scale, one of the
  two authors is off it.
- **Bilateral symmetry.** `opus55` scores more mirror pairs on 5 of 6 units (64 vs 56 total),
  i.e. more of its geometry is authored as exact left/right duplicates rather than hand-placed
  once. `argon` is the more asymmetric author.
- **Joint coverage.** Both authors use the same 13 bone names (the rig in `build_unit.py` is fixed
  at 14 joints including root), and they agree on all 6 units except one: `argon-n01I` has **no
  part on the `head` bone** (12 bones used, `opus55` uses 13). That head joint will animate
  nothing in the idle/attack clips for the argon Corrupted Ent.
- **Tri counts are fully explained by the spec.** For all 12 models the gate's triangle count
  equals `12 x boxes + 44 x cylinders + 80 x wheels` (cube, 12-vertex cylinder, 10x4 torus), so the
  two tables above are the same information twice — no hidden geometry.

## What these tables cannot decide

Mesh counts, material split and proportions are above; whether a model *looks like the sheet* is
not measurable from a JSON, and both authors pass every mechanical gate. Watch the paired GIFs in
Table 2 side by side to judge likeness — the numbers only tell you what to look for: `argon` is
the rounder, more detailed, more asymmetric read (with the golem's valve wheel), `opus55` the
boxier, larger, more consistently symmetric one.
