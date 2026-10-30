"""Ablation hooks (PIPELINE 29.L11-7): module globals and build_unit arguments set from the environment, so ablation_matrix.py can
run one variant of every opt-in through the unchanged pipeline. Both are empty by default and change nothing.

    CF_OVERRIDES   JSON {"module.NAME": value, "module.DICT.key": value}, applied once by spec_pipeline.main (lists become tuples)
    CF_BUILD_ARGS  extra build_unit.py arguments (e.g. "sdf_thin=keep palette_snap"), appended to every build_unit call"""
import importlib
import json
import os
import shlex


def apply(env=None):
    """Set each CF_OVERRIDES entry; an unknown module or name is an error (a typo must not pass as a variant). Returns the dict applied."""
    todo = json.loads((env or os.environ).get("CF_OVERRIDES") or "{}")
    for key, value in todo.items():
        path = key.split(".")
        owner = importlib.import_module(path[0])
        for name in path[1:-1]:
            owner = owner[name] if isinstance(owner, dict) else getattr(owner, name)
        last = path[-1]
        if isinstance(owner, dict):
            owner[last] = value
        elif hasattr(owner, last):
            setattr(owner, last, tuple(value) if isinstance(value, list) else value)
        else:
            raise SystemExit(f"CF_OVERRIDES: {key} does not exist")
    return todo


def build_args(env=None):
    """The CF_BUILD_ARGS words, to append to a build_unit.py command."""
    return shlex.split((env or os.environ).get("CF_BUILD_ARGS", ""))
