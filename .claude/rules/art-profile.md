# Art profile — unit models

Models are alpha placeholders: they must read and work in game, nothing more. No polish passes for beauty.
Each rule has an id, a check and the evidence it needs. A rule with no evidence is not PASS.

| Id | Rule | Check |
|---|---|---|
| A1 | **Style.** Armed humanoids are dieselpunk / Trench Crusade: trench-war gear, combustion engines, dirty lead-acid electricity, 1920-40s noir, aviation. Two or three elements from `artifacts/model-sheets/prompts/STYLE-trench-crusade.txt`, as large crude shapes. Fantasy races keep their own body. **Never a fuel/gas tank on the back.** | front/side/back views |
| A2 | **No outlines.** No black ink lines or dark seams between pieces, no `outline*` mesh. | views + palette |
| A3 | **Flat palette.** One flat colour per piece, one 64x64 palette atlas per unit (`model.palette.png`, 8x8 cells), one material/image. | `magick identify`; `mesh_lint.py` `materials`/`images` = 1 |
| A4 | **Locomotion visible.** Wheels, tracks, legs, wings or hover gap read from the match camera. Never a fixed stand or base. | v_game, side view, walk clip |
| A5 | **Eyes only when the concept shows them.** Default: no eyes. | concept sheet vs model |
| A6 | **Accents survive.** Saturated accents (eyes, jewels, lanterns, furnaces, coils) keep their saturation in the palette and in the game view; never greyed or merged into neighbours. | palette cells, v_game |
| A7 | **Judged as the player sees it.** Match camera (56 deg ortho) with the game's pixel-art shader on. Offline renders have no shader: final call in game, `build/castle_fight --model-scene hand` (pixel art on by default, F8 toggles). | v_game + render_gamecam; in-game check |
| A8 | **Strikes keyed on the weapon.** Attack moves the weapon tip into a held contact pose, not a body lean. Judge by eye and in game (top-down hides vertical dips). | `attack_gate.py` PASS + clips.png |
| A9 | **Silhouette matches the approved sheet.** IoU per view at or above `silhouette.py` `GATES`; spill (model outside the sheet) near zero; small uncovered sheet tolerated. | `silhouette.txt`, overlay.png |
| A10 | **Mesh sane.** 0 flipped, 0 degenerate, feet on the ground (`pivot.min_y` ~ 0), `root_scale` 1, one skin. | `mesh_lint.py` |

Process rules:
- Every paper used -> row in `docs/references.md`, same commit.
- Model work verifies with `make test` + `make lint` only; never castle_fight's `make check`.
