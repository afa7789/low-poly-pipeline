# L12-10a ablation matrix (PIPELINE 30.L12-10a)

Each variant rebuilds the v13 spec of the 6 units with `--deterministic` (noise 0), cameras of v13 fixed, no LLM; Δ against `base` (colour: against `c-base`). Spill and bare are the gate's numbers (the body's where the sheet has props). "falls > 2σ" counts the (unit, view) cells whose IoU falls by more than 2σ of `noise-l12.json`. Verdict: default-candidate = mean spill falls (by more than 0.002) and no view falls > 2σ; opt-in = spill or IoU improves but a view falls; no = nothing improves.

## Summary by variant

| variant | units | Δ spill | views spill ≤ .03 (base) | Δ IoU | Δ bare | views fall > 2σ | Δ contact | Δ z_err | Δ planarity | Δ crease R | Δ tris | Δ s | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c-legacy | 6 | +0.0000 | 0/36 (0) | +0.0000 | +0.0000 | 0 | +0.0000 | +0.0000 | +0.000 | +0.000 | +0 | +44 | no (no-op: nothing moved) |
| c-shared | 6 | +0.0000 | 0/36 (0) | +0.0000 | +0.0000 | 0 | +0.0000 | +0.0000 | +0.000 | +0.000 | +0 | +59 | no (no-op: nothing moved) |
| c-split | 6 | +0.0000 | 0/36 (0) | +0.0000 | +0.0000 | 0 | +0.0000 | +0.0000 | +0.000 | +0.000 | +0 | +50 | no (no-op: nothing moved) |
| c-luma | 6 | +0.0000 | 0/36 (0) | +0.0000 | +0.0000 | 0 | +0.0000 | +0.0000 | +0.000 | +0.000 | +0 | +19 | no (no-op: nothing moved) |
| c-ramp | 6 | +0.0000 | 0/36 (0) | +0.0000 | +0.0000 | 0 | +0.0000 | +0.0000 | +0.000 | +0.000 | +0 | -13 | no (no-op: nothing moved) |
| c-snap | 6 | +0.0000 | 0/36 (0) | +0.0000 | +0.0000 | 0 | +0.0000 | +0.0000 | +0.000 | +0.000 | +0 | -17 | no (no-op: nothing moved) |
| c-painted | 6 | +0.0000 | 0/36 (0) | +0.0000 | +0.0000 | 0 | +0.0000 | +0.0000 | +0.000 | +0.000 | +0 | -14 | no (no-op: nothing moved) |

## Variant x unit (shape)

| variant | unit | IoU f/l/b/top/bot/rts | spill f/l/b/top/bot/rts | spill ≤ .03 | bare mean | Δ IoU | Δ spill | falls > 2σ | contact | z_err | plan | crease R | tris | s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Stage 2 (colour)

| variant | unit | atlas KB | image | prims | materials | luma L1 | zones mean | zone gate | uv out of range |
|---|---|---|---|---|---|---|---|---|---|
| c-base | hfoo | 6.4 | 128x128 | 2 | 2 | 0.060 | 0.204 | ok | 0 |
| c-base | n005 | 5.9 | 128x128 | 2 | 2 | 0.042 | 0.580 | ok | 0 |
| c-base | n00U | 0.7 | 32x64 | 2 | 2 | 0.058 | 0.241 | ok | 0 |
| c-base | n017 | 4.9 | 64x128 | 1 | 1 | 0.137 | 0.347 | ok | 0 |
| c-base | n01X | 2.5 | 64x64 | 1 | 1 | 0.022 | 0.359 | ok | 0 |
| c-base | n02X | 1.9 | 64x64 | 1 | 1 | 0.054 | 0.344 | ok | 0 |
| c-legacy | hfoo | 90.4 | 768x768 | 2 | 2 | 0.064 | 0.203 | ok | 1 |
| c-legacy | n005 | 86.0 | 768x768 | 2 | 2 | 0.042 | 0.582 | ok | 0 |
| c-legacy | n00U | 14.3 | 768x512 | 2 | 2 | 0.059 | 0.241 | ok | 2 |
| c-legacy | n017 | 55.5 | 512x512 | 1 | 1 | 0.134 | 0.349 | ok | 2 |
| c-legacy | n01X | 25.1 | 512x512 | 1 | 1 | 0.022 | 0.358 | ok | 0 |
| c-legacy | n02X | 70.0 | 768x768 | 1 | 1 | 0.049 | 0.343 | ok | 0 |
| c-luma | hfoo | 6.5 | 128x128 | 2 | 2 | 0.058 | 0.204 | ok | 0 |
| c-luma | n005 | 5.9 | 128x128 | 2 | 2 | 0.032 | 0.577 | ok | 0 |
| c-luma | n00U | 0.7 | 32x64 | 2 | 2 | 0.019 | 0.275 | ok | 0 |
| c-luma | n017 | 4.8 | 64x128 | 1 | 1 | 0.120 | 0.348 | ok | 0 |
| c-luma | n01X | 2.5 | 64x64 | 1 | 1 | 0.022 | 0.358 | ok | 0 |
| c-luma | n02X | 1.8 | 64x64 | 1 | 1 | 0.042 | 0.342 | ok | 0 |
| c-painted | hfoo | 390.4 | 768x768 | 9 | 9 | 0.079 | 0.203 | ok | 1 |
| c-painted | n005 | 291.6 | 768x768 | 7 | 7 | 0.055 | 0.591 | ok | 0 |
| c-painted | n00U | 185.3 | 768x512 | 6 | 6 | 0.136 | 0.222 | ok | 2 |
| c-painted | n017 | 265.2 | 512x512 | 4 | 4 | 0.183 | 0.290 | ok | 2 |
| c-painted | n01X | 142.3 | 512x512 | 3 | 3 | 0.104 | 0.302 | ok | 0 |
| c-painted | n02X | 430.6 | 768x768 | 8 | 8 | 0.059 | 0.332 | ok | 0 |
| c-ramp | hfoo | 10.1 | 128x256 | 2 | 2 | 0.066 | 0.201 | ok | 0 |
| c-ramp | n005 | 7.8 | 128x128 | 2 | 2 | 0.041 | 0.587 | ok | 0 |
| c-ramp | n00U | 1.8 | 64x64 | 2 | 2 | 0.067 | 0.249 | ok | 0 |
| c-ramp | n017 | 6.7 | 32x256 | 1 | 1 | 0.118 | 0.342 | ok | 0 |
| c-ramp | n01X | 3.6 | 64x128 | 1 | 1 | 0.023 | 0.344 | ok | 0 |
| c-ramp | n02X | 4.2 | 64x128 | 1 | 1 | 0.061 | 0.346 | ok | 0 |
| c-shared | hfoo | 4.5 | 128x128 | 2 | 2 | 0.057 | 0.206 | ok | 0 |
| c-shared | n005 | 4.1 | 128x128 | 2 | 2 | 0.041 | 0.581 | ok | 0 |
| c-shared | n00U | 1.0 | 128x128 | 2 | 2 | 0.060 | 0.228 | ok | 0 |
| c-shared | n017 | 3.0 | 128x128 | 1 | 1 | 0.136 | 0.346 | ok | 0 |
| c-shared | n01X | 2.0 | 128x128 | 1 | 1 | 0.022 | 0.359 | ok | 0 |
| c-shared | n02X | 1.7 | 128x128 | 1 | 1 | 0.055 | 0.344 | ok | 0 |
| c-snap | hfoo | 4.4 | 128x128 | 2 | 2 | 0.057 | 0.206 | ok | 0 |
| c-snap | n005 | 5.9 | 128x128 | 2 | 2 | 0.042 | 0.580 | ok | 0 |
| c-snap | n00U | 1.1 | 128x128 | 2 | 2 | 0.060 | 0.228 | ok | 0 |
| c-snap | n017 | 3.1 | 128x128 | 1 | 1 | 0.136 | 0.346 | ok | 0 |
| c-snap | n01X | 2.0 | 128x128 | 1 | 1 | 0.022 | 0.359 | ok | 0 |
| c-snap | n02X | 1.8 | 128x128 | 1 | 1 | 0.055 | 0.344 | ok | 0 |
| c-split | hfoo | 6.4 | 128x128 | 9 | 9 | 0.060 | 0.204 | ok | 0 |
| c-split | n005 | 5.9 | 128x128 | 7 | 7 | 0.042 | 0.578 | ok | 0 |
| c-split | n00U | 0.7 | 32x64 | 6 | 6 | 0.058 | 0.241 | ok | 0 |
| c-split | n017 | 4.9 | 64x128 | 4 | 4 | 0.137 | 0.347 | ok | 0 |
| c-split | n01X | 2.5 | 64x64 | 3 | 3 | 0.022 | 0.359 | ok | 0 |
| c-split | n02X | 1.9 | 64x64 | 8 | 8 | 0.054 | 0.344 | ok | 0 |
