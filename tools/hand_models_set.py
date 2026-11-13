#!/usr/bin/env python3
"""Write the manifest of the hand-built model set (assets/models-sets/hand/manifest.tsv): data/models.tsv with,
for every unit that has artifacts/model-sheets/hand/<id>/model.glb, the clip columns read from that GLB
(idle, walk, attack + attack2 + attack3, death, spell by name). tools/blender/hand_review.sh puts the GLB and
its .rig/.joints in the set; the game opens it with `build/castle_fight --model-scene hand`.

    python3 tools/hand_models_set.py            # rewrite the set's manifest, print what it covers
"""
import json
import pathlib
import shutil
import struct

ROOT = pathlib.Path(__file__).resolve().parents[1]
SET = ROOT / "assets/models-sets/hand"
HAND = ROOT / "artifacts/model-sheets/hand"
CLIP_COLUMNS = {"clip_idle": ("idle",), "clip_walk": ("walk",), "clip_attack": ("attack", "attack2", "attack3"),
                "clip_death": ("death",), "clip_spell": ("spell",)}
SHARED = {"n02L": "e00E"}       # units that use another unit's model (the Twins' second smiling figure)


def clip_names(glb):
    data = glb.read_bytes()
    doc = json.loads(data[20:20 + struct.unpack("<I", data[12:16])[0]])
    return [a.get("name", "") for a in doc.get("animations", [])]


def clip_cells(names):
    """{column: "3" or "0,1"} for the clips the GLB has; a column whose clips are all missing is left out."""
    cells = {}
    for column, wanted in CLIP_COLUMNS.items():
        found = [str(names.index(w)) for w in wanted if w in names]
        if found:
            cells[column] = ",".join(found)
    return cells


def main():
    lines = (ROOT / "data/models.tsv").read_text().splitlines()
    header = lines[0].split("\t")
    out, covered, missing = [lines[0]], [], []
    for line in lines[1:]:
        row = dict(zip(header, line.split("\t")))
        glb = SET / f"{row['unit_id']}.glb"
        source = SHARED.get(row["unit_id"])
        if source and (SET / f"{source}.glb").exists():
            for suffix in (".glb", ".rig", ".joints"):
                shutil.copyfile(SET / f"{source}{suffix}", SET / f"{row['unit_id']}{suffix}")
            (SET / f"{row['unit_id']}.cook").unlink(missing_ok=True)
        if (HAND / (source or row["unit_id"]) / "model.glb").exists() and glb.exists():
            row.update(clip_cells(clip_names(glb)))
            covered.append(row["unit_id"])
        else:
            missing.append(row["unit_id"])
        out.append("\t".join(row[c] for c in header))
    (SET / "manifest.tsv").write_text("\n".join(out) + "\n")
    print(f"hand set: {len(covered)} hand-built, {len(missing)} still the old model: {' '.join(missing)}")


if __name__ == "__main__":
    main()
