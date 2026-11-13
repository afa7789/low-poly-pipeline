#!/usr/bin/env python3
"""Install the unit models into a game checkout: copy each hand-built model
(artifacts/model-sheets/hand/<id>/{model.glb,model.palette.png}) and any GLB a row of the game's data/models.tsv
still takes from the tool's output (artifacts/model-sheets/..., e.g. perk_tower) to <game>/assets/units/<id>/,
point the row at the copy, and drop the hand units from the tool's data/anim_refresh.tsv (anim_refresh would refit
or re-key skeletons the builder already keyed).

    python3 tools/hand_models_install.py --game $CF_GAME             # dry run: say what would change
    python3 tools/hand_models_install.py --game $CF_GAME --write     # copy the files, rewrite the two tables
    python3 tools/hand_models_install.py --game $CF_GAME --write h000 n02K   # only these units

--game defaults to CF_GAME (tools/blender/game_paths.py). Per hand unit: url, sha256 and the clip columns (read
from the GLB by name), license project-own, a credit; an output GLB keeps its other columns. Afterwards, in the
game: `make assets && make cook && make model-clips-check`. The rig-family changes some units need in
data/unit_anim.tsv are listed in artifacts/model-sheets/hand/_queue/PENDING.md; this tool does not make them.
"""
import argparse
import hashlib
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "blender"))
import game_paths  # noqa: E402
import hand_models_set as S  # noqa: E402

SHEETS = "artifacts/model-sheets/"
UNITS = "assets/units"
REFRESH = S.ROOT / "data/anim_refresh.tsv"
CREDIT = "modelado à mão (hand_unit)"


def source(row, game, hand=S.HAND, sheets=S.ROOT / SHEETS):
    """(GLB to install, folder id, is a hand model) for a row, or None when nothing of ours backs it."""
    folder = S.SHARED.get(row["unit_id"], row["unit_id"])
    if (hand / folder / "model.glb").exists():
        return hand / folder / "model.glb", folder, True
    if row["url"].startswith(SHEETS):
        for glb in (sheets / row["url"][len(SHEETS):], game / row["url"]):
            if glb.exists():
                return glb, row["unit_id"], False
    return None


def installed_row(row, game, src):
    """The row pointing at the installed copy, plus {destination: source} of the files it needs."""
    glb, folder, is_hand = src
    dest = game / UNITS / folder
    copies = {dest / "model.glb": glb}
    palette = glb.with_name("model.palette.png")
    if palette.exists():
        copies[dest / "model.palette.png"] = palette
    new = dict(row, url=f"{UNITS}/{folder}/model.glb", sha256=hashlib.sha256(glb.read_bytes()).hexdigest())
    if is_hand:
        new.update(license="project-own", credit=CREDIT)
        new.update(S.clip_cells(S.clip_names(glb)))
    return new, copies


def stale(copies):
    return any(not to.exists() or to.read_bytes() != frm.read_bytes() for to, frm in copies.items())


def plan(game, ids=(), **where):
    """(new models.tsv text, changed ids, ids with no model of ours, hand ids, {destination: source})."""
    lines = (game / "data/models.tsv").read_text().splitlines()
    header = lines[0].split("\t")
    out, changed, kept, hand, copies = [lines[0]], [], [], set(), {}
    for line in lines[1:]:
        row = dict(zip(header, line.split("\t")))
        out.append(line)
        if ids and row["unit_id"] not in ids:
            continue
        src = source(row, game, **where)
        if not src:
            if not row["url"].startswith(UNITS + "/"):      # an installed output GLB is ours already
                kept.append(row["unit_id"])
            continue
        new, files = installed_row(row, game, src)
        copies.update(files)
        if src[2]:
            hand.add(row["unit_id"])
        if new != row or stale(files):
            changed.append(row["unit_id"])
        out[-1] = "\t".join(new[c] for c in header)
    return "\n".join(out) + "\n", changed, kept, hand, copies


def refresh(swapped, path=REFRESH):
    lines = path.read_text().splitlines()
    out = [line for line in lines if line.split("\t")[0] not in swapped]
    return "\n".join(out) + "\n", len(lines) - len(out)


def write(game, text, copies, refresh_text, refresh_path=REFRESH):
    for to, frm in copies.items():
        if stale({to: frm}):
            to.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(frm, to)
    (game / "data/models.tsv").write_text(text)
    refresh_path.write_text(refresh_text)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--game", type=pathlib.Path, help="game checkout (default: CF_GAME)")
    ap.add_argument("--write", action="store_true", help="copy the files and rewrite the tables")
    ap.add_argument("ids", nargs="*", help="only these unit ids")
    args = ap.parse_args(argv)
    game = args.game.resolve() if args.game else game_paths.game()
    text, changed, kept, hand, copies = plan(game, set(args.ids))
    refresh_text, dropped = refresh(hand)
    print(f"{game}/data/models.tsv: {len(changed)} rows change, {len(copies)} files in {UNITS}/, "
          f"no model of ours for: {' '.join(kept) or '-'}")
    print(f"data/anim_refresh.tsv: {dropped} rows dropped")
    if args.write:
        write(game, text, copies, refresh_text)
        print("written; next, in the game: make assets && make cook && make model-clips-check")
    else:
        print("dry run; --write to apply")


if __name__ == "__main__":
    main()
