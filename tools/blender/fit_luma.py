#!/usr/bin/env python3
"""Luma of the cel by deferred shading (DIB-R++, Chen et al. 2021; PIPELINE 26.L8-8).

The G-buffer is fixed, so there is no rasterizer to differentiate: render_silhouette.py --ids already
writes, per view, the material of every pixel (flat palette colours) and the world normal of its face.
The shading model is the smallest one that gives the cel a light direction:

    luma(p) = tone[slot(p)] x ((1 - b) + b x max(0, n(p) . L))

with L (azimuth, elevation), b and one tone per palette slot unknown, fitted by scipy `least_squares`
so that the p10/p50/p90 luma of the model pixels of each sheet colour zone equal those of the sheet's
zone (the quantiles silhouette.luma_l1 compares; the model and the sheet are not registered pixel to
pixel, so a distribution is the only honest target). The output per slot is the three cel tone
multipliers (up / side / down, surfaces.CEL_TONES' shape) that reproduce the fitted luma on the pixels
of each tone class, for surfaces.paint_cel(tones=...).
"""
import numpy as np
from scipy.optimize import least_squares

import silhouette as SIL
from surfaces import tone_index

QS = np.array(SIL.LUMA_QS)
MAX_PX = 4000          # model pixels per view in the fit: quantiles of a strided sample are as good
MIN_PX = 20            # fewer pixels than this in the model or in the sheet: the zone says nothing
TONE_LO, TONE_HI = 0.2, 1.6   # a tone multiplier outside this is the fit giving up, not light
STARTS = (0.4, 2.0, -2.0, -0.4)   # azimuths the fit restarts from: the loss is flat in some directions
DEGENERATE_B = 0.05    # b under this: the sheet has no light direction (flat paint), the tones are all that is left


def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def light(az, el):
    return np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])


def shade(b, normals, direction):
    return (1 - b) + b * np.maximum(0.0, normals @ direction)


def shot_path(ids_dir, stem, kind, view, tilt):
    return ids_dir / f"{stem}-{kind}-{view}{f'@{tilt}' if tilt else ''}.png"


def read_gbuffer(ids_dir, stem, view, tilt, slot_rgb):
    """(slot index, world normals) of the object pixels of one view, strided to MAX_PX; None when the
    shots are missing. The slot is the palette colour nearest to the ID shot's pixel."""
    zone, nrm = shot_path(ids_dir, stem, "zone", view, tilt), shot_path(ids_dir, stem, "nrm", view, tilt)
    if not (zone.exists() and nrm.exists()):
        return None
    z, n = SIL.read_rgba(zone, 512), SIL.read_rgba(nrm, 512)
    mask = (z[..., 3] > 16) & (n[..., 3] > 16)
    px = z[mask][:, :3] / 255.0
    normals = 2 * srgb_to_linear(n[mask][:, :3] / 255.0) - 1
    slot = np.argmin(((px[:, None, :] - slot_rgb[None]) ** 2).sum(axis=2), axis=1)
    keep = np.arange(0, len(slot), max(1, len(slot) // MAX_PX))
    norm = np.linalg.norm(normals[keep], axis=1, keepdims=True)
    return slot[keep], normals[keep] / np.maximum(norm, 1e-6)


def sheet_zones(sheet, layout, views):
    """(zone centres, {view: {zone: (luma quantiles, share of the view's figure)}}) of the sheet,
    labelled and masked as silhouette.zone_views does (outline pixels are not a light value)."""
    _, centres, _ = SIL.zone_palette(sheet)
    rgb = SIL.read_rgba(sheet, 768)[..., :3] / 255.0
    panels = SIL.concept_panels(sheet, layout=layout)
    luma, solid = rgb @ SIL.LUMA, rgb.max(axis=-1) > SIL.INK
    out = {}
    for view in views:
        if view not in panels:
            continue
        lab = SIL.zone_labels(rgb, panels[view], centres, ink=True)
        total = max(int((solid & (lab > 0)).sum()), 1)
        zones = {}
        for z in range(1, len(centres) + 1):
            px = luma[(lab == z) & solid]
            if len(px) >= MIN_PX:
                zones[z] = (np.quantile(px, QS), len(px) / total)
        out[view] = zones
    return centres, out


def residuals(x, gbuf, targets, zone_of):
    """Weighted p10/p50/p90 gaps between the fitted model's zones and the sheet's, all views."""
    direction, b, tone = light(x[0], x[1]), x[2], x[3:]
    out = []
    for view, (slot, normals) in gbuf.items():
        pred = tone[slot] * shade(b, normals, direction)
        for z, (q, share) in targets[view].items():
            hit = zone_of[slot] == z
            gap = np.quantile(pred[hit], QS) - q if hit.sum() >= MIN_PX else np.zeros(3)
            out.append(share * gap)
    return np.concatenate(out) if out else np.zeros(1)


def solve(gbuf, targets, zone_of, tone0):
    """Best (x, cost) over the STARTS: x = [azimuth, elevation, b, tone per slot]."""
    lo = np.r_[-np.pi, 0.0, 0.0, np.full(len(tone0), 0.02)]
    hi = np.r_[np.pi, np.pi / 2, 1.0, np.full(len(tone0), 1.5)]
    best = None
    for az in STARTS:
        x0 = np.r_[az, 0.9, 0.5, tone0]
        fit = least_squares(residuals, x0, bounds=(lo, hi), args=(gbuf, targets, zone_of),
                            loss="soft_l1", f_scale=0.02, diff_step=0.01)
        if best is None or fit.cost < best.cost:
            best = fit
    return best


def class_tones(x, gbuf, slot_luma):
    """{slot: [up, side, down]} cel multipliers: the fitted luma averaged over the pixels of each
    tone class (surfaces.tone_index), over the slot's own colour luma. A class no pixel of the slot
    falls in takes the analytic value (up = +z, down = -z, side = mean over the horizon)."""
    direction, b, tone = light(x[0], x[1]), x[2], x[3:]
    sums, counts = np.zeros((len(tone), 3)), np.zeros((len(tone), 3))
    for slot, normals in gbuf.values():
        cls = np.array([tone_index(nz) for nz in normals[:, 2]])
        pred = tone[slot] * shade(b, normals, direction)
        np.add.at(sums, (slot, cls), pred)
        np.add.at(counts, (slot, cls), 1)
    ring = np.array([[np.cos(a), np.sin(a), 0.0] for a in np.linspace(0, 2 * np.pi, 8, endpoint=False)])
    analytic = np.array([shade(b, np.array([[0, 0, 1.0]]), direction)[0],
                         shade(b, ring, direction).mean(),
                         shade(b, np.array([[0, 0, -1.0]]), direction)[0]])
    mean = np.where(counts > 0, sums / np.maximum(counts, 1), tone[:, None] * analytic[None])
    return np.clip(mean / np.maximum(slot_luma, 1e-3)[:, None], TONE_LO, TONE_HI)


def refine(k0, gbuf, targets, zone_of, slot_rgb):
    """The class tones `k0` ((slots, 3)) nudged to the loss the render is measured by: each pixel is its
    slot's luma x the tone of its class, the colour clipped at white. Same
    quantile targets as solve(); the shading model only seeded it."""
    lum, cap = slot_rgb @ SIL.LUMA, 1 / np.maximum(slot_rgb.max(axis=1), 1e-3)
    cls = {v: np.array([tone_index(nz) for nz in g[1][:, 2]]) for v, g in gbuf.items()}

    def gaps(k):
        out = []
        for view, (slot, _) in gbuf.items():
            pred = lum[slot] * np.minimum(k.reshape(-1, 3)[slot, cls[view]], cap[slot])
            for z, (q, share) in targets[view].items():
                hit = zone_of[slot] == z
                out.append(share * (np.quantile(pred[hit], QS) - q if hit.sum() >= MIN_PX else np.zeros(3)))
        return np.concatenate(out)

    fit = least_squares(gaps, k0.ravel(), bounds=(TONE_LO, TONE_HI), loss="soft_l1", f_scale=0.02, diff_step=0.02)
    return fit.x.reshape(-1, 3)


def fit(ids_dir, stem, sheet, layout, palette, tilts, refine_tones=True, views=("front", "left", "back", "top", "bottom")):
    """Fit the cel luma of `palette` ({slot: {"color": "#RRGGBB", "surface": ...}}) to the sheet from the
    ID + normal shots in `ids_dir`. Returns None when nothing could be fitted, else
      tones    {slot: [up, side, down]}   (no glow slot: it has no shading)
      light    [azimuth, elevation] in degrees, b   the fitted shading
      cost0, cost   the L1-ish loss before and after
      degenerate    True when b is under DEGENERATE_B: no light direction in the sheet"""
    names = list(palette)
    slot_rgb = np.array([[int(palette[n]["color"][i:i + 2], 16) for i in (1, 3, 5)] for n in names]) / 255.0
    slot_luma = slot_rgb @ SIL.LUMA
    centres, sheet_z = sheet_zones(sheet, layout, views)
    zone_of = SIL.nearest(slot_rgb, centres)
    gbuf = {v: g for v in views if (g := read_gbuffer(ids_dir, stem, v, tilts.get(v), slot_rgb)) is not None}
    targets = {v: sheet_z[v] for v in gbuf if sheet_z.get(v)}
    gbuf = {v: gbuf[v] for v in targets}
    if not targets:
        return None
    tone0 = np.array([np.median([q[1] for t in targets.values() for z, (q, _) in t.items() if z == zone_of[i]]
                                or [slot_luma[i]]) / 0.7 for i in range(len(names))])
    best = solve(gbuf, targets, zone_of, tone0)
    x = best.x
    k = class_tones(x, gbuf, slot_luma)
    if refine_tones:
        k = refine(k, gbuf, targets, zone_of, slot_rgb)
    cost0 = float(np.abs(residuals(np.r_[0.4, 0.9, 0.5, tone0], gbuf, targets, zone_of)).sum())
    return {"tones": {n: [round(float(v), 3) for v in k[i]] for i, n in enumerate(names)
                      if palette[n].get("surface") != "glow"},
            "light": [round(float(np.degrees(x[0])), 1), round(float(np.degrees(x[1])), 1)], "b": round(float(x[2]), 3),
            "cost0": round(cost0, 4), "cost": round(float(np.abs(residuals(x, gbuf, targets, zone_of)).sum()), 4),
            "degenerate": bool(x[2] < DEGENERATE_B)}
