#!/usr/bin/env python3
"""Front panel of a concept sheet -> baseline/input/<id>-front.png (read-only on castle_fight).
    PYTHONDONTWRITEBYTECODE=1 python3.14 prep_input.py <id> [...]"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]  # pipeline repo (game files via make link)
sys.path.insert(0, str(ROOT / "tools/blender"))
import split_sheet  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "input"
for unit in sys.argv[1:]:
    panels = split_sheet.split(ROOT / f"artifacts/model-sheets/refs/{unit}/sheet.jpg", OUT, unit, "unit")
    print(unit, panels["front"])
