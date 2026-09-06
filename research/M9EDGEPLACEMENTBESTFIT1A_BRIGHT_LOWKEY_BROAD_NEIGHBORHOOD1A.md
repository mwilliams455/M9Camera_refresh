# M9 EDGEPLACEMENT BESTFIT1A — BRIGHT LOWKEY/BROAD NEIGHBORHOOD1A

Research-only local ablation around the sole September-5 `LOWKEY_BROAD1A` prospective activation. No live APK or photographic-path change.

## Purpose

Challenge the idea that `181559` is being isolated by one arbitrary threshold. Inspect nearby natural frames that independently challenge the LOWKEY terms and the BROAD response requirement.

The active research seed remains:

```text
LOWKEY =
    achievedIntentEv < +0.10
    AND structuralLowKeyScore >= 0.60
    AND tc20Gain >= 1.50
    AND finishedGlobalMedianY >= 75

BROAD =
    medianShiftEv > 0
    AND q95ShiftEv > 0

LOWKEY_BROAD1A = LOWKEY AND BROAD
```

## Nearby natural frames

| Frame | structuralLowKeyScore | TC20 applied gain | finished global median | BROAD | decisive observation |
|---|---:|---:|---:|---|---|
| 181247 | 0.914464 | 1.5844x | 17Y | OFF | strong low-key morphology, but renderer becomes dramatically denser |
| 181404 | 0.544791 | ~2.554x | 82Y | ON | genuine small opening, but morphology is below existing 0.60 floor; visual HOLD |
| 181423 | 0.808704 | 1.4461x | — | OFF | coherent low-key morphology, but applied TC20 gain is below existing 1.50 floor |
| 181527 | 0.823406 | 1.1192x | — | OFF | coherent low-key morphology, but applied TC20 gain is far below existing 1.50 floor |
| **181559** | **0.876096** | **2.0633x** | **82Y** | **ON** | sole full47 conjunction-positive; mild treatment-positive |
| 181623 | 0.972000 | 1.5415x | 14Y | OFF | even stronger low-key morphology than 181559, but renderer preserves/creates dense placement rather than opening |

`BROAD OFF` for the listed non-181404/181559 frames follows from the already-closed complete 47-frame BROADOPENING audit, in which only 181404 and 181559 were positive.

Intent is not silently inferred for frames already rejected by another required term; no zero-intent assumption is needed to establish their OFF status.

## What this falsifies

### `structuralLowKeyScore` alone is not authority

`181247` and `181623` have scores **higher** than `181559`, yet finish at 17Y and 14Y respectively. Dark-scene morphology alone would incorrectly target already-dense M9-like rendering.

### TC20 gain alone is not authority

`181404` has an applied gain larger than `181559` yet is a visual HOLD boundary. Gain cannot be a severity map.

### Finished body level alone is not authority

`181404` and `181559` both finish near 82Y, but only 181559 satisfies the coherent LOWKEY morphology and visual mild-treatment evidence.

### BROADOPENING alone is not authority

Again, `181404` is the direct counterexample.

### Stronger LOWKEY score does not imply stronger correction

The local ordering is explicitly non-monotonic:

```text
181623 score .972 -> finished median 14 -> HOLD / dense response
181247 score .914 -> finished median 17 -> HOLD / dense response
181559 score .876 -> finished median 82 -> mild treatment-positive
181404 score .545 -> finished median 82 -> HOLD boundary
```

Therefore do not map structural score to RGB-pivot strength.

## Why the conjunction is behaving sensibly

The terms are answering different questions:

```text
structuralLowKeyScore >= .60
    -> does the preview resemble the coherent low-key morphology?

TC20 gain >= 1.50
    -> did normalization apply enough gain to make opening plausible?

finished median >= 75
    -> did the final body actually reach an ordinary/open body key?

median + q95 both positive
    -> did body and upper-body move upward together from preview to finished output?
```

No one term carries the treatment decision.

The local neighborhood is therefore evidence **against simplifying** LOWKEY_BROAD1A into any single scalar rule.

## Current conclusion

The September-5 local sequence strengthens the current conservative architecture:

```text
morphology
  AND normalization plausibility
  AND sufficiently open finished body
  AND actual broad opening response
          ↓
   treatment eligibility only
          ↓
   photographic severity / HOLD
          ↓
   bounded mild RGB pivot
```

Do not tune the 0.60 score floor, 1.50 gain floor, 75Y finished-body floor, or a new BROAD magnitude cutoff from this neighborhood. Their current value is as a falsification seed, not a fitted production classifier.

## Status

Prospective LOWKEY/BROAD evidence is now stronger, but still research-only. Historical response recovery and another untouched prospective cohort remain required before live consideration.
