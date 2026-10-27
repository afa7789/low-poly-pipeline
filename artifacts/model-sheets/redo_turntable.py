#!/usr/bin/env python3
"""Ask the edit model for an 8-view turntable of an approved sheet (PIPELINE 21.F6).

    python3 redo_turntable.py n01X --race Mech --name "Iron Golem" [--sheet sheet.jpg]

One call (~$0.004) with prompts/00-template-turntable.txt and refs/<id>/<sheet> as the image;
the answer is saved as refs/<id>/sheet-turn.jpg (4 columns x 2 rows, 0..315 deg every 45).
The input sheet is never written. Then silhouette.turn_check says whether the eight panels are
coherent enough to use; the verdict is printed and written to refs/<id>/sheet-turn.json.
"""
import argparse
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools/blender"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--race", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--sheet", default="sheet.jpg")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check-only", action="store_true", help="skip the API call, test the existing sheet-turn.jpg")
    args = ap.parse_args()
    refs = HERE / "refs" / args.id
    out = refs / "sheet-turn.jpg"
    if not args.check_only:
        pdir = HERE / "prompts" / args.id
        pdir.mkdir(exist_ok=True)
        pfile = pdir / f"unit-{args.id}-turntable.txt"
        pfile.write_text((HERE / "prompts/00-template-turntable.txt").read_text()
                         .format(race=args.race, name=args.name, uid=args.id))
        cmd = [sys.executable, str(HERE / "generate.py"), str(pfile), "--image", str(refs / args.sheet),
               "--out", str(refs), "--name", "sheet-turn", "--aspect", "16:9"] + (["--dry-run"] if args.dry_run else [])
        gen = subprocess.run(cmd, capture_output=True, text=True)
        print(gen.stdout.strip() or gen.stderr.strip())
        if args.dry_run or gen.returncode:
            sys.exit(gen.returncode)
    if not out.exists():
        sys.exit(f"no {out}")
    import silhouette
    verdict = silhouette.turn_check(silhouette.turn_panels(out))
    (refs / "sheet-turn.json").write_text(json.dumps(verdict, indent=2))
    print(json.dumps(verdict, indent=1))
    sys.exit(0 if verdict["ok"] else 1)


if __name__ == "__main__":
    main()
