---
name: install-into-game
description: Install one or more hand-built unit models (ids) from lowpoly-pipeline into the Castle Fight game checkout and verify them there. Use for "/install-into-game h000 n02K", "instala no jogo", "manda pro jogo".
---

# /install-into-game <id> [id ...]

`G=${CF_GAME:-/Users/afa/Developer/arthur/castle_fight}`. Run from the pipeline checkout that has `make link` done (`game/`, `assets/`, `artifacts/model-sheets/hand` resolve).

## 1. Model is fresh
For each id: `artifacts/model-sheets/hand/<id>/model.glb` must be newer than `tools/blender/units/<id>.py`.
If not: `tools/blender/hand_review.sh <id> <family>` (family = 2nd arg of `H.build(` in the script).

## 2. Snapshot the game
`git -C $G status --short > $TMPDIR/cf-before.txt`

## 3. Dry run, then write
```bash
python3.14 tools/hand_models_install.py --game $G <ids>           # dry run: read the plan
python3.14 tools/hand_models_install.py --game $G --write <ids>   # copy GLB + palette, rewrite data/models.tsv, drop ids from data/anim_refresh.tsv
```
`make install CF_GAME=$G` installs ALL hand units; use it only when asked for everything.

## 4. Verify in the game (cheap, per unit)
```bash
cd $G
node scripts/fetch_models.mjs --only <id1>,<id2>     # sha256 + .rig/.joints for these rows only
python3 tools/assign_model_clips.py --check          # = make model-clips-check; on drift run it without --check, then --check again
./build/model_cook cook assets/models <id>           # one id per call (substring filter); needs a window
```
- `make glb-check` only if `build/glb_import_check` is missing.
- Skip full `make assets` / `make cook` unless the loader changed. Never `make check` (model work).
- Visual check (optional, ask first): `./build/castle_fight --model-scene hand` (pixel art on).

## 5. Report
- `git -C $G status --short` diffed against the snapshot: new/changed files (`assets/units/<id>/`, `data/models.tsv`, `.cook`).
- Each check: command + OK/FAIL line.
- Pipeline side: `data/anim_refresh.tsv` change.

## Never
- Commit or push in the game repo unless asked.
- `pkill` / kill castle_fight (other agents use it).
- Edit game source to make a check pass; report the failure.
