# AGENTS.md

Instructions for coding agents (Claude Code, Codex, Cursor, ...) working in this repo.

## What this is
Low-poly unit/building model generation + animation tool for the game Castle Fight. Blender scripts build GLBs; Python
tools grade them against concept sheets. `paper/` is the research write-up (Portuguese) of how the pipeline evolved.

## Setup
- `make link CF_GAME=<castle_fight checkout>`: symlinks game data/assets (`game/`, `assets/`, `data/*.tsv`) and the
  ignored output folder. Without it, game data does not resolve.
- Optional: `CF_PAPER=<folder>` with `papers/` (reference PDFs) and `baseline/` (TRELLIS weights + runs, ~30 GB),
  linked into `paper/` by `make link`. Not in git.
- Needs `blender` (4.x) and `python3.14` on PATH; `uvx` for lint.

## Flow (current)
1. Unit = hand script `tools/blender/units/<id>.py` (`hand_unit.py`: wedge pieces rigid on a rig family, family clips,
   64x64 palette). Family = 2nd arg of its `H.build(...)` line.
2. Review: `tools/blender/hand_review.sh <id> <family>` -> `artifacts/model-sheets/hand/<id>/` (sheet.png, clips.png,
   overlay.png, silhouette.txt) + `assets/models-sets/hand/<id>.glb`.
3. Grade: agent `.claude/agents/model-reviewer.md`, gate by gate against `.claude/rules/art-profile.md`.
4. Install into the game: `make install CF_GAME=<game>`.
5. Buildings: hand-modelled Blender scripts `tools/blender/buildings_<race>.py` from the design text (`reports/design/`).

## Verify
- `make test` (unittest, blender suite) + `make lint` (ruff, C901 <= 10). Both must pass before a change is done.
- Install-type scripts write into the game checkout through the links: run them only on purpose.

## Rules
- Generated output (runs, renders, sheets) lives in the ignored output folder, never in git.
- No absolute paths in code: resolve from `__file__`, `CF_GAME`, `CF_PAPER` or `CF_PIPELINE_OUT`.
- Lessons: `tasks/lessons.md` (add one after any correction).
- Every paper used -> one row in `docs/references.md`, same commit.
