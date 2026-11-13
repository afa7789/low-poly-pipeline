# vendor

`bx_anim.py` — keyframe helpers (Blender 5.x slotted-action API, blocking-to-spline, motion measurement).
`build_unit.make_actions` loads it through `load_toolkit`; it used to be read from
`~/.config/opencode/skills/blender-animation/scripts/`, outside every repo.

- source: the author's own `blender-animation` skill, version 0.1 (2026-09-24), copied unchanged on 2026-11-13
- licence: none stated at the source (no LICENSE file); same author as this repo, covered by this repo's terms
- sha256 at copy: see `git log` of this file; update by copying the skill's `scripts/bx_anim.py` again

Other `~/.config/opencode` reads stay outside: `bx_review` (blender-expert skill, turntable.py and
spec_pipeline.py review renders) and the API key in `opencode.json` (draft_loop.py, spec_pipeline.py).
