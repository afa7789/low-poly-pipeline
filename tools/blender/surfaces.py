"""Procedural painted surfaces for unit textures: what the WC3 artists painted by hand.

Our engine draws albedo only - no roughness, no specular, no normal maps - so every
surface reads through two painted things: its pattern (plates, weave, scales, grain)
and its gloss, a highlight band painted into the texture (narrow and hard on silk,
plastic, chitin and polished brass; broad and faint on skin; absent on cloth).

    paint(surface, rgb, size=256) -> float array (size, size, 3), values in rgb's space

A slot image is a 4x4 grid of cells, one per body slot (texturize() maps each face into
the cell of its bone), so every cell gets the same pattern with a small per-cell phase.
"metal" is the original painter, kept formula for formula: the approved n01X look.
"""
import numpy as np

GRID = 4


def _cells(size):
    """u, v in 0..1 inside each cell, and the cell's column/row index (tx, ty).
    Arrays are indexed [y, x]; row 0 is the bottom of the image, as Blender stores it."""
    cell = size // GRID
    x = np.arange(size)
    tx, ty = np.meshgrid(x // cell, x // cell)
    u, v = np.meshgrid((x % cell) / (cell - 1.0), (x % cell) / (cell - 1.0))
    return u, v, tx.astype(float), ty.astype(float)


def _bump(x, centre, width):
    return np.exp(-((x - centre) ** 2) / width)


def _metal(u, v, tx, ty):
    # WC3 read: one key light from above, 4:1 from shadow to highlight, a narrow
    # bright band as the trim, a dark crease low on the tile.
    ramp = 0.30 + 0.85 * (v ** 1.1)
    trim = np.where((v > 0.62) & (v < 0.70), 1.35, 1.0)
    crease = 1.0 - 0.30 * _bump(v, 0.22, 0.0022)
    mottle = 1.0 + 0.07 * np.sin(u * 17 + tx) * np.sin(v * 9 + ty)
    return ramp * trim * crease * mottle, 0.0


def _polished(u, v, tx, ty):
    k, _ = _metal(u, v, tx, ty)
    return k, 0.35 * _bump(v, 0.78, 0.0018)


def _skin(u, v, tx, ty):
    ramp = 0.58 + 0.52 * v ** 0.9
    blotch = 1.0 + 0.05 * np.sin(u * 7 + ty) * np.sin(v * 5 + tx) + 0.02 * np.sin(u * 23 + v * 19)
    return ramp * blotch, 0.08 * _bump(v, 0.82, 0.02)


def _leather(u, v, tx, ty):
    ramp = 0.40 + 0.75 * v
    edge = np.minimum.reduce([u, 1 - u, v, 1 - v])
    rim = 1.0 - 0.35 * np.clip(1 - edge / 0.12, 0, 1)
    crease = (1.0 - 0.15 * _bump(v, 0.35, 0.003)) * (1.0 - 0.12 * _bump(v, 0.62, 0.002))
    worn = 0.10 * np.clip(np.sin(u * 11 + 2 * tx) * np.sin(v * 13 + ty), 0, 1) ** 4
    return ramp * rim * crease, worn


def _cloth(u, v, tx, ty):
    ramp = 0.45 + 0.65 * v
    folds = 1.0 + 0.18 * np.sin(u * 2 * np.pi * 2.5 + tx)
    weave = 1.0 + 0.04 * np.sign(np.sin(u * 120) * np.sin(v * 120))
    return ramp * folds * weave, 0.0


def _silk(u, v, tx, ty):
    ramp = 0.40 + 0.70 * v
    folds = 1.0 + 0.10 * np.sin(u * 2 * np.pi * 1.5 + tx)
    sheen = 0.45 * _bump(v, 0.62 + 0.08 * np.sin(u * 6 + ty), 0.004)
    return ramp * folds, sheen


def _scales(u, v, tx, ty):
    sv = v * 8
    su = u * 6 + 0.5 * (np.floor(sv) % 2)
    fu, fv = su % 1.0, sv % 1.0
    scale = (0.65 + 0.45 * fv) * (1.0 - 0.25 * np.abs(fu - 0.5) * 2)
    return (0.50 + 0.60 * v) * scale, 0.12 * _bump(fv, 0.85, 0.005)


def _chitin(u, v, tx, ty):
    ramp = 0.30 + 0.80 * v ** 1.3
    seams = 1.0 - 0.35 * _bump((v * 4) % 1.0, 0.02, 0.0008)
    mottle = 1.0 + 0.06 * np.sin(u * 13 + tx) * np.sin(v * 7 + ty)
    return ramp * seams * mottle, 0.10 * _bump(v, 0.78, 0.02)      # a creature's matte shell, not armour


def _wood(u, v, tx, ty):
    # worked timber: three vertical boards, a dark joint between them, grain lines
    # that wander along each board and a slightly different tone per board
    board = np.floor(u * 3)
    bu = (u * 3) % 1.0
    grain = 1.0 + 0.14 * np.sin(bu * 34 + 5 * np.sin(v * 3 + board * 2.1 + tx))
    joint = 1.0 - 0.45 * np.clip(1 - np.minimum(bu, 1 - bu) / 0.04, 0, 1)
    tone = 0.92 + 0.08 * np.sin(board * 2.7 + ty)
    return (0.45 + 0.65 * v) * grain * joint * tone, 0.0


def _bark(u, v, tx, ty):
    # living bark: deep vertical furrows that drift sideways, one dark knot per tile
    ridge = (0.5 + 0.5 * np.sin(u * 2 * np.pi * 5 + 1.6 * np.sin(v * 3.1 + tx))) ** 2
    furrow = 1.0 - 0.40 * (1 - ridge)
    ku, kv = 0.25 + 0.5 * ((tx * 0.37 + ty * 0.61) % 1.0), 0.30 + 0.4 * ((tx * 0.73 + ty * 0.29) % 1.0)
    knot = 1.0 - 0.45 * _bump(np.hypot((u - ku) * 1.6, v - kv), 0.0, 0.006)
    return (0.40 + 0.60 * v) * furrow * knot, 0.0


def _slime(u, v, tx, ty):
    # wet ooze: soft body, vertical drip streaks, a broad wet highlight broken by the streaks
    streak = 1.0 + 0.10 * np.sin(u * 15 + 3 * np.sin(v * 2 + tx))
    ramp = 0.60 + 0.50 * v
    sheen = (0.55 * _bump(v, 0.78, 0.006) + 0.35 * _bump(np.hypot(u - 0.3, v - 0.7), 0.0, 0.004))
    return ramp * streak, sheen * (0.7 + 0.3 * np.sin(u * 9 + ty))


def _flesh(u, v, tx, ty):
    # raw wet meat: blotchy, dark veins wandering across, a faint moist sheen
    vein = 1.0 - 0.22 * np.exp(-np.sin(u * 11 + 2.5 * np.sin(v * 6 + tx)) ** 2 / 0.02)
    blotch = 1.0 + 0.08 * np.sin(u * 5 + ty) * np.sin(v * 4 + tx)
    return (0.50 + 0.55 * v) * vein * blotch, 0.25 * _bump(v, 0.80, 0.008)


def _stone(u, v, tx, ty):
    blotch = 1.0 + 0.10 * np.sin(u * 9 + v * 4 + tx) * np.sin(v * 11 - u * 3 + ty)
    crack = 1.0 - 0.35 * _bump(u, 0.3 + 0.1 * np.sin(v * 8 + ty), 0.0006)
    return (0.45 + 0.65 * v) * blotch * crack, 0.0


def _fur(u, v, tx, ty):
    strands = 1.0 + 0.12 * np.sin(u * 55 + 0.6 * np.sin(v * 7 + tx)) * (0.6 + 0.4 * np.sin(u * 13 + ty))
    tips = 1.0 + 0.10 * v ** 3
    return (0.45 + 0.60 * v) * strands * tips, 0.0


def _plastic(u, v, tx, ty):
    return 0.55 + 0.50 * v, 0.60 * np.exp(-((v - 0.80) ** 2 + (u - 0.30) ** 2) / 0.003)


def _glass(u, v, tx, ty):
    # see-through slots (palette "alpha" < 1): a clear body and one hard reflection
    return 0.60 + 0.40 * v, 0.70 * _bump(v, 0.75, 0.0015) + 0.25 * _bump(u, 0.25, 0.002)


def _glow(u, v, tx, ty):
    return 0.90 + 0.25 * _bump(np.hypot(u - 0.5, v - 0.5), 0.0, 0.08), 0.0


# surface -> (painter, how much the highlight takes the base colour: 1 = tinted, 0 = white)
PAINTERS = {
    "metal": (_metal, 1.0), "polished": (_polished, 0.6), "skin": (_skin, 0.7),
    "leather": (_leather, 0.6), "cloth": (_cloth, 1.0), "silk": (_silk, 0.3),
    "scales": (_scales, 0.5), "chitin": (_chitin, 0.3), "wood": (_wood, 1.0),
    "bark": (_bark, 1.0), "slime": (_slime, 0.5), "flesh": (_flesh, 0.5),
    "stone": (_stone, 1.0), "fur": (_fur, 1.0), "plastic": (_plastic, 0.0),
    "glass": (_glass, 0.0), "glow": (_glow, 1.0),
}
SURFACES = tuple(PAINTERS)


def paint(surface, rgb, size=256):
    """One slot image: rgb times the painted light, plus the painted gloss."""
    painter, tint = PAINTERS[surface]
    u, v, tx, ty = _cells(size)
    k, gloss = painter(u, v, tx, ty)
    base = np.asarray(rgb[:3], dtype=float)
    highlight = tint * base + (1 - tint) * np.ones(3)
    out = base * np.asarray(k)[..., None] + np.asarray(gloss)[..., None] * highlight
    return np.clip(out, 0.0, 1.0)


# Cel style: the hard sheet's flat facets. One flat tone per face by orientation (light up,
# mid on the sides, dark underneath), no pattern, no gloss: a slot image is three flat
# tone cells (index = tone_index) and every face maps into the cell of its tone.
# A surface only nudges the three multipliers (default CEL_TONES).
CEL_TONES = (1.08, 1.0, 0.90)   # measured on the 7 v2-hard-r2 renders: render luma / sheet luma 0.95 side, 1.0 top (PIPELINE §18.F)
CEL_SURFACE = {"glow": (1.0, 1.0, 1.0), "slime": (1.30, 1.0, 0.78), "flesh": (1.25, 1.0, 0.72),
               "bark": (1.12, 0.95, 0.60)}


def tone_index(nz):
    """Cel tone cell of a face whose unit normal has vertical component nz: 0 up, 1 side, 2 down."""
    return 0 if nz > 0.55 else (2 if nz < -0.35 else 1)


INK = 0.55   # tone of the ink line at the border of every cel slot (a face spans its whole slot)
RAMP_SLOTS = 8     # a cel cell is RAMP_SLOTS horizontal slots, a dark-to-light ramp bottom to top
RAMP_SLOPE = 0.0   # tone change across the whole ramp, share of the cell's tone. 0 = flat cells: measured, a ramp lowers
                   # the colour-zone mean on n01X front (.41 -> .30) and n005 bottom (.49 -> .37) (PIPELINE 19.C1); build_unit ramp=0.5 turns it on; re-measured on the unioned shell: still negative (PIPELINE 24.L6-11)
TONE_V = (1.0, 0.5, 0.0)   # ramp v of a box's top / side / bottom face (height 1 / .5 / 0): its tone stays exact
SLOT_PAD = 0.1   # a face spans 80 % of its slot: the ink row (1 texel of 8) covers ~3 % of it, as before


def ramp_slot(nz, height, chamfer=False):
    """Ramp slot (0 = dark, bottom) of a cel face (Le 2026: gradient texturing). v is 0.6 x the
    normal's lightness + 0.4 x the face's relative height in its part; a chamfer face (three
    normal components over 0.3) takes the top of the ramp: the bevel catches the light."""
    v = 1.0 if chamfer else 0.6 * (0.5 + 0.5 * nz) + 0.4 * height
    return max(0, min(RAMP_SLOTS - 1, int(v * RAMP_SLOTS)))


def slot_v(slot, t):
    """Cell-local v of position t (0..1) across a face that sits in ramp slot `slot`."""
    return (slot + SLOT_PAD + (1 - 2 * SLOT_PAD) * t) / RAMP_SLOTS


RAMP_MAX = 0.6    # a measured ramp wider than this share of the tone is the sheet's lighting, not its paint


def ramp_slope(ramp, rgb):
    """Slope (paint_cel) of a palette slot's measured ramp (p10, p90 of the sheet zone's luma):
    its width as a share of the slot colour's luma, 0 .. RAMP_MAX."""
    luma = float(np.dot(np.asarray(rgb[:3], dtype=float), (0.299, 0.587, 0.114)))
    return max(0.0, min(RAMP_MAX, (ramp[1] - ramp[0]) / max(luma, 1e-3)))


def paint_cel(surface, rgb, size=256, slope=RAMP_SLOPE):
    """One slot image in cel style: cells 0..2 hold the light/mid/dark tone, the others the
    mid tone (the decal cells are painted over by the caller). Each cell is a vertical ramp of
    RAMP_SLOTS flat slots, darker at the bottom, and a face fills one whole slot (its colour
    is flat). The border of each slot (1-2 px) is darker: faces span their slot, so it reads
    as WC3's ink line. A glow surface has no ramp and no line."""
    tones = CEL_SURFACE.get(surface, CEL_TONES)
    u, v, tx, ty = _cells(size)
    cell = (ty * GRID + tx).astype(int)
    k = np.array(tones + (tones[1],) * (GRID * GRID - 3))[cell]
    if surface != "glow":
        px = size // GRID
        slot_px = px // RAMP_SLOTS
        pos = np.arange(size) % px
        level = ((pos // slot_px) + 0.5) / RAMP_SLOTS
        centre = np.array(TONE_V + (0.5,) * (GRID * GRID - 3))[cell]
        k = k * (1 + slope * (level[:, None] - centre))
        edge, edge_v = max(1, px // 32), max(1, slot_px // 8)
        on_u = (pos < edge) | (pos >= px - edge)
        on_v = (pos % slot_px < edge_v) | (pos % slot_px >= slot_px - edge_v)
        k = k * np.where(on_u[None, :] | on_v[:, None], INK, 1.0)
    return np.clip(np.asarray(rgb[:3], dtype=float) * k[..., None], 0.0, 1.0)


def ramp_column(surface, rgb, size):
    """(size, 3) tone ramp of one slot for the shared atlas (shared_atlas.py): row v is the colour times the
    surface's tone at v, interpolated between its dark / mid / light multipliers at TONE_V 0 / .5 / 1, so a
    face at TONE_V[tone_index] samples exactly the flat cel tone. A glow slot is flat."""
    tones = CEL_SURFACE.get(surface, CEL_TONES)
    v = np.arange(size) / (size - 1.0)          # row r is v = r / (size - 1): uv = (v * (size - 1) + .5) / size
    k = np.interp(v, (0.0, 0.5, 1.0), (tones[2], tones[1], tones[0]))
    return np.clip(np.asarray(rgb[:3], dtype=float)[None, :] * k[:, None], 0.0, 1.0)


# Painted features: eyes and similar marks are texture, not geometry. Each is a list of
# (u, v, radius[, mode]) dots in a 0..1 face, the face's front projected into a spare atlas
# cell. mode "eye" (default) is a dark eye with a glint, or lit in the decal colour; "dark"
# is a flat dark fill (mouth, mask); "lit" is an eye that always glows (pale if no colour).
DECALS = {
    "eyes2": [(0.32, 0.60, 0.11), (0.68, 0.60, 0.11)],
    "eyes8": [(0.38, 0.55, 0.10), (0.62, 0.55, 0.10),              # the big front pair
              (0.22, 0.68, 0.055), (0.78, 0.68, 0.055),
              (0.40, 0.75, 0.05), (0.60, 0.75, 0.05),
              (0.28, 0.42, 0.045), (0.72, 0.42, 0.045)],
    # simple face: two eyes over a three-dot mouth
    "face": [(0.32, 0.64, 0.09), (0.68, 0.64, 0.09),
             (0.36, 0.30, 0.05, "dark"), (0.50, 0.27, 0.05, "dark"), (0.64, 0.30, 0.05, "dark")],
    # hood shadow: a dark mask with two glowing eyes (hooded figures)
    "mask": [(0.50, 0.50, 0.46, "dark"), (0.33, 0.56, 0.085, "lit"), (0.67, 0.56, 0.085, "lit")],
    # the approved sheet's own head, cut out and projected (build_unit.py face=<png>); no dots here
    "sheet": [],
}
DARK = (0.05, 0.04, 0.04)
PALE = (0.95, 0.85, 0.45)


def decal(kind, colour=None, size=64):
    """(rgb, alpha) of one decal cell: dark eyes with a white glint, or eyes lit in
    `colour` (glowing) with a pale core. Alpha is 0 outside the dots."""
    x = (np.arange(size) + 0.5) / size
    u, v = np.meshgrid(x, x)
    rgb, alpha = np.zeros((size, size, 3)), np.zeros((size, size))
    for cu, cv, r, *mode in DECALS[kind]:
        mode = mode[0] if mode else "eye"
        d = np.hypot(u - cu, v - cv) / r
        dot = np.clip((1.0 - d) * 6, 0, 1)                         # hard edge, 1 px soft
        glow = mode == "lit" or (mode == "eye" and colour is not None)
        lit = np.asarray(DARK if mode == "dark" else colour if colour is not None else PALE, dtype=float)
        glint = np.clip((1.0 - np.hypot(u - cu + 0.3 * r, v - cv - 0.3 * r) / (0.3 * r)) * 4, 0, 1)
        core = np.clip(1.0 - d * 1.6, 0, 1) if glow else glint * (mode == "eye")
        shade = lit[None, None] * (1 - core[..., None]) + core[..., None] * (1.0 if glow else 0.9)
        rgb = rgb * (1 - dot[..., None]) + shade * dot[..., None]
        alpha = np.maximum(alpha, dot)
    return np.clip(rgb, 0, 1), alpha


def atlas_layout(count):
    """(columns, rows) of slot images in the unit's single atlas."""
    cols = int(np.ceil(np.sqrt(count)))
    return cols, int(np.ceil(count / cols))
