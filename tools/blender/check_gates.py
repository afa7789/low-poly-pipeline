#!/usr/bin/env python3
"""Gate table for every built unit GLB in a folder.

    python3 tools/blender/check_gates.py artifacts/model-sheets/draft4/glb
    python3 tools/blender/check_gates.py <dir> --kind mass     # 400-700 tris
    python3 tools/blender/check_gates.py <dir> --kind building # 600-800 tris

Gates (PIPELINE.md §6): triangle budget for the asset kind, 3-8 palette materials, one skin,
5-7 animation clips (preflight.CLIPS; 0 with --static), and the obvious mesh_lint gates
(flipped faces, UV range, one atlas, feet on the ground, root scale; texture gates skipped for
clay.glb). The lint columns: flipped, slivers (% of faces under 10 degrees), components. Exit 1 if any row fails, so it can
gate a batch run.
"""
import argparse
import json
import pathlib
import sys

import mesh_lint
from preflight import BUDGETS, CLIPS, MATERIAL_SLOTS  # one table for every gate


def stats(glb):
    data = glb.read_bytes()
    doc = json.loads(data[20:20 + int.from_bytes(data[12:16], "little")].decode("utf8", "ignore").rstrip("\0 "))
    tris = sum(doc["accessors"][p["indices"]]["count"] // 3
               for m in doc["meshes"] for p in m["primitives"])
    return (tris, len(doc.get("materials", [])), len(doc.get("skins", [])),
            len(doc.get("animations", [])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=pathlib.Path)
    ap.add_argument("--kind", default="mass", choices=BUDGETS)
    ap.add_argument("--static", action="store_true", help="static rigs and buildings: no clips")
    args = ap.parse_args()
    lo, hi = BUDGETS[args.kind]
    clips = (0, 0) if args.static else CLIPS
    bad = 0
    print(f"{'file':28} {'tris':>5}  {'budget':>9}  mats skin anims flip sliver% comps  gate")
    for glb in sorted(args.folder.glob("*.glb")):
        tris, mats, skins, anims = stats(glb)
        m = mesh_lint.lint(glb)
        lint_bad = mesh_lint.failing(m, glb.name != "clay.glb")
        ok = (not lint_bad and lo <= tris <= hi and MATERIAL_SLOTS[0] <= mats <= MATERIAL_SLOTS[1]
              and skins == 1 and clips[0] <= anims <= clips[1])
        bad += 0 if ok else 1
        print(f"{glb.name:28} {tris:5}  {f'{lo}-{hi}':>9}  {mats:4} {skins:4} {anims:5} {m['flipped']:4} {m['sliver_pct']:7} {m['components']:5}  "
              f"{'PASS' if ok else 'FAIL'}{' ' + ','.join(lint_bad) if lint_bad else ''}")
    print(f"\n{len(list(args.folder.glob('*.glb')))} models, {bad} failing")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
