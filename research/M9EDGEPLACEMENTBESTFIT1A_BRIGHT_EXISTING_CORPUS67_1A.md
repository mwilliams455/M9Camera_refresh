# M9 EDGEPLACEMENT BESTFIT1A — BRIGHT EXISTING CORPUS67 1A

Research-only corpus closure. No live APK, capture policy, TC20, renderer, curve02, color science, JPEG quality, or DNG change.

## Why this note exists

The project had begun repeatedly asking for another natural-shooting cohort even though the recent September-5 material had not been exhausted. That was the wrong development order.

The correct next step is to treat the already-retained September-5 diagnostic material as the prospective evidence base and score it completely before requesting any more photographs.

## Existing September-5 corpus

Dropbox `/chatgpt/m9/exposure` contains 67 complete diagnostic-bundle files for the current diagnostic build, naturally divided into three groups:

```text
13-frame morning/control group
 7-frame middle edge-placement group
47-frame late-afternoon untouched natural group
----------------------------------------------
67 total diagnostic bundles
```

The 7-frame middle group was the previously under-exploited gap. It contains:

- 142840
- 142939
- 143018
- 143027
- 143432
- 143532
- 144210

These are useful cross-tail controls because the set contains DARK failures, GOOD/boundary frames, and highly asymmetric bright-tail responses.

## Frozen BRIGHT research rules

### LOWKEY morphology / normalization seed

```text
BRIGHT_LOWKEY_OPENING1A =
    achievedIntentEv < +0.10
    AND structuralLowKeyScore >= 0.60
    AND appliedTc20Gain >= 1.50
    AND finishedGlobalMedianY >= 75
```

`appliedTc20Gain` means the renderer's actual `gain`, not `baseMedianGain`.

### BROADOPENING corroborator

```text
medianShiftEv = log2(finishedGlobalMedianY / previewGlobalMedianY)
q95ShiftEv    = log2(finishedGlobalQ95Y / previewGlobalQ95Y)

BRIGHT_BROADOPENING1A =
    medianShiftEv > 0
    AND q95ShiftEv > 0
```

### Current conjunction

```text
BRIGHT_LOWKEY_BROAD1A =
    BRIGHT_LOWKEY_OPENING1A
    AND BRIGHT_BROADOPENING1A
```

This is mechanism/treatment-eligibility evidence only. It is not mandatory treatment and it does not choose correction strength.

## Middle 7 — newly closed cross-tail audit

| frame | preview median / q95 | finished median / q95 | BROAD | structuralLowKeyScore | LOWKEY |
|---|---:|---:|---|---:|---|
| 142840 | 64 / 201 | 2 / 138 | OFF | 0 | OFF |
| 142939 | 65 / 196 | 4 / 91 | OFF | 0 | OFF |
| 143018 | 204 / 219 | 100 / 166 | OFF | 0 | OFF |
| 143027 | 91 / 219 | 24 / 229 | OFF | 0 | OFF |
| 143432 | 106 / 219 | 72 / 219 | OFF | 0 | OFF |
| 143532 | 93 / 221 | 60 / 239 | OFF | 0 | OFF |
| 144210 | 77 / 223 | 34 / 232 | OFF | 0 | OFF |

### Cross-tail implication

Several middle-group frames show **q95 increasing while the global body becomes substantially denser**:

```text
143027: 91 -> 24 body, q95 219 -> 229
143532: 93 -> 60 body, q95 221 -> 239
144210: 77 -> 34 body, q95 223 -> 232
```

Therefore positive q95 movement by itself is not BRIGHT opening evidence. The body + upper-body sign agreement in BROADOPENING is doing real safety work.

All seven have `structuralLowKeyScore = 0`, so the LOWKEY branch rejects them independently. This is useful cross-tail safety evidence: the BRIGHT selector does not leak into these known DARK/GOOD/boundary edge-placement cases.

## Combined September-5 result

### BROADOPENING

```text
morning 13 : 0 / 13 BROAD_POSITIVE
middle   7 : 0 / 7  BROAD_POSITIVE
late    47 : 2 / 47 BROAD_POSITIVE
---------------------------------
total   67 : 2 / 67 BROAD_POSITIVE
```

The only two BROAD positives in the entire retained September-5 bundle corpus are:

```text
181404
181559
```

### LOWKEY_BROAD

`181404` remains the HOLD boundary:

```text
preview median / q95  = 78 / 192
finished median / q95 = 82 / 196
BROAD                  = ON
structuralLowKeyScore  = ~0.5448
LOWKEY                 = OFF
LOWKEY_BROAD           = OFF
visual status          = HOLD / Frozen acceptable
```

`181559` remains the sole conjunction-positive:

```text
preview median / q95  = 66 / 141
finished median / q95 = 82 / 161
BROAD                  = ON
structuralLowKeyScore  = 0.876096
applied TC20 gain      = 2.0633x
achieved intent        ~= 0
LOWKEY                 = ON
LOWKEY_BROAD           = ON
visual status          = natural-mild treatment-positive
preferred mild range   = RGB015 / RGB025
```

Therefore:

```text
67 retained September-5 diagnostic frames
 2 BROAD positives
 1 LOWKEY_BROAD positive
66 LOWKEY_BROAD OFF
```

The sole September-5 `LOWKEY_BROAD1A` activation remains `181559`.

## What the 67-frame corpus now falsifies

The existing corpus directly argues against using any of these as standalone BRIGHT authority:

- low preview median;
- high preview q95;
- positive q95 movement;
- high structuralLowKeyScore;
- high TC20/base-median gain;
- open finished median;
- center opening;
- BROADOPENING alone;
- the failed MIDKEY seed.

The best-supported LOWKEY path remains the conjunction of pre-render morphology and actual broad renderer opening, followed by a separate photographic HOLD/severity decision.

## Treatment remains separate

The natural-mild evidence remains:

```text
173828 -> Frozen acceptable in isolation; RGB015 preferred side-by-side
          => HOLD in an automatic system, not a BRIGHT failure

181404 -> BROAD positive but LOWKEY negative; Frozen acceptable
          => HOLD

181559 -> LOWKEY_BROAD positive; mild treatment-positive
          => RGB015 first, RGB025 escalation only
```

Do not infer a correction-strength formula from structural score, TC20 gain, finished median, or BROAD magnitude.

## Development order after CORPUS67

Do not request another generic set of the same photographs.

Before any new capture request:

1. join all existing visual labels to the 67-frame corpus where identities are already known;
2. identify any unlabeled BROAD or LOWKEY near-miss that merits visual review;
3. recover any retained historical BRIGHT sidecars/percentiles for 184927, 184937, 194307, and the 190401 HOLD control if they still exist in project files/repo/history;
4. compare historical LOWKEY treatment positives against the current mechanism without inventing missing q95 values;
5. only request new shooting if a specific, genuinely missing morphology remains after the retained corpus is exhausted.

## Status

`CORPUS67_1A`: existing-data prospective corpus closed at cohort level.

```text
BROADOPENING : 2 / 67
LOWKEY_BROAD : 1 / 67
```

No live promotion follows. No APK change follows. The next work is evidence consolidation and historical recovery, not another repetition of the same capture request.
