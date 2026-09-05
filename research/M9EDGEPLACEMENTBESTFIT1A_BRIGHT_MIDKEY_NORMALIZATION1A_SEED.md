# M9 BESTFIT1A — BRIGHT_MIDKEY_NORMALIZATION1A SEED

Research-only. No live APK, capture policy, TC20, color science, curve02, or frozen renderer changes.

## Purpose

Define a second conservative BRIGHT morphology for treatment-positive anchors `190346` and `190429` without weakening `BRIGHT_LOWKEY_OPENING1A`.

The user blind review preferred RGB-pivot correction on both anchors, while `190401` from the same indoor sequence preferred Frozen.

## Provisional high-specificity seed

```text
BRIGHT_MIDKEY_NORMALIZATION1A =
    achievedIntentEv < +0.10
    AND tc20Binding == median
    AND previewCenterMedianMinusGlobalMedianY >= 0
    AND finishedGlobalMedianY >= 75
    AND finishedGlobalQ95Y <= 220
```

Threshold status: provisional falsification seed only; not frozen; not live.

This branch intentionally prioritizes specificity over recall.

## Positive anchors

### 190346
- achieved intent = 0 EV
- TC20 median-limited: gain/base ~1.9464, guard ~1.9550
- preview global median 99
- preview centre median 117; centre-global +18
- finished global median 84
- finished centre median 114
- finished q95 210
- structuralLowKeyScore ~0.0075
- user blind preference: RGB075 over RGB035 / Frozen
- seed: ON

### 190429
- achieved intent ~-0.0013 EV
- TC20 median-limited: gain/base ~1.3485, guard ~2.2006
- preview global median 85
- preview centre median 90; centre-global +5
- finished global median 84
- finished centre median 97
- finished q95 182
- structuralLowKeyScore ~0.3235
- user blind preference: RGB075 / RGB035 tie, both over Frozen
- seed: ON

## Same-sequence protective negative

### 190401
- achieved intent ~-0.00075 EV
- TC20 **guard-limited**: gain/guard ~1.2941 vs base ~2.0850
- preview global median 76
- preview centre median 87; centre-global +11
- finished global median 51
- finished centre median 75
- finished q95 199
- structuralLowKeyScore ~0.5058
- user blind preference: **Frozen** over RGB050
- seed: OFF on TC20 binding and finished median

This is strong evidence that `median-limited` versus `guard-limited` is useful context for this subtype, while still not being sufficient on its own.

## Dangerous known controls

### 084303
- TC20 median-limited: gain/base ~2.4624, guard ~2.5520
- preview global median 112
- preview centre median 101; centre-global **-11**
- preview top/middle/bottom medians ~152 / 79 / 59: strong broad spatial split
- finished global median 84
- finished centre median 103
- finished q95 **230**
- seed: OFF on preview centre/global relationship and q95 guard

This frame demonstrates why `median-limited + finished mid-key` is unsafe by itself.

### 18:27:56 prospective high-key split-field hard negative
- TC20 guard-limited: gain ~1.8707 vs base ~1.9394
- preview global median 85
- preview centre median 87; centre-global +2
- preview top median ~203 with ~90% of top field >=192
- finished global median 83
- finished centre median 93
- finished q95 237
- seed: OFF on binding and q95 guard

### 084525 known GOOD
- TC20 guard-limited: gain ~4.5781 vs base ~5.2694
- preview global median 91
- preview centre median 58; centre-global -33
- finished global median 79
- finished centre median 67
- finished q95 226
- seed: OFF

Other known guard-limited controls with high/mid finished body include 084146 and 084224; both stay OFF on binding and q95 context.

## Relationship to LOWKEY_OPENING1A

Do not merge or widen the two branches.

```text
BRIGHT_LOWKEY_OPENING1A
  coherent low-key ambience opened toward a generic body key

BRIGHT_MIDKEY_NORMALIZATION1A
  non-low-key / subject-centred body normalized toward generic mid-key
  under median-limited TC20, without broad upper-tone placement
```

Known six-frame BRIGHT bank under user blind review:
- 184927 -> LOWKEY_OPENING1A -> treatment positive
- 184937 -> LOWKEY_OPENING1A -> treatment positive
- 190346 -> MIDKEY_NORMALIZATION1A -> treatment positive
- 190401 -> HOLD -> Frozen preferred
- 190429 -> MIDKEY_NORMALIZATION1A -> treatment positive
- 194307 -> LOWKEY_OPENING1A -> treatment positive

This gives 5/6 treatment-positive coverage while preserving the one Frozen winner in the current six-frame bank, but the second branch is still derivation-set evidence and requires prospective falsification before promotion.

## Treatment

Treatment operator remains RGB-ratio-preserving pivoted density with research candidate bank:

```text
RGB035
RGB050
RGB075
```

Absolute BRIGHT research ceiling remains 0.75 EV pivot strength, not -0.75 EV global exposure.

Do not derive treatment strength directly from this selector's thresholds. Eligibility and amount remain separate.

## Next falsification

Challenge the seed on untouched prospective and known GOOD frames that are:
- median-limited
- finished median ~75-100
- centre at/above global preview key
- q95 <=220

Any GOOD activation should veto promotion and refine the morphology rather than weaken the frozen-default principle.
