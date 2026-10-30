"""Race-wide atlas for cel builds (PIPELINE 24.L6-11, 27.T3, 27.T7; Le 2026, gradient texturing).

One SIZE x SIZE image per race (128 x 128). Bottom band: a column is one palette slot (colour + surface), 2 px wide, merged
with any column of the same surface within MERGE_DE; its TONE_ROWS rows are the 3 flat cel tones of surfaces.tone_cell, light /
mid / dark, 4 rows each (the first is the ink row), so a face reads its slot's column and its tone's rows as in the compact
atlas (PIPELINE 27.T1). The side ink columns do not fit 2 px: the ink is the row only. Top band: decal cells (16 px procedural
eyes, 32 px a picture), placed first-fit on a 4 px grid, keyed by a hash of the decal + its slot. The table (JSON,
{"columns": [keys], "decals": {hash: [x, y, w, h]}}; a bare list of keys is an old table) is append only: a column or a decal
cell never moves, so a model built earlier stays valid when a later unit adds to it. Opt-in
(spec_pipeline --atlas shared, build_unit shared=<table.json>). The palette of the race (race_palettes.json, from its icon,
PIPELINE 27.T7) is a snap target for a unit's colours and a soft hint in the colour brief.
"""
import json
import pathlib

import numpy as np

import silhouette as SIL
import surfaces as SF

SIZE = 128
COL = 2                    # px per column: both texels hold the colour, so a mip level down still reads it (Halladay 2016)
COLUMNS = SIZE // COL
TONE_ROWS = 3 * SF.FLAT_ROWS     # the tone band: light / mid / dark flat cells, 4 rows each (an ink row and 3 colour rows)
MERGE_DE = 0.02            # Oklab distance under which two colours of one surface share a column (PIPELINE 27.T2)
SNAP_DE = 0.03             # ... under which a colour snaps to the race palette's (PIPELINE 27.T7)
GRID = 4                   # decal cells sit on a 4 px grid, as surfaces.pack_cells' align
PALETTES = pathlib.Path(__file__).with_name("race_palettes.json")


def key(rgb, surface):
    """'#RRGGBB:surface' of a palette slot (rgb floats 0..1)."""
    return "#%02X%02X%02X:%s" % (*(round(c * 255) for c in rgb[:3]), surface)


def rgb_of(colour):
    """0..1 floats of '#RRGGBB'."""
    return np.array([int(colour[j:j + 2], 16) / 255.0 for j in (1, 3, 5)])


def lab(k):
    """Oklab (L, a, b) of a key's colour (a key or a bare '#RRGGBB')."""
    return SIL.oklab(rgb_of(k.split(":")[0]))


def find(table, k):
    """Index of the column that serves key `k`: the exact key, else the nearest column of the same surface
    within MERGE_DE (Oklab), else None."""
    if k in table:
        return table.index(k)
    surface, here = k.split(":")[1], lab(k)
    near = [(float(np.linalg.norm(lab(t) - here)), i) for i, t in enumerate(table) if t.split(":")[1] == surface]
    best = min(near, default=(MERGE_DE, None))
    return best[1] if best[0] < MERGE_DE else None


def palette_hint(race):
    """['#RRGGBB', ...] fixed palette of a race (from its icon, make_palettes), [] for an unknown race."""
    return json.loads(PALETTES.read_text()).get(race.lower(), [])


def hint_text(race):
    """The colour brief's soft restriction for a race ('' without a palette); the author may ignore it."""
    colours = palette_hint(race)
    return f"Prefer these {race} palette tones when the sheet allows (soft, not a rule): {', '.join(colours)}.\n" if colours else ""


def snap(k, palette, de=SNAP_DE):
    """Key `k` with its colour replaced by the nearest of `palette` when that is within `de` (Oklab), else `k`."""
    if not palette:
        return k
    here = lab(k)
    dist = [float(np.linalg.norm(lab(c) - here)) for c in palette]
    best = int(np.argmin(dist))
    return palette[best].upper() + ":" + k.split(":")[1] if dist[best] < de else k


def snap_new(columns, k, palette, de=SNAP_DE):
    """Key `k` as it enters a table of `columns`: unchanged when a column already serves it (the T2 merge), else snapped to the palette."""
    return k if find(columns, k) is not None else snap(k, palette, de)


def make_palettes(icons, out=PALETTES, n=8, de=0.06):
    """Write {race: [n most frequent icon colours, > `de` apart in Oklab]} for every <race>.png under `icons` (needs PIL)."""
    from PIL import Image
    result = {}
    for png in sorted(pathlib.Path(icons).glob("*.png")):
        px = np.asarray(Image.open(png).convert("RGBA")).reshape(-1, 4)
        px = px[px[:, 3] > 200, :3] // 8 * 8 + 4
        colours, counts = np.unique(px, axis=0, return_counts=True)
        chosen = []
        for c in colours[np.argsort(-counts)]:
            c = "#%02X%02X%02X" % tuple(c)
            if all(np.linalg.norm(lab(c) - lab(o)) > de for o in chosen):
                chosen.append(c)
            if len(chosen) == n:
                break
        result[png.stem] = chosen
    pathlib.Path(out).write_text(json.dumps(result, indent=1))
    return result


def load(path):
    """{"columns": [...], "decals": {...}} of the table at `path` (empty when missing; an old table is a bare list of keys)."""
    path = pathlib.Path(path)
    data = json.loads(path.read_text()) if path.exists() else []
    return {"columns": data, "decals": {}} if isinstance(data, list) else {"columns": data["columns"], "decals": data["decals"]}


def place(decals, size):
    """(x, y) of the first free `size` x `size` spot of the decal band (rows above the tone band, GRID aligned,
    scanned row by row), None when there is none. `decals` is the table's {hash: [x, y, w, h]}."""
    used = {(x + i, y + j) for x, y, w, h in decals.values()
            for i in range(0, w, GRID) for j in range(0, h, GRID)}
    span = range(0, size, GRID)
    for y in range(-(-TONE_ROWS // GRID) * GRID, SIZE - size + 1, GRID):
        for x in range(0, SIZE - size + 1, GRID):
            if not any((x + i, y + j) in used for i in span for j in span):
                return x, y
    return None


def extend(path, keys, decals=()):
    """The table at `path` with the keys that match no column appended and the (hash, size) decals that have no cell placed
    (largest first), written back when it grew. ValueError when it would pass COLUMNS columns or the decal band is full:
    the race has outgrown one 128 px image."""
    path = pathlib.Path(path)
    old = load(path)
    grown = {"columns": list(old["columns"]), "decals": dict(old["decals"])}
    for k in dict.fromkeys(keys):
        if find(grown["columns"], k) is None:
            grown["columns"].append(k)
    if len(grown["columns"]) > COLUMNS:
        raise ValueError(f"shared atlas {path.name}: {len(old['columns'])} + {len(grown['columns']) - len(old['columns'])} slots > {COLUMNS} columns")
    for dkey, size in sorted(dict.fromkeys(decals), key=lambda d: -d[1]):
        if dkey in grown["decals"]:
            continue
        spot = place(grown["decals"], size)
        if spot is None:
            raise ValueError(f"shared atlas {path.name}: no room for a {size} px decal")
        grown["decals"][dkey] = [*spot, size, size]
    if grown != old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(grown, indent=1))
    return grown


def u_of(column):
    """u of a column's centre: the seam between its two texels, which hold the same colour."""
    return (column * COL + COL / 2) / SIZE


def tone_cell_xywh(column, tone):
    """(x, y, w, h) texels of tone `tone` (0 light, 1 mid, 2 dark) of a column."""
    return column * COL, tone * SF.FLAT_ROWS, COL, SF.FLAT_ROWS


def image(table):
    """SIZE x SIZE x 3 floats, row 0 = bottom (v = 0): the tone band (TONE_ROWS rows) holds, for table["columns"][i], columns
    2i, 2i+1 of surfaces.tone_cell at tones 0..2 (side ink columns cut: only the middle 2 of 4 texels are kept); the rest is white."""
    px = np.ones((SIZE, SIZE, 3))
    for i, k in enumerate(table["columns"]):
        colour, surface = k.split(":")
        for tone in range(3):
            x, y, w, h = tone_cell_xywh(i, tone)
            px[y:y + h, x:x + w] = SF.tone_cell(surface, rgb_of(colour), tone, slope=0, width=COL + 2)[:, 1:1 + COL]
    return px
