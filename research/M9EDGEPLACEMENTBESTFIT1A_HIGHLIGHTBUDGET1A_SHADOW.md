# M9EDGEPLACEMENTBESTFIT1A — HIGHLIGHTBUDGET1A treatment shadow

Status: **research only / selector unchanged / live renderer unchanged**  
Date: 2026-09-05

## Question

Can treatment strength be bounded by a generic finished-highlight budget rather than hard-coding a correction amount per DARK branch?

The current exact-DNG treatment sweep contains five available DARK anchors:

- `164019` — DARK_INTENT candidate
- `164048` — DARK_INTENT fail
- `142840` — DARK_ZERO_INTENT fail
- `142939` — DARK_ZERO_INTENT fail
- `144210` — DARK_FOREGROUND boundary/fail

Each has full-resolution frozen-path replays at `0 / +0.15 / +0.25 / +0.35 / +0.50 EV` with only additional pre-curve gain changed.

## Proposed separation

BESTFIT1A remains responsible only for **whether** a rescue is warranted.

HIGHLIGHTBUDGET1A is a separate research-only treatment ceiling responsible only for **how far** a selected rescue may proceed.

```text
BESTFIT1A
    HOLD -> frozen JPEG, no treatment
    DARK_* -> treatment sweep / bounded rerender

HIGHLIGHTBUDGET1A
    choose strongest candidate EV that remains inside finished-highlight budget
```

No selector branch is given a fixed EV merely because of its name.

## Provisional budget seed

For the existing discrete sweep, choose the strongest tested EV satisfying both:

- finished `q95Y <= 242`
- increase in finished `Y>=224` area relative to baseline `<= +0.040` absolute fraction (4 percentage points)
- hard maximum `+0.50 EV`

These values are **falsification seeds**, not production constants.

## Result on current DARK anchors

| frame | selector | chosen EV | why |
|---|---|---:|---|
| 164019 | DARK_INTENT | +0.50 | highlight tail stays comfortably inside budget |
| 164048 | DARK_INTENT | +0.50 | highlight tail stays comfortably inside budget |
| 142840 | DARK_ZERO_INTENT | +0.50 | existing endpoint area barely grows despite RAW clipping |
| 142939 | DARK_ZERO_INTENT | +0.50 | substantial finished headroom remains |
| 144210 | DARK_FOREGROUND | +0.25 | +0.35 crosses the highlight-growth / q95 neighborhood |

This reproduces the useful treatment asymmetry **without using branch identity to set the amount**.

## Sensitivity

The same `A/B -> +0.50` and `C -> +0.25` pattern is not confined to one exact threshold pair.

On this five-frame corpus it persists across a broad neighborhood, including:

- `q95` ceilings roughly `241..243` with bright-tail delta limits `0.035..0.060`
- `q95` ceilings roughly `244..246` when the bright-tail delta limit remains about `0.035..0.045`

This is better than a single magic cutoff, but it does **not** make the thresholds production-ready. The cohort is still too small, especially for Branch C.

## Why this is preferable to raw-clip sizing

`142840` has the highest RAW hard-clip fraction yet its finished `Y>=224` area changes very little at +0.50 EV. Therefore RAW clipping is not a reliable direct treatment-strength control.

The quantity that matters for a rerender is the **finished endpoint response** to extra pre-curve gain.

## Implementation implication

This policy still implies an edge-only two-stage JPEG path if it ever becomes live:

1. frozen baseline render and diagnostics;
2. BESTFIT1A classification;
3. only for DARK selections, bounded rerender;
4. treatment ceiling uses finished-highlight response;
5. HOLD remains on the untouched frozen path and DNG remains untouched.

A practical live implementation should not brute-force five full rerenders. A later experiment can determine whether baseline finished statistics predict the allowed ceiling closely enough to choose one rerender directly. Until then, HIGHLIGHTBUDGET1A is an **offline shadow policy only**.

## Current conclusion

The evidence now favors:

- **selector = reason/eligibility**
- **highlight budget = treatment ceiling**
- **no fixed global lift**
- **no branch-specific hard-coded amount yet**

Next falsification should be prospective DARK captures, especially additional foreground-collapse cases with different sky/highlight coverage. Do not tune this budget further on the current five anchors.
