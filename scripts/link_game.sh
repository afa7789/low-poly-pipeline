#!/usr/bin/env bash
# Phase-A shim: the tool's code still resolves game files as <repo>/data/..., <repo>/assets/... (ROOT = parents[2]).
# Until tools/blender/game_paths.py reads CF_GAME everywhere, symlink exactly the game files the tool reads.
# NOTE: through these links, install-type scripts (hand_models_install, buildings_*/map_*/fx_* --out default, anim_refresh)
# WRITE into the game checkout. That is the intended install direction, so only run them on purpose.
#   CF_GAME=/path/to/castle_fight scripts/link_game.sh
set -euo pipefail
cd "$(dirname "$0")/.."
GAME=$(cd "${CF_GAME:?set CF_GAME to the game checkout}" && pwd -P)
link() { [ -e "$1" ] || return 0; if [ -L "$2" ]; then rm "$2"; elif [ -e "$2" ]; then return 0; fi; mkdir -p "$(dirname "$2")"; ln -s "$1" "$2"; }
link "$GAME" game
for f in compendium.json models.tsv unit_anim.tsv unit_av_ideas.json building_models.tsv scenery_models.tsv; do link "$GAME/data/$f" "data/$f"; done
link "$GAME/assets" assets
link "$GAME/reports/design" reports/design   # art bible + race redesigns (unit_facts.py): the game's art profile
link "$GAME/tools/glb_import_check.cpp" tools/glb_import_check.cpp
link "$GAME/tools/assign_model_clips.py" tools/assign_model_clips.py   # inject_clips/rig_static: AMC.rows
echo "game links -> $GAME"
