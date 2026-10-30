## SCORES
| Version | Clarity | Quality | Consistency | Structure | Originality |
|---------|---------|---------|-------------|-----------|-------------|
| V1      | 7       | 6       | 6           | 8         | 8           |
| V2      | 6       | 8       | 8           | 6         | 9           |
| V3      | 7       | 6       | 5           | 8         | 7           |
| V4      | 7       | 7       | 7           | 8         | 7           |
| V5      | 8       | 9       | 8           | 8         | 8           |
| V6      | 8       | 6       | 7           | 8         | 7           |

## CRITIQUES

### V1
Best experiment design in the set: hand-edit n005 spec, prove the *metric* moves before any method — that is the missing control everyone else skips. But why rank shading-from-cel #1 while admitting the sheet is quantized n·L with 2–3 bands? Three peers call that ill-posed; V1 asserts "ALTO" with no evidence it integrates. Calls hfoo "sheet incoerente" without asking the obvious question: what does a spear tilted in the sagittal plane look like from the front? Vertical. The sheet may be fine. Also: "n017 rts .700 é a corrente" — measured where, or inferred?

### V2
Only version that brought *new data* instead of re-reading the brief: massing-vs-final per view, camera gap .07–.08 between `optimize_verts` and gate, n01X as control, 3-run variance. That is data engineering. Gets hfoo right ("coerente, não lida"). Costs: §2 is a section the contract did not ask for, the numbering drifts, and the exec summary leans on `review.md` figures the reader cannot see in the table. Where does the "90–100% do IoU vem do massing" claim come from for n00U, whose massing numbers are never shown?

### V3
Strongest process point in the packet: `GAIN .005` sits below the documented .02–.05 run-to-run noise (29.L11-0) — the loop is a coin flip. Reprojection residual as internal validation of landmarks is sound. But it contradicts itself: n02X is listed as both "falha por sheet incoerente" and one of "as 2 que passam"; the brief says 3 PASS. And the proposed Hough gate (prop angle must match across views ±15°) would *reject* a correctly drawn forward-tilted spear — the gate encodes the misdiagnosis of hfoo. Would its own z_err experiment falsify that? Probably yes; credit for falsifiability.

### V4
Single physical hypothesis unifying n005 and n00U (`K_FRAC=0.25` smooth-min fills concavities) with a file:line — the most mechanistic root cause offered, and k=0 per-part is a cheap test. "Degrau pela largura da sombra adjacente" is clever but unvalidated; what is the shadow width of a 2-band cel? Repeats the hfoo "sheet incoherent" error and adds "top não a desenha" without saying how that was checked. Title leaks reviewer identity. Does `recess_err` triangulated top×left even exist for a recess that top cannot see (face under hood)?

### V5
The one version that asks the geometric question on hfoo and answers it: sagittal tilt is vertical in FRONT, diagonal in LEFT, so the spec (`spec.json:470-480`) is wrong, not the sheet. That flips 4 of 6 peers' process item #1. `FIT_VIEWS` 3 vs gate 6 (`fit_spec.py:50` / `silhouette.py:32`) is a structural cause that, if confirmed, explains every top/bottom/rts spill at once — checkable in minutes. Weak spots: P5 ("apagar flags, ≤ 5 opt-ins") collides with the standing rule to ablate every opt-in for the paper; and "SDF só aditiva, não cava" is asserted, not shown — is `cut: sheet` not already a subtraction?

### V6
Honest triage ("1 depth, 3 props, 1 sheet → depth plan attacks 20%") and the "placeholder models" risk are the most pragmatic framing offered. `relief_agreement` (ink vs z-pass discontinuities, no 3D GT) is cheap, deterministic, and genuinely new. But the hfoo diagnosis is wrong, and `prop_coherence` via PCA ±15° would institutionalize the error as a gate — the exact failure V6 warns about in its own Risks ("gate a esconder defeitos"). Reviewer identity leaks in the header. Process 2 ("re-medir flags mortas antes de nova técnica") is correct and underweighted by everyone else.