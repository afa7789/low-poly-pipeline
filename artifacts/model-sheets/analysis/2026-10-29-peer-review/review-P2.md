## SCORES
| Version | Clarity | Quality | Consistency | Structure | Originality |
|---------|---------|---------|-------------|-----------|-------------|
| V1      | 7       | 6       | 6           | 8         | 8           |
| V2      | 8       | 7       | 7           | 8         | 6           |
| V3      | 6       | 8       | 8           | 6         | 9           |
| V4      | 7       | 7       | 5           | 8         | 7           |
| V5      | 8       | 8       | 8           | 8         | 7           |
| V6      | 8       | 6       | 7           | 8         | 7           |

## CRITIQUES

### V1
Contrarian bet: ranks shape-from-cel #1 while every other version ranks it last. Its own premise ("2–3 bands = quantized n·L") undercuts it: 1.5 bits of normal per zone is not "ALTO ganho" for mask relief in a 400–700 tri budget, and no runnable check is proposed beyond "metric drops ≥30%". The interior metric (luma_l1 vs cel, reusing `fit_luma` light) is the practical part and cheap — but the 1-day experiment validates the metric, not any depth method; honest, but the day ends with zero depth recovered. Misreads hfoo as "sheet incoerente": a spear tilted in the sagittal plane IS vertical in front and diagonal in left (V3/V5 get this right). "IoU vs juiz concordam 1/5" is asserted, not sourced.

### V2
Best data-quality framing: three non-PASS units map to sheets flagged `incoherent` (`silhouette.py:194`, numbers per view) yet weighted 2.0 in fit — concrete, 1-hour fix, measurable by rerunning v13 specs. `relief_chamfer` (z-pass vs `edges()`) is a deterministic no-GT ruler reusing the existing render path. Weak spot: hfoo row cites the real bbox-framing mechanism (§29.L11-0) and then still calls the sheet "hard/incompatible" — the sagittal-tilt reading is missing. Ranking SfS "alto custo / baixo ganho" with validation "—" is a dismissal, not an argument. Least original of the set: largely V4/V6's conclusions with tighter citations.

### V3
Only version that produces new evidence instead of re-reading the brief: massing alone already hits ~final IoU, author LLM worsens hfoo left (.719→.415) and n017 top (.920→.822); optimize_verts and gate use different cameras (gap .07–.08). Both are cheap, high-leverage; the "autor-vs-massing guard" is the v14 guard moved one stage earlier — works-over-theory. Correct hfoo diagnosis (coherent sagittal tilt, `prop_axis` via front×left). Cost: §2 n01X control table is off-brief (n01X is not one of the 5), eats ~25 lines, strains the ~120-line cap; clarity suffers from stage-by-stage density. The 3× repetition finding (same sheet: .78→.89→.87) is the single most important MLOps fact in any version and is buried in prose.

### V4
Strongest ops discipline: noise floor before any A/B, "gates calibrated to pass existing runs" called out, flag-liveness test, z_err with reprojection residual on the 3rd view as self-validation (also auto-detects incoherent sheets). Two real defects: (a) exec summary says 3/5 fail by incoherent sheet "(hfoo, n02X, n017)" then the next line says n02X is one of the two that PASS — contradiction in the first 10 lines; (b) the proposed `sheet_coherence` prop gate "ângulo do maior traço ±15° entre vistas" is geometrically wrong — a sagittally tilted spear legitimately differs ~35° between front and left. That gate would reject correct sheets. Noise .02–.05 "documentado em 29.L11-0" is the load-bearing claim and lacks the exact line.

### V5
Cleanest root cause: fit optimizes 3 views (`fit_spec.py:50`) while the verdict judges 6; `wide=True` already exists — a one-flag battery, measurable, no new code. Correct hfoo reading with spec line refs. "Falha de infra é FAIL, nunca CHECK" and "máx 5 opt-ins vivos" are real process fixes. Disagreements: (a) "SDF união só aditiva — não cava" ignores that `cut: sheet` exists; the true point is silhouettes can't see the recess, so `carve` needs a non-silhouette target or it's unoptimizable; (b) recommending suspension of L11-7 contradicts the stated in-progress ablation goal and is asserted without cost numbers. Risk section correctly flags that fitting wide only helps if fit and gate pin the same tilt — V3 found the same gap independently.

### V6
Useful reframing: only n005 is a depth problem; 3/5 are thin props/appendages, 1 is sheet — "any plan starting with depth attacks 20%". `relief_agreement` (ink mask vs z-pass edges, precision/recall, SLACK 4px) is the most prototype-ready metric proposed, and it ends with one concrete next action. But `prop_coherence` (PCA angle must agree front vs left within 15°) repeats V4's geometric error — it would flag hfoo's coherent sagittal tilt as incoherent, which is exactly the misdiagnosis in its own hfoo row. Ranking (2)+(6) first is sound for cost, but "prior diz quanto" with a fixed 0.06–0.10 H per class is a guess with no validation beyond the judge. Risk "profundidade é polish de placeholder" is the right project-level call and no one else made it.

Cross-version note: the hfoo "incoherent sheet" claim splits the field 4 (V1, V2, V4, V6) vs 2 (V3, V5). V3/V5 are geometrically right; any prop-angle-agreement gate built from the other four would reject valid sheets.