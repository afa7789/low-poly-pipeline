"""Race-wide gradient atlas for cel builds (PIPELINE 24.L6-11; Le 2026, gradient texturing).

One SIZE x SIZE image per race: a column is one palette slot (colour + surface), 2 px wide, merged with any column of the same surface within MERGE_DE, a vertical
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

import silhouette as SIL
import surfaces as SF

SIZE = 64
COL = 2                    # px per column: both texels hold the colour, so a mip level down still reads it (Halladay 2016)
COLUMNS = SIZE // COL
MERGE_DE = 0.02            # Oklab distance under which two colours of one surface share a column (PIPELINE 27.T2)


def key(rgb, surface):
    """'#RRGGBB:surface' of a palette slot (rgb floats 0..1)."""
    return "#%02X%02X%02X:%s" % (*(round(c * 255) for c in rgb[:3]), surface)


def lab(k):
    """Oklab (L, a, b) of a key's colour."""
    colour = k.split(":")[0]
    return SIL.oklab(np.array([int(colour[j:j + 2], 16) / 255.0 for j in (1, 3, 5)]))


def find(table, k):
    """Index of the column that serves key `k`: the exact key, else the nearest column of the same surface
    within MERGE_DE (Oklab), else None."""
    if k in table:
        return table.index(k)
    surface, here = k.split(":")[1], lab(k)
    near = [(float(np.linalg.norm(lab(t) - here)), i) for i, t in enumerate(table) if t.split(":")[1] == surface]
    best = min(near, default=(MERGE_DE, None))
    return best[1] if best[0] < MERGE_DE else None


def extend(path, keys):
    """The table at `path` (created when missing) with the keys that match no column appended, written
    back when it grew. ValueError when it would pass COLUMNS columns: the race has outgrown one 64 px image."""
    path = pathlib.Path(path)
    table = json.loads(path.read_text()) if path.exists() else []
    grown = list(table)
    for k in dict.fromkeys(keys):
        if find(grown, k) is None:
            grown.append(k)
    if len(grown) > COLUMNS:
        raise ValueError(f"shared atlas {path.name}: {len(table)} + {len(grown) - len(table)} slots > {COLUMNS} columns")
    if len(grown) > len(table):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(grown, indent=1))
    return grown


def u_of(column):
    """u of a column's centre: the seam between its two texels, which hold the same colour."""
    return (column * COL + COL / 2) / SIZE


def image(table):
    """SIZE x SIZE x 3 floats, row 0 = bottom (v = 0): columns 2i, 2i+1 are table[i]'s tone ramp; unused columns are white."""
    px = np.ones((SIZE, SIZE, 3))
    for i, k in enumerate(table):
        colour, surface = k.split(":")
        rgb = [int(colour[j:j + 2], 16) / 255.0 for j in (1, 3, 5)]
        px[:, i * COL:(i + 1) * COL] = SF.ramp_column(surface, rgb, SIZE)[:, None]
    return px
