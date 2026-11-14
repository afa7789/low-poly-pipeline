#!/bin/zsh
# usage: gen.sh <id> [weights=q4] ; TRELLIS raw GLB at res 512, seed 42, peak RAM by /usr/bin/time -l
B=$(cd "$(dirname "$0")/.." && pwd); U=$1; W=${2:-q4}
mkdir -p $B/runs/$U
/usr/bin/time -l $B/trellis.cpp/build/trellis-cli $B/input/clean/$U.png $B/runs/$U/raw.glb --models $B/gguf/$W --res 512 --seed 42 --require-gpu --dump-bg --verbose > $B/runs/$U/gen.log 2>&1
echo "gen $U rc=$?"
