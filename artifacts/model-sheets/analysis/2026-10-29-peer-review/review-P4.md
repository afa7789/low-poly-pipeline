## SCORES
| Version | Clarity | Quality | Consistency | Structure | Originality |
|---------|---------|---------|-------------|-----------|-------------|
| V1      | 7       | 6       | 6           | 7         | 8           |
| V2      | 8       | 9       | 8           | 8         | 7           |
| V3      | 6       | 8       | 7           | 6         | 9           |
| V4      | 7       | 7       | 5           | 8         | 7           |
| V5      | 7       | 7       | 6           | 7         | 7           |
| V6      | 8       | 7       | 7           | 8         | 7           |

## CRITIQUES
### V1
Contrarian pick: ranks shading-from-cel #1 after stating the sheet is "n·L quantizado, 2–3 bandas" — that premise is exactly why V2/V4/V5/V6 rank SfS last, and V1 never explains how 2–3 bands plus interior lines yield enough signal to integrate normals; "2 dias, tudo numpy" is hand-waved. The real contribution is methodological: validate the interior metric by hand-editing n005 and checking the metric moves while IoU doesn't (falsification of the ruler, step 5 "parar"). "Aceitação por sintoma, não por média" is the sharpest process idea in the packet. Claims like "IoU vs juiz concordam 1/5" and "`verdict_of` bloqueia stage 2" are asserted without a cited line.

### V2
Best evidence chain: per-view incoherence numbers (hfoo rts .57, n00U top .53/bottom .49, n017 rts .58) tied to `COHERENCE_MIN=0.6` and weight 2.0 at `views.py:42-44` — "mede a mentira e otimiza contra ela" is a root cause, not a symptom. Process 1 costed at 1 h with a falsifiable prediction (3 units exit FAIL with zero spec change) is how a reviewer should write. Catches that the 4/5 judge result compares clay vs textured, invalidating the original's own evidence. Weak spots: n005 "spec sem peça capuz" contradicts V3's "capuz é lathe r .287" — one of them misread spec.json; `relief_chamfer` and `z_joint_err` are two new metrics when the contract asked for one, and the 1-day experiment leans on σ from Process 3 that doesn't exist yet.

### V3
The only version that changes the problem: massing already delivers 90–100 % of final IoU and the LLM author *regresses* two units (hfoo left .719→.415, n017 top .920→.822), plus optimizer and gate render with different cameras (.07–.08 gap). If those numbers hold, every other review is optimizing the wrong stage. That is "deep over wide" done right. Costs: §2 on n01X is outside the 5 requested units and the output contract, pushes past ~120 lines, and the recess question (B) is quietly sidestepped — piece-level triangulation gives leg tips and spear axis, not how far the face sits inside the hood (top cannot see inside a hood, as V2 notes). Acceptance "+.03 média em 5 unidades" is set before measuring the 3× variance the same document says is the size of any leva's gain.

### V4
Strongest governance framing: GAIN .005 below a documented .02–.05 noise floor is "moeda ao ar"; "gates calibrados para passar runs" (`RIG_GATES`) is a real organizational smell. `z_err` with reprojection residual on the third view as built-in sheet-incoherence detector is elegant and self-validating. But the summary contradicts itself: n02X is listed both among "3 que falham por sheet incoerente" and "as 2 que passam". The sheet gate demands front mirror-IoU ≥ .90 — that rejects every 3/4-posed design (the ogre is one) instead of handling asymmetry like V3 does. And claiming metric z for the face recess from front/left ignores that the hood occludes the face in profile.

### V5
Brings a mechanism nobody else centers: SDF smooth-min `K_FRAC=0.25` filling concavities, with file:line. Yet calling n005 and n00U "a mesma falha física" overreaches — if the spec has no recess, k=0 changes nothing, and V5's own fix stacks three corrections (k=0 + cut + preflight), breaking the "UMA correção" rule. "Largura do torso lida da vista TOP quando r_sym < SYM_MIN" for n02X is a precise, cheap fix. "Profundidade do degrau pela largura da sombra adjacente" is a genuinely useful cue under fixed light that no other version exploits. Header leaks the persona ("P2, ML Ops"), breaking anonymization. Experiment applying relief.json only to the SDF is coherent with its thesis — good internal discipline.

### V6
Best strategic reframe for a lead: "1 defeito de profundidade, 3 de props/apêndices, 1 de sheet — começar por profundidade ataca 20 %", plus the risk that depth is polish on placeholder models (cites project memory) with a hard 1-day cap. `relief_agreement` (ink vs z-discontinuity P/R, SLACK 4 px, no 3D ground truth) is the same idea as V2's chamfer but better specified for a gate. Weaknesses: n017 fix "uma peça `chain` por caixa 2D do VLM" injects a non-deterministic step into a pipeline the rules say must be deterministic; Process 5 "nada a medir" dodges the question of how you'd know when to unfreeze the loop; header leaks "Revisor: P5". Mechanism depth is thinner than V2/V3 — it diagnoses categories well but rarely names the line of code that produces the symptom.