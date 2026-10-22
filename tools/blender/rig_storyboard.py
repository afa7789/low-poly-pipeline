#!/usr/bin/env python3
"""Draw each rig family's motions as storyboard strips: ten frames, side view on top,
the game's 3/4 view below. Joints are dots, bones are lines, coloured by chain.

    python3 tools/blender/rig_storyboard.py <outdir> [family ...] [--gif]
    python3 tools/blender/rig_storyboard.py <outdir> [family ...] --json

Writes <outdir>/<family>/<motion>.svg, with ImageMagick's `magick` on the PATH also
<motion>.png, and with --gif <motion>.gif (the motion playing; slow). --json writes
<outdir>/index.json and <outdir>/<family>.json instead: every strip and clip frame
already projected, for a page that draws and plays them. No Blender needed: the poses go
through rig_poses' forward kinematics, which matches Blender's pose bones, so a frame
drawn here is the keyframe the builder writes.
"""
import json
import math
import pathlib
import shutil
import subprocess
import sys

import rig_families as RF
import rig_motions as M
import rig_poses as P

CELL_W, CELL_H, HEAD = 150, 170, 58
MARGIN = 14
LEFT, RIGHT, MID = "#2f6fd0", "#d0402f", "#4a4a4a"
CHAIN_COLOURS = (("head", "#c98a10"), ("neck", "#c98a10"), ("jaw", "#c98a10"),
                 ("tail", "#2a9d5c"), ("wing", "#8a4fc8"), ("rider", "#e07a1f"),
                 ("abdomen", MID), ("spine", MID), ("pelvis", MID), ("body", MID), ("hull", MID))
# the game camera, as in render_anim.py: from front-left-above, looking at the unit
CAM = (-0.66, -0.66, 0.36)


def _norm(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


_C = _norm(CAM)
_R = _norm(_cross(tuple(-c for c in _C), (0, 0, 1)))
_U = _cross(_R, tuple(-c for c in _C))
VIEWS = {
    # (screen x, screen y up, depth toward the viewer)
    "side": lambda p: (-p[1], p[2], -p[0]),
    "3/4": lambda p: (_dot(p, _R), _dot(p, _U), _dot(p, _C)),
}


def colour(name, rest_head):
    for key, value in CHAIN_COLOURS:
        if key in name:
            return value
    if name.endswith(".L") or rest_head[0] > 0.05:
        return LEFT
    if name.endswith(".R") or rest_head[0] < -0.05:
        return RIGHT
    return MID


def _attach(js, parent, head):
    """The parent's end nearest this bone's head, when the bone does not start on it."""
    if parent is None:
        return None
    ends = js[parent]
    d = [sum((a - b) ** 2 for a, b in zip(end, head)) for end in ends]
    near = ends[d.index(min(d))]
    return near if min(d) > 1e-6 else None


def _bounds(frames, view):
    pts = [VIEWS[view](p) for js in frames for h, t in js.values() for p in (h, t)]
    pts.append((0, 0, 0))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), max(xs), min(ys), max(ys)


def _fit(frames, view, height):
    x0, x1, y0, y1 = _bounds(frames, view)
    scale = min((CELL_W - 2 * MARGIN) / max(x1 - x0, 1e-3), (height - 2 * MARGIN) / max(y1 - y0, 1e-3))
    return scale, (x0 + x1) / 2, y0


def segments(js, view, fit, origin, colours, parents):
    """One figure as drawing primitives, far first: [(x1, y1, x2, y2, colour or None
    for a shoulder/hip connector, opacity)], plus the ground line's y (side view)."""
    scale, cx, y0 = fit
    ox, oy = origin

    def at(p):
        x, y, d = VIEWS[view](p)
        return ox + CELL_W / 2 + (x - cx) * scale, oy - MARGIN - (y - y0) * scale, d

    items = []
    for name, (h, t) in js.items():
        if name == "root":
            continue
        a, b = at(h), at(t)
        items.append(((a[2] + b[2]) / 2, colours[name], a, b))
        joint = _attach(js, parents.get(name), h)
        if joint is not None:        # shoulder / hip: the gap from the parent bone
            j = at(joint)
            items.append(((j[2] + a[2]) / 2, None, j, a))
    items.sort(key=lambda item: item[0])
    near = max((i[0] for i in items), default=0)
    far = min((i[0] for i in items), default=0)
    out = [(a[0], a[1], b[0], b[1], c, 0.4 + 0.6 * ((d - far) / (near - far) if near > far else 1))
           for d, c, a, b in items]
    return out, (at((0, 0, 0))[1] if view == "side" else None)


def _bone_lines(js, view, fit, origin, colours, parents):
    """SVG for one figure: far bones first and faded, near bones on top."""
    segs, ground = segments(js, view, fit, origin, colours, parents)
    out = []
    for x1, y1, x2, y2, c, fade in segs:
        if c is None:
            out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                       f'stroke="#9a9a9a" stroke-width="1.5" opacity="{fade:.2f}"/>')
            continue
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                   f'stroke="{c}" stroke-width="3" stroke-linecap="round" opacity="{fade:.2f}"/>'
                   f'<circle cx="{x2:.1f}" cy="{y2:.1f}" r="2.6" fill="{c}" opacity="{fade:.2f}"/>')
    return out, ground


def _cell(js, view, fit, origin, rest, highlight=False):
    """SVG for one figure in a CELL_W x CELL_H box whose bottom-left is `origin`."""
    x, bottom = origin
    colours, parents = rest
    out = [f'<rect x="{x + 2}" y="{bottom - CELL_H + 2}" width="{CELL_W - 4}" height="{CELL_H - 4}" '
           f'fill="{"#fff1d6" if highlight else "#fffdf8"}" stroke="{"#e08a00" if highlight else "#ddd"}" '
           f'stroke-width="{3 if highlight else 1}" rx="6"/>']
    lines, ground = _bone_lines(js, view, fit, (x, bottom), colours, parents)
    if ground is not None:
        out.append(f'<line x1="{x + 8}" y1="{ground:.1f}" x2="{x + CELL_W - 8}" y2="{ground:.1f}" '
                   f'stroke="#bbb" stroke-dasharray="4 3"/>')
    return out + lines


def _rest(family):
    rest = P.joints(family)
    return {n: colour(n, h) for n, (h, _) in rest.items()}, RF.parents(family)


def strip_svg(family, name, motion):
    frames = [P.joints(family, motion["poses"][i]) for i in range(1, M.FRAMES + 1)]
    rest = _rest(family)
    width = CELL_W * M.FRAMES
    height = HEAD + 2 * CELL_H
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">',
           f'<rect width="{width}" height="{height}" fill="#f4f1ea"/>',
           f'<text x="10" y="22" font-size="17" font-weight="bold" fill="#222">{family} · {name}'
           f' <tspan font-weight="normal" fill="#777">({motion["kind"]})</tspan></text>',
           f'<text x="10" y="44" font-size="13" fill="#444">{motion["note"]}</text>']
    for row, view in enumerate(("side", "3/4")):
        fit = _fit(frames, view, CELL_H)
        top = HEAD + row * CELL_H
        svg.append(f'<text x="{width - 8}" y="{top + 14}" font-size="11" fill="#999" '
                   f'text-anchor="end">{"lado (frente →)" if view == "side" else "3/4 (câmera do jogo)"}</text>')
        for i, js in enumerate(frames):
            hit = motion["impact"] == i + 1
            svg.extend(_cell(js, view, fit, (i * CELL_W, top + CELL_H), rest, hit))
            if row == 0:
                label = f"{i + 1}" + (" · IMPACTO" if hit else "")
                svg.append(f'<text x="{i * CELL_W + 10}" y="{top + 18}" font-size="12" '
                           f'fill="{"#c06000" if hit else "#888"}">{label}</text>')
    svg.append("</svg>")
    return "\n".join(svg)


def gif_frames(family, motion):
    """One SVG per animation frame: side view and 3/4 view next to each other, framed
    on the whole motion so the figure does not jump."""
    frames = [P.joints(family, pose) for pose in motion["clip"]]
    rest = _rest(family)
    fits = {view: _fit(frames, view, CELL_H) for view in ("side", "3/4")}
    out = []
    for js in frames:
        svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{2 * CELL_W}" height="{CELL_H}" '
               f'viewBox="0 0 {2 * CELL_W} {CELL_H}"><rect width="{2 * CELL_W}" height="{CELL_H}" fill="#f4f1ea"/>']
        for col, view in enumerate(("side", "3/4")):
            svg.extend(_cell(js, view, fits[view], (col * CELL_W, CELL_H), rest))
        out.append("\n".join(svg + ["</svg>"]))
    return out


def write_gif(path, svgs, tmp):
    """Write the frames and let ImageMagick assemble a looping GIF (about 16 fps)."""
    tmp.mkdir(parents=True, exist_ok=True)
    names = []
    for i, svg in enumerate(svgs):
        f = tmp / f"f{i:03d}.svg"
        f.write_text(svg)
        names.append(str(f))
    subprocess.run(["magick", "-density", "96", "-delay", "6", "-loop", "0", *names, str(path)], check=True)
    shutil.rmtree(tmp)


PALETTE = [LEFT, RIGHT, MID] + [c for _, c in CHAIN_COLOURS if c not in (LEFT, RIGHT, MID)]


def _frame_data(js, fits, rest):
    """{"side"/"34": [[x1, y1, x2, y2, colour index (-1 connector), opacity %]], "g": ground y}."""
    colours, parents = rest
    out = {}
    for view, key in (("side", "side"), ("3/4", "34")):
        segs, ground = segments(js, view, fits[view], (0, CELL_H), colours, parents)
        out[key] = [[round(x1), round(y1), round(x2), round(y2), -1 if c is None else PALETTE.index(c), round(f * 100)]
                    for x1, y1, x2, y2, c, f in segs]
        if ground is not None:
            out["g"] = round(ground)
    return out


def export(families):
    """Everything the review page draws: per family and motion, the ten strip frames
    and the full-rate clip, already projected into CELL_W x CELL_H cells."""
    data = {"cell": [CELL_W, CELL_H], "palette": PALETTE, "families": {}}
    for family in families:
        rest = _rest(family)
        motions = {}
        for name, motion in M.storyboard(family).items():
            clip = [P.joints(family, pose) for pose in motion["clip"]]
            strip = [P.joints(family, motion["poses"][i]) for i in range(1, M.FRAMES + 1)]
            fits = {view: _fit(clip + strip, view, CELL_H) for view in ("side", "3/4")}
            motions[name] = {"kind": motion["kind"], "note": motion["note"], "impact": motion["impact"],
                             "strip": [_frame_data(js, fits, rest) for js in strip],
                             "clip": [_frame_data(js, fits, rest) for js in clip]}
        data["families"][family] = {"bones": len(RF.bones(family)), "motions": motions}
    return data


def render(outdir, family, gif=False):
    folder = pathlib.Path(outdir) / family
    folder.mkdir(parents=True, exist_ok=True)
    written = []
    for name, motion in M.storyboard(family).items():
        path = folder / f"{name}.svg"
        path.write_text(strip_svg(family, name, motion))
        if shutil.which("magick"):
            subprocess.run(["magick", "-density", "96", str(path), str(path.with_suffix(".png"))], check=True)
            if gif:
                write_gif(path.with_suffix(".gif"), gif_frames(family, motion), folder / f".{name}-frames")
        written.append(path)
    return written


def main():
    args = sys.argv[1:]
    flags = {a for a in args if a.startswith("--")}
    outdir, *families = [a for a in args if not a.startswith("--")]
    families = families or M.FAMILIES
    if "--json" in flags:
        out = pathlib.Path(outdir)
        out.mkdir(parents=True, exist_ok=True)
        index = {"cell": [CELL_W, CELL_H], "palette": PALETTE, "families": {}}
        for family in families:
            data = export([family])["families"][family]
            (out / f"{family}.json").write_text(json.dumps(data, separators=(",", ":")))
            index["families"][family] = {"bones": data["bones"], "motions": len(data["motions"]),
                                         "defaults": M.DEFAULTS.get(family, {})}
        units = {}
        for uid, row in M.unit_rows().items():
            for slot in M.SLOTS:
                units.setdefault(row["rig"], {}).setdefault(row[slot], []).append([uid, slot])
        index["units"] = units
        (out / "index.json").write_text(json.dumps(index, separators=(",", ":")))
        print(out / "index.json")
        return
    for family in families:
        for path in render(outdir, family, gif="--gif" in flags):
            print(path)


if __name__ == "__main__":
    main()
