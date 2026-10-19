#!/usr/bin/env python3
"""Compose every reference drawing of one unit into one contact sheet.

    python3 tools/blender/ref_sheet.py artifacts/model-sheets/refs/hfoo/sheet.jpg \
        artifacts/model-sheets/refs/hfoo/refsheet.png

Cells, in reading order: the approved 5-view sheet, the hard-edge sheet with the props
attached, the hard clean sheet (empty-handed A-pose, no props), the detached props, the
approved RTS view and the hard RTS view. Missing files are skipped.

The individual files stay separate on purpose: split_sheet.py, silhouette.py and
spec_pipeline.py read one image at a time, and concept_panels() splits the sheet on its
3+2 empty bands — an RTS view baked into the sheet would be read as a sixth panel.
"""
import pathlib
import subprocess
import sys

LABELS = [
    ("", "approved 5-view"),
    ("-hard", "hard, props in place"),
    ("-hard-clean", "hard, A-pose, no props"),
    ("-props", "props detached"),
    ("-rts", "RTS view"),
    ("-hard-rts", "hard RTS view"),
]


def refsheet(sheet, out, cell=640, columns=3):
    cells = []
    for suffix, label in LABELS:
        path = sheet.with_name(f"{sheet.stem}{suffix}.jpg")
        if path.exists():
            cells += ["-label", label, str(path)]
    if not cells:
        sys.exit(f"no reference images found beside {sheet}")
    font = next((f for f in ("/System/Library/Fonts/Helvetica.ttc",
                             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
                 if pathlib.Path(f).exists()), None)
    cmd = ["magick", "montage", *cells, "-tile", f"{columns}x", "-geometry",
           f"{cell}x{cell}+10+10", "-background", "#cfcfcf", "-fill", "#222222",
           "-pointsize", "20"]
    cmd += ["-font", font] if font else []
    cmd.append(str(out))
    subprocess.run(cmd, check=True)
    print(f"{out}  {len(cells) // 3} cells")
    return out


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    refsheet(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
