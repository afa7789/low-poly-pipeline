## SCORES
| Version | Clarity | Quality | Consistency | Structure | Originality |
|---------|---------|---------|-------------|-----------|-------------|
| V1      | 8       | 7       | 7           | 8         | 8           |
| V2      | 8       | 8       | 7           | 8         | 7           |
| V3      | 6       | 8       | 7           | 6         | 9           |
| V4      | 7       | 6       | 6           | 7         | 6           |
| V5      | 8       | 8       | 7           | 8         | 8           |
| V6      | 8       | 7       | 7           | 8         | 7           |

## CRITIQUES
### V1
Best test design of the six: 1-day experiment validates the *instrument* (hand-edited n005 must move the metric while IoU stays flat) before any method is allowed to optimize against it. Step 5 is a real kill criterion. "Acceptance by symptom, not by mean" directly fixes the v14 false-neutral.
Weak spot: ranks shape-from-shading #1 while its own premise says cel = 2–3 quantized bands (~1.5 bit of normal). Four peers rank SfS last; V1 gives no evidence that band→normal-cone integration survives flat fills. Also repeats the "hfoo = sheet incoherent" claim without geometry check (see V5).

### V2
Only version that cites measured coherence numbers (hfoo rts .57, n00U top .53/bottom .49, n017 .58) and the fit weight 2.0 that amplifies them. Noise-floor step (3 runs, threshold = 2σ) is the single most important testing fix in the whole packet; nobody else except V3 has it.
Inconsistency: calls n017 "não-PASS" (table says PASS with rts FAIL). Process 1 claims three units leave FAIL "sem mudança de spec" in 1 h — untested prediction stated as expected result. `relief_chamfer` threshold 0.02 H picked without noise data, contradicting its own item 3.

### V3
Highest information content: massing-vs-final per view (author worsens hfoo left −.30, n017 top −.10) and the optimizer/gate camera gap (.07–.08) are falsifiable, measurable, and nobody else found them. 3× repetition + 2σ acceptance is correct testing discipline.
Violates the output contract: adds an unrequested §2 on n01X, dense tables, likely over the ~120-line budget. The n01X control is valuable but belongs in an appendix. Calls hfoo lance "coerente, não lida" — agrees with V5, disagrees with 4 peers; right call, but buried.

### V4
Persona leak in title ("P2, ML Ops") breaks anonymization. Blames n00U leg tips and n005 recess on `K_FRAC=0.25` smooth-min — plausible for recess, not for tip position; no measurement offered to separate the two. "Degrau pela largura da sombra adjacente" is speculation with no validation step.
Good: `effect.json` per flag and "stage 2 always" are concrete CI gates. `recess_err` is defined but requires top/left triangulation the same doc says is low-ground for concavities — circular.

### V5
Strongest structural root cause: fit optimizes 3 views (`FIT_VIEWS`), verdict judges 6 — explains all top/bottom spill in one testable change (`wide=True`, 5-unit battery, DROP .01). Correctly refutes the "hfoo incoherent" consensus: sagittal tilt is vertical in FRONT and diagonal in LEFT by construction. "Infra failure = FAIL, never CHECK" is the right policy.
Risk: recommends suspending L11-7 and capping flags at 5 — contradicts §4 ("medir sempre") and the project's own rule to run the full ablation matrix. Disagreement is argued, but the cost (losing paper data) isn't weighed. 1.5× fit time stated without measurement.

### V6
Persona leak ("Revisor: P5"). Sharpest framing: 1 depth defect, 3 prop/appendage, 1 sheet → "depth plan attacks 20%". `relief_agreement` is the most fully specified new metric (precision/recall, SLACK px, expected baseline recall ≈ 0). Risk list is the best: raw-vs-filtered IoU side by side, priors per rig family not global, judge-as-oracle caveat.
Weaknesses: repeats the hfoo incoherence claim; Process 5 "nada a medir" is a non-answer in a document whose contract demands a metric per item; n00U carapace concavity *is* a depth defect, so the 20% figure undercounts.