## SCORES
| Version | Clarity | Quality | Consistency | Structure | Originality |
|---------|---------|---------|-------------|-----------|-------------|
| V1      | 8       | 7       | 7           | 8         | 8           |
| V2      | 8       | 8       | 8           | 8         | 7           |
| V3      | 6       | 8       | 7           | 6         | 9           |
| V4      | 7       | 7       | 5           | 7         | 7           |
| V5      | 8       | 7       | 7           | 8         | 7           |
| V6      | 8       | 4       | 5           | 8         | 7           |

Spot-checks I ran against the worktree (load-bearing for the scores): `fit_spec.py:817` has `fit(..., wide=True)` and the CLI passes `wide=not args.fast`, so the 6-view objective is already the default; `FIT_VIEWS` (line 50) is the fast/classic path only. `sdf_body.py:36 K_FRAC = 0.25` exists. `loop_stage.py:16-17 DROP/GAIN` exist. `silhouette.py:194 COHERENCE_MIN = 0.6` exists. `massing.py:895 LEAN_PROPS = False`, and PIPELINE §20.L7-4 records that leaning the hfoo pike raised left .450→.759 but dropped top −.24 / bottom −.17 / rts −.16 ("the sheet's top view does not draw the pike that long").

## CRITIQUES
### V1
Only version that puts shape-from-shading first, and it argues it honestly (cel bands = quantized n·L = normal signal). But its own Risks admit the estimated light is "pouco confiável" with 5 slots, and the method costs 2 days before any number moves; for a batch pipeline that is the slowest bet on the table. The 1-day experiment is good prototyping discipline: it tests the metric, not the method, with a hand-edited spec and a kill criterion. Cite slip: `lean_props` NEGATIVO is §20.L7-4, not §23.

### V2
Cheapest actionable item in the whole packet: weight 0 + gate waiver for `incoherent` views, 1 h, rerun the 5 v13 specs, predicted outcome stated. `relief_chamfer` (clay z-buffer steps vs `silhouette.edges()`) is a concrete new ruler with existing infra. Weak spots: "sheet-hard" for hfoo is partly wrong (vertical-front + diagonal-left is geometrically consistent; the real incoherence is top/rts, which V2 does not say), and zeroing views legitimately risks hiding bad sheets — acknowledged, not solved.

### V3
Most original: massing-vs-author table showing the LLM author worsens hfoo left .719→.415 and n017 top .920→.822, plus the optimizer/gate camera gap (.07–.08). If those numbers hold, that is the highest-return process fix in the packet and nobody else saw it. Costs: a whole section on n01X, which is not one of the 5 units asked for, blows the line budget and buries the per-model table; "lança coerente, não lida" for hfoo ignores the §20.L7-4 top/rts collapse when the pike is leaned.

### V4
Internally inconsistent in the first 3 lines: point 2 says 3 of 5 fail by sheet incoherence "(hfoo, n02X, n017)", point 3 says n02X passes — and the original table has 3 PASS. `z_err` with reprojection residual on the 3rd view as self-validation is the best-designed metric here (fail-loud on bad sheets for free). "Gates calibrated to pass existing runs" is a sharp, uncomfortable critique others skipped. Sheet-coherence gate with 5 thresholds is over-specified for a first pass.

### V5
Fits a prototyping brief best: zero GPU, OpenCV contour detector in the morning, SDF k=0 + offset in the afternoon, kill criterion by end of day. `K_FRAC=0.25` smooth-min filling concavities is verified and is a physical cause nobody else names for n005+n00U together. "Degrau estimado pela largura da sombra adjacente" is hand-waving with no validation path; ranking normals networks 3rd contradicts its own "L5-4b failed on target, not network" (if the target is now right, networks should rank higher or be tested in the same day).

### V6
Central claim is false: "fit optimizes 3 views, verdict judges 6" cites `fit_spec.py:50`, but `fit()` defaults to `wide=True` (the verdict's 6 views) and P1 proposes making default what already is default. That invalidates summary point 2, the n02X row, and P1. The hfoo "não é sheet incoerente" reading is right for front/left but ignores the top/rts record in §20.L7-4. Still worth keeping: suspend L11-7 in favour of one causal chain per leva, `carve` op for SDF (only one who notes additive SDF cannot cut a recess), and "stage 2 not run = FAIL(infra)".