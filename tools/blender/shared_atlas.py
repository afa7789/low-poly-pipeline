"""Race-wide gradient atlas for cel builds (PIPELINE 24.L6-11; Le 2026, gradient texturing).

One SIZE x SIZE image per race: a column is one palette slot (colour + surface), 1 px wide, a vertical
ramp of its tone from dark (bottom, a face looking down) to light (top, a face looking up). A face maps
to its slot's column and to the row of its tone (surfaces.TONE_V), so every unit of the race samples
the same texture instead of its own 256-px-per-slot atlas. The table (JSON, a list of keys) is append
only: a column never moves, so a model built earlier stays valid when a later unit adds columns.
Costs, measured in PIPELINE 24.L6-11: no decal cells (eyes, sheet face) and no ink line; opt-in
(spec_pipeline --atlas shared, build_unit shared=<table.json>).
"""
import json
import pathlib

import numpy as np

import surfaces as SF

SIZE = 64


def key(rgb, surface):
    """'#RRGGBB:surface' of a palette slot (rgb floats 0..1)."""
    return "#%02X%02X%02X:%s" % (*(round(c * 255) for c in rgb[:3]), surface)


def extend(path, keys):
    """The table at `path` (created when missing) with `keys` appended, written back when it grew.
    ValueError when it would pass SIZE columns: the race has outgrown one 64 px image."""
    path = pathlib.Path(path)
    table = json.loads(path.read_text()) if path.exists() else []
    new = [k for k in dict.fromkeys(keys) if k not in table]
    if len(table) + len(new) > SIZE:
        raise ValueError(f"shared atlas {path.name}: {len(table)} + {len(new)} slots > {SIZE} columns")
    if new:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(table + new, indent=1))
    return table + new


def image(table):
    """SIZE x SIZE x 3 floats, row 0 = bottom (v = 0): column i is table[i]'s tone ramp; unused columns are white."""
    px = np.ones((SIZE, SIZE, 3))
    for i, k in enumerate(table):
        colour, surface = k.split(":")
        rgb = [int(colour[j:j + 2], 16) / 255.0 for j in (1, 3, 5)]
        px[:, i] = SF.ramp_column(surface, rgb, SIZE)
    return px
