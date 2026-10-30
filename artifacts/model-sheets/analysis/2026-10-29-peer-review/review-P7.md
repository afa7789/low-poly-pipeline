## SCORES
| Version | Clarity | Quality | Consistency | Structure | Originality |
|---------|---------|---------|-------------|-----------|-------------|
| V1      | 7       | 7       | 6           | 8         | 7           |
| V2      | 8       | 8       | 7           | 8         | 8           |
| V3      | 7       | 7       | 4           | 8         | 7           |
| V4      | 7       | 7       | 6           | 7         | 8           |
| V5      | 8       | 9       | 8           | 8         | 9           |
| V6      | 8       | 8       | 8           | 8         | 8           |

## CRITIQUES
### V1
Best falsification design: hand-edit n005, require metric moves AND judge agrees AND IoU flat, else "stop, nothing is measurable" — real debugging discipline. But ranks shape-from-cel #1 while its own Risks row admits the estimated light is "pouco confiável" and the premise says cel is ~quantized n·L; a 2–3 band signal cannot be inverted to a normal cone with any precision. "IoU vs juiz concordam 1/5" appears with no source. n00U "carapaça em tenda (pico no front)" contradicts every other reviewer who saw convex/no-concavity — one of them misread the image.

### V2
Strongest evidence chain: ties the 3 non-PASS to `incoherent` views with concrete numbers (.57/.53/.49/.58), `COHERENCE_MIN=0.6`, and weight 2.0 at `views.py:42-44` — pipeline measures the lie then optimizes against it. Noise-floor-before-thresholds (`compare_runs --stability`, limiar = 2σ) is the right order. Inconsistency: exec summary #2 frames hfoo as rts-incoherence, but hfoo's actual FAIL is left .415 and the row fix is body/prop IoU split — zeroing rts fixes nothing there. "verdict por vistas coerentes" for n017 is passing by deleting the failing view; the risk row names it but the fix still does it.

### V3
Internal contradiction kills it: point 2 lists n02X among "3 das 5 unidades falham por sheet incoerente", point 3 lists n02X among "as 2 que passam". Original table says n02X PASS. Also "3 of 5 fail" is false (2 non-PASS). Good catches elsewhere: `GAIN .005` below documented run-to-run noise .02–.05 = coin flip; `RIG_GATES` lowered to fit existing runs; per-limb `limb_tip_err`. Triangulation #1 claiming "z métrico para recesso da cara" is unsupported — no orthographic view sees inside an open hood; V2 says this explicitly and is right.

### V4
Distinctive mechanism: smooth-min `K_FRAC=0.25` filling concavities, with file:line — testable in an hour. But it conflicts with its own n005 row: if the author never emitted a `hood` piece (V2: head = lathe + decal), there is no hood/head blend to harden. Both causes stated, neither isolated. "profundidade do degrau pela largura da sombra adjacente" is the only genuinely new signal proposed by anyone. `recess_err` "triangulada top/left" has the same blind-spot problem as V3. Title leaks reviewer identity ("P2, ML Ops") — contract says anonymized final doc.

### V5
Only version that disputes the crowd and is geometrically right: a spear tilted in the sagittal plane IS vertical in FRONT and diagonal in LEFT — hfoo is not sheet-incoherent, the spec sets `to` vertical and fit never rotates props. V1/V2/V3/V4/V6 all accepted "incoerente" from the brief. Second structural find: fit optimizes 3 views (`fit_spec.py:50`) while verdict judges 6 — explains why top/bottom/rts spill is invisible, and `wide=True` already exists. Weak spots: "SDF só aditiva — não cava" ignores that recess can come from piece placement + open frustum without a `carve` op; landmarks via VLM `ask` break determinism and the fix (2 passes, reject >.03 H) is a patch. Suspending L11-7 is bold but argued.

### V6
Best reframing: counts defects by class — 1 depth, 3 thin props/appendages, 1 sheet — so "qualquer plano que comece por profundidade ataca 20%". `relief_agreement` (ink mask vs z-pass discontinuities, precision/recall, SLACK 4 px) is deterministic, needs no 3D ground truth, and predicts n005 recall ≈ 0 today — falsifiable. Weaknesses: follows the hfoo-incoherent consensus without checking geometry (see V5); process item 5 "nada a medir" violates the contract's "com como medir"; "Revisor: P5" leaks identity. Risk "profundidade é polish de placeholder" imports project memory not in the artifact — correct context, but should be flagged as external.