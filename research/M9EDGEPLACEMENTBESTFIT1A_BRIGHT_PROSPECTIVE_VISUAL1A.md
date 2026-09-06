# M9 EDGEPLACEMENT BESTFIT1A — BRIGHT PROSPECTIVE VISUAL1A

Research-only. No live APK, capture policy, TC20, curve02, color science, JPEG quality, or frozen renderer change.

## Purpose

Record user visual classification of the two surviving activations from the 47-frame untouched prospective BRIGHT_MIDKEY_NORMALIZATION1A falsification cohort, then compare those judgements with the existing structural BRIGHT morphologies before any selector retuning.

## Prospective visual classification

### 17:38:28 — `IMG_20260905_173828_1788626308900_00`

Prospective diagnostics:

- TC20 median-limited: base gain ~0.946, guard ~2.099
- preview global median 107 Y
- preview center median 121 Y, center-global +14 Y
- achieved intent 0 EV
- finished global median 81 Y
- finished q95 182 Y
- `structuralLowKeyScore = 0`

User judgement:

> Frozen looks okay; no change would have been recommended.

Classification:

`FROZEN_PREFERRED / GOOD PROSPECTIVE FALSE ACTIVATION`

This frame is direct prospective evidence that the refined scalar MIDKEY conjunction remains insufficient. Its global metrics overlap the historical treatment-positive MIDKEY anchors, yet the photograph is already correct enough to leave unchanged.

Do not tune the preview-median ceiling around this frame. The missing discriminator is structural / spatial rather than another simple global brightness threshold.

### 18:15:59 — `IMG_20260905_181559_1788628559798_00`

Prospective diagnostics:

- TC20 median-limited: base gain ~2.063, guard ~3.703
- preview global median 66 Y
- preview center median 66 Y
- preview top/middle/bottom source medians ~65 / 70 / 63 Y
- display-space 3x3 preview is broadly low-key with very little >=192 Y area
- achieved intent approximately 0 EV
- finished global median 82 Y
- finished q95 161 Y
- finished center50 median 100 Y
- finished middleCenter33 median 114 Y
- `structuralLowKeyScore = 0.876096`

User judgement:

> Frozen looks okay, but it is worth testing whether the exposure/body could go a bit darker.

Classification:

`FROZEN_ACCEPTABLE / MILD_DENSITY_TEST`

This is not labelled BRIGHT_FAIL. It is acceptable at Frozen and therefore cannot justify mandatory automatic correction from eligibility alone.

## Mechanism reclassification

The two prospective survivors are not actually the same morphology.

`173828` has `structuralLowKeyScore = 0` and strong spatial variation. It is a false activation of the provisional MIDKEY selector.

`181559` has `structuralLowKeyScore = 0.876096`, TC20 gain ~2.063, intent < +0.10 EV, and finished median 82 Y. It therefore independently satisfies the existing research-only `BRIGHT_LOWKEY_OPENING1A` seed:

```text
achievedIntentEv < +0.10
AND structuralLowKeyScore >= 0.60
AND tc20Gain >= 1.50
AND finishedGlobalMedianY >= 75
```

That is an important result: the existing structural low-key feature separates the user-preferred Frozen first frame from the second frame far more cleanly than the proposed `preview global median <= 120 Y` MIDKEY refinement.

However, `181559` also establishes a new caution for LOWKEY_OPENING1A: detecting the correct opening mechanism is not equivalent to proving that the resulting Frozen JPEG is photographically bad enough to require intervention.

Eligibility and intervention severity must remain separate.

## Treatment implication for 181559

Use the established RGB-ratio-preserving 0.85-pivot density operator, not a uniform global negative exposure shift:

```text
pivot = 0.85
w(Y) = clamp(1 - Y/pivot, 0, 1)
EV(Y) = -strength * w(Y)
scale(Y) = 2^EV(Y)
```

Research bank remains:

```text
Frozen
RGB035
RGB050
RGB075
```

For the current finished global median of 82 Y, the monotonic pivot law predicts approximately:

- Frozen: 82 Y
- RGB035: 71 Y
- RGB050: 66 Y
- RGB075: 59 Y

Approximate upper-tail response:

- q95 161 Y -> ~151 / 147 / 141 Y
- q99 198 Y -> ~194 / 192 / 189 Y

The user's request for only "a bit darker" makes RGB035 the primary treatment candidate. RGB050 and RGB075 remain useful blinded stress bounds, not assumed preferred treatments.

## Current research conclusions

1. The refined `BRIGHT_MIDKEY_NORMALIZATION1A` selector has **failed prospective falsification** because 173828 is a visually GOOD activation.
2. Do not promote the `preview global median <= 120 Y` refinement into live or frozen selector logic.
3. Do not fit a new scalar threshold around 173828.
4. Spatial / structural morphology is necessary for any future MIDKEY branch.
5. 181559 is better explained by the existing LOWKEY morphology than by MIDKEY normalization.
6. LOWKEY eligibility still does not imply mandatory correction: 181559 Frozen is acceptable and should be treated as HOLD unless a bounded treatment is clearly preferred.
7. The next visual experiment for 181559 is Frozen versus RGB035 first, with RGB050/RGB075 retained as blinded bounds if exact replay is available.
8. No APK or global rendering change is justified by this result.

## Architectural consequence

The evidence strengthens a two-stage BRIGHT policy:

```text
structural eligibility / mechanism
        ↓
photographic severity / treatment value
        ↓
HOLD if Frozen is already acceptable
        ↓
otherwise bounded RGB-pivot density candidate
        ↓
finished-response safety / rollback
```

The goal remains rare best-fit correction, not universal brightness normalization.
