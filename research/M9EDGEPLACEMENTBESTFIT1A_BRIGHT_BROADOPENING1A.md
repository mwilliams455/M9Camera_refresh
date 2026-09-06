# M9 EDGEPLACEMENT BESTFIT1A — BRIGHT_BROADOPENING1A

Research-only. No live APK, capture policy, TC20, curve02, color science, JPEG quality, or frozen renderer change.

## Purpose

Define a renderer-response diagnostic that asks a narrower question than BRIGHT eligibility:

> Did the finished JPEG actually open both the scene body and upper-body relative to the captured preview structure?

This is not a selector for whether a photograph should be darkened. It is mechanism evidence only.

## Diagnostic definition

For the same frame, compare preview and finished global luma percentiles:

```text
medianShiftEv = log2(finishedGlobalMedianY / previewGlobalMedianY)
q95ShiftEv    = log2(finishedGlobalQ95Y / previewGlobalQ95Y)

BRIGHT_BROADOPENING1A =
    medianShiftEv > 0
    AND q95ShiftEv > 0

broadOpeningMinEv = min(medianShiftEv, q95ShiftEv)
```

The conjunction is intentional. Positive median alone can occur while the upper body becomes denser; positive q95 alone can occur from upper-tail redistribution while the body becomes much denser.

`broadOpeningMinEv` is retained as a descriptive magnitude only. It is not a treatment-strength mapping and has no frozen threshold.

## Why median + q95

Existing prospective and control evidence repeatedly shows four response shapes:

```text
median - / q95 -  -> broadly denser
median - / q95 +  -> upper-tail redistribution, not broad opening
median + / q95 -  -> body opening without upper-body agreement
median + / q95 +  -> broad opening across body and upper-body
```

The fourth pattern is the one this diagnostic records.

Center movement is deliberately excluded from authority. Known GOOD/HOLD frames can show strong positive center movement even when the global body becomes denser, so center response remains diagnostic context only.

## Prospective separation

The four frames that activated the failed prospective `BRIGHT_MIDKEY_NORMALIZATION1A` seed divide cleanly under this response diagnostic:

| Frame | median shift | q95 shift | BROADOPENING |
|---|---:|---:|---|
| 173342 | -0.759 EV | -0.342 EV | OFF |
| 173423 | -0.936 EV | -0.360 EV | OFF |
| 173828 | -0.402 EV | -0.031 EV | OFF |
| 181559 | +0.313 EV | +0.191 EV | ON |

This explains why the earlier MIDKEY conjunction failed: it grouped photographs that did not share the same renderer-response behavior.

`173828` can still be aesthetically improvable under a very mild RGB pivot treatment, but it is not a renderer broad-opening failure. Aesthetic preference and placement failure must remain separate.

## Key boundary pair

The complete September-5 natural cohort leaves two BROADOPENING positives:

| Frame | median shift | q95 shift | broadOpeningMinEv | visual outcome |
|---|---:|---:|---:|---|
| 181404 | +0.072 EV | +0.030 EV | +0.030 EV | `BOUNDARY_HOLD`, Frozen |
| 181559 | +0.313 EV | +0.191 EV | +0.191 EV | `NATURAL_MILD`, RGB015/RGB025 treatment-positive |

This pair is the central caution:

```text
BROADOPENING detected
    != mandatory treatment
```

`181404` proves that small, genuine broad opening can still be photographically acceptable and should remain Frozen.

## Current architecture

```text
BRIGHT structural eligibility / morphology
        ↓
renderer-response corroboration
        ↓
BRIGHT_BROADOPENING1A ?
        │
        ├─ NO -> strong HOLD / retained-density evidence
        │
        └─ YES -> genuine opening mechanism
                     ↓
              photographic severity
                     ↓
              HOLD or treatment
                     ↓
           bounded RGB-pivot candidate
                     ↓
          finished-response safety / rollback
```

For LOWKEY specifically, this supports:

```text
LOWKEY morphology
    -> BROADOPENING response check
    -> photographic severity / HOLD decision
    -> RGB015 first mild candidate
    -> RGB025 escalation only if visually justified
    -> larger legacy 0.35/0.50/0.75 strengths remain historical stress/treatment bank, not defaults
```

## What this diagnostic must not become

Do not:

- map `broadOpeningMinEv` directly to treatment strength;
- place a live cutoff between 181404 and 181559 from only two points;
- use center movement as a replacement;
- widen MIDKEY around this response feature;
- retune TC20 or capture exposure globally;
- treat aesthetic mild-density preference as proof of renderer failure.

## Status

`BRIGHT_BROADOPENING1A` is a promising research-only renderer-response corroborator.

It has survived the complete September-5 47-frame natural cohort plus independent controls without broad leakage, but it is not production logic. The next requirement is independent historical/retrospective falsification across confirmed BRIGHT_FAIL and HOLD/GOOD anchors, followed by another prospective cohort before any live consideration.
