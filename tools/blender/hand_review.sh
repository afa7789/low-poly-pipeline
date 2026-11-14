#!/usr/bin/env bash
# Build one hand-made unit (tools/blender/units/<id>.py) and write everything a review needs:
#   tools/blender/hand_review.sh <unit_id> <rig family>
# into artifacts/model-sheets/hand/<id>/:
#   model.glb         the unit, rigged, with the family's clips
#   sheet.png         the approved concept on top, the model's five rest views below
#   clips.png         four frames of every clip, side and three-quarter views
#   silhouette.txt    tools/blender/silhouette.py against the approved sheet (IoU per view, parts)
#   overlay.png       its overlays: yellow = match, green = model outside the sheet, red = sheet uncovered
# and installs the model as assets/models-sets/hand/<id>.glb (+ .rig/.joints), the set the game opens
# with `build/castle_fight --model-scene hand`.
set -euo pipefail
ID="${1:?usage: hand_review.sh <unit_id> <rig family>}"
FAMILY="${2:?usage: hand_review.sh <unit_id> <rig family>}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
OUT="artifacts/model-sheets/hand/$ID"
SHEET="artifacts/model-sheets/refs/${SHEET_ID:-$ID}/sheet.jpg"     # SHEET_ID=<other id>: a unit drawn on another unit's sheet
WORK="$OUT/work"
FONT=/System/Library/Fonts/Supplemental/Arial.ttf
[ -f "$SHEET" ] || { echo "no approved sheet: $SHEET" >&2; exit 2; }
rm -rf "$WORK"
mkdir -p "$WORK/sil"

blender -b --factory-startup -P "tools/blender/units/$ID.py" -- "$OUT/model.glb" >"$WORK/build.log" 2>&1 ||
    { grep -E "Error|Traceback|SystemExit|line " "$WORK/build.log" >&2; exit 1; }
grep HAND_UNIT "$WORK/build.log" || { tail -20 "$WORK/build.log" >&2; exit 1; }

CLIPS="$(node -e 'const d=require("fs").readFileSync(process.argv[1]);console.log(JSON.parse(d.subarray(20,20+d.readUInt32LE(12)).toString()).animations.map(a=>a.name).join(","))' "$OUT/model.glb")"
blender -b -P tools/blender/hand_views.py -- "$OUT/model.glb" "$WORK/v" 700 "$CLIPS" 4 >"$WORK/views.log" 2>&1
# the model's front / profile / back at the size of the concept's own panels, then three-quarter and match camera
magick \( "$SHEET" -resize 2100x \) \( "$WORK"/v_{front,side,back}.png +append \) \
    \( "$WORK"/v_{q,game}.png +append -gravity center -background '#bdb7b9' -extent 2100x700 \) -append "$OUT/sheet.png"
ROWS=()
for clip in ${CLIPS//,/ }; do
    magick "$WORK"/v_"$clip"_s_*.png "$WORK"/v_"$clip"_q_*.png +append -font "$FONT" -gravity northwest -pointsize 20 \
        -annotate +8+6 "$clip" "$WORK/row_$clip.png"
    ROWS+=("$WORK/row_$clip.png")
done
magick "${ROWS[@]}" -append -resize 70% "$OUT/clips.png"

python3.14 tools/blender/silhouette.py "$SHEET" "$OUT/model.glb" "$WORK/sil" --shape --rig "$FAMILY" \
    >"$OUT/silhouette.txt" 2>&1 || true            # the strict spill gate fails; the numbers are the result
OVERLAYS=()                                        # a sheet without an rts panel has no rts overlay
for view in front left back top bottom rts; do
    [ -f "$WORK/sil/overlay-$view.png" ] && OVERLAYS+=("$WORK/sil/overlay-$view.png")
done
[ ${#OVERLAYS[@]} -eq 0 ] || magick "${OVERLAYS[@]}" +append "$OUT/overlay.png"
grep -E "^(view|front|left|back|top|bottom|rts) |^parts " "$OUT/silhouette.txt" | cut -c1-58

if [ -d game ]; then   # castle_fight linked (make link): install into its hand model set
  SET="assets/models-sets/hand"
  [ -f "$SET/manifest.tsv" ] || { mkdir -p assets/models-sets; cp -c -R assets/models "$SET"; }
  cp "$OUT/model.glb" "$SET/$ID.glb"
  rm -f "$SET/$ID.cook"
  node game/scripts/fetch_models.mjs --rig-only "$SET/$ID.glb"
fi
echo "review: $OUT/sheet.png $OUT/clips.png $OUT/overlay.png"
