# M9 EDGEPLACEMENT BESTFIT1A — BRIGHT LOWKEY COHORT1A

Research-only. No live APK, capture policy, TC20, renderer, curve02, color science, JPEG quality, or DNG changes.

## Purpose

Close the untouched 2026-09-05 17:29–18:27 prospective cohort against the existing `BRIGHT_LOWKEY_OPENING1A` seed without threshold retuning.

Existing provisional seed, unchanged:

```text
achievedIntentEv < +0.10
AND structuralLowKeyScore >= 0.60
AND tc20Gain >= 1.50
AND finishedGlobalMedianY >= 75
```

Threshold status remains `provisional_falsification_seed_not_frozen_not_live`.

## Cohort result

- untouched prospective frames: **47**
- structural-score-qualified frames (`score >= 0.60`): **12/47**
- full LOWKEY activations: **1/47**
- sole activation: **IMG_20260905_181559_1788628559798_00**

This is substantially more selective than `structuralLowKeyScore` by itself. Eleven structurally low-key frames were rejected by the TC20-gain and/or finished-body terms.

## Score-qualified frames

| Frame | structuralLowKeyScore | TC20 gain | finished median Y | LOWKEY result | decisive interpretation |
|---|---:|---:|---:|---|---|
| 173159 | ~0.6017 | ~2.4038 | 41 | OFF | gain qualifies; finished body stayed dense |
| 174327 | ~0.8761 | ~4.3178 | 39 | OFF | score essentially matches 181559; finished body stayed dense |
| 174410 | ~0.9145 | ~1.4235 | 7 | OFF | gain below seed and body dense |
| 174524 | ~0.8758 | ~1.4461 | 7 | OFF | gain below seed and body dense |
| 175630 | ~0.9586 | ~1.0872 | 6 | OFF | strong low-key structure but almost no opening |
| 181125 | ~0.9163 | ~1.0134 | 6 | OFF | strong low-key structure but almost no opening |
| 181247 | ~0.9145 | ~1.5844 | 17 | OFF | gain qualifies; finished body stayed dense |
| 181300 | ~0.9314 | ~1.3825 | 13 | OFF | gain below seed and body dense |
| 181423 | ~0.8087 | ~1.4461 | 17 | OFF | gain below seed and body dense |
| 181527 | ~0.8234 | ~1.1192 | 2 | OFF | strong low-key structure but almost no opening |
| **181559** | **~0.876** | **~2.06** | **~82** | **ON** | coherent low-key scene opened into a generic mid-body region |
| 181623 | ~0.9720 | ~1.5415 | 14 | OFF | gain qualifies; finished body stayed dense |

## Dangerous controls

The original prospective MIDKEY false activations `173342` and `173423` both have `structuralLowKeyScore = 0`, so LOWKEY does not inherit the failed MIDKEY scalar morphology.

The late high-key / clipped controls `182012`, `182032`, `182039`, and `182756` are also score-OFF in this cohort. They do not leak into LOWKEY despite bright or clipped upper-field structure.

`173828`, which looked acceptable Frozen in isolation and later preferred only a very mild RGB015 density change in exact side-by-side review, has `structuralLowKeyScore = 0`; it is not a LOWKEY activation and therefore remains an important example of aesthetic preference not implying correction eligibility.

## Exact prospective treatment evidence for 181559

`181559` is not a severe BRIGHT_FAIL. Exact-pixel blind review narrowed its preferred region to:

```text
Frozen  ~= acceptable / near-tie
RGB015  ~= preferred contender
RGB025  ~= preferred contender
RGB035  = no longer preferred once the mild range was resolved
```

User review explicitly noted that increasing darkness eventually loses the M9 character. Therefore the prospective LOWKEY result currently supports a **NATURAL_MILD** treatment class, not automatic use of the historical severe BRIGHT bank.

## Current interpretation

The useful semantic conjunction is not:

```text
low-key scene -> darken
```

It is closer to:

```text
coherent low-key preview
AND meaningful TC20 opening
AND finished JPEG lands in an opened mid-body region
-> prospective LOWKEY_OPENING candidate
```

The finished-body term is currently essential. Several controls have structural scores equal to or stronger than `181559`, and some have larger TC20 gains, yet remain correctly OFF because their finished JPEGs retain dense placement.

Do **not** tighten `structuralLowKeyScore` around the 181559 value. `174327` demonstrates why score magnitude is not a severity or eligibility oracle.

## Development status

Current research architecture:

```text
Frozen render
  -> BRIGHT subtype eligibility
     -> HOLD
     -> LOWKEY_OPENING / NATURAL_MILD
          -> RGB015 / RGB025 research bank
          -> RGB035 upper stress bound only
     -> confirmed severe BRIGHT_FAIL
          -> historical RGB035 / RGB050 / RGB075 research bank
          -> no automatic strength mapping yet
```

No live treatment is authorized.

## Next falsification

1. Keep the current APK/frozen renderer unchanged.
2. Run the same unchanged LOWKEY seed prospectively on a later independent natural batch.
3. Visually inspect Frozen first for every activation.
4. Only if Frozen is genuinely a little too open, expose RGB015/RGB025 (RGB035 only as an upper bound).
5. Require another independent treatment-positive LOWKEY activation before considering production promotion.
6. Continue to treat `181559` as the sole prospective positive in this 47-frame cohort, not sufficient by itself for a live rule.

Priority remains zero GOOD false corrections and preservation of normal M9 rendering.
