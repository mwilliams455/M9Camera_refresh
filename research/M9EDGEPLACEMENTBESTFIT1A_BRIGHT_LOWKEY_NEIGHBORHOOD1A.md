# M9 EDGEPLACEMENT BESTFIT1A — BRIGHT LOWKEY NEIGHBORHOOD1A

Research-only. No live APK, capture, TC20, renderer, DNG, curve02, color science, or JPEG-quality changes.

## Purpose

Test whether prospective `181559` is merely one of many ordinary dark/woodland frames that happen to have a high `structuralLowKeyScore`, or whether the existing `BRIGHT_LOWKEY_OPENING1A` conjunction isolates a more specific opened-low-key state.

Current research-only seed:

```text
achievedIntentEv < +0.10
AND structuralLowKeyScore >= 0.60
AND tc20Gain >= 1.50
AND finishedGlobalMedianY >= 75
```

## Immediate temporal neighborhood

### 181125

- structuralLowKeyScore ~0.9163
- TC20 gain ~1.0134
- base median request ~8.2078
- physical/tail guard ~1.0134
- finished global median 6 Y

Result: **OFF**.

This is a strong low-key preview but the renderer is guard-limited and remains very dark. It is not an opened-low-key BRIGHT case.

### 181138

- structuralLowKeyScore = 0
- preview has strong spatial/highlight separation

Result: **OFF** before treatment context.

### 181527

- structuralLowKeyScore ~0.8234
- TC20 gain ~1.1192
- base median request ~15.5168
- guard ~1.1192
- finished global median 2 Y

Result: **OFF**.

Again the structural score alone is high, but the frame remains very dark rather than being normalized open.

### 181559

Retained prospective candidate:

- structuralLowKeyScore ~0.8761
- TC20 gain ~2.063
- achieved intent approximately 0 EV
- finished global median ~82 Y
- Frozen visually acceptable but mild extra density preferred in exact blind replay
- mild-bank preference: RGB015 or RGB025

Result: **ON**.

### 181623

- structuralLowKeyScore ~0.972
- TC20 gain ~1.5415
- base median request ~7.6741
- guard ~1.5415
- finished global median 14 Y

Result: **OFF** on finished body.

This is especially useful because score and TC20 gain both exceed the low-key activation floors, but the result never becomes an opened generic mid-key JPEG. The finished-body term correctly prevents BRIGHT treatment.

## Interpretation

The immediate neighborhood supports the semantic role of `LOWKEY_OPENING1A`:

```text
high structuralLowKeyScore alone          != BRIGHT failure
high score + some TC20 gain               != BRIGHT failure
low-key scene that remains dense          -> HOLD / not BRIGHT
low-key scene opened into ~ordinary body  -> BRIGHT_LOWKEY candidate
```

The conjunction is therefore doing materially more than detecting darkness or woodland content.

The current evidence does NOT yet prove production readiness. It is one local prospective neighborhood, not a broad natural falsification cohort.

## Treatment implication

The exact mild-bank result for `181559` supports a natural-mild candidate bank:

```text
RGB015 / RGB025
```

Do not infer that all historical severe LOWKEY BRIGHT_FAIL anchors should be capped to 0.25. Historical blind review still supports 0.50-0.75 on some confirmed severe cases.

## Next development

1. Preserve the current LOWKEY eligibility conjunction unchanged.
2. Continue looking for independent natural LOWKEY_OPENING activations in later cohorts.
3. For each activation, classify Frozen first.
4. If Frozen is genuinely a little too open, test exact RGB015/RGB025/RGB035.
5. Keep severe BRIGHT strength selection unresolved and separate.
6. Do not revive or promote the failed MIDKEY scalar branch from the 173828 side-by-side preference.
