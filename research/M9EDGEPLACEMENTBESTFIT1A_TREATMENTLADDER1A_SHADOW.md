# M9EDGEPLACEMENTBESTFIT1A — TREATMENTLADDER1A shadow

Status: **research only / no APK change / selector unchanged / frozen HOLD path unchanged**  
Date: 2026-09-05

## Motivation

HIGHLIGHTBUDGET1A showed that treatment strength can be limited by finished-highlight response rather than assigning a fixed EV by branch. A practical edge-only implementation does not need to predict the correct EV perfectly from baseline statistics.

Because BESTFIT DARK activations are intended to be rare, quality can be prioritized with a bounded strongest-to-weakest rerender ladder.

## Shadow ladder

After the frozen baseline render:

```text
if BESTFIT == HOLD:
    publish frozen baseline
else:
    try +0.50 EV pre-curve
    if inside finished-highlight budget: accept
    else try +0.35
    else try +0.25
    else try +0.15
    else publish baseline
```

Provisional HIGHLIGHTBUDGET1A seed used for each candidate:

- `q95Y <= 242`
- increase in `Y>=224` area from baseline `<= 0.040`

The ladder is a **treatment shadow**, not a production algorithm.

## Exact-DNG result

| frame | selector | attempts | accepted |
|---|---|---|---:|
| 164019 | DARK_INTENT | +0.50 pass | +0.50 |
| 164048 | DARK_INTENT | +0.50 pass | +0.50 |
| 142840 | DARK_ZERO_INTENT | +0.50 pass | +0.50 |
| 142939 | DARK_ZERO_INTENT | +0.50 pass | +0.50 |
| 144210 | DARK_FOREGROUND | +0.50 fail -> +0.35 fail -> +0.25 pass | +0.25 |

So the current treatment asymmetry emerges without a branch-specific amount.

## Why this is attractive for the M9 project

- HOLD photographs remain entirely on the frozen photographic path.
- The DNG is never modified.
- No broad shadow lift, exposure-policy rewrite or curve change is required.
- The correction remains a pre-curve M9 render, rather than a post-JPEG brightness hack.
- Treatment is allowed to vary by the finished photograph's response.
- A difficult foreground/highlight scene can automatically back away from +0.50.

## Performance implication

This deliberately spends extra render work only on rare selected failures. The current native colour stage is already much smaller than the historical multi-second renderer, so even a rollback case is preferable to changing the normal path for every photograph.

Do not optimize this yet. First establish prospective selector and treatment validity. If the architecture survives, later work can reduce retries using a one-probe interpolation or baseline prediction while preserving identical accepted pixels.

## Decision

TREATMENTLADDER1A is currently a cleaner prospective implementation candidate than hard-coding:

- Branch A = X EV
- Branch B = Y EV
- Branch C = Z EV

The branch identifies the failure morphology; the finished-highlight budget determines how much rescue survives.
