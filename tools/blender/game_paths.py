"""Where the game checkout and the tool's output folder are.

    CF_GAME           the game checkout (castle_fight). Read: its data tables; write: only the install step.
                      Default: the ./game link that scripts/link_game.sh makes, else a castle_fight folder next
                      to this repo. Neither there -> SystemExit that says what to set.
    CF_PIPELINE_OUT   everything the tool produces (runs, refs, hand, history, eval, ...), never versioned.
                      Default: ./output in this repo (scripts/link_output.sh links artifacts/model-sheets/* into it).
"""
import os
import pathlib

TOOL = pathlib.Path(__file__).resolve().parents[2]


def game():
    """The game checkout, checked by its data/models.tsv."""
    raw = os.environ.get("CF_GAME")
    candidates = [pathlib.Path(raw).expanduser()] if raw else [TOOL / "game", TOOL.parent / "castle_fight"]
    for path in candidates:
        if (path / "data/models.tsv").is_file():
            return path.resolve()
    where = raw or " or ".join(str(p) for p in candidates)
    raise SystemExit(f"CF_GAME: no game checkout at {where} (no data/models.tsv); "
                     "set CF_GAME=/path/to/castle_fight or pass --game")


def out_arg(args, flag, *sub):
    """The folder after `flag` in a script's args, else the game's own folder for what the script writes:
    $CF_GAME/assets/<sub...> (buildings_*, map_*, fx_* write game assets; --out still points them elsewhere)."""
    return args[args.index(flag) + 1] if flag in args else str(game().joinpath("assets", *sub))


def output():
    """The output folder (not created here)."""
    return pathlib.Path(os.environ.get("CF_PIPELINE_OUT") or TOOL / "output").expanduser().resolve()
