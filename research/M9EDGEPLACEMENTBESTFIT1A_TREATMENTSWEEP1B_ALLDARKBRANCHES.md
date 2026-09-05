# M9EDGEPLACEMENTBESTFIT1A — TREATMENTSWEEP1B all DARK branches

Status: **research only / selector unchanged / renderer unchanged**  
Date: 2026-09-05

## Scope

Exact-DNG pre-curve treatment sweeps now cover the available confirmed/candidate DARK anchors from all current selector branches:

- Branch A `DARK_INTENT`: `164019` DARK candidate, `164048` DARK_FAIL
- Branch B `DARK_ZERO_INTENT`: `142840` DARK_FAIL, `142939` DARK_FAIL
- Branch C `DARK_FOREGROUND`: `144210` foreground/boundary failure

Each frame was replayed at full 4096x3072 source geometry with only an additional pre-curve gain changed:

`0.00 / +0.15 / +0.25 / +0.35 / +0.50 EV`

Frozen photographic core remained R3.8-H25, Cobalt main-camera calibration, TC20, SAT3 M06/M07, curve02 and exact BT.601 4:2:2. TG1 has zero daylight weight on these frames.

## Full-resolution endpoint response

| branch | frame | raw clip | Y mean 0 -> +0.50 | q95 0 -> +0.50 | >=224 0 -> +0.50 |
|---|---|---:|---:|---:|---:|
| A | 164019 | 0.00067% | 25.35 -> 32.68 | 153.99 -> 180.37 | 1.079% -> 1.636% |
| A | 164048 | 0.2630% | 28.72 -> 36.26 | 179.01 -> 204.00 | 1.474% -> 2.880% |
| B | 142840 | 1.2109% | 21.55 -> 26.55 | 133.23 -> 160.33 | 3.392% -> 3.558% |
| B | 142939 | 0.0149% | 19.82 -> 26.44 | 93.31 -> 120.04 | 1.045% -> 1.357% |
| C | 144210 | 0% | 84.92 -> 99.48 | 231.92 -> 248.29 | 7.187% -> 13.847% |

## What the all-branch sweep establishes

### 1. +0.50 EV is a defensible **upper treatment cap**, not a universal treatment constant

All four A/B DARK anchors remain photographically dense at +0.50 EV. None develops a large new finished-highlight area in the tested range.

This makes `+0.50 EV` a defensible **maximum bounded correction seed** for collapsed-dark branches A/B.

It does **not** justify assigning +0.50 to every A/B trigger. `164019` is only a DARK candidate and visually does not require the same rescue certainty as the confirmed failures. Prior project experiments also showed that one fixed alternative does not consistently win every scene.

### 2. Branch C is materially different

`144210` already has a high finished highlight tail before treatment. At +0.50 EV its `Y>=224` area nearly doubles and q95 approaches 248 Y.

For Branch C, the current visual/headroom best-fit range is `+0.25 to +0.35 EV`, with `+0.25 EV` the safer seed.

### 3. `rawHardClipFraction` must not directly determine lift size

`142840` has the largest RAW hard-clip fraction (~1.21%), yet its finished `Y>=224` fraction changes by only ~0.17 percentage points at +0.50 EV. Those highlights were already largely at the endpoint.

Therefore raw clipping is scene evidence, not a direct treatment-strength controller. The useful quantity is the **finished response to additional pre-curve gain**, especially how much of the image is driven toward the upper endpoint.

### 4. Deep black preservation is still intact

Even +0.50 EV does not turn A/B failures into lifted-HDR photographs. Their medians remain low because curve02 preserves the M9-like dense black behavior.

That is desirable. The goal is to rescue edge-case placement without introducing global shadow lifting or replacing the frozen M9 tone curve.

## Provisional treatment architecture

Do not combine classification and treatment into one rule.

```text
BESTFIT1A selector
    HOLD                -> frozen render
    DARK_INTENT         -> bounded treatment policy A
    DARK_ZERO_INTENT    -> bounded treatment policy B
    DARK_FOREGROUND     -> bounded treatment policy C
```

Current **falsification seeds**, not production constants:

- A `DARK_INTENT`: bounded `0 .. +0.50 EV`; current corpus does not yet justify one fixed value.
- B `DARK_ZERO_INTENT`: `+0.50 EV` is the strongest tested best-fit endpoint for both confirmed failures and a useful cap/seed.
- C `DARK_FOREGROUND`: `+0.25 EV` conservative seed, `+0.35 EV` alternate, `+0.50 EV` rejected as unnecessarily expensive to highlight structure on `144210`.

## Important implementation consequence

Branches B/C use finished-render placement features. Therefore a genuine **pre-curve** correction cannot be selected from those features before any rendering has occurred.

If this architecture eventually goes live, the clean quality-preserving implementation is likely an **edge-only two-stage render decision**:

1. produce the frozen baseline render and its placement diagnostics;
2. if BESTFIT selects a DARK branch, rerun only the retained pre-curve/color stage with the bounded branch treatment;
3. publish the corrected JPEG; keep DNG untouched.

This avoids broad exposure-policy changes and leaves all HOLD photographs byte/photographically on the frozen path. The implementation should not be attempted until prospective selector/treatment falsification is stronger.

## Next evidence needed

The current cohort is now exhausted for fitting. The next high-value data are prospective, visually labelled edge cases:

- new zero-intent collapse positives and hard negatives for Branch B;
- new foreground-collapse positives and good bright-sky/foreground negatives for Branch C;
- additional positive-intent collapse examples for Branch A.

Judge the baseline JPEG first, then inspect the selector, then replay only genuine positives. Do not tune thresholds or treatment values to force activation.
