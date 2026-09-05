# M9 EDGEPLACEMENTBESTFIT1A — multi-branch seed audit

**Date:** 2026-09-05  
**Mode:** offline research only  
**Parent:** `m9edgeplacementlift1a-offline2`  
**Photographic baseline:** frozen

## Status

This note records the first `EDGEPLACEMENTBESTFIT1A` multi-branch seed after the 2 PM prospective `EDGEPLACEMENTGATE1A` pass.

No capture or renderer mutation is introduced here. There is still no live lift.

The purpose of this stage is to encode the three observed DARK failure morphologies separately and make them falsifiable on paired capture/PRIMARY telemetry.

## Candidate selector

```text
if INTENT_COLLAPSE:
    DARK_INTENT
elif ZERO_INTENT_COLLAPSE:
    DARK_ZERO_INTENT
elif FOREGROUND_COLLAPSE:
    DARK_FOREGROUND
else:
    HOLD
```

The thresholds below are **provisional falsification seeds**, not production constants.

---

## A — INTENT_COLLAPSE

Preserve the existing Part-3 conjunction:

```text
achievedIntentEv >= +0.10
upperLowerShiftEv >= +1.50
renderCellMedianP75 <= 30
integralRelativeShiftEv <= +0.15
```

This keeps the established separation:

- `164048` DARK_FAIL -> ON
- `164019` DARK_CANDIDATE -> ON
- `164402` GOOD -> OFF
- available Part-3 GOOD / BOUNDARY controls -> OFF in the existing audit

This branch is intentionally left structurally unchanged in BESTFIT1A.

---

## B — ZERO_INTENT_COLLAPSE

The 2 PM zero-intent failures do **not** look like Branch A.

Exact matched region retention, defined as:

```text
retentionEv = log2(render_region_Y / preview_region_Y)
```

for the same 4x6-derived center/lower/upper/edge geometry:

| Frame | Visual class | Center | Lower | Upper | Edge | collapsed <= -1.50 EV |
|---|---|---:|---:|---:|---:|---:|
| 142840 | DARK_FAIL | -1.880 | -2.807 | -2.015 | -2.031 | 4/4 |
| 142939 | DARK_FAIL | -1.735 | -2.481 | -2.084 | -2.518 | 4/4 |
| 143432 | GOOD / mild boundary | -0.150 | -1.350 | -0.329 | -0.519 | 0/4 |
| 143532 | GOOD | -0.059 | -0.779 | -0.080 | -0.328 | 0/4 |
| 144210 | foreground boundary | -0.295 | -1.733 | -0.289 | -0.513 | 1/4 |

That is the important morphology: `142840` and `142939` are **broad structural retention collapse**, not merely low finished luma and not a large upper/lower divergence.

Seed rule:

```text
achievedIntentEv < +0.10
previewSceneSpreadEv >= 1.30
previewBrightRegionFraction >= 0.20
renderCellMedianP75 <= 15
renderGridMeanY <= 30
at least 3 of {center, lower, upper, edge}
    have retentionEv <= -1.50
```

Current exact result:

- `142840` -> ON
- `142939` -> ON
- `143432` -> OFF
- `143532` -> OFF
- `144210` -> OFF

### 084858 hard-negative protection

`084858` is the key dark-but-GOOD zero-intent hard negative.

It predates the full `EDGEPLACEMENTGATE1A` 16x22 finished-grid diagnostic, so exact matched-region retention is not available for this frame.

However the seed branch is forced OFF before that missing geometry matters:

```text
previewSceneSpreadEv = 0.8747   < 1.30
previewBrightRegionFraction = 0.125 < 0.20
```

Its legacy finished-luma sample was still very dark:

```text
global mean   = 33.67
global median = 14
dark <= 64    = 0.845
```

That is precisely why the branch uses **preview structural support + matched collapse**, rather than absolute JPEG darkness.

This is a strong hard-negative guard, but it is not yet a claim of full exact matched-geometry falsification for `084858`.

---

## C — FOREGROUND / SPLIT-FIELD COLLAPSE

Define:

```text
upperLowerShiftEv =
    renderUpperVsLowerEv - previewUpperVsLowerEv
```

Exact 2 PM comparison:

| Frame | Visual class | preview U/L | render U/L | shift | render lower | render P75 |
|---|---|---:|---:|---:|---:|---:|
| 143432 | GOOD / mild boundary | 1.947 | 2.968 | +1.021 | 21.51 | 183.5 |
| 143532 | GOOD | 1.496 | 2.195 | +0.699 | 43.59 | 207.5 |
| 144210 | foreground boundary | 2.161 | 3.605 | **+1.444** | **13.75** | 161.75 |

This confirms that absolute finished upper/lower separation is not enough. `143432` can finish at nearly 3 EV and remain photographically acceptable.

Seed rule:

```text
upperLowerShiftEv >= +1.20
renderLower12Y <= 18
renderUpper6Y >= 140
renderCellMedianP75 >= 120
centerRetentionEv >= -1.00
```

Current exact result:

- `144210` -> ON as `DARK_FOREGROUND`
- `143432` -> OFF
- `143532` -> OFF
- `142840` / `142939` -> OFF

There is deliberately **no achieved-intent prerequisite** in this branch. The morphology is spatial finished-placement loss with healthy upper/high support, not a specific capture-assist state.

---

## Why the three branches remain separate

The current anchors now occupy different parts of feature space:

- `164048`: positive intent + strong preview->render split growth + low global body placement.
- `142840` / `142939`: zero intent + 4/4 broad matched-region collapse + low finished body.
- `144210`: center and upper field survive, while the lower field loses much more placement.

Trying to merge these into one threshold would either lose recall or start lifting legitimate dark M9-like photographs.

---

## Research tool

`m9edgeplacementbestfit1a_multibranch.py` implements the seed classifier against a paired:

```text
*_M9.json
*_M9_PRIMARY.json
```

It emits only diagnostic JSON.

It explicitly reports:

```text
liveLiftEnabled = false
```

and contains no rendering/capture write path.

---

## Current acceptance status

### Passed at seed level

- original Part-3 INTENT_COLLAPSE separation retained
- `142840` ZERO_INTENT -> ON
- `142939` ZERO_INTENT -> ON
- `084858` hard-negative -> OFF through preview low-key guard
- `144210` FOREGROUND -> ON
- `143432` -> OFF
- `143532` -> OFF

### Not yet passed

- full GOOD-control sweep with exact `EDGEPLACEMENTGATE1A` geometry
- exact same-schema matched-retention test for `084858`
- full boundary sweep (`084154`, `163702`, etc.) under the new B/C branches
- opposite-tail BRIGHT_FAIL audit
- visual treatment-strength replay

Therefore **no live lift is authorized**.

---

## Next falsification

1. Run the offline script over every available exact diagnostic M9/PRIMARY pair.
2. Record any GOOD/BORDERLINE activations before adjusting thresholds.
3. Keep Branch A frozen while falsifying B and C.
4. Only after selector coverage is credible, perform research-only pre-curve lift replay:
   - Frozen
   - +0.15 EV
   - +0.25 EV
   - +0.35 EV
   - +0.50 EV research-only for the severe zero-intent anchors
5. Do not add renderer mutation until a separate explicit promotion decision.
