# lowpoly-pipeline

Low-poly unit/building models for Castle Fight. The game checkout is `CF_GAME` (`/Users/afa/Developer/arthur/castle_fight`).

@.claude/rules/art-profile.md

## Flow (current)
1. Unit = hand script `tools/blender/units/<id>.py` (`hand_unit.py`: wedge pieces rigid on a rig family, family clips, 64x64 palette). Family = 2nd arg of its `H.build(...)` line.
2. Review: `tools/blender/hand_review.sh <id> <family>` -> `artifacts/model-sheets/hand/<id>/` (sheet.png, clips.png, overlay.png, silhouette.txt) + `assets/models-sets/hand/<id>.glb`.
3. Grade: agent `model-reviewer` (gate by gate against the art profile).
4. Install: `/install-into-game <id...>`.
5. Buildings: hand-modelled Blender scripts `tools/blender/buildings_<race>.py` from the design text (`reports/design/`), not the spec pipeline.

## Setup
- `make link CF_GAME=<game>`: symlinks game data/assets (`game/`, `assets/`, `data/*.tsv`) and the ignored output folder. Without it nothing resolves.
- Review renders and runs live in the ignored output folder, never in git.

## Verify
- Model work: `make test` (blender suite) + `make lint` (ruff, C901 <= 10). Nothing else.
- Never `make check` in castle_fight for model work. Never `pkill` castle_fight (other agents run it).

## Rules
- Lessons: `tasks/lessons.md` (add one after any correction).
- Every paper used -> one row in `docs/references.md`, same commit.
