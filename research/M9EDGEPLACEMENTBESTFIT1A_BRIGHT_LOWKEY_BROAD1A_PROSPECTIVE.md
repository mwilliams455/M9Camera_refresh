# M9 EDGEPLACEMENT BESTFIT1A — BRIGHT_LOWKEY_BROAD1A PROSPECTIVE

Research-only. No live APK, capture, TC20, curve02, color, JPEG-quality, or DNG mutation.

## Question

Can the prospective BRIGHT evidence be made safer without fitting a new numeric severity threshold between the two BROADOPENING-positive frames?

The test combines two independently motivated dimensions:

1. **pre-render structural morphology** — `BRIGHT_LOWKEY_OPENING1A`; and
2. **post-render response corroboration** — `BRIGHT_BROADOPENING1A`.

The conjunction is diagnostic only:

```text
LOWKEY_BROAD1A =
    BRIGHT_LOWKEY_OPENING1A
    AND BRIGHT_BROADOPENING1A
```

No new scalar cutoff is introduced.

## Existing LOWKEY seed

```text
achievedIntentEv < +0.10
AND structuralLowKeyScore >= 0.60
AND tc20Gain >= 1.50
AND finishedGlobalMedianY >= 75
```

## BROADOPENING corroborator

```text
medianShiftEv = log2(finishedGlobalMedianY / previewGlobalMedianY)
q95ShiftEv    = log2(finishedGlobalQ95Y / previewGlobalQ95Y)

BROADOPENING = medianShiftEv > 0 AND q95ShiftEv > 0
```

## Prospective boundary pair

### 18:14:04 — HOLD boundary

`IMG_20260905_181404_1788628444407_00`

Observed preview structure:

- preview global median = 78Y
- preview global q95 = 192Y
- `structuralLowKeyScore = 0.5447914875`

Renderer response:

- median shift = approximately `+0.072 EV`
- q95 shift = approximately `+0.030 EV`
- therefore `BROADOPENING = ON`

Visual/treatment status:

- `BOUNDARY_HOLD`
- Frozen remains photographically acceptable

Crucially, this frame does **not** pass the existing LOWKEY structural floor because `0.5448 < 0.60`.

Therefore:

```text
LOWKEY = OFF
BROADOPENING = ON
LOWKEY_BROAD1A = OFF
```

This excludes the HOLD boundary without inventing a BROAD magnitude cutoff between +0.030 and +0.191 EV.

### 18:15:59 — mild treatment-positive

`IMG_20260905_181559_1788628559798_00`

Observed preview structure:

- preview global median = 66Y
- preview global q95 = 141Y
- `structuralLowKeyScore = 0.876096`
- TC20 gain/base median gain = `2.0633145986`
- TC20 guard gain = `3.7034552846`
- median-limited

Finished response:

- finished global median = 82Y
- finished global q95 = 161Y
- median shift = approximately `+0.313 EV`
- q95 shift = approximately `+0.191 EV`
- therefore `BROADOPENING = ON`

The frame independently satisfies the LOWKEY seed and was visually treatment-positive only at mild density strengths.

Therefore:

```text
LOWKEY = ON
BROADOPENING = ON
LOWKEY_BROAD1A = ON
```

## Why this is preferable to a two-point severity threshold

A tempting rule would be to choose a `broadOpeningMinEv` threshold somewhere between the HOLD frame (`+0.030`) and mild-positive frame (`+0.191`). That would be direct two-point overfit.

The conjunction above does something different:

```text
scene morphology says this is a coherent low-key normalization risk
AND
finished response confirms the renderer actually opened body + upper body
```

The two tests come from different evidence domains and neither is derived by numerically splitting 181404 from 181559.

## Historical compatibility — not yet closed

The existing historical LOWKEY treatment-positive anchors remain:

- 184927 — structuralLowKeyScore ~0.732, TC20 gain ~2.63
- 184937 — structuralLowKeyScore ~0.625, TC20 gain ~1.60
- 194307 — structuralLowKeyScore 1.0, TC20 gain ~4.94

The known Frozen/withhold anchor `190401` has structuralLowKeyScore ~0.506 and is already excluded by the LOWKEY structural floor.

However exact historical preview-global q95 and finished-global q95 values have not yet been recovered on the current branch/source set, so historical BROADOPENING status must **not** be invented. The next historical test is to recover those exact percentile pairs and replay the conjunction.

## Current interpretation

Prospective evidence now supports this research architecture:

```text
LOWKEY morphology
       │
       ├─ OFF -> HOLD / other BRIGHT morphology
       │
       └─ ON
            ↓
     BROADOPENING?
       │
       ├─ OFF -> HOLD / retained-density evidence
       │
       └─ ON
            ↓
    treatment eligibility
            ↓
      severity remains separate
            ↓
     RGB015 first mild candidate
     RGB025 only if justified
            ↓
   finished-response safety/rollback
```

This is still **eligibility, not mandatory treatment**. Frozen remains valid whenever the visual/severity stage does not justify intervention.

## Status

`BRIGHT_LOWKEY_BROAD1A`: promising prospective conjunction, research-only, no live promotion.

Next requirements:

1. complete the entire 47-frame LOWKEY activation inventory rather than relying only on the boundary pair;
2. recover historical q95 pairs for 184927/184937/194307 and the 190401 HOLD control;
3. run another untouched prospective cohort before considering live logic.
