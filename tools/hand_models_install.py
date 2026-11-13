#!/usr/bin/env python3
"""Point data/models.tsv at the hand-built unit models (artifacts/model-sheets/hand/<id>/model.glb) and drop
their rows from data/anim_refresh.tsv (anim_refresh would refit or re-key skeletons the builder already keyed).

    python3 tools/hand_models_install.py            # dry run: say what would change
    python3 tools/hand_models_install.py --write    # rewrite the two files

Per unit: url, sha256 and the clip columns (read from the GLB by name), license project-own, a credit.
Afterwards: `make assets` (prepares .rig/.joints) and `make cook`. The rig-family changes some units need in
data/unit_anim.tsv are listed in artifacts/model-sheets/hand/_queue/PENDING.md; this tool does not make them.
"""
import hashlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import hand_models_set as S  # noqa: E402

ROOT = S.ROOT
MODELS = ROOT / "data/models.tsv"
REFRESH = ROOT / "data/anim_refresh.tsv"
CREDIT = "modelado à mão (hand_unit)"


def swapped_row(row):
    """The row pointing at its hand model, or None when the unit has none."""
    glb = S.HAND / S.SHARED.get(row["unit_id"], row["unit_id"]) / "model.glb"
    if not glb.exists():
        return None
    new = dict(row, url=str(glb.relative_to(ROOT)), sha256=hashlib.sha256(glb.read_bytes()).hexdigest(),
               license="project-own", credit=CREDIT)
    new.update(S.clip_cells(S.clip_names(glb)))
    return new


def models():
    lines = MODELS.read_text().splitlines()
    header = lines[0].split("\t")
    out, changed, kept = [lines[0]], [], []
    for line in lines[1:]:
        row = dict(zip(header, line.split("\t")))
        new = swapped_row(row)
        (changed if new and new != row else kept if not new else []).append(row["unit_id"])
        out.append("\t".join((new or row)[c] for c in header))
    return "\n".join(out) + "\n", changed, kept, {r.split("\t")[0] for r in out[1:]} - set(kept)


def refresh(swapped):
    lines = REFRESH.read_text().splitlines()
    out = [line for line in lines if line.split("\t")[0] not in swapped]
    return "\n".join(out) + "\n", len(lines) - len(out)


def main():
    text, changed, kept, swapped = models()
    refresh_text, dropped = refresh(swapped)
    print(f"data/models.tsv: {len(changed)} rows change, old model kept for: {' '.join(kept) or '-'}")
    print(f"data/anim_refresh.tsv: {dropped} rows dropped")
    if "--write" in sys.argv[1:]:
        MODELS.write_text(text)
        REFRESH.write_text(refresh_text)
        print("written; next: make assets && make cook")
    else:
        print("dry run; --write to apply")


if __name__ == "__main__":
    main()
