# M9 EDGEPLACEMENT BESTFIT1A — BRIGHT_LOWKEY_BROAD FULL47 1A

Research-only prospective closure. No live APK, capture policy, TC20, curve02, color science, JPEG quality, DNG, or frozen-renderer change.

## Question

Does the conjunction of the existing coherent-low-key morphology and the new renderer-response corroborator leak across the complete September-5 natural cohort?

```text
LOWKEY_BROAD1A =
    BRIGHT_LOWKEY_OPENING1A
    AND BRIGHT_BROADOPENING1A
```

Existing LOWKEY seed:

```text
achievedIntentEv < +0.10
AND structuralLowKeyScore >= 0.60
AND tc20Gain >= 1.50
AND finishedGlobalMedianY >= 75
```

BROADOPENING:

```text
medianShiftEv = log2(finishedGlobalMedianY / previewGlobalMedianY)
q95ShiftEv    = log2(finishedGlobalQ95Y / previewGlobalQ95Y)

BROADOPENING = medianShiftEv > 0 AND q95ShiftEv > 0
```

## Full47 reduction

The complete untouched 47-frame cohort has only two BROADOPENING positives:

```text
181404
181559
```

Therefore no BROAD_OFF frame can satisfy `LOWKEY_BROAD1A`; the full conjunction can be closed by auditing LOWKEY only on these two survivors rather than fitting or scanning another response threshold.

### 181404 — BROAD positive, LOWKEY negative

`IMG_20260905_181404_1788628444407_00`

- preview global median = 78Y
- preview global q95 = 192Y
- finished global median = 82Y
- finished global q95 = 196Y
- median shift = +0.072 EV
- q95 shift = +0.030 EV
- `BROADOPENING = ON`
- `structuralLowKeyScore = 0.5447914875`
- TC20 applied gain ~2.554x
- finished median 82Y
- visual status: `BOUNDARY_HOLD`, Frozen acceptable

The existing LOWKEY structural floor rejects it independently:

```text
0.5447914875 < 0.60
LOWKEY = OFF
LOWKEY_BROAD1A = OFF
```

No BROAD magnitude threshold is needed.

### 181559 — BROAD positive, LOWKEY positive

`IMG_20260905_181559_1788628559798_00`

- preview global median = 66Y
- preview global q95 = 141Y
- finished global median = 82Y
- finished global q95 = 161Y
- median shift = +0.313 EV
- q95 shift = +0.191 EV
- `BROADOPENING = ON`
- `structuralLowKeyScore = 0.876096`
- TC20 gain = 2.0633145986x
- TC20 guard gain = 3.7034552846x
- achieved intent is below the +0.10-EV LOWKEY limit in the retained prospective audit
- finished median = 82Y
- visual status: `NATURAL_MILD`; mild RGB-pivot treatment positive

Therefore:

```text
LOWKEY = ON
BROADOPENING = ON
LOWKEY_BROAD1A = ON
```

## Prospective result

```text
47 natural frames
 2 BROADOPENING positives
 1 LOWKEY_BROAD1A positive
46 LOWKEY_BROAD1A off by conjunction
```

The sole prospective conjunction-positive is `181559`.

This is not the same thing as claiming `181559` must always be treated. It means it is the sole frame in this cohort that simultaneously exhibits:

1. the pre-render coherent low-key morphology associated with the historical LOWKEY BRIGHT mechanism; and
2. actual finished-image opening across both global body and upper-body.

Treatment/severity remains a later decision.

## Important nearby control

`181247` demonstrates why structural LOWKEY alone is not sufficient.

- preview global median = 64Y
- preview q95 = 151Y
- `structuralLowKeyScore = 0.914464`
- TC20 applied gain ~1.584x, base median gain ~6.646x, guard-limited
- finished global median = 17Y
- finished global q95 = 66Y

This frame has very strong low-key morphology but the renderer makes it dramatically denser rather than opening it. It fails the LOWKEY seed's finished-median requirement and is also BROADOPENING OFF.

That is useful independent evidence for keeping morphology, actual renderer response, and treatment severity separate.

## What is now falsified prospectively

The following are not sufficient BRIGHT treatment triggers:

- low preview median alone;
- high `structuralLowKeyScore` alone;
- high TC20/base-median gain alone;
- finished median alone;
- positive center movement alone;
- positive q95 movement alone;
- BROADOPENING alone (`181404` HOLD);
- the failed MIDKEY seed.

The current best-supported LOWKEY path is the conjunction, not any one scalar.

## Current architecture

```text
BRIGHT structural family
        ↓
LOWKEY morphology?
        │
        ├─ NO -> HOLD / other independently justified BRIGHT morphology
        │
        └─ YES
             ↓
      BROADOPENING?
        │
        ├─ NO -> HOLD / retained-density evidence
        │
        └─ YES
             ↓
       treatment eligibility
             ↓
     photographic severity / HOLD
             ↓
     RGB015 first mild candidate
     RGB025 only if justified
             ↓
   finished-response safety / rollback
```

## Status

`BRIGHT_LOWKEY_BROAD1A` has passed the complete 47-frame prospective conjunction audit with **1/47 activation** and no activation on the known `181404` HOLD boundary.

It remains research-only. Do not promote live yet.

The next independent falsifier is historical response recovery:

- recover exact preview/finished global q95 pairs for `184927`, `184937`, `194307`;
- recover the same for `190401` as the Frozen/HOLD control;
- do not force second-morphology frames `190346` or `190429` to satisfy LOWKEY_BROAD1A;
- then run another untouched prospective cohort before any live consideration.
