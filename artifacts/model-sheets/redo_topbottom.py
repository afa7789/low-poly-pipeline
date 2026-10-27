#!/usr/bin/env python3
"""Redraw only the top-down / bottom-up panels of a sheet as strict orthographic plans (PIPELINE 20.N4).

    python3 redo_topbottom.py n01X --race Mech --name "Iron Golem" [--sheet sheet-hard.jpg]

Keeps the original in refs/<id>/old/ (never overwritten), asks the edit model for the whole sheet
with orthographic bottom panels (prompts/00-template-topbottom.txt), and pastes only the bottom
row of that answer under the original top row. The result replaces refs/<id>/<sheet>.
"""
import argparse
import pathlib
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent


def empty_rows(img, tol=14):
    """Row indices where the image is the flat background (median colour of the page)."""
    a = np.asarray(img.convert("RGB")).astype(int)
    bg = np.median(a.reshape(-1, 3), axis=0)
    return (np.abs(a - bg).max(axis=2) <= tol).all(axis=1)


def cut_row(old, new):
    """A y inside the empty band between the two rows of both sheets, or None."""
    both = empty_rows(old) & empty_rows(new)
    mid = old.height // 2
    ys = np.where(both[mid - old.height // 6: mid + old.height // 6])[0]
    return None if len(ys) == 0 else int(ys[len(ys) // 2] + mid - old.height // 6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--race", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--sheet", default="sheet.jpg")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    refs = HERE / "refs" / args.id
    sheet = refs / args.sheet
    old_dir = refs / "old"
    old_dir.mkdir(exist_ok=True)
    keep = old_dir / args.sheet
    if not keep.exists():
        shutil.copy2(sheet, keep)
    # the edit model copies the bottom row it is shown: blank it so it has to draw it again
    orig = Image.open(keep).convert("RGB")
    blank = old_dir / f"{pathlib.Path(args.sheet).stem}-tb-in.jpg"
    y0 = cut_row(orig, orig)
    if y0 is None:
        sys.exit("no empty band between the rows of the original sheet")
    masked = orig.copy()
    masked.paste(Image.new("RGB", (orig.width, orig.height - y0), tuple(np.median(np.asarray(orig).reshape(-1, 3), axis=0).astype(int))), (0, y0))
    masked.save(blank, quality=92)
    prompt = (HERE / "prompts/00-template-topbottom.txt").read_text()
    prompt = prompt.format(race=args.race, name=args.name, uid=args.id)
    pdir = HERE / "prompts" / args.id
    pfile = pdir / f"unit-{args.id}-topbottom.txt"
    pfile.write_text(prompt)
    tmp_stem = f"{pathlib.Path(args.sheet).stem}-tb-raw"
    cmd = [sys.executable, str(HERE / "generate.py"), str(pfile), "--image", str(blank),
           "--out", str(old_dir), "--name", tmp_stem] + (["--dry-run"] if args.dry_run else [])
    gen = subprocess.run(cmd, capture_output=True, text=True)
    print(gen.stdout.strip() or gen.stderr.strip())
    raw = old_dir / f"{tmp_stem}.jpg"
    if args.dry_run or gen.returncode or not raw.exists():
        sys.exit(gen.returncode or 0)
    new = Image.open(raw).convert("RGB").resize(orig.size)
    y = cut_row(orig, new)
    if y is None:
        sys.exit(f"no common empty band between rows; raw answer kept at {raw}")
    out = orig.copy()
    out.paste(new.crop((0, y, new.width, new.height)), (0, y))
    out.save(sheet, quality=92)
    print(f"{sheet} <- bottom row of {raw.name} below y={y}; original in {keep}")


if __name__ == "__main__":
    main()
