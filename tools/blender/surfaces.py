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
    return ramp * seams, 0.55 * _bump(v, 0.78, 0.0012)


def _wood(u, v, tx, ty):
    grain = 1.0 + 0.12 * np.sin(u * 40 + 3 * np.sin(v * 6 + tx))
    return (0.45 + 0.65 * v) * grain, 0.0


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
    "scales": (_scales, 0.5), "chitin": (_chitin, 0.2), "wood": (_wood, 1.0),
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


# Painted features: eyes and similar marks are texture, not geometry. Each is a list of
# (u, v, radius) dots in a 0..1 face, the face's front projected into a spare atlas cell.
DECALS = {
    "eyes2": [(0.32, 0.60, 0.11), (0.68, 0.60, 0.11)],
    "eyes8": [(0.38, 0.55, 0.10), (0.62, 0.55, 0.10),              # the big front pair
              (0.22, 0.68, 0.055), (0.78, 0.68, 0.055),
              (0.40, 0.75, 0.05), (0.60, 0.75, 0.05),
              (0.28, 0.42, 0.045), (0.72, 0.42, 0.045)],
}


def decal(kind, colour=None, size=64):
    """(rgb, alpha) of one decal cell: dark eyes with a white glint, or eyes lit in
    `colour` (glowing) with a pale core. Alpha is 0 outside the dots."""
    x = (np.arange(size) + 0.5) / size
    u, v = np.meshgrid(x, x)
    rgb, alpha = np.zeros((size, size, 3)), np.zeros((size, size))
    lit = np.asarray(colour if colour is not None else (0.05, 0.04, 0.04), dtype=float)
    for cu, cv, r in DECALS[kind]:
        d = np.hypot(u - cu, v - cv) / r
        dot = np.clip((1.0 - d) * 6, 0, 1)                         # hard edge, 1 px soft
        glint = np.clip((1.0 - np.hypot(u - cu + 0.3 * r, v - cv - 0.3 * r) / (0.3 * r)) * 4, 0, 1)
        core = glint if colour is None else np.clip(1.0 - d * 1.6, 0, 1)
        shade = lit[None, None] * (1 - core[..., None]) + core[..., None] * (0.9 if colour is None else 1.0)
        rgb = rgb * (1 - dot[..., None]) + shade * dot[..., None]
        alpha = np.maximum(alpha, dot)
    return np.clip(rgb, 0, 1), alpha


def atlas_layout(count):
    """(columns, rows) of slot images in the unit's single atlas."""
    cols = int(np.ceil(np.sqrt(count)))
    return cols, int(np.ceil(count / cols))
