#!/usr/bin/env bash
# Everything the tool produces (runs, concept sheets, review renders, history, eval, final picks) lives in ONE ignored
# output folder, never in git: $CF_PIPELINE_OUT (default ./output). The code still writes under
# artifacts/model-sheets/<dir> and artifacts/reference, so those paths are symlinks into the output folder.
#   scripts/link_output.sh                      # ./output (created)
#   CF_PIPELINE_OUT=/Volumes/x/pipeline-out scripts/link_output.sh
#   scripts/link_output.sh --from-game <game>   # phase A: link the 13 GB still sitting in the game checkout, copy nothing
set -euo pipefail
cd "$(dirname "$0")/.."
M=artifacts/model-sheets
DIRS="runs refs history hand eval pipeline-final leva6-texture atlas-v2-hard"
if [ "${1:-}" = "--from-game" ]; then
  SRC=$(cd "${2:?game checkout}" && pwd -P)/$M; REF=$(dirname "$SRC")/reference
else
  OUT=${CF_PIPELINE_OUT:-output}; mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd -P)
  for d in $DIRS reference; do mkdir -p "$OUT/$d"; done
  SRC=$OUT; REF=$OUT/reference
fi
link() { [ -e "$1" ] || return 0; if [ -L "$2" ]; then rm "$2"; elif [ -e "$2" ]; then echo "skip $2: real folder"; return 0; fi; mkdir -p "$(dirname "$2")"; ln -s "$1" "$2"; }
for d in $DIRS; do link "$SRC/$d" "$M/$d"; done
link "$REF" artifacts/reference
# paper: reference PDFs and the TRELLIS baseline (30 GB) stay in the paper folder
PAPER=${CF_PAPER:-../IA_gen_paper}
if [ -d "$PAPER" ]; then
  PAPER=$(cd "$PAPER" && pwd -P)
  for d in "$PAPER"/papers/*/; do link "${d%/}" "paper/papers/$(basename "$d")"; done
  for d in gguf trellis.cpp runs input; do link "$PAPER/baseline/$d" "paper/baseline/$d"; done
fi
echo "output links -> $SRC"
