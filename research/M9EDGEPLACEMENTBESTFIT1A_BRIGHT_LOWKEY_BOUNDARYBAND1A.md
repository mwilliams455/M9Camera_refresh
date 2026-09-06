# M9 BESTFIT1A — BRIGHT LOWKEY BOUNDARYBAND1A

Research-only. No live APK, capture policy, TC20, renderer, curve02, color science, JPEG quality, or DNG change.

## Purpose

Separate threshold sensitivity from production eligibility for `BRIGHT_LOWKEY_OPENING1A`.

The existing selector remains unchanged:

```text
achievedIntentEv < +0.10
AND structuralLowKeyScore >= 0.60
AND tc20Gain >= 1.50
AND finishedGlobalMedianY >= 75
```

`0.60` remains a provisional high-specificity falsification floor, not a frozen production constant.

## Critical boundary frame — 181404

`IMG_20260905_181404_1788628444407_00`:

- achieved intent ~0 EV
- structuralLowKeyScore = 0.5447914875
- TC20 gain = 2.5540036931x
- finished global median = 82 Y
- preview median = 78 Y
- preview q95 = 192 Y
- finished q95 = 196 Y
- finished center q95 = 218 Y

It therefore satisfies the intent/gain/finished-body terms and misses LOWKEY only on the 0.60 structural floor.

## Why the score differs from prospective 181559

The SCENEEXPOSURE1D score is:

```text
min(lowKeyMedianEvidence, lowKeyDarkBodyEvidence)
* lowBroadBrightEvidence
* lowSpatialAxisSeparationEvidence
* nonSevereBacklightEvidence
* existingLandscapeProtectionBypass
```

For 181404:

```text
lowKeyMedianEvidence              0.559872
lowKeyDarkBodyEvidence            0.807346
lowBroadBrightEvidence            0.973064
lowSpatialAxisSeparationEvidence  1.0
nonSevereBacklightEvidence        1.0
existingLandscapeProtectionBypass 1.0
structuralLowKeyScore             0.544791
```

For 181559:

```text
lowKeyMedianEvidence              0.876096
lowKeyDarkBodyEvidence            1.0
lowBroadBrightEvidence            1.0
lowSpatialAxisSeparationEvidence  1.0
nonSevereBacklightEvidence        1.0
existingLandscapeProtectionBypass 1.0
structuralLowKeyScore             0.876096
```

Thus the separation is dominated by preview-body placement rather than a different spatial/backlight morphology. For the 181404 component values, score 0.60 corresponds approximately to preview median ~76 Y. This is evidence that the numeric floor must be falsified prospectively rather than treated as semantic truth.

## Important upper-tail difference

181404 also has substantially stronger surviving highlight structure than 181559:

| metric | 181404 | 181559 |
|---|---:|---:|
| preview q95 | 192 | 141 |
| finished q95 | 196 | 161 |
| finished center q95 | 218 | 166 |

This may be photographically meaningful, but retained historical LOWKEY-positive evidence does not currently contain enough comparable preview-q95 detail to justify adding a q95 protection term. Do not create one from this single boundary frame.

## Boundary-band diagnostic

Research overlay only:

```text
base = intent < +0.10
       AND tc20Gain >= 1.50
       AND finishedGlobalMedianY >= 75

if base AND score >= 0.60:
    STRONG_CANDIDATE
elif base AND 0.50 <= score < 0.60:
    BOUNDARY_HOLD
else:
    OFF
```

`BOUNDARY_HOLD` always publishes Frozen. It is a collection/review state, not treatment eligibility.

In the completed 47-frame 2026-09-05 natural cohort:

- strong LOWKEY activation: 181559
- newly identified boundary/HOLD case: 181404
- the 12 score-qualified controls already documented remain governed by gain/body rejection where applicable

## Development consequence

Do not lower the 0.60 selector to recover 181404.

Instead:

1. Keep 181404 Frozen unless later blind treatment evidence says otherwise.
2. Prospectively collect future `BOUNDARY_HOLD` frames.
3. Classify Frozen visually before generating treatment candidates.
4. If boundary frames repeatedly prove treatment-positive, investigate a second mechanism or a better continuous structural descriptor.
5. If boundary frames are usually already right, retain the 0.60 high-specificity floor.
6. Do not add a new upper-tail/q95 veto until historical and prospective positives support it.

Priority remains zero GOOD false corrections and preservation of normal M9 rendering.
