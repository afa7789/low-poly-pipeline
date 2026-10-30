## SCORES
| Version | Clarity | Quality | Consistency | Structure | Originality |
|---------|---------|---------|-------------|-----------|-------------|
| V1      | 8       | 7       | 7           | 8         | 6           |
| V2      | 6       | 8       | 7           | 6         | 9           |
| V3      | 7       | 6       | 5           | 8         | 7           |
| V4      | 7       | 6       | 6           | 7         | 7           |
| V5      | 8       | 9       | 8           | 8         | 8           |
| V6      | 8       | 7       | 7           | 7         | 8           |

Spot-checked against repo: `fit_spec.py:50 FIT_VIEWS = ("front","left","back")` (V5 correct, nobody else caught it); `silhouette.py:194 COHERENCE_MIN = 0.6` (V1 correct); `sdf_body.py:36 K_FRAC = 0.25` (V4 correct); HOODS at `spec_pipeline.py:115` (all); `pin_tilts` and `triangulate_joints` exist (V2/V1/V5 correct).

## CRITIQUES
### V1
Cleanest contract compliance; every claim has a file:line and all checked out. But core process item 1 (weight 0 for incoherent views) treats the measurement as the problem: n00U's top/bottom panels disagree with the hull because the spider is drawn differently, and zeroing them makes the gate blind exactly where the legs are wrong. hfoo framed as "sheet-hard"/incompatible pose is geometrically wrong (see V5). Ranking lines (where) above triangulation (ruler) while admitting lines give no magnitude is a soft contradiction with its own "first the ruler" opener.

### V2
Most original and the only one with stage-by-stage numbers (massing → author → final; gate-vs-optimizer camera gap .07–.08). "Author worsens 2 of 5" is a falsifiable, high-value claim. But it breaks the output contract: an unrequested n01X section pushes it past ~120 lines and buries question A. Dense notation (.771 → .764, r_sym .72) without the reader knowing those fields; several items depend on `review.md` numbers the reader cannot see. Camera-gap finding partially overlaps V5's FIT_VIEWS root cause but V2 never names it.

### V3
Metric-first argument (z_err with 3rd-view reprojection residual as self-validation) is the soundest depth proposal in the set. Undermined by internal contradiction: summary says 3/5 fail by incoherent sheet including n02X, next line says n02X passes. Proposed sheet gates (front mirror-IoU ≥ .90 for bipeds, prop angle match across views ±15°) would reject every legitimate 3/4 pose and every prop tilted in the sagittal plane; a tilted lance IS vertical in front and diagonal in left. That gate encodes a geometry error.

### V4
K_FRAC smooth-min as the shared physical cause for n005 and n00U is specific and checkable, but overreaches for n005: V1 shows the spec has no hood piece at all (lathe + decal), so there is no recess for the SDF to fill; smoothing is second-order. "Degrau pela largura da sombra adjacente" on a 2–3 tone cel is not defensible. Same prop-coherence misreading of hfoo. Persona leak in the title. Process items are solid and the "why L5-4b gave zero: wrong target, not the network" paragraph is the best single explanation across all six.

### V5
Only version that finds the structural bug: fit optimizes 3 views, verdict judges 6, so all top/bottom/rts spill is invisible to the optimizer; fix is one flag (`wide=True`) already in code. Also the only one to correctly refuse the "hfoo sheet incoherent" consensus with the sagittal-tilt argument. Weak spots: proposing a `carve` SDF op for n005 is over-engineering when a hood frustum + head placed further back is a plain union; P5 (cap flags at 5) is governance opinion dressed as metric. Risk list correctly notes the tilt-sweep leniency that `wide=True` would expose.

### V6
Best reframing of question B: "1 of 5 is a depth defect; starting with depth attacks 20% of the problem", backed by the project memory that models are alpha placeholders and the RTS camera barely sees a recess. `relief_agreement` (ink vs z-pass discontinuities, no 3D ground truth) is pragmatic and cheap. But it repeats the ±15° prop-coherence gate flaw, and "chain de 3 segmentos" × 8 legs strains the 400–700 tri budget it later invokes against SfS. Persona leak ("Revisor: P5"). Process item 5 ("nothing to measure") contradicts the brief's rule 3.